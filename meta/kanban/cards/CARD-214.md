# CARD-214: Single-puzzle generation can reveal given cells to make a non-unique picture uniquely solvable

**Status:** done
**Priority:** P1
**Category:** feature
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/214-given-cells
**Worktree:** —
**Source:** owner's Google Doc "Nonograms - Print layout", 2026-10-13 ("## Puzzle generator — This one has a flaw: for now it's more likely to get a «there's no unique solution» then the real picture. So I propose to include black\\white cells in the puzzle grid to make it uniquely solvable"; "## Infrastructure — add to generator an option: generate with some answer provided if it fails to generate unique solutions (I think we'll apply it to single puzzle generation, not batch) as POC"); owner decision 2026-10-13 via AskUserQuestion — "Cut them now as POC cards"
**Idea:** —
**Wave:** 38
**Depends on:** —
**Touches:** src/nonogram/solver/search.py, src/nonogram/solver/propagate.py, src/nonogram/orchestrator.py, src/nonogram/errors.py, tests/property/test_solver_uniqueness.py, tests/helpers/brute_force_oracle.py, tests/test_solver.py, tests/test_given_cells.py, tests/property/test_given_cells.py
**Review score:** 8.1/10 (cycle 1/3; fix cycle 1 closed F-1 and four minors) — AC/EC gate passed, awaiting merge gate
**Started:** 2026-10-13T10:16:42Z
**Closed:** 2026-10-14T05:31:05Z
**Actual:** 2.4d
**Merge commit:** d49e73a
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

- [Notes recovered 2026-10-14] pulled one-way from the worktree copy after a
  `git reset --hard` in the main repo discarded this card's uncommitted
  bookkeeping (see the incident note below). Agent-authored content, verbatim:

  ### What was built

  A third recovery option that keeps the picture intact, in four pieces:

  1. **A seeded count (COMP-005).** `solve(row_clues, column_clues, *, givens=None,
     deadline=None)`. `givens` is a grid-shaped partial assignment seeded into the
     board with `Board.assign` *before* the first propagation round — the same
     operation a branch uses — so every ADR-0029 rung, the search, and the
     CON-005 re-encode backstop read a given exactly as they read a deduction,
     and there is no third cell state anywhere. With `givens=None` the board is
     the blank one it always was: the default path builds nothing extra, pays no
     cell walk, and reads no clock it did not read before (G-3).
  2. **A pure chooser (COMP-005).** `choose_givens(grid, row_clues, column_clues,
     *, cap, deadline=None)`: solve, and while the count is `MANY`, reveal the
     first cell by `(row, column)` on which the two witnesses disagree — to the
     value the *grid* holds — and solve again. Returns a value; mutates nothing.
     Two things are proved rather than hoped: it always advances (a disagreement
     cell is undecided in the solve that reported it, EC-011, so each round
     reveals a *new* cell) and it never advances into a contradiction (the two
     witnesses differ at that cell, so one of them survives whichever value is
     revealed — which is why a 0 count can only mean the clues have no solution
     at all, i.e. they are not this grid's encoding).
  3. **The error (shared layer).** `errors.GivenCellsCapExceeded(GenerationAbandoned)`.
  4. **The policy (COMP-002).** `GenerationRequest.reveal_given_cells` (off by
     default), `MAX_GIVEN_CELL_SHARE_PERCENT = 5`, `given_cells_cap(grid)`,
     `Puzzle.givens`, and `generate`'s `accept_by_revealing()` — tried **only**
     after the mode's own recovery has exhausted its own bound (all 30
     redraws/repairs, or all 5 nudges), on the run's **first** sourced candidate,
     and accepted only through the same `judge_candidate` with the givens passed
     to the one `solver.solve` call the module has.

  Two further behaviours fell out of the design and are deliberate, not
  oversights:

  - **A missed difficulty tier is not rescued**, by either of the two routes into
    one. Revealing is a *uniqueness* remedy, exactly as POL-002's nudge is ("a
    conversion that is unique but misses the requested tier is not nudged"), and
    it can only make a puzzle grade *easier*. (a) A run abandoned because its
    candidate was unique but out of tier has nothing to reveal, so the chooser
    returns nothing and `accept_by_revealing` returns `None`; in image mode that
    refusal is raised outside the `try` that calls the policy, so the policy is
    not even entered. (b) A candidate that *was* revealed is returned only if it
    lands in the requested tier — `accept_by_revealing`'s last line — which is
    the load-bearing half in random/library mode, where the outer handler
    re-checks nothing. Without (b) the flag would silently widen what
    `--difficulty` means. Tests:
    `test_the_reveal_policy_does_not_rescue_a_missed_difficulty_tier` (route b,
    random mode — added in fix cycle 1, review F-1) and
    `test_an_already_unique_tier_miss_never_reaches_the_reveal_policy` (route a;
    this is the test that carried the first name until fix cycle 1 renamed it,
    because it never reached the policy).
  - **Batch generation cannot reach it** (the owner's "not batch"): nothing sets
    the flag, and `generate_batch` builds its own `GenerationRequest` without it.
    If a later card ever did set it, a cap refusal would be skipped as a bad draw
    like any other `GenerationAbandoned`, which is coherent — but it is not
    enabled here.

  ### Structural decisions (copy these, CARD-215 / CARD-216)

  - `STRUCTURE: the givens boundary type is list[list[bool | None]] (aliased solver.Givens), grid-shaped, True = filled / False = empty / None = unknown — because it is a plain builtin structure that needs no import to produce or to consume. That is what lets CARD-215 (export/) and CARD-216 (db/, templates) read a puzzle's givens WITHOUT importing solver/, which ADR-0007 forbids as a lateral import. A list of (row, column, value) triples or a value object would have forced either that illegal import or a second representation; the solver already proved the rule (propagate.mask_runs reimplements a clue check rather than importing clues.py), and CARD-215 should reimplement the three-line row-major enumeration natively rather than import solver.revealed_cells.`
  - `STRUCTURE: choose_givens lives in solver/search.py (COMP-005), not beside repair_candidate in the orchestrator — it loops over solve, reads the witnesses and the undecided mask, and answers a question about a clue set ("which revealed cells make this unique?"), which is COMP-005's subject. Keeping it there also preserves the orchestrator's "exactly one solver.solve call site" property (CARD-016 G-4): the seeded re-verify goes through the same judge_candidate as every other candidate. The POLICY — when to reveal, the cap, the opt-in flag, the mode interaction, the re-verify — stays in the orchestrator, which is ADR-0007's split: capability modules reason, the orchestrator composes.`
  - `STRUCTURE: the cap NUMBER lives in the orchestrator (MAX_GIVEN_CELL_SHARE_PERCENT = 5, beside MAX_NUDGE_ATTEMPTS) and is passed into choose_givens as a REQUIRED keyword with no default — the mechanism takes a bound and never carries a policy default, so the number is stated in exactly one place and a test can reach the refusal without a 900-cell corpus. Same posture as MAX_NUDGE_ATTEMPTS: deliberately not a fraction or alias of MAX_RETRY_ATTEMPTS.`
  - `STRUCTURE: the new error is errors.GivenCellsCapExceeded(GenerationAbandoned), not a direct NonogramError sibling — exit_code_for's MRO walk then maps it to GENERATION_FAILED with no new row in cli.py's table (the SizeTooSmallForSource precedent, and cli.py is untouched by this card), and it IS what GenerationAbandoned's docstring describes: a bounded recovery loop that hit its cap.`
  - `STRUCTURE: the reveal policy acts on the run's FIRST sourced candidate — the image-mode conversion, or the first random/library draw — captured once in generate, never on the last-judged grid, because the last-judged grid is a repaired or five-pixel-nudged derivative and AC-3 requires the accepted grid be cell-for-cell the candidate's.`
  - `STRUCTURE: a puzzle's givens ride on the aggregate as Puzzle.givens (the same plain boundary type), written only by judge_candidate and cleared by record_candidate with the rest of the per-candidate verdict facts — the single-writer shape solution_count / undecided_mask / witnesses already have. CARD-216 persists THIS field; CARD-215 renders it.`
  - `STRUCTURE: the seeded re-verify goes through judge_candidate's `givens` keyword rather than through a second solver.solve call, so COMP-002 still contains exactly ONE solve call site (CARD-016 G-4, docs/GENERATION_ALGORITHM.md §8) and a revealed puzzle is judged by the identical path as a fresh draw, a repair and a nudge — ADR-0024/R1's rule applied to a new remedy.`
  - `STRUCTURE: a puzzle accepted with givens is GRADED off that seeded solve's signals (the same record_difficulty call every other candidate gets), not off an unseeded re-solve — ADR-0029/R2 allows one derivation from the one verifying solve, and the seeded solve is the one that verified it. The consequence is honest rather than hidden: line_logic_cells counts the given cells (they ARE known at the first fixed point) and a given cell carries no rung tag (no rung deduced it), so a revealed puzzle grades easier — which is what it is, since the solver meets it with those cells already filled. No difficulty.py change, and no grade on record moves: every pre-CARD-214 grade came from an unseeded solve.`

  ### Per-AC evidence

  | AC | Card's test name | Where it lives (pytest name) |
  |---|---|---|
  | AC-1 | `TestGivenCells_MakeThePuzzleUnique` | `tests/test_given_cells.py::test_given_cells_make_the_puzzle_unique` (+ `_without_touching_the_grid`, `_reveal_the_first_ambiguous_cell_by_row_then_column`), widened to the whole corpus by `tests/property/test_given_cells.py::test_given_cells_always_make_the_puzzle_unique` |
  | AC-2 | `TestGivenCells_UniqueGridNeedsNone` | `tests/test_given_cells.py::test_given_cells_unique_grid_needs_none` (+ `_even_with_a_cap_of_zero`) |
  | AC-3 | `TestGenerate_RevealPolicyNeverChangesTheGrid` | `tests/test_given_cells.py::test_generate_reveal_policy_never_changes_the_grid` — asserts the accepted grid is **equal** to the conversion, that the verdict is 1 and the export gate open, that all 5 nudges ran first, and that the unseeded solve of the same grid is still `MANY` (so the uniqueness really does come from the givens). Companions: `_does_not_fire_while_the_nudge_can_still_help`, `_keeps_the_random_mode_retry_bound` |
  | AC-4 | `TestGivenCells_RefusesBeyondTheCap` | `tests/test_given_cells.py::test_given_cells_refuses_beyond_the_cap`, `_through_generate`, `test_the_cap_refusal_is_grouped_with_the_other_no_puzzle_failures` (the CLI exit-code half), `test_the_cap_is_five_percent_of_the_grid_over_the_whole_size_range` |
  | AC-5 | `PropertyTest_Recovery_AcceptedGridsHaveRealVerdictsWithinOneBound`, `TestRecovery_RepairKeepsFilledCountExact` | both pre-existing and still green, unmodified (`tests/property/test_recovery_bound.py`, `tests/test_orchestrator.py`). Added at this card's own boundary: `tests/test_solver.py::test_an_empty_givens_is_the_default_question_field_for_field` and `::test_the_seeded_parameter_is_keyword_only_and_defaults_to_none`, plus `tests/test_given_cells.py::test_generate_without_the_flag_still_abandons_the_same_picture` and the per-case G-3 check inside `test_uniqueness_holds_under_givens` |
  | AC-6 | `PropertyTest_SolverUniqueness_HoldsUnderGivens` | `tests/property/test_solver_uniqueness.py::test_uniqueness_holds_under_givens` — **1500** `(clues, givens)` pairs (floor of 500 asserted in the test), cross-checked against the independent oracle. Corpus floors are asserted too, including floors taken from the *oracle's* answers (>= 100 truly-0 and >= 50 truly-ambiguous pairs), so the corpus cannot drift into asserting only the easy half |
  | AC-7 | `PropertyTest_GivenCells_DeterministicForAGrid` | `tests/property/test_given_cells.py::test_given_cells_deterministic_for_a_grid` (300 grids, three calls each under three different global `random` states) and `::test_given_cells_deterministic_across_processes` (child interpreters under `PYTHONHASHSEED=0` and `=1` — the "in any process" half, and the one in-process repetition cannot make) |
  | AC-8 | `TestGivenCells_ContradictoryGivenCountsZero` | `tests/test_given_cells.py::test_given_cells_contradictory_given_counts_zero` (+ `_for_a_whole_wrong_grid`, which reaches the same verdict by the fully-given path where no search runs at all) |

  Mutation-checked, not just written (two injected bugs, both caught by
  `test_uniqueness_holds_under_givens`): seeding only the filled givens
  (`if value:` instead of `if value is not None:`) and ignoring `givens`
  altogether. With the in-solver backstop also disabled — to prove the *oracle*
  is what catches it rather than the solver's own self-check — the failure is
  `solver said 1, brute-force oracle said 0`, i.e. exactly the CON-005 false
  positive.

  ### Architecture delta this card requires and must NOT make

  Kanban cards only read `meta/architecture/`. Both of these belong at the
  architect station:

  - **ADR-0024 needs a new recovery-policy entry.** ADR-0024/R5 enumerates the
    three recovery routes by mode (POL-001 redraw / POL-002 nudge / POL-006
    repair) and this card adds a fourth, opt-in one that mutates nothing. The
    card's text calls it POL-007 — **that id is already taken**:
    `meta/architecture/domain/policies.yml` defines POL-007
    (`RederivePlanMatrixOnSplitChange`, added 2026-09-22 for FR-034/BK-UI-2).
    The reveal policy therefore needs the next free id, **POL-008**, when the ADR
    is amended; the code's docstrings say "the reveal policy (POL-007 on the
    card, id to be confirmed — POL-007 is taken by FR-034)" rather than minting
    an id this card has no mandate to mint.
  - **What CARD-215 and CARD-216 need from here.**
    - The boundary type is `list[list[bool | None]]`, grid-shaped, row-major,
      `True` = filled, `False` = empty, `None` = not revealed. It is on the
      aggregate as `Puzzle.givens`, and `None` (not an all-`None` grid) is what
      a puzzle with no givens carries.
    - **Do not import `nonogram.solver` to read it.** `export/` and the admin
      layer are capability/adapter modules on the wrong side of ADR-0007 for
      that, and `tests/test_cli.py`'s `ast` guard fails the suite on it.
      `solver.revealed_cells(givens)` is three lines — reimplement it natively,
      the way `solver/propagate.py`'s `mask_runs` reimplements a clue check.
    - A revealed puzzle's `solution_count` is 1 **given its givens**: its clues
      on their own are ambiguous. Anything that re-solves a stored puzzle to
      re-check it (the admin's `puzzle_review.audit_uniqueness`, the player's
      JS solver, a regrade) must pass the givens or it will correctly report
      `MANY` and look like a defect. That is the INV-002 clause below, and it is
      the single most likely way to get CARD-216 wrong.
    - Nothing persists the field yet, so no migration exists and no export schema
      moved (ADR-0023 untouched).

  - **INV-002 needs its "given its given cells" clause.** `domain/aggregates.yml`
    INV-002 reads "a puzzle is only marked ready for export after its uniqueness
    check has confirmed exactly one solution". That stays true here — the gate is
    still `confirm_uniqueness` and still the solver's number — but for a puzzle
    with givens the confirmed statement is "exactly one solution *given its given
    cells*", which is what CARD-215's rendering and CARD-216's player have to
    honour. Also worth recording there: INV-001 is untouched, since givens reveal
    cells and never alter the grid or its clues.

  ### Resume after a rate-limit interruption (2026-10-13)

  The first implementation run was terminated by an API rate limit *after* the
  code was finished and the suite had gone green, and before anything was
  committed. Nothing above was changed on resume: the whole diff was re-read
  against AC-1..AC-8, both EC entries and G-1..G-7, and no defect was found that
  warranted touching sound work. What the resume added is the evidence below, the
  two SCOPE+ declarations, and the commit itself.

  **Why the first run could not read its own counts** — worth recording, because
  it cost a whole run and will cost the next one too. `pyproject.toml` sets
  `addopts = "-q"`, so a command line that *also* passes `-q` makes `-qq`, and at
  `-qq` pytest prints the progress dots and **no summary line at all**. The suite
  was green (exit 0) and simply never reported its totals. Run the full suite
  without `-q` on the command line:
  `python -m pytest -p no:warnings -rf` — the ini's own `-q` is what gives the
  one-line summary.

  ### SCOPE+ — two files outside this card's declared `Touches:`

  - `SCOPE+ tests/test_cli.py` — **required, not optional**: line 666's
    `test_every_domain_error_has_an_exit_code` asserts
    `declared == {error for error, _ in ERROR_EXIT_CODES}` over every
    `NonogramError` subclass in `errors.py`, so adding `GivenCellsCapExceeded`
    without a row there *fails the suite*. The row is also AC-4's CLI half as a
    parametrised case (the MRO walk finding `GENERATION_FAILED` through
    `GenerationAbandoned`). **`src/nonogram/cli.py` itself is untouched** — no new
    row in `cli._EXIT_CODES`, which is the whole point of subclassing.
  - `SCOPE+ docs/GENERATION_ALGORITHM.md` — this doc's contract is that it
    describes the generation pipeline *as the code implements it*, so a fourth
    recovery route absent from it is stale documentation rather than an optional
    extra. §8.5 added (the reveal policy and the seeded count); the previous §8.5
    "What is never retried" renumbered §8.6 with its content unchanged; one
    change-log row appended. No other section edited.

  Nothing under `meta/` is committed by this branch. The branch predates main's
  card commits, so `git diff --stat main -- meta/` shows ~3955 deletions across
  `meta/kanban/` and `meta/review/` purely from being behind; those are the
  orchestrator's files and were neither staged nor "restored".

  ### Verification on resume — what was re-checked directly, and how

  - **AC-6 / EC(CON-005), the oracle's independence** (the highest-stakes claim).
    Read off `tests/helpers/brute_force_oracle.py` with `ast`: its only imports
    are `__future__`, `collections.abc.Iterator`, `itertools.product` and
    `nonogram.clues` — **no `nonogram.solver`**, so the cross-check is a genuine
    second opinion. Guarded twice over: the package-wide `ast` guard in
    `tests/test_cli.py` and the oracle-specific
    `tests/test_solver.py::test_the_oracle_shares_no_code_with_the_solver`, which
    asserts the *positive* too (clues still derived through COMP-004) so a
    rewrite that stopped using the oracle's own encoder would also be caught. The
    oracle learned givens as a filter over its own enumeration (row-candidate
    prune **plus** a whole-grid re-check), and its two independent counters are
    cross-checked under givens by
    `test_the_two_oracles_agree_under_givens` on both consistent and
    deliberately contradicted assignments.
  - **AC-7 / EC(ADR-0024/R4), determinism.** `choose_givens` reads no clock, no
    rng and no module state, and holds no set or dict on its choice path —
    `_first_disagreement_cell` walks the two witness grids in row-major order and
    returns the first mismatch. The "in any process" half is the one in-process
    repetition cannot make, and is covered by
    `test_given_cells_deterministic_across_processes` (child interpreters under
    `PYTHONHASHSEED=0` and `=1`, compared against this process's answer).
  - **AC-5 / G-3.** The three tests AC-5 names are **unmodified** — `git status`
    shows no change to `tests/test_orchestrator.py` or
    `tests/property/test_recovery_bound.py` — so the repair-lineage replay
    (`test_the_same_seed_replays_the_same_repair_lineage`, AC-C), the exact
    filled count (`test_repair_keeps_the_filled_count_exact`, AC-114) and
    `test_accepted_grids_have_real_verdicts_within_one_bound` all judge the new
    code with their old assertions. The "`deadline=None` still reads no clock"
    half is `tests/test_timeout.py::test_a_deadline_never_reads_the_clock_when_it_is_none`,
    also unmodified; the seeded path adds no clock read, since
    `_check_givens_shape` returns immediately for `None` and every other new
    block is behind `if givens is not None`.
  - **AC-8, and `solve`'s two pre-board early exits** — audited specifically,
    because an early exit that returned before `Board.blank` would ignore
    `givens` and could report 1 for a contradicted cell. Both are sound: the
    filled-count mismatch exit returns 0, which is 0 under any assignment; and
    the `total_cells == 0` exit returns 1 for a grid whose only valid `givens` is
    shaped `[[], [], ...]` and therefore reveals nothing. `_check_givens_shape`
    runs *before* both, so a malformed assignment is always the promised
    `ValueError` rather than whatever the clues alone would have returned.
  - **Scope containment.** `reveal_given_cells` appears in exactly one file
    (`src/nonogram/orchestrator.py`) and `givens` in three
    (`orchestrator.py`, `solver/search.py`, `solver/__init__.py`). No `export/`,
    no `admin/`, no template, no JS, no DB column, no migration, no
    `pyproject.toml` change — CARD-215 and CARD-216 are untouched (G-6, G-7).
    Neither `cli.py` nor `generate_batch` sets the flag, so the policy is
    reachable only by a caller that constructs a `GenerationRequest` directly
    (single-puzzle only, the owner's call).
  - **POL id, re-confirmed against main.** `meta/architecture/domain/policies.yml`
    defines POL-001..POL-007 with POL-007 taken by `RederivePlanMatrixOnSplitChange`
    (FR-034), so POL-007 is the *last* used id and **POL-008** is the next free
    one for the reveal policy when the architect station amends ADR-0024. No id
    is minted in code or in `meta/architecture/` by this card.

  ### For CARD-215 / CARD-216 — the givens boundary, in one place

  Repeating only what the next two cards must not get wrong (the reasoning is in
  "Structural decisions" above):

  - `Puzzle.givens: list[list[bool | None]] | None` — grid-shaped, row-major,
    `True` = filled, `False` = empty, `None` = not revealed. A puzzle with no
    givens carries `None`, **not** an all-`None` grid, so `if puzzle.givens` is a
    safe emptiness test and `revealed_cells(None) == ()`.
  - **Do not `import nonogram.solver` to read it.** `export/` and the admin layer
    are on the wrong side of ADR-0007, and `tests/test_cli.py`'s `ast` guard
    fails the suite on it. Reimplement the row-major enumeration natively (three
    lines), the way `solver/propagate.py`'s `mask_runs` reimplements a clue check.
  - A revealed puzzle's `solution_count` is 1 **given its givens**; its clues
    alone are ambiguous. Anything that re-solves a stored puzzle —
    `puzzle_review.audit_uniqueness`, the player's JS solver, a regrade — must
    pass the givens or it will correctly report `MANY` and look like a defect.
    This is the single most likely way to get CARD-216 wrong.

  ### Full-suite result (the run the first attempt never got to print)

  ```
  /Users/omelnikova/PycharmProjects/PythonProject4/.venv/bin/python -m pytest -p no:warnings -rf
  6881 passed, 9 skipped in 979.77s (0:16:19)       EXIT=0
  ```

  Zero failures, zero errors; the 9 skips are the pre-existing DB-mode skips (no
  `nonogram_test` database on this machine) and are the same 9 main has.

  **Every test in the delta accounted for.** `git diff main HEAD -- src/ tests/
  docs/` is **empty**, so the branch's code baseline is identical to main's and
  the difference is exactly this card's working tree. Collected totals:
  **main 6859 → this branch 6890, +31**, which breaks down as

  | + | Where | Why |
  |---|---|---|
  | 23 | `tests/test_given_cells.py` (20) and `tests/property/test_given_cells.py` (3) | the card's new files |
  | 4 | `tests/test_solver.py` | signature/G-3 guard, the two-oracle agreement under givens, the oracle-independence `ast` guard |
  | 1 | `tests/property/test_solver_uniqueness.py` | `test_uniqueness_holds_under_givens` (AC-6) |
  | 1 | `tests/test_cli.py` | the `GivenCellsCapExceeded` row in `ERROR_EXIT_CODES`, one parametrised case |
  | 2 | `tests/test_web_submission.py` | **no edit to that file** — `test_every_error_class_surfaces_as_a_structured_failure` parametrises over every `NonogramError` subclass it discovers, so the new error picked up its `[GivenCellsCapExceeded-from-generate]` and `[-from-export]` cases automatically, and both pass. Worth knowing: the web layer's structured-failure contract already covers this error with no work, which is a second reason to keep it a `GenerationAbandoned` subclass rather than a new top-level error. |

  One number in the dispatch brief did not reconcile and is recorded rather than
  smoothed over: the brief states main's baseline as **6857 passed / 9 skipped**
  (6866 collected), but main's checkout collects **6859** today (6850 passed /
  9 skipped) with no code difference from this branch's base. The brief's figure
  appears to predate something; it does not affect this card's verdict, since the
  branch has **0 failures** and all 31 added tests are attributed above.

  ### [Fix 1] — review cycle 1 closed (score 8.1: 0 critical, 1 Important, 4 Minor)

  No behaviour changed in this cycle. One missing test, one renamed test, one
  corpus widened, three pieces of prose corrected, and one structural guard that
  replaces a rationale which was simply not true. `git diff` touches
  `tests/test_given_cells.py`, `tests/property/test_given_cells.py`,
  `tests/property/test_solver_uniqueness.py`,
  `src/nonogram/solver/search.py` (docstring only) and
  `docs/GENERATION_ALGORITHM.md` (the declared SCOPE+ doc). `orchestrator.py`,
  `errors.py`, `cli.py`, the oracle and every pre-existing recovery test are
  untouched, so G-1..G-7 and AC-5 are where cycle 1 left them.

  **F-1 (Important) — the requested-tier gate now has a test, on the branch
  where it is load-bearing.** The reviewer was right on both halves, and both
  were reproduced here before anything was written.

  - Added `test_the_reveal_policy_does_not_rescue_a_missed_difficulty_tier` as a
    **random-mode** case: the scripted `_SIX_SWITCHES` source, `difficulty="hard"`,
    the flag on. All 30 regenerate attempts and their repairs are spent, the
    reveal policy then makes the first draw unique with six givens — and the
    revealed puzzle grades **easy** (measured: score 31.6, tier easy, 0 branch
    nodes), so the gate is the one thing that refuses it. The test asserts the
    run still raises a plain `GenerationAbandoned` (not `GivenCellsCapExceeded`)
    naming the Hard band, and — so a reader can tell it apart from the
    already-unique case — that the aggregate really went through the policy: six
    revealed cells, `solution_count == 1`, the grid still cell-for-cell
    `_SIX_SWITCHES`, and `difficulty_in_requested_tier is False`.
  - **Teeth, as asked.** Mutating `return accepted if
    accepted.difficulty_in_requested_tier else None` (the gate) to
    `return accepted`: `1 failed, 20 passed` — the new test, with
    `DID NOT RAISE GenerationAbandoned`. Gate restored: `21 passed`. The
    reviewer's probe was re-run too — `raise AssertionError` as
    `accept_by_revealing`'s first statement now fails **five** tests instead of
    four, the fifth being the new one, and the renamed test below is still not
    among them (it genuinely does not enter the policy).
  - **The old test was renamed, not re-pointed**, to
    `test_an_already_unique_tier_miss_never_reaches_the_reveal_policy`, with the
    rename and its reason recorded in its docstring. Re-pointing it would have
    deleted a real case: an already-unique tier miss in image mode is refused at
    a *different* site (the tier check outside the inner `try`), and that route
    deserves its own test rather than being folded into the gate's. It now also
    asserts what makes it that route — `givens is None`, `solution_count == 1`,
    `nudge.attempts == 0`. The card's "a missed difficulty tier is not rescued"
    note above was rewritten to state both routes and both test names; §8.5 of
    `docs/GENERATION_ALGORITHM.md` likewise.

  **F-2 (Minor) — the PYTHONHASHSEED rationale was wrong and is now a real
  guard.** Confirmed the reviewer's measurement under this venv before changing
  anything: the same 8-element `set[tuple[int, int]]` iterates byte-identically
  under `PYTHONHASHSEED` 0, 1, 2 and 42, while a 5-element set of `str` reorders
  under each — `int` hashes to itself, and CPython randomises `str`/`bytes`/
  `datetime` only. So:

  - the module docstring, `_in_child`'s docstring and the cross-process test's
    docstring now claim only what the subprocess proves — a **fresh
    interpreter**: no inherited module state, no warmed cache, a clean
    environment — and say explicitly that the two hash seeds are two fresh
    interpreters rather than two orderings, so the next reader does not trust a
    guard that is not there. The "collect the disagreeing cells, take one"
    example is gone.
  - the property that *does* hold got the structural check the reviewer
    suggested: `test_the_choosers_source_builds_no_set_or_dict` parses
    `solver/search.py` with `ast` and asserts that `choose_givens`,
    `revealed_cells` and `_first_disagreement_cell` build no set and no dict —
    by literal, by comprehension or by `set()`/`frozenset()`/`dict()` call —
    the same posture as `tests/test_cli.py`'s import guard. Deliberately scoped
    to the choice path and not to `solve`, which keeps a per-call memo.
    **Teeth:** inserting `_probe = {(0, 0)}` into `_first_disagreement_cell`
    fails it (`builds a Set on the choice path`); removed, it passes.

  **F-3 (Minor) — `solve`'s docstring no longer contradicts the orchestrator.**
  The sentence "the grades on record all come from unseeded solves" is replaced
  by the card's own version: both seeded signals *are* read by whatever grades
  the puzzle (ADR-0029/R2's one derivation from the one verifying solve, and for
  a revealed puzzle the seeded solve **is** that solve), so a revealed puzzle
  grades easier — which is what it is. The true, narrower statement is kept: every
  grade recorded before CARD-214 came from an unseeded solve and none of them
  moved. §8.5 gained the same fact as a bullet, since that doc describes the
  pipeline as the code implements it and the grade is what F-1's gate compares
  against.

  **F-4 (Minor) — the seeded corpus was widened, not re-explained. Measured
  first.** `GIVEN_SIZES` is now `(2, 3, 4, 5, 6, 7, 8)` — :data:`SIZES`'s own
  range minus 1x1, which stays dropped for its stated reason (no interesting
  partial assignment of one cell). Cost, measured on this machine:
  `test_uniqueness_holds_under_givens` **0.41s -> 0.93s**, the whole module
  **2.00s -> 2.53s**. That is the number in the comment now, and the comment
  cites the honest bound — the *oracle's* 8x8 ceiling — rather than the
  contradicted-given argument, which explained nothing. All the corpus floors
  still hold at the wider range, and the `GIVEN_SHARES` comment's measured
  figures were **re-measured** rather than left to rot: 122 of 1500 truly
  ambiguous under the weighting against 102 under a uniform draw, 432 at 0 and
  946 at 1 (was 94/55/450/956 at sizes 2..6). Nothing was mutated into the
  solver for this one: the reviewer's own 7x7/8x8 cross-check found 0 mismatches,
  and the point of the finding was that the committed guard did not assert it.

  **F-5 (Minor, optional) — taken, because it was cheap.** Added
  `_ScriptedSource`, which serves `grids[n]` while the script lasts and
  `grids[-1]` after (deliberately not cycling, so "the last grid this run drew"
  is one known grid), plus `_OTHER_SIX_SWITCHES` — the same switching-pair shape
  in different places, so it is exactly as repair-resistant and the run still
  exhausts its bound. `test_the_reveal_policy_keeps_the_random_mode_retry_bound`
  now draws `[_SIX_SWITCHES, _OTHER_SIX_SWITCHES]` (5 fresh draws in practice,
  the last being the second grid) and asserts the accepted grid is the **first**.
  **Teeth:** mutating `if pristine_candidate is None:` to `if True:` fails that
  test; restored, `21 passed`. `test_the_scripted_grids_are_what_the_ac_tests_assume`
  pins the new fixture's ambiguity against the real solver like the other two.

  **F-6 (info, out of scope) — only its in-scope half.** `admin/` is not this
  card's to touch, so the two call sites carry no new note; but the reviewer's
  alternative ("one line in §8.5") is in a file this card already owns, so §8.5
  now names `admin.regrade.grade_stored_grid` and
  `admin.puzzle_review.PuzzleReviewService.audit_uniqueness` as the two
  production re-solves of a stored grid that will need the givens once CARD-216
  persists them. By symbol, not by line anchor:
  `meta/ops/check_doc_references.py` resolves both (254 resolved, 1 failed — the
  one failure, `difficulty.py` at line 445, is pre-existing and untouched).

  **F-7 (info) — nothing to do.** The ADR-0024/INV-002 delta stays recorded on
  this card for the architect station; no POL-008 is minted in code, and
  `meta/architecture/` is untouched by this branch.

  **Full suite after the fix** (the ini's own `-q`, no `-q` on the command line):

  ```
  /Users/omelnikova/PycharmProjects/PythonProject4/.venv/bin/python -m pytest -p no:warnings -rf
  6883 passed, 9 skipped in 1016.04s (0:16:56)      EXIT=0
  ```

  **6881 -> 6883, +2, zero failures**, which is exactly the two tests added:
  `tests/test_given_cells.py` 20 -> 21 (the random-mode tier-gate case; the
  rename is net zero) and `tests/property/test_given_cells.py` 3 -> 4 (the
  no-set-or-dict guard). The 9 skips are the same pre-existing DB-mode skips. The
  run took 16:56 against the pre-fix 16:19 on this machine, with another card's
  suite running concurrently — F-4's widened corpus accounts for ~0.5s of that,
  measured above.

- [LEDGER RESTORED 2026-10-14] This card's records were destroyed by the
  `git reset --hard` in the main repo described on CARD-204 (it reverted every tracked
  file; this card's bookkeeping was uncommitted). Re-authored from the session's record
  and committed immediately; the agents' own notes were recovered from the worktree copy.
- [Implementation complete] committed `7402ecb` (12 files, +2198/-29, `meta/` clean) after
  the first agent was killed mid-run by the weekly rate limit and a second verified rather
  than trusted its work. Full suite 6881 passed, 9 skipped, 0 failed. Orchestrator-verified
  independently: the oracle at `tests/helpers/brute_force_oracle.py` imports only
  `__future__`, `collections.abc`, `itertools` and `nonogram.clues` — so the EC-001
  cross-check is genuinely independent of the solver under test.
  **Repo gotcha diagnosed here, worth keeping:** `pyproject.toml` sets `addopts = "-q"`,
  so a command line that also passes `-q` becomes `-qq` and pytest prints NO summary line.
  That is the only thing that stopped the first agent finishing — its suite was green and
  simply never printed its totals.
- [Review] cycle 1/3 — **score 8.1**, 0 Critical, 1 Important, 4 Minor. The central
  judgement (the seeded uniqueness verdict is sound) was earned by experiment, not
  inherited: the reviewer mutated the seeding to apply only the filled givens AND disabled
  the in-solver backstop, and the independent oracle caught it ("solver said 1,
  brute-force oracle said 0" on a contradicted 5x5) — the exact CON-005 false positive the
  mechanism exists to prevent. It also ran its own corpus at 7x7/8x8, sizes the committed
  one does not reach, with 0 mismatches. Mutation check: 7 mutants, 5 killed, 2 survived.
- [Severity gate] blocked on F-1: the reveal policy's requested-tier gate could be deleted
  with all 20 tests still passing, because the test named for that behaviour used an
  already-unique conversion and never entered the policy — it passed for a reason
  unrelated to its name.
- [Fix 1 complete] committed `fe2c945` (5 files, +265/-43); the only `src/` edit is one
  docstring paragraph. Full suite **6883 passed, 9 skipped, 0 failed**. F-1 closed with a
  random-mode test where the revealed puzzle grades easy against a `difficulty="hard"`
  request, so the tier gate is the only thing that can refuse it; teeth confirmed both
  ways. The mis-named test was **renamed, not re-pointed** — re-pointing would have
  deleted a real case (in image mode an already-unique tier miss is refused at a different
  site). It also declined to assert one thing and said why: `ready_for_export` is True on
  the refused aggregate, pre-existing behaviour shared with every random-mode tier miss.
- [AC/EC check] **All criteria/constraints ✓** — 8 ACs, both ECs, 7 guardrails and
  CON-005/INV-001/INV-002/INV-003 evidenced; 270 targeted tests green; 7 mutation probes
  run on a disposable copy, never the worktree. AC-6/EC(CON-005) rests on 1500 pairs with
  floors taken from the ORACLE's answers over a population `choose_givens` cannot produce
  (~25% contradicted, ~20% on mutated clues). AC-5 verified the strongest way available:
  the three tests it names are absent from the diff, so they judge new code with old
  assertions.
  **Correction the gate found in this card's own claim:** G-2 cites
  `tests/test_cli.py`'s inward-import guard as what keeps the oracle independent, but that
  guard walks `src/nonogram/**` only and never covered the oracle. The guarantee holds via
  the card's own new `test_the_oracle_shares_no_code_with_the_solver`; the mechanism named
  on the card was wrong.
- [Merge authorized] owner 2026-10-13: "merge both when the fixes land", gate not waived.
- [Merge gate] pending — runs after CARD-204's, never concurrently.

- [Merge gate] 2026-10-14 — **PASSED** on the merged tree: 6883 passed, 9 skipped,
  0 failed, `PYTEST_EXIT=0` (read in its own command, per the corrected practice).
- [Done] 2026-10-14 — merged as `d49e73a` (`--no-ff`). Worktree removed, branch
  `card/214-given-cells` deleted, review report synced to `meta/review/`.
  Actual 2.4d against a 1d estimate — the span includes a weekly-rate-limit kill
  mid-implementation and the resume that followed, so it measures calendar time, not
  effort.
  **Unblocked by this merge:** CARD-215 (render givens as a black cell / white dot)
  and CARD-216 (persist them, lock them in the player). CARD-216 additionally carries
  review F-6: `admin/puzzle_review.py` and `admin/regrade.py` re-solve stored grids
  without givens, which becomes a real defect the moment givens are persisted.
