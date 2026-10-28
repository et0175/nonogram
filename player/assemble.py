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
    library/index.html  the /library page               (from player/library.html)
    b/index.html        the /b/<slug> landing           (from player/book.html)
    pages.js            the two listing pages' glue     (from player/pages.js)
    player.css          its styling                     (from player/player.css)
    solver_state.js     the admin player's pure module  (byte-identical copy)
    tokens.css          the design tokens               (byte-identical copy)
    vercel.json         the host's rewrites for the three doors
    .player-site        the marker check_out_dir recognises this tree by
    puzzle/<key>.json   one REBUILT file per bundle puzzle (see below)
    index.json          the REBUILT library index        (see "The two listings")
    book/<slug>.json    one REBUILT file per bundle book (see "The two listings")

The two copies are copies and not forks: ADR-0041/R3 requires the board-state
module to be reused from ``src/nonogram/admin/static/solver_state.js`` by
byte-identical build-time copy, never by editing it, and the design tokens
travel the same way for the same reason (one definition of the colours, as
``tests/test_admin_design_tokens.py`` already holds for the panel's own copy).
:data:`COPIED_FROM_ADMIN` is the table, and the equality is checked here at
assembly time *and* from the test tree.

Why this script exists at all, rather than ``cp -r``
----------------------------------------------------
**Because this is where EC-048 is carried, and it could not be carried
downstream of here.** Carried, not closed — the word "closed" is reserved
for the paragraph below that begins "But 'one open edge' is true only AFTER
the two exemptions are granted", which is the only place this file states the
scope, and which concludes that EC-048's literal text is not satisfiable by
any implementation of ADR-0041 at all.

ADR-0041/R2 forbids any public asset from carrying "a solution grid or data
from which any solution cell is recoverable, for any puzzle, on any export
path". CARD-282 shipped the exporter and then *measured
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

What is left is then held to EC-048 by two statements, and it matters a great
deal which of them does the work:

* ``clues`` and ``key`` are the two projections ADR-0041 sanctions by name
  (R5 and R1) — :data:`EXEMPT_SERVED_FIELDS`. They are **exempt**, not
  safe-by-measurement: ADR-0041/R2's own second sentence grants the
  exemption, and ADR-0041/R5 — the exporter taking every clue from
  ``compute_clues`` of the stored grid, upstream of this script — is where
  their integrity actually lives. :func:`_clues` checks only that a served
  clue set *could* belong to a grid of this extent (every clue fits its line,
  the two axes agree on the filled count); it does not establish that one
  does, and the clue field's own capacity is far above any grid's — a
  ``MIN_SIZE``-cell line admits 144 distinct clues, so a 10x10's twenty lines
  carry about 143 bits. An earlier revision of this docstring claimed the
  validation stopped the clues being "borrowed as a free numeric channel";
  that was measured false in cycle 1 of this card's review (a clue set no grid
  realises is accepted) and the claim is gone rather than softened;
* every OTHER served value is drawn from a domain this module can enumerate,
  and two of the three are not free at all. A served file is refused unless
  ``len(clues.columns) == width`` and ``len(clues.rows) == height``
  (:data:`DETERMINED_BY_CLUES`, enforced in :func:`_clues`), so a reader
  recomputes both extents from the clues they already have: those two fields
  carry nothing beyond the exempt projection. :data:`SERVED_VALUE_SPACE`
  counts what is left, :func:`free_capacity_bits` sums the base-2 logarithms,
  and :func:`check_capacity` refuses to assemble unless the total is strictly
  below ``MIN_SIZE * MIN_SIZE`` bits.

What that ceiling does and does not establish
---------------------------------------------
It establishes **"no served field is wide enough to be worth encoding a grid
in"**: a channel below ``MIN_SIZE * MIN_SIZE`` bits — the fewest cells any
published grid can have (CON-011) — cannot hold the smallest published grid,
so it cannot hold any.

It does **not** establish EC-048, whose threshold is *one cell*, one bit. No
bound that leaves a served field any choice at all can reach that threshold,
so this script does not pretend to: the ceiling is a trip-wire that fires when
somebody widens the schema, and EC-048's one-cell threshold is carried by the
closed rebuild plus the enumerated domains, not by the number.

That distinction is not pedantic. Cycle 1 of this card's review measured the
gap: while a served ``tier`` was "any lowercase string of up to twelve
characters" (56.46 of the 65.25 bits the bound then spent), a store could
write the first 56 cells of a published answer into that field as base-26,
and the capacity check, the rebuild and the decoding sweep all passed it
through — 56 of 56 cells recovered from the served file. The ceiling held and
the rule it was offered for did not.

So the domains carry it, and the residual is named rather than implied:

* ``width`` / ``height``: zero free bits, because they are recomputable from
  the clues (above);
* ``tier``: :data:`SERVED_TIERS` plus the empty string a value outside the
  vocabulary is dropped to — four values, two bits. The vocabulary is the
  runtime's own (``nonogram.difficulty.Tier``, ordered by
  ``nonogram.admin.book_plan.TIERS``) rather than a hand-written alphabet
  rule, which is ADR-0039/R2, and it is held to that enum from the test tree —
  where importing the package is legal — by
  ``tests/test_public_player.py::test_the_served_tier_set_is_the_runtimes_tier_vocabulary``;
* the residual, stated because two bits is above EC-048's one bit: a hostile
  store that chooses a puzzle's tier **label** as a function of its answer
  signals at most two bits per puzzle through this field, so **2N bits across
  a library of N published puzzles**. Nothing here excludes that — a label is
  a label — and the only way to close it is not to serve the tier at all,
  which is a product decision for ADR-0041 rather than a worktree one. Cycle
  2 of this card's review measured the rest of the rebuild total: a bundle
  carrying base-64 of its own grid in ``title``, in ``note``, in
  ``picture_name``, in ``difficulty_tier``, in a nested object AND in one of
  its field NAMES assembles to served bytes byte-identical to the clean
  payload's, and ``_dump``'s canonical form leaves no writer artefact to
  carry a bit either.

So the ``puzzle/<key>.json`` files have one open edge, the tier, and it is
two bits wide. **That sentence used to end this paragraph as a statement
about the whole script, and cycle 1 of this card's review measured it false
in the same commit that broke it**: the served listings CARD-284 added carry
three residuals of their own, every one of them wider than the tier's two
bits, and none of them countable by :func:`free_capacity_bits` (which counts
the puzzle files' fields and nothing else). Named here, sized where they are
declared:

* the **order** a book's puzzles are listed in — ``log2(k!)`` bits for a
  book of ``k`` puzzles: 4.58 for this card's four-puzzle fixture, 79.04 for
  a 24-puzzle book, 660.48 for a 120-puzzle one
  (:data:`LISTING_STRUCTURE_FIELDS`);
* the **membership** of that list — which ``k`` of ``N`` published puzzles a
  book holds, ``log2(C(N, k))`` bits, independent of the order: 83.17 bits
  for 24 of 120 (:data:`LISTING_STRUCTURE_FIELDS`, cycle-1 F-8);
* the book's **display title**, served since the owner's 2026-10-28 decision
  under an explicit exemption rather than a bound:
  :func:`book_title_residual_bits` derives it as
  ``SERVED_TITLE_MAX_CHARS * log2`` of the Unicode scalar space — 2410.18
  bits at today's constants, which is 24x the ceiling below and more than
  the 900 cells of the largest publishable grid. It is an EXEMPTION and this
  script says so: see :data:`EXEMPT_LISTING_FIELDS` for the decision, the
  scope that keeps the *puzzle* title forbidden, and what is measured.

The tier figure and the ceiling below are the puzzle files'. The three above
are the listings', they are declared rather than closed, and the only one of
the three that is a choice at all is the title.

**But "one open edge" is true only AFTER the two exemptions are granted, and
it is worth saying in one place rather than two paragraphs apart.** Given
ADR-0041/R5 the clues are a deterministic function of the stored grid, so
they carry zero FREE bits — and they leak every cell *by solving*, which is
the game (ADR-0041's Context: the solved check IS clue satisfaction) and not
a channel anything here could narrow. The consequence, cycle 2's and the
architect's rather than this script's: **EC-048's literal text — "data from
which any solution cell is recoverable" — is not satisfiable by any
implementation of ADR-0041**, so the registry's own wording is the blocker
for the word "closed" (cycle-1 F-12, ``meta/architecture/requirements.yml``,
outside this card's Touches and not edited). Read every "carries EC-048"
above as "carries it for everything except the three exemptions ADR-0041 and
the owner grant — the clues, the key and a book's display title — and the
four declared residuals: the tier's two bits per puzzle, and a book file's
order, membership and title".

Every number above that this script owns is computed here, from the declared
value space; none of it is transcribed. Ask for it with
``python player/assemble.py --capacity``.

What this script does not reach, named rather than left to look covered
-----------------------------------------------------------------------
* ``index.json`` and ``book/<slug>.json`` are **not** copied — and as of
  CARD-284 they are served, REBUILT, exactly as the puzzle files are. Two
  different ``title`` fields travel in those two files and **they get
  opposite answers**, which is the distinction cycle 1 of this card's review
  gated on arguing as one:

  - a **puzzle's** title is the picture name. EC-048 forbids it by name on
    every asset the public site serves, CARD-163 took it out of the admin
    player's own header for the same reason, and the picture name IS the
    answer to the puzzle. It is in neither :data:`SERVED_SCHEMA` nor
    :data:`SERVED_ENTRY_SCHEMA`, so it reaches neither listing, and
    :func:`check_listing_capacity` refuses to assemble if anybody puts it
    there. Not a decision — serving it would be the violation;
  - a **book's** display title is owner-authored editorial text that
    EC-048's enumeration does not name, and FR-045's own bundle clause
    already lists it ("holding its slug, display title and ordered puzzle
    keys") in the same sentence that forbids the picture name. The owner was
    asked and decided on 2026-10-28 to serve it: ``/b/<slug>`` is a book
    customer's first contact with the product seconds after a scan, and the
    card's body (line 31) always required the title there. It is served
    under an explicit exemption with its residual derived and declared —
    :data:`EXEMPT_LISTING_FIELDS`.

  Serving the book's title also answers the product question ADR-0041/R7
  opened and the card routed in (two finalized books with identical
  membership in identical order are one slug with two candidate titles): the
  decision is the card's **first** routed option, *publish one title*, and
  which one is CARD-282's deterministic reduction, held by
  ``tests/test_player_bundle.py::test_two_books_with_the_same_puzzles_are_one_public_book``.
* The **order** a book's puzzles are listed in, their **membership**, the
  book's **title** and the two bits of tier label are the whole residual of
  the served listings — see :data:`LISTING_STRUCTURE_FIELDS` and
  :data:`EXEMPT_LISTING_FIELDS`.
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
    "DETERMINED_BY_CLUES",
    "EXEMPT_LISTING_FIELDS",
    "EXEMPT_SERVED_FIELDS",
    "KEY_PATTERN",
    "LISTING_STRUCTURE_FIELDS",
    "MIRRORED_FROM_PUZZLE_FILE",
    "PLAYER_FILES",
    "SERVED_BOOK_SCHEMA",
    "SERVED_ENTRY_SCHEMA",
    "SERVED_INDEX_SCHEMA",
    "SERVED_SCHEMA",
    "SERVED_TIERS",
    "SERVED_TITLE_MAX_CHARS",
    "SERVED_VALUE_SPACE",
    "SITE_BOOK_DIR",
    "SITE_INDEX_FILE",
    "SITE_MARKER_FILE",
    "SITE_MARKER_TEXT",
    "SITE_PUZZLE_DIR",
    "TITLE_CODE_POINTS",
    "AssembleReport",
    "assemble",
    "book_title_residual_bits",
    "check_capacity",
    "check_listing_capacity",
    "check_out_dir",
    "free_capacity_bits",
    "listing_entry",
    "served_book",
    "served_index",
    "served_puzzle",
    "tier_narrowed",
    "title_narrowed",
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
#:
#: ``library.html`` and ``book.html`` travel the same way for the same
#: reason (CARD-284) — but ``vercel.json`` carries a rule for **both** of
#: them, not only for ``/b/<slug>``. An earlier revision of this comment
#: said ``/library`` resolved without one; cycle 1 of this card's review
#: measured that false in the same commit that added the rule, by killing it
#: (``"/library"`` -> ``"/zzzzzz"``) and redding
#: ``tests/test_public_player_pages.py::test_the_two_doors_are_routed_by_the_shipped_config``.
#: ``/library/index.html`` is what a host with a directory index would serve
#: for ``/library/``; the extensionless ``/library`` needs the rewrite, and
#: the loopback fixture's ``^/library/?$`` is the same rule read from the
#: same file.
PLAYER_FILES: dict[str, str] = {
    "play.html": "play/index.html",
    "play.js": "play.js",
    "library.html": "library/index.html",
    "book.html": "b/index.html",
    "pages.js": "pages.js",
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

#: Where the rebuilt puzzle files go.
SITE_PUZZLE_DIR = "puzzle"

#: Where the rebuilt book files go, and the name the rebuilt library index is
#: served under. Both are CARD-284's: CARD-283 served neither and said so.
#: The names are the bundle's own, because the pages' URLs are what the
#: printed QR codes and AC-389 name ("the library page over ``index.json``"),
#: not because the files are copies — they are rebuilds, like the puzzles.
SITE_BOOK_DIR = "book"
SITE_INDEX_FILE = "index.json"

#: The marker :func:`assemble` writes into every tree it builds, and the ONE
#: thing :func:`check_out_dir` recognises a previous run's tree by.
#:
#: Until CARD-284's fix round that guard compared the target's top-level
#: names against :func:`_site_entries`, which is a predicate that WIDENS
#: every time a published path is added: this card's own commit added
#: ``index.json``, ``book``, ``b``, ``library`` and ``pages.js`` to it, so a
#: directory whose only entry was ``index.json`` — one of the most generic
#: filenames on the web — became silently deletable where it had been
#: refused by name. Cycle 1 of this card's review found the widening shipped
#: with no control for what the guard must still DENY, only one for what it
#: must now allow.
#:
#: A marker this script writes itself is the strictly stronger predicate and
#: is the one chosen: it does not widen with the published set, it says
#: "this run's own output" rather than "a shape that resembles output", and
#: a target that merely looks like a site is refused. The cost is stated
#: rather than hidden: a tree assembled before this file existed has no
#: marker and needs ``--force`` once.
SITE_MARKER_FILE = ".player-site"

#: What the marker holds. Constant — it carries nothing about the bundle, so
#: it belongs to the static half of the site
#: (``tests/test_public_player.py::test_the_static_half_of_the_site_does_not
#: _vary_with_the_puzzles``) and a reader who finds it knows what erases it.
SITE_MARKER_TEXT = (
    "This directory was written by player/assemble.py (COMP-011).\n"
    "Assembling into it again DELETES everything here first.\n"
)

#: A public puzzle key, as ADR-0041/R1 pins it: the first 10 lowercase
#: hexadecimal characters of a SHA-256 digest. Re-checked here rather than
#: trusted, because the key becomes a *file name* in the output tree.
KEY_PATTERN = re.compile(r"^[0-9a-f]{10}$")

# --------------------------------------------------------------------------
# The served schema — the closed set a /play/<key> asset may carry
# --------------------------------------------------------------------------

#: The tier labels a served file may carry: the runtime's own tier
#: vocabulary, not an alphabet rule (ADR-0039/R2 — a guard's set is derived
#: from an authority the runtime can enumerate). The authority is
#: ``nonogram.difficulty.Tier``, a ``StrEnum`` of exactly these three values,
#: which ``nonogram.admin.book_plan.TIERS`` orders for the book matrix. It is
#: restated here as a three-label allow-list rather than loaded, because that
#: module imports ``nonogram.errors`` and so cannot be read by path the way
#: :func:`_limits` reads the import-free ``limits.py``; the equality with the
#: enum is therefore held from the test tree, where importing the package is
#: legal, by
#: ``tests/test_public_player.py::test_the_served_tier_set_is_the_runtimes_tier_vocabulary``
#: (the precedent CLAUDE.md names: reimplement natively, cross-check from the
#: tests, never import across).
#:
#: A stored value is stripped and lowercased before it is matched, so the
#: panel's "Hard" and "hard" are one served label, and anything else is
#: dropped to ``""`` rather than refused: a strange tier is cosmetic, and
#: refusing the puzzle would cost the player a page over a chip. Dropping is
#: also what closes the 56-bit channel cycle 1 of this card's review measured
#: through this field — see the module docstring.
SERVED_TIERS: tuple[str, ...] = ("easy", "medium", "hard")

#: The two served extents, and the clue axis each one is the length of. A
#: payload whose extent disagrees with its clue axes is refused (:func:`_clues`),
#: so these fields are redundant with the exempt clue projection rather than
#: free: a reader recomputes both, and their contribution to
#: :data:`SERVED_VALUE_SPACE` is one value — zero bits — each.
DETERMINED_BY_CLUES: dict[str, str] = {"width": "columns", "height": "rows"}

#: ADR-0041's two sanctioned projections of the solution. Exempt from the
#: capacity count by the ADR (R5 for the clues, R1 for the key), not by
#: anything this module measures — see the module docstring — and checked by
#: recipe instead (:func:`_clues`, :data:`KEY_PATTERN`), exactly as
#: ``player_bundle.SOLUTION_DERIVED_FIELDS`` routes them in the exporter.
EXEMPT_SERVED_FIELDS: tuple[str, ...] = ("clues", "key")

#: How many values each non-exempt served field may FREELY take, once the
#: exempt projection has fixed everything it fixes. The authority
#: :func:`free_capacity_bits` counts; see the module docstring for what the
#: total does and does not establish.
SERVED_VALUE_SPACE: dict[str, int] = {
    **dict.fromkeys(DETERMINED_BY_CLUES, 1),
    # The three labels, plus the "" a value outside the vocabulary becomes.
    "tier": len(SERVED_TIERS) + 1,
}

#: The capacity ceiling, in bits: the fewest cells any published grid has
#: (CON-011's floor, squared). Derived, not written. A total below it cannot
#: carry even the smallest grid — which is ALL it establishes; EC-048's own
#: threshold is one cell, and the module docstring says what carries that.
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
    """Refuse to assemble unless every served field is counted and narrow.

    Two refusals, because the count is worth nothing if a field can escape it:

    #. the schema has to be *partitioned* by :data:`EXEMPT_SERVED_FIELDS` and
       :data:`SERVED_VALUE_SPACE` — a name added to :data:`SERVED_SCHEMA` and
       to neither is a served field nobody counted, which is how this field
       was wide in the first place;
    #. the counted total has to stay strictly below
       :data:`CAPACITY_CEILING_BITS`.

    Returns the capacity in bits. Raises :class:`ValueError` on either, which
    is the moment somebody has to go back to ADR-0041 rather than to this
    constant.
    """
    counted = set(SERVED_VALUE_SPACE) | set(EXEMPT_SERVED_FIELDS)
    if counted != set(SERVED_SCHEMA) or set(SERVED_VALUE_SPACE) & set(EXEMPT_SERVED_FIELDS):
        raise ValueError(
            "the served schema is not partitioned into exempt and counted "
            f"fields: schema {sorted(SERVED_SCHEMA)}, exempt "
            f"{sorted(EXEMPT_SERVED_FIELDS)}, counted {sorted(SERVED_VALUE_SPACE)} "
            "— an uncounted served field is outside EC-048's capacity argument"
        )
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
    """A served tier label, or ``""`` when the stored value is not one.

    Stripped and lowercased first, so the admin panel's "Hard" and "hard" are
    one served label, and then matched against :data:`SERVED_TIERS` — the
    runtime's tier vocabulary, by membership, not an alphabet pattern. A value
    outside it is dropped rather than refused, and the drop is reported:
    :func:`tier_narrowed` is what :func:`assemble` asks, and the answer lands
    in :attr:`AssembleReport.narrowed` and in ``main``'s output. Cycle 2 of
    this card's review measured the earlier revision of this sentence false —
    it claimed ``dropped`` carried the narrowing, and ``dropped`` carries only
    names the served schema does not admit, so a narrowed tier was reported
    nowhere and was indistinguishable from an absent one.

    The membership test is what makes this field two bits wide instead of
    56.46: the string the review's cycle-1 plant put here ("tqlhkuhxpmgj", the
    first 56 cells of a published answer in base-26) is not a tier label, so
    nothing of it reaches the site.
    """
    if not isinstance(value, str):
        return ""
    folded = value.strip().lower()
    return folded if folded in SERVED_TIERS else ""


def tier_narrowed(value: object) -> bool:
    """Whether :func:`_tier` *dropped* a stored tier rather than passing one.

    The distinction the report needs, and the one cycle 2 of this card's
    review found missing: the served ``""`` means "no chip", and a bundle that
    never carried a tier says the same thing, so only the case where something
    was stored and nothing is served is a narrowing worth telling the owner
    about. It matters operationally — if ``nonogram.difficulty.Tier`` grows a
    member and :data:`SERVED_TIERS` lags, every puzzle of the new tier loses
    its chip, and without this the only thing that would notice is
    ``tests/test_public_player.py::test_the_served_tier_set_is_the_runtimes
    _tier_vocabulary``, in CI, after the deploy.
    """
    if value is None:
        return False
    if isinstance(value, str) and value.strip() == "":
        return False
    return _tier(value) == ""


def _line(clue: object, length: int, what: str) -> list[int]:
    """One validated clue: a run-length encoding that could fit ``length``.

    The ADR's convention (AC-013) is ``[0]`` for a line with no filled cell,
    never ``[]``. Everything else must be positive runs whose lengths plus one
    gap between each pair fit the line.

    This narrows the exempt field; it does not close it, and the stronger
    claim an earlier revision made here ("what stops clues being usable as a
    free numeric channel") was measured false. A line of ``length`` cells
    still admits every clue that fits it — 144 of them at ``MIN_SIZE`` — which
    is more capacity than a grid needs. The clues are exempt by ADR-0041/R2
    and their values are ADR-0041/R5's guarantee, taken from ``compute_clues``
    of the stored grid upstream of this script; what this function buys is
    that a served file cannot carry a clue a line could not have, which is
    what the page's own ``isClue`` also refuses on the other side of the wire.
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
    from one grid and are refused. (Agreeing does not mean a grid realises
    them: ``{"rows": [[1,1]] + [[0]]*9, "columns": [[2]] + [[0]]*9}`` is
    accepted and no grid produces it. The exemption does not rest on this.)

    The two length checks are also what :data:`DETERMINED_BY_CLUES` rests on:
    because a payload is refused unless its clue axes are exactly ``height``
    and ``width`` long, the served ``width`` and ``height`` are recomputable
    from the served clues and carry no free bits of their own.
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
# The two listings — index.json and book/<slug>.json (CARD-284)
# --------------------------------------------------------------------------
#
# CARD-283 served neither file and routed both decisions here, because both
# carry the bundle's free-text ``title`` and the answer taken for the puzzle
# page (drop the channel) had to be taken for them too or not at all. It is
# taken: no title is served, on either listing, for the reason F-2 of that
# card gives for the puzzle page — free text cannot be scanned for an encoded
# grid, so the public surface carries none. What the pages show instead is the
# extent and the tier, which are the same two values the ``/play/<key>``
# header already shows.
#
# The second decision routed here is CARD-282's F-8: an export that fails
# part-way through leaves ``index.json`` naming puzzle files that were never
# written, and ``book/<slug>.json`` naming keys with no file. A listing that
# names an absent file is a tile that 404s on tap, which is the one thing a
# reader seconds after scanning a QR code cannot diagnose.
#
# **It is closed by construction rather than by a check.** Every entry of
# every served listing IS the served payload of that key's own
# ``puzzle/<key>.json``, minus the clues (:func:`listing_entry`), so the
# listing's membership is the set of files this run actually wrote and an
# entry naming an absent file is not possible rather than merely detected.
# The bundle's own ``index.json`` is read as a SECOND, independent instrument
# — what the export *declared* — and every disagreement between the two is
# named in the report: :attr:`AssembleReport.unresolved` for a key a listing
# declared and the site does not serve, :attr:`AssembleReport.unlisted` for a
# served key the bundle's index named nowhere. A bundle with no ``index.json``
# at all therefore reports every served key as unlisted, which is the loudest
# shape available: the instrument cannot read as "nothing wrong" when it has
# nothing to read.

#: One entry of a served listing: :data:`SERVED_SCHEMA` without the clues.
#: Derived from the one schema rather than written again, so a field added
#: there arrives here — and has to be bucketed by
#: :func:`check_listing_capacity` before anything assembles.
#:
#: The clues are left out because a listing is a listing: twenty puzzles'
#: clue sets are the whole game downloaded to draw a page of tiles, and
#: ``/play/<key>`` fetches them one at a time already.
SERVED_ENTRY_SCHEMA: tuple[str, ...] = tuple(
    name for name in SERVED_SCHEMA if name != "clues"
)

#: Top-level fields of the served ``index.json``.
SERVED_INDEX_SCHEMA: tuple[str, ...] = ("puzzles",)

#: Top-level fields of a served ``book/<slug>.json``. ``puzzle_keys`` is
#: absent, replaced by the resolved entries themselves so the landing page
#: renders from this one file with nothing else to load first (CARD-284 G-2:
#: no second index is derived at page-load time).
#:
#: ``title`` is the book's DISPLAY title and is present since the owner's
#: 2026-10-28 decision — see :data:`EXEMPT_LISTING_FIELDS`. It is the only
#: schema in this module that carries a title, and
#: :func:`check_listing_capacity` refuses to assemble if the name appears in
#: any of the others.
SERVED_BOOK_SCHEMA: tuple[str, ...] = ("puzzles", "slug", "title")

#: How many characters of a book's display title are served.
#:
#: Not a capacity bound — no reachable cap is one, which is the whole reason
#: the field is an exemption and not a counted field: EC-048's threshold is
#: ONE bit, and one character of base-64 carries six. It is a LAYOUT bound
#: and a declaration bound. A heading longer than this cannot be read on the
#: 390 px phone a QR scan lands on, and a cap is what turns the residual
#: from "unbounded" into the number :func:`book_title_residual_bits` prints.
SERVED_TITLE_MAX_CHARS = 120

#: The Unicode scalar values a served character may be: every code point
#: except the 2048 surrogates. Derived from ``sys.maxunicode`` rather than
#: written, so the figure below is the interpreter's own answer.
TITLE_CODE_POINTS = sys.maxunicode + 1 - 2048

#: The one served listing field that is EXEMPT rather than counted or
#: mirrored: a book's display title.
#:
#: **Two different fields are at stake here and they get opposite answers.**
#: Cycle 1 of this card's review gated on them being argued as one, so the
#: distinction is written out once, here, and every sentence this module
#: writes about a title names which one it means:
#:
#: * the **puzzle** title is the picture name. EC-048 forbids it by name
#:   ("the picture name") on every asset the public site serves; CARD-282
#:   measured a stored puzzle name that was the base-64 of its own grid
#:   decoding back to all 144 cells of a 12x12 answer; CARD-163 took the
#:   picture name out of the admin player's own header for the same reason.
#:   It stays forbidden, and the forbidding is mechanical: ``title`` is in
#:   neither :data:`SERVED_SCHEMA` nor :data:`SERVED_ENTRY_SCHEMA`, and
#:   :func:`check_listing_capacity` raises if it is added to either;
#: * the **book's** display title is owner-authored editorial text about a
#:   book. EC-048's enumeration does not name it, and FR-045's own bundle
#:   clause lists it ("holding its slug, display title and ordered puzzle
#:   keys") in the same sentence that forbids the picture name. The owner
#:   was asked directly and decided on 2026-10-28 to serve it.
#:
#: What the exemption costs, derived rather than asserted:
#: :func:`book_title_residual_bits` is ``SERVED_TITLE_MAX_CHARS *
#: log2(TITLE_CODE_POINTS)`` = 2410.18 bits at today's constants. That is
#: 24x :data:`CAPACITY_CEILING_BITS` and more than the 900 cells of the
#: largest publishable grid (``MAX_SIZE * MAX_SIZE``), so **this is an open
#: channel, not a narrow one**, and no honest cap closes it. A hostile store
#: that names a book after the base-64 of one of its puzzles' answers
#: publishes that answer, exactly as CARD-282 measured. Measured in cells
#: rather than bits, which is the second instrument:
#: ``tests/test_public_player_pages.py::test_the_book_title_exemption_is_scoped_and_its_cost_is_measured``
#: recovers every cell of a MIN_SIZE grid out of a served book title.
#:
#: It is granted anyway, by the owner, because the alternative is a landing
#: page with no name on it — the same "not serving it means not having the
#: page" trade the order and the membership are declared under. What makes
#: it an exemption rather than a leak is that it is bounded in SCOPE: a
#: book file, and nothing else.
EXEMPT_LISTING_FIELDS: tuple[str, ...] = ("title",)

#: Listing fields whose served value is, by construction, a value already
#: served on that key's ``puzzle/<key>.json``. They are therefore worth zero
#: NEW capacity: a reader of the listing learns nothing a reader of the puzzle
#: files does not already have. :func:`listing_entry` is the construction, and
#: it copies from the served payload rather than from the bundle, which is
#: what makes the claim structural instead of a comparison somebody has to
#: remember to make.
MIRRORED_FROM_PUZZLE_FILE: tuple[str, ...] = SERVED_ENTRY_SCHEMA

#: Listing fields that are structure rather than a puzzle's value: the list
#: itself and the book's own slug, which is the file's name and is re-checked
#: against :data:`KEY_PATTERN` (ADR-0041/R7 truncates the slug digest to the
#: same length as R1's key, so the shapes are the same ten hex characters).
#:
#: These two carry TWO residuals, not one, and the second was argued in
#: cycle 1 and not declared (its F-8). Both are declared rather than closed,
#: both for the same reason — not serving them means not having a landing
#: page — and closing either is ADR-0041's decision, not a worktree one:
#:
#: * the **ORDER** of ``puzzles`` in a book file. AC-387 asks for the book's
#:   own order, a printed book publishes that order on its pages anyway, and
#:   a hostile store that chose the order by the answer signals up to
#:   ``log2(k!)`` bits through it: 4.58 bits for a 4-puzzle book, 79.04 for
#:   24, 660.48 for 120;
#: * the **MEMBERSHIP** of that list — which ``k`` of the ``N`` published
#:   puzzles this book holds. It is a different channel from the order and
#:   independent of it: ``log2(C(N, k))`` bits, 83.17 for 24 of 120, and a
#:   store that chose membership by an answer signals through it even if the
#:   order were fixed. The library's ``index.json`` has no such residual —
#:   it is every puzzle served, so there is no choice to encode in — which
#:   is why this is specific to the book file.
#:
#: Both are the same shape, and the same reason, as the two bits of tier
#: label. The book's title is a third residual and a wider one, and it is
#: declared separately because it is an EXEMPTION rather than structure —
#: :data:`EXEMPT_LISTING_FIELDS`.
LISTING_STRUCTURE_FIELDS: tuple[str, ...] = ("puzzles", "slug")


def book_title_residual_bits() -> float:
    """What the exempt book title could carry, in bits.

    ``SERVED_TITLE_MAX_CHARS`` characters drawn from
    :data:`TITLE_CODE_POINTS` scalar values. Derived by deployed code for the
    reason :func:`free_capacity_bits` is: a residual written into a comment
    goes stale the first time a constant moves, which is precisely what cycle
    1 of this card's review found at the top of this file.

    This is NOT compared against :data:`CAPACITY_CEILING_BITS` and does not
    gate the assembly. It cannot be: the figure is 24x that ceiling and
    larger than the biggest publishable grid, so there is no pass to be had.
    It is the size of a declared exemption, printed by ``--capacity`` so the
    owner can see what was granted.
    """
    return SERVED_TITLE_MAX_CHARS * math.log2(TITLE_CODE_POINTS)


def check_listing_capacity() -> None:
    """Refuse to assemble unless every served LISTING field is accounted for.

    The sibling of :func:`check_capacity`, and the same default-deny shape:
    every name any served listing carries has to be in exactly one of three
    buckets — mirrored from a puzzle file
    (:data:`MIRRORED_FROM_PUZZLE_FILE` — zero new capacity), structure
    (:data:`LISTING_STRUCTURE_FIELDS` — the list and the slug, whose two
    residuals are named there), or exempt
    (:data:`EXEMPT_LISTING_FIELDS` — the book's display title, whose cost is
    :func:`book_title_residual_bits`). A name in two buckets, or in none, is
    a served value nobody accounted for, which is exactly how the ``tier``
    channel got to be 56 bits wide in cycle 1 of CARD-283's review.

    The third bucket is an exemption, so ADR-0039/R3 makes it a claim that
    carries a control for what it must NOT absorb. Two refusals do that, and
    they are the half an exemption usually ships without. They run in this
    order, and the order is what makes each of them REACHABLE — the first
    draft put them after the partition check, where both were dead code
    because any edit that reaches them breaks the partition first:

    #. **liveness.** An exempt name no book schema carries is refused. An
       exemption granted for a field nothing serves is an exemption nobody
       can see go wrong, and the equality against the sites that exist is
       what ADR-0039/R3 asks for;
    #. **scope.** An exempt name may appear in :data:`SERVED_BOOK_SCHEMA` and
       nowhere else. Added to :data:`SERVED_ENTRY_SCHEMA`,
       :data:`SERVED_INDEX_SCHEMA` or :data:`SERVED_SCHEMA` it is refused —
       which is what keeps the PUZZLE title forbidden while the BOOK's is
       served, mechanically rather than by everyone remembering the
       distinction;
    #. the **partition** itself, over all three buckets.

    Raises:
        ValueError: when the liveness, the scope or the partition does not
            hold. That is the moment to go back to ADR-0041, not to this
            function.
    """
    unused = set(EXEMPT_LISTING_FIELDS) - set(SERVED_BOOK_SCHEMA)
    if unused:
        raise ValueError(
            f"the listing exemption names {sorted(unused)}, which no served "
            "schema carries: an exemption for a field nothing serves is a "
            "claim nothing can check (ADR-0039/R3)"
        )
    outside = set(EXEMPT_LISTING_FIELDS) & (
        set(SERVED_INDEX_SCHEMA) | set(SERVED_ENTRY_SCHEMA) | set(SERVED_SCHEMA)
    )
    if outside:
        raise ValueError(
            f"the listing exemption {sorted(EXEMPT_LISTING_FIELDS)} is scoped "
            "to a book file, and "
            f"{sorted(outside)} reached a puzzle file or the library index: "
            "a book's display title is exempt by the owner's 2026-10-28 "
            "decision, the PICTURE NAME is forbidden by EC-048, and they are "
            "not the same field"
        )
    carried = set(SERVED_INDEX_SCHEMA) | set(SERVED_BOOK_SCHEMA) | set(SERVED_ENTRY_SCHEMA)
    buckets = (MIRRORED_FROM_PUZZLE_FILE, LISTING_STRUCTURE_FIELDS, EXEMPT_LISTING_FIELDS)
    accounted = {name for bucket in buckets for name in bucket}
    twice = {
        name
        for name in accounted
        if sum(name in bucket for bucket in buckets) > 1
    }
    if carried != accounted or twice:
        raise ValueError(
            "the served listings are not partitioned into mirrored, "
            f"structural and exempt fields: carried {sorted(carried)}, "
            f"mirrored {sorted(MIRRORED_FROM_PUZZLE_FILE)}, structural "
            f"{sorted(LISTING_STRUCTURE_FIELDS)}, exempt "
            f"{sorted(EXEMPT_LISTING_FIELDS)}, in more than one "
            f"{sorted(twice)} — an unaccounted listing field is outside "
            "EC-048's argument"
        )


def listing_entry(served: dict[str, object]) -> dict[str, object]:
    """One listing tile, built from a SERVED puzzle payload.

    ``served`` is :func:`served_puzzle`'s own output — never a bundle payload
    — so every value here has already passed that function's domains, and the
    "a listing carries nothing the puzzle files do not" claim is a property of
    this one expression rather than of a comparison elsewhere.
    """
    return {name: served[name] for name in SERVED_ENTRY_SCHEMA}


def served_index(entries: dict[str, dict[str, object]]) -> dict[str, object]:
    """The served ``index.json``: every puzzle this run wrote, by key.

    ``entries`` maps key -> :func:`listing_entry`. Sorted by key so the bytes
    are a function of the published set and not of the order the bundle
    directory was walked — the same determinism ``_dump`` exists for, one
    layer out: EC-049 makes an export's bytes a function of the store, and
    this is what makes a deploy diff of the SITE readable too.

    That sentence had no control until this card's fix round, and cycle 1 of
    its review measured the gap: reversing this sort survived 51 nodes,
    because every library assertion wrapped the rendered keys in ``sorted``
    and ``test_the_static_half_of_the_site_does_not_vary_with_the_puzzles``
    excludes ``index.json`` from its byte comparison by design. It is held
    now, in two places and two shapes —
    ``tests/test_public_player_pages.py::test_the_served_index_is_key_sorted``
    on this function's own output, and
    ``tests/test_public_player_pages.py::test_two_assemble_runs_are_byte_identical``
    on the whole assembled tree, which is the property at the layer that is
    actually deployed.

    The key order is NOT claimed to be an order a reader wants: a key is ten
    hex characters of a digest, so to a reader /library is in no order at
    all, and no AC states one. What is claimed is only that it is the same
    order twice.
    """
    served = {"puzzles": [entries[key] for key in sorted(entries)]}
    assert sorted(served) == sorted(SERVED_INDEX_SCHEMA)
    return served


def _book_title(value: object) -> str:
    """A book's served display title, or ``""`` when the bundle has none.

    The whole of what this module does to the field, written out because it
    is an EXEMPT field and the temptation is to read the processing as a
    narrowing (:data:`EXEMPT_LISTING_FIELDS` — it is not one; no reachable
    cap is):

    * a non-string is dropped to ``""``. A served title is a heading, and a
      number or an object in that field is a bundle this module does not
      understand rather than a title;
    * whitespace is collapsed to single spaces, so a stored title with a
      newline in it is one line of heading rather than a layout accident;
    * it is truncated to :data:`SERVED_TITLE_MAX_CHARS`.

    None of that is a defence against an encoded grid. It cannot be: cycle 1
    of CARD-282 established there is no decision procedure for "does this
    string carry a grid?", its denylist missed 7 of 7 planted encodings, and
    one character of base-64 already carries six bits against EC-048's
    threshold of one. The field is served because the owner decided on
    2026-10-28 that ``/b/<slug>`` has to carry the book's name, and the cost
    is declared rather than filtered.

    The PUZZLE title is a different field and is not served at all — see
    :data:`EXEMPT_LISTING_FIELDS` for why the two get opposite answers, and
    :func:`check_listing_capacity` for the refusal that keeps them apart.
    """
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())[:SERVED_TITLE_MAX_CHARS]


def title_narrowed(value: object) -> bool:
    """Whether :func:`_book_title` served LESS than the bundle's title.

    The ``narrowed`` report's second member, and the same distinction
    :func:`tier_narrowed` draws: a book that carried no title and a book
    whose title was truncated both end up with a shorter served string, and
    only the second is something to tell the owner about. Truncation is the
    case that matters operationally — a 130-character title loses its last
    ten characters on the page a QR code lands on, and without this nothing
    would say so.
    """
    if not isinstance(value, str):
        return value is not None
    collapsed = " ".join(value.split())
    return collapsed != "" and _book_title(value) != collapsed


def served_book(
    payload: object, stem: str, entries: dict[str, dict[str, object]]
) -> tuple[dict[str, object], list[str], list[str]]:
    """``(served payload, dropped field names, unresolved keys)`` for one book.

    ``stem`` is the file's name without ``.json``, which ADR-0041/R7 makes the
    slug, and the payload's own ``slug`` must equal it. The book's
    ``puzzle_keys`` are kept in **book order** (AC-387) and resolved against
    ``entries``: a key with no served puzzle file is left out of the listing
    and returned as unresolved, so a half-written bundle costs the reader the
    tile rather than a 404 on tap.

    The book's ``title`` is served (:func:`_book_title`), which is the one
    field this function passes through from the bundle rather than deriving,
    and the one place in this module a title is served at all. The puzzle
    titles inside ``entries`` are already gone — those entries are
    :func:`listing_entry` outputs over :data:`SERVED_ENTRY_SCHEMA`, which has
    no ``title`` — so a book file carries one editorial string and no picture
    name, which is the distinction :data:`EXEMPT_LISTING_FIELDS` draws.

    A book all of whose keys are unresolved is still served, with an empty
    list. The slug is real — it is printed in a QR code — so the landing page
    saying "none of this book's puzzles are on the site yet" is the honest
    answer, and the not-found page is reserved for a slug the bundle does not
    have at all (AC-388).

    Raises:
        ValueError: with a reason, for a payload this function cannot read.
            The caller turns that into a named refusal rather than a failed
            assembly, as it does for a puzzle file.
    """
    if not isinstance(payload, dict):
        raise ValueError("the file is not a JSON object")
    slug = _key(payload.get("slug"), "slug")
    if slug != stem:
        raise ValueError(f"the file is named {stem}.json but carries the slug {slug}")
    declared = payload.get("puzzle_keys")
    if not isinstance(declared, list):
        raise ValueError("puzzle_keys is not a list")
    order = [_key(value, f"puzzle_keys[{i}]") for i, value in enumerate(declared)]
    unresolved = [key for key in order if key not in entries]
    served: dict[str, object] = {
        "slug": slug,
        "title": _book_title(payload.get("title")),
        "puzzles": [entries[key] for key in order if key in entries],
    }
    assert sorted(served) == sorted(SERVED_BOOK_SCHEMA)
    dropped = sorted(name for name in payload if name not in (*SERVED_BOOK_SCHEMA, "puzzle_keys"))
    return served, dropped, unresolved


def _declared_keys(path: Path) -> tuple[list[str], str | None]:
    """``(keys the bundle's index.json declares, why it could not be read)``.

    The second instrument behind :attr:`AssembleReport.unlisted`, and read
    permissively on purpose: it is a cross-check against what the export
    *said* it wrote, never the authority for what is served. An absent or
    unreadable index therefore does not refuse the assembly — it returns no
    declared keys, which makes every served key unlisted and the silence
    impossible.
    """
    if not path.is_file():
        return [], f"{SITE_INDEX_FILE} is not in the bundle"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeDecodeError) as unreadable:
        return [], f"{SITE_INDEX_FILE} could not be read: {unreadable}"
    if not isinstance(payload, dict) or not isinstance(payload.get("puzzles"), list):
        return [], f"{SITE_INDEX_FILE} carries no puzzles list"
    keys = [
        entry["key"]
        for entry in payload["puzzles"]
        if isinstance(entry, dict) and isinstance(entry.get("key"), str)
    ]
    return keys, None


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

    ``narrowed`` is the third silence, and it was still silent until cycle 2
    of this card's review: ``(key, field)`` for a field whose stored value was
    *admitted by the schema but emptied by its domain* — today only ``tier``
    (:func:`tier_narrowed`). It is deliberately separate from ``dropped``: a
    dropped field is one the site does not serve at all, a narrowed one is
    served with less in it than the bundle had.

    ``unresolved`` and ``unlisted`` are CARD-284's two, and they are the F-8
    instrument rather than the F-8 fix (the fix is structural — see "The two
    listings" above). ``unresolved`` is ``(listing path, key)`` for a key a
    bundle listing declared and this run does not serve: a half-written
    export. ``unlisted`` is the other direction — a key whose puzzle file was
    served and whose entry the bundle's ``index.json`` named nowhere — and
    ``index_unread`` says why that index could not be consulted at all, in
    which case every served key is unlisted.

    ``book_count`` is how many book files were served, which is not the same
    number as the bundle's books: two finalized books with identical
    membership are one public slug (ADR-0041/R7), and a book file the schema
    refuses is in ``refused`` instead.
    """

    site_dir: Path
    puzzle_count: int
    capacity_bits: float
    book_count: int = 0
    dropped: tuple[tuple[str, str], ...] = ()
    narrowed: tuple[tuple[str, str], ...] = ()
    refused: tuple[tuple[str, str], ...] = ()
    ignored: tuple[str, ...] = ()
    copied: tuple[str, ...] = ()
    unresolved: tuple[tuple[str, str], ...] = ()
    unlisted: tuple[str, ...] = ()
    index_unread: str | None = None


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


def _site_entries() -> set[str]:
    """The top-level names an assembled site holds, derived from the tables.

    ``play/index.html`` contributes ``play``, so the set is the first segment
    of every published path plus the marker and the three the bundle's own
    data goes to. Derived rather than listed: a new published file widens
    this set by being added to :data:`PLAYER_FILES`, not by somebody
    remembering this function.

    **This is a description of the tree, and is no longer what
    :func:`check_out_dir` consults.** It was, until CARD-284's fix round, and
    that is the defect cycle 1 of this card's review found: a predicate that
    widens with the published set admits more every time a page is added, and
    this card's own commit widened it by five names — so a directory whose
    only entry was ``index.json`` became deletable. The guard recognises
    :data:`SITE_MARKER_FILE` instead, which does not widen. What this
    function is still for is the one place that wants to state the tree's
    top-level shape: ``tests/test_public_player.py::test_an_out_dir_that_is
    _not_a_previous_site_is_refused``'s positive control.
    """
    published = [*PLAYER_FILES.values(), *COPIED_FROM_ADMIN.values()]
    return {path.split("/", 1)[0] for path in published} | {
        SITE_PUZZLE_DIR,
        SITE_BOOK_DIR,
        SITE_INDEX_FILE,
        SITE_MARKER_FILE,
    }


def check_out_dir(out_dir: Path | str, *, force: bool = False) -> Path:
    """The ``--out`` directory, or :class:`ValueError` if it is not ours to erase.

    :func:`assemble` deletes its output directory, which is right for a deploy
    target and catastrophic for a typo: measured in cycle 1 of CARD-283's
    review, a directory holding ``precious/notes.txt`` came back holding only
    the site. So a target that exists and is non-empty is refused unless it
    holds :data:`SITE_MARKER_FILE` — the file :func:`assemble` writes into
    every tree it builds, before it writes anything else.

    **The predicate changed in CARD-284's fix round, and the reason is worth
    the paragraph.** Until then it was a name test: the target was accepted
    if every top-level name in it was one an assembled site has
    (:func:`_site_entries`). That predicate widens every time a published
    path is added, and this card's own commit widened it by five names —
    ``index.json``, ``book``, ``b``, ``library``, ``pages.js`` — so a
    directory whose only entry was ``index.json``, one of the most generic
    filenames on the web, went from refused-by-name to silently deleted.
    Cycle 1 of this card's review found the widening shipped with a control
    for what the guard must now ALLOW and none for what it must still DENY.

    A marker is the strictly stronger predicate: it asks "did this script
    write this tree?" instead of "does this tree look like output?", and it
    does not widen with the published set. Two consequences, both stated
    rather than discovered later: a tree assembled before the marker existed
    needs ``--force`` once, and a directory that happens to hold a site's
    filenames but not the marker is refused — which is the point.

    The repository root is nevertheless refused **by name, unconditionally,
    and before ``force`` is read**. That is the one bound ``--force`` has.
    ``--force`` is the owner's escape hatch for a real deploy target this
    script did not write, and ADR-0039/R3 makes an exemption a claim that
    carries a control: cycle 2 measured ``check_out_dir(repo_root,
    force=True)`` returning the checkout, so ``assemble --out . --force``
    would have deleted it. Deleting the checkout is never what ``--force``
    means, so it is outside the exemption rather than inside it, and
    ``tests/test_public_player.py::test_an_out_dir_that_is_not_a_previous
    _site_is_refused`` holds that both ways. A non-directory target is
    likewise refused outright, force or not.
    """
    site = Path(out_dir)
    if site.exists() and not site.is_dir():
        raise ValueError(f"--out {site} is not a directory")
    if site.resolve() == REPO_ROOT:
        raise ValueError(
            f"--out {site} is the repository root; assembling would delete the checkout"
        )
    if force or not site.is_dir():
        return site
    present = sorted(entry.name for entry in site.iterdir())
    if present and not (site / SITE_MARKER_FILE).is_file():
        raise ValueError(
            f"--out {site} holds {', '.join(present)} and no "
            f"{SITE_MARKER_FILE} marker, so no run of this script wrote it: "
            "refusing to delete a directory this script did not write. Pass "
            "--force if it really is the deploy target."
        )
    return site


def assemble(
    bundle_dir: Path | str | None, out_dir: Path | str, *, force: bool = False
) -> AssembleReport:
    """Write the deployable site into ``out_dir``. Read-only against the input.

    ``bundle_dir`` is a CARD-282 player bundle (``None`` assembles the static
    half alone, which is what a page test that supplies its own puzzle file
    wants). ``out_dir`` is removed first, so the tree is a function of the
    input and nothing a previous run left behind survives into a deploy — but
    only once :func:`check_out_dir` has agreed that the directory is one a
    previous run wrote (or ``force`` says to go ahead anyway).
    """
    capacity = check_capacity()
    check_listing_capacity()
    site = check_out_dir(out_dir, force=force)
    if site.exists():
        shutil.rmtree(site)
    site.mkdir(parents=True)
    # Written FIRST, and before any failure can happen: the marker is what
    # check_out_dir recognises this tree by, so a run that dies half way
    # through still leaves a target the next run may replace. Written the
    # moment the directory exists rather than at the end, which is the
    # difference between "a retry works" and "a retry needs --force".
    _write(site / SITE_MARKER_FILE, SITE_MARKER_TEXT)

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
    narrowed: list[tuple[str, str]] = []
    refused: list[tuple[str, str]] = []
    ignored: list[str] = []
    unresolved: list[tuple[str, str]] = []
    entries: dict[str, dict[str, object]] = {}
    index_unread: str | None = None
    books = 0
    count = 0
    if bundle_dir is not None:
        bundle = Path(bundle_dir)
        files = [path for path in sorted(bundle.rglob("*")) if path.is_file()]
        book_files: list[Path] = []
        for path in files:
            relative = path.relative_to(bundle).as_posix()
            if path.suffix != ".json":
                ignored.append(relative)
                continue
            if relative.startswith(f"{SITE_BOOK_DIR}/"):
                # Second pass: a book's tiles are the served puzzle entries,
                # so every puzzle file has to have been read first.
                book_files.append(path)
                continue
            if relative == SITE_INDEX_FILE:
                # Read as the F-8 cross-check, never as the served listing.
                continue
            if not relative.startswith(f"{SITE_PUZZLE_DIR}/"):
                ignored.append(relative)
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                served, names = served_puzzle(payload, path.stem)
            except (ValueError, UnicodeDecodeError) as unservable:
                refused.append((path.stem, str(unservable)))
                continue
            dropped.extend((path.stem, name) for name in names)
            if tier_narrowed(payload.get("tier")):
                narrowed.append((path.stem, "tier"))
            _dump(site / SITE_PUZZLE_DIR / f"{served['key']}.json", served)
            entries[served["key"]] = listing_entry(served)
            count += 1

        for path in book_files:
            relative = path.relative_to(bundle).as_posix()
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                book, names, missing = served_book(payload, path.stem, entries)
            except (ValueError, UnicodeDecodeError) as unservable:
                refused.append((path.stem, str(unservable)))
                continue
            dropped.extend((path.stem, name) for name in names)
            if title_narrowed(payload.get("title")):
                narrowed.append((path.stem, "title"))
            unresolved.extend((relative, key) for key in missing)
            _dump(site / SITE_BOOK_DIR / f"{book['slug']}.json", book)
            books += 1

        declared, index_unread = _declared_keys(bundle / SITE_INDEX_FILE)
        unresolved.extend(
            (SITE_INDEX_FILE, key) for key in declared if key not in entries
        )
        unlisted = sorted(key for key in entries if key not in set(declared))
    else:
        unlisted = []

    # Always written, even with no bundle: the site has a library page, so it
    # has a library index, and an empty one is a true statement about an
    # empty bundle rather than a missing file the page has to guess about.
    _dump(site / SITE_INDEX_FILE, served_index(entries))

    return AssembleReport(
        site_dir=site,
        puzzle_count=count,
        capacity_bits=capacity,
        book_count=books,
        dropped=tuple(sorted(dropped)),
        narrowed=tuple(sorted(narrowed)),
        refused=tuple(sorted(refused)),
        ignored=tuple(sorted(ignored)),
        copied=tuple(sorted(copied)),
        unresolved=tuple(sorted(unresolved)),
        unlisted=tuple(unlisted),
        index_unread=index_unread,
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
    parser.add_argument(
        "--force",
        action="store_true",
        help="erase --out even when it is not a directory a previous run wrote",
    )
    args = parser.parse_args(argv)
    if args.capacity:
        print(
            f"{free_capacity_bits():.2f} bits of free capacity in the "
            f"{len(SERVED_VALUE_SPACE)} counted served fields; trip-wire "
            f"ceiling {CAPACITY_CEILING_BITS} bits "
            f"({MIN_SIZE}x{MIN_SIZE} cells, the smallest published grid)"
        )
        for name, count in sorted(SERVED_VALUE_SPACE.items()):
            determined = DETERMINED_BY_CLUES.get(name)
            why = f" (determined by clues.{determined})" if determined else ""
            print(f"  {name}: {count} values, {math.log2(count):.2f} bits{why}")
        print(f"  exempt, uncounted (ADR-0041): {', '.join(sorted(EXEMPT_SERVED_FIELDS))}")
        print(
            "The ceiling establishes only that no served field is wide enough "
            "to carry a grid. EC-048's threshold is one cell; see the module "
            "docstring for what carries it and for the residual."
        )
        print(
            "The two served LISTINGS are counted separately and are NOT under "
            "that ceiling: every entry field is mirrored from a puzzle file "
            f"({', '.join(sorted(MIRRORED_FROM_PUZZLE_FILE))}) and so adds 0 "
            "free bits, and the rest is declared residual:"
        )
        print(
            f"  exempt, by the owner's 2026-10-28 decision: "
            f"{', '.join(sorted(EXEMPT_LISTING_FIELDS))} on "
            f"{SITE_BOOK_DIR}/<slug>.json only, "
            f"{book_title_residual_bits():.2f} bits "
            f"({SERVED_TITLE_MAX_CHARS} chars x {TITLE_CODE_POINTS} code "
            f"points) — above this ceiling and above {MAX_SIZE}x{MAX_SIZE} "
            f"= {MAX_SIZE * MAX_SIZE} cells, so an exemption and not a bound"
        )
        print(
            f"  declared residual, structural: "
            f"{', '.join(sorted(LISTING_STRUCTURE_FIELDS))} — a book's ORDER "
            "log2(k!) bits and its MEMBERSHIP log2(C(N,k)) bits, for k "
            "puzzles of N published"
        )
        print(
            "  the PICTURE NAME is in none of it and is refused by name "
            "(EC-048): a book's display title and a puzzle's title are "
            "different fields."
        )
        return 0
    if args.out is None:
        parser.error("--out is required unless --capacity is given")
    report = assemble(args.bundle, args.out, force=args.force)
    print(f"{report.puzzle_count} puzzles into {report.site_dir}")
    print(f"  {report.book_count} book landings")
    for listing, key in report.unresolved:
        print(f"  unresolved {key}: {listing} names it and no puzzle file was served")
    if report.unlisted:
        print(f"  not in the bundle's index: {', '.join(report.unlisted)}")
    if report.index_unread is not None:
        print(f"  the bundle's index was not consulted: {report.index_unread}")
    if report.dropped:
        fields = sorted({name for _, name in report.dropped})
        print(f"  dropped (not in the served schema): {', '.join(fields)}")
    for key, field in report.narrowed:
        print(f"  narrowed {key}: {field} was outside the served vocabulary, so it is blank")
    for key, reason in report.refused:
        print(f"  refused {key}: {reason}")
    if report.ignored:
        print(f"  not served by this page: {', '.join(report.ignored)}")
    return 0


if __name__ == "__main__":  # pragma: no cover - the command line
    sys.exit(main())
