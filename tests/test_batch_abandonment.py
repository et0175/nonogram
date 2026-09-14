"""CARD-083 — a batch survives a candidate it had to abandon.

``orchestrator.generate_batch`` called ``generate`` in a loop with nothing
around it, so the first ``GenerationAbandoned`` ended the whole batch. At the
measured abandon rate that is not a rare event: 4 of 200 candidates at 25x25
and density 50 (what ``generate_batch`` hardcodes), so a 50-puzzle request lost
everything roughly a third of the time, after doing all the work.

A skipped candidate is now a shorter list, and the batch still fails loudly in
the two cases where "shorter" is the wrong answer: nothing was produced at all,
or :data:`MAX_CONSECUTIVE_ABANDONMENTS` candidates failed back-to-back, which
says the parameters are infeasible rather than unlucky.

``generate`` is scripted throughout. What is under test is the loop's reaction
to an outcome, not the pipeline that produces it — and a real 25x25 corpus
large enough to hit abandonment on demand would cost minutes per assertion.
The premise the scripting stands on (that ``generate`` raises
``GenerationAbandoned`` for a candidate it cannot make unique) is
``TestRegenerate_StopsAtMaxRetryBound``'s, not this file's.
"""

from __future__ import annotations

import pytest

from nonogram import orchestrator
from nonogram.errors import GenerationAbandoned, SolverTimeout
from nonogram.orchestrator import (
    MAX_CONSECUTIVE_ABANDONMENTS,
    MAX_RETRY_ATTEMPTS,
    GenerationRequest,
    Puzzle,
)

#: 2x2, one solution. Small enough that scripting is instant, real enough that
#: ``Puzzle`` accepts it through the same calls the pipeline makes.
_GRID = [[True, True], [False, True]]


def _puzzle(request: GenerationRequest) -> Puzzle:
    puzzle = Puzzle(request=request, seed=0)
    puzzle.record_candidate(_GRID)
    puzzle.confirm_uniqueness(1)
    puzzle.record_difficulty(10.0, 0)
    return puzzle


def _script(monkeypatch: pytest.MonkeyPatch, outcomes: list[object]) -> list[str]:
    """Make the n-th ``generate`` call do ``outcomes[n]``.

    An entry is either the string ``"ok"`` or an exception instance to raise.
    Returns the list the calls append to, so a test can assert how many slots
    were actually attempted — which is the only way to see that an early exit
    stopped the loop rather than merely reporting after it.
    """
    attempted: list[str] = []

    def fake_generate(request: GenerationRequest) -> Puzzle:
        outcome = outcomes[len(attempted)]
        attempted.append("attempt")
        if isinstance(outcome, BaseException):
            raise outcome
        return _puzzle(request)

    monkeypatch.setattr(orchestrator, "generate", fake_generate)
    return attempted


def _abandonment(n: int = MAX_RETRY_ATTEMPTS) -> GenerationAbandoned:
    return GenerationAbandoned(f"abandoned after {n} regenerate attempts")


def _batch(count: int):
    return orchestrator.generate_batch(count=count, sizes=[10], source="random")


# --------------------------------------------------------------------------
# The thing the card was opened for
# --------------------------------------------------------------------------


class TestBatch_SurvivesAnAbandonedCandidate:
    def test_one_bad_draw_no_longer_costs_the_batch(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _script(monkeypatch, ["ok", "ok", _abandonment(), "ok", "ok"])

        puzzles = _batch(5)

        assert len(puzzles) == 4

    def test_every_remaining_slot_is_still_attempted(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Skipping is not stopping: the loop still runs ``count`` times."""
        attempted = _script(monkeypatch, ["ok", _abandonment(), "ok", "ok", "ok"])

        _batch(5)

        assert len(attempted) == 5

    @pytest.mark.parametrize("slot", [0, 2, 4])
    def test_the_position_of_the_bad_draw_does_not_matter(
        self, monkeypatch: pytest.MonkeyPatch, slot: int
    ) -> None:
        """First, middle and last — a loop that handled only one of them would
        pass a test that used only that one."""
        outcomes: list[object] = ["ok"] * 5
        outcomes[slot] = _abandonment()
        _script(monkeypatch, outcomes)

        assert len(_batch(5)) == 4

    def test_two_in_a_row_is_still_bad_luck(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The bound is three, so two consecutive must survive — otherwise the
        constant is decorative and any consecutive pair would end the batch."""
        _script(monkeypatch, ["ok", _abandonment(), _abandonment(), "ok", "ok"])

        assert len(_batch(5)) == 3

    def test_the_run_is_not_derailed_by_scattered_failures(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        outcomes: list[object] = ["ok"] * 10
        for slot in (1, 4, 8):
            outcomes[slot] = _abandonment()
        _script(monkeypatch, outcomes)

        assert len(_batch(10)) == 7


# --------------------------------------------------------------------------
# Where "shorter" is the wrong answer
# --------------------------------------------------------------------------


class TestBatch_StillFailsWhenTheBatchItselfFailed:
    def test_a_batch_that_produced_nothing_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An empty list returned quietly would be the worst of both: no
        puzzles, and no error saying so."""
        _script(monkeypatch, [_abandonment(), _abandonment()])

        with pytest.raises(GenerationAbandoned, match="no puzzle in a batch of 2"):
            _batch(2)

    def test_the_consecutive_bound_ends_the_batch(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        outcomes: list[object] = ["ok", "ok"] + [_abandonment()] * 8
        _script(monkeypatch, outcomes)

        with pytest.raises(GenerationAbandoned) as caught:
            _batch(10)

        assert "consecutive" in str(caught.value)

    def test_it_stops_rather_than_finishing_the_loop(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The point of the bound is the work it *saves*. A version that
        counted consecutive failures and reported them only at the end would
        pass the test above and none of this one."""
        outcomes: list[object] = ["ok"] + [_abandonment()] * 199
        attempted = _script(monkeypatch, outcomes)

        with pytest.raises(GenerationAbandoned):
            _batch(200)

        assert len(attempted) == 1 + MAX_CONSECUTIVE_ABANDONMENTS

    def test_the_refusal_says_how_much_was_produced(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A batch that made 7 of 50 and then gave up is a different situation
        from one that made none, and the message has to tell them apart."""
        outcomes: list[object] = ["ok"] * 7 + [_abandonment()] * 43
        _script(monkeypatch, outcomes)

        with pytest.raises(GenerationAbandoned) as caught:
            _batch(50)

        assert "7 of 50" in str(caught.value)

    def test_the_candidate_s_own_abandonment_is_the_cause(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CARD-080's F-008 lesson: the batch-level error must not replace the
        candidate-level one, or a caller logging with ``exc_info`` loses what
        the pipeline actually said."""
        last = _abandonment()
        _script(monkeypatch, ["ok", _abandonment(), _abandonment(), last])

        with pytest.raises(GenerationAbandoned) as caught:
            _batch(10)

        assert caught.value.__cause__ is last


# --------------------------------------------------------------------------
# What a batch deliberately does NOT survive
# --------------------------------------------------------------------------


class TestBatch_DoesNotSwallowATimeout:
    def test_a_timeout_still_ends_the_batch(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """ADR-0011's 30s bound is per request. Skipping a timed-out candidate
        would leave a 200-puzzle batch with no time bound at all — an hour and
        a half where the request used to fail in thirty seconds. Measured:
        30x30 at density 50 reaches the deadline rather than the retry bound,
        so this is not a hypothetical extent.
        """
        _script(monkeypatch, ["ok", SolverTimeout("passed its deadline"), "ok"])

        with pytest.raises(SolverTimeout):
            _batch(3)

    def test_a_timeout_is_not_counted_as_an_abandonment(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """It propagates on the first one, so it can never reach the bound."""
        attempted = _script(
            monkeypatch, [SolverTimeout("passed its deadline")] + ["ok"] * 9
        )

        with pytest.raises(SolverTimeout):
            _batch(10)

        assert len(attempted) == 1


# --------------------------------------------------------------------------
# The bound itself
# --------------------------------------------------------------------------


def test_the_batch_bound_is_its_own_number() -> None:
    """Not an alias of the per-puzzle bound. They answer different questions —
    how many draws one candidate is worth, versus how many failures in a row
    say the request is infeasible — and chaining them would say they move
    together (the same reasoning ``MAX_NUDGE_ATTEMPTS`` carries next door).
    """
    assert MAX_CONSECUTIVE_ABANDONMENTS == 3
    assert MAX_CONSECUTIVE_ABANDONMENTS != MAX_RETRY_ATTEMPTS
