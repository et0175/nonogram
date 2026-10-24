"""CARD-282 — the admin panel exports the public player's bundle (FR-045).

    AC-380  test_bundle_tree_and_clues_match_the_encoder
    AC-381  test_bundle_is_clean_of_answers                 (EC-048)
    AC-382  test_export_is_readonly_and_deterministic       (EC-049)

The three criteria are the three functions named above; everything else in
this file is either a *control* for a mechanism one of them relies on — each
one able to fail, with its failing state constructed rather than imagined
(ADR-0039/R1) — or a pin on a set one of them derives (ADR-0039/R2).

Where each mechanism lives, so a mutant can delete it
-----------------------------------------------------
* :func:`answer_violations` is AC-381's scan. It is a pure function of a
  written bundle and the records it was written from, so
  ``test_the_answer_scan_catches_each_leak_shape`` can hand it a bundle with a
  leak planted in it and watch it fire. Without that control the AC test would
  be a claim; with it, "no file carries the answer" has a measured failing
  state.
* The scan's two halves are deliberately different in kind, because a mutant
  can widen one of them:

  - :func:`forbidden_encodings` derives, **from the grid itself at runtime**,
    the encodings a solution could leave in a file: both cell alphabets, both
    traversal orders, each reversed, several separators, the JSON form, the
    hex and base-64 forms of the bit string, and the untruncated digest.
    Nothing is written out as a literal, so it covers a grid nobody has seen.
  - :func:`object_keys` walks every JSON object in the bundle and the scan
    holds the result to :data:`DECLARED_FIELDS`, which is derived from
    ``player_bundle``'s own schema tuples. **An unrecognised field is a
    violation, not a pass** — and because that authority is code a mutant
    could widen, ``test_the_declared_schema_is_the_field_set_the_criteria_name``
    holds those tuples to the literal field list AC-380 and FR-045 spell out.
* :func:`recorded_statements` is EC-049's read-only mechanism: a listener on
  SQLAlchemy's ``Engine`` class that records every statement and *refuses*
  anything whose leading verb is not in :data:`READ_ONLY_VERBS`. Default-deny,
  so a verb nobody thought of is a failure.
  ``test_the_statement_log_catches_a_write`` is its control — a real write,
  caught.
* :func:`table_rows` snapshots the database from
  ``Base.metadata.sorted_tables``, so a table a later migration adds is
  compared without this file being edited.

What this file does **not** assert, deliberately
------------------------------------------------
That the bundle is *playable*. The public player is CARD-283 and does not
exist; nothing here reads ``player/``.

No ``hypothesis`` (ADR-0006/R1 keeps it out of the baseline): AC-381's corpus
is built with stdlib :class:`random.Random` from a fixed seed and the test
asserts its own size, so the corpus cannot silently shrink.
"""

from __future__ import annotations

import base64
import hashlib
import itertools
import json
import os
import random
import re
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path

import pytest
from sqlalchemy import event, text
from sqlalchemy.engine import Engine

from nonogram import clues
from nonogram.admin import player_bundle
from nonogram.admin.book_manager import Book, BookManager, BookMetadata, BookStatus
from nonogram.admin.book_plan import DistributionPlan, Split, bucket_of
from nonogram.admin.puzzle_review import PuzzleReviewService
from nonogram.db.models import Base
from nonogram.limits import MAX_SIZE, MIN_SIZE
from tests.helpers.db import sqlite_session_scope

REPO_ROOT = Path(__file__).resolve().parents[1]

#: The corpus AC-381 scans. Large enough that a leak shape has to survive
#: every grid in it, and asserted inside the test so it cannot shrink.
CORPUS_SEED = 282
MIN_CORPUS_GRIDS = 48

#: The picture names the corpus stores, so the scan has a real value to look
#: for. Distinct from every puzzle name, or "the picture name is absent" would
#: be unfalsifiable.
PICTURE_SUFFIX = ".png"


# --------------------------------------------------------------------------
# The field set AC-380 / FR-045 name, written out once
# --------------------------------------------------------------------------
#
# This is the *literal* half of the authority, and it is here rather than in
# the module under test on purpose: the scan derives its field set from
# ``player_bundle``'s schema tuples, which a mutant can widen alongside the
# writers. Holding those tuples to this literal set is what makes that mutant
# a kill. Read off the acceptance criteria:
#
#   AC-380 "one entry per published puzzle (key, width, height, difficulty
#   tier, title)" ... "row clues and column clues plus the same metadata" ...
#   "its slug, display title, and the ordered list of its puzzle keys"
CRITERIA_FIELDS = {
    "index entry": {"key", "width", "height", "tier", "title"},
    "index file": {"puzzles"},
    "puzzle file": {"key", "width", "height", "tier", "title", "clues"},
    "puzzle clues": {"rows", "columns"},
    "book file": {"slug", "title", "puzzle_keys"},
}

#: Every field name any bundle file may carry, derived from the exporter's own
#: declared schema — the authority the runtime can enumerate (ADR-0039/R2).
DECLARED_FIELDS = frozenset(
    name
    for declared in (
        player_bundle.INDEX_ENTRY_FIELDS,
        player_bundle.INDEX_FILE_FIELDS,
        player_bundle.PUZZLE_FILE_FIELDS,
        player_bundle.PUZZLE_CLUES_FIELDS,
        player_bundle.BOOK_FILE_FIELDS,
    )
    for name in declared
)


# --------------------------------------------------------------------------
# An independent second implementation of the two derived values
# --------------------------------------------------------------------------


def independent_key(grid) -> str:
    """ADR-0041/R1's recipe, written again and differently.

    Byte assembly through a :class:`bytearray` and a nested loop rather than
    the production helper's generator comprehension, and the extent formatted
    separately — so an agreement between the two is evidence about the recipe
    and not about one expression being compared with itself (CLAUDE.md's
    "prefer an independent second implementation").
    """
    width = len(grid[0])
    height = len(grid)
    material = bytearray(f"{width}x{height}:".encode("utf-8"))
    for row in grid:
        for cell in row:
            material.append(0x31 if cell else 0x30)
    return hashlib.sha256(bytes(material)).hexdigest()[:10]


def independent_clues(grid):
    """Row and column clues by :func:`itertools.groupby`, not by COMP-004.

    The AC compares the bundle's clues with ``compute_clues``; this is the
    cross-check that keeps that comparison from being a function compared with
    itself. ``[0]`` for a line with no filled cells, the AC-013 convention.
    """

    def line(cells):
        runs = [len(list(group)) for value, group in itertools.groupby(cells) if value]
        return runs or [0]

    return (
        [line(row) for row in grid],
        [line([row[x] for row in grid]) for x in range(len(grid[0]))],
    )


# --------------------------------------------------------------------------
# AC-381's scan — EC-048, including its second clause
# --------------------------------------------------------------------------


def forbidden_encodings(grid) -> dict[str, str]:
    """Encodings of ``grid``'s cells that must appear in no bundle file.

    Derived from the grid at run time: the product of two cell alphabets, four
    traversals (row-major and column-major, each forwards and reversed) and
    four separators, plus the JSON forms of the grid and of its rows, plus the
    hex and base-64 forms of the row-major bit string, plus the **untruncated**
    SHA-256 digest of the key's own material.

    That last one is EC-048's second clause taken literally: the first ten hex
    characters are the key ADR-0041/R1 requires, and the full digest is 54 more
    characters of the same one-way material that nothing has any reason to
    carry. Writing it would narrow nothing either — which is exactly why it
    belongs here rather than in a judgement call: *data derived from the
    solution that the ADR did not sanction is forbidden by default*, and the
    exemption is the three names in
    ``player_bundle.SOLUTION_DERIVED_FIELDS``, no more.

    Only encodings at least 8 characters long are kept: a 1x2 grid's bit
    string is "10", which occurs in clue numbers by coincidence, and a scan
    that cannot tell coincidence from a leak reports noise rather than
    evidence.
    """
    height, width = len(grid), len(grid[0])
    row_major = [bool(cell) for row in grid for cell in row]
    column_major = [bool(grid[y][x]) for x in range(width) for y in range(height)]
    found: dict[str, str] = {}
    for (one, zero), (order, cells), separator in itertools.product(
        (("1", "0"), ("#", "."), ("X", " "), ("true", "false")),
        (
            ("row-major", row_major),
            ("row-major reversed", list(reversed(row_major))),
            ("column-major", column_major),
            ("column-major reversed", list(reversed(column_major))),
        ),
        ("", ",", " ", "\\n"),
    ):
        text_form = separator.join(one if cell else zero for cell in cells)
        found[f"{order} {one}/{zero} joined by {separator!r}"] = text_form
    bits = "".join("1" if cell else "0" for cell in row_major)
    found["grid as JSON"] = json.dumps([[bool(c) for c in row] for row in grid])
    found["rows as JSON"] = json.dumps(
        [[1 if c else 0 for c in row] for row in grid]
    )[1:-1]
    found["bit string as hex"] = f"{int(bits, 2):x}"
    found["bit string as base64"] = base64.b64encode(bits.encode("ascii")).decode()
    found["the untruncated digest"] = hashlib.sha256(
        f"{width}x{height}:{bits}".encode("utf-8")
    ).hexdigest()
    return {name: form for name, form in found.items() if len(form) >= 8}


def object_keys(payload) -> set[str]:
    """Every field name in every JSON object inside ``payload``."""
    names: set[str] = set()
    if isinstance(payload, dict):
        for name, value in payload.items():
            names.add(name)
            names |= object_keys(value)
    elif isinstance(payload, list):
        for value in payload:
            names |= object_keys(value)
    return names


def answer_violations(root: Path, records) -> list[str]:
    """Every way the bundle under ``root`` fails EC-048, named.

    ``records`` is every stored puzzle record the bundle was written from. The
    three checks, in the order they would catch a leak:

    1. no file's bytes contain any of :func:`forbidden_encodings` of any
       record's grid;
    2. no file's bytes contain any record's ``source_image`` — the picture
       name, which the public surface must not carry at all;
    3. every field name in every file is in :data:`DECLARED_FIELDS`
       (default-deny: an unrecognised field is a violation).

    Returns a list, never raises, and never short-circuits: every file is
    checked against every record, so one leak cannot mask another.
    """
    files = sorted(path for path in root.rglob("*.json"))
    violations: list[str] = []
    if not files:
        return ["no bundle files to scan: the scan would pass vacuously"]
    for path in files:
        blob = path.read_text(encoding="utf-8")
        for record in records:
            grid = record["grid"]
            for name, form in forbidden_encodings(grid).items():
                if form in blob:
                    violations.append(f"{path.name} carries the solution as {name}")
            picture = record.get("source_image")
            if picture and picture in blob:
                violations.append(f"{path.name} carries the picture name {picture!r}")
        undeclared = sorted(object_keys(json.loads(blob)) - DECLARED_FIELDS)
        if undeclared:
            violations.append(f"{path.name} carries undeclared field(s) {undeclared}")
    return violations


# --------------------------------------------------------------------------
# EC-049's mechanism — a statement log that refuses a write
# --------------------------------------------------------------------------

#: The leading SQL verbs a read-only path may issue. Everything else — every
#: verb in this list's complement, named or not — is a violation, which is
#: what makes the log default-deny rather than a list of three forbidden
#: words that a fourth spelling walks past (ADR-0039/R2).
READ_ONLY_VERBS = frozenset(
    {"SELECT", "BEGIN", "COMMIT", "ROLLBACK", "PRAGMA", "SAVEPOINT", "RELEASE", "WITH"}
)

_VERB = re.compile(r"^\s*(?:/\*.*?\*/\s*)?([A-Za-z]+)")


def forbidden_statements(statements) -> list[str]:
    """Those of ``statements`` whose leading verb is not read-only."""
    offenders = []
    for statement in statements:
        found = _VERB.match(statement)
        verb = found.group(1).upper() if found else "<unparsable>"
        if verb not in READ_ONLY_VERBS:
            offenders.append(statement.strip().splitlines()[0])
    return offenders


@contextmanager
def recorded_statements():
    """Record every SQL statement any engine executes while the block runs.

    Attached to SQLAlchemy's ``Engine`` *class*, the way ``conftest.py``
    attaches its foreign-key pragma, so it sees every engine the block builds
    without anything having to hand it one — including an engine built inside
    the code under test.
    """
    seen: list[str] = []

    def record(conn, cursor, statement, parameters, context, executemany):
        seen.append(statement)

    event.listen(Engine, "before_cursor_execute", record)
    try:
        yield seen
    finally:
        event.remove(Engine, "before_cursor_execute", record)


def table_rows(session_factory) -> dict[str, list]:
    """Every row of every table, keyed by table name.

    The table set comes from ``Base.metadata.sorted_tables`` — the schema
    itself — so this compares a table a later migration adds without being
    edited, and each table's rows are sorted so the comparison is of content
    and not of row order.
    """
    snapshot: dict[str, list] = {}
    with session_factory() as db:
        for table in Base.metadata.sorted_tables:
            rows = db.execute(text(f'SELECT * FROM "{table.name}"')).fetchall()  # noqa: S608
            snapshot[table.name] = sorted(repr(tuple(row)) for row in rows)
    return snapshot


# --------------------------------------------------------------------------
# Building stored data
# --------------------------------------------------------------------------


def rectangle(width, height, left, top, right, bottom):
    """A filled rectangle — uniquely solvable, so the storage boundary stores it."""
    return [
        [left <= x < right and top <= y < bottom for x in range(width)]
        for y in range(height)
    ]


def add_rectangle(store, index, *, tier="easy", name=None, picture=None, side=12):
    """One stored puzzle, through the real storage boundary (ADR-0032/R1)."""
    grid = rectangle(side, side, index, index, side - 2, side - 1 - index)
    found = clues.compute_clues(grid)
    puzzle_id = store.add_puzzle(
        grid=grid,
        clues_rows=[list(c) for c in found.rows],
        clues_cols=[list(c) for c in found.columns],
        width=side,
        height=side,
        theme="winter",
        difficulty_score=10,
        difficulty_tier=tier,
        quality_score=50,
        recognizability="medium",
        strategies_used=[],
        source_image=picture,
    )
    if name is not None:
        assert store.rename_puzzle(puzzle_id, name)
    return puzzle_id


def matching_plan(records):
    """The distribution plan ``records``' own selection satisfies.

    So a book can be taken out of draft through the **real** readiness gate
    (ADR-0035/R1, INV-007) rather than by writing a status onto a row. The
    counts are read off the selection, which is what makes it match.
    """
    from nonogram.admin.book_plan import BUCKETS, TIERS
    from nonogram.difficulty import Tier

    counts = {(bucket, tier): 0 for bucket in BUCKETS for tier in TIERS}
    for record in records:
        bucket = bucket_of(record["width"], record["height"])
        counts[(bucket, Tier(record["difficulty_tier"]))] += 1
    total = len(records)
    per_tier = {tier: sum(counts[(b, tier)] for b in BUCKETS) for tier in TIERS}
    assert total and all(
        per_tier[tier] * 100 % total == 0 for tier in TIERS
    ), "pick a selection whose tier shares are whole percents"
    return DistributionPlan(
        count=total,
        split=Split(*(per_tier[tier] * 100 // total for tier in TIERS)),
        cells=tuple(tuple(counts[(b, t)] for t in TIERS) for b in BUCKETS),
    )


def finalized_book(manager, store, puzzle_ids, title="Winter pictures"):
    """A book holding ``puzzle_ids``, taken out of draft through the gate."""
    book_id = manager.create_book(
        title=title,
        description="Pictures of winter.",
        theme="generic",
        target_audience="adults",
        size="8x10",
    )
    assert manager.add_puzzles_to_book(book_id, list(puzzle_ids))
    records = [store.get_puzzle(pid) for pid in puzzle_ids]
    assert manager.save_plan(book_id, matching_plan(records))
    assert manager.set_book_status(book_id, BookStatus.READY_FOR_PDF.value) is True
    assert manager.get_book(book_id).status in player_bundle.FINALIZED_STATUSES
    return book_id


@pytest.fixture
def shelf():
    """A real store and a real book manager, in the panel's in-memory mode."""
    store = PuzzleReviewService(session_factory=None)
    return store, BookManager(session_factory=None, puzzle_store=store)


# --------------------------------------------------------------------------
# The corpus AC-381 scans
# --------------------------------------------------------------------------


def corpus(store, manager):
    """A seeded corpus of grids, stored and carried by finalized books.

    Injected into the real store's and the real manager's own in-memory maps
    rather than passed through ``add_puzzle`` and the readiness gate: the
    criterion is about what the *exporter writes*, and a corpus of this size
    through the uniqueness solver would buy nothing for it while costing
    minutes. The read paths are the production ones either way —
    ``get_puzzles`` and ``get_all_books`` read these maps in this mode.

    The record's shape is not invented here; it is taken from a record the
    real storage boundary produced (``shape`` below), so a field the store
    starts returning is in the corpus too and
    ``test_the_corpus_records_have_the_shape_the_store_returns`` fails if that
    stops being true.
    """
    rng = random.Random(CORPUS_SEED)
    shape = store.get_puzzle(add_rectangle(store, 1, name="Shape", side=10))

    records = []
    for index in range(MIN_CORPUS_GRIDS + 4):
        width = rng.randint(MIN_SIZE, MAX_SIZE)
        height = rng.randint(MIN_SIZE, MAX_SIZE)
        density = rng.choice((0.1, 0.35, 0.5, 0.65, 0.9))
        grid = [
            [rng.random() < density for _ in range(width)] for _ in range(height)
        ]
        # Two degenerate shapes the encodings have to survive: an all-empty
        # grid (every line "(0,)") and an all-filled one.
        if index == 0:
            grid = [[False] * width for _ in range(height)]
        elif index == 1:
            grid = [[True] * width for _ in range(height)]
        puzzle_id = f"corpus_{index:06d}"
        record = dict.fromkeys(shape)
        record.update(
            id=puzzle_id,
            grid=grid,
            clues_rows=[list(c) for c in clues.compute_clues(grid).rows],
            clues_cols=[list(c) for c in clues.compute_clues(grid).columns],
            width=width,
            height=height,
            difficulty_tier=rng.choice(("easy", "medium", "hard", None)),
            puzzle_name=f"Picture number {index}",
            source_image=f"secret-picture-{index}{PICTURE_SUFFIX}",
            status="approved",
        )
        store.puzzles[puzzle_id] = record
        records.append(record)

    # A puzzle with no name at all, so the title fallback is exercised by the
    # scan rather than only by its own test.
    nameless = dict(records[2])
    nameless.update(id="corpus_nameless", puzzle_name=None)
    store.puzzles["corpus_nameless"] = nameless
    records.append(nameless)

    # Three books, so the book files and the index both have several members,
    # and one puzzle shared by two books.
    ids = [record["id"] for record in records]
    for number, member_ids in enumerate(
        (ids[: len(ids) // 2], ids[len(ids) // 2 :], ids[:3]), start=1
    ):
        book_id = f"corpus-book-{number}"
        manager.books[book_id] = Book(
            book_id=book_id,
            metadata=BookMetadata(
                title=f"Winter book {number}",
                description="",
                theme="generic",
                target_audience="adults",
                size="8x10",
                page_count=0,
            ),
            puzzle_ids=list(member_ids),
            status=BookStatus.PUBLISHED.value,
        )
    # And a draft book, whose puzzles must not reach the bundle.
    draft_id = add_rectangle(store, 2, name="Still a draft", side=10)
    manager.books["corpus-draft"] = Book(
        book_id="corpus-draft",
        metadata=BookMetadata(
            title="Draft book",
            description="",
            theme="generic",
            target_audience="adults",
            size="8x10",
            page_count=0,
        ),
        puzzle_ids=[draft_id],
        status=BookStatus.DRAFT.value,
    )
    return records, draft_id


# ==========================================================================
# AC-380
# ==========================================================================


def test_bundle_tree_and_clues_match_the_encoder(shelf, tmp_path):
    """AC-380 / ADR-0041/R1 — the tree, the keys, and the clues.

    The expected key and the expected clues are both computed by the
    independent second implementations at the top of this file, so what is
    compared is the recipe and the encoding, not one expression against
    itself. ``compute_clues`` is then cross-checked against the independent
    encoder as INV-001's own tests do, which is the only thing that makes
    "equals ``compute_clues`` of the stored grid" a meaningful equality here.
    """
    store, manager = shelf
    ids = [
        add_rectangle(store, index, name=name)
        for index, name in enumerate(("Snowflake", "Angel", "Reindeer", "Star"))
    ]
    book_id = finalized_book(manager, store, ids)
    root = tmp_path / "bundle"

    report = player_bundle.export_bundle(manager, store, root)

    expected_keys = {
        independent_key(store.get_puzzle(pid)["grid"]): pid for pid in ids
    }
    assert report.puzzle_count == len(ids)
    assert report.book_count == 1
    assert report.skipped == ()

    # The tree: index.json, one book file, one puzzle file per published key.
    assert sorted(path.relative_to(root).as_posix() for path in root.rglob("*.json")) == sorted(
        ["index.json"]
        + [f"book/{player_bundle.book_slug('Winter pictures', _book_order(store, manager, book_id))}.json"]
        + [f"puzzle/{key}.json" for key in expected_keys]
    )

    index = json.loads((root / "index.json").read_text(encoding="utf-8"))
    assert [entry["key"] for entry in index["puzzles"]] == sorted(expected_keys)

    # Each puzzle file's clues equal compute_clues of the stored grid, and the
    # independent encoder agrees with compute_clues on the same grid.
    for key, puzzle_id in expected_keys.items():
        grid = store.get_puzzle(puzzle_id)["grid"]
        payload = json.loads((root / "puzzle" / f"{key}.json").read_text(encoding="utf-8"))
        encoded = clues.compute_clues(grid)
        rows, columns = independent_clues(grid)
        assert (rows, columns) == (
            [list(c) for c in encoded.rows],
            [list(c) for c in encoded.columns],
        ), key
        assert payload["clues"] == {"rows": rows, "columns": columns}, key
        assert (payload["key"], payload["width"], payload["height"]) == (
            key,
            len(grid[0]),
            len(grid),
        )

    book_file = next((root / "book").glob("*.json"))
    book = json.loads(book_file.read_text(encoding="utf-8"))
    assert book["slug"] == book_file.stem
    assert book["title"] == "Winter pictures"
    assert book["puzzle_keys"] == _book_order(store, manager, book_id)


def _book_order(store, manager, book_id):
    """The book's puzzle keys in book order, by the independent recipe."""
    book = manager.get_book(book_id)
    return [independent_key(store.get_puzzle(pid)["grid"]) for pid in book.puzzle_ids]


# ==========================================================================
# AC-381 / EC-048
# ==========================================================================


def test_bundle_is_clean_of_answers(shelf, tmp_path):
    """AC-381 / EC-048 — no bundle file carries the answer, over a corpus.

    One assertion per category of violation, each one taken over the **whole**
    corpus and the whole tree, so a leak in one grid cannot hide a leak in
    another: :func:`answer_violations` collects and returns, and the assert is
    on the collection. The corpus size is asserted here, in the test, so it
    cannot shrink without this failing (CLAUDE.md's rule for property tests
    without ``hypothesis``).
    """
    store, manager = shelf
    records, draft_id = corpus(store, manager)
    root = tmp_path / "bundle"

    report = player_bundle.export_bundle(manager, store, root)

    assert len(records) >= MIN_CORPUS_GRIDS, "the corpus has shrunk"
    assert report.puzzle_count >= MIN_CORPUS_GRIDS - 1, report.puzzle_count
    assert len(list(root.rglob("*.json"))) >= MIN_CORPUS_GRIDS

    assert answer_violations(root, records) == []

    # The draft book's puzzle is not published, so neither its key nor its
    # grid is anywhere in the tree — the index is the library, not the store.
    draft_grid = store.get_puzzle(draft_id)["grid"]
    blob = "".join(
        path.read_text(encoding="utf-8") for path in sorted(root.rglob("*.json"))
    )
    assert independent_key(draft_grid) not in blob
    assert "Still a draft" not in blob

    # And the one thing a reader of the scan should not have to take on trust:
    # the records it scanned really did have a picture name to leak.
    assert all(record["source_image"].endswith(PICTURE_SUFFIX) for record in records)


@pytest.mark.parametrize(
    "shape",
    [
        "grid as a field",
        "grid bits in the title",
        "grid bits column-major",
        "grid as dots and hashes",
        "picture name as the title",
        "undeclared field",
        "the untruncated digest",
    ],
)
def test_the_answer_scan_catches_each_leak_shape(shelf, tmp_path, shape):
    """ADR-0039/R1's control for EC-048: the scan has a failing state.

    A real bundle, then one leak planted in one file, then the scan. Each
    shape is its own case, so a shape the scan is blind to is one red cell and
    not a silently unreached assert.
    """
    store, manager = shelf
    ids = [
        add_rectangle(store, index, name=f"P{index}", picture=f"secret-{index}.png")
        for index in range(3)
    ]
    finalized_book(manager, store, ids)
    root = tmp_path / "bundle"
    player_bundle.export_bundle(manager, store, root)
    records = [store.get_puzzle(pid) for pid in ids]
    assert answer_violations(root, records) == [], "the clean bundle must be clean"

    grid = records[0]["grid"]
    bits = "".join("1" if cell else "0" for row in grid for cell in row)
    column_bits = "".join(
        "1" if grid[y][x] else "0"
        for x in range(len(grid[0]))
        for y in range(len(grid))
    )
    key = independent_key(grid)
    target = root / "puzzle" / f"{key}.json"
    payload = json.loads(target.read_text(encoding="utf-8"))
    if shape == "grid as a field":
        payload["clues"]["rows"] = [[1 if c else 0 for c in row] for row in grid]
    elif shape == "grid bits in the title":
        payload["title"] = bits
    elif shape == "grid bits column-major":
        payload["title"] = column_bits
    elif shape == "grid as dots and hashes":
        payload["title"] = "".join("#" if c else "." for row in grid for c in row)
    elif shape == "picture name as the title":
        payload["title"] = records[0]["source_image"]
    elif shape == "undeclared field":
        payload["filled_cells"] = bits.count("1")
    elif shape == "the untruncated digest":
        payload["title"] = hashlib.sha256(
            f"{len(grid[0])}x{len(grid)}:{bits}".encode("utf-8")
        ).hexdigest()
    target.write_text(json.dumps(payload), encoding="utf-8")

    assert answer_violations(root, records) != [], shape


def test_an_undeclared_field_is_a_violation_and_not_a_pass(shelf, tmp_path):
    """ADR-0039/R2 — the field scan is default-DENY, measured.

    ``filled_cells`` above is the case that matters most and is the easiest to
    get wrong: it is not a grid encoding, so no amount of searching for cell
    strings finds it, and a scan built from a hand-written list of forbidden
    names would wave it through. What catches it is that it is not in
    :data:`DECLARED_FIELDS`, and this states that directly: the name is
    unknown to the schema, and being unknown is the whole violation.
    """
    store, manager = shelf
    ids = [add_rectangle(store, index, name=f"P{index}") for index in range(2)]
    finalized_book(manager, store, ids)
    root = tmp_path / "bundle"
    player_bundle.export_bundle(manager, store, root)

    assert "filled_cells" not in DECLARED_FIELDS
    target = next((root / "puzzle").glob("*.json"))
    payload = json.loads(target.read_text(encoding="utf-8"))
    payload["filled_cells"] = 0  # a value that leaks nothing; the FIELD is the leak
    target.write_text(json.dumps(payload), encoding="utf-8")

    # Asserted on the list rather than unpacked into one name: an unpacking
    # raises before the assert runs, and an error reports the arm as
    # NOT-REACHED — indistinguishable, in a per-assertion reading, from an arm
    # that never ran at all.
    undeclared = [
        found
        for found in answer_violations(root, [store.get_puzzle(pid) for pid in ids])
        if "undeclared" in found
    ]
    assert [found for found in undeclared if "filled_cells" in found] == undeclared != []


def test_the_declared_schema_is_the_field_set_the_criteria_name():
    """The completeness pin under :data:`DECLARED_FIELDS` (ADR-0039/R1, R2).

    The scan derives its field set from ``player_bundle``'s schema tuples,
    which is the right authority — it is code, enumerable at run time, and it
    cannot drift from the writers that read the same names. But it is also
    code a mutant can widen *together with* the writer, which would make the
    default-deny absorb the very field it exists to catch. So each tuple is
    held, by name, to the literal set AC-380 and FR-045 spell out.
    """
    assert {
        "index entry": set(player_bundle.INDEX_ENTRY_FIELDS),
        "index file": set(player_bundle.INDEX_FILE_FIELDS),
        "puzzle file": set(player_bundle.PUZZLE_FILE_FIELDS),
        "puzzle clues": set(player_bundle.PUZZLE_CLUES_FIELDS),
        "book file": set(player_bundle.BOOK_FILE_FIELDS),
    } == CRITERIA_FIELDS


def test_the_solution_derived_exemption_is_the_three_fields_the_adr_sanctions():
    """ADR-0039/R3 — the exemption is a claim, so it is held to its size.

    EC-048 forbids solution-derived data; ADR-0041/R1 and R5 *require* two
    kinds of it (the key, in three places, and the clues). Those are the whole
    exemption. A fourth name here is an ADR touch, and this is what makes
    adding one a red rather than a quiet widening.
    """
    assert player_bundle.SOLUTION_DERIVED_FIELDS == {"clues", "key", "puzzle_keys"}
    assert player_bundle.SOLUTION_DERIVED_FIELDS <= DECLARED_FIELDS


def test_the_title_never_falls_back_to_the_picture_name(shelf, tmp_path):
    """The admin panel's own fallback chain ends at ``source_image``; this one does not."""
    store, manager = shelf
    named = add_rectangle(store, 0, name="A named picture", picture="angel1.png")
    unnamed = add_rectangle(store, 1, name=None, picture="snowflake2.png")
    finalized_book(manager, store, [named, unnamed])
    root = tmp_path / "bundle"
    player_bundle.export_bundle(manager, store, root)

    titles = {
        entry["key"]: entry["title"]
        for entry in json.loads((root / "index.json").read_text(encoding="utf-8"))["puzzles"]
    }
    unnamed_key = independent_key(store.get_puzzle(unnamed)["grid"])
    assert titles[independent_key(store.get_puzzle(named)["grid"])] == "A named picture"
    assert titles[unnamed_key] == f"Puzzle {unnamed_key}"
    assert "snowflake2" not in json.dumps(titles)


# ==========================================================================
# AC-382 / EC-049
# ==========================================================================


def test_export_is_readonly_and_deterministic(tmp_path):
    """AC-382 / EC-049 — nothing written to the database, same bytes twice.

    Against a real database (SQLite, through ``sqlite_session_scope``) rather
    than the in-memory mode, because "no INSERT, UPDATE or DELETE" is only a
    statement about a path that issues statements. It does not skip: the
    Postgres-backed tests in this suite skip silently when no test database is
    configured, and a criterion that can be green by not running is no
    criterion.

    Three mechanisms, three different kinds of evidence:

    * the **statement log** (:func:`recorded_statements`), read through
      :func:`forbidden_statements`, which is default-deny on the leading verb;
    * a **row snapshot** of every table in ``Base.metadata``, before and
      after;
    * **byte comparison** across four runs — twice in this process and twice
      in subprocesses under *different* ``PYTHONHASHSEED`` values, which is
      the only way a set or dict iteration order leaking into the output can
      be seen at all.
    """
    scope = sqlite_session_scope(tmp_path, "player-bundle.db")
    store = PuzzleReviewService(session_factory=scope)
    manager = BookManager(session_factory=scope, puzzle_store=store)
    ids = [
        add_rectangle(store, index, name=name, picture=f"p{index}.png", side=10)
        for index, name in enumerate(("Snowflake", "Angel", "Reindeer", "Star"))
    ]
    finalized_book(manager, store, ids)

    before = table_rows(scope)
    with recorded_statements() as statements:
        first = player_bundle.export_bundle(manager, store, tmp_path / "one")
    after = table_rows(scope)

    assert first.puzzle_count == len(ids)
    assert statements, "the log recorded nothing: the export did not read the database"
    assert forbidden_statements(statements) == []
    assert after == before

    # A second run over the same data, then two more in subprocesses whose
    # hash randomisation differs from each other and from this process.
    player_bundle.export_bundle(manager, store, tmp_path / "two")
    for seed, name in (("0", "three"), ("123456789", "four")):
        _export_in_subprocess(tmp_path, tmp_path / name, seed)

    digests = {
        name: _tree_digest(tmp_path / name)
        for name in ("one", "two", "three", "four")
    }
    assert len(digests["one"]) >= 1 + 1 + len(ids)
    assert list(digests.values()) == [digests["one"]] * 4

    # Re-exporting over an existing tree is the owner's normal case, and must
    # land on the same bytes rather than merging into what was there.
    again = player_bundle.export_bundle(manager, store, tmp_path / "one")
    assert _tree_digest(tmp_path / "one") == digests["one"]
    assert again == first
    assert table_rows(scope) == before


def _tree_digest(root: Path) -> dict[str, str]:
    """Each file's path and the SHA-256 of its bytes — a tree compared by content."""
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _export_in_subprocess(db_dir: Path, out: Path, hash_seed: str) -> None:
    """Export the same stored data from a fresh process under ``hash_seed``.

    Hash randomisation is fixed for a process's lifetime, so a set iteration
    order reaching the output cannot be seen from inside one process however
    many times the export is run. This is what makes "deterministic" a
    measurement rather than a hope.
    """
    script = db_dir / f"export_{hash_seed}.py"
    script.write_text(
        "import sys\n"
        "from pathlib import Path\n"
        "from nonogram.admin import player_bundle\n"
        "from nonogram.admin.book_manager import BookManager\n"
        "from nonogram.admin.puzzle_review import PuzzleReviewService\n"
        "from tests.helpers.db import sqlite_session_scope\n"
        "scope = sqlite_session_scope(Path(sys.argv[1]), 'player-bundle.db')\n"
        "store = PuzzleReviewService(session_factory=scope)\n"
        "player_bundle.export_bundle(\n"
        "    BookManager(session_factory=scope, puzzle_store=store), store, sys.argv[2]\n"
        ")\n",
        encoding="utf-8",
    )
    environment = dict(os.environ)
    environment["PYTHONHASHSEED"] = hash_seed
    environment["PYTHONPATH"] = os.pathsep.join(
        [str(REPO_ROOT / "src"), str(REPO_ROOT)]
    )
    environment.pop("DATABASE_URL", None)
    finished = subprocess.run(
        [sys.executable, str(script), str(db_dir), str(out)],
        cwd=REPO_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert finished.returncode == 0, finished.stderr


def test_the_statement_log_catches_a_write(tmp_path):
    """ADR-0039/R1's control for EC-049's log: a real write, caught.

    Without it, ``forbidden_statements(...) == []`` above would hold just as
    well for a log that never sees a write, or for a verb set that admits
    everything.
    """
    scope = sqlite_session_scope(tmp_path, "writes.db")
    store = PuzzleReviewService(session_factory=scope)

    with recorded_statements() as statements:
        add_rectangle(store, 0, name="Written", side=10)

    offenders = forbidden_statements(statements)
    assert offenders, "a stored puzzle issued no statement the log calls a write"
    assert any(statement.upper().startswith("INSERT") for statement in offenders)


@pytest.mark.parametrize(
    "statement, forbidden",
    [
        ("SELECT 1", False),
        ("select * from puzzles", False),
        ("  BEGIN (implicit)", False),
        ("PRAGMA foreign_keys=ON", False),
        ("INSERT INTO puzzles VALUES (1)", True),
        ("update books set title='x'", True),
        ("DELETE FROM books", True),
        ("TRUNCATE TABLE puzzles", True),
        ("MERGE INTO puzzles", True),
        ("REPLACE INTO puzzles VALUES (1)", True),
        ("UPSERT INTO puzzles VALUES (1)", True),
        ("DROP TABLE puzzles", True),
        ("CREATE TABLE t (a int)", True),
        ("GRANT ALL ON puzzles TO x", True),
        ("¿qué?", True),
    ],
)
def test_the_statement_verdict_is_default_deny(statement, forbidden):
    """The log's verdict, per verb — including verbs EC-049 never names.

    EC-049 says "no INSERT/UPDATE/DELETE". A guard that looks for exactly
    those three words is default-ALLOW underneath, and ``TRUNCATE``,
    ``MERGE``, ``UPSERT``, ``DROP`` and ``GRANT`` are each a write it would
    wave through. The verdict is therefore taken on the *complement* of
    :data:`READ_ONLY_VERBS`, and a statement whose verb cannot be parsed at
    all is forbidden rather than skipped.
    """
    assert bool(forbidden_statements([statement])) is forbidden


def test_the_export_writes_no_float_and_refuses_one(tmp_path, shelf):
    """Determinism, the part that is pinned by absence.

    Float formatting is one of the levers determinism has to pin, and the
    bundle pins it the strongest way available: there are no floats in it. The
    first half of this measures that over a written tree; the second half
    measures that the writer *refuses* one, so the first half is a property of
    the code and not of today's data.
    """
    store, manager = shelf
    ids = [add_rectangle(store, index, name=f"P{index}") for index in range(2)]
    finalized_book(manager, store, ids)
    root = tmp_path / "bundle"
    player_bundle.export_bundle(manager, store, root)

    def floats(payload, where="payload"):
        if isinstance(payload, float):
            return [where]
        if isinstance(payload, dict):
            return [f for k, v in payload.items() for f in floats(v, f"{where}.{k}")]
        if isinstance(payload, list):
            return [f for i, v in enumerate(payload) for f in floats(v, f"{where}[{i}]")]
        return []

    assert [
        found
        for path in sorted(root.rglob("*.json"))
        for found in floats(json.loads(path.read_text(encoding="utf-8")), path.name)
    ] == []
    # The message, not just the exception type: without the float branch a
    # float still raises, through the "not a bundle value" arm whose message
    # *contains the word float* (it prints the type name). ``match="float"``
    # therefore passed with the branch deleted — measured, as M9 of this
    # card's kill matrix, which is why this matches the branch's own sentence.
    with pytest.raises(TypeError, match="refusing to write a float"):
        player_bundle._dump(tmp_path / "nope.json", {"width": 20.0})
    with pytest.raises(TypeError, match="not a bundle value"):
        player_bundle._dump(tmp_path / "nope.json", {"when": object()})


# ==========================================================================
# ADR-0041/R1 and the slug — the recipe's own cross-checks
# ==========================================================================


@pytest.mark.parametrize(
    "lever, reading",
    [
        ("key order", "sorted"),
        ("non-ascii", "escaped"),
        ("line ending", "lf only"),
        ("trailing newline", "present"),
    ],
)
def test_the_serialisation_levers_are_pinned(tmp_path, lever, reading):
    """Determinism's other half: what :func:`player_bundle._dump` fixes.

    The byte comparison in AC-382 cannot see these, because a process that
    builds its payloads the same way twice writes the same bytes twice however
    free the serialiser is. Each lever therefore has its own case here, fed a
    payload built in the *wrong* order or holding a character the default
    would pass through — which is the failing state each pin needs.
    """
    path = tmp_path / "pinned.json"
    player_bundle._dump(path, {"width": 1, "title": "Ёлка", "height": 2, "clues": {}})
    blob = path.read_bytes()

    if lever == "key order":
        assert re.findall(rb'"(\w+)":', blob) == [b"clues", b"height", b"title", b"width"]
    elif lever == "non-ascii":
        assert b"\\u0401" in blob and "Ёлка".encode("utf-8") not in blob
    elif lever == "line ending":
        assert b"\r" not in blob
    else:
        assert blob.endswith(b"\n")


def test_a_puzzle_that_leaves_every_finalized_book_leaves_the_bundle(shelf, tmp_path):
    """The tree is a function of the input, which is what makes a diff mean something.

    Re-exporting after a removal has to *remove* the file, not leave it beside
    the new ones: a bundle that only ever grows would answer "did it change?"
    with half the truth, and the deploy-time diff ADR-0041 wants would be
    wrong in the one direction nobody checks.
    """
    store, manager = shelf
    ids = [add_rectangle(store, index, name=f"P{index}") for index in range(4)]
    book_id = finalized_book(manager, store, ids)
    root = tmp_path / "bundle"
    player_bundle.export_bundle(manager, store, root)
    gone = independent_key(store.get_puzzle(ids[-1])["grid"])
    assert (root / "puzzle" / f"{gone}.json").is_file()

    # Removing a member returns the book to draft (INV-012), so it goes back
    # out through the readiness gate on its new plan before it is exported.
    manager.books[book_id].puzzle_ids.remove(ids[-1])
    assert manager.save_plan(
        book_id, matching_plan([store.get_puzzle(pid) for pid in ids[:-1]])
    )
    assert manager.set_book_status(book_id, BookStatus.READY_FOR_PDF.value) is True
    report = player_bundle.export_bundle(manager, store, root)

    assert report.puzzle_count == len(ids) - 1
    assert not (root / "puzzle" / f"{gone}.json").exists()
    assert sorted(path.name for path in (root / "puzzle").glob("*.json")) == sorted(
        f"{independent_key(store.get_puzzle(pid)['grid'])}.json" for pid in ids[:-1]
    )


def test_the_key_is_the_adrs_worked_example():
    """ADR-0041/R1's own example: a 2x2 grid with the top-left cell filled.

    The ADR writes the hashed material out — ``"2x2:1000"`` — so the material
    is asserted directly, not only the digest it produces. A recipe whose
    prefix, separator, cell encoding or cell order drifted would still agree
    with an expected digest computed the same wrong way; it cannot agree with
    this string.
    """
    grid = [[True, False], [False, False]]
    expected = hashlib.sha256(b"2x2:1000").hexdigest()[:10]

    # The ADR's example is SQUARE, so it cannot tell "{width}x{height}" from
    # "{height}x{width}" — measured: swapping the two in the production recipe
    # left this test green (M11 of this card's kill matrix) until this second,
    # non-square material was asserted beside it. 3 wide, 1 tall.
    assert player_bundle.puzzle_key([[True, False, False]]) == hashlib.sha256(
        b"3x1:100"
    ).hexdigest()[:10]
    assert player_bundle.puzzle_key(grid) == expected
    assert player_bundle.puzzle_key(grid) == independent_key(grid)
    assert len(player_bundle.puzzle_key(grid)) == player_bundle.KEY_LENGTH == 10
    assert player_bundle.puzzle_key(grid) == player_bundle.puzzle_key(grid).lower()
    assert all(c in "0123456789abcdef" for c in player_bundle.puzzle_key(grid))


@pytest.mark.parametrize(
    "drift, grid, other",
    [
        ("the same cells under two extents", [[True, False, False]], [[True], [False], [False]]),
        ("a cell swapped", [[True, False], [False, False]], [[False, True], [False, False]]),
        ("a transposed grid", [[True, True], [False, False]], [[True, False], [True, False]]),
    ],
)
def test_the_key_separates_the_recipes_parts(drift, grid, other):
    """Each part of R1's recipe is load-bearing, measured as a disagreement.

    The ADR calls the prefix, the separator, the cell encoding, the algorithm,
    the truncation and the case parts of the recipe. These three pairs are the
    ones a reimplementation actually gets wrong: the extent being in the
    material at all, cell order, and row-major versus column-major.

    **What this test cannot see, stated rather than implied:** it compares two
    keys for inequality, so it is blind to the extent being formatted
    ``{height}x{width}`` — both keys move together and stay unequal. That
    spelling is caught by the *material* assertions in
    :func:`test_the_key_is_the_adrs_worked_example`, which is where the
    recipe's text is pinned.
    """
    assert player_bundle.puzzle_key(grid) != player_bundle.puzzle_key(other), drift


def test_the_stores_internal_fingerprint_is_not_the_public_key():
    """A trap this module's docstring names, held to a measurement.

    ``PuzzleReviewService._grid_fingerprint`` hashes a string of the same
    *shape* as R1's — extent, colon, bits — but with the extent reversed and
    with no truncation. For a non-square grid it is therefore a different
    value for the same cells, and reusing it as the public key would be a
    breaking change to every printed book that looked like a refactor.
    """
    grid = [[True, False, False], [False, True, False]]
    fingerprint = PuzzleReviewService._grid_fingerprint(grid)

    assert player_bundle.puzzle_key(grid) != fingerprint[:10]
    assert len(fingerprint) == 64


@pytest.mark.parametrize(
    "grid, why",
    [
        ([], "no rows"),
        ([[]], "no columns"),
        ([[True, False], [True]], "ragged"),
    ],
)
def test_the_key_refuses_a_grid_row_major_order_has_no_meaning_for(grid, why):
    with pytest.raises(ValueError):
        player_bundle.puzzle_key(grid)


def test_the_slug_is_content_addressed_and_not_the_books_row_id(shelf, tmp_path):
    """The slug is a function of the title and the ordered keys, nothing else.

    ADR-0041 specifies no slug recipe (see ``player_bundle``'s docstring), and
    this is what the recipe it does use claims: recomputable from the printed
    book — its cover title and its puzzles — and independent of the database
    row, which is the property ADR-0041 rejected a stored slug for.
    """
    store, manager = shelf
    ids = [add_rectangle(store, index, name=f"P{index}") for index in range(3)]
    book_id = finalized_book(manager, store, ids, title="Winter pictures")
    keys = _book_order(store, manager, book_id)

    slug = player_bundle.book_slug("Winter pictures", keys)
    assert slug == hashlib.sha256(
        ("book:Winter pictures:" + "".join(keys)).encode("utf-8")
    ).hexdigest()[:10]
    assert book_id not in slug
    assert slug != player_bundle.book_slug("Winter pictures", list(reversed(keys)))
    assert slug != player_bundle.book_slug("Winter picture", keys)

    root = tmp_path / "bundle"
    player_bundle.export_bundle(manager, store, root)
    assert (root / "book" / f"{slug}.json").is_file()


def test_identical_grids_are_one_public_puzzle(shelf, tmp_path):
    """ADR-0041's "identical grids share a key by design", and its consequence.

    Two stored rows with the same cells are one key, so they are one file —
    and their differing metadata has to be reconciled by something that is a
    function of the *values* rather than of the read order, or EC-049's
    determinism would hold only for stores that happen to read them the same
    way twice.
    """
    store, manager = shelf
    first = add_rectangle(store, 0, name="Zebra", tier="hard")
    twin = dict(store.get_puzzle(first))
    twin.update(id="twin", puzzle_name="Aardvark", difficulty_tier="easy")
    store.puzzles["twin"] = twin
    finalized_book(manager, store, [first])
    manager.books[next(iter(manager.books))].puzzle_ids.append("twin")
    root = tmp_path / "bundle"

    report = player_bundle.export_bundle(manager, store, root)

    assert report.puzzle_count == 1
    assert len(list((root / "puzzle").glob("*.json"))) == 1
    entry = json.loads((root / "index.json").read_text(encoding="utf-8"))["puzzles"][0]
    assert (entry["title"], entry["tier"]) == ("Aardvark", "easy")
    book = json.loads(next((root / "book").glob("*.json")).read_text(encoding="utf-8"))
    assert book["puzzle_keys"] == [entry["key"]] * 2


def test_a_member_with_an_unreadable_grid_is_named_not_silently_dropped(shelf, tmp_path):
    store, manager = shelf
    good = add_rectangle(store, 0, name="Fine")
    broken = dict(store.get_puzzle(good))
    broken.update(id="broken", grid=[[True, False], [True]])
    store.puzzles["broken"] = broken
    finalized_book(manager, store, [good])
    manager.books[next(iter(manager.books))].puzzle_ids.append("broken")

    report = player_bundle.export_bundle(manager, store, tmp_path / "bundle")

    assert report.puzzle_count == 1
    assert [pid for pid, _ in report.skipped] == ["broken"]
    assert "ragged" in dict(report.skipped)["broken"]


# ==========================================================================
# What counts as published, and where the output lands
# ==========================================================================


def test_the_finalized_statuses_are_every_status_but_draft():
    """Derived from the enum, and that is what is asserted (ADR-0039/R2)."""
    assert player_bundle.FINALIZED_STATUSES == {
        status.value for status in BookStatus
    } - {BookStatus.DRAFT.value}
    assert BookStatus.DRAFT.value not in player_bundle.FINALIZED_STATUSES
    assert len(player_bundle.FINALIZED_STATUSES) == len(BookStatus) - 1


def test_the_default_output_directory_is_a_gitignored_build_directory():
    """Trap 10 — the default must land somewhere no export can enter the index.

    Asked of git itself rather than of ``.gitignore``'s text, because the
    question is whether git ignores the path, not whether a pattern that looks
    like it does appears in a file.
    """
    default = player_bundle.default_output_dir()

    assert default.parent == REPO_ROOT / "build"
    assert not default.is_relative_to(REPO_ROOT / "src")
    ignored = subprocess.run(
        ["git", "check-ignore", "-q", str(default)], cwd=REPO_ROOT, timeout=60
    )
    assert ignored.returncode == 0, f"git does not ignore {default}"


def test_the_corpus_records_have_the_shape_the_store_returns(shelf):
    """The corpus is not a hand-written record shape (its docstring's claim)."""
    store, manager = shelf
    records, _ = corpus(store, manager)
    shape = set(store.get_puzzle(add_rectangle(store, 3, name="Shape", side=10)))

    assert {frozenset(record) for record in records} == {frozenset(shape)}


# ==========================================================================
# The trigger — ADR-0041/R5's "explicit admin-panel action"
# ==========================================================================


@pytest.fixture
def panel(monkeypatch, tmp_path):
    """The admin panel in its in-memory mode, with its bundle directory set."""
    import nonogram.admin.book_manager as book_manager_module
    import nonogram.admin.image_manager as image_manager_module

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TESTING", "true")
    from nonogram.admin.app import create_app

    image_manager_module._image_manager = None
    monkeypatch.setattr(
        book_manager_module,
        "_book_manager",
        book_manager_module.BookManager(session_factory=None),
    )
    app = create_app()
    app.config["TESTING"] = True
    app.config["BOOK_COVER_DIR"] = str(tmp_path / "covers")
    app.config["PLAYER_BUNDLE_DIR"] = str(tmp_path / "bundle")
    with app.app_context():
        yield app
    image_manager_module._image_manager = None


def test_the_book_page_offers_the_action_and_it_writes_the_bundle(panel, tmp_path):
    """The owner's action, end to end: the page's own form, posted."""
    store, manager = panel.puzzle_review_service, panel.book_manager
    ids = [add_rectangle(store, index, name=f"P{index}") for index in range(3)]
    book_id = finalized_book(manager, store, ids)
    client = panel.test_client()

    page = client.get(f"/book/{book_id}").get_data(as_text=True)
    assert f'action="/book/{book_id}/export-player-bundle"' in page

    posted = client.post(f"/book/{book_id}/export-player-bundle")

    assert posted.status_code == 302
    root = tmp_path / "bundle"
    assert (root / "index.json").is_file()
    assert len(list((root / "puzzle").glob("*.json"))) == len(ids)


@pytest.mark.parametrize(
    "path, data",
    [
        ("/book/{book_id}/status", {"status": "ready_for_pdf"}),
        ("/book/{book_id}/add-puzzles", {"puzzle_ids": ""}),
    ],
)
def test_no_other_book_action_writes_the_bundle(panel, tmp_path, path, data):
    """ADR-0041/R5 — "exported by an explicit action", so nothing else exports.

    A claim about a side effect needs the side effect's absence measured on
    the routes that would plausibly have it, not asserted of the export route
    alone.
    """
    store, manager = panel.puzzle_review_service, panel.book_manager
    ids = [add_rectangle(store, index, name=f"P{index}") for index in range(3)]
    book_id = finalized_book(manager, store, ids)
    client = panel.test_client()

    client.post(path.format(book_id=book_id), data=data)

    assert not (tmp_path / "bundle").exists()
