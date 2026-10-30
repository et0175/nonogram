"""CARD-283 — the public player page: the admin game, served static, with no
answer in the browser (COMP-011, FR-045, ADR-0041, ADR-0038/R6).

The page is ``/play/<key>``. It is static files (``player/``) plus the static
JSON CARD-282's exporter writes, assembled into one deployable directory by
``player/assemble.py`` and served here by a plain ``http.server`` over
loopback — no Flask, no admin service, no database in the customer path.

Three tiers, and which tier answers which AC is a decision rather than a
convenience:

* **tree tests** read the assembled site off disk. They own EC-048, because
  "no asset carries the answer" is a statement about bytes and a browser adds
  nothing to it;
* **browser tests** (``@pytest.mark.browser``, pytest-playwright + Chromium,
  ADR-0038/R7) own AC-383..AC-386 and EC-050: the drawn board, the marking
  transitions, the solved state, resume across a reload, the phone layout and
  what leaves the page. They refuse LOUDLY when Chromium is absent
  (ADR-0038/R8) through CARD-160's own fixtures, imported below rather than
  rewritten;
* **module tests** drive ``player/assemble.py``'s pure functions directly, so
  each guard's control can plant its defect as a value instead of writing a
  broken tree.

No ``hypothesis`` (not in the dependency baseline): the corpora below are
hand-built with seeded ``random.Random`` and every sweep asserts its own
minimum case count, so a corpus cannot silently shrink to nothing.

Clues are compared against ``_encode`` — the independent run-length encoder in
``tests/test_puzzle_solver_page.py`` — never against ``nonogram.clues``, which
is the function under test on the other side of the wire.

=========================================================================
EC-048, and why the answer to it is a REMOVED CHANNEL and not a better scan
=========================================================================
ADR-0041/R2 forbids any public asset from carrying "a solution grid or data
from which any solution cell is recoverable, for any puzzle, on any export
path". CARD-282 built the exporter, wrote the scan for that rule — and then
measured a path straight through it (its cycle 2, F-3): rename a puzzle to the
base-64 of its own packed grid, and the exporter writes that string into the
bundle's declared ``title`` field. Every provenance check passes, because the
value's source is "a stored title", which is a named good source. The
published ``index.json`` then base-64-decodes back to all 144 cells of a 12x12
answer. CARD-282's own comment calls it "a REACHABLE PATH past ADR-0041/R2 ...
it is not something this scan can decide" and routes the decision to this
card.

It cannot be decided by a scan, and that is the finding rather than an
excuse. A scan must answer "does this string carry a grid?", and there is no
such decision procedure: the set of encodings of a grid is not enumerable, and
CARD-282 measured its own denylist missing **7 of 7** planted encodings.

So this card does not filter the free-text field. ``player/assemble.py``
**rebuilds** every served ``puzzle/<key>.json`` from a closed schema
(:data:`SERVED_SCHEMA` there) and ``title`` is not in it. The channel is gone,
and what remains is provably too narrow to hold a grid:

#. ``clues`` and ``key`` are the two projections ADR-0041 sanctions by name
   (R5, R1). They are **exempt**, and the exemption is the ADR's rather than
   anything measured here: ``_clues`` narrows the field (a clue has to be a
   run-length encoding a line of that length could have, the two axes have to
   agree on the filled count) but a 10-cell line still admits 144 clues, so
   twenty lines of a 10x10 carry ~143 bits and a clue set no grid realises is
   accepted. The claim "clues cannot be borrowed as a free numeric channel"
   was measured false in cycle 1 of this card's review and is gone; the clue
   values' integrity is ADR-0041/R5's, upstream in the exporter;
#. every other served value is drawn from a domain the assembler enumerates,
   and two of the three are not free at all — ``width`` and ``height`` are
   refused unless they equal the lengths of the served clue axes, so a reader
   recomputes them. What is left is the tier, whose domain is the runtime's
   three-label tier enum. ``check_capacity`` refuses to assemble unless every
   served name is either exempt or counted and the counted total is strictly
   below ``MIN_SIZE * MIN_SIZE`` bits. That ceiling establishes "no served
   field is wide enough to carry a grid" and NOT EC-048's one-cell threshold,
   which no capacity bound can reach; the figure (2.00 bits today) is computed
   by the deployed code (``free_capacity_bits``), never transcribed. Cycle 1
   measured what the difference is worth: a 56-bit ``tier`` passed the ceiling
   and carried 56 cells of a published answer to the site
   (``test_a_tier_outside_the_vocabulary_carries_no_cell_to_the_site`` is now
   that plant, refused). The residual is two bits of tier label a hostile
   store could choose by the answer — named in ``assemble.py``'s docstring,
   not covered;
#. and a sweep runs anyway, over the bytes: it tries to *decode* every
   non-exempt value and every static file in the served tree, and it is proved
   able to fail by running the identical sweep over the **bundle** the site was
   assembled from, where it must find the grid. Dirty in, clean out, one scan.

What that does NOT claim, named rather than omitted:

* the **clues determine the solution** of a uniquely solvable puzzle. That is
  not a leak, it is the game (ADR-0041's Context: the solved check *is* clue
  satisfaction). It is measured here against the real solver rather than
  asserted, and the exempt fields are redacted before the sweep reads a file;
* the sweep is a belt. The *guarantee* is the canonical rebuild plus the
  capacity bound, both of which are default-deny by construction.

==============================
Tests, by node id (FR-045)
==============================
Written out in full — path and name on one line each — because the
architecture validator resolves a check ref by ``git grep -lw`` of the WHOLE
``path::name`` string over tracked, non-Markdown code. A ref whose string
appears nowhere reads as a DEAD check ref however green the test is, and the
four this card owns were wrapped across two lines in the card, so writing the
tests did not by itself revive them. The table is held to the registry by
``test_the_registrys_check_refs_for_this_card_all_resolve``, so it cannot
outlive a rename in either direction:

* AC-383 — ``tests/test_public_player.py::test_play_page_renders_and_marks``
* AC-384 — ``tests/test_public_player.py::test_solved_fires_on_clue_satisfaction_only``
* AC-385 — ``tests/test_public_player.py::test_resume_is_local_and_the_page_writes_nowhere``
* AC-386 — ``tests/test_public_player.py::test_phone_viewport_is_playable``
* EC-050 — ``tests/test_public_player.py::test_no_write_request_for_any_interaction``
* EC-048 — ``tests/test_public_player.py::test_served_tree_is_clean_of_answers``

The last one is listed for a different reason, and the difference is a finding
rather than a formatting choice. **The registry does not name it.** FR-045's
EC-048 carries one ref, ``tests/test_player_bundle.py::test_bundle_is_clean_of_answers``
— the BUNDLE half, CARD-282's. Both the card and ADR-0041/R2's own comment say
the served half is this module's ``test_served_tree_is_clean_of_answers``, and
the validator splits a ref on commas, so EC-048's ref should be the pair. It is
one word of requirements.yml, which is outside this card's declared Touches, so
it is reported instead of edited — and named here so the node id is at least
greppable from code.
"""

from __future__ import annotations

import ast
import base64
import hashlib
import http.server
import importlib.util
import itertools
import json
import math
import random
import re
import shutil
import sys
import threading
from pathlib import Path

import pytest

from nonogram.admin import player_bundle
from nonogram.limits import MAX_SIZE, MIN_SIZE
from nonogram.solver import solve
from tests.test_puzzle_solver_page import (  # noqa: F401 — fixtures used by name
    MAJOR_EVERY,
    _encode,
    _unique_grid,
    browser_page,
    browser_type,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
PLAYER_DIR = REPO_ROOT / "player"


def _load_assembler():
    """``player/assemble.py``, loaded by path.

    ``player/`` is not a package and is not on ``sys.path`` — ADR-0041/R3 puts
    the public player outside the Python package on purpose, and putting it on
    the path to test it would undo that. Same reason
    ``tests/test_suite_profile.py`` loads ``meta/profiling/rank_durations.py``
    by path.
    """
    path = PLAYER_DIR / "assemble.py"
    spec = importlib.util.spec_from_file_location("player_assemble", path)
    assert spec is not None and spec.loader is not None, path
    module = importlib.util.module_from_spec(spec)
    # Registered before it is executed: ``@dataclass`` resolves annotations
    # through ``sys.modules[cls.__module__]``, so a module loaded by path and
    # left unregistered raises at the decorator rather than at the import.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


assembler = _load_assembler()

#: The bundle fields ADR-0041 exempts from EC-048, read from the exporter's own
#: declaration rather than restated (ADR-0039/R2). Redacted before the sweep
#: below reads a file: they ARE derived from the solution, by name and by
#: design, so including them would make the sweep report the game as a leak.
EXEMPT_FIELDS = frozenset(player_bundle.SOLUTION_DERIVED_FIELDS)


# ==========================================================================
# Grids, keys and a bundle to assemble from
# ==========================================================================


def _bits(grid) -> str:
    return "".join("1" if cell else "0" for row in grid for cell in row)


def _public_key(grid) -> str:
    """ADR-0041/R1's key, reimplemented here.

    A second implementation rather than a call to
    ``player_bundle.puzzle_key``: the fixtures below name their files with it,
    so if it disagreed with the exporter the whole suite would be testing a
    namespace nothing else uses.
    ``test_the_key_recipe_matches_the_exporters`` is that cross-check.
    """
    text = f"{len(grid[0])}x{len(grid)}:{_bits(grid)}"
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:10]


def _bundle_payload(grid, *, tier: str, title: str) -> dict:
    """One ``puzzle/<key>.json`` as CARD-282's exporter writes it.

    Its field names come from ``player_bundle.PUZZLE_FILE_FIELDS``, so a field
    that exporter adds later arrives in these fixtures — and in the "what did
    the assembler drop?" assertions — without anybody remembering to add it.
    """
    rows, columns = [_encode(row) for row in grid], [_encode(col) for col in zip(*grid)]
    payload = {
        "key": _public_key(grid),
        "width": len(grid[0]),
        "height": len(grid),
        "tier": tier,
        "title": title,
        "clues": {"rows": rows, "columns": columns},
    }
    assert set(payload) == set(player_bundle.PUZZLE_FILE_FIELDS), sorted(payload)
    return payload


def _leaky_title(grid) -> str:
    """The exact shape CARD-282 cycle 2 measured: base-64 of the packed grid.

    Fully recoverable — :func:`decoded_recoveries` finds every cell in it,
    which is what makes it a control and not a decoration.
    """
    bits = _bits(grid)
    packed = int(bits + "0" * (-len(bits) % 8), 2).to_bytes((len(bits) + 7) // 8, "big")
    return base64.b64encode(packed).decode("ascii")


#: The corpus every tree test runs over: one grid per interesting shape, each
#: uniquely solvable by construction (``_unique_grid``: every row tight, so
#: the clues admit exactly one grid) and re-verified against the real solver by
#: ``test_every_fixture_puzzle_is_uniquely_solvable``.
#:
#: The 12x12 is CARD-282 cycle 2's own case, cell for cell: 144 cells is the
#: grid that was recovered from a published title.
GRIDS: dict[str, list[list[bool]]] = {
    "min": _unique_grid(MIN_SIZE, MIN_SIZE, seed=283),
    "cycle2-144": _unique_grid(12, 12, seed=2822),
    "oblong": _unique_grid(25, 15, seed=2833),
    "max": _unique_grid(MAX_SIZE, MAX_SIZE, seed=2834),
}

#: Which tier string each fixture puzzle is stored with — including the three
#: the served tier rule must narrow or drop: a capitalised one, an empty one
#: and one that is neither a word nor short.
TIERS = {
    "min": "easy",
    "cycle2-144": "Hard",
    "oblong": "",
    "max": "medium",
}


#: The BOOK title the shared fixtures carry: editorial text, deliberately
#: not an encoded grid.
#:
#: It is a named constant with a parameter beside it rather than a literal
#: inside :func:`write_bundle` because of what cycle 2 of CARD-284's review
#: did to the literal. Its C2-M41 changed it to a leaky value, and
#: ``test_served_tree_is_clean_of_answers`` — the test ADR-0041/R2's own
#: ``check:`` comment names as the served tree's half — FAILED, while
#: ``tests/test_public_player_pages.py::test_the_book_title_exemption_is_scoped_and_its_cost_is_measured``
#: asserted that exactly that leak SUCCEEDS. Two tests, one mandatory rule,
#: opposite outcomes, discriminated by a fixture constant. The served-half
#: control now passes BOTH titles in explicitly and asserts both outcomes,
#: so this default is a convenience for every other test and is load-bearing
#: for none of them.
BOOK_TITLE = "A book"


def write_bundle(
    root: Path, grids=None, *, leaky=True, book_title: str = BOOK_TITLE
) -> dict[str, str]:
    """A player bundle at ``root``; returns ``{name: key}``.

    Every puzzle's title is the base-64 of its own grid when ``leaky`` (the
    default), because the question this card exists to answer is what happens
    to such a title — a fixture that only ever carries "Snowy owl" would make
    every assertion below pass for the wrong reason.

    The BOOK's title is a different field with the opposite answer — it is
    SERVED, under ADR-0041/R2's 2026-10-28 exemption — so it is
    :data:`BOOK_TITLE` by default and overridable per call. Nothing may read
    that default as a guarantee: see :data:`BOOK_TITLE`.

    ``index.json`` and one ``book/<slug>.json`` are written too: they are part
    of a real bundle, and this card's site must be measured *not* serving
    them rather than measured against a bundle that never had them.
    """
    grids = GRIDS if grids is None else grids
    keys: dict[str, str] = {}
    entries = []
    for name, grid in grids.items():
        payload = _bundle_payload(
            grid,
            tier=TIERS.get(name, "easy"),
            title=_leaky_title(grid) if leaky else f"Picture {name}",
        )
        keys[name] = payload["key"]
        path = root / "puzzle" / f"{payload['key']}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        entries.append({k: v for k, v in payload.items() if k != "clues"})
    (root / "index.json").write_text(
        json.dumps({"puzzles": entries}, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    book = root / "book" / "0123456789.json"
    book.parent.mkdir(parents=True, exist_ok=True)
    book.write_text(
        json.dumps(
            {
                "slug": "0123456789",
                "title": book_title,
                "puzzle_keys": sorted(keys.values()),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return keys


@pytest.fixture
def bundle(tmp_path) -> tuple[Path, dict[str, str]]:
    root = tmp_path / "bundle"
    return root, write_bundle(root)


@pytest.fixture
def site(bundle, tmp_path):
    """The assembled, deployable site — what a static host would serve."""
    root, keys = bundle
    report = assembler.assemble(root, tmp_path / "site")
    assert report.puzzle_count == len(keys), report
    return report, keys


# ==========================================================================
# EC-048's sweep: can anything in the tree be decoded back into the grid?
# ==========================================================================


def grid_bit_forms(grid) -> dict[str, str]:
    """The bit strings a recovered grid could legitimately be read as.

    Row-major and column-major, each forwards and reversed, and the
    complement of each — eight readings, because a leak that stores the
    transpose or the inverse of a grid has leaked it just the same.
    """
    row_major = _bits(grid)
    column_major = "".join("1" if grid[y][x] else "0" for x in range(len(grid[0])) for y in range(len(grid)))
    forms: dict[str, str] = {}
    for order, text in (("row-major", row_major), ("column-major", column_major)):
        for direction, value in ((order, text), (f"{order} reversed", text[::-1])):
            forms[direction] = value
            forms[f"{direction} complemented"] = value.translate(str.maketrans("01", "10"))
    return forms


#: Alphabets a leak might spell cells in, mapped onto ``1``/``0`` before the
#: bit forms above are looked for. Not a claim of completeness — the
#: completeness claim is the canonical rebuild, not this table.
_CELL_ALPHABETS = (("#", "."), ("X", " "), ("*", "-"), ("true", "false"), ("1", "0"))

#: Decoders tried on every token long enough to carry a grid. Each turns text
#: into bytes, which are then read as a bit string, most significant bit
#: first — the packing ``_leaky_title`` uses and the one ``int.to_bytes``
#: produces.
_DECODERS = {
    "base64": lambda text: base64.b64decode(text + "=" * (-len(text) % 4), validate=True),
    "base64url": lambda text: base64.urlsafe_b64decode(text + "=" * (-len(text) % 4)),
    "base32": lambda text: base64.b32decode(text + "=" * (-len(text) % 8)),
    "base85": base64.b85decode,
    "hex": bytes.fromhex,
}

#: Tokens shorter than this are not swept. A grid is at least
#: ``MIN_SIZE * MIN_SIZE`` bits; the shortest encoding of that many bits is
#: base-85 at ~6.4 bits per character, so anything shorter than this cannot
#: carry one and a scan that reported it would be reporting coincidence.
#: Derived, not chosen: a number a later reader can recompute.
MIN_TOKEN = int((MIN_SIZE * MIN_SIZE) / 6.5)

_TOKEN = re.compile(r"[A-Za-z0-9+/=_\-]{%d,}" % MIN_TOKEN)


def _as_bits(data: bytes) -> str:
    return "".join(format(byte, "08b") for byte in data)


def decoded_recoveries(text: str, grid) -> list[str]:
    """Every way ``text`` can be read back as ``grid``'s cells.

    Three families, in increasing effort:

    #. the text, with each cell alphabet folded onto ``1``/``0``, holding one
       of :func:`grid_bit_forms` as a substring;
    #. any token of :data:`_TOKEN` in it that one of :data:`_DECODERS` turns
       into bytes whose bit string holds one of those forms;
    #. the same, over the whole text with whitespace removed, so a leak split
       across lines is still read.

    An empty list is the only acceptable answer for a served asset. It is not
    the same as "there is no encoding of the grid in here" — see this module's
    docstring on why no scan can say that, and what says it instead.
    """
    forms = grid_bit_forms(grid)
    hits: list[str] = []
    for one, zero in _CELL_ALPHABETS:
        folded = text.replace(one, "1").replace(zero, "0")
        for name, bits in forms.items():
            if bits in folded:
                hits.append(f"{name} spelled {one}/{zero}")
    candidates = set(_TOKEN.findall(text))
    squeezed = re.sub(r"\s+", "", text)
    candidates.update(_TOKEN.findall(squeezed))
    for token, (decoder_name, decode) in itertools.product(sorted(candidates), _DECODERS.items()):
        try:
            raw = decode(token)
        except Exception:  # noqa: BLE001 — any failure means "not this decoder"
            continue
        if len(raw) * 8 < len(forms["row-major"]):
            continue
        unpacked = _as_bits(raw)
        for name, bits in forms.items():
            if bits in unpacked:
                hits.append(f"{name} out of {decoder_name}")
    return sorted(set(hits))


def _redacted(payload, depth: int = 0):
    """``payload`` with every :data:`EXEMPT_FIELDS` value replaced.

    So the sweep reads what EC-048 actually forbids. Written recursively
    rather than at the top level only: an exempt name nested inside another
    object is still the exempt projection.
    """
    if isinstance(payload, dict):
        return {
            name: ("<exempt>" if name in EXEMPT_FIELDS else _redacted(value, depth + 1))
            for name, value in payload.items()
        }
    if isinstance(payload, list):
        return [_redacted(value, depth + 1) for value in payload]
    return payload


def sweep_tree(root: Path, grids) -> dict[str, list[str]]:
    """Every recovery :func:`decoded_recoveries` finds anywhere under ``root``.

    Keyed by ``"<relative path> [<grid name>]"``. A JSON file is swept once,
    as its redacted payload, so the exempt projections are not reported as
    leaks; every other file is swept whole. (An earlier revision of this
    docstring described a second raw-text pass over each JSON file. There is
    no such pass — the body is one ``if``/``else`` — and the sentence was
    deleted rather than implemented: the pass would read the exempt clue
    numbers, which is the one thing this sweep must not report, and the belt's
    value is the non-exempt text it already reads.)
    """
    found: dict[str, list[str]] = {}
    files = [path for path in sorted(root.rglob("*")) if path.is_file()]
    assert files, f"nothing to sweep under {root}"
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:  # pragma: no cover — the tree is text
            text = path.read_bytes().decode("latin-1")
        if path.suffix == ".json":
            swept = json.dumps(_redacted(json.loads(text)), sort_keys=True)
        else:
            swept = text
        for name, grid in grids.items():
            hits = decoded_recoveries(swept, grid)
            if hits:
                found[f"{path.relative_to(root).as_posix()} [{name}]"] = hits
    return found


# ==========================================================================
# Tree tests — EC-048 and the assembled tree
# ==========================================================================


def test_served_tree_is_clean_of_answers(bundle, tmp_path) -> None:
    """EC-048 / AC-381's served half (ADR-0041/R2) — and its own control.

    The same sweep runs over both trees. The **bundle** must be dirty: its
    PUZZLE titles are base-64 of their grids, which is the path CARD-282
    measured and routed here. One scan, both directions, so a sweep that had
    quietly stopped working could not report this as a pass — the failure
    mode CARD-282's cycle 1 found in its own guard.

    **The served half is TWO statements since ADR-0041/R2's 2026-10-28
    amendment, and this test makes both of them rather than one.** R2 now
    carries a third exemption beside the clues and the answer key: a book's
    own owner-authored display title, served verbatim on ``/b/<slug>`` and
    nowhere else, exempt by SCOPE rather than by safety. So "the served tree
    is clean" is false as a bare sentence, and the rule's own served-half
    control has to say which half is which:

    #. **a PUZZLE title cannot get out.** With an editorial book title, the
       served tree is clean — ``== {}``, nothing exempted, nothing
       subtracted — although every puzzle title in the bundle is the base-64
       of its own grid;
    #. **a BOOK title is admitted, and only in the book file.** With a leaky
       book title the sweep reports EXACTLY ``book/<slug>.json``, by name,
       and the puzzle files and the library index stay clean under the same
       plant. That is the declared exemption, asserted here rather than
       inferred from a fixture.

    Why both titles are passed in explicitly instead of taken from
    :data:`BOOK_TITLE`: cycle 2 of CARD-284's review changed that literal to
    a leaky value (its C2-M41) and this test failed, while
    ``test_the_book_title_exemption_is_scoped_and_its_cost_is_measured``
    asserted in the same suite that exactly that leak succeeds — two tests,
    opposite outcomes for one mandatory rule, discriminated only by a fixture
    constant. A control a fixture default can flip is not a control.
    """
    bundle_root, _ = bundle

    # EC-048's own verification clause: a seeded corpus, "with the minimum
    # corpus size asserted in the test". Asserted HERE and not only in
    # test_every_fixture_puzzle_is_uniquely_solvable, because the control
    # below (len(leaked) >= len(GRIDS)) scales with the corpus and would pass
    # just as green on a GRIDS of one — co-location is not ownership.
    assert len(GRIDS) >= 4, sorted(GRIDS)
    assert {len(grid) for grid in GRIDS.values()} >= {MIN_SIZE, MAX_SIZE}, (
        "the corpus no longer spans the supported extent"
    )

    leaked = sweep_tree(bundle_root, GRIDS)
    assert len(leaked) >= len(GRIDS), (
        "the control is dead: the sweep found no recoverable grid in a bundle "
        f"whose every title is base-64 of its own grid. Found: {leaked}"
    )
    assert decoded_recoveries(_leaky_title(GRIDS["cycle2-144"]), GRIDS["cycle2-144"]), (
        "the sweep cannot even read CARD-282 cycle 2's own measured leak"
    )

    # Half 1 — a PUZZLE title cannot get out. Every puzzle title in this
    # bundle is base-64 of its own grid and the book's is editorial, so the
    # served tree has to be clean with nothing exempted.
    editorial = "A book about owls"
    assert not decoded_recoveries(editorial, GRIDS["min"]), (
        "the editorial title is itself recoverable, so half 1 would be vacuous"
    )
    clean_root = tmp_path / "editorial-bundle"
    clean_keys = write_bundle(clean_root, book_title=editorial)
    clean = assembler.assemble(clean_root, tmp_path / "editorial-site")
    assert clean.puzzle_count == len(clean_keys), clean
    assert sweep_tree(clean.site_dir, GRIDS) == {}

    # Half 2 — a BOOK title IS admitted, by R2's 2026-10-28 exemption, and
    # only in the book file. The exemption is named in the assembler as well
    # as asserted here, so this is the declared channel and not a surprise.
    assert assembler.EXEMPT_LISTING_FIELDS == ("title",)
    assert "title" in assembler.SERVED_BOOK_SCHEMA
    assert "title" not in assembler.SERVED_ENTRY_SCHEMA
    assert "title" not in assembler.SERVED_INDEX_SCHEMA
    assert "title" not in assembler.SERVED_SCHEMA
    leak = _leaky_title(GRIDS["min"])
    assert len(leak) <= assembler.SERVED_TITLE_MAX_CHARS, len(leak)
    leaky_root = tmp_path / "leaky-bundle"
    write_bundle(leaky_root, book_title=leak)
    leaky = assembler.assemble(leaky_root, tmp_path / "leaky-site")
    recovered = sweep_tree(leaky.site_dir, GRIDS)
    assert sorted(recovered) == ["book/0123456789.json [min]"], recovered
    assert not [where for where in recovered if where.startswith("puzzle/")]
    assert not [where for where in recovered if where.startswith("index.json")]


def test_the_served_puzzle_files_are_rebuilt_not_copied(site) -> None:
    """The guarantee behind EC-048: every served value is one this card derived.

    Each file holds exactly ``SERVED_SCHEMA``, and its bytes equal a rebuild
    from (key, extent, tier, clues) alone. So there is no spare room in the
    file at all: a value that is not one of those five is not merely
    unchecked, it is absent.
    """
    report, keys = site
    checked = 0
    for name, grid in GRIDS.items():
        path = report.site_dir / "puzzle" / f"{keys[name]}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert sorted(payload) == sorted(assembler.SERVED_SCHEMA), (name, sorted(payload))
        rebuilt = {
            "key": _public_key(grid),
            "width": len(grid[0]),
            "height": len(grid),
            "tier": TIERS[name].strip().lower(),
            "clues": {
                "rows": [_encode(row) for row in grid],
                "columns": [_encode(column) for column in zip(*grid)],
            },
        }
        expected = json.dumps(rebuilt, sort_keys=True, ensure_ascii=True, indent=2) + "\n"
        assert path.read_text(encoding="utf-8") == expected, name
        checked += 1
    assert checked == len(GRIDS)


def test_the_picture_name_is_dropped_and_the_books_title_is_not(site) -> None:
    """The two ``title`` fields, and the opposite answers they get.

    Both are declared by the exporter, so neither assertion is a defence
    against a field nobody writes — and that is the whole trap this test
    exists to hold open, because cycle 1 of CARD-284's review gated on the
    two being argued as one field:

    #. a **puzzle's** title is the picture's name. EC-048 forbids it by name
       on every asset the public site serves, so it is in none of the three
       served schemas, and every drop is named in the report so the owner can
       see that the public page shows no picture name rather than wondering;
    #. a **book's** display title is owner-authored editorial text. The owner
       decided on 2026-10-28 to serve it (CARD-284 F-001), so it is in
       ``SERVED_BOOK_SCHEMA``, it is NOT dropped, and the served value is the
       bundle's.

    The drop list is asserted as an equality over the whole report rather
    than by membership, which is what makes the book's absence from it a
    measurement: if the book's title started being dropped again, or a
    puzzle's stopped being, this reds.
    """
    report, keys = site
    assert "title" in player_bundle.PUZZLE_FILE_FIELDS
    assert "title" in player_bundle.BOOK_FILE_FIELDS
    # The picture name: forbidden, on all three schemas that could carry it.
    assert "title" not in assembler.SERVED_SCHEMA
    assert "title" not in assembler.SERVED_ENTRY_SCHEMA
    # The book's: exempt and served, on exactly one.
    assert "title" in assembler.SERVED_BOOK_SCHEMA
    assert assembler.EXEMPT_LISTING_FIELDS == ("title",)
    assert sorted(report.dropped) == sorted((key, "title") for key in keys.values())
    assert ("0123456789", "title") not in report.dropped
    book = json.loads(
        (report.site_dir / "book" / "0123456789.json").read_text(encoding="utf-8")
    )
    assert book["title"] == BOOK_TITLE, book
    # Read through the constant rather than off a second copy of the literal:
    # cycle 2's C2-M41 changed the fixture's title and the suite's two
    # statements about it disagreed. Now exactly one test says what the
    # fixture's title IS (this one, through the name), and R2's served-half
    # control states the rule with both titles passed in explicitly.
    assert BOOK_TITLE == "A book"


def test_the_index_and_book_files_are_rebuilt_and_never_copied(site) -> None:
    """The two listings are served, and not one byte of them is a copy.

    This test was ``..._are_not_served_by_this_page`` until CARD-284, which
    is the card CARD-283 routed the decision to. The rename is the point —
    the old name would now be a false claim.

    "Rebuilt" and "carries no title" are different claims and only the first
    is this test's. A served book file carries the BOOK's display title under
    CARD-284's exemption, and the entries inside it carry no puzzle title at
    all; which is which is
    ``test_the_picture_name_is_dropped_and_the_books_title_is_not``'s. What
    is held here is that neither file's bytes are the bundle's and that each
    holds exactly its schema — rebuilt field by field, so there is no room in
    either file for a value this module did not derive or exempt.

    Three halves, because "rebuilt" is only worth something if none of the
    bundle's own bytes survive: the served files exist, they hold exactly the
    served schemas, and neither file is byte-equal to the bundle's.
    """
    report, keys = site
    bundle_index = (report.site_dir.parent / "bundle" / "index.json").read_bytes()
    served_index = (report.site_dir / "index.json").read_bytes()
    assert served_index != bundle_index
    assert sorted(json.loads(served_index)) == sorted(assembler.SERVED_INDEX_SCHEMA)
    for entry in json.loads(served_index)["puzzles"]:
        assert sorted(entry) == sorted(assembler.SERVED_ENTRY_SCHEMA), entry

    book = report.site_dir / "book" / "0123456789.json"
    assert book.read_bytes() != (
        report.site_dir.parent / "bundle" / "book" / "0123456789.json"
    ).read_bytes()
    assert sorted(json.loads(book.read_text(encoding="utf-8"))) == sorted(
        assembler.SERVED_BOOK_SCHEMA
    )
    # Nothing else of the bundle is served: ``ignored`` is now only what no
    # page reads, and the two listings have left it.
    assert report.ignored == ()
    assert report.book_count == 1
    assert len(json.loads(served_index)["puzzles"]) == len(keys)


def test_the_capacity_bound_is_derived_and_can_fail(monkeypatch, tmp_path) -> None:
    """The number the assembler's half of EC-048 rests on, and what it is for.

    The claim the deployed code makes — and the only one it makes — is "no
    served field is wide enough to carry a grid": the counted total is
    strictly below the fewest cells a published grid has. EC-048's own
    threshold is one cell, which no capacity bound can reach while any field
    has a choice, so the number is a trip-wire and the domains do the work
    (``assemble.py``'s docstring says so, and
    ``test_the_served_tier_set_is_the_runtimes_tier_vocabulary`` plus
    ``test_the_served_extents_are_recomputable_from_the_served_clues`` are
    where each domain is held).

    Four halves are measured here: the live figure, the partition (a served
    field nobody counted is refused), the ceiling firing when a counted field
    is widened, and the check being consulted by ``assemble`` rather than
    merely present.
    """
    bits = assembler.check_capacity()
    assert bits == assembler.free_capacity_bits()
    assert assembler.CAPACITY_CEILING_BITS == MIN_SIZE * MIN_SIZE
    assert bits < assembler.CAPACITY_CEILING_BITS
    # The residual the docstring names, derived here rather than transcribed:
    # the extents are determined by the clues and the tier is the one free
    # field, four labels wide.
    assert bits == pytest.approx(math.log2(len(assembler.SERVED_TIERS) + 1))

    # The partition: every served name is either exempt or counted, and a new
    # one is neither until somebody counts it.
    assert set(assembler.SERVED_SCHEMA) == set(assembler.SERVED_VALUE_SPACE) | set(
        assembler.EXEMPT_SERVED_FIELDS
    )
    assert not set(assembler.SERVED_VALUE_SPACE) & set(assembler.EXEMPT_SERVED_FIELDS)
    monkeypatch.setattr(assembler, "SERVED_SCHEMA", (*assembler.SERVED_SCHEMA, "note"))
    with pytest.raises(ValueError, match="not partitioned"):
        assembler.check_capacity()
    monkeypatch.undo()

    # The ceiling: a counted field widened to grid size fires it.
    widened = dict(assembler.SERVED_VALUE_SPACE)
    widened["tier"] = 2 ** (MAX_SIZE * MAX_SIZE)
    monkeypatch.setattr(assembler, "SERVED_VALUE_SPACE", widened)
    with pytest.raises(ValueError, match="capacity argument no longer holds"):
        assembler.check_capacity()
    # And the check is CONSULTED, not merely present: assembling with the
    # widened schema refuses outright. Without this half the call site could
    # be deleted and the test above would still pass (CARD-283's mutation
    # round, M16).
    with pytest.raises(ValueError, match="capacity argument no longer holds"):
        assembler.assemble(None, tmp_path / "refused")
    assert not (tmp_path / "refused" / "play").exists()


def test_the_served_tier_set_is_the_runtimes_tier_vocabulary() -> None:
    """ADR-0039/R2 — the served tier set is the enum's, not a hand-written rule.

    ``assemble.py`` cannot import the package (ADR-0041/R3) and cannot load
    ``nonogram.difficulty`` by path the way it loads the import-free
    ``limits.py``, because that module imports ``nonogram.errors``. So the
    vocabulary is restated there as a three-label allow-list and held to the
    authority *here*, where importing the package is legal — the precedent
    CLAUDE.md names for exactly this situation (``propagate.mask_runs``,
    cross-checked against ``clues.encode_line`` from the test tree).

    Both directions, so neither side can drift alone: the served set is
    exactly the enum's values, in ``book_plan``'s book order, and every
    served label round-trips through ``_tier`` while nothing outside the set
    does.
    """
    from nonogram.admin.book_plan import TIERS as BOOK_TIERS
    from nonogram.difficulty import Tier

    assert assembler.SERVED_TIERS == tuple(tier.value for tier in Tier)
    assert assembler.SERVED_TIERS == tuple(tier.value for tier in BOOK_TIERS)
    assert len(assembler.SERVED_TIERS) == 3
    for tier in Tier:
        assert assembler._tier(tier.value) == tier.value
        assert assembler._tier(tier.value.upper()) == tier.value
    assert assembler.SERVED_VALUE_SPACE["tier"] == len(assembler.SERVED_TIERS) + 1


def test_the_tier_is_narrowed_to_the_vocabulary_or_dropped() -> None:
    """A tier is one of the three labels or it is not served at all.

    This is the one free non-exempt field, so it is where all of the capacity
    bound is spent: the membership rule below is what makes
    ``SERVED_VALUE_SPACE["tier"]`` four. Each case is a value the admin store
    can really hold — including the one cycle 1 of this card's review measured
    going through, which the next test takes apart cell by cell.
    """
    assert assembler._tier("medium") == "medium"
    assert assembler._tier("Hard") == "hard"
    assert assembler._tier("  easy  ") == "easy"
    assert assembler._tier("") == ""
    assert assembler._tier(None) == ""
    assert assembler._tier("requires guessing") == ""
    assert assembler._tier("tqlhkuhxpmgj") == ""  # a short lowercase word, not a tier
    assert assembler._tier("easyish") == ""
    assert assembler._tier(_leaky_title(GRIDS["min"])) == ""

    # And the half that was reported nowhere until cycle 2 of this card's
    # review (N-4): a tier the bundle HAD and the site does not is a
    # narrowing the owner is told about, while an absent or blank tier is not,
    # because nothing was lost. Both served values are "", so without this
    # distinction the two cases are the same to a reader of the report.
    assert assembler.tier_narrowed("tqlhkuhxpmgj") is True
    assert assembler.tier_narrowed("requires guessing") is True
    assert assembler.tier_narrowed(_leaky_title(GRIDS["min"])) is True
    assert assembler.tier_narrowed(17) is True
    assert assembler.tier_narrowed(None) is False
    assert assembler.tier_narrowed("") is False
    assert assembler.tier_narrowed("   ") is False
    assert assembler.tier_narrowed("Hard") is False
    assert assembler.tier_narrowed("medium") is False


#: The lowercase alphabet a tier string could be read as digits of, and how
#: many whole bits 12 of those characters carry. Cycle 1 of this card's review
#: used exactly this: 26**12 > 2**56, so a 12-character lowercase "tier"
#: carries 56 cells — and 12 characters is below :data:`MIN_TOKEN`, so the
#: decoding sweep cannot see it either. Only the tier's domain stops it.
_BASE26 = "abcdefghijklmnopqrstuvwxyz"
_BASE26_CHARS = 12
_BASE26_BITS = 56


def _base26_cells(text: str) -> str:
    """``text`` read back as the bits it would encode, or ``""``.

    The inverse of the review's plant: a 12-character lowercase string is a
    base-26 numeral, and its low 56 bits are 56 cells of a grid.
    """
    if len(text) != _BASE26_CHARS or any(character not in _BASE26 for character in text):
        return ""
    value = 0
    for character in text:
        value = value * 26 + _BASE26.index(character)
    return format(value, f"0{_BASE26_BITS}b")[-_BASE26_BITS:]


def test_a_tier_outside_the_vocabulary_carries_no_cell_to_the_site(tmp_path) -> None:
    """EC-048, at its own threshold: cycle 1's measured channel, closed.

    Cycle 1 of this card's review stored a 12-character base-26 encoding of
    the first 56 cells of a published answer in a bundle puzzle's ``tier``,
    assembled, and read all 56 cells back out of the served file with the
    capacity check satisfied and the sweep clean. The capacity ceiling could
    not have caught it — 56 bits is below 100 — and the sweep cannot see a
    12-character token. The *domain* catches it, and this is that control:

    #. the plant really is readable, so the test is not measuring an encoding
       nobody could decode (asserted on the bundle, where it travels);
    #. the served file carries no cell of it at all;
    #. the owner is TOLD — cycle 2 of this card's review (N-4) measured the
       narrowing appearing in no field of the report and in nothing ``main()``
       prints, so a channel being closed looked exactly like a puzzle that
       never had a tier. ``report.narrowed`` is now asserted here and the
       absent case is asserted beside it, so the two are distinguishable.
    """
    grid = GRIDS["min"]
    answer = _bits(grid)
    value = int(answer[:_BASE26_BITS], 2)
    planted = "".join(
        _BASE26[digit]
        for digit in reversed([(value // 26**k) % 26 for k in range(_BASE26_CHARS)])
    )
    assert _base26_cells(planted) == answer[:_BASE26_BITS], "the plant does not decode"
    assert len(planted) < MIN_TOKEN, "the sweep could see this one, so it is the wrong plant"

    root = tmp_path / "bundle"
    keys = write_bundle(root)
    path = root / "puzzle" / f"{keys['min']}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["tier"] = planted
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # The bundle half: the channel exists upstream, which is why it is checked
    # here rather than assumed away.
    assert _base26_cells(json.loads(path.read_text(encoding="utf-8"))["tier"]) == (
        answer[:_BASE26_BITS]
    )

    report = assembler.assemble(root, tmp_path / "site")
    served = json.loads(
        (report.site_dir / "puzzle" / f"{keys['min']}.json").read_text(encoding="utf-8")
    )
    assert served["tier"] == "", served["tier"]
    recovered = _base26_cells(served["tier"])
    assert recovered == "", recovered
    cells = sum(1 for index, bit in enumerate(recovered) if bit == answer[index])
    assert cells == 0, f"{cells} of {_BASE26_BITS} answer cells reached the site"
    # And the rest of the file is still the puzzle, so the fix is a narrowing
    # of one field rather than a refusal of the page.
    assert report.puzzle_count == len(keys)
    assert served["clues"]["rows"] == [_encode(row) for row in grid]

    # The report says so, and says it of this puzzle only: the fixture's other
    # tiers are "easy", "Hard" and "" — two served and one absent-equivalent,
    # none of them a narrowing.
    assert report.narrowed == ((keys["min"], "tier"),), report.narrowed
    assert report.refused == (), report.refused
    # The same bundle with the tier simply MISSING: same served "", and
    # nothing in the report, which is the distinction the field exists for.
    payload.pop("tier")
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    absent = assembler.assemble(root, tmp_path / "site-absent")
    assert json.loads(
        (absent.site_dir / "puzzle" / f"{keys['min']}.json").read_text(encoding="utf-8")
    )["tier"] == ""
    assert absent.narrowed == (), absent.narrowed


def test_the_command_line_says_what_it_dropped_and_what_it_narrowed(tmp_path, capsys) -> None:
    """The report reaches the owner, which is the half ``main()`` owns.

    ``AssembleReport`` carrying a field is not the owner being told: cycle 2
    of this card's review (N-4) found the tier narrowing missing from the
    report AND from everything the CLI prints, and a field nobody prints is
    the same silence one step further in. So both lines are read off the real
    command line here, and the absent-tier run is read beside them, because a
    line that is always printed says nothing either.
    """
    root = tmp_path / "bundle"
    keys = write_bundle(root)
    path = root / "puzzle" / f"{keys['min']}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["tier"] = "requires guessing"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    assert assembler.main(["--bundle", str(root), "--out", str(tmp_path / "site")]) == 0
    printed = capsys.readouterr().out
    assert f"{len(keys)} puzzles into" in printed, printed
    assert "dropped (not in the served schema): title" in printed, printed
    assert f"narrowed {keys['min']}: tier" in printed, printed

    payload.pop("tier")
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    assert assembler.main(["--bundle", str(root), "--out", str(tmp_path / "site2")]) == 0
    absent = capsys.readouterr().out
    assert "narrowed" not in absent, absent
    assert "dropped (not in the served schema): title" in absent, absent


def test_the_served_extents_are_recomputable_from_the_served_clues(site) -> None:
    """Why ``width`` and ``height`` count as zero bits in the capacity figure.

    ``SERVED_VALUE_SPACE`` gives each of them one value, which is only honest
    if the served value is *forced*: a reader with the clues already has both
    extents. ``_clues`` is what forces it, by refusing a payload whose clue
    axes are not exactly that long — the refusal cases ``clues-count`` and
    ``clues-column-count`` in
    ``test_a_puzzle_file_the_schema_cannot_accept_is_refused_and_named`` are
    the other half of this, and this is the positive one: on every served
    file, the equality holds.
    """
    report, keys = site
    checked = 0
    for field, axis in assembler.DETERMINED_BY_CLUES.items():
        for name, key in keys.items():
            payload = json.loads(
                (report.site_dir / "puzzle" / f"{key}.json").read_text(encoding="utf-8")
            )
            assert len(payload["clues"][axis]) == payload[field], (field, name)
            checked += 1
    assert checked == len(assembler.DETERMINED_BY_CLUES) * len(keys) >= 8
    assert sorted(assembler.DETERMINED_BY_CLUES) == ["height", "width"]
    assert all(assembler.SERVED_VALUE_SPACE[field] == 1 for field in assembler.DETERMINED_BY_CLUES)


def test_an_out_dir_that_is_not_a_previous_site_is_refused(monkeypatch, tmp_path) -> None:
    """``--out`` erases its target, so it refuses a target it did not write.

    Measured in cycle 1 of CARD-283's review: a directory holding
    ``precious/notes.txt`` passed as ``--out`` came back holding only the
    site, and ``--out .`` from the repository root would have taken the
    checkout. Both directions here — a target with no marker is refused and
    its files survive, a previous run's tree is replaced without complaint —
    plus the repository root by name and the owner's ``--force`` escape
    hatch.

    **The DENIAL half is CARD-284's fix round, and it is the half that was
    missing.** Until it, the predicate was a name test against
    ``_site_entries()``, and CARD-284's own commit widened that set by five
    names (``index.json``, ``book``, ``b``, ``library``, ``pages.js``) — so a
    directory whose only entry was ``index.json`` became silently deletable.
    The suite pinned what had to be ALLOWED (the positive control below
    re-assembles into a directory that now holds ``index.json``) and nothing
    pinned what had to still be DENIED, so the mutant dropping
    ``SITE_INDEX_FILE`` from the set was killed by the wrong assertion.
    ``check_out_dir`` recognises :data:`assembler.SITE_MARKER_FILE` now, and
    there are **six** denial cases below — fix round 1's docstring said four
    beside a table of five that asserted five, which is cycle 2's F-008.
    Four are drawn from shapes the guard was NOT written from: a lone
    ``index.json``, a lone ``book/``, a lone ``pages.js``, and ``index.json``
    beside a foreign name. Every one of them would have passed the old
    predicate on at least its generic half. The fifth,
    ``every-name-but-the-marker``, is the one case drawn FROM the shape the
    old predicate was written from, and it is the interesting half: the tree
    the old name-set predicate was designed to accept is now refused. The
    sixth is the predicate's EDGE rather than its core and is built
    separately after the table — see there for why it cannot be a row in it.

    The marker's ORDERING is held here too, and separately, because cycle 2
    found nothing in the suite discriminating it (F-006): ``_write`` is made
    to raise on its second call, so ``assemble`` dies after the marker and
    before the tree is finished, and the half-written target must still be
    one the next run may replace. A marker written LAST would pass the
    delete-everything-but-the-marker paragraph identically.

    ``--force`` is an exemption, so it carries its own two controls
    (ADR-0039/R3, and CARD-283 cycle 2's N-5): what it lifts, and what it
    does not. ``assemble`` is called only on ``tmp_path`` targets; the
    repository-root refusal is asserted through ``check_out_dir`` alone, which
    is cycle 2's N-6 and the reason the test cannot delete the checkout even
    if the guard stops firing.
    """
    precious = tmp_path / "deploy"
    (precious / "notes").mkdir(parents=True)
    (precious / "notes" / "important.txt").write_text("keep me", encoding="utf-8")
    with pytest.raises(ValueError, match="no run of this script wrote it"):
        assembler.assemble(None, precious)
    assert (precious / "notes" / "important.txt").read_text(encoding="utf-8") == "keep me"

    # The denial controls the widening shipped without. Each shape is built
    # ONLY out of names an assembled site has, so the old name-set predicate
    # accepted every one of them; each is asserted through `check_out_dir`
    # rather than `assemble`, because `assemble`'s next statement after the
    # guard is `shutil.rmtree`, and a test of a guard must not depend on the
    # guard to avoid deleting its own fixture (CARD-283 cycle 2's N-6).
    denied = {
        "lone-index": [assembler.SITE_INDEX_FILE],
        "lone-book-dir": [f"{assembler.SITE_BOOK_DIR}/{'0' * 10}.json"],
        "lone-page-script": ["pages.js"],
        "index-and-a-stranger": [assembler.SITE_INDEX_FILE, "notes.txt"],
        "every-name-but-the-marker": sorted(
            assembler._site_entries() - {assembler.SITE_MARKER_FILE}
        ),
    }
    for name, members in denied.items():
        target = tmp_path / f"denied-{name}"
        target.mkdir()
        for member in members:
            spot = target / member
            spot.parent.mkdir(parents=True, exist_ok=True)
            spot.write_text("x", encoding="utf-8")
        assert not (target / assembler.SITE_MARKER_FILE).exists(), name
        with pytest.raises(ValueError, match="no run of this script wrote it"):
            assembler.check_out_dir(target)
        # Nothing was deleted on the way to the refusal.
        assert sorted(entry.name for entry in target.iterdir()), name
        # ...and the marker is the ONE thing that separates allowed from
        # denied: the same tree with it is accepted, which is what makes the
        # refusals above a statement about the marker and not about the names.
        (target / assembler.SITE_MARKER_FILE).write_text(
            assembler.SITE_MARKER_TEXT, encoding="utf-8"
        )
        assert assembler.check_out_dir(target) == target, name
    assert len(denied) == 5

    # The SIXTH denial case, and it is the predicate's EDGE rather than its
    # core: `check_out_dir` asks whether the marker is a FILE, and cycle 2 of
    # this card's review measured `.is_file()` -> `.exists()` SURVIVING every
    # row above (its C2-M17), because none of their trees holds a
    # `.player-site` entry at all and the positive controls all write a real
    # file. A DIRECTORY by that name is the one tree that tells the two
    # predicates apart, and what sits behind the difference is
    # `shutil.rmtree`. It cannot be a row in the table above because that
    # loop asserts the marker absent and then writes it as a file, and
    # neither step is true of this shape.
    masquerade = tmp_path / "denied-marker-is-a-directory"
    (masquerade / assembler.SITE_MARKER_FILE / "inner").mkdir(parents=True)
    assert (masquerade / assembler.SITE_MARKER_FILE).exists()
    assert not (masquerade / assembler.SITE_MARKER_FILE).is_file()
    with pytest.raises(ValueError, match="no run of this script wrote it"):
        assembler.check_out_dir(masquerade)
    assert (masquerade / assembler.SITE_MARKER_FILE / "inner").is_dir(), (
        "check_out_dir deleted something on the way to the refusal"
    )
    # ...and the same tree with the marker as a FILE is accepted, so this is
    # a statement about the predicate and not about the name.
    shutil.rmtree(masquerade / assembler.SITE_MARKER_FILE)
    (masquerade / assembler.SITE_MARKER_FILE).write_text(
        assembler.SITE_MARKER_TEXT, encoding="utf-8"
    )
    assert assembler.check_out_dir(masquerade) == masquerade

    # The repository root, through `check_out_dir` ALONE — never through
    # `assemble`. Cycle 2 of this card's review (N-6) found this assertion
    # written against the destructive entry point on the real checkout: the
    # next line of `assemble` after the guard is `shutil.rmtree(site)`, so a
    # change that let the guard stop firing while the call was still reached
    # would delete the worktree from inside the test suite. The function under
    # test is public and pure, so it is called directly.
    #
    # Spelled four ways, because the guard is a resolved-path comparison and
    # the spelling is what a typo varies: the root itself, `player/..`, a
    # symlink to it, and the root with a trailing separator.
    link = tmp_path / "link-to-checkout"
    link.symlink_to(REPO_ROOT)
    for spelling in (REPO_ROOT, REPO_ROOT / "player" / "..", link, Path(f"{REPO_ROOT}/")):
        with pytest.raises(ValueError, match="repository root"):
            assembler.check_out_dir(spelling)
        # --force is the exemption, and this is its bound (N-5, ADR-0039/R3):
        # it absorbs a directory this script did not write, never the
        # checkout. Measured before the fix: force=True returned the root.
        with pytest.raises(ValueError, match="repository root"):
            assembler.check_out_dir(spelling, force=True)
    assert (REPO_ROOT / "pyproject.toml").exists()

    # What --force IS for, so the bound above is a bound and not a wall: the
    # foreign-name refusal is what it lifts.
    assert assembler.check_out_dir(precious, force=True) == precious
    assert (precious / "notes" / "important.txt").exists(), "check_out_dir deleted something"

    # The positive control: an empty directory, and then a previous run's own
    # tree, are both assembled into without complaint.
    empty = tmp_path / "empty"
    empty.mkdir()
    assert assembler.assemble(None, empty).site_dir == empty
    assert (empty / assembler.SITE_MARKER_FILE).read_text(encoding="utf-8") == (
        assembler.SITE_MARKER_TEXT
    )
    again = assembler.assemble(None, empty)
    # The two directories a bundle fills are absent with no bundle; the
    # library index is written anyway, because the site always has a library.
    assert sorted(path.name for path in again.site_dir.iterdir()) == sorted(
        assembler._site_entries()
        - {assembler.SITE_PUZZLE_DIR, assembler.SITE_BOOK_DIR}
    )
    # A run that dies part way through still leaves a target the next run may
    # replace, because the marker is written the moment the directory exists
    # rather than at the end. Measured by deleting everything BUT the marker.
    for path in sorted(again.site_dir.iterdir()):
        if path.name != assembler.SITE_MARKER_FILE:
            shutil.rmtree(path) if path.is_dir() else path.unlink()
    assert assembler.check_out_dir(again.site_dir) == again.site_dir

    # And the ORDERING itself, which the paragraph above does NOT
    # discriminate: a marker written LAST would pass it identically, and
    # cycle 2 of this card's review found no test in the repo that makes
    # `assemble` fail part way (its F-006). So one is made here. `_write`
    # raises on its second call, so the run dies after the marker and before
    # the tree is finished, and the half-written target must still be one the
    # next run may replace. This is the assertion `assemble`'s comment is
    # making, and it is the difference between "a retry works" and "a retry
    # needs --force".
    real_write = assembler._write
    calls = []

    def dying_write(path, payload):
        calls.append(path)
        if len(calls) >= 2:
            raise OSError("disk full, part way through")
        return real_write(path, payload)

    half = tmp_path / "half-written"
    monkeypatch.setattr(assembler, "_write", dying_write)
    with pytest.raises(OSError, match="disk full"):
        assembler.assemble(None, half)
    monkeypatch.undo()
    assert calls[0] == half / assembler.SITE_MARKER_FILE, calls[:1]
    assert len(calls) == 2, calls
    assert (half / assembler.SITE_MARKER_FILE).is_file()
    assert sorted(path.name for path in half.iterdir()) == [
        assembler.SITE_MARKER_FILE
    ], sorted(path.name for path in half.iterdir())
    assert assembler.check_out_dir(half) == half

    # And --force is the way past it, which is what makes the refusal a
    # decision rather than a wall.
    assembler.assemble(None, precious, force=True)
    assert not (precious / "notes").exists()


def test_a_puzzle_file_the_schema_cannot_accept_is_refused_and_named(tmp_path) -> None:
    """Every validator refuses, and says which value it refused.

    Default-deny needs a control per rule or it is a claim about rules nobody
    ran. Each case below is a payload one edit away from valid, **paired with
    the fragment of the reason it must be refused for**.

    That pairing is cycle 2's N-7, and it is the root of the only defect
    family this card hit three times. The loop used to assert that
    ``report.refused[0][1]`` was truthy and nothing about its text, so a case
    refused by a rule OTHER than the one it is named for passed and its own
    rule's control was dead: ``clues-no-room`` was masked by the agreement
    rule in the implementation round, and ``clues-column-count`` by the row
    length check in the first fix round. Both were found only by mutating.
    With the fragment asserted, a case refused for the wrong reason fails on
    its own, and every case added later is self-checking.

    "Every validator" is held to the code and not to the length of this
    table: the refusal branches of the five functions a served file passes
    through are counted in ``assemble.py``'s own source at the end, so a
    branch with no case reds (cycle 3's m-3, where two had none).
    """
    grid = GRIDS["min"]
    good = _bundle_payload(grid, tier="easy", title="Picture")
    cases = {
        "key": ({**good, "key": "NOTAKEY"}, "is not 10 lowercase hex characters"),
        "name": ({**good, "key": _public_key(GRIDS["oblong"])}, "but carries the key"),
        "width": ({**good, "width": MAX_SIZE + 1}, f"width {MAX_SIZE + 1} is outside"),
        "height": ({**good, "height": 0}, "height 0 is outside"),
        # Both ENDS of ``_extent``'s range, not just both axes. Cycle 3
        # measured the asymmetry: `<= MAX_SIZE + 1` dies on the width case,
        # while `MIN_SIZE - 1 <= value` survived the whole module, because 0
        # is still outside a range that starts at 9. This is the same
        # one-end-only hole as the isClueSolved loop bounds, in another
        # function, and `MIN_SIZE - 1` is the only value that reads it.
        "width-low": ({**good, "width": MIN_SIZE - 1}, f"width {MIN_SIZE - 1} is outside"),
        # And ``_extent``'s type branch, which had no case at all: a
        # key-shaped file whose extent is the STRING "10".
        "height-type": ({**good, "height": str(MIN_SIZE)}, "height is not an integer"),
        "clues-shape": (
            {**good, "clues": {"rows": good["clues"]["rows"]}},
            "clues is not an object with exactly rows and columns",
        ),
        # The two length checks DETERMINED_BY_CLUES rests on, one per axis:
        # without them a served extent would no longer be recomputable from
        # the served clues, and SERVED_VALUE_SPACE's one-value count for
        # width/height would be a claim with nothing behind it.
        #
        # Each case is built so the LENGTH is the only thing wrong: both axes
        # still agree on the filled count. The obvious case — the good clues
        # with the last line dropped — is masked, because dropping a line
        # drops its filled cells too and the agreement rule refuses it first.
        # Measured: with the column length check deleted, the dropped-line
        # case left this test and the served-extent test green.
        "clues-count": (
            {
                **good,
                "clues": {
                    "rows": [[1] for _ in range(len(grid) - 1)],
                    "columns": [[1] for _ in range(len(grid[0]) - 1)] + [[0]],
                },
            },
            f"clues.rows is not {len(grid)} lines",
        ),
        "clues-column-count": (
            {
                **good,
                "clues": {
                    "rows": [[1] for _ in grid],
                    "columns": [[2]] + [[1] for _ in range(len(grid[0]) - 2)],
                },
            },
            f"clues.columns is not {len(grid[0])} lines",
        ),
        "clues-empty": (
            {**good, "clues": {**good["clues"], "rows": [[] for _ in grid]}},
            "clues.rows[0] is not a non-empty list",
        ),
        "clues-zero-mixed": (
            {**good, "clues": {**good["clues"], "rows": [[0, 3] for _ in grid]}},
            "clues.rows[0] mixes 0 with other runs",
        ),
        # ``_line``'s run-length type/sign branch, which had no case at all
        # (cycle 3's m-3). It is the only thing keeping arbitrary signed
        # integers out of ``clues`` — the field ADR-0041/R2 EXEMPTS from
        # EC-048 and whose narrowing is the stated reason the exemption is
        # tolerable — and the fit check cannot stand in for it, because
        # `sum + len - 1 > length` never trips on negatives. Measured with the
        # branch deleted: ``_line`` accepted [-1234567890123456789], [-5, -7,
        # 3] and [True, 2] unchanged, with the whole module green.
        "clues-run-sign": (
            {**good, "clues": {**good["clues"], "rows": [[-1] for _ in grid]}},
            "which is not a run length",
        ),
        "clues-too-long": (
            {**good, "clues": {**good["clues"], "rows": [[MIN_SIZE + 1] for _ in grid]}},
            f"clues.rows[0] cannot fit a line of {len(grid[0])} cells",
        ),
        # A clue set with no room for its gaps, whose two axes nevertheless
        # agree on the filled count: [5, 5] needs 11 cells in a 10-cell line,
        # and 10 rows of [5, 5] total the same 100 cells as 10 columns of
        # [10]. So this case is refused by the fits-the-line rule and by
        # nothing else — which is what makes that rule's own control live.
        # Without it the fit check could be deleted and this test stayed green
        # (CARD-283's mutation round, M4b). It shares `clues-too-long`'s
        # fragment because it is the same rule; what differs is that this one
        # is refused by that rule ALONE, which is what makes the rule's own
        # control live.
        "clues-no-room": (
            {
                **good,
                "clues": {
                    "rows": [[MIN_SIZE // 2, MIN_SIZE // 2] for _ in grid],
                    "columns": [[len(grid)] for _ in grid[0]],
                },
            },
            f"clues.rows[0] cannot fit a line of {len(grid[0])} cells",
        ),
        "clues-disagree": (
            {**good, "clues": {**good["clues"], "rows": [[1] for _ in grid]}},
            "clues.rows and clues.columns disagree on the filled count",
        ),
        "not-an-object": ([good], "the file is not a JSON object"),
    }
    for name, (payload, because) in cases.items():
        root = tmp_path / name
        path = root / "puzzle" / f"{good['key']}.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

        report = assembler.assemble(root, tmp_path / f"site-{name}")

        assert report.puzzle_count == 0, name
        assert len(report.refused) == 1 and report.refused[0][0] == good["key"], name
        assert because, f"{name} declares no expected reason"
        # Not "a reason was given" — THIS reason. See the docstring: the
        # weaker assertion is what let two rules' controls die unnoticed.
        assert because in report.refused[0][1], (name, because, report.refused[0][1])
        assert not (report.site_dir / "puzzle").exists(), name
    assert len(cases) >= 16
    # The fragments are distinct per rule, not per case: the only pair that
    # shares one is the two fit-the-line cases above, so a fragment copied
    # across cases to make them pass would show here.
    assert len({because for _, because in cases.values()}) == len(cases) - 1

    # And the docstring's "EVERY validator" held to the code rather than to a
    # count of cases. Cycle 3's m-3 is why: thirteen cases and `len(cases) >=
    # 13` read as a complete sweep while two refusal branches had no case at
    # all. The authority is the number of ``raise ValueError`` statements in
    # the five functions a served file passes through, counted in the source;
    # a sixth validator, or a new branch in one of these, reds here and has to
    # be given a case. It pins the BRANCH SET, not the bounds inside a branch
    # — `width-low` above is what reads one of those.
    refusals = ast.parse((PLAYER_DIR / "assemble.py").read_text(encoding="utf-8"))
    branches = {
        node.name: sum(isinstance(child, ast.Raise) for child in ast.walk(node))
        for node in ast.walk(refusals)
        if isinstance(node, ast.FunctionDef)
        and node.name in ("served_puzzle", "_extent", "_key", "_line", "_clues")
    }
    assert branches == {
        "served_puzzle": 2,
        "_extent": 2,
        "_key": 1,
        "_line": 4,
        "_clues": 4,
    }, branches
    assert sum(branches.values()) == 13 and len(cases) >= sum(branches.values())

    # The control for every one of them: the unedited payload is served.
    root = tmp_path / "good"
    path = root / "puzzle" / f"{good['key']}.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(good), encoding="utf-8")
    assert assembler.assemble(root, tmp_path / "site-good").puzzle_count == 1


def test_the_state_module_and_tokens_are_byte_identical_copies(site) -> None:
    """ADR-0041/R3 — reused by copy, never by fork, and never by edit (G-1).

    Both directions: the served copy equals its source byte for byte, and the
    comparison can tell a one-byte difference from equality (a comparison that
    could not is how a byte-identity claim stops being one).
    """
    report, _ = site
    checked = 0
    for source, published in assembler.COPIED_FROM_ADMIN.items():
        origin = (REPO_ROOT / source).read_bytes()
        served = (report.site_dir / published).read_bytes()
        assert served == origin, published
        assert served != origin + b" ", f"{published}: the comparison is not reading bytes"
        checked += 1
    assert checked == len(assembler.COPIED_FROM_ADMIN) >= 2
    assert "solver_state.js" in assembler.COPIED_FROM_ADMIN["src/nonogram/admin/static/solver_state.js"]


def test_the_static_half_of_the_site_does_not_vary_with_the_puzzles(tmp_path) -> None:
    """No asset but ``puzzle/<key>.json`` moves with what was published.

    Which is the other half of EC-048: a page, a script or a stylesheet that
    changed with the corpus would be carrying something about it. Assembled
    twice from two disjoint corpora and compared byte for byte, with a planted
    difference to show the comparison can fail.

    CARD-284 added two data files that DO vary with the corpus (``index.json``
    and ``book/<slug>.json``), so "the static half" stopped being "not under
    ``puzzle/``" and is now the published paths of the two copy tables —
    :data:`PLAYER_FILES` and :data:`COPIED_FROM_ADMIN`, which is the
    enumerable authority for what the site serves that is NOT a function of
    the bundle (ADR-0039/R2). The change defaults to deny rather than to
    "static": every file in the tree is either one of those published paths
    or one of the three declared data shapes, and a file that is neither
    fails this test instead of quietly dropping out of the comparison.
    """
    first = write_bundle(tmp_path / "b1", {"a": GRIDS["min"]})
    second = write_bundle(tmp_path / "b2", {"b": GRIDS["oblong"], "c": GRIDS["max"]})
    assert set(first.values()).isdisjoint(second.values())
    one = assembler.assemble(tmp_path / "b1", tmp_path / "s1").site_dir
    two = assembler.assemble(tmp_path / "b2", tmp_path / "s2").site_dir

    # The marker belongs to the static half: its text is a constant and
    # carries nothing about the bundle, so it is compared byte for byte with
    # the published assets rather than exempted from the comparison.
    published = {
        *assembler.PLAYER_FILES.values(),
        *assembler.COPIED_FROM_ADMIN.values(),
        assembler.SITE_MARKER_FILE,
    }

    def declared_data(relative: str) -> bool:
        """Whether ``relative`` is one of the three bundle-derived shapes."""
        return (
            relative == assembler.SITE_INDEX_FILE
            or relative.startswith(f"{assembler.SITE_PUZZLE_DIR}/")
            or relative.startswith(f"{assembler.SITE_BOOK_DIR}/")
        )

    def statics(root):
        found = {}
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(root).as_posix()
            if relative in published:
                found[relative] = path.read_bytes()
                continue
            assert declared_data(relative), (
                f"{relative} is neither a published static asset nor one of the "
                "declared bundle-derived shapes, so no rule here covers it"
            )
        return found

    assert statics(one) == statics(two)
    assert len(statics(one)) == len(published) == 1 + len(assembler.PLAYER_FILES) + len(
        assembler.COPIED_FROM_ADMIN
    )
    planted = dict(statics(one))
    planted["play.js"] += b"//"
    assert planted != statics(two), "the comparison would not notice a changed asset"


def test_the_key_recipe_matches_the_exporters() -> None:
    """ADR-0041/R1 has exactly one implementation, and these fixtures use it.

    The local reimplementation above names every bundle file in this module,
    so a disagreement with the exporter would mean these tests exercise a
    namespace the product does not have. The ADR's own worked example is here
    too, as the recipe's independent anchor.
    """
    assert player_bundle.puzzle_key([[True, False], [False, False]]) == _public_key(
        [[True, False], [False, False]]
    )
    assert _public_key([[True, False], [False, False]]) == (
        hashlib.sha256(b"2x2:1000").hexdigest()[:10]
    )
    for name, grid in GRIDS.items():
        assert _public_key(grid) == player_bundle.puzzle_key(grid), name
        assert assembler.KEY_PATTERN.match(_public_key(grid)), name


def test_every_fixture_puzzle_is_uniquely_solvable() -> None:
    """The premise the solved check rests on, measured against the solver.

    "Every clue satisfied" is the solution only for a uniquely solvable
    puzzle. ADR-0032/R1 makes that true of every published puzzle, and
    ``_unique_grid`` makes it true of these fixtures by construction — but
    construction is an argument, and COMP-005 is the authority, so each grid
    goes through the real solver here. Without this, AC-384 would be checking
    a rule whose premise nothing in this file had established.
    """
    for name, grid in GRIDS.items():
        rows = tuple(tuple(_encode(row)) for row in grid)
        columns = tuple(tuple(_encode(column)) for column in zip(*grid))
        assert solve(rows, columns).solution_count == 1, name
    assert len(GRIDS) >= 4


def test_the_clue_satisfaction_rule_agrees_with_the_solution_on_a_corpus() -> None:
    """AC-384's rule, cross-checked against the answer it never sees.

    ``play.js``'s ``isClueSolved`` is reimplemented here in Python — a second
    implementation, as this tree prefers — and run over a seeded corpus of
    boards built from each fixture grid: the solution itself, and the solution
    with one cell moved, added or removed. Satisfied must mean "is the
    solution" in every case, which is only true because the puzzles are
    uniquely solvable (the test above).
    """

    def satisfied(marks, rows, columns):
        height, width = len(marks), len(marks[0])
        for r in range(height):
            if _encode(marks[r]) != rows[r]:
                return False
        for c in range(width):
            if _encode([marks[r][c] for r in range(height)]) != columns[c]:
                return False
        return True

    rng = random.Random(283)
    cases = 0
    for name, grid in GRIDS.items():
        rows = [_encode(row) for row in grid]
        columns = [_encode(column) for column in zip(*grid)]
        assert satisfied(grid, rows, columns), name
        height, width = len(grid), len(grid[0])
        for _ in range(12):
            marks = [list(row) for row in grid]
            r, c = rng.randrange(height), rng.randrange(width)
            marks[r][c] = not marks[r][c]
            assert satisfied(marks, rows, columns) is False, (name, r, c)
            assert marks != grid
            cases += 1
    assert cases >= 48


# ==========================================================================
# The static host: a plain file server, with the deploy config's own rewrite
# ==========================================================================


def rewrites(site_dir: Path):
    """``vercel.json``'s rewrites, as ``(pattern, destination)`` pairs.

    Read from the deploy config rather than hand-written into the fixture
    (ADR-0039/R2): the host's routing for ``/play/<key>`` is a shipped
    artefact, so the test server has to be driven by the same file the host
    is, or it would be testing a route nothing deploys.
    """
    config = json.loads((site_dir / "vercel.json").read_text(encoding="utf-8"))
    pairs = []
    for rule in config["rewrites"]:
        pattern = re.sub(r":([A-Za-z_][A-Za-z0-9_]*)", r"(?P<\1>[^/]+)", rule["source"])
        pairs.append((re.compile(f"^{pattern}/?$"), rule["destination"]))
    assert pairs, "vercel.json declares no rewrite, so /play/<key> resolves to nothing"
    return pairs


class _Host(http.server.SimpleHTTPRequestHandler):
    """The assembled tree over loopback, with the deploy config's rewrites.

    Extensions are mapped explicitly rather than inherited from the host's
    mime database: an ES module served as ``text/plain`` is refused by the
    browser, and ``mimetypes`` reads the system registry, so the one thing
    this fixture must not do is depend on the host for it.
    """

    extensions_map = {
        ".html": "text/html",
        ".js": "text/javascript",
        ".css": "text/css",
        ".json": "application/json",
        "": "application/octet-stream",
    }

    def do_GET(self):  # noqa: N802 — BaseHTTPRequestHandler's name
        path = self.path.split("?", 1)[0]
        if not (Path(self.directory) / path.lstrip("/")).is_file():
            for pattern, destination in self.server.rewrites:
                if pattern.match(path):
                    self.path = destination
                    break
        super().do_GET()

    def log_message(self, *args):
        """Silent: the suite's output is the suite's, not the server's."""


@pytest.fixture
def host(site):
    """The site served on 127.0.0.1 with an ephemeral port. Yields the URL."""
    import socketserver

    report, keys = site
    directory = str(report.site_dir)

    class Server(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True

    handler = type("Handler", (_Host,), {})
    server = Server(("127.0.0.1", 0), lambda *a: handler(*a, directory=directory))
    server.rewrites = rewrites(report.site_dir)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}", report, keys
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def _open(page, host, key):
    url, _, _ = host
    page.goto(f"{url}/play/{key}")
    page.wait_for_function("window.publicPlayer !== undefined")


def _save(key, grid, cells, state="filled"):
    """The localStorage save text for one stroke setting ``cells`` to ``state``.

    The page's own resume format (``play.js`` serialize/deserialize), written
    here independently so a prefilled board is a *public* mechanism rather
    than a test-only API bolted onto the page. Used to put a nearly-solved
    board on screen without 900 clicks.
    """
    return json.dumps(
        {
            "v": 1,
            "key": key,
            "width": len(grid[0]),
            "height": len(grid),
            "rows": [_encode(row) for row in grid],
            "columns": [_encode(column) for column in zip(*grid)],
            "done": [{"cells": [[r, c] for r, c in cells], "state": state}],
            "undone": [],
        }
    )


def _filled_cells(grid):
    return [(r, c) for r, row in enumerate(grid) for c, cell in enumerate(row) if cell]


def _count_preserving_swap(grid):
    """``grid``'s filled cells with one 2x2 rectangle rotated.

    Two filled corners of a rectangle become empty and the other two become
    filled, so **every row sum and every column sum is unchanged** while the
    runs are not. This is the board AC-384 actually needs: a wrong board that a
    solved check comparing filled COUNTS per line would accept.

    It is needed because the obvious wrong board — the solution with one extra
    cell — does *not* need the rule under test. CARD-283's own mutation round
    measured that: ``isClueSolved`` rewritten to compare per-line filled totals
    instead of runs left ``test_solved_fires_on_clue_satisfaction_only``
    GREEN. The control was dead, in exactly the family this board escalates on,
    and this function is the fix.
    """
    height, width = len(grid), len(grid[0])
    for r1, r2, c1, c2 in itertools.product(range(height), range(height), range(width), range(width)):
        if r1 >= r2 or c1 >= c2:
            continue
        if grid[r1][c1] and grid[r2][c2] and not grid[r1][c2] and not grid[r2][c1]:
            swapped = [list(row) for row in grid]
            swapped[r1][c1] = swapped[r2][c2] = False
            swapped[r1][c2] = swapped[r2][c1] = True
            assert [sum(row) for row in swapped] == [sum(row) for row in grid]
            assert [sum(col) for col in zip(*swapped)] == [sum(col) for col in zip(*grid)]
            assert swapped != [list(row) for row in grid]
            return _filled_cells(swapped)
    raise AssertionError("no count-preserving swap exists in this grid")


def _prefill(page, host, key, text):
    """Load the page, plant a save, reload onto it."""
    url, _, _ = host
    page.goto(f"{url}/play/{key}")
    page.evaluate("([k, v]) => window.localStorage.setItem(k, v)", [f"nonogram-public:{key}", text])
    page.goto(f"{url}/play/{key}")
    page.wait_for_function("window.publicPlayer !== undefined")


def _tap(page, row, col):
    page.click(f'td.player-cell[data-row="{row}"][data-col="{col}"]')


def _css_token(name: str) -> str:
    """One ``--token: value`` from ``player/player.css``'s own declaration.

    So an assertion about the phone layout is measured against the number the
    page actually declares (ADR-0039/R2), not against a copy of it in the
    test. The declared value is asserted on its own where it is used, so this
    reading cannot follow a regression down.
    """
    match = re.search(rf"^\s*{re.escape(name)}:\s*([^;]+);", (PLAYER_DIR / "player.css").read_text(encoding="utf-8"), re.M)
    assert match is not None, f"{name} is not declared in player.css"
    return match.group(1).strip()


#: AC-386's tap-target floor, as the page declares it. The card's named mobile
#: guarantee is 28 px; this is where that number comes from.
_CELL_FLOOR_PX = float(_css_token("--player-cell-min").removesuffix("px"))


def _cell_centre(page, row, col):
    box = page.query_selector(f'td.player-cell[data-row="{row}"][data-col="{col}"]').bounding_box()
    return box["x"] + box["width"] / 2, box["y"] + box["height"] / 2


def _drag(page, cells):
    """A real pointer drag across ``cells``: one down, a move per cell, one up.

    ``page.click`` cannot produce this — a drag is the one input that reaches
    ``play.js``'s pointermove/pointerup drag branch, which is where EC-050's
    statement names "a drag" and where cycle 1 of this card's review measured
    a planted POST surviving every test in the card.
    """
    page.mouse.move(*_cell_centre(page, *cells[0]))
    page.mouse.down()
    for cell in cells[1:]:
        page.mouse.move(*_cell_centre(page, *cell))
    page.mouse.up()


def _touch_drag(page, cells, *, end: str = "touchEnd"):
    """A real TOUCH drag across ``cells``, driven through a CDP session.

    ``end="touchCancel"`` ends the stream the way a system gesture does — the
    one input that reaches ``play.js``'s pointercancel handler on purpose
    rather than as a side effect of ``touch-action: auto``.

    Playwright's own input API cannot produce one: ``page.mouse`` reports
    ``pointerType === "mouse"`` and ``page.touchscreen.tap`` is a tap, not a
    drag. ``Input.dispatchTouchEvent`` produces real touch events with real
    pointer ids — ``setPointerCapture`` accepts them, which an earlier
    revision of this file declared it would not, and cycle 2 of this card's
    review measured that declaration false. Chromium only, which is the one
    browser ADR-0038/R7 declares, and the session comes off the page's own
    context, so no dependency is added.

    What this device measures is narrower than it looks, and
    :func:`_pen_drag` exists because of it: with Region off the cells are
    ``touch-action: auto``, so Chromium's own gesture recognizer takes the
    stream over and fires **pointercancel** after the first pointermove
    (measured: ``pointerdown touch`` / ``pointermove touch`` /
    ``pointercancel touch``). So the Region-off half of a touch drag is
    carried by the CSS rule and by ``play.js``'s pointercancel handler, NOT
    by ``gesturePaints`` — which is why the pointer-type rule needs the pen.
    """
    session = page.context.new_cdp_session(page)
    try:
        x, y = _cell_centre(page, *cells[0])
        session.send(
            "Input.dispatchTouchEvent",
            {"type": "touchStart", "touchPoints": [{"x": x, "y": y, "id": 1}]},
        )
        for cell in cells[1:]:
            x, y = _cell_centre(page, *cell)
            session.send(
                "Input.dispatchTouchEvent",
                {"type": "touchMove", "touchPoints": [{"x": x, "y": y, "id": 1}]},
            )
        session.send("Input.dispatchTouchEvent", {"type": end, "touchPoints": []})
    finally:
        session.detach()


def _pen_drag(page, cells):
    """A real PEN drag across ``cells``, driven through a CDP session.

    ``gesturePaints``'s rule is "a mouse drag always marks; a touch **or pen**
    drag marks only while Region is armed", and the pen is the device that
    isolates it: ``Input.dispatchMouseEvent`` takes a ``pointerType``, and a
    pen stream goes through the mouse path, so the compositor does not cancel
    it the way it cancels a ``touch-action: auto`` touch drag. Measured, with
    Region off: ``pointerdown pen`` / ``pointermove pen`` / ``pointermove
    pen`` / ``pointerup pen`` — the whole drag branch reached, with
    ``gesturePaints`` the only thing deciding whether it marks.
    """
    session = page.context.new_cdp_session(page)
    pen = {"pointerType": "pen", "button": "left", "buttons": 1, "clickCount": 1}
    try:
        x, y = _cell_centre(page, *cells[0])
        session.send("Input.dispatchMouseEvent", {"type": "mousePressed", "x": x, "y": y, **pen})
        for cell in cells[1:]:
            x, y = _cell_centre(page, *cell)
            session.send("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x, "y": y, **pen})
        session.send("Input.dispatchMouseEvent", {"type": "mouseReleased", "x": x, "y": y, **pen})
    finally:
        session.detach()


def _state(page, row, col):
    return page.get_attribute(f'td.player-cell[data-row="{row}"][data-col="{col}"]', "data-state")


# ==========================================================================
# Browser tests
# ==========================================================================


@pytest.mark.browser
def test_play_page_renders_and_marks(browser_page, host) -> None:
    """AC-383 — the board renders, and marking matches ``solver_state.js``.

    The transitions are not merely *observed* to be three states: the expected
    sequence is computed in the page by calling the served
    ``solver_state.js``'s own ``clickedState``, so this test fails if the page
    ever stops routing clicks through the module ADR-0041/R3 makes it share
    with the admin player.
    """
    page = browser_page
    url, report, keys = host
    grid = GRIDS["oblong"]
    _open(page, host, keys["oblong"])

    drawn = page.evaluate(
        """() => {
      const text = (box) => [...box.querySelectorAll('.player-clue-num')].map((n) => n.textContent);
      return {
        rows: [...document.querySelectorAll('.player-board tbody tr')]
                .map((tr) => tr.querySelectorAll('td.player-cell').length),
        rowClues: [...document.querySelectorAll('th.player-clue.is-row')].map(text),
        colClues: [...document.querySelectorAll('th.player-clue.is-col')].map(text),
        states: [...new Set([...document.querySelectorAll('td.player-cell')]
                .map((c) => c.dataset.state))],
        title: document.querySelector('[data-player-title]').textContent,
      };
    }"""
    )
    assert drawn["rows"] == [len(grid[0])] * len(grid)
    assert drawn["rowClues"] == [[str(n) for n in _encode(row)] for row in grid]
    assert drawn["colClues"] == [[str(n) for n in _encode(col)] for col in zip(*grid)]
    assert drawn["states"] == ["unknown"]
    assert drawn["title"] == f"Puzzle {len(grid[0])}×{len(grid)}"

    # The three states, against the module's own answer for each step.
    expected = page.evaluate(
        """async () => {
      const m = await import('/solver_state.js');
      const seq = [];
      let state = m.UNKNOWN;
      for (let k = 0; k < 3; k++) { state = m.clickedState(state, m.FILLED, k > 0); seq.push(state); }
      return seq;
    }"""
    )
    assert expected == ["filled", "empty", "unknown"]
    for step, state in enumerate(expected):
        _tap(page, 1, 1)
        assert _state(page, 1, 1) == state, step

    # A drag along the first-move line marks every cell it covers.
    board = page.query_selector('td.player-cell[data-row="3"][data-col="0"]').bounding_box()
    far = page.query_selector('td.player-cell[data-row="3"][data-col="4"]').bounding_box()
    page.mouse.move(board["x"] + board["width"] / 2, board["y"] + board["height"] / 2)
    page.mouse.down()
    for step in range(1, 5):
        at = page.query_selector(f'td.player-cell[data-row="3"][data-col="{step}"]').bounding_box()
        page.mouse.move(at["x"] + at["width"] / 2, at["y"] + at["height"] / 2)
    page.mouse.up()
    assert [_state(page, 3, col) for col in range(5)] == ["filled"] * 5
    assert far["y"] == board["y"], "the drag did not stay on one row"

    # Undo takes the whole drag back as one step; redo puts it back.
    page.click('[data-player-action="undo"]')
    assert [_state(page, 3, col) for col in range(5)] == ["unknown"] * 5
    page.click('[data-player-action="redo"]')
    assert [_state(page, 3, col) for col in range(5)] == ["filled"] * 5

    # Reset clears every mark, and is itself one undo step.
    page.click('[data-player-action="reset"]')
    assert page.evaluate("() => window.publicPlayer.getBoard().cells.every((s) => s === 'unknown')")
    page.click('[data-player-action="undo"]')
    assert [_state(page, 3, col) for col in range(5)] == ["filled"] * 5

    # Every fifth line is the heavier rule, never the last (CARD-160).
    rules = page.evaluate(
        """() => {
      const px = (el, side) => parseFloat(getComputedStyle(el)[`border${side}Width`]);
      const cells = [...document.querySelectorAll('tbody tr:first-child td.player-cell')];
      return cells.map((cell) => px(cell, 'Right'));
    }"""
    )
    heavy = {index for index, width in enumerate(rules) if width == max(rules)}
    assert max(rules) > min(rules)
    assert heavy == {
        index
        for index in range(len(grid[0]))
        if (index + 1) % MAJOR_EVERY == 0 and index + 1 != len(grid[0])
    }


@pytest.mark.browser
def test_solved_fires_on_clue_satisfaction_only(browser_page, host) -> None:
    """AC-384 — solved is every clue satisfied, and nothing weaker.

    The board is prefilled through the page's own save to one cell short of
    the solution, so the **last mark is a real click**, which is what the AC
    says. Then the same board with one extra wrong cell: the identical final
    click must not report solved. The page has no answer to compare against in
    either case — ``window.publicPlayer.isSolved()`` reads the clues.
    """
    page = browser_page
    grid = GRIDS["min"]
    key = host[2]["min"]
    filled = _filled_cells(grid)
    last = filled[-1]
    empty = next(
        (r, c)
        for r in range(len(grid))
        for c in range(len(grid[0]))
        if not grid[r][c]
    )

    _prefill(page, host, key, _save(key, grid, filled[:-1]))
    assert page.evaluate("() => window.publicPlayer.isSolved()") is False
    assert page.is_hidden("[data-player-solved]")

    _tap(page, *last)

    assert page.evaluate("() => window.publicPlayer.isSolved()") is True
    assert page.is_visible("[data-player-solved]")
    assert page.get_attribute("body", "data-solved") == "true"

    # One wrong cell, same final click: not solved.
    _prefill(page, host, key, _save(key, grid, [*filled[:-1], empty]))
    assert page.evaluate("() => window.publicPlayer.isSolved()") is False
    _tap(page, *last)
    assert page.evaluate("() => window.publicPlayer.isSolved()") is False
    assert page.is_hidden("[data-player-solved]")
    assert page.get_attribute("body", "data-solved") == "false"

    # The case that makes this an assertion about CLUES and not about counts:
    # a board with every row's and every column's filled count exactly right
    # and one 2x2 rectangle rotated, so the runs are wrong. A solved check
    # comparing per-line totals would call this solved; the clue rule must not.
    swapped = _count_preserving_swap(grid)
    assert len(swapped) == len(filled)
    _prefill(page, host, key, _save(key, grid, swapped))
    assert page.evaluate("() => window.publicPlayer.getHistory().done.length") == 1, (
        "the save was rejected, so the board under test was never on screen"
    )
    assert page.evaluate("() => window.publicPlayer.isSolved()") is False
    assert page.is_hidden("[data-player-solved]")

    # ------------------------------------------------------------------
    # The rule itself, per line, on boards a real puzzle cannot produce.
    #
    # This table exists because the page-level cases above cannot isolate the
    # rule: on a uniquely solvable puzzle almost every wrong board breaks many
    # lines in many ways, so a WEAKENED check still rejects it and the control
    # reports a pass. CARD-283's mutation round measured exactly that — three
    # separate weakenings of ``isClueSolved`` (compare per-line totals, skip
    # the columns, ignore the order of the runs) all left this test GREEN
    # against real boards. ``isClueSolved`` is a pure function, so it is tested
    # as one: hand-made clue sets where exactly one thing is wrong.
    # ------------------------------------------------------------------
    cases = [
        # (name, width, height, marks, rows, columns, expected)
        ("the clue exactly", 5, 1, "#x###", [[1, 3]], [[1], [0], [1], [1], [1]], True),
        ("whites left undecided", 5, 1, "#.###", [[1, 3]], [[1], [0], [1], [1], [1]], True),
        ("the runs in the wrong order", 5, 1, "###x#", [[1, 3]], [[1], [1], [1], [0], [1]], False),
        ("the right count, the wrong runs", 5, 1, "##x##", [[1, 3]], [[1], [1], [0], [1], [1]], False),
        ("every row right, one column wrong", 2, 2, "#xx#", [[1], [1]], [[2], [0]], False),
        ("every column right, one row wrong", 2, 2, "#xx#", [[2], [0]], [[1], [1]], False),
        # Both ends of both sweeps, one case each, and that is what the four
        # rows below establish — no more. The family was measured twice. Cycle
        # 1 found `row < height - 1` dying on the table above (the single-row
        # cases make the last row the only row) while `col < width - 1`
        # SURVIVED it and the whole module, because no case had its only error
        # in the last column. Cycle 2 then found the OTHER end still open
        # after the last-index pair was added: `let col = 1` survived too,
        # because case 5's columns [[2], [0]] over "#xx#" are BOTH wrong, so
        # skipping column 0 still trips on column 1.
        #
        # So each of these four has its only wrong clue at one named index of
        # one axis, with every other clue of both axes right:
        #
        #   first column -> kills `let col = 1`      (column 0, clue [2] / [1])
        #   last column  -> kills `col < width - 1`  (column 1, clue [2] / [1])
        #   first row    -> kills `let row = 1`      (row 0, clue [2] / [1])
        #   last row     -> kills `row < height - 1` (row 1, clue [2] / [1])
        #
        # All four mutants were fired against this table and each one reds on
        # the case named beside it. The claim is exactly that: the four
        # off-by-one mutants of `isClueSolved`'s two loop bounds are each
        # refused. It is not a claim about every weakening of the sweeps —
        # the three the cycle-1 round measured (per-line totals, skipping the
        # columns, ignoring run order) are carried by the cases above.
        ("every row right, the FIRST column wrong", 2, 2, "#xx#", [[1], [1]], [[2], [1]], False),
        ("every row right, the LAST column wrong", 2, 2, "#xx#", [[1], [1]], [[1], [2]], False),
        ("every column right, the FIRST row wrong", 2, 2, "#xx#", [[2], [1]], [[1], [1]], False),
        ("every column right, the LAST row wrong", 2, 2, "#xx#", [[1], [2]], [[1], [1]], False),
        # And the conjunct one step to the LEFT of those two loop bounds: the
        # length comparison inside ``sameNumbers``. Cycle 3 measured it
        # uncontrolled — dropping `a.length === b.length` announced a 4x4
        # UNIQUELY SOLVABLE board SOLVED while one cell short, and reversing
        # the comparison to `b.every(...)` announced one with an extra mark
        # solved, both with the whole module green. The ten rows above cannot
        # reach either weakening: they are all 5x1 or 2x2, where a wrong board
        # makes some line read `[0]`, and `[0]` is neither a prefix nor an
        # extension of a nonzero clue. These two are built so NO line is empty
        # and exactly one line's runs are a strict PREFIX of its clue (the
        # first) or a strict EXTENSION of it (the second):
        #
        #   short of its clue -> kills `a.every(...)` (row runs [1] prefix [1, 3])
        #   past its clue     -> kills `b.every(...)` (row runs [1, 1] extend [1])
        #
        # Each kills one direction and survives the other, so these are two
        # live controls and not one row carrying both.
        ("a line short of its clue", 5, 1, "#xxxx", [[1, 3]], [[1], [0], [0], [0], [0]], False),
        ("a line past its clue", 5, 1, "#x#xx", [[1]], [[1], [0], [1], [0], [0]], False),
        ("an empty line, empty", 5, 1, "xxxxx", [[0]], [[0], [0], [0], [0], [0]], True),
        ("an empty line, marked", 5, 1, "#xxxx", [[0]], [[1], [0], [0], [0], [0]], False),
        # A "?" is not a filled cell, so it breaks no run it does not sit in.
        # The public page has no Maybe brush at all, so this board is only
        # reachable from a hand-edited save; it is here as a decision on the
        # record rather than an untested corner. Clue satisfaction is the
        # whole rule (ADR-0041), and a board whose FILLED cells are the
        # solution is solved whatever notes sit on its white cells — which is
        # a deliberate divergence from the admin player's isSolved, where any
        # "?" means not solved because that function compares with the answer.
        ("a note on a white cell", 5, 1, "#?###", [[1, 3]], [[1], [0], [1], [1], [1]], True),
    ]
    answers = page.evaluate(
        """async (cases) => {
      const play = await import('/play.js');
      const m = await import('/solver_state.js');
      const of = { '#': m.FILLED, 'x': m.EMPTY, '.': m.UNKNOWN, '?': m.MAYBE };
      return cases.map(([name, width, height, marks, rows, columns]) => {
        const board = Object.freeze({
          width, height,
          cells: Object.freeze([...marks].map((ch) => of[ch])),
        });
        if (!m.isBoard(board)) throw new Error(`${name}: not a board`);
        return play.isClueSolved(board, rows, columns);
      });
    }""",
        [list(case[:-1]) for case in cases],
    )
    assert answers == [case[-1] for case in cases], [
        (case[0], got, case[-1]) for case, got in zip(cases, answers) if got != case[-1]
    ]
    assert len(cases) >= 15 and sum(case[-1] for case in cases) == 4

    # And the solved state is a function of the board, not of history: undoing
    # the last mark on a solved board takes the banner away again.
    _prefill(page, host, key, _save(key, grid, filled[:-1]))
    _tap(page, *last)
    page.click('[data-player-action="undo"]')
    assert page.evaluate("() => window.publicPlayer.isSolved()") is False
    assert page.is_hidden("[data-player-solved]")


@pytest.mark.browser
def test_the_empty_mark_is_a_dot_and_solving_is_revealed(browser_page, host) -> None:
    """The owner's two calls of 2026-10-30, held where each one can drift.

    **The empty mark is a dot.** It was a cross here — two linear-gradient
    strokes painted into the cell's background — while the admin player drew
    a centred dot, so the same mark meant one thing in the panel and another
    on the public page. The dot is asserted through the ``::after`` box and
    the cell's own ``background-image``, not through the declaration: a rule
    that stops applying (an override, a specificity change, a later edit that
    puts the cross back as a background) reds here.

    **Solving is revealed, not merely recorded.** The page set a success
    frame and showed a banner; the panel also plays a reveal, and the owner
    asked for it. Two animations, and both are asserted through the
    *computed* ``animation-*`` properties rather than through
    ``getAnimations()``: a running animation is gone from that list once it
    finishes, so a test that reads it races the 440 ms it is testing. The
    computed delay is what makes the sweep a sweep — it varies per cell with
    ``--player-wave`` (row + col, set in ``play.js``) — and it is a value, so
    it can be asserted exactly.

    The negative half matters as much: while the board is NOT solved the same
    cell animates nothing, so the reveal is keyed on solving rather than on
    being drawn.
    """
    page = browser_page
    grid = GRIDS["min"]
    key = host[2]["min"]
    filled = _filled_cells(grid)
    blanks = [
        (r, c)
        for r in range(len(grid))
        for c in range(len(grid[0]))
        if not grid[r][c]
    ]

    # ---- the empty mark -------------------------------------------------
    _prefill(page, host, key, _save(key, grid, blanks, state="empty"))
    mark = page.evaluate(
        """() => {
      const cell = document.querySelector('.player-cell[data-state="empty"]');
      const after = getComputedStyle(cell, '::after');
      const box = cell.getBoundingClientRect();
      return {
        content: after.content,
        widthRatio: parseFloat(after.width) / box.width,
        heightRatio: parseFloat(after.height) / box.height,
        radius: after.borderRadius,
        colour: after.backgroundColor,
        cellBackgroundImage: getComputedStyle(cell).backgroundImage,
        secondary: getComputedStyle(document.documentElement)
          .getPropertyValue('--color-text-secondary').trim(),
      };
    }"""
    )
    assert mark["content"] in ('""', "''"), mark["content"]
    assert 0.24 <= mark["widthRatio"] <= 0.32, mark
    assert 0.24 <= mark["heightRatio"] <= 0.32, mark
    assert mark["radius"].startswith("50%"), mark["radius"]
    # A round mark in the secondary ink, and NOT the cross: the cross was a
    # pair of gradients on the cell itself, so an empty cell's own
    # background-image has to be nothing at all.
    assert mark["cellBackgroundImage"] == "none", mark["cellBackgroundImage"]
    assert mark["colour"] not in ("rgba(0, 0, 0, 0)", "transparent"), mark["colour"]
    assert mark["secondary"], "tokens.css did not reach the page"

    # ---- the reveal -----------------------------------------------------
    # One cell short of the solution, so the board becomes solved by a click,
    # which is the transition the reveal is keyed on.
    _prefill(page, host, key, _save(key, grid, filled[:-1]))
    before = page.evaluate(
        """() => {
      const cell = document.querySelector('.player-cell[data-state="filled"]');
      return getComputedStyle(cell).animationName;
    }"""
    )
    assert before == "none", before

    _tap(page, *filled[-1])
    assert page.get_attribute("body", "data-solved") == "true"

    reveal = page.evaluate(
        """() => {
      const cells = [...document.querySelectorAll('.player-cell[data-state="filled"]')];
      const read = (el) => {
        const style = getComputedStyle(el);
        return {
          name: style.animationName,
          delay: style.animationDelay,
          duration: style.animationDuration,
          wave: el.style.getPropertyValue('--player-wave'),
          row: Number(el.dataset.row),
          col: Number(el.dataset.col),
        };
      };
      const banner = getComputedStyle(document.querySelector('[data-player-solved]'));
      return {
        cells: cells.map(read),
        banner: { name: banner.animationName, duration: banner.animationDuration },
      };
    }"""
    )
    assert reveal["banner"]["name"] == "player-solved-in", reveal["banner"]
    assert reveal["cells"], "no filled cell on a solved board"
    for cell in reveal["cells"]:
        assert cell["name"] == "player-solved-flash", cell
        # The sweep: the delay IS the cell's diagonal, 12 ms a step. Compared
        # as seconds and not as text -- Chrome writes a zero delay "0s", not
        # "0.0s", and the unit is the browser's to choose.
        assert cell["wave"] == str(cell["row"] + cell["col"]), cell
        assert cell["delay"].endswith("s"), cell
        assert float(cell["delay"].removesuffix("s")) == pytest.approx(
            (cell["row"] + cell["col"]) * 0.012
        ), cell
    delays = {cell["delay"] for cell in reveal["cells"]}
    assert len(delays) > 1, f"every cell flashes at once, so it is not a sweep: {delays}"

    # ---- and none of it under prefers-reduced-motion --------------------
    page.emulate_media(reduced_motion="reduce")
    try:
        _prefill(page, host, key, _save(key, grid, filled[:-1]))
        _tap(page, *filled[-1])
        assert page.get_attribute("body", "data-solved") == "true"
        still = page.evaluate(
            """() => {
          const cell = document.querySelector('.player-cell[data-state="filled"]');
          const banner = document.querySelector('[data-player-solved]');
          return {
            cell: getComputedStyle(cell).animationName,
            banner: getComputedStyle(banner).animationName,
            frame: getComputedStyle(document.querySelector('.player-board')).outlineStyle,
            bannerShown: !banner.hidden,
          };
        }"""
        )
    finally:
        page.emulate_media(reduced_motion="no-preference")
    assert still["cell"] == "none" and still["banner"] == "none", still
    # The reveal is still a reveal: the frame and the banner do not move.
    assert still["bannerShown"] is True and still["frame"] == "solid", still


@pytest.mark.browser
def test_resume_is_local_and_the_page_writes_nowhere(browser_page, host) -> None:
    """AC-385 — marks come back after a reload, from this browser only.

    Both halves in one test because the AC is one sentence: the marks are
    restored, and no request other than this page's own static assets was
    ever issued. Every request the context makes is recorded, including the
    ones the reload makes, and each one is held to the site's own origin and
    to GET.
    """
    page = browser_page
    url, report, keys = host
    grid = GRIDS["min"]
    key = keys["min"]
    seen: list[tuple[str, str]] = []
    page.context.on("request", lambda request: seen.append((request.method, request.url)))

    _open(page, host, key)
    for row, col in ((0, 0), (0, 1), (2, 3)):
        _tap(page, row, col)
    marked = {(row, col): _state(page, row, col) for row, col in ((0, 0), (0, 1), (2, 3))}
    assert set(marked.values()) == {"filled"}

    stored = page.evaluate("(k) => window.localStorage.getItem(k)", f"nonogram-public:{key}")
    assert stored is not None, "nothing was saved, so there is nothing to resume from"
    assert "solution" not in stored and "grid" not in stored

    page.reload()
    page.wait_for_function("window.publicPlayer !== undefined")
    assert {(row, col): _state(page, row, col) for row, col in marked} == marked
    assert page.evaluate("() => window.publicPlayer.getHistory().done.length") == 3

    assert seen, "no request was recorded, so this half of the AC measured nothing"
    assert [method for method, _ in seen] == ["GET"] * len(seen)
    assert all(request.startswith(url + "/") for _, request in seen), seen
    served = {
        path.relative_to(report.site_dir).as_posix() for path in report.site_dir.rglob("*") if path.is_file()
    }
    for _, request in seen:
        path = request[len(url) + 1 :].split("?", 1)[0]
        assert path in served or path == f"play/{key}", path


@pytest.mark.browser
def test_phone_viewport_is_playable(browser_page, host) -> None:
    """AC-386 — 390 px wide, ``MAX_SIZE`` per side, and still playable.

    Four readings, because "playable" is four things: the page itself never
    scrolls sideways, the cells are big enough for a thumb, the clue numerals
    are drawn, and the far corner can be reached. The last one is the
    accepted trade-off stated in ``player.css``: 30 cells do not fit 390 px at
    a tappable size, so the BOARD scrolls inside its stage while the page
    does not — and the clue gutters stay in view while it does.
    """
    page = browser_page
    grid = GRIDS["max"]
    page.set_viewport_size({"width": 390, "height": 844})
    _open(page, host, host[2]["max"])

    reading = page.evaluate(
        """() => {
      const stage = document.querySelector('[data-player-stage]');
      const cell = document.querySelector('td.player-cell');
      const rowClue = document.querySelector('th.player-clue.is-row');
      const colClue = document.querySelector('th.player-clue.is-col');
      const box = cell.getBoundingClientRect();
      return {
        pageScroll: document.documentElement.scrollWidth - document.documentElement.clientWidth,
        cellWidth: box.width, cellHeight: box.height,
        stageScrollable: stage.scrollWidth > stage.clientWidth,
        rowClueSticky: getComputedStyle(rowClue).position,
        colClueSticky: getComputedStyle(colClue).position,
        clueFont: parseFloat(getComputedStyle(colClue).fontSize),
        clueText: colClue.textContent.trim(),
        viewport: document.querySelector('meta[name=viewport]').content,
        cells: document.querySelectorAll('td.player-cell').length,
      };
    }"""
    )
    assert reading["cells"] == MAX_SIZE * MAX_SIZE
    assert reading["pageScroll"] <= 0, reading
    # The floor is the page's own token, read from the file rather than
    # hand-picked — and the token's VALUE is asserted too, because an
    # assertion against the token alone would follow the token down. Cycle 1
    # of this card's review measured exactly that gap: the assertion was
    # `>= 24` while the card, the token and the mutation record all said
    # 28 px, so a 25 px token passed.
    assert _CELL_FLOOR_PX >= 28, _CELL_FLOOR_PX
    assert reading["cellWidth"] >= _CELL_FLOOR_PX, (reading, _CELL_FLOOR_PX)
    assert reading["cellHeight"] >= _CELL_FLOOR_PX, (reading, _CELL_FLOOR_PX)
    assert reading["stageScrollable"] is True, "nothing to pan: the reading below is vacuous"
    assert reading["rowClueSticky"] == "sticky" and reading["colClueSticky"] == "sticky"
    assert reading["clueFont"] >= 10 and reading["clueText"] != ""
    assert "user-scalable=no" not in reading["viewport"]
    assert "maximum-scale" not in reading["viewport"]

    # The far corner is reachable, and the clues are still there when it is.
    far = page.evaluate(
        """() => {
      const stage = document.querySelector('[data-player-stage]');
      stage.scrollLeft = stage.scrollWidth;
      stage.scrollTop = stage.scrollHeight;
      const last = [...document.querySelectorAll('td.player-cell')].at(-1);
      const cellBox = last.getBoundingClientRect();
      const stageBox = stage.getBoundingClientRect();
      const rowClue = document.querySelector('th.player-clue.is-row').getBoundingClientRect();
      return {
        inView: cellBox.right <= stageBox.right + 1 && cellBox.left >= stageBox.left - 1,
        rowClueInView: rowClue.right > stageBox.left && rowClue.left < stageBox.right,
        pageScroll: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      };
    }"""
    )
    assert far["inView"], far
    assert far["rowClueInView"], "the row clues did not stay in view while panning"
    assert far["pageScroll"] <= 0

    # And a tap on the far cell marks it, which is what "reachable" is for.
    page.click(".player-board tbody tr:last-child td.player-cell:last-child")
    assert _state(page, MAX_SIZE - 1, MAX_SIZE - 1) == "filled"


@pytest.mark.browser
def test_the_stage_fits_the_board_on_a_wide_screen(browser_page, host) -> None:
    """The bordered stage is the board's box, not the page's — and still scrolls.

    Nothing in this card read the desktop layout at all, and cycle 1 of its
    review measured the consequence: at 1440 px the stage was 1408 px wide
    beside a 465 px board, so 942 px of empty bordered box sat to the right of
    the 10x10. ``width: fit-content`` is the fix, and both halves of it are
    read here, because the phone behaviour is what the width was defending:

    #. wide screen, small board — the stage is the board's width, not the
       page's, and there is nothing to scroll;
    #. phone, largest board — the stage is clamped to the viewport and the
       board scrolls INSIDE it, with the page still not scrolling sideways
       (AC-386's trade-off, re-read here against the same change).
    """
    page = browser_page
    page.set_viewport_size({"width": 1440, "height": 900})
    _open(page, host, host[2]["min"])
    wide = page.evaluate(
        """() => {
      const stage = document.querySelector('[data-player-stage]');
      const board = document.querySelector('.player-board');
      return {
        stage: stage.getBoundingClientRect().width,
        board: board.getBoundingClientRect().width,
        page: document.documentElement.clientWidth,
        scrollable: stage.scrollWidth > stage.clientWidth,
      };
    }"""
    )
    assert wide["page"] >= 1400, wide
    assert wide["board"] < wide["page"] / 2, wide  # the 10x10 is a small board
    # The stage is the board plus its own 1 px rules, never the page.
    assert wide["stage"] - wide["board"] <= 4, wide
    assert wide["scrollable"] is False, wide

    page.set_viewport_size({"width": 390, "height": 844})
    _open(page, host, host[2]["max"])
    phone = page.evaluate(
        """() => {
      const stage = document.querySelector('[data-player-stage]');
      const board = document.querySelector('.player-board');
      return {
        stage: stage.getBoundingClientRect().width,
        board: board.getBoundingClientRect().width,
        page: document.documentElement.clientWidth,
        scrollable: stage.scrollWidth > stage.clientWidth,
        pageScroll: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      };
    }"""
    )
    assert phone["board"] > phone["page"], phone  # 30 cells do not fit 390 px
    assert phone["stage"] <= phone["page"], phone
    assert phone["scrollable"] is True, phone
    assert phone["pageScroll"] <= 0, phone


@pytest.mark.browser
def test_no_write_request_for_any_interaction(browser_page, host) -> None:
    """EC-050 / ADR-0041/R4 — for every interaction, zero writes leave the page.

    "Every interaction sequence" is approximated in two passes over the same
    control set, and the first pass is the one that makes the approximation
    honest: **every control is driven once, deterministically**, and then a
    seeded walk runs over the set. The exercised set is asserted EQUAL to the
    control set, so a reseed — or a control added to the page and not to this
    table — reds here instead of quietly dropping a path.

    That assertion is the fix for a measured hole. Cycle 1 of this card's
    review found the seeded draw never produced Reset (``Random(2831)``'s 24
    draws from 8 simply do not contain 6) and contained no drag at all, both
    of which EC-050's statement names by word: a ``fetch(POST)`` planted in
    the reset handler, and the same planted in the drag branch, each left this
    test and the whole module GREEN. Three of the controls below therefore
    also assert that the path was really reached — the drag marks its line,
    Region's state flips, Reset announces itself — because "the control was
    clicked" is not "the handler ran".

    The assertion about requests is on the METHOD, the ORIGIN and the PATH of
    every one — not on a count, because a count passes when nothing happened
    at all, so the number of interactions is asserted too. The path half is
    cycle 3's M-2: method and origin alone are satisfied by a same-origin GET
    of the whole board, and the sibling test three tests up the file already
    held requests to the served file set while never pressing Reset, dragging
    or using the keys.
    """
    page = browser_page
    url, report, keys = host
    key = keys["min"]
    writes: list[tuple[str, str]] = []
    requests: list[str] = []

    def record(request):
        requests.append(request.url)
        if request.method != "GET":
            writes.append((request.method, request.url))

    page.context.on("request", record)
    _open(page, host, key)
    after_load = len(requests)

    def drag_a_line():
        page.click('[data-player-tool="filled"]')
        _drag(page, [(5, 0), (5, 1), (5, 2)])
        marked = [_state(page, 5, col) for col in range(3)]
        assert marked == ["filled"] * 3, f"the drag marked nothing: {marked}"

    def toggle_region():
        before = page.evaluate("() => window.publicPlayer.isRegion()")
        page.click("[data-player-region]")
        assert page.evaluate("() => window.publicPlayer.isRegion()") is not before

    def press_reset():
        # force=True on purpose here and below: an aria-disabled button is one
        # of the interactions this test must cover, and Playwright's
        # actionability check would otherwise refuse to press it at all.
        page.click('[data-player-action="reset"]', force=True)
        announced = page.inner_text("[data-player-announce]").strip()
        assert announced.startswith("Board reset"), f"the reset handler did not run: {announced!r}"

    #: Every control the page has, by the thing a player does. The page's own
    #: markup is the authority for what exists: ``test_every_player_control_is
    #: _in_the_ec_050_walk`` holds this table to the buttons in play.html, so a
    #: fourth brush or a new action cannot be added without being walked — and
    #: holds ``play.js``'s own listener set and its one request separately,
    #: because markup cannot see a key binding (cycle 2's N-3).
    controls = {
        "brush-black": lambda: page.click('[data-player-tool="filled"]'),
        "brush-white": lambda: page.click('[data-player-tool="empty"]'),
        "brush-clear": lambda: page.click('[data-player-tool="unknown"]'),
        "region": toggle_region,
        "tap": lambda: _tap(page, rng.randrange(MIN_SIZE), rng.randrange(MIN_SIZE)),
        "drag": drag_a_line,
        "undo-button": lambda: page.click('[data-player-action="undo"]', force=True),
        "redo-button": lambda: page.click('[data-player-action="redo"]', force=True),
        "reset": press_reset,
        "undo-key": lambda: page.keyboard.press("Control+z"),
        "redo-key": lambda: page.keyboard.press("Control+Shift+z"),
    }

    rng = random.Random(2831)
    exercised: list[str] = []
    # Pass one: every control, once, in a fixed order.
    for name, drive in controls.items():
        drive()
        exercised.append(name)
    # Pass two: a seeded walk over the same set, for sequences the sweep's
    # fixed order cannot reach.
    order = sorted(controls)
    for _ in range(24):
        name = order[rng.randrange(len(order))]
        controls[name]()
        exercised.append(name)
    page.reload()
    page.wait_for_function("window.publicPlayer !== undefined")

    assert set(exercised) == set(controls), sorted(set(controls) - set(exercised))
    assert len(exercised) == len(controls) + 24 >= 35
    assert writes == []
    assert len(requests) > after_load, "the reload issued nothing, so nothing was watched"
    assert all(request.startswith(url + "/") for request in requests), requests
    # The one request kind this page makes at all, named: its own assets.
    assert any(request.endswith(f"/puzzle/{key}.json") for request in requests)
    # And every request held to the SET of files this site serves, not only to
    # GET and to the origin. ``test_resume_is_local_and_the_page_writes
    # _nowhere`` already carried this assertion three tests up the file;
    # cycle 3 measured what the weaker pair here let through. A same-origin
    # GET exfil of the whole board, planted in the *walked* reset handler —
    # `globalThis.fetch.bind(globalThis)("/collect?b=" + cells)`, `new
    # Image().src = ...`, `import("/collect.js?b=" + cells)` — shipped all 100
    # cells on every Reset with the whole module green, because a safe method
    # to this page's own origin satisfied both of the assertions above. The
    # walk is the test that presses Reset, toggles Region, drags and uses the
    # keys, so the allowlist belongs here and not only there.
    served = {
        path.relative_to(report.site_dir).as_posix() for path in report.site_dir.rglob("*") if path.is_file()
    }
    for request in requests:
        # The query string is deliberately NOT stripped (the sibling strips
        # it): a SERVED path carrying the board in its query is the one exfil
        # shape a path allowlist alone cannot see, and this page asks for
        # nothing with a query at all. `assert any(... .json)` above is the
        # positive control that this loop is reading real requests.
        assert request[len(url) + 1 :] in served or request == f"{url}/play/{key}", request
    # One shape further out, because a path allowlist reads the URL and a
    # request has more than a URL: the board can ride out in a HEADER on this
    # page's own allowlisted asset request. Measured here — `document.cookie =
    # "b=" + cells` in the reset handler ships all 100 cells on the next
    # `/puzzle/<key>.json` fetch and leaves every assertion above green. The
    # page stores play state in localStorage by ADR-0041/R4 and has no reason
    # to set a cookie at all, so "no cookie" is the whole of it, and the walk
    # has driven every control before it is read.
    assert page.context.cookies() == [], page.context.cookies()


def test_every_player_control_is_in_the_ec_050_walk() -> None:
    """EC-050's walk is held to the page's own controls (ADR-0039/R1-R2).

    The walk above drives a named table of controls. A table is a hand-written
    set unless something holds it to an authority the runtime enumerates, so
    this reads ``play.html``'s buttons — the brushes by ``data-player-tool``,
    the actions by ``data-player-action``, Region by its own attribute — and
    insists every one of them is walked. A fourth brush or a new action added
    to the page reds here, which is the completeness half ADR-0039/R1 asks for
    before the set is trusted.

    The two keyboard paths are the exception the rule allows: they are not
    elements, so they are listed rather than derived, and they are named in
    the page as ``aria-keyshortcuts`` on the two buttons they duplicate —
    which this test checks, so "listed" is still held to the markup.

    Markup is not the whole authority, and cycle 2 of this card's review
    measured the gap: a second branch in ``play.js``'s keydown listener that
    POSTs is a new player-visible control writing to a server, and no element
    changes, so all 31 tests stayed green. The second half of this test is
    therefore held to ``play.js`` itself — its registered event types, the one
    key its keydown handler may read, and the one request the file is allowed
    to make at all. What that covers and what it does not is stated with each
    assertion; it is a narrower authority than "every interaction sequence",
    and the gap that remains is named at the end.
    """
    page_html = (PLAYER_DIR / "play.html").read_text(encoding="utf-8")
    walked = {
        "brush-black": "filled",
        "brush-white": "empty",
        "brush-clear": "unknown",
    }
    tools = set(re.findall(r'data-player-tool="([a-z]+)"', page_html))
    actions = set(re.findall(r'data-player-action="([a-z]+)"', page_html))
    assert tools == set(walked.values()), tools
    assert actions == {"undo", "redo", "reset"}, actions
    assert "data-player-region" in page_html
    # The names the walk uses, derived from the same markup: one per brush,
    # one per action button, plus region, tap, drag and the two key paths.
    expected = (
        set(walked)
        | {f"{action}-button" for action in actions if action != "reset"}
        | {"reset", "region", "tap", "drag", "undo-key", "redo-key"}
    )
    assert len(expected) == 11, sorted(expected)
    assert "aria-keyshortcuts=\"Control+Z Meta+Z\"" in page_html
    assert "aria-keyshortcuts=\"Shift+Control+Z Shift+Meta+Z\"" in page_html
    source = Path(__file__).read_text(encoding="utf-8")
    parts = source.split("\ndef test_no_write_request_for_any_interaction")
    assert len(parts) == 2, "the walk is not where this test looks for it"
    walk = parts[1].split("\ndef ")[0]
    named = set(re.findall(r'^\s{8}"([a-z-]+)": ', walk, re.M))
    assert named == expected, sorted(expected ^ named)

    # ------------------------------------------------------------------
    # The listener half (cycle 2's N-3): the controls that are not markup.
    # ------------------------------------------------------------------
    script = (PLAYER_DIR / "play.js").read_text(encoding="utf-8")
    #: Every event type ``play.js`` binds, by registration. The four stage
    #: pointer events are the drag (``tap``/``drag`` above drive the first
    #: three; ``pointercancel`` is driven by
    #: ``test_a_touch_or_pen_drag_marks_only_while_region_is_armed``), and the
    #: click count is the markup's rather than a number: one shared handler in
    #: the loop over ``[data-player-tool]``, one on Region, and one per action
    #: button. A new event type, or a second handler on an existing one, reds.
    registered = sorted(re.findall(r'addEventListener\("([a-z]+)"', script))
    assert registered == sorted(
        ["pointerdown", "pointermove", "pointerup", "pointercancel", "keydown"]
        + ["click"] * (2 + len(actions))
    ), registered

    # The keydown handler's guard, pinned to the one key it may read: the
    # planted second branch compared `event.key` to "r", and a key binding is
    # the one control shape the markup authority above cannot see.
    halves = script.split('document.addEventListener("keydown"')
    assert len(halves) == 2, "play.js does not bind keydown exactly once"
    handler = halves[1].split("\n  });", 1)[0]
    assert re.findall(r'event\.key[^;]*?"([a-z]+)"', handler) == ["z"], handler
    assert sorted(set(re.findall(r"event\.([a-zA-Z]+)", handler))) == [
        "ctrlKey",
        "key",
        "metaKey",
        "preventDefault",
        "shiftKey",
    ], handler

    # And EC-050's own word, as a flat property of the file: ``play.js`` makes
    # exactly ONE request, and it is the puzzle file by GET. This is what
    # closes the planted POST whatever control reaches it — a branch that
    # writes without reading `event` at all is still refused here, which the
    # two assertions above would not catch.
    assert re.findall(r"\bfetch\(", script) == ["fetch("], "play.js makes more than one request"
    assert 'fetch(`/puzzle/${key}.json`, { cache: "no-store" })' in script
    for forbidden in ("XMLHttpRequest", "sendBeacon", "WebSocket", "EventSource", "method:"):
        assert forbidden not in script, forbidden
        assert forbidden not in page_html, forbidden
    # The residual, named by its SHAPE rather than enumerated: this holds the
    # SHAPE of play.js's writes and the SET of its listeners, not every
    # interaction sequence. A write smuggled through an element attribute in
    # play.html (a form action, an img src) is covered by
    # ``test_the_page_carries_no_answer_and_no_third_party_asset``'s
    # same-origin assertion and by the walk's recorded requests.
    #
    # The earlier version of this sentence said the one thing outside all
    # three was "a write a future file other than play.js makes", and cycle 3
    # measured that false: a safe-method, same-origin request from play.js
    # itself, reached through a name other than ``fetch(`` (a rebound
    # ``fetch``, ``new Image().src``, a dynamic ``import()``), satisfied every
    # assertion here and shipped all 100 cells from a WALKED control. The
    # walk now holds every request to the served file set — query included —
    # and the context to no cookie, which is where those shapes die. So what
    # the three authorities together still miss is stated by shape: a channel
    # the context's request recorder cannot see at all, leaving nothing in a
    # method, an origin, a URL or a cookie; and a write made by a file other
    # than play.js or play.html.
    assert set(assembler.PLAYER_FILES) >= {"play.js", "play.html"}, assembler.PLAYER_FILES


@pytest.mark.browser
def test_a_save_or_a_puzzle_file_the_page_cannot_trust_is_refused(browser_page, host) -> None:
    """The page checks its two inputs rather than trusting them, and both halves
    of that were unexercised (cycle 1 of this card's review, F-4 A and B).

    Two mechanisms, each with its own positive control:

    #. ``deserialize``'s clue comparison — "a re-export that changed a
       puzzle's clues under the same key cannot replay marks onto a different
       puzzle" (``play.js``'s own words). A save carrying another 10x10's
       clues under this puzzle's key must be dropped, leaving a blank board,
       while the same save with the right clues restores its stroke;
    #. ``readPayload``'s clue checks — the page's half of the deliberately
       duplicated "checked rather than trusted" rule. A key-shaped file whose
       row clue cannot fit its line must leave the fallback paragraph up, no
       board and no ``window.publicPlayer`` at all, while the published file
       next to it loads.
    """
    page = browser_page
    url, report, keys = host
    grid = GRIDS["min"]
    key = keys["min"]
    other = _unique_grid(MIN_SIZE, MIN_SIZE, seed=28311)
    assert [_encode(row) for row in other] != [_encode(row) for row in grid]
    assert (len(other), len(other[0])) == (len(grid), len(grid[0]))

    # The positive control first, so "blank" below is a refusal and not the
    # page failing to restore anything at all.
    _prefill(page, host, key, _save(key, grid, _filled_cells(grid)[:1]))
    assert page.evaluate("() => window.publicPlayer.getHistory().done.length") == 1

    _prefill(page, host, key, _save(key, other, _filled_cells(grid)[:1]))
    assert page.evaluate("() => window.publicPlayer.getHistory().done.length") == 0, (
        "a save carrying another puzzle's clues replayed its marks onto this one"
    )
    assert page.evaluate("() => window.publicPlayer.getBoard().cells.every((s) => s === 'unknown')")

    # The payload half: a file the schema would have refused, planted into the
    # served tree after assembly (the assembler refuses to write one, which is
    # the other side of the same rule).
    planted_key = "abcdef0123"
    bad = {
        "key": planted_key,
        "width": MIN_SIZE,
        "height": MIN_SIZE,
        "tier": "easy",
        "clues": {
            "rows": [[MIN_SIZE + 1]] + [[0]] * (MIN_SIZE - 1),
            "columns": [[0]] * MIN_SIZE,
        },
    }
    (report.site_dir / "puzzle" / f"{planted_key}.json").write_text(
        json.dumps(bad), encoding="utf-8"
    )
    page.goto(f"{url}/play/{planted_key}")
    page.wait_for_selector(".player-fallback")
    assert page.evaluate("() => window.publicPlayer === undefined")
    assert page.query_selector("td.player-cell") is None
    assert page.inner_text(".player-fallback").strip() != ""


@pytest.mark.browser
def test_the_brush_region_and_touch_bindings_are_the_modules(browser_page, host) -> None:
    """What a brush writes, what a drag does to Region, and what a cell allows.

    Three bindings between ``play.js`` and ``solver_state.js`` that cycle 1 of
    this card's review measured as unexercised — ``tool = FILLED`` in the
    brush handler, ``setRegion(region)`` in place of ``nextRegion(region,
    "drag")``, and nothing reading ``touch-action`` at all:

    #. the brush decides the mark: White writes "empty" and Clear writes
       "unknown" (``clickedState``'s answer for each, and neither is the
       default brush, so a handler that ignored the chosen brush would show);
    #. Region is ONE-SHOT: it disarms itself the instant a drag is recorded,
       which is ``nextRegion(region, "drag")`` and not "leave it as it was";
    #. the cell's ``touch-action`` follows Region — ``auto`` while it is off,
       so a touch drag pans the page (``gesturePaints``'s rule, item 5 of the
       card), and ``none`` while it is armed, so the drag marks instead. This
       is the CSS half; the pointer-type half — what ``play.js`` itself does
       with a touch or pen drag — is
       ``test_a_touch_or_pen_drag_marks_only_while_region_is_armed``.
    """
    page = browser_page
    _open(page, host, host[2]["min"])

    page.click('[data-player-tool="empty"]')
    assert page.evaluate("() => window.publicPlayer.getTool()") == "empty"
    _tap(page, 2, 2)
    assert _state(page, 2, 2) == "empty"
    page.click('[data-player-tool="unknown"]')
    _tap(page, 2, 2)
    assert _state(page, 2, 2) == "unknown"

    touch_action = """() => getComputedStyle(document.querySelector('td.player-cell')).touchAction"""
    assert page.evaluate(touch_action) == "auto"
    page.click("[data-player-region]")
    assert page.evaluate("() => window.publicPlayer.isRegion()") is True
    assert page.evaluate(touch_action) == "none"

    # A drag disarms it, and the drag itself still marks its line.
    page.click('[data-player-tool="filled"]')
    _drag(page, [(7, 1), (7, 2), (7, 3)])
    assert [_state(page, 7, col) for col in (1, 2, 3)] == ["filled"] * 3
    assert page.evaluate("() => window.publicPlayer.isRegion()") is False, (
        "Region stayed armed after a drag, so it is not one-shot"
    )
    assert page.evaluate(touch_action) == "auto"


@pytest.mark.browser
def test_a_touch_or_pen_drag_marks_only_while_region_is_armed(browser_page, host) -> None:
    """Item 5 of the card, on the pointer TYPE rather than on the CSS shadow.

    ``play.js`` reads ``gesturePaints(event.pointerType, region)`` once, at
    pointerdown, and a touch or pen drag marks only while Region is armed —
    with Region off the gesture marks nothing and the browser is free to pan
    the page instead. ``test_the_brush_region_and_touch_bindings_are_the
    _modules`` reads the ``touch-action`` the CSS sets, which is the browser's
    half of that bargain; this reads ``play.js``'s own.

    Two devices, because they measure different mechanisms and cycle 2 of
    this card's review conflated them:

    #. **the pen** is what isolates ``gesturePaints``. A pen stream is not
       cancelled by the compositor, so with Region off the drag branch is
       fully reached and only ``gesturePaints("pen", false)`` stops it from
       marking. This is the half that kills ``const paints = true``, and the
       only half that does — measured.
    #. **the touch drag** is what a phone actually sends, and with Region off
       Chromium fires ``pointercancel`` after the first move (``touch-action:
       auto``), so the board is left alone by the CSS rule and ``play.js``'s
       pointercancel handler rather than by ``gesturePaints``. It is here
       because ``pointercancel`` otherwise has no control at all (cycle 2's
       N-3 named it unreachable), and it is named for what it measures.

    ``done.length`` is read as well as the cell states in both, so "marked
    nothing" is "recorded no stroke" and not "repainted over it".

    The residual, because the split above is an attribution and not a claim
    of coverage: ``gesturePaints``'s **touch** branch has no control on any
    browser this suite runs. Cycle 3 measured it — `event.pointerType ===
    "touch" ? true : gesturePaints(...)` survives all 33, because in Chromium
    with ``touch-action: auto`` the compositor cancels the stream whatever
    ``gesturePaints`` returns, even with ``preventDefault()`` called. That
    mutant is behaviourally equivalent on the one browser ADR-0038/R7
    declares, so it is evidence for the attribution rather than a hole to
    plug here; the branch is load-bearing only on a browser that honours
    ``preventDefault`` for a touch stream, and a control for it needs WebKit,
    which this suite does not drive.
    """
    page = browser_page
    _open(page, host, host[2]["min"])
    page.click('[data-player-tool="filled"]')
    pen_line = [(5, 0), (5, 1), (5, 2)]
    touch_line = [(7, 0), (7, 1), (7, 2)]

    # The pen, Region off: the drag runs to pointerup and marks nothing.
    assert page.evaluate("() => window.publicPlayer.isRegion()") is False
    _pen_drag(page, pen_line)
    assert [_state(page, *cell) for cell in pen_line] == ["unknown"] * 3
    assert page.evaluate("() => window.publicPlayer.getHistory().done.length") == 0

    # The touch drag, Region off: cancelled, so also nothing.
    _touch_drag(page, touch_line)
    assert [_state(page, *cell) for cell in touch_line] == ["unknown"] * 3
    assert page.evaluate("() => window.publicPlayer.getHistory().done.length") == 0

    # The pen, Region armed: the same drag marks the line, records one stroke
    # and disarms Region (the one-shot rule, from a third input device).
    page.click("[data-player-region]")
    assert page.evaluate("() => window.publicPlayer.isRegion()") is True
    _pen_drag(page, pen_line)
    assert [_state(page, *cell) for cell in pen_line] == ["filled"] * 3
    assert page.evaluate("() => window.publicPlayer.getHistory().done.length") == 1
    assert page.evaluate("() => window.publicPlayer.isRegion()") is False

    # The touch drag, Region armed: touch-action is none, so no cancel, and
    # the touch device marks too.
    page.click("[data-player-region]")
    _touch_drag(page, touch_line)
    assert [_state(page, *cell) for cell in touch_line] == ["filled"] * 3
    assert page.evaluate("() => window.publicPlayer.getHistory().done.length") == 2
    assert page.evaluate("() => window.publicPlayer.isRegion()") is False

    # And the pointercancel handler's OTHER statement, read directly (cycle
    # 3's m-4). Gutting the whole listener already reds this test, but it reds
    # at the pen-armed assertion above, because the stale `gesture` blocks the
    # NEXT pointerdown — sequencing, not rollback. So the rollback half had no
    # control: `gesture = null; refresh();` without `shown = history.board`
    # left all 33 green, and on a phone a Region-armed touch drag interrupted
    # by a system gesture would leave phantom marks on the board that are in
    # no stroke, in no history and in no save.
    #
    # Region armed, a drag that paints a preview, and then a real
    # touchCancel: the cells go back and no stroke is recorded.
    cancel_line = [(8, 0), (8, 1), (8, 2)]
    page.click("[data-player-region]")
    assert page.evaluate("() => window.publicPlayer.isRegion()") is True
    _touch_drag(page, cancel_line, end="touchCancel")
    assert [_state(page, *cell) for cell in cancel_line] == ["unknown"] * 3
    assert page.evaluate("() => window.publicPlayer.getHistory().done.length") == 2
    # Rolled back TO ``history.board``, not to a blank one: the marks the two
    # committed drags left are still there. Measured — `shown =
    # applyStroke(history.board, resetStroke(history.board))` in the cancel
    # handler wipes the board on every interrupted gesture and the three
    # assertions above do not see it.
    assert [_state(page, *cell) for cell in touch_line] == ["filled"] * 3
    assert [_state(page, *cell) for cell in pen_line] == ["filled"] * 3


@pytest.mark.browser
def test_the_page_carries_no_answer_and_no_third_party_asset(browser_page, host) -> None:
    """EC-048 in the browser: what the live page has, not only what disk has.

    The disk sweep is the guarantee; this is the reading a reviewer actually
    wants — after a full load, the page's own serialised DOM and every script
    it fetched are swept for the grid, and the page is held to loading nothing
    from another origin (which is also why no analytics tag is on it yet; see
    play.html).
    """
    page = browser_page
    url, report, keys = host
    origins: list[str] = []
    page.context.on("request", lambda request: origins.append(request.url))
    _open(page, host, keys["cycle2-144"])
    _tap(page, 0, 0)

    assert all(request.startswith(url + "/") for request in origins), origins
    html = page.content()
    for name, grid in GRIDS.items():
        assert decoded_recoveries(html, grid) == [], name
    # The page's own idea of its puzzle: clues and extent, and nothing the
    # answer could be read out of. Asserted on the live object rather than on
    # the file, because this is what the browser actually holds.
    assert page.evaluate("() => Object.keys(window.publicPlayer.payload).sort()") == [
        "columns",
        "height",
        "key",
        "rows",
        "tier",
        "width",
    ]


@pytest.mark.browser
def test_an_unknown_or_malformed_key_draws_no_board(browser_page, host) -> None:
    """A link to nothing says so, and sets no player — never a blank board.

    The soft not-found PAGE is CARD-284's; what belongs here is that this
    route refuses rather than half-renders, and that a key-shaped path cannot
    become a request for some other file.
    """
    page = browser_page
    url, report, keys = host
    asked: list[str] = []
    page.context.on("request", lambda request: asked.append(request.url))

    # A path that is not key-shaped is refused BEFORE anything is fetched, so
    # a hand-typed or hostile path never becomes a request for another file.
    # The "no request" half is the one with teeth: without the shape check the
    # fetch simply 404s and the page shows the same message, so a test that
    # only read the message passed either way (mutation round, M15).
    for path in ("/play/not-a-key", "/play/", "/play/..%2f..%2findex.json", "/play/ABCDEF0123"):
        asked.clear()
        page.goto(f"{url}{path}")
        page.wait_for_selector(".player-fallback")
        assert page.evaluate("() => window.publicPlayer === undefined"), path
        assert page.query_selector("td.player-cell") is None, path
        assert page.inner_text(".player-fallback").strip() != "", path
        assert [request for request in asked if "/puzzle/" in request] == [], (path, asked)

    # A key-shaped path that names nothing published does ask, and is told no.
    asked.clear()
    page.goto(f"{url}/play/0000000000")
    page.wait_for_selector(".player-fallback")
    assert page.evaluate("() => window.publicPlayer === undefined")
    assert [request for request in asked if request.endswith("/puzzle/0000000000.json")], asked
    assert page.query_selector("td.player-cell") is None


# ==========================================================================
# Structural: the tree stays static-only, and the page stays tokens-only
# ==========================================================================


def test_the_player_tree_is_static_and_adds_nothing_to_the_package() -> None:
    """ADR-0041/R3 — plain hand-written files in ``player/``, and no toolchain.

    The one Python file is the assembler, which is a deploy script and not
    part of the package: nothing under ``src/`` may import it, and no
    ``package-data`` glob may ship it. Both are checked, not assumed.
    """
    #
    # The expected set is DERIVED from the copy table plus the assembler
    # itself, not written out: CARD-284 added three files to ``player/``, and
    # a hand-written list would have had to be edited to admit them, which is
    # the same edit a stray file would need. A source file nobody publishes,
    # or a published source that is not on disk, fails here.
    files = sorted(path.name for path in PLAYER_DIR.iterdir() if path.is_file())
    assert files == sorted({*assembler.PLAYER_FILES, "assemble.py"})
    assert len(files) >= 8, files
    for forbidden in ("package.json", "node_modules", "package-lock.json"):
        assert not (PLAYER_DIR / forbidden).exists(), forbidden
    sources = (REPO_ROOT / "src").rglob("*.py")
    offenders = [
        path.relative_to(REPO_ROOT).as_posix()
        for path in sources
        if "assemble" in path.read_text(encoding="utf-8") and "player" in path.read_text(encoding="utf-8")
    ]
    assert offenders == [], offenders
    manifest = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "player/" not in manifest and '"player"' not in manifest


def test_the_player_assets_carry_no_colour_literal_and_only_defined_tokens() -> None:
    """Colours belong to tokens.css, and every token the page uses exists.

    The second half is the one with teeth: a ``var(--typo)`` resolves to
    nothing and renders as an unstyled page, which no assertion about classes
    would notice. The set of names comes from the token file itself
    (ADR-0039/R2), and the control plants an undefined name.
    """
    css = (PLAYER_DIR / "player.css").read_text(encoding="utf-8")
    script = (PLAYER_DIR / "play.js").read_text(encoding="utf-8")
    page = (PLAYER_DIR / "play.html").read_text(encoding="utf-8")
    for name, text in (("player.css", css), ("play.js", script), ("play.html", page)):
        assert not re.search(r"#[0-9a-fA-F]{3,8}\b", text), name
        assert "rgb(" not in text and "hsl(" not in text, name

    def undefined_in(text: str) -> list[str]:
        """Which ``var(--name)`` in ``text`` no definition answers.

        The defined set is read from the token file and from ``text``'s own
        ``--player-*`` declarations; ``--player-width`` / ``--player-height``
        are set on the element by ``play.js`` and so are declared in script
        rather than in CSS, which is why they are named here.
        """
        defined = set(
            re.findall(
                r"(--[a-z0-9-]+)\s*:",
                (REPO_ROOT / "src/nonogram/admin/static/tokens.css").read_text(encoding="utf-8"),
            )
        )
        assert len(defined) >= 40, len(defined)
        defined |= set(re.findall(r"^\s*(--player-[a-z-]+):", text, re.M))
        defined |= {"--player-width", "--player-height"}
        used = set(re.findall(r"var\((--[a-z0-9-]+)\)", text))
        assert used, "no token is used, so this rule measures nothing"
        return sorted(used - defined)

    assert undefined_in(css) == []
    # The control: the same rule over the same file with one token misspelt.
    assert undefined_in(css.replace("var(--color-bg)", "var(--color-bgg)")) == ["--color-bgg"]


def test_the_registrys_check_refs_for_this_card_all_resolve() -> None:
    """Every ``tests/test_public_player.py::…`` the model names is defined here.

    The defect this closes is the one the card arrived with: FR-045's AC-383
    through AC-386 named node ids in a file that did not exist, and the
    validator reported four DEAD check refs — a criterion that reads as
    verified at planning time and is not. Writing the tests is only half of
    the fix, because the validator matches the whole ``path::name`` string and
    finds it in no code file unless something names it.

    So this test is the other half, in both directions and derived from the
    registry rather than from a list kept here:

    #. every ref ``meta/architecture/requirements.yml`` points at this module
       resolves to a module-level function in it — a renamed test reds here
       instead of going quietly dead in the model;
    #. every one of them is written out in this module's docstring, which is
       what the validator's ``git grep`` actually reads, so a ref cannot be
       alive in pytest and dead in the model at the same time.

    The registry is parsed with a regex rather than a YAML library: there is
    no YAML parser in the dependency baseline (ADR-0006/R1), and the shape
    being read is one line.
    """
    registry = (REPO_ROOT / "meta" / "architecture" / "requirements.yml").read_text(encoding="utf-8")
    module = Path(__file__).relative_to(REPO_ROOT).as_posix()
    refs = sorted(set(re.findall(rf"({re.escape(module)}::[A-Za-z_][A-Za-z0-9_]*)", registry)))
    # Five today: AC-383..AC-386 and EC-050. EC-048's served half is the one
    # the registry does not yet name — see this module's docstring.
    assert len(refs) >= 5, refs

    defined = {
        name
        for name, value in globals().items()
        if name.startswith("test_") and callable(value) and getattr(value, "__module__", "") == __name__
    }
    assert len(defined) >= 20, sorted(defined)

    missing = [ref for ref in refs if ref.split("::", 1)[1] not in defined]
    assert missing == [], missing

    docstring = __doc__ or ""
    unnamed = [ref for ref in refs if ref not in docstring]
    assert unnamed == [], (
        "these refs resolve in pytest but the validator's git grep will not "
        f"find their node id in any code file: {unnamed}"
    )


def test_the_runtime_dependency_baseline_is_untouched() -> None:
    """G-3 / ADR-0006/R1 — nothing here is a runtime dependency.

    The page vendors no JavaScript library at all: it imports exactly one
    module, the admin player's own ``solver_state.js``, by build-time copy. No
    npm manifest, no CDN URL, no bundled third-party file — which is what
    makes "no new dependency" a statement about this tree rather than about
    ``pyproject.toml`` alone.
    """
    script = (PLAYER_DIR / "play.js").read_text(encoding="utf-8")
    page = (PLAYER_DIR / "play.html").read_text(encoding="utf-8")
    imports = re.findall(r"""from\s+["']([^"']+)["']""", script)
    assert imports == ["/solver_state.js"], imports
    for name, text in (("play.js", script), ("play.html", page)):
        assert "http://" not in text.replace("http://127.0.0.1", ""), name
        # No exemption here, because neither file needs a URL. The disjunct
        # this assertion used to carry ("or openapi.vercel.sh in text") was
        # dead — that host is vercel.json's $schema, which this assertion
        # never reads — and while it was dead it would have absorbed any
        # https:// URL added to either file beside a mention of that host.
        # ADR-0039/R3: an exemption is a claim, and an exemption with nothing
        # to exempt is a hole. It now lives where the URL actually is, below.
        assert "https://" not in text, name
    assert "cdn" not in script.lower()
    srcs = re.findall(r'src="([^"]+)"', page)
    assert srcs == ["/play.js"], srcs

    # The one https:// URL this tree does carry, and the exemption stated as
    # an EQUALITY against the URLs that exist rather than as a disjunct that
    # would absorb the next one (ADR-0039/R3). It is a JSON Schema reference
    # read by editors, never fetched by the page or the host.
    deploy = (PLAYER_DIR / "vercel.json").read_text(encoding="utf-8")
    assert re.findall(r"https?://[^\"']+", deploy) == ["https://openapi.vercel.sh/vercel.json"]
    assert json.loads(deploy)["$schema"] == "https://openapi.vercel.sh/vercel.json"
    import tomllib

    manifest = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert manifest["project"]["dependencies"] == ["Pillow>=10.0", "numpy>=1.24"]
