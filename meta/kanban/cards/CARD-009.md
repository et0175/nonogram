# CARD-009: Difficulty scoring formula from solver signals

**Status:** review
**Priority:** P1
**Category:** feature
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/009-difficulty-scoring
**Worktree:** ../PythonProject4-card-009
**Source:** meta/architecture/handoff.md#increment-2
**Idea:** —
**Wave:** 6
**Depends on:** CARD-004, CARD-006, CARD-007
**Touches:** src/nonogram/difficulty.py, src/nonogram/solver/__init__.py, src/nonogram/solver/search.py, tests/test_difficulty.py
**Review score:** 9.2 (cycle 1/3)
**Started:** 2026-08-28T10:17:03Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

COMP-006 (Difficulty Scoring) — the second-riskiest thing in the plan after the solver, and
the reason Increment 2's checkpoint exists: the formula is untested until real puzzles are
scored.

1. **Solver signal emission (COMP-005).** The five signals of FR-009 are internal states of
   the hand-rolled solver (ADR-0009), so COMP-005 emits them: cells solved by line-only
   logic before the first branch, backtracking amount (branch nodes visited / depth), solve
   time, puzzle size, clue density. CARD-004 already returns them as part of the solve
   result — finish/normalize the surface here if a signal is missing, but do not change how
   the solver solves.
2. **Normalization and weighting (COMP-006, ADR-0013).** Normalize each signal to 0..1 and
   combine into a single 0..100 score with the ADR-0013 weights. Size and clue density are
   normalizers, not difficulty in themselves — a big easy puzzle must not out-score a small
   hard one purely on cell count.
3. **Monotonicity sanity.** A puzzle solved entirely by line logic with zero backtracking
   must land at the easiest end of the scale (AC-023). That is the anchor point of the whole
   scale; if the weights make it possible to score such a puzzle mid-range, the weights are
   wrong, not the test.
4. Keep `difficulty.py` a pure function of the solve result — no solver re-entry, no I/O.
   CARD-010's resample loop calls it once per candidate.

## Acceptance criteria

- **AC-022** (happy) — given solver signals for a 15x15 candidate (80% of cells solved by
  line-logic, low backtracking, 0.2s solve time), when the candidate is scored, then a single
  numeric difficulty score is produced reflecting the weighted combination of all signals.
  *test:* `TestScoreDifficulty_CombinesSignals`
- **AC-023** (boundary) — given a candidate solved entirely by line-logic with zero
  backtracking, when the candidate is scored, then the score falls at the easiest end of the
  scale.
  *test:* `TestScoreDifficulty_ZeroBacktrackingScoresEasiest`

## Guardrails

- G-1: Do not edit `src/nonogram/export/**` — owned by CARD-012 and CARD-013 this wave
- G-2: Do not edit `src/nonogram/sourcing/**` — owned by CARD-008 this wave
- G-3: Do not edit `src/nonogram/orchestrator.py`, `src/nonogram/cli.py` — the tier selector
  and resample loop are CARD-010; this card only produces a score
- G-4: **Solver semantics unchanged.** This card may extend the solver's signal *reporting*
  (Increment 2 is additive), but must not alter propagation, search order, or the uniqueness
  verdict. `PropertyTest_Solver_NeverFalsePositiveUniqueness`, `TestSolver_ReportsUniqueSolution`,
  `TestSolver_FailsFastOnSecondSolution` and `TestGenerate_50x50_RespectsTimeoutBound` must
  still pass unchanged (handoff Increment 2 Rollback: "revert without touching the solver or
  orchestrator's core generation logic")
  (test: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- G-5: Difficulty is a heuristic score bucket, not a construction guarantee (CON-004). Do not
  add grid-construction logic that tries to *build* an easy or hard puzzle — scoring
  classifies candidates, it never shapes them
- G-6: Signal collection must not move the NFR-001 p95 budget — instrumentation stays O(1)
  per propagation step (test: BenchGenerate_20x20_p95Under5s)

## System contract

- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions (check: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (check: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (check: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF)
- INV-003 — A puzzle's automatic-retry counter (regenerate, resample, pixel-nudge) never exceeds its configured maximum bound (check: TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestNudge_ReportsFailureAtCap, TestRetryLoop_BoundedIterations)

## Architecture context

- **FR:** FR-009
- **NFR:** —
- **CON:** CON-004
- **ADR:** ADR-0009, ADR-0013
- **Components:** COMP-006 (Difficulty Scoring), COMP-005 (signal emission)
- **Trace:** meta/architecture/trace.yml

## Worktree notes

### Summary

`src/nonogram/difficulty.py` (new) implements ADR-0013's 0..100 scale as a pure function of
the signals one solve already produced, plus `tests/test_difficulty.py` (22 tests) covering
both ACs, the monotonicity properties, the scale's ends and the module's contract.

**No solver change was needed and none was made.** CARD-004/006 already report every FR-009
signal or the raw material for it, so `src/nonogram/solver/search.py` and
`src/nonogram/solver/__init__.py` — both in the predicted Touches — are untouched. `git diff`
against the branch point is empty for every tracked file; the card adds two new files and
edits this one.

Result: 658 passed, 1 xfailed (the pre-existing AC-037/CARD-018 xfail), up from the
636 passed / 1 xfailed baseline. No regressions.

### STRUCTURE-1: no new solver signals — all five of FR-009's are already reported or derivable

`SolveSignals` (CARD-004) carries `line_logic_cells`, `total_cells`, `branch_nodes`,
`backtracks` and `elapsed_seconds`. Against FR-009's five signals: line-logic coverage is
`line_logic_cells`, backtracking amount is `branch_nodes` (ADR-0013 names branch nodes as
that term), solve time is `elapsed_seconds`, puzzle size is `total_cells` — which is exactly
ADR-0013's size-relative denominator, so no height/width is needed. Only clue density was
absent, and it is not a solver-internal signal at all: it is a property of the clues the
caller already holds (`sum of all runs / total_cells`), so it is computed in `difficulty.py`
(`clue_density`). Why: G-4 asks for the solver's semantics to be unchanged, and the smallest
possible way to honour that is to change no solver line at all. It also makes G-6 exact
rather than approximate — zero instrumentation was added, so per-propagation-step cost is
provably unmoved, not merely measured as unmoved.

### STRUCTURE-2: the signals arrive by structural Protocol, not by import (ADR-0007)

`difficulty.py` may not import `nonogram.solver`: both are capability modules at the same
rank, and `tests/test_cli.py::test_every_import_in_the_package_points_inward` walks the AST
of every module on disk and fails a lateral import (a `TYPE_CHECKING` import would fail it
too — the walk does not care where the import sits). So `difficulty.SolverSignals` is a
read-only `typing.Protocol` over the four members the scorer reads, which
`solver.SolveSignals` satisfies as-is. The orchestrator, which sits outward of both, is what
hands one to the other. Because nothing in the package would then notice a field rename,
`test_solver_signals_satisfy_the_protocol_this_module_scores` scores a real `SolveSignals`
and asserts the member names, so the seam is checked where it cannot be imported.

### STRUCTURE-3: the scorer takes the signals, not the whole `SolveResult`

`score_difficulty(signals, clues, *, weights=SIGNAL_WEIGHTS)`. The verdict and the solution
grid are not inputs to a difficulty score, and taking them would mean a second protocol for
no gain. Call site is `score_difficulty(result.signals, clues.rows)`. `clues` may be passed
in either orientation — row clues and column clues of one grid encode the same filled cells,
so density comes out the same (pinned by a test), which removes the classic transposition
bug at CARD-010's call site. Scoring deliberately does **not** check uniqueness: INV-002 is
the caller's gate, and a scorer that raised on a non-unique candidate would be a second place
that invariant lives.

### STRUCTURE-4: effort as a fixed-weight sum, size and density strictly as multipliers

ADR-0013 says two things that do not sit together literally: "the five normalized values are
combined via a fixed-weight sum", and "size and density act as NORMALIZERS on the other
signals rather than as independent additive terms in their own right ... AC-023 [holds] by
construction ... because size only ever appears as a denominator". The second is the binding
one — it is the claim AC-023 rests on — so the implementation is:

    effort = W.line_logic * (1 - coverage) + W.backtracking * branch_pressure
           + W.solve_time * time_pressure                       # weights sum to 1.0
    relief = 1 - W.size * (1 - size_pressure) - W.density * (1 - density_pressure)
    score  = 100 * effort * relief

All five signals are in the score with fixed weights from one named, tunable table
(`SIGNAL_WEIGHTS`), satisfying AC-022 as written; size and density never add, only discount,
satisfying the normalizer clause and ADR-0013's stated failure mode ("a big easy puzzle must
not out-score a small hard one purely on cell count" — its own test).

### STRUCTURE-5: normalizer denominators

Coverage and branch pressure are per ADR-0013 verbatim (`/ total_cells`, branch pressure
capped at 1.0). Two denominators the ADR left to implementation:

- **Time.** `SECONDS_PER_CELL_BUDGET = 5.0 / 400` — NFR-001/ADR-0001's 5s p95 cap for 20x20,
  per cell, so the time term is size-relative like the other two rather than an absolute
  clock reading that would score every large puzzle Hard.
- **Size.** Stretched between `MIN_SUPPORTED_CELLS = 100` and `MAX_SUPPORTED_CELLS = 2500`
  (docs/requirements.md decision 6: 10x10..50x50). Out-of-range grids clamp rather than
  raise — an out-of-size puzzle is COMP-002's input-validation matter, not a scorer's.

Every ratio is clamped to 0..1, so no single signal can push the score off its own scale.

### STRUCTURE-6: `SignalWeights` validates itself; tier cutoffs are left to CARD-010

The weight table is a frozen dataclass that rejects, on construction, effort weights that do
not sum to 1.0 and normalizer weights that sum above 1.0. Neither mistake would fail anywhere
else — the first silently moves the top of the scale ADR-0005's cutoffs are drawn on, the
second can make `relief` negative and invert the score — so a future recalibration (which
ADR-0013 expects) fails loudly instead of quietly. The Easy/Medium/Hard constants themselves
are **not** added here: CARD-010's card claims them explicitly ("keep the cutoffs as named
constants in difficulty.py next to the formula"), and this card owns the scale, not the bands
drawn on it. Nothing here reads a tier.

### How AC-023's anchor is guaranteed by the formula

A candidate solved entirely by line logic with zero backtracking has, by definition,
`line_logic_cells == total_cells` and `branch_nodes == 0`, so `line_logic_gap == 0` and
`branch_pressure == 0` **exactly** — both terms vanish, whatever the puzzle's size or density.
That leaves `effort <= W.solve_time` (the time term is itself capped at 1.0), and `relief` is
a multiplier bounded in `[1 - W.size - W.density, 1] = [0.70, 1.0]` — it can only ever shrink
a number that is already near zero, never add to it or invert it. Hence:

    score <= 100 * W.solve_time = 15   for ANY zero-backtracking, fully-line-logic candidate

That is a hard ceiling on the 100-point scale, independent of grid size, clue density,
machine speed and load — a machine slow enough to burn a 50x50's entire 31-second budget on
one propagation sweep still cannot push such a puzzle past 15, comfortably inside ADR-0005's
Easy band (<= 33). The ceiling is the property the tests assert (`ANCHOR_CEILING`), so AC-023
holds by construction rather than by calibration, and a retune that broke it fails at
`test_the_shipped_weights_keep_the_anchor_inside_the_easiest_band` rather than at whichever
AC test noticed first. In practice a real line-logic-only solve spends a thousandth of its
time budget: the observed score for the 5x5 plus sign and for a 15x15 line-logic-only
candidate is under 0.05 of a point, and the tests assert `< 1.0` on top of the ceiling.

Sanity spread of the resulting scale (synthetic signals, default weights): 15x15 line-logic
only `0.02`; AC-022's candidate (80% coverage, 5 branches, 0.2s) `8.5`; 15x15 60%/40
branches/1.0s `25.1`; 15x15 30%/150 branches/2.5s `61.1`; a nasty 20x20 `79.9`; the worst
case `100.0`. The bands are populated rather than everything piling up at one end, though
ADR-0013 is explicit that the weights are provisional until real distributions are observed.

### Verification

- **AC-022** `test_combines_signals_into_one_number_on_the_scale`,
  `test_combines_all_five_signals_and_not_a_subset` (each of the five signals, perturbed
  alone, must move the score), `test_combines_signals_by_the_documented_weighted_formula`.
- **AC-023** three ways: `test_zero_backtracking_scores_at_the_easiest_end` (the arithmetic),
  `test_zero_backtracking_scores_easiest_at_every_size_and_density` (20 size/density
  combinations, up to 50x50 at the hardest density — the "by construction" claim), and
  `test_zero_backtracking_scores_easiest_on_a_real_solve` (a real solve of the plus sign, so
  the anchor is not resting on a fixture that flatters it).
- **Monotonicity** beyond the named case: a spread of branch counts `(0, 1, 5, 25, 100, 224,
  225, 1000)` must be non-decreasing and saturate past the cap; coverage `(0 .. 225)`
  non-increasing; solve time non-decreasing and saturating; plus
  `test_a_big_easy_puzzle_does_not_outscore_a_small_hard_one` and
  `test_a_puzzle_that_needs_guessing_scores_above_one_that_does_not` (two real solves).
- **G-4** — the four named tests re-run and pass unchanged:
  `tests/property/test_solver_uniqueness.py` (2 passed),
  `test_reports_unique_solution*` / `test_fails_fast_on_second_solution*` (6 passed),
  `tests/test_timeout.py::TestGenerate_50x50_RespectsTimeoutBound` (16 passed in that file).
  No solver file was edited, so "unchanged" is literal.
- **G-6** — `tests/bench_generate.py`: 2 passed, 1 xfail, the same pre-existing AC-037 xfail
  with the same CARD-018 reason and the same over-cap count (2 of 2 sampled) as at the branch
  point. No timeout or perf test turned red. Since no tracked file changed, there is no
  instrumentation to cost anything: per-propagation-step work is unmoved by construction.

[Scope] Predicted Touches matched exactly for difficulty.py and tests/test_difficulty.py; solver/__init__.py and solver/search.py listed as predicted but untouched (no solver change needed — confirmed by empty diff on both files).
[Build gate] PASSED (full, independently re-run by orchestrator: 658 passed, 1 xfailed, exit 0, no regressions vs the pre-CARD-009 baseline of 636 passed + 1 xfailed).
[Review 1/3] Score: 9.2 — crit: 0, imp: 1. G-4 verified in the strongest available sense: solver/** byte-identical to main (not just tests passing), all 4 named tests (31/2/16/6) identical counts to CARD-004/006's baseline on both branches. AC-023's ceiling arithmetic independently re-derived from the actual shipped constants by the reviewer: effort<=0.15, relief in [0.70,1.0], score<=15.0<33 (ADR-0005's Easy cutoff) — confirmed by a numeric sweep including a 1e9-second solve time, still exactly 15.0. Mutation-verified: 7/8 injected bugs killed (the survivor is a defensive clamp unreachable with the shipped weight table); the exact ADR-0013 failure mode (size/density as additive terms) is caught by 4 tests. ADR-0007 layering verified non-vacuous (fabricated difficulty->solver edge rejected by the real guard). Monotonicity verified for all 3 effort signals; density's deliberate non-monotonicity (peaks at 0.5) verified symmetric. Important finding: (I-1) ADR-0013's own Decision text was internally self-contradictory — literally asserts both "all five signals combined via a fixed-weight sum" AND "size/density are normalizers, not additive terms," and only this card's Worktree notes recorded which reading is actually load-bearing (the normalizer one — proven necessary since a literal 5-term sum makes AC-023 impossible for a large/dense grid). Resolved by revising ADR-0013 directly (no new DEC needed — a clarification of self-contradictory prose to match the only implementable reading, not a new decision with alternatives to weigh): the Decision section now states the effort/relief split explicitly. 4 Minor findings, none gating: (M-1) __all__ omits 2 documented tuning constants; (M-2) SignalWeights under-validates effort-weight non-negativity, so an injected weights= table could in principle break AC-023 at a call site (shipped table is fine, guarded by its own test); (M-3) the final score clamp is the one untested/unreachable line with the shipped table; (M-4/M-5/M-6/M-7) test-comment precision nits. Final verdict: PASS — ready to merge.
