# CARD-329: The one-image reader learns the content stream — AC-3's real content, separated from the three causes that were not readers

**Status:** done
**Priority:** P1 <!-- RAISED P2 -> P1 2026-10-30 on the owner's "move from raster to vector first". It is on the critical path to CARD-322, which is the card that finally gives the vector interior a reader -- nothing in `src/` turns an interior page into operators until it lands. CARD-330 was already P1; these three are one front and a split priority would have the dispatcher take them in the wrong order. -->
**Category:** tech-debt
**Estimate:** 2d <!-- RE-CUT 2026-10-31 from 0.75d on the owner's "re-cut 329". 0.75d priced the helper fix plus a triage; this card now also REPAIRS the population-B modules its triage names, and builds the verification that makes AC-4 capable of failing. Five modules, a helper, and a harness. -->
**Complexity:** moderate <!-- RAISED from `standard` at the re-cut: the card now spans a shared helper, five test modules and a verification mechanism, and its conflict surface is what sequences it against CARD-322. -->
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** `card/329-one-image-reader-learns-the-stream`
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-329
**Source:** CARD-309's implementation round, 2026-10-30 — cause 1 of the four that blocked its AC-1, and **the only one of them that is actually a PDF reader**. Its AC-3 was written as though all of the breakage were this, which is why the card could not close.
**Idea:** —
**Wave:** 72 <!-- STAMPED 2026-10-31 at dispatch, opening wave 72 after wave 71 closed two-for-two. Re-cut the same day on the owner's call: it now REPAIRS population B, not just triages it. Measured free of CARD-316 (intersection EMPTY). Its one conflict edge is tests/test_book_pdf.py with CARD-322, which serializes them in the intended order -- this card lands first and CARD-322 consumes its AC-6 output. It is CARD-322's LAST open dependency. -->
**Created wave:** 69
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/helpers/pdf_pages.py, tests/test_book_pdf.py, tests/test_book_pdf_levels.py, tests/test_book_pdf_two_up.py, tests/property/test_book_pdf_geometry.py, tests/test_book_puzzle_frame.py, tests/test_book_cell_size.py <!-- WIDENED 2026-10-31 at the re-cut, by the five unowned population-B modules. DELIBERATELY EXCLUDED: tests/test_book_difficulty_dots.py and tests/helpers/round_ink.py (CARD-331's, G-3) and tests/helpers/page_ink.py (CARD-330's, G-2). -->
**Review score:** 9.0 (cycle 3 of 3 — CERTIFIED; 6.5 → 7.5 → 9.0; no Critical, no Important, one non-gating Minor — F-011, closed at the merge gate by re-derivation)
**Started:** 2026-10-31T06:47:15+00:00
**Closed:** 2026-10-31T10:52:18+00:00
**Actual:** 4.1h wall-clock against a 2d estimate (measured from Started, not estimated)
**Merge commit:** `9db10da6` — gate green on the merged tree: 10101 passed / 0 failed / 27 skipped / 1 xfailed in 1288s. Skips attributed from `-rfs`, not from memory: **26** from the bare `DATABASE_URL` check at `tests/conftest.py:207` ("Database not reachable: DATABASE_URL is not set") and **1** from the `setrlimit(RLIMIT_AS)` platform gate at `tests/test_book_pdf_memory.py:1297`; the per-worktree `*_test` resolution gate did NOT fire. G-5 re-derived twice on the merged tree and agreeing: the card's own `ast` walk over the seven `Touches` paths gives 282 → 310, and pytest's own whole-suite collection gives 10101 → 10129 — **0 lost, 28 gained, the two instruments naming the IDENTICAL 28 node ids**. Validator of record (the forge_1 copy, read-only): 0 errors / 88 warnings on main before the merge and on the merged tree, with the WARN **sets** compared by `comm` rather than by total — empty symmetric difference in both directions, so no `+1/-1` pair hides inside the unchanged total, and no dead-ref warning DISAPPEARED, which is the empirical proof that merging `scratchpad/card329/*.py` revived no dead check ref. Merged onto `59eb2126`, one kanban bookkeeping commit past the `ce2765dd` the gate brief named (`board.md` + `dispatcher.state` only, no `tests/` and no `src/`, so the baseline is unaffected).
**Blocked by:** —

## [Re-cut 2026-10-31] — the owner's call, and the vacuity it exposed

**Re-cut at the decompose station on the owner's instruction ("re-cut 329"), before
dispatch.** The question put to them was whether this card should also *repair* the
population-B modules it classifies, or only triage them; they chose repair. What the
re-cut changed:

| | was | now |
|---|---|---|
| item 3 | classify B, raise scope findings | classify B **and repair** the five it owns |
| AC-4 | "all 21 modules pass" | passes **under a declaration-lifting probe** |
| AC-5 | two mutants on the helper | **plus one per repaired module** |
| AC-6 | — | **new**: the five are repaired, with a stated disposition each |
| `Touches` | 2 paths | **7** — the five unowned population-B modules added |
| estimate | 0.75d | **2d** |
| complexity | standard | moderate |

**The re-cut found a defect worth more than the scope change: AC-4 could not fail.**
It read "all 21 modules pass" without naming a converted tree — and on `main` nothing
is converted, so all 21 pass with an empty diff; the suite is green at 10,033. That is
this family's signature failure, recorded in the orchestrator's own notes after four
consecutive cards hit it: **a premise about a tree that does not exist, asserted as
though it did.** The difference here is that it was caught at the decompose station
rather than in the round, which is where the four earlier ones were caught, and the
fix is the mechanism rather than the wording — AC-4 now runs under a probe, and the
round's first job is to record the red count **before changing anything**.

**What this card is NOT, after the re-cut.** It still converts no page and flips no
rule; CARD-322 performs the conversion. It does not touch the three files owned by
CARD-330 and CARD-331. And its triage may still report a module outside `Touches` that
needs an edit — that remains a scope finding to raise, not a licence to widen.

**Conflict graph re-measured at the re-cut** (the widened `Touches` is what changes
it): CARD-329 ∩ **CARD-331 is EMPTY** and CARD-329 ∩ **CARD-316 is EMPTY**, so this
card runs concurrently with either. Its one edge is **CARD-329 ∩ CARD-322 =
`tests/test_book_pdf.py`**, which serializes them in the order already intended —
this card lands first, and CARD-322 consumes its AC-6 output. No
`conflict.hotspots` entry is in the widened set.

**Two downstream records already point here, and both were corrected to do so:**
- **CARD-322's scope note.** It had asked CARD-322 to choose a disposition per module
  for eleven modules. That per-module disposition is **this card's** AC-6 output, so
  CARD-322 consumes it rather than producing it. Of the eleven: four are population A
  (the helper fix reaches them), five are the population-B modules now in this card's
  `Touches`, one is CARD-331's and one is CARD-330's.
- **CARD-288**, gated the same day because its performance premise dissolved into
  CARD-322. Its file (`property/test_book_pdf_geometry.py`) is now in **this** card's
  `Touches`, so this card is the likely successor for the half that matters — making
  that module survive the conversion. CARD-288's own subject, not materialising 3,820
  bitmaps, stays dissolved: after the conversion there are no bitmaps to avoid.

## Why this card exists

CARD-309's AC-3 said *"every test module that reads a book interior passes — the 12
test modules that import `tests/helpers/pdf_pages.py`'s one-image reader"*. When the
conversion was implemented, 22 modules broke — and **root-causing them showed only
one cause was a reader**: `pdf_pages.py`'s one-image reader raising
`KeyError: b'XObject'` on a page that has no image XObject because it is now
operators. The other three causes were independent pixel oracles (**CARD-330**), an
accounting instrument monkeypatching a raster drawing site that a vector page never
calls (**CARD-331**), and frozen AST censuses CARD-309 re-derived itself.

**This card is cause 1 alone, and it is small.** Separating it is the point: bundled
with the other three it was unclosable, and the bundling is what made CARD-309 look
like a 1-day card.

## The populations, measured — and AC-3's blind spot, which this card inherits

CARD-309's round derived both by AST (`derive_readers.py`) and the figures are the
ones to re-derive here:

- **Population A = 12 modules** that import the one-image reader itself. This
  reproduces CARD-309's AC-3 exactly. (Its earlier figure of "14 modules plus 3
  helpers" did **not** reproduce: 18 files *mention* the string, 14 import *something*
  from the helper, and only 12 import the reader. `tests/helpers/book_corpus.py`
  imports only `pdf_page_count`, `tests/test_book_toc.py` only `same_page`, and
  `tests/property/test_book_pdf_geometry.py` imports it **zero** times — matching a
  grep only because three of its node ids end in `_pdf_pages`. A mention count is
  not a reader count.)
- **Population B \ A = 9 modules** that never import the reader but reach the same
  hazard through `.interior()` / `.interior_pages()` and use the returned pages as
  images — invisible to A's derivation. CARD-309 named 8 and the round found a 9th
  (`tests/helpers/book_corpus.py`).

**Both populations are in scope.** Per ADR-0039/R2 a module the walk cannot classify
is a **FAILURE**, not a silent pass.

## What to implement

1. **Give the one-image reader a medium-aware path.** A page that is operators has no
   image XObject; the reader must either read the stream or say clearly that the page
   is not a bitmap — **decide which, and state why**. A `KeyError` on a legal page is
   the current behaviour and is the defect.
2. **Keep it a reader, not an oracle.** `pdf_pages.py` is a convenience reader used by
   assertions; `tests/helpers/page_ink.py` holds the independent pixel oracles and is
   **CARD-330's, not this card's** (G-2). Do not fold them together — they exist
   separately on purpose.
3. **Classify population B per module, then REPAIR the ones this card owns.**
   *Re-cut 2026-10-31 on the owner's decision: triage alone was the deliverable and is
   no longer.* For each population-B module, derive whether item 1's helper change is
   enough or whether the module needs its own edit — and then **make that edit**, for
   every module in `Touches`. Three are deliberately **not** this card's and stay
   excluded by G-2/G-3: `tests/test_book_difficulty_dots.py` and
   `tests/helpers/round_ink.py` are CARD-331's, `tests/helpers/page_ink.py` is
   CARD-330's. A module outside `Touches` that the triage finds needs an edit is still
   a scope finding to be raised, not a silent widening.
4. **Do not convert any page**, and **verify against a tree where one is converted.**
   This card makes the readers survive a conversion CARD-322 performs. Two mechanisms
   exist **on main** for standing that counterfactual up without touching a production
   medium, and the card must use them rather than reason about the converted tree:
   - `nonogram.admin.book_interior_vector.interior_generator(book, pages=…)` — merged
     with CARD-309 and still with **zero production call sites**; its `pages` override
     exists precisely so a test can hand in a writer set instead of mutating the thing
     under test, and its own docstring says so. `src/` is **read, never edited** (G-6).
   - **A declaration-lifting session probe**, the mechanism CARD-331 used to measure a
     converted tree (29 failed / 160 passed) from a scratchpad plugin that lifts
     `PageKind.PUZZLE` out of `_RASTER_DECLARATIONS` for one run. Build this card's own;
     do **not** import a sibling card's scratchpad.

## Acceptance criteria

- **AC-1** (the reader survives an operators page): *Given* an interior page written
  as content-stream operators, *then* the one-image reader returns a usable result or
  refuses with a message naming the medium — **never `KeyError: b'XObject'`**. (test:
  `TestPdfPagesReader_AnOperatorsPageIsNotAKeyError`)
- **AC-2** (the reader still works on raster): *Given* a raster page — the cover and
  the divider stay raster by ADR-0042/R2 — *then* the reader behaves exactly as
  before, byte for byte in its result. (test:
  `TestPdfPagesReader_ARasterPageIsUnchanged`)
- **AC-3** (both populations are derived, not listed): *Given* the tree, *then* the
  card records population A and population B\A **derived by AST** with their counts,
  and every module is classified — nothing unclassified (ADR-0039/R2). The expected
  counts re-derive CARD-309's: **A = 12**, **B\A = 9**. A different number is a
  finding, and the derivation is what is asserted, not the number.

  **A different number has already turned up, so resolve it first.** The orchestrator
  derived these independently on 2026-10-31 and got **A = 14, B\A = 6**. Neither pair
  is "right" — they are different *bases*, and the card's own warning that *a mention
  count is not a reader count* is the reason:
  - **A = 14** counts modules importing **anything** from the helper; **A = 12** counts
    modules importing the **reader**. The card already records the gap (`book_corpus.py`
    imports only `pdf_page_count`, `test_book_toc.py` only `same_page`), so 14 and 12
    are the same measurement at two filters, and **12 is the one AC-3 means**.
  - **B\A = 6 vs 9** is not reconciled. The orchestrator's filter required both a
    page source (`interior`/`interior_pages`) **and** a direct PIL attribute use, which
    misses a module that hands a page to a helper instead of touching it. **Derive B by
    the hazard, not by the attribute**: a module reaches it if a page from that source
    is used as an image anywhere downstream, however indirectly.
  State the filter for each population in one sentence beside its number, and if the
  reconciled figure is neither 9 nor 6, that is the finding AC-3 asks for. (test:
  `TestPdfPagesReader_BothReaderPopulationsAreDerived`)
- **AC-4** (every reader in both populations passes **on a converted tree**): *Given*
  a run under this card's declaration-lifting probe — a tree where `PageKind.PUZZLE`
  is written as operators — *then* every module of population A and population B
  passes, with **every skip attributed by name** (this suite's skips are
  `DATABASE_URL`-gated and the browser fixtures refuse loudly without Chromium,
  ADR-0038/R8, so green-with-skips must not read as verified). (test: the modules
  themselves, run by node id with `-o addopts=''`, under the probe)

  **THIS AC WAS VACUOUS AS FIRST WRITTEN AND THAT IS WHY IT CHANGED.** It said "all 21
  modules pass" with no mention of a converted page — and on `main` nothing is
  converted, so **every one of the 21 passes by doing nothing**: the whole suite is
  green at 10,033 passed. An AC satisfied by an empty diff is narrative, not coverage
  (ADR-0039/R1), and it is the same shape this card family keeps producing — a claim
  about a tree that does not exist, asserted as though it did. The probe is what makes
  the criterion capable of failing: **run it before changing anything and record the
  red count**, because that number is the card's starting measurement and its absence
  is how this AC passed review as written.

- **AC-6** (the population-B modules this card owns are repaired, not just classified):
  *Given* the probe's run, *then* each of the five population-B modules named in
  `Touches` — `test_book_pdf_levels.py`, `test_book_pdf_two_up.py`,
  `property/test_book_pdf_geometry.py`, `test_book_puzzle_frame.py`,
  `test_book_cell_size.py` — passes under it, and the card states **per module** which
  of three dispositions it took and why: the helper change sufficed, the module was
  edited, or the module's claims were retired with a named survivor. A module left
  green only because the probe does not reach it is **not** repaired, and saying so is
  the AC. (test: the five modules, by node id, under the probe)
- **AC-5** (the change can fail): **Two mutants on the helper** — one that makes the
  reader return a wrong page for an operators page, one at the edge that makes it
  mis-handle the raster path — both killed. **Plus one mutant per repaired module**
  (AC-6's five): a plant that re-breaks that module's own repair, each killed, each
  with its matched control measured green in the same run. A repair with no plant is
  a claim, not a fix. (evidence: the mutant table in `## Worktree notes`)

## Guardrails

- **G-1: convert no page and flip no rule.** CARD-322 owns the conversions and
  ADR-0042/R1; CARD-312 owns R6's flip.
- **G-2: do not touch `tests/helpers/page_ink.py`.** Its `drawing_of` and `two_up_ink`
  are the independent pixel oracles and are **CARD-330's** subject. Folding a reader
  and an oracle together destroys the cross-check CLAUDE.md requires.
- **G-3: do not touch `tests/test_book_difficulty_dots.py` or
  `tests/helpers/round_ink.py`** — **CARD-331's**.
- **G-4: do not lower a corpus minimum** and regenerate nothing under
  `tests/fixtures/**`. No baseline moves in this card.
- **G-5: no test deleted, renamed, skipped or merged**, `parametrize` ids included
  (gate: node-id set difference with `-o addopts=''`).
- **G-6: do not edit `src/nonogram/admin/**`.** This card is test-side only and its
  `Touches` says so. *(De-staled 2026-10-31: the original reason was "CARD-309's
  worktree is open on those files" — CARD-309 **merged** as `db366763`, so that reason
  is gone and the guardrail is not. It stands on its own: this card makes readers
  survive a conversion, and CARD-322 performs the conversion. `interior_generator` and
  the declaration probe are both read-only uses of `src/`.)*
- **G-7: probes stay OUT of `tests/`** (`RENDER_HEAVY_SNAPSHOT`).

## System contract

- ADR-0042/R6 — a claim about an interior page is asserted against the content stream (check: CARD-299's)
- ADR-0042/R2 — a raster page is declared with a reason; the cover and divider stay raster, which is why AC-2 exists (check: CARD-298's derived guard)
- ADR-0039/R2 — a guard's set is derived and an unanalysable shape is a FAILURE (check: AC-3)
- ADR-0039/R1 — a claim needs a control that CAN fail (check: AC-5's mutant pair)
- ADR-0038/R8 — a browser test refuses LOUDLY when Chromium is absent, never skips green (check: AC-4's skip attribution)
- CON-020 — the 10 pt interior type floor; CARD-314 marked the clue digits so the exemption survives by the mark rather than by the size (check: CARD-299's re-expressed test)

## Architecture context

- **FR:** FR-030, FR-032, FR-040
- **ADR:** ADR-0042/R2, R6, ADR-0039/R1-R2
- **Components:** COMP-009
- **Trace:** not updated by this card

## Worktree notes

- **[It is cause 1 of four, and the only reader]** The other three are CARD-330 (the
  pixel oracles and the 0.169 mm question), CARD-331 (the difficulty-dot accounting
  instrument) and a frozen-census re-derivation CARD-309 already completed. Keeping
  them apart is what makes each closable.
- **[Re-derive the two populations; do not trust the numbers above]** 12 and 9 are
  CARD-309's round's figures, and that round corrected an earlier "14 plus 3" that did
  not reproduce. A mention count is not a reader count — the lesson is in AC-3.

### The round, 2026-10-31

- **[THE STARTING MEASUREMENT, taken before a line of the tree changed]** Under
  this card's declaration-lifting probe
  (`scratchpad/card329/probe_puzzle_operators.py`, run by
  `scratchpad/card329/measure_probe.py` at commit `adcea9a1`, which carries the
  instruments and nothing else): **20 of 20 modules RED, 259 failed+error,
  1088 passed, 1 skipped.** The one skip was attributed by `-rs` and is
  `tests/test_book_pdf_memory.py:1297` — `setrlimit(RLIMIT_AS)` refused by this
  kernel; it is not DB-gated and not a browser fixture.
  This is the number whose absence made AC-4 vacuous, and it is now the card's
  floor.
- **[AC-4's "21 modules" is 20, derived]** A (12) + B\A (9) = 21 *files*, but
  `tests/helpers/book_corpus.py` is a helper and collects **zero** test nodes,
  so 20 modules are runnable. A criterion counting 21 runnable modules could
  not have been met by any tree.
- **[AC-3, both populations, each filter in one sentence]** Derived by AST
  (`scratchpad/card329/derive_populations.py`, and independently inside
  `TestPdfPagesReader_BothReaderPopulationsAreDerived`, which asserts the
  filters rather than the counts).
  - **A = 12.** Filter: the module's AST holds an `ImportFrom` of
    `tests.helpers.pdf_pages` that names **`pdf_pages`**, the one-image reader.
    This reproduces CARD-309's figure exactly.
  - **B \ A = 9.** Filter: the module obtains a page from
    `interior`/`interior_pages` and that page is used **as an image** anywhere
    downstream, directly or through a function that itself uses a parameter as
    an image — the hazard, not the attribute.
  - **Unclassified = 0** (ADR-0039/R2).
  - **A = 14 vs 12 is settled as the card said:** two filters, one
    measurement. Re-derived here, "imports *anything* from the helper" is now
    **19**, not 14 — because this card's own commit adds an `interior_images`
    import to five of those modules plus this file. The card's 14 was correct
    for the tree it was written against; a figure about imports moves when
    imports are added.
  - **B\A = 6 vs 9 is resolved at 9, and the SET differs from the card's.** The
    nine are `helpers/book_corpus.py`, `property/test_book_pairing.py`,
    `property/test_book_pdf_geometry.py`, `test_book_cell_size.py`,
    `test_book_difficulty_dots.py`, `test_book_divider_pages_option.py`,
    `test_book_pdf_levels.py`, `test_book_pdf_two_up.py`,
    `test_book_puzzle_frame.py`. `tests/helpers/page_ink.py` is **not** among
    them, although CARD-322's scope note counts it as one: it never obtains a
    page, it is *handed* one, which is precisely why it is one of the page
    **consumers** that put `test_book_pairing.py` into B. The count agrees with
    the card by coincidence of arithmetic, not of membership.
  - **The closure is load-bearing and was measured.** Taken at depth 1 the
    consumer walk does **not** recognise `page_ink.drawing_of`, the tree's
    central pixel oracle, because it reads nothing off its own `page` and hands
    it to `_dark` one frame in. B's membership is unchanged by closing the walk
    to a fixed point, which is what makes 9 robust rather than lucky.
  - **The two implementations of A disagreed, and the AST was right.** The
    text-scan cross-check did not see this file's own new import, which is
    parenthesised over five lines. That is the finding two implementations
    exist to produce (CLAUDE.md:52); the scan now reads both forms.
- **[The reader: it RETURNS, and the reason is that a refusal changes no
  verdict]** `pdf_pages` now rasterises an operators page with **poppler** and
  hands back a `PIL.Image.Image`; it refuses — naming the medium, the page and
  the remedy — only when no DPI to rasterise at can be established, and when
  poppler is absent (ADR-0038/R8: a missing engine is a missing reading, never
  a skip). AC-1 left both halves open. Refusing would have satisfied its letter
  and moved **nothing**: all 37 `KeyError: b'XObject'` reds in the baseline are
  callers reading a page's pixels, so a better-worded exception leaves each of
  them exactly as red. ADR-0042/R6 asks that a claim about an interior page be
  asserted *against* that page, so the reader has to produce one. Poppler and
  not an interpreter of ours because the engine must not be the one that wrote
  the file (CLAUDE.md:52); it is also the seam this tree already chose — this
  module's own `_edge_reading` writes one `ContentStream` out and measures
  poppler's raster of it. **37 of the 37 `KeyError` reds are cleared by the
  helper alone** (36 in population A plus 1 shared), e.g.
  `test_book_interior_face.py` goes 3 failed → 0.
- **[AC-6, the five, one disposition each]** The seam edit is the same shape in
  all five — `interior_images` at the module's one page-source function — and
  it is **necessary in all five and sufficient in one**. Figures are per-module
  reds under the probe, before → after.
  | module | before | after | disposition |
  |---|---|---|---|
  | `test_book_cell_size.py` | 20 | **0** | **REPAIRED — edited.** The helper change alone reaches nothing here (this module never imports the reader); the seam edit does all of it. |
  | `test_book_pdf_levels.py` | 10 | 4 | **EDITED, NOT REPAIRED.** The four survivors compare a page byte-for-byte with `expected_puzzle_page`, a **raster** page the module composes by hand. Cross-medium byte identity cannot hold; the expectation needs composing in the page's own medium, which re-opens what its independent form is. |
  | `test_book_pdf_two_up.py` | 24 | 4 | **EDITED, NOT REPAIRED.** Two survivors are the same byte-identity family as above; two are pixel-row claims about the upper slot's top edge. |
  | `test_book_puzzle_frame.py` | 22 | 4 | **EDITED, NOT REPAIRED.** All four are `TwoUp` stroke-weight and placed-edge claims: the two-up page reads weights `[2, 4, 6]` where it declares two, the third weight being a boundary-straddling rule read one pixel wider. |
  | `property/test_book_pdf_geometry.py` | 4 | 4 | **EDITED, NOT REPAIRED.** All four node ids of the module are red before and after; the edit moved their cause from `AttributeError: 'ContentStream' object has no attribute 'size'` (x3) and `…no attribute 'convert'` to a placed-edge disagreement. **Each residual is stated against the bound its own site carries**, and the bound is not `EDGE_TOLERANCE_MM`: that token appears **0** times in this module (`grep -c EDGE_TOLERANCE` = 0). The module defines `PX_PER_MM = 300 / 25.4` and `HALF_PIXEL_MM = 0.5 / PX_PER_MM` = **0.042333 mm** (`:69-70`) and each of the four sites is bound by a different **multiple** of it — **re-measured at cycle 2's fix round, two clean runs agreeing to every printed digit** (4 failed / 0 passed / 0 skipped): `:435` **0.26264 mm** against `3 x HALF_PIXEL_MM` = 0.12700 mm, **2.07x**; `:527` **0.29931 mm** against `3 x` = 0.12700 mm, **2.36x**; `:660` **0.28800 mm** against `2 x` = 0.08467 mm, **3.40x**; `:836` **0.23133 mm** against `1 x` = 0.04233 mm, **5.46x**. There is deliberately **no single range** over the four: they are governed by three different multiples, so a range across them would be normalised against nothing. This row used to say "0.254 mm", the aliasing figure, which understated what these sites see at three of them — but **not at `:836`, where 0.23133 < 0.254** and the aliasing figure accounts for more than the whole residual. Which strengthens the disposition rather than weakening it: every one of the four is 2x–5.5x past the bound it actually carries, the widening that would close them is far bigger than the card's aliasing figure implies, and the frame-centre oracle is the only thing that closes them without one. *(Provenance: these four figures were carried from cycle 1's own observation — 0.263 / 0.299 / 0.288 / **0.289** — and cycle 2's F-009 found the fourth wrong by 25% and the yardstick wrong for all four. The values above are re-read off a fresh run at `ea248582`; this module **is** in the fix delta, 19 insertions / 4 deletions, so "untouched, therefore unchanged" was never available as a reason.)* |
  Total across the five: **80 → 16**. None of the 16 is green-because-unreached:
  every one is a measured red, named above.
- **[Why the 16 are not a tolerance away, measured]**
  `scratchpad/card329/probe_aliasing.py` reads the SAME page in both media at
  300 DPI through the SAME oracle (`page_ink.drawing_of`):
  - the grid's four edges: **1 device pixel, 0.0847 mm**;
  - the drawing's own left/top edges: **3 device pixels, 0.254 mm** — a lower
    bound on what a site sees at *three* of the four
    `test_book_pdf_geometry.py` sites and an **upper** bound at the fourth,
    re-measured at cycle 2's fix round: 0.26264 (`:435`), 0.29931 (`:527`)
    and 0.28800 mm (`:660`) each exceed it, so there the aliasing accounts
    for most of the residual but not all of it; at `:836` the residual is
    **0.23133 mm**, below 0.254, so the aliasing figure accounts for *more*
    than the whole of it. The figure is therefore a lower bound at three
    sites and not a bound at all at the fourth — stated that way rather than
    as one range, because the four sites are bound by three different
    multiples of `HALF_PIXEL_MM` (3/3/2/1) and share no yardstick;
  - **identical with poppler's antialiasing on and off** (`-aa`/`-aaVector`),
    so it is not a halo; it is the two writers' line-placement conventions.
  These two numbers reproduce, independently, the two that
  `ADR-0042`'s own `_RASTER_DECLARATIONS` note already records as "what a
  conversion really moves" — and that note says the 0.254 mm needs **an oracle
  that reads a frame rule's CENTRE rather than its first inked line**, assigns
  that oracle to **CARD-322**, and says in as many words that *CARD-329 owns
  the readers and need not re-measure this*. **`EDGE_TOLERANCE_MM` stays 0.1
  and nothing was widened** (CARD-330's G-1, inherited).
- **[The scope finding, which is the honest shape of AC-4]** AC-4 asks that
  every module of A and B pass under the probe. Within this card's seven
  `Touches` paths that is unreachable, and the measurement says where the rest
  lives:
  - **7 population-A modules** carry `ContentStream`-attribute reds of exactly
    the kind the five B modules had, and are **not** in `Touches`:
    `property/test_book_export_interior.py`, `test_book_export_interior_cover.py`,
    `test_book_pdf_band.py`, `test_book_pdf_ink_mode.py`,
    `test_book_pdf_memory.py`, `test_book_proof_pages.py`,
    `test_book_solved_answer_key.py`. Each needs the same one-line seam edit.
    *(Cycle 1 re-ran the probe over all 20 modules and confirmed this list of
    seven is the correct one; the dispatcher's copy carried
    `test_book_arrange_page_breaks.py` and dropped `test_book_pdf_ink_mode.py`,
    which is red at 10 before and 10 after and does belong here. The
    orchestrator's note has been corrected to this list.)*
  - **2 population-B modules** likewise: `property/test_book_pairing.py` (1
    red) and `test_book_divider_pages_option.py` (3 reds).
  - **`test_book_difficulty_dots.py` is red at 29 under the probe** — the same
    29 CARD-331 measured — and is excluded by **G-3**. AC-4 and G-3 cannot both
    be satisfied; G-3 wins, and the contradiction is the finding.
  - **`test_book_pdf.py`'s registry guards red under the probe and SHOULD.**
    Six of its reds are assertions *about* `_RASTER_DECLARATIONS` ("the registry
    no longer declares `['puzzle']` and the comment above it claims nothing was
    taken out"). The probe lifts a declaration and nothing else, so those
    guards are doing their job. They are not defects and must not be repaired
    here — CARD-322 updates registry, comment and card together.
  - **Two population-A modules are red for a reason that is NEITHER of the
    above, and cycle 1's F-004 is that this list did not say so.** The note
    undertakes to place the *whole* residue and these two landed in no bucket:
    `test_book_arrange_page_breaks.py` (**1** red,
    `ValueError: too many values to unpack (expected 1, got 2)` at `:753` — a
    `two_up_ink` reading that finds two drawings where one is expected on a
    poppler-rendered page) and `test_book_guide_page.py` (**1** red,
    `AssertionError: (6, -62.0)` / `assert 2.944881889763778 <= 2` at
    `:1682`). Both are **pixel-oracle readings of a converted page** — a
    disagreement between the oracle and the rendered geometry, which is
    CARD-312's per-site disposition and CARD-322's frame-centre oracle, **not
    the one-line seam edit** the seven above need. Routing them with the seven
    would be the wrong instruction, which is why they get their own bullet
    rather than a longer list. *(The orchestrator's note now carries both with
    this reasoning; this card and that note agree.)*
  - **The arithmetic closes, so nothing is left for a reader to discover.**
    The 151 residual reds, per module, summed from the final measurement
    below: the nine routed modules **66** (`test_book_pdf_band.py` 23,
    `test_book_pdf_memory.py` 23, `test_book_pdf_ink_mode.py` 10,
    `property/test_book_export_interior.py` 2,
    `test_book_export_interior_cover.py` 2, `test_book_proof_pages.py` 1,
    `test_book_solved_answer_key.py` 1, `test_book_divider_pages_option.py` 3,
    `property/test_book_pairing.py` 1) + the two just placed **2** +
    `test_book_pdf.py` **38** + `test_book_difficulty_dots.py` **29** (G-3) +
    the five modules this card repaired **16** = **151**. Three modules are at
    0 and are the three that went green.
- **[AC-5, twenty-four plants, every control green with 0 skipped in the same run]**
  `scratchpad/card329/mutate.py`. **22 KILLED, 2 DECLARED SURVIVORS.** (Twelve
  at the first pass, 13-15 at the gap this card's own helper opened,
  16/16b/17/18/19 at cycle 1's F-001, F-002 and F-003, and 20-23 at cycle 2's
  F-008.)
  | plant | what it breaks | verdict | node it reds |
  |---|---|---|---|
  | MUT-1 | **inside the claim**: an operators page comes back as a raster page the reader already decoded | KILLED | `…AnOperatorsPageIsNotAKeyError::test_an_operators_page_inside_a_file_reads_beside_its_raster_pages` |
  | MUT-2 | **at the claim's edge**: a raster page comes back as a converted copy, equal bytes and a different object | KILLED | `…ARasterPageIsUnchanged::test_a_live_raster_page_is_handed_back_as_the_very_same_object` |
  | MUT-3 | the raster path's decode mode drifts RGB → L | KILLED | `…ARasterPageIsUnchanged::test_every_raster_page_of_a_whole_book_is_unchanged` |
  | MUT-4 | the DPI the reader cannot establish is GUESSED, not refused (ADR-0039/R2) | KILLED | `…::test_a_file_whose_dpi_cannot_be_established_is_refused_by_name` |
  | MUT-5 | a page in neither medium is passed over as raster | KILLED | `…::test_a_page_in_neither_medium_is_a_failure_not_a_silent_pass` |
  | MUT-6 | AC-3's A filter slides from the reader back to a mention | KILLED | `…BothReaderPopulationsAreDerived::test_population_a_is_the_reader_and_not_a_mention` |
  | MUT-7 | AC-3's indirect half loses its closure and drops `drawing_of` | KILLED | `…::test_the_files_this_card_does_not_own_are_excluded_by_name_not_missed` |
  | MUT-8 | `test_book_cell_size.py`'s seam put back | KILLED | `…SameGridSizeSameCell::test_every_twenty_by_twenty_is_drawn_at_the_same_cell` |
  | MUT-9 | `test_book_pdf_levels.py`'s seam put back | KILLED | `…DifficultyOrderWithDividerPerLevel::test_the_puzzle_section_runs_divider_then_that_levels_puzzles` |
  | MUT-10 | `test_book_pdf_two_up.py`'s seam put back | KILLED | `…TwoSmallSameTierNeighboursShareAPage::test_both_puzzles_print_on_one_page` |
  | MUT-11 | `property/test_book_pdf_geometry.py`'s seam removed, **no probe** | **SURVIVED, declared** | — |
  | MUT-12 | `test_book_puzzle_frame.py`'s seam put back | KILLED | `…PairIsFramedOnThePrintedPage::test_both_slots_read_back_as_framed_drawings` |
  | MUT-13 | a placed-edge site reads its page through `page_image` **inside its own body** | KILLED | `…EveryPlacedEdgeExpectationNamesItsMedium::test_no_site_reads_a_content_stream` |
  | MUT-14 | a name defined nowhere joins the medium-blind exemption register | KILLED | `…::test_every_public_reader_of_the_two_owners_is_classified` |
  | MUT-15 | `page_image` stops crossing the medium, so the set's *reason* goes false | KILLED | `…::test_the_pixel_returning_stream_readers_really_cross_the_medium` |
  | MUT-16 | **the same crossing one frame in**, at `_interior` — the seam shape CARD-322 is handed. The plant cycle 1 fired and watched survive | KILLED | `…::test_no_site_reaches_a_stream_reader_through_a_helper_either` |
  | MUT-16b | MUT-16 against the **depth-0** cell, which must not see it — otherwise the two cells are one assertion written twice | **SURVIVED, declared** | — |
  | MUT-17 | the derivation is replaced by the retired hand-written set, dropping `rendered_page` and eight more (nine of the 16, named in the cell's own `unclassified` list) | KILLED | `…::test_every_public_reader_of_the_two_owners_is_classified` |
  | MUT-18 | the poppler guard in `page_image` stops guarding: a missing engine reads a page instead of saying the reading is MISSING | KILLED | `…AnOperatorsPageIsNotAKeyError::test_a_missing_poppler_is_a_missing_reading_and_never_a_skip` |
  | MUT-19 | raster pages at **disagreeing** DPIs settle a scale anyway — `_derived_dpi` pops one instead of refusing | KILLED | `…::test_raster_pages_at_disagreeing_dpis_are_refused_not_averaged` + `…::test_the_dpi_derivation_itself_answers_none_only_when_it_must` |
  | MUT-20 | MUT-16's crossing at a **new** site whose bare name collides with a registered exemption in a different class — the dodge that needed no register edit | KILLED | `…::test_every_site_reads_its_page_through_the_raster_ink_oracle` + `…::test_no_site_reaches_a_stream_reader_through_a_helper_either` |
  | MUT-21 | MUT-20's **matched control**: the identical site and helper under a bare name that also already exists in this module but is **not** registered, so registration is the only variable between the two | KILLED | the same two cells |
  | MUT-22 | the exemption lookup degrades back to `_bare()`, the regression that opened the hole and the one that fails silently | KILLED | `…::test_the_exemption_lookup_does_not_strip_the_class` |
  | MUT-23 | the register collapses to an empty `frozenset` — every subset assertion it had is satisfied vacuously | KILLED | `…::test_the_exemption_list_names_only_sites_that_exist` + `…::test_the_exemption_lookup_does_not_strip_the_class` |
  **MUT-11 is where this card cannot meet AC-5, and it says so.** All four of
  `property/test_book_pdf_geometry.py`'s node ids are red under the probe both
  before and after the edit, so the module holds **no green node** to be a
  matched control. The plant that can be measured is the other direction —
  removing the seam with no probe running must change nothing, because
  `interior_images` is the identity on a raster page — and it is declared a
  survivor for that reason. A plant that reddened there would mean the seam had
  altered a raster reading, which is AC-2 at module scope.
- **[G-5, derived]** Node-id set difference over all seven `Touches` paths
  against `f7ba9c96`, by `ast` (`scratchpad/card329/node_ids.py` — not
  `--collect-only`, which prints no node ids under this project's
  `addopts = "-q"`): **282 → 310, 0 lost, 28 gained.** Nothing deleted,
  renamed, skipped or merged. *(Re-derived at every fix round. Round 1 added
  7 cells — 4 on the pin and the derivation, 3 on the refusal branches —
  giving 309; round 2 adds the 8th, `test_the_exemption_lookup_does_not_strip_the_class`
  (cycle 2's F-008), giving 310. The reading this note first carried,
  "282 → 300, 18 gained", was taken before `bd14c108` and was cycle 1's
  F-006: the node count was refreshed to 302 in the note below and this one
  was not. Both now come from the same run of `node_ids.py f7ba9c96`, and
  the arithmetic closes: 282 + 20 + 7 + 1 = 310.)
- **[G-1/G-6 hold]** No page converted, no rule flipped, nothing under `src/`
  edited. Every one of the seven page kinds is declared raster on `main`, so a
  mixed-medium file cannot be built from the rules in force; the one test that
  needs one lifts PUZZLE's declaration under `monkeypatch` for its own
  duration, which is the session probe at test scope.
- **[FINAL measurement under the probe, RE-RUN WHOLE at the merge gate]** 20
  modules, one run each (`scratchpad/card329/measure_probe.py`): **17 of 20 RED
  (was 20 of 20), 151 failed+error (was 259), 1224 passed (was 1088), 1
  skipped** — the
  `setrlimit` skip at `tests/test_book_pdf_memory.py:1297`, attributed by `-rs`
  and not from memory. **108 reds cleared.** Three modules are fully green
  under the probe: `test_book_interior_face.py` (3 -> 0),
  `test_book_trim_persistence.py` (2 -> 0) and `test_book_cell_size.py`
  (20 -> 0).

  **The passed count derives, which is cycle 1's F-006.** This note first said
  **1214**, and the arithmetic says why that was wrong: 1088 + 108 cleared +
  20 new cells = 1216, while 1214 is 1088 + 108 + **18**, the state before
  `bd14c108` added the gap-closing pair. The two fix rounds add 8 more cells,
  so **1088 + 108 + 20 + 8 = 1224**, which is what the run reports. A figure
  refreshed beside one that was not is precisely the drift
  `config.yml`'s "a count here is a DATED READING, never a current fact" exists
  to catch, and it caught this one — **twice**. It read **1223** until the
  merge gate, from fix round 1, stale by exactly the one cell fix round 2
  added; cycle 3 filed that as F-011 but named only this derivation site, and
  the headline reading above carried the same number, so correcting one would
  have reproduced the finding in the more prominent of the two places. The
  gate did not patch the arithmetic: it **re-ran the whole 20-module census**,
  because an arithmetic correction to a figure nobody re-measured is the same
  defect one level up. The per-module reds come back unchanged from the
  reading below — 151 in total, all 20 modules — so the only thing that moved
  is the one added cell, and it passes under the probe.
  Per module, so the 151 is auditable rather than asserted: 2 / 1 / 2 / 1 / 0 /
  **38** / 23 / 10 / 23 / 1 / 1 / 0 (population A, in `measure_probe.py`'s
  order) and 1 / 4 / 0 / **29** / 3 / 4 / 4 / 4 (population B).
- **[`tests/test_book_pdf.py` is red at 38 under the probe and SHOULD BE]** Its
  placed-edge expectations are pinned to the raster **by design**:
  `TestEdgeOffset_EveryPlacedEdgeExpectationNamesItsMedium` derives every site
  comparing against `EDGE_TOLERANCE_MM` and requires it to read its page
  through `drawing_of` and through no stream reader, so — in that class's own
  words — "when CARD-322 converts a page under one of them, the reading
  changes medium and this goes red until the site says so."
  **All 38 enumerated and classified**, because "none of them is a defect this
  card may repair" reads as "all 38 belong to the pin or the registry" and
  cycle 1's F-005 is that two of them belong to neither:
  - **6** are assertions *about* `_RASTER_DECLARATIONS` itself, which the probe
    lifts and nothing else. They are doing their job.
  - **30** are the raster-pinned 25.45 mm placed-edge family and its
    neighbours, every one reading its page through `page_ink`'s oracle.
    ADR-0042's own `_RASTER_DECLARATIONS` note states the figure they disagree
    by (3 device pixels / 0.254 mm on the drawing's own edges, outside
    `EDGE_TOLERANCE_MM`), assigns the frame-centre oracle that closes them to
    CARD-322, and says in as many words that CARD-329 owns the readers and
    need not re-measure. Model-backed, not an excuse.
  - **2 are this round's OWN new cells, and they are new debt this card hands
    on**: `TestPdfPagesReader_ARasterPageIsUnchanged::test_every_raster_page_of_a_whole_book_is_unchanged`
    and its control `…::test_the_reference_reader_can_tell_a_changed_page`.
    They read a whole interior through `_old_one_image_reader`, the
    pre-CARD-329 body, which indexes `Resources/XObject` unconditionally — so
    they are **raster-only by construction** and will red *permanently* the
    moment CARD-322 converts PUZZLE, not just under the probe. **Disposition
    for CARD-322:** retire them at the conversion, or re-express them as
    "every page the plan declares RASTER is unchanged", which survives it.
    Either is safe, because AC-2's medium-durable half already exists beside
    them — their `export.cover` sibling stays green under the probe, the cover
    being a permanent raster by ADR-0042/R2. Saying this here is the point:
    CARD-322 should read it, not discover it.

  **None of the 38 is a defect this card may repair** — the 36 above by the
  model, the 2 by being correct about a tree that is about to change — and
  `EDGE_TOLERANCE_EXEMPTIONS` is still empty.
- **[A gap this card's own helper opened, found and closed]** The set that
  decides whether a placed-edge site has changed medium — `_STREAM_READERS` as
  it was then, `_stream_readers()` as the fix round left it — held
  four names, all from `pdf_vector`. This card gave `pdf_pages` three
  functions that hand back **pixels from a content stream**, so a site reading
  through one of them crosses the medium with `drawing_of` still in its call
  set and the pin passing. Measured, not supposed: MUT-13 plants that on
  `TestBookPdf_DrawingCentredOnRightHandPage::test_the_drawing_sits_25_45_mm_from_the_left_trim_edge`
  and it is invisible to the pin without the fix. The three names are now in
  the set (default-DENY, ADR-0039/R2), with one cell resolving each member to
  a `def` and one asserting the *reason* rather than the membership — MUT-14
  and MUT-15. That set's comment also claimed to be "derived from this
  module's own imports" and never was; corrected — and cycle 1's F-002 is that
  the correction stopped one step short of actually deriving it.
  **Cycle 1 re-fired MUT-13 both ways and upheld it — and then fired a third
  variant that SURVIVED, which is F-001.** The site walk collected names from
  the body of the `EDGE_TOLERANCE_MM`-bearing function only, so the identical
  crossing written **one frame in**, at this module's own page-source helper
  `_interior`, was invisible to the pin. That is not an exotic shape: it is
  the one-line seam this card standardised across five modules and the one
  CARD-322 is instructed to apply to nine more, so applying the house style
  here would have silently retired CARD-330's pin over 30 of the 38 reds. And
  the lesson was already on the board one walk over — `_page_consuming_functions`
  needs a fixed point because `drawing_of` hands its page to `_dark` one frame
  in. **The closure was applied to the population walk and not to the pin;
  `_closed_sites()` is that correction**, following every name a site mentions
  into that callable's body, and on, to a fixed point over this module and
  `tests/helpers/**`. The page-source chain at the 25.45 mm site is three
  frames deep: `_mirrored_pages` → `_interior` → `interior_pages`.
  Measured in both directions, which is what makes the two cells two
  assertions and not one written twice: **MUT-16** (the plant at `_interior`)
  **KILLED** by the closed cell, naming all three readers it reaches
  (`interior_images`, `page_image`, `rendered_page`); **MUT-16b**, the same
  plant against the depth-0 cell, **SURVIVED as declared**; and **MUT-13**,
  the depth-0 plant, **still KILLED**.
  **The set itself is no longer hand-written, which is F-002.** It had a
  control that every *listed* name was a real reader and none that a name
  which *should* be listed was — and omission is the permissive direction
  (ADR-0039/R2, this card's own system contract). Measured at the time:
  `pdf_vector` defines 20 public functions, the set named 4, and the one its
  own stated rationale names — `rendered_page`, the stream reader that returns
  pixels and the one `page_image` itself delegates to — was absent.
  `_stream_readers()` now derives it from the two owners' source: a function
  crosses the medium when it reaches poppler, holds `/Contents` or
  `/Resources`, or takes a decoded stream as a parameter — then, to a fixed
  point, when it calls anything that does. **16 of the 26 public module-level
  readers** (20 public in `pdf_vector` + 6 in `pdf_pages`), the hand-written 7
  included. The other **10** are named in `_MEDIUM_BLIND_READERS`, so the
  classification is a **partition with nothing unclassified** rather than a
  filter whose omissions are invisible; a reader added to either helper that
  the derivation does not recognise reds. *(Cycle 2's F-010: this bullet said
  "16 of the 28 … the other 12", which adds up as arithmetic and therefore
  reads as derived, over a population that is 26 on disk. Re-derived three
  ways — the review's own AST walk, its call-graph variant, and
  `_stream_readers()`/`_owner_functions()` called directly: 26 public, 16
  crossing, 10 blind, union equal to the public set, intersection empty, 0
  unclassified.)*
  **MUT-17** puts the retired hand-written set back and is **KILLED** by the
  completeness cell, whose `unclassified` list names the **nine** readers it
  drops — the derived 16 less the hand-written 7, `rendered_page` among them,
  i.e. the plant reproduces exactly the shipped defect F-002 reported. (Cycle
  2's F-010: this said "six"; fired at the fix round the message names nine,
  `extracted_text`, `marked_type_sizes`, `page_resource_keys`,
  `rendered_page`, `stroke_widths`, `subpath_vertices`, `tones`, `type_sizes`
  and `word_boxes`.) **MUT-14** was re-aimed at the exemption register, now the only
  hand-written half, and is **KILLED**.
  Plants now **24: 22 KILLED, 2 declared SURVIVORS**. Node ids over the seven
  `Touches` paths: **282 -> 310, 0 lost.**
- **[The exemption register is matched on the whole key — cycle 2's F-008]**
  The pin's two denies exempt `_BOUND_ONLY_SITES`, and cycle 1 asked whether
  that exemption was controlled. It was, against the hazard it was asked
  about — the register is existence-controlled, the depth-0 deny exempts
  nobody, and both media-comparison entries really do reach `content_streams`
  and `rendered_page` through `_edge_reading`, which is their job. The hole
  was elsewhere: **the lookup stripped the class.** The register held bare
  function names and all three consulting cells matched through `_bare()`,
  while `_sites()` is keyed class-qualified — and it is keyed that way
  *because the bare name is not unique in this module* (CARD-330 cycle 1's
  F-002 lost a site to exactly such a collision, which is why
  `_COLLIDING_SITES` exists). So any future site in any class whose bare name
  happened to equal a registered one was exempt from the closed deny **and**
  from the raster-oracle requirement, with nothing added to the register and
  no cell reporting it. Omission is the permissive direction (ADR-0039/R2).
  **Measured, matched pair, the planted bare name the only variable, SHA-256
  asserted before plant and after restore:** against the pre-fix lookup at
  `ea248582` the colliding-name plant left the whole pin green — **11 passed
  / 0 failed / 0 skipped**; against the fix it reds two cells (**MUT-20**),
  and the same site under an existing but *unregistered* bare name reds the
  same two (**MUT-21**). Both plants borrow a bare name that `tests/` already
  defines and use a class name pytest does not collect, so the harness adds
  no test-like symbol to a tracked file — `ref_pollution_check.py` reds on
  one, and it is at **0 orphans of 59 symbols** (it reported 3 on the first
  draft of these plants, which is how the convention was settled). The
  register now holds the three class-qualified keys, the three cells match on
  the whole key, and `_bare()` is left only at the walk's floor control, where
  the class genuinely does not matter. Two controls on the fix itself, because
  the old lookup failed silently: `test_the_exemption_lookup_does_not_strip_the_class`
  asserts both directions and resolves the degradation by `ast` — no
  consulting cell may call `_bare` (**MUT-22** KILLED) — and the existence
  cell now asserts the register non-empty, since the empty set satisfied every
  subset assertion it had (**MUT-23** KILLED). The pin is what this card says
  protects 30 of the 38 reds, and the crossing it could not see is exactly the
  seam CARD-322 applies next.
- **[The closure control's depth, taken inline at cycle 2]** F-001's control
  pinned depths 0, 1 and 2 at one site and its docstring claimed only that
  much, so it was honest — but hard-stopped at **2** rounds the walk still
  passed it. The oracle chain at the same site runs one frame further:
  `drawing_of` → `_dark` → `ink_mask` → `INK_LEVEL`, and no body nearer than
  `ink_mask`'s names that threshold, so depth 3 is now asserted too and any
  bounded stop at 2 reds. Measured: the walk settles at **4** rounds at this
  site (121 reachable names, unchanged from round 3).
- **[AC-1's refusal half is now driven, not just implemented — cycle 1's
  F-003]** AC-1 is a disjunction and both halves were written, but only one of
  the three refusal branches had a control that could fail. ADR-0039/R1 is in
  this card's own system contract, so this was the round failing its own
  standard.
  - **`pdf_vector.PDFTOPPM is None`** — the branch the card states as doctrine
    ("a missing engine is a missing reading, never a skip", ADR-0038/R8) — was
    reachable by nothing: `grep -rn PDFTOPPM tests/` found four `skipif`
    markers in other modules and the two new raise sites, and no monkeypatch.
    One `monkeypatch.setattr(pdf_vector, "PDFTOPPM", None)` now drives it
    through **both** doors, `page_image` and `pdf_pages`. The cell's first
    assertion is the matched control and is deliberately a **failure, not a
    skip**, on a host without poppler: this card's reader depends on the
    engine, so a cell that skipped itself away there would be the very thing
    the doctrine forbids. **MUT-18** kills it.
  - **`_derived_dpi`'s disagreeing-DPI arm** — stated in both the docstring and
    the exception text, exercised by nothing; MUT-4 covered only the
    zero-raster-page arm. It is now driven through the reader on a real file
    **and** at the function in all three directions. **This tree's writer
    cannot produce a disagreeing file** — Pillow's PDF writer takes one
    resolution per file and derives every MediaBox from it, so pixel width
    over box width is constant across the pages it writes — which is *why* the
    branch needs an adversarial file rather than a counterfactual
    declaration: one page's MediaBox width is halved **in the written bytes at
    equal byte length**, so the xref offsets stay valid and only page 1's
    physical extent moves (2550 px over 4.25 in beside 2550 px over 8.5 in).
    `scratchpad/card329/probe_disagreeing_dpi.py` is that measurement.
    **MUT-19** kills both cells.
- **[`page_medium_of(page) is RASTER` became `==` — cycle 1's F-007]** The one
  comparison in the new helper whose failure mode was silent and wrong rather
  than loud: it worked only because the function returns that very `str`
  object, and a RASTER page taking the vector branch would be handed to
  `write_vector_pdf`. Every other comparison of the same value in the diff
  already used `==`. Three plants (MUT-2, MUT-15 and MUT-18's neighbour)
  quoted that line by text and were re-aimed with it — which is the whole
  reason the plants are located by text with their occurrence count asserted.
- **[The oracles' cross-check survives]** `pdf_pages.py` now imports
  `pdf_vector` — it is a reader and may. `tests/helpers/page_ink.py` and
  `two_up_ink.py`, the independent pixel oracles, import no stream reader and
  were not touched; `TestEdgeOffset_ThePixelOraclesStillReadPixels` is what
  says so, and it is green. That is G-2's reason, intact.
- **[The architecture validator, re-derived — and what the reading does NOT
  support]** `forge_1`'s `validate.py` (the validator of record,
  `meta/kanban/config.yml:38`) in this worktree: **0 error(s), 88 warning(s)**.
  **De-staled 2026-10-31 at the fix round.** This note used to hedge against
  `config.yml`'s 90, and both halves of the hedge are now resolved rather than
  argued. (1) Main's `config.yml` no longer carries a current figure at all —
  it carries a dated-readings log, whose last line is
  `2026-10-31  forge_1  0 error(s), 88 warning(s)  (at f7ba9c96)`, i.e. **this
  round's own figure at this card's merge base**. The 90 is this worktree's
  stale copy, not main's claim. (2) The `comm` set diff this round declined to
  run beside CARD-316 was completed by cycle 1: **0 errors / 88 warnings on
  both trees, symmetric difference empty in both directions.** So the
  substitute argument below was not a substitute — it was right, and for the
  right reason: **this round cannot have moved a warning either way.**
  - It adds nothing under `meta/architecture`, which is the validator's input.
  - The check-ref search is a TEXT search over the repo, so a scratchpad
    mention can silence a dead ref. `scratchpad/card329/ref_pollution_check.py`
    derives every test-like symbol the **eleven** instruments mention —
    **59**, re-derived at the merge gate and agreeing with the same figure at
    the ref-pollution note above (this site read **50** until the gate: one
    copy of the figure was refreshed at fix round 2 and this one was not,
    which is cycle 3's F-011 and the same shape as cycle 1's F-006) — and
    resolves each to a `def`/`class` in `tests/`: **0 orphans**. A clean
    reading here is worthless without a control, because a matcher that finds
    nothing *because it was built wrong* prints the same 0: the gate therefore
    ran a second matcher of a different shape (tokenise every identifier, then
    filter by prefix in Python, instead of one `\b`-anchored alternation). It
    agrees on the identical genuine set of 59 with 0 orphans, differing only
    by the two bare prefix fragments `PropertyTest` and `PropertyTest_` that
    the card's `{4,}` tail excludes; and with two synthetic orphans injected
    into the scanned text it reported **both**, so the 0 is a measurement and
    not a silence. Every one is
    already resolved by a real definition, so the scratchpad changes no ref's
    resolution. (This is the failure recorded in the orchestrator's notes: a
    commit of measurement text reddened a merge gate by making dead refs
    resolve from `scratchpad/`. It is why nothing in this round is a `.txt`
    census or a validator dump — the instruments are `.py` and the numbers
    live in this card.)
- **[The impact run, on `main`'s rules with no probe]** All six runnable
  `Touches` paths in one node-scoped call with `-o addopts=` and `-rs`:
  **347 passed, 0 failed, 0 skipped**, re-measured at the merge gate at
  `e690d15f` with `-rfs` as ONE flag (339 + the 8 cells the two fix rounds add,
  so the figure derives rather than being retyped). The figure this note first
  carried, **346**, was honestly stamped at `b609e675` and went stale by
  exactly the one cell fix round 2 added — that is cycle 3's F-011, re-derived
  at the gate rather than copied from the review. Zero skips is the assertion,
  not an
  observation — a skip keeps the collected count and removes the assertion, so
  a green-with-skips reading would say nothing. (A full suite shows 27 skips,
  26 DB-gated and 1 `setrlimit`; an impact run of these files touches neither
  gate, and `-rs` printed no reason because there was none to print.) The full
  suite was **not** run: that is the merge gate's job and it must not run
  beside another card's pytest, which CARD-316's worktree had live throughout
  this round.
- **[What was deliberately NOT done]** The 16 residual reds were not forced
  green. Each needs its claim re-expressed against the content stream
  (ADR-0042/R6) or its expectation re-composed in the page's own medium, and
  both are the conversion's work: ADR-0042 assigns the frame-centre oracle to
  CARD-322 and the per-site disposition of the pixel-reading sites to CARD-312.
  Widening a tolerance would have closed every one of them and is exactly what
  CARD-330 was cut to prevent. `tests/helpers/pdf_vector.py` carries a now-stale
  sentence — "`tests/helpers/pdf_pages.py` is deliberately left alone" — and is
  outside `Touches`; raised, not edited.
