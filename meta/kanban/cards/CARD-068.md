# CARD-068: Batch results — the per-puzzle Delete, and bulk actions that say what they did

**Status:** review
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d _(was 0.5d for the whole card; most of it shipped outside the board — see Re-cut)_
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** red -> green -> mutation check (9 mutants, all caught)
**Branch:** card/068-batch-results-bulk-actions
**Worktree:** ../PythonProject4-CARD-068
**Source:** owner, 2026-09-12: "I'd like «delete» button on the generated puzzles last Batch generation step, then «Accept all», «reject all» and «delete rejected»"
**Idea:** —
**Wave:** 1
**Depends on:** CARD-099 (merged 2ac201a) — same page; the cards now sit inside per-picture sections
**Touches:** src/nonogram/admin/templates/generated_puzzles.html, src/nonogram/admin/app.py (the delete route's return and guard, the bulk flashes, the page's counts), src/nonogram/admin/puzzle_review.py (`BulkOutcome`, `batch_action_counts`), src/nonogram/admin/book_manager.py (`book_listing`), tests
**Review score:** —
**Started:** 2026-09-20
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

### Delivered 2026-09-20

**The Delete button (item 1, AC-1, AC-7).** Beside Approve and Reject on every
card, hidden until the puzzle is rejected — option (a), the owner's pick. The
form is rendered for every card rather than only the rejected ones, so the
fetch that flips the badge reveals it without a reload; approving hides it
again. A real POST, not the fetch its neighbours use: the page has to
re-render, or a deleted card would linger and its picture's section (CARD-099)
could outlive its last puzzle.

**Where Delete lands (item 2).** `?batch_id=` — the same parameter the Approve
and Reject forms beside it have always posted — returns to the batch instead
of dropping the owner into the global library mid-review. Without it the route
behaves exactly as before, which the review list depends on (G-2).

**The counts (item 3, AC-6).** Each bulk confirmation names its number:
"Approve all 5 puzzles in this batch?", "Delete the 1 rejected puzzle in this
batch? This cannot be undone." A button with nothing to do is disabled rather
than confirming its way to a no-op. The numbers come from
`batch_action_counts`, which applies the store's own rules, so the number on
the button and the number in the flash are two readings of one rule — pinned
by `test_the_promised_count_is_what_the_action_reports`, which clicks the
button and compares.

**The reports (item 4, AC-3, partly).** `BulkOutcome(changed, unchanged,
in_book)` replaces the bare `int` both helpers returned, and the flash says
"Approved 1 puzzle; 2 were already approved." A bare "Approved 1" on a batch
of three is the kind of count that sends the owner looking for the other two.

**AC-5.** The store's bulk operations are now exercised in both modes through
a parametrised `store` fixture.

### What this card does NOT do, and why (CARD-100)

AC-3's other half — "1 skipped: in a book" — is **not** built, at the owner's
call, and AC-4 is weaker than it reads. Found while starting this card and
demonstrated before writing a line of it: **the in-book guard does not fire
for real books.** `BookManager.add_puzzles_to_book` records membership in
`Book.puzzle_ids` and never touches the puzzle row; every guard here reads
`Puzzle.book_id`; and `mark_in_book`, the only code that writes it, has no
production caller — it is reached only from tests. So the number would be zero
however many puzzles a book actually lists, and a confident "0 left alone: in
a book" is worse than silence. `BulkOutcome.in_book` counts them anyway, so
the clause is one sentence away once CARD-100 makes the number true.

The sidebar's claim "Puzzles already in a book are not changed." is **removed**
for the same reason: it was the page asserting the thing that is not so.

**The one place this card does close the hole** is the button it adds. A
Delete the owner clicks is destructive and new, so the route asks
`book_manager.book_listing(puzzle_id)` — the side that actually records
membership — as well as the puzzle's own column. A scan, affordable for one
puzzle at a time, and precisely why it is not the answer for the bulk paths.

### Verified by eye

`~/Documents/nonogram-reviews/CARD-068/` — `batch-top.jpg` (the batch panel
with its counted buttons) and `delete-on-a-rejected-card.jpg`: `butterfly.png`
at two sizes, the approved 14x10 offering no Delete and the rejected 20x15
offering one beside its badge. `batch-review.html` is the rendered page.

### Tests

`tests/test_card_068_batch_curation.py`, 25 tests. The delete rules (rejected
only, never in a book by either reading, back to the batch), the page's
offer of Delete, the counted confirmations and the disabled empty button, the
reports, and the store's two modes side by side.

**Mutation check** — nine mutants: Delete ignoring the batch, Delete trusting
only the puzzle row, Delete offered on every card, the confirmation dropping
its count, the empty button left live, the report omitting what needed
nothing, the counts including booked puzzles, `delete_rejected_in_batch`
ignoring books, and `book_listing` always returning `None`. All nine caught —
the seventh only after its first run was found not to have applied (a
multi-line `perl` substitution without `-0`), which is its own small lesson
about trusting a mutant that reports "all passed".

**Full suite: 3,522 passed, 0 failed**, 26 skipped, one deselection
(`test_size_configuration_applied`, unrelated).

### A correction to CARD-099's record

That card's notes say "3,495 passed". The number was measured before its last
two tests were added (the upload-order pins that caught its surviving mutant),
so `main` at merge was 3,497. The suite was green at both counts; the figure
in the card is simply one measurement out of date.
