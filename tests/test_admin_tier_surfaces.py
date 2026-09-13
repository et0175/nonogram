"""The admin surfaces that read a tier back, across all four members.

CARD-076 review, finding F-002. ADR-0025 added a fourth tier, and the card's
objective 4 is that every ``Tier`` consumer handles it. Four consumers were
missed, and all four shared one older defect that hid the gap: they compared a
row's ``difficulty_tier`` against a *display label* (``"Easy"``), while a row
written by the generation pipeline stores the enum *value* (``"easy"``) —
``orchestrator.Puzzle.difficulty_tier`` is a ``Tier``, and a ``StrEnum``'s
``str`` is its value. So the counts read 0 for every generated book and the
filter matched none of its rows, which looks like an empty book rather than
like a broken reader.

These tests are written over **pipeline spelling**, because that is the case
that was broken and the case that was not covered: ``test_book_scaffolding.py``
already had a ``test_difficulty_breakdown``, but it recomputed the production
expression inside the test body, so it asserted the formula against itself and
would have passed no matter what production did.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from nonogram.admin.book_pdf_generator import BookPDFGenerator, tier_breakdown
from nonogram.admin.puzzle_review import PuzzleFilter, PuzzleReviewService
from nonogram.difficulty import Tier


def _rows(*tiers: str | None) -> list[dict[str, object]]:
    return [{"id": f"p{i}", "difficulty_tier": t} for i, t in enumerate(tiers)]


# --------------------------------------------------------------------------
# The breakdown both the finalize screen and the printed guide page read
# --------------------------------------------------------------------------


def test_the_breakdown_counts_rows_written_by_the_pipeline() -> None:
    """The defect exactly: lowercase rows used to count as nothing."""
    counts = tier_breakdown(_rows("easy", "easy", "medium", "hard"))

    assert counts[Tier.EASY] == 2
    assert counts[Tier.MEDIUM] == 1
    assert counts[Tier.HARD] == 1


def test_the_breakdown_counts_both_spellings_as_one_tier() -> None:
    """A book may hold rows from before and after the pipeline wrote them."""
    counts = tier_breakdown(_rows("easy", "Easy", "HARD", "hard"))

    assert counts[Tier.EASY] == 2
    assert counts[Tier.HARD] == 2


def test_the_breakdown_counts_the_fourth_tier() -> None:
    """ADR-0025's Guess is a tier of the book, not a row that vanishes."""
    counts = tier_breakdown(_rows("guess", "Guess", "easy"))

    assert counts[Tier.GUESS] == 2
    assert counts[Tier.EASY] == 1


def test_unreadable_tiers_are_counted_in_no_tier_rather_than_guessed_at() -> None:
    """The totals must never exceed the puzzle count.

    A missing or junk tier is not evidence for any tier, so it is counted in
    none — the alternative, folding it into Easy or Hard, would put a puzzle
    nobody graded into a book that claims a grade for it.
    """
    rows = _rows("easy", None, "", "extreme", "guess")
    counts = tier_breakdown(rows)

    assert sum(counts.values()) == 2
    assert counts[Tier.EASY] == 1
    assert counts[Tier.GUESS] == 1


def test_every_tier_reads_zero_rather_than_missing_on_an_empty_book() -> None:
    """Indexable without a ``get`` — which is why it returns a Counter."""
    counts = tier_breakdown([])

    assert [counts[tier] for tier in Tier] == [0, 0, 0, 0]


# --------------------------------------------------------------------------
# The printed guide page
# --------------------------------------------------------------------------


def test_the_guide_page_renders_with_a_guess_count() -> None:
    """The fourth count is a real parameter, not a dict the template ignores."""
    guide = BookPDFGenerator().create_guide_page(
        puzzle_count=10, easy_count=3, medium_count=4, hard_count=2, guess_count=1
    )

    assert guide is not None
    assert guide.mode == "RGB"


def test_the_guide_page_still_takes_three_counts() -> None:
    """``guess_count`` defaults, so every existing caller keeps working.

    A book with no Guess puzzles omits the line entirely, so a book of
    line-solvable puzzles prints exactly the guide it printed before the tier
    existed.
    """
    guide = BookPDFGenerator().create_guide_page(
        puzzle_count=10, easy_count=3, medium_count=4, hard_count=3
    )

    assert guide is not None


# --------------------------------------------------------------------------
# The puzzle-list difficulty filter
# --------------------------------------------------------------------------


def _service_holding(*tiers: str | None) -> PuzzleReviewService:
    """An in-memory service (no session factory) holding one row per tier given.

    ``filter_puzzles`` takes the legacy in-memory branch when there is no
    session factory, which is the branch these tests need: the defect was the
    comparison, and the comparison is reachable without a database.
    """
    service = PuzzleReviewService()
    for index, tier in enumerate(tiers):
        service.puzzles[f"p{index}"] = {
            "id": f"p{index}",
            "puzzle_name": f"P{index}",
            "width": 10,
            "height": 10,
            "difficulty_tier": tier,
            "difficulty_score": 33,
            "quality_score": 50,
            "status": "approved",
            "created_at": datetime(2026, 9, 13, tzinfo=timezone.utc),
        }
    return service


def _ids(response: object) -> set[str]:
    return {puzzle["id"] for puzzle in response.puzzles}


@pytest.mark.parametrize("requested", ["easy", "Easy", "EASY", "  easy  "])
def test_the_filter_selects_pipeline_rows_whatever_the_form_submitted(
    requested: str,
) -> None:
    """The form submits a label; a pipeline row holds a value. Both must match.

    This is the defect end to end: before the fix, ``difficulty=Easy`` — which
    is exactly what the select element submits — returned an empty list on a
    page full of generated easy puzzles.
    """
    service = _service_holding("easy", "Easy", "hard", "medium")

    selected = service.filter_puzzles(PuzzleFilter(difficulty=requested))

    assert _ids(selected) == {"p0", "p1"}


def test_the_filter_selects_the_fourth_tier() -> None:
    """``guess`` is offered by the form, so it has to select its rows."""
    service = _service_holding("guess", "Guess", "hard")

    selected = service.filter_puzzles(PuzzleFilter(difficulty="Guess"))

    assert _ids(selected) == {"p0", "p1"}


def test_a_query_string_that_names_no_tier_does_not_widen_the_filter() -> None:
    """Junk must not silently return the whole table.

    The tolerant branch fires only when the requested value actually names a
    tier; anything else keeps the exact-string comparison it always had. A
    filter that matched everything on a typo would be a worse failure than the
    one being fixed, because it would look like it worked.
    """
    service = _service_holding("easy", "hard", "guess")

    selected = service.filter_puzzles(PuzzleFilter(difficulty="extreme"))

    assert _ids(selected) == set()


def test_a_row_with_no_tier_is_selected_by_no_tier_filter() -> None:
    """An ungraded row belongs to no band, so no band's filter may claim it."""
    service = _service_holding(None, "easy")

    for requested in ("easy", "medium", "hard", "guess"):
        selected = service.filter_puzzles(PuzzleFilter(difficulty=requested))
        assert "p0" not in _ids(selected), f"{requested} claimed an ungraded row"
