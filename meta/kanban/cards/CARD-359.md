# CARD-359: The `page_ink` reader meets a content stream — 6 reds, one cause signature, four modules nobody else touches

**Status:** in_progress
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1c (0.5d)
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/359-page-ink-reader
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-359
**Source:** Module-sliced out of CARD-337 at the decompose station, 2026-11-04, on the owner's "module slicing" instruction. CARD-337's own item 0 refuted its premise three ways and its round then derived the mechanism x module cross-tab; that table reconciles to 143 reds in both directions. The axis was changed from mechanism to MODULE because the round measured that a mechanism-sliced partition cannot run concurrently at all -- nine of thirteen modules split across mechanisms, `tests/test_book_pdf_band.py` would have needed five separate cards to edit it, and nothing could have run beside the M10 card. The file axis is the one the scope gate enforces.
**Idea:** —
**Wave:** 79
**Created wave:** 75
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/test_book_divider_pages_option.py, tests/property/test_book_pairing.py, tests/test_book_proof_pages.py, tests/property/test_book_export_interior.py
**Review score:** —
**Started:** 2026-11-05T16:07Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## The population, from CARD-337's cross-tab

**6 reds, and all six print the SAME line** — which makes this the cleanest card of the set:

```
page_ink.py: AttributeError: 'ContentStream' object has no attribute 'convert'
```

| module | M7 reds | exclusively this card's? |
|---|---|---|
| `tests/test_book_divider_pages_option.py` | 3 | **yes** |
| `tests/property/test_book_pairing.py` | 1 | **yes** |
| `tests/test_book_proof_pages.py` | 1 | **yes** |
| `tests/property/test_book_export_interior.py` | 1 | **no** — CARD-322 holds its other 6 (M1 5, M2 1) |

**One mechanism, one signature, three exclusive modules.** The only shared file is
`property/test_book_export_interior.py`, where CARD-322 owns 6 of the 7 reds — so **this card
and CARD-322 must not run concurrently**, and CARD-322 runs last by design anyway.

## What this actually is

`tests/helpers/page_ink.py`'s reader is handed a page and calls `.convert(...)` on it. On a
vector page that object is a `ContentStream`, which has no `convert`. **The reader is
medium-blind at the point of the call** — it does not ask what it was given.

**CARD-336 built the precedent for the answer**: its `frame_centre_of` reads a boundary in
**both** media and holds no medium constant, and `TestEdgeOffset_ThePixelOraclesStillReadPixels`
keeps the raster oracles reading pixels byte for byte. ADR-0042/R6 exempts those independent
pixel oracles **by name**, so the route here is not to convert them — it is to make the call
site state which medium it needs, or to re-express the claim against the stream.

**Do not convert `page_ink.py`'s raster oracles.** That is CARD-336's AC-2 and CLAUDE.md's
cross-check requirement, and this card's `Touches` deliberately excludes `page_ink.py` itself.

## What to implement

1. **Decide, per call site, whether the claim needs pixels or needs a coordinate.** Four sites,
   one signature — if they split, that is a finding.
2. Where a claim needs pixels on a page that has none, **retire it with a named survivor**
   (ADR-0042/R6). Where it needs a coordinate, re-express against the stream.
3. **Do not edit `tests/helpers/page_ink.py`** — not in `Touches`, and its oracles are exempt by
   name. If the honest fix requires changing it, that is a finding and a routing.

## Acceptance criteria

- **AC-1** *Given* the five-kind probe, *then* all four modules' M7 reds are closed or carry a
  stated ADR-0042/R6 disposition, and the count is stated before and after.
  (check: review-lens — a stated count or a mutation run is not a test, and no committed test can name it: its instruments live in the worktree and the force-add gate forbids tracking them. **No card owes a flip.** Restated 2026-11-05 on CARD-358's F-004.)
- **AC-2** *Given* the four call sites, *then* the card states per site whether the claim needs
  pixels or a coordinate — and if they are not all the same, says so.
  (check: review-lens)
- **AC-3** *Given* `tests/helpers/page_ink.py`, *then* it is **unchanged** (`git diff` empty) and
  `TestEdgeOffset_ThePixelOraclesStillReadPixels` is green **unmodified**.
  (test: `TestEdgeOffset_ThePixelOraclesStillReadPixels`)
- **AC-4** *Given* `property/test_book_export_interior.py`, *then* its 6 CARD-322 reds (M1 5,
  M2 1) are **still present and attributed**, not absorbed.
  (check: review-lens — the claim is that six REDS in a module this card does not own are still red under the
  probe; a committed test cannot assert a red, and a census count is an instrument run whose instruments live
  in the worktree and the force-add gate forbids tracking them. **No card owes a flip.** Restated 2026-11-05,
  the same disposition CARD-358's F-004 gave the sibling cards' markers.)
- **AC-5** *Given* each repair, *then* a plant re-breaks it with its matched control green in the
  same run and `0 skipped`.
  (check: review-lens — a stated count or a mutation run is not a test, and no committed test can name it: its instruments live in the worktree and the force-add gate forbids tracking them. **No card owes a flip.** Restated 2026-11-05 on CARD-358's F-004.)

## How to measure, and the instrument is not yours to build

**Re-derive your own population before implementing anything.** The instruments are committed:

- `scratchpad/card338/census_five_kinds.py` — the driver (drives `probe_five_kinds.py`). **Run
  it, do not rebuild it.** CARD-338 owns, committed and refusal-proved it.
- `scratchpad/card338/classify_reds.py` — the mechanism taxonomy.
- `scratchpad/card337/cross_tab.py` — the mechanism × module table. It **imports** `RULES` /
  `classify` from `classify_reds.py` rather than restating the taxonomy; keep that property if
  you extend it.

**Two hazards in those instruments, both measured:**

1. **`classify_reds.py` is NOT filter-agnostic.** Faithful on the five-kind dump (143/143, exit
   0, no "other" group). On a `PUZZLE`-only dump of the same thirteen modules it leaves **13 of
   78 unclassified and exits 1** — loud, but only if you read the exit code. **Scope nothing
   from a `PUZZLE`-only reading.**
2. **A mechanism census of the UNPLANTED tree is not the census after a repair.** Measured:
   `pdf_band` shows **zero** byte-identity reds unplanted, and **three** among the survivors
   once the `interior_images` seam is planted. So your post-repair survivors may carry
   mechanisms your pre-repair census does not list. Re-census after your repair, not only
   before.

**And `-rfs` omits ERRORs — use `-rEfs`.** That matters more here than usual: **21 of the 40
M7d reds board-wide print as `ERROR at setup`**, fixture-raised, so one repair flips many node
ids at once and one plant can re-break many. Clear `addopts = "-q"` with `-o addopts=` as **two
argv items**. The worktree has no `.venv` — use
`/Users/omelnikova/PycharmProjects/PythonProject4/.venv/bin/python`.

## Guardrails

- **G-1** — **No `src/` change.** Every product-behaviour red in this module family is routed to
  **CARD-322** (M1 delitem, M2 expected-side gap, M3 `Image`-arrived-as-vector, M3b the cp1252
  title refusal). If your measurement indicts the generator, that is a **finding and a routing**,
  not an edit.
- **G-2** — **Do not widen a bound or a tolerance to make a cell pass.** `EDGE_TOLERANCE_MM`,
  `EDGE_TOLERANCE_PX` and `HALF_PIXEL_MM` are not yours to move.
- **G-3** — **Stay inside your `Touches`.** The module partition is what makes these cards
  concurrently runnable; a card that reaches into a sibling's module destroys that property.
  Planting a mutant into another module and restoring it byte-identically is a measurement and
  is allowed — the SHA-256 pair is the proof — but leaving an edit there is the violation.
- **G-4** — No new runtime dependency (ADR-0006/R1): stdlib + Pillow + NumPy is closed.
- **G-5** — Take no timing measurements and report no durations; other work shares the machine.
- **G-6** — A full suite needs the board's lock (`meta/kanban/.full-suite.lock`, structured,
  identity is the **worktree**, no pid). **Never** set `NONOGRAM_IGNORE_FULL_SUITE_LOCK` and
  never redirect `NONOGRAM_FULL_SUITE_LOCK` — the guard fires in `pytest_configure` for **any**
  selection, so a redirect blinds a file-scoped run to a gate that *is* holding it.
- **G-7** — **G-8 standing: do not connect to the production database.** `conftest.py` refuses
  by URL text before connecting; do not widen or bypass `_refuse_unless_test_database`.

## System contract

- ADR-0039/R1 — a claim needs a control that can fail (check: review-lens)
- ADR-0039/R2 — a guard's set is derived from an authority the runtime can enumerate; where none
  exists it defaults to **deny** (check: review-lens)
- ADR-0039/R4 — a figure recomputed and refuted is retracted everywhere it was written
  (check: review-lens)
- ADR-0042/R1 — interior pages are operators (check: review-lens)
- ADR-0042/R6 — a claim that has no subject in the converted medium is re-expressed against the
  content stream or retired with a named survivor (check: review-lens)

## Premise re-verified 2026-11-05 (CARD-354, CARD-355 and CARD-324 landed since this card was written)

Read against current `main`, by the orchestrator. Nothing here changes an AC except the AC-4 marker restated above.

- **Not measured, and yours to measure first:** the six reds and their one signature. Re-derive them with
  `census_five_kinds.py --only <module>` for each of the four modules before implementing anything, and say which
  figures are yours. The signature was last read by CARD-337's round.
- **The shared-reader defect is FIXED on `main`** (CARD-355, merge `e4849464`: `rendered_page` in
  `tests/helpers/pdf_vector.py` now reads the page it was asked for, where it used to return the first
  `page-*.png` in a shared directory). Two of your four modules import `pdf_pages`
  (`tests/test_book_proof_pages.py` and `tests/property/test_book_export_interior.py`). The CARD-355 author measured
  both under the probe, old helper against fixed: **no change in either** (`test_book_proof_pages` 1 failed and
  `property/test_book_export_interior` 7 failed, both before and after; carried, not mine). So these M7 reds are
  not that defect. It does mean a vector page you read through `pdf_pages` after the first now reads as itself, so
  re-check any claim in these modules that was green while reading a vector page through it.
- **The label is not the mechanism, twice over.** CARD-355 and CARD-356 each found that their M10 and M7 buckets were a
  reader defect plus a template, and that the classifier's rules key on a failure shape or a string, not a cause.
  Here the single signature `page_ink.py: AttributeError: 'ContentStream' object has no attribute 'convert'` is a
  better key than most, but classify per call site by reading it, not by the label, and expect `classify_reds.py`
  not to read this family (it was not filter-agnostic and CARD-338 is closed; do not edit it).
- **`page_ink` appears on 1 + 1 + 3 + 1 LINES of your four modules** (`grep -c`, so imports and comments count:
  `test_book_divider_pages_option` 1, `property/test_book_pairing` 1, `test_book_proof_pages` 3,
  `property/test_book_export_interior` 1). That is a count of mentions, not of call sites: read each to see whether it
  is a call, an import or a comment before you say "four sites". The card says four sites; the mention count is six.
  Reconciling the two is the first thing to do (AC-2).
- **AC-3's test is in a file this card does not touch.** `TestEdgeOffset_ThePixelOraclesStillReadPixels` lives in
  `tests/test_book_pdf.py`, not in `Touches`: run it unmodified, as the AC says, and do not edit that file.
- **Sequencing stands:** `tests/property/test_book_export_interior.py` is shared with CARD-322, which runs last and
  must not run concurrently with this card.
- **Precedent for the disposition vocabulary:** CARD-355 and CARD-356 each landed with per-site tables of
  re-expression versus retirement-with-named-survivor, a stated-after-the-fact census, and plants with matched
  controls. Read their records on `main` (`meta/kanban/cards/CARD-355.md`, `CARD-356.md`) before writing yours.

## Worktree notes

[Author round, commit `e022d697`] Verified by the orchestrator: tip `e022d697`, one commit over the cut `a32eb8bf`, worktree clean; exactly the four Touches files (`tests/property/test_book_export_interior.py` +22, `tests/property/test_book_pairing.py` +11, `tests/test_book_divider_pages_option.py` +86, `tests/test_book_proof_pages.py` +98; 187 insertions, 30 deletions); `src/`, `tests/helpers` (so `page_ink.py` unchanged), `tests/test_book_pdf.py`, non-test and `meta/` diffs all 0; the four modules unlifted give 205 passed (matches the author), and `TestEdgeOffset_ThePixelOraclesStillReadPixels` gives 4 passed unmodified (AC-3). Author-reported, not re-run by me: census under the probe, divider 3 red -> 0, pairing 1 -> 0, proof 1 -> 0, export_interior 7 -> 6 (the six left are CARD-322's, unchanged: five `KeyError: PageKind.TITLE` in `TestInteriorReadings_TheStreamArmIsReached` and one "interior page 2 is written as operators but no vector guide writer" assertion; the one of the seven that was this card's, `test_PropertyTest_BookExport_ParityCountsFromTheTitlePage`, is closed); skips 0 and unaccounted 0 in every run; the four modules together probe-scoped 6 failed / 199 passed / 0 skipped, unprobed 205 passed / 0 skipped. NOT the shared-reader defect: both `pdf_pages` modules were run probe-scoped before any change with the CARD-355 fix present and gave the same 1 and 7 reds as CARD-355's author measured; the cause line is `page_ink` reading a `ContentStream`.

AC-2, the call-site reconciliation: four SITES, six MENTIONS. The six mentions are 3 import lines (divider, proof, export_interior) and 3 docstring mentions (pairing 1, proof 2), none on a red path; the four red paths are `drawing_of` in two divider test bodies (3 reds), `drawings_of` via `two_up_ink` reaching `page_ink`'s `_dark` (pairing), `_foot_strip` calling `drawing_of` (proof), and `drawings_of` in the title-page parity test (export_interior). FINDING: the sites SPLIT, which the card said would be a finding: divider "which side" needs pixels, divider "how far" needs a coordinate, pairing needs pixels (extent in whole cells), proof needs neither (it needs what the page says), export_interior parity needs a coordinate. Dispositions: divider side = `interior_images` plus `drawing_of`, sign of the ink centre only (medium-blind: the two media differ by about 2 px against an offset of 59); divider magnitude = re-expression, `frame_centre_of(...).frame_left` with odd minus even asserted equal to gutter minus outside within the SAME 2 px bound (the per-page bound read 56/-62 px in vector against 58/-60 in raster, expectation 59.06, so vector missed by 3.06 px; the bound was NOT widened, G-2; the common centring bias cancels; it asserts all drawings are one width); pairing = `page_image` on the pages measured, whole-cell ratios absorb the 1-3 px; proof = RETIREMENT for operators pages with the raster arm keeping byte identity, the vector arm asserting no note markers in the text operators the page shows and failing if there is no text at all, named survivor `test_nothing_on_the_book_export_path_imports_this_module`, guarded by a new `test_the_cited_survivor_still_resolves` (by `ast`, exactly once; the author replayed its logic on a renamed and a doubled copy of the file, the committed file itself was not mutated); export_interior parity = `page_image` plus `frame_centre_of(...).frame_left` with the same 0.1 mm bound. SECOND FINDING (divider page selection): the walk used to skip whatever `drawing_of` declined, but under poppler the vector guide's second page reads as a 7 x 1 "grid" (page 3, offset 160.5 px); the measured pages now come from the plan's `PuzzlePagePlan`s and the last `len(puzzles)` pages, and a `ValueError` on one is a failure.

Plants (all `-p` plugins, no source file edited, every run with the probe and 0 skipped): divider `parity` 3 red, `halfgutter` 2 red, gutter shortened 0.2 mm 2 red and 0.3 mm 2 red (on the equal-width precondition) but **0.1 mm 0 red, by design** (within the 2 px bound); pairing `stalepayload` 1 red, `nopair` 3 red (but the interior test reds on the page-count assertion, so `nopair` does NOT exercise the pairing ink assertion; `stalepayload` does); proof `note` 1 red (control `test_the_stream_reading_flags_a_note_written_into_the_page`); export_interior `parity` 7 red (the card's 1 plus CARD-322's 6), gutter shortened 0.05 and 0.2 mm still green and red from 0.4 mm up (the 0.1 mm bound is not blind to a coarse shift but is to a fine one). Latent site for CARD-322 (unmeasured): the first export_interior test is red on CARD-322's early abort before it reaches its own `drawing_of(page).left` and `page.crop(...).convert("L")` answer-page reads, which have the same signature and will surface when CARD-322 closes that abort; not edited, because that test is a CARD-322 red. [CORRECTED 2026-11-05 under ADR-0039/R4 on the cycle-1 review: this is MISLABELLED. Pages in that test come through `pdf_pages`, which already rasterises, so there is NO `ContentStream.convert` AttributeError there. With the guide-page abort skipped in a scratch copy the test reds at `_measured` with `page 6 draws its puzzle at 12.446 mm, not 12.700 mm`, i.e. the 3 px (0.254 mm) ink-first-line gap against the 0.1 mm bound, the same family as the parity fix. The routing for CARD-322 is on that card.] Two unmeasured spots: the other claims in `test_book_proof_pages` and `test_book_export_interior` that were green while reading raster pages have no per-claim list, and the unprobed-versus-probed difference was run per module, not per test. No SCOPE+ file.

[Review 1/3] Score: **7.6 - CHANGES REQUESTED** (threshold 8.0), at tip `e022d697`. All five ACs hold; the score is below threshold because the divider "how far" claim got WEAKER without the residue being declared. Derived by the reviewer: probe-scoped on the four modules the cut gives 12 failed / 191 passed (divider 3, pairing 1, proof 1, export_interior 7), the tip 6 failed / 199 passed / 0 skipped; unprobed the cut 203 passed and the tip 205 (two new tests); the six that remain are exactly the six `test_book_export_interior.py` reds already failing at the cut (five `KeyError: PageKind.TITLE` plus the "interior page 2 is written as operators but no vector guide writer" assertion: the same six node ids at cut and tip); the seventh, `test_PropertyTest_BookExport_ParityCountsFromTheTitlePage`, is closed (without `frame_centre_of` it reds with the 3 px ink-versus-boundary gap against the 0.1 mm bound). The media diff is measured and empty at test level: exactly the six CARD-322 tests change outcome between media, so the author's second "unmeasured spot" is closed. The site list is right (four red-path sites, six mentions) and the split holds; the card's `page_ink.py`, `tests/test_book_pdf.py` and `tests/helpers` diffs are empty; `TestEdgeOffset_ThePixelOraclesStillReadPixels` 4 passed unmodified. Author plants re-fired and confirmed: divider `parity` 3 red (86 control green), `halfgutter` 2, gutter shortened 0.1 mm 0 red by design, 0.2 mm 2, 0.3 mm 2; pairing `stalepayload` 1 red (2 green), `nopair` 3 red; proof `note` 1 red (104 green); export_interior `parity` 7 red and the 0.05/0.2 mm shifts not caught (6 red, CARD-322's six only), 0.4/0.6/1.0 mm 7 red; 0 skipped in every run. Page selection is derived from `PuzzlePagePlan` and the last `len(puzzles)` pages and four mutants go red (shifted one page 2, a guide page for a puzzle page 3, answer window early 1, one answer page dropped 2); re-adding skip-on-`ValueError` survives (89 passed), which is equivalent because no selected page raises, so "a `ValueError` is a failure" has no killer of its own. The reviewer's own mutants: swapped odd/even 2 red, sign flip of gutter and outside margin 3 red (divider) and 7 (export_interior), parity wrong on page 6 only 3, on page 14 only 2, from page 14 on 2.

Findings, ranked. F-1 (inline fix): the divider magnitude claim is WEAKER. Odd-minus-even cancels any common-mode drift: a common 1.0 mm left-margin shift on every page (about 5.9 px) turns the OLD per-page 2 px test red (2 failed, cut, unprobed) while the new test is green in both media (89 passed each); a centring bug that moves every drawing the same way now ships green, and the only absolute check left is the single title-parity test in export_interior. Fix: add an absolute check on the pair SUM using the same coordinate and the same 2 px, or declare the loss under F-2. F-2 (inline fix): the sub-bound residues are written only in card notes, not in the tests (ADR-0039/R3 wants a measured bound with its own failing control): divider gutter shortened 0.1 mm 0 red and outside margin lengthened 0.1 mm 0 red, outside margin lengthened 0.2 mm 2 red, gutter lengthened 0.1 mm 2 red; export_interior 0.05 and 0.2 mm not caught, red from 0.4 mm; the tests say only "the old bound, unmoved". Fix: a comment with the residue and its reason next to each bound. F-3: the NAMED SURVIVOR holds a different, weaker claim: `test_nothing_on_the_book_export_path_imports_this_module` asserts only that `book_proof` is imported solely by `app.py` (it exists exactly once); the retired claim was "no ink at all beyond the page, frame and caption", and a vector page with a stray rule and no text passes the new arm (105 passed), as does a note with reworded text; a stray bitmap block and a bitmap-drawn note still red the raster arm; the honest disposition is to say the survivor covers only the proof-note route, not stray ink. Guard `test_the_cited_survivor_still_resolves` reds when the survivor is renamed (1) and when doubled in another class (1); a module-level duplicate would not be seen (minor); a split marker ("PROOF" then "PAGE") is caught; the "at least some text" guard has no committed unit control (the `notext` product plant adds one red); `_NOTE_MARKERS` is a literal tuple though its comment says "derived" (a control test pins it to `annotation_lines`, so low). F-4: the latent-site note is mislabelled (corrected in place above; routing note on CARD-322). F-5 (informational): `frame_centre_of` is not load-bearing in the divider test (swapping it for `drawing.left` leaves 89 passed because the difference cancels the bias); in the title-parity test it is needed (7 red without it). F-6: `nopair` has no in-run control (`stalepayload` is the matched one, and `nopair` reds only the page-count assertion); the pairing ink assertion has a killer only for single pages; swapping the payloads of two-up slots passes (3 passed: the test reads geometry, so slot content is unmeasured; predates the card); measuring extents in pixels instead of whole cells reds (1), so the unit is pinned. F-7 (minor): the equal-width precondition is the detector at 0.3 mm, caught by a 1 px rounding difference (`[1771, 1772]`), not by the bound. Could not verify: the cut tree was rebuilt with `git archive`, not a real worktree; no full suite or other module was run. Next: a fix round for F-1, F-2, F-3 (and the F-6/F-7 declarations), then review cycle 2.

[Fix round for review 1, commit `a71fb2da`] Verified by the orchestrator at tip `a71fb2da`: worktree clean; over the cut `a32eb8bf` exactly the four Touches files and nothing else; `src/`, `tests/helpers`, `tests/test_book_pdf.py`, non-test and `meta/` diffs all 0; `git diff --stat e022d697 HEAD` is 4 files, 262 insertions and 61 deletions (`test_book_export_interior` +53, `test_book_pairing` +6, `test_book_divider_pages_option` 165 lines changed, `test_book_proof_pages` 99 lines changed); my own run of the four modules unlifted gave 217 passed (the author reports the same), and `TestEdgeOffset_ThePixelOraclesStillReadPixels` 4 passed unmodified. Author-reported, not re-run by me: probe-scoped 6 failed / 211 passed, no skips, the six being CARD-322's unchanged (five `KeyError: PageKind.TITLE` in `TestInteriorReadings_TheStreamArmIsReached` plus `test_PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage`); divider alone 97 passed in both media, proof alone 106 in both; census modules on the tip, no red: `test_suite_profile`, `test_impact_set`, `test_check_ref_resolution`, `test_kanban_review_record`, `test_collected_names`, `test_guard_integrity`, `test_shared_fixture_controls` 820 passed, and `test_cli`, `test_browser_fixture_scope`, `test_full_suite_lock` 209 passed; because nothing was red the clean-archive comparison on the cut was not run, and the author did not run other tests that parse the tests tree such as `test_book_pdf` beyond the listed modules and the four edited ones.

F-1, the ABSOLUTE check restored for the divider "how far" claim: a helper `_problems(...)` on `TestDividerPages_EveryPagesParityIsStillItsOwnPosition` returns a list of problem messages (so no test body has an early `return`) and checks the absolute offset `(frame_centre_of(...).frame_left + grid_right)/2 - page.width/2` against 59.055 px. Measured at this tip: raster page 6/7 -59.75/58.25 (off by 0.70/0.80 px), vector under the probe -60.75/57.25 (off by 1.70/1.80 px), because the vector grid edge reads 1 px left of the raster's. The old 2 px bound was KEPT, not widened (G-2): the vector margin to it is only **0.2 px** (raster about 1.2 px), which is a thin bound and is declared as such next to it, with both numbers. Controls: `test_a_common_shift_of_every_page_is_caught_by_the_absolute_check` (every page shifted 6 px in the image reds on the "centre" problem and not on the odd-minus-even one) and `test_the_control_for_the_common_shift_is_the_unshifted_book` (passes). Plant `leftshift` (every page's left margin 1.0 mm shorter, probe-scoped): 3 failed, 94 passed (`test_every_pages_parity_equals_its_own_1_based_position[True]`, `[False]`, and the unshifted-book control, which the plant reaches at product level: not a leak), 0 skipped.

F-2, the residues declared and pinned from both sides. Re-measured by building the book with a shifted real margin while the expectation stays nominal (margins are stored to 0.01 cm, so 0.1 mm is the finest step), and they DIFFER BY MEDIUM and from the reviewer's figures because the new absolute check changed them. Divider shifts caught (raster / vector): gutter -0.1 mm no / yes, outside +0.1 mm no / yes, gutter +0.1 mm yes / yes, outside +0.2 mm yes / yes, outside -0.1 mm yes / yes, gutter -0.2 mm yes / yes. A `_RESIDUE` table in the test holds those outcomes and `test_the_residue_is_what_the_table_declares` runs 6 parametrized cases against it, the table selected by `page_medium(PageKind.PUZZLE)` with no skip, reason: the 0.2 px vector headroom. export_interior: `TestParity_TheBoundIsPinnedFromBothSides` (3 tests) with a helper `_parity_error_mm`; the error in mm for a gutter longer by +0.1 / +0.2 / +0.4 mm is raster 0.003 / 0.088 / 0.172 and vector 0.088 / 0.172 / 0.257, so +0.1 mm is not caught in either medium and +0.4 mm is caught in both; the nominal raster page already sits 0.082 mm from the coordinate, leaving 0.018 mm of room against the 0.1 mm bound. The reviewer's "0.05 mm" shift CANNOT BE BUILT (stored margins round it to no change, which is why it never reddened), so that part of the reviewer's table is retracted here as a non-experiment. [RETRACTION RETRACTED 2026-11-05 under ADR-0039/R4, on the cycle-2 review: the claim that a 0.05 mm shift cannot be built is FALSE at the product level. The margin column is an unconstrained `String` (`db/models.py`) and `_stored_mm` parses any Decimal; only the TESTS' own `:.2f` formatting rounds. The cycle-2 reviewer built margin strings with four decimals (for example "2.005") in a scratch copy: a +0.025 to +0.1 mm gutter gave a `_parity_error_mm` of 0.0030 mm in raster and 0.0877 mm in vector (0.0817 and 0.0030 unshifted), and divider shifts of +-0.025 and +-0.05 mm also take effect. So the cycle-1 "0.05 mm not caught" was a REAL experiment (a spec-level plant); its substance holds, the export_interior bound does not see it. The comments "margins are stored to 0.01 cm, so 0.1 mm is the finest step" in `tests/test_book_divider_pages_option.py` and `tests/test_book_export_interior.py` are false and are reworded in the cycle-2 fix.]

F-3, the proof stream arm: the author chose the HONEST STATEMENT, not a strengthened arm. The comment now says what holds and what is retired: a stray rule or a reworded note passes the vector arm, and the survivor `test_nothing_on_the_book_export_path_imports_this_module` holds only the proof-note route. Measured: a stray vertical line on every vector puzzle page (plant `strayrule`) leaves `tests/test_book_proof_pages.py` at 105 passed, and the same plant reds 10 of 65 in `tests/test_book_puzzle_page_vector.py`; the author makes no claim that module reads this fixture's page (drawn by the same writer, `vector_puzzle_page`). Note markers are now derived from `annotation_lines` (`_note_markers`) and a test pins them to the four real labels; new control `test_a_stream_that_shows_no_text_is_refused_not_passed` (an empty stream and a stream with only a line); `test_the_cited_survivor_still_resolves` now counts the survivor anywhere in the file, so a module-level duplicate reds it; the vector arm is an if/else with the raster arm in a helper (no early `return`); plant `note` still reds the book-page test (1 failed, 105 passed). F-6 and F-7 are declared in comments (pairing: `nopair` reds only the page-count assertion and `stalepayload` is the matched control for the ink assertion; divider: the equal-width precondition detects the 0.3 mm gutter shift through a 1 px rounding difference, not the bound). Not re-run this round: the pairing `nopair` and `stalepayload` plants (their results carry over).

[Review 2/3] Score: **8.3 - APPROVED** (threshold 8.0), at tip `a71fb2da`. Cycle 1's blocking finding F-1 is closed; three small findings remain, all comment or declaration fixes under the cut bar. Derived by the cycle-2 reviewer, from scratch `git archive` copies of the tip and the cut (plants only in scratch copies or `-p` plugins, the worktree never edited; every run showed a summary line, 0 skipped): per module, cut unprobed / cut probed / tip unprobed / tip probed: divider 89 passed / 3 failed, 86 passed / 97 passed / 97 passed; pairing 3 / 1 failed, 2 passed / 3 / 3; proof 103 / 1 failed, 102 passed / 106 / 106; export_interior 8 / 7 failed, 1 passed / 11 / 6 failed, 5 passed; the four together cut 203 passed unprobed and 12 failed / 191 passed probed, tip 217 passed unprobed and 6 failed / 211 passed probed. The six reds at the tip are exactly the seven at the cut minus `test_PropertyTest_BookExport_ParityCountsFromTheTitlePage`, the same six node ids (a `diff` of the sorted FAILED ids gave the same six), CARD-322's. AC-3 `TestEdgeOffset_ThePixelOraclesStillReadPixels` 4 passed unmodified; `tests/helpers`, `src/`, `tests/test_book_pdf.py` and `meta/` diffs over the cut empty; the diff is exactly the four Touches files. F-1: the common-mode left-margin plant `leftshift` at +-1.0 mm goes red in BOTH media, so the absolute claim is restored; the 0.2 px vector headroom is declared in `_problems` with both numbers and the reason (the vector grid edge reads 1 px left of the raster's) and was not widened; vector sensitivity on the parity tests only: a left-margin shift of -0.01/-0.02 mm green, -0.04/-0.06 mm red (the bound flips at about 0.03 mm of margin, about 0.2 px of centre), +0.4/+0.6 mm green and +0.8 mm red (a one-sided blind range, because the nominal sits at the bound's edge); raster non-monotone (-0.04 red, -0.06 green, +0.3 red, +0.4 green, +0.6 red) because of the 1 px width-precondition rounding; the bound is pinned from the TIGHT side (1.5 px reds 3 in vector) but NOT from the loose side (a bound of 2.3 px passes all 97 in both media; in raster 1.5 px also passes). F-2: all six `_RESIDUE` rows re-derived with independent spec-level plants in both media: raster -0.1 gutter not caught and +0.1 outside not caught, the other four caught; vector all six caught; the table is right. `TestParity_TheBoundIsPinnedFromBothSides` is genuinely pinned from both sides (`ei_nominal_from_real`, with the expectation computed from the real margins, reds `test_the_first_shift_past_the_residue_is_caught`). F-3 is handled honestly and is a DECLARED BOUND, not a blocker: the comment states exactly that what holds is "the stream shows none of the proof note's own wording", what is retired is "no ink beyond the page, frame and caption", and the survivor holds only the proof-note route; `stray_rect`, `note_ink_only` and `note_other_wording` all pass (106 passed), so vector stray ink is not held; `note` reds `test_a_book_page_of_the_same_fixture_carries_no_note`; a bitmap-drawn note and a stray bitmap block red the raster arm (1 each); `test_the_cited_survivor_still_resolves` reds on a module-level duplicate and on a rename in both media; `_note_markers` is derived from `annotation_lines` and the pin reds on a reworded note; the new `test_a_stream_that_shows_no_text_is_refused_not_passed` has a killer (turning the no-text guard off reds exactly it). The loss has little practical reach (the proof note comes from `book_proof`'s raster writer, not the vector page writer) but it is the owner's call whether the weaker survivor deserves recording on a card. The census modules: all 12 listed run on the worktree, 1077 passed, 0 failed, 0 skipped; no test body this card adds ends in an early `return` (the diff was grepped for added bare `return` lines and for skip/xfail additions: none); `test_suite_profile` green. The reviewer's mutants: the absolute check's expectation taken from the same drawing 1 red raster / 3 vector, the absolute check removed 1 / 3, odd/even swapped in it 6 / 4, `_RESIDUE` for the wrong medium 2 / 2, page selection shifted by one page 10 / 10, a bound widened to 2.3 px SURVIVES in both, a bound tightened to 1.5 px SURVIVES in raster and 3 red in vector, `frame_centre_of` replaced by `drawing.left` in the parity helper SURVIVES in raster (4 passed) and 2 red in vector, the parity helper's nominal from the real margins 1 / 1, survivor duplicated or renamed 1 red each.

Findings, ranked: F2-1 (minor, fix inline): the comments "stored to 0.01 cm, so 0.1 mm is the finest step" are false and the card's retraction of the cycle-1 0.05 mm experiment is wrong (corrected in place above); failure scenario: a reader trusts "finest step" and misses a real sub-0.1 mm defect the bound cannot see. F2-2 (minor, fix inline): declare next to the vector bound that the headroom is about 0.2 px and a poppler or rendering change of about 0.3 px would flip it red (a loud false red, only once PUZZLE is vector), the one-sided range (red at about -0.03 mm of common left-margin shift, blind for about +0.4 to +0.6 mm), and that a bound of 2.3 px is not caught; failure scenario: someone widens the bound to quiet a false red and nothing objects. F2-3 (declared bound, owner visibility): a stray rule or reworded note on a vector proof page passes; acceptable under AC-1. Informational: the raster arm pins nothing about the absolute bound; the vector column of the residue table exists only under the probe today, so it is exercised in vector only after the medium flips; `_parity_error_mm` hard-codes page index 5 with no assertion that page 6 is a puzzle page (a wrong page fails loudly because `(drawing,) = drawings_of(ink)` would not unpack); the `_RESIDUE` parametrized ids (`shift0`..`shift5`) are opaque and the odd-minus-even message carries no bound. Not verified: the author's "10 of 65 in `tests/test_book_puzzle_page_vector.py`" (carried), the cut-state `ParityCountsFromTheTitlePage` without `frame_centre_of`, pairing `nopair` and `stalepayload` (not re-fired), the production environment's poppler version.

[Fix round for review 2, commit `c474cf08`] Verified by the orchestrator at tip `c474cf08`: worktree clean; over the cut `a32eb8bf` still exactly the four Touches files; `src/`, `tests/helpers`, `tests/test_book_pdf.py`, non-test and `meta/` diffs 0; `git diff --stat a71fb2da HEAD` is 2 files, 65 insertions and 11 deletions (`tests/property/test_book_export_interior.py` 18 lines, `tests/test_book_divider_pages_option.py` 58 lines); no added bare early-`return` and no added skip or xfail; my own run of the four modules plus `tests/test_suite_profile.py` unlifted gave 668 passed. Author-reported, not re-run by me: probe-scoped 6 failed / 212 passed, the six the same CARD-322 ones (`test_PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage` plus the five `TestInteriorReadings_TheStreamArmIsReached`), unprobed 218 passed, `tests/test_suite_profile.py` + `tests/test_kanban_review_record.py` + `tests/test_collected_names.py` 531 passed, 0 skipped.

F2-1: the false "stored to 0.01 cm, so 0.1 mm is the finest step" comments are reworded in both files: the product accepts finer margins and the tests' own `:.2f` formatting is what rounds; the declared residue is the bound's, not a limit of what can be built. Re-measured by the author this round (four-decimal margin strings in `_parity_error_mm`, noted in the `TestParity_TheBoundIsPinnedFromBothSides` docstring as measured this round): gutter 2.00 cm unshifted raster 0.0817 mm / vector 0.0030 mm; 2.005 cm (+0.05 mm) raster 0.0030 / vector 0.0877; 2.0075 cm (+0.075 mm) raster 0.0030 / vector 0.0877; the author's numbers agree with the cycle-2 reviewer's, so the cycle-1 "0.05 mm not caught" was real, as the un-retraction above says.

F2-2: the vector headroom is declared next to the bound in `_problems`; the bound is now a named constant `CENTRE_BOUND_PX = 2`, `test_the_bound_is_the_declared_number` pins its value, and the declaration says nobody may widen it without moving that declaration. Re-measured by the author in both media (bound 1.5 px: vector 3 failed / 94 passed, raster 97 passed, a loud false red in vector only because the nominal vector centre is 1.7 to 1.8 px; common left-margin shift of every page by a spec plant: shorter by 0.03 mm red in both, longer by 0.4 mm green in both, longer by 0.6 mm red in raster and green in vector, longer by 0.8 mm red in both). **DISCREPANCY, unresolved:** at a bound of 2.3 px the author measures vector 97 passed and raster 2 failed / 95 passed (two `_RESIDUE` cases that stop being caught), whereas the cycle-2 reviewer measured "passes all 97 in both media"; the declaration records the author's number; the author suggests the reviewer moved only one of the two bounds and says it did not identify which two ids fail in raster; the 0.3 px flip sensitivity is DERIVED from the 0.2 px headroom, not separately measured; the author's "longer by 0.4 mm" raster figure was measured as -0.4 in its sweep, which is the longer direction. Optional items done: the `_RESIDUE` ids are renamed from `shift0`..`shift5` to `gutter{g:+}mm-outside{o:+}mm` (for example `gutter-0.1mm-outside+0.0mm`; the author's own new tests from this card, so renaming is not a G-7 violation), the odd-minus-even and centre failure messages carry the bound, and `_parity_error_mm` asserts that interior page 6 is the puzzle page. Next: the merge gate.

