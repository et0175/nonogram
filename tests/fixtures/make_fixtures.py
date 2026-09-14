"""Regenerate the three *synthetic* image fixtures, from their tests' demands.

    python tests/fixtures/make_fixtures.py

Run from the repository root. Writes ``bands.png``, ``landscape.png`` and
``portrait.png`` beside this file, byte-for-byte as committed, and touches
nothing else — the photographic fixtures (``owl1.png``, ``duck1.png`` and the
rest) are real pictures whose measured properties several tests pin, and this
script must never overwrite one (CARD-087 G-3).

Why this file exists
--------------------
These three images were fabricated by hand in ``02a25a2`` (2026-09-10) to fill
in for fixtures that had never been committed, and they were built by reading
the *test names* rather than the assertions. The result passed nothing: six
tests failed for months against images that did not contain what their own
docstrings said they contained — ``bands.png`` was documented as having "a flat
128 grey" middle third and held only pure black and white.

The intent lived exclusively in test docstrings, where no one could check an
image against it. It lives here now. Every structural choice below names the
assertion it serves, so a future change to a fixture is a change to a stated
reason rather than a guess.

The shared rule: an ink bounding box that spans the sheet
--------------------------------------------------------
``sourcing/image.py`` trims to the ink bounding box (FR-022) *before* cropping,
so a fixture whose ink sits in the middle is silently cropped to that middle
and no longer has the proportions its test reasons about. Each image below
therefore carries ink that reaches all four edges — the black head and the
"ground rule" in ``bands.png``, the outer bands in the other two.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent

BLACK, MID_GREY, WHITE = 0, 128, 255


def bands() -> Image.Image:
    """32x32: ink head, a flat mid-grey band, paper, a ground rule.

    - **The mid-grey band is the point of the file.** A 50% threshold renders a
      flat 128 grey as one solid block; Floyd-Steinberg error diffusion renders
      it as a mixed texture whose density carries the level. Only an image that
      actually contains 128 can tell those apart
      (``test_the_mid_tone_band_comes_out_dithered_rather_than_thresholded``
      reads grid rows 9:15 of a 24x24 conversion and requires 0.35..0.65 fill).
    - **Rows 10..21** put that band across the middle three-eighths, which lands
      inside rows 9:15 at 24x24 and inside 7:17 at 25x25.
    - **Rows 0..9 black, 22..29 white** give the polarity assertions their
      unambiguous ends (``test_convert_image_produces_a_dithered_grid``:
      ``grid[0]``/``grid[1]`` filled, ``grid[-3]``/``grid[-4]`` empty at 25x25).
    - **Rows 30..31 black** are the ground rule. Without them the ink box stops
      at row 21 and the sheet is trimmed to a 32x22 — which would both break the
      polarity rows and cost the square ink box that
      ``tests/property/test_grid_dimensions.py`` states in prose and depends on.
    """
    sheet = np.full((32, 32), WHITE, dtype=np.uint8)
    sheet[0:10, :] = BLACK
    sheet[10:22, :] = MID_GREY
    sheet[22:30, :] = WHITE
    sheet[30:32, :] = BLACK
    return Image.fromarray(sheet, mode="L").convert("RGB")


def _outer_bands_with_a_core(width: int, height: int) -> Image.Image:
    """A black sixth at each end of the long axis, and a small centred core.

    This is the one shape that separates all three aspect-ratio policies at
    once, which is why both crop tests use it:

    - a **centred crop** discards the two outer bands entirely, so the grid's
      outer rows/columns are empty and the only ink left is the core;
    - a **stretch** would map the outer bands onto the grid's outer
      rows/columns, so they would not be empty;
    - **letterboxing** would keep the whole source, squeezing the bands into a
      middle strip — so ink would appear outside the central block.

    Hence ``test_the_outer_bands_of_the_source_do_not_reach_the_grid_at_all``
    asserting that *every* filled cell of a 20x20 conversion lies within rows
    and columns 4..15: true only under the crop.

    The core is 12x12 at the centre. At 20x20 the crop is the middle square, so
    the core lands on grid rows/columns 7..12 — inside 4..15 with room to
    spare, and overlapping ``grid[10][6:14]``, which the other crop test reads.
    """
    sheet = np.full((height, width), WHITE, dtype=np.uint8)
    if width >= height:                      # landscape: bands left and right
        sixth = width // 6
        sheet[:, :sixth] = BLACK
        sheet[:, width - sixth:] = BLACK
    else:                                    # portrait: bands top and bottom
        sixth = height // 6
        sheet[:sixth, :] = BLACK
        sheet[height - sixth:, :] = BLACK

    centre_y, centre_x = height // 2, width // 2
    sheet[centre_y - 6:centre_y + 6, centre_x - 6:centre_x + 6] = BLACK
    return Image.fromarray(sheet, mode="L").convert("RGB")


def landscape() -> Image.Image:
    """60x40 — wider than tall, so the crop takes the middle 40x40."""
    return _outer_bands_with_a_core(60, 40)


def portrait() -> Image.Image:
    """40x60 — the same claim on the other axis, so the crop is not an accident
    of which way the landscape fixture happened to be long."""
    return _outer_bands_with_a_core(40, 60)


FIXTURES = {
    "bands.png": bands,
    "landscape.png": landscape,
    "portrait.png": portrait,
}


def write_all(destination: Path = HERE) -> list[Path]:
    written = []
    for name, build in FIXTURES.items():
        path = destination / name
        build().save(path)
        written.append(path)
    return written


if __name__ == "__main__":
    for path in write_all():
        print(f"wrote {path.relative_to(Path.cwd()) if path.is_relative_to(Path.cwd()) else path}")
