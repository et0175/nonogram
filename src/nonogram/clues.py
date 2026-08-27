"""COMP-004 (Clue Derivation) — CAP-002 / FR-005: clues by run-length encoding.

A pure function module: no state, no I/O, no logging, no clock, no randomness.
Every function here is a total function of its arguments, which is what lets
INV-001 be checked as a property (AC-014) without any fixture machinery.

Boundary representation (ADR-0012, guardrail G-3)
------------------------------------------------
The grid arrives in the *boundary* representation — ``list[list[bool]]``, one
inner list per row, ``True`` for a filled cell — and clues leave as
``tuple[tuple[int, ...], ...]``, one inner tuple per line. The solver's
internal int-bitmask-per-line representation (also ADR-0012) is COMP-005's
private business and deliberately does not appear in this module's API: clues
and grid bitmasks are separate representations serving separate concerns, and
ADR-0012's "Neutral" consequence asks future work to preserve that separation.
Immutable tuples on the way out mean a clue set can be shared with the solver,
the difficulty scorer and the exporters without any of them being able to
mutate what the others see.

The empty-row marker (AC-013)
-----------------------------
A line with no filled cells encodes to ``(0,)``, not ``()``. This is the
conventional nonogram notation, and it keeps every line's clue non-empty so
downstream renderers and the solver's line logic can treat "clue" uniformly —
``len(clue)`` is always at least 1, and the "sum of runs plus one gap between
each pair" arithmetic the solver uses stays valid without a special case.

Public surface
--------------
``encode_line``          run-length encode one line (the primitive)
``compute_clues``        encode every row and every column of a grid
``clue_matches_line``    the inverse check behind INV-001 / AC-014
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import NamedTuple

__all__ = ["Clues", "clue_matches_line", "compute_clues", "encode_line"]

# The ADR-0012 boundary types, named so the intent reads at every call site.
Grid = list[list[bool]]
LineClue = tuple[int, ...]
ClueSet = tuple[tuple[int, ...], ...]

#: The clue of a line with no filled cells (AC-013).
EMPTY_LINE_CLUE: LineClue = (0,)


class Clues(NamedTuple):
    """A grid's two clue sets, in the ADR-0012 boundary type.

    A pair rather than two separate return values because rows and columns are
    derived from one grid in one pass and are meaningless apart; naming the
    two members removes the classic ``(rows, cols)`` transposition bug at the
    call site. Still a plain tuple, so it unpacks and serializes like one.
    """

    rows: ClueSet
    columns: ClueSet


def encode_line(line: Iterable[bool]) -> LineClue:
    """Run-length encode one line: the lengths of its contiguous filled runs.

    ``[True, True, False, True, True, True, False, False]`` -> ``(2, 3)``
    (AC-012). A line with no filled cells -> ``(0,)`` (AC-013, and see the
    module docstring on why not ``()``).

    Accepts any iterable of truthy/falsy cells so the solver's line logic can
    pass a generator or a transposed column without materialising a list.
    """
    runs: list[int] = []
    run = 0
    for cell in line:
        if cell:
            run += 1
        elif run:
            runs.append(run)
            run = 0
    if run:
        runs.append(run)
    return tuple(runs) if runs else EMPTY_LINE_CLUE


def compute_clues(grid: Grid) -> Clues:
    """Encode every row and every column of ``grid`` (FR-005).

    ``grid`` is the ADR-0012 boundary representation: a list of equal-length
    rows of booleans. Returns row clues in top-to-bottom order and column
    clues in left-to-right order, each line encoded by :func:`encode_line`.

    An empty grid yields two empty clue sets. A ragged grid is a programming
    error, not a domain condition, and raises ``ValueError`` — ``zip``'s
    ``strict`` check catches it rather than silently truncating the columns to
    the shortest row, which would produce clues that quietly disagree with the
    grid and so violate INV-001 without anything failing.
    """
    rows: ClueSet = tuple(encode_line(row) for row in grid)
    columns: ClueSet = tuple(encode_line(column) for column in zip(*grid, strict=True))
    return Clues(rows=rows, columns=columns)


def clue_matches_line(clue: Sequence[int], line: Iterable[bool]) -> bool:
    """Is ``clue`` exactly the run-length encoding of ``line``? (INV-001)

    The inverse of :func:`encode_line`, and the check AC-014 applies to every
    row and column of a grid. Used by the solver's line logic to accept or
    reject a candidate placement of a line.

    The comparison is *exact*, in both directions: ``(2, 3)`` matches only a
    line whose filled runs are 2 then 3, and an all-empty line is matched only
    by the ``(0,)`` marker — never by ``()``, so a clue set that dropped the
    marker somewhere is reported as a mismatch instead of passing silently.
    """
    return tuple(clue) == encode_line(line)
