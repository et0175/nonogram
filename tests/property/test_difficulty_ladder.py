"""Engineering-constraint property tests for COMP-006's strategy ladder.

    EC-015          PropertyTest_ScoreDifficulty_RequiresGuessingIffSearchBranched
                        -> test_requires_guessing_iff_search_branched*
    EC-016          PropertyTest_ScoreDifficulty_IndependentOfElapsedTime
                        -> test_independent_of_elapsed_time*   (CON-014's declared check)
    ADR-0029/R1     PropertyTest_ScoreDifficulty_MonotoneInRungOrder
                        -> test_monotone_in_rung_order*

House style, and it is load-bearing here rather than decorative. There is no
``hypothesis`` in this project's dependency baseline (ADR-0006), so a "property"
is a large seeded corpus built with stdlib :class:`random.Random`, with a
**minimum case count asserted inside the test** so the corpus cannot silently
shrink to nothing and leave a green tick behind.

Where a corpus of synthetic signal records would be enough, this file builds one
*and* a corpus of real solves, because the two answer different questions: the
synthetic one covers the input space the scorer must be total over (including
the branch counts the generator has never once produced), and the real one
checks that the solver actually emits records of that shape.

The other house rule — *prefer an independent second implementation over
re-deriving a value with the function under test* — shows up in
:func:`_ladder_key`. The monotonicity property is checked against an ordinal
pair ``(rung index, share)`` computed straight from the histogram, never
against a second call to ``score_difficulty``; a bug in the band arithmetic
would otherwise agree with itself.
"""

from __future__ import annotations

import random
from collections.abc import Mapping
from dataclasses import dataclass, field, replace

import pytest

from nonogram.clues import compute_clues
from nonogram.difficulty import (
    LADDER,
    SCORE_MAX,
    SCORE_MIN,
    Tier,
    classify,
    hardest_rung,
    score_difficulty,
)
from nonogram.solver import solve
from nonogram.sourcing import random_grid

#: Extents and densities the seeded real-solve corpus draws from: both ends of
#: the supported range (ADR-0022), each at densities where a useful share of
#: draws come back uniquely solvable *and* the solve is cheap.
#:
#: The density list narrows as the extent grows, and that is a measurement
#: rather than a preference. Mid-density at 25x25 and above is the solver's
#: known-hard class (``docs/GENERATION_ALGORITHM.md`` §6.4): four 25x25 draws at
#: density 45 take 29 seconds, against 0.03 s at density 65. A property test
#: that sampled there would be a benchmark. What these corpora need from the
#: large extents is that the score is *size-free*, and that is exercised by
#: sampling them at all.
_CORPUS_PLAN: tuple[tuple[tuple[int, int], tuple[int, ...]], ...] = (
    ((10, 10), (45, 50, 55, 65, 75)),
    ((12, 12), (45, 50, 60, 70)),
    ((15, 15), (45, 50, 55, 65, 75)),
    ((20, 20), (55, 60, 70)),
    ((30, 30), (60, 70)),
)

#: Draws per (extent, density) cell. Every draw is solved; the ones that are not
#: puzzles are dropped, so the corpus is smaller than this times the cell count.
_DRAWS_PER_CELL = 14

#: Floors, asserted inside every test that uses a corpus.
_MIN_REAL_PUZZLES = 120
_MIN_SYNTHETIC_RECORDS = 500


@dataclass(frozen=True, slots=True)
class _Signals:
    """A synthetic ``SolveSignals``, carrying the clock members too.

    The two members ``difficulty.SolverSignals`` omits are present for the same
    reason as in ``tests/test_difficulty.py``: EC-016's question cannot be posed
    with a record that has no elapsed time to vary.
    """

    total_cells: int
    branch_nodes: int = 0
    rung_cells: Mapping[str, int] = field(default_factory=dict)
    line_logic_cells: int = 0
    backtracks: int = 0
    elapsed_seconds: float = 0.0


def _real_puzzles(seed: int) -> list[object]:
    """A seeded corpus of ``SolveSignals`` from genuinely solved unique puzzles.

    Every record is the output of one real ``solve`` of one real random grid;
    nothing is constructed. Non-puzzles (0 or >= 2 solutions) are dropped, which
    is what the generator does and what ADR-0029's scoping rule requires — such
    a clue set carries no rung attribution at all.
    """
    rng = random.Random(seed)
    records = []
    for (width, height), densities in _CORPUS_PLAN:
        for density in densities:
            for _ in range(_DRAWS_PER_CELL):
                grid = random_grid.generate(width, height, density, rng)
                clues = compute_clues(grid)
                result = solve(clues.rows, clues.columns)
                if result.solution_count == 1:
                    records.append(result.signals)
    return records


def _synthetic_records(seed: int, count: int) -> list[_Signals]:
    """A seeded corpus of signal records spanning the whole input space.

    Deliberately wider than anything the generator emits: branch counts the
    real pipeline has never produced (EC-015's entire subject), histograms that
    stop at each rung, and elapsed times from a microsecond to a minute. The
    scorer is total over its input, so the property has to be checked over the
    input and not over the sample.
    """
    rng = random.Random(seed)
    records = []
    for _ in range(count):
        width = rng.randint(10, 30)
        height = rng.randint(10, 30)
        total = width * height
        top = rng.randrange(len(LADDER))
        # Split the grid across the rungs up to and including `top`, leaving
        # `top` with at least one cell so that it is genuinely the top rung.
        counts = dict.fromkeys(LADDER, 0)
        remaining = total
        for level in range(top):
            share = rng.randint(0, remaining - 1)
            counts[LADDER[level]] = share
            remaining -= share
        counts[LADDER[top]] = max(1, remaining)
        records.append(
            _Signals(
                total_cells=total,
                branch_nodes=rng.choice([0, 0, 0, 1, 2, 7, 250, 10_000]),
                rung_cells=counts,
                line_logic_cells=rng.randint(0, total),
                elapsed_seconds=rng.choice([0.0, 1e-6, 0.001, 0.2, 4.9, 60.0]),
            )
        )
    return records


def _ladder_key(signals: _Signals | object) -> tuple[int, float]:
    """ADR-0029's ordering, derived *independently* of the function under test.

    The ADR says the grade is "the rung of the hardest technique required" and,
    inside a rung, "the number of cells settled at that rung divided by the
    total". That is an ordinal followed by a ratio, and this function is that
    pair — computed from the histogram with no band table, no affine map and no
    call to ``score_difficulty``.

    The property the tests assert is that the scorer's number induces the same
    order this pair does. Deriving the expectation from the scorer instead
    would only check that it agrees with itself.
    """
    rung_cells = signals.rung_cells
    rung = hardest_rung(rung_cells)
    if rung is None:
        return (-1, 0.0)
    return (LADDER.index(rung), rung_cells[rung] / signals.total_cells)


# --------------------------------------------------------------------------
# EC-015 — the tier is `guess` iff the verifying solve branched
# --------------------------------------------------------------------------


def test_requires_guessing_iff_search_branched() -> None:
    """``PropertyTest_ScoreDifficulty_RequiresGuessingIffSearchBranched``.

    EC-015, both directions, over a corpus that spans the whole branch-count
    input space: for any uniquely solvable puzzle the tier is ``guess`` **iff**
    the verifying solve's ``branch_nodes`` is greater than zero — a fact about
    the solve, never a threshold on the score.

    The "iff" is what the corpus is for. Either half alone is satisfiable by a
    broken classifier: one that always answered ``GUESS`` passes the forward
    direction, and one that never did passes the reverse. Checked together,
    across every band the score can land in, only the real rule survives.
    """
    records = _synthetic_records(seed=15, count=900)
    assert len(records) >= _MIN_SYNTHETIC_RECORDS, "the corpus shrank"

    branched = 0
    for signals in records:
        tier = classify(score_difficulty(signals), signals.branch_nodes)
        assert (tier is Tier.GUESS) == (signals.branch_nodes > 0), signals
        branched += signals.branch_nodes > 0

    # Both halves of the "iff" were actually exercised, and not by a handful of
    # cases: a corpus that drifted to all-branching or none-branching would
    # still pass the loop above.
    assert branched >= 100
    assert len(records) - branched >= 100


def test_requires_guessing_is_decided_before_the_score_is_looked_at() -> None:
    """EC-015's "never a threshold", stated as an independence.

    Holding the branch count and varying the score across the full 0..100
    range must not move the tier off ``GUESS`` once; holding the branch count
    at zero must not move it *onto* ``GUESS`` once. Together that says the
    score is not consulted at all in the first case — which is what "a fact
    about the solve" means operationally.
    """
    records = _synthetic_records(seed=16, count=600)
    assert len(records) >= _MIN_SYNTHETIC_RECORDS, "the corpus shrank"

    scores_seen = set()
    for signals in records:
        score = score_difficulty(signals)
        scores_seen.add(round(score))
        assert classify(score, 1) is Tier.GUESS
        assert classify(score, 0) is not Tier.GUESS

    # The scores really did span the scale rather than clustering in one band.
    assert min(scores_seen) <= 33 and max(scores_seen) >= 67


def test_no_real_generated_puzzle_is_classified_guess() -> None:
    """EC-015 against real solves — and the measurement it records.

    ``Tier.GUESS`` has an assignment rate of zero for the sources this build
    has: 0 of 6,620 grids in ADR-0029's sweep, 0 of 462 in CARD-076's, and 0
    here. So this corpus exercises the *reverse* direction of EC-015 on real
    data — every genuinely generated puzzle is line-solvable and none is
    classified ``GUESS`` — and the forward direction is left to the synthetic
    corpus above, which is the only place it can be posed.

    The minimum case count is asserted for the usual reason, and it matters
    doubly here: a corpus that had quietly stopped producing *any* unique
    puzzle would make the "none is GUESS" claim vacuously true.
    """
    records = _real_puzzles(seed=155)
    assert len(records) >= _MIN_REAL_PUZZLES, (
        f"only {len(records)} unique puzzles in the corpus; the property would "
        "be close to vacuous"
    )

    for signals in records:
        assert signals.branch_nodes == 0
        assert classify(score_difficulty(signals), signals.branch_nodes) is not Tier.GUESS


# --------------------------------------------------------------------------
# EC-016 / CON-014 — no clock reading anywhere
# --------------------------------------------------------------------------


def test_independent_of_elapsed_time() -> None:
    """``PropertyTest_ScoreDifficulty_IndependentOfElapsedTime`` — CON-014's
    declared check.

    For any two signal records differing only in ``elapsed_seconds``,
    ``score_difficulty`` returns the same score and the tier decision is the
    same — every extent, every clue set, every elapsed value.

    Checked on **real** ``SolveSignals`` records, with ``dataclasses.replace``
    substituting the elapsed time: that is a genuine record of a genuine solve
    with one field moved, which is exactly the counterfactual AC-123's dilated
    clock produces on a slower host. Equality is exact for the same reason
    AC-122 asks for it — the clock is either an input or it is not.
    """
    records = _real_puzzles(seed=16016)
    assert len(records) >= _MIN_REAL_PUZZLES, "the corpus shrank"

    dilations = (0.0, 1e-6, 0.001, 0.2, 1.0, 4.9, 50.0, 3600.0)
    for signals in records:
        baseline_score = score_difficulty(signals)
        baseline_tier = classify(baseline_score, signals.branch_nodes)
        for elapsed in dilations:
            moved = replace(signals, elapsed_seconds=elapsed)
            assert score_difficulty(moved) == baseline_score
            assert classify(score_difficulty(moved), moved.branch_nodes) is baseline_tier


def test_independent_of_elapsed_time_across_the_whole_input_space() -> None:
    """The same property over synthetic records, including branching ones.

    The real corpus cannot reach the branching half of the input space (its
    measured rate is zero), and "the clock does not enter the tier decision" is
    a claim about that half too — a classifier that fell back to a clock when
    ``branch_nodes`` was non-zero would pass the real-corpus test above.
    """
    records = _synthetic_records(seed=16017, count=700)
    assert len(records) >= _MIN_SYNTHETIC_RECORDS, "the corpus shrank"

    for signals in records:
        stopped = replace(signals, elapsed_seconds=0.0)
        slow = replace(signals, elapsed_seconds=600.0)
        assert score_difficulty(stopped) == score_difficulty(slow)
        assert classify(score_difficulty(stopped), stopped.branch_nodes) is classify(
            score_difficulty(slow), slow.branch_nodes
        )


# --------------------------------------------------------------------------
# ADR-0029/R1 — the score is monotone in ladder order
# --------------------------------------------------------------------------


def test_monotone_in_rung_order() -> None:
    """``PropertyTest_ScoreDifficulty_MonotoneInRungOrder``.

    For line-solvable puzzles, the score is monotone in ladder order: any
    puzzle topping out at a higher rung scores strictly above any puzzle
    topping out at a lower one, and within a rung the order follows the
    settled-cell share.

    Checked as "the scorer induces the same order as :func:`_ladder_key`" over
    every ordered pair in a seeded corpus — an O(n^2) comparison against an
    independently derived key, which is what makes this a property rather than
    a restatement of the formula.

    ADR-0029/R1 scopes the strictness to "puzzles of the same extent" and the
    corpus deliberately mixes extents anyway: under this ADR size does not
    enter the score at all, so the cross-rung half must hold *between* extents
    too, and a normaliser sneaking back in would show up here first.
    """
    records = [s for s in _synthetic_records(seed=291, count=260) if s.branch_nodes == 0]
    assert len(records) >= 60, f"only {len(records)} line-solvable records"

    scored = [(score_difficulty(s), _ladder_key(s)) for s in records]
    rungs_seen = {key[0] for _, key in scored}
    assert rungs_seen == set(range(len(LADDER))), (
        f"the corpus did not reach every rung: {sorted(rungs_seen)}"
    )

    for score_a, key_a in scored:
        for score_b, key_b in scored:
            if key_a[0] != key_b[0]:
                # Different top rungs: strict, and in ladder order.
                assert (score_a < score_b) == (key_a[0] < key_b[0])
            elif key_a[1] != key_b[1]:
                # Same rung: the settled-cell share breaks the tie.
                assert (score_a < score_b) == (key_a[1] < key_b[1])
            else:
                assert score_a == score_b


def test_monotone_in_rung_order_on_real_solves() -> None:
    """The same ordering over genuinely solved puzzles.

    The synthetic corpus can pose histograms the solver never emits; this one
    poses only what it does. Both matter: the first checks the scorer is right
    over its input space, the second that the input space it is right over is
    the one the solver inhabits.
    """
    records = _real_puzzles(seed=292)
    assert len(records) >= _MIN_REAL_PUZZLES, "the corpus shrank"

    scored = [(score_difficulty(s), _ladder_key(s)) for s in records]
    for score_a, key_a in scored:
        for score_b, key_b in scored:
            if key_a[0] != key_b[0]:
                assert (score_a < score_b) == (key_a[0] < key_b[0])
            elif key_a[1] != key_b[1]:
                assert (score_a < score_b) == (key_a[1] < key_b[1])


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_every_score_lands_on_the_scale_and_in_its_rungs_own_band(seed: int) -> None:
    """The containment half of ADR-0029/R1: a rung's puzzles stay in its band.

    Not implied by the ordering property — an ordering can be correct on a
    scale that has drifted off 0..100 — and it is what POL-004's resample
    predicate, the DB column and the JSON export all assume.
    """
    records = _synthetic_records(seed=seed, count=400)
    assert len(records) >= 200, "the corpus shrank"

    for signals in records:
        score = score_difficulty(signals)
        assert SCORE_MIN <= score <= SCORE_MAX
        # Line-solvable puzzles land in the band their rung maps onto; the
        # branching ones are not graded on this ladder at all (ADR-0025).
        if signals.branch_nodes == 0:
            expected = (Tier.EASY, Tier.MEDIUM, Tier.HARD)[_ladder_key(signals)[0]]
            assert classify(score, 0) is expected
