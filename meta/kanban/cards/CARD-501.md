# CARD-501: A typed matrix cell is judged against the count and split the owner submitted

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/501-judge-against-submitted-split
**Worktree:** ../PythonProject4-card-501
**Source:** owner 2026-11-20 ("yes, judge typed cells against the submitted split"), on CARD-500 review F-002 = CARD-489 review F-003.
**Idea:** —
**Wave:** 84
**Created wave:** 84
**Deferred waves:** 0
**Depends on:** CARD-489, CARD-500
**Touches:** src/nonogram/admin/book_manager.py, tests/test_book_plan_storage.py
**UI surface:** admin Print setup (step 2), which matrix cells are marked hand-edited after a save or a refusal
**Review score:** —
**Started:** 2026-11-20T13:01Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

`book_manager.revise_plan` decides whether a typed cell is hand-edited by comparing it with a reference prefill. CARD-489 made that reference use the **submitted count** but kept the **shown split**. So when the owner changes count and split together and types the new split's values, those cells are marked "edited" — contradicting the matrix caption ("until you change it back to the value the split gives"). Measured 2026-11-20 on CARD-500: 150 at 40/40/20 -> 120 at 30/45/25 with one cell typed off marked six cells.

## What to implement

The reference is the prefill at the submitted count **and** the submitted split. Unchanged: a value equal to the shown value is "left alone" and keeps its mark; un-edited cells re-derive from the new split.

## Acceptance criteria

* **AC-1**: count and split changed together, every cell typed to the new prefill but one typed off it (and off the shown value): only that one is edited; control: the shown-split reference reds it.
* **AC-2**: every existing revise_plan and Print setup test still holds (CARD-489's count-only case, CARD-120's rules, CARD-500's save-based marks).
* **AC-3**: net test count 0.

## Guardrails

* **G-1**: no schema change; a stored plan's existing marks are not rewritten (the rule applies to new submissions only).

## Worktree notes
