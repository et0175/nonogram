"""COMP-003 tests — the built-in image library source (card CARD-008, FR-002).

Acceptance-criterion traceability (trace.yml FR-002). The architecture names
each check in PascalCase; pytest collects snake_case, so the mapping is spelled
out here and repeated in each test's docstring:

===========  ==========================================  =====================================
AC           architecture test name                      test below
===========  ==========================================  =====================================
AC-005       TestGenerateLibrary_ProducesCatGrid          test_generate_library_produces_cat_grid
AC-006       TestGenerateLibrary_RejectsUnknownKey        test_generate_library_rejects_unknown_key
===========  ==========================================  =====================================

Everything after the AC block guards the seams the two criteria do not
describe: the fixed-in-package registry (guardrail G-5), the shape-not-bitmap
rescale, POL-001's boundary tie-break and the ADR-0015 reproducibility it has
to preserve, and the dispatch/orchestrator/CLI wiring this card adds.

Every test constructs its own ``random.Random``, so nothing here depends on
global random state and no test can perturb another's draws.
"""

from __future__ import annotations

import argparse
import ast
import random
from pathlib import Path

import pytest

from nonogram import cli, errors, orchestrator, sourcing
from nonogram.sourcing import library, random_grid
from nonogram.sourcing.templates import cat, heart, house, moon

SEED = 20260828

#: Every length CON-011 allows a grid *side* to have. Named ``SIZES`` because
#: the square case is what most of this file exercises; the rectangular
#: behaviour has its own tests, which name their two extents explicitly.
SUPPORTED_SIZES = range(random_grid.MIN_SIZE, random_grid.MAX_SIZE + 1)

#: Side lengths at which the template's own resolution divides that axis
#: exactly, so every target cell on it is built from whole template cells.
#: Both axes have to be one of these for the tie-break to have nothing left to
#: act on (see the module docstring in ``library.py``), which inside 10..30
#: makes 16x16 the one degenerate extent. Derived rather than hard-coded so the
#: list follows :data:`library.TEMPLATE_EDGE` if the templates are ever redrawn.
DEGENERATE_SIZES = tuple(
    size
    for size in SUPPORTED_SIZES
    if size % library.TEMPLATE_EDGE == 0 or library.TEMPLATE_EDGE % size == 0
)

#: A side length where the rescale genuinely has boundary cells — the
#: interesting case for everything about the tie-break.
JITTERED_SIZE = 20


def _rng(seed: int = SEED) -> random.Random:
    return random.Random(seed)


def _shape(grid: list[list[bool]]) -> tuple[int, set[int]]:
    """``(row count, the set of row lengths)`` — the grid's height and width.

    A *set* of row lengths rather than one number, so a ragged grid can never be
    mistaken for a rectangle of the right width.
    """
    return len(grid), {len(row) for row in grid}


def _certain_cells(key: str, size: int) -> dict[tuple[int, int], bool]:
    """The cells the shape wholly covers or does not touch, and their value.

    These are the ones no threshold can move (:data:`library.MIN_EDGE_THRESHOLD`
    and :data:`library.MAX_EDGE_THRESHOLD` are strictly inside ``(0, 1)``), so
    they are what "matches the template at the target extent" means for a source
    whose boundary is deliberately jittered. Square-only by design — its callers
    are the AC tests, which are about the shape rather than about the extent.
    """
    numerators, denominator = library.coverage(library.template_for(key), size, size)
    return {
        (row, column): numerator == denominator
        for row, values in enumerate(numerators)
        for column, numerator in enumerate(values)
        if numerator in (0, denominator)
    }


# --------------------------------------------------------------------------
# Acceptance criteria
# --------------------------------------------------------------------------


def test_generate_library_produces_cat_grid() -> None:
    """AC-005 / TestGenerateLibrary_ProducesCatGrid (happy).

    Given the built-in library key ``"cat"``, a grid matching the cat template
    at the target size is produced.

    "Matching the template" is asserted three ways, because a single equality
    against one hard-coded 20x20 array would pin the tie-break draw rather than
    the shape: the grid is the requested size in the ADR-0012 representation,
    every cell the cat wholly covers or does not touch has the template's value,
    and it is recognisably *this* template rather than any other in the library.
    """
    grid = library.generate("cat", JITTERED_SIZE, JITTERED_SIZE, _rng())

    assert _shape(grid) == (JITTERED_SIZE, {JITTERED_SIZE})
    assert all(cell is True or cell is False for row in grid for cell in row)

    certain = _certain_cells("cat", JITTERED_SIZE)
    assert certain, "the cat covers no cell wholly — the fixture is meaningless"
    assert {(row, column): grid[row][column] for row, column in certain} == certain

    # ...and it is the cat, not merely "a shape at the right size".
    others = {
        key: library.generate(key, JITTERED_SIZE, JITTERED_SIZE, _rng())
        for key in library.KEYS
        if key != "cat"
    }
    assert all(grid != other for other in others.values())


def test_generate_library_rejects_unknown_key() -> None:
    """AC-006 / TestGenerateLibrary_RejectsUnknownKey (negative).

    An unknown key ``"dragon"`` is rejected with an unknown-library-image error
    and no grid is produced. The domain raises (ADR-0010) — no argv involved —
    and the message lists what the user could have asked for instead.
    """
    with pytest.raises(errors.UnknownLibraryImage) as excinfo:
        library.generate("dragon", JITTERED_SIZE, JITTERED_SIZE, _rng())

    message = str(excinfo.value)
    assert "dragon" in message
    for key in library.KEYS:
        assert key in message


# --------------------------------------------------------------------------
# The registry: fixed in-package, not discovered (guardrail G-5, ADR-0007)
# --------------------------------------------------------------------------

_LIBRARY_SOURCE = Path(library.__file__)
_TEMPLATE_MODULES = (cat, heart, house, moon)


def test_the_library_advertises_at_least_the_four_named_templates() -> None:
    assert {"cat", "house", "heart", "moon"} <= set(library.KEYS)


def test_every_advertised_key_resolves_to_a_usable_template() -> None:
    """``KEYS`` is what the error message and ``--help`` promise; it must not
    drift from the dict ``template_for`` actually looks in."""
    for key in library.KEYS:
        assert library.template_for(key) is not None


def test_the_registry_is_a_literal_table_not_a_directory_scan() -> None:
    """G-5 / ADR-0007: the plugin-registry alternative was rejected outright.

    Checked against the module's AST rather than its text, so the docstring
    naming ``pkgutil.iter_modules`` as the thing this is *not* cannot make the
    test pass or fail. Any of these appearing as real code would mean the set
    of library images had stopped being knowable by reading the source.
    """
    forbidden = {
        "pkgutil",
        "iter_modules",
        "walk_packages",
        "importlib",
        "import_module",
        "__import__",
        "entry_points",
        "glob",
        "iglob",
        "rglob",
        "iterdir",
        "getattr",
    }
    tree = ast.parse(_LIBRARY_SOURCE.read_text(encoding="utf-8"))
    used = {
        node.id if isinstance(node, ast.Name) else node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Name | ast.Attribute)
    }

    assert not (used & forbidden), f"dynamic template discovery: {sorted(used & forbidden)}"


@pytest.mark.parametrize("module", _TEMPLATE_MODULES, ids=lambda m: m.__name__)
def test_a_template_module_carries_data_and_nothing_else(module: object) -> None:
    """The ``templates`` package's own rule, enforced instead of asserted.

    The shapes live in ``.py`` files only because ``pyproject.toml`` (guardrail
    G-3) cannot be taught to ship ``.txt`` package data. That is a packaging
    workaround, so the files must stay as inert as the ``.txt`` they stand in
    for: no functions, no classes, no calls, no imports beyond ``__future__``.
    """
    source = Path(module.__file__).read_text(encoding="utf-8")  # type: ignore[attr-defined]
    tree = ast.parse(source)

    for node in ast.walk(tree):
        assert not isinstance(
            node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef | ast.Call
        ), f"{module.__name__} contains executable code: {ast.dump(node)[:80]}"
        if isinstance(node, ast.ImportFrom):
            assert node.module == "__future__"
        assert not isinstance(node, ast.Import)


@pytest.mark.parametrize("key", library.KEYS)
def test_every_template_is_a_square_non_degenerate_picture(key: str) -> None:
    """A template with no filled cells (or no empty ones) is not a shape, and a
    non-square one would be distorted by the square rescale."""
    template = library.template_for(key)

    assert len(template) == library.TEMPLATE_EDGE
    assert {len(row) for row in template} == {library.TEMPLATE_EDGE}

    filled = sum(cell for row in template for cell in row)
    assert 0 < filled < library.TEMPLATE_EDGE**2


# --------------------------------------------------------------------------
# Parsing the art
# --------------------------------------------------------------------------


def test_parse_art_reads_filled_and_empty_cells() -> None:
    assert library.parse_art("#.\n.#\n") == ((True, False), (False, True))


def test_parse_art_tolerates_a_missing_trailing_newline() -> None:
    assert library.parse_art("#.\n.#") == library.parse_art("#.\n.#\n")


@pytest.mark.parametrize(
    ("art", "reason"),
    [
        pytest.param("", "empty", id="empty"),
        pytest.param("\n", "empty", id="blank-first-line"),
        pytest.param("##\n#\n", "rectangular", id="ragged"),
        pytest.param("#x\n##\n", "only use", id="stray-character"),
        pytest.param("# \n##\n", "only use", id="space-is-not-empty"),
    ],
)
def test_malformed_art_is_a_packaging_bug_not_a_domain_error(
    art: str, reason: str
) -> None:
    """A ``ValueError``, deliberately: the art is in-package data this build
    ships, so malformed art is nothing a user did and must not be mapped onto
    an input-rejection exit code."""
    with pytest.raises(ValueError, match=reason) as excinfo:
        library.parse_art(art)

    assert not isinstance(excinfo.value, errors.NonogramError)


# --------------------------------------------------------------------------
# A template is a shape, not a fixed-size bitmap
# --------------------------------------------------------------------------


@pytest.mark.parametrize("size", [10, 11, 16, 17, 20, 23, 29, 30])
@pytest.mark.parametrize("key", library.KEYS)
def test_a_template_scales_to_any_supported_size(key: str, size: int) -> None:
    """The card's headline requirement: ``--size 20`` with key ``cat`` yields a
    20x20 grid, and so does every other supported size and key."""
    grid = library.generate(key, size, size, _rng())

    assert _shape(grid) == (size, {size})
    assert 0 < sum(cell for row in grid for cell in row) < size * size


@pytest.mark.parametrize("extent", [(30, 12), (12, 30), (10, 30), (29, 11), (16, 20)])
@pytest.mark.parametrize("key", library.KEYS)
def test_a_template_scales_to_a_rectangular_grid(
    key: str, extent: tuple[int, int]
) -> None:
    """FR-018/ADR-0022/R1: the two target lengths are independent.

    ``_axis_overlaps`` was always per axis; this is the assertion that both of
    its call sites now get the target's *own* length rather than one number
    twice. The shape is checked as ``(rows, {row length})``, so a signature that
    transposed the pair would fail here rather than pass by symmetry, and the
    grid is required to still be a recognisable silhouette (neither all-empty
    nor all-filled) at every shape.
    """
    width, height = extent
    grid = library.generate(key, width, height, _rng())

    assert _shape(grid) == (height, {width})
    assert 0 < sum(cell for row in grid for cell in row) < width * height


def test_a_rectangle_and_its_transpose_are_different_grids() -> None:
    """The strongest available statement that the two arguments are not aliases.

    A ``30x12`` cat and a ``12x30`` cat are both legal requests. If the pair
    were collapsed anywhere — into a max, a min, or one value passed twice — one
    of these would come back the wrong shape or the two would agree.
    """
    wide = library.generate("cat", 30, 12, _rng())
    tall = library.generate("cat", 12, 30, _rng())

    assert _shape(wide) == (12, {30})
    assert _shape(tall) == (30, {12})
    assert [list(column) for column in zip(*wide)] != tall


def test_coverage_accounts_for_the_whole_template_area() -> None:
    """The rescale's arithmetic, checked by conservation rather than by
    re-deriving it: every target cell covers the same share of the template, so
    the numerators must sum to the template's filled cell count times the
    denominator divided by the number of target cells... which is easier to
    state as: the mean coverage equals the template's filled fraction, exactly.

    Rectangles are in the corpus because the identity is over ``width *
    height``: a square-only corpus cannot tell that product from one side
    squared.
    """
    template = library.template_for("heart")
    filled = sum(cell for row in template for cell in row)

    for width, height in ((10, 10), (13, 13), (20, 20), (29, 29), (30, 12), (12, 30)):
        numerators, denominator = library.coverage(template, width, height)
        total = sum(sum(row) for row in numerators)
        # Each of the width*height target cells carries `denominator` units of
        # template area between them, of which `filled` template cells' worth
        # is filled.
        assert total * (len(template) * len(template[0])) == (
            filled * denominator * width * height
        ), (width, height)


def test_an_exact_magnification_replicates_the_template_block_by_block() -> None:
    """At a whole-number magnification the rescale must be exact.

    32 is 16 doubled, so every template cell becomes a 2x2 block and nothing is
    interpolated — the strongest available statement that the grid really is
    the template's shape and not an approximation of it.

    Driven through :func:`library.render` rather than :func:`library.generate`
    because CON-011 caps a *requested* grid at 30 a side, so 32 is no longer a
    size the mode entry point will accept. The geometry core takes an
    already-validated size and is size-agnostic by contract, and 16 — the only
    exact magnification left inside 10..30 — is the identity, which would prove
    nothing about block replication. So the multiplication is exercised where
    it lives, and the request range is enforced by the tests that own it.
    """
    template = library.template_for("house")
    grid = library.render(template, 32, 32, library.CANONICAL_THRESHOLD)

    for row in range(32):
        for column in range(32):
            assert grid[row][column] is template[row // 2][column // 2]


def test_scaling_does_not_lose_a_whole_row_of_the_shape() -> None:
    """Guards the nearest-neighbour implementation this one rejected.

    At size 11 a nearest-neighbour rescale of a 16-cell template drops five of
    its rows outright; area coverage degrades them into partial cells instead.
    Every template row that has filled cells must still leave a mark.
    """
    template = library.template_for("moon")
    edge = library.TEMPLATE_EDGE

    # What nearest-neighbour would do: sample one source row per target row and
    # never look at the rest. Five of the sixteen are simply never read.
    sampled = {row * edge // 11 for row in range(11)}
    assert len(sampled) == 11 and len(set(range(edge)) - sampled) == 5

    # What area coverage does: every target row that overlaps filled template
    # area carries some of it, so no part of the shape is silently dropped.
    numerators, _ = library.coverage(template, 11, 11)
    assert sum(1 for row in template if any(row)) == 15
    assert sum(1 for row in numerators if any(row)) == 11


# --------------------------------------------------------------------------
# Validation (ADR-0010): domain rules, raised inward of the CLI
# --------------------------------------------------------------------------


@pytest.mark.parametrize("key", ["dragon", "Cat", "cat ", "", "CAT"])
def test_an_unknown_key_is_rejected_however_it_is_misspelled(key: str) -> None:
    """Key lookup is exact — no case folding, no trimming. A user who typed
    ``Cat`` gets the list of real keys rather than a silent near-miss."""
    with pytest.raises(errors.UnknownLibraryImage):
        library.generate(key, JITTERED_SIZE, JITTERED_SIZE, _rng())


def test_an_absent_key_is_rejected_rather_than_defaulted() -> None:
    """``--mode library`` with no ``--library-key`` reaches here as ``None``.

    Picking a default shape would generate a puzzle the user did not ask for;
    the error names the alternatives instead.
    """
    with pytest.raises(errors.UnknownLibraryImage) as excinfo:
        library.generate(None, JITTERED_SIZE, JITTERED_SIZE, _rng())

    message = str(excinfo.value)
    assert "--library-key" in message
    assert "None" not in message, "a forgotten flag must not read as a bad key"
    for key in library.KEYS:
        assert key in message


@pytest.mark.parametrize("side", [-1, 0, 1, 9, 31, 51, 60, 1000, None])
def test_the_shared_extent_rule_applies_to_library_mode_too(side: int | None) -> None:
    """The supported range is a rule about the puzzle, not about the source, so
    library mode reuses ``random_grid.validate_extent`` rather than restating it
    — including the ``None`` case, which must be a domain error and never a
    ``TypeError`` from a comparison.

    Each axis is checked with the other held legal, so the delegation is shown
    to cover both sides rather than only the one a square request would move."""
    with pytest.raises(errors.SizeOutOfRange):
        library.generate("cat", side, 20, _rng())
    with pytest.raises(errors.SizeOutOfRange):
        library.generate("cat", 20, side, _rng())


def test_the_key_is_judged_before_the_extent() -> None:
    """Both arguments are wrong; the key is what the mode is about, so that is
    the error the user is told about first. Pinned because it is otherwise an
    accident of statement order."""
    with pytest.raises(errors.UnknownLibraryImage):
        library.generate("dragon", 60, 60, _rng())


def test_a_rejected_request_draws_no_randomness() -> None:
    """Validation runs before the tie-break draw, so a failed call cannot shift
    a seed — the same contract ``random_grid.generate`` keeps, and the reason a
    retry loop that swallowed an invalid request could not silently change the
    grids a later valid one produces."""
    rng = _rng()
    for bad_key, bad_size in (("dragon", 20), ("cat", 60), ("cat", 9), (None, 20)):
        with pytest.raises(errors.NonogramError):
            library.generate(bad_key, bad_size, bad_size, rng)

    assert rng.getstate() == _rng().getstate()


def test_the_rng_is_a_required_argument() -> None:
    """No default RNG: a defaulted one would reintroduce unseeded randomness at
    the exact call site ADR-0015 exists to make reproducible."""
    with pytest.raises(TypeError):
        library.generate("cat", 20, 20)  # type: ignore[call-arg]


# --------------------------------------------------------------------------
# POL-001's tie-break, and the ADR-0015 determinism it must not cost
# --------------------------------------------------------------------------


def test_the_threshold_band_is_strictly_inside_zero_and_one() -> None:
    """The whole "the cat stays the cat" argument rests on this.

    A band touching 0 or 1 would let a draw fill a cell the shape does not
    touch, or empty one it wholly covers — the tie-break would be redrawing the
    shape rather than its outline.
    """
    assert 0 < library.MIN_EDGE_THRESHOLD < library.MAX_EDGE_THRESHOLD < 1
    assert (
        library.MIN_EDGE_THRESHOLD < library.CANONICAL_THRESHOLD
        < library.MAX_EDGE_THRESHOLD
    )


@pytest.mark.parametrize("key", library.KEYS)
def test_the_tie_break_moves_the_outline_and_never_the_shape(key: str) -> None:
    """Across the entire band, the cells the shape wholly covers or does not
    touch keep their value — so every attempt of a library run renders the same
    picture, differing only where the rasteriser genuinely had a choice."""
    template = library.template_for(key)
    certain = _certain_cells(key, JITTERED_SIZE)

    for threshold in (
        library.MIN_EDGE_THRESHOLD,
        library.CANONICAL_THRESHOLD,
        library.MAX_EDGE_THRESHOLD,
    ):
        grid = library.render(template, JITTERED_SIZE, JITTERED_SIZE, threshold)
        for (row, column), expected in certain.items():
            assert grid[row][column] is expected, (key, threshold, row, column)


def test_the_same_seed_and_parameters_reproduce_the_same_grid() -> None:
    """ADR-0015 holds for library mode on exactly the terms it holds for random
    mode: the threshold is the only stochastic input and it comes from the run's
    RNG, so seed plus key plus size fixes the grid."""
    first = library.generate("cat", 23, 23, _rng(4242))
    second = library.generate("cat", 23, 23, _rng(4242))

    assert first == second


def test_successive_draws_from_one_rng_render_a_different_outline() -> None:
    """POL-001's retry, at the level of the source.

    The orchestrator threads one RNG through every attempt, so the second call
    must produce a different candidate — otherwise a library retry would be
    twenty identical solver verdicts.
    """
    rng = _rng()
    first = library.generate("cat", JITTERED_SIZE, JITTERED_SIZE, rng)
    second = library.generate("cat", JITTERED_SIZE, JITTERED_SIZE, rng)

    assert first != second


def test_a_retry_stays_on_the_same_template() -> None:
    """The card is explicit: a retry re-renders the same template, it does not
    switch key. Nothing in the source can reach another template's data — shown
    by the certain cells still being this shape's after many draws."""
    rng = _rng()
    certain = _certain_cells("moon", JITTERED_SIZE)

    for _ in range(20):
        grid = library.generate("moon", JITTERED_SIZE, JITTERED_SIZE, rng)
        for (row, column), expected in certain.items():
            assert grid[row][column] is expected


@pytest.mark.parametrize("size", DEGENERATE_SIZES)
def test_at_an_exact_magnification_a_retry_is_honestly_a_no_op(size: int) -> None:
    """The documented limit of the tie-break, pinned rather than glossed over.

    When the grid is a whole-number magnification of the template no cell is on
    the boundary, so the threshold has nothing to act on and every attempt
    renders the same grid. A library run at 16 that is not uniquely
    solvable will therefore spend its retry budget confirming one verdict and
    abandon — a property of a deterministic source, not a defect in POL-001's
    loop, and the reason this is a test rather than a comment.
    """
    assert size == 16
    rng = _rng()
    grids = {
        tuple(tuple(row) for row in library.generate("cat", size, size, rng))
        for _ in range(5)
    }

    assert len(grids) == 1


def test_every_other_supported_size_does_vary_between_attempts() -> None:
    """The flip side: the no-op above is the exception, not the rule.

    20 of the 21 supported sizes — including 20, where the ratio only *looks*
    round — give the retry loop a genuinely different candidate. CON-011's
    10..30 range is named below as well as read from the constant, so this
    keeps saying something if the constant ever moves again.
    """
    varying = []
    for size in SUPPORTED_SIZES:
        rng = _rng()
        grids = {
            tuple(tuple(row) for row in library.generate("cat", size, size, rng))
            for _ in range(6)
        }
        if len(grids) > 1:
            varying.append(size)

    assert set(SUPPORTED_SIZES) == set(range(10, 31))
    assert DEGENERATE_SIZES == (16,)
    assert set(varying) == set(range(10, 31)) - {16}
    assert len(varying) == 20


def test_the_no_op_needs_both_axes_magnified_not_just_one() -> None:
    """The module docstring's per-axis restatement of the degenerate case.

    With the axes rescaled independently, "an exact magnification" became a
    condition on each of them: 16 cells on one axis alone leaves the *other*
    axis with boundary cells, so the threshold still has something to act on and
    consecutive attempts still differ. 16x16 is the only extent inside 10..30
    where both axes are magnified — which is what makes the claim above
    ("the only degenerate extent is 16x16") a statement about the pair rather
    than a leftover from the square era.
    """
    for width, height in ((16, 20), (20, 16), (16, 30), (10, 16)):
        rng = _rng()
        grids = {
            tuple(tuple(row) for row in library.generate("cat", width, height, rng))
            for _ in range(6)
        }
        assert len(grids) > 1, (width, height)

    rng = _rng()
    square = {
        tuple(tuple(row) for row in library.generate("cat", 16, 16, rng))
        for _ in range(6)
    }
    assert len(square) == 1


# --------------------------------------------------------------------------
# Wiring: the dispatch row, the orchestrator route, the CLI flags
# --------------------------------------------------------------------------


def test_for_mode_returns_the_library_source() -> None:
    assert sourcing.for_mode(sourcing.LIBRARY) is library.generate


def test_library_is_advertised_alongside_random() -> None:
    assert sourcing.LIBRARY == "library"
    assert sourcing.LIBRARY in sourcing.MODES


def test_for_mode_dispatches_to_a_usable_library_source() -> None:
    """The dispatch seam end to end: look the mode up, then source a grid with
    the mode's own argument list."""
    source = sourcing.for_mode("library")
    grid = source("heart", JITTERED_SIZE, JITTERED_SIZE, _rng())

    assert _shape(grid) == (JITTERED_SIZE, {JITTERED_SIZE})
    assert grid == library.generate("heart", JITTERED_SIZE, JITTERED_SIZE, _rng())


def test_the_orchestrator_assembles_the_library_argument_list() -> None:
    """The key and extent go to the source in the mode's order, and the RNG is
    appended by the call site for every mode alike.

    The extent is a *pair* in the argument list, sitting directly after the
    mode's own leading argument (ADR-0022/R1) — a rectangle here, so a call site
    that passed one number twice would fail rather than pass by symmetry.

    Since CARD-033 the pair is an *argument* (``_resolved_extent``'s answer) and
    not a read of the request, because a bare ``--size N`` leaves the request
    half-stated (FR-023). The request below carries a different pair from the
    one passed in, so this asserts the argument is what reaches the source."""
    request = orchestrator.GenerationRequest(
        mode="library", library_key="moon", width=99, height=99, density=99
    )

    assert orchestrator._source_arguments(request, (14, 22)) == ("moon", 14, 22)


def test_the_orchestrator_still_assembles_the_random_argument_list() -> None:
    """The library row must not have changed what random mode is called with."""
    request = orchestrator.GenerationRequest(
        mode="random", width=99, height=99, density=35, library_key="moon"
    )

    assert orchestrator._source_arguments(request, (14, 22)) == (14, 22, 35)


def test_a_library_run_goes_through_the_existing_pipeline() -> None:
    """POL-001 end to end, unmodified: source -> clues -> uniqueness -> ready.

    The point of the card is that library mode reuses increment 1 wholesale, so
    the assertion is about the *aggregate* the shared loop produced — a
    confirmed-unique puzzle with its own retry counter, holding the cat.
    """
    request = orchestrator.GenerationRequest(
        mode="library", library_key="cat", width=15, height=15, seed=3
    )
    puzzle = orchestrator.generate(request)

    assert puzzle.ready_for_export is True
    assert puzzle.solution_count == 1
    assert puzzle.mode == "library"
    assert puzzle.regenerate.bound == orchestrator.MAX_REGENERATE_ATTEMPTS
    assert 1 <= puzzle.regenerate.attempts <= orchestrator.MAX_REGENERATE_ATTEMPTS

    assert puzzle.grid is not None
    for (row, column), expected in _certain_cells("cat", 15).items():
        assert puzzle.grid[row][column] is expected


def test_an_unknown_key_fails_the_run_before_any_retry_is_spent() -> None:
    """An invalid request does not become valid by being asked again: the error
    travels straight out of the bounded loop (it is not a rejected candidate),
    so the counter stops at the first attempt rather than at twenty."""
    request = orchestrator.GenerationRequest(
        mode="library", library_key="dragon", width=15, height=15, seed=3
    )

    with pytest.raises(errors.UnknownLibraryImage):
        orchestrator.generate(request)


def test_the_same_seed_replays_a_whole_library_run() -> None:
    request = orchestrator.GenerationRequest(
        mode="library", library_key="house", width=17, height=17, seed=11
    )

    assert orchestrator.generate(request).grid == orchestrator.generate(request).grid


def _generate_parser_action(dest: str) -> argparse.Action:
    """The ``generate`` subparser's action for ``dest``.

    argparse exposes no public way to read back a configured subparser, so this
    walks the two private collections it does keep — a test-only introspection,
    deliberately in one place rather than inlined into the assertions.
    """
    subparsers = next(
        action
        for action in cli.build_parser()._actions
        if isinstance(action, argparse._SubParsersAction)
    )
    return next(
        action
        for action in subparsers.choices["generate"]._actions
        if action.dest == dest
    )


def test_the_parser_offers_exactly_the_registered_modes() -> None:
    """``--mode``'s choices are mirrored by hand in ``cli.py``; this is the
    drift guard, kept in the test tree so the adapter does not have to import a
    capability module to stay honest. A mode registered in ``sourcing`` but not
    offered here is unreachable; one offered but not registered is a
    ``ValueError`` from ``for_mode`` in front of the user."""
    assert tuple(_generate_parser_action("mode").choices or ()) == sourcing.MODES


@pytest.mark.parametrize("mode", sourcing.MODES)
def test_every_registered_mode_is_actually_accepted(mode: str) -> None:
    """The same guard from the outside, through argv."""
    assert cli.build_parser().parse_args(["generate", "--mode", mode]).mode == mode


def test_the_library_key_carries_no_argparse_choices() -> None:
    """The structural half of ADR-0010 for this flag: not "these values happen
    to be accepted" but "the parser was never given a list to check against"."""
    assert _generate_parser_action("library_key").choices is None


def test_the_cli_parses_the_library_flags_into_the_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """argv -> GenerationRequest, the adapter's whole job for this card."""
    seen: list[orchestrator.GenerationRequest] = []

    def fake_generate(request: orchestrator.GenerationRequest) -> orchestrator.Puzzle:
        seen.append(request)
        return orchestrator.Puzzle(request=request, seed=request.seed or 0)

    monkeypatch.setattr(orchestrator, "generate", fake_generate)
    monkeypatch.setattr(orchestrator, "export_puzzle", lambda puzzle: ())

    exit_code = cli.main(
        ["generate", "--mode", "library", "--library-key", "cat", "--size", "20"]
    )

    assert exit_code == cli.ExitCode.OK
    assert seen == [
        orchestrator.GenerationRequest(
            # ``height=None``: a bare ``--size 20`` states one number and the
            # adapter passes it on unsquared since CARD-033 (FR-023). It still
            # *renders* 20x20 — every template is 16x16 — but that is the
            # template's ratio saying so, which
            # ``TestDeriveShape_LibraryTemplateRatioAppliesSquareToday`` covers.
            mode="library", width=20, height=None, library_key="cat", seed=None
        )
    ]


def test_the_library_key_defaults_to_unset() -> None:
    assert cli.build_parser().parse_args(["generate"]).library_key is None


@pytest.mark.parametrize("key", ["dragon", "Cat", "", "anything at all"])
def test_the_parser_does_not_judge_the_library_key(key: str) -> None:
    """ADR-0010 / guardrail G-3: key membership is a domain rule (AC-006), so
    it must NOT be encoded as argparse ``choices`` — the parser is required to
    accept these and hand them inward unchanged."""
    args = cli.build_parser().parse_args(
        ["generate", "--mode", "library", "--library-key", key]
    )

    assert args.library_key == key


def test_an_unknown_key_reaches_the_user_as_an_invalid_input_exit_code(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AC-006 through the adapter: a domain error, not a usage error — exit
    code 3 with a message naming the keys, not argparse's exit code 2."""
    exit_code = cli.main(
        ["generate", "--mode", "library", "--library-key", "dragon", "--size", "20"]
    )

    assert exit_code == cli.ExitCode.INVALID_INPUT
    assert "dragon" in capsys.readouterr().err
