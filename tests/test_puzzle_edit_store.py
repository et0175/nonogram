"""CARD-245 — an edited grid is re-verified and re-graded by one solve, or it is not stored.

The store half. ``PuzzleReviewService`` had no update path at all before this
card (``add_puzzle``, ``rename_puzzle``, ``_set_status``, ``assign_to_book``,
and nothing that replaced a grid), so what is tested here is a *new write path
to* ``Puzzle.grid`` and the one refusal it must go through rather than around.

What each class pins
--------------------
AC-1  ``TestPuzzleEdit_StoresAndRederivesEverythingDerived``
AC-2  ``TestPuzzleEdit_RefusesZeroAndMultipleSolutions``
AC-3  ``TestPuzzleEdit_GradesFromTheProvingSolve``
AC-4  ``TestPuzzleEdit_RefusesAPuzzleThatIsInABook``
AC-5  ``TestPuzzleEdit_VerifyReturnsTheGradeWithoutStoring``
AC-6  ``TestPuzzleEdit_RefusesAnApproveWhoseGridMoved``
      ``TestPuzzleEdit_TheMemoIsReadThroughOneAccessor``     (cycle 1, F-011)
      ``TestPuzzleEdit_AProofDoesNotCrossGridExtents``       (cycle 1, F-001)
AC-7  ``TestPuzzleEdit_RefusesAMalformedGridBeforeSolving``
AC-8  ``TestPuzzleEdit_StampsTheEditAndKeepsTheQualityScore``
AC-9  ``TestPuzzleEdit_ARefusedEditLeavesNoStamp``
AC-10 ``TestPuzzleEdit_AnEditedPuzzleStillPassesTheQualityFilter``
G-1   ``TestPuzzleEdit_EveryGridWriteGoesThroughTheOneRefusal``
      — default-deny since review cycle 1 (F-002): every function in the
      module is a candidate grid writer unless it is *provably* read-only,
      and a candidate must reach the gate or be on a justified short list.
G-2   ``TestPuzzleEdit_AuditStillOnlyReports``
plus  ``TestManuallyEditedAt_Migration016`` and ``TestStoredScore_MatchesRegrades``

Both storage modes, every test
------------------------------
Every behavioural test runs twice, over the in-memory store and over a real
SQLite database through ``tests/helpers/db.py:sqlite_session_scope`` — so the
DB branch of the new write path is exercised without the suite being able to
skip it green. The Postgres path is exercised by
``tests/test_puzzle_edit_routes.py``, which goes through the panel's own
fixtures.

Expected values are written out by hand (``[[9]] + [[10]] * 9``, score 33,
tier ``easy``) rather than re-derived with the functions under test. The two
grids the corpus is built from are the two that make hand-derivation possible:
a solid grid encodes to one run per line, and a two-cell diagonal encodes to
``(1,)`` twice — whose *other* diagonal encodes identically, which is the
ambiguity.
"""

from __future__ import annotations

import ast
import copy
import inspect
import random
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

import pytest

import nonogram.admin.puzzle_review as puzzle_review_module
from nonogram.admin.puzzle_review import (
    MAX_REMEMBERED_VERIFICATIONS,
    EditNotVerified,
    PuzzleFilter,
    PuzzleReviewService,
)
from nonogram.errors import NotUniquelySolvable
from tests.helpers.db import make_book, sqlite_session_scope

REPO_ROOT = Path(__file__).resolve().parents[1]


# --------------------------------------------------------------------------
# grids whose clues can be written out by hand
# --------------------------------------------------------------------------


def solid(height: int = 10, width: int = 10) -> list[list[bool]]:
    """Every cell filled: one run per line, so the clues are the extents."""
    return [[True] * width for _ in range(height)]


def solid_minus_corner(height: int = 10, width: int = 10) -> list[list[bool]]:
    """Solid but for ``(0, 0)`` — row 0 and column 0 lose one from their run."""
    grid = solid(height, width)
    grid[0][0] = False
    return grid


def two_cell_diagonal(height: int = 10, width: int = 10) -> list[list[bool]]:
    """``(0,0)`` and ``(1,1)`` filled, nothing else — the classic 2x2 switch.

    Rows read ``(1,), (1,), (0,) …`` and columns the same, and the *other*
    diagonal — ``(0,1)`` and ``(1,0)`` — encodes to exactly those clues. So the
    clue set has two solutions and is not a puzzle (FR-006).
    """
    grid = [[False] * width for _ in range(height)]
    grid[0][0] = True
    grid[1][1] = True
    return grid


#: One row of four, filled at both ends. Rows read ``(1, 1)``, which three
#: placements satisfy, and the columns ``(1,), (0,), (0,), (1,)`` pin exactly
#: one of them — so this *is* a puzzle.
ONE_BY_FOUR = [[True, False, False, True]]

#: The 2x2 diagonal: rows ``(1,), (1,)`` and columns ``(1,), (1,)``, which the
#: *other* diagonal satisfies too, so it has two solutions and is not a
#: puzzle. Its cells read ``1001`` in row-major order — the same four bits as
#: :data:`ONE_BY_FOUR`. That collision is what the extent in
#: ``_grid_fingerprint`` exists to break (review cycle 1, F-001).
TWO_BY_TWO_DIAGONAL = [[True, False], [False, True]]


def row_major_bits(grid) -> str:
    """The digest's cell half, written independently of the store's own code."""
    return "".join("1" if cell else "0" for row in grid for cell in row)


@contextmanager
def frozen_clock(monkeypatch, instant: datetime):
    """Hold ``puzzle_review``'s ``datetime.now`` at ``instant``.

    So "the stamp moved" can be asserted strictly rather than with ``>=``,
    which a stamp that never moved also satisfies (review cycle 1, F-004).
    """

    class _Frozen(datetime):
        @classmethod
        def now(cls, tz=None):
            return instant if tz is None else instant.astimezone(tz)

    with monkeypatch.context() as patched:
        patched.setattr(puzzle_review_module, "datetime", _Frozen)
        yield


#: Row and column clues of :func:`solid_minus_corner` at 10x10, by hand.
MINUS_CORNER_CLUES = [[9]] + [[10]] * 9

#: What one solve says about :func:`solid_minus_corner`: the overlap rule
#: settles all 100 cells, so the share of the bottom rung is 1.0 and
#: ADR-0029's band arithmetic lands on exactly 33.0 — Easy (measured
#: 2026-10-18 on this worktree; the same figure ``difficulty.py``'s docstring
#: records for 420 of 420 line-solvable grids).
MINUS_CORNER_SCORE = 33
MINUS_CORNER_TIER = "easy"
MINUS_CORNER_STRATEGIES = ["simple_overlap"]

#: Everything an edit is allowed to move. The complement of this set is what
#: G-3 and AC-8 assert survives.
DERIVED_KEYS = frozenset(
    {
        "grid",
        "clues_rows",
        "clues_cols",
        "width",
        "height",
        "difficulty_score",
        "difficulty_tier",
        "strategies_used",
        "manually_edited_at",
    }
)


# --------------------------------------------------------------------------
# the harness: one store, either mode, and a book it can put a puzzle in
# --------------------------------------------------------------------------


@dataclass
class Harness:
    """A store in one of its two modes, plus what a test needs around it."""

    store: PuzzleReviewService
    mode: str
    session_factory: Optional[Callable] = None
    seeded: list[str] = field(default_factory=list)

    def seed(self, **overrides) -> str:
        """A stored puzzle whose derived columns are deliberately *wrong*.

        The clues, the score, the tier and the strategies all disagree with
        the grid, so an edit that carried them over instead of re-deriving
        them would be visible rather than coincidentally right.
        """
        payload = {
            "grid": solid(),
            "clues_rows": [[1]] * 10,
            "clues_cols": [[1]] * 10,
            "width": 10,
            "height": 10,
            "theme": "winter",
            "difficulty_score": 99,
            "difficulty_tier": "hard",
            "quality_score": 71,
            "recognizability": "high",
            "strategies_used": ["guess"],
            "source_image": "snowflake.png",
        }
        payload.update(overrides)
        puzzle_id = self.store.add_puzzle(**payload)
        self.seeded.append(puzzle_id)
        return puzzle_id

    def row(self, puzzle_id: str) -> dict:
        """The stored row, deep-copied — memory mode hands out the live dict."""
        return copy.deepcopy(self.store.get_puzzle(puzzle_id))

    def new_book_id(self) -> str:
        """A book id that satisfies ``puzzles.book_id``'s foreign key (CARD-103)."""
        if self.session_factory is None:
            return str(uuid.uuid4())
        return make_book(self.session_factory, title="Winter nights")

    def put_in_a_book(self, puzzle_id: str) -> str:
        """Record a book as holding ``puzzle_id``, FK and all."""
        book_id = self.new_book_id()
        assert self.store.assign_to_book([puzzle_id], book_id) == 1
        return book_id

    def set_the_legacy_in_book_status(self, puzzle_id: str) -> None:
        """Record membership the pre-CARD-100 way: the status, no ``book_id``.

        Written straight into storage rather than through ``mark_in_book``, so
        the legacy arm of AC-4 is reached unconditionally — the version of
        this that went through ``mark_in_book`` skipped itself when the mode
        did not record membership, which turned a mode that stopped recording
        it green rather than red (review cycle 1, F-005).
        """
        if self.session_factory is None:
            self.store.puzzles[puzzle_id]["status"] = "in_book"
            return
        import uuid as uuid_module

        from nonogram.db.models import Puzzle

        with self.session_factory() as db:
            row = (
                db.query(Puzzle)
                .filter(Puzzle.id == uuid_module.UUID(puzzle_id))
                .first()
            )
            assert row is not None, f"no puzzles row for {puzzle_id}"
            row.status = "in_book"


@pytest.fixture(params=["memory", "sqlite"])
def harness(request, tmp_path) -> Harness:
    if request.param == "memory":
        return Harness(store=PuzzleReviewService(), mode="memory")
    session_factory = sqlite_session_scope(tmp_path)
    return Harness(
        store=PuzzleReviewService(session_factory=session_factory),
        mode="sqlite",
        session_factory=session_factory,
    )


class SolveCounter:
    """Stands in front of ``puzzle_review.solve`` and counts the entries."""

    def __init__(self, real: Callable) -> None:
        self._real = real
        self.entries = 0

    def __call__(self, *args, **kwargs):
        self.entries += 1
        return self._real(*args, **kwargs)


@pytest.fixture
def solver_entries(monkeypatch) -> SolveCounter:
    counter = SolveCounter(puzzle_review_module.solve)
    monkeypatch.setattr(puzzle_review_module, "solve", counter)
    return counter


def edit(harness: Harness, puzzle_id: str, grid) -> dict:
    """The two-phase save as the panel performs it: verify, then save."""
    harness.store.verify_replacement_grid(puzzle_id, grid)
    return harness.store.save_edited_grid(puzzle_id, grid)


# --------------------------------------------------------------------------
# AC-1 — a unique edit is stored, and everything derived is re-derived
# --------------------------------------------------------------------------


class TestPuzzleEdit_StoresAndRederivesEverythingDerived:
    """AC-1: the grid lands, and the five derived columns are rebuilt from it."""

    def test_the_grid_and_every_derived_column_come_from_the_edit(self, harness):
        puzzle_id = harness.seed()
        replacement = solid_minus_corner()

        edit(harness, puzzle_id, replacement)
        row = harness.row(puzzle_id)

        assert row["grid"] == replacement
        # Hand-derived, not taken from compute_clues (COMP-004 re-encodes
        # these on the way in; a test that asked the same function would only
        # be asserting that it is deterministic).
        assert row["clues_rows"] == MINUS_CORNER_CLUES
        assert row["clues_cols"] == MINUS_CORNER_CLUES
        assert row["difficulty_score"] == MINUS_CORNER_SCORE
        assert row["difficulty_tier"] == MINUS_CORNER_TIER
        assert row["strategies_used"] == MINUS_CORNER_STRATEGIES

    def test_none_of_the_seeded_wrong_values_survive(self, harness):
        """The seed's derived columns are wrong on purpose; none may remain."""
        puzzle_id = harness.seed()
        before = harness.row(puzzle_id)

        edit(harness, puzzle_id, solid_minus_corner())
        row = harness.row(puzzle_id)

        assert before["clues_rows"] == [[1]] * 10
        assert before["difficulty_score"] == 99
        for key in ("clues_rows", "clues_cols", "difficulty_score",
                    "difficulty_tier", "strategies_used"):
            assert row[key] != before[key], f"{key} was carried over"

    def test_a_resized_edit_moves_width_and_height(self, harness):
        puzzle_id = harness.seed()

        edit(harness, puzzle_id, solid(12, 15))
        row = harness.row(puzzle_id)

        assert (row["width"], row["height"]) == (15, 12)
        assert row["clues_rows"] == [[15]] * 12
        assert row["clues_cols"] == [[12]] * 15

    def test_identity_and_provenance_columns_survive(self, harness):
        """G-3: ``id``, ``batch_id``, ``source_image`` and ``created_at``."""
        puzzle_id = harness.seed()
        before = harness.row(puzzle_id)

        edit(harness, puzzle_id, solid_minus_corner())
        after = harness.row(puzzle_id)

        for key in ("id", "batch_id", "source_image", "created_at"):
            assert after[key] == before[key], f"{key} moved"
        assert after["id"] == puzzle_id

    def test_nothing_outside_the_derived_set_moves(self, harness):
        """The complement of :data:`DERIVED_KEYS`, read off the row itself."""
        puzzle_id = harness.seed()
        before = harness.row(puzzle_id)

        edit(harness, puzzle_id, solid_minus_corner())
        after = harness.row(puzzle_id)

        untouched = set(before) - DERIVED_KEYS
        assert untouched, "the row had no columns outside the derived set"
        assert {key: after[key] for key in untouched} == {
            key: before[key] for key in untouched
        }

    def test_the_saved_row_is_what_the_save_returned(self, harness):
        puzzle_id = harness.seed()

        returned = edit(harness, puzzle_id, solid_minus_corner())

        assert returned == harness.row(puzzle_id)


# --------------------------------------------------------------------------
# AC-2 — the gate holds, and the stored row does not move
# --------------------------------------------------------------------------


class _ZeroSolutions:
    """A solver that reports no solutions. See the test for why it is needed."""

    class _Signals:
        total_cells = 100
        branch_nodes = 0
        rungs: tuple = ()
        rung_cells: dict = {}

    solution_count = 0
    signals = _Signals()

    def __call__(self, *args, **kwargs):
        return self


class TestPuzzleEdit_RefusesZeroAndMultipleSolutions:
    """AC-2: both non-puzzle verdicts are refused, by name, changing nothing.

    **A grid cannot have zero solutions**, and that is a fact about this
    boundary rather than a gap in the test: the clue set is derived *from the
    grid* (``_why_this_is_not_a_puzzle`` re-encodes it and will not take a
    caller's claim), and a grid always satisfies its own clues. The store's own
    comment records the measurement — 120 random derived clue sets, 97 unique,
    23 ambiguous, none unsolvable. So the zero arm is reached the only way it
    can be: with the solver replaced, which is what pins the *message* for the
    verdict the solver's contract allows but a grid payload cannot produce.
    """

    def test_a_two_solution_grid_is_refused_and_says_so(self, harness):
        puzzle_id = harness.seed()
        before = harness.row(puzzle_id)

        with pytest.raises(NotUniquelySolvable) as refusal:
            edit(harness, puzzle_id, two_cell_diagonal())

        assert "2 or more" in str(refusal.value)
        assert harness.row(puzzle_id) == before

    def test_a_zero_solution_verdict_is_refused_and_says_so(self, harness, monkeypatch):
        puzzle_id = harness.seed()
        before = harness.row(puzzle_id)
        monkeypatch.setattr(puzzle_review_module, "solve", _ZeroSolutions())

        with pytest.raises(NotUniquelySolvable) as refusal:
            edit(harness, puzzle_id, solid_minus_corner())

        assert "has 0 solutions" in str(refusal.value)
        assert harness.row(puzzle_id) == before

    def test_the_save_path_refuses_it_too_without_a_verification(self, harness):
        """The write path's own refusal, with no verify call in front of it.

        The uniqueness verdict wins over "you did not verify this": a grid
        that is not a puzzle is refused for not being one, which is the
        stronger and more useful statement (and the one AC-2 asks for).
        """
        puzzle_id = harness.seed()
        before = harness.row(puzzle_id)

        with pytest.raises(NotUniquelySolvable):
            harness.store.save_edited_grid(puzzle_id, two_cell_diagonal())

        assert harness.row(puzzle_id) == before

    def test_the_unchanged_check_can_see_a_row_that_did_change(self, harness):
        """The control for every ``== before`` above (ADR-0039/R1).

        A snapshot comparison that cannot fail proves nothing, so this is the
        same comparison over an edit that *is* stored. It must disagree, and
        disagree exactly on the derived columns.
        """
        puzzle_id = harness.seed()
        before = harness.row(puzzle_id)

        edit(harness, puzzle_id, solid_minus_corner())
        after = harness.row(puzzle_id)

        assert after != before, "the snapshot comparison cannot see a changed row"
        moved = {key for key in before if after[key] != before[key]}
        assert moved <= DERIVED_KEYS, f"{moved - DERIVED_KEYS} moved unexpectedly"
        assert "grid" in moved and "clues_rows" in moved


# --------------------------------------------------------------------------
# AC-3 — one solve serves both answers
# --------------------------------------------------------------------------


class TestPuzzleEdit_GradesFromTheProvingSolve:
    """AC-3: the verdict and the grade come from the same solve.

    Counted, not read off the code: ``puzzle_review.solve`` is replaced by a
    wrapper that delegates to the real solver and counts its entries.
    """

    def test_a_verify_and_the_save_that_follows_enter_the_solver_once(
        self, harness, solver_entries
    ):
        puzzle_id = harness.seed()
        assert solver_entries.entries == 1, "the seed's own add_puzzle solve"

        harness.store.verify_replacement_grid(puzzle_id, solid_minus_corner())
        after_verify = solver_entries.entries
        harness.store.save_edited_grid(puzzle_id, solid_minus_corner())

        assert after_verify == 2, "verifying a replacement grid costs one solve"
        assert solver_entries.entries == 2, (
            "the save re-entered the search to grade — the proof that was "
            "already in hand is what ADR-0029/R2 says must be read instead"
        )

    def test_the_counter_can_count_past_one(self, harness, solver_entries):
        """The control: two different grids really do report two entries."""
        puzzle_id = harness.seed()
        base = solver_entries.entries

        harness.store.verify_replacement_grid(puzzle_id, solid_minus_corner())
        harness.store.verify_replacement_grid(puzzle_id, solid(11, 11))

        assert solver_entries.entries - base == 2

    def test_the_grade_shown_is_the_grade_stored(self, harness):
        puzzle_id = harness.seed()

        shown = harness.store.verify_replacement_grid(puzzle_id, solid_minus_corner())
        harness.store.save_edited_grid(puzzle_id, solid_minus_corner())
        row = harness.row(puzzle_id)

        assert (shown["difficulty_score"], shown["difficulty_tier"],
                shown["strategies_used"]) == (
            row["difficulty_score"], row["difficulty_tier"], row["strategies_used"]
        )


# --------------------------------------------------------------------------
# AC-4 — a booked puzzle is not editable
# --------------------------------------------------------------------------


class TestPuzzleEdit_RefusesAPuzzleThatIsInABook:
    """AC-4: the precedent approve, reject, restore and delete already set."""

    def test_the_save_refuses_a_puzzle_a_book_holds(self, harness):
        puzzle_id = harness.seed()
        harness.put_in_a_book(puzzle_id)
        before = harness.row(puzzle_id)

        harness.store.verify_replacement_grid(puzzle_id, solid_minus_corner())
        assert harness.store.save_edited_grid(puzzle_id, solid_minus_corner()) is None
        assert harness.row(puzzle_id) == before

    def test_the_verify_refuses_it_too(self, harness):
        puzzle_id = harness.seed()
        harness.put_in_a_book(puzzle_id)

        assert harness.store.verify_replacement_grid(
            puzzle_id, solid_minus_corner()
        ) is None

    def test_a_legacy_in_book_status_refuses_it_as_well(self, harness):
        """Rows written before CARD-100 carry the status rather than a book id.

        No skip and no tautology: the status is written directly, the premise
        is asserted (``in_book``, and ``book_id`` still null, so this really
        is the legacy arm and not the one the test above covers), and the
        refusal is asserted unconditionally.
        """
        puzzle_id = harness.seed()
        harness.set_the_legacy_in_book_status(puzzle_id)
        before = harness.row(puzzle_id)
        assert before["status"] == "in_book"
        assert before.get("book_id") is None, "this arm is the status alone"

        assert harness.store.save_edited_grid(puzzle_id, solid_minus_corner()) is None
        assert harness.store.verify_replacement_grid(puzzle_id, solid_minus_corner()) is None
        assert harness.row(puzzle_id) == before

    def test_an_unknown_puzzle_is_not_an_edit_either(self, harness):
        unknown = str(uuid.uuid4())

        assert harness.store.verify_replacement_grid(unknown, solid_minus_corner()) is None
        assert harness.store.save_edited_grid(unknown, solid_minus_corner()) is None

    def test_the_control_an_unbooked_puzzle_is_editable(self, harness):
        """So the two ``is None`` assertions above are about the book."""
        puzzle_id = harness.seed()

        assert harness.store.verify_replacement_grid(
            puzzle_id, solid_minus_corner()
        ) is not None
        assert harness.store.save_edited_grid(puzzle_id, solid_minus_corner()) is not None


# --------------------------------------------------------------------------
# AC-5 — verify does not persist
# --------------------------------------------------------------------------


class TestPuzzleEdit_VerifyReturnsTheGradeWithoutStoring:
    """AC-5: the owner must be able to Cancel and lose nothing."""

    def test_the_grade_comes_back_and_the_row_does_not_move(self, harness):
        puzzle_id = harness.seed()
        before = harness.row(puzzle_id)

        grade = harness.store.verify_replacement_grid(puzzle_id, solid_minus_corner())

        assert grade["difficulty_score"] == MINUS_CORNER_SCORE
        assert grade["difficulty_tier"] == MINUS_CORNER_TIER
        assert grade["strategies_used"] == MINUS_CORNER_STRATEGIES
        assert grade["clues_rows"] == MINUS_CORNER_CLUES
        assert grade["clues_cols"] == MINUS_CORNER_CLUES
        assert (grade["width"], grade["height"]) == (10, 10)
        assert harness.row(puzzle_id) == before

    def test_a_cancelled_verification_leaves_no_stamp(self, harness):
        puzzle_id = harness.seed()

        harness.store.verify_replacement_grid(puzzle_id, solid_minus_corner())

        assert harness.row(puzzle_id)["manually_edited_at"] is None


# --------------------------------------------------------------------------
# AC-6 — the grid moved between verify and approve
# --------------------------------------------------------------------------


class TestPuzzleEdit_RefusesAnApproveWhoseGridMoved:
    """AC-6: the hole the two-phase flow opens, closed by construction.

    The store remembers the grids it has proved, by fingerprint, together with
    the puzzles whose owner has been *shown* that grid's grade. A save is
    refused unless this very grid is one of them — so a save can only ever
    store the grid whose grade was on screen.
    """

    def test_a_save_whose_grid_moved_is_refused(self, harness):
        puzzle_id = harness.seed()
        before = harness.row(puzzle_id)
        harness.store.verify_replacement_grid(puzzle_id, solid_minus_corner())

        with pytest.raises(EditNotVerified):
            harness.store.save_edited_grid(puzzle_id, solid(11, 11))

        assert harness.row(puzzle_id) == before

    def test_a_save_with_no_verification_at_all_is_refused(self, harness):
        puzzle_id = harness.seed()
        before = harness.row(puzzle_id)

        with pytest.raises(EditNotVerified):
            harness.store.save_edited_grid(puzzle_id, solid_minus_corner())

        assert harness.row(puzzle_id) == before

    def test_another_puzzles_verification_does_not_license_this_one(self, harness):
        other = harness.seed()
        puzzle_id = harness.seed()
        harness.store.verify_replacement_grid(other, solid_minus_corner())

        with pytest.raises(EditNotVerified):
            harness.store.save_edited_grid(puzzle_id, solid_minus_corner())

    def test_a_forgotten_verification_is_refused_rather_than_assumed(self, harness):
        """What "expires" means here: the oldest remembered grid is dropped.

        There is no clock. A verification is forgotten when
        :data:`MAX_REMEMBERED_VERIFICATIONS` newer grids have been proved (or
        when the process restarts), and a save whose verification has been
        forgotten is refused — the owner verifies again, which is cheap and
        cannot store anything ungraded.
        """
        puzzle_id = harness.seed()
        harness.store.verify_replacement_grid(puzzle_id, solid_minus_corner())

        # Solid grids of distinct extents: each is uniquely solvable and each
        # has its own fingerprint.
        for index in range(MAX_REMEMBERED_VERIFICATIONS + 1):
            harness.store.verify_replacement_grid(puzzle_id, solid(10, 10 + index))

        with pytest.raises(EditNotVerified):
            harness.store.save_edited_grid(puzzle_id, solid_minus_corner())

    def test_the_control_a_verification_that_is_still_there_saves(self, harness):
        """So the refusals above are about the verification, not about saving."""
        puzzle_id = harness.seed()
        harness.store.verify_replacement_grid(puzzle_id, solid_minus_corner())

        assert harness.store.save_edited_grid(puzzle_id, solid_minus_corner()) is not None


# --------------------------------------------------------------------------
# AC-6 (review cycle 1, F-011) — the memo has one reader
# --------------------------------------------------------------------------


class TestPuzzleEdit_TheMemoIsReadThroughOneAccessor:
    """F-011: ``_refuse_unless_verified`` went through the raw dict.

    It read ``self._verifications`` directly, so a save did not refresh the
    entry's LRU recency. Nothing was wrong *today* — the gate called
    immediately before it does the ``move_to_end`` — which is the whole
    problem: the correctness was a property of the call order, and F-006's
    suggested reordering would have turned it into a bug silently. The save
    now reads through ``_remembered_verification`` like the gate does.

    This is pinned structurally and deliberately so. A behavioural test
    cannot separate the two versions, because the recency *is* refreshed
    either way by the call in front; asserting behaviour here would be
    asserting the trap rather than the fix.
    """

    #: The memo's own three methods. Everything else asks one of them.
    MEMO_OWNERS = frozenset({"__init__", "_remember_proof", "_remembered_verification"})

    def test_nothing_outside_the_memos_own_methods_touches_it(self):
        class_node = next(
            node for node in ast.walk(_store_module_ast())
            if isinstance(node, ast.ClassDef) and node.name == "PuzzleReviewService"
        )
        reached_from = set()
        for member in class_node.body:
            if not isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for node in ast.walk(member):
                if (
                    isinstance(node, ast.Attribute)
                    and node.attr == "_verifications"
                    and isinstance(node.value, ast.Name)
                    and node.value.id == "self"
                ):
                    reached_from.add(member.name)

        assert reached_from, "nothing touches the memo at all, so this proves nothing"
        assert reached_from <= self.MEMO_OWNERS, (
            f"{sorted(reached_from - self.MEMO_OWNERS)} read the memo directly "
            "instead of through _remembered_verification"
        )

    def test_the_accessor_hands_back_the_verification_and_refreshes_it(self, harness):
        """So the accessor the others go through is the one that does the work."""
        store = harness.store
        first = solid_minus_corner()
        second = solid(11, 11)
        store.verify_replacement_grid(harness.seed(), first)
        store.verify_replacement_grid(harness.seed(), second)

        oldest = store._grid_fingerprint(first)
        assert next(iter(store._verifications)) == oldest
        remembered = store._remembered_verification(oldest)

        assert remembered is not None and remembered.proof is not None
        assert next(iter(store._verifications)) != oldest, "recency was not refreshed"


# --------------------------------------------------------------------------
# AC-6 (review cycle 1, F-001) — a proof is a proof of one *shape* of grid
# --------------------------------------------------------------------------


class TestPuzzleEdit_AProofDoesNotCrossGridExtents:
    """The extent in ``_grid_fingerprint``, which nothing asserted.

    The memo keys a proof by a digest of the grid, and the digest covers the
    *extent* as well as the cells. Drop the extent and two grids whose cells
    read the same in row-major order share a name — so a proof bought for one
    answers for the other, the save never enters the solver, the verification
    pairing matches on both halves, and a grid with two solutions is stored.
    Mutant M2 (``text = bits``) survived the card's whole 161-test selection;
    this is the round trip that kills it. The digest-inequality test below is
    the locator, not the guard: it would not have caught the flow.
    """

    def test_the_premise_two_extents_really_do_share_their_bits(self):
        """Asserted, so a later edit to either grid cannot make this vacuous."""
        assert row_major_bits(ONE_BY_FOUR) == row_major_bits(TWO_BY_TWO_DIAGONAL) == "1001"
        assert (len(ONE_BY_FOUR), len(ONE_BY_FOUR[0])) == (1, 4)
        assert (len(TWO_BY_TWO_DIAGONAL), len(TWO_BY_TWO_DIAGONAL[0])) == (2, 2)

    def test_the_narrow_grid_is_a_puzzle_and_the_square_one_is_not(self, harness):
        """The two verdicts the collision would confuse, measured separately."""
        puzzle_id = harness.seed()

        assert harness.store.verify_replacement_grid(puzzle_id, ONE_BY_FOUR) is not None
        with pytest.raises(NotUniquelySolvable, match="2 or more"):
            harness.store.verify_replacement_grid(puzzle_id, TWO_BY_TWO_DIAGONAL)

    def test_a_reshaped_grid_with_the_same_bits_is_refused_and_stores_nothing(
        self, harness
    ):
        """The corruption, end to end: verify one extent, save the other.

        The refusal must be ``NotUniquelySolvable`` — the save re-entered the
        solver and the gate answered — and not ``EditNotVerified``, which
        would mean the pairing caught it by accident rather than the gate
        catching it on purpose.
        """
        puzzle_id = harness.seed()
        assert harness.store.verify_replacement_grid(puzzle_id, ONE_BY_FOUR) is not None
        before = harness.row(puzzle_id)

        with pytest.raises(NotUniquelySolvable, match="2 or more"):
            harness.store.save_edited_grid(puzzle_id, TWO_BY_TWO_DIAGONAL)

        assert harness.row(puzzle_id) == before
        assert harness.row(puzzle_id)["manually_edited_at"] is None

    def test_the_reshaped_save_is_not_answered_from_the_other_grids_proof(
        self, harness, solver_entries
    ):
        """Counted, not inferred: the save buys its own solve.

        A memo hit is exactly how the corrupt write happens, so the measure
        that matters is that the search was entered again.
        """
        puzzle_id = harness.seed()
        harness.store.verify_replacement_grid(puzzle_id, ONE_BY_FOUR)
        after_the_verify = solver_entries.entries
        assert after_the_verify >= 1, "the verify did not reach the solver at all"

        with pytest.raises(NotUniquelySolvable):
            harness.store.save_edited_grid(puzzle_id, TWO_BY_TWO_DIAGONAL)

        assert solver_entries.entries > after_the_verify, (
            "the save was answered from a proof of a differently shaped grid"
        )

    def test_the_control_the_same_extent_is_answered_from_the_proof(
        self, harness, solver_entries
    ):
        """So the entry above is the reshape, not every save solving again."""
        puzzle_id = harness.seed()
        harness.store.verify_replacement_grid(puzzle_id, ONE_BY_FOUR)
        after_the_verify = solver_entries.entries

        assert harness.store.save_edited_grid(puzzle_id, ONE_BY_FOUR) is not None

        assert solver_entries.entries == after_the_verify

    def test_the_digest_names_the_extent(self):
        """The locator for the line above, kept as the cheap direct statement."""
        digest = PuzzleReviewService._grid_fingerprint

        assert digest(ONE_BY_FOUR) != digest(TWO_BY_TWO_DIAGONAL)
        assert digest(ONE_BY_FOUR) == digest([[True, False, False, True]])


# --------------------------------------------------------------------------
# AC-7 — a malformed grid is refused before any solve
# --------------------------------------------------------------------------


MALFORMED = [
    pytest.param([], id="empty"),
    pytest.param([[]], id="empty-row"),
    pytest.param("not a grid", id="string"),
    pytest.param(None, id="none"),
    pytest.param({"grid": True}, id="dict"),
    pytest.param([[True], [True, True]], id="ragged"),
    pytest.param([[1, 0]], id="integers"),
    pytest.param([[True, None]], id="nulls"),
    pytest.param([True, False], id="flat"),
]


class TestPuzzleEdit_RefusesAMalformedGridBeforeSolving:
    """AC-7: a shape error must not be spent as solver budget."""

    @staticmethod
    def _forbid_the_solver(monkeypatch):
        """Replace the solver with one that fails on sight.

        Installed *after* the row is seeded, because seeding a puzzle goes
        through the same gate and legitimately solves.
        """
        def refuse(*args, **kwargs):
            raise AssertionError("the solver was entered for a malformed grid")

        monkeypatch.setattr(puzzle_review_module, "solve", refuse)

    @pytest.mark.parametrize("grid", MALFORMED)
    def test_verify_refuses_the_shape_without_solving(self, harness, monkeypatch, grid):
        puzzle_id = harness.seed()
        self._forbid_the_solver(monkeypatch)

        with pytest.raises(NotUniquelySolvable) as refusal:
            harness.store.verify_replacement_grid(puzzle_id, grid)

        assert "not a readable grid" in str(refusal.value)

    @pytest.mark.parametrize("grid", MALFORMED)
    def test_save_refuses_the_shape_without_solving(self, harness, monkeypatch, grid):
        puzzle_id = harness.seed()
        before = harness.row(puzzle_id)
        self._forbid_the_solver(monkeypatch)

        with pytest.raises(NotUniquelySolvable):
            harness.store.save_edited_grid(puzzle_id, grid)

        assert harness.row(puzzle_id) == before

    def test_the_forbidden_solver_really_would_fire(self, harness, monkeypatch):
        """The control: a well-shaped grid does reach the solver it forbids.

        A grid this store has never proved, so the remembered proof cannot
        answer for it either.
        """
        puzzle_id = harness.seed()
        self._forbid_the_solver(monkeypatch)

        with pytest.raises(AssertionError, match="the solver was entered"):
            harness.store.verify_replacement_grid(puzzle_id, solid_minus_corner())


# --------------------------------------------------------------------------
# AC-8 / AC-9 — the stamp, and the quality score it licenses keeping
# --------------------------------------------------------------------------


class TestPuzzleEdit_StampsTheEditAndKeepsTheQualityScore:
    """AC-8 (SETTLED 2026-10-18): a timestamp, and the score left alone."""

    def test_the_stamp_is_set_and_the_quality_columns_are_untouched(self, harness):
        puzzle_id = harness.seed(quality_score=71, recognizability="high")
        assert harness.row(puzzle_id)["manually_edited_at"] is None

        edit(harness, puzzle_id, solid_minus_corner())
        row = harness.row(puzzle_id)

        assert row["manually_edited_at"] is not None
        assert row["quality_score"] == 71
        assert row["recognizability"] == "high"

    def test_the_stamp_is_a_timestamp_and_not_a_flag(self, harness):
        from datetime import datetime

        puzzle_id = harness.seed()
        edit(harness, puzzle_id, solid_minus_corner())

        stamp = harness.row(puzzle_id)["manually_edited_at"]
        assert not isinstance(stamp, bool)
        parsed = datetime.fromisoformat(stamp)
        assert parsed.year >= 2026, stamp

    def test_a_second_edit_moves_the_stamp_forward(self, harness, monkeypatch):
        """Strictly forward, on a clock the test holds.

        Review cycle 1, F-004: this asserted ``second >= first``, which a
        stamp that never moved also satisfies — and mutant M7 (write the
        stamp only when it is currently NULL) survived the whole selection
        because of it. Two fixed, distinct instants make the movement
        provable without leaning on wall-clock resolution, and the stored
        value is pinned to the instant so the clock is demonstrably what
        drove it. The mode decides the suffix (memory stores an aware
        ``isoformat``, the DB column is naive UTC), so the prefix is what is
        matched.
        """
        puzzle_id = harness.seed()
        nine = datetime(2026, 10, 18, 9, 0, 0, tzinfo=timezone.utc)
        half_past = datetime(2026, 10, 18, 9, 31, 42, tzinfo=timezone.utc)

        with frozen_clock(monkeypatch, nine):
            edit(harness, puzzle_id, solid_minus_corner())
        first = harness.row(puzzle_id)["manually_edited_at"]

        with frozen_clock(monkeypatch, half_past):
            edit(harness, puzzle_id, solid(11, 11))
        second = harness.row(puzzle_id)["manually_edited_at"]

        assert first.startswith("2026-10-18T09:00:00"), first
        assert second.startswith("2026-10-18T09:31:42"), second
        assert second > first


class TestPuzzleEdit_ARefusedEditLeavesNoStamp:
    """AC-9: the stamp records a stored edit, never an attempt."""

    def test_a_non_unique_edit_leaves_the_stamp_null(self, harness):
        puzzle_id = harness.seed()

        with pytest.raises(NotUniquelySolvable):
            edit(harness, puzzle_id, two_cell_diagonal())

        assert harness.row(puzzle_id)["manually_edited_at"] is None

    def test_an_unverified_edit_leaves_the_stamp_null(self, harness):
        puzzle_id = harness.seed()

        with pytest.raises(EditNotVerified):
            harness.store.save_edited_grid(puzzle_id, solid_minus_corner())

        assert harness.row(puzzle_id)["manually_edited_at"] is None

    def test_a_refused_edit_after_a_stored_one_keeps_the_earlier_stamp(self, harness):
        puzzle_id = harness.seed()
        edit(harness, puzzle_id, solid_minus_corner())
        stored = harness.row(puzzle_id)["manually_edited_at"]

        with pytest.raises(NotUniquelySolvable):
            edit(harness, puzzle_id, two_cell_diagonal())

        assert harness.row(puzzle_id)["manually_edited_at"] == stored


# --------------------------------------------------------------------------
# AC-10 — the regression nulling the score would have caused
# --------------------------------------------------------------------------


class TestPuzzleEdit_AnEditedPuzzleStillPassesTheQualityFilter:
    """AC-10: ``puzzle_review.py:890`` excludes a null from ``quality_min``.

    Nulling ``quality_score`` after an edit would make a hand-edited puzzle
    vanish from every quality-filtered view — the list the owner picks book
    puzzles from. This is that regression, asserted shut.
    """

    def _ids(self, harness, **filters) -> set:
        response = harness.store.filter_puzzles(PuzzleFilter(limit=100, **filters))
        return {row["id"] for row in response.puzzles}

    def test_a_hand_edited_puzzle_is_still_in_the_filtered_list(self, harness):
        puzzle_id = harness.seed(quality_score=71)

        edit(harness, puzzle_id, solid_minus_corner())

        assert puzzle_id in self._ids(harness, quality_min=70)

    def test_the_control_the_filter_can_still_exclude(self, harness):
        """So the inclusion above is the filter agreeing, not the filter idle."""
        puzzle_id = harness.seed(quality_score=71)
        edit(harness, puzzle_id, solid_minus_corner())

        assert puzzle_id not in self._ids(harness, quality_min=80)
        assert puzzle_id in self._ids(harness)

    def test_an_unmeasured_puzzle_is_still_excluded(self, harness):
        """The meaning a null already has on this board is unchanged."""
        puzzle_id = harness.seed(quality_score=None)
        edit(harness, puzzle_id, solid_minus_corner())

        assert puzzle_id not in self._ids(harness, quality_min=1)


# --------------------------------------------------------------------------
# G-1 — every write of a grid goes through the one refusal
# --------------------------------------------------------------------------


#: The one gate. G-1: there is exactly one, and it is this.
THE_GATE = "PuzzleReviewService._refuse_unless_uniquely_solvable"

#: Calls through which a value can reach durable state: a mutator that *writes*
#: something (so a whole-row payload, and therefore a grid, can enter through
#: it) and one that only *removes* or *reorders*. Both count as mutations — the
#: split is only used when checking what an exempt method is allowed to do.
VALUE_WRITING_MUTATORS = frozenset(
    {
        "update", "add", "add_all", "merge", "setdefault", "insert", "execute",
        "values", "bulk_save_objects", "bulk_update_mappings",
        "bulk_insert_mappings", "append", "extend",
    }
)
REMOVING_MUTATORS = frozenset(
    {"pop", "popitem", "clear", "delete", "discard", "remove", "move_to_end",
     "flush", "commit"}
)
MUTATORS = VALUE_WRITING_MUTATORS | REMOVING_MUTATORS

#: Expressions that build a brand-new container, so a name bound to one cannot
#: be the store's own state and writing into it cannot persist anything. Where
#: such a local *goes* is a separate write and is seen on its own.
_FRESH_NODES = (ast.Dict, ast.List, ast.Set, ast.DictComp, ast.ListComp, ast.SetComp)
_FRESH_CALLS = frozenset({"dict", "list", "set", "sorted", "defaultdict", "Counter", "OrderedDict"})


def _store_module_ast() -> ast.Module:
    """The whole ``puzzle_review`` module, parsed off disk.

    The *module*, not just ``PuzzleReviewService``'s ``ClassDef``: a
    module-level helper that writes a grid, called from a method, is a real
    bypass and a class-only parse cannot see it (review cycle 1, F-002).
    """
    source = Path(inspect.getsourcefile(PuzzleReviewService)).read_text(encoding="utf-8")
    return ast.parse(source)


def _symbols(module: ast.Module) -> dict:
    """Every function in the module, keyed ``Class.method`` or ``function``.

    Qualified because two classes in this module both define ``to_dict``, and
    a shared key would let one answer for the other.
    """
    found = {}
    for node in module.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            found[node.name] = node
        elif isinstance(node, ast.ClassDef):
            for member in node.body:
                if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    found[f"{node.name}.{member.name}"] = member
    return found


def _owner(qualified: str) -> str:
    return qualified.rsplit(".", 1)[0] if "." in qualified else ""


def _fresh_locals(method: ast.AST) -> set:
    """Names in this body that are bound to a freshly built container.

    Includes names reached *from* one — ``summary = summaries.get(k)`` off a
    local ``summaries = {}`` — because a slot of a fresh container is still
    not durable state. Re-run to a fixpoint so the chain is followed.
    """
    names: set = set()

    def _is_fresh(value) -> bool:
        if isinstance(value, _FRESH_NODES):
            return True
        if isinstance(value, ast.Call) and isinstance(value.func, ast.Name):
            return value.func.id in _FRESH_CALLS
        if isinstance(value, ast.Subscript):
            return _root_name(value) in names
        if isinstance(value, ast.Call) and isinstance(value.func, ast.Attribute):
            return _root_name(value.func) in names
        return False

    for _ in range(4):
        for node in ast.walk(method):
            targets = []
            if isinstance(node, ast.Assign):
                targets = node.targets
            elif isinstance(node, ast.AnnAssign):
                targets = [node.target]
            if len(targets) == 1 and isinstance(targets[0], ast.Name) and _is_fresh(node.value):
                names.add(targets[0].id)
            if (
                isinstance(node, ast.For)
                and isinstance(node.target, ast.Name)
                and isinstance(node.iter, ast.Call)
                and isinstance(node.iter.func, ast.Attribute)
                and _root_name(node.iter.func) in names
            ):
                names.add(node.target.id)
    return names


def _root_name(node) -> Optional[str]:
    """The bare name an attribute/subscript chain hangs off, if any."""
    while isinstance(node, (ast.Attribute, ast.Subscript)):
        node = node.value
    return node.id if isinstance(node, ast.Name) else None


def _mutating_shapes(method: ast.AST) -> list:
    """Every place in this body where a value could reach durable state.

    Default-deny (ADR-0039/R2): this is a catalogue of *writes*, and anything
    it names makes the method a **candidate grid writer** that then has to
    reach the gate or be excused. It is deliberately broad — a store into
    anything that is not a fresh local, any ``setattr``/``del``, any ``**``
    splat (whose payload is unreadable), any call to a mutating method, and a
    dict literal carrying a ``"grid"`` key handed to a call. Compare the
    predicate this replaced, which was a list of four *grid-write* shapes and
    therefore classified every shape it did not recognise as "not a write".

    Known bound, stated rather than papered over: a grid written through an
    *imported* helper, or through a mutating method whose name is outside
    :data:`MUTATORS`, is not seen here. What is seen is every shape in which
    the grid value itself is placed, spliced or named.
    """
    fresh = _fresh_locals(method)
    shapes = []
    for node in ast.walk(method):
        if isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                for part in ast.walk(target):
                    if isinstance(part, (ast.Attribute, ast.Subscript)) and isinstance(
                        getattr(part, "ctx", None), ast.Store
                    ):
                        if _root_name(part) not in fresh:
                            shapes.append(f"store into {_root_name(part)}")
        if isinstance(node, ast.Delete):
            for target in node.targets:
                if isinstance(target, (ast.Attribute, ast.Subscript)) and _root_name(target) not in fresh:
                    shapes.append(f"del from {_root_name(target)}")
        if isinstance(node, ast.Call):
            function = node.func
            if any(keyword.arg is None for keyword in node.keywords):
                shapes.append("** splat into a call")
            if isinstance(function, ast.Name) and function.id in ("setattr", "delattr"):
                shapes.append(f"{function.id}()")
            if isinstance(function, ast.Attribute) and function.attr in MUTATORS:
                # `d.values()` and `q.update()` with no argument read or build;
                # it is the *argument* that carries a payload.
                argument_free = not node.args and not node.keywords
                reads_only = function.attr in ("values", "update") and argument_free
                if not reads_only and _root_name(function) not in fresh:
                    shapes.append(f".{function.attr}() on {_root_name(function)}")
            for argument in list(node.args) + [keyword.value for keyword in node.keywords]:
                if _dict_literal_with_a_grid_key(argument):
                    shapes.append("a {'grid': ...} payload handed to a call")
    return shapes


def _dict_literal_with_a_grid_key(value) -> bool:
    if value is None:
        return False
    for node in ast.walk(value):
        if isinstance(node, ast.Dict):
            for key in node.keys:
                if isinstance(key, ast.Constant) and key.value == "grid":
                    return True
    return False


def _writes_the_name_grid(method: ast.AST) -> bool:
    """Does this body name ``grid`` on the writing side of something?

    No longer the guard's gatekeeper — :func:`_mutating_shapes` is — but still
    how an entry on :data:`WRITES_NO_GRID` is checked for having quietly grown
    a grid write.
    """
    for node in ast.walk(method):
        if isinstance(node, ast.Attribute) and node.attr == "grid" and isinstance(node.ctx, ast.Store):
            return True
        if isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Store):
            index = node.slice
            if isinstance(index, ast.Constant) and index.value == "grid":
                return True
        if isinstance(node, ast.Call):
            if any(keyword.arg == "grid" for keyword in node.keywords):
                return True
            if (
                isinstance(node.func, ast.Name)
                and node.func.id in ("setattr", "delattr")
                and len(node.args) >= 2
                and isinstance(node.args[1], ast.Constant)
                and node.args[1].value == "grid"
            ):
                return True
            for argument in list(node.args) + [keyword.value for keyword in node.keywords]:
                if _dict_literal_with_a_grid_key(argument):
                    return True
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            into_something = any(
                isinstance(target, (ast.Subscript, ast.Attribute)) for target in targets
            )
            if into_something and _dict_literal_with_a_grid_key(node.value):
                return True
    return False


def _unreadable_payload_writes(method: ast.AST) -> list:
    """Writes whose *contents* cannot be read off the source.

    A ``**`` splat and a ``.update(x)``/``.values(x)`` with a non-literal
    argument are the two shapes through which a whole-row payload — and so a
    grid — enters without the name ``grid`` appearing anywhere. A method that
    contains one of these can never be excused as "writes no grid", because
    nothing in the source says what it writes. This is the production
    ``save_edited_grid``'s legacy branch (``puzzle.update(derived)``), which is
    exactly why the old predicate could not see it.
    """
    found = []
    for node in ast.walk(method):
        if isinstance(node, ast.Call):
            if any(keyword.arg is None for keyword in node.keywords):
                found.append("** splat")
            if isinstance(node.func, ast.Attribute) and node.func.attr in ("update", "values"):
                if not node.args and not node.keywords:
                    continue  # `d.values()` — a read
                if node.args and isinstance(node.args[0], ast.Dict):
                    if any(not isinstance(key, ast.Constant) for key in node.args[0].keys):
                        found.append(f".{node.func.attr}(<dict with a computed key>)")
                elif not node.keywords:
                    found.append(f".{node.func.attr}(<opaque>)")
            if isinstance(node.func, ast.Name) and node.func.id == "setattr":
                if len(node.args) >= 2 and not isinstance(node.args[1], ast.Constant):
                    found.append("setattr(<computed name>)")
    return found


def _local_callees(qualified: str, method: ast.AST, symbols: dict) -> set:
    """Symbols in this module that ``qualified`` calls.

    ``self.x()``/``cls.x()`` resolves inside the owning class only;
    a bare ``x()`` resolves to a module-level function. Both, because a
    module-level writer is reachable and was invisible before (F-002).
    """
    owner = _owner(qualified)
    names = set()
    for node in ast.walk(method):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        if (
            isinstance(function, ast.Attribute)
            and isinstance(function.value, ast.Name)
            and function.value.id in ("self", "cls")
        ):
            candidate = f"{owner}.{function.attr}" if owner else function.attr
            if candidate in symbols:
                names.add(candidate)
        elif isinstance(function, ast.Name) and function.id in symbols:
            names.add(function.id)
    return names


def _provably_read_only(symbols: dict, mutations: dict, callees: dict) -> set:
    """Symbols that write nothing, directly or through another symbol here.

    The *only* way out of the candidate set that is derived rather than
    declared: no mutating shape of its own, and every module-local symbol it
    calls is itself read-only. A new reader lands here by itself; a new
    *writer* cannot.
    """
    read_only = {name for name in symbols if not mutations[name]}
    changed = True
    while changed:
        changed = False
        for name in sorted(read_only):
            if any(callee not in read_only for callee in callees[name]):
                read_only.discard(name)
                changed = True
                break
    return read_only


#: The read-only list G-1 is default-deny *against*: a method of
#: ``PuzzleReviewService`` is presumed a grid writer and must reach
#: :data:`THE_GATE` unless it is here, with a reason. Every entry is itself
#: checked — it may not name ``grid`` on the writing side
#: (:func:`_writes_the_name_grid`) and may not write an unreadable payload
#: (:func:`_unreadable_payload_writes`) — so an entry cannot quietly grow into
#: a grid write, and a method that writes a blob cannot be put here at all.
#:
#: Short by construction, not by taste: everything that writes nothing is
#: derived out by :func:`_provably_read_only`, and everything whose only
#: writes are *other* methods on this list is derived out transitively. What is
#: left is the methods that write a puzzle column with their own hands.
WRITES_NO_GRID = {
    "PuzzleReviewService.__init__": "binds the empty instance state; no row exists yet",
    "PuzzleReviewService._set_status": "writes `status`, named, and nothing else",
    "PuzzleReviewService.set_batch_status": "writes `status` on a batch's rows, named",
    "PuzzleReviewService._write_book_id": "writes `book_id` (and `status`), both named",
    "PuzzleReviewService.mark_in_book": "the legacy pair, `status` and `book_id`, named",
    "PuzzleReviewService.rename_puzzle": "writes `puzzle_name`, named",
    "PuzzleReviewService.delete_puzzle": "removes a row; a delete cannot carry a grid",
    "PuzzleReviewService.delete_rejected_in_batch": "removes rows; same reason",
    "PuzzleReviewService._remember_proof": "writes the proof memo, not a puzzle row",
    "PuzzleReviewService._remembered_verification": "LRU recency on the memo only",
}


def _accounted_for(symbols: dict, mutations: dict, callees: dict, read_only: set) -> set:
    """Everything that is allowed not to reach the gate.

    ``read_only`` plus :data:`WRITES_NO_GRID` plus, to a fixpoint, any symbol
    that writes nothing itself and only calls symbols already in here — which
    is how ``approve_puzzle`` (all of whose writing is ``_set_status``'s) stays
    out of the hand-written list.
    """
    safe = set(read_only) | set(WRITES_NO_GRID) | {THE_GATE}
    changed = True
    while changed:
        changed = False
        for name in symbols:
            if name in safe or mutations[name]:
                continue
            if callees[name] <= safe:
                safe.add(name)
                changed = True
    return safe


def _reaches(start: str, symbols: dict, callees: dict, target: str) -> bool:
    """Can ``start`` reach ``target`` through module-local calls?"""
    if start == target:
        return True
    seen, pending = set(), [start]
    while pending:
        name = pending.pop()
        if name in seen or name not in symbols:
            continue
        seen.add(name)
        if target in callees[name]:
            return True
        pending.extend(callees[name])
    return False


def _analyse(module: ast.Module) -> dict:
    """One pass: symbols, their mutating shapes, their callees, the verdicts."""
    symbols = _symbols(module)
    mutations = {name: _mutating_shapes(node) for name, node in symbols.items()}
    callees = {name: _local_callees(name, node, symbols) for name, node in symbols.items()}
    read_only = _provably_read_only(symbols, mutations, callees)
    safe = _accounted_for(symbols, mutations, callees, read_only)
    candidates = set(symbols) - read_only
    ungated = sorted(
        name
        for name in candidates
        if name not in safe and not _reaches(name, symbols, callees, THE_GATE)
    )
    return {
        "symbols": symbols,
        "mutations": mutations,
        "callees": callees,
        "read_only": read_only,
        "safe": safe,
        "candidates": candidates,
        "ungated": ungated,
    }


def _analyse_source(source: str) -> dict:
    return _analyse(ast.parse(source))


@pytest.fixture(scope="module")
def analysis() -> dict:
    """One analysis of the real store module, shared by the G-1 assertions."""
    return _analyse(_store_module_ast())


class TestPuzzleEdit_EveryGridWriteGoesThroughTheOneRefusal:
    """G-1: presumed a grid writer unless proved otherwise (ADR-0039/R2).

    Review cycle 1, F-002: the first version of this guard derived the method
    *set* from the class but decided "is this a grid write?" with a list of
    four syntactic shapes, so a write in any fifth shape was classified "not a
    write" and exempted — default-allow. Eight of nine plausible writer bodies
    were invisible to it, including the one production itself uses in legacy
    mode (``puzzle.update(derived)``), and a behaviour-identical ``setattr``
    loop in the DB branch dropped ``save_edited_grid`` out of the writer set
    while the assertion still passed.

    This version inverts it. Every function in the module is a **candidate
    grid writer** unless it is *provably* read-only — no mutating shape of its
    own and no call to anything here that has one. A candidate must then reach
    :data:`THE_GATE`, or appear on :data:`WRITES_NO_GRID` with a reason, and
    an entry there is itself checked for not naming a grid and not writing an
    unreadable payload. A method added tomorrow that writes *anything* is in
    the candidate set the moment it exists and fails this by default.

    The scope is the module, not the class, so a module-level helper that
    writes a grid is seen too — the other half of F-002.
    """

    def test_every_candidate_writer_reaches_the_refusal_or_is_excused(self, analysis):
        assert analysis["candidates"], "nothing was classified a writer, so this proves nothing"
        assert not analysis["ungated"], (
            f"these write without reaching {THE_GATE} and are not on "
            f"WRITES_NO_GRID: {analysis['ungated']} — every write of a grid goes "
            "through the one refusal (G-1)"
        )

    def test_the_two_grid_writers_are_candidates_and_reach_the_gate(self, analysis):
        """A floor under the inversion, not the definition of the set."""
        for name in ("PuzzleReviewService.add_puzzle", "PuzzleReviewService.save_edited_grid"):
            assert name in analysis["candidates"], f"{name} was classified read-only"
            assert name not in WRITES_NO_GRID, f"{name} must not be excused"
            assert _reaches(name, analysis["symbols"], analysis["callees"], THE_GATE)

    def test_save_edited_grid_could_not_be_excused_even_if_someone_listed_it(self, analysis):
        """F-002's sharpest edge, asserted shut.

        Its legacy branch is ``puzzle.update(derived)`` — the shape the old
        predicate could not see. The exemption check refuses any method that
        writes a payload the source cannot read, so this one cannot be moved
        onto ``WRITES_NO_GRID`` to silence a failure.
        """
        node = analysis["symbols"]["PuzzleReviewService.save_edited_grid"]

        assert _unreadable_payload_writes(node), (
            "save_edited_grid no longer writes an opaque payload; if the legacy "
            "branch was rewritten, re-check that this control still bites"
        )

    def test_every_excused_method_is_still_not_a_grid_write(self, analysis):
        """The hand-written list cannot grow a grid write under it."""
        offences = {}
        for name in sorted(WRITES_NO_GRID):
            assert name in analysis["symbols"], f"{name} is on WRITES_NO_GRID but does not exist"
            node = analysis["symbols"][name]
            reasons = []
            if _writes_the_name_grid(node):
                reasons.append("names `grid` on the writing side")
            reasons.extend(_unreadable_payload_writes(node))
            if reasons:
                offences[name] = reasons

        assert not offences, (
            f"excused methods that are not excusable: {offences} — remove the "
            "entry and send the method through the gate"
        )

    def test_every_excused_method_carries_a_reason(self):
        for name, reason in WRITES_NO_GRID.items():
            assert reason and len(reason) > 15, f"{name} is excused without a reason"

    def test_the_readers_are_derived_out_not_listed(self, analysis):
        """``audit_uniqueness`` and the row readers come out read-only by proof."""
        for name in (
            "PuzzleReviewService._row_to_dict",
            "PuzzleReviewService._all_rows_for_audit",
            "PuzzleReviewService.audit_uniqueness",
            "PuzzleReviewService.filter_puzzles",
            "PuzzleReviewService.get_puzzle",
        ):
            assert name in analysis["read_only"], (
                f"{name} is not provably read-only: {analysis['mutations'][name]}"
            )
            assert name not in WRITES_NO_GRID, f"{name} should not need an entry"

    def test_the_read_only_list_is_short(self, analysis):
        """A long list would be the snapshot of today's methods G-1 forbids."""
        assert len(WRITES_NO_GRID) <= 12, sorted(WRITES_NO_GRID)
        assert len(analysis["read_only"]) > len(WRITES_NO_GRID), (
            "most of the class should be derived out, not listed out"
        )

    #: The nine writer bodies review cycle 1 probed the old predicate with —
    #: eight of which it could not see. Each is placed in a method that does
    #: **not** call the gate, so each must be reported ungated. These are the
    #: control (ADR-0039/R1): if the inversion stops seeing one of them, the
    #: assertion above starts passing for the wrong reason.
    NINE_SHAPES = [
        pytest.param("        db.query(Puzzle).filter(x).update({'grid': grid})", id="query-update"),
        pytest.param("        db.add(Puzzle(**derived))", id="kwargs-splat"),
        pytest.param(
            "        for column, value in derived.items():\n"
            "            setattr(row, column, value)",
            id="setattr-loop",
        ),
        pytest.param("        self.puzzles[pid].update(derived)", id="dict-update"),
        pytest.param("        column = 'grid'\n        setattr(row, column, grid)", id="computed-setattr"),
        pytest.param("        _apply(row, grid)", id="module-level-helper"),
        pytest.param(
            "        payload = {'grid': grid}\n        self.puzzles[pid] = payload",
            id="payload-then-assign",
        ),
        pytest.param("        row.grid[0][0] = True", id="in-place-cell"),
        pytest.param("        target = row\n        target.grid = grid", id="aliased-attribute"),
    ]

    @pytest.mark.parametrize("body", NINE_SHAPES)
    def test_the_nine_shapes_cycle_one_probed_are_all_seen(self, body):
        source = (
            "def _apply(row, grid):\n"
            "    row.grid = grid\n"
            "class PuzzleReviewService:\n"
            "    def smuggle_a_grid(self, pid, db, row, derived, grid, x):\n"
            f"{body}\n"
            "    def _refuse_unless_uniquely_solvable(self, grid):\n"
            "        return None\n"
        )
        analysis = _analyse_source(source)

        assert "PuzzleReviewService.smuggle_a_grid" in analysis["candidates"], (
            "the inversion classified a grid write as read-only"
        )
        assert "PuzzleReviewService.smuggle_a_grid" in analysis["ungated"], analysis["mutations"]

    def test_a_module_level_writer_is_reported_in_its_own_right(self):
        """The scope half of F-002: the class-only parse could not see this."""
        source = (
            "def _apply(row, grid):\n"
            "    row.grid = grid\n"
            "class PuzzleReviewService:\n"
            "    def _refuse_unless_uniquely_solvable(self, grid):\n"
            "        return None\n"
        )
        analysis = _analyse_source(source)

        assert "_apply" in analysis["ungated"], analysis

    def test_a_writer_that_reaches_the_gate_through_a_helper_passes(self):
        source = (
            "class PuzzleReviewService:\n"
            "    def store_it(self, row, grid):\n"
            "        self._prove(grid)\n"
            "        row.grid = grid\n"
            "    def _prove(self, grid):\n"
            "        return self._refuse_unless_uniquely_solvable(grid)\n"
            "    def _refuse_unless_uniquely_solvable(self, grid):\n"
            "        return None\n"
        )
        analysis = _analyse_source(source)

        assert "PuzzleReviewService.store_it" in analysis["candidates"]
        assert not analysis["ungated"], analysis["ungated"]

    def test_a_pure_reader_is_not_a_candidate(self):
        """The other side of the control: the inversion is not red-by-default."""
        source = (
            "class PuzzleReviewService:\n"
            "    def read_it(self, row):\n"
            "        return {'grid': row.grid, 'id': str(row.id)}\n"
            "    def _refuse_unless_uniquely_solvable(self, grid):\n"
            "        return None\n"
        )
        analysis = _analyse_source(source)

        assert "PuzzleReviewService.read_it" in analysis["read_only"]
        assert not analysis["ungated"]

    def test_the_parsed_symbols_are_the_methods_the_store_runs(self, analysis):
        """The AST set and the runtime set agree, so nothing is parsed past."""
        parsed = {
            name.split(".", 1)[1]
            for name in analysis["symbols"]
            if name.startswith("PuzzleReviewService.")
        }
        runtime = {
            name for name, value in vars(PuzzleReviewService).items()
            if callable(value) or isinstance(value, staticmethod)
        }

        assert runtime <= parsed, sorted(runtime - parsed)

    def test_there_is_exactly_one_solver_call_site_in_the_store(self):
        """One gate to audit: nothing else in the module enters the search."""
        callers = [
            node for node in ast.walk(_store_module_ast())
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "solve"
        ]

        assert len(callers) == 1, (
            f"{len(callers)} call sites enter the solver in puzzle_review.py; "
            "the store asks the uniqueness question in exactly one place"
        )


# --------------------------------------------------------------------------
# G-2 — the audit still only reports
# --------------------------------------------------------------------------


class TestPuzzleEdit_AuditStillOnlyReports:
    """G-2: ``audit_uniqueness`` answers "what is in there now?" and writes nothing."""

    def test_an_edited_row_passes_the_audit(self, harness):
        puzzle_id = harness.seed()
        edit(harness, puzzle_id, solid_minus_corner())

        assert harness.store.audit_uniqueness() == []

    def test_the_audit_writes_nothing(self, harness):
        puzzle_id = harness.seed()
        edit(harness, puzzle_id, solid_minus_corner())
        before = harness.row(puzzle_id)

        harness.store.audit_uniqueness()

        assert harness.row(puzzle_id) == before

    def test_the_audit_can_still_see_a_row_that_is_not_a_puzzle(self, harness):
        """The control: it reports when there is something to report.

        The ambiguous grid is written past the gate deliberately — which is
        the only way such a row can exist now, and the reason the audit is
        kept (CARD-080).
        """
        puzzle_id = harness.seed()
        if harness.mode == "memory":
            harness.store.puzzles[puzzle_id]["grid"] = two_cell_diagonal()
        else:
            from nonogram.db.models import Puzzle

            with harness.session_factory() as db:
                row = db.query(Puzzle).filter(Puzzle.id == uuid.UUID(puzzle_id)).first()
                row.grid = two_cell_diagonal()

        failures = harness.store.audit_uniqueness()

        assert [pid for pid, _ in failures] == [puzzle_id]


# --------------------------------------------------------------------------
# the stored score, cross-checked against the other implementation
# --------------------------------------------------------------------------


class TestStoredScore_MatchesRegrades:
    """``puzzle_review`` rounds a score the way ``regrade`` does, natively.

    ``regrade`` imports SQLAlchemy and ``puzzle_review`` must not require it
    (the precedent ``_strategies_of``'s docstring already records), so the
    ceiling rule is reimplemented rather than imported — and pinned against
    the other implementation from the test tree, where the import is legal.
    """

    def test_the_two_implementations_agree_over_a_seeded_corpus(self):
        from nonogram.admin.regrade import _stored_score as regrades

        mine = PuzzleReviewService._stored_score
        rng = random.Random(245)
        cases = [0.0, 33.0, 33.08, 65.99, 66.0, 90.0, 90.01, 100.0]
        cases += [rng.uniform(-10.0, 110.0) for _ in range(400)]

        assert len(cases) >= 400, "the corpus must not silently shrink"
        disagreements = [score for score in cases if mine(score) != regrades(score)]
        assert not disagreements, disagreements[:5]

    def test_the_rounding_is_a_ceiling_and_the_corpus_could_see_it_otherwise(self):
        """The control: ordinary rounding would be caught by that corpus."""
        assert PuzzleReviewService._stored_score(33.08) == 34
        assert round(33.08) == 33


# --------------------------------------------------------------------------
# migration 016
# --------------------------------------------------------------------------


_OLD_ROW_ID = "11111111-1111-4111-8111-111111111111"


class TestManuallyEditedAt_Migration016:
    """016 adds ``puzzles.manually_edited_at``, nullable, with no backfill.

    The pre-016 database is built in today's shape, the column dropped back
    off, a row inserted and the database stamped at 015 — the pattern
    ``TestBatchRequestedTier``'s migration test already uses for 014.
    """

    @pytest.fixture
    def pre_016_db(self, tmp_path, monkeypatch):
        from sqlalchemy import create_engine, text

        from nonogram.db.models import Base

        url = f"sqlite:///{tmp_path / 'pre016.db'}"
        engine = create_engine(url)
        Base.metadata.create_all(engine)
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE puzzles DROP COLUMN manually_edited_at"))
            connection.execute(
                text(
                    "INSERT INTO puzzles (id, grid, clues_rows, clues_cols, width, "
                    "height, theme, difficulty_score, difficulty_tier, quality_score, "
                    "recognizability, strategies_used, status, source_image, "
                    "puzzle_name, created_at) "
                    "VALUES (:id, '[[true]]', '[[1]]', '[[1]]', 1, 1, 'winter', 33, "
                    "'easy', 71, 'high', '[\"simple_overlap\"]', 'draft', "
                    "'snowflake.png', 'Snowflake', '2026-09-01 10:00:00')"
                ),
                {"id": _OLD_ROW_ID},
            )
        engine.dispose()

        # migrations/env.py reads DATABASE_URL before the config's URL.
        monkeypatch.setenv("DATABASE_URL", url)
        from alembic import command

        command.stamp(self._config(url), "015")
        return url

    @staticmethod
    def _config(url: str):
        from alembic.config import Config

        config = Config()
        config.set_main_option("script_location", str(REPO_ROOT / "migrations"))
        config.set_main_option("sqlalchemy.url", url)
        return config

    @staticmethod
    def _puzzles(url: str):
        from sqlalchemy import create_engine, inspect, text

        engine = create_engine(url)
        try:
            columns = {c["name"]: c for c in inspect(engine).get_columns("puzzles")}
            with engine.connect() as connection:
                rows = [
                    dict(row._mapping)
                    for row in connection.execute(text("SELECT * FROM puzzles"))
                ]
            return columns, rows
        finally:
            engine.dispose()

    def test_the_fixture_really_is_a_pre_016_database(self, pre_016_db):
        columns, rows = self._puzzles(pre_016_db)
        assert "manually_edited_at" not in columns
        assert len(rows) == 1

    def test_up_down_up(self, pre_016_db):
        from alembic import command

        config = self._config(pre_016_db)
        _, [before] = self._puzzles(pre_016_db)

        command.upgrade(config, "016")
        columns, [upgraded] = self._puzzles(pre_016_db)
        assert "manually_edited_at" in columns
        assert columns["manually_edited_at"]["nullable"] is True
        assert upgraded["manually_edited_at"] is None, (
            "no backfill: an existing row reads 'never hand-edited', which is true"
        )
        assert {k: v for k, v in upgraded.items() if k != "manually_edited_at"} == before

        command.downgrade(config, "015")
        columns, [downgraded] = self._puzzles(pre_016_db)
        assert "manually_edited_at" not in columns
        assert downgraded == before, "the old row's other columns are unchanged"

        command.upgrade(config, "016")
        columns, [again] = self._puzzles(pre_016_db)
        assert "manually_edited_at" in columns
        assert again["manually_edited_at"] is None

    def test_016_revises_015(self):
        """This card's own link in the chain, which no later card may re-point."""
        from alembic.script import ScriptDirectory

        script = ScriptDirectory.from_config(self._config("sqlite://"))
        assert script.get_revision("016").down_revision == "015"

    def test_the_head_is_the_highest_numbered_migration_on_disk(self):
        """Derived, not named: the highest numbered version file on disk.

        ``tests/test_batch_requested_tier.py`` asserts the chain *property*
        (one head, every link, nothing orphaned) and that assertion is why 016
        needed no edit to it. This one says the head is whatever the newest
        file is, so the next migration moves it by itself.

        It used to end ``== ["016"]``, which pinned today's head by *name* and
        would have turned red on whichever unrelated card wrote 017 — the
        brittleness ``tests/test_batch_requested_tier.py:300-302`` records
        having already been paid for once at 014 → 015 (review cycle 1,
        F-003). ``test_016_revises_015`` is this card's own link in the chain
        and is the assertion that names a number legitimately.

        Named ``test_016_is_the_head`` until that fix; renamed because the
        name made the claim the assertion must not make (G-6: the survivor is
        this test, nothing was retired).
        """
        from alembic.script import ScriptDirectory

        script = ScriptDirectory.from_config(self._config("sqlite://"))
        on_disk = {
            path.name.split("_", 1)[0]
            for path in (REPO_ROOT / "migrations" / "versions").glob("[0-9]*_*.py")
        }

        assert script.get_heads() == [max(on_disk, key=int)]
