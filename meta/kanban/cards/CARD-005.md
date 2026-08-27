# CARD-005: Pipeline orchestrator and regenerate-on-failure loop

**Status:** ready
**Priority:** P1
**Category:** feature
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/005-orchestrator-regenerate-loop
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-1
**Idea:** —
**Wave:** 4
**Depends on:** CARD-003, CARD-004
**Touches:** src/nonogram/orchestrator.py, tests/test_orchestrator.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

COMP-002 (Pipeline Orchestrator) — the thin layer that owns the `Puzzle` aggregate
(AGG-001) and is the **single enforcement point** for its invariants (ADR-0007). Every
later card that adds a loop (difficulty resample CARD-010, pixel nudge CARD-016) extends
this module, so the shape laid down here is the shape they copy.

1. **The `Puzzle` aggregate.** One instance per generation request, carrying mode, size,
   density, grid, clues, uniqueness verdict, retry counters, and the `ready_for_export`
   flag. It is **not** re-created per retry — that is exactly why INV-003's retry counter is
   one invariant on one aggregate (see aggregates.yml AGG-001).
2. **The generation pipeline.** `source grid (CARD-003) → compute clues (CARD-002) →
   solve for uniqueness (CARD-004) → mark ready`. Inject the seeded `random.Random`
   (ADR-0015) built from the `--seed` flag so the whole pipeline is reproducible.
3. **POL-001 AutoRegenerateOnUniquenessFailure (FR-007).** When the uniqueness check
   reports `solution_count != 1` in random/library mode, discard the candidate and generate
   a new one automatically — no user interaction.
4. **POL-005 AbandonAfterMaxRetries + INV-003 (NFR-002).** The loop is bounded at
   **20 attempts** (ADR-0002). At the bound, abandon with a clear `GenerationAbandoned`
   error rather than retrying again. Implement the bound as one shared, counted loop
   primitive: CARD-010's resample and CARD-016's nudge both reuse it, and INV-003 must have
   exactly one home.
5. **INV-002 export gate.** `ready_for_export` is set only after the uniqueness check
   confirms exactly one solution. The gate lives here, not in COMP-007 (ADR-0007's
   single-enforcement-point rule; trace.yml FR-011/FR-016 notes) — export cards call it.

## Acceptance criteria

- **AC-018** (happy, POL-001) — given a freshly generated random or library grid whose
  uniqueness check reports `solution_count != 1`, when the auto-regenerate policy evaluates,
  then a new candidate grid is generated automatically without user interaction and
  re-checked.
  *test:* `TestRegenerate_FiresOnUniquenessFailure`
- **AC-019** (boundary, INV-003, POL-005) — given a candidate that has already been
  regenerated up to the configured maximum retry bound, when another uniqueness failure
  occurs, then generation is abandoned and a clear error is reported instead of retrying
  again.
  *test:* `TestRegenerate_StopsAtMaxRetryBound`
- **AC-039** (boundary, INV-003) — given a generation request whose candidates never pass
  the uniqueness or difficulty check, when the retry loop runs, then it stops after at most
  the configured maximum retry count (20 regenerate/resample attempts, 5 pixel-nudge
  attempts — ADR-0002) and reports a clear failure instead of looping indefinitely.
  *test:* `TestRetryLoop_BoundedIterations`

## Guardrails

- G-1: Do not edit `src/nonogram/solver/**`, `src/nonogram/clues.py`,
  `src/nonogram/sourcing/**` — CARD-002/003/004's deliverables. The orchestrator composes
  them; if one of them needs a change to be composable, that is an escalation, not an edit
- G-2: INV-003 has exactly one home — this module (trace.yml NFR-002 note). Do not scatter
  retry counting into the sourcing or solver modules
- G-3: The uniqueness verdict is the solver's; the orchestrator must not re-derive,
  second-guess or short-circuit it (CON-005 is mandatory and is verified in CARD-004)
- G-4: No persistence — the `Puzzle` aggregate lives only for the duration of one process
  and the export file is the sole durable artifact (CON-003)
- G-5: Out of scope — no difficulty scoring or resample loop (FR-008/009/010, Increment 2),
  no pixel-nudge loop (FR-013, Increment 3), no export renderers (CARD-007 onward), no
  timeout enforcement (ADR-0011, CARD-006)

## System contract

- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions (check: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (check: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (check: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF)
- INV-003 — A puzzle's automatic-retry counter (regenerate, resample, pixel-nudge) never exceeds its configured maximum bound (check: TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestNudge_ReportsFailureAtCap, TestRetryLoop_BoundedIterations)

## Architecture context

- **FR:** FR-007
- **NFR:** NFR-002
- **INV:** INV-002, INV-003
- **POL:** POL-001, POL-005
- **ADR:** ADR-0002, ADR-0007, ADR-0015
- **Components:** COMP-002 (Pipeline Orchestrator), COMP-003, COMP-005 (consumed)
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—
