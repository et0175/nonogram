"""EC-006, EC-007 and EC(ADR-0022/R3) — fitting an image to the grid's shape.

    EC-006  PropertyTest_FitImage_CropBoxIsLargestCentredRectangleOfTargetAspect
    EC-007  PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore
    ADR-0022/R3
            PropertyTest_FitImage_NeverStretchesAndNeverPads
    ADR-0022/R3 (2026-09-01 revision, CARD-030)
            PropertyTest_AspectGuard_JudgesInkBoxBeforeAnyCropIsApplied

Three of the four are standing properties of two pure functions of four
integers (``source_width, source_height, target_width, target_height``), which
is why they can be swept over a large corpus for the price of arithmetic. The
fourth is about *order* rather than arithmetic and so has to run real
conversions; it is swept over shapes instead of over integers, and instruments
the pipeline rather than inspecting its output.

What the corpus is, and why it is not ``hypothesis``
----------------------------------------------------
CLAUDE.md's test policy: no ``hypothesis`` (it is not in ADR-0006's dependency
baseline), so a "property" test here builds a large seeded corpus by hand with
stdlib ``random.Random`` and asserts a **minimum case count inside the test**,
so the corpus cannot silently shrink into vacuity. Every property below whose
verdict has two sides also asserts a minimum count for *each* of them — a
corpus that only contained refusals would pass a guard that refuses everything,
which is exactly the failure EC-007's "if and only if" is written to exclude.
Measured on this tree at the seeds below, the splits are comfortable rather
than marginal: the primary EC-007 corpus is 796 accepted / 704 refused of 1500,
and the symmetry corpus 405 / 395 of 800.

Where the expectations come from
--------------------------------
Not from the functions under test. The crop box is checked against its
*defining* properties, evaluated in exact rational arithmetic
(:mod:`fractions`) rather than by re-running the implementation's integer
floor-division — and, for every source small enough to brute-force,
against an independent **search**: enumerate every rectangle of exactly the
target ratio that fits inside the source, and bound the returned box **from
both sides** against them — it must contain every one of them, and it must not
reach the next one up. A one-sided containment claim is not an oracle: the box
that returns the whole source contains every exact rectangle too. That search
shares no line of reasoning with the implementation.

The threshold constants (``0.5`` retained, a ``2x`` ratio difference) are
written as literals here for the same reason ``tests/property/test_size_range``
writes ``10`` and ``30`` as literals: a test that reads its expectation off the
constant under test follows that constant anywhere and asserts nothing about
where the boundary is.
"""

from __future__ import annotations

import random
from fractions import Fraction
from pathlib import Path

import pytest
from PIL import Image

from nonogram.errors import ImageNeedsManualCrop, UnreadableImage
from nonogram.sourcing import image

SEED = 20260831

#: The rule, as two literals rather than as a reference to the implementation:
#: a centred crop to the grid's ratio keeps ``min(r_src, r_tgt) /
#: max(r_src, r_tgt)`` of the source, and a request is accepted exactly when
#: that is at least a half — equivalently when the two ratios differ by at most
#: twofold. The boundary is inclusive (CON-012, guardrail G-5).
MIN_RETAINED = Fraction(1, 2)
MAX_RATIO_DIFFERENCE = 2

#: The supported grid range (CON-011), named here rather than imported for the
#: reason the module docstring gives.
MIN_SIDE = 10
MAX_SIDE = 30


# --------------------------------------------------------------------------
# The independent oracle
# --------------------------------------------------------------------------


def _ratio(width: int, height: int) -> Fraction:
    return Fraction(width, height)


def _exact_cropped_extent(
    source_width: int, source_height: int, target_width: int, target_height: int
) -> tuple[bool, Fraction]:
    """``(the source is the wider of the two, the exact cropped extent)``.

    The real-valued rectangle of exactly the target ratio that touches both
    source edges on its uncropped axis. The implementation floors this onto the
    pixel grid; the assertions below bracket the returned integer against it
    rather than recomputing the floor, so a change of rounding is visible as a
    bracket violation rather than silently agreed with.
    """
    target = _ratio(target_width, target_height)
    if _ratio(source_width, source_height) >= target:
        return True, source_height * target
    return False, source_width / target


def _retained_fraction(
    source_width: int, source_height: int, target_width: int, target_height: int
) -> Fraction:
    """``min(r_src, r_tgt) / max(r_src, r_tgt)``, in exact rational arithmetic.

    The quantity CON-012 is stated over, computed the way the requirement
    writes it — two ratios, then a quotient — rather than the way the
    implementation computes it (one cross-multiplication, no division at all).
    """
    source = _ratio(source_width, source_height)
    target = _ratio(target_width, target_height)
    return min(source, target) / max(source, target)


def _largest_exact_ratio_rectangles(
    source_width: int, source_height: int, target_width: int, target_height: int
) -> list[tuple[int, int]]:
    """Every whole-pixel rectangle of *exactly* the target ratio fitting inside.

    A brute-force search, deliberately: it enumerates candidates and filters
    them by the definition, so it can disagree with any formula. Only usable on
    small sources, which is why the property that uses it runs on its own
    small-extent corpus.
    """
    target = _ratio(target_width, target_height)
    return [
        (width, height)
        for width in range(1, source_width + 1)
        for height in range(1, source_height + 1)
        if Fraction(width, height) == target
    ]


# --------------------------------------------------------------------------
# The corpora
# --------------------------------------------------------------------------


def _target_extents() -> list[tuple[int, int]]:
    """Every supported grid shape: all 441 pairs in 10..30 x 10..30."""
    return [
        (width, height)
        for width in range(MIN_SIDE, MAX_SIDE + 1)
        for height in range(MIN_SIDE, MAX_SIDE + 1)
    ]


def _source_extents(rng: random.Random, count: int) -> list[tuple[int, int]]:
    """A seeded spread of source extents across four orders of magnitude.

    Named extents first — the three AC-071..AC-079 shapes and the degenerate
    strips a floor-to-zero needs — then a random spread, so the corpus contains
    both the cases the criteria talk about and cases nobody chose.
    """
    named = [
        (563, 980),  # the increment's worked example (eagle-silhouette1.jpg)
        (600, 600),
        (980, 563),
        (1, 1),
        (1, 30),
        (30, 1),
        (2, 3),
        (4000, 3),
    ]
    spread = []
    while len(spread) < count:
        magnitude = rng.choice([2, 20, 200, 4000])
        spread.append(
            (rng.randint(1, magnitude), rng.randint(1, magnitude))
        )
    return named + spread


def _pairs(rng: random.Random, count: int) -> list[tuple[int, int, int, int]]:
    """``count`` seeded (source, target) quadruples over the two corpora."""
    targets = _target_extents()
    sources = _source_extents(rng, count)
    return [
        (*rng.choice(sources), *rng.choice(targets)) for _ in range(count)
    ]


# --------------------------------------------------------------------------
# EC-006 — PropertyTest_FitImage_CropBoxIsLargestCentredRectangleOfTargetAspect
# --------------------------------------------------------------------------


def test_property_fit_image_crop_box_is_the_largest_centred_rectangle_of_target_aspect() -> None:
    """EC-006 verbatim, over the whole corpus.

    "For any source image dimensions and any accepted (width, height) request,
    the crop box is the largest centred sub-rectangle of the source whose aspect
    ratio equals width/height: it lies entirely within the source bounds and
    touches both source edges on at least one axis, for every such input."

    Four claims, checked separately so a failure names which one broke:

    1. **Inside the source.** No coordinate is negative or past an edge, and
       neither extent is zero — a crop box that left the source would be
       padding by another name.
    2. **Touches both source edges on at least one axis.** That axis is kept
       whole, which is what makes the rectangle maximal: it cannot grow along
       it without leaving the source.
    3. **Of the target's aspect ratio,** to the precision a pixel grid has. The
       cropped axis is the floor of the exact rational extent that would give
       the ratio exactly — asserted by bracketing that exact value between the
       returned extent and one more pixel, in ``Fraction`` arithmetic.
    4. **Centred.** The two discarded margins differ by at most one pixel and
       the near one is never the larger (AC-073's half-pixel bias, pinned in the
       direction the module documents).
    """
    rng = random.Random(SEED)
    cases = _pairs(rng, 1200)
    accepted = 0

    for source_width, source_height, target_width, target_height in cases:
        left, upper, right, lower = image.fit_crop_box(
            source_width, source_height, target_width, target_height
        )
        crop_width, crop_height = right - left, lower - upper
        where = (source_width, source_height, target_width, target_height)

        # 1. inside the source
        assert 0 <= left < right <= source_width, where
        assert 0 <= upper < lower <= source_height, where

        # 2. one axis kept whole
        keeps_width = (left, right) == (0, source_width)
        keeps_height = (upper, lower) == (0, source_height)
        assert keeps_width or keeps_height, where

        # 3. the cropped axis is the floor of the exact extent — or the
        #    declared one-pixel clamp, when that floor would be zero
        source_is_wider, exact = _exact_cropped_extent(*where)
        if source_is_wider:
            assert keeps_height, where
            cropped = crop_width
        else:
            assert keeps_width, where
            cropped = crop_height
        if exact >= 1:
            assert cropped <= exact < cropped + 1, (where, exact)
        else:
            assert cropped == 1, (where, exact)

        # 4. centred, with the odd pixel on the far side
        assert 0 <= (source_width - crop_width) - 2 * left <= 1, where
        assert 0 <= (source_height - crop_height) - 2 * upper <= 1, where

        if _retained_fraction(*where) >= MIN_RETAINED:
            accepted += 1

    assert len(cases) >= 1200
    # EC-006 is stated over *accepted* requests, so the corpus has to contain a
    # substantial number of them rather than being all refusals.
    assert accepted >= 300, accepted


def test_property_fit_image_is_bracketed_by_the_exact_ratio_rectangles_that_fit() -> None:
    """EC-006's "largest", against an independent brute-force search, **both
    ways**.

    For every source small enough to enumerate, let the search produce every
    whole-pixel rectangle of *exactly* the target ratio that fits inside the
    source. Those rectangles are the multiples ``(k * p, k * q)`` of the target
    ratio in lowest terms, and the returned crop box is bracketed between two
    consecutive ones:

    * **From below** — it contains every one of them, on both axes. A formula
      that cropped the wrong axis drops the largest.
    * **From above** — it reaches neither extent of the *next* multiple, the
      first one that does not fit. This is the half that makes the search an
      oracle rather than a rubber stamp: containment alone is satisfied by
      returning the whole source, which is precisely the stretch ADR-0022/R3
      forbids, and by any over-large box a ceil would produce.

    Both bounds are read off the enumeration, not off a formula: the largest
    fitting multiple comes from the search, and the step to the next one is the
    target ratio reduced by :class:`~fractions.Fraction`. Mutation-checked when
    it was written — ``return (0, 0, source_width, source_height)``, cropping
    the other axis, and ``-(-x // y)`` in place of ``x // y`` each fail here.
    """
    rng = random.Random(SEED + 1)
    targets = _target_extents()
    cases = 0
    with_a_witness = 0

    for _ in range(400):
        source_width = rng.randint(1, 60)
        source_height = rng.randint(1, 60)
        target_width, target_height = rng.choice(targets)
        left, upper, right, lower = image.fit_crop_box(
            source_width, source_height, target_width, target_height
        )
        crop_width, crop_height = right - left, lower - upper
        where = (source_width, source_height, target_width, target_height)
        exact = _largest_exact_ratio_rectangles(*where)

        for width, height in exact:
            assert width <= crop_width, (where, (width, height))
            assert height <= lower - upper, (where, (width, height))

        if exact:
            # The next multiple of the target ratio after the largest one that
            # fits. The box must not reach it on either axis, or it would be
            # keeping pixels an exactly-proportioned crop cannot use.
            widest, tallest = max(exact)
            ratio = _ratio(target_width, target_height)
            step_width, step_height = ratio.numerator, ratio.denominator
            assert crop_width < widest + step_width, (where, (widest, tallest))
            assert crop_height < tallest + step_height, (
                where, (widest, tallest)
            )

        cases += 1
        with_a_witness += bool(exact)

    assert cases == 400
    # Most small sources admit no exactly-proportioned rectangle at all, so both
    # brackets would be vacuous without this: it pins that the search really did
    # produce rectangles to check against.
    assert with_a_witness >= 100, with_a_witness


def test_property_fit_image_reproduces_the_square_crop_for_every_square_grid() -> None:
    """The generalization is a superset, not a replacement (AC-072).

    At ``target_width == target_height`` the box must be the largest centred
    square of the source — computed here by the two-line rule the removed
    ``square_crop_box`` used, which is an implementation this module owns and
    the module under test no longer contains.
    """
    rng = random.Random(SEED + 2)
    cases = 0

    for source_width, source_height in _source_extents(rng, 400):
        edge = min(source_width, source_height)
        expected = (
            (source_width - edge) // 2,
            (source_height - edge) // 2,
            (source_width - edge) // 2 + edge,
            (source_height - edge) // 2 + edge,
        )
        for side in (MIN_SIDE, 17, MAX_SIDE):
            assert image.fit_crop_box(
                source_width, source_height, side, side
            ) == expected, (source_width, source_height, side)
            cases += 1

    assert cases >= 1200


# --------------------------------------------------------------------------
# EC-007 —
# PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore
# --------------------------------------------------------------------------


def _accepts(
    source_width: int, source_height: int, target_width: int, target_height: int
) -> bool:
    try:
        image.validate_aspect_ratio(
            source_width, source_height, target_width, target_height
        )
    except ImageNeedsManualCrop:
        return False
    return True


def test_property_aspect_guard_accepts_exactly_those_requests_retaining_half_or_more() -> None:
    """EC-007 verbatim, both directions, over the whole corpus.

    "For any source image dimensions and any (width, height) pair in 10..30, the
    request is accepted if and only if ``min(r_src, r_tgt) / max(r_src, r_tgt)
    >= 0.5`` with ``r = width/height``."

    The "if and only if" is the whole claim, so the corpus is required to
    contain a substantial number of *both* verdicts: a guard that accepted
    everything and a guard that refused everything each satisfy one half of the
    equivalence on a lopsided corpus.
    """
    rng = random.Random(SEED + 3)
    cases = _pairs(rng, 1500)
    accepted = refused = 0

    for source_width, source_height, target_width, target_height in cases:
        retained = _retained_fraction(
            source_width, source_height, target_width, target_height
        )
        verdict = _accepts(
            source_width, source_height, target_width, target_height
        )
        assert verdict is (retained >= MIN_RETAINED), (
            source_width, source_height, target_width, target_height, retained
        )
        accepted += verdict
        refused += not verdict

    assert len(cases) >= 1500
    assert accepted >= 300, accepted
    assert refused >= 300, refused


def test_property_aspect_guard_pins_both_sides_of_the_inclusive_boundary() -> None:
    """The boundary itself, at every supported grid shape (guardrail G-5).

    For each of the 441 grid shapes, two sources are constructed by exact
    integer arithmetic: one whose ratio is precisely twice the grid's, and one
    a single pixel past that. The first retains exactly one half and must be
    **accepted**; the second retains less and must be refused. A strict ``>``
    on the retained fraction fails on the first — that is what this pins.

    It does **not** pin the integer decision itself, and says so rather than
    claiming it: substituting ``(kept / whole) >= 0.5`` for the implementation's
    ``2 * kept >= whole`` leaves this test, the three other guard properties and
    AC-075 all green (measured). With source extents at most 4000 px and grid
    sides at most 30, both cross-products stay under 120000, every one of them
    is exactly representable as a ``float``, and IEEE division of ``x`` by
    ``2 * x`` is exact — so no *reachable* input distinguishes the two
    decisions. The integer form is kept because it is unconditionally right
    rather than right within a bound nobody re-checks when the bound moves, not
    because a test can currently tell.

    Constructed rather than sampled, because a random corpus essentially never
    lands on an exact boundary — which is how a boundary bug survives one.
    """
    exactly_two_fold = 0
    just_past = 0

    for target_width, target_height in _target_extents():
        for scale in (1, 7, 53):
            # r_src = 2 * r_tgt exactly.
            source_width = MAX_RATIO_DIFFERENCE * target_width * scale
            source_height = target_height * scale
            assert _retained_fraction(
                source_width, source_height, target_width, target_height
            ) == MIN_RETAINED
            assert _accepts(
                source_width, source_height, target_width, target_height
            ), (source_width, source_height, target_width, target_height)
            exactly_two_fold += 1

            # One pixel wider on the same source: strictly past the threshold.
            assert _retained_fraction(
                source_width + 1, source_height, target_width, target_height
            ) < MIN_RETAINED
            assert not _accepts(
                source_width + 1, source_height, target_width, target_height
            ), (source_width + 1, source_height, target_width, target_height)
            just_past += 1

            # And the mirror image, with the source the narrower of the two.
            assert _accepts(
                target_width * scale,
                MAX_RATIO_DIFFERENCE * target_height * scale,
                target_width,
                target_height,
            )
            assert not _accepts(
                target_width * scale,
                MAX_RATIO_DIFFERENCE * target_height * scale + 1,
                target_width,
                target_height,
            )

    assert exactly_two_fold == 441 * 3
    assert just_past == 441 * 3


def test_property_aspect_guard_is_symmetric_in_which_side_is_wider() -> None:
    """AC-078 generalised: transposing *both* shapes leaves the verdict alone.

    ``min/max`` is symmetric, so a source and grid pair judged acceptable must
    stay acceptable when both are rotated a quarter turn. An implementation
    that compared ``r_src`` against ``r_tgt`` with the wrong sign somewhere
    passes the one-sided examples and fails here.

    Symmetry alone is satisfied by a guard that accepts everything and by one
    that refuses everything, so both verdicts are counted: the corpus splits 405
    accepted / 395 refused at this seed (measured), and the floors below are set
    well under those so a re-seed does not break the test, while a corpus that
    collapsed onto one verdict would.
    """
    rng = random.Random(SEED + 4)
    cases = _pairs(rng, 800)
    accepted = refused = 0

    for source_width, source_height, target_width, target_height in cases:
        verdict = _accepts(
            source_width, source_height, target_width, target_height
        )
        assert verdict is _accepts(
            source_height, source_width, target_height, target_width
        ), (source_width, source_height, target_width, target_height)
        accepted += verdict
        refused += not verdict

    assert len(cases) >= 800
    assert accepted >= 100, accepted
    assert refused >= 100, refused


def test_property_a_degenerate_source_is_refused_before_the_ratio_is_considered() -> None:
    """The zero-pixel source, preserved from ``square_crop_box`` (AC-008's
    neighbour): it is the user's file being unusable, so it is that error and
    not the aspect one, whatever the ratios would have said."""
    rng = random.Random(SEED + 5)
    cases = 0

    for target_width, target_height in _target_extents():
        for source_width, source_height in (
            (0, rng.randint(1, 4000)),
            (rng.randint(1, 4000), 0),
            (0, 0),
        ):
            for call in (image.fit_crop_box, image.validate_aspect_ratio):
                with pytest.raises(UnreadableImage):
                    call(source_width, source_height, target_width, target_height)
                cases += 1

    assert cases == 441 * 3 * 2


# --------------------------------------------------------------------------
# EC(ADR-0022/R3) — PropertyTest_FitImage_NeverStretchesAndNeverPads
# --------------------------------------------------------------------------


def test_property_fit_image_never_stretches_and_never_pads() -> None:
    """ADR-0022/R3's standing property, structurally.

    "For every source and every target shape, the fitted image is produced by a
    centred crop followed by an isotropic resize — never by stretching the whole
    source and never by padding."

    *Never pads* is the crop box lying entirely inside the source: there is no
    coordinate outside it for padding to come from, so the resampler only ever
    sees the user's own pixels.

    *Never stretches* is the crop's own ratio being the target's rather than the
    source's. Stretching is the implementation that returns the whole source
    every time, so the discriminating assertion is that whenever the two ratios
    differ by at least one pixel's worth, the returned box is **not** the whole
    source — plus the exact bracket that says which rectangle it is instead.
    """
    rng = random.Random(SEED + 6)
    cases = _pairs(rng, 1200)
    genuinely_cropped = 0

    for source_width, source_height, target_width, target_height in cases:
        left, upper, right, lower = image.fit_crop_box(
            source_width, source_height, target_width, target_height
        )
        crop_width, crop_height = right - left, lower - upper
        where = (source_width, source_height, target_width, target_height)

        # never pads
        assert (left, upper) >= (0, 0), where
        assert right <= source_width and lower <= source_height, where

        # never stretches: the crop's ratio is the target's, floored onto the
        # pixel grid, so it is within one pixel of exact on the cropped axis.
        source_is_wider, exact = _exact_cropped_extent(*where)
        if source_is_wider:
            assert crop_height == source_height, where
            cropped = crop_width
        else:
            assert crop_width == source_width, where
            cropped = crop_height
        if exact >= 1:
            assert cropped <= exact < cropped + 1, (where, exact)
        else:
            assert cropped == 1, (where, exact)

        if (crop_width, crop_height) != (source_width, source_height):
            genuinely_cropped += 1

    assert len(cases) >= 1200
    # A crop that always returned the whole source would pass every assertion
    # above vacuously on a corpus of exactly-matching shapes.
    assert genuinely_cropped >= 1000, genuinely_cropped


CONVERSION_SHAPES = [
    (563, 980, 15, 30),
    (563, 980, 20, 20),
    (600, 600, 30, 15),
    (600, 600, 15, 30),
    (980, 563, 30, 15),
    (120, 90, 30, 30),
    (90, 120, 10, 12),
    (61, 41, 29, 19),
]


def test_property_a_solid_source_converts_to_a_solid_grid_at_every_shape(
    tmp_path: Path,
) -> None:
    """The same claim end to end, on real conversions rather than on geometry.

    A wholly black source contains no white anywhere, so a letterboxed
    conversion would have to invent it: any padding row or column arrives as an
    empty cell. Every accepted shape below therefore converts to a grid that is
    filled in every cell and has exactly the requested extent — the strongest
    "no padding, no stray dimension" statement available without inspecting the
    crop box at all.

    Kept to a handful of real Pillow conversions on purpose; the geometry is
    swept above, and a resize per case is orders of magnitude more expensive
    than the arithmetic.
    """
    for source_width, source_height, target_width, target_height in CONVERSION_SHAPES:
        path = tmp_path / f"solid-{source_width}x{source_height}.png"
        if not path.exists():
            Image.new("L", (source_width, source_height), 0).save(path)

        greyscale = image.load_greyscale(path)
        # A wholly black source is entirely ink, so its bounding box is the
        # whole sheet and the trim is a no-op — which is what makes it still
        # the letterbox witness after FR-022 rather than a picture of itself.
        assert image.ink_bounding_box(greyscale) == (
            0, 0, source_width, source_height
        )
        image.validate_aspect_ratio(
            source_width, source_height, target_width, target_height
        )
        grid = image.to_grid(
            image.binarize(greyscale, target_width, target_height)
        )

        assert len(grid) == target_height
        assert {len(row) for row in grid} == {target_width}
        assert all(all(row) for row in grid), (
            source_width, source_height, target_width, target_height
        )

    assert len(CONVERSION_SHAPES) >= 8


# --------------------------------------------------------------------------
# EC(ADR-0022/R3, 2026-09-01) —
# PropertyTest_AspectGuard_JudgesInkBoxBeforeAnyCropIsApplied
# --------------------------------------------------------------------------


def _picture_on_a_sheet(
    tmp_path: Path,
    ink_width: int,
    ink_height: int,
    margin_x: int,
    margin_y: int,
) -> tuple[Path, tuple[int, int], tuple[int, int]]:
    """A black ``ink_width`` x ``ink_height`` rectangle centred on white paper.

    Returns ``(path, sheet extent, ink extent)``. The margins are given per
    axis and are deliberately unequal in most of the corpus below: an equal
    margin only ever pulls the sheet's ratio *towards* 1:1, so it can make the
    retired whole-file reading wrongly accept but hardly ever wrongly refuse,
    and a corpus of one-sided disagreements cannot show that the file reading
    "errs both ways rather than conservatively" (ADR-0022).
    """
    sheet = (ink_width + 2 * margin_x, ink_height + 2 * margin_y)
    path = tmp_path / f"sheet-{ink_width}x{ink_height}-{margin_x}x{margin_y}.png"
    if not path.exists():
        picture = Image.new("L", sheet, 255)
        picture.paste(
            0, (margin_x, margin_y, margin_x + ink_width, margin_y + ink_height)
        )
        picture.save(path)
    return path, sheet, (ink_width, ink_height)


#: ``(ink width, ink height, margin x, margin y)``, chosen so that against the
#: grid shapes swept below the ink-box verdict and the whole-file verdict
#: disagree in *both* directions: pairs the file reading would wrongly accept
#: (a wide subject on a nearly square sheet) and pairs it would wrongly refuse
#: (a square subject on a wide sheet). A corpus where the two always agree
#: cannot distinguish them at all.
INK_EXTENTS = [
    (600, 120, 40, 200),
    (120, 600, 200, 40),
    (400, 400, 400, 0),
    (400, 400, 0, 400),
    (400, 200, 200, 200),
    (200, 400, 200, 200),
    (500, 260, 300, 20),
    (260, 500, 20, 300),
]


class _CropWatch:
    """Counters for every function in this module that crops or converts.

    ``binarize`` calls ``fit_crop_box`` through the module's own globals, so
    patching the attribute catches the internal call as well as ``generate``'s.
    ``Image.Image.crop`` is patched too, because FR-022's trim is a Pillow
    method rather than one of this module's functions — an implementation that
    trimmed first and judged afterwards would leave the three named counters at
    zero and still have cropped the user's picture.
    """

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.calls: dict[str, int] = {
            "fit_crop_box": 0,
            "binarize": 0,
            "to_grid": 0,
            "Image.crop": 0,
        }
        for name in ("fit_crop_box", "binarize", "to_grid"):
            monkeypatch.setattr(image, name, self._counted(name, getattr(image, name)))
        monkeypatch.setattr(
            Image.Image, "crop", self._counted("Image.crop", Image.Image.crop)
        )

    def _counted(self, name, function):  # type: ignore[no-untyped-def]
        def wrapper(*args, **kwargs):  # type: ignore[no-untyped-def]
            self.calls[name] += 1
            return function(*args, **kwargs)

        return wrapper

    @property
    def total(self) -> int:
        return sum(self.calls.values())


def test_property_aspect_guard_judges_the_ink_box_before_any_crop_is_applied(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ADR-0022/R3 as revised 2026-09-01, both halves, instrumented.

    *Judges the ink box*: the verdict must follow the ratio of the ink bounding
    box, never the ratio of the file it sits on. Each source below is a black
    rectangle centred on a much larger white sheet, so the two ratios differ;
    the expected verdict is computed from the ink extent in exact rational
    arithmetic by :func:`_retained_fraction`, the same oracle EC-007 uses, and
    the corpus is required to contain pairs where the file reading would have
    disagreed — in both directions, since a reading that is merely conservative
    would be defensible and this one is not (ADR-0022: it errs both ways).

    *Before any crop is applied*: every function in ``sourcing.image`` that
    crops, resizes or converts is counted, and ``Image.Image.crop`` with them so
    that FR-022's own trim cannot slip through as "not one of ours". For a
    refused request all four counters must be **zero** — the guard's refusal
    arrives with the user's picture untouched, which is the whole of what
    EC-007 promises now that a decode necessarily precedes it. For an accepted
    request they must be non-zero, or the property would be satisfied by a
    pipeline that never converts anything.
    """
    watch = _CropWatch(monkeypatch)
    accepted = refused = 0
    file_reading_would_have_accepted = 0
    file_reading_would_have_refused = 0

    for ink_width, ink_height, margin_x, margin_y in INK_EXTENTS:
        path, sheet, ink = _picture_on_a_sheet(
            tmp_path, ink_width, ink_height, margin_x, margin_y
        )
        for target_width, target_height in _target_extents()[::17]:
            expected = (
                _retained_fraction(*ink, target_width, target_height)
                >= MIN_RETAINED
            )
            by_the_file = (
                _retained_fraction(*sheet, target_width, target_height)
                >= MIN_RETAINED
            )
            if by_the_file and not expected:
                file_reading_would_have_accepted += 1
            if expected and not by_the_file:
                file_reading_would_have_refused += 1

            before = dict(watch.calls)
            try:
                grid = image.generate(
                    path, target_width, target_height, random.Random(SEED)
                )
            except ImageNeedsManualCrop:
                assert not expected, (ink, sheet, target_width, target_height)
                assert watch.calls == before, (
                    "a refused request cropped something",
                    {
                        name: watch.calls[name] - before[name]
                        for name in watch.calls
                        if watch.calls[name] != before[name]
                    },
                )
                refused += 1
            else:
                assert expected, (ink, sheet, target_width, target_height)
                assert len(grid) == target_height
                assert {len(row) for row in grid} == {target_width}
                assert watch.total > sum(before.values())
                accepted += 1

    assert accepted + refused >= 200, (accepted, refused)
    assert accepted >= 40, accepted
    assert refused >= 40, refused
    # The discriminating half: on this corpus the retired whole-file reading
    # would have got the verdict wrong in *both* directions, so the assertions
    # above cannot be satisfied by an implementation that still judges the file.
    assert file_reading_would_have_accepted >= 10, file_reading_would_have_accepted
    assert file_reading_would_have_refused >= 10, file_reading_would_have_refused
