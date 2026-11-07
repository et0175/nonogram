"""CARD-311 -- the owner's uploaded divider pages: the store, the four slots, the fit.

    AC-1  an uploaded divider reaches the reader and no other page changes
    AC-2  mixing works, enumerated over every subset of the four slots
    AC-3  an upload changes ink, never geometry (+ EC, a seeded corpus)
    AC-4  the refusals are refusals, each naming which, with two mutants each
    AC-5  persistence: a fresh manager over the same database still has it
    AC-6  the medium stays declared: the exported page is the declared bitmap

Scope of this module: the store and the upload slots (the first half of the
card). The drawn divider is still the fallback for an empty slot here.

Every expected value is stated from the page's own size or from a colour chosen
in the test, never read back from the function under test.
"""

from __future__ import annotations

import io
import itertools
import random
import uuid
from dataclasses import replace

import pytest
from PIL import Image, ImageChops

import nonogram.admin.book_manager as book_manager_module
from nonogram.admin.book_dividers import (
    ASPECT_TOLERANCE,
    DIVIDER_SLOTS,
    BelowBookDpi,
    DividerRefused,
    NotAnImage,
    TooLarge,
    WrongAspectRatio,
    accept_upload,
    fit_to_page,
    require_slot,
    slot_for_level,
)
from nonogram.admin.book_interior_vector import interior_generator
from nonogram.admin.book_manager import BookManager
from nonogram.admin.book_pdf_generator import (
    BookPDFGenerator,
    DividerPagePlan,
    PageKind,
    PageMedium,
    _RASTER_DECLARATIONS,
    page_medium,
)
from nonogram.difficulty import Tier
from tests.helpers.db import sqlite_session_scope
from tests.test_book_pdf_levels import AC253_MEMBERS, _book, _book_of
from tests.test_book_plan_storage import MODES, _build_app, _new_book

W, H, DPI = 600, 900, 300


def _png(width: int, height: int, colour=(200, 30, 30), fmt="PNG") -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (width, height), colour).save(out, format=fmt)
    return out.getvalue()


def _accept(data: bytes) -> bytes:
    return accept_upload(io.BytesIO(data), W, H, DPI)


@pytest.fixture
def scope(tmp_path):
    return sqlite_session_scope(tmp_path, "dividers311.db")


@pytest.fixture(params=MODES)
def mode(request):
    return request.param


@pytest.fixture
def manager(mode, scope):
    return BookManager(session_factory=None if mode == "memory" else scope)


# --------------------------------------------------------------------------
# the slots
# --------------------------------------------------------------------------


class TestSlots_AreTheThreeLevelsAndTheAnswerKey:
    def test_derived_from_the_tiers_then_solutions(self) -> None:
        assert DIVIDER_SLOTS == tuple(t.value for t in Tier) + ("solutions",)
        assert len(DIVIDER_SLOTS) == 4

    @pytest.mark.parametrize("bad", ["", "EASY", "../easy", "easy/../hard", None, "cover"])
    def test_a_name_outside_the_closed_set_is_refused(self, bad) -> None:
        with pytest.raises(ValueError):
            require_slot(bad)


# --------------------------------------------------------------------------
# AC-4 -- the refusals
# --------------------------------------------------------------------------


class TestRefusals_NameWhichAndStoreNothing:
    def test_a_page_shaped_picture_is_accepted_and_re_encoded(self) -> None:
        stored = _accept(_png(W, H, fmt="JPEG"))

        image = Image.open(io.BytesIO(stored))
        assert image.format == "PNG" and image.size == (W, H)

    def test_not_an_image(self) -> None:
        with pytest.raises(NotAnImage, match="not an image"):
            _accept(b"%PDF-1.4 definitely not a picture")

    def test_too_large_a_file(self) -> None:
        with pytest.raises(TooLarge):
            _accept(b"\0" * (10 * 1024 * 1024 + 1))

    def test_wrong_aspect_ratio_inside_the_claim(self) -> None:
        with pytest.raises(WrongAspectRatio, match="shape"):
            _accept(_png(900, 900))

    def test_wrong_aspect_ratio_at_the_edge(self) -> None:
        """Just inside the tolerance is accepted, just outside is refused."""
        inside = int(H * (W / H) * (1 + ASPECT_TOLERANCE * 0.5))
        outside = int(H * (W / H) * (1 + ASPECT_TOLERANCE * 2))
        assert _accept(_png(inside, H))
        with pytest.raises(WrongAspectRatio):
            _accept(_png(outside, H))

    def test_below_the_books_dpi_inside_the_claim(self) -> None:
        with pytest.raises(BelowBookDpi, match="not enlarged"):
            _accept(_png(W // 2, H // 2))

    def test_below_the_books_dpi_at_the_edge(self) -> None:
        """Exactly the page's pixels passes; one pixel short of it does not."""
        assert _accept(_png(W, H))
        with pytest.raises(BelowBookDpi):
            _accept(_png(W, H - 1))

    def test_a_phone_photo_sideways_is_turned_upright_before_it_is_judged(self) -> None:
        """EXIF orientation 6: stored as H x W, shown as W x H.

        Without ``exif_transpose`` this is a landscape picture and is refused
        as the wrong shape -- which is the control that the turn happens.
        """
        sideways = Image.new("RGB", (H, W), (10, 120, 10))
        exif = Image.Exif()
        exif[0x0112] = 6
        out = io.BytesIO()
        sideways.save(out, format="JPEG", exif=exif)

        stored = _accept(out.getvalue())

        assert Image.open(io.BytesIO(stored)).size == (W, H)


class TestFit_IsMadeAtExportAndNeverStretchesOrEnlarges:
    def test_a_larger_page_shaped_picture_is_reduced_to_the_page(self) -> None:
        fitted = fit_to_page(_png(2 * W, 2 * H), W, H, DPI)

        assert fitted.size == (W, H) and fitted.mode == "RGB"

    def test_a_trim_changed_after_the_upload_refuses_rather_than_stretches(self) -> None:
        with pytest.raises(WrongAspectRatio):
            fit_to_page(_png(W, H), W, H + 300, DPI)

    def test_a_trim_grown_after_the_upload_refuses_rather_than_enlarges(self) -> None:
        with pytest.raises(BelowBookDpi):
            fit_to_page(_png(W, H), 2 * W, 2 * H, DPI)

    def test_stored_bytes_that_are_not_a_picture(self) -> None:
        with pytest.raises(NotAnImage):
            fit_to_page(b"garbage", W, H, DPI)


# --------------------------------------------------------------------------
# AC-5 -- the store
# --------------------------------------------------------------------------


class TestStore_HoldsOnePicturePerBookAndSlot:
    def test_set_get_replace_clear(self, manager) -> None:
        book_id = _new_book(manager)
        first, second = _png(W, H, (1, 2, 3)), _png(W, H, (4, 5, 6))

        assert manager.divider_images(book_id) == {}
        assert manager.set_divider_image(book_id, "easy", first) is True
        assert manager.divider_images(book_id) == {"easy": first}
        manager.set_divider_image(book_id, "easy", second)
        manager.set_divider_image(book_id, "solutions", first)
        assert manager.divider_images(book_id) == {"easy": second, "solutions": first}
        assert manager.clear_divider_image(book_id, "easy") is True
        assert manager.clear_divider_image(book_id, "easy") is False
        assert manager.divider_images(book_id) == {"solutions": first}

    def test_another_books_slot_is_not_this_books(self, manager) -> None:
        a, b = _new_book(manager), _new_book(manager)
        manager.set_divider_image(a, "hard", _png(W, H))

        assert manager.divider_images(b) == {}

    def test_a_missing_book_stores_nothing(self, manager, mode) -> None:
        ghost = str(uuid.uuid4())

        assert manager.set_divider_image(ghost, "easy", _png(W, H)) is False
        assert manager.divider_images(ghost) == {}

    def test_an_unknown_slot_is_refused_and_stores_nothing(self, manager) -> None:
        book_id = _new_book(manager)

        with pytest.raises(ValueError):
            manager.set_divider_image(book_id, "../../etc/passwd", _png(W, H))
        assert manager.divider_images(book_id) == {}

    def test_deleting_the_book_deletes_its_pictures(self, manager, mode, scope) -> None:
        from nonogram.db.models import BookDividerImage

        book_id = _new_book(manager)
        manager.set_divider_image(book_id, "easy", _png(W, H))
        assert manager.delete_book(book_id) is True

        assert manager.divider_images(book_id) == {}
        if mode == "db":
            with scope() as db:
                assert db.query(BookDividerImage).count() == 0


class TestPersistence_SurvivesWhatTheCoversTempFileDoesNot:
    def test_a_fresh_manager_over_the_same_database_still_has_the_picture(
        self, scope, tmp_path
    ) -> None:
        """AC-5, measured: no object, session or directory carries the image.

        The second manager shares nothing with the first but the database; the
        temp directory the cover uses is not consulted at all, so purging it
        cannot touch this.
        """
        first = BookManager(session_factory=scope)
        book_id = _new_book(first)
        stored = _png(W, H, (9, 9, 9))
        first.set_divider_image(book_id, "medium", stored)
        del first

        reopened = BookManager(session_factory=scope)

        assert reopened.divider_images(book_id) == {"medium": stored}
        assert list(tmp_path.glob("**/*cover*")) == []


# --------------------------------------------------------------------------
# AC-1 / AC-2 / AC-3 / AC-6 -- the interior
# --------------------------------------------------------------------------

COLOURS = {
    "easy": (220, 20, 20),
    "medium": (20, 200, 20),
    "hard": (20, 20, 220),
    "solutions": (200, 200, 20),
}


def _generator(book=None, uploads=()):
    book = book or _book()
    base = BookPDFGenerator(book)
    images = {
        slot: _png(base.page_width_px, base.page_height_px, COLOURS[slot])
        for slot in uploads
    }
    return interior_generator(book, dividers=images)


def _pages(generator, puzzles):
    stream = generator.interior_stream(list(puzzles))
    return list(stream.pages), stream


def _slot_order(generator, puzzles):
    section = generator.section_plan(list(puzzles)).pages
    return [
        slot_for_level(p.level) for p in section if isinstance(p, DividerPagePlan)
    ] + ["solutions"]


def _same(a, b) -> bool:
    if isinstance(a, Image.Image):
        return (
            isinstance(b, Image.Image)
            and a.size == b.size
            and ImageChops.difference(a.convert("RGB"), b.convert("RGB")).getbbox() is None
        )
    return not isinstance(b, Image.Image) and a.operators == b.operators


def _divider_indices(stream):
    return [i for i, kind in enumerate(stream.page_kinds) if kind is PageKind.DIVIDER]


class TestInterior_AnUploadedDividerReachesTheReader:
    def test_the_uploaded_level_is_the_picture_and_no_other_page_changes(self) -> None:
        puzzles = _book_of(*AC253_MEMBERS)
        baseline, base_stream = _pages(_generator(), puzzles)
        pages, stream = _pages(_generator(uploads=["medium"]), puzzles)
        indices = _divider_indices(stream)
        order = _slot_order(_generator(), puzzles)
        target = indices[order.index("medium")]

        assert [i for i, _ in enumerate(pages) if not _same(pages[i], baseline[i])] == [target]
        page = pages[target]
        assert page.size == baseline[target].size
        assert page.convert("RGB").getpixel((page.width // 2, page.height // 2)) == COLOURS["medium"]
        assert page.convert("RGB").getpixel((page.width - 1, page.height - 1)) == COLOURS["medium"]

    @pytest.mark.parametrize(
        "uploaded",
        [
            subset
            for size in range(5)
            for subset in itertools.combinations(DIVIDER_SLOTS, size)
        ],
        ids=lambda s: "+".join(s) or "none",
    )
    def test_every_filled_slot_prints_its_image_and_every_empty_one_the_drawn_word(
        self, uploaded
    ) -> None:
        """AC-2, over all sixteen subsets, the slots read from the page plan."""
        puzzles = _book_of(*AC253_MEMBERS)
        baseline, _ = _pages(_generator(), puzzles)
        generator = _generator(uploads=uploaded)
        pages, stream = _pages(generator, puzzles)
        order = _slot_order(generator, puzzles)
        indices = _divider_indices(stream)

        assert len(order) == len(indices) == len(DIVIDER_SLOTS)
        for slot, index in zip(order, indices):
            if slot in uploaded:
                assert pages[index].convert("RGB").getpixel((5, 5)) == COLOURS[slot]
            else:
                assert _same(pages[index], baseline[index])
        others = [i for i in range(len(pages)) if i not in indices]
        assert all(_same(pages[i], baseline[i]) for i in others)

    def test_a_trim_that_no_longer_suits_the_upload_refuses_the_export(self) -> None:
        book = _book()
        wrong = _png(500, 500)
        generator = interior_generator(book, dividers={"easy": wrong})

        with pytest.raises(DividerRefused):
            _pages(generator, _book_of(*AC253_MEMBERS))


class TestInterior_AnUploadChangesInkNeverGeometry:
    """AC-3 and the EC."""

    def test_a_slot_for_an_absent_level_creates_no_page(self) -> None:
        """A book with Easy puzzles only has two dividers; uploads for the rest add none."""
        puzzles = _book_of(("E1", "easy"), ("E2", "easy"))
        plain = _generator()
        loaded = _generator(uploads=list(DIVIDER_SLOTS))

        plain_pages, plain_stream = _pages(plain, puzzles)
        pages, stream = _pages(loaded, puzzles)

        assert _slot_order(plain, puzzles) == ["easy", "solutions"]
        assert stream.page_count == plain_stream.page_count == len(pages)
        assert stream.page_kinds == plain_stream.page_kinds

    def test_the_corpus_page_plan_is_identical_with_and_without_uploads(self) -> None:
        rng = random.Random(311)
        tiers = ["easy", "medium", "hard"]
        cases = 0
        for _ in range(40):
            width = rng.choice(["12.7", "14.8", "15.24", "21.59"])
            height = rng.choice(["17.78", "21.0", "22.86", "27.94"])
            book = replace(_book(), trim_width_cm=width, trim_height_cm=height)
            members = [
                (f"P{i}", rng.choice(tiers)) for i in range(rng.randint(1, 6))
            ]
            puzzles = _book_of(*members)
            uploads = [s for s in DIVIDER_SLOTS if rng.random() < 0.5]

            plain_pages, plain = _pages(_generator(book), puzzles)
            pages, stream = _pages(_generator(book, uploads), puzzles)

            assert stream.page_count == plain.page_count == len(pages) == len(plain_pages)
            assert stream.unpaired_page_count == plain.unpaired_page_count
            assert stream.page_kinds == plain.page_kinds
            plan = [
                (type(p).__name__, p.page_number)
                for p in _generator(book, uploads).section_plan(puzzles).pages
            ]
            assert plan == [
                (type(p).__name__, p.page_number)
                for p in _generator(book).section_plan(puzzles).pages
            ]
            for index, (a, b) in enumerate(zip(pages, plain_pages)):
                if stream.page_kinds[index] is not PageKind.DIVIDER:
                    assert _same(a, b), (width, height, members, uploads, index)
            cases += 1
        assert cases >= 40


class TestMedium_TheUploadedPageIsTheDeclaredBitmap:
    def test_the_declaration_is_permanent_and_says_why(self) -> None:
        declaration = _RASTER_DECLARATIONS[PageKind.DIVIDER]

        assert page_medium(PageKind.DIVIDER) is PageMedium.RASTER
        assert declaration.expires_with == ()
        assert "uploaded" in declaration.reason
        assert "CARD-231" not in declaration.reason + declaration.authority

    def test_the_book_exports_with_an_uploaded_divider_and_write_pdf_does_not_refuse(
        self,
    ) -> None:
        puzzles = _book_of(*AC253_MEMBERS)
        generator = _generator(uploads=list(DIVIDER_SLOTS))

        pdf = generator.export_interior(puzzles).getvalue()
        _, stream = _pages(generator, puzzles)

        assert pdf.startswith(b"%PDF")
        assert pdf.count(b"/DCTDecode") >= len(DIVIDER_SLOTS)
        assert all(
            page_medium(kind) is PageMedium.RASTER
            for kind in stream.page_kinds
            if kind is PageKind.DIVIDER
        )


# --------------------------------------------------------------------------
# the routes
# --------------------------------------------------------------------------


@pytest.fixture
def app(mode, scope, monkeypatch):
    return _build_app(mode, scope, monkeypatch)


def _frame(app, book_id):
    generator = BookPDFGenerator(app.book_manager.get_book(book_id))
    return generator.page_width_px, generator.page_height_px


def _post(client, book_id, slot, data, filename="photo.png"):
    return client.post(
        f"/book/{book_id}/divider/{slot}",
        data={"divider": (io.BytesIO(data), filename)},
        content_type="multipart/form-data",
        follow_redirects=True,
    )


class TestRoutes_UploadAndRefuse:
    def test_an_upload_is_stored_under_the_slot_and_never_the_clients_filename(
        self, app
    ) -> None:
        client = app.test_client()
        book_id = _new_book(app.book_manager)
        w, h = _frame(app, book_id)

        response = _post(client, book_id, "easy", _png(w, h), "../../etc/evil name.png")

        assert response.status_code == 200
        assert "Easy divider uploaded" in response.get_data(as_text=True)
        stored = app.book_manager.divider_images(book_id)
        assert list(stored) == ["easy"]
        assert Image.open(io.BytesIO(stored["easy"])).size == (w, h)

    @pytest.mark.parametrize(
        ("kind", "message"),
        [("shape", "shape"), ("small", "not enlarged"), ("text", "not an image")],
    )
    def test_each_refusal_names_which_and_leaves_the_store_as_it_was(
        self, app, kind, message
    ) -> None:
        client = app.test_client()
        book_id = _new_book(app.book_manager)
        w, h = _frame(app, book_id)
        before = _png(w, h, (7, 7, 7))
        app.book_manager.set_divider_image(book_id, "hard", before)
        data = {
            "shape": _png(w, w),
            "small": _png(w // 2, h // 2),
            "text": b"just some words",
        }[kind]

        response = _post(client, book_id, "hard", data)

        html = response.get_data(as_text=True)
        assert "Hard divider was refused" in html and message in html
        assert app.book_manager.divider_images(book_id) == {"hard": before}

    def test_an_unknown_slot_is_refused(self, app) -> None:
        client = app.test_client()
        book_id = _new_book(app.book_manager)
        w, h = _frame(app, book_id)

        response = _post(client, book_id, "cover", _png(w, h))

        assert "Unknown divider" in response.get_data(as_text=True)
        assert app.book_manager.divider_images(book_id) == {}

    def test_clear_removes_it_and_the_finalise_page_lists_all_four_slots(self, app) -> None:
        client = app.test_client()
        book_id = _new_book(app.book_manager)
        w, h = _frame(app, book_id)
        _post(client, book_id, "solutions", _png(w, h))

        page = client.get(f"/book/{book_id}/finalize").get_data(as_text=True)
        for slot in DIVIDER_SLOTS:
            assert f'data-divider-slot="{slot}"' in page
        assert "Uploaded" in page

        client.post(f"/book/{book_id}/divider/solutions/clear")

        assert app.book_manager.divider_images(book_id) == {}


# --------------------------------------------------------------------------
# migration 019
# --------------------------------------------------------------------------


class TestMigration019:
    def test_chain_and_roundtrip(self, tmp_path, monkeypatch) -> None:
        import sqlalchemy as sa

        from tests.test_book_page_spec import _alembic

        url = f"sqlite:///{tmp_path / 'migrate-019.db'}"
        command, config = _alembic(url, monkeypatch)
        command.upgrade(config, "018")
        engine = sa.create_engine(url)
        assert "book_divider_images" not in sa.inspect(engine).get_table_names()

        command.upgrade(config, "019")

        inspector = sa.inspect(engine)
        assert "book_divider_images" in inspector.get_table_names()
        assert {c["name"] for c in inspector.get_columns("book_divider_images")} == {
            "id", "book_id", "slot", "image", "created_at", "updated_at",
        }
        assert any(
            sorted(u["column_names"]) == ["book_id", "slot"]
            for u in inspector.get_unique_constraints("book_divider_images")
        )

        command.downgrade(config, "018")
        assert "book_divider_images" not in sa.inspect(engine).get_table_names()
