"""What CARD-113's tripwire pins, and the one way each thing is measured.

Shared by the two golden test modules and by :mod:`.regenerate`, so that the
fixture is written and read through exactly the same serialization — a golden
written one way and compared another is a tripwire that can never fire, or one
that always does.

Two kinds of golden live in this directory:

``layout.json``
    ``compute_layout(row_clues, column_clues)`` for a fixed corpus of clue
    sets, every field of :class:`~nonogram.export.layout.Layout` as it existed
    at the base commit, every :class:`GridLine` and every :class:`ClueEntry`
    included (ADR-0036/R1).

``cli_exports.json``
    SHA-256 digests of the PNG, SVG and PDF files ``nonogram generate`` writes
    for a fixed set of requests (AC-180, EC-020, CON-019).

The PDF is not byte-deterministic, and exactly how it is not
------------------------------------------------------------
``pdf.write_pdf`` saves through Pillow's PDF writer, which stamps the document
info dictionary with ``/CreationDate (D:YYYYMMDDHHMMSSZ)`` and
``/ModDate (D:YYYYMMDDHHMMSSZ)`` taken from ``time.gmtime()`` at save time.
Pillow honours no ``SOURCE_DATE_EPOCH`` (checked in Pillow 12.3.0's
``PdfImagePlugin._save``), and nothing in ``src/`` passes ``creationDate``/
``modDate`` to override it — so two otherwise identical runs a second apart
differ in exactly those 28 digits. Everything else is deterministic, measured:
two runs a minute apart differed only there. The ``/Title`` entry is the
file's stem, which is deterministic because every pinned request names its
puzzle (see below).

:func:`normalized_pdf` therefore zeroes those two timestamps and nothing else,
and the digest is taken over the result. The replacement is length-preserving,
so the xref table's byte offsets are still pinned. It also insists on finding
each field exactly once: a PDF whose info dictionary changed shape is a change
to the output, and must fail as one rather than be normalized around.

Why every pinned request carries ``--name``
-------------------------------------------
Without it, the puzzle's name is ``random-<YYYY-MM-DD-HHMM>`` read off the wall
clock (FR-015, AC-042), and that name is both the filename and the text in the
PDF's header band. A request without a name is therefore not a *fixed*
request in AC-180's sense; naming it is what makes it one.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import re
from pathlib import Path
from typing import Any

from nonogram import cli
from nonogram.export.layout import Layout

__all__ = [
    "AC180_CASE_ID",
    "AC180_REQUEST",
    "CLI_GOLDEN",
    "CLUE_ENTRY_FIELDS",
    "EXPORT_FORMATS",
    "FIXTURE_DIR",
    "GRID_LINE_FIELDS",
    "LAYOUT_GOLDEN",
    "LAYOUT_SCALAR_FIELDS",
    "LAYOUT_SEQUENCE_FIELDS",
    "Request",
    "cli_argv",
    "digests_of",
    "layout_differences",
    "load",
    "normalized_pdf",
    "run_cli",
    "serialize_layout",
]

FIXTURE_DIR = Path(__file__).resolve().parent
LAYOUT_GOLDEN = FIXTURE_DIR / "layout.json"
CLI_GOLDEN = FIXTURE_DIR / "cli_exports.json"

#: The three print formats CON-019 names, in the order they are requested.
EXPORT_FORMATS: tuple[str, ...] = ("png", "svg", "pdf")

#: One ``nonogram generate`` request, as the four values that vary between
#: pinned requests: ``(size token, density, seed, name)``. The size token is
#: passed through exactly as typed (``"30x30"`` or a bare ``"20"``).
type Request = tuple[str, int, int, str]

#: AC-180's fixed request: a seeded 30x30. Density 60 because the AC names
#: none and the CLI requires one; it is inside the regime where generation is
#: a pure function of the seed (see the property module's docstring on why
#: lower densities are not).
AC180_CASE_ID = "ac180-30x30-seed42"
AC180_REQUEST: Request = ("30x30", 60, 42, "ac180-golden")

#: Every :class:`Layout` field at the base commit, split by shape. Listed
#: explicitly rather than read off ``dataclasses.fields`` so that a field a
#: later card *adds* is not compared against a golden that predates it (the
#: CLI byte digests catch any effect it has on output), while a field it
#: renames or removes fails loudly. ``regenerate`` asserts this list was
#: complete when the golden was captured.
LAYOUT_SCALAR_FIELDS: tuple[str, ...] = (
    "rows",
    "columns",
    "orientation",
    "cell",
    "margin",
    "row_gutter_cells",
    "column_gutter_cells",
    "width",
    "height",
    "grid_left",
    "grid_top",
    "grid_right",
    "grid_bottom",
    "thin_rule",
    "thick_rule",
    "clue_font_size",
    "dpi",
)
LAYOUT_SEQUENCE_FIELDS: tuple[str, ...] = (
    "vertical_lines",
    "horizontal_lines",
    "row_clues",
    "column_clues",
)
GRID_LINE_FIELDS: tuple[str, ...] = ("index", "position", "start", "end", "width", "major")
CLUE_ENTRY_FIELDS: tuple[str, ...] = ("value", "line", "depth", "center_x", "center_y")

_SEQUENCE_ITEM_FIELDS: dict[str, tuple[str, ...]] = {
    "vertical_lines": GRID_LINE_FIELDS,
    "horizontal_lines": GRID_LINE_FIELDS,
    "row_clues": CLUE_ENTRY_FIELDS,
    "column_clues": CLUE_ENTRY_FIELDS,
}

#: Pillow's two info-dictionary timestamps — the only non-deterministic bytes
#: in the PDF (see the module docstring).
_PDF_TIMESTAMP = re.compile(rb"/(CreationDate|ModDate) \(D:(\d{14})Z\)")


def load(path: Path) -> dict[str, Any]:
    """A golden file, parsed."""
    return json.loads(path.read_text(encoding="utf-8"))


def serialize_layout(layout: Layout) -> dict[str, Any]:
    """``layout`` as plain JSON values, field by field.

    Scalars keep their name; each sequence becomes a list of rows, one row per
    :class:`GridLine`/:class:`ClueEntry` in :data:`GRID_LINE_FIELDS`/
    :data:`CLUE_ENTRY_FIELDS` order — positional rather than keyed only to keep
    the fixture a readable size.
    """
    serialized: dict[str, Any] = {name: getattr(layout, name) for name in LAYOUT_SCALAR_FIELDS}
    for name, item_fields in _SEQUENCE_ITEM_FIELDS.items():
        serialized[name] = [
            [getattr(item, field) for field in item_fields] for item in getattr(layout, name)
        ]
    return serialized


def layout_differences(expected: dict[str, Any], actual: dict[str, Any]) -> list[str]:
    """Every field on which ``actual`` departs from ``expected``, spelled out.

    For a sequence, the first differing element is named with both values, so
    a red test says *which* grid line or clue moved rather than only that one
    did.
    """
    differences: list[str] = []
    for name in LAYOUT_SCALAR_FIELDS:
        if expected[name] != actual[name]:
            differences.append(f"{name}: golden {expected[name]!r}, now {actual[name]!r}")
    for name, item_fields in _SEQUENCE_ITEM_FIELDS.items():
        golden_items, live_items = expected[name], actual[name]
        if golden_items == live_items:
            continue
        if len(golden_items) != len(live_items):
            differences.append(
                f"{name}: golden has {len(golden_items)} entries, now {len(live_items)}"
            )
        for index, (golden_item, live_item) in enumerate(
            zip(golden_items, live_items, strict=False)
        ):
            if golden_item != live_item:
                differences.append(
                    f"{name}[{index}] ({', '.join(item_fields)}): "
                    f"golden {golden_item}, now {live_item}"
                )
                break
    return differences


def normalized_pdf(data: bytes) -> bytes:
    """``data`` with Pillow's two save-time timestamps zeroed, nothing else.

    Raises:
        AssertionError: the info dictionary does not carry exactly one
            ``/CreationDate`` and one ``/ModDate`` in Pillow's format — the
            PDF's structure changed, which the tripwire must report rather
            than normalize around.
    """
    found = sorted(match.group(1) for match in _PDF_TIMESTAMP.finditer(data))
    if found != [b"CreationDate", b"ModDate"]:
        raise AssertionError(
            "the PDF's info dictionary no longer carries exactly one "
            "/CreationDate and one /ModDate in Pillow's D:YYYYMMDDHHMMSSZ form "
            f"(found {found!r}); its structure changed since the golden was taken"
        )
    return _PDF_TIMESTAMP.sub(lambda match: b"/%s (D:%sZ)" % (match.group(1), b"0" * 14), data)


def digests_of(directory: Path) -> dict[str, dict[str, str]]:
    """``{extension: {"file": name, "sha256": digest}}`` for every file in ``directory``.

    The PDF is digested after :func:`normalized_pdf`; the PNG and SVG as
    written.
    """
    digests: dict[str, dict[str, str]] = {}
    for path in sorted(directory.iterdir()):
        extension = path.suffix.lstrip(".")
        if extension in digests:
            raise AssertionError(f"two .{extension} files written into {directory}")
        data = path.read_bytes()
        if extension == "pdf":
            data = normalized_pdf(data)
        digests[extension] = {"file": path.name, "sha256": hashlib.sha256(data).hexdigest()}
    return digests


def cli_argv(request: Request) -> list[str]:
    """The ``nonogram generate`` argv for ``request``, all three formats, no ``--out``."""
    size, density, seed, name = request
    argv = ["generate", "--mode", "random", "--size", size, "--density", str(density)]
    argv += ["--seed", str(seed), "--name", name]
    for export_format in EXPORT_FORMATS:
        argv += ["--export", export_format]
    return argv


def run_cli(request: Request, out: Path) -> dict[str, dict[str, str]]:
    """Run ``nonogram generate`` in-process for ``request`` into ``out``; digest it.

    In-process through :func:`nonogram.cli.main` — the console script's own
    entry point — so the suite exercises the ``nonogram`` package pytest
    imported (the worktree's ``src/``, via ``pythonpath``) rather than whatever
    a ``nonogram`` executable on ``PATH`` happens to be installed from.

    ``out`` must be empty or absent: ADR-0017 suffixes a colliding filename,
    and a suffixed name is not the pinned one.
    """
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = cli.main([*cli_argv(request), "--out", str(out)])
    if code != 0:
        raise AssertionError(
            f"nonogram {' '.join(cli_argv(request))} exited {code}: {stderr.getvalue()}"
        )
    return digests_of(out)
