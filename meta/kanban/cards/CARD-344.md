# CARD-344: `_EDGE_OVERHANG = 3` is a hard-coded half-rule already medium-dependent inside the existing ink reader

**Status:** ready
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
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## The defect in one line

`tests/helpers/page_ink.py` carries

```python
_EDGE_OVERHANG = 3   # the heaviest rule the book strokes is 6 px, so 3 px is the overhang, exactly
```

and it is load-bearing in `_drawing_rows`. The comment's arithmetic is right for a **raster**
page and wrong for a **vector** one: the heavy rule is 1.3 pt, which at 300 DPI rasterises to
**5.42 px**, so the half is **2.71 px**, not 3.

So the existing reader carries exactly the medium-dependent constant that CARD-336's item 1
forbids the *new* reader from using. **The word "exactly" in that comment is the tell**: it is
exact only in one medium, and nothing in the file says which.

## Why this is small but not a nit

CARD-336's round measured a neighbouring instance of the same arithmetic and it mattered
there: `tests/test_book_puzzle_frame.py`'s residual is **2.504 px against a 1.5 px bound**,
and a hard-coded 3 would have missed that cell. The same off-by-0.29-px reasoning is sitting
in the existing reader with no test naming it.

**It is P3 and depends on CARD-336** deliberately: CARD-336 establishes how a rule width is
read off the page. This card applies that to the constant the old reader kept. Doing it first
would mean inventing the mechanism twice.

## What to implement

1. **Re-derive the heavy rule's rasterised width** rather than trusting either 6 or 5.42.
   State the figure and how it was measured. Both numbers in this card are carried figures.
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
