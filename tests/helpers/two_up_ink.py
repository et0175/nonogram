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
The horizontal rules of one drawing are one pitch apart — the printed cell, at
most 7.5 mm (88.6 px at 300 DPI) on a two-up page, since FR-040 caps the shared
cell at the standard cell. Between the two drawings there is always at least the
lower slot's whole band (12 mm, 142 px), because that band sits between the
upper drawing's last rule and the lower drawing's first. So the widest gap
between consecutive rules on a two-up page is always at least 1.6x the
narrowest, and on a one-puzzle page every gap is the same pitch to within the
pixel each boundary was rounded to. :data:`_GAP_RATIO` sits between the two.

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

#: How many times the narrowest gap between consecutive grid rules the widest
#: one must be for the page to be read as holding two drawings.
_GAP_RATIO = 1.5


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

    Raises:
        ValueError: the page carries no ink at all.
    """
    starts = rule_rows(page)
    if len(starts) < 3:
        return None
    gaps = [later - earlier for earlier, later in zip(starts, starts[1:])]
    widest = max(gaps)
    if widest < _GAP_RATIO * min(gaps):
        return None
    index = gaps.index(widest)
    return (starts[index] + starts[index + 1]) // 2


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
