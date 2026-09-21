# CARD-101: Reordering a book's puzzles and naming them do nothing in DB mode

**Status:** done
**Priority:** P1
**Category:** bugfix
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** red -> green -> mutation check (5 mutants, 4 caught, 1 reported)
**Branch:** card/101-json-columns-are-not-mutable
**Worktree:** ../PythonProject4-CARD-101
**Source:** found 2026-09-20 while fixing `remove_puzzle_from_book` for CARD-100; measured against a real database before starting, which corrected two of this card's own claims
**Idea:** —
**Wave:** 1
**Depends on:** CARD-100 (the same bug, in the one method that card had to fix)
**Touches:** src/nonogram/admin/book_manager.py (`move_puzzle_up`, `move_puzzle_down`, `set_puzzle_title`), possibly src/nonogram/db/models.py (the JSON columns), tests
**Review score:** — _(merged without a review cycle, at the owner's call)_
**Started:** 2026-09-21
**Closed:** 2026-09-21
**Actual:** 0.5d
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

### Decision taken on starting, 2026-09-21

**Option (b), the owner's call: `MutableList`/`MutableDict` on the columns.**
The measurement is the argument. The pattern that loses data is the one that
looks most obviously correct, it is invisible in a diff, and it did not even
fail consistently — a title written while the column was still `NULL`
persisted, because `or {}` built a new dict. A rule that must be remembered at
every call site had already been forgotten at four of them, and CARD-100 found
a fifth.

### Delivered 2026-09-21

**Three columns on `Book` are mutation-tracked**: `puzzle_ids`,
`puzzle_titles`, `book_metadata`. That is the whole fix — **not one line of
`book_manager.py` changed**, and every method that was losing writes now keeps
them. The measured table from the top of this card, re-run against the fix:

| operation | before | after |
|---|---|---|
| `move_puzzle_up` | no | **yes** |
| `move_puzzle_down` | no | **yes** |
| `set_puzzle_title`, changing | no | **yes** |
| `set_puzzle_title`, clearing | no | **yes** |
| `reorder_puzzles` | yes | yes |
| `add_puzzles_to_book` | yes | yes |

**A third symptom, found while writing the tests.** `book_metadata` had the
same fault: `add_puzzles_to_book` assigns `book_row.book_metadata['page_count']`
in place, so a book's page count stopped following its puzzles after the first
add. Fixed by the same wrapping, and pinned by
`test_the_page_count_follows_the_puzzles`.

**`Puzzle.grid`, `clues_rows` and `clues_cols` are deliberately left plain**,
with a comment saying so. They are written whole and never edited in place, and
`MutableList` tracks only *top-level* mutation — on a list of rows it would
report nothing while a cell changed, which is worse than not claiming to track
them at all.

### A mutant that survived, and why it is not a gap

Five mutants; four caught. The fifth reverted `default=list`/`default=dict` to
`default=[]`/`default={}` and **nothing failed** — so the change it reverses
has no observable behaviour. The worry it was written for (every new row
handed the *same* container, which matters far more once those containers are
tracked) turns out not to arise: the value is serialised per insert and rebuilt
per load. The defaults keep the factory form as the one that cannot be misread,
and the card says plainly that this is tidiness rather than a fix. The test
written for it stays, pinning the property itself — one book's edits never
reach another — rather than the reasoning that turned out to be wrong.

### Tests

`tests/test_card_101_mutable_json_columns.py`, 15 tests, every one DB-backed
and reading the row back **through a fresh session** — the bug is invisible
while the original object is still in the identity map, because the in-memory
object does hold the change. Three title paths rather than one, because the
first write always worked and hid the other two.

The regression guard is `test_a_list_column_mutated_in_place_is_written` and
its dict twin: they perform the pattern that used to lose data and assert it
now persists, so unwrapping a column fails the suite (AC-4).

**Full suite: 3,593 passed, 0 failed**, 26 skipped, one deselection (G-3: the
whole suite, not only the new file, since mutation tracking changes *when*
writes happen and not merely whether).

### Still measured only against SQLite

As when the card was opened. The identity comparison is SQLAlchemy's behaviour
rather than the driver's, so it should hold on Postgres, but nothing here has
been run against one.
