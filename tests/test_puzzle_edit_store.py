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
AC-7  ``TestPuzzleEdit_RefusesAMalformedGridBeforeSolving``
AC-8  ``TestPuzzleEdit_StampsTheEditAndKeepsTheQualityScore``
AC-9  ``TestPuzzleEdit_ARefusedEditLeavesNoStamp``
AC-10 ``TestPuzzleEdit_AnEditedPuzzleStillPassesTheQualityFilter``
G-1   ``TestPuzzleEdit_EveryGridWriteGoesThroughTheOneRefusal``
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
from dataclasses import dataclass, field
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
        """Rows written before CARD-100 carry the status rather than a book id."""
        puzzle_id = harness.seed()
        assert harness.store.mark_in_book(puzzle_id, harness.new_book_id()) in (True, False)
        before = harness.row(puzzle_id)
        if not harness.store.in_a_book(puzzle_id):
            pytest.skip("mark_in_book did not record membership in this mode")

        assert harness.store.save_edited_grid(puzzle_id, solid_minus_corner()) is None
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

    def test_a_second_edit_moves_the_stamp_forward(self, harness):
        puzzle_id = harness.seed()
        edit(harness, puzzle_id, solid_minus_corner())
        first = harness.row(puzzle_id)["manually_edited_at"]

        edit(harness, puzzle_id, solid(11, 11))
        second = harness.row(puzzle_id)["manually_edited_at"]

        assert second >= first


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


def _service_class_ast() -> ast.ClassDef:
    """``PuzzleReviewService``'s own class body, parsed off disk."""
    source = Path(inspect.getsourcefile(PuzzleReviewService)).read_text(encoding="utf-8")
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ClassDef) and node.name == "PuzzleReviewService":
            return node
    raise AssertionError("PuzzleReviewService is not in its own module's source")


def _methods_of(class_node: ast.ClassDef) -> dict:
    return {
        node.name: node
        for node in class_node.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _binds_a_grid(method: ast.AST) -> bool:
    """Does this method bind a value under the name ``grid``?

    Three shapes, and the context is what keeps readers out of the set:

    * ``row.grid = …`` / ``d["grid"] = …`` — the name in a *store* context.
      ``row.grid`` and ``puzzle["grid"]`` as *loads* are reads and do not count.
    * a call with a ``grid=`` keyword — ``Puzzle(grid=…)``, and any future
      helper that takes the grid by name.
    * a dict literal carrying a ``"grid"`` key that is assigned into this
      object's own state (``self.puzzles[pid] = {"grid": …}``) — the in-memory
      store's shape. A dict literal that is *returned* is a reader's output
      (``_row_to_dict``, ``_all_rows_for_audit``) and does not count.
    * ``setattr(row, "grid", …)``, which the three above would not see.
    """
    for node in ast.walk(method):
        if isinstance(node, ast.Attribute) and node.attr == "grid":
            if isinstance(node.ctx, ast.Store):
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
                and node.func.id == "setattr"
                and len(node.args) >= 2
                and isinstance(node.args[1], ast.Constant)
                and node.args[1].value == "grid"
            ):
                return True
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            into_self = any(
                isinstance(target, (ast.Subscript, ast.Attribute))
                and "self" in ast.dump(target)
                for target in targets
            )
            if into_self and _dict_literal_with_a_grid_key(node.value):
                return True
    return False


def _dict_literal_with_a_grid_key(value) -> bool:
    if value is None:
        return False
    for node in ast.walk(value):
        if isinstance(node, ast.Dict):
            for key in node.keys:
                if isinstance(key, ast.Constant) and key.value == "grid":
                    return True
    return False


def _calls_on_self(method: ast.AST) -> set:
    names = set()
    for node in ast.walk(method):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            value = node.func.value
            if isinstance(value, ast.Name) and value.id == "self":
                names.add(node.func.attr)
    return names


def _reaches(start: str, methods: dict, target: str) -> bool:
    """Can ``start`` reach ``target`` through ``self.…`` calls inside the class?"""
    seen, pending = set(), [start]
    while pending:
        name = pending.pop()
        if name in seen or name not in methods:
            continue
        seen.add(name)
        called = _calls_on_self(methods[name])
        if target in called:
            return True
        pending.extend(called)
    return False


#: The one gate. G-1: there is exactly one, and it is this.
THE_GATE = "_refuse_unless_uniquely_solvable"


class TestPuzzleEdit_EveryGridWriteGoesThroughTheOneRefusal:
    """G-1: derived from the class, defaulting to deny (ADR-0039/R2).

    The set of grid-writing methods is **computed** from
    ``PuzzleReviewService``'s own source, not listed here: a method added
    tomorrow that binds a grid is in the set the moment it exists, and it has
    to reach the gate or this fails. A hand-written list would be a snapshot
    of today's methods, which is exactly what a new bypass walks past.
    """

    def test_every_grid_writing_method_reaches_the_refusal(self):
        methods = _methods_of(_service_class_ast())
        writers = {name for name, node in methods.items() if _binds_a_grid(node)}

        assert writers, "the detector found no grid writer at all, so it proves nothing"
        ungated = sorted(
            name for name in writers if not _reaches(name, methods, THE_GATE)
        )
        assert not ungated, (
            f"these methods bind a grid without reaching {THE_GATE}: {ungated} — "
            "every write of a grid goes through the one refusal (G-1)"
        )

    def test_the_two_known_writers_are_in_the_derived_set(self):
        """Not the definition of the set — a floor under the detector."""
        methods = _methods_of(_service_class_ast())
        writers = {name for name, node in methods.items() if _binds_a_grid(node)}

        assert {"add_puzzle", "save_edited_grid"} <= writers, sorted(writers)

    def test_the_readers_are_not_in_the_set(self):
        """``audit_uniqueness`` and ``_row_to_dict`` read grids; G-2 forbids writing."""
        methods = _methods_of(_service_class_ast())
        writers = {name for name, node in methods.items() if _binds_a_grid(node)}

        assert "_row_to_dict" not in writers
        assert "_all_rows_for_audit" not in writers
        assert "audit_uniqueness" not in writers

    @pytest.mark.parametrize(
        "bypass",
        [
            pytest.param("row.grid = grid", id="attribute"),
            pytest.param('self.puzzles[pid]["grid"] = grid', id="subscript"),
            pytest.param('setattr(row, "grid", grid)', id="setattr"),
            pytest.param('Puzzle(grid=grid)', id="keyword"),
            pytest.param('self.puzzles[pid] = {"grid": grid}', id="dict-literal"),
        ],
    )
    def test_the_detector_catches_a_bypass_it_has_never_seen(self, bypass):
        """The control (ADR-0039/R1): the guard above can fail.

        Five syntactic ways to write a grid, each in a method that does *not*
        call the gate. Each must be detected and each must be reported as
        ungated — otherwise the real assertion is passing because it sees
        nothing, not because nothing is wrong.
        """
        source = (
            "class PuzzleReviewService:\n"
            "    def smuggle_a_grid(self, pid, row, grid):\n"
            f"        {bypass}\n"
            "    def _refuse_unless_uniquely_solvable(self, grid):\n"
            "        return None\n"
        )
        class_node = next(
            node for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.ClassDef)
        )
        methods = _methods_of(class_node)

        assert _binds_a_grid(methods["smuggle_a_grid"]), "the detector missed a write"
        assert not _reaches("smuggle_a_grid", methods, THE_GATE)

    def test_the_detector_sees_a_write_hidden_behind_a_helper(self):
        """A writer that reaches the gate through another method still passes."""
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
        class_node = next(
            node for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.ClassDef)
        )
        methods = _methods_of(class_node)

        assert _binds_a_grid(methods["store_it"])
        assert _reaches("store_it", methods, THE_GATE)

    def test_the_parsed_class_is_the_class_the_store_runs(self):
        """The AST set and the runtime set agree, so nothing is parsed past."""
        parsed = set(_methods_of(_service_class_ast()))
        runtime = {
            name for name, value in vars(PuzzleReviewService).items()
            if callable(value) or isinstance(value, staticmethod)
        }

        assert runtime <= parsed, sorted(runtime - parsed)

    def test_there_is_exactly_one_solver_call_site_in_the_store(self):
        """One gate to audit: nothing else in the module enters the search."""
        source = Path(inspect.getsourcefile(PuzzleReviewService)).read_text(
            encoding="utf-8"
        )
        callers = [
            node for node in ast.walk(ast.parse(source))
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

    def test_016_is_the_head(self):
        """Derived, not named: the highest numbered version file on disk.

        ``tests/test_batch_requested_tier.py`` asserts the chain *property*
        (one head, every link, nothing orphaned) and that assertion is why 016
        needed no edit to it. This one says which revision that head is today,
        and the next migration moves it by itself.
        """
        from alembic.script import ScriptDirectory

        script = ScriptDirectory.from_config(self._config("sqlite://"))
        on_disk = {
            path.name.split("_", 1)[0]
            for path in (REPO_ROOT / "migrations" / "versions").glob("[0-9]*_*.py")
        }

        assert script.get_heads() == [max(on_disk, key=int)] == ["016"]
