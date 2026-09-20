"""CARD-100 — repair the half of book membership that was never written.

The one question this module answers: *which puzzles does a book say it holds,
and do those puzzles agree?* — and, on the write path, it makes them agree.

Why a repair is needed rather than just a fix
---------------------------------------------
Membership is two facts: ``Book.puzzle_ids`` on the book, and ``book_id`` on
each puzzle. Until CARD-100 only the first was ever written —
``BookManager.add_puzzles_to_book`` never touched the puzzle row, and
``PuzzleReviewService.mark_in_book``, the only code that did, had no production
caller. Every guard in the panel reads the second fact, so for every book made
before this card the guards see nothing: "Approve all" rewrites the status of a
puzzle a book is built on, and "Delete rejected" deletes it, leaving the book
pointing at an id that is no longer in the store.

Fixing the writers stops new books from being born broken. It does nothing for
the ones already on disk. This module is for those.

What it does to one book
------------------------
Reads ``Book.puzzle_ids``, and for each id compares what the book says with
what the puzzle says::

    the puzzle already names this book   -> already   (nothing to do)
    the puzzle names no book             -> repaired  (write it)
    the puzzle names a different book    -> contested (report, never guess)
    the store has no such puzzle         -> missing   (report; see below)

**Contested** is only possible because of the very bug this repairs: with the
column unwritten, nothing stopped a puzzle being added to two books, and the
book builder's "unassigned" filter offered it both times. Two books claim it
and this module cannot know which is right, so it reports the pair and writes
nothing. An operator resolves it by removing the puzzle from one of them.

**Missing** is a ghost — a book listing a puzzle the bulk actions already
deleted. This module reports them and does not touch them: removing the id
would edit a book's contents, which is a decision about a book, not a repair
of a column (G-1). It is the number that says how much damage was done before
the repair landed.

Dry run
-------
:func:`backfill` takes ``dry_run`` and runs the identical loop either way; it
decides only whether the writes are issued, so the report and the write can
never disagree — the shape CARD-077's ``regrade`` established for the same
reason.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class BackfillOutcome:
    """What a run found, and what it did about it."""

    dry_run: bool
    books_seen: int = 0
    #: Puzzles whose ``book_id`` was written (or would be, on a dry run).
    repaired: int = 0
    #: Puzzles that already named the right book.
    already: int = 0
    #: ``(puzzle_id, (book_id, other_book_id))`` — two books claim it.
    contested: tuple[tuple[str, tuple[str, str]], ...] = ()
    #: Ids a book lists that the store does not have.
    missing: tuple[str, ...] = ()

    @property
    def needs_an_operator(self) -> bool:
        """Whether anything here cannot be settled by running this again."""
        return bool(self.contested or self.missing)

    def __str__(self) -> str:
        verb = "would repair" if self.dry_run else "repaired"
        parts = [
            f"{self.books_seen} book(s): {verb} {self.repaired}, "
            f"{self.already} already correct"
        ]
        if self.contested:
            parts.append(f"{len(self.contested)} claimed by two books")
        if self.missing:
            parts.append(f"{len(self.missing)} listed but not in the store")
        return "; ".join(parts) + "."


def backfill(book_manager, puzzle_store, *, dry_run: bool) -> BackfillOutcome:
    """Make every puzzle a book lists agree that the book holds it.

    Args:
        book_manager: the :class:`BookManager` whose books are read.
        puzzle_store: the :class:`PuzzleReviewService` whose rows are written.
        dry_run: when true, nothing is written and the outcome reports what
            would have been.

    Returns:
        A :class:`BackfillOutcome`. Writes nothing but ``Puzzle.book_id``, and
        never edits a book (G-1).
    """
    repaired: list[tuple[str, str]] = []
    already = 0
    contested: list[tuple[str, tuple[str, str]]] = []
    missing: list[str] = []
    books = book_manager.get_all_books()

    # Which books claim each puzzle, gathered before anything is judged. A
    # puzzle listed by two books is the case this cannot settle, and with the
    # column empty — the state it is repairing — the conflict is visible only
    # by looking across all the books first.
    listings: dict[str, list[str]] = {}
    for book in books:
        for puzzle_id in book.puzzle_ids or []:
            claims = listings.setdefault(puzzle_id, [])
            if book.book_id not in claims:
                claims.append(book.book_id)

    for puzzle_id, claims in listings.items():
        puzzle = puzzle_store.get_puzzle(puzzle_id)
        if puzzle is None:
            missing.append(puzzle_id)
            continue
        if len(claims) > 1:
            contested.append((puzzle_id, (str(claims[0]), str(claims[1]))))
            continue
        (book_id,) = claims
        held_by = puzzle.get("book_id")
        if held_by is None:
            repaired.append((puzzle_id, book_id))
        elif str(held_by) == str(book_id):
            already += 1
        else:
            contested.append((puzzle_id, (str(held_by), str(book_id))))

    if not dry_run:
        for puzzle_id, book_id in repaired:
            puzzle_store.assign_to_book([puzzle_id], book_id)

    return BackfillOutcome(
        dry_run=dry_run,
        books_seen=len(books),
        repaired=len(repaired),
        already=already,
        contested=tuple(contested),
        missing=tuple(missing),
    )


def _services():
    """The store and book manager for whatever ``DATABASE_URL`` points at.

    Built the way ``create_app`` builds them, so the command repairs the same
    database the panel reads. Without ``DATABASE_URL`` there is nothing
    durable to repair — in-memory books do not survive the process — and the
    command says so rather than reporting a cheerful zero.
    """
    import os

    from nonogram.admin.book_manager import BookManager
    from nonogram.admin.puzzle_review import PuzzleReviewService

    if not os.getenv("DATABASE_URL"):
        raise SystemExit(
            "DATABASE_URL is not set. There is no stored database to repair: "
            "in-memory books live only as long as the admin process."
        )
    from nonogram.db import session_scope

    store = PuzzleReviewService(session_factory=session_scope)
    return BookManager(session_factory=session_scope, puzzle_store=store), store


def main(argv=None) -> int:
    """``python -m nonogram.admin.book_membership`` — report, or repair.

    Reports by default. Writing takes ``--write`` and says so first, because
    this is a one-shot repair of live data and the shape of a mistake here is
    "I meant to look".
    """
    import argparse

    parser = argparse.ArgumentParser(
        prog="python -m nonogram.admin.book_membership",
        description=(
            "Repair book membership: give every puzzle a book lists the "
            "book_id that the panel's guards read (CARD-100)."
        ),
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="apply the repair; without it nothing is written and the same "
             "loop only reports what it would do",
    )
    args = parser.parse_args(argv)

    book_manager, store = _services()
    outcome = backfill(book_manager, store, dry_run=not args.write)
    print(outcome)

    for puzzle_id, (one, other) in outcome.contested:
        print(f"  claimed by two books, not repaired: {puzzle_id} ({one}, {other})")
    for puzzle_id in outcome.missing:
        print(f"  listed by a book but not in the store: {puzzle_id}")

    if outcome.dry_run and outcome.repaired:
        print("\nNothing was written. Re-run with --write to apply this.")
    if outcome.needs_an_operator:
        print(
            "\nSome rows need a decision this command will not make for you: a "
            "puzzle two books claim is resolved by removing it from one, and a "
            "puzzle a book lists that no longer exists was deleted before this "
            "repair landed."
        )
    return 0


if __name__ == "__main__":  # pragma: no cover - operator entry point
    raise SystemExit(main())
