# CARD-485: A single-puzzle page leaves room for its footer, so every puzzle page keeps its centred folio

**Status:** in_progress
**Priority:** P1
**Category:** ops
**Estimate:** 2c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/485-single-page-footer-reserve
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-485
**Source:** owner 2026-11-19, on the downloaded "Christmas Nonograms" interior (prod DB): "Puzzle 140 - page number is in the corner, while other page numbers are in the middle, puzzles 114-115 have no folio, but it looks like we can make cell size a bit smaller." Owner: "yes, card it and start CARD-485".
**Idea:** —
**Wave:** 81
**Created wave:** 81
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/export/layout.py, src/nonogram/admin/book_page_spec.py, src/nonogram/admin/book_pdf_generator.py, tests/test_book_page_numbers.py, tests/property/test_book_pdf_geometry.py, tests/test_book_vector_goldens.py
**UI surface:** printed interior (single-puzzle pages)
**Review score:** —
**Started:** 2026-11-19T14:42Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

A puzzle that gets a page to itself is fitted by `compute_layout` to the **whole** usable box, down to the bottom margin. The footer strip (`INTERIOR_FOOTER_MM`, about 9.9 mm, 117 px at 300 dpi) is not reserved, so the footer group is drawn only when the grid happens to stop above `interior_frame(spec).footer_rule.y`. Otherwise `draw_sheet_furniture` falls back to the bottom-outer-corner folio, and when the grid also reaches that corner, to no folio at all. Two-up pages already reserve the strip (`compute_pair_layout`'s `footer_reserve_px`, CARD-248); single pages never did. CARD-392's owner intent was "the grid area now runs down to that line".

Measured 2026-11-19 by the orchestrator on the owner's book (160 puzzles, 21.59 x 27.94 cm, gutter 1.27, outside 0.95 cm), rebuilt from main against the prod DB read-only (byte-identical to the download apart from a trailing date):

* Puzzle 140 (18x24, column clues 7 deep): the grid ends 11 px below the footer rule, so the folio goes to the corner. Puzzle 139, the same size with 5-deep clues, fits.
* Puzzles 114 (17x30) and 115 (22x30): height-bound, they overrun by exactly 117 px, and the corner is covered too, so they print no folio.
* Simulated fix (bottom margin + `INTERIOR_FOOTER_MM` in the fit, frame unchanged): 12 of 80 grid sizes change, 29 puzzles, cells smaller by at most 4.1% (22x30 6.527 -> 6.26 mm; 18x24 7.5 -> 7.238 mm); smallest cell in the book unchanged at 4.967 mm; **0** single pages still overrun the footer rule.

## What to implement

1. A single-puzzle book page fits its grid above the footer rule, from the same figure the frame draws (`interior_frame` / `_puzzle_area_px`), never a second constant. The frame itself does not move.
2. The per-grid-size book cell (`book_cell_sizes`, NFR-008) is derived from that same fit, so every member of a grid size shares the smaller cell.
3. Two-up pages are unchanged in rule (they already reserve the strip). If the smaller book cells change any pairing decision or the page count, measure and report it on the owner's book; do not suppress it.

## Acceptance criteria

* **AC-1**: on the owner's book profile, every single-puzzle page draws the full footer group (rule, centred folio, label, pointer): `draw_sheet_furniture` returns True for every one. Pin with the measured shape of puzzle 140 (18x24, 7-deep column clues next to a 5-deep sibling) and a height-bound 22x30.
* **AC-2**: the grid's lowest drawn row is at or above the footer rule on every single page of a sweep over `MIN_SIZE..MAX_SIZE` grid sizes at the deepest clue depth the corpus helpers build.
* **AC-3**: cells shrink only where the footer did not fit before: a grid size whose page already cleared the footer keeps its cell exactly (state the count on Book 1 and on the owner's profile).
* **AC-4**: one control per AC-1 (put the old full-box fit back: it reds). Owner's test budget: change existing tests rather than add; net test count at most +2.
* **AC-5**: renders of the owner's pages (puzzles 114, 115, 139, 140 and one two-up page) before and after, in `~/Documents/nonogram-reviews/CARD-485/`, for the owner's visual check.

## Guardrails

* **G-1**: the footer's design (rule weight, gap, folio size, label, pointer) is unchanged; only the grid's fit moves.
* **G-2**: no change to the CLI/A4 path (no parity, no frame): byte-identical output.
* **G-3**: read-only against production. Any DB read uses a read-only transaction; nothing is migrated or written.
* **G-4**: CARD-483's F-5 (a lower border drawn on the footer rule when slack is under 4 px) is the owner's open decision: report whether this card changes it, do not decide it.

## Worktree notes

—
