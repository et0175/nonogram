"""COMP-005 (Solver) — CAP-003 / FR-006: how many solutions does a clue set have?

The one question this package answers is uniqueness: given row and column
clues, are there ``0`` solutions, exactly ``1``, or more than one — with the
search stopping the instant a second one appears (AC-017), because that is
what makes CARD-005's retry loop able to afford a uniqueness check on every
candidate grid it generates.

Public surface (this is the whole API; everything else is internal)
-------------------------------------------------------------------
``solve(row_clues, column_clues, *, givens=None, deadline=None)``
                                    ->  :class:`SolveResult`
``SolveResult``                     the count, the witnesses, the first fixed
                                    point's undecided mask, the per-cell rung
                                    tags and the signals
``choose_givens(grid, row_clues, column_clues, *, cap, deadline=None)``
                                    ->  :data:`Givens`: which cells to reveal
                                    so that the clues have exactly one
                                    solution, or
                                    :class:`~nonogram.errors.GivenCellsCapExceeded`
``revealed_cells(givens)``          the revealed cells of a :data:`Givens` as
                                    ``(row, column, value)`` triples
``Givens``                          ``list[list[bool | None]]`` — a grid-shaped
                                    partial assignment
``SolveSignals``                    FR-009's raw difficulty inputs, plus
                                    ADR-0029's per-rung cell counts and the
                                    ordered list of rungs the solve used
``MANY``                            the ``solution_count`` meaning ">= 2"
``RUNG_ORDER`` and the three        ADR-0029's ladder, lowest rung first:
``RUNG_*`` names                    ``simple_overlap`` < ``line_dp`` <
                                    ``probe_contradiction``, each the fixed
                                    point of its technique. ``guess`` is not
                                    one of them — ADR-0025 keys that on
                                    ``branch_nodes``.

``deadline`` is ADR-0011's cooperative generation deadline: an absolute
:func:`time.monotonic` reading, computed once per generation *request* by the
orchestrator (COMP-002) and checked here at every propagation fixed point and
every branch node. Past it, :func:`solve` raises
:class:`nonogram.errors.SolverTimeout` rather than returning a verdict — a
timed-out solve has no answer, and INV-002 keeps the puzzle unexportable.
Omitting it (the default) runs to completion, however long that takes.

``givens`` is CARD-214's *seeded* count: a grid-shaped partial assignment
(``True`` filled, ``False`` empty, ``None`` unknown) seeded into the board
before the first propagation round, so ``solution_count`` becomes "solutions
consistent with the clues **and** these known cells". It is how a picture that
is not uniquely solvable can be made into a puzzle without changing a single
cell of it — the orchestrator's reveal policy asks :func:`choose_givens` which
cells, then re-verifies the answer with a fresh seeded :func:`solve`, because
uniqueness is never inferred from the fact that cells were revealed (the rule
ADR-0024/R1 makes for repairs). Omitting it (the default) is the question this
package has always answered, with byte-identical verdicts.

Boundary types only, at the edge (ADR-0012, guardrail G-3). Clues arrive as
CARD-002's ``tuple[tuple[int, ...], ...]``, a solution leaves as
``list[list[bool]]`` and a partial assignment crosses in and out as
``list[list[bool | None]]``. The int-bitmask-per-line representation the search
actually runs on lives in :mod:`nonogram.solver.propagate` and never crosses
this line, in either direction — ADR-0012's "Neutral" consequence asks that
clue tuples and grid bitmasks stay separate representations, and keeping the
bitmasks unexported is how that stays true as later cards call in.

Layout
------
``propagate``  line logic: the intersection of all placements of one clue,
               and the fixed-point sweep that feeds each deduced cell to the
               perpendicular line
``search``     branch-and-count on top of it: guess the most constrained
               unknown cell, backtrack on contradiction, stop at two solutions

Usage::

    from nonogram.clues import compute_clues
    from nonogram.solver import solve

    result = solve(*compute_clues(grid))
    if result.is_unique:
        ...  # result.solution is the grid, result.signals feeds CARD-009
"""

from __future__ import annotations

from nonogram.solver.propagate import (
    RUNG_LINE_DP,
    RUNG_ORDER,
    RUNG_PROBE_CONTRADICTION,
    RUNG_SIMPLE_OVERLAP,
    STRATEGY_GUESS,
)
from nonogram.solver.search import (
    MANY,
    Givens,
    RungTags,
    SolveResult,
    SolveSignals,
    choose_givens,
    revealed_cells,
    solve,
)

__all__ = [
    "MANY",
    "RUNG_LINE_DP",
    "RUNG_ORDER",
    "RUNG_PROBE_CONTRADICTION",
    "RUNG_SIMPLE_OVERLAP",
    "STRATEGY_GUESS",
    "Givens",
    "RungTags",
    "SolveResult",
    "SolveSignals",
    "choose_givens",
    "revealed_cells",
    "solve",
]
