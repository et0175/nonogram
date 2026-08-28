"""COMP-007 — the JSON renderer (FR-012, the JSON half).

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
has one obvious thing to invert.

Nothing here checks whether the puzzle may be exported: INV-002 is the
orchestrator's single enforcement point (ADR-0007, guardrail G-3), applied
before the payload is even built.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - import cycle is type-time only
    from nonogram.export import ExportPayload

__all__ = ["SCHEMA_VERSION", "document", "render"]

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
