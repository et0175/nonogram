"""COMP-005 line logic — the bitmask half of the solver (ADR-0009, ADR-0012).

This module owns two things and nothing else:

``line_intersection``
    The line solver. Given one line's clue, its length and what is already
    known about it, it returns the cells that are filled in *every* placement
    of that clue and the cells that are empty in every placement — i.e. the
    intersection of all consistent placements, which is exactly the deduction
    a human makes when they overlap a line's leftmost and rightmost fits.
``propagate``
    Applies ``line_intersection`` to every dirty row and column, feeding each
    newly decided cell back to the perpendicular line, until nothing changes
    (the fixed point ADR-0009 describes).

Representation (ADR-0012)
-------------------------
Every line is a pair of ints: ``filled`` and ``empty``, bit ``i`` set meaning
"cell ``i`` of this line is known filled / known empty". A cell whose bit is
set in neither is unknown; a cell set in both is a contradiction that this
module never constructs. Both orientations are kept in parallel — row masks
indexed by row with column bits, column masks indexed by column with row bits
— which is the "maintaining row and column masks in parallel" option ADR-0012
names, chosen over transposing the board on every pass because a propagation
step only ever touches the handful of cells it just decided.

Why the line logic is native and not built on ``nonogram.clues``
----------------------------------------------------------------
Both worktree notes on CARD-004 say it: ``clues.encode_line`` and
``clues.clue_matches_line`` are scoped to *complete* lines. They read any
falsy cell as empty, so a partially-known line — the only kind that exists
during propagation — is silently misread rather than rejected, and they
allocate a tuple per call in a loop that runs millions of times per generation
run. The three-valued reasoning below is therefore written natively against
the bitmasks, and so is the finished-line encoder ``mask_runs`` that ``search``
uses to re-check a completed grid — ADR-0007 forbids importing another
capability's module laterally in any case, so the solver consumes the clue
*contract* (ADR-0012's boundary tuples) without importing the clue *module*.
The EC-001 property test supplies the independent cross-check, from outside.

Purity (ADR-0007, guardrail G-2)
--------------------------------
No I/O, no clock, no randomness, no module-level mutable state. Every function
here is a total function of its arguments; ``propagate`` mutates only the
``Board`` it is handed.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["Board", "canonical_clue", "line_intersection", "mask_runs", "propagate"]

LineClue = tuple[int, ...]


def canonical_clue(clue: tuple[int, ...]) -> LineClue:
    """Normalise a clue to its run list: the empty-line marker becomes ``()``.

    ``clues.encode_line`` emits ``(0,)`` for a line with no filled cells
    (AC-013). The placement DP wants "a list of runs", and an empty line has
    zero runs, so the marker is stripped here — once, at the boundary — rather
    than special-cased inside the hot loop. A bare ``()`` is accepted as the
    same thing so a caller that dropped the marker is not silently misread as
    something else.

    Raises:
        ValueError: a run is not a positive integer. That is a malformed clue,
            i.e. a programming error at the call site, not a puzzle that
            happens to be unsolvable — reporting it as "0 solutions" would
            hide the bug behind a plausible-looking domain answer.
    """
    if clue == (0,) or clue == ():
        return ()
    for run in clue:
        if not isinstance(run, int) or isinstance(run, bool) or run <= 0:
            raise ValueError(
                f"malformed clue {clue!r}: runs must be positive ints, or the "
                f"single empty-line marker (0,)"
            )
    return tuple(clue)


def line_intersection(
    runs: LineClue,
    length: int,
    known_filled: int,
    known_empty: int,
) -> tuple[int, int, int] | None:
    """Deduce the cells every valid placement of ``runs`` agrees on.

    Args:
        runs: The line's clue in canonical form (see :func:`canonical_clue`) —
            positive run lengths, ``()`` for an empty line.
        length: Number of cells in the line.
        known_filled: Bitmask of cells already known to be filled.
        known_empty: Bitmask of cells already known to be empty.

    Returns:
        ``(filled, empty, placements)`` — the cells filled in *every*
        consistent placement, the cells empty in every consistent placement,
        and how many consistent placements there are. The two masks are
        supersets of the corresponding input mask, since a known cell is
        trivially agreed on by every placement consistent with it. ``None``
        when no placement of ``runs`` is consistent with what is known, which
        is a contradiction the caller must treat as "this branch has no
        solution".

    ``placements`` is the line's remaining freedom, and it is counted here
    because the same DP walk already visits every placement: it costs one
    addition per state and gives the search a far sharper "most constrained"
    measure than counting unknown cells does (a line with twenty unknown cells
    and two possible placements is nearly settled; one with four unknown cells
    and six placements is not).

    The algorithm is a DP over ``(position, run index)`` states. From each
    state a placement either leaves the current cell empty and moves on, or
    starts run ``index`` exactly here; every placement corresponds to exactly
    one path through those states, so OR-ing each transition's cell masks
    accumulates the union over all placements without ever enumerating them
    one by one (there can be astronomically many). A cell filled in every
    placement is then one that appears in the filled union and never in the
    empty union, and vice versa.

    The state space is ``length x (len(runs) + 1)`` — at most 50 x 26 for the
    largest supported grid — with O(1) work per state. It is evaluated bottom
    up, from the end of the line backwards, rather than as a memoised
    recursion: every transition reads a state strictly further along the line,
    so a plain reverse loop has them all in hand. That matters because this
    function is *the* hot path (ADR-0012's "millions of intersections per
    generation run"), and at these sizes CPython's per-call overhead for the
    recursive form costs several times the arithmetic it wraps.
    """
    if length < 0:
        raise ValueError(f"line length must be non-negative, got {length}")
    # Cheap impossibility check: the runs plus one mandatory gap between each
    # adjacent pair cannot be squeezed into the line.
    if sum(runs) + len(runs) - 1 > length:
        return None

    full = (1 << length) - 1
    if not runs:
        # An empty line: one placement, every cell empty — but only if nothing
        # is already known to be filled.
        return None if known_filled else (0, full, 1)
    if known_filled | known_empty == full:
        # The line is already fully decided, which happens constantly near the
        # leaves of the search. Checking the finished line against its clue
        # directly is a single pass, where the DP would be O(length x runs).
        return (known_filled, known_empty, 1) if mask_runs(known_filled, length) == runs else None

    run_count = len(runs)
    states = run_count + 1
    size = (length + 1) * states
    # Flat arrays indexed by ``pos * states + idx``: the union of filled cells,
    # the union of empty cells, and the number of placements, for the tail of
    # the line from ``pos`` on with runs ``idx..`` still to place. A count of
    # zero means that state admits no placement at all.
    union_filled = [0] * size
    union_empty = [0] * size
    counts = [0] * size

    # Base row (``pos == length``): the line is over, which is a valid
    # placement only if every run has been placed.
    counts[length * states + run_count] = 1

    # ``need[idx]`` cells are required to lay out runs ``idx..`` with their
    # mandatory gaps. A state with fewer cells left than that admits no
    # placement, so it is skipped entirely and keeps its zero count — which
    # cuts the state space roughly in half on a long line with many runs.
    need = [0] * states
    for idx in range(run_count - 1, -1, -1):
        need[idx] = need[idx + 1] + runs[idx] + (1 if idx + 1 < run_count else 0)

    lowest_idx = run_count
    for pos in range(length - 1, -1, -1):
        offset = pos * states
        next_offset = offset + states
        pos_is_filled = (known_filled >> pos) & 1
        pos_bit = 1 << pos
        remaining = length - pos
        while lowest_idx and need[lowest_idx - 1] <= remaining:
            lowest_idx -= 1
        for idx in range(run_count, lowest_idx - 1, -1):
            filled = 0
            empty = 0
            count = 0

            # Transition 1: leave cell ``pos`` empty and carry on.
            if not pos_is_filled:
                rest = next_offset + idx
                rest_count = counts[rest]
                if rest_count:
                    count = rest_count
                    filled = union_filled[rest]
                    empty = union_empty[rest] | pos_bit

            # Transition 2: start run ``idx`` at cell ``pos``.
            if idx < run_count:
                end = pos + runs[idx]
                if end <= length:
                    run_mask = ((1 << runs[idx]) - 1) << pos
                    if not known_empty & run_mask:
                        if end == length:
                            # The run ends the line: no separating gap needed,
                            # but no run may be left unplaced.
                            if idx + 1 == run_count:
                                count += 1
                                filled |= run_mask
                        elif not (known_filled >> end) & 1:
                            # One mandatory empty cell separates this run from
                            # the next; the line resumes after it.
                            rest = (end + 1) * states + idx + 1
                            rest_count = counts[rest]
                            if rest_count:
                                count += rest_count
                                filled |= union_filled[rest] | run_mask
                                empty |= union_empty[rest] | (1 << end)

            union_filled[offset + idx] = filled
            union_empty[offset + idx] = empty
            counts[offset + idx] = count

    placements = counts[0]
    if not placements:
        return None
    # Every placement assigns every cell, so a cell in exactly one union is
    # one all placements agree on; a cell in both unions stays unknown.
    return (union_filled[0] & ~union_empty[0], union_empty[0] & ~union_filled[0], placements)


def mask_runs(filled: int, length: int) -> LineClue:
    """Run-length encode a fully decided line straight from its filled mask.

    The bitmask twin of ``clues.encode_line``, for the one case where the line
    is complete and the DP would be wasted work. It is *not* a substitute for
    that function at the module boundary — it takes an int, not a line — and
    ``search`` still verifies finished grids through ``clues.compute_clues``.
    """
    runs: list[int] = []
    run = 0
    for pos in range(length):
        if (filled >> pos) & 1:
            run += 1
        elif run:
            runs.append(run)
            run = 0
    if run:
        runs.append(run)
    return tuple(runs)


@dataclass(slots=True)
class Board:
    """The solver's three-valued knowledge of one grid, as ADR-0012 bitmasks.

    Row masks are indexed by row and carry column bits; column masks are
    indexed by column and carry row bits. The two are redundant by
    construction and :func:`propagate` is the only thing that writes them, so
    they cannot drift apart.

    ``decided`` is the running count of cells known to be filled or empty. It
    is maintained incrementally because "how many cells did line logic alone
    settle" is one of the FR-009 difficulty signals this card has to emit, and
    recounting it by popcount on every pass would be pure waste.

    ``row_placements`` / ``column_placements`` cache how many placements each
    line still admits, as last computed by :func:`propagate`. A line is
    re-examined whenever anything writes into it, so at a fixed point these
    are current, and the branching heuristic reads them instead of recomputing
    a line DP per candidate cell.
    """

    height: int
    width: int
    row_clues: tuple[LineClue, ...]
    column_clues: tuple[LineClue, ...]
    row_filled: list[int]
    row_empty: list[int]
    column_filled: list[int]
    column_empty: list[int]
    row_placements: list[int]
    column_placements: list[int]
    decided: int

    @classmethod
    def blank(
        cls,
        row_clues: tuple[LineClue, ...],
        column_clues: tuple[LineClue, ...],
    ) -> Board:
        """A board where every cell is unknown, sized from the two clue sets."""
        height = len(row_clues)
        width = len(column_clues)
        return cls(
            height=height,
            width=width,
            row_clues=row_clues,
            column_clues=column_clues,
            row_filled=[0] * height,
            row_empty=[0] * height,
            column_filled=[0] * width,
            column_empty=[0] * width,
            # Filled in by the first propagation sweep, which examines every
            # line; until then the count is unknown, not zero.
            row_placements=[-1] * height,
            column_placements=[-1] * width,
            decided=0,
        )

    def clone(self) -> Board:
        """A copy that can be mutated without touching this one.

        Backtracking's undo step, and the reason ADR-0012 calls it "essentially
        free": the masks are immutable ints, so four shallow list copies of at
        most 50 elements each are the entire cost of saving a search node.
        """
        return Board(
            height=self.height,
            width=self.width,
            row_clues=self.row_clues,
            column_clues=self.column_clues,
            row_filled=self.row_filled.copy(),
            row_empty=self.row_empty.copy(),
            column_filled=self.column_filled.copy(),
            column_empty=self.column_empty.copy(),
            row_placements=self.row_placements.copy(),
            column_placements=self.column_placements.copy(),
            decided=self.decided,
        )

    def cell_is_known(self, row: int, column: int) -> bool:
        """Is the cell at ``(row, column)`` already decided either way?"""
        return bool((self.row_filled[row] | self.row_empty[row]) >> column & 1)

    def assign(self, row: int, column: int, filled: bool) -> None:
        """Record one cell's value in both orientations (the branch step).

        The caller is responsible for marking ``row`` and ``column`` dirty; a
        cell that is already known is a programming error, not a no-op, since
        every caller here picks an explicitly unknown cell.
        """
        if self.cell_is_known(row, column):
            raise ValueError(f"cell ({row}, {column}) is already decided")
        if filled:
            self.row_filled[row] |= 1 << column
            self.column_filled[column] |= 1 << row
        else:
            self.row_empty[row] |= 1 << column
            self.column_empty[column] |= 1 << row
        self.decided += 1


def propagate(
    board: Board,
    dirty_rows: list[bool],
    dirty_columns: list[bool],
) -> bool:
    """Run line logic over the dirty lines until nothing more can be deduced.

    Args:
        board: Mutated in place with everything the line logic settles.
        dirty_rows: ``dirty_rows[r]`` — row ``r`` needs (re)examining. Consumed:
            every flag is cleared by the time this returns.
        dirty_columns: The same for columns.

    Returns:
        ``True`` if the board is still consistent (a fixed point was reached),
        ``False`` the moment some line admits no placement at all — i.e. this
        branch of the search is contradictory and can be abandoned.

    A line is re-examined whenever a perpendicular line writes into it, so at
    the fixed point *every* line is known to admit at least one placement
    given the board's final state. That is what lets ``search`` treat a fully
    decided board as a solution: with no unknown cells left, "admits at least
    one placement" and "matches its clue" are the same statement.

    ADR-0011's cooperative deadline check belongs at the top of the outer
    ``while`` below (one check per fixed-point sweep) and at each branch node
    in ``search``; CARD-006 owns that, and guardrail G-5 keeps it out of this
    card. The loop is shaped so that check is a single added line, exactly as
    ADR-0011's "Neutral" note requires of whatever solver technique landed.
    """
    height = board.height
    width = board.width
    row_clues = board.row_clues
    column_clues = board.column_clues

    pending = True
    while pending:
        pending = False

        for row in range(height):
            if not dirty_rows[row]:
                continue
            dirty_rows[row] = False
            deduced = line_intersection(
                row_clues[row], width, board.row_filled[row], board.row_empty[row]
            )
            if deduced is None:
                return False
            filled, empty, placements = deduced
            board.row_placements[row] = placements
            new_filled = filled & ~board.row_filled[row]
            new_empty = empty & ~board.row_empty[row]
            if not (new_filled or new_empty):
                continue
            board.row_filled[row] = filled
            board.row_empty[row] = empty
            board.decided += new_filled.bit_count() + new_empty.bit_count()
            row_bit = 1 << row
            bits = new_filled
            while bits:
                column = (bits & -bits).bit_length() - 1
                bits &= bits - 1
                board.column_filled[column] |= row_bit
                dirty_columns[column] = True
                pending = True
            bits = new_empty
            while bits:
                column = (bits & -bits).bit_length() - 1
                bits &= bits - 1
                board.column_empty[column] |= row_bit
                dirty_columns[column] = True
                pending = True

        for column in range(width):
            if not dirty_columns[column]:
                continue
            dirty_columns[column] = False
            deduced = line_intersection(
                column_clues[column],
                height,
                board.column_filled[column],
                board.column_empty[column],
            )
            if deduced is None:
                return False
            filled, empty, placements = deduced
            board.column_placements[column] = placements
            new_filled = filled & ~board.column_filled[column]
            new_empty = empty & ~board.column_empty[column]
            if not (new_filled or new_empty):
                continue
            board.column_filled[column] = filled
            board.column_empty[column] = empty
            board.decided += new_filled.bit_count() + new_empty.bit_count()
            column_bit = 1 << column
            bits = new_filled
            while bits:
                row = (bits & -bits).bit_length() - 1
                bits &= bits - 1
                board.row_filled[row] |= column_bit
                dirty_rows[row] = True
                pending = True
            bits = new_empty
            while bits:
                row = (bits & -bits).bit_length() - 1
                bits &= bits - 1
                board.row_empty[row] |= column_bit
                dirty_rows[row] = True
                pending = True

    return True
