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
**Review score:** —
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
