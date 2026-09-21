# CARD-074: Repair before redraw — flip one filled/empty pair inside the disagreement set, K=3 per lineage, one shared bound

**Status:** done
**Priority:** P1
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/074-repair-then-redraw
**Worktree:** ../PythonProject4-CARD-074
**Source:** meta/architecture/handoff.md#increment-9
**Idea:** —
**Wave:** 1
**Depends on:** CARD-073
**Touches:** src/nonogram/orchestrator.py (run_bounded branch, MAX_CONSECUTIVE_REPAIRS, repair step beside POL-001, run summary counts), tests/test_orchestrator.py, tests/test_resample.py, tests/property/test_recovery_bound.py (new), meta/architecture/decisions/adr/0002-*.md (History entry only), tests/test_naming.py and tests/test_sourcing_image.py (one `MAX_CONSECUTIVE_REPAIRS = 0` monkeypatch each — both are scripted random-mode tests counting *source* calls, which a repair does not make; added 2026-09-22 by CARD-071, closing review finding F-002)
**Review score:** 8.5 (cycle 1, one finding fixed)
**Started:** 2026-09-12T23:57Z
**Closed:** 2026-09-13T18:10Z
**Actual:** 1d
**Merge commit:** aa6d863
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
- **AC-D** (calibration, handoff checkpoint) — on a **36-seed 10x10
  density-30 corpus** the abandonment rate is not worse than pure redraw on
  the same seeds (18 with repair against 26 without, when written), and the
  20x20 calibration sweep ADR-0024 asks for is recorded in Worktree notes.
  *test:* `TestRecovery_AbandonmentRateNotWorseThanPureRedraw`
  *(Re-worded 2026-09-22 by CARD-071, closing review finding F-001. This AC
  named "the 100-request 20x20 density-20 seeded corpus" until then, while its
  test ran 36 seeds at 10x10 density 30. The test is the right artefact: on the
  corpus originally named the assertion is **vacuous** — all 60 sampled
  requests abandon at both `MAX_CONSECUTIVE_REPAIRS = 0` and `= 3`, so
  `with_repair <= pure_redraw` holds trivially — and the 20x20 sweep takes
  minutes, which is why it is a recorded measurement rather than suite work.
  The id and the test name are unchanged, per the FR-003/AC-009 convention.)*

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

### Where the repair sits

`generate`'s `attempt_candidate` closure decides what the *next* attempt is;
`run_bounded` is untouched and still counts. A random-mode candidate the solver
rejects leaves a `Repair` pending (computed by the pure, module-level
`repair_candidate` from the rejected grid's own witnesses and mask, which are
still on the aggregate at that point); the next call judges that grid instead
of drawing one. After `MAX_CONSECUTIVE_REPAIRS` consecutive repairs on one
lineage the pending repair is simply not set, and the next call draws from the
same `rng` — POL-001 exactly as before. Both kinds of attempt are attempts of
the one `regenerate` `RetryCounter`; `Puzzle.recovery` (a `RecoveryLog`) is a
tally, not a counter, and records how the 20 divided.

### Calibration (AC-D, the K=3 measurement ADR-0024 owes)

Same seeds, same requests, `MAX_CONSECUTIVE_REPAIRS = 0` (today's pure redraw)
against `= 3`. Solver calls are counted at `orchestrator.solver.solve`.

| corpus | metric | K=0 (redraw) | K=3 (repair) |
|---|---|---|---|
| 20x20, densities 20/25/30, seeds 0..19 (60 requests) | abandoned | 60 (100%) | 60 (100%) |
| | solver calls / accepted puzzle | n/a (none accepted) | n/a (none accepted) |
| | seconds / request | 1.258 | 1.242 |
| 10x10, densities 30/40/50, seeds 0..39 (120 requests) | abandoned | 32 (26.7%) | 22 (18.3%) |
| | solver calls / accepted puzzle | 5.39 | 4.77 |
| | seconds / request | 0.015 | 0.012 |
| 15x15, densities 40/50, seeds 0..19 (40 requests) | abandoned | 13 (32.5%) | 8 (20.0%) |
| | solver calls / accepted puzzle | 4.33 | 4.69 |
| | seconds / request | 0.215 | 0.211 |

**Reading.** Repair helps where the request is near-feasible and is free where
it is not. At 10x10 it removes 10 of 32 abandonments (-31% relative) and costs
*fewer* solver calls per accepted puzzle, because a repair that lands converges
in one or two attempts where a redraw re-rolls from scratch. At 15x15 it
removes 5 of 13 (-38%) for 8% more solver calls per accepted puzzle — it
converts abandonments into accepted puzzles, which is the trade ADR-0024 asked
for. The handoff's own corpus — 20x20 at density 20 — shows **no difference**:
every one of those 60 requests is abandoned either way. A 20x20 grid at 20-30%
density has an undecided mask covering essentially the whole grid (400 of 400
cells at density 20), so one pair flip cannot make it unique; those requests
are infeasible under a 20-attempt bound, with or without POL-006. Repair is not
worse there — the wall time per request is within noise (1.24s vs 1.26s),
because a repair costs one solve exactly as a redraw does.

**K is not retuned on this card** (the card says record and stop). The data K's
recalibration will want is now recorded per run in `Puzzle.recovery`: across the
10x10 corpus, 60 lineages hit K=3 and 309 repairs were made on accepted runs,
21 of them (6.8%) from the undecided-mask fallback region.

### The fallback region is a live path, not a defensive branch

ADR-0024's per-row filled-count argument holds only when the candidate grid is
itself one of the two witnesses. Often it is not — the witnesses are the first
two solutions the search found, and the candidate is frequently a *third*
solution. Measured here: at 20x20 density 20, 40 of 40 sampled ambiguous
candidates were third solutions and 9 of 40 (22.5%) had a disagreement set with
no filled/empty pair of the parent; over the property corpus (10x10/12x12) the
fallback supplied 32 of 466 repairs (6.9%). CARD-073's review measured 9 in 241
(3.7%) on its own corpus. It has both a forced unit test
(`test_falls_back_to_the_undecided_mask_when_the_disagreement_set_has_no_pair`)
and a corpus test that fails if real runs stop reaching it
(`test_the_fallback_region_is_reached_by_real_runs`).

### Determinism (AC-C)

`--seed 42 --size 10 --density 30` exports byte-identical puzzles on two
consecutive runs (the auto-name's duplicate counter aside), and
`test_the_same_seed_replays_the_same_repair_lineage` compares the recorded
repair sequence — region, emptied cell, filled cell — of two runs of the same
request, not merely the accepted grid. The repair draws nothing from the `rng`:
`test_a_repair_draws_nothing_from_the_rng` checks that the rng state entering
each draw is exactly its state leaving the previous one, across the corpus.

### Rollback switch, verified rather than asserted

`MAX_CONSECUTIVE_REPAIRS = 0` was checked against the pre-change code on main
(d48ade8) over 45 requests — 10x10 at densities 30/40/50, seeds 0..14 — and the
two agree on every request: same outcome, same accepted grid, same regenerate
and resample attempt counts, same abandonment messages. The repair step is off
by construction when K is 0 (the branch is never entered and no rng draw
moves), so the rollback is a constant, not a revert.

### Re-pinned test

`test_regenerate_stops_at_max_retry_bound_for_a_real_request` moved from seed 0
to seed 3 (10x10, density 30): with POL-006 live, seed 0 now succeeds on its
nineteenth attempt after fourteen repairs. That is ADR-0024's stated Negative
("every existing random seed that ever hit MANY now maps to a different
accepted grid"), not a regression. The scripted POL-001 tests in
`tests/test_orchestrator.py` and `tests/test_resample.py` now call
`_without_repairs(monkeypatch)` (`MAX_CONSECUTIVE_REPAIRS = 0`, ADR-0024's own
rollback switch), so they keep asserting the pure-redraw loop one-to-one
against their scripts while the repair-on behaviour has its own section.

### Cycle-1 review fix — F-003, the repeat tally

`RecoveryLog` gained `repeated_attempts`: repairs that re-judged a grid their
own lineage had already judged. It is observability only — the pair choice is
still ADR-0024/R4's first-by-(row, column) rule, unamended — and that was
verified rather than asserted: the 90-request determinism probe returns
byte-identical grids, attempt counts and tallies before and after the change,
and `MAX_CONSECUTIVE_REPAIRS = 0` still matches pre-CARD-074 `main` exactly.

**Why the field earns its place.** `lineages_at_repair_cap` was going to be the
number ADR-0024's deferred K calibration read, and on its own it conflates two
populations. The pathological grid in `test_repair_attempts_count_against_the_retry_bound`
shows it at full strength: five lineages, all five at the cap — which reads as
"K is too tight, try 5" — while ten of the fifteen repairs were re-solving a
grid the lineage had already judged. Two thirds of the repair budget went on
known grids, so a larger K there buys solver time and nothing else.

**Measured on real runs**, 1,502 ambiguous candidates at 10x10-15x15: repeats
occur in roughly 7% of lineages, 154 repeat attempts in all, and 105 of 106
sampled are an immediate reversal of the previous flip rather than a longer
return.

**What was deliberately not done.** Skipping a pair whose result the lineage
already judged was measured before being rejected: it costs nothing
(21.5s against 21.6s over the same corpus — a lineage holds at most four grids)
but converts only 13 more lineages of 1,502, 32.6% against 31.8%. That is under
a percentage point in exchange for amending ADR-0024/R4, which this card has no
mandate to do. Recorded here so the recalibration can weigh it with numbers.

**Tests.** `test_a_cycling_lineage_is_told_apart_from_one_still_making_progress`
pins the contrast; `test_the_repeat_tally_reads_zero_on_a_lineage_that_keeps_finding_new_grids`
pins the zero case on a real seeded run so the field cannot become a constant;
`test_the_repeat_tally_agrees_with_an_independent_count` re-derives the count
from the outside, off the recorded (parent, repaired) pairs, and fails if the
corpus ever stops containing a cycling lineage.
