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

[Review 1/3] Score: **8.1 - PASS** (threshold 8.0), at tip `377d3ad4`; no finding blocks, no owner decision; F-1 and F-2 are cheap and worth fixing inline before the merge. Derived by the reviewer (private clones under its own scratch directory, `-p` plants, the worktree and `src/` never touched, the lock checked before every pytest, no full suite): census at the cut, probe-scoped, levels 4 failed / 11 passed and two_up 4 failed / 41 passed (8 failed, 52 passed together), unlifted levels 15 and two_up 45; at the tip probe-scoped levels 24 passed and two_up 2 failed / 47 passed, unlifted levels 24 and two_up 49, so 73 passed together (the author carried 72: off by one, corrected here). The 2 reds left are the M8 pair `test_the_control_the_retired_fixed_top_edge_would_share_the_row` and `test_that_row_is_the_top_margin_plus_the_band`, with the same cause lines and values at cut and tip (`0.23133333333333184 < 0.2` and `0.23133333333333184 <= 0.0423... + 1e-9` with `Drawing top=304`), CARD-352 still `ready`. No test id removed or renamed: levels 15 -> 24 methods (6 in the AC-1 class, 3 in the survivor guard), two_up 39 -> 43 (all in the new class); scope exactly the two Touches files, `src/`, `tests/helpers/`, `tests/test_book_pdf.py`, `tests/test_book_puzzle_frame.py`, `tests/test_book_pdf_band.py` and `meta/` empty; no skip, xfail or bare `return` added, no tolerance touched; the 12 census modules 1077 passed, 0 failed, 0 skipped. The reviewer ran `-p probe_five_kinds` directly, not the `census_five_kinds.py` driver. Cause-line re-split verified at the cut: levels' four are one mechanism (a bare `bytes == bytes` between a poppler render and a PIL bitmap; first differing byte at index 1617678 in three tests and 1617645 in one), the board's M9/M10 split for levels being only assertion-message text; two_up's two are a different arm (`_same_ink` comparing a tight crop of a poppler-rendered band, 431x57 px, with a bitmap reference crop, 432x57 px). The vacuity claim holds: `test_it_is_not_numbered_by_its_page` at the cut under the probe is green unplanted AND with a walk that numbers pages by position; at the tip it is green unplanted and red under that plant (through the new control assertion; the loop only checks the matcher is injective).

Identity: determinism versus rightness is a real distinction (a deterministic swap of pages 6 and 7 gives 3 reds and the determinism test stays green; a nondeterministic swap gives 3 reds including the determinism test; a last page dropped or different on the second export gives 1 red each). For operators pages the expectation is the generator's own writer, which IS a genuine weakening of the bitmap-era independent drawing, declared in the module docstring so it is not a hidden tautology; what remains is a poppler text-layer read of the band and the folio. Writer-wide plants reproduce the author's disposition: a stray rule in the page corner moves 0 in levels and 0 in two_up; a stray rule at the left of the footer zone 1 in levels (`test_no_page_of_the_interior_is_a_hard_divider`, a pixel heuristic) and 17 beyond the M8 pair in two_up, 4 red in `TestPuzzlePage_AgreesWithTheRasterTwin`; the grid shifted 1 pt 0 / 1 / 1 red there (`test_the_ink_and_the_stream_rule_the_same_grid`); every page transposed 0 / 1 (a pairing page-count test) / green. The author's declared residue (2) is OVERSTATED, not understated: other classes in the same writer module hold clue digits and furniture and the author does not cite them. Survivors and guard: both cited classes exist exactly once by `ast`; a rename and a module-level duplicate are caught, a method cited from a sibling class is caught as "no such method"; but two plants stay green (3 passed each): one empties the survivor class of its tests and one renames the real class and leaves a `pass` stub carrying its name (the guard proves a name exists, not that the survivor still holds anything), and a citation written without the `tests/` prefix is silently not derived. The memory survivor holds determinism of its own corpus export: sibling evidence rather than the survivor of any claim this card retired.

Declared residues (ADR-0039/R3): residue (2) is in the levels docstring with its reason and protects the score. Residue (1), two_up page parity, is only in the card notes, not the test; measured: the reference band's left edge is 1061 on page 6 and on page 7; a walk-plan `page_number + 1` plant gives 0 extra reds, a plan-numbers+1 plant gives 2; the author's reason is confirmed. Residue (3), the 15% footer assumption, is only in the card notes with no measured window in the test: the window runs from 0.807 (the lowest clue digit of a 30x30 grid) to 0.8624 (the folio top); the chosen 0.85 sits inside it; floors of 0.0 and 0.995 each give 7 reds but nothing pins the window itself; the folio reads correctly for pages 6 to 150 on 20x20, 10x10, 30x30, 15x20 and 30x10 grids; a 20x30 or 10x30 vector page carries NO footer or folio at all (apparently the footer's all-or-nothing design; not checked against the raster twin), and `footer_digits` would then pick up clue digits, so a correct page false-reds loudly. Plants: the author's re-fired all reproduced exactly (levels probe: swap 3, nondeterministic 3, no dot spaces 7, number+1 7, writer page+1 7; `same_page` blind 3 probe / 4 unlifted and `names_the_page` always True 4 / 4, only controls moving; two_up beyond the M8 pair: no dot spaces 3, number+1 3, `_same_ink` blind 2 / 2, `like=` ignored 4, writer page+1 0). The reviewer's levels mutants: bitmap and stream treated as equal 2 (controls), `same_page` comparing a page with itself 3 (controls), footer strip across the whole page or at 0.995 7 each, the band read as a constant line 6, the walk page+1 5, the walk number+1 5, walk numbers by page position run on the class 3; two_up: the reference band rasterised at 1.02x DPI 2 beyond the M8 pair, a constant `_band_lines` 2 beyond the baseline under the probe and 1 unlifted (the single-page test only). A first reference-DPI plant was a NO-OP: `like=` is used only for an `isinstance` check and the DPI comes from the drawn stream itself, so "same DPI" holds by construction, not by anything the tests pin. CARD-356 implication (AC-5): the agreement is REAL (the two `same_page` helpers on `main` both refuse a cross-medium comparison and compare operators plus extent; levels adds a bitmap size check, which is stricter; the only difference is what the twin varies); the "five, not three" question does not arise, but the author's reason ("present before any seam was planted") is loose: both modules are fully GREEN unprobed at the cut and the 8 reds exist only under the probe; the conclusion holds (the cut-probe population of 8 becomes 2, the M8 pair, with no new mechanism after the repair).

Findings, ranked: F-1 (inline, ADR-0039/R3): write residues (1) and (3) INTO the tests with their measured numbers, pin the footer window with a control just past it, and state that grids with 20 or 30 rows and fewer than 30 columns have no footer. F-2 (inline): in two_up the `if isinstance(raw, ContentStream): assert _band_lines(...)` is skipped on the unlifted tree, and the new class calls `_band_lines` only on single pages, so the two-up text-layer read runs only under the probe: add one direct `vector_two_up_page` test; the class docstring's claim that every operators arm runs on both trees is true only for single pages. F-3 (minor): make the guard assert each cited survivor class still holds at least one test. F-4 (wording): residue (2) names only the grid survivor: also cite the digit and furniture classes. F-5 (wording): "present before any seam" becomes "absent unprobed, present under the probe", and 72 becomes 73. Not verified: other poppler versions or trims; whether another module catches a generator that draws every page transposed; the raster twin for 20-row and 30-row grids. METHOD NOTE: the session scratchpad is shared by every agent and mid-review another agent replaced this reviewer's `scratchpad/tip` clone with a CARD-357 clone (caught because the test totals dropped to 60); the reviewer discarded those runs and redid every verdict-bearing run in private clones. Next: a fix round for F-1 to F-5, then the merge gate.

[Fix round for review 1, commit `47da70f9`] Verified by the orchestrator at tip `47da70f9`: worktree clean; one commit over the reviewed `377d3ad4`; over the cut `2eeec589` exactly the two Touches files; `src/`, `tests/helpers`, `tests/test_book_pdf.py`, `tests/test_book_puzzle_frame.py`, `tests/test_book_pdf_band.py`, non-test and `meta/` diffs 0; `git diff --stat 377d3ad4 HEAD` is 2 files, 247 insertions and 23 deletions (`tests/test_book_pdf_levels.py` 183 lines changed, `tests/test_book_pdf_two_up.py` 87); no added bare early-`return` and no added skip or xfail since the review; my own run of the two modules plus `tests/test_suite_profile.py` unlifted gave 531 passed (81 + 450). Author-reported, not re-run by me: unlifted levels 29 + two_up 52 = 81 passed, 0 skipped (the 73 of the review is superseded by the new tests); probe-scoped 79 passed, 2 failed, the two exactly `test_the_control_the_retired_fixed_top_edge_would_share_the_row` and `test_that_row_is_the_top_margin_plus_the_band` with values unchanged (0.2313... and 0.0423... + 1e-09, CARD-352's); the 12 standing census modules plus the two = 1158 passed, 0 failed, 0 skipped. No ids renamed; ids added (G-7): levels +5 (`test_the_footer_window_is_derived_and_a_floor_past_either_end_is_refused`, `test_a_page_with_no_footer_has_no_folio_and_is_refused_loudly`, `test_a_survivor_with_no_tests_is_refused_and_one_with_a_test_is_not`, `test_a_renamed_real_class_with_a_stub_carrying_its_name_is_refused`, `test_a_citation_without_the_tests_prefix_is_derived_not_skipped`) and two_up +3 (`test_the_two_up_page_the_writer_draws_carries_both_bands_upper_first`, `test_the_single_and_the_two_up_page_are_drawn_at_one_dpi`, `test_the_band_left_edge_does_not_depend_on_page_parity`).

F-1(3), the footer window: the 0.85 constant is REMOVED; the floor is derived as the top of the row carrying the grid-size label's `x` word (`footer_floor`) and the window is (lowest clue digit, derived floor]. Re-measured by the author as shares of 792 pt for 10x10, 20x20, 30x30, 15x20, 30x10 at pages 6, 7 and 150: footer row top 0.8624 on all; lowest clue digit 10x10 0.587, 20x20 0.7427, 30x30 0.7918, 15x20 0.7427, 30x10 0.5482; the folio read correctly in all 15 combinations; a 20x30 and a 10x30 vector page (pages 6, 7, 150) have no `x` label word and NO footer (the digits near the bottom are clue digits), stated in the test. **DISCREPANCY, unresolved:** the author's 30x30 figure is 0.7918 where the reviewer reported 0.807; both sit below 0.8624 and the window logic is unchanged; the author did not establish why they differ. Asserted by `test_the_footer_window_is_derived_and_a_floor_past_either_end_is_refused` (clue_top < floor and `footer_digits == [folio]` for the five grids at three pages; controls: a floor at the lowest clue digit takes a clue digit for part of the footer, a floor 1 pt past the folio row finds no folio) and `test_a_page_with_no_footer_has_no_folio_and_is_refused_loudly` (no `x` word on 20x30 and 10x30; `footer_digits` raises an `AssertionError` matching "no footer"; matched control the 20x20 page in the same test). Plants on levels unlifted patching `footer_floor` (control the unplanted 29-green run): floor 0.0 moves 4 node ids, floor 0.995 of page height moves the same 4 (the window test, the no-footer test, `test_an_operators_page_is_named_by_its_position_number_tier_and_puzzle` and the folio test); a constant inside the window would stay green, correctly. F-1(1), page-parity residue: the reference band's left edge is 1061 on interior pages 5, 6, 7 and 8, and a two-up page drawn from page 6 and from page 7 also has its upper band at 1061; written into the `TestBookPdf_ABandIsReadInTheMediumItWasWritten` docstring and pinned by `test_the_band_left_edge_does_not_depend_on_page_parity` (control `shift_px=1`: the edge moves to 1062 and `_same_ink` refuses it). **The reviewer's plan plants were NOT reproduced:** the author's `page_number + 1` plant on `puzzle_pages`' plans reds 3 beyond the two M8 (probe), all three tests added this round that call `puzzle_pages` directly and assert the plan's `page_number`, while the original AC-251 tests still red 0 under it (which matches the reviewer's 0, carried), so the position is pinned only at the entry those tests call, not for the page the interior walk draws; the author's `numbers + 1` plant reds 34 (it perturbs every test reading plan numbers), not the reviewer's 2; the docstring says this plainly and says nothing in two_up reads a two-up page's folio.

F-2: `test_the_two_up_page_the_writer_draws_carries_both_bands_upper_first` calls `puzzle_pages` and `vector_two_up_page` directly so it runs on BOTH trees and asserts `_band_lines == ["Puzzle 1 · Easy", "Puzzle 2 · Easy"]`; the class docstring is corrected (the operators arm of `_band_lines` and `_reference_band` runs on both trees; the `isinstance(raw, ContentStream)` assertions inside the AC-251 class run only under the probe, and it says so). Plants on unlifted two_up (control the unplanted 52 green): `_band_lines` returning `[]` moves 2 (the two-up test and `test_the_text_layer_reads_the_band_a_page_of_operators_carries`); `_band_lines` returning the two-up pair constant moves 1 (the single-page test only; the two-up test stays green by construction). F-3: the survivor guard now requires each cited class to hold at least one `test*` method, the citation regex accepts an optional `tests/` prefix, and tmp_path controls cover an emptied class (a helper only), a `pass` stub, a renamed real class with a stub under the old name, a kept class with a test, an unprefixed citation derived, and a missing one reported as "0 definitions". F-4: residue (2) now lists the classes in `tests/test_book_puzzle_page_vector.py` and what each holds (grid `TestPuzzlePage_AgreesWithTheRasterTwin`, clue digits `TestPuzzlePage_EveryClueDigitRendersWhereTheLayoutPutIt`, band `TestPuzzlePage_BandCarriesNumberAndTierAndNeverTheTitle`, furniture `TestSheetFurniture_TheProductionPageCarriesTheFurniture` and `TestSheetFurniture_TheFooterIsAllOrNothing`), all five guarded; measured: one stray rule added to every content stream of that writer module reds 19 failed + 17 errors across 17 classes, including every class above except the clue-digit one (the plant also lands in the module's own control streams, so this is not a count of real catches; the corner and footer-left positions gave identical results, so they do not discriminate); the clue-digit class was not moved by a stray rule and the docstring says its claim is by name only, not plant-measured; carried from the review, not re-measured and labelled so: a stray rule at the left of the footer zone 1 in levels and 17 beyond the M8 pair in two_up, the grid shifted 1 pt 0 and 1, the corner rule 0 and 0, transposed pages 0 and 1. F-5: the levels module docstring now says both modules are fully green unlifted and the reds are ABSENT unprobed, present only under the probe; the `_reference_band` docstring says the DPI is the drawn stream's own, by construction, because `like=` is only an `isinstance` check, and the "same DPI" wording is removed; one pin added, `test_the_single_and_the_two_up_page_are_drawn_at_one_dpi` (both drawn streams have `dpi == 300`; it pins the streams' DPI, not the rasteriser call). Not done by the author: the reviewer's grid-shift and transposed-page plants were not re-measured; the plan `numbers + 1` figure of 2 was not reproduced; `tests/test_book_pdf.py` and `tests/test_book_puzzle_frame.py` and the full suite were not run. Next: the merge gate.

