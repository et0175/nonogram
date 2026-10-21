# Puzzle Creation (CTX-001) — SRE / operator's perspective

## Why this matters to `sre`

Only one of the three containers is a service you can be paged about: the admin
panel, a Flask app behind gunicorn on Render, with a Postgres database. The CLI and
the web UI are local processes a person starts and stops — nothing to monitor, no
uptime, no deployment.

Two properties of that one service are worth knowing before the first incident:
**every generation is synchronous inside the HTTP request**, so the slow routes'
budgets are what keep a worker alive; and the panel is **single-process by
construction, not by configuration**, so "scale it out" is not a lever you have.

A third thing: this doc can tell you what the code does. It cannot tell you what
production runs. See "What is not determinable from code".

## Description

| Surface | How it runs | Access control | State |
|---|---|---|---|
| COMP-001 CLI | `nonogram generate …`, one process, exits | none needed | writes exports to `--out` |
| COMP-008 web UI | `nonogram serve`, stdlib `ThreadingHTTPServer`, **same process** as the CLI's entry point | a loopback bind, plus a cross-origin refusal | exports, plus ≤ 8 retained temp uploads |
| COMP-009 admin panel | `start.sh` → `gunicorn … nonogram.admin.app:create_app()`, Render | loopback by default, **or** one credentialed door | Postgres, plus uploaded pictures and covers on disk |
| COMP-010 database | Postgres via SQLAlchemy + Alembic | reached by COMP-009 alone | the only persistent state in the system |

The deployed panel's door is covered in
[09 — the three inbound adapters](../09-the-three-inbound-adapters.md). The two
things to carry into an incident: it **fails closed at boot** (an
`AdminConfigurationError` in the *build log*, before a socket exists), and in
deployed mode it answers a `Host` it does not recognise with a **bare 404** while
logging the detail for you — `app.logger.warning("refused: Host %r does not match
%s=%r", …)` (`app.py:1350`), "because the one refusal designed to be
indistinguishable from 'no such page' is also the one they have to debug blind."

## Examples

**The timeout chain, derived end to end.** `start.sh`'s `--timeout 120` is not a
default left alone, and the file says so:

> `--timeout 120` is not a default left alone. It has to clear the worst case of
> the slowest route: `POST /regrade` stops starting new rows after
> `REGRADE_BUDGET_SECONDS` (60 s) and a row already started may run for
> `GENERATION_BUDGET_SECONDS` (30 s) more, so the ceiling is 90 s.

Re-derived from the constants: `admin/regrade.py:141` is
`REGRADE_BUDGET_SECONDS = 60.0`, `orchestrator.py:341` is
`GENERATION_BUDGET_SECONDS = 30.0`. **90 s, cleared by 120.** And the relationship
is not a comment: `tests/test_admin_serving.py` reads `--timeout` out of `start.sh`
and asserts it exceeds the sum, "so the two cannot drift apart silently."

The batch route has its own chain: `BATCH_BUDGET_SECONDS = 75.0` is checked
**before** each candidate, so one that starts always finishes, giving a true
ceiling of `75 + 30 = 105 s` (`orchestrator.py:306`) — **also inside 120, with
15 s of margin.**

**Why `WEB_CONCURRENCY` is pinned at 1, and what it would take to raise it.**
`start.sh` gives two independent reasons and one procedure:

> WEB_CONCURRENCY stays at Render's 1 (CARD-086 G-4): nothing here has been
> examined for multi-worker safety, and the admin keeps in-memory state in its
> legacy non-DB mode.

> Before raising WEB_CONCURRENCY below, read this … The manual grid edit is a
> TWO-PHASE flow held in the serving process: `POST /puzzle/<id>/edit/verify`
> grades a replacement grid and remembers the proof on the `PuzzleReviewService`
> instance, and `POST /puzzle/<id>/edit` stores the grid that proof is for. With
> two workers the verify and the approve can land on different processes, and the
> second one has no proof — so the save refuses with "verify it again" rather than
> storing anything ungraded. **It fails closed, but it fails closed INTERMITTENTLY,
> which reads as a broken editor.** Raising this needs the proof moved out of
> process first (a shared cache, or a staging row), not just a bigger number.

The proof cache is bounded at `MAX_REMEMBERED_VERIFICATIONS = 16`
(`admin/puzzle_review.py:54`).

**The OOM that had no traceback.** `CARD-145.md`'s worktree notes record the
diagnosis method, which is reusable: the owner reported "render crashes when I try
to generate pdf", **with no traceback in the logs — "the signature of an OOM kill
rather than an exception."** It was diagnosed by arithmetic: 2550 × 3300 × 3 bytes
per page times the page count, against a 512 MB instance.

The fix is a generator, not a tuning knob. `interior_stream`
(`admin/book_pdf_generator.py:6503`) draws pages one at a time and holds none, and
its three page counts come from the plan's own arithmetic "so an export can report
what it is about to write **without building 25.2 MB of bitmap per page to count
them**". Pinned by `test_the_whole_book_holds_one_page_bitmap_at_a_time`. If a
future change reintroduces an eager page list, the symptom will again be a silent
kill rather than an exception.

**How to tell a guard refusal from a database stall.** `CARD-085.md`'s notes carry
a measured discriminator: with `DATABASE_URL` pointed at a black-holed address, a
request carrying the Render `Host` came back **404 in 6.9 ms**, while the same
request carrying `Host: localhost` took **75 seconds** and raised
`OperationalError`. "That gap is the whole proof that the 404s were the guard and
not the database." Pinned behaviourally by
`test_a_wrong_credential_never_reaches_the_database`
(`tests/test_admin_auth.py:166`): **a refusal never costs a database query.**

**The connect deadline, and where it does and does not apply.**
`CONNECT_TIMEOUT_SECONDS = 10` (`db/session.py:40`) is passed as `connect_args`
**only** for `_TIMEOUT_SCHEMES = ("postgresql", "postgres")` (`:48`), read off the
**raw** URL so both spellings stay live. Any other scheme gets no connect
deadline.

**A driver change that broke a boot.** `pyproject.toml:46` records it:
SQLAlchemy 2.1.0 changed the default DBAPI for a bare `postgresql://` URL from
psycopg2 to psycopg (v3), and the deployed panel failed to boot with
`No module named 'psycopg'`. The cap that papered over it was removed by CARD-148
and the driver is now **named in the URL** by `db.session.normalized_url`, with
`tests/test_db_url_driver.py` failing if the named driver is not installed.

## Operational limits, failure modes, capacity

### Enforced bounds, with their constants

| Bound | Value | Where | What exceeding it does |
|---|---|---|---|
| one generation request | `GENERATION_BUDGET_SECONDS = 30.0` | `orchestrator.py:341` | `SolverTimeout`, **no verdict**, puzzle stays unexportable |
| attempts per request | `MAX_RETRY_ATTEMPTS = 30` | `orchestrator.py:192` | `GenerationAbandoned` |
| pixel nudges per image run | `MAX_NUDGE_ATTEMPTS = 5` | `:261` | POL-003's refusal; the picture stops being altered |
| revealed cells (opt-in) | 5% of cells, floored — 5 / 20 / 45 at 10×10 / 20×20 / 30×30 | `:287`, `:842` | `GivenCellsCapExceeded`; the picture is left unaltered |
| consecutive batch abandonments | `MAX_CONSECUTIVE_ABANDONMENTS = 3` | `:247` | the batch stops starting candidates |
| batch wall clock | `BATCH_BUDGET_SECONDS = 75.0` | `:312` | the batch returns what it has |
| batch size | `MAX_BATCH_COUNT = 50` | `:323` | refused up front |
| re-grade wall clock | `REGRADE_BUDGET_SECONDS = 60.0` | `admin/regrade.py:141` | stops starting new rows |
| gunicorn request | `--timeout 120`, `--graceful-timeout 30` | `start.sh:47` | worker killed |
| web UI idle socket | `IDLE_TIMEOUT_S = 30` | `web/handler.py:77` | socket closed; "the only thing being bounded is *silence*" |
| web UI request body | `MAX_BODY_BYTES = 65536` | `:89` | 413, drained first so the refusal is delivered rather than arriving as a reset |
| web UI retained uploads | `MAX_RETAINED = 8` | `web/uploads.py:55` | oldest evicted and unlinked |
| admin edit proofs | `MAX_REMEMBERED_VERIFICATIONS = 16` | `admin/puzzle_review.py:54` | oldest proof forgotten; the save asks for re-verification |
| admin password | `MIN_ADMIN_PASSWORD_LENGTH = 16` | `admin/app.py:481` | **boot refused**, in the build log |

### Capacity, from the project's own measurements

Generation cost at density 50 (`orchestrator.py:299`): **~0.06 s at 20×20, 0.55 s
at 25×25, 3.90 s at 30×30.** So a 50-puzzle batch is ~3 s at the small end and
~195 s at the large one — which is exactly why `BATCH_BUDGET_SECONDS` is a *time*
budget and not a count: 75 s "is what makes the *same* request safe at every
extent, returning about 19 puzzles of a 50-puzzle 30×30 batch instead of dying at
120 s with nothing."

Re-grade cost, measured over a **copy** of the 290-row development database
(`CARD-086`): 290 rows, 20 skipped as not uniquely solvable, **5.5 s total,
19 ms mean, 2 ms median.**

Book PDF memory: one page bitmap at a time, 2550 × 3300 × 3 bytes ≈ **25.2 MB per
page** on the Book 1 profile. The historical failure was holding more than one on a
512 MB instance.

Performance is **asymmetric by design**: line logic alone finishes easy and dense
grids in milliseconds; random mid-density grids at the top of the supported range
are the known-hard class. ADR-0001's 5 s p95 for grids up to 20×20 is a *benchmark
gate* (`tests/bench_generate.py`), not a failure boundary — the only enforced
ceiling is the 30 s deadline.

### Failure modes

- **A timeout is not a verdict.** `SolverTimeout` returns nothing, is not retried,
  and leaves `confirm_uniqueness` unreached so INV-002 keeps the puzzle
  unexportable. The storage guard treats it the same way: `"uniqueness could not
  be proven within {n}s — unproven is not proven"` (`admin/puzzle_review.py:588`).
  **A timeout never stores anything and is never cached** — "a timeout is a fact
  about one run's clock" (`:641`).
- **A batch keeps partial work.** Abandoned candidates are skipped, not fatal, and
  the budget is checked before each candidate so one that starts always finishes.
- **A gunicorn worker killed mid-batch loses what it had produced** — the reason
  `BATCH_BUDGET_SECONDS` exists at all (`orchestrator.py:289`).
- **The readiness gate is not atomic in DB mode.** `book_manager.py:2247` states
  it, and states the scope honestly: the row is read and judged in one session and
  written in another; "the exposure is the whole DB layer's, not this method's. It
  is accepted here because the panel is a single-user loopback tool (CON-015)."
- **The deployed panel does not offer the re-grade at all.**
  `REGRADE_ENABLED = not remote_host` (`app.py:1283`); both routes `abort(404)` and
  the nav hides it, because it "rewrites every stored grade with no undo … not a
  button on a panel the internet can reach."
- **`nonogram serve` does not drain on Ctrl-C.** Handlers are daemon threads and
  `socketserver`'s join tracks only non-daemon ones, so `server_close` returns
  immediately and a generation still running is abandoned (`web/server.py:107`).
  **Up to 8 retained temp uploads are left for the OS to reap**: `uploads.clear()`
  exists but "the server has no shutdown hook of its own to call it from"
  (`web/uploads.py:107`).
- **Unset `DATABASE_URL` is not an error — it is a different mode.** The admin
  panel silently falls back to in-memory dicts and logs "Running in in-memory mode
  (DATABASE_URL not set)" (`app.py:1367`). There is **no sqlite fallback**: the
  `RuntimeError` at `db/session.py:196` only fires if something reaches the engine
  while the variable is unset.
- **The `Procfile` and `start.sh` disagree, and one of them is known-broken.**
  `Procfile` is `flask --app src.nonogram.admin.app run --host=0.0.0.0` — Flask's
  dev server, every interface, and the `src.` prefix `start.sh` documents as a
  trap: it imports the package a second time under a second name, producing two
  distinct `LongestSideBucket` enums, and **Print setup dies with
  `ValueError: tuple.index(x): x not in tuple` on any book whose plan is stored.
  A plan-less book renders fine, which is what made it look like bad data in
  production.** If that error appears, check the import path before the data.

### Logging and observability

- Every export failure is `app.logger.exception(...)` **before** it is flashed and
  redirected (`app.py:5513`, CARD-171) — so the traceback is in the log even though
  the user sees a flash.
- The proof-page path distinguishes "the one expected refusal (a trim that leaves
  no room for the proof note)" from "anything else is a bug worth keeping the stack
  of" (`:5552`).
- `Puzzle.recovery` (`RecoveryLog`, `orchestrator.py:863`) is **observability and
  nothing else**: "nothing reads these numbers to decide anything, no bound is
  checked against them, and deleting the field would change no verdict." It is not
  emitted anywhere by default.
- gunicorn is configured with `--access-logfile -` and `--error-logfile -`, i.e.
  both to stdout/stderr.
- There are **no metrics, no tracing and no health-check endpoint** in this
  codebase. `GET /api/batch/<id>/status` (`app.py:5846`) is a batch progress API,
  not a liveness probe.

### Security posture, briefly

- Default is loopback only, in all three surfaces.
- The deployed panel's two doors are **mutually exclusive by construction**:
  setting `ADMIN_ALLOWED_HOST` *replaces* the loopback rule, because behind a
  reverse proxy `REMOTE_ADDR` is the proxy — "Render's logs report every request as
  `127.0.0.1`" — so leaving the loopback door open would make `Host: localhost` a
  password bypass (`app.py:1326`).
- `SESSION_COOKIE_SECURE` is `False` by default and raised to `True` only in
  deployed mode (`app.py:1227`, `:1274`). `SECRET_KEY` falls back to
  `"dev-key-change-in-production"` in local mode, and the **boot refuses** that
  literal in deployed mode.
- `X-Content-Type-Options: nosniff` and `X-Frame-Options: SAMEORIGIN` are set on
  every response; `Access-Control-Allow-Origin: *` is set in local mode and
  **dropped in deployed mode** (`app.py:1391`).
- The puzzle player ships the solution grid in its page payload, and that is
  explicitly scoped to the admin panel behind its door (ADR-0038/R6, CON-021):
  "**a public player must not do this**" (`app.py:6202`). If the panel is ever put
  in front of untrusted users, that is the first thing to revisit.

## What is not determinable from code

**What production actually runs.** `render.yaml` declares itself
non-authoritative on its own first line, and `docs/deploy/render.md` marks the
start command, build command, Python version, whether `alembic upgrade head` runs
on deploy, and the env-var set each as `TODO(owner)`. Its one evidence line records
that **as last observed on 2026-09-23, production ran Flask's dev server
(`flask run`) on `src.nonogram.admin.app`** — i.e. the `Procfile` shape, not
`start.sh`. Everything in this file about `--timeout 120` and
`WEB_CONCURRENCY` describes `start.sh`, and whether it is in force is a dashboard
question.

The Python version is a second instance of the same gap: `pyproject.toml:9` is
`requires-python = ">=3.14"`, `runtime.txt` says `python-3.11.11`, and
`render.yaml` pins 3.11.

**Whether the three unread tables hold rows** — `users`,
`user_selected_books`, `generation_history` (see
[10](../10-persistence-and-the-unmodelled-edges.md)). Code-wise unreachable; the
component diagram calls the disposition "CARD-111 option B, undecided". Answering
it needs the live database.

**Whether any stored puzzle still carries `difficulty_tier = 'guess'`** — retired
by ADR-0031. The readers would treat it as "no recognisable tier", and
`book_plan.selection_cells` would drop such a row from every plan bucket, so it
would silently belong nowhere.

## Related docs

- Narrative: [09 — the three inbound adapters](../09-the-three-inbound-adapters.md) · [07 — book assembly](../07-book-assembly-and-the-admin-panel.md) · [10 — persistence](../10-persistence-and-the-unmodelled-edges.md) · [04 — uniqueness and recovery](../04-uniqueness-and-recovery.md)
- Siblings: [architect](architect.md) · [developer](developer.md) · [puzzle-creator (ACT-001)](puzzle-creator.md)
- ADRs: [ADR-0001](../../../../../meta/architecture/decisions/adr/0001-generation-time-thresholds.md) · [ADR-0002](../../../../../meta/architecture/decisions/adr/0002-retry-and-nudge-bounds.md) · [ADR-0011](../../../../../meta/architecture/decisions/adr/0011-generation-timeout-mechanism.md) · [ADR-0030](../../../../../meta/architecture/decisions/adr/0030-admin-remote-access-behind-a-credential.md) · [ADR-0032](../../../../../meta/architecture/decisions/adr/0032-admin-storage-guarantees.md)
- Repo: `start.sh` · `Procfile` · `render.yaml` · `docs/deploy/` · `DATABASE_MIGRATIONS.md` · `ADMIN_SETUP.md`
