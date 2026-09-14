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

import time

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

        with pytest.raises(GenerationAbandoned, match="no puzzle in this batch of 2"):
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
        pass the test above and none of this one.

        The count was 200 until CARD-088 brought the ceiling down to 50; the
        assertion is about how few candidates are *attempted* (four), so the
        largest askable batch demonstrates it exactly as well as the old one
        did. Changed because 200 is now refused before the loop runs, not
        because the claim weakened.
        """
        outcomes: list[object] = ["ok"] + [_abandonment()] * 49
        attempted = _script(monkeypatch, outcomes)

        with pytest.raises(GenerationAbandoned):
            _batch(orchestrator.MAX_BATCH_COUNT)

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
        # Padded to the full count: a mutant that moved the bound would
        # otherwise run past a short script and die on IndexError rather than
        # on the assertion this test is about (review cycle 1, F-005).
        outcomes: list[object] = ["ok", _abandonment(), _abandonment(), last]
        outcomes += [_abandonment()] * (10 - len(outcomes))
        _script(monkeypatch, outcomes)

        with pytest.raises(GenerationAbandoned) as caught:
            _batch(10)

        assert caught.value.__cause__ is last

    @pytest.mark.parametrize(
        ("count", "exit_taken"), [(1, "no puzzle in this batch"), (2, "no puzzle in this batch"), (3, "consecutive"), (10, "consecutive")]
    )
    def test_both_exits_chain_the_candidate_s_abandonment(
        self, monkeypatch: pytest.MonkeyPatch, count: int, exit_taken: str
    ) -> None:
        """There are two ways out and they must not disagree about this.

        Only the consecutive one chained at first, so a caller asking for one
        or two puzzles lost what the pipeline said — CARD-080's F-008 defect,
        on the other branch of the same function (review cycle 1, F-001). The
        parametrize spans the boundary deliberately: count 1 and 2 reach the
        empty-batch exit, count 3 and up cannot, because with no successes the
        consecutive counter never resets.
        """
        # The abandonment that actually triggers the exit — the last slot for a
        # count below the bound, the third one above it. Getting this wrong is
        # how the first draft of this test asserted against an exception the
        # run never reached.
        trigger = min(count, MAX_CONSECUTIVE_ABANDONMENTS)
        last = _abandonment()
        outcomes: list[object] = [_abandonment() for _ in range(trigger - 1)]
        outcomes += [last] + [_abandonment()] * (count - trigger)
        _script(monkeypatch, outcomes)

        with pytest.raises(GenerationAbandoned) as caught:
            _batch(count)

        assert exit_taken in str(caught.value)
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


# --------------------------------------------------------------------------
# CARD-088 — the batch stops on its own clock, not on the worker's
# --------------------------------------------------------------------------


class TestBatch_StopsOnItsOwnClock:
    """AC-1: a batch that would outlive the request stops and returns.

    ``generate_batch`` runs synchronously inside the request, and since
    CARD-086 the deployed panel has a gunicorn worker timeout. A batch that
    overran it was killed mid-run and lost everything it had produced — after
    doing all the work. The clock here is what makes the same request safe at
    every extent, where a flat count cannot be: measured, a puzzle costs about
    0.06s at 20x20 and 3.90s at 30x30, so 50 of them is 3s at one end and 195s
    at the other.
    """

    @staticmethod
    def _clock_that_jumps_after(calls: int):
        """Real time plus an offset that leaps once, so only the batch's own
        deadline is crossed — a fake returning small absolute numbers would
        also poison each candidate's own deadline, which the solver reads
        against the real clock (the trap CARD-086 hit)."""
        base = time.monotonic()
        state = {"calls": 0}

        def clock() -> float:
            state["calls"] += 1
            return base + (0.0 if state["calls"] <= calls else 999.0)

        return clock

    def test_a_batch_that_fits_reports_no_shortfall(self) -> None:
        result = orchestrator.generate_batch(count=5, sizes=[10])

        assert len(result) == 5
        assert result.not_attempted == 0
        assert result.stopped_early is False

    def test_a_batch_that_runs_out_of_time_stops_and_counts_the_rest(self) -> None:
        result = orchestrator.generate_batch(
            count=10,
            sizes=[10],
            budget_seconds=10.0,
            monotonic=self._clock_that_jumps_after(3),
        )

        assert result.stopped_early is True
        assert result.not_attempted > 0
        assert len(result) >= 1, "the puzzles it did make are still returned"

    def test_every_candidate_is_accounted_for(self) -> None:
        """Produced, abandoned, or never attempted — no third state.

        A candidate falling out of all three would be a puzzle the caller paid
        for and cannot see, which is exactly the silence this card removes.
        """
        result = orchestrator.generate_batch(
            count=10,
            sizes=[10],
            budget_seconds=10.0,
            monotonic=self._clock_that_jumps_after(3),
        )

        assert len(result) + result.abandoned + result.not_attempted == 10

    def test_the_result_is_still_a_list(self) -> None:
        """CARD-083's contract survives: the shortfall *is* the return value.

        Ten test modules and the one production caller treat this as a
        sequence. Carrying the new counts as attributes on a list subclass
        keeps every one of them working untouched — a dataclass would have
        rewritten them all to reach through a ``.puzzles``.
        """
        result = orchestrator.generate_batch(count=3, sizes=[10])

        assert isinstance(result, list)
        assert result == list(result)
        assert len([puzzle for puzzle in result]) == 3

    def test_a_started_candidate_always_finishes(self) -> None:
        """The deadline is checked before a candidate, never during one.

        So the ceiling is a sum that can be stated —
        ``BATCH_BUDGET_SECONDS + GENERATION_BUDGET_SECONDS`` — rather than a
        race, and no puzzle is ever half-made. Every puzzle that comes back is
        complete and uniquely solvable, clock or no clock.
        """
        result = orchestrator.generate_batch(
            count=10,
            sizes=[10],
            budget_seconds=10.0,
            monotonic=self._clock_that_jumps_after(3),
        )

        for puzzle in result:
            assert puzzle.solution_count == 1
            assert puzzle.ready_for_export


class TestBatch_SaysWhichBoundStoppedIt:
    """AC-3: "unlucky" and "will happen again" are different facts.

    A caller told only "you got fewer than you asked for" re-runs the request.
    That is the right move after an abandoned candidate and a waste of time
    after a clock stop, which will end in the same place every time.
    """

    def test_a_clock_stop_is_not_reported_as_an_abandonment(self) -> None:
        base = time.monotonic()
        state = {"calls": 0}

        def clock() -> float:
            state["calls"] += 1
            return base + (0.0 if state["calls"] <= 3 else 999.0)

        result = orchestrator.generate_batch(
            count=10, sizes=[10], budget_seconds=10.0, monotonic=clock
        )

        assert result.not_attempted > 0
        assert result.abandoned == 0, (
            "these candidates were never tried; calling them abandoned would "
            "name a cause that did not happen"
        )

    def test_an_empty_clock_stopped_batch_says_so(self) -> None:
        """Not "every candidate was abandoned" — none of them were tried."""
        base = time.monotonic()
        state = {"calls": 0}

        def clock() -> float:
            state["calls"] += 1
            return base + (0.0 if state["calls"] <= 1 else 999.0)

        with pytest.raises(orchestrator.GenerationAbandoned) as caught:
            orchestrator.generate_batch(
                count=5, sizes=[10], budget_seconds=10.0, monotonic=clock
            )

        message = str(caught.value)
        assert "budget" in message
        assert "abandoned after" not in message, (
            "the retry-exhaustion message would name a cause that never ran"
        )


class TestBatch_CountCap:
    """AC-4: 200 described nothing real at the top of the supported range."""

    def test_the_ceiling_is_fifty(self) -> None:
        assert orchestrator.MAX_BATCH_COUNT == 50

    @pytest.mark.parametrize("count", [0, 51, 200])
    def test_a_count_outside_the_range_is_refused(self, count: int) -> None:
        with pytest.raises(ValueError) as caught:
            orchestrator.generate_batch(count=count, sizes=[10])

        assert str(orchestrator.MAX_BATCH_COUNT) in str(caught.value)

    def test_the_boundary_itself_is_accepted(self) -> None:
        """The limit, not limit-1: 50 must be askable or the cap is 49."""
        result = orchestrator.generate_batch(count=50, sizes=[10])

        assert len(result) <= 50

    def test_the_cap_is_not_the_mechanism(self) -> None:
        """G-1 in miniature: the count bound and the clock answer different
        questions, so neither is derived from the other. A cap that happened to
        equal the budget would read as one number doing two jobs."""
        assert orchestrator.MAX_BATCH_COUNT != orchestrator.BATCH_BUDGET_SECONDS
