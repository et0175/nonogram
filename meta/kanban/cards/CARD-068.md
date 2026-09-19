# CARD-068: Batch results — the per-puzzle Delete, and bulk actions that say what they did

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d _(was 0.5d for the whole card; most of it shipped outside the board — see Re-cut)_
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/068-batch-results-bulk-actions
**Worktree:** —
**Source:** owner, 2026-09-12: "I'd like «delete» button on the generated puzzles last Batch generation step, then «Accept all», «reject all» and «delete rejected»"
**Idea:** —
**Wave:** 1
**Depends on:** CARD-099 (merged 2ac201a) — same page; the cards now sit inside per-picture sections
**Touches:** src/nonogram/admin/templates/generated_puzzles.html, src/nonogram/admin/app.py (the delete route's return, the bulk flashes), src/nonogram/admin/puzzle_review.py (bulk helpers return what they skipped), tests
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Re-cut 2026-09-19 — three quarters of this card is already on main

Checked against `main` at `25446fd` before re-opening. Commit **`db4e0dc`**
(2026-09-14, "fix(admin): review actions keep the list's place, live size
prediction, bulk batch curation") shipped most of this card directly to `main`
without a card, while the card sat in Ready — the same thing that happened to
CARD-067. What it delivered, verified by reading the code and the tests:

- **Accept all / Reject all / Delete rejected** exist as POST routes
  (`/batch/<id>/approve-all|reject-all|delete-rejected`), are wired into the
  page's "Whole batch" panel, and land back on the batch page (item 2, AC-2's
  first half).
- **They act on the whole batch**, not on what the page rendered:
  `set_batch_status` and `delete_rejected_in_batch` query by `batch_id`
  (AC-2, AC-4).
- **A puzzle in a book is never touched** by any of them, and no action
  reaches another batch's puzzles — both pinned by tests in
  `tests/test_admin_review_actions.py` (G-1, AC-4).
- **Deletion lives in the store, in both modes.** `delete_puzzle`,
  `set_batch_status` and `delete_rejected_in_batch` each have an in-memory and
  a DB branch, so item 3 of the original card is done and the route no longer
  talks to `session_scope` itself.

**AC-2's second half is retired, not deferred.** It asked for the bulk buttons
to act beyond the 100 puzzles the page renders and to say so when the batch is
bigger. CARD-088 capped a batch at `MAX_BATCH_COUNT = 50`, and both
`create_batch` call sites validate against it — an image batch on its planned
puzzle count (CARD-069), a random batch on its requested count. A batch cannot
hold more than 50 puzzles, so the page's limit of 100 always shows all of them
and there is nothing for the button to warn about. The requirement was written
when the ceiling was 200.

## What is actually left

1. **The per-puzzle Delete button — the owner's first ask, and the one thing
   with no code at all.** `/puzzle/<id>/delete` exists, works in both modes and
   enforces both rules (rejected only, never in a book), but the batch page
   does not offer it: a card's actions are Approve, Reject, SVG and PDF. To
   curate a batch you still leave the page.
2. **The delete route goes to the wrong place from here.** It ends in
   `_back_to_puzzles_list()`, which honours a `return_batch` form field — the
   batch's own puzzle list posts one. The generated-puzzles page does not, so a
   delete from here would land the owner in the global library mid-batch.
   AC-1 says it returns to the same batch.
3. **The confirmations do not name a count** (AC-6). They read "Approve all
   puzzles in this batch?" whether that is 2 puzzles or 50 — which is the
   number that decides whether you mean it.
4. **The bulk actions do not report what they skipped** (AC-3). The store
   knows: `set_batch_status` passes over puzzles in a book and ones already in
   the target status, `delete_rejected_in_batch` passes over rejected puzzles
   in a book. All three flashes report one number, so "Deleted 3 rejected
   puzzle(s)" is what you see whether or not a fourth was held back by a book.
   Both helpers return a bare `int`; they need to return both numbers.
5. **AC-5 is half-tested.** The bulk tests run in in-memory mode only. The
   store branches are the ones that differ, so the DB branch of all three is
   currently unexercised — parametrise the way the store's own tests do.

## The open sub-decision (for the owner, before item 1 is built)

The original card flagged it and it is still open: **Delete is only reachable
from Rejected.** A puzzle must be rejected first, so removing one is two
clicks and a decision you cannot take back in one gesture.

- **(a) Keep the rule.** Delete appears on a card only once it is rejected —
  today it is revealed by the same fetch that flips the badge, so no reload.
  Safest, and it keeps one meaning for the button everywhere in the panel.
- **(b) Delete from any status except in-a-book.** One click from Draft.
  Matches the owner's words ("a «delete» button on the generated puzzles
  step") most literally, and widens what a mis-click destroys — on this page
  the cards are a grid of near-identical thumbnails.

**Recommendation: (a).** The batch page is where puzzles are judged quickly
and in bulk, which is exactly where a one-click irreversible delete is worst;
and "Reject all" followed by "Delete rejected" already gives a two-gesture
route to emptying a batch. If (a) proves annoying in real use, (b) is a
one-line change to the guard.

## Acceptance criteria

- **AC-1** — per-puzzle Delete removes a rejected puzzle from the store and
  the page returns to the same batch, not to the global list.
- **AC-3** — Delete rejected deletes exactly the batch's rejected puzzles that
  are not in a book, and reports both numbers ("3 rejected puzzles deleted, 1
  skipped: in a book"); Accept all and Reject all likewise say what they
  passed over.
- **AC-4** — no action deletes a puzzle that is in a book, and none touches
  another batch's puzzles. _(Holds today; keep it pinned.)_
- **AC-5** — every bulk action works in in-memory mode **and** in DB mode,
  parametrised.
- **AC-6** — each bulk button's confirmation names the count it is about, and
  a cancelled confirmation changes nothing.
- **AC-7** — Delete obeys whichever rule the owner picks above, and the button
  is not offered where the rule would refuse it.

## Guardrails

- G-1: Never delete a puzzle that is in a book, and never act across batches.
- G-2: Keep the existing per-puzzle Approve and Reject behaviour, including
  the `batch_id` redirect back to the batch page.
- G-3: Bulk actions are POSTs with confirmation — no destructive GET.
- G-4: Admin-only; no edits under `sourcing/`, `orchestrator.py`, `cli.py`.
- G-5: CARD-099's grouping stays intact — a Delete added to the card must not
  make one control stand for several puzzles, and the per-picture sections
  must survive a delete that empties one.
- G-6: Commit only your own files — explicit pathspecs.

## Architecture context

- **FR:** — (admin curation)
- **Components:** the admin panel's review surface
- **Trace:** none
