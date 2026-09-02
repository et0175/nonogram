"""COMP-003's image source (FR-003, CARD-015) — conversion, policy and wiring.

Acceptance criteria, by the card's test names:

    AC-007  TestConvertImage_ProducesDitheredGrid        -> test_convert_image_produces_a_dithered_grid*
    AC-008  TestConvertImage_RejectsUnreadableFile       -> test_convert_image_rejects_an_unreadable_file*
    AC-059  TestConvertImage_ProducesExactTargetDimensionsWithinAcceptedRatioBand
                                                         -> test_convert_image_produces_exact_target_dimensions_within_the_accepted_ratio_band
    AC-071  TestFitImage_CropsToRequestedAspectRatio     -> test_fit_image_crops_to_the_requested_aspect_ratio
    AC-072  TestFitImage_SquareGridReproducesSquareCropBox
                                                         -> test_fit_image_square_grid_reproduces_the_square_crop_box
    AC-073  TestFitImage_CropIsCentredOnBothAxes         -> test_fit_image_crop_is_centred_on_both_axes
    AC-074  TestFitImage_ProducesExactDimensionsWithoutLetterbox
                                                         -> test_fit_image_produces_exact_dimensions_without_letterbox
    AC-075  TestAspectGuard_AcceptsExactlyTwoFoldRatioDifference
                                                         -> test_aspect_guard_accepts_exactly_a_two_fold_ratio_difference
    AC-076  TestAspectGuard_RefusesRatioDifferenceAboveTwoFold
                                                         -> test_aspect_guard_refuses_a_ratio_difference_above_two_fold
    AC-077  TestAspectGuard_RefusalMessageSuggestsManualCrop
                                                         -> test_aspect_guard_refusal_message_suggests_a_manual_crop
    AC-078  TestAspectGuard_ThresholdIsSymmetricInSourceAndTarget
                                                         -> test_aspect_guard_threshold_is_symmetric_in_source_and_target
    AC-079  TestAspectGuard_AcceptsWellMatchedPortraitSource
                                                         -> test_aspect_guard_accepts_a_well_matched_portrait_source

    AC-086  TestTrimToInk_Fixes17Of19CorpusViolations
                                                         -> test_trim_to_ink_fixes_17_of_the_19_corpus_violations
    AC-087  TestTrimToInk_ReducesWorstCaseBorderToAtMostOneLine
                                                         -> test_trim_to_ink_reduces_the_worst_case_border_to_at_most_one_line
    AC-088  TestTrimToInk_AcceptsResidualBlankLinesOnDear1Jpg
                                                         -> test_trim_to_ink_accepts_the_residual_blank_lines_on_dear1_jpg
    AC-091  TestTrimToInk_AcceptsResidualBlankLinesOnWolf1Jpeg
                                                         -> test_trim_to_ink_accepts_the_residual_blank_lines_on_wolf1_jpeg
    AC-089  TestTrimToInk_MidGreyThresholdOutperformsNearWhiteThreshold
                                                         -> test_trim_to_ink_mid_grey_threshold_outperforms_the_near_white_threshold

    ADR-0022/R3  TestFitImage_RefusesRatioMismatchBeyondTwice
                                                         -> test_fit_image_refuses_a_ratio_mismatch_beyond_twice

AC-009 is **superseded** by AC-059 (FR-021). Its unqualified "a source image
whose aspect ratio differs from the target grid ... the output grid has exactly
the requested target dimensions" became false the moment a >2x difference became
a refusal, so it now asserts a converted grid for inputs the tool must reject.
Its test name ``TestConvertImage_ProducesExactTargetDimensions`` is deliberately
not reused.

Fixtures live in ``tests/fixtures/`` and are deliberately tiny (under 200 bytes
each). Their content is chosen so that the assertions below can *distinguish*
implementations rather than merely observe one:

``bands.png``    32x32, three horizontal bands — black (rows 0..10), mid-grey
                 128 (11..21), white (22..29) — closed by a **2-pixel black rule
                 along the bottom edge** (rows 30..31). The mid band is the
                 dithering witness: a plain 50% threshold renders a flat 128
                 region as one solid colour, error diffusion renders it as a
                 mixed, roughly half-filled texture.

                 The ground rule is CARD-030's doing and is load-bearing, not
                 decoration. FR-022 trims an upload to its ink bounding box, and
                 ink is a value *below* 128 — so the mid band is paper and, with
                 no rule, this fixture's ink box would be its black third alone:
                 32x11 against a 20x20 grid keeps 34% of it and FR-021 refuses
                 the conversion outright. The rule puts the sheet's bottom edge
                 back inside the picture, the box becomes the whole 32x32, the
                 trim is a no-op, and the fixture goes on testing the conversion
                 rather than the trim (which is measured against the real 25
                 pictures under ``pictures/``, below). Its thickness is 2 rather
                 than 1 because at 1 the pinned 10x10 conversion in
                 ``tests/test_nudge.py`` needs four nudges instead of the two it
                 has always needed; both are honest fixtures and the thinner one
                 was passed over only to leave that pin alone.
``landscape.png``  60x40 (3:2), vertical bands — a black sixth, white with a
                 16x16 black core, a black sixth. Against a square grid the
                 centred crop is the middle 40x40, which is *exactly* the two
                 black bands discarded: the grid's first and last columns come
                 out **empty**, whereas a stretch would put the black bands in
                 them. One assertion therefore tells the two policies apart.
                 3:2 against 1:1 keeps 67% of the picture, comfortably inside
                 FR-021's accepted band.
``portrait.png`` the transpose of ``landscape.png``, so the crop is pinned on
                 both axes rather than only on the one that happened to be
                 tested.
``wide.png``     60x20, vertical thirds — black, white with a small black core,
                 black. At 3:1 against a square grid it keeps only 33% of the
                 picture, so since CARD-026 it is not a crop fixture at all: it
                 is the natural **refusal** witness for FR-021, and the
                 conversion tests that used to run against it moved to
                 ``landscape.png``.
``tall.png``     the transpose of ``wide.png``.
``corrupt.png``  a real PNG signature followed by garbage — a file that claims
                 to be a picture and is not.

Images that are exotic rather than representative (a flat mid-grey field, an
RGBA image with a transparent hole) are built in ``tmp_path`` instead: they
exist to pin one behaviour each, and a repo fixture should be something a
reader of the test tree can open and recognise. The three sources AC-071..AC-079
name by pixel extent — 563x980, 600x600, 980x563 — are built the same way, by
the ``silhouette`` factory below: nothing about their *content* matters, only
their dimensions, and writing those dimensions in the test that depends on them
beats storing three more files whose sizes a reader would have to go and check.
``pictures/eagle-silhouette1.jpg`` is 563x980 and is the increment's worked
example; it is not in the test tree and these criteria do not need it to be.
"""

from __future__ import annotations

import argparse
import io
import random
import struct
import zlib
from collections.abc import Callable
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, UnidentifiedImageError

from nonogram import cli, orchestrator, sourcing
from nonogram.errors import (
    GenerationAbandoned,
    ImageNeedsManualCrop,
    NonogramError,
    SizeOutOfRange,
    UnreadableImage,
)
from nonogram.sourcing import image, library, random_grid

FIXTURES = Path(__file__).parent / "fixtures"

BANDS = FIXTURES / "bands.png"
LANDSCAPE = FIXTURES / "landscape.png"
PORTRAIT = FIXTURES / "portrait.png"
WIDE = FIXTURES / "wide.png"
TALL = FIXTURES / "tall.png"
CORRUPT = FIXTURES / "corrupt.png"


def _rng() -> random.Random:
    """A seeded RNG, for the argument every source takes and this one ignores."""
    return random.Random(20250828)


def _shape(grid: list[list[bool]]) -> tuple[int, set[int]]:
    """``(row count, the set of row widths)`` — one value for a square grid."""
    return len(grid), {len(row) for row in grid}


def _filled_fraction(grid: list[list[bool]]) -> float:
    cells = sum(len(row) for row in grid)
    return sum(cell for row in grid for cell in row) / cells


def _flat(value: int, tmp_path: Path, name: str = "flat.png", size: int = 64) -> Path:
    """A ``size`` x ``size`` image of one uniform grey ``value``."""
    path = tmp_path / name
    Image.new("L", (size, size), value).save(path)
    return path


@pytest.fixture(scope="session")
def silhouette(
    tmp_path_factory: pytest.TempPathFactory,
) -> Callable[[int, int], Path]:
    """A factory for a high-contrast silhouette of an exact pixel extent.

    AC-071..AC-079 are stated over three sources named only by their dimensions
    (563x980, 600x600, 980x563 — the shapes of this project's own pictures).
    What they contain is irrelevant to every one of those criteria, so they are
    built rather than stored, with the dimensions written where the criterion
    that needs them is. Session-scoped and memoised: the largest is half a
    megapixel and several tests want the same one.

    The content is a centred black ellipse on white — a silhouette, which is
    what image mode is for (CON-013) — inset far enough that a crop of either
    orientation still contains ink to observe.
    """
    directory = tmp_path_factory.mktemp("silhouettes")
    built: dict[tuple[int, int], Path] = {}

    def build(width: int, height: int) -> Path:
        if (width, height) not in built:
            path = directory / f"silhouette-{width}x{height}.png"
            picture = Image.new("L", (width, height), 255)
            inset_x, inset_y = width // 4, height // 4
            ImageDraw.Draw(picture).ellipse(
                (inset_x, inset_y, width - inset_x, height - inset_y), fill=0
            )
            picture.save(path)
            built[(width, height)] = path
        return built[(width, height)]

    return build


@pytest.fixture(scope="session")
def solid_black(
    tmp_path_factory: pytest.TempPathFactory,
) -> Callable[[int, int], Path]:
    """A factory for a wholly black image of an exact pixel extent.

    The letterbox witness: nothing in it is white, so *any* padding the
    conversion added would show up as an empty cell in the grid.
    """
    directory = tmp_path_factory.mktemp("solids")

    def build(width: int, height: int) -> Path:
        path = directory / f"solid-{width}x{height}.png"
        if not path.exists():
            Image.new("L", (width, height), 0).save(path)
        return path

    return build


def _ink_extent(source: Path) -> tuple[int, int]:
    """``(width, height)`` of ``source``'s ink bounding box, in pixels.

    The extent the aspect guard judges since CARD-030 (FR-021/CON-012 as revised
    2026-09-01), and therefore the one a test that wants to reason about the
    guard has to compute. Written as a helper rather than inline because
    :func:`nonogram.sourcing.image.ink_bounding_box` returns a Pillow crop box
    and the guard takes two extents.
    """
    with image.load_greyscale(source) as greyscale:
        left, upper, right, lower = image.ink_bounding_box(greyscale)
    return (right - left, lower - upper)


def _convert(source: Path, target_width: int, target_height: int) -> list[list[bool]]:
    """The image pipeline at an arbitrary grid extent.

    CARD-026 wrote this as a hand-assembled copy of ``generate``'s body, because
    ``generate`` still took a scalar ``size`` and a rectangular request had no
    caller. CARD-027 gave it the request's ``(width, height)`` pair (FR-018), so
    the copy is now the real thing and the helper is a one-line alias kept only
    to spell the two extents out at the call sites below. A second
    implementation of the pipeline would drift from the shipped one on the first
    change to either — which is precisely the class of defect the aspect guard
    has already produced once.
    """
    return image.generate(source, target_width, target_height, _rng())


# --------------------------------------------------------------------------
# The fixtures themselves — guard the guard (see the module docstring)
# --------------------------------------------------------------------------


def test_the_two_crop_fixtures_are_inside_the_accepted_ratio_band() -> None:
    """The premise the conversion tests below rest on, made explicit.

    ``landscape.png`` and ``portrait.png`` exist *because* ``wide.png`` and
    ``tall.png`` stopped being convertible at a square grid: 3:1 against 1:1
    keeps a third of the picture and FR-021 refuses it. The replacement pair had
    to be shaped mildly enough to be accepted and extremely enough that the crop
    is still observable, and this asserts both halves at the size the
    conversion tests actually use.
    """
    for accepted in (LANDSCAPE, PORTRAIT):
        image.validate_aspect_ratio(*_ink_extent(accepted), 20, 20)
    for refused in (WIDE, TALL):
        with pytest.raises(ImageNeedsManualCrop):
            image.validate_aspect_ratio(*_ink_extent(refused), 20, 20)


def test_the_fixture_images_are_present_and_shaped_as_documented() -> None:
    """Every assertion below reasons from these dimensions; a fixture silently
    regenerated at another size would weaken the tests without failing them."""
    with Image.open(BANDS) as bands:
        assert bands.size == (32, 32)
        # The ground rule, asserted rather than trusted: without it the trim
        # would reduce this fixture to its black third and FR-021 would refuse
        # every square-grid conversion below (see the module docstring).
        pixels = bands.convert("L").load()
        assert pixels is not None
        assert (pixels[0, 29], pixels[0, 30], pixels[0, 31]) == (255, 0, 0)
    assert _ink_extent(BANDS) == (32, 32)
    with Image.open(LANDSCAPE) as landscape:
        assert landscape.size == (60, 40)
    with Image.open(PORTRAIT) as portrait:
        assert portrait.size == (40, 60)
    with Image.open(WIDE) as wide:
        assert wide.size == (60, 20)
    with Image.open(TALL) as tall:
        assert tall.size == (20, 60)
    assert CORRUPT.read_bytes().startswith(b"\x89PNG")


def test_the_fixture_images_stay_tiny() -> None:
    """They live in the repo (card step 5), so their size is part of the deal."""
    for fixture in (BANDS, LANDSCAPE, PORTRAIT, WIDE, TALL, CORRUPT):
        assert fixture.stat().st_size < 1024


# --------------------------------------------------------------------------
# AC-007 (happy) — TestConvertImage_ProducesDitheredGrid
# --------------------------------------------------------------------------


def test_convert_image_produces_a_dithered_grid() -> None:
    """AC-007 verbatim: a valid PNG and a target of 25x25 give a 25x25
    black/white grid, produced by resizing and dithering."""
    grid = image.generate(BANDS, 25, 25, _rng())

    assert _shape(grid) == (25, {25})
    assert all(cell is True or cell is False for row in grid for cell in row)
    # The black band is ink and the white band is paper: the polarity, on a
    # grid whose top and bottom are unambiguous whatever the dither does. The
    # white band now ends two source rows above the sheet's edge — the ground
    # rule the trim needs (module docstring) occupies the last one and a bit
    # grid rows — so the paper claim is made about the two rows above it.
    assert all(grid[0]) and all(grid[1])
    assert not any(grid[-3]) and not any(grid[-4])


def test_convert_image_produces_a_dithered_grid_of_plain_python_bools() -> None:
    """ADR-0012's boundary type, not a NumPy array wearing its clothes: the
    conversion runs through NumPy internally and must not leak it."""
    grid = image.generate(BANDS, 25, 25, _rng())

    assert isinstance(grid, list)
    assert all(isinstance(row, list) for row in grid)
    assert {type(cell) for row in grid for cell in row} == {bool}


def test_the_mid_tone_band_comes_out_dithered_rather_than_thresholded() -> None:
    """The card's actual ask, and the one a 50% threshold would fail.

    ``bands.png``'s middle third is a flat 128 grey. Thresholding renders it as
    one solid block (all filled or all empty); Floyd-Steinberg error diffusion
    renders it as a mixed texture whose *density* carries the grey level. So
    the assertion is that the band contains both kinds of cell and sits near
    half filled — which no thresholding implementation can satisfy.
    """
    grid = image.generate(BANDS, 24, 24, _rng())
    cells = [cell for row in grid[9:15] for cell in row]

    assert any(cells) and not all(cells)
    assert 0.35 <= sum(cells) / len(cells) <= 0.65


@pytest.mark.parametrize("value", [110, 128, 140])
def test_a_flat_mid_grey_field_dithers_to_about_its_own_level(
    value: int, tmp_path: Path
) -> None:
    """The same property stated as the thing error diffusion is *for*: filled
    density tracks the source's grey level, on an image with no edges at all
    for a resize artefact to hide behind."""
    grid = image.generate(_flat(value, tmp_path), 30, 30, _rng())

    expected = 1.0 - value / 255.0
    assert abs(_filled_fraction(grid) - expected) < 0.1


def test_black_and_white_fields_convert_without_a_dither_artefact(
    tmp_path: Path,
) -> None:
    """The two ends of the scale are not a matter of taste: a wholly black
    image is a wholly filled grid, a wholly white one a wholly empty grid.
    Error diffusion must not sprinkle either with the other."""
    assert all(
        all(row)
        for row in image.generate(_flat(0, tmp_path, "black.png"), 20, 20, _rng())
    )
    assert not any(
        any(row)
        for row in image.generate(_flat(255, tmp_path, "white.png"), 20, 20, _rng())
    )


def test_transparent_areas_are_paper_and_not_ink(tmp_path: Path) -> None:
    """A transparent PNG's alpha is flattened onto white before greyscaling.

    Without the flattening, ``convert("L")`` reads the colour *under* the
    transparent pixels — which for the usual "transparent PNG with black
    underneath" is a solid black rectangle where the user sees nothing.

    The image carries an opaque stripe at the top **and** at the bottom since
    CARD-030, for the reason ``bands.png`` grew a ground rule: flattened
    transparency is paper, paper is not ink, and a single top stripe would make
    the ink box a 40x10 band that FR-021 then refuses at a square grid. Two
    stripes leave the box the whole sheet, so this test goes on testing the
    flattening rather than the trim — and the transparent middle is still the
    only place the "paper, not ink" claim is made.
    """
    path = tmp_path / "hole.png"
    transparent = Image.new("RGBA", (40, 40), (0, 0, 0, 0))
    transparent.paste((0, 0, 0, 255), (0, 0, 40, 10))
    transparent.paste((0, 0, 0, 255), (0, 30, 40, 40))
    transparent.save(path)

    grid = image.generate(path, 20, 20, _rng())

    assert all(grid[0])  # the opaque black stripe is ink
    assert all(grid[-1])  # and so is the one at the far edge
    # The transparent field between them is paper, not the black that sits
    # underneath it in the file.
    assert not any(any(row) for row in grid[6:14])


def test_the_conversion_is_reproducible_for_the_same_file_and_size() -> None:
    grid = image.generate(LANDSCAPE, 20, 20, _rng())

    assert image.generate(LANDSCAPE, 20, 20, _rng()) == grid


def test_the_conversion_never_draws_from_the_run_rng() -> None:
    """G-4's premise, made observable: the conversion of a given file at a
    given size is fully determined, which is *why* image mode cannot be handed
    to POL-001's regenerate loop — a retry would return this same grid.

    Asserted twice over: two different seeds give the same grid, and the RNG
    handed in comes back with its state untouched.
    """
    unused = random.Random(1)
    state = unused.getstate()

    assert image.generate(BANDS, 22, 22, unused) == image.generate(
        BANDS, 22, 22, random.Random(999)
    )
    assert unused.getstate() == state


# --------------------------------------------------------------------------
# AC-008 (negative) — TestConvertImage_RejectsUnreadableFile
# --------------------------------------------------------------------------


def test_convert_image_rejects_an_unreadable_file_that_is_missing(
    tmp_path: Path,
) -> None:
    """AC-008's first half: a path to a file that is not there."""
    missing = tmp_path / "no-such-picture.png"

    with pytest.raises(UnreadableImage) as excinfo:
        image.generate(missing, 20, 20, _rng())

    assert "cannot read image" in str(excinfo.value)
    assert str(missing) in str(excinfo.value)


def test_convert_image_rejects_an_unreadable_file_that_is_corrupt() -> None:
    """AC-008's second half: a file that claims to be a PNG and is not."""
    with pytest.raises(UnreadableImage) as excinfo:
        image.generate(CORRUPT, 20, 20, _rng())

    assert "cannot read image" in str(excinfo.value)


def test_convert_image_rejects_a_path_that_is_a_directory(tmp_path: Path) -> None:
    """Not in the criterion's words, but the same failure from the user's side
    — a ``--image`` that names something unreadable — and a different OSError
    underneath, which is the point: the guard is on the outcome, not on a list
    of errno values."""
    with pytest.raises(UnreadableImage):
        image.generate(tmp_path, 20, 20, _rng())


def test_convert_image_rejects_a_missing_image_argument() -> None:
    """``--mode image`` with no ``--image``: the same domain error, with a
    message that names the forgotten flag rather than a path. The shape
    ``library.template_for`` uses for a missing ``--library-key``."""
    with pytest.raises(UnreadableImage) as excinfo:
        image.generate(None, 20, 20, _rng())

    assert "--image" in str(excinfo.value)


@pytest.mark.parametrize("unreadable", [CORRUPT, FIXTURES / "absent.png"])
def test_pillows_own_exception_never_reaches_the_caller(unreadable: Path) -> None:
    """The structural half of AC-008. ``UnidentifiedImageError`` is itself an
    ``OSError``, so "a domain error was raised" is not enough on its own —
    what is asserted is that the escaping exception is a ``NonogramError`` and
    is *not* an ``OSError`` of any kind, with Pillow's exception demoted to a
    chained ``__cause__`` for the traceback."""
    with pytest.raises(UnreadableImage) as excinfo:
        image.generate(unreadable, 20, 20, _rng())

    error = excinfo.value
    assert isinstance(error, NonogramError)
    assert not isinstance(error, OSError)
    assert not isinstance(error, UnidentifiedImageError)
    assert isinstance(error.__cause__, Exception)


def test_an_unreadable_image_produces_no_grid_and_no_puzzle(tmp_path: Path) -> None:
    """AC-008's "and no grid is produced", at the pipeline level: the run ends
    at sourcing, so no aggregate comes back and nothing is written."""
    request = orchestrator.GenerationRequest(
        mode="image",
        image=tmp_path / "absent.png",
        width=20,
        height=20,
        seed=1,
        out=tmp_path,
    )

    with pytest.raises(UnreadableImage):
        orchestrator.generate(request)

    assert list(tmp_path.iterdir()) == []


def test_the_size_rule_is_checked_before_the_file_is_opened() -> None:
    """The contract the other two sources keep: reject an invalid request
    before doing its work. An out-of-range side is reported as such even when
    the path is also unusable, so the user fixes the first thing that is
    wrong rather than the second. Checked with only the *height* out of range
    too, so the guard is not passing on the first argument alone."""
    with pytest.raises(SizeOutOfRange):
        image.generate(FIXTURES / "absent.png", 60, 60, _rng())
    with pytest.raises(SizeOutOfRange):
        image.generate(FIXTURES / "absent.png", 20, 60, _rng())


@pytest.mark.parametrize("side", [9, 31, 51, None])
def test_the_supported_extent_range_is_the_same_as_every_other_mode(
    side: int | None,
) -> None:
    """Shared from ``random_grid`` rather than restated (the rule is about the
    puzzle, not about the source), so this pins that it really is shared — on
    each axis independently, with the other held legal."""
    with pytest.raises(SizeOutOfRange):
        image.generate(BANDS, side, 20, _rng())
    with pytest.raises(SizeOutOfRange):
        image.generate(BANDS, 20, side, _rng())

    assert random_grid.MIN_SIZE == 10 and random_grid.MAX_SIZE == 30


# --------------------------------------------------------------------------
# AC-059 (boundary) —
# TestConvertImage_ProducesExactTargetDimensionsWithinAcceptedRatioBand
# --------------------------------------------------------------------------


def test_convert_image_produces_exact_target_dimensions_within_the_accepted_ratio_band(
    silhouette: Callable[[int, int], Path],
) -> None:
    """AC-059 verbatim, on the criterion's own numbers.

    A 563x980 portrait source (ratio 0.574) into a 15x30 grid (ratio 0.500):
    the ratios differ by 1.15x, inside FR-021's accepted 2x band, and the output
    grid has exactly 15 columns and 30 rows.

    Replaces AC-009, whose unqualified "differs from the target grid" now covers
    inputs the tool refuses — see the module docstring.
    """
    grid = _convert(silhouette(563, 980), 15, 30)

    assert _shape(grid) == (30, {15})


@pytest.mark.parametrize("source", [LANDSCAPE, PORTRAIT, BANDS])
@pytest.mark.parametrize("size", [10, 17, 25, 30])
def test_convert_image_produces_exact_square_dimensions_for_every_accepted_source(
    source: Path, size: int
) -> None:
    """AC-059's claim generalised over the square grids ``generate`` can still
    be asked for in this card: whatever an accepted source's aspect ratio, the
    grid has exactly the requested dimensions, at both ends of the supported
    size range."""
    assert _shape(image.generate(source, size, size, _rng())) == (size, {size})


def test_the_aspect_ratio_policy_is_centre_crop_and_not_stretch() -> None:
    """The documented policy, asserted where the two answers differ.

    ``landscape.png`` is 60x40: a black sixth | white with a black core | a
    black sixth. Against a square grid the centred crop is the middle 40x40,
    which is exactly the two black bands discarded, so the grid's first and last
    columns are empty and its centre holds the core. A stretch would map the
    outer black bands onto the grid's outer columns instead — so this one test
    tells the implemented policy from the rejected one.
    """
    grid = image.generate(LANDSCAPE, 20, 20, _rng())

    outer_columns = [row[0] for row in grid] + [row[-1] for row in grid]
    assert not any(outer_columns)
    assert any(grid[10][6:14])


def test_the_aspect_ratio_policy_holds_on_the_other_axis() -> None:
    """The same claim for a portrait source: the crop is not an accident of
    which axis the landscape fixture happened to be long on."""
    grid = image.generate(PORTRAIT, 20, 20, _rng())

    assert not any(grid[0]) and not any(grid[-1])
    assert any(grid[10][6:14])


def _ink(grid: list[list[bool]]) -> set[tuple[int, int]]:
    return {
        (row, column)
        for row, cells in enumerate(grid)
        for column, cell in enumerate(cells)
        if cell
    }


def test_exif_orientation_is_applied_before_the_crop(tmp_path: Path) -> None:
    """A phone photo's EXIF orientation is honoured, not the axis the file
    happens to be stored along.

    A camera held rotated stores the sensor's raw raster in one orientation
    and records the correction needed to display it upright in an EXIF tag
    (``Orientation``). Cropping the *stored* raster without applying that tag
    crops along the wrong axis — silently ruining the picture on exactly the
    input this feature exists for.

    Built rather than a repo fixture (JPEG EXIF is fiddly to keep byte-stable
    across Pillow versions, same reasoning as the transparent-PNG test
    above). ``displayed`` carries a small, deliberately off-centre marker —
    the aspect-ratio tests above use a symmetric pattern, which turns out to
    be *unable* to distinguish "orientation honoured" from "orientation
    ignored" here, since a symmetric image's crop is unaffected by rotation.
    An asymmetric marker is required to tell them apart, and it does:
    honouring the tag reproduces ``displayed``'s own conversion exactly;
    ignoring it (verified by also saving the same rotated raster with no
    EXIF tag at all) puts the marker at a different position entirely.
    """
    displayed = Image.new("L", (60, 40), 255)
    displayed.paste(0, (23, 4, 33, 16))  # off-centre: neither axis is symmetric

    stored = displayed.transpose(Image.Transpose.ROTATE_90)
    exif = stored.getexif()
    exif[0x0112] = 6  # "rotate 90 CW to display correctly"
    oriented = tmp_path / "phone.jpg"
    stored.save(oriented, format="JPEG", quality=100, exif=exif)

    reference_source = tmp_path / "displayed.png"
    displayed.save(reference_source)

    reference = image.generate(reference_source, 20, 20, _rng())
    honoured = image.generate(oriented, 20, 20, _rng())

    assert honoured == reference
    assert _ink(honoured)  # the marker did land somewhere, not just "matched by both being blank"


@pytest.mark.parametrize("source", [LANDSCAPE, PORTRAIT])
def test_the_outer_bands_of_the_source_do_not_reach_the_grid_at_all(
    source: Path,
) -> None:
    """The third policy, excluded: letterboxing.

    Padding the short axis to square keeps the *whole* source, so
    ``landscape.png``'s two black outer bands would land somewhere in the grid —
    squeezed into a middle band with blank rows above and below it. Cropping
    discards them outright. So the strongest statement of the policy is that the
    only ink in the grid comes from the black core at the centre: every filled
    cell is inside the central block, and there are some.
    """
    grid = image.generate(source, 20, 20, _rng())
    ink = {
        (row, column)
        for row, cells in enumerate(grid)
        for column, cell in enumerate(cells)
        if cell
    }

    assert ink
    assert all(4 <= row <= 15 and 4 <= column <= 15 for row, column in ink)


@pytest.mark.parametrize(
    ("width", "height", "expected"),
    [
        (20, 20, (0, 0, 20, 20)),  # already square: the whole image
        (60, 20, (20, 0, 40, 20)),  # landscape: the middle third
        (20, 60, (0, 20, 20, 40)),  # portrait: the middle third
        (7, 4, (1, 0, 5, 4)),  # odd leftover: the near side keeps the extra
        (4, 7, (0, 1, 4, 5)),
    ],
)
def test_the_crop_box_for_a_square_grid_is_the_largest_centred_square(
    width: int, height: int, expected: tuple[int, int, int, int]
) -> None:
    """``square_crop_box``'s whole table, carried over verbatim onto its
    replacement at a square target — the boxes are literals, not values
    re-derived from the function under test, so they pin where the crop is and
    which side keeps the odd leftover pixel."""
    box = image.fit_crop_box(width, height, 20, 20)

    assert box == expected
    left, upper, right, lower = box
    assert right - left == lower - upper == min(width, height)


@pytest.mark.parametrize(("width", "height"), [(0, 10), (10, 0), (0, 0), (-3, 10)])
def test_an_image_with_no_pixels_is_an_input_error(width: int, height: int) -> None:
    """A degenerate source is the user's file being unusable, not an
    arithmetic accident several frames later. Preserved from
    ``square_crop_box``, and asserted on the guard too — the guard runs first,
    so it is the one that actually reports it on the ``generate`` path."""
    with pytest.raises(UnreadableImage):
        image.fit_crop_box(width, height, 20, 20)
    with pytest.raises(UnreadableImage):
        image.validate_aspect_ratio(width, height, 20, 20)


@pytest.mark.parametrize(
    ("target_width", "target_height"), [(0, 20), (20, 0), (-1, 20)]
)
def test_a_zero_extent_grid_is_a_caller_bug_and_not_an_input_error(
    target_width: int, target_height: int
) -> None:
    """The other degenerate extent, declared and separated from the first.

    Grid extents reach these functions only after
    ``random_grid.validate_size``, so a target of ``0`` cannot come from a user
    — it is a wiring bug, and gets ``ValueError`` the way ``nudge`` treats a
    zeroth attempt, not a domain error the CLI would map to an exit code.
    """
    with pytest.raises(ValueError) as excinfo:
        image.fit_crop_box(60, 40, target_width, target_height)
    assert not isinstance(excinfo.value, NonogramError)

    with pytest.raises(ValueError):
        image.validate_aspect_ratio(60, 40, target_width, target_height)


# --------------------------------------------------------------------------
# AC-071..AC-074 (FR-020) — TestFitImage_* : the crop box at a rectangular grid
# --------------------------------------------------------------------------


def test_fit_image_crops_to_the_requested_aspect_ratio() -> None:
    """AC-071 verbatim, on the criterion's own numbers.

    A 563x980 portrait silhouette and a requested 15x30 grid (target ratio
    0.500): the crop box has aspect ratio 0.500 and is the largest such
    rectangle fitting inside 563x980 — 490x980, the full height and 490 of the
    563 columns. Every number here is the criterion's, written as a literal.

    "Largest" is derived rather than restated: the widest column count whose
    ``2 * columns`` rows still fit in 980 is found by search over the source's
    own width, so it is an expectation this test computes and not a consequence
    of the box it is checking. (The three assertions this replaced — the ratio,
    the in-bounds check and a maximality arithmetic — were all implied by the
    literal pin above them and could not fail on their own.)
    """
    left, upper, right, lower = image.fit_crop_box(563, 980, 15, 30)

    widest_that_fits = max(
        columns for columns in range(1, 563 + 1) if 2 * columns <= 980
    )
    assert (right - left, lower - upper) == (widest_that_fits, 980) == (490, 980)


def test_fit_image_square_grid_reproduces_the_square_crop_box() -> None:
    """AC-072: at a 20x20 grid the generalization returns exactly what the old
    ``square_crop_box`` returned for 563x980 — the largest centred square,
    ``(0, 208, 563, 771)``. The expected box is the literal the removed
    function produced, not a call to anything still in the tree.
    """
    assert image.fit_crop_box(563, 980, 20, 20) == (0, 208, 563, 771)


def test_fit_image_crop_is_centred_on_both_axes() -> None:
    """AC-073: the discarded margins on the cropped axis differ by at most one
    pixel. 563 - 490 = 73 columns are discarded, 36 on the near side and 37 on
    the far one — the half-pixel bias the module docstring pins deliberately.

    ``36`` and ``37`` are the criterion's "at most one pixel apart" **and** the
    direction of the bias, in one assertion; a separate ``abs(near - far) <= 1``
    could not fail once this one holds, so it is not written.
    """
    left, upper, right, lower = image.fit_crop_box(563, 980, 15, 30)

    assert (left, 563 - right) == (36, 37)
    # The uncropped axis: nothing discarded at either end, which is a different
    # claim about a different axis and can fail on its own.
    assert (upper, 980 - lower) == (0, 0)


def test_fit_image_produces_exact_dimensions_without_letterbox(
    silhouette: Callable[[int, int], Path],
    solid_black: Callable[[int, int], Path],
) -> None:
    """AC-074: converted end to end, a 563x980 source into a 15x30 grid gives
    exactly 15 columns by 30 rows, with no letterbox padding row or column and
    no anisotropic stretch.

    "No letterbox" is asserted the way the policy is falsifiable: an all-black
    source has no white in it anywhere, so *any* padding would show up as an
    empty cell. A stretch is excluded separately by the crop box's own ratio.
    """
    grid = _convert(silhouette(563, 980), 15, 30)
    assert _shape(grid) == (30, {15})

    solid = _convert(solid_black(563, 980), 15, 30)
    assert all(all(row) for row in solid)


# --------------------------------------------------------------------------
# AC-075..AC-079 (FR-021) — TestAspectGuard_* : the >2x refusal
# --------------------------------------------------------------------------


def test_aspect_guard_accepts_exactly_a_two_fold_ratio_difference(
    silhouette: Callable[[int, int], Path],
) -> None:
    """AC-075, the inclusive boundary (guardrail G-5).

    A 600x600 square source (r_src 1.000) into a 30x15 grid (r_tgt 2.000): the
    ratios differ by exactly 2.000x, the retained fraction is exactly 0.500, and
    the request is **accepted** — a 30x15 grid is produced. An implementation
    that compared a float quotient against 0.5 with a strict ``>`` fails here,
    which is the entire reason this criterion exists.
    """
    image.validate_aspect_ratio(600, 600, 30, 15)

    grid = _convert(silhouette(600, 600), 30, 15)
    assert _shape(grid) == (15, {30})


def test_aspect_guard_refuses_a_ratio_difference_above_two_fold(
    silhouette: Callable[[int, int], Path],
) -> None:
    """AC-076: 600x600 into 30x14 (r_tgt 2.143) retains 0.467 and is refused,
    and no grid is produced.

    Guardrail G-4's half of EC-007 is asserted with it: the refusal reaches the
    caller before the picture's pixels are decoded, observed by pointing the
    guard at a file whose header is fine and whose body is not. A conversion
    that got as far as decoding would raise ``UnreadableImage`` instead.
    """
    with pytest.raises(ImageNeedsManualCrop):
        image.validate_aspect_ratio(600, 600, 30, 14)

    source = silhouette(600, 600)
    with pytest.raises(ImageNeedsManualCrop):
        _convert(source, 30, 14)


def test_aspect_guard_refusal_message_suggests_a_manual_crop() -> None:
    """AC-077: the message the user reads says to crop the picture themselves
    before retrying, and names both shapes so they know what to crop it to.

    The percentage it quotes is **floored**, and the case that forces it is a
    request refused just past the boundary: 401x200 into 20x20 retains 0.4988,
    which rounds to 50 — and keeping exactly 50% is the *accepted* boundary
    (G-5, AC-075). A user refused at "50% of the picture" would reasonably
    conclude the tool contradicts its own rule, so the figure is floored to 49.
    """
    with pytest.raises(ImageNeedsManualCrop) as excinfo:
        image.validate_aspect_ratio(600, 600, 30, 14)

    message = str(excinfo.value)
    assert "Crop the picture yourself" in message
    assert "600x600" in message and "30x14" in message
    assert "46% of the picture" in message  # 8400/18000 = 0.4667

    with pytest.raises(ImageNeedsManualCrop) as excinfo:
        image.validate_aspect_ratio(401, 200, 20, 20)

    assert "49% of the picture" in str(excinfo.value)
    # The accepted neighbour it must not be confused with: one pixel narrower
    # retains exactly a half and raises nothing at all.
    image.validate_aspect_ratio(400, 200, 20, 20)


def test_aspect_guard_threshold_is_symmetric_in_source_and_target() -> None:
    """AC-078: a 980x563 landscape source (r_src 1.741) into a 12x30 portrait
    grid (r_tgt 0.400) retains 0.230 and is refused with the same error — the
    threshold does not care which of the two is the wider."""
    with pytest.raises(ImageNeedsManualCrop):
        image.validate_aspect_ratio(980, 563, 12, 30)

    # The mirror image of the same pairing, refused just as flatly.
    with pytest.raises(ImageNeedsManualCrop):
        image.validate_aspect_ratio(563, 980, 30, 12)


def test_aspect_guard_accepts_a_well_matched_portrait_source(
    silhouette: Callable[[int, int], Path],
) -> None:
    """AC-079: a 563x980 portrait silhouette (r_src 0.574) into a 15x30 grid
    (r_tgt 0.500) retains 0.870 — the increment's worked example — so the
    request is accepted and a 15x30 grid is produced."""
    image.validate_aspect_ratio(563, 980, 15, 30)

    assert _shape(_convert(silhouette(563, 980), 15, 30)) == (30, {15})


def test_fit_image_refuses_a_ratio_mismatch_beyond_twice() -> None:
    """ADR-0022/R3's named check, as the rule states it: an uploaded image is
    fitted by a centred crop, and a request whose grid and source aspect ratios
    differ by more than 2x is refused rather than cropped.

    Both halves, on one pairing: 60x20 (3:1) into a 20x20 grid would keep a
    third of the picture, so it is refused; the same source into a 30x10 grid
    (3:1) matches exactly and converts. The refusal is not "image mode is
    fragile", it is "this grid shape and this picture do not go together".
    """
    with pytest.raises(ImageNeedsManualCrop):
        image.validate_aspect_ratio(60, 20, 20, 20)

    assert _shape(_convert(WIDE, 30, 10)) == (10, {30})


# --------------------------------------------------------------------------
# AC-086..AC-091 (FR-022) — TestTrimToInk_* : the ink-box trim, measured
# against the real corpus committed under ``pictures/``
#
# These five criteria are the only place in the test tree that reads that
# corpus, and deliberately so. Every other image test runs against a fixture
# built to isolate one behaviour; FR-022 is a claim about *photographs and
# silhouettes people actually uploaded*, and a synthetic margin proves nothing
# about it — the whole reason the requirement is best-effort rather than an
# invariant is that real pictures do not cooperate. The numbers below were
# re-measured on this tree; where one disagrees with the criterion, the test
# says so in its docstring rather than adopting the measurement silently.
# --------------------------------------------------------------------------

#: The 25 pictures FR-022's criteria are stated over (CARD-030's corpus check:
#: exactly 25 committed files, all four named fixtures present).
PICTURES = Path(__file__).resolve().parent.parent / "pictures"

#: The grid every FR-022 criterion is measured at. Seed 1 is in the criteria
#: too and is recorded here for completeness only — image mode never draws from
#: the RNG, so the conversion is the same at every seed (pinned by
#: ``test_the_conversion_never_draws_from_the_run_rng``).
TRIM_EXTENT = (20, 20)

#: FR-022's near-white comparator (AC-089): a threshold that counts JPEG
#: ringing and off-white paper as ink and so trims almost nothing. Written as a
#: literal rather than derived from ``INK_THRESHOLD``, because the point of the
#: criterion is *where* the shipped threshold sits relative to another one.
NEAR_WHITE_THRESHOLD = 245


def _corpus() -> list[Path]:
    """The committed corpus, sorted, with its size asserted by the caller."""
    return sorted(path for path in PICTURES.iterdir() if path.is_file())


def _blank_edges(grid: list[list[bool]]) -> dict[str, int]:
    """How many all-empty lines each of the four edges carries.

    Written from FR-022's own words ("an all-empty row or column at some edge")
    rather than by asking anything in ``nonogram`` — the requirement is about
    the finished grid, and a helper that reused the trim's own arithmetic could
    only ever agree with it.
    """
    height, width = len(grid), len(grid[0])
    rows = [any(row) for row in grid]
    columns = [any(row[column] for row in grid) for column in range(width)]

    def leading(flags: list[bool]) -> int:
        count = 0
        while count < len(flags) and not flags[count]:
            count += 1
        return count

    return {
        "top": leading(rows),
        "bottom": leading(rows[::-1]),
        "left": leading(columns),
        "right": leading(columns[::-1]),
    }


def _deepest_blank_edge(grid: list[list[bool]]) -> int:
    return max(_blank_edges(grid).values())


def _untrimmed_grid(source: Path) -> list[list[bool]]:
    """The conversion FR-022 replaced: aspect crop, resize, dither, no trim.

    ``binarize`` is the pipeline from the aspect crop onward and does not trim,
    so handing it the whole decoded picture reproduces exactly what ``generate``
    did before CARD-030 — the "before trimming" half of AC-086 and AC-087,
    without a second copy of the resize and the dither to drift from the real
    one.
    """
    with image.load_greyscale(source) as greyscale:
        return image.to_grid(image.binarize(greyscale, *TRIM_EXTENT))


def _trimmed_grid(source: Path, threshold: int) -> list[list[bool]]:
    """The same conversion with the ink box of ``threshold`` trimmed off first."""
    with image.load_greyscale(source) as greyscale:
        box = image.ink_bounding_box(greyscale, threshold)
        return image.to_grid(image.binarize(greyscale.crop(box), *TRIM_EXTENT))


def test_the_corpus_the_trim_criteria_are_stated_over_is_the_one_on_disk() -> None:
    """AC-086/AC-089's premise, so neither can pass by the corpus shrinking.

    A "property" test in this repository asserts its own case count (CLAUDE.md);
    these are acceptance criteria rather than properties, but they quote counts
    out of 25 and would silently weaken if a picture were deleted, so the same
    rule is applied to them here, once, rather than in each.
    """
    corpus = _corpus()

    assert len(corpus) == 25, [path.name for path in corpus]
    for named in ("img_2.png", "img_3.png", "dear1.jpg", "wolf1.jpeg"):
        assert (PICTURES / named).is_file(), named


def test_trim_to_ink_fixes_17_of_the_19_corpus_violations() -> None:
    """AC-086 verbatim, on the criterion's own numbers.

    Given the 25 committed pictures each fitted to a 20x20 grid: 19 carry more
    than one all-empty row or column at some edge before trimming. Trimming to
    the ink box (ink < 128) first, 17 of those 19 satisfy the
    at-most-one-blank-line-per-edge rule and exactly 2 do not, so 23 of 25 hold
    overall. All four figures re-measured on this tree and reproduced exactly.

    The two survivors are named rather than counted, because AC-088 and AC-091
    pin them individually: a change that fixed either must amend those criteria,
    and a change that broke a third one must fail here rather than shift a
    tolerance. Nothing newly violates the rule *because* of the trim, which is
    asserted separately — a transform that fixed 17 and broke 3 would satisfy a
    count of "2 violations" on a differently composed 2.
    """
    corpus = _corpus()
    before = {path.name: _deepest_blank_edge(_untrimmed_grid(path)) for path in corpus}
    after = {
        path.name: _deepest_blank_edge(_trimmed_grid(path, image.INK_THRESHOLD))
        for path in corpus
    }

    violated_before = {name for name, depth in before.items() if depth > 1}
    violated_after = {name for name, depth in after.items() if depth > 1}

    assert len(corpus) == 25
    assert len(violated_before) == 19, sorted(violated_before)
    assert len(violated_before - violated_after) == 17
    assert len(violated_before & violated_after) == 2
    assert violated_after == {"dear1.jpg", "wolf1.jpeg"}
    assert violated_after - violated_before == set()
    assert len(corpus) - len(violated_after) == 23


def test_trim_to_ink_reduces_the_worst_case_border_to_at_most_one_line() -> None:
    """AC-087 verbatim, on the criterion's own numbers.

    ``img_2.png`` is the corpus's worst pre-trim case at 6 blank lines deep, and
    ``img_3.png`` ties it at 6; trimmed to the ink box first, each grid has at
    most one blank row or column at every edge. Both re-measured and reproduced.

    One figure in the criterion's ``given`` does **not** reproduce and is
    recorded here rather than quietly dropped: it says "300 of 400 cells spent
    on border". Measured, ``img_2.png``'s untrimmed edges are top 6, bottom 5,
    left 2, right 2, so the blank frame is 400 - 9*16 = **256** cells; the grid
    holds **297** empty cells in total, which is the nearest reading to 300 and
    is not a border count (it includes the paper inside the subject). Neither
    number is 300. The claim the criterion *tests* — 6 deep before, at most 1
    after — is exact; the parenthetical is a description of the ``given``
    rather than part of the ``then``, so it is reported here and not asserted.
    """
    for name in ("img_2.png", "img_3.png"):
        before = _blank_edges(_untrimmed_grid(PICTURES / name))
        after = _blank_edges(_trimmed_grid(PICTURES / name, image.INK_THRESHOLD))

        assert max(before.values()) == 6, (name, before)
        assert max(after.values()) <= 1, (name, after)

    # And it is the *worst* case, not merely a bad one — otherwise "6" is a
    # number about one picture rather than about the corpus.
    assert (
        max(_deepest_blank_edge(_untrimmed_grid(path)) for path in _corpus()) == 6
    )


def test_trim_to_ink_accepts_the_residual_blank_lines_on_dear1_jpg() -> None:
    """AC-088 verbatim: an accepted residual, not a defect.

    ``dear1.jpg`` trimmed at ink < 128 still shows 2 blank lines at one edge —
    measured on this tree: 2 at the right edge, 0 at the other three, down from
    4 before the trim. FR-022 is best-effort by explicit decision, and this is
    one of the two places it falls short.

    Asserted as an equality rather than as ``>= 2``: if a later change fixes
    this picture, the right move is to amend the criterion, not to let a laxer
    assertion pass silently over an improvement nobody recorded.
    """
    before = _blank_edges(_untrimmed_grid(PICTURES / "dear1.jpg"))
    after = _blank_edges(_trimmed_grid(PICTURES / "dear1.jpg", image.INK_THRESHOLD))

    assert max(before.values()) == 4, before
    assert max(after.values()) == 2, after
    assert sorted(after.values()) == [0, 0, 0, 2], after


def test_trim_to_ink_accepts_the_residual_blank_lines_on_wolf1_jpeg() -> None:
    """AC-091 verbatim: the corpus's worst accepted residual.

    ``wolf1.jpeg`` trimmed at ink < 128 still shows 3 blank lines at one edge —
    measured: 3 at the left, 1 at the right, 0 top and bottom. It measures 3
    deep *before* the trim as well, so the trim neither helps nor harms it, and
    that is precisely why FR-022 is a best-effort transform rather than an
    invariant: no threshold in the swept range reaches this picture. The blank
    margin here survives the resize and the dither, not the crop.
    """
    before = _blank_edges(_untrimmed_grid(PICTURES / "wolf1.jpeg"))
    after = _blank_edges(_trimmed_grid(PICTURES / "wolf1.jpeg", image.INK_THRESHOLD))

    assert max(before.values()) == 3, before
    assert max(after.values()) == 3, after
    assert before == after, (before, after)

    # The worst *remaining* case in the corpus, so "3" is a bound and not an
    # anecdote.
    assert (
        max(
            _deepest_blank_edge(_trimmed_grid(path, image.INK_THRESHOLD))
            for path in _corpus()
        )
        == 3
    )


def test_trim_to_ink_mid_grey_threshold_outperforms_the_near_white_threshold() -> None:
    """AC-089 verbatim: why 128 and not "anything not pure white".

    The same 25 pictures at the same 20x20 grid, trimmed at ink < 245: 6 of the
    25 violate the at-most-one-blank-line-per-edge rule, against 2 at ink < 128.
    Both counts re-measured on this tree and reproduced exactly. Near-white
    counts JPEG ringing and off-white backgrounds as ink, so it finds a bounding
    box that is very nearly the whole file and trims almost nothing.

    This is the evidence the threshold was chosen rather than assumed, so it is
    stated as a comparison of two measurements and not as "128 is good".
    """
    corpus = _corpus()
    mid_grey = [
        path
        for path in corpus
        if _deepest_blank_edge(_trimmed_grid(path, image.INK_THRESHOLD)) > 1
    ]
    near_white = [
        path
        for path in corpus
        if _deepest_blank_edge(_trimmed_grid(path, NEAR_WHITE_THRESHOLD)) > 1
    ]

    assert len(corpus) == 25
    assert len(near_white) == 6, [path.name for path in near_white]
    assert len(mid_grey) == 2, [path.name for path in mid_grey]
    assert image.INK_THRESHOLD == 128


def test_the_shipped_conversion_applies_the_trim_the_criteria_measure() -> None:
    """FR-022 on ``image.generate`` itself — the one thing the criteria miss.

    AC-086..AC-091 above are stated over the trim *transform* and are measured
    through ``_untrimmed_grid``/``_trimmed_grid``, which reassemble the pipeline
    in the test body; and every conversion fixture in this file is a deliberate
    trim no-op (``bands.png``'s ink box is its whole sheet). So nothing else here
    observes the shipped entry point cropping, and an implementation that
    computed the ink box, judged the request against it, and then converted the
    *untrimmed* picture would satisfy every criterion on the card. That mutation
    was run and it left the whole suite green; these assertions are what now fail
    on it.

    ``img_2.png`` is the corpus's worst case (AC-087), so the trimmed and
    untrimmed conversions are far apart — 6 blank lines deep at one edge without
    the trim, at most 1 with it. The equality against ``_trimmed_grid`` is the
    other half: it ties the AC helpers to the shipped pipeline, so the two
    cannot drift apart again without a failure here.
    """
    source = PICTURES / "img_2.png"
    shipped = _convert(source, *TRIM_EXTENT)
    untrimmed = _untrimmed_grid(source)

    assert shipped == _trimmed_grid(source, image.INK_THRESHOLD)
    assert shipped != untrimmed
    assert _deepest_blank_edge(shipped) <= 1
    assert _deepest_blank_edge(untrimmed) == 6


def test_a_near_degenerate_ink_box_drives_the_guard_and_the_resize(
    tmp_path: Path,
) -> None:
    """The small end of the ink box, which no corpus picture reaches.

    The trim has no floor: a sheet whose only ink is a speck is trimmed to that
    speck, and the speck is then what both FR-021's guard and the resize see.
    Two outcomes follow, and both are intended rather than accidents nobody
    looked at — CARD-030's failure matrix declares them:

    * A **2x2 speck on a 400x400 sheet** trims to a square box, which fits every
      square grid, so the resize upsamples 4 ink pixels to a wholly filled grid.
      The picture the user handed over really is 4 black pixels on white; a
      filled grid is the honest rendering of it at 20x20, not a defect.
    * A **1px rule across a 400x400 sheet** trims to a 400x1 box, which FR-021
      refuses for every grid in 10..30 — retaining 0% is exactly what its rule is
      for. Before CARD-030 this file converted, because the *sheet* was square;
      that change of outcome is the guard doing what the ADR revision asked.
    """
    speck = tmp_path / "speck.png"
    sheet = Image.new("L", (400, 400), 255)
    sheet.paste(0, (100, 100, 102, 102))
    sheet.save(speck)

    with image.load_greyscale(speck) as greyscale:
        assert image.ink_bounding_box(greyscale) == (100, 100, 102, 102)
    assert all(all(row) for row in _convert(speck, 20, 20))

    rule = tmp_path / "rule.png"
    sheet = Image.new("L", (400, 400), 255)
    sheet.paste(0, (0, 200, 400, 201))
    sheet.save(rule)

    with image.load_greyscale(rule) as greyscale:
        assert image.ink_bounding_box(greyscale) == (0, 200, 400, 201)
    with pytest.raises(ImageNeedsManualCrop, match="400x1"):
        _convert(rule, 20, 20)


def test_a_picture_with_no_ink_at_all_is_trimmed_by_nothing(tmp_path: Path) -> None:
    """The degenerate end of the trim, which the criteria do not reach.

    A blank sheet has no ink bounding box. Returning an empty box would make the
    crop, and then the resize, undefined; returning the whole extent says the
    honest thing — there is nothing to trim to — and a blank sheet goes on
    converting to a blank grid. The mid-grey field is the case that matters
    most, because 128 is *not* ink by FR-022's own definition, so a flat 128
    picture is one this rule must leave entirely alone.
    """
    for value in (128, 200, 255):
        path = _flat(value, tmp_path, f"blank-{value}.png")
        with image.load_greyscale(path) as greyscale:
            assert image.ink_bounding_box(greyscale) == (0, 0, 64, 64), value

    assert not any(
        any(row) for row in image.generate(_flat(255, tmp_path), 20, 20, _rng())
    )


def test_an_ink_threshold_outside_the_greyscale_range_is_a_caller_bug() -> None:
    """The same reasoning ``_checked_extents`` applies to a zero-side grid: a
    threshold is not user input, so an impossible one is a wiring error rather
    than a domain outcome, and gets ``ValueError`` rather than a
    ``NonogramError``.

    Matched on **this module's own message**, not merely on ``ValueError``: with
    the upper bound loosened to 257 the argument falls through to Pillow, whose
    "wrong number of lut entries" is also a ``ValueError``, so a bare
    ``pytest.raises(ValueError)`` passes while the guard here is broken (verified
    — that mutant survived). The match is what makes the module the enforcer the
    docstring above says it is.
    """
    with image.load_greyscale(BANDS) as greyscale:
        for bad in (-1, 257, 1000):
            with pytest.raises(ValueError, match=r"greyscale value in 0\.\.256"):
                image.ink_bounding_box(greyscale, bad)

        # The two ends of the legal range are legal: nothing is ink at 0, and
        # everything is ink at 256.
        assert image.ink_bounding_box(greyscale, 0) == (0, 0, 32, 32)
        assert image.ink_bounding_box(greyscale, 256) == (0, 0, 32, 32)


def test_a_refused_request_now_pays_for_a_decode_and_nothing_more(
    tmp_path: Path,
) -> None:
    """The cost ADR-0022's 2026-09-01 revision accepted, pinned as a cost.

    Before CARD-030 the guard read the file header and refused without decoding,
    so a truncated PNG asked for a grid it did not fit came back with the aspect
    error rather than the decode error. The ink box is not derivable from a
    header, so that path is gone: **every** image request now decodes first, and
    a file that cannot be decoded reports that, whatever grid was asked for.

    This is a behaviour change, not a regression, and it is asserted rather than
    left to be discovered: the ordering EC-007 actually promises — refused
    before any *cropping* — is the property, and it is proved separately in
    ``tests/property/test_image_fit.py`` by instrumenting the three functions
    that crop.
    """
    whole = tmp_path / "whole.png"
    Image.new("L", (600, 600), 0).save(whole)
    truncated = tmp_path / "truncated.png"
    truncated.write_bytes(whole.read_bytes()[: -len(whole.read_bytes()) // 3])

    with pytest.raises(UnreadableImage):
        _convert(truncated, 30, 15)  # fits (exactly 2x)

    # Used to be ``ImageNeedsManualCrop``, refused from the header alone.
    with pytest.raises(UnreadableImage):
        _convert(truncated, 30, 14)  # does not fit — and still never says so


def test_the_repo_fixtures_carry_no_orientation_metadata_at_all() -> None:
    """The premise every fixture-based assertion in this file rests on.

    None of the five repo fixtures has an EXIF block, so nothing below can be an
    artefact of orientation handling: the extent the loader produces is the
    stored one. Orientation itself is covered by the parametrised test below and
    by ``test_exif_orientation_is_applied_before_the_crop``.
    """
    for source in (BANDS, LANDSCAPE, PORTRAIT, WIDE, TALL):
        with Image.open(source) as opened:
            assert "exif" not in opened.info
            stored = opened.size
        with image.load_greyscale(source) as loaded:
            assert loaded.size == stored


@pytest.mark.parametrize("orientation", [1, 2, 3, 4, 5, 6, 7, 8, 9])
def test_the_decode_honours_exif_orientation(
    tmp_path: Path, orientation: int
) -> None:
    """Failure-matrix row 13, over every value of the tag rather than one.

    One stored 60x40 raster is written eight times with each defined EXIF
    orientation, and once with a value outside the defined range. The decode
    must exchange the axes for exactly ``{5, 6, 7, 8}`` — the quarter-turn four
    — and leave them alone for ``1..4`` (the identity, the two mirrors and the
    half turn, none of which changes the extent) and for the out-of-range ``9``.

    CARD-030 retired ``probe_extent``, and with it the whole class of bug this
    test was originally written against: no extent is read from a header any
    more, and the guard and the crop are handed the same one — the ink box
    derived from the decoded raster — so they cannot disagree about the shape
    being fitted. What survives is the claim that still has teeth — a phone
    photo stored on its side is measured, trimmed and cropped along the axis the
    user actually sees — and it is asserted on the decode itself rather than on
    a header parse that no longer happens.
    """
    stored = Image.new("L", (60, 40), 255)
    stored.paste(0, (23, 4, 33, 16))
    exif = stored.getexif()
    exif[0x0112] = orientation
    oriented = tmp_path / f"phone-{orientation}.jpg"
    stored.save(oriented, format="JPEG", quality=100, exif=exif)

    quarter_turn = orientation in {5, 6, 7, 8}
    with image.load_greyscale(oriented) as loaded:
        assert loaded.size == ((40, 60) if quarter_turn else (60, 40))


def _jpeg_with_a_raw_exif_block(path: Path, block: bytes) -> Path:
    """A 60x40 JPEG carrying ``block`` verbatim as its APP1 segment.

    Written by hand rather than through Pillow's ``exif=`` argument, because the
    point is a block Pillow would never *write*: the segment's declared length
    is correct, so the file is a well-formed JPEG and decodes normally, and only
    the EXIF payload inside it is nonsense.
    """
    plain = Image.new("L", (60, 40), 255)
    plain.paste(0, (10, 10, 30, 30))
    buffer = io.BytesIO()
    plain.save(buffer, format="JPEG", quality=100)
    data = buffer.getvalue()

    segment = b"\xff\xe1" + struct.pack(">H", len(block) + 2) + block
    path.write_bytes(data[:2] + segment + data[2:])
    return path


def test_a_corrupt_exif_block_is_not_an_unreadable_picture(
    tmp_path: Path,
) -> None:
    """Regression, kept after the parser that caused it was retired.

    ``Image.Exif().load`` on a spliced APP1 segment raises ``SyntaxError: not a
    TIFF file`` for a bad magic and ``struct.error: unpack requires a buffer of
    4 bytes`` for a block cut off inside the TIFF header. Neither is an
    ``OSError``, a ``ValueError`` or a ``NonogramError``, so both once escaped
    ``probe_extent``, ``generate`` and ``cli.main``'s only handler and reached
    the user as a stack trace — on a file that ``load_greyscale`` reads
    perfectly, because ``exif_transpose`` tolerates a corrupt block.

    CARD-030 deleted ``probe_extent`` along with its hand-rolled header parse,
    so the defect is now structurally impossible rather than handled. The test
    stays because the *claim* is about the user's file, not about one function:
    a picture with a corrupt EXIF block converts, and no third-party exception
    escapes. If a future card reintroduces header parsing anywhere in this
    pipeline, this is what catches it a second time.
    """
    # Both measured against Pillow 12.3.0 in this venv, on the exact bytes
    # below: a block whose magic is wrong, and one cut off inside the eight-byte
    # TIFF header itself. (A *complete* header pointing at a missing IFD does
    # not raise — Pillow warns and yields no tags — so it is not a case here.)
    corruptions = {
        "bad-magic.jpg": b"\xff\xff\xff\xff\x00\x00\x00\x08",  # SyntaxError
        "truncated-header.jpg": b"MM\x00\x2a\x00",  # struct.error
    }
    for name, header in corruptions.items():
        path = _jpeg_with_a_raw_exif_block(
            tmp_path / name, b"Exif\x00\x00" + header
        )

        with image.load_greyscale(path) as loaded:
            assert loaded.size == (60, 40), name
        assert _shape(image.generate(path, 20, 20, _rng())) == (20, {20}), name


def _png_with_a_trailing_exif_chunk(
    path: Path, width: int, height: int, orientation: int
) -> Path:
    """A PNG whose ``eXIf`` chunk sits *after* ``IDAT``, where ``Image.open``
    does not reach it.

    Legal PNG — the chunk may appear either side of ``IDAT`` — and the one
    construction on which the retired ``probe_extent`` and ``load_greyscale``
    used to disagree: the header parse never saw the orientation,
    ``exif_transpose`` did. Kept as the regression witness for the fail-open
    hole that disagreement opened.
    """
    buffer = io.BytesIO()
    Image.new("L", (width, height), 0).save(buffer, format="PNG")
    data = buffer.getvalue()

    tags = Image.Exif()
    tags[0x0112] = orientation
    payload = tags.tobytes()
    if payload.startswith(b"Exif\x00\x00"):
        payload = payload[len(b"Exif\x00\x00") :]
    chunk = (
        struct.pack(">I", len(payload))
        + b"eXIf"
        + payload
        + struct.pack(">I", zlib.crc32(b"eXIf" + payload) & 0xFFFFFFFF)
    )
    end = data.rindex(b"\x00\x00\x00\x00IEND")
    path.write_bytes(data[:end] + chunk + data[end:])
    return path


def test_the_guard_judges_the_extent_the_crop_will_actually_use(
    tmp_path: Path,
) -> None:
    """CON-012 on the two inputs that once made the guard fail open.

    A 563x980 PNG carrying ``eXIf`` orientation 6 after ``IDAT`` is stored
    portrait and displayed landscape: the retired header probe reported
    (563, 980) while ``load_greyscale`` produces (980, 563). Measured on this
    tree. Judging the probed extent, a 15x30 grid was **accepted** while the
    crop retained 0.287 of the displayed picture — the guard failing open on
    exactly the thing FR-021 exists to prevent. CARD-026 patched that with a
    second check; CARD-030 removes the disagreement instead, because there is
    now only one extent in the pipeline and it is the decoded one.

    The **false refusal** that patch left behind goes with it, and that is the
    part worth asserting rather than merely noting: a 30x15 grid retains 0.870
    of the displayed picture and used to be refused anyway, because the cheap
    probe refused it before the decode that would have corrected the shape. It
    now converts.

    The second construction reaches the same disagreement by a different
    mechanism, which is why this tested extents and not formats: an
    orientation-tagged TIFF carries no ``info["exif"]`` at all, and Pillow's
    TIFF reader applies the orientation to ``size`` at open before
    ``exif_transpose`` applies it a second time. Stored 60x40 + orientation 6
    decodes to 60x40 (measured, Pillow 12.3.0). Flat 128 is *not* ink, so its
    ink box is the whole sheet — a picture with no ink is trimmed by nothing —
    and 60x40 against a 10x30 grid retains 0.222 and is refused.
    """
    source = _png_with_a_trailing_exif_chunk(
        tmp_path / "trailing-exif.png", 563, 980, 6
    )

    with image.load_greyscale(source) as loaded:
        assert loaded.size == (980, 563)

    with pytest.raises(ImageNeedsManualCrop):
        _convert(source, 15, 30)

    # Was refused by the probe before the decode could correct the shape.
    assert _shape(_convert(source, 30, 15)) == (15, {30})
    assert _shape(_convert(source, 20, 20)) == (20, {20})

    tiff = tmp_path / "orientation.tiff"
    Image.new("L", (60, 40), 128).save(tiff, tiffinfo={0x0112: 6})

    with image.load_greyscale(tiff) as rotated:
        assert rotated.size == (60, 40)
        assert image.ink_bounding_box(rotated) == (0, 0, 60, 40)

    with pytest.raises(ImageNeedsManualCrop):
        _convert(tiff, 10, 30)


# --------------------------------------------------------------------------
# Wiring: the dispatch row, the argument list, the orchestrator route
# --------------------------------------------------------------------------


def test_for_mode_returns_the_image_source() -> None:
    assert sourcing.for_mode(sourcing.IMAGE) is image.generate


def test_image_is_advertised_alongside_random_and_library() -> None:
    assert sourcing.IMAGE == "image"
    assert sourcing.MODES == ("random", "library", "image")


def test_for_mode_dispatches_to_a_usable_image_source() -> None:
    """The dispatch seam end to end: look the mode up, then source a grid with
    the mode's own argument list."""
    source = sourcing.for_mode("image")
    grid = source(LANDSCAPE, 20, 20, _rng())

    assert _shape(grid) == (20, {20})
    assert grid == image.generate(LANDSCAPE, 20, 20, _rng())


def test_the_orchestrator_assembles_the_image_argument_list() -> None:
    """The path and extent go to the source in the mode's order, and the RNG is
    appended by the call site for every mode alike.

    The extent is a *pair*, directly after the mode's own leading argument
    (ADR-0022/R1). A rectangle, so a call site that passed one number twice
    would fail here rather than pass by symmetry."""
    request = orchestrator.GenerationRequest(
        mode="image", image=WIDE, width=14, height=22, density=99, library_key="moon"
    )

    assert orchestrator._source_arguments(request) == (WIDE, 14, 22)


def test_the_orchestrator_still_assembles_the_other_argument_lists() -> None:
    """The image row must not have changed what the first two modes are called
    with — the branch that used to be an implicit fallback is now explicit."""
    common = {
        "width": 14,
        "height": 22,
        "density": 35,
        "library_key": "moon",
        "image": WIDE,
    }

    assert orchestrator._source_arguments(
        orchestrator.GenerationRequest(mode="random", **common)
    ) == (14, 22, 35)
    assert orchestrator._source_arguments(
        orchestrator.GenerationRequest(mode="library", **common)
    ) == ("moon", 14, 22)


def test_a_mode_with_no_argument_list_is_a_loud_wiring_error() -> None:
    """CARD-008's review follow-up, closed.

    The fallback used to be "anything that is not library is random", on the
    reasoning that ``sourcing.for_mode`` has already rejected an unknown mode —
    true only of a mode that is not *registered*. Registering ``image`` without
    a branch here would have called ``image.generate(width, height, density, rng)``
    and
    bound a file path to an integer. The ``else`` now raises instead, so the
    next mode added to the dispatch table fails here, immediately and by name.
    """
    with pytest.raises(ValueError) as excinfo:
        orchestrator._source_arguments(
            orchestrator.GenerationRequest(mode="webcam", width=20, height=20, density=30)
        )

    assert "no source argument list" in str(excinfo.value)
    assert "webcam" in str(excinfo.value)


def test_every_registered_mode_has_an_argument_list() -> None:
    """The guard generalised: no mode can be in the dispatch table without one,
    which is the pairing the follow-up was about."""
    for mode in sourcing.MODES:
        arguments = orchestrator._source_arguments(
            orchestrator.GenerationRequest(
                mode=mode,
                width=20,
                height=25,
                density=30,
                library_key="cat",
                image=WIDE,
            )
        )
        # Three arguments in every mode now: the mode's own leading value plus
        # the (width, height) pair — random's density takes the third slot, the
        # other two modes' extent fills the last two (ADR-0022/R1).
        assert len(arguments) == 3
        assert None not in arguments
        extent = arguments[:2] if mode == sourcing.RANDOM else arguments[-2:]
        assert tuple(extent) == (20, 25)


def test_an_image_run_goes_through_the_existing_pipeline() -> None:
    """FR-003 end to end: source -> clues -> uniqueness -> scored -> ready, on
    a real file, with nothing about the downstream pipeline changed."""
    request = orchestrator.GenerationRequest(
        mode="image", image=LANDSCAPE, width=20, height=20, seed=1
    )
    puzzle = orchestrator.generate(request)

    assert puzzle.ready_for_export is True
    assert puzzle.solution_count == 1
    assert puzzle.mode == "image"
    assert puzzle.grid is not None
    assert _shape(puzzle.grid) == (20, {20})
    assert puzzle.difficulty_score is not None


def test_an_image_run_is_reproducible() -> None:
    request = orchestrator.GenerationRequest(
        mode="image", image=BANDS, width=24, height=24, seed=5
    )

    assert orchestrator.generate(request).grid == orchestrator.generate(request).grid


def test_an_image_run_ignores_the_seed_entirely() -> None:
    """A consequence of the conversion being deterministic, worth pinning at
    the pipeline level too: ``--seed`` does not change an image puzzle, which
    is why the failure message for a non-unique conversion does not offer it as
    a lever."""
    grids = [
        orchestrator.generate(
            orchestrator.GenerationRequest(
                mode="image", image=BANDS, width=24, height=24, seed=seed
            )
        ).grid
        for seed in (1, 2, 12345)
    ]

    assert grids[0] == grids[1] == grids[2]


# --------------------------------------------------------------------------
# G-4 — image mode is not wired into POL-001's regenerate loop
# --------------------------------------------------------------------------


class _CountingSource:
    """A grid source that reports how many candidates were asked of it.

    The scripted-source style of ``tests/test_orchestrator.py``: the loop's
    behaviour is observed through the *real* clue derivation and the *real*
    solver, and only the grid is scripted. Faking the uniqueness verdict would
    test the mock (guardrail G-3).
    """

    def __init__(self, grid: list[list[bool]]) -> None:
        self.grid = grid
        self.candidates_requested = 0

    def __call__(self, *arguments: object) -> list[list[bool]]:
        self.candidates_requested += 1
        return [row[:] for row in self.grid]


def _install_source(
    monkeypatch: pytest.MonkeyPatch, source: Callable[..., object]
) -> None:
    monkeypatch.setattr(orchestrator.sourcing, "for_mode", lambda mode: source)


#: A 10x10 grid whose clues have more than one solution — two isolated cells on
#: a diagonal can be swapped for the other diagonal without changing any clue.
_AMBIGUOUS = [[False] * 10 for _ in range(10)]
_AMBIGUOUS[2][2] = _AMBIGUOUS[3][3] = True


def test_a_non_unique_conversion_is_never_re_sourced(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """G-4, stated the way the guardrail is: the source is asked for exactly
    **one** candidate.

    CARD-016 changed what happens *after* that one candidate is rejected — the
    run no longer ends there, it nudges the converted grid (POL-002, see
    ``tests/test_nudge.py``) — but not this: a nudge edits the grid already in
    hand, so however a run turns out, the picture is decoded once. The
    regenerate counter left at zero is the same fact read off the aggregate.
    """
    source = _CountingSource(_AMBIGUOUS)
    _install_source(monkeypatch, source)
    request = orchestrator.GenerationRequest(
        mode="image", image=WIDE, width=10, height=10, seed=1
    )

    puzzle = orchestrator.generate(request)

    assert source.candidates_requested == 1
    assert puzzle.regenerate.attempts == 0
    assert puzzle.nudge.attempts == 1


def test_a_non_unique_conversion_leaves_both_retry_counters_at_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The same fact read off the aggregate rather than off the source.

    The puzzle is captured by patching the class's constructor path — the
    counters belong to COMP-002 (INV-003, guardrail G-6) and image mode must
    leave *these two* untouched, which is what makes CARD-016's nudge counter a
    genuinely new one rather than a reuse of POL-001's. One aggregate per run,
    nudges included: a nudge replaces the candidate, never the puzzle.
    """
    source = _CountingSource(_AMBIGUOUS)
    _install_source(monkeypatch, source)
    built: list[orchestrator.Puzzle] = []
    real_puzzle = orchestrator.Puzzle

    def capturing(*args: object, **kwargs: object) -> orchestrator.Puzzle:
        puzzle = real_puzzle(*args, **kwargs)  # type: ignore[arg-type]
        built.append(puzzle)
        return puzzle

    monkeypatch.setattr(orchestrator, "Puzzle", capturing)

    orchestrator.generate(
        orchestrator.GenerationRequest(
            mode="image", image=WIDE, width=10, height=10, seed=1
        )
    )

    assert len(built) == 1
    assert built[0].regenerate.attempts == 0
    assert built[0].resample.attempts == 0


def test_a_successful_image_run_also_spends_no_retry_attempt() -> None:
    """The happy path of the same rule, on a real file: image mode never enters
    either loop, so a run that works reports zero attempts rather than one."""
    puzzle = orchestrator.generate(
        orchestrator.GenerationRequest(
            mode="image", image=LANDSCAPE, width=20, height=20, seed=1
        )
    )

    assert puzzle.regenerate.attempts == 0
    assert puzzle.resample.attempts == 0


def test_a_real_image_that_converts_ambiguously_reports_it(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The same failure without a scripted source anywhere: ``landscape.png`` at
    22x22 genuinely converts to a grid whose clues have more than one solution,
    and stays that way through all five of CARD-016's nudges.

    A pinned case, in the sense ``tests/test_orchestrator.py`` uses the word —
    if the dithering, the solver or the nudge heuristic changes such that this
    size becomes unique, re-pin it by re-running the 10..25 sweep this comment
    names rather than deleting the test. (It was ``bands.png`` at 10x10 until
    CARD-016: that conversion is now repaired by two nudges, which is
    ``tests/test_nudge.py``'s real-image recovery case. It was ``wide.png`` at
    22x22 until CARD-026 made a 3:1 source into a square grid an FR-021
    refusal; the re-run sweep put ``landscape.png`` at the same size.)
    """
    exit_code = cli.main(
        ["generate", "--mode", "image", "--image", str(LANDSCAPE), "--size", "22"]
    )

    assert exit_code == cli.ExitCode.GENERATION_FAILED
    assert "uniquely-solvable" in capsys.readouterr().err


def test_a_missed_difficulty_tier_also_fails_without_resampling() -> None:
    """POL-004 cannot help a fixed source either — resampling would convert the
    same picture again — so the tier miss ends the run with its own message."""
    request = orchestrator.GenerationRequest(
        mode="image", image=LANDSCAPE, width=20, height=20, seed=1, difficulty="hard"
    )

    with pytest.raises(GenerationAbandoned) as excinfo:
        orchestrator.generate(request)

    message = str(excinfo.value)
    assert "Hard band" in message
    assert "fixed" in message


def test_the_regenerate_loop_still_fires_for_the_modes_it_owns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """G-4's other half: exempting image mode must not have exempted anything
    else. A random-mode run with a scripted non-unique first candidate still
    regenerates, which is what ``TestRegenerate_FiresOnUniquenessFailure``
    asserts in full over in ``tests/test_orchestrator.py``.
    """
    unique = [[False] * 10 for _ in range(10)]
    unique[0] = [True] * 10

    class _TwoShot:
        def __init__(self) -> None:
            self.candidates_requested = 0

        def __call__(self, *arguments: object) -> list[list[bool]]:
            self.candidates_requested += 1
            grid = _AMBIGUOUS if self.candidates_requested == 1 else unique
            return [row[:] for row in grid]

    source = _TwoShot()
    _install_source(monkeypatch, source)

    puzzle = orchestrator.generate(
        orchestrator.GenerationRequest(
            mode="random", width=10, height=10, density=30, seed=1
        )
    )

    assert source.candidates_requested == 2
    assert puzzle.regenerate.attempts == 2


# --------------------------------------------------------------------------
# G-3 / G-6 — what this card deliberately did not build
# --------------------------------------------------------------------------


def test_the_image_module_exposes_no_retry_machinery() -> None:
    """G-3 and G-6 as an API-surface pin, narrowed by CARD-016 to the half that
    is still this module's business.

    The *loop* (FR-013) and its *count* (FR-014) belong to COMP-002; CARD-016
    landed the nudge **mechanism** here on purpose, and the pin that keeps the
    split honest is now in ``tests/test_nudge.py``
    (``test_the_image_module_counts_nothing_itself``). What remains true here
    is the part that never moved: no retry loop, no counter, no bound.
    """
    assert not hasattr(image, "RetryCounter")
    assert not any(name.startswith("MAX_") for name in vars(image))


def test_the_other_two_sources_are_untouched() -> None:
    """G-1, as a behaviour rather than as a diff: the additive third mode must
    leave random and library mode producing exactly what they did."""
    assert _shape(random_grid.generate(20, 20, 30, random.Random(4))) == (20, {20})
    assert random_grid.density_of(
        random_grid.generate(20, 20, 30, random.Random(4))
    ) == 30.0
    assert _shape(library.generate("cat", 15, 15, random.Random(4))) == (15, {15})


# --------------------------------------------------------------------------
# COMP-001 — the flags (parsing only, ADR-0010) and the exit code
# --------------------------------------------------------------------------


def _generate_parser_action(dest: str) -> argparse.Action:
    """The ``generate`` subparser's action for ``dest`` (see
    ``tests/test_sourcing_library.py`` for the same test-only introspection)."""
    subparsers = next(
        action
        for action in cli.build_parser()._actions
        if isinstance(action, argparse._SubParsersAction)
    )
    return next(
        action
        for action in subparsers.choices["generate"]._actions
        if action.dest == dest
    )


def test_the_parser_offers_the_image_mode() -> None:
    """``--mode``'s choices are mirrored by hand in ``cli.py``; a mode
    registered in ``sourcing`` but not offered here is unreachable."""
    assert tuple(_generate_parser_action("mode").choices or ()) == sourcing.MODES
    assert (
        cli.build_parser().parse_args(["generate", "--mode", "image"]).mode == "image"
    )


def test_the_image_flag_carries_no_argparse_validation() -> None:
    """ADR-0010 / guardrail G-5, structurally: ``type=Path`` is a syntactic
    conversion (the same one ``--out`` gets) and there is no ``choices``, no
    ``FileType`` and no existence check — so an unreadable path reaches the
    domain and comes back as AC-008's error rather than as a usage error."""
    action = _generate_parser_action("image")

    assert action.type is Path
    assert action.choices is None
    assert not isinstance(action.type, argparse.FileType)


def test_a_nonexistent_image_parses_fine_and_is_rejected_inward(
    tmp_path: Path,
) -> None:
    """The same rule from the outside: argparse accepts the path happily."""
    missing = tmp_path / "absent.png"
    parsed = cli.build_parser().parse_args(
        ["generate", "--mode", "image", "--image", str(missing)]
    )

    assert parsed.image == missing


def test_the_cli_parses_the_image_flags_into_the_request(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """argv -> GenerationRequest, the adapter's whole job for this card."""
    seen: list[orchestrator.GenerationRequest] = []

    def fake_generate(request: orchestrator.GenerationRequest) -> orchestrator.Puzzle:
        seen.append(request)
        return orchestrator.Puzzle(request=request, seed=request.seed or 0)

    monkeypatch.setattr(orchestrator, "generate", fake_generate)

    exit_code = cli.main(
        [
            "generate",
            "--mode",
            "image",
            "--image",
            str(WIDE),
            "--size",
            "25",
            "--seed",
            "3",
        ]
    )

    assert exit_code == cli.ExitCode.OK
    assert seen[0].mode == "image"
    assert seen[0].image == WIDE
    assert (seen[0].width, seen[0].height) == (25, 25)


def test_an_unreadable_image_is_reported_as_an_input_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC-008's CLI half, and CARD-007's review follow-up closed.

    ``main`` used to wrap the whole handler in ``except OSError -> exit 5``, on
    the premise that an ``OSError`` could only come from writing an export.
    Reading the user's ``--image`` broke that premise, so a missing picture
    would have been reported as "export rejected". It is an *input* error:
    exit code 3, the same group as a bad size or an unknown library key.
    """
    exit_code = cli.main(
        [
            "generate",
            "--mode",
            "image",
            "--image",
            str(tmp_path / "absent.png"),
            "--size",
            "20",
        ]
    )

    assert exit_code == cli.ExitCode.INVALID_INPUT
    assert exit_code != cli.ExitCode.EXPORT_REJECTED
    captured = capsys.readouterr()
    assert captured.err.startswith(f"{cli.PROG}: error: ")
    assert "cannot read image" in captured.err
    assert "Traceback" not in captured.err


def test_the_unreadable_image_error_maps_to_the_input_group() -> None:
    """The table entry itself, without going through argv."""
    assert (
        cli.exit_code_for(UnreadableImage("x")) == cli.ExitCode.INVALID_INPUT
    )


def test_a_non_export_oserror_is_no_longer_swallowed_as_an_export_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The narrowing, asserted rather than described.

    The ``except OSError`` clause now wraps only ``export_puzzle``. An
    ``OSError`` raised anywhere else in a run is therefore *not* silently
    relabelled "export rejected" — it stays unhandled, which is the honest
    outcome for a failure the adapter has no story for. (A read failure on
    ``--image`` never gets that far: it is a domain error, see above.)
    """
    def exploding(request: orchestrator.GenerationRequest) -> orchestrator.Puzzle:
        raise OSError("something that is not an export")

    monkeypatch.setattr(orchestrator, "generate", exploding)

    with pytest.raises(OSError, match="not an export"):
        cli.main(["generate", "--size", "20", "--density", "30"])


def test_an_export_oserror_is_still_reported_cleanly(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The other side of the narrowing: what CARD-007 added the clause for
    still works. Kept here next to the test above so the pair reads as one
    decision — ``tests/test_export_json.py`` covers the original repro."""
    def exploding(puzzle: orchestrator.Puzzle) -> tuple[Path, ...]:
        raise PermissionError("cannot write there")

    monkeypatch.setattr(orchestrator, "export_puzzle", exploding)

    exit_code = cli.main(
        [
            "generate",
            "--size",
            "10",
            "--density",
            "40",
            "--seed",
            "3",
            "--export",
            "json",
            "--out",
            str(tmp_path),
        ]
    )

    assert exit_code == cli.ExitCode.EXPORT_REJECTED
    assert "cannot write there" in capsys.readouterr().err


def test_an_image_run_exports_like_any_other(tmp_path: Path) -> None:
    """FR-011 over the new mode: nothing downstream of sourcing knows or cares
    where the grid came from."""
    exit_code = cli.main(
        [
            "generate",
            "--mode",
            "image",
            "--image",
            str(LANDSCAPE),
            "--size",
            "20",
            "--export",
            "json",
            "--out",
            str(tmp_path),
        ]
    )

    assert exit_code == cli.ExitCode.OK
    assert [path.suffix for path in sorted(tmp_path.iterdir())] == [".json"]
