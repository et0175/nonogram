# CARD-392: The one-line footer gives the grid its room — the footer band shrinks, and pairing and cell sizes are re-derived from the larger area

**Status:** in_progress
**Priority:** P2
**Category:** feature
**Estimate:** 4c (1.5d)
<!-- The arithmetic is small; the cost is the re-derivation of numbers the registry states (FR-040's 29..32-cell thresholds, AC-377's neighbours, the cell-size table) from first principles rather than by re-recording, plus the baselines. If the page-kind consequences (item 2) prove large, the split is: the band + puzzle pages here, the other kinds' re-measure in a follow-up. -->
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/392-one-line-footer
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-392
**Source:** owner decision 2026-11-07, version B: "A one-line footer, so grids get a little more room" and "The grid area now runs down to that line."
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** CARD-391
<!-- Recommended to land BEFORE CARD-232 (solution tiles), CARD-226 (two-up slots), CARD-229/230 (guide) and CARD-233: all of them measure against the frame's usable area, which this card changes. -->
**Touches:** src/nonogram/export/layout.py, src/nonogram/admin/book_page_spec.py, src/nonogram/admin/book_pdf_generator.py, src/nonogram/admin/book_kdp.py, tests/test_layout_page_spec.py, tests/test_book_page_frame.py, tests/test_book_pdf_two_up.py, tests/test_book_pdf.py, tests/test_book_toc.py, tests/test_book_page_numbers.py, tests/property/test_book_pairing.py, tests/property/test_book_pdf_geometry.py, tests/fixtures/, meta/architecture/requirements.yml, docs/how-it-works/01-domain/puzzle-creation/07-book-assembly-and-the-admin-panel.md
<!-- tests/fixtures/ is the baseline directory (re-recorded here); the author names the exact files. -->
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

`INTERIOR_FOOTER_MM` is 29.878 mm today: the QR icon's row (`QR_SLOT_MM`, 20 mm), the footer line (3.53 mm) and two 9 pt gaps (measured by importing the constants, 2026-11-07). With the QR gone (CARD-391) that row is empty. The owner's version B shrinks the footer to hairline + one line and runs the grid area down to it, about 20 mm more height on the Book 1 profile (the author states the exact figure). The band is the unit the usable area is measured against, so the shrink is not cosmetic: it changes every grid's room, FR-040's stated pairing thresholds (29 to 32 combined cells; "28 cells still pairs and 33 was already refused before the strip"), the one-cell-size-per-grid-size table (CARD-225), and, because `interior_frame` is shared by every interior page kind, possibly the TOC's rows per page and the answer packing. The registry states numbers; they must be re-derived and the registry must be true again, not re-recorded to whatever the code now prints.

**[OWNER INTENT 2026-11-07, on the question 'without QR codes can some puzzles go two per page instead of one?']** Yes: the pairing decision must USE the space the one-line footer frees. No threshold may stay hard-coded from the QR-footer era; the pair boundary is computed from the new usable height (AC-4), and no separate before/after measurement is wanted beforehand (owner: 'probably not'). Puzzles that newly pair are expected and are reported in the page-count attribution (AC-5 or the card's equivalent).

## What to implement

1. **The band.** `INTERIOR_FOOTER_MM` becomes the footer line plus its two gaps (the author derives it from the constants that state them, as the current expression does) and `QR_SLOT_MM` is deleted. State the old and new band in px and mm and the puzzle area's new depth on the Book 1 profile and on the shortest trim `book_page_spec` admits.
2. **One frame for every kind, measured.** CARD-222's principle is one frame for every interior page, and the owner's text says section openers and solution pages are "unchanged from version A", which does not say the footer band stays tall on them. Keep one frame (recommended) and MEASURE what it does to the other kinds on the corpus: TOC entries per page (`_toc_entries_per_page`) and TOC page count, the guide's two pages, answer packing and page count, the Play page. If any page count moves, the KDP band and gutter follow the true total (they already read it); record each moved book. If a kind needs the old height, STOP and report instead of forking the frame.
3. **Re-derive FR-040's thresholds with independent arithmetic.** In the test, compute the largest shared cell and the pair boundary from the usable height, the band, the two title bands, the clue depths and the 7.0 / 7.5 mm limits written out directly, not by calling `compute_pair_layout`. Replace the "29, 30, 31 and 32 cells" statement and the worked cases in `requirements.yml` with the new figures, each with its boundary neighbour (N cells pairs, N+1 does not). Clause (b)'s "one footer strip carrying both puzzles' links" is rewritten: one shared line.
4. **Re-derive the cell-size table.** `book_cell_mm` / `book_cell_sizes` choose one cell per grid size across the book, capped at 7.5 mm. Generate the table of (grid size, cell mm) before and after for the profile set, attribute every changed entry to the freed height (a size already at the 7.5 mm cap must NOT change), and hold the generated table in a test (the QR-shape block in `docs/deploy/player.md` is the precedent for a doc table a test holds).
5. **Re-record the baselines**, reading the diff with a control that distinguishes the intended change (area grew; marks that scale with it) from drift (any mark that moved without the area explaining it).
6. **Docs.** `07-book-assembly-and-the-admin-panel.md` and the FR-031/FR-032/FR-040 text in `requirements.yml` describe the footer as hairline + grid size + pointer + folio, no QR row.

## Acceptance criteria

- **AC-1** (happy, the band): *Given* the layout constants, *then* the footer band equals the footer line plus two gaps computed from the constants that state them, and no symbol `QR_SLOT_MM` remains in `src/`. (test: `TestFooterBand_IsOneLineAndTwoGaps`)
- **AC-2** (happy, the area): *Given* the Book 1 profile and the shortest admitted trim, *then* the puzzle area's depth equals the usable height minus the new band, minus header, computed in the test from the profile's millimetres; and it is larger than before by exactly the freed row. (test: `TestFrame_PuzzleAreaGrowsByTheFreedRow`)
- **AC-3** (happy, grid reaches the line): *Given* the tallest admitted grid on a single page, *then* the grid's bottom plus its minimum clearance sits above the footer line and no grid, clue box or band mark crosses the footer rule. (test: `TestPuzzlePages_GridRunsDownToTheFooterLine`)
- **AC-4** (boundary, pairing re-derived): *Given* two same-tier neighbours whose combined drawing height is the new threshold N cells and N+1 cells, *then* N pairs at the shared cell the independent arithmetic gives (+/- 0.05 mm) and N+1 prints as two single pages; the figures in `requirements.yml` equal these. (test: `TestTwoUp_ThresholdsRederivedFromTheOneLineFooter`)
- **AC-5** (guard, cap): *Given* a grid size whose cell was already the 7.5 mm cap, *then* its cell is unchanged; every other changed entry is attributed in the table. (test: `TestBookCellSizes_HeldTableAndTheCapDoesNotMove`)
- **AC-6** (guard, other kinds): *Given* the corpus, *then* TOC rows per page, TOC page count, answer page count and interior page count before and after are recorded in the test as literals with each change attributed to the band; a book whose count crosses a `KDP_GUTTER_BANDS` boundary is named. (test: `TestInterior_PageCountChangeIsAttributedToTheBand`)
- **AC-7** (guard, nothing else moved): *Given* the corpus, *then* every mark that does not depend on the area (rule weights, header band, clue digit size, folio position relative to the page bottom) is at the same coordinate as before. (test: `TestPuzzlePages_OnlyAreaDependentMarksMove`)
- **AC-8** (registry): *Given* this card merged, *then* FR-040's statement and worked ACs, FR-032's footer wording and AC-377's replacement state the new figures and the architect-validate run (forge_1 copy) reports 0 errors. (review-lens, evidence: validator output)
- **AC-9** (guard, CLI/web): *Given* the CLI and web-UI exports, *then* byte-identical to main (CON-019). (test: `PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry`)

## Guardrails

- G-1: CLI and web geometry never change (ADR-0036/R1: `compute_layout` without a `PageSpec` is byte-identical to today's A4 golden).
- G-2: No stored setting changes meaning: a book's margins and trim are unchanged; only the interior frame's footer band is.
- G-3: Do not re-record a threshold from the code's output. Every number the registry states is derived in the test from first principles (CLAUDE.md test style: an independent second implementation).
- G-4: The page counts that move are reported, not hidden: the KDP gutter follows the true total.
- G-5: Writes the vector page only: no raster writer, no raster test twin; retires the raster-twin tests of its own module. (This card's modules: test_book_page_frame, test_book_pdf_two_up, test_book_pdf, test_book_toc, test_book_page_numbers; their ids that CARD-387's recount marks 'convert after' stay with CARD-387's tail unless this card already rewrites them.)

## System contract

- ADR-0036/R1, R2 — default geometry byte-identical; only COMP-007 places things (check: `TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden`; review-lens)
- ADR-0036/R3, R4 — rounds drawn, never typed (check: their own tests)
- CON-018 — the profile set the figures are measured on (check: review-lens)
- FR-040 — two-up pairing (check: the AC tests above)

## Architecture context

- **FR:** FR-030 to FR-032 (frame and puzzle page), FR-040.
- **Decisions this follows:** CARD-222 (one frame), CARD-224 (42% placement), CARD-225 (one cell per grid size).

## Worktree notes

(none yet)
