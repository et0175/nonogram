"""Convert images to grids and clues, for the admin panel.

Two thin delegations to the canonical modules — the ink-trim/dither conversion
in :mod:`nonogram.sourcing.image` and the run-length encoder in
:mod:`nonogram.clues`. Grading is deliberately *not* here: since CARD-049 the
admin generates image puzzles through ``orchestrator.generate``, and since
CARD-076 there is exactly one tier classifier in the package
(``nonogram.difficulty.classify``, ADR-0025/R2). See the note at the foot of
this module for what used to live there and why it is gone.
"""

import random
from typing import Tuple, List, Optional

try:
    from PIL import Image as PILImage
    import numpy as np
except ImportError:
    PILImage = None
    np = None

from nonogram import clues as nonogram_clues
from nonogram.errors import NonogramError
from nonogram.sourcing import image as sourcing_image


def image_to_grid(image_path: str, target_size: Tuple[int, int]) -> Optional[List[List[bool]]]:
    """Convert image to boolean grid (nonogram).

    Delegates to :mod:`nonogram.sourcing.image` — the same ink-bounding-box
    trim, aspect-preserving centre-crop to the grid's own ratio (ADR-0022/R3),
    and Floyd-Steinberg dithering that ``nonogram generate --mode image`` and
    ``nonogram serve`` use. A puzzle generated here from a given file now
    matches (rather than diverges from, as a previous bounding-box-only crop
    plus a plain resize used to) one generated from the same file through the
    CLI/web path — a plain resize squashes a non-square crop into the target
    square and drops thin detail (e.g. a bird's legs) that dithering keeps.

    Args:
        image_path: Path to image file
        target_size: Target (width, height) for grid

    Returns:
        List[List[bool]] grid where True = filled, False = empty
        Or None if conversion fails
    """
    if not PILImage or not np:
        return None

    width, height = target_size
    try:
        return sourcing_image.generate(image_path, width, height, random.Random())
    except NonogramError as e:
        print(f"Error converting image: {str(e)}")
        return None


def generate_clues(
    grid: List[List[bool]],
) -> Tuple[Tuple[Tuple[int, ...], ...], Tuple[Tuple[int, ...], ...]]:
    """Generate nonogram clues from grid.

    Delegates to :func:`nonogram.clues.compute_clues` — the canonical
    run-length encoder (ADR-0012) admin already calls correctly elsewhere
    (``app.py``'s ``clues.encode_line`` usage). A ragged ``grid`` raises
    ``ValueError`` (via that function's ``zip(..., strict=True)`` guard)
    instead of an uncontrolled ``IndexError``.

    Args:
        grid: List[List[bool]] where True = filled cell

    Returns:
        (row_clues, col_clues), each a tuple of per-line clue tuples
        (ADR-0012 boundary type — ``(0,)`` for an empty line, never ``()``).
    """
    computed = nonogram_clues.compute_clues(grid)
    return computed.rows, computed.columns


# ``create_puzzle_from_image`` lived here until CARD-076 and is gone.
#
# It derived a difficulty tier and score from the grid's *size alone*
# ((width + height) / 2, bucketed at 15 and 25) and returned a hardcoded
# ``strategies_used`` sample beside them. Both are ADR-0025/R2 violations: tier
# classification has exactly one implementation, in ``nonogram.difficulty``,
# taking ``(score, branch_nodes)`` from the one verifying solve — and a size is
# neither. Under ADR-0029 the claim was not merely unauthorised but wrong: which
# technique a puzzle needs is a fact about the puzzle, and a 30x30 that never
# leaves simple overlap is exactly as Easy as a 10x10 that never does.
#
# It is deleted rather than routed through the classifier because CARD-049 had
# already made it dead: ``admin/app.py`` generates image puzzles through
# ``orchestrator.generate`` (the same solver-verified pipeline
# ``nonogram generate --mode image`` runs) and stores the score and tier that
# pipeline produced. Nothing in ``src/`` called this function. Routing a
# second, unverified conversion through the real classifier would have kept a
# path that produces a grid nobody ever solved.
#
# ``image_to_grid`` and ``generate_clues`` above stay: they are thin delegations
# to ``nonogram.sourcing.image`` and ``nonogram.clues``, and they are called.
