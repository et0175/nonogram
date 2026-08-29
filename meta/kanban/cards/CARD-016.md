# CARD-016: Bounded pixel-nudge recovery loop for image mode

**Status:** in_progress
**Priority:** P2
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/016-pixel-nudge-recovery
**Worktree:** ../PythonProject4-card-016
**Source:** meta/architecture/handoff.md#increment-3
**Idea:** —
**Wave:** 10
**Depends on:** CARD-015
**Touches:** src/nonogram/orchestrator.py, src/nonogram/sourcing/image.py, tests/test_nudge.py
**Review score:** —
**Started:** 2026-08-29T09:20:00Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

The recovery path for image mode. An uploaded image is the user's picture, so it cannot be
discarded and redrawn the way a random grid can — instead the tool makes a small, bounded
number of pixel adjustments and re-checks uniqueness.

1. **POL-002 AutoNudgePixelsOnImageUniquenessFailure (FR-013).** When the converted grid
   fails the uniqueness check and `nudge_count < cap`, apply a bounded pixel nudge and
   re-check. The policy decision lives in COMP-002; the nudge itself is **applied by
   COMP-003**, which owns the grid the image produced (trace.yml FR-013 note).
2. **The heuristic.** Pick the cell whose flip most plausibly disambiguates — e.g. inside a
   line the solver could not decide, or at a run boundary. The heuristic's effectiveness is
   the risk this card exists to collapse; keep it in one named function so it can be swapped
   without touching the loop, and record what you tried in the worktree notes.
3. **Cap: 5 attempts (ADR-0002)** — distinct from the 20-attempt regenerate/resample bound.
   Reuse CARD-005's shared bounded-loop primitive with a different bound; INV-003 still has
   exactly one home (COMP-002).
4. **POL-003 ReportFailureWhenNudgeCapExhausted.** At the cap, stop altering the image and
   report failure. The message must tell the user what to do next: retry with a different
   image or a different size (AC-036) — not just "failed".
5. Carry the running `nudge_count` on the `Puzzle` aggregate; CARD-017 reports it.

## Acceptance criteria

- **AC-034** (happy, POL-002) — given an uploaded image whose initial conversion fails the
  uniqueness check, with nudge attempts remaining under the cap, when the auto-nudge policy
  evaluates, then a bounded pixel nudge is applied automatically and the result is
  re-checked.
  *test:* `TestNudge_AttemptsBoundedRecovery`
- **AC-035** (boundary, INV-003, POL-003) — given an uploaded image conversion that has
  exhausted the configured nudge cap without reaching uniqueness, when the uniqueness check
  is evaluated again, then the tool reports failure to the user and stops altering the image.
  *test:* `TestNudge_ReportsFailureAtCap`
- **AC-036** (negative) — given a reported nudge-cap failure, when the failure is presented
  to the user, then the message states that the user should retry with a different image or
  size.
  *test:* `TestNudge_FailureMessageSuggestsRetry`

## Guardrails

- G-1: Do not edit `src/nonogram/sourcing/random_grid.py`,
  `src/nonogram/sourcing/library.py`, `src/nonogram/solver/**`,
  `src/nonogram/export/**`, `src/nonogram/clues.py`, `src/nonogram/difficulty.py` — the
  nudge loop must revert without touching random/library modes, the solver, or export
  (handoff Increment 3 Rollback)
  (test: TestGenerateRandom_ProducesRequestedSize, TestGenerateLibrary_ProducesCatGrid,
  TestExport_WritesPNG)
- G-2: The nudge cap is 5 (ADR-0002) and is enforced through COMP-002's single bounded-loop
  primitive — INV-003 has exactly one home. Do not add an independent counter in
  `image.py`
  (test: TestRetryLoop_BoundedIterations)
- G-3: At the cap the tool **stops altering the image** and reports — no unbounded "one more
  try", no silent continued modification (POL-003, FR-013 statement)
- G-4: Uniqueness is still the solver's verdict — a nudged grid is re-checked in full, never
  assumed unique because a nudge was applied (CON-005 is mandatory)
- G-5: Out of scope — no nudge-count CLI output (FR-014, CARD-017); this card only carries
  the count on the aggregate
- G-6: No new dependency (ADR-0006)

## System contract

- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions (check: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (check: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (check: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF)
- INV-003 — A puzzle's automatic-retry counter (regenerate, resample, pixel-nudge) never exceeds its configured maximum bound (check: TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestNudge_ReportsFailureAtCap, TestRetryLoop_BoundedIterations)

## Architecture context

- **FR:** FR-013
- **NFR:** NFR-002
- **INV:** INV-003
- **CON:** CON-005
- **POL:** POL-002, POL-003
- **ADR:** ADR-0002, ADR-0004, ADR-0007
- **Components:** COMP-002 (policy + bound), COMP-003 (applies the nudge), COMP-005 (re-check)
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—
