"""ADR-0014's brute-force reference oracle. TEST-ONLY — never a production path.

CON-005 is the model's one mandatory constraint: the uniqueness check must
never produce a false positive. ADR-0009 chose a hand-rolled solver knowing
that this is exactly where such a bug would hide, and named this oracle as its
mitigation. So what lives here is a second, deliberately naive solver that
shares *no* code with ``nonogram.solver``: two implementations agreeing is
evidence, one implementation checking itself is not.

Everything here derives clues through ``nonogram.clues`` (CARD-002), which is
independently written and independently property-tested, and never touches the
solver's bitmask representation.

Two counters, and why there are two
-----------------------------------
``count_solutions``
    Enumerates, per row, *every* line pattern whose run-length encoding equals
    that row's clue, then walks the cartesian product of those per-row choices
    and keeps the combinations whose columns also encode to the column clues.
    Used by the EC-001 property test.
``count_solutions_by_cell``
    Enumerates all ``2 ** (height * width)`` grids and keeps the ones whose
    clues match. Unarguably exhaustive, unarguably correct, and unusable above
    about 16 cells. It exists to check the first counter on small grids — an
    oracle nobody has verified is just a second guess.

Why the first counter is not literally ``2 ** (size * size)``
-------------------------------------------------------------
The card describes the oracle as exhaustive enumeration of all
``2 ** (size * size)`` grids, which is what ``count_solutions_by_cell`` does;
that is 4x4 = 65,536 grids (instant), 5x5 = 33,554,432 (about a minute in
Python), 6x6 = 6.9e10 (days). Since the property test needs thousands of cases
at 6x6, ``count_solutions`` reformulates the same exhaustive search over line
patterns instead of over cells. It is still exhaustive — no heuristic, no
deduction, no early cut that is not proved below — and it remains obviously
correct because both of its steps are themselves brute-force enumerations:

* a row's candidate set is every one of the ``2 ** width`` patterns, filtered
  by ``clues.encode_line``;
* the column check is "is this partial column the prefix of some fully
  enumerated candidate for that column", i.e. a lookup in a set that was
  itself built by brute force. If a full grid is a solution then each of its
  columns *is* one of those candidates, so every prefix of it is in the set —
  the prune can therefore never discard a solution, only combinations that
  provably have no completion.

Every kept grid is then re-derived through ``clues.compute_clues`` and
compared with the input clues before it is counted, so a bug in the pruning
could only ever make the oracle count too few — and the property test would
see the disagreement rather than silently agreeing with a broken solver.

Practical size ceiling
----------------------
``count_solutions`` is comfortable to 7x7 and usable at 8x8 for grids whose
clues are not extremely loose (its cost is the product of the per-row
candidate counts, which grows with how little each clue constrains its line —
sparse, few-run clues are the expensive ones, not dense ones). The property
test cross-checks at 6x6 and below, where a worst case is still milliseconds;
see that module for the reasoning behind that ceiling.
"""

from __future__ import annotations

from collections.abc import Iterator
from itertools import product

from nonogram.clues import compute_clues, encode_line

Grid = list[list[bool]]
ClueSet = tuple[tuple[int, ...], ...]

#: Above this many cells, ``count_solutions_by_cell`` stops being a test and
#: starts being a coffee break: 2**16 grids is instant, 2**25 is a minute.
MAX_CELLS_BY_CELL = 16


def line_candidates(clue: tuple[int, ...], length: int) -> list[tuple[bool, ...]]:
    """Every line of ``length`` cells whose run-length encoding is ``clue``.

    Brute force over all ``2 ** length`` patterns, filtered with CARD-002's
    ``encode_line``. No cleverness on purpose: this is the oracle's ground
    truth for "what could this line be", and it has to be checkable by eye.
    """
    wanted = tuple(clue)
    return [
        pattern
        for pattern in product((False, True), repeat=length)
        if encode_line(pattern) == wanted
    ]


def iter_solutions(
    row_clues: ClueSet,
    column_clues: ClueSet,
    limit: int | None = None,
) -> Iterator[Grid]:
    """Yield every grid matching both clue sets, oldest-fashioned way possible.

    Args:
        row_clues: One clue tuple per row, top to bottom.
        column_clues: One clue tuple per column, left to right.
        limit: Stop after yielding this many solutions. ``None`` enumerates
            all of them.

    Yields:
        Solution grids in ``list[list[bool]]``, in a deterministic order.
    """
    height = len(row_clues)
    width = len(column_clues)
    if height == 0 or width == 0:
        return

    row_options = [line_candidates(clue, width) for clue in row_clues]
    if any(not options for options in row_options):
        return  # some row's clue cannot be laid out at all

    # Every prefix of every legal column, by prefix length. Built by brute
    # force from the same exhaustive candidate enumeration, which is what
    # makes pruning on it safe (see the module docstring).
    column_prefixes: list[list[set[tuple[bool, ...]]]] = []
    for clue in column_clues:
        candidates = line_candidates(clue, height)
        column_prefixes.append(
            [{candidate[: depth + 1] for candidate in candidates} for depth in range(height)]
        )

    found = 0
    chosen: list[tuple[bool, ...]] = []

    def extend(row: int) -> Iterator[Grid]:
        nonlocal found
        if row == height:
            grid = [list(line) for line in chosen]
            derived = compute_clues(grid)
            # Belt and braces: the count is only trustworthy if each counted
            # grid genuinely encodes back to the clues asked about.
            if (derived.rows, derived.columns) == (tuple(row_clues), tuple(column_clues)):
                found += 1
                yield grid
            return
        for candidate in row_options[row]:
            chosen.append(candidate)
            prefixes = tuple(
                tuple(line[column] for line in chosen) for column in range(width)
            )
            if all(
                prefixes[column] in column_prefixes[column][row] for column in range(width)
            ):
                yield from extend(row + 1)
                if limit is not None and found >= limit:
                    chosen.pop()
                    return
            chosen.pop()

    yield from extend(0)


def count_solutions(
    row_clues: ClueSet,
    column_clues: ClueSet,
    limit: int | None = None,
) -> int:
    """How many grids match both clue sets, counting no further than ``limit``.

    With ``limit=2`` the answer is directly comparable to the solver's
    ``solution_count``: ``0``, ``1``, or ``2`` meaning ">= 2".
    """
    return sum(1 for _ in iter_solutions(row_clues, column_clues, limit=limit))


def count_solutions_by_cell(row_clues: ClueSet, column_clues: ClueSet) -> int:
    """Count solutions by trying all ``2 ** (height * width)`` grids.

    The most literal reading of "exhaustive enumeration" there is, and the
    check on :func:`count_solutions`. Refuses to run above
    :data:`MAX_CELLS_BY_CELL` cells rather than appearing to hang.

    Raises:
        ValueError: the grid has more cells than this can enumerate.
    """
    height = len(row_clues)
    width = len(column_clues)
    cells = height * width
    if cells > MAX_CELLS_BY_CELL:
        raise ValueError(
            f"{height}x{width} = {cells} cells is {2 ** cells} grids; "
            f"count_solutions_by_cell is capped at {MAX_CELLS_BY_CELL} cells"
        )

    wanted = (tuple(row_clues), tuple(column_clues))
    total = 0
    for bits in range(1 << cells):
        grid = [
            [bool((bits >> (row * width + column)) & 1) for column in range(width)]
            for row in range(height)
        ]
        derived = compute_clues(grid)
        if (derived.rows, derived.columns) == wanted:
            total += 1
    return total
