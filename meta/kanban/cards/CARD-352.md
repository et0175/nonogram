# CARD-352: The placed-edge partition misses three literal-bound sites and falls through to "no extent" where ADR-0039/R2 says it must fail

**Status:** skipped
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1c (0.5d)
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** Findings 2 and 3 of CARD-336's review cycle 1, 2026-11-04, carded together because they are two holes in one derivation — `_partition`'s key and `_partition`'s default. The review UPHELD the round's refusal to widen the filter (it measured 25 candidate sites and most need a classifier the walk does not have), so this card is not "widen it"; it is "make the two holes visible and bounded".
**Idea:** —
**Wave:** —
**Created wave:** 74
**Deferred waves:** 0
**Depends on:** CARD-336
**Touches:** tests/test_book_puzzle_frame.py
**Review score:** n/a — **RETIRED** on the owner's 2026-11-09 board triage. No work is owed here.
**Started:** —
**Closed:** 2026-11-09
**Actual:** none — retired (see the closing note).
**Merge commit:** —
**Blocked by:** —

## Hole 1 — the bound key misses THREE sites, and the card says one

CARD-336's `_partition` keys the placed-edge population on a site's **declared bound name**
(`HALF_PIXEL_MM` / `EDGE_TOLERANCE_PX`). A site bound by a **literal** is invisible to it. The
round found one such site (its F-10) and re-expressed it. **Its reviewer re-ran the walk's own
classifier ignoring the bound key and found two more that are this card's subject and carry no
declaration:**

- **`TestPuzzleFrame_TwoUpGeometryIsUnmovedByTheFrame::test_the_upper_slot_still_starts_on_the_bands_own_foot`** —
  `assert abs(upper.top / PX_PER_MM - (TOP_MM + BAND_MM)) <= 0.5`. An ink extent differenced
  against a millimetre coordinate, **four lines above the cell CARD-336 re-expressed, in the
  same class.** Green only because 0.5 mm is about 11.8 half-pixels, which is generous; the
  vector ink offset is **0.212 mm**.
- **`drawing.grid_right <= usable_right + 1` and `drawing.grid_bottom <= usable_bottom + 1`** —
  argued away in a **prose comment** ("genuinely about ink"), not entered in
  `PLACED_EDGE_ON_THE_INK_BY_DECLARATION`, and invisible to the walk.

**The round's stated reason for not widening is weaker than it looks**, and the reviewer
measured why: the walk's own pairing logic already sorts the array-index reads into
`cancelling`/`no_extent` **without** a new classifier. So "needs a classifier for those shapes
first" is true of most of the 25 and not of these three.

**The honest statement is "the bound key misses three sites, one re-expressed and two left on
the ink undeclared", not "one exists".** That is what this card fixes.

**Re-derive all of it.** The 25, the three, and the 0.212 mm are dated readings.

## Hole 2 — the classifier's default is the wrong way round

`_partition` returns `UNCLASSIFIED` **only** when an ink-named attribute has an *unresolvable*
base. An ink-named attribute whose base **resolves** but whose reader is not in `_INK_READERS`
or `_BOUNDARY_READERS` falls through to **`no_extent`** — "it reads no ink extent at all".

The reviewer instrumented the walk and found **four such live reads across two sites**:
`frame.left` and `frame.top` in `test_the_frame_is_the_drawings_own_box` and
`test_PropertyTest_PuzzleFrame_IsTheDrawingsBoxOnEveryTrimAndParity`.

**Both are benign today** — that `frame` is `compute_layout`'s `layout.frame`, a coordinate, so
`no_extent` is the right answer. **But the walk reaches it by accident rather than by
analysis:** it cannot tell a coordinate source from an unrecognised ink reader. A future
`drawing = some_new_ink_helper(page)` lands in `no_extent` **silently**, and
**ADR-0039/R2 makes failure the correct default for a shape a guard cannot analyse.**

This is the same false-green direction as CARD-351's `framed: bool = False` and
`_BOARD_STATUSES`' unseen-spelling deny — a default that gives every caller a plausible answer.

## What to implement

1. **Invert the default.** An ink-named attribute whose base resolves to neither reader is
   **`UNCLASSIFIED`** unless the base resolves to a **declared coordinate source**. Add a small
   `_COORDINATE_SOURCES` set carrying `compute_layout` / `layout.frame`. The reviewer's estimate
   is one `elif` and a frozenset — **verify that rather than trusting it**, and if it is larger,
   say so with the measurement.
2. **Handle the three literal-bound sites**, choosing one and saying which: enter them in
   `PLACED_EDGE_ON_THE_INK_BY_DECLARATION` keyed on `(path, qualified name, literal bound)` with
   the measured residual, **or** state in `_partition`'s docstring that the bound key excludes
   literal-bound sites and **name all three**. The first is better; the second is honest.
   **Silence is neither.**
3. **Do not widen the filter to all 25.** The reviewer upheld the round's refusal: most of the
   25 are array indices and AC-1's deliberate `> tolerance` controls, and sweeping them in is a
   blanket exemption rather than a partition. If your measurement disagrees, that is a finding
   to report, not a licence.
4. **Do not widen any bound.** The 0.5 mm on the two-up site is generous; tightening it is a
   separate decision with a corpus behind it, and CARD-330 owns the related `1 → 2` multiple.

## Acceptance criteria

- **AC-1** *Given* `_partition`, *then* an ink-named attribute whose base resolves to an
  unrecognised reader is **`UNCLASSIFIED`** and that is a **FAILURE**, not a skip — demonstrated
  by planting a synthetic `drawing = some_new_ink_helper(page)` site and showing the walk reds.
  (test: named by the implementation; state it)
- **AC-2** *Given* the four benign `frame.left` / `frame.top` reads, *then* they still classify
  as `no_extent` **by analysis** — because `compute_layout` is a declared coordinate source —
  and removing it from `_COORDINATE_SOURCES` makes them **`UNCLASSIFIED`**. Both states shown.
  (test: named by the implementation; state it)
- **AC-3** *Given* the three literal-bound sites, *then* each is either declared with a measured
  residual or named in `_partition`'s docstring, and the set of literal-bound placed-edge sites
  is **derived** rather than listed (ADR-0039/R2). State the count; three is a dated reading.
  (test: named by the implementation; state it)
- **AC-4** *Given* CARD-336's totality guard, *then* `TestFrameCentre_EveryPlacedEdgeSiteIsClassified`
  is still green and still reports **0 unclassified** on the real tree, and its site count is
  stated. A change that makes the guard pass by shrinking its population is the defect.
  (test: `TestFrameCentre_EveryPlacedEdgeSiteIsClassified`)
- **AC-5** *Given* `PLACED_EDGE_ON_THE_INK_BY_DECLARATION`, *then* every entry still fails in
  the four directions CARD-336's review measured — a dead key, a key naming a `boundary` site, a
  reason naming no card, and an emptied registry. Adding entries must not weaken that control.
  (test: the declaration's own cell; name it)

## Guardrails

- **G-1** — No `src/` change.
- **G-2** — **Do not widen a bound to make anything green.** `EDGE_TOLERANCE_MM`,
  `EDGE_TOLERANCE_PX` and `HALF_PIXEL_MM` are not yours to move, and neither is the 0.5 mm.
- **G-3** — **A declaration is not an exemption.** Every entry added carries a reason and a
  measured residue and is held by the registry's own control. An entry added to make the walk
  total without measuring the site is the defect this card exists to remove, one level up.
- **G-4** — Do not re-expand CARD-336's oracle or its field set. It reads `left`, `top` and
  `grid_bottom` deliberately (see CARD-351 for why `framed` is not among them).
- **G-5** — No new runtime dependency (ADR-0006/R1).
- **G-6** — Take no timing measurements and report no durations.
- **G-7** — A full suite needs the board's lock (`meta/kanban/.full-suite.lock`, structured,
  identity is the **worktree**, no pid). Never set `NONOGRAM_IGNORE_FULL_SUITE_LOCK`, and never
  redirect `NONOGRAM_FULL_SUITE_LOCK` — the guard fires in `pytest_configure` for **any**
  selection.

## System contract

- ADR-0039/R1 — a claim needs a control that can fail (check: review-lens)
- ADR-0039/R2 — a guard's set is derived from an authority the runtime can enumerate; where none
  exists it defaults to **deny** (check: `TestFrameCentre_EveryPlacedEdgeSiteIsClassified`)
- ADR-0039/R3 — a declaration carries a reason and a measured residue (check: review-lens)

## RETIRED 2026-11-09 — board triage

The placed-edge partition it would make total was deleted in the 2026-11-09 curation (6731e0ec), and its subject, the clue frame, no longer ships.
