"""ADR-0037's proof pages: the book's own geometry, printed to be measured.

ADR-0037 fixes the band's wording and the book's stroke minimum — thin rule
at least 0.25 mm, heavy rule twice that, in pure black — and then says the
numbers become final **only after the owner has seen them on printed proof
pages**. That step cannot be automated: a ruler on paper is the measurement,
and a 0.25 mm rule on a 4.97 mm cell is either comfortable or too dense by
eye. This module is the export that produces the paper.

What it renders (CARD-118)
--------------------------
Two pages on the book's own :class:`~nonogram.export.layout.PageSpec`:

* **Puzzle 1** — a 30 x 30 whose row *and* column clue gutters are exactly 9
  entries deep, which is the deepest-gutter case at CON-011's largest extent
  and the one that gets the book's **smallest** cell (4.97 mm on CON-018's
  Book 1 profile, which is where NFR-008's 4.8 mm floor is nearly met and
  where a faint rule would hurt most);
* **Puzzle 2** — a 15 x 15 with 7-deep gutters, which is comfortably inside
  the sheet and so takes NFR-008's flat 7.5 mm **cap** on the Book 1 profile.

Together they bracket the book's whole cell range, so one sheet of paper
answers ADR-0037's question at both ends of it.

The two puzzles are **fixed fixtures** (:data:`PROOF_PUZZLES`), written out
below as literal grids. They are not drawn from the database on purpose: the
measurements ADR-0037's checkpoint states — 4.97 mm and 7.5 mm — hold only for
those extents at those gutter depths, so a proof set that changed with the
panel's contents would stop being a proof of anything. The grids were drawn
once from a seeded, transpose-symmetric random source at a density that puts
the deepest clue at exactly the depth wanted, and then frozen here; the
symmetry is why the row and column gutters are equally deep. They are not
meant to be solved and are not claimed to be uniquely solvable — a puzzle page
prints no answer, so what reaches the paper is the ruled grid and the clue
digits, which is exactly what is being measured.

How it reuses the book's page builder (G-1, G-3, ADR-0036/R2)
-------------------------------------------------------------
**This module fits no cell and places no grid rule.** Every millimetre on a
proof page comes from COMP-007's layout for the book's spec, reached through
the same public seams the book PDF uses:
:meth:`~nonogram.admin.book_pdf_generator.BookPDFGenerator.page_spec` for the
sheet, :func:`~nonogram.admin.book_pdf_generator.page_frame` for the usable
area, :func:`~nonogram.admin.book_pdf_generator.band_identity` for the band's
line, and :func:`~nonogram.export.pdf.render_pages` for the page itself. That
is the whole point of the exercise: a proof page that measured itself would
prove something about this module instead of about the book.

Proof pages take interior positions 1 and 2, so page 1 is right-hand (gutter
on the left) and page 2 left-hand — the mirrored margins of FR-032/FR-043 are
visible on the same sheet of paper. Parity never changes a cell, so both pages
measure the same geometry the book will print.

The annotation, and why it lives only here
------------------------------------------
Each proof page carries one two-line note in small type at the page foot,
inside the margins: the trim, the printed cell in millimetres, and the thin
and heavy rule widths in millimetres. Every figure is **read back off the
layout** (:func:`annotation_lines`), never restated from a profile constant,
so the note and the ink beside it cannot disagree — the owner puts a ruler on
the grid and compares it with the page's own claim.

A real book page never carries it. The note is drawn by :func:`_annotate`,
which is called from :func:`proof_pages` and from nowhere else;
``book_pdf_generator`` does not import this module, so there is no path from
the book export to this ink (pinned by
``tests/test_book_proof_pages.py::TestBookProof_AnnotationIsProofOnly``).
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from functools import cached_property, lru_cache
from importlib import resources
from io import BytesIO
from typing import Sequence

from PIL import Image, ImageDraw, ImageFont

from nonogram import clues
from nonogram.admin.book_pdf_generator import (
    BookPDFGenerator,
    PageFrame,
    band_identity,
    page_frame,
)
from nonogram.export import ExportPayload
from nonogram.export.layout import DPI, Layout, compute_layout
from nonogram.export.pdf import FONT_PACKAGE, FONT_RESOURCE, render_pages
from nonogram.limits import MAX_SIZE, MIN_SIZE

__all__ = [
    "PROOF_PUZZLES",
    "ProofPuzzle",
    "annotation_lines",
    "proof_pages",
    "render_proof_pdf",
]

_MM_PER_INCH = 25.4

#: The proof note's nominal type size and the floor it may shrink to, in
#: millimetres. "Small type below the band area or at the page foot" (CARD-118):
#: 2.6 mm is about half the 5 mm band (TERM-028), small enough to read as an
#: annotation rather than as part of the puzzle and large enough to read at
#: arm's length. The floor exists because a narrow trim has a narrow usable
#: width, and a note set past the margin would be a note that fails the very
#: rule it is printed to demonstrate.
_NOTE_MM = 2.6
_NOTE_FLOOR_MM = 1.6

#: Line spacing of the note, as a multiple of its type size.
_NOTE_LEADING = 1.35

#: The clear air the note keeps between itself and the drawing above it, in
#: millimetres. Without it a note on a sheet the drawing nearly fills would
#: sit against the grid's bottom border and read as part of the puzzle.
_NOTE_GAP_MM = 2.0

#: What separates the fields of the note's second line. The same middle dot
#: the band joins a puzzle's number to its tier with (``BAND_SEPARATOR``),
#: written out here rather than imported: the band's mark is ADR-0037's and
#: this one is this card's, and the two are free to differ.
_NOTE_SEPARATOR = " · "


# --------------------------------------------------------------------------
# The two fixed fixtures
# --------------------------------------------------------------------------

#: The 30 x 30 of :data:`PROOF_PUZZLES`, drawn once and frozen (see the module
#: docstring). Its deepest row clue and its deepest column clue are both 9
#: entries, which is what makes the drawing 39 x 39 cells and the printed cell
#: 4.97 mm on the Book 1 profile. ``#`` is a filled cell.
_PROOF_LARGE_ROWS: tuple[str, ...] = (
    ".##.###.....###......##.......",
    "##.#..####.#.#.#.....#.....##.",
    "#.....#####...#.#...#....#.###",
    ".#..##..###...#.#.##..#..##.#.",
    "#..#....#.##...##.##.###.#....",
    "#..#...#.##..##.#.####.##...##",
    "###...#..#.##....#..#.#.#...#.",
    ".##..#.#.##.#..#.##.....#.####",
    ".####...#.##...#...#.###...###",
    ".###.###.#.#........##.#....##",
    "..####.##..###.....#.#..#...#.",
    ".#..#.#.#####....#.###.#.##...",
    "#.....##..##...#.######..###..",
    "##...#....#..###########.###..",
    "#.##.#.......##.......#..#..#.",
    ".#..#..##...##..##.#.####..#..",
    "..####.......#.####.#####...##",
    "......##...###.##..###..##..##",
    "...###.#....##..#...#....#....",
    "...###..#.####.#.#..###..#####",
    "..#..##..#.###..#####..#.#.###",
    "##..##..######.###.#.#...#...#",
    "#..##.#.#...#####..#...#..#...",
    "....##..##.#.#.##...#.#...##..",
    ".....###..#....###.......#..#.",
    "..###......####..#####..#...##",
    "...#...#...###.....#..##..#...",
    ".##....##...##.#...##..#....##",
    ".###.######...#.##.##...##.#.#",
    "..#..#.###......##.###...#.##.",
)

#: The 15 x 15 of :data:`PROOF_PUZZLES`, built the same way. Its gutters are
#: both 7 entries deep, so its drawing is 22 x 22 cells — small enough that the
#: sheet is not what limits it on the Book 1 profile, and NFR-008's 7.5 mm cap
#: is.
_PROOF_SMALL_ROWS: tuple[str, ...] = (
    ".#.#...#.##..#.",
    "#.##.#..#....##",
    ".##.##.#.##..##",
    "##.###....#.#.#",
    "..##.##..####.#",
    ".#######...####",
    "....##.####.#..",
    "#.#..###....###",
    ".#....#.##..###",
    "#.#.#.#.#.###.#",
    "#.###.#..####.#",
    "....##...####.#",
    "...#########...",
    "###..#.##....#.",
    ".#####.#####...",
)


def _grid_of(rows: Sequence[str]) -> list[list[bool]]:
    """``#``/``.`` art as the boolean grid the export takes.

    Raises:
        ValueError: the art is not rectangular, or holds a character that is
            neither ``#`` nor ``.``.
    """
    width = len(rows[0])
    grid: list[list[bool]] = []
    for y, row in enumerate(rows):
        if len(row) != width:
            raise ValueError(f"proof row {y} is {len(row)} cells, not {width}")
        if set(row) - {"#", "."}:
            raise ValueError(f"proof row {y} holds something other than # and .: {row!r}")
        grid.append([character == "#" for character in row])
    return grid


@dataclass(frozen=True)
class ProofPuzzle:
    """One of the two proof puzzles: a fixture, never a row from the database.

    Attributes:
        grid: The solution, as ``list[list[bool]]``'s boundary form. It is
            carried because :class:`~nonogram.export.ExportPayload` takes one;
            no proof page reveals it.
        tier: The tier its band prints after the puzzle number. A *nominal*
            label, not a solver verdict — these fixtures were never graded,
            because they were never generated as puzzles. It is printed so the
            band on the proof is the length and weight the book's own band will
            be, and the page says on its face (:func:`annotation_lines`) that
            it is a proof page and not a book page. ADR-0037/R1 governs a book
            puzzle page's band; nothing here reaches a book.
    """

    grid: tuple[tuple[bool, ...], ...]
    tier: str

    @staticmethod
    def from_art(rows: Sequence[str], tier: str) -> "ProofPuzzle":
        """A fixture from ``#``/``.`` art, checked against CON-011's range.

        Raises:
            ValueError: a side lies outside :data:`~nonogram.limits.MIN_SIZE`
                ..:data:`~nonogram.limits.MAX_SIZE`. A proof page is only a
                proof of what the book prints if the fixture is a grid the
                book could actually hold.
        """
        grid = _grid_of(rows)
        puzzle = ProofPuzzle(grid=tuple(tuple(row) for row in grid), tier=tier)
        for side, extent in (("width", puzzle.width), ("height", puzzle.height)):
            if not MIN_SIZE <= extent <= MAX_SIZE:
                raise ValueError(
                    f"proof fixture {side} is {extent}, outside CON-011's "
                    f"{MIN_SIZE}..{MAX_SIZE}"
                )
        return puzzle

    @property
    def width(self) -> int:
        """The grid's extent across (ADR-0022: an extent is a pair, never a size)."""
        return len(self.grid[0])

    @property
    def height(self) -> int:
        return len(self.grid)

    @cached_property
    def row_clues(self) -> tuple[tuple[int, ...], ...]:
        """The run-length encoding of :attr:`grid`'s rows (INV-001).

        Derived from the grid rather than written out beside it: one statement
        of the fixture, so the clues on the page can never describe a different
        picture than the grid does. Cached because a page render asks for them
        several times and the fixture cannot change.
        """
        return clues.compute_clues([list(row) for row in self.grid]).rows

    @cached_property
    def column_clues(self) -> tuple[tuple[int, ...], ...]:
        return clues.compute_clues([list(row) for row in self.grid]).columns

    @property
    def row_gutter_depth(self) -> int:
        """How many clue boxes deep the left gutter is — the longest row clue.

        With :attr:`column_gutter_depth` and the extent, this is what decides
        the printed cell, which is why the checkpoint's 4.97 mm and 7.5 mm are
        claims about *these* depths and are pinned by a test.
        """
        return max(len(clue) for clue in self.row_clues)

    @property
    def column_gutter_depth(self) -> int:
        return max(len(clue) for clue in self.column_clues)

    def payload(self, band: str) -> ExportPayload:
        """The fixture as COMP-007's boundary type, banded with ``band``.

        ``name`` is ``None``, exactly as a book puzzle page's payload is
        (ADR-0037/R1): the export sets the non-empty header fields and nothing
        else, so a payload with no name has no title to leave off.
        """
        return ExportPayload(
            grid=[list(row) for row in self.grid],
            row_clues=self.row_clues,
            column_clues=self.column_clues,
            seed=0,
            mode="random",
            width=self.width,
            height=self.height,
            name=None,
            difficulty=band,
        )


#: ADR-0037's proof set, in the order it prints. The 30 x 30 first: it is the
#: page the decision is actually about (the smallest cell and the tightest
#: rules), so it is the one the owner meets first and the one that lands on a
#: right-hand page.
PROOF_PUZZLES: tuple[ProofPuzzle, ...] = (
    ProofPuzzle.from_art(_PROOF_LARGE_ROWS, tier="hard"),
    ProofPuzzle.from_art(_PROOF_SMALL_ROWS, tier="easy"),
)


# --------------------------------------------------------------------------
# The proof-only annotation
# --------------------------------------------------------------------------


def _mm_of(pixels: float, dpi: int) -> float:
    """``pixels`` at ``dpi`` as millimetres — the note's one conversion."""
    return pixels * _MM_PER_INCH / dpi


def annotation_lines(layout: Layout) -> tuple[str, str]:
    """What a proof page says about itself, read back off ``layout``.

    Two lines: the trim, then the printed cell and the two rule widths, all in
    millimetres. Nothing here is restated from :data:`BOOK1_PROFILE
    <nonogram.admin.book_page_spec.BOOK1_PROFILE>` or from an argument this
    module passed in — the trim is the laid-out page's own size, the cell is
    :attr:`PagePlacement.cell_mm <nonogram.export.layout.PagePlacement.cell_mm>`
    (the exact millimetre, not the pixel pitch re-divided), and the rules are
    the widths COMP-007 will actually stroke. So the note is a *measurement of
    the page it is printed on*, which is the only kind of claim a ruler can
    check.

    Raises:
        ValueError: ``layout`` is not a placed page (its spec carried no
            parity), so it has no trim and no book cell to report.
    """
    placement = layout.page
    if placement is None:
        raise ValueError(
            "a proof note describes a placed book page: lay the fixture out "
            "on a spec with a parity (book_page_spec)"
        )
    width_mm = _mm_of(layout.width, layout.dpi)
    height_mm = _mm_of(layout.height, layout.dpi)
    fields = (
        f"cell {placement.cell_mm:.2f} mm",
        f"thin rule {_mm_of(layout.thin_rule, layout.dpi):.2f} mm",
        f"heavy rule {_mm_of(layout.thick_rule, layout.dpi):.2f} mm",
        f"grid {layout.columns} × {layout.rows}, clues "
        f"{layout.row_gutter_cells} and {layout.column_gutter_cells} deep",
    )
    return (
        f"PROOF PAGE (not a book page) · trim {width_mm:.1f} × "
        f"{height_mm:.1f} mm ({layout.width_inches:.2f} × "
        f"{layout.height_inches:.2f} in) at {layout.dpi} dpi",
        _NOTE_SEPARATOR.join(fields),
    )


@lru_cache(maxsize=1)
def _note_font_bytes() -> bytes:
    """The bundled DejaVu Sans, read once.

    The same package data COMP-007 sets its header in
    (:data:`~nonogram.export.pdf.FONT_PACKAGE` /
    :data:`~nonogram.export.pdf.FONT_RESOURCE`, both public), loaded here
    rather than through that module's private ``_header_font``. The note needs
    the middle dot and the multiplication sign, which Pillow's embedded default
    face does not carry, and G-2 puts ``src/nonogram/export/**`` out of this
    card's reach — so the seam is these six lines, on this side of the
    boundary, addressing the font as package data exactly as the export does.
    """
    return resources.files(FONT_PACKAGE).joinpath(FONT_RESOURCE).read_bytes()


@lru_cache(maxsize=16)
def _note_font(face_px: int) -> ImageFont.FreeTypeFont:
    """The note's face at ``face_px`` device pixels of type size.

    ``face_px`` is a **type** size, never a grid extent (ADR-0022/R1): the
    parameter is named for the face so the two cannot be confused, here or by
    the package-wide scalar-extent guard.
    """
    return ImageFont.truetype(io.BytesIO(_note_font_bytes()), size=face_px)


def _fitted_note_font(
    lines: Sequence[str], width: int, height: int, dpi: int
) -> ImageFont.FreeTypeFont:
    """The largest note face at or below :data:`_NOTE_MM` that fits the strip.

    ``width`` is the usable width and ``height`` the clear strip the drawing
    leaves above the bottom margin. The nominal size is scaled proportionally
    first and then stepped down, the way the export fits a header: on a narrow
    or shallow strip the note is what gives, never the margin it is printed
    inside.

    Raises:
        ValueError: the strip cannot hold the note even at
            :data:`_NOTE_FLOOR_MM`. See :func:`_annotate` for why this is a
            refusal and not an overprinted grid.
    """
    nominal = max(1, round(_NOTE_MM * dpi / _MM_PER_INCH))
    floor = max(1, round(_NOTE_FLOOR_MM * dpi / _MM_PER_INCH))

    def widest(face_px: int) -> float:
        font = _note_font(face_px)
        return max(font.getlength(line) for line in lines)

    def tall(face_px: int) -> float:
        return max(1, round(face_px * _NOTE_LEADING)) * len(lines)

    face_px = nominal
    total = widest(face_px)
    if total > width:
        face_px = max(floor, int(face_px * width / total))
    while face_px > floor and (widest(face_px) > width or tall(face_px) > height):
        face_px -= 1
    if widest(face_px) > width or tall(face_px) > height:
        raise ValueError(
            "this trim leaves no room for the proof note inside its margins: "
            f"the note needs {widest(face_px) * _MM_PER_INCH / dpi:.1f} x "
            f"{tall(face_px) * _MM_PER_INCH / dpi:.1f} mm and the page has "
            f"{width * _MM_PER_INCH / dpi:.1f} x {height * _MM_PER_INCH / dpi:.1f} mm "
            "clear below the drawing"
        )
    return _note_font(face_px)


def _annotate(page: Image.Image, layout: Layout, frame: PageFrame) -> Image.Image:
    """Print the proof note at ``page``'s foot, inside ``frame``.

    The block's bottom sits on the usable area's bottom edge and its left on
    the usable area's left edge, so the note is inside the book's own margins
    on both parities — mirrored with the rest of the page, because ``frame``
    is this page's frame and not page 1's.

    **The note never overprints the grid.** It is fitted to the strip the
    drawing leaves between its own bottom edge and the bottom margin, less
    :data:`_NOTE_GAP_MM` of air, and a strip too shallow for the note at its
    floor size raises rather than printing over the puzzle. That case is a
    sheet the drawing fills top to bottom, which happens when the trim is
    close to square — the drawing is then limited by the page's *height*
    instead of its width, and both proof fixtures are square, so there is
    nothing left at the foot. A proof page whose own measurements were printed
    across its grid would be unreadable exactly where it has to be read, and a
    note pushed into the margin would break the rule it is printed to
    demonstrate; so the refusal names the trim and the route reports it. Every
    portrait book trim (every KDP paperback size taller than it is wide by more
    than about a centimetre) leaves tens of millimetres of clear strip.

    Raises:
        ValueError: the sheet leaves no room for the note (see above), or
            ``layout`` is not a placed page.
    """
    lines = annotation_lines(layout)
    placement = layout.page
    assert placement is not None  # annotation_lines has already refused None
    gap = round(_NOTE_GAP_MM * layout.dpi / _MM_PER_INCH)
    font = _fitted_note_font(
        lines,
        frame.right - frame.left,
        frame.bottom - placement.drawing_bottom - gap,
        layout.dpi,
    )
    leading = max(1, round(font.size * _NOTE_LEADING))
    top = frame.bottom - leading * len(lines)
    draw = ImageDraw.Draw(page)
    for index, line in enumerate(lines):
        draw.text(
            (frame.left, top + index * leading),
            line,
            fill="black",
            font=font,
            anchor="la",
        )
    return page


# --------------------------------------------------------------------------
# The export
# --------------------------------------------------------------------------


def proof_pages(book: object = None) -> list[Image.Image]:
    """ADR-0037's proof pages for ``book``'s sheet, in print order.

    Args:
        book: Anything carrying the ``books`` print columns — a
            :class:`~nonogram.admin.book_manager.Book` or a row. ``None`` is a
            book with no stored print specification, which is CON-018's Book 1
            profile, exactly as an empty column is. **No puzzle membership is
            read**: proofs come before curation, so a draft book with an empty
            selection produces the same two pages a finished one does.

    Raises:
        ValueError: the book's stored print specification cannot be laid out —
            the message names the column at fault.
    """
    generator = BookPDFGenerator(book)
    pages: list[Image.Image] = []
    for position, puzzle in enumerate(PROOF_PUZZLES, start=1):
        spec = generator.page_spec(position)
        payload = puzzle.payload(band_identity(position, puzzle.tier))
        page, _ = render_pages(payload, page_spec=spec)
        layout = compute_layout(payload.row_clues, payload.column_clues, spec)
        pages.append(_annotate(page, layout, page_frame(spec)))
    return pages


def render_proof_pdf(book: object = None) -> BytesIO:
    """:func:`proof_pages` as one PDF, rewound to 0.

    One image per page at :data:`~nonogram.export.layout.DPI`, which is what
    makes the pages their trim in the document rather than 4.17x too large —
    the same writing ``BookPDFGenerator`` does for the interior. It is six
    lines here rather than a call into that generator because its writer is
    private and G-3 puts the module out of this card's reach; the note on
    ``_note_font_bytes`` says the same about the face.
    """
    pages = proof_pages(book)
    pdf_bytes = BytesIO()
    pages[0].save(
        pdf_bytes,
        format="PDF",
        save_all=True,
        append_images=pages[1:],
        dpi=(DPI, DPI),
    )
    pdf_bytes.seek(0)
    return pdf_bytes
