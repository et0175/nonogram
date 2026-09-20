# CARD-101: Reordering a book's puzzles and naming them do nothing in DB mode

**Status:** ready
**Priority:** P1
**Category:** bugfix
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/101-json-columns-are-not-mutable
**Worktree:** —
**Source:** found 2026-09-20 while fixing `remove_puzzle_from_book` for CARD-100
**Idea:** —
**Wave:** 1
**Depends on:** CARD-100 (the same bug, in the one method that card had to fix)
**Touches:** src/nonogram/admin/book_manager.py (`move_puzzle_up`, `move_puzzle_down`, `reorder_puzzles`, `set_puzzle_title`), possibly src/nonogram/db/models.py (the JSON columns), tests
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why

`Book.puzzle_ids` and `Book.puzzle_titles` are plain JSON columns. SQLAlchemy
decides what to write by comparing object identity, so mutating the list or
dict **in place** and assigning it back to the same attribute is not a change
as far as the session is concerned, and the `commit()` writes nothing.

Four methods in `BookManager` do exactly that::

    puzzle_ids = book_row.puzzle_ids or []     # the column's own list
    puzzle_ids[i], puzzle_ids[i-1] = ...       # mutated in place
    book_row.puzzle_ids = puzzle_ids           # assigned back: same object

So in DB mode — which is production — **moving a puzzle up or down in a book,
reordering a book, and setting or clearing a puzzle's title all silently do
nothing.** The request succeeds, the page re-renders from the unchanged row,
and the owner sees their change vanish.

`add_puzzles_to_book` was never affected: it builds a new list by
concatenation (`existing + new`), which is a different object.

CARD-100 hit this in `remove_puzzle_from_book` — a puzzle could not be taken
out of a book in DB mode — and fixed that one method, because its AC-2 needed
it. The other four are the same bug and are left here deliberately rather than
fixed unverified in a card about something else.

**Not yet confirmed against a running Postgres.** The reasoning above and
CARD-100's measurement are both from SQLite; the identity-comparison behaviour
is SQLAlchemy's, not the driver's, so it should hold, but the first task is to
reproduce it rather than to assume it.

## What to implement

1. **Reproduce each one** against a DB-backed `BookManager` before changing
   anything: move up, move down, reorder, set a title, clear a title.
2. **Fix them.** Two options, and the card should pick one and say why:
   - **(a) Build a new object at each assignment**, as CARD-100 did for
     removal. Local, obvious, and invisible in a diff — the next person to
     write `book.puzzle_ids.append(...)` reintroduces it.
   - **(b) Make the columns `MutableList`/`MutableDict`** in
     `db/models.py` so in-place mutation is tracked everywhere at once. One
     change, protects code not yet written, and touches every reader of those
     columns — so it needs the whole book suite run in DB mode, not just
     these four methods.
3. **A test that fails for the right reason.** Each fix needs a DB-mode test
   that reads the row back through a *new* session, since the identity problem
   is invisible while the original object is still in the identity map.

## Acceptance criteria

- **AC-1** — moving a puzzle up, then reading the book back in a new session,
  shows the new order; likewise down, and `reorder_puzzles`.
- **AC-2** — setting a puzzle's title, and clearing it, survive a new session.
- **AC-3** — every book operation is exercised in DB mode, not only
  in-memory; the existing book tests run in both.
- **AC-4** — whichever option is taken, a test would fail if someone
  reintroduced the in-place pattern.

## Guardrails

- G-1: No data repair here — this card stops new losses; it cannot recover an
  order the owner already set and lost.
- G-2: Admin-only; no edits under `sourcing/`, `orchestrator.py`, `cli.py`.
- G-3: If option (b) is taken, the whole book and puzzle suite runs in DB mode
  before it is called done — mutation tracking changes when writes happen, not
  just whether.
- G-4: Commit only your own files — explicit pathspecs.

## Architecture context

- **FR:** — (admin books)
- **Components:** the admin panel's book manager
- **Trace:** none
