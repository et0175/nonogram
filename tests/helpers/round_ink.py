"""Find a page's round marks by measuring its ink (CARD-241).

Why this exists, and what it replaces
-------------------------------------
CARD-228 cut one function that draws a difficulty tier as three dots, and four
later cards are meant to reuse it rather than each inventing their own. The
guarantee that they *must* was attempted as a static ``ast`` walk over
``src/nonogram/**``, and three review cycles proved that instrument cannot hold
it: the walk discriminates by **syntactic form**, and no authority enumerates
the forms. Each cycle closed the routes it could name and the next cycle landed
a complete second three-dot glyph through a new family one level down —
receiver, then binding form, then call shape, ink accumulated across calls and
a stored bound method.

This module is the other instrument: **render a page, find the ink, measure it
for roundness.** It is blind to spelling altogether, because it never looks at
source code. A disc drawn by ``draw.ellipse``, by a fan of ``draw.line`` rays,
by a loop of ``draw.point`` calls, through ``getattr(draw, "ellipse")``, as a
``chr(0x25CF)`` typed into ``draw.text`` or pasted in as an ``Image`` mask all
land the same ink, so they all measure the same.

Nothing here imports ``nonogram`` at all: it takes a Pillow image and answers
with numbers, which is what keeps it an independent second measurement
(CLAUDE.md, "prefer an independent second implementation") and what lets
CARD-207/229/231/233 reuse it for their own printed proofs.

What is measured, and why those two numbers
-------------------------------------------
Ink is split into **4-connected regions** of horizontal runs (see
:func:`ink_regions`), and each region is measured against its own bounding box:

* :attr:`InkRegion.aspect` — the box's width over its height. A disc's box is
  square: every disc measured during CARD-228's cycles and this card's own
  sweeps reads **exactly 1.000**, at every diameter it was measured at (2 px
  to 142 px; a 1 px ellipse inks nothing) and in every spelling.
* :attr:`InkRegion.fill` — the region's ink over the ink an *inscribed ellipse*
  of that box would carry (``pi / 4 * width * height``). A filled disc reads
  **1.00**; a square reads ``4 / pi`` = **1.273**; a hollow ring reads far
  below 1 because its middle is paper.

A mark is :attr:`~InkRegion.is_round` when both are within tolerance of 1. The
two numbers are not independent dressing: ``aspect`` alone admits every square
the book draws, and ``fill`` alone admits every long filled bar (a 981 x 94
rule on the guide page reads ``fill`` 0.985).

Where the tolerances come from — measured, not chosen
-----------------------------------------------------
Both are the midpoint of a **measured gap**, and both gaps are asserted in
``tests/test_book_difficulty_dots.py::TestRoundMarkOnThePage_TheBoundaryIsMeasured``
so they cannot quietly close:

* :data:`ROUND_FILL_TOLERANCE` = 0.12, i.e. ``fill`` in 0.88..1.12. Measured
  below it: a regular pentagon, 0.822..0.870. Measured above it: a 41 px square
  with a 14 px corner radius, 1.134, and the book's own filled answer cell,
  1.273. Measured inside it: every disc of the sweep (0.961..1.008 over
  diameters 12..142, which is the range
  ``test_a_disc_measures_round_at_every_diameter_it_can_be_drawn`` asserts), a
  regular octagon
  (0.897..0.921), a hexagon (0.930..0.958), a ``chr(0x25CF)`` set as type
  (0.990..1.004), a circular ``Image`` mask pasted in (1.038).
* :data:`ROUND_ASPECT_TOLERANCE` = 0.2, i.e. ``aspect`` in 0.8..1.2. Every disc
  reads 1.000. The nearest mark on the book's own 13 interior pages that gets
  anywhere near a disc's ``fill`` is a letter stem at ``aspect`` 0.545 and a
  filled rule at 10.436, so 0.2 sits in a gap with 0.255 of margin to the
  closer of the two. Chosen *loose* rather than tight on purpose: at 0.08 a
  hexagon (1.083..1.167) would escape, and at 0.2 it does not.

  Read that qualifier as written: it is the nearest mark *carrying a disc's*
  ``fill``. The nearest mark on those pages **overall** is nearer and of
  another kind — a 99 x 94 px filled block at ``aspect`` 1.053, which is
  already *inside* this tolerance — and what keeps it out is ``fill`` alone
  (1.226). So the book's whole margin rests on ``fill``, not on both numbers;
  that is measured, and asserted, in
  ``test_the_closest_the_book_comes_to_a_round_mark_is_measured``.

**No size floor is imposed by hand — and the metric has one of its own.** None
is needed to keep the guard quiet: measured over 33 real pages (the baseline
book's 13, carrying 3222 ink regions, and a seeded picture-corpus book's 20,
carrying 4236) not one ink region of any size passes the metric. And a floor
at the glyph's own smallest dot (12 px at 300 DPI) would have hidden a rogue
mark smaller than the glyph itself can draw. That argument is why none was
written by hand, and it still holds.

What does **not** follow is that the metric therefore has no floor. ``fill``
has a resolution of its own: at a few pixels across, Pillow's raster of a
circle is either too square or too sparse to land inside ``0.88..1.12``.
Measured diameter by diameter, and asserted against a recorded table in
``test_the_metrics_own_size_floor_is_where_the_raster_puts_it``:

* **from 7 px up a filled disc is round**, at every diameter measured to
  142 px;
* **below 7 px the verdict is the raster's accident rather than the shape's**:
  4 px (``fill`` 0.955) and 5 px (1.070) read round, while 2 px (1.273), 3 px
  (0.707) and 6 px (0.849) do not, and a 1 px ellipse inks nothing at all.

So a mark under 7 px may or may not be measured as round, and which it is
depends on the diameter — a bound, not a claim, and it is in the list below.

What this instrument does **not** see (each with a control that fails if the
reach ever widens, in the test class named above)
-------------------------------------------------
**It discriminates on silhouette only.** Every bound below is a corollary of
that one sentence, and so is the next gap anybody finds here: a region's shape
is all this metric has, so every *non-silhouette* property of ink — its
darkness, its colour, its opacity — is open by construction, and closing one
of them takes a different measurement rather than a wider tolerance.

* **a mark lighter than the ink it measures.** :data:`INK_LEVEL` is a hard
  threshold at grey 128 (``tests/helpers/page_ink.py``): a pixel lighter than
  that is paper, so a lighter mark has no region at all — no silhouette, no
  ``aspect``, no ``fill``, nothing to measure. The package already draws
  *above* that threshold: ``book_pdf_generator._SOLVED_GRID_GRAY`` is grey
  160, the colour a solved page rules its answer cells in. A difficulty dot
  stroked in the book's own grey is therefore invisible to this instrument,
  and ADR-0036/R3's declared check passes green with it on the page, where a
  reader of the printed book would see it. Measured: a grey-160 disc yields
  **0 ink regions and 0 round marks**, and the same disc in ``INK`` yields
  **1 of each**
  (``test_a_mark_lighter_than_the_ink_level_is_not_measured_at_all``).
* **a hollow mark.** An outlined circle with paper inside reads ``fill`` 0.15
  to 0.28 and is not round to this metric. The glyph's own outlined dots are in
  that class, and so is a typed ``chr(0x25CB)``. It is not a hole in the guard
  for the glyph's sake — ``DifficultyDots`` cannot express a row with no filled
  dot — but a mark drawn *only* as rings escapes, and that is a bound, not a
  claim.
* **a mark that touches other ink.** Ink is measured in connected regions, so a
  dot stroked across a rule is one region with the rule and is not round. A
  rogue mark deliberately placed on top of existing ink is outside the reach of
  anything that measures silhouettes.
* **a footprint that is not nearly square.** An oval beyond
  :data:`ROUND_ASPECT_TOLERANCE` is not measured as round. The tolerance is
  where the measured gap puts it; a deliberately squashed dot escapes.
* **a mark too small for ``fill`` to resolve.** Under 7 px across the verdict
  is the raster's accident rather than the shape's (the table above): a 6 px
  disc is not round, a 4 px one is. That floor is not imposed — it is what the
  metric's own resolution comes to — and its control is the same recorded
  table, so the day that resolution moves, a test says so.
* **a surface this guard does not render.** It measures the pages it is given.
  A round mark drawn somewhere nobody renders is invisible to it. This is one
  of **two** respects in which CARD-228's static walk — which reads every
  module on disk, and reads an ``ellipse`` call whatever colour it paints in —
  is still the wider instrument; the grey above is the other. That is why both
  are kept.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from PIL import Image

from tests.helpers.page_ink import INK_LEVEL, ink_mask

__all__ = [
    "INK_LEVEL",
    "ROUND_ASPECT_TOLERANCE",
    "ROUND_FILL_TOLERANCE",
    "InkRegion",
    "ink_regions",
    "round_marks",
]

#: How far a region's bounding box may be from square and still be round.
#: 0.2 — the midpoint of the measured gap between a disc (aspect exactly 1.000
#: at every diameter and in every spelling) and the nearest mark on the book's
#: own pages that carries a disc's ``fill`` (a letter stem at 0.545).
ROUND_ASPECT_TOLERANCE = 0.2

#: How far a region's ink may be from an inscribed ellipse's and still be
#: round. 0.12 — the midpoint of the measured gap between a regular pentagon
#: (0.822..0.870) below and a 41 px square with a 14 px corner radius (1.134)
#: above, with every disc of the sweep (0.961..1.008) comfortably inside.
ROUND_FILL_TOLERANCE = 0.12


@dataclass(frozen=True)
class InkRegion:
    """One connected region of ink on a page, in device pixels.

    Attributes:
        left: Its bounding box's left edge, inclusive.
        top: Its top edge, inclusive.
        right: Its right edge, inclusive.
        bottom: Its bottom edge, inclusive.
        ink: How many pixels of the region are ink — the region's area, which
            is **not** the box's area unless the region fills its box.
    """

    left: int
    top: int
    right: int
    bottom: int
    ink: int

    @property
    def box(self) -> tuple[int, int, int, int]:
        """The bounding box as Pillow spells one: ``(left, top, right, bottom)``."""
        return (self.left, self.top, self.right, self.bottom)

    @property
    def width(self) -> int:
        return self.right - self.left + 1

    @property
    def height(self) -> int:
        return self.bottom - self.top + 1

    @property
    def aspect(self) -> float:
        """The box's width over its height: 1.0 for a square footprint."""
        return self.width / self.height

    @property
    def fill(self) -> float:
        """The region's ink over an inscribed ellipse's: 1.0 for a filled disc.

        ``4 / pi`` (1.273) for a filled rectangle, and far below 1 for anything
        hollow — the number that tells a disc from the square cells, frames and
        rules a book page is otherwise made of.
        """
        return self.ink / (math.pi / 4 * self.width * self.height)

    @property
    def is_round(self) -> bool:
        """Whether this region is a round mark.

        Both measurements within tolerance of 1: a nearly square footprint
        carrying nearly as much ink as a disc of that footprint would. See this
        module's docstring for what that catches, what it does not, and which
        measured gap each tolerance sits in.
        """
        return (
            abs(self.aspect - 1.0) <= ROUND_ASPECT_TOLERANCE
            and abs(self.fill - 1.0) <= ROUND_FILL_TOLERANCE
        )


def _ink_runs(mask: np.ndarray) -> tuple[list[int], list[int], list[int]]:
    """Every horizontal run of ink in ``mask``, as ``(row, start, stop)`` lists.

    ``stop`` is exclusive. Found the way ``tests/helpers/page_ink.py`` finds
    its longest runs — a False padded onto both ends of every row so runs
    cannot join across the boundary, then one pass over the transitions — so
    the whole page's runs come out of NumPy in one go and only the merging
    below is Python.
    """
    rows, length = mask.shape
    padded = np.zeros((rows, length + 2), dtype=bool)
    padded[:, 1:-1] = mask
    flat = padded.ravel()
    edges = np.flatnonzero(flat[1:] != flat[:-1])
    starts, ends = edges[0::2], edges[1::2]
    row = starts // (length + 2)
    offset = row * (length + 2)
    return row.tolist(), (starts - offset).tolist(), (ends - offset).tolist()


def ink_regions(page: Image.Image) -> list[InkRegion]:
    """Every connected region of ink on ``page``.

    **4-connected**, and merged by union-find over the page's horizontal runs:
    two runs on adjacent rows belong to the same region when their columns
    overlap. Written here rather than taken from a library because the obvious
    tool (``scipy.ndimage.label``) is not on this project's dependency baseline
    (ADR-0006/R1) and a test helper is where this project puts its independent
    second implementations.

    4-connectivity is the conservative reading: ink that touches only at a
    corner is reported as two regions rather than one, so the measurement never
    merges unrelated marks into a shape neither of them has. A filled disc is
    solid and is therefore never split by it.
    """
    rows, starts, ends = _ink_runs(ink_mask(page))
    count = len(rows)
    if count == 0:
        return []

    parent = list(range(count))

    def root(node: int) -> int:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    # Runs come out in (row, start) order, so each row owns one contiguous
    # slice of the lists; bounds[row] is that slice's first and last index.
    bounds: dict[int, list[int]] = {}
    for index, row in enumerate(rows):
        if row in bounds:
            bounds[row][1] = index
        else:
            bounds[row] = [index, index]

    for row, (first, last) in bounds.items():
        below = bounds.get(row + 1)
        if below is None:
            continue
        here, there = first, below[0]
        while here <= last and there <= below[1]:
            if starts[there] < ends[here] and starts[here] < ends[there]:
                left, right = root(here), root(there)
                if left != right:
                    parent[right] = left
            if ends[here] <= ends[there]:
                here += 1
            else:
                there += 1

    grouped: dict[int, list[int]] = {}
    for index in range(count):
        grouped.setdefault(root(index), []).append(index)

    regions: list[InkRegion] = []
    for members in grouped.values():
        regions.append(
            InkRegion(
                left=min(starts[index] for index in members),
                top=rows[members[0]],
                right=max(ends[index] for index in members) - 1,
                bottom=rows[members[-1]],
                ink=sum(ends[index] - starts[index] for index in members),
            )
        )
    return regions


def round_marks(page: Image.Image) -> list[InkRegion]:
    """Every region of ``page``'s ink that measures as a round mark.

    The whole instrument, in one call: what a printed page carries that a
    reader would see as a dot, however it was drawn.
    """
    return [region for region in ink_regions(page) if region.is_round]
