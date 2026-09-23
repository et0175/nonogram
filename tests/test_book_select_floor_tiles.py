"""CARD-123 — the cell on every tile, the floor flag, and the finalise count.

    AC-182  a 30 x 25 puzzle with a 12-deep row-clue gutter shows 4.61 mm on
            its selection tile, with a below-floor flag and an override control
    AC-241  a 25 x 12 puzzle above the floor carries no flag at all — neither a
            below-floor flag nor a wide-grid one (FR-032 amended; AC-191/192
            retired, so only the floor flags a tile)
    AC-187  a book of 150 puzzles, 2 of them admitted below the floor with
            overrides, reports 2 below the floor on the finalise summary
    AC-188  the same summary is **recomputed on the book's current trim** every
            render: a 20 x 20 puzzle at 6.92 mm on 8.5 x 11 in becomes 4.65 mm
            when the trim is changed to 6 x 9 in, and the count goes 0 -> 1
    AC-239  (NFR-008) the flag half — a 12-deep band on a 30-wide grid falls
            below the floor and is flagged there

The evidence class is the Flask test client: these are user-facing criteria on
server-rendered screens and this project has no browser harness, so each drives
the real route and reads the real HTML that came back — the reading
``tests/test_book_floor.py`` and ``tests/test_book_select_tabs.py`` make.

The expected cell figures are the **card's** (4.61 mm, 6.92 mm, 4.65 mm) and
the grids here are built by hand to hit them; they are not re-derived from
``book_cell_mm``, which would only prove the code agrees with itself. What must
come from ``book_cell_mm`` is the number the product shows (G-1, EC-021), and
``tests/property/test_book_membership_floor.py`` holds the tile, the add
refusal and the finalise count to that one number over the whole corpus.
"""

from __future__ import annotations

import re
from types import SimpleNamespace

import pytest

import nonogram.admin.book_manager as book_manager_module
import nonogram.admin.image_manager as image_manager_module
from nonogram.admin.book_manager import BookManager
from nonogram.admin.book_page_spec import FLOOR_MM, book_cell_mm, book_page_spec
from tests.test_book_floor import Panel, clues_of, dotted_grid, text_of

#: AC-182/AC-239: 30 wide x 25 tall, row-clue gutter 12 deep, column-clue
#: gutter 8 — 42 cells across the sheet, 4.61 mm on the Book 1 profile. The
#: same fixture CARD-121's ACs use, so the tile and the refusal are about one
#: puzzle. Its tab is the 26-30 one.
BELOW_FLOOR = (30, 25, 12, 8, 4.61, "26-30")

#: AC-241: 25 wide x 12 tall — a *wide* grid, comfortably above the floor.
#: The card states "6.0 mm"; that exact figure is not reachable at this extent
#: on the Book 1 profile (the sheet's 193.675 mm of usable width divided by a
#: whole number of cells lands on 6.05 or 5.87, never 6.00), so the nearest
#: grid is taken and the criterion's substance — a wide grid above the floor
#: carries no flag — is what is asserted. Its tab is the 21-25 one.
ABOVE_FLOOR_WIDE = (25, 12, 7, 4, 6.05, "21-25")

#: AC-188: 20 x 20 with 8-deep gutters — 6.92 mm on 8.5 x 11 in, 4.65 mm once
#: the trim becomes 6 x 9 in. Its tab is the 16-20 one.
TRIM_SENSITIVE = (20, 20, 8, 8, 6.92, 4.65)

#: A tiny grid that clears the floor on any supported trim: filler for AC-187's
#: 150-puzzle book.
COMFORTABLE = (10, 10, 1, 1)

#: 6 x 9 inches as the ``books`` print columns store it (centimetres).
SIX_BY_NINE = {"trim_width_cm": "15.24", "trim_height_cm": "22.86"}


# --------------------------------------------------------------------------
# the panel, and the two screens read as the owner reads them
# --------------------------------------------------------------------------


@pytest.fixture
def admin_app(monkeypatch):
    """The panel in in-memory mode, with a book manager of its own.

    The same fixture ``tests/test_book_floor.py`` uses, spelled out here
    rather than imported so that this file's tests stand on their own; the
    module singletons are emptied on both sides so no book or picture made
    here can be inherited by the next test's panel.
    """
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
    book_manager_module._book_manager = BookManager(session_factory=None)


@pytest.fixture
def panel(admin_app):
    return Panel(admin_app)


def tab_html(panel, book_id, bucket) -> str:
    """The selection step's HTML for one longest-side tab."""
    response = panel.client.get(f"/book/{book_id}/select-puzzles?bucket={bucket}")
    assert response.status_code == 200
    return response.get_data(as_text=True)


def tile_of(html: str, puzzle_id: str) -> str:
    """One tile's markup, cut out of the rendered tab.

    From this tile's opening ``<div class="puzzle-tile" …>`` to the next one
    (or to the end of the grid), so an assertion about "the tile" cannot be
    satisfied by a neighbour's markup.
    """
    opening = f'<div class="puzzle-tile" data-puzzle-id="{puzzle_id}"'
    start = html.find(opening)
    assert start != -1, f"no tile for puzzle {puzzle_id} on this tab"
    rest = html[start + len(opening):]
    end = rest.find('<div class="puzzle-tile"')
    return opening + (rest if end == -1 else rest[:end])


def finalize_html(panel, book_id) -> str:
    response = panel.client.get(f"/book/{book_id}/finalize")
    assert response.status_code == 200
    return response.get_data(as_text=True)


def below_floor_count(html: str) -> int:
    """The finalise summary's below-the-floor figure, read off the page."""
    match = re.search(r'data-below-floor-count="(\d+)"', html)
    assert match is not None, "the finalise summary reports no below-floor figure"
    return int(match.group(1))


def retrim(panel, book_id, **columns) -> None:
    """Change the book's stored trim, as a Print-setup save would.

    The columns themselves, because what AC-188 is about is that the summary
    reads *them* on every render rather than remembering an earlier verdict.
    """
    book = panel.books.books[book_id]
    for column, value in columns.items():
        setattr(book, column, value)


def cell_of(shape, book) -> float:
    """``book_cell_mm`` for a hand-built grid on a book — the one computation."""
    width, height, row_gutter, column_gutter = shape[:4]
    rows, columns = clues_of(dotted_grid(width, height, row_gutter, column_gutter))
    return book_cell_mm(
        book_page_spec(book),
        tuple(tuple(line) for line in rows),
        tuple(tuple(line) for line in columns),
    )


# --------------------------------------------------------------------------
# AC-182 — the tile shows its cell, flags the floor, and offers the override
# --------------------------------------------------------------------------


class TestBookSelect_TileShowsCellAndBelowFloorFlag:
    """A 4.61 mm puzzle's tile says 4.61 mm and says it is under the floor."""

    def test_the_tile_shows_the_cell_to_two_decimals(self, panel) -> None:
        width, height, row_gutter, column_gutter, cell, bucket = BELOW_FLOOR
        puzzle_id = panel.puzzle(width, height, row_gutter, column_gutter)
        book_id = panel.book()

        tile = tile_of(tab_html(panel, book_id, bucket), puzzle_id)

        assert f"{cell:.2f} mm" in text_of(tile), (
            f"the tile must show the puzzle's cell on this book ({cell:.2f} mm); "
            f"it showed: {text_of(tile)}"
        )
        # One decimal is too coarse beside a 4.8 mm floor, so the markup's own
        # figure is pinned at two as well.
        assert f'data-book-cell-mm="{cell:.2f}"' in tile

    def test_the_tile_carries_a_below_floor_flag_in_words(self, panel) -> None:
        """A11y minimum: the flag is text, never colour alone."""
        puzzle_id = panel.puzzle(*BELOW_FLOOR[:4])
        book_id = panel.book()

        tile = tile_of(tab_html(panel, book_id, BELOW_FLOOR[5]), puzzle_id)

        assert f"Below the {FLOOR_MM:g} mm floor" in text_of(tile), (
            f"the tile must say it is under the floor; it said: {text_of(tile)}"
        )
        assert 'data-below-floor="true"' in tile

    def test_the_flag_comes_with_the_override_control_the_store_reads(self, panel) -> None:
        """``override_<id>`` is the field CARD-121 fixed; this renders it."""
        puzzle_id = panel.puzzle(*BELOW_FLOOR[:4])
        book_id = panel.book()

        tile = tile_of(tab_html(panel, book_id, BELOW_FLOOR[5]), puzzle_id)

        assert f'name="override_{puzzle_id}"' in tile
        assert "Include below floor" in text_of(tile)

    def test_the_rendered_control_is_the_one_that_actually_admits_it(self, panel) -> None:
        """End to end: tick what the tile renders, and the puzzle joins.

        The tile would be a decoration if its control's name were not the one
        the book store reads, so the field is submitted exactly as the page
        spells it rather than as this test remembers it.
        """
        puzzle_id = panel.puzzle(*BELOW_FLOOR[:4])
        book_id = panel.book()
        tile = tile_of(tab_html(panel, book_id, BELOW_FLOOR[5]), puzzle_id)
        field = re.search(r'name="(override_[^"]+)"', tile).group(1)

        panel.client.post(
            f"/book/{book_id}/select-puzzles",
            data={
                "bucket": BELOW_FLOOR[5],
                "shown_ids": [puzzle_id],
                "puzzle_ids": [puzzle_id],
                field: "on",
            },
            follow_redirects=True,
        )

        assert panel.ids_of(book_id) == [puzzle_id]
        assert panel.books.floor_overrides(book_id) == [puzzle_id]

    def test_the_tile_and_the_add_refusal_name_the_same_millimetres(self, panel) -> None:
        """G-1/EC-021 on one puzzle: one computation, so one number."""
        puzzle_id = panel.puzzle(*BELOW_FLOOR[:4])
        book_id = panel.book()

        tile = tile_of(tab_html(panel, book_id, BELOW_FLOOR[5]), puzzle_id)
        refused = text_of(panel.select(book_id, [puzzle_id]).get_data(as_text=True))

        refusal = panel.books.below_floor(book_id, [puzzle_id])[0]
        assert f'data-book-cell-mm="{refusal.cell_mm:.2f}"' in tile
        assert f"{refusal.cell_mm:.2f} mm" in refused


# --------------------------------------------------------------------------
# AC-241 — a wide grid above the floor carries no flag of its own
# --------------------------------------------------------------------------


class TestBookSelect_WideGridAboveFloorCarriesNoFlag:
    """FR-032 amended (G-2): only the floor flags a tile. Width does not."""

    def test_the_tile_shows_its_cell_and_nothing_else(self, panel) -> None:
        width, height, row_gutter, column_gutter, cell, bucket = ABOVE_FLOOR_WIDE
        puzzle_id = panel.puzzle(width, height, row_gutter, column_gutter)
        book_id = panel.book()

        tile = tile_of(tab_html(panel, book_id, bucket), puzzle_id)

        assert f"{cell:.2f} mm" in text_of(tile)
        assert cell >= FLOOR_MM, "the fixture must clear the floor for this to mean anything"

    def test_no_below_floor_flag(self, panel) -> None:
        puzzle_id = panel.puzzle(*ABOVE_FLOOR_WIDE[:4])
        book_id = panel.book()

        tile = tile_of(tab_html(panel, book_id, ABOVE_FLOOR_WIDE[5]), puzzle_id)

        assert "data-below-floor" not in tile
        assert "floor" not in text_of(tile).lower(), (
            f"a puzzle above the floor must not mention it; the tile said: {text_of(tile)}"
        )

    def test_no_wide_grid_flag_and_no_override_control(self, panel) -> None:
        """AC-191/AC-192 are retired: a wide grid has no flag of its own."""
        puzzle_id = panel.puzzle(*ABOVE_FLOOR_WIDE[:4])
        book_id = panel.book()

        tile = tile_of(tab_html(panel, book_id, ABOVE_FLOOR_WIDE[5]), puzzle_id)

        assert "wide" not in text_of(tile).lower()
        assert f"override_{puzzle_id}" not in tile, (
            "nothing to override: this puzzle clears the floor"
        )

    def test_it_joins_the_book_with_no_override_at_all(self, panel) -> None:
        """The flagless tile is the truth: the store takes it as it is."""
        puzzle_id = panel.puzzle(*ABOVE_FLOOR_WIDE[:4])
        book_id = panel.book()

        panel.client.post(
            f"/book/{book_id}/select-puzzles",
            data={
                "bucket": ABOVE_FLOOR_WIDE[5],
                "shown_ids": [puzzle_id],
                "puzzle_ids": [puzzle_id],
            },
            follow_redirects=True,
        )

        assert panel.ids_of(book_id) == [puzzle_id]
        assert panel.books.floor_overrides(book_id) == []


# --------------------------------------------------------------------------
# AC-187 — the finalise summary counts the book's below-floor puzzles
# --------------------------------------------------------------------------


class TestBookFinalize_SummaryCountsPuzzlesBelowFloor:
    """150 puzzles, 2 of them admitted below the floor: the summary says 2."""

    @staticmethod
    def _book_of_150(panel):
        book_id = panel.book()
        comfortable = [panel.puzzle(*COMFORTABLE) for _ in range(148)]
        small = [
            panel.puzzle(*BELOW_FLOOR[:4]),
            panel.puzzle(*BELOW_FLOOR[:4], tier="medium"),
        ]
        panel.books.add_puzzles_to_book(book_id, comfortable + small, small)
        assert len(panel.ids_of(book_id)) == 150
        assert sorted(panel.books.floor_overrides(book_id)) == sorted(small)
        return book_id, small

    def test_the_summary_reports_two_below_the_floor(self, panel) -> None:
        book_id, _ = self._book_of_150(panel)

        html = finalize_html(panel, book_id)

        assert below_floor_count(html) == 2
        assert f"Below the {FLOOR_MM:g} mm floor" in text_of(html)

    def test_it_names_them_with_their_own_cells(self, panel) -> None:
        book_id, small = self._book_of_150(panel)

        shown = text_of(finalize_html(panel, book_id))

        for puzzle_id in small:
            assert puzzle_id in shown
        assert f"{BELOW_FLOOR[4]:.2f} mm" in shown

    def test_a_book_with_none_below_the_floor_renders_a_zero(self, panel) -> None:
        """StatBlock's "zero" state: 0 is printed, never hidden."""
        book_id = panel.book()
        panel.books.add_puzzles_to_book(book_id, [panel.puzzle(*COMFORTABLE)])

        html = finalize_html(panel, book_id)

        assert below_floor_count(html) == 0
        assert f"Below the {FLOOR_MM:g} mm floor 0" in text_of(html)

    def test_the_count_is_the_store_s_own_verdict_on_the_same_members(
        self, panel
    ) -> None:
        """EC-021: the count and the refusal cannot disagree about a puzzle."""
        book_id, _ = self._book_of_150(panel)
        members = panel.ids_of(book_id)

        counted = below_floor_count(finalize_html(panel, book_id))

        assert counted == len(panel.books.below_floor(book_id, members))


# --------------------------------------------------------------------------
# AC-188 — and it is recomputed on the book's current trim every render
# --------------------------------------------------------------------------


class TestBookFinalize_SummaryRecountsBelowFloorAfterTrimChange:
    """No stored verdict: the summary measures the sheet the book has now."""

    @staticmethod
    def _book_with_the_trim_sensitive_puzzle(panel):
        book_id = panel.book()
        puzzle_id = panel.puzzle(*TRIM_SENSITIVE[:4])
        panel.books.add_puzzles_to_book(book_id, [puzzle_id])
        assert panel.ids_of(book_id) == [puzzle_id]
        return book_id, puzzle_id

    def test_on_the_book_1_profile_nothing_is_below_the_floor(self, panel) -> None:
        book_id, _ = self._book_with_the_trim_sensitive_puzzle(panel)

        html = finalize_html(panel, book_id)

        assert below_floor_count(html) == 0
        assert cell_of(TRIM_SENSITIVE, panel.books.get_book(book_id)) == pytest.approx(
            TRIM_SENSITIVE[4], abs=0.005
        )

    def test_changing_the_trim_to_six_by_nine_makes_it_one(self, panel) -> None:
        book_id, _ = self._book_with_the_trim_sensitive_puzzle(panel)
        assert below_floor_count(finalize_html(panel, book_id)) == 0

        retrim(panel, book_id, **SIX_BY_NINE)

        html = finalize_html(panel, book_id)
        assert below_floor_count(html) == 1, (
            "the summary kept an answer it made on the old trim; AC-188 asks for "
            "it to be recomputed every render"
        )
        assert f"{TRIM_SENSITIVE[5]:.2f} mm" in text_of(html), (
            f"it must name the cell on the *new* trim ({TRIM_SENSITIVE[5]:.2f} mm)"
        )

    def test_the_stored_override_is_not_what_the_count_reads(self, panel) -> None:
        """The book stores no override at all here, and still counts 1.

        An override records that the owner accepted a small cell once, not
        that the cell is still small — so the count cannot be read from it.
        """
        book_id, _ = self._book_with_the_trim_sensitive_puzzle(panel)
        retrim(panel, book_id, **SIX_BY_NINE)

        assert panel.books.floor_overrides(book_id) == []
        assert below_floor_count(finalize_html(panel, book_id)) == 1

    def test_changing_it_back_takes_the_count_back_down(self, panel) -> None:
        book_id, _ = self._book_with_the_trim_sensitive_puzzle(panel)
        retrim(panel, book_id, **SIX_BY_NINE)
        assert below_floor_count(finalize_html(panel, book_id)) == 1

        retrim(panel, book_id, trim_width_cm="21.59", trim_height_cm="27.94")

        assert below_floor_count(finalize_html(panel, book_id)) == 0

    def test_the_selection_tile_moves_with_the_trim_too(self, panel) -> None:
        """One sheet, one number: the tile is measured on the same columns."""
        puzzle_id = panel.puzzle(*TRIM_SENSITIVE[:4])
        book_id = panel.book()
        before = tile_of(tab_html(panel, book_id, "16-20"), puzzle_id)
        assert f'data-book-cell-mm="{TRIM_SENSITIVE[4]:.2f}"' in before
        assert "data-below-floor" not in before

        retrim(panel, book_id, **SIX_BY_NINE)

        after = tile_of(tab_html(panel, book_id, "16-20"), puzzle_id)
        assert f'data-book-cell-mm="{TRIM_SENSITIVE[5]:.2f}"' in after
        assert 'data-below-floor="true"' in after


# --------------------------------------------------------------------------
# AC-239 (NFR-008) — the flag half: a 12-deep band falls below the floor
# --------------------------------------------------------------------------


class TestBookCell_TwelveDeepBandFallsBelowFloor:
    """The 4.61 mm cell itself is CARD-114's; this is that it is *flagged*."""

    def test_the_computed_cell_is_under_the_floor(self, panel) -> None:
        book_id = panel.book()

        cell = cell_of(BELOW_FLOOR, panel.books.get_book(book_id))

        assert cell < FLOOR_MM, (
            f"a 30-wide grid with a 12-deep row-clue gutter prints at {cell:.2f} mm "
            f"on the Book 1 profile, which NFR-008's {FLOOR_MM:g} mm floor refuses"
        )

    def test_the_store_names_it_as_below_the_floor(self, panel) -> None:
        puzzle_id = panel.puzzle(*BELOW_FLOOR[:4])
        book_id = panel.book()

        refusals = panel.books.below_floor(book_id, [puzzle_id])

        assert [r.puzzle_id for r in refusals] == [puzzle_id]
        assert refusals[0].cell_mm < FLOOR_MM

    def test_the_selection_tile_carries_the_flag(self, panel) -> None:
        puzzle_id = panel.puzzle(*BELOW_FLOOR[:4])
        book_id = panel.book()

        tile = tile_of(tab_html(panel, book_id, BELOW_FLOOR[5]), puzzle_id)

        assert 'data-below-floor="true"' in tile
        assert f"Below the {FLOOR_MM:g} mm floor" in text_of(tile)

    def test_a_shallower_band_on_the_same_extent_clears_it(self, panel) -> None:
        """The band is what does it, not the 30 cells: AC-186's 4.84 mm grid."""
        book_id = panel.book()

        assert cell_of((30, 20, 10, 8), panel.books.get_book(book_id)) >= FLOOR_MM


# --------------------------------------------------------------------------
# the postures the screens need when a cell cannot be measured at all
# --------------------------------------------------------------------------


class TestBookFloorTiles_UnmeasurableCellsFailClosed:
    """A cell nobody can compute is not a cell known to clear the floor."""

    def test_an_unreadable_clue_set_is_flagged_rather_than_shown_as_a_number(
        self, panel
    ) -> None:
        puzzle_id = panel.puzzle(*BELOW_FLOOR[:4])
        book_id = panel.book()
        panel.store.puzzles[puzzle_id]["clues_rows"] = []

        tile = tile_of(tab_html(panel, book_id, BELOW_FLOOR[5]), puzzle_id)

        assert "data-book-cell-mm" not in tile
        assert 'data-below-floor="true"' in tile
        assert "not measurable" in text_of(tile)

    def test_a_book_whose_trim_cannot_be_read_shows_no_cell_at_all(
        self, panel
    ) -> None:
        puzzle_id = panel.puzzle(*BELOW_FLOOR[:4])
        book_id = panel.book()
        retrim(panel, book_id, trim_width_cm="not a number")

        tile = tile_of(tab_html(panel, book_id, BELOW_FLOOR[5]), puzzle_id)

        assert "data-book-cell-mm" not in tile
        assert "not measurable" in text_of(tile)

    def test_the_finalise_count_holds_the_same_posture(self, panel) -> None:
        book_id = panel.book()
        puzzle_id = panel.puzzle(*COMFORTABLE)
        panel.books.add_puzzles_to_book(book_id, [puzzle_id])
        assert below_floor_count(finalize_html(panel, book_id)) == 0

        panel.store.puzzles[puzzle_id]["clues_cols"] = []

        html = finalize_html(panel, book_id)
        assert below_floor_count(html) == 1
        assert "cell cannot be measured" in text_of(html)


# --------------------------------------------------------------------------
# G-1 — the admin fits no cell of its own (ADR-0036/R2)
# --------------------------------------------------------------------------


class TestBookFloorTiles_TheCellIsTheOneComputation:
    """The panel's figure is ``book_cell_mm``'s, whatever that returns."""

    def test_the_tile_follows_book_cell_mm_rather_than_a_rule_of_its_own(
        self, panel, monkeypatch
    ) -> None:
        puzzle_id = panel.puzzle(*BELOW_FLOOR[:4])
        book_id = panel.book()
        import nonogram.admin.app as app_module

        monkeypatch.setattr(app_module, "book_cell_mm", lambda *a, **k: 12.34)

        tile = tile_of(tab_html(panel, book_id, BELOW_FLOOR[5]), puzzle_id)

        assert 'data-book-cell-mm="12.34"' in tile
        assert "data-below-floor" not in tile, (
            "the flag must follow the one computation's answer, not the grid's shape"
        )

    def test_the_finalise_count_follows_it_too(self, panel, monkeypatch) -> None:
        book_id = panel.book()
        puzzle_id = panel.puzzle(*COMFORTABLE)
        panel.books.add_puzzles_to_book(book_id, [puzzle_id])
        import nonogram.admin.app as app_module

        monkeypatch.setattr(app_module, "book_cell_mm", lambda *a, **k: 1.0)

        assert below_floor_count(finalize_html(panel, book_id)) == 1

    def test_the_sheet_is_book_page_spec_s(self, panel) -> None:
        """``book_page_spec(book)`` and nothing the panel built itself."""
        book_id = panel.book()
        book = panel.books.get_book(book_id)
        profile_spec = book_page_spec(book)
        retrim(panel, book_id, **SIX_BY_NINE)
        six_by_nine_spec = book_page_spec(panel.books.get_book(book_id))

        assert profile_spec != six_by_nine_spec
        assert book_cell_mm(
            six_by_nine_spec, *[tuple(tuple(l) for l in c) for c in clues_of(
                dotted_grid(*TRIM_SENSITIVE[:4])
            )]
        ) == pytest.approx(TRIM_SENSITIVE[5], abs=0.005)
