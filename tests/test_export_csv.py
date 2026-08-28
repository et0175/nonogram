"""COMP-007 tests: the CSV renderer, its layout and its decoder (FR-012).

AC / test-id mapping — the trace.yml names, kept traceable from these
pytest-idiomatic function names:

    AC-032  TestExport_WritesCSV  -> test_export_writes_csv*

EC-002's round-trip property, and AC-033's named JSON instance of it, live in
``tests/property/test_export_roundtrip.py`` — the property is stated over both
formats at once, so both belong in one file. What is asserted *here* is the
half that file deliberately does not: the CSV file's actual layout, cell by
cell, and what the decoder refuses. A round-trip test alone cannot see either
— an encoder/decoder pair that agreed on a wrong or ambiguous format would
round-trip perfectly — so the layout documented in ``csv_export``'s docstring
is pinned by example below, and every documented rejection has a case.

Same conventions as ``tests/test_export_json.py``: ``█`` filled, ``·`` empty,
puzzles reach ``ready_for_export`` only through INV-002's own transition, and
nothing is ever written outside ``tmp_path``.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

import pytest

from nonogram import cli, export
from nonogram.clues import compute_clues
from nonogram.export import csv_export, json_export
from nonogram.orchestrator import GenerationRequest, Puzzle, export_puzzle, generate

# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

_FILLED = "█"


def _grid(*patterns: str) -> list[list[bool]]:
    return [[glyph == _FILLED for glyph in pattern] for pattern in patterns]


#: The 4x4 the module docstring's worked example is written against.
#:
#:     ██··
#:     ····
#:     ████
#:     ·██·
EXAMPLE = _grid("██··", "····", "████", "·██·")


def _payload(
    grid: list[list[bool]] | None = None,
    **fields: object,
) -> export.ExportPayload:
    """A payload with clues that really are the grid's (INV-001)."""
    cells = EXAMPLE if grid is None else grid
    rows, columns = compute_clues(cells)
    defaults: dict[str, object] = {
        "grid": cells,
        "row_clues": rows,
        "column_clues": columns,
        "seed": 42,
        "mode": "random",
        "size": len(cells),
        "density": 50,
    }
    defaults.update(fields)
    return export.ExportPayload(**defaults)  # type: ignore[arg-type]


def _puzzle(out: Path, *, grid: list[list[bool]] | None = None, **request_fields: object) -> Puzzle:
    """A puzzle at the point the pipeline would hand it to the export step."""
    fields: dict[str, object] = {
        "mode": "random",
        "size": 2,
        "density": 50,
        "seed": 7,
        "export_formats": (export.CSV,),
        "out": out,
    }
    fields.update(request_fields)
    request = GenerationRequest(**fields)  # type: ignore[arg-type]
    puzzle = Puzzle(request=request, seed=request.seed or 0)
    puzzle.record_candidate(grid if grid is not None else _grid("██", "█·"))
    puzzle.confirm_uniqueness(1)
    return puzzle


def _rows(text: str) -> list[list[str]]:
    return list(csv.reader(io.StringIO(text, newline="")))


def _section(text: str, marker: str) -> list[list[str]]:
    """The data rows of one section, by the file's own marker convention."""
    rows = _rows(text)
    start = rows.index([marker]) + 1
    body: list[list[str]] = []
    for row in rows[start:]:
        if row and row[0].startswith("#"):
            break
        body.append(row)
    return body


# --------------------------------------------------------------------------
# The registry — CARD-013's one added row
# --------------------------------------------------------------------------


def test_the_registry_knows_the_csv_format() -> None:
    assert export.CSV in export.FORMATS


def test_the_csv_registry_row_carries_its_extension_and_its_renderer() -> None:
    row = export.for_format(export.CSV)

    assert row.name == export.CSV
    assert row.extension == ".csv"
    assert row.render is csv_export.render


def test_the_cli_accepts_csv_without_the_adapter_being_edited() -> None:
    """The registry's whole point (CARD-007): ``--export csv`` works because
    of the row above, not because ``cli.py`` learned a new string."""
    assert cli.build_parser().parse_args(
        ["generate", "--export", "csv"]
    ).export_formats == ["csv"]


# --------------------------------------------------------------------------
# AC-032 — TestExport_WritesCSV
# --------------------------------------------------------------------------


def test_export_writes_csv(tmp_path: Path) -> None:
    """AC-032, end to end and unmocked.

    Same pinned seed as ``test_export_json``'s AC-031: at 10x10 / 50% density,
    seed 0's first candidate is already unique, so "finalized,
    uniqueness-confirmed" is the solver's word here rather than the test's.
    """
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
    assert puzzle.ready_for_export is True

    paths = export_puzzle(puzzle)

    assert len(paths) == 1
    written = paths[0]
    assert written.exists()
    assert written.suffix == ".csv"
    assert sorted(tmp_path.iterdir()) == [written]

    text = written.read_text(encoding="utf-8")
    # The *full* solution grid, every row of it — not the blank puzzle.
    grid = _section(text, csv_export.GRID)
    assert len(grid) == 10
    assert all(len(row) == 10 for row in grid)
    assert grid == [["1" if cell else "0" for cell in row] for row in puzzle.grid]
    # ...and both clue sets, which INV-001 makes the encoding of that grid.
    expected = compute_clues(puzzle.grid)
    assert _section(text, csv_export.ROW_CLUES) == [
        [str(run) for run in clue] for clue in expected.rows
    ]
    assert _section(text, csv_export.COLUMN_CLUES) == [
        [str(run) for run in clue] for clue in expected.columns
    ]


def test_export_writes_csv_for_a_scripted_puzzle(tmp_path: Path) -> None:
    """The same assertion at a size small enough to write out in full."""
    text = export_puzzle(_puzzle(tmp_path))[0].read_text(encoding="utf-8")

    assert _section(text, csv_export.GRID) == [["1", "1"], ["1", "0"]]
    assert _section(text, csv_export.ROW_CLUES) == [["2"], ["1"]]
    assert _section(text, csv_export.COLUMN_CLUES) == [["2"], ["1"]]


def test_the_csv_export_records_the_seed_and_parameters(tmp_path: Path) -> None:
    """ADR-0015: the file traces back to the request that produced it — the
    CSV export carries the same provenance the JSON one does, or the two
    formats would not be interchangeable representations of one puzzle."""
    text = export_puzzle(_puzzle(tmp_path, seed=4242, size=2, density=50))[0].read_text(
        encoding="utf-8"
    )

    assert _section(text, csv_export.META) == [
        ["version", str(csv_export.SCHEMA_VERSION)],
        ["seed", "4242"],
        ["mode", "random"],
        ["size", "2"],
        ["density", "50"],
    ]


def test_json_and_csv_of_one_puzzle_decode_to_the_same_payload(tmp_path: Path) -> None:
    """The two FR-012 formats are two spellings of one export, not two
    different exports: whichever a user keeps, they hold the same puzzle."""
    puzzle = _puzzle(tmp_path, export_formats=("json", "csv"))
    as_json, as_csv = export_puzzle(puzzle)

    assert json_export.read(as_json) == csv_export.read(as_csv)


# --------------------------------------------------------------------------
# The layout, pinned by example (see ``csv_export``'s module docstring)
# --------------------------------------------------------------------------


def test_the_document_is_built_without_touching_the_filesystem() -> None:
    assert csv_export.document(_payload()).startswith(f"{csv_export.META}\n")


def test_the_layout_is_exactly_the_documented_one() -> None:
    """The worked example from the module docstring, byte for byte.

    Pinned as one literal rather than section by section because the layout
    *is* the contract here: a decoder somebody else writes reads this file,
    not this module's internals, so a reordering or a re-spelling that both
    halves of our own pair agreed on would still break them.
    """
    assert csv_export.document(_payload()) == (
        "#meta\n"
        "version,1\n"
        "seed,42\n"
        "mode,random\n"
        "size,4\n"
        "density,50\n"
        "#grid\n"
        "1,1,0,0\n"
        "0,0,0,0\n"
        "1,1,1,1\n"
        "0,1,1,0\n"
        "#row-clues\n"
        "2\n"
        "0\n"
        "4\n"
        "2\n"
        "#column-clues\n"
        "1,1\n"
        "1,2\n"
        "2\n"
        "1\n"
    )


def test_the_sections_appear_once_each_in_the_documented_order() -> None:
    markers = [row[0] for row in _rows(csv_export.document(_payload())) if row[0].startswith("#")]

    assert tuple(markers) == csv_export.SECTIONS


def test_the_grid_is_zero_one_cells_and_not_a_bitmask() -> None:
    """Guardrail G-4, at the CSV seam.

    An internal per-line bitmask would be one integer per row. What is written
    is ADR-0012's boundary type cell by cell, which is why decoding it back
    cannot depend on bit order or mask width.
    """
    grid = _section(csv_export.document(_payload()), csv_export.GRID)

    assert len(grid) == 4
    assert all(len(row) == 4 for row in grid)
    assert {cell for row in grid for cell in row} <= {"0", "1"}


def test_ragged_clue_rows_are_written_ragged(tmp_path: Path) -> None:
    """CSV's raggedness is used, not padded around.

    Padding short clues to the longest one would put cells in the file that a
    decoder has to guess were not really runs — the exact ambiguity the empty
    cell case below is about.
    """
    payload = _payload(_grid("█·█·█", "·····", "█████", "██·██", "·███·"))

    clues = _section(csv_export.document(payload), csv_export.ROW_CLUES)

    assert clues == [["1", "1", "1"], ["0"], ["5"], ["2", "2"], ["3"]]
    assert len({len(row) for row in clues}) > 1, "the fixture is not ragged"


def test_an_all_empty_line_keeps_its_zero_marker(tmp_path: Path) -> None:
    """AC-013's ``(0,)`` survives the file: it is written as a ``0`` cell, not
    as a blank row, so it comes back as ``(0,)`` and never as ``()``."""
    payload = _payload(_grid("··", "··"))

    text = csv_export.document(payload)

    assert _section(text, csv_export.ROW_CLUES) == [["0"], ["0"]]
    assert _section(text, csv_export.COLUMN_CLUES) == [["0"], ["0"]]
    assert csv_export.decode(text).row_clues == ((0,), (0,))


def test_an_all_filled_grid_round_trips(tmp_path: Path) -> None:
    payload = _payload(_grid("███", "███", "███"))

    assert csv_export.decode(csv_export.document(payload)) == payload


def test_an_unrequested_size_and_density_stay_none(tmp_path: Path) -> None:
    """ADR-0015 records the parameters *as asked for*, and "not asked" is a
    real answer — an empty cell, decoded back to ``None`` rather than ``0``."""
    payload = _payload(size=None, density=None)

    assert _section(csv_export.document(payload), csv_export.META)[3:] == [
        ["size", ""],
        ["density", ""],
    ]
    assert csv_export.decode(csv_export.document(payload)) == payload


def test_a_mode_containing_a_comma_is_quoted_and_survives() -> None:
    """The layout is CSV, not "text split on commas": the writer quotes, the
    reader unquotes, and neither has to be taught about a value's contents."""
    payload = _payload(mode='random,"odd"')

    assert csv_export.decode(csv_export.document(payload)).mode == 'random,"odd"'


def test_render_writes_what_document_built(tmp_path: Path) -> None:
    payload = _payload()
    path = tmp_path / "puzzle.csv"

    csv_export.render(payload, path)

    assert path.read_text(encoding="utf-8") == csv_export.document(payload)
    assert "\r" not in path.read_text(encoding="utf-8"), "plain newlines, like the JSON export"
    assert csv_export.read(path) == payload


# --------------------------------------------------------------------------
# The decoder refuses everything the layout does not allow
# --------------------------------------------------------------------------


def _broken(**replacement: str) -> str:
    """The documented example with one line replaced — one defect at a time."""
    text = csv_export.document(_payload())
    for original, substitute in replacement.items():
        assert original in text, f"{original!r} is not in the example"
        text = text.replace(original, substitute, 1)
    return text


@pytest.mark.parametrize(
    ("text", "message"),
    [
        pytest.param(_broken(**{"#grid\n": ""}), "in that order", id="missing-section"),
        pytest.param(
            csv_export.document(_payload()) + "#grid\n1,1,0,0\n",
            "in that order",
            id="repeated-section",
        ),
        pytest.param(
            "#grid\n1\n#meta\nversion,1\nseed,1\nmode,r\nsize,\ndensity,\n"
            "#row-clues\n1\n#column-clues\n1\n",
            "in that order",
            id="out-of-order-sections",
        ),
        pytest.param(_broken(**{"#meta\n": "#metadata\n"}), "unknown section", id="unknown-marker"),
        pytest.param(_broken(**{"#meta\n": "#meta,extra\n"}), "trailing cells", id="marker-with-cells"),
        pytest.param("version,1\n" + csv_export.document(_payload()), "data before", id="leading-data"),
        pytest.param(_broken(**{"1,1,0,0\n": "\n"}), "blank row", id="blank-row"),
        pytest.param(_broken(**{"version,1\n": "version,2\n"}), "unsupported CSV export version", id="future-version"),
        pytest.param(_broken(**{"seed,42\n": ""}), "missing key", id="missing-meta-key"),
        pytest.param(_broken(**{"seed,42\n": "seed,42,43\n"}), "key,value row", id="three-cell-meta-row"),
        pytest.param(_broken(**{"seed,42\n": "nonce,42\n"}), "unknown key", id="unknown-meta-key"),
        pytest.param(_broken(**{"mode,random\n": "mode,random\nmode,other\n"}), "duplicate key", id="duplicate-meta-key"),
        pytest.param(_broken(**{"seed,42\n": "seed,forty-two\n"}), "expected an integer", id="non-integer-seed"),
        pytest.param(_broken(**{"1,1,0,0\n": "1,1,0\n"}), "the grid is rectangular", id="ragged-grid"),
        pytest.param(_broken(**{"1,1,0,0\n": "1,1,0,true\n"}), "expected '1' or '0'", id="non-binary-cell"),
        pytest.param(_broken(**{"1,1,0,0\n": "1,1,0,2\n"}), "expected '1' or '0'", id="out-of-range-cell"),
        pytest.param(_broken(**{"1,2\n": "1,x\n"}), "expected an integer", id="non-integer-clue"),
    ],
)
def test_the_decoder_rejects_a_malformed_file(text: str, message: str) -> None:
    """Every documented rule, with the file that breaks it.

    Strictness is the point: EC-002 is a fidelity property, and a decoder that
    repaired what it read — skipping an unknown row, padding a short one —
    would round-trip a file it had quietly altered while the property still
    passed.
    """
    with pytest.raises(ValueError, match=message):
        csv_export.decode(text)


def test_the_decoder_rejects_a_file_that_is_not_an_export() -> None:
    """Some other program's CSV: it has no marker row, so it fails at the
    first line rather than being read as a headerless ``#meta`` block."""
    with pytest.raises(ValueError, match="data before the first section marker"):
        csv_export.decode("name,score\nada,10\n")


def test_the_decoder_rejects_a_trailing_blank_line() -> None:
    """Strict here too, and for the layout's own reason.

    The file already ends in a newline; an *extra* blank line is one more row
    in the last section, and a blank row in a clue section is precisely the
    ``()`` that cannot be told from "nothing here". Accepting it as harmless
    at the end of the file would mean the final clue's existence depended on
    whitespace, so it is refused like any other blank row.
    """
    with pytest.raises(ValueError, match="blank row"):
        csv_export.decode(csv_export.document(_payload()) + "\n")


def test_a_file_written_with_windows_line_endings_still_decodes() -> None:
    """The layout is CSV, and CSV's line ending is not part of the contract —
    a file that made a round trip through a Windows tool is still readable."""
    payload = _payload()

    text = csv_export.document(payload).replace("\n", "\r\n")

    assert csv_export.decode(text) == payload


def test_the_decoder_rejects_an_empty_file() -> None:
    with pytest.raises(ValueError, match="in that order"):
        csv_export.decode("")
