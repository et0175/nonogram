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
the tier classification is always the real ``difficulty.tier_for_score``.

*Pinned-seed* tests run the whole pipeline unmocked, scorer included, and are
the evidence that the composition works end to end.

The bands themselves — which score is Easy, which is Hard — are
``tests/test_difficulty_tiers.py``; this module is about what the loop does
with the answer.
"""

from __future__ import annotations

import random
from collections.abc import Callable, Iterable

import pytest

from nonogram import cli, difficulty, orchestrator
from nonogram.difficulty import MEDIUM_MAX_SCORE, SCORE_MAX, Tier
from nonogram.errors import GenerationAbandoned, SizeOutOfRange
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

    Records the clues it was asked about, so a test can show *which* candidate
    each score was attached to — which is how AC-026 ("the new candidate is
    re-scored") is checked as something other than a call count.
    """

    def __init__(self, *scores: float, repeat_last: bool = False) -> None:
        self._scores = list(scores)
        self._repeat_last = repeat_last
        self.scored: list[tuple[tuple[int, ...], ...]] = []

    def __call__(self, signals: object, clues: tuple[tuple[int, ...], ...]) -> float:
        self.scored.append(clues)
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
    ``tier_for_score`` still classifies whatever this returns.
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


def _in_band(tier: Tier) -> float:
    """A score comfortably inside ``tier``'s band."""
    low, high = tier.band
    return (low + high) / 2


def _outside_band(tier: Tier) -> float:
    """A score in some *other* tier's band."""
    other = next(candidate for candidate in Tier if candidate is not tier)
    return _in_band(other)


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


@pytest.mark.parametrize("tier", list(Tier))
def test_accepts_candidate_in_range_at_either_end_of_the_band(
    tier: Tier, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-024 at the boundaries: a cutoff score is *in* its own band.

    The band edges are where an off-by-one in the comparison would live, and
    where a wrong answer costs the most — a run that resampled 20 times over a
    candidate that was exactly on the cutoff would abandon a perfectly good
    puzzle.
    """
    low, high = tier.band
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
    records the clues it was handed, so the assertion is that round two scored
    the clues of round two's grid. A loop that re-checked the previous score
    would have scored once, and one that scored the wrong candidate would show
    the wrong clues.
    """
    source = _ScriptedSource(UNIQUE, ALSO_UNIQUE)
    scorer = _ScriptedScorer(_outside_band(Tier.EASY), _in_band(Tier.EASY))
    _install_source(monkeypatch, source)
    _install_scorer(monkeypatch, scorer)

    puzzle = generate(_request(difficulty="easy"))

    assert scorer.candidates_scored == 2
    assert scorer.scored[0] != scorer.scored[1]
    # The second score is the second grid's, and it is the one that was judged.
    assert puzzle.clues is not None
    assert scorer.scored[1] == puzzle.clues.rows
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
    assert puzzle.record_difficulty(_in_band(Tier.EASY)) is True
    assert puzzle.difficulty_in_requested_tier is True

    puzzle.record_candidate(ALSO_UNIQUE)

    assert puzzle.difficulty_score is None
    assert puzzle.difficulty_tier is None
    # Unscored is not "in tier": POL-004 must not accept a candidate on the
    # strength of its predecessor's score.
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
    assert puzzle.difficulty_tier is difficulty.tier_for_score(_in_band(Tier.HARD))


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
    """
    calls = 0

    def failing_source(*args: object) -> object:
        nonlocal calls
        calls += 1
        raise SizeOutOfRange("size 3 is outside the supported range")

    _install_source(monkeypatch, failing_source)

    with pytest.raises(SizeOutOfRange):
        generate(_request(width=3, height=3, difficulty="hard"))

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
    assert Tier.EASY.contains(puzzle.difficulty_score)
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
    the same reasons. Not the score to the last digit — ADR-0013 puts wall-clock
    solve time in the formula, weighted lightest of the three effort terms
    precisely because "it is the only signal that varies with the machine", so
    two runs of the identical solve score within a whisker of each other rather
    than identically. Asserting bit-equality here would be asserting that the
    machine is a clock-free abstraction, and would fail on a busy laptop rather
    than on a regression.
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
    assert first.difficulty_score == pytest.approx(second.difficulty_score, abs=1.0)
