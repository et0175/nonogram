"""PDF generation service for book scaffolding.

Exports a book as two files (FR-043, INV-013): the interior PDF — guide page,
puzzles, SOLUTIONS divider and answers, with no cover page — and the cover
file, a single front-cover page.

Every page is the book's own trim at 300 DPI (CARD-116, FR-030/FR-032)
--------------------------------------------------------------------
The generator used to hard-code a 2550 x 3300 px letter page and print each
puzzle through the A4 layout, so a book puzzle was sized for A4 and then laid
on a sheet it had never been measured against. It now builds **one page spec
per page** through :func:`~nonogram.admin.book_page_spec.book_page_spec` — the
one door onto the book's sheet (CARD-115) — and every page of the interior
(guide, puzzles, SOLUTIONS divider, answers) and the cover file's single page
is that trim: 2550 x 3300 px on the Book 1 profile, 1800 x 2700 px on a 6 x 9
in book.

``book_page_spec`` takes the page's **1-based position in the interior**, and
that position is where the page's parity comes from (FR-043): interior page 1
is the guide page and is right-hand (odd), so the gutter margin is on its
left; page 2 is left-hand, and so on for every page kind alike. Parity moves
the drawing sideways only — its top edge is top margin + band on every puzzle
page (FR-032) — which is COMP-007's arithmetic, not this module's.

**This module fits no cell and places no grid line** (ADR-0036/R2). Every
number it uses is read off :func:`~nonogram.export.layout.compute_layout`
called with the book's spec: the trim and the usable area through
:func:`page_frame`, the placed drawing through
:func:`~nonogram.export.pdf.render_pages`. The only thing positioned here is
text the layout knows nothing about — the guide page's lines and the divider's
word — and it is positioned against the usable area the layout reported.

What the band says (ADR-0037/R1, CARD-117)
------------------------------------------
A book puzzle page's 12 mm band (TERM-028) reads **"Puzzle N · Tier"** — the
puzzle's 1-based position in the print order and the solver's tier, nothing
else. The picture's title is not on it (FR-033): a titled puzzle page gives
the picture away before the solver has drawn it. The title appears once, on
that puzzle's **answer-key page**, beside the same "Puzzle N · Tier" line, so
the answer can be found by the number printed on the puzzle and recognised by
the name once it is found.

Both bands are the export's own header, set by COMP-007 inside the band the
`PageSpec` reserves; this module chooses only the *text*, by what it puts in
the two header fields of each page's :class:`~nonogram.export.ExportPayload`
(:func:`~nonogram.export.pdf.header_parts` is the non-empty members of
``(name, difficulty)``, em rule between them). So the two pages of one puzzle
are two different payloads and two ``render_pages`` calls — see
:meth:`BookPDFGenerator._banded`. Drawing lettering is the admin's to decide
(ADR-0036/R2 forbids fitting cells and placing rules, not wording), and it is
set in the packaged DejaVu Sans the export already uses (ADR-0006/DEC-027),
which covers the middle dot.

Two puzzles to a page (FR-040, INV-010, CARD-127)
--------------------------------------------------
:meth:`BookPDFGenerator.puzzle_pages` walks the book order from the first
puzzle and offers puzzle *i* and puzzle *i+1* to COMP-007's
:func:`~nonogram.export.layout.compute_pair_layout` **only when their tiers are
equal**. A :class:`~nonogram.export.layout.PairLayout` back means both print on
one page and the walk moves to *i+2*; ``None`` — a verdict, not an error: the
pair's largest shared cell is under 7.0 mm — means *i* prints alone and the
walk moves to *i+1*. An *exception* from that call is not a verdict and is not
read as one: it is re-raised naming the two puzzles offered, so that a member
too malformed to measure is named whether or not it happened to have a
same-tier neighbour. The last puzzle of an odd run prints alone. **The walk
never reorders**, never looks past the immediate successor for a better
partner, and never skips a puzzle to keep a later pair intact, so
concatenating the pages front to back yields the book order exactly (EC-027).

What the panel decides is *which neighbours to offer* and nothing else (G-1,
ADR-0036/R2): the shared cell, both slot positions, every ruled line and every
clue centre are read off the ``PairLayout``. What it composes is the page,
because COMP-007 exposes no call that draws a *given*
:class:`~nonogram.export.layout.Layout` — :func:`~nonogram.export.png.render_image`
and :func:`~nonogram.export.pdf.render_pages` each fit their own layout from a
payload and a spec, so neither can draw a two-up slot. :func:`_stroke_drawing`,
:func:`_write_clues` and :func:`_set_band` therefore stroke what the pair
already measured, natively here rather than through the renderers' private
helpers — the precedent ``solver/propagate.py``'s ``mask_runs`` sets, and the
only shape the import layering allows. They place nothing: every coordinate
they are given came from COMP-007.

Each slot carries **its own band**, "Puzzle N · Tier", measured by
:func:`~nonogram.export.layout.header_band` on that slot and set with the same
type, the same centring and the same measure-and-shrink fitting the export's
header uses (:func:`_set_band`, whose docstring records the one step of the
export's three it does not reproduce and why that step cannot be reached), so
a slot's band and a single page's band are the same ink. The upper
slot is the earlier puzzle and its drawing's top edge is the fixed row every
single puzzle page uses — top margin plus band (FR-032, EC-022).

Pairing is decided here, at PDF time, and nothing about it is stored
(Increment 15's rollback story). It shortens the interior, so **every later
page's parity flips** — which is why each page is still built on the spec of
its own position and never on a position assumed in advance. Both page counts,
before and after pairing, come back on :class:`Interior` and
:class:`BookExport`.
"""

import logging
from collections import Counter
from dataclasses import dataclass, replace
from functools import lru_cache
from importlib import resources
from typing import Any, Dict, Optional, List, Tuple
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

from nonogram.admin.book_page_spec import book_page_spec
from nonogram.difficulty import Tier, tier_of_record
from nonogram.export import ExportPayload
from nonogram.export.layout import (
    DPI,
    HeaderBand,
    Layout,
    PageSpec,
    PairLayout,
    compute_layout,
    compute_pair_layout,
    header_band,
)
from nonogram.export.pdf import FONT_PACKAGE, FONT_RESOURCE, render_pages
from nonogram.export.png import BACKGROUND, INK

#: The panel's own logger, like the rest of ``admin/``: a dropped puzzle is
#: the only trace the export leaves of a member that did not reach the file,
#: and a ``print`` of it lands nowhere in a served request.
logger = logging.getLogger(__name__)

#: What stands between a puzzle's number and its tier in the band: a middle dot
#: (U+00B7) with a space either side, exactly as ADR-0037 writes it
#: ("Puzzle 12 · Easy").
#:
#: It is part of one header piece, set as a glyph in the packaged DejaVu Sans,
#: which covers U+00B7 — unlike the em rule the export *strokes* between two
#: pieces (``pdf.HEADER_SEPARATOR``). The two marks are deliberately different:
#: the dot joins the number to its tier inside one line, the rule joins that
#: line to the picture's title on the answer page.
BAND_SEPARATOR = " · "


def band_identity(puzzle_number: int, stored_tier: object) -> str:
    """The band line of one book puzzle: ``"Puzzle 12 · Easy"`` (ADR-0037/R1).

    The whole of what a puzzle page's band says. ``N`` is the puzzle's 1-based
    position in the **print** order, which is the number its answer-key entry
    carries too, so the two can be matched by eye; ``Tier`` is the solver's
    own grade, never anything derived from the grid's size (FR-009).

    ``stored_tier`` is whatever the puzzle's row holds, in any of the spellings
    that reach it — the enum value a generated row stores (``"easy"``), the
    display label an older or hand-entered row carries (``"Easy"``), or
    ADR-0031/R3's retired ``"guess"``, which reads back as Hard without being
    rewritten. It is normalised through
    :func:`nonogram.difficulty.tier_of_record`, the one reader of stored tier
    text, rather than printed as it is stored: a band reading "Puzzle 12 ·
    easy" would be the same counting bug that function exists to prevent,
    wearing a typography bug's clothes.

    **A row with no tier of record prints "Puzzle 12" and stops.** ``None`` out
    of ``tier_of_record`` means the text on the row is not a tier at all — a
    missing column, a blank, a word from some retired vocabulary — and there
    is nothing true to print after the dot. The three honest options are to
    print the raw text (which would put an unvetted string from the database on
    a printed page and spell it however it happens to be spelled), to invent a
    label such as "Unrated" (a fourth tier on the page, which ADR-0031 has
    exactly three of), or to say only what is known. This says only what is
    known: the number still identifies the puzzle and still matches the answer
    key, and the missing grade is visible as an absence to whoever proofs the
    book rather than dressed up as one.

    Raises:
        ValueError: ``puzzle_number`` is not a print position (below 1).
    """
    if puzzle_number < 1:
        raise ValueError(f"puzzles are numbered from 1, got {puzzle_number}")
    tier = tier_of_record(stored_tier)
    if tier is None:
        return f"Puzzle {puzzle_number}"
    return f"Puzzle {puzzle_number}{BAND_SEPARATOR}{tier.label}"


def tier_breakdown(puzzles: List[Dict[str, Any]]) -> "Counter[Tier]":
    """Count a book's puzzles by tier, however their rows spell it.

    One implementation for both places a book's difficulty breakdown is built —
    the PDF guide page here and the finalize screen in ``app.py`` — because two
    copies of it is how the defect below survived in both at once.

    Every count goes through :func:`nonogram.difficulty.tier_of_record` rather
    than comparing against a display label. A row written by the generation
    pipeline stores the enum *value* (``"easy"``), so the previous
    ``== "Easy"`` matched none of them: every generated book reported a 0/0/0
    breakdown, which reads as an empty book rather than as a broken reader
    (CARD-076 review F-002). Rows whose tier is missing or unrecognised are
    counted in no tier at all, so the totals never exceed the puzzle count.

    Returns a :class:`collections.Counter`, so every member of :class:`Tier`
    can be indexed without a ``get`` and reads
    0 when the book has none.
    """
    return Counter(
        tier
        for tier in (
            tier_of_record(puzzle.get("difficulty_tier")) for puzzle in puzzles
        )
        if tier is not None
    )


# ---------------------------------------------------------------------------
# Drawing a page COMP-007 measured but draws no call for (FR-040, ADR-0036/R2)
# ---------------------------------------------------------------------------

#: How much of a slot's usable width a band's line may occupy, and how far the
#: type may shrink to fit it — COMP-007's own header numbers
#: (``pdf._HEADER_WIDTH_RATIO``, ``pdf._MIN_HEADER_FONT_RATIO``), restated here
#: because they are private to that module. They never bite on a band this
#: module writes: "Puzzle 120 · Medium" is about a tenth of a book page's
#: usable width at the 5 mm the band is set in. They are kept so that a band is
#: fitted by the same rule wherever it is drawn, rather than running off the
#: page in the one case nobody measured — and they are pinned equal to
#: COMP-007's pair by
#: ``test_a_two_up_band_is_fitted_by_the_exports_own_header_ratios``
#: (``tests/test_book_pdf_two_up.py``, where importing those private names is
#: legal), so a retuning on that side cannot leave this side silently behind.
_BAND_WIDTH_RATIO = 0.9
_MIN_BAND_FONT_RATIO = 1 / 3


@lru_cache(maxsize=1)
def _band_font_bytes() -> bytes:
    """The packaged DejaVu Sans, read once (ADR-0006/R1, ADR-0006/DEC-027).

    The same face, addressed the same way as :mod:`nonogram.export.pdf`
    addresses it for its own header — package *data*, named by that module's
    public :data:`~nonogram.export.pdf.FONT_PACKAGE` and
    :data:`~nonogram.export.pdf.FONT_RESOURCE` and read through
    :mod:`importlib.resources`, not a filesystem path and not a system font.
    A band reads "Puzzle 12 · Easy", and U+00B7 is not in Pillow's embedded
    ASCII default face — a band set in that would print a ``.notdef`` box
    between the number and the tier.
    """
    return resources.files(FONT_PACKAGE).joinpath(FONT_RESOURCE).read_bytes()


@lru_cache(maxsize=8)
def _band_font(size: int) -> ImageFont.FreeTypeFont:
    """The packaged face at ``size`` device pixels. Cached: a book asks for one
    or two sizes across every page it prints."""
    return ImageFont.truetype(BytesIO(_band_font_bytes()), size=size)


def _stroke_drawing(draw: ImageDraw.ImageDraw, slot: Layout) -> None:
    """Stroke every ruled line of ``slot``, thin ones first (FR-040).

    Every number here — each line's axis position, its two ends and its width —
    is COMP-007's, read off the :class:`~nonogram.export.layout.Layout` the
    pair-aware call placed. Nothing is measured, rounded or offset.

    Thin rules first and the every-5th and border rules last, so that where a
    heavy line crosses a thin one the heavy line survives the overlap and stays
    visually continuous — the same order, and the same reason, as the PNG
    renderer's. It is reimplemented rather than imported: ``png._draw_grid`` is
    private, and ``export/`` exposes no call that draws a layout it is handed.
    """
    oriented: List[Tuple[Any, bool]] = [
        *((line, True) for line in slot.vertical_lines),
        *((line, False) for line in slot.horizontal_lines),
    ]
    for line, vertical in sorted(oriented, key=lambda pair: pair[0].major):
        if vertical:
            ends = [(line.position, line.start), (line.position, line.end)]
        else:
            ends = [(line.start, line.position), (line.end, line.position)]
        draw.line(ends, fill=INK, width=line.width)


def _write_clues(draw: ImageDraw.ImageDraw, slot: Layout) -> None:
    """Write ``slot``'s clue numbers, each centred on the point COMP-007 placed it.

    ``anchor="mm"`` centres the glyph box on that point in both axes — the one
    placement rule that does not depend on a face's ascent or digit width — and
    the size is :attr:`Layout.clue_font_size`, which the layout derived from the
    shared cell. Pillow's embedded default face, at an explicit size, exactly as
    a single puzzle page's clues are set: they are ASCII decimal digits, so the
    coverage that forces the band onto the packaged face does not arise.
    """
    font = ImageFont.load_default(size=slot.clue_font_size)
    for entry in slot.clue_entries:
        draw.text(
            (entry.center_x, entry.center_y),
            str(entry.value),
            font=font,
            fill=INK,
            anchor="mm",
        )


def _set_band(draw: ImageDraw.ImageDraw, band: HeaderBand, text: str, room: int) -> None:
    """Set ``text`` centred in ``band``, shrunk if it would not fit ``room``.

    The band's strip, its centre and its type size are
    :func:`~nonogram.export.layout.header_band`'s answer for the slot; ``room``
    is the slot's usable width, the same measurement the export fits a header
    against. One piece, so there is no separator to stroke: a puzzle page's
    header is the identity line alone (:meth:`BookPDFGenerator._banded` clears
    the picture's name), and a two-up slot is a puzzle page.

    Drawn from the line's left edge with ``anchor="lm"`` at
    ``center_x - width / 2`` rather than with a centred anchor, because that is
    what :func:`~nonogram.export.pdf.render_pages` does for a one-piece header:
    the two must put the same ink in the same pixels, or the upper slot's band
    and the band of the same puzzle printed alone would differ.

    **Two of the export's three fitting steps, not three.** ``pdf._draw_header``
    measures, shrinks once to :data:`_MIN_BAND_FONT_RATIO` of the band's type
    size, and then — if the line is *still* too wide at that floor — elides its
    first piece. The first two steps are above; the third is deliberately not
    reproduced, and cannot be reached from here: the export elides the first of
    several pieces because only a picture's name is long enough to need it
    (:meth:`BookPDFGenerator._banded`), while a band is the one piece
    :func:`band_identity` composes — "Puzzle 120 · Medium", about a tenth of a
    book page's usable width at the 5 mm the band is set in, with the number
    bounded by the book's membership and the tier by ADR-0031's three labels.
    There is nothing here that could grow into the case the third step exists
    for, and eliding the only piece would cut the number the answer key is
    looked up by. Were a band ever to carry a second, unbounded piece, that
    step would have to come with it.
    """
    if band.height <= 0 or not text:
        return
    size = band.font_size
    font = _band_font(size)
    width = font.getlength(text)
    usable = room * _BAND_WIDTH_RATIO
    if width > usable:
        size = max(round(band.font_size * _MIN_BAND_FONT_RATIO), int(size * usable / width))
        font = _band_font(size)
        width = font.getlength(text)
    draw.text(
        (band.center_x - width / 2, band.center_y),
        text,
        font=font,
        fill=INK,
        anchor="lm",
    )


@dataclass(frozen=True)
class PuzzlePagePlan:
    """One page of the interior's puzzle section: one puzzle, or two (FR-040).

    What :meth:`BookPDFGenerator.puzzle_pages`'s walk decided, before any page
    is drawn: where the page sits, which puzzles it holds, and — for a two-up
    page — the geometry COMP-007 measured for the pair.

    Attributes:
        page_number: The page's 1-based position in the interior, which is
            where its parity comes from (FR-043).
        numbers: The 1-based print numbers of the puzzles on it, in print
            order: one number, or two with the upper slot's first.
        pair: ``None`` for a single-puzzle page. Otherwise the
            :class:`~nonogram.export.layout.PairLayout` whose ``upper`` slot is
            ``numbers[0]`` and whose ``lower`` slot is ``numbers[1]``.
    """

    page_number: int
    numbers: Tuple[int, ...]
    pair: Optional[PairLayout] = None

    @property
    def is_two_up(self) -> bool:
        """Whether this page holds two puzzles (TERM-030)."""
        return self.pair is not None


@dataclass(frozen=True)
class Interior:
    """The interior's pages, and what two-up pairing saved (FR-040).

    Attributes:
        pages: Every interior page in print order; ``pages[n - 1]`` is interior
            page ``n``. No cover page (FR-043, INV-013).
        unpaired_page_count: What the same interior would have taken with every
            puzzle on a page of its own — the "before pairing" count. Both are
            **interior** counts: the cover is a separate file and is never
            counted.
    """

    pages: List[Image.Image]
    unpaired_page_count: int

    @property
    def page_count(self) -> int:
        """The interior's real page count, after pairing."""
        return len(self.pages)

    @property
    def pages_saved(self) -> int:
        """How many interior pages the two-up pages saved. Never negative."""
        return self.unpaired_page_count - self.page_count


@dataclass(frozen=True)
class BookExport:
    """A book's export: the interior PDF and, beside it, the cover file.

    ``interior_page_count`` is the book's page count (FR-030 as amended by
    FR-043) — the interior's pages only; the cover file is never counted.
    ``unpaired_interior_page_count`` is the same count before two-up pairing
    (FR-040), so the two together are the saving the owner's "big books"
    research asks for. Both are interior counts.
    """

    interior: BytesIO
    cover: BytesIO
    interior_page_count: int
    unpaired_interior_page_count: int

    @property
    def pages_saved(self) -> int:
        """Interior pages saved by printing two puzzles to a page (FR-040)."""
        return self.unpaired_interior_page_count - self.interior_page_count


@dataclass(frozen=True)
class PageFrame:
    """One book page's trim and usable area in device pixels (ADR-0036/R2).

    Not measured here: it is :func:`~nonogram.export.layout.compute_layout`'s
    own answer for the page's :class:`~nonogram.export.layout.PageSpec`, read
    off a :class:`~nonogram.export.layout.PagePlacement`. That is what lets
    the pages this module draws itself — the guide, the divider, the cover —
    sit on the same trim, inside the same mirrored margins, as the puzzle
    pages COMP-007 places, without the admin panel converting a millimetre to
    a pixel anywhere.

    Attributes:
        width: The trim's width; ``height`` its height.
        left: The usable area's left edge — the gutter margin on an odd
            (right-hand) page, the outside margin on an even one.
        top: The usable area's top edge (the title band starts here).
        right: Its right edge; ``bottom`` its bottom edge.
    """

    width: int
    height: int
    left: int
    top: int
    right: int
    bottom: int


#: The smallest clue set that still describes a puzzle: one 1-cell row and one
#: 1-cell column. :func:`page_frame` lays it out purely to read the sheet's own
#: numbers back, so the probe's extent never reaches any output.
_PROBE_CLUES: Tuple[Tuple[int, ...], ...] = ((1,),)


def page_frame(spec: PageSpec) -> PageFrame:
    """The trim and usable area of a page laid out on ``spec``.

    Raises:
        ValueError: ``spec`` carries no parity, so it lays out a drawing-sized
            image rather than a book page — build it with ``book_page_spec``.
    """
    layout = compute_layout(_PROBE_CLUES, _PROBE_CLUES, spec)
    placement = layout.page
    if placement is None:
        raise ValueError(
            "a book page needs a PageSpec with a parity: build it with book_page_spec"
        )
    return PageFrame(
        width=layout.width,
        height=layout.height,
        left=placement.usable_left,
        top=placement.usable_top,
        right=placement.usable_right,
        bottom=placement.usable_bottom,
    )


def page_is_right_hand(page_number: int) -> bool:
    """Whether interior page ``page_number`` (1-based) is a right-hand page.

    Parity counts from the interior's page 1, the guide page, which is
    right-hand: odd pages are right-hand, even pages left-hand (FR-043).
    """
    if page_number < 1:
        raise ValueError(f"interior pages are numbered from 1, got {page_number}")
    return page_number % 2 == 1


def interior_page_count(puzzle_count: int, puzzle_pages: Optional[int] = None) -> int:
    """The interior's page count for ``puzzle_count`` rendered puzzles.

    The page plan :meth:`BookPDFGenerator.interior` builds — one guide page,
    the puzzle pages, then (only when there are puzzles) the SOLUTIONS divider
    and one answer page per puzzle; never the cover (FR-030 as amended by
    FR-043). ``interior`` checks its own output against this, so a change to
    the make-up of the pages that forgets this function fails loudly instead of
    shipping a book whose stated page count is not its page count.

    ``puzzle_pages`` is how many pages those puzzles actually take. It is
    ``puzzle_count`` — one page each — until two-up pairing shortens it
    (FR-040), and that is why it defaults to ``puzzle_count``: called with the
    count alone this is the **un-paired** plan, the number the Finalise screen
    has always shown and the "before pairing" half of the saving FR-040 asks
    the generator to report. CARD-129 owns making the Finalise count exact
    (EC-034); until then that screen deliberately shows the un-paired plan as
    an upper bound rather than a promise.

    ``puzzle_count`` counts puzzles that *render*: :meth:`interior` skips a
    puzzle it cannot build an export payload for, so a count taken from the
    book's members is an upper bound when one of them is broken. That skip is
    the only way the two can differ — a puzzle that builds a payload and then
    will not draw aborts the export with a :class:`RuntimeError` naming it,
    rather than quietly making the file one page shorter than this number.
    CARD-116 put every page on the book's trim and left this plan alone;
    CARD-127's two-up pairing changes it through ``puzzle_pages``, and the
    packed answer key (CARD-134) will change the answer half here too.
    """
    if puzzle_count < 0:
        raise ValueError(f"puzzle count cannot be negative, got {puzzle_count}")
    pages = puzzle_count if puzzle_pages is None else puzzle_pages
    if pages < 0:
        raise ValueError(f"puzzle page count cannot be negative, got {pages}")
    return 1 + pages + (puzzle_count + 1 if puzzle_count else 0)


def _named_puzzles(ids: Optional[List[Any]], numbers: Tuple[int, ...]) -> str:
    """The puzzles of one page, as an aborted export names them.

    One naming rule for every abort :meth:`BookPDFGenerator.interior` can raise
    — a pair that will not lay out, a page that will not draw — because the
    owner searches a 120-puzzle book by the id in the message and nothing else
    (:meth:`BookPDFGenerator.interior`'s ``Raises``).

    ``ids`` is the puzzle ids, parallel to the payloads, so ``numbers`` (1-based
    print numbers) index into it. Without them — :meth:`puzzle_pages` called on
    its own, as a test or a future caller may — the print numbers are named
    instead, which is still the only handle such a caller has.
    """
    if ids is None:
        return ", ".join(f"#{number}" for number in numbers)
    return ", ".join(repr(ids[number - 1]) for number in numbers)


def _pairable_tier(payload: ExportPayload) -> Optional[Tier]:
    """The tier a payload pairs on, or ``None`` when its row states none.

    :func:`~nonogram.difficulty.tier_of_record` is the one reader of stored
    tier text, so ``"easy"``, ``"Easy"`` and ADR-0031/R3's retired ``"guess"``
    are the tiers they mean rather than three different strings.

    A row whose tier cannot be read has no tier, and **never pairs** — not even
    with another unreadable one. INV-010 lets two puzzles share a page only
    when *their tiers are equal*, and two absences are not an equality: the
    band of such a puzzle already prints "Puzzle 12" and stops
    (:func:`band_identity`), and putting two ungraded puzzles on one page would
    state a sameness the book cannot show the reader.
    """
    return tier_of_record(payload.difficulty)


class BookPDFGenerator:
    """Generates a book's interior PDF (guide, puzzles, answers) and cover file.

    Args:
        book: The book being exported — anything carrying the ``books`` print
            columns (a :class:`~nonogram.admin.book_manager.Book` or a row).
            ``None`` is a book with no stored print specification, which is
            CON-018's Book 1 profile, exactly as an empty column is
            (:func:`~nonogram.admin.book_page_spec.book_page_spec`).

    Raises:
        ValueError: the book's stored print specification cannot be laid out
            (a trim outside KDP's bounds, a margin below the minimum, a
            non-numeric column) — the message names the column at fault.
    """

    def __init__(self, book: Any = None):
        self.book = book
        self.dpi = DPI  # 300, the resolution COMP-007 measures every page at
        # The trim, as the layout reports it for this book's sheet. Parity
        # never changes a page's size, so page 1's frame gives it for all.
        frame = page_frame(self.page_spec(1))
        self.page_width_px = frame.width
        self.page_height_px = frame.height

    def page_spec(self, page_number: int = 1) -> PageSpec:
        """The book's sheet for interior page ``page_number`` (1-based).

        The one door onto the book's geometry (CARD-115). Page 1 is the guide
        page and is right-hand; each page's parity is its position (FR-043).
        """
        return book_page_spec(self.book, page_number)

    def create_cover_page(self, book_title: str, cover_image: Optional[Image.Image] = None) -> Image.Image:
        """Create cover page image, one trim-size page.

        The cover file is never numbered (FR-043), so it has no parity of its
        own; its page is the trim, and the generated title cover is centred on
        it, which a mirrored margin would not move anyway.

        Args:
            book_title: Title for the book
            cover_image: Optional pre-built cover image

        Returns:
            Cover page as PIL Image
        """
        if cover_image:
            # Use provided cover, resized to standard page size
            return cover_image.resize((self.page_width_px, self.page_height_px), Image.Resampling.LANCZOS)

        # Create blank cover with title
        cover = Image.new("RGB", (self.page_width_px, self.page_height_px), "white")
        draw = ImageDraw.Draw(cover)

        # Try to load a nice font, fall back to default
        try:
            title_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 72)
        except OSError:
            # Fallback font
            title_font = ImageFont.load_default()

        # Draw title centered on page
        title_bbox = draw.textbbox((0, 0), book_title, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (self.page_width_px - title_width) // 2
        title_y = (self.page_height_px - (title_bbox[3] - title_bbox[1])) // 2

        draw.text((title_x, title_y), book_title, fill="black", font=title_font)

        return cover

    def create_guide_page(
        self,
        puzzle_count: int,
        easy_count: int,
        medium_count: int,
        hard_count: int,
        page_number: int = 1,
    ) -> Image.Image:
        """Create guide page image with difficulty summary.

        Args:
            puzzle_count: Total number of puzzles
            easy_count: Number of easy puzzles
            medium_count: Number of medium puzzles
            hard_count: Number of hard puzzles
            page_number: Its 1-based position in the interior. The guide page
                *is* interior page 1 (FR-043), so the default is the only
                value the export uses; it is a parameter because the page's
                margins are mirrored by that position like any other page's.

        Three counts, one per tier, since CARD-098 retired ADR-0025's fourth.

        Returns:
            Guide page as PIL Image
        """
        frame = page_frame(self.page_spec(page_number))
        guide = Image.new("RGB", (frame.width, frame.height), "white")
        draw = ImageDraw.Draw(guide)

        # Try to load fonts
        try:
            title_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 48)
            text_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 28)
        except OSError:
            title_font = ImageFont.load_default()
            text_font = ImageFont.load_default()

        # Inside the usable area the layout reported, so the guide page keeps
        # the book's mirrored margins like every other interior page.
        title = "How to Use This Book"
        draw.text((frame.left, frame.top), title, fill="black", font=title_font)

        # Draw guide text
        guide_text = [
            f"This book contains {puzzle_count} puzzles.",
            "",
            "Difficulty Levels:",
            f"  Easy:   {easy_count} puzzles",
            f"  Medium: {medium_count} puzzles",
            f"  Hard:   {hard_count} puzzles",
            "",
            "Instructions:",
            "  1. Fill in the grid based on the clues",
            "  2. Check your work against the answer key",
            "  3. Have fun!",
        ]

        y = frame.top + 150
        for line in guide_text:
            draw.text((frame.left, y), line, fill="black", font=text_font)
            y += 50

        return guide

    def create_divider_page(self, page_number: int, text: str = "SOLUTIONS") -> Image.Image:
        """The divider that opens the answer section, one trim-size page.

        Its word is centred on the trim, so ``page_number`` decides its size
        and nothing else — but it is taken, not assumed, because the divider
        is an interior page like any other and its position is where a page's
        parity comes from (FR-043).
        """
        frame = page_frame(self.page_spec(page_number))
        divider = Image.new("RGB", (frame.width, frame.height), "white")
        draw = ImageDraw.Draw(divider)
        try:
            divider_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 60)
        except OSError:
            divider_font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), text, font=divider_font)
        x = (frame.width - (bbox[2] - bbox[0])) // 2
        y = (frame.height - (bbox[3] - bbox[1])) // 2
        draw.text((x, y), text, fill="black", font=divider_font)
        return divider

    def export_book(
        self,
        puzzles: List[dict],
        book_title: str,
        cover_image: Optional[Image.Image] = None,
    ) -> BookExport:
        """Export a book as its two files: the interior PDF and the cover file.

        The one entry point every export route goes through (FR-043, INV-013).
        The interior holds no cover page — its page 1 is the guide page — and
        the cover file is a single page at the book's page size holding the
        uploaded ``cover_image`` when one is given, otherwise the generated
        title cover. Front cover only: the KDP cover wrap (spine, back cover,
        bleed) is deferred.

        Args:
            puzzles: List of puzzle dicts (from puzzle_review service), in
                book order
            book_title: Title for the book (the generated cover's text)
            cover_image: The uploaded front-cover image, if one is set

        The trim is the ``book`` this generator was built for (CARD-116), not
        a pair of loose strings: the two ``trim_*_cm`` arguments this method
        used to take were informational only, and a second way to state the
        sheet is a second sheet waiting to disagree with the one every page is
        laid out on.

        Returns:
            :class:`BookExport` — both files, the interior's page count and
            what it would have been without two-up pairing (FR-040).
        """
        interior = self.interior(puzzles)
        return BookExport(
            interior=self._save_pdf(interior.pages),
            cover=self.export_cover(book_title, cover_image),
            interior_page_count=interior.page_count,
            unpaired_interior_page_count=interior.unpaired_page_count,
        )

    def export_interior(self, puzzles: List[dict]) -> BytesIO:
        """The interior PDF alone — :meth:`export_book`'s ``interior``.

        For a route that serves only the interior: it renders no cover page.
        """
        return self._save_pdf(self.interior_pages(puzzles))

    def export_cover(
        self, book_title: str, cover_image: Optional[Image.Image] = None
    ) -> BytesIO:
        """The cover file alone — :meth:`export_book`'s ``cover``.

        One page: ``cover_image`` when given, else the generated title cover.
        It renders no interior page, so a cover download costs one page.
        """
        return self._save_pdf([self.create_cover_page(book_title, cover_image)])

    def generate_book_pdf(
        self,
        puzzles: List[dict],
        book_title: str,
    ) -> BytesIO:
        """The book's interior PDF alone — :meth:`export_book`'s ``interior``.

        Kept for callers that want only the interior. It carries no cover
        page, so there is no way left to produce the old single file whose
        page 1 was the cover (FR-043).
        """
        return self.export_interior(puzzles)

    @staticmethod
    def _payload(puzzle: dict) -> ExportPayload:
        """One book puzzle as the export's boundary type — the row, as it is.

        The *record* payload: it carries the puzzle's own name and its stored
        tier text, in the spelling the row holds them. Neither reaches a page
        in that form. :meth:`_banded` turns this into the two payloads a page
        is actually drawn from, once the puzzle's print position is known, and
        that position is handed out only after a row has proved it can build a
        payload at all (:meth:`interior_pages`) — which is why the band text is
        not composed here.
        """
        clues_rows = puzzle.get("clues_rows", [])
        clues_cols = puzzle.get("clues_cols", [])
        return ExportPayload(
            grid=puzzle.get("grid", [[]]),
            row_clues=tuple(tuple(row) for row in clues_rows) if clues_rows else (),
            column_clues=tuple(tuple(col) for col in clues_cols) if clues_cols else (),
            seed=0,  # Seed for reproducibility (not available from book puzzles)
            mode="random",  # Mode (not available from book puzzles)
            width=puzzle.get("width"),
            height=puzzle.get("height"),
            name=puzzle.get("puzzle_name"),
            difficulty=puzzle.get("difficulty_tier"),  # Display name, not score
        )

    @staticmethod
    def _banded(
        payload: ExportPayload, puzzle_number: int
    ) -> Tuple[ExportPayload, ExportPayload]:
        """``payload`` as the two payloads its pages are drawn from (ADR-0037/R1).

        Returns ``(puzzle_page_payload, answer_page_payload)``. Both carry the
        same :func:`band_identity` line for ``puzzle_number``; only the answer
        page keeps the picture's title, and the puzzle page's is cleared, which
        is the whole mechanism by which no title is drawn on it — the export
        sets the non-empty header fields and nothing else
        (:func:`~nonogram.export.pdf.header_parts`), so a page whose payload
        has no name has no title to leave off.

        **The title leads on the answer page**, ahead of the identity:
        "Snowflake — Puzzle 12 · Easy". Reading order is the lesser reason.
        The binding one is that the export fits a header too wide for its page
        by setting it smaller and then, at the floor, eliding *the first
        piece* — which it can do safely because the first piece is the only
        one long enough to need it. A 200-character picture name in the second
        slot would be the piece that does not fit and the piece that is never
        cut. Putting the name first keeps that assumption true, so a long name
        is shortened with an ellipsis and the puzzle's number and tier — the
        part the answer key is *used* by — always survives whole.
        """
        identity = band_identity(puzzle_number, payload.difficulty)
        return (
            replace(payload, name=None, difficulty=identity),
            replace(payload, difficulty=identity),
        )

    def _blank_page(
        self, payload: ExportPayload, puzzle_number: int, puzzle_page: int
    ) -> Image.Image:
        """One puzzle's blank page, alone on the sheet of *its own* position.

        A puzzle's blank page and its answer page sit at different places in
        the interior, so they are different sheets whenever their positions
        disagree in parity — the drawing moves sideways by gutter − outside
        and nothing else (FR-032). That is why they are two ``render_pages``
        calls and not one: since ADR-0037/R1 they do not even share a header —
        the puzzle page's band is "Puzzle N · Tier" and the answer page's also
        names the picture (:meth:`_banded`) — so each page is drawn from its
        own payload, and the page the other call also produced (a blank titled
        like an answer, an answer titled like a puzzle page) is dropped.
        """
        puzzle_payload, _ = self._banded(payload, puzzle_number)
        blank, _ = render_pages(puzzle_payload, page_spec=self.page_spec(puzzle_page))
        return blank

    def _answer_page(
        self, payload: ExportPayload, puzzle_number: int, answer_page: int
    ) -> Image.Image:
        """One puzzle's answer page, on the sheet of its own position.

        Unchanged by CARD-127: the answer section is still one page per
        puzzle, in puzzle-number order. FR-042's packed 6-up/4-up key
        (CARD-134) replaces this, in this same file.
        """
        _, answer_payload = self._banded(payload, puzzle_number)
        _, answer = render_pages(answer_payload, page_spec=self.page_spec(answer_page))
        return answer

    def _two_up_page(
        self, plan: PuzzlePagePlan, payloads: List[ExportPayload]
    ) -> Image.Image:
        """The page two puzzles share, composed from what COMP-007 measured.

        The panel strokes; it does not place (ADR-0036/R2, G-1). Every
        coordinate comes off ``plan.pair``: the two slot
        :class:`~nonogram.export.layout.Layout`\\ s carry the shared cell's
        ruled lines and clue centres, and
        :func:`~nonogram.export.layout.header_band` measures each slot's own
        band from its placement. What this method chooses is the *text* of the
        two bands — "Puzzle N · Tier" for each, in print order, the upper slot
        holding the earlier puzzle — exactly as a single page's band text is
        chosen (:meth:`_banded`).

        The page is drawn rather than rendered because ``export/`` offers no
        call that draws a :class:`~nonogram.export.layout.Layout` it is handed;
        see the module docstring.
        """
        pair = plan.pair
        if pair is None:  # pragma: no cover - the walk only sends two-up plans here
            raise ValueError(f"page {plan.page_number} is not a two-up page")
        page = Image.new("RGB", (pair.upper.width, pair.upper.height), BACKGROUND)
        draw = ImageDraw.Draw(page)
        # ``strict``: a plan whose numbers and payloads disagree with its two
        # slots is a bug in the walk, and a silently half-drawn page is the
        # one way a book could ship a puzzle nobody printed.
        for slot, number, payload in zip(
            (pair.upper, pair.lower), plan.numbers, payloads, strict=True
        ):
            placement = slot.page
            if placement is None:  # pragma: no cover - PairLayout refuses one
                raise ValueError("a two-up slot must be a placed page")
            _stroke_drawing(draw, slot)
            _write_clues(draw, slot)
            _set_band(
                draw,
                header_band(slot),
                band_identity(number, payload.difficulty),
                placement.usable_right - placement.usable_left,
            )
        return page

    def puzzle_pages(
        self,
        payloads: List[ExportPayload],
        first_page: int = 2,
        ids: Optional[List[Any]] = None,
    ) -> List[PuzzlePagePlan]:
        """The pairing walk over the book order (FR-040, INV-010, EC-027).

        Walks ``payloads`` — the book order, as CARD-126 leaves it — from the
        first puzzle. Puzzle *i* and puzzle *i+1* are offered to COMP-007's
        :func:`~nonogram.export.layout.compute_pair_layout` **only when their
        tiers are equal** (:func:`_pairable_tier`). A ``PairLayout`` back means
        both go on one page and the walk moves to *i+2*; ``None`` means *i*
        prints alone and the walk moves to *i+1*. The last puzzle of an odd run
        prints alone.

        **Greedy, forward, and deliberately so.** The walk offers only the
        immediate successor, never looks further for a better partner, and
        never leaves a puzzle alone that its successor would have paired with.
        Concatenating the pages' puzzles front to back therefore yields the
        book order exactly: pairing is an arrangement of the order, never a
        change to it (EC-027). The owner arranged that order (INV-009, FR-041)
        and a PDF that re-sorted it to save paper would be silently overruling
        them.

        Each pair is measured on the spec of **its own page** — the page number
        the walk has reached, whose parity is its position (FR-043) — so a page
        saved earlier in the book moves every later page to the other side of
        the spread, and each one is laid out for the side it actually lands on.
        (Parity moves the usable area, never its size, so it cannot change a
        verdict; measuring on the real page is what keeps that true by
        construction rather than by assumption.)

        ``None`` back from :func:`~nonogram.export.layout.compute_pair_layout`
        is the only verdict it has; an **exception** from it is a malformed
        member (clue sets that disagree about the grid) or a page spec that is
        not a book page, and is re-raised as a :class:`RuntimeError` naming the
        two puzzles the walk offered. It is not turned into "this pair does not
        pair": ``None`` means *measured and too small*, and a walk that answered
        it for a member it could not measure would print that member alone and
        leave the export to fail — or not — somewhere else, under a different
        name. The failure is named here, where it happened, so that every abort
        of :meth:`interior` names a puzzle whatever stage it came from.

        Args:
            payloads: The drawable puzzles in print order. A payload's
                ``difficulty`` is the row's stored tier text, and its clue sets
                are what the pair is fitted from.
            first_page: The interior position of the first puzzle page. Page 1
                is the guide page, so the default is 2.
            ids: The puzzle ids, parallel to ``payloads``, for the message of
                the raise below. Optional: without them a failure names the
                print numbers instead.

        Returns:
            One :class:`PuzzlePagePlan` per page, in print order.

        Raises:
            ValueError: ``ids`` was given and is not parallel to ``payloads``
                — naming the wrong puzzle is worse than naming none.
            RuntimeError: a pair the walk offered could not be laid out. The
                message names both members (``_named_puzzles``) and keeps the
                original failure as its ``__cause__``.
        """
        if ids is not None and len(ids) != len(payloads):
            raise ValueError(
                f"ids must be parallel to payloads: {len(ids)} id(s) for "
                f"{len(payloads)} payload(s)"
            )
        plan: List[PuzzlePagePlan] = []
        page_number = first_page
        index = 0
        while index < len(payloads):
            first, second = payloads[index], None
            if index + 1 < len(payloads):
                tier = _pairable_tier(first)
                if tier is not None and tier is _pairable_tier(payloads[index + 1]):
                    second = payloads[index + 1]
            if second is None:
                pair = None
            else:
                numbers = (index + 1, index + 2)
                try:
                    pair = compute_pair_layout(
                        (first.row_clues, first.column_clues),
                        (second.row_clues, second.column_clues),
                        self.page_spec(page_number),
                    )
                except Exception as e:
                    raise RuntimeError(
                        f"puzzle {_named_puzzles(ids, numbers)} could not be "
                        f"laid out: {e}"
                    ) from e
            if pair is None:
                plan.append(PuzzlePagePlan(page_number, (index + 1,)))
                index += 1
            else:
                plan.append(PuzzlePagePlan(page_number, (index + 1, index + 2), pair))
                index += 2
            page_number += 1
        return plan

    def interior_pages(self, puzzles: List[dict]) -> List[Image.Image]:
        """Every page of the interior, in print order; no cover page.

        :attr:`Interior.pages` of :meth:`interior`, for the callers that want
        the pages and not the page-count saving beside them.
        """
        return self.interior(puzzles).pages

    def interior(self, puzzles: List[dict]) -> Interior:
        """Every page of the interior, in print order, and what pairing saved.

        ``pages[n - 1]`` is interior page ``n``: page 1 is the guide page,
        a right-hand page (:func:`page_is_right_hand`), followed by the
        puzzle pages, the SOLUTIONS divider and the answer pages. The list's
        length is the book's page count (FR-030); the cover is never counted.

        A puzzle page holds one puzzle, or two of equal tier that the walk
        paired (:meth:`puzzle_pages`, FR-040). The answer section is untouched:
        one page per puzzle, in puzzle-number order.

        Every page is built on ``book_page_spec(book, its own position)``, so
        each one is the book's trim and takes its parity from where it lands
        (FR-043). That is why the payloads are built first: a puzzle that
        cannot even be turned into an export payload is dropped *before* any
        position is handed out, so no later page is numbered as though a page
        that does not exist were there — every surviving page still sits where
        its **own** 1-based position puts it. The drop is logged, at warning,
        and is the only trace of a member that did not reach the file.

        The same pass decides the **puzzle numbers** ADR-0037/R1 prints. A
        puzzle's ``N`` is its 1-based position among the payloads that
        survived, not among ``puzzles``, so the numbers a reader sees run
        1, 2, 3 with no gap where a dropped member was — and its answer page
        carries that same number, whichever page its puzzle was printed on.
        Numbering follows the print order, whatever put the puzzles in it:
        CARD-128's grouping by level reorders ``puzzles`` and the numbers
        follow.

        Returns:
            The :class:`Interior`: the pages, and the count the same interior
            would have taken with every puzzle on a page of its own (FR-040).

        Raises:
            RuntimeError: one puzzle built a payload and then would not print.
                That failure is **not** swallowed — the page plan
                :func:`interior_page_count` states would no longer describe the
                file, and a book that is quietly one page short is worse than
                an export that says so — so it aborts the whole export. The
                message names the puzzle's ``id``, which is the only thing in
                the raised text a 120-puzzle book can be searched by: the
                position in ``puzzles`` no longer matches the interior once a
                puzzle has been dropped, and the interior page number does not
                point back at a row at all.

                A puzzle can fail at either of two stages, and **both name it**:
                "puzzle <id> could not be laid out" when the pairing walk
                offered it to COMP-007 and the measurement itself failed
                (:meth:`puzzle_pages`; a pair names both members, since the
                measurement is of the two together), and "puzzle <id> could not
                be drawn" when its page would not render. Which stage a given
                malformed row reaches depends on whether it has a same-tier
                neighbour, so a failure that named the row in one book and not
                in the other would be the contract holding by luck.

                It is also raised when the page plan and the pages built
                disagree, and when the walk's plan does not print every puzzle
                exactly once, in order.
        """
        # The puzzle's own id travels with its payload: it is what the raise
        # below names, and once a member has been dropped nothing else left in
        # the loop identifies the row the failure came from.
        payloads: List[Tuple[Any, ExportPayload]] = []
        for puzzle in puzzles:
            # Read outside the try: a row so malformed it is not even a
            # mapping must still be logged, not raise again inside the
            # handler that is reporting it.
            puzzle_id = puzzle.get("id") if hasattr(puzzle, "get") else None
            try:
                payloads.append((puzzle_id, self._payload(puzzle)))
            except Exception as e:
                logger.warning(
                    "Dropping book puzzle %s from the interior: no export "
                    "payload could be built for it (%s)",
                    puzzle_id,
                    e,
                )
                continue

        # The positions every page is built on: 1 the guide page, then the
        # puzzle pages the walk planned, the divider, and one answer page per
        # puzzle. The walk runs before a single page is drawn, because how
        # many pages the puzzles take is what puts the divider and every
        # answer page where it goes.
        count = len(payloads)
        ids = [puzzle_id for puzzle_id, _ in payloads]
        plan = self.puzzle_pages([payload for _, payload in payloads], ids=ids)

        # The walk's own half of the page-plan tripwire below, and the one the
        # tripwire cannot make: `interior_page_count(count, len(plan))` takes
        # the puzzle-page term from the walk's output, so a walk that dropped a
        # puzzle (or printed one twice) would agree with itself and ship a book
        # missing a puzzle whose answer page is printed all the same. Checked
        # against this call's own input instead, before a page is drawn.
        printed = [number for entry in plan for number in entry.numbers]
        if printed != list(range(1, count + 1)):
            raise RuntimeError(
                f"the page plan prints {printed}, not puzzles 1..{count}"
            )
        first_answer_page = 3 + len(plan)

        # Calculate difficulty counts for guide — over every member of the
        # book, drawable or not, because that is what the book holds.
        counts = tier_breakdown(puzzles)
        pages: List[Image.Image] = [
            self.create_guide_page(
                len(puzzles),
                counts[Tier.EASY],
                counts[Tier.MEDIUM],
                counts[Tier.HARD],
                page_number=1,
            )
        ]

        for page_plan in plan:
            members = [payloads[number - 1] for number in page_plan.numbers]
            try:
                if page_plan.pair is None:
                    ((_, payload),) = members
                    pages.append(
                        self._blank_page(
                            payload, page_plan.numbers[0], page_plan.page_number
                        )
                    )
                else:
                    pages.append(
                        self._two_up_page(page_plan, [p for _, p in members])
                    )
            except Exception as e:
                named = _named_puzzles(ids, page_plan.numbers)
                raise RuntimeError(f"puzzle {named} could not be drawn: {e}") from e

        answer_pages: List[Image.Image] = []
        for index, (puzzle_id, payload) in enumerate(payloads):
            try:
                answer_pages.append(
                    self._answer_page(payload, index + 1, first_answer_page + index)
                )
            except Exception as e:
                raise RuntimeError(
                    f"puzzle {puzzle_id!r} could not be drawn: {e}"
                ) from e

        # Add a divider page before solutions
        if answer_pages:
            pages.append(self.create_divider_page(2 + len(plan)))
            # Add all solution pages
            pages.extend(answer_pages)

        # The page plan is this function's own make-up; fail loudly rather
        # than let the two drift apart. It is taken over this call's *input* —
        # the puzzles that survived the payload pass — and over the walk's own
        # verdict on how many pages they take, never over the list the loops
        # above built, so a change to the make-up of the pages (a divider per
        # level, a packed answer key) that forgets `interior_page_count` fails
        # here instead of shipping a book whose stated page count is not its
        # page count.
        planned = interior_page_count(count, len(plan))
        if len(pages) != planned:
            raise RuntimeError(
                f"interior has {len(pages)} pages, its page plan says {planned}"
            )
        return Interior(pages=pages, unpaired_page_count=interior_page_count(count))

    def _save_pdf(self, pages: List[Image.Image]) -> BytesIO:
        """Write ``pages`` as one PDF, one image per page, rewound to 0."""
        # PIL's save_all only works with images in same format
        # Convert all to RGB if needed
        rgb_pages = []
        for page in pages:
            if page.mode != "RGB":
                page = page.convert("RGB")
            rgb_pages.append(page)

        # Save to BytesIO
        pdf_bytes = BytesIO()
        if rgb_pages:
            rgb_pages[0].save(
                pdf_bytes,
                format="PDF",
                save_all=True,
                append_images=rgb_pages[1:] if len(rgb_pages) > 1 else [],
                dpi=(self.dpi, self.dpi),
            )
        pdf_bytes.seek(0)

        return pdf_bytes
