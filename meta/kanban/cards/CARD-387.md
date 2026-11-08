# CARD-387: Convert or retire the raster interior tests that no queued card owns, and the dot arm (387a; its tail is CARD-416)

**Status:** ready
**Priority:** P2
**Category:** enabler
**Estimate:** 10c (3d)
<!-- Restated 2026-11-08 from the recount at ~/Documents/nonogram-reviews/CARD-387-recount/ (range 8 to 11c). Was 20c (6d) for the whole job; the tail (the convert-after modules, the writer deletion, the prose) is CARD-416 at 6c (2d), range 5 to 8c. The two together are 16c, below the old 20c because the recount found fewer ids and fewer writers. NOT yet priced by a batch; the first module batch re-prices it. -->
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** CARD-322's scope change, owner ruling 2026-11-07 ("Will we have tests just for the sake of tests? will they check something?"), restated 2026-11-08 on the owner's "restate 387 and fix the 207/232 text" after a recount of the tree at CARD-391's tip (`c0de74d8`) and main (`48b1265b`). CARD-322 landed the vector interior flip and kept the raster writers and their class-a/c tests as reference. This card (387a) retires the part of that reference nothing else is about to rewrite; CARD-416 (387b) takes the rest and deletes the writers.
**Idea:** —
**Wave:** —
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** CARD-322, CARD-391 (starts after CARD-391 merges: 391 retires the three QR writers and their QR tests, and edits `book_pdf_generator.py`)
**Touches:** src/nonogram/admin/book_pdf_generator.py, tests/test_book_difficulty_dots.py, tests/test_puzzle_solver_clues.py, tests/helpers/book_corpus.py, tests/test_book_export_interior_cover.py, tests/conftest.py, tests/test_check_ref_resolution.py, meta/profiling/rank_durations.py
<!-- The module list is a derived starting point: the author re-derives the module set with the classifier (`~/Documents/nonogram-reviews/CARD-387-recount/classify_tests_without_interior_bitmap_mode.py`, which EXCLUDES `interior_bitmap_mode`, a KEEP name) as the class-a/c modules minus every module a queued card touches (CARD-392, 207, 229, 230, 232, 233 and CARD-416), and states any difference. Likely members from the recount table: test_book_difficulty_dots, test_puzzle_solver_clues, test_book_export_interior_cover, test_book_pdf_levels, test_book_pdf_memory, test_book_puzzle_page_vector, test_book_detail_page, test_admin_tier_surfaces, test_book_scaffolding, property/test_book_export_interior. -->
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

After CARD-322 the interior is written as PDF operators on every production path. The raster interior writers survive only as a reference oracle and as the subject of class-a/c tests. The owner's rule (2026-11-07): a test is kept only if its claim is still a live product decision; no tests for the sake of tests. Vector is the only writer for the book interior (ADR-0042); the divider stays a bitmap and the cover stays raster.

**What the 2026-11-08 recount found (it replaces the figures this card first carried).** Re-derived with the classifier that EXCLUDES `interior_bitmap_mode` (a KEEP name; the earlier classifier counted its tests as class a):
* Class a + c: **369 node ids are true** on CARD-391's tip (375 raw, 6 of them false positives from `interior_bitmap_mode`); **402 on main** before CARD-391 lands. The card said ~390.
* **+14** `test_puzzle_solver_clues` ids still call `_blank_page`; they are counted apart from the 369.
* **21 raster writers (~2,092 lines)** remain after CARD-391 (three QR writers went with it); the card said 23 / 2,236. All are production-unreachable: their only callers are `produce`'s bitmap arms, gated on a vector kind. `_draw_difficulty_dots` has no caller at all.
* **Saving is at most 84 s per gate (~5%, realistically half of that).** The reason for this work is dead code and the two-writer trap (a reader fixes a raster writer that nothing calls), NOT gate time.
* Ownership: the guide_page group (58 ids) retires with CARD-229/230; the solved_page + answer_key group (103 ids) with CARD-232/233; each of those cards now carries the line "Writes the vector page only: no raster writer, no raster test twin; retires the raster-twin tests of its own module."

**The split.** This card (387a) takes what can be done now, after CARD-391: the dot arm (item 8, option A, with its 27 raster ids), the 14 `test_puzzle_solver_clues` ids, the ~58 "do now" ids in modules no queued card touches, the ~12 unaudited ids, and the switch of the page-obtaining helper. CARD-416 (its tail, 387b) converts the ~62 "convert after" ids in `pdf`, `pdf_band`, `type_floor`, `page_frame`, `page_numbers` and `toc` once CARD-392 and CARD-207 have rewritten those subjects, then deletes the remaining writers and the bitmap arms and restates the docs, ADRs and censuses. Every id figure above is the recount's and is re-derived at dispatch; a different number is the finding.

## What to implement

Work in MODULE BATCHES, each its own commits, each checked green before the next. The first batch re-prices this card: STOP and report if it costs more than 3c.

0. **Re-derive.** Re-run the classifier (the `interior_bitmap_mode`-excluding one) on the tree you start from, after CARD-391 has merged; compare with the recount (369 class a+c, 14 solver_clues ids, 21 writers). A different number is the finding. Resolve the 2 name collisions (one id each in `test_admin_tier_surfaces` and `test_book_scaffolding`).
1. **Point the page-obtaining helper at the vector render** (the existing poppler rasteriser `page_image`, the vector stream writers `answer_page_stream`, `toc_page_stream`, `puzzle_page_stream`, the other `*_stream` functions) in the modules this card owns, and keep every assertion as written. Where the instrument is raster-specific (a spy on `ImageDraw.ImageDraw.text`), re-express it with the `pdf_vector` readers; where the comparator is a raster reference, switch the reference to the vector render. A red that is a real vector/raster difference is a finding to report, not a test to retire: the live decision wins.
2. **Retire only on evidence.** A claim the owner reverted or superseded (cite the commit, card or ADR), or a claim about the bitmap medium itself, is retired with the evidence in the commit message and a named vector survivor for anything still live. An UNKNOWN goes to the owner: list it, do not decide it.
3. **The 14 `test_puzzle_solver_clues` ids** call `_blank_page` as a canvas only; re-point them at a canvas the vector side provides (or at the cover/divider path if that is what they exercise), changing the existing tests, adding none.
4. **The dot arm (item 8 below, option A).** Retire the raster arm and its 27 raster ids with a named survivor; change the arm guard deliberately. Delete `_draw_difficulty_dots` (no caller) in this card. Delete `_set_band` ONLY if, at the start tree, no remaining raster writer calls it (today `_two_up_page` and others do; if any caller remains, delete nothing here and leave `_set_band` to CARD-416).
5. Owner's rule for tests: change existing, add none, verify once. The dot arm's ast cell is a CHANGE to the existing arm guard, not a new test.

## Acceptance criteria

* **AC-A** (every id is accounted for): *Given* the re-derived set of this card's modules, *then* each node id is converted (passes on the vector page with its assertions unchanged or re-expressed with a plant that can fail), or retired with cited evidence and a named survivor where the claim is still live, or reported UNKNOWN; the collected-id difference is exactly that table. (check: review-lens on `--collect-only -q` by `comm`; each survivor verified by `ast` and a plant. No new test is named; the mechanical flip for the whole-set census is owed to CARD-416's AC-15.)
* **AC-B** (no lost claim): the per-node-id table in the report states, for each retirement, why the claim is not a live decision; a retirement with no evidence and no survivor is a deletion and is forbidden. (check: review-lens.)
* **AC-C** (the recount is reproduced): the re-derived class a+c count and writer count are stated beside the recount's (369 / 14 / 21 on CARD-391's tip) with the classifier excluding `interior_bitmap_mode`, and any difference explained. (check: review-lens.)
- **AC-6** (the dot arm, D9 ruled): the raster arm is retired with the vector arm and the answer/TOC no-round-mark assertions as survivors; `test_there_is_one_arm_per_medium_the_product_can_write` is changed deliberately with its reason; the vector arm has a control that reds a dot one pixel off, a missing dot and a wrong radius; the 29 reds are gone and no raster dot drawer remains in `src/`. (test: the existing `TestDifficultyDots_TheVectorArmReadsTheStream` and `test_there_is_one_arm_per_medium_the_product_can_write`, changed here; `_draw_difficulty_dots` absent from `src/` and `_set_band` absent only if no raster caller remains — check: review-lens by `ast` over `src/`, the mechanical absence cell is owed to CARD-416's AC-15, which changes the existing writer-set census rather than adding a test.)

## Guardrails

* **G-0** Writes the vector page only: no raster writer, no raster test twin; retires the raster-twin tests of its own module. This card creates no raster writer and no raster test twin.
* **G-1** No `src/` behaviour change except deleting `_draw_difficulty_dots` (and `_set_band` if safe); the interior stays vector on every production path throughout.
* **G-2** Cover, divider and proof raster tests stay (about 160, carried).
* **G-3** A raster writer is deleted only after the last test that calls it is converted or retired; one commit per deletion step; the layering guard re-derived, not pasted.
* **G-4** No bound widened, no corpus shrunk, no skip or xfail added.
* **G-5** The full suite is the merge gate (this card touches `src/` and `tests/`).
* **G-6** Do not touch modules a queued card owns (guide_page group: CARD-229/230; solved_page + answer_key: CARD-232/233; the convert-after set: CARD-416).

## System contract

* ADR-0042/R1 and R5: the interior is vector; retire-with-named-survivor.
* ADR-0039: controls that can fail.

## Moved from CARD-322 (verbatim; the numbers are CARD-322's, which other cards cite)

### Items

8. **D9 — the dot arm (RULED 2026-11-06, option A below; executable).** Facts: 27 of the 29 reds in `tests/test_book_difficulty_dots.py` are cells reading the interior as bitmaps through `generator.interior_pages(...)` after planting dots with a spy on `_draw_difficulty_dots`/`_set_band` (all fail at one reading site, `'ContentStream' object has no attribute 'convert'`); 2 are by design (`TestDifficultyDots_AnArmWhoseMechanismIsDeadFails::test_each_arms_mechanism_is_still_exercised[raster]` and `::test_each_arms_probe_reports_death_when_its_mechanism_goes`). **Do option (A): retire the raster arm with a named survivor** (the vector arm, `TestDifficultyDots_TheVectorArmReadsTheStream`, and the answer/TOC no-round-mark assertions in `test_book_solved_answer_key.py`), which needs the arm's own guard changed because `test_there_is_one_arm_per_medium_the_product_can_write` holds arms to `PageMedium` and the arm's `remedy` says retiring is not an option: change the guard deliberately (the product no longer writes a dots page in the raster medium for the interior; the cover and dividers carry no dots by the owner's ruling, so option B, re-pointing the raster arm at them, is REJECTED), with the reason written in the test, and keep a control that can fail (a vector dot drawn one pixel off, a missing dot, a dot of the wrong radius must red the vector arm). Derive `RASTER_ARM_FUNCTIONS` from the arm's reachable surface by `ast` while it still exists in the transition (a plant that adds a function and omits it must red); at the end the raster arm and that list are gone and a cell asserts no raster dot drawer remains. Remove `_draw_difficulty_dots` (89 lines, no caller in `src/`) and `_set_band` (48 lines) with the rest of item 16. The vector dot primitive is exercised by the vector arm's planted harness until CARD-207 lands the first real page; say in the card's closing note that NO product page draws dots yet and which cards do.


17. **THE TEST RETIREMENT RULE for the tests that call the deleted writers (the measurement's classes a and c; about 238 plus up to about 159 node ids of about 2,240 in the 41 book-PDF modules, carried; a heuristic, so re-derive).** Run `classify_tests.py <repo_root>` (read-only, in the measurement folder) and `fidelity_to_the_end_state.py`; the classes: **a** = the test calls a deleted writer directly (biggest: `test_book_solved_page` 52 of 54, `test_book_difficulty_dots` 38 + 17 c, `test_book_guide_page` 34, `test_book_qr_slot` 30, `test_book_toc` 25, `test_book_solved_answer_key` 18 + 29 c, `test_book_guide_page_type` 11, `test_book_interior_type_floor` 11 + 19 c, `test_book_page_numbers` 7, `test_book_pdf_ink_mode` 6, carried); **c** = the test compares both media. **RULE:** each class-a or class-c node id is RETIRED with a NAMED VECTOR SURVIVOR in a per-node-id table kept in your report and in the commit message (this card states the rule and the stop conditions, not 400 rows). A survivor exists exactly once (by `ast`), reads the vector page (the content stream, or the poppler render of it, or the text layer), is green at the end state, and has a plant that reds it with `must_red` asserted non-empty first; a class-c test is retired by keeping its vector half as the survivor when that half already asserts the claim on its own. Re-expression into a vector reading is allowed where the claim has a vector subject and no survivor exists yet; a retirement with no survivor is a deletion and is forbidden (G-5). **Stay:** the ~160 cover, divider and proof raster tests (`test_book_cover`, `test_book_divider_pages_option`, `test_book_proof_pages`, the divider assertions in `test_book_pdf_levels`, the `TestNonDrawingPages` baseline tests in `test_book_pdf_memory`) and the ~370 tests that read pages in a way that works in either medium (`pdf_pages`/`page_image`). The two `test_book_proof_pages.py` tests that rebuild page furniture with the deleted `_draw_page_frame`/`_blank_page` are re-pointed at a poppler render of the vector page, or dropped with a named survivor; the 5 proof baselines are NOT touched (D7). **STOP CONDITIONS:** (1) if the class a + c set re-derives to MORE THAN 400 node ids, STOP after the first module batch and report the real size (it is not priced); (2) if a retirement cannot name a survivor that already asserts the claim, STOP on that node id and report it as a lost claim rather than deleting it; (3) never let a "survivor" be a test that is merely green. List, in the report, which of the lost safety nets each survivor replaces (item 18's table).



## Carried from CARD-322's reviews (2026-11-07), for this card's author

* **F5** — the three retired raster-oracle placed-edge guards also covered `tests/test_book_pdf.py`'s OWN placed-edge sites; the surviving classification cell covers only the puzzle-frame and geometry modules. Decide whether `test_book_pdf.py`'s own sites need a guard (the claim is live) and add one with a plant.
* **F6** — `tests/test_book_difficulty_dots.py` runs its raster-arm cells through a `bitmap_medium()` / `raster_interior()` seam and was edited to avoid the frozen render-set grep (`rank_durations.py` / `test_suite_profile`) instead of being added to the snapshot: test code no product path runs. Item 8's text above PREDATES the seam and `TestDifficultyDots_TheInteriorPagesCarryNoDotsYet` (which pins "no interior page carries dots" and stays until CARD-207/233/229); AC-6 must be read against the file as it is, and the arm guard's `remedy` text (still offers option B, rejected) is fixed here.
* **F7** — `BookPDFGenerator.generate_book_pdf` has no caller (derive again; delete only with evidence).
* The dual-medium controls (`_ensure_declared`, `_declare_all`, the lifts in `test_book_pdf.py`, `test_the_raster_twin_of_the_same_page_does_carry_one`) and `_DECLARED_CLIP_DIVERGENCE` + its three consumers (CARD-322 kept both because the raster writers stay): go or change with the writers.
* ADR-0042/R6 is in tension with the kept bitmap-reading tests (not false); R2's comment ("registry holds SEVEN", "unlike R1's the flip is honest") is stale history without a "since" marker: fix both.
* **Estimate:** restated 2026-11-08 to `10c (3d)` (387a) plus `6c (2d)` for the tail CARD-416; both still exceed the 1d sizing cap, which the owner LIFTED for this work on 2026-11-07 ("let's lift the cap"). Worked in module batches; the first batch re-prices it and STOPS if it costs more than 3c.


## Worktree notes
