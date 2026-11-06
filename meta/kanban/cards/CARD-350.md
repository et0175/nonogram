# CARD-350: Poppler rasterises a 282.1 mm trim 1.11 px taller than the dpi says, and two page-size cells have been hiding behind a first-failure attribution

**Status:** ready
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1c (0.5d)
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** Raised as F-8 by CARD-336's implementation round, 2026-11-04, and carded on the owner's instruction. The round found it by closing the placed-edge cells that were failing FIRST in the same tests — so these two cells existed all along and no instrument could see them, because pytest stops a test at its first failing assertion. That is the generalisable half and it is why this is a card rather than a line in CARD-336.
**Idea:** —
**Wave:** —
**Created wave:** 74
**Deferred waves:** 0
**Depends on:** CARD-336
**Touches:** tests/property/test_book_pdf_geometry.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## The two cells, and why nobody had seen them

Both live in `tests/property/test_book_pdf_geometry.py` and both are **pre-existing on `main`** —
neither is created by CARD-336. They were masked because the placed-edge assertion **above**
each of them failed first, and a pytest test stops at its first failing assertion.

**Cell 1 — the trim height.** `assert abs(page.size[1] - trim_height_px) <= 0.5` (the cell in
the test that measures a portrait page's fixed top edge). Under the five-kind probe it reds at
**1.110 px**. The arithmetic, re-derived independently at the decompose station and reproducing
the round's figures exactly:

| quantity | value |
|---|---|
| 300 dpi in px/mm | 11.811024 |
| 282.1 mm × that | **3331.890 px** |
| what poppler actually rasterises | **3333 px** |
| delta against a 0.5 px bound | **1.110 px** |

**Cell 2 — page sizes are not uniform.** `assert len({page.size for page in pages}) == 1`
measures **2** distinct sizes.

**Re-derive both.** They are dated readings taken under
`scratchpad/card338/probe_five_kinds.py` (CARD-338's, driven by `census_five_kinds.py`) over
CARD-336's branch, and a different number is the finding.

## What this is probably about, stated as a hypothesis and not a premise

A rasteriser that is handed a page in points and asked for 300 dpi has to land on an integer
pixel count, and 282.1 mm is not a whole number of pixels at that density. **1.110 px is
close to — but not equal to — the 1.0 px a naive ceiling would give** (`ceil(3331.890)` is
3332, not 3333), so "poppler rounds up" does not explain it either. **Do not implement against
this paragraph.** Measure what poppler is actually doing with the page box before deciding
whether the bound, the expectation or the generator is wrong.

Three outcomes are all legitimate and the card does not prejudge between them:

1. The **bound** is wrong — 0.5 px is tighter than any rasteriser can promise across a
   non-integral trim, in which case the honest bound is derived from the density and stated.
2. The **expectation** is wrong — the test should compare against what the page box asks for
   rather than against a millimetre figure re-multiplied.
3. The **generator** is wrong — it emits a page box that does not correspond to the trim.

## Why the masking matters more than either cell

**A first-failure attribution reads exactly like a complete one.** CARD-336's card carried four
figures naming four failing cells; all four were real, and **two of them were the second
assertion in their test**, invisible until the first closed. Nothing in the suite or the census
distinguishes "this test fails for one reason" from "this test fails for the first of several".

That is worth a measurement of its own here, because it is cheap once you are in the file:
**how many other tests in this module stop at a first failure that masks a later assertion?**
Derive it — run each failing test with its first failing assertion neutralised and see what
appears — and report the count. If it is two, say so. If it is twelve, this card has found
something larger than its own two cells.

## [Addendum 2026-11-06, from CARD-322's re-cut] — a third cell with the same mechanism, and one cell this card must NOT absorb

Measured by the CARD-322 re-cut (mine, a private clone of main at `bb8d1121`, five-kind probe, `tests/property/test_book_pdf_geometry.py` run alone; the module finishes under the default 300 s hang guard with all four of its tests red and none killed). The module has four reds under the probe, and the same four at the on-disk end state with the default writer set assembled.

* **Cells 1 and 2 are the two this card already names.** `..._PortraitWithFixedTopEdgeForEveryExtent_pdf_pages` reds at `0.9448818897637921 <= 0.5` (the trim-height assertion), and `..._MirroredMarginsCentreDrawingForEveryParity_pdf_pages` reds at `assert 2 == 1` (the page-size count). Both reproduce.
* **Cell 3 (new to this card): `test_PropertyTest_BookLayout_DrawingFitsUsableAreaUnderStandardCell_pdf_pages`** reds at an assertion of the SAME shape as cell 1, `assert abs(page.size[1] - trim_height_px) <= 0.5`, printing `Sheet(137.9 x 282.1 ...)` with page size `(1629, 3333)`: the same 282.1 mm trim at the same 3333 px. CARD-336's own table lists it as "a page-SIZE claim: poppler rasterises a 282.1 mm trim to 3333 px where 11.811 px/mm says 3331.890". It is not named by this card's text. **Treat it as a third cell of cell 1's mechanism**: step 1 (measure what poppler does with the page box) answers it for free, and step 2 should fix all of the cells the measurement indicts, saying which of the three outcomes (bound, expectation, generator) applies to each. Its AC-1 reads "both cells pass"; read it as "all the cells this card names pass".
* **Cell 4 is NOT this card's: `test_PropertyTest_BookPdf_PortraitWithFixedTopEdgeForEveryExtent_two_up_pages`** reds at `AssertionError: (6, 25.7387...)`: it is CARD-336's DECLARED `1 x HALF_PIXEL_MM` site (its F-4, measured 5.46x in the vector medium and 0.46x by centre reading). The measurement is in that module's own comment above the assertion and in CARD-336's F-4. It cannot be closed by any reading in both media, and the only lever is the site's own multiple, which this card's G-2 (and CARD-322's G-3b) forbids moving. **Do not touch it.** It is a decision for the owner (move that one multiple from 1 to 2, which admits both readings per the module's comment, or declare the red) and it blocks CARD-322's merge until decided. If your measurement for cells 1 to 3 changes that picture, report it.

## What to implement

1. **Measure what poppler does with the page box**, in both media, before touching anything.
   Report the page box as emitted, the dpi, and the pixel count, and say which of the three
   outcomes above the measurement supports.
2. **Fix the cell the measurement indicts** — bound, expectation or generator — and say which
   you chose and why the other two are wrong.
3. **Do the same for cell 2.** Two distinct page sizes may be the same cause or a second one;
   name which, with evidence per size.
4. **Count the masked assertions in this module** (above), and card anything you find rather
   than absorbing it.

## Acceptance criteria

- **AC-1** *Given* the five-kind probe, *then* both cells pass, and the card states the measured
  page box, density and pixel count that justify the fix — not a recomputed millimetre figure.
  (test: `tests/property/test_book_pdf_geometry.py`'s two cells, named by the implementation)
- **AC-2** *Given* the fix, *then* a plant that changes the emitted page box by one pixel
  **reds** — the cell must still be able to fail for the claim as stated (ADR-0039/R1). A bound
  widened until nothing can fail is this card's failure mode.
  (test: named by the implementation; state it)
- **AC-3** *Given* this module, *then* the number of tests whose first failing assertion masks a
  later one is **derived and reported**, and anything beyond these two cells is carded with an
  owner rather than fixed here.
  (check: review-lens)
- **AC-4** *Given* the bound, *then* if it is widened at all, the new value is **derived from
  the density** and carries the measurement, not chosen to make the cell pass.
  (test: named by the implementation; state it)

## Guardrails

- **G-1** — No `src/` change unless the measurement indicts the generator. If it does, say so
  explicitly and expect the reviewer to check that attribution hardest — a test-side defect
  reframed as a generator defect is how scope escapes.
- **G-2** — **Do not widen a bound to make a cell pass.** AC-2 and AC-4 are the guards. ADR-0042
  and CARD-336 both turn on bounds that were never widened; `EDGE_TOLERANCE_MM`,
  `EDGE_TOLERANCE_PX` and `HALF_PIXEL_MM` are not yours to move.
- **G-3** — Do not re-express a placed-edge reading. CARD-336 owns the frame-centre oracle and
  these two cells are **not** placed-edge claims; if you find yourself touching
  `frame_centre_of`, the card has been misdiagnosed.
- **G-4** — No new runtime dependency (ADR-0006/R1).
- **G-5** — Take no timing measurements and report no durations; other work shares the machine.
  Note that this module carries a node id that exceeds the project's **120 s per-test hang
  guard** under the probe (CARD-336's F-9) — if you meet it, that is a known condition and not
  yours.
- **G-6** — A full suite needs the board's lock (`meta/kanban/.full-suite.lock`, structured,
  identity is the **worktree**, no pid). Never set `NONOGRAM_IGNORE_FULL_SUITE_LOCK`, and never
  redirect `NONOGRAM_FULL_SUITE_LOCK` — the guard fires in `pytest_configure` for **any**
  selection.

## System contract

- ADR-0039/R1 — a claim needs a control that can fail (check: review-lens)
- ADR-0039/R4 — a figure recomputed and refuted is retracted everywhere it was written
  (check: review-lens)
- ADR-0042/R1 — interior pages are operators (check: review-lens)
