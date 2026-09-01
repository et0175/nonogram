"""Grid extent as a pair: the three standing properties CARD-027 owns.

This file replaces ``tests/property/test_size_range.py``, whose subject — one
scalar edge length in 10..30 — stopped existing when FR-018/ADR-0022 made grid
extent a ``(width, height)`` pair. It is a replacement rather than an addition
because the old property is a strictly weaker statement about the new domain: a
corpus that only ever moves both sides together cannot tell "each side is
checked" from "the larger side is checked", which is precisely the confusion the
pair introduces.

Three properties live here.

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

The positive half of each property is asserted as well, because a validator that
rejected everything, or a parser that accepted nothing, would satisfy the
negative halves completely.
"""

from __future__ import annotations

import ast
import random
from pathlib import Path

import pytest

from nonogram import cli, difficulty, sourcing
from nonogram.errors import ImageNeedsManualCrop, SizeOutOfRange
from nonogram.sourcing import random_grid

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

    ``bands.png`` is square, so FR-021's ">2x refusal" (ADR-0022/R3, shipped by
    CARD-026 and untouched by this card) accepts exactly the grids whose own
    ratio is within 2x of 1. That guard is a *different* rule from the range one
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

#: Annotations that could carry a cell count. A grid extent is a number of
#: cells, so it is an ``int``; this is what excludes
#: ``difficulty.SignalWeights.size``, a ``float`` normalizer weight that has
#: nothing to do with how big a grid is (and that CARD-027's guardrail G-4
#: forbids touching). The exclusion is a property of the type, not an
#: allowlisted name, so it cannot be stretched to cover a real violation.
_INT_ANNOTATIONS = frozenset({"int", "int | None", "None | int", "Optional[int]"})


def _is_public(name: str) -> bool:
    return not name.startswith("_")


def _annotation_is_int(node: ast.expr | None) -> bool:
    return node is not None and ast.unparse(node) in _INT_ANNOTATIONS


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
                if (
                    isinstance(statement, ast.AnnAssign)
                    and isinstance(statement.target, ast.Name)
                    and _is_public(statement.target.id)
                    and statement.target.id in _SCALAR_EXTENT_NAMES
                    and _annotation_is_int(statement.annotation)
                ):
                    offences.append(
                        f"{path.name}:{statement.lineno} "
                        f"{node.name}.{statement.target.id} is a scalar extent field"
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
    a user would actually type for it.
    """
    rejected, accepted = _corpus()
    parser = cli.build_parser()

    assert len(rejected) >= 500

    for width, height in rejected + accepted:
        args = parser.parse_args(["generate", "--size", f"{width}x{height}"])
        assert args.extent == (width, height)

        if width == height and width >= 0:
            bare = parser.parse_args(["generate", "--size", str(width)])
            assert bare.extent == (width, width)


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
