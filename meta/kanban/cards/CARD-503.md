# CARD-503: Registry wording owed: INV-009's "move", AC-343's 24 px floor, FR-044's two unstated player rules

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/503-registry-wording
**Worktree:** ../PythonProject4-card-503
**Source:** roadmap wave 6 (cut 2026-11-20 on the owner's "please start the next wave"; premises re-read against main the same day). IDEA-159, IDEA-167, IDEA-064 (WSJF 2.31 each); bundled as registry amendments.
**Idea:** IDEA-159, IDEA-167, IDEA-064
**Wave:** 85
**Created wave:** 85
**Deferred waves:** 0
**Depends on:** —
**Touches:** meta/architecture/domain/aggregates.yml, meta/architecture/requirements.yml, meta/architecture/trace.yml, tests/test_check_ref_resolution.py
**UI surface:** —
**Review score:** —
**Started:** 2026-11-20T15:14Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

1. **IDEA-159 (CARD-191).** aggregates.yml INV-009 says a level's order is "changed only by an explicit move"; EC-026 already says reorder. Its AC-7 wording should say a DB-mode unsized puzzle is an id with no row. Re-read 2026-11-20: "explicit move" still there.
2. **IDEA-167 (after CARD-193).** requirements.yml AC-343's `given` still says "(cells at the 24 px phone floor)"; CARD-193 removed that flat floor and CARD-196 made it numeral-driven. Re-read 2026-11-20: still there.
3. **IDEA-064 (wave-31 goal check).** FR-044 leaves two player rules unstated: a drag follows the line of its FIRST move away from the start cell, and board cells are pointer-only, while the statement says "every control" is keyboard-reachable (AC-310 covers only tools, undo, redo and reset).

## What to implement

1. Reword INV-009 and its AC-7 as above.
2. Reword AC-343's `given` to the floor the code applies today (read it from the player CSS/JS by name, not from memory).
3. Add the two FR-044 rules as ACs, each naming an EXISTING test that pins it (find it by `ast`; if none pins one, say so and use the honest form from memory "ADR check refs must be honest": no invented test name), and narrow the "every control" statement so it no longer contradicts pointer-only cells.

## Acceptance criteria

* **AC-1**: the forge validator (forge_1 copy, `--phase all`) reports 0 errors before and after.
* **AC-2**: every new `test:` name resolves to one `def` (ast); tests/test_check_ref_resolution.py green, any frozen class re-derived as a set, never pasted.
* **AC-3**: each new AC's test reds when the rule it names is broken (one plant per rule, on a scratch copy).
* **AC-4**: net test count 0.

## Guardrails

* **G-1**: no product code change; if a rule is not what the code does, stop and report.
* **G-2**: trace.yml and requirements.yml agree on every AC this card touches.

## Worktree notes
