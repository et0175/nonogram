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
"""

import logging
from collections import Counter
from dataclasses import dataclass, replace
from typing import Any, Dict, Optional, List, Tuple
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

from nonogram.admin.book_page_spec import book_page_spec
from nonogram.difficulty import Tier, tier_of_record
from nonogram.export import ExportPayload
from nonogram.export.layout import DPI, PageSpec, compute_layout
from nonogram.export.pdf import render_pages

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


@dataclass(frozen=True)
class BookExport:
    """A book's export: the interior PDF and, beside it, the cover file.

    ``interior_page_count`` is the book's page count (FR-030 as amended by
    FR-043) — the interior's pages only; the cover file is never counted.
    """

    interior: BytesIO
    cover: BytesIO
    interior_page_count: int


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


def interior_page_count(puzzle_count: int) -> int:
    """The interior's page count for ``puzzle_count`` rendered puzzles.

    The page plan :meth:`BookPDFGenerator.interior_pages` builds — one guide
    page, one page per puzzle, then (only when there are puzzles) the
    SOLUTIONS divider and one answer page per puzzle; never the cover
    (FR-030 as amended by FR-043). ``interior_pages`` checks its own output
    against this, so the Finalise screen, which shows this number before
    anything is rendered, cannot drift from the export's layout rules.

    ``puzzle_count`` counts puzzles that *render*: ``interior_pages`` skips
    a puzzle it cannot build an export payload for, so a count taken from the
    book's members is an upper bound when one of them is broken. That skip is
    the only way the two can differ — a puzzle that builds a payload and then
    will not draw aborts the export with a :class:`RuntimeError` naming it,
    rather than quietly making the file one page shorter than this number.
    CARD-129 owns
    the finalise count's exact equality (EC-034). CARD-116 put every page on
    the book's trim and left this plan alone; the two-up pairing and the
    packed answer key (CARD-134) do change it, and must change it here.
    """
    if puzzle_count < 0:
        raise ValueError(f"puzzle count cannot be negative, got {puzzle_count}")
    return 1 + puzzle_count + (puzzle_count + 1 if puzzle_count else 0)


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
            :class:`BookExport` — both files and the interior's page count.
        """
        pages = self.interior_pages(puzzles)
        return BookExport(
            interior=self._save_pdf(pages),
            cover=self.export_cover(book_title, cover_image),
            interior_page_count=len(pages),
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

    def _puzzle_and_answer(
        self,
        payload: ExportPayload,
        puzzle_number: int,
        puzzle_page: int,
        answer_page: int,
    ) -> Tuple[Image.Image, Image.Image]:
        """One puzzle's two pages, each placed on the sheet of *its own* position.

        A puzzle's blank page and its answer page sit at different places in
        the interior, so they are different sheets whenever their positions
        disagree in parity — the drawing moves sideways by gutter − outside
        and nothing else (FR-032).

        Two ``render_pages`` calls, always. They used to be one whenever the
        two positions shared a parity, because both pages carried the same
        header and differed only in the revealed cells. Since ADR-0037/R1 they
        do not: the puzzle page's band is "Puzzle N · Tier" and the answer
        page's also names the picture (:meth:`_banded`), so each page is drawn
        from its own payload and the page the other call also produced — a
        blank titled like an answer, an answer titled like a puzzle page — is
        dropped rather than used.
        """
        puzzle_payload, answer_payload = self._banded(payload, puzzle_number)
        blank, _ = render_pages(puzzle_payload, page_spec=self.page_spec(puzzle_page))
        _, answer = render_pages(answer_payload, page_spec=self.page_spec(answer_page))
        return blank, answer

    def interior_pages(self, puzzles: List[dict]) -> List[Image.Image]:
        """Every page of the interior, in print order; no cover page.

        ``pages[n - 1]`` is interior page ``n``: page 1 is the guide page,
        a right-hand page (:func:`page_is_right_hand`), followed by the
        puzzle pages, the SOLUTIONS divider and the answer pages. The list's
        length is the book's page count (FR-030); the cover is never counted.

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
        1, 2, 3 with no gap where a dropped member was — and the answer page
        built in the same iteration carries that same number. Numbering
        follows the print order, whatever put the puzzles in it: CARD-128's
        grouping by level reorders ``puzzles`` and the numbers follow.

        Raises:
            RuntimeError: one puzzle built a payload and then would not draw.
                That failure is **not** swallowed — the page plan
                :func:`interior_page_count` states would no longer describe the
                file, and a book that is quietly one page short is worse than
                an export that says so — so it aborts the whole export. The
                message names the puzzle's ``id``, which is the only thing in
                the raised text a 120-puzzle book can be searched by: the
                position in ``puzzles`` no longer matches the interior once a
                puzzle has been dropped, and the interior page number does not
                point back at a row at all. It is also raised when the page
                plan and the pages built disagree.
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

        # The positions every page is built on: 1 the guide page, 2.. the
        # puzzles, then the divider, then one answer page per puzzle.
        count = len(payloads)
        first_answer_page = 3 + count

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

        answer_pages: List[Image.Image] = []
        for index, (puzzle_id, payload) in enumerate(payloads):
            try:
                blank_page, answer_page = self._puzzle_and_answer(
                    payload, index + 1, 2 + index, first_answer_page + index
                )
            except Exception as e:
                raise RuntimeError(
                    f"puzzle {puzzle_id!r} could not be drawn: {e}"
                ) from e
            pages.append(blank_page)
            answer_pages.append(answer_page)

        # Add a divider page before solutions
        if answer_pages:
            pages.append(self.create_divider_page(2 + count))
            # Add all solution pages
            pages.extend(answer_pages)

        # The page plan the Finalise screen shows is this function's own
        # make-up; fail loudly rather than let the two drift apart. The plan
        # is taken over this call's *input* — the puzzles that survived the
        # payload pass — not over a list the loop above built, so a change to
        # the make-up of the pages (a divider per level, a two-up page) that
        # forgets `interior_page_count` fails here instead of shipping a book
        # whose stated page count is not its page count.
        planned = interior_page_count(len(payloads))
        if len(pages) != planned:
            raise RuntimeError(
                f"interior has {len(pages)} pages, its page plan says {planned}"
            )
        return pages

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
