# CARD-487: ADR-0029/R4's check tests its own rule, not the import graph

**Status:** review
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/487-r4-check
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-487
**Source:** roadmap rescore 2026-11-18, wave 3 (IDEA-006, WSJF 3.85); premise re-read against main on 2026-11-19.
**Idea:** IDEA-006
**Wave:** 82
**Created wave:** 82
**Deferred waves:** 0
**Depends on:** —
**Touches:** meta/architecture/decisions/adr/0029-difficulty-by-strategy-ladder.md, tests/test_solver*.py, tests/property/*, tests/test_check_ref_resolution.py
**UI surface:** —
**Review score:** 9.5 (cycle 2/3 - CERTIFIED)
**Started:** 2026-11-19T19:53Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

ADR-0029/R4 (mandatory) has two halves: the overlap masks behind the `simple_overlap` rung are computed **relative to the line's already-known cells** (the leftmost and rightmost placements consistent with them, intersected), and they are re-derived natively inside `solver/` without importing `clues.py`. Its `check:` is `test_every_import_in_the_package_points_inward` (tests/test_cli.py), which covers only the import half. Re-read 2026-11-19: the ref is unchanged. A dead-ref sweep cannot catch this, because the ref is alive; it just cannot fail when the rule is broken.

## What to implement

1. Find whether a test already pins the first half (masks relative to known cells). If one exists, add it to R4's `check:` ref; if not, write the narrowest one, preferably by extending an existing solver test, against an independent oracle (the project's brute-force or line-enumeration helpers), never by re-deriving with the function under test.
2. Keep the import-graph test on the ref for the second half.

## Acceptance criteria

* **AC-1**: R4's `check:` names a test that reds when the masks are computed ignoring the known cells (control: plant the from-scratch overlap, it reds), and still names the import-graph test.
* **AC-2**: tests/test_check_ref_resolution.py stays green; any frozen class it holds is re-derived, not pasted.
* **AC-3**: net test count at most +1; report it.

## Guardrails

* **G-1**: no solver behaviour change; if the control finds the rule actually broken in code, stop and report: that is a correctness finding, not this card's fix.
* **G-2**: the brute-force oracle never imports `nonogram.solver` (CLAUDE.md).

## Worktree notes

—
