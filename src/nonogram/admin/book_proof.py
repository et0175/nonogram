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
Each proof page carries one note inside the margins: the trim, the printed
cell in millimetres, and the thin and heavy rule widths in millimetres. On a
portrait trim it is two lines of small type at the page foot. On a square or
landscape trim the drawing reaches the bottom margin and leaves no foot, so
the note moves to the first clear spot that holds it at 10 pt — the outer
side strip beside the drawing (landscape) or the 30 x 30's blank clue corner
(square) — word-wrapped to fit (CARD-172). A trim with no such spot, such as a
15 x 15 cm square, is refused. :func:`_annotate` says how each spot is chosen.
Every figure is **read back off the
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
from nonogram.export.layout import DPI, Layout, PageParity, compute_layout
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

#: The fallback note's type size, in points (CARD-172). Where the foot strip
#: cannot hold the note — a square or landscape trim, whose drawing reaches the
#: bottom margin — the note moves to the outer side strip or the blank clue
#: corner and is set at a fixed 10 pt, CON-020's floor for printed text: 42 px
#: of face at 300 dpi. It never shrinks; a spot too small for it is skipped.
_FALLBACK_NOTE_PT = 10

#: Line spacing of the fallback note, as a multiple of its type size. Tighter
#: than :data:`_NOTE_LEADING` because the fallback is a wrapped block in a
#: bounded box: at 1.35 the 30 x 30's clue corner on an 8.25 x 8.25 in trim
#: does not hold it, at 1.2 it does (CARD-172 Worktree notes).
_FALLBACK_NOTE_LEADING = 1.2

#: The clear air the fallback note keeps from the drawing's rules, in
#: millimetres, measured from the rule's ink rather than its centre line.
_FALLBACK_INSET_MM = 1.0

_POINTS_PER_INCH = 72

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
            :data:`_NOTE_FLOOR_MM`. :func:`_annotate` then tries the
            fallback spots, and refuses with this message if none holds it.
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


@dataclass(frozen=True)
class _Spot:
    """A clear box on the page the fallback note may be set in, in device pixels."""

    name: str
    left: int
    top: int
    right: int
    bottom: int


def _fallback_spots(layout: Layout, frame: PageFrame) -> tuple[_Spot, _Spot]:
    """The outer side strip and the blank clue corner, in that order.

    Every edge is read off ``layout`` and ``frame`` — COMP-007's own answer for
    this page — and nothing is fitted or moved (ADR-0036/R2). The rules either
    spot borders on are heavy rules stroked centred on their coordinate, so a
    spot starts half a heavy rule plus :data:`_FALLBACK_INSET_MM` away from
    each rule's coordinate; on its margin side it runs to the usable area's
    edge, as the foot note does.

    * **Outer side strip**: between the drawing and the outer margin — right of
      the grid on an odd (right-hand) page, left of the drawing on an even one —
      from the drawing's top, which is below the band, down to the bottom
      margin.
    * **Blank clue corner**: the empty box at the drawing's top-left where the
      row and column clue gutters meet, bounded by the frame's left and top
      sides and the grid's left and top borders. No clue digit and no grid rule
      enters it.
    """
    placement = layout.page
    assert placement is not None  # annotation_lines has already refused None
    overhang = -(-layout.thick_rule // 2)
    clear = overhang + round(_FALLBACK_INSET_MM * layout.dpi / _MM_PER_INCH)
    if placement.parity is PageParity.ODD:
        side = _Spot(
            "outer side strip",
            placement.drawing_right + clear,
            placement.drawing_top,
            frame.right,
            frame.bottom,
        )
    else:
        side = _Spot(
            "outer side strip",
            frame.left,
            placement.drawing_top,
            placement.drawing_left - clear,
            frame.bottom,
        )
    corner = _Spot(
        "blank clue corner",
        placement.drawing_left + clear,
        placement.drawing_top + clear,
        layout.grid_left - clear,
        layout.grid_top - clear,
    )
    return side, corner


def _wrapped(text: str, font: ImageFont.FreeTypeFont, width: int) -> list[str] | None:
    """``text`` word-wrapped to ``width`` pixels, or ``None`` if a word is wider.

    Greedy: each printed line takes as many words as fit. A separator dot is
    kept on the end of the word before it, so a wrapped line never starts
    with one.
    """
    words: list[str] = []
    for token in text.split(" "):
        if token == _NOTE_SEPARATOR.strip() and words:
            words[-1] = f"{words[-1]} {token}"
        else:
            words.append(token)
    wrapped: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}" if current else word
        if font.getlength(candidate) <= width:
            current = candidate
        elif current and font.getlength(word) <= width:
            wrapped.append(current)
            current = word
        else:
            return None
    wrapped.append(current)
    return wrapped


def _fallback_note(
    lines: Sequence[str], layout: Layout, frame: PageFrame
) -> tuple[_Spot, list[str], ImageFont.FreeTypeFont, int] | None:
    """The first fallback spot that holds the note at 10 pt, wrapped to fit.

    The note's two lines are run together as one paragraph, joined by the
    same separator its fields are, and wrapped to the spot's width: a narrow
    box fills better that way than with each line wrapped on its own (on the
    30 x 30's clue corner at 8.25 x 8.25 in, 9 lines instead of 10).

    Returns the spot, the wrapped lines, the face and the leading in pixels;
    ``None`` when neither spot holds it.
    """
    font = _note_font(round(_FALLBACK_NOTE_PT * layout.dpi / _POINTS_PER_INCH))
    leading = round(font.size * _FALLBACK_NOTE_LEADING)
    for spot in _fallback_spots(layout, frame):
        block = _wrapped(_NOTE_SEPARATOR.join(lines), font, spot.right - spot.left)
        if block is not None and leading * len(block) <= spot.bottom - spot.top:
            return spot, block, font, leading
    return None


def _annotate(page: Image.Image, layout: Layout, frame: PageFrame) -> Image.Image:
    """Print the proof note inside ``frame``, in the first clear spot that holds it.

    **At the foot, wherever it fits** (CARD-118). The block's bottom sits on
    the usable area's bottom edge and its left on the usable area's left edge,
    so the note is inside the book's own margins on both parities — mirrored
    with the rest of the page, because ``frame`` is this page's frame and not
    page 1's. It is fitted to the strip the drawing leaves between its own
    bottom edge and the bottom margin, less :data:`_NOTE_GAP_MM` of air, at
    :data:`_NOTE_MM` shrinking to :data:`_NOTE_FLOOR_MM`. The portrait KDP
    trims of the test corpus all take this path, and their pages are
    unchanged by CARD-172 (pinned by
    ``TestBookProof_PortraitProofsAreByteIdentical``). So does the 15 x 15 on
    the 8.25 x 8.25, 8.5 x 8.5 and 11 x 8.5 in trims, which leave room at
    its foot.

    **Otherwise in the outer side strip, then the blank clue corner**
    (CARD-172). On a square or landscape trim the drawing is limited by the
    page's *height* and reaches the bottom margin, so there is no foot strip.
    The note is then word-wrapped to the width of the first of
    :func:`_fallback_spots` that holds it at a fixed
    :data:`_FALLBACK_NOTE_PT` pt and set at that spot's top-left: landscape
    trims leave a wide side strip, square trims leave the 30 x 30's clue
    corner.

    **The note never overprints the grid or enters a margin.** If no spot holds
    it — a small square such as 15 x 15 cm — the export refuses rather than
    printing over the puzzle, and the route reports the refusal.

    Raises:
        ValueError: no spot on the sheet holds the note (the message says "no
            room for the proof note"), or ``layout`` is not a placed page.
    """
    lines = annotation_lines(layout)
    placement = layout.page
    assert placement is not None  # annotation_lines has already refused None
    gap = round(_NOTE_GAP_MM * layout.dpi / _MM_PER_INCH)
    try:
        font = _fitted_note_font(
            lines,
            frame.right - frame.left,
            frame.bottom - placement.drawing_bottom - gap,
            layout.dpi,
        )
    except ValueError as foot_refusal:
        fallback = _fallback_note(lines, layout, frame)
        if fallback is None:
            raise ValueError(
                f"{foot_refusal}, and neither the outer side strip nor the blank "
                f"clue corner holds it at {_FALLBACK_NOTE_PT} pt"
            ) from foot_refusal
        spot, block, font, leading = fallback
        left, top = spot.left, spot.top
    else:
        block = list(lines)
        leading = max(1, round(font.size * _NOTE_LEADING))
        left, top = frame.left, frame.bottom - leading * len(lines)
    draw = ImageDraw.Draw(page)
    for index, line in enumerate(block):
        draw.text(
            (left, top + index * leading),
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
