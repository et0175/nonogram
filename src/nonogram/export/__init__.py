"""COMP-007 — export renderers: the format-dispatch surface over CAP-005.

A finalized puzzle can leave the process five ways — PNG and SVG (FR-011,
CARD-012), JSON and CSV (FR-012, CARD-013 for the CSV half) and PDF (FR-016,
CARD-014). All five exist today, so this package is a short lookup table plus
the modules behind it: adding a format means registering an
:class:`ExportFormat` in :data:`_FORMATS`, not reshaping the dispatch.

The registry is the *only* list of format names in the codebase
--------------------------------------------------------------
``cli.py`` derives ``--export``'s accepted values from :data:`FORMATS` rather
than repeating them in its ``choices=``. That is deliberate and is the whole
point of keeping the table trivial: CARD-012/013/014 each add one row here and
the CLI adapter picks the new format up — its flag, its help text and its
argparse rejection of an unknown format — without being edited at all. It is
also why the table carries the file extension next to the renderer: the
extension is part of "what this format is", so a new row brings its own, and
nothing outside this file has to learn a per-format special case.

(``sourcing.for_mode`` is the same shape for the three grid sources. It stops
one step short — the CLI still mirrors ``--mode``'s strings by hand — because
the three sourcing modes do not share a parameter list, whereas the five export
formats all render one puzzle to one path.)

Where the readiness gate is *not* (guardrail G-3)
-------------------------------------------------
Nothing here asks whether a puzzle may be exported. INV-002 — a puzzle is
exportable only once its uniqueness check confirmed exactly one solution — is
enforced once, by the orchestrator (COMP-002), before it ever builds an
:class:`ExportPayload`. ADR-0007 puts cross-capability invariants in the
orchestrator precisely so that all five renderers inherit one gate instead of
carrying five copies of it that can drift apart. A renderer that re-checked
readiness would be the second enforcement point that rule exists to prevent.

What crosses the boundary (guardrail G-4)
-----------------------------------------
:class:`ExportPayload` is ADR-0012's *boundary* representation only —
``list[list[bool]]`` for the grid and ``tuple[tuple[int, ...], ...]`` for the
clues — never the solver's internal per-line bitmask. EC-002's round-trip
fidelity (CARD-013) is a property of that choice: what is written is already a
plain, JSON-native structure, so decoding it back cannot depend on bit order or
mask width. The payload also carries the run's seed and generation parameters
(ADR-0015), which is what makes an exported file traceable to the request that
produced it.

Layering (ADR-0007): a capability package, so it imports only its own
submodules and the stdlib — never the adapter, the orchestrator or a sibling
capability.
"""

from __future__ import annotations

import itertools
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from nonogram.export import csv_export, json_export, pdf, png, svg

__all__ = [
    "CSV",
    "FORMATS",
    "JSON",
    "PDF",
    "PNG",
    "SVG",
    "ExportFormat",
    "ExportPayload",
    "Renderer",
    "default_stem",
    "for_format",
    "write",
]

#: The ``--export`` value the JSON renderer is selected by (FR-012).
JSON = "json"

#: The ``--export`` values the two print-ready renderers are selected by
#: (FR-011, CARD-012).
PNG = "png"
SVG = "svg"

#: The ``--export`` value the CSV renderer is selected by (FR-012, CARD-013).
CSV = "csv"

#: The ``--export`` value the two-page PDF renderer is selected by (FR-016,
#: CARD-014). The only format whose filename is not the puzzle's bare name:
#: ADR-0016 spells it ``<name>-<difficulty>.pdf``, which the orchestrator
#: composes and passes in as this format's ``stem``.
PDF = "pdf"


@dataclass(frozen=True, slots=True)
class ExportPayload:
    """One finalized puzzle, as the renderers see it.

    A flat record of ADR-0012 boundary values rather than the ``Puzzle``
    aggregate itself: the aggregate is the orchestrator's (AGG-001) and a
    capability module may not import it (ADR-0007), but more usefully, a
    payload with no ``ready_for_export`` on it cannot tempt a renderer into
    re-checking the gate COMP-002 already applied (guardrail G-3).

    Attributes:
        grid: The full solution grid, row-major, ``True`` for a filled cell.
        row_clues: Row clues, top to bottom — the run-length encoding of
            :attr:`grid` (INV-001).
        column_clues: Column clues, left to right.
        seed: The run's effective seed, always concrete (ADR-0015).
        mode: How the grid was sourced — ``"random"`` today.
        size: The requested edge length, or ``None`` if the request left it to
            the domain default. Recorded as *asked for*, alongside the seed,
            so the request can be replayed exactly (ADR-0015).
        density: The requested fill percentage, same nullability, same reason.
        name: FR-015's puzzle name, verbatim — what the PDF header shows
            (FR-016) and what the filename stem was derived from. ``None`` for
            an aggregate that never got a name.
        difficulty: FR-008's tier **as it is displayed** — ``"Medium"``, not
            ``"medium"``. A plain string and not a ``difficulty.Tier`` for the
            same reason the clues arrive as tuples rather than as the solver's
            bitmasks (ADR-0012): a capability module may not import a sibling
            capability (ADR-0007), so the tier's display spelling is resolved
            once by the orchestrator — through ``Tier.label``, the single
            source of that spelling — and carried across the boundary as a
            value. ``None`` until the puzzle has been scored.
    """

    grid: list[list[bool]]
    row_clues: tuple[tuple[int, ...], ...]
    column_clues: tuple[tuple[int, ...], ...]
    seed: int
    mode: str
    size: int | None = None
    density: int | None = None
    name: str | None = None
    difficulty: str | None = None


#: What a renderer looks like from the dispatcher's side: it writes one payload
#: to one path and returns nothing. Every format shares this signature — unlike
#: the sourcing modes, the five renderers really do take the same two things.
Renderer = Callable[[ExportPayload, Path], None]


@dataclass(frozen=True, slots=True)
class ExportFormat:
    """One row of the registry: a format's name, its extension and its renderer."""

    name: str
    extension: str
    render: Renderer


_FORMATS: dict[str, ExportFormat] = {
    JSON: ExportFormat(JSON, ".json", json_export.render),
    PNG: ExportFormat(PNG, ".png", png.render),
    SVG: ExportFormat(SVG, ".svg", svg.render),
    CSV: ExportFormat(CSV, ".csv", csv_export.render),
    PDF: ExportFormat(PDF, ".pdf", pdf.render),
}

#: The formats this build can export, in registration order. ``cli.py`` builds
#: ``--export``'s ``choices`` from this tuple (see the module docstring).
FORMATS: tuple[str, ...] = tuple(_FORMATS)


def for_format(name: str) -> ExportFormat:
    """Return the registry row for ``name``.

    Args:
        name: An ``--export`` value, e.g. ``"json"``.

    Returns:
        The :class:`ExportFormat` registered under that name.

    Raises:
        ValueError: ``name`` is not registered. Deliberately *not* a
            ``nonogram.errors`` type, for the same reason
            ``sourcing.for_mode`` makes the same choice: an unsupported
            format is rejected by argparse's ``choices`` at the adapter — and
            those choices come from this very table — so an unknown format
            arriving here is a wiring bug inside the pipeline, not invalid
            user input to be mapped onto an exit code.
    """
    try:
        return _FORMATS[name]
    except KeyError:
        raise ValueError(
            f"unknown export format {name!r}; known formats: {', '.join(FORMATS)}"
        ) from None


def default_stem(mode: str, *, moment: datetime | None = None) -> str:
    """The filename stem to use when the puzzle has no name of its own yet.

    FR-015 will give every puzzle a name as an attribute of the aggregate —
    auto-generated as ``"<mode>-<YYYY>-<MM>-<DD>-<HHMM>"`` for random-sourced
    puzzles (AC-042), the library key for library-sourced ones (AC-043), or
    whatever ``--name`` says (AC-044) — and the export path is then derived
    from that name (ADR-0016). That card has not landed, so this reproduces
    FR-015's own convention for the one mode that exists rather than inventing
    a second one: when the aggregate starts carrying a name, this function's
    caller reads it instead and the filenames users already have keep their
    shape.

    Args:
        mode: The generation mode, which is the stem's first component.
        moment: The timestamp to name the file after; defaults to now. An
            argument so the convention itself is testable without freezing
            the clock.
    """
    when = moment if moment is not None else datetime.now()
    return f"{mode}-{when:%Y-%m-%d-%H%M}"


def write(
    payload: ExportPayload,
    name: str,
    *,
    directory: Path,
    stem: str,
) -> Path:
    """Render ``payload`` as ``name`` into ``directory`` and return the path.

    The shared "write to ``--out``" plumbing behind every format: resolve a
    non-colliding path, make sure the directory exists, hand the renderer a
    path and report where the file landed. A renderer therefore only ever
    serializes — it does not decide where its output goes, which is what keeps
    the four later format cards down to one registry row each.

    ``directory`` is a directory and not a file path because ``--export`` is
    repeatable: one run can ask for JSON and PDF at once, and the two files
    have to differ by extension in one place the user chose.

    Collisions are auto-suffixed (``-1``, ``-2``, ...) rather than overwritten,
    per ADR-0017 — the export path is computed, never dictated, so two runs of
    the same mode in the same minute would otherwise silently destroy the first
    run's artifact.

    Args:
        payload: The finalized puzzle to serialize. That it *is* finalized was
            settled by COMP-002's INV-002 gate before this call (G-3).
        name: A registered format name.
        directory: Where the file goes; created if it does not exist.
        stem: The filename without its extension — see :func:`default_stem`.
            Per call, not per run: four of the five formats are written under
            the puzzle's name, while ADR-0016 gives the PDF its own
            ``<name>-<difficulty>`` stem, and which stem a format takes is the
            composing layer's decision rather than this dispatcher's.

    Returns:
        The path actually written, suffix included if there was a collision.

    Raises:
        ValueError: ``name`` is not a registered format.
        OSError: the directory could not be created or the file not written.
    """
    export_format = for_format(name)
    directory.mkdir(parents=True, exist_ok=True)
    path = _free_path(directory, stem, export_format.extension)
    export_format.render(payload, path)
    return path


def _free_path(directory: Path, stem: str, extension: str) -> Path:
    """ADR-0017's collision policy: the first ``stem[-N]`` nobody is using."""
    candidate = directory / f"{stem}{extension}"
    if not candidate.exists():
        return candidate
    for suffix in itertools.count(1):
        candidate = directory / f"{stem}-{suffix}{extension}"
        if not candidate.exists():
            return candidate
    raise AssertionError("unreachable: itertools.count is infinite")  # pragma: no cover
