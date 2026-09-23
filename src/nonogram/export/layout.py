"""COMP-007 — the shared print geometry behind every rendered puzzle (FR-011).

Three renderers draw the same picture: the PNG raster (CARD-012), the SVG vector
(CARD-012) and CARD-014's PDF, which CON-006 makes a second sink on the PNG
raster path rather than a new dependency. "The same picture" has to mean the
same *numbers*, so the numbers live here, once, and the renderers only choose
how to stroke them.

The one thing not all three draw is a header. It is measured here anyway
(:func:`header_band`) — a page's geometry is this module's subject whoever ends
up drawing it — but as a separate measurement laid *above* a computed
:class:`Layout` rather than as a parameter of :func:`compute_layout`, so that
a format without a header carries none of it in its *coordinates*: the PNG and
the PDF's puzzle page are the same pixels, offset by the band's height. The one
thing every format does share is the band's claim on the *sheet*: the cell is
sized so that drawing **plus** band fits A4 (NFR-005 defines page fit that
way), because a cell chosen without the band is a cell the PDF cannot print.
See :func:`header_band` and :func:`_fit_cell`.

A pure function of the clues and the sheet, and of nothing else
---------------------------------------------------------------
:func:`compute_layout` takes the two clue sets and returns plain ints, floats
and tuples. No Pillow type, no SVG string and no filesystem appears in its
signature, which is what lets a third renderer consume it without inheriting
the second one's library. The grid's size is not a separate parameter because
it is not separate information: ``len(row_clues)`` is the number of rows and
``len(column_clues)`` the number of columns (INV-001 makes the clue sets the
encoding of the grid, so a size argument could only ever agree with them or be
a bug). Everything else — page size, margins, band, the cap on the cell, the
orientation rule, the strokes — comes from a :class:`PageSpec`, and the
default one (:data:`DEFAULT_PAGE_SPEC`) is exactly the module constants below,
so the same clues on the same sheet always produce the same geometry.

Which sheet: the default one, or one the caller names (ADR-0036)
----------------------------------------------------------------
This module used to carry a guardrail (G-1, "no second paper size"): A4 was
the only sheet it knew. ADR-0036 retired that rule. COMP-007 now knows more
than one sheet, but **only through an explicit** :class:`PageSpec`, **never by
guessing**. Nothing here infers a sheet from the puzzle, the payload or the
caller. A caller that passes no spec (the CLI, the web UI, every existing
export) gets :data:`DEFAULT_PAGE_SPEC`, which is today's A4 byte for byte
(ADR-0036/R1, CON-019, pinned by ``tests/test_export_a4_golden.py``). The book
(COMP-009) is the only caller that passes one.

A spec lays a puzzle out in one of two ways, and its ``parity`` decides which:

* **no parity: a drawing-sized image.** The image is the drawing plus one
  uniform margin on all four sides, the sheet may turn (NFR-006) and the cell
  is a whole number of device pixels. This is the only path the default spec
  takes, and every measurement in the sections below (the 441-extent sweeps,
  the orientation counts, the band's cost) **describes the default spec
  only**.
* **a parity (``ODD``/``EVEN``): a placed page.** The image is the whole trim.
  The usable area is the trim minus its margins, with the gutter margin on the
  binding side: left on an odd (right-hand) page, right on an even one. The
  title band sits at the top of the usable area, and the drawing's top edge
  sits directly under it, at a fixed offset of top margin + band (FR-032). The
  drawing is centred across the usable width (FR-032 amended 2026-09-22 (c)),
  so parity moves it sideways by gutter − outside and never changes its size.
  The sheet is never turned (``PORTRAIT_ONLY``). The cell is
  ``min(cap, page fit)`` computed in millimetres and drawn at a fractional
  pitch, so the cell a book tile reports (FR-031) is the cell the page prints.
  Where the drawing sits is reported as :class:`PagePlacement` on
  :attr:`Layout.page`. The book's behaviour is measured by
  ``tests/test_layout_page_spec.py`` and ``tests/property/test_book_layout.py``,
  not by the A4 numbers here.

What the geometry is
--------------------
A standard printed nonogram: a square-celled grid, a left gutter holding the
row clues right-aligned against the grid's left edge, a top gutter holding the
column clues bottom-aligned against its top edge, and an empty corner block
where the two gutters meet. The gutters are exactly as deep as the longest
clue in their direction, so a puzzle whose rows never need more than three
numbers does not carry a gutter sized for twenty-five.

Grid lines run the *full* extent of their axis, gutter included — the vertical
line between column 4 and column 5 continues up through the column-clue gutter
— because that is what makes a clue number readable as belonging to its line.
Every fifth line, and both outer borders, is stroked heavier
(:attr:`Layout.thick_rule` against :attr:`Layout.thin_rule`); counting to
twelve along a thirty-cell row is the thing a solver actually does with a ruler
otherwise, and the every-5th rule is the convention that makes it unnecessary.

Why the sizes are what they are (the A4 / 300 DPI target)
---------------------------------------------------------
The card asks for output "legible when printed at A4". That is a physical
statement, so the geometry is computed in physical units and only then turned
into device pixels at :data:`DPI` = 300 — the resolution at which a printed
line looks like a line rather than a staircase, and the number both renderers
stamp onto their output (the PNG as a ``dpi`` tag, the SVG as a physical
``width``/``height`` in inches over a pixel ``viewBox``) so that a printer
reproduces the intended size instead of guessing.

The sheet turns whichever way prints the larger cell (NFR-006)
--------------------------------------------------------------
*Default spec only (this and every section below): a placed book page is never
turned.* The default sheet is A4, but it is not always the same way up.
Page fit is a different measurement on a turned sheet — 186 mm across by
273 mm down becomes 273 mm across by 186 mm down — so :func:`_orientation_for`
measures the cell **both ways and keeps the larger**, a tie going to portrait
(EC-010). That is the whole rule: orientation is not a function of the grid's
extent, and two puzzles of the same extent can print on differently turned
sheets when their clue gutters differ.

The rule it replaced turned the sheet on the grid's *shape* — landscape iff
``columns > rows`` — which reads the wrong object: what has to fit the paper
is the **drawing**, grid plus both gutters plus the band, and a wide grid can
draw tall behind a deep column gutter. A 26x25 whose rows alternate full and
empty draws 27 cells across by 38 down, and prints 6.86 mm upright against the
4.57 mm the landscape sheet its shape asks for would give. Measured over
CON-011's 441 extents at the two gutter-heavy clue patterns
:mod:`tests.property.test_layout_cell_size` sweeps, the shape rule costs cell
size on 102 of those 882 cases and gains on none, for a mean printed cell of
6.626 mm against this rule's 6.749 mm.

Turning is worth having where it applies: a 26x10 checkerboard goes 4.74 mm to
6.86 mm, a 30x10 5.93 mm to 6.43 mm. It is also self-limiting, without a rule
saying so — a small grid is held by the comfort cap on both sheets, so the two
cells come out equal and the tie keeps it upright. Swept over the 441 extents
at four clue patterns, 446 of the 1764 cases turn, none of them below a larger
dimension of 16.

:func:`compute_layout` then sizes the cell as NFR-005 defines it — the
comfortable size for a grid that big, held down to whatever the sheet can
actually take::

    cell = min(comfort_cap(max(columns, rows)), page_fit(orientation))

* the *comfort cap* (:func:`comfort_cap_mm`) is how big a cell wants to be at
  that grid size: 9.0 mm at 10 cells a side, declining to 6.5 mm at 30
  (CON-011's largest supported grid), linearly interpolated between NFR-005's
  chosen points and flat outside them. It is a function of the **grid's**
  longer side and of nothing else — a gutter makes a drawing wider, not a cell
  harder to mark. The declining curve replaces a single flat 6.5 mm cap, under
  which a 10x10 and a 25x25 printed *identically* at 6.52 mm and a 10x10 came
  out about 30% smaller than it was meant to be.
* *page fit* is the largest cell whose whole page — grid, plus both clue
  gutters, plus the :data:`HEADER_BAND_MM` strip a titled page lays above the
  drawing — still fits the printable area of A4 **as the puzzle turned it**. The
  band is counted for all three formats, not only the PDF that draws it: it
  eats height, so it only ever costs a drawing whose height term binds — which
  on a portrait sheet means a drawing about 1.40x taller than it is wide
  (186 mm across against 261 mm down once the band is reserved) and on a
  landscape one about 0.64x, since a turned sheet leaves 273 mm across against
  only 174 mm down. Where the height term does bind, a cell chosen without the
  band is a cell the PDF cannot put on a sheet. That is not hypothetical — a
  10x25 whose rows alternate full and empty is an ordinary uniquely-solvable
  puzzle, and sized on the drawing alone it overruns A4 by 34 device pixels
  once the band is added.
* the cap is a **ceiling, never a floor**: where the two disagree, page fit
  wins. Which of the two binds is as much a question of the gutter as of the
  grid's size — a 30x30 checkerboard draws 45 cells across, 293 mm of paper at
  the 6.5 mm the cap allows against the 186 mm A4 actually prints, so page fit
  overrules the cap; a 20x20 with a single filled cell draws 21 across and sits
  at its 7.5 mm cap with room to spare. Over the four-pattern sweep, 564 of the
  1364 cases at 20 cells a side or more are page-fit bound and the other 800
  are at the cap. A cap honoured where the page allows it is a real gain at the
  small sizes a person prints most; a cap treated as a target would be a
  promise the format cannot keep.
* the *floor* (:data:`MIN_CELL_MM`) is the honest limit of the format, and is
  deliberately untouched by the above — turning the sheet does not move it.
  No supported puzzle reaches it: the worst 30x30 draws 45 cells across and
  still gets a ~4 mm cell, and page fit would have to fall below 2 mm — over
  ninety cells across a portrait sheet, over a hundred and thirty across a
  landscape one — before the floor bites at all. It is the backstop for that
  case, and it answers it by keeping
  2 mm cells and letting the image grow past A4 rather than shrinking past the
  point where a pencil mark is meaningless: a user printing a drawing that
  large is scaling it down or printing it on A3 either way, and a silently
  unreadable page would be the worse answer.

Layering (ADR-0007): a capability submodule — stdlib only, no siblings, no
orchestrator, no admin panel (a :class:`PageSpec` carries print numbers, never
a book), and (guardrail G-3) no notion whatsoever of whether the puzzle it is
measuring may be exported.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, replace
from enum import StrEnum
from fractions import Fraction
from typing import Literal

__all__ = [
    "ANSWER_CAPTION_MM",
    "ANSWER_HEADING_MM",
    "ANSWER_MAX_CELL_MM",
    "ANSWER_TEXT_FONT_MM",
    "ANSWER_TILE_CAPACITIES",
    "ANSWER_TILE_GAP_MM",
    "CELL_COMFORT_MM",
    "DEFAULT_PAGE_SPEC",
    "DPI",
    "HEADER_BAND_MM",
    "HEADER_FONT_MM",
    "MAX_CELL_MM",
    "MIN_CELL_MM",
    "MAJOR_RULE_EVERY",
    "PAGE_HEIGHT_MM",
    "PAGE_MARGIN_MM",
    "PAGE_WIDTH_MM",
    "TWO_UP_MIN_CELL_MM",
    "AnswerPageLayout",
    "AnswerTile",
    "CellCapPolicy",
    "ClueEntry",
    "GridLine",
    "HeaderBand",
    "Layout",
    "Orientation",
    "OrientationPolicy",
    "PageParity",
    "PagePlacement",
    "PageSpec",
    "PairLayout",
    "comfort_cap_mm",
    "compute_answer_page_layout",
    "compute_layout",
    "compute_pair_layout",
    "header_band",
]

#: Output resolution in dots per inch. 300 is the conventional print target:
#: at 150 a thin rule and a small clue digit both start to alias, and at 600
#: the 30x30 page is four times the bytes for detail no home printer resolves.
DPI = 300

#: A4 held **portrait**, in millimetres (ISO 216) — the orientation these two
#: names describe, and the one a puzzle keeps unless turning the sheet prints
#: it a larger cell (NFR-006), in which case the two swap.
#: :func:`_page_size_mm` is the one place that swap happens, so that every
#: other reference to A4 in this module can go on meaning the same physical
#: piece of paper.
PAGE_WIDTH_MM = 210.0
PAGE_HEIGHT_MM = 297.0

#: Blank border kept on every side, in millimetres — comfortably inside the
#: unprintable margin of a typical inkjet, and enough to hold the sheet by.
PAGE_MARGIN_MM = 12.0

#: NFR-005's chosen comfort values: how big a printed cell should be, in
#: millimetres, for a grid whose *larger* dimension is that many cells. Five
#: decided points, read as a piecewise-linear curve by :func:`comfort_cap_mm`
#: — the points were decided, the line between them is interpolation. Kept as
#: ``(cells, mm)`` pairs in ascending order of ``cells``; the curve must stay
#: non-increasing in ``cells`` (EC-008), which is the whole content of "a
#: bigger grid gets a smaller cell".
CELL_COMFORT_MM: tuple[tuple[int, float], ...] = (
    (10, 9.0),
    (15, 8.0),
    (20, 7.5),
    (25, 7.0),
    (30, 6.5),
)

#: The comfort value for the largest supported grid (CON-011: 30 cells a
#: side), in millimetres. This is no longer *the* cap — the cap is
#: :func:`comfort_cap_mm`, one value per grid size — only the bottom end of
#: its curve, kept under a name because it is the one point of that curve a
#: reader has reason to reach for directly.
MAX_CELL_MM = CELL_COMFORT_MM[-1][1]

#: The cell-size floor, in millimetres: smaller than this is not a puzzle any
#: more, it is a grey square. Unlike the comfort cap above, the floor wins
#: over page fit rather than yielding to it — see the module docstring for why
#: an oversized image beats a silently unreadable page.
#:
#: **A backstop for out-of-range drawings only, and knowingly so.** Measured
#: over all 441 extents CON-011 supports at four clue patterns, each on the
#: sheet NFR-006 turns it to: the smallest cell any of them gets is 48 px /
#: 4.06 mm — three checkerboards, 30x28, 30x29 and 30x30, each drawing 45 cells
#: across and so having to fit 45 of them into the 186 mm of width a portrait
#: sheet leaves (the 30x30 stays upright because turning it would print only
#: 3.81 mm) — against this floor's 24 px.
#: Page fit has to fall under 24 px for the floor to engage at all, which needs
#: 92 cells across or 129 down on a portrait sheet, and 135 across or 86 down on a
#: landscape one — nearly twice CON-011's widest grid plus its deepest gutter
#: even by the easiest of those four routes. So the guarantee
#: "the floor still beats page fit" (guardrail G-3) is certified against a
#: synthetic drawing (``test_the_largest_drawing_keeps_a_markable_cell``'s
#: 120x60 clue set) rather than a constructible puzzle, because the domain can
#: no longer construct one. That is recorded rather than hidden: the clamp is
#: live code for a case only a future widening of CON-011, or a future format
#: with a much deeper gutter, would reach — and a later reader tempted to
#: delete it as dead should reach that conclusion on purpose.
MIN_CELL_MM = 2.0

#: Every Nth grid line is stroked heavy — the standard nonogram counting aid.
MAJOR_RULE_EVERY = 5

#: The strip CARD-014's PDF adds *above* a rendered page for its
#: ``<name> — <tier>`` header, and the type size the header is set in, both in
#: millimetres. 5 mm is roughly 14 pt: larger than any clue digit at any cell
#: size, so the title reads as a title, and the 12 mm band leaves a clear
#: half-band of white above and below it. See :func:`header_band` for why the
#: band is measured here but added by the renderer.
HEADER_BAND_MM = 12.0
HEADER_FONT_MM = 5.0

#: Clue digits, as a fraction of the cell they sit in. 0.62 leaves a visible
#: gap on both sides of a two-digit clue (the widest that can occur: the
#: longest possible run is 30, CON-011) without the numbers touching the rules.
_CLUE_FONT_RATIO = 0.62

#: Thin and heavy rule widths, as a fraction of the cell. The thin rule is
#: pinned to the cell rather than fixed in pixels so that the drawing keeps
#: its proportions at every size the clamp above can produce. A spec's
#: ``min_thin_rule_mm`` can hold it up (ADR-0037/R2), and never pull it down.
_THIN_RULE_RATIO = 1 / 30

#: A run-length clue for one line, and a full set of them — the same boundary
#: types ``nonogram.clues`` produces and ``ExportPayload`` carries (ADR-0012).
type LineClue = tuple[int, ...]
type ClueSet = tuple[LineClue, ...]

#: Which way up the sheet is held (NFR-006). Two values and no third: turning
#: the sheet is the only freedom the layout has with it. A spec whose policy is
#: :attr:`OrientationPolicy.PORTRAIT_ONLY` is always ``"portrait"``.
type Orientation = Literal["portrait", "landscape"]


class OrientationPolicy(StrEnum):
    """How a :class:`PageSpec` chooses which way up its sheet is held."""

    #: NFR-006: measure the cell on both sheets and keep the larger, ties
    #: upright. The default spec's policy.
    LARGER_CELL_WINS = "larger_cell_wins"
    #: The sheet as given, never turned, and the grid never rotated (FR-032:
    #: a book puzzle prints upright).
    PORTRAIT_ONLY = "portrait_only"


class CellCapPolicy(StrEnum):
    """The one named cell cap. The other kind of cap is a flat number of mm.

    A :class:`PageSpec`'s ``cell_cap`` is either :attr:`COMFORT_CURVE` or a
    finite positive float, the flat cap in millimetres (NFR-008's 7.5 mm
    standard cell for a book).
    """

    #: NFR-005: :func:`comfort_cap_mm` of the grid's longer side.
    COMFORT_CURVE = "comfort_curve"


class PageParity(StrEnum):
    """Which side of a spread a placed page is on (ADR-0036, "Mirrored margins").

    The gutter margin is on the binding side: the left of a right-hand
    (``ODD``) page and the right of a left-hand (``EVEN``) one. Which page is
    page 1 is the caller's decision (FR-043: the book's interior page 1, the
    guide page, is right-hand); a spec only carries the parity it is given.
    """

    ODD = "odd"
    EVEN = "even"


def _is_real(value: object) -> bool:
    """A finite int or float. ``bool`` is not a measurement, even though it is an int."""
    return (
        isinstance(value, int | float)
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _exact_mm(value: float | Fraction) -> Fraction:
    """A measurement as the exact decimal it was written as.

    ``Fraction(repr(value))``, not ``Fraction(value)``: 9.525 mm is 0.375 in
    exactly, and the binary float nearest to it is not. The placed path keeps
    the spec's numbers exact so that its fit and its parity arithmetic are
    exact too.
    """
    return value if isinstance(value, Fraction) else Fraction(repr(value))


@dataclass(frozen=True, slots=True, kw_only=True)
class PageSpec:
    """The sheet a puzzle is laid out on, in physical units (ADR-0036).

    A value object: frozen, compared by value, and valid by construction.
    :meth:`__post_init__` refuses every spec that could not be laid out, so
    :func:`compute_layout` never re-checks one. See the module docstring for
    the two ways a spec lays a puzzle out, which ``parity`` selects.

    Attributes:
        width_mm: Trim (sheet) width, held upright.
        height_mm: Trim height.
        top_mm: Top margin.
        bottom_mm: Bottom margin.
        gutter_mm: The binding-side margin: left on an ``ODD`` page, right on
            an ``EVEN`` one.
        outside_mm: The margin on the other side.
        band_mm: The title band reserved above the drawing (TERM-028). On the
            default spec it is :data:`HEADER_BAND_MM`, reserved from the
            sheet's height but drawn by the PDF above the image. On a placed
            page it is the strip between the top margin and the drawing.
        orientation: :class:`OrientationPolicy`.
        cell_cap: :attr:`CellCapPolicy.COMFORT_CURVE`, or a flat cap in mm.
        min_thin_rule_mm: The thinnest a thin grid rule may be (ADR-0037/R2:
            0.25 mm on a book). ``None`` keeps the ``cell / 30`` rule unchanged.
            The heavy rule is always twice the thin one, and every rule is
            drawn in pure black by the renderers.
        parity: ``None`` means a drawing-sized image with one uniform border,
            the default spec's way. ``ODD``/``EVEN`` means a trim-sized placed
            page.

    Raises:
        ValueError: a field is not a finite number where one is required, a
            size is non-positive, a margin or band is negative, the usable
            area (trim minus margins minus band) is non-positive, a policy or
            parity is not one of its enum's members, a spec without parity has
            unequal margins, or a spec with parity may be turned.
    """

    width_mm: float
    height_mm: float
    top_mm: float
    bottom_mm: float
    gutter_mm: float
    outside_mm: float
    band_mm: float
    orientation: OrientationPolicy
    cell_cap: CellCapPolicy | float
    min_thin_rule_mm: float | None = None
    parity: PageParity | None = None

    def __post_init__(self) -> None:
        measurements = {
            "width_mm": self.width_mm,
            "height_mm": self.height_mm,
            "top_mm": self.top_mm,
            "bottom_mm": self.bottom_mm,
            "gutter_mm": self.gutter_mm,
            "outside_mm": self.outside_mm,
            "band_mm": self.band_mm,
        }
        for name, value in measurements.items():
            if not _is_real(value):
                raise ValueError(f"PageSpec.{name} must be a finite number, not {value!r}")
        if self.width_mm <= 0 or self.height_mm <= 0:
            raise ValueError(
                f"PageSpec trim must be positive, not {self.width_mm} x {self.height_mm} mm"
            )
        for name in ("top_mm", "bottom_mm", "gutter_mm", "outside_mm", "band_mm"):
            if measurements[name] < 0:
                raise ValueError(f"PageSpec.{name} must not be negative, not {measurements[name]}")
        # Exactly, as the placed path computes it, so that a spec accepted
        # here is never one the layout finds to have no usable area.
        usable_width = (
            _exact_mm(self.width_mm) - _exact_mm(self.gutter_mm) - _exact_mm(self.outside_mm)
        )
        usable_height = (
            _exact_mm(self.height_mm)
            - _exact_mm(self.top_mm)
            - _exact_mm(self.bottom_mm)
            - _exact_mm(self.band_mm)
        )
        if usable_width <= 0 or usable_height <= 0:
            raise ValueError(
                "PageSpec usable area is non-positive: "
                f"{self.usable_width_mm:g} x {self.usable_height_mm:g} mm "
                "(trim minus margins minus band)"
            )
        if not isinstance(self.orientation, OrientationPolicy):
            raise ValueError(f"PageSpec.orientation must be an OrientationPolicy, not {self.orientation!r}")
        if not isinstance(self.cell_cap, CellCapPolicy) and not (
            _is_real(self.cell_cap) and self.cell_cap > 0
        ):
            raise ValueError(
                "PageSpec.cell_cap must be CellCapPolicy.COMFORT_CURVE or a finite "
                f"positive number of mm, not {self.cell_cap!r}"
            )
        if self.min_thin_rule_mm is not None and not (
            _is_real(self.min_thin_rule_mm) and self.min_thin_rule_mm > 0
        ):
            raise ValueError(
                "PageSpec.min_thin_rule_mm must be None or a finite positive number "
                f"of mm, not {self.min_thin_rule_mm!r}"
            )
        if self.parity is not None and not isinstance(self.parity, PageParity):
            raise ValueError(f"PageSpec has an invalid parity {self.parity!r}: use PageParity or None")
        if self.parity is None and len(
            {self.top_mm, self.bottom_mm, self.gutter_mm, self.outside_mm}
        ) != 1:
            raise ValueError(
                "a PageSpec without parity lays out a drawing-sized image with one "
                "uniform border, so its four margins must be equal"
            )
        if self.parity is not None and self.orientation is not OrientationPolicy.PORTRAIT_ONLY:
            raise ValueError("a placed page (a PageSpec with parity) is never turned: use PORTRAIT_ONLY")

    @property
    def left_margin_mm(self) -> float:
        """The margin on the page's left: the gutter unless this is an even page."""
        return self.outside_mm if self.parity is PageParity.EVEN else self.gutter_mm

    @property
    def right_margin_mm(self) -> float:
        """The margin on the page's right: the outside margin unless this is an even page."""
        return self.gutter_mm if self.parity is PageParity.EVEN else self.outside_mm

    @property
    def usable_width_mm(self) -> float:
        """Trim width minus both side margins. The same on either parity."""
        return self.width_mm - self.gutter_mm - self.outside_mm

    @property
    def usable_height_mm(self) -> float:
        """Trim height minus top and bottom margins minus the band."""
        return self.height_mm - self.top_mm - self.bottom_mm - self.band_mm


#: Today's sheet, as a spec: A4 upright, 12 mm margins, the header band, NFR-006's
#: larger-cell-wins turning, NFR-005's comfort curve, the ``cell / 30`` strokes and
#: no parity. ``compute_layout(r, c)`` and ``compute_layout(r, c, DEFAULT_PAGE_SPEC)``
#: are the same call (ADR-0036/R1, G-6).
DEFAULT_PAGE_SPEC = PageSpec(
    width_mm=PAGE_WIDTH_MM,
    height_mm=PAGE_HEIGHT_MM,
    top_mm=PAGE_MARGIN_MM,
    bottom_mm=PAGE_MARGIN_MM,
    gutter_mm=PAGE_MARGIN_MM,
    outside_mm=PAGE_MARGIN_MM,
    band_mm=HEADER_BAND_MM,
    orientation=OrientationPolicy.LARGER_CELL_WINS,
    cell_cap=CellCapPolicy.COMFORT_CURVE,
    min_thin_rule_mm=None,
    parity=None,
)


@dataclass(frozen=True, slots=True)
class PagePlacement:
    """Where a placed page's drawing sits on its trim, in device pixels (ADR-0036).

    Only a spec with a parity produces one. It is everything a caller needs to
    put the band and the drawing on the page without fitting a cell or placing
    a line itself (ADR-0036/R2). The origin is the trim's top-left corner.

    Attributes:
        parity: The page's side of the spread.
        cell_mm: The cell, exactly: ``min(cap, page fit)`` in millimetres, never
            above the cap and never below :data:`MIN_CELL_MM`. It is the number a
            book tile shows (FR-031). The drawing prints it as the pitch between
            grid lines, each line rounded to the nearest device pixel.
        usable_left: The usable area's left edge, i.e. the left margin.
        usable_top: The usable area's top edge, i.e. the top margin. The title
            band starts here.
        usable_right: The usable area's right edge.
        usable_bottom: The usable area's bottom edge.
        drawing_left: The drawing's left edge (the row-clue gutter's outer edge).
        drawing_top: The drawing's top edge (the column-clue gutter's outer
            edge), always ``usable_top`` + band, on every page and parity.
        drawing_right: The grid's right edge.
        drawing_bottom: The grid's bottom edge.
    """

    parity: PageParity
    cell_mm: float
    usable_left: int
    usable_top: int
    usable_right: int
    usable_bottom: int
    drawing_left: int
    drawing_top: int
    drawing_right: int
    drawing_bottom: int

    @property
    def fits(self) -> bool:
        """Whether the drawing lies inside the usable area below the band.

        ``False`` only when page fit fell under :data:`MIN_CELL_MM` and the
        floor won. The drawing then overflows to the right and downwards.
        """
        return (
            self.usable_left <= self.drawing_left
            and self.drawing_right <= self.usable_right
            and self.drawing_bottom <= self.usable_bottom
        )


@dataclass(frozen=True, slots=True)
class GridLine:
    """One ruled line of the grid, positioned along its own axis.

    Attributes:
        index: Which boundary this is, ``0`` for the top/left edge through
            ``rows``/``columns`` for the bottom/right one.
        position: The line's coordinate on its axis, in device pixels — ``x``
            for a vertical line, ``y`` for a horizontal one.
        start: Where the line begins on the *other* axis, in device pixels.
        end: Where it ends.
        width: How heavy to stroke it — :attr:`Layout.thin_rule` or
            :attr:`Layout.thick_rule`.
        major: Whether this is one of the every-5th (or outer-border) rules.
            Carried separately from :attr:`width` because it is the *reason*
            for the width, and a renderer may want to say so (a different ink,
            a different SVG class) without re-deriving the modulo.
    """

    index: int
    position: int
    start: int
    end: int
    width: int
    major: bool


@dataclass(frozen=True, slots=True)
class ClueEntry:
    """One clue number, and the point it is centred on.

    Attributes:
        value: The run length, exactly as ``nonogram.clues`` encoded it — the
            ``0`` of an empty line included (AC-013), which prints as a real
            ``0`` because that is what the clue set says.
        line: Which row or column the clue belongs to, 0-based.
        depth: How far into the gutter the entry sits, 0-based from the outer
            edge. Right-aligned for rows and bottom-aligned for columns, so
            the last entry of every clue always abuts the grid.
        center_x: The horizontal centre of the entry's box, in device pixels.
        center_y: The vertical centre. Both renderers draw text centred on
            this point, which is the one placement rule that does not depend
            on how a given library measures a glyph.
    """

    value: int
    line: int
    depth: int
    center_x: int
    center_y: int


@dataclass(frozen=True, slots=True)
class Layout:
    """The complete geometry of one rendered puzzle, in device pixels.

    The origin is the image's top-left corner and ``y`` grows downward, which
    is both Pillow's convention and SVG's, so neither renderer has to flip
    anything.

    Attributes:
        rows: Grid height in cells.
        columns: Grid width in cells.
        orientation: Which way up the A4 sheet this cell was sized against
            (NFR-006) — ``"landscape"`` when the turned sheet printed a larger
            cell for this puzzle, ``"portrait"`` otherwise, ties included. It
            is not a coordinate: the drawing is measured to its own extent, so
            no renderer has to rotate anything. It is recorded because it names
            the sheet page fit was computed against, and neither a reader of a
            :class:`Layout` nor the extent it carries can tell which sheet a
            6.86 mm cell came off — two puzzles of the same extent can be on
            different ones.
        cell: The side of one square cell.
        margin: The blank border on all four sides.
        row_gutter_cells: How many clue boxes deep the left gutter is — the
            length of the longest row clue.
        column_gutter_cells: The same for the top gutter.
        width: Total image width.
        height: Total image height.
        grid_left: ``x`` of the grid's left edge, i.e. the right edge of the
            row-clue gutter.
        grid_top: ``y`` of the grid's top edge.
        grid_right: ``x`` of the grid's right edge.
        grid_bottom: ``y`` of the grid's bottom edge.
        thin_rule: Stroke width of an ordinary grid line.
        thick_rule: Stroke width of an every-5th or outer-border line.
        clue_font_size: The size to draw a clue number at.
        vertical_lines: Column boundaries, left to right — ``columns + 1`` of
            them, each spanning the full height inside the margins.
        horizontal_lines: Row boundaries, top to bottom — ``rows + 1``, each
            spanning the full width inside the margins.
        row_clues: The left gutter's numbers, already placed.
        column_clues: The top gutter's numbers, already placed.
        dpi: The resolution :attr:`width` and :attr:`height` are expressed at,
            so a renderer can tag its output with the physical size it means.
        page: ``None`` for a drawing-sized image (the default spec's path, so
            the default ``Layout`` is exactly what it always was). For a placed
            page (a :class:`PageSpec` with a parity) it is the
            :class:`PagePlacement`, and several fields above read differently:
            every coordinate is on the trim, :attr:`width`/:attr:`height` are
            the trim, :attr:`cell` is the pitch floored to a whole pixel (the
            exact cell is :attr:`PagePlacement.cell_mm`), and :attr:`margin` is
            the top margin. The lines start at the drawing's edges rather than
            at :attr:`margin`.
    """

    rows: int
    columns: int
    orientation: Orientation
    cell: int
    margin: int
    row_gutter_cells: int
    column_gutter_cells: int
    width: int
    height: int
    grid_left: int
    grid_top: int
    grid_right: int
    grid_bottom: int
    thin_rule: int
    thick_rule: int
    clue_font_size: int
    vertical_lines: tuple[GridLine, ...]
    horizontal_lines: tuple[GridLine, ...]
    row_clues: tuple[ClueEntry, ...]
    column_clues: tuple[ClueEntry, ...]
    dpi: int = DPI
    page: PagePlacement | None = None

    @property
    def clue_entries(self) -> tuple[ClueEntry, ...]:
        """Every placed clue number, rows first then columns."""
        return self.row_clues + self.column_clues

    @property
    def grid_lines(self) -> tuple[GridLine, ...]:
        """Every ruled line, verticals first then horizontals."""
        return self.vertical_lines + self.horizontal_lines

    @property
    def width_inches(self) -> float:
        """:attr:`width` as a physical measurement at :attr:`dpi`."""
        return self.width / self.dpi

    @property
    def height_inches(self) -> float:
        """:attr:`height` as a physical measurement at :attr:`dpi`."""
        return self.height / self.dpi


@dataclass(frozen=True, slots=True)
class HeaderBand:
    """The strip a titled page carries above the drawing (FR-016).

    Attributes:
        height: How tall the band is, in device pixels — what the page grows
            by, and how far down the puzzle drawing moves.
        center_x: The horizontal centre of the band.
        center_y: The vertical centre, measured from the *page's* top edge
            (which is the band's own top edge, the band being the first thing
            on the page). A renderer centres the title on ``(center_x,
            center_y)``, the same ``anchor="mm"`` placement rule the clue
            numbers use.
        font_size: The size to set the title in.
    """

    height: int
    center_x: int
    center_y: int
    font_size: int


def header_band(layout: Layout, page_spec: PageSpec | None = None) -> HeaderBand:
    """Measure the title strip for a page drawn to ``layout`` (FR-016).

    Why this is a second function and not a parameter of
    :func:`compute_layout`
    ----------------------------------------------------------------------
    Only the PDF carries a header: FR-011's PNG and SVG are the bare printable
    puzzle, and CON-006 makes the PDF a second *sink* on that same raster
    rather than a second drawing. Folding a header into
    :func:`compute_layout` would move ``grid_top`` — and with it every clue
    centre and every ruled line — for all three renderers, so a format that
    shows no header would still be paying for one in its coordinates. Measured
    separately and added on top, the band is strictly additive: the PNG and the
    PDF's puzzle page are the same pixels, offset by :attr:`HeaderBand.height`.

    What *is* shared is the band's claim on the sheet. :func:`_fit_cell`
    reserves :data:`HEADER_BAND_MM` out of the printable height for every
    format, because all three read one :func:`compute_layout` and a cell chosen
    without the band is a cell the PDF cannot fit on A4 (NFR-005 defines page
    fit over drawing *plus* band for exactly this reason). So the band is free
    in a headerless format's coordinates and not quite free in its cell — and
    only where the height term binds at all, which on a portrait sheet needs a
    drawing about 1.40x taller than it is wide, and on a landscape one only
    about 0.64x.

    Measured cost, over CON-011's 441 extents at each of the **four** clue
    patterns :mod:`tests.property.test_layout_cell_size` sweeps — naming them
    rather than counting them, because two different three-pattern subsets of
    this corpus both have 1323 cases and quoting a bare denominator has already
    caused one round of confusion:

    ===================  ================
    pattern              cells moved /441
    ===================  ================
    ``_random_grid``                   74
    ``_checkerboard``                 151
    ``_sparse``                        10
    ``_alternating_rows``             118
    ===================  ================

    **353 of 1764 (20.0%)** over the whole corpus, by at most 0.5080mm —
    exactly six device pixels at :data:`DPI`. Counted the way the question is
    actually asked: drop the reservation and let NFR-006 re-choose the sheet
    without it, since the band now moves the orientation as well as the cell.
    Those counts were 3, 58, 0 and 111 (172 of 1764, 9.8%, at most three
    pixels) when every page was portrait, and they doubled because a landscape
    sheet has 174 mm of printable height to a portrait one's 261 mm: the band's
    12 mm is a much larger share of a much smaller axis, so the height term it
    comes out of binds on most landscape drawings rather than on a tall
    minority. The reservation is correspondingly more load-bearing than it was,
    not less — ``_sparse``, which never moved a single cell before, now moves
    ten.

    The type size is physical (:data:`HEADER_FONT_MM` at :data:`DPI`) and not a
    fraction of the cell, unlike :attr:`Layout.clue_font_size`. A clue digit has
    to fit inside its cell, so it must scale with it; a title has a whole page
    width to sit in and only has to be legible, and pinning it to the cell would
    set a 30x30 puzzle's header in the same 3 mm type as its clues.

    On a placed page (``layout.page`` set) the band is not laid *above* the
    image. It is the strip of the trim between the top margin and the
    drawing, ``[page.usable_top, page.drawing_top)``, so ``center_y`` is
    measured from the trim's top edge, and the renderer draws into the page it
    already has. A trim cannot grow.

    Args:
        layout: The geometry of the page the band belongs to — read for its
            width (or, on a placed page, its drawing edges), so the title is
            centred over the drawing.
        page_spec: The spec ``layout`` was computed with, for the band's
            height on a drawing-sized image. ``None`` is the default spec.
            A placed page carries its band in ``layout.page``.

    Returns:
        The :class:`HeaderBand` the renderer draws into.
    """
    font_size = _mm_to_px(HEADER_FONT_MM)
    page = layout.page
    if page is None:
        spec = DEFAULT_PAGE_SPEC if page_spec is None else page_spec
        height = _mm_to_px(spec.band_mm)
        return HeaderBand(
            height=height,
            center_x=layout.width // 2,
            center_y=height // 2,
            font_size=max(1, min(font_size, height)),
        )
    height = page.drawing_top - page.usable_top
    return HeaderBand(
        height=height,
        center_x=(page.drawing_left + page.drawing_right) // 2,
        center_y=page.usable_top + height // 2,
        font_size=max(1, min(font_size, height)),
    )


def _mm_to_px(millimetres: float) -> int:
    """Millimetres at :data:`DPI`, rounded to a whole device pixel."""
    return round(millimetres / 25.4 * DPI)


def _gutter_depth(clue_set: ClueSet) -> int:
    """How many clue boxes deep a gutter has to be for ``clue_set``.

    The longest clue in the set, and never less than one: an all-empty line
    still carries the ``(0,)`` marker, so every clue occupies at least one box
    and a gutter of zero would leave a puzzle's clues nowhere to go.
    """
    return max((len(clue) for clue in clue_set), default=1)


def _mm_to_px_at_least(millimetres: float) -> int:
    """The fewest whole device pixels that measure *at least* ``millimetres``.

    Rounding up rather than to nearest, for a minimum: ADR-0037/R2's 0.25 mm is
    2.95 px, and rounding to nearest would still give 3 px, but only by luck.
    The tolerance absorbs float noise on an exact pixel count (25.4 mm is
    exactly 300 px and must not become 301).
    """
    return math.ceil(millimetres / 25.4 * DPI - 1e-9)


def _page_size_mm(
    orientation: Orientation, page_spec: PageSpec = DEFAULT_PAGE_SPEC
) -> tuple[float, float]:
    """The spec's sheet width and height in millimetres, held that way up.

    The single place the spec's width and height are allowed to swap. A sheet
    is the same sheet either way (no tiling); only the axis each measurement
    lands on changes. There is no second paper size unless the caller passes
    one (ADR-0036): the default spec is A4.
    """
    if orientation == "landscape":
        return page_spec.height_mm, page_spec.width_mm
    return page_spec.width_mm, page_spec.height_mm


def _cap_mm(larger_dimension: int, page_spec: PageSpec) -> float:
    """The spec's cell cap for a grid this many cells on its longer side."""
    if page_spec.cell_cap is CellCapPolicy.COMFORT_CURVE:
        return comfort_cap_mm(larger_dimension)
    return float(page_spec.cell_cap)


def comfort_cap_mm(larger_dimension: int) -> float:
    """How big a printed cell may be for a grid this many cells on its longer
    side, in millimetres (NFR-005).

    :data:`CELL_COMFORT_MM`'s five decided points, linearly interpolated
    between neighbours and held flat outside the range: a grid smaller than
    the first point gets the first point's value and one larger than the last
    gets the last's, because extrapolating a curve that was only ever decided
    over 10..30 would be inventing numbers rather than reading them. CON-011
    keeps every real puzzle inside that range anyway; the flat ends exist so
    that this is a total function on any int a caller can hold.

    Args:
        larger_dimension: ``max(columns, rows)`` of the **grid** — not of the
            drawing. The clue gutter widens the page, not the cell.

    Returns:
        The cell edge the cap allows, in millimetres. Non-increasing in
        ``larger_dimension``, and independent of orientation: a 12x10 and a
        10x12 share a cap, and the cap is the same number offered to both
        candidate sheets when :func:`_orientation_for` compares them (EC-008).
        That is why it decides where the two sheets *tie* — wherever the cap is
        the binding term on both, the cells are equal and the puzzle stays
        upright.
    """
    if larger_dimension <= CELL_COMFORT_MM[0][0]:
        return CELL_COMFORT_MM[0][1]
    for (left_cells, left_mm), (right_cells, right_mm) in zip(
        CELL_COMFORT_MM, CELL_COMFORT_MM[1:], strict=False
    ):
        if larger_dimension <= right_cells:
            travelled = (larger_dimension - left_cells) / (right_cells - left_cells)
            return left_mm + travelled * (right_mm - left_mm)
    return CELL_COMFORT_MM[-1][1]


def _fit_cell(
    total_columns: int,
    total_rows: int,
    *,
    larger_dimension: int,
    orientation: Orientation,
    reserved_height_mm: float,
    page_spec: PageSpec = DEFAULT_PAGE_SPEC,
) -> int:
    """The cell size in device pixels: ``min(comfort cap, page fit)`` (NFR-005).

    For a drawing-sized image (a spec without parity). The sheet, its uniform
    margin and the cap come from ``page_spec``. The default spec is A4, 12 mm
    and NFR-005's curve, and everything measured below is about that spec. A
    placed page is fitted by :func:`_placed_cell_mm` instead.

    Two measurements of the same cell, and they are functions of different
    things — which is why this takes both the drawing's totals and the grid's
    own longer side:

    * *page fit* is the largest cell whose whole page still fits the printable
      area of an A4 sheet held ``orientation`` way up — 186 mm across by 273 mm
      down, or 273 mm across by 186 mm down, which are different constraints on
      the same drawing. The way up is an **argument**, never something this
      function decides or looks up: that is what lets :func:`_orientation_for`
      call it once per sheet and keep the larger answer (NFR-006), and a
      version of this function that consulted the chosen orientation would make
      that comparison recursive. Gutters included, which is why
      ``total_columns``/``total_rows`` are totals and not the grid's own
      dimensions; and ``reserved_height_mm`` included too, which is the strip
      a renderer lays above the drawing without :func:`compute_layout` knowing
      any of its geometry.
    * the *comfort cap* is what :func:`comfort_cap_mm` assigns to
      ``larger_dimension``, the longer side of the grid alone — the one term
      of the two that a turned sheet leaves untouched, and therefore the term
      that decides when the two sheets tie.

    Why the reserved strip is a parameter here and a constant at the call site
    ----------------------------------------------------------------------
    The band is the PDF's, and only the PDF draws it — but the *cell* it
    implies is shared, because all three renderers read one
    :func:`compute_layout` and the PDF must be able to print the result. Taking
    the reservation as an argument rather than reading :data:`HEADER_BAND_MM`
    off the module keeps that a decision of the caller, visible at the one line
    that makes it, instead of a global this function silently consults. A
    caller that genuinely draws no band can pass ``0.0``; today none does, and
    the cost of the shared reservation is confined to drawings tall enough for
    the height term to bind at all — roughly 1.40x taller than wide on a
    portrait sheet (the reservation leaves 261mm of height against 186mm of
    width) and roughly 0.64x on a landscape one (174mm against 273mm), which
    is why turning the page makes the band's reservation bite more often, not
    less.

    The cap is a ceiling and page fit wins whenever it is the smaller of the
    two — over the four-pattern sweep, on 564 of the 1364 cases at 20 cells a
    side or more (see the module docstring). The cap is converted to whole
    pixels by truncation rather than rounding, so "the printed cell never
    exceeds the cap" (EC-008) holds exactly in millimetres instead of to within
    half a device pixel.

    :data:`MIN_CELL_MM` is the one clamp still allowed to win *over* page fit,
    exactly as before: below it the page is allowed to outgrow A4 rather than
    shrink past the point where a pencil mark is meaningless.
    """
    page_width_mm, page_height_mm = _page_size_mm(orientation, page_spec)
    # The four margins of a spec without parity are equal (PageSpec enforces
    # it), so one of them is the border on every side, whichever way up.
    margin_mm = page_spec.top_mm
    printable_width = _mm_to_px(page_width_mm - 2 * margin_mm)
    printable_height = _mm_to_px(page_height_mm - 2 * margin_mm) - _mm_to_px(
        reserved_height_mm
    )
    page_fit = min(
        printable_width // max(total_columns, 1),
        max(printable_height, 0) // max(total_rows, 1),
    )
    cap = int(_cap_mm(larger_dimension, page_spec) / 25.4 * DPI)
    return max(_mm_to_px(MIN_CELL_MM), min(cap, page_fit))


#: Millimetres per inch, exactly.
_MM_PER_INCH = Fraction("25.4")


def _exact_px(millimetres: float | Fraction) -> Fraction:
    """Millimetres at :data:`DPI`, as an exact (fractional) number of pixels."""
    return _exact_mm(millimetres) * DPI / _MM_PER_INCH


def _round_px(value: int | Fraction) -> int:
    """The nearest whole pixel, a half rounded up.

    Rounding half up rather than to even (``round``'s rule), so that a
    half-pixel margin (0.375 in is 112.5 px) always lands the same way,
    whatever the neighbouring digit. An int is returned unchanged, which is
    what keeps the drawing-sized path's integer arithmetic exact.
    """
    return math.floor(value + Fraction(1, 2))


def _placed_cell_mm(
    total_columns: int,
    total_rows: int,
    *,
    larger_dimension: int,
    page_spec: PageSpec,
) -> Fraction:
    """The cell of a placed page, exactly, in millimetres: ``min(cap, page fit)``.

    Page fit is FR-030's own definition: usable width (trim − gutter −
    outside) over the drawing's columns, and usable height (trim − top −
    bottom − band) over its rows. The drawing's totals are the real clue
    depths (:func:`_gutter_depth`) plus the grid. It is kept exact rather than
    floored to a pixel: at 300 DPI a whole-pixel cell cannot express the
    book's numbers (7.5 mm is 88.58 px; 4.61 mm is 54.46 px). The minimum is
    taken exactly, so the result never exceeds the cap, not even by a rounding
    step. Parity does not enter: it moves the usable area, never its size.

    :data:`MIN_CELL_MM` still wins over page fit, as it does on the default
    path. On a trim that cannot hold the drawing at 2 mm the drawing overflows
    (:attr:`PagePlacement.fits` is then ``False``) rather than printing cells
    nobody can mark.
    """
    usable_width = (
        _exact_mm(page_spec.width_mm)
        - _exact_mm(page_spec.gutter_mm)
        - _exact_mm(page_spec.outside_mm)
    )
    usable_height = (
        _exact_mm(page_spec.height_mm)
        - _exact_mm(page_spec.top_mm)
        - _exact_mm(page_spec.bottom_mm)
        - _exact_mm(page_spec.band_mm)
    )
    fit = min(usable_width / total_columns, usable_height / total_rows)
    cap = _exact_mm(_cap_mm(larger_dimension, page_spec))
    return max(_exact_mm(MIN_CELL_MM), min(cap, fit))


def _orientation_for(
    total_columns: int,
    total_rows: int,
    *,
    larger_dimension: int,
    reserved_height_mm: float,
    page_spec: PageSpec = DEFAULT_PAGE_SPEC,
) -> Orientation:
    """Which way up the sheet goes for this puzzle (NFR-006, EC-010).

    A spec whose policy is :attr:`OrientationPolicy.PORTRAIT_ONLY` answers
    ``"portrait"`` without measuring anything. Otherwise (the default spec):

    **Whichever sheet prints the larger cell**, with a tie going to portrait.
    Not a function of the grid's extent: the same 30x20 turns or does not
    according to how deep its clue gutters are, because what has to fit the
    paper is the drawing — grid plus both gutters plus the band a titled sheet
    carries — and a wide grid can draw tall behind a deep column gutter.

    The rule this replaced turned the sheet on the grid's *shape* (landscape
    iff ``columns > rows``). That states orientation over the grid while page
    fit is governed by the drawing, and it costs cell size on 102 of the 882
    cases in CON-011's range at the two gutter-heavy clue patterns
    :mod:`tests.property.test_layout_cell_size` sweeps: worst is a
    26x25 whose rows alternate full and empty, which draws 27 cells across by
    38 down and so prints 6.86 mm upright against the 4.57 mm the landscape
    sheet its shape asks for would give — a 33% loss. Mean printed cell over
    the same corpus: 6.626 mm on the shape rule, 6.749 mm here.

    Why the comparison and not a formula
    ------------------------------------
    There is no closed form to compare against. "Turn it if the *drawing* is
    wider than it is tall" is the obvious approximation and is circular: a
    drawing's extent in millimetres depends on the cell, the cell depends on
    page fit, and page fit depends on the orientation being chosen. Comparing
    the two fitted cells has no such loop — :func:`_fit_cell` takes the
    orientation as an argument and never asks which one was chosen, so it can
    be evaluated for both sheets and the larger answer kept. **This is the one
    invariant to preserve here:** the dependency runs one way, from this
    function into :func:`_fit_cell`, and a "convenience" that had page fit
    consult the chosen orientation, or had this call :func:`compute_layout`,
    would close the loop into unbounded recursion.

    Ties go to portrait, and they are common rather than a corner: wherever the
    comfort cap is the binding term on both sheets the two cells are equal by
    construction. That is what keeps a small grid upright without a rule saying
    so. Swept over CON-011's 441 extents at the four clue patterns
    :mod:`tests.property.test_layout_cell_size` uses, 446 of the 1764 cases
    turn, concentrated at 27..30, and the smallest larger-dimension that turns
    at all is 16: of the 144 cases at 15 or fewer, 132 tie on the cap and the
    remaining 12 are won outright by portrait. So a small puzzle is never
    turned gratuitously — it turns only once it is genuinely page-constrained,
    which is when turning buys something. That is a consequence of the
    comparison, not a rule written alongside it, and NFR-006/AC-106 record it
    as such.

    Args:
        total_columns: The drawing's width in cells — the grid plus its row
            gutter, exactly what :func:`_fit_cell` measures.
        total_rows: The drawing's height in cells, gutter included.
        larger_dimension: ``max(columns, rows)`` of the grid, for the comfort
            cap. Orientation-independent, but it decides where the cap binds
            and therefore where the two sheets tie.
        reserved_height_mm: The strip reserved above the drawing, passed
            through so both candidate sheets are measured on the same terms as
            the one that wins.

    Returns:
        ``"landscape"`` when the turned sheet prints a strictly larger cell,
        ``"portrait"`` otherwise.
    """
    if page_spec.orientation is OrientationPolicy.PORTRAIT_ONLY:
        return "portrait"
    upright = _fit_cell(
        total_columns,
        total_rows,
        larger_dimension=larger_dimension,
        orientation="portrait",
        reserved_height_mm=reserved_height_mm,
        page_spec=page_spec,
    )
    turned = _fit_cell(
        total_columns,
        total_rows,
        larger_dimension=larger_dimension,
        orientation="landscape",
        reserved_height_mm=reserved_height_mm,
        page_spec=page_spec,
    )
    return "landscape" if turned > upright else "portrait"


def _rule_widths(cell: float, page_spec: PageSpec = DEFAULT_PAGE_SPEC) -> tuple[int, int]:
    """The thin and heavy stroke widths for a given cell size.

    Kept proportional to the cell so the drawing looks the same at every size
    the clamp can produce, and the heavy rule is exactly twice the thin one —
    enough to read as "heavier" across a page without the every-5th lines
    reading as a second, coarser grid.

    A spec's ``min_thin_rule_mm`` (ADR-0037/R2, the book's 0.25 mm) raises the
    thin rule to at least that many millimetres, rounded *up* to whole pixels
    (3 px at 300 DPI), and never lowers it. The heavy rule stays exactly twice
    the thin one. The default spec has no minimum, so its strokes are
    unchanged. ``cell`` may be fractional on a placed page.
    """
    thin = max(1, round(cell * _THIN_RULE_RATIO))
    if page_spec.min_thin_rule_mm is not None:
        thin = max(thin, _mm_to_px_at_least(page_spec.min_thin_rule_mm))
    return thin, thin * 2


def _is_major(index: int, last: int) -> bool:
    """Is boundary ``index`` one of the heavy rules?

    Every :data:`MAJOR_RULE_EVERY`-th boundary counting from the top/left, plus
    the far edge — a 12-wide grid gets heavy rules at 0, 5, 10 and 12, so the
    frame is closed even when the width is not a multiple of five.
    """
    return index % MAJOR_RULE_EVERY == 0 or index == last




def _boundaries(
    origin: int | Fraction, pitch: int | Fraction, count: int
) -> tuple[int, ...]:
    """The ``count + 1`` box boundaries of one axis, from ``origin``, in whole pixels.

    ``_round_px(origin + index * pitch)``: each boundary is rounded on its own,
    so a fractional pitch (a placed page) never accumulates rounding error
    along the axis. Every boundary is within half a pixel of where it belongs.
    With an integer origin and an integer pitch (the drawing-sized path) the
    sum is already an int and this is exactly ``origin + index * cell``, as
    before.
    """
    return tuple(_round_px(origin + index * pitch) for index in range(count + 1))


def _axis_lines(
    positions: Sequence[int], *, start: int, end: int, thin: int, thick: int
) -> tuple[GridLine, ...]:
    """One ruled line per boundary in ``positions`` (``count + 1`` of them)."""
    last = len(positions) - 1
    return tuple(
        GridLine(
            index=index,
            position=position,
            start=start,
            end=end,
            width=thick if _is_major(index, last) else thin,
            major=_is_major(index, last),
        )
        for index, position in enumerate(positions)
    )


def _centre(boundaries: Sequence[int], box: int) -> int:
    """The centre of box ``box``: its near boundary plus half its own width.

    ``b + (b_next - b) // 2``. On an integer pitch that is ``b + cell // 2``,
    exactly one half-cell from the box's own boundary and never a rounding
    step away from where the matching grid line was placed.
    """
    near = boundaries[box]
    return near + (boundaries[box + 1] - near) // 2


def _place_row_clues(
    clue_set: ClueSet, *, depth: int, xs: Sequence[int], ys: Sequence[int]
) -> tuple[ClueEntry, ...]:
    """Lay the row clues out in the left gutter, right-aligned.

    Right-aligned rather than left-aligned so that the *last* number of every
    clue — the run that ends at the grid's edge — sits in the same column for
    every row, which is how a printed nonogram is read.

    ``xs`` are the drawing's column boundaries, gutter boxes first; ``ys`` its
    row boundaries from the grid's top edge.
    """
    return tuple(
        ClueEntry(
            value=value,
            line=row,
            depth=depth - len(clue) + offset,
            center_x=_centre(xs, depth - len(clue) + offset),
            center_y=_centre(ys, row),
        )
        for row, clue in enumerate(clue_set)
        for offset, value in enumerate(clue)
    )


def _place_column_clues(
    clue_set: ClueSet, *, depth: int, xs: Sequence[int], ys: Sequence[int]
) -> tuple[ClueEntry, ...]:
    """Lay the column clues out in the top gutter, bottom-aligned.

    The transpose of :func:`_place_row_clues`, and bottom-aligned for the same
    reason: the last number of each clue abuts the grid. ``xs`` are the grid's
    column boundaries; ``ys`` the drawing's row boundaries, gutter boxes first.
    """
    return tuple(
        ClueEntry(
            value=value,
            line=column,
            depth=depth - len(clue) + offset,
            center_x=_centre(xs, column),
            center_y=_centre(ys, depth - len(clue) + offset),
        )
        for column, clue in enumerate(clue_set)
        for offset, value in enumerate(clue)
    )


def compute_layout(
    row_clues: ClueSet, column_clues: ClueSet, page_spec: PageSpec | None = None
) -> Layout:
    """Measure the printed page for one puzzle's clues.

    Pure and total: same clues and sheet in, same numbers out, no I/O, no
    library types. The grid's dimensions come from the clue sets themselves
    (see the module docstring), and the blank grid is the only thing being
    measured — the solution never reaches this function, which is the
    structural reason the renderers cannot leak it onto a page they are only
    given coordinates for.

    The sheet's orientation is derived here too, from those same clue sets and
    the spec's policy: under NFR-006 the cell is measured on both sheets and
    the larger one wins, ties staying upright (:func:`_orientation_for`). It is
    deliberately *not* a parameter — a caller that had to supply it would have
    to know not just the extent but the gutters, and the whole reason this
    function reads its dimensions off the clues is that nothing upstream should
    have to hand them over twice. A spec can only *forbid* turning
    (``PORTRAIT_ONLY``), never pick a side.

    Args:
        row_clues: Row clues, top to bottom, in the ADR-0012 boundary type.
        column_clues: Column clues, left to right.
        page_spec: The sheet (ADR-0036). ``None`` and :data:`DEFAULT_PAGE_SPEC`
            are the same call and give today's A4 geometry exactly. A spec with
            a parity lays the puzzle out on its trim (see the module docstring).

    Returns:
        The :class:`Layout` the renderers draw from.

    Raises:
        ValueError: one clue set is empty while the other is not — a grid with
            rows but no columns (or the reverse) cannot be drawn, and is a
            pipeline bug rather than a puzzle.
        TypeError: ``page_spec`` is neither ``None`` nor a :class:`PageSpec`.
    """
    if page_spec is None:
        spec = DEFAULT_PAGE_SPEC
    elif isinstance(page_spec, PageSpec):
        spec = page_spec
    else:
        raise TypeError(f"page_spec must be a PageSpec or None, not {type(page_spec).__name__}")

    rows, columns = len(row_clues), len(column_clues)
    if bool(rows) != bool(columns):
        raise ValueError(
            f"clue sets disagree about the grid: {rows} row clue(s) but "
            f"{columns} column clue(s); a grid has either both or neither"
        )

    row_gutter_cells = _gutter_depth(row_clues)
    column_gutter_cells = _gutter_depth(column_clues)

    # The two terms of NFR-005 read different things off the same puzzle: page
    # fit measures the page (grid + gutters + the header band a titled sheet
    # carries above them) against a sheet held a given way up, the cap
    # measures the grid. NFR-006 picks the way up by measuring the cell both
    # ways and keeping the larger, so the same four numbers describe the
    # drawing for the choice and for the cell that follows it — named once
    # here rather than threaded through, so the two cannot drift apart. All of
    # them come from the clue sets and the spec, so compute_layout still needs
    # nothing else (G-4), and the orientation is derived here rather than
    # passed in so that no caller has to know the extent.
    drawing_columns = row_gutter_cells + columns
    drawing_rows = column_gutter_cells + rows
    larger_dimension = max(columns, rows)

    placement: PagePlacement | None
    if spec.parity is None:
        # A drawing-sized image: today's path, every number from the spec.
        orientation = _orientation_for(
            drawing_columns,
            drawing_rows,
            larger_dimension=larger_dimension,
            reserved_height_mm=spec.band_mm,
            page_spec=spec,
        )
        cell = _fit_cell(
            drawing_columns,
            drawing_rows,
            larger_dimension=larger_dimension,
            orientation=orientation,
            reserved_height_mm=spec.band_mm,
            page_spec=spec,
        )
        margin = _mm_to_px(spec.top_mm)
        pitch: int | Fraction = cell
        left: int | Fraction = margin
        top: int | Fraction = margin
        cell_mm: float | None = None
    else:
        # A placed page: the trim is the image, and every coordinate is exact
        # (a Fraction of a pixel) until the one rounding step per boundary in
        # _boundaries. That is what makes "the drawing fits the usable area"
        # and "parity never changes the usable size" exact rather than true
        # to within a float's last bit.
        orientation = "portrait"
        exact_cell_mm = _placed_cell_mm(
            drawing_columns,
            drawing_rows,
            larger_dimension=larger_dimension,
            page_spec=spec,
        )
        cell_mm = float(exact_cell_mm)
        pitch = _exact_px(exact_cell_mm)
        cell = math.floor(pitch)
        usable_left_px = _exact_px(spec.left_margin_mm)
        usable_width_px = (
            _exact_px(spec.width_mm) - _exact_px(spec.gutter_mm) - _exact_px(spec.outside_mm)
        )
        # Centred across the usable width (FR-032). Only when the MIN_CELL_MM
        # floor has made the drawing wider than the usable area does it anchor
        # at the usable area's left edge instead, overflowing to the right.
        spare = usable_width_px - drawing_columns * pitch
        left = usable_left_px + max(spare, Fraction(0)) / 2
        # The top edge is fixed: top margin + band, on every page (FR-032).
        top = _exact_px(spec.top_mm) + _exact_px(spec.band_mm)
        page_width = _round_px(_exact_px(spec.width_mm))
        page_height = _round_px(_exact_px(spec.height_mm))
        usable_left = _round_px(usable_left_px)
        usable_right = _round_px(usable_left_px + usable_width_px)
        usable_top = _round_px(_exact_px(spec.top_mm))
        usable_bottom = _round_px(_exact_px(spec.height_mm) - _exact_px(spec.bottom_mm))
        margin = usable_top

    xs = _boundaries(left, pitch, drawing_columns)
    ys = _boundaries(top, pitch, drawing_rows)
    grid_xs = xs[row_gutter_cells:]
    grid_ys = ys[column_gutter_cells:]
    grid_left, grid_right = grid_xs[0], grid_xs[-1]
    grid_top, grid_bottom = grid_ys[0], grid_ys[-1]
    thin, thick = _rule_widths(pitch, spec)

    if cell_mm is None:
        placement = None
        width, height = grid_right + margin, grid_bottom + margin
    else:
        placement = PagePlacement(
            parity=spec.parity,
            cell_mm=cell_mm,
            usable_left=usable_left,
            usable_top=usable_top,
            usable_right=usable_right,
            usable_bottom=usable_bottom,
            drawing_left=xs[0],
            drawing_top=ys[0],
            drawing_right=grid_right,
            drawing_bottom=grid_bottom,
        )
        width, height = page_width, page_height

    return Layout(
        rows=rows,
        columns=columns,
        orientation=orientation,
        cell=cell,
        margin=margin,
        row_gutter_cells=row_gutter_cells,
        column_gutter_cells=column_gutter_cells,
        width=width,
        height=height,
        grid_left=grid_left,
        grid_top=grid_top,
        grid_right=grid_right,
        grid_bottom=grid_bottom,
        thin_rule=thin,
        thick_rule=thick,
        clue_font_size=max(1, round(pitch * _CLUE_FONT_RATIO)),
        # Both axes span the gutters as well as the grid: a vertical line
        # continues up through the column-clue gutter so its clue reads as
        # belonging to that column, and vice versa.
        vertical_lines=_axis_lines(
            grid_xs, start=ys[0], end=grid_bottom, thin=thin, thick=thick
        ),
        horizontal_lines=_axis_lines(
            grid_ys, start=xs[0], end=grid_right, thin=thin, thick=thick
        ),
        row_clues=_place_row_clues(row_clues, depth=row_gutter_cells, xs=xs, ys=grid_ys),
        column_clues=_place_column_clues(
            column_clues, depth=column_gutter_cells, xs=grid_xs, ys=ys
        ),
        page=placement,
    )


# ---------------------------------------------------------------------------
# Two-up pages (FR-040, ADR-0036 clarification "Two-up pages", CARD-125)
# ---------------------------------------------------------------------------

#: FR-040's two-up minimum, in millimetres: two puzzles share a book page only
#: at a shared cell of at least this much. It sits inside NFR-008's 4.8..7.5 mm
#: book range, so a two-up page never uses the 4.8 mm floor or its override;
#: the spec's flat cap (the 7.5 mm standard cell) still caps the shared cell.
#: A named constant rather than a :class:`PageSpec` field: it is the owner's
#: rule for every book, not a property of a trim.
TWO_UP_MIN_CELL_MM = 7.0


@dataclass(frozen=True, slots=True)
class PairLayout:
    """Two puzzles laid out on one book page at one shared cell (FR-040, TERM-030).

    A value object, valid by construction: :meth:`__post_init__` refuses any
    pair that is not a two-up page, so a caller holding one never re-checks it.

    Each slot is an ordinary placed-page :class:`Layout` on the page's trim, so
    the renderers draw it exactly as they draw a single puzzle page, and
    :func:`header_band` measures each slot's own band from it. The one
    difference is what a slot's :class:`PagePlacement` calls its usable area:
    across, it is the page's usable width (each slot's drawing is centred on it,
    FR-032); down, it is **the slot's own share** of the usable height —
    ``usable_top`` is where the slot's band starts and ``usable_bottom`` where
    the slot ends. The upper slot runs from the top margin to the lower slot's
    band; the lower slot from its band to the bottom margin. So
    ``upper.page.usable_bottom == lower.page.usable_top``, the slots never
    overlap, and ``page.fits`` holding on each slot is "both drawings with
    their bands lie inside the usable area without overlapping" (EC-028).

    Attributes:
        upper: The earlier puzzle in the book order. Its drawing's top edge is
            top margin + band, the same fixed row as a single puzzle page
            (FR-032, EC-022).
        lower: The later puzzle, under its own band. Its drawing's bottom edge
            is the bottom margin, so whatever height the pair leaves spare falls
            *between* the two slots: the lower band then sits against the
            puzzle it labels, never midway between two drawings.
        cell_mm: The shared cell, exactly as both slots report it
            (:attr:`PagePlacement.cell_mm`): at least :data:`TWO_UP_MIN_CELL_MM`
            and never above the spec's flat cap.

    Raises:
        ValueError: a slot is not a placed page, the slots disagree about the
            cell, the page or its parity, the cell is below
            :data:`TWO_UP_MIN_CELL_MM`, the slots overlap, or a drawing lies
            outside its slot.
    """

    upper: Layout
    lower: Layout
    cell_mm: float

    def __post_init__(self) -> None:
        upper, lower = self.upper.page, self.lower.page
        if upper is None or lower is None:
            raise ValueError("both slots of a two-up page must be placed-page layouts")
        if not (upper.cell_mm == lower.cell_mm == self.cell_mm):
            raise ValueError(
                "both slots of a two-up page print at one shared cell, not "
                f"{upper.cell_mm} and {lower.cell_mm} mm (pair says {self.cell_mm})"
            )
        if upper.parity is not lower.parity or (self.upper.width, self.upper.height) != (
            self.lower.width,
            self.lower.height,
        ):
            raise ValueError("both slots of a two-up page must be on the same page")
        if self.cell_mm < TWO_UP_MIN_CELL_MM:
            raise ValueError(
                f"a two-up page's shared cell is at least {TWO_UP_MIN_CELL_MM} mm, not {self.cell_mm}"
            )
        if upper.usable_bottom > lower.usable_top:
            raise ValueError("the slots of a two-up page must not overlap")
        if not (upper.fits and lower.fits):
            raise ValueError("each drawing of a two-up page must lie inside its own slot")


def compute_pair_layout(
    first: tuple[ClueSet, ClueSet],
    second: tuple[ClueSet, ClueSet],
    page_spec: PageSpec,
) -> PairLayout | None:
    """Lay two puzzles out on one book page at one shared cell, or decline (FR-040).

    The pair-aware call of ADR-0036's "Two-up pages" clarification. It decides
    only the geometry of one page: whether this pair fits two-up, at what cell,
    and where each slot sits. Which neighbours to offer it (same tier, adjacent
    in the book order, the in-order walk; INV-010, EC-027) is the book's
    decision, and a single puzzle keeps using :func:`compute_layout`.

    The shared cell is the largest cell, capped at the spec's flat cap, at which
    (a) both drawings' heights — grid rows plus column-clue rows of each —
    plus one band per puzzle fit the usable height (trim − top − bottom), and
    (b) each drawing's width — grid columns plus row-clue columns — fits the
    usable width. Clue depths are the real ones (:func:`_gutter_depth`,
    TERM-021). That is exactly :func:`_placed_cell_mm` of one combined drawing
    — the wider of the two drawings across, the two stacked down — on the same
    spec with a second band reserved, so the pair is fitted by the same code,
    exactly, as a single page: there is no second implementation of cell
    fitting. Each slot is then built from the same helpers as
    :func:`compute_layout`'s placed page (:func:`_boundaries`,
    :func:`_rule_widths`, :func:`_axis_lines`, the clue placers), so strokes,
    the every-5th rules and clue positions are the single page's.

    Args:
        first: ``(row_clues, column_clues)`` of the earlier puzzle in the book
            order. It takes the upper slot.
        second: ``(row_clues, column_clues)`` of the later one, the lower slot.
        page_spec: The book page: a placed page (a parity, hence portrait
            only) with a flat cell cap. The spec's own ``band_mm`` is each
            slot's band.

    Returns:
        The :class:`PairLayout`, or ``None`` when the largest fitting cell is
        below :data:`TWO_UP_MIN_CELL_MM` (or the usable height cannot hold even
        the two bands). ``None`` is a verdict on a valid pair — print them on
        separate pages — never an error.

    Raises:
        TypeError: ``page_spec`` is not a :class:`PageSpec`.
        ValueError: ``page_spec`` is not a placed page with a flat cap (so the
            default A4 spec never pairs), ``first`` or ``second`` is not a
            ``(row_clues, column_clues)`` pair, or one of its clue sets is empty
            while the other is not.
    """
    if not isinstance(page_spec, PageSpec):
        raise TypeError(f"page_spec must be a PageSpec, not {type(page_spec).__name__}")
    if page_spec.parity is None or page_spec.cell_cap is CellCapPolicy.COMFORT_CURVE:
        raise ValueError(
            "a two-up page is laid out only on a placed, portrait-only page with a flat "
            "cell cap (a PageSpec with a parity and a cap in mm); this spec "
            f"(parity {page_spec.parity}, cap {page_spec.cell_cap}) never pairs"
        )
    upper_rows, upper_columns = _pair_member(first, "first")
    lower_rows, lower_columns = _pair_member(second, "second")

    upper_down = _gutter_depth(upper_columns) + len(upper_rows)
    lower_down = _gutter_depth(lower_columns) + len(lower_rows)
    across = max(
        _gutter_depth(upper_rows) + len(upper_columns),
        _gutter_depth(lower_rows) + len(lower_columns),
    )

    # One band per puzzle. Checked exactly as PageSpec checks its own usable
    # area, so the two-band spec below is always constructible when reached.
    two_bands_mm = 2 * page_spec.band_mm
    pair_height_mm = (
        _exact_mm(page_spec.height_mm)
        - _exact_mm(page_spec.top_mm)
        - _exact_mm(page_spec.bottom_mm)
        - _exact_mm(two_bands_mm)
    )
    if pair_height_mm <= 0:
        return None
    exact_cell_mm = _placed_cell_mm(
        across,
        upper_down + lower_down,
        larger_dimension=max(
            len(upper_rows), len(upper_columns), len(lower_rows), len(lower_columns)
        ),
        page_spec=replace(page_spec, band_mm=two_bands_mm),
    )
    if exact_cell_mm < _exact_mm(TWO_UP_MIN_CELL_MM):
        return None

    pitch = _exact_px(exact_cell_mm)
    band = _exact_px(page_spec.band_mm)
    # The upper band starts at the top margin (the single page's fixed row);
    # the lower drawing ends at the bottom margin. The fit above guarantees
    # upper_top + band + upper_down x pitch <= lower_band_top.
    upper_band_top = _exact_px(page_spec.top_mm)
    page_bottom = _exact_px(page_spec.height_mm) - _exact_px(page_spec.bottom_mm)
    lower_band_top = page_bottom - lower_down * pitch - band
    cell_mm = float(exact_cell_mm)
    return PairLayout(
        upper=_slot_layout(
            upper_rows,
            upper_columns,
            page_spec,
            cell_mm=cell_mm,
            pitch=pitch,
            band_top=upper_band_top,
            slot_bottom=lower_band_top,
        ),
        lower=_slot_layout(
            lower_rows,
            lower_columns,
            page_spec,
            cell_mm=cell_mm,
            pitch=pitch,
            band_top=lower_band_top,
            slot_bottom=page_bottom,
        ),
        cell_mm=cell_mm,
    )


def _pair_member(member: object, name: str) -> tuple[ClueSet, ClueSet]:
    """One puzzle of a pair, checked the way :func:`compute_layout` checks its clues."""
    if not isinstance(member, tuple | list) or len(member) != 2:
        raise ValueError(f"{name} must be a (row_clues, column_clues) pair, not {member!r}")
    row_clues, column_clues = member
    rows, columns = len(row_clues), len(column_clues)
    if bool(rows) != bool(columns):
        raise ValueError(
            f"{name}: clue sets disagree about the grid: {rows} row clue(s) but "
            f"{columns} column clue(s); a grid has either both or neither"
        )
    return row_clues, column_clues


def _slot_layout(
    row_clues: ClueSet,
    column_clues: ClueSet,
    page_spec: PageSpec,
    *,
    cell_mm: float,
    pitch: Fraction,
    band_top: Fraction,
    slot_bottom: Fraction,
) -> Layout:
    """One slot of a two-up page: a placed-page :class:`Layout` at a given cell.

    :func:`compute_layout`'s placed page with the cell and the band's row
    handed in instead of fitted: centred across the usable width, the drawing's
    top edge one band below ``band_top``, every boundary rounded once
    (:func:`_boundaries`). ``band_top`` and ``slot_bottom`` are exact pixels,
    and become the slot's :attr:`PagePlacement.usable_top` and
    :attr:`PagePlacement.usable_bottom` (see :class:`PairLayout`).
    """
    rows, columns = len(row_clues), len(column_clues)
    row_gutter_cells = _gutter_depth(row_clues)
    column_gutter_cells = _gutter_depth(column_clues)
    drawing_columns = row_gutter_cells + columns
    drawing_rows = column_gutter_cells + rows

    usable_left_px = _exact_px(page_spec.left_margin_mm)
    usable_width_px = (
        _exact_px(page_spec.width_mm)
        - _exact_px(page_spec.gutter_mm)
        - _exact_px(page_spec.outside_mm)
    )
    spare = usable_width_px - drawing_columns * pitch
    left = usable_left_px + max(spare, Fraction(0)) / 2
    top = band_top + _exact_px(page_spec.band_mm)

    xs = _boundaries(left, pitch, drawing_columns)
    ys = _boundaries(top, pitch, drawing_rows)
    grid_xs = xs[row_gutter_cells:]
    grid_ys = ys[column_gutter_cells:]
    grid_right, grid_bottom = grid_xs[-1], grid_ys[-1]
    thin, thick = _rule_widths(pitch, page_spec)
    return Layout(
        rows=rows,
        columns=columns,
        orientation="portrait",
        cell=math.floor(pitch),
        margin=_round_px(_exact_px(page_spec.top_mm)),
        row_gutter_cells=row_gutter_cells,
        column_gutter_cells=column_gutter_cells,
        width=_round_px(_exact_px(page_spec.width_mm)),
        height=_round_px(_exact_px(page_spec.height_mm)),
        grid_left=grid_xs[0],
        grid_top=grid_ys[0],
        grid_right=grid_right,
        grid_bottom=grid_bottom,
        thin_rule=thin,
        thick_rule=thick,
        clue_font_size=max(1, round(pitch * _CLUE_FONT_RATIO)),
        vertical_lines=_axis_lines(grid_xs, start=ys[0], end=grid_bottom, thin=thin, thick=thick),
        horizontal_lines=_axis_lines(grid_ys, start=xs[0], end=grid_right, thin=thin, thick=thick),
        row_clues=_place_row_clues(row_clues, depth=row_gutter_cells, xs=xs, ys=grid_ys),
        column_clues=_place_column_clues(
            column_clues, depth=column_gutter_cells, xs=grid_xs, ys=ys
        ),
        page=PagePlacement(
            parity=page_spec.parity,
            cell_mm=cell_mm,
            usable_left=_round_px(usable_left_px),
            usable_top=_round_px(band_top),
            usable_right=_round_px(usable_left_px + usable_width_px),
            usable_bottom=_round_px(slot_bottom),
            drawing_left=xs[0],
            drawing_top=ys[0],
            drawing_right=grid_right,
            drawing_bottom=grid_bottom,
        ),
    )


# ---------------------------------------------------------------------------
# Answer tiles (FR-042, owner decision BK-8, ADR-0036/R2, CARD-133)
# ---------------------------------------------------------------------------
#
# FR-042 replaced one full answer page per puzzle with a packed answer key: a
# book page carrying six (2 x 3) or four (2 x 2) answers, each drawn as its
# filled grid alone. The tiling is geometry, so by ADR-0036/R2 it lives here
# and not in the admin panel. What this module does *not* decide is which
# answers land on which page, which page carries a level heading, or what a
# caption says — that walk is the book's (COMP-009, CARD-134). This call lays
# out the answers it is handed, in the order it is handed them.
#
# An answer page carries **no title band**: its usable height is the trim minus
# the top and bottom margins only, and the spec's ``band_mm`` — which is the
# puzzle page's band — is deliberately not subtracted. That is the one place an
# answer page reads a book PageSpec differently from every other call here, so
# it is stated rather than left to be inferred from the arithmetic below.

#: The blank strip between two tiles, and between the heading line and the
#: first tile row, in millimetres (FR-042). Both axes: it is the same gap
#: across as down, so the page reads as a grid of tiles rather than as two
#: columns that happen to be near each other.
ANSWER_TILE_GAP_MM = 2.0

#: The strip each tile reserves at its top for its caption (FR-042), in
#: millimetres. The caption sits *above* its grid, the way a book puzzle page's
#: band sits above its drawing (FR-032), so a reader scanning the key meets the
#: puzzle number before the picture it belongs to.
ANSWER_CAPTION_MM = 6.0

#: The level heading's own line at the top of the page's usable area, in
#: millimetres (FR-042 amended 2026-09-22 (d)). A page that carries one spends
#: ``ANSWER_HEADING_MM + ANSWER_TILE_GAP_MM`` — the line plus the same gap that
#: separates two tile rows — before the first row of tiles begins.
ANSWER_HEADING_MM = 6.0

#: The cap on an answer's cell, in millimetres (FR-042 amended 2026-09-22 (d),
#: BK-8). An answer is read, not written on, so it does not want the 7.5 mm a
#: puzzle's cell wants: a 10x10 would otherwise take 7.94 mm of a six-up tile
#: and a 15x15 5.30 mm, and both print better at 5.0 mm with white around them.
#: Unlike a puzzle's cell this cap has no matching floor — the floor is the
#: caller's capacity rule (INV-011: a six-up page holds nothing above 20 cells
#: on its longest side), and on the Book 1 profile that rule is exactly what
#: keeps every answer at or above EC-031's 3.19 mm.
ANSWER_MAX_CELL_MM = 5.0

#: The type size a caption and a level heading are set in, in millimetres —
#: physical, like :data:`HEADER_FONT_MM`, not a fraction of the cell. One size
#: for both because both sit on a 6 mm line: 3.5 mm is roughly 10 pt, which
#: leaves a clear quarter-line of white above and below, and is the "small"
#: FR-042 asks the heading to be set in.
ANSWER_TEXT_FONT_MM = 3.5

#: The two page capacities FR-042 defines: six answers as 2 columns x 3 rows,
#: or four as 2 x 2. Always two columns; the capacity chooses the row count.
ANSWER_TILE_CAPACITIES = (4, 6)

#: An answer page is always two tiles across. Named because the tile width
#: below divides by it, and "2" alone in that expression could as easily be the
#: 2 mm gap.
_ANSWER_TILE_COLUMNS = 2


@dataclass(frozen=True, slots=True)
class AnswerTile:
    """One answer's place on a packed answer page (FR-042), in device pixels.

    The tile is the rectangle the answer owns; inside it sit the caption line
    (the top :data:`ANSWER_CAPTION_MM`) and the grid, drawn at the largest
    square cell that fits the rest of the tile and never above
    :data:`ANSWER_MAX_CELL_MM`. The grid is centred across the tile and hangs
    from the caption line, so whatever height the cap leaves spare falls at the
    tile's bottom rather than between the caption and the picture it labels.

    There are no clue gutters and no clue entries: an answer is the solved
    picture, and FR-042's answer key prints nothing else (AC-267). That is why
    this is not a :class:`Layout` — a ``Layout`` is a drawing *with* gutters,
    and a tile with two empty ones would be a lie about what is on the page.

    Attributes:
        index: The tile's position in the page's fill order, ``0`` first,
            left to right then top to bottom.
        rows: The answer's height in cells.
        columns: Its width in cells.
        cell_mm: The cell, exactly, in millimetres:
            ``min(ANSWER_MAX_CELL_MM, tile width / columns, (tile height −
            ANSWER_CAPTION_MM) / rows)``. The grid prints it as the pitch
            between rules, each rule rounded to the nearest device pixel.
        tile_left: The tile's left edge.
        tile_top: Its top edge, which is also the caption line's top.
        tile_right: Its right edge.
        tile_bottom: Its bottom edge.
        caption_top: The caption line's top edge (``tile_top``).
        caption_bottom: Its bottom edge, i.e. where the grid may begin.
        caption_font_size: The size to set the caption in, never taller than
            the line itself.
        grid_left: The grid's left edge.
        grid_top: Its top edge, always ``caption_bottom``.
        grid_right: Its right edge.
        grid_bottom: Its bottom edge.
        thin_rule: Stroke width of an ordinary rule (ADR-0037/R2 applies: a
            book spec's ``min_thin_rule_mm`` holds it up).
        thick_rule: Stroke width of an every-5th or border rule, twice the thin
            one.
        vertical_lines: Column boundaries, left to right, ``columns + 1`` of
            them, each spanning the grid's height. Named as
            :class:`Layout`'s are, so a renderer strokes a tile with the same
            code that strokes a page.
        horizontal_lines: Row boundaries, top to bottom, ``rows + 1``.
    """

    index: int
    rows: int
    columns: int
    cell_mm: float
    tile_left: int
    tile_top: int
    tile_right: int
    tile_bottom: int
    caption_top: int
    caption_bottom: int
    caption_font_size: int
    grid_left: int
    grid_top: int
    grid_right: int
    grid_bottom: int
    thin_rule: int
    thick_rule: int
    vertical_lines: tuple[GridLine, ...]
    horizontal_lines: tuple[GridLine, ...]

    @property
    def column_boundaries(self) -> tuple[int, ...]:
        """The ``columns + 1`` vertical cell boundaries, left to right.

        Cell ``(row, column)`` of the answer is the rectangle between
        ``column_boundaries[column]`` and ``[column + 1]`` across, and the
        matching pair of :attr:`row_boundaries` down. Read off the rules rather
        than stored again, so a filled cell and the rule that frames it can
        never disagree.
        """
        return tuple(line.position for line in self.vertical_lines)

    @property
    def row_boundaries(self) -> tuple[int, ...]:
        """The ``rows + 1`` horizontal cell boundaries, top to bottom."""
        return tuple(line.position for line in self.horizontal_lines)

    @property
    def caption_center_x(self) -> int:
        """The horizontal centre of the caption line: the tile's own centre."""
        return (self.tile_left + self.tile_right) // 2

    @property
    def caption_center_y(self) -> int:
        """The vertical centre of the caption line.

        A renderer sets the caption centred on
        ``(caption_center_x, caption_center_y)`` — the same ``anchor="mm"``
        rule the clue numbers and the title use.
        """
        return (self.caption_top + self.caption_bottom) // 2

    @property
    def fits(self) -> bool:
        """Whether the grid and its caption line lie inside the tile (EC-031).

        Always ``True`` for a tile this module built — the cell is fitted to
        the tile and capped, never floored, so there is no case where the grid
        can outgrow its tile. It is asserted rather than assumed because
        :class:`AnswerPageLayout` refuses a page whose tiles do not satisfy it,
        which is what makes EC-031 a property of the type rather than of the
        tests.
        """
        return (
            self.tile_left <= self.grid_left
            and self.grid_right <= self.tile_right
            and self.caption_bottom <= self.grid_top
            and self.grid_bottom <= self.tile_bottom
        )


@dataclass(frozen=True, slots=True)
class AnswerPageLayout:
    """A packed answer page: up to ``capacity`` answer tiles on a book page (FR-042).

    A value object, valid by construction: :meth:`__post_init__` refuses any
    page whose tiles overlap, leave the usable area, or hold a grid outside
    their own tile, so a caller holding one never re-checks EC-031.

    The page is the book's trim with mirrored margins (ADR-0036) and **no
    title band**: the usable area is the trim minus the four margins, and the
    tiles (plus the heading line, when there is one) share all of it.

    Attributes:
        parity: The page's side of the spread. It moves the usable area
            sideways, never its size, exactly as on a puzzle page.
        capacity: 6 (2 x 3) or 4 (2 x 2) — the tiling the page was measured
            for, not how many answers it was given. A half-filled last page of
            a level keeps its capacity's tile size.
        tile_rows: ``capacity // 2``, the number of tile rows.
        tile_columns: Always :data:`_ANSWER_TILE_COLUMNS`, i.e. 2.
        width: The trim's width in device pixels.
        height: The trim's height.
        usable_left: The usable area's left edge (the left margin).
        usable_top: Its top edge. The heading line, if any, starts here;
            otherwise the first tile row does.
        usable_right: Its right edge.
        usable_bottom: Its bottom edge.
        heading: The level heading's line as a :class:`HeaderBand` — the same
            measurement a title band is, because it is the same thing: a strip
            of reserved height with a centred string on it. ``None`` on a page
            that carries no heading, and then the tiles start at
            :attr:`usable_top`.
        tiles: One :class:`AnswerTile` per answer given, in fill order —
            left to right, then top to bottom. At most ``capacity`` of them,
            and fewer on a page the caller did not fill.
        dpi: The resolution every coordinate above is expressed at.

    Raises:
        ValueError: the capacity is not one FR-042 defines, the tile rows do
            not match it, there are more tiles than the capacity allows, a
            tile's grid or caption leaves its tile, a tile's cell exceeds
            :data:`ANSWER_MAX_CELL_MM`, two tiles overlap, or a tile or the
            heading line leaves the usable area.
    """

    parity: PageParity
    capacity: int
    tile_rows: int
    tile_columns: int
    width: int
    height: int
    usable_left: int
    usable_top: int
    usable_right: int
    usable_bottom: int
    heading: HeaderBand | None
    tiles: tuple[AnswerTile, ...]
    dpi: int = DPI

    def __post_init__(self) -> None:
        if self.capacity not in ANSWER_TILE_CAPACITIES:
            raise ValueError(
                f"an answer page holds {' or '.join(map(str, ANSWER_TILE_CAPACITIES))} "
                f"answers, not {self.capacity}"
            )
        if self.tile_columns * self.tile_rows != self.capacity:
            raise ValueError(
                f"an answer page of {self.capacity} is {self.tile_columns} x "
                f"{self.tile_rows} tiles, which is {self.tile_columns * self.tile_rows}"
            )
        if len(self.tiles) > self.capacity:
            raise ValueError(
                f"{len(self.tiles)} answers on a page that holds {self.capacity}"
            )
        first_tile_top = self.usable_top
        if self.heading is not None:
            heading_top = self.heading.center_y - self.heading.height // 2
            if heading_top < self.usable_top:
                raise ValueError("the heading line must lie inside the usable area")
            first_tile_top = self.usable_top + self.heading.height
        for tile in self.tiles:
            if not tile.fits:
                raise ValueError(
                    f"answer {tile.index}'s grid and caption must lie inside its own tile"
                )
            if tile.cell_mm > ANSWER_MAX_CELL_MM:
                raise ValueError(
                    f"answer {tile.index}'s cell is {tile.cell_mm} mm, above the "
                    f"{ANSWER_MAX_CELL_MM} mm answer cap"
                )
            if not (
                self.usable_left <= tile.tile_left
                and tile.tile_right <= self.usable_right
                and first_tile_top <= tile.tile_top
                and tile.tile_bottom <= self.usable_bottom
            ):
                raise ValueError(f"answer {tile.index}'s tile must lie inside the usable area")
        for position, earlier in enumerate(self.tiles):
            for later in self.tiles[position + 1 :]:
                if _tiles_overlap(earlier, later):
                    raise ValueError(
                        f"answers {earlier.index} and {later.index} sit on overlapping tiles"
                    )


def _tiles_overlap(one: AnswerTile, other: AnswerTile) -> bool:
    """Do two tiles share any area? Touching edges do not count as overlapping."""
    return (
        one.tile_left < other.tile_right
        and other.tile_left < one.tile_right
        and one.tile_top < other.tile_bottom
        and other.tile_top < one.tile_bottom
    )


def compute_answer_page_layout(
    extents: Sequence[tuple[int, int]],
    capacity: int,
    page_spec: PageSpec,
    heading: str | None = None,
) -> AnswerPageLayout:
    """Tile one page of the book's answer key (FR-042).

    The answer-key half of ADR-0036/R2: the page is divided into ``capacity``
    equal tiles, two across, and each answer is drawn inside its own tile at
    the largest square cell that tile can hold, capped at
    :data:`ANSWER_MAX_CELL_MM`. Every tile on a page is the same size whatever
    the answers on it are, so the key reads as a regular grid and a 10x10 next
    to a 20x20 does not pull the page out of true.

    The geometry, in millimetres, on the usable area (trim minus the four
    margins — an answer page carries **no title band**)::

        tile width  = (usable width − ANSWER_TILE_GAP_MM) / 2
        tile height = (usable height − heading − (rows − 1) × ANSWER_TILE_GAP_MM) / rows
        cell        = min(ANSWER_MAX_CELL_MM,
                          tile width / columns,
                          (tile height − ANSWER_CAPTION_MM) / rows)

    where ``rows`` is ``capacity // 2`` and ``heading`` is
    ``ANSWER_HEADING_MM + ANSWER_TILE_GAP_MM`` on a page that carries one and
    zero otherwise. On the Book 1 profile (193.675 x 260.35 mm usable) that is
    a 95.84 x 85.45 mm six-up tile, 95.84 x 129.18 mm four-up, and a six-up
    tile of 95.84 x 82.78 mm under a heading; a 20x20 answer then prints at
    3.97 mm, 3.87 mm under a heading, and a 30x30 four-up at 3.19 mm
    (AC-262, AC-265, AC-294, AC-295).

    **No cell floor, and why that is safe.** Unlike a puzzle's cell this one is
    capped but never held up: a floor would push a grid past the edge of its
    own tile, which is the one thing EC-031 forbids. What keeps an answer
    readable is the caller's capacity rule (INV-011 — a six-up page holds
    nothing above 20 cells on its longest side, a four-up page up to 30), and
    on the Book 1 profile that rule is exactly what puts every answer at or
    above EC-031's 3.19 mm: the same profile would print a 25x25 six-up at
    3.18 mm, which is why the capacity rule is a rule and not a preference.

    Args:
        extents: Up to ``capacity`` answers as ``(width, height)`` pairs in
            cells — columns then rows, the boundary form ADR-0022 fixes — in
            the order they fill the page, left to right then top to bottom.
        capacity: 6 (2 x 3) or 4 (2 x 2), one of
            :data:`ANSWER_TILE_CAPACITIES`. Which one a page gets is INV-011's
            rule and the caller's decision (CARD-134).
        page_spec: The book page: a placed page (a parity, hence portrait
            only) with a flat cell cap. Its ``band_mm`` is ignored — an answer
            page has no title band.
        heading: The level heading's text, or ``None`` for a page that carries
            none. Only its presence is read here; the string itself is the
            renderer's, and which page carries one is the caller's decision
            (CARD-128/CARD-134). It is taken as the text rather than as a flag
            so that a caller passes the one value to this call and to
            ``png.render_answer_page`` and the two cannot fall out of step.

    Returns:
        The :class:`AnswerPageLayout` the renderer draws from.

    Raises:
        TypeError: ``page_spec`` is not a :class:`PageSpec`.
        ValueError: ``page_spec`` is not a placed page with a flat cap (so the
            default A4 spec has no answer tiles), ``capacity`` is not one
            FR-042 defines, ``extents`` is empty or holds more answers than the
            capacity, an extent is not a pair of positive whole numbers, or the
            usable area cannot hold that many tiles above their caption lines.
    """
    if not isinstance(page_spec, PageSpec):
        raise TypeError(f"page_spec must be a PageSpec, not {type(page_spec).__name__}")
    if page_spec.parity is None or page_spec.cell_cap is CellCapPolicy.COMFORT_CURVE:
        raise ValueError(
            "an answer page is tiled only on a placed, portrait-only page with a flat "
            "cell cap (a PageSpec with a parity and a cap in mm); this spec "
            f"(parity {page_spec.parity}, cap {page_spec.cell_cap}) has no answer tiles"
        )
    if capacity not in ANSWER_TILE_CAPACITIES:
        raise ValueError(
            f"an answer page holds {' or '.join(map(str, ANSWER_TILE_CAPACITIES))} "
            f"answers, not {capacity!r}"
        )
    measured = tuple(_answer_extent(extent, index) for index, extent in enumerate(extents))
    if not measured:
        raise ValueError("an answer page holds at least one answer")
    if len(measured) > capacity:
        raise ValueError(f"{len(measured)} answers on a page that holds {capacity}")

    tile_rows = capacity // _ANSWER_TILE_COLUMNS
    gap_mm = _exact_mm(ANSWER_TILE_GAP_MM)
    caption_mm = _exact_mm(ANSWER_CAPTION_MM)
    heading_mm = (
        _exact_mm(ANSWER_HEADING_MM) + gap_mm if heading is not None else Fraction(0)
    )

    usable_width_mm = (
        _exact_mm(page_spec.width_mm)
        - _exact_mm(page_spec.gutter_mm)
        - _exact_mm(page_spec.outside_mm)
    )
    # The spec's band is the *puzzle* page's title band (FR-032). An answer
    # page has none, so it is not subtracted here — the tiles have the whole
    # usable height, minus the heading line when the page carries one.
    usable_height_mm = (
        _exact_mm(page_spec.height_mm)
        - _exact_mm(page_spec.top_mm)
        - _exact_mm(page_spec.bottom_mm)
    )
    tile_width_mm = (usable_width_mm - gap_mm) / _ANSWER_TILE_COLUMNS
    tile_height_mm = (
        usable_height_mm - heading_mm - (tile_rows - 1) * gap_mm
    ) / tile_rows
    if tile_width_mm <= 0 or tile_height_mm - caption_mm <= 0:
        raise ValueError(
            f"a {page_spec.width_mm:g} x {page_spec.height_mm:g} mm page cannot hold "
            f"{capacity} answer tiles above their {ANSWER_CAPTION_MM:g} mm caption lines"
        )

    usable_left_px = _exact_px(page_spec.left_margin_mm)
    usable_top_px = _exact_px(page_spec.top_mm)
    usable_width_px = _exact_px(usable_width_mm)
    usable_height_px = _exact_px(usable_height_mm)
    tile_width_px = _exact_px(tile_width_mm)
    tile_height_px = _exact_px(tile_height_mm)
    gap_px = _exact_px(gap_mm)
    caption_px = _exact_px(caption_mm)
    first_row_top_px = usable_top_px + _exact_px(heading_mm)

    band: HeaderBand | None = None
    if heading is not None:
        heading_px = _exact_px(ANSWER_HEADING_MM)
        heading_height = _round_px(heading_px)
        band = HeaderBand(
            height=heading_height,
            center_x=_round_px(usable_left_px + usable_width_px / 2),
            center_y=_round_px(usable_top_px) + heading_height // 2,
            font_size=max(1, min(_mm_to_px(ANSWER_TEXT_FONT_MM), heading_height)),
        )

    tiles = tuple(
        _answer_tile(
            index,
            columns,
            rows,
            page_spec,
            tile_left_px=usable_left_px
            + (index % _ANSWER_TILE_COLUMNS) * (tile_width_px + gap_px),
            tile_top_px=first_row_top_px
            + (index // _ANSWER_TILE_COLUMNS) * (tile_height_px + gap_px),
            tile_width_px=tile_width_px,
            tile_height_px=tile_height_px,
            tile_width_mm=tile_width_mm,
            tile_height_mm=tile_height_mm,
            caption_px=caption_px,
            caption_mm=caption_mm,
        )
        for index, (columns, rows) in enumerate(measured)
    )
    return AnswerPageLayout(
        parity=page_spec.parity,
        capacity=capacity,
        tile_rows=tile_rows,
        tile_columns=_ANSWER_TILE_COLUMNS,
        width=_round_px(_exact_px(page_spec.width_mm)),
        height=_round_px(_exact_px(page_spec.height_mm)),
        usable_left=_round_px(usable_left_px),
        usable_top=_round_px(usable_top_px),
        usable_right=_round_px(usable_left_px + usable_width_px),
        usable_bottom=_round_px(usable_top_px + usable_height_px),
        heading=band,
        tiles=tiles,
    )


def _answer_extent(extent: object, index: int) -> tuple[int, int]:
    """One answer's ``(width, height)``, checked before anything is measured.

    Whole positive cell counts, as ADR-0022's boundary pair. The supported
    range itself (:data:`~nonogram.limits.MIN_SIZE`..``MAX_SIZE``) is not
    re-checked here: a grid that reached the answer key was validated where it
    was created, and this module measures whatever extent it is handed.
    """
    if not isinstance(extent, tuple | list) or len(extent) != 2:
        raise ValueError(f"answer {index} must be a (width, height) pair, not {extent!r}")
    columns, rows = extent
    if not all(isinstance(side, int) and not isinstance(side, bool) and side > 0
               for side in (columns, rows)):
        raise ValueError(
            f"answer {index}'s extent must be two positive whole numbers of cells, "
            f"not {columns!r} x {rows!r}"
        )
    return columns, rows


def _answer_tile(
    index: int,
    columns: int,
    rows: int,
    page_spec: PageSpec,
    *,
    tile_left_px: Fraction,
    tile_top_px: Fraction,
    tile_width_px: Fraction,
    tile_height_px: Fraction,
    tile_width_mm: Fraction,
    tile_height_mm: Fraction,
    caption_px: Fraction,
    caption_mm: Fraction,
) -> AnswerTile:
    """One answer in its tile: the cell, the caption line and the ruled grid.

    The cell is taken exactly, in millimetres, so ``cell_mm`` is the number the
    tile really prints rather than a pixel count read back as a length. The
    grid is centred across the tile and hangs from the caption line, and every
    boundary is rounded once (:func:`_boundaries`), so a fractional pitch never
    accumulates error down the grid. Strokes and the every-5th rules come from
    :func:`_rule_widths` and :func:`_axis_lines` — the page's own, so an answer
    is ruled exactly as a puzzle is (ADR-0037/R2).
    """
    cell_mm = min(
        _exact_mm(ANSWER_MAX_CELL_MM),
        tile_width_mm / columns,
        (tile_height_mm - caption_mm) / rows,
    )
    pitch = _exact_px(cell_mm)
    grid_left_px = tile_left_px + max(tile_width_px - columns * pitch, Fraction(0)) / 2
    grid_top_px = tile_top_px + caption_px

    xs = _boundaries(grid_left_px, pitch, columns)
    ys = _boundaries(grid_top_px, pitch, rows)
    thin, thick = _rule_widths(pitch, page_spec)
    return AnswerTile(
        index=index,
        rows=rows,
        columns=columns,
        cell_mm=float(cell_mm),
        tile_left=_round_px(tile_left_px),
        tile_top=_round_px(tile_top_px),
        tile_right=_round_px(tile_left_px + tile_width_px),
        tile_bottom=_round_px(tile_top_px + tile_height_px),
        caption_top=_round_px(tile_top_px),
        caption_bottom=_round_px(grid_top_px),
        caption_font_size=max(1, min(_mm_to_px(ANSWER_TEXT_FONT_MM), _round_px(caption_px))),
        grid_left=xs[0],
        grid_top=ys[0],
        grid_right=xs[-1],
        grid_bottom=ys[-1],
        thin_rule=thin,
        thick_rule=thick,
        vertical_lines=_axis_lines(xs, start=ys[0], end=ys[-1], thin=thin, thick=thick),
        horizontal_lines=_axis_lines(ys, start=xs[0], end=xs[-1], thin=thin, thick=thick),
    )
