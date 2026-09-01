"""EC-002 / FR-012 / ADR-0023: what an export writes, and what it reads back.

    PropertyTest_Export_RoundTripsExactlyForAnyPuzzle
        -> test_round_trips_exactly_for_any_puzzle_as_json
        -> test_round_trips_exactly_for_any_puzzle_as_csv
        -> test_a_slice_of_the_corpus_round_trips_through_real_files
        -> test_the_two_formats_decode_to_the_same_payload
        -> test_the_corpus_covers_what_ec_002_asks_for  (the corpus's own gate)

    PropertyTest_Export_MetadataCarriesBothDimensionsForAnyPuzzle  (ADR-0023/R1)
        -> test_property_export_metadata_carries_both_dimensions_for_any_puzzle

    PropertyTest_Export_RejectsEveryVersionOtherThanItsOwn  (ADR-0023/R2)
        -> test_property_export_rejects_every_version_other_than_its_own

    AC-033  TestExport_JSONRoundTripsExactly -> test_json_round_trips_exactly
            (EC-002's named instance, on one real pipeline-finalized puzzle;
             test_csv_round_trips_exactly is the CSV instance beside it)

    AC-060  TestExport_JSONRoundTripsRectangularDimensions
                -> test_json_round_trips_rectangular_dimensions
    AC-061  TestExport_CSVRoundTripsRectangularDimensions
                -> test_csv_round_trips_rectangular_dimensions

The three ADR-0023 tests live here, beside EC-002's, because they are claims
about the same pair of functions over the same corpus. Splitting them into the
per-format files would mean two copies of the corpus, and the metadata property
is only worth anything *because* the corpus contains rectangles.

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

Four things the corpus is built to contain, because EC-002 and ADR-0023 name
them:

* **The whole supported size range, in both dimensions.** Every edge length
  from 1 to 50 appears as a width and as a height —
  asserted, not hoped for. 1x1 is where a one-cell grid and a one-run clue
  coincide; 50x50 is where a row is 50 CSV cells wide.
* **Rectangles, in the majority.** Since ADR-0023 the extent is two fields
  rather than one, and the failure this property now exists to catch is a
  decoder that reconstructs one dimension from the other — from its partner,
  or from the grid. A corpus of squares cannot catch it: every wrong answer
  is right on a square. So most drawn cases are non-square, in both
  orientations, and the corpus gate asserts a floor on how many.
* **A density spread including both extremes.** An all-empty line is the
  ``(0,)`` marker (AC-013) and an all-filled line is a single full-width run;
  both are legal sourcing outcomes (CARD-003) and both are the shapes a flat
  format is most likely to mangle — ``(0,)`` into ``()``, or a blank cell into
  a zero.
* **Hand-picked degenerate shapes** the random draw would essentially never
  produce: fully empty and fully filled grids at both ends of the size range,
  single-row and single-column grids, a single filled cell in a large grid,
  maximal-run stripes and a checkerboard (the most clue-runs a line can hold),
  and payloads whose ``width``/``height``/``density`` were never requested at
  all (``None``, not zero) — including the mixed case where one half of the
  extent pair was asked for and the other was not.
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

#: EC-002's non-square floor. A corpus of squares cannot discharge the
#: round-trip property any more (see the corpus gate for why), so the count is
#: a named bar rather than an accident of the cycle strides. This is the bar
#: that actually binds: :data:`REQUIRED_CASES` above is the older, weaker floor
#: and a corpus small enough to fail it now fails this one first.
REQUIRED_NON_SQUARE_CASES = 1500

#: The decoupling floor. Not a size bar but a *shape* bar: the fewest distinct
#: heights any single width may appear with. 1 would mean height is a function
#: of width — a corpus that no longer discharges EC-002 however large it is.
#: Measured on the shipped corpus: 40.
REQUIRED_HEIGHTS_PER_WIDTH = 10

#: The edge lengths this corpus sweeps. Deliberately 1..50, WIDER than
#: CON-011's supported 10..30 request range: the export format is a pure
#: function of the payload it is handed and must round-trip any extent, so
#: the corpus is not bounded by what a request can ask for. It formerly
#: cited AC-038's ceiling of 50 as its authority; AC-038 was SUPERSEDED by
#: AC-084 under CON-011 (MAX_SIZE 30), so that citation was doubly wrong —
#: a stale id, and the wrong kind of bound for this corpus (cycle-2 F-202).
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
    def width(self) -> int:
        return len(self.payload.grid[0])

    @property
    def height(self) -> int:
        return len(self.payload.grid)

    def describe(self) -> str:
        return f"case {self.index} ({self.label}, {self.width}x{self.height})"


def _payload(
    grid: list[list[bool]],
    *,
    seed: int,
    mode: str,
    width: int | None,
    height: int | None,
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
        width=width,
        height=height,
        density=density,
    )


def _random_grid(
    rng: random.Random, width: int, height: int, density: float
) -> list[list[bool]]:
    """A random ``width`` x ``height`` grid at roughly ``density`` filled.

    Drawn here rather than through ``nonogram.sourcing.random_grid.generate``
    because that module enforces the request range (CON-011: 10..30 per side
    since 2026-08-31, superseding the 10x10..50x50 this line used to name) (AC-003/
    AC-004), while EC-002's property is about the export boundary and so has
    to reach the 1x1 end of the representable range as well. The draw is still
    seeded and reproducible, which is the only property of it this test needs.
    """
    return [[rng.random() < density for _ in range(width)] for _ in range(height)]


def _edge_grid(kind: str, width: int, height: int) -> list[list[bool]]:
    """The degenerate shapes a random draw would essentially never produce."""
    match kind:
        case "empty":  # every line encodes to the (0,) marker (AC-013)
            return [[False] * width for _ in range(height)]
        case "full":  # every line is one full-width run
            return [[True] * width for _ in range(height)]
        case "one-cell":  # a single filled cell adrift in empty lines
            grid = [[False] * width for _ in range(height)]
            grid[height // 2][width // 2] = True
            return grid
        case "stripes":  # alternating rows: full runs beside empty markers
            return [[row % 2 == 0] * width for row in range(height)]
        case "checkerboard":  # the most runs a line can hold
            return [
                [(row + column) % 2 == 0 for column in range(width)]
                for row in range(height)
            ]
        case _:  # pragma: no cover - guards a typo in _EDGE_KINDS
            raise AssertionError(f"unknown edge grid {kind!r}")


#: The hand-picked cases, appended to the drawn ones.
_EDGE_KINDS: tuple[str, ...] = ("empty", "full", "one-cell", "stripes", "checkerboard")
#: Hand-picked extents. Squares stay (the version-1 corpus was all squares and
#: those cases must keep holding), and rectangles are added on both sides of
#: square — including 30x12, the card's worked example, in both orientations,
#: and the 1xN / Nx1 degenerate strips where a decoder that reconstructs one
#: dimension from the other goes wrong most visibly.
_EDGE_SHAPES: tuple[tuple[int, int], ...] = (
    (1, 1), (2, 2), (3, 3), (10, 10), (49, 49), (50, 50),
    (1, 2), (2, 1), (2, 3), (3, 2), (12, 30), (30, 12),
    (1, 50), (50, 1), (49, 50), (50, 49),
)


def _corpus(count: int) -> list[Case]:
    """``count`` drawn cases plus the hand-picked ones, all reproducible.

    Sizes are cycled rather than sampled so every edge length from 1 to 50 is
    hit the same number of times — a uniform sample would leave some size
    uncovered on some seeds, which is the kind of gap a property test is
    supposed to close rather than open.

    Width and height cycle on *different* strides, so the corpus is mostly
    rectangular rather than mostly square.

    **The decoupler is the ``index // len(SIZES)`` term, not the stride.**
    Writing ``index = 50q + r``, width is ``r`` and height collapses to
    ``(3r + q) mod 50`` — it is ``q``, the lap counter, that makes a given
    width meet many different heights. The coprime stride 3 only spreads the
    heights within a lap; ``(index * 3) % 50`` *alone* is a bijection of
    ``r`` and would pin height to a pure function of width, which is exactly
    the degeneracy that lets a decoder infer one extent from the other and
    still pass. That is not a hypothetical: it survives every other assertion
    in this module, so the corpus gate asserts the decoupling directly rather
    than trusting this paragraph.

    Squares still occur (every 50th case or so) and the hand-picked shapes
    below add more, because AC-031..033's square round-trips must keep holding
    too.
    """
    rng = random.Random(SEED)
    cases: list[Case] = []
    for index in range(count):
        width = SIZES[index % len(SIZES)]
        height = SIZES[(index * 3 + index // len(SIZES)) % len(SIZES)]
        density = DENSITIES[index % len(DENSITIES)]
        # Provenance varies too, including the "never asked for" shape
        # ADR-0015 records as None rather than as zero. The two extents are
        # dropped independently: a document carrying one of the pair but not
        # the other is a shape the decoder has to survive (ADR-0023/R1).
        requested_width: int | None = None if index % 7 == 0 else width
        requested_height: int | None = None if index % 13 == 0 else height
        requested_density: int | None = None if index % 11 == 0 else int(density * 100)
        cases.append(
            Case(
                index,
                f"drawn d={density}",
                _payload(
                    _random_grid(rng, width, height, density),
                    seed=rng.getrandbits(63),
                    mode=_MODES[index % len(_MODES)],
                    width=requested_width,
                    height=requested_height,
                    density=requested_density,
                ),
            )
        )

    for kind in _EDGE_KINDS:
        for width, height in _EDGE_SHAPES:
            index = len(cases)
            cases.append(
                Case(
                    index,
                    f"edge {kind}",
                    _payload(
                        _edge_grid(kind, width, height),
                        seed=index,
                        mode="random",
                        width=width,
                        height=height,
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
    assert (
        decoded.seed,
        decoded.mode,
        decoded.width,
        decoded.height,
        decoded.density,
    ) == (
        original.seed,
        original.mode,
        original.width,
        original.height,
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
    assert {case.width for case in CASES} == set(SIZES), (
        "the corpus must cover every supported edge length from 1 to 50 as a WIDTH"
    )
    assert {case.height for case in CASES} == set(SIZES), (
        "the corpus must cover every supported edge length from 1 to 50 as a HEIGHT"
    )

    # EC-002's new failure mode, and the reason a square-only corpus can no
    # longer discharge it: what can break fidelity now is a decoder that
    # reconstructs one dimension from the other, and every square case in the
    # corpus is consistent with exactly that bug. So the non-square count is
    # asserted here rather than left to follow from how the cycles happen to
    # line up — narrowing the strides back to a square corpus must FAIL this
    # gate, not silently weaken the two properties below.
    non_square = sum(1 for case in CASES if case.width != case.height)
    squares = len(CASES) - non_square
    assert non_square >= REQUIRED_NON_SQUARE_CASES, (
        f"EC-002 needs >= {REQUIRED_NON_SQUARE_CASES} non-square cases, "
        f"the corpus has {non_square}"
    )
    # And squares must not vanish either: AC-031..033 are square round-trips.
    assert squares >= 50, f"only {squares} square cases left in the corpus"

    # Both orientations of the same shape, so no test can pass by assuming
    # width <= height (or the reverse).
    assert any(case.width > case.height for case in CASES), "no wide cases"
    assert any(case.height > case.width for case in CASES), "no tall cases"

    # The property the non-square floor above does NOT give us. A corpus can be
    # 97% non-square and still be degenerate: if height is a pure function of
    # width, a decoder that computes one extent from the other round-trips
    # every case perfectly. Measured on this corpus, every width meets 40
    # distinct heights; the bar is set well below that so ordinary tuning does
    # not trip it, but any change collapsing height onto width does.
    heights_per_width: dict[int, set[int]] = {}
    for case in CASES:
        heights_per_width.setdefault(case.width, set()).add(case.height)
    thinnest = min(len(heights) for heights in heights_per_width.values())
    assert thinnest >= REQUIRED_HEIGHTS_PER_WIDTH, (
        f"some width is paired with only {thinnest} distinct height(s): the "
        "corpus has collapsed height onto width, and a decoder that infers "
        "one extent from the other would pass it"
    )

    empty_lines = sum(
        1
        for case in CASES
        if (0,) in case.payload.row_clues or (0,) in case.payload.column_clues
    )
    full_lines = sum(
        1
        for case in CASES
        if (case.width,) in case.payload.row_clues
        or (case.height,) in case.payload.column_clues
    )
    unrequested = sum(
        1
        for case in CASES
        if case.payload.width is None
        or case.payload.height is None
        or case.payload.density is None
    )

    # The docstring promises a case where one extent was asked for and the
    # other was not; `unrequested` above is an `or` across three fields and a
    # corpus with only `density=None` would satisfy it. Gate the shape itself.
    mixed_extent = sum(
        1
        for case in CASES
        if (case.payload.width is None) != (case.payload.height is None)
    )
    assert mixed_extent >= 50, (
        f"only {mixed_extent} cases record one extent but not the other"
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
    # A square request, so ADR-0023's pair records 10 twice — the orchestrator
    # feeds both extents from the one scalar until CARD-027 (FR-018) gives the
    # request a pair of its own. Asserted as two fields, not one, so this test
    # keeps meaning the same thing after that card lands.
    assert (decoded.seed, decoded.mode, decoded.width, decoded.height, decoded.density) == (
        0,
        "random",
        10,
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
    # A square request, so ADR-0023's pair records 10 twice — the orchestrator
    # feeds both extents from the one scalar until CARD-027 (FR-018) gives the
    # request a pair of its own. Asserted as two fields, not one, so this test
    # keeps meaning the same thing after that card lands.
    assert (decoded.seed, decoded.mode, decoded.width, decoded.height, decoded.density) == (
        0,
        "random",
        10,
        10,
        50,
    )


# --------------------------------------------------------------------------
# ADR-0023's two rules, as properties over the same corpus
# --------------------------------------------------------------------------


def test_property_export_metadata_carries_both_dimensions_for_any_puzzle() -> None:
    """PropertyTest_Export_MetadataCarriesBothDimensionsForAnyPuzzle (ADR-0023/R1).

    Asserted on the *serialized bytes*, not on a decoded payload, because the
    rule is about what the file carries. A decoder that reconstructed height
    from the grid it just read would satisfy a round-trip assertion perfectly
    while writing a document that had lost the value — which is precisely the
    version-1 shape ADR-0023 replaced.

    Three claims per case, both formats: both extent fields are present, a
    scalar ``size`` is absent, and the value written is the one asked for
    (including ``None``, which ADR-0015 distinguishes from zero).
    """
    checked = 0
    for case in CASES:
        payload = case.payload

        request = json_export.document(payload)["request"]
        assert "width" in request and "height" in request, (
            f"{case.describe()}: JSON request block is missing an extent field"
        )
        assert "size" not in request, (
            f"{case.describe()}: JSON still writes a scalar 'size' (schema v1)"
        )
        assert (request["width"], request["height"]) == (payload.width, payload.height), (
            f"{case.describe()}: JSON extent is not the one requested"
        )

        # Only the #meta block: the document continues into the grid and clue
        # sections, which are not key/value rows.
        meta_lines: list[str] = []
        for line in csv_export.document(payload).splitlines()[1:]:
            if line.startswith("#"):
                break
            if line:
                meta_lines.append(line)
        meta = dict(line.split(",", 1) for line in meta_lines)
        assert "width" in meta and "height" in meta, (
            f"{case.describe()}: CSV #meta is missing an extent key"
        )
        assert "size" not in meta, (
            f"{case.describe()}: CSV still writes a scalar 'size' (schema v1)"
        )
        # None is written as an empty value and must not become "0" or "None".
        assert meta["width"] == ("" if payload.width is None else str(payload.width)), (
            f"{case.describe()}: CSV width {meta['width']!r} is not what was requested"
        )
        assert meta["height"] == ("" if payload.height is None else str(payload.height)), (
            f"{case.describe()}: CSV height {meta['height']!r} is not what was requested"
        )
        checked += 1

    assert checked >= REQUIRED_CASES, (
        f"ADR-0023/R1 needs >= {REQUIRED_CASES} cases, checked {checked}"
    )
    # Non-vacuous in the direction that matters: the claim is only meaningful
    # if the corpus contains documents whose two extents actually differ.
    differing = sum(
        1
        for case in CASES
        if case.payload.width is not None
        and case.payload.height is not None
        and case.payload.width != case.payload.height
    )
    assert differing >= REQUIRED_NON_SQUARE_CASES // 2, (
        f"only {differing} cases write two different extents"
    )


def test_property_export_rejects_every_version_other_than_its_own() -> None:
    """PropertyTest_Export_RejectsEveryVersionOtherThanItsOwn (ADR-0023/R2).

    Every version a document can declare except the decoder's own is refused
    by exact comparison, with an error naming both numbers — never a
    best-effort read. Version 1 is in the sweep as one case among many rather
    than as a special one, which is the point of G-3: there is no migration
    path, so the superseded version is not privileged over any other wrong
    value.
    """
    sample = CASES[:: max(1, len(CASES) // 40)]
    assert len(sample) >= 20, "the version sweep needs a spread of documents"

    # Swept per format against ITS OWN version. ADR-0023 bumped both to 2
    # together, but nothing binds them: the day CSV moves to 3 alone, a shared
    # list would quietly start asserting that CSV rejects its own documents.
    candidates = (*range(0, 12), 12, 20, 99, 1000, -1)
    wrong_by_format = {
        "json": [v for v in candidates if v != json_export.SCHEMA_VERSION],
        "csv": [v for v in candidates if v != csv_export.SCHEMA_VERSION],
    }
    assert 1 in wrong_by_format["json"] and 1 in wrong_by_format["csv"], (
        "the superseded version must be in both sweeps"
    )

    for case in sample:
        for version in wrong_by_format["json"]:
            document = json_export.document(case.payload)
            document["version"] = version
            try:
                json_export.decode(json.dumps(document))
            except ValueError as error:
                message = str(error)
                # The phrase, not a loose digit: a bare `str(version) in
                # message` passes on "version 2" when sweeping 12 or 20, which
                # is why those two are now in the candidate list.
                assert f"version {version}" in message and (
                    f"version {json_export.SCHEMA_VERSION}" in message
                    or f"expected {json_export.SCHEMA_VERSION}" in message
                    or f"of version {json_export.SCHEMA_VERSION}" in message
                ), (
                    f"{case.describe()}: JSON error {message!r} does not name "
                    f"both {version} and {json_export.SCHEMA_VERSION}"
                )
            else:  # pragma: no cover - a pass here is the failure
                raise AssertionError(
                    f"{case.describe()}: JSON accepted version {version}"
                )

        for version in wrong_by_format["csv"]:
            text = csv_export.document(case.payload).replace(
                f"version,{csv_export.SCHEMA_VERSION}", f"version,{version}", 1
            )
            try:
                csv_export.decode(text)
            except ValueError as error:
                message = str(error)
                assert f"version {version}" in message and (
                    f"version {csv_export.SCHEMA_VERSION}" in message
                    or f"expected {csv_export.SCHEMA_VERSION}" in message
                    or f"of version {csv_export.SCHEMA_VERSION}" in message
                ), (
                    f"{case.describe()}: CSV error {message!r} does not name "
                    f"both {version} and {csv_export.SCHEMA_VERSION}"
                )
            else:  # pragma: no cover - a pass here is the failure
                raise AssertionError(f"{case.describe()}: CSV accepted version {version}")

    # The decoder's own version must still be accepted, or the test above
    # would pass just as well against a decoder that refuses everything.
    for case in sample:
        assert json_export.decode(json.dumps(json_export.document(case.payload))).grid == (
            case.payload.grid
        )
        assert csv_export.decode(csv_export.document(case.payload)).grid == case.payload.grid


# --------------------------------------------------------------------------
# AC-060 / AC-061 — the card's two headline criteria, as named tests
# --------------------------------------------------------------------------
#
# The corpus above round-trips 30x12 among two thousand other shapes, but
# neither AC is discharged by "it is in there somewhere": both name a test,
# and a named check-ref that resolves to nothing is how an untested criterion
# comes to read as covered. Both go through a real file (render -> read), not
# document()/decode(), because the criterion is about an exported puzzle.


def _rectangular_payload() -> ExportPayload:
    """A 30 wide x 12 tall puzzle — deliberately not square, and deliberately
    not symmetric under transposition, so a decoder that swapped the two or
    derived one from the grid could not pass by coincidence."""
    grid = [[(row + column) % 3 == 0 for column in range(30)] for row in range(12)]
    rows, columns = compute_clues(grid)
    return ExportPayload(
        grid=grid,
        row_clues=rows,
        column_clues=columns,
        seed=4242,
        mode="random",
        width=30,
        height=12,
        density=None,
    )


def test_json_round_trips_rectangular_dimensions(tmp_path: Path) -> None:
    """AC-060: a 30x12 puzzle exported as JSON decodes back with width 30 and
    height 12, both read from the file's metadata rather than inferred."""
    payload = _rectangular_payload()
    path = tmp_path / "rectangle.json"
    json_export.render(payload, path)

    # Read from the file's own bytes: the extent must be recorded, not implied.
    request = json.loads(path.read_text(encoding="utf-8"))["request"]
    assert (request["width"], request["height"]) == (30, 12)

    decoded = json_export.read(path)
    assert decoded.width == 30
    assert decoded.height == 12
    assert (len(decoded.grid[0]), len(decoded.grid)) == (30, 12)
    _assert_round_trip(Case(0, "AC-060 30x12", payload), decoded, "json")


def test_csv_round_trips_rectangular_dimensions(tmp_path: Path) -> None:
    """AC-061: the same puzzle through CSV, for the same reason."""
    payload = _rectangular_payload()
    path = tmp_path / "rectangle.csv"
    csv_export.render(payload, path)

    text = path.read_text(encoding="utf-8")
    assert "width,30" in text and "height,12" in text
    assert "size," not in text  # the version-1 scalar must be gone

    decoded = csv_export.read(path)
    assert decoded.width == 30
    assert decoded.height == 12
    assert (len(decoded.grid[0]), len(decoded.grid)) == (30, 12)
    _assert_round_trip(Case(0, "AC-061 30x12", payload), decoded, "csv")
