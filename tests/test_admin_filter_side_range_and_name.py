"""The review page's size filter is a side range, and its name search sees
what the page shows.

Both filters used to answer a question nobody asked. ``size`` matched an
exact square extent, but almost no picture-derived grid is square (a 20×30
butterfly was unreachable by any single number). ``puzzle_name`` was a
substring search — but over ``puzzle_name`` only, and a pipeline-written row
carries none: the page lists it under ``source_image``, so searching for the
name on screen found nothing.

Now ``size_from``/``size_to`` bound *either* side, and the name search covers
both fields. The exact-extent ``size`` stays for the API.
"""

from __future__ import annotations

import re

import pytest

from nonogram.admin.puzzle_review import PuzzleFilter, PuzzleReviewService
from nonogram.limits import MAX_SIZE, MIN_SIZE


@pytest.fixture
def admin_app(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TESTING", "true")
    from nonogram.admin.app import create_app

    app = create_app()
    app.config["TESTING"] = True
    with app.app_context():
        yield app


def _add(service: PuzzleReviewService, width, height, *, name=None, source=None):
    """Store one all-filled (hence uniquely solvable) grid."""
    puzzle_id = service.add_puzzle(
        grid=[[True] * width for _ in range(height)],
        clues_rows=[[width] for _ in range(height)],
        clues_cols=[[height] for _ in range(width)],
        width=width,
        height=height,
        theme="test",
        difficulty_score=10,
        difficulty_tier="Medium",
        quality_score=90,
        recognizability="medium",
        strategies_used=[],
        source_image=source,
    )
    if name is not None:
        # add_puzzle takes no name; the pipeline sets it afterwards.
        service.puzzles[puzzle_id]["puzzle_name"] = name
    return puzzle_id


def _names(body: str) -> list:
    return re.findall(r'class="name"[^>]*>([^<]+)<', body)


# --------------------------------------------------------------------------
# Side range
# --------------------------------------------------------------------------


def test_a_range_matches_when_either_side_falls_inside():
    service = PuzzleReviewService()
    tall = _add(service, 20, 30, source="butterfly3.jpg")
    wide = _add(service, 27, 20, source="butterfly1.png")
    small = _add(service, 10, 10, source="dot.png")

    found = {p["id"] for p in service.filter_puzzles(PuzzleFilter(side_range=(25, 30))).puzzles}

    assert found == {tall, wide}, "30 and 27 are inside 25–30; no side of the 10×10 is"
    assert small not in found


def test_an_open_bound_means_the_supported_limit():
    service = PuzzleReviewService()
    _add(service, 10, 10, source="dot.png")
    _add(service, 20, 30, source="butterfly3.jpg")

    from_only = service.filter_puzzles(PuzzleFilter(side_range=(21, None))).puzzles
    to_only = service.filter_puzzles(PuzzleFilter(side_range=(None, 10))).puzzles

    assert [p["source_image"] for p in from_only] == ["butterfly3.jpg"]
    assert [p["source_image"] for p in to_only] == ["dot.png"]


@pytest.mark.parametrize(
    "side_range",
    [(MAX_SIZE + 1, None), (None, MIN_SIZE - 1), (25, 15), (5, 5)],
)
def test_an_impossible_range_is_reported_not_swallowed(side_range):
    service = PuzzleReviewService()
    with pytest.raises(ValueError):
        service.filter_puzzles(PuzzleFilter(side_range=side_range))


def test_the_page_reads_from_and_to_and_keeps_them_in_pagination(admin_app):
    service = admin_app.puzzle_review_service
    for _ in range(3):
        _add(service, 20, 30, source="butterfly3.jpg")
    _add(service, 10, 10, source="dot.png")

    body = admin_app.test_client().get("/puzzles?size_from=25&size_to=30&limit=2").get_data(as_text=True)

    assert "Puzzles (3 total)" in body
    assert "dot" not in _names(body)
    assert "size_from=25&amp;size_to=30" in body, "the page links must carry the range forward"


def test_an_inverted_range_on_the_page_is_a_filter_error(admin_app):
    body = admin_app.test_client().get("/puzzles?size_from=25&size_to=15").get_data(as_text=True)
    assert "Filter error" in body


def test_the_exact_size_parameter_still_works_for_the_api(admin_app):
    service = admin_app.puzzle_review_service
    _add(service, 20, 20, source="square.png")
    _add(service, 20, 30, source="tall.png")

    data = admin_app.test_client().get("/api/puzzles?size=20").get_json()

    assert [p["source_image"] for p in data["puzzles"]] == ["square.png"]


# --------------------------------------------------------------------------
# Name search
# --------------------------------------------------------------------------


def test_the_name_search_finds_a_row_listed_under_its_source_image():
    service = PuzzleReviewService()
    _add(service, 20, 20, source="butterflies/butterfly1.png")
    _add(service, 20, 20, name="Raven", source="raven1.jpg")
    _add(service, 20, 20, source="crab2.jpg")

    by_source = service.filter_puzzles(PuzzleFilter(puzzle_name="BUTTER")).puzzles
    by_name = service.filter_puzzles(PuzzleFilter(puzzle_name="rav")).puzzles

    assert [p["source_image"] for p in by_source] == ["butterflies/butterfly1.png"]
    assert [p["puzzle_name"] for p in by_name] == ["Raven"]


def test_the_name_search_is_a_substring_on_the_page(admin_app):
    service = admin_app.puzzle_review_service
    _add(service, 20, 20, source="crab2.jpg")
    _add(service, 20, 20, source="crab6.jpg")
    _add(service, 20, 20, source="owl1.png")

    body = admin_app.test_client().get("/puzzles?puzzle_name=crab").get_data(as_text=True)

    assert "Puzzles (2 total)" in body
    assert sorted(_names(body)) == ["crab2.jpg", "crab6.jpg"]
