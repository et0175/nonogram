# CARD-097: A Postgres connection with no timeout hangs the suite whenever Postgres.app is waiting on its permission dialog

**Status:** done
**Priority:** P2
**Category:** bugfix
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** red -> green -> mutation check (6 mutants, 5 caught, 1 near-equivalent)
**Branch:** card/097-suite-stall-in-regrade-route
**Worktree:** ../PythonProject4-CARD-097
**Source:** owner — "open a card for the Postgres hang" (observed during CARD-079, 2026-09-17)
**Idea:** —
**Wave:** 1
**Depends on:** —
**Touches:** tests/conftest.py (the DB fixtures and the `db_required` skip hook), tests/test_admin_regrade.py (the `TestRegradeRoute_PreviewsBeforeItWrites` fixture), possibly src/nonogram/db/session.py — none of it decided, because the cause is not known yet
**Review score:** — _(merged without a review cycle, at the owner's call)_
**Started:** 2026-09-18
**Closed:** 2026-09-18
**Actual:** 0.5d
**Merge commit:** —
**Blocked by:** —

## Why

_(Written 2026-09-17, before the cause was known — kept as the record of what
it looked like from outside. The **Diagnosed** section above supersedes its
conclusion.)_

One full-suite run on 2026-09-17 stalled and never finished. It was killed
after ~11 minutes. **It has not reproduced since**, and the first diagnosis —
"a local Postgres being up hangs the suite" — is **wrong**: two later full runs
with the same Postgres listening completed normally. This card exists because
a suite that stalls once will stall again, and the next person to meet it
should start from the evidence rather than from scratch.

## Diagnosed 2026-09-18 — the cause, found while running CARD-072

**It is not a lock, a leaked session or a slow query. The process is blocked
making the connection, and the connection can never complete.**

Caught in the act during a CARD-072 suite run, with `sample` on the live
process:

```
psyco_connect  (in _psycopg...)
  connection_init
    conn_connect        <- the main thread, parked here, 0% CPU
```

And the server's side of the same attempt, from `psql`:

```
FATAL:  Postgres.app failed to verify "trust" authentication
DETAIL: You did not confirm the permission dialog.
```

**Postgres.app (18) shows a macOS permission dialog on connection.** Until
somebody clicks it, the TCP socket is `ESTABLISHED` — which is why `lsof`
showed a live connection — but authentication never finishes. Nothing in this
project sets `connect_timeout`, and libpq's default is *wait forever*, so the
test that opened it waits forever too.

That explains every observation on this card, including the ones that made it
look intermittent:

- **0% CPU over eleven minutes** — blocked in `connect`, not computing.
- **An ESTABLISHED connection with no query running** — connected, unauthenticated.
- **Not reproducible in short runs** — the dialog is per app session and per
  user action. Runs after it is confirmed (or where nothing connects) are
  normal; the "114 s with Postgres listening" measurement was such a run.
- **The test it stops is arbitrary** — whichever one first opens a connection.
  It appeared in `test_admin_regrade.py` on 2026-09-17 and in CARD-072's new
  `create_app()` test on 2026-09-18, which is also why that test now clears
  `DATABASE_URL` explicitly.
- **`db_required` tests still "skip"** — the skip hook's `SELECT 1` is what
  hangs, so the skip it was written to produce never arrives.

## What to implement (revised by the diagnosis)

1. **Give every connection attempt a deadline.** `create_engine(...,
   connect_args={"connect_timeout": N})` in `db/session.py` turns "hang
   forever" into an error the existing skip hook already handles. This is the
   fix; the rest is hygiene.
2. **Make the skip hook honest.** `pytest_runtest_setup` exists to skip DB
   tests when the database is unreachable — with no timeout it cannot, because
   unreachable and unanswered look the same. With item 1 it works as written.
3. **Then the diagnosability work below** is still worth doing, but it is no
   longer the way this bug gets found.

**For the owner, separately from the code:** confirming Postgres.app's
permission dialog once, or quitting Postgres.app, removes the symptom today.
The card is about the tool not hanging when it happens again.

## What was observed, exactly

At the time of the stall (`ps`, `sample`, `lsof` on the live process):

- The run had been going ~11 minutes and had used **~77 s of CPU** — so it was
  waiting, not computing.
- The active test was
  `tests/test_admin_regrade.py::TestRegradeRoute_PreviewsBeforeItWrites::test_post_applies_the_run_the_preview_described`
  (its `route.db` was open on fd 12).
- The process also held an **ESTABLISHED TCP connection to
  `localhost:postgresql`** — which is what sent the first diagnosis down the
  Postgres path.
- `sample` showed the stack deep in `_PyEval_EvalFrameDefault` with no syscall
  wait visible, which fits a Python-level wait/retry loop rather than a blocked
  read.

## What has been ruled out since

| checked | result |
|---|---|
| That test file alone, on `main` | 70 passed in **1.5 s** |
| That test file alone, on the CARD-079 branch | 70 passed in **0.76 s** |
| `tests/test_db_e2e_smoke.py` + `tests/test_admin_regrade.py` together | 76 passed in **3.3 s**, 6 skipped |
| Full suite, Postgres **unreachable** (`TEST_DATABASE_URL` → dead port) | 3,451 passed in **94–97 s** |
| Full suite, Postgres **listening** (verbose) | 3,451 passed in **190 s** |
| Full suite, Postgres **listening** (quiet, like-for-like) | 3,451 passed in **114 s** |
| Stale engine bound to the wrong URL | **Not possible** — `db/session.py` rebuilds when `DATABASE_URL` changes |
| The re-grade route running against a real database | **No** — that fixture points `DATABASE_URL` at a two-row sqlite file in `tmp_path` |

So: not deterministic, not that test on its own, not the DB smoke tests, not a
stale engine, and not Postgres merely being up.

**Where the Postgres connection comes from is still unexplained**, and it is
the most interesting thread. `db_required` tests skip because
`pytest_runtest_setup` asks `nonogram.db.engine` *before* fixtures run, when
`DATABASE_URL` is unset — so they skip whether or not Postgres is up (26
skipped in every run above). Something else in the session therefore opened
that connection. Finding what, and whether it is ever closed, is step 1.

## What to implement

1. **Make the next stall diagnosable instead of fatal.** Today a stalled run
   has to be caught by hand with `ps`/`sample`. **Decided 2026-09-18, by the
   owner: `faulthandler`, not `pytest-timeout`** — armed before each test and
   cancelled after, in `tests/conftest.py`. It is stdlib, so ADR-0006/R1's
   baseline does not move for a debugging convenience, and it dumps *every*
   thread's stack rather than only the one pytest is watching. The cost is
   about ten lines of hook and a per-test wall-clock bound that has to be
   generous enough for the slowest honest test (the corpus property tests run
   into the tens of seconds), which is worth stating in the notes.
2. **Account for the Postgres connection.** Find what opens it, whether it is
   closed, and whether a test can leave a session open across tests. A leaked
   connection is worth fixing on its own merits even if it is not the cause.
3. **Only then look for the stall itself**, with the evidence above as the
   starting point rather than a fresh bisect.

## Acceptance criteria

- **AC-0** *(added by the diagnosis, and the one that matters)* — with
  Postgres listening but not answering (Postgres.app awaiting its permission
  dialog, or any equivalent), the suite **finishes**: the connection attempt
  fails inside the configured timeout and the `db_required` tests skip as they
  were designed to.
  *test:* an engine built against a black-hole address fails fast rather than
  blocking — e.g. a listening socket that never replies
- **AC-1** — a test that hangs is reported as a failure with a stack, not as a
  run that never ends: with a deliberately hanging test injected, the suite
  fails within the configured limit and names the test.
  *test:* whichever mechanism item 1 chooses, exercised on an injected hang
- **AC-2** — the Postgres connection observed during the stall is accounted
  for: either no full-suite run opens one (shown by checking the process's
  sockets during a run), or the test that opens it closes it, and that is
  asserted.
- **AC-3** *(already measured while writing this card, 2026-09-17)* — the
  suite's wall-clock with Postgres listening and with it unreachable:
  **114 s against 94–97 s**, quiet both times, same deselections. So a
  listening Postgres costs roughly 17% and nothing like a stall. The earlier
  190 s figure was a verbose run and is not comparable. Re-take these if the
  machine or the corpus changes; do not quote the 190 s.

## Guardrails

- G-1: **No test may re-grade, drop, truncate or write to a database that is
  not a throwaway created by that test** (CARD-077 G-1: never run the re-grade
  against the live DB). The existing `db_session` fixture does
  `DROP TABLE ... CASCADE` against whatever `TEST_DATABASE_URL` names — if this
  card touches that fixture, it must not widen what it can reach.
- G-2: The fix is **not** "skip or deselect the test". A stall that is hidden
  is a stall that returns.
- G-3: `nonogram_admin.db` and the owner's `pictures/`, `pic1/` are untouched.
- G-4: Adding `pytest-timeout` (or any package) is a dependency-baseline
  decision — ADR-0006/R1 — and needs the owner's word, not just a passing
  suite.
- G-5: Commit only your own files — explicit pathspecs.

## System contract

- ADR-0006/R1 — dependency baseline: stdlib + Pillow + NumPy + reportlab, with
  pytest as the dev extra; a new dev dependency is still a change to it
  (check: review-lens)
- CARD-077 G-1 — the re-grade never runs against a live database
  (check: the fixture's `DATABASE_URL` points inside `tmp_path`)

## Architecture context

- **FR:** — (test-infrastructure card; no requirement changes)
- **ADR:** ADR-0006 (if a dependency is added)
- **Components:** the test tree; possibly COMP-002's admin layer
- **Trace:** none — this card adds no criteria to the model

## Worktree notes

### Delivered 2026-09-18

**The fix (AC-0).** `db/session.py` gains `CONNECT_TIMEOUT_SECONDS = 10`, passed
as libpq's `connect_timeout` — and **only for PostgreSQL URLs**, since SQLite's
driver has no such keyword and would raise `TypeError` on every legacy and test
path. `session.py` is the only place in `src/` that builds an engine, so one
change covers everything.

**The skip hook, made honest (AC-2).** It now asks a session-cached probe
instead of connecting per test. That mattered more than expected — see below.

**The net (AC-1).** `tests/hang_guard.py`: `faulthandler.dump_traceback_later`
armed before each test and cancelled after, 120 s, overridable with
`NONOGRAM_TEST_HANG_SECONDS`. The owner chose stdlib over `pytest-timeout`, so
ADR-0006/R1's baseline does not move.

### Measured, before and after (AC-3)

| full suite | before this card | after |
|---|---|---|
| Postgres unreachable | 94–97 s | ~95 s (unchanged) |
| **Postgres listening but not answering** | **never finished** | **2 m 08 s** |
| Postgres answering normally | 114 s | ~120 s |

### Two things the fix uncovered, both fixed here

1. **The deadline alone made the suite take eight and a half minutes.** With a
   database that listens and never answers, every fixture wanting one paid the
   full 10 s — ~25 `test_wave3_*` tests paid it *twice each* in setup, and the
   run took **8 m 24 s** to report the same 26 skips a 95-second run reports.
   Trading an infinite hang for eight minutes is a poor fix. The reachability
   verdict is now taken **once per URL per session**
   (`conftest._unreachable_reason`), which is what brings it to 2 m 08 s. The
   cost is now one deadline for the whole run, which is the least it can be.

2. **The stack dump was invisible — twice.** pytest captures at the
   file-descriptor level, so a dump written to fd 2 during a test lands in a
   buffer that is discarded when the process is killed a moment later. The
   first version printed nothing. Duplicating fd 2 at import time fixes that
   *only* if the module is imported before capture is installed — true under
   `-p tests.hang_guard`, false when `tests/conftest.py` imports it, so the
   second version printed nothing either, and I only noticed because a mutant
   run ended in silence at exactly the 20 s bound. The dump now goes to a
   **file** (`$TMPDIR/nonogram-test-hang.txt`, or `NONOGRAM_TEST_HANG_DUMP`),
   whose path is announced in the run header. A file has no ordering problem.

   Worth stating plainly: a safety net that is silent is not a safety net, and
   this one was silent in exactly the situation it exists for.

### Tests

`tests/test_db_connect_timeout.py`, 5 tests. The fixture is a socket that
listens and never accepts — the kernel completes the handshake from the
backlog, so `connect` succeeds and the first read waits forever, which is what
a Postgres blocked on a permission dialog looks like from the client side. No
Postgres needed to reproduce the bug.

Mutation check — six mutants, restored from saved copies:

| mutant | caught by |
|---|---|
| connection deadline removed | the black-hole test (the run is killed by the guard at its bound — which is the guard proving itself) |
| deadline applied to every scheme, SQLite included | `..._a_sqlite_url_is_not_given_a_postgres_connect_option` |
| reachability verdict not cached | `..._the_reachability_verdict_is_taken_once_per_url` |
| dump written to captured stderr | `..._a_hanging_test_is_killed_and_its_stack_printed` |
| header announcement removed | `..._a_run_says_where_a_hang_dump_would_go` |
| timer never cancelled after a test | **survived — near-equivalent**: arming resets the timer each test, so the only difference is an alarm left armed through session teardown. Cancelling is hygiene; a test for it would have to make teardown outlast the bound, which is contrived. Recorded rather than faked. |

**Full suite: 3,473 passed, 0 failed** — with Postgres listening, which is the
configuration that could not finish at all before this card.

### For the owner

The machine-level symptom is Postgres.app's permission dialog. Confirming it
once, or quitting Postgres.app, removes it. Nothing here depends on that: the
suite now finishes either way, which was the point.
