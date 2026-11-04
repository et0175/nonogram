# CARD-342: `_weights` demands two run widths and antialiasing gives it three — a stroke-weight reading, not an edge position

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
**Source:** Split out of CARD-336 at the decompose station, 2026-11-04, on the owner's re-cut instruction, after CARD-336's own round measured its population and found these cells are a different mechanism from the one that card is named for. CARD-336 is a boundary-reading card; these three cells make a claim about stroke *weight*, which no frame-centre oracle touches.
**Idea:** —
**Wave:** —
**Created wave:** 74
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/test_book_puzzle_frame.py, tests/helpers/page_ink.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## The defect, measured before it was written down

`tests/test_book_puzzle_frame.py` carries **3 reds** whose message is

```
a row through the grid shows weights [2, 4, 6]
```

The helper `_weights` scans a row through the grid and requires exactly **two** distinct run
widths — the light rule and the heavy rule. Under the probe it finds **three**: `[2, 4, 6]`.

**Measured by CARD-336's round, 2026-11-04**, under `scratchpad/card338/census_five_kinds.py`
with `--causes`, `unaccounted=0` and `0 skipped`: these 3 cells are red under **both** the
`PageKind.PUZZLE`-only filter and the five-kind filter — the count does not move, so this is
not a conversion artefact of one page kind.

**Re-derive that before implementing.** The count is a dated reading and a different number is
the finding.

## Why it is not CARD-336's, stated because the two look alike

CARD-336 re-expresses cells that compare an **ink extent** against a **coordinate**. These
three compare a **set of run widths** against an expected **cardinality**. A frame-centre
oracle changes where the edge is read; it does not change how many distinct widths a row
contains. CARD-336's round classified them as its class C and routed them here rather than
absorbing them — which is why this card exists instead of a silent widening.

## What to implement

1. **Establish why there are three widths, not two.** The obvious hypothesis is antialiasing
   producing an intermediate run at a rule boundary — `[2, 4, 6]` is consistent with a 2 px
   light rule, a 6 px heavy rule and a 4 px blend. **Do not implement against that hypothesis
   until it is measured.** Dump the actual run widths and their positions.
2. **Decide what the test is entitled to claim**, and say which you chose: that a row shows
   exactly two *nominal* weights (so the reading must collapse blends), or that it shows two
   weights *within a tolerance* (so the tolerance is derived, not invented). A tolerance
   chosen to make three look like two is the defect, not the fix.
3. **If the reading must change, change the reading, not the bound.** `page_ink.py` is in
   `Touches` for that reason and for no other.

## Acceptance criteria

- **AC-1** *Given* the probe, *then* the three cells pass, and the count of placed reds in
  `tests/test_book_puzzle_frame.py` attributable to `_weights` is **derived from the message
  the gate prints** rather than listed, with the number and the filter stated.
  (test: named by the implementation; state it)
- **AC-2** *Given* the fix, *then* planting an extra genuine run width into a row **reds** —
  the reading must still be able to fail for the claim as stated (ADR-0039/R1). A fix that
  cannot distinguish a real third weight from a blend has removed the control.
  (test: named by the implementation; state it)
- **AC-3** *Given* the measurement, *then* the card states what produced the third width, with
  evidence, rather than asserting antialiasing. (evidence: the card's own measurement)

## Guardrails

- **G-1** — No `src/` change. These are test-side readings of a page the generator draws
  correctly; if the measurement shows otherwise, that is a finding and a new card, not a
  silent `src/` edit.
- **G-2** — Do not widen a tolerance to absorb the third width without a measured residue and
  a stated reason. An exemption added to make this card green is the defect one level up.
- **G-3** — No new runtime dependency (ADR-0006/R1): stdlib + Pillow + NumPy is closed.
- **G-4** — Take no timing measurements and report no durations; other work shares the machine.

## System contract

- ADR-0039/R1 — a claim needs a control that can fail: caught WITH the mechanism, missed
  WITHOUT it (check: review-lens)
- ADR-0039/R2 — a guard's set is derived from an authority the runtime can enumerate, not
  hand-written (check: review-lens)
- ADR-0039/R4 — a figure recomputed and refuted is retracted everywhere it was written
  (check: review-lens)
