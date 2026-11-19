# CARD-485: A single-puzzle page leaves room for its footer, so every puzzle page keeps its centred folio

**Status:** done
**Priority:** P1
**Category:** ops
**Estimate:** 2c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/485-single-page-footer-reserve
**Worktree:** —
**Source:** owner 2026-11-19, on the downloaded "Christmas Nonograms" interior (prod DB): "Puzzle 140 - page number is in the corner, while other page numbers are in the middle, puzzles 114-115 have no folio, but it looks like we can make cell size a bit smaller." Owner: "yes, card it and start CARD-485".
**Idea:** —
**Wave:** 81
**Created wave:** 81
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/export/layout.py, src/nonogram/admin/book_page_spec.py, src/nonogram/admin/book_pdf_generator.py, tests/test_book_page_numbers.py, tests/property/test_book_pdf_geometry.py, tests/test_book_vector_goldens.py
**UI surface:** printed interior (single-puzzle pages)
**Review score:** 9.0 (cycle 1/3 - CERTIFIED)
**Started:** 2026-11-19T14:42Z
**Closed:** 2026-11-19T16:47Z
**Actual:** 1c — ratio 1/2 = 0.5
**Merge commit:** 53235f323d90364b6920ac7633a59e629a5c219a
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

**Seam: a `footer_reserve_px` keyword on `compute_layout`, passed at the two places a book puzzle page is fitted.** It is the single-page twin of `compute_pair_layout`'s parameter of the same name and takes the same figure, `interior_frame(spec).footer_depth` (117 px on every stored trim), so the depth constant has one definition and the frame does not move. `_placed_cell_mm` takes the reserve off its usable height exactly (pixels to millimetres as a `Fraction`). Placement is unchanged: the drawing already floated in `_puzzle_area_px`'s area, which ends at the footer rule. The bug was that asymmetry (the fit ran to the bottom margin, the placement stopped at the rule), and a drawing fitted above the rule leaves at least the header rule's lift of spare (17.72 px at the 12 mm band). That is more than the 14.29 px the ratio needs at every cell up to the 7.5 mm cap, so the drawing floats at the ratio and clears the rule. The two callers are the generator's `vector_puzzle_page` and `book_page_spec.book_cell_mm`, so `book_cell_sizes` and both panel readers (`app.py` cell display, `book_manager` floor gate) follow. A non-zero reserve on a spec with no parity raises, and the CLI path never passes one (G-2).

*Why not do it inside `compute_layout` for every parity spec:* the full answer page is laid out on `answer_section_spec`, which already adds `INTERIOR_FOOTER_MM` to `bottom_mm`. A blanket reserve would take that strip off twice and shrink tall answers. *Why not hand the page a spec with a deeper `bottom_mm`:* `_placed_drawing_top` reads `_puzzle_area_px` from the same spec, so the float area would move up by a strip.

**Every caller of compute_layout with a parity spec, after the change:**
* single puzzle page (`vector_puzzle_page`): reserves the strip. Right; this is the fix. With `cell_sizes` the reserved book cell caps it anyway; without them (F-14 callers) the reserve alone keeps it above the rule.
* `book_cell_mm` / `book_cell_sizes`: reserves. Right: the per-grid-size cell is the page's own fit (NFR-008), and every member of a size shares the smaller cell.
* `_pair_cell_mm`: no compute_layout call of its own. It takes the min of two book cells, so it inherits the smaller cells. On the owner's book the 7 pairs, their cells and their slack are identical before and after (measured), so it is right there. It could only move a pair whose member is height-bound as a single page.
* full answer page (`book_answer_vector.answer_page`): no reserve, unchanged. Right: `answer_section_spec` already gives the strip up.
* packed answers: `compute_packed_solved_layout`, its own fit, untouched.
* guide (`example_line_layout`, `guide_icon_layout`, `_guide_rule_width`), `page_frame`'s probe, `header_band`'s probe: no reserve, unchanged. Right: they read rule widths, the usable box or a cropped one-row diagram, and no puzzle page is fitted. The goldens are unchanged in the gate.
* proof pages (`book_proof._drawn_pages`, through `render_pages`): no reserve, unchanged. Right on Book 1, where both proof puzzles are width- or cap-bound and their book cells do not move (30x30 stays at 4.8846 mm). Gap, not closed: on a square or very short trim the proof's 30x30 could show a larger cell than a book page would print, because the proof draws no footer and keeps the full-box fit.

**Measured on the owner's book** (built from the JSON, read-only, through `interior_generator(...).export_interior` on base and branch, every `draw_sheet_furniture` verdict recorded):
* Single pages without the footer group: **15 before, 0 after**, of 146. The 15 before, as (puzzle, size, slack px, corner folio drawn): 55 18x24 -99 no; 58 22x25 -26 yes; 92 21x24 -11 yes; 93 17x25 -117 no; 94 18x25 -99 no; 109 18x26 -117 no; 110 18x27 -99 no; 112 10x29 -117 no; 114 17x30 -117 no; 115 22x30 -117 no; 140 18x24 -11 yes; 143 18x25 -99 no; 144 20x25 -80 no; 152 14x29 -117 no; 154 22x30 -40 yes. So 4 pages had a corner folio and 11 had none. The owner named three of them (114, 115, 140).
* Cells: 12 of 80 grid sizes change (29 puzzles), all smaller, by 0.39 to 4.10%: 10x29, 14x29, 17x25, 17x30 and 22x30 by -4.10% (22x30 6.5268 -> 6.2591 mm), 18x24/18x25/18x27 7.5 -> 7.2371 (-3.51%), 18x26 7.3179 -> 7.0178, 20x25 7.45 -> 7.2371, 21x24 7.5 -> 7.4705, 22x25 6.6793 -> 6.6167. The smallest cell is unchanged at 4.9667 mm. These 12 sizes are exactly the sizes of the 15 pages above.
* Pairing and page count: **unchanged.** 204 PDF pages, 146 single and 7 two-up, the same pairs (1-2, 3-4, 5-6, 7-8, 9-10, 69-70, 79-80), so no page number moves.
* Book 1 (`corpus_book()` with `corpus_puzzles()` and with `baseline_puzzles()`): **no cell changes** (18x18 7.5, 20x20 7.3269, 10x10 7.5, 15x15 7.5, 30x30 4.8846 on both trees).
* AC-3, over every extent 10..30 x 10..30 at every clue depth `_gutter_grid` builds (3745 cases per parity): **0** cases shrink where the full-box page already cleared the footer, and none grow. 422 shrink on Book 1, 443 on the owner's profile. Afterwards every case floats at `"ratio"`, 0 overrun the rule and 0 land on it, with a minimum slack of 10 px.
* CLI/A4 (G-2): `repr(compute_layout(r, c))` over 882 extent/depth cases hashes the same on base and branch, and no CLI test moved.

**G-4 / CARD-483's F-5 (not decided here):** this card takes single pages out of F-5's reach. On the owner's book no single page has `drawing_bottom == footer_rule.y`; the smallest single-page slack is 10 px (13 pages), against -117 px before. The same holds over the full sweeps above, where the minimum is 10 px. Two-up pages are untouched: pair 79-80 still ends exactly on the rule (slack 0) on both trees, and that is where F-5 still applies.

**Finding, needs the owner's decision, not fixed (G-1 keeps the footer design):** on very narrow trims the footer's grid-size label now overprints the centred folio. It was always possible, but no single page on such a trim reached it before, because the page lost its footer. On the 10 x 10 cm min-trim book, a 20x20 page reads "20 6 x 20 · Solution on p. 8" (folio 6 under the label), seen in a 200 dpi render. Worst-case label "30 x 30 · Solution on p. 388" against folio "388", computed with the face metrics at minimum margins: trims up to 12.40 cm wide collide, and 5 x 8 in (12.7 cm) and wider do not. Nothing measures label against folio today.

**Tests** (net **+1**, see the counts below). Each change below says why the new value is right:
* AC-1: `tests/test_book_page_numbers.py` `test_every_single_page_draws_its_footer_group_on_the_owners_profile` replaces `test_blank_page_omits_the_folio_when_the_grid_is_page_fit_bound`, which asserted the old omission on the same F-1 tight fit. It uses the owner's profile, both parities, and puzzle 140's shape (18x24, 7-deep column clues, a 5-deep sibling), a height-bound 22x30 and the F-1 tight fit. It asserts `draw_sheet_furniture` returns True and the centred folio is read back, and its premise asserts that the full-box fit put the 18x24 and the 22x30 past the rule.
* AC-2: `test_no_single_page_of_the_extent_sweep_reaches_below_the_footer_rule` (new) runs every 10..30 extent at depth ceil(min/2) through `vector_puzzle_page` on Book 1 and the owner's profile, both parities (1764 pages). It holds `content_bottom <= footer_rule.y`, and 308 of those pages overran under the full-box fit (75 per parity on Book 1, 79 on the owner's profile). There is also a rendered half in `tests/property/test_book_pdf_geometry.py`: `test_PropertyTest_BookPdf_PortraitWithFixedTopEdgeForEveryExtent_pdf_pages` and `test_PropertyTest_BookLayout_DrawingFitsUsableAreaUnderStandardCell_pdf_pages` now also assert that poppler's `grid_bottom` is at or above the footer rule.
* AC-3: `tests/test_book_cell_size.py` `test_the_table_is_held_and_only_the_height_bound_shapes_follow_the_band` (renamed from `..._nothing_changed_with_the_band`). CARD-392 left this table "the place its changes are attributed". The 5 width-bound squares are unchanged, and the 2 tall shapes lose exactly 9.906 mm / drawing rows (45 and 38): Book 1 5.3665 -> 5.1464 and 6.3551 -> 6.0944, 6x9 4.2376 -> 4.0175 and 5.0182 -> 4.7575, 5x8 3.6732 -> 3.453 (exact 3.45302) and 4.3498 -> 4.0891. A 20 mm deeper footer now moves exactly those two shapes on every trim.
* Geometry oracle (`test_book_pdf_geometry.py`): `Sheet.usable_height_mm` now subtracts `FOOTER_STRIP_MM`, the same strip the module already wrote out for the puzzle area. `CLEARANCE_WINDOW_MM` goes from 2.0 to 1.4: every fitted height-bound drawing now has exactly the 1.5 mm lift of spare, which a 2 mm window swallowed (measured: EC-019 checked 165 of a 200 floor, and the two other sweeps passed their window caps with 30 vs 237 and 64 over 157). 1.4 sits above the real 1.21 mm threshold, which is the same at every cell up to the cap (computed from `_rule_widths`).
* `tests/test_book_page_frame.py`: `test_a_puzzle_page_on_that_trim_carries_the_frame_and_its_folio` (10 cm trim). The footer was on 0 of 4 single pages and is now on 3 of 4 (the two 10x10s and the 15x15). The 30x30 d9 is held at the 2 mm floor and overflows. The premise is asserted from the full-box fit. `test_a_height_bound_puzzle_is_fitted_above_the_footer_rule_and_gets_it` (renamed from `..._keeps_the_corner_folio_and_gets_no_footer_rule`): the same height-bound 30x30 now renders its footer rule.
* `test_book_page_numbers.py` `test_a_page_whose_slack_is_too_small_prints_no_folio_rather_than_collide`: its 20x20 fixture now gets a footer (and hits the label collision above), so the fixture becomes a 30x30 d9 held at the floor, the only single page shape that still reaches the footer on that trim. Every other count in it is unchanged.
* `test_book_pdf_levels.py` `test_a_page_with_no_footer_has_no_folio_and_is_refused_loudly`: no Book 1 page lacks its footer any more. The footerless page the reader must refuse is planted with the full-box fit, and the same two sizes are first shown to carry their footer.
* `test_book_puzzle_page_vector.py`: the corpus moves from 51/9 to 60/0 pages with/without a footer, and the rule count from 111 to 120. The 9 page-fit-bound pages gain the footer rule: 111 + 9. The omission arm is held by `test_a_blocked_footer_draws_neither_the_rule_nor_the_number` and `test_the_one_pixel_either_side_of_the_verdict_decides_it`.
* `test_book_page_spec.py` `test_calls_compute_layout_with_the_spec`: the spy takes the keyword, and asserts it is `interior_frame(spec).footer_depth`.
* `test_book_export_interior_cover.py` `CALLEE_EXEMPTION_COST`: 726 -> 727 and 466 -> 467, the one new `interior_frame(page_spec)` call (an import), read off the test's own measurement.

**AC-4 controls** (mutants planted in `src`, then restored):
* Old full-box fit (reserve 0 at both call sites): reds AC-1's test, AC-2's sweep, the held table, both page-frame tests and both corpus counts (7 reds).
* Edge mutant (`footer_depth - 1` at both sites): **only the held table reds**. The footer verdicts cannot see one pixel, because a fitted page has at least 10 px of slack.
* Single-site mutants. Page path only: AC-1 stays green, because the reserved book cell caps the page. Only `test_a_page_with_no_footer_has_no_folio_and_is_refused_loudly` reds, through the no-`cell_sizes` path. `book_cell_mm` only: AC-1 stays green, but the held table, the spy test, both corpus counts and the two layout-equality tests in `test_book_puzzle_page_vector.py` red, because page and book cell disagree.

**AC-5 renders** (100 dpi, `pdftoppm -r 100`): in `~/Documents/nonogram-reviews/CARD-485/`, `before-`/`after-` with `p114`, `p115`, `p139`, `p140` and `twoup-p69-70` (`.png`). These are puzzles 114/115/139/140 on interior pages 113/114/139/140 and the two-up page 70. Caveat for the eyeball: at 100 dpi the fifth and tenth grid rules alias, so which lines look heavy differs between before and after. That is the rasteriser, not the geometry.

**Gate** (every `tests/` and `tests/property/` file whose name holds book/layout/pdf/page_spec/print, plus test_cli, test_kanban_review_record, test_check_ref_resolution, test_suite_profile; `-o addopts= -rfs`, run on bec417ba's tree before the commit): **1 failed, 4509 passed, 1 skipped**. The red is `tests/test_book_landing_page.py::test_the_way_back_from_a_puzzle_keeps_the_sections_and_the_place`, which also reds on the base tree (run alone with src and tests stashed). The skip is `tests/test_book_pdf_memory.py`'s setrlimit, the platform skip. The first gate on the unadjusted tests had 14 reds: the landing page plus the 13 moved above. Test count (`--collect-only -q -o addopts=` over `tests/`): base **10700**, branch **10701**, so net **+1**.

[Review 1/3] Score: 9.0, nothing gating, certified. Seam checked at all 13 `compute_layout` call sites (none missing the reserve, none reserving twice); CLI/A4 layouts hash identically over 882 cases (G-2); owner's book re-measured independently: 15 footerless single pages to 0, same 7 pairs, 12 of 80 sizes shrink 0.39-4.10%, none grow; mutants: reserve dropped (9 red), 1 px less (2), twice (2), page site only (1), `book_cell_mm` only (6); changed goldens derived, not pasted; 569 passed, 0 skipped; net +1. Fixed inline by the orchestrator: F-2 the spare is 17 px (1.44 mm) after rounding, not "exactly 1.5 mm", in the `CLEARANCE_WINDOW_MM` comment and the `_placed_drawing_top` docstring; F-3 `test_a_spec_without_parity_has_no_book_cell` now also asserts `compute_layout` refuses a reserve on a parity-less spec and a negative one (removing the guard reds it). Recorded, not fixed: F-1 on trims up to about 12.4 cm wide the grid-size label overprints the centred folio on pages that newly get a footer: **owner's ruling 2026-11-19: "Narrow trims aren't a concern, we print letter size for now."** F-4 nothing pins that answer pages do not reserve twice (a mutant adding it passed 452 tests): pre-existing, one line here, no card. F-5 the floor gate (`FLOOR_MM` 4.75) could refuse a height-bound size on another book now its cell is up to 4.1% smaller; `book_proof._drawn_pages` keeps the full-box fit.

**Merge gate (orchestrator).** First run cut off by a session end (its lock left behind; holder pid confirmed dead, heartbeat stopped, lock removed). Re-run `make test-gate BASE=main`: 1 failed / 10103 passed / 30 skipped (the expected unarmed count) / 1 xfailed, plus 11 passed marked. The one red, `tests/test_book_landing_page.py::test_the_way_back_from_a_puzzle_keeps_the_sections_and_the_place`, reds on main too (another session's merge) and is outside this card.

**Owner check, 2026-11-19.** After the owner pushed and Render redeployed, the owner re-downloaded the live book's interior: "looks like the footer is fixed".
