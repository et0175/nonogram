"""FR-027's two engineering constraints — the classifier and the threshold cut.

    ADR-0028/R1  PropertyTest_Binarize_ClassifierPureFunctionOfSourceImage
                 -> test_the_classifier_is_a_pure_function_of_the_source_image
    ADR-0026/R1  PropertyTest_Binarize_ThresholdIsInclusiveHalfCoverageOnResizedImage
                 -> test_the_threshold_is_inclusive_half_coverage_on_the_resized_image

ADR-0028/R1, in full: the path choice is a pure function of the decoded source
image against ``MIDTONE_SHARE_THRESHOLD`` — same file, same path, on every load
and every host; no rng, request field or override enters it.

ADR-0026/R1, in full: under the threshold path, for any resized grey value g,
the cell is filled iff ``g <= 127``; the threshold is never applied before the
resize, and never diffuses error.

Both are statements about *every* image rather than about a chosen one, which
is why they are here and not in ``tests/test_sourcing_image.py``, where
AC-124..AC-127 are pinned on hand-built greys and on the owner's corpus.

The corpus, house style (no ``hypothesis`` — it is not in the dependency
baseline): synthetic images built from stdlib ``random.Random`` on fixed
seeds, with the case counts asserted inside each test so the corpus cannot
silently shrink. Silhouettes at varying anti-alias width and gradients at
varying mid-tone share, because those are the two populations ADR-0028 has to
separate, plus the degenerate ends (all black, all white, one pixel).

Where a claim can be re-derived it is re-derived here: the expected mid-tone
share is counted from the image's own pixels by the helper below rather than
by calling :func:`image.midtone_share`, which is the function under test.
"""

from __future__ import annotations

import random

import pytest
from PIL import Image, ImageDraw

from nonogram.sourcing import image

#: Asserted inside the tests: a corpus that stopped being built would leave a
#: vacuous green behind.
_MINIMUM_CASES = 24


def _silhouette(rng: random.Random, blur: int) -> Image.Image:
    """Hard shapes on white, with ``blur`` steps of grey around each edge.

    ``blur`` is the anti-alias width in pixels, drawn as concentric rings of
    intermediate grey. It is the knob that matters: a clean silhouette has
    almost no mid-tones, and a heavily anti-aliased or JPEG-ringed one has
    some, and ADR-0028 has to keep both on the threshold path.
    """
    canvas = Image.new("L", (96, 96), 255)
    draw = ImageDraw.Draw(canvas)
    for _ in range(rng.randint(1, 3)):
        left, top = rng.randint(0, 50), rng.randint(0, 50)
        right, bottom = left + rng.randint(20, 40), top + rng.randint(20, 40)
        for step in range(blur, 0, -1):
            grey = 255 - (255 * (blur - step + 1)) // (blur + 1)
            draw.ellipse((left - step, top - step, right + step, bottom + step), fill=grey)
        draw.ellipse((left, top, right, bottom), fill=0)
    return canvas


def _gradient(rng: random.Random, span: int) -> Image.Image:
    """A ramp covering ``span`` of the 8-bit range, always crossing the band.

    ``low`` is constrained so the ramp reaches from at or below the band's
    floor to at or above its ceiling. That is not a convenience: a ramp that
    sits **entirely** in the highlights has no mid-tones and no ink, and the
    classifier correctly calls it a silhouette — it is simply not a member of
    the population ADR-0028 calls "genuinely greyscale", and putting one in
    this corpus would be mislabelling the fixture rather than finding a defect.
    What such a picture *does* do downstream is a real finding and is pinned in
    ``tests/test_sourcing_image.py``
    (``test_the_threshold_path_turns_an_inkless_picture_into_a_blank_grid``).
    """
    low, high = image.MIDTONE_BAND
    span = max(span, high - low + 2)
    start = rng.randint(max(0, low - 20), low)
    canvas = Image.new("L", (96, 96))
    canvas.putdata(
        [min(255, start + (x * span) // 95) for _ in range(96) for x in range(96)]
    )
    return canvas


def _share_in_band(greyscale: Image.Image) -> float:
    """The mid-tone share, counted from the pixels themselves.

    A second implementation, deliberately: reading it back out of
    :func:`image.midtone_share` would only ever agree with itself.
    """
    low, high = image.MIDTONE_BAND
    pixels = list(greyscale.get_flattened_data())
    inside = sum(1 for value in pixels if low <= value <= high)
    return inside / len(pixels)


def _corpus() -> list[tuple[str, Image.Image]]:
    """Seeded synthetic images, labelled by the population they belong to."""
    cases: list[tuple[str, Image.Image]] = []
    for seed in range(8):
        rng = random.Random(seed)
        for blur in (0, 1, 2):
            cases.append(("silhouette", _silhouette(rng, blur)))
        for span in (140, 200, 255):
            cases.append(("gradient", _gradient(rng, span)))
    cases.append(("degenerate", Image.new("L", (10, 10), 0)))
    cases.append(("degenerate", Image.new("L", (10, 10), 255)))
    cases.append(("degenerate", Image.new("L", (1, 1), 128)))
    return cases


def test_the_classifier_is_a_pure_function_of_the_source_image() -> None:
    """ADR-0028/R1 over the whole corpus.

    Three properties, which together are what "pure function of the source"
    means operationally: the answer matches the band arithmetic re-derived
    from the pixels, it is the same on every call, and it is the same for a
    freshly constructed copy of the same pixels (so nothing is cached against
    an object's identity).
    """
    cases = _corpus()

    for _, picture in cases:
        share = _share_in_band(picture)
        expected = (
            image.DITHER
            if share >= image.MIDTONE_SHARE_THRESHOLD
            else image.THRESHOLD
        )

        assert image.classify_binarisation(picture) == expected
        assert image.classify_binarisation(picture) == expected
        assert image.midtone_share(picture) == pytest.approx(share)

        copy = picture.copy()
        assert image.classify_binarisation(copy) == expected

    assert len(cases) >= _MINIMUM_CASES


def test_the_classifier_separates_the_two_populations_it_exists_for() -> None:
    """The constant is provisional, but the separation is the claim.

    ADR-0028 owes a calibration (CARD-079 records every corpus picture's share
    for the owner), so this does not pin ``MIDTONE_SHARE_THRESHOLD``. What it
    pins is that the *measurement* orders the two populations the right way
    round at all: every synthetic silhouette scores below every synthetic
    gradient. A band or a counting rule that failed to do that would make the
    constant unsettable at any value.
    """
    cases = _corpus()
    silhouettes = [image.midtone_share(p) for kind, p in cases if kind == "silhouette"]
    gradients = [image.midtone_share(p) for kind, p in cases if kind == "gradient"]

    assert silhouettes and gradients
    assert max(silhouettes) < min(gradients)


def test_the_threshold_is_inclusive_half_coverage_on_the_resized_image() -> None:
    """ADR-0026/R1: filled iff the resized grey value is at most 127.

    Stated over every 8-bit value rather than over the three the acceptance
    criteria name, and read through ``binarize`` itself so that the resize
    step is included — the constraint is about the value *after* the resize,
    which is where "ink coverage" is a meaning rather than a metaphor.

    The image is handed in already at the target size, so the LANCZOS step is
    the identity (``tests/test_sourcing_image.py`` guards that premise) and
    the only thing this varies is the value.
    """
    greys = list(range(256))
    strip = Image.new("L", (len(greys), 1))
    strip.putdata(greys)

    row = image.to_grid(
        image.binarize(strip, len(greys), 1, path=image.THRESHOLD)
    )[0]

    assert row == [value <= 127 for value in greys]
    assert row[127] is True and row[128] is False


def test_the_threshold_never_diffuses_error_between_neighbours() -> None:
    """The other half of ADR-0026/R1, and the property that names the path.

    A cell's verdict depends on its own resized value and nothing else, so
    shuffling the cells of a row must shuffle the verdicts identically. Error
    diffusion fails this by construction — that is what it *is* — which is
    what makes it the discriminating test rather than a restatement.
    """
    rng = random.Random(11)
    greys = [rng.randrange(256) for _ in range(64)]

    def binarised(values: list[int]) -> list[bool]:
        strip = Image.new("L", (len(values), 1))
        strip.putdata(values)
        return image.to_grid(
            image.binarize(strip, len(values), 1, path=image.THRESHOLD)
        )[0]

    straight = binarised(greys)
    order = list(range(len(greys)))
    rng.shuffle(order)
    shuffled = binarised([greys[index] for index in order])

    assert shuffled == [straight[index] for index in order]
