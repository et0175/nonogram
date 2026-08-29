"""COMP-003's image source (FR-003, CARD-015) — conversion, policy and wiring.

Acceptance criteria, by the card's test names:

    AC-007  TestConvertImage_ProducesDitheredGrid        -> test_convert_image_produces_a_dithered_grid*
    AC-008  TestConvertImage_RejectsUnreadableFile       -> test_convert_image_rejects_an_unreadable_file*
    AC-009  TestConvertImage_ProducesExactTargetDimensions
                                                         -> test_convert_image_produces_exact_target_dimensions*

Fixtures live in ``tests/fixtures/`` and are deliberately tiny (under 100 bytes
each). Their content is chosen so that the assertions below can *distinguish*
implementations rather than merely observe one:

``bands.png``    32x32, three horizontal bands — black, mid-grey (128), white.
                 The mid band is the dithering witness: a plain 50% threshold
                 renders a flat 128 region as one solid colour, error diffusion
                 renders it as a mixed, roughly half-filled texture.
``wide.png``     60x20, vertical thirds — black, white with a small black core,
                 black. Centre-cropping keeps only the middle third, so the
                 outer edges of the grid come out **empty**; a stretch would put
                 the black thirds in the grid's first and last columns. One
                 assertion therefore tells the two policies apart.
``tall.png``     the transpose of ``wide.png``, so the crop is pinned on both
                 axes rather than only on the one that happened to be tested.
``corrupt.png``  a real PNG signature followed by garbage — a file that claims
                 to be a picture and is not.

Images that are exotic rather than representative (a flat mid-grey field, an
RGBA image with a transparent hole) are built in ``tmp_path`` instead: they
exist to pin one behaviour each, and a repo fixture should be something a
reader of the test tree can open and recognise.
"""

from __future__ import annotations

import argparse
import random
from collections.abc import Callable
from pathlib import Path

import pytest
from PIL import Image, UnidentifiedImageError

from nonogram import cli, orchestrator, sourcing
from nonogram.errors import (
    GenerationAbandoned,
    NonogramError,
    SizeOutOfRange,
    UnreadableImage,
)
from nonogram.sourcing import image, library, random_grid

FIXTURES = Path(__file__).parent / "fixtures"

BANDS = FIXTURES / "bands.png"
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


# --------------------------------------------------------------------------
# The fixtures themselves — guard the guard (see the module docstring)
# --------------------------------------------------------------------------


def test_the_fixture_images_are_present_and_shaped_as_documented() -> None:
    """Every assertion below reasons from these dimensions; a fixture silently
    regenerated at another size would weaken the tests without failing them."""
    with Image.open(BANDS) as bands:
        assert bands.size == (32, 32)
    with Image.open(WIDE) as wide:
        assert wide.size == (60, 20)
    with Image.open(TALL) as tall:
        assert tall.size == (20, 60)
    assert CORRUPT.read_bytes().startswith(b"\x89PNG")


def test_the_fixture_images_stay_tiny() -> None:
    """They live in the repo (card step 5), so their size is part of the deal."""
    for fixture in (BANDS, WIDE, TALL, CORRUPT):
        assert fixture.stat().st_size < 1024


# --------------------------------------------------------------------------
# AC-007 (happy) — TestConvertImage_ProducesDitheredGrid
# --------------------------------------------------------------------------


def test_convert_image_produces_a_dithered_grid() -> None:
    """AC-007 verbatim: a valid PNG and a target of 25x25 give a 25x25
    black/white grid, produced by resizing and dithering."""
    grid = image.generate(BANDS, 25, _rng())

    assert _shape(grid) == (25, {25})
    assert all(cell is True or cell is False for row in grid for cell in row)
    # The black band is ink and the white band is paper: the polarity, on a
    # grid whose top and bottom are unambiguous whatever the dither does.
    assert all(grid[0]) and all(grid[1])
    assert not any(grid[-1]) and not any(grid[-2])


def test_convert_image_produces_a_dithered_grid_of_plain_python_bools() -> None:
    """ADR-0012's boundary type, not a NumPy array wearing its clothes: the
    conversion runs through NumPy internally and must not leak it."""
    grid = image.generate(BANDS, 25, _rng())

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
    grid = image.generate(BANDS, 24, _rng())
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
    grid = image.generate(_flat(value, tmp_path), 30, _rng())

    expected = 1.0 - value / 255.0
    assert abs(_filled_fraction(grid) - expected) < 0.1


def test_black_and_white_fields_convert_without_a_dither_artefact(
    tmp_path: Path,
) -> None:
    """The two ends of the scale are not a matter of taste: a wholly black
    image is a wholly filled grid, a wholly white one a wholly empty grid.
    Error diffusion must not sprinkle either with the other."""
    assert all(
        all(row) for row in image.generate(_flat(0, tmp_path, "black.png"), 20, _rng())
    )
    assert not any(
        any(row)
        for row in image.generate(_flat(255, tmp_path, "white.png"), 20, _rng())
    )


def test_transparent_areas_are_paper_and_not_ink(tmp_path: Path) -> None:
    """A transparent PNG's alpha is flattened onto white before greyscaling.

    Without the flattening, ``convert("L")`` reads the colour *under* the
    transparent pixels — which for the usual "transparent PNG with black
    underneath" is a solid black rectangle where the user sees nothing.
    """
    path = tmp_path / "hole.png"
    transparent = Image.new("RGBA", (40, 40), (0, 0, 0, 0))
    transparent.paste((0, 0, 0, 255), (0, 0, 40, 10))
    transparent.save(path)

    grid = image.generate(path, 20, _rng())

    assert all(grid[0])  # the opaque black stripe is ink
    assert not any(any(row) for row in grid[8:])  # the transparent field is paper


def test_the_conversion_is_reproducible_for_the_same_file_and_size() -> None:
    grid = image.generate(WIDE, 20, _rng())

    assert image.generate(WIDE, 20, _rng()) == grid


def test_the_conversion_never_draws_from_the_run_rng() -> None:
    """G-4's premise, made observable: the conversion of a given file at a
    given size is fully determined, which is *why* image mode cannot be handed
    to POL-001's regenerate loop — a retry would return this same grid.

    Asserted twice over: two different seeds give the same grid, and the RNG
    handed in comes back with its state untouched.
    """
    unused = random.Random(1)
    state = unused.getstate()

    assert image.generate(BANDS, 22, unused) == image.generate(
        BANDS, 22, random.Random(999)
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
        image.generate(missing, 20, _rng())

    assert "cannot read image" in str(excinfo.value)
    assert str(missing) in str(excinfo.value)


def test_convert_image_rejects_an_unreadable_file_that_is_corrupt() -> None:
    """AC-008's second half: a file that claims to be a PNG and is not."""
    with pytest.raises(UnreadableImage) as excinfo:
        image.generate(CORRUPT, 20, _rng())

    assert "cannot read image" in str(excinfo.value)


def test_convert_image_rejects_a_path_that_is_a_directory(tmp_path: Path) -> None:
    """Not in the criterion's words, but the same failure from the user's side
    — a ``--image`` that names something unreadable — and a different OSError
    underneath, which is the point: the guard is on the outcome, not on a list
    of errno values."""
    with pytest.raises(UnreadableImage):
        image.generate(tmp_path, 20, _rng())


def test_convert_image_rejects_a_missing_image_argument() -> None:
    """``--mode image`` with no ``--image``: the same domain error, with a
    message that names the forgotten flag rather than a path. The shape
    ``library.template_for`` uses for a missing ``--library-key``."""
    with pytest.raises(UnreadableImage) as excinfo:
        image.generate(None, 20, _rng())

    assert "--image" in str(excinfo.value)


@pytest.mark.parametrize("unreadable", [CORRUPT, FIXTURES / "absent.png"])
def test_pillows_own_exception_never_reaches_the_caller(unreadable: Path) -> None:
    """The structural half of AC-008. ``UnidentifiedImageError`` is itself an
    ``OSError``, so "a domain error was raised" is not enough on its own —
    what is asserted is that the escaping exception is a ``NonogramError`` and
    is *not* an ``OSError`` of any kind, with Pillow's exception demoted to a
    chained ``__cause__`` for the traceback."""
    with pytest.raises(UnreadableImage) as excinfo:
        image.generate(unreadable, 20, _rng())

    error = excinfo.value
    assert isinstance(error, NonogramError)
    assert not isinstance(error, OSError)
    assert not isinstance(error, UnidentifiedImageError)
    assert isinstance(error.__cause__, Exception)


def test_an_unreadable_image_produces_no_grid_and_no_puzzle(tmp_path: Path) -> None:
    """AC-008's "and no grid is produced", at the pipeline level: the run ends
    at sourcing, so no aggregate comes back and nothing is written."""
    request = orchestrator.GenerationRequest(
        mode="image", image=tmp_path / "absent.png", size=20, seed=1, out=tmp_path
    )

    with pytest.raises(UnreadableImage):
        orchestrator.generate(request)

    assert list(tmp_path.iterdir()) == []


def test_the_size_rule_is_checked_before_the_file_is_opened() -> None:
    """The contract the other two sources keep: reject an invalid request
    before doing its work. An out-of-range size is reported as such even when
    the path is also unusable, so the user fixes the first thing that is
    wrong rather than the second."""
    with pytest.raises(SizeOutOfRange):
        image.generate(FIXTURES / "absent.png", 60, _rng())


@pytest.mark.parametrize("size", [9, 51, None])
def test_the_supported_size_range_is_the_same_as_every_other_mode(
    size: int | None,
) -> None:
    """Shared from ``random_grid`` rather than restated (the rule is about the
    puzzle, not about the source), so this pins that it really is shared."""
    with pytest.raises(SizeOutOfRange):
        image.generate(BANDS, size, _rng())

    assert random_grid.MIN_SIZE == 10 and random_grid.MAX_SIZE == 50


# --------------------------------------------------------------------------
# AC-009 (boundary) — TestConvertImage_ProducesExactTargetDimensions
# --------------------------------------------------------------------------


@pytest.mark.parametrize("source", [WIDE, TALL, BANDS])
@pytest.mark.parametrize("size", [10, 17, 25, 50])
def test_convert_image_produces_exact_target_dimensions(
    source: Path, size: int
) -> None:
    """AC-009 verbatim: whatever the source's aspect ratio, the grid has
    exactly the requested dimensions — including the 3:1 and 1:3 fixtures at
    both ends of the supported size range."""
    assert _shape(image.generate(source, size, _rng())) == (size, {size})


def test_the_aspect_ratio_policy_is_centre_crop_and_not_stretch() -> None:
    """The documented policy, asserted where the two answers differ.

    ``wide.png`` is black | white-with-a-black-core | black in vertical thirds.
    Centre-cropping converts the middle third alone, so the grid's first and
    last columns are empty and its centre holds the core. A stretch would map
    the outer black thirds onto the grid's outer columns instead — so this one
    test tells the implemented policy from the rejected one.
    """
    grid = image.generate(WIDE, 20, _rng())

    outer_columns = [row[0] for row in grid] + [row[-1] for row in grid]
    assert not any(outer_columns)
    assert any(grid[10][6:14])


def test_the_aspect_ratio_policy_holds_on_the_other_axis() -> None:
    """The same claim for a portrait source: the crop is not an accident of
    which axis the wide fixture happened to be long on."""
    grid = image.generate(TALL, 20, _rng())

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
    displayed = Image.new("L", (60, 20), 255)
    displayed.paste(0, (23, 2, 33, 8))  # off-centre: neither axis is symmetric

    stored = displayed.transpose(Image.Transpose.ROTATE_90)
    exif = stored.getexif()
    exif[0x0112] = 6  # "rotate 90 CW to display correctly"
    oriented = tmp_path / "phone.jpg"
    stored.save(oriented, format="JPEG", quality=100, exif=exif)

    reference_source = tmp_path / "displayed.png"
    displayed.save(reference_source)

    reference = image.generate(reference_source, 20, _rng())
    honoured = image.generate(oriented, 20, _rng())

    assert honoured == reference
    assert _ink(honoured)  # the marker did land somewhere, not just "matched by both being blank"


@pytest.mark.parametrize("source", [WIDE, TALL])
def test_the_outer_thirds_of_the_source_do_not_reach_the_grid_at_all(
    source: Path,
) -> None:
    """The third policy, excluded: letterboxing.

    Padding the short axis to square keeps the *whole* source, so ``wide.png``'s
    two black outer thirds would land somewhere in the grid — squeezed into a
    middle band with blank rows above and below it. Cropping discards them
    outright. So the strongest statement of the policy is that the only ink in
    the grid comes from the black core at the centre of the middle third: every
    filled cell is inside the central block, and there are some.
    """
    grid = image.generate(source, 20, _rng())
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
def test_the_crop_box_is_the_largest_centred_square(
    width: int, height: int, expected: tuple[int, int, int, int]
) -> None:
    box = image.square_crop_box(width, height)

    assert box == expected
    left, upper, right, lower = box
    assert right - left == lower - upper == min(width, height)


@pytest.mark.parametrize(("width", "height"), [(0, 10), (10, 0), (0, 0)])
def test_an_image_with_no_pixels_is_an_input_error(width: int, height: int) -> None:
    """A degenerate source is the user's file being unusable, not an
    arithmetic accident several frames later."""
    with pytest.raises(UnreadableImage):
        image.square_crop_box(width, height)


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
    grid = source(WIDE, 20, _rng())

    assert _shape(grid) == (20, {20})
    assert grid == image.generate(WIDE, 20, _rng())


def test_the_orchestrator_assembles_the_image_argument_list() -> None:
    """The path and size go to the source in the mode's order, and the RNG is
    appended by the call site for every mode alike."""
    request = orchestrator.GenerationRequest(
        mode="image", image=WIDE, size=14, density=99, library_key="moon"
    )

    assert orchestrator._source_arguments(request) == (WIDE, 14)


def test_the_orchestrator_still_assembles_the_other_argument_lists() -> None:
    """The image row must not have changed what the first two modes are called
    with — the branch that used to be an implicit fallback is now explicit."""
    common = {"size": 14, "density": 35, "library_key": "moon", "image": WIDE}

    assert orchestrator._source_arguments(
        orchestrator.GenerationRequest(mode="random", **common)
    ) == (14, 35)
    assert orchestrator._source_arguments(
        orchestrator.GenerationRequest(mode="library", **common)
    ) == ("moon", 14)


def test_a_mode_with_no_argument_list_is_a_loud_wiring_error() -> None:
    """CARD-008's review follow-up, closed.

    The fallback used to be "anything that is not library is random", on the
    reasoning that ``sourcing.for_mode`` has already rejected an unknown mode —
    true only of a mode that is not *registered*. Registering ``image`` without
    a branch here would have called ``image.generate(size, density, rng)`` and
    bound a file path to an integer. The ``else`` now raises instead, so the
    next mode added to the dispatch table fails here, immediately and by name.
    """
    with pytest.raises(ValueError) as excinfo:
        orchestrator._source_arguments(
            orchestrator.GenerationRequest(mode="webcam", size=20, density=30)
        )

    assert "no source argument list" in str(excinfo.value)
    assert "webcam" in str(excinfo.value)


def test_every_registered_mode_has_an_argument_list() -> None:
    """The guard generalised: no mode can be in the dispatch table without one,
    which is the pairing the follow-up was about."""
    for mode in sourcing.MODES:
        arguments = orchestrator._source_arguments(
            orchestrator.GenerationRequest(
                mode=mode, size=20, density=30, library_key="cat", image=WIDE
            )
        )
        assert len(arguments) == 2
        assert None not in arguments


def test_an_image_run_goes_through_the_existing_pipeline() -> None:
    """FR-003 end to end: source -> clues -> uniqueness -> scored -> ready, on
    a real file, with nothing about the downstream pipeline changed."""
    request = orchestrator.GenerationRequest(
        mode="image", image=WIDE, size=20, seed=1
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
        mode="image", image=BANDS, size=24, seed=5
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
                mode="image", image=BANDS, size=24, seed=seed
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
        mode="image", image=WIDE, size=10, seed=1
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
        orchestrator.GenerationRequest(mode="image", image=WIDE, size=10, seed=1)
    )

    assert len(built) == 1
    assert built[0].regenerate.attempts == 0
    assert built[0].resample.attempts == 0


def test_a_successful_image_run_also_spends_no_retry_attempt() -> None:
    """The happy path of the same rule, on a real file: image mode never enters
    either loop, so a run that works reports zero attempts rather than one."""
    puzzle = orchestrator.generate(
        orchestrator.GenerationRequest(mode="image", image=WIDE, size=20, seed=1)
    )

    assert puzzle.regenerate.attempts == 0
    assert puzzle.resample.attempts == 0


def test_a_real_image_that_converts_ambiguously_reports_it(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The same failure without a scripted source anywhere: ``wide.png`` at
    22x22 genuinely converts to a grid whose clues have more than one solution,
    and stays that way through all five of CARD-016's nudges.

    A pinned case, in the sense ``tests/test_orchestrator.py`` uses the word —
    if the dithering, the solver or the nudge heuristic changes such that this
    size becomes unique, re-pin it by re-running the 10..25 sweep this comment
    names rather than deleting the test. (It was ``bands.png`` at 10x10 until
    CARD-016: that conversion is now repaired by two nudges, which is
    ``tests/test_nudge.py``'s real-image recovery case.)
    """
    exit_code = cli.main(
        ["generate", "--mode", "image", "--image", str(WIDE), "--size", "22"]
    )

    assert exit_code == cli.ExitCode.GENERATION_FAILED
    assert "uniquely-solvable" in capsys.readouterr().err


def test_a_missed_difficulty_tier_also_fails_without_resampling() -> None:
    """POL-004 cannot help a fixed source either — resampling would convert the
    same picture again — so the tier miss ends the run with its own message."""
    request = orchestrator.GenerationRequest(
        mode="image", image=WIDE, size=20, seed=1, difficulty="hard"
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
            mode="random", size=10, density=30, seed=1
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
    assert _shape(random_grid.generate(20, 30, random.Random(4))) == (20, {20})
    assert random_grid.density_of(random_grid.generate(20, 30, random.Random(4))) == 30.0
    assert _shape(library.generate("cat", 15, random.Random(4))) == (15, {15})


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
    assert seen[0].size == 25


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
            str(WIDE),
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
