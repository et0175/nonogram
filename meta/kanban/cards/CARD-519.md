# CARD-519: Write the wave-30 book behaviours into requirements.yml as acceptance criteria

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 2c
**Complexity:** standard
**Revision pending:** false
**Skill:** business-analyst
**TDD:** —
**Branch:** card/519-wave30-acs
**Worktree:** ../PythonProject4-card-519
**Source:** roadmap wave 11, cut 2026-11-22 on the owner's "start the no-decision wave 11". IDEA-010.
**Idea:** IDEA-010
**Wave:** 90
**Created wave:** 90
**Deferred waves:** 0
**Depends on:** —
**Touches:** meta/architecture/requirements.yml
**UI surface:** —
**Review score:** —
**Started:** 2026-11-22T10:32Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

IDEA-010: behaviours CARD-158 and CARD-159 shipped exist only as card ACs, not in `meta/architecture/requirements.yml`, so nothing in the registry says a later change must keep them. Listed then: inches trims reachable on Print setup; the stored trim shown on the book page ("Not set" / "Cannot be read"); step prose agreeing with the stepper; /book/create keeping typed input; two download buttons per page; lost-cover handling (FR-043 has no AC for it).

## What to implement

Re-verify each behaviour on main first (it may have changed or been removed since wave 30): find the code and the test that verifies it today, by `ast`/import, not text search. Then add each still-true behaviour as an AC under the right FR, in the registry's existing format, naming the test that verifies it. A behaviour that no longer holds, or whose test no longer exists, is not added: say so in one line each.

## Acceptance criteria

* **AC-1**: each listed behaviour is either an AC in requirements.yml naming an existing test node that verifies it, or dropped with one line saying why.
* **AC-2**: every named test node exists and passes (run each by node id, report skips; a skip is not a pass), and is the test that actually asserts the behaviour (attribute by the enclosing test, not by file).
* **AC-3**: the registry's own checks stay green: tests/test_check_ref_resolution.py, the forge validator (meta/architecture validators, forge_1 copy), and tests/test_kanban_review_record.py. Frozen census pins that move are re-derived against a def/class line, never pasted from a printed number.
* **AC-4**: no code or test changes; net test count 0.

## Guardrails

* **G-1**: no planned or future test is named as a check: only tests that exist and pass today.
* **G-2**: no edits outside requirements.yml, other than this card's notes and any census pin AC-3 forces (name it).

## Worktree notes
