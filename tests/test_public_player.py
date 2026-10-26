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
   (R5, R1), and they are *validated* — a clue has to be a run-length encoding
   a line of that length could have, and the two axes have to agree on the
   filled count — so ``clues`` cannot be borrowed as a free numeric channel;
#. every other served value is drawn from a set the assembler can count, and
   ``check_capacity`` refuses to assemble unless the total information
   capacity of those sets is strictly below ``MIN_SIZE * MIN_SIZE`` bits — the
   fewest cells any published grid has. A channel that cannot hold the
   smallest grid cannot hold any grid. The figure is computed by the deployed
   code (``free_capacity_bits``), never transcribed;
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

import base64
import hashlib
import http.server
import importlib.util
import itertools
import json
import random
import re
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


def write_bundle(root: Path, grids=None, *, leaky=True) -> dict[str, str]:
    """A player bundle at ``root``; returns ``{name: key}``.

    Every puzzle's title is the base-64 of its own grid when ``leaky`` (the
    default), because the question this card exists to answer is what happens
    to such a title — a fixture that only ever carries "Snowy owl" would make
    every assertion below pass for the wrong reason.

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
            {"slug": "0123456789", "title": "A book", "puzzle_keys": sorted(keys.values())},
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

    Keyed by ``"<relative path> [<grid name>]"``. A JSON file is swept twice:
    once as its redacted payload (so the exempt projections are not reported
    as leaks) and once as its raw text with a decoder-only pass, because a
    packed grid is never a legitimate clue however it is spelled. Every other
    file is swept whole.
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


def test_served_tree_is_clean_of_answers(site, bundle) -> None:
    """EC-048 / AC-381's served half (ADR-0041/R2) — and its own control.

    The same sweep runs over both trees. The **bundle** must be dirty: its
    titles are base-64 of their grids, which is the path CARD-282 measured and
    routed here. The **site** must be clean. One scan, both directions, so a
    sweep that had quietly stopped working could not report this as a pass —
    the failure mode CARD-282's cycle 1 found in its own guard.
    """
    report, keys = site
    bundle_root, _ = bundle

    leaked = sweep_tree(bundle_root, GRIDS)
    assert len(leaked) >= len(GRIDS), (
        "the control is dead: the sweep found no recoverable grid in a bundle "
        f"whose every title is base-64 of its own grid. Found: {leaked}"
    )
    assert decoded_recoveries(_leaky_title(GRIDS["cycle2-144"]), GRIDS["cycle2-144"]), (
        "the sweep cannot even read CARD-282 cycle 2's own measured leak"
    )

    assert sweep_tree(report.site_dir, GRIDS) == {}


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


def test_the_title_is_dropped_on_every_puzzle_and_named_in_the_report(site) -> None:
    """``title`` is the removed channel, and the removal is loud.

    Two halves, because either alone would be weak: the exporter really does
    declare the field (so this is not a defence against a field nobody
    writes), and the assembler names every drop in its report (so the owner
    can see that the public page shows no picture name, rather than wondering).
    """
    report, keys = site
    assert "title" in player_bundle.PUZZLE_FILE_FIELDS
    assert "title" not in assembler.SERVED_SCHEMA
    assert sorted(report.dropped) == sorted((key, "title") for key in keys.values())


def test_the_index_and_book_files_are_not_served_by_this_page(site) -> None:
    """This card serves ``/play/<key>`` and nothing else, and says which.

    ``index.json`` and ``book/<slug>.json`` both carry a free-text ``title``
    too. Dropping it there is the library page's and the book page's question
    (CARD-284, CARD-285) and theirs to answer; this card leaves both files out
    and names them in the report instead of copying them untouched.
    """
    report, _ = site
    assert report.ignored == ("book/0123456789.json", "index.json")
    assert not (report.site_dir / "index.json").exists()
    assert not (report.site_dir / "book").exists()


def test_the_capacity_bound_is_derived_and_can_fail(monkeypatch, tmp_path) -> None:
    """The number EC-048's argument rests on, computed by the deployed code.

    The claim is "every non-exempt served field together cannot hold the
    smallest published grid". Both halves are measured here: the live schema's
    capacity is below the ceiling, and the check *fires* when a field wide
    enough to carry a grid is added — so the bound is a control and not a
    comment.
    """
    bits = assembler.check_capacity()
    assert bits == assembler.free_capacity_bits()
    assert assembler.CAPACITY_CEILING_BITS == MIN_SIZE * MIN_SIZE
    assert bits < assembler.CAPACITY_CEILING_BITS

    widened = dict(assembler.SERVED_VALUE_SPACE)
    widened["name"] = 2 ** (MAX_SIZE * MAX_SIZE)
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


def test_the_tier_is_narrowed_to_the_rule_or_dropped() -> None:
    """A tier is a short lowercase word or it is not served at all.

    This is the one non-exempt string field, so it is where the capacity bound
    is actually spent: the rule below is what makes
    ``SERVED_VALUE_SPACE["tier"]`` countable. Each case is a value the admin
    store can really hold.
    """
    assert assembler._tier("medium") == "medium"
    assert assembler._tier("Hard") == "hard"
    assert assembler._tier("  easy  ") == "easy"
    assert assembler._tier("") == ""
    assert assembler._tier(None) == ""
    assert assembler._tier("requires guessing") == ""  # a space is not in the alphabet
    assert assembler._tier("a" * (assembler.TIER_MAX_CHARS + 1)) == ""
    assert assembler._tier(_leaky_title(GRIDS["min"])) == ""


def test_a_puzzle_file_the_schema_cannot_accept_is_refused_and_named(tmp_path) -> None:
    """Every validator refuses, and says which value it refused.

    Default-deny needs a control per rule or it is a claim about rules nobody
    ran. Each case below is a payload one edit away from valid.
    """
    grid = GRIDS["min"]
    good = _bundle_payload(grid, tier="easy", title="Picture")
    cases = {
        "key": {**good, "key": "NOTAKEY"},
        "name": {**good, "key": _public_key(GRIDS["oblong"])},
        "width": {**good, "width": MAX_SIZE + 1},
        "height": {**good, "height": 0},
        "clues-shape": {**good, "clues": {"rows": good["clues"]["rows"]}},
        "clues-count": {**good, "clues": {**good["clues"], "rows": good["clues"]["rows"][:-1]}},
        "clues-empty": {**good, "clues": {**good["clues"], "rows": [[] for _ in grid]}},
        "clues-zero-mixed": {
            **good,
            "clues": {**good["clues"], "rows": [[0, 3] for _ in grid]},
        },
        "clues-too-long": {
            **good,
            "clues": {**good["clues"], "rows": [[MIN_SIZE + 1] for _ in grid]},
        },
        # A clue set with no room for its gaps, whose two axes nevertheless
        # agree on the filled count: [5, 5] needs 11 cells in a 10-cell line,
        # and 10 rows of [5, 5] total the same 100 cells as 10 columns of
        # [10]. So this case is refused by the fits-the-line rule and by
        # nothing else — which is what makes that rule's own control live.
        # Without it the fit check could be deleted and this test stayed green
        # (CARD-283's mutation round, M4b).
        "clues-no-room": {
            **good,
            "clues": {
                "rows": [[MIN_SIZE // 2, MIN_SIZE // 2] for _ in grid],
                "columns": [[len(grid)] for _ in grid[0]],
            },
        },
        "clues-disagree": {
            **good,
            "clues": {**good["clues"], "rows": [[1] for _ in grid]},
        },
        "not-an-object": [good],
    }
    for name, payload in cases.items():
        root = tmp_path / name
        path = root / "puzzle" / f"{good['key']}.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

        report = assembler.assemble(root, tmp_path / f"site-{name}")

        assert report.puzzle_count == 0, name
        assert len(report.refused) == 1 and report.refused[0][0] == good["key"], name
        assert report.refused[0][1], f"{name} was refused without a reason"
        assert not (report.site_dir / "puzzle").exists(), name
    assert len(cases) >= 12

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
    """
    first = write_bundle(tmp_path / "b1", {"a": GRIDS["min"]})
    second = write_bundle(tmp_path / "b2", {"b": GRIDS["oblong"], "c": GRIDS["max"]})
    assert set(first.values()).isdisjoint(second.values())
    one = assembler.assemble(tmp_path / "b1", tmp_path / "s1").site_dir
    two = assembler.assemble(tmp_path / "b2", tmp_path / "s2").site_dir

    def statics(root):
        return {
            path.relative_to(root).as_posix(): path.read_bytes()
            for path in sorted(root.rglob("*"))
            if path.is_file() and path.parent.name != "puzzle"
        }

    assert statics(one) == statics(two)
    assert len(statics(one)) == len(assembler.PLAYER_FILES) + len(assembler.COPIED_FROM_ADMIN)
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
    assert len(cases) >= 9 and sum(case[-1] for case in cases) == 4

    # And the solved state is a function of the board, not of history: undoing
    # the last mark on a solved board takes the banner away again.
    _prefill(page, host, key, _save(key, grid, filled[:-1]))
    _tap(page, *last)
    page.click('[data-player-action="undo"]')
    assert page.evaluate("() => window.publicPlayer.isSolved()") is False
    assert page.is_hidden("[data-player-solved]")


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
    assert reading["cellWidth"] >= 24 and reading["cellHeight"] >= 24, reading
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
def test_no_write_request_for_any_interaction(browser_page, host) -> None:
    """EC-050 / ADR-0041/R4 — for every interaction, zero writes leave the page.

    "Every interaction sequence" is approximated by driving every control the
    page has, in a seeded order, with the request log open: marks, a drag, a
    brush change, Region on and off, undo, redo, reset, a keyboard undo and a
    reload. The assertion is on the METHOD and the ORIGIN of every request —
    not on a count, because a count passes when nothing happened at all, so
    the number of interactions is asserted too.
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

    rng = random.Random(2831)
    interactions = 0
    for _ in range(24):
        choice = rng.randrange(8)
        if choice == 0:
            page.click('[data-player-tool="empty"]')
        elif choice == 1:
            page.click('[data-player-tool="filled"]')
        elif choice == 2:
            page.click("[data-player-region]")
        elif choice == 3:
            # force=True on purpose: an aria-disabled Undo is one of the
            # interactions this test must cover, and Playwright's actionability
            # check would otherwise refuse to press it at all.
            page.click('[data-player-action="undo"]', force=True)
        elif choice == 4:
            page.click('[data-player-action="redo"]', force=True)
        elif choice == 5:
            page.keyboard.press("Control+z")
        elif choice == 6:
            page.click('[data-player-action="reset"]', force=True)
        else:
            _tap(page, rng.randrange(MIN_SIZE), rng.randrange(MIN_SIZE))
        interactions += 1
    page.reload()
    page.wait_for_function("window.publicPlayer !== undefined")

    assert interactions == 24
    assert writes == []
    assert len(requests) > after_load, "the reload issued nothing, so nothing was watched"
    assert all(request.startswith(url + "/") for request in requests), requests
    # The one request kind this page makes at all, named: its own assets.
    assert any(request.endswith(f"/puzzle/{key}.json") for request in requests)


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
    files = sorted(path.name for path in PLAYER_DIR.iterdir() if path.is_file())
    assert files == ["assemble.py", "play.html", "play.js", "player.css", "vercel.json"]
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
    for text in (script, page):
        assert "http://" not in text.replace("http://127.0.0.1", "")
        assert "https://" not in text or "openapi.vercel.sh" in text
    assert "cdn" not in script.lower()
    srcs = re.findall(r'src="([^"]+)"', page)
    assert srcs == ["/play.js"], srcs
    import tomllib

    manifest = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert manifest["project"]["dependencies"] == ["Pillow>=10.0", "numpy>=1.24"]
