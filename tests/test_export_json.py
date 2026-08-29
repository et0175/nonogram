"""COMP-007 tests: the JSON renderer, the format registry and the INV-002 gate.

AC / test-id mapping — the trace.yml names, kept traceable from these
pytest-idiomatic function names:

    AC-031  TestExport_WritesJSON              -> test_export_writes_json*
    INV-002 TestExport_RejectsUnverifiedPuzzle -> test_export_rejects_an_unverified_puzzle*

INV-002's gate is delivered by this card even though its acceptance criteria
are named against the other formats (AC-030 for PNG/SVG, AC-048 for PDF): the
gate is one check in COMP-002 that all five renderers inherit (ADR-0007), so it
is tested here, against the first format to reach it, and CARD-012/CARD-014 add
their per-format instances on top rather than a second gate.

Three things this file deliberately does *not* do. It does not assert AC-032 or
AC-033 (the CSV export and the exact round-trip, CARD-013). It does not fake the
uniqueness verdict where it can avoid it — the AC-031 test runs the real
pipeline at a pinned seed, and the scripted tests set the verdict through
``confirm_uniqueness`` exactly as the loop would, never by writing
``ready_for_export`` by hand. And it never writes outside ``tmp_path``.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from nonogram import cli, export, orchestrator
from nonogram.clues import compute_clues
from nonogram.errors import ExportRejected
from nonogram.export import json_export
from nonogram.orchestrator import GenerationRequest, Puzzle, export_puzzle, generate
from nonogram.solver import MANY

# --------------------------------------------------------------------------
# Helpers — same notation as tests/test_orchestrator.py: ``█`` filled, ``·`` empty.
# --------------------------------------------------------------------------

_FILLED = "█"


def _grid(*patterns: str) -> list[list[bool]]:
    return [[glyph == _FILLED for glyph in pattern] for pattern in patterns]


#: Exactly one solution (the same 2x2 the orchestrator tests pin on).
#:
#:     ██
#:     █·
UNIQUE = _grid("██", "█·")


def _puzzle(
    out: Path | None,
    *,
    grid: list[list[bool]] | None = None,
    solution_count: int | None = 1,
    formats: tuple[str, ...] = (export.JSON,),
    **request_fields: object,
) -> Puzzle:
    """A puzzle at the point the pipeline would hand it to the export step.

    Built by driving the aggregate the way :func:`generate` does — record a
    candidate, then report a verdict — so ``ready_for_export`` is only ever
    reached through INV-002's own transition. ``solution_count=None`` leaves
    the candidate unjudged, which is the "not ready" case the gate exists for.
    """
    fields: dict[str, object] = {
        "mode": "random",
        "size": 2,
        "density": 50,
        "seed": 7,
        "export_formats": formats,
        "out": out,
    }
    fields.update(request_fields)
    request = GenerationRequest(**fields)  # type: ignore[arg-type]
    puzzle = Puzzle(request=request, seed=request.seed or 0)
    puzzle.record_candidate(grid if grid is not None else UNIQUE)
    if solution_count is not None:
        puzzle.confirm_uniqueness(solution_count)
    return puzzle


def _written(directory: Path) -> list[Path]:
    return sorted(directory.iterdir())


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# The format registry — one row per format, and the only list of format names
# --------------------------------------------------------------------------


def test_the_registry_knows_the_json_format() -> None:
    """JSON is registered, and stays registered as later cards add their rows.

    Was ``FORMATS == (JSON,)`` while JSON was the only format; CARD-012 added
    the PNG and SVG rows and CARD-013 added csv, so what this asserts now is
    membership rather than the whole table — the table's *contents* belong to
    whichever card owns each row, and pinning the tuple here would make every
    later registration look like a regression in the JSON renderer's own test
    file.
    """
    assert export.JSON in export.FORMATS
    assert export.for_format(export.JSON).render is json_export.render
    assert len(set(export.FORMATS)) == len(export.FORMATS), "duplicate format name"


def test_a_registry_row_carries_its_extension_and_its_renderer() -> None:
    row = export.for_format(export.JSON)

    assert row.name == export.JSON
    assert row.extension == ".json"
    assert row.render is json_export.render


def test_an_unregistered_format_is_a_wiring_bug_not_a_domain_error() -> None:
    """Same choice as ``sourcing.for_mode``: argparse already rejected this
    for the user, so reaching here means the pipeline asked for a format that
    does not exist — not something to map onto an exit code."""
    with pytest.raises(ValueError, match="unknown export format 'xlsx'"):
        export.for_format("xlsx")


@pytest.mark.parametrize("name", export.FORMATS)
def test_every_registered_format_is_accepted_by_the_cli(name: str) -> None:
    args = cli.build_parser().parse_args(["generate", "--export", name])
    assert args.export_formats == [name]


def test_an_unregistered_format_is_rejected_by_the_cli() -> None:
    """``xlsx`` is the stand-in for "a format this build does not have", which
    used to be ``csv`` until CARD-013 registered it and ``pdf`` until CARD-014
    did. All five planned formats now exist, so the stand-in is a format the
    tool deliberately does not have — FR-012 answers the spreadsheet case with
    CSV — rather than the next card's."""
    with pytest.raises(SystemExit) as excinfo:
        cli.build_parser().parse_args(["generate", "--export", "xlsx"])
    assert excinfo.value.code == cli.ExitCode.USAGE


def test_registering_a_format_reaches_the_cli_without_editing_the_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The design claim behind deriving ``--export``'s choices from the registry.

    CARD-012/013/014 each add one row to ``export._FORMATS``. This stands in
    for that row and shows the adapter picking it up — the new format parses,
    and it is documented in ``--help`` — with ``cli.py`` untouched. If someone
    later re-hardcodes the choices, this test is what fails.
    """
    monkeypatch.setattr(export, "FORMATS", (export.JSON, "svg"))

    parser = cli.build_parser()

    assert parser.parse_args(["generate", "--export", "svg"]).export_formats == ["svg"]
    with pytest.raises(SystemExit):
        parser.parse_args(["generate", "--export", "pdf"])


def test_the_help_text_names_the_registered_formats(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit):
        cli.main(["generate", "--help"])

    out = capsys.readouterr().out
    for name in export.FORMATS:
        assert name in out


# --------------------------------------------------------------------------
# AC-031 — TestExport_WritesJSON
# --------------------------------------------------------------------------


def test_export_writes_json(tmp_path: Path) -> None:
    """AC-031, end to end and unmocked.

    Pinned seed: at 10x10 / 50% density, seed 0's first candidate is already
    unique — the same pin ``tests/test_orchestrator.py`` documents. The point
    of running the real pipeline here rather than a scripted aggregate is that
    "finalized, uniqueness-confirmed" is then the solver's word, not the test's.
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

    paths = export_puzzle(puzzle)

    assert len(paths) == 1
    written = paths[0]
    assert written.exists()
    assert written.suffix == ".json"
    assert _written(tmp_path) == [written]

    document = _load(written)
    # The *full* solution grid, every row of it — not the blank puzzle.
    assert document["grid"] == puzzle.grid
    assert len(document["grid"]) == 10
    assert all(len(row) == 10 for row in document["grid"])
    # ...and both clue sets, which INV-001 makes the encoding of that grid.
    assert document["clues"] == {
        "rows": [list(clue) for clue in compute_clues(puzzle.grid).rows],
        "columns": [list(clue) for clue in compute_clues(puzzle.grid).columns],
    }


def test_export_writes_json_for_a_scripted_puzzle(tmp_path: Path) -> None:
    """The same assertion at a size small enough to write out in full."""
    puzzle = _puzzle(tmp_path)

    document = _load(export_puzzle(puzzle)[0])

    assert document["grid"] == [[True, True], [True, False]]
    assert document["clues"] == {"rows": [[2], [1]], "columns": [[2], [1]]}


def test_the_export_records_the_seed(tmp_path: Path) -> None:
    """ADR-0015: the file traces back to the request that produced it."""
    puzzle = _puzzle(tmp_path, seed=4242)

    assert _load(export_puzzle(puzzle)[0])["seed"] == 4242


def test_the_export_records_an_auto_drawn_seed_too(tmp_path: Path) -> None:
    """The seed recorded is the run's *effective* one, so a run nobody seeded
    is still replayable from its own file (ADR-0015)."""
    puzzle = _puzzle(tmp_path, seed=None)
    puzzle.seed = 99

    assert _load(export_puzzle(puzzle)[0])["seed"] == 99


def test_the_export_records_the_generation_parameters(tmp_path: Path) -> None:
    puzzle = _puzzle(tmp_path, size=2, density=50)

    assert _load(export_puzzle(puzzle)[0])["request"] == {
        "mode": "random",
        "size": 2,
        "density": 50,
    }


def test_the_export_carries_a_schema_version(tmp_path: Path) -> None:
    assert _load(export_puzzle(_puzzle(tmp_path))[0])["version"] == (
        json_export.SCHEMA_VERSION
    )


# --------------------------------------------------------------------------
# Guardrail G-4 — the boundary type crosses, never the solver's bitmask
# --------------------------------------------------------------------------


def test_the_exported_grid_is_booleans_and_not_a_bitmask(tmp_path: Path) -> None:
    """ADR-0012's boundary type, cell by cell.

    An internal per-line bitmask would serialize as one integer per line; what
    EC-002's round-trip (CARD-013) will invert is this nested list of JSON
    ``true``/``false`` instead, with no bit order or mask width at the seam.
    """
    path = export_puzzle(_puzzle(tmp_path))[0]

    grid = _load(path)["grid"]
    assert isinstance(grid, list)
    assert all(isinstance(row, list) for row in grid)
    assert all(isinstance(cell, bool) for row in grid for cell in row)
    assert "true" in path.read_text(encoding="utf-8")


def test_the_exported_clues_are_arrays_of_integers(tmp_path: Path) -> None:
    clues = _load(export_puzzle(_puzzle(tmp_path))[0])["clues"]

    for direction in ("rows", "columns"):
        assert all(
            isinstance(run, int) and not isinstance(run, bool)
            for clue in clues[direction]
            for run in clue
        )


def test_the_document_is_built_without_touching_the_filesystem() -> None:
    """``document`` is separable from ``render`` — the shape is assertable on
    its own, and CARD-013's round-trip has one function to invert."""
    payload = export.ExportPayload(
        grid=[[True, False]],
        row_clues=((1,),),
        column_clues=((1,), (0,)),
        seed=1,
        mode="random",
    )

    assert json_export.document(payload)["grid"] == [[True, False]]


# --------------------------------------------------------------------------
# The decoder (CARD-013) — what it refuses
# --------------------------------------------------------------------------
#
# EC-002's round trip lives in ``tests/property/test_export_roundtrip.py``,
# stated over both formats at once. What is asserted here is the half a
# round-trip test structurally cannot see: an encoder/decoder pair that agreed
# on a wrong reading would round-trip perfectly. So every documented rejection
# gets a case, because a decoder that repaired what it read — coercing ``1``
# into ``true``, filling in a missing field — would still pass the property
# while having quietly altered the file.


def _document(**replacement: object) -> dict[str, object]:
    """A valid document with one field replaced — one defect at a time."""
    payload = export.ExportPayload(
        grid=[[True, False], [False, True]],
        row_clues=((1,), (1,)),
        column_clues=((1,), (1,)),
        seed=7,
        mode="random",
        size=2,
        density=50,
    )
    document = json_export.document(payload)
    document.update(replacement)
    return document


def test_the_decoder_inverts_the_document_exactly() -> None:
    payload = export.ExportPayload(
        grid=[[True, False]],
        row_clues=((1,),),
        column_clues=((1,), (0,)),
        seed=1,
        mode="random",
    )

    assert json_export.parse(json_export.document(payload)) == payload


@pytest.mark.parametrize(
    ("document", "message"),
    [
        pytest.param(_document(version=2), "unsupported JSON export version", id="future-version"),
        pytest.param(_document(version="1"), "expected an integer", id="version-as-string"),
        pytest.param({"seed": 1}, "missing field 'version'", id="missing-version"),
        pytest.param(_document(seed=None), "expected an integer", id="null-seed"),
        pytest.param(_document(seed=True), "expected an integer", id="bool-seed"),
        pytest.param(_document(request={"mode": "random", "size": 2}), "missing field 'density'", id="missing-parameter"),
        pytest.param(_document(request={"mode": 1, "size": None, "density": None}), "expected a string", id="non-string-mode"),
        pytest.param(_document(request=[]), "request: expected an object", id="request-not-an-object"),
        pytest.param(_document(grid=[[1, 0], [0, 1]]), "expected true or false", id="numeric-cells"),
        pytest.param(_document(grid=[[True, False], [True]]), "the grid is rectangular", id="ragged-grid"),
        pytest.param(_document(grid="TF"), "grid: expected an array", id="grid-as-string"),
        pytest.param(_document(clues={"rows": [[1], [1]]}), "missing field 'columns'", id="missing-clue-set"),
        pytest.param(_document(clues={"rows": [["1"], [1]], "columns": [[1], [1]]}), "expected an integer", id="clue-as-string"),
        pytest.param(_document(clues={"rows": [1, 1], "columns": [[1], [1]]}), "expected an array", id="clue-not-an-array"),
        pytest.param([], "document: expected an object", id="not-an-object"),
        pytest.param(
            _document(clues={"rows": [[1], [1]], "columns": [[1]]}),
            r"1 column clue\(s\) for a grid of 2 column\(s\)",
            id="column-clue-count-mismatch",
        ),
        pytest.param(
            _document(clues={"rows": [[1]], "columns": [[1], [1]]}),
            r"1 row clue\(s\) for a grid of 2 row\(s\)",
            id="row-clue-count-mismatch",
        ),
    ],
)
def test_the_decoder_rejects_a_malformed_document(document: object, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        json_export.parse(document)


def test_the_decoder_rejects_a_document_truncated_by_dropping_a_column_clue() -> None:
    """A realistic failure mode, not a synthetic one: a truncated download, a
    partial write or a hand-edited file can drop the trailing
    ``clues.columns`` entry from an otherwise well-formed export. Every field
    is still individually well-shaped, so only the cross-check against the
    grid's own width catches the missing entry.
    """
    payload = export.ExportPayload(
        grid=[[True, False, True], [False, True, False]],
        row_clues=((1, 1), (1,)),
        column_clues=((1,), (1,), (1,)),
        seed=3,
        mode="random",
    )
    document = json_export.document(payload)
    document["clues"]["columns"].pop()  # simulate a dropped trailing entry

    with pytest.raises(ValueError, match=r"2 column clue\(s\) for a grid of 3 column\(s\)"):
        json_export.parse(document)


def test_the_decoder_rejects_column_clues_that_do_not_match_the_grid_width() -> None:
    """The reviewer's counterexample, literally: a 2-column grid must not
    silently decode with ``column_clues=((1,),)``."""
    document = {
        "version": 1,
        "seed": 1,
        "request": {"mode": "random", "size": None, "density": None},
        "grid": [[True, False], [False, True]],
        "clues": {"rows": [[1], [1]], "columns": [[1]]},
    }

    with pytest.raises(ValueError, match=r"1 column clue\(s\) for a grid of 2 column\(s\)"):
        json_export.parse(document)


def test_the_decoder_accepts_an_empty_grid_with_no_clues() -> None:
    """The empty-grid convention (``clues.compute_clues``: an empty grid
    yields two empty clue sets) is what the new check must not reject."""
    document = {
        "version": 1,
        "seed": 1,
        "request": {"mode": "random", "size": None, "density": None},
        "grid": [],
        "clues": {"rows": [], "columns": []},
    }

    payload = json_export.parse(document)

    assert (payload.grid, payload.row_clues, payload.column_clues) == ([], (), ())


def test_the_decoder_rejects_text_that_is_not_json() -> None:
    """``json.JSONDecodeError`` is a ``ValueError``, so a caller has one
    exception type for "this file is not one of ours" either way."""
    with pytest.raises(ValueError):
        json_export.decode("not json at all")


def test_reading_a_file_inverts_writing_one(tmp_path: Path) -> None:
    path = export_puzzle(_puzzle(tmp_path, seed=11))[0]

    decoded = json_export.read(path)

    assert decoded.grid == UNIQUE
    assert (decoded.seed, decoded.mode) == (11, "random")


# --------------------------------------------------------------------------
# INV-002 — TestExport_RejectsUnverifiedPuzzle (the gate, in COMP-002)
# --------------------------------------------------------------------------


def test_export_rejects_an_unverified_puzzle(tmp_path: Path) -> None:
    """A candidate the solver has not judged is not exportable, and nothing is
    written on the way to finding that out."""
    puzzle = _puzzle(tmp_path, solution_count=None)

    with pytest.raises(ExportRejected, match="not ready for export"):
        export_puzzle(puzzle)

    assert _written(tmp_path) == []


@pytest.mark.parametrize(
    "solution_count",
    [pytest.param(0, id="no-solutions"), pytest.param(MANY, id="many-solutions")],
)
def test_export_rejects_a_puzzle_the_solver_did_not_call_unique(
    solution_count: int, tmp_path: Path
) -> None:
    puzzle = _puzzle(tmp_path, solution_count=solution_count)

    with pytest.raises(ExportRejected):
        export_puzzle(puzzle)

    assert _written(tmp_path) == []


def test_a_discarded_candidate_closes_the_gate_again(tmp_path: Path) -> None:
    """The gate tracks the *current* candidate: a puzzle that was ready and
    then took on a fresh grid is not exportable until that one is judged."""
    puzzle = _puzzle(tmp_path)
    puzzle.record_candidate(_grid("█·", "·█"))

    with pytest.raises(ExportRejected):
        export_puzzle(puzzle)


def test_the_gate_is_not_consulted_when_no_format_was_requested(
    tmp_path: Path,
) -> None:
    """A run that asked for no export cannot be refused one — and writes
    nothing, which is what keeps ``generate``'s CON-003 promise intact for
    callers that never export."""
    puzzle = _puzzle(tmp_path, solution_count=None, formats=())

    assert export_puzzle(puzzle) == ()
    assert _written(tmp_path) == []


def test_the_renderer_does_not_re_check_readiness(tmp_path: Path) -> None:
    """Guardrail G-3, structurally.

    The gate is one check in COMP-002 (ADR-0007's single-enforcement-point
    rule). COMP-007 therefore has no notion of readiness at all: it neither
    names the flag nor raises the error, and the payload it is handed carries
    neither. A renderer that "helpfully" re-checked would be the second
    enforcement point that can drift from the first.
    """
    package = Path(export.__file__).parent
    for module in sorted(package.glob("*.py")):
        source = module.read_text(encoding="utf-8")
        for forbidden in ("ready_for_export", "ExportRejected"):
            assert f"{forbidden}(" not in source and f".{forbidden}" not in source, (
                f"{module.name} looks like it re-checks INV-002"
            )

    assert not hasattr(export.ExportPayload, "ready_for_export")


# --------------------------------------------------------------------------
# The shared write-to---out plumbing: destination, filename, collisions
# --------------------------------------------------------------------------


def test_the_default_stem_follows_the_fr_015_naming_convention() -> None:
    """FR-015/AC-042's own format, reproduced so the filenames users get now
    keep their shape when the aggregate starts carrying a name of its own."""
    assert (
        export.default_stem("random", moment=datetime(2026, 8, 27, 14, 30))
        == "random-2026-08-27-1430"
    )


def test_the_default_stem_names_the_mode() -> None:
    assert export.default_stem("library").startswith("library-")


def test_the_export_lands_in_the_requested_directory(tmp_path: Path) -> None:
    destination = tmp_path / "puzzles"

    path = export_puzzle(_puzzle(destination))[0]

    assert path.parent == destination
    assert path.name.startswith("random-")
    assert path.name.endswith(".json")


def test_a_missing_destination_directory_is_created(tmp_path: Path) -> None:
    destination = tmp_path / "deeply" / "nested"

    export_puzzle(_puzzle(destination))

    assert destination.is_dir()


def test_the_default_destination_is_the_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``--out`` is optional; without it the file lands where the user is."""
    monkeypatch.chdir(tmp_path)

    path = export_puzzle(_puzzle(None))[0]

    assert path.parent == Path.cwd()
    assert _written(tmp_path) == [path]


def test_a_colliding_filename_is_suffixed_rather_than_overwritten(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ADR-0017: the export path is computed, so a second run in the same
    minute must not silently destroy the first run's artifact.

    The stem is pinned rather than left to the clock — three runs *do* share a
    minute in practice, but a test that only usually collides is a test that
    only usually checks anything.
    """
    monkeypatch.setattr(export, "default_stem", lambda mode, **kwargs: "puzzle")

    first = export_puzzle(_puzzle(tmp_path, seed=1))[0]
    second = export_puzzle(_puzzle(tmp_path, seed=2))[0]
    third = export_puzzle(_puzzle(tmp_path, seed=3))[0]

    assert {first, second, third} == set(_written(tmp_path))
    assert second.stem.endswith("-1")
    assert third.stem.endswith("-2")
    assert _load(first)["seed"] == 1
    assert _load(second)["seed"] == 2


def test_a_repeated_format_writes_one_file(tmp_path: Path) -> None:
    """``--export json --export json`` asked for JSON, not for two copies."""
    paths = export_puzzle(_puzzle(tmp_path, formats=("json", "json")))

    assert len(paths) == 1
    assert _written(tmp_path) == list(paths)


def test_several_formats_share_one_filename_stem(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One puzzle in several formats, not several differently-named files —
    the property CARD-012/013/014's rows inherit from this plumbing."""
    monkeypatch.setattr(export, "default_stem", lambda mode, **kwargs: "puzzle")
    rendered: list[Path] = []
    registry = dict(export._FORMATS)
    registry["svg"] = export.ExportFormat(
        "svg", ".svg", lambda payload, path: rendered.append(path) or path.touch()
    )
    monkeypatch.setattr(export, "_FORMATS", registry)

    paths = export_puzzle(_puzzle(tmp_path, formats=("json", "svg")))

    assert len(rendered) == 1
    assert [path.suffix for path in paths] == [".json", ".svg"]
    assert len({path.stem for path in paths}) == 1


# --------------------------------------------------------------------------
# The CLI, wired end to end (COMP-001 -> COMP-002 -> COMP-007)
# --------------------------------------------------------------------------


def test_the_cli_writes_the_file_and_reports_the_path(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The increment-1 walking skeleton, as a user runs it."""
    exit_code = cli.main(
        [
            "generate",
            "--mode",
            "random",
            "--size",
            "10",
            "--density",
            "50",
            "--seed",
            "42",
            "--export",
            "json",
            "--out",
            str(tmp_path),
        ]
    )

    assert exit_code == cli.ExitCode.OK
    written = _written(tmp_path)
    assert len(written) == 1
    assert str(written[0]) in capsys.readouterr().out
    assert _load(written[0])["seed"] == 42


def test_the_cli_writes_nothing_without_an_export_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    assert cli.main(["generate", "--size", "10", "--density", "50", "--seed", "42"]) == cli.ExitCode.OK
    assert _written(tmp_path) == []


def test_the_cli_echoes_a_seed_the_user_did_not_choose(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """ADR-0015: an unseeded run is still reproducible, because the drawn seed
    is printed at run time."""
    cli.main(
        ["generate", "--size", "10", "--density", "50", "--export", "json", "--out", str(tmp_path)]
    )

    out = capsys.readouterr().out
    seed = _load(_written(tmp_path)[0])["seed"]
    assert f"seed: {seed}" in out


def test_the_cli_does_not_echo_a_seed_the_user_chose(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cli.main(
        ["generate", "--size", "10", "--density", "50", "--seed", "42", "--out", str(tmp_path)]
    )

    assert "seed:" not in capsys.readouterr().out


def test_a_rejected_export_reaches_the_user_as_exit_code_five(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """INV-002 refusing an export is a documented outcome, not a traceback."""
    unready = _puzzle(tmp_path, solution_count=None)
    monkeypatch.setattr(orchestrator, "generate", lambda request: unready)

    exit_code = cli.main(
        [
            "generate",
            "--size",
            "10",
            "--density",
            "50",
            "--export",
            "json",
            "--out",
            str(tmp_path),
        ]
    )

    assert exit_code == cli.ExitCode.EXPORT_REJECTED
    assert "not ready for export" in capsys.readouterr().err
    assert _written(tmp_path) == []


def test_an_out_directory_that_is_actually_a_file_reaches_the_user_cleanly(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Review finding (cycle 1): ``--out`` colliding with an existing file
    made ``directory.mkdir(..., exist_ok=True)`` raise ``FileExistsError`` —
    an ``OSError`` subclass, not a ``NonogramError`` — which used to escape
    ``main()`` as a raw traceback instead of a clean message and exit code.

    Reproduces the reviewer's exact repro command (mode/size/density/seed),
    against a real ``--out`` collision rather than a mock, so the fix is
    pinned at the same layer the crash was found in: the CLI's own exception
    handling, not the export plumbing that already documents the ``OSError``.
    """
    blocked = tmp_path / "notadir"
    blocked.write_text("not a directory", encoding="utf-8")

    exit_code = cli.main(
        [
            "generate",
            "--size",
            "10",
            "--density",
            "40",
            "--seed",
            "3",
            "--export",
            "json",
            "--out",
            str(blocked),
        ]
    )

    assert exit_code == cli.ExitCode.EXPORT_REJECTED
    captured = capsys.readouterr()
    assert captured.err.startswith(f"{cli.PROG}: error: ")
    assert "Traceback" not in captured.err
    assert blocked.read_text(encoding="utf-8") == "not a directory"
