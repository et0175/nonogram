"""CARD-192 — the Arrangement page can show one plan band, with left/over against the plan.

    AC-1  ?bucket=16-20 lists only the 18x16 row; with no bucket all three are listed
          (TestArrangeSizeFilter_ShowsOnlyTheChosenBucket)
    AC-2  the plan line reads Easy 18 / 20 (2 left), Medium 22 / 20 (2 over) with
          the medium figure data-over="true", and Hard 10 / 10 (on plan)
          (TestArrangeSizeFilter_PlanLineShowsLeftAndOver)
    AC-3  the arrange page's plan line and the selection step's 16-20 tab carry the
          same planned and selected numbers, tier by tier
          (TestArrangeSizeFilter_SameNumbersAsSelectionTab)
    AC-4  a book with no stored plan shows member counts with no planned figure,
          and names Print setup (TestArrangeSizeFilter_PlanLessBookShowsCountsOnly)
    AC-5  a filtered page has no move, position or sort control and says reordering
          is off; the unfiltered page has them as before
          (TestArrangeSizeFilter_MovesOffWhileFiltered)
    AC-6  saving a title and confirming a Remove both come back still filtered; the
          confirm form's action carries the band
          (TestArrangeSizeFilter_FilterSurvivesTitleAndRemove)
    AC-7  an unknown bucket lists every member and shows no plan line
          (TestArrangeSizeFilter_UnknownBucketMeansAllSizes)

plus the bucket filter's invariant, as a property over a seeded corpus:
every shown row is in the band and every in-band member is shown
(TestArrangeSizeFilter_PropertyBandIsExactlyItsMembers).

The evidence class is the Flask test client: these are user-facing criteria on a
server-rendered screen, so each test GETs or POSTs the real route and reads the
HTML that came back. Both storage modes run through the same route: memory, and
a SQLite file reached through DATABASE_URL and the database session scope, the way
tests/test_admin_filter_side_range_and_name.py builds its DB-mode panel.

The expected numbers are written out here by hand, never taken from the function
under test: the band ranges below are the longest-side bounds of the four plan
bands, and the plan figures are the ones the test put in the plan.
"""

from __future__ import annotations

import random
import re
import uuid

import pytest

import nonogram.admin.book_manager as book_manager_module
import nonogram.admin.image_manager as image_manager_module
from nonogram.admin.book_manager import BookManager
from nonogram.admin.book_plan import BUCKETS, DistributionPlan, Split
from nonogram.db.models import Book as DBBook
from nonogram.limits import MAX_SIZE, MIN_SIZE
from tests.helpers.db import sqlite_session_scope
from tests.test_book_level_order import MODES, text_of

#: The four plan bands by label, each with its inclusive longest-side range.
#: Written here by hand so the property grades the filter with numbers that are
#: not the code's own.
BAND_RANGES = {
    "<=15": (10, 15),
    "16-20": (16, 20),
    "21-25": (21, 25),
    "26-30": (26, 30),
}

#: The one plan the page-level tests use: 16-20 wants 20 easy, 20 medium, 10 hard.
PLAN_16_20 = {"16-20": (20, 20, 10)}

#: A book that can reach "published": its 16-20 members match its plan cell for
#: cell (2 easy, 1 medium), so the ready gate lets it out (ADR-0035).
PUBLISHABLE_16_20_SIZES = [(16, 16, "easy"), (18, 16, "easy"), (20, 16, "medium")]
PUBLISHABLE_16_20_PLAN = {"16-20": (2, 1, 0)}

#: The four actions the page offers only while every size is shown.
REORDER_ACTIONS = ("move_up", "move_down", "set_position", "sort_by_size")

REORDER_OFF = "Reordering is off while one size is shown. Show all sizes to move puzzles or sort them."


# --------------------------------------------------------------------------
# the panel: the real app, in one storage mode
# --------------------------------------------------------------------------


class Panel:
    """The app, its store and its books, with the one-liners these tests need."""

    def __init__(self, app, scope):
        self.app = app
        self.scope = scope
        self.store = app.puzzle_review_service
        self.books = app.book_manager
        self.client = app.test_client()
        self._made = 0

    def puzzle(self, width, height, tier="easy"):
        """An approved, solid puzzle of that extent (the store's uniqueness proof is trivial)."""
        self._made += 1
        puzzle_id = self.store.add_puzzle(
            grid=[[True] * width for _ in range(height)],
            clues_rows=[[width]] * height,
            clues_cols=[[height]] * width,
            width=width,
            height=height,
            theme="generic",
            difficulty_score=10,
            difficulty_tier=tier,
            quality_score=50,
            recognizability="medium",
            strategies_used=[],
            batch_id=None,
            source_image=f"card192-{self._made}.png",
        )
        self.store.approve_puzzle(puzzle_id)
        return puzzle_id

    def stock(self, sizes, plan=None, status=None):
        """A book holding one puzzle per ``(width, height, tier)`` in ``sizes``.

        ``plan`` is stored when given; ``status`` is walked to through the gate,
        as the product reaches it. Returns ``(book_id, ids)`` in ``sizes`` order.
        """
        book_id = self.books.create_book("Winter", "a book", "christmas", "adults")
        ids = [self.puzzle(w, h, tier) for w, h, tier in sizes]
        if ids:
            self.books.add_puzzles_to_book(book_id, ids)
        if plan is not None:
            self.books.save_plan(book_id, plan)
        for step in _path_to(status):
            assert self.books.set_book_status(book_id, step) is True, step
        return book_id, ids

    def drop_plan(self, book_id):
        """Leave the book with no stored plan, the way a book from before migration 010 has none."""
        if self.scope is None:
            self.books._plans.pop(book_id, None)
        else:
            with self.scope() as db:
                db.query(DBBook).filter(DBBook.id == uuid.UUID(book_id)).first().distribution_plan = None
        assert self.books.get_plan(book_id) is None

    def page(self, book_id, query=""):
        """GET the arrangement screen, with an optional query string."""
        url = f"/book/{book_id}/arrange-puzzles" + (f"?{query}" if query else "")
        response = self.client.get(url)
        assert response.status_code == 200
        return response.get_data(as_text=True)


_STATUS_LADDER = ["ready_for_pdf", "pdf_generated", "ready_for_kdp", "published"]


def _path_to(status):
    """The statuses walked from draft to ``status``, in order."""
    if status is None:
        return []
    return _STATUS_LADDER[: _STATUS_LADDER.index(status) + 1]


@pytest.fixture(params=MODES)
def panel(request, tmp_path, monkeypatch):
    monkeypatch.setenv("TESTING", "true")
    image_manager_module._image_manager = None
    if request.param == "memory":
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setattr(book_manager_module, "_book_manager", BookManager(session_factory=None))
        scope = None
    else:
        import nonogram.db

        scope = sqlite_session_scope(tmp_path, "card-192.db")
        monkeypatch.setenv("DATABASE_URL", "sqlite:///card-192-test-only")
        monkeypatch.setattr(nonogram.db, "session_scope", scope)

    from nonogram.admin.app import create_app

    app = create_app()
    app.config["TESTING"] = True
    # The tests must exercise the store they name, not silently fall back.
    assert (app.puzzle_review_service._session_factory is None) == (scope is None)
    panel = Panel(app, scope)
    yield panel
    image_manager_module._image_manager = None


# --------------------------------------------------------------------------
# reading the rendered page
# --------------------------------------------------------------------------


def shown_ids(markup):
    """The ids of the rows the page lists, in document order (one title box per row)."""
    return re.findall(r'id="title_([^"]+)"', markup)


def plan_line(markup):
    """The #bandPlan line's HTML, or None when the page shows no plan line."""
    found = re.search(r'<p class="stat-line" id="bandPlan"[^>]*>(.*?)</p>', markup, re.S)
    return found.group(1) if found else None


def figures(text):
    """``{tier-or-total: (selected, planned or None)}`` read from one summary line."""
    return {
        key.lower(): (int(selected), int(planned) if planned else None)
        for key, selected, planned in re.findall(
            r"\b(Easy|Medium|Hard|Total|easy|medium|hard|total) (\d+)(?: / (\d+))?", text
        )
    }


def current_band(markup):
    """The label of the band link the page marks as current, or None for "All sizes" (or no link)."""
    found = re.search(r'<a class="tab is-current"[^>]*aria-current="page">([^<]+)</a>', markup)
    return found.group(1) if found else None


def current_links(markup):
    """Every filter link whose class marks it current, by its label (one, in a correct page)."""
    return re.findall(r'<a class="tab[^"]*\bis-current\b[^"]*"[^>]*>([^<]+)</a>', markup)


def in_band(width, height, label):
    """Is this stored size in the band, by the written-out ranges?"""
    if not all(MIN_SIZE <= side <= MAX_SIZE for side in (width, height)):
        return False
    low, high = BAND_RANGES[label]
    return low <= max(width, height) <= high


def plan_of(rows):
    """A DistributionPlan with the given ``{band label: (easy, medium, hard)}`` cells."""
    cells = tuple(tuple(rows.get(band.label, (0, 0, 0))) for band in BUCKETS)
    return DistributionPlan(
        count=max(1, sum(sum(row) for row in cells)), split=Split(40, 40, 20), cells=cells
    )


def sixteen_twenty_book(panel):
    """50 puzzles in 16-20 (18 easy, 22 medium, 10 hard) and 2 hard in 21-25, on PLAN_16_20."""
    sizes = (
        [(16, 16, "easy")] * 18
        + [(16, 16, "medium")] * 22
        + [(16, 16, "hard")] * 10
        + [(25, 21, "hard")] * 2
    )
    return panel.stock(sizes, plan=plan_of(PLAN_16_20))


# --------------------------------------------------------------------------
# AC-1 — the filter lists only the chosen band
# --------------------------------------------------------------------------


class TestArrangeSizeFilter_ShowsOnlyTheChosenBucket:
    def test_the_chosen_band_lists_only_its_rows(self, panel):
        book_id, (small, mid, big) = panel.stock(
            [(15, 15, "easy"), (18, 16, "medium"), (25, 21, "hard")]
        )

        chosen = panel.page(book_id, "bucket=16-20")
        assert shown_ids(chosen) == [mid]
        assert current_links(chosen) == ["16-20"], "only the band in force is marked current"
        assert shown_ids(panel.page(book_id, "bucket=21-25")) == [big]

    def test_with_no_bucket_all_three_are_listed(self, panel):
        book_id, ids = panel.stock(
            [(15, 15, "easy"), (18, 16, "medium"), (25, 21, "hard")]
        )

        assert set(shown_ids(panel.page(book_id))) == set(ids)

    def test_the_up_to_15_band_is_addressed_by_its_own_label(self, panel):
        book_id, (small, mid, big) = panel.stock(
            [(15, 15, "easy"), (18, 16, "medium"), (25, 21, "hard")]
        )

        assert shown_ids(panel.page(book_id, "bucket=%3C%3D15")) == [small]

    def test_each_level_says_how_many_of_it_is_shown(self, panel):
        book_id, _ = panel.stock(
            [(15, 15, "easy"), (18, 16, "medium"), (25, 21, "hard")]
        )

        text = text_of(panel.page(book_id, "bucket=16-20"))

        assert "Easy level (0 shown of 1)" in text, text
        assert "Medium level (1 shown of 1)" in text, text
        assert "Hard level (0 shown of 1)" in text, text
        assert text.count("No puzzles of this size in this level.") == 2, text

    def test_a_size_outside_the_supported_range_is_under_no_band(self, panel):
        book_id, (inside, outside) = panel.stock(
            [(15, 15, "easy"), (MAX_SIZE + 2, 12, "easy")]
        )

        assert shown_ids(panel.page(book_id, "bucket=<=15")) == [inside]
        assert shown_ids(panel.page(book_id, "bucket=26-30")) == []
        assert set(shown_ids(panel.page(book_id))) == {inside, outside}

    def test_an_ungraded_row_in_the_band_is_shown_under_the_ungraded_heading(self, panel):
        book_id, (ungraded,) = panel.stock([(18, 16, None)])

        html = panel.page(book_id, "bucket=16-20")

        assert shown_ids(html) == [ungraded]
        assert 'data-level="ungraded"' in html


# --------------------------------------------------------------------------
# AC-2 — the plan line gives the gap in words
# --------------------------------------------------------------------------


class TestArrangeSizeFilter_PlanLineShowsLeftAndOver:
    def test_the_line_reads_left_over_and_on_plan_per_level(self, panel):
        book_id, _ = sixteen_twenty_book(panel)

        line = plan_line(panel.page(book_id, "bucket=16-20"))

        assert line is not None, "a chosen band shows its plan line"
        assert text_of(line) == (
            "16-20: Easy 18 / 20 (2 left) · Medium 22 / 20 (2 over) · "
            "Hard 10 / 10 (on plan) · Total 50 / 50"
        )

    def test_only_the_over_figure_carries_the_over_marker(self, panel):
        book_id, _ = sixteen_twenty_book(panel)

        cells = re.findall(
            r'<span class="stat-cell"([^>]*)>([^<]*)</span>',
            plan_line(panel.page(book_id, "bucket=16-20")),
        )
        marked = {text_of(content): 'data-over="true"' in attrs for attrs, content in cells}

        assert marked == {
            "Easy 18 / 20 (2 left)": False,
            "Medium 22 / 20 (2 over)": True,
            "Hard 10 / 10 (on plan)": False,
            "Total 50 / 50": False,
        }, marked

    def test_a_tier_over_plan_is_named_over_and_the_total_says_how_far_short(self, panel):
        book_id, _ = panel.stock([(16, 16, "easy")] * 25, plan=plan_of(PLAN_16_20))

        line = text_of(plan_line(panel.page(book_id, "bucket=16-20")))

        assert line == (
            "16-20: Easy 25 / 20 (5 over) · Medium 0 / 20 (20 left) · "
            "Hard 0 / 10 (10 left) · Total 25 / 50 (25 left)"
        ), line


# --------------------------------------------------------------------------
# AC-3 — the same numbers as the selection step's tab
# --------------------------------------------------------------------------


class TestArrangeSizeFilter_SameNumbersAsSelectionTab:
    def test_the_arrange_line_and_the_selection_tab_agree_tier_by_tier(self, panel):
        book_id, _ = sixteen_twenty_book(panel)

        arranged = figures(text_of(plan_line(panel.page(book_id, "bucket=16-20"))))
        selection = panel.client.get(f"/book/{book_id}/select-puzzles?bucket=16-20")
        assert selection.status_code == 200
        summary = re.search(
            r'<p class="stat-line" id="tabSummary"[^>]*>(.*?)</p>',
            selection.get_data(as_text=True),
            re.S,
        )
        assert summary, "the selection step has no 16-20 tab summary"
        ticked = figures(text_of(summary.group(1)))

        expected = {"easy": (18, 20), "medium": (22, 20), "hard": (10, 10), "total": (50, 50)}
        assert ticked == expected, ticked
        assert arranged == expected, arranged


# --------------------------------------------------------------------------
# AC-4 — a book with no plan shows counts only
# --------------------------------------------------------------------------


class TestArrangeSizeFilter_PlanLessBookShowsCountsOnly:
    def test_counts_with_no_planned_figure_and_a_pointer_to_print_setup(self, panel):
        book_id, _ = sixteen_twenty_book(panel)
        panel.drop_plan(book_id)

        html = panel.page(book_id, "bucket=16-20")
        line = plan_line(html)

        assert line is not None
        assert text_of(line) == "16-20: Easy 18 · Medium 22 · Hard 10 · Total 50", text_of(line)
        assert "/" not in text_of(line), "a plan-less book must not invent a planned figure"
        assert "data-over" not in line
        # The stepper also names Print setup and links to it, so the sentence
        # itself is what is asserted, in words.
        assert (
            "This book has no distribution plan yet, so only the member counts are shown. "
            "Set the plan in Print setup"
        ) in text_of(html)


# --------------------------------------------------------------------------
# AC-5 — no moves, position or sort while a band is shown
# --------------------------------------------------------------------------


class TestArrangeSizeFilter_MovesOffWhileFiltered:
    def test_the_filtered_page_has_no_reorder_control_and_says_so(self, panel):
        book_id, ids = panel.stock(
            [(16, 16, "easy"), (16, 16, "easy"), (18, 16, "medium"), (18, 16, "medium")]
        )

        filtered = panel.page(book_id, "bucket=16-20")

        for action in REORDER_ACTIONS:
            assert f'value="{action}"' not in filtered, action
        assert f'id="position_' not in filtered
        assert REORDER_OFF in text_of(filtered)
        assert 'aria-label="Remove from book"' in filtered, "the Remove button stays"
        assert 'name="title"' in filtered, "title editing stays"

    def test_the_unfiltered_page_keeps_every_reorder_control(self, panel):
        book_id, ids = panel.stock(
            [(16, 16, "easy"), (16, 16, "easy"), (18, 16, "medium"), (18, 16, "medium")]
        )

        whole = panel.page(book_id)

        assert 'value="move_up"' in whole and 'value="move_down"' in whole
        assert 'value="set_position"' in whole
        assert 'value="sort_by_size"' in whole
        assert REORDER_OFF not in text_of(whole)


# --------------------------------------------------------------------------
# AC-6 — the band survives a title save and a Remove
# --------------------------------------------------------------------------


class TestArrangeSizeFilter_FilterSurvivesTitleAndRemove:
    def test_saving_a_title_comes_back_still_filtered(self, panel):
        book_id, (small, mid, big) = panel.stock(
            [(15, 15, "easy"), (18, 16, "medium"), (25, 21, "hard")]
        )

        response = panel.client.post(
            f"/book/{book_id}/arrange-puzzles?bucket=16-20",
            data={"action": "set_title", "puzzle_id": mid, "title": "Renamed"},
        )

        html = response.get_data(as_text=True)
        assert response.status_code == 200
        assert current_band(html) == "16-20", html
        assert shown_ids(html) == [mid]
        assert "Renamed" in html

    def test_removing_asks_with_a_confirm_action_that_carries_the_band(self, panel):
        # A published book's membership change is asked first (INV-008).
        book_id, (small, mid, big) = panel.stock(
            PUBLISHABLE_16_20_SIZES, plan=plan_of(PUBLISHABLE_16_20_PLAN), status="published"
        )

        response = panel.client.post(
            f"/book/{book_id}/arrange-puzzles?bucket=16-20",
            data={"action": "delete", "puzzle_id": mid},
        )

        html = response.get_data(as_text=True)
        assert f'action="/book/{book_id}/arrange-puzzles?bucket=16-20"' in html, html
        assert mid in panel.books.get_book(book_id).puzzle_ids, "the store changed nothing yet"

    def test_confirming_a_remove_comes_back_still_filtered(self, panel):
        book_id, (small, mid, big) = panel.stock(
            PUBLISHABLE_16_20_SIZES, plan=plan_of(PUBLISHABLE_16_20_PLAN), status="published"
        )

        response = panel.client.post(
            f"/book/{book_id}/arrange-puzzles?bucket=16-20",
            data={"action": "delete", "puzzle_id": mid, "confirm": "1"},
        )

        html = response.get_data(as_text=True)
        assert response.status_code == 200
        assert mid not in panel.books.get_book(book_id).puzzle_ids
        assert current_band(html) == "16-20", html
        assert shown_ids(html) == [small, big], "the page comes back filtered, the removed row gone"
        assert figures(text_of(plan_line(html)))["total"] == (2, 3)


# --------------------------------------------------------------------------
# AC-7 — an unknown band is all sizes
# --------------------------------------------------------------------------


class TestArrangeSizeFilter_UnknownBucketMeansAllSizes:
    def test_a_bucket_that_names_no_band_lists_everything_and_shows_no_plan_line(self, panel):
        book_id, ids = sixteen_twenty_book(panel)

        html = panel.page(book_id, "bucket=nonsense")

        assert set(shown_ids(html)) == set(ids)
        assert plan_line(html) is None
        assert REORDER_OFF not in text_of(html)
        assert 'value="move_up"' in html
        assert current_links(html) == ["All sizes"], "the All sizes link is the one marked current"
        assert current_band(html) == "All sizes"

    def test_an_empty_bucket_is_the_same_as_none(self, panel):
        book_id, ids = sixteen_twenty_book(panel)

        assert set(shown_ids(panel.page(book_id, "bucket="))) == set(ids)


# --------------------------------------------------------------------------
# the property: the filter's invariant, over a seeded corpus
# --------------------------------------------------------------------------

#: How many books the corpus builds, and how many pages it must have checked.
#: Asserted inside the test so the corpus cannot quietly shrink.
CORPUS_BOOKS = 12
CORPUS_MIN_CHECKS = 60


class TestArrangeSizeFilter_PropertyBandIsExactlyItsMembers:
    def test_every_shown_row_is_in_the_band_and_every_member_is_shown(self, panel):
        rng = random.Random(192)
        books_checked = 0
        checks = 0
        for _ in range(CORPUS_BOOKS):
            sizes = []
            for _ in range(rng.randint(3, 7)):
                sizes.append(
                    (
                        rng.randint(MIN_SIZE, MAX_SIZE),
                        rng.randint(MIN_SIZE, MAX_SIZE),
                        rng.choice(["easy", "medium", "hard", None]),
                    )
                )
            if rng.random() < 0.5:
                # Outside the supported range: under no band, shown under All.
                sizes.append((MIN_SIZE - 1, 12, "easy"))
            if rng.random() < 0.5:
                sizes.append((MAX_SIZE + 1, 12, "hard"))
            book_id, ids = panel.stock(sizes)
            extent = dict(zip(ids, [(w, h) for w, h, _ in sizes]))
            books_checked += 1

            assert set(shown_ids(panel.page(book_id))) == set(ids)
            checks += 1
            for label in BAND_RANGES:
                shown = set(shown_ids(panel.page(book_id, f"bucket={label}")))
                expected = {pid for pid, (w, h) in extent.items() if in_band(w, h, label)}
                assert shown == expected, (label, sizes, shown, expected)
                assert all(in_band(*extent[pid], label) for pid in shown), (label, sizes)
                checks += 1

        assert books_checked == CORPUS_BOOKS
        assert checks >= CORPUS_MIN_CHECKS, f"the corpus checked only {checks} pages"
