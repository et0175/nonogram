"""Find a page's round marks by measuring its ink (CARD-241, CARD-243).

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

This module is the other instrument: **render a page, find the marks, measure
them for roundness.** It is blind to spelling altogether, because it never
looks at source code. A disc drawn by ``draw.ellipse``, by a fan of
``draw.line`` rays, by a loop of ``draw.point`` calls, through ``getattr(draw,
"ellipse")``, as a ``chr(0x25CF)`` typed into ``draw.text`` or pasted in as an
``Image`` mask all land the same ink, so they all measure the same.

It is also blind to **which tone** the mark is printed in, within the range the
package prints at (CARD-243). CARD-241 read ink at one hard threshold, grey 128,
and the package draws its solved grid at grey 160 — lighter than that, so a
difficulty dot stroked in the book's own grey had no region, no ``aspect`` and
no ``fill``, and ADR-0036/R3's declared check passed green with eighteen of them
printed on the pages. :data:`MARK_LEVEL` is where a **mark** begins instead:
grey 208, the midpoint of the gap between the lightest tone the package draws
and paper. Both readings are kept, because they answer different questions —
:func:`ink_regions` is still *what ink is on this page*, which is what every
geometry measurement in ``tests/helpers/page_ink.py`` asks and what CARD-241's
recorded figures are figures of, and :func:`mark_regions` is *what a reader of
the printed page would see*.

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
  filled rule at 10.316, so 0.2 sits in a gap with 0.255 of margin to the
  closer of the two. Chosen *loose* rather than tight on purpose: at 0.08 a
  hexagon (1.083..1.167) would escape, and at 0.2 it does not.

  Read that qualifier as written: it is the nearest mark *carrying a disc's*
  ``fill``. The nearest mark on those pages **overall** is nearer and of
  another kind — a 99 x 95 px filled block at ``aspect`` 1.042, which is
  already *inside* this tolerance — and what keeps it out is ``fill`` alone
  (1.226). So the book's whole margin rests on ``fill``, not on both numbers;
  that is measured, and asserted, in
  ``test_the_closest_the_book_comes_to_a_round_mark_is_measured``.

**Both tolerances were re-measured against the wider ink population**
(CARD-243) and **both keep their values, because the measurement says so.**
Widening the threshold brings the book's own grey and every glyph's
anti-aliased edge into the population, and the canvas shapes above do not move
at all — ``polygon``, ``ellipse`` and ``rounded_rectangle`` do not anti-alias,
so a pentagon still reads 0.870, a hexagon 0.958, and the rounded rectangle
still flips between a 14 px corner radius and a 15 px one. What moves is the
book's own figures, measured over the same 13 pages at each threshold:

======================  ============  ============  ======================
measurement             at grey 128   at grey 208   set by
======================  ============  ============  ======================
margin (either          1.8855        **1.8182**    a 99 x 95 block /
tolerance, whichever                                a 7 x 11 letter stem
binds)
``ROUND_FILL`` room     1.8855        1.8855        the same 99 x 95 block
``ROUND_ASPECT`` room   2.2727        **46.5789**   a letter stem / a rule
======================  ============  ============  ======================

So the margin falls by 3.6 % and **changes hands** — at grey 208 it is carried
by ``aspect``, because the letter stem that sets it grows a pixel of its own
grey edge and leaves the fill tolerance — while ``fill``'s own room on the book
is untouched, the 99 x 95 block being a hard-edged rectangle with no grey edge
to grow. Each figure is asserted in
``test_the_closest_the_book_comes_to_a_round_mark_is_measured`` and
``test_each_tolerances_own_room_on_the_book_is_measured``.

**No size floor is imposed by hand — and the metric has one of its own.** None
is needed to keep the guard quiet: measured over 34 real pages (the baseline
book's 13, carrying 2640 ink regions, and a seeded picture-corpus book's 21,
carrying 3689 — 33 pages, 3222 and 4236, before CON-018's amended margins
shrank the usable area) not one ink region of any size passes the metric. And a floor
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

What this instrument does **not** see
------------------------------------
**It discriminates on silhouette, within a range of tones.** Each bound below
carries its ``BOUND:`` marker, and the markers are not decoration: they are
read back by ``test_each_bound_list_carries_exactly_the_open_bounds``, which
holds this list to a table whose every verdict is derived by execution and
whose every row has a control that fails if the reach widens
(``MEASURED_MARK_BOUNDS`` in
``tests/test_book_difficulty_dots.py``). A bound is struck from this list only
in the diff that closes it, and
``test_the_struck_bound_and_the_closed_route_agree`` is red in both directions
if the two ever come apart.

**One bound was struck.** CARD-241's widest bound — *darkness*, a mark lighter
than grey 128 — is closed: the metric reads at :data:`MARK_LEVEL` now, so the
book's own grey 160 is a mark, and a glyph stroked in it is found on the real
pages it is planted on (``TestRoundMarkOnThePage_SeesTheGreysTheBookPrints``).
What replaced it is the first three bullets below: a threshold is not gone, it
has moved, and the three ways a mark can reach the lighter side of the new one
are each measured with the darker control beside it.

* **a mark lighter than the threshold itself** (BOUND: lightness). A flat tone
  at :data:`MARK_LEVEL` exactly is paper again; one level darker is found. The
  crossing is one grey level wide, which makes it the tightest control in this
  list — and nothing the package draws is on the far side of it, which is the
  difference between this bound and the one that was struck.
* **a light luminance in a colour nobody would call light** (BOUND: colour).
  The metric reads ``convert("L")``, so it reads luminance and not colour. Pure
  yellow is luminance 226 and is **not** measured at all, while pure red is 76
  and is. A reader of a colour proof would see both.
* **ink composited thin enough to land above the threshold** (BOUND: opacity).
  A black disc pasted through a flat alpha mask at 40 composites to tone 215
  and is not measured; at 64 it composites to 191 and is. So the bound is the
  tone the compositing comes to, and the crossing sits between those two.
* **a hollow mark** (BOUND: hollow). An outlined circle with paper inside reads
  ``fill`` 0.15 to 0.28 and is not round to this metric. The glyph's own
  outlined dots are in that class, and so is a typed ``chr(0x25CB)``. It is not
  a hole in the guard for the glyph's sake — ``DifficultyDots`` cannot express
  a row with no filled dot — but a mark drawn *only* as rings escapes, and that
  is a bound, not a claim.
* **a mark that touches other ink** (BOUND: touching). Marks are measured in
  connected regions, so a dot stroked across a rule is one region with the rule
  and is not round. A rogue mark deliberately placed on top of existing ink is
  outside the reach of anything that measures silhouettes.
* **a footprint that is not nearly square** (BOUND: footprint). An oval beyond
  :data:`ROUND_ASPECT_TOLERANCE` is not measured as round. The tolerance is
  where the measured gap puts it; a deliberately squashed dot escapes.
* **a mark too small for ``fill`` to resolve** (BOUND: resolution). Under 7 px
  across the verdict is the raster's accident rather than the shape's (the
  table above): a 6 px disc is not round, a 4 px one is. That floor is not
  imposed — it is what the metric's own resolution comes to — and its control
  is the same recorded table, so the day that resolution moves, a test says so.
  The table is unchanged at the wider threshold, because ``draw.ellipse`` does
  not anti-alias.
* **a surface this guard does not render** (BOUND: unrendered). It measures the
  pages it is given. A round mark drawn somewhere nobody renders is invisible
  to it — the metric finds a disc on a cover page perfectly well, and the cover
  is not an interior page. This is now the **only** respect in which CARD-228's
  static walk, which reads every module on disk, is the wider instrument; the
  grey that used to be the other is closed. That is still why both are kept
  (CARD-243 G-1).
"""

from __future__ import annotations

import math
import re
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from PIL import Image

from tests.helpers.page_ink import INK_LEVEL, ink_mask

__all__ = [
    "INK_LEVEL",
    "MARK_LEVEL",
    "MEASURED_LEVELS",
    "ROUND_ASPECT_TOLERANCE",
    "ROUND_FILL_TOLERANCE",
    "InkRegion",
    "StreamMark",
    "StreamShapeError",
    "ink_regions",
    "mark_regions",
    "round_marks",
    "round_stream_marks",
    "stream_marks",
]

#: A PDF number as a content stream writes one: no exponent form, because
#: ``nonogram.admin.book_vector._number`` refuses to emit one.
_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")

#: Where a **mark** begins, as against where ink begins: a pixel darker than
#: this (0..255 grey) is something a reader of the printed page would see,
#: whatever tone it is printed in. 208 — the midpoint of the measured gap
#: between the lightest tone the package draws (grey 160,
#: ``book_pdf_generator._SOLVED_GRID_GRAY``) and paper (grey 255), rounded up,
#: so the darker side of that gap is a mark and paper is not.
#:
#: Derived rather than chosen: the package's whole palette is three flat tones
#: (``INK`` 0, ``_SOLVED_GRID_GRAY`` 160, ``BACKGROUND`` 255), and
#: ``tests/test_book_difficulty_dots.py``'s
#: ``test_the_mark_level_is_the_midpoint_of_the_palette_the_package_draws``
#: enumerates them off the package on disk and recomputes this number, so a
#: production module that starts drawing in a lighter tone reds a test rather
#: than quietly escaping the measurement.
MARK_LEVEL = 208

#: The two thresholds a page is read at, darkest first. :data:`INK_LEVEL` is
#: CARD-241's — the reading every *geometry* measurement in
#: ``tests/helpers/page_ink.py`` uses, and the one whose numbers on the book's
#: own pages are recorded and asserted; :data:`MARK_LEVEL` is CARD-243's, the
#: reading :func:`round_marks` answers at. Both are kept because they measure
#: different things and neither contains the other's recorded figures.
MEASURED_LEVELS = (INK_LEVEL, MARK_LEVEL)

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


def ink_regions(page: Image.Image, level: int = INK_LEVEL) -> list[InkRegion]:
    """Every connected region of ``page``'s pixels darker than ``level``.

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

    ``level`` defaults to :data:`INK_LEVEL`, so this call still answers
    CARD-241's question — *what ink is on this page* — unchanged, and the
    figures recorded against it (2640 regions on the baseline interior's 13
    pages, a margin of 1.8855) still reproduce. :func:`mark_regions` is the
    same question asked at :data:`MARK_LEVEL`.

    Args:
        page: The page to measure.
        level: A pixel strictly darker than this (0..255 grey) belongs to a
            region.
    """
    rows, starts, ends = _ink_runs(ink_mask(page, level))
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


def mark_regions(page: Image.Image) -> list[InkRegion]:
    """Every connected region of ``page``'s **marks** — ink or lighter tone.

    :func:`ink_regions` at :data:`MARK_LEVEL`: the reading that includes every
    tone the package draws, not only the ones darker than grey 128. Separate
    from :func:`ink_regions` rather than a changed default, so the two
    thresholds are two named calls and CARD-241's recorded figures stay
    readable off the call that produced them.
    """
    return ink_regions(page, MARK_LEVEL)


def round_marks(page: Image.Image, level: int = MARK_LEVEL) -> list[InkRegion]:
    """Every region of ``page`` that measures as a round mark.

    The whole instrument, in one call: what a printed page carries that a
    reader would see as a dot, however it was drawn **and in whatever tone the
    book prints it**. ``level`` defaults to :data:`MARK_LEVEL` rather than to
    :data:`INK_LEVEL` because a reader does not read a threshold: a dot in the
    book's own grey 160 is a dot on the paper, and before CARD-243 this call
    answered that it was not there at all. Pass :data:`INK_LEVEL` to ask
    CARD-241's narrower question — the black-ink control does, which is how
    "the widened reading is what catches the grey" stays a measurement.

    Args:
        page: The page to measure.
        level: The darkness threshold a region must reach to be measured.
    """
    return [region for region in ink_regions(page, level) if region.is_round]


# --------------------------------------------------------------------------
# The vector twin: the same two numbers, read off a content stream (CARD-331)
# --------------------------------------------------------------------------
#
# Everything above reads a **bitmap**. A page written as operators
# (ADR-0042/R1) has no pixels to read, and a raster instrument pointed at one
# does not measure a lighter page — it measures nothing at all. CARD-331's
# subject is what that costs: the difficulty-dot accounting hooked the raster
# drawing site, and a hook on a function the page never calls never fires.
#
# ``stream_marks`` below is the twin, and it is deliberately a **different
# instrument with a different domain**, not the same one widened:
#
# * ``ink_regions`` measures **ink extents** in device pixels — where the
#   raster actually put dark pixels, which for a stroked shape sits
#   ``(width - 1) // 2`` outside the boundary that was asked for (CARD-330).
# * ``stream_marks`` measures **path coordinates** in PDF points — the
#   boundary the stream *states*, before any rasteriser has decided which
#   pixel to darken.
#
# So a figure from one is not a figure from the other, and differencing them
# produces an artefact that reads exactly like a placement disagreement
# (CARD-309 lost a round to that). Every call site here must say which domain
# its reading is in, and an accounting must match path against path or ink
# against ink — never one against the other.

#: Every PDF path-construction operator this reader understands, and how many
#: operands each takes. ``h`` closes the current subpath and takes none.
#:
#: ``v`` and ``y`` — the two shorthand Bézier operators — are deliberately
#: **absent**: this project's writer emits neither
#: (``nonogram.admin.book_vector.ContentStream``), and a reader that guessed
#: at a shape it had never been shown would be the silent pass ADR-0039/R2
#: refuses. :func:`stream_marks` raises on them instead.
#:
#: That "the writer emits neither" is a **measurement**, not this comment's
#: word: ``tests/test_book_difficulty_dots.py``'s
#: ``test_the_readers_vocabulary_covers_every_operator_the_writer_emits``
#: drives every public ``ContentStream`` member, takes the union of what each
#: one emits, and holds it to this set, :data:`_PAINT_OPERATORS`,
#: :data:`_REFUSED_PATH_OPERATORS` and :data:`_REFUSED_STATE_OPERATORS`
#: together — so an operator the writer grows reds there rather than being
#: read by whichever of this module's branches happens to swallow it.
_PATH_OPERANDS = {"m": 2, "l": 2, "c": 6, "re": 4, "h": 0}

#: The PDF path-painting operators, and whether each one paints. ``n`` ends a
#: path without painting it, so it puts no mark on the paper and is not one.
#: The rest are PDF 1.7 §8.5.3's full set, so a painted path cannot reach this
#: reader as an operator it has no opinion about.
_PAINT_OPERATORS = {
    "S": True,
    "s": True,
    "f": True,
    "F": True,
    "f*": True,
    "B": True,
    "B*": True,
    "b": True,
    "b*": True,
    "n": False,
}

#: The operators that construct a path but that this reader refuses to guess
#: at — see :data:`_PATH_OPERANDS`.
_REFUSED_PATH_OPERATORS = frozenset({"v", "y"})

#: The operators that would make this reader's answer **wrong** rather than
#: merely unfamiliar, and which it therefore refuses outright.
#:
#: Every other token it does not recognise is passed over by clearing the
#: operand stack, which is why ``v``, ``y``, a starved operand and an unknown
#: token between coordinates all end in a refusal anyway. These four are
#: refused because each one either moves the coordinate system the operands are
#: read in or paints a mark that is not a path at all, so tolerating one means
#: answering with the **wrong** number instead of a missing one.
#:
#: The pass-over is **not** safe for every token outside this set, and this
#: comment used to claim it was ("every other token only sets state"). Two
#: measured counter-examples, both *wrong* rather than short: ``W`` clips, so
#: ``q 0 0 5 5 re W n 10 10 20 20 re f Q`` is read as the **unclipped**
#: (10,10)–(30,30) box; and ``gs`` can set ``/ca 0`` or an ``/SMask``, so an
#: **invisible** mark is reported as a mark. Neither has a consequence today,
#: and the reason is a binding rather than luck: the vocabulary guard in
#: ``tests/test_book_difficulty_dots.py`` holds the writer's measured emission
#: set *equal* to ``WRITER_OPERATORS_RECORDED``, which contains neither, so the
#: day the writer can emit one that cell reds before any corpus is read
#: (MUT-20 dies on exactly that equality). They are therefore deliberately
#: **not** added here: refusing an operator no writer in reach can emit buys
#: nothing and costs a refusal nothing measures.
#:
#: Measured before this set existed, which is why it exists: a
#: ``10 10 20 20 re f`` under ``2 0 0 2 0 0 cm`` read its *untransformed* box,
#: bit-identical to the same rect with no ``cm`` at all; ``/Im0 Do`` and
#: ``/Sh0 sh`` each read **0 marks and said nothing**.
#:
#: * ``cm`` concatenates a transform onto the CTM. A non-uniform one prints a
#:   path-space circle as an ellipse (a false round mark) or a path-space
#:   ellipse as a circle — a **missed** round mark, which is the direction the
#:   no-round-mark-on-the-book's-own-sheets accounting depends on.
#: * ``Do`` paints an external object, form or image, whose own marks live in a
#:   stream this reader is never handed.
#: * ``sh`` paints a shading, which has no path to measure.
#: * ``BI`` opens an inline image, whose data is not tokens at all.
#:
#: ``q`` and ``Q`` are deliberately **not** here, and that is an argument
#: rather than an omission. The argument does not need an "in between"
#: qualifier: ``cm`` is refused at **any** position in the stream, and ``cm``
#: is PDF's only in-stream CTM operator, so for every stream this reader
#: finishes the CTM is provably the identity from the first token to the last —
#: a saved and restored graphics state can therefore move nothing. The three
#: other routes by which an operand could land somewhere else are each refused
#: above as well: a Form XObject's ``/Matrix`` (reached only by ``Do``), an
#: inline image's unit-square map (``BI``), and a shading (``sh``). So refusing
#: ``cm`` closes the ``q``/``Q`` dependency outright, instead of this reader
#: asserting the writer's absence of them — and the non-refusal is load-bearing
#: rather than merely safe: adding ``q``/``Q`` to this set is KILLED by
#: ``test_an_operator_the_reader_would_misread_is_refused_not_ignored``
#: (MUT-25), at that cell's names-its-own-operator assertion rather than at its
#: ``q``/``Q`` box control — ``q`` refused makes the ``Do`` row raise on its
#: own ``q``, which the row then reports as not being its control.
#:
#: Bound to the writer's own **measured** emission set, not to this comment, by
#: ``tests/test_book_difficulty_dots.py``'s
#: ``test_the_readers_vocabulary_covers_every_operator_the_writer_emits``,
#: which drives every public ``ContentStream`` member and reds if the writer
#: grows an operator this reader would refuse — or one it would pass over
#: without that having been recorded (ADR-0039/R2).
_REFUSED_STATE_OPERATORS = frozenset({"cm", "Do", "sh", "BI"})

#: How many straight segments one cubic Bézier is flattened into before its
#: box and its enclosed area are measured.
#:
#: 32, and what it costs is **measured** rather than assumed. A circle written
#: by ``ContentStream.round_mark`` is four cubics; flattened at 32 segments
#: each its ``fill`` reads 0.999859, and at 256 — eight times as fine, where
#: the number has converged to five places — 1.000255. So the flattening's own
#: error is **3.96e-4 of the ratio, 0.33 % of**
#: :data:`ROUND_FILL_TOLERANCE`, and it points the ratio *down*, towards the
#: cautious side. The figures are re-derived, at three segment counts, by
#: ``tests/test_book_difficulty_dots.py``'s
#: ``test_the_flattening_costs_far_less_than_the_tolerance_it_is_read_against``.
#:
#: A circle's **box** does not depend on this number at all: each quadrant arc
#: of a Bézier circle has its extremes at its own endpoints, which every
#: flattening includes exactly.
_BEZIER_SEGMENTS = 32


class StreamShapeError(Exception):
    """A content stream carried a shape this reader cannot analyse.

    ADR-0039/R2: an unanalysable shape is a FAILURE and never a silent pass.
    Raised rather than skipped, because a subpath quietly dropped is a round
    mark quietly unaccounted for.
    """


@dataclass(frozen=True)
class StreamMark:
    """One painted subpath of a content stream, in the stream's own domain.

    **PDF user-space points, y counted up from the page's bottom edge** — the
    operands as the stream writes them, converted by nothing. That is the
    *stated boundary* of the shape and not an ink extent: see this section's
    header for why the two are different instruments.

    Attributes:
        x0: The subpath's smallest x.
        y0: Its smallest y.
        x1: Its largest x.
        y1: Its largest y.
        area: The absolute area its outline encloses, by the shoelace formula
            over the subpath flattened to straight segments. Signed area is
            deliberately not kept: a path's winding direction is how a viewer
            decides what is a hole, and this reader measures one subpath at a
            time and claims nothing about a composite.
        paint: The painting operator that painted it.
    """

    x0: float
    y0: float
    x1: float
    y1: float
    area: float
    paint: str

    @property
    def box(self) -> tuple[float, float, float, float]:
        """``(x0, y0, x1, y1)``, in points."""
        return (self.x0, self.y0, self.x1, self.y1)

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0

    @property
    def is_degenerate(self) -> bool:
        """Whether the subpath has no extent on one axis at all.

        An axis-aligned rule is exactly that — ``m``/``l``/``S`` between two
        points of the same y — and it is the commonest subpath on an interior
        page. It encloses nothing, so neither :attr:`aspect` nor :attr:`fill`
        is a number about it, and both refuse rather than return one. A sweep
        looking for the page's *closest* thing to a round mark has to skip
        this population and say that it did.
        """
        return self.width <= 0 or self.height <= 0

    @property
    def aspect(self) -> float:
        """The box's width over its height: 1.0 for a square footprint.

        Raises:
            StreamShapeError: the subpath is :attr:`is_degenerate`.
        """
        if self.is_degenerate:
            raise StreamShapeError(
                f"a subpath of {self.width} x {self.height} pt has no aspect: "
                "it has no extent on one axis"
            )
        return self.width / self.height

    @property
    def fill(self) -> float:
        """The enclosed area over an inscribed ellipse's: 1.0 for a circle.

        The same ratio :attr:`InkRegion.fill` is, over the same inscribed
        ellipse — and over a different measurement of "how much is inside".
        :class:`InkRegion` counts dark pixels, which is why a *stroked* ring
        reads far below 1 there; this counts the area the outline encloses,
        which for the same ring is a full disc. The vector reading is
        therefore **wider** on a hollow mark and the raster reading wider on a
        mark that is not a path at all (a typed dingbat). Each difference has
        a control in ``tests/test_book_difficulty_dots.py``'s
        ``TestDifficultyDots_TheVectorArmReadsTheStream``.

        Raises:
            StreamShapeError: the subpath is :attr:`is_degenerate`.
        """
        if self.is_degenerate:
            raise StreamShapeError(
                f"a subpath of {self.width} x {self.height} pt has no fill "
                "ratio: an inscribed ellipse of it has no area"
            )
        return self.area / (math.pi / 4 * self.width * self.height)

    @property
    def is_round(self) -> bool:
        """Whether this subpath is a round mark, by the same two tolerances."""
        if self.is_degenerate:
            return False
        return (
            abs(self.aspect - 1.0) <= ROUND_ASPECT_TOLERANCE
            and abs(self.fill - 1.0) <= ROUND_FILL_TOLERANCE
        )


def _without_strings(stream: str) -> str:
    """``stream`` with every literal string replaced by a space.

    A ``(…) Tj`` operand is text, so an operand that happens to read ``0 0 m``
    is a word on the page and not a path. Written here rather than imported
    from ``tests/helpers/pdf_vector.py`` for the reason this module imports no
    ``nonogram``: it is the independent second reader, and a shared scanner
    would make the two one.
    """
    return re.sub(r"\((?:\\.|[^()\\])*\)", " ", stream)


def _flatten(points: Sequence[tuple[float, float]]) -> list[tuple[float, float]]:
    """One cubic Bézier's four control points as :data:`_BEZIER_SEGMENTS` + 1 points."""
    (x0, y0), (x1, y1), (x2, y2), (x3, y3) = points
    out = []
    for step in range(_BEZIER_SEGMENTS + 1):
        t = step / _BEZIER_SEGMENTS
        u = 1.0 - t
        out.append(
            (
                u * u * u * x0 + 3 * u * u * t * x1 + 3 * u * t * t * x2 + t * t * t * x3,
                u * u * u * y0 + 3 * u * u * t * y1 + 3 * u * t * t * y2 + t * t * t * y3,
            )
        )
    return out


def _shoelace(points: Sequence[tuple[float, float]]) -> float:
    """The absolute area the closed polygon through ``points`` encloses."""
    total = 0.0
    for index in range(len(points)):
        x0, y0 = points[index]
        x1, y1 = points[(index + 1) % len(points)]
        total += x0 * y1 - x1 * y0
    return abs(total) / 2.0


def _mark(points: Sequence[tuple[float, float]], paint: str) -> StreamMark:
    xs = [x for x, _ in points]
    ys = [y for _, y in points]
    return StreamMark(
        x0=min(xs),
        y0=min(ys),
        x1=max(xs),
        y1=max(ys),
        area=_shoelace(points),
        paint=paint,
    )


def stream_marks(stream: str) -> list[StreamMark]:
    """Every **painted** subpath of ``stream``, in the order it was painted.

    The vector twin of :func:`ink_regions`, and the instrument the difficulty
    dots' vector arm accounts from (ADR-0042/R6: a claim about an interior
    page is asserted against the content stream).

    One :class:`StreamMark` per subpath, not per path: a path with two
    ``m``\\ s paints two shapes, and an accounting that reported the pair as
    one box would have a round mark hiding inside a rectangle's. Each subpath
    is flattened — a ``c`` into :data:`_BEZIER_SEGMENTS` straight segments, a
    ``re`` into its four corners — and then measured for a box and an enclosed
    area.

    **What it does not see.** Only paths. Type is not a path here: a
    ``chr(0x25CF)`` set as a glyph reaches the file as a string inside a text
    object, so it is invisible to this reader and visible to
    :func:`ink_regions` on a rendered page. That asymmetry is the vector arm's
    stated bound and it has a control.

    Args:
        stream: A decoded content stream — ``ContentStream.operators`` joined,
            or what ``tests/helpers/pdf_vector.content_streams`` reads back
            out of a written file.

    Raises:
        StreamShapeError: the stream paints a path built with an operator this
            reader does not understand, paints one with no subpath open, runs
            out of operands mid-operator, or uses one of
            :data:`_REFUSED_STATE_OPERATORS` — an operator that would leave the
            reading *wrong* rather than short. An unanalysable shape is a
            FAILURE (ADR-0039/R2).
    """
    tokens = _without_strings(stream).split()
    marks: list[StreamMark] = []
    subpaths: list[list[tuple[float, float]]] = []
    operands: list[float] = []
    for token in tokens:
        if _NUMBER.fullmatch(token):
            operands.append(float(token))
            continue
        if token in _REFUSED_PATH_OPERATORS:
            raise StreamShapeError(
                f"the stream builds a path with {token!r}, a shorthand Bezier "
                "this reader has never been shown and will not guess at: an "
                "unanalysable shape is a FAILURE (ADR-0039/R2)"
            )
        if token in _REFUSED_STATE_OPERATORS:
            raise StreamShapeError(
                f"the stream uses {token!r}, which this reader would have to "
                "ignore to carry on — and ignoring it does not lose a mark, it "
                "reports the wrong one: see _REFUSED_STATE_OPERATORS for the "
                "measurement. An unanalysable stream is a FAILURE "
                "(ADR-0039/R2)"
            )
        if token in _PATH_OPERANDS:
            wanted = _PATH_OPERANDS[token]
            if len(operands) < wanted:
                raise StreamShapeError(
                    f"{token!r} wants {wanted} operands and the stream offered "
                    f"{len(operands)}"
                )
            taken = operands[len(operands) - wanted :] if wanted else []
            operands = []
            if token == "m":
                subpaths.append([(taken[0], taken[1])])
            elif token == "re":
                x, y, width, height = taken
                subpaths.append(
                    [
                        (x, y),
                        (x + width, y),
                        (x + width, y + height),
                        (x, y + height),
                    ]
                )
            elif token == "h":
                continue
            else:
                if not subpaths:
                    raise StreamShapeError(
                        f"{token!r} extends a subpath that was never opened"
                    )
                if token == "l":
                    subpaths[-1].append((taken[0], taken[1]))
                else:
                    start = subpaths[-1][-1]
                    subpaths[-1].extend(
                        _flatten(
                            [
                                start,
                                (taken[0], taken[1]),
                                (taken[2], taken[3]),
                                (taken[4], taken[5]),
                            ]
                        )[1:]
                    )
            continue
        if token in _PAINT_OPERATORS:
            if _PAINT_OPERATORS[token]:
                if not subpaths:
                    raise StreamShapeError(
                        f"{token!r} paints a path with no subpath in it"
                    )
                marks.extend(_mark(points, token) for points in subpaths)
            subpaths = []
            operands = []
            continue
        operands = []
    return marks


def round_stream_marks(stream: str) -> list[StreamMark]:
    """Every subpath of ``stream`` that measures as a round mark.

    The whole vector instrument in one call, and the twin of
    :func:`round_marks`. The reading is in **points** and is of a *stated*
    boundary; :func:`round_marks` answers in device pixels and about ink.
    """
    return [mark for mark in stream_marks(stream) if mark.is_round]
