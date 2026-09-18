# CARD-097: A Postgres connection with no timeout hangs the suite whenever Postgres.app is waiting on its permission dialog

**Status:** ready
**Priority:** P2
**Category:** bugfix
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/097-suite-stall-in-regrade-route
**Worktree:** —
**Source:** owner — "open a card for the Postgres hang" (observed during CARD-079, 2026-09-17)
**Idea:** —
**Wave:** 1
**Depends on:** —
**Touches:** tests/conftest.py (the DB fixtures and the `db_required` skip hook), tests/test_admin_regrade.py (the `TestRegradeRoute_PreviewsBeforeItWrites` fixture), possibly src/nonogram/db/session.py — none of it decided, because the cause is not known yet
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
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
   has to be caught by hand with `ps`/`sample`. A per-test timeout that dumps
   the stack would turn an eleven-minute mystery into a failure with a
   traceback. `pytest-timeout` is the obvious tool and is **not in the
   dependency baseline** (ADR-0006/R1, dev extra) — adding it is a decision to
   take deliberately, not a side effect of this card. The alternative with no
   new dependency is a `faulthandler.dump_traceback_later()` call in
   `conftest.py`, which needs no package and prints every thread's stack.
   **Decide which, and say why, in the card's notes.**
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

—
