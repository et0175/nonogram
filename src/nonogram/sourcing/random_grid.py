"""COMP-003 / CAP-001 — the random source of a solution grid (FR-001, FR-004).

Three decisions shape this module.

*Boundary representation* (ADR-0012): a sourced grid is a plain
``list[list[bool]]`` — row-major, ``True`` meaning a filled (black) cell. The
solver's int-bitmask representation is its own internal business; nothing here
knows about it, which is what keeps the sourcing seam and the export boundary
(EC-002) reasoning about one simple, JSON-native structure.

*Validation placement* (ADR-0010): the supported range — **each side** 10..30
cells inclusive (CON-011, AC-069, AC-070) — and the valid density range
(AC-011) are rules about the Puzzle domain, not about argument syntax, so they
live here and raise the ``nonogram.errors`` types. This module is the single
normative statement of the range: ``library.generate`` and ``image.generate``
both delegate to :func:`validate_extent` rather than restating it (ADR-0022/R2).
The CLI only turns those errors into a message and an exit code; a ``40x20``
request parses fine at the adapter and is rejected here.

*A grid is a rectangle* (ADR-0022/R1, FR-018/FR-019): extent crosses this
module's boundary as a ``(width, height)`` pair and never as one scalar. The
two sides are validated independently — a request may be legal on one and not
the other, and the error says which — so nothing here can silently treat the
larger side as "the size".

*A half-stated extent is completed by the source, not by an assumption*
(FR-023, ADR-0022/R4, CARD-033): a bare ``--size N`` states one number and
leaves the shape open, so :func:`derive_extent` reads N as the grid's **longer**
side and derives the other as ``round(N * short/long)`` of whatever ratio the
mode's :func:`source_shape` reports. It lives here for the same reason
:func:`validate_extent` does — it is one rule about extents, stated once, with
``library`` and ``image`` delegating rather than restating — even though the
*shapes* it is fed come from those modules.

*Injected randomness* (ADR-0015, guardrail G-4): every draw goes through a
``random.Random`` the caller passes in. This module never touches the
module-level ``random`` functions, so the same seed plus the same extent and
density reproduces the same grid — the seam CARD-005's regenerate loop and
CARD-004's property test rely on for determinism.

Density accuracy (ADR-0003): the tolerance is ±3 percentage points, and it has
to hold at the smallest supported grid. At 10x10 a per-cell Bernoulli draw at
p=0.30 has a standard deviation of ~4.6 filled cells (~4.6 points), so roughly
a third of such grids would land outside the band — the retry loop would be
carrying an accuracy problem that belongs to the sampler. So the exact target
count of filled cells is computed once and its positions are shuffled: the only
error left is the rounding of a fractional cell count, at most ``0.5 / cells``
(half a percentage point even at 10x10), well inside the band by construction
rather than on average.
"""

from __future__ import annotations

import random

from nonogram.errors import InvalidDensity, SizeOutOfRange, SizeTooSmallForSource

__all__ = [
    "DENSITY_TOLERANCE_POINTS",
    "MAX_DENSITY",
    "MAX_SIZE",
    "MIN_DENSITY",
    "MIN_SIZE",
    "density_of",
    "derive_extent",
    "filled_target",
    "generate",
    "source_shape",
    "validate_density",
    "validate_extent",
]

#: Supported length of **one grid side**, inclusive on both ends (FR-019,
#: NFR-001). The bound is per side, not per grid: a 30x12 grid is as legal as a
#: 12x12 one. CON-011 caps this at 30, and the reason is print legibility rather
#: than solver cost: past about 30 cells a side the printed cell drops under
#: ~6 mm on a sheet of paper (NFR-005) and stops being comfortable to mark by
#: hand.
MIN_SIZE = 10
MAX_SIZE = 30

#: Valid requested density, in percent, inclusive on both ends (FR-004): 0
#: yields an all-empty grid and 100 an all-filled one. Both are degenerate
#: puzzles that later pipeline stages (uniqueness, difficulty) will reject on
#: their own terms — they are not *invalid input*, which is all this module
#: judges.
MIN_DENSITY = 0
MAX_DENSITY = 100

#: ADR-0003: a generated grid honours the requested density when its filled
#: fraction is within this many percentage points of the request. Exposed here
#: because it is a property of the sampler's contract; CARD-005's regenerate
#: loop is expected to read it rather than restate the constant.
DENSITY_TOLERANCE_POINTS = 3


def _validate_side(length: int | None, side: str) -> int:
    """Return ``length`` if it is a supported side, else raise, naming ``side``.

    Private on purpose (ADR-0022/R1): a *public* one-integer validator would be
    a supported way to keep reasoning about a grid as one number, and half an
    extent is not a thing the model validates. :func:`validate_extent` is the
    only public statement of this rule, and this is the only message format.
    """
    if length is None or not MIN_SIZE <= length <= MAX_SIZE:
        raise SizeOutOfRange(
            f"grid {side} must be between {MIN_SIZE} and {MAX_SIZE} inclusive, "
            f"got {length!r}"
        )
    return length


def validate_extent(width: int | None, height: int | None) -> tuple[int, int]:
    """Return ``(width, height)`` if both sides are supported, else raise.

    The domain rule behind AC-069 (31x30 rejected) and AC-070 (30x9 rejected),
    and the single definition every source mode delegates to (ADR-0022/R2). Kept
    callable as a pure function so those criteria are testable without argv
    (ADR-0010): the CLI parses the ``--size N``/``--size NxM`` token and applies
    no bound of its own.

    Each side is judged **independently**, so a request that is legal on one
    axis and not the other is still refused, and the message names which axis is
    at fault. Width is judged first, so a request out of range on both sides
    reports its width — an order, not a preference, pinned here because two
    equally-true messages would otherwise vary with an implementation detail.
    """
    return _validate_side(width, "width"), _validate_side(height, "height")


def source_shape() -> tuple[int, int]:
    """The random source's own shape — it has none, so a square (FR-023).

    Every mode answers this question so that a bare ``--size N`` can be
    completed from *the source's* proportions rather than from an assumption
    (ADR-0022/R4). The random source is the mode with nothing to answer with: a
    draw at a requested density has no subject, no framing and no orientation,
    so the only honest ratio it can report is 1:1.

    ``(1, 1)`` and not ``(MIN_SIZE, MIN_SIZE)`` or ``(MAX_SIZE, MAX_SIZE)``:
    only the *ratio* of the pair is read (:func:`derive_extent` divides the
    shorter by the longer), so the unit square is the smallest truthful way to
    say "square". Returning a square here is what makes "random stays N x N"
    fall out of the same rule the other two modes follow, rather than being a
    branch in the derivation (CARD-033 guardrail G-2).

    Returns:
        ``(1, 1)`` — a square, in the same ``(width, height)`` pixel-extent
        shape ``library.source_shape`` and ``image.source_shape`` return.
    """
    return (1, 1)


def _keeps_half(
    source_width: int, source_height: int, width: int, height: int
) -> bool:
    """Would fitting a ``source_width`` x ``source_height`` source to this grid
    keep at least half of it?

    FR-021/CON-012's criterion, in exact integers: a centred crop to the grid's
    ratio retains ``min(r_src, r_tgt) / max(r_src, r_tgt)`` with ``r =
    width / height``, so "keeps at least half" is ``2 * kept >= whole`` after
    cross-multiplication, with the boundary inclusive.

    Deliberately a **native reimplementation** of the arithmetic
    ``sourcing.image._retained`` performs, not an import of it: ``image``
    already imports this module for the shared range rule, so importing back
    would be a cycle, and ADR-0007 forbids two capability modules leaning on
    each other laterally in any case. The precedent is ``solver/propagate.py``'s
    ``mask_runs``, which reimplements one clue-encoding check rather than
    importing ``clues``. The two copies are cross-checked against each other
    from the test tree, where the import is legal.

    This is a *predicate*; it never raises and never crops. FR-021's refusal —
    its message, its error type and its ink-box subject — stays entirely in
    ``sourcing.image`` (CARD-033 guardrail G-4). What this card uses the
    criterion for is choosing which grid shape to *request*, one step earlier.
    """
    source_over_target = source_width * height
    target_over_source = source_height * width
    return 2 * min(source_over_target, target_over_source) >= max(
        source_over_target, target_over_source
    )


def _derived_extent(
    stated: int, source_width: int, source_height: int
) -> tuple[int, int]:
    """FR-023's arithmetic: ``stated`` on the source's longer axis, the other
    side ``round(stated * short / long)`` with :data:`MIN_SIZE` as a floor.

    Split out of :func:`derive_extent` so the shape rule can be read without the
    refusal, the validation and the messages around it — and so the ceiling
    search in :func:`_smallest_workable_size` runs the *same* arithmetic the
    real derivation does rather than a second copy of it.

    Two properties of the returned pair are structural rather than checked:

    * the longer side is exactly ``stated``, because ``short <= long`` makes
      ``round(stated * short / long) <= stated``. **There is no clamp at the
      top and there must never be one** — ``stated`` is already inside
      ``MIN_SIZE..MAX_SIZE`` when this is called, so an upper clamp could only
      ever fire by masking a defect in this line (ADR-0022/R4, guardrail G-3);
    * ``stated`` lands on the axis the *source* is longer on, so a portrait
      picture gets a portrait grid and a landscape one a landscape grid. A
      square source (``source_width == source_height``) takes the first branch
      and comes back square, which is the same answer either branch would give.

    The float division is exact where it matters. ``stated`` is at most 30 and
    the products involved are far inside a double's 53-bit integer range, so the
    only inputs whose quotient is not exactly representable round to the same
    integer either way; a quotient that is *exactly* a half-integer is
    representable exactly, and Python's ``round`` breaks that tie to even. The
    tie is pinned by the property test rather than left to be discovered.
    """
    shorter_edge = min(source_width, source_height)
    longer_edge = max(source_width, source_height)
    derived = max(MIN_SIZE, round(stated * shorter_edge / longer_edge))
    if source_width >= source_height:
        return stated, derived
    return derived, stated


def _smallest_workable_size(source_width: int, source_height: int) -> int | None:
    """The smallest bare ``--size N`` this source can be fitted at, if any.

    Searched over ``MIN_SIZE..MAX_SIZE`` with the same two helpers the real
    derivation uses, rather than solved algebraically: the closed form
    (``ceil(MIN_SIZE * long / (2 * short))``) is one rearrangement away from
    being subtly wrong at the boundary, and the search is obviously right.

    Returns:
        The smallest supported ``N``, or ``None`` when even :data:`MAX_SIZE`
        cannot follow this source — which happens exactly when the source is
        more elongated than ``MAX_SIZE / 5 : 1``, i.e. 6:1.
    """
    for candidate in range(MIN_SIZE, MAX_SIZE + 1):
        if _keeps_half(
            source_width,
            source_height,
            *_derived_extent(candidate, source_width, source_height),
        ):
            return candidate
    return None


def derive_extent(
    width: int | None,
    height: int | None,
    source_width: int,
    source_height: int,
) -> tuple[int, int]:
    """Complete a half-stated extent from the source's own shape (FR-023).

    The domain rule behind ADR-0022/R4, and the counterpart of
    :func:`validate_extent`: that function judges an extent the user gave in
    full, this one *finishes* one they gave half of. A bare ``--size N`` reaches
    the domain as a pair with exactly one side filled in, and this turns it into
    the two numbers the grid actually has.

    The rule, in one sentence: **N is the grid's longer side, and the shorter
    one is ``round(N * short/long)`` of the source's own ratio, floored at
    :data:`MIN_SIZE` and never capped at the top.**

    Why the longer side is the load-bearing half of that (ADR-0022's own
    argument, restated because this is the code it constrains): with ``N`` as
    the longer side the derived side is ``<= N <= MAX_SIZE`` *by construction*,
    so nothing ever needs clamping at the top — and a top clamp would crop
    content, which is the harm this whole line of work exists to prevent.

    The bottom clamp is the one place the source cannot be followed, and it is
    where the refusal lives. Holding the short side at :data:`MIN_SIZE` while
    the source goes on getting narrower means the grid stops tracking the
    source, so past some elongation the fit would discard more than half the
    picture — CON-012's line. That point is exactly ``N/5 : 1`` (2:1 at
    ``--size 10``, 4:1 at ``--size 20``, 6:1 at ``--size 30``), and it is exact
    arithmetic rather than a sampled figure: at the clamp the grid's ratio is
    ``MIN_SIZE : N``, and half-retention against a source of ratio
    ``short : long`` is ``2 * N * short >= MIN_SIZE * long``.

    Beyond it the request is **refused rather than silently clamped**, and the
    message names the smallest ``--size N`` that would take this source. It does
    *not* reuse FR-021's "crop the picture yourself" advice, because cropping is
    not what fixes this: a larger ``N`` is (see
    :class:`~nonogram.errors.SizeTooSmallForSource`).

    Args:
        width: The requested grid width, or ``None`` when the ``--size`` token
            stated only one number.
        height: The requested grid height, same.
        source_width: The source's own width, in pixels — the ink bounding box
            for image mode (FR-022), the template's own extent for library
            mode, the unit square for random mode. Whatever the caller's
            :func:`source_shape` reported.
        source_height: The source's own height, same.

    Returns:
        The ``(width, height)`` pair the grid actually has, both sides inside
        ``MIN_SIZE..MAX_SIZE``.

    Raises:
        SizeOutOfRange: neither side was stated, both were, or the stated one is
            outside ``MIN_SIZE..MAX_SIZE``. The first two are caller bugs
            expressed as the domain error the caller would have got anyway —
            :func:`validate_extent` is the only public statement of the range
            and the only message format for it (ADR-0022/R2).
        SizeTooSmallForSource: the source is more elongated than ``N/5 : 1``, so
            the derived grid would keep less than half of it. A subclass of
            ``SizeOutOfRange``; its message names the smallest ``N`` that works.
        ValueError: the reported source shape has a non-positive axis. A wiring
            bug in the caller — every :func:`source_shape` is contracted to
            return a real extent — and so deliberately not a domain error.
    """
    if (width is None) == (height is None):
        # Both stated is an explicit ``NxM``, which needs no completing, and
        # neither stated is ``--size`` omitted. Either way the caller should not
        # have come here; both are answered by the shared validator, so this
        # cannot invent a second message for a range the domain states once.
        return validate_extent(width, height)
    if source_width <= 0 or source_height <= 0:
        raise ValueError(
            "a source's own shape has a positive extent on both axes, got "
            f"{source_width}x{source_height}"
        )

    stated = width if width is not None else height
    # The stated number is a grid side and faces the same range rule as any
    # other; validating it as a square is the same test, because the derived
    # side is between MIN_SIZE and ``stated`` by construction.
    validate_extent(stated, stated)

    extent = _derived_extent(stated, source_width, source_height)
    if _keeps_half(source_width, source_height, *extent):
        return validate_extent(*extent)

    smallest = _smallest_workable_size(source_width, source_height)
    unclamped = round(
        stated * min(source_width, source_height)
        / max(source_width, source_height)
    )
    if smallest is not None:
        remedy = (
            f"Ask for --size {smallest} or larger — counter-intuitively, a "
            "LARGER puzzle accepts a picture that a smaller one refuses, "
            "because its shorter side has further to fall before it reaches "
            f"the {MIN_SIZE}-cell floor. Cropping the picture is not what "
            "fixes this; a different --size is, or stating both sides yourself "
            "as --size WxH."
        )
    else:
        remedy = (
            f"No supported --size can follow it: even --size {MAX_SIZE}, the "
            f"largest, reaches only {MAX_SIZE // 5}:1. Crop the picture to "
            "something less elongated first, or state both sides yourself as "
            "--size WxH."
        )
    raise SizeTooSmallForSource(
        f"a {source_width}x{source_height} source is too elongated to follow at "
        f"--size {stated}: the grid's shorter side would have to be "
        f"{unclamped} cells, under the {MIN_SIZE}-cell minimum, and holding it "
        f"at {MIN_SIZE} would discard more than half the picture. {remedy}"
    )


def validate_density(density: int | None) -> int:
    """Return ``density`` if it is a valid percentage, else raise.

    Domain rule behind AC-011 (150% rejected), same placement rationale as
    :func:`validate_extent`.
    """
    if density is None or not MIN_DENSITY <= density <= MAX_DENSITY:
        raise InvalidDensity(
            f"density must be a percentage between {MIN_DENSITY} and "
            f"{MAX_DENSITY} inclusive, got {density!r}"
        )
    return density


def filled_target(width: int, height: int, density: int) -> int:
    """How many cells a ``width``x``height`` grid at ``density`` percent fills.

    The exact count, rounded to the nearest whole cell — the reason the
    sampler's density error is bounded by rounding alone (ADR-0003). Assumes
    validated arguments; :func:`generate` validates before calling it.
    """
    return round(width * height * density / 100)


def density_of(grid: list[list[bool]]) -> float:
    """The filled fraction of ``grid``, in percentage points.

    The measurement side of ADR-0003's tolerance: the acceptance check that
    compares this against the request is one subtraction, so both the sampler's
    tests and the regenerate loop can express the rule the same way.
    """
    cells = sum(len(row) for row in grid)
    if cells == 0:
        return 0.0
    return 100.0 * sum(cell for row in grid for cell in row) / cells


def generate(
    width: int | None,
    height: int | None,
    density: int | None,
    rng: random.Random,
) -> list[list[bool]]:
    """Draw one random ``width``x``height`` grid at ~``density`` percent.

    Args:
        width: Grid width in cells; must be within ``MIN_SIZE..MAX_SIZE``.
        height: Grid height in cells; the same range, judged separately — the
            random source has no shape of its own, so the pair it is handed is
            the pair it draws (ADR-0022/R1).
        density: Requested share of filled cells in percent, ``0..100``.
        rng: The run's random source (ADR-0015). Required, not defaulted: a
            default would quietly reintroduce global randomness and with it
            every non-reproducible run this seam exists to prevent.

    Returns:
        A row-major ``list[list[bool]]`` of ``height`` rows of ``width`` cells,
        ``True`` for filled (ADR-0012). The filled fraction is within
        ``DENSITY_TOLERANCE_POINTS`` of ``density`` for every supported extent.

    Raises:
        SizeOutOfRange: a side is outside the supported range (AC-069/AC-070).
        InvalidDensity: ``density`` is not a valid percentage (AC-011).

    Both validations run before anything is drawn, so a rejected request
    consumes no randomness — two invalid calls followed by a valid one produce
    the same grid a single valid call would.
    """
    width, height = validate_extent(width, height)
    density = validate_density(density)

    cells = width * height
    filled = filled_target(width, height, density)
    # Exact count, then shuffle the positions: the filled total is fixed before
    # any draw, so the only density error is the rounding above (ADR-0003).
    flat = [True] * filled + [False] * (cells - filled)
    rng.shuffle(flat)
    return [flat[offset : offset + width] for offset in range(0, cells, width)]
