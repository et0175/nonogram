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

Each file keeps its expectations independent of the code it checks: `test_layout_page_spec.py` says "`export` tests never import `nonogram.admin`", `test_book_layout.py` imports no `nonogram.admin` module, and `test_book_pdf_geometry.py` says "Nothing here imports `compute_layout`, `PageSpec` or `book_page_spec`" (it does import `book_manager`, `book_pdf_generator` and `book_vector` to render the PDF). `FLOOR_MM` lives in `book_page_spec`, so none of the three may read it. Owner ruling 2026-11-24: keep that rule.

## What to implement

1. Define the floor once in the test tree as a named literal, `BOOK_FLOOR_MM = 4.75`, with a comment naming NFR-008 and `FLOOR_MM`. Put it in a `tests/helpers/` module that does not import `nonogram.admin` (an existing one if one fits; otherwise a small new one).
2. The four comparisons above read `BOOK_FLOOR_MM`. Each file's "never imports `nonogram.admin`" statement stays true.
3. Add one assert to an existing test that already imports `FLOOR_MM` (the card first named `tests/property/test_book_membership_floor.py`; see the notes for where it went): `BOOK_FLOOR_MM == FLOOR_MM`. A future floor change then fails there instead of drifting.
4. Measure both counters at 4.8 and at 4.75 on the fixed seeds, and record the four figures. If a count falls below its own minimum (100, 20), stop and report it. Do not lower the minimum.
5. Net tests 0.

## Acceptance criteria

- AC-1: `git grep -nE "< ?4\.8\b|>= ?4\.8\b" -- tests` finds none of the four comparisons, and each reads `BOOK_FLOOR_MM`.
- AC-2: No file gains an import its own rule forbids: `test_layout_page_spec.py` and `test_book_layout.py` import no `nonogram.admin` module, `test_book_pdf_geometry.py` imports neither `book_page_spec` nor `compute_layout`/`PageSpec`, and the helper imports nothing. Check this with an `ast` walk, not grep.
- AC-3: The cross-check assert fails when `BOOK_FLOOR_MM` is set to 4.8, and passes at 4.75.
- AC-4: The two counters' figures at 4.8 and at 4.75 are recorded, and both counters still meet their minimums.
- AC-5: Net tests 0.

## Worktree notes

**Implementation (orchestrator).** `tests/helpers/book_floor.py` holds `BOOK_FLOOR_MM = 4.75` and imports nothing. The four comparisons read it: `test_book_layout.py` (EC-019 counter), `test_book_pdf_geometry.py` (EC-019 PDF counter), and both `test_layout_page_spec.py` asserts. The cross-check went into `tests/test_book_floor.py::TestBookAddPuzzles_AcceptsCellJustAboveFloor::test_the_two_fixtures_sit_either_side_of_the_floor`, not the membership property the card first named: that test already imports `FLOOR_MM`, is about exactly where the floor sits, and runs in about a second.
- Card correction: the Why first said all three files never import `nonogram.admin`. An `ast` walk shows `test_book_pdf_geometry.py` imports `book_manager`, `book_pdf_generator` and `book_vector`; its own rule excludes only `book_page_spec`, `compute_layout` and `PageSpec`. Why and AC-2 now say so.
- AC-1: `git grep -nE "(<|>=) ?4\.8\b"` over the three files finds nothing.
- AC-2 (`ast`): helper imports nothing. `test_layout_page_spec.py` and `test_book_layout.py`: no `nonogram.admin` module. `test_book_pdf_geometry.py`: `nonogram.admin.book_manager`, `.book_pdf_generator`, `.book_vector` (all on main before this card), no `book_page_spec`.
- AC-3: with `BOOK_FLOOR_MM = 4.8` the cross-check fails (`AssertionError: (4.8, 4.75)`); at 4.75 it passes. That test plus `tests/test_layout_page_spec.py`: 113 passed.
- AC-4, measured by a temporary print, removed: the layout counter is 506 at 4.8 and 494 at 4.75, out of 1485 checked (minimum 100). The PDF counter is 127 at 4.8 and 126 at 4.75, out of 216 checked (minimum 20). So 12 layout cases and 1 PDF case print between 4.75 and 4.8 mm and were counted as below the floor. Both minimums still hold by a wide margin.
- AC-5: no test added or removed (net 0).
