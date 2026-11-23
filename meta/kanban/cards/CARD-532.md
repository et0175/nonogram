# CARD-532: Test prose stops stating the retired 4.8 mm cell floor as current

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/532-retired-floor-prose
**Worktree:** ../PythonProject4-card-532
**Source:** roadmap wave 15, cut 2026-11-23 on the owner's "pick the next no-decision wave from the backlog". IDEA-173.
**Idea:** IDEA-173
**Wave:** 94
**Created wave:** 94
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/ (docstrings and comments in the files listed below)
**UI surface:** —
**Review score:** —
**Started:** 2026-11-23T17:51Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

NFR-008's amendment of 2026-10-17 lowered the printed-cell floor from 4.8 mm to 4.75 mm (`book_manager.py`'s floor comment, CARD-121; `MIN_CELL_MM`). Re-checked on main at the cut: `git grep -n "4.8 mm" -- tests` gives 15 lines in 13 files. Some are correct history ("the retired 4.8 mm floor", "lowered the floor from 4.8 mm to 4.75 mm"). Others state 4.8 mm as the floor in force, for example `test_book_ready_gate.py` ("against the 4.8 mm floor (INV-006)"), `test_layout_page_spec.py` ("above the 4.8 mm floor") and `test_book_published_confirm.py` ("misses the 4.8 mm floor"). A reader then reasons from the wrong number.

## What to implement

1. Classify every `4.8 mm` line in `tests/` as history (true as written) or a present-tense claim. Record the table in `## Worktree notes`.
2. Rewrite each present-tense claim to name the floor in force. Name it by its source (`MIN_CELL_MM` / INV-006), or say 4.75 mm, whichever the surrounding prose already does. Leave history lines alone.
3. Where the prose describes a fixture's relation to the floor ("misses", "clears", "far above"), measure that fixture's printed cell against 4.75 mm and record the figure. If the claim is false at 4.75 mm (for example, a "misses the floor" fixture printing between 4.75 and 4.8 mm), stop and report it rather than fix it. That would be a test that no longer tests what it says, and it needs its own card.
4. Prose only: no assertion, fixture or test name changes. Net tests 0.

## Acceptance criteria

- AC-1: every remaining `4.8 mm` in `tests/` is history, and the worktree notes' table shows it.
- AC-2: every fixture-versus-floor sentence touched has its measured cell size recorded, and is true at 4.75 mm.
- AC-3: `git diff` touches comments and docstrings only. The touched files pass, and the collected test ids are unchanged.

## Worktree notes

### Premise, re-checked in the worktree (2026-11-23)

`git grep -n "4\.8 mm" -- tests` before the change: 15 lines in 13 files, as the card says. The floor in force is `FLOOR_MM = 4.75` in `nonogram.admin.book_page_spec` (imported by `book_manager`, whose `add_puzzles_to_book` refuses `cell_mm < FLOOR_MM`). Note: `MIN_CELL_MM` (named in the card's item 2) is `nonogram.export.layout`'s 2.0 mm page-fit floor, not the book floor; the rewrites name 4.75 mm (the figure the surrounding prose already used) or the registry's own wording, never `MIN_CELL_MM`.

### Item 1: classification of every `4.8 mm` line (before the change)

| File (function / class) | Kind | Action |
|---|---|---|
| property/test_book_layout.py (module docstring, "How the MIN_CELL_MM floor interacts") | present tense | rewritten to 4.75 mm |
| property/test_book_membership_floor.py (module docstring, EC-021) | present tense | rewritten to the registry's EC-021 wording, "the cell floor (TERM-024, NFR-008)" |
| test_book_cell_size.py (`RETIRED_FLOOR_MM` comment) | history | left |
| test_book_cell_size.py (`TestBookCell_ThirtyByThirtyDepthTenHoldsTheAmendedFloor`, 2 lines) | history | left |
| test_book_interior_type_floor.py (module docstring, "was 4.8 mm before it") | history | left |
| test_book_finalise_gutter.py (`book` docstring) | present tense | rewritten to 4.75 mm |
| test_book_published_confirm.py (`below_the_floor`) | present tense + fixture claim | rewritten to 4.75 mm |
| test_book_ready_gate.py (stub-records docstring, CARD-121 paragraph) | present tense + fixture claim | rewritten to 4.75 mm |
| test_book_trim_persistence.py (`_comfortable_puzzle`) | present tense + fixture claim | **STOPPED, not changed** (claim false at 4.75 mm, see item 3) |
| test_book_workflow_steps.py (`Shelf`) | present tense + fixture claim | rewritten to 4.75 mm |
| test_books_list_mobile.py (`_member`) | present tense | rewritten to 4.75 mm |
| test_books_list_plan_stats.py (`Shelf`) | present tense + fixture claim | rewritten to 4.75 mm |
| test_layout_page_spec.py (`TestBookCell_ThirtyByThirtyNineDeepAboveFloor`) | present tense + fixture claim | rewritten to 4.75 mm |
| test_puzzle_review_bulk_read.py (`seed`) | present tense + fixture claim | rewritten to 4.75 mm |

After the change: 5 lines in 3 files remain. Four are history (test_book_cell_size.py x3, test_book_interior_type_floor.py x1). The fifth is `_comfortable_puzzle`'s, left on purpose (item 3).

### Item 3: fixture cells, measured with `book_cell_sizes(book_page_spec(book), ...)` (the floor check's own call)

Script: /private/tmp/claude-501/card532/measure.py (scratch, not in the repo).

| Fixture | Trim | Cell (mm) | Claim at 4.75 mm |
|---|---|---|---|
| one-cell clue pair (`[[1]]`/`[[1]]`): ready_gate, workflow_steps, plan_stats, bulk_read | Book 1 default | 7.5 (the cap) | "far/well above": true |
| same | KDP minimum 10 x 10 cm | 7.5 | true |
| `BELOW_FLOOR` (30x25, 12-deep rows), published_confirm | Book 1 default | 4.5357 | "misses": true |
| AC-238 30x30 9-deep, test_layout_page_spec's own `BOOK1_ODD` spec | (test spec) | 4.9660 | "above": true |
| same shape via production `book_cell_mm` | Book 1 default | 4.8846 | above: true |
| `_comfortable_puzzle` (10x10, depth-1 clues), trim_persistence | Book 1 default / 6x9 in / 30x48 cm | 7.5 / 7.5 / 7.5 | true |
| same | **any trim 10.0 cm tall** (e.g. 10 x 10 cm) | **4.7442** | **"clears the floor on any supported trim": FALSE** |

`finalise_gutter`'s "has passed the floor" is not a figure claim: the members go through `add_puzzles_to_book`, which refuses any puzzle below the floor, so the sentence holds by construction.

Side fix in the same docstring: `below_the_floor` said `BELOW_FLOOR`'s cell is "4.61 mm ... measured there"; test_book_floor.py's `BELOW_FLOOR` records 4.54 (measured above: 4.5357). Changed to 4.54. (4.61 is test_layout_page_spec's AC-239 figure on its own older-margin spec.)

### STOPPED: `_comfortable_puzzle` (test_book_trim_persistence.py)

Its docstring says it "clears the 4.8 mm floor on any supported trim". At the KDP minimum height (10.0 cm, any width, Book 1 margins) its cell is 4.7442 mm: below 4.75 mm as well as 4.8 mm. The tests that use it add it to a book on the Book 1 trim (7.5 mm), so they still pass; the prose overstates the fixture. Not changed here, per item 3: it needs its own card (fix the wording to "on the trims this file uses", or pick a fixture that does clear the floor everywhere).

### Out of scope, recorded: `4.8` as code, not prose

Three numeric literals still use 4.8 as a threshold: `property/test_book_layout.py` (`below_book_floor += page.cell_mm < 4.8`), `property/test_book_pdf_geometry.py` (`below_book_floor += expected_cell < 4.8`), and `test_layout_page_spec.py`'s `TestBookCell_ThirtyByThirtyNineDeepAboveFloor` (`assert cell >= 4.8`). They are assertions/counters, which this card may not change. The last one is still true (4.966 >= 4.8) and stricter than the floor; the two counters count cells below 4.8 rather than 4.75, which still exercises the regime their comments describe. A later card may want them to read `FLOOR_MM`.

### Item 4 / AC-3: controls

- Collected ids over the 10 touched files: 638 before, 638 after, `diff` of the id lists empty.
- AST: each touched file's AST with module/class/function docstrings stripped is equal before and after (10/10); the full ASTs differ (10/10), so the check sees the change. Control: the same check on a scratch copy of `property/test_book_layout.py` with `< 4.8` changed to `< 4.75` reports `stripped-equal: False`. Every changed line is inside a docstring (no comments changed).
- Net collected tests: 10713 before, 10713 after (net 0).

### Gate (unarmed, `-o addopts= -rfs`)

The 10 touched files plus neighbours test_book_floor.py, test_book_trim_persistence.py, test_book_cell_size.py: 890 passed, 0 failed, 0 skipped.
