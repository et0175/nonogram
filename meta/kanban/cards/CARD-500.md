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
Implemented by the orchestrator.

* **Change.** `_plan_context` (app.py) computes `marked = frozenset() if summary is None else summary.edited` from the same `summary` CARD-497 chose for the Planned row and the warning, and the matrix's `(bucket, tier) in marked` replaces `in plan.edited`. The docstring says the marks follow that plan and that this replaces CARD-120's "the edited marks stay the stored plan's". `summary` is the stored plan whenever no refused submission carried the plan fields, so GET and successful pages read the same marks as before.
* **AC-1.** `test_trim_refusal_carries_the_plan_input_back` (stored plan disagreeing: hand-edit at cell 2 x hard; submitted 120 at 30/45/25 with cell 1 x medium typed off, refused trim) now asserts the marked cells equal what a real save stores: the same form with a readable trim posted to a twin book in the same stored state, its stored `edited` read back. Measured: that set is six cells (`cell_0_easy`, `cell_1_easy`, `cell_1_medium`, `cell_2_easy`, `cell_2_medium`, `cell_2_hard`), not the one typed off — because the submission changes the split as well as the count, and CARD-489 judges typed cells against the SHOWN split (its review F-003, recorded for the backlog), and the untouched stored edit keeps its mark (CARD-489 F-002's rule). My first two expectations ("only cell 1 x medium", then "not cell 2 x hard") were wrong for that reason; the oracle replaced them. Control (main's app.py): `{'cell_2_hard'} == {six cells}`, both modes.
* **AC-2.** `test_refused_split_keeps_the_typed_matrix` asserts no cell is marked. Control (main): `{'cell_2_hard'} == set()`, both modes.
* **AC-3.** CARD-497's capture script on main and on the branch: 12 pages (GET default / disagreeing / inches / after success; successful, disagreeing, inches and unchanged-plan POSTs and the pages they lead to) byte-identical. Collected: 10711 on main and on the branch, net 0.
* **Gate (unarmed, -o addopts= -rfs):** CARD-497's ten Print setup files: 813 passed, 0 skipped.
