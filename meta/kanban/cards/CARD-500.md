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

[Review 1/3] Score: 9.0, one gating finding, not certified. Behaviour held everywhere it was measured: 3 stored-plan states x 7 submitted plans x 21 refusals, 441 cases per storage mode, 0 mismatches between the marks and what a twin save stores (main: 246 mismatches); 18 unchanged pages byte-identical; 1445 passed over the 21 files that reference /setup-print. F-001 (high, gating, ADR-0022/R4) AC-1's test could not tell "the submitted plan's marks" from "those plus the stored plan's" (the stored hand-edit stayed edited in its one scenario), so a union mutant passed all 73 cases; F-002 (low, pre-existing: CARD-489 F-003) the six-cell surprise is consistent with a save but misleads (a typed value equal to what the new split gives is marked edited, against the matrix caption) — put to the owner 2026-11-20; F-003 (info) the "ten Print setup files" were not named.
Fix round 1 (orchestrator): F-001 — the same test also submits the stored hand-edit typed back to its split value (150 at 40/40/20, the AC-198 matrix, refused trim) against the disagreeing stored plan, with the twin-save oracle; it asserts `cell_2_hard` is not in what the save stores and the marks equal it, and nothing was stored. Controls: the union mutant (`summary.edited | plan.edited`) reds it in both modes (`{'cell_2_hard'} == set()`); main's app.py reds 4 of 4. F-003 — the ten files: tests/test_book_plan_storage.py, test_book_setup_print_mobile.py, test_book_trim_persistence.py, test_book_player_domain.py, test_book_divider_pages_option.py, test_print_specs.py, test_book_pdf_ink_mode.py, test_book_workflow_steps.py, test_admin_import_consistency.py, test_book_proof_pages.py. tests/test_book_plan_storage.py after the fix: 73 passed.
