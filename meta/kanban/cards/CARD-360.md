# CARD-360: `pdf_levels` and `pdf_two_up` — 6 reds in the two modules where the seam is already present

**Status:** in_progress
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1c (0.5d)
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/360-pdf-levels-two-up
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-360
**Source:** Module-sliced out of CARD-337 at the decompose station, 2026-11-04, on the owner's "module slicing" instruction. CARD-337's own item 0 refuted its premise three ways and its round then derived the mechanism x module cross-tab; that table reconciles to 143 reds in both directions. The axis was changed from mechanism to MODULE because the round measured that a mechanism-sliced partition cannot run concurrently at all -- nine of thirteen modules split across mechanisms, `tests/test_book_pdf_band.py` would have needed five separate cards to edit it, and nothing could have run beside the M10 card. The file axis is the one the scope gate enforces.
**Idea:** —
**Wave:** 79
**Created wave:** 75
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/test_book_pdf_levels.py, tests/test_book_pdf_two_up.py
**Review score:** —
**Started:** 2026-11-05T18:14Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

> **⚠ UNVERIFIED FIGURES, 2026-11-05.** This card quotes **57 M10 reds / 35 cause lines**. They are CARD-337's round's roll-up and **three readers have now tried and failed to verify them** (CARD-358's round, its review, and the orchestrator). The review's census aborted on its own gate at 14 of 20 modules — *the instrument working*, a zero-collect most plausibly caused by a foreign lock appearing mid-run, since the guard refuses in `pytest_configure`. **And one component has already moved:** CARD-356's module measures 26 reds, not its stated 25. **Do not quote the roll-up as fact; re-derive your own module's count at the start**, which is what scopes your card anyway.

## The population, from CARD-337's cross-tab

**8 reds under the five-kind probe; this card owns 6.** The other 2 are **M8** (placed-edge,
`assert 0.2313… <= (0.0423… + 1e-09)`) in `pdf_two_up`, and they are **CARD-352's** — CARD-336
closed, so they were re-routed there.

| module | mechanism | reds | owner |
|---|---|---|---|
| `tests/test_book_pdf_levels.py` | M10 medium-blind empty read | 2 | this card |
| | M9 byte identity | 2 | this card |
| `tests/test_book_pdf_two_up.py` | M10 medium-blind empty read | 2 | this card |
| | **M8 placed-edge** | **2** | **CARD-352** |

## Why these two modules are grouped, and it is a measured property

**They are the only two modules of the thirteen where the `interior_images` seam is ALREADY
present** — class S0 in CARD-337's seam derivation. So whatever their reds are, they are **not**
a missing seam, and that rules out the whole family of repair the original CARD-337 was built
around. Their mechanisms are what is left when the seam is not the answer.

**M9 byte identity is the interesting half.** Its signatures:

```
AssertionError: assert b'\xff…' == b'\xff…'
interior page N is not the page it was
stored page N is …
```

**A byte comparison across a medium change is a claim about determinism, not about pixels.** Two
renderings of the same page as operators can be byte-identical; a raster rendering and an
operator rendering cannot. **So the question is what identity means once a page is a stream** —
and whether the claim was ever about bytes or about "the same page came back".

**Byte identity also appears in `pdf_band` AFTER its seam is planted** (3 cells, where the
unplanted census shows zero), which is why CARD-337's old AC-2 enumeration of this family was
incomplete. **If you settle what identity means here, say what it implies for those three.**

**M10 warning:** board-wide M10 is 57 reds across 35 cause lines — a residual, not a mechanism.
Re-split your 4 before trusting the label.

## What to implement

1. **Settle what byte identity means for an operator page**, and state it. That is the card's
   substance; the M10 reds are probably cheaper.
2. **Re-split the 4 M10 reds** across the two modules and report the histogram.
3. Repair or disposition each per ADR-0042/R6, stating re-expression or retirement-with-survivor.
4. **Say what your identity answer implies for `pdf_band`'s three post-seam byte-identity
   cells** — a statement for CARD-356, not a fix here.

## Acceptance criteria

- **AC-1** *Given* the M9 reds, *then* the card states what identity means for a page written as
  operators, and the claim is **asserted** in that form rather than commented.
  (test: named by the implementation; state it)
  *Clarified 2026-11-05:* this IS a genuine test, not a census. CARD-355 (merge `e4849464`) already settled the
  question for its own module and is the precedent: for an operators page, identity is DETERMINISM OF THE STREAM
  (`TestBookPdfMemory_AnOperatorsPageIsTheSameStreamEveryExport` exports twice and asserts equal content streams,
  equal length and equal render digests, with a control that can fail), and a stored raster-era digest is compared
  only against a BITMAP page (`raster_digests` yields `None` for an operators page, and every retirement site
  counts its retirements and asserts them equal to the file's vector pages). State whether your two modules'
  claims were about bytes or about "the same page came back", and name the class you write.
- **AC-2** *Given* the five-kind probe, *then* both modules' red counts are stated before and
  after, and `pdf_two_up`'s 2 M8 reds are **still present and attributed to CARD-352**.
  (check: review-lens — a stated count or a mutation run is not a test, and no committed test can name it: its instruments live in the worktree and the force-add gate forbids tracking them. **No card owes a flip.** Restated 2026-11-05 on CARD-358's F-004.)
- **AC-3** *Given* the 4 M10 reds, *then* their cause-signature histogram is reported.
  (check: review-lens)
- **AC-4** *Given* each repair, *then* a plant re-breaks it with its matched control green in the
  same run and `0 skipped`.
  (check: review-lens — a stated count or a mutation run is not a test, and no committed test can name it: its instruments live in the worktree and the force-add gate forbids tracking them. **No card owes a flip.** Restated 2026-11-05 on CARD-358's F-004.)
- **AC-5** *Given* CARD-356's three post-seam byte-identity cells, *then* this card states what
  its identity answer implies for them — a routing statement, not a repair.
  (check: review-lens)

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

## Premise re-verified 2026-11-05 (CARD-354, CARD-355 and CARD-356 landed since this card was written)

Read against current `main`, by the orchestrator. Nothing here changes an AC except the AC-1 clarification above.

- **Not measured, and yours to measure first:** the 8 reds, the 6 you own, and the 2 M8 reds. Re-derive them with
  `census_five_kinds.py --only <module>` for both modules before implementing anything, and say which figures are yours.
- **The question this card is built around has a first answer on `main`, from CARD-355** (see AC-1's clarification).
  Do not re-derive it from scratch; decide whether it carries to `pdf_levels` and `pdf_two_up`, and if it does not,
  say why. Carrying it is the cheaper outcome and the expected one.
- **Item 4 / AC-5 now has a second data point: CARD-356** (the band module). Its author re-expressed the post-seam
  byte-identity reds as operator-for-operator equality with a same-medium untitled twin plus a text-layer reading of the
  band zone, and counted FIVE M9-family reds there, not the card's three (CARD-356's record, on `main` once its gate
  lands; check its status first). State whether your identity answer agrees with theirs or diverges, and why. A routing
  statement, not a fix.
- **The shared-reader defect is FIXED on `main`** (CARD-355, `e4849464`). Both of your modules import `pdf_pages`. The
  CARD-355 author measured both under the probe, old helper against fixed: **no change** (`test_book_pdf_levels`
  4 failed and `test_book_pdf_two_up` 4 failed, before and after; carried, not mine), so your 4 M10 reds are not that
  defect. Re-split them anyway, by reading the cause lines, not by the label (the board's own M10 label has been a
  different mechanism on every module so far: CARD-354 A, CARD-355 D, CARD-356 a reader defect over a glyph template).
- **The 2 M8 reds are CARD-352's and CARD-352 is still `ready`** (touches `tests/test_book_puzzle_frame.py`, not your
  modules): they must still be present and attributed to it, which is a census fact, not a test; AC-2 is review-lens
  as written.
- **The seam is already present in both modules** (class S0), so what the author of CARD-355 found is the relevant
  caution: the seam was not where the card said it was (`LivePageBytes.track`, not `interior_images`). Read the call
  sites before accepting this card's own account of them.

## Worktree notes

[Author round, commit `377d3ad4`] Verified by the orchestrator: tip `377d3ad4`, one commit over the cut `2eeec589`, worktree clean; exactly the two Touches files (`tests/test_book_pdf_levels.py` 485 lines changed, `tests/test_book_pdf_two_up.py` 204 lines changed; 645 insertions, 44 deletions); `src/`, `tests/helpers`, `tests/test_book_pdf.py`, `tests/test_book_puzzle_frame.py`, `tests/test_book_pdf_band.py`, non-test and `meta/` diffs all 0; no added bare early-`return` line and no added skip or xfail in the diff; my own run of the two modules plus `tests/test_suite_profile.py` unlifted gave 523 passed. Author-reported, not re-run by me: census under the probe, levels red 4 -> 0 (24 passed, 0 skipped), two_up red 4 -> 2 (47 passed, 0 skipped), the 2 left being the M8 placed-edge pair (`test_the_control_the_retired_fixed_top_edge_would_share_the_row`, `AssertionError: (0.2313..., "AC-252's placement really is the upper slot's own row")`, and `test_that_row_is_the_top_margin_plus_the_band`, `assert 0.2313... <= (0.0423... + 1e-09)`), values unchanged, CARD-352's and untouched; 12 census modules on the tip 1077 passed, 0 failed, 0 skipped; five more modules that cite these files by name 234 passed; NOT run: `tests/test_book_pdf.py` and `tests/test_book_puzzle_frame.py`, and the full suite.

M10 re-split, by reading the cause lines (not by the label): before any change both modules gave 4 failed probe-scoped, as CARD-355 measured, so NOT the shared `rendered_page` defect. Levels' four reds, which the board labelled 2 M10 + 2 M9, are ONE mechanism: `test_each_puzzle_page_is_the_puzzle_and_the_band_it_should_be` ("interior page 6 is not E1 banded"), `test_the_medium_puzzles_band_reads_puzzle_three_medium` and `test_the_numbers_run_one_to_n_over_the_puzzles` (bare `assert b'..' == b'..'`), `test_the_puzzles_print_grouped_by_level` ("E1 does not print on interior page 6"), each `interior_page.tobytes() == expected.tobytes()`, a poppler render of a stream compared with a PIL bitmap from `render_pages`: the board's M9/M10 split for levels is only assertion-message text. Two_up's two reds (`test_the_upper_band_reads_puzzle_one_and_the_lower_puzzle_two`, `test_the_numbers_follow_the_pages_before_this_one`, both `assert _same_ink(...)`) compare the tight ink crop of a band on a poppler-rendered interior page with a crop from a bitmap reference: a cross-medium REFERENCE, a different arm from CARD-354's, CARD-355's and CARD-356's. Also found: `test_it_is_not_numbered_by_its_page` in levels was green only VACUOUSLY (`!=` of a stream render against a bitmap); it is now guarded by a control.

AC-1, what identity means (a genuine test, as the card's clarification says): CARD-355's answer carries to both modules unchanged. For an operators page identity is determinism of the stream, never equality with a bitmap; every claim in these files was about "the same page came back", not about bytes (bytes of a bitmap were only the instrument), and neither module stores a digest, so the `raster_digests`/`None` retirement-counting apparatus has no subject here. Asserted by `TestBookPdf_AnOperatorsPageIsTheSameStreamEveryExport` in `tests/test_book_pdf_levels.py` (6 tests: two exports of the same book give the same pages compared by index, 18 pages, same media; a control that the comparison tells pages apart by position; a control for `same_page` itself (twin, one mark more, another extent, bitmap vs stream both ways, a one-pixel bitmap difference); an operators page named by its position, number, tier and puzzle with wrong-number, wrong-tier, wrong-puzzle, next-page and previous-page refusals beside a green control; the band's words read from poppler's text layer, not from `band_identity` (a planted `band_identity` that loses the dot's spaces is carried by both the page and its twin and is still refused); the folio read from poppler pins the page position (a writer one page late is carried by both and still refused)); in two_up `TestBookPdf_ABandIsReadInTheMediumItWasWritten` (4 tests) with the reference band drawn as operators and rasterised by the same poppler at the same DPI (a new `like=` argument of `_reference_band`) and the words read from the text layer; both new classes run their operators-arm controls on the unlifted tree too, by calling `vector_puzzle_page` directly. Dispositions (ADR-0042/R6): all six are RE-EXPRESSIONS against the content stream, none a retirement; survivors cited, each defined exactly once and guarded by the new native `TestBookPdf_EveryCitedSurvivorStillExists` in levels (by `ast`, default-deny, with a rename/missing-method control): `tests/test_book_pdf_memory.py::TestBookPdfMemory_AnOperatorsPageIsTheSameStreamEveryExport` and `tests/test_book_puzzle_page_vector.py::TestPuzzlePage_AgreesWithTheRasterTwin`.

Plants (in-process mutations, `src/` untouched on disk, matched control the unplanted green run in the same invocation mode, 0 skipped, no ERRORs; unlifted / probe node ids moved): levels pages 6/7 swapped 3 / 3, nondeterministic (alternate swap per call) 3 / 3, `band_identity` without the dot spaces 7 / 7, `band_identity` number+1 7 / 7, page number +1 in the writer 7 / 7, `same_page` made blind to content 4 / 3, `names_the_page` always True 4 / 4 (only the controls move, as they must); two_up (probe, beyond the 2 M8 baseline) `band_identity` without the dot spaces 3, number+1 3, `_same_ink` blind 2 (also 2 unlifted), `like=` ignored 4, writer page +1 0. The swapped plant leaves the AC-1 determinism test green because a deterministic swap is deterministic; the nondeterministic plant is the one it catches, so determinism is distinguished from "pages are right".

DECLARED RESIDUE (ADR-0039/R3), author-stated, for the reviewer to judge: (1) the two_up PAGE-PARITY edge: shifting the reference's page number by one is NOT detected (0 extra reds on the writer-page+1 plant) because both slots are centred across the one usable width, so the band's left edge is parity-invariant; AC-251 does not claim parity and the bound was not widened; (2) levels: the drawing itself is not independently held in operators: the expected operators page is the generator's own page writer, so a page drawn wrong the same way by the walk and by the writer passes; a whole-page expectation would be a second implementation of the writer; declared in the module docstring with its reason, and the survivor holds only the grid (rule count, span, placement, weights); (3) the folio check assumes the footer is the lowest 15% of the page and the grid-size label is "C x R"; it is tuned to 20x20 puzzles at pages below 20 and other cases were not measured. CARD-356 implication (a routing statement, AC-5): the author AGREES with CARD-356's re-expression (operator-for-operator equality with a same-medium untitled twin plus a text-layer reading of the band zone); `_same_page` has the same shape and the same refusal of bitmap against stream; the one difference is what the twin varies (CARD-356's varies the picture name, an independent variable; this card's is the page writer at the position the test states, which pins the walk's choices); for these two modules the reds were present before any seam was planted (the seam was already there, class S0), so the three-versus-five post-seam inflation question does not arise. AC-vs-body: the card's labels (2 M10 + 2 M9 in levels, 2 M10 in two_up) do not match the mechanisms (levels one mechanism, two_up a different arm); AC-3's histogram is given by cause lines and re-labels two of the board's M9 as the same mechanism. Not verified: any poppler other than this host's, other trims, the folio on pages of 20 or more, other puzzle sizes. Not yet reviewed.
