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
(``_CLUE_FONT_RATIO``), and INV-006's 4.8 mm cell floor puts them at 8.4 pt, so
no setting reaches 10 pt there without breaking the cell floor. They are
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
from PIL import ImageDraw, ImageFont

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

#: The level names an answer page's heading prints (FR-042).
LEVEL_NAMES = frozenset({"Easy", "Medium", "Hard"})

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
#: eleven (``BASELINE_PAGE_COUNT``); the 10x10 cm trim packs its answer key
#: onto one more page.
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
        if self.caller[1] == "render_answer_page":
            return "answer heading" if self.text in LEVEL_NAMES else "answer caption"
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
    """Every ``draw.text`` call one interior export makes, tagged by page."""
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


def without_arial(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make ``ImageFont.truetype`` fail for the Arial path, and only that path."""
    original = ImageFont.truetype

    def truetype(font=None, *args, **kwargs):
        if str(font) == ARIAL_PATH:
            raise OSError(f"cannot open resource {font}")
        return original(font, *args, **kwargs)

    monkeypatch.setattr(ImageFont, "truetype", truetype)


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
        kinds = {call.kind for call in recording(book, arial=True)}
        assert {
            "guide",
            "divider",
            "band",
            "answer heading",
            "answer caption",
        } <= kinds


# --------------------------------------------------------------------------
# AC-2
# --------------------------------------------------------------------------


class TestInteriorType_FloorHoldsWithoutArial:
    """AC-2 — with Arial unavailable, no face is unsized and the floor holds."""

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
        assert len(dividers) == 4  # three levels and SOLUTIONS


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
    """AC-4 — the divider is 14.4 pt at 300 DPI and at 600 DPI."""

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

    def test_the_divider_is_the_same_size_in_points_at_300_and_600_dpi(self, monkeypatch):
        at_300 = self.divider_points(300, monkeypatch)
        at_600 = self.divider_points(600, monkeypatch)
        assert at_300 == pytest.approx([DIVIDER_PT])
        assert at_600 == pytest.approx([DIVIDER_PT])
