# CARD-086: Serve the deployed admin with a production server, and give its slowest route a bound it can live with

**Status:** done
**Priority:** P2
**Category:** enabler
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/086-production-wsgi-server
**Worktree:** ../PythonProject4-CARD-086
**Source:** owner request, after CARD-085 — Render's logs warn on every boot
**Idea:** —
**Wave:** 1
**Depends on:** CARD-085 (merged 84fcc46) — the panel is only worth serving properly now that it is reachable
**Touches:** pyproject.toml (the `admin` extra), requirements.txt, start.sh, render.yaml, ADMIN_SETUP.md, tests/test_admin_serving.py (new)
**Review score:** merged without a review cycle, at the owner's call — production was down and the card carries the diagnostics
**Started:** 2026-09-14
**Closed:** 2026-09-14
**Actual:** —
**Merge commit:** f381d62
**Blocked by:** —

## Why

Render runs the admin panel with Flask's development server, and says so on
every boot:

```
 * Serving Flask app 'src.nonogram.admin.app'
 * Debug mode: off
WARNING: This is a development server. Do not use it in a production deployment.
```

`start.sh` is `python -m flask --app src.nonogram.admin.app run --host=0.0.0.0
--port=$PORT`. Werkzeug's server is single-threaded by default, has no request
timeout, no graceful shutdown, and no worker supervision — it is a debugging
convenience that has been carrying a public, credentialed admin panel since
CARD-085 merged.

### This is not an ADR-0006/R1 revision — I said twice that it was, and I was wrong

The claim was that adding `gunicorn` changes the runtime dependency baseline.
It does not, and the shape that makes it not is already in `pyproject.toml`:

```toml
dependencies = ["Pillow>=10.0", "numpy>=1.24"]           # ADR-0006/R1's baseline

[project.optional-dependencies]
admin = ["Flask>=3.0", "Werkzeug>=3.0", "reportlab>=4.0"]
db    = ["SQLAlchemy>=2.0", "alembic>=1.13", "psycopg2-binary>=2.9"]
```

ADR-0006/R1's check (`test_the_dependency_baseline_is_still_closed`,
`tests/test_export_pdf.py:1236`) reads `manifest["project"]["dependencies"]`
and asserts it equals `{pillow, numpy}` — the **core** list. The extras are
outside it by construction, and the `admin` extra's own comment says why:
Flask and reportlab live there because "a bare `pip install nonogram`
(CLI-only) has no use for any of the three."

`gunicorn` is a server for the admin panel. It belongs beside Flask in the
`admin` extra, and ADR-0006/R1 is untouched. No ADR is needed for this card —
only the honest note that the earlier framing was wrong.

### The part that is a real decision: the slowest route now has a deadline

This is why the card is not "s/flask run/gunicorn/".

Gunicorn kills a worker whose request exceeds `--timeout` (default **30
seconds**). The dev server has no such limit, so nothing in this codebase has
ever had to fit one. `POST /regrade` does not fit:

`admin/regrade.py:334` takes `budget_seconds` **per row**, not per request
(`ADR-0011`'s 30s bound is per solve). So the worst case is rows x 30s:

| database | rows | worst case | vs. a 30s worker timeout |
|---|---|---|---|
| `nonogram_admin.db` | 16 | 8 min | 16x over |
| Render (production) | 86 | **43 min** | **86x over** |
| `nonogram_dev` | 294 | 147 min | 294x over |

The typical case is far better — most rows solve in milliseconds — but a
*timed-out* row burns the full 30s, and two of those alone exceed the default.
Under the dev server a long regrade merely blocks; under gunicorn it is killed
mid-run, and `regrade` commits per-run, not per-row.

Three honest options, to be decided in this card rather than defaulted into:

1. **Raise `--timeout` past the worst case.** Simple, and wrong in the usual
   way: it disables the protection for every other route to accommodate one.
2. **Give the route its own bound**, and make the report say it stopped early
   — a batch-level deadline, the way CARD-083 gave `generate_batch` its own
   number rather than borrowing the per-puzzle one.
3. **Move the run off the request** (a job, polled by the page). The most
   correct and the most work; also the first thing in this codebase that would
   need one, since no admin path runs in a thread today (`grep` for
   `Thread(`/`ThreadPool` under `src/nonogram/admin/`: no hits).

**Recommended: (2).** It matches an existing precedent, keeps the whole thing
synchronous, and turns "the worker died" into "the report says 31 of 86 rows
were re-graded, run it again". (3) is the right answer if the panel ever gets
a second long route; it is not warranted by one.

## Acceptance criteria

- **AC-1** (a production server) — the deployed panel is served by `gunicorn`,
  and the "development server" warning no longer appears in Render's boot log.
  `gunicorn` is declared in the `admin` extra in `pyproject.toml` and in
  `requirements.txt`.
  *test:* `TestAdminServing_UsesAProductionServerInDeployment`
- **AC-2** (ADR-0006/R1 is untouched) — `project.dependencies` still reads
  exactly `Pillow` and `numpy`.
  *test:* the existing `test_the_dependency_baseline_is_still_closed`, unmodified
- **AC-3** (the factory still refuses to boot misconfigured) — gunicorn loads
  the app through `create_app()`, so CARD-085's `AdminConfigurationError` still
  fails the boot rather than starting a worker that serves an open panel. A
  worker that cannot build the app must not be restarted into a loop that hides
  the error.
  *test:* `TestAdminServing_AMisconfiguredBootStillFails`
- **AC-4** (the slow route fits its bound) — `POST /regrade` completes within
  the configured worker timeout for a table the size of production's, or
  returns a report saying it stopped early. Whichever option is chosen, the
  bound is one number, stated once, and the report names it.
  *test:* `TestRegrade_StopsWithinItsOwnBoundAndSaysSo`
- **AC-5** (measured, not assumed) — the card records the *actual* wall-clock
  of a full re-grade over a copy of production's 86 rows, so the bound in AC-4
  is chosen against a measurement. Copy only, never the live database
  (CARD-077 G-1).
- **AC-6** (the local path is unchanged) — `python -m nonogram.admin.app` and
  `flask --app nonogram.admin.app run` still work for local use, still bind
  loopback, and still need no gunicorn installed.
  *test:* the existing `TestAdminPanel_BindsLoopbackOnlyByDefault`, unmodified

## Guardrails

- **G-1** — `project.dependencies` in `pyproject.toml` is not touched.
  ADR-0006/R1's baseline stays exactly `Pillow` + `numpy`; `gunicorn` goes in
  the `admin` extra beside Flask.
- **G-2** — CARD-085's request hook is not touched. The credential, the
  host rule and the cross-site refusal are a separate concern from which
  server runs the WSGI app, and a change to the server must not become an
  occasion to adjust them. CON-016 and ADR-0030 hold unchanged.
- **G-3** — local development does not gain a required dependency. A developer
  with `pip install -e '.[dev]'` and no `admin` extra must still run the tests.
- **G-4** — `WEB_CONCURRENCY` stays at 1 unless this card proves otherwise.
  Nothing here has been examined for multi-worker safety, and the admin holds
  in-memory state in its legacy (non-DB) mode; more than one worker is a
  separate question, not a free win.
- **G-5** — no behaviour change to grading, generation, or any route's output.
  If option (2) is taken, a run that fits the bound must produce exactly the
  report it produces today.

## Open questions for the owner

- ~~**Q-1** — which of the three options for `POST /regrade`?~~ **Answered
  2026-09-14: option 2** — the route gets its own bound and the report says it
  stopped early.
- ~~**Q-2** — `autoDeploy: true` sends every merge to production.~~ **Answered
  2026-09-14: turn it off.** Folded into this card rather than split out: it is
  one line in the same file, and shipping a server change on a branch that
  still auto-deploys would be the last thing this card should do.

## Worktree notes

**AC-5, measured before the bound was chosen.** A full re-grade over a *copy*
of the 290-row development database (`pg_dump | psql` into a scratch database,
dropped after — CARD-077 G-1: copies only):

| | |
|---|---|
| rows | 290 (20 skipped as not uniquely solvable) |
| total | **5.5 s** |
| mean / median | 19 ms / 2 ms |
| p95 / p99 | 46 ms / 290 ms |
| slowest row | 2.1 s |
| rows over 10 s | **0** |

So the 43-minute worst case in the card's "Why" is arithmetic, not observation:
real data re-grades a table larger than production's in under six seconds.
`REGRADE_BUDGET_SECONDS = 60` is therefore over ten times the measured cost and
will not fire on data like today's. It exists for the case the arithmetic
allows and the measurement did not contain — enough rows hitting ADR-0011's own
30 s ceiling to outlast a worker.

**The ceiling is 90 s, not 60.** The deadline is checked *before* each row, so a
row that starts always finishes: `REGRADE_BUDGET_SECONDS + GENERATION_BUDGET_SECONDS`.
`--timeout 120` clears it, and `tests/test_admin_serving.py` reads the flag out
of `start.sh` and asserts it clears the sum — the two numbers cannot drift
apart in a comment.

Checking before the row rather than interrupting one is also what keeps the
clock out of `SkipReason`. A row skipped for running out of time would make the
skip list ambiguous between "this is not a puzzle" (CON-005) and "we were in a
hurry", which is the one thing it must never be.

**An existing test caught a real bug in this change.** I computed
`run_deadline = monotonic() + run_budget_seconds` one line *above*
`session.begin_nested()`. `monotonic` is an injected seam, so that read is a
call into caller code, and on the dry-run path it fell outside the savepoint —
`test_a_dry_run_undoes_a_write_made_while_it_ran` failed immediately. That test
was written at CARD-077 cycle 2 because deleting the rollback entirely had left
the suite green; it earned its keep a second time here.

**Two of my own tests were wrong before the code was.** The first asserted "no
`flask run` in `start.sh`" over the raw file and matched the comment explaining
what had been removed — it now reads the script with comments stripped. The
second drove the run budget with a fake clock returning small numbers, which
made every *row's* deadline (`monotonic() + budget_seconds`, handed to a solver
that reads the **real** clock) an absolute time decades in the past, so every
row timed out and the test measured nothing it intended. The clock now returns
the real time plus a jumping offset.

**Smoke-tested under real gunicorn**, not only the test client:

```
anonymous GET /              -> 401
authenticated GET /          -> 200
cross-site POST /regrade     -> 403
cross-site link to the panel -> 200
wrong password               -> 401
"development server" in log  -> 0 occurrences
missing ADMIN_PASSWORD       -> AdminConfigurationError, worker refuses to boot
```

CARD-085's boot refusal survives the move: gunicorn loads through
`create_app()`, so the exception propagates out of the worker's app load rather
than being swallowed by an import-time module-level app.
