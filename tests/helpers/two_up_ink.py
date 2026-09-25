"""Read a two-up book page's two drawings off its own ink (CARD-127, FR-040).

:func:`tests.helpers.page_ink.drawing_of` measures *one* puzzle drawing on a
page: it takes the page's first and last grid rule as the drawing's top and
bottom, which is right for a page holding one puzzle and wrong for a page
holding two — it would report a single drawing spanning both, with the rules of
both counted as one grid's.

This splits such a page first, and then measures each half with that same
helper, so what a two-up slot is compared against is the same measurement a
single puzzle page is compared against. Nothing here imports
``nonogram.export.layout``, ``nonogram.admin.book_pdf_generator`` or
``book_page_spec``: a test that measures a page with this and compares the
result with millimetres worked out by hand is still comparing two independent
answers.

Which rows are rules
--------------------
A horizontal grid rule is one unbroken run of ink the whole width of **its
own** drawing, and the two slots of a two-up page need not be the same width —
a 10-wide puzzle over a 22-wide one is an ordinary pair. ``page_ink`` counts a
line as a rule when its longest run is within 10% of the longest on the page,
which is exactly right for a page holding one drawing and would, here, find
only the wider slot's rules. :data:`_SLOT_RULE_SHARE` is the same test with
room for the narrower slot: a drawing is at least 11 cells across (a 10-cell
grid behind a 1-deep gutter), and a two-up page's usable width holds at most
``usable / 7.0`` of the shared cell — at most about 40 cells on the widest trim
KDP allows — so the narrower slot's rule is never under about 0.27 of the
wider's. Nothing else on a blank page comes near a quarter of a rule: a clue
digit's run is one glyph wide, a band's letters likewise, and a row crossing the
column-clue gutter meets only the thin verticals, a few pixels each.

Where the cut goes
------------------
Between two consecutive horizontal rules of the **same** drawing there is
always a vertical rule: the verticals run the full extent of their axis,
gutters included, from the drawing's top edge to the grid's bottom one. So a
pixel column somewhere is unbroken ink right through that gap. Between the two
drawings of a two-up page there is no such column — the strip holds the lower
slot's band, whose letters are a few pixels tall each. The cut therefore goes
through the widest gap **no vertical rule crosses**, and a page where every gap
is crossed holds one drawing.

That is a stronger reading than the gap widths it replaced, and CARD-144 is why
it had to be. A framed book page (CARD-144) rules the drawing's own top edge, so
a single puzzle page now shows one extra horizontal rule a whole clue gutter
above the grid — four cells on an ordinary page, which is wider than the 12 mm
band that separates two slots. Measured by gap width alone, a framed
one-puzzle page reads as two drawings and gets cut through its own clue gutter;
measured by what crosses the gap, it reads as the one drawing it is, framed or
not.

A page whose drawing overflows the trim (the ``MIN_CELL_MM`` floor beating page
fit) puts some of its rules off the canvas, so the gaps it shows are not the
grid's; such a page is never a two-up page — FR-040 declines any pair under
7.0 mm long before the 2.0 mm floor — but it is not what this helper is for.
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np
from PIL import Image

from tests.helpers.page_ink import Drawing, _dark, _groups, _longest_runs, drawing_of

#: How long a line's longest unbroken run of ink must be, as a share of the
#: longest on the page, for that line to count as a grid rule of *either* slot.
_SLOT_RULE_SHARE = 0.25


def rule_rows(page: Image.Image) -> list[int]:
    """The first pixel row of every horizontal grid rule on ``page``.

    Raises:
        ValueError: the page carries no ink at all.
    """
    longest = _longest_runs(_dark(page))
    peak = longest.max()
    if peak == 0:
        raise ValueError("the page carries no ink at all")
    return [group[0] for group in _groups(np.flatnonzero(longest >= _SLOT_RULE_SHARE * peak))]


def split_row(page: Image.Image) -> int | None:
    """The pixel row to cut ``page`` at, or ``None`` if it holds one drawing.

    The widest gap between consecutive horizontal rules that no vertical rule
    crosses — see the module docstring for why that, and not the widest gap,
    is the question.

    Raises:
        ValueError: the page carries no ink at all.
    """
    starts = rule_rows(page)
    if len(starts) < 3:
        return None
    dark = _dark(page)
    between = [
        (later - earlier, earlier, later)
        for earlier, later in zip(starts, starts[1:])
        if not _crossed(dark, earlier, later)
    ]
    if not between:
        return None
    _, earlier, later = max(between)
    return (earlier + later) // 2


def _crossed(dark: np.ndarray, earlier: int, later: int) -> bool:
    """Is the gap between two horizontal rules crossed by a vertical one?

    ``True`` when some pixel column is unbroken ink from the first rule's own
    top row through to the second's, which is what every column carrying a
    vertical rule does inside one drawing — and what no column does across the
    strip between two slots, where the only ink is a band's lettering.
    """
    band = dark[earlier : later + 1]
    return bool(band.size and band.all(axis=0).any())


def drawings_of(page: Image.Image) -> list[Drawing]:
    """Every puzzle drawing on ``page``, top to bottom: one of them, or two.

    Each is measured by :func:`tests.helpers.page_ink.drawing_of` on its own
    half of the page, with the lower one's coordinates moved back into the
    page's own frame, so both are in trim pixels like every other measurement.

    Blank puzzle pages only, as ``page_ink`` documents: an answer page's
    revealed runs are long enough to be counted as rules.
    """
    cut = split_row(page)
    if cut is None:
        return [drawing_of(page)]
    upper = drawing_of(page.crop((0, 0, page.width, cut)))
    lower = drawing_of(page.crop((0, cut, page.width, page.height)))
    return [upper, _moved_down(lower, cut)]


def _moved_down(drawing: Drawing, by: int) -> Drawing:
    """``drawing``, measured on a crop, back in the whole page's coordinates."""
    return replace(
        drawing,
        top=drawing.top + by,
        grid_top=drawing.grid_top + by,
        grid_bottom=drawing.grid_bottom + by,
    )
