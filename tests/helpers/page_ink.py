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


def _dark(page: Image.Image) -> np.ndarray:
    return np.asarray(page.convert("L")) < INK_LEVEL


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


def _rule_groups(longest: np.ndarray) -> list[list[int]]:
    peak = longest.max()
    if peak == 0:
        raise ValueError("the page carries no ink at all")
    return _groups(np.flatnonzero(longest >= _RULE_SHARE * peak))


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
    horizontal = _rule_groups(_longest_runs(dark))
    vertical = _rule_groups(_longest_runs(dark.T.copy()))
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
