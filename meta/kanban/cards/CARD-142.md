# CARD-142: The batch's bulk buttons keep up with per-puzzle approve and reject

**Status:** ready
**Priority:** P1
**Category:** bug
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/142-bulk-buttons-follow-single-actions
**Worktree:** —
**Source:** owner, 2026-09-23 ("delete rejected button is disabled if we reject individual puzzles, not the batch")
**Idea:** —
**Wave:** 26
**Depends on:** —
**Touches:** src/nonogram/admin/templates/generated_puzzles.html, src/nonogram/admin/app.py, tests/test_batch_bulk_button_state.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

On the batch review screen, rejecting puzzles one at a time leaves **Delete rejected**
greyed out, even though there are now rejected puzzles to delete. Rejecting the whole batch
enables it, because that route redirects and the page re-renders.

The cause is a split between two update paths. The per-puzzle Approve and Reject forms post
by `fetch` and never reload (generated_puzzles.html:146-162): the handler rewrites the status
badge and reveals that puzzle's own Delete form, so the card looks right. But the three bulk
buttons carry a server-rendered `disabled` attribute and a confirmation count from
`action_counts` (generated_puzzles.html:114, `batch_action_counts`), computed once at page
load and never touched again. Per-puzzle Delete does a real POST — the CARD-068 comment says
why — so it re-renders and looks correct, which is what makes the bug look arbitrary.

1. **Let the action endpoints report the fresh counts.** `/puzzle/<id>/approve` and
   `/puzzle/<id>/reject` return `batch_action_counts(batch_id)` as JSON when the caller asks
   for JSON (the `fetch` sets the header; negotiate on `Accept`, or an explicit flag). A
   request without it keeps today's redirect exactly — the no-JavaScript path must not
   change, and the existing route tests must stay green unedited.
2. **The handler applies them.** After a successful action it updates all three bulk buttons:
   the `disabled` state and the number their confirmation names. Approve-all and Reject-all
   drift for the same reason and are fixed by the same update — do not fix only the one the
   owner noticed.
3. **Do not count the rendered cards.** `batch_action_counts` is deliberately computed from
   the batch, not from the rows a page happens to show (see its docstring); counting DOM
   cards would break on any batch the page does not render whole, and would put a second
   implementation of the rules in JavaScript.
4. **A failed action changes nothing.** The counts are applied only on a successful response,
   so a puzzle the store refuses — one that is in a book (CARD-100) — leaves the buttons as
   they were.

Out of scope: the per-puzzle Delete form's real POST (CARD-068 chose that deliberately and it
works), pagination of the batch screen, and any change to what the bulk actions do.

## Acceptance criteria

- New: rejecting one puzzle by fetch enables Delete rejected and its confirmation names 1.
  test: TestBulkButtons_SingleRejectEnablesDeleteRejected
- New: the approve and reject endpoints return the fresh counts to a JSON caller, and a
  browser form post still gets today's redirect.
  test: TestBulkButtons_ActionsReportCountsToJsonCallersOnly
- New: the counts a JSON caller receives equal `batch_action_counts` for that batch.
  test: TestBulkButtons_ReportedCountsMatchTheBatch
- Regression: a puzzle in a book is still refused, and the refusal leaves the counts alone.
  test: TestBulkButtons_RefusedActionDoesNotChangeCounts

## Guardrails

- G-1: The no-JavaScript path is unchanged — every existing test of
  `/puzzle/<id>/approve` and `/puzzle/<id>/reject` stays green without being edited.
- G-2: No second implementation of the counting rules. The numbers come from
  `batch_action_counts`; JavaScript only displays what the server sent.
- G-3: Do not edit `src/nonogram/export/**` or `tests/fixtures/a4_golden/**` (CON-019).
- G-4: No schema change.

## Architecture context

- **FR:** FR-026, FR-027 (batch review)
- **ADR:** ADR-0032 (the storage boundary), ADR-0019 (adapters hold no domain logic)
- **Components:** COMP-009
- **Trace:** meta/architecture/trace.yml

## Worktree notes

- [Origin] Owner, 2026-09-23, on the first working deploy. Reported as "delete rejected is
  disabled", but Approve-all and Reject-all go stale by the same mechanism — the report is
  one symptom of one bug, and the card fixes the mechanism.
