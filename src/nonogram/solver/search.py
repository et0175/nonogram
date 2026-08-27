"""COMP-005 search — counting solutions with fail-fast (ADR-0009, FR-006).

The public entry point is :func:`solve`. It takes clues in CARD-002's boundary
type and answers the one question CAP-003 exists to answer: does this clue set
have no solution, exactly one, or more than one?

Shape of the search (ADR-0009)
------------------------------
1. Run :func:`~nonogram.solver.propagate.propagate` over every line to a fixed
   point. Cells settled here are settled by line logic alone — the count at
   this first fixed point is FR-009's "cells solved before the first branch".
2. If the board is fully decided, that is the only solution reachable without
   guessing, and the search is over.
3. Otherwise pick the most constrained unknown cell, guess ``filled``, and
   propagate again; on contradiction, backtrack and guess ``empty``. Every
   guess is made on a cloned board, so undoing one is dropping a reference.
4. Stop the instant a *second* distinct solution is recorded (AC-017).

The search is iterative rather than recursive. Depth is bounded by the number
of guesses, which at the 50x50 upper bound (ADR-0001) can exceed CPython's
default recursion limit on a pathological puzzle; an explicit stack makes the
worst case a memory question instead of a ``RecursionError``.

Why counting stops at two (FR-006)
----------------------------------
``solution_count`` is ``0``, ``1`` or :data:`MANY` (``2``, read as ">= 2").
CARD-005 calls this on every candidate grid it generates, and the only thing
it ever asks is "is it exactly 1?" — enumerating the 40,000 solutions of a
sloppy clue set to answer "not 1" would make the uniqueness check the most
expensive part of generation for the least useful information.

Self-check before counting (CON-005)
------------------------------------
CON-005 is the model's one mandatory constraint and ADR-0009 is explicit that
a hand-rolled search is where a false-positive uniqueness verdict would hide.
So every completed board is re-encoded from its finished masks and compared
against the clues it was solved from before it is allowed to count as a
solution. A mismatch is a solver bug, not a puzzle outcome, so it raises
rather than being quietly discarded: a wrong answer that crashes is
recoverable, a wrong answer that looks right is what CON-005 forbids.

That re-encoding is done natively (``propagate.mask_runs``) rather than
through ``clues.encode_line``, even though the grid is complete by then and
CARD-002's function would be safe on it. ADR-0007 forbids lateral imports
between capability modules, and ``clues`` is COMP-004's capability, not a
shared kernel — ``tests/test_cli.py`` enforces that on every module in the
package. The solver consumes the clue *contract* (the boundary tuples of
ADR-0012) without importing the clue *module*. Independence from the solver's
own code is what the EC-001 property test provides, and it does cross-check
against ``clues.compute_clues`` from outside.

Out of scope here (guardrail G-5): no difficulty scoring (CARD-009 consumes
:class:`SolveSignals`), no deadline enforcement (CARD-006 hooks ADR-0011's
check into the fixed-point and branch-node boundaries this search exposes),
no retry loop (CARD-005).
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from nonogram.solver.propagate import (
    Board,
    LineClue,
    canonical_clue,
    line_intersection,
    mask_runs,
    propagate,
)

__all__ = ["MANY", "SolveResult", "SolveSignals", "solve"]

Grid = list[list[bool]]
ClueSet = tuple[tuple[int, ...], ...]

#: The reported ``solution_count`` for a clue set with more than one solution.
#: The search stops here by design (AC-017), so the value means ">= 2" and
#: never "exactly 2".
MANY = 2


@dataclass(frozen=True, slots=True)
class SolveSignals:
    """The raw solver telemetry FR-009 scores and NFR-001 is measured by.

    Emitted now, scored never — guardrail G-5 puts the formula in CARD-009
    (ADR-0013). Recording them here is what stops that card having to reopen
    the search's control flow to instrument it.
    """

    #: Cells decided by line logic alone, before the first guess (ADR-0013
    #: normalises this against ``total_cells``). Equal to ``total_cells`` when
    #: the puzzle never needed a guess.
    line_logic_cells: int
    #: Cells in the grid — ADR-0013's size-relative denominator.
    total_cells: int
    #: How many times the search had to guess a cell because propagation
    #: stalled. ADR-0013's "backtracking amount" term.
    branch_nodes: int
    #: How many guesses ran straight into a contradiction. Distinct from
    #: ``branch_nodes``: a puzzle can branch a lot and never backtrack.
    backtracks: int
    #: Wall-clock seconds for the whole solve, from a monotonic clock.
    elapsed_seconds: float


@dataclass(frozen=True, slots=True)
class SolveResult:
    """What :func:`solve` answers: a count, a witness, and the signals."""

    #: ``0``, ``1``, or :data:`MANY` (``2``, meaning ">= 2").
    solution_count: int
    #: The solution grid in the ADR-0012 boundary type when
    #: ``solution_count == 1``; ``None`` when there is no solution. When there
    #: is more than one, this is the first solution found — a witness, not
    #: "the" solution, and callers gated on uniqueness must not use it.
    solution: Grid | None
    signals: SolveSignals

    @property
    def is_unique(self) -> bool:
        """Exactly one solution — the INV-002 gate CARD-005's loop retries on."""
        return self.solution_count == 1


def solve(row_clues: ClueSet, column_clues: ClueSet) -> SolveResult:
    """Count a clue set's solutions, stopping at two (FR-006).

    Args:
        row_clues: One clue tuple per row, top to bottom, in CARD-002's
            boundary type — ``(0,)`` for an empty line (AC-013).
        column_clues: One clue tuple per column, left to right.

    Returns:
        A :class:`SolveResult` whose ``solution_count`` is ``0`` (AC-016),
        ``1`` (AC-015) or :data:`MANY` (AC-017), carrying the solution grid
        when the count is 1 and the FR-009 signals either way.

    Raises:
        ValueError: the clue set is malformed — a run that is not a positive
            int, or the empty-line marker used alongside other runs. Not a
            domain outcome: an unsolvable puzzle is reported as
            ``solution_count = 0``, never as an exception.

    Pure (ADR-0007, guardrail G-2): a total function of its two arguments,
    with no filesystem, CLI, randomness or module state involved, which is why
    EC-001's property test needs no fixture at all.

    A ``nonogram.clues.Clues`` unpacks straight into the two arguments::

        result = solve(*compute_clues(grid))
    """
    started = time.perf_counter()

    rows = tuple(canonical_clue(clue) for clue in row_clues)
    columns = tuple(canonical_clue(clue) for clue in column_clues)
    height = len(rows)
    width = len(columns)
    total_cells = height * width

    def finish(count: int, solution: Grid | None, branches: int, backtracks: int,
               line_logic_cells: int) -> SolveResult:
        return SolveResult(
            solution_count=count,
            solution=solution,
            signals=SolveSignals(
                line_logic_cells=line_logic_cells,
                total_cells=total_cells,
                branch_nodes=branches,
                backtracks=backtracks,
                elapsed_seconds=time.perf_counter() - started,
            ),
        )

    # A solution's filled cells are counted once by the row clues and once by
    # the column clues, so unequal totals mean there is nothing to search for.
    # Only an early exit — the search below would reach the same verdict.
    if sum(sum(clue) for clue in rows) != sum(sum(clue) for clue in columns):
        return finish(0, None, 0, 0, 0)

    if total_cells == 0:
        # A grid with no cells: the empty grid is its only candidate, and it
        # is a solution exactly when every line's clue is the empty marker
        # (the sum check above has already established that). Handled here
        # because ``compute_clues`` cannot round-trip a zero-row grid's column
        # clues, so the verification below would misread this as a defect.
        return finish(1, [[] for _ in range(height)], 0, 0, 0)

    board = Board.blank(rows, columns)
    dirty_rows = [True] * height
    dirty_columns = [True] * width
    if not propagate(board, dirty_rows, dirty_columns):
        return finish(0, None, 0, 0, board.decided)

    # Everything settled up to here came from line logic alone (FR-009).
    line_logic_cells = board.decided

    solutions: list[Grid] = []
    branch_nodes = 0
    backtracks = 0

    if board.decided == total_cells:
        solutions.append(_verified_grid(board))
    else:
        # Each frame is a board that propagation has stalled on, the unknown
        # cell chosen to guess at, and the guesses not yet tried there.
        stack: list[tuple[Board, int, int, list[bool]]] = [_frame(board)]
        branch_nodes += 1
        while stack and len(solutions) < MANY:
            parent, row, column, remaining = stack[-1]
            if not remaining:
                stack.pop()
                continue
            # Popping from the end takes the better-supported value first
            # (see ``_frame``). Both values are always tried before the frame
            # is dropped, so the order is a speed choice, not a correctness
            # one — and being a fixed function of the board it keeps the whole
            # solve reproducible.
            guess = remaining.pop()

            child = parent.clone()
            child.assign(row, column, guess)
            dirty_rows = [False] * height
            dirty_columns = [False] * width
            dirty_rows[row] = True
            dirty_columns[column] = True

            if not propagate(child, dirty_rows, dirty_columns):
                backtracks += 1
                continue
            if child.decided == total_cells:
                solutions.append(_verified_grid(child))
                continue
            stack.append(_frame(child))
            branch_nodes += 1

    count = len(solutions)
    solution = solutions[0] if solutions else None
    return finish(count, solution, branch_nodes, backtracks, line_logic_cells)


def _frame(board: Board) -> tuple[Board, int, int, list[bool]]:
    """A search frame: a stalled board, the cell to guess at, and the guesses.

    The guesses are ordered by how much room each value leaves the two lines
    through the cell — the product of the placements the row still admits and
    the placements the column still admits, once the cell is forced that way.
    The better-supported value goes last so it is popped first, because a
    value that almost no placement of its own lines agrees with is unlikely to
    lead to a solution and likely to cost a deep descent to disprove.

    Both values are always tried, so this only reorders work; it cannot change
    the reported ``solution_count``. Two extra line DPs per branch node buy
    that ordering, which is cheap next to the propagation sweep a guess
    triggers.
    """
    row, column = _branch_cell(board)
    column_bit = 1 << column
    row_bit = 1 << row
    filled_support = _support(
        board.row_clues[row], board.width, board.row_filled[row] | column_bit,
        board.row_empty[row],
    ) * _support(
        board.column_clues[column], board.height,
        board.column_filled[column] | row_bit, board.column_empty[column],
    )
    empty_support = _support(
        board.row_clues[row], board.width, board.row_filled[row],
        board.row_empty[row] | column_bit,
    ) * _support(
        board.column_clues[column], board.height, board.column_filled[column],
        board.column_empty[column] | row_bit,
    )
    guesses = [False, True] if filled_support >= empty_support else [True, False]
    return board, row, column, guesses


def _support(runs: LineClue, length: int, known_filled: int, known_empty: int) -> int:
    """How many placements of ``runs`` survive the given knowledge; 0 if none."""
    deduced = line_intersection(runs, length, known_filled, known_empty)
    return 0 if deduced is None else deduced[2]


def _branch_cell(board: Board) -> tuple[int, int]:
    """The most constrained unknown cell: ``(row, column)`` (ADR-0009).

    "Most constrained" is measured by how many placements a line still admits,
    not by how many of its cells are unknown. Placement count is the line's
    actual remaining freedom: a 50-cell line with twenty unknown cells but
    only two possible placements is one guess away from being settled, while a
    line with four unknown cells and six placements is not. Propagation
    already computed and cached those counts, so the heuristic is a scan of
    two int lists rather than a re-run of the line DP.

    The cell chosen is the intersection of the least-free line with the
    least-free perpendicular line through it — so both of the lines a guess
    triggers propagation on are near-forced, which is what makes a wrong guess
    surface as a contradiction immediately instead of hundreds of levels deep.

    Ties break toward the lowest index, keeping the choice deterministic and
    the whole solve reproducible for a given clue set.

    Both orientations are considered, because a nearly-forced column
    constrains a cell exactly as much as a nearly-forced row does.
    """
    best_freedom = -1
    best_is_row = True
    best_index = -1

    for row in range(board.height):
        if board.width == (board.row_filled[row] | board.row_empty[row]).bit_count():
            continue  # fully decided: nothing here to branch on
        freedom = board.row_placements[row]
        if best_index < 0 or freedom < best_freedom:
            best_freedom = freedom
            best_is_row = True
            best_index = row
    for column in range(board.width):
        decided = (board.column_filled[column] | board.column_empty[column]).bit_count()
        if board.height == decided:
            continue
        freedom = board.column_placements[column]
        if best_index < 0 or freedom < best_freedom:
            best_freedom = freedom
            best_is_row = False
            best_index = column

    if best_index < 0:  # pragma: no cover - the caller checks for completion
        raise RuntimeError("no unknown cell to branch on: the board is complete")

    if best_is_row:
        unknown_bits = ~(board.row_filled[best_index] | board.row_empty[best_index])
        best_cell = -1
        best_cross = -1
        for column in range(board.width):
            if not (unknown_bits >> column) & 1:
                continue
            cross = board.column_placements[column]
            if best_cell < 0 or cross < best_cross:
                best_cell = column
                best_cross = cross
        return best_index, best_cell

    unknown_bits = ~(board.column_filled[best_index] | board.column_empty[best_index])
    best_cell = -1
    best_cross = -1
    for row in range(board.height):
        if not (unknown_bits >> row) & 1:
            continue
        cross = board.row_placements[row]
        if best_cell < 0 or cross < best_cross:
            best_cell = row
            best_cross = cross
    return best_cell, best_index


def _to_grid(board: Board) -> Grid:
    """A fully decided board in the ADR-0012 boundary type (``list[list[bool]]``).

    The bitmask-to-boundary seam ADR-0012 flags as the place off-by-one and
    bit-order bugs live, so it is one expression, used by exactly one caller,
    and covered directly by ``TestSolver_*`` round-trip tests.
    """
    return [
        [bool((board.row_filled[row] >> column) & 1) for column in range(board.width)]
        for row in range(board.height)
    ]


def _verified_grid(board: Board) -> Grid:
    """Convert a completed board to a grid, refusing to return a wrong one.

    The CON-005 backstop described in the module docstring: every line of the
    finished board is re-encoded from its mask and compared with the clue it
    was solved from, in *both* orientations, before the grid is handed back to
    be counted.

    This is not a tautology, which is the only reason it is worth its cost.
    The search reaches this point by way of the placement DP, its fixed-point
    sweep and the bitmask/boundary conversion; :func:`~nonogram.solver.propagate.mask_runs`
    walks the finished masks cell by cell and shares none of that machinery. A
    dropped fixed point, a bit-order slip in the conversion, or an off-by-one
    in a line's placement all show up here as a mismatch.

    Raises:
        RuntimeError: the completed grid does not encode back to the clues it
            was solved from. Unreachable unless the solver is broken, which is
            precisely why it is not silently swallowed.
    """
    for row in range(board.height):
        found = mask_runs(board.row_filled[row], board.width)
        if found != board.row_clues[row]:
            raise _defect("row", row, board.row_clues[row], found)
    for column in range(board.width):
        found = mask_runs(board.column_filled[column], board.height)
        if found != board.column_clues[column]:
            raise _defect("column", column, board.column_clues[column], found)
    return _to_grid(board)


def _defect(orientation: str, index: int, expected: LineClue, found: LineClue) -> RuntimeError:
    return RuntimeError(
        f"solver completed a grid whose {orientation} {index} encodes to "
        f"{found} but was solved from clue {expected}; this is a solver defect "
        f"(CON-005), not a puzzle outcome"
    )
