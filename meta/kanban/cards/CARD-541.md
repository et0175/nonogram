# CARD-541: The book detail page's print-number fallback for a repeated puzzle id, verified first and pinned only if live

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/541-repeated-id-number
**Worktree:** ../PythonProject4-card-541
**Source:** roadmap wave 18, cut 2026-11-24 on the owner's pick of "a small Wave 18" from the backlog's remaining no-decision items. IDEA-084.
**Idea:** IDEA-084
**Wave:** 97
**Created wave:** 97
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/test_book_detail_page.py
**UI surface:** —
**Review score:** —
**Started:** 2026-11-24T11:03Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

CARD-165's review left three minors (F-001/F-002/F-003). F-003: the stored-order fallback with a repeated id is untested (a mutant survived). F-001: the printed-number test reads the band only through the single-puzzle-page path, with no shared two-up fixture. Re-checked on main at the cut: the book detail view in `src/nonogram/admin/app.py` builds its rows from `book.puzzle_ids` as copies ("a repeated id is two rows here as it is two rows there; rows are matched back by identity"), and `tests/test_book_detail_page.py` has a CARD-165 section. Whether either minor is still live is not known. F-002 (the no-plan banner points to Finalise even when the cause is a code bug) is banner wording the owner decides, and is not in this card.

## What to implement

1. Verify first. F-003: write a mutant of the detail view's fallback that mishandles a repeated id (for example, matching rows back by puzzle id instead of by identity, or dropping the second copy) and run `tests/test_book_detail_page.py` against it. F-001: check whether any test reads a printed number from a two-up page; if none does, run a mutant that numbers two-up pages wrongly and see whether a test notices.
2. Fix only the live ones, by extending an existing test or its parametrize.
3. Leave the banner wording alone.

## Acceptance criteria

- AC-1: each in-scope item has a recorded verdict, live or moot, backed by a run (a mutant, a probe or a computed figure), never by reading code alone. Record the command and its result in `## Worktree notes`.
- AC-2: every live item is fixed, and a fix to a test or to code has one control that fails when the fix is reverted. A comment-only fix records the computed figure instead.
- AC-3: owner's test budget: change existing tests rather than add; net test count at most +1; report it.

## Worktree notes
