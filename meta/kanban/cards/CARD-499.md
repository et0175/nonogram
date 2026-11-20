# CARD-499: Two test instruments' blind spots: the globals guard ignores augmented and annotated assignment; the kill matrix cannot measure a test that patches its own module

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 2c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/499-instrument-blind-spots
**Worktree:** ../PythonProject4-card-499
**Source:** roadmap wave 5 (cut 2026-11-20 on the owner's "please start the next wave"; premises re-read against main the same day). IDEA-113 WSJF 3.08, IDEA-196 WSJF 3.08; bundled as test-instrument fixes, each 0.125 d.
**Idea:** IDEA-113, IDEA-196
**Wave:** 84
**Created wave:** 84
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/test_db_engine_lifecycle.py, tests/kill_matrix.py, tests/test_kill_matrix.py
**UI surface:** —
**Review score:** —
**Started:** 2026-11-20T10:24Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

1. **IDEA-113 (CARD-258 deferral).** tests/test_db_engine_lifecycle.py `_global_names_assigned_by` collects only `ast.Assign` targets, so a global the builder sets with `+=` (`ast.AugAssign`) or `x: T = …` (`ast.AnnAssign`) is never collected, and the guard passes by silence. Its docstring claims "a shape this function cannot analyse biases it to red rather than to a pass", which is false for those two shapes.
2. **IDEA-196.** tests/kill_matrix.py's child plugin (`pytest_configure` in the generated plugin source) registers the rewritten target module in `sys.modules` but never sets it as an attribute of its parent package. pytest's `monkeypatch.setattr("pkg.mod.name", …)` resolves a dotted target by attribute walk from the package, so any test that patches its own module by a dotted string cannot be measured (found by CARD-264). The backlog says a one-line fix.

## What to implement

1. The collector handles `AugAssign` and `AnnAssign` (value present) targets, or raises on any assignment shape it does not analyse, so the docstring's "biases to red" is true; the docstring says exactly what is collected.
2. The plugin sets the rewritten module on its parent package (and restores nothing it did not set); a test that dotted-`setattr`s its own module is measured.

## Acceptance criteria

* **AC-1**: a planted `global x; x += 1` (and `x: int = 1`) in a copy of session.py's builder reds the guard; control: the old collector stays green on it.
* **AC-2**: the kill matrix measures a fixture test that dotted-`setattr`s its own module (extend an existing kill-matrix test case if one fits); control: without the fix it reports the instrument failure it does today.
* **AC-3**: the guard and the kill matrix's own tests green; net test count at most +1.

## Guardrails

* **G-1**: never edit src/nonogram/db/session.py for the plant; plant in a copy or a parsed string.
* **G-2**: the kill matrix's existing measured figures elsewhere are unchanged (run its own test file).

## Worktree notes
