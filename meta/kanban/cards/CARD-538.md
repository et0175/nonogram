# CARD-538: The CARD-150 admin-local script-test minors, verified first and fixed only where still live

**Status:** ready
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** —
**Worktree:** —
**Source:** roadmap wave 17, cut 2026-11-24 on the owner's "pick the next no-decision wave from the backlog". IDEA-018.
**Idea:** IDEA-018
**Wave:** 96
**Created wave:** 96
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/test_admin_local_cost.py, tests/helpers/admin_script_stubs.py, tests/test_start_admin_local.py
**UI surface:** —
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

CARD-150's review left four minors (F-003/F-004/F-005/F-007): a "14 of 18" figure that is an artifact of `--check-only` not existing on the old script; the README tests' `returncode != 0` precondition is met by any failure; the two Docker branches match on database name only, dropping host, port and credentials, with no runtime coverage; and nothing asserts G-3's launch target although the stub logs it. Re-checked on main at the cut: the script tests were restructured since (CARD-236, CARD-492: `tests/helpers/admin_script_stubs.py`), and `tests/test_admin_local_cost.py` now asserts `[c["dbname"] for c in connections(run)] == [url]` beside several `run.returncode != 0` asserts. So some items may be moot.

## What to implement

1. Verify first. For each of the four, find where the claim now lives (grep the three files named in Touches) and record live or moot. For F-004 and F-005, run a mutant: make the script fail for an unrelated reason, or connect to the right database name on the wrong host, and see whether a test notices.
2. Fix only the live ones, by tightening an existing assert (for example matching the failure's message, or comparing the full connection target, not the database name).
3. F-003 is a figure in prose. If it still appears, correct it to what a run measures today, or delete it.

## Acceptance criteria

- AC-1: each item has a recorded verdict, live or moot, backed by a run (a mutant, a probe or a test), never by reading code alone. Record the command and its result in `## Worktree notes`.
- AC-2: every live item is fixed, and its fix has one control that fails when the fix is reverted.
- AC-3: owner's test budget: change existing tests rather than add; net test count at most +1; report it.

## Worktree notes
