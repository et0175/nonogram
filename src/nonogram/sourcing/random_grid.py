"""COMP-003 / CAP-001 — the random source of a solution grid (FR-001, FR-004).

Three decisions shape this module.

*Boundary representation* (ADR-0012): a sourced grid is a plain
``list[list[bool]]`` — row-major, ``True`` meaning a filled (black) cell. The
solver's int-bitmask representation is its own internal business; nothing here
knows about it, which is what keeps the sourcing seam and the export boundary
(EC-002) reasoning about one simple, JSON-native structure.

*Validation placement* (ADR-0010): the supported size range — 10..30 cells a
side inclusive (CON-011, AC-003, AC-004) — and the valid density range
(AC-011) are rules about the Puzzle domain, not about argument syntax, so they
live here and raise the ``nonogram.errors`` types. This module is the single
normative statement of the range: ``library.generate`` and ``image.generate``
both delegate to :func:`validate_size` rather than restating it (ADR-0022/R2).
The CLI only turns those errors into a message and an exit code; a 60x60
request parses fine at the adapter and is rejected here.

*Injected randomness* (ADR-0015, guardrail G-4): every draw goes through a
``random.Random`` the caller passes in. This module never touches the
module-level ``random`` functions, so the same seed plus the same size and
density reproduces the same grid — the seam CARD-005's regenerate loop and
CARD-004's property test rely on for determinism.

Density accuracy (ADR-0003): the tolerance is ±3 percentage points, and it has
to hold at the smallest supported size. At 10x10 a per-cell Bernoulli draw at
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

from nonogram.errors import InvalidDensity, SizeOutOfRange

__all__ = [
    "DENSITY_TOLERANCE_POINTS",
    "MAX_DENSITY",
    "MAX_SIZE",
    "MIN_DENSITY",
    "MIN_SIZE",
    "density_of",
    "filled_target",
    "generate",
    "validate_density",
    "validate_size",
]

#: Supported square-grid edge lengths, inclusive on both ends (FR-019, NFR-001).
#: CON-011 caps this at 30, and the reason is print legibility rather than
#: solver cost: past about 30 cells a side the printed cell drops under ~6 mm
#: on a sheet of paper (NFR-005) and stops being comfortable to mark by hand.
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


def validate_size(size: int | None) -> int:
    """Return ``size`` if it is a supported edge length, else raise.

    Domain rule behind AC-003 (60x60 rejected) and AC-004 (9x9 rejected), kept
    callable as a pure function so those criteria are testable without argv
    (ADR-0010).
    """
    if size is None or not MIN_SIZE <= size <= MAX_SIZE:
        raise SizeOutOfRange(
            f"grid size must be between {MIN_SIZE} and {MAX_SIZE} inclusive, "
            f"got {size!r}"
        )
    return size


def validate_density(density: int | None) -> int:
    """Return ``density`` if it is a valid percentage, else raise.

    Domain rule behind AC-011 (150% rejected), same placement rationale as
    :func:`validate_size`.
    """
    if density is None or not MIN_DENSITY <= density <= MAX_DENSITY:
        raise InvalidDensity(
            f"density must be a percentage between {MIN_DENSITY} and "
            f"{MAX_DENSITY} inclusive, got {density!r}"
        )
    return density


def filled_target(size: int, density: int) -> int:
    """How many cells a ``size``x``size`` grid at ``density`` percent fills.

    The exact count, rounded to the nearest whole cell — the reason the
    sampler's density error is bounded by rounding alone (ADR-0003). Assumes
    validated arguments; :func:`generate` validates before calling it.
    """
    return round(size * size * density / 100)


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
    size: int | None,
    density: int | None,
    rng: random.Random,
) -> list[list[bool]]:
    """Draw one random ``size``x``size`` solution grid at ~``density`` percent.

    Args:
        size: Square grid edge length; must be within ``MIN_SIZE..MAX_SIZE``.
        density: Requested share of filled cells in percent, ``0..100``.
        rng: The run's random source (ADR-0015). Required, not defaulted: a
            default would quietly reintroduce global randomness and with it
            every non-reproducible run this seam exists to prevent.

    Returns:
        A row-major ``list[list[bool]]`` of ``size`` rows of ``size`` cells,
        ``True`` for filled (ADR-0012). The filled fraction is within
        ``DENSITY_TOLERANCE_POINTS`` of ``density`` for every supported size.

    Raises:
        SizeOutOfRange: ``size`` is outside the supported range (AC-003/AC-004).
        InvalidDensity: ``density`` is not a valid percentage (AC-011).

    Both validations run before anything is drawn, so a rejected request
    consumes no randomness — two invalid calls followed by a valid one produce
    the same grid a single valid call would.
    """
    size = validate_size(size)
    density = validate_density(density)

    cells = size * size
    filled = filled_target(size, density)
    # Exact count, then shuffle the positions: the filled total is fixed before
    # any draw, so the only density error is the rounding above (ADR-0003).
    flat = [True] * filled + [False] * (cells - filled)
    rng.shuffle(flat)
    return [flat[offset : offset + size] for offset in range(0, cells, size)]
