"""COMP-003 tests — the random grid source and the mode-dispatch seam.

Acceptance-criterion traceability (cards CARD-003 and CARD-027; trace.yml
FR-019, FR-004). The architecture names each check in PascalCase; pytest
collects snake_case, so the mapping is spelled out here and repeated in each
test's docstring:

===========  ==============================================  ==================================================
AC           architecture test name                          test below
===========  ==============================================  ==================================================
AC-066       TestGenerateRandom_ProducesRequestedDimensions  test_generate_random_produces_requested_dimensions
AC-067       TestGenerateRandom_ProducesRectangularGrid      test_generate_random_produces_rectangular_grid
AC-068       TestGenerateRandom_AcceptsMaxSide30             test_generate_random_accepts_max_side_30
AC-069       TestGenerateRandom_RejectsSideAbove30           test_generate_random_rejects_side_above_30
AC-070       TestGenerateRandom_RejectsSideBelow10           test_generate_random_rejects_side_below_10
AC-010       TestGenerateRandom_RespectsDensityParameter     test_generate_random_respects_density_parameter
AC-011       TestGenerateRandom_RejectsInvalidDensity        test_generate_random_rejects_invalid_density
—            TestValidateExtent_RejectsSideAboveThirty       test_validate_extent_rejects_side_above_thirty
===========  ==============================================  ==================================================

AC-001..AC-004 (FR-001's square 10..50 range) are superseded and are not cited
here: FR-019 replaced FR-001, and AC-066..AC-070 replaced the four criteria
CARD-003 was written against, because a criterion phrased over one edge length
cannot say anything about a rectangle.

Everything after the AC block guards the seams the ACs do not describe: the
ADR-0015 reproducibility contract this card owns (guardrail G-4), the ADR-0012
boundary representation, and the dispatch table CARD-008/CARD-015 extend.

Every test constructs its own ``random.Random``, so nothing here depends on
global random state and no test can perturb another's draws.
"""

from __future__ import annotations

import ast
import random
from pathlib import Path

import pytest

from nonogram import errors, sourcing
from nonogram.sourcing import random_grid

SEED = 20260827


def _rng(seed: int = SEED) -> random.Random:
    return random.Random(seed)


def _shape(grid: list[list[bool]]) -> tuple[int, set[int]]:
    """``(row count, the set of row lengths)``.

    Two numbers rather than one, because a grid is a rectangle: the row count is
    its height and the (single-element) set of row lengths is its width. Written
    as a *set* so a ragged grid — rows of differing length — can never be
    mistaken for a rectangle of the right width.
    """
    return len(grid), {len(row) for row in grid}


# --------------------------------------------------------------------------
# Acceptance criteria
# --------------------------------------------------------------------------


def test_generate_random_produces_requested_dimensions() -> None:
    """AC-066 / TestGenerateRandom_ProducesRequestedDimensions (happy).

    A request for a 20x20 random grid produces a 20-column, 20-row black/white
    grid.
    """
    grid = random_grid.generate(20, 20, 30, _rng())

    assert _shape(grid) == (20, {20})
    # "black/white" is ADR-0012's boundary representation: plain bools, no
    # third unknown state at this seam.
    assert all(cell is True or cell is False for row in grid for cell in row)


def test_generate_random_produces_rectangular_grid() -> None:
    """AC-067 / TestGenerateRandom_ProducesRectangularGrid (happy, FR-018).

    A request for 30x12 produces 12 rows of 30 columns — *not* a square, and
    not the transpose. The two numbers differ and are both prime to the other's
    factors of interest, so a signature that swapped them would fail here rather
    than pass by symmetry.
    """
    grid = random_grid.generate(30, 12, 30, _rng())

    assert _shape(grid) == (12, {30})


def test_generate_random_accepts_max_side_30() -> None:
    """AC-068 / TestGenerateRandom_AcceptsMaxSide30 (boundary, CON-011).

    The largest supported grid, 30x30, is generated without error. The number
    is named here as well as read from the constant: a boundary test that only
    reads ``MAX_SIZE`` follows the constant wherever it moves and so proves
    nothing about *where* the boundary is — which is exactly the property
    CON-011 narrowed.
    """
    assert random_grid.MAX_SIZE == 30

    grid = random_grid.generate(random_grid.MAX_SIZE, random_grid.MAX_SIZE, 30, _rng())

    assert _shape(grid) == (30, {30})


def test_generate_random_rejects_side_above_30() -> None:
    """AC-069 / TestGenerateRandom_RejectsSideAbove30 (negative, CON-011).

    A 31x30 request — one cell past the narrowed maximum on *one* side — is
    rejected with a size-range error and no grid is produced; the domain raises,
    per ADR-0010, without argv involved. The offending side is named, so the
    user is not left to work out which of the two numbers they typed is the
    problem. 60 is checked alongside 31 so the far side of the range is covered
    too, and the height variant is checked so the rule is not "the larger side".
    """
    for width in (31, 60):
        with pytest.raises(errors.SizeOutOfRange) as excinfo:
            random_grid.generate(width, 30, 30, _rng())

        assert str(width) in str(excinfo.value)
        assert "width" in str(excinfo.value)

    with pytest.raises(errors.SizeOutOfRange) as excinfo:
        random_grid.generate(30, 31, 30, _rng())

    assert "height" in str(excinfo.value)


def test_generate_random_rejects_side_below_10() -> None:
    """AC-070 / TestGenerateRandom_RejectsSideBelow10 (negative).

    A 30x9 request — legal width, one cell short on the height — is rejected
    with a size-range error naming the height, and no grid is produced.
    """
    assert random_grid.MIN_SIZE == 10

    with pytest.raises(errors.SizeOutOfRange) as excinfo:
        random_grid.generate(30, 9, 30, _rng())

    assert "9" in str(excinfo.value)
    assert "height" in str(excinfo.value)


def test_validate_extent_rejects_side_above_thirty() -> None:
    """TestValidateExtent_RejectsSideAboveThirty — ADR-0022/R2's own check.

    The rule as a pure function, called directly rather than through a source
    mode: this is the single definition all three modes delegate to, and
    ADR-0010's whole point is that it is reachable without argv. Both sides are
    exercised independently, and the accepted case is asserted too — a validator
    that refused everything would satisfy the negative half alone.
    """
    with pytest.raises(errors.SizeOutOfRange) as excinfo:
        random_grid.validate_extent(31, 30)
    assert "width" in str(excinfo.value)

    with pytest.raises(errors.SizeOutOfRange) as excinfo:
        random_grid.validate_extent(30, 31)
    assert "height" in str(excinfo.value)

    assert random_grid.validate_extent(30, 12) == (30, 12)


def test_validate_extent_reports_the_width_when_both_sides_are_wrong() -> None:
    """The declared order (failure matrix row 4), pinned so it cannot drift.

    Two equally-true messages are available when both sides are out of range;
    which one the user gets should be a decision, not a consequence of argument
    evaluation order.
    """
    with pytest.raises(errors.SizeOutOfRange) as excinfo:
        random_grid.validate_extent(99, 99)

    assert "width" in str(excinfo.value)
    assert "height" not in str(excinfo.value)


def test_generate_random_respects_density_parameter() -> None:
    """AC-010 / TestGenerateRandom_RespectsDensityParameter (happy).

    A requested density of 30% yields a filled fraction within ±3 percentage
    points (ADR-0003). Asserted at the *smallest* supported grid first, where
    the band is only ±3 cells and a per-cell Bernoulli sampler would fail
    roughly a third of the time, then across the range and several seeds so the
    guarantee is shown to be structural rather than one lucky draw. The extents
    include rectangles, since the target count is now a product of two numbers
    and a sampler that squared one of them would keep the band only by accident.
    """
    tolerance = random_grid.DENSITY_TOLERANCE_POINTS

    for seed in range(30):
        grid = random_grid.generate(
            random_grid.MIN_SIZE, random_grid.MIN_SIZE, 30, _rng(seed)
        )
        assert abs(random_grid.density_of(grid) - 30) <= tolerance

    for width, height in ((10, 10), (11, 29), (17, 17), (20, 13), (30, 10), (30, 30)):
        for seed in range(5):
            grid = random_grid.generate(width, height, 30, _rng(seed))
            assert abs(random_grid.density_of(grid) - 30) <= tolerance, (
                width,
                height,
                seed,
            )


def test_generate_random_rejects_invalid_density() -> None:
    """AC-011 / TestGenerateRandom_RejectsInvalidDensity (negative).

    A requested density of 150% — outside the valid 0-100% range — is rejected
    with an error and no grid is produced.
    """
    with pytest.raises(errors.InvalidDensity) as excinfo:
        random_grid.generate(20, 20, 150, _rng())

    assert "150" in str(excinfo.value)


# --------------------------------------------------------------------------
# Validation, beyond the two values the ACs name
# --------------------------------------------------------------------------


@pytest.mark.parametrize("side", [10, 11, 25, 29, 30])
def test_every_side_in_the_supported_range_is_accepted(side: int) -> None:
    """Each supported length works as a width and, independently, as a height.

    Paired against 17 — an in-range constant that is neither bound — so the
    parameter under test is the only thing moving on each axis.
    """
    assert _shape(random_grid.generate(side, 17, 40, _rng())) == (17, {side})
    assert _shape(random_grid.generate(17, side, 40, _rng())) == (side, {17})


@pytest.mark.parametrize("side", [-1, 0, 1, 9, 31, 51, 60, 1000, None])
def test_sides_outside_the_supported_range_are_rejected(side: int | None) -> None:
    """Both ends of the range, and an unspecified side, are domain errors.

    Checked on each axis with the other held at a legal value, so the rule is
    shown to be per side rather than "one of the two must be legal".

    ``None`` reaches here whenever ``--size`` is omitted: resolving a default
    belongs to the orchestrator (CARD-005), so an unresolved extent must surface
    as the same domain error as an out-of-range one — never as a ``TypeError``
    from a comparison.
    """
    with pytest.raises(errors.SizeOutOfRange):
        random_grid.generate(side, 20, 30, _rng())
    with pytest.raises(errors.SizeOutOfRange):
        random_grid.generate(20, side, 30, _rng())


@pytest.mark.parametrize("density", [-1, -100, 101, 150, 1000, None])
def test_densities_outside_the_valid_percentage_range_are_rejected(
    density: int | None,
) -> None:
    with pytest.raises(errors.InvalidDensity):
        random_grid.generate(20, 20, density, _rng())


@pytest.mark.parametrize("density", [0, 1, 30, 50, 99, 100])
def test_the_percentage_range_is_inclusive_at_both_ends(density: int) -> None:
    """0% and 100% are valid input, not nonsense.

    They produce degenerate grids — empty and full — which later stages judge
    on their own terms (uniqueness, difficulty); this module only rules on
    whether the *request* is a valid percentage.
    """
    grid = random_grid.generate(20, 20, density, _rng())

    assert abs(random_grid.density_of(grid) - density) <= (
        random_grid.DENSITY_TOLERANCE_POINTS
    )


def test_a_rejected_request_draws_no_randomness() -> None:
    """Validation runs before sampling, so a failed call cannot shift a seed.

    Otherwise a retry loop that swallowed an invalid request would silently
    change the grid a subsequent valid request produces from the same RNG.
    """
    rng = _rng()
    for bad in ((60, 20, 30), (9, 20, 30), (20, 60, 30), (20, 20, 150), (20, 20, -1)):
        with pytest.raises(errors.NonogramError):
            random_grid.generate(*bad, rng)

    assert rng.getstate() == _rng().getstate()


# --------------------------------------------------------------------------
# Density accuracy (ADR-0003)
# --------------------------------------------------------------------------


@pytest.mark.parametrize("density", [0, 5, 25, 30, 50, 75, 95, 100])
@pytest.mark.parametrize("extent", [(10, 10), (20, 20), (30, 30), (30, 10), (10, 30)])
def test_density_holds_across_the_extent_and_density_space(
    extent: tuple[int, int], density: int
) -> None:
    """The ±3-point band holds at every corner, not only at the AC's 30%.

    The corners are of the *extent* space now, both squares and the two extreme
    rectangles the range allows, because the filled target is a product of two
    independent numbers.
    """
    width, height = extent
    for seed in range(10):
        grid = random_grid.generate(width, height, density, _rng(seed))
        assert abs(random_grid.density_of(grid) - density) <= (
            random_grid.DENSITY_TOLERANCE_POINTS
        ), (extent, density, seed)


def test_the_filled_count_is_exact_not_merely_within_tolerance() -> None:
    """The sampler fixes the filled total before drawing.

    This is the mechanism behind AC-010 at 10x10: the count equals the rounded
    target exactly, so the only density error left is that rounding (at most
    half a cell), rather than a per-cell draw's variance. The rectangles are
    what pin ``filled_target`` to ``width * height`` rather than to one side
    squared — a square-only corpus cannot tell the two apart.
    """
    for width, height in ((10, 10), (20, 20), (30, 30), (30, 12), (12, 30)):
        for density in (0, 3, 30, 67, 100):
            grid = random_grid.generate(width, height, density, _rng())
            filled = sum(cell for row in grid for cell in row)
            assert filled == random_grid.filled_target(width, height, density)
            assert abs(filled - width * height * density / 100) <= 0.5


def test_the_grid_is_actually_shuffled_not_filled_in_order() -> None:
    """An exact count is only half the contract; the positions must be random.

    Guards the obvious wrong implementation — the correct count of filled cells
    packed into the first rows — which would satisfy every density assertion
    above while producing an unusable puzzle.
    """
    grid = random_grid.generate(20, 20, 50, _rng())
    per_row_filled = {sum(row) for row in grid}

    assert len(per_row_filled) > 1, "every row has the same filled count"
    assert grid[0] != grid[1], "the first two rows are identical"


# --------------------------------------------------------------------------
# Reproducibility — the seam this card owns (ADR-0015, guardrail G-4)
# --------------------------------------------------------------------------


def test_the_same_seed_and_parameters_reproduce_the_same_grid() -> None:
    """ADR-0015: what makes CARD-004's property test and CARD-005's loop
    deterministic. Two independently seeded RNGs must agree cell for cell."""
    first = random_grid.generate(25, 18, 35, _rng(4242))
    second = random_grid.generate(25, 18, 35, _rng(4242))

    assert first == second


def test_different_seeds_produce_different_grids() -> None:
    """Reproducibility must not have been bought by dropping the randomness."""
    grids = {
        tuple(tuple(row) for row in random_grid.generate(20, 20, 30, _rng(seed)))
        for seed in range(10)
    }

    assert len(grids) == 10


def test_successive_draws_from_one_rng_differ() -> None:
    """One run's RNG is threaded through many draws (the regenerate loop).

    Consecutive calls must therefore advance the shared state rather than
    re-deriving the same grid from the seed.
    """
    rng = _rng()
    first = random_grid.generate(20, 20, 30, rng)
    second = random_grid.generate(20, 20, 30, rng)

    assert first != second


def test_the_rng_is_a_required_argument() -> None:
    """No default RNG: a defaulted one would reintroduce unseeded randomness
    at the exact call site ADR-0015 exists to make reproducible."""
    with pytest.raises(TypeError):
        random_grid.generate(20, 20, 30)  # type: ignore[call-arg]


# --------------------------------------------------------------------------
# Guardrail G-4, enforced against the source itself
# --------------------------------------------------------------------------

_SOURCING_DIR = Path(random_grid.__file__).parent


def _random_module_calls(path: Path) -> list[str]:
    """Calls that resolve back to the ``random`` module or one of its members.

    A name-resolution pass rather than a syntactic pattern match: it first
    collects the bindings that name the ``random`` module itself
    (``import random``, ``import random as X``, and a single-level
    ``alias = random`` assignment) or one of its members (``from random
    import Y [as Z]``), then walks every ``ast.Call`` and flags one whose
    callable resolves back to one of those bindings. Reporting is normalised
    to ``"random.<name>"`` regardless of which spelling reached it, so
    ``random.shuffle(...)``, ``rnd.shuffle(...)`` (``import random as rnd``),
    ``shuffle(...)`` (``from random import shuffle``) and ``r.shuffle(...)``
    (``r = random``) all show up the same way.

    An annotation such as ``rng: random.Random`` is an attribute reference,
    not a ``Call`` node, so it is correctly ignored — and that alone is what
    makes a legitimate ``from random import Random`` (imported to *type* an
    injected generator) safe, so ``Random``/``SystemRandom`` need no
    from-import exemption and no longer get one. Closing that exemption was
    CARD-003 review cycle 2's first Minor follow-up, taken by CARD-008: it
    used to un-flag ``Random().shuffle(x)`` as well, a real ADR-0015 violation
    reached through a different import spelling than ``random.Random()``.

    ``from random import *`` is the second follow-up. A star import binds every
    draw function under its own name and the scan cannot tell which of them the
    module then calls, so it is reported as the single offence
    ``"random.*"`` — the import itself, not a call site.

    Known, deliberate gap: ``getattr(random, "shuffle")(x)`` is not detected.
    Resolving a dynamically computed attribute name is beyond what a static
    AST scan can do without executing the code — this is a documented blind
    spot, not a coverage claim.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))

    # Names bound to the `random` module itself.
    module_aliases: set[str] = set()
    # Names bound directly to a member of `random` (its original name kept
    # for reporting).
    member_aliases: dict[str, str] = {}
    # Offences that are the *import* rather than a call — see the docstring.
    import_offences: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "random":
                    module_aliases.add(alias.asname or alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module == "random":
            for alias in node.names:
                if alias.name == "*":
                    import_offences.append("random.*")
                    continue
                member_aliases[alias.asname or alias.name] = alias.name

    # A single-level `alias = random` assignment. Resolved in its own pass
    # (after the loop above) so source order does not matter.
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and isinstance(node.value, ast.Name)
            and node.value.id in module_aliases
        ):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    module_aliases.add(target.id)

    calls: list[str] = list(import_offences)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and isinstance(func.value, ast.Name)
            and func.value.id in module_aliases
        ):
            calls.append(f"random.{func.attr}")
        elif isinstance(func, ast.Name) and func.id in member_aliases:
            calls.append(f"random.{member_aliases[func.id]}")

    return calls


def test_the_source_walk_actually_sees_the_package() -> None:
    """Guard the guard below: an empty walk must not pass silently."""
    found = {path.name for path in _SOURCING_DIR.rglob("*.py")}

    assert {"__init__.py", "random_grid.py", "library.py"} <= found


def test_no_module_level_random_usage_anywhere_in_sourcing() -> None:
    """G-4 / ADR-0015, checked structurally rather than by convention.

    Every draw must go through the injected instance. Written against the whole
    package so a module a later sourcing card adds is covered the moment it
    lands.
    """
    offenders = {
        str(path.relative_to(_SOURCING_DIR)): calls
        for path in sorted(_SOURCING_DIR.rglob("*.py"))
        if (calls := _random_module_calls(path))
    }

    assert not offenders, f"module-level random usage: {offenders}"


def test_the_guardrail_check_would_catch_a_violation(tmp_path: Path) -> None:
    """The G-4 check is only worth its line count if it can fail.

    Runs the *real* detector — not a re-implementation of its AST-scan logic
    — against a temp file containing a genuine violation. (Proven necessary:
    the previous version of this test re-implemented the scan inline and
    never called ``_random_module_calls`` at all — replacing that function's
    body with ``return []`` still passed every test.)
    """
    offender = tmp_path / "offender.py"
    offender.write_text("import random\n\n\ndef f():\n    return random.shuffle([1])\n")

    assert _random_module_calls(offender) == ["random.shuffle"]


def test_the_guardrail_check_catches_the_import_from_branch(tmp_path: Path) -> None:
    """``from random import shuffle`` was never exercised by any test."""
    offender = tmp_path / "offender.py"
    offender.write_text(
        "from random import shuffle\n\n\ndef f():\n    return shuffle([1])\n"
    )

    assert _random_module_calls(offender) == ["random.shuffle"]


def test_the_guardrail_check_catches_an_aliased_module_import(
    tmp_path: Path,
) -> None:
    """``import random as rnd`` must not evade the scan."""
    offender = tmp_path / "offender.py"
    offender.write_text(
        "import random as rnd\n\n\ndef f():\n    return rnd.shuffle([1])\n"
    )

    assert _random_module_calls(offender) == ["random.shuffle"]


def test_the_guardrail_check_catches_an_aliased_from_import(
    tmp_path: Path,
) -> None:
    """``from random import shuffle as sh`` must not evade the scan."""
    offender = tmp_path / "offender.py"
    offender.write_text(
        "from random import shuffle as sh\n\n\ndef f():\n    return sh([1])\n"
    )

    assert _random_module_calls(offender) == ["random.shuffle"]


def test_the_guardrail_check_catches_aliasing_via_plain_assignment(
    tmp_path: Path,
) -> None:
    """``r = random; r.shuffle(x)`` — aliasing via assignment, not import."""
    offender = tmp_path / "offender.py"
    offender.write_text(
        "import random\n\nr = random\n\n\ndef f():\n    return r.shuffle([1])\n"
    )

    assert _random_module_calls(offender) == ["random.shuffle"]


def test_the_guardrail_check_does_not_flag_the_legitimate_random_class_import(
    tmp_path: Path,
) -> None:
    """``from random import Random`` for a type annotation is not G-4 (Minor).

    ``Random``/``SystemRandom`` are class imports, not draw functions; a
    module using one only as a type annotation (or to accept an injected
    instance) must not be flagged. Note what does the work now: the annotation
    is an ``ast.Name``, not an ``ast.Call``, so nothing has to exempt the
    *import* for this to pass — see the next test for why that matters.
    """
    offender = tmp_path / "offender.py"
    offender.write_text(
        "from random import Random\n\n\ndef f(rng: Random) -> None:\n"
        "    rng.shuffle([1])\n"
    )

    assert _random_module_calls(offender) == []


def test_the_guardrail_check_catches_minting_a_generator_via_a_from_import(
    tmp_path: Path,
) -> None:
    """``from random import Random`` then ``Random().shuffle(x)`` is a
    violation (CARD-003 review cycle 2, Minor 1; closed by CARD-008).

    ``random.Random()`` was already flagged through the module path, so
    exempting the from-import binding left the identical offence reachable by
    changing the import spelling — an unseeded generator minted inside the
    module, which is exactly what ADR-0015 forbids.
    """
    offender = tmp_path / "offender.py"
    offender.write_text(
        "from random import Random\n\n\ndef f():\n    return Random().shuffle([1])\n"
    )

    assert _random_module_calls(offender) == ["random.Random"]


def test_the_guardrail_check_catches_a_star_import(tmp_path: Path) -> None:
    """``from random import *`` is a violation on sight (Minor 2, same review).

    The star binds every draw function under its own name, so the scan cannot
    say which one is called — and must not therefore say "none". The import
    itself is reported.
    """
    offender = tmp_path / "offender.py"
    offender.write_text("from random import *\n\n\ndef f():\n    return shuffle([1])\n")

    assert _random_module_calls(offender) == ["random.*"]


def test_the_guardrail_check_documents_the_getattr_indirection_gap(
    tmp_path: Path,
) -> None:
    """Known, deliberate gap: ``getattr(random, "shuffle")(x)`` is not caught.

    A static AST scan cannot resolve a runtime-computed attribute name
    without executing the code; this test pins that limitation down rather
    than letting it silently regress into a false claim of full coverage.
    """
    offender = tmp_path / "offender.py"
    offender.write_text(
        "import random\n\n\ndef f():\n    return getattr(random, 'shuffle')([1])\n"
    )

    assert _random_module_calls(offender) == []


# --------------------------------------------------------------------------
# The mode-dispatch surface (CARD-008 / CARD-015 extend this)
# --------------------------------------------------------------------------


def test_for_mode_returns_the_random_source() -> None:
    assert sourcing.for_mode(sourcing.RANDOM) is random_grid.generate


def test_for_mode_dispatches_to_a_usable_grid_source() -> None:
    """The dispatch seam end to end: look the mode up, then source a grid."""
    source = sourcing.for_mode("random")
    grid = source(20, 20, 30, _rng())

    assert _shape(grid) == (20, {20})
    assert grid == random_grid.generate(20, 20, 30, _rng())


def test_for_mode_rejects_an_unregistered_mode() -> None:
    """Not a domain error on purpose: argparse's ``choices`` rejects a mode the
    user typed (ADR-0010), so an unknown mode here is a pipeline wiring bug.

    The table is complete as of CARD-015 — random, library and image are the
    three modes the model names — so the unregistered mode asked for here is a
    made-up one rather than the next card's.
    """
    with pytest.raises(ValueError) as excinfo:
        sourcing.for_mode("webcam")

    message = str(excinfo.value)
    assert "webcam" in message
    assert "random" in message


def test_the_advertised_modes_match_the_dispatch_table() -> None:
    """``MODES`` is what a caller enumerates; it must not drift from the table
    ``for_mode`` looks in — CARD-008 added ``library`` to both rows, CARD-015
    ``image``."""
    assert sourcing.MODES == ("random", "library", "image")
    for mode in sourcing.MODES:
        assert callable(sourcing.for_mode(mode))
