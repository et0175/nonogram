# CARD-540: The print-spec test's inch-to-centimetre comment states the product it computes

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/540-inch-comment
**Worktree:** ../PythonProject4-card-540
**Source:** roadmap wave 18, cut 2026-11-24 on the owner's pick of "a small Wave 18" from the backlog's remaining no-decision items. IDEA-104.
**Idea:** IDEA-104
**Wave:** 97
**Created wave:** 97
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/test_print_specs.py (one comment)
**UI surface:** —
**Review score:** —
**Started:** 2026-11-24T11:03Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

CARD-174's review (F-004) found a comment in `tests/test_print_specs.py` saying `18.8976 x 2.54 = 48.0`. The product is 47.999904; the assertion beside it is right. Re-checked on main at the cut: the comment above the inch-limit cases still reads "18.8976 x 2.54 = 48.0", beside "3.937 x 2.54 = 9.99998" and "11.811 x 2.54 = 29.99994", which are given to more places. IDEA-104's second half (the inch refusal says "on both sides" where the centimetre one says "in both dimensions") is wording the owner decides, and is not in this card.

## What to implement

1. Compute each product in that comment with `decimal` (exact), and record the three figures.
2. Correct any that the comment misstates, at the precision its neighbours use. No assertion or case changes.
3. Leave the "on both sides" wording alone; it is the owner's call.

## Acceptance criteria

- AC-1: each in-scope item has a recorded verdict, live or moot, backed by a run (a mutant, a probe or a computed figure), never by reading code alone. Record the command and its result in `## Worktree notes`.
- AC-2: every live item is fixed, and a fix to a test or to code has one control that fails when the fix is reverted. A comment-only fix records the computed figure instead.
- AC-3: owner's test budget: change existing tests rather than add; net test count at most +1; report it.

## Worktree notes

**Implementation (orchestrator).** The comment above `EXACT_BOUNDARY_INCHES` in `tests/test_print_specs.py`, computed exactly with `decimal`: 3.937 x 2.54 = 9.99998 (as written), 11.811 x 2.54 = 29.99994 (as written), 18.8976 x 2.54 = 47.999904 (written as 48.0: live, fixed to 47.999904, the precision its neighbours use). The same comment's "0.01 in beyond" figures also hold: 3.927 x 2.54 = 9.97458 (9.97), 11.821 x 2.54 = 30.02534 (30.03), 18.9076 x 2.54 = 48.025304 (48.03). Comment only: no assertion or case changed, net tests 0. The "on both sides" wording (IDEA-104's second half) is left for the owner.
