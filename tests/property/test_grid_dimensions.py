"""Grid extent as a pair: three standing properties from CARD-027, two from CARD-033.

This file replaces ``tests/property/test_size_range.py``, whose subject — one
scalar edge length in 10..30 — stopped existing when FR-018/ADR-0022 made grid
extent a ``(width, height)`` pair. It is a replacement rather than an addition
because the old property is a strictly weaker statement about the new domain: a
corpus that only ever moves both sides together cannot tell "each side is
checked" from "the larger side is checked", which is precisely the confusion the
pair introduces.

Five properties live here — three CARD-027's, two CARD-033's.

**EC-005 — PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30.**
For every source mode, and for every ``(width, height)`` with *either* side
outside 10..30, the request is refused by the one shared pure domain validator
before any grid is produced; and the CLI adapter enforces no part of that range
itself. Four claims, each of which a per-mode example test can miss:

1. *Every* pair, not four of them, and the two sides move **independently** —
   the corpus below walks each side across both bounds while the other is held
   legal, then adds seeded far-away magnitudes and mixed pairs. A minimum case
   count is asserted inside each test so the corpus cannot silently shrink (no
   ``hypothesis`` here — CLAUDE.md's test policy).
2. *The shared validator*, not a per-mode restatement. Each mode's refusal is
   compared against ``random_grid.validate_extent``'s own message for the same
   pair, byte for byte. A mode that grew its own copy of the bound would still
   raise ``SizeOutOfRange`` and would still pass a test that only checked the
   exception type; it would not produce the same sentence, and it would drift
   the first time the bound moved.
3. *Naming the offending side.* With two independent sides an unattributed
   message leaves the user guessing which number they typed wrong, so the
   message is required to say ``width`` or ``height``, and to say the one that
   is actually at fault.
4. *Before any grid is produced.* Each mode's source is called with arguments
   that would otherwise do real work (a real template key, a real image file),
   and nothing comes back.

**ADR-0022/R1 — PropertyTest_Extent_NoPublicBoundaryReducesGridToOneScalar.**
A structural property, enforced the way ``tests/test_cli.py`` enforces the
ADR-0007 import rule: by walking ``src/nonogram/**/*.py`` on disk with ``ast``.
So a module a later card adds is covered from the moment it lands, rather than
when someone remembers to extend a list.

**ADR-0022/R2 — PropertyTest_Extent_RangeRejectionAlwaysComesFromTheDomain.**
For every well-formed token a user can type, the refusal comes from the domain
(the tool's message, exit code 3) and never from argparse (a usage error, exit
code 2). Its converse is asserted too: a *malformed* token is argparse's, and
builds no request at all.

**EC-009 — PropertyTest_DeriveShape_ShortSideIsRoundedRatioClampedAtMinOrRefused.**
CARD-033's arithmetic property, over every supported ``N`` and a seeded corpus
of source ratios rather than over the four ratios its acceptance criteria name.
Four claims: the long side is always exactly ``N``; the short side is
``round(N * short/long)`` while that is at least ``MIN_SIZE``; it is held at
``MIN_SIZE`` below that; and the request is refused exactly when the source is
more elongated than ``N/5 : 1``, with the refusal naming the smallest ``N`` that
would take it. The expected short side is computed independently, with
``Fraction`` and explicit tie-breaking, so an implementation and its test cannot
agree by sharing an expression.

**ADR-0022/R4 — PropertyTest_BareSize_DerivesShorterSideFromSourceShape.** The
same rule seen from outside, through all three source modes at once: for every
mode and every supported ``N``, a bare ``--size N`` resolves to a grid the
*source's own shape* explains, and the grid the mode then produces has exactly
those dimensions. Random staying square and library staying square are asserted
here as consequences of their reported shapes, not as exceptions — which is what
would catch a derivation that special-cased a mode (guardrail G-2).

The positive half of each property is asserted as well, because a validator that
rejected everything, or a parser that accepted nothing, would satisfy the
negative halves completely.
"""

from __future__ import annotations

import ast
import random
from fractions import Fraction
from pathlib import Path

import pytest
from PIL import Image

from nonogram import cli, difficulty, orchestrator, sourcing
from nonogram.errors import (
    ImageNeedsManualCrop,
    SizeOutOfRange,
    SizeTooSmallForSource,
)
from nonogram.sourcing import image, library, random_grid

#: A real image, so image mode's refusal happens before the file is opened
#: rather than because there was nothing to open. It is square (32x32), which
#: matters for the acceptance half — see ``_fits_the_aspect_band``.
BANDS = Path(__file__).parent.parent / "fixtures" / "bands.png"

#: A real template key, for the same reason on the library side.
LIBRARY_KEY = "cat"

SEED = 20260901

#: The bounds this property is about, named rather than read from
#: ``random_grid`` — a property test that derives its expectation from the
#: constant under test follows that constant anywhere and asserts nothing about
#: where the boundary is. The constants are pinned against these numbers once,
#: below, and everything else is built from the numbers.
MIN_SUPPORTED = 10
MAX_SUPPORTED = 30

#: A dense band across both bounds: every integer from well below the minimum
#: to well above the maximum, so the two transitions are covered exhaustively
#: rather than sampled.
_BAND = range(-20, 81)

#: An in-range partner for a side under test. Neither bound, so a pair built
#: from it isolates the side that is moving.
_LEGAL_PARTNER = 17


def _far_sides(rng: random.Random) -> list[int]:
    """Magnitudes no hand-written band would reach, drawn reproducibly."""
    return [rng.randint(81, 10_000) for _ in range(40)] + [
        -rng.randint(81, 10_000) for _ in range(40)
    ]


def _in_range(side: int) -> bool:
    return MIN_SUPPORTED <= side <= MAX_SUPPORTED


def _corpus() -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    """The ``(rejected, accepted)`` extent corpora this file runs over.

    Built so the two sides genuinely move independently:

    * every candidate side paired with a legal partner **as the width** and,
      separately, **as the height** — the pairs that distinguish a per-side rule
      from a rule about one of the two;
    * every candidate side paired with itself — the square corpus the scalar
      predecessor had, kept so nothing it covered is lost;
    * a seeded sample of mixed pairs where *both* sides are drawn freely, which
      is where an implementation that validated only the larger side, or only
      the first argument, is caught;
    * the full 21x21 product of in-range sides as the acceptance corpus, so
      every legal rectangle is generated, not just the square diagonal.
    """
    rng = random.Random(SEED)
    sides = sorted({*_BAND, *_far_sides(rng)})

    pairs: set[tuple[int, int]] = set()
    for side in sides:
        pairs.add((side, _LEGAL_PARTNER))
        pairs.add((_LEGAL_PARTNER, side))
        pairs.add((side, side))
    for _ in range(300):
        pairs.add((rng.choice(sides), rng.choice(sides)))

    rejected = sorted(p for p in pairs if not (_in_range(p[0]) and _in_range(p[1])))
    accepted = [
        (width, height)
        for width in range(MIN_SUPPORTED, MAX_SUPPORTED + 1)
        for height in range(MIN_SUPPORTED, MAX_SUPPORTED + 1)
    ]
    return rejected, accepted


def _offending_side(width: int, height: int) -> str:
    """Which side the message must name — width first when both are wrong.

    The declared order (CARD-027's failure matrix, row 4), restated here rather
    than read off the implementation, so a change to the order fails this test
    instead of silently redefining what it checks.
    """
    return "width" if not _in_range(width) else "height"


def _fits_the_aspect_band(width: int, height: int) -> bool:
    """Whether image mode will convert :data:`BANDS` into this grid at all.

    ``bands.png``'s **ink bounding box** is square — the fixture carries a rule
    along its bottom edge precisely so that the box is its whole 32x32 sheet,
    asserted by ``test_the_fixture_images_are_present_and_shaped_as_documented``
    in ``tests/test_sourcing_image.py``. Since CARD-030 the box, not the file, is
    what FR-021's ">2x refusal" judges (ADR-0022/R3 as revised 2026-09-01), so
    the guard accepts exactly the grids whose own ratio is within 2x of 1. The
    fixture being square in *file* terms no longer implies that on its own.

    That guard is a *different* rule from the range one
    this file is about, and it runs after it — so the acceptance half filters
    the pairs it would refuse rather than asserting anything about them. What
    the guard does with the pairs outside the band is
    ``tests/property/test_image_fit.py``'s property, not this one.
    """
    return min(width, height) * 2 >= max(width, height)


def _call_for(mode: str):  # type: ignore[no-untyped-def]
    """The mode's source, reduced to a callable of ``(width, height)``.

    Every other argument is a real one — a real template key, a real image file
    — so a refusal can never be an artefact of a missing template or an absent
    path.
    """
    source = sourcing.for_mode(mode)
    rng = random.Random(SEED)
    match mode:
        case sourcing.RANDOM:
            return lambda width, height: source(width, height, 30, rng)
        case sourcing.LIBRARY:
            return lambda width, height: source(LIBRARY_KEY, width, height, rng)
        case sourcing.IMAGE:
            return lambda width, height: source(BANDS, width, height, rng)
    raise AssertionError(f"unhandled source mode {mode!r}")


def test_the_range_this_property_is_written_around_is_the_one_in_force() -> None:
    """The one place this file reads the constants, so the rest can name numbers."""
    assert (random_grid.MIN_SIZE, random_grid.MAX_SIZE) == (
        MIN_SUPPORTED,
        MAX_SUPPORTED,
    )
    assert set(sourcing.MODES) == {sourcing.RANDOM, sourcing.LIBRARY, sourcing.IMAGE}


def test_the_corpus_really_does_move_the_two_sides_independently() -> None:
    """The corpus's own precondition, asserted rather than assumed.

    EC-005 warns that a corpus which only ever moves the sides together cannot
    distinguish "each side is checked" from "the larger side is checked". This
    is that warning turned into a check on the fixture: the rejected corpus must
    contain pairs legal on the width and illegal on the height, pairs the other
    way round, and pairs illegal on both — in quantity, not as one example each.
    """
    rejected, accepted = _corpus()

    bad_width_only = [p for p in rejected if not _in_range(p[0]) and _in_range(p[1])]
    bad_height_only = [p for p in rejected if _in_range(p[0]) and not _in_range(p[1])]
    both_bad = [p for p in rejected if not _in_range(p[0]) and not _in_range(p[1])]

    assert len(bad_width_only) >= 140, "the width-only corpus has shrunk"
    assert len(bad_height_only) >= 140, "the height-only corpus has shrunk"
    assert len(both_bad) >= 140, "the both-sides-bad corpus has shrunk"
    assert len(accepted) == 441, "the acceptance corpus is no longer the 21x21 product"
    assert sum(1 for w, h in accepted if w != h) == 420


@pytest.mark.parametrize("mode", sourcing.MODES)
def test_every_source_mode_rejects_every_side_outside_ten_to_thirty(mode: str) -> None:
    """EC-005, claims 1-4: every out-of-range pair, refused by the shared rule.

    ``PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30``.
    """
    rejected, _ = _corpus()
    call = _call_for(mode)

    assert len(rejected) >= 500, "the rejection corpus has shrunk"

    for width, height in rejected:
        with pytest.raises(SizeOutOfRange) as raised:
            call(width, height)

        with pytest.raises(SizeOutOfRange) as shared:
            random_grid.validate_extent(width, height)

        assert str(raised.value) == str(shared.value), (mode, width, height)
        assert _offending_side(width, height) in str(raised.value), (width, height)


@pytest.mark.parametrize("mode", sourcing.MODES)
def test_every_source_mode_accepts_every_extent_inside_ten_to_thirty(mode: str) -> None:
    """The positive half: a validator that refused everything would be useless.

    Every legal rectangle, in every mode, comes back as exactly ``height`` rows
    of ``width`` cells — which is also the assertion that no mode transposes the
    pair, since 420 of the 441 cases are not square.
    """
    _, accepted = _corpus()
    call = _call_for(mode)
    convertible = [
        pair
        for pair in accepted
        if mode != sourcing.IMAGE or _fits_the_aspect_band(*pair)
    ]

    assert len(convertible) >= 300, "the acceptance corpus has shrunk"
    assert sum(1 for w, h in convertible if w != h) >= 280

    for width, height in convertible:
        grid = call(width, height)

        assert len(grid) == height, (mode, width, height)
        assert {len(row) for row in grid} == {width}, (mode, width, height)


def test_a_missing_side_is_the_same_domain_error_in_every_mode() -> None:
    """``None`` is the shape an omitted ``--size`` has when it reaches a source.

    It must be a domain error from the shared validator, never a ``TypeError``
    from comparing ``None`` with an int — the failure mode a per-mode
    reimplementation of the bound would be most likely to produce. Checked on
    each axis separately, because ``--size`` is one flag but two fields, and a
    half-filled extent is exactly what a future adapter bug would produce.
    """
    for width, height in ((None, None), (None, 20), (20, None)):
        with pytest.raises(SizeOutOfRange) as shared:
            random_grid.validate_extent(width, height)

        for mode in sourcing.MODES:
            with pytest.raises(SizeOutOfRange) as raised:
                _call_for(mode)(width, height)

            assert str(raised.value) == str(shared.value), (mode, width, height)


def test_an_out_of_band_image_request_is_still_refused_before_any_grid() -> None:
    """The one refusal the acceptance half filters out, pinned so it is not lost.

    The aspect guard is CARD-026's and this card does not own it (guardrail
    G-6), but the acceptance corpus above *skips* the pairs it refuses — so this
    states plainly that those pairs are refused rather than quietly converted.
    A 30x10 grid against a square source keeps a third of the picture, which is
    exactly what FR-021 exists to stop.
    """
    with pytest.raises(ImageNeedsManualCrop):
        _call_for(sourcing.IMAGE)(30, 10)


def test_difficultys_cell_span_agrees_with_the_source_range() -> None:
    """The range's *second* definition, bound to the first from the test tree.

    ``difficulty.py`` restates the supported range as cell counts —
    ``MIN_SUPPORTED_CELLS = 10 * 10`` and ``MAX_SUPPORTED_CELLS = 30 * 30`` —
    and CARD-023 had to hand-edit the maximum from ``50 * 50`` alongside
    ``random_grid.MAX_SIZE``. Two definitions of one fact, kept in step by
    hand, is a silent-drift hazard: the next range change can move one and
    leave the other, and nothing in ``tests/test_difficulty.py`` would fail
    because it imports difficulty's own constants.

    The duplication cannot be removed. ``difficulty`` (COMP-006) and
    ``random_grid`` (COMP-003) are both capability modules, and ADR-0007
    forbids a lateral import between them — the structural guard in
    ``tests/test_cli.py`` would fail the moment ``difficulty`` imported
    ``random_grid`` to derive the constant. So the binding has to live where
    a cross-boundary import is legal, which is here in the test tree.

    The two constants are the *square* corners of the extent space, and stay so
    deliberately: they are the smallest and largest cell counts a legal request
    can have, which is what a normalizer denominator needs, and CARD-027's
    guardrail G-4 leaves open whether area is the right normalizer for a
    rectangle at all. This test pins the arithmetic, not that question.

    This is not a gate: ``difficulty`` clamps rather than raises, so a
    disagreement would skew difficulty scores rather than admit an
    out-of-range grid. It is exactly the kind of quiet wrongness that a
    property file about the range should refuse to leave unpinned.
    """
    assert difficulty.MIN_SUPPORTED_CELLS == random_grid.MIN_SIZE**2
    assert difficulty.MAX_SUPPORTED_CELLS == random_grid.MAX_SIZE**2


# --------------------------------------------------------------------------
# ADR-0022/R1 — PropertyTest_Extent_NoPublicBoundaryReducesGridToOneScalar
# --------------------------------------------------------------------------

_PACKAGE_DIR = Path(__file__).resolve().parents[2] / "src" / "nonogram"

#: Names that would mean "a grid's extent, as one number". ``size`` is the one
#: the codebase actually used; the rest are the plausible renames a later card
#: might reach for instead, so the rule cannot be satisfied by a synonym.
_SCALAR_EXTENT_NAMES = frozenset(
    {"size", "grid_size", "edge", "edge_length", "side", "n"}
)

def _is_public(name: str) -> bool:
    return not name.startswith("_")


def _annotation_is_int(node: ast.expr | None) -> bool:
    """Does this annotation admit an ``int``, structurally rather than by spelling?

    A grid extent is a number of cells, so an extent-named binding that admits
    an ``int`` is a scalar-extent boundary. What must NOT be caught is
    ``difficulty.SignalWeights.size``, a ``float`` normalizer weight that has
    nothing to do with how big a grid is (and which guardrail G-4 forbids
    touching anyway).

    This was first written as exact string equality against four spellings, and
    cycle-1 review broke it in five ways: ``typing.Optional[int]``,
    ``Annotated[int, ...]``, ``builtins.int`` and the string form ``'int'`` all
    slipped past, and so did an **unannotated** parameter — an undeclared third
    exclusion the comment did not admit to. The comment additionally claimed the
    exclusion "cannot be stretched to cover a real violation", which was exactly
    backwards. So the test now walks the annotation instead of spelling it:

    * any ``int`` reachable in the annotation's own tree counts — that covers
      unions, ``Optional``, ``Annotated``, and dotted forms like
      ``builtins.int``, without enumerating them;
    * a string annotation is re-parsed and walked, so quoting is not an escape;
    * **an absent annotation counts as a hit**. An unannotated public parameter
      called ``size`` is a scalar-extent boundary whatever anyone intended, and
      this project has no mypy or ruff to notice it. That is a real rule, and it
      is declared here rather than left as a silent third exclusion.

    ``float`` is excluded because ``float`` contains no ``int`` NODE — the walk
    is token-level, not substring, so ``Point`` and ``print`` do not match either.
    """
    if node is None:
        return True
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        try:
            node = ast.parse(node.value, mode="eval").body
        except SyntaxError:
            return True
    for sub in ast.walk(node):
        if isinstance(sub, ast.Name) and sub.id == "int":
            return True
        if isinstance(sub, ast.Attribute) and sub.attr == "int":
            return True
    return False


def _scalar_extent_offences(path: Path) -> list[str]:
    """Public signatures and fields in one module that reduce extent to one int.

    Walked with ``ast`` rather than by importing, exactly as ``tests/test_cli.py``
    walks the package for the ADR-0007 import rule: a source-level check covers
    a module that fails to import and does not depend on what a module happens
    to re-export.

    Three shapes are checked, because a boundary can leak an extent through any
    of them: a *parameter* of a public function, an annotated *field* of a
    public class, and the *name* of a public accessor returning an int (a
    ``size`` property is as much a scalar boundary as a ``size`` argument).
    Private helpers are exempt: they are not module boundaries, and the type
    size ``export/pdf._header_font(size: int)`` takes is not a grid at all.
    """
    offences: list[str] = []
    tree = ast.parse(path.read_text(encoding="utf-8"))

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and _is_public(node.name):
            for statement in node.body:
                # AnnAssign is the annotated field (`size: int = 30`); Assign is
                # the BARE one (`size = 30`). Cycle 1 cited both shapes as
                # evasions and cycle 2 found only the first had been closed —
                # the bare form matters most, because `web/` (which CARD-028
                # edits next) is exactly where a bare class attribute would go.
                if isinstance(statement, ast.AnnAssign):
                    targets = [statement.target]
                    annotated = statement.annotation
                elif isinstance(statement, ast.Assign):
                    targets = list(statement.targets)
                    annotated = None  # absent annotation counts as a hit
                else:
                    continue
                for target in targets:
                    if (
                        isinstance(target, ast.Name)
                        and _is_public(target.id)
                        and target.id in _SCALAR_EXTENT_NAMES
                        and _annotation_is_int(annotated)
                    ):
                        offences.append(
                            f"{path.name}:{statement.lineno} "
                            f"{node.name}.{target.id} is a scalar extent field"
                        )

        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        if not _is_public(node.name):
            continue
        arguments = node.args
        for argument in (
            *arguments.posonlyargs,
            *arguments.args,
            *arguments.kwonlyargs,
        ):
            if argument.arg in _SCALAR_EXTENT_NAMES and _annotation_is_int(
                argument.annotation
            ):
                offences.append(
                    f"{path.name}:{node.lineno} {node.name}({argument.arg}: int) "
                    "takes a scalar extent"
                )
        if node.name in _SCALAR_EXTENT_NAMES and _annotation_is_int(node.returns):
            offences.append(
                f"{path.name}:{node.lineno} {node.name}() is a scalar extent accessor"
            )

    return offences


def test_no_public_boundary_reduces_a_grid_to_one_scalar() -> None:
    """ADR-0022/R1, over the whole package rather than over the files one card
    happened to touch.

    ``PropertyTest_Extent_NoPublicBoundaryReducesGridToOneScalar``. A module a
    later card adds is covered from the moment it lands, which is the same
    reason ``tests/test_cli.py`` discovers the package from disk for the
    ADR-0007 import rule.
    """
    modules = sorted(_PACKAGE_DIR.rglob("*.py"))
    assert len(modules) >= 20, "the package walk found suspiciously few modules"

    offences = [
        offence for path in modules for offence in _scalar_extent_offences(path)
    ]

    assert offences == []


#: What the ADR-0022/R1 guard reaches, as a TABLE rather than as prose or a
#: shell probe. Each row is one source shape and whether the guard must flag it.
#:
#: This exists because of how cycles 1 and 2 went, and the pattern is worth
#: naming: cycle 1 found the guard overclaimed in a comment, and the remedy was
#: a longer comment; cycle 2 found holes by probing, and the remedy was a probe
#: run in a shell. Neither left anything behind. Cycle 2 then proved the point —
#: reverting the whole cycle-1 resolver fix left the suite GREEN, because the
#: teeth test only ever exercised spellings the OLD code already matched. A
#: guard whose reach is established by ad-hoc probe is a guard whose reach is
#: unpinned.
#:
#: So the rows below include the shapes that are DELIBERATELY NOT REACHED. The
#: guard walks annotation syntax and never resolves a name binding, so a type
#: alias defeats it. That is a real limit, and an honest declared limit is worth
#: more than an undeclared one: if a later card closes it, this table fails and
#: has to be updated, which is exactly the notification we want.
_GUARD_SHAPES: tuple[tuple[str, str, bool], ...] = (
    # (label, source, must_be_flagged)
    ("plain int param",        "def g(k, size: int, r): ...", True),
    ("Optional[int] param",    "import typing\ndef g(k, size: typing.Optional[int], r): ...", True),
    ("Annotated[int] param",   "from typing import Annotated\ndef g(k, size: Annotated[int, 'cells'], r): ...", True),
    ("dotted builtins.int",    "import builtins\ndef g(k, size: builtins.int, r): ...", True),
    ("stringized 'int'",       "def g(k, size: 'int', r): ...", True),
    ("stringized union",       "def g(k, size: 'int | None', r): ...", True),
    ("unannotated param",      "def g(k, size, r): ...", True),
    ("annotated class field",  "class R:\n    size: int = 30\n", True),
    ("BARE class field",       "class R:\n    size = 30\n", True),
    ("int accessor",           "class R:\n    @property\n    def size(self) -> int: ...\n", True),
    # CARD-033's near miss, pinned because it is the signature FR-023 invites:
    # "take the bare N and derive the pair". Written with a scalar parameter it
    # is a scalar-extent boundary whatever it returns, and the guard says so —
    # which is why ``random_grid.derive_extent`` takes the half-stated PAIR
    # instead and this row stays a probe rather than a description of the code.
    ("scalar N derivation",    "def derive_extent(n: int, w: int, h: int) -> tuple[int, int]: ...", True),
    # Deliberately NOT reached — the guard resolves syntax, not name bindings.
    ("type alias (declared gap)",   "Size = int\ndef g(k, size: Size, r): ...", False),
    ("NewType (declared gap)",      "from typing import NewType\nCells = NewType('Cells', int)\ndef g(k, size: Cells, r): ...", False),
    # Must NOT be flagged — these are correct code.
    ("float weight",           "def g(k, size: float, r): ...", False),
    ("non-extent name",        "def g(k, count: int, r): ...", False),
    ("private helper",         "def _g(k, size: int, r): ...", False),
)


def test_the_guard_reaches_exactly_the_shapes_it_claims_to(tmp_path: Path) -> None:
    """Every shape in :data:`_GUARD_SHAPES`, checked against the real scanner.

    This is what pins the resolver. Cycle 2 demonstrated that without it the
    entire cycle-1 fix could be reverted with the suite staying green, because
    the teeth test below exercises only the scanner and only through spellings
    the pre-fix resolver already matched.

    The rows asserting ``False`` are as load-bearing as the rows asserting
    ``True``: two of them are DECLARED GAPS (a type alias and a ``NewType``
    defeat the guard, because it walks annotation syntax and never resolves a
    name binding), and pinning them means a later card that closes the gap gets
    a failing test telling it to update this table, rather than leaving the
    declaration quietly wrong.
    """
    for label, source, must_flag in _GUARD_SHAPES:
        module = tmp_path / "probe.py"
        module.write_text(source, encoding="utf-8")
        flagged = bool(_scalar_extent_offences(module))
        assert flagged is must_flag, (
            f"{label}: guard {'missed' if must_flag else 'wrongly flagged'} "
            f"this shape — if that is a deliberate change, update _GUARD_SHAPES"
        )


def test_the_scalar_extent_guard_would_catch_a_violation(tmp_path: Path) -> None:
    """The guard's own teeth, checked against a module written to fail it.

    Without this, a scanner that silently matched nothing — a typo in a node
    type, a walk that never recursed — would pass the test above forever while
    enforcing nothing.
    """
    offending = tmp_path / "regression.py"
    offending.write_text(
        "from dataclasses import dataclass\n"
        "\n"
        "def generate(size: int) -> list[list[bool]]: ...\n"
        "\n"
        "@dataclass\n"
        "class Request:\n"
        "    size: int | None = None\n"
        "\n"
        "class Puzzle:\n"
        "    @property\n"
        "    def size(self) -> int | None: ...\n",
        encoding="utf-8",
    )

    offences = _scalar_extent_offences(offending)

    assert len(offences) == 3
    assert any("takes a scalar extent" in offence for offence in offences)
    assert any("scalar extent field" in offence for offence in offences)
    assert any("scalar extent accessor" in offence for offence in offences)


def test_the_scalar_extent_guard_leaves_the_two_declared_exclusions_alone(
    tmp_path: Path,
) -> None:
    """...and does not fire on the two shapes CARD-027 declared out of scope.

    A private helper taking a type size in pixels, and a ``float`` normalizer
    weight that happens to be called ``size``. Both exist in the package today
    (``export/pdf._header_font`` and ``difficulty.SignalWeights.size``), and
    both are exercised here as source rather than by name, so the exclusions are
    a property of the rule rather than an allowlist someone has to maintain.
    """
    allowed = tmp_path / "allowed.py"
    allowed.write_text(
        "from dataclasses import dataclass\n"
        "\n"
        "def _header_font(size: int) -> object: ...\n"
        "\n"
        "@dataclass\n"
        "class SignalWeights:\n"
        "    size: float = 0.15\n"
        "\n"
        "def generate(width: int, height: int) -> list[list[bool]]: ...\n",
        encoding="utf-8",
    )

    assert _scalar_extent_offences(allowed) == []


# --------------------------------------------------------------------------
# ADR-0022/R2 — PropertyTest_Extent_RangeRejectionAlwaysComesFromTheDomain
# --------------------------------------------------------------------------


def test_the_cli_enforces_no_part_of_the_range_itself() -> None:
    """``PropertyTest_Extent_RangeRejectionAlwaysComesFromTheDomain``.

    Every extent this file refuses inward must still *parse* at the adapter and
    arrive unchanged, so that the domain is what refuses it (ADR-0010). A
    ``type=``/``choices=`` range check in ``cli`` would make every test above
    pass while moving the decision out of the domain — the tests above call the
    sourcing modules directly and would never notice.

    Both token forms are exercised for every pair: the ``WxH`` form always, and
    the bare ``N`` form whenever the pair is square, since that is the shorthand
    a user would actually type for it. Since CARD-033 a bare token parses to
    ``(N, None)`` — the one number it contains, with the shape left for
    ``random_grid.derive_extent`` to complete (FR-023) — so what is asserted of
    it here is that the *number* still arrives unjudged, which is the whole of
    this property's subject. Whether ``None`` is then filled in correctly is
    ``PropertyTest_BareSize_DerivesShorterSideFromSourceShape``'s, below.
    """
    rejected, accepted = _corpus()
    parser = cli.build_parser()

    assert len(rejected) >= 500

    for width, height in rejected + accepted:
        args = parser.parse_args(["generate", "--size", f"{width}x{height}"])
        assert args.extent == (width, height)

        if width == height and width >= 0:
            bare = parser.parse_args(["generate", "--size", str(width)])
            assert bare.extent == (width, None)


def test_a_malformed_token_is_argparses_and_an_out_of_range_one_is_not() -> None:
    """The two halves of the placement rule, side by side.

    ADR-0010 draws the line at *syntax*: splitting ``WxH`` is the adapter's, the
    10..30 bound is the domain's. Stating both directions in one test is what
    makes the line visible — either assertion alone is satisfied by putting
    everything on one side of it.
    """
    parser = cli.build_parser()

    # Well formed, wildly out of range: parses, and reaches the domain intact.
    assert parser.parse_args(["generate", "--size", "9999x1"]).extent == (9999, 1)

    # Malformed: argparse's, before any request exists.
    for token in ("30x", "x20", "3x4x5", "30X20"):
        with pytest.raises(SystemExit) as excinfo:
            parser.parse_args(["generate", "--size", token])
        assert excinfo.value.code == cli.ExitCode.USAGE


# --------------------------------------------------------------------------
# EC-009 — PropertyTest_DeriveShape_ShortSideIsRoundedRatioClampedAtMinOrRefused
# ADR-0022/R4 — PropertyTest_BareSize_DerivesShorterSideFromSourceShape
# --------------------------------------------------------------------------

#: How many source ratios the derivation corpus carries, per side of the
#: boundary. Asserted inside the tests, so the corpus cannot silently shrink.
_RATIO_SAMPLES = 240


def _ratio_corpus() -> list[tuple[int, int]]:
    """``(short, long)`` pixel extents for the derivation property to run over.

    Three groups, each answering a different way the rule could be wrong:

    * **hand-placed exact boundaries** — for every supported ``N``, a source of
      ratio exactly ``N/5 : 1`` (which must be accepted, with the short side
      landing on ``MIN_SIZE``) and one pixel past it (which must be refused).
      Sampling alone would step over both;
    * **hand-placed round ratios** — 1:1, 2:1, 3:2, 16:9 and their transposes,
      the shapes real pictures actually are;
    * **a seeded random sweep**, half of it across the whole 1:1..12:1 range
      and half confined to 1:1..2:1, so the corpus is not a list of the cases
      somebody thought of *and* still has plenty of accepted cases at
      ``--size 10``, whose ceiling is 2:1 and which an unweighted sweep would
      leave almost entirely on the refused side.

    Square sources appear too (``short == long``), because "a source with no
    shape of its own is a square" has to be the same code path as everything
    else here (guardrail G-2).
    """
    rng = random.Random(SEED)
    pairs: set[tuple[int, int]] = set()

    for stated in range(MIN_SUPPORTED, MAX_SUPPORTED + 1):
        # Exactly N/5 : 1, as integers: short = 5k, long = N*k.
        for scale in (1, 7, 100):
            pairs.add((5 * scale, stated * scale))
        # And one pixel past it, at a scale where one pixel is a real step.
        pairs.add((1000, stated * 200 + 1))

    for short, long in ((1, 1), (2, 1), (3, 2), (9, 16), (4, 5), (10, 11)):
        pairs.add((short * 37, long * 37))
        pairs.add((min(short, long) * 37, max(short, long) * 37))

    while len(pairs) < _RATIO_SAMPLES:
        short = rng.randint(1, 900)
        widest = short * 12 if len(pairs) % 2 else short * 2
        pairs.add((short, rng.randint(short, widest)))

    return sorted(pairs)


def _rounded_half_to_even(numerator: int, denominator: int) -> int:
    """``round(numerator / denominator)`` computed exactly, without floats.

    The independent second implementation EC-009's "equals ``round(N * r)``" is
    checked against. It matters that this is written out rather than delegated
    to ``round(a / b)``: the two disagree only when the quotient is exactly a
    half-integer, which is precisely the input a shared expression would hide —
    and that input is reachable (``round(25 * 16/32)`` is one).

    Python's ``round`` breaks a tie to the nearest *even* integer, so this does
    too; the point is that the rule is stated somewhere other than in the code
    under test.
    """
    exact = Fraction(numerator, denominator)
    floored = exact.numerator // exact.denominator
    remainder = exact - floored
    if remainder > Fraction(1, 2):
        return floored + 1
    if remainder < Fraction(1, 2):
        return floored
    return floored if floored % 2 == 0 else floored + 1


def _expected_extent(
    stated: int, source_width: int, source_height: int
) -> tuple[int, int] | None:
    """What EC-009 says ``derive_extent`` must answer, or ``None`` for refused.

    Written from the requirement's own words rather than from the
    implementation: N on the source's longer axis, ``round(N * short/long)`` on
    the other with ``MIN_SIZE`` as a floor, and refused exactly when the
    source's ``long:short`` exceeds ``N/5``.
    """
    shorter = min(source_width, source_height)
    longer = max(source_width, source_height)
    if Fraction(longer, shorter) > Fraction(stated, 5):
        return None
    derived = max(MIN_SUPPORTED, _rounded_half_to_even(stated * shorter, longer))
    if source_width >= source_height:
        return stated, derived
    return derived, stated


def test_the_derivation_corpus_covers_both_sides_of_the_ceiling() -> None:
    """The corpus's own precondition, asserted rather than assumed.

    A corpus of only-acceptable ratios would let a derivation that never refuses
    pass the property below, and a corpus of only-refused ones would let one
    that always refuses. Both halves have to be there in quantity, at every N,
    and so does at least one source of each orientation.
    """
    corpus = _ratio_corpus()

    assert len(corpus) >= _RATIO_SAMPLES, "the ratio corpus has shrunk"

    for stated in (MIN_SUPPORTED, 20, MAX_SUPPORTED):
        expected = [_expected_extent(stated, short, long) for short, long in corpus]
        assert sum(1 for e in expected if e is None) >= 10, stated
        assert sum(1 for e in expected if e is not None) >= 30, stated

    assert any(short == long for short, long in corpus)
    assert any(short != long for short, long in corpus)


def test_the_derived_short_side_is_the_rounded_ratio_clamped_at_min_or_refused() -> None:
    """``PropertyTest_DeriveShape_ShortSideIsRoundedRatioClampedAtMinOrRefused``.

    EC-009 in full, over every supported ``N`` against the whole ratio corpus —
    ``21 * 240`` cases rather than the four its acceptance criteria name.

    Both orientations of every ratio are run, so "N is the longer side" is
    checked as a statement about the *source's* longer axis and not about the
    width. The refusal half checks the message as well as the exception: naming
    a size that does not work, or one larger than the smallest that does, is a
    wrong answer even though the refusal itself was right.
    """
    corpus = _ratio_corpus()
    assert len(corpus) >= _RATIO_SAMPLES

    checked = refused = clamped = 0
    for stated in range(MIN_SUPPORTED, MAX_SUPPORTED + 1):
        for short, long in corpus:
            for width, height in ((short, long), (long, short)):
                expected = _expected_extent(stated, width, height)
                checked += 1

                if expected is None:
                    refused += 1
                    with pytest.raises(SizeTooSmallForSource) as raised:
                        random_grid.derive_extent(stated, None, width, height)
                    _assert_names_the_smallest_working_size(
                        str(raised.value), stated, width, height
                    )
                    continue

                for pair in (
                    random_grid.derive_extent(stated, None, width, height),
                    random_grid.derive_extent(None, stated, width, height),
                ):
                    assert pair == expected, (stated, width, height)
                    # No top clamp, ever: the long side is exactly what was
                    # asked for, and both sides are in range (guardrail G-3).
                    assert max(pair) == stated
                    assert MIN_SUPPORTED <= min(pair) <= MAX_SUPPORTED
                    # FR-021's own guard, unchanged and on its own terms, must
                    # accept every grid this rule requests (guardrail G-4).
                    image.validate_aspect_ratio(width, height, *pair)

                if min(expected) == MIN_SUPPORTED:
                    clamped += 1

    assert checked >= 10_000, "the derivation corpus has shrunk"
    assert refused >= 500, "nothing was refused — the ceiling is not being tested"
    assert clamped >= 500, "nothing hit the floor — the clamp is not being tested"


def _assert_names_the_smallest_working_size(
    message: str, stated: int, source_width: int, source_height: int
) -> None:
    """A refusal must name the smallest ``--size N`` that would take the source.

    Or say plainly that none would. Both halves are checked against a search run
    here, over ``_expected_extent`` — the requirement's arithmetic, not the
    implementation's — so a message naming a size that does not work, or a
    needlessly large one, fails.
    """
    workable = [
        candidate
        for candidate in range(MIN_SUPPORTED, MAX_SUPPORTED + 1)
        if _expected_extent(candidate, source_width, source_height) is not None
    ]

    assert stated not in workable
    if workable:
        assert f"--size {workable[0]} or larger" in message
        # The counter-intuitive consequence FR-023 asks be carried rather than
        # deduced, and the remedy that is NOT FR-021's.
        assert "LARGER puzzle accepts a picture that a smaller one refuses" in message
        assert "Crop the picture yourself" not in message
    else:
        assert "No supported --size can follow it" in message
        assert "or larger" not in message


#: The source shapes the end-to-end property builds real pictures for. Kept
#: modest because each one is written to disk and decoded twice per case; the
#: exhaustive sweep over ratios is the arithmetic property above, and this one
#: is about the wiring reaching all three modes.
_IMAGE_SHAPES: tuple[tuple[int, int], ...] = (
    (120, 120),
    (240, 120),
    (120, 240),
    (300, 200),
    (200, 300),
    (400, 130),
    (130, 400),
    (500, 105),
)


def test_a_bare_size_derives_the_shorter_side_from_the_source_shape(
    tmp_path: Path,
) -> None:
    """``PropertyTest_BareSize_DerivesShorterSideFromSourceShape`` (ADR-0022/R4).

    The rule from outside, through every registered mode, for every supported
    ``N``:

    1. a bare ``--size N`` resolves to the extent the source's own reported
       shape explains — the same ``_expected_extent`` oracle the arithmetic
       property uses, fed with what ``sourcing.shape_for_mode`` says rather than
       with a shape written here. So random staying ``N x N`` and library
       staying ``N x N`` are *derived* facts about ``(1, 1)`` and ``(16, 16)``,
       and a mode-specific branch in the derivation would not produce them;
    2. the mode then really builds a grid of exactly those dimensions — the
       assertion a resolution-only test would leave open;
    3. an explicit ``--size WxH`` is untouched by any of it (AC-096);
    4. the long side is always ``N``. Never clamped at the top, in any mode, at
       any ratio (guardrail G-3).

    Images are solid black rectangles, so their ink bounding box is their whole
    extent and the ratio under test is the ratio written above.
    """
    for width, height in _IMAGE_SHAPES:
        Image.new("L", (width, height), 0).save(tmp_path / f"{width}x{height}.png")

    checked = 0
    for stated in range(MIN_SUPPORTED, MAX_SUPPORTED + 1):
        cases: list[tuple[str, dict[str, object], tuple[int, int]]] = [
            ("random", {"density": 30}, random_grid.source_shape()),
            (
                "library",
                {"library_key": LIBRARY_KEY},
                library.source_shape(LIBRARY_KEY),
            ),
        ]
        cases += [
            (
                "image",
                {"image": tmp_path / f"{width}x{height}.png"},
                (width, height),
            )
            for width, height in _IMAGE_SHAPES
        ]

        for mode, extras, shape in cases:
            expected = _expected_extent(stated, *shape)
            request = orchestrator.GenerationRequest(
                mode=mode, width=stated, **extras
            )
            if expected is None:
                with pytest.raises(SizeTooSmallForSource):
                    orchestrator._resolved_extent(request)
                continue

            resolved = orchestrator._resolved_extent(request)
            assert resolved == expected, (mode, stated, shape)
            assert max(resolved) == stated, (mode, stated, shape)

            grid = sourcing.for_mode(mode)(
                *orchestrator._source_arguments(request, resolved),
                random.Random(SEED),
            )
            assert len(grid) == resolved[1], (mode, stated, shape)
            assert {len(row) for row in grid} == {resolved[0]}, (mode, stated, shape)

            # (3) The same request with both sides stated keeps both sides.
            explicit = orchestrator.GenerationRequest(
                mode=mode, width=stated, height=MIN_SUPPORTED, **extras
            )
            assert orchestrator._resolved_extent(explicit) == (stated, MIN_SUPPORTED)
            checked += 1

    assert checked >= 180, "the end-to-end derivation corpus has shrunk"


def test_a_bare_size_out_of_range_is_refused_before_the_source_is_consulted() -> None:
    """The stated ``N`` faces the range rule first, and by the shared validator.

    Two claims in one. An out-of-range bare ``N`` is a ``SizeOutOfRange`` with
    ``random_grid.validate_extent``'s own message, byte for byte — the same
    guarantee this file makes for a fully-stated extent, so a bare token cannot
    reach the domain and get a second, differently-worded refusal. And it is
    refused *before* the source's shape is read, which for image mode is what
    keeps "an out-of-range request pays for nothing" true across a change that
    otherwise makes every bare-size image run decode its file.
    """
    for stated in (-5, 0, 9, 31, 9999):
        with pytest.raises(SizeOutOfRange) as shared:
            random_grid.validate_extent(stated, stated)
        with pytest.raises(SizeOutOfRange) as raised:
            random_grid.derive_extent(stated, None, 300, 400)

        assert str(raised.value) == str(shared.value), stated

    consulted = 0

    def counting_shape(*arguments: object) -> tuple[int, int]:
        nonlocal consulted
        consulted += 1
        return (300, 400)

    original = sourcing._SHAPES[sourcing.IMAGE]
    sourcing._SHAPES[sourcing.IMAGE] = counting_shape
    try:
        with pytest.raises(SizeOutOfRange):
            orchestrator._resolved_extent(
                orchestrator.GenerationRequest(mode="image", image=BANDS, width=31)
            )
        assert consulted == 1, (
            "the shape is read before the stated side is validated — an "
            "out-of-range request must not pay for a decode"
        )
    finally:
        sourcing._SHAPES[sourcing.IMAGE] = original
