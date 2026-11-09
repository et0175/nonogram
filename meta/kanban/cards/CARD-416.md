# CARD-416: Convert the last raster interior tests, then delete the remaining raster writers and the bitmap arms (387b, the tail of CARD-387)

**Status:** done
**Priority:** P2
**Category:** enabler
**Estimate:** 6c (2d)
<!-- Cut 2026-11-08 out of CARD-387's old 20c (6d); range 5 to 8c. Runs LAST: it waits for the cards that rewrite the subjects of its ~62 ids. NOT yet priced by a batch; the first module batch re-prices it. -->
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** The tail of CARD-387 (restated and split 2026-11-08 on the owner's "restate 387 and fix the 207/232 text"). CARD-387 (387a) takes the work that can be done now; this card takes the ids whose subject another queued card is about to rewrite, and the deletion.
**Idea:** —
**Wave:** —
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** CARD-387, CARD-392, CARD-207, CARD-229, CARD-230, CARD-232, CARD-233
**Touches:** src/nonogram/admin/book_pdf_generator.py, tests/test_book_pdf.py, tests/test_book_pdf_band.py, tests/test_book_interior_type_floor.py, tests/test_book_page_frame.py, tests/test_book_page_numbers.py, tests/test_book_toc.py, tests/test_book_proof_pages.py, tests/test_book_guide_page.py, tests/test_book_guide_page_type.py, tests/test_book_solved_page.py, tests/test_book_solved_answer_key.py, tests/test_cli.py, docs/guides/how-to-solve-nonograms.md, docs/how-it-works/01-domain/puzzle-creation/07-book-assembly-and-the-admin-panel.md, meta/architecture/requirements.yml, meta/architecture/decisions/adr/0037-book-puzzle-page-band-and-strokes.md, meta/architecture/decisions/adr/0042-book-interior-is-vector-cover-stays-raster.md
<!-- The guide_page, solved_page and answer_key modules are listed because any ids their cards (CARD-229/230, CARD-232/233) leave behind are mopped up here; the author re-derives the list with the classifier (`~/Documents/nonogram-reviews/CARD-387-recount/classify_tests_without_interior_bitmap_mode.py`). -->
**Review score:** n/a — closed on the owner's 2026-11-09 board triage; built under other work, no review of its own.
**Started:** —
**Closed:** 2026-11-09
**Actual:** built elsewhere (see the closing note).
**Merge commit:** ab4cdfbd, 4cf2cc70, 85627111
**Blocked by:** —

## Why this card exists

CARD-387's restatement (2026-11-08) split the raster-interior cleanup. This card is the tail. After CARD-387 (the dot arm, the solver_clues ids and the "do now" modules), CARD-392 and CARD-207 (which rewrite the `pdf`, `pdf_band`, `type_floor`, `page_frame`, `page_numbers` and `toc` subjects), and CARD-229/230/232/233 (which retire the guide_page group, 58 ids, and the solved_page + answer_key group, 103 ids, each in its own card), what remains is: the ~62 "convert after" ids, any leftovers, and the deletion of the raster writers nothing calls.

Recount facts to carry (re-derive at dispatch): 21 raster writers (~2,092 lines) remain after CARD-391 (the original card said 23 / 2,236; the three QR writers went with CARD-391); all production-unreachable, their only callers are `produce`'s bitmap arms gated on a vector kind. The saving is at most 84 s per gate (~5%, realistically half): the reason is dead code and the two-writer trap, not time. Vector is the only writer for the book interior (ADR-0042); the divider stays a bitmap and the cover stays raster.

## What to implement

0. **Re-derive** the classifier counts and the 21 writers on the tree you start from (the classifier that excludes `interior_bitmap_mode`, a KEEP name); a different number is the finding.
1. **Convert the "convert after" ids** in `pdf`, `pdf_band`, `type_floor`, `page_frame`, `page_numbers` and `toc` by CARD-387's step 1 and 2 (page-obtaining helper at the vector render; raster-specific instruments re-expressed with the `pdf_vector` readers; retire only on evidence with a named survivor). Change existing tests, add none.
2. **Delete the remaining raster writers and the bitmap arms** of `produce` by item 16 below, re-derived to the 21 that remain (the item's names and spans are CARD-322's; the three QR writers, and `_draw_difficulty_dots` and possibly `_set_band`, are already gone).
3. **Restate the prose and the censuses** the deletion touches: the docs, requirements comments and ADR sentences item 16 lists; the dual-medium controls and `_DECLARED_CLIP_DIVERGENCE` as the carried notes say; the layering guard and the writer-set census re-derived, not pasted.

## Acceptance criteria

* **AC-A** (every id is accounted for): as CARD-387's AC-A, for this card's modules. (check: review-lens on `--collect-only -q` by `comm`; each survivor verified by `ast` and a plant.)
* **AC-B** (no lost claim): as CARD-387's AC-B. (check: review-lens.)
- **AC-15** (the bitmap interior path is gone, and only it): *Given* `src/`, *then* the 23 functions of item 16 and the bitmap arms of `interior_stream` are absent; every KEEP name of item 16 is present and the cover and divider still export; `tests/test_cli.py`'s layering guard and the writer-set census are green; and `grep` for the deleted names over `src/` finds nothing. (test: the existing cover and divider tests, the layering guard, the existing writer-set census in `tests/test_book_pdf.py`, CHANGED here to assert the deleted names absent and the KEEP names present, with a plant that re-adds one; owner's rule: change existing, add none.)
- **AC-16** (every retirement has a survivor): *Given* the item 17 table, *then* each retired node id names a vector survivor that exists once by `ast`, is green, and has a plant that reds it; the collected-id difference is exactly the table (plus the F-307 rename and added tests); the ~160 cover/divider/proof raster tests are all still collected and green; if the re-derived set exceeded 400 ids the card stopped and reported. (check: review-lens on a `--collect-only -q` set difference by `comm` and the table; each survivor verified by `ast` and a plant.)



## Guardrails

* **G-0** Writes the vector page only: no raster writer, no raster test twin; retires the raster-twin tests of its own module. This card creates no raster writer and no raster test twin.
* **G-1** No `src/` behaviour change before the deletion batch; the interior stays vector on every production path throughout.
* **G-2** Cover, divider and proof raster tests stay (about 160, carried).
* **G-3** The raster writers are deleted only after the last test that calls them is converted or retired; one commit per deletion step; the layering guard and the writer-set census re-derived, not pasted.
* **G-4** No bound widened, no corpus shrunk, no skip or xfail added.
* **G-5** The full suite is the merge gate (this card touches `src/` and `tests/`).
* **G-6** Starts only after CARD-387, 392, 207, 229, 230, 232 and 233 have merged: converting a subject another card is rewriting is the rework the split avoids.

## System contract

* ADR-0042/R1 and R5: the interior is vector; retire-with-named-survivor.
* ADR-0039: controls that can fail.

## Moved from CARD-322 (verbatim; the numbers are CARD-322's, which other cards cite; the counts are superseded by the recount above)

### Items

16. **DELETE THE BITMAP INTERIOR PATH** (`src/nonogram/admin/book_pdf_generator.py`). After the flip the only `src/` caller of the bitmap interior writers is the raster branch of `interior_stream`'s inner `produce` (**mine, `ast` over `src/` on main at `c79d506c`, re-verify at dispatch**). The 23 functions and their spans (mine): `create_guide_page` 456, `create_title_page` 25, `create_toc_page` 183, `_blank_page` 97, `_puzzle_payload` 21, `_two_up_page` 163, `_draw_two_up_qr_groups` 68, `_draw_solved_slot` 191, `solved_puzzle_page` 130, `_packed_answer_page` 213, `_draw_page_frame` 139, `_draw_rule` 13, `_draw_qr_caption` 38, `_draw_qr_placeholder` 29 (`export/png.py` has its own function of that name; it is not a caller of this one), `_draw_difficulty_dots` 89, `_draw_pipeline_diagram` 88, `_draw_difficulty_legend` 61, `draw_example_line` 37, `wrap_words` 17, `_clipped_to` 21, `_set_band` 48, `_write_clues` 19, `_stroke_drawing` 90: **2,236 lines of 8,473**, matching the measurement exactly. Outside callers by `ast`: `produce` calls `create_title_page`, `create_guide_page`, `create_toc_page`, `_blank_page`, `_two_up_page`, `solved_puzzle_page`, `_packed_answer_page`; `_draw_difficulty_legend`, `draw_example_line` and `wrap_words` are called only from inside `create_guide_page` (its nested `set_page`, `line_image`, `paragraph`); every other name has no caller outside the set. Also delete the bitmap branches of `produce` (the `else:` arms after each `page_medium(PageKind.X) is PageMedium.VECTOR` test, about 40 lines, read) and the now-orphaned `is_heading` (read: referenced only from the deleted set; verify) . **KEEP (read and `ast`):** `_draw_folio`, `_guide_face`, `_band_font`, `type_px`, `interior_bitmap_mode`; the helpers the vector writers import: `_guide_rule_width`, `example_line_layout`, `guide_icon_layout`, `_toc_entries_per_page`, `page_frame`; the layout-time helpers `_two_up_qr_insets`, `_folio_reserve_px`, `_qr_group_line_px`; `_write_page` and `_write_pdf` (the cover and dividers use the raster path); the cover (`create_cover_page`, `_cover_page`, `export_cover`, `_cover_title_face`) and divider (`create_divider_page`) writers. **D9 (ruled): `_draw_difficulty_dots` and `_set_band` go with the rest** (item 8); all 23 functions, 2,236 lines. **The registry stays default-deny** (`page_medium`, `_write_pdf`'s refusal, G-6); only the writers go. After the deletion, lifting a declaration back for one of the five kinds has no writer to route to, so the dual-medium controls (`_ensure_declared`, `_declare_all`, the lifts in `test_book_pdf.py`, `test_the_raster_twin_of_the_same_page_does_carry_one`) go with item 17, or use the DIVIDER as their raster control (an XObject check can use a divider page). Update the prose that names the deleted writers (mine, grep): `docs/guides/how-to-solve-nonograms.md` (4 lines), `docs/how-it-works/01-domain/puzzle-creation/07-book-assembly-and-the-admin-panel.md` (1 line), `meta/architecture/requirements.yml` (4 comment lines), `meta/architecture/decisions/adr/0037-book-puzzle-page-band-and-strokes.md` (5) and `0042-...md` (1): 5 lines in `docs/` and 12 in `meta/architecture`, the "12" the measurement cites; ADR-0037's and `raw-requirements.md`'s mentions are history and are marked, not rewritten, unless an ADR sentence calls a deleted function live. After the deletion run the layering guard (`tests/test_cli.py`) and `tests/test_book_pdf.py`'s writer-set census; report both.


## Worktree notes

- Cut 2026-11-08 from CARD-387; see that card's Why section for the recount. Number chosen as the next free card number (the highest existing was CARD-415).

## Closed 2026-11-09 — board triage

The raster interior writers and the bitmap arms of `interior_stream`'s `produce` were deleted on 2026-11-09 (ab4cdfbd), with the legacy layout pin (4cf2cc70) and the counts and citations the deletion moved (85627111). Left: a few present-tense mentions of deleted writers in requirements.yml (CON-020 exemption), ADR-0037, book_vector.py, book_vector_draw.py, book_sheet_vector.py and tests/test_book_interior_type_floor.py, for the next docs sweep.
