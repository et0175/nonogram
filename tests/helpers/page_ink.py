"""Measure a rendered book page's drawing off its own ink (CARD-116).

The book PDF's geometry is asserted the way a printer would check it: by
looking at the page. Nothing here imports ``nonogram.export.layout`` or
``nonogram.admin.book_page_spec``, so a test that measures a page with these
helpers and compares the result against numbers worked out in millimetres is
comparing two independent answers, not re-deriving one with the function under
test (CLAUDE.md, "prefer an independent second implementation").

What is measurable, and why
---------------------------
A placed puzzle page is ruled by lines that run the **full** extent of their
axis, gutters included (see ``nonogram.export.layout``'s "What the geometry
is"): a horizontal rule runs from the drawing's left edge to the grid's right
edge, and a vertical rule from the drawing's top edge to the grid's bottom.
So:

Since CARD-222 an interior page also carries **furniture**: a rule under the
header and a hairline above the footer, each running the full text width,
which is wider than the rules of any drawing narrower than the text block. The
horizontal axis is therefore measured inside the drawing's own **box** — the
row span and the column span its vertical rules give, which no furniture
reaches — see :func:`_rule_groups`, :func:`_drawing_rows` and
:func:`_drawing_columns`. The column span also closes a fragility that
predates this card: the QR icon's box is drawn with its top edge on the
drawing's own top row and its far edge on the usable area's, so that one row's
ink runs further than any rule the grid draws, and a page-wide peak taken from
it hid every rule on a page measured here. Nothing else about the measurement
changed, and on a page carrying nothing but its drawing the box contains every
rule there is, so the answer is the same one as before.

* a pixel column crossing a vertical rule holds one **unbroken** run of ink
  the whole height of the drawing, which no other column does: a clue digit's
  ink is broken by the white of its own box every cell. So a column is a rule
  exactly when its longest unbroken run is within :data:`_RULE_SHARE` of the
  longest on the page — and that run's start is the **drawing's top edge**;
* the same for rows, whose longest run starts at the **drawing's left edge**;
* counting the groups of such rows and columns counts the grid's rules, so
  ``columns`` and ``rows`` are read back off the page — which is how "the grid
  is drawn unrotated" is checked rather than assumed;
* the first and last vertical rule are both *heavy* rules, so the distance
  between their left edges is exactly the grid's width whatever a renderer's
  line-cap convention is, and dividing it by the number of columns gives the
  **printed cell**.

It is the *run*, not the column's total ink, that tells a rule from a gutter:
at the small cell a 30x30 gets on a small trim, a column of clue digits can
hold nearly as much ink as a rule does, but never in one piece.

A page whose answer is revealed has long runs of filled cells too. A filled
run lives *inside* the grid, so it is always shorter than the rule beside it
and can never be above the grid's top rule nor left of its left border:
:attr:`Drawing.left` and :attr:`Drawing.top` are safe on an answer page.
:attr:`Drawing.columns` and :attr:`Drawing.rows` are not — count rules on a
blank puzzle page only.

The page the printer measures
----------------------------
:func:`pdf_page_boxes` reads each PDF page's **MediaBox** — its physical size
in PDF points, which is what a printer trims to. It is the other half of
"1800 x 2700 px at 300 DPI" (AC-177): the pixel size is the raster the page
embeds, and only the MediaBox says how large that raster is *printed*. A book
whose ``dpi`` were dropped would keep every pixel assertion green while
measuring 6 x 9 in at the wrong trim, so both are asserted.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PIL import Image, PdfParser

#: A pixel darker than this (0..255 grey) is ink. The same level
#: ``tests/helpers/pdf_pages.py`` reads a PDF's pages at.
INK_LEVEL = 128

#: How long a line's longest unbroken run of ink must be, as a share of the
#: longest on the page, for that line to count as a grid rule.
_RULE_SHARE = 0.9


@dataclass(frozen=True)
class Drawing:
    """One puzzle drawing as the page shows it, in device pixels.

    Attributes:
        left: The drawing's left edge — the row-clue gutter's outer edge.
        top: The drawing's top edge — the column-clue gutter's outer edge.
        grid_left: The grid's left border (the first vertical rule).
        grid_right: The grid's right border (the last vertical rule), measured
            at the same edge of the rule as ``grid_left``.
        grid_top: The grid's top border (the first horizontal rule).
        grid_bottom: The grid's bottom border (the last horizontal rule),
            measured at the same edge of the rule as ``grid_top``. It is the
            lowest ink the drawing puts on the page.
        columns: How many columns the grid is drawn with, counted from its
            vertical rules. Blank puzzle pages only.
        rows: The same, down the page.
        framed: Whether the drawing is closed off by a book page's frame
            (CARD-144; the owner's decision of 2026-09-23, recorded at
            ``meta/architecture/inputs/raw-requirements.md:265`` and not yet
            formalised as a requirement), read off the page — see
            :func:`drawing_of` for what the page is asked, and for why an
            FR-042 answer tile, which carries no gutter of its own, answers
            ``False``.
    """

    left: int
    top: int
    grid_left: int
    grid_right: int
    grid_top: int
    grid_bottom: int
    columns: int
    rows: int
    framed: bool = False

    @property
    def cell(self) -> float:
        """The printed cell in device pixels: the grid's width over its columns."""
        return (self.grid_right - self.grid_left) / self.columns


def pdf_page_boxes(data: bytes) -> list[tuple[float, float, float, float]]:
    """Every page's MediaBox in ``data``, in page order.

    Four PDF points (1/72 in) — ``(left, bottom, right, top)`` — straight off
    the page object Pillow wrote, with nothing re-derived from the page's
    raster. A 6 x 9 in page is ``(0, 0, 432, 648)``.
    """
    parser = PdfParser.PdfParser(buf=data)
    try:
        boxes = []
        for ref in parser.pages:
            page = parser.read_indirect(ref)
            left, bottom, right, top = page[b"MediaBox"]
            boxes.append((float(left), float(bottom), float(right), float(top)))
        return boxes
    finally:
        parser.close()


def ink_mask(page: Image.Image, level: int = INK_LEVEL) -> np.ndarray:
    """``page``'s ink as a boolean mask, ``True`` where a pixel is darker than
    ``level`` (:data:`INK_LEVEL` by default).

    Public because a second measurement of the same pages needs the same
    reading of what ink *is* (CARD-241's ``tests/helpers/round_ink.py``): two
    helpers disagreeing about the threshold would be two different pages.

    ``level`` is a parameter rather than a constant read from the module
    because one of those two measurements reads the page at **two** thresholds
    (CARD-243): a mark the book prints in its own grey is paper to
    :data:`INK_LEVEL` and ink to ``round_ink.MARK_LEVEL``. The default is the
    one every geometry measurement in this module uses, so :func:`drawing_of`
    and ``tests/helpers/two_up_ink.py`` read exactly the page they always did
    — a rule is told from a gutter at grey 128 and nowhere else.

    Args:
        page: The page to read.
        level: A pixel strictly darker than this (0..255 grey) is ink.
    """
    return np.asarray(page.convert("L")) < level


# Kept as an alias only because four call sites already import this name (one
# below and three in ``tests/helpers/two_up_ink.py``), and renaming them is
# outside the footprint of the card that promoted the body to the public
# :func:`ink_mask` (CARD-241, cycle 1 F-007). One concept wants one name: new
# code calls ``ink_mask``, and whoever next edits ``two_up_ink.py`` should
# retire this alias rather than add a fifth caller to it.
def _dark(page: Image.Image) -> np.ndarray:
    return ink_mask(page)


def _groups(indices: np.ndarray) -> list[list[int]]:
    """Consecutive runs of ``indices`` — one group per drawn rule, however thick."""
    groups: list[list[int]] = []
    for index in indices.tolist():
        if groups and index == groups[-1][-1] + 1:
            groups[-1].append(index)
        else:
            groups.append([index])
    return groups


def _longest_run_start(mask: np.ndarray) -> int:
    """Where the longest unbroken run of ink in ``mask`` begins.

    A rule is one unbroken run the whole length of its axis, so its start is
    the drawing's edge. The *first* run would not do: a titled page sets its
    header inside the band above the drawing, and that text can fall in the
    same pixel column as the grid's left border — short runs, well above the
    drawing's top edge, which is exactly the reading this avoids.
    """
    runs = _groups(np.flatnonzero(mask))
    if not runs:
        raise ValueError("no ink on this line")
    return max(runs, key=len)[0]


def _longest_runs(lines: np.ndarray) -> np.ndarray:
    """The longest unbroken run of ink in each row of ``lines``.

    Every row is scanned at once: a False is padded onto both ends of each so
    that runs cannot join across the boundary, the whole thing is flattened,
    and the transitions give every run's start, length and row.
    """
    count, length = lines.shape
    padded = np.zeros((count, length + 2), dtype=bool)
    padded[:, 1:-1] = lines
    flat = padded.ravel()
    edges = np.flatnonzero(flat[1:] != flat[:-1])
    starts, ends = edges[0::2], edges[1::2]
    longest = np.zeros(count, dtype=np.int64)
    np.maximum.at(longest, starts // (length + 2), ends - starts)
    return longest


def _rule_groups(longest: np.ndarray, rows: slice | None = None) -> list[list[int]]:
    """The rule groups of one axis, optionally measured within ``rows`` only.

    ``rows`` is how :func:`drawing_of` keeps **page furniture** out of the
    horizontal axis (CARD-222). An interior page's frame rules run the full
    text width, which is wider than the rules of any drawing narrower than the
    text block, so a page-wide peak would put every grid rule under
    :data:`_RULE_SHARE` of it and the page would read as carrying no grid at
    all. The drawing's own row span is measured independently, off the vertical
    axis, which no page furniture reaches (:func:`_drawing_rows`); both the
    peak and the groups are then taken inside that span, so a rule above or
    below the drawing cannot be mistaken for one of its own and cannot change
    the threshold the drawing's rules are judged by either.
    """
    if rows is not None:
        inside = np.zeros_like(longest)
        inside[rows] = longest[rows]
        longest = inside
    peak = longest.max()
    if peak == 0:
        raise ValueError("the page carries no ink at all")
    return _groups(np.flatnonzero(longest >= _RULE_SHARE * peak))


#: How far **above** its own top edge a drawing's first rule can reach, in
#: pixels. Every rule is centred on its boundary, so half of it falls outside
#: the box it closes (:class:`~nonogram.export.layout.PuzzleFrame`'s own
#: docstring): the heaviest rule the book strokes is 6 px, so 3 px is the
#: overhang, exactly.
#:
#: **Only upwards, and only this far.** The top end needs it: a framed page's
#: top side is a heavy rule centred on the drawing's top edge, and a rule read
#: at half its thickness would not match the border beside it
#: (:func:`_outer_rule_is_a_frames` compares the two). The bottom end does not
#: — nothing below the drawing is read, and the group at the grid's bottom
#: border is identified by its first row either way — while extending the span
#: downwards would reach the footer's hairline on a page whose drawing stops
#: just above it (CARD-222) and count it as one of the grid's own rules.
_EDGE_OVERHANG = 3


def _drawing_columns(vertical: list[list[int]]) -> slice:
    """The columns the drawing itself occupies, from its own vertical rules.

    The first vertical rule is the drawing's leftmost ruled line and the last
    its grid's right border, so every horizontal rule the drawing draws lies
    inside this span — and anything drawn beside the drawing does not.
    """
    return slice(vertical[0][0], vertical[-1][-1] + 1)


def _drawing_rows(dark: np.ndarray, vertical: list[list[int]]) -> slice:
    """The rows the drawing itself occupies, read off its vertical rules.

    A vertical rule is one unbroken run of ink from the drawing's top edge to
    the grid's bottom one, and nothing a page's frame draws makes a run
    anywhere near that long down a column — so the first vertical rule's own
    longest run *is* the drawing's row span, measured without reference to any
    horizontal ink. :data:`_EDGE_OVERHANG` is added at the top, and only
    there, so that a rule centred on the drawing's top edge is counted whole
    — see that constant for why the bottom end is left exactly where the
    drawing's own ink ends.
    """
    column = dark[:, vertical[0][0]]
    runs = _groups(np.flatnonzero(column))
    if not runs:
        raise ValueError("no ink on this line")
    longest = max(runs, key=len)
    return slice(max(0, longest[0] - _EDGE_OVERHANG), longest[-1] + 1)


def _outer_rule_is_a_frames(rules: list[list[int]], edge: int) -> bool:
    """Whether ``rules[0]`` is a frame's side rather than the grid's own border.

    ``rules`` are one axis's rule groups in order, each a run of consecutive
    pixel lines, so ``len(group)`` is how heavily that rule is stroked;
    ``edge`` is the drawing's outer edge on that axis — the point the *other*
    axis's rules all start from.

    Two things are true of a frame's side and of nothing else on the page:

    * **it sits on the drawing's outer edge.** A frame's left side is ruled on
      the drawing's left edge, which is where every horizontal rule starts, so
      its own ink covers ``edge``. The grid's left border does not, on a page
      that has a clue gutter: the border is a whole gutter to the right of it.
    * **the rule beside it is stroked just as heavily.** What lies immediately
      inside a frame's side is the grid's own outer border, and an outer border
      is one of the two heavy rules of its axis. What lies immediately inside a
      grid's *border* is boundary 1, which is heavy only when the grid is one
      cell wide (``MAJOR_RULE_EVERY`` is 5 and ``MIN_SIZE`` is 10, so never):
      it is thin, and thin is exactly half of heavy (ADR-0037/R2).

    The first test alone is what CARD-144 shipped, and it is not enough: an
    FR-042 answer tile carries no clues, so the tile's own left edge **is** its
    grid's left border and the first test passes trivially — which had the key's
    pages reading one column and one row short, with the frame they do not carry
    reported as present. The second test is what tells a zero-gutter drawing
    from a framed one, and it needs no measurement of a gutter's depth, so it
    does not depend on how deep this page's clues happen to run.
    """
    outer, inner = rules[0], rules[1]
    on_the_edge = outer[0] <= edge < outer[0] + len(outer)
    return on_the_edge and len(inner) == len(outer)


def drawing_of(page: Image.Image) -> Drawing:
    """Measure ``page``'s puzzle drawing.

    A book page's frame (CARD-144; owner intake, ``raw-requirements.md:265``,
    not yet a formalised requirement) is told from the grid by where it sits
    and how heavily it is stroked, not by being told about it — the same
    principle as everything else here. :func:`_outer_rule_is_a_frames` states
    the two questions the page is asked, and both axes must answer yes: the
    leftmost full-height rule must be a frame's left side *and* the topmost
    full-width rule a frame's top. The frame's two rules are then dropped
    before the grid's are counted, which is what keeps ``columns``, ``rows``
    and therefore :attr:`Drawing.cell` the grid's own on a framed page and
    identical to before the frame on an unframed one — an FR-042 answer page
    included, where the drawing has no gutter at all.

    Raises:
        ValueError: the page carries no ink, or no grid rules were found (it
            is not a puzzle page).
    """
    dark = _dark(page)
    vertical = _rule_groups(_longest_runs(dark.T.copy()))
    # Inside the drawing's own box on both axes, which the vertical rules give
    # independently of any horizontal ink (:func:`_drawing_rows`,
    # :func:`_drawing_columns`): page furniture above or below the drawing is
    # out of the row span, and a mark beside it — the QR icon, whose own box
    # edge is drawn on the drawing's top row and runs on to the usable area's
    # far edge — is out of the column span. Either would otherwise lengthen a
    # row's run past every rule the grid draws and take the threshold with it.
    rows = _drawing_rows(dark, vertical)
    columns = _drawing_columns(vertical)
    horizontal = _rule_groups(_longest_runs(dark[:, columns].copy()), rows=rows)
    if len(horizontal) < 2 or len(vertical) < 2:
        raise ValueError("this page does not carry a ruled grid")

    left = _longest_run_start(dark[horizontal[0][0]])
    top = _longest_run_start(dark[:, vertical[0][0]])
    framed = _outer_rule_is_a_frames(vertical, left) and _outer_rule_is_a_frames(
        horizontal, top
    )
    if framed:
        horizontal, vertical = horizontal[1:], vertical[1:]
        if len(horizontal) < 2 or len(vertical) < 2:
            raise ValueError("this page carries a frame but no ruled grid inside it")

    return Drawing(
        left=left,
        top=top,
        grid_left=vertical[0][0],
        grid_right=vertical[-1][0],
        grid_top=horizontal[0][0],
        grid_bottom=horizontal[-1][0],
        columns=len(vertical) - 1,
        rows=len(horizontal) - 1,
        framed=framed,
    )
