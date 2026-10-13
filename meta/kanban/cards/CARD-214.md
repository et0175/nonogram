# CARD-214: Single-puzzle generation can reveal given cells to make a non-unique picture uniquely solvable

**Status:** in_progress
**Priority:** P1
**Category:** feature
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/214-given-cells
**Worktree:** ../PythonProject4-CARD-214
**Source:** owner's Google Doc "Nonograms - Print layout", 2026-10-13 ("## Puzzle generator — This one has a flaw: for now it's more likely to get a «there's no unique solution» then the real picture. So I propose to include black\\white cells in the puzzle grid to make it uniquely solvable"; "## Infrastructure — add to generator an option: generate with some answer provided if it fails to generate unique solutions (I think we'll apply it to single puzzle generation, not batch) as POC"); owner decision 2026-10-13 via AskUserQuestion — "Cut them now as POC cards"
**Idea:** —
**Wave:** 37
**Depends on:** —
**Touches:** src/nonogram/solver/search.py, src/nonogram/solver/propagate.py, src/nonogram/orchestrator.py, src/nonogram/errors.py, tests/property/test_solver_uniqueness.py, tests/helpers/brute_force_oracle.py, tests/test_solver.py, tests/test_given_cells.py, tests/property/test_given_cells.py
**Review score:** —
**Started:** 2026-10-13T10:16:42Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**Current behaviour (verified by reading the code).**

- `solver.solve(row_clues, column_clues, *, deadline=None)`
  (`solver/search.py:422`) counts a clue set's solutions, stopping at two. It
  takes **no** partial assignment: there is no way to ask "how many solutions
  are there *given* that these cells are known?". When the count is `MANY` it
  returns two witnesses, and `orchestrator._disagreement_mask`
  (`orchestrator.py:690`) already computes the cells those witnesses differ on.
- Recovery today **mutates the picture**: POL-006 repair flips one filled and
  one empty cell inside the witness-disagreement set, random mode only
  (ADR-0024/R3, R5); image mode nudges pixels (POL-002); library mode redraws
  (POL-001). Every attempt counts against the one retry bound (ADR-0024/R2,
  INV-003), and a repaired grid is re-verified by a fresh solve (ADR-0024/R1).
- So a picture that is not uniquely solvable is either changed until it is, or
  refused. The owner's complaint is exactly this: for a real picture the
  common outcome is a refusal.

**What changes — a third recovery option that keeps the picture intact.** When
single-puzzle generation asks for it, cells of the solution are **revealed** as
*givens* until the puzzle is uniquely solvable given them.

1. **Solver: a seeded count.** `solve` gains a keyword-only
   `givens: Givens | None = None` — a grid-shaped partial assignment
   (filled / empty / unknown per cell) seeded into the initial per-line
   bitmasks before the first propagation round. `solution_count` then means
   "solutions consistent with the clues **and** the givens". Default `None`
   keeps every existing caller and every recorded verdict byte-identical.
   Boundary type: `list[list[bool | None]]` (or an equivalent frozen value
   object) — the internal bitmasks never cross the module boundary, as today.
2. **A pure chooser.** `choose_givens(grid, row_clues, column_clues)` returns
   the set of revealed cells, as a value, computing nothing in place:
   - solve; if the count is already 1, return the empty set;
   - if it is `MANY`, take the witness-disagreement set, pick the **first cell
     by `(row, column)`** (deterministic — the same rule ADR-0024/R4 fixes for
     the repair pair, and for the same reason: a seed must replay), reveal it
     to the value the *solution grid* holds, and re-solve with the givens so
     far;
   - repeat until the count is 1, or until a stated cap is reached.
   No randomness, no host state, no clock.
3. **A cap, and a refusal.** Revealing cells always terminates (in the worst
   case the whole grid is given, and a fully-given puzzle has one solution),
   but a puzzle needing a quarter of its cells revealed is not a puzzle. Cap
   the reveal count (state the chosen cap and its rationale on the card's
   Worktree notes — a share of the grid, e.g. ≤ 5 %, plus the existing retry
   bound for the solves), and raise a new `NonogramError` subclass when the cap
   is reached, mapped to an exit code by `cli.py`'s `exit_code_for` MRO walk
   like every other domain error.
4. **Orchestrator policy, opt-in, single puzzle only.** `GenerationRequest`
   gains the flag (unvalidated at the boundary, like every other field);
   the orchestrator applies the reveal policy **only after** the mode's own
   existing recovery has failed within its bound — redraw (POL-001), pixel
   nudge (POL-002) and repair (POL-006) are untouched and keep their
   mode-exclusivity (ADR-0024/R5). The accepted puzzle carries its givens.
5. **Verification is not optional.** A puzzle accepted with givens is accepted
   only after a **fresh** seeded solve reports exactly 1 (the same rule
   ADR-0024/R1 makes for repairs — never infer uniqueness from the fact that
   cells were revealed).
6. **The uniqueness property extends, it does not bend.** CON-005/EC-001 says
   the solver must never report unique when there are 0 or ≥ 2 solutions.
   `tests/helpers/brute_force_oracle.py` must learn givens the same way — as an
   independent filter over its own enumeration — and must still not import
   `nonogram.solver`. The mandatory property test gains seeded cases.

**Architecture delta this card requires (flag, do not edit).** A reveal policy
is a new policy (POL-007) and a decision ADR-0024 does not cover: ADR-0024/R5
enumerates the three recovery routes by mode and this adds a fourth, opt-in
one. INV-002 ("ready for export only after the uniqueness check confirmed
exactly one solution") stays true but gains a clause — *given the puzzle's
given cells*. Both belong at the architect station; the card implements the
behaviour and records the needed delta in its Worktree notes (the same posture
CARD-198/202/206 took).

## Acceptance criteria

- **AC-1** (happy): *Given* a grid whose clues have several solutions, *when*
  `choose_givens` runs, *then* it returns a set of cells such that a fresh
  seeded solve reports exactly 1 solution, and every returned cell's value
  equals that grid's own. (test: `TestGivenCells_MakeThePuzzleUnique`)
- **AC-2** (happy, already unique): *Given* a grid that is already uniquely
  solvable, *when* `choose_givens` runs, *then* it returns the empty set and
  the puzzle is unchanged. (test: `TestGivenCells_UniqueGridNeedsNone`)
- **AC-3** (happy, picture preserved): *Given* image-mode generation with the
  flag set, *when* a candidate is not uniquely solvable and its nudge bound is
  exhausted, *then* the accepted puzzle's grid is **cell-for-cell the
  candidate's** and the uniqueness comes from the givens — no pixel of the
  picture is changed by this path. (test:
  `TestGenerate_RevealPolicyNeverChangesTheGrid`)
- **AC-4** (edge, cap): *Given* a grid that would need more than the cap,
  *when* generation runs with the flag, *then* it fails with the new
  `NonogramError` subclass naming the cap, and the CLI maps it to an exit code
  grouped with the other "no acceptable puzzle" failures. (test:
  `TestGivenCells_RefusesBeyondTheCap`)
- **AC-5** (guard, default off): *Given* any request without the flag, *when*
  it is generated, *then* the behaviour and the accepted puzzles are exactly
  what they were before this card — including the repair lineage a seed
  replays. (test: `PropertyTest_Recovery_AcceptedGridsHaveRealVerdictsWithinOneBound`,
  `TestRecovery_RepairKeepsFilledCountExact`)
- **AC-6** (property, EC-001 under givens): *Given* a seeded corpus of ≥ 500
  (grid, givens) pairs built with `random.Random` (the count asserted in the
  test), *when* each is solved seeded and independently enumerated by the
  brute-force oracle with the same givens applied, *then* the solver's verdict
  and the oracle's count agree on every case — in particular the solver never
  reports 1 where the oracle finds 0 or ≥ 2. (test:
  `PropertyTest_SolverUniqueness_HoldsUnderGivens` in
  `tests/property/test_solver_uniqueness.py`)
- **AC-7** (property, determinism): *Given* the same grid, *when*
  `choose_givens` runs any number of times in any process, *then* it returns
  the identical set in the identical order. (test:
  `PropertyTest_GivenCells_DeterministicForAGrid`)
- **AC-8** (edge, seeded count semantics): *Given* clues with exactly one
  solution and a given cell that **contradicts** it, *when* solved seeded,
  *then* the count is 0 — not 1, and not an exception. (test:
  `TestGivenCells_ContradictoryGivenCountsZero`)

## Guardrails

- G-1: The uniqueness check must never produce a false positive, with or
  without givens (CON-005/EC-001; test:
  `PropertyTest_Solver_NeverFalsePositiveUniqueness`).
- G-2: `tests/helpers/brute_force_oracle.py` must not import
  `nonogram.solver` — the cross-check stays independent (test:
  `test_every_import_in_the_package_points_inward` plus the oracle's own guard).
- G-3: `solve`'s existing signature and verdicts are unchanged for every
  caller that passes no givens; the solver stays pure (ADR-0007).
- G-4: POL-001 redraw, POL-002 nudge and POL-006 repair keep their current
  behaviour and mode-exclusivity (ADR-0024/R5); the retry bound is not raised
  (INV-003, ADR-0024/R2).
- G-5: Internal bitmasks never cross a module boundary (project convention);
  givens cross as `list[list[bool | None]]`.
- G-6: Out of scope — rendering givens (CARD-215), persisting them and showing
  them in the player (CARD-216), batch generation (owner: "not batch"), and any
  public generator surface.
- G-7: No new runtime dependency (ADR-0006/R1).

## System contract

- CON-005 — the uniqueness check must never produce a false positive (check:
  `PropertyTest_Solver_NeverFalsePositiveUniqueness`)
- INV-002 — a puzzle is ready for export only after its uniqueness check
  confirmed exactly one solution (check: review-lens — **this card adds the
  "given its given cells" clause; see the delta note**)
- INV-001 — clues always equal the run-length encoding of the solution grid
  (check: review-lens — unchanged: givens reveal cells, they never alter the
  grid or its clues)
- INV-003 — the retry counter never exceeds its configured bound (check:
  review-lens)
- ADR-0024/R1 — a repaired grid is accepted only after a fresh solver run
  reports exactly 1 (check:
  `PropertyTest_Recovery_AcceptedGridsHaveRealVerdictsWithinOneBound`)
- ADR-0024/R4 — the recovery's choice is a deterministic function of the grid
  and the witnesses, drawing nothing from the injected Random (check:
  review-lens)
- ADR-0024/R5 — repair fires for random mode only; library recovers by redraw
  and image by nudge (check: review-lens)
- ADR-0006/R1 — runtime dependencies are exactly stdlib + Pillow + NumPy
  (check: `TestDependencyBaseline_IsExactlyPillowAndNumpy`)

## Engineering constraints

- EC(CON-005): the seeded solve holds the no-false-positive property for every
  (clues, givens) pair, not only for the pairs this card's generation path
  produces. test: `PropertyTest_SolverUniqueness_HoldsUnderGivens`
- EC(ADR-0024/R4): the reveal choice is a pure, deterministic function of the
  grid and the solver's witnesses — same input, same givens, in any process.
  test: `PropertyTest_GivenCells_DeterministicForAGrid`

## Architecture context

- **FR:** FR-006 (uniqueness counting), FR-011 (ready for export), FR-024 (the
  undecided mask the witnesses come from), FR-023/FR-024 (image-mode recovery
  this policy follows).
- **ADR:** ADR-0024 (recovery policies — **needs a delta for POL-007**),
  ADR-0007 (dependency direction, purity), ADR-0011 (cooperative deadline — the
  seeded solve must honour it), ADR-0006/R1.
- **CON:** CON-005, CON-011.
- **Components:** COMP-005 (`solver/`), COMP-002 (`orchestrator.py`), and
  `errors.py` (one new subclass).
- **Trace:** `meta/architecture/trace.yml` — not updated by this card.

## Worktree notes

- [Env] forge 2026.8.17 (project declares no `forge.min_version`; no `.skills.yml` in this repo)
- [Dispatch] wave 37, started 2026-10-13T10:16:42Z — concurrency 2 (owner decision 2026-10-13), paired with CARD-204's resumed Fix 4

- [Touches drift] 2026-10-13T10:40Z — 8 files changed, 1 outside the declared
  `Touches:`: src/nonogram/solver/__init__.py (the package's `__all__` export of
  the new seeded-solve surface). Expected for a card that widens the solver's
  public API; recorded for Touches calibration.
- [Guard] 2026-10-13T10:40Z — runtime conflict guard: no file shared with
  CARD-204, the other active card of wave 37. No runtime conflict edge added.

- [Full-suite lock gap] 2026-10-13T10:50Z — two full suites are running
  concurrently on this host: CARD-204's worktree (`pytest -p no:warnings -rf`,
  its SECOND full run of this fix — scratchpad `full2.log`) and CARD-214's
  (`pytest -q -p no:warnings`). cmd-start-review's FULL-SUITE LOCK
  (`meta/kanban/.full-suite.lock`) is an orchestrator-side mechanism and the
  implementation agents do not take it themselves, so nothing serialized them.
  Not killed — both runs are 8+ minutes in and killing them wastes the time
  already spent. Consequence to weigh when the results land: wall-clock per run
  is inflated, and any UNEXPECTED failure in the admin/DB-touching tests should
  be re-run serialized before it is believed.
