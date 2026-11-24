# CARD-535: The three below-floor test thresholds count against the 4.75 mm floor, not 4.8

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/535-floor-thresholds
**Worktree:** ../PythonProject4-card-535
**Source:** CARD-532 review F-004 (wave 15, recorded, not carded); carded 2026-11-24 on the owner's "card the three 4.8 thresholds to read FLOOR_MM". Owner ruling the same day: keep each file's import rule, use a test-side 4.75 literal cross-checked against `FLOOR_MM`.
**Idea:** —
**Wave:** 95
**Created wave:** 95
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/property/test_book_layout.py, tests/property/test_book_pdf_geometry.py, tests/test_layout_page_spec.py, tests/property/test_book_membership_floor.py, one module under tests/helpers/
**UI surface:** —
**Review score:** —
**Started:** 2026-11-24T05:42Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

NFR-008's printed-cell floor is 4.75 mm (`FLOOR_MM` in `nonogram.admin.book_page_spec`). CARD-532 fixed the test prose; three test thresholds still use 4.8:

- `tests/property/test_book_layout.py`, the EC-019 property: `below_book_floor += page.cell_mm < 4.8`, then `assert below_book_floor >= 100`.
- `tests/property/test_book_pdf_geometry.py`, the EC-019 PDF half: `below_book_floor += expected_cell < 4.8`, then `assert below_book_floor >= 20`.
- `tests/test_layout_page_spec.py`: `assert cell >= 4.8` in `TestBookCell_ThirtyByThirtyNineDeepAboveFloor` and `assert cell < 4.8` in `TestBookCell_TwelveDeepBandFallsBelowFloor`.

A cell between 4.75 and 4.8 mm is above the floor, but the two counters count it as below. The counters exist to prove the corpus exercises the below-floor regime, so they over-count it.

All three files state that they never import `nonogram.admin` (`test_book_pdf_geometry.py`: "Nothing here imports ... `book_page_spec`"; `test_layout_page_spec.py`: "`export` tests never import `nonogram.admin`"; `test_book_layout.py` imports only `nonogram.export.layout` and `nonogram.clues`). That keeps their expected numbers independent of the code under test. Owner ruling 2026-11-24: keep that rule.

## What to implement

1. Define the floor once in the test tree as a named literal, `BOOK_FLOOR_MM = 4.75`, with a comment naming NFR-008 and `FLOOR_MM`. Put it in a `tests/helpers/` module that does not import `nonogram.admin` (an existing one if one fits; otherwise a small new one).
2. The four comparisons above read `BOOK_FLOOR_MM`. Each file's "never imports `nonogram.admin`" statement stays true.
3. Add one assert to an existing test in `tests/property/test_book_membership_floor.py`, which already imports `FLOOR_MM`: `BOOK_FLOOR_MM == FLOOR_MM`. A future floor change then fails there instead of drifting.
4. Measure both counters at 4.8 and at 4.75 on the fixed seeds, and record the four figures. If a count falls below its own minimum (100, 20), stop and report it. Do not lower the minimum.
5. Net tests 0.

## Acceptance criteria

- AC-1: `git grep -nE "< ?4\.8\b|>= ?4\.8\b" -- tests` finds none of the four comparisons, and each reads `BOOK_FLOOR_MM`.
- AC-2: None of the three files imports `nonogram.admin`, directly or through the helper. Check this with an `ast` walk, not grep.
- AC-3: The cross-check assert fails when `BOOK_FLOOR_MM` is set to 4.8, and passes at 4.75.
- AC-4: The two counters' figures at 4.8 and at 4.75 are recorded, and both counters still meet their minimums.
- AC-5: Net tests 0.

## Worktree notes
