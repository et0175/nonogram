# CARD-258: Make the next `relation "puzzles" does not exist` red say what it was talking to

**Status:** in_progress
**Priority:** P1
**Category:** ops
**Complexity:** standard
**Estimate:** 0.5d
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/258-the-ops-red-says-what-it-talked-to
**Worktree:** ../PythonProject4-card-258
**Source:** CARD-256's build gates 1 and 2 (2026-10-20) — red then green on the same commit, on a tree carrying CARD-252's `reset_engine()`. The hazard survives the fix that was expected to remove it.
**Idea:** —
**Wave:** 51
**Depends on:** —
**Touches:** tests/conftest.py, tests/test_admin_binding.py, tests/helpers/ (a new diagnostic helper), src/nonogram/db/session.py — only if a read-only accessor is needed
**Review score:** —
**Started:** 2026-10-20T16:52:59Z · **Closed:** — · **Actual:** — · **Merge commit:** —
**Blocked by:** —

## Why — four waves, one signature, no data

The same red has now appeared on build gates in waves 47, 48 and 50: **five failures in
`tests/test_admin_binding.py::TestAdminPanel_RefusesRequestsThatDidNotAddressThisMachine`, with
`relation "puzzles" does not exist` raised inside the server thread**, and a sixth variant where the
page times out because the request died server-side on `uuid.UUID(hex=<float>)` inside SQLAlchemy's
UUID processor. Every occurrence has been solo, guard-enforced, and **green on a re-run of the same
commit**.

Two explanations have been offered and both are dead:

- *psycopg2's prepared statements* — refuted in wave 45: psycopg2 has no `prepare_threshold`.
- *a module-global engine surviving the schema rebuild* — CARD-252 published `reset_engine()` and
  wired it into `_rebuild_public_schema`. **CARD-256's gates ran red then green on a tree carrying
  it.** That card's AC-3 was withdrawn rather than claimed, and its docstring says the failures
  remain unexplained; this is that sentence being right.

So the next step is not a third hypothesis. **It is to make the next occurrence diagnostic.** The
cost of staying blind is measurable: ~16 minutes per re-run, three waves running, plus one
attribution written down and withdrawn.

## What to implement

A failure hook that fires **only** on this error class and records what no traceback currently shows:

1. **Which database the failing connection is attached to** — `SELECT current_database()`,
   `current_schema()`, `current_setting('search_path')`, and the backend pid (`pg_backend_pid()`).
   The derived name (CARD-244) means a connection to the *wrong* database is a one-line proof.
2. **Which engine object served it** — `id(engine)`, its URL, pool status
   (`engine.pool.status()`), and whether `reset_engine()` has been called since process start (a
   counter it already could expose read-only).
3. **Which process and thread** — pid, thread name, and whether the frame is inside a werkzeug server
   thread. These five tests are the only ones in the suite that serve real HTTP from a thread while
   the fixture owns the schema; that is a fact worth confirming rather than assuming.
4. **What the schema actually holds at that moment** — `to_regclass('public.puzzles')` and the row
   from `pg_tables`. "The table is missing" and "we are looking in the wrong place" are different
   failures with the same message.

Write it where it cannot distort the thing it measures: a `pytest_exception_interact` hook or an
`except` path that captures through a **separate connection**, never the failing one, and that is
silent when the error is anything else.

## Acceptance criteria

- **AC-1** *Given* a test that raises `UndefinedTable` for `puzzles`, *then* the report carries the
  four groups above, and the test still fails with its original traceback intact.
  (test: a test that provokes the error against a schema it has dropped itself)
- **AC-2** (the control) *Given* the hook removed, *then* AC-1's test fails. A diagnostic that cannot
  be shown absent is not wired in.
- **AC-3** *Given* any other failure, *then* the hook adds nothing — measured on a selection with an
  ordinary assertion failure, byte-compared against the same run without the hook.
- **AC-4** (guard) *Given* the hook, *then* a passing run is byte-identical to one without it, and
  the suite's skip profile is unchanged.
- **AC-5** *Given* the capture path itself fails (no connection, server gone), *then* the test's own
  failure is still reported and the capture's failure is named, not swallowed. A diagnostic that
  masks the defect it was built for is worse than none.

## Guardrails

- G-1: **No production code changes behaviour.** If `session.py` needs a read-only accessor (a reset
  counter, the engine's id), it is additive and nothing in `src/` calls it.
- G-2: `nonogram_poc` is never created, dropped, connected to or truncated;
  `_refuse_unless_test_database` is neither widened nor bypassed. The capture connection derives its
  URL the same way every other test does.
- G-3: No new runtime dependency.
- G-4: The hook must not run per-test on the happy path — it fires on the exception class only.
- G-5: No test retired without a named survivor; `test_admin_binding.py`'s five parametrisations stay
  exactly as they are. **This card does not try to fix the hazard.**

## Worktree notes

- **[Do not take timing measurements]** other cards may share this machine.
- **[The trap]** The obvious implementation captures through the connection that just failed — which
  is in a broken transaction, so the capture raises `InFailedSqlTransaction` and the report says
  nothing, on exactly the run it was built for. Use a separate connection, and make AC-5 the control
  for that.
- **[The second trap]** This card is worth doing *only* if it is silent and free on the 8627 runs
  that pass. A diagnostic that costs a per-test query is a tax levied forever to catch something that
  happens once a wave.
- **[What success looks like]** the next occurrence produces a line that names a database, a schema,
  an engine and a pid — and that line either proves the connection was attached to the wrong
  database, or proves it was attached to the right one and the table genuinely was not there. Either
  is the first real datum this class has produced.
- **[System contract]** to be derived at dispatch under `meta/kanban/curation.md`, reading the ADR
  files case-insensitively for the reach-limit idiom.

## System contract

Curated to **10 of 29** in-scope rules under `meta/kanban/curation.md`: every rule whose
enforcement does not reach this card's new code is kept; the rest are dropped because the suite runs them
on every gate. **19 dropped.** ADR-0039 present, as the sanity check requires for a card
touching `tests/**`.

- **ADR-0022/R1** — _review-lens — nothing executes it_
  Grid extent crosses module boundaries as a (width, height) pair. No public function signature,
  request field, or export field reduces a grid's extent to a single scalar "size", and no source
  mode constructs a grid from one integer.
- **ADR-0036/R3** — _`kind: test`, but its ADR declares the check's reach stops at the code that existed when it was written_
  Exactly one function in src/nonogram/** puts a round mark on a page. A second one is a defect
  whatever Pillow call it is written with.
- **ADR-0036/R4** — _`kind: test`, but its ADR declares the check's reach stops at the code that existed when it was written_
  No string literal anywhere in src/nonogram/** -- docstrings included -- holds a codepoint in
  U+25A0..U+25FF, U+2022 or U+2219. A round mark is drawn, never typed.
- **ADR-0038/R6** — _review-lens — nothing executes it_
  Only the admin panel's player, behind the CON-015 / CON-016 door, may ship a puzzle's solution
  grid to the browser. A public or reader-facing player must not send the solution before the
  puzzle is solved, and any public phase reopens this ADR (CON-021).
- **ADR-0038/R7** — _review-lens — nothing executes it_
  Browser tests use pytest-playwright with Chromium, declared only in a dev-only extra in
  pyproject.toml. It is never added to project.dependencies or to the admin extra.
- **ADR-0038/R8** — _review-lens — nothing executes it_
  Browser tests run locally, against Chromium installed by `playwright install chromium`. When
  Chromium is not installed, browser tests fail or skip loudly, with a named skip reason visible
  in the run summary. They never pass silently.
- **ADR-0039/R1** — _`kind: test`, but its ADR declares the check's reach stops at the code that existed when it was written_
  A set a guard consults needs a completeness test written before the set, and any claim the guard
  makes about what it catches needs a control that can fail: caught WITH the set member present,
  missed WITHOUT it. A claim whose control cannot fail is narrative, not coverage, and must be
  narrowed to what is measured or deleted.
- **ADR-0039/R2** — _`kind: test`, but its ADR declares the check's reach stops at the code that existed when it was written_
  A guard's set is derived from an authority the runtime can enumerate, not hand-written. Where no
  such authority exists, the guard defaults to deny: a shape it cannot analyse is a FAILURE, never
  a silent pass, and the unanalysable sites become named exemptions under ADR-0039/R3.
- **ADR-0039/R3** — _`kind: test`, but its ADR declares the check's reach stops at the code that existed when it was written_
  An exemption is a claim. Every exemption a guard grants carries a control for what it must NOT
  absorb — caught with the exemption removed, missed with it in place — is held to an equality
  against the sites that exist today, and records whatever it still cannot see as a measured bound
  with its own failing control.
- **CON-021** — _review-lens — nothing executes it_
  Interactive play exists only as the admin panel's puzzle player, behind the door that guards
  every other admin page (CON-015, CON-016). Play state is never persisted on the server; the one
  place it may be kept is the browser's own localStorage, per puzzle.

## Implementation record — `8e40c0c0`

Commit `8e40c0c0` on `card/258-the-ops-red-says-what-it-talked-to`, pathspecs `tests/conftest.py`
`tests/test_admin_binding.py` `tests/helpers/undefined_table_report.py` (new) `src/nonogram/db/session.py`
— the card's `Touches`, exactly. Nothing under `meta/` in it.

`tests/helpers/undefined_table_report.py` is a pytest plugin with **exactly one hook**,
`pytest_exception_interact`, registered by name (`undefined-table-report`) from conftest's existing
`pytest_configure` rather than imported as a hook — which keeps it off the four hook names conftest
already owns **and** makes `-p no:undefined-table-report` a real control. 15 test functions / 21 node IDs
/ **48 assertion nodes**; selection green at 21 passed, the reachable neighbourhood at 201 passed.

### TDD red, and then a better red

The first red was a bare `ImportError` on a helper that did not exist. The agent then wired a **no-op
stub** so each AC would red on its own assertion rather than on collection — **10 failed, 9 passed**, and
the 9 passes were the correct ones: both byte comparisons (a no-op hook *is* byte-identical), the four
negative detector arms, the registration check, the one-hook AST check, the G-1 sweep. That is the right
instinct: a collection error tells you nothing about which claim is unmet.

### 22 mutants, every one red — and three of them changed the work

- **M13 survived and was a DEAD MECHANISM**: a `warnings.catch_warnings()` suppression around the
  capture's lazy imports, whose comment called it load-bearing. **Removed rather than narrowed**, with
  the reasoning recorded: all it could ever do is hide the one thing the byte comparisons exist to catch —
  a warning from the diagnostic's own import *is* the diagnostic changing something besides the section,
  so a red comparison there is the **correct** outcome. Now a declared open bound.
- **M16, M18 and M20 initially survived** → three claims being made without controls. Each got one. The
  best of them: the verdict's **MISMATCH** arm now has a probe where the failing connection is on
  PostgreSQL's maintenance database while the capture resolves to the derived `_test` one — **the card's
  headline "wrong database is a one-line proof", which nothing had ever actually taken.** And G-2's
  refusal consult got a probe with `TEST_DATABASE_URL` naming an invented non-`_test` database behind a
  dead port, so `NOT OPENED` (refusal fired) and `FAILED` (it tried) are distinguishable.
- **Two of its own first-draft mutants were NO-OPS reporting as survivors** (`None or connection.execute(…)`,
  `[] or sorted(…)`). Caught and rewritten as real deletions. **That is wave 50's trap 5 recurring in a
  fresh context** — a no-op mutant and a genuine survivor look identical — and it is now CARD-260's AC-5.

### AC-3 / AC-4 proved byte-identical, by SHA-256 over the whole output

Each probe is a throwaway test file in a temp directory, which is its own rootdir — so the repo conftest
(and with it CARD-255's lock guard) is **not loaded**, the plugin arrives only via `-p`, and "not passed"
is the control. Same file, same directory, run twice:

```
AC-3 ordinary assertion failure: with=0e253e3e23429968 without=0e253e3e23429968 bytes=914/914 identical=True
AC-4 one pass + one skip       : with=1726b62ab40a0b8b without=1726b62ab40a0b8b bytes=375/375 identical=True
```

The only normalisation is a duration token — **which is also how the agent avoided recording a timing**.
AC-1's "traceback intact" needed one further normalisation, hex object addresses, because two processes
print different `id()` values in a default traceback's `self = <…>` lines; it is used **only** there and
is documented at the function. AC-2's real-suite half: `-p no:undefined-table-report` reds
`test_the_diagnostic_is_registered_in_this_very_run`.

### The broken-transaction trap — split, not avoided

Groups 1 and 2 read **libpq attributes only** (`get_dsn_parameters()`, `get_backend_pid()`, `status`,
`get_transaction_status()` via `error.cursor.connection`) — these answer from the client's own handle and
issue **no SQL**. Every question needing SQL goes to a **separate** connection whose URL comes from
`tests.db_name.resolve_test_database_url` and is screened by `conftest._refusal_reason` before anything
opens. Measured rather than reasoned: a query through the failing connection raises
`InFailedSqlTransaction`, while `get_dsn_parameters()`/`get_backend_pid()` answer fine on that same
handle. **M2** (rebuild the capture on the failing DBAPI connection) is the control. Both transaction
states are now on record — the AC-1 probe's connection is `INERROR`, the real instance below was already
rolled back at `IDLE` — **and the libpq-only approach reads both.**

### What it prints, from a provoked real instance — the card's "what success looks like", first try

```
group-1 failing-connection: dbname=…card_258_07a8a3b5229b_test host=localhost port=5432 backend_pid=64079
                            libpq_status=READY txn_status=IDLE [libpq attributes, no SQL]
group-1 error: class=psycopg2.errors.UndefinedTable sqlstate=42P01 message=relation "puzzles" does not exist
group-2 app-engine: id=0x10a2a3770 pool=Pool size: 5 … reset_engine_calls=0
group-2 failing-dbapi-connection: dbname_matches_app_engine=yes [a comparison, not a provenance]
group-3 process: pid=64053 hook_thread=MainThread alive_threads=['MainThread']
group-3 traceback: werkzeug_frames=['werkzeug/test.py:1162:get', …] frames=51
group-4 capture-connection: current_database=… current_schema=public search_path="$user", public backend_pid=64081
group-4 schema-now: to_regclass('public.puzzles')=None to_regclass('puzzles')=None pg_tables(puzzles)=[]
group-4 failing-backend-from-server: pid=64079 datname=… state=idle query=ROLLBACK [the server's own view]
group-4 verdict: MATCH
```

Right database (`MATCH`), table genuinely absent — **not** a wrong-place lookup.

### ⚑ A premise of this card is REFUTED, which is why it asked

Point 3 said these five "are the only ones in the suite that serve real HTTP **from a thread**… a fact
worth confirming rather than assuming." **It does not hold.** `alive_threads=['MainThread']` and the
werkzeug frames are `werkzeug/test.py` — Flask's **in-process test client on the main thread**, not
`werkzeug/serving.py`. (The helper reports the werkzeug *module path*, not the basename, precisely because
a bare `test.py` reads as ours.) One provoked instance is what that rests on.

### ⚑ And a hypothesis offered with evidence — which the orchestrator then REFUTED for the gate scenario

The agent proposed, from provoking the error rather than from looking for a cause: the five fail
deterministically when `DATABASE_URL` names an **existing but unmigrated** database; the table is
genuinely absent from the right database at `reset_engine_calls=0`; after one schema build the file is
52/52 green; and — by grep over `tests/test_*.py` in sort order — nothing before `test_admin_binding.py`
builds the schema. It named its own gap: *that the gates' actual collection order matches file sort
order*, which it could not test without a full-suite run.

**I tested that gap with `--collect-only`, which runs no tests, and the gap is where it fails.**

- **Collection order is not file sort order.** Subdirectories come first: of 211 collected files,
  `tests/e2e/…` and `tests/property/…` occupy positions 1–31 and **`test_admin_binding.py` is position 32.**
- **The very first file collected builds the schema.** `tests/e2e/test_admin_workflow.py` has **18 test
  functions taking `client` as a parameter** — verified by AST, not by grep, because a word-boundary grep
  over the other four candidates matched prose and the AST check cleared them.
- **And `client` → `app` → `db_session` → `request.getfixturevalue("_test_database_tables")` → `alembic
  upgrade head`**, session-scoped. So in a full-suite gate run the schema **is** built, by position 1,
  long before position 32.

So the mechanical account is **correct for the agent's reproduction and wrong for the gate**: it
reproduced the signature in a scenario the gate does not have (one file, in isolation, against an
unmigrated database). The agent was right to call it a hypothesis and right not to act on it (G-5).

**What this leaves is sharper than what we had.** In a gate run the schema *was* built before those five,
so the next occurrence is either (a) a schema built and then lost, (b) a connection that cannot see it —
wrong database or wrong `search_path` — or (c) a session-scoped fixture torn down and rebuilt mid-run.
**Those three are exactly what `to_regclass` + `current_database` + `pg_stat_activity` + the verdict line
now distinguish, on the first occurrence, for free.** The card did its job and did not need the
hypothesis to be right.

### `src/nonogram/db/session.py` — needed, and G-1 proved mechanically

An engine's `id()` cannot distinguish *fresh because `reset_engine()` ran* from *never built*, so the
counter is the datum. Added `_reset_count`, incremented in `reset_engine()`, plus read-only
`reset_count()`, documented as counting **calls** not disposals. G-1 is not asserted but walked:
`test_nothing_in_src_calls_the_reset_counter` parses every `*.py` under `src/` by AST for a `Call` whose
callee is `reset_count` and asserts the list empty. **M11** (a caller added inside `session.py`) reds it;
**M10** (the increment removed) reds the engine-group test. `tests/test_db_engine_lifecycle.py` —
including CARD-257's convention-text and globals-counting tests, which read this module's AST — is green.

### Declared bounds, not closed

1. **It does not name the engine the failing connection came from** — the exception carries a DBAPI
   connection and nothing naming an engine. Group 2 prints `dbname_matches_app_engine=yes/no`, labelled a
   comparison, not a provenance.
2. **It does not report the failing connection's own `search_path`** — that needs a query and only the
   unusable connection could answer. `pg_stat_activity` is asked about the failing *backend* instead,
   which gives its database from the server's side.
3. **The detector's sqlstate arm has no real reach today** — no psycopg2 error takes it without also
   matching the class arm. Exercised only by a fabrication; it exists for a non-psycopg2 driver. Declared
   in the docstring, not claimed as coverage.
4. **A lazy-import warning would break the byte comparisons** — left open deliberately (M13).
5. **The sixth gate variant is out of reach** — `uuid.UUID(hex=<float>)` is a different class and the hook
   is silent for it, by design.
6. **An error dying inside a werkzeug server thread without propagating is invisible** — the hook only
   sees what reaches pytest.
7. **AC-4's skip-profile half is measured on the AC-4 selection only**, plus the structural argument that
   the plugin implements one hook and it is not a collection or setup hook (M1 reds it).
8. **The matrix is ANY-RED per test node, not per assertion** — 48 assertion nodes is the denominator, and
   it does **not** claim all 48 are reached. *Exactly the domain discipline wave 50 promoted, applied
   unprompted.*

### Orchestrator note — my own `-qq` slip, for the record

My first collection-order command passed `-q` on top of `pyproject.toml`'s `addopts = "-q"`, making `-qq`,
which collapsed the listing to 227 lines and returned **zero** matches — so my first reading was that
nothing collected at all. That is the trap recorded on CARD-250 and restated in four briefs this wave, and
I walked into it while verifying someone else's claim. Cost: one command.
