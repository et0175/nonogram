"""COMP-006 tests: the FR-009 difficulty score (ADR-0013's 0..100 scale).

AC / test-id mapping — the trace.yml names, kept traceable from these
pytest-idiomatic function names:

    AC-022  TestScoreDifficulty_CombinesSignals              -> test_combines_*
    AC-023  TestScoreDifficulty_ZeroBacktrackingScoresEasiest -> test_zero_backtracking_*

AC-023 is the anchor point of the whole scale, so it is checked three ways and
not one: on synthetic signals (the arithmetic), across a spread of sizes and
densities (the *by construction* claim — that nothing about the grid's shape
can move it), and end to end on a real solve of a real line-logic-only puzzle
(that the solver actually reports the inputs the arithmetic assumes).

Most tests here drive :func:`score_difficulty` with a synthetic
:class:`_Signals`, because the point of nearly every one of them is to vary
*one* signal and hold the other four still — which no real puzzle will do on
request. The two tests that do solve for real are what tie the synthetic
fixture back to ``nonogram.solver.SolveSignals``.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, replace

import pytest

from nonogram.clues import compute_clues
from nonogram.difficulty import (
    HARDEST_DENSITY,
    MAX_SUPPORTED_CELLS,
    MIN_SUPPORTED_CELLS,
    SCORE_MAX,
    SCORE_MIN,
    SECONDS_PER_CELL_BUDGET,
    SIGNAL_WEIGHTS,
    SignalWeights,
    clue_density,
    normalize_signals,
    score_difficulty,
)
from nonogram.solver import SolveSignals, solve

# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _Signals:
    """A stand-in for ``SolveSignals`` that a test can vary one field of.

    Structurally identical to the real thing on the four members
    ``SolverSignals`` names, which is the point: if the protocol and the
    solver's dataclass ever drift apart, this fixture keeps working while
    ``test_solver_signals_satisfy_the_protocol`` below fails loudly.
    """

    line_logic_cells: int
    total_cells: int
    branch_nodes: int
    elapsed_seconds: float


def _clues_at_density(total_cells: int, density: float) -> tuple[tuple[int, ...], ...]:
    """A one-line clue set whose runs sum to ``density`` of ``total_cells``.

    Only the *sum* of the runs matters to :func:`clue_density`, so a single
    synthetic line is enough to pose any density the scorer needs to see —
    and far clearer than transcribing a grid whose real clues happen to add up.
    """
    return ((round(total_cells * density),),)


#: The AC-022 candidate: 15x15, 80% of cells settled by line logic before the
#: first branch, a low branch count, 0.2s on the clock.
AC022_SIGNALS = _Signals(
    line_logic_cells=180,  # 80% of 225
    total_cells=225,
    branch_nodes=5,
    elapsed_seconds=0.2,
)
AC022_CLUES = _clues_at_density(225, 0.45)

#: A 5x5 plus sign — unique, and settled entirely by line logic (the same
#: puzzle ``tests/test_solver.py`` pins the zero-branch signals on).
PLUS = [
    [glyph == "#" for glyph in row]
    for row in ("..#..", "..#..", "#####", "..#..", "..#..")
]

#: A 6x6 that propagation cannot finish: the solver has to guess. Taken from
#: ``tests/test_solver.py``, where it is pinned as branching.
BRANCHING_ROWS = ((1, 1), (0,), (2, 1), (1,), (1, 1), (1, 1))
BRANCHING_COLUMNS = ((2,), (1, 1, 1), (1, 1), (1, 1), (1,), (0,))


# --------------------------------------------------------------------------
# AC-022 — one number, reflecting the weighted combination of all five signals
# --------------------------------------------------------------------------


def test_combines_signals_into_one_number_on_the_scale() -> None:
    """AC-022: score a 15x15 candidate and get a single number in 0..100."""
    score = score_difficulty(AC022_SIGNALS, AC022_CLUES)

    assert isinstance(score, float)
    assert SCORE_MIN <= score <= SCORE_MAX


def test_combines_all_five_signals_and_not_a_subset() -> None:
    """AC-022: *every* named signal has to be able to move the score.

    The literal content of the criterion — "reflecting the weighted
    combination of all signals" — and the reason ADR-0013 rejected the
    backtracking-dominant alternative, which dropped two of the five. Perturb
    each signal on its own from the AC-022 candidate and the score has to
    respond; a signal that is silently ignored shows up here as an unchanged
    number.
    """
    baseline = score_difficulty(AC022_SIGNALS, AC022_CLUES)

    # 1. line-logic coverage, 2. backtracking amount, 3. solver wall-clock time
    perturbed = {
        "line-logic coverage": (
            replace(AC022_SIGNALS, line_logic_cells=90),
            AC022_CLUES,
        ),
        "backtracking amount": (
            replace(AC022_SIGNALS, branch_nodes=120),
            AC022_CLUES,
        ),
        "solver wall-clock time": (
            replace(AC022_SIGNALS, elapsed_seconds=2.5),
            AC022_CLUES,
        ),
        # 4. puzzle size — same *proportions*, a bigger grid: 30x30 with the
        #    same 80% coverage and the same branch-nodes-per-cell ratio, so
        #    only the size normalizer differs.
        "puzzle size": (
            _Signals(
                line_logic_cells=720,
                total_cells=900,
                branch_nodes=20,
                elapsed_seconds=0.8,
            ),
            _clues_at_density(900, 0.45),
        ),
        # 5. clue density — same solve, a sparser picture.
        "clue density": (AC022_SIGNALS, _clues_at_density(225, 0.05)),
    }

    for signal, (signals, clues) in perturbed.items():
        assert score_difficulty(signals, clues) != pytest.approx(baseline), (
            f"changing {signal} left the score at {baseline}: the formula is "
            f"not reflecting all five FR-009 signals"
        )


def test_combines_signals_by_the_documented_weighted_formula() -> None:
    """AC-022: the number is the ADR-0013 combination, not an opaque blend.

    Recomputing the formula by hand from the normalized signals and the weight
    table is what makes "weighted combination" checkable rather than a claim
    the docstring makes about itself. It also pins the shape ADR-0013 requires
    — effort as a fixed-weight sum, size and density strictly as multiplicative
    normalizers — so a future retune moves the numbers while a rewrite of the
    *shape* fails here.
    """
    normalized = normalize_signals(AC022_SIGNALS, AC022_CLUES)
    weights = SIGNAL_WEIGHTS

    effort = (
        weights.line_logic * normalized.line_logic_gap
        + weights.backtracking * normalized.branch_pressure
        + weights.solve_time * normalized.time_pressure
    )
    relief = (
        1.0
        - weights.size * (1.0 - normalized.size_pressure)
        - weights.density * (1.0 - normalized.density_pressure)
    )

    assert score_difficulty(AC022_SIGNALS, AC022_CLUES) == pytest.approx(
        SCORE_MAX * effort * relief
    )


def test_normalizes_every_signal_onto_the_unit_range() -> None:
    """ADR-0013's first step: five heterogeneous signals, all mapped to 0..1.

    Checked on the AC-022 candidate for the values themselves, and on absurd
    inputs for the clamping — an unnormalized signal is what would let one term
    swamp the other four and push the score off its own scale.
    """
    normalized = normalize_signals(AC022_SIGNALS, AC022_CLUES)

    assert normalized.line_logic_gap == pytest.approx(0.2)
    assert normalized.branch_pressure == pytest.approx(5 / 225)
    assert normalized.time_pressure == pytest.approx(
        0.2 / (SECONDS_PER_CELL_BUDGET * 225)
    )
    assert normalized.size_pressure == pytest.approx(
        (225 - MIN_SUPPORTED_CELLS) / (MAX_SUPPORTED_CELLS - MIN_SUPPORTED_CELLS)
    )
    density = clue_density(AC022_CLUES, 225)
    assert normalized.density_pressure == pytest.approx(
        1.0 - abs(density - HARDEST_DENSITY) / HARDEST_DENSITY
    )

    absurd = normalize_signals(
        _Signals(
            line_logic_cells=10_000,
            total_cells=16,  # a 4x4, below the supported range
            branch_nodes=10_000,
            elapsed_seconds=10_000.0,
        ),
        _clues_at_density(16, 1.0),
    )
    for field in fields(absurd):
        value = getattr(absurd, field.name)
        assert 0.0 <= value <= 1.0, f"{field.name} escaped 0..1 at {value}"


# --------------------------------------------------------------------------
# AC-023 — the anchor: zero backtracking sits at the easiest end
# --------------------------------------------------------------------------

#: The ceiling AC-023 rests on. A candidate solved entirely by line logic with
#: zero backtracking zeroes the two terms that carry ``1 - solve_time`` of the
#: scale between them, so nothing but the wall-clock term is left to score —
#: whatever its size and density do to the relief factor. Well inside ADR-0005's
#: Easy band (score <= 33), and by construction rather than by calibration.
ANCHOR_CEILING = SCORE_MAX * SIGNAL_WEIGHTS.solve_time


def test_zero_backtracking_scores_at_the_easiest_end() -> None:
    """AC-023: solved entirely by line logic, no guesses -> the easy extreme.

    A 15x15 at the hardest density and a realistically quick line-logic solve.
    Two assertions, deliberately: the structural ceiling that holds on any
    machine however slow, and the near-zero score a real one produces.
    """
    signals = _Signals(
        line_logic_cells=225,
        total_cells=225,
        branch_nodes=0,
        elapsed_seconds=0.01,
    )

    score = score_difficulty(signals, _clues_at_density(225, HARDEST_DENSITY))

    assert score <= ANCHOR_CEILING
    assert score < 1.0


def test_zero_backtracking_scores_easiest_at_every_size_and_density() -> None:
    """AC-023 is a property of the formula, not of one hand-picked puzzle.

    ADR-0013's whole reason for making size and density normalizers instead of
    additive terms: "a puzzle solved entirely by line logic, with zero
    backtracking, must land at the easy extreme *regardless of size*". A
    50x50 at the hardest density is where an additive size term would betray
    that — it is the largest supported grid, scored at the density the density
    term peaks on — so it is in the sweep, alongside the smallest.
    """
    for total_cells in (MIN_SUPPORTED_CELLS, 400, 900, MAX_SUPPORTED_CELLS):
        for density in (0.0, 0.1, HARDEST_DENSITY, 0.9, 1.0):
            signals = _Signals(
                line_logic_cells=total_cells,
                total_cells=total_cells,
                branch_nodes=0,
                # A full second, far longer than any real line-logic-only
                # solve, so the sweep is not leaning on a fast machine.
                elapsed_seconds=1.0,
            )

            score = score_difficulty(signals, _clues_at_density(total_cells, density))

            assert score <= ANCHOR_CEILING, (
                f"a line-logic-only {total_cells}-cell puzzle at density "
                f"{density} scored {score}, above the anchor ceiling "
                f"{ANCHOR_CEILING}: size or density is adding to the score "
                f"instead of normalizing it (ADR-0013)"
            )


def test_zero_backtracking_scores_easiest_on_a_real_solve() -> None:
    """AC-023 end to end: a real puzzle, the real solver, the real signals.

    The synthetic cases above prove the arithmetic. This one proves the
    arithmetic is fed what it assumes — that ``SolveSignals`` really does
    report full coverage and a zero branch count for a puzzle line logic
    finishes, so the anchor is not resting on a fixture that flatters it.
    """
    clues = compute_clues(PLUS)
    result = solve(*clues)

    assert result.is_unique
    assert result.signals.branch_nodes == 0

    score = score_difficulty(result.signals, clues.rows)

    assert score <= ANCHOR_CEILING
    assert score < 1.0


def test_a_puzzle_that_needs_guessing_scores_above_one_that_does_not() -> None:
    """The scale's one ordering claim, on two real solves.

    AC-023 fixes where the easy end *is*; this fixes that it is an end — that
    a puzzle the solver had to branch on scores strictly above one it did not.
    Both puzzles are solved for real, so this fails if the signals stop
    distinguishing the two search paths.
    """
    plus_clues = compute_clues(PLUS)
    line_logic_only = solve(*plus_clues)
    needs_guessing = solve(BRANCHING_ROWS, BRANCHING_COLUMNS)

    assert needs_guessing.signals.branch_nodes > 0

    easy = score_difficulty(line_logic_only.signals, plus_clues.rows)
    harder = score_difficulty(needs_guessing.signals, BRANCHING_ROWS)

    assert harder > easy


# --------------------------------------------------------------------------
# Monotonicity — the scale reads in one direction (card item 3)
# --------------------------------------------------------------------------


def test_score_never_decreases_as_backtracking_increases() -> None:
    """More guessing is never easier, holding the other four signals still.

    A spread rather than a pair, because a formula can be monotone across one
    step and not across the range — and because the branch term is capped at
    one branch node per cell, which is a place a naive implementation stops
    being monotone (or starts being non-monotone the other way).
    """
    scores = [
        score_difficulty(
            replace(AC022_SIGNALS, branch_nodes=branch_nodes), AC022_CLUES
        )
        for branch_nodes in (0, 1, 5, 25, 100, 224, 225, 1000)
    ]

    assert scores == sorted(scores), f"not monotone in branch count: {scores}"
    assert scores[0] < scores[-2], "the branch count barely moved the score"
    # Past the cap the term saturates rather than continuing to climb, which
    # is what stops one pathological puzzle from dominating the whole scale.
    assert scores[-1] == pytest.approx(scores[-2])


def test_score_never_increases_as_line_logic_solves_more_of_the_grid() -> None:
    """The more line logic settles before the first guess, the easier it is.

    The inversion ADR-0013 specifies ("normalized as solved-before-first-branch
    cells / total cells, *inverted*"), checked as an ordering rather than as an
    arithmetic identity — a sign slip here would put the whole scale backwards
    while every individual score still looked plausible.
    """
    scores = [
        score_difficulty(
            replace(AC022_SIGNALS, line_logic_cells=line_logic_cells), AC022_CLUES
        )
        for line_logic_cells in (0, 45, 90, 180, 224, 225)
    ]

    assert scores == sorted(scores, reverse=True), (
        f"not monotone in line-logic coverage: {scores}"
    )
    assert scores[0] > scores[-1]


def test_score_never_decreases_as_the_solve_takes_longer() -> None:
    """Wall-clock time reads in the same direction as the other two (FR-009)."""
    scores = [
        score_difficulty(
            replace(AC022_SIGNALS, elapsed_seconds=elapsed), AC022_CLUES
        )
        for elapsed in (0.0, 0.05, 0.2, 1.0, 2.8125, 30.0)
    ]

    assert scores == sorted(scores), f"not monotone in solve time: {scores}"
    assert scores[-1] == pytest.approx(scores[-2]), "the time term should saturate"


def test_a_big_easy_puzzle_does_not_outscore_a_small_hard_one() -> None:
    """ADR-0013's named failure mode, stated as a test.

    "A big easy puzzle must not out-score a small hard one purely on cell
    count" — the raw-sum failure that would make every 50x50 Hard by size
    alone. The big one here is the largest supported grid, solved without a
    single guess; the small one is at the bottom of the supported range and
    fought for most of its cells.
    """
    big_and_easy = score_difficulty(
        _Signals(
            line_logic_cells=MAX_SUPPORTED_CELLS,
            total_cells=MAX_SUPPORTED_CELLS,
            branch_nodes=0,
            elapsed_seconds=0.5,
        ),
        _clues_at_density(MAX_SUPPORTED_CELLS, HARDEST_DENSITY),
    )
    small_and_hard = score_difficulty(
        _Signals(
            line_logic_cells=20,
            total_cells=MIN_SUPPORTED_CELLS,
            branch_nodes=60,
            elapsed_seconds=1.0,
        ),
        _clues_at_density(MIN_SUPPORTED_CELLS, HARDEST_DENSITY),
    )

    assert small_and_hard > big_and_easy


# --------------------------------------------------------------------------
# The scale's ends, and the density normalizer
# --------------------------------------------------------------------------


def test_the_hardest_possible_signals_reach_the_top_of_the_scale() -> None:
    """The far end exists and is reachable: nothing line logic settled, a
    branch per cell, the whole time budget spent, at the largest supported
    size and the hardest density."""
    score = score_difficulty(
        _Signals(
            line_logic_cells=0,
            total_cells=MAX_SUPPORTED_CELLS,
            branch_nodes=MAX_SUPPORTED_CELLS,
            elapsed_seconds=SECONDS_PER_CELL_BUDGET * MAX_SUPPORTED_CELLS,
        ),
        _clues_at_density(MAX_SUPPORTED_CELLS, HARDEST_DENSITY),
    )

    assert score == pytest.approx(SCORE_MAX)


def test_density_peaks_at_the_midpoint_and_falls_off_both_ways() -> None:
    """ADR-0013's non-monotonic density term: hardest in the middle.

    "Both very sparse and very dense grids tend to be easier" — so the term is
    nearness to 0.5, not density itself. A linearly-increasing density term
    would pass a sparse-vs-mid comparison and fail this one.
    """
    scores = {
        density: score_difficulty(
            AC022_SIGNALS, _clues_at_density(225, density)
        )
        for density in (0.0, 0.25, HARDEST_DENSITY, 0.75, 1.0)
    }

    assert scores[HARDEST_DENSITY] == max(scores.values())
    assert scores[0.0] == pytest.approx(scores[1.0])
    assert scores[0.25] == pytest.approx(scores[0.75])
    assert scores[0.0] < scores[0.25] < scores[HARDEST_DENSITY]


def test_clue_density_is_the_same_from_either_orientation() -> None:
    """One grid, two clue sets, one density — so the caller cannot pass the
    wrong one. Row clues and column clues encode the same filled cells, which
    is why :func:`score_difficulty` takes "the clues" and not "the row clues".
    """
    clues = compute_clues(PLUS)
    total_cells = 25

    from_rows = clue_density(clues.rows, total_cells)
    from_columns = clue_density(clues.columns, total_cells)

    assert from_rows == from_columns == pytest.approx(9 / 25)


def test_clue_density_counts_the_empty_line_marker_as_empty() -> None:
    """AC-013's ``(0,)`` is a clue like any other and contributes no cells."""
    assert clue_density(((0,), (0,), (0,)), 9) == 0.0
    assert clue_density(((3,), (0,), (3,)), 9) == pytest.approx(6 / 9)


# --------------------------------------------------------------------------
# Contract: purity, degenerate input, and the weight table
# --------------------------------------------------------------------------


def test_scoring_is_deterministic_and_does_not_touch_its_inputs() -> None:
    """A pure function of the solve result (the card's fourth item).

    Scored twice, the same candidate gives the same number — no clock read, no
    randomness, no accumulated module state — and the signals it was handed
    come back untouched, which is what lets CARD-010's resample loop score a
    candidate and then keep using it.
    """
    signals = replace(AC022_SIGNALS)

    first = score_difficulty(signals, AC022_CLUES)
    second = score_difficulty(signals, AC022_CLUES)

    assert first == second
    assert signals == AC022_SIGNALS


def test_an_empty_grid_scores_at_the_bottom_rather_than_dividing_by_zero() -> None:
    """Nothing to solve, no difficulty to report — and no ``ZeroDivisionError``.

    A 0-cell grid is not a puzzle anyone asks for, but the solver answers for
    one (``tests/test_solver.py`` pins it as uniquely solvable), so the scorer
    has to have an answer rather than an exception.
    """
    empty = _Signals(
        line_logic_cells=0, total_cells=0, branch_nodes=0, elapsed_seconds=0.0
    )

    assert score_difficulty(empty, ()) == SCORE_MIN


def test_weights_stay_injectable_so_the_scale_can_be_retuned() -> None:
    """FR-010's "tunable later without changing the solver", as a seam.

    ADR-0013 expects these numbers to be recalibrated once real score
    distributions exist. That has to be a change to the table, not to the
    formula — so the table is a parameter, and swapping it moves the score.
    """
    backtracking_heavy = SignalWeights(
        line_logic=0.1, backtracking=0.8, solve_time=0.1, size=0.0, density=0.0
    )

    retuned = score_difficulty(AC022_SIGNALS, AC022_CLUES, weights=backtracking_heavy)
    default = score_difficulty(AC022_SIGNALS, AC022_CLUES)

    assert retuned != pytest.approx(default)
    assert SCORE_MIN <= retuned <= SCORE_MAX


def test_a_retune_that_would_break_the_scale_is_rejected() -> None:
    """The weight table's own invariant, checked where a retune happens.

    Effort weights that do not sum to 1.0 would silently move the top of the
    scale ADR-0005's tier cutoffs are drawn on; normalizer weights above 1.0
    would let the relief factor go negative and invert the score. Neither
    would fail anywhere else, so both fail here.
    """
    with pytest.raises(ValueError, match="sum to 1.0"):
        SignalWeights(
            line_logic=0.5, backtracking=0.5, solve_time=0.5, size=0.1, density=0.1
        )

    with pytest.raises(ValueError, match="at most 1.0"):
        SignalWeights(
            line_logic=0.4, backtracking=0.45, solve_time=0.15, size=0.7, density=0.7
        )


def test_the_shipped_weights_keep_the_anchor_inside_the_easiest_band() -> None:
    """The calibration guard behind AC-023, stated on the table itself.

    ``ANCHOR_CEILING`` — the most a zero-backtracking, fully-line-logic-solved
    puzzle can score — is ``100 * solve_time``. AC-023 survives any retune that
    keeps that under ADR-0005's Easy cutoff of 33, and this is where a retune
    that did not would be caught, rather than in whichever AC test happened to
    notice first.
    """
    assert SCORE_MAX * SIGNAL_WEIGHTS.solve_time < 33.0


def test_solver_signals_satisfy_the_protocol_this_module_scores() -> None:
    """The seam ADR-0007 forbids an import across, checked instead.

    ``difficulty`` may not import ``solver`` (both are capability modules; see
    ``tests/test_cli.py::test_every_import_in_the_package_points_inward``), so
    nothing in the package would notice if ``SolveSignals`` renamed a field
    the scorer reads. This test is what notices: a real ``SolveSignals``,
    scored, plus the member names spelled out.
    """
    signals = solve(*compute_clues(PLUS)).signals

    assert isinstance(signals, SolveSignals)
    for member in ("line_logic_cells", "total_cells", "branch_nodes", "elapsed_seconds"):
        assert hasattr(signals, member), (
            f"SolveSignals no longer reports {member!r}, which "
            f"difficulty.SolverSignals requires"
        )

    assert SCORE_MIN <= score_difficulty(signals, compute_clues(PLUS).rows) <= SCORE_MAX
