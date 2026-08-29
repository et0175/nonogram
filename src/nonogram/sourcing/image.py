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

from nonogram.errors import UnreadableImage
from nonogram.sourcing import random_grid

__all__ = [
    "RESAMPLING",
    "binarize",
    "generate",
    "load_greyscale",
    "nudge",
    "nudge_cells",
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
