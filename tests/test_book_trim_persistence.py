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
    TestBookTrim_ReopeningInInchesDoesNotShiftIt  review cycle 1 (F-002) — a
            trim field submitted exactly as the page rendered it stores the
            centimetres already there, so reopening in inches cannot move it
    TestBookTrim_ThePageCarriesOneUnit  review cycle 1 (F-003) — a stored
            column with no inch form puts the whole page back in centimetres,
            rather than one field in each unit under one label
    TestBookTrim_AWriteThatStoredNothingIsReported  review cycle 1 (F-004) — a
            book removed mid-submission is reported, not flashed as saved
    TestBookTrim_ABlankTrimFieldStoresNothing  review cycle 2 (F-101) — an
            empty, whitespace-only or absent trim field is a refused
            submission in both units, not a request for the Book 1 profile

Until this card Print setup validated the owner's trim and then threw it away
(it wrote ``book.metadata.size``, a display string, which in DB mode lived on
a detached snapshot), so a book whose trim the owner changed still printed on
the Book 1 profile and the Finalise summary reported "8x10 × 27.94 cm".

Every storage-level test runs in **both** storage modes: in memory, and DB
mode against a real SQLite file (no mocks), read back through fresh sessions.
The user-facing halves are driven through the Flask test client against the
real routes, in both modes too — the reading ``tests/test_book_plan_storage.py``
makes, whose app/plan-form helpers are reused here rather than restated. That
claim is checked, not decorative: review cycle 1 (F-006) found the two legacy
classes hard-coding DB mode, and (F-005) three G-4 assertions comparing a
memory-mode ``Book`` with itself, because ``get_book`` hands back the live
object there. Whatever a test compares across a write is copied out first.

The figures are 6 x 9 inches worked out here — 15.24 x 22.86 cm, and
1800 x 2700 px at 300 DPI — never read back from the code under test.
"""

from __future__ import annotations

import contextlib
import re
import uuid

import pytest
from flask import message_flashed

from nonogram import clues
from nonogram.admin.book_page_spec import BOOK1_PROFILE, book_page_spec
from nonogram.admin.book_plan import DEFAULT_PLAN, Split, prefill
from nonogram.admin.print_specs import PrintSpec
from tests.helpers.db import make_batch, sqlite_session_scope
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
        # Copied out, not held on the Book: in memory mode ``get_book`` hands
        # back the live object and the comparison would be with itself (F-005).
        before_updated_at = app.book_manager.get_book(book_id).updated_at

        response = client.post(
            f"/book/{book_id}/setup-print",
            data=_form(150, (40, 40, 30), AC198_MATRIX,
                       width=SIX_BY_NINE_CM[0], height=SIX_BY_NINE_CM[1]),
        )

        assert response.status_code == 200  # re-rendered, not redirected on
        assert "Plan not saved" in response.get_data(as_text=True)
        assert _stored_columns(app.book_manager, book_id) == BOOK1_CM
        assert app.book_manager.get_plan(book_id) == DEFAULT_PLAN
        assert app.book_manager.get_book(book_id).updated_at == before_updated_at

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
        # Snapshots, not the Book: in memory mode ``get_book`` hands back the
        # live object, so ``after.status == before.status`` would compare a
        # field with itself and pass however the writer behaved (review cycle
        # 1, F-005). Every compared field is copied out before the write.
        before_ids, before_titles = list(before.puzzle_ids), dict(before.puzzle_titles)
        before_status = before.status
        before_overrides = list(before.floor_overrides)
        before_updated_at = before.updated_at

        assert books.set_print_spec(book_id, PrintSpec(*SIX_BY_NINE_CM)) is True

        after = books.get_book(book_id)
        assert (after.trim_width_cm, after.trim_height_cm) == SIX_BY_NINE_CM
        assert after.puzzle_ids == before_ids == [ids[2], ids[0], ids[1]]
        assert after.puzzle_titles == before_titles == {ids[0]: "First light"}
        assert after.status == before_status == "draft"
        assert books.get_plan(book_id) == DEFAULT_PLAN
        assert list(after.floor_overrides) == before_overrides
        assert after.updated_at >= before_updated_at

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
    @pytest.mark.parametrize(
        "refused",
        [
            pytest.param({"trim_width_cm": "15.24", "trim_height_cm": "22.86"}, id="a-dict"),
            pytest.param(PrintSpec("999", "abc"), id="out-of-bounds-and-not-a-number"),
            pytest.param(PrintSpec(None, None), id="both-columns-none"),
            pytest.param(PrintSpec("15.24", None), id="one-column-none"),
            pytest.param(PrintSpec("5", "9"), id="below-KDPs-minimum"),
            pytest.param(PrintSpec("15.24", "99"), id="above-KDPs-maximum-height"),
            pytest.param(PrintSpec("31", "22.86"), id="above-KDPs-maximum-width"),
            pytest.param(PrintSpec("nan", "22.86"), id="not-a-finite-number"),
            pytest.param(PrintSpec("inf", "22.86"), id="infinite"),
        ],
    )
    def test_it_accepts_nothing_but_a_validated_spec(self, mode, scope, refused) -> None:
        """Only a trim the reader can read back reaches the columns (F-001).

        ``PrintSpec`` is a plain mutable dataclass with no validating
        construction, so — unlike the frozen ``DistributionPlan`` ``save_plan``
        is handed — its *type* is no proof that
        ``PrintSpecValidator.create_spec`` ever saw the value: every spec below
        is as constructible as a real one. Before this fix each of them was
        stored and returned ``True``, after which ``book_page_spec`` on the
        same book raised ``ValueError`` — the state the docstring said could
        not occur. The invariant is the reader's own: what is stored is a pair
        of finite centimetre numbers inside KDP's bounds.
        """
        books = _manager(mode, scope)
        book_id = books.create_book("Winter", "A book.", "generic", "adults")

        with pytest.raises(ValueError):
            books.set_print_spec(book_id, refused)

        assert _stored_columns(books, book_id) == BOOK1_CM
        # And the reader that pays for a bad write still has a sheet to build.
        assert book_page_spec(books.get_book(book_id)).width_mm == pytest.approx(215.9)


# --------------------------------------------------------------------------
# G-1 and G-2 — the profile a book starts on, and the legacy fallback
# --------------------------------------------------------------------------


def _stored_book(books, scope, mode, book_id):
    """A context manager over the book *as stored*, writable in either mode.

    The point of the two tests below is a column in a state no writer puts it
    in — a pre-migration NULL, or a value that is not a number — so they reach
    past the writers to the store itself: the live :class:`Book` in memory
    mode, the ``books`` row in DB mode.
    """
    import contextlib

    @contextlib.contextmanager
    def _memory():
        yield books.books[book_id]

    @contextlib.contextmanager
    def _row():
        from nonogram.db.models import Book as DBBook

        with scope() as db:
            yield db.query(DBBook).filter(DBBook.id == uuid.UUID(book_id)).one()

    return _memory() if mode == "memory" else _row()


def _empty_the_print_columns(books, scope, mode, book_id) -> None:
    """The state a row written before migration 004 is actually in."""
    with _stored_book(books, scope, mode, book_id) as stored:
        stored.trim_width_cm = stored.trim_height_cm = None
        stored.gutter_margin_cm = stored.outside_margin_cm = None


def _damage_the_stored_width(books, scope, mode, book_id, value) -> None:
    """A stored trim width no sheet can be built from."""
    with _stored_book(books, scope, mode, book_id) as stored:
        stored.trim_width_cm = value


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
        self, mode, app, scope
    ) -> None:
        """G-2 — the fallback for a pre-print-columns row is untouched.

        A book from before migration 004, whose print columns were never
        written and are empty (the column default the ORM applies is emptied
        here, which is the state a pre-migration row is actually in). Both
        screens must report the profile it will really print on, rather than
        an empty size or the row's ``metadata.size``.

        Both storage modes: the reading branch is ``book.trim_width_cm or
        DEFAULT`` in the route, which memory mode reaches just as DB mode does
        (review cycle 1, F-006).
        """
        book_id = _new_book(app.book_manager)
        _empty_the_print_columns(app.book_manager, scope, mode, book_id)
        client = app.test_client()
        assert _stored_columns(app.book_manager, book_id) == (None, None)

        assert _shown_trim(_page(client, book_id)) == BOOK1_CM
        assert _finalize_trim(_finalize_html(client, book_id)) == BOOK1_CM

    def test_a_trim_that_cannot_be_read_is_said_rather_than_shown(
        self, mode, app, scope
    ) -> None:
        """A stored column no sheet can be built from has no size to report.

        Both storage modes: ``_trim_cm``'s ``ValueError`` branch is the route's,
        not the database's (F-006).
        """
        book_id = _new_book(app.book_manager)
        _damage_the_stored_width(app.book_manager, scope, mode, book_id, "not a number")

        html = _finalize_html(app.test_client(), book_id)

        assert _finalize_trim(html) is None
        assert "Cannot be read" in html
        # And Print setup still opens, carrying the stored value to correct.
        assert _shown_trim(_page(app.test_client(), book_id))[0] == "not a number"


# --------------------------------------------------------------------------
# Review cycle 1 — the two screens' own arithmetic
# --------------------------------------------------------------------------


def _prefer(client, unit: str) -> None:
    """The session's remembered measurement unit, without a submission."""
    with client.session_transaction() as sess:
        sess["unit_preference"] = unit


def _shown_unit(html: str) -> str:
    """The unit the whole page is in: whichever unit radio is checked."""
    checked = [
        unit
        for unit in ("cm", "inches")
        if "checked"
        in re.search(r'<input\b[^>]*\bid="unit_' + unit + r'"[^>]*>', html, re.S).group(0)
    ]
    assert len(checked) == 1, f"the unit radio is not in exactly one state: {checked}"
    return checked[0]


def _unit_suffixes(html: str) -> tuple[str, str]:
    """The unit printed beside each of the two trim fields."""
    return tuple(  # type: ignore[return-value]
        re.search(r'id="' + field + r'_unit">([^<]*)<', html).group(1)
        for field in ("width", "height")
    )


class TestBookTrim_ReopeningInInchesDoesNotShiftIt:
    """Review cycle 1, F-002 — an untouched field stores what was already there.

    Print setup prefills from the stored centimetres and converts to inches at
    two decimals; the submission converts back at two decimals. The two
    roundings do not cancel, so before this fix reopening a 15.00 x 20.00 cm
    book in inches and pressing Save without touching anything stored
    15.01 x 19.99 — silently moving the trim the page size and every cell
    measurement are derived from, for a book KDP wants an exact trim for.
    """

    STORED_CM = ("15.00", "20.00")
    #: 15.00 / 2.54 and 20.00 / 2.54, worked out here, to two decimals.
    STORED_IN = ("5.91", "7.87")

    def test_saving_an_untouched_inches_form_leaves_the_trim_exactly(self, app) -> None:
        client = app.test_client()
        book_id = _new_book(app.book_manager)
        assert _set_trim(client, book_id, *self.STORED_CM).status_code == 302
        assert _stored_columns(app.book_manager, book_id) == self.STORED_CM

        _prefer(client, "inches")
        shown = _shown_trim(_page(client, book_id))
        assert shown == self.STORED_IN

        assert _set_trim(client, book_id, *shown, unit="inches").status_code == 302

        # Not ("15.01", "19.99"), which converting 5.91 / 7.87 back gives.
        assert _stored_columns(app.book_manager, book_id) == self.STORED_CM

    def test_reopening_in_inches_is_stable_however_often_it_is_saved(self, app) -> None:
        """The drift was 0.1 mm a time; nothing may accumulate."""
        client = app.test_client()
        book_id = _new_book(app.book_manager)
        assert _set_trim(client, book_id, *self.STORED_CM).status_code == 302
        _prefer(client, "inches")

        for _ in range(5):
            shown = _shown_trim(_page(client, book_id))
            assert shown == self.STORED_IN
            assert _set_trim(client, book_id, *shown, unit="inches").status_code == 302

        assert _stored_columns(app.book_manager, book_id) == self.STORED_CM

    def test_a_field_the_owner_really_edited_is_still_converted(self, app) -> None:
        """The discriminator is "the page's own string came back", not a window."""
        client = app.test_client()
        book_id = _new_book(app.book_manager)
        assert _set_trim(client, book_id, *self.STORED_CM).status_code == 302
        _prefer(client, "inches")

        assert _set_trim(client, book_id, *SIX_BY_NINE_IN, unit="inches").status_code == 302

        assert _stored_columns(app.book_manager, book_id) == SIX_BY_NINE_CM

    def test_one_edited_field_converts_while_the_other_is_kept(self, app) -> None:
        client = app.test_client()
        book_id = _new_book(app.book_manager)
        assert _set_trim(client, book_id, *self.STORED_CM).status_code == 302
        _prefer(client, "inches")

        assert _set_trim(
            client, book_id, self.STORED_IN[0], "9", unit="inches"
        ).status_code == 302

        assert _stored_columns(app.book_manager, book_id) == ("15.00", "22.86")


class TestBookTrim_ThePageCarriesOneUnit:
    """Review cycle 1, F-003 — an unreadable column never mixes the two units.

    The inches prefill converted both fields under one ``try``, so a stored
    value with no inch form left the *other* field converted while its own was
    shown as stored — two units under one inches label and one inches radio,
    which the next submission then reads as inches and stores.
    """

    def test_an_unreadable_column_shows_the_whole_page_in_cm(
        self, mode, app, scope
    ) -> None:
        client = app.test_client()
        book_id = _new_book(app.book_manager)
        assert _set_trim(client, book_id, "15.00", "20.00").status_code == 302
        _damage_the_stored_width(app.book_manager, scope, mode, book_id, "not a number")
        _prefer(client, "inches")

        html = _page(client, book_id)

        assert _shown_trim(html) == ("not a number", "20.00")
        assert _shown_unit(html) == "cm"
        assert _unit_suffixes(html) == ("cm", "cm")
        # 20.00 cm rendered as inches beside a centimetre width is the mix.
        # Over the whole page, not only the two fields: the inch form of the
        # readable column must not survive anywhere on a page in centimetres
        # (review cycle 2, F-104 — this used to read the parsed tuple, where
        # it could not fail given the assertion above).
        assert "7.87" not in html

    def test_correcting_that_page_stores_centimetres_not_inches(
        self, mode, app, scope
    ) -> None:
        """The mixed page's real cost: the correcting save is read in cm."""
        client = app.test_client()
        book_id = _new_book(app.book_manager)
        assert _set_trim(client, book_id, "15.00", "20.00").status_code == 302
        _damage_the_stored_width(app.book_manager, scope, mode, book_id, "not a number")
        _prefer(client, "inches")
        html = _page(client, book_id)

        # Exactly what the rendered form submits: its own unit and its own
        # height, with the width the owner typed over the unreadable one.
        assert _set_trim(
            client, book_id, "15.24", _shown_trim(html)[1], unit=_shown_unit(html)
        ).status_code == 302

        # Not ("38.70", "50.80") — 15.24 and 20.00 read as inches.
        assert _stored_columns(app.book_manager, book_id) == ("15.24", "20.00")

    def test_two_readable_columns_still_open_in_inches(self, app) -> None:
        """The inches preference itself is untouched (G-0 for this fix)."""
        client = app.test_client()
        book_id = _new_book(app.book_manager)
        assert _set_trim(client, book_id, *SIX_BY_NINE_CM).status_code == 302
        _prefer(client, "inches")

        html = _page(client, book_id)

        assert _shown_trim(html) == ("6.00", "9.00")
        assert _shown_unit(html) == "inches"
        assert _unit_suffixes(html) == ("in", "in")


def _delete_the_book(books, scope, mode, book_id) -> None:
    """Remove the book from storage the way a concurrent deletion would."""
    if mode == "memory":
        books.books.pop(book_id, None)
        books._plans.pop(book_id, None)
        return
    from nonogram.db.models import Book as DBBook

    with scope() as db:
        db.query(DBBook).filter(DBBook.id == uuid.UUID(book_id)).delete()


class TestBookTrim_AWriteThatStoredNothingIsReported:
    """Review cycle 1, F-004 — a writer's ``False`` is not a saved submission.

    Both writers answer ``False`` for "no such book", and the route ignored
    both: a book removed between the read at the top of the route and the
    writes was still flashed "Print specs set: W x H cm" and redirected on to
    puzzle selection, as if the trim had been stored.

    The book is really removed from the store here, from inside the writer
    call the route makes, so the route travels its own path — this is the
    race, not a stubbed return value.
    """

    @pytest.mark.parametrize("writer", ["save_plan", "set_print_spec"])
    def test_a_book_that_went_away_is_reported_not_flashed_as_saved(
        self, mode, app, scope, monkeypatch, writer
    ) -> None:
        client = app.test_client()
        book_id = _new_book(app.book_manager)
        original = getattr(app.book_manager, writer)

        def vanish(*args, **kwargs):
            _delete_the_book(app.book_manager, scope, mode, book_id)
            return original(*args, **kwargs)

        monkeypatch.setattr(app.book_manager, writer, vanish)

        response = client.post(
            f"/book/{book_id}/setup-print",
            data=_form(120, (30, 45, 25), AC198_MATRIX,
                       width=SIX_BY_NINE_CM[0], height=SIX_BY_NINE_CM[1]),
        )

        assert response.status_code == 302
        assert response.headers["Location"].endswith("/books")
        # What this route said, exactly — not "Print specs set: 15.24 x 22.86
        # cm", which it flashed over a book that is not there.
        with client.session_transaction() as sess:
            assert [message for _category, message in sess["_flashes"]] == [
                "Book not found"
            ]
        assert app.book_manager.get_book(book_id) is None


# --------------------------------------------------------------------------
# Review cycle 2 (F-101) — a blank trim field is refused, never defaulted
# --------------------------------------------------------------------------


@contextlib.contextmanager
def _recorded_flashes(app):
    """Every message the app flashes while the block runs, in order.

    A refused submission re-renders the page, and the template consumes the
    flashes on the way out, so reading ``session["_flashes"]`` afterwards (the
    F-004 tests' reading, which works because that one redirects) would see an
    empty list whatever the route said. Flask's ``message_flashed`` signal is
    the flash itself, caught at ``flash()``: the real list, not a substring of
    the rendered page.
    """
    recorded: list[str] = []

    def record(_sender, message, category, **_extra):
        recorded.append(message)

    message_flashed.connect(record, app)
    try:
        yield recorded
    finally:
        message_flashed.disconnect(record, app)


def _blank_trim_form(*, unit, blank_field, absent, plan=True):
    """The submission the finding describes: one trim field empty or absent.

    The other field carries a perfectly good value in ``unit``'s own unit, so
    the only thing wrong with the form is the blank field.
    """
    good = {"cm": SIX_BY_NINE_CM, "inches": SIX_BY_NINE_IN}[unit]
    fields = {"width": good[0], "height": good[1]}
    if absent:
        del fields[blank_field]
    else:
        fields[blank_field] = ""

    if plan:
        # A valid plan attached: the plan half must not gate the trim half.
        data = _form(150, (40, 40, 20), AC198_MATRIX)
        data.pop("width")
        data.pop("height")
    else:
        data = {}
    data.update(fields)
    data["unit"] = unit
    return data


class TestBookTrim_ABlankTrimFieldStoresNothing:
    """Review cycle 2, F-101 — an empty or absent trim field is a refusal.

    ``create_spec`` reads a falsy width or height as "no trim was named" and
    substitutes the CON-018 Book 1 profile (that defaulting is for a
    programmatic caller and is deliberately left alone). The cm branch passed
    the raw form value straight through, so ``width=""`` — and a form with the
    key missing altogether — stored 21.59 x 27.94 cm over the trim the owner
    had chosen, redirected on to puzzle selection and flashed "Print specs
    set: 21.59 × 22.86 cm" while doing it. The storage-boundary check in
    ``set_print_spec`` cannot catch that: by the time it runs the spec is a
    valid Book 1 spec. The inches branch already refused the same submission,
    so the two branches disagreed about what an empty field means.

    The trim is set to 6 x 9 in first, so what a refusal must protect is a
    real stored value and not a default that would be indistinguishable from
    the overwrite.
    """

    @pytest.mark.parametrize("unit", ["cm", "inches"])
    @pytest.mark.parametrize("absent", [False, True], ids=["empty", "absent"])
    @pytest.mark.parametrize("blank_field", ["width", "height"])
    def test_it_is_refused_and_the_stored_trim_is_untouched(
        self, app, unit, absent, blank_field
    ) -> None:
        client = app.test_client()
        book_id = _new_book(app.book_manager)
        assert _set_trim(client, book_id, *SIX_BY_NINE_CM).status_code == 302
        assert _stored_columns(app.book_manager, book_id) == SIX_BY_NINE_CM

        with _recorded_flashes(app) as flashes:
            response = client.post(
                f"/book/{book_id}/setup-print",
                data=_blank_trim_form(unit=unit, blank_field=blank_field, absent=absent),
            )

        # The inches branch's posture, now in both: re-render, do not redirect.
        assert response.status_code == 200
        # Not "Print specs set: 21.59 × 22.86 cm", and no redirect to
        # /book/<id>/select-puzzles.
        assert flashes == [
            f"Error: Trim {blank_field} must be entered: an empty trim field is not"
            " a size, so nothing was stored and the book keeps the trim it is on."
        ]
        # Not ("21.59", "22.86") / ("21.59", "27.94") — the Book 1 profile
        # standing in for the blank field.
        assert _stored_columns(app.book_manager, book_id) == SIX_BY_NINE_CM

    @pytest.mark.parametrize("unit", ["cm", "inches"])
    def test_both_fields_blank_names_both(self, app, unit) -> None:
        client = app.test_client()
        book_id = _new_book(app.book_manager)
        assert _set_trim(client, book_id, *SIX_BY_NINE_CM).status_code == 302

        with _recorded_flashes(app) as flashes:
            response = client.post(
                f"/book/{book_id}/setup-print",
                data={"unit": unit, "width": "", "height": ""},
            )

        assert response.status_code == 200
        assert flashes == [
            "Error: Trim width and height must be entered: an empty trim field is"
            " not a size, so nothing was stored and the book keeps the trim it is on."
        ]
        assert _stored_columns(app.book_manager, book_id) == SIX_BY_NINE_CM

    @pytest.mark.parametrize("unit", ["cm", "inches"])
    def test_a_plan_beside_the_blank_field_is_not_stored_either(
        self, app, unit
    ) -> None:
        """The plan half does not gate it, and does not slip through it."""
        client = app.test_client()
        book_id = _new_book(app.book_manager)
        assert _set_trim(client, book_id, *SIX_BY_NINE_CM).status_code == 302

        data = _blank_trim_form(unit=unit, blank_field="width", absent=False)
        data["plan_count"] = "120"

        with _recorded_flashes(app) as flashes:
            response = client.post(f"/book/{book_id}/setup-print", data=data)

        assert response.status_code == 200
        assert not [message for message in flashes if message.startswith("Print specs set")]
        assert _stored_columns(app.book_manager, book_id) == SIX_BY_NINE_CM
        assert app.book_manager.get_plan(book_id) == DEFAULT_PLAN

    def test_a_trim_only_form_with_a_blank_field_is_refused_too(self, app) -> None:
        """No plan fields at all: the trim half still refuses on its own."""
        client = app.test_client()
        book_id = _new_book(app.book_manager)
        assert _set_trim(client, book_id, *SIX_BY_NINE_CM).status_code == 302

        with _recorded_flashes(app) as flashes:
            response = client.post(
                f"/book/{book_id}/setup-print",
                data=_blank_trim_form(
                    unit="cm", blank_field="height", absent=True, plan=False
                ),
            )

        assert response.status_code == 200
        assert flashes == [
            "Error: Trim height must be entered: an empty trim field is not"
            " a size, so nothing was stored and the book keeps the trim it is on."
        ]
        assert _stored_columns(app.book_manager, book_id) == SIX_BY_NINE_CM

    @pytest.mark.parametrize("unit", ["cm", "inches"])
    def test_a_whitespace_only_field_is_blank_and_says_so(self, app, unit) -> None:
        """Whitespace was refused in both units already, but not in one voice."""
        client = app.test_client()
        book_id = _new_book(app.book_manager)
        assert _set_trim(client, book_id, *SIX_BY_NINE_CM).status_code == 302

        data = _blank_trim_form(unit=unit, blank_field="width", absent=False)
        data["width"] = "   \n  "

        with _recorded_flashes(app) as flashes:
            response = client.post(f"/book/{book_id}/setup-print", data=data)

        assert response.status_code == 200
        # Not "Error: Invalid inch value: \n    " — the form's own whitespace
        # quoted back at the owner (the incidental issue noted with F-101).
        assert flashes == [
            "Error: Trim width must be entered: an empty trim field is not"
            " a size, so nothing was stored and the book keeps the trim it is on."
        ]
        assert _stored_columns(app.book_manager, book_id) == SIX_BY_NINE_CM

    def test_the_refused_page_carries_the_submission_back(self, app) -> None:
        """The re-render is the inches branch's: the owner's entries survive."""
        client = app.test_client()
        book_id = _new_book(app.book_manager)
        assert _set_trim(client, book_id, *SIX_BY_NINE_CM).status_code == 302

        response = client.post(
            f"/book/{book_id}/setup-print",
            data={"unit": "cm", "width": "", "height": "22.86"},
        )

        html = response.get_data(as_text=True)
        assert _shown_trim(html) == ("", "22.86")
