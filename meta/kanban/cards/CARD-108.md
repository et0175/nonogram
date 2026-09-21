# CARD-108: Deleting a book strands its puzzles in in-memory mode

**Status:** done
**Priority:** P2
**Category:** bugfix
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** red -> green -> mutation check (4 mutants, 3 caught, 1 reported)
**Branch:** card/108-delete-book-releases-its-puzzles
**Worktree:** ../PythonProject4-CARD-108
**Source:** found 2026-09-21 while confirming CARD-107's repair holds in both modes
**Idea:** —
**Wave:** 1
**Depends on:** —
**Touches:** src/nonogram/admin/book_manager.py (`delete_book`), tests
**Review score:** — _(merged without a review cycle, at the owner's call)_
**Started:** 2026-09-21
**Closed:** 2026-09-21
**Actual:** 0.25d
**Merge commit:** —
**Blocked by:** —

## Why

`BookManager.delete_book` removes the book and leaves its puzzles pointing at
it. In DB mode that is invisible from CARD-103 onward, because
`puzzles.book_id` carries `ON DELETE SET NULL` and the database does the work.
**In-memory mode has no foreign key and nothing does it**, measured on `main`
at `0f8330b`:

```
  booked                 : True
  after delete_book      : STILL POINTS AT book_000001
  puzzle still rejectable : False
```

The second line is the damage. CARD-100 made every in-book guard read
`book_id`, so a puzzle left pointing at a deleted book can no longer be
rejected, restored, approved, or deleted — by anything, ever. It is stranded.

This is precisely the outcome CARD-103 used to argue *against* `ON DELETE
RESTRICT`: *"would leave a deleted book's puzzles permanently unrejectable — a
worse hole than the one this closes."* The argument was right; it simply did
not notice that the other storage mode already had the hole.

## Why it matters even though production is DB mode

The two modes disagree about what deleting a book does, and in-memory is what
local development and most of the suite run on. A guard that behaves
differently depending on storage is the same class of problem as CARD-100's
original defect: a rule that holds in the place you test it and not in the
place it matters — here, inverted.

It also makes the fix in CARD-107 mode-dependent. `release_orphans` repairs
this state in either mode, but in DB mode it can only ever be cleaning up
history, while in memory mode it is cleaning up something still being created.

## What to implement

1. **`delete_book` releases its puzzles before removing the book**, in both
   branches — `puzzle_store.release_from_book(book.puzzle_ids)`. In DB mode
   the foreign key would do it anyway; doing it explicitly costs nothing, says
   what is meant at the point it happens, and removes the mode difference.
2. A manager with **no puzzle store** keeps working and warns, as
   `_mirror_onto_puzzles` already does for add and remove — the same
   arrangement, for the same reason.

## Acceptance criteria

- **AC-1** — after `delete_book`, its puzzles have `book_id` NULL in **both**
  storage modes, read back through a fresh session in DB mode.
- **AC-2** — those puzzles can then be rejected and deleted again; the guard
  does not outlive the book.
- **AC-3** — deleting one book does not release another's puzzles.
- **AC-4** — the puzzles themselves are not deleted, only released.

## Guardrails

- G-1: Do not delete a puzzle. This clears a column.
- G-2: Do not change `ON DELETE SET NULL`. The database doing it and the
  application doing it are belt and braces, and the belt stays.
- G-3: Commit only your own files — explicit pathspecs.

## Architecture context

- **FR:** — (admin books)
- **Components:** the admin panel's book manager
- **Trace:** none

### Delivered 2026-09-21

**`delete_book` releases its puzzles before the book goes**, in both branches.
In DB mode `ON DELETE SET NULL` had been doing it since CARD-103; in memory
mode nothing did. Both say it explicitly now, so the two modes cannot disagree
about what deleting a book means — which was the actual defect, more than
either branch's behaviour on its own.

**The red/green split was the card's own argument.** Before the fix: five tests
failed, **all of them in memory mode**, and every DB-mode test passed. A test
written against DB mode alone would have passed throughout and proved nothing.
That is why the file is parametrised over both.

**The damage, stated as the thing that must work:**
`test_a_released_puzzle_is_curatable_again` asserts that a puzzle is guarded
while its book holds it, and rejectable and deletable once the book is gone.
Before this card the guard outlived the book, so the puzzle could not be
rejected, restored, approved or deleted by anything — and no book existed to
remove it from.

**Also checked:** a released puzzle returns to the book builder's "unassigned"
list, a published book is still refused (and its puzzles are **not** released
when the refusal happens), deleting an unknown id changes nothing, and a
manager with no puzzle store still deletes the book and warns — the same
arrangement `_mirror_onto_puzzles` already had for add and remove.

### Mutation check — 3 of 4, and the fourth is the point of the design

Caught: the memory branch not releasing (5 tests — the original bug), the book
not actually being deleted, and a published book becoming deletable.

**Survived:** removing the explicit release from the **DB** branch. The foreign
key still clears the column, so the outcome is identical and no test can
distinguish them. That is precisely what the code comment claims — "belt to the
foreign key's braces" — so the surviving mutant confirms the reasoning rather
than exposing a gap. The call stays because it makes both modes state the same
intent, and because a database whose constraint is ever dropped (a `009`
downgrade) would otherwise silently revert to stranding puzzles.

**Full suite: 3,667 passed, 0 failed.**
