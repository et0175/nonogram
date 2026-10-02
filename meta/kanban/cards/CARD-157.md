# CARD-157: Read a book's puzzles in one query, not one session per puzzle

**Status:** ready
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** —
**Worktree:** —
**Source:** CARD-122 F-006, CARD-124 follow-up, CARD-126 F-002 (backlog); code re-read on main beaecdd, 2026-10-02
**Idea:** —
**Wave:** 30
**Depends on:** CARD-156
**Touches:** src/nonogram/admin/puzzle_review.py, src/nonogram/admin/app.py, src/nonogram/admin/book_manager.py, tests/test_puzzle_review_bulk_read.py (new)
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

In DB mode, `PuzzleReviewService.get_puzzle` (`puzzle_review.py:1096`) opens a new
session for every call. Three book paths call it once per puzzle:

| Path | Where | Cost on a 150-puzzle default-plan book |
|---|---|---|
| Book selection: `_selected_cells` | `app.py:3179` | one session per member + per ticked puzzle, up to ~300 per render |
| A book's status change re-reads its selection | via `BookManager._selection_records` | ~150 per change |
| Arrange/order: `_tier_of` → `_stored_tier` | `book_manager.py:1662`, :1699 | ~150 per arrow click; called from :1264, :1526, :1656, :1737 |

## What to do

1. Add `PuzzleReviewService.get_puzzles(ids) -> Dict[str, record]`: one session,
   one `WHERE id IN (…)` query, returning the same record shape `get_puzzle`
   returns. Ids that don't match or aren't UUIDs are left out of the result
   instead of raising, matching how each caller handles a missing record today.
   Memory mode reads from the dict.
2. Use it in all three paths. `_tier_of` keeps its `known=` behaviour.

**Read this before writing the query.** The obvious one-query fix is wrong:
filtering by `puzzles.book_id` reads the book-membership **mirror**, which
`BookManager` writes only when it was given a puzzle store (CARD-122 Fix 1
notes). The bulk read must go by **id**, taking the ids from the book's own
`puzzle_ids` plus the ticked ones, exactly as each caller does now. ADR-0033/R1:
book assembly may write the mirror, but nothing reads membership from it.

## Acceptance criteria

- **AC-1:** `get_puzzles` returns the same records as calling `get_puzzle` on
  each id, for a mix of present, absent and malformed ids, in both memory and
  DB mode.
  *test: PropertyTest_BulkRead_MatchesPerIdReads (seeded corpus, at least 200 cases)*
- **AC-2:** Rendering book selection, changing a book's status, and moving a
  puzzle on the arrange screen each open a bounded number of sessions that
  doesn't grow with the book's size.
  *test: TestBookPaths_SessionCountDoesNotScaleWithBookSize*
- **AC-3:** A book whose `puzzles.book_id` mirror is stale or empty still shows
  its full membership on all three paths.
  *test: TestBulkRead_IgnoresTheMembershipMirror*

## Guardrails

- G-1: Don't read membership from `puzzles.book_id` (ADR-0033/R1).
- G-2: Screen output on all three paths is unchanged; their existing tests stay
  green without edits.
- G-3: No schema change, no new index unless measured as needed.

## Architecture context

- **ADR:** ADR-0033/R1, ADR-0031 (tiers are read from the row, never re-derived)
- **Components:** COMP-009
- **Trace:** meta/architecture/trace.yml

## Worktree notes

- [Origin] Three cards each left their own N+1 on the backlog. They share one
  missing method. Cut on 2026-10-02.
- [Order] Depends on CARD-156 so the DB-mode tests here run against a fixture
  that doesn't drop tables underneath them.
