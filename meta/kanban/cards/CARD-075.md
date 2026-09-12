# CARD-075: Image-mode nudge picks its cells from the solver's undecided mask, nearest the ink boundary first

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/075-mask-driven-nudge
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-9 (FR-013 amendment, split from CARD-074 by decompose)
**Idea:** —
**Wave:** 1
**Depends on:** CARD-073
**Touches:** src/nonogram/sourcing/image.py (nudge_cells, nudge — signature gains the mask), src/nonogram/orchestrator.py (attempt_nudged_candidate passes the ORIGINAL conversion's mask — the one call site), tests/test_nudge.py, tests/property/test_nudge_mask.py (new)
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why

Today's nudge ranks cells by a 2x2 "switching block" heuristic
(`sourcing/image.py` `nudge_cells`) — a guess at where the ambiguity is
(CARD-016's recorded risk). CARD-073 makes the ambiguity locatable: the
solver reports the cells line logic left undecided and where the two
witnesses disagree. FR-013's 2026-09-12 amendment (mechanism half only)
has the nudge choose from that mask, nearest the ink boundary first. The
policy half is untouched: POL-002 bounded and automatic, POL-003 reports at
the cap, cap of 5 (ADR-0002), and the cumulative property "attempt n flips
the n best cells of the ORIGINAL conversion".

Split from CARD-074 by decompose: different module (`sourcing/image.py` vs
the orchestrator's recovery loop), different policy (POL-002 vs POL-006),
different test file, and a separate owner question (below). The handoff
lists it under Increment 9; it shares no code with the repair step beyond
the one call site in `orchestrator.py`.

**Sequencing.** After CARD-073 (needs the mask on the aggregate). Parallel
with CARD-074 is possible; the two share `orchestrator.py` only at the
nudge call site (conflict-graph matter). CARD-079's AC-127 nudge counts
are taken after this card lands, so this card precedes CARD-079.

**Owner question (FR-013 _meta.gaps, recorded not invented):** what does
attempt n do when the mask holds fewer than n cells? EC-014 reads it as
"flip all min(n, |mask|) of them" — implement that reading and record it
in the module docstring; if the owner wants a secondary ranking instead,
that is a follow-up, not this card.

## What to implement

1. `sourcing.image.nudge_cells(grid, count, mask)` ranks candidate cells
   **from the mask only** (undecided mask, or the witness-disagreement set
   when present — both grid-shaped `list[list[bool]]` from CARD-073), by
   Chebyshev distance to the nearest differently-valued neighbour (ink
   boundary) ascending, then (row, column) for determinism. Returns the
   first `min(count, |mask|)` cells. The 2x2 switching-block ranking
   (`_switch_counts`, `_boundary_counts` as primary key) is retired or
   demoted to a tiebreak inside the mask — say which in the docstring.
2. `sourcing.image.nudge(grid, attempt_number, mask)` keeps flipping the
   best n cells of the ORIGINAL conversion (nesting preserved), now drawn
   from the mask.
3. `orchestrator.attempt_nudged_candidate` passes the mask recorded for
   the ORIGINAL conversion (stored by CARD-073 on the aggregate at the
   first `judge_candidate`) — not the previous nudge round's mask. Cap,
   counter, `run_bounded` exhaustion branch and POL-003 wording unchanged.
4. Re-pin `tests/test_nudge.py` to the mask-driven choice: the scripted
   sources gain a mask; real-image pins are re-taken honestly (CARD-070's
   convention: the docstring states the count and where it came from).
   The mechanism-agnostic tests (cap, failure message, CLI reporting —
   AC-034..AC-036, FR-014) must pass unchanged in assertion.
5. Rewrite the `nudge_cells` docstring and `docs/GENERATION_ALGORITHM.md`
   §8.3's one paragraph on cell choice (a one-row docs touch; do not
   restructure the doc).

## Acceptance criteria

- **AC-115** — given an uploaded silhouette whose conversion at 20x20
  reports MANY with an undecided/disagreement mask of 14 cells, when nudge
  attempt 3 is applied, then all 3 flipped cells are members of that
  14-cell mask.
  *test:* `TestNudge_FlipsOnlyCellsInsideUndecidedMask`
- **AC-116** — given an undecided mask containing one cell adjacent to the
  ink boundary (Chebyshev distance 0 from a differently-valued neighbour)
  and one cell 3 cells away from any ink boundary, when attempt 1 is
  applied, then the cell adjacent to the ink boundary is the one flipped.
  *test:* `TestNudge_PrefersCellsNearestInkBoundary`
- **AC-117** — given a conversion whose mask-driven attempts 1, 2 and 3
  flipped sets S1, S2, S3, when compared to the ORIGINAL conversion, then
  S1 ⊂ S2 ⊂ S3 and S3 differs from the original in exactly 3 cells.
  *test:* `TestNudge_MaskDrivenAttemptsRemainCumulativeFromOriginalConversion`
- **AC-034 / AC-035 / AC-036** unchanged and green
  (`TestNudge_AttemptsBoundedRecovery`, `TestNudge_ReportsFailureAtCap`,
  `TestNudge_FailureMessageSuggestsRetry`); FR-014 nudge-count reporting
  tests unchanged.

## Engineering constraints

- **EC-014** — For any uploaded image whose conversion reports MANY and any
  attempt number n in 1..5, the set of cells nudge attempt n flips is a
  subset of the solver's undecided/disagreement mask for the ORIGINAL
  conversion, has exactly min(n, |mask|) members, and contains every cell
  attempt n-1 flipped — for every image and every n. The cap of 5 and the
  re-verification of every nudged grid by the real solver (CON-005) are
  unchanged. Seeded corpus of scripted grids + masks, minimum case count
  asserted in the test, no hypothesis.
  *test:* `PropertyTest_Nudge_FlippedCellsSubsetOfUndecidedMaskAndNested`

## Guardrails

- G-1: `MAX_NUDGE_ATTEMPTS` (5), POL-002's `when`, POL-003's report-at-cap
  reaction and its message wording are unchanged (ADR-0002, AC-035/036).
- G-2: Every nudged grid is still judged through the one `judge_candidate`
  path (CON-005, INV-002); image mode never repairs (ADR-0024/R5) and
  never draws from the rng (ADR-0015).
- G-3: No edits under `src/nonogram/solver/`, `difficulty.py`,
  `export/**`, `web/**`, `admin/**`; `orchestrator.py` changes are limited
  to the nudge call site.
- G-4: Do not alter fixtures other than as CARD-070 permits
  (`tests/fixtures/bands.png`); `landscape.png` byte-identical.
- G-5: Do not touch the random-mode recovery loop (CARD-074).
- G-6: Commit only your own files — explicit pathspecs.

## System contract

- ADR-0002 — pixel-nudge cap is 5 (check: TestNudge_ReportsFailureAtCap)
- ADR-0024/R5 — image mode recovers by POL-002 only, never repairs (check:
  review-lens)
- ADR-0015 — image mode stays rng-free (check: review-lens)
- INV-002 / CON-005 — nudged grid accepted only on a fresh solver verdict
  of 1 (check: tests/test_nudge.py)
- INV-003 — one counter home in the orchestrator; `sourcing.image` counts
  nothing (check: tests/test_orchestrator.py)
- ADR-0007 — `sourcing/` imports no capability module; the mask arrives
  as a parameter from the orchestrator (check:
  test_every_import_in_the_package_points_inward)

## Architecture context

- **FR:** FR-013 (amended 2026-09-12; AC-115..AC-117), FR-024 (consumer),
  FR-014 (unchanged)
- **EC:** EC-014
- **ADR:** ADR-0002, ADR-0015, ADR-0024 (R5), ADR-0007
- **Domain:** POL-002 (mechanism note), POL-003, EVT-006 (carries the mask)
- **Components:** COMP-003 (sourcing/image), COMP-002 (call site)
- **Trace:** meta/architecture/trace.yml (FR-013 row)

**Checkpoint (from the Increment 9 checkpoint, the nudge half):** the
nudge tests are re-pinned to the mask-driven choice and green; a MANY
conversion's nudges all land inside its mask.
**Collapses:** FR-013's "which cell to flip is a guess" risk (CARD-016);
EC-014.
**Rollback:** revert the branch — `nudge_cells` returns to the 2x2
heuristic; no stored data changes.

## Worktree notes

—
