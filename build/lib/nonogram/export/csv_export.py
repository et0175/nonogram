"""COMP-007 — the CSV renderer and its decoder (FR-012, the CSV half).

CARD-007 delivered the JSON half of FR-012; this module adds the CSV one and,
with :mod:`nonogram.export.json_export`'s decoder, closes EC-002: what is
written can be read back into exactly the payload that produced it.

CSV is flat, so the file format is where all the design is
====================================================================
JSON carries its own structure — a decoder finds ``grid`` and ``clues`` by
name. A CSV file is an undifferentiated sequence of rows, and this export has
to hold four things of three different shapes: scalar metadata, a rectangular
0/1 matrix, and two *ragged* lists of integer tuples. Getting them into one
file unambiguously means saying, in the file itself, where each block starts.

The layout, exactly
-------------------
Four sections, each opened by a one-cell marker row, in this fixed order::

    #meta
    version,1
    seed,42
    mode,random
    size,4
    density,50
    #grid
    1,1,0,0
    0,0,0,0
    1,1,1,1
    0,1,1,0
    #row-clues
    2
    0
    4
    2
    #column-clues
    1,1
    1,2
    2
    1

* **Marker rows** are a single cell whose text is ``#meta``, ``#grid``,
  ``#row-clues`` or ``#column-clues`` (:data:`SECTIONS`). The ``#`` prefix is
  what makes them unmistakable: every data row in every section is a row of
  bare integers, so no data row can ever be read as a marker and no marker as
  data. All four must appear, exactly once, in the order above — a decoder
  that accepted them in any order would also accept a file whose two clue
  blocks had been swapped, which is a silent transposition, not an error.
* **``#meta``** is one ``key,value`` row per field, all five keys required and
  no others accepted. ``size`` and ``density`` are optional in the payload
  (ADR-0015 records them as *asked for*, and "not asked" is a real answer), so
  a ``None`` is written as an empty value — ``size,`` — and read back as
  ``None`` rather than as ``0`` or ``""``. ``version`` is :data:`SCHEMA_VERSION`.
* **``#grid``** is one row per grid line, top to bottom, one cell per column,
  ``1`` filled and ``0`` empty — ADR-0012's boundary type written out cell by
  cell, never the solver's per-line bitmask (guardrail G-4). A bitmask would
  be one integer per row here and would make the file's fidelity depend on bit
  order and mask width; ``1,0,1`` cannot be misread in either direction.
* **``#row-clues`` / ``#column-clues``** are one nonogram line-clue per row,
  the runs comma-separated: rows top to bottom, columns left to right.
  Raggedness is free in CSV — a short row is short, and nothing pads it — so
  ``(2, 3)`` and ``(4,)`` sit in the same block without either growing filler
  cells that a decoder would have to guess were not really zeros.

Why an empty row is never written, and always an error to read
--------------------------------------------------------------
The one shape this layout could not represent is an *empty* clue tuple: it
would serialize to a blank line, which is indistinguishable from a stray blank
line in the file. It never arises — a line with no filled cells encodes to the
``(0,)`` marker, not to ``()`` (AC-013, ``clues.EMPTY_LINE_CLUE``), so every
clue tuple has at least one run and every clue row at least one cell. This
module does not depend on knowing that: it serializes whatever tuples it is
handed, and :func:`decode` rejects a blank row outright. So the one input that
could not survive the round trip fails loudly at the decode instead of quietly
coming back as ``()`` — EC-002 is a fidelity property, and a format that
guesses is a format that can lose. That rule has no exception for the end of
the file either: the text already ends in a newline, so an extra blank line is
one more row of ``#column-clues``, and letting whitespace decide whether a
final clue exists is the same ambiguity wearing a friendlier face.

Guardrails: stdlib :mod:`csv` only, no new dependency (G-5, ADR-0006), and
nothing here asks whether the puzzle may be exported — INV-002 is COMP-002's
single gate (ADR-0007, G-3).
"""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - import cycle is type-time only
    from nonogram.export import ExportPayload

__all__ = [
    "COLUMN_CLUES",
    "GRID",
    "META",
    "ROW_CLUES",
    "SCHEMA_VERSION",
    "SECTIONS",
    "decode",
    "document",
    "read",
    "render",
]

#: Version of the layout documented above. Bumped only by a change an existing
#: reader could not survive. Deliberately its own number rather than a shared
#: one with ``json_export``: the two formats are decoded by two parsers and
#: nothing says a change to one is a change to the other.
SCHEMA_VERSION = 1

#: The four section markers, in the order they must appear in the file.
META = "#meta"
GRID = "#grid"
ROW_CLUES = "#row-clues"
COLUMN_CLUES = "#column-clues"
SECTIONS: tuple[str, ...] = (META, GRID, ROW_CLUES, COLUMN_CLUES)

#: The ``#meta`` keys, all required and no others accepted.
_META_KEYS: tuple[str, ...] = ("version", "seed", "mode", "size", "density")

#: A grid cell, both ways.
_FILLED, _EMPTY = "1", "0"

#: ``\n`` rather than :mod:`csv`'s default ``\r\n``: an export is a durable
#: text artifact somebody may diff, and the JSON renderer already writes plain
#: newlines. The decoder accepts either, since :mod:`csv` handles both.
_LINE_TERMINATOR = "\n"


def document(payload: ExportPayload) -> str:
    """The CSV text for ``payload``, as one string.

    Separated from :func:`render` for the same reason ``json_export.document``
    is: the serialized shape is assertable without a filesystem, and EC-002's
    round trip has one obvious thing to invert.
    """
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator=_LINE_TERMINATOR)

    writer.writerow([META])
    writer.writerow(["version", SCHEMA_VERSION])
    writer.writerow(["seed", payload.seed])
    writer.writerow(["mode", payload.mode])
    writer.writerow(["size", "" if payload.size is None else payload.size])
    writer.writerow(["density", "" if payload.density is None else payload.density])

    writer.writerow([GRID])
    for row in payload.grid:
        writer.writerow([_FILLED if cell else _EMPTY for cell in row])

    writer.writerow([ROW_CLUES])
    writer.writerows(list(clue) for clue in payload.row_clues)

    writer.writerow([COLUMN_CLUES])
    writer.writerows(list(clue) for clue in payload.column_clues)

    return buffer.getvalue()


def render(payload: ExportPayload, path: Path) -> None:
    """Write ``payload`` to ``path`` as CSV (the :data:`~nonogram.export.Renderer`
    signature).

    UTF-8, matching the JSON renderer, so a future ``name`` field (FR-015)
    keeps its characters. ``newline=""`` is :mod:`csv`'s documented
    requirement: it stops the platform's newline translation from turning the
    writer's own line terminator into something else on the way to disk.
    """
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(document(payload))


def read(path: Path) -> ExportPayload:
    """Decode the CSV file at ``path`` — the inverse of :func:`render`.

    Raises:
        ValueError: the file does not follow the layout in the module
            docstring.
        OSError: the file could not be read.
    """
    return decode(path.read_text(encoding="utf-8"))


def decode(text: str) -> ExportPayload:
    """Decode CSV ``text`` into the payload that produced it (EC-002).

    The inverse of :func:`document`, and strict about it: every departure from
    the documented layout raises rather than being repaired. A round-trip
    property is only worth what its decoder refuses — a parser that skipped an
    unrecognised row or padded a short one would still "round-trip" a file it
    had silently altered.

    Args:
        text: The contents of a CSV export.

    Returns:
        The :class:`~nonogram.export.ExportPayload` the file was written from:
        the grid as ADR-0012's ``list[list[bool]]`` and both clue sets as
        ``tuple[tuple[int, ...], ...]``, the same shapes :func:`document` took
        them in.

    Raises:
        ValueError: the text is not a CSV export of :data:`SCHEMA_VERSION`, a
            section is missing, out of order or repeated, a row inside one
            does not have that section's shape, or the clue counts do not
            match the grid's dimensions (e.g. a truncated file that dropped a
            trailing clue line).
    """
    # Imported here, not at module scope: ``nonogram.export.__init__`` imports
    # this module to build its registry, so the boundary type is only bound
    # once that import has finished — which it always has by the time anybody
    # can call this function.
    from nonogram.export import ExportPayload

    sections = _split_sections(text)
    meta = _decode_meta(sections[META])
    grid = _decode_grid(sections[GRID])
    row_clues = _decode_clues(sections[ROW_CLUES], ROW_CLUES)
    column_clues = _decode_clues(sections[COLUMN_CLUES], COLUMN_CLUES)
    _check_clue_counts(grid, row_clues, column_clues)
    return ExportPayload(
        grid=grid,
        row_clues=row_clues,
        column_clues=column_clues,
        seed=meta["seed"],
        mode=meta["mode"],
        size=meta["size"],
        density=meta["density"],
    )


def _split_sections(text: str) -> dict[str, list[list[str]]]:
    """Cut ``text`` into its four blocks, checking every structural rule.

    Order, completeness and non-repetition are all one check here: the markers
    seen, in the order seen, must be exactly :data:`SECTIONS`.
    """
    seen: list[str] = []
    blocks: dict[str, list[list[str]]] = {}
    for number, row in enumerate(csv.reader(io.StringIO(text, newline="")), start=1):
        if not row:
            raise ValueError(f"line {number}: blank row (see the layout docstring)")
        if row[0] in SECTIONS:
            if len(row) != 1:
                raise ValueError(
                    f"line {number}: section marker {row[0]!r} has trailing cells {row[1:]}"
                )
            seen.append(row[0])
            blocks[row[0]] = []
            continue
        if row[0].startswith("#"):
            raise ValueError(f"line {number}: unknown section marker {row[0]!r}")
        if not seen:
            raise ValueError(f"line {number}: data before the first section marker")
        blocks[seen[-1]].append(row)

    if tuple(seen) != SECTIONS:
        raise ValueError(
            f"expected the sections {list(SECTIONS)} exactly once and in that "
            f"order, found {seen}"
        )
    return blocks


def _decode_meta(rows: list[list[str]]) -> dict[str, object]:
    """The ``#meta`` block: five ``key,value`` rows, no more and no fewer."""
    fields: dict[str, str] = {}
    for row in rows:
        if len(row) != 2:
            raise ValueError(f"{META}: expected a key,value row, found {row}")
        key, value = row
        if key not in _META_KEYS:
            raise ValueError(f"{META}: unknown key {key!r}")
        if key in fields:
            raise ValueError(f"{META}: duplicate key {key!r}")
        fields[key] = value

    missing = [key for key in _META_KEYS if key not in fields]
    if missing:
        raise ValueError(f"{META}: missing key(s) {missing}")

    version = _int(fields["version"], f"{META}: version")
    if version != SCHEMA_VERSION:
        raise ValueError(
            f"unsupported CSV export version {version}; this build reads "
            f"version {SCHEMA_VERSION}"
        )
    return {
        "seed": _int(fields["seed"], f"{META}: seed"),
        "mode": fields["mode"],
        "size": _optional_int(fields["size"], f"{META}: size"),
        "density": _optional_int(fields["density"], f"{META}: density"),
    }


def _decode_grid(rows: list[list[str]]) -> list[list[bool]]:
    """The ``#grid`` block, back into ADR-0012's boundary type.

    Cells are ``1``/``0`` and nothing else: accepting ``true``, ``""`` or any
    non-empty string as filled would make two different files decode to the
    same grid, so a file could no longer be said to *be* its puzzle.
    """
    grid: list[list[bool]] = []
    width: int | None = None
    for number, row in enumerate(rows, start=1):
        if width is None:
            width = len(row)
        elif len(row) != width:
            raise ValueError(
                f"{GRID}: row {number} has {len(row)} cells, expected {width} "
                f"— the grid is rectangular"
            )
        line: list[bool] = []
        for cell in row:
            if cell not in (_FILLED, _EMPTY):
                raise ValueError(
                    f"{GRID}: row {number} has cell {cell!r}, expected "
                    f"{_FILLED!r} or {_EMPTY!r}"
                )
            line.append(cell == _FILLED)
        grid.append(line)
    return grid


def _decode_clues(rows: list[list[str]], section: str) -> tuple[tuple[int, ...], ...]:
    """One clue block: one line-clue per row, ragged, every cell an integer."""
    return tuple(
        tuple(_int(run, f"{section}: line {number}") for run in row)
        for number, row in enumerate(rows, start=1)
    )


def _check_clue_counts(
    grid: list[list[bool]],
    row_clues: tuple[tuple[int, ...], ...],
    column_clues: tuple[tuple[int, ...], ...],
) -> None:
    """The two clue blocks must have one entry per grid line, no more, no fewer.

    A truncated file — a dropped last line, a partial write, a hand edit — can
    still parse as a well-formed ``#row-clues``/``#column-clues`` block while
    holding too few (or too many) entries for the grid's actual shape. Nothing
    upstream of this catches that: each block is decoded on its own, so a
    ``#column-clues`` section with one line for a two-column grid silently
    becomes a same-shaped-looking payload with the wrong number of columns'
    worth of clues. This is the same structural check as the grid's own
    rectangularity check, applied across sections instead of within one.
    """
    if len(row_clues) != len(grid):
        raise ValueError(
            f"{ROW_CLUES}: {len(row_clues)} row clue(s) for a grid of "
            f"{len(grid)} row(s)"
        )
    expected_columns = len(grid[0]) if grid else 0
    if len(column_clues) != expected_columns:
        raise ValueError(
            f"{COLUMN_CLUES}: {len(column_clues)} column clue(s) for a grid "
            f"of {expected_columns} column(s)"
        )


def _int(value: str, where: str) -> int:
    try:
        return int(value)
    except ValueError:
        raise ValueError(f"{where}: expected an integer, found {value!r}") from None


def _optional_int(value: str, where: str) -> int | None:
    """An empty cell is ``None`` — "not asked for" (ADR-0015), not zero."""
    return None if value == "" else _int(value, where)
