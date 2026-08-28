"""COMP-007 — the JSON renderer and its decoder (FR-012, the JSON half).

FR-012 asks for an export "sufficient to exactly reconstruct the puzzle", and
ADR-0015 widens that to the *run*: the seed and the generation parameters
travel with the grid and the clues, so a file found on disk months later still
names the request that produced it. The document below is therefore three
things at once — the puzzle (grid + clues), its provenance (seed + request
parameters) and a schema version so a future reader can tell which it is
holding.

The grid is written as ADR-0012's boundary type, a plain ``list[list[bool]]``
of JSON ``true``/``false``, and the clues as arrays of integers — never the
solver's internal per-line bitmask (guardrail G-4). EC-002's round-trip
property (CARD-013) rests on exactly that: `json.loads` on this document hands
back the same nested lists of the same Python scalars, with no bit order,
mask width or sign convention to get wrong at the seam.

:func:`document` is separated from :func:`render` so the serialized *shape* can
be asserted without touching a filesystem, and so CARD-013's round-trip test
has one obvious thing to invert. :func:`parse` is that inverse, with
:func:`decode` and :func:`read` stacking the same two steps ``render`` stacks
in the other direction:

    payload -> document() -> json.dumps -> render()  writes a file
    payload <- parse()    <- json.loads <- decode()  <- read()  reads one back

The decoder is deliberately strict (CARD-013). EC-002 is a *fidelity*
property, and a decoder that coerced ``1`` into ``True``, tolerated a missing
field or padded a short clue would still "round-trip" a document it had
quietly altered — the property would pass while the guarantee it stands for
was gone. So every departure from the shape :func:`document` writes raises
``ValueError`` instead of being repaired.

Nothing here checks whether the puzzle may be exported: INV-002 is the
orchestrator's single enforcement point (ADR-0007, guardrail G-3), applied
before the payload is even built.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - import cycle is type-time only
    from nonogram.export import ExportPayload

__all__ = ["SCHEMA_VERSION", "decode", "document", "parse", "read", "render"]

#: Version of the document shape below. Bumped only by a change that an
#: existing reader could not survive; CARD-013's CSV export and round-trip
#: decode are written against this number.
SCHEMA_VERSION = 1


def document(payload: ExportPayload) -> dict[str, Any]:
    """The JSON document for ``payload``, as plain Python objects.

    Clue tuples become lists because JSON has one sequence type; the values
    inside them are untouched integers, and the grid's cells untouched bools.
    """
    return {
        "version": SCHEMA_VERSION,
        "seed": payload.seed,
        "request": {
            "mode": payload.mode,
            "size": payload.size,
            "density": payload.density,
        },
        "grid": [list(row) for row in payload.grid],
        "clues": {
            "rows": [list(clue) for clue in payload.row_clues],
            "columns": [list(clue) for clue in payload.column_clues],
        },
    }


def render(payload: ExportPayload, path: Path) -> None:
    """Write ``payload`` to ``path`` as JSON (the :data:`~nonogram.export.Renderer`
    signature).

    Indented and newline-terminated: an export is a durable artifact a person
    may open or diff, so the structure is worth the bytes — at the maximum
    supported 50x50 (AC-038) the file is still tens of kilobytes. UTF-8 with
    ``ensure_ascii=False``, so a future ``name`` field (FR-015) keeps its
    characters rather than being escaped.
    """
    text = json.dumps(document(payload), indent=2, ensure_ascii=False)
    path.write_text(f"{text}\n", encoding="utf-8")


def read(path: Path) -> ExportPayload:
    """Decode the JSON file at ``path`` — the inverse of :func:`render`.

    Raises:
        ValueError: the file is not a JSON export of :data:`SCHEMA_VERSION`,
            or its shape does not match what :func:`document` writes.
        OSError: the file could not be read.
    """
    return decode(path.read_text(encoding="utf-8"))


def decode(text: str) -> ExportPayload:
    """Decode JSON ``text`` into the payload that produced it (EC-002).

    Raises:
        ValueError: ``text`` is not valid JSON, or not a well-formed export.
            ``json.JSONDecodeError`` is already a ``ValueError``, so a caller
            has one exception type to handle for "this file is not one of
            ours" whichever way it fails.
    """
    return parse(json.loads(text))


def parse(source: Any) -> ExportPayload:
    """Rebuild the payload from a decoded JSON document — :func:`document`'s inverse.

    Args:
        source: The object ``json.loads`` produced, i.e. the dict
            :func:`document` returned before serialization.

    Returns:
        The :class:`~nonogram.export.ExportPayload` the document was written
        from: the grid back as ADR-0012's ``list[list[bool]]`` and the clues
        back as ``tuple[tuple[int, ...], ...]`` — the same shapes
        :func:`document` took them in, so an exported puzzle compares equal to
        the original with no normalisation on either side.

    Raises:
        ValueError: the document is not of :data:`SCHEMA_VERSION`, is missing
            a field, has a field of the wrong shape or type, or the clue
            counts do not match the grid's dimensions (e.g. a dropped
            ``clues.columns`` entry).
    """
    # Imported here, not at module scope: ``nonogram.export.__init__`` imports
    # this module to build its registry, so the boundary type is only bound
    # once that import has finished — which it always has by the time anybody
    # can call this function.
    from nonogram.export import ExportPayload

    document_ = _mapping(source, "document")
    version = _int(_field(document_, "version", "document"), "version")
    if version != SCHEMA_VERSION:
        raise ValueError(
            f"unsupported JSON export version {version}; this build reads "
            f"version {SCHEMA_VERSION}"
        )

    request = _mapping(_field(document_, "request", "document"), "request")
    clues = _mapping(_field(document_, "clues", "document"), "clues")
    mode = _field(request, "mode", "request")
    if not isinstance(mode, str):
        raise ValueError(f"request.mode: expected a string, found {mode!r}")

    grid = _grid(_field(document_, "grid", "document"))
    row_clues = _clues(_field(clues, "rows", "clues"), "clues.rows")
    column_clues = _clues(_field(clues, "columns", "clues"), "clues.columns")
    _check_clue_counts(grid, row_clues, column_clues)

    return ExportPayload(
        grid=grid,
        row_clues=row_clues,
        column_clues=column_clues,
        seed=_int(_field(document_, "seed", "document"), "seed"),
        mode=mode,
        size=_optional_int(_field(request, "size", "request"), "request.size"),
        density=_optional_int(_field(request, "density", "request"), "request.density"),
    )


def _field(mapping: Mapping[str, Any], key: str, where: str) -> Any:
    if key not in mapping:
        raise ValueError(f"{where}: missing field {key!r}")
    return mapping[key]


def _mapping(value: Any, where: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{where}: expected an object, found {type(value).__name__}")
    return value


def _rows(value: Any, where: str) -> Sequence[Any]:
    """A JSON array, and not a string — which is also a ``Sequence``."""
    if not isinstance(value, list):
        raise ValueError(f"{where}: expected an array, found {type(value).__name__}")
    return value


def _int(value: Any, where: str) -> int:
    """An integer, and never a ``bool``.

    ``True == 1`` in Python, so without the ``bool`` rejection a document with
    ``"seed": true`` would decode to seed ``1`` — a file silently becoming a
    different puzzle's provenance is exactly what EC-002's fidelity is about.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{where}: expected an integer, found {value!r}")
    return value


def _optional_int(value: Any, where: str) -> int | None:
    """``null`` stays ``None`` — "not asked for" (ADR-0015), not zero."""
    return None if value is None else _int(value, where)


def _grid(value: Any) -> list[list[bool]]:
    """The grid, back to ADR-0012's boundary type.

    Cells must be JSON ``true``/``false``: accepting ``1``/``0`` would let two
    different documents decode to the same grid, and would quietly re-admit
    the numeric encodings guardrail G-4 keeps out of the file in the first
    place.
    """
    grid: list[list[bool]] = []
    width: int | None = None
    for index, row in enumerate(_rows(value, "grid")):
        cells = _rows(row, f"grid[{index}]")
        if width is None:
            width = len(cells)
        elif len(cells) != width:
            raise ValueError(
                f"grid[{index}]: has {len(cells)} cells, expected {width} — "
                f"the grid is rectangular"
            )
        for position, cell in enumerate(cells):
            if not isinstance(cell, bool):
                raise ValueError(
                    f"grid[{index}][{position}]: expected true or false, found {cell!r}"
                )
        grid.append(list(cells))
    return grid


def _clues(value: Any, where: str) -> tuple[tuple[int, ...], ...]:
    """One clue set, back to the immutable boundary type."""
    return tuple(
        tuple(
            _int(run, f"{where}[{index}][{position}]")
            for position, run in enumerate(_rows(clue, f"{where}[{index}]"))
        )
        for index, clue in enumerate(_rows(value, where))
    )


def _check_clue_counts(
    grid: list[list[bool]],
    row_clues: tuple[tuple[int, ...], ...],
    column_clues: tuple[tuple[int, ...], ...],
) -> None:
    """The two clue sets must have one entry per grid line, no more, no fewer.

    A truncated file — a dropped ``clues.columns`` entry, a partial write, a
    hand edit — can still be a well-formed JSON document with well-formed
    ``clues.rows``/``clues.columns`` arrays while holding too few (or too
    many) entries for the grid's actual shape: each array is validated on its
    own, so nothing upstream of this notices that ``clues.columns`` has one
    entry for a two-column grid. This is the same structural check as the
    grid's own rectangularity check, applied across fields instead of within
    one.
    """
    if len(row_clues) != len(grid):
        raise ValueError(
            f"clues.rows: {len(row_clues)} row clue(s) for a grid of "
            f"{len(grid)} row(s)"
        )
    expected_columns = len(grid[0]) if grid else 0
    if len(column_clues) != expected_columns:
        raise ValueError(
            f"clues.columns: {len(column_clues)} column clue(s) for a grid "
            f"of {expected_columns} column(s)"
        )
