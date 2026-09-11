# CARD-055: Confine MockGenerator's random metrics to test-only reach

**Status:** ready
**Priority:** P3
**Category:** tech-debt
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/055-mockgenerator-test-only
**Worktree:** —
**Source:** meta/review/20260910T170025Z.yml#F-007
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/admin/puzzle_review.py, tests/test_wave3_e2e.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

`puzzle_review.py`'s `MockGenerator` (around lines 717-728) assigns
`quality_score: self.rng.randint(1, 100)` and
`recognizability: self.rng.choice(['low', 'medium', 'high'])` — random values,
not measurements. Grep-verified: `MockGenerator(...)` is not instantiated
anywhere in `src/nonogram/admin/*.py` today — it is reachable only from
`tests/test_wave3_e2e.py`. Not a live bug, but a third distinct "fake metrics"
implementation in the codebase (alongside CARD-050's targets) that would be easy
to reach for by mistake when wiring up a new admin code path, given its name
reads as a legitimate generator option alongside the real ones
(`orchestrator.generate_batch`).

1. Move `MockGenerator` out of `src/nonogram/admin/puzzle_review.py` (production
   code) into a test-support location (e.g. `tests/helpers/` or inline in the
   test file(s) that use it), OR clearly gate it so it cannot be imported from a
   production route — implementer's judgment on which fits this codebase's
   existing test-helper conventions better.
2. Update `tests/test_wave3_e2e.py`'s import accordingly.

## Acceptance criteria

- **AC-1** — given the move/gate is applied, when `src/nonogram/admin/*.py` is
  grepped for `MockGenerator`, then no production module defines or imports it.
- **AC-2** — given the existing tests that use `MockGenerator`, when the suite
  runs after this card, then they still pass unchanged in behavior.

## Guardrails

- G-1: Do not change `MockGenerator`'s behavior — this card only relocates it,
  it does not fix or improve its fakeness (that would be scope creep; the class
  is legitimately mock-only by design, it just shouldn't live where production
  code could accidentally reach it).
