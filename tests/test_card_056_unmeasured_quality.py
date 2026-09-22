"""CARD-056 — a puzzle with no measured quality is a value, not an error.

CARD-050 settled that random mode has no quality metric to report: its puzzles
store ``quality_score = None`` rather than the hardcoded ``75`` they used to.
What it did not settle — because nothing in the architecture model says what
``quality_score`` is — was what the rest of the admin panel does when it meets
that ``None``. Three places had each decided separately:

* ``PuzzleReviewService.filter_puzzles``'s in-memory branch compared
  ``None < quality_min`` and raised ``TypeError``;
* the same method's DB branch filters in SQL, where ``NULL >= n`` is simply
  false, so those rows were dropped without comment;
* ``BookPDFGenerator`` printed ``Quality: None/100`` into a book, its
  ``.get("quality_score", 0)`` default never firing because the key is present
  and holds ``None``.

The rule ADR-0032 now states is the one the templates had already chosen
(``quality_score or 'N/A'``, five of them): an unmeasured puzzle is *unknown*,
not zero and not an error. Unknown does not satisfy a minimum, and it prints
as ``N/A``.
"""

from __future__ import annotations

import pytest

from nonogram.admin.pdf_generator import BookPDFGenerator
from nonogram.admin.puzzle_review import PuzzleFilter, PuzzleReviewService

from tests.helpers.mock_generator import MockGenerator


def _store(service, quality_score, *, seed):
    """Store one real puzzle carrying *quality_score*; return its id."""
    puzzle = MockGenerator(seed=seed).generate_batch(count=1, sizes=[10])[0]
    return service.add_puzzle(
        grid=puzzle["grid"],
        clues_rows=puzzle["clues_rows"],
        clues_cols=puzzle["clues_cols"],
        width=puzzle["width"],
        height=puzzle["height"],
        theme=puzzle["theme"],
        difficulty_score=puzzle["difficulty_score"],
        difficulty_tier=puzzle["difficulty_tier"],
        quality_score=quality_score,
        recognizability=None if quality_score is None else "high",
        strategies_used=puzzle["strategies_used"],
    )


class TestUnmeasuredQuality_SurvivesTheFilter:
    """AC-4: a `None` quality is excluded by a minimum, never an exception."""

    def test_the_filter_does_not_raise_on_an_unmeasured_puzzle(self) -> None:
        """The reported defect: two admin routes pass `quality_min` straight in.

        Before this card the comparison was ``puzzle["quality_score"] <
        filter_opts.quality_min``, which raises as soon as one random-mode
        puzzle is in the store — and random-mode puzzles are exactly what
        ``batch_generator`` writes ``None`` for.
        """
        service = PuzzleReviewService()
        _store(service, None, seed=2026)

        result = service.filter_puzzles(PuzzleFilter(quality_min=50))

        assert result.puzzles == [], (
            "a puzzle with no measured quality cannot satisfy a minimum, so the "
            "filter should exclude it rather than raise or admit it"
        )

    def test_a_measured_puzzle_still_passes_the_same_filter(self) -> None:
        """The other half: excluding `None` must not exclude everything."""
        service = PuzzleReviewService()
        _store(service, None, seed=2026)
        measured = _store(service, 80, seed=7)

        result = service.filter_puzzles(PuzzleFilter(quality_min=50))

        assert [p["id"] for p in result.puzzles] == [measured]

    def test_an_unmeasured_puzzle_is_listed_when_no_minimum_is_asked_for(self) -> None:
        """Unknown quality hides a puzzle only from a question it cannot answer."""
        service = PuzzleReviewService()
        unmeasured = _store(service, None, seed=2026)

        result = service.filter_puzzles(PuzzleFilter())

        assert [p["id"] for p in result.puzzles] == [unmeasured]

    def test_the_boundary_is_the_same_one_a_measured_puzzle_gets(self) -> None:
        """`quality_min` is inclusive for a measured score; `None` is not a score.

        Pinned together so a future change to the comparison has to keep both
        halves in view: 80 passes `quality_min=80`, and `None` does not pass it
        however low it goes — short of not being asked at all.
        """
        service = PuzzleReviewService()
        _store(service, None, seed=2026)
        measured = _store(service, 80, seed=7)

        at_the_boundary = service.filter_puzzles(PuzzleFilter(quality_min=80))
        assert [p["id"] for p in at_the_boundary.puzzles] == [measured], (
            "80 satisfies a minimum of 80 — the comparison is `<`, so the "
            "boundary belongs to the puzzle"
        )

        at_the_floor = service.filter_puzzles(PuzzleFilter(quality_min=1))
        assert [p["id"] for p in at_the_floor.puzzles] == [measured], (
            "a minimum of 1 admits every measured score and still cannot admit "
            "an unmeasured one: `None` is not a score below 1, it is no score"
        )


class TestUnmeasuredQuality_PrintsAsNotAvailable:
    """AC-4: a book never prints `None/100`."""

    @staticmethod
    def _puzzle(quality_score):
        return {
            "grid": [[True, False], [False, True]],
            "width": 2,
            "height": 2,
            "difficulty_tier": "easy",
            "quality_score": quality_score,
            "clues_rows": [[1], [1]],
            "clues_cols": [[1], [1]],
        }

    def test_an_unmeasured_score_prints_as_n_a_with_no_denominator(self) -> None:
        """`N/A/100` reads as a typo on a printed page — 100 of what?

        The denominator belongs to the number, so the helper carries it: a
        measured score is `73/100`, an unmeasured one is `N/A` and stops.
        The owner chose this on a rendered sample (2026-09-22); the five admin
        templates still print `N/A/100`, which a screen carries and a book
        does not.
        """
        generator = BookPDFGenerator()
        assert generator._quality_label(self._puzzle(None)) == "N/A"

    def test_a_measured_score_prints_as_the_number_over_one_hundred(self) -> None:
        generator = BookPDFGenerator()
        assert generator._quality_label(self._puzzle(73)) == "73/100"

    def test_no_quality_field_at_all_is_also_not_available(self) -> None:
        """A row from before the column existed reads the same as an unmeasured one."""
        generator = BookPDFGenerator()
        assert generator._quality_label({}) == "N/A"

    def test_no_call_site_reads_quality_score_with_a_zero_default(self) -> None:
        """Both rendered strings go through the helper, checked structurally.

        Walked with ``ast`` rather than grepped, because the helper's own
        docstring quotes the retired expression to explain what it replaced —
        a source-text assertion fails on the prose that documents the fix. The
        same reason ``test_cli.py``'s import guard and ``pages.py``'s escaping
        guard walk the tree instead of the text.
        """
        import ast
        import inspect

        tree = ast.parse(inspect.getsource(BookPDFGenerator))

        zero_defaults = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
            and len(node.args) == 2
            and isinstance(node.args[0], ast.Constant)
            and node.args[0].value == "quality_score"
        ]
        assert not zero_defaults, (
            "a `.get('quality_score', <default>)` default never fires — the key "
            "is present and holds None — so it reads as a safeguard while "
            "printing `None/100`"
        )

        helper_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "_quality_label"
        ]
        assert len(helper_calls) >= 2, (
            "the contents page and the puzzle page should ask the same helper; "
            f"found {len(helper_calls)} call(s)"
        )
