"""The book's :class:`~nonogram.export.layout.PageSpec`, built from its stored print specification.

COMP-009's one door onto COMP-007's book geometry (FR-030, ADR-0036). Every
book-side caller — the book PDF, the proof pages, the floor tile, the two-up
pairing — builds its sheet here and measures a puzzle's cell with
:func:`book_cell_mm`, so that "the cell a puzzle gets in this book" is one
computation (EC-021).

**Since CARD-225 that question has two forms, and both are answered here.**
NFR-008 as amended 2026-10-17 chooses the printed cell *per grid size per
book*, fitted to the deepest-clued member of that grid size, so:

* :func:`book_cell_mm` is one puzzle's own page fit — the largest cell it
  could take on this sheet, which is a **ceiling** on what it prints at;
* :func:`book_cell_sizes` is what a grid size really prints at in a given
  book: the **minimum** of those fits within each grid size. It is a
  selection over :func:`book_cell_mm`'s answers and measures nothing itself;
* :func:`book_cell_spec` is how that figure reaches a page — the sheet's flat
  cap lowered to it, so ``compute_layout`` still does every measurement
  (ADR-0036/R2) and no caller places anything.

* :data:`BOOK1_PROFILE` is CON-018 **as amended 2026-10-17** (CARD-222): trim
  8.5 x 11 in, gutter 0.5 in, outside 0.5 in, top 0.55 in, bottom 0.47 in, no
  bleed, the 12 mm title band (TERM-028). Three sides moved out from 0.375 in
  and the gutter deliberately did not (the owner's decision of 2026-10-14 to
  keep KDP's required 0.5 in rather than the artifact's 0.75 in), so the
  gutter and the outside margin are now **equal** and the mirrored margins of
  FR-030 are a geometric no-op on this profile — the rule still holds and its
  difference is simply zero, and it still bites on a book that stores unequal
  margins. It is
  stated once, in inches, and both forms callers need are derived from that:
  the exact millimetres a :class:`PageSpec` takes, and the two-decimal
  centimetre strings the ``books`` table stores.
* :func:`book_page_spec` reads a book's ``trim_width_cm``/``trim_height_cm``
  and ``gutter_margin_cm``/``outside_margin_cm``. An empty or missing value
  falls back to the profile (CON-018; AC-178's builder half). Top and bottom
  have no column and always come from the profile. The sheet is portrait-only,
  has NFR-008's flat 7.5 mm cap, ADR-0037/R2's three physical grid-rule
  weights (:data:`GRID_RULES`) and the 0.25 mm **raster** thin-rule minimum
  that is all ``min_thin_rule_mm`` has meant since R2's 2026-10-25 amendment,
  and carries the page's parity (ADR-0036, "Mirrored margins").
* :func:`book_cell_mm` converts ``compute_layout``'s result and does nothing
  else. **The admin panel fits no cell and places no grid line itself**
  (ADR-0036/R2): the exact cell is ``Layout.page.cell_mm``, which layout
  computes in millimetres; re-deriving it from the pixel ``Layout.cell`` would
  round it (4.57 mm instead of 4.61 mm for a 12-deep 30-wide grid).
* :data:`FLOOR_MM` is NFR-008's other end of the same band (TERM-024): the
  4.75 mm below which a puzzle joins a book only with a stored override
  (FR-031, INV-006 — enforced in ``BookManager``, which is where membership
  is written).

**The profile's stored form.** A stored value that *is* the profile's own
storage form means the profile's exact value, not the two decimals it rounds
to; any other stored value is read as the centimetres it says. That keeps "a
book created on the profile" and "a legacy book whose margins are empty" the
same sheet to the last micrometre (AC-178, AC-272, AC-273). Since the
2026-10-17 amendment both side margins are 0.5 in = 1.27 cm, which a
two-decimal column stores exactly, so on *this* profile the two readings
coincide and the rescue is invisible. It is kept because it is the profile's
contract and not this profile's arithmetic: 0.375 in was 0.9525 cm, stored as
``"0.95"``, and a book created before the amendment still carries that string
— which, no longer being the profile's own form, is now read as the 9.5 mm
that column actually states rather than as 9.525 mm.

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

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation
from enum import Enum

from nonogram.export.layout import (
    CellCapPolicy,
    GridRule,
    GridRules,
    OrientationPolicy,
    PageParity,
    PageSpec,
    compute_layout,
)

__all__ = [
    "BOOK1_PROFILE",
    "DEFAULT_DIVIDER_PAGES",
    "DEFAULT_INK_MODE",
    "DIVIDER_PAGES_COLUMN",
    "FLOOR_MM",
    "INK_MODE_COLUMN",
    "InkMode",
    "MAX_TRIM_HEIGHT_CM",
    "MAX_TRIM_WIDTH_CM",
    "MIN_SIDE_MARGIN_MM",
    "MIN_TRIM_CM",
    "PrintProfile",
    "book_cell_mm",
    "book_cell_sizes",
    "book_cell_spec",
    "book_divider_pages",
    "book_ink_mode",
    "book_page_spec",
    "divider_pages_from_stored",
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
#: the cell that came back, it is the same 4.75 mm for every trim, every margin
#: and every profile, and nothing downstream of it is laid out differently
#: because of it. One statement, in one place: the tile (CARD-123), the add
#: refusal and the finalise count all read this name (EC-021).
#:
#: **4.8 -> 4.75 mm, NFR-008 as amended 2026-10-17** (CARD-222, the same pass
#: that moved CON-018's three margins out): the owner lowered the floor so that
#: the margin change costs no grid a clue-depth step — the figure is chosen to
#: restore exactly the breach point the old margins had at the old floor, not
#: to admit a smaller cell than the book ever admitted. Measured with
#: ``compute_layout`` on the amended margins: a 30-wide grid at clue depth 10
#: lands at 4.7625 mm, 0.012 mm **above** this floor, where the retired 4.8 mm
#: would have refused it (AC-370); a 30-wide grid first falls under this floor
#: at clue depth 11 (4.6463 mm).
FLOOR_MM = 4.75

#: The narrowest side margin a book sheet may have: KDP's 0.25 in minimum for
#: the outside margin (CON-018 as amended 2026-10-17: "the 0.5 in outside
#: margin leaves room for trim variance well above KDP's 0.25 in minimum"),
#: applied to both side margins. A stored margin below it is refused, naming
#: the column.
MIN_SIDE_MARGIN_MM = 6.35


#: ADR-0037/R2's three rule weights for a book puzzle grid, **the owner's own
#: figures** from the artifact "Puzzle page layout" (2026-10-14): 0.3 pt cell
#: lines in grey, 0.8 pt every fifth line, 1.3 pt outer border. Stated once,
#: here, and read by every book-side sheet through :data:`BOOK1_PROFILE`.
#:
#: **Confirmed by the owner on 2026-10-25** against the alternative that stood
#: here for eight days — the same ratios (1 : 2.667 : 4.333) scaled by 1.6 to
#: 0.48 / 1.28 / 2.08 pt. That scaling was never a design opinion: it was an
#: arithmetic correction so the thinnest line would be 2 device pixels at
#: 300 DPI instead of one, and ADR-0042 removed the floor by making the
#: interior a content stream. The owner read both on
#: ``card293-proof-vector.pdf`` and chose page 1.
#:
#: **These figures hold only in vector** (ADR-0037/R2, ADR-0042/R1). Through a
#: rasteriser at 300 DPI they round to 1 / 3 / 5 px — the one-pixel grey cell
#: grid that 7 of 17 reviews of the 450-puzzle book complained about — which is
#: why :func:`~nonogram.export.layout.refuse_rasterised_rule` is called at
#: every raster grid stroker that a sheet carrying them can reach. Raster
#: pages ARE built from this profile's spec — the single-puzzle page, the
#: two-up page, the solved page and the packed answer key all are — and they
#: are drawn at COMP-007's proportional device widths, never at these.
#:
#: The cell line's ``0.35`` grey renders as grey 89 (``round(255 * 0.35)``),
#: measured by poppler on the CARD-293 proof at both 300 and 1200 DPI. The
#: fifth line and the border are the interior's one ink, pure black, so the
#: cell lines read as light guidance under them.
GRID_RULES = GridRules(
    cell=GridRule(width_pt=0.3, grey=0.35),
    fifth=GridRule(width_pt=0.8, grey=0.0),
    border=GridRule(width_pt=1.3, grey=0.0),
)


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
    #: The thinnest a thin grid rule may be **on a raster surface**, in
    #: millimetres. **Not ADR-0037/R2's interior minimum, which no longer
    #: exists**: R2 as amended 2026-10-25 states the interior's weights as
    #: physical points (:attr:`grid_rules`) and gives them no millimetre floor
    #: at all, because the medium carries the dropout guarantee — a content
    #: stream declares a width and the renderer resolves it.
    #:
    #: **Scoped rather than retired, and rather than re-numbered** (CARD-227's
    #: Obligation 2). The honest alternatives were to scope this field to the
    #: raster path or to drop it from the book profile; replacing 0.25 with
    #: 0.1058 (0.3 pt in millimetres) was refused outright, because a floor
    #: set *at* the figure it is meant to protect asserts nothing and reads as
    #: licence. It is scoped and not dropped because the pages it governs are
    #: still here: the live interior walk is raster until CARD-298 flips it,
    #: and on that surface R2 keeps a 2-device-pixel floor and 0.25 mm is
    #: 3 px at 300 DPI — above it, which is the point of keeping it.
    min_thin_rule_mm: float
    #: ADR-0037/R2's three physical grid-rule weights, as a content stream
    #: declares them. The interior's figures live here, on the print profile,
    #: beside the band and the cap, because they are a property of how this
    #: book is printed and not of the geometry engine.
    grid_rules: GridRules

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
    outside_in=Decimal("0.5"),
    top_in=Decimal("0.55"),
    bottom_in=Decimal("0.47"),
    band_mm=12.0,
    cell_cap_mm=7.5,
    min_thin_rule_mm=0.25,
    grid_rules=GRID_RULES,
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


#: The ``books`` column :func:`book_divider_pages` reads, named once so every
#: refusal message and every writer spells it the same way.
DIVIDER_PAGES_COLUMN = "interior_divider_pages"

#: Whether a book with nothing stored in :data:`DIVIDER_PAGES_COLUMN` prints
#: its divider pages. ``True``, because every book that existed before the
#: column did printed them — they were unconditional from CARD-128 (the level
#: dividers, AC-254) and CARD-198 (the SOLUTIONS divider, AC-292) until this
#: setting existed. An empty column therefore means "the book as it has always
#: been", not "undecided".
DEFAULT_DIVIDER_PAGES = True

#: What a divider-pages value may say for "yes" and for "no". A real boolean
#: is the shape the *column* has on both backends — nothing the shipped schema
#: stores here is a string. The string forms are the **form's** vocabulary,
#: reached through :func:`divider_pages_from_form` (a checkbox posts ``"1"``,
#: and a client that means "no" explicitly says one of the false spellings
#: instead of relying on posting nothing), and they are also what a
#: hand-edited or hand-migrated column may hold. One vocabulary for both
#: doors, so neither has to know which layer it is being read from.
#:
#: CARD-305 review cycle 1, F-005: this comment used to claim the strings were
#: also "what SQLite hands back for a boolean on some drivers". No driver this
#: project uses does that and none was named, so that claim is gone; the form
#: half is now true because the route really goes through it (F-004).
_DIVIDER_PAGES_TRUE = frozenset({"1", "on", "true", "yes", "y", "t"})
_DIVIDER_PAGES_FALSE = frozenset({"0", "off", "false", "no", "n", "f"})


def divider_pages_from_stored(raw: object) -> bool:
    """One stored divider-pages column as a plain bool.

    ``None`` and an empty string are :data:`DEFAULT_DIVIDER_PAGES`: no choice
    was ever stored, which is every book written before the column existed,
    and those books printed their dividers.

    Args:
        raw: Whatever the column holds — ``None``, a bool, an int, or one of
            the strings a form or a driver spells a boolean with.

    Raises:
        ValueError: the stored value is neither empty nor a recognisable
            boolean; the message names :data:`DIVIDER_PAGES_COLUMN`, the same
            posture :func:`ink_mode_from_stored` takes.
    """
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return DEFAULT_DIVIDER_PAGES
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, int):
        # 0/1 from a backend that stores a boolean as an integer. Anything
        # else is a value nobody meant, and is refused rather than read as
        # truthy — a 2 here is a bug upstream, not "on".
        if raw in (0, 1):
            return bool(raw)
    if isinstance(raw, str):
        value = raw.strip().lower()
        if value in _DIVIDER_PAGES_TRUE:
            return True
        if value in _DIVIDER_PAGES_FALSE:
            return False
    raise ValueError(
        f"book {DIVIDER_PAGES_COLUMN} must be empty or a boolean, not {raw!r}"
    )


def book_divider_pages(book: object) -> bool:
    """Whether ``book``'s interior prints its divider pages (CARD-305).

    The four pages this decides are the level dividers — one per non-empty
    named level, "Easy" / "Medium" / "Hard" (AC-254) — and the "SOLUTIONS"
    page that opens the answer key (AC-292). They are one setting because they
    are one editorial decision and one page design
    (:meth:`~nonogram.admin.book_pdf_generator.BookPDFGenerator.create_divider_page`
    draws all four).

    Args:
        book: Anything carrying the ``books`` print columns as attributes — a
            :class:`~nonogram.admin.book_manager.Book`, a ``books`` row, or
            ``None``. A missing or empty attribute is
            :data:`DEFAULT_DIVIDER_PAGES`.

    Raises:
        ValueError: the stored value is neither empty nor a recognisable
            boolean, naming :data:`DIVIDER_PAGES_COLUMN`.
    """
    return divider_pages_from_stored(getattr(book, DIVIDER_PAGES_COLUMN, None))


def divider_pages_from_form(raw: object) -> bool:
    """What a Print-setup submission's divider-pages **field** means.

    The second door onto :data:`_DIVIDER_PAGES_TRUE` /
    :data:`_DIVIDER_PAGES_FALSE`, and it has to be a second door rather than
    the same one: an HTML checkbox posts **nothing at all** when it is
    unticked, so an absent or empty field here is ``False`` — the opposite of
    what :func:`divider_pages_from_stored` makes of it, where empty means
    "nothing was ever stored" and therefore :data:`DEFAULT_DIVIDER_PAGES`.

    Whether the submission carries the control at all is a *different*
    question, answered by the form's hidden companion marker before this
    function is reached (see the Print-setup route). This answers only "the
    control was there; what was it set to".

    Anything else is read with :func:`divider_pages_from_stored`, so a client
    that spells "no" explicitly — ``0``, ``off``, ``false``, ``no`` — is
    believed instead of being swallowed by ``bool()``, which is CARD-305
    review cycle 1's F-004: the route read this field with ``bool()`` and
    stored ``True`` for every one of those.

    Args:
        raw: The field as the form hands it over — ``None`` when the box was
            unticked (or the client sent no value beside the marker), else
            whatever string it posted.

    Raises:
        ValueError: the field is neither empty nor a recognisable boolean,
            naming :data:`DIVIDER_PAGES_COLUMN`. The route turns that into a
            flashed refusal that stores nothing, which is the posture it
            already takes for an unreadable trim — guessing at a value nobody
            meant is how a book silently loses four pages.
    """
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return False
    return divider_pages_from_stored(raw)


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
        grid_rules=profile.grid_rules,
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


#: A grid size, as the book groups puzzles by it: ``(columns, rows)``, read off
#: a puzzle's own clue sets (``len(column_clues)`` across, ``len(row_clues)``
#: down). 30x20 and 20x30 are two grid sizes, not one — they are two different
#: shapes on the page and a shared cell for them would be meaningless.
GridSize = tuple[int, int]

#: One member of a book, as the per-grid-size fit reads it: its
#: ``(row_clues, column_clues)``. Nothing else about a puzzle enters the
#: computation — not its id, its tier, its name or its grid (ADR-0033/R1).
BookMember = tuple[Sequence[tuple[int, ...]], Sequence[tuple[int, ...]]]


def book_cell_sizes(spec: PageSpec, members: Iterable[BookMember]) -> dict[GridSize, float]:
    """The cell each **grid size** in this book prints at, in millimetres (NFR-008).

    NFR-008 as amended 2026-10-17: the figure is chosen *per grid size per
    book*, fitted to the deepest-clued member of that grid size, so every
    20x20 in one book prints at one cell however its clue columns differ
    (CARD-225, AC-369).

    **It is a selection, not a second fit.** Each member's own cell is
    :func:`book_cell_mm` — ``compute_layout``'s, read off (ADR-0036/R2: the
    admin panel fits no cell) — and this function takes the **minimum** of
    them within each grid size. Nothing here measures a sheet, a gutter or a
    margin.

    **Why the minimum rather than "the deepest-clued member's".** They are the
    same number whenever one member is deepest on both axes, which is the case
    NFR-008's AC-369 and this card's AC-2 state. They can differ when one
    member has the deeper **row** clues (which decide the width term) and
    another the deeper **column** clues (the height term): the minimum is then
    the only figure at which *neither* overflows, and "the deepest-clued
    member" has no single referent. The minimum is also what makes
    non-overflow an identity rather than a case analysis: for any member *m*,
    ``result <= book_cell_mm(spec, *m)``, so *m*'s own page fit is never
    exceeded.

    Args:
        spec: The book's sheet, as :func:`book_page_spec` builds it. Parity
            moves the usable area and never its size, so either parity gives
            the same sizes.
        members: The book's members as ``(row_clues, column_clues)`` pairs, in
            any order and with repeats allowed. A member appearing twice is
            one member: the minimum is order- and multiplicity-independent
            (AC-7).

    Returns:
        ``{(columns, rows): cell in mm}``, holding exactly the grid sizes
        ``members`` covers. An empty iterable gives an empty mapping — a book
        with no members prints no puzzle page, and a caller that asks for a
        grid size it did not supply gets a :class:`KeyError` rather than a
        guessed cell (see :func:`book_cell_spec`'s caller contract).

    Raises:
        ValueError: ``spec`` has no parity, or a member's clue sets cannot be
            laid out — propagated from :func:`book_cell_mm`/``compute_layout``
            unchanged, naming what was wrong with it. Fail closed: a book with
            one unmeasurable member gets **no** sizes at all, rather than
            sizes for the grid sizes that happened to measure (F-3).
    """
    sizes: dict[GridSize, float] = {}
    for row_clues, column_clues in members:
        key: GridSize = (len(column_clues), len(row_clues))
        cell_mm = book_cell_mm(spec, row_clues, column_clues)
        current = sizes.get(key)
        sizes[key] = cell_mm if current is None else min(current, cell_mm)
    return sizes


def book_cell_spec(spec: PageSpec, cell_mm: float) -> PageSpec:
    """``spec`` with its flat cap lowered to ``cell_mm`` — the book's own cell.

    How a book-wide figure reaches the page **without a second placement**
    (ADR-0036/R2, and the precedent ``compute_pair_layout`` set with its
    ``fit_spec``): the cell a placed page draws is ``min(cap, page fit)``, so
    a spec whose cap *is* the grid size's shared cell makes every member of
    that grid size draw exactly that cell — the shared figure is at or below
    every member's own fit by construction (:func:`book_cell_sizes`), so the
    cap is what binds for every one of them, and ``compute_layout`` still does
    all the measuring.

    The cap is lowered, never raised: NFR-008's 7.5 mm standard cell is a
    ceiling this card does not touch (G-1). A ``cell_mm`` above the spec's own
    cap is therefore a no-op rather than an error — it is what a grid size at
    the cap already asks for (AC-3).

    Args:
        spec: A **book** sheet: one with a parity and a flat cap in mm.
        cell_mm: The grid size's own cell, from :func:`book_cell_sizes`.

    Raises:
        ValueError: ``cell_mm`` is not a finite positive number of mm, or
            ``spec`` carries NFR-005's comfort curve rather than a flat cap —
            a CLI/A4 sheet has no book cell, and giving it one would be the
            byte-identity ADR-0036/R1 forbids rather than a smaller page.
    """
    if spec.cell_cap is CellCapPolicy.COMFORT_CURVE:
        raise ValueError(
            "book_cell_spec needs a book sheet with a flat cell cap in mm, not "
            "NFR-005's comfort curve: a CLI page has no book cell"
        )
    if (
        isinstance(cell_mm, bool)
        or not isinstance(cell_mm, int | float)
        or cell_mm != cell_mm  # NaN
        or cell_mm in (float("inf"), float("-inf"))
        or cell_mm <= 0
    ):
        raise ValueError(f"cell_mm must be a finite positive number of mm, not {cell_mm!r}")
    return replace(spec, cell_cap=min(float(spec.cell_cap), float(cell_mm)))
