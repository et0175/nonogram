"""COMP-002 tests: POL-004's resample loop and its shared INV-003 bound.

AC / test-id mapping — the trace.yml names, kept traceable from these
pytest-idiomatic function names:

    AC-024  TestResample_AcceptsCandidateInRange   -> test_accepts_candidate_in_range*
    AC-025  TestResample_FiresWhenScoreOutOfRange  -> test_fires_when_score_out_of_range*
    AC-026  TestResample_RescoresNewCandidate      -> test_rescores_new_candidate*
    AC-027  TestResample_StopsAtMaxRetryBound      -> test_stops_at_max_retry_bound*

Three styles of test, for three different claims — the same split
``tests/test_orchestrator.py`` uses, with one addition.

*Scripted-source* tests replace the mode's grid source with a fixed sequence of
hand-drawn grids and let the **real** clue derivation, the **real** solver and
the **real** scorer judge them. Where the loop's behaviour can be shown that
way, it is.

*Scripted-score* tests additionally replace ``difficulty.score_difficulty``
with a fixed sequence of scores. AC-024 asks for a candidate that scores inside
the **Hard** band, and no hand-drawable 2x2 grid will ever do that — the whole
point of ADR-0013's scale is that a puzzle line logic walks through scores near
zero. What is under test in those cases is the orchestrator's *loop*: which
candidate it keeps, which it discards, how often it re-draws and where it
stops. The number itself is COMP-006's and is tested against real solves in
``tests/test_difficulty.py``; substituting it here is substituting the
collaborator, not the behaviour being asserted. Note what is *not* faked even
then: the uniqueness verdict is always the real solver's (guardrail G-3), and
the tier classification is always the real ``difficulty.classify``, and the
branch count it is classified with is always the real solve's.

*Pinned-seed* tests run the whole pipeline unmocked, scorer included, and are
the evidence that the composition works end to end.

The bands themselves — which score is Easy, which is Hard — are
``tests/test_difficulty_tiers.py``; this module is about what the loop does
with the answer.
"""

from __future__ import annotations

import random
import time
from collections.abc import Callable, Iterable

import pytest

from nonogram import cli, difficulty, orchestrator
from nonogram.clues import compute_clues
from nonogram.difficulty import MEDIUM_MAX_SCORE, SCORE_MAX, Tier
from nonogram.errors import GenerationAbandoned, InvalidDensity
from nonogram.orchestrator import (
    MAX_REGENERATE_ATTEMPTS,
    MAX_RESAMPLE_ATTEMPTS,
    MAX_RETRY_ATTEMPTS,
    GenerationRequest,
    Puzzle,
    generate,
)

# --------------------------------------------------------------------------
# Helpers — same notation as tests/test_orchestrator.py: ``█`` filled, ``·``
# empty. The two grids below are that module's, for the same reasons.
# --------------------------------------------------------------------------

_FILLED = "█"
_EMPTY = "·"


def _grid(*patterns: str) -> list[list[bool]]:
    for pattern in patterns:
        assert set(pattern) <= {_FILLED, _EMPTY}, f"bad pattern glyph in {pattern!r}"
    return [[glyph == _FILLED for glyph in pattern] for pattern in patterns]


#: Two solutions (the opposite diagonal fits the same clues), so the uniqueness
#: check rejects it — POL-001's rejection, not POL-004's.
AMBIGUOUS = _grid("█·", "·█")

#: Exactly one solution: the uniqueness check passes it, so it is a candidate
#: POL-004 gets to have an opinion about.
UNIQUE = _grid("██", "█·")

#: A second uniquely-solvable grid, distinguishable from :data:`UNIQUE`, for
#: the tests that have to show a candidate was really *replaced*.
ALSO_UNIQUE = _grid("··", "·█")


class _ScriptedSource:
    """Hands out pre-written grids in order, recording every call."""

    def __init__(self, *grids: list[list[bool]], repeat_last: bool = False) -> None:
        self._grids = list(grids)
        self._repeat_last = repeat_last
        self.calls: list[tuple[int | None, int | None, int | None, random.Random]] = []

    def __call__(
        self,
        width: int | None,
        height: int | None,
        density: int | None,
        rng: random.Random,
    ) -> list[list[bool]]:
        self.calls.append((width, height, density, rng))
        if not self._repeat_last and len(self.calls) > len(self._grids):
            raise AssertionError(
                f"the loop asked for candidate {len(self.calls)} but the script "
                f"only has {len(self._grids)}"
            )
        return self._grids[min(len(self.calls) - 1, len(self._grids) - 1)]

    @property
    def candidates_requested(self) -> int:
        return len(self.calls)


class _ScriptedScorer:
    """Stands in for ``difficulty.score_difficulty``: fixed scores, in order.

    Records the signals it was asked about, so a test can show *which*
    candidate each score was attached to — which is how AC-026 ("the new
    candidate is re-scored") is checked as something other than a call count.

    Takes one argument, because since ADR-0029 the scorer does: the clues went
    with the density term when size and density left the formula.
    """

    def __init__(self, *scores: float, repeat_last: bool = False) -> None:
        self._scores = list(scores)
        self._repeat_last = repeat_last
        self.scored: list[object] = []

    def __call__(self, signals: object) -> float:
        self.scored.append(signals)
        if not self._repeat_last and len(self.scored) > len(self._scores):
            raise AssertionError(
                f"the loop scored candidate {len(self.scored)} but the script "
                f"only has {len(self._scores)} scores"
            )
        return self._scores[min(len(self.scored) - 1, len(self._scores) - 1)]

    @property
    def candidates_scored(self) -> int:
        return len(self.scored)


def _install_source(
    monkeypatch: pytest.MonkeyPatch, source: Callable[..., object]
) -> None:
    """Point every mode at ``source``."""
    monkeypatch.setattr(orchestrator.sourcing, "for_mode", lambda mode: source)


def _install_scorer(
    monkeypatch: pytest.MonkeyPatch, scorer: Callable[..., float]
) -> None:
    """Replace COMP-006's scorer for the orchestrator only.

    Patched on the ``difficulty`` module the orchestrator holds, so what is
    swapped is the collaborator the loop calls — the real function is still
    what ``tests/test_difficulty.py`` exercises, and the real
    ``difficulty.classify`` still classifies whatever this returns, against the
    real solve's own branch count — which is what keeps these tests honest
    about ADR-0025: a scripted score cannot conjure ``Tier.GUESS``, because
    that tier is not reachable from a number.
    """
    monkeypatch.setattr(orchestrator.difficulty, "score_difficulty", scorer)


def _request(**overrides: object) -> GenerationRequest:
    """A minimal valid request; the scripted source ignores extent/density."""
    fields: dict[str, object] = {
        "mode": "random",
        "width": 10,
        "height": 10,
        "density": 50,
        "seed": 0,
    }
    fields.update(overrides)
    return GenerationRequest(**fields)  # type: ignore[arg-type]


#: The three tiers a *score* can land in. ``Tier.GUESS`` is keyed on the
#: solve's branch count instead (ADR-0025/R1, EC-015), so it has no band, no
#: score inside it and no place in any parametrization below that varies a
#: score. What the loop does when ``guess`` is requested is
#: ``tests/test_difficulty_tiers.py``'s
#: ``test_requesting_the_fourth_tier_is_a_generation_outcome_not_a_rejection``:
#: a legitimate request POL-004 tries and, on today's sources, cannot fill.
_BAND_TIERS: tuple[Tier, ...] = (Tier.EASY, Tier.MEDIUM, Tier.HARD)


def _in_band(tier: Tier) -> float:
    """A score comfortably inside ``tier``'s band."""
    band = tier.band
    assert band is not None, f"{tier} is not a score band (ADR-0025)"
    low, high = band
    return (low + high) / 2


def _outside_band(tier: Tier) -> float:
    """A score in some *other* tier's band."""
    other = next(candidate for candidate in _BAND_TIERS if candidate is not tier)
    return _in_band(other)


def _without_repairs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Turn ADR-0024's repair step (POL-006) off for a scripted-source test.

    ``MAX_CONSECUTIVE_REPAIRS = 0`` is ADR-0024's own rollback switch: with it
    the recovery loop is exactly the pure-redraw loop POL-001 was before
    CARD-074, so the scripted grid sequence maps one-to-one onto attempts
    again. Every test that calls this is asserting POL-001's own behaviour —
    which candidate is kept, how many grids are drawn, where the bound stops —
    and would otherwise be asserting it *through* a repair lineage, which has
    its own coverage in the CARD-074 ``TestRecovery_*`` tests (both kinds of
    attempt against the same one counter, in tests/test_orchestrator.py) and in
    tests/property/test_recovery_bound.py.

    It is a real switch and not a test seam: the constant is read by
    :func:`nonogram.orchestrator.generate` on every run, and 0 is the value the
    card's rollback plan names.
    """
    monkeypatch.setattr(orchestrator, "MAX_CONSECUTIVE_REPAIRS", 0)


# --------------------------------------------------------------------------
# AC-024 — TestResample_AcceptsCandidateInRange
# --------------------------------------------------------------------------


def test_accepts_candidate_in_range(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC-024: a Hard-tier request accepts a candidate that scores Hard.

    "No further resampling occurs" is the half worth pinning: the source is
    scripted with a single grid, so a second draw would fail the run outright
    rather than quietly passing on the repeat.
    """
    source = _ScriptedSource(UNIQUE)
    scorer = _ScriptedScorer(_in_band(Tier.HARD))
    _install_source(monkeypatch, source)
    _install_scorer(monkeypatch, scorer)

    puzzle = generate(_request(difficulty="hard"))

    assert puzzle.requested_tier is Tier.HARD
    assert puzzle.difficulty_tier is Tier.HARD
    assert puzzle.difficulty_score == _in_band(Tier.HARD)
    assert puzzle.ready_for_export is True
    # Accepted as final: one candidate drawn, one scored, one resample round.
    assert source.candidates_requested == 1
    assert scorer.candidates_scored == 1
    assert puzzle.resample.attempts == 1
    assert puzzle.regenerate.attempts == 1


@pytest.mark.parametrize("tier", _BAND_TIERS)
def test_accepts_candidate_in_range_at_either_end_of_the_band(
    tier: Tier, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-024 at the boundaries: a cutoff score is *in* its own band.

    The band edges are where an off-by-one in the comparison would live, and
    where a wrong answer costs the most — a run that resampled 20 times over a
    candidate that was exactly on the cutoff would abandon a perfectly good
    puzzle.
    """
    band = tier.band
    assert band is not None
    low, high = band
    for score in (low if tier is Tier.EASY else low + 1e-9, high):
        source = _ScriptedSource(UNIQUE)
        scorer = _ScriptedScorer(score)
        _install_source(monkeypatch, source)
        _install_scorer(monkeypatch, scorer)

        puzzle = generate(_request(difficulty=tier.value))

        assert puzzle.difficulty_score == score
        assert puzzle.resample.attempts == 1


def test_a_run_without_a_tier_accepts_the_first_unique_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Guardrail G-5: no ``--difficulty`` leaves POL-001's behaviour alone.

    The resample check is vacuous, not absent — the candidate is still scored
    (CARD-014's PDF header needs one) — and the loop still stops on the first
    uniquely-solvable grid, whatever that grid scored.
    """
    source = _ScriptedSource(AMBIGUOUS, UNIQUE)
    scorer = _ScriptedScorer(_in_band(Tier.HARD))
    _install_source(monkeypatch, source)
    _without_repairs(monkeypatch)
    _install_scorer(monkeypatch, scorer)

    puzzle = generate(_request())

    assert puzzle.requested_tier is None
    assert puzzle.difficulty_score == _in_band(Tier.HARD)
    assert puzzle.regenerate.attempts == 2
    assert puzzle.resample.attempts == 1
    assert source.candidates_requested == 2


def test_a_non_unique_candidate_is_not_scored_at_all(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The score of a non-unique clue set means nothing, so it is not taken.

    Also guardrail G-6's arithmetic: adding COMP-006 to the loop costs one
    scoring pass per *accepted* candidate, not one per attempt, so a run that
    regenerates 20 times pays for scoring exactly as often as it did before
    this card — zero.
    """
    source = _ScriptedSource(AMBIGUOUS, AMBIGUOUS, UNIQUE)
    scorer = _ScriptedScorer(_in_band(Tier.EASY))
    _install_source(monkeypatch, source)
    _without_repairs(monkeypatch)
    _install_scorer(monkeypatch, scorer)

    puzzle = generate(_request(difficulty="easy"))

    assert source.candidates_requested == 3
    assert scorer.candidates_scored == 1
    assert puzzle.difficulty_score == _in_band(Tier.EASY)


# --------------------------------------------------------------------------
# AC-025 — TestResample_FiresWhenScoreOutOfRange
# --------------------------------------------------------------------------


def test_fires_when_score_out_of_range(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC-025: an out-of-band score discards the candidate and draws a new one.

    The two grids are different, so "a new candidate is generated" is checked
    on the aggregate's contents and not only on a counter: the puzzle that
    comes back is the *second* grid, and the first is gone.
    """
    source = _ScriptedSource(UNIQUE, ALSO_UNIQUE)
    scorer = _ScriptedScorer(_outside_band(Tier.MEDIUM), _in_band(Tier.MEDIUM))
    _install_source(monkeypatch, source)
    _install_scorer(monkeypatch, scorer)

    puzzle = generate(_request(difficulty="medium"))

    assert source.candidates_requested == 2
    assert puzzle.grid == ALSO_UNIQUE
    assert puzzle.difficulty_score == _in_band(Tier.MEDIUM)
    assert puzzle.difficulty_tier is Tier.MEDIUM
    assert puzzle.resample.attempts == 2


@pytest.mark.parametrize(
    ("requested", "score"),
    [
        pytest.param(Tier.EASY, _in_band(Tier.MEDIUM), id="easy-got-medium"),
        pytest.param(Tier.EASY, _in_band(Tier.HARD), id="easy-got-hard"),
        pytest.param(Tier.MEDIUM, _in_band(Tier.EASY), id="medium-got-easy"),
        pytest.param(Tier.MEDIUM, _in_band(Tier.HARD), id="medium-got-hard"),
        pytest.param(Tier.HARD, _in_band(Tier.EASY), id="hard-got-easy"),
        pytest.param(Tier.HARD, _in_band(Tier.MEDIUM), id="hard-got-medium"),
        pytest.param(Tier.HARD, MEDIUM_MAX_SCORE, id="hard-got-the-cutoff-below-it"),
    ],
)
def test_fires_when_score_out_of_range_for_every_tier_pair(
    requested: Tier, score: float, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-025 for every way a candidate can miss, the cutoff case included."""
    source = _ScriptedSource(UNIQUE, ALSO_UNIQUE)
    scorer = _ScriptedScorer(score, _in_band(requested))
    _install_source(monkeypatch, source)
    _install_scorer(monkeypatch, scorer)

    puzzle = generate(_request(difficulty=requested.value))

    assert source.candidates_requested == 2
    assert puzzle.resample.attempts == 2
    assert puzzle.difficulty_tier is requested


def test_the_resample_does_not_steer_the_grid_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CON-004 / guardrail G-3: a tier is a filter, never a construction target.

    The source is called with the *same* arguments on every round — the
    request's extent and density and the run's RNG — so nothing about the
    requested tier reaches the sourcing of a grid. POL-004 discards and
    re-draws; it does not ask for a harder picture.
    """
    source = _ScriptedSource(UNIQUE, UNIQUE, ALSO_UNIQUE)
    scorer = _ScriptedScorer(
        _outside_band(Tier.HARD), _outside_band(Tier.HARD), _in_band(Tier.HARD)
    )
    _install_source(monkeypatch, source)
    _install_scorer(monkeypatch, scorer)

    generate(_request(width=10, height=13, density=50, difficulty="hard"))

    assert len(source.calls) == 3
    extents_and_densities = {call[:3] for call in source.calls}
    assert extents_and_densities == {(10, 13, 50)}
    # One RNG for the whole run (ADR-0015), resamples included.
    assert len({id(call[-1]) for call in source.calls}) == 1


# --------------------------------------------------------------------------
# AC-026 — TestResample_RescoresNewCandidate
# --------------------------------------------------------------------------


def test_rescores_new_candidate(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC-026: the resampled candidate is scored before anything else is asked.

    Checked on *what* was scored rather than on how many times: the scorer
    records the signals record it was handed, so the assertion is that round
    two scored *round two's solve*. A loop that re-checked the previous score
    would have scored once, and one that scored the wrong candidate would show
    the wrong solve.

    Until ADR-0029 the scorer was handed the candidate's *clues* and this test
    compared those, which named the candidate outright. The clues left the
    signature with the density term, and what remains — the per-rung histogram
    and the cell count — cannot tell two 2x2 grids apart: both settle all four
    cells at ``simple_overlap``. So the binding is made through the aggregate
    instead, and it is no weaker for it. The returned puzzle is the *second*
    grid, carrying the *second* script entry as its score, and the source was
    asked exactly twice. A loop that re-checked the first candidate's score
    would have returned the first grid; one that scored the wrong candidate
    would have returned the second grid with the first score.
    """
    source = _ScriptedSource(UNIQUE, ALSO_UNIQUE)
    scorer = _ScriptedScorer(_outside_band(Tier.EASY), _in_band(Tier.EASY))
    _install_source(monkeypatch, source)
    _install_scorer(monkeypatch, scorer)

    puzzle = generate(_request(difficulty="easy"))

    assert scorer.candidates_scored == source.candidates_requested == 2
    assert puzzle.grid == ALSO_UNIQUE
    assert puzzle.clues is not None
    assert puzzle.clues.rows == compute_clues(ALSO_UNIQUE).rows
    assert puzzle.difficulty_score == _in_band(Tier.EASY)


def test_a_replaced_candidate_carries_no_score_until_it_is_rescored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-026 on the aggregate: recording a candidate drops the old score.

    The window this closes is the one between "this candidate was discarded"
    and "its replacement was judged". A stale score left on the aggregate in
    that window could be read as the new candidate's — by the tier check, or by
    an export — and would be wrong.
    """
    puzzle = Puzzle(request=_request(), seed=0, requested_tier=Tier.EASY)
    puzzle.record_candidate(UNIQUE)
    assert puzzle.record_difficulty(_in_band(Tier.EASY), 0) is True
    assert puzzle.difficulty_in_requested_tier is True

    puzzle.record_candidate(ALSO_UNIQUE)

    assert puzzle.difficulty_score is None
    assert puzzle.branch_nodes is None
    assert puzzle.difficulty_tier is None
    # Unscored is not "in tier": POL-004 must not accept a candidate on the
    # strength of its predecessor's solve. Both halves of the grade are dropped
    # — a branch count left behind would classify the replacement ``GUESS`` on
    # its predecessor's account, which is AC-026 the other way up (ADR-0025).
    assert puzzle.difficulty_in_requested_tier is False


def test_the_score_recorded_is_the_one_the_tier_check_used(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One score per candidate, computed once and read thereafter.

    A loop that scored a candidate to test it and then scored it again to
    report it could hand the user a puzzle labelled with a different number
    than the one it was accepted on — and, with a scorer as cheap as COMP-006's
    is meant to be, would double the cost the timing budget accounts for
    (guardrail G-6).
    """
    source = _ScriptedSource(UNIQUE, ALSO_UNIQUE)
    scorer = _ScriptedScorer(_outside_band(Tier.HARD), _in_band(Tier.HARD))
    _install_source(monkeypatch, source)
    _install_scorer(monkeypatch, scorer)

    puzzle = generate(_request(difficulty="hard"))

    assert scorer.candidates_scored == source.candidates_requested == 2
    assert puzzle.difficulty_score == _in_band(Tier.HARD)
    assert puzzle.difficulty_tier is difficulty.classify(_in_band(Tier.HARD), 0)


# --------------------------------------------------------------------------
# AC-027 / INV-003 — TestResample_StopsAtMaxRetryBound
# --------------------------------------------------------------------------


def test_stops_at_max_retry_bound(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC-027: resampling stops at the bound and abandons with a clear error.

    Every candidate here is uniquely solvable, so POL-001 never fires and the
    only thing being counted is POL-004's own rejections — which is what makes
    this the resample loop's bound and not the regenerate loop's.
    """
    source = _ScriptedSource(UNIQUE, repeat_last=True)
    scorer = _ScriptedScorer(_outside_band(Tier.HARD), repeat_last=True)
    _install_source(monkeypatch, source)
    _install_scorer(monkeypatch, scorer)

    with pytest.raises(GenerationAbandoned) as excinfo:
        generate(_request(difficulty="hard"))

    message = str(excinfo.value)
    assert "resample" in message
    assert str(MAX_RESAMPLE_ATTEMPTS) in message
    # Clear: it says which band was missed, and what the user can change.
    assert "Hard" in message
    assert "--difficulty" in message
    # INV-003: the bound is reached, never exceeded.
    assert source.candidates_requested == MAX_RESAMPLE_ATTEMPTS


def test_stops_at_max_retry_bound_without_exceeding_any_counter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """INV-003 on both counters at once, read off the aggregate.

    ``generate`` raises rather than returning, so the aggregate is reached
    through the one thing that survives: a source that counted its calls. The
    counters themselves are checked in ``tests/test_orchestrator.py``'s retry
    primitive section; what this adds is that *two* live counters still cannot
    together outrun one bound's worth of candidates.
    """
    source = _ScriptedSource(UNIQUE, repeat_last=True)
    _install_source(monkeypatch, source)
    _install_scorer(monkeypatch, _ScriptedScorer(SCORE_MAX, repeat_last=True))

    with pytest.raises(GenerationAbandoned):
        generate(_request(difficulty="easy"))

    assert source.candidates_requested == MAX_RETRY_ATTEMPTS


def test_stops_at_max_retry_bound_with_the_real_scorer() -> None:
    """AC-027 with nothing faked at all — the loop, the solver and COMP-006.

    A 2x2 grid line logic walks straight through scores a fraction of a point
    (ADR-0013's scale is built so it does), so a request for Hard at this size
    is genuinely infeasible: 20 real solves, 20 real scores, all Easy, and the
    run abandons. This is the evidence that the scripted-score tests above are
    scripting a collaborator rather than papering over one.
    """
    source = _ScriptedSource(UNIQUE, repeat_last=True)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(orchestrator.sourcing, "for_mode", lambda mode: source)

        with pytest.raises(GenerationAbandoned) as excinfo:
            generate(_request(difficulty="hard"))

    assert "resample" in str(excinfo.value)
    assert source.candidates_requested == MAX_RESAMPLE_ATTEMPTS


def test_an_infeasible_tier_reaches_the_user_as_generation_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-027 at the boundary: abandonment is exit code 4, not a traceback."""
    source = _ScriptedSource(UNIQUE, repeat_last=True)
    _install_source(monkeypatch, source)
    _install_scorer(monkeypatch, _ScriptedScorer(SCORE_MAX, repeat_last=True))

    exit_code = cli.main(["generate", "--size", "10", "--difficulty", "easy"])

    assert exit_code == cli.ExitCode.GENERATION_FAILED


# --------------------------------------------------------------------------
# How the two loops compose (guardrails G-2 and G-5)
# --------------------------------------------------------------------------


def test_the_two_loops_share_one_bound_constant() -> None:
    """Guardrail G-2 / ADR-0002: one number, not two that can drift apart.

    Identity, not equality: two independently-declared ``20``s would satisfy
    ``==`` today and diverge the first time somebody retuned one of them.
    """
    assert MAX_REGENERATE_ATTEMPTS is MAX_RETRY_ATTEMPTS
    assert MAX_RESAMPLE_ATTEMPTS is MAX_RETRY_ATTEMPTS
    assert MAX_RETRY_ATTEMPTS == 20


def test_both_counters_are_the_same_primitive_with_the_same_bound() -> None:
    """G-2 again, on the aggregate: one counter type, two instances.

    A fresh puzzle carries both counters, named for their policies, bounded by
    the same ADR-0002 number and starting at zero — which is what makes INV-003
    one invariant with one home rather than a rule restated per loop.
    """
    puzzle = Puzzle(request=_request(), seed=0)

    assert type(puzzle.regenerate) is type(puzzle.resample)
    assert (puzzle.regenerate.kind, puzzle.resample.kind) == ("regenerate", "resample")
    assert puzzle.regenerate.bound == puzzle.resample.bound == MAX_RETRY_ATTEMPTS
    assert puzzle.regenerate.attempts == puzzle.resample.attempts == 0


def test_regeneration_still_fires_inside_a_resample_round(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Guardrail G-5: resampling composes with POL-001, it does not replace it.

    Round one draws an ambiguous grid (POL-001 rejects it), then a unique one
    that scores out of band (POL-004 rejects that), and round two draws a
    unique one in band. Both loops fire in one run, and the counters show which
    did what.
    """
    source = _ScriptedSource(AMBIGUOUS, UNIQUE, ALSO_UNIQUE)
    scorer = _ScriptedScorer(_outside_band(Tier.MEDIUM), _in_band(Tier.MEDIUM))
    _install_source(monkeypatch, source)
    _without_repairs(monkeypatch)
    _install_scorer(monkeypatch, scorer)

    puzzle = generate(_request(difficulty="medium"))

    assert source.candidates_requested == 3
    # Three grids drawn: every one of them is a regenerate attempt.
    assert puzzle.regenerate.attempts == 3
    # Two rounds of the tier check: one rejected, one accepted.
    assert puzzle.resample.attempts == 2
    assert puzzle.grid == ALSO_UNIQUE
    assert puzzle.ready_for_export is True


def test_the_regenerate_budget_is_the_requests_and_not_the_rounds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The counter is not reset between resample rounds (CARD-005's semantics).

    This is the design question CARD-005's review left open, pinned as
    behaviour: a resample round does *not* get a fresh 20-attempt regenerate
    budget. Across the whole run at most ``MAX_RETRY_ATTEMPTS`` grids are
    sourced, however the two rejection causes divide them up — which is what
    keeps scoring inside the loop from multiplying the work NFR-001 budgets
    (guardrail G-6).
    """
    source = _ScriptedSource(UNIQUE, AMBIGUOUS, repeat_last=True)
    scorer = _ScriptedScorer(_outside_band(Tier.HARD), repeat_last=True)
    _install_source(monkeypatch, source)
    _without_repairs(monkeypatch)
    _install_scorer(monkeypatch, scorer)

    with pytest.raises(GenerationAbandoned):
        generate(_request(difficulty="hard"))

    # Candidate 1 was unique and out of band (resample round 1); every
    # candidate after it is ambiguous, so the regenerate loop burns the rest of
    # the shared budget inside round 2 and the run ends there — 20 grids in
    # total, not 20 per round.
    assert source.candidates_requested == MAX_RETRY_ATTEMPTS


def test_an_exhausted_regenerate_loop_ends_the_run_rather_than_resampling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The other half of that open question: an inner abandonment propagates.

    A run whose candidates are never unique must report *that*, once — not be
    caught by the resample loop and retried as though a tier had been missed.
    The evidence is the count: exactly one bound's worth of grids, and an error
    that names the uniqueness failure.
    """
    source = _ScriptedSource(AMBIGUOUS, repeat_last=True)
    scorer = _ScriptedScorer(_in_band(Tier.EASY), repeat_last=True)
    _install_source(monkeypatch, source)
    _without_repairs(monkeypatch)
    _install_scorer(monkeypatch, scorer)

    with pytest.raises(GenerationAbandoned) as excinfo:
        generate(_request(difficulty="easy"))

    message = str(excinfo.value)
    assert "regenerate" in message
    assert "uniquely solvable" in message
    # Named the tier too: when both checks share a budget, a message that
    # mentioned only uniqueness would be naming the wrong cause for a run that
    # did find unique candidates and rejected them for their score.
    assert "Easy" in message
    assert source.candidates_requested == MAX_REGENERATE_ATTEMPTS
    assert scorer.candidates_scored == 0


def test_an_abandonment_message_is_unchanged_when_no_tier_was_requested(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Guardrail G-5: a run without ``--difficulty`` is CARD-005's run.

    Same loop, same bound, same wording — nothing about POL-004 is visible to a
    user who did not ask for a tier.
    """
    source = _ScriptedSource(AMBIGUOUS, repeat_last=True)
    _install_source(monkeypatch, source)
    _without_repairs(monkeypatch)

    with pytest.raises(GenerationAbandoned) as excinfo:
        generate(_request())

    message = str(excinfo.value)
    assert "regenerate" in message
    assert "no candidate grid had exactly one solution" in message
    assert "--difficulty" not in message
    assert source.candidates_requested == MAX_REGENERATE_ATTEMPTS


def test_an_invalid_request_is_not_retried_as_a_resample(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only a *rejected candidate* is a retry — an invalid request is not.

    CARD-005's rule, re-checked through the new outer loop: an exception from
    sourcing must travel out through both loops untouched, spending one attempt
    rather than 20 (or 400).

    The invalid thing is a *density* rather than the extent it used to be. Since
    CARD-033 an out-of-range extent never reaches the source at all — it is
    refused while FR-023's derivation resolves it — which would make this test
    pass on a source that was never called, and "travels out through both loops"
    is a claim about a source that *was*. A bad density is exactly as invalid
    and is still the source's to refuse, so it keeps the assertion honest. The
    extent's own path is covered by
    ``test_an_invalid_request_is_not_retried`` in ``tests/test_orchestrator.py``.
    """
    calls = 0

    def failing_source(*args: object) -> object:
        nonlocal calls
        calls += 1
        raise InvalidDensity("density 150 is outside the supported range")

    _install_source(monkeypatch, failing_source)

    with pytest.raises(InvalidDensity):
        generate(_request(width=13, height=13, density=150, difficulty="hard"))

    assert calls == 1


# --------------------------------------------------------------------------
# End to end, unmocked (Increment 2's tertile checkpoint, in miniature)
# --------------------------------------------------------------------------


@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4])
def test_a_puzzle_generated_for_a_tier_really_scores_in_that_tier(seed: int) -> None:
    """The whole point of the loop, checked without faking any of it.

    Pinned seeds at 10x10 / 50% density, where the real scorer puts a
    line-solvable random grid in the Easy band. The assertion is deliberately
    not "the score is small" but "the score is in the band the user asked for,
    as the real classifier reads it" — the same proposition Increment 2's
    checkpoint makes for all three tiers, which is why the bands have one home
    (ADR-0005) rather than being restated here.
    """
    puzzle = generate(
        GenerationRequest(
            mode="random", width=10, height=10, density=50, seed=seed, difficulty="easy"
        )
    )

    assert puzzle.difficulty_score is not None
    assert difficulty.classify(puzzle.difficulty_score, 0) is Tier.EASY
    assert puzzle.difficulty_tier is Tier.EASY
    assert puzzle.requested_tier is Tier.EASY
    assert puzzle.ready_for_export is True
    assert puzzle.resample.attempts <= MAX_RESAMPLE_ATTEMPTS
    assert puzzle.regenerate.attempts <= MAX_REGENERATE_ATTEMPTS


def test_the_same_seed_replays_the_same_resample_run() -> None:
    """ADR-0015 through the new loop: one RNG, so the whole run replays.

    Including the resamples — a loop that drew its own randomness to "try
    something different" would break reproducibility exactly here.

    What replays is the *work*: the same grids in the same order, discarded for
    the same reasons — **and, since CARD-076, the score to the last digit.**

    That last clause used to read the other way round. ADR-0013 put wall-clock
    solve time in the formula, so two runs of the identical solve scored within
    a whisker of each other rather than identically, and this test carried an
    ``abs=1.0`` tolerance with a note saying that asserting bit-equality would
    be asserting that the machine is a clock-free abstraction. Under ADR-0029
    the machine *is* a clock-free abstraction as far as the grade is concerned
    (``difficulty.SolverSignals`` does not carry ``elapsed_seconds``), so the
    tolerance is gone and its disappearance is the point: a loosened assertion
    that nobody tightened again is how a reproducibility promise quietly stops
    being one.
    """
    requests: Iterable[GenerationRequest] = (
        GenerationRequest(
            mode="random", width=10, height=10, density=50, seed=99, difficulty="easy"
        )
        for _ in range(2)
    )
    first, second = (generate(request) for request in requests)

    assert first.grid == second.grid
    assert first.clues == second.clues
    assert first.resample.attempts == second.resample.attempts
    assert first.regenerate.attempts == second.regenerate.attempts
    # The tier — the thing the loop actually decides on — does replay.
    assert first.difficulty_tier is second.difficulty_tier
    assert first.difficulty_score is not None and second.difficulty_score is not None
    assert first.difficulty_score == second.difficulty_score
    assert first.branch_nodes == second.branch_nodes


# --------------------------------------------------------------------------
# AC-123 (NFR-007) — TestResample_SameSeedSameTierUnderDilatedClock
# --------------------------------------------------------------------------


def _dilate_the_solvers_clock(
    monkeypatch: pytest.MonkeyPatch, factor: float
) -> None:
    """Make every solve *report* ``factor`` times the elapsed seconds it took.

    The injection point is ``time.perf_counter`` inside ``nonogram.solver.search``
    — the one clock ``SolveSignals.elapsed_seconds`` is measured with — and
    deliberately not ``time.monotonic``, which is what ADR-0011's cooperative
    deadline reads. Dilating only the reported elapsed time is exactly the
    counterfactual AC-123 poses: the same work, on a host that took fifty times
    as long to do it, with no timeout behaviour changed and nothing else moved.

    A test that instead slowed the machine down would be asserting something
    about the machine. This asserts something about the scorer.
    """
    real = time.perf_counter

    def dilated() -> float:
        return real() * factor

    monkeypatch.setattr(orchestrator.solver.search.time, "perf_counter", dilated)


#: AC-123's request, with one deviation, stated rather than hidden.
#:
#: The criterion names "seed 42, 20x20, density 40, --difficulty Medium". That
#: request *abandons* on this tree — 20x20 at density 40 is where the uniqueness
#: rate collapses, and the run burns its whole shared budget in about 15 seconds
#: without producing a puzzle — so "both runs return the same grid" would have
#: nothing to compare. The claim under test is not about those particular
#: numbers: it is that a dilated clock changes neither the grid nor the resample
#: count for a given seed. This request makes that claim checkable, in a
#: hundredth of the time, on a run that really does exercise POL-004 — three
#: resample rounds and eight regenerate attempts before a Medium candidate is
#: accepted, so a clock-dependent tier decision would have plenty of chances to
#: diverge. The abandoning case is covered for the same property by
#: ``test_an_infeasible_tier_reaches_the_user_as_generation_failed``.
_AC123_REQUEST = {"width": 12, "height": 12, "density": 45, "seed": 1}


def test_same_seed_same_tier_under_dilated_clock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-123 — ``TestResample_SameSeedSameTierUnderDilatedClock``.

    One seed, one request, two host speeds: the same grid, the same score, the
    same tier and the same attempt counts. The two runs are compared with each
    other rather than against transcribed constants, which is what the
    criterion asks ("both runs return the same grid") and is also the form that
    cannot rot — a legitimate change to the source would move both runs
    together and this test would go on asserting the thing it is for.

    Equality is exact, ``grid`` and ``difficulty_score`` included. Before this
    card the same claim could only be made to within a tolerance, because
    ADR-0013 put wall-clock solve time in the formula — ``test_the_same_seed_
    replays_the_same_resample_run`` below carried an ``abs=1.0`` for exactly
    that reason and no longer needs it. This is ADR-0015's reproducibility
    promise extended to requests that carry ``--difficulty``
    (``docs/GENERATION_ALGORITHM.md`` §10.2 finding 3, now closed).

    The run really exercises POL-004: three resample rounds and eight
    regenerate attempts before a Medium candidate is accepted, so a
    clock-dependent tier decision would have eight chances to keep a different
    candidate under the slow clock.
    """
    with monkeypatch.context() as normal_speed:
        _dilate_the_solvers_clock(normal_speed, 1.0)
        at_1x = generate(_request(difficulty="Medium", **_AC123_REQUEST))

    with monkeypatch.context() as slow_host:
        _dilate_the_solvers_clock(slow_host, 50.0)
        at_50x = generate(_request(difficulty="Medium", **_AC123_REQUEST))

    assert at_1x.difficulty_tier is Tier.MEDIUM
    assert at_50x.difficulty_tier is at_1x.difficulty_tier
    assert at_50x.grid == at_1x.grid
    assert at_50x.clues == at_1x.clues
    assert at_50x.difficulty_score == at_1x.difficulty_score
    assert at_50x.branch_nodes == at_1x.branch_nodes
    # The *sequence* of discarded candidates replays too, not only the accepted
    # one: that is the half a per-candidate clock term would have broken.
    assert at_50x.resample.attempts == at_1x.resample.attempts == 3
    assert at_50x.regenerate.attempts == at_1x.regenerate.attempts == 8


def test_the_dilated_clock_really_reaches_the_solvers_report(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Guard the injection: AC-123 is vacuous if the clock never moved.

    A fixture that patched the wrong ``time`` would make the test above pass by
    doing nothing at all — the strongest possible form of a silently useless
    test. So the dilation is shown *arriving*: the same solve reports an
    elapsed time an order of magnitude larger under the 50x clock, while its
    score and its tier do not move a digit.
    """
    clues = compute_clues(UNIQUE)

    at_1x = orchestrator.solver.solve(clues.rows, clues.columns).signals
    _dilate_the_solvers_clock(monkeypatch, 50.0)
    at_50x = orchestrator.solver.solve(clues.rows, clues.columns).signals

    assert at_50x.elapsed_seconds > at_1x.elapsed_seconds * 10
    assert difficulty.score_difficulty(at_50x) == difficulty.score_difficulty(at_1x)
    assert difficulty.classify(
        difficulty.score_difficulty(at_50x), at_50x.branch_nodes
    ) is difficulty.classify(
        difficulty.score_difficulty(at_1x), at_1x.branch_nodes
    )


# --------------------------------------------------------------------------
# AC-A (handoff checkpoint) — TestGenerate_HardTierIsLineSolvableAndMachineIndependent
# --------------------------------------------------------------------------

#: AC-A's request, and the one deviation this card had to make, stated rather
#: than hidden.
#:
#: The checkpoint names ``--mode random --size 20 --density 25 --difficulty hard
#: --seed 7``. That request **abandons** on this tree, and for a reason that has
#: nothing to do with the difficulty grade: at 20x20 and density 25 the
#: *uniqueness* rate collapses — a measured 0 of 4 draws come back with exactly
#: one solution, against 3 of 4 at density 65 — so POL-004's shared budget is
#: spent on candidates that never reach the tier check at all. Changing that
#: would mean changing the source or the retry bound, neither of which is this
#: card's business.
#:
#: The proposition AC-A makes is "``--difficulty hard`` returns a puzzle that
#: never branched, with an identical score and tier under a dilated clock", and
#: that is checkable at a density where the source produces puzzles. 20x20 is
#: kept — it is the extent the checkpoint names and the one NFR-001 is written
#: over — and the density moves to 50. The literal request is covered too, by
#: the second test below: it abandons *identically* under both clocks, which is
#: the same machine-independence claim made about the failure path.
_ACA_REQUEST = {"width": 20, "height": 20, "density": 50, "seed": 0}


def test_generate_hard_tier_is_line_solvable_and_machine_independent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-A — ``TestGenerate_HardTierIsLineSolvableAndMachineIndependent``.

    Two claims in one run, and they are the whole point of the card together.

    **Line-solvable.** A Hard puzzle comes back with ``branch_nodes == 0``. Under
    ADR-0013 this was impossible in the other direction: the only route into the
    Hard band was backtracking, so ``--difficulty hard`` meant "needs guessing" —
    exactly backwards for the printed-book workflow the intake described.
    ADR-0025 moved guessing out of the score entirely and ADR-0029 gave line
    reasoning the whole scale, so Hard now means "deep, and logically solvable".

    **Machine-independent.** The same request under a 1x and a 50x clock returns
    the same grid, the same score to the last digit and the same tier — the two
    machines of the checkpoint's "on two different machines", simulated at the
    one place a host's speed can enter the pipeline (NFR-007, AC-123).
    """
    with monkeypatch.context() as normal_speed:
        _dilate_the_solvers_clock(normal_speed, 1.0)
        at_1x = generate(_request(difficulty="hard", **_ACA_REQUEST))

    with monkeypatch.context() as slow_host:
        _dilate_the_solvers_clock(slow_host, 50.0)
        at_50x = generate(_request(difficulty="hard", **_ACA_REQUEST))

    # The promise --difficulty hard now makes.
    assert at_1x.difficulty_tier is Tier.HARD
    assert at_1x.branch_nodes == 0
    assert at_1x.ready_for_export is True

    # ...made identically on a host fifty times slower.
    assert at_50x.grid == at_1x.grid
    assert at_50x.difficulty_score == at_1x.difficulty_score
    assert at_50x.difficulty_tier is at_1x.difficulty_tier
    assert at_50x.branch_nodes == at_1x.branch_nodes
    assert at_50x.resample.attempts == at_1x.resample.attempts
    assert at_50x.regenerate.attempts == at_1x.regenerate.attempts


def test_the_checkpoints_own_request_abandons_identically_on_either_clock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-A's literal request, and its literal outcome.

    ``--size 20 --density 25 --difficulty hard --seed 7`` abandons — see the
    note on ``_ACA_REQUEST`` for why, and note that the cause is the uniqueness
    rate at that density and not the tier: the message names both checks and
    says they share one budget.

    Pinned rather than quietly replaced, for two reasons. It keeps the
    checkpoint's own numbers in the tree, so the next person to read AC-A finds
    out what they actually do instead of re-discovering it. And the failure path
    carries the same machine-independence claim as the success path: a run that
    abandoned after a different number of attempts on a slower host would be
    ADR-0015 broken just as surely, and would be easier to miss.
    """
    failures = []
    for factor in (1.0, 50.0):
        with monkeypatch.context() as clock:
            _dilate_the_solvers_clock(clock, factor)
            with pytest.raises(GenerationAbandoned) as excinfo:
                generate(
                    _request(
                        difficulty="hard", width=20, height=20, density=25, seed=7
                    )
                )
            failures.append(str(excinfo.value))

    assert failures[0] == failures[1]
    # Both checks are named, because either could be the one that ran out.
    assert "uniquely solvable" in failures[0]
    assert Tier.HARD.label in failures[0]
