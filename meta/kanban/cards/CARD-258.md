# CARD-258: Make the next `relation "puzzles" does not exist` red say what it was talking to

**Status:** ready
**Priority:** P1
**Category:** ops
**Complexity:** standard
**Estimate:** 0.5d
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** CARD-256's build gates 1 and 2 (2026-10-20) — red then green on the same commit, on a tree carrying CARD-252's `reset_engine()`. The hazard survives the fix that was expected to remove it.
**Idea:** —
**Wave:** 51 (queued)
**Depends on:** —
**Touches:** tests/conftest.py, tests/test_admin_binding.py, tests/helpers/ (a new diagnostic helper), src/nonogram/db/session.py — only if a read-only accessor is needed
**Review score:** —
**Started:** — · **Closed:** — · **Actual:** — · **Merge commit:** —
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
