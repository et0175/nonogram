"""CARD-136 — Print setup stores the chosen trim on the book (FR-030, CON-018).

    TestBookTrim_SetupPrintStoresAndExportFollows  the trim chosen on Print
            setup is stored on the book, shows on Print setup and on Finalise
            when the book is reopened, and is the trim the export prints at
    TestBookTrim_RefusedPlanStoresNothing  AC-197's rule reaching the trim: a
            submission whose plan is refused saves neither the plan nor the trim
    TestSetPrintSpec_WritesOnlyTheTrim  G-4 (INV-008) — the writer touches the
            two trim columns and ``updated_at``, and nothing else of the book
    TestBookTrim_ProfileAndLegacyBooks  G-1 and G-2 — a book created and never
            edited keeps the Book 1 profile, and a legacy book with empty
            columns still falls back to it

Until this card Print setup validated the owner's trim and then threw it away
(it wrote ``book.metadata.size``, a display string, which in DB mode lived on
a detached snapshot), so a book whose trim the owner changed still printed on
the Book 1 profile and the Finalise summary reported "8x10 × 27.94 cm".

Every storage-level test runs in **both** storage modes: in memory, and DB
mode against a real SQLite file (no mocks), read back through fresh sessions.
The user-facing halves are driven through the Flask test client against the
real routes, in both modes too — the reading ``tests/test_book_plan_storage.py``
makes, whose app/plan-form helpers are reused here rather than restated.

The figures are 6 x 9 inches worked out here — 15.24 x 22.86 cm, and
1800 x 2700 px at 300 DPI — never read back from the code under test.
"""

from __future__ import annotations

import re
import uuid

import pytest

from nonogram import clues
from nonogram.admin.book_page_spec import BOOK1_PROFILE
from nonogram.admin.book_plan import DEFAULT_PLAN, Split, prefill
from nonogram.admin.print_specs import PrintSpec
from tests.helpers.db import make_batch, make_book, sqlite_session_scope
from tests.helpers.pdf_pages import pdf_pages
from tests.test_book_plan_storage import (
    AC198_MATRIX,
    MODES,
    _build_app,
    _form,
    _input_value,
    _new_book,
    _page,
)

#: 6 x 9 inches: what the owner types on Print setup, and the centimetres the
#: two trim columns must hold afterwards (1 in = 2.54 cm, to two decimals).
SIX_BY_NINE_IN = ("6", "9")
SIX_BY_NINE_CM = ("15.24", "22.86")

#: The same trim as a page raster at 300 DPI: 6 x 300 by 9 x 300.
SIX_BY_NINE_PX = (1800, 2700)

#: The Book 1 profile's trim, as CON-018 states it and the column stores it.
BOOK1_CM = ("21.59", "27.94")


@pytest.fixture
def scope(tmp_path):
    return sqlite_session_scope(tmp_path, "trim.db")


@pytest.fixture(params=MODES)
def mode(request):
    return request.param


@pytest.fixture
def app(mode, scope, monkeypatch):
    return _build_app(mode, scope, monkeypatch)


# --------------------------------------------------------------------------
# driving the two screens
# --------------------------------------------------------------------------


def _set_trim(client, book_id, width, height, *, unit="cm", plan=True):
    """Save the trim on Print setup, exactly as the step's form submits it."""
    if plan:
        data = _form(150, (40, 40, 20), AC198_MATRIX, width=width, height=height)
    else:
        data = {"width": width, "height": height}
    data["unit"] = unit
    return client.post(f"/book/{book_id}/setup-print", data=data)


def _shown_trim(html: str) -> tuple[str, str]:
    """The trim Print setup shows in its two fields."""
    return _input_value(html, "width"), _input_value(html, "height")


def _finalize_html(client, book_id) -> str:
    response = client.get(f"/book/{book_id}/finalize")
    assert response.status_code == 200
    return response.get_data(as_text=True)


def _finalize_trim(html: str) -> tuple[str, str] | None:
    """The trim the Finalise summary reports, read off the rendered row."""
    match = re.search(
        r'data-trim-width-cm="([^"]+)" data-trim-height-cm="([^"]+)"', html
    )
    return None if match is None else (match.group(1), match.group(2))


def _stored_columns(books, book_id) -> tuple[str, str]:
    book = books.get_book(book_id)
    return book.trim_width_cm, book.trim_height_cm


def _comfortable_puzzle(app, scope, mode) -> str:
    """One small puzzle that clears the 4.8 mm floor on any supported trim."""
    grid = [[2 <= x < 8 and 2 <= y < 7 for x in range(10)] for y in range(10)]
    found = clues.compute_clues(grid)
    batch_id = None if mode == "memory" else make_batch(scope, source="random", total_count=1)
    return app.puzzle_review_service.add_puzzle(
        grid=grid,
        clues_rows=[list(line) for line in found.rows],
        clues_cols=[list(line) for line in found.columns],
        width=10,
        height=10,
        theme="generic",
        difficulty_score=10,
        difficulty_tier="easy",
        quality_score=50,
        recognizability="medium",
        strategies_used=[],
        batch_id=batch_id,
        source_image="comfortable.png",
    )


# --------------------------------------------------------------------------
# The trim chosen on Print setup is stored, read back, and printed
# --------------------------------------------------------------------------


class TestBookTrim_SetupPrintStoresAndExportFollows:
    """Setting the trim on Print setup and reopening the book shows the stored
    trim on both Print setup and Finalise, and the export uses it."""

    def test_the_two_trim_columns_carry_the_chosen_trim(self, app) -> None:
        client = app.test_client()
        book_id = _new_book(app.book_manager)
        assert _stored_columns(app.book_manager, book_id) == BOOK1_CM

        response = _set_trim(client, book_id, *SIX_BY_NINE_IN, unit="inches")

        assert response.status_code == 302
        assert "/select-puzzles" in response.headers["Location"]
        assert _stored_columns(app.book_manager, book_id) == SIX_BY_NINE_CM

    def test_reopening_print_setup_shows_the_stored_trim(
        self, mode, scope, monkeypatch
    ) -> None:
        app = _build_app(mode, scope, monkeypatch)
        book_id = _new_book(app.book_manager)

        assert _set_trim(app.test_client(), book_id, *SIX_BY_NINE_CM).status_code == 302

        # Leave the workflow: a new client (no session), and in DB mode a new
        # app too, so nothing but the stored row can carry the trim back.
        if mode == "db":
            app = _build_app(mode, scope, monkeypatch)
        assert _shown_trim(_page(app.test_client(), book_id)) == SIX_BY_NINE_CM

    def test_the_finalise_summary_reports_the_same_trim(
        self, mode, scope, monkeypatch
    ) -> None:
        """The defect this card closes: the row read ``metadata.size``."""
        app = _build_app(mode, scope, monkeypatch)
        client = app.test_client()
        book_id = _new_book(app.book_manager)
        assert _finalize_trim(_finalize_html(client, book_id)) == BOOK1_CM

        assert _set_trim(client, book_id, *SIX_BY_NINE_CM).status_code == 302

        if mode == "db":
            app = _build_app(mode, scope, monkeypatch)
        html = _finalize_html(app.test_client(), book_id)
        assert _finalize_trim(html) == SIX_BY_NINE_CM
        width, height = SIX_BY_NINE_CM
        assert f"{width} × {height} cm" in html
        # The old row's shape, and the nonsense it rendered, are both gone.
        assert "8x10" not in html

    def test_the_exported_interior_is_printed_at_the_stored_trim(
        self, mode, scope, monkeypatch
    ) -> None:
        """End to end: the trim typed on Print setup is the page a printer gets."""
        app = _build_app(mode, scope, monkeypatch)
        client = app.test_client()
        book_id = _new_book(app.book_manager)
        app.book_manager.add_puzzles_to_book(
            book_id, [_comfortable_puzzle(app, scope, mode)]
        )

        assert _set_trim(client, book_id, *SIX_BY_NINE_IN, unit="inches").status_code == 302

        response = client.post(
            f"/book/{book_id}/finalize", data={"action": "download_pdf", "part": "interior"}
        )
        assert response.status_code == 200
        assert response.mimetype == "application/pdf"
        pages = pdf_pages(response.get_data())
        assert pages, "the interior PDF has no pages"
        assert {page.size for page in pages} == {SIX_BY_NINE_PX}
        # Not the Book 1 page it printed before the columns were written.
        assert (2550, 3300) not in {page.size for page in pages}

    def test_the_trim_survives_a_later_plan_only_save(self, app) -> None:
        """A second visit that changes the plan must not lose the trim."""
        client = app.test_client()
        book_id = _new_book(app.book_manager)
        assert _set_trim(client, book_id, *SIX_BY_NINE_CM).status_code == 302

        response = client.post(
            f"/book/{book_id}/setup-print",
            data=_form(120, (30, 45, 25), AC198_MATRIX, width=SIX_BY_NINE_CM[0],
                       height=SIX_BY_NINE_CM[1]),
        )

        assert response.status_code == 302
        assert _stored_columns(app.book_manager, book_id) == SIX_BY_NINE_CM
        assert app.book_manager.get_plan(book_id) == prefill(120, Split(30, 45, 25))

    def test_a_trim_only_form_stores_the_trim_too(self, app) -> None:
        """The form without the plan fields saves the trim, as it always did."""
        client = app.test_client()
        book_id = _new_book(app.book_manager)

        response = _set_trim(client, book_id, *SIX_BY_NINE_CM, plan=False)

        assert response.status_code == 302
        assert _stored_columns(app.book_manager, book_id) == SIX_BY_NINE_CM
        assert app.book_manager.get_plan(book_id) == DEFAULT_PLAN

    def test_the_three_screens_report_one_trim(
        self, mode, scope, monkeypatch
    ) -> None:
        """Print setup, Finalise and the exported page agree, whatever the trim."""
        app = _build_app(mode, scope, monkeypatch)
        client = app.test_client()
        book_id = _new_book(app.book_manager)

        for width, height, pixels in (
            ("15.24", "22.86", (1800, 2700)),
            ("20.32", "25.40", (2400, 3000)),
            ("21.59", "27.94", (2550, 3300)),
        ):
            assert _set_trim(client, book_id, width, height).status_code == 302

            assert _shown_trim(_page(client, book_id)) == (width, height)
            assert _finalize_trim(_finalize_html(client, book_id)) == (width, height)
            book = app.book_manager.get_book(book_id)
            from nonogram.admin.book_pdf_generator import BookPDFGenerator

            assert BookPDFGenerator(book).create_cover_page("Winter").size == pixels


# --------------------------------------------------------------------------
# A refused plan stores nothing — the trim included (AC-197)
# --------------------------------------------------------------------------


class TestBookTrim_RefusedPlanStoresNothing:
    """A submission the plan refuses saves neither the plan nor the trim."""

    def test_a_split_not_summing_to_100_leaves_both_columns_alone(self, app) -> None:
        client = app.test_client()
        book_id = _new_book(app.book_manager)
        before = app.book_manager.get_book(book_id)

        response = client.post(
            f"/book/{book_id}/setup-print",
            data=_form(150, (40, 40, 30), AC198_MATRIX,
                       width=SIX_BY_NINE_CM[0], height=SIX_BY_NINE_CM[1]),
        )

        assert response.status_code == 200  # re-rendered, not redirected on
        assert "Plan not saved" in response.get_data(as_text=True)
        assert _stored_columns(app.book_manager, book_id) == BOOK1_CM
        assert app.book_manager.get_plan(book_id) == DEFAULT_PLAN
        assert app.book_manager.get_book(book_id).updated_at == before.updated_at

    @pytest.mark.parametrize(
        "field, value",
        [("split_easy", "39"), ("split_easy", "forty"), ("plan_count", "0"),
         ("cell_2_hard", "-1"), ("cell_0_easy", "2.5")],
    )
    def test_every_value_inv005_refuses_leaves_the_trim_alone(
        self, app, field, value
    ) -> None:
        client = app.test_client()
        book_id = _new_book(app.book_manager)
        form = _form(150, (40, 40, 20), AC198_MATRIX,
                     width=SIX_BY_NINE_CM[0], height=SIX_BY_NINE_CM[1])
        form[field] = value

        response = client.post(f"/book/{book_id}/setup-print", data=form)

        assert response.status_code == 200
        assert _stored_columns(app.book_manager, book_id) == BOOK1_CM
        assert app.book_manager.get_plan(book_id) == DEFAULT_PLAN

    def test_the_refused_trim_never_reaches_the_finalise_summary(self, app) -> None:
        client = app.test_client()
        book_id = _new_book(app.book_manager)

        client.post(
            f"/book/{book_id}/setup-print",
            data=_form(150, (40, 40, 30), AC198_MATRIX,
                       width=SIX_BY_NINE_CM[0], height=SIX_BY_NINE_CM[1]),
        )

        assert _finalize_trim(_finalize_html(client, book_id)) == BOOK1_CM

    def test_a_refused_trim_stores_neither_half_either(self, app) -> None:
        """The other direction: an out-of-range trim leaves the plan alone."""
        client = app.test_client()
        book_id = _new_book(app.book_manager)

        response = client.post(
            f"/book/{book_id}/setup-print",
            data=_form(120, (30, 45, 25), AC198_MATRIX, width="5", height="9"),
        )

        assert response.status_code == 200
        assert _stored_columns(app.book_manager, book_id) == BOOK1_CM
        assert app.book_manager.get_plan(book_id) == DEFAULT_PLAN


# --------------------------------------------------------------------------
# G-4 (INV-008) — the writer writes the trim and nothing else
# --------------------------------------------------------------------------


def _manager(mode, scope):
    from nonogram.admin.book_manager import BookManager
    from nonogram.admin.puzzle_review import PuzzleReviewService

    if mode == "memory":
        return BookManager(session_factory=None)
    return BookManager(
        session_factory=scope, puzzle_store=PuzzleReviewService(session_factory=scope)
    )


def _puzzle_ids(books, mode, scope, count=3):
    if mode == "memory":
        return [str(uuid.uuid4()) for _ in range(count)]
    batch_id = make_batch(scope, source="random", total_count=count)
    grid = [[2 <= x < 8 and 2 <= y < 7 for x in range(10)] for y in range(10)]
    found = clues.compute_clues(grid)
    return [
        books.puzzle_store.add_puzzle(
            grid=grid,
            clues_rows=[list(line) for line in found.rows],
            clues_cols=[list(line) for line in found.columns],
            width=10,
            height=10,
            theme="generic",
            difficulty_score=10,
            difficulty_tier="easy",
            quality_score=50,
            recognizability="medium",
            strategies_used=[],
            batch_id=batch_id,
            source_image=f"g4-{n}.png",
        )
        for n in range(count)
    ]


class TestSetPrintSpec_WritesOnlyTheTrim:
    """Membership, order, titles, status, margins and the plan are untouched."""

    @pytest.mark.parametrize("mode", MODES)
    def test_nothing_but_the_trim_columns_moves(self, mode, scope) -> None:
        books = _manager(mode, scope)
        book_id = books.create_book("Winter", "Twenty winter pictures.", "generic", "adults")
        ids = _puzzle_ids(books, mode, scope)
        books.add_puzzles_to_book(book_id, ids)
        books.reorder_puzzles(book_id, [ids[2], ids[0], ids[1]])
        books.set_puzzle_title(book_id, ids[0], "First light")
        before = books.get_book(book_id)
        before_ids, before_titles = list(before.puzzle_ids), dict(before.puzzle_titles)

        assert books.set_print_spec(book_id, PrintSpec(*SIX_BY_NINE_CM)) is True

        after = books.get_book(book_id)
        assert (after.trim_width_cm, after.trim_height_cm) == SIX_BY_NINE_CM
        assert after.puzzle_ids == before_ids == [ids[2], ids[0], ids[1]]
        assert after.puzzle_titles == before_titles == {ids[0]: "First light"}
        assert after.status == before.status == "draft"
        assert books.get_plan(book_id) == DEFAULT_PLAN
        assert after.floor_overrides == before.floor_overrides
        assert after.updated_at >= before.updated_at

    @pytest.mark.parametrize("mode", MODES)
    def test_the_margins_are_not_the_writers_to_touch(self, mode, scope) -> None:
        """Print setup offers no margin field, so CON-018's margins stay put (G-1)."""
        books = _manager(mode, scope)
        book_id = books.create_book("Winter", "A book.", "generic", "adults")

        books.set_print_spec(
            book_id,
            PrintSpec(*SIX_BY_NINE_CM, gutter_margin_cm="2.50", outside_margin_cm="2.50"),
        )

        book = books.get_book(book_id)
        assert book.gutter_margin_cm == BOOK1_PROFILE.gutter_margin_cm
        assert book.outside_margin_cm == BOOK1_PROFILE.outside_margin_cm
        assert book.outside_margin_bleed_cm is None

    @pytest.mark.parametrize("mode", MODES)
    def test_an_unknown_book_is_reported_rather_than_created(self, mode, scope) -> None:
        books = _manager(mode, scope)
        missing = str(uuid.uuid4()) if books._session_factory else "book_999999"

        assert books.set_print_spec(missing, PrintSpec(*SIX_BY_NINE_CM)) is False
        assert books.get_book(missing) is None

    @pytest.mark.parametrize("mode", MODES)
    def test_it_accepts_nothing_but_a_validated_spec(self, mode, scope) -> None:
        """The posture ``save_plan`` takes: only the value object storage accepts."""
        books = _manager(mode, scope)
        book_id = books.create_book("Winter", "A book.", "generic", "adults")

        with pytest.raises(ValueError):
            books.set_print_spec(book_id, {"trim_width_cm": "15.24", "trim_height_cm": "22.86"})

        assert _stored_columns(books, book_id) == BOOK1_CM


# --------------------------------------------------------------------------
# G-1 and G-2 — the profile a book starts on, and the legacy fallback
# --------------------------------------------------------------------------


class TestBookTrim_ProfileAndLegacyBooks:
    @pytest.mark.parametrize("mode", MODES)
    def test_a_book_created_and_never_edited_keeps_the_profile(self, mode, scope) -> None:
        """G-1 — create_book's CON-018 defaults are unchanged by this card."""
        books = _manager(mode, scope)
        book_id = books.create_book("Winter", "A book.", "generic", "adults")

        book = books.get_book(book_id)

        assert (book.trim_width_cm, book.trim_height_cm) == BOOK1_CM
        assert book.gutter_margin_cm == BOOK1_PROFILE.gutter_margin_cm
        assert book.outside_margin_cm == BOOK1_PROFILE.outside_margin_cm

    def test_a_legacy_book_with_empty_columns_shows_the_profile(
        self, scope, monkeypatch
    ) -> None:
        """G-2 — the fallback for a pre-print-columns row is untouched.

        A row from before migration 004, whose print columns were never
        written and are NULL (the column default the ORM applies is emptied
        here, which is the state a pre-migration row is actually in). Both
        screens must report the profile it will really print on, rather than
        an empty size or the row's ``metadata.size``.
        """
        from nonogram.db.models import Book as DBBook

        app = _build_app("db", scope, monkeypatch)
        book_id = make_book(scope, title="Legacy")
        with scope() as db:
            row = db.query(DBBook).filter(DBBook.id == uuid.UUID(book_id)).one()
            row.trim_width_cm = row.trim_height_cm = None
            row.gutter_margin_cm = row.outside_margin_cm = None
        client = app.test_client()
        assert _stored_columns(app.book_manager, book_id) == (None, None)

        assert _shown_trim(_page(client, book_id)) == BOOK1_CM
        assert _finalize_trim(_finalize_html(client, book_id)) == BOOK1_CM

    def test_a_trim_that_cannot_be_read_is_said_rather_than_shown(
        self, scope, monkeypatch
    ) -> None:
        """A stored column no sheet can be built from has no size to report."""
        from nonogram.db.models import Book as DBBook

        app = _build_app("db", scope, monkeypatch)
        book_id = _new_book(app.book_manager)
        with scope() as db:
            row = db.query(DBBook).filter(DBBook.id == uuid.UUID(book_id)).one()
            row.trim_width_cm = "not a number"

        html = _finalize_html(app.test_client(), book_id)

        assert _finalize_trim(html) is None
        assert "Cannot be read" in html
        # And Print setup still opens, carrying the stored value to correct.
        assert _shown_trim(_page(app.test_client(), book_id))[0] == "not a number"
