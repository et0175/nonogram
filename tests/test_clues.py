"""COMP-004 tests: run-length clue derivation and its inverse check (FR-005).

AC / test-id mapping — the trace.yml names, kept traceable from these
pytest-idiomatic function names:

    AC-012  TestComputeClues_EncodesRunLengths   -> test_encodes_run_lengths*
    AC-013  TestComputeClues_HandlesEmptyRow     -> test_handles_empty_row*
    AC-014  TestComputeClues_MatchesGridExactly  -> test_matches_grid_exactly*
            (INV-001, checked as a property over generated + hand-picked grids)

AC-014 is an invariant, so it is tested as a property rather than as a single
example: ``_property_grids()`` yields hand-picked edge shapes plus grids drawn
from a *seeded* ``random.Random``, so the run is varied but reproducible and no
new dependency (hypothesis) is pulled in against ADR-0006's closed baseline.

The sweep is checked against ``_reference_encode_line``, a from-scratch,
independently written run-length encoder that lives only in this test file
(see its docstring). ``clue_matches_line`` re-derives its expectation by
calling ``clues.encode_line`` again internally, so checking compute_clues's
output only through ``clue_matches_line`` would reduce to
``encode_line(x) == encode_line(x)`` — true for any implementation, correct
or not, because both sides share the same function and so share any of its
defects. ``_reference_encode_line`` shares no code with ``encode_line``, so
it is real, independent evidence when the two agree.
"""

from __future__ import annotations

import itertools
import random
from collections.abc import Iterable, Iterator

import pytest

from nonogram import clues

# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

# Reads like the AC's own notation: ``█`` filled, ``·`` empty.
_FILLED = "█"
_EMPTY = "·"


def _line(pattern: str) -> list[bool]:
    """``"██·███··"`` -> the boundary-type line the AC describes."""
    assert set(pattern) <= {_FILLED, _EMPTY}, f"bad pattern glyph in {pattern!r}"
    return [glyph == _FILLED for glyph in pattern]


def _grid(*patterns: str) -> list[list[bool]]:
    """A ``list[list[bool]]`` grid (ADR-0012 boundary type) from row patterns."""
    return [_line(pattern) for pattern in patterns]


def _reference_encode_line(line: Iterable[bool]) -> tuple[int, ...]:
    """An INDEPENDENT run-length encoder, written only for this test's oracle.

    This deliberately does not call, import, or share a single line of code
    with ``clues.encode_line``. It is a from-scratch reimplementation using
    ``itertools.groupby`` instead of a hand-rolled running counter, so a bug
    in ``encode_line`` (wrong run order, a dropped run, an off-by-one at an
    edge) has to be reproduced independently here by coincidence to slip
    through — which is exactly the property that makes an oracle real
    evidence rather than a tautology (`encode_line(x) == encode_line(x)` is
    true for any implementation, correct or not; two independently written
    encoders agreeing is not).

    The empty-line marker ``(0,)`` is hardcoded here rather than imported
    from ``clues.EMPTY_LINE_CLUE``, so this function has zero coupling to the
    module under test beyond the boundary type itself.
    """
    runs = tuple(
        len(list(group)) for is_filled, group in itertools.groupby(map(bool, line)) if is_filled
    )
    return runs if runs else (0,)


# --------------------------------------------------------------------------
# AC-012 (happy) — TestComputeClues_EncodesRunLengths
# --------------------------------------------------------------------------


def test_encodes_run_lengths() -> None:
    """AC-012: row ``██·███··`` -> row clue ``[2, 3]``.

    Asserted through the public grid-level entry point, in the ADR-0012
    boundary type, so the AC covers the API the orchestrator will actually
    call rather than only the private line primitive.
    """
    grid = _grid("██·███··")

    result = clues.compute_clues(grid)

    assert result.rows[0] == (2, 3)


def test_encodes_run_lengths_for_the_line_primitive() -> None:
    """AC-012, at the ``encode_line`` level the solver's line logic uses."""
    assert clues.encode_line(_line("██·███··")) == (2, 3)


@pytest.mark.parametrize(
    ("pattern", "expected"),
    [
        ("█", (1,)),
        ("██", (2,)),
        ("█·█", (1, 1)),
        ("███", (3,)),  # a fully filled line is one run, not per-cell runs
        ("█···████", (1, 4)),  # run touching the left edge
        ("··█·██·█", (1, 2, 1)),  # run touching the right edge
        ("█·█·█·█·█", (1, 1, 1, 1, 1)),  # alternating: the maximum run count
    ],
)
def test_encodes_run_lengths_at_the_edges(pattern: str, expected: tuple[int, ...]) -> None:
    """AC-012: runs are counted correctly against both grid edges.

    Runs flush with the start or the end of a line are where run-length
    encoding classically goes off by one, so they are pinned explicitly.
    """
    assert clues.encode_line(_line(pattern)) == expected
    # Independent oracle, not just the hand-written literal: a second,
    # differently-written encoder must land on the same answer too.
    assert _reference_encode_line(_line(pattern)) == expected


def test_column_clues_read_top_to_bottom() -> None:
    """AC-012 applied to columns: the transpose is taken, in order.

    ``compute_clues`` must not silently return the row clues twice, and column
    ``i`` must be the i-th cell of each row read downwards. This grid is
    deliberately asymmetric so a transposition bug cannot pass.
    """
    grid = _grid(
        "██·",
        "·█·",
        "·██",
    )

    result = clues.compute_clues(grid)

    assert result.rows == ((2,), (1,), (2,))
    assert result.columns == ((1,), (3,), (1,))


def test_clues_are_immutable_tuples() -> None:
    """ADR-0012 / G-3: the boundary clue type is ``tuple[tuple[int, ...], ...]``.

    Immutability is what lets one clue set be handed to the solver, the
    difficulty scorer and the exporters at once, so it is asserted rather than
    assumed.
    """
    result = clues.compute_clues(_grid("██·███··"))

    assert isinstance(result.rows, tuple)
    assert isinstance(result.columns, tuple)
    assert all(isinstance(clue, tuple) for clue in (*result.rows, *result.columns))
    assert all(isinstance(run, int) for clue in result.rows for run in clue)


# --------------------------------------------------------------------------
# AC-013 (boundary) — TestComputeClues_HandlesEmptyRow
# --------------------------------------------------------------------------


def test_handles_empty_row() -> None:
    """AC-013: a row with no filled cells gets the empty-row marker ``[0]``."""
    grid = _grid("········")

    result = clues.compute_clues(grid)

    assert result.rows[0] == (0,)


def test_handles_empty_row_marker_is_not_the_empty_tuple() -> None:
    """AC-013, the part that actually bites: ``(0,)`` and never ``()``.

    Downstream renderers and the solver's line arithmetic rely on every clue
    being non-empty, so the distinction is pinned separately from the value.
    """
    clue = clues.encode_line(_line("····"))

    assert clue == (0,)
    assert clue != ()
    assert len(clue) == 1


def test_handles_empty_column_with_the_same_marker() -> None:
    """AC-013 symmetrically: an all-empty *column* also encodes to ``[0]``."""
    grid = _grid(
        "█·█",
        "█·█",
    )

    result = clues.compute_clues(grid)

    assert result.columns == ((2,), (0,), (2,))


def test_handles_a_wholly_empty_grid() -> None:
    """AC-013 at the extreme: every line of a blank grid carries the marker."""
    result = clues.compute_clues(_grid("···", "···"))

    assert result.rows == ((0,), (0,))
    assert result.columns == ((0,), (0,), (0,))


def test_handles_a_zero_row_grid() -> None:
    """A grid with no rows has no clues at all — not a marker per missing line."""
    result = clues.compute_clues([])

    assert result.rows == ()
    assert result.columns == ()


def test_clue_matches_line_rejects_the_bare_empty_tuple() -> None:
    """AC-013 through the inverse check: ``()`` is not a valid empty-line clue.

    A clue set that lost the marker must be reported as a mismatch, otherwise
    INV-001 could hold vacuously for blank lines.
    """
    blank = _line("····")

    assert clues.clue_matches_line((0,), blank)
    assert not clues.clue_matches_line((), blank)


# --------------------------------------------------------------------------
# AC-014 (boundary, INV-001) — TestComputeClues_MatchesGridExactly
# --------------------------------------------------------------------------

# Fixed seed: the property sweep is varied but byte-for-byte reproducible, so a
# failure is replayable from the reported case alone.
_PROPERTY_SEED = 20260827


def _random_grid(rng: random.Random, rows: int, columns: int, density: float) -> list[list[bool]]:
    return [[rng.random() < density for _ in range(columns)] for _ in range(rows)]


def _property_grids() -> Iterator[tuple[str, list[list[bool]]]]:
    """Varied grids for the INV-001 sweep, each with a label for the failure message."""
    # Hand-picked shapes: the degenerate and saturated ends, which random
    # sampling at a middling density would essentially never produce.
    yield "1x1 filled", _grid("█")
    yield "1x1 empty", _grid("·")
    yield "single row", _grid("█··██·█████·")
    yield "single column", _grid("█", "·", "█", "█", "·")
    yield "all filled 6x6", [[True] * 6 for _ in range(6)]
    yield "all empty 6x6", [[False] * 6 for _ in range(6)]
    yield "checkerboard 7x7", [[(r + c) % 2 == 0 for c in range(7)] for r in range(7)]
    yield "diagonal 8x8", [[r == c for c in range(8)] for r in range(8)]
    yield "anti-diagonal 8x8", [[r + c == 7 for c in range(8)] for r in range(8)]
    yield "frame 9x9", [
        [r in (0, 8) or c in (0, 8) for c in range(9)] for r in range(9)
    ]
    yield "asymmetric 3x5", _grid("██·██", "·····", "█···█")

    # Seeded random sweep across the supported size range (ADR-0012 caps a line
    # at 50 cells) and across densities, including the 0.0/1.0 extremes.
    _sizes = (1, 2, 3, 5, 8, 13, 21, 34, 50)
    _densities = (0.0, 0.1, 0.25, 0.35, 0.5, 0.65, 0.75, 0.9, 1.0)
    rng = random.Random(_PROPERTY_SEED)
    for size in _sizes:
        for density in _densities:
            yield (
                f"random {size}x{size} d={density}",
                _random_grid(rng, size, size, density),
            )
    # Non-square grids too, so a rows/columns mix-up cannot survive by
    # symmetry — and swept across every density above, not just one, so a
    # non-square-specific bug that only shows up at a particular fill level
    # cannot hide behind a single fixed density.
    _nonsquare_shapes = (
        (1, 50),
        (50, 1),
        (3, 17),
        (17, 3),
        (4, 29),
        (29, 4),
        (2, 33),
        (33, 2),
        (11, 19),
        (19, 11),
    )
    for rows, columns in _nonsquare_shapes:
        for density in _densities:
            yield (
                f"random {rows}x{columns} d={density}",
                _random_grid(rng, rows, columns, density),
            )


_PROPERTY_CASES = list(_property_grids())


@pytest.mark.parametrize(
    "grid", [grid for _, grid in _PROPERTY_CASES], ids=[label for label, _ in _PROPERTY_CASES]
)
def test_matches_grid_exactly(grid: list[list[bool]]) -> None:
    """AC-014 / INV-001: every computed clue is exactly its line's encoding.

    The property: for an arbitrary solution grid, computing clues and then
    running the inverse check (``clue_matches_line``) against the corresponding
    row or column must confirm the match for *every* line — no clue may be off,
    dropped, duplicated, or transposed.

    ``clue_matches_line`` re-derives its own expectation by calling
    ``encode_line`` again internally, so on its own this only proves
    ``encode_line(x) == encode_line(x)`` — true for any implementation of
    ``encode_line``, correct or not, since compute_clues's output and
    clue_matches_line's expectation share the same underlying function. The
    ``_reference_encode_line`` assertions below are the real check: a
    from-scratch, independently written encoder (see its docstring) that does
    not call or share code with ``encode_line``, so an encoder bug (wrong run
    order, a dropped run, an edge off-by-one) has to be reproduced by
    coincidence in a second, differently-written implementation to survive.
    """
    result = clues.compute_clues(grid)

    assert len(result.rows) == len(grid)
    assert len(result.columns) == (len(grid[0]) if grid else 0)

    for index, (clue, row) in enumerate(zip(result.rows, grid, strict=True)):
        assert clues.clue_matches_line(clue, row), f"row {index}: {clue} vs {row}"
        assert clue == _reference_encode_line(row), (
            f"row {index}: {clue} disagrees with the independent oracle"
        )

    for index, (clue, column) in enumerate(
        zip(result.columns, zip(*grid, strict=True), strict=True)
    ):
        assert clues.clue_matches_line(clue, column), f"column {index}: {clue} vs {column}"
        assert clue == _reference_encode_line(column), (
            f"column {index}: {clue} disagrees with the independent oracle"
        )


@pytest.mark.parametrize(
    "grid", [grid for _, grid in _PROPERTY_CASES], ids=[label for label, _ in _PROPERTY_CASES]
)
def test_matches_grid_exactly_conserves_filled_cell_count(grid: list[list[bool]]) -> None:
    """AC-014, a second independent view of INV-001: the run sums must agree.

    Row runs and column runs both have to total the grid's filled-cell count.
    This catches an encoding that satisfies the per-line check on one axis but
    has lost or invented cells on the other — the marker ``0`` contributes
    nothing to either sum, which is exactly why it is safe as a marker.
    """
    result = clues.compute_clues(grid)
    filled = sum(cell for row in grid for cell in row)

    assert sum(sum(clue) for clue in result.rows) == filled
    assert sum(sum(clue) for clue in result.columns) == filled


def test_matches_grid_exactly_rejects_a_wrong_clue() -> None:
    """AC-014's check must be able to *fail* — a green sweep would be worthless
    if ``clue_matches_line`` returned ``True`` unconditionally.
    """
    line = _line("██·███··")

    assert clues.clue_matches_line((2, 3), line)
    assert not clues.clue_matches_line((3, 2), line)  # order matters
    assert not clues.clue_matches_line((2, 3, 1), line)  # extra run
    assert not clues.clue_matches_line((2,), line)  # missing run
    assert not clues.clue_matches_line((5,), line)  # same total, wrong split
    assert not clues.clue_matches_line((0,), line)  # marker on a filled line


def test_matches_grid_exactly_accepts_a_list_clue() -> None:
    """The inverse check compares by value, so a JSON-decoded ``list`` works.

    Clues round-trip through JSON/CSV as lists (EC-002), and the solver builds
    candidate clues as lists; neither should have to re-tuple to be checked.
    """
    assert clues.clue_matches_line([2, 3], _line("██·███··"))


def test_ragged_grid_is_rejected_rather_than_silently_truncated() -> None:
    """A ragged grid is a programming error, not a domain condition.

    ``zip(..., strict=True)`` surfaces it as ``ValueError`` instead of
    truncating the columns to the shortest row, which would emit clues that
    quietly disagree with the grid and so break INV-001 with nothing failing.
    """
    with pytest.raises(ValueError):
        clues.compute_clues([[True, False], [True]])


def test_compute_clues_does_not_mutate_the_grid() -> None:
    """A pure function of its argument: the caller's grid comes back untouched."""
    grid = _grid("██·███··", "····████")
    snapshot = [row[:] for row in grid]

    clues.compute_clues(grid)

    assert grid == snapshot


def test_clues_unpacks_as_a_plain_pair() -> None:
    """``Clues`` names its members but stays a tuple, so callers may unpack."""
    rows, columns = clues.compute_clues(_grid("█·", "·█"))

    assert rows == ((1,), (1,))
    assert columns == ((1,), (1,))
