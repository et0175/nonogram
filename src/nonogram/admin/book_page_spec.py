"""The book's :class:`~nonogram.export.layout.PageSpec`, built from its stored print specification.

COMP-009's one door onto COMP-007's book geometry (FR-030, ADR-0036). Every
book-side caller — the book PDF, the proof pages, the floor tile, the two-up
pairing — builds its sheet here and measures a puzzle's cell with
:func:`book_cell_mm`, so that "the cell a puzzle gets in this book" is one
computation (EC-021).

* :data:`BOOK1_PROFILE` is CON-018: trim 8.5 x 11 in, gutter 0.5 in, outside,
  top and bottom 0.375 in, no bleed, the 12 mm title band (TERM-028). It is
  stated once, in inches, and both forms callers need are derived from that:
  the exact millimetres a :class:`PageSpec` takes, and the two-decimal
  centimetre strings the ``books`` table stores.
* :func:`book_page_spec` reads a book's ``trim_width_cm``/``trim_height_cm``
  and ``gutter_margin_cm``/``outside_margin_cm``. An empty or missing value
  falls back to the profile (CON-018; AC-178's builder half). Top and bottom
  have no column and always come from the profile. The sheet is portrait-only,
  has NFR-008's flat 7.5 mm cap and ADR-0037/R2's 0.25 mm thin-rule minimum,
  and carries the page's parity (ADR-0036, "Mirrored margins").
* :func:`book_cell_mm` converts ``compute_layout``'s result and does nothing
  else. **The admin panel fits no cell and places no grid line itself**
  (ADR-0036/R2): the exact cell is ``Layout.page.cell_mm``, which layout
  computes in millimetres; re-deriving it from the pixel ``Layout.cell`` would
  round it (4.57 mm instead of 4.61 mm for a 12-deep 30-wide grid).
* :data:`FLOOR_MM` is NFR-008's other end of the same band (TERM-024): the
  4.8 mm below which a puzzle joins a book only with a stored override
  (FR-031, INV-006 — enforced in ``BookManager``, which is where membership
  is written).

**The profile's stored form.** 0.375 in is 0.9525 cm, which a two-decimal
column stores as ``"0.95"``. A stored value that *is* the profile's own storage
form therefore means the profile's exact value (9.525 mm), not 9.5 mm; any
other stored value is read as the centimetres it says. That keeps "a book
created on the profile" and "a legacy book whose margins are empty" the same
sheet to the last micrometre (AC-178, AC-272, AC-273).

How the interior is printed (CARD-147)
--------------------------------------
:class:`InkMode` is the second thing a book stores about how it is *printed*
rather than about how it is *laid out*: **black-and-white** or **colour**, kept
in ``books.interior_ink_mode`` beside the trim and the margins and read back by
:func:`book_ink_mode`. It is owner intake
(``meta/architecture/inputs/raw-requirements.md``, 2026-09-25) and not a
formalised requirement; there is deliberately no FR to cite for it.

It is **not geometry**, and ADR-0036/R1 is untouched by it: no page's size,
margin, cell, rule, stroke or count depends on it, and :class:`PageSpec` never
carries it. What it decides is exactly one thing — the colour space the
interior's pages are composed and written in — so it lives here, beside the
other readers of the book's stored print specification, and travels no further
than ``book_pdf_generator``'s page writer.

An empty or missing column is :data:`DEFAULT_INK_MODE`, black-and-white, which
is every book that existed before the column did: their interiors have no
colour in them at all (``export/png.py`` draws one ink on one background), and
a file that *declares* colour invites the expensive print classification for a
book that has none. A stored value that is neither of the two is refused the
way a non-numeric margin is, naming the column — it is not quietly read as one
of them.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum

from nonogram.export.layout import (
    OrientationPolicy,
    PageParity,
    PageSpec,
    compute_layout,
)

__all__ = [
    "BOOK1_PROFILE",
    "DEFAULT_INK_MODE",
    "FLOOR_MM",
    "INK_MODE_COLUMN",
    "InkMode",
    "MAX_TRIM_HEIGHT_CM",
    "MAX_TRIM_WIDTH_CM",
    "MIN_SIDE_MARGIN_MM",
    "MIN_TRIM_CM",
    "PrintProfile",
    "book_cell_mm",
    "book_ink_mode",
    "book_page_spec",
    "ink_mode_from_stored",
]

_MM_PER_INCH = Decimal("25.4")
_CM_PER_INCH = Decimal("2.54")

#: Amazon KDP's trim bounds, in centimetres. :class:`PrintSpecValidator`
#: refuses a trim outside them at the form; the builder refuses a *stored* one
#: outside them too, naming the column (CARD-114 F-003: the sheet had no upper
#: bound). Stated here so print_specs and the builder share one statement.
MIN_TRIM_CM = 10.0
MAX_TRIM_WIDTH_CM = 30.0
MAX_TRIM_HEIGHT_CM = 48.0

#: NFR-008's printed-cell **floor** (TERM-024), in millimetres: the smallest
#: cell a puzzle may be printed at in a book, below which the picture stops
#: being comfortably solvable in pen on paper. CARD-121 (FR-031, INV-006): a
#: puzzle whose cell on the book's trim falls below this joins the book only
#: together with an explicit override stored for its id.
#:
#: It sits here, a module constant beside :data:`BOOK1_PROFILE`, rather than on
#: :class:`PrintProfile`, because the floor and the cap are the two ends of
#: NFR-008's band but are *not* the same kind of number.
#: :attr:`PrintProfile.cell_cap_mm` is an **input** to the sheet — it is handed
#: to :class:`PageSpec` and changes the geometry ``compute_layout`` produces,
#: so a profile that printed at a different standard cell would carry a
#: different cap. The floor is a **verdict** the book store then makes about
#: the cell that came back, it is the same 4.8 mm for every trim, every margin
#: and every profile, and nothing downstream of it is laid out differently
#: because of it. One statement, in one place: the tile (CARD-123), the add
#: refusal and the finalise count all read this name (EC-021).
FLOOR_MM = 4.8

#: The narrowest side margin a book sheet may have: KDP's 0.25 in minimum for
#: the outside margin (CON-018: "0.375 in outside leaves room for trim variance
#: above KDP's 0.25 in minimum"), applied to both side margins. A stored
#: margin below it is refused, naming the column.
MIN_SIDE_MARGIN_MM = 6.35


@dataclass(frozen=True, slots=True)
class PrintProfile:
    """A book print profile, stated in inches (CON-018 states it that way)."""

    trim_width_in: Decimal
    trim_height_in: Decimal
    gutter_in: Decimal
    outside_in: Decimal
    top_in: Decimal
    bottom_in: Decimal
    #: The title band above each puzzle (TERM-028), in millimetres.
    band_mm: float
    #: NFR-008's standard cell: the flat cap, in millimetres.
    cell_cap_mm: float
    #: ADR-0037/R2's thinnest thin grid rule, in millimetres.
    min_thin_rule_mm: float

    @staticmethod
    def _mm(inches: Decimal) -> float:
        return float(inches * _MM_PER_INCH)

    @staticmethod
    def _stored_cm(inches: Decimal) -> str:
        return f"{inches * _CM_PER_INCH:.2f}"

    @property
    def width_mm(self) -> float:
        return self._mm(self.trim_width_in)

    @property
    def height_mm(self) -> float:
        return self._mm(self.trim_height_in)

    @property
    def gutter_mm(self) -> float:
        return self._mm(self.gutter_in)

    @property
    def outside_mm(self) -> float:
        return self._mm(self.outside_in)

    @property
    def top_mm(self) -> float:
        return self._mm(self.top_in)

    @property
    def bottom_mm(self) -> float:
        return self._mm(self.bottom_in)

    @property
    def trim_width_cm(self) -> str:
        """The trim width as the ``books`` table stores it (``"21.59"``)."""
        return self._stored_cm(self.trim_width_in)

    @property
    def trim_height_cm(self) -> str:
        return self._stored_cm(self.trim_height_in)

    @property
    def gutter_margin_cm(self) -> str:
        return self._stored_cm(self.gutter_in)

    @property
    def outside_margin_cm(self) -> str:
        return self._stored_cm(self.outside_in)

    def stored_columns(self) -> dict[str, str | None]:
        """The profile as the book's print columns: what a new book stores (AC-181)."""
        return {
            "trim_width_cm": self.trim_width_cm,
            "trim_height_cm": self.trim_height_cm,
            "gutter_margin_cm": self.gutter_margin_cm,
            "outside_margin_cm": self.outside_margin_cm,
            "outside_margin_bleed_cm": None,  # no bleed
        }


#: CON-018: the Book 1 print profile, the default for every book.
BOOK1_PROFILE = PrintProfile(
    trim_width_in=Decimal("8.5"),
    trim_height_in=Decimal("11"),
    gutter_in=Decimal("0.5"),
    outside_in=Decimal("0.375"),
    top_in=Decimal("0.375"),
    bottom_in=Decimal("0.375"),
    band_mm=12.0,
    cell_cap_mm=7.5,
    min_thin_rule_mm=0.25,
)


#: The ``books`` column :func:`book_ink_mode` reads, named once so every
#: refusal message and every writer spells it the same way.
INK_MODE_COLUMN = "interior_ink_mode"


class InkMode(Enum):
    """How a book's **interior** is printed: black-and-white, or in colour.

    Owner intake, 2026-09-25 (``meta/architecture/inputs/raw-requirements.md``):
    "2 modes to pdf generator: black/white and colors … we may add colors for
    book2". Per **book**, not a global default with an override: the mode is
    stored on the book beside its trim and margins.

    The value is what the column holds, so it is short, lower case and stable:
    a stored ``"bw"`` must keep meaning black-and-white for as long as there
    are rows carrying it. :attr:`bitmap_mode` is the one thing the mode
    decides — the Pillow image mode every page of that interior is composed
    and JPEG-encoded in — and it is deliberately the *only* thing: the PDF
    colour space and procset that follow from it are
    ``PdfImagePlugin``'s business and are transcribed in the page writer, not
    restated here.
    """

    BLACK_AND_WHITE = "bw"
    COLOUR = "colour"

    @property
    def bitmap_mode(self) -> str:
        """The Pillow image mode an interior page of this book is written in.

        ``"L"`` is one 8-bit channel and ``"RGB"`` three. The interior's *ink*
        is the same either way — ``export/png.py`` draws black on white and
        nothing else, and ``Image.convert("L")``'s ITU-R 601-2 luma maps a grey
        ``(v, v, v)`` to exactly ``v`` (its three integer coefficients sum to
        65536), so 0 stays 0, 255 stays 255 and no value between them is
        invented (ADR-0037/R2: a rule is not softened by the conversion).
        """
        return "L" if self is InkMode.BLACK_AND_WHITE else "RGB"

    @property
    def label(self) -> str:
        """What the panel calls this mode on Print setup and on Finalise."""
        return "Black and white" if self is InkMode.BLACK_AND_WHITE else "Colour"


#: What a book with nothing stored in :data:`INK_MODE_COLUMN` is printed as —
#: every book that existed before the column did (CARD-147, AC-3).
DEFAULT_INK_MODE = InkMode.BLACK_AND_WHITE


def ink_mode_from_stored(raw: object) -> InkMode:
    """One stored ``interior_ink_mode`` value as an :class:`InkMode`.

    ``None`` and an empty string are :data:`DEFAULT_INK_MODE`: no mode was
    ever stored, which is a legacy book, and a legacy book is
    black-and-white.

    Raises:
        ValueError: ``raw`` is neither empty nor one of the two modes. The
            message names :data:`INK_MODE_COLUMN`, the posture
            :func:`_stored_mm` already takes for a margin nobody can read: a
            value nobody can print is reported, not silently read as one of
            the two.
    """
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return DEFAULT_INK_MODE
    if isinstance(raw, InkMode):
        return raw
    if isinstance(raw, str):
        try:
            return InkMode(raw.strip().lower())
        except ValueError:
            pass
    known = ", ".join(repr(mode.value) for mode in InkMode)
    raise ValueError(f"book {INK_MODE_COLUMN} must be one of {known}, not {raw!r}")


def book_ink_mode(book: object) -> InkMode:
    """How ``book``'s interior is printed (CARD-147).

    Args:
        book: Anything carrying the ``books`` print columns as attributes — a
            :class:`~nonogram.admin.book_manager.Book`, a ``books`` row, or
            ``None``. A missing or empty attribute is
            :data:`DEFAULT_INK_MODE`, exactly as an empty margin column is the
            profile's margin.

    Raises:
        ValueError: the stored value is neither empty nor one of the two
            modes, naming :data:`INK_MODE_COLUMN`.
    """
    return ink_mode_from_stored(getattr(book, INK_MODE_COLUMN, None))


def _stored_mm(book: object, column: str, profile_cm: str, profile_mm: float) -> float:
    """One stored centimetre column as millimetres, the profile standing in for empty.

    Raises:
        ValueError: the stored value is not a finite number; the message names
            ``column`` (CARD-114 F-001).
    """
    raw = getattr(book, column, None)
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return profile_mm
    if isinstance(raw, bool) or not isinstance(raw, str | int | float):
        raise ValueError(f"book {column} must be a number of cm, not {raw!r}")
    try:
        # str() rather than the value itself: a NumPy scalar's str is its
        # plain decimal, and what reaches PageSpec is always a Python float.
        value = Decimal(str(raw).strip())
    except InvalidOperation:
        raise ValueError(f"book {column} must be a number of cm, not {raw!r}") from None
    if not value.is_finite():
        raise ValueError(f"book {column} must be a finite number of cm, not {raw!r}")
    if value == Decimal(profile_cm):
        return profile_mm
    return float(value * 10)


def _parity(page_number: int) -> PageParity:
    if isinstance(page_number, bool) or not isinstance(page_number, int) or page_number < 1:
        raise ValueError(f"page_number must be a whole number >= 1, not {page_number!r}")
    return PageParity.ODD if page_number % 2 else PageParity.EVEN


def book_page_spec(book: object, page_number: int = 1) -> PageSpec:
    """The sheet for one page of ``book``'s interior PDF.

    Args:
        book: Anything carrying the ``books`` print columns as attributes
            (``trim_width_cm``, ``trim_height_cm``, ``gutter_margin_cm``,
            ``outside_margin_cm``) — a :class:`~nonogram.admin.book_manager.Book`
            or a ``books`` row. A missing or empty attribute falls back to
            :data:`BOOK1_PROFILE`.
        page_number: The page's 1-based position in the interior PDF, as the
            generator reports it. Interior page 1 is the guide page and is a
            right-hand (odd) page, gutter on the left (FR-043). Parity moves
            the margins sideways and never changes the usable size, so any
            page gives the same cell (:func:`book_cell_mm`).

    Raises:
        ValueError: a stored value is not a finite number, a trim is outside
            KDP's bounds, a side margin is below :data:`MIN_SIDE_MARGIN_MM`,
            or the side margins leave no usable width — each naming the
            column(s) at fault — or ``page_number`` is not a whole number >= 1.
    """
    profile = BOOK1_PROFILE
    parity = _parity(page_number)
    width = _stored_mm(book, "trim_width_cm", profile.trim_width_cm, profile.width_mm)
    height = _stored_mm(book, "trim_height_cm", profile.trim_height_cm, profile.height_mm)
    gutter = _stored_mm(book, "gutter_margin_cm", profile.gutter_margin_cm, profile.gutter_mm)
    outside = _stored_mm(book, "outside_margin_cm", profile.outside_margin_cm, profile.outside_mm)

    for column, value_mm, maximum_cm in (
        ("trim_width_cm", width, MAX_TRIM_WIDTH_CM),
        ("trim_height_cm", height, MAX_TRIM_HEIGHT_CM),
    ):
        if not MIN_TRIM_CM * 10 <= value_mm <= maximum_cm * 10:
            raise ValueError(
                f"book {column} is {value_mm / 10:g} cm, outside KDP's "
                f"{MIN_TRIM_CM:g}..{maximum_cm:g} cm"
            )
    for column, value_mm in (("gutter_margin_cm", gutter), ("outside_margin_cm", outside)):
        if value_mm < MIN_SIDE_MARGIN_MM:
            raise ValueError(
                f"book {column} is {value_mm / 10:g} cm, below the "
                f"{MIN_SIDE_MARGIN_MM / 10:g} cm minimum side margin"
            )
    if gutter + outside >= width:
        raise ValueError(
            f"book gutter_margin_cm + outside_margin_cm ({(gutter + outside) / 10:g} cm) "
            f"leave no usable width on a {width / 10:g} cm trim"
        )

    return PageSpec(
        width_mm=width,
        height_mm=height,
        top_mm=profile.top_mm,
        bottom_mm=profile.bottom_mm,
        gutter_mm=gutter,
        outside_mm=outside,
        band_mm=profile.band_mm,
        orientation=OrientationPolicy.PORTRAIT_ONLY,
        cell_cap=profile.cell_cap_mm,
        min_thin_rule_mm=profile.min_thin_rule_mm,
        parity=parity,
    )


def book_cell_mm(
    spec: PageSpec,
    row_clues: Sequence[tuple[int, ...]],
    column_clues: Sequence[tuple[int, ...]],
) -> float:
    """A puzzle's printed cell on the book, in millimetres: ``compute_layout``'s, read off.

    Raises:
        ValueError: ``spec`` has no parity, so it lays out a drawing-sized
            image rather than a book page and has no book cell.
    """
    layout = compute_layout(tuple(row_clues), tuple(column_clues), page_spec=spec)
    if layout.page is None:
        raise ValueError("book_cell_mm needs a book page spec (one with a parity): build it with book_page_spec")
    return layout.page.cell_mm
