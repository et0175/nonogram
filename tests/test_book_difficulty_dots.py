"""CARD-228 — difficulty as three dots, filled by tier: one glyph the whole book reuses.

    AC-1  TestDifficultyDots_FilledCountIsTheTierRank
    AC-2  TestDifficultyDots_ReadsTheProjectsTierOrder
    AC-3  TestDifficultyDots_FilledAndOutlinedAreDistinguishable
    AC-4  TestDifficultyDots_HasExactlyOneDrawingSite
    AC-5  TestDifficultyDots_FitsTheSmallestHeader
    AC-6  TestDifficultyDots_UntieredDrawsNothing
          TestDifficultyDots_GeometryHoldsOverASeededCorpus (the invariants)

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
import random
from collections.abc import Mapping
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw

import nonogram
from nonogram.admin import book_pdf_generator
from nonogram.admin.book_pdf_generator import (
    _MIN_BAND_FONT_RATIO,
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
from nonogram.export.png import BACKGROUND

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
TEXT_METHODS = frozenset({"multiline_text", "text"})

#: Everything else Pillow's draw object does: flat shapes and the measuring
#: calls. Unguarded, and said so — a straight line, a rectangle and the four
#: calls that only *measure* have no vertex list and no string to hide a dot
#: in, which is why these are the residue after the four guarded sets above
#: rather than "everything that is not an ellipse".
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
#: ``draw``, or an inline ``ImageDraw.Draw(...)``. Completeness is measured
#: rather than assumed — see
#: :meth:`TestDifficultyDots_HasExactlyOneDrawingSite.test_every_draw_object_in_the_package_is_spelled_draw`.
DRAW_RECEIVER_NAME = "draw"

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
    """AC-4: one function draws the dots; every caller goes through it.

    Asserted the way ``tests/test_cli.py`` asserts ADR-0007's import rule —
    by walking ``src/nonogram/**/*.py`` with ``ast`` — because a promise that
    four later cards will reuse one function is worth nothing unless a fifth
    dot is a test failure. The walk is over the whole package, so CARD-207,
    CARD-229, CARD-231 and CARD-233 cannot grow a second dot glyph **by any
    of the four routes guarded below** wherever they end up drawing.

    **Exactly how far this reaches, and where it stops.** The claim is the
    width of the mechanism and no wider; review cycle 1 (F-001) planted three
    second glyphs that an earlier, more confidently worded version of this
    class let through. Four routes are guarded, each by a control that fires:

    1. an ellipse drawn as an ellipse — :data:`ELLIPSE_METHODS`, zero calls
       outside :data:`THE_DRAWING_SITE`;
    2. the four approximation methods the package calls nowhere —
       :data:`ROUND_ENOUGH_METHODS`, zero calls at all;
    3. a circle built out of vertices — :data:`VERTEX_BOUNDED_METHODS`, held
       to :data:`MAX_FLAT_VERTICES` rather than to absence, because the
       package really does call ``draw.polygon``;
    4. a dot typed as a character — :data:`ROUND_DINGBATS`, which is the route
       CARD-207 would most cheaply take.

    What this instrument **cannot** see, named rather than argued away, since
    the set of methods it watches is derived from ``dir(ImageDraw.ImageDraw)``
    and the walk reads written syntax:

    * anything outside ``ImageDraw`` entirely — ``Image.paste`` of a circular
      mask, ``ImageDraw.floodfill`` (a module function, not a draw method), a
      pre-rendered PNG asset pasted in, a circle that arrives inside an
      imported image;
    * a dynamically dispatched draw call, ``getattr(draw, "ellipse")(box)``
      (also stated on :func:`_round_mark_sites`);
    * a vertex list this walk cannot count — which it treats as a failure
      rather than a pass, so it is a blind spot that shows itself;
    * a draw object reached by a receiver this package does not currently use
      (:data:`DRAW_RECEIVER_NAME` has its own completeness test, so a new
      spelling fails that test rather than slipping past this one).

    A card taking one of the first two routes would be making a deliberate
    choice this guard should be extended for. That is a narrower promise than
    "cannot each grow their own circles", and it is the one the tests keep.
    """

    def test_the_method_classification_covers_every_pillow_draw_method(self) -> None:
        """The completeness test for the set the guard consults — its own oracle.

        Every public method of Pillow's draw object is classified into exactly
        one of the three sets above. A Pillow release that adds a method fails
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
        # and it is made here instead (cycle 1, F-006).
        assert f"def {THE_DRAWING_SITE[1]}" in sources[THE_DRAWING_SITE[0]]
        assert getattr(book_pdf_generator, THE_DRAWING_SITE[1]) is _draw_difficulty_dots

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

    def test_every_draw_object_in_the_package_is_spelled_draw(self) -> None:
        """The receiver set's own completeness test — :func:`_is_draw_receiver`'s oracle.

        ``point`` is a method of ``Image`` as well as of the draw object, so
        the vertex guard below has to tell ``draw.point([...])`` (ink) from
        ``greyscale.point([...])`` (a pixel-value map) and does it on the
        receiver. That only works if every draw object in the package really
        is spelled :data:`DRAW_RECEIVER_NAME` or built inline, which is what
        this measures: every ``ImageDraw.Draw(...)`` the package assigns, and
        every parameter it annotates ``ImageDraw.ImageDraw``, carries that one
        name. A module introducing a second spelling fails here, where the
        remedy is obvious, instead of quietly widening the blind spot.
        """
        assigned: set[str] = set()
        annotated: set[str] = set()
        for source in _package_sources().values():
            for node in ast.walk(ast.parse(source)):
                if (
                    isinstance(node, ast.Assign)
                    and isinstance(node.value, ast.Call)
                    and isinstance(node.value.func, ast.Attribute)
                    and node.value.func.attr == "Draw"
                ):
                    assigned |= {
                        target.id
                        for target in node.targets
                        if isinstance(target, ast.Name)
                    }
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for argument in (*node.args.posonlyargs, *node.args.args):
                        annotation = argument.annotation
                        if (
                            isinstance(annotation, ast.Attribute)
                            and annotation.attr == "ImageDraw"
                        ):
                            annotated.add(argument.arg)
        assert assigned == {DRAW_RECEIVER_NAME}, assigned
        assert annotated == {DRAW_RECEIVER_NAME}, annotated

    def test_no_module_draws_a_round_mark_out_of_vertices(self) -> None:
        """A polygon with enough vertices is a circle; this bounds the vertices.

        Cycle 1 (F-001/H2) put a 32-gon tier glyph in ``export/png.py`` and
        every test stayed green, because ``polygon`` was binned flat on the
        reasoning that "none of them can draw a circle" while
        ``regular_polygon`` — strictly less capable — was binned round.
        Absence is not available as a claim for ``polygon``: the proof sheet's
        pipeline diagram really does draw an arrow head with it. So the bound
        is on the shape, not on the call.

        A vertex list this walk cannot count is a **failure**, not a pass: a
        card that computes its points (a comprehension, a helper, a name) has
        to say so by extending this guard, which is the declaration the lenient
        reading would have let it skip.
        """
        calls = _draw_calls(_package_sources(), VERTEX_BOUNDED_METHODS)
        assert calls, (
            "no draw-object call to "
            f"{sorted(VERTEX_BOUNDED_METHODS)} remains in the package — this guard "
            "has gone vacuous; keep it honest by pointing it at a fabricated "
            "source, as test_a_many_sided_polygon_is_caught does"
        )
        for module, function, call in calls:
            points = call.args[0] if call.args else None
            assert isinstance(points, (ast.List, ast.Tuple)), (
                module,
                function,
                "vertices this guard cannot count",
            )
            assert len(points.elts) <= MAX_FLAT_VERTICES, (
                module,
                function,
                len(points.elts),
            )

    def test_a_many_sided_polygon_is_caught(self) -> None:
        """Control, caught: cycle 1's surviving H2 mutant, against the new guard."""
        points = ", ".join(f"({index}, {index})" for index in range(32))
        rogue = {"fake.mod": f"def dots(draw):\n    draw.polygon([{points}], fill=1)\n"}
        calls = _draw_calls(rogue, VERTEX_BOUNDED_METHODS)
        assert [(module, function) for module, function, _ in calls] == [
            ("fake.mod", "dots")
        ]
        with pytest.raises(AssertionError):
            for _, _, call in calls:
                assert len(call.args[0].elts) <= MAX_FLAT_VERTICES

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
        # as safe: not a countable literal, so not a pass.
        assert not isinstance(calls[0][2].args[0], (ast.List, ast.Tuple))

    def test_a_three_vertex_arrow_head_is_not_caught(self) -> None:
        """Control, not caught: the guard bounds roundness, not drawing.

        Without this the bound's discriminating power would be unknown — a
        guard that rejected every polygon would also pass the two controls
        above.
        """
        flat = {
            "fake.mod": (
                "def arrow(draw):\n"
                "    draw.polygon([(0, 0), (4, 2), (0, 4)], fill=1)\n"
            )
        }
        calls = _draw_calls(flat, VERTEX_BOUNDED_METHODS)
        assert len(calls) == 1
        assert len(calls[0][2].args[0].elts) <= MAX_FLAT_VERTICES

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
