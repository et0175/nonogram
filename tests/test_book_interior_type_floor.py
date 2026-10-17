"""Every face the book's interior draws holds CON-020's 10 pt floor (CARD-184).

CON-020: no text the interior prints for the reader is set below 10 pt at the
page's own resolution. Until this card only the guide page was tested against
it (CARD-149, CARD-167); this module walks **every** ``draw.text`` call one
interior export makes.

**Why a spy on ``ImageDraw.text``, and not on the font constructors.**
``_band_font``, ``png._lettering_font`` and ``pdf._header_font`` are
``lru_cache``d, so a spy on ``ImageFont.truetype`` misses every size an earlier
test already asked for. What is *drawn* is what the reader sees, and spying
there also leaves out the guide title's fitting probes, which are measured and
never drawn.

Each recorded call carries the font's size in pixels (``font.size``), or
``None`` — "unsized" — when the font is not a ``FreeTypeFont`` or is the face a
sizeless ``ImageFont.load_default()`` returned during the walk (on Pillow
>= 10.1 that face *is* a ``FreeTypeFont``, at a 10 px em); the chain of
functions that called it; and the interior page it was drawn for. A size in
points is ``size * 72 / generator.dpi``. An unsized face always fails.

**The one exemption.** A puzzle page's clue digits are bound to their cell
(``_CLUE_FONT_RATIO``), and INV-006's cell floor puts them at 8.4 pt, so
no setting reaches 10 pt there without breaking the cell floor. The floor
is **4.75 mm since NFR-008's amendment of 2026-10-17** (CARD-222) and was
4.8 mm before it; the 8.4 pt is unchanged by that move, because at 300 dpi
both floors round ``pitch * _CLUE_FONT_RATIO`` to the same 35 px. They are
exempt **by the function that draws them**: ``png._draw_clues`` and
``book_pdf_generator._write_clues``. The guide page's worked example draws its
clue digits through ``_write_clues`` too, from inside ``draw_example_line``;
those are the reader's instruction text and are **never** exempt, so a call
with ``draw_example_line`` anywhere in its chain is held to the floor.

AC-1..AC-4 of CARD-184, one class each.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import pytest
from PIL import Image, ImageDraw, ImageFont

from nonogram.admin import book_pdf_generator
from nonogram.admin.book_manager import Book, BookMetadata
from nonogram.admin.book_pdf_generator import BookPDFGenerator

from tests.helpers.book_corpus import BASELINE_PAGE_COUNT, baseline_puzzles, corpus_book

# --------------------------------------------------------------------------
# What the acceptance criteria ask for, written out rather than imported
# --------------------------------------------------------------------------

#: CON-020's floor, in points.
FLOOR_PT = 10.0

#: A point is 1/72 in.
POINTS_PER_INCH = 72.0

#: The divider's size, in points (AC-4): the 60 px it was at 300 DPI.
DIVIDER_PT = 14.4

#: CARD-200: the folio's own size, in points — CON-020's floor exactly
#: (``book_pdf_generator.FOLIO_PT``), written out rather than imported so
#: this file's own independent statement of every interior face's size
#: stays independent.
FOLIO_PT = 10.0

#: The path the interior asks Pillow for Arial at (AC-2 makes it fail).
ARIAL_PATH = "/System/Library/Fonts/Arial.ttf"

#: The functions whose ``draw.text`` calls are puzzle-page clue digits
#: (AC-3), as ``(module, function)``.
EXEMPT_CALLERS = frozenset(
    {
        ("nonogram.export.png", "_draw_clues"),
        ("nonogram.admin.book_pdf_generator", "_write_clues"),
    }
)

#: A call made from inside this function is the guide page's worked example,
#: never exempt (AC-3).
WORKED_EXAMPLE = "draw_example_line"

#: The functions that letter a puzzle page's band: the two-up page's own
#: setter, and COMP-007's header for a page that prints one puzzle alone.
BAND_SETTERS = frozenset(
    {
        ("nonogram.admin.book_pdf_generator", "_set_band"),
        ("nonogram.export.pdf", "_draw_header"),
    }
)

#: CARD-222's footer line: the grid-size label, the one face the frame adds.
#: It is set at ``SIZE_LABEL_PT``, which reads COMP-007's own
#: ``INTERIOR_FOOTER_LINE_PT`` — the floor again — and the folio beside it is
#: CARD-200's, drawn by ``_draw_folio`` and already covered.
FOOTER_LABEL_SETTER = ("nonogram.admin.book_pdf_generator", "_draw_page_frame")

#: CARD-198 note: FR-042's level headings are gone (the packed key that
#: drew them no longer exists), so there is no "answer heading" kind any
#: longer — only the caption :meth:`BookPDFGenerator.solved_puzzle_page`
#: draws directly, tagged below by that caller.
#:
#: CARD-202 note (SCOPE+): the caption's own ``draw.text`` call moved from
#: ``solved_puzzle_page``'s body into a new shared helper,
#: ``BookPDFGenerator._draw_solved_slot`` — both a full answer page and a
#: packed slot draw their caption through it now (reuse, not reinvention;
#: see that method's own docstring). The immediate caller the spy sees is
#: therefore ``_draw_solved_slot`` on every page, full or packed, which is
#: why :attr:`TextCall.kind` below checks for either name: the two calls are
#: the same kind of caption either way, and the old name is kept in the
#: check (rather than dropped) only because nothing here requires removing it.

#: The smallest trim a book may be stored with
#: (``book_page_spec.MIN_TRIM_CM``), written out rather than imported, and the
#: margins the 10x10 cm book was measured on when the card was drafted.
MIN_TRIM_CM = 10.0
MIN_TRIM_GUTTER_CM = "0.95"
MIN_TRIM_OUTSIDE_CM = "0.64"


def min_trim_book() -> Book:
    """The baseline book's print specification at the 10x10 cm minimum trim."""
    return Book(
        book_id="card-184-min-trim",
        metadata=BookMetadata(
            title="Winter Pictures",
            description="The book CARD-184's type-floor test draws.",
            theme="generic",
            target_audience="adults",
            size="",
            page_count=0,
        ),
        trim_width_cm=f"{MIN_TRIM_CM:.2f}",
        trim_height_cm=f"{MIN_TRIM_CM:.2f}",
        gutter_margin_cm=MIN_TRIM_GUTTER_CM,
        outside_margin_cm=MIN_TRIM_OUTSIDE_CM,
    )


BOOKS = {"book1": corpus_book, "min-trim": min_trim_book}

#: How many interior pages each book's export of the baseline puzzles draws,
#: asserted so the walk cannot silently shrink. Book 1 is the baseline book's
#: own count (``BASELINE_PAGE_COUNT``); the 10x10 cm trim's tighter sheet
#: changes what the puzzle section's pairing walk can fit, one page longer.
PAGE_COUNTS = {"book1": BASELINE_PAGE_COUNT, "min-trim": BASELINE_PAGE_COUNT + 1}


@pytest.fixture(params=sorted(BOOKS))
def book(request) -> str:
    """Book 1, and the same book at the 10x10 cm minimum trim."""
    return request.param

# --------------------------------------------------------------------------
# The spy
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class TextCall:
    """One ``draw.text`` call, as the spy saw it."""

    page: int
    text: str
    size_px: Optional[int]  # None: the font is not a FreeTypeFont (unsized)
    chain: Tuple[Tuple[str, str], ...]  # (module, function), innermost first
    dpi: int

    @property
    def caller(self) -> Tuple[str, str]:
        return self.chain[0]

    @property
    def caller_names(self) -> frozenset:
        return frozenset(name for _, name in self.chain)

    @property
    def points(self) -> Optional[float]:
        if self.size_px is None:
            return None
        return self.size_px * POINTS_PER_INCH / self.dpi

    @property
    def exempt(self) -> bool:
        return self.caller in EXEMPT_CALLERS and WORKED_EXAMPLE not in self.caller_names

    @property
    def kind(self) -> str:
        names = self.caller_names
        if "create_guide_page" in names:
            return "guide"
        if "create_divider_page" in names:
            return "divider"
        if self.caller in BAND_SETTERS:
            return "band"
        if self.caller == FOOTER_LABEL_SETTER:
            return "footer label"
        if self.caller[1] in ("solved_puzzle_page", "_draw_solved_slot"):
            return "answer caption"
        return "other"

    def describe(self) -> str:
        size = "unsized" if self.size_px is None else f"{self.size_px} px = {self.points:.2f} pt"
        where = " <- ".join(f"{module}.{name}" for module, name in self.chain[:3])
        return f"page {self.page} {self.kind} {self.text!r}: {size} ({where})"


def _call_chain(frame: Any) -> Tuple[Tuple[str, str], ...]:
    """The ``nonogram`` functions on the stack above ``frame``, innermost first."""
    chain: List[Tuple[str, str]] = []
    while frame is not None:
        module = frame.f_globals.get("__name__", "")
        if module.startswith("nonogram."):
            chain.append((module, frame.f_code.co_name))
        frame = frame.f_back
    return tuple(chain)


def record_interior(
    generator: BookPDFGenerator, monkeypatch: pytest.MonkeyPatch, page_count: int
) -> List[TextCall]:
    """Every ``draw.text`` call one interior export makes, tagged by page.

    Starts by emptying the module's font caches (:func:`clear_font_caches`),
    so that each recording loads the faces its own configuration resolves
    to rather than inheriting the previous recording's.
    """
    clear_font_caches()
    original = ImageDraw.ImageDraw.text
    original_default = ImageFont.load_default
    calls: List[TextCall] = []
    current = {"page": 0}
    # Faces a sizeless ``load_default()`` returned. On Pillow >= 10.1 that is
    # a FreeTypeFont at a 10 px em, so ``isinstance`` alone cannot tell it
    # from a face that was asked for at 10 px; the faces are kept alive so an
    # ``id`` is never reused for another face during the walk.
    sizeless: List[Any] = []

    def load_default(size=None):
        face = original_default() if size is None else original_default(size)
        if size is None:
            sizeless.append(face)
        return face

    def spy(self, xy, text, fill=None, font=None, *args, **kwargs):
        face = font if font is not None else self.getfont()
        sized = isinstance(face, ImageFont.FreeTypeFont) and not any(
            face is seen for seen in sizeless
        )
        size = face.size if sized else None
        calls.append(
            TextCall(current["page"], str(text), size, _call_chain(sys._getframe(1)), generator.dpi)
        )
        return original(self, xy, text, fill, font, *args, **kwargs)

    monkeypatch.setattr(ImageFont, "load_default", load_default)
    monkeypatch.setattr(ImageDraw.ImageDraw, "text", spy)
    stream = generator.interior_stream(baseline_puzzles())
    pages = iter(stream.pages)
    drawn = 0
    while True:
        current["page"] = drawn + 1
        try:
            next(pages)
        except StopIteration:
            break
        drawn += 1
    monkeypatch.setattr(ImageDraw.ImageDraw, "text", original)
    monkeypatch.setattr(ImageFont, "load_default", original_default)
    assert drawn == stream.page_count == page_count
    return calls


def clear_font_caches() -> None:
    """Empty ``book_pdf_generator``'s two font caches.

    ``_band_font`` is an ``lru_cache(maxsize=8)`` over ``(size,)`` and
    ``_band_font_bytes`` an ``lru_cache(maxsize=1)``, so a face loaded under
    one font configuration is handed straight back under the next one in the
    same process — and this file records two configurations per book, in one
    process, with ``arial=True`` always first (:func:`recording`).

    **Added by CARD-221 fix 5, because the blindness was demonstrated rather
    than suspected.** The AC/EC/G gate put a host Arial lookup with a
    *sizeless* ``load_default()`` fallback — the CARD-149 defect verbatim —
    inside ``_band_font`` and this whole file stayed green, 21 passed, while
    killing 3 tests when ``TestInteriorType_FloorHoldsWithoutArial`` ran
    alone in a cold process. The warmed cache was the difference. Until it
    was cleared, that class's own claim to be "what fails first if a host
    lookup returns to the drawing" was false of the suite as it actually
    runs.
    """
    book_pdf_generator._band_font.cache_clear()
    book_pdf_generator._band_font_bytes.cache_clear()


def without_arial(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make ``ImageFont.truetype`` fail for the Arial path, and only that path.

    Clears the font caches on the way in (:func:`clear_font_caches`): a face
    cached while Arial was available is not a measurement of a machine
    without it.
    """
    original = ImageFont.truetype

    def truetype(font=None, *args, **kwargs):
        if str(font) == ARIAL_PATH:
            raise OSError(f"cannot open resource {font}")
        return original(font, *args, **kwargs)

    monkeypatch.setattr(ImageFont, "truetype", truetype)
    clear_font_caches()


_RECORDINGS: Dict[Tuple[str, bool], List[TextCall]] = {}


def recording(book: str, arial: bool) -> List[TextCall]:
    """The recorded calls of ``book``'s interior, with or without Arial; once each."""
    key = (book, arial)
    if key not in _RECORDINGS:
        with pytest.MonkeyPatch.context() as monkeypatch:
            if not arial:
                without_arial(monkeypatch)
            _RECORDINGS[key] = record_interior(
                BookPDFGenerator(BOOKS[book]()), monkeypatch, PAGE_COUNTS[book]
            )
    return _RECORDINGS[key]


def below_floor(calls: List[TextCall]) -> List[str]:
    """Every non-exempt call that is unsized or below the floor, described."""
    return [
        call.describe()
        for call in calls
        if not call.exempt and (call.points is None or call.points < FLOOR_PT)
    ]


# --------------------------------------------------------------------------
# AC-1
# --------------------------------------------------------------------------


class TestInteriorType_EveryFaceHoldsTheFloor:
    """AC-1 — every drawn face outside the exemption is at least 10 pt."""

    def test_every_face_outside_the_exemption_is_at_least_ten_points(self, book):
        assert below_floor(recording(book, arial=True)) == []

    def test_the_recording_covers_every_kind_of_interior_lettering(self, book):
        """CARD-198: "answer heading" is gone — there is no level heading
        left to draw inside the answer section at all. "answer caption" is
        also not required on ``min-trim``: CARD-197's AC-6 omits the caption
        rather than overlap the drawing when the trim leaves no slack for
        it, which the 10x10 cm book genuinely does not.
        """
        kinds = {call.kind for call in recording(book, arial=True)}
        required = {"guide", "divider", "band"}
        if book != "min-trim":
            # CARD-222's footer line. Not on ``min-trim``: no page of that
            # book frees its footer strip (that file's own measurement), so
            # the group — label included — is omitted there.
            required.add("footer label")
        if book != "min-trim":
            required.add("answer caption")
        assert required <= kinds


# --------------------------------------------------------------------------
# AC-2
# --------------------------------------------------------------------------


class TestInteriorType_FloorHoldsWithoutArial:
    """AC-2 — with Arial unavailable, no face is unsized and the floor holds.

    **Deliberately redundant since CARD-221** (its review cycle 1, F-007).
    That card made ``_guide_face`` return the packaged face on every host,
    so ``without_arial`` can no longer change anything the interior draws:
    every assertion below now measures the same recording as
    :class:`TestInteriorType_EveryFaceHoldsTheFloor` above, and this class
    passes for a reason it no longer tests.

    It is kept rather than retired, as insurance of the cheapest kind: it
    costs one extra export per book and it is the test that fails first if
    a host lookup ever comes back into the interior — including one that
    CARD-221's own structural watch would miss, since that watch
    (``tests/test_book_interior_face.py``'s
    ``TestInteriorFace_NoFaceIsReadFromAHostPath``) looks at
    ``ImageFont.truetype``'s argument while this one looks at what was
    actually drawn. ``test_arial_really_is_unavailable`` below is still a
    real test of the helper, not of the interior.

    The claim this class can no longer make on its own is "the floor holds
    on a machine without Arial **because this run had none**" — that one
    moved to ``tests/test_book_interior_face.py``, which exports the same
    books twice and compares them. Read the two together.
    """

    def test_arial_really_is_unavailable(self):
        with pytest.MonkeyPatch.context() as monkeypatch:
            without_arial(monkeypatch)
            with pytest.raises(OSError):
                ImageFont.truetype(ARIAL_PATH, 60)

    def test_no_face_is_unsized(self, book):
        unsized = [call.describe() for call in recording(book, arial=False) if call.size_px is None]
        assert unsized == []

    def test_every_face_outside_the_exemption_is_at_least_ten_points(self, book):
        assert below_floor(recording(book, arial=False)) == []

    def test_the_dividers_are_drawn(self, book):
        dividers = [call for call in recording(book, arial=False) if call.kind == "divider"]
        # Three levels and SOLUTIONS, two draw.text calls each since
        # CARD-200 (the word, then the folio sharing its bottom-outer
        # corner — both carry "create_divider_page" in their call chain,
        # so both are tagged "divider" by `TextCall.kind`).
        assert len(dividers) == 8


# --------------------------------------------------------------------------
# AC-3
# --------------------------------------------------------------------------


class TestInteriorType_OnlyPuzzleClueDigitsAreExempt:
    """AC-3 — only puzzle-page clue digits are exempt, and they are exercised."""

    def test_the_exempt_set_is_non_empty(self, book):
        assert [call for call in recording(book, arial=True) if call.exempt]

    def test_only_the_two_clue_writers_are_exempt(self, book):
        callers = {call.caller for call in recording(book, arial=True) if call.exempt}
        assert callers <= EXEMPT_CALLERS

    def test_exempt_calls_are_puzzle_page_digits(self, book):
        exempt = [call for call in recording(book, arial=True) if call.exempt]
        assert all(call.text.isdigit() for call in exempt)
        assert all(call.kind == "other" for call in exempt)

    def test_worked_example_digits_are_drawn_and_never_exempt(self, book):
        example = [
            call for call in recording(book, arial=True) if WORKED_EXAMPLE in call.caller_names
        ]
        assert example, "the guide page's worked example drew no text"
        assert not any(call.exempt for call in example)

    def test_the_exemption_rule_by_name(self):
        def call(*chain: Tuple[str, str]) -> TextCall:
            return TextCall(1, "3", 10, tuple(chain), 300)

        png = ("nonogram.export.png", "_draw_clues")
        writer = ("nonogram.admin.book_pdf_generator", "_write_clues")
        example = ("nonogram.admin.book_pdf_generator", WORKED_EXAMPLE)
        assert call(png).exempt
        assert call(writer).exempt
        assert not call(writer, example).exempt
        assert not call(example).exempt
        assert not call(("nonogram.export.png", "render_answer_page")).exempt


# --------------------------------------------------------------------------
# AC-4
# --------------------------------------------------------------------------


class TestDividerPage_PointSizeIsIndependentOfDpi:
    """AC-4 — the divider is 14.4 pt at 300 DPI and at 600 DPI.

    CARD-200 (SCOPE+): a divider page now draws two faces, not one — its
    own word, then the folio sharing its bottom-outer corner — so this
    test's own spy now expects two sizes, in the order they are drawn, not
    one.
    """

    @staticmethod
    def divider_points(dpi: int, monkeypatch: pytest.MonkeyPatch) -> List[float]:
        monkeypatch.setattr(book_pdf_generator, "DPI", dpi)
        generator = BookPDFGenerator(corpus_book())
        assert generator.dpi == dpi
        sizes: List[Optional[int]] = []
        original = ImageDraw.ImageDraw.text

        def spy(self, xy, text, fill=None, font=None, *args, **kwargs):
            sizes.append(font.size if isinstance(font, ImageFont.FreeTypeFont) else None)
            return original(self, xy, text, fill, font, *args, **kwargs)

        with monkeypatch.context() as patch:
            patch.setattr(ImageDraw.ImageDraw, "text", spy)
            generator.create_divider_page(2, "Easy")
        assert sizes and None not in sizes
        return [size * POINTS_PER_INCH / dpi for size in sizes]

    @staticmethod
    def _expected_folio_pt(dpi: int) -> float:
        """:data:`FOLIO_PT` round-tripped through whole device pixels.

        Unlike :data:`DIVIDER_PT` (14.4 pt is exactly 60 px at 300 DPI, no
        rounding), 10.0 pt rounds to 42 px at 300 DPI — 10.08 pt, not 10.0 —
        so the independent expectation here is the same whole-pixel rounding
        :func:`~nonogram.admin.book_pdf_generator.type_px` performs, written
        out rather than imported, not a loosened tolerance.
        """
        return round(FOLIO_PT * dpi / POINTS_PER_INCH) * POINTS_PER_INCH / dpi

    def test_the_divider_is_the_same_size_in_points_at_300_and_600_dpi(self, monkeypatch):
        at_300 = self.divider_points(300, monkeypatch)
        at_600 = self.divider_points(600, monkeypatch)
        assert at_300 == pytest.approx([DIVIDER_PT, self._expected_folio_pt(300)])
        assert at_600 == pytest.approx([DIVIDER_PT, self._expected_folio_pt(600)])


class TestInteriorType_DifficultyDotsAreNotText:
    """CARD-228 (G-2): the difficulty glyph is ink, not type, so the floor misses it.

    CON-020 is a rule about *text*, and ``TestInteriorType_EveryFaceHoldsTheFloor``
    above enforces it by spying on ``draw.text``. CARD-228's three dots are
    drawn as circles, so that spy does not see them — and the card says it
    should not (guardrail G-2: the dots are not text; the **word** beside them
    is, and is held to the floor by its own caller).

    A guardrail no test can falsify is worth nothing, so both halves of that
    sentence are measured here rather than asserted in a docstring:

    * the glyph makes **no** ``draw.text`` call at all, so the floor cannot
      reach it *and* nothing can evade the floor by hiding a caption inside
      it (a dot drawn as a "•" glyph at 6 pt would be exactly that);
    * the spy that sees nothing here is the same spy that *does* see the
      word, which is the control — without it, "no text calls" could equally
      mean the spy was broken.
    """

    BOX = (0, 0, 999, 141)

    @staticmethod
    def _text_sizes(draw_something) -> List[Optional[int]]:
        """Every ``draw.text`` size ``draw_something`` asks for, in order."""
        sizes: List[Optional[int]] = []
        original = ImageDraw.ImageDraw.text

        def spy(self, xy, text, fill=None, font=None, *args, **kwargs):
            sizes.append(font.size if isinstance(font, ImageFont.FreeTypeFont) else None)
            return original(self, xy, text, fill, font, *args, **kwargs)

        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(ImageDraw.ImageDraw, "text", spy)
            draw_something()
        return sizes

    def _page(self):
        page = Image.new("RGB", (self.BOX[2] + 1, self.BOX[3] + 1), "white")
        return page, ImageDraw.Draw(page)

    def test_the_glyph_sets_no_type_at_all(self):
        page, draw = self._page()
        drawn: List[object] = []

        def draw_dots():
            drawn.append(
                book_pdf_generator._draw_difficulty_dots(draw, "medium", *self.BOX)
            )

        assert self._text_sizes(draw_dots) == []
        assert drawn[0] is not None, "the glyph must have drawn, or this proves nothing"

    def test_the_spy_does_see_the_word_beside_them(self):
        """The control: the same spy, on the band line the glyph sits beside."""
        page, draw = self._page()
        band = book_pdf_generator.HeaderBand(
            height=self.BOX[3] + 1,
            center_x=(self.BOX[0] + self.BOX[2]) // 2,
            center_y=(self.BOX[1] + self.BOX[3]) // 2,
            font_size=book_pdf_generator.type_px(FLOOR_PT, 300),
        )

        def draw_word():
            book_pdf_generator._set_band(draw, band, "Puzzle 12 · Medium", self.BOX[2] + 1)

        sizes = self._text_sizes(draw_word)
        assert len(sizes) == 1
        assert sizes[0] is not None
        assert sizes[0] * POINTS_PER_INCH / 300 >= FLOOR_PT
