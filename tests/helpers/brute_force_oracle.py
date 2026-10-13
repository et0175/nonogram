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

Given cells (CARD-214)
----------------------
Both counters take an optional ``givens`` — the same grid-shaped partial
assignment ``nonogram.solver.solve`` takes (``True`` filled, ``False`` empty,
``None`` unknown) — and both answer the seeded question: how many grids match
the clues **and** agree with every revealed cell.

It is implemented here as what it is: a **filter over this module's own
enumeration**, written from the definition and sharing nothing with the
solver's seeding. ``count_solutions`` drops each row's candidate patterns that
disagree with that row's revealed cells before the product is walked, and the
completed grid is checked against the assignment cell by cell before it is
counted — the same belt-and-braces shape the clue re-derivation already has, so
a bug in the pruning could only ever make the oracle count too *few* and the
property test would see a disagreement rather than agree with a broken solver.
``count_solutions_by_cell`` adds one condition to its ``2 ** cells`` loop and
prunes nothing at all, which is what makes it the check on the filter itself
(``test_the_two_oracles_agree_under_givens``).

**This module must not import ``nonogram.solver``** — it never has, and under
givens that matters more rather than less: an oracle that borrowed the solver's
seeding would turn the one mandatory cross-check in the model into the solver
agreeing with itself. ``test_the_oracle_shares_no_code_with_the_solver`` reads
this file with ``ast`` and fails on any such import.

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
#: CARD-214's partial assignment, in the same boundary type the solver takes.
#: Spelled out here rather than imported from ``nonogram.solver``: this module's
#: whole value is that it imports none of it (see the module docstring).
Givens = list[list[bool | None]]

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


def line_agrees_with_givens(
    pattern: tuple[bool, ...], given_row: list[bool | None]
) -> bool:
    """Does one line pattern agree with every revealed cell of that line?

    The whole of this oracle's understanding of a given, written from the
    definition: a revealed cell fixes that cell's value, an unrevealed one
    (``None``) says nothing. No deduction, no propagation, nothing shared with
    the solver's seeding (CARD-214).
    """
    return all(
        value is None or pattern[index] == value
        for index, value in enumerate(given_row)
    )


def grid_agrees_with_givens(grid: Grid, givens: Givens | None) -> bool:
    """Does a whole grid agree with every revealed cell? (``None`` -> yes.)"""
    if givens is None:
        return True
    return all(
        line_agrees_with_givens(tuple(row), given_row)
        for row, given_row in zip(grid, givens, strict=True)
    )


def iter_solutions(
    row_clues: ClueSet,
    column_clues: ClueSet,
    limit: int | None = None,
    givens: Givens | None = None,
) -> Iterator[Grid]:
    """Yield every grid matching both clue sets, oldest-fashioned way possible.

    Args:
        row_clues: One clue tuple per row, top to bottom.
        column_clues: One clue tuple per column, left to right.
        limit: Stop after yielding this many solutions. ``None`` enumerates
            all of them.
        givens: CARD-214's partial assignment, or ``None`` for the unseeded
            question. Applied twice on purpose: as a filter on each row's
            candidate patterns (which prunes, and is sound for the same reason
            the column-prefix prune is — a solution's rows each agree with the
            assignment, so no solution is discarded), and again on the
            completed grid before it is counted. The second check is what makes
            a bug in the first one visible as an undercount instead of as
            agreement with a broken solver.

    Yields:
        Solution grids in ``list[list[bool]]``, in a deterministic order.
    """
    height = len(row_clues)
    width = len(column_clues)
    if height == 0 or width == 0:
        return
    if givens is not None and (
        len(givens) != height or any(len(row) != width for row in givens)
    ):
        raise ValueError(
            f"givens is not shaped like the {height}x{width} puzzle the clues "
            f"describe"
        )

    row_options = [line_candidates(clue, width) for clue in row_clues]
    if givens is not None:
        row_options = [
            [
                pattern
                for pattern in options
                if line_agrees_with_givens(pattern, givens[row])
            ]
            for row, options in enumerate(row_options)
        ]
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
            # grid genuinely encodes back to the clues asked about — and, since
            # CARD-214, genuinely agrees with every revealed cell.
            if (
                derived.rows,
                derived.columns,
            ) == (tuple(row_clues), tuple(column_clues)) and grid_agrees_with_givens(
                grid, givens
            ):
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
    givens: Givens | None = None,
) -> int:
    """How many grids match both clue sets, counting no further than ``limit``.

    With ``limit=2`` the answer is directly comparable to the solver's
    ``solution_count``: ``0``, ``1``, or ``2`` meaning ">= 2". Pass ``givens``
    to ask the seeded question the solver's ``givens`` keyword asks (CARD-214);
    the two answers must agree on every input, which is what
    ``PropertyTest_SolverUniqueness_HoldsUnderGivens`` checks.
    """
    return sum(
        1
        for _ in iter_solutions(row_clues, column_clues, limit=limit, givens=givens)
    )


def count_solutions_by_cell(
    row_clues: ClueSet,
    column_clues: ClueSet,
    givens: Givens | None = None,
) -> int:
    """Count solutions by trying all ``2 ** (height * width)`` grids.

    The most literal reading of "exhaustive enumeration" there is, and the
    check on :func:`count_solutions` — including on its ``givens`` filter,
    which here is one extra condition on a loop that prunes nothing at all.
    Refuses to run above :data:`MAX_CELLS_BY_CELL` cells rather than appearing
    to hang.

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
        if (derived.rows, derived.columns) == wanted and grid_agrees_with_givens(
            grid, givens
        ):
            total += 1
    return total
