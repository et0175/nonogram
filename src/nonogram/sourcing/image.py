"""COMP-003 / CAP-001 — the uploaded-image source of a grid (FR-003).

The third and last grid origin, and deliberately the same shape of thing as the
first two: a callable registered in the package's mode table that returns one
grid in the ADR-0012 boundary representation (``list[list[bool]]``, row-major,
``True`` for a filled cell) and takes the run's injected ``random.Random``
last (ADR-0015). Everything downstream — clue derivation, the uniqueness check,
export — is reused unchanged.

The pipeline, in one line
-------------------------
``open -> flatten transparency onto white -> greyscale -> crop to square ->
resize to size x size -> Floyd-Steinberg dither -> ink is a filled cell``.

Aspect-ratio policy: **centre-crop, then resize** (AC-009)
----------------------------------------------------------
AC-009 only demands that the output be exactly ``size`` x ``size`` whatever the
source's proportions are; *how* to get there is a choice, and this module makes
one deliberately. A non-square source is centre-cropped to its largest centred
square (:func:`square_crop_box`) and that square is resized to the grid. The
two rejected alternatives, and why:

* **Stretch** (resize the whole image straight to ``size`` x ``size``) keeps
  every pixel but distorts the subject: a circle becomes an ellipse, a face is
  squashed or drawn out. A nonogram's entire payoff is that the solved grid is
  a *recognisable* picture, and at 10..50 cells there is no resolution to spare
  for the viewer to mentally un-stretch it.
* **Letterbox** (pad the short axis to square with white) keeps proportions but
  spends the scarcest resource there is on nothing: a 16:9 photo letterboxed
  into a 25x25 grid burns ~7 of its 25 rows on blank paper, which is both a
  worse picture and a worse puzzle (a wholly empty row is a ``0`` clue and a
  free line for the solver).

Cropping loses the ends of the long axis, which is the honest cost of the
choice and is why it is centred rather than anchored: the subject of a
photograph is near the middle far more often than at an edge. A user who wants
the whole frame crops or pads it themselves before passing it in — that is a
picture-editing decision, and this tool is a puzzle generator.

Why Pillow does the dithering
-----------------------------
``Image.convert("1")`` *is* Floyd-Steinberg error diffusion (it is Pillow's
default dither for the 1-bit target), so ADR-0006's baseline already ships the
algorithm the card asks for; reimplementing the error-diffusion loop by hand
would add a second, slower and less-tested copy of it for no behavioural gain.
NumPy does the arithmetic on the far side of it — the bilevel raster comes back
as an array and is inverted into the boundary type in one vectorised step
rather than pixel by pixel (ADR-0006's division of labour).

Dither before threshold, not instead of it: a plain 50% cut turns a photograph
into two flat blobs, while error diffusion trades grey *level* for filled-cell
*density*, which is what makes a mid-tone region readable at all on a grid this
coarse.

No retry loop lives here (guardrails G-3, G-6)
----------------------------------------------
An uploaded image is fixed: unlike a random draw or a library template's
boundary tie-break, asking this module for "another" grid returns the identical
grid. So image mode is not wired into POL-001's regenerate loop — the
orchestrator fails the run cleanly when the conversion is not uniquely solvable
— and the bounded pixel-nudge recovery (POL-002, FR-013) lands with CARD-016,
in COMP-002, where INV-003's counter already lives. There is no counter, no
loop and no nudge in this file, by design.

Layering (ADR-0007): a capability module. It imports its own package's
``random_grid`` for the shared size rule and ``nonogram.errors``; never the
adapter, the orchestrator or a sibling capability.
"""

from __future__ import annotations

import random
from os import PathLike

import numpy
from PIL import Image, UnidentifiedImageError

from nonogram.errors import UnreadableImage
from nonogram.sourcing import random_grid

__all__ = [
    "RESAMPLING",
    "binarize",
    "generate",
    "load_greyscale",
    "square_crop_box",
    "to_grid",
]

#: The resampling filter the crop is scaled down with. Lanczos over
#: nearest-neighbour for the same reason ``library.render`` computes exact area
#: coverage rather than sampling one source pixel per target cell: at the
#: reduction factors involved here (a 1000px photo into 25 cells) point sampling
#: throws away 99.9% of the pixels and keeps whichever one happened to land
#: under the sample point, so fine detail turns into noise. Pillow scales the
#: filter's support with the reduction, so this averages the whole neighbourhood
#: a cell covers — which is exactly the grey level the dither below needs.
RESAMPLING = Image.Resampling.LANCZOS

#: Pillow's byte value for a black pixel in the bilevel ``"1"`` mode. Black is
#: *ink*, and ink is a filled cell (ADR-0012's ``True``) — the one place this
#: module states which way round the two representations sit.
_BLACK = 0

#: What ``Image.open``/``load`` raises for a file that is not a readable image.
#: ``UnidentifiedImageError`` (a plain unknown/garbage file) is itself an
#: ``OSError`` subclass and is named only for documentation; ``ValueError`` and
#: ``DecompressionBombError`` are not, and cover a malformed-but-recognised
#: header — a truncated PNG, an absurd declared size — which Pillow reports
#: while decoding rather than while opening.
_UNREADABLE = (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError)


def load_greyscale(source: str | PathLike[str]) -> Image.Image:
    """Open ``source`` and return it as a greyscale (``"L"``) image.

    The only function in the module that touches the filesystem, and therefore
    the only one that can fail on the user's input. Every way Pillow has of
    saying "this is not an image I can read" is turned into one domain error
    here (AC-008), so nothing downstream — and in particular nothing the user
    sees — is phrased in Pillow's vocabulary.

    Transparency is flattened onto **white** before the greyscale conversion.
    A bare ``convert("L")`` on an RGBA image ignores the alpha channel and reads
    whatever colour happens to sit under the transparent pixels, which for the
    common "transparent PNG saved with black underneath" is a solid black
    rectangle where the user sees nothing at all. White is the right background
    because this module's output is ink on paper: transparent is paper.

    Args:
        source: Path to the user's image file, as given.

    Returns:
        The image in mode ``"L"``, at its original pixel dimensions. Fully
        decoded — the file handle is not held open past this call.

    Raises:
        UnreadableImage: the path does not exist, is not readable, is not a
            directory entry Pillow can decode, or decodes to nothing usable
            (AC-008). The original exception is chained as ``__cause__`` for a
            traceback, but never for the message the user reads.
    """
    try:
        with Image.open(source) as opened:
            # Pillow is lazy: ``open`` reads the header only, so a truncated or
            # corrupt body raises here, inside the guarded block, rather than
            # later at the caller's first pixel access.
            opened.load()
            return _flattened(opened)
    except _UNREADABLE as error:
        raise UnreadableImage(
            f"cannot read image {str(source)!r}: {error}"
        ) from error


def _flattened(image: Image.Image) -> Image.Image:
    """``image`` in mode ``"L"``, with any transparency composited onto white."""
    has_alpha = image.mode in {"RGBA", "LA", "PA"} or (
        "transparency" in image.info
    )
    if not has_alpha:
        return image.convert("L")
    paper = Image.new("RGBA", image.size, (255, 255, 255, 255))
    return Image.alpha_composite(paper, image.convert("RGBA")).convert("L")


def square_crop_box(width: int, height: int) -> tuple[int, int, int, int]:
    """The largest centred square inside a ``width`` x ``height`` image.

    The aspect-ratio policy, on its own so it can be reasoned about (and
    tested) without an image in the way — see the module docstring for why
    cropping rather than stretching or padding.

    Args:
        width: Source width in pixels.
        height: Source height in pixels.

    Returns:
        A Pillow crop box ``(left, upper, right, lower)`` whose width and height
        are both ``min(width, height)``. An odd leftover pixel goes to the
        *far* side, because integer division floors the near offset; that is a
        half-pixel bias on one axis of a source that is about to be resized to
        at most 50 cells, and pinning it explicitly is worth more than
        pretending it can be avoided.

    Raises:
        UnreadableImage: the image has no pixels on one of its axes. Pillow can
            hold a 0-width image; there is nothing to convert and the user's
            file is the reason, so it is reported as the same input error as an
            undecodable one rather than as an arithmetic accident downstream.
    """
    if width <= 0 or height <= 0:
        raise UnreadableImage(
            f"image has no pixels to convert (its size is {width}x{height})"
        )
    edge = min(width, height)
    left = (width - edge) // 2
    upper = (height - edge) // 2
    return (left, upper, left + edge, upper + edge)


def binarize(greyscale: Image.Image, size: int) -> Image.Image:
    """Crop, resize to ``size`` x ``size`` and Floyd-Steinberg dither.

    Args:
        greyscale: The source in mode ``"L"``, at its original dimensions.
        size: The target square edge length. Assumed validated —
            :func:`generate` validates before calling.

    Returns:
        A ``size`` x ``size`` image in Pillow's bilevel ``"1"`` mode.

    The crop and the resize are one call: ``resize`` takes the source rectangle
    as its ``box`` argument, so the intermediate cropped image is never
    materialised and the resampling filter sees the crop's true pixel grid
    rather than a re-quantised copy of it.
    """
    scaled = greyscale.resize(
        (size, size),
        resample=RESAMPLING,
        box=square_crop_box(*greyscale.size),
    )
    # Pillow's default dither for a 1-bit target *is* Floyd-Steinberg; naming it
    # anyway, because "the default" is not what the card asked for.
    return scaled.convert("1", dither=Image.Dither.FLOYDSTEINBERG)


def to_grid(bilevel: Image.Image) -> list[list[bool]]:
    """Turn a bilevel image into the ADR-0012 boundary representation.

    Ink is a filled cell: a black pixel becomes ``True``. The inversion is one
    vectorised NumPy comparison rather than a per-pixel loop, and comparing
    against :data:`_BLACK` (rather than negating a truth value) reads correctly
    whether Pillow hands the mode-``"1"`` raster back as booleans or as 0/255
    bytes — ``False`` and ``0`` are both the black end in either case.

    Returns:
        A row-major ``list[list[bool]]`` of plain Python ``bool`` — ``tolist``
        converts NumPy's ``bool_`` scalars, so nothing NumPy-typed crosses the
        module boundary (ADR-0012).
    """
    pixels = numpy.asarray(bilevel)
    return (pixels == _BLACK).tolist()


def generate(
    source: str | PathLike[str] | None,
    size: int | None,
    rng: random.Random,
) -> list[list[bool]]:
    """Convert the user's image into one ``size`` x ``size`` solution grid.

    The mode table's entry point for ``image`` (FR-003, AC-007/AC-008/AC-009).
    The argument order is the mode's own — the path first, because it is what
    the mode is *about*, the way ``key`` leads for the library source — and the
    RNG comes last, as it does for every source.

    Args:
        source: Path to the user's image file (``--image``). ``None`` — the
            flag omitted in image mode — is rejected the way library mode
            rejects a missing ``--library-key``: with a message that names the
            forgotten flag, rather than by defaulting to some file.
        size: Square grid edge length; the same supported range as every other
            mode, since it is a rule about the puzzle and not about the source
            (``random_grid.validate_size``, shared rather than restated).
        rng: The run's random source (ADR-0015). Accepted for the mode table's
            uniform calling convention and deliberately **not drawn from**: the
            conversion of a given file at a given size is fully determined, and
            jittering it would make the picture the user handed over come back
            as a different picture per seed. Library mode's threshold draw
            exists to give POL-001 a second chance at unique solvability; image
            mode has no regenerate loop to give one to (see the module
            docstring, guardrail G-4).

    Returns:
        A row-major ``list[list[bool]]`` of ``size`` rows of ``size`` cells,
        ``True`` for filled (ADR-0012) — exactly the requested dimensions
        whatever the source's aspect ratio was (AC-009).

    Raises:
        UnreadableImage: ``source`` is ``None``, missing, unreadable or not a
            decodable image (AC-008). Pillow's own exception never reaches the
            caller.
        SizeOutOfRange: ``size`` is outside the supported range.

    Validation runs before the file is opened, so a request that was invalid
    anyway does not also pay for a decode — the same "reject before you work"
    contract the other two sources keep.
    """
    if source is None:
        raise UnreadableImage(
            "image mode needs an --image PATH pointing at the picture to convert"
        )
    size = random_grid.validate_size(size)
    greyscale = load_greyscale(source)
    return to_grid(binarize(greyscale, size))
