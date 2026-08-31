"""COMP-003 / CAP-001 — the uploaded-image source of a grid (FR-003).

The third and last grid origin, and deliberately the same shape of thing as the
first two: a callable registered in the package's mode table that returns one
grid in the ADR-0012 boundary representation (``list[list[bool]]``, row-major,
``True`` for a filled cell) and takes the run's injected ``random.Random``
last (ADR-0015). Everything downstream — clue derivation, the uniqueness check,
export — is reused unchanged.

The pipeline, in one line
-------------------------
``open -> flatten transparency onto white -> greyscale -> crop to the requested
grid's aspect ratio -> resize to width x height -> Floyd-Steinberg dither ->
ink is a filled cell``.

Aspect-ratio policy: **centre-crop to the grid's ratio, then resize**
---------------------------------------------------------------------
The grid drives the picture, not the reverse (ADR-0022). The user asks for a
grid of ``width`` x ``height`` cells; the source is fitted to *that* shape by
taking its largest centred sub-rectangle whose aspect ratio is ``width /
height`` (:func:`fit_crop_box`) and resizing that rectangle to the grid
(AC-059, AC-071..AC-074, FR-020). The square crop this module used to take is
now simply the ``width == height`` case of the same function — the policy below
is generalized, not replaced.

*How* to reach the requested dimensions is a choice, and this module makes one
deliberately. The two rejected alternatives, and why:

* **Stretch** (resize the whole image straight to ``width`` x ``height``) keeps
  every pixel but distorts the subject: a circle becomes an ellipse, a face is
  squashed or drawn out. A nonogram's entire payoff is that the solved grid is
  a *recognisable* picture, and at 10..30 cells there is no resolution to spare
  for the viewer to mentally un-stretch it. ADR-0022/R3 forbids it outright.
* **Letterbox** (pad the short axis with white until the source matches the
  grid's ratio) keeps proportions but spends the scarcest resource there is on
  nothing: a 16:9 picture letterboxed into a 25x25 grid fits into 14 rows
  (``25 * 9 / 16``) and burns the remaining 11 on blank paper — 44% of the
  grid, and the retained fraction the refusal rule below computes for that same
  pairing is 0.563, so cropping keeps more than half the *picture* where
  letterboxing spends nearly half the *puzzle*. Both a worse picture and a
  worse puzzle (a wholly empty
  row is a ``0`` clue and a free line for the solver). The argument only gets
  stronger now that the grid can be rectangular: a user who wants their portrait
  silhouette whole no longer has to pad it into a square, they can ask for a
  portrait grid, so padding would be spending rows to avoid a shape the tool now
  supports directly.

Cropping loses the ends of the long axis, which is the honest cost of the
choice and is why it is centred rather than anchored: the subject of a picture
is near the middle far more often than at an edge.

The refusal rule: never discard more than half the picture (FR-021)
--------------------------------------------------------------------
A centred crop to a target ratio retains exactly
``min(r_src, r_tgt) / max(r_src, r_tgt)`` of the source, where ``r = width /
height`` — the cropped axis is scaled by that factor and the other axis is kept
whole. So "the crop would discard more than half the user's picture" is exactly
"the two ratios differ by more than 2x", and that is what
:func:`validate_aspect_ratio` refuses, with a message telling the user to crop
the picture themselves first (AC-075..AC-079, CON-012, ADR-0022/R3). The
boundary is **inclusive**: a square source into a 30x15 grid retains exactly
half and is accepted. The check is a pure predicate on four integers, decided by
integer cross-multiplication rather than float division, and it runs before the
file's pixels are ever decoded — a refused request pays for a header read and
nothing else.

Scope: silhouettes, not photographs (CON-013)
----------------------------------------------
This module targets high-contrast black-and-white silhouettes. The dither
tuning, the crop policy and the uniqueness/nudge budget are all calibrated for
them. Photographic input is **out of scope** rather than
unsupported-with-a-warning: it will convert, and nothing will complain, but
nothing here is aiming at it and no acceptance criterion covers it.

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

No retry loop lives here (guardrails G-3, G-6; CARD-016 G-2)
------------------------------------------------------------
An uploaded image is fixed: unlike a random draw or a library template's
boundary tie-break, asking this module for "another" grid returns the identical
grid. So image mode is not wired into POL-001's regenerate loop.

CARD-016 splits POL-002's bounded pixel-nudge recovery (FR-013) along exactly
that line, and trace.yml's FR-013 note is the split: the *policy* — when to
nudge, how many times, and what to say when the cap is reached — lives in
COMP-002, where INV-003's counter already is, and the *mechanism* — which cell
to flip — lives here, in the module that owns what the conversion produced.
:func:`nudge` is that mechanism and the whole of this module's part in it. It
takes the attempt number as an argument and keeps none: there is still no
counter, no loop and no bound in this file, by design (guardrail G-2), and
nothing here decides whether a nudged grid is good — the orchestrator re-runs
the real solver on every one of them (CON-005, guardrail G-4).

Layering (ADR-0007): a capability module. It imports its own package's
``random_grid`` for the shared size rule and ``nonogram.errors``; never the
adapter, the orchestrator or a sibling capability.
"""

from __future__ import annotations

import random
from os import PathLike

import numpy
from PIL import Image, ImageOps, UnidentifiedImageError

from nonogram.errors import ImageNeedsManualCrop, UnreadableImage
from nonogram.sourcing import random_grid

__all__ = [
    "RESAMPLING",
    "binarize",
    "fit_crop_box",
    "generate",
    "load_greyscale",
    "nudge",
    "nudge_cells",
    "probe_extent",
    "to_grid",
    "validate_aspect_ratio",
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

    EXIF orientation is applied before anything else touches the pixels
    (``ImageOps.exif_transpose``), so a phone photo is rotated/cropped along
    the axis the user actually sees rather than the axis the file happens to
    store it in. A no-op, and one that strips the tag, on a file with no
    orientation metadata — the common case for anything not straight off a
    camera.

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
            return _flattened(ImageOps.exif_transpose(opened))
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


#: EXIF's ``Orientation`` tag, and the four of its eight values that exchange
#: the two axes (transpose, rotate 90, transverse, rotate 270). ``ImageOps.
#: exif_transpose`` acts on the same four and ignores anything outside 2..8, so
#: :func:`probe_extent` and :func:`load_greyscale` agree on what "the picture's
#: width" means — a phone photo stored on its side is measured, and cropped,
#: along the axis the user actually sees.
_ORIENTATION_TAG = 0x0112
_AXIS_SWAPPING_ORIENTATIONS = frozenset({5, 6, 7, 8})


def probe_extent(source: str | PathLike[str]) -> tuple[int, int]:
    """The source's ``(width, height)`` in pixels, without decoding it.

    Exists for guardrail G-4: :func:`validate_aspect_ratio` needs the source's
    shape, and nothing else, to decide whether the request is refused — so a
    refused request must not pay for a decode. ``Image.open`` is lazy and reads
    the header only, which carries both the extent and the EXIF orientation, so
    the guard's four integers are available for the price of a header parse.

    The extent returned is the *displayed* one: the axes are exchanged for the
    four orientations that rotate the picture a quarter turn, which is exactly
    what :func:`load_greyscale`'s ``exif_transpose`` will do to the pixels a
    moment later. Measuring the stored raster instead would judge a portrait
    phone photo as landscape and refuse — or badly crop — the very input this
    feature is for.

    Args:
        source: Path to the user's image file, as given.

    Returns:
        ``(width, height)`` in pixels, as the user sees the picture.

    Raises:
        UnreadableImage: the same failures :func:`load_greyscale` reports, from
            the same guard — a file whose header cannot even be parsed is an
            unreadable image (AC-008) and is reported as one *before* the aspect
            ratio is considered, since its shape is not known at all.
    """
    try:
        with Image.open(source) as opened:
            width, height = opened.size
            orientation = _header_orientation(opened)
    except _UNREADABLE as error:
        raise UnreadableImage(
            f"cannot read image {str(source)!r}: {error}"
        ) from error
    if orientation in _AXIS_SWAPPING_ORIENTATIONS:
        return (height, width)
    return (width, height)


def _header_orientation(opened: Image.Image) -> int | None:
    """``opened``'s EXIF orientation, read from the header alone.

    Pointedly **not** ``opened.getexif()``: for PNG that call decodes the whole
    file (Pillow looks for an ``eXIf`` chunk and falls back to ``load()`` when
    there is none), which is the one thing :func:`probe_extent` exists to avoid.
    ``Image.open`` puts the raw EXIF block in ``info`` for the formats that
    carry one in their header — JPEG above all, which is what a phone produces
    and therefore what orientation handling is for — so parsing that block is
    both cheap and enough.

    **Total by construction: it answers "no orientation" rather than raising.**
    A corrupt EXIF block is not an unreadable picture — ``exif_transpose``
    tolerates one and converts the pixels perfectly — so the only honest answer
    here is the one it independently reaches: no usable orientation tag.
    ``Image.Exif().load`` reports a bad block with whatever its TIFF parser
    happens to raise (measured on Pillow 12.3.0: ``SyntaxError: not a TIFF
    file`` for a bad magic, ``struct.error: unpack requires a buffer of 4
    bytes`` for a block cut off inside the eight-byte TIFF header), none of
    which is in :data:`_UNREADABLE` and none of which is a
    ``NonogramError``; letting one out would put a stack trace in front of a
    user whose file converts fine. Hence the bare ``except Exception``: the set
    of things a third-party header parser can raise is not enumerable, and every
    member of it means the same thing here. The tag lookup sits inside the same
    guard as the parse: Pillow 12.3.0 parses the IFD eagerly in ``load``, so
    ``get`` is a plain dictionary read today and 13 crafted blocks (bad magic,
    truncated header, IFD offset past the end, entry types 0/2/5/7/13/99, lying
    and oversized entry counts) could not make it raise — but the argument above
    is about a parser this project does not pin a version of, and it applies to
    both lines or to neither.

    A file whose EXIF sits somewhere ``open`` does not reach also reports no
    orientation here, while ``exif_transpose`` *would* still find it. That
    disagreement is declared rather than avoided (the alternative costs a full
    decode on every conversion of every PNG); :func:`generate` closes it by
    re-running the guard on the extent the decode actually produced whenever the
    two differ — see failure-matrix row 14.
    """
    raw = opened.info.get("exif")
    if not raw:
        return None
    exif = Image.Exif()
    try:
        exif.load(raw)
        return exif.get(_ORIENTATION_TAG)
    except Exception:  # noqa: BLE001 — a corrupt tag is not an unreadable file
        return None


def _checked_extents(
    source_width: int, source_height: int, target_width: int, target_height: int
) -> None:
    """Reject the two degenerate extents both public geometry functions share.

    A zero-pixel *source* axis is the user's file being unusable — Pillow can
    hold a 0-width image, there is nothing to convert, and the reason is the
    file — so it is reported as the same input error as an undecodable one
    rather than as an arithmetic accident downstream.

    A zero-or-negative *target* axis is a different animal: grid extents come
    from :func:`~nonogram.sourcing.random_grid.validate_size` and are 10..30 by
    the time anything here sees them (CON-011), so a target of ``0`` is a wiring
    bug in the caller, not a domain outcome. It gets ``ValueError``, the same
    way :func:`nudge` treats a zeroth nudge attempt.
    """
    if source_width <= 0 or source_height <= 0:
        raise UnreadableImage(
            "image has no pixels to convert "
            f"(its size is {source_width}x{source_height})"
        )
    if target_width <= 0 or target_height <= 0:
        raise ValueError(
            "grid extents are at least 1 cell a side, got "
            f"{target_width}x{target_height}"
        )


def fit_crop_box(
    source_width: int, source_height: int, target_width: int, target_height: int
) -> tuple[int, int, int, int]:
    """The largest centred crop of the source having the *grid's* aspect ratio.

    The aspect-ratio policy, on its own so it can be reasoned about (and
    tested) without an image in the way — see the module docstring for why
    cropping rather than stretching or padding, and FR-020/EC-006 for the
    property this is the implementation of.

    Exactly one axis is cropped: whichever of the two is longer *relative to the
    grid*. The other is kept whole, which is what makes this the largest such
    rectangle — the box touches both source edges on that axis, so it cannot be
    grown without leaving the source. ``target_width == target_height``
    reproduces the largest centred square this function used to return under its
    old name ``square_crop_box`` (AC-072).

    All the arithmetic is integer. The ideal crop extent
    (``source_height * target_width / target_height`` on the cropped axis, or
    its transpose) is generally not a whole number of pixels, so it is floored:
    the box is the largest *integer* rectangle that does not exceed the target
    ratio on the cropped axis. Python's integers are arbitrary-precision, so
    there is nothing here for an overflow to happen to at any image size Pillow
    can decode.

    Args:
        source_width: Source width in pixels.
        source_height: Source height in pixels.
        target_width: Requested grid width in cells.
        target_height: Requested grid height in cells.

    Returns:
        A Pillow crop box ``(left, upper, right, lower)`` lying entirely inside
        the source, touching both source edges on at least one axis. An odd
        leftover pixel on the cropped axis goes to the *far* side, because
        integer division floors the near offset; the two discarded margins
        therefore differ by at most one pixel (AC-073). That is a half-pixel
        bias on one axis of a source about to be resized to at most 30 cells,
        and pinning it explicitly is worth more than pretending it can be
        avoided.

        Both returned extents are at least 1 pixel. The floor above can reach
        ``0`` only on a source with an axis of one or two pixels; clamping keeps
        the box usable as a ``resize`` argument, at the cost of a crop whose
        ratio is then not the grid's. Nothing else in the module can produce
        that case: :func:`validate_aspect_ratio` refuses every request where the
        two ratios differ by more than 2x, and inside that band a floor to zero
        needs a source axis in ``{1, 2}``.

    Raises:
        UnreadableImage: the source has no pixels on one of its axes.
        ValueError: a target extent is zero or negative — a caller bug, see
            :func:`_checked_extents`.
    """
    _checked_extents(source_width, source_height, target_width, target_height)
    if source_width * target_height >= source_height * target_width:
        # The source is wider than the grid (or exactly as wide): height is kept
        # whole and width is cropped down to the grid's ratio.
        crop_height = source_height
        crop_width = max(1, source_height * target_width // target_height)
    else:
        crop_width = source_width
        crop_height = max(1, source_width * target_height // target_width)
    left = (source_width - crop_width) // 2
    upper = (source_height - crop_height) // 2
    return (left, upper, left + crop_width, upper + crop_height)


def _retained(
    source_width: int, source_height: int, target_width: int, target_height: int
) -> tuple[int, int]:
    """``(kept, whole)`` — the retained fraction of the source, as a ratio.

    ``min(r_src, r_tgt) / max(r_src, r_tgt)`` with ``r = width / height``,
    rearranged into two integers by cross-multiplication so that the comparison
    the guard makes on it is exact at every input. Dividing the two ratios as
    floats and comparing against ``0.5`` gets the inclusive boundary wrong for
    inputs where the quotient is representable only approximately, which is the
    whole reason AC-075 exists (guardrail G-5).
    """
    source_over_target = source_width * target_height
    target_over_source = source_height * target_width
    return (
        min(source_over_target, target_over_source),
        max(source_over_target, target_over_source),
    )


def validate_aspect_ratio(
    source_width: int, source_height: int, target_width: int, target_height: int
) -> None:
    """Refuse a request whose crop would discard more than half the source.

    FR-021/CON-012/ADR-0022/R3, as a pure predicate over the same four integers
    :func:`fit_crop_box` takes — which is what lets it run before the picture's
    pixels are decoded, let alone dithered or solved (EC-007). The centred crop
    keeps exactly ``min(r_src, r_tgt) / max(r_src, r_tgt)`` of the source, so
    "would discard more than half" is precisely "the ratios differ by more than
    2x".

    The boundary is **inclusive**: retaining exactly half — a square source into
    a 30x15 grid, say — is accepted (AC-075). The comparison is therefore
    ``2 * kept >= whole`` on the two integers :func:`_retained` returns, never a
    float division against ``0.5``.

    Args:
        source_width: Source width in pixels.
        source_height: Source height in pixels.
        target_width: Requested grid width in cells.
        target_height: Requested grid height in cells.

    Raises:
        ImageNeedsManualCrop: the ratios differ by more than 2x. The message
            names both extents, says what fraction of the picture would survive,
            and tells the user to crop it themselves before retrying (AC-077).
            The percentage is floored, not rounded, and no float is involved in
            producing it either: a request refused at 0.4988 retained (401x200
            into 20x20, measured) must not be reported as "50% of the picture"
            when keeping exactly 50% is the *accepted* boundary — a user told
            they were refused at the accepted figure would reasonably conclude
            the tool is wrong. Flooring makes the number an understatement in
            the safe direction: every refusal reports at most 49%.
        UnreadableImage: the source has no pixels on one of its axes.
        ValueError: a target extent is zero or negative.
    """
    _checked_extents(source_width, source_height, target_width, target_height)
    kept, whole = _retained(
        source_width, source_height, target_width, target_height
    )
    if 2 * kept >= whole:
        return
    raise ImageNeedsManualCrop(
        f"a {source_width}x{source_height} picture is too differently shaped "
        f"from a {target_width}x{target_height} grid: fitting it would keep "
        f"only {100 * kept // whole}% of the picture. Crop the picture "
        "yourself to roughly the grid's proportions first, or ask for a grid "
        "shaped more like the picture."
    )


def binarize(
    greyscale: Image.Image, target_width: int, target_height: int
) -> Image.Image:
    """Crop to the grid's ratio, resize to ``target_width`` x ``target_height``
    and Floyd-Steinberg dither.

    Args:
        greyscale: The source in mode ``"L"``, at its original dimensions.
        target_width: Requested grid width in cells.
        target_height: Requested grid height in cells.

    Returns:
        A ``target_width`` x ``target_height`` image in Pillow's bilevel ``"1"``
        mode — note Pillow's ``(width, height)`` order, which is the transpose
        of the row-major grid :func:`to_grid` builds from it.

    The extents are assumed already validated, exactly as ``size`` was before
    them: :func:`generate` checks the range and the aspect ratio before calling.

    The crop and the resize are one call: ``resize`` takes the source rectangle
    as its ``box`` argument, so the intermediate cropped image is never
    materialised and the resampling filter sees the crop's true pixel grid
    rather than a re-quantised copy of it.
    """
    scaled = greyscale.resize(
        (target_width, target_height),
        resample=RESAMPLING,
        box=fit_crop_box(*greyscale.size, target_width, target_height),
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
        whenever the source's aspect ratio is inside FR-021's accepted band
        (AC-059).

    Raises:
        UnreadableImage: ``source`` is ``None``, missing, unreadable or not a
            decodable image (AC-008). Pillow's own exception never reaches the
            caller.
        SizeOutOfRange: ``size`` is outside the supported range.
        ImageNeedsManualCrop: the source's aspect ratio differs from the grid's
            by more than 2x, so fitting it would throw away more than half the
            picture (AC-076, FR-021).

    The three checks run in the order the user can act on them, and each runs
    before the work it would have paid for: the size range before the file is
    touched at all, the aspect ratio after a header read and before the decode,
    the decode before the conversion. So an invalid request never pays for a
    decode and a refused one never pays for a dither — the "reject before you
    work" contract the other two sources keep (guardrail G-4, EC-007).

    The aspect check runs a *second* time, and only when the decoded picture
    turns out not to be the shape the header advertised — the one case where
    :func:`probe_extent` and :func:`load_greyscale` can disagree (a PNG whose
    ``eXIf`` chunk follows ``IDAT``). Judging the probed extent alone would let
    such a request through the guard while the crop discarded most of it, which
    is exactly what CON-012 forbids. The re-check costs nothing on the refused
    path — it is downstream of a decode a refused request never reaches — so
    G-4 is unaffected: the cheap probe still refuses the common case before any
    pixel is read, and the rare disagreement is caught after the decode rather
    than never (failure-matrix row 14).

    This card deliberately still takes a scalar ``size`` and passes ``(size,
    size)`` to both new functions, which are already general. CARD-027 replaces
    these two call sites with the request's ``(width, height)`` pair (FR-018,
    ADR-0022/R1) and changes nothing else here.
    """
    if source is None:
        raise UnreadableImage(
            "image mode needs an --image PATH pointing at the picture to convert"
        )
    size = random_grid.validate_size(size)
    probed = probe_extent(source)
    validate_aspect_ratio(*probed, size, size)
    greyscale = load_greyscale(source)
    if greyscale.size != probed:
        # The header probe and the decode disagreed about the picture's shape.
        # Two measured classes reach here, so the test is on the extents rather
        # than on a format: a PNG whose ``eXIf`` chunk follows ``IDAT`` (which
        # ``Image.open`` does not reach), and an orientation-tagged TIFF (whose
        # reader applies the orientation to ``size`` and then lets
        # ``exif_transpose`` apply it a second time). Judge the extent the crop
        # will actually use, so the guard cannot be talked into accepting a
        # request that discards most of the picture.
        #
        # This is the one path on which a refusal costs a decode: the cheap
        # probe still refuses the common case for free, but a request the probe
        # accepted and the truth rejects is refused only after ``load_greyscale``
        # has run. Cropping, dithering, clue derivation and the solver stay
        # unreachable for it. See failure-matrix rows 12 and 14 — G-4's
        # unqualified wording is narrowed there to match this.
        validate_aspect_ratio(*greyscale.size, size, size)
    return to_grid(binarize(greyscale, size, size))


#: How far apart two cells flipped by the same nudge must be, as a Chebyshev
#: distance. ``1`` means "not touching, diagonals included", and it exists
#: because of how :func:`nudge_cells` ranks: the four cells of one switching
#: 2x2 block all score identically, so an unspaced top-``n`` would spend a whole
#: nudge budget inside a single block — and flipping *both* cells of a diagonal
#: pair simply turns that block into the other diagonal, which is the same
#: ambiguity again. Spacing makes each successive flip break a different local
#: structure.
_NUDGE_SPACING = 1


def _switch_counts(rows: list[list[bool]]) -> dict[tuple[int, int], int]:
    """How many 2x2 "switching" blocks each cell belongs to.

    The heuristic's primary signal. A 2x2 block whose two diagonals each hold
    one value and the other holds the other —

    ::

        # .        . #
        . #   or   # .

    — is the canonical seed of a non-unique nonogram: exchanging the two
    diagonals moves no cell into or out of any run when the block sits in the
    interior of otherwise-equal lines, so the clue set cannot tell the two
    apart. Real ambiguity is usually a chain of such blocks rather than a lone
    one, which is why this counts *participation* rather than flagging blocks:
    a cell shared by several of them is where a chain is anchored, and is
    therefore the flip most likely to break the whole chain at once.
    """
    counts: dict[tuple[int, int], int] = {}
    for row in range(len(rows) - 1):
        top, bottom = rows[row], rows[row + 1]
        for column in range(len(top) - 1):
            upper_left, upper_right = top[column], top[column + 1]
            lower_left, lower_right = bottom[column], bottom[column + 1]
            if (
                upper_left != upper_right
                and upper_left == lower_right
                and upper_right == lower_left
            ):
                for cell in (
                    (row, column),
                    (row, column + 1),
                    (row + 1, column),
                    (row + 1, column + 1),
                ):
                    counts[cell] = counts.get(cell, 0) + 1
    return counts


def _boundary_counts(rows: list[list[bool]]) -> dict[tuple[int, int], int]:
    """How many orthogonal neighbours disagree with each cell.

    The heuristic's secondary signal — the card's "at a run boundary", counted.
    A cell with no disagreeing neighbour is buried inside a solid block or a
    wide expanse of paper, where a flip splits a run in two (or plants a stray
    dot) and changes the picture more than it changes the puzzle. A cell with
    three or four is an isolated dot or a single-cell notch: the flimsiest part
    of the drawing, where a clue is most likely to be doing the least work.
    """
    height = len(rows)
    width = len(rows[0]) if height else 0
    counts: dict[tuple[int, int], int] = {}
    for row in range(height):
        for column in range(width):
            value = rows[row][column]
            different = sum(
                1
                for neighbour_row, neighbour_column in (
                    (row - 1, column),
                    (row + 1, column),
                    (row, column - 1),
                    (row, column + 1),
                )
                if 0 <= neighbour_row < height
                and 0 <= neighbour_column < width
                and rows[neighbour_row][neighbour_column] != value
            )
            if different:
                counts[(row, column)] = different
    return counts


def nudge_cells(grid: list[list[bool]], count: int) -> tuple[tuple[int, int], ...]:
    """The ``count`` cells of ``grid`` a nudge should flip, best first.

    The ranking, split out of :func:`nudge` so the choice of cell can be
    inspected (and tested) without diffing two grids. Every cell of the grid is
    ranked, so a supply of candidates always exists — even for a blank or solid
    conversion, where neither signal fires and the order falls back to
    centre-outward.

    The sort key, in order:

    1. switching-block participation, descending (:func:`_switch_counts`);
    2. disagreeing-neighbour count, descending (:func:`_boundary_counts`);
    3. distance from the centre of the grid, ascending — a tie-break with a
       reason: the middle of the picture carries the subject, so a flip there
       is more likely to be inside the structure the clues are ambiguous about
       than one in a corner, and the crop policy above has already thrown the
       edges away once;
    4. row then column, so the result is fully deterministic.

    Selection is greedy over that ranking with a :data:`_NUDGE_SPACING`
    exclusion around each cell already chosen. If spacing cannot supply
    ``count`` cells (a grid too small to hold them), the shortfall is filled
    from the rest of the ranking in order rather than returning fewer.

    Args:
        grid: The converted grid, in the ADR-0012 boundary representation.
        count: How many cells to pick. ``0`` or less picks none.

    Returns:
        Up to ``count`` ``(row, column)`` pairs, best first, all distinct. The
        first ``k`` of the answer for ``count = n`` are the answer for
        ``count = k``, which is what makes the nudges of one run nest.
    """
    rows = [[bool(cell) for cell in row] for row in grid]
    height = len(rows)
    width = len(rows[0]) if height else 0
    if count <= 0 or height == 0 or width == 0:
        return ()

    switch = _switch_counts(rows)
    boundary = _boundary_counts(rows)

    def rank(cell: tuple[int, int]) -> tuple[int, int, int, int, int]:
        row, column = cell
        # Doubled offsets keep the centre distance an exact integer for grids
        # of either parity, so the ordering never depends on float rounding.
        centre_distance = max(
            abs(2 * row - (height - 1)), abs(2 * column - (width - 1))
        )
        return (
            -switch.get(cell, 0),
            -boundary.get(cell, 0),
            centre_distance,
            row,
            column,
        )

    ranked = sorted(
        ((row, column) for row in range(height) for column in range(width)), key=rank
    )

    chosen: list[tuple[int, int]] = []
    for cell in ranked:
        if len(chosen) == count:
            break
        if all(
            max(abs(cell[0] - taken[0]), abs(cell[1] - taken[1])) > _NUDGE_SPACING
            for taken in chosen
        ):
            chosen.append(cell)
    if len(chosen) < count:
        remaining = [cell for cell in ranked if cell not in set(chosen)]
        chosen.extend(remaining[: count - len(chosen)])
    return tuple(chosen)


def nudge(grid: list[list[bool]], attempt_number: int) -> list[list[bool]]:
    """POL-002's pixel nudge: ``grid`` with ``attempt_number`` cells flipped.

    The mechanism half of FR-013 (the policy half is COMP-002's bounded loop).
    The orchestrator hands in the grid the conversion produced and the 1-based
    number of the nudge attempt it is on, and gets back a *new* grid — the
    argument is never mutated, so the run's original conversion stays available
    for the next attempt and for the failure message.

    Cumulative, and cumulative *from the conversion* rather than from the
    previous nudge: attempt ``n`` flips the best ``n`` cells of the original
    grid (:func:`nudge_cells`), so after ``n`` attempts exactly ``n`` pixels of
    the user's picture have been changed and each attempt is a strict extension
    of the one before it. Nudging the previously nudged grid instead would make
    each attempt's ranking depend on the last attempt's flip, which lets a flip
    be undone by the next one and turns a five-attempt budget into a two-grid
    oscillation. It also keeps POL-003 honest at the cap: "stops altering the
    image" is observable as "the grid is the conversion plus at most five
    pixels", not "the grid has drifted somewhere unknown".

    The heuristic, and what else was considered
    -------------------------------------------
    Which cell to flip is a guess, and the card says so — this is the risk
    CARD-016 exists to collapse. The guess made here is that a nonogram's
    non-uniqueness lives in 2x2 switching blocks, so the ranking is
    "participates in the most of them, then sits on the most run boundaries,
    then nearest the middle" (:func:`nudge_cells` spells the key out). It is a
    *structural* guess about the grid, not a reading of the solver: the solver
    reports how many solutions a clue set has and which cells line logic
    settled (``SolveSignals``), but not which cells the two solutions disagreed
    on, and COMP-003 may not ask it anything anyway (ADR-0007) — a capability
    module never calls a sibling. Flipping a cell the solver could not decide,
    the card's other suggestion, is therefore the strictly better heuristic
    that this codebase cannot express today; it would need the solver to
    surface a disagreement mask and the orchestrator to pass it in, which is a
    change to COMP-005's contract and out of this card's scope (guardrail G-1).

    Everything here is deliberately in one swappable function: the loop above
    calls :func:`nudge` and nothing else, so a better heuristic — a
    disagreement mask, a density-preserving swap, a flip chosen to lengthen the
    shortest clue — replaces the body of these two functions and leaves
    COMP-002 untouched.

    Args:
        grid: The converted grid, in the ADR-0012 boundary representation.
        attempt_number: Which nudge attempt this is, counted from ``1`` by
            COMP-002's :class:`~nonogram.orchestrator.RetryCounter`. It is an
            argument rather than module state precisely so that INV-003 has one
            home (guardrail G-2): this module counts nothing.

    Returns:
        A fresh row-major ``list[list[bool]]`` of the same dimensions, with
        ``attempt_number`` cells flipped.

    Raises:
        ValueError: ``attempt_number`` is not at least 1. A nudge is an attempt
            that has already been counted, so a zeroth one is a wiring bug in
            the caller rather than a domain outcome — the same reasoning
            ``_source_arguments``' own ``ValueError`` follows.
    """
    if attempt_number < 1:
        raise ValueError(
            f"nudge attempt numbers start at 1, got {attempt_number!r}"
        )
    nudged = [[bool(cell) for cell in row] for row in grid]
    for row, column in nudge_cells(grid, attempt_number):
        nudged[row][column] = not nudged[row][column]
    return nudged
