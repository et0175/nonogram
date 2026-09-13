"""COMP-006 tests: FR-026's strategy-ladder grade (ADR-0029's 0..100 scale).

AC / test-id mapping — the trace.yml names, kept traceable from these
pytest-idiomatic function names:

    AC-118  TestScoreDifficulty_LineSolvableCorpusSpansAllThreeBands
                -> test_a_line_solvable_corpus_spans_all_three_bands
    AC-119  TestScoreDifficulty_DeeperLineReasoningScoresHigher
                -> test_deeper_line_reasoning_scores_higher*
    AC-120  TestScoreDifficulty_RequiresGuessingAttributeSetWhenSearchBranched
                -> test_requires_guessing_attribute_set_when_search_branched*
    AC-121  TestScoreDifficulty_RequiresGuessingAttributeClearForLineSolvable
                -> test_requires_guessing_attribute_clear_for_line_solvable*
    AC-122  TestScoreDifficulty_IgnoresElapsedSeconds
                -> test_ignores_elapsed_seconds*

Superseded by the above and deliberately not re-used as names (the FR-003 /
AC-009 convention): AC-022 ``TestScoreDifficulty_CombinesSignals`` and AC-023
``TestScoreDifficulty_ZeroBacktrackingScoresEasiest``, both of ADR-0013's
five-signal formula. AC-023 in particular is *contradicted* rather than merely
replaced — under ADR-0029 a puzzle with zero backtracking can score anywhere on
the scale, which is the whole point of FR-026.

Two kinds of test here, and the split is deliberate.

*Synthetic* signals (:class:`_Signals`) drive everything that needs one input
varied and the rest held still — which no real puzzle will do on request. That
fixture carries **all six** members of ``solver.SolveSignals``, including the
two ``difficulty.SolverSignals`` deliberately does not name, so that "the
scorer ignores ``elapsed_seconds``" is a claim this file can actually pose.

*Real solves* tie that fixture back to the solver: the corpus test below grades
~290 genuinely generated puzzles through ``solve`` and ``score_difficulty``
with nothing faked, and :func:`test_the_ladder_is_the_solvers_own_ladder` pins
COMP-006's copy of the rung names against COMP-005's. ADR-0007 forbids
``difficulty`` importing ``solver``, so that binding has to live here, in the
test tree, where the import is legal — the same arrangement
``tests/property/test_solver_uniqueness.py`` uses for its oracle.
"""

from __future__ import annotations

import random
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field, replace

import pytest

from nonogram import difficulty
from nonogram.clues import compute_clues
from nonogram.difficulty import (
    EASY_MAX_SCORE,
    LADDER,
    MEDIUM_MAX_SCORE,
    RUNG_BANDS,
    RUNG_LINE_DP,
    RUNG_PROBE_CONTRADICTION,
    RUNG_SIMPLE_OVERLAP,
    SCORE_MAX,
    SCORE_MIN,
    Tier,
    classify,
    hardest_rung,
    score_difficulty,
)
from nonogram.solver import RUNG_ORDER, SolveSignals, solve
from nonogram.sourcing import random_grid

# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _Signals:
    """A stand-in for ``SolveSignals`` that a test can vary one field of.

    Carries every member the real dataclass does, not only the three
    ``difficulty.SolverSignals`` names. That is the point: the two the protocol
    omits — ``line_logic_cells`` and ``elapsed_seconds`` — are exactly the ones
    ADR-0029/R3 says nothing graded may read, and a fixture that omitted them
    too could not pose the question (AC-122, EC-016).
    """

    total_cells: int
    branch_nodes: int = 0
    rung_cells: Mapping[str, int] = field(default_factory=dict)
    line_logic_cells: int = 0
    backtracks: int = 0
    elapsed_seconds: float = 0.0


def _rungs(
    simple_overlap: int = 0, line_dp: int = 0, probe_contradiction: int = 0
) -> Mapping[str, int]:
    """A per-rung histogram carrying all three keys, as the solver reports it."""
    return {
        RUNG_SIMPLE_OVERLAP: simple_overlap,
        RUNG_LINE_DP: line_dp,
        RUNG_PROBE_CONTRADICTION: probe_contradiction,
    }


def _signals(
    total_cells: int,
    *,
    branch_nodes: int = 0,
    elapsed_seconds: float = 0.0,
    **rung_counts: int,
) -> _Signals:
    return _Signals(
        total_cells=total_cells,
        branch_nodes=branch_nodes,
        rung_cells=_rungs(**rung_counts),
        line_logic_cells=total_cells,
        elapsed_seconds=elapsed_seconds,
    )


#: A 5x5 plus sign — unique, and settled entirely by the overlap rule (the same
#: puzzle ``tests/test_solver.py`` pins the zero-branch signals on).
PLUS = [
    [glyph == "#" for glyph in row]
    for row in ("..#..", "..#..", "#####", "..#..", "..#..")
]


# --------------------------------------------------------------------------
# The ladder itself, and the bands drawn over it
# --------------------------------------------------------------------------


def test_the_ladder_is_the_solvers_own_ladder() -> None:
    """COMP-006's rung names are COMP-005's, bound here rather than imported.

    ADR-0007 forbids ``difficulty`` importing ``solver`` (a lateral edge
    between two capability modules), so the three names are spelled out in
    each — the precedent ``propagate.py``'s ``mask_runs`` set, which re-derives
    one clue-encoding check rather than importing ``clues.py`` and is
    cross-checked from this same tree.

    Reimplementation across a closed boundary is only safe if something binds
    the two copies. This is that something: a rename or a reorder on either
    side fails here, at the seam, rather than silently re-grading the corpus.
    The *order* is asserted and not just the set — the order is the grading.
    """
    assert LADDER == RUNG_ORDER


def test_the_three_rung_bands_are_adr_0005s_cutoffs_and_tile_the_scale() -> None:
    """ADR-0029, as corrected 2026-09-13: the band edges *are* the cutoffs.

    Not idealised thirds. The distinction is a third of a point wide and it
    decides 88% of the corpus: at a width of 33.33 a full-share bottom rung
    scores 33.33, lands above ``EASY_MAX_SCORE`` and classifies Medium, which
    would empty the Easy band and make AC-118 unsatisfiable.

    Asserted against ``EASY_MAX_SCORE``/``MEDIUM_MAX_SCORE`` rather than
    against ``33``/``66``, so a legitimate retune moves this test's expectation
    with it — the literal numbers are checked once, in
    ``tests/test_difficulty_tiers.py``, against ADR-0005 directly.
    """
    assert RUNG_BANDS[RUNG_SIMPLE_OVERLAP] == (SCORE_MIN, EASY_MAX_SCORE)
    assert RUNG_BANDS[RUNG_LINE_DP] == (EASY_MAX_SCORE, MEDIUM_MAX_SCORE)
    assert RUNG_BANDS[RUNG_PROBE_CONTRADICTION] == (MEDIUM_MAX_SCORE, SCORE_MAX)

    # No gap and no overlap: each band starts where the last one ended, the
    # first at the bottom of the scale and the last at the top.
    edges = [RUNG_BANDS[rung] for rung in LADDER]
    assert edges[0][0] == SCORE_MIN
    assert edges[-1][1] == SCORE_MAX
    assert all(high == nxt for (_, high), (nxt, _) in zip(edges, edges[1:]))


def test_every_rung_band_is_the_band_of_the_tier_that_rung_means() -> None:
    """ADR-0029's tier-per-rung mapping, as a table rather than as a sentence.

    Easy = the puzzle never left overlap, Medium = it needed the full placement
    intersection, Hard = it needed a refuted probe. The two tables are zipped
    from one another in the module, so this is really asserting that the zip is
    in the order a reader would assume.
    """
    assert [RUNG_BANDS[rung] for rung in LADDER] == [
        Tier.EASY.band,
        Tier.MEDIUM.band,
        Tier.HARD.band,
    ]


def test_hardest_rung_reads_the_top_of_the_histogram_and_ignores_empty_rungs() -> None:
    """A rung is "present" only if it settled a cell.

    That is what makes the within-rung share strictly positive, which is what
    makes ADR-0029/R1's cross-rung ordering *strict* rather than merely
    non-decreasing.
    """
    assert hardest_rung(_rungs(simple_overlap=25)) == RUNG_SIMPLE_OVERLAP
    assert hardest_rung(_rungs(simple_overlap=20, line_dp=5)) == RUNG_LINE_DP
    assert (
        hardest_rung(_rungs(simple_overlap=20, probe_contradiction=1))
        == RUNG_PROBE_CONTRADICTION
    )
    # A rung with a zero count is not present, even sitting above a used one.
    assert hardest_rung(_rungs(simple_overlap=20, line_dp=0)) == RUNG_SIMPLE_OVERLAP
    # Nothing settled anywhere: no grade at all, which is ADR-0029's scoping
    # rule for a clue set that is not a puzzle.
    assert hardest_rung(_rungs()) is None
    assert hardest_rung({}) is None


# --------------------------------------------------------------------------
# The band edge AC-118 stands or falls on
# --------------------------------------------------------------------------


@pytest.mark.parametrize("total_cells", [100, 144, 225, 400, 900])
def test_a_puzzle_that_never_leaves_overlap_scores_exactly_the_easy_cutoff(
    total_cells: int,
) -> None:
    """The single most load-bearing number in this module, at every extent.

    A puzzle topping out at ``simple_overlap`` has *every* settled cell at that
    rung by definition, so its within-rung share is exactly 1.0 — measured
    1.000 in 420 of 420 line-solvable grids before this card was written, and
    in every ``simple_overlap`` puzzle of the AC-118 corpus below. Its score is
    therefore the top of the first band exactly.

    That number has to be ``EASY_MAX_SCORE`` and not a hair above it, because
    the cutoff is an *inclusive* upper bound: at 33.33 this puzzle classifies
    Medium and the Easy band is empty. Pinned as equality, not as
    ``<= EASY_MAX_SCORE``, because "just under" would pass a test that exists
    to catch "just over".

    Size does not enter (ADR-0029), so the same equality holds from 10x10 to
    30x30 — which is why this is parametrized over extents rather than stated
    once.
    """
    score = score_difficulty(_signals(total_cells, simple_overlap=total_cells))

    assert score == EASY_MAX_SCORE
    assert classify(score, 0) is Tier.EASY


def test_the_first_cell_at_a_higher_rung_lifts_the_score_out_of_the_band_below() -> None:
    """The other half of the edge: a rung that settled *one* cell scores above
    its band's floor, not on it.

    ``33.0`` is Easy and ``33.0 + epsilon`` is Medium, so a 900-cell puzzle
    with a single ``line_dp`` cell has to land in the second band. If the share
    could be zero the two bands would touch at a point belonging to the lower
    one, and the ladder's strictness would fail on exactly this case.
    """
    score = score_difficulty(_signals(900, simple_overlap=899, line_dp=1))

    assert score > EASY_MAX_SCORE
    assert classify(score, 0) is Tier.MEDIUM


# --------------------------------------------------------------------------
# AC-118 — the corpus spans every band
# --------------------------------------------------------------------------

#: The AC-118 corpus plan: extents from 10x10 to 30x30, each at several
#: densities. The densities are chosen from a measured map of the source, not
#: for tidiness, and that choice is the whole reason this test is not flaky.
#:
#: Two facts about random nonograms shape it. (1) The uniqueness rate climbs
#: steeply with density — at 10x10 it is 6 draws in 400 at density 30 and 396
#: in 400 at density 75 — so a corpus drawn only at the low end spends its
#: budget on candidates that are not puzzles. (2) The ``line_dp`` rung, i.e.
#: the whole Medium band, lives in a narrow window around densities 45-50 at
#: the smaller extents: 22% of unique 12x12 grids at density 45 top out there,
#: against 0.4% at density 55 and none at all at 65 and above. A corpus drawn
#: at one density — or only at the fast, high-density end — misses Medium
#: entirely, and the test then fails looking like flake rather than like
#: measurement.
#:
#: The large extents are sampled at the high-density end deliberately: a 25x25
#: at density 45 is the known-hard class for the search (seconds per candidate,
#: ``docs/GENERATION_ALGORITHM.md`` §6.4) and would make this a benchmark
#: rather than a test. What the extents are here for is AC-118's "spanning
#: 10x10..30x30", and that is satisfied by sampling them at all.
_CORPUS_PLAN: tuple[tuple[tuple[int, int], tuple[int, ...]], ...] = (
    ((10, 10), (45, 50, 55, 65, 75)),
    ((12, 12), (45, 50, 60, 70)),
    ((15, 15), (45, 50, 55, 65, 75)),
    ((20, 20), (55, 60, 70)),
    ((25, 25), (60, 70)),
    ((30, 30), (60, 70)),
)

#: Unique puzzles wanted per (extent, density) cell, and how many grids may be
#: drawn to find them. 14 across 21 cells is ~290 puzzles, comfortably past
#: AC-118's 200 — the margin is there because the criterion is about *coverage*
#: of three bands whose smallest member is under 3% of the corpus.
_CORPUS_PER_CELL = 14
_CORPUS_DRAW_BUDGET = 120

#: One fixed seed, so the corpus is the same on every machine and every run
#: (ADR-0015's discipline applied to a test fixture). The band coverage below
#: was checked at seeds 118, 2026 and 7 before this one was pinned: Medium came
#: out at 8, 13 and 7 puzzles respectively, so the margin is real and not an
#: artefact of the seed that happened to be tried first.
_CORPUS_SEED = 118

#: AC-118's own floor.
_CORPUS_MINIMUM = 200

#: One graded corpus row: ``(extent, density, score, branch_nodes, top rung)``.
_CorpusRow = tuple[tuple[int, int], int, float, int, "str | None"]


def _line_solvable_corpus() -> list[_CorpusRow]:
    """Grade the seeded corpus, one row per uniquely-solvable grid.

    Nothing is faked on the grading side: every grid goes through
    ``compute_clues`` -> ``solve`` -> ``score_difficulty``, and a draw that is
    not a puzzle (0 or >= 2 solutions) is dropped before grading, exactly as
    the generator drops it (INV-002 — and ADR-0029's scoping rule, since such a
    clue set carries no rung attribution to grade).
    """
    rng = random.Random(_CORPUS_SEED)
    rows: list[_CorpusRow] = []
    for (width, height), densities in _CORPUS_PLAN:
        for density in densities:
            kept = 0
            for _ in range(_CORPUS_DRAW_BUDGET):
                if kept >= _CORPUS_PER_CELL:
                    break
                grid = random_grid.generate(width, height, density, rng)
                clues = compute_clues(grid)
                result = solve(clues.rows, clues.columns)
                if result.solution_count != 1:
                    continue
                kept += 1
                rows.append(
                    (
                        (width, height),
                        density,
                        score_difficulty(result.signals),
                        result.signals.branch_nodes,
                        hardest_rung(result.signals.rung_cells),
                    )
                )
    return rows


def test_a_line_solvable_corpus_spans_all_three_bands() -> None:
    """AC-118 — ``TestScoreDifficulty_LineSolvableCorpusSpansAllThreeBands``.

    *given* a seeded corpus of >= 200 line-solvable puzzles (solution count 1,
    branch_nodes 0) spanning 10x10..30x30, *when* each is scored, *then* at
    least one scores inside each of Easy, Medium and Hard.

    This is the criterion ADR-0013 could not meet at all: its formula bounded a
    line-solvable puzzle at 15 points, so the corpus would have been 100% Easy
    whatever the retune. It is also the criterion the *pre-correction* band
    edges could not meet — at a width of 33.33 it would have been 0% Easy.

    The measured distribution at seed 118 — written into CARD-076's Worktree
    notes as the input for ADR-0005's owed recalibration — is **292 puzzles:
    Easy 258 (88.4%), Medium 8 (2.7%), Hard 26 (8.9%), Guess 0 (0%)**. The
    assertions below are ``>= 1`` per band and not those counts: the criterion
    is coverage, and pinning 8 would turn a harmless change in the source into
    a failure here. What *is* pinned tightly is the corpus size, the extent
    span and the Easy band's degeneracy — the three tests after this one.
    """
    corpus = _line_solvable_corpus()
    assert len(corpus) >= _CORPUS_MINIMUM, (
        f"the corpus plan yielded {len(corpus)} puzzles, below AC-118's "
        f"{_CORPUS_MINIMUM} — raise _CORPUS_PER_CELL or the draw budget"
    )

    # Every member is line-solvable, which is what AC-118 says its corpus is.
    assert all(branch_nodes == 0 for _, _, _, branch_nodes, _ in corpus)

    tiers = Counter(classify(score, branch) for _, _, score, branch, _ in corpus)
    for tier in (Tier.EASY, Tier.MEDIUM, Tier.HARD):
        assert tiers[tier] >= 1, (
            f"no corpus puzzle classified {tier.label}; distribution was "
            f"{ {t.label: n for t, n in tiers.items()} }"
        )


def test_the_corpus_covers_the_whole_supported_extent_range() -> None:
    """AC-118's "spanning 10x10..30x30", asserted rather than assumed.

    A corpus that quietly stopped finding unique 30x30 grids would still pass
    the band-coverage test above on its small extents alone, and the claim
    being made — that the grade is a fact about the puzzle and not about its
    size — would go unexercised at the top of the range.
    """
    extents = {extent for extent, _, _, _, _ in _line_solvable_corpus()}

    assert (10, 10) in extents
    assert (30, 30) in extents
    assert len(extents) == len(_CORPUS_PLAN)


def test_every_corpus_puzzle_that_never_left_overlap_scores_the_same_point() -> None:
    """The finding this card records and deliberately does **not** act on (G-5).

    Easy is a *single point* on the scale: a puzzle that never leaves
    ``simple_overlap`` has a within-rung share of exactly 1.0 by definition, so
    all 258 Easy puzzles of the corpus score 33.0 and nothing distinguishes
    them. The within-rung ordering ADR-0005's recalibration is waiting on
    therefore does not exist inside the bottom band — a fact about the
    secondary count, not a defect of the band edges.

    Pinned here so that the recalibration, when it comes, has to change this
    test on purpose rather than discover the property by accident.
    """
    easy_scores = {
        score
        for _, _, score, _, rung in _line_solvable_corpus()
        if rung == RUNG_SIMPLE_OVERLAP
    }

    assert easy_scores == {EASY_MAX_SCORE}


def test_no_corpus_puzzle_needed_a_real_branch() -> None:
    """ADR-0025's measured zero, re-measured by this card.

    0 of 6,620 grids in ADR-0029's own sweep, 0 of 462 in CARD-076's
    pre-implementation measurement, and 0 of ~290 here. It is recorded as a
    *test* rather than as a comment because it is the fact that makes
    ``Tier.GUESS`` untestable end to end — every AC-120 case in this file uses
    a synthetic branch count, and this is why.

    A failure here is not a regression: it is the safety net catching
    something, and the right response is to celebrate and then check that the
    puzzle really did need a guess.
    """
    assert all(branch_nodes == 0 for _, _, _, branch_nodes, _ in _line_solvable_corpus())


# --------------------------------------------------------------------------
# AC-119 — deeper line reasoning scores higher
# --------------------------------------------------------------------------


def test_deeper_line_reasoning_scores_higher() -> None:
    """AC-119 — ``TestScoreDifficulty_DeeperLineReasoningScoresHigher``, cross-rung.

    The criterion is written in ADR-0029's *pre-revision* vocabulary — "A
    (2 sweeps, 90% decided first sweep)" against "B (12 sweeps, 20% first
    sweep)" — and sweeps are exactly what the 2026-09-12 revision removed from
    the ladder: a sweep index is a statement about iteration order, not about
    inference, and grading by it made a puzzle score differently from its own
    transpose. Read forward onto the ladder the criterion survives intact and
    means: **A is the shallow puzzle the overlap rule finishes by itself, B is
    the deep one that needed a dearer technique; B scores strictly higher.**

    Both are 20x20 and both are line-solvable (``branch_nodes == 0``), as
    AC-119 specifies, so the only thing separating them is the depth of the
    reasoning — which is the claim.
    """
    shallow = _signals(400, simple_overlap=400)
    deep = _signals(400, simple_overlap=320, line_dp=80)

    assert score_difficulty(deep) > score_difficulty(shallow)
    assert classify(score_difficulty(shallow), 0) is Tier.EASY
    assert classify(score_difficulty(deep), 0) is Tier.MEDIUM


def test_deeper_line_reasoning_scores_higher_even_at_one_cell_of_depth() -> None:
    """The extreme of the same claim: 399 easy cells and one that was not.

    A scale on which "almost entirely overlap" rounded back down to Easy would
    satisfy the comfortable case above and fail the one that matters — the
    puzzle whose single hard deduction is the whole reason it is not easy.
    """
    shallow = _signals(400, simple_overlap=400)
    barely_deep = _signals(400, simple_overlap=399, line_dp=1)

    assert score_difficulty(barely_deep) > score_difficulty(shallow)


@pytest.mark.parametrize(
    "rung", [RUNG_LINE_DP, RUNG_PROBE_CONTRADICTION], ids=["line_dp", "probe"]
)
def test_deeper_line_reasoning_scores_higher_within_one_rung(rung: str) -> None:
    """AC-119's tiebreak half — ADR-0029's declared Negative ("coarse inside a
    rung; AC-119's strictly-greater case must hold through the tiebreak when
    both puzzles share a top rung").

    Two 20x20 puzzles that both top out at the same rung are separated only by
    ADR-0029's secondary count, the share of cells that rung settled. More of
    the grid needing the dearer technique is the deeper puzzle.

    **Not parametrized over ``simple_overlap``, and that is a finding rather
    than an omission.** A puzzle that tops out at the bottom rung has settled
    *every* cell there, so its share is 1.0 without exception and there is no
    tiebreak to exercise: the case cannot be posed for that rung without
    fabricating a histogram the solver cannot emit (some cells at
    ``simple_overlap``, none anywhere else, and yet not all of them). So the
    tiebreak is covered at the two rungs where it is real, and the bottom
    rung's degeneracy is pinned instead by
    ``test_every_corpus_puzzle_that_never_left_overlap_scores_the_same_point``.
    """
    less = _signals(400, simple_overlap=340, **{rung: 60})
    more = _signals(400, simple_overlap=280, **{rung: 120})

    assert score_difficulty(more) > score_difficulty(less)
    # Still the same tier: the tiebreak orders inside a band, it does not move
    # a puzzle out of one. That is ADR-0029's coarseness, stated as a property.
    assert classify(score_difficulty(more), 0) is classify(score_difficulty(less), 0)


def test_a_higher_rung_outscores_a_lower_one_whatever_the_shares_are() -> None:
    """ADR-0029/R1 orders by rung *first*: no share at a lower rung overtakes
    any share at a higher one.

    The case that would break it is a lower rung with the whole grid against a
    higher rung with a single cell — the largest possible secondary count
    against the smallest. The band edges are what make it hold, so this is the
    property the band arithmetic exists to deliver.
    """
    maximal_overlap = score_difficulty(_signals(400, simple_overlap=400))
    minimal_dp = score_difficulty(_signals(400, simple_overlap=399, line_dp=1))
    maximal_dp = score_difficulty(_signals(400, simple_overlap=1, line_dp=399))
    minimal_probe = score_difficulty(
        _signals(400, simple_overlap=399, probe_contradiction=1)
    )

    assert maximal_overlap < minimal_dp
    assert maximal_dp < minimal_probe


# --------------------------------------------------------------------------
# AC-120 / AC-121 — the Guess tier is a fact about the solve
# --------------------------------------------------------------------------

# Every case below drives ``classify`` with a *synthetic* branch count, and that
# is not a shortcut. ``Tier.GUESS`` is unreachable from the generator: 0 of
# 6,620 uniquely-solvable grids in ADR-0029's measurement and 0 of 462 in
# CARD-076's needed a real branch after the solve's own one-step lookahead
# phase, and the AC-118 corpus above adds ~290 more with the same result
# (``test_no_corpus_puzzle_needed_a_real_branch``). The tier is a deliberate,
# measured safety net (ADR-0025, History 2026-09-12), so the only way to
# exercise it is to pose the solve fact it keys on directly.


@pytest.mark.parametrize("branch_nodes", [1, 2, 17, 4000])
def test_requires_guessing_attribute_set_when_search_branched(
    branch_nodes: int,
) -> None:
    """AC-120 — a solve that branched classifies ``Tier.GUESS``.

    Parametrized over the whole range of "at least one" rather than checking a
    single case, because EC-015's threshold is ``>= 1`` and a rule written as
    ``> 1`` or as a ratio against the cell count would pass on one well-chosen
    value.
    """
    signals = _signals(400, simple_overlap=400, branch_nodes=branch_nodes)

    assert classify(score_difficulty(signals), signals.branch_nodes) is Tier.GUESS


@pytest.mark.parametrize(
    "rung_counts",
    [
        {"simple_overlap": 400},
        {"simple_overlap": 300, "line_dp": 100},
        {"simple_overlap": 300, "probe_contradiction": 100},
        {"simple_overlap": 1, "probe_contradiction": 399},
    ],
    ids=["overlap", "dp", "probe", "almost-all-probe"],
)
def test_requires_guessing_attribute_set_whatever_the_score_would_have_been(
    rung_counts: dict[str, int],
) -> None:
    """AC-120's real content: the tier is the solve fact, **not** a threshold.

    The same branch count against four different scores spanning all three
    bands. A classifier that read the score first — or that treated Guess as
    "Hard, but more so" — would answer three different tiers here.
    """
    signals = _signals(400, branch_nodes=1, **rung_counts)

    assert classify(score_difficulty(signals), signals.branch_nodes) is Tier.GUESS


@pytest.mark.parametrize(
    "rung_counts",
    [
        {"simple_overlap": 400},
        {"simple_overlap": 300, "line_dp": 100},
        {"simple_overlap": 300, "probe_contradiction": 100},
        {"probe_contradiction": 400},
    ],
    ids=["overlap", "dp", "probe", "all-probe"],
)
def test_requires_guessing_attribute_clear_for_line_solvable(
    rung_counts: dict[str, int],
) -> None:
    """AC-121 — ``branch_nodes == 0`` is never ``Tier.GUESS``, whatever band it
    lands in.

    The converse of AC-120, and the promise ``--difficulty hard`` makes: Easy,
    Medium and Hard contain only line-solvable puzzles (ADR-0025/R1). Checked
    at the top of the scale too — a puzzle that needed refutation on every cell
    is Hard, not Guess, because refutation is a rung and a branch is not.
    """
    signals = _signals(400, branch_nodes=0, **rung_counts)
    tier = classify(score_difficulty(signals), signals.branch_nodes)

    assert tier is not Tier.GUESS
    assert tier in (Tier.EASY, Tier.MEDIUM, Tier.HARD)


def test_a_real_generated_puzzle_is_line_solvable_and_is_not_guess() -> None:
    """The same claim end to end, on a solve nobody faked.

    Ties the synthetic fixture back to the solver: the plus sign really does
    come back with ``branch_nodes == 0`` and a ``simple_overlap``-only
    histogram, which is what the AC-121 cases above assume a real solve can
    report.
    """
    clues = compute_clues(PLUS)
    result = solve(clues.rows, clues.columns)

    assert result.solution_count == 1
    assert result.signals.branch_nodes == 0
    assert hardest_rung(result.signals.rung_cells) == RUNG_SIMPLE_OVERLAP

    score = score_difficulty(result.signals)
    assert score == EASY_MAX_SCORE
    assert classify(score, result.signals.branch_nodes) is Tier.EASY


# --------------------------------------------------------------------------
# AC-122 — no clock anywhere (NFR-007, CON-014)
# --------------------------------------------------------------------------


def test_ignores_elapsed_seconds() -> None:
    """AC-122 — ``TestScoreDifficulty_IgnoresElapsedSeconds``.

    *given* two signal records identical except elapsed_seconds 0.001s and
    4.9s, *when* scored, *then* the scores are equal to the last digit.

    ``==`` and not ``approx``: the criterion says "to the last digit", and the
    two values come from the same arithmetic on the same inputs, so anything
    short of bit-equality would mean the clock got in.
    """
    fast = _signals(400, simple_overlap=300, line_dp=100, elapsed_seconds=0.001)
    slow = replace(fast, elapsed_seconds=4.9)

    assert score_difficulty(fast) == score_difficulty(slow)
    assert classify(score_difficulty(fast), fast.branch_nodes) is classify(
        score_difficulty(slow), slow.branch_nodes
    )


def test_the_scorer_is_not_even_handed_a_clock_to_ignore() -> None:
    """CON-014 made structural rather than behavioural.

    ``elapsed_seconds`` is not a member of ``difficulty.SolverSignals`` at all,
    so the scorer cannot read it — the protocol is the enforcement. A test that
    only varied the value would still pass if somebody added the member back
    and then took care not to use it; this one fails the moment the member
    reappears, which is when the mistake is cheap.

    The same holds for ``line_logic_cells``: it survives on the solver's own
    dataclass for NFR-001 reporting and is deliberately not graded.
    """
    protocol_members = {
        name for name in vars(difficulty.SolverSignals) if not name.startswith("_")
    }

    assert protocol_members == {"total_cells", "branch_nodes", "rung_cells"}


def test_the_module_holds_no_clock_size_or_density_term_at_all() -> None:
    """ADR-0029/R3 and guardrail G-2, as a named-surface check.

    ADR-0013's five-signal machinery is *retired*, not merely unused: a weight
    table left in the module is a weight table somebody re-wires. The names
    below are the ones ADR-0029's Neutral section lists as retiring with the
    formula, plus the two cell-span constants that existed only as the size
    normalizer's denominators, plus the classifier ADR-0025 says can no longer
    stand alone.
    """
    retired = [
        "SignalWeights",
        "SIGNAL_WEIGHTS",
        "NormalizedSignals",
        "normalize_signals",
        "clue_density",
        "SECONDS_PER_CELL_BUDGET",
        "HARDEST_DENSITY",
        "MIN_SUPPORTED_CELLS",
        "MAX_SUPPORTED_CELLS",
        "tier_for_score",
    ]
    still_there = [name for name in retired if hasattr(difficulty, name)]

    assert still_there == [], (
        f"ADR-0013's formula surface is supposed to be gone: {still_there}"
    )


# --------------------------------------------------------------------------
# Contract: purity, degenerate input, and what the solver actually reports
# --------------------------------------------------------------------------


def test_solver_signals_satisfy_the_protocol_this_module_grades() -> None:
    """The seam ADR-0007 leaves open, checked from the side that may see both.

    ``difficulty`` may not import ``solver``, so nothing in ``src/`` asserts
    that ``SolveSignals`` actually satisfies ``SolverSignals``; a renamed field
    on either side would surface as an ``AttributeError`` at generation time.
    This test is the binding, and it checks the *members*, because a structural
    protocol of read-only properties cannot be ``isinstance``-checked usefully.
    """
    for member in ("total_cells", "branch_nodes", "rung_cells"):
        assert member in SolveSignals.__slots__, member

    # And the real thing grades without complaint.
    clues = compute_clues(PLUS)
    signals = solve(clues.rows, clues.columns).signals
    assert SCORE_MIN <= score_difficulty(signals) <= SCORE_MAX


def test_scoring_is_deterministic_and_does_not_touch_its_inputs() -> None:
    """Pure: same input, same answer, and the argument comes back unchanged.

    The resample loop scores every candidate it draws, so a scorer with state
    would make a run depend on how many candidates preceded it — which is
    ADR-0015's reproducibility promise broken somewhere nobody would look.
    """
    signals = _signals(225, simple_overlap=200, line_dp=25)
    before = dict(signals.rung_cells)

    first = score_difficulty(signals)
    second = score_difficulty(signals)

    assert first == second
    assert dict(signals.rung_cells) == before


@pytest.mark.parametrize(
    "signals",
    [
        _signals(0),
        _signals(100),
        _Signals(total_cells=100, branch_nodes=0, rung_cells={}),
    ],
    ids=["empty-grid", "nothing-settled", "no-histogram-at-all"],
)
def test_a_clue_set_with_no_rung_attribution_scores_at_the_bottom(
    signals: _Signals,
) -> None:
    """ADR-0029's scoping rule, at the scorer: no attribution, no grade.

    A clue set with 0 or >= 2 solutions carries an all-zero histogram, and the
    generator discards it long before anything would score it (INV-002,
    CON-004). :data:`SCORE_MIN` is returned rather than raising because the
    number means *nothing* in that case, and a scorer that crashed on it would
    turn a caller's ordering mistake into a failure at the point furthest from
    its cause.
    """
    assert score_difficulty(signals) == SCORE_MIN


def test_a_histogram_that_over_counts_the_grid_still_lands_on_the_scale() -> None:
    """Total, not trusting: a share above 1 clamps instead of leaving the band.

    Nothing the solver emits can do this — the counts sum to the tagged cells —
    but the scorer's answer feeds a tier decision and an exported number, and
    "bend toward the end of the scale" is a better failure than "an Easy puzzle
    scoring 82".
    """
    score = score_difficulty(_signals(100, simple_overlap=250))

    assert score == EASY_MAX_SCORE
    assert SCORE_MIN <= score <= SCORE_MAX


def test_an_unknown_rung_name_is_ignored_rather_than_crashing_the_scorer() -> None:
    """A fourth rung would be a decision, not a crash at COMP-006.

    If the solver ever grows one, the right response is an ADR revision that
    re-draws the bands — and until then a scorer that raised would take the
    whole pipeline down over a telemetry key it did not recognise.
    """
    signals = _Signals(
        total_cells=100,
        branch_nodes=0,
        rung_cells={RUNG_SIMPLE_OVERLAP: 100, "trial_and_error": 40},
    )

    assert score_difficulty(signals) == EASY_MAX_SCORE
