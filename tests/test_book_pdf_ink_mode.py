"""CARD-147 — the book interior is written black-and-white or in colour, and says which.

    AC-1   TestBookInk_BlackAndWhiteInteriorIsGrayscale
    AC-2   TestBookInk_ColourInteriorIsUnchanged
    AC-3   TestBookInk_ModeIsStoredAndDefaultsToBlackAndWhite
    AC-4   TestBookInk_PrintSetupAndFinaliseShowTheMode
    AC-5   TestBookInk_CoverIgnoresTheInteriorMode
    EC-1   TestBookInk_InkPositionsDoNotDependOnTheMode

**There is no FR to cite, and that is deliberate.** This is owner intake —
``meta/architecture/inputs/raw-requirements.md``, 2026-09-25, "2 modes to pdf
generator: black/white and colors … I was a bit too creative making colored
pages for book 1 — then it gets more expensive. But we may add colors for
book2" — which the architect station has not formalised. CARD-144 cited FR-041,
the level-divider requirement, at about fifteen sites in order to look traced,
and its review charged it a finding for exactly that. The intake line is the
honest citation and it is the only one here.

What the card is, and what it is not
------------------------------------
The interior's **content** has always been pure black and white: COMP-007 draws
``INK = (0, 0, 0)`` on ``BACKGROUND = (255, 255, 255)`` and nothing else. So
this is not "remove the colours" — there are none. It is that the **file**
declared colour: every page was composed ``"RGB"``, JPEG-encoded in RGB and
written with ``/DeviceRGB``, which invites a print-on-demand interior's colour
price for a book with no colour in it. The book now stores which it is
(``books.interior_ink_mode``, migration 013) and the file says what the book
says.

**The measured surprise, recorded here because it is the opposite of what the
card predicted.** The card expected a grayscale interior to move every page's
recorded digest. It moves **none** of them. ``tests/helpers/pdf_pages.py``
reads a page back out of the PDF and normalises it to RGB, and a JPEG keeps the
luma plane: libjpeg's integer RGB->YCbCr maps a grey ``(v, v, v)`` to ``Y = v``
with ``Cb = Cr = 128``, the same luma quantisation table is used either way, and
``Cb = Cr = 128`` decodes back to ``R = G = B = Y`` exactly. So the eleven pages
decoded out of a grayscale interior are **byte-identical** to the eleven decoded
out of the RGB one, and ``book_baseline_card147.json`` records that as its
finding rather than eleven moved digests. What *does* move is the file's length,
which is the whole point: one channel of JPEG instead of three.
:class:`TestBookInk_BlackAndWhiteInteriorIsGrayscale` asserts both halves — the
file declares ``DeviceGray`` and is materially smaller, and not one mark moved.

How the two modes are compared
------------------------------
Two independent readings, because each would hide something the other catches:

* **off the written file** — :func:`pdf_image_objects` parses the PDF's own
  image XObjects and reports the ``ColorSpace``, the ``ProcSet`` and the decoded
  page. That is what a printer reads, and it is the only place "the file
  declares ``DeviceGray``" can be checked at all. It is a second implementation
  of what ``tests/helpers/pdf_pages.py`` does, deliberately: that helper
  normalises every page to RGB, which is precisely the fact under test here, so
  it cannot be the instrument.
* **off the page bitmaps before they are encoded** — ``interior_stream``'s own
  pages, converted the way the writer converts them. JPEG is lossy, so an
  exact "no mark moved" claim belongs on the bitmaps; the file-level reading
  then confirms that the loss is identical in the two colour spaces.

No ``hypothesis`` (it is not in the dependency baseline): EC-1's corpus is
built by hand with stdlib ``random.Random`` and asserts its own size, so it
cannot silently shrink (CLAUDE.md).
"""

from __future__ import annotations

import json
import random
import uuid
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pytest
from PIL import Image, PdfParser

import nonogram.admin.book_manager as book_manager_module
from nonogram import clues
from nonogram.admin.book_manager import Book, BookManager, BookMetadata
from nonogram.admin.book_page_spec import (
    DEFAULT_INK_MODE,
    INK_MODE_COLUMN,
    InkMode,
    book_ink_mode,
    ink_mode_from_stored,
)
from nonogram.admin.book_pdf_generator import BookPDFGenerator
from nonogram.admin.book_plan import BUCKETS, TIERS, DistributionPlan, Split, bucket_of
from nonogram.admin.print_specs import PrintSpec, PrintSpecValidator
from tests.helpers.book_corpus import (
    BASELINE_PAGE_COUNT,
    baseline_puzzles,
    corpus_book,
    export_of,
    font_fingerprint,
    page_digests,
)
from tests.helpers.pdf_pages import pdf_page_count, pdf_pages

REPO_ROOT = Path(__file__).resolve().parents[1]

#: The recording of this book made **before** this card, by CARD-146, left
#: unregenerated. AC-2's "byte-identical to the pre-card export" is checked
#: against it rather than against a number typed into this file: it is the
#: evidence of what a colour interior was, recorded when it was the only kind.
PRE_CARD_BASELINE = REPO_ROOT / "tests" / "fixtures" / "book_baseline_card146.json"

#: A pixel darker than this (0..255 grey) is ink — the level every other reader
#: of a book page in this suite uses.
INK_LEVEL = 128

#: How many books EC-1's corpus holds. Asserted inside the property test
#: against a literal, so neither the constant nor the loop can quietly shrink
#: it (the idiom at ``tests/test_books_list_plan_stats.py:808``; CARD-149's
#: review found a floor that could not fail).
EC1_BOOKS = 14

#: How many interior **pages** EC-1 compares across its whole corpus. A floor
#: on the pages and not only on the books: a corpus of fourteen one-page books
#: would satisfy a book count and prove nothing.
#:
#: 117 is the number the corpus above really produces — measured, not a bound
#: with room in it — so one page fewer fails. The literal in the assertion's
#: chain (``pages >= EC1_PAGES >= 110``) is what keeps this constant from being
#: quietly lowered to whatever a shrunken corpus happens to yield.
EC1_PAGES = 117


# --------------------------------------------------------------------------
# Reading a book PDF's own colour space
# --------------------------------------------------------------------------


def _pdf_name(value: Any) -> str:
    """One PDF name as plain text — ``PdfName(b'DeviceGray')`` -> ``"DeviceGray"``.

    Pillow's parser hands a ``/Name`` back as a :class:`PIL.PdfParser.PdfName`
    whose ``name`` is the bytes without the slash. Spelled out here so an
    assertion reads as the colour space a printer would see.
    """
    name = getattr(value, "name", value)
    return name.decode("ascii") if isinstance(name, bytes) else str(name)


def pdf_image_objects(data: bytes) -> List[Dict[str, Any]]:
    """Every page's image XObject in ``data``, as the file declares it.

    One dict per page, in page order: ``colour_space`` and ``procset`` straight
    off the PDF objects, ``filter``, the JPEG stream's length, and ``image``,
    the page decoded **in the mode it was written in** — ``"L"`` for a
    grayscale page, ``"RGB"`` for a colour one.

    That last point is why this exists beside ``tests/helpers/pdf_pages.py``
    rather than calling it: that helper ends with ``.convert("RGB")``, which
    normalises away the one thing this card changes. Nothing here asks the
    generator anything; it reads the bytes a route produced.
    """
    parser = PdfParser.PdfParser(buf=data)
    try:
        pages = []
        for ref in parser.pages:
            page = parser.read_indirect(ref)
            resources = page[b"Resources"]
            xobjects = resources[b"XObject"]
            assert len(xobjects) == 1, "a book page is exactly one image"
            (stream_ref,) = xobjects.values()
            stream = parser.read_indirect(stream_ref)
            image = Image.open(BytesIO(stream.buf))
            image.load()
            pages.append(
                {
                    "colour_space": _pdf_name(stream.dictionary[b"ColorSpace"]),
                    "procset": [_pdf_name(name) for name in resources[b"ProcSet"]],
                    "filter": _pdf_name(stream.dictionary[b"Filter"]),
                    "bits": int(stream.dictionary[b"BitsPerComponent"]),
                    "jpeg_bytes": len(stream.buf),
                    "image": image,
                }
            )
        return pages
    finally:
        parser.close()


def ink_mask(image: Image.Image) -> np.ndarray:
    """Which of ``image``'s pixels are ink, at full resolution and no tolerance.

    ``convert("L")`` on an already-grayscale page is the identity, and on a
    grey RGB page it is exact (ITU-R 601-2's three integer coefficients sum to
    65536), so the two modes are compared on the same quantity without either
    being favoured.
    """
    return np.asarray(image.convert("L")) < INK_LEVEL


def grey_levels(image: Image.Image) -> np.ndarray:
    """``image``'s luma as a 2-D array of 0..255."""
    return np.asarray(image.convert("L"))


# --------------------------------------------------------------------------
# Books
# --------------------------------------------------------------------------


def book_on(mode: InkMode | None, book_id: str = "card-147") -> Book:
    """The baseline book, on CON-018's Book 1 profile, printed ``mode``.

    ``None`` stores nothing in the column, which is every book that existed
    before migration 013 — the case AC-3 is about.
    """
    book = corpus_book(book_id)
    book.interior_ink_mode = mode.value if mode is not None else None
    return book


def interiors_both_ways(puzzles, book_id: str = "card-147") -> Tuple[bytes, bytes]:
    """The same book's interior exported black-and-white, then colour.

    One function, so the two exports cannot differ in anything but the mode:
    the same puzzle list, the same stored trim and margins, the same call.
    """
    bw = export_of(BookPDFGenerator(book_on(InkMode.BLACK_AND_WHITE, book_id)), puzzles)
    colour = export_of(BookPDFGenerator(book_on(InkMode.COLOUR, book_id)), puzzles)
    return bw, colour


@pytest.fixture(scope="module")
def baseline_exports() -> Tuple[bytes, bytes]:
    """The eleven-page baseline book, exported both ways, once for the module."""
    return interiors_both_ways(baseline_puzzles())


@pytest.fixture(scope="module")
def pre_card_baseline() -> Dict[str, Any]:
    """CARD-146's recording of this book: what a colour interior was before."""
    with PRE_CARD_BASELINE.open(encoding="utf-8") as handle:
        return json.load(handle)


@pytest.fixture(scope="module")
def same_face(pre_card_baseline) -> bool:
    """Whether this machine letters the guide and the dividers as recorded."""
    return font_fingerprint() == pre_card_baseline["font_fingerprint"]


# --------------------------------------------------------------------------
# AC-1
# --------------------------------------------------------------------------


class TestBookInk_BlackAndWhiteInteriorIsGrayscale:
    """A black-and-white book's interior is grayscale, and no mark moved (AC-1).

    Three claims, each measured rather than reasoned about:

    * every page of the file is written in one 8-bit channel and the PDF
      declares ``/DeviceGray`` with the grayscale procset ``/ImageB`` — which
      is what makes the file honest about a book that has no colour in it;
    * the ink is **pixel-for-pixel the same marks** as the RGB rendering, on
      the page bitmaps (exact, before the lossy encode) and on the pages
      decoded back out of the two files (also exact, as it turns out);
    * and the conversion softens nothing (G-2, ADR-0037/R2): pure black stays
      0, pure white stays 255, and the conversion invents no level between
      them.
    """

    def test_every_page_declares_devicegray_and_one_channel(self, baseline_exports):
        bw, _colour = baseline_exports
        pages = pdf_image_objects(bw)

        assert len(pages) == BASELINE_PAGE_COUNT, "the corpus cannot silently shrink"
        for number, page in enumerate(pages, start=1):
            assert page["colour_space"] == "DeviceGray", f"interior page {number}"
            assert page["procset"] == ["PDF", "ImageB"], f"interior page {number}"
            assert page["filter"] == "DCTDecode", f"interior page {number}"
            assert page["bits"] == 8, f"interior page {number}"
            assert page["image"].mode == "L", f"interior page {number}"

    def test_the_colour_export_of_the_same_book_declares_devicergb(
        self, baseline_exports
    ):
        """The control: the difference really is the mode and not the export."""
        _bw, colour = baseline_exports
        for number, page in enumerate(pdf_image_objects(colour), start=1):
            assert page["colour_space"] == "DeviceRGB", f"interior page {number}"
            assert page["procset"] == ["PDF", "ImageC"], f"interior page {number}"
            assert page["image"].mode == "RGB", f"interior page {number}"

    def test_no_mark_moves_on_any_page_bitmap(self):
        """The exact half: COMP-007's page, converted, is the same ink (G-2).

        Compared before the JPEG encode, where "pixel-for-pixel" can be
        asserted without a tolerance at all. The conversion is the writer's
        own — ``Image.convert("L")`` — and what is checked is that it is the
        identity on luma: the grayscale page equals the RGB page's own
        ``convert("L")``, every ink position is the same position, and the set
        of levels is unchanged, so no anti-aliasing was introduced and no rule
        was softened.
        """
        generator = BookPDFGenerator(book_on(InkMode.BLACK_AND_WHITE))
        assert generator.interior_bitmap_mode == "L"

        checked = 0
        for number, page in enumerate(
            generator.interior_stream(baseline_puzzles()).pages, start=1
        ):
            assert page.mode == "RGB", "COMP-007 draws the page in RGB either way"
            rgb = np.asarray(page)
            grey = np.asarray(page.convert("L"))

            # The three channels of a book page are equal to begin with: the
            # interior has no colour to lose. Asserted, not assumed — if a
            # future page ever drew one, the claims below would be false.
            assert np.array_equal(rgb[:, :, 0], rgb[:, :, 1])
            assert np.array_equal(rgb[:, :, 1], rgb[:, :, 2])

            # ... so the conversion is the identity on the page's own levels.
            assert np.array_equal(grey, rgb[:, :, 0]), f"page {number} moved"
            assert np.array_equal(grey < INK_LEVEL, rgb[:, :, 0] < INK_LEVEL)

            # G-2: pure black stays 0, pure white stays 255, and no level that
            # was not already on the page appears.
            assert set(np.unique(grey).tolist()) <= set(
                np.unique(rgb[:, :, 0]).tolist()
            ), f"page {number} gained a grey level the RGB page did not have"
            assert int((grey == 0).sum()) == int((rgb[:, :, 0] == 0).sum())
            assert int((grey == 255).sum()) == int((rgb[:, :, 0] == 255).sum())
            assert int((grey == 0).sum()) > 0, f"page {number} carries no pure black"
            checked += 1

        assert checked == BASELINE_PAGE_COUNT == 11, f"only {checked} pages compared"

    def test_the_two_files_hold_the_same_marks_page_for_page(self, baseline_exports):
        """And the same after the encode: the two files decode to one ink.

        The claim the card's "nothing moves, nothing is lost" makes about the
        *file*, which is what a printer sees. It holds exactly — JPEG keeps the
        luma plane and constant chroma planes decode back to it — so this is an
        equality and not an overlap ratio.
        """
        bw, colour = baseline_exports
        grey_pages = pdf_image_objects(bw)
        colour_pages = pdf_image_objects(colour)

        assert pdf_page_count(bw) == pdf_page_count(colour) == BASELINE_PAGE_COUNT
        for number, (g, c) in enumerate(zip(grey_pages, colour_pages, strict=True), 1):
            assert g["image"].size == c["image"].size, f"interior page {number}"
            assert np.array_equal(
                ink_mask(g["image"]), ink_mask(c["image"])
            ), f"interior page {number}: the ink moved"
            assert np.array_equal(
                grey_levels(g["image"]), grey_levels(c["image"])
            ), f"interior page {number}: a level moved"

    @pytest.mark.parametrize(
        "mode,colour_space",
        [(InkMode.BLACK_AND_WHITE, "DeviceGray"), (InkMode.COLOUR, "DeviceRGB")],
    )
    def test_the_file_the_owner_downloads_is_the_one_the_book_chose(
        self, panel, mode, colour_space
    ):
        """End to end, through the route Finalise's button posts to.

        Everything above exports through the generator. This closes the loop
        the owner actually walks: choose the mode on Print setup's form,
        press Download interior PDF on Finalise, and read the colour space off
        the bytes that come back as an attachment. Nothing between the two
        screens is stubbed.
        """
        book_id = panel.book()
        panel.submit_print_setup(book_id, interior_ink_mode=mode.value)

        downloaded = panel.download_interior(book_id)
        spaces = {page["colour_space"] for page in pdf_image_objects(downloaded)}
        assert spaces == {colour_space}
        assert f'data-interior-ink-mode="{mode.value}"' in panel.finalise(book_id), (
            "and Finalise names the mode the file was written in"
        )

    def test_the_grayscale_file_is_materially_smaller(self, baseline_exports):
        """Size is one of the card's three stated reasons, so it is measured.

        One channel of JPEG where there were three. The bound is loose on
        purpose — what is asserted is that the saving is real and
        page-for-page, not a particular ratio, which depends on how much ink a
        page carries.
        """
        bw, colour = baseline_exports
        assert len(bw) < len(colour)

        grey_pages = pdf_image_objects(bw)
        colour_pages = pdf_image_objects(colour)
        for number, (g, c) in enumerate(zip(grey_pages, colour_pages, strict=True), 1):
            assert g["jpeg_bytes"] < c["jpeg_bytes"], f"interior page {number}"

        saved = 1 - len(bw) / len(colour)
        assert 0.05 < saved < 0.5, f"the grayscale interior saved {saved:.1%}"


# --------------------------------------------------------------------------
# AC-2
# --------------------------------------------------------------------------


class TestBookInk_ColourInteriorIsUnchanged:
    """A colour book exports exactly what shipped before this card (AC-2).

    Checked against ``tests/fixtures/book_baseline_card146.json`` — the
    recording of this very book made before a line of this card existed, left
    unregenerated. Both halves of "byte-identical": the eleven page digests and
    the file's own length.

    The length is gated on the machine's face, exactly as
    ``tests/test_book_pdf_memory.py`` gates it: the guide page and the four
    dividers are lettered in the system's Arial when Pillow can find it, and
    their JPEG streams are a different length under another face.
    """

    def test_the_eleven_pages_are_the_pages_card146_recorded(
        self, baseline_exports, pre_card_baseline, same_face
    ):
        _bw, colour = baseline_exports
        now = page_digests(pdf_pages(colour))
        recorded = pre_card_baseline["pages"]
        machine_face = set(pre_card_baseline["font_dependent_pages"])

        assert len(now) == len(recorded) == BASELINE_PAGE_COUNT
        compared = 0
        for number, (drawn, was) in enumerate(zip(now, recorded, strict=True), start=1):
            if number in machine_face and not same_face:
                continue
            assert drawn == was, f"interior page {number} is not the page it was"
            assert drawn["mode"] == "RGB"
            compared += 1

        expected = BASELINE_PAGE_COUNT - (0 if same_face else len(machine_face))
        assert compared == expected, f"compared {compared}, expected {expected}"

    def test_the_colour_interior_is_the_length_it_always_was(
        self, baseline_exports, pre_card_baseline, same_face
    ):
        if not same_face:
            pytest.skip(
                "this machine letters the guide page and the dividers in "
                "another face, so the file's length is not the recorded one"
            )
        _bw, colour = baseline_exports
        assert len(colour) == pre_card_baseline["interior_bytes"]

    def test_the_black_and_white_interior_is_not_that_length(
        self, baseline_exports, pre_card_baseline, same_face
    ):
        """The control for the test above: the equality is not vacuous."""
        if not same_face:
            pytest.skip("see the test above")
        bw, _colour = baseline_exports
        assert len(bw) != pre_card_baseline["interior_bytes"]


# --------------------------------------------------------------------------
# AC-3
# --------------------------------------------------------------------------


class TestBookInk_ModeIsStoredAndDefaultsToBlackAndWhite:
    """The mode is stored, survives a reopen, and defaults to black-and-white (AC-3).

    "Every existing book" is three different books, and each is checked:

    * a book whose column holds ``NULL`` — a row from before migration 013;
    * a book whose column holds the empty string — what a form that submitted
      a blank field would leave;
    * and a ``books`` row that migration 013 has actually upgraded, which is
      where the backfill is executed rather than described.
    """

    @pytest.mark.parametrize("stored", [None, "", "   "])
    def test_a_book_with_nothing_stored_is_black_and_white(self, stored):
        assert ink_mode_from_stored(stored) is InkMode.BLACK_AND_WHITE
        assert ink_mode_from_stored(stored) is DEFAULT_INK_MODE
        assert book_ink_mode(book_on(None)) is InkMode.BLACK_AND_WHITE

    def test_a_book_that_is_not_a_book_at_all_is_black_and_white(self):
        """``BookPDFGenerator(None)`` is CON-018's profile, and its ink too."""
        assert book_ink_mode(None) is InkMode.BLACK_AND_WHITE
        assert BookPDFGenerator().interior_bitmap_mode == "L"

    @pytest.mark.parametrize(
        "mode,bitmap", [(InkMode.BLACK_AND_WHITE, "L"), (InkMode.COLOUR, "RGB")]
    )
    def test_each_mode_names_one_bitmap_mode(self, mode, bitmap):
        assert mode.bitmap_mode == bitmap
        assert BookPDFGenerator(book_on(mode)).interior_bitmap_mode == bitmap

    def test_a_value_nobody_can_print_is_refused_naming_the_column(self):
        """Not silently read as one of the two (the ``_stored_mm`` posture)."""
        with pytest.raises(ValueError) as raised:
            ink_mode_from_stored("greyscale")
        assert INK_MODE_COLUMN in str(raised.value)
        assert "'bw'" in str(raised.value) and "'colour'" in str(raised.value)

        # And through the book, which is how every reader asks.
        with pytest.raises(ValueError) as raised:
            book_ink_mode(_odd_book())
        assert INK_MODE_COLUMN in str(raised.value)

        # A generator cannot be built for such a book at all, so no file is
        # written in a colour space nobody chose.
        with pytest.raises(ValueError):
            BookPDFGenerator(_odd_book())

    def test_the_mode_is_stored_and_survives_a_reopen(self, panel):
        """Written through the real setter, read back through a fresh get_book."""
        book_id = panel.book()
        assert book_ink_mode(panel.books.get_book(book_id)) is InkMode.BLACK_AND_WHITE

        panel.books.set_print_spec(
            book_id, PrintSpec("21.59", "27.94", interior_ink_mode="colour")
        )
        reopened = panel.books.get_book(book_id)
        assert reopened.interior_ink_mode == "colour"
        assert book_ink_mode(reopened) is InkMode.COLOUR

        panel.books.set_print_spec(
            book_id, PrintSpec("21.59", "27.94", interior_ink_mode="bw")
        )
        assert book_ink_mode(panel.books.get_book(book_id)) is InkMode.BLACK_AND_WHITE

    def test_a_spec_that_names_no_mode_leaves_the_stored_one_alone(self, panel):
        """"The caller said nothing" is not "set it to the default"."""
        book_id = panel.book()
        panel.books.set_print_spec(
            book_id, PrintSpec("21.59", "27.94", interior_ink_mode="colour")
        )
        panel.books.set_print_spec(book_id, PrintSpec("20.32", "25.40"))
        reopened = panel.books.get_book(book_id)
        assert reopened.trim_width_cm == "20.32", "the trim was stored"
        assert book_ink_mode(reopened) is InkMode.COLOUR, "and the mode was kept"

    def test_the_storage_boundary_refuses_a_mode_the_reader_would_refuse(self, panel):
        book_id = panel.book()
        with pytest.raises(ValueError) as raised:
            panel.books.set_print_spec(
                book_id, PrintSpec("21.59", "27.94", interior_ink_mode="sepia")
            )
        assert "interior ink mode" in str(raised.value)
        assert book_ink_mode(panel.books.get_book(book_id)) is InkMode.BLACK_AND_WHITE

    def test_the_validator_accepts_the_two_modes_and_nothing_else(self):
        for mode in InkMode:
            assert PrintSpecValidator.validate_interior_ink_mode(mode.value) == (
                True,
                None,
            )
        assert PrintSpecValidator.validate_interior_ink_mode(None)[0] is True
        assert PrintSpecValidator.validate_interior_ink_mode("")[0] is True
        valid, error = PrintSpecValidator.validate_interior_ink_mode("mono")
        assert valid is False and "mono" in error

    def test_create_spec_fills_the_default(self):
        spec, error = PrintSpecValidator.create_spec("21.59", "27.94")
        assert error is None
        assert spec.interior_ink_mode == DEFAULT_INK_MODE.value == "bw"
        assert spec.to_dict()["interior_ink_mode"] == "bw"


def _odd_book() -> Book:
    """A book whose stored mode is one nobody can print."""
    book = corpus_book("card-147-odd")
    book.interior_ink_mode = "greyscale"
    return book


class TestBookInk_Migration013BackfillsEveryExistingBook:
    """AC-3's stored half: migration 013 gives every existing row ``'bw'``.

    Executed, not described. The database is built in today's shape, the
    column is dropped back off to make it a pre-013 row, a book is inserted
    into it by the pre-013 code path, and then 013 is actually run.

    SQLite here rather than Postgres because the suite must run without a
    server (the project's DB-mode tests skip when there is none). The
    migration uses ``batch_alter_table`` and a portable ``UPDATE`` built from
    SQLAlchemy's expression language, so what is exercised is the statement
    both backends run; the Postgres path was additionally run by hand against
    ``nonogram_test`` and is reported on the card.
    """

    @pytest.fixture
    def pre_013_db(self, tmp_path, monkeypatch):
        from sqlalchemy import create_engine, text

        from nonogram.db.models import Base

        path = tmp_path / "pre013.db"
        url = f"sqlite:///{path}"
        engine = create_engine(url)
        Base.metadata.create_all(engine)
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE books DROP COLUMN interior_ink_mode")
            )
            connection.execute(
                text(
                    "INSERT INTO books (id, title, puzzle_ids, puzzle_titles, "
                    "book_metadata, status) VALUES "
                    "('11111111-1111-1111-1111-111111111111', 'Book 1', "
                    "'[]', '{}', '{}', 'draft')"
                )
            )
        engine.dispose()

        monkeypatch.setenv("DATABASE_URL", url)
        from alembic import command

        command.stamp(self._config(url), "012")
        return url

    @staticmethod
    def _config(url: str):
        from alembic.config import Config

        config = Config()
        config.set_main_option("script_location", str(REPO_ROOT / "migrations"))
        config.set_main_option("sqlalchemy.url", url)
        return config

    @staticmethod
    def _books(url: str):
        from sqlalchemy import create_engine, inspect, text

        engine = create_engine(url)
        try:
            columns = {c["name"] for c in inspect(engine).get_columns("books")}
            with engine.connect() as connection:
                if "interior_ink_mode" in columns:
                    rows = connection.execute(
                        text("SELECT title, interior_ink_mode FROM books")
                    ).all()
                else:
                    rows = connection.execute(text("SELECT title FROM books")).all()
            return columns, rows
        finally:
            engine.dispose()

    def test_the_fixture_really_is_a_pre_013_database(self, pre_013_db):
        columns, rows = self._books(pre_013_db)
        assert "interior_ink_mode" not in columns
        assert len(rows) == 1, "the book the upgrade has to reach"

    def test_upgrade_adds_the_column_and_backfills_the_existing_book(
        self, pre_013_db
    ):
        from alembic import command

        command.upgrade(self._config(pre_013_db), "013")

        columns, rows = self._books(pre_013_db)
        assert "interior_ink_mode" in columns
        assert [(title, mode) for title, mode in rows] == [("Book 1", "bw")]
        assert ink_mode_from_stored(rows[0][1]) is InkMode.BLACK_AND_WHITE

    def test_a_book_inserted_after_the_upgrade_is_black_and_white_too(
        self, pre_013_db
    ):
        """The column's own default, so a row written without naming it is 'bw'."""
        from alembic import command
        from sqlalchemy import create_engine, text

        command.upgrade(self._config(pre_013_db), "013")
        engine = create_engine(pre_013_db)
        try:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO books (id, title, puzzle_ids, puzzle_titles, "
                        "book_metadata, status) VALUES "
                        "('22222222-2222-2222-2222-222222222222', 'Book 2', "
                        "'[]', '{}', '{}', 'draft')"
                    )
                )
                stored = connection.execute(
                    text(
                        "SELECT interior_ink_mode FROM books WHERE title = 'Book 2'"
                    )
                ).scalar()
        finally:
            engine.dispose()
        assert stored == "bw"

    def test_the_downgrade_takes_the_column_back_off(self, pre_013_db):
        from alembic import command

        command.upgrade(self._config(pre_013_db), "013")
        command.downgrade(self._config(pre_013_db), "012")
        columns, rows = self._books(pre_013_db)
        assert "interior_ink_mode" not in columns
        assert len(rows) == 1, "and takes no book with it"


# --------------------------------------------------------------------------
# AC-4
# --------------------------------------------------------------------------


class TestBookInk_PrintSetupAndFinaliseShowTheMode:
    """Print setup offers the choice and Finalise names it (AC-4).

    The owner has to be able to see which of the two the file they are about to
    upload will be, because that is what it is priced on. Both screens are read
    as the owner sees them — the rendered HTML — and the choice is made through
    the real form POST, not by writing the column.
    """

    def test_print_setup_offers_both_modes_with_the_stored_one_checked(self, panel):
        book_id = panel.book()
        shown = panel.print_setup(book_id)

        for mode in InkMode:
            assert f'value="{mode.value}"' in shown, mode
            assert mode.label in shown, mode
        assert 'name="interior_ink_mode"' in shown
        # The stored mode is the one that comes back checked.
        assert _checked_ink_mode(shown) == "bw"

    def test_choosing_colour_on_the_form_stores_it_and_comes_back_checked(
        self, panel
    ):
        book_id = panel.book()
        panel.submit_print_setup(book_id, interior_ink_mode="colour")

        assert book_ink_mode(panel.books.get_book(book_id)) is InkMode.COLOUR
        assert _checked_ink_mode(panel.print_setup(book_id)) == "colour"

    def test_a_submission_that_names_no_mode_keeps_the_stored_one(self, panel):
        """A client built before this card cannot flip a colour book."""
        book_id = panel.book()
        panel.submit_print_setup(book_id, interior_ink_mode="colour")
        panel.submit_print_setup(book_id, interior_ink_mode=None)
        assert book_ink_mode(panel.books.get_book(book_id)) is InkMode.COLOUR

    def test_an_unknown_mode_is_refused_and_stores_nothing(self, panel):
        book_id = panel.book()
        response = panel.submit_print_setup(book_id, interior_ink_mode="sepia")
        shown = response.get_data(as_text=True)
        assert response.status_code == 200, "refused in place, not redirected"
        assert "Interior ink mode must be" in shown
        assert book_ink_mode(panel.books.get_book(book_id)) is InkMode.BLACK_AND_WHITE
        assert panel.books.get_book(book_id).trim_width_cm == "21.59", (
            "a refused mode stores no trim either"
        )

    @pytest.mark.parametrize(
        "mode,label", [(InkMode.BLACK_AND_WHITE, "Black and white"), (InkMode.COLOUR, "Colour")]
    )
    def test_finalise_names_the_mode(self, panel, mode, label):
        book_id = panel.book()
        panel.submit_print_setup(book_id, interior_ink_mode=mode.value)
        shown = panel.finalise(book_id)
        assert f'data-interior-ink-mode="{mode.value}"' in shown
        assert "Interior ink" in shown
        assert label in shown

    def test_finalise_says_so_when_the_stored_mode_cannot_be_read(self, panel):
        """The posture the Trim size row already takes for an unreadable trim."""
        book_id = panel.book()
        panel.books.get_book(book_id).interior_ink_mode = "sepia"
        shown = panel.finalise(book_id)
        assert "Cannot be read — set it again on Print setup" in shown
        assert "data-interior-ink-mode" not in shown


def _checked_ink_mode(html: str) -> str:
    """Which interior-ink radio the rendered form came back with checked.

    Read off the markup rather than off the context, so what is asserted is
    what the owner's browser is given.
    """
    checked = [
        mode.value
        for mode in InkMode
        if f'id="ink_{mode.value}" value="{mode.value}"\n' in html
        and "checked" in html.split(f'id="ink_{mode.value}"', 1)[1].split(">", 1)[0]
    ]
    assert len(checked) == 1, f"expected one checked radio, found {checked}"
    return checked[0]


# --------------------------------------------------------------------------
# AC-5
# --------------------------------------------------------------------------


class TestBookInk_CoverIgnoresTheInteriorMode:
    """An uploaded colour cover stays colour on a black-and-white book (AC-5).

    The cover is a separate file (FR-043, CARD-135) holding an image the owner
    supplied, which may be anything; a colour cover on a black-and-white
    interior is the ordinary KDP case, not a mistake to correct. G-4 keeps the
    cover path out of this card's scope, so what is asserted is that the mode
    does not reach it.
    """

    @staticmethod
    def _colour_cover(width: int, height: int) -> Image.Image:
        """An unmistakably coloured cover: three bands no grey can imitate."""
        cover = Image.new("RGB", (width, height), (10, 20, 200))
        pixels = np.asarray(cover).copy()
        pixels[: height // 3] = (220, 30, 40)
        pixels[height // 3 : 2 * height // 3] = (30, 200, 60)
        return Image.fromarray(pixels, "RGB")

    def test_the_cover_file_of_a_black_and_white_book_is_devicergb(self):
        generator = BookPDFGenerator(book_on(InkMode.BLACK_AND_WHITE))
        assert generator.interior_bitmap_mode == "L", "the interior really is grey"

        cover = generator.export_cover(
            "Winter Pictures",
            self._colour_cover(generator.page_width_px, generator.page_height_px),
        ).getvalue()

        (page,) = pdf_image_objects(cover)
        assert page["colour_space"] == "DeviceRGB"
        assert page["procset"] == ["PDF", "ImageC"]
        assert page["image"].mode == "RGB"

    def test_the_cover_still_carries_colour(self):
        """Not merely declared RGB: the pixels are not grey."""
        generator = BookPDFGenerator(book_on(InkMode.BLACK_AND_WHITE))
        cover = generator.export_cover(
            "Winter Pictures",
            self._colour_cover(generator.page_width_px, generator.page_height_px),
        ).getvalue()

        pixels = np.asarray(pdf_image_objects(cover)[0]["image"], dtype=np.int16)
        spread = (
            pixels.max(axis=2) - pixels.min(axis=2)
        )  # 0 everywhere on a grey page
        assert spread.max() > 100, "the cover came out grey"
        assert float((spread > 20).mean()) > 0.5, "most of the cover lost its colour"

    def test_the_generated_title_cover_is_devicergb_too(self):
        """No uploaded image, and still the cover's own colour space."""
        generator = BookPDFGenerator(book_on(InkMode.BLACK_AND_WHITE))
        cover = generator.export_cover("Winter Pictures").getvalue()
        (page,) = pdf_image_objects(cover)
        assert page["colour_space"] == "DeviceRGB"
        assert page["image"].mode == "RGB"

    def test_export_book_writes_a_grey_interior_beside_a_colour_cover(self):
        """Both files of one export, each in its own colour space."""
        generator = BookPDFGenerator(book_on(InkMode.BLACK_AND_WHITE))
        export = generator.export_book(
            baseline_puzzles(),
            "Winter Pictures",
            self._colour_cover(generator.page_width_px, generator.page_height_px),
        )
        interior = export.interior.getvalue()
        cover = export.cover.getvalue()

        assert export.interior_page_count == BASELINE_PAGE_COUNT
        assert {page["colour_space"] for page in pdf_image_objects(interior)} == {
            "DeviceGray"
        }
        assert [page["colour_space"] for page in pdf_image_objects(cover)] == [
            "DeviceRGB"
        ]


# --------------------------------------------------------------------------
# EC-1
# --------------------------------------------------------------------------


def ec1_books(seed: int = 147) -> List[Dict[str, Any]]:
    """EC-1's corpus: books that differ in every way the mode must not touch.

    Trim, both side margins, the puzzle sizes, the clue depths, the tier runs
    and therefore the page count, the pairing verdicts and the answer-key
    packing all vary; the mode is the one thing held apart and applied twice to
    each book. Sizes and depths come from a seeded ``random.Random`` drawn in a
    fixed order, so the corpus is the same on every run and on every machine
    (no ``hypothesis`` — it is not in the dependency baseline).

    The trims are real KDP ones and two of them are not the Book 1 profile, so
    "the gutter, the origin and the cell do not depend on the mode" is asserted
    on sheets whose gutter, origin and cell genuinely differ from each other.
    """
    rng = random.Random(seed)
    trims = [
        ("21.59", "27.94", "1.27", "0.95"),  # CON-018's Book 1 profile
        ("15.24", "22.86", "1.27", "0.95"),  # 6 x 9 in
        ("20.32", "25.40", "1.59", "0.95"),  # 8 x 10 in, a wider gutter
        ("21.00", "29.70", "1.27", "0.64"),  # A4, the narrowest legal outside
    ]
    tier_runs = [
        ("easy", "easy"),
        ("easy", "easy", "medium"),
        ("medium", "hard"),
        ("easy", "medium", "hard"),
        ("hard", "hard", "hard"),
        ("easy", "easy", "medium", "medium", "hard"),
        ("medium",),
    ]

    books: List[Dict[str, Any]] = []
    for index in range(EC1_BOOKS):
        trim = trims[index % len(trims)]
        tiers = tier_runs[index % len(tier_runs)]
        puzzles = []
        for position, tier in enumerate(tiers, start=1):
            side = rng.choice((10, 12, 15, 18, 20, 25, 30))
            depth = rng.choice((3, 4, 5))
            if 2 * depth - 1 > side:
                depth = 3
            puzzles.append(
                _ec1_puzzle(f"card147-{index}-{position}", side, depth, tier, position)
            )
        books.append({"label": f"book {index} on {trim[0]}x{trim[1]} cm",
                      "trim": trim, "puzzles": puzzles})
    return books


def _ec1_puzzle(
    puzzle_id: str, side: int, depth: int, tier: str, number: int
) -> Dict[str, Any]:
    limit = 2 * depth - 1
    grid = [
        [x % 2 == 0 and x < limit and y % 2 == 0 and y < limit for x in range(side)]
        for y in range(side)
    ]
    found = clues.compute_clues(grid)
    return {
        "id": puzzle_id,
        "grid": grid,
        "clues_rows": [list(clue) for clue in found.rows],
        "clues_cols": [list(clue) for clue in found.columns],
        "width": side,
        "height": side,
        "puzzle_name": f"Picture {number}",
        "difficulty_tier": tier,
    }


def _ec1_book(trim, mode: InkMode) -> Book:
    width, height, gutter, outside = trim
    return Book(
        book_id="card-147-ec1",
        metadata=BookMetadata(
            title="EC-1",
            description="",
            theme="generic",
            target_audience="adults",
            size="",
            page_count=0,
        ),
        trim_width_cm=width,
        trim_height_cm=height,
        gutter_margin_cm=gutter,
        outside_margin_cm=outside,
        interior_ink_mode=mode.value,
    )


class TestBookInk_InkPositionsDoNotDependOnTheMode:
    """EC-1, as a property over a corpus: the mode changes the colour space only.

    *For any book and any mode, the set of inked pixel positions is identical;
    cell size, origin, gutter, rules, frame and page count do not depend on
    it.* Stated as a standing property, so it is verified over
    :data:`EC1_BOOKS` books that differ in trim, both side margins, puzzle
    sizes, clue depths, tier runs, pairing verdicts and page count — never on
    one book.

    Every claim is read off the written files and nothing is asked of the
    generator: the page count comes out of the PDF's page tree, the printed
    size out of each page's ``MediaBox`` (the only thing that says how large
    the raster is *printed*), and the ink out of the decoded pages. The two
    colour spaces are asserted to differ in the same loop, so a run in which
    both exports came out the same way cannot pass as agreement.

    The floor is an exact chain — ``checked >= EC1_BOOKS >= 12`` — and a
    second one on the pages compared, because fourteen one-page books would
    satisfy a book count and prove nothing. CARD-149's review found a floor
    that could not fail; this one can.
    """

    @pytest.fixture(scope="class")
    @classmethod
    def exports(cls):
        """Every corpus book's interior, both ways. Built once for the class."""
        built = []
        for entry in ec1_books():
            bw = export_of(
                BookPDFGenerator(_ec1_book(entry["trim"], InkMode.BLACK_AND_WHITE)),
                entry["puzzles"],
            )
            colour = export_of(
                BookPDFGenerator(_ec1_book(entry["trim"], InkMode.COLOUR)),
                entry["puzzles"],
            )
            built.append((entry["label"], bw, colour))
        return built

    def test_the_corpus_is_the_size_it_claims_and_varies(self, exports):
        assert len(exports) == EC1_BOOKS >= 12, f"the corpus shrank to {len(exports)}"
        page_counts = {pdf_page_count(bw) for _label, bw, _c in exports}
        assert len(page_counts) >= 4, (
            f"the corpus's books all have the same length ({page_counts}); a "
            "property over one page count is an example"
        )
        sizes = {
            tuple(pdf_image_objects(bw)[0]["image"].size)
            for _label, bw, _c in exports
        }
        assert len(sizes) >= 3, f"the corpus exercises only {len(sizes)} trims"

    def test_the_two_modes_agree_on_every_page_of_every_book(self, exports):
        from tests.helpers.page_ink import pdf_page_boxes

        books = 0
        pages = 0
        for label, bw, colour in exports:
            grey_pages = pdf_image_objects(bw)
            colour_pages = pdf_image_objects(colour)

            # The page count is the file's own, read out of its page tree.
            assert pdf_page_count(bw) == pdf_page_count(colour) == len(grey_pages), label
            assert len(grey_pages) == len(colour_pages), label

            # The printed size of every page, in PDF points.
            assert pdf_page_boxes(bw) == pdf_page_boxes(colour), label

            for number, (g, c) in enumerate(
                zip(grey_pages, colour_pages, strict=True), start=1
            ):
                # The modes really did differ on this page ...
                assert g["colour_space"] == "DeviceGray", f"{label} page {number}"
                assert c["colour_space"] == "DeviceRGB", f"{label} page {number}"
                assert g["image"].mode == "L" and c["image"].mode == "RGB"

                # ... and the ink is in exactly the same places.
                assert g["image"].size == c["image"].size, f"{label} page {number}"
                grey_ink, colour_ink = ink_mask(g["image"]), ink_mask(c["image"])
                assert np.array_equal(grey_ink, colour_ink), (
                    f"{label} page {number}: {int(np.logical_xor(grey_ink, colour_ink).sum())} "
                    "pixels of ink moved with the mode"
                )
                assert np.array_equal(
                    grey_levels(g["image"]), grey_levels(c["image"])
                ), f"{label} page {number}: a grey level moved with the mode"
                assert int(grey_ink.sum()) > 0, f"{label} page {number} has no ink"
                pages += 1
            books += 1

        assert books == EC1_BOOKS >= 12, f"only {books} books compared"
        assert pages >= EC1_PAGES >= 110, f"only {pages} pages compared"

    def test_the_mode_never_reaches_the_sheet(self):
        """The other half of EC-1: ``PageSpec`` does not carry the mode at all.

        The geometry is built by ``book_page_spec`` from the stored trim and
        margins, so two books differing only in their ink mode produce the
        *same object*. Asserted on the spec rather than on a page, because that
        is where a mode leaking into the geometry would first show (ADR-0036/R1).
        """
        for entry in ec1_books():
            grey = BookPDFGenerator(_ec1_book(entry["trim"], InkMode.BLACK_AND_WHITE))
            colour = BookPDFGenerator(_ec1_book(entry["trim"], InkMode.COLOUR))
            for page_number in (1, 2, 7):
                assert grey.page_spec(page_number) == colour.page_spec(page_number)
            assert (grey.page_width_px, grey.page_height_px) == (
                colour.page_width_px,
                colour.page_height_px,
            )
            assert grey.interior_bitmap_mode != colour.interior_bitmap_mode

    def test_the_page_plan_is_the_same_plan(self):
        """Page count, pairing and the packed key are decided without the mode.

        ``interior_stream`` settles all three before a pixel exists, so the
        cheapest place to see a mode leaking into them is there — and it costs
        no drawing, which is what makes the whole corpus affordable here.
        """
        checked = 0
        for entry in ec1_books():
            grey = BookPDFGenerator(
                _ec1_book(entry["trim"], InkMode.BLACK_AND_WHITE)
            ).interior_stream(entry["puzzles"])
            colour = BookPDFGenerator(
                _ec1_book(entry["trim"], InkMode.COLOUR)
            ).interior_stream(entry["puzzles"])
            assert grey.page_count == colour.page_count, entry["label"]
            assert grey.unpaired_page_count == colour.unpaired_page_count, entry["label"]
            assert grey.answer_page_count == colour.answer_page_count, entry["label"]
            checked += 1
        assert checked == EC1_BOOKS >= 12, f"only {checked} books compared"


# --------------------------------------------------------------------------
# The panel
# --------------------------------------------------------------------------


@pytest.fixture
def panel(monkeypatch):
    """The admin panel in memory mode, with a book store of its own."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.setattr(
        book_manager_module, "_book_manager", BookManager(session_factory=None)
    )
    from nonogram.admin.app import create_app

    app = create_app()
    app.config["TESTING"] = True
    return Panel(app)


class Panel:
    """A panel, one book on it, and the two screens AC-4 is about."""

    def __init__(self, app):
        self.app = app
        self.client = app.test_client()
        self.books = app.book_manager
        self.store = app.puzzle_review_service

    def book(self, title: str = "Winter") -> str:
        """A draft book holding two puzzles, on a plan the gate accepts."""
        book_id = self.books.create_book(title, "a book", "generic", "adults")
        records = [
            dict(_ec1_puzzle(str(uuid.uuid4()), 15, 4, "easy", 1), status="approved", book_id=None),
            dict(_ec1_puzzle(str(uuid.uuid4()), 15, 4, "medium", 2), status="approved", book_id=None),
        ]
        for record in records:
            self.store.puzzles[record["id"]] = record
        self.books.add_puzzles_to_book(book_id, [r["id"] for r in records])
        self.books.save_plan(book_id, _plan_of(records))
        return book_id

    def print_setup(self, book_id: str) -> str:
        response = self.client.get(f"/book/{book_id}/setup-print")
        assert response.status_code == 200, response.status_code
        return response.get_data(as_text=True)

    def submit_print_setup(self, book_id: str, *, interior_ink_mode, **extra):
        data = {"unit": "cm", "width": "21.59", "height": "27.94", **extra}
        if interior_ink_mode is not None:
            data["interior_ink_mode"] = interior_ink_mode
        return self.client.post(f"/book/{book_id}/setup-print", data=data)

    def finalise(self, book_id: str) -> str:
        response = self.client.get(f"/book/{book_id}/finalize")
        assert response.status_code == 200, response.status_code
        return response.get_data(as_text=True)

    def download_interior(self, book_id: str) -> bytes:
        """The interior PDF Finalise's own button posts for (FR-043)."""
        response = self.client.post(
            f"/book/{book_id}/finalize",
            data={"action": "download_pdf", "part": "interior"},
        )
        assert response.status_code == 200, response.status_code
        assert response.mimetype == "application/pdf"
        return response.get_data()


def _plan_of(records) -> DistributionPlan:
    """A plan whose matrix is this selection, so the readiness gate is silent."""
    count = len(records)
    cells = [[0] * len(TIERS) for _ in BUCKETS]
    for record in records:
        bucket = bucket_of(record["width"], record["height"])
        tier = next(t for t in TIERS if t.value == record["difficulty_tier"])
        cells[BUCKETS.index(bucket)][TIERS.index(tier)] += 1
    matrix = tuple(tuple(row) for row in cells)
    columns = tuple(sum(row[t] for row in cells) for t in range(len(TIERS)))
    rounded = [round(100 * column / count) for column in columns]
    rounded[0] += 100 - sum(rounded)
    for easy, medium, hard in [tuple(rounded)] + [
        (e, m, 100 - e - m) for e in range(101) for m in range(101 - e)
    ]:
        candidate = DistributionPlan(
            count=count, split=Split(easy, medium, hard), cells=matrix
        )
        if not candidate.disagrees_with_split:
            return candidate
    raise AssertionError("no split agrees with this selection")
