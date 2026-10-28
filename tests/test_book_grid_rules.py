"""The printed grid's three rule weights — CARD-227, ADR-0037/R2.

The owner's artifact "Puzzle page layout" (2026-10-14) asks for a three-weight
hierarchy: **0.3 pt** cell lines in grey, **0.8 pt** every fifth line on both
axes, **1.3 pt** outer border. The owner confirmed those figures on 2026-10-25
against the ×1.6-scaled 0.48 / 1.28 / 2.08 pt that stood in their place for
eight days — a scaling that was never a design opinion but an arithmetic
correction for a 300 DPI raster floor, which ADR-0042 removed by making the
interior a content stream.

Which claims read the stream, and which read a render
-----------------------------------------------------

ADR-0042/R6 says an interior claim is asserted against the content stream, not
a bitmap, and R6 gained a **second declared exemption** on 2026-10-25 for
exactly this card's shape. The discriminator is **what the assertion
concludes**, never a test's name or its file:

* "this line is 0.3 pt" is a number the generator *stated*, so it is read out
  of the stream (:class:`TestBookGridRules_HasThreeWeights`,
  :class:`TestBookGridRules_CellLinesAreLighterThanTheFifths`,
  :class:`TestBookGridRules_FifthLinesOnBothAxes`,
  :class:`TestBookGridRules_RaggedLastBand`). Recovering a stated number by
  counting dark pixels is the reconstruction R6 forbids;
* "these two resolve differently" and "this tone survives a change of
  resolution" are **device facts** — things the renderer does with a declared
  number — and the content stream is precisely what cannot test them. Those
  are read off a poppler render (:class:`TestBookGridRules_WeightsSurviveTheFloor`,
  :class:`TestBookGridRules_PointsNotPixels`), and they are the exempt pair.

:class:`TestBookGridRules_TheseWidthsNeverReachARasterGrid` reads neither: it
reads the *medium*, and then shows the refusal.

The two figures this card owed, now measured
--------------------------------------------

CARD-293 measured the **cell** line through poppler — 2 px at grey 89 at
300 DPI, 5 px at grey 89 at 1200 DPI. The 0.8 pt and 1.3 pt spans were
measured by nobody, and the card recorded that so it would not be mistaken for
evidence. They are measured here, through the same door
(:func:`tests.helpers.pdf_vector.rendered_page`, one scanline, run lengths):

====================  =========  =============  ==============  =====
weight                declared   300 DPI inked  1200 DPI inked  tone
====================  =========  =============  ==============  =====
cell line             0.3 pt     2 px           5 px            89
every fifth line      0.8 pt     4 px           14 px           0
outer border          1.3 pt     6 px           22 px           0
====================  =========  =============  ==============  =====

The inked span is wider than the declared width resolves to (0.3 pt is
1.25 px at 300 DPI, inked 2) because poppler antialiases a stroke that does not
land on a pixel boundary, and the same phase makes each span vary by one pixel
along a page. Every assertion below is written against that: the spans are held
**ordered and disjoint**, and the scaling is held as a ratio with a band, never
as an exact ×4. The ×4 that *is* exact is the declared width's own resolution
(1.25 px → 5 px), and that is asserted where it is exact.

This module names none of the eight render idioms
``meta/profiling/rank_durations.py`` greps for, so it does not join the frozen
render-heavy set — ``vector_puzzle_page`` is singular where the idiom is
``puzzle_pages``, and that is deliberate rather than lucky.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import replace
from pathlib import Path

import pytest
from PIL import ImageDraw, Image

from nonogram.admin import book_vector_draw
from nonogram.admin.book_page_spec import GRID_RULES
from nonogram.admin.book_pdf_generator import BookPDFGenerator, _stroke_drawing
from nonogram.admin.book_vector import write_vector_pdf
from nonogram.export.layout import (
    DPI,
    MAJOR_RULE_EVERY,
    RASTER_RULE_FLOOR_PX,
    GridRule,
    GridRules,
    Layout,
    compute_layout,
    rasterise_rule_px,
    refuse_rasterised_rule,
)
from tests.helpers import pdf_vector
from tests.helpers.book_corpus import corpus_book, puzzle

NO_POPPLER = (
    "poppler (pdftoppm) is not installed: AC-5's and AC-6's independent "
    "renderer is absent, and a device fact cannot be read off the stream "
    "that declared it"
)
needs_poppler = pytest.mark.skipif(pdf_vector.PDFTOPPM is None, reason=NO_POPPLER)

#: A right-hand interior page well inside the puzzle section, so the sheet
#: carries a parity and a frame exactly as a real puzzle page does.
A_PUZZLE_PAGE = 6

#: The owner's three figures, written out rather than imported from
#: ``book_page_spec``. Every assertion about *what the weights are* compares
#: against these literals, so the production constant and the artifact are two
#: statements that have to agree rather than one read twice.
CELL_PT = 0.3
FIFTH_PT = 0.8
BORDER_PT = 1.3
CELL_GREY = 0.35
HEAVY_GREY = 0.0

#: The ×1.6-scaled figures the card carried from 2026-10-17 to 2026-10-25.
#: Kept as the **discriminator** for AC-1's reading: a reading that could not
#: tell these from the owner's own would prove nothing about which landed, and
#: CARD-293's AC-4 demonstration rests on exactly that (it passed at 0.48 pt
#: and failed at 0.3 pt).
SCALED_RULES = GridRules(
    cell=GridRule(width_pt=0.48, grey=CELL_GREY),
    fifth=GridRule(width_pt=1.28, grey=HEAVY_GREY),
    border=GridRule(width_pt=2.08, grey=HEAVY_GREY),
)

#: ``round(255 * 0.35)``: the byte the 0.35 grey cell line renders as. Asserted
#: only where the claim is "the tone did not move between resolutions" — AC-2
#: asserts the *ordering*, not this byte.
CELL_GREY_BYTE = 89

#: A pixel lighter than this is paper, as the scanline reader below treats one.
#: Generous on purpose: a 0.3 pt stroke's outermost antialiased column is only
#: a few levels off white, and counting it as ink would make a 2 px rule read
#: as 4. 250 keeps the faintest *chosen* tone (89) and drops the fringe.
PAPER_LEVEL = 250


class Drawn:
    """One book puzzle page: its layout, its stream text, and its renders.

    Built once per shape and shared, because a 1200 DPI render of an
    8.5 × 11 in trim is 134 megapixels and takes about three seconds — the
    cost AC-6 exists to pay once rather than per assertion.
    """

    def __init__(
        self,
        label: str,
        columns: int,
        rows: int,
        depth: int,
        *,
        rules: GridRules | None = None,
        tmp_path: Path | None = None,
    ) -> None:
        self.label = label
        generator = BookPDFGenerator(corpus_book())
        row = puzzle("card227", columns, rows, depth, "medium", label)
        payload = BookPDFGenerator._payload(row)
        sizes = generator.cell_sizes([payload])
        spec = generator._puzzle_page_spec(A_PUZZLE_PAGE, sizes.get((columns, rows)))
        if rules is not None:
            spec = replace(spec, grid_rules=rules)
        self.layout = compute_layout(payload.row_clues, payload.column_clues, spec)
        stream = generator.vector_puzzle_page(payload, 1, A_PUZZLE_PAGE, sizes)
        if rules is not None:
            # The generator's own door builds the sheet from the book profile,
            # so an alternative set of weights is drawn through the same
            # writer on the same geometry instead of through a second one.
            stream = book_vector_draw.page_stream(self.layout)
            book_vector_draw.draw_ruled_grid(stream, self.layout)
            if self.layout.frame is not None:
                book_vector_draw.draw_frame(stream, self.layout.frame)
        self.pdf = write_vector_pdf([stream], 1).getvalue()
        (self.text,) = pdf_vector.content_streams(self.pdf)
        self._tmp_path = tmp_path
        self._renders: dict[int, object] = {}

    def render(self, dpi: int):
        """``self`` rasterised by poppler at ``dpi``, cached per resolution."""
        if dpi not in self._renders:
            directory = (self._tmp_path or Path(".")) / f"{self.label}-{dpi}"
            self._renders[dpi] = pdf_vector.rendered_page(
                self.pdf, dpi, out_dir=directory
            )
        return self._renders[dpi]

    # -- stream readings ---------------------------------------------------

    def stated_widths(self) -> list[float]:
        """Every ``w`` operand of the page, in order, in points."""
        return pdf_vector.stroke_widths(self.text)

    def stroke_tones(self) -> list[float]:
        """Every stroke tone (``G``) the page sets, in order."""
        return [level for level, operator in pdf_vector.tones(self.text) if operator == "G"]

    def lines_by_tier(self, vertical: bool) -> dict[str, list]:
        """One axis's grid lines grouped by the tier COMP-007 assigned them."""
        grouped: dict[str, list] = {"cell": [], "fifth": [], "border": []}
        source = self.layout.vertical_lines if vertical else self.layout.horizontal_lines
        for line in source:
            grouped[line.tier].append(line)
        return grouped

    # -- render readings ---------------------------------------------------

    def inked_spans(self, dpi: int) -> dict[str, Counter]:
        """Each tier's inked span and darkest level, off a poppler render.

        One scanline through the middle of the first row of cells, and the
        unbroken run of ink around each **vertical** line's own position —
        so a run is attributed to a tier by the position COMP-007 placed it
        at, not by its width. A reading that grouped runs *by width* would
        assume the answer it is asked for.

        Returns ``{tier: Counter({(span, darkest level): how many})}``.
        """
        page = self.render(dpi)
        layout = self.layout
        scale = dpi / layout.dpi
        middle = int(
            (layout.grid_top + (layout.grid_bottom - layout.grid_top) / layout.rows / 2)
            * scale
        )
        reach = max(2, int(layout.cell * scale / 2) - 1)
        found: dict[str, Counter] = {"cell": Counter(), "fifth": Counter(), "border": Counter()}
        scanline = page[middle].tolist()
        for line in layout.vertical_lines:
            centre = int(round(line.position * scale))
            span, darkest = 0, 255
            for offset in range(-reach, reach + 1):
                index = centre + offset
                if 0 <= index < len(scanline) and scanline[index] < PAPER_LEVEL:
                    span += 1
                    darkest = min(darkest, scanline[index])
                elif span and offset > 0:
                    break
                elif span:
                    span, darkest = 0, 255
            found[line.tier][(span, darkest)] += 1
        return found


@pytest.fixture(scope="module")
def hero(tmp_path_factory) -> Drawn:
    """A 20×20 at the 7.5 mm cap: the shape the owner's artifact was drawn on."""
    return Drawn("hero", 20, 20, 3, tmp_path=tmp_path_factory.mktemp("card227-hero"))


@pytest.fixture(scope="module")
def ragged(tmp_path_factory) -> Drawn:
    """AC-3's and AC-4's non-square grid whose sides are not multiples of five."""
    return Drawn("ragged", 22, 13, 3, tmp_path=tmp_path_factory.mktemp("card227-ragged"))


@pytest.fixture(scope="module")
def at_the_floor(tmp_path_factory) -> Drawn:
    """AC-5's page: a 30×30 at clue depth 10, which lands on NFR-008's floor.

    4.7625 mm, 0.012 mm above the 4.75 mm floor — the smallest cell this book
    admits without a stored override (``book_page_spec.FLOOR_MM``), which the
    registry already measures at exactly this shape.
    """
    return Drawn("floor", 30, 30, 10, tmp_path=tmp_path_factory.mktemp("card227-floor"))


# --------------------------------------------------------------------------
# AC-1 — three weights, read from the content stream
# --------------------------------------------------------------------------


class TestBookGridRules_HasThreeWeights:
    """AC-1: ordinary cell lines 0.3 pt, every fifth 0.8 pt, border 1.3 pt.

    **Read from the stream, not off ink** (ADR-0042/R6). The generator stated
    these numbers; recovering them by counting dark pixels would be the
    reconstruction R6 forbids, and CARD-293's AC-4 demonstrated the
    replacement — 168 lines of ink reading became 41 of stream reading, 4.1×
    smaller and strictly more exact.
    """

    def test_the_page_states_exactly_the_three_weights(self, hero: Drawn) -> None:
        stated = set(hero.stated_widths())

        assert stated == {CELL_PT, FIFTH_PT, BORDER_PT}, stated

    def test_each_weight_is_set_on_the_lines_that_carry_it(self, hero: Drawn) -> None:
        """The three weights, each against the lines of its own tier.

        A set equality says the three numbers are *present*; it does not say
        the border got the border's width. What is asserted instead is the
        **stroke order**, which is the part a set cannot see: the light cell
        lines are stroked first, all of them, so a heavy rule crossing one
        survives the overlap — and the cell weight is therefore the first
        width the page sets and is never set again after a heavy one.

        **Measured, and not what this test first assumed:** the page does
        *not* emit exactly three ``w`` operators. Every renderer's stroke
        order is keyed on ``GridLine.major``, which has two values, while
        there are now three weights — so inside the heavy half the border and
        the fifths interleave in COMP-007's own order and the width is re-set
        on each change (seven ``w`` operators on this 20x20, not three). That
        costs operators and nothing else: both heavy tiers are the same pure
        black, so no crossing looks different whichever of the two is on top.
        Keying the order on the tier would make it three, and that is a change
        to **stroke order** in four renderers rather than to a number, which
        G-2 keeps out of this card. Recorded here so the next reader of this
        page's operator count is not surprised by it.
        """
        stated = hero.stated_widths()
        tiers = hero.lines_by_tier(vertical=True)
        across = hero.lines_by_tier(vertical=False)

        assert set(stated) == {CELL_PT, FIFTH_PT, BORDER_PT}, stated
        # The ordering claim: the cell weight opens the page and never recurs.
        assert stated[0] == CELL_PT, stated
        assert CELL_PT not in stated[1:], stated
        # The measured count, asserted rather than left in the prose above —
        # seven, not three, and the docstring explains why. Pinned so the
        # claim in ``book_vector_draw.draw_grid_lines`` has a control.
        assert len(stated) == 7, stated
        # Every axis really does have lines of all three tiers, so none of the
        # three widths above is being set for an empty group.
        for axis, grouped in (("down", tiers), ("across", across)):
            assert all(grouped[tier] for tier in ("cell", "fifth", "border")), (
                axis,
                {tier: len(lines) for tier, lines in grouped.items()},
            )
        # And the border is the two far edges on each axis, which is the claim
        # a width count alone cannot make.
        assert [line.index for line in tiers["border"]] == [0, hero.layout.columns]
        assert [line.index for line in across["border"]] == [0, hero.layout.rows]

    def test_the_reading_discriminates_the_scaled_figures(
        self, tmp_path_factory
    ) -> None:
        """AC-1's control: the same reading on the ×1.6 figures reports them.

        **Without this the reading proves nothing about which figures landed.**
        CARD-293's AC-4 earned its place by passing at 0.48 pt and failing at
        0.3 pt, and this is that demonstration kept: the same writer, the same
        geometry, the same parser, the retired scaled weights — and the parser
        reports 0.48 / 1.28 / 2.08 and **not** the owner's figures.
        """
        scaled = Drawn(
            "scaled",
            20,
            20,
            3,
            rules=SCALED_RULES,
            tmp_path=tmp_path_factory.mktemp("card227-scaled"),
        )
        stated = set(scaled.stated_widths())

        assert stated == {0.48, 1.28, 2.08}, stated
        assert stated.isdisjoint({CELL_PT, FIFTH_PT, BORDER_PT}), stated

    def test_a_sheet_cannot_declare_two_weights_at_the_same_width(self) -> None:
        """"Exactly three rule weights" made structural, not remembered.

        ``GridRules`` is valid by construction and its widths are *strictly*
        increasing, so a hierarchy whose fifth line equals its cell line — two
        weights wearing three names — is a sheet that cannot be built rather
        than a page a renderer has to get right. Two near-misses, because one
        would not distinguish a guard from a coincidence: a tie at the bottom
        of the hierarchy and a tie at the top. A third case, an *inverted*
        hierarchy, is included because a guard written as "no two equal" would
        admit it.
        """
        for label, (cell, fifth, border) in (
            ("fifth ties the cell line", (0.3, 0.3, 1.3)),
            ("border ties the fifth", (0.3, 0.8, 0.8)),
            ("inverted", (1.3, 0.8, 0.3)),
        ):
            with pytest.raises(ValueError, match="three distinct rule weights"):
                GridRules(
                    cell=GridRule(width_pt=cell, grey=CELL_GREY),
                    fifth=GridRule(width_pt=fifth, grey=HEAVY_GREY),
                    border=GridRule(width_pt=border, grey=HEAVY_GREY),
                )
        # ... and the owner's own figures are admitted, so the guard is not
        # refusing every triple alike.
        assert GRID_RULES.cell.width_pt < GRID_RULES.fifth.width_pt
        assert GRID_RULES.fifth.width_pt < GRID_RULES.border.width_pt

    def test_a_weight_that_is_not_a_width_and_a_tone_is_refused(self) -> None:
        """``GridRule``'s own two guards, each with its near-miss.

        A width is a finite **positive** number of points — zero and a
        negative are not thin rules, they are a rule that is not there and a
        rule that is nonsense — and a tone is a content stream's one-number
        grey level, which lives in ``0.0..1.0`` and nowhere else. ``1.0``
        (white) is admitted on purpose: it is a legal operand and a sheet is
        entitled to it, so the guard is a range check and not a taste check.
        """
        for bad_width in (0.0, -0.3, float("inf")):
            with pytest.raises(ValueError, match="finite positive number of points"):
                GridRule(width_pt=bad_width, grey=CELL_GREY)
        for bad_grey in (-0.01, 1.01, float("nan")):
            with pytest.raises(ValueError, match="grey level in 0.0..1.0"):
                GridRule(width_pt=CELL_PT, grey=bad_grey)
        assert GridRule(width_pt=CELL_PT, grey=1.0).grey == 1.0

    def test_a_sheet_cannot_carry_something_that_is_not_a_set_of_rules(self) -> None:
        """``PageSpec``'s own door, which is where a bad sheet is caught.

        ``PageSpec`` refuses every spec that could not be laid out, so
        ``compute_layout`` never re-checks one; the weights join that contract
        rather than being validated by whichever renderer reached them first.
        A bare tuple of the three numbers is the near-miss worth naming — it
        is the shape a caller is most likely to reach for, and it carries no
        tones and no ordering at all.
        """
        from nonogram.export.layout import DEFAULT_PAGE_SPEC

        for bad in ((0.3, 0.8, 1.3), 0.3, "0.3/0.8/1.3"):
            with pytest.raises(ValueError, match="must be None or a GridRules"):
                replace(DEFAULT_PAGE_SPEC, grid_rules=bad)
        # None is admitted — it is what every sheet but the book's carries.
        assert replace(DEFAULT_PAGE_SPEC, grid_rules=None).grid_rules is None

    def test_the_weights_are_the_books_own_sheet_and_not_this_files_literals(
        self, hero: Drawn
    ) -> None:
        """The production constant and the artifact's figures, held together.

        Every other assertion here compares the stream against this module's
        literals. This one compares the literals against
        ``book_page_spec.GRID_RULES``, so the two statements of the owner's
        decision cannot drift apart silently: editing one without the other
        fails here rather than in whichever renderer noticed first.
        """
        assert (
            GRID_RULES.cell.width_pt,
            GRID_RULES.fifth.width_pt,
            GRID_RULES.border.width_pt,
        ) == (CELL_PT, FIFTH_PT, BORDER_PT)
        assert hero.layout.frame is not None
        assert hero.layout.frame.width_pt == BORDER_PT


# --------------------------------------------------------------------------
# AC-2 — the cell lines are grey, the fifths and the border darker
# --------------------------------------------------------------------------


class TestBookGridRules_CellLinesAreLighterThanTheFifths:
    """AC-2: an ink-value **ordering**, not one literal colour.

    The tone is 0.35 grey, which renders as grey 89. AC-2 asserts the ordering
    because that is what the design is after — light guidance under heavy
    structure — and a card that pinned the byte would fail the day the owner
    moved the tone a step without changing the hierarchy at all.
    """

    def test_the_page_sets_two_tones_and_the_lighter_one_is_the_cell_lines(
        self, hero: Drawn
    ) -> None:
        tones = hero.stroke_tones()
        cell_lines = hero.lines_by_tier(vertical=True)["cell"]
        heavy = hero.lines_by_tier(vertical=True)["fifth"]

        # Two tones on the page, not one: a grid drawn in a single ink has no
        # ordering to assert and would pass a one-sided comparison.
        assert len(set(tones)) == 2, tones
        # The lighter tone is set first, because the cell lines are stroked
        # first — so "lighter" and "the cell lines' own" are the same number.
        assert tones[0] == max(tones), tones
        assert tones[0] > tones[-1], tones
        # And that is what COMP-007 stated for those lines.
        assert {line.grey for line in cell_lines} == {tones[0]}
        assert {line.grey for line in heavy} == {tones[-1]}

    def test_the_cell_lines_are_grey_and_the_heavy_rules_are_the_one_ink(
        self, hero: Drawn
    ) -> None:
        """Grey, not black — the literal word in the owner's artifact.

        The heavy rules are held against ``book_vector_draw.INK_GREY``, the
        constant derived from the raster renderers' own ``png.INK``, so the two
        media cannot disagree about what ink is while the cell lines sit above
        it.
        """
        tones = set(hero.stroke_tones())

        assert CELL_GREY in tones and CELL_GREY > 0.0
        assert book_vector_draw.INK_GREY in tones
        assert CELL_GREY > book_vector_draw.INK_GREY

    def test_a_grid_whose_cell_lines_are_not_lighter_cannot_be_built(self) -> None:
        """The negative control, and the mechanism that makes AC-2 structural.

        ``GridRules`` is valid by construction, so the ordering is not a thing
        a renderer remembers to honour — it is a thing a sheet cannot express
        otherwise. Two near-misses, because one would not distinguish a guard
        from a coincidence: a cell line in **pure black** (the retired wording)
        and a cell line merely **no lighter** than the fifths.
        """
        with pytest.raises(ValueError, match="grey, not pure black"):
            GridRules(
                cell=GridRule(width_pt=CELL_PT, grey=0.0),
                fifth=GridRule(width_pt=FIFTH_PT, grey=0.0),
                border=GridRule(width_pt=BORDER_PT, grey=0.0),
            )
        with pytest.raises(ValueError, match="lighter in ink"):
            GridRules(
                cell=GridRule(width_pt=CELL_PT, grey=0.2),
                fifth=GridRule(width_pt=FIFTH_PT, grey=0.4),
                border=GridRule(width_pt=BORDER_PT, grey=0.4),
            )
        # ... and the real figures pass it, so the guard is not refusing
        # everything alike.
        assert GridRules(
            cell=GridRule(width_pt=CELL_PT, grey=CELL_GREY),
            fifth=GridRule(width_pt=FIFTH_PT, grey=HEAVY_GREY),
            border=GridRule(width_pt=BORDER_PT, grey=HEAVY_GREY),
        ) == GRID_RULES


# --------------------------------------------------------------------------
# AC-3 — the every-fifth rule runs on both axes, counted from the border
# --------------------------------------------------------------------------


class TestBookGridRules_FifthLinesOnBothAxes:
    """AC-3: rows and columns independently, each counting from its own border."""

    def test_each_axis_counts_its_own_fifths_from_its_own_border(
        self, ragged: Drawn
    ) -> None:
        """A 22 × 13 grid: 5/10/15/20 down the page and 5/10 across it.

        The two axes have **different** fifth sets, which is the whole of
        "independently": a layout that counted one axis's boundaries on the
        other would put a fifth at 15 across a 13-row grid, where there is no
        boundary 15 at all.
        """
        down = ragged.lines_by_tier(vertical=True)
        across = ragged.lines_by_tier(vertical=False)

        assert [line.index for line in down["fifth"]] == [5, 10, 15, 20]
        assert [line.index for line in across["fifth"]] == [5, 10]
        assert [line.index for line in down["fifth"]] != [
            line.index for line in across["fifth"]
        ]
        # Every fifth really is a multiple of five counted from the near edge,
        # and no cell line is.
        for grouped in (down, across):
            assert all(line.index % MAJOR_RULE_EVERY == 0 for line in grouped["fifth"])
            assert not any(
                line.index % MAJOR_RULE_EVERY == 0 for line in grouped["cell"]
            )

    def test_the_stream_strokes_both_axes_at_the_fifth_weight(
        self, ragged: Drawn
    ) -> None:
        """The stream half: 0.8 pt is really set, and on lines of both axes.

        Read out of the written PDF rather than off the ``Layout`` alone,
        because "COMP-007 tiered it" and "the page was stroked at it" are two
        claims and the card's AC is the second.
        """
        stated = ragged.stated_widths()
        verticals, horizontals = _strokes_by_axis(ragged)

        assert FIFTH_PT in stated, stated
        assert {width for _position, width in verticals} == {
            CELL_PT,
            FIFTH_PT,
            BORDER_PT,
        }
        assert {width for _position, width in horizontals} == {
            CELL_PT,
            FIFTH_PT,
            BORDER_PT,
        }
        # Four fifths down the page and two across it, as the indices above say.
        assert sum(1 for _p, w in verticals if w == FIFTH_PT) == 4
        assert sum(1 for _p, w in horizontals if w == FIFTH_PT) == 2


# --------------------------------------------------------------------------
# AC-4 — a side that is not a multiple of five
# --------------------------------------------------------------------------


class TestBookGridRules_RaggedLastBand:
    """AC-4: the last band is short and the border is still 1.3 pt.

    No half-weight line at the edge. The failure this forbids is a border that
    loses its weight to the every-fifth tier (or the other way round) on a
    grid whose side happens to divide by five — which is why
    ``_rule_tier`` tests the two far edges **first**, with no fallthrough.
    """

    def test_the_last_band_is_short_and_the_border_keeps_its_weight(
        self, ragged: Drawn
    ) -> None:
        down = ragged.lines_by_tier(vertical=True)
        verticals, _horizontals = _strokes_by_axis(ragged)
        positions = {line.index: line.position for line in ragged.layout.vertical_lines}

        # The last full band is 15 → 20 and the ragged one 20 → 22: shorter,
        # measured, not assumed.
        full = positions[20] - positions[15]
        short = positions[22] - positions[20]
        assert 0 < short < full, (short, full)
        # The border is the far edge and nothing else, at the border weight.
        assert [line.index for line in down["border"]] == [0, 22]
        edge = {width for position, width in verticals if position in (
            _points(positions[0], ragged), _points(positions[22], ragged)
        )}
        assert edge == {BORDER_PT}, edge
        # No weight on the page but the three, so nothing "half" exists to be
        # the edge's.
        assert set(ragged.stated_widths()) == {CELL_PT, FIFTH_PT, BORDER_PT}

    def test_a_side_that_divides_by_five_still_gets_a_border(
        self, hero: Drawn
    ) -> None:
        """The other half of the edge case, and the one that is easy to lose.

        A 20-wide grid's far boundary is index 20, which **is** a multiple of
        five. Tiered by the modulo alone it would be a fifth line, and the
        page would close on a 0.8 pt edge instead of a 1.3 pt one. The 22-wide
        case above cannot see that: 22 is not a multiple of five, so it passes
        under either rule.
        """
        down = hero.lines_by_tier(vertical=True)

        assert hero.layout.columns % MAJOR_RULE_EVERY == 0
        assert [line.index for line in down["border"]] == [0, 20]
        assert 20 not in [line.index for line in down["fifth"]]


# --------------------------------------------------------------------------
# AC-5 — the smallest cell the book admits (render; ADR-0042/R6 exemption)
# --------------------------------------------------------------------------


class TestBookGridRules_WeightsSurviveTheFloor:
    """AC-5: at NFR-008's 4.75 mm floor the three weights are still distinct.

    **Re-expressed from the raster version**, which said "each is at least one
    pixel and no two round to the same width". Pixel rounding is not how a
    content stream works, and that phrasing would now assert a property of
    whichever renderer the test happened to use.

    So the claim has two halves and they are read in two places, because they
    conclude two different things. That the *declared* widths are distinct and
    ordered is a fact about the document: read from the stream. That they
    *resolve* differently on a device — the hierarchy a solver actually sees —
    is a fact about the renderer: read from a render, which is R6's second
    declared exemption.
    """

    def test_the_declared_widths_are_still_three_and_ordered(
        self, at_the_floor: Drawn
    ) -> None:
        stated = at_the_floor.stated_widths()

        assert at_the_floor.layout.page is not None
        assert at_the_floor.layout.page.cell_mm == pytest.approx(4.7625, abs=5e-4)
        assert set(stated) == {CELL_PT, FIFTH_PT, BORDER_PT}, stated
        assert stated[0] == CELL_PT, stated
        assert CELL_PT < FIFTH_PT < BORDER_PT

    @needs_poppler
    def test_the_hierarchy_is_visible_at_the_floor(self, at_the_floor: Drawn) -> None:
        """The device half: the three weights ink three disjoint, ordered spans.

        Measured at 300 DPI on the smallest cell the book admits — 2 / 4 / 6
        device pixels, with the cell lines at grey 89 under pure-black fifths
        and border. Disjoint rather than merely unequal, because "no two round
        to the same width" is the property the raster phrasing was after and it
        survives the re-expression; ordered, because a hierarchy that inverted
        would satisfy disjointness and look wrong.
        """
        spans = at_the_floor.inked_spans(300)
        widths = {tier: {span for span, _dark in found} for tier, found in spans.items()}

        assert all(widths[tier] for tier in ("cell", "fifth", "border")), widths
        assert max(widths["cell"]) < min(widths["fifth"]), widths
        assert max(widths["fifth"]) < min(widths["border"]), widths
        # The light grey cell grid under heavier, darker structure.
        assert {dark for _span, dark in spans["cell"]} == {CELL_GREY_BYTE}
        assert max(dark for _span, dark in spans["fifth"]) < CELL_GREY_BYTE


# --------------------------------------------------------------------------
# AC-6 — points, not pixels (render; ADR-0042/R6 exemption)
# --------------------------------------------------------------------------


class TestBookGridRules_PointsNotPixels:
    """AC-6: the same page at 300 and 1200 DPI — the sharpest control here.

    **This is the property that made the owner's figures available at all.**
    The ×1.6 scaling existed because a rasteriser chooses an integer pixel
    count per stroke and 0.3 pt rounds to one pixel at 300 DPI. A renderer
    handed a *declared* width does not choose: it resolves the width at
    whatever resolution it runs. A card that shipped these widths without this
    control would have no evidence that the thing which made them safe is
    true.

    Both arms are measured, as CARD-293 measured them for the cell line: the
    span scales with the resolution and the **tone does not move**.
    """

    @needs_poppler
    def test_each_weights_span_scales_with_the_resolution(self, hero: Drawn) -> None:
        """The span the renderer inks **brackets** the declared width, at both.

        **This is the form the claim survived in, and the ratio form is the
        one it did not.** A span-to-span ratio looked like the obvious reading
        of "the pixel width scales with the resolution", and measuring it
        showed why it is weak: the cell line goes 2 px to 5 px, a ratio of
        **2.5** against the resolution's 4, because a declared stroke's
        antialiased fringe is about a pixel at each end whatever the
        resolution and so is a far larger share of a 1.25 px rule than of a
        5 px one. A band loose enough to admit 2.5 would admit almost
        anything.

        So each span is held against the width the renderer was actually
        asked for -- ``declared <= span <= declared + 2``, the fringe being at
        most one pixel at each end -- which is tighter at **both**
        resolutions than any ratio between them, and says the thing AC-6 is
        for: the renderer resolved the declared width at the resolution it ran
        at. The monotone arm is kept beside it, because a bracket that held at
        two resolutions without the span moving would be a different page.
        """
        for dpi in (300, 1200):
            spans = hero.inked_spans(dpi)
            for tier, points in (
                ("cell", CELL_PT),
                ("fifth", FIFTH_PT),
                ("border", BORDER_PT),
            ):
                declared = points * dpi / 72
                assert spans[tier], (tier, dpi)
                for span, _dark in spans[tier]:
                    assert declared <= span <= declared + 2, (
                        tier,
                        dpi,
                        declared,
                        span,
                    )

        coarse = hero.inked_spans(300)
        fine = hero.inked_spans(1200)
        for tier in ("cell", "fifth", "border"):
            low = max(span for span, _dark in coarse[tier])
            high = max(span for span, _dark in fine[tier])
            assert high > low * 2, (tier, low, high)

    @needs_poppler
    def test_the_tone_is_identical_at_both_resolutions(self, hero: Drawn) -> None:
        """The half that would be easy to leave out, and the one 7 of 17 reviews
        were about: a lighter line that goes lighter still on a finer device is
        a line that drops out."""
        coarse = hero.inked_spans(300)
        fine = hero.inked_spans(1200)

        for tier in ("cell", "fifth", "border"):
            assert {dark for _span, dark in coarse[tier]} == {
                dark for _span, dark in fine[tier]
            }, tier
        assert {dark for _span, dark in coarse["cell"]} == {CELL_GREY_BYTE}

    def test_the_declared_width_resolves_exactly_four_times_as_fine(self) -> None:
        """The ×4 that **is** exact, stated where it is exact.

        The stream states 0.3 pt and nothing else; the device count is the
        renderer's arithmetic on that one number, and four times the
        resolution is four times the count — 1.25 px at 300 DPI, 5 px at 1200.
        No ink is read here, because no ink is claimed: this is the document's
        property, and the two tests above are the device's.
        """
        for points in (CELL_PT, FIFTH_PT, BORDER_PT):
            coarse = points * 300 / 72
            fine = points * 1200 / 72
            assert fine == pytest.approx(coarse * 4)
        assert CELL_PT * 300 / 72 == pytest.approx(1.25)
        assert CELL_PT * 1200 / 72 == pytest.approx(5.0)

    @needs_poppler
    def test_the_page_carries_no_bitmap_at_either_resolution(self, hero: Drawn) -> None:
        """The premise the two exemptions rest on (ADR-0042/R1).

        A render is only evidence about a *declared* width if the page declared
        one. If the page were an image XObject, poppler would be resampling a
        bitmap and the scaling above would be a fact about interpolation.
        """
        assert b"/Image" not in hero.pdf
        # One stroked path per ruled line, so the grid is operators and not a
        # picture of operators. Every boundary on both axes, and at least that
        # many: the frame and the band add their own marks.
        assert pdf_vector.operator_tally(hero.text)["S"] >= (
            hero.layout.columns + hero.layout.rows + 2
        ), pdf_vector.operator_tally(hero.text)


# --------------------------------------------------------------------------
# AC-7 — the refused configuration stays refused
# --------------------------------------------------------------------------


class TestBookGridRules_TheseWidthsNeverReachARasterGrid:
    """AC-7: these weights onto a **raster** surface is refused.

    **The card's one genuinely new claim**, and per ADR-0039/R1 it needs a
    control that CAN fail. The mutant the card names is "let a raster page take
    the 0.3 pt figure", and the controls below red on exactly that.

    Why the claim is not decoration: through a rasteriser at 300 DPI these
    figures round to **1 / 3 / 5 px** — a one-pixel grey cell grid, which is
    what ADR-0037/R2's 2026-10-17 amendment refused on the evidence of 7 of 17
    reviews of the 450-puzzle book complaining of faint grid lines. Shipping
    them onto a bitmap would quietly re-open the one complaint ADR-0037 exists
    to close.

    **What this does and does not reach, declared rather than implied.** Two
    doors are held: the one a raster generator must come through to turn a
    declared width into pixels (:func:`rasterise_rule_px`), and the one raster
    grid stroker in the book generator (``_stroke_drawing``). What is *not*
    closed here is ``png._draw_grid``, the other raster stroker — it reads a
    line's device width and ignores the declared one, so these figures cannot
    reach it today, but nothing stops a later card making it read them.
    CARD-298 is where the raster exceptions are declared and guarded, and that
    is where this bound closes.
    """

    def test_the_raster_door_refuses_the_cell_line_at_300_dpi(self) -> None:
        with pytest.raises(ValueError, match="cannot be rasterised"):
            rasterise_rule_px(CELL_PT, 300)

    def test_the_raster_door_is_a_device_floor_and_not_a_blanket_refusal(self) -> None:
        """The **negative** control: the same figure at 1200 DPI is admitted.

        A guard that refused the owner's weights everywhere would pass the test
        above and mean something quite different — "these widths are forbidden"
        rather than "these widths need a device that can hold them". 0.3 pt is
        5 px at 1200 DPI, over the floor, and the door lets it through.
        """
        assert rasterise_rule_px(CELL_PT, 1200) == 5
        assert rasterise_rule_px(FIFTH_PT, 300) == 3
        assert rasterise_rule_px(BORDER_PT, 300) == 5
        assert RASTER_RULE_FLOOR_PX == 2

    def test_the_stroke_guard_refuses_a_declared_weight_and_admits_the_device_rule(
        self, hero: Drawn
    ) -> None:
        """The guard the raster stroker calls, on both sides of its boundary.

        Positive: a rule about to be stroked at the declared figure's own
        device count (1 px for 0.3 pt at 300 DPI) is refused. Negative, and the
        near-miss that matters: the book's **real** raster width for the same
        declared line — COMP-007's proportional 3 px — is admitted, so a book
        page drawn the way the raster renderers really draw it is not caught.
        """
        with pytest.raises(ValueError, match="declared physical"):
            refuse_rasterised_rule(1, CELL_PT, dpi=300)
        refuse_rasterised_rule(hero.layout.thin_rule, CELL_PT, dpi=300)
        refuse_rasterised_rule(hero.layout.thick_rule, BORDER_PT, dpi=300)
        # A width that is not whole pixels at all — a physical measurement that
        # never went through the door — is refused too, on every sheet.
        with pytest.raises(ValueError, match="whole device pixels"):
            refuse_rasterised_rule(1.25, None)
        # ... and a line the sheet declares nothing for is left alone, which is
        # every sheet but the book's (CON-019).
        refuse_rasterised_rule(3, None)

    def test_the_book_raster_stroker_draws_the_book_page_and_refuses_the_mutant(
        self, hero: Drawn
    ) -> None:
        """End to end, through the raster stroker the book really calls.

        The mutant the card names, built: every cell line's device width
        replaced by the 0.3 pt figure's own device count. ``_stroke_drawing``
        reds on it. The unmutated page — the same ``Layout``, whose lines carry
        the declared weights and COMP-007's device widths — draws, which is
        what keeps every raster page in the book byte-identical while these
        weights exist (G-5: no baseline moves in this card).
        """
        canvas = Image.new("RGB", (hero.layout.width, hero.layout.height), "white")
        _stroke_drawing(ImageDraw.Draw(canvas), hero.layout)

        mutant = replace(
            hero.layout,
            vertical_lines=tuple(
                replace(line, width=1) if line.tier == "cell" else line
                for line in hero.layout.vertical_lines
            ),
        )
        with pytest.raises(ValueError, match="declared physical"):
            _stroke_drawing(ImageDraw.Draw(canvas), mutant)

    def test_the_frame_is_guarded_too_and_not_only_the_grids_lines(
        self, hero: Drawn
    ) -> None:
        """The frame continues the border, so it is a grid rule and is guarded.

        **This arm exists because the guard has two call sites and a mutant
        that deleted only the second would otherwise survive.** The frame is
        stroked after the lines, from its own width, so a raster page that
        took the declared 1.3 pt figure for its frame while keeping the
        proportional width for its lines would be half the refused
        configuration and nothing above would see it.

        The mutant: a frame whose device width is the border figure's own
        device count (5 px for 1.3 pt at 300 DPI). The near-miss beside it:
        the frame as COMP-007 really builds it, 6 px, which draws.
        """
        canvas = Image.new("RGB", (hero.layout.width, hero.layout.height), "white")
        frame = hero.layout.frame
        assert frame is not None and frame.width_pt == BORDER_PT
        assert frame.width != rasterise_rule_px(BORDER_PT, DPI)

        mutant = replace(
            hero.layout, frame=replace(frame, width=rasterise_rule_px(BORDER_PT, DPI))
        )
        with pytest.raises(ValueError, match="declared physical"):
            _stroke_drawing(ImageDraw.Draw(canvas), mutant)

    def test_a_raster_sheet_carries_no_declared_weights_at_all(self) -> None:
        """The default spec — the CLI's and the web UI's — states none.

        CON-019: book geometry never changes those exports. The weights are a
        book ``PageSpec`` field, so a default-spec page cannot carry them and
        every line of it is left alone by the guard above.
        """
        layout = compute_layout(((3,), (1, 1)), ((1,), (1,), (2,)))

        assert all(line.width_pt is None for line in layout.grid_lines)
        assert all(line.grey is None for line in layout.grid_lines)
        assert layout.frame is None
        assert {line.width for line in layout.grid_lines} == {
            layout.thin_rule,
            layout.thick_rule,
        }
        for line in layout.grid_lines:
            refuse_rasterised_rule(line.width, line.width_pt, dpi=DPI)


# --------------------------------------------------------------------------
# Readers
# --------------------------------------------------------------------------


def _points(pixels: int, drawn: Drawn) -> float:
    """``pixels`` on ``drawn``'s sheet as the points its stream states."""
    return round(pixels * 72 / drawn.layout.dpi, 3)


def _strokes_by_axis(drawn: Drawn) -> tuple[list, list]:
    """``drawn``'s stroked lines as ``(position, width)``, split by axis.

    Parsed out of the written PDF: each ``m``/``l``/``S`` triple with its
    current ``w``. A vertical's position is its ``x`` and a horizontal's its
    ``y``, both in points as the stream states them — no conversion, because
    the comparison this feeds is a comparison of stated numbers.
    """
    import re

    number = r"-?\d+(?:\.\d+)?"
    verticals: list[tuple[float, float]] = []
    horizontals: list[tuple[float, float]] = []
    width = None
    for line in drawn.text.splitlines():
        stripped = line.strip()
        set_width = re.fullmatch(rf"({number}) w", stripped)
        if set_width:
            width = float(set_width.group(1))
            continue
        drawn_line = re.fullmatch(
            rf"({number}) ({number}) m ({number}) ({number}) l S", stripped
        )
        if not drawn_line:
            continue
        x1, y1, x2, _y2 = (float(group) for group in drawn_line.groups())
        assert width is not None, "a line was stroked before any width was set"
        if x1 == x2:
            verticals.append((x1, width))
        else:
            horizontals.append((y1, width))
    return verticals, horizontals
