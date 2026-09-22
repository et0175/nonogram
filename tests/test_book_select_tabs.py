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

Review cycle 1 added four more, each driving the URL the screen itself emits:

    F-001   a tab offers its own members at the paging a browser actually uses
    F-002   "(N available)" is the tab's total, never the surviving page slice
    F-004   a whole book's worth of pending ticks never enters the cookie
    F-005   the over-plan tab is marked by a word, not by a colour alone

Review cycle 2 found the same defect class one step along — the *sort* applied
after the store's slice instead of the filter — and added:

    F-001   AC-215's order is the tab's, held across every page of it
    F-002   applying a filter folds this page's ticks instead of losing them
    F-003   "Clear this page" and "Clear all selected" are two acts
    F-004   the tab strip implements the tabs pattern its roles declare

The evidence class is the Flask test client: these are user-facing criteria on
a server-rendered screen and this project has no browser harness, so each one
GETs or POSTs the real route and reads the real HTML it rendered.
"""

from __future__ import annotations

import html as html_module
import random
import re
import uuid

import pytest

import nonogram.admin.book_manager as book_manager_module
import nonogram.admin.image_manager as image_manager_module
from nonogram.admin.book_manager import BookManager
from nonogram.admin.book_plan import (
    BUCKETS,
    DEFAULT_PLAN,
    TIERS,
    DistributionPlan,
    LongestSideBucket,
    Split,
    bucket_of,
)
from nonogram.admin.puzzle_review import BOOK_TAB_SORT, PuzzleFilter
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
        """The rendered HTML of one tab.

        With no ``query`` this is the URL the product itself emits for a tab:
        the ``?bucket=`` redirect a tab button lands on, with no ``limit`` and
        no ``offset`` — which is the only URL a browser ever asks for unless
        it presses a control the page rendered.
        """
        args = "&".join(f"{k}={v}" for k, v in {"bucket": bucket.label, **query}.items())
        response = self.client.get(f"/book/{book_id}/select-puzzles?{args}")
        assert response.status_code == 200
        return response.get_data(as_text=True)

    def next_page_offset(self, body):
        """The offset the rendered "Next page" control moves to, or ``None``.

        ``None`` means the page rendered no reachable next page — either the
        tab fits on one page, or there is no pagination control at all.
        """
        match = re.search(r'name="go_offset" value="(\d+)" aria-label="Next page"', body)
        return None if match is None else match.group(1)

    def pages_of(self, book_id, bucket):
        """Every page of one tab, reached only through what the page renders.

        The first is the default URL; each further one is the "Next page"
        button pressed inside the step's own form, which is how a browser
        moves and how the ticks come along (they are re-submitted, as the
        browser re-submits a checked box).
        """
        url = f"/book/{book_id}/select-puzzles"
        body = self.tab(book_id, bucket)
        for _ in range(200):  # a guard: a next-page control must terminate
            yield body
            offset = self.next_page_offset(body)
            if offset is None:
                return
            moved = self.client.post(url, data={
                "bucket": bucket.label,
                "shown_ids": self.offered(body),
                "puzzle_ids": sorted(self.ticked(body)),
                "go_offset": offset,
            })
            assert moved.status_code == 302, "the next-page control did not move"
            body = self.client.get(moved.headers["Location"]).get_data(as_text=True)
        raise AssertionError("the next-page control never ran out of pages")

    def offered_across_pages(self, book_id, bucket):
        """Every id one tab offers, walked the way a browser walks it."""
        return [pid for body in self.pages_of(book_id, bucket) for pid in self.offered(body)]

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


#: One tab's declared order, derived from what the test itself built rather
#: than from anything the route or the store computes: the tier's position in
#: ``book_plan.TIERS``, then the shorter side, then the longer side, then the
#: id. An independent second implementation of AC-215, which is the only kind
#: of expectation worth comparing a rendered order against.
def _card_order(built):
    ranks = {tier.value: rank for rank, tier in enumerate(TIERS)}
    return [
        puzzle_id
        for _key, puzzle_id in sorted(
            (
                (ranks[tier], min(width, height), max(width, height), str(puzzle_id)),
                puzzle_id,
            )
            for puzzle_id, (width, height, tier) in built.items()
        )
    ]


class TestBookSelect_TabOrderHoldsAcrossTheTabsPages:
    """F-001 (cycle 2): AC-215's order is the *tab's*, not each page's.

    A tab that outgrows one page is the finding's own scenario: the store
    slices with LIMIT/OFFSET, so an order applied afterwards to the rows the
    route was handed re-sorts one page in isolation and the tier sequence
    restarts at easy on the next one. The walk below is the rendered one —
    the default URL, then the "Next page" control the page itself emits.
    """

    @staticmethod
    def _a_multi_page_tab(panel):
        """21-25 members with every tier at every shorter side, > one page.

        Tiers are round-robined across the shorter sides so that *no* page
        boundary can fall on a tier boundary by luck: page 2 restarting at
        easy is then the defect's signature rather than a coincidence.
        """
        spellings = [tier.value for tier in TIERS]
        built = {}
        for n in range(MORE_THAN_A_PAGE):
            longer, shorter = 21 + (n % 5), 10 + (n % 11)
            spelling = spellings[n % len(spellings)]
            built[panel.puzzle(longer, shorter, spelling)] = (longer, shorter, spelling)
        return built

    def test_the_concatenated_pages_are_in_the_cards_order(self, panel):
        built = self._a_multi_page_tab(panel)
        book_id = panel.book()

        first_page = panel.offered(panel.tab(book_id, FROM_21_TO_25))
        walked = panel.offered_across_pages(book_id, FROM_21_TO_25)

        assert len(first_page) < len(built), (
            "the tab must outgrow one page or this proves nothing about paging"
        )
        assert sorted(walked) == sorted(built), "the walk did not reach every member"
        assert walked == _card_order(built), (
            "the tab's pages, read end to end, are not in tier-then-shorter-side order"
        )

    def test_the_tier_sequence_never_restarts_on_a_later_page(self, panel):
        """The finding's own symptom, named: easy · medium · hard, once."""
        built = self._a_multi_page_tab(panel)
        book_id = panel.book()
        ranks = {tier.value: rank for rank, tier in enumerate(TIERS)}

        pages = [panel.offered(body) for body in panel.pages_of(book_id, FROM_21_TO_25)]
        walked = [pid for page in pages for pid in page]
        sequence = [ranks[built[pid][2]] for pid in walked]

        assert len(pages) > 1, f"the corpus fitted on {len(pages)} page"
        assert sequence == sorted(sequence), (
            "the tier sequence restarts: "
            f"page sizes {[len(p) for p in pages]}, tiers {sequence}"
        )

    def test_the_route_changes_nothing_about_the_page_the_store_returned(self, panel):
        """The post-slice sweep, pinned: what the route does to
        ``result.puzzles`` is three cross-checks, and a cross-check that
        changes what the owner sees is not one. The store's page and the
        rendered page must be the same ids in the same order — on page 2 as
        much as on page 1, which is where a re-sort would show.
        """
        built = self._a_multi_page_tab(panel)
        book_id = panel.book()
        page_size = int(panel.next_page_offset(panel.tab(book_id, FROM_21_TO_25)))

        for start in (0, page_size):
            from_store = panel.store.filter_puzzles(PuzzleFilter(
                longest_side_range=(FROM_21_TO_25.low, FROM_21_TO_25.high),
                sort_by=BOOK_TAB_SORT,
                status="approved",
                book_id="unassigned",
                limit=page_size,
                offset=start,
            ))
            rendered = panel.offered(panel.tab(book_id, FROM_21_TO_25, offset=start))

            assert rendered, f"page at offset {start} rendered nothing"
            assert [p["id"] for p in from_store.puzzles] == rendered, start
        assert len(built) > page_size

    def test_the_shorter_side_climbs_inside_each_tier_across_pages(self, panel):
        """...and the second key too: `-size` is not "shorter side ascending"."""
        built = self._a_multi_page_tab(panel)
        book_id = panel.book()

        walked = panel.offered_across_pages(book_id, FROM_21_TO_25)
        by_tier = {}
        for puzzle_id in walked:
            longer, shorter, tier = built[puzzle_id]
            by_tier.setdefault(tier, []).append(min(longer, shorter))

        assert set(by_tier) == {tier.value for tier in TIERS}
        for tier, shorter_sides in by_tier.items():
            assert shorter_sides == sorted(shorter_sides), (
                f"the {tier} run of the tab is not by shorter side: {shorter_sides}"
            )


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

        # F-010: the tablist/tabpanel pair is wired, and nothing claims page
        # navigation for a control that submits a form.
        panel_id = re.search(r'role="tabpanel"[^>]*', body).group(0)
        assert 'id="tabpanel_current"' in panel_id or re.search(
            r'id="([^"]+)"[^>]*role="tabpanel"', body
        ), "the panel the tabs point at has no id"
        assert all('aria-controls="tabpanel_current"' in attrs for _, attrs in tabs)
        assert all("aria-current" not in attrs for _, attrs in tabs), (
            "aria-current claims page-navigation semantics for a submit button"
        )

    def test_a_bookmarked_size_parameter_is_answered_rather_than_ignored(self, panel):
        """F-009: the filter this card deleted does not vanish in silence."""
        book_id = panel.book()
        body = panel.client.get(
            f"/book/{book_id}/select-puzzles?size=20"
        ).get_data(as_text=True)

        assert "size filter is gone from this step" in text_of(body)
        assert "size was ignored" in text_of(body)


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
# F-001 / F-002 — a tab is a query, so its page is a page of the tab
# --------------------------------------------------------------------------


#: Wider than a page of the tab, so paging is the thing under test rather than
#: an implementation detail nobody reaches.
MORE_THAN_A_PAGE = 70


def _a_superset_of_the_first_tab(panel, how_many=60):
    """Rows the *old* store narrowing would have put on the ``<=15`` tab.

    Each is 26..30 by 12: its longest side is 26-30, so it belongs to the last
    tab — but its shorter side is inside 10-15, which is what "either side in
    range" matched. They are also the widest rows, so the default sort
    (``-size``) puts every one of them ahead of the tab's real members.
    """
    return [panel.puzzle(26 + (n % 5), 12, "hard") for n in range(how_many)]


class TestBookSelect_TabOffersItsOwnMembersAtDefaultPaging:
    """F-001: LIMIT must bite on the tab's members, not on a wider superset.

    The finding's own scenario: the page renders no URL carrying ``limit`` or
    ``offset``, so a browser asks for the tab and nothing else. What comes
    back must be the tab.
    """

    def test_the_first_tab_offers_its_own_puzzles_although_wider_rows_outnumber_them(self, panel):
        members = [panel.puzzle(12, 12 + (n % 4), "easy") for n in range(12)]
        _a_superset_of_the_first_tab(panel)
        book_id = panel.book()

        offered = panel.offered(panel.tab(book_id, UP_TO_15))

        assert sorted(offered) == sorted(members), (
            "the <=15 tab rendered "
            f"{len(offered)} of its {len(members)} puzzles at the paging a browser uses"
        )

    def test_a_tab_bigger_than_one_page_reaches_every_member_through_its_pages(self, panel):
        members = [panel.puzzle(21, 21 + (n % 5), "easy") for n in range(MORE_THAN_A_PAGE)]
        book_id = panel.book()

        first_page = panel.offered(panel.tab(book_id, FROM_21_TO_25))
        walked = panel.offered_across_pages(book_id, FROM_21_TO_25)

        assert len(first_page) < len(members), (
            "the corpus must outgrow one page or this proves nothing"
        )
        assert sorted(walked) == sorted(members), (
            f"{len(members) - len(set(walked))} puzzles were unreachable from the rendered page"
        )
        assert len(walked) == len(set(walked)), "a puzzle was offered on two pages of one tab"

    def test_ticks_made_on_one_page_survive_the_move_to_the_next(self, panel):
        """A page move is the tab switch's twin: it keeps, it never commits."""
        members = [panel.puzzle(21, 21 + (n % 5), "easy") for n in range(MORE_THAN_A_PAGE)]
        book_id = panel.book()
        url = f"/book/{book_id}/select-puzzles"

        first = panel.tab(book_id, FROM_21_TO_25)
        shown = panel.offered(first)
        picked = shown[:3]
        moved = panel.client.post(url, data={
            "bucket": FROM_21_TO_25.label,
            "shown_ids": shown,
            "puzzle_ids": picked,
            "go_offset": panel.next_page_offset(first),
        })
        second = panel.client.get(moved.headers["Location"]).get_data(as_text=True)

        assert f"{len(picked)} puzzles selected" in text_of(second)
        assert panel.books.get_book(book_id).puzzle_ids == [], "a page move committed"
        assert set(members) >= set(shown)


class TestBookSelect_AvailableCountIsTheTabsOwnTotal:
    """F-002: "(N available)" is the tab's total, not the page's survivors."""

    def test_the_header_counts_the_tabs_members_rather_than_the_surviving_slice(self, panel):
        members = [panel.puzzle(12, 12 + (n % 4), "easy") for n in range(12)]
        _a_superset_of_the_first_tab(panel)
        book_id = panel.book()

        body = panel.tab(book_id, UP_TO_15)

        assert f"({len(members)} available)" in text_of(body)
        assert "No approved puzzles with a longest side" not in text_of(body), (
            "a tab with members told the owner it has none"
        )

    def test_a_genuinely_empty_tab_still_says_zero_and_offers_the_empty_state(self, panel):
        _a_superset_of_the_first_tab(panel, how_many=3)
        book_id = panel.book()

        body = text_of(panel.tab(book_id, UP_TO_15))

        assert "(0 available)" in body
        assert "No approved puzzles with a longest side" in body


# --------------------------------------------------------------------------
# F-004 — where a pending selection lives
# --------------------------------------------------------------------------


def _with_database_shaped_ids(panel, puzzle_ids):
    """Re-key those rows to the 36-character UUIDs the database stores.

    The panel's in-memory store numbers its rows 1, 2, 3..., which is not the
    size of an id the deployed panel keeps (``db/models.py``: a UUID primary
    key). F-004 is a measurement in bytes, so it has to be made on ids of the
    real shape or it measures nothing.
    """
    renamed = []
    for puzzle_id in puzzle_ids:
        record = panel.store.puzzles.pop(puzzle_id)
        record["id"] = str(uuid.uuid4())
        panel.store.puzzles[record["id"]] = record
        renamed.append(record["id"])
    return renamed


class TestBookSelect_PendingSelectionDoesNotRideInTheCookie:
    """F-004: a book's worth of ticks must not overflow the session cookie.

    A cookie over the browser's limit is discarded whole and in silence,
    taking every other session key with it — so AC-211 would fail with
    nothing the owner could see. The ids belong server-side.
    """

    #: Werkzeug's own ceiling for a ``Set-Cookie`` header; a browser's is the
    #: same 4 KB, and the rest of the session shares it.
    BROWSER_COOKIE_LIMIT = 4093

    def test_a_whole_books_worth_of_ticks_stays_out_of_the_cookie_and_survives(self, panel):
        picked = _with_database_shaped_ids(
            panel,
            [panel.puzzle(12, 12 + (n % 4), "easy") for n in range(DEFAULT_PLAN.count)],
        )
        book_id = panel.book()
        url = f"/book/{book_id}/select-puzzles"

        away = panel.client.post(url, data={
            "bucket": UP_TO_15.label,
            "shown_ids": picked,
            "puzzle_ids": picked,
            "go_bucket": FROM_21_TO_25.label,
        })

        cookies = away.headers.getlist("Set-Cookie")
        assert cookies, "the step set no cookie at all"
        biggest = max(len(cookie) for cookie in cookies)
        assert biggest < self.BROWSER_COOKIE_LIMIT, (
            f"{len(picked)} ticks made a {biggest}-byte cookie; a browser drops it whole"
        )
        assert not any(pid in cookie for pid in picked for cookie in cookies), (
            "a puzzle id rode in the cookie"
        )

        # ... and the selection is still all there (AC-211 at book scale).
        back = panel.tab(book_id, UP_TO_15)
        assert f"{len(picked)} puzzles selected" in text_of(back)

    def test_the_kept_selection_still_commits_once_through_the_book_manager(self, panel):
        """The one commit point is unchanged by where the pending ticks live."""
        picked = [panel.puzzle(12, 12, "easy"), panel.puzzle(22, 22, "medium")]
        book_id = panel.book()
        url = f"/book/{book_id}/select-puzzles"

        panel.client.post(url, data={
            "bucket": UP_TO_15.label,
            "shown_ids": [picked[0]],
            "puzzle_ids": [picked[0]],
            "go_bucket": FROM_21_TO_25.label,
        })
        done = panel.client.post(url, data={
            "bucket": FROM_21_TO_25.label,
            "shown_ids": [picked[1]],
            "puzzle_ids": [picked[1]],
        })

        assert "arrange-puzzles" in done.headers["Location"]
        assert set(panel.books.get_book(book_id).puzzle_ids) == set(picked)
        # Committed once and cleared: the next render starts from nothing.
        assert "0 puzzles selected" in text_of(panel.tab(book_id, UP_TO_15))


# --------------------------------------------------------------------------
# F-005 — the tab strip's over-plan marker
# --------------------------------------------------------------------------


class TestBookSelect_OverPlanTabMarkedBeyondColour:
    """F-005: the tab strip is the only signal an *other* tab is over plan."""

    def test_the_over_plan_tab_says_so_in_words_not_in_colour_alone(self, panel):
        book_id = panel.book()
        panel.books.save_plan(book_id, plan_of(((0, 0, 0), (0, 0, 0), (10, 20, 12), (0, 0, 0))))
        panel.books.add_puzzles_to_book(
            book_id, [panel.puzzle(21, 25, "hard") for _ in range(14)]
        )

        # A different tab is in force: the strip is all the owner can see.
        body = panel.tab(book_id, UP_TO_15)
        strip = {
            html_module.unescape(label): (attributes, text_of(inner))
            for label, attributes, inner in re.findall(
                r'(?s)<button type="submit" name="go_bucket" value="([^"]+)"(.*?)>(.*?)</button>',
                body,
            )
        }

        attributes, reading = strip[FROM_21_TO_25.label]
        assert 'data-over="true"' in attributes
        assert "over" in reading.split(), (
            f"the over-plan tab reads {reading!r} — nothing but the colour says so"
        )
        assert "over" not in strip[UP_TO_15.label][1].split(), (
            "an under-plan tab was marked over"
        )


# --------------------------------------------------------------------------
# F-002 / F-003 / F-004 (cycle 2) — the controls around the list
# --------------------------------------------------------------------------


class TestBookSelect_ApplyingAFilterKeepsThisPagesTicks:
    """F-002: Apply submits the step, so the ticks are folded, not dropped."""

    def test_the_filter_controls_submit_the_steps_own_form(self, panel):
        book_id = panel.book()
        body = panel.tab(book_id, FROM_21_TO_25)

        assert 'method="GET"' not in body, "the filter card still navigates away"
        for field in ("difficulty", "quality_min", "theme", "puzzle_name"):
            control = re.search(rf'<(?:input|select)[^>]*\bname="{field}"[^>]*>', body)
            assert control, f"no {field} control on the page"
            assert 'form="puzzleForm"' in control.group(0), field
            assert body.count(f'name="{field}"') == 1, (
                f"{field} is submitted twice — a hidden twin is still in the form"
            )

    def test_applying_a_filter_folds_the_ticks_instead_of_losing_them(self, panel):
        wanted = panel.puzzle(22, 22, "easy", theme="halloween")
        other = panel.puzzle(23, 23, "easy", theme="generic")
        book_id = panel.book()
        url = f"/book/{book_id}/select-puzzles"

        applied = panel.client.post(url, data={
            "bucket": FROM_21_TO_25.label,
            "shown_ids": [wanted, other],
            "puzzle_ids": [wanted, other],
            "theme": "halloween",
            "go_filter": "1",
        })

        assert applied.status_code == 302
        assert "theme=halloween" in applied.headers["Location"]
        filtered = panel.client.get(applied.headers["Location"]).get_data(as_text=True)
        assert "2 puzzles selected" in text_of(filtered), (
            "applying a filter dropped the ticks made on the page"
        )
        assert panel.offered(filtered) == [wanted]
        assert panel.books.get_book(book_id).puzzle_ids == [], "applying a filter committed"

    def test_applying_a_filter_goes_back_to_the_first_page(self, panel):
        """The page numbers the owner left belong to the old result set."""
        [panel.puzzle(21, 21 + (n % 5), "easy") for n in range(MORE_THAN_A_PAGE)]
        book_id = panel.book()

        applied = panel.client.post(f"/book/{book_id}/select-puzzles", data={
            "bucket": FROM_21_TO_25.label,
            "offset": "50",
            "difficulty": "easy",
            "go_filter": "1",
        })

        assert "offset=" not in applied.headers["Location"], applied.headers["Location"]


class TestBookSelect_ClearingThisPageAndClearingEverything:
    """F-003: two different acts, two controls, each saying which it is."""

    def test_the_page_control_says_it_clears_this_page(self, panel):
        panel.puzzle(22, 22)
        book_id = panel.book()

        reading = text_of(panel.tab(book_id, FROM_21_TO_25))

        assert "Clear this page" in reading
        assert "Clear all selected" in reading

    def test_clear_all_selected_drops_the_whole_kept_set(self, panel):
        here = panel.puzzle(22, 22, "easy")
        elsewhere = panel.puzzle(12, 12, "easy")
        book_id = panel.book()
        url = f"/book/{book_id}/select-puzzles"

        panel.client.post(url, data={
            "bucket": UP_TO_15.label,
            "shown_ids": [elsewhere],
            "puzzle_ids": [elsewhere],
            "go_bucket": FROM_21_TO_25.label,
        })
        assert "1 puzzle selected" in text_of(panel.tab(book_id, FROM_21_TO_25))

        cleared = panel.client.post(url, data={
            "bucket": FROM_21_TO_25.label,
            "shown_ids": [here],
            "puzzle_ids": [here],
            "go_clear": "1",
        })

        assert cleared.status_code == 302
        after = panel.client.get(cleared.headers["Location"]).get_data(as_text=True)
        assert "0 puzzles selected" in text_of(after), (
            "the kept selection survived Clear all selected"
        )
        assert panel.ticked(after) == set()
        assert panel.books.get_book(book_id).puzzle_ids == [], "clearing committed something"


class TestBookSelect_TabStripImplementsTheTabsPatternItDeclares:
    """F-004: role="tablist" promises roving tabindex and arrow keys."""

    def test_only_the_current_tab_is_in_the_page_tab_order(self, panel):
        book_id = panel.book()
        body = panel.tab(book_id, FROM_21_TO_25)

        tabs = re.findall(
            r'(?s)<button type="submit" name="go_bucket" value="([^"]+)"(.*?)>', body
        )
        tabbable = [
            html_module.unescape(label)
            for label, attrs in tabs
            if 'tabindex="0"' in attrs
        ]

        assert tabbable == [FROM_21_TO_25.label], tabbable
        assert all(
            'tabindex="-1"' in attrs
            for label, attrs in tabs
            if html_module.unescape(label) != FROM_21_TO_25.label
        )

    def test_arrow_keys_move_focus_along_the_strip(self, panel):
        """The script the pattern needs is on the page and binds the four keys."""
        book_id = panel.book()
        body = panel.tab(book_id, FROM_21_TO_25)
        script = re.search(r"(?s)<script>(.*?)</script>", body).group(1)

        assert 'keydown' in script
        for key in ("ArrowRight", "ArrowLeft", "Home", "End"):
            assert key in script, key
        assert "tabIndex" in script, "focus moves but the roving tabindex does not"

    def test_the_panel_is_named_by_the_tab_in_force(self, panel):
        book_id = panel.book()

        for index, bucket in enumerate(BUCKETS, start=1):
            body = panel.tab(book_id, bucket)
            panel_tag = re.search(r'<div[^>]*role="tabpanel"[^>]*>', body).group(0)
            assert f'aria-labelledby="tab_{index}"' in panel_tag, bucket.label
            assert f'id="tab_{index}"' in body


# --------------------------------------------------------------------------
# EC-024 — the route-level half of the partition property
# --------------------------------------------------------------------------


#: Every supported extent — 21 x 21 of them, the corpus of the property below.
EXTENTS = [(w, h) for w in range(MIN_SIZE, MAX_SIZE + 1) for h in range(MIN_SIZE, MAX_SIZE + 1)]

#: The store pages at most 100 rows at a time (``PuzzleFilter.limit``).
PAGE = 100


def _walked_by_the_rendered_page(panel, book_id, bucket):
    """One tab's whole list, reached the way the screen offers it.

    The default URL, then the "Next page" control the page renders — no
    ``limit`` and no ``offset`` typed by the test, because the product emits
    neither (review cycle 1, F-003: the test's *given* must be the screen's).
    """
    return panel.offered_across_pages(book_id, bucket)


def _walked_at_the_stores_cap(panel, book_id, bucket):
    """One tab's whole list, paged by hand at the store's maximum page.

    Kept as the second case: it exercises a page size the page itself never
    asks for, which is worth covering and is not evidence about the screen.
    """
    seen = []
    for offset in range(0, len(EXTENTS) + PAGE, PAGE):
        seen += panel.offered(panel.tab(book_id, bucket, limit=PAGE, offset=offset))
    return seen


@pytest.mark.parametrize(
    "walk",
    [_walked_by_the_rendered_page, _walked_at_the_stores_cap],
    ids=["as the page renders it", "paged by hand at the store's cap"],
)
def test_PropertyTest_LongestSideBuckets_PartitionEveryExtent(panel, walk):
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

    Both walks must hold. The first is the one that speaks for the product:
    441 puzzles, four tabs, and nothing but the URLs and controls the rendered
    page itself emits.
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
        for puzzle_id in walk(panel, book_id, bucket):
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
