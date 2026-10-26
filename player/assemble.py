#!/usr/bin/env python3
"""COMP-011's site assembler — the public player's deployable tree (CARD-283).

The public player is static files (ADR-0041/R3), so "building" it is copying:
this script writes the directory a static host serves. It is deliberately NOT
part of the Python package — it lives in ``player/`` beside the files it
copies, imports nothing from ``nonogram`` by name (it loads
``src/nonogram/limits.py`` *by path*, see :func:`_limits`, because that module
imports nothing and is the one authority on the supported grid extent), and is
never imported by anything under ``src/``. Running it needs the standard
library and nothing else (ADR-0006/R1 untouched).

    python player/assemble.py --bundle build/player-bundle --out build/site

What it produces
----------------
::

    play/index.html     the /play/<key> page            (from player/play.html)
    play.js             its glue                        (from player/play.js)
    player.css          its styling                     (from player/player.css)
    solver_state.js     the admin player's pure module  (byte-identical copy)
    tokens.css          the design tokens               (byte-identical copy)
    vercel.json         the host's rewrite for /play/<key>
    puzzle/<key>.json   one REBUILT file per bundle puzzle (see below)

The two copies are copies and not forks: ADR-0041/R3 requires the board-state
module to be reused from ``src/nonogram/admin/static/solver_state.js`` by
byte-identical build-time copy, never by editing it, and the design tokens
travel the same way for the same reason (one definition of the colours, as
``tests/test_admin_design_tokens.py`` already holds for the panel's own copy).
:data:`COPIED_FROM_ADMIN` is the table, and the equality is checked here at
assembly time *and* from the test tree.

Why this script exists at all, rather than ``cp -r``
----------------------------------------------------
**Because this is where EC-048 is closed, and it could not be closed
downstream of here.** ADR-0041/R2 forbids any public asset from carrying "a
solution grid or data from which any solution cell is recoverable, for any
puzzle, on any export path". CARD-282 shipped the exporter and then *measured
a path straight through it*: the owner renames a puzzle to the base-64 of its
own packed grid, the exporter writes that string into the bundle's declared
``title`` field, every one of CARD-282's guards passes (the value's provenance
is "a stored title", which is a named good source), and the published JSON
base-64-decodes back to all 144 cells of a 12x12 answer. CARD-282's own
comment calls it "a REACHABLE PATH past ADR-0041/R2" and routes the question
here.

It is routed here because it cannot be answered by a scan. A scan has to
decide whether a *string* carries a grid, and there is no such decision
procedure: the set of encodings of a grid is not enumerable, and CARD-282
measured its denylist missing 7 of 7 planted encodings. So this script does
not filter free text. **It removes the channel**: every file it serves under
``puzzle/`` is REBUILT from :data:`SERVED_SCHEMA` rather than copied, and the
bundle's ``title`` — the only free-text field in the bundle — is not in that
schema and does not reach the site. A field the schema does not name is
dropped, named in the report, and never written.

What is left is then provably too small to carry a grid, which is the whole
point of the schema being closed:

* ``clues`` and ``key`` are the two projections ADR-0041 sanctions by name
  (R5 and R1). The clues determine the solution of a uniquely solvable puzzle
  — that is what the player plays against and is why no answer is needed to
  detect a solved board. They are the exemption, and they are *validated* for
  internal consistency (:func:`_clues`) so that "clues" cannot be borrowed as
  a free numeric channel;
* every other served value is drawn from a closed set this module can count:
  :data:`SERVED_VALUE_SPACE`. :func:`free_capacity_bits` sums the base-2
  logarithms of those counts, and :func:`check_capacity` refuses to assemble
  at all unless the total is strictly below ``MIN_SIZE * MIN_SIZE`` bits — the
  fewest cells any published grid can have (CON-011). A channel that cannot
  hold the smallest grid cannot hold any grid.

The number that bound rests on is computed here, by the deployed code, from
the declared value space; it is not transcribed into a comment. Ask for it
with ``python player/assemble.py --capacity``.

What this script does not reach, named rather than left to look covered
-----------------------------------------------------------------------
* ``index.json`` and ``book/<slug>.json`` are **not** copied. They are read by
  the library and book pages, which are CARD-284's and CARD-285's, and both
  carry a free-text ``title`` that this card's answer (drop the channel) would
  also have to be taken for — a book's title on its own cover page is a very
  different editorial question from a puzzle's name, and deciding it here
  would be deciding their cards. :func:`assemble` names the bundle files it
  ignored in its report so the omission is visible rather than silent.
* A grid recovered from the **clues** is not a leak but the game. Stated
  because a reader of EC-048 has to accept it, and measured (not merely
  asserted) by the test tree against the real solver.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "COPIED_FROM_ADMIN",
    "CAPACITY_CEILING_BITS",
    "KEY_PATTERN",
    "PLAYER_FILES",
    "SERVED_SCHEMA",
    "SERVED_VALUE_SPACE",
    "SITE_PUZZLE_DIR",
    "TIER_ALPHABET",
    "TIER_MAX_CHARS",
    "AssembleReport",
    "assemble",
    "check_capacity",
    "free_capacity_bits",
    "served_puzzle",
]

#: This file's directory (``player/``) and the repository root above it. Used
#: only to find the two files :data:`COPIED_FROM_ADMIN` names and
#: ``src/nonogram/limits.py``; every output path comes from ``--out``.
PLAYER_DIR = Path(__file__).resolve().parent
REPO_ROOT = PLAYER_DIR.parent


def _limits() -> tuple[int, int]:
    """``(MIN_SIZE, MAX_SIZE)`` from ``src/nonogram/limits.py``, by path.

    CLAUDE.md: use ``limits.py`` rather than writing 10 or 30. Loaded by path
    instead of imported by name so that this script needs nothing on
    ``sys.path`` and adds nothing to the Python package — safe precisely
    because that module "imports nothing", which is its own docstring's first
    promise and what puts it in the import guard's innermost rank.
    """
    path = REPO_ROOT / "src" / "nonogram" / "limits.py"
    spec = importlib.util.spec_from_file_location("_player_limits", path)
    if spec is None or spec.loader is None:  # pragma: no cover - unreachable
        raise RuntimeError(f"cannot read the supported grid extent from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.MIN_SIZE, module.MAX_SIZE


MIN_SIZE, MAX_SIZE = _limits()

# --------------------------------------------------------------------------
# The tree: what is copied, and from where
# --------------------------------------------------------------------------

#: ``player/`` source -> published path. The page is published as
#: ``play/index.html`` so that a plain static host serves ``/play/`` without a
#: rewrite and ``vercel.json``'s rewrite only has to cover ``/play/<key>``.
PLAYER_FILES: dict[str, str] = {
    "play.html": "play/index.html",
    "play.js": "play.js",
    "player.css": "player.css",
    "vercel.json": "vercel.json",
}

#: ADR-0041/R3's byte-identical build-time copies: admin source -> published
#: path. ``solver_state.js`` is the rule's own subject; ``tokens.css`` travels
#: the same way so the public page's colours are the one definition the panel
#: already uses (``meta/design/tokens.css``, mirrored into the panel's static
#: directory and held equal by ``tests/test_admin_design_tokens.py``).
#: **Copied, never edited** — G-1.
COPIED_FROM_ADMIN: dict[str, str] = {
    "src/nonogram/admin/static/solver_state.js": "solver_state.js",
    "src/nonogram/admin/static/tokens.css": "tokens.css",
}

#: Where the rebuilt puzzle files go, and the only directory of the bundle
#: this card's site serves.
SITE_PUZZLE_DIR = "puzzle"

#: A public puzzle key, as ADR-0041/R1 pins it: the first 10 lowercase
#: hexadecimal characters of a SHA-256 digest. Re-checked here rather than
#: trusted, because the key becomes a *file name* in the output tree.
KEY_PATTERN = re.compile(r"^[0-9a-f]{10}$")

# --------------------------------------------------------------------------
# The served schema — the closed set a /play/<key> asset may carry
# --------------------------------------------------------------------------

#: The alphabet and length a served ``tier`` may use. Lowercase ASCII letters
#: only, so the field cannot carry digits, punctuation or case as signal; the
#: value is lowercased before it is matched, so "Hard" is served as "hard"
#: and a tier that does not fit is dropped (never refused: a strange tier is
#: cosmetic, and refusing the puzzle would cost the player a page over a chip).
TIER_ALPHABET = "abcdefghijklmnopqrstuvwxyz"
TIER_MAX_CHARS = 12
_TIER = re.compile(rf"^[{TIER_ALPHABET}]{{1,{TIER_MAX_CHARS}}}$")

#: How many distinct values each non-exempt served field may take. The
#: authority :func:`free_capacity_bits` counts; see the module docstring.
#: ``clues`` and ``key`` are absent on purpose — they are ADR-0041's two
#: sanctioned projections of the grid and are checked by recipe instead
#: (:func:`_clues`, :data:`KEY_PATTERN`), exactly as
#: ``player_bundle.SOLUTION_DERIVED_FIELDS`` routes them in the exporter.
SERVED_VALUE_SPACE: dict[str, int] = {
    "width": MAX_SIZE - MIN_SIZE + 1,
    "height": MAX_SIZE - MIN_SIZE + 1,
    # Every string the tier rule admits, by length.
    "tier": 1 + sum(len(TIER_ALPHABET) ** k for k in range(1, TIER_MAX_CHARS + 1)),
}

#: The capacity ceiling, in bits: the fewest cells any published grid has
#: (CON-011's floor, squared). Derived, not written: a channel below it cannot
#: carry even the smallest grid, so it cannot carry any grid.
CAPACITY_CEILING_BITS = MIN_SIZE * MIN_SIZE


def free_capacity_bits() -> float:
    """How much a reader could learn from every non-exempt served field.

    The sum of ``log2`` of each field's value count — the information capacity
    of :data:`SERVED_VALUE_SPACE`, which is an upper bound on what the owner
    or the store could smuggle through those fields no matter how they are
    encoded. Computed here so the figure is derived by deployed code and can
    never be a stale number in a comment.
    """
    return sum(math.log2(count) for count in SERVED_VALUE_SPACE.values())


def check_capacity() -> float:
    """Refuse to assemble unless the free capacity is below the ceiling.

    Returns the capacity in bits. Raises :class:`ValueError` when a later
    change widens :data:`SERVED_VALUE_SPACE` past
    :data:`CAPACITY_CEILING_BITS` — which is the moment EC-048's argument
    stops holding, and the moment somebody has to go back to ADR-0041.
    """
    bits = free_capacity_bits()
    if bits >= CAPACITY_CEILING_BITS:
        raise ValueError(
            f"the served schema's free fields can carry {bits:.1f} bits, which "
            f"is not below the {CAPACITY_CEILING_BITS}-bit floor of a published "
            f"grid ({MIN_SIZE}x{MIN_SIZE} cells): EC-048's capacity argument no "
            "longer holds, so widening it needs ADR-0041 reopened, not this "
            "constant raised"
        )
    return bits


def _extent(value: object, what: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{what} is not an integer")
    if not MIN_SIZE <= value <= MAX_SIZE:
        raise ValueError(f"{what} {value} is outside {MIN_SIZE}..{MAX_SIZE}")
    return value


def _key(value: object, what: str = "key") -> str:
    if not isinstance(value, str) or not KEY_PATTERN.match(value):
        raise ValueError(f"{what} {value!r} is not 10 lowercase hex characters")
    return value


def _tier(value: object) -> str:
    """A served tier, or ``""`` when the stored value does not fit the rule.

    Lowercased first, so the admin panel's "Hard" and "hard" are one served
    value, and matched against :data:`_TIER`. A value that does not fit is
    dropped rather than refused — and dropped silently *into the report*,
    which :class:`AssembleReport` carries.
    """
    if not isinstance(value, str):
        return ""
    folded = value.strip().lower()
    return folded if _TIER.match(folded) else ""


def _line(clue: object, length: int, what: str) -> list[int]:
    """One validated clue: a run-length encoding that could fit ``length``.

    The ADR's convention (AC-013) is ``[0]`` for a line with no filled cell,
    never ``[]``. Everything else must be positive runs whose lengths plus one
    gap between each pair fit the line. This is what stops ``clues`` — the one
    exempt field with room in it — from being usable as a free numeric
    channel: a value smuggled here has to be a clue a line of this length
    could actually have.
    """
    if not isinstance(clue, list) or not clue:
        raise ValueError(f"{what} is not a non-empty list")
    numbers: list[int] = []
    for number in clue:
        if not isinstance(number, int) or isinstance(number, bool) or number < 0:
            raise ValueError(f"{what} holds {number!r}, which is not a run length")
        numbers.append(number)
    if 0 in numbers:
        if numbers != [0]:
            raise ValueError(f"{what} mixes 0 with other runs")
        return [0]
    if sum(numbers) + len(numbers) - 1 > length:
        raise ValueError(f"{what} cannot fit a line of {length} cells")
    return numbers


def _clues(value: object, width: int, height: int) -> dict[str, list[list[int]]]:
    """The served ``clues`` object, validated against the extent.

    One clue per row and per column, each one fitting its own line, and the
    two axes agreeing on how many cells are filled — a grid has one answer to
    that, so a row clue set and a column clue set that disagree did not come
    from one grid and are refused.
    """
    if not isinstance(value, dict) or set(value) != {"rows", "columns"}:
        raise ValueError("clues is not an object with exactly rows and columns")
    rows, columns = value["rows"], value["columns"]
    if not isinstance(rows, list) or len(rows) != height:
        raise ValueError(f"clues.rows is not {height} lines")
    if not isinstance(columns, list) or len(columns) != width:
        raise ValueError(f"clues.columns is not {width} lines")
    checked_rows = [_line(clue, width, f"clues.rows[{i}]") for i, clue in enumerate(rows)]
    checked_cols = [_line(clue, height, f"clues.columns[{i}]") for i, clue in enumerate(columns)]
    if sum(map(sum, checked_rows)) != sum(map(sum, checked_cols)):
        raise ValueError("clues.rows and clues.columns disagree on the filled count")
    return {"rows": checked_rows, "columns": checked_cols}


#: Every field a served ``puzzle/<key>.json`` carries, and how its value is
#: derived from the bundle's. **This tuple is the schema**: a name absent from
#: it is dropped, whatever the bundle calls it and however well-known it is.
#: ``title`` is absent deliberately — see the module docstring.
SERVED_SCHEMA: tuple[str, ...] = ("clues", "height", "key", "tier", "width")


def served_puzzle(payload: object, stem: str) -> tuple[dict[str, object], list[str]]:
    """``(served payload, dropped field names)`` for one bundle puzzle file.

    Rebuilt field by field from :data:`SERVED_SCHEMA`, never copied: the
    returned object holds exactly the schema's names and values this module
    derived itself. ``stem`` is the file's name without ``.json``, which
    ADR-0041/R1 makes the key, and the payload's own ``key`` must equal it —
    a file whose name and content disagree is refused rather than served under
    either name.

    Raises:
        ValueError: with a reason, for a payload the schema cannot accept. The
            caller turns that into a named refusal rather than a failed
            assembly: one unreadable puzzle must not cost the owner the site.
    """
    if not isinstance(payload, dict):
        raise ValueError("the file is not a JSON object")
    key = _key(payload.get("key"))
    if key != stem:
        raise ValueError(f"the file is named {stem}.json but carries the key {key}")
    width = _extent(payload.get("width"), "width")
    height = _extent(payload.get("height"), "height")
    served: dict[str, object] = {
        "key": key,
        "width": width,
        "height": height,
        "tier": _tier(payload.get("tier")),
        "clues": _clues(payload.get("clues"), width, height),
    }
    assert sorted(served) == sorted(SERVED_SCHEMA)  # the schema IS this object
    dropped = sorted(name for name in payload if name not in SERVED_SCHEMA)
    return served, dropped


# --------------------------------------------------------------------------
# Assembling
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class AssembleReport:
    """What one :func:`assemble` run wrote, and what it refused to write.

    ``dropped`` and ``ignored`` are the two silences this card was warned
    about, made loud: ``dropped`` is every ``(key, field)`` the served schema
    did not admit — the bundle's ``title`` on every puzzle, by design — and
    ``ignored`` is every bundle file outside ``puzzle/`` that this card's site
    does not serve. ``refused`` carries ``(key, reason)`` for a puzzle file the
    schema could not accept.
    """

    site_dir: Path
    puzzle_count: int
    capacity_bits: float
    dropped: tuple[tuple[str, str], ...] = ()
    refused: tuple[tuple[str, str], ...] = ()
    ignored: tuple[str, ...] = ()
    copied: tuple[str, ...] = ()


def _write(path: Path, text: str) -> None:
    """One output file, with every serialisation lever pinned.

    The same reasons ``player_bundle._dump`` gives: field order is the
    payload's content and not its construction order, a non-ASCII value is
    escaped identically everywhere, and the newline is explicit so the bytes
    do not follow the host's convention. Determinism matters here for the same
    reason it does there — "did the site change?" stays a byte diff.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _dump(path: Path, payload: object) -> None:
    _write(path, json.dumps(payload, sort_keys=True, ensure_ascii=True, indent=2, allow_nan=False) + "\n")


def assemble(bundle_dir: Path | str | None, out_dir: Path | str) -> AssembleReport:
    """Write the deployable site into ``out_dir``. Read-only against the input.

    ``bundle_dir`` is a CARD-282 player bundle (``None`` assembles the static
    half alone, which is what a page test that supplies its own puzzle file
    wants). ``out_dir`` is removed first, so the tree is a function of the
    input and nothing a previous run left behind survives into a deploy.
    """
    capacity = check_capacity()
    site = Path(out_dir)
    if site.exists():
        shutil.rmtree(site)
    site.mkdir(parents=True)

    copied: list[str] = []
    for source, published in PLAYER_FILES.items():
        _write(site / published, (PLAYER_DIR / source).read_text(encoding="utf-8"))
        copied.append(published)
    for source, published in COPIED_FROM_ADMIN.items():
        origin = REPO_ROOT / source
        data = origin.read_bytes()
        (site / published).write_bytes(data)
        # The equality R3 asks for, asserted where the copy is made as well as
        # from the test tree: a copy that is not byte-identical is a fork.
        if (site / published).read_bytes() != data:  # pragma: no cover - I/O
            raise RuntimeError(f"the copy of {source} is not byte-identical")
        copied.append(published)

    dropped: list[tuple[str, str]] = []
    refused: list[tuple[str, str]] = []
    ignored: list[str] = []
    count = 0
    if bundle_dir is not None:
        bundle = Path(bundle_dir)
        for path in sorted(bundle.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(bundle).as_posix()
            if not relative.startswith(f"{SITE_PUZZLE_DIR}/") or path.suffix != ".json":
                ignored.append(relative)
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                served, names = served_puzzle(payload, path.stem)
            except (ValueError, UnicodeDecodeError) as unservable:
                refused.append((path.stem, str(unservable)))
                continue
            dropped.extend((path.stem, name) for name in names)
            _dump(site / SITE_PUZZLE_DIR / f"{served['key']}.json", served)
            count += 1

    return AssembleReport(
        site_dir=site,
        puzzle_count=count,
        capacity_bits=capacity,
        dropped=tuple(sorted(dropped)),
        refused=tuple(sorted(refused)),
        ignored=tuple(sorted(ignored)),
        copied=tuple(sorted(copied)),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--bundle", default=None, help="a CARD-282 player bundle directory")
    parser.add_argument("--out", default=None, help="where to write the site")
    parser.add_argument(
        "--capacity",
        action="store_true",
        help="print the served schema's free capacity and the ceiling, and stop",
    )
    args = parser.parse_args(argv)
    if args.capacity:
        print(
            f"{free_capacity_bits():.2f} bits of non-exempt capacity; "
            f"ceiling {CAPACITY_CEILING_BITS} bits "
            f"({MIN_SIZE}x{MIN_SIZE} cells, the smallest published grid)"
        )
        for name, count in sorted(SERVED_VALUE_SPACE.items()):
            print(f"  {name}: {count} values, {math.log2(count):.2f} bits")
        return 0
    if args.out is None:
        parser.error("--out is required unless --capacity is given")
    report = assemble(args.bundle, args.out)
    print(f"{report.puzzle_count} puzzles into {report.site_dir}")
    if report.dropped:
        fields = sorted({name for _, name in report.dropped})
        print(f"  dropped (not in the served schema): {', '.join(fields)}")
    for key, reason in report.refused:
        print(f"  refused {key}: {reason}")
    if report.ignored:
        print(f"  not served by this page: {', '.join(report.ignored)}")
    return 0


if __name__ == "__main__":  # pragma: no cover - the command line
    sys.exit(main())
