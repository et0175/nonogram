# CARD-534: The Finalise route asks BookManager's plan gate through a public read-only method

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/534-public-plan-gate
**Worktree:** ../PythonProject4-card-534
**Source:** roadmap wave 15, cut 2026-11-23 on the owner's "pick the next no-decision wave from the backlog". IDEA-042 (CARD-153 F-003).
**Idea:** IDEA-042
**Wave:** 94
**Created wave:** 94
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/book_manager.py, src/nonogram/admin/app.py
**UI surface:** —
**Review score:** 9.5 (cycle 1/3 - CERTIFIED)
**Started:** 2026-11-23T18:30Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

Re-checked on main at the cut: the Finalise branch of `src/nonogram/admin/app.py` calls `book_mgr._refuse_unless_the_planned_book(book_id, book.status, BookStatus.READY_FOR_PDF.value, list(book.puzzle_ids))`, a private `BookManager` method, across modules. Its own comment says so: "book_manager.py has no public read-only form of the gate yet (review F-003, follow-up)". The caller wants only the ADR-0035/R1 gate's refusal, ahead of the gutter check, and none of `set_book_status`'s other checks or its write.

## What to implement

1. Add a public method on `BookManager` that runs only the plan gate for a proposed status change and writes nothing. Its docstring says it is the read-only form of the gate `set_book_status` runs. It raises what the private method raises (`StatusRefusal`, and the existing `ValueError` for a missing puzzle store, which CARD-496 routes to the outer handler). Have it delegate to the private method, so there is one gate, not two.
2. Switch the Finalise route to it and rewrite the comment above the call: the "private method, on purpose" paragraph goes, and the CARD-171/CARD-496 sentences stay.
3. Grep `src/` for any other cross-module call to `_refuse_unless_the_planned_book` and switch it too; record the grep.
4. Tests: change an existing Finalise or gate test to reach the public method (no new file). Add one assertion that the public method writes nothing: the book's stored status and row are unchanged after a refusal and after a pass.

## Acceptance criteria

- AC-1: no module other than `book_manager.py` names `_refuse_unless_the_planned_book`.
- AC-2: the Finalise route's refusal text and order are unchanged; the existing Finalise and CARD-171/CARD-496 tests pass.
- AC-3: the public gate writes nothing, asserted.
- AC-4: net tests +1 at most.

## Worktree notes

- 2026-11-23 (implementation). Premise re-verified by a run before any change: a throwaway spy on `BookManager._refuse_unless_the_planned_book`, driven through `tests/test_book_finalise_gutter.py`'s off-plan uncountable case, recorded one caller, `finalize_book`, and the plan refusal on the screen.
- Call-site census, by `ast` over src/, tests/ and scripts/ (attribute, name and string nodes). Before: one cross-module call, `create_app.finalize_book` in src/nonogram/admin/app.py; inside book_manager.py, two calls from `set_book_status` plus docstring mentions; one test docstring mention (`test_the_changed_membership_cannot_ship_behind_the_pass_it_no_longer_has` in tests/test_book_published_confirm.py); no test called the method directly; nothing in scripts/. After: only book_manager.py names it (its definition, `set_book_status`'s two calls, `check_plan_gate`'s delegation, docstrings). The test docstring now names `BookManager.check_plan_gate`, so AC-1 also holds for tests/.
- What changed: `BookManager.check_plan_gate(book_id, current_status, new_status, puzzle_ids)` is new. It delegates to the private gate and adds no logic of its own, so it raises `StatusRefusal` or the CARD-496 `ValueError` exactly as the private gate does. `finalize_book` calls it, and the "private method, on purpose" paragraph is gone from the comment above the call. The CARD-171/CARD-496 sentences are unchanged.
- Tests (net 0: 10713 collected before and after). `Shelf.stored` (row columns in DB mode; the stored Book and plan in memory mode) and `Shelf.gate` were added to tests/test_book_ready_gate.py. `test_the_book_reaches_the_ready_status` now asks the public gate first and asserts storage is unchanged after a pass. `test_the_transition_is_rejected_and_the_book_stays_draft` asserts the gate raises, storage is unchanged after the refusal, and the refusal text equals `set_book_status`'s. Both run in memory and SQLite DB mode through the `shelf` fixture, so the DB branch runs unarmed (it is not `db_required`).
- Control 1: `check_plan_gate` was made to write `updated_at` before delegating. 4 tests went red: both of the tests above, in both modes ("the read-only gate wrote on a pass" / "... on a refusal"). File restored; `git diff --stat` empty.
- Control 2: `check_plan_gate` was changed to `return None` without delegating. 3 tests went red: `test_the_transition_is_rejected_and_the_book_stays_draft[memory]` and `[db]` ("DID NOT RAISE StatusRefusal"), and `TestFinalisePost_PlanGateRefusalIsNotAnError::test_the_refusal_is_flashed_and_nothing_is_logged[uncountable]` (`assert 'x medium: 0% against 100%' in` the page). File restored; `git diff --stat` empty.
- Gate, unarmed, `-rfs`: tests/test_book_finalise_gutter.py, tests/test_book_ready_gate.py, tests/property/test_book_ready_gate.py, tests/test_book_published_confirm.py, tests/test_admin_error_text.py, tests/test_book_manager.py, tests/test_book_finalise_guide_preview.py, tests/test_book_finalise_guide_preview_layout.py, tests/test_card_108_delete_book_releases.py, tests/test_book_arrange_size_filter.py, tests/test_book_arrange_sort_by_size.py. Result: 499 passed, 0 failed, 0 skipped.
- Not established: no test sends the CARD-496 `ValueError` (manager with no puzzle store) through `check_plan_gate`. It reaches the private gate only through `set_book_status` (`TestBookReady_UnreadableSelectionIsRefused`). The public method passes the call through unchanged, and `create_app` always wires a store, so the route cannot reach that state.

[Review 1/3] Score: 9.5, certified. Re-derived: an `ast` walk of src/, tests/ and scripts/ finds `_refuse_unless_the_planned_book` only in book_manager.py (definition, `set_book_status`, `check_plan_gate`, docstrings). Baseline 355 passed over the five gate files. Skip-the-gate control: 4 red (both modes of `test_the_transition_is_rejected_and_the_book_stays_draft`, `TestBookReady_RefusalNamesOffendingCell::test_the_finalize_route_flashes_it`, and `TestFinalisePost_PlanGateRefusalIsNotAnError::test_the_refusal_is_flashed_and_nothing_is_logged[uncountable]`). Write-to-row and write-to-plan-only controls: each 4 red on their own messages, in memory and db, so "writes nothing" catches a plan write too. Finalise: only the call name and the comment changed; the refusal handling is identical to main. Net 0. F-001 (low): the notes' "Control 2: 3 tests red" is 4; the fourth is `TestBookReady_RefusalNamesOffendingCell::test_the_finalize_route_flashes_it`. This line is the correction. F-002 (info): `Shelf.stored` does not compare puzzles.book_id; AC-3 does not ask for it. F-003 (info): the CARD-496 `ValueError` is not sent through `check_plan_gate`; already under "Not established".

**Merge gate (orchestrator).** `make test-gate BASE=main` on `9118874f` (main 233e10a2, already merged in) answered SELECTION: 9039 passed / 30 skipped (unarmed) / 13 deselected / 1 xfailed / 0 failed in 42 min 32 s, then the marked run 11 passed. 2 marked tests are owed at the wave close.
