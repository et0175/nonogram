"""COMP-005 (Solver) — CAP-003 / FR-006: how many solutions does a clue set have?

The one question this package answers is uniqueness: given row and column
clues, are there ``0`` solutions, exactly ``1``, or more than one — with the
search stopping the instant a second one appears (AC-017), because that is
what makes CARD-005's retry loop able to afford a uniqueness check on every
candidate grid it generates.

Public surface (this is the whole API; everything else is internal)
-------------------------------------------------------------------
``solve(row_clues, column_clues)``  ->  :class:`SolveResult`
``SolveResult``                     the count, the solution grid, the signals
``SolveSignals``                    FR-009's raw difficulty inputs
``MANY``                            the ``solution_count`` meaning ">= 2"

Boundary types only, at the edge (ADR-0012, guardrail G-3). Clues arrive as
CARD-002's ``tuple[tuple[int, ...], ...]`` and a solution leaves as
``list[list[bool]]``. The int-bitmask-per-line representation the search
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

from nonogram.solver.search import MANY, SolveResult, SolveSignals, solve

__all__ = ["MANY", "SolveResult", "SolveSignals", "solve"]
