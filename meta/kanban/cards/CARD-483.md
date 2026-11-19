# CARD-483: A two-up page stops reserving the corner folio it no longer draws, if that is proved

**Status:** in_progress
**Priority:** P2
**Category:** feature
**Estimate:** 2c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/483-two-up-folio-reserve
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-483
**Source:** roadmap rescore 2026-11-18, wave 2 (IDEA-176, WSJF 1.23); premise re-read against main on 2026-11-19.
**Idea:** IDEA-176
**Wave:** 81
**Created wave:** 81
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/book_pdf_generator.py, tests/test_book_pdf_two_up.py, tests/test_layout_two_up.py, tests/property/test_book_pairing.py
**UI surface:** printed interior (two-up pages)
**Review score:** —
**Started:** 2026-11-19T08:49Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

`_folio_reserve_px` takes 108 px off a two-up pair's lower slot for a corner folio. Since CARD-248 a two-up page draws its folio centred in the footer strip. The corner is used only when `content_bottom` reaches below the footer rule (`_draw_page_frame`'s omission branch). If that branch cannot be reached on a two-up page, the reserve refuses pairs for nothing: 18 pairs at the time of writing (2026-10-18), **before CARD-392's footer change, so the figure is stale**.

## What to implement

1. **Measure first.** Re-run the equal-pair sweep on main (find it from `tests/property/test_book_pairing.py` and `tests/test_book_pdf_two_up.py`) and count the pairs refused only because of the reserve. Record the figure in the card notes.
2. **Stop rule:** if the count is 0, record it, change no code, and close the card as no change.
3. Otherwise, prove the omission branch unreachable for a two-up page, with a control that fails when it becomes reachable (ADR-0039/R3). Include the F-4 one-pixel round-trip residue from CARD-248. Only then drop the reserve for two-up pages.

## Acceptance criteria

* **AC-1**: the re-measured refusal count, with the sweep's own command, is in the notes.
* **AC-2**: if code changed: a test proves a two-up page never takes the corner-folio branch across the sweep, and a planted reachable case reds it.
* **AC-3**: if code changed: the pairs the reserve was refusing now pair, and no single-page layout moves (pin both).
* **AC-4**: renders of three recovered pairs (including the 25 × 10 if it is among them) in `~/Documents/nonogram-reviews/CARD-483` for the owner's visual check after merge.

## Guardrails

* **G-1**: single-page layouts keep the reserve; the corner folio stays where the footer is omitted.
* **G-2**: the vector interior (ADR-0042) and the raster path must agree; change both or neither.

## Worktree notes

**Step 1, the measurement (AC-1), on the branch base before any edit.** The sweep is CARD-248's "depth-1 equal pairs": every
`(columns, rows)` in `MIN_SIZE..MAX_SIZE` (441), both members
`tests/helpers/book_corpus._gutter_grid(c, r, 1)`, on `corpus_book()` (Book 1,
8.5 x 11 in, 12.7/12.7 mm). Each pair is asked exactly as `puzzle_pages` asks
it: `compute_pair_layout(m, m, gen._puzzle_page_spec(5,
gen._pair_cell_mm(p, p, gen.cell_sizes([p, p]))), folio_reserve_px=R,
footer_reserve_px=interior_frame(spec).footer_depth)`, once with
`R = _folio_reserve_px(300)` (= 108, read off the function) and once with
`R = 0`. A pair is "refused only by the reserve" when the first is `None`
and the second is not. Script (scratch, not committed):
`PYTHONDONTWRITEBYTECODE=1 .venv/bin/python sweep.py` from the worktree root.

* **Book 1: 10 of 441.** 75 pair with the reserve, 10 more pair only without
  it, 356 refuse either way. The 10 are 25 x 10..14 (cell 7.3269 mm, 7.3195
  for 25 x 14) and 26 x 10..14 (7.0556 mm); identical with and without the
  book cell map. Every one is also confirmed refused by `puzzle_pages` itself
  (two single plans).
* **The 25 x 10 pair: refused on main; pairs at 7.3269 mm without the
  reserve** (190.5 / 26 mm: realised `PairLayout.cell_mm`, width-bound, not
  the cap).
* Other trims, same sweep and margins (reserve-only / pairing with reserve):
  8.25 x 11 10/70, 8 x 10 3/42, 7.5 x 9.25 2/24, 7 x 10 3/30, 8.5 x 8.5 2/15,
  6 x 9 4/12.
* The backlog's 18 is stale as the card warned (it predates CARD-392's
  footer); not carried.

**The two call sites.** `book_pdf_generator.py`'s `puzzle_pages` passes the
reserve to `compute_pair_layout` -- the only place it enters a pairing
verdict. `_sheet_furniture` passes it into `SheetFurniture.folio_reserve_px`,
where `footer_pointer` uses it as the width to keep the Play-online pointer
clear of the **centred** folio, on every page kind. That second use is not a
corner reservation and is kept. **There is no raster two-up path any more**:
`ab4cdfbd` deleted the raster interior writers (`_draw_page_frame` with
them); every puzzle page, single or two-up, is drawn by
`vector_puzzle_page`/`vector_two_up_page` from the one `puzzle_pages` plan.
So G-2 holds by construction: one walk feeds the only renderer.

**Step 3, reachability (measured, not argued).** The branch is
`SheetFurniture.footer_is_clear` false, i.e. `lower.drawing_bottom >
footer_rule.y`.
* (A) Every pair that pairs, reserve 108 and 0: 17 trims x 3 margin sets
  (12.7/12.7, 6.35/6.35, 19/7) x parity 5/6 x columns 10..30 x rows 10..30 x
  {equal, lower one row taller}: 10890 layouts, max(`drawing_bottom -
  footer_rule.y`) = **0** (touches, never passes).
* (B) F-4, every storable trim height (cm to 2 dp, 10.00..48.00 = 3801), the
  strip's top as `compute_pair_layout` computes it (px -> float mm -> exact
  px): max exact residue below the rule 0.49606 px = 126/254, rounded residue
  **0** on all. Why it cannot round over: the sheet's millimetres are 0.1 mm
  multiples, so the fraction moves in 1/254 px steps and stays < 1/2 by
  `_round_px`'s half-up definition; the float detour is ~1e-13 px.
* (C) Hypothetical bottom margins 5.00..40.00 mm (0.01 mm) on three heights:
  10503 sheets, rounded residue > 0 on **none**. (Production's bottom margin is
  the profile constant; `book_page_spec` stores no bottom margin.)
* Since the lower drawing ends at `round(strip top - gap)` with `gap >= 0`, no
  two-up page can take the corner branch. **Unreachable**, so the code change
  went ahead.

**What changed.** `puzzle_pages` no longer passes `folio_reserve_px` (one
line); docstrings that described the reserve as a live pairing input are
corrected (module docstring, `_folio_reserve_px`, `_draw_folio`'s (c),
`puzzle_pages`, `puzzle_section`). `compute_pair_layout` keeps its
`folio_reserve_px` parameter (default 0, still exercised by
`test_layout_two_up.py`); `layout.py` is not edited. Single pages never
received the reserve (`compute_layout` has no such parameter), so G-1 holds
without a guard of its own; the corner-folio fallback stays for every page
whose content reaches the footer.

**Guard (AC-2)**, `tests/test_book_page_numbers.py::TestTwoUpNeverTakesTheCornerFolio`:
* `test_no_pair_the_walk_makes_reaches_below_the_footer_rule` -- 6 trims x 2
  parities x 21 x 21 x {equal, +1 row} through `puzzle_pages` and
  `_sheet_furniture(...).footer_is_clear`: 1110 pairs, 304 end exactly on the
  rule; floors 1000/250 asserted. Control in the same test: the walk with the
  strip planted one pixel short (`compute_pair_layout` wrapped) makes 20 of 20
  touching pairs take the corner branch. Also pins AC-3: on Book 1 the 10
  recovered pairs pair, 25 x 10 named, and the equal pairs that pair are
  exactly 85 (75 + 10).
* `test_the_strip_never_rounds_below_the_rule_on_any_storable_trim_height` --
  all 3801 heights; control per height: one pixel less strip rounds past the
  rule.

**AC-3, single pages don't move.** Pinned by the page-digest goldens
(`test_book_pdf_memory`, `test_book_pdf_ink_mode`, `test_book_interior_face`
read `load_baseline()`), which pass unedited.

**Other tests the change moved** (each was modelling the reserve the walk
passed): `tests/property/test_book_pairing.py`'s oracle drops its `reserve`
flag, and `test_PropertyTest_BookPairing_ReserveIsTheBookSOwnScaleNotAPageNumber`
(name kept, it is in the wave-close registry) now holds three shapes on the
production walk: 23-col pairs at the 7.5 cap, the 25-col depth-2 pair
(across 27) that the reserve refused now **pairs** at 190.5/27 mm in every
regime (an AC-3 pin), a 26-col pair refuses in every regime.
`tests/test_book_arrange_page_breaks.py`'s hand walk drops the reserve; its
flip measurement re-asks with the footer strip the walk's verdicts used
(it had been re-asked without it since CARD-248, so the comparison was not
"only the clues"): 96 offered, 7/7 flips -> **95, 5/5**. Measured apart: the
strip fix alone on the old walk gives 96, 1/1; the reserve drop alone 95,
12/12. `tests/property/test_book_pdf_geometry.py`'s gap oracle drops the
reserve re-fit. `tests/test_book_export_interior_cover.py`'s AST call census
727 -> 726 / 467 -> 466 (the removed `_folio_reserve_px(self.dpi)` call),
read off the test. The docstring edits shift `book_pdf_generator.py` by
+13 lines; no test pins that module by line (`OUTSIDE_CALLERS_WITH_A_POSITION`
names `book_proof.py`; the two other `book_pdf_generator.py:NNNN` mentions in
tests are prose), and `test_book_export_interior_cover.py` passes in full.

**Mutations (both on 4c1557ad, restored with `git checkout --`, clean
status after).** M1, the reserve put back in `puzzle_pages`: reds
`TestTwoUpNeverTakesTheCornerFolio::test_no_pair_the_walk_makes_reaches_below_the_footer_rule`,
the pairing property above and `test_PropertyTest_ArrangeBreaks_AgreeWithTheGeneratedBook`
(3 failed, 19 passed). M2, the walk's strip one pixel short
(`footer_depth - 1`): reds the guard at the Book 1 10 x 14/14 pair (1 failed).

**Tests run** (`-o addopts= -q -rfs`, from the worktree): two_up, layout_two_up,
page_numbers, qr_slot, puzzle_frame **196 passed**; property pairing,
property two_up, arrange_page_breaks, suite_profile, check_ref_resolution,
browser_fixture_scope **539 passed**; puzzle_page_vector, property
export_interior, property pdf_geometry **69 passed**; export_interior_cover,
pdf_ink_mode, interior_face, pdf_memory **264 passed, 1 skipped** (the known
`setrlimit(RLIMIT_AS)` platform skip). Net test count **+2** (the two guard
tests); every other change edits an existing test.

**AC-4.** `~/Documents/nonogram-reviews/CARD-483/`: two-up pages (PDF + 100
dpi PNG) of three recovered Book 1 pairs drawn by `vector_two_up_page` from
`puzzle_pages`' own plan: 25 x 10 (page 5, 7.3269 mm), 26 x 12 (page 6,
7.0556 mm), 25 x 14 (page 5, 7.3195 mm). They are corpus geometry puzzles
(depth-1 clues), not real pictures; the footer group (rule, pointer, centred
folio) is present on all three.

### Fix round 1 (review cycle 1, 7/10)

* **F-1 (docstrings).** Every `folio_reserve`/`_folio_reserve_px`/"folio
  reserve" mention in `src/` and `tests/` was read; the ones stating the
  reserve as a live pairing input now say it was until CARD-483:
  `layout.py` (`InteriorFrame.page_bottom`, `compute_pair_layout`'s Fix-4
  paragraph, its cost section with the `_tight_pair` sentence, the
  `folio_reserve_px` Arg, the decline comment, `_slot_layout`'s "decision for
  the card that wants to make it"), `book_sheet_vector.draw_sheet_furniture`,
  `book_pdf_generator.FOLIO_RESERVE_DIGITS`. The pointer-width uses
  (`footer_pointer`, `SheetFurniture.folio_reserve_px`,
  `test_book_puzzle_page_vector`) are true today and unchanged. **Beyond the
  docstrings, three test oracles still modelled the reserve re-fit and were
  passing only because their corpora never hit it** (F-2's question):
  `test_book_puzzle_frame._shared_cell_mm`,
  `property/test_book_export_interior._shared_cell_mm` and
  `test_book_qr_slot._two_up`/`_cell` (`_two_up` passed the reserve to
  `compute_pair_layout` and called itself "as `puzzle_pages` passes them").
  All three now model the walk without it; their `RESERVE_MM` /
  `_folio_reserve_px` imports are gone. Comments only in
  `test_layout_two_up`, `property/test_book_two_up`, `test_book_pdf_two_up`,
  `test_book_page_numbers` (two Fix-4 tests that pass the reserve on
  purpose, as the corner fallback's own case). No behaviour change in `src/`.
* **F-2 (cells that grow).** Re-derived with the step-1 inputs, pairs that
  pair both with and without the reserve: **Book 1, 5 of 75 equal depth-1
  pairs change cell**, at both parities: 24 x 10..13 7.25424 -> 7.5 mm (cap),
  24 x 14 7.25424 -> 7.31953 mm (height-bound). Other trims: 8.25x11 5/70,
  8x10 6/42, 7.5x9.25 3/24, 7x10 3/30, 8.5x8.5 0/15, 6x9 1/12 (per parity,
  equal pairs only; the reviewer's 372 is a wider sweep with unequal and
  deeper pairs). Render added: `two-up-24x10-p5-cell7.5000mm.{pdf,png}`. Every
  test that wrote the reserve re-fit into an expected cell was found by the
  F-1 grep and fixed (above); the module runs below are green with them.
* **F-3.** The last assertion is now `worst < 1/2` (the safety claim), with
  the measured 126/254 in a comment. **M4 re-run** (`interior_frame`'s footer
  rule `y=footer_y - 1`, on fc4843f0): **nothing reds** (the class: 2
  passed). That is the right verdict: `footer_depth` is `page_bottom -
  footer_rule.y`, so the strip grows with the rule and production stays
  safe; the only thing M4 reddened before was the exact-equality line.
* **F-4.** The height test's docstring says it models the arithmetic and is
  sound only with the walk test, which reads production's `drawing_bottom`;
  the walk test's docstring says M1 is caught by the AC-3 pins, not the
  footer assertion. Not restructured.
* **F-5 (owner item, pre-existing since CARD-248, not changed).** When a
  pair's vertical slack is under 4 px the rule gap floors to 0 and the lower
  grid's bottom border is stroked on exactly the footer rule's row. Measured
  on Book 1 page 5, equal depth-1 pairs: 14 do it on main (10..23 x 14), 16
  without the reserve (adds 24 x 14 and **25 x 14**). Example:
  `~/Documents/nonogram-reviews/CARD-483/two-up-25x14-p5-cell7.3195mm.png`.
  Owner to decide whether a coincident grid border and footer rule is
  acceptable.
* **F-6.** The height test builds one `Book` and one generator and rewrites
  the stored height per step (`page_spec` reads the column each call, and the
  test asserts the spec's height followed it): warnings for the class 3807 ->
  7, time 0.86 s -> 0.31 s.

**Fix-round mutations (on fc4843f0, restored with `git checkout --`, clean
status after).** M4 above. M1 (reserve back in `puzzle_pages`) against the
guard class plus the three re-modelled oracles (`test_book_qr_slot`,
`test_book_puzzle_frame`, `property/test_book_export_interior`): 1 failed
(the walk test, via the AC-3 pins), 100 passed: those oracles' corpora never
reach a reserve-affected pair, so they agree with either walk; the
discriminating tests remain the guard, the pairing property and the arrange
agreement test (round 0's M1).

**Fix-round tests** (`-o addopts= -q -rfs`): two_up, layout_two_up,
page_numbers, qr_slot, puzzle_frame **196 passed**; property pairing,
property two_up, arrange_page_breaks, suite_profile, check_ref_resolution,
browser_fixture_scope **539 passed** (after a re-run of suite_profile: its
render census had flagged `test_book_puzzle_frame.py`, because a new
docstring spelled ``puzzle_pages``, a render idiom the census greps; reworded,
census green); puzzle_page_vector, property export_interior, property
pdf_geometry **69 passed**; export_interior_cover (in full), pdf_ink_mode,
interior_face, pdf_memory **264 passed, 1 skipped** (setrlimit). Net test
count unchanged by this round (still +2 for the card).
