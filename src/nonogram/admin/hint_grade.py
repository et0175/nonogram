"""The admin solve page's hint grade (CARD-484): each cell's solver rung.

A module of its own, not a method of the puzzle store: ``puzzle_review.py``
enters the solver in exactly one place, its uniqueness gate
(``test_there_is_exactly_one_solver_call_site_in_the_store``), and this solve
is a read for the page that stores nothing.
"""

from __future__ import annotations

import logging
import time
from typing import List, Optional

from nonogram.clues import compute_clues
from nonogram.errors import SolverTimeout
from nonogram.solver import RUNG_ORDER, solve

_log = logging.getLogger(__name__)


#: CARD-484 G-4: how long the solve page may spend grading a puzzle's cells
#: for the hint before it opens without the grade. The page must never wait
#: on a hard puzzle for more than about 2 s; the solver's cooperative check
#: fires within one propagation sweep past this.
HINT_GRADE_DEADLINE_SECONDS = 1.5


def hint_rungs(
    grid: List[List[bool]], *, deadline_seconds: Optional[float] = None
) -> Optional[List[List[Optional[int]]]]:
    """Every cell's ADR-0029 rung as its index in ``RUNG_ORDER``, or ``None``.

    The admin solve page's hint grade (CARD-484, owner's decision 2026-11-19:
    solved when the page opens, never stored — no column, no migration). One
    fresh :func:`~nonogram.solver.solve` of the grid's clues, as the re-grade
    batch runs one; the tags are a pure function of the clue set
    (ADR-0029/R3, R5), so they are the tags the verifying solve recorded.
    A cell no rung settled (the search guessed it) is ``None`` in the grid.

    Returns ``None`` — and the page hints row-major, as before — when the
    solve passes ``deadline_seconds`` (default
    :data:`HINT_GRADE_DEADLINE_SECONDS`, read at call time), the solve fails,
    or the clue set is not uniquely solvable, which has no grade (ADR-0029/R5).
    """
    if deadline_seconds is None:
        deadline_seconds = HINT_GRADE_DEADLINE_SECONDS
    row_clues, column_clues = compute_clues(grid)
    try:
        result = solve(row_clues, column_clues, deadline=time.monotonic() + deadline_seconds)
    except SolverTimeout:
        _log.info(
            "hint grade skipped: the solve passed its %.1f s page-open deadline;"
            " the page hints row-major", deadline_seconds)
        return None
    except Exception:  # card item 3: a failed grade degrades, the page still opens
        _log.exception("hint grade failed; the page hints row-major")
        return None
    if not result.is_unique:
        # ADR-0032/R1 says a stored puzzle is unique; one that is not is worth a line.
        _log.warning("hint grade skipped: the clue set is not uniquely solvable")
        return None
    rank = {name: index for index, name in enumerate(RUNG_ORDER)}
    return [[None if tag is None else rank[tag] for tag in row] for row in result.rung_tags]
