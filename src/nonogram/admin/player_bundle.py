"""COMP-009's player-bundle exporter — FR-045, ADR-0041 (CARD-282).

The data layer of the public player phase. A printed book is frozen, so the
public player reads **static JSON exported at publication time** rather than
the admin panel's Postgres: no live database in the customer path, and the
panel stays behind its CON-015 / CON-016 door.

What :func:`export_bundle` writes (TERM-040, the player bundle)::

    index.json          {"puzzles": [entry, ...]}   the library index
    puzzle/<key>.json   one file per published puzzle: its clues + metadata
    book/<slug>.json    one file per finalized book: slug, title, puzzle keys

A *published* puzzle is one a finalized book carries (FR-045's assumption,
2026-10-23), and *finalized* is every book status except draft —
:data:`FINALIZED_STATUSES`, derived from :class:`BookStatus` rather than
written out, so a status a later card adds is finalized or not by the enum's
say and never by a stale copy here (ADR-0039/R2).

The two engineering constraints this module is designed around
--------------------------------------------------------------
**EC-048 (ADR-0041/R2, ADR-0038/R6) — nothing here carries a solution grid,
"or data from which any solution cell is recoverable".** The grid reaches this
module (it has to: the clues and the key are computed from it) and leaves it
only as two lossy projections, each one sanctioned by name:

* the **clues**, from :func:`~nonogram.clues.compute_clues` — the one encoder,
  the same call the storage boundary makes (ADR-0038/R3, ADR-0041/R5). They
  are what the player plays against; for a uniquely solvable puzzle they
  determine the solution, which is the whole point and is why the public
  player needs no answer to detect a solved board (ADR-0041's Context).
* the **key**, from :func:`puzzle_key` — SHA-256 truncated to 10 hex
  characters, which ADR-0041/R1 *requires* every public URL, bundle filename
  and index entry to use. It is one-way: the ADR's own words are "it is
  one-way, so the URL reveals nothing about the solution".

Those two are the only solution-derived values any bundle file carries, and
:data:`SOLUTION_DERIVED_FIELDS` names them so the scan behind AC-381 can state
the exemption instead of absorbing it (ADR-0039/R3). Everything else written
here is extent, tier, title or book order. The **picture name is not written
at all**: the title falls back from the stored ``puzzle_name`` to a neutral
string built from the key, never to ``source_image`` the way the admin panel's
own solve page does (``app.py``'s ``puzzle_solve``) — this is the public
surface, which is where that difference matters.

**EC-049 (ADR-0041/R5) — read-only and deterministic.** This module issues no
INSERT, UPDATE or DELETE: it reads books through
:class:`~nonogram.admin.book_manager.BookManager` and puzzles through
:class:`~nonogram.admin.puzzle_review.PuzzleReviewService`, both read methods
only, and never touches an ORM row. Determinism is built rather than hoped
for:

* every collection written is **sorted explicitly** — index entries and puzzle
  files by key, books by slug — and no set or dict iteration order reaches the
  output;
* :func:`_dump` pins the serialisation: ``sort_keys``, ``ensure_ascii``, a
  fixed indent, an explicit ``"\\n"`` newline and ``allow_nan=False``;
* :func:`_refuse_unless_serialisable` refuses a **float** anywhere in a
  payload, so no value in the bundle has a formatting question to get wrong,
  and refuses any type it does not recognise rather than letting
  :mod:`json` improvise (deny-default, ADR-0039/R2);
* two puzzle rows with the same grid share one key by ADR-0041's design, so
  their metadata is reconciled by :func:`_settled` — a pure function of the
  candidate values, not of the order the rows arrived in;
* the two directories this module owns are removed before they are rewritten,
  so the tree is a function of the input and not of what a previous export
  left behind.

The output goes outside the Python package, under ``build/`` (gitignored) by
default — see :func:`default_output_dir`.

Both recipes are the ADR's, and R7 excludes the title on purpose
----------------------------------------------------------------
ADR-0041 pins the *puzzle* key as R1 and the *book slug* as **R7** (DEC-044b,
owner decision 2026-10-24); any change to either is a breaking change to every
printed book and needs a new ADR. Both are the same
prefix-then-fixed-width-payload shape, and :func:`puzzle_key` and
:func:`book_slug` are the one implementation each of them calls for.

R7's **title exclusion is the part to read twice**: a book's slug hashes its
puzzle keys and nothing else. The title is not an input, deliberately — the
slug is printed in a QR code that cannot be re-pointed, and a title is
editorial, so a one-character typo fix in the admin panel must not silently
break every code in an already-printed run. (CARD-282 shipped a
``"book:{title}:"`` variant in the commit before R7 existed, and R7's own text
names that variant as the alternative the owner decided against; this is the
revision to R7.) What the slug *does* move with is the book's puzzle
membership, which is a change of content rather than an editorial one and is
already an explicit confirmed act on a book that has left draft (INV-012).
Both directions are held by R7's own control,
``tests/test_player_bundle.py::test_the_slug_does_not_move_when_the_title_is_edited``.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from nonogram.admin.book_manager import BookStatus
from nonogram.clues import compute_clues

__all__ = [
    "BOOK_FILE_FIELDS",
    "BundleReport",
    "FINALIZED_STATUSES",
    "INDEX_ENTRY_FIELDS",
    "INDEX_FILE_FIELDS",
    "KEY_LENGTH",
    "PUZZLE_CLUES_FIELDS",
    "PUZZLE_FILE_FIELDS",
    "SOLUTION_DERIVED_FIELDS",
    "book_slug",
    "default_output_dir",
    "export_bundle",
    "puzzle_key",
]

# --------------------------------------------------------------------------
# The schema — the authority the AC-381 scan derives its field set from
# --------------------------------------------------------------------------
#
# Declared as data rather than left implicit in the writers below so that a
# scan for forbidden content can *enumerate at runtime* what a bundle file is
# allowed to carry and fail on anything else (ADR-0039/R2: a guard's set is
# derived from an authority the runtime can enumerate, and an unrecognised
# field is a failure, not a pass). The writers build their payloads from these
# same names, so the two cannot drift apart silently, and
# ``tests/test_player_bundle.py`` additionally holds each tuple to the literal
# field list FR-045 / AC-380 spell out — which is what stops a mutant from
# widening the schema and the scan together.

#: Fields of one entry in ``index.json``'s ``puzzles`` list.
INDEX_ENTRY_FIELDS: tuple[str, ...] = ("height", "key", "tier", "title", "width")

#: Top-level fields of ``index.json``.
INDEX_FILE_FIELDS: tuple[str, ...] = ("puzzles",)

#: Top-level fields of ``puzzle/<key>.json``.
PUZZLE_FILE_FIELDS: tuple[str, ...] = (
    "clues",
    "height",
    "key",
    "tier",
    "title",
    "width",
)

#: Fields of a puzzle file's ``clues`` object.
PUZZLE_CLUES_FIELDS: tuple[str, ...] = ("columns", "rows")

#: Top-level fields of ``book/<slug>.json``.
BOOK_FILE_FIELDS: tuple[str, ...] = ("puzzle_keys", "slug", "title")

#: The only bundle fields computed from a solution grid, and therefore the
#: whole of EC-048's declared exemption (ADR-0039/R3). ``clues`` is the lossy
#: projection the player plays against (ADR-0041/R5 requires it to come from
#: ``compute_clues``); ``key`` and ``puzzle_keys`` are the one-way hash
#: ADR-0041/R1 requires every public URL and filename to use. A fourth name
#: appearing here is an architecture decision, not a worktree one.
SOLUTION_DERIVED_FIELDS = frozenset({"clues", "key", "puzzle_keys"})

# --------------------------------------------------------------------------
# ADR-0041/R1 — the public player key, and the one implementation of it
# --------------------------------------------------------------------------

#: How many hex characters of the digest the key is (ADR-0041/R1). Named
#: because the ADR calls the truncation length part of the recipe, so a change
#: to it is a breaking change to every printed book.
KEY_LENGTH = 10

#: The prefix :func:`book_slug` hashes under. See the module docstring: the
#: book slug is this card's recipe, not ADR-0041's.
_BOOK_PREFIX = "book:"


def puzzle_key(grid: Sequence[Sequence[bool]]) -> str:
    """``grid``'s public player key — ADR-0041/R1, TERM-041.

    The first :data:`KEY_LENGTH` lowercase hexadecimal characters of SHA-256
    over the UTF-8 bytes of ``"{width}x{height}:"`` followed by the grid's
    cells in row-major order, ``'1'`` for a filled cell and ``'0'`` for an
    empty one. A 2x2 grid with only its top-left cell filled hashes the bytes
    of ``"2x2:1000"`` — the ADR's own example.

    This is the **one** implementation (ADR-0041/R1: "Exactly one
    implementation computes it"). Note in particular what it is *not*:
    :meth:`PuzzleReviewService._grid_fingerprint` hashes a string of the same
    shape with the extent the other way round (``"{height}x{width}:"``) and
    does not truncate, so for any non-square grid it is a different value for
    the same cells. It is an internal memo key and must never be mistaken for
    this one.

    The extent is taken from the grid itself, so the key and the bundle's
    ``width``/``height`` metadata have a single source and cannot disagree
    with each other.

    Raises:
        ValueError: if ``grid`` is not a non-empty rectangle. Refused rather
            than hashed, because "the cells in row-major order" has no meaning
            for a ragged grid and a key nobody can recompute from the printed
            book is worse than no key at all.
    """
    height = len(grid)
    if height == 0:
        raise ValueError("a grid with no rows has no key")
    width = len(grid[0])
    if width == 0:
        raise ValueError("a grid with no columns has no key")
    if any(len(row) != width for row in grid):
        raise ValueError(
            "refusing to key a ragged grid: row-major order is undefined for it"
        )
    cells = "".join("1" if cell else "0" for row in grid for cell in row)
    text = f"{width}x{height}:{cells}"
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:KEY_LENGTH]


def book_slug(puzzle_keys: Iterable[str]) -> str:
    """A finalized book's public slug — ADR-0041/R7, DEC-044b.

    The first :data:`KEY_LENGTH` lowercase hexadecimal characters of SHA-256
    over the UTF-8 bytes of ``"book:"`` followed by the book's puzzle keys in
    book order, concatenated **with no separator** — every key is exactly
    :data:`KEY_LENGTH` characters by R1, so the concatenation is unambiguous
    without one, and the shape is R1's own: a prefix naming the domain, then a
    fixed-width payload. This is the one implementation (R7: "Exactly one
    implementation computes it"), and any change to the prefix, the ordering,
    the absence of a separator, the algorithm, the truncation length or the
    case is a breaking change to every printed book requiring a new ADR.

    **The title is not a parameter, let alone an input.** R7 excludes it
    because the slug is printed in a QR code that cannot be re-pointed and a
    title is editorial: a typo fix would otherwise move every code in an
    already-printed run. Nothing else here needs the title either — the book
    file's ``title`` field is read straight from the book by :func:`_book_title`
    — so it is gone from the signature rather than accepted and ignored, which
    is the only version of "not an input" a caller cannot get wrong.

    Content addressed for the reason ADR-0041 rejected a stored slug for
    puzzles: a content hash survives a database re-seed because the printed
    book preserves its puzzles.

    One consequence of excluding the title that is **not** harmless and is
    handled rather than noted: two finalized books holding the same puzzles in
    the same order now share a slug *even when their titles differ*, so one
    file has to speak for both. :func:`_book_file` settles that, so which title
    it carries is a function of the titles and not of the order the books were
    read in — see there.
    """
    text = _BOOK_PREFIX + "".join(puzzle_keys)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:KEY_LENGTH]


# --------------------------------------------------------------------------
# What counts as published
# --------------------------------------------------------------------------

#: The statuses a book is *finalized* in: every one except draft, derived from
#: the enum rather than listed (ADR-0039/R2). A book leaves draft only through
#: the readiness gate (ADR-0035/R1, INV-007) and returns to draft on any
#: membership change (INV-012), so "not draft" is exactly "holds the
#: membership that last passed the plan check".
FINALIZED_STATUSES = frozenset(
    status.value for status in BookStatus if status is not BookStatus.DRAFT
)


@dataclass(frozen=True)
class BundleReport:
    """What one :func:`export_bundle` run wrote, for the owner's flash message.

    ``skipped`` carries ``(puzzle id, reason)`` pairs sorted by id — a member
    whose stored grid is unreadable is left out of the bundle and *named*,
    rather than silently dropped or allowed to fail the whole export.
    """

    output_dir: Path
    puzzle_count: int
    book_count: int
    skipped: tuple[tuple[str, str], ...] = ()


def default_output_dir() -> Path:
    """Where the bundle goes when the caller names no directory.

    ``build/player-bundle`` under the repository root for a src-layout
    checkout (``build/`` is gitignored, so an export never enters the index),
    and under the process's working directory otherwise. Outside the Python
    package either way, which ADR-0041/R3 wants for the player tree and this
    module's output shares no reason to violate.
    """
    parents = Path(__file__).resolve().parents
    root = parents[3] if len(parents) > 3 and parents[2].name == "src" else Path.cwd()
    return root / "build" / "player-bundle"


def export_bundle(
    book_manager: Any,
    puzzle_store: Any,
    output_dir: Path | str | None = None,
) -> BundleReport:
    """Write the player bundle for every finalized book. Read-only (EC-049).

    The callable entry point the owner's "Export player bundle" action and the
    tests both drive (ADR-0041/R5: an explicit action, never a side effect of
    anything else).

    Args:
        book_manager: a :class:`~nonogram.admin.book_manager.BookManager`.
            Read through ``get_all_books`` only; no book is modified (G-1).
        puzzle_store: a
            :class:`~nonogram.admin.puzzle_review.PuzzleReviewService`. Read
            through ``get_puzzles`` only, by id, from each book's own
            ``puzzle_ids`` — never from the ``puzzles.book_id`` mirror
            (ADR-0033/R1).
        output_dir: where to write. :func:`default_output_dir` when omitted.

    Returns:
        A :class:`BundleReport`.

    The tree is rewritten rather than merged into: ``index.json`` and the two
    directories this module owns are removed first, so the output is a
    function of the input alone and a bundle diff at deploy time means what it
    says. Nothing outside those three paths is touched.
    """
    root = Path(output_dir) if output_dir is not None else default_output_dir()

    books = [
        book
        for book in book_manager.get_all_books()
        if book.status in FINALIZED_STATUSES
    ]

    # One read per book, by the book's own ids. Keyed by puzzle key, because
    # ADR-0041 makes the key the name of the *content*: two rows with the same
    # grid are one public puzzle.
    candidates: dict[str, list[Mapping[str, Any]]] = {}
    skipped: dict[str, str] = {}
    # Keyed by slug, because ADR-0041/R7 makes the slug the name of the book's
    # *content* too: two finalized books holding the same puzzles in the same
    # order are one public book file, and :func:`_book_file` settles the one
    # thing they can still disagree about.
    book_keys: dict[str, list[tuple[str, tuple[str, ...]]]] = {}
    for book in books:
        records = puzzle_store.get_puzzles(book.puzzle_ids)
        keys: list[str] = []
        for puzzle_id in book.puzzle_ids:
            record = records.get(puzzle_id)
            if record is None:
                skipped[str(puzzle_id)] = "no stored puzzle with this id"
                continue
            try:
                key = puzzle_key(_grid_of(record))
            except (TypeError, ValueError) as unreadable:
                skipped[str(puzzle_id)] = str(unreadable)
                continue
            keys.append(key)
            candidates.setdefault(key, []).append(record)
        book_keys.setdefault(book_slug(keys), []).append(
            (_book_title(book), tuple(keys))
        )

    entries = [_index_entry(key, candidates[key]) for key in sorted(candidates)]

    _reset(root)
    _dump(root / "index.json", {"puzzles": entries})
    for entry in entries:
        _dump(root / "puzzle" / f"{entry['key']}.json", _puzzle_file(entry, candidates))
    for slug in sorted(book_keys):
        _dump(root / "book" / f"{slug}.json", _book_file(slug, book_keys[slug]))

    return BundleReport(
        output_dir=root,
        puzzle_count=len(entries),
        book_count=len(book_keys),
        skipped=tuple(sorted(skipped.items())),
    )


# --------------------------------------------------------------------------
# Building one file's payload
# --------------------------------------------------------------------------


def _index_entry(key: str, records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """One ``index.json`` entry, carrying exactly :data:`INDEX_ENTRY_FIELDS`.

    ``records`` is every stored row whose grid hashes to ``key``. Their extent
    is identical by construction (the key carries it), and their metadata is
    reconciled by :func:`_settled` so that the entry is a function of the rows
    and not of the order they were read in.
    """
    grid = _grid_of(records[0])
    return {
        "key": key,
        "width": len(grid[0]),
        "height": len(grid),
        "tier": _settled(record.get("difficulty_tier") for record in records),
        "title": _settled(_title_of(record, key) for record in records),
    }


def _puzzle_file(
    entry: Mapping[str, Any], candidates: Mapping[str, Sequence[Mapping[str, Any]]]
) -> dict[str, Any]:
    """One ``puzzle/<key>.json`` payload: the index entry plus its clues.

    The clues come from :func:`~nonogram.clues.compute_clues` of the stored
    grid — the one encoder, the same call the storage boundary makes
    (ADR-0041/R5, ADR-0038/R3, FR-005). They are *not* read from the stored
    ``clues_rows`` / ``clues_cols`` columns, which the schema itself marks
    "display only".
    """
    found = compute_clues(_grid_of(candidates[entry["key"]][0]))
    return {
        **entry,
        "clues": {
            "rows": [list(clue) for clue in found.rows],
            "columns": [list(clue) for clue in found.columns],
        },
    }


def _book_file(slug: str, books: Sequence[tuple[str, tuple[str, ...]]]) -> dict[str, Any]:
    """One ``book/<slug>.json`` payload, carrying exactly :data:`BOOK_FILE_FIELDS`.

    ``books`` is every finalized book whose puzzle keys hash to ``slug``.
    Before ADR-0041/R7 that was always one book, because the title was in the
    hash; R7 excluded the title, so two books with the same puzzles in the same
    order are now one public book under one slug, and their titles can differ.

    The keys are the same for all of them — the slug *is* their hash — and the
    title is reduced by :func:`_settled`, a pure function of the candidate
    titles. That matters for EC-049 rather than for editorial reasons: writing
    "whichever book was read last" would make the bundle's bytes depend on the
    store's row order, which is exactly the determinism the byte diff at deploy
    time rests on.
    """
    return {
        "slug": slug,
        "title": _settled(title for title, _ in books),
        "puzzle_keys": list(min(books)[1]),
    }


def _title_of(record: Mapping[str, Any], key: str) -> str:
    """A puzzle's public title: its stored name, else a neutral fallback.

    **The fallback is deliberately not the picture name.** The admin panel's
    own solve page falls back ``puzzle_name`` -> ``source_image`` -> id, and
    the backlog's "Wave-31 goal-check" already flags that page for leaking the
    picture name in its hidden solved banner. This is the public surface, so
    the chain stops at the name: an unnamed puzzle is "Puzzle <key>", which
    carries nothing the filename does not already.
    """
    name = record.get("puzzle_name")
    if isinstance(name, str) and name.strip():
        return name.strip()
    return f"Puzzle {key}"


def _book_title(book: Any) -> str:
    """A book's display title, as stored. Blank titles become a stable stand-in."""
    title = getattr(getattr(book, "metadata", None), "title", None)
    if isinstance(title, str) and title.strip():
        return title.strip()
    return "Untitled book"


def _settled(values: Iterable[Any]) -> Any:
    """One value for a field several rows sharing a key disagree about.

    ADR-0041's "identical grids share a key by design" means two stored rows
    can land in one public puzzle, and nothing stops their tier or name from
    differing. The reduction is the first of the distinct values in sort
    order, with ``None`` last — a pure function of the *set* of candidates, so
    the output cannot depend on which row was read first. Not a merge policy
    anybody asked for; a determinism requirement (EC-049) met explicitly
    rather than by accident of iteration order.
    """
    distinct = {value for value in values}
    ordered = sorted(
        distinct, key=lambda value: (value is None, "" if value is None else str(value))
    )
    return ordered[0] if ordered else None


def _grid_of(record: Mapping[str, Any]) -> list[list[bool]]:
    """``record``'s stored grid as the ADR-0012 boundary type.

    Raises:
        ValueError: if the stored value is not a non-empty rectangle of cells.
            The caller turns that into a named skip rather than a failed
            export: one damaged row must not cost the owner the whole bundle.
    """
    grid = record.get("grid")
    if not isinstance(grid, (list, tuple)) or not grid:
        raise ValueError("stored grid is not a non-empty list of rows")
    rows: list[list[bool]] = []
    for row in grid:
        if not isinstance(row, (list, tuple)) or not row:
            raise ValueError("stored grid has a row that is not a non-empty list")
        rows.append([bool(cell) for cell in row])
    if any(len(row) != len(rows[0]) for row in rows):
        raise ValueError("stored grid is ragged")
    return rows


# --------------------------------------------------------------------------
# Writing — where determinism is pinned
# --------------------------------------------------------------------------

#: Every type a bundle payload may carry. ``float`` is deliberately absent:
#: nothing in the bundle is fractional, and a type with a formatting question
#: cannot get it wrong if it is never written (EC-049). Anything else — a
#: ``Decimal``, a ``datetime``, a ``UUID``, a tuple, a set — is refused rather
#: than left to :mod:`json` to improvise or to reject with a less useful
#: message (deny-default, ADR-0039/R2).
_SERIALISABLE = (str, bool, int, type(None), list, dict)


def _refuse_unless_serialisable(payload: Any, where: str = "payload") -> None:
    """Refuse a payload holding a float, or any type :data:`_SERIALISABLE` omits."""
    if isinstance(payload, float):
        raise TypeError(
            f"{where}: refusing to write a float into the bundle — every value "
            "in it is exact, and a float is the one that could be formatted "
            "two ways"
        )
    if not isinstance(payload, _SERIALISABLE):
        raise TypeError(f"{where}: {type(payload).__name__} is not a bundle value")
    if isinstance(payload, dict):
        for name, value in payload.items():
            if not isinstance(name, str):
                raise TypeError(f"{where}: field names must be strings")
            _refuse_unless_serialisable(value, f"{where}.{name}")
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            _refuse_unless_serialisable(value, f"{where}[{index}]")


def _dump(path: Path, payload: Mapping[str, Any]) -> None:
    """Write ``payload`` to ``path`` as the bundle's one JSON shape.

    Every lever :mod:`json` leaves open is set here and nowhere else:
    ``sort_keys`` so field order is the payload's content and not its
    construction order, ``ensure_ascii`` so a non-ASCII title is escaped the
    same way on every platform, a fixed ``indent``, ``allow_nan=False``, and
    an explicit trailing ``"\\n"`` written with ``newline="\\n"`` so the bytes
    do not depend on the host's line-ending convention.
    """
    _refuse_unless_serialisable(dict(payload), path.name)
    text = json.dumps(
        payload, sort_keys=True, ensure_ascii=True, indent=2, allow_nan=False
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text + "\n", encoding="utf-8", newline="\n")


def _reset(root: Path) -> None:
    """Remove the three paths this module owns under ``root``, and only those.

    So the tree is a function of the input: a puzzle that has left every
    finalized book leaves the bundle with it, and "did the bundle change?"
    stays a byte diff. Anything else in ``root`` — a deploy config, the copied
    player files CARD-283 will put there — is left alone.
    """
    (root / "index.json").unlink(missing_ok=True)
    for owned in ("puzzle", "book"):
        shutil.rmtree(root / owned, ignore_errors=True)
