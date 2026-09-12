# CARD-074: Repair before redraw — flip one filled/empty pair inside the disagreement set, K=3 per lineage, one shared bound

**Status:** ready
**Priority:** P1
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/074-repair-then-redraw
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-9
**Idea:** —
**Wave:** 1
**Depends on:** CARD-073
**Touches:** src/nonogram/orchestrator.py (run_bounded branch, MAX_CONSECUTIVE_REPAIRS, repair step beside POL-001, run summary counts), tests/test_orchestrator.py, tests/test_resample.py, tests/property/test_recovery_bound.py (new), meta/architecture/decisions/adr/0002-*.md (History entry only)
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why

In random mode every uniqueness failure is an ambiguity (MANY — a count of
0 cannot occur because the clues come from a real grid), and today's only
reaction is to throw the candidate away and redraw (POL-001), re-rolling the
same odds and discarding what the solve learned. At mid density and 30x30+
that abandons real requests after 20 attempts
(`docs/GENERATION_ALGORITHM.md` §10.2). ADR-0024 (resolving DEC-029, owner's
choice `redraw_then_repair`) has the orchestrator first REPAIR the candidate
from the witness-disagreement set CARD-073 now exposes, up to K consecutive
times on one lineage, then redraw — all inside ADR-0002's single 20-attempt
bound.

**Sequencing.** After CARD-073 (needs the mask and the second witness on
`SolveResult`). Independent of CARD-075 (image nudge) and CARD-076
(scoring); may run in parallel with them — the only shared file with
CARD-076 is `orchestrator.py` (conflict-graph matter, not a guardrail).

## What to implement

COMP-002 (`orchestrator.py`) gains the repair step beside POL-001 (POL-006
`RepairCandidateOnUniquenessFailure` -> CMD-014 -> EVT-015, always followed
by a fresh CMD-005 solve):

1. **Region.** On MANY for a random-mode candidate, take the
   witness-disagreement set (cells where the two witnesses differ). Only if
   that set holds no filled/empty pair of the parent grid — which the
   per-row filled-count argument says cannot happen but the code must not
   assume — fall back to the first-fixed-point undecided mask. Cells
   outside the chosen region are never touched (ADR-0024/R3).
2. **Flip.** Exactly one cell filled in the parent becomes empty and
   exactly one empty becomes filled, both inside the region; the filled
   count of the repaired grid equals its parent's, so the requested density
   holds by construction (ADR-0003 untouched).
3. **Pair choice.** Deterministic, no rng draw: rank the region's filled
   cells and empty cells by (row, column) and take the first of each
   (ADR-0024/R4). Same seed replays the same lineage on every machine
   (ADR-0015).
4. **Re-verify.** Re-derive clues (FR-005) and solve through the ONE
   `judge_candidate` path — the real solver forms the verdict (CON-005),
   `confirm_uniqueness` is the only acceptance point (INV-002). A repaired
   grid is never assumed unique (ADR-0024/R1).
5. **Escape.** `MAX_CONSECUTIVE_REPAIRS = 3`, a named constant beside
   `MAX_RETRY_ATTEMPTS`, never a second bound (ADR-0024/R2). After K
   consecutive repairs on one lineage without a unique verdict, discard and
   redraw from the same injected rng (POL-001); recovery continues from
   there. `run_bounded`'s attempt callable must know whether the current
   candidate is a fresh draw or a repair and how many consecutive repairs
   it has had.
6. **One counter.** Repairs and redraws advance the same `RetryCounter`
   (INV-003); exhausting it raises `GenerationAbandoned` whichever kind of
   attempt came last (POL-005). Timeouts (`SolverTimeout`) and invalid
   input still propagate.
7. **Random mode only** (ADR-0024/R5). Library mode keeps POL-001 redraw;
   image mode keeps POL-002 nudge (CARD-075). Neither ever repairs.
8. **Observability** (ADR-0024 Neutral): per-run counts of repairs vs
   redraws and of lineages that hit K in the orchestrator's run summary —
   the data the K recalibration needs. Additive; no export schema change
   (ADR-0023 untouched).
9. **Rollback switch by construction:** `MAX_CONSECUTIVE_REPAIRS = 0`
   restores today's pure-redraw behaviour without a revert.
10. **ADR-0002 History entry** (owed by ADR-0024): repairs and redraws share
    the one 20-attempt bound; K is an interleaving split of that budget,
    not a second bound; the 20 and the 5 stand. History only.
11. **Calibration measurement** (the K=3 calibration ADR-0024 says is
    owed): on a seeded corpus of 100 random 20x20 requests at density 20,
    report the abandonment rate and mean solver calls per accepted puzzle
    against today's pure-redraw loop on the same seeds
    (`MAX_CONSECUTIVE_REPAIRS = 0` vs `3`). Write both numbers to Worktree
    notes. Do not retune K on this card — record and stop.

## Acceptance criteria

- **AC-111** — given a random 20x20 candidate at density 40 whose solve
  reports MANY with a 6-cell undecided mask, when the repair step runs
  once, then exactly one filled cell and one empty cell inside that 6-cell
  mask have swapped values.
  *test:* `TestRecovery_RepairFlipsOnePairInsideUndecidedMask`
- **AC-132** — same candidate and mask, when the repair runs once, then
  every cell outside the mask holds the value it held before.
  *test:* `TestRecovery_RepairLeavesCellsOutsideMaskUntouched`
- **AC-112** — given a recovered candidate (redrawn or repaired) not yet
  solved, when the pipeline decides whether to accept it, then it is
  accepted only after a fresh solver run on its clues reports
  solution_count 1.
  *test:* `TestRecovery_RecoveredGridIsReverifiedBySolver`
- **AC-113** — given a random-mode request whose every candidate and every
  repair stays non-unique, when redraws and repairs together reach the
  ADR-0002 bound of 20, then generation is abandoned with the existing
  `GenerationAbandoned` and the bound counts both kinds in one counter.
  *test:* `TestRecovery_RepairAttemptsCountAgainstRetryBound`
- **AC-114** — given a 20x20 candidate at density 40 (160 filled) repaired
  5 times in a row, when the filled cells of each repaired grid are
  counted, then every repaired grid has exactly 160 filled cells.
  *test:* `TestRecovery_RepairKeepsFilledCountExact`
- **AC-A** (K boundary, both sides; ADR-0024 Negative) — a scripted source
  returning an ambiguous grid: the 3rd consecutive repair on a lineage is
  still a repair; the 4th attempt is a redraw from the same rng; the
  counter arithmetic is asserted across the boundary.
  *test:* `TestRecovery_RedrawsAfterKConsecutiveRepairs`
- **AC-B** (fallback region is exercised, not dead code) — a witness pair
  constructed so the disagreement set holds no filled/empty pair forces
  the undecided-mask fallback.
  *test:* `TestRecovery_FallsBackToUndecidedMaskWhenNoPairInDisagreementSet`
- **AC-C** (ADR-0015) — `--seed 42` replays the identical repair lineage
  twice (same accepted grid, same attempt counts, same repair/redraw
  sequence).
  *test:* `TestRecovery_SameSeedReplaysSameRepairLineage`
- **AC-D** (calibration, handoff checkpoint) — on the 100-request 20x20
  density-20 seeded corpus the abandonment rate is not worse than pure
  redraw on the same seeds; both numbers recorded in Worktree notes.
  *test:* `TestRecovery_AbandonmentRateNotWorseThanPureRedraw`

## Engineering constraints

- **EC-013** — For any random-mode request: no grid is ever accepted
  without a solver verdict of exactly 1 obtained on that grid's own clues;
  the total number of recovery attempts (redraws plus repairs) never
  exceeds the single ADR-0002 bound; and when a repair is applied, the
  repaired grid has a filled-cell count equal to its parent's and differs
  from it only inside the undecided/disagreement region. Holds for every
  seed and extent. Seeded corpus, minimum case count asserted in the test.
  *test:* `PropertyTest_Recovery_AcceptedGridsHaveRealVerdictsWithinOneBound`
- **EC(ADR-0024/R4)** — The pair choice is a deterministic function of the
  grid and the witnesses, drawing nothing from the injected `Random` or
  host state: the rng stream is not perturbed by repairs (compare the rng
  state before/after a repair; same seed, same lineage).
  *test:* `PropertyTest_Recovery_RepairDrawsNothingFromRng`
- **EC(ADR-0003, density after repair)** — every repaired grid's density
  equals its parent's exactly (filled count preserved), across the corpus.
  *test:* `PropertyTest_Recovery_RepairedGridDensityExact`

## Guardrails

- G-1: A repaired grid is never accepted without a fresh solver verdict of
  1 on its own re-derived clues (ADR-0024/R1, INV-002, CON-005).
- G-2: One bound — `MAX_RETRY_ATTEMPTS` (20) — one `RetryCounter`;
  `MAX_CONSECUTIVE_REPAIRS` is never a second bound (ADR-0024/R2,
  INV-003, ADR-0002). The 20 and the 5 stand.
- G-3: Random mode only (ADR-0024/R5) — library and image paths
  behaviourally unchanged; `tests/test_nudge.py` and
  `tests/test_sourcing_library.py` untouched and green.
- G-4: No edits under `src/nonogram/solver/`, `sourcing/**`,
  `difficulty.py`, `export/**`, `web/**`, `admin/**`; the oracle and
  `tests/property/test_solver_uniqueness.py` untouched.
- G-5: No rng draw in the repair (ADR-0024/R4, ADR-0015); no clock reading
  in any recovery decision.
- G-6: `GenerationAbandoned` keeps naming the attempt count and the bound
  (POL-005 wording, AC-113); tests/test_generation_failures.py stays green.
- G-7: Do not touch the nudge mechanism (CARD-075) or the scorer/tier
  (CARD-076) — `orchestrator.py` is shared with CARD-076 this wave; keep
  the diff to the recovery loop.
- G-8: ADR-0002 edit is a History entry only.
- G-9: Commit only your own files — explicit pathspecs.

## System contract

- ADR-0024/R1 — repaired grid accepted only after a fresh solver run on its
  own re-derived clues reports exactly 1 (check:
  PropertyTest_Recovery_AcceptedGridsHaveRealVerdictsWithinOneBound)
- ADR-0024/R2 — repairs and redraws advance the same RetryCounter bounded
  by MAX_RETRY_ATTEMPTS (20); K is a named constant, never a second bound
  (check: TestRecovery_RepairAttemptsCountAgainstRetryBound)
- ADR-0024/R3 — exactly one filled and one empty cell flipped, both inside
  the witness-disagreement set (fallback: undecided mask) (check:
  TestRecovery_RepairKeepsFilledCountExact)
- ADR-0024/R4 — pair choice deterministic in (grid, witnesses), no rng or
  host state (check: review-lens)
- ADR-0024/R5 — POL-006 fires only for random mode (check: review-lens)
- INV-002 — a puzzle is marked ready for export only after the uniqueness
  check on that grid (check: tests/test_orchestrator.py)
- INV-003 — the automatic-retry counter never exceeds its bound (check:
  tests/test_orchestrator.py, tests/test_resample.py)
- CON-005 — the solver's verdict is the only uniqueness authority
- ADR-0015 — a seed replays the same run on every machine (check:
  TestRecovery_SameSeedReplaysSameRepairLineage)
- ADR-0007 — orchestrator drives capability modules; no lateral imports
  (check: test_every_import_in_the_package_points_inward)

## Architecture context

- **FR:** FR-025 (AC-111..AC-114, AC-132); FR-007 mechanism note
- **NFR:** NFR-002 (bounded retries)
- **EC:** EC-013
- **ADR:** ADR-0024 (R1..R5), ADR-0002 (History owed), ADR-0003, ADR-0015,
  ADR-0007
- **Domain:** POL-006, CMD-014, EVT-015, POL-001, POL-005, INV-002, INV-003
- **Components:** COMP-002 (owner), COMP-005 (verdicts + region), COMP-003
  (redraw source)
- **Trace:** meta/architecture/trace.yml (FR-025 row)

**Checkpoint (handoff, verbatim):** On a seeded corpus of 100 random 20x20
requests at density 20, the abandonment rate and mean solver calls per
accepted puzzle are both reported against today's pure-redraw loop on the
same seeds — the K=3 calibration ADR-0024 says is owed. `--seed 42` replays
the identical repair lineage twice.
**Collapses:** FR-025, EC-013, ADR-0024's unmeasured K, the wasted-budget
failure mode at low density that motivated the delta. (FR-013's "which cell
to flip is a guess" risk collapses with CARD-075.)
**Rollback:** `MAX_CONSECUTIVE_REPAIRS = 0` restores today's behaviour
without a revert; a full revert is one branch. No stored data changes.

## Worktree notes

—
