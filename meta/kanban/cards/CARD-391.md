# CARD-391: Puzzle pages carry no QR — the per-puzzle code, its caption and link are retired, and the footer points at the Play online page

**Status:** in_progress
**Priority:** P2
**Category:** feature
**Estimate:** 4c (1.5d)
<!-- Mostly deletion and test retirement, and the retirement is the expensive half: tests/test_book_qr_slot.py alone is 70 test functions in 17 classes, and 17 more test modules read the QR names (the author lists them by `git grep` in the Worktree notes at the start). Geometry is HELD on purpose so the diff is separable from CARD-392's, which changes it. -->
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** owner decision 2026-11-07: "we decided to remove individual QR codes altogether". Version B, "Puzzle pages without a code": the footer keeps a hairline rule, the grid size on the inner side and, on the outer side, a short line "Play puzzle 53 online · p. 167"; "Two to a page": the two grids centre across the full width and share one footer line.
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** CARD-390
<!-- CARD-390 is the page the footer line names and the plan it reads the page number from. Do not export or print a book between the merges of CARD-390 and this card: the interior would carry both the old per-puzzle code and the new page. -->
**Touches:** src/nonogram/admin/book_pdf_generator.py, src/nonogram/admin/book_puzzle_vector.py, src/nonogram/admin/book_sheet_vector.py, src/nonogram/admin/book_proof.py, src/nonogram/export/layout.py, src/nonogram/export/png.py, tests/test_book_qr_slot.py, tests/test_book_vector_goldens.py, tests/test_book_pdf_two_up.py, tests/test_layout_page_spec.py, tests/test_book_pdf.py, tests/test_book_page_frame.py, tests/test_book_puzzle_frame.py, tests/test_book_pdf_levels.py, tests/test_book_pdf_band.py, tests/test_book_grid_rules.py, tests/test_book_proof_pages.py, tests/test_book_page_numbers.py, tests/test_book_arrange_page_breaks.py, tests/test_book_finalise_gutter.py, tests/test_book_pdf_memory.py, tests/test_book_puzzle_page_vector.py, tests/property/test_book_pdf_geometry.py, tests/property/test_book_pairing.py, tests/test_book_footer_pointer.py, meta/architecture/requirements.yml, meta/architecture/decisions/adr/0041-public-player-static-bundle-and-hash-urls.md
<!-- The test list is `git grep -l "qr_slot\|qr_link\|QR_LINK_TEMPLATE\|qr_caption\|qr_group\|QR_CAPTION_TEXT" -- tests src` as read on main 2026-11-07, plus the new file. Re-derive it; do not trust it. -->
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

The owner removed individual QR codes (ADR-0041/R8). Today every puzzle page prints a 2 x 2 cm placeholder checkerboard, a "Solve it online" caption and the typed link `nonogram.example/p/NNN` (`QR_LINK_TEMPLATE`, `QR_CAPTION_TEXT`, `_draw_qr_placeholder`; the vector writer composes them through `book_sheet_vector.QrGroup`), and a two-up page carries two of them in one footer strip. FR-040's pairing rule even has a clause (c) that exists only because two QR groups must fit side by side (AC-377). All of it goes, and a one-line pointer to the Play online page (CARD-390) replaces it.

The footer BAND's height (`INTERIOR_FOOTER_MM`, 29.878 mm = the QR row 20 mm + the label line + two gaps) is deliberately NOT changed here: it is the unit every page's usable area is measured against, and shrinking it moves every grid and re-derives the pairing numbers. That is CARD-392. Holding it here makes this card's diff only the ink that left and the line that arrived, and gives a strong control (AC-6).

## What to implement

1. **Retire the QR from the vector writers and the layout.** Remove `QrGroup` and its drawing, `qr_module_boxes`, `_vector_qr_group`, `_vector_two_up_qr_groups`, `QR_LINK_TEMPLATE`, `qr_link`, `QR_CAPTION_TEXT`, `qr_group_caption`, `_draw_qr_placeholder`, the bitmap drawers that read them (`_draw_qr_caption`, `_draw_two_up_qr_groups`; deleting the bitmap interior path is CARD-387's, but its QR drawers must go here or `qr_slot` cannot), and in `export/layout.py` `qr_slot`, `qr_caption`, `qr_group_insets`, `QrSlot`, `QrCaption`. Keep `QR_SLOT_MM` only as the band's reserved row, renamed and commented as retired by CARD-392. `export/png.py` and `book_proof.py` read `qr_slot`; for a single-puzzle CLI/web export the layout has no page, `qr_slot` was already `None`, so deleting it is byte-neutral (AC-8 proves it).
2. **Pairing clause (c) goes.** `compute_pair_layout`/the pairing walk stop refusing a pair on QR-group width. Consequence: a narrow trim (about 175.6 mm usable width and below, e.g. 6 x 9 in) can now print two-up pages it could not. FR-040's statement loses clause (c) and AC-377 is rewritten (a narrow trim now pairs by the height and width rules alone); the Book 1 profile's pairing verdicts must not change (AC-7). Edit `requirements.yml` in the same delta.
3. **The footer pointer.** Outer side of the footer line, mirrored by parity: `Play puzzle {N} online · p. {X}`, N the puzzle's print number, X the Play page's interior page number read from `section_plan` (CARD-390; this card computes no page number). Inner side keeps the grid size on a single puzzle page. Folio unchanged. A two-up page prints ONE shared footer line; the wording is not fixed by the owner's text (owner question 1; recommendation `Play puzzles 9 and 10 online · p. 167`), and the grid-size label stays absent from two-up pages as today (AC-18 of CARD-322). The pointer exists only when the Play page exists (domain stored); otherwise the footer carries the grid size and folio only. Placement comes from `export/layout.py` (ADR-0036/R2).
4. **Retire the tests honestly.** For `tests/test_book_qr_slot.py` (70 tests, 17 classes) and each other module that reads a retired name: audit each test's CLAIM. A claim about the QR (slot size, caption, link, gutter-side ink of a QR) is retired by the owner's ruling of 2026-11-07, with the evidence recorded in the Worktree notes; a claim that survives (a footer mark never lands on the gutter side; a two-up page carries its folio; the footer geometry of a two-up page equals a single page's; the pair that cannot fit splits into single pages) is converted to the footer line, not deleted. Do not keep a test that now asserts nothing; do not delete one whose claim still holds. CARD-387 is auditing the same file for the bitmap path: this card goes first and retires the QR classes, and the author states which node ids CARD-387 therefore no longer owns.
5. **Rewrite AC-18 of CARD-322** (`tests/test_book_vector_goldens.py` `qr_findings` cells): the expectation is now the footer line, a literal string in the test built from the book's own numbers and the plan's Play page number, read from the text layer, below the grid and inside the usable area; plus a control that neither "Solve it online" nor "nonogram.example" appears on any page.
6. **ADR-0041/R8's check flips** from `review-lens` to `kind: test` naming `tests/test_book_landing_address.py::test_the_printed_slug_is_the_bundles_slug` (CARD-389) and this card's AC-1 test, in this delta (resolve both with `git grep -w`).

## Acceptance criteria

- **AC-1** (guard, exactly one code in the book): *Given* a fixture book with a stored domain, *when* the whole interior is exported and every page is rendered and read with CARD-388's reader, *then* exactly one QR is found, on the Play online page; and no puzzle, two-up, guide, contents, divider or answer page has one. A plant that restores the placeholder checkerboard on a puzzle page reds it. (test: `test_no_interior_page_but_the_play_page_carries_a_qr`, the planned ref of ADR-0041/R8)
- **AC-2** (happy, the pointer): *Given* puzzle 53 on a single page with the Play page at 167, *then* the page's text layer holds `Play puzzle 53 online · p. 167` on the outer side for both parities, and the grid size on the inner side; expected strings are literals built in the test from the book. (test: `TestFooterPointer_NamesThePuzzleAndThePlayPage`)
- **AC-3** (happy, two-up): *Given* a two-up page, *then* it carries exactly one pointer line, naming both puzzles, on the outer side, and no grid-size label. (test: `TestFooterPointer_TwoUpSharesOneLine`)
- **AC-4** (negative, no domain): *Given* a book with no stored domain, *then* no page has a pointer and the footer carries the grid size and folio only. (test: `TestFooterPointer_AbsentWithoutADomain`)
- **AC-5** (guard, the pointer is true): *Given* every pointer in the corpus, *then* the page number it prints is the interior page number of a PLAY page in the exported PDF. (test: `TestFooterPointer_NamesARealPlayPage`)
- **AC-6** (guard, geometry held): *Given* the corpus, *then* apart from the removed QR group and the added footer line, every mark on every puzzle page (grid, clue boxes, band, rules, folio) is at the same coordinate as on main before this card; the footer band's height is unchanged. (test: `TestPuzzlePages_GeometryHeldExceptTheFooter`)
- **AC-7** (guard, pairing): *Given* the Book 1 profile corpus, *then* the set of paired and unpaired puzzles equals the set on main before this card; *given* a 6 x 9 in trim, two-up pages now appear where AC-377 said none could, and the registry says so. (tests: `TestTwoUp_BookOneVerdictsUnchanged`, `TestTwoUp_NarrowTrimsNowPairOnHeightAndWidthAlone`)
- **AC-8** (guard, CLI/web): *Given* the CLI and web-UI exports, *then* they are byte-identical to main (CON-019). (test: `PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry`)
- **AC-9** (registry): *Given* this card merged, *then* `requirements.yml` no longer states a QR slot, QR group or per-puzzle link in FR-032 or FR-040, AC-377 is rewritten, and the architect-validate run (forge_1 copy) reports 0 errors. (review-lens, evidence: the validator output)
- **AC-10** (claims, the retirement): *Given* every test node removed or converted, *then* the Worktree notes list each with its claim and its disposition (retired by the owner's ruling / converted to the footer line / kept), and `git grep -w` for each retired name over `src/` and `tests/` returns nothing. (review-lens)

## Guardrails

- G-1: The footer band height, the grid, the clue boxes and the band do not move (AC-6). CARD-392 owns every geometry change.
- G-2: The pointer and the Play page exist together or not at all (ADR-0041/R8): never a pointer to a page that was not printed.
- G-3: No page number computed here; read it from `section_plan`.
- G-4: CLI/web exports byte-identical (CON-019).
- G-5: Do not delete the bitmap interior path beyond the QR drawers; that is CARD-387's.

## System contract

- ADR-0041/R8 — one QR, no per-puzzle address, pointer only with the page (check: review-lens until this card's delta flips it; AC-1 is the test)
- ADR-0036/R2 — placement only from COMP-007 (check: review-lens)
- ADR-0037/R1 — no picture title on a puzzle page (check: review-lens)
- CON-019 — CLI/web byte-identical (check: `PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry`)
- FR-040 — two-up pairing, as amended by this card (check: the AC tests above)

## Architecture context

- **FR:** FR-032 (puzzle-page placement and footer), FR-040 (two-up), FR-045.
- **Supersedes in part:** CARD-204 (QR slot), CARD-223 (QR in the footer's outer corner, caption, typed link), CARD-248 (one footer strip carrying both links), CARD-210 (retired).
- **Raw requirement:** `meta/architecture/inputs/raw-requirements.md`, "Delta 2026-11-07".

## Worktree notes

(none yet)
