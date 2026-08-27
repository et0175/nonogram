# CARD-010: Difficulty tier selection and resample loop

**Status:** ready
**Priority:** P1
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/010-difficulty-tier-resample
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-2
**Idea:** —
**Wave:** 7
**Depends on:** CARD-009, CARD-011
**Touches:** src/nonogram/orchestrator.py, src/nonogram/difficulty.py, src/nonogram/cli.py, tests/test_resample.py, tests/test_difficulty_tiers.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

Turns CARD-009's raw score into the user-facing Easy/Medium/Hard selector, and closes the
loop that makes a requested tier actually come out.

1. **Tier selector (FR-008).** `--difficulty {easy,medium,hard}` on the parser (parsing
   only), with the unsupported-tier rejection as a **domain** error inward of COMP-001
   (ADR-0010, same pattern as FR-001's size range). The requested tier is recorded on the
   `Puzzle` aggregate at creation, "pending score confirmation" (AC-020).
2. **Tier cutoffs (ADR-0005).** Map the 0..100 score to the three tiers at the ADR-0005
   cutoffs. Keep the cutoffs as named constants in `difficulty.py` next to the formula, not
   inlined in the orchestrator — Increment 2's checkpoint checks that generating at each
   tier produces a score in that tier's tertile band, and a single source for the bands is
   what makes that checkable.
3. **POL-004 ResampleOnDifficultyOutOfRange (FR-010).** In the orchestrator: score each
   candidate; if the score is outside the requested tier's range, resample a new candidate
   and **re-score it** before any further check (AC-026). Reuse CARD-005's shared bounded
   loop primitive — do not write a second counted loop.
4. **POL-005 / INV-003.** The resample loop shares the 20-attempt bound (ADR-0002). At the
   bound, abandon with a clear error (AC-027). INV-003 has exactly one home: COMP-002.

## Acceptance criteria

- **AC-020** (happy) — given a request specifying difficulty `"Medium"`, when generation
  runs, then the resulting puzzle is tagged with requested tier `"Medium"` pending score
  confirmation.
  *test:* `TestSelectDifficulty_AcceptsValidTier`
- **AC-021** (negative) — given a request specifying difficulty `"Extreme"` (not a supported
  tier), when generation is requested, then the request is rejected with an
  unsupported-difficulty error.
  *test:* `TestSelectDifficulty_RejectsUnknownTier`
- **AC-024** (happy) — given a scored candidate whose score falls within the requested
  `"Hard"` tier's threshold range, when the score is checked, then the candidate is accepted
  as final and no further resampling occurs.
  *test:* `TestResample_AcceptsCandidateInRange`
- **AC-025** (boundary, POL-004) — given a scored candidate whose score falls outside the
  requested tier's threshold range, when the score is checked, then the resample policy fires
  and a new candidate is generated.
  *test:* `TestResample_FiresWhenScoreOutOfRange`
- **AC-026** (boundary, POL-004) — given a newly resampled candidate produced in response to
  an out-of-range score, when the resample completes, then the new candidate is re-scored
  automatically before any further check.
  *test:* `TestResample_RescoresNewCandidate`
- **AC-027** (boundary, INV-003, POL-005) — given a candidate that has already been resampled
  up to the configured maximum retry bound without matching the requested tier, when the
  score is checked again, then generation is abandoned with a clear error.
  *test:* `TestResample_StopsAtMaxRetryBound`

## Guardrails

- G-1: Do not edit `src/nonogram/solver/**`, `src/nonogram/clues.py`,
  `src/nonogram/export/**`, `src/nonogram/sourcing/**` — Increment 2 is additive on top of
  Increment 1; the resample loop must revert without touching the solver or the
  orchestrator's core generation logic (handoff Increment 2 Rollback)
- G-2: INV-003 has exactly one home — `orchestrator.py` (trace.yml NFR-002 note). Reuse
  CARD-005's shared bounded-loop primitive; do not add a second independent counter
  (test: TestRetryLoop_BoundedIterations)
- G-3: Difficulty is a heuristic score bucket, not a construction guarantee (CON-004). The
  resample loop discards and re-draws candidates; it must not steer grid construction toward
  a tier, and an "Easy" puzzle carries no promise of being backtracking-free
- G-4: `--difficulty` validation stays inward of argparse (ADR-0010) — no `choices=` shortcut
  for AC-021; the unsupported-tier error is a domain error
- G-5: The existing regenerate-on-uniqueness-failure behavior is unchanged — resampling
  composes with it, it does not replace it
  (test: TestRegenerate_FiresOnUniquenessFailure, TestRegenerate_StopsAtMaxRetryBound)
- G-6: NFR-001's timing budget still holds with scoring in the loop — a resample loop that
  scores every candidate must not push 20x20 p95 past 5s
  (test: BenchGenerate_20x20_p95Under5s)

## System contract

- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions (check: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (check: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (check: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF)
- INV-003 — A puzzle's automatic-retry counter (regenerate, resample, pixel-nudge) never exceeds its configured maximum bound (check: TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestNudge_ReportsFailureAtCap, TestRetryLoop_BoundedIterations)

## Architecture context

- **FR:** FR-008, FR-010
- **NFR:** NFR-002
- **INV:** INV-003
- **CON:** CON-004
- **POL:** POL-004, POL-005
- **ADR:** ADR-0002, ADR-0005, ADR-0007, ADR-0010, ADR-0013
- **Components:** COMP-002, COMP-006, COMP-001, COMP-003
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—
