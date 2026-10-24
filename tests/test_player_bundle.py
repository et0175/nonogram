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
* :func:`provenance_violations` is AC-381's scan, and EC-048's guarantee. It
  is a **whitelist on provenance**, not a denylist of leak shapes: every
  scalar in every written file must be accounted for by a named good source —
  the extent, a stored tier, a stored title or its neutral fallback, a
  published key, ADR-0041/R5's clues, ADR-0041/R7's slug — and a value no
  source claims is a violation. It is default-deny at the tree, the object,
  the field and the value; ``player_bundle.SOLUTION_DERIVED_FIELDS`` is its
  routing table, so EC-048's declared exemption decides which check a field
  gets. ``test_the_answer_scan_catches_each_leak_shape`` plants each of
  :data:`LEAK_SHAPES` **through the exporter's own writer** and watches it
  fire; the leak that shipped green past the denylist this replaced is one of
  them.
* :func:`answer_violations` is the belt beside it: the old denylist, kept
  because it is free and reads bytes, claiming nothing. Its two measured
  limits are written into :func:`forbidden_encodings`' own docstring, and
  ``test_the_belt_runs_on_the_bytes_the_exporter_writes`` both proves it can
  fail on bytes the exporter really writes and pins the hole it cannot close.
* :func:`object_keys` and :data:`DECLARED_FIELDS` serve the belt only.
  ``test_the_declared_schema_is_the_field_set_the_criteria_name`` holds
  ``player_bundle``'s schema tuples to the literal field list AC-380 and
  FR-045 spell out, because those tuples are the whitelist's per-file
  authority and are code a mutant could widen alongside the writer.
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
is built with stdlib :class:`random.Random` from a fixed seed, and the test
asserts its size against :data:`MIN_CORPUS_GRIDS` — a floor the builder does
not read, which is the part that stops the corpus shrinking silently and the
part that was missing (cycle 1, F-2).
"""

from __future__ import annotations

import base64
import hashlib
import itertools
import json
import math
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

#: How many grids :func:`corpus` **builds**. Read by the builder and by
#: nothing else.
CORPUS_GRIDS = 52

#: The floor AC-381 refuses to go below — a literal, and deliberately *not*
#: the constant the corpus is built from.
#:
#: Until CARD-282's first fix round these were one constant: the corpus looped
#: ``range(MIN_CORPUS_GRIDS + 4)`` and was then asserted to be at least
#: ``MIN_CORPUS_GRIDS`` long, so the assertion could not fail and the corpus
#: was silently shrinkable to 9 grids with the suite green (cycle 1, F-2) —
#: which is the one thing EC-048's registry statement names explicitly, "with
#: the minimum corpus size asserted in the test". A bound that moves with the
#: thing it bounds asserts nothing. Lowering this number is not a remedy for
#: anything; :func:`test_the_corpus_floor_is_a_bound_the_corpus_does_not_set`
#: measures both directions of the separation.
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
#: It is the **union** of the five per-file tuples, which is all the belt can
#: use: it walks every object in every file without knowing which file it is
#: in. The per-file equality — the check a leak reusing another file's
#: declared name has to get past — is in :func:`provenance_violations`.
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

    **This is the belt, not the guarantee** — read
    :func:`provenance_violations` for the guarantee. A denylist of encodings
    cannot be complete, because the set of encodings of a grid is not
    enumerable, and this one was measured incomplete: 7 of 7 recoverable
    encodings planted in the declared ``title`` field survived it (CARD-282
    cycle 1, F-1). Two further limits, stated because a reader would otherwise
    assume them away:

    * every form below is **compact text**, while
      :func:`player_bundle._dump` writes with ``indent=2``, so no *structured*
      leak can match one of these strings in a real bundle file. The
      ``"\\\\n"`` in the separators is the two-character escape, not a
      newline — measured: 0 of the forms contain a newline character. The
      reach that remains is a leak inside a single JSON **string** value,
      which is where it does catch things, and
      :func:`test_the_belt_runs_on_the_bytes_the_exporter_writes` plants one
      through ``_dump`` to prove that much can fail;
    * it is kept because it is free and because it reads *bytes*, so it is
      blind to nothing the JSON parser normalises. It is believed to add
      nothing the whitelist misses, and nothing rests on it.

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


# --------------------------------------------------------------------------
# EC-048's guarantee: the provenance whitelist
# --------------------------------------------------------------------------
#
# This is the inversion CARD-282's cycle 1 asked for, and the reason it had
# to be an inversion rather than a bigger denylist.
#
# What was here before was two denylists: a set of encodings a solution could
# leave in a file, and a set of field *names* a file may carry. Both were
# derived rather than hand-written, and both were still default-ALLOW
# underneath, which was measured three ways:
#
#   * the field set was the flat UNION of the five per-file schemas, and
#     nothing held a written file's object to its OWN schema — so one edit on
#     the production path put the whole 144-cell solution grid into
#     ``index.json`` under the already-declared name ``clues``, with every
#     test green;
#   * ``forbidden_encodings`` enumerates encodings, and the set of encodings
#     of a grid is not enumerable: 7 of 7 recoverable encodings planted in the
#     declared ``title`` field (base64 and base85 of the packed bits, a
#     diagonal traversal, run-length, per-row hex, row-reversed, '-'-joined)
#     were missed;
#   * every form it derives is compact text while :func:`player_bundle._dump`
#     writes ``indent=2``, so the one control that proved it could fail was
#     planting bytes the exporter cannot produce.
#
# So the polarity is inverted here. Instead of asking "is this one of the
# shapes we thought of?", the scan asks of **every value in every file**: "is
# this value one that a named good source produces?" — and an answer of "no
# source claims it" is a violation. That is default-DENY by construction: a
# leak has to BE a width, a stored tier, a stored title, a published key, the
# ADR's clues or the ADR's slug to pass.
#
# THE BOUNDARY THAT FOLLOWS FROM THAT, stated because the sentence here used
# to deny it (cycle 2, F-3): "and none of those is a solution cell except
# through the two projections ADR-0041 requires by name" was FALSE. A **stored
# title** is in the pass-list and is free text the owner types. Cycle 2
# reproduced it end to end through the real storage boundary and the real
# exporter: `rename_puzzle(pid, base64(packed bits))` stores a name that this
# scan accounts for as "a stored title", `answer_violations` is empty too, and
# the published `index.json` title base64-decodes back to the exact 144-cell
# bit string. Every solution cell recovered from the public bundle, suite
# green. `difficulty_tier` is the same shape, narrower.
#
# That is defensible for a whitelist on PROVENANCE — the value did come from a
# named source, and a provenance guard is not a content classifier — but it is
# a REACHABLE PATH past ADR-0041/R2's "or data from which any solution cell is
# recoverable", so it is a declared bound here and not a gap nobody measured.
# The owner can leak the answers by naming a puzzle badly. Whether the
# exporter should refuse or neutralise such a title is an R2 scope question
# and CARD-283's; it is not something this scan can decide.
#
# Three properties to keep if this is ever rewritten:
#
#   1. it reads the files back with :mod:`json` and whitelists the **parsed
#      values**, so what the exporter's serialiser does to the bytes cannot
#      open a hole in it (that was the indent gap, closed by construction
#      rather than by remembering it);
#   2. every object is held to **its own** schema tuple, never to the union;
#   3. ``player_bundle.SOLUTION_DERIVED_FIELDS`` is the *routing table*, so
#      the declared exemption decides which of the two checks a field gets and
#      is load-bearing in both directions.


#: The ADR's own recipe for each field EC-048 exempts. Consulted **only** for
#: a field ``player_bundle.SOLUTION_DERIVED_FIELDS`` names; a name in the
#: exemption with no recipe here has nothing checking its value, which the
#: scan reports as a violation rather than passing over.
_ADR_RECIPES: dict = {}

#: The named source for every declared field the exemption does *not* cover.
#: A value a source does not produce is a violation, and a declared field with
#: no entry here and no recipe above is a violation too.
_PLAIN_SOURCES: dict = {}

#: Declared fields whose own leaves are accounted for by the recursion into
#: them rather than by their rule (the rule checks the container's shape, the
#: recursion checks each member). ``rows`` and ``columns`` are not routed at
#: all: they are the ``clues`` object's own fields and are checked with it.
_CONTAINER_FIELDS = frozenset({"puzzles"})


def leaf_paths(payload, where: str = "") -> dict[str, object]:
    """Every scalar in ``payload``, keyed by its JSON path.

    The unit the whitelist accounts for. A container is not a leaf — it is
    accounted for by its members — so "every value is accounted for" means
    every string, number, boolean and null that a bundle file actually
    carries.
    """
    found: dict[str, object] = {}
    if isinstance(payload, dict):
        for name, value in payload.items():
            found |= leaf_paths(value, f"{where}.{name}")
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            found |= leaf_paths(value, f"{where}[{index}]")
    else:
        found[where or "<root>"] = payload
    return found


def independent_slug(puzzle_keys) -> str:
    """ADR-0041/R7's recipe, written out rather than called.

    The slug the whitelist accepts is this one, so a book file's ``slug`` is
    compared with the rule's text and not with the function under test.
    """
    material = bytearray(b"book:")
    for key in puzzle_keys:
        material += key.encode("utf-8")
    return hashlib.sha256(bytes(material)).hexdigest()[:10]


def bundle_sources(records, books) -> dict:
    """Every value the bundle is allowed to carry, by where it may come from.

    Built from the *stored* rows and books alone — never from the written
    tree — so it is an independent statement of what a clean bundle holds.
    Only puzzles a **finalized** book carries are published, which is why a
    draft book's key and title have no source here and are caught by the same
    default-deny as any other unaccounted value.
    """
    by_id = {record["id"]: record for record in records}
    grids: dict[str, list] = {}
    rows_by_key: dict[str, list] = {}
    book_sources: dict[str, dict] = {}

    for book in books:
        if book.status not in player_bundle.FINALIZED_STATUSES:
            continue
        keys = []
        for puzzle_id in book.puzzle_ids:
            record = by_id.get(puzzle_id)
            if record is None:
                continue
            grid = [[bool(cell) for cell in row] for row in record["grid"]]
            if not grid or not grid[0] or any(len(r) != len(grid[0]) for r in grid):
                continue  # the exporter's named skip; no key, so nothing published
            key = independent_key(grid)
            keys.append(key)
            grids[key] = grid
            rows_by_key.setdefault(key, []).append(record)
        slug = independent_slug(keys)
        settled = book_sources.setdefault(slug, {"keys": keys, "titles": set()})
        stored = (getattr(getattr(book, "metadata", None), "title", None) or "").strip()
        settled["titles"].add(stored or "Untitled book")

    titles: dict[str, set] = {}
    tiers: dict[str, set] = {}
    clue_sets: dict[str, dict] = {}
    for key, found in rows_by_key.items():
        allowed = set()
        for record in found:
            name = record.get("puzzle_name")
            if isinstance(name, str) and name.strip():
                allowed.add(name.strip())
            else:
                # The exporter's neutral fallback, allowed only because a row
                # with this key really has no stored name — never as a free
                # pass for any title shaped like it.
                allowed.add(f"Puzzle {key}")
        titles[key] = allowed
        tiers[key] = {record.get("difficulty_tier") for record in found}
        encoded_rows, encoded_columns = independent_clues(grids[key])
        clue_sets[key] = {"rows": encoded_rows, "columns": encoded_columns}

    return {
        "grids": grids,
        "extent": {key: (len(grid[0]), len(grid)) for key, grid in grids.items()},
        "titles": titles,
        "tiers": tiers,
        "clues": clue_sets,
        "books": book_sources,
    }


def _recipe_key(value, ctx):
    """ADR-0041/R1 — the key is the published grid's key and nothing else."""
    if not isinstance(value, str):
        return f"is {type(value).__name__}, not a key"
    if value not in ctx["sources"]["grids"]:
        return f"{value!r} is not R1's key of any published grid"
    if ctx["key"] is not None and value != ctx["key"]:
        return f"{value!r} is not the key this entry is filed under ({ctx['key']!r})"
    return None


def _recipe_clues(value, ctx):
    """ADR-0041/R5 — the clues are the one encoder's output for that grid."""
    expected = ctx["sources"]["clues"].get(ctx["key"])
    if expected is None:
        return "no published grid for this key, so no sanctioned clues either"
    if not isinstance(value, dict):
        return f"is {type(value).__name__}, not a clues object"
    if set(value) != set(player_bundle.PUZZLE_CLUES_FIELDS):
        return (
            f"clues fields {sorted(value)} are not this object's own schema "
            f"{sorted(player_bundle.PUZZLE_CLUES_FIELDS)}"
        )
    if value != expected:
        return "is not the independent run-length encoding of the stored grid"
    return None


def _recipe_puzzle_keys(value, ctx):
    """ADR-0041/R1 + R7 — the book's members' keys, in book order."""
    book = ctx["sources"]["books"].get(ctx["slug"])
    if book is None:
        return f"no finalized book hashes to the slug {ctx['slug']!r}"
    if value != book["keys"]:
        return "is not this book's members' keys in book order"
    return None


def _source_puzzles(value, ctx):
    """The index's entry list: one entry per published key, sorted by key."""
    if not isinstance(value, list):
        return f"is {type(value).__name__}, not a list of entries"
    found = [entry.get("key") if isinstance(entry, dict) else entry for entry in value]
    expected = sorted(ctx["sources"]["grids"])
    if found != expected:
        return f"lists {found!r}, not the published keys in order ({expected!r})"
    return None


def _source_width(value, ctx):
    extent = ctx["sources"]["extent"].get(ctx["key"])
    if extent is None:
        return "no published grid for this key"
    return None if value == extent[0] else f"{value!r} is not the grid's width {extent[0]}"


def _source_height(value, ctx):
    extent = ctx["sources"]["extent"].get(ctx["key"])
    if extent is None:
        return "no published grid for this key"
    return None if value == extent[1] else f"{value!r} is not the grid's height {extent[1]}"


def _source_tier(value, ctx):
    allowed = ctx["sources"]["tiers"].get(ctx["key"])
    if allowed is None:
        return "no published grid for this key"
    if not any(value == tier for tier in allowed):
        return f"{value!r} is no difficulty_tier stored on a row with this key"
    return None


def _source_title(value, ctx):
    # ``any(value == allowed)`` rather than ``value in allowed`` throughout:
    # the sets are sets, and a planted dict or list is unhashable, so ``in``
    # would raise ``TypeError`` out of a scan whose docstring says it never
    # raises. A scan that crashes on a hostile shape is not a scan that
    # rejected it.
    if ctx["kind"] == "book file":
        book = ctx["sources"]["books"].get(ctx["slug"])
        if book is None:
            return f"no finalized book hashes to the slug {ctx['slug']!r}"
        if not any(value == title for title in book["titles"]):
            return f"{value!r} is no stored title of a book with this slug"
        return None
    allowed = ctx["sources"]["titles"].get(ctx["key"])
    if allowed is None:
        return "no published grid for this key"
    if not any(value == title for title in allowed):
        return (
            f"{value!r} is neither a stored puzzle_name of a row with this key "
            "nor its neutral fallback"
        )
    return None


def _source_slug(value, ctx):
    if not isinstance(value, str):
        return f"is {type(value).__name__}, not a slug"
    if value != ctx["slug"]:
        return f"{value!r} is not the file's own name {ctx['slug']!r}"
    if value != independent_slug(ctx["payload"].get("puzzle_keys") or []):
        return "is not R7's book_slug of this file's own puzzle_keys"
    if value not in ctx["sources"]["books"]:
        return "names no finalized book"
    return None


_ADR_RECIPES.update(
    key=_recipe_key, clues=_recipe_clues, puzzle_keys=_recipe_puzzle_keys
)
_PLAIN_SOURCES.update(
    puzzles=_source_puzzles,
    width=_source_width,
    height=_source_height,
    tier=_source_tier,
    title=_source_title,
    slug=_source_slug,
)


def _object_fields_are_its_own(violations, where, payload, declared) -> bool:
    """Hold one written object to **its own** schema tuple, not to the union.

    The union was the first of F-1's two causes: ``clues``, ``slug`` and
    ``puzzles`` are all declared *somewhere*, so a value under any of those
    names passed in any file.
    """
    if not isinstance(payload, dict):
        violations.append(f"{where}: is {type(payload).__name__}, not a JSON object")
        return False
    if set(payload) != set(declared):
        violations.append(
            f"{where}: field set {sorted(payload)} is not this file's own schema "
            f"{sorted(declared)}"
        )
        return False
    return True


def _check_object(violations, accounted, where, payload, declared, ctx) -> None:
    """One written object: its own field set, then each value's provenance."""
    if not _object_fields_are_its_own(violations, where, payload, declared):
        return
    inner = dict(ctx, payload=payload)
    for field in sorted(payload):
        at = f"{where}.{field}"
        exempt = field in player_bundle.SOLUTION_DERIVED_FIELDS
        rule = (_ADR_RECIPES if exempt else _PLAIN_SOURCES).get(field)
        if rule is None:
            violations.append(
                f"{at}: {field!r} is "
                + (
                    "exempt by SOLUTION_DERIVED_FIELDS but no ADR recipe checks it"
                    if exempt
                    else "declared but has no named non-solution source"
                )
            )
            continue
        complaint = rule(payload[field], inner)
        if complaint:
            violations.append(f"{at}: {complaint}")
        elif field not in _CONTAINER_FIELDS:
            accounted |= set(leaf_paths(payload[field], at))


def provenance_violations(root: Path, records, books) -> list[str]:
    """Every value in the bundle under ``root`` that no good source accounts for.

    EC-048's guarantee, and AC-381's primary scan. Default-DENY at four
    levels, each one a level the denylist it replaced was default-ALLOW at:

    * **the tree** — a file whose path is not ``index.json``, a published
      key's ``puzzle/<key>.json`` or a finalized book's ``book/<slug>.json``
      is a violation, and so is a missing one;
    * **the object** — every object's field set must equal **its own** schema
      tuple from ``player_bundle``, never the union of the five;
    * **the field** — a declared name is routed by
      ``player_bundle.SOLUTION_DERIVED_FIELDS``: exempt names to the ADR's own
      recipe for them, every other name to a source with no solution cell in
      it. A name with neither is a violation;
    * **the value** — every scalar leaf must have been *accounted for* by a
      rule that accepted it. The leaves are enumerated from the parsed file
      and the accounted ones subtracted, so **a value in a place no branch
      visits** is a violation rather than an oversight. (It does *not* catch a
      value a rule accepted without looking inside it — see the note on the
      fourth level below, which used to claim otherwise.)

    The fourth level is a **backstop with no reachable case of its own
    today**, and says so rather than taking credit: every rule above accounts
    for exactly what it accepts, so deleting the subtraction changes no
    reading in this file — measured, and recorded as an unkilled mutant (L4)
    rather than as a mutant nobody tried.

    **It does NOT backstop a future under-checking rule, and the sentence here
    used to say it did.** Cycle 2 reproduced the counterexample:
    :func:`_check_object` marks a field accounted for with
    ``accounted |= set(leaf_paths(payload[field], at))`` — over **every** leaf
    of **every** accepted field — so the subtraction can never see a rule that
    accepted a value without looking inside it. With the ``title`` rule
    replaced by ``lambda value, ctx: None`` and a structured
    ``{"bits": "<144 cells>"}`` title written through :func:`_dump`,
    ``provenance_violations`` returns ``[]``. The retired claim was *"a rule
    that later accepts a value with more structure than it checks becomes a
    violation instead of a hole"*; it is false, and leaving it would have told
    the next card to add a rule that it was covered when it is not.

    What the level **does** do is catch a value in a place **no branch visits
    at all** — a field outside every schema tuple, or a shape the recursion
    does not reach. Adding a rule therefore still requires its own control;
    the subtraction is not one.

    Reads the files back as JSON, so the serialiser's own choices — indent,
    key order, escaping — cannot open a hole in the scan the way they did in
    the byte-level one.

    Returns a list and never short-circuits, and no value or shape a bundle
    file can carry makes it raise — hostile shapes included, which is what the
    "a nested object as the title" and "a list as the key" leak cases read
    (``value in a_set`` raises on an unhashable value, and a scan that crashes
    on a shape has not rejected it). An unparsable file would still raise, and
    that is deliberate: there is nothing to scan and nothing to report.
    """
    sources = bundle_sources(records, books)
    violations: list[str] = []
    files = sorted(root.rglob("*.json"))
    if not files:
        return ["no bundle files to scan: the scan would pass vacuously"]

    found_tree = {path.relative_to(root).as_posix() for path in files}
    expected_tree = (
        {"index.json"}
        | {f"puzzle/{key}.json" for key in sources["grids"]}
        | {f"book/{slug}.json" for slug in sources["books"]}
    )
    if found_tree != expected_tree:
        violations.append(
            "the tree is not the published set: unaccounted "
            f"{sorted(found_tree - expected_tree)}, missing "
            f"{sorted(expected_tree - found_tree)}"
        )

    for path in files:
        relative = path.relative_to(root).as_posix()
        payload = json.loads(path.read_text(encoding="utf-8"))
        # Prefixed with the file's own path, so a violation names the file and
        # the path inside it in one string — and so the accounted paths the
        # rules below produce are the same strings as these.
        found_leaves = leaf_paths(payload, relative)
        leaves = set(found_leaves)
        accounted: set[str] = set()
        parent = path.parent.name

        if relative == "index.json":
            ctx = {"sources": sources, "kind": "index file", "key": None, "slug": None}
            _check_object(
                violations,
                accounted,
                relative,
                payload,
                player_bundle.INDEX_FILE_FIELDS,
                ctx,
            )
            for index, entry in enumerate(
                payload.get("puzzles", []) if isinstance(payload, dict) else []
            ):
                _check_object(
                    violations,
                    accounted,
                    f"{relative}.puzzles[{index}]",
                    entry,
                    player_bundle.INDEX_ENTRY_FIELDS,
                    {
                        "sources": sources,
                        "kind": "index entry",
                        "key": entry.get("key") if isinstance(entry, dict) else None,
                        "slug": None,
                    },
                )
        elif parent == "puzzle":
            _check_object(
                violations,
                accounted,
                relative,
                payload,
                player_bundle.PUZZLE_FILE_FIELDS,
                {
                    "sources": sources,
                    "kind": "puzzle file",
                    "key": path.stem,
                    "slug": None,
                },
            )
        elif parent == "book":
            _check_object(
                violations,
                accounted,
                relative,
                payload,
                player_bundle.BOOK_FILE_FIELDS,
                {
                    "sources": sources,
                    "kind": "book file",
                    "key": None,
                    "slug": path.stem,
                },
            )
        else:
            violations.append(f"{relative}: no bundle file belongs at this path")
            continue

        unaccounted = sorted(leaves - accounted)
        if unaccounted:
            violations.append(
                f"{relative}: no source accounts for "
                + ", ".join(f"{at} = {found_leaves[at]!r}" for at in unaccounted[:4])
                + (f" (+{len(unaccounted) - 4} more)" if len(unaccounted) > 4 else "")
            )
    return violations


def answer_violations(root: Path, records) -> list[str]:
    """The belt beside :func:`provenance_violations`: a denylist over the bytes.

    Kept because it costs nothing and reads the bytes rather than the parsed
    values, but **EC-048 does not rest on it** — see
    :func:`forbidden_encodings` for what it provably misses and
    :func:`provenance_violations` for the default-deny guarantee that
    replaced it as AC-381's scan.

    ``records`` is every stored puzzle record the bundle was written from. The
    three checks, in the order they would catch a leak:

    1. no file's bytes contain any of :func:`forbidden_encodings` of any
       record's grid;
    2. no file's bytes contain any record's ``source_image`` — the picture
       name, which the public surface must not carry at all;
    3. every field name in every file is in :data:`DECLARED_FIELDS` — which
       is the **union** of the five per-file schemas, so this catches only a
       name no file may carry at all. Holding an object to *its own* schema is
       :func:`provenance_violations`' job, and the difference between the two
       is F-1's first cause.

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


def two_bars(side, top, bottom, a0, a1, b0, b1):
    """Two separated vertical bars — **more than one run on a line**.

    Every :func:`rectangle` grid has at most ONE run per line, which made
    AC-380's cross-check against :func:`independent_clues` vacuous: a run
    *order* defect is invisible when there is nothing to order. Cycle 2's
    Step 8f measured it — ``clues.py:84``'s ``tuple(runs)`` mutated to
    ``tuple(reversed(runs))`` left
    ``test_bundle_tree_and_clues_match_the_encoder`` **green** while its
    docstring claimed the independent encoder "is the only thing that makes
    'equals ``compute_clues`` of the stored grid' a meaningful equality here".

    Two bars give 2 runs on every filled row, so the order is observable.
    Verified **uniquely solvable before it was added** (the solver reports
    ``is_unique=True``, ``solution_count=1`` for the three parameter sets
    tried), because the storage boundary refuses anything else (ADR-0032/R1)
    and a fixture that cannot be stored is not a fixture.
    """
    return [
        [((a0 <= x < a1) or (b0 <= x < b1)) and top <= y < bottom for x in range(side)]
        for y in range(side)
    ]


def lines_visible_under_run_reversal(grid):
    """How many of ``grid``'s lines have a clue that is not its own reverse.

    **The property that makes a run-ORDER defect observable**, and not the
    proxy it is tempting to use. "More than one run per line" is *not* enough:
    the orchestrator's first attempt at cycle 2's F-1 used two bars of equal
    width, whose clue is ``(3, 3)`` — two runs, and a palindrome, so
    ``tuple(reversed(runs))`` is the same value and the mutant stayed green
    exactly as it had with the rectangles. Measured: 0 lines differing.

    Bars of *unequal* width give ``(2, 4)`` and 8 differing lines. A guard on
    the fixture has to assert the property the mutant exercises rather than
    something that usually comes with it.
    """
    found = clues.compute_clues(grid)
    return sum(
        1
        for line in list(found.rows) + list(found.columns)
        if tuple(line) != tuple(reversed(line))
    )


def add_two_bars(store, index, *, tier="easy", name=None, picture=None, side=12):
    """One stored multi-run puzzle, through the real storage boundary."""
    grid = two_bars(side, 2, side - 2, 1 + (index % 2), 3, 6, 10)
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


def new_shelf():
    """A real store and a real book manager, in the panel's in-memory mode.

    A plain function as well as a fixture, because the corpus-floor control
    needs two independent shelves inside one test and a fixture can only hand
    it one.
    """
    store = PuzzleReviewService(session_factory=None)
    return store, BookManager(session_factory=None, puzzle_store=store)


@pytest.fixture
def shelf():
    return new_shelf()


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
    for index in range(CORPUS_GRIDS):
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

    **That sentence was false for this fixture until cycle 2 measured it, and
    the fifth puzzle is the correction.** Every :func:`rectangle` grid carries
    at most ONE run per line, so ``tuple(runs)`` and ``tuple(reversed(runs))``
    are the same value and a run-order defect in ``compute_clues`` was
    invisible here: Step 8f mutated ``clues.py:84`` that way and this test
    stayed **green** while ``test_bundle_is_clean_of_answers`` caught it. A
    cross-check against an independent encoder is only a cross-check over
    inputs where the two could disagree. :func:`add_two_bars` supplies one,
    and ``max_runs_per_line`` below holds the fixture to still containing it —
    so the vacuity cannot come back by someone editing the grid list.
    """
    store, manager = shelf
    ids = [
        add_rectangle(store, index, name=name)
        for index, name in enumerate(("Snowflake", "Angel", "Reindeer", "Star"))
    ]
    ids.append(add_two_bars(store, 0, name="Lantern"))

    # The fixture must contain an input on which the two encoders COULD
    # disagree, or the clue equality below is an identity (cycle 2, F-1).
    # Asserted as "a clue that is not its own reverse", which is the property
    # the run-order mutant exercises — NOT "more than one run", which is a
    # proxy that two equal-width bars satisfy while staying invisible.
    assert any(
        lines_visible_under_run_reversal(store.get_puzzle(pid)["grid"]) for pid in ids
    ), (
        "no fixture grid has a clue that differs from its own reversal, so "
        "comparing compute_clues against independent_clues cannot see a "
        "run-order defect — add a grid with unequal run lengths on a line "
        "rather than deleting this assertion"
    )

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
        + [f"book/{player_bundle.book_slug(_book_order(store, manager, book_id))}.json"]
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


def corpus_floor_violations(records, report, root) -> list[str]:
    """Why ``records`` is too small a corpus for AC-381 to mean anything.

    The floor, as a function, so it has a failing state a control can
    construct — and compared against :data:`MIN_CORPUS_GRIDS`, which the
    corpus builder does not read (cycle 1, F-2).
    """
    found = len(list(root.rglob("*.json")))
    failures = []
    if len(records) < MIN_CORPUS_GRIDS:
        failures.append(
            f"the corpus is {len(records)} records, below the floor of {MIN_CORPUS_GRIDS}"
        )
    if report.puzzle_count < MIN_CORPUS_GRIDS - 1:
        failures.append(
            f"only {report.puzzle_count} published puzzles, below {MIN_CORPUS_GRIDS - 1}"
        )
    if found < MIN_CORPUS_GRIDS:
        failures.append(f"only {found} bundle files, below {MIN_CORPUS_GRIDS}")
    return failures


def test_bundle_is_clean_of_answers(shelf, tmp_path):
    """AC-381 / EC-048 — no bundle file carries the answer, over a corpus.

    One assertion per category of violation, each one taken over the **whole**
    corpus and the whole tree, so a leak in one grid cannot hide a leak in
    another: each scan collects and returns, and the assert is on the
    collection.

    The guarantee is :func:`provenance_violations` — every value in every file
    accounted for by a named non-solution source, or by the ADR's own recipe
    for one of the three fields EC-048 exempts. :func:`answer_violations` runs
    beside it as a belt and proves nothing on its own.

    The corpus size is asserted here, in the test, so it cannot shrink without
    this failing (CLAUDE.md's rule for property tests without ``hypothesis``)
    — through :func:`corpus_floor_violations`, against a floor the corpus
    builder does not read.
    """
    store, manager = shelf
    records, draft_id = corpus(store, manager)
    root = tmp_path / "bundle"

    report = player_bundle.export_bundle(manager, store, root)

    assert corpus_floor_violations(records, report, root) == []
    assert provenance_violations(root, records, manager.get_all_books()) == []
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


#: Every leak the whitelist is claimed to catch, as the material to plant.
#: Each one is a *fully recoverable* encoding of every solution cell unless
#: its name says otherwise, and the seven marked (cycle 1) are the seven the
#: denylist this replaced was measured to miss.
LEAK_SHAPES = (
    "grid as a field",
    "the whole grid in index.json under clues",  # F-1's own single-edit mutant
    "another file's declared names in a puzzle file",
    "grid bits in the title",
    "grid bits column-major",
    "grid as dots and hashes",
    "picture name as the title",
    "undeclared field",
    "the untruncated digest",
    "base64 of the packed bits in the title",  # cycle 1
    "base85 of the packed bits in the title",  # cycle 1
    "a diagonal traversal in the title",  # cycle 1
    "run-length of the cells in the title",  # cycle 1
    "per-row hex in the title",  # cycle 1
    "each row reversed in the title",  # cycle 1
    "the bits joined by dashes in the title",  # cycle 1
    "the untruncated digest as the key",
    "the bits in a book's puzzle_keys",
    "the bits in the tier",
    "a puzzle file under a key nothing published",
    "a width that is not the grid's extent",
    "an index entry with its tier dropped",
    "a published puzzle's file removed",
    "a nested object as the title",
    "a list as the key",
)


def _encodings_of(grid, record) -> dict[str, object]:
    """The material each leak shape plants, derived from ``grid`` at run time."""
    height, width = len(grid), len(grid[0])
    bits = "".join("1" if cell else "0" for row in grid for cell in row)
    packed = int(bits, 2).to_bytes((len(bits) + 7) // 8, "big")
    runs = []
    for value, group in itertools.groupby(bits):
        runs.append(f"{len(list(group))}{'F' if value == '1' else 'E'}")
    return {
        "bits": bits,
        "column bits": "".join(
            "1" if grid[y][x] else "0" for x in range(width) for y in range(height)
        ),
        "dots and hashes": "".join("#" if c else "." for row in grid for c in row),
        "picture": record.get("source_image"),
        "digest": hashlib.sha256(f"{width}x{height}:{bits}".encode("utf-8")).hexdigest(),
        "base64 packed": base64.b64encode(packed).decode("ascii"),
        "base85 packed": base64.b85encode(packed).decode("ascii"),
        "diagonal": "".join(
            "1" if grid[y][x] else "0"
            for total in range(width + height - 1)
            for y in range(height)
            for x in range(width)
            if x + y == total
        ),
        "run-length": ",".join(runs),
        "row hex": ":".join(
            f"{int(''.join('1' if c else '0' for c in row), 2):x}" for row in grid
        ),
        "rows reversed": "".join(
            "1" if cell else "0" for row in grid for cell in reversed(row)
        ),
        "dash joined": "-".join(bits),
        "grid as ints": [[1 if c else 0 for c in row] for row in grid],
    }


def _plant(shape, root, grid, record, key):
    """Plant ``shape`` into the written bundle **through the exporter's writer**.

    ``player_bundle._dump``, not ``json.dumps``: the control this replaces
    rewrote its file compactly, which is a byte shape the exporter cannot
    produce, so the one reading that proved the scan could fail was taken on
    bytes nothing writes (cycle 1, F-1, second cause). Planting through
    ``_dump`` means a shape that passes here passes against the real thing.
    """
    material = _encodings_of(grid, record)
    puzzle_path = root / "puzzle" / f"{key}.json"
    index_path = root / "index.json"
    book_path = sorted((root / "book").glob("*.json"))[0]
    puzzle = json.loads(puzzle_path.read_text(encoding="utf-8"))
    titles = {
        "grid bits in the title": material["bits"],
        "grid bits column-major": material["column bits"],
        "grid as dots and hashes": material["dots and hashes"],
        "picture name as the title": material["picture"],
        "the untruncated digest": material["digest"],
        "base64 of the packed bits in the title": material["base64 packed"],
        "base85 of the packed bits in the title": material["base85 packed"],
        "a diagonal traversal in the title": material["diagonal"],
        "run-length of the cells in the title": material["run-length"],
        "per-row hex in the title": material["row hex"],
        "each row reversed in the title": material["rows reversed"],
        "the bits joined by dashes in the title": material["dash joined"],
    }

    if shape in titles:
        puzzle["title"] = titles[shape]
    elif shape == "grid as a field":
        puzzle["clues"]["rows"] = material["grid as ints"]
    elif shape == "another file's declared names in a puzzle file":
        puzzle.update(slug="a" * 10, puzzles=[])
    elif shape == "undeclared field":
        puzzle["filled_cells"] = material["bits"].count("1")
    elif shape == "the untruncated digest as the key":
        puzzle["key"] = material["digest"]
    elif shape == "the bits in the tier":
        puzzle["tier"] = material["bits"]
    elif shape == "a width that is not the grid's extent":
        puzzle["width"] = len(grid[0]) + 1
    elif shape == "a nested object as the title":
        # Hostile shapes as well as hostile values: the scan's docstring says
        # it never raises, and ``value in a_set`` raises on an unhashable one.
        puzzle["title"] = {"bits": material["bits"]}
    elif shape == "a list as the key":
        puzzle["key"] = [material["bits"]]
    elif shape == "an index entry with its tier dropped":
        # Not a leak: an omission. It is the one shape only the per-file field
        # *equality* can see, which is why it is here — a file that does not
        # carry what its own schema says it carries is as much a provenance
        # failure as one that carries something else.
        index = json.loads(index_path.read_text(encoding="utf-8"))
        for entry in index["puzzles"]:
            entry.pop("tier")
        player_bundle._dump(index_path, index)
        return
    elif shape == "the whole grid in index.json under clues":
        index = json.loads(index_path.read_text(encoding="utf-8"))
        for entry in index["puzzles"]:
            entry["clues"] = {"rows": material["grid as ints"], "columns": []}
        player_bundle._dump(index_path, index)
        return
    elif shape == "the bits in a book's puzzle_keys":
        book = json.loads(book_path.read_text(encoding="utf-8"))
        book["puzzle_keys"] = [material["bits"]]
        player_bundle._dump(book_path, book)
        return
    elif shape == "a puzzle file under a key nothing published":
        player_bundle._dump(root / "puzzle" / "0123456789.json", puzzle)
        return
    elif shape == "a published puzzle's file removed":
        # The other direction of the tree check, and the only shape only it can
        # see: the index still advertises the key, every value left in the tree
        # still has its source, and the file the player would fetch is gone.
        # Measured: without the tree check this is the one case that survives
        # (mutant L8), which is why it is a case rather than a comment.
        puzzle_path.unlink()
        return
    else:  # pragma: no cover - a shape named in LEAK_SHAPES with no planting
        raise AssertionError(f"no planting for {shape!r}")
    player_bundle._dump(puzzle_path, puzzle)


@pytest.mark.parametrize("shape", LEAK_SHAPES)
def test_the_answer_scan_catches_each_leak_shape(shelf, tmp_path, shape):
    """ADR-0039/R1's control for EC-048: the scan has a failing state.

    A real bundle, then one leak planted in one file through the exporter's
    own writer, then the scan. Each shape is its own case, so a shape the scan
    is blind to is one red cell and not a silently unreached assert — and the
    reading is taken on :func:`provenance_violations` alone, not on the union
    of it and the belt, because a surviving hole in the guarantee must not be
    masked by the thing that guarantees nothing.
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
    books = manager.get_all_books()
    assert provenance_violations(root, records, books) == [], "the clean bundle is clean"

    grid = records[0]["grid"]
    _plant(shape, root, grid, records[0], independent_key(grid))

    assert provenance_violations(root, records, books) != [], shape


@pytest.mark.parametrize(
    "legitimate",
    [
        "a name that looks like an encoding but is the stored one",
        "no stored name at all, so the neutral fallback",
        "no stored tier at all",
        "a non-ascii name with surrounding whitespace",
        "two books with the same puzzles and different titles",
    ],
)
def test_a_legitimate_value_stays_green(shelf, tmp_path, legitimate):
    """The whitelist's edge: what it must NOT reject (ADR-0039/R1's other arm).

    A default-deny guard is only worth having if its accept side is right: a
    whitelist that reds on a nameless puzzle, a null tier or a stored name
    full of digits would be turned off within a week, and "the bundle is
    clean" would then be a statement about a disabled scan. Each of these is a
    value the exporter really writes, and each is one case so a wrongly
    rejected one is a single red cell.
    """
    store, manager = shelf
    name, tier = f"Picture {legitimate}", "easy"
    if legitimate == "a name that looks like an encoding but is the stored one":
        name = "1010101010101010101010"
    elif legitimate == "no stored name at all, so the neutral fallback":
        name = None
    elif legitimate == "no stored tier at all":
        tier = None
    elif legitimate == "a non-ascii name with surrounding whitespace":
        name = "  Ёлка под снегом  "

    first = add_rectangle(store, 0, name=name, tier=tier or "easy")
    second = add_rectangle(store, 1, name="Another", tier="easy")
    book_id = finalized_book(manager, store, [first, second], title="Winter pictures")
    if tier is None:
        # After the readiness gate, which reads the tier as a Tier: an
        # unmeasured tier is ADR-0032/R2's None, and the bundle writes it as
        # null, so the whitelist has to accept it (and does not accept a
        # *different* tier -- that is the leak-shape control's "bits in the
        # tier" case).
        store.puzzles[first]["difficulty_tier"] = None
    if legitimate == "two books with the same puzzles and different titles":
        finalized_book(manager, store, [first, second], title="Aardvark edition")
    root = tmp_path / "bundle"

    player_bundle.export_bundle(manager, store, root)

    records = [store.get_puzzle(first), store.get_puzzle(second)]
    assert provenance_violations(root, records, manager.get_all_books()) == [], (
        legitimate,
        manager.get_book(book_id).metadata.title,
    )


def test_the_belt_runs_on_the_bytes_the_exporter_writes(shelf, tmp_path):
    """ADR-0039/R1 for the belt — and the hole it provably cannot close.

    Both readings are taken on bytes written by :func:`player_bundle._dump`,
    because the control this replaces planted its leak with compact
    ``json.dumps`` while the exporter writes ``indent=2``: the scan was shown
    catching a shape no bundle file can have (cycle 1, F-1).

    The second reading asserts the belt **misses** a structured leak, which is
    not a weakness being tolerated but a measured fact being pinned: the
    guarantee is the whitelist, and the same bundle is caught by it in the
    same breath. If a later change makes the belt catch this too, this goes
    red — restate it then, rather than quietly letting the belt look like the
    thing EC-048 rests on.
    """
    store, manager = shelf
    ids = [
        add_rectangle(store, index, name=f"P{index}", picture=f"secret-{index}.png")
        for index in range(2)
    ]
    finalized_book(manager, store, ids)
    root = tmp_path / "bundle"
    player_bundle.export_bundle(manager, store, root)
    records = [store.get_puzzle(pid) for pid in ids]
    books = manager.get_all_books()
    grid = records[0]["grid"]
    key = independent_key(grid)
    assert answer_violations(root, records) == [], "the clean bundle is clean"

    # (a) a leak inside one JSON string value — the belt's real reach.
    _plant("grid bits in the title", root, grid, records[0], key)
    assert answer_violations(root, records) != [], "the belt caught nothing at all"

    # (b) the same cells, structured. Indented by the writer, so no compact
    # form the belt derives can match them.
    player_bundle.export_bundle(manager, store, root)
    _plant("grid as a field", root, grid, records[0], key)
    assert answer_violations(root, records) == [], (
        "the belt now catches a structured leak: restate this control, and do "
        "not take it as a reason to lean on the belt"
    )
    assert provenance_violations(root, records, books) != []


def test_the_corpus_floor_is_a_bound_the_corpus_does_not_set(monkeypatch, tmp_path):
    """F-2's remedy, measured in both directions.

    The corpus size and the floor it is refused below are two different
    things, and until this round they were one constant: the corpus looped
    ``range(MIN_CORPUS_GRIDS + 4)`` and was then asserted ``>=
    MIN_CORPUS_GRIDS``, so lowering it to 4 left a 9-grid corpus with 55 tests
    green. Separated, each direction has a reading:

    * **lowering the floor must not shrink the corpus** — the builder does not
      read :data:`MIN_CORPUS_GRIDS`, so the corpus is the same size with the
      floor at 4;
    * **shrinking the corpus must red** — with :data:`CORPUS_GRIDS` at 4 the
      floor check returns violations instead of passing.

    Both are needed: the first alone would hold for a floor nothing compares
    against, and the second alone would hold for the tautology that was there.
    """
    module = sys.modules[__name__]

    store, manager = new_shelf()
    monkeypatch.setattr(module, "MIN_CORPUS_GRIDS", 4)
    lowered, _ = corpus(store, manager)
    monkeypatch.undo()
    assert len(lowered) == CORPUS_GRIDS + 1
    assert len(lowered) >= MIN_CORPUS_GRIDS > 4

    store, manager = new_shelf()
    monkeypatch.setattr(module, "CORPUS_GRIDS", 4)
    small, _ = corpus(store, manager)
    root = tmp_path / "small"
    report = player_bundle.export_bundle(manager, store, root)
    monkeypatch.undo()
    assert len(small) == 5
    assert corpus_floor_violations(small, report, root) != []


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
    player_bundle._dump(target, payload)  # the exporter's writer, not json.dumps

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

    This is the exemption's *size*. What it must not absorb is
    :func:`test_each_sanctioned_source_absorbs_only_the_adrs_own_recipe`, and
    the premises it rests on are
    :func:`test_the_exemptions_two_premises_are_measured_not_cited` — the
    three together are ADR-0039/R3's reading, and until this round only this
    one existed, which made the exemption a control for its own spelling
    (cycle 1, F-3).
    """
    assert player_bundle.SOLUTION_DERIVED_FIELDS == {"clues", "key", "puzzle_keys"}
    assert player_bundle.SOLUTION_DERIVED_FIELDS <= DECLARED_FIELDS


def test_every_declared_field_has_one_source_and_the_exemption_picks_which():
    """The whitelist's routing table is total, and the exemption is the switch.

    The property that makes :data:`player_bundle.SOLUTION_DERIVED_FIELDS`
    load-bearing rather than decorative: it *partitions* the declared fields
    into the ones checked against the ADR's own recipe and the ones checked
    against a source with no solution cell in it. Removing a name from it
    leaves that field with no accepted source at all; adding one leaves it
    with no recipe. Either way the scan reports a violation on every file
    carrying the field — which is what "an exemption carries a control"
    means, as against stating its own spelling.
    """
    assert set(_ADR_RECIPES) == set(player_bundle.SOLUTION_DERIVED_FIELDS)
    assert set(_ADR_RECIPES).isdisjoint(_PLAIN_SOURCES)
    # ``rows`` and ``columns`` are the clues object's own fields, checked with
    # it by ``_recipe_clues`` and never routed on their own — stated here so
    # the partition covers every declared name and a new one has nowhere to
    # hide.
    assert set(_ADR_RECIPES) | set(_PLAIN_SOURCES) | {"rows", "columns"} == DECLARED_FIELDS
    assert set(player_bundle.PUZZLE_CLUES_FIELDS) == {"rows", "columns"}
    assert _CONTAINER_FIELDS < set(_PLAIN_SOURCES)


#: The three sanctioned projections of a solution grid, as the whitelist sees
#: them: the two names EC-048 exempts outright plus the slug, which R7 derives
#: from the keys. Each needs a reading of what it must NOT absorb.
SANCTIONED_SOURCES = ("clues", "key", "puzzle_keys", "slug")


@pytest.mark.parametrize("field", SANCTIONED_SOURCES)
def test_each_sanctioned_source_absorbs_only_the_adrs_own_recipe(shelf, tmp_path, field):
    """ADR-0039/R3 — what each exemption must NOT absorb, one cell each.

    An exemption that let *any* value through in its field would be a hole the
    size of the field: ``clues`` would carry the grid, ``key`` the untruncated
    digest, ``puzzle_keys`` anything at all. So each exempt field is checked
    against the ADR's own recipe for it and against nothing weaker, and each
    case here plants solution material in one of them, through the exporter's
    writer, and requires the scan to say so.
    """
    assert set(SANCTIONED_SOURCES) - {"slug"} == set(
        player_bundle.SOLUTION_DERIVED_FIELDS
    ), "the exemption changed size without a case here"

    store, manager = shelf
    ids = [add_rectangle(store, index, name=f"P{index}") for index in range(2)]
    finalized_book(manager, store, ids)
    root = tmp_path / "bundle"
    player_bundle.export_bundle(manager, store, root)
    records = [store.get_puzzle(pid) for pid in ids]
    books = manager.get_all_books()
    grid = records[0]["grid"]
    key = independent_key(grid)
    material = _encodings_of(grid, records[0])
    assert provenance_violations(root, records, books) == [], "the clean bundle is clean"

    if field == "clues":
        target = root / "puzzle" / f"{key}.json"
        payload = json.loads(target.read_text(encoding="utf-8"))
        payload["clues"]["rows"] = material["grid as ints"]
    elif field == "key":
        target = root / "puzzle" / f"{key}.json"
        payload = json.loads(target.read_text(encoding="utf-8"))
        payload["key"] = material["digest"]
    else:
        target = sorted((root / "book").glob("*.json"))[0]
        payload = json.loads(target.read_text(encoding="utf-8"))
        if field == "puzzle_keys":
            payload["puzzle_keys"] = [material["bits"]]
        else:
            payload["slug"] = material["digest"][:10]
    player_bundle._dump(target, payload)

    violations = provenance_violations(root, records, books)
    assert [found for found in violations if field in found] != [], violations


@pytest.mark.parametrize(
    "exemption, complaint",
    [
        (frozenset({"clues", "key", "puzzle_keys", "title"}), "no ADR recipe"),
        (frozenset({"key", "puzzle_keys"}), "no named non-solution source"),
        (frozenset(), "no named non-solution source"),
    ],
)
def test_a_wrong_exemption_is_loud_in_the_scan(shelf, tmp_path, monkeypatch, exemption, complaint):
    """ADR-0039/R3's own words: caught with the exemption changed, missed with
    the right one in place — and in **both** directions.

    This is what makes :data:`player_bundle.SOLUTION_DERIVED_FIELDS` a
    mechanism rather than a spelling. As shipped in 3f6b57a0 the only reading
    of it was a test comparing the constant with its own literal, so emptying
    it reded one tautological cell and changed nothing about what was caught
    or written (cycle 1, F-3).

    Now the scan *routes* on it: a name in it is checked against the ADR's own
    recipe and a name outside it against a source with no solution cell in it.
    So **widening** the exemption leaves a field with no recipe, and
    **narrowing** it leaves a field with no source — each loud on every file
    carrying that field, which is the difference between an exemption that is
    declared and one that is absorbed.
    """
    store, manager = shelf
    ids = [add_rectangle(store, index, name=f"P{index}") for index in range(2)]
    finalized_book(manager, store, ids)
    root = tmp_path / "bundle"
    player_bundle.export_bundle(manager, store, root)
    records = [store.get_puzzle(pid) for pid in ids]
    books = manager.get_all_books()
    assert provenance_violations(root, records, books) == [], "the clean bundle is clean"

    monkeypatch.setattr(player_bundle, "SOLUTION_DERIVED_FIELDS", exemption)
    violations = provenance_violations(root, records, books)

    assert [found for found in violations if complaint in found] != [], violations


def test_the_exemptions_two_premises_are_measured_not_cited(shelf):
    """ADR-0039/R3 — the exemption's premises, recomputed rather than quoted.

    EC-048 allows the clues and the key because of two claims, and a claim is
    only as good as its reading:

    * **the clues are injective on the published set — by CONSTRUCTION, not
      by the sample this test used to take.** A published puzzle has been
      proved uniquely solvable at the storage boundary (ADR-0032/R1), and
      unique solvability *is* "these clues determine this grid", so two
      distinct published grids cannot share an extent and a clue pair. That is
      why publishing the clues is the point rather than a leak (ADR-0041's
      Context: the player's solved check *is* clue satisfaction).

      **Cycle 2's F-4 corrected this bullet twice over.** The property is
      **false in general over the extent** — two distinct 10×10 grids with
      cells {(0,0),(1,1)} and {(0,1),(1,0)} have identical row clues, column
      clues and extent, confirmed with this file's own
      :func:`independent_clues` — so it holds only *because* of ADR-0032/R1
      and not as a fact about clues. And the sample was drawn from the wrong
      population: :func:`corpus` injects past the storage boundary, and the
      solver reports **5 of the 10 smallest corpus grids as NOT uniquely
      solvable** (``solution_count=2``), so they could never be in a book and
      measuring over them proves nothing about published puzzles. The claim is
      therefore stated from the ADR it rests on, with the counterexample
      recorded so nobody reinstates the sampling;
    * **the key adds nothing to a reader who has the clues.** It is
      ``KEY_LENGTH`` hex characters — 40 bits — over a grid of at least
      ``MIN_SIZE * MIN_SIZE`` cells by CON-011, so it cannot name one grid
      among the 2**100 the smallest allowed extent admits. The grid floor is
      measured over the corpus rather than cited from CON-011, and the bit
      arithmetic is computed rather than asserted as a sentence.
    """
    store, manager = shelf
    records, _ = corpus(store, manager)
    sources = bundle_sources(records, manager.get_all_books())
    published = sources["grids"]

    assert len(published) >= MIN_CORPUS_GRIDS - 1, len(published)
    fingerprints = {
        (
            len(grid[0]),
            len(grid),
            json.dumps(independent_clues(grid), sort_keys=True),
        )
        for grid in published.values()
    }
    distinct = {json.dumps(grid) for grid in published.values()}
    assert len(fingerprints) == len(distinct) == len(published)

    smallest = min(len(grid[0]) * len(grid) for grid in published.values())
    assert smallest >= MIN_SIZE * MIN_SIZE == 100
    assert 4 * player_bundle.KEY_LENGTH == 40 < smallest


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
    """ADR-0041/R7's material, asserted as material: ``"book:"`` then the keys.

    The hashed string is written out rather than re-derived through the
    function under test, for R1's reason and R7's: the recipe's text is the
    rule, and a digest computed the same wrong way agrees with itself. The
    *absence* of a separator is part of the material, so it is part of this
    string.
    """
    store, manager = shelf
    ids = [add_rectangle(store, index, name=f"P{index}") for index in range(3)]
    book_id = finalized_book(manager, store, ids, title="Winter pictures")
    keys = _book_order(store, manager, book_id)

    slug = player_bundle.book_slug(keys)
    assert slug == hashlib.sha256(
        ("book:" + "".join(keys)).encode("utf-8")
    ).hexdigest()[:10]
    assert book_id not in slug
    assert slug != player_bundle.book_slug(list(reversed(keys)))
    assert slug == slug.lower() and len(slug) == player_bundle.KEY_LENGTH

    root = tmp_path / "bundle"
    player_bundle.export_bundle(manager, store, root)
    assert (root / "book" / f"{slug}.json").is_file()


def test_the_slug_does_not_move_when_the_title_is_edited(shelf, tmp_path):
    """ADR-0041/R7's own control, and it runs in both directions.

    R7 excludes the title from the slug because the slug is printed in a QR
    code that cannot be re-pointed and a title is editorial: a typo fix must
    not move an already-printed code. The paired direction is asserted too —
    changing the book's **puzzle membership** *does* move the slug — because a
    test that only checks stability would pass just as well on a slug that is
    a constant, and R7's whole claim is that one input matters and the other
    does not.

    **Why these titles and not an empty one.** The mutant this control exists
    to kill reintroduces the title into the hashed material. Whether it is
    visible depends on the fixture: a book titled ``""`` would hash
    ``"book:" + keys`` either way under a mutant that adds the title without a
    separator, and would hide it completely — the same shape as the ADR's
    *square* worked example hiding a reversed extent in
    :func:`test_the_key_is_the_adrs_worked_example`. So both titles here are
    non-empty, differ from each other, and are asserted to be so before the
    export, which is what makes a green reading mean something.
    """
    store, manager = shelf
    before_title, after_title = "Winter pictures", "Winter pictures, corrected"
    assert before_title and after_title and before_title != after_title

    ids = [add_rectangle(store, index, name=f"P{index}") for index in range(3)]
    book_id = finalized_book(manager, store, ids, title=before_title)
    root = tmp_path / "bundle"
    player_bundle.export_bundle(manager, store, root)
    # Read by index with the count asserted, not unpacked: an unpacking raises
    # before the arms below it and they then report NOT-REACHED, which a
    # per-assertion reading cannot tell from arms that never ran at all.
    first = sorted((root / "book").glob("*.json"))
    assert len(first) == 1
    assert json.loads(first[0].read_text(encoding="utf-8"))["title"] == before_title

    # Naming a book is not a membership change, so it stays finalized
    # (BookManager.update_book_details' own rule) — the book that re-exports
    # here is the same book, out of draft, with a new title.
    assert manager.update_book_details(
        book_id, after_title, "Pictures of winter.", "generic", "adults"
    )
    player_bundle.export_bundle(manager, store, root)
    second = sorted((root / "book").glob("*.json"))

    assert len(second) == 1
    assert second[0].name == first[0].name, "an editorial title change moved the slug"
    assert json.loads(second[0].read_text(encoding="utf-8"))["title"] == after_title

    # The other direction: membership is content, so it does move the slug.
    manager.books[book_id].puzzle_ids.pop()
    assert manager.save_plan(
        manager.books[book_id].book_id,
        matching_plan([store.get_puzzle(pid) for pid in manager.books[book_id].puzzle_ids]),
    )
    assert manager.set_book_status(book_id, BookStatus.READY_FOR_PDF.value) is True
    player_bundle.export_bundle(manager, store, root)
    third = sorted((root / "book").glob("*.json"))

    assert len(third) == 1
    assert third[0].name != first[0].name, "a membership change left the slug unmoved"


def test_two_books_with_the_same_puzzles_are_one_public_book(shelf, tmp_path):
    """R7's consequence of excluding the title, handled rather than noted.

    Before R7 the title was in the hash, so two books could only share a slug
    by sharing a title as well and the file's content was the same either way.
    With the title excluded, two finalized books holding the same puzzles in
    the same order are **one** slug with **two** candidate titles, and the one
    file has to carry a title chosen by something that is a function of the
    titles rather than of the order the store returned the books in — or the
    bundle's bytes would depend on row order and EC-049's byte diff would stop
    meaning anything.
    """
    store, manager = shelf
    ids = [add_rectangle(store, index, name=f"P{index}") for index in range(3)]
    first = finalized_book(manager, store, ids, title="Zebra edition")
    second = finalized_book(manager, store, ids, title="Aardvark edition")
    assert manager.books[first].puzzle_ids == manager.books[second].puzzle_ids
    root = tmp_path / "bundle"

    report = player_bundle.export_bundle(manager, store, root)

    # Read with an index rather than an unpacking: an unpacking raises before
    # the asserts below it, and a per-assertion reading cannot tell that from
    # arms that never ran (the same lesson as M9/M11 on this card).
    written = sorted((root / "book").glob("*.json"))
    assert report.book_count == len(written) == 1
    payload = json.loads(written[0].read_text(encoding="utf-8"))
    assert written[0].stem == player_bundle.book_slug(_book_order(store, manager, first))
    assert payload["title"] == "Aardvark edition"  # settled, not last-read
    assert payload["puzzle_keys"] == _book_order(store, manager, second)


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


@pytest.mark.parametrize(
    "candidates, settled",
    [
        ([], "None"),
        ([None, None], "None"),
        ([None, "easy"], "'easy'"),
        (["hard", "easy", "medium"], "'easy'"),
        (["  a", "a"], "'  a'"),
        (["1", 1], "1"),
        ([True, 1], "1"),
        ([["b"], ["a"]], "['a']"),
    ],
)
def test_settled_is_a_function_of_its_candidates_and_of_nothing_else(candidates, settled):
    """EC-049's reduction, per candidate set — and under every input order.

    ``_settled`` exists so that two stored rows sharing a key cannot make the
    bundle's bytes depend on which row was read first, so a tie decided by
    arrival order is a defect in the mechanism that exists to prevent exactly
    that. One was measured: ``_settled(["1", 1])`` returned ``1`` under
    ``PYTHONHASHSEED`` 0/1/12345 and ``'1'`` under 99999, because the distinct
    values went through a ``set`` whose iteration order broke the tie between
    two candidates with the same ``str()`` (cycle 1, F-5).

    Read over **every permutation** of the candidates rather than under a few
    hash seeds: order-independence is the property, and permutations measure
    it directly instead of sampling the one input that happens to expose it.
    The last three cases are the ones the old reduction got wrong or could not
    take at all — the ``str()`` tie, ``True``/``1`` (equal *and* differently
    typed), and unhashable candidates, which raised ``TypeError`` from the set.
    Each reading is compared by ``repr`` rather than by value, because ``1 ==
    True == 1.0``: a comparison by value cannot tell which of a tie's two
    candidates came back, which is the whole question here.
    """
    readings = [
        repr(player_bundle._settled(list(order)))
        for order in itertools.permutations(candidates)
    ]

    assert len(readings) == math.factorial(len(candidates))
    assert readings == [settled] * len(readings)


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


@pytest.fixture
def db_panel(monkeypatch, tmp_path):
    """The admin panel in **DB mode**, wired to this test's SQLite file.

    The in-memory ``panel`` above issues no SQL at all, so a read-only
    measurement taken around it would pass vacuously — which is why EC-049's
    route reading needs this fixture and not that one. Built the way the
    suite's other DB-mode panels are (``tests/test_book_plan_storage.py``):
    ``DATABASE_URL`` set so ``create_app`` chooses DB mode, and
    ``nonogram.db.session_scope`` pointed at the SQLite scope it then imports.
    """
    import nonogram.db

    from nonogram.admin.app import create_app

    scope = sqlite_session_scope(tmp_path, "route-readonly.db")
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///card-282-test-only")
    monkeypatch.setattr(nonogram.db, "session_scope", scope)
    app = create_app()
    app.config["TESTING"] = True
    app.config["PLAYER_BUNDLE_DIR"] = str(tmp_path / "bundle")
    with app.app_context():
        yield app, scope


def test_the_route_the_owner_posts_is_read_only_too(db_panel, tmp_path):
    """EC-049 "on any export path" — including the only path the owner has.

    AC-382 drives ``export_bundle`` directly. That is the callable entry
    point, not the action: the POST route does a ``get_book`` read of its own
    before the export and is the only way an owner can trigger one, so EC-049
    was proven on everything except the thing it is about (cycle 1, F-6).

    Measured with the same two mechanisms AC-382 uses, against a real
    database: the default-deny statement log, and a row snapshot from
    ``Base.metadata``. The log is asserted non-empty first, because a
    read-only verdict over an empty log is the vacuous pass this fixture
    exists to avoid.
    """
    app, scope = db_panel
    store, manager = app.puzzle_review_service, app.book_manager
    ids = [
        add_rectangle(store, index, name=f"P{index}", side=10) for index in range(3)
    ]
    book_id = finalized_book(manager, store, ids)
    client = app.test_client()
    before = table_rows(scope)

    with recorded_statements() as statements:
        posted = client.post(f"/book/{book_id}/export-player-bundle")

    assert posted.status_code == 302
    assert statements, "the route issued no statement: it did not read the database"
    assert forbidden_statements(statements) == []
    assert table_rows(scope) == before
    root = tmp_path / "bundle"
    assert len(list((root / "puzzle").glob("*.json"))) == len(ids)
    records = [store.get_puzzle(pid) for pid in ids]
    assert provenance_violations(root, records, manager.get_all_books()) == []


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
