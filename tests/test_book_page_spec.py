"""CARD-115 — the book's PageSpec from its stored trim and margins, Book 1 profile as the fallback.

    AC-181  TestBookCreate_StoresBook1PrintProfile             (both storage
            modes, and the /book/create route with no print values entered)
    AC-178  TestBookPageSpec_EmptyMarginsFallBackToBook1Profile (the builder
            half; the PDF half is CARD-116)
    AC-272  TestBookPageSpec_OddPageGutterOnLeft
    AC-273  TestBookPageSpec_EvenPageGutterOnRight
    NFR-008 TestBookPageSpec_FlatStandardCellCap               (the 7.5 mm cap)
            TestBookPageSpec_MinimumSideMargin
    G-1     TestBookCellMm_OnlyReadsComputeLayout               (ADR-0036/R2)
    F-001/F-003 (CARD-114 minors) TestBookPageSpec_RefusesBadStoredTrimNamingTheColumn
    011     TestMigration011                                    (defaults only,
            no backfill, a working downgrade)

The standing properties (parity moves margins, never the usable size; empty
margins build the CON-018 sheet) are in ``tests/property/test_book_page_spec.py``.

Expected numbers are CON-018's own, in millimetres, written as literals
(8.5 in = 215.9 mm, 0.5 in = 12.7 mm, 0.375 in = 9.525 mm) and never read
back from ``BOOK1_PROFILE``.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

import nonogram.admin.book_manager as book_manager_module
from nonogram.admin.book_manager import BookManager
from nonogram.admin.book_page_spec import BOOK1_PROFILE, book_cell_mm, book_page_spec
from nonogram.admin.print_specs import PrintSpecValidator
from nonogram.admin.puzzle_review import PuzzleReviewService
from nonogram.export.layout import (
    DEFAULT_PAGE_SPEC,
    DPI,
    OrientationPolicy,
    PageParity,
    PageSpec,
    compute_layout,
)
from tests.helpers.db import sqlite_session_scope

MODES = ("memory", "db")

#: CON-018 as the stored columns (AC-181's numbers).
CON018_COLUMNS = {
    "trim_width_cm": "21.59",
    "trim_height_cm": "27.94",
    "gutter_margin_cm": "1.27",
    "outside_margin_cm": "0.95",
}

#: CON-018 as a sheet, literal millimetres, for an odd (right-hand) page.
CON018_ODD = PageSpec(
    width_mm=215.9,
    height_mm=279.4,
    top_mm=9.525,
    bottom_mm=9.525,
    gutter_mm=12.7,
    outside_mm=9.525,
    band_mm=12.0,
    orientation=OrientationPolicy.PORTRAIT_ONLY,
    cell_cap=7.5,
    min_thin_rule_mm=0.25,
    parity=PageParity.ODD,
)

#: Half a device pixel, in mm: the most a placed edge can move when rounded.
HALF_PX_MM = 0.5 / DPI * 25.4


def _clues(lines: int, depth: int) -> tuple[tuple[int, ...], ...]:
    """``lines`` clues, each ``depth`` runs of 1: a gutter exactly ``depth`` deep."""
    return tuple((1,) * depth for _ in range(lines))


def _book(**columns):
    return SimpleNamespace(**columns)


def _px_to_mm(pixels: int) -> float:
    return pixels / DPI * 25.4


# --------------------------------------------------------------------------
# Storage-mode plumbing
# --------------------------------------------------------------------------


@pytest.fixture
def scope(tmp_path):
    return sqlite_session_scope(tmp_path, "book-page-spec.db")


def _manager(mode, scope) -> BookManager:
    if mode == "memory":
        return BookManager(session_factory=None)
    return BookManager(session_factory=scope, puzzle_store=PuzzleReviewService(session_factory=scope))


def _build_app(mode, scope, monkeypatch):
    from nonogram.admin.app import create_app

    monkeypatch.setenv("TESTING", "true")
    if mode == "memory":
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setattr(book_manager_module, "_book_manager", BookManager(session_factory=None))
    else:
        import nonogram.db

        monkeypatch.setenv("DATABASE_URL", "sqlite:///card-115-test-only")
        monkeypatch.setattr(nonogram.db, "session_scope", scope)
    app = create_app()
    app.config["TESTING"] = True
    return app


def _stored_row_columns(scope, book_id: str) -> dict:
    """The print columns as the ``books`` row holds them, read through a fresh session."""
    from nonogram.db.models import Book as DBBook

    with scope() as db:
        row = db.query(DBBook).filter(DBBook.id == uuid.UUID(book_id)).one()
        return {name: getattr(row, name) for name in (*CON018_COLUMNS, "outside_margin_bleed_cm")}


def _print_columns(book) -> dict:
    return {name: getattr(book, name) for name in (*CON018_COLUMNS, "outside_margin_bleed_cm")}


# --------------------------------------------------------------------------
# AC-181
# --------------------------------------------------------------------------


class TestBookCreate_StoresBook1PrintProfile:
    @pytest.mark.parametrize("mode", MODES)
    def test_book_manager_stores_con018_profile(self, mode, scope) -> None:
        books = _manager(mode, scope)
        book_id = books.create_book("Winter", "Twenty winter pictures.", "generic", "adults")

        assert _print_columns(books.get_book(book_id)) == {**CON018_COLUMNS, "outside_margin_bleed_cm": None}
        if mode == "db":
            assert _stored_row_columns(scope, book_id) == {**CON018_COLUMNS, "outside_margin_bleed_cm": None}

    @pytest.mark.parametrize("mode", MODES)
    def test_create_route_with_no_print_values_stores_con018_profile(self, mode, scope, monkeypatch) -> None:
        app = _build_app(mode, scope, monkeypatch)
        response = app.test_client().post(
            "/book/create",
            data={"title": "Winter", "description": "Twenty pictures.", "theme": "generic", "target_audience": "adults"},
        )
        assert response.status_code == 302
        book_id = response.headers["Location"].rstrip("/").split("/")[-2]

        assert _print_columns(app.book_manager.get_book(book_id)) == {
            **CON018_COLUMNS,
            "outside_margin_bleed_cm": None,
        }
        if mode == "db":
            assert _stored_row_columns(scope, book_id) == {**CON018_COLUMNS, "outside_margin_bleed_cm": None}

    def test_print_spec_defaults_agree_with_the_profile(self) -> None:
        spec, error = PrintSpecValidator.create_spec()
        assert error is None
        assert spec.to_dict() == {**CON018_COLUMNS, "outside_margin_bleed_cm": None}
        assert PrintSpecValidator.DEFAULT_TRIM_WIDTH_CM == BOOK1_PROFILE.trim_width_cm

    def test_empty_margin_fields_take_the_profile_but_entered_ones_are_kept(self) -> None:
        spec, _ = PrintSpecValidator.create_spec(gutter_margin_cm="", outside_margin_cm=None)
        assert (spec.gutter_margin_cm, spec.outside_margin_cm) == ("1.27", "0.95")
        spec, _ = PrintSpecValidator.create_spec(gutter_margin_cm="1.60", outside_margin_cm="1.00")
        assert (spec.gutter_margin_cm, spec.outside_margin_cm) == ("1.60", "1.00")

    def test_model_defaults_mirror_the_profile(self) -> None:
        from nonogram.db.models import Book as DBBook

        columns = DBBook.__table__.columns
        for name in ("gutter_margin_cm", "outside_margin_cm"):
            assert columns[name].default.arg == CON018_COLUMNS[name]
            assert columns[name].server_default.arg == CON018_COLUMNS[name]
            assert columns[name].nullable


# --------------------------------------------------------------------------
# AC-178 (builder half)
# --------------------------------------------------------------------------


class TestBookPageSpec_EmptyMarginsFallBackToBook1Profile:
    @pytest.mark.parametrize(
        "margins",
        [
            {"gutter_margin_cm": None, "outside_margin_cm": None},
            {"gutter_margin_cm": "", "outside_margin_cm": "  "},
            {},  # columns missing altogether
        ],
        ids=["null", "blank", "missing"],
    )
    def test_empty_margins_build_the_con018_sheet(self, margins) -> None:
        book = _book(trim_width_cm="21.59", trim_height_cm="27.94", **margins)
        assert book_page_spec(book) == book_page_spec(_book(**CON018_COLUMNS)) == CON018_ODD

    def test_legacy_db_row_with_null_margins(self, scope) -> None:
        from nonogram.db.models import Book as DBBook

        import sqlalchemy as sa

        legacy = uuid.uuid4()
        with scope() as db:
            db.add(DBBook(id=legacy, title="Legacy", puzzle_ids=[], puzzle_titles={}, book_metadata={}))
        # A row from before migration 011: its margins were never written.
        with scope() as db:
            db.execute(sa.text("UPDATE books SET gutter_margin_cm = NULL, outside_margin_cm = NULL"))
        assert _stored_row_columns(scope, str(legacy))["gutter_margin_cm"] is None
        book = BookManager(session_factory=scope).get_book(str(legacy))
        assert (book.gutter_margin_cm, book.outside_margin_cm) == (None, None)
        assert book_page_spec(book) == CON018_ODD

    def test_thirty_by_thirty_nine_deep_cell_is_4_97_mm(self) -> None:
        spec = book_page_spec(_book(trim_width_cm="21.59", trim_height_cm="27.94"))
        clues = _clues(30, 9)
        # FR-030: 193.675 mm usable width / (30 + 9) cells = 4.966 mm.
        assert book_cell_mm(spec, clues, clues) == pytest.approx(4.97, abs=0.05)
        assert book_cell_mm(spec, clues, clues) == pytest.approx(193.675 / 39, abs=1e-9)


# --------------------------------------------------------------------------
# AC-272 / AC-273 — mirrored margins
# --------------------------------------------------------------------------


def _usable_span_mm(page_number: int) -> tuple[float, float, PageSpec]:
    spec = book_page_spec(_book(**CON018_COLUMNS), page_number)
    return spec.left_margin_mm, spec.width_mm - spec.right_margin_mm, spec


class TestBookPageSpec_OddPageGutterOnLeft:
    def test_page_3_usable_area_spans_12_7_to_206_375_mm(self) -> None:
        left, right, spec = _usable_span_mm(3)
        assert spec.parity is PageParity.ODD
        assert left == pytest.approx(12.7, abs=1e-9)
        assert right == pytest.approx(206.375, abs=1e-9)

    def test_placed_page_puts_the_usable_area_there(self) -> None:
        _, _, spec = _usable_span_mm(3)
        page = compute_layout(_clues(20, 5), _clues(20, 5), page_spec=spec).page
        assert _px_to_mm(page.usable_left) == pytest.approx(12.7, abs=HALF_PX_MM)
        assert _px_to_mm(page.usable_right) == pytest.approx(206.375, abs=HALF_PX_MM)

    def test_interior_page_1_the_guide_page_is_right_hand(self) -> None:
        assert book_page_spec(_book(**CON018_COLUMNS), 1).parity is PageParity.ODD
        assert book_page_spec(_book(**CON018_COLUMNS)).parity is PageParity.ODD


class TestBookPageSpec_EvenPageGutterOnRight:
    def test_page_4_usable_area_spans_9_525_to_203_2_mm(self) -> None:
        left, right, spec = _usable_span_mm(4)
        assert spec.parity is PageParity.EVEN
        assert left == pytest.approx(9.525, abs=1e-9)
        assert right == pytest.approx(203.2, abs=1e-9)

    def test_placed_page_puts_the_usable_area_there(self) -> None:
        _, _, spec = _usable_span_mm(4)
        page = compute_layout(_clues(20, 5), _clues(20, 5), page_spec=spec).page
        assert _px_to_mm(page.usable_left) == pytest.approx(9.525, abs=HALF_PX_MM)
        assert _px_to_mm(page.usable_right) == pytest.approx(203.2, abs=HALF_PX_MM)

    @pytest.mark.parametrize("page_number", [0, -1, 1.0, True, "2", None])
    def test_page_number_must_be_a_whole_number_from_one(self, page_number) -> None:
        with pytest.raises(ValueError, match="page_number"):
            book_page_spec(_book(**CON018_COLUMNS), page_number)


# --------------------------------------------------------------------------
# NFR-008 cap, sheet shape, minimum margin
# --------------------------------------------------------------------------


class TestBookPageSpec_FlatStandardCellCap:
    def test_spec_is_portrait_only_with_flat_cap_and_stroke_minimum(self) -> None:
        spec = book_page_spec(_book(**CON018_COLUMNS))
        assert spec.orientation is OrientationPolicy.PORTRAIT_ONLY
        assert spec.cell_cap == 7.5
        assert spec.min_thin_rule_mm == 0.25
        assert (spec.top_mm, spec.bottom_mm, spec.band_mm) == (9.525, 9.525, 12.0)

    def test_small_grid_is_held_at_7_5_mm_not_the_comfort_curve(self) -> None:
        # A 10x10 with 1-deep gutters would get 9.0 mm on NFR-005's curve and
        # far more by page fit; the book caps it flat at 7.5 mm.
        spec = book_page_spec(_book(**CON018_COLUMNS))
        assert book_cell_mm(spec, _clues(10, 1), _clues(10, 1)) == 7.5

    def test_the_cap_holds_on_a_larger_trim_too(self) -> None:
        spec = book_page_spec(_book(trim_width_cm="30", trim_height_cm="48"))
        assert book_cell_mm(spec, _clues(30, 1), _clues(30, 1)) == 7.5


class TestBookPageSpec_MinimumSideMargin:
    @pytest.mark.parametrize("column", ["gutter_margin_cm", "outside_margin_cm"])
    def test_margin_below_quarter_inch_refused_naming_the_column(self, column) -> None:
        with pytest.raises(ValueError, match=column):
            book_page_spec(_book(**{**CON018_COLUMNS, column: "0.60"}))

    @pytest.mark.parametrize("column", ["gutter_margin_cm", "outside_margin_cm"])
    def test_quarter_inch_margin_accepted(self, column) -> None:
        spec = book_page_spec(_book(**{**CON018_COLUMNS, column: "0.635"}))
        assert getattr(spec, column.replace("_margin_cm", "_mm")) == pytest.approx(6.35)

    def test_margins_leaving_no_usable_width_refused_naming_both(self) -> None:
        with pytest.raises(ValueError, match="gutter_margin_cm \\+ outside_margin_cm"):
            book_page_spec(_book(**{**CON018_COLUMNS, "gutter_margin_cm": "11", "outside_margin_cm": "11"}))

    def test_a_stored_non_profile_margin_is_read_as_written(self) -> None:
        spec = book_page_spec(_book(**{**CON018_COLUMNS, "gutter_margin_cm": "1.60", "outside_margin_cm": "1.00"}))
        assert (spec.gutter_mm, spec.outside_mm) == (16.0, 10.0)


# --------------------------------------------------------------------------
# CARD-114 F-001 / F-003 — a bad stored trim names its column
# --------------------------------------------------------------------------


class TestBookPageSpec_RefusesBadStoredTrimNamingTheColumn:
    @pytest.mark.parametrize("value", ["abc", "nan", "inf", "-inf", True, [21.59], np.float64("nan")])
    @pytest.mark.parametrize("column", ["trim_width_cm", "trim_height_cm"])
    def test_non_numeric_trim(self, column, value) -> None:
        with pytest.raises(ValueError, match=column):
            book_page_spec(_book(**{**CON018_COLUMNS, column: value}))

    @pytest.mark.parametrize(
        "column, value", [("trim_width_cm", "30.01"), ("trim_height_cm", "48.01"), ("trim_width_cm", "9.99"), ("trim_height_cm", "0")]
    )
    def test_trim_outside_kdp_bounds(self, column, value) -> None:
        with pytest.raises(ValueError, match=column):
            book_page_spec(_book(**{**CON018_COLUMNS, column: value}))

    def test_numpy_scalar_trim_reaches_the_sheet_as_a_plain_float(self) -> None:
        spec = book_page_spec(_book(**{**CON018_COLUMNS, "trim_width_cm": np.float64(21.0)}))
        assert type(spec.width_mm) is float and spec.width_mm == 210.0

    def test_kdp_bounds_are_the_same_as_the_print_setup_form(self) -> None:
        assert PrintSpecValidator.validate_trim_size("30.0", "48.0") == (True, None)
        assert book_page_spec(_book(trim_width_cm="30.0", trim_height_cm="48.0")).width_mm == 300.0


# --------------------------------------------------------------------------
# G-1 — book_cell_mm reads compute_layout and fits nothing itself
# --------------------------------------------------------------------------


class TestBookCellMm_OnlyReadsComputeLayout:
    def test_is_the_placed_page_cell_mm_not_the_pixel_cell(self) -> None:
        # CARD-114 handover: a 30-wide grid under a 12-deep band is 4.61 mm
        # exactly; converting the pixel cell would give 4.57 mm.
        spec = book_page_spec(_book(**CON018_COLUMNS))
        clues = _clues(30, 12)
        layout = compute_layout(clues, clues, page_spec=spec)
        assert book_cell_mm(spec, clues, clues) == layout.page.cell_mm
        assert book_cell_mm(spec, clues, clues) == pytest.approx(4.61, abs=0.005)
        assert _px_to_mm(layout.cell) == pytest.approx(4.57, abs=0.01)

    def test_calls_compute_layout_with_the_spec(self, monkeypatch) -> None:
        import nonogram.admin.book_page_spec as module

        seen = []
        real = module.compute_layout

        def spy(row_clues, column_clues, page_spec=None):
            seen.append(page_spec)
            return real(row_clues, column_clues, page_spec=page_spec)

        monkeypatch.setattr(module, "compute_layout", spy)
        spec = book_page_spec(_book(**CON018_COLUMNS), 2)
        book_cell_mm(spec, _clues(15, 3), _clues(15, 3))
        assert seen == [spec]

    def test_a_spec_without_parity_has_no_book_cell(self) -> None:
        with pytest.raises(ValueError, match="parity"):
            book_cell_mm(DEFAULT_PAGE_SPEC, _clues(10, 1), _clues(10, 1))


# --------------------------------------------------------------------------
# Migration 011
# --------------------------------------------------------------------------


def _alembic(database_url, monkeypatch):
    from alembic import command
    from alembic.config import Config

    root = Path(__file__).resolve().parent.parent
    # No ini file: fileConfig would disable loggers later tests assert on.
    config = Config()
    config.set_main_option("script_location", str(root / "migrations"))
    monkeypatch.setenv("DATABASE_URL", database_url)
    return command, config


class TestMigration011:
    def test_chain_and_revision(self) -> None:
        import importlib.util

        path = Path(__file__).resolve().parent.parent / "migrations" / "versions" / "011_book_margin_defaults.py"
        spec = importlib.util.spec_from_file_location("migration_011", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert (module.revision, module.down_revision) == ("011", "010")

    def test_defaults_only_no_backfill_and_downgrade(self, tmp_path, monkeypatch) -> None:
        import sqlalchemy as sa

        url = f"sqlite:///{tmp_path / 'migrate.db'}"
        command, config = _alembic(url, monkeypatch)
        command.upgrade(config, "010")
        engine = sa.create_engine(url)

        def insert(title):
            with engine.begin() as conn:
                conn.execute(
                    sa.text(
                        "INSERT INTO books (id, title, puzzle_ids, puzzle_titles, book_metadata, status)"
                        " VALUES (:id, :title, '[]', '{}', '{}', 'draft')"
                    ),
                    {"id": uuid.uuid4().hex, "title": title},
                )

        def margins():
            with engine.connect() as conn:
                return dict(
                    (title, (gutter, outside))
                    for title, gutter, outside in conn.execute(
                        sa.text("SELECT title, gutter_margin_cm, outside_margin_cm FROM books")
                    )
                )

        insert("Legacy")
        command.upgrade(config, "011")
        assert margins() == {"Legacy": (None, None)}  # no backfill
        insert("New")
        assert margins() == {"Legacy": (None, None), "New": ("1.27", "0.95")}

        # The legacy row still builds the CON-018 sheet through the fallback.
        from contextlib import contextmanager

        from sqlalchemy.orm import sessionmaker

        factory = sessionmaker(bind=engine)

        @contextmanager
        def migrated_scope():
            db = factory()
            try:
                yield db
                db.commit()
            finally:
                db.close()

        books = BookManager(session_factory=migrated_scope)
        for book in books.get_all_books():
            assert book_page_spec(book) == CON018_ODD

        command.downgrade(config, "010")
        insert("After downgrade")
        assert margins() == {
            "Legacy": (None, None),
            "New": ("1.27", "0.95"),
            "After downgrade": (None, None),
        }
        command.upgrade(config, "011")  # up -> down -> up
        assert margins()["New"] == ("1.27", "0.95")
        engine.dispose()
