"""CARD-087 — the synthetic fixtures are what their tests say they are.

The defect this guards against is not a bug in any one test; it is a *drift*
between an image and the prose that describes it. Six tests failed for months
because ``bands.png`` was documented as carrying "a flat 128 grey" middle third
and held only pure black and white — an assertion no implementation could
satisfy, against a file nobody had checked.

The images are generated now (``tests/fixtures/make_fixtures.py``), so the
structure has a single readable source. These tests are the other half: they
check the committed bytes still match that source, and that the structural
properties other test files state in prose are actually true of the files.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from tests.fixtures import make_fixtures

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _grey(name: str) -> np.ndarray:
    return np.asarray(Image.open(FIXTURES / name).convert("L"))


def test_the_committed_fixtures_are_what_the_generator_produces(
    tmp_path: Path,
) -> None:
    """AC-2: the generator is the source of truth, not a historical note.

    A generator that has drifted from the files it supposedly produced is worse
    than no generator — it documents a structure the tests are not running
    against, which is precisely the failure this card fixed.
    """
    make_fixtures.write_all(tmp_path)

    for name in make_fixtures.FIXTURES:
        assert (tmp_path / name).read_bytes() == (FIXTURES / name).read_bytes(), (
            f"{name} differs from what make_fixtures.py produces — regenerate "
            f"it (python tests/fixtures/make_fixtures.py) or fix the generator"
        )


def test_the_bands_fixture_carries_a_real_mid_grey_band() -> None:
    """AC-1: the property the dithering test cannot be written without.

    A 50% threshold turns a flat mid-grey into one solid block; error diffusion
    turns it into a texture whose density carries the level. Without a genuine
    mid-tone in the file, the test that separates them is vacuous — it was, and
    it failed.
    """
    greys = set(_grey("bands.png").flatten().tolist())

    assert make_fixtures.MID_GREY in greys, (
        f"bands.png holds {sorted(greys)}; the dithering test needs a flat "
        f"{make_fixtures.MID_GREY} band to be about anything"
    )
    assert greys == {0, make_fixtures.MID_GREY, 255}


def test_the_bands_fixture_has_a_square_ink_box() -> None:
    """AC-3: stated in prose by tests/property/test_grid_dimensions.py.

    That file reasons about ``bands.png`` on the basis that its ink bounding
    box is square, and ``sourcing/image.py`` trims to the ink box before
    cropping — so if the ground rule ever went, the sheet would trim to a
    non-square and a dozen derived expectations would shift at once, none of
    them obviously connected to the fixture.
    """
    ink = _grey("bands.png") < 128
    rows = np.flatnonzero(ink.any(axis=1))
    columns = np.flatnonzero(ink.any(axis=0))

    height = rows[-1] - rows[0] + 1
    width = columns[-1] - columns[0] + 1
    assert (width, height) == (32, 32)


@pytest.mark.parametrize(
    "name, size", [("landscape.png", (60, 40)), ("portrait.png", (40, 60))]
)
def test_the_crop_fixtures_have_outer_bands_and_a_centred_core(
    name: str, size: tuple[int, int]
) -> None:
    """AC-1: the shape that separates crop from stretch from letterbox.

    Three facts, each load-bearing for a different assertion in
    ``test_sourcing_image.py``: ink at both ends of the long axis (so a stretch
    would put it in the grid's outer rows/columns), a gap of white between the
    bands and the core (so letterboxing would show ink outside the centre), and
    ink at the centre (so the crop has something to keep).
    """
    image = Image.open(FIXTURES / name)
    assert image.size == size

    ink = _grey(name) < 128
    long_axis_is_width = size[0] >= size[1]
    line = ink.any(axis=0) if long_axis_is_width else ink.any(axis=1)
    length = len(line)
    sixth = length // 6

    assert line[:sixth].all(), "no ink band at the near end of the long axis"
    assert line[-sixth:].all(), "no ink band at the far end of the long axis"
    assert not line[sixth + 1], "the band must end, or there is no white to crop to"
    assert line[length // 2], "no core at the centre for the crop to keep"


@pytest.mark.parametrize("name", ["landscape.png", "portrait.png"])
def test_the_crop_fixtures_ink_box_spans_the_whole_sheet(name: str) -> None:
    """The trim runs before the crop (FR-022), so a fixture whose ink sits in
    the middle is cropped to that middle and stops having the proportions its
    test reasons about. The outer bands are what prevent it."""
    ink = _grey(name) < 128
    rows = np.flatnonzero(ink.any(axis=1))
    columns = np.flatnonzero(ink.any(axis=0))
    height, width = ink.shape

    assert (rows[0], rows[-1]) == (0, height - 1)
    assert (columns[0], columns[-1]) == (0, width - 1)


def test_the_generator_does_not_touch_the_photographs() -> None:
    """G-3: the real pictures are pinned by measured properties elsewhere.

    ``owl1.png`` carries ``tests/test_nudge.py``'s two-nudge recovery case and
    ``duck1.png`` now carries the ambiguity pin; regenerating or re-encoding
    either would move numbers in tests that never mention this file.
    """
    generated = set(make_fixtures.FIXTURES)
    photographs = {
        path.name
        for path in FIXTURES.iterdir()
        if path.suffix in {".png", ".jpg", ".jpeg"} and path.stat().st_size > 5000
    }

    assert generated & photographs == set(), (
        f"the generator would overwrite real photographs: "
        f"{sorted(generated & photographs)}"
    )
