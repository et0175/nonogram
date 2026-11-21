# CARD-510: Independently re-fire CARD-276's six mutant cells, or declare each one unfired with its reason

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/510-refire-276-mutants
**Worktree:** ../PythonProject4-card-510
**Source:** roadmap wave 7, added 2026-11-20 on the owner's "add IDEA-215 to this wave too". IDEA-215 (WSJF 3.08), split out of CARD-300 (skipped) on 2026-10-28, where it was AC-5.
**Idea:** IDEA-215
**Wave:** 86
**Created wave:** 86
**Deferred waves:** 0
**Depends on:** —
**Touches:** none in src/ or tests/ (a measurement; results go on this card)
**UI surface:** —
**Review score:** —
**Started:** 2026-11-21T00:19Z
**Blocked by:** —

## Why this card exists

CARD-276 (done, merged `f794d5a8` at review 6.5, NOT certified) owed AC-5: fire the six kill-matrix cells N8, N12b, N13, N14, N16, N18 against CARD-262's `ac479658` and against CARD-276's own HEAD. Its implementation round did fire them once and recorded a table (CARD-276, section "5. The six unfired cells (AC-5)": against `ac479658` N8 = 1, N12b = 5, N13 = 1, N14 = 2, N16 = 1, N18 = 1 FAIL cells; against HEAD N8h = 1, N13h = 0 declared no-op, N14 = 2, N16 = 1, N18 = 1, N12b no analogue). Review cycle 2 accepted that table on trust and called it "the largest single thing I did not measure". What is owed is an independent re-run, or a written declaration per cell, with no code change.

## What to implement

1. Read CARD-276 section 5 (the domain: committed `tests/kill_matrix.py`, `Pass.RECORDING`, `ast.Assert` node counts, child instrumentation off, ANY-RED aggregation, line-count-preserving mutants, SHIPPED re-run FAIL-free between mutants) and its mutant definitions. Read tests/kill_matrix.py's own API by import.
2. Re-create each mutant from its definition (not from CARD-276's scratch scripts, if any survive) and fire it against `git archive` copies of `ac479658` and of CARD-276's merged tree (`f794d5a8`), under /private/tmp/claude-501/card510/, never in a worktree. Confirm each copy is the code under test (`__file__`).
3. Record a table per tree: cell, mechanism deleted, FAIL count, the assertion nodes it reds (by test name), and whether it matches CARD-276's table. A mismatch is a finding: say which number is right and why.
4. A cell that cannot be fired faithfully (its mechanism or the instrument no longer supports it at that commit) is declared unfired with its concrete reason.
5. One line on whether each cell's mechanism still exists on today's main (by `ast`); no firing on main is required.

## Acceptance criteria

* **AC-1**: each of the six cells, against both trees, is fired and recorded with its FAIL count and red nodes, or declared unfired with its reason (N12b has no HEAD analogue by CARD-276's AC-4: confirm that by `ast`, do not assume it).
* **AC-2**: SHIPPED (unmutated) is FAIL-free on each tree, re-run between mutants; every mutant is shown to change the file (the instrument's `old` present, the mutated bytes differ).
* **AC-3**: no change under src/ or tests/; net test count 0.

## Guardrails

* **G-1**: never run a mutant in the worktree or the main checkout; scratch copies only. `git diff --stat` on the worktree is empty apart from this card at hand-back.
* **G-2**: no database is needed; if a selected test is db_required, say it skipped and why.

## Worktree notes
