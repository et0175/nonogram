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

and CARD-331, which is the same accounting again for the medium ADR-0042/R1
is converting the interior to. Everything above reads a bitmap; a page written
as operators has no pixels, and an instrument pointed at one measures nothing
rather than measuring a lighter page. So the accounting is **two arms, one per
medium, each naming the mechanism its reading comes out of**, and the card's
whole point is that an arm whose mechanism stops firing must RED:

    AC-1  TestDifficultyDots_TheClaimIsAboutThePageNotTheCall
    AC-2  TestDifficultyDots_TheVectorArmReadsTheStream
    AC-3  TestDifficultyDots_TheRasterArmHoldsWithoutHookingTheProduct
    AC-4  TestDifficultyDots_AnArmWhoseMechanismIsDeadFails
    AC-5  the per-assertion mutant table in CARD-331's ## Worktree notes
    AC-6  tests/test_book_pdf.py's own
          test_no_declaration_outlives_the_cards_that_remove_it, unmodified

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
import textwrap
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
    GUIDE_PAGE_COUNT,
    TITLE_PAGE_COUNT,
    BookPDFGenerator,
    PageKind,
    PageMedium,
    _band_font,
    _draw_difficulty_dots,
)
from nonogram.admin.book_plan import TIERS
from nonogram.admin import book_vector
from nonogram.admin.book_vector import ContentStream
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
    compute_layout,
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
    StreamMark,
    ink_regions,
    mark_regions,
    round_marks,
    round_stream_marks,
    stream_marks,
)

# The writer's own operator surface, **as the module that measures it reports
# it** rather than as this one would re-list it (ADR-0039/R2).
# ``_DOOR_EMITS`` is what ``_content_stream_doors`` records when it drives every
# public ``ContentStream`` member; ``_UNCLASSIFIED_DOORS`` is the members its
# probe table cannot call, and must be empty for the union of the first to be
# the whole surface; ``_PATH_OPERATORS`` is that surface partitioned into the
# operators that put a path on a page. Imported across the test tree the way
# ``tests/test_book_cell_size.py`` and sixteen other modules import a sibling's
# measurement: the import CLAUDE.md forbids is a lateral one inside
# ``src/nonogram``, and this is the test tree, which is exactly where that rule
# says a cross-check belongs.
from tests.test_book_solved_answer_key import (
    _DOOR_EMITS as _WRITER_DOOR_EMITS,
    _PATH_OPERATORS as _WRITER_PATH_OPERATORS,
    _UNCLASSIFIED_DOORS as _WRITER_UNCLASSIFIED_DOORS,
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
#: for a dot needs a dozen or more (cycle 1's surviving mutant used 32).
#:
#: **It does NOT leave a circle out, and this comment used to say it did**
#: ("four leaves room for a quadrilateral without leaving room for a circle").
#: The bound is **per call**, so a disc approximated as a *fan of three-point
#: polygons* clears it, and since the one real call needs three there is no
#: figure that admits the package and refuses the fan. Pre-existing and out of
#: CARD-296's scope — recorded here because CARD-296 cited this bound as proof
#: the mechanism works, measured the identical hole in its own copy of it one
#: medium over, and a reader who follows the citation back should not find the
#: claim restated. It is the same family as the ``draw.point`` accumulation
#: limit this class already names, and the same owner closes both by measuring
#: ink: **CARD-241**.
MAX_FLAT_VERTICES = 4

#: Codepoints that are a round or geometric mark in their own right: Unicode's
#: Geometric Shapes block (U+25A0..U+25FF, which holds \u25cf BLACK CIRCLE and
#: \u25cb WHITE CIRCLE — a three-dot glyph needs nothing else), plus U+2022
#: BULLET, U+2219 BULLET OPERATOR and U+00B0 DEGREE SIGN.
#:
#: **What this set does NOT hold, measured and named rather than implied**
#: (CARD-296 review cycle 2, N-4). In a **vector** page the medium is
#: ``book_vector.TEXT_ENCODING`` (cp1252), and the Geometric Shapes block is
#: outside it: a planted \u25cf in a ``stream.text`` call never reaches this
#: rule, because ``book_vector._escape`` raises first. For that medium the
#: encoder is the protection and this rule is not. The two round glyphs a
#: WinAnsi stream really *can* print are U+00B0 and U+00B7 MIDDLE DOT:
#:
#: * **U+00B0 is added here**, measured free \u2014 no module in ``src/nonogram``
#:   writes it, so the rule tightens at no cost and
#:   :data:`DINGBAT_EXEMPT_MODULES`' equality is untouched;
#: * **U+00B7 is this rule's named hole, and cannot be closed from here.** It
#:   is the package's own typographic separator \u2014 the puzzle band's at
#:   ``book_pdf_generator.py:466``, the proof page's at ``book_proof.py:157``,
#:   and a docstring in ``book_vector.py`` \u2014 so barring it would need three
#:   exemptions covering the band, which is exactly where CARD-207's glyph
#:   would hide, and the rule would mean less than it does now. A middle-dot
#:   tier glyph on the vector guide is caught instead by that page's own pair
#:   of equalities (its legend's strings against ``GUIDE_DIFFICULTY_LABELS``,
#:   and its record against the written stream, both in
#:   ``tests/test_book_guide_page_vector.py``). On a **raster** band it is
#:   caught by nothing here; **CARD-241**'s ink measurement is the instrument
#:   that does not care how a dot was spelled.
ROUND_DINGBATS = frozenset(chr(code) for code in range(0x25A0, 0x2600)) | {
    "\u2022",
    "\u2219",
    "\u00b0",
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
#: fourth one is a failure that has to be looked at.
#:
#: **Three since CARD-223, down from four.** ``_blank_page`` built its draw
#: object inline and handed it to ``_draw_page_frame``; that card gives the
#: same page a second mark to draw (the QR icon's two footer lines), so the
#: object is now bound once, as ``draw``, and the site leaves this table by
#: satisfying the rule rather than by being excused from it. The entry is
#: **removed, not kept "just in case"**: this is an equality, and a name left
#: in it after its site has gone is a licence for whatever takes that name
#: next (ADR-0039/R3, the same reasoning
#: ``test_every_exemption_is_a_constant_that_really_exists`` applies in
#: ``test_book_page_frame.py``).
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
#: **Why one of these names is written in two halves.** Cycle 2 reduced
#: this table to a per-module-and-form *count* because one of the sites
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
    ("nonogram.admin.book_pdf_generator", "sample", "receiver"),
    ("nonogram.export.pdf", "_titled", "argument"),
    ("nonogram.export.pdf", "render" + "_pages", "argument"),
)

#: Every call to a draw-method *name* in the package whose receiver is not a
#: draw object, as ``(module, enclosing function, method, receiver)`` — an
#: earned exemption in the shape :data:`DINGBAT_EXEMPT_MODULES` already uses:
#: an equality against what exists today, plus a second assertion (in
#: :meth:`TestDifficultyDots_HasExactlyOneDrawingSite.test_the_non_draw_receiver_exemptions_cannot_draw_a_round_mark`)
#: that no site can actually put a round mark on a page.
#:
#: **Back to ONE family, and the reason is the point.** CARD-295 met the
#: vector receivers by adding **four rows** here; CARD-296 met the same
#: receivers by **deriving the rule** (:data:`VECTOR_RECEIVER_NAME` and
#: :func:`_excused_vector_methods`). Both landed, and for one commit the
#: table and the predicate each claimed the same four calls — wave 49's
#: rule arriving as a merge conflict no auto-merge could see: *widening a
#: predicate and adding an exemption are the same edit*, and keeping both
#: leaves the exemption absorbing what the predicate now handles. The rows
#: are **removed, not kept "just in case"**: this is an equality, and a row
#: that no longer earns itself is a licence for whatever next takes that
#: spelling. Caught by the merge pre-check, which ran the touched files
#: together.
#:
#: * ``Image.point``, a per-pixel lookup table: one takes a 256-entry table
#:   built with ``*`` and ``+``, the other a lambda. Neither takes
#:   coordinates, which is the property the second assertion pins.
#: * ``ContentStream.line`` / ``.rectangle`` / ``.text`` — the PDF **operator
#:   recorder** ADR-0042 draws the book's interior with
#:   (``nonogram.admin.book_vector``), reached from the one module that turns
#:   a COMP-007 ``Layout`` into its calls. Three of its method names collide
#:   with Pillow's and its receiver is a ``ContentStream``, so the first
#:   vector page lands here by construction. **Added rather than dodged**: the
#:   calls could have been spelled through a wrapper this walk does not read,
#:   which would have kept this table short while the drawing stayed exactly
#:   where it is.
#:
#:   What earns the exemption is not the receiver's name but its **surface**:
#:   a ``ContentStream`` has no ellipse-family and no round-enough method at
#:   all — asserted against ``dir()``, not against this comment — and
#:   ``round_mark``, one round shape it can make, is not a draw-method name,
#:   so no call to it would be collected here whatever its receiver. That
#:   spelling has its own guard in the file that wrote it:
#:   ``tests/test_book_pdf_vector_primitives.py``'s
#:   ``TestVectorVocabulary_TheRoundMarkRouteTheOldGuardCannotSee``, which
#:   holds the ``c`` operator to one module and ``round_mark`` to one
#:   definition called nowhere.
#:
#:   **CORRECTED, CARD-295 cycle 1 F-004.** This comment used to end "The two
#:   compose; neither is trusted alone", which claimed a coverage the pair
#:   does not have. They compose over **two spellings** and not over the
#:   route: a round mark assembled from ``ContentStream.begin_path`` /
#:   ``curve`` / ``close_path`` / ``paint`` passes this walk (none of those
#:   five names is in :data:`ALL_DRAW_METHODS`, so the call is never collected
#:   and this exemption table is never consulted) **and** both tests over
#:   there — measured, not reasoned. That hole is named as a set by
#:   ``TestVectorVocabulary_…``'s ``UNWATCHED_MARKS`` and owned by
#:   **CARD-298**, which reads every interior page kind's written operators at
#:   once; an operator that reached a page is a fact no source pattern can be
#:   fooled about, which is why the closable version of this guard lives
#:   there and not here.
NON_DRAW_RECEIVER_SITES = (
    ("nonogram.sourcing.image", "binarize", "point", "scaled"),
    ("nonogram.sourcing.image", "ink_bounding_box", "point", "greyscale"),
)

#: How a **vector content stream** is spelled in this package: the bare name
#: ``stream`` (CARD-296, ADR-0042).
#:
#: **This is the fifth route CARD-294 said would be needed**, and it is here
#: for the reason that card's measurements document records (§5, finding one):
#: ``ContentStream`` is not a Pillow draw object at all, so this guard's four
#: routes are all outside it — and yet ``stream.line(...)``,
#: ``stream.rectangle(...)`` and ``stream.text(...)`` are *written* with names
#: this guard watches, so the inverted receiver rule reports every one of them
#: as an unrecognised receiver. CARD-296, the first page card, is where the
#: decision CARD-294 deferred gets taken.
#:
#: What is **not** done here: widening any round-shape bin. **A content stream
#: has three routes to a round shape, and this comment used to name one of
#: them** — "a content stream's only round shape is
#: ``ContentStream.round_mark``", which review cycle 1 (F-1) measured false and
#: which is corrected here rather than left standing in the place a later card
#: would read it. None of the three is a method name Pillow ever had, so none
#: is in this guard's families. **Two of the three are controlled elsewhere;
#: the third is a declared, open limit** — cycle 3's F-301 caught this
#: comment still claiming all three, which is the claim
#: ``tests/test_book_pdf_vector_primitives.py`` retracts 350 lines away, so
#: two merged guards contradicted each other on this card's central claim:
#:
#: * ``ContentStream.round_mark`` and a hand-written ``c`` operator —
#:   ``tests/test_book_pdf_vector_primitives.py``'s
#:   ``TestVectorVocabulary_TheRoundMarkRouteTheOldGuardCannotSee``, which
#:   asserts that ``round_mark(`` appears in no module but the vocabulary's own
#:   and that the ``c`` operator is written in exactly one module;
#: * a **polygonal disc** built from ``begin_path``/``line_to``/``close_path``
#:   — invisible to both of those, as a planted 32-gon on the guide's
#:   difficulty legend demonstrated with 248 tests green. **NOT bounded, and
#:   not closable here.** Fix round 1 bounded it per page kind and review
#:   cycle 2 measured that the bound cannot close it: a fan of 32
#:   **three-point** triangles and a staircase of 24 filled ``re`` bands both
#:   passed 264/264. The reason is structural, not a figure to tune — the
#:   guide's own arrow head is three points and so is a triangle, so **no
#:   value of a vertex bound admits this page and refuses a disc**. CARD-295
#:   then showed the same from the other side: the route *is* shut on the
#:   puzzle page, but only because that page writes **no filled path at all**,
#:   whereas this page legitimately writes both of the defeating vocabularies
#:   (a filled three-point arrow head, and ``re``+``f`` diagram squares). So
#:   neither a vertex count nor an operator-vocabulary rule separates the page
#:   from a disc. It is carried as a **NAMED LIMIT with CARD-298 as owner**,
#:   which holds ADR-0042/R1's derived per-page-kind check — the residue is
#:   cross-page, and the discriminator has to be geometric (ink, or a rule on
#:   filled subpaths). ``tests/test_book_guide_page_vector.py``'s
#:   ``TestGuidePage_DifficultyLegendCarriesNoRoundShapeToday`` keeps the
#:   narrower thing it does say: the longest *single* subpath this page writes
#:   is the three-point arrow head;
#: * a round **dingbat** inside a ``(…) Tj`` — the dingbat rule in this file,
#:   which reads every string literal in the package and so already covers the
#:   vector modules.
#:
#: Named here rather than duplicated, because two copies of one claim drift —
#: which is how the sentence this comment replaces came to be wrong in three
#: places at once.
VECTOR_RECEIVER_NAME = "stream"

#: The draw-method names a ``ContentStream`` may be excused for, **derived
#: from the class** (ADR-0039/R2 — a guard's set comes from an enumerable
#: authority) and then narrowed by subtraction rather than by a list.
#:
#: The intersection of :data:`ALL_DRAW_METHODS` with the class's own public
#: methods, minus every family that could put a round mark on a page. So
#: ``stream.line`` and ``stream.rectangle`` (flat) and ``stream.text`` (a
#: string) are accounted for, and the day ``ContentStream`` grows an
#: ``ellipse``, a ``polygon`` or a ``rounded_rectangle`` this set does **not**
#: grow to cover it: such a call is reported as an unrecognised receiver and
#: this guard reds, which is the point.
#:
#: **Written as a function of the surface rather than as an expression over
#: ``ContentStream``, because the subtraction has to be controllable.** Today
#: that class carries no ``ellipse``, no ``polygon`` and no
#: ``rounded_rectangle``, so taking those families out changes nothing about
#: the value below, and an assertion that the value avoids them passes whether
#: the subtraction is written or not — measured, not supposed: deleting the
#: three subtractions left this whole class green. The rule is therefore also
#: exercised against a stand-in surface that *does* carry them, in
#: :meth:`TestDifficultyDots_HasExactlyOneDrawingSite.test_the_vector_stream_receiver_is_excused_only_for_marks_that_cannot_be_round`,
#: which is the only way the narrowing can be shown to be load-bearing.
def _excused_vector_methods(surface: type) -> frozenset[str]:
    """Which of ``surface``'s public methods a vector receiver is excused for."""
    return frozenset(name for name in dir(surface) if not name.startswith("_")) & (
        ALL_DRAW_METHODS
        - ELLIPSE_METHODS
        - ROUND_ENOUGH_METHODS
        - VERTEX_BOUNDED_METHODS
    )


VECTOR_STREAM_METHODS = _excused_vector_methods(ContentStream)

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


def _is_vector_receiver(node: ast.AST) -> bool:
    """Whether ``node`` is a vector content stream, as this package spells one.

    The bare name :data:`VECTOR_RECEIVER_NAME` — a **name-shaped** test, the
    same shape as :func:`_is_draw_receiver`'s own first clause.

    **It is not narrow on its own, and this docstring used to claim it was**
    ("as narrow as ``_is_draw_receiver``'s own first clause and for the same
    reason"). The name ``draw`` is narrow because two sibling rules *bind* it
    to real draw objects; review cycle 1 (F-4) measured that nothing in the
    tree bound the name ``stream`` to a ``ContentStream``, so an unannotated
    parameter called ``stream`` handed a Pillow draw object was excused for
    ``line`` — cycle 2's M2 control with the name changed. What makes the name
    narrow is therefore written down beside it rather than asserted here:

    * :meth:`TestDifficultyDots_HasExactlyOneDrawingSite.test_every_content_stream_in_the_package_is_spelled_stream`
      — every ``ContentStream(...)`` binding that yields a name yields this
      one, every parameter that *is* one is spelled it, and no
      ``ImageDraw.Draw(...)`` binding and no ``ImageDraw``-annotated parameter
      is;
    * :func:`_passes_a_coordinate_display` — and the excuse is refused for a
      call written in Pillow's own shape, which is what closes M2's route
      whatever the parameter is called.
    """
    return isinstance(node, ast.Name) and node.id == VECTOR_RECEIVER_NAME


#: What counts as a **sequence display** in an argument position, held in ONE
#: place because the two helpers that ask the question used to disagree and the
#: disagreement was the defect (CARD-296 review cycle 3, N-3).
#:
#: :func:`_passes_a_coordinate_display` tested ``List``/``Tuple`` only while
#: :func:`_names_bound_to_a_sequence` already counted a comprehension as a
#: sequence, so an **inline** comprehension —
#: ``stream.line([(i, i) for i in range(32)], 1, 3, None)`` — was reported by
#: nothing: not a display to the one, and never bound to a name for the other.
#: Measured by cycle 3, which is also why this is a constant rather than a
#: fourth copy of the tuple.
#:
#: **One difference from :func:`_names_bound_to_a_sequence` remains and is
#: deliberate:** that function also counts ``ast.Set``, and this does not.
#: A set display is unordered and so is not a coordinate list any drawing
#: surface would accept, and cycle 3 prescribed the three comprehension types
#: and measured those. **The residue is therefore named, not closed**: a
#: ``stream.line({(0, 0), (1, 1)}, ...)`` is still reported by neither helper.
#: It belongs with the rest of this card's declared limits (CARD-298).
SEQUENCE_DISPLAYS = (ast.List, ast.Tuple, ast.ListComp, ast.SetComp, ast.GeneratorExp)


def _passes_a_coordinate_display(call: ast.Call) -> bool:
    """Whether ``call``'s first positional argument is a coordinate display.

    The discriminating property between the two surfaces that share these
    method names, and it is a property of the **call** rather than of the
    receiver's spelling:

    * ``ContentStream.line(x1, y1, x2, y2)``, ``rectangle(left, top, right,
      bottom)`` and ``text(value, x, y, size_pt)`` take scalars — a number or
      a string first, never a sequence of points;
    * ``ImageDraw.line(xy, ...)``, ``rectangle(xy, ...)`` and
      ``polygon(xy, ...)`` take a coordinate display first, and that display is
      where a disc hides (``FLAT_METHODS`` carries ``line``'s polyline hole at
      length).

    So a call excused as a content stream must not be written in Pillow's
    shape. The same instrument
    :meth:`TestDifficultyDots_HasExactlyOneDrawingSite.test_the_non_draw_receiver_exemptions_cannot_draw_a_round_mark`
    already points at :data:`NON_DRAW_RECEIVER_SITES` ("a coordinate display on
    a receiver excused as a pixel map"), pointed at the vector route.
    """
    argument = call.args[0] if call.args else None
    return isinstance(argument, SEQUENCE_DISPLAYS)


def _binds_the_vector_surface(method: str, call: ast.Call) -> bool:
    """Whether ``call`` could be a call of ``ContentStream.<method>`` at all.

    The **type-shaped** half of the vector exemption, and the reason it is here
    rather than a sentence: the authority is the class itself
    (ADR-0039/R2). ``inspect.signature(ContentStream.line)`` is
    ``(self, x1, y1, x2, y2)``, so this call's positional count and keyword
    names are bound against it, and a call that cannot bind is **not** a call
    on that surface whatever its receiver is called.

    That is what refuses Pillow's own shapes under the vector name, including
    the one :func:`_passes_a_coordinate_display` alone would miss —
    ``stream.line(points, fill=1, width=3)`` with ``points`` a bare name, which
    is exactly how this package writes its real ``draw.line`` calls
    (``book_pdf_generator.py:1429``): one positional argument where four are
    required, and two keywords ``ContentStream`` does not have.

    **Default-deny** on anything the walk cannot count: a starred argument or a
    ``**kwargs`` splat makes the arity unknowable, so the excuse is refused
    rather than guessed at — the same inversion
    :func:`_uncountable_vertices` applies to a vertex display.

    **The wholly-positional Pillow call, and why it is now refused rather than
    dismissed.** ``draw.line(a, b, c, d)`` — ``xy``, ``fill``, ``width``,
    ``joint`` positionally — binds ``ContentStream.line(x1, y1, x2, y2)``'s
    arity exactly, and a bare ``Name`` is not an ``ast.List``, so neither this
    rule nor :func:`_passes_a_coordinate_display` fired. This docstring used to
    dismiss the spelling ("it is not a spelling that draws anything round —
    ``a`` would have to be the coordinate sequence, and a literal one is
    refused") three paragraphs after establishing that the **non**-literal
    coordinate sequence is this package's own idiom, and CARD-296 review cycle
    2 (N-3) measured ``stream.line(points, 1, 3, None)`` reported by nothing at
    all — five mechanisms blind, on the one method :data:`FLAT_METHODS`
    documents as the route a previous cycle landed a complete second glyph
    through.

    One clause closes it, and :func:`_hides_a_sequence_argument` is that
    clause: an excused call may not hand over a positional argument that is a
    call result, or a bare name the module binds to a sequence display, because
    every positional parameter ``ContentStream`` offers here is a scalar — a
    coordinate, a size or a string. Every call the package really writes passes
    it (``Name``, ``Attribute``, ``BinOp`` or ``Constant``, none of them bound
    to a sequence), measured over all 21 of them; a vertex list under any of
    the three spellings does not.

    What it still does not reach, and CARD-241's ink measurement is the
    instrument that does not depend on spelling at all: a vertex sequence
    handed over as a subscript or an attribute (``stream.line(self.points, 1,
    3, None)``), where this walk has no binding to read.
    """
    try:
        signature = inspect.signature(getattr(ContentStream, method))
    except (AttributeError, TypeError, ValueError):  # pragma: no cover - defensive
        return False
    if any(isinstance(argument, ast.Starred) for argument in call.args):
        return False
    if any(keyword.arg is None for keyword in call.keywords):
        return False
    # One extra positional for the receiver the attribute call binds to
    # ``self``; the values are placeholders because only the arity and the
    # keyword names are being checked.
    positional = [None] * (len(call.args) + 1)
    keywords = {keyword.arg: None for keyword in call.keywords}
    try:
        signature.bind(*positional, **keywords)
    except TypeError:
        return False
    return True


def _names_bound_to_a_sequence(sources: Mapping[str, str]) -> dict[str, frozenset[str]]:
    """``{module: the names it binds to a sequence display}`` — a vertex list's home.

    Read per module rather than per function, which is the stricter reading and
    the cheaper one: the question :func:`_hides_a_sequence_argument` asks is
    whether a name handed to an excused call could be a sequence, and a name
    that is a list anywhere in a module is answer enough. Assignment, annotated
    assignment and walrus, with a ``Name`` target and a list, tuple, set or
    comprehension on the right.
    """
    found: dict[str, frozenset[str]] = {}
    for module, source in sorted(sources.items()):
        names: set[str] = set()
        for node in ast.walk(ast.parse(source)):
            if not isinstance(node, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
                continue
            if not isinstance(
                node.value,
                (ast.List, ast.Tuple, ast.Set, ast.ListComp, ast.SetComp, ast.GeneratorExp),
            ):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names |= {target.id for target in targets if isinstance(target, ast.Name)}
        found[module] = frozenset(names)
    return found


def _hides_a_sequence_argument(call: ast.Call, sequence_names: frozenset[str]) -> bool:
    """Whether ``call`` hands a positional argument that could be a vertex list.

    The clause that closes CARD-296 review cycle 2's N-3 — the wholly
    positional Pillow call under the vector name, whose arity binds
    ``ContentStream``'s and whose first argument is not a display, so neither
    of the two older clauses saw it. Every positional parameter of the
    ``ContentStream`` methods this excuse covers is a **scalar**: a coordinate,
    a point size or a string. So a positional argument that is a call result,
    or a bare name the module binds to a sequence display, is refused.

    Both measured spellings close on it: ``stream.line(points, 1, 3, None)``
    after ``points = [(i, i) for i in range(32)]``, and
    ``stream.line(_disc(rank), 1, 3, None)``. Named limit: a subscript or an
    attribute (``self.points``) has no binding here to read, and closing that
    means measuring ink — **CARD-241**.

    **What it costs, measured rather than hoped** (the fix round found this on
    a plant of its own, not by reasoning). The ``ast.Call`` arm is
    default-deny, so it also refuses an honest scalar written as a call —
    ``stream.text(str(value), x, y, size)`` is reported. No call the package
    writes today is of that shape (all 21 pass positional ``Name``,
    ``Attribute``, ``BinOp`` or ``Constant``), and the way out is the way out
    of every default-deny rule in this file: bind the scalar to a name, or earn
    a named exemption. That is deliberate — the alternative is a predicate that
    decides which calls return scalars, which is the enumeration ADR-0039/R2
    says not to write.
    """
    return any(
        isinstance(argument, ast.Call)
        or (isinstance(argument, ast.Name) and argument.id in sequence_names)
        for argument in call.args
    )


def _is_accounted_receiver(
    method: str,
    node: ast.AST,
    call: ast.Call | None = None,
    sequence_names: frozenset[str] = frozenset(),
) -> bool:
    """Whether a call of ``method`` on ``node`` is a receiver this guard places.

    Either a Pillow draw object (:func:`_is_draw_receiver`, for any method), or
    a vector content stream (:func:`_is_vector_receiver`) for one of the
    methods a ``ContentStream`` really carries and that cannot be round
    (:data:`VECTOR_STREAM_METHODS`) **and written in that class's own call
    shape** — a call that binds its signature
    (:func:`_binds_the_vector_surface`) and does not pass Pillow's coordinate
    display (:func:`_passes_a_coordinate_display`). Everything else is
    reported.

    The method is part of the question for the vector case and not for the
    Pillow one, which is the asymmetry that keeps the new route narrow:
    ``draw.ellipse`` is a drawing site this guard already measures, while
    ``stream.ellipse`` is a receiver it has never seen and must refuse.

    ``call`` is optional only so a caller that has a receiver and no call node
    can still ask the receiver half of the question; every walk in this file
    passes it, because the shape of the call is half the discrimination.
    ``sequence_names`` is the module's own list-bound names
    (:func:`_names_bound_to_a_sequence`), which is what
    :func:`_hides_a_sequence_argument` needs; left empty, the third clause
    simply cannot fire, so a caller that does not supply it gets the two older
    clauses and no silent widening.
    """
    if _is_draw_receiver(node):
        return True
    if not (_is_vector_receiver(node) and method in VECTOR_STREAM_METHODS):
        return False
    if call is None:
        return True
    return (
        _binds_the_vector_surface(method, call)
        and not _passes_a_coordinate_display(call)
        and not _hides_a_sequence_argument(call, sequence_names)
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
    sequences = _names_bound_to_a_sequence(sources)
    return sorted(
        (module, function, method, ast.unparse(receiver))
        for module, function, method, receiver, call in _draw_method_calls(sources)
        if not _is_accounted_receiver(
            method, receiver, call, sequences.get(module, frozenset())
        )
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


#: How a ``ContentStream`` is constructed, as written: the class's own name,
#: whether imported (``ContentStream(...)``) or reached through its module
#: (``book_vector.ContentStream(...)``). Both spellings are read, for the same
#: reason :func:`_is_draw_receiver` reads both of Pillow's.
VECTOR_STREAM_FACTORY = "ContentStream"

#: The annotation shapes :func:`_content_stream_parameters` understands, and
#: what each one means for the receiver rule. **Default-deny**: an annotation
#: mentioning ``ContentStream`` in a shape not listed here is reported as
#: unrecognised and breaks the equality in
#: :meth:`TestDifficultyDots_HasExactlyOneDrawingSite.test_every_content_stream_in_the_package_is_spelled_stream`,
#: rather than being skipped.
#:
#: * ``one stream`` — the parameter *is* a content stream, so it must be
#:   spelled :data:`VECTOR_RECEIVER_NAME`: it is a receiver the excuse applies
#:   to.
#: * ``a collection of streams`` — an iterable of them
#:   (``write_vector_pdf(pages: Iterable[ContentStream])``). It is **not** a
#:   receiver, so it must *not* be spelled :data:`VECTOR_RECEIVER_NAME`: a draw
#:   method written on a list of streams would otherwise inherit the excuse.
VECTOR_STREAM_CONTAINERS = ("Iterable", "Iterator", "Sequence", "list", "tuple")


def _content_stream_parameters(
    sources: Mapping[str, str],
) -> list[tuple[str, str, str, str]]:
    """Every parameter whose annotation mentions ``ContentStream``, classified.

    ``(module, function, parameter, shape)``, sorted, with ``shape`` one of
    :data:`VECTOR_STREAM_CONTAINERS`' two meanings or ``unrecognised:<text>``.
    Matched on the unparsed annotation text rather than on one ``ast`` shape,
    exactly as :func:`_imagedraw_annotated_parameters` is and for the same
    reason: a string annotation, an ``Optional[...]`` and a keyword-only
    parameter all count.
    """
    found: list[tuple[str, str, str, str]] = []
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
            if argument.annotation is None:
                continue
            text = ast.unparse(argument.annotation).strip("'\"")
            if VECTOR_STREAM_FACTORY not in text:
                continue
            bare = text.removeprefix("Optional[").removesuffix("]")
            if bare.split(".")[-1] == VECTOR_STREAM_FACTORY or bare.replace(
                " | None", ""
            ).split(".")[-1] == VECTOR_STREAM_FACTORY:
                shape = "one stream"
            elif text.split("[")[0] in VECTOR_STREAM_CONTAINERS:
                shape = "a collection of streams"
            else:
                shape = f"unrecognised:{text}"
            found.append((module, node.name, argument.arg, shape))
    return sorted(found)


def _content_stream_bindings(
    sources: Mapping[str, str],
) -> list[tuple[str, str, str, str]]:
    """Every ``ContentStream(...)`` call written in the package, by its form.

    ``(module, enclosing function, form, name)``, sorted — the same
    classification :func:`_draw_object_bindings` applies to
    ``ImageDraw.Draw(...)``, pointed at the vector constructor, so the name
    ``stream`` is bound by a rule rather than by convention (review cycle 1,
    F-4). Unrecognised forms are reported, not skipped.
    """
    bindings: list[tuple[str, str, str, str]] = []
    for module, function, parent, node in _enclosing_walk(sources):
        if not isinstance(node, ast.Call):
            continue
        factory = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
        if factory != VECTOR_STREAM_FACTORY:
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
        elif isinstance(parent, ast.Return):
            # CARD-295's book_vector_draw returns a freshly built stream
            # (book_vector_draw.py:116). Nothing is bound, so there is no
            # name for the vector excuse to be borrowed by -- which is the
            # risk the name rule below exists to close. Named rather than
            # folded into DRAW_BINDING_FORMS, because that set carries an
            # obligation ("the name must be `stream`") that a return has
            # nothing to satisfy it with.
            form = "return"
        elif isinstance(parent, ast.Attribute) and parent.value is node:
            form = "receiver"
        elif isinstance(parent, ast.Call) and node in (
            *parent.args,
            *(keyword.value for keyword in parent.keywords),
        ):
            form = "argument"
        bindings.append((module, function, form, name))
    return sorted(bindings)


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

        The equality above says *which* sites are excused; this says *why*, so
        an exemption cannot quietly grow into one that could draw. There are
        two families and each is asked its own question — a single question
        asked of both would have to be the weaker of the two.

        * **A pixel map** (``Image.point``): the discriminating property is
          that it takes no coordinates — a table built with ``*`` and ``+``, or
          a lambda. A future card that writes a coordinate display on such a
          receiver fails here instead of inheriting the excuse.
        * **The vector operator recorder** (``ContentStream``, CARD-295): the
          discriminating property is the class's own surface. It is read off
          ``dir()`` rather than asserted from the table's comment, so the day
          somebody gives a content stream an ``ellipse`` the excuse stops
          applying here — which is the shape of the defect this family would
          otherwise introduce, a second drawing medium arriving with an
          exemption nobody re-earns.
        """
        from nonogram.admin.book_vector import ContentStream

        sources = _package_sources()
        sequences = _names_bound_to_a_sequence(sources)
        exempt = [
            (module, function, method, call)
            for module, function, method, receiver, call in _draw_method_calls(sources)
            if not _is_accounted_receiver(
                method, receiver, call, sequences.get(module, frozenset())
            )
        ]
        assert len(exempt) == len(NON_DRAW_RECEIVER_SITES)
        surface = set(dir(ContentStream))
        assert not surface & (ELLIPSE_METHODS | ROUND_ENOUGH_METHODS), sorted(
            surface & (ELLIPSE_METHODS | ROUND_ENOUGH_METHODS)
        )
        for module, function, method, call in exempt:
            if method in VECTOR_STREAM_METHODS:
                assert module.endswith("book_vector_draw"), (module, function, method)
                # Scalars, never a vertex display: `ContentStream.line` takes
                # four numbers and `rectangle` four edges, so neither can be
                # handed the polygon a round mark would need.
                assert not any(
                    isinstance(argument, SEQUENCE_DISPLAYS)
                    for argument in call.args
                ), (module, function, "a vertex display on a content stream")
                continue
            assert method == "point", (module, function, method)
            argument = call.args[0] if call.args else None
            assert not isinstance(argument, SEQUENCE_DISPLAYS), (
                module,
                function,
                "a coordinate display on a receiver excused as a pixel map",
            )
        # And the excused names are never a draw object anywhere in the
        # package, so the excuse cannot be borrowed by rebinding the name.
        bound = {name for _, _, _, name in _draw_object_bindings(sources)}
        for _module, _function, _method, spelling in NON_DRAW_RECEIVER_SITES:
            assert spelling not in bound, spelling

    def test_the_vector_stream_receiver_is_excused_only_for_marks_that_cannot_be_round(
        self,
    ) -> None:
        """CARD-296's fifth route — earned by what a ``ContentStream`` carries.

        The exemption :data:`VECTOR_RECEIVER_NAME` grants is the same shape as
        :data:`NON_DRAW_RECEIVER_SITES`': an excuse plus a control for what it
        must **not** absorb. Three things are asserted, each of which can
        fail on its own:

        * the excused set is non-empty — an empty one would excuse nothing and
          make the route decorative;
        * it meets none of the three families that could put a round mark on a
          page, so a ``ContentStream`` that grew an ``ellipse``, a ``polygon``
          or a ``rounded_rectangle`` would not be excused for it;
        * and a planted ``stream.ellipse(...)`` really is still reported,
          which is the only way to know the second point is live rather than
          true-by-arithmetic.

        The round shape a content stream *does* have is ``round_mark``, which
        is in none of this guard's families because PDF has no circle
        operator. Its control is named on
        :data:`VECTOR_RECEIVER_NAME` and lives with the vocabulary's own
        tests; it is not restated here.
        """
        assert VECTOR_STREAM_METHODS
        assert VECTOR_STREAM_METHODS <= TEXT_METHODS | FLAT_METHODS

        # The narrowing, shown on a surface that could exercise it. Against
        # ``ContentStream`` the subtraction is a no-op (it carries none of
        # those names), so asserting the real set avoids them proves nothing
        # about the rule.
        class _RoundCapableSurface:
            def line(self): ...

            def text(self): ...

            def ellipse(self): ...

            def polygon(self): ...

            def rounded_rectangle(self): ...

        assert _excused_vector_methods(_RoundCapableSurface) == {"line", "text"}

        rogue = {
            "planted.module": (
                "def draw_a_dot(stream):\n"
                "    stream.ellipse((0, 0, 10, 10), fill=0)\n"
                "    stream.polygon([(0, 0), (1, 0), (1, 1)], fill=0)\n"
            )
        }

        assert _unrecognised_draw_receivers(rogue) == [
            ("planted.module", "draw_a_dot", "ellipse", "stream"),
            ("planted.module", "draw_a_dot", "polygon", "stream"),
        ]

    def test_every_content_stream_in_the_package_is_spelled_stream(self) -> None:
        """What makes the name ``stream`` narrow — the rules ``draw`` already has.

        Review cycle 1 (F-4) measured the hole this closes: the exemption was
        granted to **any** ``ast.Name`` spelled ``stream``, and nothing in the
        tree asserted that such a thing is a ``ContentStream``. The name
        ``draw`` is safe because two sibling rules bind it
        (:meth:`test_every_draw_object_in_the_package_is_spelled_draw` and
        :meth:`test_every_imagedraw_annotated_parameter_is_spelled_draw`); this
        is those two rules for the vector name, from all three ends:

        * every ``ContentStream(...)`` construction that yields a name yields
          this one, and a binding form nobody taught the walk is reported
          rather than skipped;
        * every parameter that *is* a content stream is spelled it, and every
          parameter that is a *collection* of them is not — a draw method
          written on a list of streams would otherwise inherit the excuse;
        * and the name is never a Pillow draw object: no
          ``ImageDraw.Draw(...)`` binding and no ``ImageDraw``-annotated
          parameter is spelled ``stream``, so the excuse cannot be borrowed by
          taking the name.
        """
        sources = _package_sources()

        bindings = _content_stream_bindings(sources)
        assert bindings, (
            "the walk found no ContentStream(...) call in the package — this "
            "rule has gone vacuous; keep it honest with the fabricated sources "
            "in test_a_content_stream_bound_to_another_name_is_caught"
        )
        named = sorted({name for _m, _f, form, name in bindings if form in DRAW_BINDING_FORMS})
        assert named == [VECTOR_RECEIVER_NAME], named
        unbound = sorted(
            form for _m, _f, form, _n in bindings if form not in DRAW_BINDING_FORMS
        )
        # An EQUALITY, not a subset: exactly one construction in the package
        # binds no name -- ``book_vector_draw.py:116``'s ``return
        # ContentStream(...)`` -- and a second is a failure to look at rather
        # than a pattern to absorb. A ``receiver`` or ``argument`` form would
        # red here too, which is intended: a stream handed straight into a
        # call is a shape nothing above reasons about.
        assert unbound == ["return"], unbound

        parameters = _content_stream_parameters(sources)
        shapes = {shape for _m, _f, _p, shape in parameters}
        assert shapes <= {"one stream", "a collection of streams"}, sorted(shapes)
        receivers = [
            (module, function, parameter)
            for module, function, parameter, shape in parameters
            if shape == "one stream"
        ]
        assert {parameter for _m, _f, parameter in receivers} == {
            VECTOR_RECEIVER_NAME
        }, receivers
        # A floor rather than an equality: six such parameters exist today and
        # a card that adds a seventh is doing nothing wrong. The floor is here
        # only so the rule cannot pass by finding nothing.
        assert len(receivers) >= 6, receivers
        for module, function, parameter, shape in parameters:
            if shape == "a collection of streams":
                assert parameter != VECTOR_RECEIVER_NAME, (module, function)

        # And the name is never a draw object, from either direction.
        assert VECTOR_RECEIVER_NAME not in {
            name for _m, _f, _form, name in _draw_object_bindings(sources)
        }
        assert VECTOR_RECEIVER_NAME not in {
            parameter for _m, _f, parameter in _imagedraw_annotated_parameters(sources)
        }

    def test_a_pillow_call_wearing_the_vector_name_is_caught(self) -> None:
        """Control, caught: cycle 2's M2 with the parameter renamed ``stream``.

        The mutant review cycle 1 (F-4) reopened — an unannotated parameter
        handed the real draw object, drawing a 32-point polyline on it, under
        the one name the vector route excuses and through ``line``, which
        :data:`FLAT_METHODS` documents as a known hole. **Measured before the
        fix: the pre-CARD-296 rule reported it and the CARD-296 rule reported
        nothing** — the new route had widened a hole rather than adding one.

        It is caught on the shape of the call — ``ContentStream``'s own
        signature (:func:`_binds_the_vector_surface`), Pillow's coordinate
        display (:func:`_passes_a_coordinate_display`) and, since CARD-296
        review cycle 2, a positional argument that could be a sequence
        (:func:`_hides_a_sequence_argument`) — which is the half of the
        discrimination that does not depend on what the parameter is called.
        **Every spelling is planted and each clause is load-bearing on a
        different one**: ``fake.literal`` on the display clause,
        ``fake.positional`` on the signature clause, and
        ``fake.positional_line``/``fake.positional_call`` on the sequence
        clause — those last two were reported by nothing at all until it
        landed. The last half of the control is the five mechanisms that stay
        blind to them, which is what made it worth measuring.
        """
        points = ", ".join(f"({index}, {index})" for index in range(32))
        rogue = {
            "fake.literal": (
                "def _rogue(stream, rank):\n"
                f"    stream.line([{points}], fill=1, width=3)\n"
            ),
            "fake.name": (
                "def _rogue(stream, rank):\n"
                "    points = [(index, index) for index in range(32)]\n"
                "    stream.line(points, fill=1, width=3)\n"
            ),
            # Pillow's ``rectangle(xy, fill, outline, width)`` written wholly
            # positionally: four positional arguments, so it *binds*
            # ``ContentStream.rectangle(left, top, right, bottom)``'s arity and
            # only the coordinate display gives it away. The two clauses catch
            # different plants, which is why both are here.
            "fake.positional": (
                "def _rogue(stream, rank):\n"
                "    stream.rectangle([(0, 0), (10, 10)], 0, 0, 3)\n"
            ),
            # CARD-296 review cycle 2, N-3: Pillow's ``line(xy, fill, width,
            # joint)`` written WHOLLY POSITIONALLY with a bare-name vertex
            # list. Four positionals bind ``ContentStream.line``'s arity
            # exactly and a bare ``Name`` is not a display, so both older
            # clauses pass it; measured reported by NOTHING before
            # ``_hides_a_sequence_argument``. Both of that finding's spellings
            # are here — the bound name, and the call result.
            "fake.positional_line": (
                "def _rogue(stream, rank):\n"
                "    points = [(index, index) for index in range(32)]\n"
                "    stream.line(points, 1, 3, None)\n"
            ),
            "fake.positional_call": (
                "def _rogue(stream, rank):\n"
                "    stream.line(_disc(rank), 1, 3, None)\n"
            ),
        }

        assert _unrecognised_draw_receivers(rogue) == [
            ("fake.literal", "_rogue", "line", "stream"),
            ("fake.name", "_rogue", "line", "stream"),
            ("fake.positional", "_rogue", "rectangle", "stream"),
            ("fake.positional_call", "_rogue", "line", "stream"),
            ("fake.positional_line", "_rogue", "line", "stream"),
        ]
        # Blind without it: the vertex guard filters on a draw receiver, there
        # is no `.Draw(...)` for the binding rule, no annotation for the
        # annotation rule, and no `ContentStream(...)` for the vector binding
        # rule either — the name alone was the whole of the excuse.
        assert _draw_calls(rogue, VERTEX_BOUNDED_METHODS) == []
        assert _draw_object_bindings(rogue) == []
        assert _imagedraw_annotated_parameters(rogue) == []
        assert _content_stream_bindings(rogue) == []

    def test_the_vector_calls_the_package_really_writes_are_not_caught(self) -> None:
        """Control, not caught: the honest spelling must pass, or the rule is a ban.

        ``ContentStream``'s own call shape — scalars, and a string for text —
        on the name the binding rules hold to a content stream. Without this
        the shape rule's discriminating power would be unknown.
        """
        honest = {
            "fake.mod": (
                "def page(frame, dpi):\n"
                "    stream = ContentStream(width_px=frame.width, height_px=1, dpi=dpi)\n"
                "    stream.line(0, 0, 10, 10)\n"
                "    stream.rectangle(0, 0, 10, 10, paint='fill')\n"
                "    stream.text('3', 1.0, 2.0, 11.0)\n"
            )
        }

        assert _unrecognised_draw_receivers(honest) == []
        assert _content_stream_bindings(honest) == [
            ("fake.mod", "page", "assignment", "stream")
        ]

    def test_a_content_stream_bound_to_another_name_is_caught(self) -> None:
        """Control, caught: the binding rule, on fabricated sources.

        A content stream under another name is not a failure of taste: the
        receiver excuse is granted on the name, so a second spelling is a
        second route into it. The unrecognised forms are reported too, exactly
        as :meth:`test_an_unrecognised_draw_binding_form_is_caught` reports
        Pillow's.
        """
        rogue = {
            "fake.named": "def page(dpi):\n    canvas = ContentStream(dpi=dpi)\n",
            "fake.attr": "def page(self, dpi):\n    self.canvas = ContentStream(dpi=dpi)\n",
            "fake.module": "def page(dpi):\n    sheet = book_vector.ContentStream(dpi=dpi)\n",
        }
        bindings = _content_stream_bindings(rogue)

        assert bindings == [
            ("fake.attr", "page", "unrecognised assignment target (Attribute)", "<unbound>"),
            ("fake.module", "page", "assignment", "sheet"),
            ("fake.named", "page", "assignment", "canvas"),
        ], bindings
        # NOT re-asserted here that the bound names are not {VECTOR_RECEIVER_NAME}:
        # the equality above has already pinned them to {"sheet", "canvas"}, so
        # such a line cannot fail given the line above it, and it read as a
        # second check without being one (CARD-296 review cycle 2, N-5). The
        # live form of that claim is
        # ``test_every_content_stream_in_the_package_is_spelled_stream``, over
        # the real package.

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

#: How many connected ink regions the baseline interior's 13 pages must still
#: carry, at **each** measured threshold — the denominator that keeps "no round
#: mark on these pages" from being a statement about a blank book.
#:
#: 2600, just under the 2640 measured on this tree at both grey 128 and grey
#: 208. What moved it is CON-018's amendment: the amended interior margins
#: leave the usable area 1.6 % narrower and 2.6 % shorter, so every grid not
#: already at the 7.5 mm cell cap prints smaller and merges ink that used to
#: separate. Re-derived on the merged tree rather than inherited from either
#: card of wave 44, and corroborated by measuring ``main`` at ``c2b0646``
#: beside this branch through the same ``_book_ink(None)``: 3222 regions and
#: margin 1.885921 there, 2640 and 1.885525 here, so the whole difference is
#: the margin amendment and nothing else.
REGION_FLOOR = 2600

#: The seeded picture corpus AC-2 sweeps, and the two floors it must clear
#: (CLAUDE.md: no ``hypothesis``, a corpus with its minimum asserted inside the
#: test so it cannot silently shrink). The second floor is the load-bearing
#: one: a corpus of blank grids would satisfy the first and measure nothing.
PICTURE_SEED = 241
PICTURE_MIN_PAGES = 18
PICTURE_MIN_CELLS = 400

#: And CARD-243's third floor: how many pixels of this corpus are paper to
#: :data:`INK_LEVEL` and a mark to :data:`MARK_LEVEL`. 245 710 when measured
#: on CON-018's amended margins (265 543 before them),
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
    **1.8855** at the black threshold, carried by ``fill`` alone on a 99 x 95
    filled block (``aspect`` 1.0421 — already inside
    :data:`ROUND_ASPECT_TOLERANCE`); **1.8182** at the widened one, carried by
    ``aspect`` on a 7 x 11 letter stem (``fill`` 0.8599, outside its tolerance
    too). Both numbers, each mark's **footprint**, and *which* tolerance
    carries each are asserted in
    :meth:`test_the_closest_the_book_comes_to_a_round_mark_is_measured`, and
    each tolerance's own room is measured separately in
    :meth:`test_each_tolerances_own_room_on_the_book_is_measured` — because
    the margin is whichever binds first and that hides the other (CARD-241
    cycle 1, F-003, where the 2.27 quoted here was the letter-stem family's
    aspect room and not the closest mark at all).

    **The footprint rather than the box** (CARD-243 review, F-001). Pinning
    ``closest.box`` pins one member of a tie: at the widened threshold eleven
    7 x 11 stems sit at exactly 1.8182 and which of them is reported is page
    and region iteration order, so any geometry change flips the box while the
    margin and the binding tolerance are untouched — and the failure then
    reads "the margin is no longer carried by aspect", which is not what
    happened. CON-018's amended margins did precisely that: every figure below
    was re-derived on this tree, and the only ones that *moved* were the two
    the fall in region size touches (the margin's fourth decimal and
    ``aspect``'s own room). So what is asserted is ``(width, height)`` — the
    shape the claim is about — and, for the block that sets ``fill``'s room,
    that the **same region** sets it at both thresholds. Position is
    deliberately not pinned: it is the one thing a page-layout change is
    *allowed* to move.

    Every floor sits just under its measured value, so a future page whose ink
    drifts towards roundness reds a test *before* it reds the guard.
    """

    def test_the_books_own_pages_carry_no_undeclared_round_mark(self) -> None:
        """ADR-0036/R3's declared check, now asked at both thresholds."""
        ink = _book_ink(None)
        assert ink.pages >= 13, f"the baseline interior lost pages: {ink.pages}"
        # Both cards' claims, kept: CARD-243's per-level loop (the floor and the
        # quiet-book assertion hold at EACH measured threshold, not aggregated)
        # and CARD-222's lowered floor, :data:`REGION_FLOOR` — see there for the
        # measurement it is set from and for the two readings of `main` and this
        # branch that attribute the whole fall to CON-018's amended margins.
        for level in MEASURED_LEVELS:
            assert ink.at[level].regions >= REGION_FLOOR, (
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
            f"population: {ink.widened_pixels} (58424 when measured; 76347 "
            "before CON-018's amended margins shrank the usable area)"
        )

    def test_the_closest_the_book_comes_to_a_round_mark_is_measured(self) -> None:
        """The margin at **both** thresholds, and which tolerance carries each.

        Re-measured for CARD-243 rather than inherited, because the widened
        threshold brings the book's own greys and every glyph's anti-aliased
        edge into the population the margin is taken over. What it comes to:

        * at :data:`INK_LEVEL`, **1.8855** on a 99 x 95 filled block,
          ``aspect`` 1.0421 and ``fill`` 1.2263 — the single nearest region on
          the pages, no tie. The widening does not move it, which is the point
          of keeping the reading;
        * at :data:`MARK_LEVEL`, **1.8182**, and the closest mark is a
          *different* one: a 7 x 11 letter stem, ``aspect`` 0.6364, ``fill``
          0.8599, one of eleven at exactly that distance. It is the same stem
          family that is 6 x 11 at the black threshold, one pixel wider for
          its own grey edge — and at that width its ``fill`` leaves the fill
          tolerance, so the number is now carried by ``aspect``.

        **What CON-018's amended margins did to these two readings, measured
        rather than assumed.** Both were 1.8859 / 1.8182 on the old margins
        (re-measured on ``main`` at ``c2b0646``: closest at grey 128 a 99 x 94
        block, ``aspect`` 1.0532, ``fill`` 1.2263, ink 8963). The amended
        margins print the guide page's blocks one row taller and one pixel of
        ink lighter — 99 x 95, ink 9058, ``fill`` 1.2263 to four places still —
        so the black margin falls by 0.0004 to **1.8855**, and the widened
        reading does not move at all: its stem is 7 x 11 on both trees, and
        ``aspect`` on a 7 x 11 box is 7/11 whatever the page around it does.
        So the margin did **not** change hands under this card, and the
        quantity that did change is the one the fourth decimal records.

        Both halves matter and neither is a conclusion drawn from the other:
        between the thresholds the margin *moves* (down 0.067, by 3.6 %) and
        *changes hands*. The floor stays at 1.8, just under the measured
        1.8182, for the reason CARD-241 set it there: a floor at 1.5 would let
        the margin fall by a fifth in silence (cycle 1, F-003).
        """
        ink = _book_ink(None)
        black, widened = ink.at[INK_LEVEL], ink.at[MARK_LEVEL]
        for level in (black, widened):
            assert level.margin >= 1.8, (
                f"the roundest mark on the book's pages at level {level.level} "
                f"is now {level.margin:.4f} tolerances from round; it was "
                "1.8855 at the black threshold and 1.8182 at the widened one "
                "when they were set, and under 1.0 it would be a false positive"
            )
            assert level.closest is not None, "a book with no region to measure"
        # CARD-241's reading, unchanged by the widening: the same block, the
        # same number, still carried by `fill` alone. Its FOOTPRINT is pinned
        # and its position is not — see the class docstring's "the footprint
        # rather than the box" for why (CARD-243 review, F-001).
        assert (black.closest.width, black.closest.height) == (99, 95), black.closest
        assert black.margin == pytest.approx(1.8855, abs=5e-4), black.margin
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
        # One of eleven 7 x 11 stems at exactly this distance, so the footprint
        # is the claim and the box is not: which member is reported is page and
        # region iteration order (CARD-243 review, F-001).
        assert (widened.closest.width, widened.closest.height) == (
            7,
            11,
        ), widened.closest
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
        ``ROUND_FILL``          1.8855      1.8855        the 99 x 95 block
        ``ROUND_ASPECT``        2.2727      46.5789       a letter stem / a rule
        ======================  ==========  ============  ==============

        So the widening leaves ``fill``'s room on the book **exactly where it
        reads at the black threshold** — the 99 x 95 filled block is a
        hard-edged rectangle and has no grey edge to grow by, and it is
        literally the same region at both, which is asserted rather than said
        — and it *widens* ``aspect``'s, from 2.27 to 46.58, because the letter
        stem that used to sit 2.27 tolerances out with a disc's ``fill`` grew a
        grey pixel and left the fill tolerance altogether. Both tolerances
        therefore keep their values because the measurement says so, which is
        the outcome AC-3 allows; what moved is recorded here rather than in a
        docstring.

        **And CON-018's amended margins moved two of the four**, re-derived on
        this tree against ``main`` at ``c2b0646``: ``fill``'s room falls
        1.8859 → **1.8855** at both thresholds (the block it is set on is
        99 x 95 now, not 99 x 94), and ``aspect``'s room at grey 208 falls
        47.1809 → **46.5789**, because the guide-page rule that sets it is
        980 x 95 on the narrowed text block rather than 981 x 94. ``aspect``'s
        room at grey 128 is **unchanged at 2.2727**: it is set by a 6 x 11
        stem, and 6/11 does not care how wide the page is. No tolerance was
        touched to keep any of this green.
        """
        ink = _book_ink(None)
        black, widened = ink.at[INK_LEVEL], ink.at[MARK_LEVEL]
        assert black.fill_headroom == pytest.approx(1.8855, abs=5e-4), black
        assert widened.fill_headroom == pytest.approx(1.8855, abs=5e-4), widened
        # The footprint, not the position (CARD-243 review, F-001) — and then
        # the claim the two readings share: it is the SAME region that sets
        # `fill`'s room at both thresholds, which is what "the block has no
        # grey edge to grow by" means and what a pair of equal numbers alone
        # would not show.
        assert (black.fill_closest.width, black.fill_closest.height) == (
            99,
            95,
        ), black.fill_closest
        assert widened.fill_closest.box == black.fill_closest.box, (
            "`fill`'s room is set by a hard-edged block with no grey edge, so "
            "the widened threshold must find the very same region; it now "
            f"finds {widened.fill_closest.box} against {black.fill_closest.box}"
        )
        assert black.aspect_headroom == pytest.approx(2.2727, abs=5e-4), black
        assert widened.aspect_headroom == pytest.approx(46.5789, abs=5e-4), widened
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
        than before (3689 at the black threshold, 3540 at the widened one;
        4236 and 4087 before CON-018's amended margins). It
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


# ==========================================================================
# CARD-331 — the dots' claim, and one instrument arm per medium, each able
# to die loudly
#
#     AC-1  TestDifficultyDots_TheClaimIsAboutThePageNotTheCall
#     AC-2  TestDifficultyDots_TheVectorArmReadsTheStream
#     AC-3  TestDifficultyDots_TheRasterArmHoldsWithoutHookingTheProduct
#     AC-4  TestDifficultyDots_AnArmWhoseMechanismIsDeadFails
#     AC-5  the per-assertion mutant table in CARD-331's ``## Worktree notes``
#     AC-6  the existing ``test_no_declaration_outlives_the_cards_that_remove_it``
#           in ``tests/test_book_pdf.py``, unmodified — nothing here converts a
#           page or touches ``_RASTER_DECLARATIONS``
#
# Why this section exists, and what the card's premise turned out to be
# ---------------------------------------------------------------------
# Everything above measures a **bitmap**. :func:`_interior_ink` renders the
# interior and hooks two module attributes to do it, and ADR-0042/R1 is
# converting the interior to pages written as operators — so the card's
# question was what those 27 cells do on a page the product stops drawing.
#
# **The card's premise was that they pass silently. Measured on this branch,
# they do not — and the measurement matters, because it says what this section
# has to add and what it does not.** Lifting ``PageKind.PUZZLE`` out of
# ``_RASTER_DECLARATIONS`` (``scratchpad/card331/probe_puzzle_vector.py``) reds
# **27** of this module's 155 cells, every one of them at the same line and
# with the same message: ``'ContentStream' object has no attribute 'convert'``.
# The accounting never runs at all; the render loop dies on the page object's
# type first. That is a failure and not a silent pass, so ADR-0039/R2 is
# satisfied *today* — by accident, by a type mismatch whose message names
# neither a dot nor a dead hook.
#
# **What is a silent pass is the next step, and it is one patch away.** The
# obvious way to make the instrument medium-tolerant is to stop reading the
# pages it cannot read. Doing exactly that
# (``scratchpad/card331/probe_medium_tolerant.py``: the declaration lifted and
# ``interior_pages`` filtered to the bitmaps) leaves **13** of the 27 red and
# turns **14 green** — on a book whose puzzle pages are no longer in the
# measurement. The 13 that survive are the ones the author floored by hand
# (``plants >= 6``, ``pages >= 13``, :data:`REGION_FLOOR`); the 14 that go
# green include ``test_every_spelling_is_caught``,
# ``test_every_route_the_table_says_is_closed_is_caught_on_the_page`` and
# ``test_the_limits_list_is_exactly_the_routes_no_instrument_closes`` — three
# claims about what the instrument catches, passing on four answer-page bands
# with nothing saying that the puzzle pages left the corpus. Both node lists
# are in ``scratchpad/card331/``.
#
# So what this section adds is not a louder failure for a type error. It is
# the thing neither probe produced: an arm **per medium**, each naming the
# mechanism its accounting comes out of, and a guard that reds when an arm's
# mechanism stops being exercised — whatever the page object's type turns out
# to be on the day it stops.
#
# The two arms are **different instruments with different domains**, and
# nothing here differences one against the other (CARD-330): the raster arm
# accounts ink extents in device pixels against declared boxes in device
# pixels, and the vector arm accounts path coordinates in points against
# declared boxes converted to points. Where the two arms' verdicts on one
# glyph differ, that difference is measured and asserted rather than tolerated
# — see
# :meth:`TestDifficultyDots_TheVectorArmReadsTheStream.test_a_stroked_ring_is_round_to_this_arm_and_hollow_to_the_other`.
# ==========================================================================

#: Points per device pixel at :data:`DPI` — this file's own conversion, for
#: the same reason :data:`DPI` and :func:`_px` are written out here.
#:
#: At 300 DPI it is 0.24 pt exactly, which is an exact multiple of the
#: 1/1000 pt a content stream rounds its operands to
#: (``book_vector._PLACES``), so a dot box on an integer pixel reaches the
#: stream **exactly** and the vector arm's accounting needs no tolerance at
#: all. That is a property of this resolution and not of the writer:
#: :meth:`TestDifficultyDots_TheVectorArmReadsTheStream.test_an_integer_pixel_reaches_the_stream_exactly`
#: derives it, so a book drawn at a DPI where it stops being true reds here
#: rather than failing to match by a thousandth of a point.
PT_PER_PX = 72.0 / DPI


# --------------------------------------------------------------------------
# AC-1 — the claim, written in terms of the page
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class DotClaim:
    """What must be true of **the page** for one difficulty (AC-1).

    Not "which function was called": every field below is something a reader
    of the printed page could check with a ruler, and every one of them is
    asserted on a real page of **each** medium in
    :class:`TestDifficultyDots_TheClaimIsAboutThePageNotTheCall`.

    Attributes:
        tier: The difficulty this row of dots is about.
        solid: How many of the row's dots are filled in — the rank a reader
            counts. Stated as the tier's own 1-based position on
            :data:`~nonogram.admin.book_plan.TIERS`, the project's one ladder,
            which is where :func:`_rank` reads it and where the drawing site
            reads it; there is deliberately no second ladder here.
        dots: How many dots the row has in all, filled and outlined together
            — ``len(TIERS)``, so the glyph reads as *n of three* and the total
            cannot drift from the ladder's length.
    """

    tier: Tier
    solid: int
    dots: int


#: The dots' claim, per difficulty — one row per tier of the project's own
#: ladder, in the ladder's order.
#:
#: Built from :data:`~nonogram.admin.book_plan.TIERS` rather than written out,
#: so a tier added to the project arrives here with it; the covering check is
#: :meth:`TestDifficultyDots_TheClaimIsAboutThePageNotTheCall.test_the_claim_covers_every_tier_the_project_has_exactly_once`,
#: which holds this table to that enumeration in both directions and to its
#: own length, so a row dropped or a row duplicated reds independently of the
#: table that built it.
THE_CLAIM: tuple[DotClaim, ...] = tuple(
    DotClaim(tier=tier, solid=index + 1, dots=len(TIERS))
    for index, tier in enumerate(TIERS)
)

#: What the claim is about, beside the counts: the three page facts that are
#: the same on both media, written as prose a reader can check and read back
#: by
#: :meth:`TestDifficultyDots_TheClaimIsAboutThePageNotTheCall.test_the_claim_is_stated_about_the_page_and_names_no_function`.
#:
#: Each is measured, on each medium, by the test named beside it.
CLAIM_PLACEMENT = (
    "every dot of a row lies inside the box the row was given, in one "
    "horizontal line, and no two of them touch"
)
CLAIM_SIZE = (
    "every dot of a row is the same size, and square: its footprint is as "
    "wide as it is tall"
)
CLAIM_COUNT = (
    "a row carries one dot per tier the project has, and the tier's own "
    "1-based position on that ladder is how many of them are filled in"
)

#: The three statements above, as the table AC-1's test reads.
THE_CLAIMS_PROSE = (CLAIM_COUNT, CLAIM_PLACEMENT, CLAIM_SIZE)

#: The names a statement of the claim must **not** carry: the drawing sites,
#: the media's primitives and the hooks. A claim that names one of these is a
#: claim about a call, which is the shape this card exists to replace.
#:
#: They are the names of real things in this tree, so the list cannot be
#: checked against nothing:
#: :meth:`TestDifficultyDots_TheClaimIsAboutThePageNotTheCall.test_the_forbidden_names_are_things_that_really_exist`
#: resolves every one of them to an attribute of the module that owns it.
CALL_NAMES_THE_CLAIM_MAY_NOT_USE = (
    "_draw_difficulty_dots",
    "_set_band",
    "round_mark",
    "ellipse",
    "monkeypatch",
)


# --------------------------------------------------------------------------
# The two arms, and the one page each of them reads
# --------------------------------------------------------------------------
#
# Both arms read **the same puzzle page of the same book**, written twice: the
# raster twin through ``_blank_page`` and the vector twin through
# ``vector_puzzle_page``. Writing one page both ways is what the assembly
# point already makes possible (AC-6) and it converts nothing: ``page_medium``
# is not consulted here and ``_RASTER_DECLARATIONS`` is not touched, so the
# book this branch ships is byte-for-byte the book ``main`` ships.


@dataclass(frozen=True)
class ArmPage:
    """One puzzle page of the baseline book, written as both media.

    Attributes:
        bitmap: The page ``_blank_page`` draws — the raster arm's reading.
        stream: The page ``vector_puzzle_page`` writes — the vector arm's.
        box: The box a difficulty glyph would occupy in that page's band, as
            :func:`_plant_box` gives it: the same box the legacy harness
            plants in, so the two arms and the 27 cells are measuring one
            place on one page.
        width_px: The page's width in device pixels.
        height_px: The page's height in device pixels — the vector arm's only
            conversion, because a content stream counts y **up** from the
            page's bottom edge and a ``Layout`` counts it down from the top.
    """

    bitmap: Image.Image
    stream: ContentStream
    box: tuple[int, int, int, int]
    width_px: int
    height_px: int


def _arm_page() -> ArmPage:
    """The baseline book's first single-puzzle page, written as both media.

    The layout is recomputed here, from the same ``_puzzle_page_spec`` and the
    same ``compute_layout`` the writer calls, because the band's own geometry
    is what a glyph's box is measured in and the writer does not hand it back.
    That recomputation is **checked** rather than trusted, and checked
    narrowly:
    :meth:`TestDifficultyDots_TheVectorArmReadsTheStream.test_the_page_extent_this_arm_flips_y_about_is_the_streams_own`
    holds the stream's own ``MediaBox`` to it, so the **extent** the y-flip is
    done against cannot drift unnoticed.

    Read that as exactly what it says. It is *not* a check that the recomputed
    layout is the writer's in every respect, and the wider sentence this
    docstring used to carry — that a drifted layout "would red instead of
    putting the declared dots in the wrong place" — is **retracted**: this
    round measured it false. A one-pixel drift of the recomputed extent reds
    one cell and one only (that one), because :func:`_appended` builds its
    scratch stream from the same figure, so the accounting stays
    self-consistent and the declared dots are *not* put in the wrong place; and
    a page-number drift leaves the band's centre and the glyph's box
    bit-identical, so it is invisible here altogether. The cell's own docstring
    states both limits (ADR-0039/R4: a refuted figure is retracted everywhere
    it was written).

    A **single**-puzzle page, not a two-up one: a two-up sheet carries two
    bands and the accounting would then be about which of them a plant landed
    in, which is a second question. The two-up page is where this arm would go
    next, and it is not in this card. So the page is composed directly, one
    puzzle on one sheet at one interior position, exactly as
    ``tests/test_book_puzzle_page_vector.py``'s own ``twin`` fixture composes
    it — the pairing walk is not consulted, and :data:`FIRST_PUZZLE_PAGE` says
    where the sheet sits.
    """
    generator = BookPDFGenerator(corpus_book())
    payloads = [
        BookPDFGenerator._payload(row)
        for row in book_pdf_generator.print_order(baseline_puzzles())
    ]
    sizes = generator.cell_sizes(payloads)
    payload = payloads[0]
    spec = generator._puzzle_page_spec(
        FIRST_PUZZLE_PAGE, sizes.get(generator._grid_size(payload))
    )
    layout = compute_layout(payload.row_clues, payload.column_clues, spec)
    placement = layout.page
    assert placement is not None, "a book page is a placed page"
    box = _plant_box(
        header_band(layout), placement.usable_right - placement.usable_left
    )
    assert box is not None, "the baseline book's band is big enough for a glyph"
    return ArmPage(
        bitmap=generator._blank_page(payload, 1, FIRST_PUZZLE_PAGE, sizes),
        stream=generator.vector_puzzle_page(payload, 1, FIRST_PUZZLE_PAGE, sizes),
        box=box,
        width_px=layout.width,
        height_px=layout.height,
    )


@pytest.fixture(scope="module")
def arm_page() -> ArmPage:
    """:func:`_arm_page`, once for the module: the bitmap half is 25 MB."""
    return _arm_page()


def _stream_text(stream: ContentStream) -> str:
    """``stream``'s operators as the one string the vector reader takes."""
    return "\n".join(stream.operators)


def _declared_in_points(
    dot: tuple[int, int, int, int], height_px: int
) -> tuple[float, float, float, float]:
    """``dot``'s box, in the **stream's** domain: points, y up from the bottom.

    The one conversion the vector arm makes, and it is a conversion of a
    *declared boundary* into the units a *stated boundary* is written in — not
    an ink extent turned into a path coordinate, which is the differencing
    CARD-330 measured as an artefact. ``dot`` is Pillow's inclusive box and
    ``round_mark`` is handed its centre and radius, so the path's extent is
    ``left..right`` and ``top..bottom`` with no half-pixel in it either way.
    """
    left, top, right, bottom = dot
    return (
        left * PT_PER_PX,
        (height_px - bottom) * PT_PER_PX,
        right * PT_PER_PX,
        (height_px - top) * PT_PER_PX,
    )


def _write_the_glyph(
    stream: ContentStream,
    dots: DifficultyDots,
    *,
    solid: int | None = None,
) -> None:
    """Write ``dots`` into ``stream`` through the medium's own round primitive.

    The vector twin of what :func:`_the_declared_site` does on a bitmap, and
    **test code on purpose**: the package has no vector drawing site for this
    glyph (CARD-207 is the card that puts one on the puzzle page), which the
    static walk above already pins — ``round_mark(`` appears in no module but
    the vocabulary's own. So this arm is a *forward* instrument: it is the
    accounting a vector dot site will be measured by, standing ready, and
    until then its own declared route is the only thing that can declare.

    ``solid`` overrides how many dots are filled, for AC-5's wrong-count
    mutant; by default the glyph's own verdict is used.
    """
    for index, dot in enumerate(dots.dots):
        left, top, right, bottom = dot
        filled = dots.is_filled(index) if solid is None else index < solid
        stream.round_mark(
            (left + right) / 2.0,
            (top + bottom) / 2.0,
            (right - left) / 2.0,
            paint="fill" if filled else "stroke",
        )


# --------------------------------------------------------------------------
# AC-4 — an arm whose mechanism the page no longer exercises must RED
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class ArmLiveness:
    """Whether one arm's accounting mechanism is still being exercised.

    Attributes:
        alive: Whether the mechanism produced anything to account for.
        units: How many accounting units it produced — ink regions for the
            raster arm, painted subpaths for the vector one. The denominator
            that keeps "nothing undeclared" from being a statement about a
            page nobody drew.
        what: What the arm found, in one line, for the failure message. A
            dead arm's message has to tell the next reader which arm died and
            on what, because that reader is three cards away and will be
            holding a diff that converted a page.
    """

    alive: bool
    units: int
    what: str


def _raster_arm_liveness(medium: PageMedium, page: object) -> ArmLiveness:
    """The raster arm's mechanism, probed — **its inputs as arguments**.

    Taken as arguments rather than read from the product inside, for the same
    reason :func:`_round_mark_sites` takes its sources that way: a probe that
    can only be handed the live state has no control, and ADR-0039/R1 wants
    one that CAN fail. :meth:`TestDifficultyDots_AnArmWhoseMechanismIsDeadFails.test_each_arms_probe_reports_death_when_its_mechanism_goes`
    hands it the dead state.

    Two ways this arm dies, and they are **not** the same event:

    * the product stops writing this page kind as a bitmap (``medium``) — the
      day CARD-322 lands, and the day the 27 cells above stop measuring the
      product's own puzzle page;
    * the page object it is handed is not a bitmap at all (``page``) — which
      is what reds today, loudly and for the wrong reason.

    A medium that has moved is reported even when a bitmap is still in hand,
    because a bitmap the product does not print is exactly the page this card
    is about.
    """
    if medium is not PageMedium.RASTER:
        return ArmLiveness(
            False,
            0,
            f"the product now writes a puzzle page as {medium.value}, so a "
            "bitmap of one is a page it does not print",
        )
    if not isinstance(page, Image.Image):
        return ArmLiveness(
            False, 0, f"the puzzle page arrived as {type(page).__name__}, not a bitmap"
        )
    units = len(ink_regions(page, MARK_LEVEL))
    return ArmLiveness(units > 0, units, f"{units} ink regions on the bitmap page")


def _vector_arm_liveness(page: object) -> ArmLiveness:
    """The vector arm's mechanism, probed — its input as an argument.

    This arm dies when the stream it accounts from stops carrying painted
    paths: a writer that emits nothing, a page handed over as a bitmap, or a
    content stream whose shapes all left. It does **not** depend on
    ``page_medium``: the arm reads a page a fixture writes as operators (AC-6),
    so it is alive before the declaration is lifted and stays alive after.
    """
    if not isinstance(page, ContentStream):
        return ArmLiveness(
            False,
            0,
            f"the puzzle page arrived as {type(page).__name__}, not a content stream",
        )
    units = len(stream_marks(_stream_text(page)))
    return ArmLiveness(units > 0, units, f"{units} painted subpaths in the stream")


@dataclass(frozen=True)
class InstrumentArm:
    """One medium's half of the difficulty-dot accounting.

    Attributes:
        name: What this arm is called, in a failure message.
        medium: The medium it reads. There is one arm per
            :class:`~nonogram.admin.book_pdf_generator.PageMedium`, held to
            that enumeration by
            :meth:`TestDifficultyDots_AnArmWhoseMechanismIsDeadFails.test_there_is_one_arm_per_medium_the_product_can_write`,
            so a third medium cannot arrive without an arm.
        kind: The page kind its accounting source is a page of.
        mechanism: The source of its accounting, in one line, naming the
            domain the reading is in.
        remedy: What the next reader must do when this arm dies. A guard that
            reds without saying what to do gets widened rather than answered.
        probe: Its liveness probe, handed the page pair.
    """

    name: str
    medium: PageMedium
    kind: PageKind
    mechanism: str
    remedy: str
    probe: object

    def liveness(self, page: ArmPage) -> ArmLiveness:
        return self.probe(page)


#: The two arms. **One per medium the product can write**, not one per page
#: kind and not one per instrument: the thing that died under the old shape
#: was a medium, so the medium is the axis the arms are enumerated on.
ARMS: tuple[InstrumentArm, ...] = (
    InstrumentArm(
        name="raster",
        medium=PageMedium.RASTER,
        kind=PageKind.PUZZLE,
        mechanism=(
            "ink extents, in device pixels, of the connected regions of a "
            "bitmap puzzle page the product draws through _blank_page"
        ),
        remedy=(
            "the product no longer draws this page as a bitmap: RE-POINT this "
            "arm at a page kind _RASTER_DECLARATIONS still declares raster — "
            "the cover and the divider, which keep their bitmaps under "
            "ADR-0042/R2 — and move the 27 cells of this module that read the "
            "interior as bitmaps with it. Retiring the arm is NOT one of the "
            "options while PageMedium keeps RASTER: an arm set that loses a "
            "medium reds test_there_is_one_arm_per_medium_the_product_can_write"
        ),
        probe=lambda page: _raster_arm_liveness(
            book_pdf_generator.page_medium(PageKind.PUZZLE), page.bitmap
        ),
    ),
    InstrumentArm(
        name="vector",
        medium=PageMedium.VECTOR,
        kind=PageKind.PUZZLE,
        mechanism=(
            "path coordinates, in points, of the painted subpaths of a "
            "puzzle page written as operators by vector_puzzle_page"
        ),
        remedy=(
            "the writer this arm accounts from stopped emitting painted "
            "paths: find out what draws the page now and account from that, "
            "rather than widening this arm until it agrees"
        ),
        probe=lambda page: _vector_arm_liveness(page.stream),
    ),
)


class TestDifficultyDots_AnArmWhoseMechanismIsDeadFails:
    """AC-4, and the card's standing contribution.

    The defect this card was opened for is an accounting whose mechanism can
    stop firing without anything saying so. The fix is not a louder exception
    — the measurement in this section's header shows the exception is already
    loud, and already useless — it is an **arm per medium, each naming its
    own mechanism, each with a probe that can report death**.

    Each arm's probe takes its inputs as arguments, so the two directions are
    both tested here: the live state reports alive, and a fabricated dead
    state reports dead. Neither direction alone is the claim — a probe that
    always says "alive" passes the first, and one that always says "dead"
    passes the second.
    """

    @pytest.mark.parametrize("arm", ARMS, ids=[arm.name for arm in ARMS])
    def test_each_arms_mechanism_is_still_exercised(
        self, arm: InstrumentArm, arm_page: ArmPage
    ) -> None:
        """The guard itself: an arm reading a page nobody draws reds here."""
        liveness = arm.liveness(arm_page)
        assert liveness.alive, (
            f"the {arm.name} arm of the difficulty-dot accounting is DEAD: "
            f"{liveness.what}. Its mechanism is {arm.mechanism}. "
            f"{arm.remedy}"
        )
        assert liveness.units > 0, (
            f"the {arm.name} arm found nothing to account for, so its verdict "
            "would be a statement about an empty page"
        )

    def test_there_is_one_arm_per_medium_the_product_can_write(self) -> None:
        """Held to :class:`PageMedium`, so a third medium cannot arrive unarmed.

        **What this cell deliberately does not pin, and what does.** It is a
        claim about the set of *media*, not about the arms' spellings, so
        renaming an arm must leave it green — the round's declared negative
        control (MUT-13) and the reason it survived. That is only half the
        reason the survival is legitimate. The other half is that
        :attr:`InstrumentArm.name` feeds the ``ids=`` of the two parametrized
        cells in this class, so a rename moves a node id from ``[raster]`` to
        whatever it was renamed to — and node ids are pinned, by G-5's node-id
        gate, a different instrument at a different layer. So a rename is
        caught; it is caught *there* rather than here. Without that second
        half, a reader cannot tell this declared negative control from a claim
        quietly narrowed until its mutant stopped failing.
        """
        assert {arm.medium for arm in ARMS} == set(PageMedium), (
            "a medium the product can write has no arm of this accounting: "
            f"{sorted(medium.value for medium in set(PageMedium) - {a.medium for a in ARMS})}"
        )
        # Key count == source count. CARD-330's medium pin keyed a dict on a
        # bare test name, two tests shared one, and the guard silently lost a
        # member; an arm set that collapsed two arms into one medium would
        # lose one the same way.
        assert len(ARMS) == len(set(PageMedium)), (
            f"{len(ARMS)} arms for {len(set(PageMedium))} media"
        )
        assert len({arm.name for arm in ARMS}) == len(ARMS), "two arms share a name"
        assert len({arm.medium for arm in ARMS}) == len(ARMS), "two arms share a medium"

    def test_exactly_one_arm_reads_the_medium_the_product_writes_today(self) -> None:
        """Which arm is the live one is **derived**, so the day it flips is visible.

        Not asserted as "the raster arm": asserted as "the arm whose medium is
        the one ``page_medium`` returns for its own page kind", which is the
        raster arm today and the vector arm after CARD-322. What is pinned is
        that it is **exactly one** — two arms claiming the product's medium,
        or none, is an accounting nobody can read.
        """
        live = [
            arm for arm in ARMS if book_pdf_generator.page_medium(arm.kind) is arm.medium
        ]
        assert len(live) == 1, (
            "exactly one arm reads the medium the product writes for its page "
            f"kind; {[arm.name for arm in live]} do"
        )
        assert live[0].medium is book_pdf_generator.page_medium(PageKind.PUZZLE)

    def test_no_arms_remedy_offers_an_option_this_section_forbids(self) -> None:
        """A work order cannot offer a route its own sibling cell reds.

        The raster arm's remedy used to begin "retire this arm, or re-point
        it…". Taking the first option **reds**
        :meth:`test_there_is_one_arm_per_medium_the_product_can_write`, because
        ``PageMedium`` keeps ``RASTER`` for the cover and the divider
        (ADR-0042/R2) — so the remedy sent its reader down a path that fails
        for a reason the remedy did not mention, in a string whose whole
        purpose is that a guard which reds without saying what to do gets
        widened rather than answered.

        The forbiddenness is **derived** here, not stated: dropping any arm
        from the set leaves a medium the product can write with no arm of this
        accounting. Then the remedies are held to it.
        """
        for arm in ARMS:
            rest = tuple(other for other in ARMS if other is not arm)
            assert {other.medium for other in rest} != set(PageMedium), (
                f"retiring the {arm.name} arm would leave every medium armed, "
                "so this cell's premise no longer holds and the remedies below "
                "may offer retirement again"
            )

        # The one place retirement may be named is as the option it is not.
        forbidden_named_as_forbidden = "Retiring the arm is NOT one of the options"
        (raster_arm,) = [arm for arm in ARMS if arm.medium is PageMedium.RASTER]
        assert forbidden_named_as_forbidden in raster_arm.remedy, (
            "the raster arm's remedy no longer says that retiring it is "
            "forbidden, and CARD-322 reads that string as its work order"
        )
        for arm in ARMS:
            offered = arm.remedy.replace(forbidden_named_as_forbidden, "")
            for verb in ("retire", "retiring"):
                assert verb not in offered.lower(), (
                    f"the {arm.name} arm's remedy OFFERS {verb!r}, which reds "
                    "test_there_is_one_arm_per_medium_the_product_can_write: "
                    f"{arm.remedy!r}"
                )

    def test_both_reds_of_this_section_name_the_mechanism_and_the_remedy(
        self,
    ) -> None:
        """The card's claim about this section's two reds, machine-checked.

        Under the declaration lift exactly two of this module's new cells red,
        and the card says both name the arm, its mechanism and its remedy. One
        did; its sibling red on its live-state loop with the arm's name and
        nothing else, so the claim was half true and a reader of that red got
        no work order.

        Derived rather than re-read: the two cells' assert **messages** are
        taken off their own source, and each must carry both attributes. A
        message that drops either one reds here.
        """
        for leaf in (
            "test_each_arms_mechanism_is_still_exercised",
            "test_each_arms_probe_reports_death_when_its_mechanism_goes",
        ):
            messages = " ".join(
                _assert_messages_of(
                    "TestDifficultyDots_AnArmWhoseMechanismIsDeadFails", leaf
                )
            )
            for attribute in ("arm.name", "arm.mechanism", "arm.remedy"):
                assert attribute in messages, (
                    f"{leaf} can red without naming {attribute}, so a reader of "
                    "that failure is told an arm is dead and not what to do"
                )

    def test_each_arms_probe_reports_death_when_its_mechanism_goes(
        self, arm_page: ArmPage
    ) -> None:
        """The control, both arms, each fed the death its own mechanism has.

        Three deaths, because the two arms do not die of the same thing: the
        raster arm dies of a medium that moved **and** of a page that is not a
        bitmap, and the vector arm dies of a page that carries no painted
        path. Each is constructed here rather than caused, so the control
        costs no render and converts nothing.
        """
        moved = _raster_arm_liveness(PageMedium.VECTOR, arm_page.bitmap)
        assert not moved.alive and moved.units == 0, (
            "the raster arm's probe called itself alive while holding a bitmap "
            "of a page the product writes as operators"
        )
        assert "vector" in moved.what

        wrong_type = _raster_arm_liveness(PageMedium.RASTER, arm_page.stream)
        assert not wrong_type.alive, (
            "the raster arm's probe called itself alive on a content stream"
        )

        empty = ContentStream(width_px=100.0, height_px=100.0, dpi=DPI)
        gone = _vector_arm_liveness(empty)
        assert not gone.alive and gone.units == 0, (
            "the vector arm's probe called itself alive on a stream with no "
            "painted path in it"
        )

        # And the live state, in the same test, so neither direction can be
        # passing because the probe is stuck. The message carries the mechanism
        # and the remedy, as its sibling cell's does: cycle 1 of this card's
        # review found the card claiming both reds name them and only one
        # doing so, and a red here is read by the same person for the same
        # reason — a guard that reds without saying what to do gets widened
        # rather than answered.
        for arm in ARMS:
            live = arm.liveness(arm_page)
            assert live.alive, (
                f"the {arm.name} arm is not alive: {live.what}. Its mechanism "
                f"is {arm.mechanism}. {arm.remedy}"
            )


# --------------------------------------------------------------------------
# The accounting, once, for both arms
# --------------------------------------------------------------------------
#
# The *matching rule* is :func:`_unaccounted` above, unchanged and shared: a
# multiset, matched per page and exactly. What differs between the arms is the
# reading each one brings it — ink extents in device pixels, or path
# coordinates in points — and that difference is the whole of the two arms'
# separation. One rule, two readings; not one reading stretched over two
# media, which is the shape that died.

#: The PDF paint operators that **fill** a path, as against stroking its
#: outline. Held to :mod:`tests.helpers.round_ink`'s own painting set by
#: :meth:`TestDifficultyDots_TheVectorArmReadsTheStream.test_the_filling_paints_are_a_subset_of_the_readers_own_set`,
#: so a paint operator the reader learns about cannot be silently missing here.
PAINTS_THAT_FILL = frozenset({"f", "F", "f*", "B", "B*", "b", "b*"})


def _writer_operators() -> frozenset[str]:
    """Every operator the book's vector writer is **measured** to emit.

    The union of :data:`_WRITER_DOOR_EMITS`' values — one entry per public
    ``ContentStream`` member, each one *driven* and its output read, which is
    the enumerable authority ADR-0039/R2 asks a guard's set to be derived from.
    Not ``dir(ContentStream)`` directly: a member's *name* says nothing about
    which operators it writes, and the module next door already pays the cost
    of finding out.
    """
    return frozenset(
        token for tokens in _WRITER_DOOR_EMITS.values() for token in tokens
    )


#: :func:`_writer_operators`' answer, **recorded**, so the vocabulary guard
#: below is a statement about a known surface rather than a tautology over
#: whatever the writer happens to emit today. 17 operators, measured off
#: ``ContentStream``'s 18 public members (``to_points``, ``media_box``,
#: ``operators`` and ``render`` emit none; ``line``, ``rectangle``,
#: ``round_mark`` and ``text`` emit several each).
WRITER_OPERATORS_RECORDED = frozenset(
    {
        "BMC",
        "BT",
        "EMC",
        "ET",
        "G",
        "S",
        "Td",
        "Tf",
        "Tj",
        "c",
        "f",
        "g",
        "h",
        "l",
        "m",
        "re",
        "w",
    }
)

#: The operators of that surface the stream reader deliberately **passes over**,
#: with what each one is: state the paper never sees, or type, which is the
#: reader's one stated bound (a glyph is not a path — the asymmetry
#: :meth:`TestDifficultyDots_TheVectorArmReadsTheStream.test_a_typed_round_mark_is_outside_this_arms_reach`
#: controls).
#:
#: An entry here is a **recorded** pass-over, which is the whole difference the
#: cycle-1 review found: ``cm``, ``Do`` and ``sh`` used to be passed over too,
#: and were in no list at all, so the reader answered with the wrong box or
#: with silence and nothing said so. They are refused now
#: (:data:`round_ink._REFUSED_STATE_OPERATORS`), and this dict is what keeps the
#: remaining pass-overs from growing the same way.
WRITER_OPERATORS_NOT_A_PATH = {
    "G": "sets the stroke tone; state, not a mark",
    "g": "sets the fill tone; state, not a mark",
    "w": "sets the stroke width; state, and CARD-330's subject, not a path",
    "BT": "opens a text object",
    "Tf": "selects a font inside one",
    "Td": "moves the text line inside one",
    "Tj": "shows a string — TYPE, this reader's stated bound",
    "ET": "closes a text object",
    "BMC": "CARD-314's marked-content bracket; paints nothing",
    "EMC": "closes one; paints nothing",
}


def _at_the_streams_places(
    box: tuple[float, float, float, float]
) -> tuple[float, float, float, float]:
    """``box`` rounded to the 1/1000 pt a content stream writes its operands at.

    The vector arm's accounting key. Rounding rather than a tolerance, because
    a stream's coordinates **are** three-place decimals: the reading and the
    declaration are then the same canonical number and the match is exact, as
    the raster arm's is, instead of resting on a tolerance nobody measured.
    That it is lossless for a dot on integer pixels at :data:`DPI` is derived
    by
    :meth:`TestDifficultyDots_TheVectorArmReadsTheStream.test_an_integer_pixel_reaches_the_stream_exactly`
    — worst case 1.1369e-13 pt over its own 200-case seeded sweep, eleven
    orders inside the place being rounded to.
    """
    return tuple(round(value, 3) for value in box)  # type: ignore[return-value]


def _raster_arm_reading(
    page: Image.Image, box: tuple[int, int, int, int], plant: object
) -> tuple[tuple[Mark, ...], tuple[Mark, ...]]:
    """``(found, declared)`` for one bitmap page with ``plant`` drawn in ``box``.

    **No monkeypatch** (AC-3). ``plant`` is called with the page's own draw
    object and its box, and whatever geometry it returns is what it declared —
    the site's own return value, as the legacy spy recorded, obtained by
    calling it instead of by replacing it. A hook was only ever needed because
    the legacy harness let the *interior walk* reach the site; this arm draws
    the page and then the glyph, so the caller is in hand.

    ``found`` is :func:`round_marks` — **ink extents, device pixels**.
    ``declared`` is the filled dots' boxes, which on this medium are ink
    extents too: a dot stroked by ``draw.ellipse`` inks precisely its own box.
    An outlined dot is not declared here, because its ink is a ring and a ring
    is not round to this reading — the raster instrument's stated hollow
    bound, and the one place the two arms' verdicts on one glyph differ.
    """
    drawn = plant(ImageDraw.Draw(page), box)
    declared: list[Mark] = []
    if isinstance(drawn, DifficultyDots):
        declared = [
            (0, dot)
            for index, dot in enumerate(drawn.dots)
            if drawn.is_filled(index)
        ]
    found = [(0, mark.box) for mark in round_marks(page)]
    return tuple(found), tuple(declared)


def _vector_arm_reading(
    text: str, declared_dots: Sequence[tuple[int, int, int, int]], height_px: int
) -> tuple[tuple[Mark, ...], tuple[Mark, ...]]:
    """``(found, declared)`` for one page written as operators.

    ``found`` is every **round painted subpath** of ``text`` — path
    coordinates, points, at the stream's own three places. ``declared`` is
    ``declared_dots`` put into that same domain by :func:`_declared_in_points`.
    Path against path: nothing here is differenced against an ink extent.

    Every dot is declared on this medium, filled or outlined, and that is not
    an oversight: a stroked circle's **path** encloses a full disc, so this
    reading calls it round where the raster reading calls it hollow. The
    difference is measured in
    :meth:`TestDifficultyDots_TheVectorArmReadsTheStream.test_a_stroked_ring_is_round_to_this_arm_and_hollow_to_the_other`.
    """
    found = [
        (0, _at_the_streams_places(mark.box)) for mark in round_stream_marks(text)
    ]
    declared = [
        (0, _at_the_streams_places(_declared_in_points(dot, height_px)))
        for dot in declared_dots
    ]
    return tuple(found), tuple(declared)


def _appended(page: ArmPage, write: object) -> str:
    """``page``'s stream with whatever ``write`` records appended to it.

    A content stream **is** its operators in order, so appending text is
    appending operators; writing into a fresh stream of the same extent and
    concatenating keeps the module-scoped fixture's own page unmutated, which
    a plant drawn straight into it would not.
    """
    extra = ContentStream(
        width_px=page.width_px, height_px=page.height_px, dpi=DPI
    )
    write(extra)
    return _stream_text(page.stream) + "\n" + _stream_text(extra)


#: How many connected ink regions one bitmap puzzle page of the baseline book
#: must still carry — the raster arm's denominator, the twin of
#: :data:`REGION_FLOOR` for a single page. 85, just under the 91 measured on
#: this branch — a puzzle page is a grid of rules, a frame, a band, a folio
#: and a QR group, and its ink merges into far fewer regions than the whole
#: interior's 2640. The same 91 at both measured thresholds, because an
#: unsolved puzzle page draws nothing in the book's own grey: the solved grid
#: is the answer pages'.
RASTER_ARM_MIN_REGIONS = 85


def _declaring_plant(
    draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]
) -> DifficultyDots | None:
    """The honest raster route: the one drawing site, **called**, not replaced.

    :func:`_the_declared_site` with its return value kept. That one line is
    the whole of AC-3's "without a monkeypatch": the legacy harness needs a
    spy because the *interior walk* makes the call, and this arm does not
    because it makes the call itself.
    """
    return book_pdf_generator._draw_difficulty_dots(draw, PLANTED_TIER, *box)


def _rogue_plant(
    draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]
) -> DifficultyDots | None:
    """A second glyph in the same place, drawn by nobody who declares it.

    :func:`_rogue_ellipse`, which the static walk above *can* see, with
    nothing declared — the raster arm's counterpart to the vector arm's
    32-gon. Which spelling it is does not matter to this arm (that is
    :class:`TestRoundMarkOnThePage_SameVerdictForEverySpelling`'s subject);
    what matters is that it declares nothing.
    """
    _rogue_ellipse(draw, box)
    return None



# --------------------------------------------------------------------------
# The vector arm's corpus: every puzzle page two books plan, as operators
# --------------------------------------------------------------------------

#: Where the first puzzle page of an interior sits, as an interior position:
#: the expression ``vector_puzzle_page``'s own caller uses for its default
#: first page, read off this module's two page-count constants rather than
#: written as a 4. Both arms' page and every page of the vector corpus are
#: numbered from here, consecutively, so **both page parities occur** in the
#: sweep (FR-043 gives an odd and an even page different gutters) — which is
#: asserted rather than assumed, in
#: :meth:`TestDifficultyDots_TheVectorArmReadsTheStream.test_the_corpus_is_one_page_per_puzzle_of_both_books`.
FIRST_PUZZLE_PAGE = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT

#: The books the vector corpus is built from, by name, each with the callable
#: that enumerates its rows. Two, and not one: the baseline corpus is built
#: from ``_gutter_grid``, where no two filled cells ever touch, and the
#: picture corpus (:func:`_picture_puzzles`) carries the deliberately round
#: blob — the same pairing AC-2's raster sweep makes, so the two arms sweep
#: the same puzzles.
#:
#: The callable is held here rather than its result, because the **row count
#: is the corpus's authority**: one vector page per puzzle, so a page missing
#: from the sweep is a row missing from the book, and
#: :meth:`TestDifficultyDots_TheVectorArmReadsTheStream.test_the_corpus_is_one_page_per_puzzle_of_both_books`
#: compares the two rather than comparing the sweep with a constant it built
#: itself (CARD-330's corpus guard asserted a floor against a fixture built
#: from the same constant, so it could not fail for any value).
VECTOR_CORPUS_SOURCES: tuple[tuple[str, object], ...] = (
    ("baseline", baseline_puzzles),
    ("pictures", _picture_puzzles),
)

#: How many vector puzzle pages the corpus must hold at the least, and how
#: many painted subpaths they must carry between them.
#:
#: Floors just under a measured value, and **neither is the assertion that
#: keeps the corpus honest** — that one is the equality against each book's
#: own row count above. Measured on this branch: 13 pages, 4 from the
#: baseline book and 9 from the picture book, carrying 588 painted subpaths
#: of which 182 have extent on both axes — the rest are the grid's own rules,
#: which enclose nothing and so cannot be round.
VECTOR_CORPUS_MIN_PAGES = 12
VECTOR_CORPUS_MIN_SUBPATHS = 560
VECTOR_CORPUS_MIN_SHAPED = 170


def _vector_pages(puzzles: Sequence[dict]) -> list[ContentStream]:
    """One vector puzzle page per row of ``puzzles``, in print order.

    Composed one sheet at a time through
    :meth:`BookPDFGenerator.vector_puzzle_page`, from
    :data:`FIRST_PUZZLE_PAGE` upwards — **the pairing walk is deliberately not
    consulted**, for two reasons that both matter here:

    * this arm is about a single-puzzle sheet's band (:func:`_arm_page` says
      why), and a paired sheet carries two of them;
    * one page per row makes the **row count** the corpus's authority, which
      is a stronger anchor than a pairing verdict: a dropped page is then a
      dropped puzzle and nothing else.

    Consecutive positions, so the sweep carries both page parities.
    """
    generator = BookPDFGenerator(corpus_book())
    payloads = [
        BookPDFGenerator._payload(row)
        for row in book_pdf_generator.print_order(puzzles)
    ]
    sizes = generator.cell_sizes(payloads)
    return [
        generator.vector_puzzle_page(
            payload, number, FIRST_PUZZLE_PAGE + number - 1, sizes
        )
        for number, payload in enumerate(payloads, start=1)
    ]


@pytest.fixture(scope="module")
def vector_corpus() -> dict[str, tuple[int, list[ContentStream]]]:
    """``{book: (its row count, one vector page per row)}``, once."""
    return {
        name: (len(rows()), _vector_pages(rows()))
        for name, rows in VECTOR_CORPUS_SOURCES
    }


# --------------------------------------------------------------------------
# AC-3's structural half: this arm hooks nothing
# --------------------------------------------------------------------------


def _production_hooks(sources: Mapping[str, str]) -> list[str]:
    """Every place ``sources`` rebinds an attribute of a production module.

    ``sources`` is ``{what it is called: its text}``, taken as an argument for
    the reason :func:`_round_mark_sites` takes its sources that way: a
    detector that can only be pointed at the real thing has no control.

    Three shapes, because a hook has three spellings and a guard that caught
    one would be the kind of claim this file exists to stop making:
    ``module.attribute = value``, ``setattr(module, ...)`` and a
    ``monkeypatch`` parameter. ``module`` is any name this test module has
    bound to a module of the ``nonogram`` package, read off this module's own
    globals — which is what makes "production" a measurement here rather than
    a list somebody has to keep.
    """
    production = {
        name
        for name, value in globals().items()
        if inspect.ismodule(value)
        and getattr(value, "__name__", "").split(".")[0] == "nonogram"
    }
    assert production, "this module binds no nonogram module that could be hooked"
    findings: list[str] = []
    for where, text in sources.items():
        for node in ast.walk(ast.parse(text)):
            if isinstance(node, (ast.Assign, ast.AugAssign)):
                targets = (
                    node.targets if isinstance(node, ast.Assign) else [node.target]
                )
                for target in targets:
                    if (
                        isinstance(target, ast.Attribute)
                        and isinstance(target.value, ast.Name)
                        and target.value.id in production
                    ):
                        findings.append(
                            f"{where} rebinds {target.value.id}.{target.attr}"
                        )
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "setattr"
            ):
                findings.append(f"{where} calls setattr")
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if any(
                    argument.arg == "monkeypatch" for argument in node.args.args
                ):
                    findings.append(f"{where} takes the monkeypatch fixture")
    return findings


#: Every function the raster arm's accounting is made of, by name. The list
#: :func:`_production_hooks` is pointed at, and the reason the arm's claim
#: "it hooks nothing" is a measurement over a named set rather than a hope
#: about a whole 6000-line module — the legacy harness in the same file
#: *does* hook, deliberately, and still does.
#:
#: The two **plant** functions are in it, and were not until cycle 1 of this
#: card's review proved the hole with a mutant: a plant that inserted
#: ``book_pdf_generator._NOT_A_REAL_ATTRIBUTE = 1`` into
#: :func:`_declaring_plant`'s body — a textbook production rebind, the exact
#: shape the detector's own first control catches when handed it as a string —
#: left the module at 189 passed and the detector never saw it. They are not
#: part of the 6000-line module's noise the narrowing exists to exclude; they
#: are the arm's own moving parts, and ``_raster_arm_reading`` reads nothing
#: without the one it is handed.
RASTER_ARM_FUNCTIONS = (
    "_arm_page",
    "_raster_arm_reading",
    "_raster_arm_liveness",
    "_declaring_plant",
    "_rogue_plant",
)


def _raster_arm_sources() -> dict[str, str]:
    """:data:`RASTER_ARM_FUNCTIONS`' own text, off this module."""
    return {
        name: inspect.getsource(globals()[name]) for name in RASTER_ARM_FUNCTIONS
    }


class TestDifficultyDots_TheClaimIsAboutThePageNotTheCall:
    """AC-1: the claim, stated as page facts, and measured as page facts.

    The instrument's shape has been standing in for the claim: "the one
    drawing site declared these dots" is a statement about a call, and a twin
    built from it inherits the coupling that is this card's subject. So
    :data:`THE_CLAIM` and the three prose statements beside it say what must
    be true of **the paper** — how many dots, how many of them filled, where
    they sit, what size they are — and every one of those is then measured on
    a real page of **each** medium below.

    The "names no function" half is not decoration either: it has a mutant on
    each arm. A claim rewritten to name the drawing site reds
    :meth:`test_the_claim_is_stated_about_the_page_and_names_no_function`, and
    a forbidden name that names nothing real reds
    :meth:`test_the_forbidden_names_are_things_that_really_exist` — so the
    list cannot be padded with words to make the first test pass.
    """

    def test_the_claim_covers_every_tier_the_project_has_exactly_once(self) -> None:
        assert tuple(row.tier for row in THE_CLAIM) == tuple(TIERS), (
            "the claim's rows are not the project's ladder, in its order"
        )
        assert len(THE_CLAIM) == len(TIERS)
        assert len({row.tier for row in THE_CLAIM}) == len(THE_CLAIM), (
            "two rows of the claim are about one tier"
        )

    def test_the_claims_counts_are_the_ladder_and_not_a_second_one(self) -> None:
        """One filled dot per rank, no gap, and one total — read off ``TIERS``."""
        assert [row.solid for row in THE_CLAIM] == list(range(1, len(TIERS) + 1))
        assert {row.dots for row in THE_CLAIM} == {len(TIERS)}
        assert [row.solid for row in THE_CLAIM] == [_rank(tier) for tier in TIERS]

    def test_the_claim_is_stated_about_the_page_and_names_no_function(self) -> None:
        """No statement of the claim names a call, a hook or a primitive."""
        for statement in THE_CLAIMS_PROSE:
            for name in CALL_NAMES_THE_CLAIM_MAY_NOT_USE:
                assert name not in statement, (
                    f"the claim names {name!r}, which is a call and not "
                    f"something true of the page: {statement!r}"
                )
        assert len(THE_CLAIMS_PROSE) == 3, (
            "the claim is count, placement and size; a statement has gone"
        )

    def test_the_forbidden_names_are_things_that_really_exist(self) -> None:
        """The list cannot be padded: every name on it resolves to a real thing."""
        real = {
            "_draw_difficulty_dots": lambda: book_pdf_generator._draw_difficulty_dots,
            "_set_band": lambda: book_pdf_generator._set_band,
            "round_mark": lambda: ContentStream.round_mark,
            "ellipse": lambda: ImageDraw.ImageDraw.ellipse,
            "monkeypatch": lambda: pytest.MonkeyPatch,
        }
        assert set(real) == set(CALL_NAMES_THE_CLAIM_MAY_NOT_USE), (
            "a forbidden name has no resolution here, so nothing says it names "
            "anything at all"
        )
        for name, resolve in real.items():
            assert resolve() is not None, f"{name} resolves to nothing"

    @pytest.mark.parametrize("row", THE_CLAIM, ids=[row.tier.value for row in THE_CLAIM])
    def test_the_claims_counts_hold_on_a_bitmap_page(
        self, row: DotClaim, arm_page: ArmPage
    ) -> None:
        """Count and placement, measured off the ink of a real raster page."""
        page = arm_page.bitmap.copy()
        drawn = book_pdf_generator._draw_difficulty_dots(
            ImageDraw.Draw(page), row.tier, *arm_page.box
        )
        assert drawn is not None, "the band of a real book page declined the glyph"
        regions = {region.box: region for region in ink_regions(page, MARK_LEVEL)}
        present = [dot for dot in drawn.dots if dot in regions]
        assert len(present) == row.dots, (
            f"{row.tier.value} put {len(present)} dots on the paper, not {row.dots}"
        )
        solid = [dot for dot in present if regions[dot].is_round]
        assert len(solid) == row.solid, (
            f"{row.tier.value} filled {len(solid)} of {row.dots} dots on the "
            f"paper, not {row.solid}"
        )
        # Placement and size, as the prose states them: one line, inside the
        # box, equal and square, none touching. "None touching" is carried by
        # `len(present) == row.dots`: ink is measured in connected regions, so
        # two dots that touched would be one region and one box short.
        left, top, right, bottom = arm_page.box
        for dot in present:
            region = regions[dot]
            assert left <= region.left and region.right <= right
            assert top <= region.top and region.bottom <= bottom
            assert region.width == region.height, "a dot's footprint is not square"
        assert len({regions[dot].width for dot in present}) == 1, "the dots differ in size"
        assert len({regions[dot].top for dot in present}) == 1, "the dots are not in one line"

    @pytest.mark.parametrize("row", THE_CLAIM, ids=[row.tier.value for row in THE_CLAIM])
    def test_the_claims_counts_hold_on_a_page_written_as_operators(
        self, row: DotClaim, arm_page: ArmPage
    ) -> None:
        """The same claim, the same page, measured in the content stream."""
        dots = difficulty_dots(
            *arm_page.box, filled=row.solid, total=row.dots
        )
        assert dots is not None, "the band of a real book page declined the glyph"
        before = len(stream_marks(_stream_text(arm_page.stream)))
        text = _appended(arm_page, lambda stream: _write_the_glyph(stream, dots))
        written = stream_marks(text)[before:]
        assert len(written) == row.dots, (
            f"{row.tier.value} put {len(written)} subpaths in the stream, not "
            f"{row.dots}"
        )
        solid = [mark for mark in written if mark.paint in PAINTS_THAT_FILL]
        assert len(solid) == row.solid, (
            f"{row.tier.value} filled {len(solid)} of {row.dots} dots in the "
            f"stream, not {row.solid}"
        )
        box = _declared_in_points(arm_page.box, arm_page.height_px)
        for mark in written:
            assert box[0] <= round(mark.x0, 3) and round(mark.x1, 3) <= box[2]
            assert box[1] <= round(mark.y0, 3) and round(mark.y1, 3) <= box[3]
            assert round(mark.width, 3) == round(mark.height, 3), (
                "a dot's path is not as wide as it is tall"
            )
        assert len({round(mark.width, 3) for mark in written}) == 1, "the dots differ in size"
        assert len({round(mark.y0, 3) for mark in written}) == 1, "the dots are not in one line"


class TestDifficultyDots_TheVectorArmReadsTheStream:
    """AC-2: the dots accounted from the content stream, per ADR-0042/R6.

    The 27 cells' equivalents, on the medium they will be measured on — the
    quiet verdict on the book's own pages with a denominator under it, a
    measured margin, a declared glyph found and paid for, a rogue glyph
    caught, and the reader's own two bounds each with a control. The count of
    pages swept is **derived from the generator's own page plan** and not
    listed, so dropping a page or a whole book reds here rather than shrinking
    the sweep quietly.

    **What this arm is not.** It is not a reading of a page the product writes
    today: ``_RASTER_DECLARATIONS`` still declares ``PageKind.PUZZLE`` raster
    and nothing here lifts it (AC-6, G-1). It is the accounting a vector
    puzzle page will be measured by, standing ready and exercised against the
    page ``vector_puzzle_page`` already writes — which is what makes it an arm
    rather than a plan.
    """

    def test_the_page_extent_this_arm_flips_y_about_is_the_streams_own(
        self, arm_page: ArmPage
    ) -> None:
        """The one figure the vector accounting takes on trust, checked.

        :func:`_declared_in_points` flips a declared box's y about
        :attr:`ArmPage.height_px`, which :func:`_arm_page` reads off a
        ``Layout`` it recomputed rather than off the page the writer wrote. The
        stream's own ``MediaBox`` is the independent reading of the same
        extent, and it refuses a disagreement — which matters, because a wrong
        height is a declared box in the wrong place with the counts still
        agreeing, and that is the failure MUT-15 plants.

        **Narrowly this and nothing more.** It is *not* a check that the
        recomputed layout is the writer's in every respect: measured, taking
        the spec for the next interior position instead leaves the band's
        centre and the glyph's box bit-identical (the trim and
        ``center_x = width / 2`` are the same on both parities), so a
        page-number drift is invisible here and this test does not claim to
        see it. What it holds is the extent the conversion is done against.
        """
        _, _, width_pt, height_pt = arm_page.stream.media_box
        assert round(height_pt, 3) == round(arm_page.height_px * PT_PER_PX, 3), (
            "the page height this arm flips y about is not the stream's own, "
            "so every declared box is in the wrong place by the difference"
        )
        assert round(width_pt, 3) == round(arm_page.width_px * PT_PER_PX, 3)

    def test_the_corpus_is_one_page_per_puzzle_of_both_books(
        self, vector_corpus: Mapping[str, tuple[int, list[ContentStream]]]
    ) -> None:
        """The corpus floor, anchored to each book's rows rather than to itself."""
        assert sorted(vector_corpus) == sorted(
            name for name, _ in VECTOR_CORPUS_SOURCES
        )
        assert len(vector_corpus) == len(VECTOR_CORPUS_SOURCES), (
            "a book of the corpus was keyed onto another book's name"
        )
        for name, (rows, pages) in vector_corpus.items():
            assert rows > 0, f"the {name} book holds no puzzle at all"
            assert len(pages) == rows, (
                f"the {name} book holds {rows} puzzles and the sweep holds "
                f"{len(pages)} pages"
            )
        pages = sum(len(streams) for _, streams in vector_corpus.values())
        assert pages == sum(rows for rows, _ in vector_corpus.values())
        assert pages >= VECTOR_CORPUS_MIN_PAGES, (
            f"the vector corpus has shrunk to {pages} pages"
        )
        # And both page parities are in it, which consecutive numbering from
        # FIRST_PUZZLE_PAGE gives and which nothing else would notice losing.
        parities = {
            book_pdf_generator.page_is_right_hand(FIRST_PUZZLE_PAGE + offset)
            for _, streams in vector_corpus.values()
            for offset in range(len(streams))
        }
        assert parities == {True, False}, (
            "the sweep is all one page parity, so a gutter-dependent "
            "placement could not be wrong in it"
        )

    def test_the_books_own_vector_sheets_carry_no_round_mark(
        self, vector_corpus: Mapping[str, tuple[int, list[ContentStream]]]
    ) -> None:
        """ADR-0042/R6's half of the declared check, with its denominator."""
        subpaths = 0
        shaped = 0
        rogue: list[tuple[str, int, tuple[float, float, float, float]]] = []
        for name, (_, streams) in vector_corpus.items():
            for number, stream in enumerate(streams):
                marks = stream_marks(_stream_text(stream))
                subpaths += len(marks)
                shaped += sum(1 for mark in marks if not mark.is_degenerate)
                rogue.extend(
                    (name, number, mark.box) for mark in marks if mark.is_round
                )
        assert subpaths >= VECTOR_CORPUS_MIN_SUBPATHS, (
            f"only {subpaths} painted subpaths across the corpus — these pages "
            "have stopped carrying the shapes this test exists to tolerate"
        )
        assert shaped >= VECTOR_CORPUS_MIN_SHAPED, (
            f"only {shaped} of {subpaths} subpaths have extent on both axes, so "
            "passing says little: the rest are rules, which cannot be round"
        )
        assert rogue == [], (
            f"a vector puzzle page paints a round mark nobody declared: {rogue[:4]}"
        )

    def test_the_closest_a_vector_page_comes_to_a_round_mark_is_derived(
        self, vector_corpus: Mapping[str, tuple[int, list[ContentStream]]]
    ) -> None:
        """The margin, and it is a **derivation** rather than a recorded number.

        The closest shaped subpath on every page of the corpus is a square
        filled rectangle — a QR placeholder module, 11.28 x 11.28 pt. A
        rectangle's enclosed area is exactly its box's, so its ``fill`` is
        exactly ``4 / pi`` whatever its size, and the margin is therefore
        ``(4 / pi - 1) / ROUND_FILL_TOLERANCE`` = 2.276996 by arithmetic and
        not by measurement. What is measured is that **this** is the shape
        that sets it: ``aspect`` exactly 1.0, so the whole margin rests on
        ``fill`` — the same hand the raster reading's margin rests in on the
        book's own pages, for the same reason.
        """
        derived = (4.0 / math.pi - 1.0) / ROUND_FILL_TOLERANCE
        closest: StreamMark | None = None
        margin = float("inf")
        for _, streams in vector_corpus.values():
            for stream in streams:
                for mark in stream_marks(_stream_text(stream)):
                    if mark.is_degenerate:
                        continue
                    distance = max(
                        abs(mark.aspect - 1.0) / ROUND_ASPECT_TOLERANCE,
                        abs(mark.fill - 1.0) / ROUND_FILL_TOLERANCE,
                    )
                    if distance < margin:
                        margin, closest = distance, mark
        assert closest is not None
        assert margin == pytest.approx(derived, abs=1e-9), (
            f"the closest subpath is {margin} tolerances off, not the "
            f"{derived} a square filled rectangle is"
        )
        assert closest.paint in PAINTS_THAT_FILL, "the closest shape is not filled"
        assert closest.aspect == pytest.approx(1.0, abs=1e-9), (
            "the margin no longer rests on fill alone: the closest shape's "
            f"footprint is {closest.aspect} rather than square"
        )
        assert closest.fill == pytest.approx(4.0 / math.pi, abs=1e-6), (
            "the closest shape no longer encloses its own box, so it is not a "
            "rectangle and this derivation does not describe it"
        )
        assert margin > 1.0, "a page of the corpus is one tolerance from round"

    def test_a_declared_glyph_is_found_in_the_stream_and_accounted_for(
        self, arm_page: ArmPage
    ) -> None:
        """The honest route: a glyph written as operators, found and paid for."""
        dots = difficulty_dots(
            *arm_page.box, filled=_rank(PLANTED_TIER), total=len(TIERS)
        )
        assert dots is not None
        text = _appended(arm_page, lambda stream: _write_the_glyph(stream, dots))
        found, declared = _vector_arm_reading(text, dots.dots, arm_page.height_px)
        assert len(declared) == len(dots.dots), (
            "every dot is declared on this medium, filled or outlined"
        )
        assert len(found) == len(dots.dots), (
            f"{len(dots.dots)} dots were written and {len(found)} round "
            "subpaths are in the stream"
        )
        assert _unaccounted(found, declared) == (), (
            "a dot written through the medium's own round primitive is not "
            "matched by its own declared box"
        )
        # And the same page without the glyph declares nothing and finds
        # nothing, so the balance above is not a balance of two empty sets.
        bare_found, bare_declared = _vector_arm_reading(
            _stream_text(arm_page.stream), (), arm_page.height_px
        )
        assert bare_found == () and bare_declared == ()

    def test_a_rogue_glyph_in_the_stream_is_unaccounted(
        self, arm_page: ArmPage
    ) -> None:
        """A 32-gon per dot: the route no vertex bound can refuse, caught here.

        ``tests/helpers/pdf_vector.subpath_vertices``' own docstring records
        that a bound over a subpath's vertex count cannot close this route and
        names an instrument over **filled subpaths** as what would. This is
        that instrument: the polygon is measured for the shape it is, not for
        the operators it is spelled with, so it is caught at 32 sides and the
        glyph's own Bezier circles are caught at four curves.
        """
        dots = difficulty_dots(
            *arm_page.box, filled=_rank(PLANTED_TIER), total=len(TIERS)
        )
        assert dots is not None

        def rogue(stream: ContentStream) -> None:
            for dot in dots.dots:
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
                stream.begin_path(*corners[0])
                for corner in corners[1:]:
                    stream.line_to(*corner)
                stream.close_path()
                stream.paint("fill")

        text = _appended(arm_page, rogue)
        found, declared = _vector_arm_reading(text, (), arm_page.height_px)
        assert declared == (), "a rogue route declares nothing"
        assert len(found) == len(dots.dots), (
            f"{len(dots.dots)} polygons were painted and {len(found)} measure round"
        )
        assert _unaccounted(found, declared) == found, (
            "every one of them is undeclared, so every one is the verdict"
        )

    def test_a_stroked_ring_is_round_to_this_arm_and_hollow_to_the_other(
        self, arm_page: ArmPage
    ) -> None:
        """The two arms' one measured disagreement, asserted rather than tolerated.

        A stroked circle's **path** encloses a full disc, so this reading calls
        it round; its **ink** is a ring with paper inside, so the raster
        reading calls it hollow (a bound that module's docstring states). Both
        numbers are measured here, on one glyph, so the difference is a
        property of the two domains and not a disagreement about the page.
        """
        dots = difficulty_dots(*arm_page.box, filled=1, total=len(TIERS))
        assert dots is not None
        outlined = [
            dot for index, dot in enumerate(dots.dots) if not dots.is_filled(index)
        ]
        assert outlined, "the glyph draws no outlined dot at this rank"

        text = _appended(arm_page, lambda stream: _write_the_glyph(stream, dots))
        before = len(stream_marks(_stream_text(arm_page.stream)))
        written = stream_marks(text)[before:]
        rings = [mark for mark in written if mark.paint not in PAINTS_THAT_FILL]
        assert len(rings) == len(outlined)
        for ring in rings:
            assert ring.is_round, (
                f"a stroked circle's path encloses fill {ring.fill}, which this "
                "reading does not call round"
            )

        page = arm_page.bitmap.copy()
        book_pdf_generator._draw_difficulty_dots(
            ImageDraw.Draw(page), TIERS[0], *arm_page.box
        )
        regions = {region.box: region for region in ink_regions(page, MARK_LEVEL)}
        for dot in outlined:
            assert dot in regions, "an outlined dot put no ink on the page"
            assert not regions[dot].is_round, (
                "the raster reading calls a ring round, so the hollow bound "
                "this file states has gone"
            )
            assert regions[dot].fill < 1.0 - ROUND_FILL_TOLERANCE

    def test_a_typed_round_mark_is_outside_this_arms_reach(
        self, arm_page: ArmPage
    ) -> None:
        """The arm's other bound, with the raster arm as its control.

        Type is not a path: a round glyph set as a character reaches the file
        inside a text object, so this arm reads none of it. Two measurements,
        because the bound turned out to be narrower on this medium than on the
        other and saying only the first would overstate it:

        * **the glyph's own dingbat cannot be typed here at all.** ``\u25cf``
          is outside the interior's cp1252 encoding and the writer refuses it
          (``UnrepresentableText``), so the raster route's typed spelling is
          closed by the medium rather than by this reader;
        * **the bound still stands**, because a round-ish character the
          encoding *does* carry — ``\u00b7``, the middle dot the band itself
          is set with — reaches the stream as a string and this reader
          measures no subpath for it.

        The control is the **other** arm: the same dingbat, drawn as type on a
        bitmap, is a round ink region. That is why both arms are kept rather
        than one widened.
        """
        with pytest.raises(book_vector.UnrepresentableText):
            _appended(
                arm_page,
                lambda stream: stream.text("\u25cf", 100.0, 100.0, 24.0),
            )

        before = len(stream_marks(_stream_text(arm_page.stream)))
        text = _appended(
            arm_page,
            lambda stream: stream.text("\u00b7", 100.0, 100.0, 24.0),
        )
        assert "\u00b7" in text, "the typed mark never reached the stream"
        assert len(stream_marks(text)) == before, (
            "this reader measured a subpath for a glyph set as type, which it "
            "reads none of"
        )
        found, _ = _vector_arm_reading(text, (), arm_page.height_px)
        assert found == ()

        page = arm_page.bitmap.copy()
        _rogue_typed_dingbat(ImageDraw.Draw(page), arm_page.box)
        assert round_marks(page), (
            "the raster arm cannot see the typed mark either, so this bound "
            "has no control"
        )

    def test_the_filling_paints_are_a_subset_of_the_readers_own_set(self) -> None:
        """:data:`PAINTS_THAT_FILL` cannot name an operator the reader ignores."""
        painting = {
            operator
            for operator, paints in round_ink._PAINT_OPERATORS.items()
            if paints
        }
        assert PAINTS_THAT_FILL <= painting, (
            f"{sorted(PAINTS_THAT_FILL - painting)} fill nothing the reader reads"
        )
        assert "S" in painting and "S" not in PAINTS_THAT_FILL, (
            "a stroke is a paint and is not a fill"
        )

    def test_the_readers_vocabulary_covers_every_operator_the_writer_emits(
        self,
    ) -> None:
        """The cell above, widened from paints to the **whole** vocabulary.

        ADR-0039/R2. The reader's own comments carried a claim about the
        product — "this project's writer emits neither ``v`` nor ``y``" — and
        nothing bound it to the writer, while three operator classes the reader
        passed over (``cm``, ``Do``, ``sh``) were in no list at all. That is the
        shape this card's whole thesis is about, one layer down: the liveness
        probe stays green on 588 painted subpaths of grid rules while a dot
        drawn through a route the reader cannot see goes unaccounted.

        So the vocabulary is held to an **enumerated authority** instead:
        :func:`_writer_operators` is the union of what
        ``_content_stream_doors`` records when it *drives* every public
        ``ContentStream`` member. Every operator in it must be understood,
        refused, or a recorded pass-over — and the day the writer grows one, it
        is in none of the three and this cell reds.
        """
        # The authority is only the whole surface if its probe could call every
        # member. That module asserts this too; it is restated here because
        # *this* cell's "every operator the writer emits" rests on it.
        assert _WRITER_UNCLASSIFIED_DOORS == (), (
            "the writer has a public member nothing drives, so the operator "
            f"set below is not its whole surface: {_WRITER_UNCLASSIFIED_DOORS}"
        )
        emitted = _writer_operators()
        assert emitted == WRITER_OPERATORS_RECORDED, (
            "the writer's measured operator surface moved: "
            f"gained {sorted(emitted - WRITER_OPERATORS_RECORDED)}, "
            f"lost {sorted(WRITER_OPERATORS_RECORDED - emitted)}"
        )

        understood = set(round_ink._PATH_OPERANDS) | set(round_ink._PAINT_OPERATORS)
        refused = set(round_ink._REFUSED_PATH_OPERATORS) | set(
            round_ink._REFUSED_STATE_OPERATORS
        )
        passed_over = set(WRITER_OPERATORS_NOT_A_PATH)

        # The three classifications are a partition, not three overlapping
        # opinions: an operator in two of them makes the verdict below depend
        # on which branch of the reader happens to run first.
        assert not understood & refused, sorted(understood & refused)
        assert not understood & passed_over, sorted(understood & passed_over)
        assert not refused & passed_over, sorted(refused & passed_over)

        unknown = emitted - understood - passed_over - refused
        assert not unknown, (
            f"the writer emits {sorted(unknown)}, which tests/helpers/round_ink.py "
            "neither understands, refuses, nor records as a pass-over — so the "
            "vector arm's reading of a page carrying it is wrong or short, and "
            "the liveness probe would stay green either way"
        )
        collides = emitted & refused
        assert not collides, (
            f"the writer emits {sorted(collides)}, which the reader now REFUSES: "
            "every stream of the corpus raises StreamShapeError"
        )

        # And the pass-over list is held down as well as up: an entry naming an
        # operator the writer does not emit is a pass-over nobody measured, and
        # is how this list would start absorbing the next cm.
        stale = passed_over - emitted
        assert not stale, (
            f"{sorted(stale)} are recorded as pass-overs the writer emits, and "
            "it does not emit them"
        )

        # The other half of the authority: the surface partitioned into the
        # operators that put a PATH on a page. All of them are understood —
        # which is the claim the reader's comments made and did not check.
        assert set(_WRITER_PATH_OPERATORS) <= understood, (
            f"{sorted(set(_WRITER_PATH_OPERATORS) - understood)} put a path on "
            "a page and this reader does not understand them"
        )
        assert emitted & set(_WRITER_PATH_OPERATORS), (
            "the writer emits no path operator at all, so this cell is "
            "measuring an empty intersection"
        )

    def test_an_operator_the_reader_would_misread_is_refused_not_ignored(
        self,
    ) -> None:
        """``cm``, ``Do``, ``sh`` and ``BI``, each with its matched control.

        Cycle 1 of this card's review measured all three of the first against
        the reader as committed: a ``10 10 20 20 re f`` under
        ``2 0 0 2 0 0 cm`` reported its **untransformed** box, bit-identical to
        the same rect with no transform; ``/Im0 Do`` and ``/Sh0 sh`` each
        reported 0 marks and raised nothing. Tolerating them is not a missing
        mark, it is the **wrong** mark — and the wrong direction is the
        dangerous one, because a path-space ellipse printed as a circle by a
        non-uniform ``cm`` is a round mark the no-round-mark cells would not
        find.

        The control is the same stream without the operator, read and measured,
        so "refused" is a change of verdict rather than a reader that refuses
        everything. ``q``/``Q`` is the second control and the reason that set
        does not list them: a graphics state saved and restored moves nothing
        unless something moved the CTM in between, and the only operator that
        can is ``cm``.
        """
        rect = "10 10 20 20 re f"
        (plain,) = stream_marks(rect)
        assert (plain.x0, plain.y0, plain.x1, plain.y1) == (10.0, 10.0, 30.0, 30.0)

        for stream, what in (
            (f"2 0 0 2 0 0 cm {rect}", "a transform (cm)"),
            ("q 100 0 0 100 0 0 cm /Im0 Do Q", "an external object (Do)"),
            ("/Sh0 sh", "a shading (sh)"),
            ("BI /W 1 /H 1 /CS /G /BPC 8 ID z EI", "an inline image (BI)"),
        ):
            try:
                tolerated = stream_marks(stream)
            except round_ink.StreamShapeError:
                continue
            raise AssertionError(
                f"{what} passed this reader silently; it reported "
                f"{len(tolerated)} marks "
                f"{[(m.x0, m.y0, m.x1, m.y1) for m in tolerated]}, and a "
                "silent pass is what ADR-0039/R2 refuses"
            )

        # q/Q alone: read, not refused, and the same box as without them.
        (bracketed,) = stream_marks(f"q {rect} Q")
        assert (bracketed.x0, bracketed.y0, bracketed.x1, bracketed.y1) == (
            plain.x0,
            plain.y0,
            plain.x1,
            plain.y1,
        ), "q/Q moved a box, so refusing cm is not enough to close the CTM"

        # And every recorded pass-over, in one stream with the rect: still read,
        # still one mark, still the same box — the control for the other half of
        # the vocabulary cell above.
        state_and_type = (
            "0 g 0 G 1 w BT /F1 10 Tf 1 1 Td (x) Tj ET "
            f"/ClueDigit BMC {rect} EMC"
        )
        (through_state,) = stream_marks(state_and_type)
        assert (
            through_state.x0,
            through_state.y0,
            through_state.x1,
            through_state.y1,
        ) == (plain.x0, plain.y0, plain.x1, plain.y1)

    def test_an_integer_pixel_reaches_the_stream_exactly(self) -> None:
        """Why the accounting rounds to three places instead of tolerating a gap.

        A seeded sweep of dots on integer pixels, written and read back: the
        worst disagreement between the path's own box and the declared box
        converted to points is **1.137e-13 pt**, eleven orders inside the
        1/1000 pt the stream writes at. So rounding both sides to the stream's
        own places is lossless, and the match can be exact.

        The worst case over this test's own 200-case sweep is **1.1369e-13
        pt**, which is where the recorded figure comes from.
        """
        generator = random.Random(331)
        worst = 0.0
        cases = 0
        for _ in range(200):
            left = generator.randrange(0, 2400)
            top = generator.randrange(0, 3200)
            side = generator.randrange(8, 120)
            right, bottom = left + side, top + side
            stream = ContentStream(width_px=2550.0, height_px=3300.0, dpi=DPI)
            stream.round_mark(
                (left + right) / 2.0,
                (top + bottom) / 2.0,
                (right - left) / 2.0,
                paint="fill",
            )
            (mark,) = stream_marks(_stream_text(stream))
            declared = _declared_in_points((left, top, right, bottom), 3300)
            worst = max(
                worst, max(abs(a - b) for a, b in zip(mark.box, declared))
            )
            assert _at_the_streams_places(mark.box) == _at_the_streams_places(declared)
            cases += 1
        assert cases == 200, "the sweep lost cases"
        assert worst < 5e-4, (
            f"a dot on integer pixels misses its declared box by {worst} pt, "
            "which the stream's own three places no longer absorb"
        )

    def test_the_flattening_costs_far_less_than_the_tolerance_it_is_read_against(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """``_BEZIER_SEGMENTS``' price, derived at three segment counts.

        A ``round_mark`` circle's ``fill`` reads 0.999859 at 32 segments and
        1.000255 at 256, where it has converged; the flattening's own error is
        therefore 3.96e-4 of the ratio, which is 0.33 % of
        :data:`ROUND_FILL_TOLERANCE`. Measured by moving the segment count,
        which is also the control: a flattening coarse enough to matter would
        move the number.

        Moved through ``monkeypatch.context()`` rather than by rebinding the
        global and restoring it in a ``finally``. The ``finally`` was correct
        serially and the cell re-asserted the restored value, but
        ``round_ink._BEZIER_SEGMENTS`` is reachable from 21 test modules
        through the ``page_ink`` hop, and a sibling reading a round mark while
        this cell held 8 would get a ``fill`` 0.9 % off — inside
        :data:`ROUND_FILL_TOLERANCE`, so **silent** rather than loud. Nothing in
        this repo runs workers in parallel today; a scoped patch is what keeps
        that from being the reason (engineering-standards §6).
        """
        stream = ContentStream(width_px=1000.0, height_px=1000.0, dpi=DPI)
        stream.round_mark(500.0, 500.0, 50.0, paint="fill")
        text = _stream_text(stream)
        readings: dict[int, float] = {}
        for segments in (8, round_ink._BEZIER_SEGMENTS, 256):
            with monkeypatch.context() as patched:
                patched.setattr(round_ink, "_BEZIER_SEGMENTS", segments)
                (mark,) = stream_marks(text)
                readings[segments] = mark.fill
        assert round_ink._BEZIER_SEGMENTS == 32, "the flattening's value moved"
        cost = abs(readings[256] - readings[32])
        assert cost == pytest.approx(3.96e-4, abs=1e-5), (
            f"the flattening's error is {cost}, not the 3.96e-4 recorded"
        )
        assert cost < ROUND_FILL_TOLERANCE / 100, (
            "the flattening now costs more than a hundredth of the tolerance "
            "it is read against"
        )
        assert abs(readings[8] - readings[256]) > cost, (
            "a coarse flattening reads the same as a fine one, so this "
            "measurement is not measuring the flattening"
        )
        for reading in readings.values():
            assert abs(reading - 1.0) <= ROUND_FILL_TOLERANCE

    def test_a_shape_the_reader_cannot_analyse_is_a_failure(self) -> None:
        """ADR-0039/R2, in the reader itself: it refuses rather than skipping."""
        with pytest.raises(round_ink.StreamShapeError):
            stream_marks("10 10 m 20 20 30 30 y f")
        with pytest.raises(round_ink.StreamShapeError):
            stream_marks("10 10 m 20 20 30 30 v S")
        with pytest.raises(round_ink.StreamShapeError):
            stream_marks("f")
        with pytest.raises(round_ink.StreamShapeError):
            stream_marks("10 m")
        # And the control: the shapes it does understand are read, not refused.
        assert len(stream_marks("0 0 10 10 re f 20 20 m 30 20 l 30 30 l h f")) == 2

    def test_a_wrong_count_in_the_stream_reds_this_arm(
        self, arm_page: ArmPage
    ) -> None:
        """AC-5 on this medium: a dot too few, and a dot too many.

        Both directions, because the accounting is a multiset and the two are
        not the same failure: an undeclared mark lands in the verdict, and a
        declaration nobody drew leaves the verdict empty while the counts
        disagree. A guard that only compared the verdict would pass the
        second.
        """
        dots = difficulty_dots(
            *arm_page.box, filled=_rank(PLANTED_TIER), total=len(TIERS)
        )
        assert dots is not None
        text = _appended(arm_page, lambda stream: _write_the_glyph(stream, dots))

        # one dot too few declared: the undeclared one is the verdict
        found, short = _vector_arm_reading(
            text, dots.dots[:-1], arm_page.height_px
        )
        assert len(_unaccounted(found, short)) == 1

        # one dot too many declared: the verdict is empty and the counts are not
        over = dots.dots + (dots.dots[0],)
        found, declared = _vector_arm_reading(text, over, arm_page.height_px)
        assert _unaccounted(found, declared) == ()
        assert len(found) != len(declared), (
            "a declaration nobody drew is invisible to the verdict alone, which "
            "is why the count is asserted beside it"
        )


class TestDifficultyDots_TheRasterArmHoldsWithoutHookingTheProduct:
    """AC-3: the same accounting on a bitmap page, and nothing is hooked.

    The legacy harness above hooks two module attributes — a spy on
    ``_draw_difficulty_dots`` so the interior walk's own calls are declared,
    and a wrapper on ``_set_band`` so a plant reaches a real band. **Those
    hooks stay**, and the one-line justification AC-3 asks for is this: the
    legacy harness measures the *interior walk*, which calls the drawing site
    itself and hands this file no caller to read a return value from, so
    removing its spy would mean rebuilding the walk's accounting rather than
    the hook — work that belongs to whichever card re-points those 27 cells.

    This arm needs no hook at all, and that is the point. It draws the page,
    then calls the drawing site itself: the declaration is the site's own
    return value, obtained by calling it. :meth:`test_this_arm_hooks_no_production_attribute`
    holds that structurally over the arm's own named functions, with a
    detector that has a control each way.
    """

    def test_this_arm_hooks_no_production_attribute(self) -> None:
        """No rebinding, no ``setattr``, no ``monkeypatch`` in the arm's own text."""
        assert _production_hooks(_raster_arm_sources()) == []
        assert set(_raster_arm_sources()) == set(RASTER_ARM_FUNCTIONS), (
            "a function of the arm has no source to read"
        )

    def test_the_hook_detector_can_fire(self) -> None:
        """Its control: the three spellings of a hook, each caught; honest text, not.

        And the legacy harness is the fourth case, and the one that matters:
        the detector is pointed at :func:`_interior_ink`, which really does
        hook, and must report it — so "this arm hooks nothing" is a
        measurement against an instrument that *can* say otherwise, in this
        same file.
        """
        assert _production_hooks(
            {"rebind": "book_pdf_generator._draw_difficulty_dots = spy\n"}
        ) == ["rebind rebinds book_pdf_generator._draw_difficulty_dots"]
        assert _production_hooks({"setattr": "setattr(book_pdf_generator, 'x', 1)\n"}) == [
            "setattr calls setattr"
        ]
        assert _production_hooks(
            {"fixture": "def test_it(monkeypatch) -> None:\n    pass\n"}
        ) == ["fixture takes the monkeypatch fixture"]
        assert _production_hooks({"honest": "dots = _draw_difficulty_dots(draw, t, 0, 0, 1, 1)\n"}) == []
        legacy = _production_hooks({"legacy": inspect.getsource(_interior_ink)})
        assert legacy, (
            "the detector reports nothing against the harness that admits to "
            "hooking two attributes, so it cannot report anything"
        )
        assert any("_draw_difficulty_dots" in finding for finding in legacy)
        assert any("_set_band" in finding for finding in legacy)

    def test_the_bitmap_page_carries_no_round_mark_of_its_own(
        self, arm_page: ArmPage
    ) -> None:
        """The quiet verdict on this medium, with its own denominator."""
        regions = ink_regions(arm_page.bitmap, MARK_LEVEL)
        assert len(regions) >= RASTER_ARM_MIN_REGIONS, (
            f"only {len(regions)} ink regions on the bitmap puzzle page — it "
            "has stopped carrying the marks this test exists to tolerate"
        )
        assert [region.box for region in regions if region.is_round] == [], (
            "the bitmap puzzle page carries a round mark nobody declared"
        )

    def test_a_declared_glyph_is_found_as_ink_and_accounted_for(
        self, arm_page: ArmPage
    ) -> None:
        """The honest route, with no hook: the site is called, not replaced."""
        page = arm_page.bitmap.copy()
        found, declared = _raster_arm_reading(page, arm_page.box, _declaring_plant)
        assert len(declared) == _rank(PLANTED_TIER), (
            "the filled dots are what this medium declares: a ring is not "
            f"round to it, so {_rank(PLANTED_TIER)} were expected"
        )
        assert len(found) == len(declared), (
            f"{len(declared)} filled dots were drawn and {len(found)} round ink "
            "regions are on the page"
        )
        assert _unaccounted(found, declared) == (), (
            "a dot the one drawing site drew is not matched by its own box"
        )

    def test_a_rogue_glyph_on_the_bitmap_page_is_unaccounted(
        self, arm_page: ArmPage
    ) -> None:
        """And the arm can fail on its own medium (AC-5, the raster half)."""
        page = arm_page.bitmap.copy()
        found, declared = _raster_arm_reading(page, arm_page.box, _rogue_plant)
        assert declared == (), "a rogue route declares nothing"
        assert len(found) >= _rank(PLANTED_TIER), (
            f"the rogue glyph put {len(found)} round marks on the page"
        )
        assert _unaccounted(found, declared) == found

    def test_a_wrong_count_on_the_bitmap_reds_this_arm(
        self, arm_page: ArmPage
    ) -> None:
        """AC-5 on this medium: a dot too few declared, and one too many."""
        page = arm_page.bitmap.copy()
        found, declared = _raster_arm_reading(page, arm_page.box, _declaring_plant)
        assert len(found) >= 2, "the glyph draws fewer than two filled dots"
        assert len(_unaccounted(found, declared[:-1])) == 1
        assert _unaccounted(found, declared + (declared[0],)) == ()
        assert len(found) != len(declared) + 1


# --------------------------------------------------------------------------
# AC-5's own evidence, derived instead of transcribed
# --------------------------------------------------------------------------
#
# AC-5 declared its verifier as "the per-assertion table in `## Worktree
# notes`" — prose. Three commits after that table was written, 4 of its 5
# distinct line numbers pointed at other code: the table was transcribed out of
# a `--tb=line` run, and the commit that renamed a cell shifted every line
# below it. Nothing re-derived it, so nothing noticed.
#
# The table is DATA here, and what it cites is what cannot drift: the cell by
# name and the assertion by its own source text, normalised through
# `ast.unparse` so whitespace and line breaks do not enter into it. The card's
# table now points at this cell instead of carrying line numbers, which is the
# standing rule this board adopted on CARD-317's F-003 — a criterion verified
# only by prose is a visibility regression.


def _assertions_of(owner: str, leaf: str) -> list[str]:
    """Every ``assert``'s own tested expression in ``owner.leaf``, in order.

    Source text, normalised by ``ast.unparse``: an assertion cited this way
    survives every reformatting and every line shift, and stops being citable
    the moment the assertion itself changes — which is the point.
    """
    target = getattr(globals()[owner], leaf)
    tree = ast.parse(textwrap.dedent(inspect.getsource(target)))
    return [
        ast.unparse(node.test)
        for node in ast.walk(tree)
        if isinstance(node, ast.Assert)
    ]


def _assert_messages_of(owner: str, leaf: str) -> list[str]:
    """Every ``assert``'s own failure message in ``owner.leaf``, as source text."""
    target = getattr(globals()[owner], leaf)
    tree = ast.parse(textwrap.dedent(inspect.getsource(target)))
    return [
        ast.unparse(node.msg)
        for node in ast.walk(tree)
        if isinstance(node, ast.Assert) and node.msg is not None
    ]


#: AC-5's evidence: one row per plant of this round, naming the **wrongness**
#: it introduces, the cell it reds, and the assertion inside that cell it
#: reaches. ``(arm, mutant, wrongness, kind, class, method, assertion)``.
#:
#: Three kinds per arm, because a test short-circuits at its first failing
#: assert and a surviving mutant looks exactly like a never-reached assertion:
#: *liveness* (the arm's source is gone), *count* (the declaration and the
#: reading disagree in number) and *verdict* (they agree in number and not in
#: place). MUT-7/MUT-8 alone would have left the verdict assertion unmeasured.
AC5_PER_ASSERTION: tuple[tuple[str, str, str, str, str, str, str], ...] = (
    (
        "raster",
        "MUT-2",
        "the page arrives as operators",
        "liveness",
        "TestDifficultyDots_AnArmWhoseMechanismIsDeadFails",
        "test_each_arms_mechanism_is_still_exercised",
        "liveness.alive",
    ),
    (
        "raster",
        "MUT-7",
        "one dot too few is declared",
        "count",
        "TestDifficultyDots_TheRasterArmHoldsWithoutHookingTheProduct",
        "test_a_declared_glyph_is_found_as_ink_and_accounted_for",
        "len(declared) == _rank(PLANTED_TIER)",
    ),
    (
        "raster",
        "MUT-14",
        "the declared boxes are shifted one device pixel, so the counts agree",
        "verdict",
        "TestDifficultyDots_TheRasterArmHoldsWithoutHookingTheProduct",
        "test_a_declared_glyph_is_found_as_ink_and_accounted_for",
        "_unaccounted(found, declared) == ()",
    ),
    (
        "vector",
        "MUT-1",
        "the writer emits an empty stream",
        "liveness",
        "TestDifficultyDots_AnArmWhoseMechanismIsDeadFails",
        "test_each_arms_mechanism_is_still_exercised",
        "liveness.alive",
    ),
    (
        "vector",
        "MUT-8",
        "one dot too few is declared",
        "count",
        "TestDifficultyDots_TheVectorArmReadsTheStream",
        "test_a_declared_glyph_is_found_in_the_stream_and_accounted_for",
        "len(declared) == len(dots.dots)",
    ),
    (
        "vector",
        "MUT-15",
        "the declared boxes are flipped about the wrong page height, so the "
        "counts agree",
        "verdict",
        "TestDifficultyDots_TheVectorArmReadsTheStream",
        "test_a_declared_glyph_is_found_in_the_stream_and_accounted_for",
        "_unaccounted(found, declared) == ()",
    ),
)


class TestDifficultyDots_AC5ReachesADistinctAssertionPerWrongness:
    """AC-5's evidence, re-derived off the cells rather than read off a table.

    This class is the whole of F-002's remedy. AC-5's claim is not "both arms
    have a failing test" — it is "each wrongness reaches **its own**
    assertion", which is a claim about the structure of two cells, and a claim
    about structure can be derived from the structure.
    """

    def test_each_wrongness_ac5_names_reaches_its_own_assertion(self) -> None:
        """Every row of :data:`AC5_PER_ASSERTION` names an assertion that exists.

        The citation is the assertion's **source text**, so this cell reds both
        ways: an assertion that is edited or deleted stops matching, and a row
        kept for a cell that no longer carries it stops matching too. Neither
        failure mode is available to a line number, which is what went stale.
        """
        assert len(AC5_PER_ASSERTION) == 6, len(AC5_PER_ASSERTION)
        for arm, mutant, wrongness, kind, owner, leaf, assertion in (
            AC5_PER_ASSERTION
        ):
            assert owner in globals(), f"{mutant} names a class that is gone: {owner}"
            assert hasattr(globals()[owner], leaf), (
                f"{mutant} names a cell that is gone: {owner}::{leaf}"
            )
            tests = _assertions_of(owner, leaf)
            assert tests.count(assertion) == 1, (
                f"{mutant} ({arm}, {kind}: {wrongness}) cites "
                f"{assertion!r} in {owner}::{leaf}, which carries it "
                f"{tests.count(assertion)} times. Its assertions are {tests}"
            )

    def test_the_count_and_the_verdict_are_two_assertions_not_one(self) -> None:
        """The separation itself, per arm, and in the order that makes it matter.

        A fused ``assert count and verdict`` would satisfy every row above and
        measure one thing: the short-circuit AC-5 exists to name. So the two
        are required to be **distinct** assert statements of the same cell,
        with the count strictly **earlier** — which is what makes "MUT-7 alone
        would have left the verdict unmeasured" a fact about this code rather
        than a story about it.
        """
        for arm in ("raster", "vector"):
            rows = {
                kind: (owner, leaf, assertion)
                for row_arm, _, _, kind, owner, leaf, assertion in AC5_PER_ASSERTION
                if row_arm == arm
            }
            assert set(rows) == {"liveness", "count", "verdict"}, (
                f"the {arm} arm reaches {sorted(rows)}, not three distinct "
                "wrongnesses"
            )
            count_owner, count_leaf, count_assertion = rows["count"]
            verdict_owner, verdict_leaf, verdict_assertion = rows["verdict"]
            assert (count_owner, count_leaf) == (verdict_owner, verdict_leaf), (
                f"the {arm} arm's count and verdict are in different cells, so "
                "neither can short-circuit the other and this cell is vacuous"
            )
            assert count_assertion != verdict_assertion
            tests = _assertions_of(count_owner, count_leaf)
            # Both present before either is located, so a fused or deleted
            # assertion reds with a message rather than raising ValueError out
            # of ``list.index`` — a crash reads as a broken instrument, and
            # this cell's whole job is to be readable when it fires.
            missing = [
                assertion
                for assertion in (count_assertion, verdict_assertion)
                if assertion not in tests
            ]
            assert not missing, (
                f"the {arm} arm's {count_owner}::{count_leaf} no longer carries "
                f"{missing} as an assertion of its own — fused into another "
                f"assert, or gone. Its assertions are {tests}"
            )
            assert tests.index(count_assertion) < tests.index(verdict_assertion), (
                f"the {arm} arm's verdict assertion runs BEFORE its count "
                f"assertion in {count_owner}::{count_leaf}, so the count is "
                "the one a short-circuit hides"
            )
            # And the liveness assertion is elsewhere: the arm's source going
            # dead is not a wrongness the accounting cells can see at all,
            # which is this card's whole subject.
            assert rows["liveness"][:2] != (count_owner, count_leaf)
