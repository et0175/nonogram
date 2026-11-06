# CARD-382: Seven interior-reading modules the census never covered, plus two unowned placed-edge reds, go green BOTH ways — carved out of CARD-322

**Status:** ready
**Priority:** P1
**Category:** tech-debt
**Estimate:** 2c (1d)
<!-- Stated in review cycles at DRAFT time, so the card cannot redden tests/test_kanban_review_record.py when it is stamped into a wave (CARD-325 did). Basis, mine and carried: 47 reds in 8 modules, no src/ change, no owner decision. Comparators carried from the CARD-322 premise pass: 29 to 33 reds at 2c landed in 1 cycle (CARD-355, 354, 356), 15 reds at 2c took 2 (CARD-357), 8 to 12 reds at 1c took 1 or 2 (CARD-358, 359, 360), and CARD-379 (18 reds fixed across 5 modules, 2c) took 1. 47 reds is about 1.5 of the 2c slices, discounted because the 15 `test_book_toc` / 16 `test_book_page_frame` reds are formulaic once one reading is converted. This is the edge of 2c: the two `test_book_pdf_two_up` reds carry a stop clause (item 7) precisely so they cannot silently turn this into 3c. NOT priced: any owner ruling, any content oracle, waits behind gates, modules the full suite finds red that the keyword grep behind item 0 did not. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** CARD-322's re-cut, 2026-11-06 (draft kept at `~/Documents/nonogram-reviews/CARD-322/` once applied; the measurements are the re-cut author's, run in a private clone of main at `bb8d1121`), accepted by the owner as "pre-flip card A": the seven modules the five-kind census never covered (45 reds, owned by nobody) plus the unowned reds. Follows the module-slice pattern of CARD-354 to CARD-360 and CARD-379.
**Idea:** —
**Wave:** —
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/test_book_page_frame.py, tests/test_book_toc.py, tests/test_book_page_numbers.py, tests/test_book_qr_slot.py, tests/property/test_book_order.py, tests/test_book_detail_page.py, tests/test_book_puzzle_page_vector.py, tests/test_book_pdf_two_up.py
<!-- Conflict edges, derived by grep over the Touches line of every ready / in_progress / backlog card on 2026-11-06 and not exhaustive: CARD-231 and CARD-289 name tests/test_book_toc.py; CARD-226, CARD-229 and CARD-231 name tests/test_book_page_numbers.py. CARD-229 and CARD-231 depend on CARD-322, which depends on this card, so the order is already serial; whether CARD-226 and CARD-289 depend on CARD-322 was not checked, and a card of theirs that edits those modules first changes this card's starting tree: re-run item 0 at dispatch. CARD-342 and CARD-343 own tests/helpers/page_ink.py, which this card does NOT edit (G-3). -->
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

CARD-322 flips ADR-0042/R1: the last five interior kinds (title, guide, TOC, answer, puzzle) stop being bitmaps. Every card in the ADR-0042 slice (CARD-354 to CARD-360, CARD-379) made the test modules it owned green on today's tree AND under the five-kind probe, so the flip could land on a tree whose readers already read operators pages. The probe census they worked from was 22 modules. **It was not the set of modules the conversion reds.** A keyword grep of `tests/` for the export surface (`export_interior`, `_export_part`, `BookPDFGenerator`, `interior_stream`, `interior_pages`, `section_plan`, `download-pdf`, `render_proof_pdf`, `page_medium`, `_RASTER_DECLARATIONS`) found 25 modules outside the census; running them under the probe (mine, 2026-11-06) found **seven that are red: 45 reds, owned by nobody**, and the same reds at the on-disk end state with the default writer set assembled (E2) and with it left default-deny (E1). The same shape as the 22nd module CARD-338 found. Separately, two reds in `tests/test_book_pdf_two_up.py` are credited by CARD-337 and CARD-360 to CARD-352, whose Touches is `tests/test_book_puzzle_frame.py` only: nobody owns them.

Doing this first (a) lets CARD-322's end-state census be read without 47 unowned reds in it, (b) is the only part of CARD-322's residue that is both free of owner decisions and free of `src/` change, and (c) keeps CARD-322 inside the board's `sizing.max_estimate` of 1d once the other pre-flip pieces are out.

## The population it owns (47 reds; mine, derived 2026-11-06 under the five-kind probe; a CARRIED figure until you re-derive it)

| module | red / passed | the cause line the red prints | family |
|---|---|---|---|
| `tests/test_book_page_frame.py` | 16 / 13 | `'ContentStream' object has no attribute 'copy'` (x2), `'convert'` (x1), then the later assertions behind them | a bitmap reader handed a stream |
| `tests/test_book_toc.py` | 15 / 62 | `assert [] == ['How to Solve…', 'Solutions']`, `StopIteration`, `IndexError`, `assert 0 == 1`: TOC rows read off the page come back empty | text read off a bitmap finds nothing on an operators page |
| `tests/test_book_page_numbers.py` | 5 / 12 | "no page carried the frame's centred folio", "almost every page carried a checkable folio", `KeyError: 9` | the folio is read off a bitmap |
| `tests/test_book_qr_slot.py` | 4 / 102 | "only 0 QR footer lines were drawn", "no page of the book set the invitation at all" | same |
| `tests/property/test_book_order.py` | 2 / 0 | `'ContentStream' object has no attribute 'size'` | a bitmap reader handed a stream |
| `tests/test_book_detail_page.py` | 2 / 35 | "every member drew one page", `KeyError: 'puzzle_000001'`: band numbers are read off the exported pages | same family |
| `tests/test_book_puzzle_page_vector.py` | 1 / 64 | `TypeError: page 1 is a vector puzzle page, but arrived as Image` | the `_write_pdf` refusal, CARD-379's M3 shape |
| `tests/test_book_pdf_two_up.py` | 2 / 50 | `assert 0.2313 <= 0.0423 (+1e-9)` at the retired-fixed-top-edge control | a placed-edge reading, ink first line against a half-pixel bound |

The node ids (the first 45 are the seven modules, the last 2 are `pdf_two_up`):

```
property/test_book_order.py::test_PropertyTest_BookOrder_GroupedByTierUnderAnyEditSequence[memory] and [db]
test_book_detail_page.py::TestBookDetail_NumbersPuzzlesLikeTheBook::test_each_number_is_the_band_the_exported_interior_prints
test_book_detail_page.py::TestBookDetail_UndrawableMemberHasNoNumber::test_the_other_numbers_still_match_the_pdf
test_book_page_frame.py:: (16) HeaderRuleIsOnTheSameBaselineEverywhere x3, FooterCarriesSizeAndFolio x4, PuzzleAreaHasOneDefinition x3, TwoUpCarriesTheWholeFrame x2, TheHairlineSitsOnTheFloorUnderTheHeaderRule x1, ShortestTrimStillHoldsTheFrame x2, FooterIsOmittedWholeWhereContentReachesIt x1
test_book_page_numbers.py:: EveryInteriorPageShowsItsOwnNumber x2, FoliosMatchInteriorStreamsOwnArithmetic x1, ParityHoldsWithTheTocInserted x2
test_book_puzzle_page_vector.py::TestPuzzlePage_CarriesNoImageXObject::test_the_raster_twin_of_the_same_page_does_carry_one
test_book_qr_slot.py:: CarriesItsCaptionAndLink x2, TwoUpFooter_CarriesBothPuzzlesLinks x1, TwoUpFooter_APairThatCannotFitSplitsIntoSinglePages x1
test_book_toc.py:: (15) ListsSectionsNotPuzzles x2, RowsDeclareTheGroupsTheyOpen x3, PageNumbersMatchTheWalk x2, RangeRowsFollowTheLevelRuns x1, SkipsEmptyLevels x3, PageNumbersSurviveTheTitlePage x4
test_book_pdf_two_up.py::TestBookPdf_TwoUpUpperSlotDoesNotShareTheSinglePagesTopRow::test_the_control_the_retired_fixed_top_edge_would_share_the_row
test_book_pdf_two_up.py::TestBookPdf_TwoUpUpperSlotDoesNotShareTheSinglePagesTopRow::test_that_row_is_the_top_margin_plus_the_band
```

**All 47 are green unlifted** (the premise: they are red only once a page is operators). `tests/test_book_toc.py` is 15 red under the probe and 18 at the default-deny tree (E1); the 3 extra are the flip card's seam, not yours (G-5).

## What to implement

0. **Re-derive the population before editing anything, and state the number you get.** Run the eight modules unlifted, then under the probe, then against the on-disk end state (instruments below); a different count is the finding. The seven-module list comes from a keyword grep, which is not a census: **if your run, or the full suite's gate run, finds another red module that reads an interior page, name it in your report and card it; do not absorb it** (G-3).
1. **Convert each reader to read the page in the medium the page is.** The pattern is CARD-354 to CARD-360's and CARD-379's: re-express against the content stream (or the poppler render of it through `tests/helpers/pdf_pages.py`) where the claim has a subject in both media; where a claim's only subject was a bitmap that no longer exists, retire it with a NAMED survivor (ADR-0042/R6) listed per node id in your report. Re-expression is the default; every weakening carries its measured residue written IN THE TEST (ADR-0039/R3). Say per module which you chose and why.
2. **`tests/test_book_page_frame.py` (16) and `tests/property/test_book_order.py` (2):** both hand a `ContentStream` to a bitmap reader (`.copy`, `.convert`, `.size`). Read the stream's own geometry (its `MediaBox`) or the rendered page; for any placed-edge claim use `frame_centre_of`, not the first inked line (CARD-336's oracle, `tests/helpers/page_ink.py`, consumed and not edited).
3. **`tests/test_book_toc.py` (15), `tests/test_book_page_numbers.py` (5), `tests/test_book_qr_slot.py` (4), `tests/test_book_detail_page.py` (2):** these read TEXT off the page (TOC rows, folios, QR captions, band numbers). On a raster page that text is found by a raster reading; on an operators page it is in the stream. Read it from the stream (the project's `tests/helpers/pdf_vector.py` readers exist for this; CARD-355 to CARD-360 used them), and keep each test's claim, not its mechanism. Beware lesson 2 of the CARD-322 premise pass: never compare across media (a `!=` between a poppler render and a Pillow bitmap is vacuously true).
4. **`tests/test_book_puzzle_page_vector.py` (1), the `_write_pdf` refusal:** `TestPuzzlePage_CarriesNoImageXObject::test_the_raster_twin_of_the_same_page_does_carry_one` hands a bitmap to a vector declaration. Make it green both ways with the SAME name. READ how CARD-379 made the two refusal tests in `tests/test_book_pdf_memory.py` green both ways (its Worktree notes) and say whether the same move applies; do not assume it. **Do not rename `TestPuzzlePage_DrawsTheDrawingAndTheBandAndNoSheetFurniture` in this module: that rename is CARD-322's named G-5 exception.**
5. **Matched controls.** Every re-expressed test has a plant that re-breaks the claim it states and a matched control green in the same run, with `0 skipped`; assert `must_red` non-empty before the plant runs. A plant is verified to be the intended site by `ast` (CARD-358's cycle-1 lesson).
6. **The unowned geometry reds are NOT in this card.** `tests/property/test_book_pdf_geometry.py` has four reds under the probe; this card edits none of them. Two are CARD-350's by its text, a third is the same poppler trim-height mechanism that CARD-350's text does not name (an addendum to CARD-350 was drafted for it), and the fourth is CARD-336's declared `1 x HALF_PIXEL_MM` site (F-4), which cannot be closed without moving a multiple that G-2 forbids moving and needs a decision. They are named here so nobody believes this card closes them.
7. **The two `tests/test_book_pdf_two_up.py` reds.** `TestBookPdf_TwoUpUpperSlotDoesNotShareTheSinglePagesTopRow::test_the_control_the_retired_fixed_top_edge_would_share_the_row` and `::test_that_row_is_the_top_margin_plus_the_band` compare an ink first line against a bound of `0.0423 mm` (half a device pixel). Measure first, in both media, with `frame_centre_of`-style boundary readings, what the cell can honestly assert. **STOP CLAUSE: if neither the ink reading nor a boundary reading meets the bound in BOTH media (the shape CARD-336 measured and declared as its F-4: a six-line frame rule whose centre is a half-integer on a different side in each rasteriser), do NOT widen the bound and do NOT move a multiple (G-2).** Write the measured figures into the test as a declared residue, leave the two reds as the only reds of this card, and report them as a decision for the owner. That outcome does not fail this card; it reduces it to 45 reds and a recorded decision.

## Acceptance criteria

- **AC-1** *Given* the five-kind probe, *then* the red count for each of the eight modules is stated before and after, and the 47 reds are 0 except for any item-7 stop-clause outcome, which is stated per node id with the measured figures.
  (check: review-lens — a stated count or a mutation run is not a test, and no committed test can name it: its instruments live in the worktree and the force-add gate forbids tracking them. **No card owes a flip.**)
- **AC-2** *Given* the eight modules, *then* each is green UNLIFTED and green under the PROBE, with every skip attributed by reason (`-rEfs` as ONE flag; none of these modules is expected to skip).
  (check: review-lens)
- **AC-3** *Given* the end state (the five entries deleted and the default writer set assembled, no probe, in a private clone), *then* `scratchpad/card338/fidelity_to_the_end_state.py` reports these modules at 0 in the E2 column. The E1 column (default left deny) is NOT this card's: CARD-322 owns that seam.
  (check: review-lens)
- **AC-4** *Given* each re-expressed or retired test, *then* it has a stated disposition, a plant that re-breaks it and a matched control green in the same run, and each retirement names a survivor that exists exactly once (by `ast`), reads the converted medium and is green.
  (test: named by the implementation, per module; state each)
- **AC-5** *Given* `tests/test_book_puzzle_page_vector.py`'s refusal test, *then* it keeps its name and is green both ways.
  (test: `TestPuzzlePage_CarriesNoImageXObject::test_the_raster_twin_of_the_same_page_does_carry_one`)
- **AC-6** *Given* the branch, *then* the collected node-id set against the cut differs only by added tests and by retirements listed per node id with their survivors; nothing is skipped, xfailed or merged; no parametrize id is dropped unlisted.
  (check: review-lens on a `pytest --collect-only -q` set difference, old versus new)
- **AC-7** *Given* any other module the author's census or the gate finds red that reads an interior page, *then* it is named in the report with its cause and carded, not repaired here.
  (check: review-lens)

## How to measure, and the instruments are not yours to build

**Re-derive your own population before implementing anything** (`-rEfs` as ONE flag; `-o addopts=` as two argv items; the whole environment inherited, since a stripped `PATH` makes a platform-gated test SKIP, which reads as a pass). The instruments are committed in the repo and are not yours to build or edit: the five-kind probe is `scratchpad/card338/probe_five_kinds.py`, loaded with `-p` and `PYTHONPATH=scratchpad/card338`; the per-module census is `scratchpad/card338/census_five_kinds.py --only <module> [<module> ...]` (run from the worktree root; `--only` accepts any module, the built-in lists are only its default); the on-disk end-state comparison is `scratchpad/card338/fidelity_to_the_end_state.py <module>`, which prints E0, E1, E2 and the probe side by side (its `-rfs` omits the `E`, so read errors from pytest's summary line); `scratchpad/card338/derive_delitem_sites.py` lists `delitem` sites. Do not edit `classify_reds.py`; CARD-338 is closed. The probe lifts the five declarations AND rebinds the generator's default writer set, so it equals the E2 tree, not the E1 tree. **The hang guard's default is 300 s (CARD-381); set nothing about `NONOGRAM_TEST_HANG_SECONDS`.** A killed run can leave a test file mutated: check `git status` and restore it before the next run. Do not kill processes by name (`pkill -f`): other cards' runs share the machine.

## Guardrails

- **G-1** — **No `src/` change.** If your measurement indicts the generator, that is a finding and a routing, not an edit.
- **G-2** — **Do not widen a bound or a tolerance to make a cell pass, and do not move a multiple** (`EDGE_TOLERANCE_MM`, `EDGE_TOLERANCE_PX`, `HALF_PIXEL_MM` and its 3/3/2/1 multiples, `PLACEMENT_BOUND_MM`, the 0.1 mm parity bound). A residue you cannot close is declared in the test with its measurement and reported (item 7).
- **G-3** — **Stay inside your `Touches`.** Do not edit `tests/helpers/*` (`page_ink.py` belongs to CARD-342 and CARD-343; `pdf_pages.py`, `two_up_ink.py`, `round_ink.py` to their cards), `tests/property/test_book_pdf_geometry.py` (CARD-350's) or `tests/test_book_puzzle_frame.py` (CARD-342's and CARD-352's). A module that needs more is a finding, raised. Planting a mutant into another module and restoring it byte-identically (SHA-256 pair) is a measurement and is allowed.
- **G-4** — No test deleted, renamed, skipped or merged, parametrize ids included (derive the node-id set difference with `-o addopts=` against the cut and report it), except a retirement under ADR-0042/R6 with a named survivor listed per node id in your report. The F-307 rename is CARD-322's and not yours.
- **G-5** — Do not make the default-deny seam green here. These modules are judged unlifted, under the probe and at E2; their E1 reds belong to CARD-322's item 1.
- **G-6** — No new runtime dependency (ADR-0006/R1).
- **G-7** — A full suite needs the board's lock; never set `NONOGRAM_IGNORE_FULL_SUITE_LOCK`, never redirect `NONOGRAM_FULL_SUITE_LOCK`; you do not run the full suite.
- **G-8** — Do not connect to the production database.
- **G-9** — Take no timing measurements and report no durations (the owner's standing ruling: the clock measures the queue, not the work).

## System contract

- ADR-0039/R1 — a claim needs a control that can fail (check: review-lens)
- ADR-0039/R2 — a guard's set is derived from an authority the runtime can enumerate; where none exists it defaults to **deny** (check: review-lens)
- ADR-0039/R3 — a declared bound carries a reason and a measured residue, written in the test (check: review-lens)
- ADR-0039/R4 — a figure recomputed and refuted is retracted everywhere it was written (check: review-lens)
- ADR-0042/R1 — interior pages are operators (check: review-lens)
- ADR-0042/R6 — a claim that has no subject in the converted medium is re-expressed against the content stream or retired with a named survivor (check: review-lens)

## Worktree notes

(none yet)
