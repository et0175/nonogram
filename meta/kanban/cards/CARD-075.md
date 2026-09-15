# CARD-075: Image-mode nudge adds one cell per attempt from where the solver's witnesses disagree

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false  _(revised 2026-09-15 from CARD-096 — see Revision)_
**Skill:** python-pro
**TDD:** —
**Branch:** card/075-mask-driven-nudge
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-9 (FR-013 amendment, split from CARD-074 by decompose)
**Idea:** —
**Wave:** 1
**Depends on:** CARD-073
**Touches:** src/nonogram/sourcing/image.py (nudge_cells, nudge), src/nonogram/orchestrator.py (the nudge call site only — it keeps the attempt's chosen cells, as it keeps the repair lineage), tests/test_nudge.py, tests/property/test_nudge_mask.py (new), meta/architecture/requirements.yml (FR-013 AC-115/AC-116, EC-014 — amended by this card), docs/GENERATION_ALGORITHM.md (§8.4)
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Revision — 2026-09-15, from CARD-096's measurement (owner: "revise CARD-075")

This card was written on 2026-09-12, before anyone had measured why image mode
abandons. CARD-096 measured it, and two of the choices below were wrong in a
way the data makes plain. **What changed, and why:**

1. **The source of cells is the witness-disagreement set, with the undecided
   mask as the fallback** — not the mask first. On the original conversion of
   every abandoned picture, the two witnesses disagreed on **4 cells in 27 of
   34** (one 2x2 block that can be drawn either way), while the undecided mask
   covered a median **35% of the grid** and up to 100%. Ranking inside a mask
   that size is guessing again; the disagreement set is the ambiguity itself.
2. **Each attempt adds one cell chosen from the previous attempt's verdict** —
   not the best n cells chosen once from the original conversion. Flipping one
   cell of an ambiguous block usually exposes the *next* ambiguity somewhere the
   original disagreement set never contained. Measured on the 36 dither failures,
   cap 5, both variants nested and exactly n cells from the picture:
   **static 9 of 36, adaptive 19 of 36** (CARD-096, *Follow-up measurement*).
   Today's nudge rescued 0 of those.

**What did not change:** the policy half. The cap is 5 (ADR-0002); POL-003
reports at the cap with the same message; every nudged grid is judged by the one
`judge_candidate` path; image mode never draws from the rng and never repairs.
And the user-facing promise FR-013's cumulative property exists for still
holds in full: **attempt n differs from the uploaded picture's conversion in
exactly n cells, and contains every cell attempt n−1 flipped** — no edit is ever
undone. What changes is only *which* cell each attempt adds.

**It cannot break a picture that works today.** The nudge runs only when the
conversion is not unique, so every puzzle made at the first solve is untouched.

**Sequencing with CARD-079** is unchanged — this card first. CARD-096 measured
the two together at 32 of 36, with no regression on the 89 conversions dither
makes today; CARD-079's AC-127 is taken after this lands.

**The owner question below** ("fewer than n cells in the mask") is superseded:
attempts no longer draw n cells from one fixed set. Its successor is AC-116's
fallback rule.

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

**Owner question (FR-013 _meta.gaps, recorded not invented) — _superseded 2026-09-15, see Revision; kept for the record_:** what does
attempt n do when the mask holds fewer than n cells? EC-014 reads it as
"flip all min(n, |mask|) of them" — implement that reading and record it
in the module docstring; if the owner wants a secondary ranking instead,
that is a follow-up, not this card.

## What to implement

*(Revised 2026-09-15 — see the Revision section.)*

1. `sourcing.image.next_nudge_cell(grid, flipped, witnesses, undecided_mask)`
   returns the one cell attempt n adds, or `None`. `grid` is the grid the
   *previous* attempt judged (the original conversion for attempt 1); `flipped`
   is the set of cells already changed from the original. Candidates are the
   cells where the two witnesses differ, excluding `flipped`; if there are none,
   the undecided mask's cells, excluding `flipped`. Within the candidates, rank
   by Chebyshev distance to the nearest differently-valued neighbour (ink
   boundary) ascending, then (row, column). A pure function: no rng, no count,
   no state (INV-003 — `sourcing.image` counts nothing).
2. `sourcing.image.nudge(original, cells)` returns the original conversion with
   exactly `cells` flipped — the whole of nesting is that the caller passes
   attempt n−1's cells plus one. The 2x2 switching-block ranking
   (`nudge_cells`, `_switch_counts`, `_boundary_counts`) is retired.
3. The orchestrator's nudge call site keeps the chosen cells across attempts
   in its closure, as `attempt_candidate` keeps the repair lineage: each
   attempt reads the witnesses and mask `judge_candidate` stored for the
   *previous* candidate, asks `next_nudge_cell`, appends it, and judges
   `nudge(original, cells)`. When `next_nudge_cell` returns `None` the attempt
   has nothing to add and returns `None` — the counter still advances, so the
   cap and POL-003's report are reached exactly as today. Cap, counter,
   `run_bounded` exhaustion branch and POL-003 wording unchanged.
4. Re-pin `tests/test_nudge.py` to the mask-driven choice: the scripted
   sources gain a mask; real-image pins are re-taken honestly (CARD-070's
   convention: the docstring states the count and where it came from).
   The mechanism-agnostic tests (cap, failure message, CLI reporting —
   AC-034..AC-036, FR-014) must pass unchanged in assertion.
5. Rewrite the docstrings and `docs/GENERATION_ALGORITHM.md` §8.4's
   paragraph on cell choice; keep `meta/ops/check_doc_references.py` passing.
6. Amend FR-013's AC-115/AC-116 and EC-014 in `meta/architecture/requirements.yml`
   to the revised rule (below), with a `_meta` note citing CARD-096.
7. Re-run `PYTHONPATH=src python meta/ops/image_abandonment_sweep.py` and record
   the before/after in Worktree notes.

## Acceptance criteria

- **AC-115** *(revised)* — given a candidate the solver reported MANY for, whose
  witnesses disagree on a set D, when the next nudge attempt is built, then the
  one cell it adds is a member of D not already flipped.
  *test:* `TestNudge_AddsACellWhereTheWitnessesDisagree`
- **AC-116** *(revised)* — given a MANY candidate whose witness-disagreement
  cells are all already flipped (or absent), when the next attempt is built,
  then the added cell comes from that candidate's undecided mask; and given
  neither holds an unflipped cell, then the attempt adds nothing and returns no
  candidate, and the counter still advances. Within either source the cell
  nearest the ink boundary is chosen, then (row, column).
  *test:* `TestNudge_FallsBackToTheMaskThenStops`, `TestNudge_PrefersCellsNearestInkBoundary`
- **AC-117** *(unchanged in substance)* — given attempts 1, 2 and 3 with flipped
  sets S1, S2, S3, when compared to the ORIGINAL conversion, then
  S1 ⊂ S2 ⊂ S3 and S3 differs from the original in exactly 3 cells.
  *test:* `TestNudge_MaskDrivenAttemptsRemainCumulativeFromOriginalConversion`
- **AC-172** *(new — the measured effect)* — the corpus sweep
  (`meta/ops/image_abandonment_sweep.py`, all 25 pictures, sizes 10..30) makes
  **at least 19 more** of the 36 conversions that dithering fails today than it
  did before this card, and **every** conversion made before is still made.
  The second half holds by construction (the nudge runs only on a non-unique
  conversion); the first is CARD-096's adaptive, nested measurement, and a
  result below it is reported rather than shipped. Numbers, not a test: the
  corpus is not in the suite's time budget.
- **AC-034 / AC-035 / AC-036** unchanged and green
  (`TestNudge_AttemptsBoundedRecovery`, `TestNudge_ReportsFailureAtCap`,
  `TestNudge_FailureMessageSuggestsRetry`); FR-014 nudge-count reporting
  tests unchanged.

## Engineering constraints

- **EC-014** *(revised)* — For any uploaded image whose conversion reports MANY
  and any attempt number n in 1..5 that adds a cell, the set of cells attempt n
  flips has exactly one more member than attempt n−1's, contains every cell
  attempt n−1 flipped, and its new cell belongs to the witness-disagreement set
  of attempt n−1's candidate or, when that holds no unflipped cell, to that
  candidate's undecided mask — for every image and every n. The grid attempt n
  judges differs from the ORIGINAL conversion in exactly those cells. The cap of 5 and the
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

**Checkpoint (from the Increment 9 checkpoint, the nudge half, revised):** the
nudge tests are re-pinned to the disagreement-driven choice and green; every
nudge attempt adds one cell from the previous candidate's disagreement set (mask
fallback); the corpus sweep's before/after is in Worktree notes.
**Collapses:** FR-013's "which cell to flip is a guess" risk (CARD-016);
EC-014.
**Rollback:** revert the branch — `nudge_cells` returns to the 2x2
heuristic; no stored data changes.

## Worktree notes

—
