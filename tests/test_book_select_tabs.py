"""CARD-122 — puzzle selection in four longest-side tabs (FR-036, BK-UI-4/5/6).

    AC-208  a 15x30 is offered on the 26-30 tab only
    AC-209  a 15x16 is offered on 16-20, not on <=15
    AC-210  a 15x15 is offered on <=15
    AC-211  a selection survives a tab switch and the way back
    AC-212  a tab header reads selected / planned per tier
    AC-213  an over-plan cell is marked as over
    AC-214  the whole-book summary above the tabs sums every tab
    AC-215  a tab sorts by tier, then by shorter side ascending
    AC-216  the size-range filter is gone, replaced by the tab
    AC-217  the surviving filters still apply inside a tab
    EC-024  every available puzzle appears on exactly one rendered tab

The evidence class is the Flask test client: these are user-facing criteria on
a server-rendered screen and this project has no browser harness, so each one
GETs or POSTs the real route and reads the real HTML it rendered.
"""

from __future__ import annotations

import html as html_module
import random
import re

import pytest

import nonogram.admin.book_manager as book_manager_module
import nonogram.admin.image_manager as image_manager_module
from nonogram.admin.book_manager import BookManager
from nonogram.admin.book_plan import (
    BUCKETS,
    TIERS,
    DistributionPlan,
    LongestSideBucket,
    Split,
    bucket_of,
)
from nonogram.limits import MAX_SIZE, MIN_SIZE


# --------------------------------------------------------------------------
# fixtures and helpers
# --------------------------------------------------------------------------


@pytest.fixture
def admin_app(monkeypatch):
    """The panel in in-memory mode, with a book manager of its own."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TESTING", "true")
    from nonogram.admin.app import create_app

    image_manager_module._image_manager = None
    book_manager_module._book_manager = BookManager(session_factory=None)
    app = create_app()
    app.config["TESTING"] = True
    with app.app_context():
        yield app
    image_manager_module._image_manager = None


class Panel:
    """The app, its store and its books, with the one-liners the ACs need."""

    def __init__(self, app):
        self.app = app
        self.store = app.puzzle_review_service
        self.books = app.book_manager
        self.client = app.test_client()

    def puzzle(self, width, height, tier="easy", *, theme="generic", quality=50, name=None):
        """An approved puzzle of that extent. The grid is solid, so the
        uniqueness proof the store insists on (ADR-0032/R1) is trivial."""
        puzzle_id = self.store.add_puzzle(
            grid=[[True] * width for _ in range(height)],
            clues_rows=[[width]] * height,
            clues_cols=[[height]] * width,
            width=width,
            height=height,
            theme=theme,
            difficulty_score=10,
            difficulty_tier=tier,
            quality_score=quality,
            recognizability="medium",
            strategies_used=[],
            batch_id=None,
            source_image=name or f"{width}x{height}-{tier}.png",
        )
        self.store.approve_puzzle(puzzle_id)
        return puzzle_id

    def book(self, title="Winter"):
        return self.books.create_book(title, "a book", "christmas", "adults")

    def plan_less_book(self, title="No plan"):
        """A book with no stored plan — one made before migration 010.

        Every book created today starts on DEFAULT_PLAN (ADR-0034), so the
        only way to reach ADR-0035's plan-less remedy is to drop the stored
        document the way an un-migrated row has none.
        """
        book_id = self.book(title)
        self.books._plans.pop(book_id, None)
        assert self.books.get_plan(book_id) is None
        return book_id

    def tab(self, book_id, bucket, **query):
        """The rendered HTML of one tab."""
        args = "&".join(f"{k}={v}" for k, v in {"bucket": bucket.label, **query}.items())
        response = self.client.get(f"/book/{book_id}/select-puzzles?{args}")
        assert response.status_code == 200
        return response.get_data(as_text=True)

    def offered(self, body):
        """The puzzle ids the rendered tab offers, in the order it lists them."""
        return re.findall(r'name="shown_ids" value="([^"]+)"', body)

    def ticked(self, body):
        """The ids whose checkbox the rendered tab shows already ticked."""
        return {
            match.group(1)
            for match in re.finditer(r'name="puzzle_ids" value="([^"]+)"([^>]*)', body)
            if "checked" in match.group(2)
        }


@pytest.fixture
def panel(admin_app):
    return Panel(admin_app)


def text_of(html):
    """The rendered page as readable text: no tags, no entities, one space."""
    without_scripts = re.sub(r"(?s)<script.*?</script>", " ", html)
    return re.sub(r"\s+", " ", html_module.unescape(re.sub(r"<[^>]+>", " ", without_scripts))).strip()


def summary_of(html, element_id):
    """The text of one summary line (``bookSummary`` or ``tabSummary``)."""
    match = re.search(rf'(?s)<p class="stat-line" id="{element_id}"[^>]*>(.*?)</p>', html)
    assert match, f"the page has no #{element_id} summary line"
    return text_of(match.group(1))


def plan_of(cells, count=150, split=(40, 40, 20)):
    """A DistributionPlan whose 4x3 matrix is ``cells``, rows in BUCKETS order."""
    return DistributionPlan(count=count, split=Split(*split), cells=cells)


#: Four buckets, named for the tests that talk about one of them.
UP_TO_15 = LongestSideBucket.UP_TO_15
FROM_16_TO_20 = LongestSideBucket.FROM_16_TO_20
FROM_21_TO_25 = LongestSideBucket.FROM_21_TO_25
FROM_26_TO_30 = LongestSideBucket.FROM_26_TO_30


# --------------------------------------------------------------------------
# AC-208 / AC-209 / AC-210 — which tab a puzzle is listed on
# --------------------------------------------------------------------------


class TestBookSelect_PuzzleListedUnderLongestSideTab:
    """AC-208: a 15 x 30 belongs to 26-30 — the longest side alone decides."""

    def test_the_tall_puzzle_is_on_the_26_30_tab_only(self, panel):
        puzzle_id = panel.puzzle(15, 30)
        book_id = panel.book()

        holding = [
            bucket for bucket in BUCKETS
            if puzzle_id in panel.offered(panel.tab(book_id, bucket))
        ]

        assert holding == [FROM_26_TO_30], (
            "a 15x30 puzzle is bucketed by max(width, height) = 30, so it belongs "
            f"on the 26-30 tab and on no other; it appeared on {[b.label for b in holding]}"
        )


class TestBookSelect_LongestSideSixteenGoesToSecondTab:
    """AC-209: 16 is the first side that leaves the <=15 tab."""

    def test_the_fifteen_by_sixteen_is_on_16_20_not_on_up_to_15(self, panel):
        puzzle_id = panel.puzzle(15, 16)
        book_id = panel.book()

        assert puzzle_id in panel.offered(panel.tab(book_id, FROM_16_TO_20))
        assert puzzle_id not in panel.offered(panel.tab(book_id, UP_TO_15))


class TestBookSelect_LongestSideFifteenGoesToFirstTab:
    """AC-210: 15 x 15 is the last extent the first tab holds."""

    def test_the_fifteen_square_is_on_the_up_to_15_tab(self, panel):
        puzzle_id = panel.puzzle(15, 15)
        book_id = panel.book()

        assert puzzle_id in panel.offered(panel.tab(book_id, UP_TO_15))
        assert puzzle_id not in panel.offered(panel.tab(book_id, FROM_16_TO_20))


# --------------------------------------------------------------------------
# AC-211 — a selection survives a tab switch
# --------------------------------------------------------------------------


class TestBookSelect_SelectionKeptAcrossTabSwitch:
    """AC-211: three ticked on <=15, away to 21-25 and back, still three."""

    def test_the_three_are_still_ticked_after_the_round_trip(self, panel):
        picked = [panel.puzzle(12, 12), panel.puzzle(13, 14), panel.puzzle(15, 15)]
        panel.puzzle(22, 24)  # a tile on the far tab, deliberately left alone
        book_id = panel.book()
        url = f"/book/{book_id}/select-puzzles"

        # Tick the three, then use the 21-25 tab button to leave.
        away = panel.client.post(url, data={
            "bucket": UP_TO_15.label,
            "shown_ids": picked,
            "puzzle_ids": picked,
            "go_bucket": FROM_21_TO_25.label,
        })
        assert away.status_code == 302
        assert f"bucket={FROM_21_TO_25.label}" in html_module.unescape(away.headers["Location"])

        far_tab = panel.client.get(away.headers["Location"]).get_data(as_text=True)
        assert panel.ticked(far_tab) == set(), "the far tab pre-ticked something"

        # ... and back again, with the far tab's (empty) submission folded in.
        back = panel.client.post(url, data={
            "bucket": FROM_21_TO_25.label,
            "shown_ids": panel.offered(far_tab),
            "go_bucket": UP_TO_15.label,
        })
        first_tab = panel.client.get(back.headers["Location"]).get_data(as_text=True)

        assert panel.ticked(first_tab) == set(picked), "the selection did not survive the tab switch"
        assert "3 puzzles selected" in text_of(first_tab)

    def test_untouched_tabs_are_still_committed_when_the_step_is_submitted(self, panel):
        """The whole kept selection joins the book, not just the last tab's."""
        small = panel.puzzle(12, 12)
        large = panel.puzzle(22, 24)
        book_id = panel.book()
        url = f"/book/{book_id}/select-puzzles"

        panel.client.post(url, data={
            "bucket": UP_TO_15.label,
            "shown_ids": [small],
            "puzzle_ids": [small],
            "go_bucket": FROM_21_TO_25.label,
        })
        done = panel.client.post(url, data={
            "bucket": FROM_21_TO_25.label,
            "shown_ids": [large],
            "puzzle_ids": [large],
        })

        assert done.status_code == 302
        assert "arrange-puzzles" in done.headers["Location"]
        assert set(panel.books.get_book(book_id).puzzle_ids) == {small, large}

    def test_unticking_a_tile_on_its_own_tab_drops_it(self, panel):
        """Keeping a selection is not the same as never letting go of one."""
        first, second = panel.puzzle(12, 12), panel.puzzle(13, 13)
        book_id = panel.book()
        url = f"/book/{book_id}/select-puzzles"

        panel.client.post(url, data={
            "bucket": UP_TO_15.label,
            "shown_ids": [first, second],
            "puzzle_ids": [first, second],
            "go_bucket": UP_TO_15.label,
        })
        back = panel.client.post(url, data={
            "bucket": UP_TO_15.label,
            "shown_ids": [first, second],
            "puzzle_ids": [first],
            "go_bucket": UP_TO_15.label,
        })

        body = panel.client.get(back.headers["Location"]).get_data(as_text=True)
        assert panel.ticked(body) == {first}


# --------------------------------------------------------------------------
# AC-212 / AC-213 / AC-214 — planned vs selected
# --------------------------------------------------------------------------


class TestBookSelect_TabHeaderShowsPlannedVsActual:
    """AC-212: the 21-25 header reads easy 8 / 10 · medium 20 / 20 · hard 14 / 12."""

    def test_the_tab_header_reads_selected_over_planned_per_tier(self, panel):
        book_id = panel.book()
        panel.books.save_plan(book_id, plan_of(((0, 0, 0), (0, 0, 0), (10, 20, 12), (0, 0, 0))))

        selected = []
        for tier, how_many in (("easy", 8), ("medium", 20), ("hard", 14)):
            selected += [panel.puzzle(21, 25, tier) for _ in range(how_many)]
        panel.books.add_puzzles_to_book(book_id, selected)

        header = summary_of(panel.tab(book_id, FROM_21_TO_25), "tabSummary")

        assert "21-25: easy 8 / 10 · medium 20 / 20 · hard 14 / 12" in header, header

    def test_a_book_with_no_plan_shows_the_counts_and_points_at_print_setup(self, panel):
        """ADR-0035's remedy: no plan is not a blank screen."""
        book_id = panel.plan_less_book()
        panel.books.add_puzzles_to_book(book_id, [panel.puzzle(22, 22, "medium")])

        body = panel.tab(book_id, FROM_21_TO_25)
        header = summary_of(body, "tabSummary")

        assert "21-25: easy 0 · medium 1 · hard 0 · total 1" in header, header
        assert "/" not in header, "a plan-less book must not invent a planned figure"
        assert f"/book/{book_id}/setup-print" in body


class TestBookSelect_OverPlanCellMarked:
    """AC-213: 14 hard against a plan of 12 is shown as over, not hidden."""

    def test_the_over_plan_cell_carries_the_over_marker(self, panel):
        book_id = panel.book()
        panel.books.save_plan(book_id, plan_of(((0, 0, 0), (0, 0, 0), (10, 20, 12), (0, 0, 0))))
        panel.books.add_puzzles_to_book(
            book_id, [panel.puzzle(21, 25, "hard") for _ in range(14)]
        )

        body = panel.tab(book_id, FROM_21_TO_25)
        marked = {
            text_of(content): 'data-over="true"' in attributes
            for attributes, content in re.findall(
                r'<span class="stat-cell"([^>]*)>([^<]*)</span>', body
            )
        }

        assert marked.get("hard 14 / 12 over") is True, f"the hard cell is not marked over: {marked}"
        assert marked.get("easy 0 / 10") is False, f"an under-plan cell was marked over: {marked}"
        assert "hard 14 / 12 over" in summary_of(body, "tabSummary"), (
            "the marker must be readable, not colour alone"
        )


class TestBookSelect_BookSummarySumsAllTabs:
    """AC-214: 12 easy on <=15 plus 30 on 16-20 reads easy 42 / 60 for the book."""

    def test_the_whole_book_summary_sums_every_tab(self, panel):
        book_id = panel.book()
        panel.books.save_plan(book_id, plan_of(((20, 7, 0), (30, 27, 6), (10, 20, 12), (0, 6, 12))))

        panel.books.add_puzzles_to_book(
            book_id,
            [panel.puzzle(14, 15, "easy") for _ in range(12)]
            + [panel.puzzle(16, 18, "easy") for _ in range(30)],
        )

        summary = summary_of(panel.tab(book_id, FROM_26_TO_30), "bookSummary")

        assert "easy 42 / 60" in summary, summary
        assert "total 42 / 150" in summary, summary

    def test_the_whole_book_summary_is_the_same_on_every_tab(self, panel):
        book_id = panel.book()
        panel.books.save_plan(book_id, plan_of(((20, 7, 0), (30, 27, 6), (10, 20, 12), (0, 6, 12))))
        panel.books.add_puzzles_to_book(book_id, [panel.puzzle(12, 12, "easy")])

        summaries = {summary_of(panel.tab(book_id, bucket), "bookSummary") for bucket in BUCKETS}

        assert len(summaries) == 1, f"the whole-book summary changed between tabs: {summaries}"

    def test_a_tile_ticked_but_not_yet_committed_counts_towards_the_summary(self, panel):
        """The figures answer "how am I doing", so they include the pending tick."""
        book_id = panel.book()
        panel.books.save_plan(book_id, plan_of(((20, 7, 0), (30, 27, 6), (10, 20, 12), (0, 6, 12))))
        ticked = panel.puzzle(12, 12, "easy")

        moved = panel.client.post(f"/book/{book_id}/select-puzzles", data={
            "bucket": UP_TO_15.label,
            "shown_ids": [ticked],
            "puzzle_ids": [ticked],
            "go_bucket": UP_TO_15.label,
        })
        body = panel.client.get(moved.headers["Location"]).get_data(as_text=True)

        assert "easy 1 / 60" in summary_of(body, "bookSummary")
        assert panel.books.get_book(book_id).puzzle_ids == [], (
            "a tab switch committed the selection to the book"
        )


# --------------------------------------------------------------------------
# AC-215 — order inside a tab
# --------------------------------------------------------------------------


class TestBookSelect_TabSortsByTierThenShorterSide:
    """AC-215: tier first, then the shorter side ascending (BK-UI-6)."""

    def test_the_tab_lists_easy_before_medium_before_hard_by_shorter_side(self, panel):
        hard_25x21 = panel.puzzle(25, 21, "hard")
        easy_25x18 = panel.puzzle(25, 18, "easy")
        easy_22x16 = panel.puzzle(22, 16, "easy")
        medium_25x25 = panel.puzzle(25, 25, "medium")
        book_id = panel.book()

        assert panel.offered(panel.tab(book_id, FROM_21_TO_25)) == [
            easy_22x16, easy_25x18, medium_25x25, hard_25x21
        ]


# --------------------------------------------------------------------------
# AC-216 / AC-217 — the filter bar
# --------------------------------------------------------------------------


class TestBookSelect_SizeRangeFilterReplacedByTab:
    """AC-216: no size_from / size_to anywhere on the step."""

    def test_the_page_carries_no_size_range_field(self, panel):
        book_id = panel.book()
        panel.puzzle(12, 12)

        for bucket in BUCKETS:
            body = panel.tab(book_id, bucket)
            for field in ("size_from", "size_to"):
                assert field not in body, f"{field} is still on the {bucket.label} tab"

    def test_every_tab_is_a_keyboard_reachable_control_and_the_current_one_is_announced(self, panel):
        """The a11y minimum: real buttons, and aria-selected on the one in force."""
        book_id = panel.book()
        body = panel.tab(book_id, FROM_21_TO_25)

        tabs = [
            (html_module.unescape(label), attrs)
            for label, attrs in re.findall(
                r'(?s)<button type="submit" name="go_bucket" value="([^"]+)"(.*?)>', body
            )
        ]

        assert [label for label, _ in tabs] == [bucket.label for bucket in BUCKETS]
        announced = [label for label, attrs in tabs if 'aria-selected="true"' in attrs]
        assert announced == [FROM_21_TO_25.label], announced


class TestBookSelect_ExistingFiltersApplyInsideTab:
    """AC-217: difficulty (and its fellows) still narrow the tab's own list."""

    def test_the_difficulty_filter_narrows_the_tab_to_its_hard_puzzles(self, panel):
        hard = [panel.puzzle(21, 21 + n, "hard") for n in range(4)]
        [panel.puzzle(22, 22 + n, "easy") for n in range(3)]
        [panel.puzzle(23, 23 + n, "medium") for n in range(2)]
        # Same tier, another tab: the filter must not reach across the tabs.
        panel.puzzle(12, 12, "hard")
        book_id = panel.book()

        offered = panel.offered(panel.tab(book_id, FROM_21_TO_25, difficulty="hard"))

        assert sorted(offered) == sorted(hard)

    @pytest.mark.parametrize("field,value,matching", [
        ("theme", "halloween", 1),
        ("quality_min", "80", 1),
        ("puzzle_name", "lantern", 1),
    ])
    def test_the_other_filters_still_apply_inside_the_tab(self, panel, field, value, matching):
        wanted = panel.puzzle(22, 22, theme="halloween", quality=90, name="lantern.png")
        panel.puzzle(23, 23, theme="generic", quality=10, name="plain.png")
        book_id = panel.book()

        offered = panel.offered(panel.tab(book_id, FROM_21_TO_25, **{field: value}))

        assert offered == [wanted]
        assert len(offered) == matching


# --------------------------------------------------------------------------
# EC-024 — the route-level half of the partition property
# --------------------------------------------------------------------------


#: Every supported extent — 21 x 21 of them, the corpus of the property below.
EXTENTS = [(w, h) for w in range(MIN_SIZE, MAX_SIZE + 1) for h in range(MIN_SIZE, MAX_SIZE + 1)]

#: The store pages at most 100 rows at a time (``PuzzleFilter.limit``).
PAGE = 100


def _every_offered_id(panel, book_id, bucket):
    """One tab's whole list, walked page by page."""
    seen = []
    for offset in range(0, len(EXTENTS) + PAGE, PAGE):
        seen += panel.offered(panel.tab(book_id, bucket, limit=PAGE, offset=offset))
    return seen


def test_PropertyTest_LongestSideBuckets_PartitionEveryExtent(panel):
    """EC-024, at the route — the case this card adds to CARD-119's property.

    The pure half (``bucket_of`` partitions 10..30 x 10..30 with no gap and no
    overlap) is ``tests/property/test_longest_side_buckets.py``. This is the
    half the tabs own: what the four rendered tabs between them offer is every
    available puzzle, each on exactly one tab, and on the tab ``bucket_of``
    names for its extent.

    The corpus is every supported extent rather than a seeded sample, so the
    boundaries (15/16, 20/21, 25/26) cannot be missed; the tier each puzzle
    carries is drawn from a seeded ``random.Random`` so the tabs are exercised
    with a mixed population, and the case count is asserted below.
    """
    rng = random.Random(122)
    tiers = [tier.value for tier in TIERS]
    expected = {}
    for width, height in EXTENTS:
        expected[panel.puzzle(width, height, rng.choice(tiers))] = bucket_of(width, height)
    book_id = panel.book()

    assert len(expected) >= 441, f"the corpus shrank to {len(expected)} extents"

    offered = {}
    for bucket in BUCKETS:
        for puzzle_id in _every_offered_id(panel, book_id, bucket):
            offered.setdefault(puzzle_id, []).append(bucket)

    twice = {pid: [b.label for b in on] for pid, on in offered.items() if len(on) > 1}
    assert twice == {}, f"puzzles offered on more than one tab: {twice}"

    missing = sorted(set(expected) - set(offered))
    assert missing == [], f"{len(missing)} puzzles were offered on no tab at all"

    wrong = {
        pid: (offered[pid][0].label, expected[pid].label)
        for pid in expected
        if offered[pid][0] is not expected[pid]
    }
    assert wrong == {}, f"tabs disagreeing with bucket_of: {wrong}"
