# CARD-066: Filter the puzzle review by status (draft / approved / rejected / in book)

**Status:** done
**Priority:** P3
**Category:** feature
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/066-review-status-filter
**Worktree:** ../PythonProject4-CARD-066
**Source:** owner, 2026-09-12: "On «Filter review and curation» I'd like to add «Filter by status (accepted/rejected/draft)»"
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/admin/app.py (the `/puzzles` route), src/nonogram/admin/templates/puzzles_list.html, tests
**Review score:** 9.5
**Started:** 2026-09-12T04:50:20Z
**Closed:** 2026-09-12T05:30:00Z
**Actual:** 0.25d
**Merge commit:** d07f2a2
**Blocked by:** —

## Why

The Puzzle Review page filters by date, book, name, size, difficulty and
quality, but not by status, so there is no way to list "everything I still
have to look at" (draft) or "what I rejected". The plumbing already exists:
`PuzzleFilter.status` is a field (`puzzle_review.py:31`) and the book
page uses it (`status="approved"`); the `/puzzles` route simply never reads
the parameter (confirmed 2026-09-12).

Statuses are `draft`, `approved`, `rejected`, `in_book`
(`PuzzleStatus`, `puzzle_review.py:14-20`).

## What to implement

1. `/puzzles` reads `status` from the query string and passes it to
   `PuzzleFilter`, the way `difficulty` is handled today.
2. A "Status" `<select>` in the filter form: "Any" plus the four statuses,
   keeping the current selection like the Difficulty control does. Label the
   options in the page's own words: Draft, Approved, Rejected, In book.
3. **Carry it through pagination.** `puzzles_list.html`'s
   `preserve_filters` macro (line 3-5) lists every filter in the page links;
   `status` has to be added, or paging silently drops the filter. This is
   the one part that is easy to miss and hard to notice.
4. An unknown status value (e.g. `?status=nonsense`) must not 500. Decide
   and state which: ignore it, or show the page's "Filter error" message the
   way an invalid size does.

## Acceptance criteria

- **AC-1** — `/puzzles?status=draft` lists only draft puzzles; the same for
  approved, rejected and in_book; with no `status` the list is unchanged
  from today (all statuses).
- **AC-2** — the rendered form marks the current status as selected, and
  "Any" when none is set.
- **AC-3** — the pagination links (First, Previous, the numbers, Next, Last)
  keep `status`, asserted on a rendered page with more than one page.
- **AC-4** — an unknown status behaves as decided in step 4, with no 500,
  pinned by a test.
- **AC-5** — the other filters, the sort and "Per Page" still work together
  with a status filter (one test combining two filters).

## Guardrails

- G-1: Do not change `PuzzleFilter`'s semantics or the store's filtering;
  this card only routes an existing field.
- G-2: Do not touch the book page's own status filtering
  (`/book/<id>/select-puzzles` passes `status="approved"` deliberately).
- G-3: Admin-only; no edits under `sourcing/`, `orchestrator.py`, `cli.py`.

## Worktree notes

[Env] forge 2026.8.17 (no `meta/.skills.yml`, so no min_version comparison).
Built on `e6a5cd5`.

**The store needed no change.** It already filters by status in both modes —
in memory at `puzzle_review.py:350`, in the database at `415-416` — which is
why the book page's `status="approved"` works. This card is route plus
template only.

**Route** (`/puzzles`): reads `status`, passes it to `PuzzleFilter`, and
hands the template the list of valid statuses. The list is
`_PUZZLE_STATUSES`, derived from the `PuzzleStatus` enum, so the page cannot
drift from the store the way the preset tables did (CARD-065).

**Unknown status (step 4's open decision): report and ignore.** A value that
is not a status flashes "Unknown status 'x' — showing every status instead"
and the list is unfiltered. Filtering on it would show an empty page that
reads as "nothing matches your other filters", which is the more misleading
of the two failures. It cannot 500.

**Template**: a Status select (Any plus the four statuses, labelled from the
value, so `in_book` reads "In book"), and `status` added to the
`preserve_filters` macro — without that, paging drops the filter. The error
branch also passes `statuses`, or the select would fail to render on a
filter error.

**Tests** — `tests/test_card_066_status_filter.py`, 8 tests: each status
lists only its own puzzles; no status lists all; the form offers every
status and marks the current one; the pagination links keep `status` (with
"Page 1 of 3" proving the filter applied before paging); an unknown status
is reported, ignored and leaves the select unmarked; status combines with
the size filter.

**Red check**: against `main`'s `src/`, 7 of the 8 fail; the one that passes
is the "no status lists everything" pin, which is unchanged behaviour.

**Tests run**: the new file plus `test_puzzles_list_pagination`,
`test_card_063_limits`, `test_card_064_thin_pictures`,
`test_card_065_follow_ups`, `test_puzzle_review`, `test_web_server` and
`test_cli`: 359 passed. Commit `5ee603c`.

[Review 1/3] Score: 8.5 — crit: 0, imp: 0, minor: 3
[Review sync] 1 report(s) → meta/review/ (20260912T050613Z-CARD-066-cycle1.yml)
[Adversarial] no gating findings to verify (0 critical, 0 important)
Cycle 1 summary (forge:review, independent agent): AC-1..AC-5 and G-1..G-3
held.
- AC-3 checked on a rendered page 3 of 5 with seven filters set: all eight
  links carry `status` and every other filter; removing `status` from the
  macro fails a test.
- AC-4 checked against empty, `Approved`, `APPROVED`, `+approved`, a
  repeated parameter, a 20,000-character value, `%00` and `<script>` (all
  200, flash rendered by `base.html`).
- Full suite: 2802 passed / 37 failed vs base 2794 / 39 — no new failures.
- Mode covered: in-memory only (no Postgres reachable), so the DB filter
  path is unverified here.
Minors, all fixed in the delta below:
- the enum-derivation was not pinned: hardcoding today's four statuses in
  the template left the suite green (the code *is* enum-derived — a fifth
  member rendered — but nothing failed when it wasn't);
- no test provoked the route's `except ValueError` branch: dropping
  `statuses` there degrades the select to "Any" silently, a 200 that quietly
  loses the filter. My note called it a render failure; the reviewer is
  right that it degrades instead, which is worse and needs the test;
- `in_book` had no listing test, though `mark_in_book()` reaches it.

[Fix delta after cycle 1] Three tests added, no production change:
- `test_ac2_the_options_come_from_the_status_enum` monkeypatches the route's
  status list with an extra value and asserts the form renders it;
- `test_ac4_the_filter_error_page_still_offers_every_status` provokes the
  error branch with `?size=999` and asserts the select is complete;
- `test_ac1_in_book_puzzles_can_be_listed` marks a puzzle in a book and
  filters on `in_book`.
Delta commit `a7e1060`; the file plus `test_puzzles_list_pagination` and
`test_puzzle_review`: 45 passed. Mutation check in a scratch copy (the
worktree untouched): all 3 killed — the template hardcoding the four
statuses (1 test fails), the error branch dropping `statuses` (1), and the
route ignoring the parameter (6). The first two are exactly the mutants that
survived cycle 1.

[Review 2/3] Score: 9.0 — crit: 0, imp: 0, minor: 1 (confirmation mode, delta 5ee603c..a7e1060)
[Review sync] 1 report(s) → meta/review/ (20260912T051946Z-CARD-066-cycle2.yml)
[Adversarial] no gating findings to verify (0 critical, 0 important)
Cycle 2 summary: pure confirmation. AC-1..AC-5 re-verified (the delta shares
their file, so nothing was carried); G-1..G-3 carried, the delta being one
test file with no `src/` path. The reviewer ran the three mutants itself:
the template hardcoding the statuses, the error branch dropping `statuses`
and the route ignoring the parameter — all killed, and it confirmed
`?size=999` genuinely reaches `except ValueError` (raised at
`puzzle_review.py:311`; "Filter error" is flashed nowhere else on this
page). It also checked the monkeypatch does not leak, probing first, last,
reversed and isolated.
Minor: the enum pin only covered *template ← route*. The test monkeypatches
the route's list and never touches `PuzzleStatus`, so replacing the
derivation in `app.py` with a literal tuple survived (45 passed). The drift
had moved rather than closed.
Note: one of the reviewer's invocations accidentally collected the full
suite (an unquoted empty shell variable) while the CARD-067 review was
running; the extra failure there is in the port-binding web tests and is
recorded as a tooling failure, not attributed to this card.

[Fix delta after cycle 2] `test_ac2_the_route_takes_its_statuses_from_the_enum`
asserts the route's list equals the enum's values, and that this file's own
`STATUSES` constant is not stale. It compares values, so a literal tuple of
today's four statuses still passes — that mutant is behaviour-identical
today — but the failure that matters does fail: adding `PuzzleStatus.X`
while the page keeps the old list.
Delta commit `60fcbbc`; the file plus `test_puzzle_review`: 33 passed.

[Review 3/3] Score: 9.5 — crit: 0, imp: 0, minor: 0 (confirmation mode, delta a7e1060..60fcbbc)
[Review sync] 1 report(s) → meta/review/ (20260912T052342Z-CARD-066-cycle3.yml)
[Adversarial] no gating findings to verify (0 critical, 0 important)
Cycle 3 summary: the Minor is closed. The reviewer killed the new assertion
from both directions in scratch copies — `PuzzleStatus` gaining `ARCHIVED`
with the route left derived fails on the staleness guard, and the same plus
`app.py` hardcoded to the old four fails on the first assertion — so the
drift is caught at the moment it becomes a defect. It explicitly accepted
not killing the literal-tuple mutant: a literal of today's four values is
behaviour-identical now, and forcing its death would mean asserting *how*
the value is computed (AST inspection of one line), brittle against any
refactor and buying nothing over value equality.
Delta verified as one +15-line hunk with no existing test touched.

[Merge gate] The card's own file plus `test_puzzles_list_pagination`,
`test_puzzle_review` and `test_cli`: 135 passed, no failures.
[Done] Merged to `main` as `d07f2a2`; worktree and branch removed.