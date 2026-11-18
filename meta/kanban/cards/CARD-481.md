# CARD-481: A mandatory rule's check names a test that exists

**Status:** ready
**Priority:** P1
**Category:** tech-debt
**Estimate:** 2c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** —
**Worktree:** —
**Source:** roadmap rescore 2026-11-18, wave 2 (IDEA-004, WSJF 5.08; absorbs IDEA-214 per meta/kanban/triage-outcomes.yml); premise re-read against main on 2026-11-19.
**Idea:** IDEA-004
**Wave:** —
**Created wave:** 81
**Deferred waves:** 0
**Depends on:** —
**Touches:** meta/architecture/requirements.yml, meta/architecture/trace.yml, tests/test_check_ref_resolution.py
**UI surface:** none
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

The constraints and invariants are the rules the code must never break, and each names the test that holds it. Several of those names resolve to no `def` or `class` anywhere. Measured on main on 2026-11-19 by a definition search over `tests/`: **CON-005** (the solver never reports a false unique solution, the one mandatory correctness property) names `PropertyTest_Solver_NeverFalsePositiveUniqueness`, while the real test is `test_never_false_positive_uniqueness` in `tests/property/test_solver_uniqueness.py`. CON-010, CON-012, CON-014 and CON-019 are in the same state. The backlog item also lists ADR-0006/R1, INV-001, INV-002, INV-008, INV-009..INV-012 and ADR-0029/R2. The validator's text search reports some of these as covered, because the names appear in prose (see `tests/test_check_ref_resolution.py`'s docstring).

## What to implement

1. Derive the population: every `test:`/`ref:`/`check:` on a `CON-*`, `INV-*` or ADR rule in `meta/architecture/**` whose name resolves to no `def`/`class` line under `tests/` (by `ast` or an anchored definition search, never a word search).
2. For each: if a test asserting that rule exists under another name, re-point the ref (and its `trace.yml` row) to it; otherwise re-type the check as `review-lens` with one sentence naming what is untested. Never write a placeholder name.
3. `tests/test_check_ref_resolution.py`'s frozen classes (`HONEST_DEAD`, `FALSELY_ALIVE`, `CENSUS`, `TRACE_TESTS`, `DEFINED` …) will move. Record each move as a repair in that file's own style, re-derived on the branch; never paste a printed count.

## Acceptance criteria

* **AC-1**: the derived population is listed in the card notes, rule by rule, with the outcome (re-pointed to X / review-lens) for each.
* **AC-2**: CON-005's ref resolves to `test_never_false_positive_uniqueness`, and a run of that test by node id collects ≥ 1 case with 0 skipped.
* **AC-3**: every re-pointed ref is checked to actually assert its rule (read, not name-matched). A test that only mentions the rule is not a resolution.
* **AC-4**: `tests/test_check_ref_resolution.py` passes on the branch with its frozen classes re-derived, and each departure is explained as a repair.
* **AC-5**: no new tests (fewer-tests rule); net test count 0.

## Guardrails

* **G-1**: AC refs on FRs are out of scope: an open FR's AC legitimately names a test that isn't written yet.
* **G-2**: no edit to `src/`; this is a registry repair.
* **G-3**: the module's rule holds: its guard must not spell a dead ref into tracked non-Markdown code (that revives it).

## Worktree notes

—
