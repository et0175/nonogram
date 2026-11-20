# CARD-500: After a refused Print setup save, the "edited" marks follow the plan the page shows

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/500-edited-marks-follow-submitted
**Worktree:** ../PythonProject4-card-500
**Source:** owner 2026-11-20 ("yes, make the edited marks follow the submitted plan"), on CARD-497 review F-005.
**Idea:** —
**Wave:** 84
**Created wave:** 84
**Deferred waves:** 0
**Depends on:** CARD-497
**Touches:** src/nonogram/admin/app.py, tests/test_book_plan_storage.py
**UI surface:** admin Print setup (step 2), the refusal re-render's matrix marks
**Review score:** —
**Started:** 2026-11-20T12:13Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

CARD-497 made a refused Print setup page describe one plan (the Planned row, the column totals, the warning). Its review (F-005) found the matrix's "edited" marks still named the **stored** plan's hand-edits, by CARD-120's recorded decision, so after a refusal the marks and the warning described different plans. The owner chose to have the marks follow the submitted plan.

## What to implement

1. On a refused submission that kept a plan (only the trim or domain refused), the marks are the submitted plan's hand-edits — exactly what saving it would store.
2. When the plan itself was refused there is no plan to judge a cell against: no cell is marked (the orchestrator's call, stated to the owner 2026-11-20).
3. A GET, a form without the plan fields, and every successful save keep the stored plan's marks, byte-identical to main.

## Acceptance criteria

* **AC-1**: after a refused trim the marked cells equal the cells a real save of the same form stores as edited (oracle: the same form, a readable trim, on a twin book in the same stored state, read back); control: main's `_plan_context` reds it.
* **AC-2**: after a refused plan no cell is marked; control: main reds it.
* **AC-3**: successful pages byte-identical to main; net test count 0.

## Guardrails

* **G-1**: nothing stored on a refusal; CARD-497's figures unchanged.

## Worktree notes
