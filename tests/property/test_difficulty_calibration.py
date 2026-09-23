"""CARD-137: the medium/hard cutoff, measured rather than argued.

    CARD-137 AC-1  TestDifficulty_MediumIsReachableOnASeededCorpus
                       -> test_medium_is_reachable_on_a_seeded_corpus
    CARD-137 AC-2  PropertyTest_Difficulty_TierIsMonotoneInScore
                       -> test_tier_is_monotone_in_score*

Two claims, and a third this card must not break.

*Medium is reachable.* ADR-0005's medium/hard cutoff sat on ``66.0`` until this
card, where it coincided with a rung boundary, so Medium meant exactly "the
puzzle needed the full placement DP somewhere and a probe nowhere". That is a
narrow accident of a random draw: the owner measured 5 Medium puzzles in 300 on
production. The cutoff is ``90.0`` now, which coincides with nothing on the
ladder and cuts the ``probe_contradiction`` rung at 70.6% of the grid — Medium
is "a little non-trivial work", Hard is "a lot" — and this file is where the
claim that Medium is now actually reachable is a test rather than a promise.

*The tier is monotone in the score.* A recalibration is free to move where a
band ends; it is not free to make a higher score classify easier than a lower
one. That property is what lets the admin panel sort by score and read the
tiers off in order, and it is asserted here over both synthetic scores and real
solves.

*No stored grade moves.* The cutoff move re-files scores; it does not change
them. The score mapping is ``difficulty.RUNG_BANDS`` and this card left it
exactly as ADR-0029 drew it, which
:func:`test_no_stored_grade_moves_the_score_mapping_is_untouched` pins against
the literal historical numbers. Re-filing the rows that already exist is the
admin panel's ``POST /regrade`` action; nothing here writes to a database.

**The corpus is built in the density band the book generator actually uses, and
that is an instruction from the owner rather than a convenience.**
``orchestrator.generate_batch`` hardcodes density 50. Above density ~55 nearly
every random draw is settled by ``simple_overlap`` alone and scores exactly
33.0 — 100% Easy at d65+, 98.3% at d60, 79.2% at d55 (CARD-137 step 1, 1001
puzzles) — so a density-uniform corpus is about 70% pinned at the Easy point
and says nothing about the puzzles this project prints. Sampling 45..52 is not
tuning the corpus until the number comes out right; it is refusing to make the
calibration a statement about densities nobody generates books at.

House style, and load-bearing rather than decorative. There is no ``hypothesis``
in the dependency baseline (ADR-0006), so a "property" is a large seeded corpus
built with stdlib :class:`random.Random`, with a **minimum case count asserted
inside the test** so the corpus cannot silently shrink to nothing and leave a
green tick behind. And the expectations are derived independently of the
function under test wherever that is possible: :func:`_tier_by_interval` reads
the band table as intervals instead of calling ``classify``, and
:func:`_adr_0029_score` re-derives the score from the rung histogram against
ADR-0029's literal band edges instead of calling ``score_difficulty``.

Measured on this corpus (seed 20260923, 315 line-solvable puzzles, 12 s):

    easy 202 (64.1%)   medium 91 (28.9%)   hard 22 (7.0%)

It is built through ``random_grid.generate`` + ``compute_clues`` + ``solve``
rather than through ``orchestrator.generate`` — the precedent is
``tests/property/test_difficulty_ladder.py``'s ``_real_puzzles``, and the reason
is cost: CARD-137's step-1 sweep of 1001 puzzles through the orchestrator took
200 seconds, which is not a thing to put in a suite. The two paths grade
identically, because the orchestrator scores exactly the solve this corpus
scores and applies no second rule; measured side by side inside the same band,
160 orchestrator puzzles came back easy 64.4% / medium 35.0% / hard 0.6%
against this corpus's 64.1 / 28.9 / 7.0. The residual difference is which
candidates each path *keeps* — the orchestrator redraws and repairs a
non-unique grid (POL-006) instead of dropping it — not how either one grades.

Both differ from step 1's figure for the same band (easy 31.2% / medium 36.9% /
hard 31.9% over 401 puzzles), and the reason is worth recording rather than
tuning away: step 1 issued an equal number of *requests* per (extent, density)
cell, and because the orchestrator retries until it has a puzzle, its large
extents contributed as heavily as its small ones. A corpus of direct draws is
weighted by uniqueness yield instead, and at these densities a 10x10 yields
~40% unique against a 30x30's ~10%, so it is dominated by small grids — which
are overwhelmingly Easy. Neither weighting is wrong; they answer different
questions, and the AC only asks that Medium be reachable on a corpus of real
puzzles in the production band, which both say it is.
"""

from __future__ import annotations

import random
from collections import Counter
from collections.abc import Mapping
from functools import cache

import pytest

from nonogram.clues import compute_clues
from nonogram.difficulty import (
    SCORE_MAX,
    SCORE_MIN,
    TIER_BANDS,
    Tier,
    classify,
    hardest_rung,
    score_difficulty,
)
from nonogram.limits import MAX_SIZE, MIN_SIZE
from nonogram.solver import solve
from nonogram.sourcing import random_grid

#: The extents and densities the corpus draws from — every density inside the
#: production band (see the module docstring), and the extent range's own two
#: ends among them.
#:
#: The band is sampled from its floor at the small extents and from its ceiling
#: at the large ones, which is a measurement rather than a preference: mid
#: density at 25x25 and above is the solver's known-hard class
#: (``docs/GENERATION_ALGORITHM.md`` §6.4), and it is also where the uniqueness
#: yield collapses. 40 draws at 20x20 density 45 cost 6.0 seconds and returned
#: **zero** puzzles; the same 40 at density 51 cost 0.35 s and returned 9. A
#: corpus that sampled the band's floor at every extent would be a benchmark
#: that graded nothing.
_CORPUS_PLAN: tuple[tuple[tuple[int, int], tuple[int, ...]], ...] = (
    ((MIN_SIZE, MIN_SIZE), (45, 47, 49, 51)),
    ((12, 12), (45, 47, 49, 51)),
    ((15, 15), (46, 48, 50, 52)),
    ((18, 18), (48, 50, 52)),
    ((20, 20), (49, 51, 52)),
    ((25, 25), (51, 52)),
    ((MAX_SIZE, MAX_SIZE), (52,)),
)

#: Draws per (extent, density) cell. Every draw is solved; the ones that are
#: not puzzles are dropped, so the corpus is far smaller than this times the
#: cell count — about a third of it.
_DRAWS_PER_CELL = 55

#: The AC's own floor, asserted inside the test that uses the corpus.
_MIN_CORPUS = 200

#: The AC's medium share, as a fraction of the corpus.
_MEDIUM_FLOOR = 0.20

#: ADR-0029's rung bands, written as literals on purpose. This is the score
#: mapping CARD-137 did **not** touch, so re-deriving it from
#: ``difficulty.RUNG_BANDS`` would make the test agree with whatever the module
#: says rather than with what the ADR decided.
_ADR_0029_RUNG_BANDS: Mapping[str, tuple[float, float]] = {
    "simple_overlap": (0.0, 33.0),
    "line_dp": (33.0, 66.0),
    "probe_contradiction": (66.0, 100.0),
}


@cache
def _line_solvable_corpus(seed: int) -> tuple[object, ...]:
    """A seeded corpus of ``SolveSignals`` from genuinely solved unique puzzles.

    Every record is the output of one real ``solve`` of one real random grid;
    nothing is constructed. Non-puzzles (0 or >= 2 solutions) are dropped,
    which is what the generator does and what ADR-0029's scoping rule requires
    — such a clue set carries no rung attribution at all. Branching solves are
    dropped too, because the AC is about *line-solvable* puzzles; the corpus
    has never contained one (``test_difficulty_ladder.py``'s
    ``test_no_generated_puzzle_needs_a_branch`` is where that is asserted).

    Cached on the seed so that the tests below share one build: the corpus
    costs about twelve seconds and answers three different questions.
    """
    rng = random.Random(seed)
    records: list[object] = []
    for (width, height), densities in _CORPUS_PLAN:
        for density in densities:
            for _ in range(_DRAWS_PER_CELL):
                grid = random_grid.generate(width, height, density, rng)
                clues = compute_clues(grid)
                result = solve(clues.rows, clues.columns)
                if result.solution_count == 1 and result.signals.branch_nodes == 0:
                    records.append(result.signals)
    return tuple(records)


def _tier_by_interval(score: float) -> Tier:
    """Which band holds ``score``, read off :data:`TIER_BANDS` as intervals.

    The independent second implementation the house style asks for:
    ``classify`` walks the two cutoffs with ``<=``, this one looks the score up
    in the table of ``(low, high)`` pairs. Both read the same two constants, so
    a retune moves them together — what they cannot share is an off-by-one at a
    band edge, which is the bug this pairing exists to catch.
    """
    for tier, (low, high) in TIER_BANDS.items():
        if low < score <= high or (low == SCORE_MIN and score <= low):
            return tier
    raise AssertionError(f"no band holds {score!r}")  # pragma: no cover


def _adr_0029_score(signals: object) -> float:
    """``score_difficulty`` re-derived from the histogram, against the ADR.

    ``rung_base + share * rung_width`` over :data:`_ADR_0029_RUNG_BANDS`, with
    no reference to the module's own table. A card that re-scaled the ladder
    while claiming not to would disagree with this function.
    """
    rung = hardest_rung(signals.rung_cells)
    if rung is None:  # pragma: no cover - a graded puzzle settled cells
        return SCORE_MIN
    low, high = _ADR_0029_RUNG_BANDS[rung]
    share = signals.rung_cells[rung] / signals.total_cells
    return low + share * (high - low)


def _tier_rank(tier: Tier) -> int:
    """Easy < Medium < Hard, as an ordinal — the order tiers are *named* in.

    Taken from the enum's declaration order rather than from the band table, so
    that "the bands run in tier order" stays something to assert instead of
    something assumed.
    """
    return list(Tier).index(tier)


# --------------------------------------------------------------------------
# TestDifficulty_MediumIsReachableOnASeededCorpus
# --------------------------------------------------------------------------


def test_medium_is_reachable_on_a_seeded_corpus() -> None:
    """``TestDifficulty_MediumIsReachableOnASeededCorpus`` — CARD-137 AC-1.

    A seeded corpus of at least 200 line-solvable puzzles, drawn in the density
    band ``orchestrator.generate_batch`` actually uses (45..52 — see the module
    docstring for why that band and not a uniform one), classifies into all
    three tiers, and Medium holds at least 20% of them.

    This is the criterion the cutoff was moved to satisfy, and it fails at the
    old value: at ``MEDIUM_MAX_SCORE = 66.0`` this same corpus puts 15.6% in
    Medium against the 20% floor, against 20.3% in Hard — and 42 of those 64
    Hard puzzles scored in ``(66, 90]``, a handful of probed cells wearing the
    same label as a grid probed almost everywhere. The assertion below is on
    the tier the module actually reports, so if a later card moves the cutoff
    back it is this line that says so.
    """
    records = _line_solvable_corpus(seed=20260923)
    assert len(records) >= _MIN_CORPUS, (
        f"only {len(records)} line-solvable puzzles in the corpus; the AC asks "
        f"for {_MIN_CORPUS} and the claim would be close to vacuous"
    )

    tiers = Counter(classify(score_difficulty(signals)) for signals in records)

    assert set(tiers) == set(Tier), (
        f"a tier is empty on a {len(records)}-puzzle corpus: {dict(tiers)}"
    )
    assert tiers[Tier.MEDIUM] >= _MEDIUM_FLOOR * len(records), (
        f"medium holds {tiers[Tier.MEDIUM]} of {len(records)} "
        f"({100 * tiers[Tier.MEDIUM] / len(records):.1f}%), under the "
        f"{100 * _MEDIUM_FLOOR:.0f}% floor: {dict(tiers)}"
    )


def test_the_corpus_really_is_drawn_in_the_batch_generators_density_band() -> None:
    """Guard the corpus: the AC above is about a band, not about any corpus.

    ``generate_batch`` hardcodes density 50, and the whole argument for these
    numbers is that the corpus sits around it. A later edit that widened the
    plan upward would make the AC easy to pass and meaningless — every draw
    above ~55 is Easy — so the band is asserted rather than trusted, together
    with the extent range's two ends.
    """
    densities = {d for _, ds in _CORPUS_PLAN for d in ds}
    assert min(densities) >= 45 and max(densities) <= 52, densities

    extents = {extent for extent, _ in _CORPUS_PLAN}
    assert (MIN_SIZE, MIN_SIZE) in extents
    assert (MAX_SIZE, MAX_SIZE) in extents


# --------------------------------------------------------------------------
# PropertyTest_Difficulty_TierIsMonotoneInScore
# --------------------------------------------------------------------------


@pytest.mark.parametrize("seed", [137, 1370, 13700])
def test_tier_is_monotone_in_score(seed: int) -> None:
    """``PropertyTest_Difficulty_TierIsMonotoneInScore`` — CARD-137 AC-2.

    No score classifies harder than a higher score. Stated over every ordered
    pair of a seeded corpus of scores that spans the scale — including both
    cutoffs exactly, both cutoffs plus and minus an epsilon, and values off
    each end of the scale, because ``classify`` is total on the whole real line
    and a monotonicity that held only on 0..100 would be a weaker claim than
    the one made.

    ADR-0029/R1's cross-rung monotonicity is a property of the *score* and is
    unchanged by this card (``test_difficulty_ladder.py`` holds it). This is
    the other half: given that the score orders puzzles correctly, the tier
    must not un-order them.
    """
    rng = random.Random(seed)
    scores = [rng.uniform(-10.0, 110.0) for _ in range(600)]
    for edge in (SCORE_MIN, SCORE_MAX, *(b for band in TIER_BANDS.values() for b in band)):
        scores += [edge - 1e-9, edge, edge + 1e-9]
    assert len(scores) >= 600, "the corpus shrank"

    graded = sorted((score, classify(score)) for score in scores)

    for (_, lower_tier), (_, higher_tier) in zip(graded, graded[1:]):
        assert _tier_rank(lower_tier) <= _tier_rank(higher_tier), (
            f"{lower_tier} then {higher_tier} — the tier fell as the score rose"
        )

    # ...and the classifier agrees with the band table read as intervals, which
    # is what makes the ordering above an ordering of the *declared* bands.
    for score, tier in graded:
        if SCORE_MIN <= score <= SCORE_MAX:
            assert tier is _tier_by_interval(score), score

    assert {tier for _, tier in graded} == set(Tier), "the corpus missed a tier"


def test_tier_is_monotone_in_score_on_real_solves() -> None:
    """The same property over genuinely solved puzzles.

    The synthetic corpus can pose scores no solve produces; this one poses only
    what the solver emits. Both matter: the first checks the classifier is
    monotone over its input space, the second that the input space it is
    monotone over is the one real puzzles inhabit.
    """
    records = _line_solvable_corpus(seed=20260923)
    assert len(records) >= _MIN_CORPUS, "the corpus shrank"

    graded = sorted(
        (score_difficulty(signals), classify(score_difficulty(signals)))
        for signals in records
    )

    for (_, lower_tier), (_, higher_tier) in zip(graded, graded[1:]):
        assert _tier_rank(lower_tier) <= _tier_rank(higher_tier)


# --------------------------------------------------------------------------
# The invariant the recalibration must not break
# --------------------------------------------------------------------------


def test_no_stored_grade_moves_the_score_mapping_is_untouched() -> None:
    """CARD-137 moved a tier cutoff; it did not move a score.

    Every puzzle in the corpus scores exactly what ADR-0029's band arithmetic
    says it should, computed here from the rung histogram against the ADR's
    literal edges (0/33/66/100) rather than against the module's table. So a
    stored ``difficulty_score`` written before this card is still the number
    this build would compute — which is what makes re-filing the rows a matter
    for the admin panel's ``POST /regrade`` and not for a migration
    (ADR-0031/R3).

    The tiers, by contrast, are *expected* to move, and the last assertion says
    where: only inside the probe rung, and only upward — a row scoring in
    ``(66, 90]`` was Hard and is Medium, and nothing else changes hands.
    """
    records = _line_solvable_corpus(seed=20260923)
    assert len(records) >= _MIN_CORPUS, "the corpus shrank"

    for signals in records:
        assert score_difficulty(signals) == pytest.approx(_adr_0029_score(signals))

    # The re-filing, stated as a fact about score ranges rather than about rows.
    moved = [
        score
        for score in (score_difficulty(signals) for signals in records)
        if classify(score) is not _tier_under_the_old_cutoff(score)
    ]
    assert moved, "the corpus holds no puzzle the recalibration re-files"
    assert all(66.0 < score <= 90.0 for score in moved), sorted(moved)[:5]


def _tier_under_the_old_cutoff(score: float) -> Tier:
    """``classify`` as it read before CARD-137 — Easy [0, 33], Medium (33, 66].

    A frozen copy, not a parameterised classifier: it exists so the test above
    can say exactly which scores changed hands, and it is deliberately the only
    place in the tree that still knows the old figure.
    """
    if score <= 33.0:
        return Tier.EASY
    if score <= 66.0:
        return Tier.MEDIUM
    return Tier.HARD
