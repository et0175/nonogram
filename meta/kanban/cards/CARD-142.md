# CARD-142: The batch's bulk buttons keep up with per-puzzle approve and reject

**Status:** review
**Priority:** P1
**Category:** bug
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/142-batch-bulk-buttons
**Worktree:** ../PythonProject4-CARD-142
**Source:** owner, 2026-09-23 ("delete rejected button is disabled if we reject individual puzzles, not the batch")
**Idea:** —
**Wave:** 26
**Depends on:** —
**Touches:** src/nonogram/admin/templates/generated_puzzles.html, src/nonogram/admin/app.py, tests/test_batch_bulk_button_state.py
**Review score:** 7.5 (cycle 1/3) — below min_score 8, fix cycle running
**Started:** 2026-09-24T17:24:11Z
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

- [Implemented] One number travels, and the page counts nothing.

  `/puzzle/<id>/approve` and `/puzzle/<id>/reject` answer a caller that *prefers* JSON
  (`Accept: application/json` rated above `text/html` — a request with no `Accept` at all
  rates them equally and is therefore HTML) with
  `{"ok", "message", "action_counts"}`, where the counts are `batch_action_counts(batch_id)`
  asked of the store. Everything else — a browser form post, the library's own rows, every
  existing route test — takes the untouched flash-and-redirect branch. The counts ride along
  only on success; a refusal answers 409 (in a book) or 404 (unknown) with no `action_counts`
  key at all, so there is nothing for the handler to apply and the buttons keep what they
  had.

  The page's `fetch` now sends that header and applies the counts to all three bulk buttons:
  `disabled` when the count is zero, and the confirmation re-worded with the fresh number.
  The wording lives in exactly one place — a `bulk_confirm` macro, read three ways: the
  sentence the page ships with, and the singular/plural shapes carried as
  `data-confirm-one`/`data-confirm-many` with an `{n}` placeholder the script substitutes.
  So JavaScript never composes a sentence, and (G-2) never counts anything: no DOM card is
  ever counted, which also keeps the numbers right on a batch bigger than the 100 rows the
  screen renders (pinned by `test_the_counts_are_the_batchs_not_the_rendered_rows`).

  Side effect worth knowing: because a refusal is now a 4xx to a `fetch` caller, a puzzle a
  book holds shows "Error" on its badge instead of silently displaying "✓ Approved" — the
  redirect used to be followed to a 200 and read as success.

  Placement detail: the `data-*` attributes sit on the `<button>` *after* `disabled`, not on
  the `<form>`. CARD-068's `test_a_bulk_button_with_nothing_to_do_is_disabled` reads a
  400-character window from the form's action, and hanging three attributes off the form
  pushed `disabled` out of it. Behaviour identical, byte offsets preserved, that test
  untouched.

- [Tests] `tests/test_batch_bulk_button_state.py`, 20 cases in the four classes the ACs name.
  No JS engine is in the dependency baseline, so the two halves are pinned separately:
  `_assert_wiring` pins that the script reads `data.action_counts` and drives the buttons off
  it, and `_apply_counts` is an independent second implementation of the *display* rule,
  written from the rendered attributes. `_counts_from_the_store` reimplements the counting
  rule over the rows as a cross-check, so AC-3 compares the reported counts against both
  `batch_action_counts` and a second reading of the same rule.

- [Suite] Full run green but for `tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied`,
  the known pre-existing failure (unrelated: it asserts the word "Fixed" on the batch-from-
  images page). No SCOPE+ — the change stayed inside the card's three files.

[Scope] src/nonogram/admin/app.py, src/nonogram/admin/templates/generated_puzzles.html, tests/test_batch_bulk_button_state.py
[Scope gate] in_scope — actual diff == Touches, no excess, no sibling poaching
[Build gate] PASSED (full suite, orchestrator-run) — 1 failure, tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied, the known pre-existing one; no regressions. Duration not captured (output was piped, which also masked pytest's exit code — rerun without a pipe to record it).
[Review 1/3] score 7.5 — 0 critical, 1 important, 3 minor. Below min_score 8 -> fix cycle.
[Review sync] 1 report -> meta/review/
[Mutation] 8 mutants, 7 killed, 1 SURVIVED. M5 (delete the sentence/onsubmit rewiring at generated_puzzles.html:175-179) leaves all 20 new tests plus CARD-068/CARD-100/admin-review green. That is half the bug the card exists to fix: the button correctly enables, then confirms "Delete all 0 rejected puzzles" from the stale server-rendered digit.
[Review] AC-1 is half-verified: the enable half is pinned, the confirmation-names-1 half is implemented but uncovered. AC-2/3/4 met and verified.
[Guard] G-1..G-4 all hold. G-1 verified empirically against installed werkzeug 3.1.8 / flask 3.1.3, not from the claim: absent -> 0,0; */* -> 1,1; browser header -> 0.8,1; "application/json, */*" -> 1,1 — all four redirect. M1 (> -> >=) killed, so the strictness is pinned.
[Review] CARD-068's window test confirmed genuinely still testing, not accommodated: the discriminating case is /reject-all, whose enabled button has no `disabled` in its 400-char window.
[Traceability defect] The card's Architecture context claims FR-026, FR-027 (batch review). In requirements.yml FR-026 is line-logic difficulty scoring and FR-027 is silhouette binarisation. No FR covers the batch-review surface — this is untraced scope carried under two misleading ids. Route: architect station, not this card.
