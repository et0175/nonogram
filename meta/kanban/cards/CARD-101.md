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
**Source:** found 2026-09-20 while fixing `remove_puzzle_from_book` for CARD-100; measured against a real database before starting, which corrected two of this card's own claims
**Idea:** —
**Wave:** 1
**Depends on:** CARD-100 (the same bug, in the one method that card had to fix)
**Touches:** src/nonogram/admin/book_manager.py (`move_puzzle_up`, `move_puzzle_down`, `set_puzzle_title`), possibly src/nonogram/db/models.py (the JSON columns), tests
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

Three methods in `BookManager` do exactly that::

    puzzle_ids = book_row.puzzle_ids or []     # the column's own list
    puzzle_ids[i], puzzle_ids[i-1] = ...       # mutated in place
    book_row.puzzle_ids = puzzle_ids           # assigned back: same object

### Measured 2026-09-20, before starting — and two of this card's claims were wrong

Run against a SQLite-backed `BookManager`, reading every result back through a
fresh session:

| operation | persists? |
|---|---|
| `move_puzzle_up` | **no** |
| `move_puzzle_down` | **no** |
| `set_puzzle_title`, first title on a book | yes |
| `set_puzzle_title`, **changing** an existing title | **no** |
| `set_puzzle_title`, **clearing** a title | **no** |
| `reorder_puzzles` | yes |
| `add_puzzles_to_book` | yes |

So the owner-facing symptoms are: **the arrange page's up and down buttons do
nothing**, and **a puzzle in a book can be named once and then never renamed
or un-named**.

Two corrections to what this card asserted when it was opened, both from not
having run it:

- **`reorder_puzzles` is fine.** It assigns the *caller's* list
  (`book_row.puzzle_ids = puzzle_ids`, the argument), which is a different
  object from the column's own, so the change is seen. It is listed above as
  passing and is out of scope.
- **`set_puzzle_title` is not simply broken** — it works exactly once per
  book. `puzzle_titles = book_row.puzzle_titles or {}` builds a *new* dict
  while the column is still `NULL`, and that first assignment persists; every
  write after that mutates the dict the column now holds. A bug that works the
  first time is the reason this needs a test per path rather than one per
  method.

`add_puzzles_to_book` was never affected: it concatenates (`existing + new`).

CARD-100 hit this in `remove_puzzle_from_book` — a puzzle could not be taken
out of a book in DB mode — and fixed that one method, because its AC-2 needed
it.

**Still not confirmed against a running Postgres.** The measurement above is
SQLite. The identity comparison is SQLAlchemy's behaviour rather than the
driver's, so it should hold, but nothing here has been run against Postgres.

## What to implement

1. ~~Reproduce each one~~ — **done before starting**, see the table above.
   Reproduce once more against Postgres if one is to hand, since everything
   measured so far is SQLite.
2. **Fix them.** Two options, and the card should pick one and say why:
   - **(a) Build a new object at each assignment**, as CARD-100 did for
     removal. Local and obvious, but invisible in a diff — the next person to
     write `book.puzzle_ids.append(...)` reintroduces it, and the measurement
     above shows this bug can look like it works.
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
  shows the new order; likewise down. `reorder_puzzles` already passes and
  keeps passing.
- **AC-2** — setting a title, **changing** it, and **clearing** it each
  survive a new session — three paths, because the first one already worked
  and hid the other two.
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
