# CARD-329: The one-image reader learns the content stream — AC-3's real content, separated from the three causes that were not readers

**Status:** in_progress
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
**Review score:** —
**Started:** 2026-10-31T06:47:15+00:00
**Closed:** —
**Actual:** —
**Merge commit:** —
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
