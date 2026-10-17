"""CARD-228 — difficulty as three dots, filled by tier: one glyph the whole book reuses.

    AC-1  TestDifficultyDots_FilledCountIsTheTierRank
    AC-2  TestDifficultyDots_ReadsTheProjectsTierOrder
    AC-3  TestDifficultyDots_FilledAndOutlinedAreDistinguishable
    AC-4  TestDifficultyDots_HasExactlyOneDrawingSite
    AC-5  TestDifficultyDots_FitsTheSmallestHeader
    AC-6  TestDifficultyDots_UntieredDrawsNothing
          TestDifficultyDots_GeometryHoldsOverASeededCorpus (the invariants)

and CARD-241, which is AC-4 again by the one instrument that can hold it —
render the pages the book prints and measure the ink, rather than read the
source (its own acceptance criteria, in the order the card states them):

    AC-1  TestRoundMarkOnThePage_CatchesWhatTheWalkCannotSee
    AC-2  TestRoundMarkOnThePage_PassesOnTheRealBook
    AC-3  TestRoundMarkOnThePage_SameVerdictForEverySpelling
    AC-4  TestRoundMarkOnThePage_TheBoundaryIsMeasured
    AC-5  TestRoundMarkOnThePage_TheNamedLimitsListShrinksHonestly

and CARD-243, which is the other half of CARD-241's narrowing: that check read
ink at one hard threshold, grey 128, and the book prints its solved grid at
grey 160, so a difficulty dot in the book's own grey was not on the page at
all. It reads at two thresholds now, and what moved when it did is measured
rather than inherited:

    AC-1  TestRoundMarkOnThePage_SeesTheGreysTheBookPrints
    AC-2  TestRoundMarkOnThePage_PassesOnTheRealBook (extended: both
          thresholds, both margins, each tolerance's own room)
    AC-3  TestRoundMarkOnThePage_TheBoundaryIsMeasured (every shape re-run at
          both thresholds)
    AC-4  TestRoundMarkOnThePage_TheBoundListShrinksHonestly
    AC-5  the same class — MEASURED_MARK_BOUNDS is the residue, one row each
          with a control
    AC-6  meta/profiling/card-243-two-threshold-cost.md

What is under test, and in which half
-------------------------------------
The glyph is two halves, as ADR-0036/R2 requires: ``export/layout.py``'s
:func:`~nonogram.export.layout.difficulty_dots` measures *where* the circles
go (COMP-007 owns geometry), and ``admin/book_pdf_generator.py``'s
``_draw_difficulty_dots`` strokes them onto a page it is handed and is the one
place that resolves a stored tier into a rank on
:data:`~nonogram.admin.book_plan.TIERS`. This file tests both halves, and
wherever an acceptance criterion says "measured off the ink" it renders and
counts pixels rather than reading the geometry back.

Every claim here has a control
------------------------------
Three cards before this one failed review for a guard whose stated coverage
exceeded its mechanism, so each guard below is paired with a case it *does*
catch and a case it deliberately does not:

* AC-2's "the count and order come from ``TIERS``" is shown by shortening and
  by reversing the ladder and watching the glyph follow — not by a comment.
* AC-4's structural one-site assertion runs its ``ast`` walk against fabricated
  sources as well as against the real package
  (``_round_mark_sites`` and ``_draw_calls`` take their sources as an argument
  for exactly that reason, the way ``tests/test_cli.py``'s ``_outward_imports``
  does), and the set of Pillow methods it consults has a completeness test
  against Pillow's own API, so a method this project has not classified cannot
  slip past it. It guards **four** routes to a second dot glyph — an ellipse,
  an unused approximation method, a many-sided polygon, a typed dingbat — each
  with a control that fires, and
  :class:`TestDifficultyDots_HasExactlyOneDrawingSite`'s own docstring names
  the routes it cannot see (cycle 1, F-001, which planted three second glyphs
  that the first version of this guard let through).
* AC-5's "it fits" is paired with a box the function declines, so "fits" is a
  measurement and not a tautology.
"""

from __future__ import annotations

import ast
import inspect
import math
import random
from collections import Counter
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw

import nonogram
from nonogram import clues
from nonogram.admin import book_pdf_generator
from nonogram.admin.book_pdf_generator import (
    _MIN_BAND_FONT_RATIO,
    _SOLVED_GRID_GRAY,
    BookPDFGenerator,
    _band_font,
    _draw_difficulty_dots,
)
from nonogram.admin.book_plan import TIERS
from nonogram.difficulty import TIER_BANDS, Tier
from nonogram.export.layout import (
    DIFFICULTY_DOT_GAP_RATIO,
    DIFFICULTY_DOT_RATIO,
    DIFFICULTY_DOT_STROKE_RATIO,
    HEADER_BAND_MM,
    HEADER_FONT_MM,
    MIN_DIFFICULTY_DOT_MM,
    SOLVED_TILE_CAPACITIES,
    DifficultyDots,
    OrientationPolicy,
    PageParity,
    PageSpec,
    compute_packed_solved_layout,
    difficulty_dots,
    header_band,
)
from nonogram.export.png import BACKGROUND, INK
from tests.helpers import round_ink
from tests.helpers.book_corpus import BASELINE_PAGE_COUNT, baseline_puzzles, corpus_book
from tests.helpers.round_ink import (
    INK_LEVEL,
    MARK_LEVEL,
    MEASURED_LEVELS,
    ROUND_ASPECT_TOLERANCE,
    ROUND_FILL_TOLERANCE,
    InkRegion,
    ink_regions,
    mark_regions,
    round_marks,
)

# --------------------------------------------------------------------------
# What the card asks for, written out rather than imported
# --------------------------------------------------------------------------

#: The print resolution every book page is measured at, written out rather
#: than imported so this file's own statement of a physical size stays
#: independent of the module it checks.
DPI = 300

#: :data:`~nonogram.export.layout.MIN_DIFFICULTY_DOT_MM` in device pixels at
#: :data:`DPI`, restated here: a dot smaller than this is declined.
MIN_DOT_PX = round(MIN_DIFFICULTY_DOT_MM / 25.4 * DPI)


def _px(millimetres: float) -> int:
    """Millimetres at :data:`DPI`, this file's own conversion.

    Written out rather than imported from ``export.layout``'s private
    ``_mm_to_px`` for the same reason :data:`DPI` is: a physical size this
    file asserts should not be computed by the module it is checking.
    """
    return round(millimetres / 25.4 * DPI)

#: The smallest trim a book may be stored with
#: (``book_page_spec.MIN_TRIM_CM``), in millimetres, and the narrowest side
#: margin it may carry (``book_page_spec.MIN_SIDE_MARGIN_MM``) — written out,
#: as ``tests/test_book_interior_type_floor.py`` writes them out.
MIN_TRIM_MM = 100.0
MIN_SIDE_MARGIN_MM = 6.35
MIN_TRIM_GUTTER_MM = 9.5
KDP_TOP_BOTTOM_MM = 0.375 * 25.4

#: The band every book page reserves above a drawing (TERM-028), and the
#: book's cell cap and thinnest rule — the three ``PageSpec`` fields a
#: solution tile's own geometry depends on.
BAND_MM = 12.0
STANDARD_CELL_MM = 7.5
MIN_THIN_RULE_MM = 0.25


# --------------------------------------------------------------------------
# Rendering helpers: every "measured off the ink" claim goes through these
# --------------------------------------------------------------------------


def _render(stored_tier: object, box: tuple[int, int, int, int]) -> tuple[Image.Image, object]:
    """Draw ``stored_tier``'s dots in ``box`` on a white page just big enough.

    The canvas is two pixels larger than the box on every side, so ink that
    escaped the box has somewhere to land and can be seen escaping rather
    than being clipped away by the canvas edge.
    """
    left, top, right, bottom = box
    page = Image.new("RGB", (right + 3, bottom + 3), BACKGROUND)
    drawn = _draw_difficulty_dots(ImageDraw.Draw(page), stored_tier, left, top, right, bottom)
    return page, drawn


def _ink(page: Image.Image) -> np.ndarray:
    """``page``'s ink as a boolean mask, ``True`` where a pixel is not paper."""
    return np.any(np.asarray(page) != np.asarray(BACKGROUND, dtype=np.uint8), axis=2)


def _ink_box(mask: np.ndarray) -> tuple[int, int, int, int] | None:
    """The bounding box of every inked pixel in ``mask``, or ``None`` if blank."""
    rows = np.flatnonzero(mask.any(axis=1))
    columns = np.flatnonzero(mask.any(axis=0))
    if not rows.size or not columns.size:
        return None
    return int(columns[0]), int(rows[0]), int(columns[-1]), int(rows[-1])


def _is_solid(mask: np.ndarray, dot: tuple[int, int, int, int]) -> bool:
    """Whether ``dot``'s own middle row of pixels is ink all the way across.

    The one measurement that tells a filled dot from an outlined one without
    reading any geometry back out of the thing under test: an outlined circle
    is paper in the middle, a solid one is not.
    """
    left, top, right, bottom = dot
    middle = mask[(top + bottom) // 2, left : right + 1]
    return bool(middle.all())


def _left_run(mask: np.ndarray, dot: tuple[int, int, int, int]) -> int:
    """How many ink pixels the dot's middle row starts with — its ring, on the left."""
    left, top, right, bottom = dot
    middle = mask[(top + bottom) // 2, left : right + 1]
    run = 0
    while run < middle.size and middle[run]:
        run += 1
    return run


# --------------------------------------------------------------------------
# The smallest box any caller gives the glyph (AC-5)
# --------------------------------------------------------------------------


def _min_trim_spec(parity: PageParity = PageParity.ODD) -> PageSpec:
    """A square page at the smallest trim a book may be stored with."""
    return PageSpec(
        width_mm=MIN_TRIM_MM,
        height_mm=MIN_TRIM_MM,
        top_mm=KDP_TOP_BOTTOM_MM,
        bottom_mm=KDP_TOP_BOTTOM_MM,
        gutter_mm=MIN_TRIM_GUTTER_MM,
        outside_mm=MIN_SIDE_MARGIN_MM,
        band_mm=BAND_MM,
        orientation=OrientationPolicy.PORTRAIT_ONLY,
        cell_cap=STANDARD_CELL_MM,
        min_thin_rule_mm=MIN_THIN_RULE_MM,
        parity=parity,
    )


#: A 10x10 puzzle's clue sets, one run per line — the smallest grid CON-011
#: supports, which is what a packed solution page is allowed to hold.
_SMALL_CLUES = (((10,),) * 10, ((10,),) * 10)


def _solution_tile_bands() -> list[tuple[int, int, int, int]]:
    """Every solution tile's own band strip, at the smallest supported trim.

    A packed solved page reserves ``band_mm`` inside each tile rather than one
    band for the page, so a tile's header is the strip between its own usable
    top and the top of its own drawing — the box CARD-233's caller has to fit
    a number, a word and this glyph into, and the smallest box any of the four
    callers gives it.
    """
    spec = _min_trim_spec()
    boxes: list[tuple[int, int, int, int]] = []
    for capacity in SOLVED_TILE_CAPACITIES:
        packed = compute_packed_solved_layout([_SMALL_CLUES] * capacity, capacity, spec)
        assert packed is not None, f"the minimum trim cannot pack {capacity} small answers"
        for slot in packed.slots:
            page = slot.page
            assert page is not None
            boxes.append((page.usable_left, page.usable_top, page.usable_right, page.drawing_top - 1))
    return boxes


def _smallest_solution_tile_band() -> tuple[int, int, int, int]:
    """The narrowest of them — the one box AC-5 is actually about."""
    return min(_solution_tile_bands(), key=lambda box: (box[2] - box[0], box[3] - box[1]))


@pytest.fixture(scope="module")
def box() -> tuple[int, int, int, int]:
    """AC-5's box: the narrowest header any of the four callers gives the glyph."""
    return _smallest_solution_tile_band()


# --------------------------------------------------------------------------
# The seeded corpus every invariant is swept over
# --------------------------------------------------------------------------

#: The corpus seed, and the two floors it must clear — the number of cases it
#: holds, and the number of them that really produce a glyph. Both are
#: asserted inside the tests themselves, so neither the sweep nor the share of
#: it that exercises any geometry at all can silently shrink and keep passing.
#: The second floor is the load-bearing one: a corpus of 2100 boxes all of
#: which were declined as too small would satisfy the first and measure
#: nothing.
CORPUS_SEED = 228
CORPUS_MIN_CASES = 2100
CORPUS_MIN_GLYPHS = 1800


def _corpus() -> list[tuple[tuple[int, int, int, int], Tier]]:
    """Boxes a caller could plausibly hand the glyph, paired with each tier.

    Built by hand with stdlib :class:`random.Random` (this project carries no
    ``hypothesis``), spanning every box from one a hair above the minimum dot
    to a full page's band, at offsets that are not zero — a glyph measured
    only from the origin would hide every missing ``+ left``. Boxes too small
    for a legible dot are deliberately left in: the declines are a case the
    sweep has to tolerate, which is why the glyph count has its own floor.
    """
    rng = random.Random(CORPUS_SEED)
    cases: list[tuple[tuple[int, int, int, int], Tier]] = []
    for _ in range(700):
        left = rng.randrange(0, 2000)
        top = rng.randrange(0, 2000)
        width = rng.randrange(MIN_DOT_PX, 2400)
        height = rng.randrange(MIN_DOT_PX, 400)
        box = (left, top, left + width - 1, top + height - 1)
        for tier in TIERS:
            cases.append((box, tier))
    return cases


CORPUS = _corpus()


def _rank(tier: Tier) -> int:
    """``tier``'s 1-based rank on the project's own ladder."""
    return TIERS.index(tier) + 1


def _measured(box: tuple[int, int, int, int], tier: Tier) -> DifficultyDots | None:
    """The glyph the geometry half answers for ``tier`` in ``box``."""
    return difficulty_dots(*box, filled=_rank(tier), total=len(TIERS))


# ==========================================================================
# AC-1 — one dot per rank
# ==========================================================================


class TestDifficultyDots_FilledCountIsTheTierRank:
    """AC-1: the filled dots count the tier's rank; the row is the whole ladder."""

    BOX = (100, 50, 1099, 191)

    @pytest.mark.parametrize("tier", list(TIERS), ids=lambda tier: tier.value)
    def test_each_tier_fills_exactly_its_own_rank(self, tier: Tier) -> None:
        dots = _measured(self.BOX, tier)
        assert dots is not None
        assert dots.filled == TIERS.index(tier) + 1
        assert dots.total == len(TIERS)

    @pytest.mark.parametrize("tier", list(TIERS), ids=lambda tier: tier.value)
    def test_the_rank_is_measured_off_the_ink_not_read_back(self, tier: Tier) -> None:
        """The *drawn* glyph: count the dots whose middle is solid."""
        page, dots = _render(tier.value, self.BOX)
        assert dots is not None
        mask = _ink(page)
        solid = [index for index, dot in enumerate(dots.dots) if _is_solid(mask, dot)]
        assert solid == list(range(TIERS.index(tier) + 1))
        assert len(dots.dots) == len(TIERS)

    def test_the_total_never_varies_with_the_tier(self) -> None:
        """Three dots for every tier — the glyph says *n of three*, not *n*."""
        totals = {_measured(self.BOX, tier).total for tier in TIERS}  # type: ignore[union-attr]
        assert totals == {len(TIERS)}

    def test_only_which_dots_are_filled_changes_between_tiers(self) -> None:
        """A header's layout must not shift between an Easy puzzle and a Hard one."""
        glyphs = [_measured(self.BOX, tier) for tier in TIERS]
        assert all(glyph is not None for glyph in glyphs)
        assert len({glyph.dots for glyph in glyphs}) == 1  # type: ignore[union-attr]
        assert len({glyph.stroke for glyph in glyphs}) == 1  # type: ignore[union-attr]
        assert {glyph.filled for glyph in glyphs} == {  # type: ignore[union-attr]
            rank for rank in range(1, len(TIERS) + 1)
        }

    def test_the_rank_holds_for_every_box_of_the_corpus(self) -> None:
        measured = 0
        for box, tier in CORPUS:
            dots = _measured(box, tier)
            if dots is None:
                continue
            assert dots.filled == _rank(tier), (box, tier)
            assert dots.total == len(TIERS), (box, tier)
            measured += 1
        assert measured >= CORPUS_MIN_GLYPHS, (
            f"only {measured} of {len(CORPUS)} corpus cases produced a glyph; "
            "the sweep must not shrink below its own floor"
        )


# ==========================================================================
# AC-2 — one source of the order
# ==========================================================================


class TestDifficultyDots_ReadsTheProjectsTierOrder:
    """AC-2: the count and the order are ``book_plan.TIERS``, and nothing else.

    The assertions are *driven from* ``TIERS`` rather than from a literal
    three, and the two controls below shorten and reverse the ladder: a second
    list of tiers anywhere in the glyph's path would keep answering three dots
    in the old order and fail them.
    """

    BOX = (0, 0, 999, 141)

    def test_the_ladder_is_every_tier_the_project_has_exactly_once(self) -> None:
        """The completeness test for the set the glyph consults.

        ``TIERS`` is the only ordering the glyph reads, so this pins what it
        is: every member of :class:`~nonogram.difficulty.Tier`, once each, in
        one order. A tier added to the enum and forgotten here would make the
        glyph silently unable to grade it (see
        :meth:`test_a_tier_absent_from_the_ladder_draws_nothing`), so the
        failure belongs on this line rather than on a printed page.
        """
        assert tuple(TIERS) == tuple(Tier)
        assert len(set(TIERS)) == len(TIERS)

    def test_the_order_agrees_with_the_difficulty_scale_itself(self) -> None:
        """An independent second source of the same order (COMP-006's bands).

        ``TIERS`` is COMP-009's ordering and :data:`TIER_BANDS` is COMP-006's;
        the glyph's rank is only meaningful if they are the same order. Read
        off the score bands rather than re-deriving it from ``TIERS``, so a
        reordered ``TIERS`` fails here instead of printing a glyph that grades
        Hard as one dot.
        """
        by_band = sorted(TIERS, key=lambda tier: TIER_BANDS[tier][0])
        assert tuple(by_band) == tuple(TIERS)

    def test_the_drawn_total_is_the_length_of_the_ladder(self) -> None:
        for tier in TIERS:
            _, dots = _render(tier.value, self.BOX)
            assert dots is not None
            assert dots.total == len(TIERS)

    def test_a_shortened_ladder_shortens_the_glyph(self, monkeypatch) -> None:
        """Control, caught: two tiers on the ladder means two dots, not three.

        If the drawing half held its own list — or a literal ``3`` — the glyph
        would still draw three dots here and this would fail.
        """
        monkeypatch.setattr(book_pdf_generator, "TIERS", (Tier.EASY, Tier.HARD))
        _, easy = _render("easy", self.BOX)
        _, hard = _render("hard", self.BOX)
        assert easy is not None and hard is not None
        assert easy.total == hard.total == 2
        assert (easy.filled, hard.filled) == (1, 2)

    def test_a_reordered_ladder_moves_the_ranks(self, monkeypatch) -> None:
        """Control, caught: reverse the ladder and every rank reverses with it."""
        monkeypatch.setattr(book_pdf_generator, "TIERS", tuple(reversed(TIERS)))
        ranks = {}
        for tier in TIERS:
            _, dots = _render(tier.value, self.BOX)
            assert dots is not None
            ranks[tier] = dots.filled
        assert ranks == {Tier.HARD: 1, Tier.MEDIUM: 2, Tier.EASY: 3}

    def test_a_tier_absent_from_the_ladder_draws_nothing(self, monkeypatch) -> None:
        """Control, not caught: a tier off the ladder has no rank, so no glyph.

        The complement of the two controls above: the ladder decides *which*
        tiers can be drawn as well as how many dots they get. A tier the
        ladder does not carry draws nothing rather than guessing a rank for it
        — the same call AC-6 makes for a row with no tier at all.
        """
        monkeypatch.setattr(book_pdf_generator, "TIERS", (Tier.EASY,))
        page, dots = _render("hard", self.BOX)
        assert dots is None
        assert not _ink(page).any()

    def test_the_geometry_half_knows_no_tier_at_all(self) -> None:
        """ADR-0007: COMP-007 may not import COMP-006, so the order cannot live there.

        The signature is the mechanism — ``difficulty_dots`` takes a box and
        two ints, with no tier, no ladder and no enum anywhere in it — so
        ``export/layout.py`` holds nothing that could disagree with ``TIERS``,
        and the one place a tier becomes a rank is the drawing half. The
        module importing nothing from ``nonogram`` at all is the other half of
        the same mechanism: there is no route by which an ordering could reach
        it (``tests/test_cli.py`` enforces the rule; this pins that the glyph
        did not need an exemption from it).
        """
        parameters = inspect.signature(difficulty_dots).parameters
        assert list(parameters) == ["left", "top", "right", "bottom", "filled", "total"]
        assert {parameter.annotation for parameter in parameters.values()} == {"int"}

        source = (Path(nonogram.__file__).parent / "export" / "layout.py").read_text(
            encoding="utf-8"
        )
        imported = set()
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
            elif isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
        assert not any(name.split(".")[0] == "nonogram" for name in imported)


# ==========================================================================
# AC-3 — filled vs outlined, measured off the ink
# ==========================================================================


class TestDifficultyDots_FilledAndOutlinedAreDistinguishable:
    """AC-3: the filled dots are solid, the rest outlined at the same stroke."""

    #: A middle tier, as the criterion asks: some dots filled, some not.
    TIER = Tier.MEDIUM
    BOX = (40, 20, 1039, 161)

    @pytest.fixture
    def rendered(self):
        page, dots = _render(self.TIER.value, self.BOX)
        assert dots is not None
        return _ink(page), dots

    def test_the_middle_tier_really_is_a_middle_tier(self) -> None:
        """Guard the fixture: a criterion about "some of each" needs some of each."""
        rank = _rank(self.TIER)
        assert 0 < rank < len(TIERS)

    def test_the_filled_dots_are_solid_and_the_rest_are_not(self, rendered) -> None:
        mask, dots = rendered
        solid = [_is_solid(mask, dot) for dot in dots.dots]
        assert solid == [index < dots.filled for index in range(dots.total)]

    def test_every_dot_is_stroked_at_the_one_reported_width(self, rendered) -> None:
        """The outlined dots' rings measure ``stroke``, on the ink.

        Measured as the ink run the dot's own middle row starts with: on an
        outlined dot that run *is* the ring, and on a filled one it is the
        whole diameter, because a filled dot is a ring filled in.
        """
        mask, dots = rendered
        for index, dot in enumerate(dots.dots):
            run = _left_run(mask, dot)
            expected = dots.diameter if dots.is_filled(index) else dots.stroke
            assert run == expected, (index, run, expected)

    def test_filled_and_outlined_share_one_silhouette(self, rendered) -> None:
        """One stroke for the row means one outline: the dots are the same circle.

        The bounding box of each dot's own ink, offset back to the dot's own
        origin, is identical for a solid dot and an outlined one — so the row
        reads as *two of three* and not as two marks of one kind beside a mark
        of another.
        """
        mask, dots = rendered
        silhouettes = set()
        for left, top, right, bottom in dots.dots:
            box = _ink_box(mask[top : bottom + 1, left : right + 1])
            assert box is not None
            silhouettes.add(box)
        assert len(silhouettes) == 1
        assert silhouettes == {(0, 0, dots.diameter - 1, dots.diameter - 1)}

    def test_an_outlined_dot_keeps_paper_inside_it(self, rendered) -> None:
        """The middle third of an outlined dot is paper, and of a filled one is ink.

        A third of the diameter, centred: well inside the ring at every size
        the measurement can produce (the ring is an eighth of the diameter),
        and large enough that a one-pixel hole would not pass for a white
        middle.
        """
        mask, dots = rendered
        side = max(1, dots.diameter // 3)
        for index, (left, top, right, bottom) in enumerate(dots.dots):
            middle_x = (left + right) // 2
            middle_y = (top + bottom) // 2
            core = mask[
                middle_y - side // 2 : middle_y + side // 2 + 1,
                middle_x - side // 2 : middle_x + side // 2 + 1,
            ]
            assert core.size >= 1
            assert core.all() if dots.is_filled(index) else not core.any(), index

    def test_the_stroke_can_never_close_the_ring(self) -> None:
        """Structural, over the corpus: two strokes never span a whole dot.

        A stroke of half the diameter or more fills an outlined dot in, and
        the glyph would then draw three identical marks. The type refuses such
        a row outright (the control below); this is the sweep showing the
        measurement never produces one.
        """
        measured = 0
        for box, tier in CORPUS:
            dots = _measured(box, tier)
            if dots is None:
                continue
            assert 2 * dots.stroke < dots.diameter, (box, dots.diameter, dots.stroke)
            assert dots.stroke >= 1
            measured += 1
        assert measured >= CORPUS_MIN_GLYPHS

    def test_the_type_refuses_a_stroke_that_closes_the_ring(self) -> None:
        """Control, caught: the invariant above is a property of the type, not of luck."""
        with pytest.raises(ValueError, match="indistinguishable"):
            DifficultyDots(dots=((0, 0, 9, 9), (20, 0, 29, 9)), filled=1, stroke=5)

    def test_the_dot_is_the_cap_height_of_the_band_it_sits_on(self) -> None:
        """:data:`DIFFICULTY_DOT_RATIO`'s stated derivation, measured not restated.

        The constant's docstring derives 0.3 from two other constants: a book
        puzzle page's band is :data:`HEADER_BAND_MM` deep and set in
        :data:`HEADER_FONT_MM` type, a cap height is about seven tenths of an
        em, so the word's own capitals stand about 0.29 of the band and a dot
        the same height sits on the word's optical line.

        Nothing pinned that until review cycle 1 (F-003) measured the hole:
        ``DIFFICULTY_DOT_RATIO`` 0.3 -> 0.45 — a half-again taller dot —
        passed every test in this file, because the one test that looked like
        it bounded the dot re-derived its bound *from the constant under
        test*, which CLAUDE.md names as the anti-pattern it is.

        So the bound here comes from a second, independent measurement: the
        **rendered** cap height of a capital in the face the band is really
        lettered in, at the band's own type size. Two pixels of tolerance, at
        a 142 px band: 0.29-0.32 passes, 0.45 and 0.9 do not. The 0.7-em
        figure the docstring reasons with is asserted separately and more
        loosely, since it is a rule of thumb about type rather than a fact
        about this face.
        """
        band = _px(HEADER_BAND_MM)
        em = _px(HEADER_FONT_MM)
        # Wide enough that the height cap, not the width fit, decides the size
        # — the term DIFFICULTY_DOT_RATIO is the whole of.
        dots = difficulty_dots(0, 0, 40 * band, band - 1, filled=2, total=len(TIERS))
        assert dots is not None
        top, bottom = _band_font(em).getbbox("HARD")[1], _band_font(em).getbbox("HARD")[3]
        rendered_cap = bottom - top
        assert rendered_cap > 0
        assert abs(dots.diameter - rendered_cap) <= 2, (dots.diameter, rendered_cap)
        # And the docstring's own arithmetic, held to the looser bound a rule
        # of thumb deserves.
        assert abs(dots.diameter - em * 0.7) <= 0.1 * band

    def test_the_stroke_ratio_is_what_keeps_them_apart(self) -> None:
        """The two ratios whose bound is a *bound* rather than a measurement.

        The cap ratio is not among them: it is pinned by measurement in
        :meth:`test_the_dot_is_the_cap_height_of_the_band_it_sits_on`. It used
        to be "pinned" here as ``0 < DIFFICULTY_DOT_RATIO < 1``, which
        displayed it rather than pinning it and is what let F-003 through.
        """
        assert DIFFICULTY_DOT_STROKE_RATIO < 0.5
        assert DIFFICULTY_DOT_GAP_RATIO > 0


# ==========================================================================
# AC-4 — one function, four callers (structural)
# ==========================================================================

#: Pillow draw methods whose own geometry **is** an ellipse or an arc of one.
#: A call to any of them puts a round mark on a page, which is what this
#: card's one function exists to be the only source of.
ELLIPSE_METHODS = frozenset({"arc", "chord", "circle", "ellipse", "pieslice"})

#: Pillow draw methods that are not ellipses but could be made to *look* like
#: one — a 24-gon, a square rounded at half its own side, an arbitrary
#: outline, a blitted mask. The guard's claim about them is narrower and
#: separate (see
#: :meth:`TestDifficultyDots_HasExactlyOneDrawingSite.test_no_module_approximates_a_round_mark_another_way`):
#: **this package writes no call to any of these four**, so for them there is
#: no second route to a dot for :data:`ELLIPSE_METHODS` to have to cover.
#: That is a claim about these four names only — the two other approximation
#: routes the package *does* use are in :data:`VERTEX_BOUNDED_METHODS`, and
#: the dingbat route is in :data:`TEXT_METHODS`.
#:
#: ``bitmap`` was moved here from :data:`FLAT_METHODS` in review cycle 1
#: (F-001): a blitted mask is as round as its mask, and nothing calls it, so
#: the stronger claim was free.
ROUND_ENOUGH_METHODS = frozenset(
    {"bitmap", "regular_polygon", "rounded_rectangle", "shape"}
)

#: Draw methods that can approximate a round mark out of *vertices* and that
#: this package really does call, so "nobody calls them" is not a claim
#: available for these two — the proof cycle 1 wanted for them does not exist:
#:
#: * ``draw.polygon`` is called once, for the arrow head between two boxes of
#:   the proof sheet's pipeline diagram
#:   (``book_pdf_generator._draw_pipeline_diagram``) — three vertices.
#: * ``point`` is called twice in ``sourcing/image.py``, but on an *image*
#:   (``Image.point``, a per-pixel value map) and not on a draw object; those
#:   are excluded on the receiver, not waved away (see
#:   :func:`_draw_calls` and
#:   :meth:`TestDifficultyDots_HasExactlyOneDrawingSite.test_a_point_call_on_an_image_is_not_a_draw_call`).
#:
#: So the guard for them is a **vertex bound** rather than absence: see
#: :data:`MAX_FLAT_VERTICES`. Cycle 1's F-001 suggested moving these two into
#: :data:`ROUND_ENOUGH_METHODS` "for free, since the file already asserts they
#: are called nowhere"; that premise is false, and the bound is what closes
#: the route instead.
VERTEX_BOUNDED_METHODS = frozenset({"point", "polygon"})

#: Draw methods that put a *string* on a page. These are guarded for
#: **content**, not for shape: ``draw.text`` is called from four modules, so
#: absence is unavailable here too, and a tier glyph spelled ``"\u25cf\u25cf\u25cb"``
#: is the cheapest implementation CARD-207 has — its header already goes
#: through ``_set_band``'s ``draw.text``, and CON-020's 10 pt floor passes a
#: 14 pt bullet happily. See :data:`ROUND_DINGBATS`.
#:
#: **This set is a classification only — no guard consults it** (cycle 2,
#: out-of-scope note). The dingbat rule ignores methods entirely and reads
#: every string literal in the package, so there is no method-scoped text
#: guard to look for; this set exists to keep
#: :meth:`TestDifficultyDots_HasExactlyOneDrawingSite.test_the_method_classification_covers_every_pillow_draw_method`'s
#: partition exhaustive and to say which names the dingbat rule stands in for.
TEXT_METHODS = frozenset({"multiline_text", "text"})

#: Everything else Pillow's draw object does: flat shapes and the measuring
#: calls. **Unguarded** — the residue after the four guarded sets above rather
#: than "everything that is not an ellipse". For ``rectangle`` and the four
#: calls that only *measure*, unguarded is also harmless: they take no vertex
#: list and no string, so there is nowhere in them to hide a dot.
#:
#: ``line`` is different, and it is a **known hole** rather than a safe name.
#: Pillow's own docstring reads "Draw a line, or a connected sequence of line
#: segments": ``ImageDraw.line(xy, fill, width, joint)`` takes an
#: arbitrary-length coordinate sequence straight to ``draw_lines``, and
#: ``joint="curve"`` even rounds the joints with ``pieslice``. A closed
#: many-point polyline is a ring and a radial fan of two-point calls is a
#: filled disc, both measurably round — review cycle 3 (F-201) landed a
#: complete second three-dot glyph that way with the suite green, and it is
#: carried as a named limit on
#: :class:`TestDifficultyDots_HasExactlyOneDrawingSite` with that mutant beside
#: it. This comment used to say a straight line "has no vertex list to hide a
#: dot in", which is false as written and is how a reader concludes the route
#: is safe.
#:
#: Why it is still unguarded here: moving ``line`` into
#: :data:`VERTEX_BOUNDED_METHODS` is not a wording change. The package already
#: hands it lists no walk can count — ``draw.line(ends, ...)`` at
#: ``book_pdf_generator.py:1429`` and ``export/png.py:186``,
#: ``draw.line(list(side), ...)`` at ``book_pdf_generator.py:1441`` and
#: ``draw.line(list(ends), ...)`` at ``export/png.py:217`` — so each would have to earn an exemption, which is
#: the same regress cycle 2 was right to refuse one level up for receivers.
#: Closing the route properly means measuring ink rather than reading syntax:
#: that is **CARD-241**.
FLAT_METHODS = frozenset(
    {
        "getfont",
        "line",
        "multiline_textbbox",
        "rectangle",
        "textbbox",
        "textlength",
    }
)

#: Every public Pillow draw method, guarded or not — the union the
#: completeness test closes over.
ALL_DRAW_METHODS = (
    ELLIPSE_METHODS
    | ROUND_ENOUGH_METHODS
    | VERTEX_BOUNDED_METHODS
    | TEXT_METHODS
    | FLAT_METHODS
)

#: The most vertices a flat shape in this package is allowed to be written
#: with. The one real call has three (an arrow head); a polygon that passes
#: for a dot needs a dozen or more (cycle 1's surviving mutant used 32). Four
#: leaves room for a quadrilateral without leaving room for a circle.
MAX_FLAT_VERTICES = 4

#: Codepoints that are a round or geometric mark in their own right: Unicode's
#: Geometric Shapes block (U+25A0..U+25FF, which holds \u25cf BLACK CIRCLE and
#: \u25cb WHITE CIRCLE — a three-dot glyph needs nothing else), plus U+2022
#: BULLET and U+2219 BULLET OPERATOR.
ROUND_DINGBATS = frozenset(chr(code) for code in range(0x25A0, 0x2600)) | {
    "\u2022",
    "\u2219",
}

#: The one module exempt from the dingbat rule, and the reason — which is
#: itself asserted, not asserted-to-be-obvious
#: (:meth:`TestDifficultyDots_HasExactlyOneDrawingSite.test_the_dingbat_exemption_is_only_for_a_module_that_cannot_draw`):
#: ``admin/pdf_generator.py`` is the legacy ReportLab generator. It carries
#: three U+2022 bullets in a prose paragraph about the difficulty levels, and
#: it imports no Pillow and makes no draw-object call at all, so it has no
#: route to a page through this guard's subject.
DINGBAT_EXEMPT_MODULES = frozenset({"nonogram.admin.pdf_generator"})

#: How a Pillow draw object is spelled in this package: the bare name
#: ``draw``, or an inline ``ImageDraw.Draw(...)``. Both halves of that are
#: **default-deny** rather than enumerated (cycle 2, F-101): every written
#: receiver of a draw-method name must be one of those two or a named
#: exemption (:data:`NON_DRAW_RECEIVER_SITES`), and every ``.Draw(...)`` call
#: must sit in a binding form this guard understands
#: (:data:`DRAW_BINDING_FORMS`) or at a named site
#: (:data:`DRAW_OBJECT_UNBOUND_SITES`). A spelling nobody predicted is a test
#: failure, not a silent pass. See
#: :meth:`TestDifficultyDots_HasExactlyOneDrawingSite.test_every_receiver_of_a_draw_method_is_a_draw_object`
#: and
#: :meth:`TestDifficultyDots_HasExactlyOneDrawingSite.test_every_draw_object_in_the_package_is_spelled_draw`.
DRAW_RECEIVER_NAME = "draw"

#: The binding forms :func:`_draw_object_bindings` can read a name out of.
#: Everything else a ``.Draw(...)`` call can sit in — an attribute or tuple
#: target, a loop target, a dict value, a ``return`` — is reported as its own
#: unrecognised form and must then be a named site, which is what makes the
#: receiver rule converge instead of chasing Python's grammar. This set is the
#: *understood* half; there is deliberately no attempt to enumerate the other.
DRAW_BINDING_FORMS = frozenset({"assignment", "annotated assignment", "walrus"})

#: Every ``.Draw(...)`` call in the package that is **not** bound to a name, as
#: ``(module, enclosing function, form)`` — an equality, not a pattern, so a
#: fifth one is a failure that has to be looked at.
#:
#: * ``receiver`` — ``ImageDraw.Draw(probe).text(...)``, the one-shot text
#:   metric in ``book_pdf_generator``. It *is* a draw object and
#:   :func:`_is_draw_receiver` accepts it as one.
#: * ``argument`` — a draw object built inline and handed straight to a
#:   function. Safe not because of this line but because the callee's own
#:   parameter is then a receiver, and the receiver rule
#:   (:func:`_unrecognised_draw_receivers`) covers it whatever it is called.
#:   The two mechanisms compose; neither is trusted alone.
#:
#: **Why one of these four names is written in two halves.** Cycle 2 reduced
#: this table to a per-module-and-form *count* because one of the four sites
#: sits in a function whose name is matched by ``meta/profiling``'s frozen
#: ``RENDER_API_PATTERN``, and that pattern is applied to the raw *text* of
#: every file under ``tests/`` (``rank_durations.regrep_render_set``): spelling
#: the name out here would add this file to ``test_suite_profile.py``'s
#: render-heavy set and redden a guard that has nothing to do with this card —
#: and the snapshot that would then have to be restated lives under ``meta/``,
#: which this card may not commit. Cycle 3 (F-204) named the third option that
#: fix missed: the obstacle is a *textual* grep, so the name can be kept while
#: the matching substring is never written, by splitting the literal. That is
#: what the last entry does, and it is the only reason that entry looks odd.
#:
#: The names are therefore back, and with them the precision the count gave up:
#: a site **moving** to a different function of the same module now breaks this
#: equality instead of leaving it unchanged (demonstrated: the ``_titled``
#: argument site moved into a new helper of the same module and the same form
#: reds this test, where the per-module-and-form count it replaced passed).
#:
#: What it still does **not** catch, measured rather than assumed: an unbound
#: site *replaced by a different one inside the same function*, since the
#: triple is then unchanged. That is not an open drawing route — the callee's
#: parameter is a receiver and :func:`_unrecognised_draw_receivers` covers it,
#: which is the composition this table leans on — but the equality alone does
#: not see it. CARD-241.
DRAW_OBJECT_UNBOUND_SITES = (
    ("nonogram.admin.book_pdf_generator", "_blank_page", "argument"),
    ("nonogram.admin.book_pdf_generator", "sample", "receiver"),
    ("nonogram.export.pdf", "_titled", "argument"),
    ("nonogram.export.pdf", "render" + "_pages", "argument"),
)

#: Every call to a draw-method *name* in the package whose receiver is not a
#: draw object, as ``(module, enclosing function, method, receiver)`` — an
#: earned exemption in the shape :data:`DINGBAT_EXEMPT_MODULES` already uses:
#: an equality against what exists today, plus a second assertion (in
#: :meth:`TestDifficultyDots_HasExactlyOneDrawingSite.test_the_non_draw_receiver_exemptions_cannot_draw_a_round_mark`)
#: that neither site can actually put a round mark on a page.
#:
#: Both are ``Image.point``, a per-pixel lookup table: one takes a 256-entry
#: table built with ``*`` and ``+``, the other a lambda. Neither takes
#: coordinates, which is the property the second assertion pins — so these are
#: excluded by what they are, not by a widened bin.
NON_DRAW_RECEIVER_SITES = (
    ("nonogram.sourcing.image", "binarize", "point", "scaled"),
    ("nonogram.sourcing.image", "ink_bounding_box", "point", "greyscale"),
)

#: The one function allowed to put a round mark on a page.
THE_DRAWING_SITE = ("nonogram.admin.book_pdf_generator", "_draw_difficulty_dots")

_PACKAGE_DIR = Path(nonogram.__file__).parent


def _package_sources() -> dict[str, str]:
    """Every module in the package as ``{dotted name: source}``, read off disk.

    Walked rather than listed, exactly as ``tests/test_cli.py``'s import guard
    walks it, so a module a later card adds is covered the moment it lands.
    """
    sources: dict[str, str] = {}
    for path in sorted(_PACKAGE_DIR.rglob("*.py")):
        parts = path.relative_to(_PACKAGE_DIR).with_suffix("").parts
        if parts[-1] == "__init__":
            parts = parts[:-1]
        sources[".".join(("nonogram", *parts))] = path.read_text(encoding="utf-8")
    return sources


def _round_mark_sites(
    sources: Mapping[str, str], methods: frozenset[str]
) -> list[tuple[str, str]]:
    """Every ``(module, enclosing function)`` that calls one of ``methods``.

    Takes its sources as an argument rather than reading the disk itself — the
    same shape ``tests/test_cli.py``'s ``_outward_imports`` has, and for the
    same reason: the rule can then be exercised against a fabricated package
    and cannot pass vacuously.

    Only an *attribute call* counts (``draw.ellipse(...)``): reading an
    attribute of that name, or a bare function of that name, is not a draw
    object putting ink on a page. The function reported is the innermost one
    enclosing the call, so a helper nested inside another is named as itself;
    a call at module level is reported as ``"<module>"``.

    **What a static walk cannot see, stated rather than claimed away.** A
    dynamically dispatched call — ``getattr(draw, "ellipse")(box)`` — is
    invisible to it, so the guard's claim is about *written* calls to those
    methods and no wider. Nothing in this package reaches a draw method that
    way (every draw call in ``src/nonogram/**/*.py`` is written out, which is
    what makes the walk the right instrument here), and a card that started to
    would be making a deliberate choice this guard should be extended for
    rather than slipping past it.
    """
    sites: list[tuple[str, str]] = []

    def walk(node: ast.AST, enclosing: str, module: str) -> None:
        for child in ast.iter_child_nodes(node):
            if (
                isinstance(child, ast.Call)
                and isinstance(child.func, ast.Attribute)
                and child.func.attr in methods
            ):
                sites.append((module, enclosing))
            inner = (
                child.name
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                else enclosing
            )
            walk(child, inner, module)

    for module, source in sorted(sources.items()):
        walk(ast.parse(source), "<module>", module)
    return sites


def _is_draw_receiver(node: ast.AST) -> bool:
    """Whether ``node`` evaluates to a Pillow draw object, as this package spells one.

    Either the bare name :data:`DRAW_RECEIVER_NAME` or an inline
    ``ImageDraw.Draw(...)``. Needed because two method names Pillow's draw
    object carries are also carried by ``Image`` — ``point`` most of all —
    and ``greyscale.point([...])`` mapping pixel values is not a draw call.
    The receiver set's completeness is asserted by
    :meth:`TestDifficultyDots_HasExactlyOneDrawingSite.test_every_draw_object_in_the_package_is_spelled_draw`,
    so this is a measured discrimination rather than a convention.
    """
    if isinstance(node, ast.Name) and node.id == DRAW_RECEIVER_NAME:
        return True
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "Draw"
        # Cycle 2: ``anything.Draw(...)`` used to qualify. Requiring the
        # factory to be Pillow's own keeps this from accepting a look-alike,
        # and the real site (``ImageDraw.Draw(probe)``) still passes.
        and "ImageDraw" in ast.unparse(node.func)
    )


def _draw_calls(
    sources: Mapping[str, str], methods: frozenset[str]
) -> list[tuple[str, str, ast.Call]]:
    """Every call to one of ``methods`` written **on a draw object**.

    The same walk as :func:`_round_mark_sites`, with two differences: the
    receiver must satisfy :func:`_is_draw_receiver`, and the call node itself
    comes back so a guard can look at what was passed to it. Takes its sources
    as an argument for the same reason.

    Carries the same stated blind spot: a dynamically dispatched call
    (``getattr(draw, "polygon")(...)``) is invisible to it.
    """
    calls: list[tuple[str, str, ast.Call]] = []

    def walk(node: ast.AST, enclosing: str, module: str) -> None:
        for child in ast.iter_child_nodes(node):
            if (
                isinstance(child, ast.Call)
                and isinstance(child.func, ast.Attribute)
                and child.func.attr in methods
                and _is_draw_receiver(child.func.value)
            ):
                calls.append((module, enclosing, child))
            inner = (
                child.name
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                else enclosing
            )
            walk(child, inner, module)

    for module, source in sorted(sources.items()):
        walk(ast.parse(source), "<module>", module)
    return calls


def _enclosing_walk(
    sources: Mapping[str, str],
) -> Iterator[tuple[str, str, ast.AST, ast.AST]]:
    """Every node as ``(module, enclosing function, parent, node)``.

    The same enclosing-function bookkeeping :func:`_round_mark_sites` and
    :func:`_draw_calls` do by hand, plus the parent — which is what lets a
    guard say *what form* a node was written in rather than only that it
    exists. Takes its sources as an argument for the same reason they do.
    """

    def walk(node: ast.AST, enclosing: str, module: str) -> Iterator[
        tuple[str, str, ast.AST, ast.AST]
    ]:
        for child in ast.iter_child_nodes(node):
            yield module, enclosing, node, child
            inner = (
                child.name
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                else enclosing
            )
            yield from walk(child, inner, module)

    for module, source in sorted(sources.items()):
        yield from walk(ast.parse(source), "<module>", module)


def _uncountable_vertices(
    calls: Sequence[tuple[str, str, ast.Call]],
) -> list[tuple[str, str, str]]:
    """Every vertex argument this guard cannot verify, and why — **default-deny**.

    The inverted form of cycle 1's bound (cycle 2, F-101). Instead of asking
    "is this a literal of at most :data:`MAX_FLAT_VERTICES` points?" and
    passing everything the question does not fit, it enumerates the one shape
    the guard *understands* — a list or tuple display whose elements are all
    countable — and reports everything else as a complaint:

    * no positional argument at all (``draw.polygon(xy=...)``);
    * a bare name, a call, a comprehension or a conditional, none of which this
      walk can count to the end of;
    * a display containing a starred unpack — ``draw.polygon([*points])`` —
      which *looks* countable (one element) and is not. This is the form that
      survived cycle 2 with 198 green, two characters from the form cycle 1's
      bound already caught, and the reason the default had to invert: the old
      shape of this guard taught the evasion by complaining about "vertices
      this guard cannot count";
    * a countable display over the bound.

    A complaint is a **failure**, not information: the author must either write
    a countable literal or earn an exemption the way
    :data:`NON_DRAW_RECEIVER_SITES` does. The guard therefore never has to
    predict the next spelling — it only has to recognise this one.
    """
    complaints: list[tuple[str, str, str]] = []
    for module, function, call in calls:
        points = call.args[0] if call.args else None
        if not isinstance(points, (ast.List, ast.Tuple)):
            shape = "no positional argument" if points is None else type(points).__name__
            complaints.append(
                (module, function, f"not a countable vertex display ({shape})")
            )
            continue
        starred = [element for element in points.elts if isinstance(element, ast.Starred)]
        if starred:
            complaints.append(
                (
                    module,
                    function,
                    f"{len(starred)} starred unpack(s) in the vertex display: its "
                    f"{len(points.elts)} element(s) are not its vertex count",
                )
            )
            continue
        if len(points.elts) > MAX_FLAT_VERTICES:
            complaints.append(
                (
                    module,
                    function,
                    f"{len(points.elts)} vertices, over the bound of {MAX_FLAT_VERTICES}",
                )
            )
    return complaints


def _draw_method_calls(
    sources: Mapping[str, str],
) -> list[tuple[str, str, str, ast.AST, ast.Call]]:
    """Every written *attribute* call to a draw-method name, whatever its receiver.

    ``(module, enclosing function, method, receiver node, call node)``. Unlike
    :func:`_draw_calls` this does **not** filter on the receiver — filtering is
    the caller's job, because the point of the receiver guard is to see the
    receivers the package was not expecting.

    **The attribute form is a precondition, not a flourish.** A node is
    collected only when ``isinstance(node.func, ast.Attribute)``, so a call has
    to be *written* as ``<something>.<method>(...)`` to be seen at all. A draw
    method pulled into a local and called as a bare name —
    ``stamp = draw.ellipse`` then ``stamp(circle, fill=INK)`` — is collected by
    nothing: the attribute is a read, and the call's ``func`` is an
    ``ast.Name``. That route is a named limit on
    :class:`TestDifficultyDots_HasExactlyOneDrawingSite`, with the mutant that
    demonstrates it, and **CARD-241** is where it closes.
    """
    return [
        (module, function, node.func.attr, node.func.value, node)
        for module, function, _parent, node in _enclosing_walk(sources)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in ALL_DRAW_METHODS
    ]


def _unrecognised_draw_receivers(
    sources: Mapping[str, str],
) -> list[tuple[str, str, str, str]]:
    """Every *attribute* draw-method call whose receiver this guard cannot account for.

    ``(module, enclosing function, method, receiver as written)``, sorted.
    **Default-deny**: a receiver is accounted for only if
    :func:`_is_draw_receiver` recognises it — the bare name
    :data:`DRAW_RECEIVER_NAME` or an inline ``ImageDraw.Draw(...)``. An
    unannotated parameter, an attribute (``self.canvas``), a subscript, a call
    result: all reported.

    This is what replaces "every spelling the package currently uses" (cycle 2,
    F-101). The old receiver test enumerated two syntactic shapes and was
    silent for every other, so a new spelling evaded the guard *and* its own
    completeness test together; here a new spelling lands in this list and the
    equality against :data:`NON_DRAW_RECEIVER_SITES` fails. It also catches by
    *behaviour* rather than by annotation: a parameter is reported because of
    the draw method written on it, not because of how it was typed.

    **What it does not reach, corrected in cycle 3 (F-203).** This docstring
    used to say the rule collects *every written call to a draw-method name
    whatever its receiver*. That is wider than
    :func:`_draw_method_calls`, which requires ``isinstance(node.func,
    ast.Attribute)``: a call written as a bare name — ``stamp(circle)``, after
    ``stamp = draw.ellipse`` — has no receiver for this rule to judge and is
    collected by nothing, so it is neither accounted for nor reported. A named
    limit on :class:`TestDifficultyDots_HasExactlyOneDrawingSite`; **CARD-241**
    closes it.
    """
    return sorted(
        (module, function, method, ast.unparse(receiver))
        for module, function, method, receiver, _call in _draw_method_calls(sources)
        if not _is_draw_receiver(receiver)
    )


def _draw_object_bindings(
    sources: Mapping[str, str],
) -> list[tuple[str, str, str, str]]:
    """Every ``.Draw(...)`` call written in the package, by the form it sits in.

    ``(module, enclosing function, form, name)``, sorted. The form is one of
    :data:`DRAW_BINDING_FORMS` when a name can be read out of it, ``receiver``
    or ``argument`` for the two unbound uses the package really has, and
    ``unrecognised:<NodeType>`` — or ``unrecognised assignment target`` —
    otherwise. ``name`` is ``"<unbound>"`` when there is none.

    **Default-deny** (cycle 2, F-101): the forms listed are the ones this guard
    understands, and an unlisted form is not silence but an entry that breaks
    :data:`DRAW_OBJECT_UNBOUND_SITES`' equality. The form cycle 2 walked
    through — ``canvas: ImageDraw.ImageDraw = ImageDraw.Draw(image)``, the
    *more* idiomatic spelling in a package that annotates all 13 of its draw
    parameters — is now read as an ``annotated assignment`` named ``canvas``,
    so it fails on the name; and a form nobody has thought of fails on the
    form.
    """
    bindings: list[tuple[str, str, str, str]] = []
    for module, function, parent, node in _enclosing_walk(sources):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "Draw"
        ):
            continue
        form, name = "unrecognised:" + type(parent).__name__, "<unbound>"
        if isinstance(parent, ast.Assign):
            targets = parent.targets
            if len(targets) == 1 and isinstance(targets[0], ast.Name):
                form, name = "assignment", targets[0].id
            else:
                form = "unrecognised assignment target (" + ", ".join(
                    type(target).__name__ for target in targets
                ) + ")"
        elif isinstance(parent, ast.AnnAssign) and isinstance(parent.target, ast.Name):
            form, name = "annotated assignment", parent.target.id
        elif isinstance(parent, ast.NamedExpr) and isinstance(parent.target, ast.Name):
            form, name = "walrus", parent.target.id
        elif isinstance(parent, ast.Attribute) and parent.value is node:
            form = "receiver"
        elif isinstance(parent, ast.Call) and node in (*parent.args, *(
            keyword.value for keyword in parent.keywords
        )):
            form = "argument"
        bindings.append((module, function, form, name))
    return sorted(bindings)


def _imagedraw_annotated_parameters(
    sources: Mapping[str, str],
) -> list[tuple[str, str, str]]:
    """Every parameter whose annotation mentions ``ImageDraw``, however spelled.

    ``(module, function, parameter)``, sorted. Matched on the unparsed
    annotation text rather than on one ``ast`` shape (cycle 2, F-101): a bare
    ``ImageDraw``, an ``ImageDraw.ImageDraw``, a string annotation, an
    ``Optional[...]`` wrapper and a keyword-only parameter all count. The
    over-approximation is the safe direction — it can only add names the
    equality then has to account for.
    """
    annotated: list[tuple[str, str, str]] = []
    for module, _enclosing, _parent, node in _enclosing_walk(sources):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        arguments = (
            *node.args.posonlyargs,
            *node.args.args,
            *node.args.kwonlyargs,
            *(argument for argument in (node.args.vararg, node.args.kwarg) if argument),
        )
        for argument in arguments:
            if argument.annotation is not None and "ImageDraw" in ast.unparse(
                argument.annotation
            ):
                annotated.append((module, node.name, argument.arg))
    return sorted(annotated)


def _dingbat_literals(sources: Mapping[str, str]) -> list[tuple[str, str]]:
    """Every ``(module, value)`` string literal holding a :data:`ROUND_DINGBATS` codepoint.

    Every string constant in the module, **including docstrings** — wider than
    "the argument of a ``draw.text`` call", and deliberately so. Cycle 1's
    F-001 proposed the narrow form, but the route it names bypasses it: a
    caller that builds ``f"{number}  {word}  \u25cf\u25cf\u25cb"`` and hands it to
    ``_set_band`` has written the literal nowhere near a ``draw.text`` call.
    A module that genuinely needs such a codepoint — in a docstring, even —
    extends this guard and says why, which is the declaration the narrow form
    would have let it skip.
    """
    found: list[tuple[str, str]] = []
    for module, source in sorted(sources.items()):
        for node in ast.walk(ast.parse(source)):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and set(node.value) & ROUND_DINGBATS
            ):
                found.append((module, node.value))
    return found


class TestDifficultyDots_HasExactlyOneDrawingSite:
    """AC-4, as amended 2026-10-16: exactly one function draws a round mark
    through any of the **four routes a static walk can see**.

    Those four are an ellipse-family method, an unrecognised draw receiver, an
    unrecognised ``.Draw(...)`` binding form, and a dingbat string literal.
    That is narrower than the criterion this class was first written against
    ("given the four call sites, then each draws its dots through this one
    function", read forward as *no second round mark can be written anywhere in
    the package*), and the narrowing is an owner decision rather than a
    concession made here. Three review cycles of this walk each landed a
    complete second three-dot glyph, through a new syntactic family each time:
    receiver, then binding form, then call shape and ink accumulated across
    calls. The root cause is stable and is the generalisable part: **these
    guards discriminate by syntactic form, and no authority enumerates the
    forms.** ``dir(ImageDraw.ImageDraw)`` is a real authority for the *method*
    half — which is why that half is sound — but Python's grammar offers
    nothing to import that lists every way to write a vertex list, name a
    receiver or reach a bound method, so enumeration cannot converge. The
    universal guarantee therefore moved to **CARD-241**, which renders a page,
    finds the ink and measures it for roundness: an instrument blind to
    spelling altogether. It is in this file, four classes below
    (:class:`TestRoundMarkOnThePage_CatchesWhatTheWalkCannotSee` onwards), and
    this class is **not** superseded by it — see the last paragraph for what
    each one reaches that the other does not.

    Asserted the way ``tests/test_cli.py`` asserts ADR-0007's import rule —
    by walking ``src/nonogram/**/*.py`` with ``ast`` — because a promise that
    four later cards will reuse one function is worth nothing unless a fifth
    dot *written through one of these four routes* is a test failure. The walk
    is over the whole package, so CARD-207, CARD-229, CARD-231 and CARD-233
    cannot grow a second dot glyph **by any of the four routes guarded below**
    wherever they end up drawing. Every other route is a **named limit** at the
    foot of this docstring, each with the mutant that demonstrates it is open.

    **Exactly how far this reaches, and where it stops.** The claim is the
    width of the mechanism and no wider; review cycle 1 (F-001) planted three
    second glyphs that an earlier, more confidently worded version of this
    class let through. Four routes are guarded, each by a control that fires:

    1. an ellipse drawn as an ellipse — :data:`ELLIPSE_METHODS`, zero calls
       outside :data:`THE_DRAWING_SITE`;
    2. the four approximation methods the package calls nowhere —
       :data:`ROUND_ENOUGH_METHODS`, zero calls at all;
    3. a circle built out of vertices **in one call** —
       :data:`VERTEX_BOUNDED_METHODS`, whose first argument must be a countable
       display of at most :data:`MAX_FLAT_VERTICES` points, rather than held to
       absence, because the package really does call ``draw.polygon``. The
       bound is **per call** and says nothing about ink laid down over many
       in-bound calls. This line read "a circle built out of vertices — held to
       :data:`MAX_FLAT_VERTICES`" until cycle 3 (F-202) stamped a disc out of
       two-point ``draw.point`` calls; the accumulation route is a named limit
       below;
    4. a dot typed as a character — :data:`ROUND_DINGBATS`, which is the route
       CARD-207 would most cheaply take.

    **The guards are default-deny** (cycle 2, F-101). Cycle 1's version
    discriminated by syntactic *form* and its completeness tests enumerated
    only the forms the package happened to use, so a new spelling evaded the
    guard and its completeness test together — twice, by execution. CARD-238
    escaped that family by deriving its set from an authority; half of this one
    can do the same (``dir(ImageDraw.ImageDraw)``, which is why the method
    partition is sound), but **there is no authority that enumerates "every way
    to write a vertex list" or "every way to name a draw receiver"** — Python's
    grammar has no such list to import. Enumerating more shapes is an infinite
    regress. So the default is inverted instead: each guard names the forms it
    *understands* and treats anything else as a **failure** that must be
    answered with a countable literal or a named, reasoned exemption
    (:data:`NON_DRAW_RECEIVER_SITES`, :data:`DRAW_OBJECT_UNBOUND_SITES`, in the
    shape :data:`DINGBAT_EXEMPT_MODULES` already uses). A new spelling is then a
    test failure, not a silent pass: the guard never has to predict the future,
    only to recognise the present and refuse the unknown.

    What that buys, stated as the distinction it is — three limits are now
    **true by mechanism**:

    * an uncountable vertex argument *fails*. A bare name, a call, a
      comprehension, a conditional, a keyword-only ``xy=`` and a display
      holding a starred unpack are all complaints
      (:func:`_uncountable_vertices`), each with its own control;
    * an unrecognised draw **receiver** fails. Every *attribute* call to a
      draw-method name is collected whatever that receiver is written as — an
      unannotated parameter, ``self.canvas``, a subscript, a call result — and
      the two honest ``Image.point`` sites are an equality with a second
      assertion that neither can draw
      (:meth:`test_every_receiver_of_a_draw_method_is_a_draw_object`,
      :meth:`test_the_non_draw_receiver_exemptions_cannot_draw_a_round_mark`).
      The attribute form is a **precondition**: :func:`_draw_method_calls`
      requires ``isinstance(node.func, ast.Attribute)``, so a draw method
      pulled into a local and called as a bare name has no receiver for this
      rule to judge and is collected by nothing. Until cycle 3 (F-203) this
      read "every written call to a draw-method name whatever its receiver",
      which was wider than the mechanism; the route it overstated is a named
      limit below;
    * an unrecognised ``.Draw(...)`` **binding form** fails — an annotated
      assignment, an attribute target, a tuple or loop target, a walrus, or a
      form nobody has thought of
      (:meth:`test_every_draw_object_in_the_package_is_spelled_draw`).
      Precondition, stated because its sibling above needed the same
      correction: this reads **attribute-form** ``.Draw(...)`` only, so a bare
      ``Draw(image)`` from ``from PIL.ImageDraw import Draw`` is classified as
      nothing here. No round mark escapes that way today — the receiver rule
      catches the glyph whatever the object is called — but the classification
      gap is real and belongs to CARD-241.

    And six routes this walk cannot reach at all — written down rather than
    left as confident sentences. Each one carries the **mutant that
    demonstrated it was open** to *this* instrument: a complete second
    three-dot glyph planted in ``src/nonogram/export/png.py``, run as its own
    fresh ``pytest`` process over this file plus
    ``tests/test_book_interior_type_floor.py``, ``tests/test_cli.py`` and
    ``tests/test_suite_profile.py`` (baseline 548 passed), with the mutated
    source restored from a byte copy and ``shasum``-verified afterwards. Each
    is recorded below with the verdict observed, because a limit asserted
    without that demonstration would be the same defect in a new costume (the
    verdicts are from the 2026-10-16 narrowing pass; batching mutants from one
    parent process yields false KILLED verdicts, so each was its own
    invocation).

    **All six are closed by CARD-241** — not by widening anything here, but by
    the second instrument beside this one: render the book's pages and measure
    the ink
    (:class:`TestRoundMarkOnThePage_CatchesWhatTheWalkCannotSee` and the three
    classes after it). So none of them is carried as a **named limit** any
    more, and none of them was *struck by hand*: the six are a table,
    :data:`NAMED_LIMITS`, and
    :meth:`TestRoundMarkOnThePage_TheNamedLimitsListShrinksHonestly.test_the_limits_list_is_exactly_the_routes_no_instrument_closes`
    holds this prose to it with an equality that derives **by execution** both
    which routes the walk is blind to and which ones the page catches. A route
    this list still carried as open while the page closed it, or struck from
    this list while the page did not catch it, both fail that equality. The
    marker it looks for is ``**LIMIT:** <mutant>``, and after this card no
    entry below carries one:

    * **CLOSED ON THE PAGE** (PA1 pasted mask) — anything outside
      ``ImageDraw`` entirely: ``Image.paste`` of a circular mask,
      ``ImageDraw.floodfill`` (a module function, not a draw method), a
      pre-rendered PNG asset pasted in, a circle that arrives inside an
      imported image. The watched methods come from ``dir(ImageDraw.ImageDraw)``
      and nothing here can see past it. *Mutant PA1*: a helper that takes the
      ``Image`` rather than a draw object and composites each dot as an
      ``Image.new("L")`` mask filled by ``putdata`` from ``x² + y² <= r²`` —
      no draw object, no ``ImageDraw`` call, discs and annuli round by
      construction — **SURVIVED, 548 passed**;
    * **CLOSED ON THE PAGE** (G1 getattr dispatch) — a dynamically dispatched draw call,
      ``getattr(draw, "ellipse")(box)``
      (also stated on :func:`_round_mark_sites`) — the walk reads written
      syntax, and a computed method name is not written. *Mutant G1*:
      ``method = getattr(draw, "ellipse")`` then ``method(circle, fill=INK)``
      for the whole glyph — **SURVIVED, 548 passed**;
    * **CLOSED ON THE PAGE** (D1 typed dingbat) — a round mark **computed** into a string
      rather than written as one —
      ``chr(0x25CF)``, ``b"\xe2\x97\x8f".decode()``,
      ``unicodedata.lookup("BLACK CIRCLE")`` (cycle 2, F-102). The dingbat rule
      is about string *literals*, which :func:`_dingbat_literals` says in so
      many words, so claim and mechanism agree; this names the gap between the
      literal route (closed, exemption and all) and the character itself. The
      non-``.py`` assets the walk never opens belong on the same line.
      *Mutant D1*: ``draw.text`` handed
      ``chr(0x25CF) * rank + chr(0x25CB) * (3 - rank)`` — **SURVIVED, 548
      passed**;
    * **CLOSED ON THE PAGE** (L1 line fan) — a **polyline**. ``line`` is in
      :data:`FLAT_METHODS` with no bound at all,
      and Pillow's own docstring reads "Draw a line, or a connected sequence of
      line segments" — an arbitrary-length coordinate sequence straight to
      ``draw_lines``, with ``joint="curve"`` rounding the joints. *Mutant L1*
      (cycle 3, F-201): a module-level helper in ``export/png.py`` drawing this
      card's whole glyph with ``draw.line`` alone — each filled dot a
      240-segment radial fan, each outlined dot one closed 33-point polyline —
      **SURVIVED, 548 passed**. The marks really are round, measured here with a
      standalone Pillow script that imports no nonogram module: the fan is
      41x41 px at aspect 1.000 with 1272 ink px against ``draw.ellipse``'s 1313
      at the same radius (0.969), and the ring is a 43x41 annulus of 207 px.
      Why it is not simply guarded is on :data:`FLAT_METHODS`: the package
      already hands ``line`` four lists no walk can count, so a bound here buys
      an exemption table rather than a closed route;
    * **CLOSED ON THE PAGE** (PT1 point loop) — ink **accumulated across calls**.
      :func:`_uncountable_vertices` judges one
      call's own first argument, and nothing bounds how many in-bound calls a
      loop may make. *Mutant PT1* (cycle 3, F-202): the same three-dot glyph in
      ``export/png.py``, stamped pixel by pixel in a nested ``for`` loop, every
      call passing a two-element display well inside
      :data:`MAX_FLAT_VERTICES` — **SURVIVED, 548 passed**; 41x41 px at aspect
      1.000, 1257 ink px against ``draw.ellipse``'s 1313 (0.957). Cycle 1's H3,
      the same disc as a comprehension *inside* one call, is caught; moving the
      loop one line out defeats the bound;
    * **CLOSED ON THE PAGE** (BM1 bound method) — a draw method held in a **local** and
      called as a bare name. *Mutant BM1*
      (cycle 3, F-203): ``stamp = draw.ellipse`` in ``export/png.py``, then
      ``stamp(circle, fill=INK)`` and ``stamp(circle, outline=INK, width=2)`` —
      :data:`ELLIPSE_METHODS` itself, on the canonical receiver, the
      most-guarded combination in this file — **SURVIVED, 548 passed**.
      ``functools.partial(draw.ellipse, ...)`` is the same shape. The attribute
      ``draw.ellipse`` is a read, which
      :meth:`test_a_name_that_is_not_a_draw_call_is_not_caught` deliberately
      pins as not-caught, and the call's ``func`` is an ``ast.Name``, so no
      site, no receiver and no binding is recorded.

    A card taking one of those six routes is caught by the render check rather
    than by this one, so what this class promises is narrower than "cannot each
    grow their own circles" and is still exactly what its own mechanism holds.
    The two instruments are kept side by side because **neither contains the
    other**: this walk reads every module on disk, including code no test
    renders, and sees four spellings of a round mark; the render check sees any
    spelling at all, on the pages it renders and nowhere else. What is open to
    *both* is a round mark spelled in one of the six ways above **and** drawn
    either on a surface nobody renders **or** in ink lighter than the render
    check's own threshold — the second disjunct is not optional: the render
    check discriminates on the ink mask alone, so a pasted mask in the grey the
    solved grid already uses (160 against a threshold of 128) is open to both
    instruments *on a page the book really prints*. That pair of routes is the
    honest residue, and both are stated with the rest of the render check's
    bounds on :class:`TestRoundMarkOnThePage_TheBoundaryIsMeasured`.
    """

    def test_the_method_classification_covers_every_pillow_draw_method(self) -> None:
        """The completeness test for the set the guard consults — its own oracle.

        Every public method of Pillow's draw object is classified into exactly
        one of the five sets above. A Pillow release that adds a method fails
        this line until this project has decided which kind it is, so the
        guard's coverage can never quietly fall behind the library it guards.
        """
        pillow = {
            name
            for name in dir(ImageDraw.ImageDraw)
            if not name.startswith("_") and callable(getattr(ImageDraw.ImageDraw, name))
        }
        partition = (
            ELLIPSE_METHODS,
            ROUND_ENOUGH_METHODS,
            VERTEX_BOUNDED_METHODS,
            TEXT_METHODS,
            FLAT_METHODS,
        )
        assert ALL_DRAW_METHODS == pillow
        assert sum(len(part) for part in partition) == len(ALL_DRAW_METHODS)
        assert ALL_DRAW_METHODS == set().union(*partition)

    def test_the_walk_actually_sees_the_package(self) -> None:
        """Guard the guard: an empty or misrooted walk must not pass silently."""
        sources = _package_sources()
        assert {
            "nonogram",
            "nonogram.admin.book_pdf_generator",
            "nonogram.export.layout",
            "nonogram.export.png",
            "nonogram.export.pdf",
        } <= set(sources)
        # Both halves of THE_DRAWING_SITE checked against the source on disk:
        # the module by indexing it, the function name by finding its own
        # ``def``. This is the one real assertion F-006's
        # test_the_real_packages_one_site_is_the_dot_drawer_itself was making,
        # and it is made here instead (cycle 1, F-006). The `getattr` clause
        # that used to follow it is gone (cycle 2, F-104): because
        # _draw_difficulty_dots is imported from book_pdf_generator at module
        # scope, it could only fail by ImportError at collection, and on the
        # one input that could break it — a typo in the literal — the line
        # above fails first.
        assert f"def {THE_DRAWING_SITE[1]}" in sources[THE_DRAWING_SITE[0]]

    def test_the_package_draws_a_round_mark_in_exactly_one_function(self) -> None:
        sites = _round_mark_sites(_package_sources(), ELLIPSE_METHODS)
        assert set(sites) == {THE_DRAWING_SITE}

    def test_no_module_approximates_a_round_mark_another_way(self) -> None:
        """The second claim: the four *unused* approximation routes stay unused.

        :data:`ELLIPSE_METHODS` catches a circle drawn as a circle. It cannot
        catch a dot drawn as a 24-gon, so that is not claimed — instead the
        four methods that could do it and that this package calls nowhere are
        asserted to be called nowhere, which is a claim this walk really can
        make. The two approximation methods the package *does* call are
        guarded by vertex count instead
        (:meth:`test_no_module_draws_a_round_mark_out_of_vertices`), and the
        character route by content
        (:meth:`test_no_module_types_a_round_mark_as_a_character`).
        """
        assert _round_mark_sites(_package_sources(), ROUND_ENOUGH_METHODS) == []

    def test_a_second_drawing_site_is_caught(self) -> None:
        """Control, caught: this is what a fifth dot looks like to the guard."""
        sites = _round_mark_sites(
            {
                "fake.one": "def legal(draw):\n    draw.ellipse((0, 0, 1, 1))\n",
                "fake.two": "def sneaky(draw):\n    draw.ellipse((0, 0, 1, 1))\n",
            },
            ELLIPSE_METHODS,
        )
        assert set(sites) == {("fake.one", "legal"), ("fake.two", "sneaky")}

    def test_a_second_site_in_the_same_module_is_caught(self) -> None:
        """Control, caught: one module, two functions, two sites."""
        sites = _round_mark_sites(
            {
                "fake.mod": (
                    "def first(draw):\n"
                    "    draw.ellipse((0, 0, 1, 1))\n"
                    "def second(draw):\n"
                    "    draw.pieslice((0, 0, 1, 1), 0, 90)\n"
                ),
            },
            ELLIPSE_METHODS,
        )
        assert set(sites) == {("fake.mod", "first"), ("fake.mod", "second")}

    def test_a_method_and_a_nested_helper_are_named_as_themselves(self) -> None:
        """Control, caught: the innermost enclosing function is the one reported."""
        sites = _round_mark_sites(
            {
                "fake.mod": (
                    "class Page:\n"
                    "    def draw_dot(self, draw):\n"
                    "        draw.circle((0, 0), 1)\n"
                    "def outer(draw):\n"
                    "    def inner():\n"
                    "        draw.arc((0, 0, 1, 1), 0, 90)\n"
                    "    inner()\n"
                ),
            },
            ELLIPSE_METHODS,
        )
        assert set(sites) == {("fake.mod", "draw_dot"), ("fake.mod", "inner")}

    def test_a_module_level_call_is_caught_and_named(self) -> None:
        """Control, caught: a circle drawn outside any function is still a site."""
        sites = _round_mark_sites(
            {"fake.mod": "draw.ellipse((0, 0, 1, 1))\n"}, ELLIPSE_METHODS
        )
        assert sites == [("fake.mod", "<module>")]

    def test_a_flat_shape_is_not_caught(self) -> None:
        """Control, not caught: the guard is about round marks, not about drawing.

        Without this the guard's discriminating power would be unknown — a
        walk that flagged everything would also pass
        :meth:`test_a_second_drawing_site_is_caught`.

        ``draw.line`` appears here as a two-point segment, and this control must
        not be read as saying such a call is harmless *because a line cannot be
        round*. It is not caught because the walk does not watch ``line`` at
        all: the same method takes a closed many-point polyline, which is a
        ring, and cycle 3's mutant L1 drew a whole glyph that way with the suite
        green. A named limit of this class, not a safe route — see
        :data:`FLAT_METHODS` and CARD-241.
        """
        flat = {
            "fake.mod": (
                "def strokes(draw):\n"
                "    draw.rectangle((0, 0, 1, 1))\n"
                "    draw.line([(0, 0), (1, 1)])\n"
                "    draw.text((0, 0), 'x')\n"
                "    draw.polygon([(0, 0), (1, 1), (0, 1)])\n"
            )
        }
        assert _round_mark_sites(flat, ELLIPSE_METHODS) == []

    def test_a_name_that_is_not_a_draw_call_is_not_caught(self) -> None:
        """Control, not caught: reading ``.circle``, or calling a bare ``ellipse``.

        An attribute of that name is data, not ink; a plain function of that
        name is not a draw object. Both appear here so the guard's one real
        false-positive route is pinned shut.
        """
        benign = {
            "fake.mod": (
                "def measure(shape, ellipse):\n"
                "    radius = shape.circle\n"
                "    ellipse((0, 0, 1, 1))\n"
                "    return radius, shape.arc\n"
            )
        }
        assert _round_mark_sites(benign, ELLIPSE_METHODS) == []


    # ----------------------------------------------------------------------
    # Route 3: a round mark built out of vertices (cycle 1, F-001 / H2, H3)
    # ----------------------------------------------------------------------

    def test_every_receiver_of_a_draw_method_is_a_draw_object(self) -> None:
        """The receiver rule, inverted: an unknown spelling **fails** (cycle 2, F-101).

        ``point`` is a method of ``Image`` as well as of the draw object, so
        the vertex guard below has to tell ``draw.point([...])`` (ink) from
        ``greyscale.point([...])`` (a pixel-value map), and it does that on the
        receiver. Cycle 1 asserted that discrimination was complete by
        enumerating the two binding shapes the package happened to use; cycle 2
        walked past it with an unannotated parameter and with an annotated
        assignment, because an enumerated guard is silent for everything it did
        not enumerate.

        So the default is inverted. Every *written* call to a draw-method name
        is collected whatever its receiver, and a receiver that is not a draw
        object as this package spells one must be a **named** exemption. There
        is no authority that enumerates "every way to name a draw receiver" —
        Python's grammar has no such list to import — so the guard does not
        try: it recognises two forms and refuses the rest.
        """
        unrecognised = _unrecognised_draw_receivers(_package_sources())
        assert unrecognised == sorted(NON_DRAW_RECEIVER_SITES), unrecognised

    def test_the_non_draw_receiver_exemptions_cannot_draw_a_round_mark(self) -> None:
        """The exemptions' own control — earned by the call, not granted to it.

        The equality above says *which* two sites are excused; this says *why*,
        so the exemption cannot quietly grow into one that could draw. Both are
        ``Image.point``, a per-pixel lookup table, and the discriminating
        property is that it takes no coordinates: a table built with ``*`` and
        ``+``, or a lambda. A future card that writes a coordinate display on
        an exempt receiver fails here instead of inheriting the excuse.
        """
        sources = _package_sources()
        exempt = [
            (module, function, method, call)
            for module, function, method, receiver, call in _draw_method_calls(sources)
            if not _is_draw_receiver(receiver)
        ]
        assert len(exempt) == len(NON_DRAW_RECEIVER_SITES)
        for module, function, method, call in exempt:
            assert method == "point", (module, function, method)
            argument = call.args[0] if call.args else None
            assert not isinstance(argument, (ast.List, ast.Tuple)), (
                module,
                function,
                "a coordinate display on a receiver excused as a pixel map",
            )
        # And the excused names are never a draw object anywhere in the
        # package, so the excuse cannot be borrowed by rebinding the name.
        bound = {name for _, _, _, name in _draw_object_bindings(sources)}
        for _module, _function, _method, spelling in NON_DRAW_RECEIVER_SITES:
            assert spelling not in bound, spelling

    def test_every_draw_object_in_the_package_is_spelled_draw(self) -> None:
        """The binding rule, inverted: an unknown **form** fails (cycle 2, F-101).

        The companion to the receiver rule above, from the other end: not "what
        is this call written on" but "what was this draw object called when it
        was made". Every ``.Draw(...)`` call in the package is classified by the
        form it sits in. A form that yields a name must yield
        :data:`DRAW_RECEIVER_NAME`; a form that yields none must be one of the
        four named sites in :data:`DRAW_OBJECT_UNBOUND_SITES`; and a form this
        guard does not understand is reported as unrecognised, which breaks
        that equality rather than contributing nothing.

        That is the whole of the fix for cycle 2's M3b. ``canvas:
        ImageDraw.ImageDraw = ImageDraw.Draw(image)`` is now read as an
        annotated assignment named ``canvas`` and fails on the name; ``self.canvas
        = ...``, a tuple target and a loop target fail on the form.
        """
        sources = _package_sources()
        bindings = _draw_object_bindings(sources)
        assert bindings, (
            "the walk found no ImageDraw.Draw(...) call in the package — this "
            "guard has gone vacuous; keep it honest with the fabricated sources "
            "in test_an_unrecognised_draw_binding_form_is_caught"
        )
        named = sorted(
            {name for _m, _f, form, name in bindings if form in DRAW_BINDING_FORMS}
        )
        assert named == [DRAW_RECEIVER_NAME], named
        unbound = sorted(
            (module, function, form)
            for module, function, form, _name in bindings
            if form not in DRAW_BINDING_FORMS
        )
        assert unbound == sorted(DRAW_OBJECT_UNBOUND_SITES), unbound

    def test_every_imagedraw_annotated_parameter_is_spelled_draw(self) -> None:
        """And the third end: a parameter *typed* as a draw object.

        Matched on the annotation's text rather than on one ``ast`` shape
        (cycle 2, F-101), so a bare ``ImageDraw``, a string annotation and a
        keyword-only parameter all count. An unannotated parameter handed the
        real draw object is invisible here by construction — it is caught by
        :meth:`test_every_receiver_of_a_draw_method_is_a_draw_object`, which
        judges a parameter by the draw method written on it rather than by how
        it was typed. Neither rule is trusted alone.
        """
        annotated = _imagedraw_annotated_parameters(_package_sources())
        assert {parameter for _m, _f, parameter in annotated} == {DRAW_RECEIVER_NAME}, (
            annotated
        )
        # A floor rather than an equality: thirteen such parameters exist
        # today, and a card that adds a fourteenth is doing nothing wrong. The
        # floor is here only so the rule cannot pass by finding nothing.
        assert len(annotated) >= 13, annotated

    def test_a_second_receiver_spelling_is_caught(self) -> None:
        """Control, caught **with** the receiver rule and missed **without** it.

        Cycle 2's M2: an unannotated parameter handed the real draw object,
        drawing a 32-gon on it. The first half is the new mechanism firing; the
        second half is the two older mechanisms being shown blind to it, which
        is what makes this a control rather than a restatement.
        """
        points = ", ".join(f"({index}, {index})" for index in range(32))
        rogue = {
            "fake.mod": (
                "def _rogue(canvas, rank):\n"
                f"    canvas.polygon([{points}], fill=1)\n"
            )
        }
        assert _unrecognised_draw_receivers(rogue) == [
            ("fake.mod", "_rogue", "polygon", "canvas")
        ]
        # Missed without it: the receiver-filtered vertex guard sees no call,
        # and there is no `.Draw(...)` anywhere for the binding rule to read.
        assert _draw_calls(rogue, VERTEX_BOUNDED_METHODS) == []
        assert _draw_object_bindings(rogue) == []
        assert _imagedraw_annotated_parameters(rogue) == []

    def test_an_annotated_draw_assignment_is_caught(self) -> None:
        """Control, caught with the inverted default and missed without it.

        Cycle 2's M3b — the *more* idiomatic spelling in this package, which
        annotates all 13 of its draw parameters and runs
        ``from __future__ import annotations``. Caught twice over: on the
        binding's name, and on the receiver the 9-gon is drawn on.
        """
        points = ", ".join(f"({index}, {index})" for index in range(9))
        rogue = {
            "fake.mod": (
                "def dots(image):\n"
                "    canvas: ImageDraw.ImageDraw = ImageDraw.Draw(image)\n"
                f"    canvas.polygon([{points}], fill=1)\n"
            )
        }
        assert _draw_object_bindings(rogue) == [
            ("fake.mod", "dots", "annotated assignment", "canvas")
        ]
        assert _unrecognised_draw_receivers(rogue) == [
            ("fake.mod", "dots", "polygon", "canvas")
        ]
        # Missed without it: cycle 1's collector read only `ast.Assign` with a
        # `Name` target, and this source has no such node at all — nor is the
        # annotation on a *parameter*, so the annotation rule is blind to it
        # too. Only the inverted default sees this source.
        assert [form for _m, _f, form, _n in _draw_object_bindings(rogue)] != [
            "assignment"
        ]
        assert _imagedraw_annotated_parameters(rogue) == []

    def test_an_unrecognised_draw_binding_form_is_caught(self) -> None:
        """Control, caught: the forms nobody enumerated are reported as unknown.

        An attribute target, a tuple target and a loop target. None of these is
        a spelling this guard was taught; each is reported as its own
        unrecognised form, which is the whole point of inverting the default —
        the guard does not need to predict the next spelling, only to refuse
        one it cannot read.
        """
        rogue = {
            "fake.attr": "def make(self, image):\n    self.canvas = ImageDraw.Draw(image)\n",
            "fake.tuple": "def make(image):\n    canvas, size = ImageDraw.Draw(image), 1\n",
            "fake.loop": "def make(image):\n    for canvas in (ImageDraw.Draw(image),):\n        pass\n",
        }
        forms = {module: form for module, _f, form, _n in _draw_object_bindings(rogue)}
        assert forms == {
            "fake.attr": "unrecognised assignment target (Attribute)",
            "fake.tuple": "unrecognised:Tuple",
            "fake.loop": "unrecognised:Tuple",
        }, forms
        assert all(form not in DRAW_BINDING_FORMS for form in forms.values())

    def test_the_one_honest_spelling_is_not_caught(self) -> None:
        """Control, not caught: the package's own form must pass, or the rule is a ban.

        Without this the inverted default's discriminating power would be
        unknown — a guard that reported everything would also pass the three
        controls above.
        """
        honest = {
            "fake.mod": (
                "def page(image):\n"
                "    draw = ImageDraw.Draw(image)\n"
                "    draw.ellipse((0, 0, 9, 9))\n"
                "    ImageDraw.Draw(image).text((0, 0), 'x')\n"
            )
        }
        assert _unrecognised_draw_receivers(honest) == []
        assert _draw_object_bindings(honest) == [
            ("fake.mod", "page", "assignment", "draw"),
            ("fake.mod", "page", "receiver", "<unbound>"),
        ]

    def test_no_module_draws_a_round_mark_out_of_vertices(self) -> None:
        """A polygon with enough vertices is a circle; this bounds the vertices.

        Cycle 1 (F-001/H2) put a 32-gon tier glyph in ``export/png.py`` and
        every test stayed green, because ``polygon`` was binned flat on the
        reasoning that "none of them can draw a circle" while
        ``regular_polygon`` — strictly less capable — was binned round.
        Absence is not available as a claim for ``polygon``: the proof sheet's
        pipeline diagram really does draw an arrow head with it. So the bound
        is on the shape, not on the call.

        A vertex argument this walk cannot count is a **failure**, not a pass,
        and since cycle 2 (F-101) that is true by mechanism rather than by
        intention: the check is :func:`_uncountable_vertices`, which enumerates
        the one shape it understands — a list or tuple display of countable
        elements — and complains about every other, the starred unpack
        ``draw.polygon([*points])`` included. A card that computes its points
        has to say so by earning an exemption, which is the declaration the
        lenient reading would have let it skip.
        """
        calls = _draw_calls(_package_sources(), VERTEX_BOUNDED_METHODS)
        assert calls, (
            "no draw-object call to "
            f"{sorted(VERTEX_BOUNDED_METHODS)} remains in the package — this guard "
            "has gone vacuous; keep it honest by pointing it at a fabricated "
            "source, as test_a_many_sided_polygon_is_caught does"
        )
        complaints = _uncountable_vertices(calls)
        assert complaints == [], complaints

    def test_a_many_sided_polygon_is_caught(self) -> None:
        """Control, caught: cycle 1's surviving H2 mutant, through the real check."""
        points = ", ".join(f"({index}, {index})" for index in range(32))
        rogue = {"fake.mod": f"def dots(draw):\n    draw.polygon([{points}], fill=1)\n"}
        calls = _draw_calls(rogue, VERTEX_BOUNDED_METHODS)
        assert [(module, function) for module, function, _ in calls] == [
            ("fake.mod", "dots")
        ]
        complaints = _uncountable_vertices(calls)
        assert [(module, function) for module, function, _ in complaints] == [
            ("fake.mod", "dots")
        ]
        assert "32 vertices" in complaints[0][2]

    def test_a_starred_vertex_literal_is_caught(self) -> None:
        """Control, caught **with** the inverted default and missed **without** it.

        Cycle 2's M1, which survived with 198 green: the 32-gon moved into a
        comprehension and spliced back into a literal. Two characters from the
        form cycle 1's bound already caught, and the old guard's own assertion
        message ("vertices this guard cannot count") pointed at it.

        The second half of this control is the one that matters — it shows the
        two clauses cycle 1 relied on *passing* this source, so the complaint
        above can only come from the starred clause.
        """
        rogue = {
            "fake.mod": (
                "def dots(draw):\n"
                "    points = [(50 + i, 50 - i) for i in range(32)]\n"
                "    draw.polygon([*points], fill=1)\n"
            )
        }
        calls = _draw_calls(rogue, VERTEX_BOUNDED_METHODS)
        assert len(calls) == 1
        complaints = _uncountable_vertices(calls)
        assert [(module, function) for module, function, _ in complaints] == [
            ("fake.mod", "dots")
        ]
        assert "starred unpack" in complaints[0][2]
        # Missed without it: cycle 1's two clauses both pass this source.
        argument = calls[0][2].args[0]
        assert isinstance(argument, (ast.List, ast.Tuple))
        assert len(argument.elts) == 1 <= MAX_FLAT_VERTICES

    def test_a_vertex_list_passed_by_name_is_caught(self) -> None:
        """Control, caught: the bare-name form, and the keyword-only form.

        Neither is countable, so neither is read as safe. These two and the
        comprehension below are the shapes the default-deny rule exists to
        refuse without having had to predict them.
        """
        rogue = {
            "fake.name": "def dots(draw, points):\n    draw.polygon(points, fill=1)\n",
            "fake.keyword": "def dots(draw, points):\n    draw.point(xy=points, fill=1)\n",
        }
        complaints = _uncountable_vertices(
            _draw_calls(rogue, VERTEX_BOUNDED_METHODS)
        )
        assert [(module, why) for module, _f, why in complaints] == [
            ("fake.keyword", "not a countable vertex display (no positional argument)"),
            ("fake.name", "not a countable vertex display (Name)"),
        ], complaints

    def test_a_disc_drawn_point_by_point_is_caught(self) -> None:
        """Control, caught: cycle 1's surviving H3 mutant (a filled disc via ``point``)."""
        rogue = {
            "fake.mod": (
                "def dots(draw):\n"
                "    draw.point([(x, y) for x in range(9) for y in range(9)], fill=1)\n"
            )
        }
        calls = _draw_calls(rogue, VERTEX_BOUNDED_METHODS)
        assert len(calls) == 1
        # A computed point list is exactly the shape the guard refuses to read
        # as safe: not a countable display, so not a pass.
        complaints = _uncountable_vertices(calls)
        assert complaints == [
            ("fake.mod", "dots", "not a countable vertex display (ListComp)")
        ]

    def test_a_three_vertex_arrow_head_is_not_caught(self) -> None:
        """Control, not caught: the guard bounds roundness, not drawing.

        Without this the bound's discriminating power would be unknown — a
        guard that rejected every polygon would also pass the three controls
        above. The real arrow head at ``book_pdf_generator:1895`` is this
        shape, and it has to keep passing without the bin being widened.
        """
        flat = {
            "fake.mod": (
                "def arrow(draw):\n"
                "    draw.polygon([(0, 0), (4, 2), (0, 4)], fill=1)\n"
            )
        }
        calls = _draw_calls(flat, VERTEX_BOUNDED_METHODS)
        assert len(calls) == 1
        assert _uncountable_vertices(calls) == []

    def test_a_point_call_on_an_image_is_not_a_draw_call(self) -> None:
        """Control, not caught: ``Image.point`` is a pixel map, not ink.

        ``sourcing/image.py`` calls it twice with a 256-entry table and with a
        lambda. Neither is a draw object putting a mark on a page, and both
        would be unmeasurable vertex lists if the receiver were ignored — so
        the vertex guard would fail on honest code. The receiver rule is what
        keeps it honest, and this pins that rule from the other side.
        """
        images = {
            "fake.mod": (
                "def binarise(greyscale):\n"
                "    ink = greyscale.point([255] * 128 + [0] * 128, mode='L')\n"
                "    return ink.point(lambda value: value, mode='L')\n"
            )
        }
        assert _draw_calls(images, VERTEX_BOUNDED_METHODS) == []
        # And the unfiltered walk shows the discrimination is the receiver's
        # doing rather than a quirk of the fabricated source.
        assert len(_round_mark_sites(images, VERTEX_BOUNDED_METHODS)) == 2

    # ----------------------------------------------------------------------
    # Route 4: a dot typed as a character (cycle 1, F-001 / H1)
    # ----------------------------------------------------------------------

    def test_no_module_types_a_round_mark_as_a_character(self) -> None:
        """The route CARD-207 would most cheaply take, closed.

        Cycle 1 (F-001/H1) drew a second tier glyph with
        ``draw.text(xy, "\u25cf" * rank + "\u25cb" * (3 - rank))`` and every test stayed
        green. ``draw.text`` is called from four modules, so absence is not
        available as a claim for it either; the claim is about **content**:
        no module in ``src/nonogram/`` writes a string literal holding a
        :data:`ROUND_DINGBATS` codepoint.

        Wider than "the argument of a ``draw.text`` call" on purpose — see
        :func:`_dingbat_literals` — because CARD-207's cheapest route builds
        the band's string at its caller and hands it to ``_set_band``.
        """
        offenders = [
            (module, value)
            for module, value in _dingbat_literals(_package_sources())
            if module not in DINGBAT_EXEMPT_MODULES
        ]
        assert offenders == []

    def test_the_dingbat_exemption_is_only_for_a_module_that_cannot_draw(self) -> None:
        """The exemption's own control: it is earned by the module, not granted.

        :data:`DINGBAT_EXEMPT_MODULES` is exactly the set of modules that
        carry such a codepoint today, and the one in it reaches no Pillow draw
        object at all — so it cannot put a dingbat on a Pillow page however
        its prose is spelled. Both halves are measured: the exemption cannot
        quietly grow to cover a module that *does* draw, and it cannot quietly
        stay behind a module that stopped needing it.
        """
        sources = _package_sources()
        assert {module for module, _ in _dingbat_literals(sources)} == (
            DINGBAT_EXEMPT_MODULES
        )
        for module in DINGBAT_EXEMPT_MODULES:
            assert _draw_calls({module: sources[module]}, ALL_DRAW_METHODS) == []
            assert "ImageDraw" not in sources[module]

    def test_a_typed_round_mark_is_caught(self) -> None:
        """Control, caught: the glyph as a band string, and as a ``draw.text`` argument."""
        band = {
            "fake.caller": (
                "def header(draw, band, number, word):\n"
                "    _set_band(draw, band, f'{number}  {word}  \u25cf\u25cf\u25cb', 100)\n"
            )
        }
        assert [module for module, _ in _dingbat_literals(band)] == ["fake.caller"]
        inline = {"fake.mod": "def dots(draw):\n    draw.text((0, 0), '\u2022\u2022\u25cb')\n"}
        assert [module for module, _ in _dingbat_literals(inline)] == ["fake.mod"]

    def test_plain_text_is_not_caught(self) -> None:
        """Control, not caught: the words the bands really carry.

        The band's own strings — a puzzle number, a tier label, an ellipsis
        spelled with three full stops — must pass, or the guard would be a
        ban on text rather than on a typed dot.
        """
        plain = {
            "fake.mod": (
                "def header(draw):\n"
                "    draw.text((0, 0), 'PUZZLE 12  MEDIUM')\n"
                "    draw.text((0, 0), '...')\n"
                "    draw.text((0, 0), 'Easy / Medium / Hard')\n"
            )
        }
        assert _dingbat_literals(plain) == []


# ==========================================================================
# AC-5 — the smallest place it appears
# ==========================================================================


class TestDifficultyDots_FitsTheSmallestHeader:
    """AC-5: three dots fit a solution tile's header, clear of the text and the rule.

    The box is measured, not invented: it is the narrowest of the bands a
    packed solution tile reserves inside itself on the smallest trim a book
    may be stored with. :data:`SOLVED_TILE_CAPACITIES` is ``(2, 4)``, so there
    are **six** such bands at a 10 cm square trim, and the narrowest measures
    **474 x 142 px** (the right-hand column's, at either capacity; the
    left-hand column's are 475 wide). Those numbers are quoted here for a
    reader, never relied on: every assertion below measures the box through
    :func:`_smallest_solution_tile_band`, which is why review cycle 1 found
    the card's prose wrong (F-005) and the tests right.

    **The superlative this cannot check.** "The narrowest header *any* of the
    four callers will hand the glyph" is what the card wants and is not yet
    measurable: only CARD-233's box exists. CARD-229's guide key strip and
    CARD-231's section opener are unbuilt and could be narrower — a key strip
    beside a legend line is a plausible candidate. So what is claimed is the
    narrowest header **this project can measure today**, plus the general
    property that carries over: a box too small is declined rather than
    overflowed (:meth:`test_a_box_too_small_is_declined_rather_than_overflowed`).
    The adopting cards re-run AC-5 against their own box (cycle 1, F-007).
    """

    def test_the_box_really_is_the_smallest_one_a_caller_gives(self, box) -> None:
        """Guard the fixture: the measurement must be the minimum of the real set."""
        bands = _solution_tile_bands()
        assert box in bands
        assert all(box[2] - box[0] <= other[2] - other[0] for other in bands)
        assert len(bands) == sum(SOLVED_TILE_CAPACITIES)

    def test_the_smallest_header_still_gets_its_dots(self, box) -> None:
        for tier in TIERS:
            assert _measured(box, tier) is not None, (tier, box)

    def test_the_row_keeps_paper_on_every_side_of_the_box(self, box) -> None:
        """Nothing the caller puts beside the glyph can be touched by it.

        The dots are centred inside the box they were given, and the row is
        fitted to half a dot less width than it is allowed, so there is always
        white between the outermost dot and the box's own edge — which is what
        makes "it does not touch the word beside it" a fact about the geometry
        rather than about the caller's own care.
        """
        left, top, right, bottom = box
        dots = _measured(box, Tier.MEDIUM)
        assert dots is not None
        assert left < dots.left and dots.right < right
        assert top < dots.top and dots.bottom < bottom
        clearance = min(dots.left - left, right - dots.right)
        # The guarantee the measurement makes for a three-rung ladder, and the
        # pixel floor underneath it. This box clears both by a wide margin
        # (10x the bound); the bound itself is swept over the corpus by
        # ``test_the_row_keeps_a_fifth_of_a_dot_of_white_at_each_end``.
        assert clearance >= 1
        assert clearance >= dots.diameter // 5

    def test_the_dots_never_reach_the_tiles_own_rule(self, box) -> None:
        """The box stops one pixel above the drawing, and the ink stops inside it.

        A solution tile's own rule is the top of its grid frame, at
        ``drawing_top``; the band ends at ``drawing_top - 1``. So the gap
        between the lowest dot and the rule is the box's own bottom clearance
        plus one, and it is positive.
        """
        spec = _min_trim_spec()
        packed = compute_packed_solved_layout([_SMALL_CLUES] * 4, 4, spec)
        assert packed is not None
        for slot in packed.slots:
            page = slot.page
            assert page is not None
            tile = (page.usable_left, page.usable_top, page.usable_right, page.drawing_top - 1)
            dots = _measured(tile, Tier.HARD)
            assert dots is not None
            assert dots.bottom < page.drawing_top
            assert dots.top > page.usable_top

    def test_the_rendered_ink_lands_inside_the_reported_box(self, box) -> None:
        page, dots = _render(Tier.HARD.value, box)
        assert dots is not None
        inked = _ink_box(_ink(page))
        assert inked is not None
        assert inked == (dots.left, dots.top, dots.right, dots.bottom)
        left, top, right, bottom = box
        assert left <= inked[0] and inked[2] <= right
        assert top <= inked[1] and inked[3] <= bottom

    def test_the_glyph_leaves_room_for_the_widest_tier_word(self, box) -> None:
        """The dots do not crowd the word out of the header they share.

        Measured against the band's own type at the shrink floor ``_set_band``
        already uses (:data:`_MIN_BAND_FONT_RATIO`), in the face the band is
        really lettered in: what is left of the box beside the glyph holds the
        widest tier label with room to spare. What each caller actually puts
        there is CARD-207/229/231/233's business (guardrail G-4); this only
        shows the glyph does not take the room away.
        """
        spec = _min_trim_spec()
        packed = compute_packed_solved_layout([_SMALL_CLUES] * 4, 4, spec)
        assert packed is not None
        band = header_band(packed.slots[0])
        font = _band_font(max(1, round(band.font_size * _MIN_BAND_FONT_RATIO)))
        widest = max(font.getlength(tier.label.upper()) for tier in TIERS)
        dots = _measured(box, Tier.MEDIUM)
        assert dots is not None
        glyph_width = dots.right - dots.left + 1
        remaining = (box[2] - box[0] + 1) - glyph_width
        assert remaining > widest

    def test_a_box_too_small_is_declined_rather_than_overflowed(self, box) -> None:
        """Control: "it fits" is a measurement, so a box that does not must fail it.

        Shrink the smallest real header until a dot would fall under
        :data:`MIN_DIFFICULTY_DOT_MM` and the answer is ``None`` — no row, no
        ink, no glyph squeezed past the point where a filled dot and an
        outlined one look the same on paper.
        """
        left, top, right, _ = box
        tiny = (left, top, right, top + MIN_DOT_PX - 1)
        assert _measured(tiny, Tier.MEDIUM) is None
        page, dots = _render(Tier.MEDIUM.value, tiny)
        assert dots is None
        assert not _ink(page).any()

    def test_the_decline_is_not_a_blanket_rule(self, box) -> None:
        """And the control above is not passing because the function never draws."""
        assert _measured(box, Tier.MEDIUM) is not None


# ==========================================================================
# AC-6 — a puzzle with no tier of record
# ==========================================================================


class TestDifficultyDots_UntieredDrawsNothing:
    """AC-6: an unreadable tier draws nothing — not three outlined dots."""

    BOX = (10, 10, 1009, 151)

    UNREADABLE = (
        None,
        "",
        "   ",
        "extreme",
        "Unrated",
        "medium-ish",
        0,
        3,
        object(),
        ["medium"],
    )

    @pytest.mark.parametrize("stored", UNREADABLE, ids=lambda value: repr(value)[:20])
    def test_nothing_is_drawn_at_all(self, stored: object) -> None:
        page, dots = _render(stored, self.BOX)
        assert dots is None
        assert not _ink(page).any(), f"{stored!r} inked a page it should have left blank"

    def test_not_even_three_outlined_dots(self) -> None:
        """The specific wrong answer the criterion names, ruled out by pixel count.

        Three outlined dots would read as the easiest of three tiers to a
        reader who has just learned the glyph on the guide page, so an unknown
        tier must not draw the frame either. Compared against the ink a real
        glyph does lay down, so the assertion cannot pass by the page being
        blank for some other reason.
        """
        blank, nothing = _render(None, self.BOX)
        drawn, dots = _render(Tier.EASY.value, self.BOX)
        assert nothing is None and dots is not None
        assert _ink(blank).sum() == 0
        assert _ink(drawn).sum() > 0

    def test_a_readable_tier_is_the_control(self) -> None:
        """Discriminating power: every spelling the reader *does* accept draws."""
        for stored in ("easy", "Easy", "  MEDIUM  ", "hard", Tier.HARD):
            _, dots = _render(stored, self.BOX)
            assert dots is not None, stored

    def test_the_retired_guess_tier_still_reads_as_hard(self) -> None:
        """ADR-0031/R3's reading rule is not re-litigated here.

        ``"guess"`` is a word no build writes any more but older rows carry;
        ``tier_of_record`` reads it as Hard, and the glyph follows that one
        reader rather than deciding for itself — which is the whole point of
        having one reader (:func:`band_identity` prints the same word).
        """
        _, dots = _render("guess", self.BOX)
        assert dots is not None
        assert dots.filled == _rank(Tier.HARD)

    def test_the_type_cannot_express_an_empty_or_unfilled_row(self) -> None:
        """Structural: "three outlined dots" is not a value this glyph has.

        The mistake the criterion warns about is unconstructible rather than
        merely untested — a row with no filled dot is refused by the type, and
        a rank of zero is refused by the measurement. That claim is about
        AC-3's and AC-6's two refusals (this one and the ring-closing stroke
        below); the other four are pinned by
        :meth:`test_the_type_refuses_every_row_it_documents_as_impossible`,
        which exists because review cycle 1 (F-002) disabled each of them and
        watched all 186 tests stay green.
        """
        with pytest.raises(ValueError, match="filled must be"):
            DifficultyDots(dots=((0, 0, 11, 11),), filled=0, stroke=1)
        with pytest.raises(ValueError, match="at least one dot"):
            DifficultyDots(dots=(), filled=1, stroke=1)
        with pytest.raises(ValueError, match="filled must be"):
            difficulty_dots(*self.BOX, filled=0, total=len(TIERS))
        with pytest.raises(ValueError, match="filled must be"):
            difficulty_dots(*self.BOX, filled=len(TIERS) + 1, total=len(TIERS))
        with pytest.raises(ValueError, match="at least one rung"):
            difficulty_dots(*self.BOX, filled=1, total=0)

    def test_the_type_refuses_every_row_it_documents_as_impossible(self) -> None:
        """The four refusals no caller can currently reach, reached directly.

        Review cycle 1 (F-002) disabled each of these four lines in
        ``__post_init__`` and every test stayed green: the single constructor
        cannot emit a row that violates them, so "unconstructible" was resting
        on the absence of a caller rather than on the type. These cases
        construct the bad rows by hand, which is the only way the refusals can
        fail if a later card (CARD-229's key strip is a declared consumer)
        changes the measurement.
        """
        # A stroke of zero: an "outlined" dot with no outline is invisible.
        with pytest.raises(ValueError, match="at least one pixel"):
            DifficultyDots(dots=((0, 0, 11, 11),), filled=1, stroke=0)
        # Two dots of different diameters: the row is not one glyph.
        with pytest.raises(ValueError, match="the same circle"):
            DifficultyDots(dots=((0, 0, 11, 11), (20, 0, 29, 9)), filled=1, stroke=1)
        # Two dots on different tops: the row is not one line.
        with pytest.raises(ValueError, match="one line"):
            DifficultyDots(dots=((0, 0, 11, 11), (20, 5, 31, 16)), filled=1, stroke=1)
        # Two overlapping dots.
        with pytest.raises(ValueError, match="overlap or touch"):
            DifficultyDots(dots=((0, 0, 11, 11), (6, 0, 17, 11)), filled=1, stroke=1)

    def test_the_type_refuses_two_dots_that_merely_touch(self) -> None:
        """F-004: "no two dots touch" is the type's rule, not just the sweep's.

        ``left == right + 1`` is adjacency — two dots sharing an edge, one
        smear at print size. The refusal used to be ``left <= right``, which
        accepted it while the corpus invariant and the card both claimed no
        two dots touch. Paired with the row one pixel wider, which is accepted,
        so the bound is a measurement rather than a blanket refusal.
        """
        with pytest.raises(ValueError, match="overlap or touch"):
            DifficultyDots(dots=((0, 0, 11, 11), (12, 0, 23, 11)), filled=1, stroke=1)
        spaced = DifficultyDots(dots=((0, 0, 11, 11), (13, 0, 24, 11)), filled=1, stroke=1)
        assert spaced.dots[1][0] - spaced.dots[0][2] - 1 == 1

    def test_the_stored_tier_is_read_and_never_written(self) -> None:
        """ADR-0033/R1: book assembly never changes a puzzle's tier.

        The glyph is handed the row's own value and gives it back untouched —
        asserted on a mutable container, which is the only shape of value that
        could carry a write back out of the function.
        """
        row = {"difficulty_tier": "medium"}
        before = dict(row)
        _render(row["difficulty_tier"], self.BOX)
        assert row == before


# ==========================================================================
# The invariants, over the seeded corpus
# ==========================================================================


class TestDifficultyDots_GeometryHoldsOverASeededCorpus:
    """Every invariant the glyph carries, swept over :data:`CORPUS`.

    The invariants, named before they are checked: the row is one line of
    equal circles; they do not overlap; they lie strictly inside the box they
    were given; the row is centred in it; the ink is the same whichever tier
    asked for it; and the measurement is pure.
    """

    def test_the_corpus_is_large_enough(self) -> None:
        assert len(CORPUS) >= CORPUS_MIN_CASES
        assert len({box for box, _ in CORPUS}) >= CORPUS_MIN_CASES // len(TIERS)
        assert {tier for _, tier in CORPUS} == set(TIERS)
        drawn = sum(1 for box, tier in CORPUS if _measured(box, tier) is not None)
        assert drawn >= CORPUS_MIN_GLYPHS, (
            f"only {drawn} of {len(CORPUS)} boxes produce a glyph at all; every "
            "sweep below would then be measuring almost nothing"
        )
        assert drawn < len(CORPUS), (
            "the corpus must keep some boxes the glyph declines, or the declining "
            "branch is swept by nothing"
        )

    def test_every_glyph_is_one_line_of_equal_circles(self) -> None:
        measured = 0
        for box, tier in CORPUS:
            dots = _measured(box, tier)
            if dots is None:
                continue
            widths = {right - left + 1 for left, _, right, _ in dots.dots}
            heights = {bottom - top + 1 for _, top, _, bottom in dots.dots}
            tops = {top for _, top, _, _ in dots.dots}
            assert widths == heights == {dots.diameter}
            assert len(tops) == 1
            assert dots.diameter >= MIN_DOT_PX
            measured += 1
        assert measured >= CORPUS_MIN_GLYPHS

    def test_no_two_dots_of_a_row_touch(self) -> None:
        measured = 0
        for box, tier in CORPUS:
            dots = _measured(box, tier)
            if dots is None:
                continue
            for (_, _, right, _), (left, _, _, _) in zip(dots.dots, dots.dots[1:]):
                assert left - right - 1 >= 1, (box, dots.dots)
            measured += 1
        assert measured >= CORPUS_MIN_GLYPHS

    def test_every_glyph_lies_strictly_inside_its_own_box(self) -> None:
        measured = 0
        for box, tier in CORPUS:
            dots = _measured(box, tier)
            if dots is None:
                continue
            left, top, right, bottom = box
            assert left < dots.left, (box, dots.left)
            assert dots.right < right, (box, dots.right)
            assert top < dots.top, (box, dots.top)
            assert dots.bottom < bottom, (box, dots.bottom)
            measured += 1
        assert measured >= CORPUS_MIN_GLYPHS

    def test_the_row_keeps_a_fifth_of_a_dot_of_white_at_each_end(self) -> None:
        """The bound :func:`difficulty_dots`' docstring states, swept.

        The glyph is drawn beside a word, so the claim that matters is not
        only "inside the box" but "not flush with it". A fifth of a dot is the
        worst case the measurement produces at this project's three-rung
        ladder; the docstring quotes it, and this is what would fail if the
        half-dot reservation in the width fit were dropped.
        """
        measured = 0
        for box, tier in CORPUS:
            dots = _measured(box, tier)
            if dots is None:
                continue
            left, _, right, _ = box
            clearance = min(dots.left - left, right - dots.right)
            assert clearance >= 1, (box, clearance)
            assert clearance * 5 >= dots.diameter, (box, clearance, dots.diameter)
            measured += 1
        assert measured >= CORPUS_MIN_GLYPHS

    def test_every_glyph_is_centred_in_its_own_box(self) -> None:
        measured = 0
        for box, tier in CORPUS:
            dots = _measured(box, tier)
            if dots is None:
                continue
            left, top, right, bottom = box
            assert abs((dots.left - left) - (right - dots.right)) <= 1, box
            assert abs((dots.top - top) - (bottom - dots.bottom)) <= 1, box
            measured += 1
        assert measured >= CORPUS_MIN_GLYPHS

    def test_a_dot_never_outgrows_its_share_of_the_box(self) -> None:
        """The two terms the size comes from, each held to its own bound."""
        measured = 0
        for box, tier in CORPUS:
            dots = _measured(box, tier)
            if dots is None:
                continue
            left, top, right, bottom = box
            assert dots.diameter <= (bottom - top + 1) * DIFFICULTY_DOT_RATIO
            allowed = (right - left + 1) / (len(TIERS) * (1 + DIFFICULTY_DOT_GAP_RATIO))
            assert dots.diameter <= allowed
            measured += 1
        assert measured >= CORPUS_MIN_GLYPHS

    def test_the_footprint_does_not_depend_on_the_tier(self) -> None:
        boxes = {box for box, _ in CORPUS}
        for box in boxes:
            glyphs = [_measured(box, tier) for tier in TIERS]
            if glyphs[0] is None:
                assert all(glyph is None for glyph in glyphs)
                continue
            assert len({glyph.dots for glyph in glyphs}) == 1  # type: ignore[union-attr]
            assert len({glyph.stroke for glyph in glyphs}) == 1  # type: ignore[union-attr]
        assert len(boxes) >= CORPUS_MIN_CASES // len(TIERS)

    def test_the_measurement_is_pure(self) -> None:
        measured = 0
        for box, tier in CORPUS:
            first = _measured(box, tier)
            assert first == _measured(box, tier)
            measured += 1
        assert measured >= CORPUS_MIN_CASES


# ==========================================================================
# CARD-241 — AC-4 universally: one round mark on the page, proved by
# rendering it rather than by reading the source
#
#     AC-1  TestRoundMarkOnThePage_CatchesWhatTheWalkCannotSee
#     AC-2  TestRoundMarkOnThePage_PassesOnTheRealBook
#     AC-3  TestRoundMarkOnThePage_SameVerdictForEverySpelling
#     AC-4  TestRoundMarkOnThePage_TheBoundaryIsMeasured
#     AC-5  TestRoundMarkOnThePage_TheNamedLimitsListShrinksHonestly
#
# The ``ast`` walk above discriminates by syntactic form and no authority
# enumerates the forms, so it cannot hold "nothing else draws a round mark"
# (three review cycles, three landed glyphs, a new family each time). The
# guard below reads **ink**: it renders the pages the book really produces and
# asserts that every round region on them was declared by the one drawing
# site. It is blind to spelling, so there is no next syntactic level for it to
# be evaded at — and it is bounded in a different direction instead, by the
# surfaces it renders and by what "round" is measured to mean. Both bounds are
# stated, each with a control that fails if the reach ever changes.
# ==========================================================================

#: The tier every plant below draws, and the rank it therefore has — read off
#: the project's own ladder rather than written as a 2, for the same reason
#: ``_draw_difficulty_dots`` reads it there (a second ladder is how
#: ``strategy_counter.py`` grew a second classifier, CARD-155).
PLANTED_TIER = TIERS[1]


def _plant_box(band: object, room: int) -> tuple[int, int, int, int] | None:
    """The box a planted glyph draws itself in, inside ``band``'s own strip.

    The left end of the band, where a slot's header has no ink of its own: the
    identity line is centred on ``band.center_x``, so a glyph set here sits on
    paper rather than across the word. That matters for a measurement of
    *connected* ink — a dot stroked over a letter is one region with the
    letter and is no longer round (a bound this file states and tests), and a
    plant landing there would be weaker evidence than it looks.
    """
    height = getattr(band, "height")
    if height <= 0 or room <= 0:
        return None
    left = getattr(band, "center_x") - room // 2 + 4
    top = getattr(band, "center_y") - height // 2
    return (left, top, left + min(2 * height, room // 4), top + height - 1)


def _planted_dots(box: tuple[int, int, int, int]) -> DifficultyDots | None:
    """The geometry a plant strokes — COMP-007's answer, as any caller gets it.

    Every rogue route below draws **the same dots in the same places** as the
    declared site would; only the Pillow call used to ink them differs. That is
    what makes AC-3's "same verdict for every spelling" a measurement of the
    instrument rather than of four different glyphs.
    """
    return difficulty_dots(*box, filled=_rank(PLANTED_TIER), total=len(TIERS))


def _the_declared_site(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]) -> None:
    """The honest route: the book's one drawing site, which declares its dots."""
    book_pdf_generator._draw_difficulty_dots(draw, PLANTED_TIER, *box)


def _rogue_ellipse(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]) -> None:
    """``draw.ellipse`` outside the one site — the route the static walk sees."""
    dots = _planted_dots(box)
    if dots is None:
        return
    for index, dot in enumerate(dots.dots):
        if dots.is_filled(index):
            draw.ellipse(dot, fill=INK)
        else:
            draw.ellipse(dot, fill=BACKGROUND, outline=INK, width=dots.stroke)


def _rogue_polygon(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]) -> None:
    """A 32-gon per dot — cycle 1's H2 and cycle 2's M1, spelled as a polygon."""
    dots = _planted_dots(box)
    if dots is None:
        return
    for index, dot in enumerate(dots.dots):
        left, top, right, bottom = dot
        middle_x, middle_y = (left + right) / 2, (top + bottom) / 2
        radius = (right - left) / 2
        corners = [
            (
                middle_x + radius * math.cos(step * math.tau / 32),
                middle_y + radius * math.sin(step * math.tau / 32),
            )
            for step in range(32)
        ]
        if dots.is_filled(index):
            draw.polygon(corners, fill=INK)
        else:
            draw.polygon(corners, fill=BACKGROUND, outline=INK, width=dots.stroke)


def _rogue_line_fan(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]) -> None:
    """Cycle 3's **mutant L1**: each filled dot a 240-ray fan of ``draw.line``.

    ``line`` is in :data:`FLAT_METHODS` with no bound at all, and Pillow draws
    a connected polyline from an arbitrary-length coordinate sequence. CARD-228
    measured this fan at 41x41 px, aspect 1.000, 1329 ink px against
    ``draw.ellipse``'s 1313 — the same mark on a printed page.
    """
    dots = _planted_dots(box)
    if dots is None:
        return
    for index, dot in enumerate(dots.dots):
        left, top, right, bottom = dot
        middle_x, middle_y = (left + right) / 2, (top + bottom) / 2
        radius = (right - left) / 2
        if dots.is_filled(index):
            for step in range(240):
                angle = step * math.tau / 240
                draw.line(
                    [
                        (middle_x, middle_y),
                        (middle_x + radius * math.cos(angle), middle_y + radius * math.sin(angle)),
                    ],
                    fill=INK,
                    width=1,
                )
        else:
            ring = [
                (
                    middle_x + radius * math.cos(step * math.tau / 32),
                    middle_y + radius * math.sin(step * math.tau / 32),
                )
                for step in range(33)
            ]
            draw.line(ring, fill=INK, width=dots.stroke)


def _rogue_point_loop(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]) -> None:
    """Cycle 3's **mutant PT1**: ink accumulated across in-bound ``draw.point`` calls.

    Every call passes a two-element display, well inside
    :data:`MAX_FLAT_VERTICES`, so the per-call vertex bound has nothing to
    complain about; the disc is the *loop*. CARD-228 measured it at 41x41 px,
    aspect 1.000, 1257 ink px.
    """
    dots = _planted_dots(box)
    if dots is None:
        return
    for index, dot in enumerate(dots.dots):
        left, top, right, bottom = dot
        middle_x, middle_y = (left + right) // 2, (top + bottom) // 2
        radius = (right - left) // 2
        for y in range(top, bottom + 1):
            for x in range(left, right + 1):
                distance = (x - middle_x) ** 2 + (y - middle_y) ** 2
                if dots.is_filled(index):
                    inside = distance <= radius * radius
                else:
                    inside = radius * radius * 0.6 <= distance <= radius * radius
                if inside:
                    draw.point((x, y), fill=INK)


def _rogue_bound_method(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]) -> None:
    """Cycle 3's **mutant BM1**: ``stamp = draw.ellipse``, then ``stamp(...)``.

    :data:`ELLIPSE_METHODS` itself, on the canonical receiver — the
    most-guarded combination in this file — reached through a local, so the
    call's ``func`` is an ``ast.Name`` and no site, receiver or binding is
    recorded by any of the walks above.
    """
    dots = _planted_dots(box)
    if dots is None:
        return
    stamp = draw.ellipse
    for index, dot in enumerate(dots.dots):
        if dots.is_filled(index):
            stamp(dot, fill=INK)
        else:
            stamp(dot, fill=BACKGROUND, outline=INK, width=dots.stroke)


def _rogue_getattr_dispatch(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]) -> None:
    """Cycle 2's **mutant G1**: the method name computed, never written."""
    dots = _planted_dots(box)
    if dots is None:
        return
    method = getattr(draw, "ellipse")
    for index, dot in enumerate(dots.dots):
        if dots.is_filled(index):
            method(dot, fill=INK)
        else:
            method(dot, fill=BACKGROUND, outline=INK, width=dots.stroke)


def _rogue_typed_dingbat(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]) -> None:
    """Cycle 2's **mutant D1**: the dot *computed* into a string and set as type.

    ``chr(0x25CF)`` rather than the character itself, which is the whole point
    of the route: :func:`_dingbat_literals` sees string **literals**, and a
    computed string is not one. Set in the band's own face at the dot's own
    diameter, so the ink is the size the glyph would have drawn.
    """
    dots = _planted_dots(box)
    if dots is None:
        return
    for index, dot in enumerate(dots.dots):
        left, top, right, bottom = dot
        # DejaVu's BLACK CIRCLE fills about 0.72 em, so the face is set larger
        # than the dot to land the same diameter; measured, not guessed, by
        # test_a_typed_dot_measures_the_same_as_a_stroked_one below.
        font = _band_font(round((right - left + 1) / 0.72))
        draw.text(
            ((left + right) / 2, (top + bottom) / 2),
            chr(0x25CF) if dots.is_filled(index) else chr(0x25CB),
            font=font,
            fill=INK,
            anchor="mm",
        )


def _rogue_pasted_mask(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]) -> None:
    """The **mutant PA1** route: outside ``ImageDraw`` altogether.

    A circular ``L`` mask built from ``x^2 + y^2 <= r^2`` and composited with
    ``Image.paste`` — no draw method is called at all, so every walk above is
    blind to it by construction. The page is reached through Pillow's own
    back-reference on the draw object (``ImageDraw.ImageDraw._image``), which is
    how a plant gets at the surface from inside a hook that is handed only the
    draw object; production code would simply be passed the image.
    """
    dots = _planted_dots(box)
    if dots is None:
        return
    page = draw._image
    for index, dot in enumerate(dots.dots):
        left, top, right, bottom = dot
        side = right - left + 1
        radius = side / 2
        mask = Image.new("L", (side, side), 0)
        mask.putdata(
            [
                255
                if (x - radius + 0.5) ** 2 + (y - radius + 0.5) ** 2 <= (radius - 0.5) ** 2
                else 0
                for y in range(side)
                for x in range(side)
            ]
        )
        if not dots.is_filled(index):
            inner = Image.new("L", (side, side), 0)
            thickness = dots.stroke
            inner.putdata(
                [
                    255
                    if (x - radius + 0.5) ** 2 + (y - radius + 0.5) ** 2
                    <= (radius - 0.5 - thickness) ** 2
                    else 0
                    for y in range(side)
                    for x in range(side)
                ]
            )
            mask.paste(0, (0, 0), inner)
        page.paste(Image.new("RGB", (side, side), INK), (left, top), mask)


def _rogue_grey_ellipse(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]) -> None:
    """CARD-243's **route GY1**: the one glyph, stroked in the book's own grey.

    ``draw.ellipse`` — the spelling CARD-228's walk *does* see — in
    :data:`~nonogram.admin.book_pdf_generator._SOLVED_GRID_GRAY`, the colour a
    solved page rules its answer cells in, read from the production module
    rather than written out here (CARD-243 G-3). It is lighter than
    :data:`~tests.helpers.round_ink.INK_LEVEL`, so to CARD-241's black-ink
    instrument this glyph is not on the page at all.
    """
    dots = _planted_dots(box)
    if dots is None:
        return
    for index, dot in enumerate(dots.dots):
        if dots.is_filled(index):
            draw.ellipse(dot, fill=_SOLVED_GRID_GRAY)
        else:
            draw.ellipse(dot, fill=BACKGROUND, outline=_SOLVED_GRID_GRAY, width=dots.stroke)


def _rogue_grey_bound_method(
    draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]
) -> None:
    """CARD-243's **route GY2**: the book's own grey, in a spelling nothing reads.

    CARD-228's mutant BM1 — ``stamp = draw.ellipse``, then ``stamp(...)``, so
    the call's ``func`` is an ``ast.Name`` and no walk records a site — painted
    in ``_SOLVED_GRID_GRAY`` instead of ``INK``. This is the mark ADR-0036/R3
    recorded as open to **both** of its instruments: a spelling the static walk
    cannot see, in a darkness the render check could not see. GY1 above is open
    to one of the two; this is the one open to the union, and it is why this
    card exists rather than a bullet in a bound list.
    """
    dots = _planted_dots(box)
    if dots is None:
        return
    stamp = draw.ellipse
    for index, dot in enumerate(dots.dots):
        if dots.is_filled(index):
            stamp(dot, fill=_SOLVED_GRID_GRAY)
        else:
            stamp(dot, fill=BACKGROUND, outline=_SOLVED_GRID_GRAY, width=dots.stroke)


#: Every way of putting this card's glyph on a page that the tests below plant,
#: by the name CARD-228's review cycles gave it. The *geometry* is identical in
#: all of them (:func:`_planted_dots`); only the Pillow call differs — and, for
#: CARD-243's two grey routes, only the colour it is painted in.
PLANTS: Mapping[str, object] = {
    "the declared site": _the_declared_site,
    "ellipse": _rogue_ellipse,
    "polygon": _rogue_polygon,
    "L1 line fan": _rogue_line_fan,
    "PT1 point loop": _rogue_point_loop,
    "BM1 bound method": _rogue_bound_method,
    "G1 getattr dispatch": _rogue_getattr_dispatch,
    "D1 typed dingbat": _rogue_typed_dingbat,
    "PA1 pasted mask": _rogue_pasted_mask,
    "GY1 grey ellipse": _rogue_grey_ellipse,
    "GY2 grey bound method": _rogue_grey_bound_method,
}

#: CARD-243's two routes, by the name this card gives them — the keys the
#: tests below plant and the names
#: :class:`TestRoundMarkOnThePage_SeesTheGreysTheBookPrints` pairs against
#: CARD-241's black-ink instrument.
GREY_ROUTES = ("GY1 grey ellipse", "GY2 grey bound method")


# --------------------------------------------------------------------------
# The harness: render the book, measure its ink, account for every round mark
# --------------------------------------------------------------------------

def _off_tolerances(region: InkRegion) -> tuple[float, float]:
    """How far ``region`` is from round on each axis, in units of its tolerance.

    ``(aspect, fill)``, each at most 1.0 for a round mark and above 1.0
    otherwise. The one definition of those two ratios, because CARD-243 needs
    three numbers out of them — the margin, and each tolerance's own room
    (:class:`LevelInk`) — and a second copy of either ratio is a second answer
    waiting to drift. A mutant that scaled a copy of this formula was the way
    that drift was found rather than reasoned about.
    """
    return (
        abs(region.aspect - 1.0) / ROUND_ASPECT_TOLERANCE,
        abs(region.fill - 1.0) / ROUND_FILL_TOLERANCE,
    )


#: How far a region is from measuring round, in units of the tolerance that
#: binds it: at most 1.0 for a round mark, above 1.0 for everything else. The
#: *margin* AC-2 and AC-4 assert is this number for the closest thing on a real
#: page — the measurement that says the tolerances sit in a gap rather than on
#: an edge.
def _distance_from_round(region: InkRegion) -> float:
    return max(_off_tolerances(region))


#: Where one round mark is: its page number and its box. Both halves are
#: carried everywhere a mark is, because the accounting matches on both — see
#: :func:`_unaccounted`.
Mark = tuple[int, tuple[int, int, int, int]]


@dataclass(frozen=True)
class LevelInk:
    """What one rendered interior measures **at one darkness threshold**.

    CARD-241 had one of these and did not need the name: its instrument read
    ink, and ink was grey 128. CARD-243's reads the same pages twice, because
    the two readings answer different questions and neither answer contains
    the other — the ink reading is the one every geometry measurement in
    ``tests/helpers/page_ink.py`` uses and the one whose figures on the book's
    own pages are recorded, and the mark reading is the one the guard's verdict
    comes from (:data:`~tests.helpers.round_ink.MEASURED_LEVELS`).

    Attributes:
        level: The threshold this record was measured at.
        regions: How many connected regions the pages carry in all — the
            denominator that keeps "no round mark" from being a statement about
            a blank book.
        found: Every round mark as a :data:`Mark` — its page number and its
            box — over all pages.
        margin: :func:`_distance_from_round` for the closest region that is
            *not* round.
        closest: That region itself. Carried so that a claim about **which**
            of the two tolerances the margin rests on is asserted rather than
            written down in a docstring (CARD-241 cycle 1, F-003). ``None``
            only for an interior with no non-round region at all.
        fill_headroom: How far :data:`ROUND_FILL_TOLERANCE` could grow, in
            units of itself, before some region of these pages whose footprint
            is *already* square enough becomes round. The one number that says
            what that tolerance's own room on the book is, as against the
            margin, which is whichever of the two binds first.
        fill_closest: The region that sets it.
        aspect_headroom: The same for :data:`ROUND_ASPECT_TOLERANCE`, over the
            regions whose ``fill`` is already inside its tolerance.
        aspect_closest: The region that sets it.
    """

    level: int
    regions: int
    found: tuple[Mark, ...]
    margin: float
    closest: InkRegion | None
    fill_headroom: float
    fill_closest: InkRegion | None
    aspect_headroom: float
    aspect_closest: InkRegion | None


@dataclass(frozen=True)
class BookInk:
    """What one rendered interior measures, at every threshold it was read at.

    Attributes:
        pages: How many pages were rendered and measured.
        declared: Every **filled** dot the one drawing site reported drawing,
            as a :data:`Mark`, over all pages. An outlined dot is not here: it
            is a ring, and a ring is not round to this instrument (a stated
            bound).
        plants: How many times the plant hook fired. Zero on an unplanted
            book, and asserted non-zero wherever a plant is the evidence, so a
            plant that silently failed to land cannot read as a pass.
        at: One :class:`LevelInk` per threshold the pages were read at, keyed
            by the threshold. ``at[INK_LEVEL]`` is CARD-241's reading and
            ``at[MARK_LEVEL]`` is the guard's.
        widened_pixels: How many pixels of these pages are paper to
            :data:`INK_LEVEL` and a mark to :data:`MARK_LEVEL` — the ink the
            widening actually added. The denominator AC-2 needs: "the book
            still passes at the wider threshold" says nothing about a book
            whose pages have no such pixel on them.

    The four properties below read the guard's own threshold, which is what
    every claim about the guard's *verdict* is about; a claim about the black
    reading asks ``at[INK_LEVEL]`` for it by name.
    """

    pages: int
    declared: tuple[Mark, ...]
    plants: int
    at: Mapping[int, LevelInk]
    widened_pixels: int

    @property
    def regions(self) -> int:
        return self.at[MARK_LEVEL].regions

    @property
    def found(self) -> tuple[Mark, ...]:
        return self.at[MARK_LEVEL].found

    @property
    def margin(self) -> float:
        return self.at[MARK_LEVEL].margin

    @property
    def closest(self) -> InkRegion | None:
        return self.at[MARK_LEVEL].closest

    @property
    def unaccounted(self) -> tuple[Mark, ...]:
        """The round marks no declared dot on *their own page* accounts for.

        The guard's verdict, and empty is a pass. Read at
        :data:`~tests.helpers.round_ink.MARK_LEVEL`, because a mark the book
        prints in its own grey is a mark on the paper.
        """
        return _unaccounted(self.found, self.declared)


def _unaccounted(
    found: Sequence[Mark],
    declared: Sequence[Mark],
) -> tuple[Mark, ...]:
    """The round marks ``declared`` does not pay for, matched page and box.

    A multiset, not a set: two round marks at one declared box are one mark
    more than was declared. Matched **exactly**, because a dot stroked by
    ``draw.ellipse`` inks precisely its own box (measured:
    :meth:`TestRoundMarkOnThePage_PassesOnTheRealBook.test_the_glyph_the_one_site_draws_is_found_and_accounted_for`),
    so a tolerance here would only buy a rogue mark room to hide beside a
    declared one.

    And matched **per page**, which is the same argument one level up. Every
    page's band geometry is identical, so a declared box on page 4 is a box on
    page 11 as well; dropping the page would let a rogue mark on one page be
    paid for by a declared dot on another whose own mark was not found — it
    touched other ink, or it was outlined. The page is carried from
    :func:`_interior_ink`, so that trade cannot be made (cycle 1, F-009).
    """
    remaining = Counter(declared)
    missing: list[Mark] = []
    for mark in found:
        if remaining[mark] > 0:
            remaining[mark] -= 1
        else:
            missing.append(mark)
    return tuple(missing)


#: The two module attributes :func:`_interior_ink` hooks, captured at import —
#: before any test has run — so "the plant was reverted" can be an identity
#: check against the real originals rather than against whatever happens to be
#: bound at the time (cycle 1, F-008).
_UNHOOKED_SITE = book_pdf_generator._draw_difficulty_dots
_UNHOOKED_SET_BAND = book_pdf_generator._set_band


def _interior_ink(
    plant: object = None, puzzles: Sequence[dict] | None = None
) -> BookInk:
    """Render an interior with ``plant`` drawing into every band, and measure it.

    Named ``_interior_ink`` rather than ``_measure_interior`` on purpose, and
    the reason is spelled around its own trap: ``meta/profiling``'s
    ``RENDER_API_PATTERN`` greps the *text* of every file under ``tests/`` for
    eight render-API names, one of which is the word *interior* immediately
    followed by an opening parenthesis. A helper spelled that way — or a
    docstring quoting it, which is how this sentence had to be rewritten — puts
    this file into the live render set while ``RENDER_HEAVY_SNAPSHOT``, a
    frozen artefact of one profiling run, does not list it, and
    ``test_the_frozen_render_set_still_matches_the_grep_that_defines_it`` goes
    red. Splitting or spelling out the matched literal is the option CARD-228's
    own fix cycle missed (its review's F-204). The call this file really makes,
    ``interior_pages``, is not one of those eight names, so the file does not
    match that grep on its own merits; CARD-241's notes record why re-freezing
    the snapshot was not this card's to do (G-5) and what the next profiling
    run should record instead.

    Two hooks, both module attributes restored in a ``finally`` (the revert
    half of AC-1's plant-and-revert, in the same process rather than in a
    comment):

    * :func:`~nonogram.admin.book_pdf_generator._draw_difficulty_dots` is
      wrapped in a spy, so whatever the **one drawing site** draws is
      *declared*. It is the site's own return value that is recorded, not a
      guess at its geometry — and it is recorded with the page it landed on,
      because the accounting matches page and box rather than box alone
      (:func:`_unaccounted`).
    * ``_set_band`` is wrapped so ``plant`` draws into each band after the
      header is set. That is the realistic site: a puzzle page's band is where
      CARD-207's dots will go, and it is reached on a real page of a real book
      rather than on a canvas invented for the test.
    """
    drawn_on: list[tuple[int, tuple[int, int, int, int]]] = []
    plants = 0
    site = book_pdf_generator._draw_difficulty_dots
    set_band = book_pdf_generator._set_band

    def spy(draw, stored_tier, left, top, right, bottom):
        dots = site(draw, stored_tier, left, top, right, bottom)
        if dots is not None:
            # Recorded with the *page* it was drawn on, because the accounting
            # is per page (:func:`_unaccounted`). The site is handed a draw
            # object and never a page number, so the page is taken from the
            # identity of the image that draw object holds and turned into a
            # page number below, once the pages exist.
            drawn_on.extend(
                (id(draw._image), dot)
                for index, dot in enumerate(dots.dots)
                if dots.is_filled(index)
            )
        return dots

    def banded(draw, band, text, room):
        nonlocal plants
        set_band(draw, band, text, room)
        box = _plant_box(band, room)
        if box is None:
            return
        plants += 1
        plant(draw, box)

    book_pdf_generator._draw_difficulty_dots = spy
    if plant is not None:
        book_pdf_generator._set_band = banded
    try:
        generator = BookPDFGenerator(corpus_book())
        pages = generator.interior_pages(
            list(baseline_puzzles() if puzzles is None else puzzles)
        )
    finally:
        book_pdf_generator._draw_difficulty_dots = site
        book_pdf_generator._set_band = set_band

    number_of = {id(page): number for number, page in enumerate(pages)}
    unplaced = sorted({key for key, _ in drawn_on if key not in number_of})
    assert not unplaced, (
        "the one drawing site drew onto an image that is not one of the pages "
        "being measured, so its dots cannot be accounted for by page"
    )
    declared = [(number_of[key], box) for key, box in drawn_on]

    # Read at every threshold, page by page rather than threshold by threshold,
    # so the pages are walked once and dropped once: holding a second list of
    # thirteen interior pages is what would actually cost memory here, not
    # reading each page twice (CARD-243 AC-6, measured in
    # meta/profiling/card-243-two-threshold-cost.md).
    found: dict[int, list[Mark]] = {level: [] for level in MEASURED_LEVELS}
    regions = dict.fromkeys(MEASURED_LEVELS, 0)
    nearest: dict[int, dict[str, tuple[float, InkRegion | None]]] = {
        level: {key: (float("inf"), None) for key in ("both", "fill", "aspect")}
        for level in MEASURED_LEVELS
    }
    widened_pixels = 0
    for number, page in enumerate(pages):
        grey = np.asarray(page.convert("L"))
        widened_pixels += int(((grey >= INK_LEVEL) & (grey < MARK_LEVEL)).sum())
        for level in MEASURED_LEVELS:
            for region in ink_regions(page, level):
                regions[level] += 1
                if region.is_round:
                    found[level].append((number, region.box))
                    continue
                off_aspect, off_fill = _off_tolerances(region)
                here = nearest[level]
                for key, distance in (
                    ("both", _distance_from_round(region)),
                    # Each tolerance's own room is measured over the regions
                    # the OTHER one already admits: a region off square is no
                    # evidence about how far `fill` could stretch, because
                    # `aspect` is what keeps it out (CARD-241 cycle 1, F-003 —
                    # the finding that the one number hid which tolerance
                    # carried it).
                    ("fill", off_fill if off_aspect <= 1.0 else float("inf")),
                    ("aspect", off_aspect if off_fill <= 1.0 else float("inf")),
                ):
                    if distance < here[key][0]:
                        here[key] = (distance, region)
    return BookInk(
        pages=len(pages),
        declared=tuple(declared),
        plants=plants,
        widened_pixels=widened_pixels,
        at={
            level: LevelInk(
                level=level,
                regions=regions[level],
                found=tuple(found[level]),
                margin=nearest[level]["both"][0],
                closest=nearest[level]["both"][1],
                fill_headroom=nearest[level]["fill"][0],
                fill_closest=nearest[level]["fill"][1],
                aspect_headroom=nearest[level]["aspect"][0],
                aspect_closest=nearest[level]["aspect"][1],
            )
            for level in MEASURED_LEVELS
        },
    )


#: Measured interiors, kept by route so the eight plants below cost one render
#: each and not one per assertion. The *pages* are dropped as soon as they are
#: measured — a list of thirteen interior pages is ~330 MB (CARD-145), and
#: holding nine of those would be the one way this file could run a machine out
#: of memory.
_MEASURED: dict[str, BookInk] = {}


def _book_ink(route: str | None) -> BookInk:
    """The measurement for ``route`` (``None`` for the book as it really is)."""
    key = "" if route is None else route
    if key not in _MEASURED:
        _MEASURED[key] = _interior_ink(None if route is None else PLANTS[route])
    return _MEASURED[key]


# --------------------------------------------------------------------------
# Shapes drawn on a canvas of their own, for the boundary measurements (AC-4)
# --------------------------------------------------------------------------

#: A canvas every boundary shape is drawn on: wide enough that nothing touches
#: an edge, so a measurement is of the shape and not of a clip.
_SHAPE_CANVAS = 240


def _shape(
    drawer: object, canvas: int = _SHAPE_CANVAS, level: int = INK_LEVEL
) -> InkRegion:
    """``drawer``'s largest region, drawn alone on a blank canvas.

    ``level`` defaults to :data:`INK_LEVEL` so every figure CARD-241 recorded
    off this helper is still read off the same measurement; the boundary tests
    sweep it over :data:`MEASURED_LEVELS` to show which of those figures the
    widened threshold moves (CARD-243 AC-3 — the answer is none of them, and
    that is measured rather than assumed).
    """
    page = Image.new("RGB", (canvas, canvas), BACKGROUND)
    drawer(ImageDraw.Draw(page), page)
    regions = ink_regions(page, level)
    assert regions, "the shape drew no ink at all"
    return max(regions, key=lambda region: region.ink)


def _regular_polygon(sides: int, radius: float, *, stretch: float = 1.0) -> object:
    """A regular ``sides``-gon of ``radius``, optionally stretched vertically."""
    middle = _SHAPE_CANVAS // 2

    def drawer(draw: ImageDraw.ImageDraw, page: Image.Image) -> None:
        draw.polygon(
            [
                (
                    middle + radius * math.cos(step * math.tau / sides),
                    middle + stretch * radius * math.sin(step * math.tau / sides),
                )
                for step in range(sides)
            ],
            fill=INK,
        )

    return drawer


#: How much paper every boundary shape keeps around itself, so a measurement
#: is of the shape and never of a clip at the canvas edge.
_SHAPE_MARGIN = 20


def _disc(diameter: int) -> object:
    """A filled circle of ``diameter``, stroked as an ellipse.

    Placed at :data:`_SHAPE_MARGIN` from the top left rather than in the middle
    of :data:`_SHAPE_CANVAS`, because the sweep that uses it sizes its own
    canvas to the diameter.
    """

    def drawer(draw: ImageDraw.ImageDraw, page: Image.Image) -> None:
        left = top = _SHAPE_MARGIN
        draw.ellipse((left, top, left + diameter - 1, top + diameter - 1), fill=INK)

    return drawer


# --------------------------------------------------------------------------
# The static walk's verdict on the same plants, so "what the walk cannot see"
# is a measurement in this file rather than a quotation from a review report
# --------------------------------------------------------------------------


def _static_walk_complaints(plant: object) -> list[str]:
    """What CARD-228's walk says about ``plant``'s own source, as a fabricated module.

    The four routes that walk guards, run over the plant's source text the way
    :meth:`TestDifficultyDots_HasExactlyOneDrawingSite.test_a_many_sided_polygon_is_caught`
    runs them over a fabricated module: an ellipse-family call, an unused
    approximation method, an uncountable vertex argument, an unrecognised draw
    receiver, a dingbat string literal. The fifth mechanism — the
    ``.Draw(...)`` binding form — cannot fire here, and not because it was
    skipped: every plant is *handed* a draw object, exactly as every drawing
    site in ``src/nonogram/**`` is, so none of them constructs one.

    This is how the pairing AC-1 needs is made without re-planting anything in
    ``src/``: the routes CARD-228's cycles recorded as SURVIVED come back with
    **no complaint** here, and the two routes it recorded as KILLED come back
    with one.
    """
    source = {"planted.module": inspect.getsource(plant)}
    complaints = [
        f"round mark site: {site}"
        for site in _round_mark_sites(source, ELLIPSE_METHODS | ROUND_ENOUGH_METHODS)
    ]
    complaints += [
        f"uncountable vertices: {complaint}"
        for complaint in _uncountable_vertices(_draw_calls(source, VERTEX_BOUNDED_METHODS))
    ]
    complaints += [
        f"unrecognised receiver: {receiver}"
        for receiver in _unrecognised_draw_receivers(source)
    ]
    complaints += [f"dingbat literal: {found}" for found in _dingbat_literals(source)]
    return complaints


@dataclass(frozen=True)
class RoundMarkRoute:
    """One way of putting a round mark on a page, and which instrument sees it.

    Attributes:
        mutant: CARD-228's own name for the route, which is also the key into
            :data:`PLANTS` and the string its named-limits list used to carry.
        seen_by_the_walk: Whether the ``ast`` walk complains about it.
            Derived by execution in
            :meth:`TestRoundMarkOnThePage_TheNamedLimitsListShrinksHonestly.test_the_walk_really_is_blind_to_every_route_in_the_table`
            — never trusted as a declaration.
        closed_on_the_page: Whether rendering the book and measuring the ink
            catches it. Derived by execution in the same class. A route whose
            flag disagrees with what the render check actually does fails
            :meth:`~TestRoundMarkOnThePage_TheNamedLimitsListShrinksHonestly.test_the_limits_list_is_exactly_the_routes_no_instrument_closes`,
            in either direction.
    """

    mutant: str
    seen_by_the_walk: bool
    closed_on_the_page: bool


#: CARD-228's six named limits, as a table instead of six paragraphs of prose
#: (AC-5). Each was recorded by that card as a complete second three-dot glyph
#: that landed in ``src/nonogram/export/png.py`` with 548 tests green; each is
#: now planted on a real page here instead, and the two flags are checked
#: against what the two instruments actually do.
#:
#: **Nothing is struck from this list by editing it.** The equality below
#: derives both columns by execution, so a route marked closed that the page
#: does not catch, and a route the page catches that is still carried as open,
#: are both red.
NAMED_LIMITS: tuple[RoundMarkRoute, ...] = (
    RoundMarkRoute("PA1 pasted mask", seen_by_the_walk=False, closed_on_the_page=True),
    RoundMarkRoute("G1 getattr dispatch", seen_by_the_walk=False, closed_on_the_page=True),
    RoundMarkRoute("D1 typed dingbat", seen_by_the_walk=False, closed_on_the_page=True),
    RoundMarkRoute("L1 line fan", seen_by_the_walk=False, closed_on_the_page=True),
    RoundMarkRoute("PT1 point loop", seen_by_the_walk=False, closed_on_the_page=True),
    RoundMarkRoute("BM1 bound method", seen_by_the_walk=False, closed_on_the_page=True),
)

#: The two routes the walk *does* see, kept beside the six so the composite
#: predicate above is shown to be able to complain at all. Without them
#: "the walk is blind to every named limit" would be a claim about a predicate
#: that might simply never fire.
SEEN_BY_THE_WALK = ("ellipse", "polygon")

#: AC-3's four spellings of one glyph: a circle drawn as a circle, as a
#: polyline fan, as a loop of points, and as a many-sided polygon.
SPELLINGS = ("ellipse", "polygon", "L1 line fan", "PT1 point loop")


# ==========================================================================
# AC-1 — the three routes a static walk cannot see die on the page
# ==========================================================================


class TestRoundMarkOnThePage_CatchesWhatTheWalkCannotSee:
    """AC-1: cycle 3's three survivors, planted on a real page and caught.

    ``draw.line`` as a ray fan, a loop of in-bound ``draw.point`` calls, and a
    draw method held in a local and called as a bare name. Each landed a
    complete second three-dot glyph in ``src/nonogram/export/png.py`` with 548
    tests green during CARD-228's third review cycle; each is planted here into
    the band of every page a real book prints, and the guard reports it.

    **Planted and reverted, in the same process.** :func:`_interior_ink`
    restores both module attributes in a ``finally``, and
    :meth:`test_reverting_the_plant_leaves_the_book_clean` plants, asserts both
    attributes are the originals again, and only then measures the unplanted
    book — in that order inside the test itself, not by declaration order — so
    "the plant is what the guard saw" is checked rather than asserted.

    What makes this a pairing and not a single-sided claim: every route here
    comes back with **no complaint** from CARD-228's own walk
    (:meth:`TestRoundMarkOnThePage_TheNamedLimitsListShrinksHonestly.test_the_walk_really_is_blind_to_every_route_in_the_table`),
    so the page is catching exactly what the syntax could not.
    """

    SURVIVORS = ("L1 line fan", "PT1 point loop", "BM1 bound method")

    @pytest.mark.parametrize("route", SURVIVORS)
    def test_a_survivor_of_the_static_walk_is_caught_on_the_page(self, route: str) -> None:
        ink = _book_ink(route)
        assert ink.plants >= 6, (
            f"the {route} plant never landed ({ink.plants} bands drawn) — this "
            "test would then be measuring an unplanted book"
        )
        assert ink.declared == (), (
            "a rogue route must declare nothing: these dots never go through "
            f"the one drawing site, yet {len(ink.declared)} were declared"
        )
        assert len(ink.found) >= 2 * ink.plants, (
            f"{route} drew {ink.plants} glyphs of {_rank(PLANTED_TIER)} filled "
            f"dots each, so at least {2 * ink.plants} round marks were expected, "
            f"found {len(ink.found)}"
        )
        assert ink.unaccounted == ink.found, (
            "every one of them is undeclared, so every one of them is the "
            "guard's verdict"
        )

    @pytest.mark.parametrize("route", SURVIVORS)
    def test_the_walk_lets_the_same_route_through(self, route: str) -> None:
        """The other half: the instrument that cannot see it, on the same source."""
        assert _static_walk_complaints(PLANTS[route]) == []

    def test_reverting_the_plant_leaves_the_book_clean(self) -> None:
        """The revert half of plant-and-revert: the book itself carries nothing.

        The order is part of the property, so this test plants **first** and
        measures the clean book afterwards, here, rather than relying on
        :data:`_MEASURED` being warm and on pytest's declaration order: run
        alone with ``-k reverting``, the first version of this test measured a
        book that had never been planted (cycle 1, F-008). The clean
        measurement is taken fresh for the same reason.

        The restore is asserted too, against the attributes captured at
        import. A ``finally`` that stopped firing would leave ``_set_band``
        wrapped, and that is what makes ``found == ()`` below more than a
        tautology — the old ``plants == 0`` was one, since an unplanted render
        never wraps ``_set_band`` at all.
        """
        planted = _book_ink("ellipse")
        assert planted.plants >= 6, (
            f"the plant never landed ({planted.plants} bands drawn), so there "
            "is nothing here for the revert to have undone"
        )
        assert planted.unaccounted, "and the guard did report it"
        assert book_pdf_generator._set_band is _UNHOOKED_SET_BAND, (
            "the plant's hook on _set_band was not restored"
        )
        assert book_pdf_generator._draw_difficulty_dots is _UNHOOKED_SITE, (
            "the declaring spy on the one drawing site was not restored"
        )
        ink = _interior_ink()
        assert ink.found == ()
        assert ink.unaccounted == ()


# ==========================================================================
# CARD-243 — AC-1: and it sees the greys the book actually prints
# ==========================================================================


def _flat_tones(sources: Mapping[str, str]) -> dict[tuple[str, str], int]:
    """Every flat grey tone ``sources`` names, as ``{(module, name): level}``.

    The authority :data:`~tests.helpers.round_ink.MARK_LEVEL` is derived from
    (ADR-0039/R2: a guard's number comes from something the runtime can
    enumerate, not from a literal somebody chose). A **flat tone** is a
    module-level assignment of a three-tuple of *equal* integers in 0..255 —
    which is what this package's palette is made of, and is what
    ``book_pdf_generator``'s own module docstring says it draws: ``INK =
    (0, 0, 0)`` on ``BACKGROUND = (255, 255, 255)`` and nothing else, plus the
    one grey a solved page rules its cells in.

    Equal components, not "three small ints": the package also carries
    ``GUIDE_BASIC_RULE_CLUE = (3, 2, 1)``, which is a nonogram clue and not a
    colour at all. That exclusion is a *measured* one rather than a name on a
    list — ``test_the_tone_walk_reads_colours_and_not_every_triple`` is its
    control — and the residue it leaves is stated with the rest: a mark painted
    in a tone the package names as an *unequal* triple is outside this
    enumeration, which is the ``colour`` bound one level up.

    Takes its sources as an argument, the shape every other walk in this file
    has, so it can be run over a fabricated module.
    """
    found: dict[tuple[str, str], int] = {}
    for module, source in sources.items():
        for node in ast.parse(source).body:
            if isinstance(node, ast.Assign):
                targets = [t for t in node.targets if isinstance(t, ast.Name)]
                value = node.value
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                targets, value = [node.target], node.value
            else:
                continue
            if not isinstance(value, ast.Tuple) or len(value.elts) != 3:
                continue
            try:
                parts = [ast.literal_eval(element) for element in value.elts]
            except ValueError:
                continue
            if not all(isinstance(part, int) and 0 <= part <= 255 for part in parts):
                continue
            if len(set(parts)) != 1:
                continue
            for target in targets:
                found[(module, target.id)] = parts[0]
    return found


class TestRoundMarkOnThePage_SeesTheGreysTheBookPrints:
    """CARD-243 AC-1: the glyph in the book's own grey dies on the page.

    CARD-241's instrument read **ink**, and ink was a hard threshold at grey
    128. The package draws its solved grid at
    :data:`~nonogram.admin.book_pdf_generator._SOLVED_GRID_GRAY`, grey 160 —
    *lighter* than that — so a difficulty dot stroked in the book's own grey
    had no region, no ``aspect`` and no ``fill``, and ADR-0036/R3's declared
    check passed green with it printed on the page. Measured at CARD-241's
    review cycle 1 (F-001) and reproduced here as the pairing both halves of
    this class assert.

    Two routes are planted, because the two are not equally open:

    * **GY1 grey ellipse** — the book's grey in the one spelling CARD-228's
      static walk *does* see. Open to the render check alone.
    * **GY2 grey bound method** — the same grey through ``stamp =
      draw.ellipse``, which is CARD-228's mutant BM1 and which no walk
      records. Open to **both** instruments, which is the residue
      ADR-0036/R3's own comment named and this card closes.

    **The card's contribution is measured, not asserted.** One render is
    measured at both thresholds (:data:`~tests.helpers.round_ink.INK_LEVEL`
    and :data:`~tests.helpers.round_ink.MARK_LEVEL`), so "the black-ink
    instrument misses this plant and the widened one catches it" is two
    readings of the same ink rather than a quotation from a review report.
    """

    @pytest.mark.parametrize("route", GREY_ROUTES)
    def test_a_glyph_in_the_books_own_grey_is_caught_on_the_page(
        self, route: str
    ) -> None:
        ink = _book_ink(route)
        assert ink.plants >= 6, (
            f"the {route} plant never landed ({ink.plants} bands drawn) — this "
            "test would then be measuring an unplanted book"
        )
        assert ink.declared == (), (
            "a rogue route must declare nothing: these dots never go through "
            f"the one drawing site, yet {len(ink.declared)} were declared"
        )
        assert len(ink.found) >= 2 * ink.plants, (
            f"{route} drew {ink.plants} glyphs of {_rank(PLANTED_TIER)} filled "
            f"dots each, so at least {2 * ink.plants} round marks were expected, "
            f"found {len(ink.found)}"
        )
        assert ink.unaccounted == ink.found, (
            "every one of them is undeclared, so every one of them is the "
            "guard's verdict"
        )

    @pytest.mark.parametrize("route", GREY_ROUTES)
    def test_the_black_ink_only_instrument_misses_the_same_plant(
        self, route: str
    ) -> None:
        """The other half of AC-1: the same render, read at CARD-241's threshold.

        Not a second plant and not a second render — the same pages, measured
        twice. At :data:`~tests.helpers.round_ink.INK_LEVEL` the grey glyph is
        not ink, so there is no region at all for the accounting to consider;
        at :data:`~tests.helpers.round_ink.MARK_LEVEL` every filled dot of it
        is a round mark nobody declared. That difference is this card.
        """
        ink = _book_ink(route)
        black = ink.at[INK_LEVEL]
        widened = ink.at[MARK_LEVEL]
        assert ink.plants >= 6
        assert black.found == (), (
            "CARD-241's black-ink instrument is supposed to miss this plant "
            f"entirely; it found {len(black.found)} round marks"
        )
        assert widened.found != (), "and the widened one is supposed to find it"
        assert widened.regions > black.regions, (
            "the grey glyph is ink to the widened threshold and paper to the "
            f"black one, so it must add regions: {black.regions} -> "
            f"{widened.regions}"
        )

    def test_the_two_grey_routes_differ_only_in_what_the_walk_can_see(self) -> None:
        """Why GY2 is the route that mattered: no instrument saw it before.

        Derived by execution on both sides. CARD-228's walk complains about
        GY1 (it is a plain ``draw.ellipse`` call) and is silent about GY2 (the
        method is reached through a local), while the widened page check
        catches both — so GY2 is the mark that was open to the *union* of
        ADR-0036/R3's two instruments, and GY1 is the control proving the
        walk's own predicate can fire on an identically-coloured glyph.
        """
        walk = {
            route: _static_walk_complaints(PLANTS[route]) != [] for route in GREY_ROUTES
        }
        assert walk == {"GY1 grey ellipse": True, "GY2 grey bound method": False}, walk
        page = {route: _book_ink(route).unaccounted != () for route in GREY_ROUTES}
        assert page == {"GY1 grey ellipse": True, "GY2 grey bound method": True}, page

    def test_the_grey_is_the_books_own_and_not_a_number_chosen_here(self) -> None:
        """G-3: the plant's colour is the production constant, and it straddles.

        The route only exists because ``_SOLVED_GRID_GRAY`` sits *between* the
        two thresholds. Both halves are asserted against the production value,
        so a card that darkened the solved grid below
        :data:`~tests.helpers.round_ink.INK_LEVEL`, or lightened it past
        :data:`~tests.helpers.round_ink.MARK_LEVEL`, reds this test instead of
        quietly making the pairing above vacuous.
        """
        assert min(_SOLVED_GRID_GRAY) > INK_LEVEL, (
            "the solved grid is no longer lighter than CARD-241's ink level, so "
            f"there is nothing for this card to close: {_SOLVED_GRID_GRAY}"
        )
        assert max(_SOLVED_GRID_GRAY) < MARK_LEVEL, (
            "the solved grid is no longer darker than the widened threshold, so "
            f"the route this card closes is not closed: {_SOLVED_GRID_GRAY}"
        )

    def test_the_mark_level_is_the_midpoint_of_the_palette_the_package_draws(
        self,
    ) -> None:
        """AC-3/ADR-0039/R2: the threshold is derived, not chosen.

        The package's palette is enumerated off disk — every module-level flat
        grey tone in ``src/nonogram/**`` — and the threshold is recomputed from
        it: the midpoint between the lightest tone that is **not** paper and
        paper itself, rounded up so the darker side of that gap is a mark and
        paper is not. Today that is ``ceil((160 + 255) / 2) = 208``.

        Which means a production module that starts drawing in a lighter tone
        reds this test rather than quietly escaping the measurement, and that
        is the completeness half ADR-0039/R1 asks for: the number is only as
        good as the claim that 160 is the lightest tone the book prints, and
        the claim is enumerated rather than asserted.
        """
        tones = _flat_tones(_package_sources())
        assert tones, "the tone walk found no palette at all"
        levels = sorted(set(tones.values()))
        assert levels == [0, max(_SOLVED_GRID_GRAY), 255], (
            "the package's palette has changed, so the threshold derived from "
            f"it has to be recomputed: {sorted(tones.items())}"
        )
        paper = max(levels)
        lightest_mark = max(level for level in levels if level != paper)
        assert lightest_mark == max(_SOLVED_GRID_GRAY), lightest_mark
        assert MARK_LEVEL == -(-(lightest_mark + paper) // 2), (
            f"MARK_LEVEL is {MARK_LEVEL}; the palette the package draws "
            f"({levels}) puts the midpoint of the gap between its lightest "
            f"mark and paper at {-(-(lightest_mark + paper) // 2)}"
        )
        assert lightest_mark < MARK_LEVEL <= paper, (levels, MARK_LEVEL)

    def test_the_tone_walk_reads_colours_and_not_every_triple(self) -> None:
        """Controls for the enumeration above, both directions.

        A derivation is only as good as what its walk can and cannot see, and
        this one has a live false positive to exclude: the package carries
        ``GUIDE_BASIC_RULE_CLUE = (3, 2, 1)``, a nonogram clue. It is excluded
        because its components are unequal — a measured property, not a name
        on a list — and the exclusion is checked on the real package rather
        than on a fabricated module. The other direction is the control that
        the walk can find a tone at all, including a *lighter* one, which is
        the case the derivation above would have to move for.
        """
        real = _flat_tones(_package_sources())
        assert ("nonogram.admin.book_pdf_generator", "_SOLVED_GRID_GRAY") in real
        assert ("nonogram.export.png", "INK") in real
        assert ("nonogram.export.png", "BACKGROUND") in real
        assert not any(name == "GUIDE_BASIC_RULE_CLUE" for _, name in real), (
            "a nonogram clue is being read as a colour: " f"{sorted(real)}"
        )
        fabricated = _flat_tones(
            {
                "planted.module": (
                    "HINT = (230, 230, 230)\n"
                    "CLUE = (3, 2, 1)\n"
                    "TINT: tuple[int, int, int] = (200, 200, 200)\n"
                    "NOT_A_COLOUR = (300, 300, 300)\n"
                    "def f():\n    LOCAL = (90, 90, 90)\n"
                )
            }
        )
        assert fabricated == {
            ("planted.module", "HINT"): 230,
            ("planted.module", "TINT"): 200,
        }, fabricated

    def test_reverting_the_grey_plant_leaves_the_book_clean(self) -> None:
        """Plant-and-revert for the grey route, in this process and in order.

        The same shape
        :meth:`TestRoundMarkOnThePage_CatchesWhatTheWalkCannotSee.test_reverting_the_plant_leaves_the_book_clean`
        has, and for the same reason: run alone, this must plant first and
        measure the clean book afterwards rather than rely on a warm
        :data:`_MEASURED` and pytest's declaration order (CARD-241 cycle 1,
        F-008).
        """
        planted = _book_ink("GY1 grey ellipse")
        assert planted.plants >= 6, (
            f"the plant never landed ({planted.plants} bands drawn), so there "
            "is nothing here for the revert to have undone"
        )
        assert planted.unaccounted, "and the guard did report it"
        assert book_pdf_generator._set_band is _UNHOOKED_SET_BAND, (
            "the plant's hook on _set_band was not restored"
        )
        assert book_pdf_generator._draw_difficulty_dots is _UNHOOKED_SITE, (
            "the declaring spy on the one drawing site was not restored"
        )
        ink = _interior_ink()
        assert ink.found == ()
        assert ink.unaccounted == ()


# ==========================================================================
# AC-2 — and it passes on the book the project really prints
# ==========================================================================

#: The seeded picture corpus AC-2 sweeps, and the two floors it must clear
#: (CLAUDE.md: no ``hypothesis``, a corpus with its minimum asserted inside the
#: test so it cannot silently shrink). The second floor is the load-bearing
#: one: a corpus of blank grids would satisfy the first and measure nothing.
PICTURE_SEED = 241
PICTURE_MIN_PAGES = 18
PICTURE_MIN_CELLS = 400

#: And CARD-243's third floor: how many pixels of this corpus are paper to
#: :data:`INK_LEVEL` and a mark to :data:`MARK_LEVEL`. 265 543 when measured,
#: nearly all of it the solved pages' grey grid — the one place in the suite
#: where the widened threshold meets the production grey in bulk rather than
#: in a plant.
PICTURE_MIN_WIDENED_PIXELS = 200_000


def _picture_puzzles() -> list[dict]:
    """Nine puzzles whose answers are pictures, not the gutter-depth pattern.

    ``tests/helpers/book_corpus.py``'s corpora are built from
    ``_gutter_grid`` — every other cell filled, so **no two filled cells ever
    touch**, which is exactly the case that cannot produce a blob. The risk
    this sweep exists for is the opposite one: a *solved* page draws its filled
    cells, and a picture whose filled cells happen to form a round-ish blob
    would be a round mark nobody declared.

    So: seeded random grids at three densities, plus one grid that is
    deliberately the worst case — a disc of filled cells, the roundest picture
    a nonogram can hold. Built here rather than in ``book_corpus`` because the
    shape of the dict is all that is shared, and because an independent second
    construction is this project's preference (CLAUDE.md).
    """
    rng = random.Random(PICTURE_SEED)
    grids: list[list[list[bool]]] = []
    for _ in range(8):
        side = rng.choice((10, 12, 15))
        density = rng.choice((0.3, 0.5, 0.7))
        grids.append([[rng.random() < density for _ in range(side)] for _ in range(side)])
    side = 15
    middle = (side - 1) / 2
    grids.append(
        [
            [(x - middle) ** 2 + (y - middle) ** 2 <= 5.5**2 for x in range(side)]
            for y in range(side)
        ]
    )
    tiers = ("easy", "medium", "hard")
    puzzles: list[dict] = []
    for index, grid in enumerate(grids):
        found = clues.compute_clues(grid)
        puzzles.append(
            {
                "id": f"card241-picture-{index + 1}",
                "grid": grid,
                "clues_rows": [list(clue) for clue in found.rows],
                "clues_cols": [list(clue) for clue in found.columns],
                "width": len(grid[0]),
                "height": len(grid),
                "puzzle_name": f"Picture {index + 1}",
                "difficulty_tier": tiers[index * len(tiers) // len(grids)],
            }
        )
    return puzzles


class TestRoundMarkOnThePage_PassesOnTheRealBook:
    """AC-2: on the pages the book really produces, the guard is quiet.

    Paired with AC-1 on purpose: a guard that fires on everything would pass
    AC-1 and be worthless. These pages carry every mark a book page is made of
    — the grid's rules, a page frame, the folio, the placeholder QR icon's
    checkerboard, the guide's pipeline diagram with the arrow head it strokes
    as a three-vertex polygon, every word of every header and of both guide
    pages, and a solved page's filled answer cells — and not one of them
    measures round.

    **At both thresholds** (CARD-243). The pages are read at
    :data:`INK_LEVEL` and at :data:`MARK_LEVEL`, and the guard is quiet at
    each — so the widening that makes the book's own grey visible does not
    make the book's own grey a defect. That is not a statement about a book
    with no grey on it: :attr:`BookInk.widened_pixels` counts the pixels the
    widening added and is asserted to clear a floor on both corpora, and the
    picture corpus carries the grey *solved grid* in bulk, over 160 000 pixels
    of it.

    **With a measured margin, not by luck — and it moved when the threshold
    did.** The closest any region comes to being round is
    :attr:`LevelInk.margin`, in units of the tolerance that binds it:
    **1.8859** at the black threshold, carried by ``fill`` alone on a 99 x 94
    filled block at ``(144, 1266, 242, 1359)`` (``aspect`` 1.0532 — already
    inside :data:`ROUND_ASPECT_TOLERANCE`); **1.8182** at the widened one,
    carried by ``aspect`` on a 7 x 11 letter stem at
    ``(2181, 477, 2187, 487)`` (``fill`` 0.8599, outside its tolerance too).
    Both numbers, both boxes and *which* tolerance carries each are asserted
    in :meth:`test_the_closest_the_book_comes_to_a_round_mark_is_measured`,
    and each tolerance's own room is measured separately in
    :meth:`test_each_tolerances_own_room_on_the_book_is_measured` — because
    the margin is whichever binds first and that hides the other (CARD-241
    cycle 1, F-003, where the 2.27 quoted here was the letter-stem family's
    aspect room and not the closest mark at all).

    Every floor sits just under its measured value, so a future page whose ink
    drifts towards roundness reds a test *before* it reds the guard.
    """

    def test_the_books_own_pages_carry_no_undeclared_round_mark(self) -> None:
        """ADR-0036/R3's declared check, now asked at both thresholds."""
        ink = _book_ink(None)
        assert ink.pages >= 13, f"the baseline interior lost pages: {ink.pages}"
        for level in MEASURED_LEVELS:
            assert ink.at[level].regions >= 3000, (
                f"only {ink.at[level].regions} regions on {ink.pages} pages at "
                f"level {level} — these pages have stopped carrying the marks "
                "this test exists to tolerate"
            )
            assert ink.at[level].found == (), (
                f"at level {level} the book's own pages carry round marks "
                f"nobody drew through the one site: {ink.at[level].found[:4]}"
            )
        assert ink.unaccounted == ()
        assert ink.widened_pixels >= 50_000, (
            "the baseline interior has nearly no pixels between the two "
            "thresholds, so passing at the wider one says nothing about a wider "
            f"population: {ink.widened_pixels} (76347 when measured)"
        )

    def test_the_closest_the_book_comes_to_a_round_mark_is_measured(self) -> None:
        """The margin at **both** thresholds, and which tolerance carries each.

        Re-measured for CARD-243 rather than inherited, because the widened
        threshold brings the book's own greys and every glyph's anti-aliased
        edge into the population the margin is taken over. What it comes to:

        * at :data:`INK_LEVEL`, **1.8859** on the 99 x 94 filled block at
          ``(144, 1266, 242, 1359)``, ``aspect`` 1.0532 and ``fill`` 1.2263 —
          CARD-241's figure, to four places, on this head. The widening does
          not move it, which is the point of keeping the reading;
        * at :data:`MARK_LEVEL`, **1.8182**, and the closest mark is a
          *different* one: a 7 x 11 letter stem at ``(2181, 477, 2187, 487)``,
          ``aspect`` 0.6364, ``fill`` 0.8599. It is the same stem family that
          was 6 x 11 at the black threshold, one pixel wider for its own grey
          edge — and at that width its ``fill`` leaves the fill tolerance, so
          the number is now carried by ``aspect``.

        Both halves matter and neither is a conclusion drawn from the other:
        the margin *moved* (down 0.068, by 3.6 %) and *changed hands*. The
        floor stays at 1.8, just under the measured 1.8182, for the reason
        CARD-241 set it there: a floor at 1.5 would let the margin fall by a
        fifth in silence (cycle 1, F-003).
        """
        ink = _book_ink(None)
        black, widened = ink.at[INK_LEVEL], ink.at[MARK_LEVEL]
        for level in (black, widened):
            assert level.margin >= 1.8, (
                f"the roundest mark on the book's pages at level {level.level} "
                f"is now {level.margin:.4f} tolerances from round; it was "
                "1.8859 at the black threshold and 1.8182 at the widened one "
                "when they were set, and under 1.0 it would be a false positive"
            )
            assert level.closest is not None, "a book with no region to measure"
        # CARD-241's reading, unchanged by the widening: the same block, the
        # same number, still carried by `fill` alone.
        assert black.closest.box == (144, 1266, 242, 1359), black.closest
        assert black.margin == pytest.approx(1.8859, abs=5e-4), black.margin
        assert abs(black.closest.fill - 1.0) / ROUND_FILL_TOLERANCE == pytest.approx(
            black.margin
        ), (
            "the black threshold's margin is no longer carried by fill: the "
            f"closest mark is {black.closest.box}, aspect "
            f"{black.closest.aspect:.4f}, fill {black.closest.fill:.4f}"
        )
        assert abs(black.closest.aspect - 1.0) <= ROUND_ASPECT_TOLERANCE, (
            "at the black threshold the closest mark is a near-square filled "
            "block whose footprint is already inside the aspect tolerance; it "
            f"is now {black.closest.box} at aspect {black.closest.aspect:.4f}"
        )
        # And the widened reading, which is the guard's own: a different mark,
        # a smaller margin, and the other tolerance carrying it.
        assert widened.closest.box == (2181, 477, 2187, 487), widened.closest
        assert widened.margin == pytest.approx(1.8182, abs=5e-4), widened.margin
        assert widened.margin < black.margin, (
            "the widened threshold is supposed to bring more ink into the "
            "population, so the margin can only shrink or stay; it grew from "
            f"{black.margin:.4f} to {widened.margin:.4f}"
        )
        assert abs(
            widened.closest.aspect - 1.0
        ) / ROUND_ASPECT_TOLERANCE == pytest.approx(widened.margin), (
            "the widened threshold's margin is no longer carried by aspect: "
            f"the closest mark is {widened.closest.box}, aspect "
            f"{widened.closest.aspect:.4f}, fill {widened.closest.fill:.4f}"
        )
        assert abs(widened.closest.fill - 1.0) > ROUND_FILL_TOLERANCE, (
            "the widened threshold's closest mark used to be clear of BOTH "
            "tolerances, unlike the black threshold's; it is now "
            f"{widened.closest.box} at fill {widened.closest.fill:.4f}, so the "
            "account above is stale"
        )

    def test_each_tolerances_own_room_on_the_book_is_measured(self) -> None:
        """AC-3: what the wider ink population does to each tolerance's room.

        The margin above is whichever tolerance binds *first*. This is the
        other question, asked separately for each: how far could **this**
        tolerance grow before some region the other one already admits turns
        round? Measured over the same pages at both thresholds:

        ======================  ==========  ============  ==============
        tolerance               at 128      at 208        set by
        ======================  ==========  ============  ==============
        ``ROUND_FILL``          1.8859      1.8859        the 99 x 94 block
        ``ROUND_ASPECT``        2.2727      47.1809       a letter stem / a rule
        ======================  ==========  ============  ==============

        So the widening leaves ``fill``'s room on the book **exactly where
        CARD-241 measured it** — the 99 x 94 filled block is a hard-edged
        rectangle and has no grey edge to grow by — and it *widens*
        ``aspect``'s, from 2.27 to 47.18, because the letter stem that used to
        sit 2.27 tolerances out with a disc's ``fill`` grew a grey pixel and
        left the fill tolerance altogether. Both tolerances therefore keep
        their values because the measurement says so, which is the outcome
        AC-3 allows; what moved is recorded here rather than in a docstring.
        """
        ink = _book_ink(None)
        black, widened = ink.at[INK_LEVEL], ink.at[MARK_LEVEL]
        assert black.fill_headroom == pytest.approx(1.8859, abs=5e-4), black
        assert widened.fill_headroom == pytest.approx(1.8859, abs=5e-4), widened
        assert black.fill_closest.box == (144, 1266, 242, 1359), black.fill_closest
        assert widened.fill_closest.box == (144, 1266, 242, 1359), widened.fill_closest
        assert black.aspect_headroom == pytest.approx(2.2727, abs=5e-4), black
        assert widened.aspect_headroom == pytest.approx(47.1809, abs=5e-4), widened
        assert widened.aspect_headroom > black.aspect_headroom, (
            "the aspect tolerance's room on the book is measured to WIDEN at "
            "the lighter threshold, because the letter stem that set it grows "
            "a grey pixel and leaves the fill tolerance; it now reads "
            f"{widened.aspect_headroom:.4f} against {black.aspect_headroom:.4f}"
        )

    def test_the_glyph_the_one_site_draws_is_found_and_accounted_for(self) -> None:
        """The discrimination: the same ink, declared, passes.

        The one drawing site draws the same glyph in the same places as every
        rogue route of AC-1, and the guard finds exactly the same round marks —
        and then accounts for every one of them, page and box, against what the
        site itself said it drew. So the guard separates *declared* from
        *undeclared*, which is the only thing it claims, rather than separating
        "plant" from "no plant".
        """
        ink = _book_ink("the declared site")
        assert ink.plants >= 6
        assert len(ink.declared) == ink.plants * _rank(PLANTED_TIER)
        assert len(ink.found) == len(ink.declared)
        assert sorted(ink.found) == sorted(ink.declared), (
            "the ink a stroked dot leaves is exactly its declared box, on the "
            "page it was declared on, which is what lets the accounting match "
            "exactly rather than within a tolerance — or across pages — a "
            "rogue mark could hide in"
        )
        assert ink.unaccounted == ()

    def test_the_accounting_is_an_exact_multiset(self) -> None:
        """The three properties :func:`_unaccounted` claims, on their own.

        Measured on the function rather than through a render, because each is
        about what a *rogue* mark could hide behind and none is exercised by
        the honest book (where every declared dot is distinct and every found
        mark matches one exactly):

        * a **multiset**: a second round mark at a declared box is one mark
          more than was declared, so it is reported;
        * **exact**: a mark one pixel off a declared box is reported, so a
          tolerance cannot be borrowed to sit beside a declared dot;
        * **per page**: a mark at a declared box on *another* page is reported.
          Every page's band geometry is identical, so without this the guard
          would let a rogue mark on page 11 be paid for by a declared dot on
          page 4 whose own mark was not found (cycle 1, F-009).
        """
        dot = (4, (10, 10, 51, 51))
        assert _unaccounted([dot], [dot]) == ()
        assert _unaccounted([dot, dot], [dot]) == (dot,)
        beside = (4, (11, 11, 52, 52))
        assert _unaccounted([beside], [dot]) == (beside,)
        assert _unaccounted([], [dot]) == ()
        elsewhere = (11, (10, 10, 51, 51))
        assert _unaccounted([elsewhere], [dot]) == (elsewhere,), (
            "the same box on another page is another mark, and nothing on "
            "page 4 pays for it"
        )
        assert _unaccounted([elsewhere], [elsewhere]) == ()

    def test_a_seeded_corpus_of_pictures_draws_no_round_mark(self) -> None:
        """The answer pages' own risk: a filled picture that is round-ish.

        Nine pictures, eight seeded random grids and one deliberate disc of
        filled cells, through the real export. This is the corpus that carries
        the grey this card is about in bulk — a solved page rules its answer
        cells in ``_SOLVED_GRID_GRAY``, which is a quarter of a million pixels
        the black threshold reads as paper.

        **And that is why the reason this sweep passes had to be re-measured.**
        CARD-241's account of it was that the grey grid, being lighter than
        :data:`~tests.helpers.round_ink.INK_LEVEL`, keeps neighbouring filled
        cells in separate regions so a picture never becomes one blob. At
        :data:`~tests.helpers.round_ink.MARK_LEVEL` that is no longer true —
        the grey rules *are* a mark, so a picture's filled cells and the whole
        grid's lattice merge, and the corpus comes back with **fewer** regions
        than before (4236 at the black threshold, 4087 at the widened one). It
        still comes back clean, and for a different reason: what the cells merge
        into is the grid's whole square lattice, far too sparse to read as a
        disc. Both readings are asserted, so the day either stops holding a
        test says which.
        """
        ink = _interior_ink(None, _picture_puzzles())
        assert ink.pages >= PICTURE_MIN_PAGES, (
            f"the picture corpus made only {ink.pages} pages"
        )
        cells = sum(sum(row) for puzzle in _picture_puzzles() for row in puzzle["grid"])
        assert cells >= PICTURE_MIN_CELLS, (
            f"the corpus holds only {cells} filled cells — too few for the blob "
            "this sweep is looking for to be possible at all"
        )
        assert ink.widened_pixels >= PICTURE_MIN_WIDENED_PIXELS, (
            "the corpus no longer carries the grey solved grid in bulk, so it "
            "is no longer the corpus that exercises the widened threshold: "
            f"{ink.widened_pixels} pixels between the two levels"
        )
        for level in MEASURED_LEVELS:
            assert ink.at[level].found == (), (
                f"at level {level} the picture corpus carries round marks: "
                f"{ink.at[level].found[:4]}"
            )
        assert ink.unaccounted == ()
        assert ink.at[MARK_LEVEL].regions < ink.at[INK_LEVEL].regions, (
            "the grey rules are supposed to join the filled cells into one "
            "lattice at the widened threshold, which can only reduce the "
            f"region count: {ink.at[INK_LEVEL].regions} -> "
            f"{ink.at[MARK_LEVEL].regions}"
        )


# ==========================================================================
# AC-3 — the verdict does not depend on how the glyph is spelled
# ==========================================================================


class TestRoundMarkOnThePage_SameVerdictForEverySpelling:
    """AC-3: one glyph, four spellings, one verdict — because this reads ink.

    An ellipse, a 32-gon, a 240-ray ``draw.line`` fan and a loop of
    ``draw.point`` calls, each drawing **the same dots in the same boxes**
    (:func:`_planted_dots`). CARD-228's walk complains about two of the four
    and is silent about the other two; the page cannot tell them apart at all,
    which is the whole point of changing instrument.
    """

    def test_every_spelling_is_caught(self) -> None:
        for route in SPELLINGS:
            ink = _book_ink(route)
            assert ink.unaccounted, f"{route} was not caught"

    def test_every_spelling_is_caught_the_same_number_of_times(self) -> None:
        counts = {route: len(_book_ink(route).unaccounted) for route in SPELLINGS}
        assert len(set(counts.values())) == 1, counts

    def test_every_spelling_is_caught_in_the_same_places(self) -> None:
        """Within a pixel, which is all four spellings' own rounding.

        The fan and the point loop step round their dot's centre in integers
        while ``ellipse`` and ``polygon`` take the box, so a dot can come out a
        pixel narrower. The *instrument* does not vary: the pages it reports
        are the same pages, and the boxes agree to a pixel on every edge.
        """
        marks = {route: sorted(_book_ink(route).unaccounted) for route in SPELLINGS}
        reference = marks[SPELLINGS[0]]
        for route, found in marks.items():
            assert len(found) == len(reference), (route, len(found), len(reference))
            for (my_page, mine), (their_page, theirs) in zip(found, reference):
                assert my_page == their_page, (route, my_page, their_page)
                assert all(abs(a - b) <= 1 for a, b in zip(mine, theirs)), (
                    route,
                    mine,
                    theirs,
                )

    def test_the_walk_sees_two_of_the_four_and_the_page_sees_all_four(self) -> None:
        """The contrast, stated as a measurement rather than as a conclusion."""
        walk = {route: _static_walk_complaints(PLANTS[route]) != [] for route in SPELLINGS}
        page = {route: _book_ink(route).unaccounted != () for route in SPELLINGS}
        assert set(walk.values()) == {True, False}, walk
        assert set(page.values()) == {True}, page

    def test_a_typed_dot_measures_the_same_as_a_stroked_one(self) -> None:
        """A ``chr(0x25CF)`` set as type is the same mark as a stroked disc.

        The fifth spelling, and the one CARD-228 judged the cheapest route a
        later card could take. Measured here rather than asserted: the typed
        dot's own ink reads as round, and the face size
        :func:`_rogue_typed_dingbat` picks lands it within a few pixels of the
        diameter the glyph would have stroked.
        """
        ink = _book_ink("D1 typed dingbat")
        assert ink.unaccounted, "a typed dot is a round mark and must be caught"
        stroked = _book_ink("ellipse")
        widths = {box[2] - box[0] + 1 for _, box in ink.unaccounted}
        expected = {box[2] - box[0] + 1 for _, box in stroked.unaccounted}
        assert max(widths) - min(expected) <= 4 and min(widths) - max(expected) >= -4, (
            f"a typed dot measured {sorted(widths)} px across against the "
            f"stroked dot's {sorted(expected)}"
        )


# ==========================================================================
# AC-4 — the metric's own boundary, measured and stated
# ==========================================================================

#: The diameters AC-4 sweeps a disc over: every one from a single pixel to a
#: dot as tall as a book page's whole band, and the minimum the sweep must hold
#: so it cannot shrink. It starts at **1** and not at :data:`MIN_DOT_PX` on
#: purpose: the region below the glyph's own smallest dot is exactly where the
#: metric's own resolution floor lives, and a sweep that began above it could
#: not fail there (cycle 1, F-002).
DISC_SWEEP_SEED = 241
DISC_SWEEP_MIN_CASES = 120

#: What a filled disc measures at each diameter *below* :data:`MIN_DOT_PX`:
#: ``True`` round, ``False`` not round, ``None`` no ink at all. Recorded from
#: the measurement so the metric's floor is asserted rather than incidental
#: (:meth:`TestRoundMarkOnThePage_TheBoundaryIsMeasured.test_the_metrics_own_size_floor_is_where_the_raster_puts_it`).
#: The shape of the table is the finding: the verdict is **not** monotone in
#: the diameter below 7 px, so "too small to be seen" is not something one
#: number describes.
DISC_VERDICT_BELOW_THE_SMALLEST_DOT: Mapping[int, bool | None] = {
    1: None,
    2: False,
    3: False,
    4: True,
    5: True,
    6: False,
    7: True,
    8: True,
    9: True,
    10: True,
    11: True,
}

#: The diameter from which a filled disc measures round at every diameter
#: measured, up to the 142 px band.
DISC_FLOOR_PX = 7


def _disc_sweep() -> list[int]:
    """Diameters to measure a disc at: every pixel to 60, then seeded samples.

    Stdlib :class:`random.Random`, no ``hypothesis`` (CLAUDE.md). The dense
    head is where a disc is least circular — at 12 px a circle is a hundred
    pixels of staircase, and under 7 px it stops reading as a circle at all —
    and the seeded tail reaches the 142 px band.
    """
    rng = random.Random(DISC_SWEEP_SEED)
    diameters = list(range(1, 61))
    diameters += [rng.randrange(61, 143) for _ in range(80)]
    return diameters


class TestRoundMarkOnThePage_TheBoundaryIsMeasured:
    """AC-4: where "round" stops, stated as a verdict and justified by a measurement.

    Both tolerances are the midpoint of a **measured gap**, and every number
    below comes out of a rendered shape rather than out of a constant:

    ===========================  ===============  =============
    shape                        ``fill``         verdict
    ===========================  ===============  =============
    disc, any diameter 12..142   0.96 .. 1.01     round
    disc, 7..11 px               0.96 .. 1.03     round
    disc, 4 and 5 px             0.95 / 1.07      round
    disc, 2, 3 and 6 px          1.27/0.71/0.85   **not** round
    disc, 1 px                   no ink at all    not measured
    disc in grey 160, any size   0.99             round (CARD-243)
    disc in grey 208, any size   no mark at all   not measured
    typed ``chr(0x25CF)``        0.99 .. 1.01     round
    pasted circular mask         1.04             round
    regular 16-gon               0.96 .. 0.98     round
    regular octagon              0.90 .. 0.92     round
    regular hexagon              0.93 .. 0.96     round
    regular pentagon             0.82 .. 0.87     **not** round
    square, any rotation         0.64 / 1.27      **not** round
    41 px square, 15 px corners  1.11             round
    41 px square, 14 px corners  1.13             **not** round
    ring (an outlined circle)    0.15 .. 0.28     **not** round
    ===========================  ===============  =============

    The near-round cases AC-4 names are therefore answered rather than left to
    chance: a **hexagon is caught** (it is as round as an octagon and only its
    footprint is off square, which the aspect tolerance is deliberately loose
    enough to admit), and a **rounded rectangle is caught from a corner radius
    of 15 px on a 41 px square** — the radius at which it has as little ink as
    a disc — and not below it.

    **Every shape above is re-measured at both thresholds** (CARD-243 AC-3),
    and every verdict in the table is the same at each. That is not a
    coincidence worth leaving unstated: ``ellipse``, ``polygon`` and
    ``rounded_rectangle`` do not anti-alias, so the raster a shape leaves is
    the same raster whichever threshold reads it, and the two rows that *do*
    differ are the two about tone. The grey-160 row is the one this card
    inverted — it read "no ink at all, not measured" until CARD-243 — and the
    grey-208 row is what replaced it.

    The bounds this instrument has are no longer listed here: they are
    :data:`MEASURED_MARK_BOUNDS`, one row each with a verdict derived by
    execution and a control, held to the two prose bound lists by
    :class:`TestRoundMarkOnThePage_TheBoundListShrinksHonestly`. Four of the
    controls still live in this class, where CARD-241 wrote them.
    """

    @pytest.mark.parametrize("level", MEASURED_LEVELS)
    def test_a_disc_measures_round_at_every_diameter_it_can_be_drawn(
        self, level: int
    ) -> None:
        """Every diameter the glyph itself can draw: :data:`MIN_DOT_PX` and up.

        The sweep reaches below that too; what it measures there is the
        raster's verdict rather than the shape's, and is asserted against a
        recorded table in
        :meth:`test_the_metrics_own_size_floor_is_where_the_raster_puts_it`.

        Swept at **both** thresholds (CARD-243 AC-3): ``draw.ellipse`` does
        not anti-alias, so the same raster is read either way and the recorded
        0.95..1.01 band is the measurement that says so rather than an
        assumption that it would be.
        """
        diameters = [
            diameter for diameter in _disc_sweep() if diameter >= MIN_DOT_PX
        ]
        assert len(diameters) >= DISC_SWEEP_MIN_CASES, len(diameters)
        fills = []
        for diameter in diameters:
            region = _shape(
                _disc(diameter), canvas=diameter + 2 * _SHAPE_MARGIN, level=level
            )
            assert region.aspect == 1.0, (level, diameter, region.aspect)
            assert region.is_round, (level, diameter, region.fill)
            fills.append(region.fill)
        assert 0.95 <= min(fills) and max(fills) <= 1.01, (min(fills), max(fills))

    def test_the_metrics_own_size_floor_is_where_the_raster_puts_it(self) -> None:
        """A stated bound: under 7 px the verdict is the raster's, not the shape's.

        No size floor is imposed by hand — the reason is recorded in
        ``tests/helpers/round_ink.py`` and still holds — but ``fill`` has a
        resolution of its own, and *that* is a floor. It is measured here
        rather than claimed: every diameter the sweep reaches below the glyph's
        own smallest dot is compared against
        :data:`DISC_VERDICT_BELOW_THE_SMALLEST_DOT`, recorded once from this
        measurement.

        The table is **not monotone**, which is the whole finding: a 4 px disc
        is round, a 6 px disc is not, and a 1 px ellipse inks nothing at all.
        So a mark under :data:`DISC_FLOOR_PX` may or may not be seen, and no
        single number says which — a bound this instrument has and the first
        version of its docstring denied (cycle 1, F-002).
        """
        below = sorted(
            diameter for diameter in _disc_sweep() if diameter < MIN_DOT_PX
        )
        assert below == sorted(DISC_VERDICT_BELOW_THE_SMALLEST_DOT), (
            "the sweep no longer reaches every diameter the table records, so "
            f"the floor would stop being asserted: {below}"
        )
        at_level: dict[int, dict[int, bool | None]] = {}
        for level in MEASURED_LEVELS:
            measured: dict[int, bool | None] = {}
            for diameter in below:
                regions = ink_regions(
                    _rendered(_disc(diameter), canvas=diameter + 2 * _SHAPE_MARGIN),
                    level,
                )
                if not regions:
                    measured[diameter] = None
                    continue
                region = max(regions, key=lambda region: region.ink)
                assert region.aspect == 1.0, (level, diameter, region.aspect)
                measured[diameter] = region.is_round
            assert measured == dict(DISC_VERDICT_BELOW_THE_SMALLEST_DOT), (
                level,
                measured,
            )
            at_level[level] = measured
        # Re-run at both thresholds for CARD-243 AC-3 and recorded as
        # unchanged: the floor is `fill`'s own resolution on a hard-edged
        # raster, and widening what counts as a mark does not touch it.
        assert at_level[INK_LEVEL] == at_level[MARK_LEVEL], at_level
        # The two halves of the bound as assertions rather than as prose: from
        # DISC_FLOOR_PX up the verdict is round, and below it the verdict is
        # not monotone in the diameter, so no single floor describes it.
        assert all(
            verdict is True
            for diameter, verdict in measured.items()
            if diameter >= DISC_FLOOR_PX
        ), measured
        assert measured[DISC_FLOOR_PX - 1] is False, measured
        assert any(
            verdict is True
            for diameter, verdict in measured.items()
            if diameter < DISC_FLOOR_PX - 1
        ), measured

    @pytest.mark.parametrize("level", MEASURED_LEVELS)
    def test_the_fill_tolerance_sits_in_a_measured_gap(self, level: int) -> None:
        """Below it a pentagon, above it a nearly square box — both measured.

        Re-run at both thresholds (CARD-243 AC-3). Polygons are not
        anti-aliased, so the gap does not move: pentagon 0.8704 below,
        octagon 0.9004 inside, disc 0.9984 at the middle, at either reading.
        """
        pentagon = _shape(_regular_polygon(5, 40), level=level)
        octagon = _shape(_regular_polygon(8, 40), level=level)
        disc = _shape(_disc(81), level=level)
        assert pentagon.fill < 1 - ROUND_FILL_TOLERANCE, pentagon.fill
        assert not pentagon.is_round
        assert octagon.fill > 1 - ROUND_FILL_TOLERANCE, octagon.fill
        assert octagon.is_round
        assert abs(disc.fill - 1) < ROUND_FILL_TOLERANCE / 2, disc.fill
        # The gap the tolerance sits in, as one assertion: a disc is nearer to
        # the tolerance's edge than the pentagon is, by a factor of two.
        assert (1 - pentagon.fill) > 2 * abs(1 - disc.fill)

    @pytest.mark.parametrize("level", MEASURED_LEVELS)
    def test_the_aspect_tolerance_sits_in_a_measured_gap(self, level: int) -> None:
        """Loose on purpose: at 0.08 a hexagon escapes, and at 0.2 it does not."""
        hexagon = _shape(_regular_polygon(6, 40), level=level)
        assert 1.08 <= hexagon.aspect <= 1.2, hexagon.aspect
        assert hexagon.is_round
        oval = _shape(_regular_polygon(32, 40, stretch=0.6), level=level)
        assert oval.aspect > 1 + ROUND_ASPECT_TOLERANCE, oval.aspect
        assert not oval.is_round
        # And the gap on the real book's own pages, in units of the tolerance
        # that binds the closest mark there. At the black threshold that is
        # `fill`, on a near-square filled block already inside this tolerance
        # (CARD-241 cycle 1, F-003); at the widened one it is this tolerance,
        # on a letter stem at 0.6364. Which is which, and each tolerance's own
        # room, are measured in
        # `test_each_tolerances_own_room_on_the_book_is_measured`.
        assert _book_ink(None).at[level].margin >= 1.8

    @pytest.mark.parametrize("level", MEASURED_LEVELS)
    def test_the_rounded_rectangle_boundary_is_where_the_measurement_puts_it(
        self, level: int
    ) -> None:
        middle = _SHAPE_CANVAS // 2
        box = (middle, middle, middle + 40, middle + 40)

        def rounded(radius: int) -> object:
            def drawer(draw: ImageDraw.ImageDraw, page: Image.Image) -> None:
                draw.rounded_rectangle(box, radius=radius, fill=INK)

            return drawer

        verdicts = {
            radius: _shape(rounded(radius), level=level).is_round
            for radius in range(21)
        }
        assert verdicts[14] is False, _shape(rounded(14), level=level).fill
        assert verdicts[15] is True, _shape(rounded(15), level=level).fill
        assert verdicts[0] is False and verdicts[20] is True
        # One crossing, not a band of noise: the verdict flips exactly once as
        # the corners are rounded off — and at the same radius under both
        # thresholds, which CARD-243 AC-3 re-ran rather than assumed.
        flips = sum(
            1 for radius in range(1, 21) if verdicts[radius] != verdicts[radius - 1]
        )
        assert flips == 1, verdicts

    def test_a_hollow_mark_is_not_measured_as_round(self) -> None:
        """A stated bound: this metric measures ink, and a ring is mostly paper.

        The glyph's own outlined dots are in this class, which is why the
        accounting is over the **filled** dots the site declares. A rogue mark
        drawn only as rings escapes — recorded here as a bound with a control,
        not left for a review cycle to find.
        """
        middle = _SHAPE_CANVAS // 2
        box = (middle - 20, middle - 20, middle + 20, middle + 20)
        ring = _shape(
            lambda draw, page: draw.ellipse(box, fill=BACKGROUND, outline=INK, width=2)
        )
        assert ring.aspect == 1.0
        assert ring.fill < 0.3, ring.fill
        assert not ring.is_round
        solid = _shape(lambda draw, page: draw.ellipse(box, fill=INK))
        assert solid.is_round, "the control: the same silhouette, filled, is round"

    def test_a_mark_in_the_books_own_grey_is_measured_and_was_not(self) -> None:
        """CARD-243 AC-4: the darkness bound, **inverted rather than deleted**.

        CARD-241's control is kept whole and its numbers still reproduce: a
        grey-160 disc has **no ink region at all** at
        :data:`~tests.helpers.round_ink.INK_LEVEL`, and the same disc in
        ``INK`` is **one** region and one round mark there. That pairing is
        what measured the bound, and striking the bound does not entitle
        anybody to drop it (CARD-243 G-1).

        What is inverted is the verdict the *guard* reaches. The same grey disc
        is now one round mark to :func:`round_marks`, which reads at
        :data:`~tests.helpers.round_ink.MARK_LEVEL`, because a reader of the
        printed page does not read a threshold. So the three readings are
        asserted together — missed as ink, found as a mark, found as ink when
        it is black — and no two of them can drift apart in silence.
        """
        assert min(_SOLVED_GRID_GRAY) > INK_LEVEL, (
            "this route is about a colour the package really draws and the "
            f"black-ink metric cannot see: {_SOLVED_GRID_GRAY} against "
            f"INK_LEVEL {INK_LEVEL}"
        )
        assert max(_SOLVED_GRID_GRAY) < MARK_LEVEL, (
            "and one the widened metric can: "
            f"{_SOLVED_GRID_GRAY} against MARK_LEVEL {MARK_LEVEL}"
        )
        middle = _SHAPE_CANVAS // 2
        box = (middle - 20, middle - 20, middle + 20, middle + 20)
        grey = _rendered(
            lambda draw, page: draw.ellipse(box, fill=_SOLVED_GRID_GRAY)
        )
        # CARD-241's half, unchanged: at the black threshold this disc is not
        # on the page at all.
        assert ink_regions(grey) == [], (
            "a grey-160 disc is not ink at all, so there is no region to "
            f"measure: {[region.box for region in ink_regions(grey)]}"
        )
        assert round_marks(grey, INK_LEVEL) == []
        # CARD-243's half: to the widened reading it is exactly one round mark,
        # at exactly the silhouette it was always drawn with.
        assert [mark.box for mark in mark_regions(grey)] == [box], (
            "the widened threshold is supposed to see the book's own grey as "
            f"one region: {[region.box for region in mark_regions(grey)]}"
        )
        assert [mark.box for mark in round_marks(grey)] == [box], (
            "and to measure that region as a round mark, which is the whole of "
            "this card"
        )
        # And the control that says what changed is the darkness and not the
        # silhouette: in INK the same disc is found at either threshold.
        dark = _rendered(lambda draw, page: draw.ellipse(box, fill=INK))
        for level in MEASURED_LEVELS:
            assert [mark.box for mark in round_marks(dark, level)] == [box], (
                "the control: the same disc in INK is one round mark at every "
                f"threshold, and at {level} it is not"
            )

    def test_a_mark_that_touches_other_ink_is_not_measured_as_round(self) -> None:
        """A stated bound: regions are connected, so a dot on a rule is one region.

        The second half is the control: the same disc one pixel clear of the
        rule is round again, so the bound is about *touching* and not about the
        rule being on the page at all.
        """
        middle = _SHAPE_CANVAS // 2
        box = (middle - 20, middle - 20, middle + 20, middle + 20)

        def with_rule(gap: int) -> object:
            def drawer(draw: ImageDraw.ImageDraw, page: Image.Image) -> None:
                draw.ellipse(box, fill=INK)
                draw.line(
                    [(0, middle + 21 + gap), (_SHAPE_CANVAS, middle + 21 + gap)],
                    fill=INK,
                    width=3,
                )

            return drawer

        touching = _shape(with_rule(0))
        assert not touching.is_round, touching
        clear = max(
            (
                region
                for region in ink_regions(_rendered(with_rule(2)))
                if region.width < _SHAPE_CANVAS
            ),
            key=lambda region: region.ink,
        )
        assert clear.is_round, clear

    def test_a_diagonal_touch_is_not_a_merge(self) -> None:
        """The control for 4-connectivity, which is a decision and not a detail.

        Ink that touches a mark only at a corner is a second region, so the
        mark keeps its own silhouette and is still found. Under an 8-connected
        reading the two would be one region whose box spans both, far from
        square, and the guard would report **neither** — so this is the test
        that makes the connectivity claim cost something: it fails if the
        overlap test in :func:`~tests.helpers.round_ink.ink_regions` is ever
        relaxed to count a corner.
        """
        middle = _SHAPE_CANVAS // 2
        box = (middle - 20, middle - 20, middle + 20, middle + 20)
        page = Image.new("RGB", (_SHAPE_CANVAS, _SHAPE_CANVAS), BACKGROUND)
        draw = ImageDraw.Draw(page)
        draw.ellipse(box, fill=INK)
        mask = np.asarray(page.convert("L")) < 128
        corner = None
        for y in range(1, _SHAPE_CANVAS - 1):
            for x in range(1, box[0]):
                if mask[y, x]:
                    continue
                diagonal = any(
                    mask[y + dy, x + dx] for dy in (-1, 1) for dx in (-1, 1)
                )
                orthogonal = any(
                    mask[y + dy, x + dx] for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1))
                )
                if diagonal and not orthogonal:
                    corner = (x, y)
                    break
            if corner is not None:
                break
        assert corner is not None, "no pixel touches this disc only at a corner"
        draw.line([(4, corner[1]), corner], fill=INK, width=1)
        regions = ink_regions(page)
        assert len(regions) == 2, [region.box for region in regions]
        marks = round_marks(page)
        assert [mark.box for mark in marks] == [box], (
            "the disc is still its own region, and still round, with ink "
            f"touching it at a corner: {[mark.box for mark in marks]}"
        )

    def test_the_guard_only_measures_the_surfaces_it_renders(self) -> None:
        """A stated bound: it is the interior's pages, and the cover is not one.

        The metric would find a dot on a cover, a proof sheet or a CLI PNG
        export — it is the *page set* that bounds this guard, not the
        measurement. CARD-228's walk reads every module on disk and is the
        wider instrument in exactly this one respect, which is why both are
        kept (G-1).
        """
        cover = BookPDFGenerator(corpus_book()).create_cover_page("Winter Pictures")
        before = len(round_marks(cover))
        draw = ImageDraw.Draw(cover)
        middle = cover.width // 2
        draw.ellipse((middle - 20, 40, middle + 20, 80), fill=INK)
        assert len(round_marks(cover)) == before + 1, (
            "the metric does find a dot on a cover — the bound is the page set"
        )
        assert _book_ink(None).pages == BASELINE_PAGE_COUNT, (
            "and the page set is the interior's own pages, which never include "
            "the cover"
        )


def _rendered(drawer: object, canvas: int = _SHAPE_CANVAS) -> Image.Image:
    """``drawer``'s own canvas, for the few assertions that need every region."""
    page = Image.new("RGB", (canvas, canvas), BACKGROUND)
    drawer(ImageDraw.Draw(page), page)
    return page


# ==========================================================================
# CARD-243 — AC-4 and AC-5: the darkness bound is struck, and what is left
# of the bound list is measured with a control each
# ==========================================================================

#: The box every bound's probe draws its mark in: a 41 px disc, the diameter
#: the glyph itself draws at a book page's band.
_BOUND_BOX = (
    _SHAPE_CANVAS // 2 - 20,
    _SHAPE_CANVAS // 2 - 20,
    _SHAPE_CANVAS // 2 + 20,
    _SHAPE_CANVAS // 2 + 20,
)


def _flat_disc(tone: int) -> Image.Image:
    """A filled disc in a flat grey ``tone`` on paper."""
    return _rendered(lambda draw, page: draw.ellipse(_BOUND_BOX, fill=(tone,) * 3))


def _colour_disc(colour: tuple[int, int, int]) -> Image.Image:
    """A filled disc in ``colour`` on paper."""
    return _rendered(lambda draw, page: draw.ellipse(_BOUND_BOX, fill=colour))


def _composited_disc(alpha: int) -> Image.Image:
    """A black disc pasted onto paper through a flat ``alpha`` mask.

    Partial opacity as Pillow can actually express it on an ``RGB`` page: an
    ``L`` mask at one level, so the composited tone is a known function of
    ``alpha`` and the bound is about that tone rather than about a blend mode.
    """

    def drawer(draw: ImageDraw.ImageDraw, page: Image.Image) -> None:
        left, top, right, bottom = _BOUND_BOX
        side = right - left + 1
        mask = Image.new("L", (side, side), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, side - 1, side - 1), fill=alpha)
        page.paste(Image.new("RGB", (side, side), INK), (left, top), mask)

    return _rendered(drawer)


def _is_seen(page: Image.Image) -> bool:
    """Whether the instrument reports a round mark at :data:`_BOUND_BOX`."""
    return _BOUND_BOX in [mark.box for mark in round_marks(page)]


_COVER: list[object] = []


def _cover_with_a_planted_disc() -> tuple[Image.Image, int, tuple[int, int, int, int]]:
    """The book's cover with a disc on it, the marks it carried before, and the box.

    Rendered once and kept, because the ``unrendered`` bound's probe, its
    control and
    :meth:`TestRoundMarkOnThePage_TheBoundaryIsMeasured.test_the_guard_only_measures_the_surfaces_it_renders`
    all want the same surface and a cover render is not free.
    """
    if not _COVER:
        cover = BookPDFGenerator(corpus_book()).create_cover_page("Winter Pictures")
        before = len(round_marks(cover))
        middle = cover.width // 2
        box = (middle - 20, 40, middle + 20, 80)
        ImageDraw.Draw(cover).ellipse(box, fill=INK)
        _COVER.extend([cover, before, box])
    return _COVER[0], _COVER[1], _COVER[2]  # type: ignore[return-value]


def _disc_beside_a_rule(gap: int) -> Image.Image:
    """A disc with a rule ``gap`` pixels below it — touching at ``gap`` 0."""
    middle = _SHAPE_CANVAS // 2

    def drawer(draw: ImageDraw.ImageDraw, page: Image.Image) -> None:
        draw.ellipse(_BOUND_BOX, fill=INK)
        draw.line(
            [(0, middle + 21 + gap), (_SHAPE_CANVAS, middle + 21 + gap)],
            fill=INK,
            width=3,
        )

    return _rendered(drawer)


def _the_cover_disc_is_in_the_guards_verdict() -> bool:
    """Whether the guard's own measurement reports the disc planted on the cover.

    The ``unrendered`` bound is the one that is not a property of the metric:
    the metric finds that disc perfectly well (its control says so), and the
    guard never renders the surface it is on. So this asks the guard.
    """
    _, _, box = _cover_with_a_planted_disc()
    return any(found == box for _, found in _book_ink(None).found)


@dataclass(frozen=True)
class MarkBound:
    """One property of a mark this instrument is measured not to see.

    Attributes:
        name: The token the prose carries it by. A bound is named in two
            places outside this file — ``tests/helpers/round_ink.py``'s bound
            list and ADR-0036/R3's comment — and each carries it as
            ``BOUND: <name>``, so a bound can be *discussed* in either text as
            often as it likes without being counted as still open. The same
            mechanism :func:`_limits_carried_by` uses for CARD-228's routes.
        caught: Whether the check reports a mark drawn this way. ``False`` is
            an open bound and ``True`` is a closed one, and this column is
            **derived by execution** in
            :meth:`TestRoundMarkOnThePage_TheBoundListShrinksHonestly.test_every_bound_is_measured_and_not_declared`
            — the declaration here is what that test can falsify.
        probe: What to draw, and where. Returns whether the check reports it.
        control: The pairing ADR-0039/R1 requires: the same mark with only the
            property this bound is about changed, which the check **does**
            report. A bound with no control is a claim about nothing.
    """

    name: str
    caught: bool
    probe: object
    control: object


#: Every bound this instrument has, with the verdict derived by execution and
#: a control for each. CARD-241 shipped six of these as prose; CARD-243 closes
#: one of them (``darkness``, which is why it is not in this table) and splits
#: what is left of it into the three it really is.
#:
#: **The darkness bound is gone and these three are what replaced it.** The
#: metric no longer stops at grey 128, so "a mark lighter than the ink" is not
#: one bound but a threshold with a measured crossing: at :data:`MARK_LEVEL`
#: exactly, a mark is paper again. The three rows below are the three ways a
#: mark reaches the lighter side of that crossing — a lighter tone, a colour
#: whose *luminance* is lighter, and ink composited at low opacity — and each
#: is a measured instance with the darker control beside it.
MEASURED_MARK_BOUNDS: tuple[MarkBound, ...] = (
    MarkBound(
        name="lightness",
        caught=False,
        # A flat tone at the threshold itself, against the tone one level
        # darker. The crossing is exactly one level wide, which is what makes
        # the control the strongest one available.
        probe=lambda: _is_seen(_flat_disc(MARK_LEVEL)),
        control=lambda: _is_seen(_flat_disc(MARK_LEVEL - 1)),
    ),
    MarkBound(
        name="colour",
        caught=False,
        # Pure yellow: luminance 226, plainly a mark to a reader of a colour
        # proof and paper to a metric that reads `convert("L")`. The control
        # is pure red at luminance 76 — the same saturation, the other side of
        # the threshold — so the bound is about luminance and not about the
        # page being coloured at all.
        probe=lambda: _is_seen(_colour_disc((255, 255, 0))),
        control=lambda: _is_seen(_colour_disc((255, 0, 0))),
    ),
    MarkBound(
        name="opacity",
        caught=False,
        # Alpha 40 composites black onto paper at tone 215; alpha 64 lands at
        # 191 and is seen. So the bound is not "opacity" in the abstract: it
        # is the tone the compositing comes to, and the crossing sits between
        # those two alphas.
        probe=lambda: _is_seen(_composited_disc(40)),
        control=lambda: _is_seen(_composited_disc(64)),
    ),
    MarkBound(
        name="hollow",
        caught=False,
        probe=lambda: _is_seen(
            _rendered(
                lambda draw, page: draw.ellipse(
                    _BOUND_BOX, fill=BACKGROUND, outline=INK, width=2
                )
            )
        ),
        control=lambda: _is_seen(
            _rendered(lambda draw, page: draw.ellipse(_BOUND_BOX, fill=INK))
        ),
    ),
    MarkBound(
        name="touching",
        caught=False,
        probe=lambda: _is_seen(_disc_beside_a_rule(0)),
        control=lambda: _is_seen(_disc_beside_a_rule(2)),
    ),
    MarkBound(
        name="footprint",
        caught=False,
        probe=lambda: _shape(_regular_polygon(32, 40, stretch=0.6)).is_round,
        control=lambda: _shape(_regular_polygon(32, 40)).is_round,
    ),
    MarkBound(
        name="resolution",
        caught=False,
        probe=lambda: _shape(_disc(6), canvas=6 + 2 * _SHAPE_MARGIN).is_round,
        control=lambda: _shape(
            _disc(DISC_FLOOR_PX), canvas=DISC_FLOOR_PX + 2 * _SHAPE_MARGIN
        ).is_round,
    ),
    MarkBound(
        name="unrendered",
        caught=False,
        # The one bound that is not a property of the metric: the metric finds
        # this disc perfectly well, on a surface the guard never renders. So
        # the probe asks the GUARD -- is this mark in the interior's own
        # verdict? -- and the control asks the metric, which says yes.
        probe=_the_cover_disc_is_in_the_guards_verdict,
        control=lambda: len(round_marks(_cover_with_a_planted_disc()[0]))
        == _cover_with_a_planted_disc()[1] + 1,
    ),
)

#: The bound this card strikes. Named once, here, because three statements
#: have to move together and a name repeated in three places is how they drift
#: apart (CARD-242's AC-5, the precedent this copies).
STRUCK_BOUND = "darkness"

#: ADR-0036, whose R3 comment is the model's own statement of this
#: instrument's reach. Located the way ``tests/test_guard_integrity.py``
#: locates CARD-239's claim sweep.
ADR_0036 = (
    Path(__file__).resolve().parent.parent
    / "meta"
    / "architecture"
    / "decisions"
    / "adr"
    / "0036-book-page-geometry-via-page-spec.md"
)

#: The two texts outside this file that carry the bound list, and which this
#: card edits in the same diff that closes the route.
BOUND_LIST_TEXTS = {
    "tests/helpers/round_ink.py": lambda: round_ink.__doc__ or "",
    "ADR-0036/R3": lambda: ADR_0036.read_text(encoding="utf-8"),
}


def _bounds_carried_by(text: str) -> set[str]:
    """The bounds ``text`` still carries as open, by their ``BOUND:`` markers.

    One marker per bound, so a bound can be named in a text's prose — as
    ``darkness`` is, in the sentence recording that it *was* one — without
    being counted as open. :meth:`...test_the_bound_marker_can_fire` is the
    control that this extractor can find one at all.
    """
    names = {bound.name for bound in MEASURED_MARK_BOUNDS} | {STRUCK_BOUND}
    return {name for name in names if f"BOUND: {name}" in text}


class TestRoundMarkOnThePage_TheBoundListShrinksHonestly:
    """CARD-243 AC-4 and AC-5: one bound struck, the rest measured.

    CARD-241 stated six bounds in prose and controlled each. This card closes
    the widest of them — ``darkness``, the one the package's own
    ``_SOLVED_GRID_GRAY`` walked straight through — and that closing has to
    happen in three places at once: the metric's threshold, the bound list in
    ``tests/helpers/round_ink.py``, and ADR-0036/R3's comment, which is where
    the *model* states this instrument's reach. Closing the route without
    striking the record leaves a bound that is no longer a bound; striking the
    record without closing the route leaves the route open with nothing naming
    it. :meth:`test_the_struck_bound_and_the_closed_route_agree` is red either
    way, which is CARD-242's mechanism and the precedent this copies.

    What is left is in :data:`MEASURED_MARK_BOUNDS`, with every verdict
    derived by execution and a control per row (ADR-0039/R1, which CARD-241
    reached a second review cycle for breaking three times in one root cause).
    The three rows that replaced ``darkness`` are the honest residue of
    widening it: the threshold moved from grey 128 to grey 208, so what is
    open now is a mark on the lighter side of *that* crossing — a lighter
    tone, a colour whose luminance is lighter, or ink composited thin enough
    to land there. None of them is hypothetical and none of them is a tone the
    package draws today, which is the difference between this residue and the
    bound this card struck.

    **What could not be made into a bound, and what was tried.** AC-5 names
    "anti-aliased edges below the threshold" as a candidate. It is not one:
    measured over faces 4 to 40 px, a ``chr(0x25CF)`` set as type always
    rasterises a fully black core (darkest pixel 0 at every size, with 7 of 10
    pixels already under grey 128 at a 4 px face), so there is no size at
    which a typed mark is *only* anti-aliasing. What is open is a mark whose
    whole raster is lighter than the threshold, which is the ``lightness`` row,
    and :meth:`test_a_typed_mark_always_leaves_a_black_core` records the
    measurement that says so.
    """

    @pytest.mark.parametrize(
        "bound", MEASURED_MARK_BOUNDS, ids=lambda bound: bound.name
    )
    def test_every_bound_is_measured_and_not_declared(self, bound: MarkBound) -> None:
        """Each row's verdict, derived — and its control, which must disagree."""
        assert bound.probe() == bound.caught, (
            f"the {bound.name} bound says the check {'does' if bound.caught else 'does not'} "
            "report a mark drawn this way, and the measurement disagrees"
        )
        assert bound.control() is True, (
            f"the {bound.name} bound's control must be a mark the check DOES "
            "report, or the bound is a claim about nothing (ADR-0039/R1)"
        )

    def test_the_table_is_the_bounds_the_instrument_really_has(self) -> None:
        """No duplicates, no empty table, and the struck bound is not in it."""
        names = [bound.name for bound in MEASURED_MARK_BOUNDS]
        assert len(names) == len(set(names)) == 8, names
        assert STRUCK_BOUND not in names, (
            f"{STRUCK_BOUND} is the bound this card closed; a row for it here "
            "would be a bound the measurement denies"
        )
        assert all(bound.caught is False for bound in MEASURED_MARK_BOUNDS), (
            "every row of this table is a bound, which means the check does "
            "not report it; a caught row belongs in the prose as closed"
        )

    def test_the_bound_marker_can_fire(self) -> None:
        """Control for the extractor the two agreements below depend on."""
        assert _bounds_carried_by("nothing here") == set()
        assert _bounds_carried_by("* a mark lighter than it (BOUND: lightness)") == {
            "lightness"
        }
        assert _bounds_carried_by(
            "darkness was a bound until CARD-243 (BOUND: colour)"
        ) == {"colour"}

    @pytest.mark.parametrize("where", sorted(BOUND_LIST_TEXTS))
    def test_each_bound_list_carries_exactly_the_open_bounds(self, where: str) -> None:
        """Both texts, held to the table rather than to each other.

        A bound the measurement says is open and neither text names is a
        bound nobody can read; a bound a text names that the measurement says
        is closed is the defect this card exists to fix, one level up.
        """
        carried = _bounds_carried_by(BOUND_LIST_TEXTS[where]())
        expected = {bound.name for bound in MEASURED_MARK_BOUNDS if not bound.caught}
        assert carried == expected, (
            f"{where} carries {sorted(carried)} as open bounds while the "
            f"measurement says {sorted(expected)}"
        )

    def test_the_struck_bound_and_the_closed_route_agree(self) -> None:
        """AC-4, as CARD-242 built it: three statements that move together.

        The route is the book's own grey on the book's own pages — planted,
        rendered and measured, not a canvas. The record is the ``BOUND:``
        marker in each of the two texts. Exactly one of "the route is open"
        and "the record names it" may be true, and this is red in both
        directions: a threshold lowered without the texts being edited, and
        texts edited without the threshold being lowered, both fail here.
        """
        closed = _book_ink("GY1 grey ellipse").unaccounted != ()
        assert closed, (
            "the route this card closes is not closed on a real page, so "
            "nothing below is about anything"
        )
        for where, read in sorted(BOUND_LIST_TEXTS.items()):
            carried = STRUCK_BOUND in _bounds_carried_by(read())
            assert closed != carried, (
                f"{where} and the deployed check disagree about "
                f"{STRUCK_BOUND}: the page closes the route ({closed}) and the "
                f"text carries it as an open bound ({carried})"
            )

    def test_the_adr_rule_states_the_reach_it_now_has(self) -> None:
        """R3's reach sentence, held to the threshold the code really uses.

        Not a prose review — two things the comment must say in numbers, both
        read off the deployed constants, because the reach statement is
        exactly what CARD-241's review found written ahead of the measurement
        three times (RC-1).
        """
        text = ADR_0036.read_text(encoding="utf-8")
        assert f"grey {MARK_LEVEL}" in text, (
            "ADR-0036/R3's comment must name the threshold the check really "
            f"reads at, which is grey {MARK_LEVEL}"
        )
        assert f"grey {max(_SOLVED_GRID_GRAY)}" in text, (
            "and the tone the package draws that the old threshold missed, "
            f"which is grey {max(_SOLVED_GRID_GRAY)}"
        )

    def test_a_typed_mark_always_leaves_a_black_core(self) -> None:
        """The candidate bound that measurement refused (AC-5).

        "Anti-aliased edges below the threshold" would be a bound only if some
        mark were *all* edge. A typed round mark never is: at every face from
        4 px to 40 px the glyph's darkest pixel is 0, so it is ink at either
        threshold and the ``lightness`` row is the bound that really covers
        the light case. Recorded as a measurement rather than as a judgement.
        """
        darkest = {}
        for face in (4, 6, 8, 12, 20, 40):
            page = Image.new("RGB", (120, 120), BACKGROUND)
            ImageDraw.Draw(page).text(
                (60, 60), chr(0x25CF), font=_band_font(face), fill=INK, anchor="mm"
            )
            grey = np.asarray(page.convert("L"))
            darkest[face] = int(grey.min())
            assert (grey < INK_LEVEL).any(), (
                f"a {face} px typed dot has no pixel darker than INK_LEVEL, so "
                "a mark made only of anti-aliasing IS reachable and is a bound "
                "this table does not carry"
            )
        assert set(darkest.values()) == {0}, darkest


# ==========================================================================
# AC-5 — the static guard's named-limits list shrinks, and only honestly
# ==========================================================================


def _limits_carried_by(doc: str) -> set[str]:
    """The routes ``doc`` still carries as named limits of the static walk.

    The marker is ``**LIMIT:** <mutant>``, one per route, so a route can be
    *mentioned* in that docstring's history as often as it likes without being
    counted as an open limit. :meth:`...test_the_marker_can_fire` is the
    control that this extractor is capable of finding one.
    """
    return {route.mutant for route in NAMED_LIMITS if f"**LIMIT:** {route.mutant}" in doc}


class TestRoundMarkOnThePage_TheNamedLimitsListShrinksHonestly:
    """AC-5: exactly the routes this card closes are struck, and no others.

    CARD-228's named-limits list was six paragraphs of prose, each carrying
    the mutant that demonstrated the route was open. This card closes all six
    — on the pages the book renders — so all six are struck from that list and
    moved into :data:`NAMED_LIMITS`, where both columns are derived by
    execution:

    * **seen by the walk**: CARD-228's own four mechanisms, run over the
      plant's own source as a fabricated module. All six come back silent, and
      :data:`SEEN_BY_THE_WALK` proves the predicate can fire at all.
    * **closed on the page**: the plant is drawn into every band of a real
      book, the interior is rendered, and the guard's verdict is read.

    The equality below is red in **both** directions, which is the property
    AC-5 asks for: a route struck from the prose that the page does not catch,
    and a route the page catches that the prose still carries as open, both
    fail it. Striking a limit is therefore not an edit anyone can make by
    hand.
    """

    def test_the_table_is_the_six_routes_cycle_3_left_open(self) -> None:
        assert len(NAMED_LIMITS) == 6
        assert len({route.mutant for route in NAMED_LIMITS}) == 6
        assert {route.mutant for route in NAMED_LIMITS} <= set(PLANTS)
        assert set(SEEN_BY_THE_WALK) <= set(PLANTS)

    def test_the_walk_really_is_blind_to_every_route_in_the_table(self) -> None:
        for route in NAMED_LIMITS:
            complaints = _static_walk_complaints(PLANTS[route.mutant])
            assert (complaints != []) == route.seen_by_the_walk, (route, complaints)

    def test_the_walks_own_predicate_can_fire(self) -> None:
        """Without this, "the walk is blind to all six" is a claim about nothing."""
        for route in SEEN_BY_THE_WALK:
            assert _static_walk_complaints(PLANTS[route]) != [], route

    def test_every_route_the_table_says_is_closed_is_caught_on_the_page(self) -> None:
        for route in NAMED_LIMITS:
            caught = _book_ink(route.mutant).unaccounted != ()
            assert caught == route.closed_on_the_page, (route, caught)

    def test_the_marker_can_fire(self) -> None:
        """Control for the extractor the equality below depends on."""
        assert _limits_carried_by("nothing here") == set()
        assert _limits_carried_by("* **LIMIT:** L1 line fan — open") == {"L1 line fan"}

    def test_the_limits_list_is_exactly_the_routes_no_instrument_closes(self) -> None:
        carried = _limits_carried_by(
            inspect.getdoc(TestDifficultyDots_HasExactlyOneDrawingSite) or ""
        )
        closed = {
            route.mutant for route in NAMED_LIMITS if _book_ink(route.mutant).unaccounted
        }
        assert carried == {route.mutant for route in NAMED_LIMITS} - closed, (
            "the static guard's named-limits list and what the render check "
            f"really closes disagree: it carries {sorted(carried)} while the "
            f"page closes {sorted(closed)}"
        )
