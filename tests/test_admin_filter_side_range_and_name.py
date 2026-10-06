"""The review page's size filter is a side range, and its name search sees
what the page shows.

Both filters used to answer a question nobody asked. ``size`` matched an
exact square extent, but almost no picture-derived grid is square (a 20×30
butterfly was unreachable by any single number). ``puzzle_name`` was a
substring search — but over ``puzzle_name`` only, and a pipeline-written row
carries none: the page lists it under ``source_image``, so searching for the
name on screen found nothing.

Now ``size_from``/``size_to`` bound the grid's *longest* side — the same
``PuzzleFilter.longest_side_range`` the book's tabs use, so a 25×15 counts as
25 only (CARD-190; before it they bounded *either* side). The name search
covers both fields. The exact-extent ``size`` stays for the API.
"""

from __future__ import annotations

import dataclasses
import re

import pytest

import nonogram.admin.book_manager as book_manager_module
from nonogram.admin.book_manager import BookManager
from nonogram.admin.puzzle_review import BOOK_TAB_SORT, PuzzleFilter, PuzzleReviewService
from nonogram.limits import MAX_SIZE, MIN_SIZE
from tests.helpers.db import sqlite_session_scope


@pytest.fixture
def admin_app(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TESTING", "true")
    from nonogram.admin.app import create_app

    app = create_app()
    app.config["TESTING"] = True
    with app.app_context():
        yield app


def _add(service: PuzzleReviewService, width, height, *, name=None, source=None, tier="Medium"):
    """Store one all-filled (hence uniquely solvable) grid.

    ``tier`` is the *stored spelling*, passed through untouched: a row carries
    either the enum value or the display label, and CARD-122's tier-rank sort
    has to rank both the same way (it reads them through
    ``difficulty.tier_of_record``).
    """
    puzzle_id = service.add_puzzle(
        grid=[[True] * width for _ in range(height)],
        clues_rows=[[width] for _ in range(height)],
        clues_cols=[[height] for _ in range(width)],
        width=width,
        height=height,
        theme="test",
        difficulty_score=10,
        difficulty_tier=tier,
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
# The page's size from/to (CARD-190): the longest side
# --------------------------------------------------------------------------


def test_an_open_bound_means_the_supported_limit():
    service = PuzzleReviewService()
    _add(service, 10, 10, source="dot.png")
    _add(service, 20, 30, source="butterfly3.jpg")

    from_only = service.filter_puzzles(PuzzleFilter(longest_side_range=(21, None))).puzzles
    to_only = service.filter_puzzles(PuzzleFilter(longest_side_range=(None, 10))).puzzles

    assert [p["source_image"] for p in from_only] == ["butterfly3.jpg"]
    assert [p["source_image"] for p in to_only] == ["dot.png"]


STORES = ("memory", "sqlite")


def _build_app(store, scope, monkeypatch):
    """The panel on the named store — CARD-160's ``_build_app``."""
    from nonogram.admin.app import create_app

    monkeypatch.setenv("TESTING", "true")
    if store == "memory":
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setattr(book_manager_module, "_book_manager", BookManager(session_factory=None))
    else:
        import nonogram.db

        monkeypatch.setenv("DATABASE_URL", "sqlite:///card-190-test-only")
        monkeypatch.setattr(nonogram.db, "session_scope", scope)
    app = create_app()
    app.config["TESTING"] = True
    # The tests must exercise the store they name, not silently fall back.
    assert (app.puzzle_review_service._session_factory is None) == (store == "memory")
    return app


@pytest.fixture(params=STORES)
def panel(request, tmp_path, monkeypatch):
    scope = sqlite_session_scope(tmp_path, "card-190.db") if request.param == "sqlite" else None
    return _build_app(request.param, scope, monkeypatch)


def _page(panel, query: str) -> str:
    response = panel.test_client().get(f"/puzzles?{query}")
    assert response.status_code == 200, response.status_code
    return response.get_data(as_text=True)


class TestPuzzleReview_SizeFilterUsesLongestSide:
    """AC-1 (memory) / AC-2 (sqlite): a 25×15 counts as 25 only.

    10–15 is the discriminator: the 25×15's short side is in it, so the old
    either-side filter listed both rows there.
    """

    @pytest.fixture
    def corpus(self, panel):
        _add(panel.puzzle_review_service, 25, 15, source="wide-25x15.png")
        _add(panel.puzzle_review_service, 15, 12, source="small-15x12.png")
        return panel

    def test_ten_to_fifteen_lists_only_the_15x12(self, corpus):
        body = _page(corpus, "size_from=10&size_to=15")

        assert "Puzzles (1 total)" in body
        assert _names(body) == ["small-15x12.png"]

    def test_twenty_one_to_twenty_five_lists_only_the_25x15(self, corpus):
        body = _page(corpus, "size_from=21&size_to=25")

        assert "Puzzles (1 total)" in body
        assert _names(body) == ["wide-25x15.png"]


class TestPuzzleReview_SizeFilterPagesItsOwnMembers:
    """AC-3: the store pages the longest-side members, so the total is theirs
    and the first page holds none of the wide rows, and the range is carried
    forward both by the pagination links and by the ``return_to`` the row
    actions redirect back through."""

    def test_the_total_counts_members_and_the_links_keep_the_range(self, panel):
        service = panel.puzzle_review_service
        for n in range(5):
            _add(service, 30, 12, source=f"wide{n}.png")
        for n in range(3):
            _add(service, 14, 12, source=f"small{n}.png")

        body = _page(panel, "size_from=10&size_to=15&limit=2")

        assert "Puzzles (3 total)" in body
        names = _names(body)
        assert len(names) == 2 and all(name.startswith("small") for name in names), names
        # The row actions' return_to (an escaped attribute value)...
        assert "size_from=10&amp;size_to=15" in body
        # ...and every pagination link (the macro's literal ``&``, unescaped).
        page_links = re.findall(r'class="page-link" href="([^"]*)"', body)
        assert page_links, "3 members at limit=2 is more than one page"
        assert all("size_from=10&size_to=15&" in href for href in page_links), page_links


class TestPuzzlesApi_SizeRangeUsesLongestSide:
    """AC-4: the API shares the page's helper, so it means the same."""

    def test_the_api_lists_only_the_15x12(self, admin_app):
        service = admin_app.puzzle_review_service
        _add(service, 25, 15, source="wide-25x15.png")
        _add(service, 15, 12, source="small-15x12.png")

        data = admin_app.test_client().get("/api/puzzles?size_from=10&size_to=15").get_json()

        assert [p["source_image"] for p in data["puzzles"]] == ["small-15x12.png"]


class TestPuzzleReview_SizeFilterLabelSaysLongestSide:
    """AC-5: book selection's wording, and no "either side" left."""

    def test_the_field_is_labelled_longest_side(self, admin_app):
        body = admin_app.test_client().get("/puzzles").get_data(as_text=True)

        assert '<label for="size_from" class="form-label">Longest side (cells)</label>' in body
        assert re.search(r'<input[^>]*id="size_from"[^>]*aria-label="Longest side from"', body)
        assert re.search(r'<input[^>]*id="size_to"[^>]*aria-label="Longest side to"', body)
        assert "either side" not in body.lower()


def test_the_filter_has_no_either_side_field_any_more():
    """AC-6: ``side_range`` is gone, not merely unused."""
    assert "side_range" not in {f.name for f in dataclasses.fields(PuzzleFilter)}
    with pytest.raises(TypeError):
        PuzzleFilter(side_range=(10, 15))


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
# Longest-side range (CARD-122) — a different question from the one above
# --------------------------------------------------------------------------


def test_a_longest_side_range_asks_about_max_width_height_not_either_side():
    """A 30x12 has a side in 10-15, but its longest side is 30, so it belongs
    to the 26-30 tab and to no other.
    """
    service = PuzzleReviewService()
    _add(service, 30, 12, source="tall.png")
    small = _add(service, 15, 12, source="small.png")

    longest = {
        p["id"]
        for p in service.filter_puzzles(PuzzleFilter(longest_side_range=(10, 15))).puzzles
    }

    assert longest == {small}, "a 30x12's longest side is 30, so 10-15 does not hold it"


def test_the_longest_side_range_pages_its_own_members_and_counts_them():
    """LIMIT has to bite on the members, and the total has to be theirs.

    The wide rows sort first under the default sort, so a superset query would
    fill the first page with rows the caller asked to exclude.
    """
    service = PuzzleReviewService()
    wide = [_add(service, 30, 12, source=f"wide{n}.png") for n in range(6)]
    small = [_add(service, 14, 12, source=f"small{n}.png") for n in range(4)]

    page = service.filter_puzzles(PuzzleFilter(longest_side_range=(10, 15), limit=2))
    found = {p["id"] for p in page.puzzles}

    assert page.total_count == len(small)
    assert found <= set(small) and len(found) == 2
    assert page.has_more
    assert not found & set(wide)


def test_a_row_outside_the_supported_range_belongs_to_no_longest_side_range():
    """A row stored under an older size limit belongs to no bucket at all —
    the verdict ``book_plan.bucket_of`` makes on the same row."""
    service = PuzzleReviewService()
    legacy = _add(service, 12, 12, source="legacy.png")
    service.puzzles[legacy]["width"] = MAX_SIZE + 20

    every_range = service.filter_puzzles(PuzzleFilter(longest_side_range=(MIN_SIZE, MAX_SIZE)))

    assert every_range.total_count == 0, "an out-of-range row must not land in a bucket"


@pytest.mark.parametrize(
    "longest_side_range",
    [(MAX_SIZE + 1, None), (None, MIN_SIZE - 1), (25, 15), (5, 5)],
)
def test_an_impossible_longest_side_range_is_reported_too(longest_side_range):
    service = PuzzleReviewService()
    with pytest.raises(ValueError):
        service.filter_puzzles(PuzzleFilter(longest_side_range=longest_side_range))


# --------------------------------------------------------------------------
# The book tab's order (CARD-122, review cycle 2 F-001) — a store-level key,
# because LIMIT/OFFSET have to slice *it*
# --------------------------------------------------------------------------


def _ordered(service, **kwargs):
    return [p["id"] for p in service.filter_puzzles(PuzzleFilter(**kwargs)).puzzles]


#: A tab's worth of rows: 12 distinct ``(shorter, longer)`` extents inside
#: 21-25, tiers round-robined across them and the two spellings mixed, so no
#: two rows tie on ``(tier rank, shorter side, longer side)`` and the id
#: tie-break never decides. That matters for the cross-backend case below,
#: where the two stores mint different ids for the same row.
_A_TAB_WORTH_OF_ROWS = [
    ((22 + (n % 4), 10 + n), f"row{n:02d}.png", ("easy", "Medium", "hard")[n % 3])
    for n in range(12)
]


def test_the_book_tab_sort_orders_by_tier_rank_then_shorter_side():
    """Tier *rank*, not the tier string: alphabetically "hard" precedes
    "medium" precedes "easy"'s opposite, and none of that is the book order.
    """
    service = PuzzleReviewService()
    hard = _add(service, 25, 21, source="hard.png", tier="hard")
    easy_wide = _add(service, 25, 18, source="easy-wide.png", tier="Easy")  # other spelling
    easy_narrow = _add(service, 22, 16, source="easy-narrow.png", tier="easy")
    medium = _add(service, 25, 25, source="medium.png", tier="medium")

    assert _ordered(service, sort_by=BOOK_TAB_SORT) == [
        easy_narrow, easy_wide, medium, hard
    ]


def test_an_ungraded_row_sorts_after_every_graded_one():
    service = PuzzleReviewService()
    graded = _add(service, 25, 25, source="graded.png")
    ungraded = _add(service, 22, 10, source="ungraded.png")
    service.puzzles[ungraded]["difficulty_tier"] = "not a tier at all"

    assert _ordered(service, sort_by=BOOK_TAB_SORT) == [graded, ungraded]


def test_limit_slices_the_book_tab_order_rather_than_some_other_one():
    """The finding itself, at the store: the first page of a sorted query is
    the *first* rows of that order, so a route need not (and must not) re-sort
    the page it is handed."""
    service = PuzzleReviewService()
    built = [_add(service, *extent, source=source, tier=tier)
             for extent, source, tier in _A_TAB_WORTH_OF_ROWS]

    whole = _ordered(service, sort_by=BOOK_TAB_SORT, limit=len(built))
    pages = [
        _ordered(service, sort_by=BOOK_TAB_SORT, limit=5, offset=offset)
        for offset in (0, 5, 10)
    ]

    assert sorted(whole) == sorted(built)
    assert [pid for page in pages for pid in page] == whole


def test_both_backends_spell_the_same_book_tab_order(tmp_path):
    """The SQL branch has to *be* the Python one, not resemble it.

    The two are separate implementations — a CASE ladder over
    ``trim(lower(difficulty_tier))`` and two more over the extent pair, against
    ``tier_of_record`` and ``min``/``max`` in Python — so the only honest check
    is to run the same corpus through both and compare the rendered order.
    Rows are compared by ``source_image``: the ids differ by construction
    (UUID against ``puzzle_NNNNNN``), and the corpus has no tie for the id to
    break.
    """
    in_memory = PuzzleReviewService()
    on_disk = PuzzleReviewService(session_factory=sqlite_session_scope(tmp_path))
    for extent, source, tier in _A_TAB_WORTH_OF_ROWS:
        for service in (in_memory, on_disk):
            _add(service, *extent, source=source, tier=tier)

    def sources(service, **kwargs):
        return [p["source_image"] for p in service.filter_puzzles(PuzzleFilter(**kwargs)).puzzles]

    expected = sources(in_memory, sort_by=BOOK_TAB_SORT, limit=len(_A_TAB_WORTH_OF_ROWS))

    assert len(expected) == len(_A_TAB_WORTH_OF_ROWS)
    assert sources(on_disk, sort_by=BOOK_TAB_SORT, limit=len(expected)) == expected
    # ...and the pages of it agree too, which is the property the tab needs.
    assert [
        source
        for offset in (0, 5, 10)
        for source in sources(on_disk, sort_by=BOOK_TAB_SORT, limit=5, offset=offset)
    ] == expected


def test_the_database_branch_of_the_longest_side_range_narrows_to_the_bucket(tmp_path):
    """The DB half of cycle 1's fix, run rather than reasoned about: the CASE
    over ``max(width, height)`` has to exclude a row whose *short* side is in
    range, and a row outside MIN_SIZE..MAX_SIZE entirely."""
    service = PuzzleReviewService(session_factory=sqlite_session_scope(tmp_path))
    _add(service, 30, 12, source="tall.png")
    _add(service, 14, 12, source="small.png")

    page = service.filter_puzzles(PuzzleFilter(longest_side_range=(10, 15)))

    assert [p["source_image"] for p in page.puzzles] == ["small.png"]
    assert page.total_count == 1


def test_the_existing_sort_tokens_still_mean_what_they_meant():
    """CARD-122's tokens are additive: the default the puzzle-list and batch
    routes drive is untouched, and so is every token it is made of."""
    service = PuzzleReviewService()
    small = _add(service, 12, 30, source="small.png")
    big = _add(service, 28, 10, source="big.png")

    assert PuzzleFilter().sort_by == "batch_id,-size,quality"
    assert _ordered(service, sort_by="-size") == [big, small]
    assert _ordered(service, sort_by="size") == [small, big]
    assert _ordered(service, sort_by="height") == [big, small]


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
