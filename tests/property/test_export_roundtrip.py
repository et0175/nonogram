"""EC-002 / FR-012: an export decodes back to exactly the puzzle it came from.

    PropertyTest_Export_RoundTripsExactlyForAnyPuzzle
        -> test_round_trips_exactly_for_any_puzzle_as_json
        -> test_round_trips_exactly_for_any_puzzle_as_csv
        -> test_a_slice_of_the_corpus_round_trips_through_real_files
        -> test_the_two_formats_decode_to_the_same_payload
        -> test_the_corpus_covers_what_ec_002_asks_for  (the corpus's own gate)

    AC-033  TestExport_JSONRoundTripsExactly -> test_json_round_trips_exactly
            (EC-002's named instance, on one real pipeline-finalized puzzle;
             test_csv_round_trips_exactly is the CSV instance beside it)

EC-002 states a property of the *pair* — writer and decoder — over any
finalized puzzle, in both formats. So it is checked the way EC-001 is: over a
corpus, not over one example. The AC-033 example is here too, immediately
above the property it is an instance of, so the named acceptance test and the
generalisation of it cannot drift apart.

What the property actually rests on (guardrail G-4)
---------------------------------------------------
ADR-0012 puts a plain ``list[list[bool]]`` and ``tuple[tuple[int, ...], ...]``
at the export boundary, never the solver's internal per-line bitmask. That is
what makes exact fidelity reachable at all: there is no bit order, mask width
or sign convention at the seam to get wrong. If a change here ever makes this
property fail, ADR-0012's note applies — the fix is the representation, not a
looser comparison.

Metadata is checked, but checked separately (ADR-0015)
------------------------------------------------------
ADR-0015 warns that this very test can go wrong in two opposite directions:
fold the seed and the generation parameters into the grid/clue equality and
two exports of one puzzle at different seeds are wrongly unequal; drop them
and the property quietly stops checking fields it should. So both tests assert
the grid and the clues as EC-002's own claim, and the provenance fields as a
second, separately-worded claim — never one comparison standing in for both.

The corpus
----------
Seeded ``random.Random``, no ``hypothesis``: ADR-0006's dependency baseline is
closed (guardrail G-5) and CARD-002/CARD-004 already set the house pattern of a
seeded corpus plus hand-picked edge shapes. The case count is asserted inside
the tests rather than left to a comment, so shrinking the corpus can never
quietly drop below the bar.

Three things the corpus is built to contain, because EC-002 names them:

* **The whole supported size range.** Every edge length from 1 to 50 (AC-038's
  ceiling) appears — asserted, not hoped for. 1x1 is where a one-cell grid and
  a one-run clue coincide; 50x50 is where a row is 50 CSV cells wide.
* **A density spread including both extremes.** An all-empty line is the
  ``(0,)`` marker (AC-013) and an all-filled line is a single full-width run;
  both are legal sourcing outcomes (CARD-003) and both are the shapes a flat
  format is most likely to mangle — ``(0,)`` into ``()``, or a blank cell into
  a zero.
* **Hand-picked degenerate shapes** the random draw would essentially never
  produce: fully empty and fully filled grids at both ends of the size range,
  a single filled cell in a large grid, maximal-run stripes and a checkerboard
  (the most clue-runs a line can hold), and payloads whose ``size``/``density``
  were never requested at all (``None``, not zero).
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path

from nonogram.clues import compute_clues
from nonogram.export import ExportPayload, csv_export, json_export
from nonogram.orchestrator import GenerationRequest, export_puzzle, generate

#: One seed for the whole module: change it and the corpus changes wholesale,
#: which is a deliberate act, not a side effect of running the suite twice.
SEED = 20260828

#: EC-002's floor. Comfortably below :data:`CASE_COUNT` so the bar is not also
#: the ceiling — the whole corpus, both formats, costs a couple of seconds.
REQUIRED_CASES = 500

#: The supported grid edge lengths (AC-038 caps the range at 50).
SIZES: tuple[int, ...] = tuple(range(1, 51))

#: Fill densities drawn from. Both extremes are in deliberately: 0.0 produces
#: the all-empty lines the ``(0,)`` marker exists for, 1.0 the all-filled ones.
DENSITIES: tuple[float, ...] = (0.0, 0.05, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95, 1.0)

#: Generation modes and requested-parameter shapes cycled through the corpus,
#: so the provenance half of the payload varies too rather than being one
#: constant the decoder could hardcode and still pass.
_MODES: tuple[str, ...] = ("random", "library", "image")


@dataclass(frozen=True)
class Case:
    """One puzzle, as the exporters see it."""

    index: int
    label: str
    payload: ExportPayload

    @property
    def size(self) -> int:
        return len(self.payload.grid)

    def describe(self) -> str:
        return f"case {self.index} ({self.label}, {self.size}x{self.size})"


def _payload(
    grid: list[list[bool]],
    *,
    seed: int,
    mode: str,
    size: int | None,
    density: int | None,
) -> ExportPayload:
    """A payload whose clues really are the grid's run-length encoding (INV-001).

    Derived rather than invented: EC-002 is about *finalized* puzzles, and a
    finalized puzzle's clues are its grid's encoding. A corpus of arbitrary
    integer tuples would still exercise the serializers, but it would no
    longer be a corpus of puzzles.
    """
    rows, columns = compute_clues(grid)
    return ExportPayload(
        grid=grid,
        row_clues=rows,
        column_clues=columns,
        seed=seed,
        mode=mode,
        size=size,
        density=density,
    )


def _random_grid(rng: random.Random, size: int, density: float) -> list[list[bool]]:
    """A random square grid at roughly ``density`` filled.

    Drawn here rather than through ``nonogram.sourcing.random_grid.generate``
    because that module enforces the 10x10..50x50 request range (AC-003/
    AC-004), while EC-002's property is about the export boundary and so has
    to reach the 1x1 end of the representable range as well. The draw is still
    seeded and reproducible, which is the only property of it this test needs.
    """
    return [[rng.random() < density for _ in range(size)] for _ in range(size)]


def _edge_grid(kind: str, size: int) -> list[list[bool]]:
    """The degenerate shapes a random draw would essentially never produce."""
    match kind:
        case "empty":  # every line encodes to the (0,) marker (AC-013)
            return [[False] * size for _ in range(size)]
        case "full":  # every line is one full-width run
            return [[True] * size for _ in range(size)]
        case "one-cell":  # a single filled cell adrift in empty lines
            grid = [[False] * size for _ in range(size)]
            grid[size // 2][size // 2] = True
            return grid
        case "stripes":  # alternating rows: full runs beside empty markers
            return [[row % 2 == 0] * size for row in range(size)]
        case "checkerboard":  # the most runs a line can hold
            return [[(row + column) % 2 == 0 for column in range(size)] for row in range(size)]
        case _:  # pragma: no cover - guards a typo in _EDGE_KINDS
            raise AssertionError(f"unknown edge grid {kind!r}")


#: The hand-picked cases, appended to the drawn ones.
_EDGE_KINDS: tuple[str, ...] = ("empty", "full", "one-cell", "stripes", "checkerboard")
_EDGE_SIZES: tuple[int, ...] = (1, 2, 3, 10, 49, 50)


def _corpus(count: int) -> list[Case]:
    """``count`` drawn cases plus the hand-picked ones, all reproducible.

    Sizes are cycled rather than sampled so every edge length from 1 to 50 is
    hit the same number of times — a uniform sample would leave some size
    uncovered on some seeds, which is the kind of gap a property test is
    supposed to close rather than open.
    """
    rng = random.Random(SEED)
    cases: list[Case] = []
    for index in range(count):
        size = SIZES[index % len(SIZES)]
        density = DENSITIES[index % len(DENSITIES)]
        # Provenance varies too, including the "never asked for" shape
        # ADR-0015 records as None rather than as zero.
        requested_size: int | None = None if index % 7 == 0 else size
        requested_density: int | None = None if index % 11 == 0 else int(density * 100)
        cases.append(
            Case(
                index,
                f"drawn d={density}",
                _payload(
                    _random_grid(rng, size, density),
                    seed=rng.getrandbits(63),
                    mode=_MODES[index % len(_MODES)],
                    size=requested_size,
                    density=requested_density,
                ),
            )
        )

    for kind in _EDGE_KINDS:
        for size in _EDGE_SIZES:
            index = len(cases)
            cases.append(
                Case(
                    index,
                    f"edge {kind}",
                    _payload(
                        _edge_grid(kind, size),
                        seed=index,
                        mode="random",
                        size=size,
                        density=None,
                    ),
                )
            )
    return cases


#: How many drawn cases run, on top of the hand-picked ones. Sized so every
#: edge length from 1 to 50 is drawn 40 times across the density spread —
#: comfortably above :data:`REQUIRED_CASES`, because the whole corpus costs
#: well under two seconds and the extra cases are free evidence.
CASE_COUNT = 2000

#: Built once at import: the corpus is a pure function of :data:`SEED`, and
#: both format tests run over the same cases, so a failure in one is
#: diagnosable against the other.
CASES: list[Case] = _corpus(CASE_COUNT)

#: Stride of the slice that additionally round-trips through real files.
#: Coprime with both the size cycle (50) and the density cycle (9) on purpose:
#: a stride sharing a factor with either — 20, say — would step through only
#: five distinct sizes, and the slice would silently stop being a spread.
_DISK_EVERY = 19


def _assert_round_trip(case: Case, decoded: ExportPayload, fmt: str) -> None:
    """EC-002's claim, and ADR-0015's, asserted as two separate claims."""
    original = case.payload

    # EC-002 proper: the puzzle itself, exactly — same values and same types,
    # with no normalisation applied to either side before comparing.
    assert decoded.grid == original.grid, f"{case.describe()}: {fmt} grid changed"
    assert decoded.row_clues == original.row_clues, (
        f"{case.describe()}: {fmt} row clues changed"
    )
    assert decoded.column_clues == original.column_clues, (
        f"{case.describe()}: {fmt} column clues changed"
    )
    assert all(isinstance(cell, bool) for row in decoded.grid for cell in row), (
        f"{case.describe()}: {fmt} grid decoded to something other than booleans"
    )
    assert isinstance(decoded.row_clues, tuple) and all(
        isinstance(clue, tuple) for clue in decoded.row_clues
    ), f"{case.describe()}: {fmt} clues decoded to the wrong container type"

    # ADR-0015, separately: the provenance travels with the puzzle, and a
    # parameter that was never requested comes back as None, not as zero.
    assert (decoded.seed, decoded.mode, decoded.size, decoded.density) == (
        original.seed,
        original.mode,
        original.size,
        original.density,
    ), f"{case.describe()}: {fmt} provenance changed"


def test_the_corpus_covers_what_ec_002_asks_for() -> None:
    """The corpus's own gate: the coverage the property claims, asserted.

    Without this, shrinking ``CASE_COUNT`` or narrowing ``DENSITIES`` would
    leave two green tests that no longer check what EC-002 names — the
    failure mode a property test is least able to notice about itself.
    """
    assert len(CASES) >= REQUIRED_CASES, (
        f"EC-002 needs >= {REQUIRED_CASES} cases, the corpus has {len(CASES)}"
    )
    assert {case.size for case in CASES} == set(SIZES), (
        "the corpus must cover every supported edge length from 1 to 50"
    )

    empty_lines = sum(
        1
        for case in CASES
        if (0,) in case.payload.row_clues or (0,) in case.payload.column_clues
    )
    full_lines = sum(
        1
        for case in CASES
        if (case.size,) in case.payload.row_clues
        or (case.size,) in case.payload.column_clues
    )
    unrequested = sum(
        1 for case in CASES if case.payload.size is None or case.payload.density is None
    )

    assert empty_lines >= 100, f"only {empty_lines} cases contain an all-empty line"
    assert full_lines >= 100, f"only {full_lines} cases contain an all-filled line"
    assert unrequested >= 100, (
        f"only {unrequested} cases leave size or density unrequested (ADR-0015's None)"
    )
    assert any(
        all(cell for row in case.payload.grid for cell in row) for case in CASES
    ), "no wholly filled grid in the corpus"
    assert any(
        not any(cell for row in case.payload.grid for cell in row) for case in CASES
    ), "no wholly empty grid in the corpus"


def test_round_trips_exactly_for_any_puzzle_as_json() -> None:
    """EC-002, JSON half, over the whole corpus.

    Runs the serializer pair rather than the file plumbing —
    ``document -> json.dumps -> decode`` is exactly the text ``render``
    writes, minus the indentation, and skipping the two thousand temporary
    files keeps the corpus affordable at full size. The bytes-on-disk path is
    checked separately, and end to end, by
    :func:`test_a_slice_of_the_corpus_round_trips_through_real_files` and by
    the two named AC tests below.
    """
    assert len(CASES) >= REQUIRED_CASES

    for case in CASES:
        text = json.dumps(json_export.document(case.payload), indent=2, ensure_ascii=False)
        _assert_round_trip(case, json_export.decode(text), "json")


def test_round_trips_exactly_for_any_puzzle_as_csv() -> None:
    """EC-002, CSV half — the same corpus, the same assertions.

    Flat CSV is the format with something to lose here: raggedness, the
    ``(0,)`` marker and the empty ``size``/``density`` cells all have to
    survive a representation that has no types of its own.
    """
    assert len(CASES) >= REQUIRED_CASES

    for case in CASES:
        _assert_round_trip(case, csv_export.decode(csv_export.document(case.payload)), "csv")


def test_a_slice_of_the_corpus_round_trips_through_real_files(tmp_path: Path) -> None:
    """The same property, but through ``render`` and ``read`` on disk.

    A pair that only ever met in memory could still be defeated by the file
    layer — an encoding, a newline translation, a truncated write. Every
    :data:`_DISK_EVERY`-th case makes that round trip for real; the stride
    keeps a spread of sizes and densities in it without paying the file cost
    for the whole corpus.
    """
    checked = 0
    for case in CASES[::_DISK_EVERY]:
        checked += 1
        json_path = tmp_path / "puzzle.json"
        csv_path = tmp_path / "puzzle.csv"
        json_export.render(case.payload, json_path)
        csv_export.render(case.payload, csv_path)

        _assert_round_trip(case, json_export.read(json_path), "json file")
        _assert_round_trip(case, csv_export.read(csv_path), "csv file")

    assert checked >= 40, f"only {checked} cases made the on-disk round trip"
    assert len({len(case.payload.grid) for case in CASES[::_DISK_EVERY]}) >= 20, (
        "the on-disk slice must still span a range of sizes"
    )


def test_the_two_formats_decode_to_the_same_payload() -> None:
    """One puzzle, two files, one puzzle again.

    FR-012 offers JSON *or* CSV; if they decoded to different payloads, the
    round-trip property could hold for each format separately while the two
    exports of one puzzle disagreed with each other.
    """
    for case in CASES:
        as_json = json_export.decode(json.dumps(json_export.document(case.payload)))
        as_csv = csv_export.decode(csv_export.document(case.payload))

        assert as_json == as_csv == case.payload, (
            f"{case.describe()}: the two formats disagree"
        )


# --------------------------------------------------------------------------
# AC-033 — TestExport_JSONRoundTripsExactly (EC-002's named instance)
# --------------------------------------------------------------------------


def test_json_round_trips_exactly(tmp_path: Path) -> None:
    """AC-033, on one puzzle the real pipeline finalized.

    The corpus above is built rather than generated, so this is the case that
    ties the property to an actual uniqueness-confirmed puzzle: same pinned
    seed as AC-031/AC-032, exported through ``export_puzzle`` exactly as a
    user's run would, then decoded and compared.
    """
    puzzle = generate(
        GenerationRequest(
            mode="random",
            size=10,
            density=50,
            seed=0,
            export_formats=("json",),
            out=tmp_path,
        )
    )
    assert puzzle.ready_for_export is True

    decoded = json_export.read(export_puzzle(puzzle)[0])

    expected = compute_clues(puzzle.grid)
    assert decoded.grid == puzzle.grid
    assert decoded.row_clues == expected.rows
    assert decoded.column_clues == expected.columns
    assert (decoded.seed, decoded.mode, decoded.size, decoded.density) == (
        0,
        "random",
        10,
        50,
    )


def test_csv_round_trips_exactly(tmp_path: Path) -> None:
    """EC-002's CSV instance of the same puzzle, for the same reason."""
    puzzle = generate(
        GenerationRequest(
            mode="random",
            size=10,
            density=50,
            seed=0,
            export_formats=("csv",),
            out=tmp_path,
        )
    )

    decoded = csv_export.read(export_puzzle(puzzle)[0])

    expected = compute_clues(puzzle.grid)
    assert decoded.grid == puzzle.grid
    assert (decoded.row_clues, decoded.column_clues) == (expected.rows, expected.columns)
    assert (decoded.seed, decoded.mode, decoded.size, decoded.density) == (
        0,
        "random",
        10,
        50,
    )
