# CARD-344: `_EDGE_OVERHANG = 3` is a hard-coded half-rule already medium-dependent inside the existing ink reader

**Status:** done
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c (0.25d)
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** Raised as F-6 by CARD-336's round, 2026-11-04, and routed here at the decompose station on the owner's re-cut instruction. The round found it while reading the constant CARD-336 forbids the NEW oracle from using, and noticed the EXISTING reader already uses it. Not named anywhere in CARD-336, so it was carded rather than absorbed.
**Idea:** —
**Wave:** —
**Created wave:** 74
**Deferred waves:** 0
**Depends on:** CARD-336
**Touches:** tests/helpers/page_ink.py
**Review score:** n/a — closed on the owner's 2026-11-09 tech-debt triage; no review of its own.
**Started:** 2026-11-09
**Closed:** 2026-11-09
**Actual:** under an hour
**Merge commit:** —
**Blocked by:** —

## The defect in one line

`tests/helpers/page_ink.py` carries

```python
_EDGE_OVERHANG = 3   # the heaviest rule the book strokes is 6 px, so 3 px is the overhang, exactly
```

and it is load-bearing in `_drawing_rows`.

> **[PREMISE CORRECTED 2026-11-04 by CARD-336's round, which built the oracle and measured the
> page instead of computing from the declaration. ADR-0039/R4 retraction — read this before
> the paragraph below it.]**
>
> **This card was cut saying the half rule is 2.71 px** — 1.3 pt at 300 DPI is 5.4167 px, so
> half is 2.71 — **and that is refuted.** CARD-336 measured both media: **poppler inks the
> declared 1.3 pt as SIX pixel lines, exactly as Pillow does** (`left_rule_px ==
> top_rule_px == 6`, confirmed structurally — for one boundary `c`, Pillow inks `c-2..c+3`
> and poppler `c-3..c+2`). So the width **read off the page** is 6 and the half rule is
> **2.5 px**, not 2.71.
>
> **And the constant is wrong in a different way than this card claimed.** `_EDGE_OVERHANG = 3`
> is exact in **neither** medium *as a half rule*: 3.000 px is the **ink-to-coordinate offset
> in vector** and **0 px in raster**. The original framing — "exact only in one medium" — is
> therefore also wrong; it is exact in neither, and it happens to equal a real vector offset,
> which is why it has survived.
>
> **What this does to the card: the defect is still real and the reason is better.** The
> constant is a hard-coded pixel figure standing in for something the page can be asked. What
> changed is that **CARD-336's `frame_centre_of` holds no half-rule constant at all** — it
> reports the run's own centre — so item 2's "replace the constant with the derivation
> CARD-336 establishes" now has a concrete mechanism to copy rather than a figure to
> recompute. **Do not carry 2.71, 5.42 or 3 into an assertion. Re-derive by recounting the
> run on the page, which is what that card's
> `test_the_rule_width_is_the_pages_and_not_the_declared_figure` does.**

## Why this is small but not a nit

CARD-336's round measured a neighbouring instance of the same arithmetic and it mattered
there: `tests/test_book_puzzle_frame.py`'s residual is **2.504 px against a 1.5 px bound**,
and a hard-coded 3 would have missed that cell. The same off-by-0.29-px reasoning is sitting
in the existing reader with no test naming it.

**It is P3 and depends on CARD-336** deliberately: CARD-336 establishes how a rule width is
read off the page. This card applies that to the constant the old reader kept. Doing it first
would mean inventing the mechanism twice.

## What to implement

1. **Re-derive the heavy rule's rasterised width by recounting the run on the page**, in
   **both** media, rather than trusting 6, 5.42, 2.71, 2.5 or 3 — every one of those is a
   carried figure and two of them have already been refuted once. CARD-336's
   `test_the_rule_width_is_the_pages_and_not_the_declared_figure` recounts it independently at
   a mid-cell row and asserts it is **not** the declared figure; copy that technique.
2. **Replace the constant with the derivation CARD-336 establishes**, or — if the reader
   genuinely only ever sees raster pages — **say so and pin that**, so the next reader is not
   left guessing which medium the "exactly" refers to. Either outcome is acceptable; leaving
   it undocumented is not.
3. **Check whether the constant has siblings.** Derive every hard-coded pixel constant in
   `page_ink.py` by `ast` and report them, rather than fixing the one this card names and
   leaving its twins.

## Acceptance criteria

- **AC-1** *Given* `tests/helpers/page_ink.py`, *then* the overhang is either derived from the
  page or explicitly pinned to one medium with the pin asserted, and the comment no longer
  claims an exactness that holds in only one medium.
  (test: named by the implementation; state it)
- **AC-2** *Given* the change, *then* the raster oracles still report the first inked line
  **byte for byte** in their result — ADR-0042/R6 exempts the independent oracles by name and
  CLAUDE.md requires the cross-check they provide.
  (test: `TestEdgeOffset_ThePixelOraclesStillReadPixels`, unmodified)
- **AC-3** *Given* a plant that changes the overhang by one pixel, *then* something **reds** —
  the constant must be load-bearing in a way a test can see (ADR-0039/R1). If nothing reds,
  that is the finding: the constant is dead and should be deleted rather than derived.
  (test: named by the implementation; state it)
- **AC-4** *Given* `page_ink.py`, *then* every hard-coded pixel constant in it is enumerated
  by derivation and reported, each either closed here or named with an owner.
  (check: review-lens)

## Guardrails

- **G-1** — No `src/` change. This is a test-helper constant.
- **G-2** — Do not convert the raster oracles. AC-2 is the guard: they must still read pixels.
- **G-3** — No new runtime dependency (ADR-0006/R1).
- **G-4** — Take no timing measurements and report no durations; other work shares the machine.

## System contract

- ADR-0039/R1 — a claim needs a control that can fail (check: review-lens)
- ADR-0039/R2 — a guard's set is derived from an authority the runtime can enumerate
  (check: review-lens)
- ADR-0042/R6 — the independent pixel oracles are exempt from the conversion by name
  (check: `TestEdgeOffset_ThePixelOraclesStillReadPixels`)

## Triage 2026-11-09

Still open, small. The 3 px overhang now only matters on poppler renders of vector pages; the frame reasoning in its comment no longer applies (`BOOK_PUZZLE_FRAME = False`). Fold in: delete the now-dead `framed` / `frame_centre_of` / `FrameCentre` / `_outer_rule_is_a_frames` helpers from tests/helpers/page_ink.py (CARD-351 and CARD-353 retired).

## Closed 2026-11-09 — owner's tech-debt triage

The dead half is removed: `FrameCentre`, `frame_centre_of` and `_refuse_unless_a_frames_rule` had no caller left in `tests/` or `src/` and are deleted from `tests/helpers/page_ink.py`. `_EDGE_OVERHANG` and `drawing_of`'s frame detection stay, because `tests/test_book_puzzle_frame.py` and `tests/property/test_book_pdf_geometry.py` still measure framed pages (the frame remains a `PageSpec` option, off in the book). Re-deriving the constant was not done: it buys nothing with the book's frame off.
