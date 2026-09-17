"""COMP-003 / CAP-001 — the uploaded-image source of a grid (FR-003).

The third and last grid origin, and deliberately the same shape of thing as the
first two: a callable registered in the package's mode table that returns one
grid in the ADR-0012 boundary representation (``list[list[bool]]``, row-major,
``True`` for a filled cell) and takes the run's injected ``random.Random``
last (ADR-0015). Everything downstream — clue derivation, the uniqueness check,
export — is reused unchanged.

The pipeline, in one line
-------------------------
``open -> flatten transparency onto white -> greyscale -> compute the ink
bounding box -> judge the request against that box -> trim to it -> crop to the
requested grid's aspect ratio -> resize to width x height -> Floyd-Steinberg
dither -> ink is a filled cell``.

That order is prescribed by ADR-0022, not chosen here. Computing a bounding box
reads pixels but writes nothing and discards nothing, so the guard below still
refuses a badly shaped request **before any cropping runs** — the trim included
(EC-007). Judging the box after applying it would break that.

Trimming blank margin: the picture, not the file (FR-022)
---------------------------------------------------------
An uploaded silhouette is usually a small subject on a large sheet of paper, and
every millimetre of that paper costs a whole grid line at 20 cells across.
:func:`ink_bounding_box` finds the smallest rectangle containing every ink pixel
— ink being a greyscale value below :data:`INK_THRESHOLD`, a mid grey — and the
conversion trims to it before the aspect fit.

The threshold is 128 rather than "anything not pure white" because it was
measured, not assumed. Over the 25 pictures committed under ``pictures/`` at a
20x20 grid: 19 carry more than one all-empty row or column at some edge
untrimmed; trimming at ink < 128 fixes 17 of those 19, leaving 2 (AC-086). A
near-white threshold of 245 counts JPEG ringing and off-white paper as ink and
so trims almost nothing — 6 of the 25 still violate the rule (AC-089).

**Best-effort, not an invariant.** FR-022 says so and the corpus shows why: the
resize and the dither downstream of the trim can still blank an edge line whose
source content was faint, so ``dear1.jpg`` keeps 2 blank lines (AC-088) and
``wolf1.jpeg`` keeps 3 (AC-091) — the latter measuring 3 deep *before* trimming
too, so no threshold helps it. Nothing here promises the property; the criteria
pin how far short it falls.

A picture with no ink at all (a wholly white or wholly light-grey field) has no
bounding box, and the honest answer is to trim nothing: the whole extent is
returned, and a blank sheet converts to a blank grid the way it always did.

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
integer cross-multiplication rather than float division.

**The source extent it judges is the INK BOUNDING BOX, not the as-decoded file**
(ADR-0022 revision 2026-09-01, DEC-025). CON-012 promises never to silently
discard more than half *the user's picture*, and blank margin is not the user's
picture: measured over the 25 corpus pictures at 20x20, the as-decoded reading
overstates what survives the crop on **22** of them — by more than 5 percentage
points on 15 of those — reads exactly right on 1, and *understates* on the
remaining 2. The worst are ``img_2.png`` and ``img_3.png``, which report 100%
retained while 55% of the actual content survives. It errs both ways rather than
conservatively, so it was not a safe approximation, merely an inaccurate one.

The price, accepted in the ADR rather than worked around here: **the guard can
no longer refuse before decoding.** A trim moves a ratio in either direction, so
no sound refusal follows from the file header alone, and the cheap
``probe_extent`` path CARD-026 built for this guard is retired — every image
request now pays for one decode. Everything the decode is *for* — the trim, the
aspect crop, the resize, the dither, clue derivation, the solver — stays
unreachable for a refused request, which is the guarantee EC-007 actually makes.

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

Two ways to reach black and white, and which one a picture gets
--------------------------------------------------------------
CARD-015 shipped one: Floyd-Steinberg dither, on the reasoning that a plain
50% cut turns a photograph into two flat blobs while error diffusion trades
grey *level* for filled-cell *density*, which is what makes a mid-tone region
readable at all on a grid this coarse. That reasoning is still right — about
photographs.

It is wrong about silhouettes, which is what CON-013 actually scopes this mode
to. Dither preserves average density, not *contour*: along a hard edge it
seeds isolated cells and ragged boundaries, which is precisely the one-cell
runs and 2x2 switching blocks that make a nonogram non-unique and that
POL-002's nudge then repairs one pixel at a time. So CARD-079 lands both:
:data:`THRESHOLD` (ADR-0026, an inclusive 50% ink-coverage cut on the resized
value) and :data:`DITHER` (unchanged), with
:func:`classify_binarisation` choosing between them on the source histogram
(ADR-0028) — mid-tones mean a photograph, their absence means a drawing.

**Which one ships was the owner's decision, not the code's.** CARD-079 landed
both paths with :data:`DEFAULT_BINARISATION` pinned to dither and stopped at a
visual gate on the corpus rendered both ways (DEC-032, FR-027 ``_meta.gate``).
The gate found what a uniqueness count cannot: a coverage threshold keeps
*filled areas*, and line art has none, so it erases a line drawing to
near-blank — and a near-blank grid is uniquely solvable *by being empty*, so
every check downstream passes it. The owner flipped the default on
2026-09-17 on the condition that this is guarded: :func:`convert` measures the
threshold conversion's ink share against :data:`USABLE_INK_SHARE` and, when it
falls outside, converts the picture on the dither path instead. Falling back
rather than refusing means no picture the tool converted before the flip can
become an error because of it.

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
:func:`next_nudge_cell` and :func:`nudge` are that mechanism and the whole of
this module's part in it: the first says which cell the next attempt adds, the
second applies a set of cells to the original conversion. Neither is told which
attempt it is on and neither keeps a count — there is no counter, no loop and
no bound in this file, by design (guardrail G-2) — and nothing here decides
whether a nudged grid is good: the orchestrator re-runs the real solver on
every one of them (CON-005, guardrail G-4).

CARD-075 (2026-09-17) replaced what the choice is *made of*, not the split.
The cells now come from the solver's own report on the previous attempt's
candidate — where its two witnesses disagreed, or its undecided mask — which
arrives as a parameter, because ADR-0007 forbids this module from asking
COMP-005 anything. What it replaced was a structural guess about 2x2
"switching" blocks, which CARD-096 measured rescuing none of the 36
conversions dithering fails across the owner's corpus.

Layering (ADR-0007): a capability module. It imports its own package's
``random_grid`` for the shared extent rule and ``nonogram.errors``; never the
adapter, the orchestrator or a sibling capability.
"""

from __future__ import annotations

import random
from collections.abc import Iterable
from os import PathLike

import numpy
from PIL import Image, ImageOps, UnidentifiedImageError

from nonogram.errors import ImageNeedsManualCrop, UnreadableImage
from nonogram.sourcing import random_grid

__all__ = [
    "DEFAULT_BINARISATION",
    "DITHER",
    "INK_THRESHOLD",
    "MIDTONE_BAND",
    "MIDTONE_SHARE_THRESHOLD",
    "RESAMPLING",
    "THRESHOLD",
    "USABLE_INK_SHARE",
    "binarisation_for",
    "binarize",
    "classify_binarisation",
    "convert",
    "fit_crop_box",
    "generate",
    "ink_bounding_box",
    "ink_share",
    "is_degenerate",
    "load_greyscale",
    "midtone_share",
    "next_nudge_cell",
    "nudge",
    "source_shape",
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

#: What counts as ink when :func:`ink_bounding_box` decides where the picture
#: stops and the paper starts: a greyscale value **strictly below** this is ink
#: (FR-022). A mid grey, and measured rather than assumed — see the module
#: docstring for the corpus figures that put it here rather than at near-white.
INK_THRESHOLD = 128

#: The two ways a resized grey value can become a filled or empty cell.
#: Strings rather than an ``Enum`` because this is a boundary value in the
#: ADR-0012 sense — it is recorded on the aggregate and (CARD-072) exported —
#: and the module's other vocabulary (``sourcing.IMAGE`` and its siblings) is
#: spelled the same way.
THRESHOLD = "threshold"
DITHER = "dither"

#: ADR-0028/R1's mid-tone band, closed at both ends. A picture whose pixels
#: mostly sit *outside* it is two-toned — a silhouette, a logo, line art — and
#: has a contour for the threshold to keep. One whose pixels sit inside it is
#: a photograph or a shaded drawing, where a threshold would flatten the
#: modelling into a blob and the dither's average-density trade is the right
#: one. 64 and 191 are the quarter and three-quarter points of the 8-bit
#: range, chosen for being obvious rather than measured.
MIDTONE_BAND = (64, 191)

#: The share of pixels inside :data:`MIDTONE_BAND` at or above which a picture
#: is treated as genuinely greyscale (ADR-0028/R1).
#:
#: **Provisional, and owed a calibration.** 0.10 is a guess; CARD-079 records
#: the measured share of every corpus picture in its Worktree notes so the
#: owner can set this on data rather than on the guess. Anti-aliasing alone
#: puts a few percent of a clean silhouette's pixels in the band, which is the
#: floor this has to clear; JPEG ringing raises it further.
MIDTONE_SHARE_THRESHOLD = 0.10

#: Which path :func:`binarize` takes when it is not told — and therefore the
#: one every uploaded picture actually gets. Three states, and the difference
#: between them is the whole shape of CARD-079:
#:
#: * :data:`DITHER` — what ships today. Every picture is dithered and
#:   :func:`classify_binarisation` is never consulted.
#: * :data:`THRESHOLD` — every picture is thresholded. Useful for the review
#:   render; not a state anything is expected to ship in.
#: * ``None`` — ask :func:`classify_binarisation` per picture. This is what
#:   ADR-0026 and ADR-0028 together describe, and it is what the owner's flip
#:   sets after the visual gate (CARD-079 guardrail G-1: never this card's
#:   commit).
#:
#: Pinned rather than defaulted, because a binarisation change alters every
#: converted picture and the owner validates image work by eye, not by test
#: (CARD-079's gate, DEC-032).
#:
#: **Flipped to ``None`` on 2026-09-17**, by the owner, after that gate: 25
#: pictures rendered both ways at 25x25, plus AC-127 over five sizes. ADR-0026
#: is Accepted with it. The flip was made conditional on the degenerate-ink
#: guard below, which is what stops the threshold path shipping the blank page
#: the gate found.
DEFAULT_BINARISATION: str | None = None

#: The filled-cell share a conversion has to land inside to be a picture at
#: all — the guard the owner attached to ADR-0026's acceptance.
#:
#: A coverage threshold keeps *filled areas*, and line art has none: it is
#: made of strokes thinner than a cell, every one of which averages to more
#: paper than ink and is erased. The result is not a bad puzzle, it is an
#: **empty** one — and an empty grid's clues have exactly one solution, so
#: every check downstream passes it and the user is handed a blank page. The
#: mirror case is a mostly-dark picture thresholding to solid black.
#:
#: Measured, not guessed (CARD-079, 25 pictures x five sizes, plus the test
#: fixtures). Under the threshold path ``cat_Mouse.png`` — line art — converts
#: at **1.0% to 2.7%** ink at every size, and the emptiest *legitimate*
#: conversion anywhere on hand is ``tests/fixtures/landscape.png`` at **9.0%**
#: — a thin horizon on a wide sheet, sparse but a picture. The corpus's own
#: next-emptiest is ``butterfly.png`` at 18.0%.
#:
#: So the floor is set from the narrower of the two gaps, [2.7%, 9.0%], not
#: from the corpus gap [2.7%, 18.0%] alone: 5% keeps line art caught with
#: nearly double the margin while leaving a genuinely sparse picture on the
#: path its histogram chose. Taking the corpus gap's midpoint (10%) would have
#: bounced ``landscape.png`` to the dither path for no reason — found by a
#: test, which is the whole argument for having fixtures that are not corpus
#: pictures.
#:
#: The ceiling is the floor's mirror and is **untriggered by anything on
#: hand** (the densest conversion is 82.0%); it is here because "all black" is
#: the same defect as "all white" and finding out the hard way is not worth
#: the asymmetry — ADR-0027 refuses density 0 *and* 100 for the same reason.
USABLE_INK_SHARE = (0.05, 0.95)

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


def ink_bounding_box(
    greyscale: Image.Image, threshold: int = INK_THRESHOLD
) -> tuple[int, int, int, int]:
    """The smallest box containing every ink pixel of ``greyscale`` (FR-022).

    Where the user's picture actually is, as opposed to where their file
    happens to end. Ink is a value **strictly below** ``threshold``, so the
    threshold itself is paper — 128 is a mid grey and the mid grey of a flat
    128 field is deliberately *not* ink, which is what keeps a dithering
    fixture a dithering fixture rather than an empty box.

    Computed with Pillow and nothing else (guardrail G-3, ADR-0006/R1): a
    256-entry lookup table turns the greyscale into an ink mask in one C-level
    pass, and ``getbbox`` walks that mask. Both are operations Pillow already
    ships, so the ink box costs one extra pass over the pixels and no new
    dependency. NumPy would do it too and is in the baseline, but it would have
    to materialise the whole raster as an array first, which is the more
    expensive of the two ways to get the same four integers.

    **Reads pixels; writes and discards nothing.** That is the property the
    pipeline order in the module docstring rests on — the box can be handed to
    :func:`validate_aspect_ratio` and the request refused with no crop of any
    kind having been applied (EC-007, ADR-0022/R3).

    Args:
        greyscale: The source in mode ``"L"``, at its original dimensions —
            :func:`load_greyscale`'s output, already flattened onto white so a
            transparent margin reads as the paper it looks like.
        threshold: What counts as ink, as a greyscale value. Defaults to
            :data:`INK_THRESHOLD`; a parameter because AC-089 compares this
            threshold against a near-white one on the same corpus, and a
            constant nothing can vary is a constant nothing has justified.

    Returns:
        A Pillow crop box ``(left, upper, right, lower)``. For a picture with
        no ink at all — a blank sheet, or one whose every pixel is lighter than
        ``threshold`` — the **whole extent** is returned rather than an empty
        or absent box: there is nothing to trim to, and the honest answer is to
        trim nothing. A zero-pixel image likewise returns its own zero extent,
        which :func:`validate_aspect_ratio` then reports as the input error it
        is.
    """
    if not 0 <= threshold <= 256:
        raise ValueError(
            f"an ink threshold is a greyscale value in 0..256, got {threshold!r}"
        )
    whole = (0, 0, greyscale.width, greyscale.height)
    if greyscale.width == 0 or greyscale.height == 0:
        return whole
    ink = greyscale.point([255] * threshold + [0] * (256 - threshold), mode="L")
    return ink.getbbox() or whole


def _checked_extents(
    source_width: int, source_height: int, target_width: int, target_height: int
) -> None:
    """Reject the two degenerate extents both public geometry functions share.

    A zero-pixel *source* axis is the user's file being unusable — Pillow can
    hold a 0-width image, there is nothing to convert, and the reason is the
    file — so it is reported as the same input error as an undecodable one
    rather than as an arithmetic accident downstream.

    A zero-or-negative *target* axis is a different animal: grid extents come
    from :func:`~nonogram.sourcing.random_grid.validate_extent` and are 10..30 by
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
        path: :data:`THRESHOLD` or :data:`DITHER`. **Required**, and
            deliberately so: this function is one half of a conversion, and
            *choosing* the half — reading :data:`DEFAULT_BINARISATION`,
            consulting the classifier, applying the degenerate-ink guard —
            belongs to :func:`convert`, which is the only place that does it.
            An earlier draft let this default to "resolve it yourself", and
            the result was two answers to "what does this picture convert to":
            callers that went through :func:`convert` got the guard and
            callers that came here directly did not. Required is what makes
            that unrepresentable.

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
    :func:`fit_crop_box` takes — which is what lets it run before any *cropping*
    of the picture, let alone dithering or solver work (EC-007). The centred crop
    keeps exactly ``min(r_src, r_tgt) / max(r_src, r_tgt)`` of the source, so
    "would discard more than half" is precisely "the ratios differ by more than
    2x".

    Since CARD-030 the source extent it is handed is the **ink bounding box**,
    not the as-decoded file (ADR-0022 revision 2026-09-01, DEC-025), so it
    necessarily runs *after* the decode — :func:`ink_bounding_box` reads pixels.
    That is the cost the ADR accepted; what EC-007 promises, and what the caller
    order in :func:`generate` still delivers, is refusal before any crop.

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


def source_shape(source: str | PathLike[str] | None) -> tuple[int, int]:
    """The picture's own extent: its **ink bounding box** (FR-022, FR-023).

    What a bare ``--size N`` is completed from in image mode
    (``random_grid.derive_extent``). The box and not the file, for exactly the
    reason ADR-0022's 2026-09-01 revision moved FR-021's guard onto it: blank
    margin is not the user's picture, and a shape derived from the sheet rather
    than from the drawing would reproduce the very defect this card exists to
    remove. This project's own ``pictures/cat.jpg`` is the case in point — a
    580x580 *file* whose ink box is 330x462, so the file says "square" and the
    picture says "portrait", and only one of them keeps the cat's ears.

    Reads pixels; writes and discards nothing, the same property
    :func:`ink_bounding_box` has and for the same reason: this runs *before*
    :func:`generate`, so a request refused on the strength of the shape it
    reports is refused before any crop of any kind (EC-007).

    It does mean a bare-``--size`` image run decodes the file twice — once here
    for the shape, once in :func:`generate` for the pixels. That is a real cost,
    accepted rather than worked around: passing a decoded ``Image`` back out
    would put a Pillow object on a module boundary that carries
    ``list[list[bool]]`` and nothing else (ADR-0012), and an explicit
    ``--size WxH`` never comes here at all, so the second decode is paid only by
    the requests the derivation is actually for.

    Args:
        source: Path to the user's image file (``--image``), as given. ``None``
            is rejected exactly as :func:`generate` rejects it — the derivation
            runs first, and a forgotten flag must come back as the forgotten
            flag rather than as a shape error.

    Returns:
        ``(width, height)`` of the ink bounding box, in pixels — the same
        ``(width, height)`` ordering the other two modes' ``source_shape``
        functions use. Only the ratio is read.

    Raises:
        UnreadableImage: ``source`` is ``None``, missing, unreadable, not a
            decodable image (AC-008), or decodes to an image with no pixels on
            one of its axes.
    """
    if source is None:
        raise UnreadableImage(
            "image mode needs an --image PATH pointing at the picture to convert"
        )
    greyscale = load_greyscale(source)
    box = ink_bounding_box(greyscale)
    width, height = box[2] - box[0], box[3] - box[1]
    if width <= 0 or height <= 0:
        raise UnreadableImage(
            f"image has no pixels to convert (its size is {width}x{height})"
        )
    return width, height


def midtone_share(greyscale: Image.Image) -> float:
    """The share of ``greyscale``'s pixels inside :data:`MIDTONE_BAND`.

    ADR-0028/R1's one measurement, as a pure function of the decoded image:
    one ``Image.histogram()`` pass, no sampling, no rng, no host state. A
    two-toned picture scores near zero — only its anti-aliased rim and any
    compression ringing land in the band — while a photograph or a shaded
    drawing scores high, because modelling *is* mid-tones.

    Args:
        greyscale: The source in mode ``"L"``, as :func:`load_greyscale`
            returns it: EXIF applied, alpha composited onto white, and
            **not** trimmed, cropped or resized. Which image this is asked
            about is the whole of ADR-0028's care — see
            :func:`classify_binarisation`.

    Returns:
        A share in ``[0.0, 1.0]``. An image with no pixels scores ``0.0``
        rather than raising: :func:`generate` and :func:`source_shape` already
        refuse such a file with :class:`UnreadableImage`, and a classifier is
        not the place to discover it a second time.
    """
    counts = greyscale.histogram()
    total = sum(counts)
    if not total:
        return 0.0
    low, high = MIDTONE_BAND
    return sum(counts[low : high + 1]) / total


def classify_binarisation(greyscale: Image.Image) -> str:
    """Which path ADR-0028 puts this picture on: :data:`THRESHOLD` or
    :data:`DITHER`.

    Mid-tone share at or above :data:`MIDTONE_SHARE_THRESHOLD` means a
    genuinely greyscale picture, which keeps today's dither; anything below is
    a silhouette in CON-013's sense and takes the threshold.

    **The image asked about is the source, before trim, crop and resize** —
    that is the rule, not an implementation detail. The resize *manufactures*
    mid-tones: averaging a hard black-and-white edge over a cell produces
    exactly the intermediate greys the band is looking for, so classifying the
    resized image would route every silhouette to the dither path by way of
    its own anti-aliasing, and the classifier would be measuring the pipeline
    rather than the picture.

    ADR-0028 rejected a ``--binarize`` flag deliberately, and the signature is
    where that holds: there is no request field, no override and no rng here,
    so the same file classifies the same way on every host and in every run
    (guardrail G-4, ADR-0015).
    """
    return DITHER if midtone_share(greyscale) >= MIDTONE_SHARE_THRESHOLD else THRESHOLD


def ink_share(grid: list[list[bool]]) -> float:
    """The share of ``grid``'s cells that are filled.

    The measurement :data:`USABLE_INK_SHARE` is read against. Takes the grid
    rather than the image because that is what the question is about: the
    defect is a *converted* picture with nothing in it, and the conversion is
    the only place that is visible.
    """
    cells = sum(len(row) for row in grid)
    if not cells:
        return 0.0
    return sum(sum(row) for row in grid) / cells


def is_degenerate(grid: list[list[bool]]) -> bool:
    """Is this conversion too empty, or too full, to be a picture?

    Outside :data:`USABLE_INK_SHARE` in either direction. Such a grid is very
    often *uniquely solvable* — an all-empty one trivially so — which is
    exactly why it needs its own check: every gate downstream is about
    uniqueness, and a blank page passes all of them.
    """
    low, high = USABLE_INK_SHARE
    share = ink_share(grid)
    return share < low or share > high


def convert(
    greyscale: Image.Image, target_width: int, target_height: int
) -> tuple[list[list[bool]], str]:
    """The conversion, and the path it actually took.

    One place, so that :func:`generate` and :func:`binarisation_for` cannot
    disagree about which path a given file at a given extent gets — which they
    would the moment the guard below made the answer depend on the *result* of
    a conversion rather than only on the picture.

    The guard, and why it falls back rather than refusing
    ----------------------------------------------------
    When the threshold path produces a degenerate grid the conversion is
    redone with the dither path, and the path reported is the one that was
    actually used. Falling back is strictly safer than refusing: dithering is
    what every picture got before ADR-0026 was accepted, so a fallback can
    never turn a picture the tool used to convert into an error — where a
    refusal could. If the dither conversion is *also* degenerate it stands,
    because there is nothing better to reach for and the incumbent path's
    output is not this card's to start rejecting (that is ADR-0027's
    territory, and FR-028's).

    Only the threshold path is guarded. Error diffusion cannot erase a drawing
    the way a coverage cut can — it trades grey level for filled-cell density,
    so a picture with any tone in it comes back with cells in it.
    """
    path = (
        DEFAULT_BINARISATION
        if DEFAULT_BINARISATION is not None
        else classify_binarisation(greyscale)
    )
    grid = to_grid(binarize(greyscale, target_width, target_height, path=path))
    if path == THRESHOLD and is_degenerate(grid):
        return (
            to_grid(binarize(greyscale, target_width, target_height, path=DITHER)),
            DITHER,
        )
    return grid, path


def binarisation_for(
    source: str | PathLike[str] | None, width: int, height: int
) -> str:
    """Which path a conversion of ``source`` at this extent actually takes.

    So COMP-002 can record the path on the aggregate without the decoded image
    crossing a boundary that carries ``list[list[bool]]`` and nothing else
    (ADR-0012). The orchestrator calls this once per image request, not once
    per nudge attempt — the answer cannot change within a run.

    Takes the extent, and converts, because since the degenerate-ink guard the
    answer genuinely depends on both: the same picture can take the threshold
    path at one size and fall back to the dither path at another. Predicting
    it from the histogram alone would be a guess that the conversion could
    then contradict, and a field on the aggregate that is sometimes wrong is
    worse than no field.

    The cost is one conversion — measured at ~4 ms a picture on this project's
    corpus, against a solve that runs from tens to thousands of milliseconds,
    and against the ~3 ms the classifier's own decode costs anyway. Stated
    rather than hidden, because a bare ``--size`` image run already decodes
    twice (see :func:`source_shape`) and this makes three.
    """
    greyscale = load_greyscale(source)
    box = ink_bounding_box(greyscale)
    return convert(greyscale.crop(box), width, height)[1]


def binarize(
    greyscale: Image.Image,
    target_width: int,
    target_height: int,
    *,
    path: str,
) -> Image.Image:
    """Crop to the grid's ratio, resize to ``target_width`` x ``target_height``
    and reduce to black and white — by threshold or by Floyd-Steinberg dither.

    Args:
        greyscale: The source in mode ``"L"``. Since FR-022 this is the picture
            :func:`generate` has already trimmed to its ink box, not the file's
            full extent — but nothing here depends on that: this function fits
            whatever rectangle it is handed to the grid's ratio, which is what
            keeps the trim a step *before* the aspect fit rather than a
            modification of it (guardrail G-1).
        target_width: Requested grid width in cells.
        target_height: Requested grid height in cells.

    Returns:
        A ``target_width`` x ``target_height`` image in Pillow's bilevel ``"1"``
        mode — note Pillow's ``(width, height)`` order, which is the transpose
        of the row-major grid :func:`to_grid` builds from it.

    The extents are assumed already validated: :func:`generate` checks both
    sides against the range and then checks the aspect ratio before calling.

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
    if path == THRESHOLD:
        # ADR-0026/R1. `point` is a per-pixel lookup table, so a cell's verdict
        # depends on its own resized value and on nothing else — which is the
        # property that distinguishes this path, not merely how it is spelled.
        # The cut is inclusive on the ink side: the resized value is 255 minus
        # the cell's ink coverage, so `<= INK_THRESHOLD - 1` is "at least half
        # ink", as closely as an 8-bit raster can say it (AC-126).
        return scaled.point(
            lambda value: 255 if value >= INK_THRESHOLD else 0, mode="L"
        ).convert("1", dither=Image.Dither.NONE)
    if path != DITHER:
        raise ValueError(
            f"binarisation path must be {THRESHOLD!r} or {DITHER!r}, got {path!r}"
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
    width: int | None,
    height: int | None,
    rng: random.Random,
) -> list[list[bool]]:
    """Convert the user's image into one ``width`` x ``height`` solution grid.

    The mode table's entry point for ``image`` (FR-003, AC-007/AC-008/AC-009).
    The argument order is the mode's own — the path first, because it is what
    the mode is *about*, the way ``key`` leads for the library source — and the
    RNG comes last, as it does for every source.

    Args:
        source: Path to the user's image file (``--image``). ``None`` — the
            flag omitted in image mode — is rejected the way library mode
            rejects a missing ``--library-key``: with a message that names the
            forgotten flag, rather than by defaulting to some file.
        width: Grid width in cells.
        height: Grid height in cells. Both sides carry the same supported range
            as every other mode, since it is a rule about the puzzle and not
            about the source (``random_grid.validate_extent``, shared rather
            than restated). The pair is what the picture is fitted *to*: it
            selects the crop box's aspect ratio, so a non-square request is
            served by cropping the source to that shape, never by stretching it
            (ADR-0022/R3).
        rng: The run's random source (ADR-0015). Accepted for the mode table's
            uniform calling convention and deliberately **not drawn from**: the
            conversion of a given file at a given extent is fully determined,
            and jittering it would make the picture the user handed over come
            back as a different picture per seed. Library mode's threshold draw
            exists to give POL-001 a second chance at unique solvability; image
            mode has no regenerate loop to give one to (see the module
            docstring, guardrail G-4).

    Returns:
        A row-major ``list[list[bool]]`` of ``height`` rows of ``width`` cells,
        ``True`` for filled (ADR-0012) — exactly the requested dimensions
        whenever the ink box's aspect ratio is inside FR-021's accepted band
        (AC-059).

    Raises:
        UnreadableImage: ``source`` is ``None``, missing, unreadable or not a
            decodable image (AC-008). Pillow's own exception never reaches the
            caller.
        SizeOutOfRange: a side is outside the supported range.
        ImageNeedsManualCrop: the ink bounding box's aspect ratio differs from
            the grid's by more than 2x, so fitting it would throw away more than
            half the picture (AC-076, FR-021).

    The order below is ADR-0022's, not a local choice
    -------------------------------------------------
    ``validate_extent -> load_greyscale -> ink_bounding_box -> aspect guard ->
    trim -> binarize -> to_grid``. Two things about it are load-bearing:

    * **The box is computed and judged before it is applied.** Finding a
      bounding box reads pixels and writes nothing, so a refused request is
      refused with no crop of any kind having run — not the trim, not the
      aspect crop, not the resize, not the dither, and nothing downstream of
      any of them. That is EC-007's guarantee, and guarding after the trim had
      been applied would break it.
    * **The extent judged is the ink box, never the file** (CON-012, ADR-0022/R3
      as revised 2026-09-01). Blank margin is not the user's picture, and
      measuring it misstated what survives the crop by up to 45 points on this
      project's own corpus.

    The per-side range is still checked before the file is touched at all, so an
    out-of-range request pays for nothing. A **refused** request, though, now
    pays for one decode: the ink box is not derivable from a file header, so the
    cheap ``probe_extent`` path is gone (see the module docstring — this cost is
    the ADR's decision, not an oversight). With it goes the header-vs-decode
    disagreement CARD-026 had to re-check for: no extent is now read from a
    header at all, and the guard and the crop below are handed the *same* extent
    — the ink box, ``box`` — so they cannot disagree about the shape being fitted.
    """
    if source is None:
        raise UnreadableImage(
            "image mode needs an --image PATH pointing at the picture to convert"
        )
    width, height = random_grid.validate_extent(width, height)
    greyscale = load_greyscale(source)
    box = ink_bounding_box(greyscale)
    validate_aspect_ratio(box[2] - box[0], box[3] - box[1], width, height)
    return convert(greyscale.crop(box), width, height)[0]


def _disagreement_cells(
    witnesses: tuple[list[list[bool]], ...] | None,
) -> list[tuple[int, int]]:
    """The cells the solver's two witnesses differ on, in reading order.

    Reimplemented here rather than imported from the orchestrator, which has
    the same walk for ADR-0024's repair: ADR-0007 forbids a capability module
    from reaching sideways or inward, and the precedent for the duplication is
    ``solver/propagate.py``'s ``mask_runs``. The witnesses arrive as a
    parameter for the same reason — COMP-003 asks COMP-005 nothing.

    Empty when the solve had fewer than two solutions in hand: a candidate the
    solver did not report ``MANY`` for has no ambiguity to locate, and a nudge
    only ever runs on one that it did.
    """
    if witnesses is None or len(witnesses) < 2:
        return []
    first, second = witnesses[0], witnesses[1]
    return [
        (row_index, column_index)
        for row_index, (first_row, second_row) in enumerate(
            zip(first, second, strict=True)
        )
        for column_index, (left, right) in enumerate(
            zip(first_row, second_row, strict=True)
        )
        if left != right
    ]


def _mask_cells(mask: list[list[bool]] | None) -> list[tuple[int, int]]:
    """The set cells of a grid-shaped mask, in reading order."""
    if not mask:
        return []
    return [
        (row_index, column_index)
        for row_index, row in enumerate(mask)
        for column_index, cell in enumerate(row)
        if cell
    ]


def _boundary_distances(rows: list[list[bool]]) -> list[list[int]]:
    """Chebyshev distance from every cell to the nearest differently-valued one.

    ``1`` means the cell sits on an edge of the ink — it touches paper if it is
    ink, or ink if it is paper, diagonals included. Larger means buried: the
    middle of a solid block, or the middle of an empty margin.

    Computed as two multi-source breadth-first searches over the
    eight-neighbourhood (one from every filled cell, one from every empty one)
    rather than by scanning outward from each candidate. On an open grid an
    eight-connected BFS step *is* a Chebyshev step, so the two agree exactly,
    and this costs one pass over the grid instead of one per candidate — which
    matters because the fallback region can be the whole grid (CARD-096
    measured an undecided mask covering a median 35% of the cells, and 100% of
    them in the worst case).

    A grid with no cell of the opposite value — a blank or solid conversion —
    has no boundary anywhere, so every cell gets the same unreachable sentinel
    and :func:`next_nudge_cell`'s (row, column) tie-break carries the whole
    choice.
    """
    height = len(rows)
    width = len(rows[0]) if height else 0
    unreachable = height * width + 1
    distances = [[unreachable] * width for _ in range(height)]
    for value in (True, False):
        # Distance to the nearest cell holding `value`, which is what the cells
        # holding `not value` need.
        seen = [[unreachable] * width for _ in range(height)]
        frontier = [
            (row, column)
            for row in range(height)
            for column in range(width)
            if rows[row][column] is value
        ]
        for row, column in frontier:
            seen[row][column] = 0
        depth = 0
        while frontier:
            depth += 1
            following: list[tuple[int, int]] = []
            for row, column in frontier:
                for next_row in range(max(0, row - 1), min(height, row + 2)):
                    for next_column in range(
                        max(0, column - 1), min(width, column + 2)
                    ):
                        if seen[next_row][next_column] != unreachable:
                            continue
                        seen[next_row][next_column] = depth
                        following.append((next_row, next_column))
            frontier = following
        for row in range(height):
            for column in range(width):
                if rows[row][column] is not value:
                    distances[row][column] = seen[row][column]
    return distances


def next_nudge_cell(
    grid: list[list[bool]],
    flipped: Iterable[tuple[int, int]],
    *,
    witnesses: tuple[list[list[bool]], ...] | None,
    undecided_mask: list[list[bool]] | None,
) -> tuple[int, int] | None:
    """The one cell the next nudge attempt adds, or ``None``.

    The mechanism half of FR-013 (the policy half is COMP-002's bounded loop),
    and the whole of what CARD-075 replaced. A pure function of the grid the
    previous attempt was judged on and what the solver reported about it: no
    rng, no clock, no count, no module state (ADR-0015, INV-003).

    Where the candidates come from
    ------------------------------
    The cells where the solver's **two witnesses disagree**, minus the ones
    already flipped; and when that holds nothing left, the cells of the
    **undecided mask**, minus the same. Two regions in one walk, the same shape
    as ``orchestrator.repair_candidate``'s, so neither can be dead.

    The order is the point, and it is measured rather than guessed. CARD-096
    took the original conversion of every picture image mode abandons: the two
    witnesses disagreed on **4 cells in 27 of 34** of them — a single 2x2 block
    that can be drawn either way — while the undecided mask covered a median
    **35%** of the grid and, at worst, all of it. The disagreement set *is* the
    ambiguity the clues cannot resolve; the mask is merely everywhere line
    logic had not finished, which at that size is another guess.

    Why one cell from the *previous* attempt, not n cells from the first
    -------------------------------------------------------------------
    ``grid`` is the grid the previous attempt was judged on — the original
    conversion for attempt 1 — and ``witnesses``/``undecided_mask`` are that
    grid's. Flipping one cell of an ambiguous block usually exposes the *next*
    ambiguity somewhere the original disagreement set never contained, so a set
    chosen once from the conversion runs out of useful cells almost
    immediately. Measured on the 36 conversions dithering fails today, cap 5,
    both variants nested and flipping exactly *n* cells of the picture:
    choosing once rescued **9**, re-reading the solver each attempt rescued
    **19** (CARD-096). The heuristic this replaced rescued **0**.

    The ranking
    -----------
    Within whichever region supplied the candidates:

    1. Chebyshev distance to the nearest differently-valued cell, ascending
       (:func:`_boundary_distances`) — the edge of the ink first. A flip buried
       in a solid expanse splits a run in two or plants a stray dot, changing
       the picture more than it changes the puzzle; a flip on a boundary moves
       a line the clues are already arguing about.
    2. row, then column, so the answer is fully determined.

    Args:
        grid: The grid the previous attempt was judged on, in the ADR-0012
            boundary representation. Read for the ranking only — the cell is
            applied to the *original* conversion by :func:`nudge`.
        flipped: The cells already changed from the original conversion.
            Excluded from the candidates, which is what makes the attempts
            nest: no attempt can undo an earlier one (EC-014).
        witnesses: The two solutions the solver reported for ``grid``, or
            ``None`` when it reported fewer than two.
        undecided_mask: The cells line logic left undecided on ``grid``, or
            ``None``.

    Returns:
        A ``(row, column)`` pair, or ``None`` when neither region holds an
        unflipped cell. ``None`` is a real outcome, not an error: the attempt
        then has nothing to add and returns no candidate, while POL-002's
        counter still advances, so the cap and POL-003's report are reached
        exactly as they were before.
    """
    rows = [[bool(cell) for cell in row] for row in grid]
    height = len(rows)
    width = len(rows[0]) if height else 0
    if height == 0 or width == 0:
        return None
    already = set(flipped)
    distances = _boundary_distances(rows)

    def inside(cell: tuple[int, int]) -> bool:
        return 0 <= cell[0] < height and 0 <= cell[1] < width

    for region in (
        _disagreement_cells(witnesses),
        _mask_cells(undecided_mask),
    ):
        candidates = [
            cell for cell in region if cell not in already and inside(cell)
        ]
        if not candidates:
            continue
        return min(
            candidates, key=lambda cell: (distances[cell[0]][cell[1]], cell)
        )
    return None


def nudge(
    original: list[list[bool]], cells: Iterable[tuple[int, int]]
) -> list[list[bool]]:
    """POL-002's pixel nudge: ``original`` with exactly ``cells`` flipped.

    Deliberately the dumbest half of the mechanism. Every attempt nudges the
    *original conversion* rather than the previous attempt's grid, so the
    caller passes attempt *n − 1*'s cells plus the one
    :func:`next_nudge_cell` just chose, and the nesting FR-013 promises — after
    *n* attempts exactly *n* pixels of the user's picture have changed, and no
    earlier edit has been undone — follows from that arithmetic instead of from
    a ranking that has to be stable. It also keeps POL-003 honest at the cap:
    "stops altering the image" is observable as "the grid is the conversion
    plus at most five pixels", not "the grid has drifted somewhere unknown".

    The argument is never mutated, so the run's original conversion stays
    available for the next attempt and for the failure message.

    Args:
        original: The conversion the uploaded picture produced, in the ADR-0012
            boundary representation.
        cells: The cells to flip — distinct, and inside the grid.

    Returns:
        A fresh row-major ``list[list[bool]]`` of the same dimensions, with
        exactly ``cells`` flipped.

    Raises:
        ValueError: A cell repeats, or lies outside the grid. Either would
            quietly break the "differs in exactly *n* cells" promise — flipping
            one cell twice returns it to its original value — so both are
            wiring bugs in the caller rather than domain outcomes, the same
            reasoning ``_source_arguments``' own ``ValueError`` follows.
    """
    nudged = [[bool(cell) for cell in row] for row in original]
    height = len(nudged)
    seen: set[tuple[int, int]] = set()
    for cell in cells:
        row, column = cell
        if not (0 <= row < height and 0 <= column < len(nudged[row])):
            raise ValueError(f"nudge cell {cell!r} is outside the grid")
        if cell in seen:
            raise ValueError(f"nudge cell {cell!r} was given twice")
        seen.add(cell)
        nudged[row][column] = not nudged[row][column]
    return nudged
