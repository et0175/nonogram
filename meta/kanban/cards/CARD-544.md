# CARD-544: A two-up page whose grids are swapped under their bands fails a test

**Status:** ready
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** —
**Worktree:** —
**Source:** roadmap wave 19, cut 2026-11-24 on the owner's "card both" (CARD-541 review F-001).
**Idea:** —
**Wave:** 98
**Created wave:** 98
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/test_book_pdf_two_up.py
**UI surface:** —
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

CARD-541's review (F-001) ran mutant R4: `vector_two_up_page` in `src/nonogram/admin/book_pdf_generator.py` zips `reversed(payloads)`, so each band keeps its "Puzzle N" number but sits over the other puzzle's grid. It survived `tests/test_book_detail_page.py` (39 passed), `tests/test_book_pdf_two_up.py` (53 passed) and the behavioural tests of seven more two-up-touching files (295 passed; the one red was the static call-count scan `test_the_callee_arm_defaults_to_deny_and_every_exemption_pays_its_cost`, not a behavioural catch). A printed book could therefore number its two-up puzzles over the wrong grids, and the solution pages would then point the reader at the wrong answer.

## What to implement

1. Verify first. Re-run mutant R4 on main against `tests/test_book_pdf_two_up.py` and record that it survives (or, if something now catches it, record which test and stop at AC-1).
2. If live, extend an existing test in `tests/test_book_pdf_two_up.py` (or its parametrize) so that it checks, for each slot of a two-up page, that the band's puzzle number sits above the grid of that same puzzle: use two puzzles whose drawn grids can be told apart (for example different sizes or different clues) and read the placement from the exported page itself, not from the arguments passed to a helper.
3. The fix is test-only. Do not change `vector_two_up_page` or any other source file.

## Acceptance criteria

- AC-1: the verdict on R4 is recorded in `## Worktree notes` with the command and result, backed by a run, never by reading code alone.
- AC-2: with the extended test, mutant R4 (reversed payloads) reds it, and a second mutant that swaps the two slots' geometry instead of their payloads reds it too; on the real code it is green. Record the three runs.
- AC-3: owner's test budget: change existing tests rather than add; net test count at most +1; report it.

## Worktree notes
