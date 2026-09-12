# CARD-068: Batch results — per-puzzle delete, Accept all, Reject all, Delete rejected

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/068-batch-results-bulk-actions
**Worktree:** —
**Source:** owner, 2026-09-12: "I'd like «delete» button on the generated puzzles last Batch generation step, then «Accept all», «reject all» and «delete rejected»"
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/admin/templates/generated_puzzles.html, src/nonogram/admin/app.py (bulk routes; the existing delete route), src/nonogram/admin/puzzle_review.py (bulk helpers, if they belong there), tests
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why

The last batch step (`/batch/<batch_id>/generated-puzzles`) offers Approve
and Reject per puzzle and nothing else, so curating a 30-puzzle batch is 30
clicks and there is no way to delete anything without leaving the page.

What exists today (checked 2026-09-12):
- per-puzzle **Approve** and **Reject** forms posting to
  `/puzzle/<id>/approve|reject?batch_id=<id>`, which redirect back to the
  batch page;
- a **delete** route (`/puzzle/<id>/delete`) that only accepts a **rejected**
  puzzle, refuses one that is in a book, talks to the database directly
  (`session_scope`, so it does nothing useful in in-memory mode) and always
  redirects to the global puzzle list;
- no bulk anything;
- the page renders at most 100 puzzles (`get_batch_puzzles(offset=0,
  limit=100)`).

## Decision (owner, 2026-09-12)

Bulk actions act on **this batch**, not on the whole library.

## What to implement

1. **Per-puzzle Delete** on the batch page, next to Approve and Reject,
   following the existing rule: a puzzle can be deleted once it is rejected
   and is not in a book. (If you want Delete to work straight from Approve
   or Draft, say so — it is the one open sub-decision here, and it widens
   what a mis-click can destroy.)
2. **Accept all / Reject all / Delete rejected** for the batch:
   - they act on **every** puzzle of that batch, not only the 100 the page
     renders, and the button says so when the batch is bigger;
   - each asks for confirmation naming the count and the action;
   - each reports what it did, including what it skipped and why ("3
     rejected puzzles deleted, 1 skipped: in a book").
3. **Delete works in both modes.** The current delete path is DB-only.
   Deletion belongs with the other store operations (`puzzle_review.py`),
   which already have an in-memory and a DB branch, rather than in the
   route.
4. The batch page stays the place you land after any of these.

## Acceptance criteria

- **AC-1** — per-puzzle Delete removes a rejected puzzle from the batch and
  from the store, and the page returns to the same batch.
- **AC-2** — Accept all / Reject all set every puzzle in the batch to that
  status, including puzzles beyond the rendered 100 (test with a batch of
  more than 100), and report the count.
- **AC-3** — Delete rejected deletes exactly the batch's rejected puzzles
  that are not in a book, leaves drafts and approved ones untouched, and
  reports both numbers.
- **AC-4** — no action ever deletes a puzzle that is in a book, and no
  action touches another batch's puzzles (test with two batches).
- **AC-5** — every bulk action works in in-memory mode and in DB mode
  (parametrised, the way the store's own tests do it).
- **AC-6** — each bulk button is guarded by a confirmation that names the
  count; a cancelled confirmation changes nothing.

## Guardrails

- G-1: Never delete a puzzle that is in a book, and never delete across
  batches.
- G-2: Keep the existing per-puzzle Approve and Reject behaviour, including
  the `batch_id` redirect back to the batch page.
- G-3: Bulk actions are POSTs with confirmation — no destructive GET.
- G-4: Admin-only; no edits under `sourcing/`, `orchestrator.py`, `cli.py`.
