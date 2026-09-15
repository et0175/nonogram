"""CARD-093 — a random batch that stops early keeps the puzzles it had already made.

``orchestrator.generate_batch`` used to hold every puzzle in memory until it
returned, and the admin stored them only after that. Either stopping exit —
``MAX_CONSECUTIVE_ABANDONMENTS`` in a row, or a ``SolverTimeout`` — raised past
the return, so the batch's puzzles went down with the exception
(``docs/GENERATION_ALGORITHM.md`` §10.2 finding 9).

The owner chose to hand each puzzle over *as it is made* (Q-1 option a): an
optional ``on_puzzle`` callable, which the admin's store step is. The stopping
rule itself is CARD-083's and does not change (AC-1, G-1). A batch that stopped
early with puzzles stored ends ``COMPLETE`` with a note; ``ERROR`` is kept for a
batch that produced nothing (Q-2).

``generate`` is scripted, as in ``tests/test_batch_abandonment.py`` and for the
same reason: the premise is an outcome, not the pipeline that produces it.
"""

from __future__ import annotations

import pytest

from nonogram import orchestrator
from nonogram.admin.batch_generator import BatchGenerator, BatchStatus
from nonogram.errors import GenerationAbandoned, SolverTimeout
from nonogram.orchestrator import MAX_CONSECUTIVE_ABANDONMENTS, GenerationRequest, Puzzle

_GRID = [[True, True], [False, True]]


def _puzzle(request: GenerationRequest) -> Puzzle:
    puzzle = Puzzle(request=request, seed=0)
    puzzle.record_candidate(_GRID)
    puzzle.confirm_uniqueness(1)
    puzzle.record_difficulty(10.0, 0)
    return puzzle


def _abandonment() -> GenerationAbandoned:
    return GenerationAbandoned("abandoned after 30 regenerate attempts")


def _timeout() -> SolverTimeout:
    return SolverTimeout("the solver ran out of its 30s budget")


def _script(monkeypatch: pytest.MonkeyPatch, outcomes: list[object], log: list[str]) -> None:
    """The n-th ``generate`` call does ``outcomes[n]``, and says so in ``log``."""
    calls = 0

    def fake_generate(request: GenerationRequest) -> Puzzle:
        nonlocal calls
        outcome = outcomes[calls]
        calls += 1
        log.append(f"generate {calls}")
        if isinstance(outcome, BaseException):
            raise outcome
        return _puzzle(request)

    monkeypatch.setattr(orchestrator, "generate", fake_generate)


def _made_then(n: int, stop: BaseException, count: int = 20) -> list[object]:
    tail = [stop] if isinstance(stop, SolverTimeout) else [_abandonment()] * MAX_CONSECUTIVE_ABANDONMENTS
    return (["ok"] * n + tail + ["ok"] * count)[:count]


# --------------------------------------------------------------------------
# orchestrator.generate_batch hands each puzzle over as it is made
# --------------------------------------------------------------------------


class TestGenerateBatch_HandsOverEachPuzzle:
    def test_every_made_puzzle_is_handed_over_once_in_order(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        log: list[str] = []
        _script(monkeypatch, ["ok", _abandonment(), "ok", "ok"], log)
        handed: list[Puzzle] = []

        result = orchestrator.generate_batch(
            count=4, sizes=[10], on_puzzle=handed.append
        )

        assert handed == list(result)
        assert len(handed) == 3

    def test_a_puzzle_is_handed_over_before_the_next_candidate_starts(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The property that makes a killed worker lose at most one puzzle:
        storage happens between candidates, not after the loop."""
        log: list[str] = []
        _script(monkeypatch, ["ok", "ok", "ok"], log)

        orchestrator.generate_batch(
            count=3, sizes=[10], on_puzzle=lambda _: log.append("handed")
        )

        assert log == [
            "generate 1", "handed", "generate 2", "handed", "generate 3", "handed",
        ]

    def test_an_abandoned_candidate_is_not_handed_over(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        log: list[str] = []
        _script(monkeypatch, [_abandonment(), "ok"], log)
        handed: list[Puzzle] = []

        orchestrator.generate_batch(count=2, sizes=[10], on_puzzle=handed.append)

        assert len(handed) == 1

    @pytest.mark.parametrize("stop", [_abandonment(), _timeout()], ids=["consecutive", "timeout"])
    def test_puzzles_made_before_a_stop_were_already_handed_over(
        self, monkeypatch: pytest.MonkeyPatch, stop: BaseException
    ) -> None:
        log: list[str] = []
        _script(monkeypatch, _made_then(7, stop), log)
        handed: list[Puzzle] = []

        with pytest.raises(type(stop)):
            orchestrator.generate_batch(count=20, sizes=[10], on_puzzle=handed.append)

        assert len(handed) == 7

    def test_the_stopping_rule_is_unchanged(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """AC-1: handing puzzles over does not buy a batch more attempts."""
        log: list[str] = []
        _script(monkeypatch, _made_then(7, _abandonment()), log)

        with pytest.raises(GenerationAbandoned):
            orchestrator.generate_batch(count=20, sizes=[10], on_puzzle=lambda _: None)

        assert log.count("generate 11") == 0
        assert len([entry for entry in log if entry.startswith("generate")]) == 7 + MAX_CONSECUTIVE_ABANDONMENTS


# --------------------------------------------------------------------------
# the admin stores them, and a stopped batch completes with a note
# --------------------------------------------------------------------------


class _Store:
    def __init__(self) -> None:
        self.stored = 0

    def add_puzzle(self, **kwargs) -> str:
        self.stored += 1
        return f"puzzle-{self.stored}"


class TestAdminBatch_KeepsWhatItMade:
    @pytest.mark.parametrize(
        ("stop", "reason"),
        [(_abandonment(), "consecutive"), (_timeout(), "timed out")],
        ids=["consecutive", "timeout"],
    )
    def test_a_stopped_batch_stores_its_puzzles_and_completes_with_a_note(
        self, monkeypatch: pytest.MonkeyPatch, stop: BaseException, reason: str
    ) -> None:
        _script(monkeypatch, _made_then(7, stop), [])
        store = _Store()
        generator = BatchGenerator(puzzle_review_service=store)

        batch_id = generator.create_batch(count=20, sizes=[10])

        job = generator.jobs[batch_id]
        assert store.stored == 7
        assert job.puzzle_count == 7
        assert job.status is BatchStatus.COMPLETE
        assert "stopped early" in job.error_message
        assert "7 of 20" in job.error_message
        assert reason in job.error_message

    def test_a_batch_that_made_nothing_is_still_an_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-4: zero puzzles is a failed batch, not a short one."""
        _script(monkeypatch, _made_then(0, _abandonment()), [])
        store = _Store()
        generator = BatchGenerator(puzzle_review_service=store)

        with pytest.raises(GenerationAbandoned):
            generator.create_batch(count=20, sizes=[10])

        (job,) = generator.jobs.values()
        assert store.stored == 0
        assert job.status is BatchStatus.ERROR

    def test_a_clean_batch_still_carries_no_note(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _script(monkeypatch, ["ok"] * 10, [])
        store = _Store()
        generator = BatchGenerator(puzzle_review_service=store)

        batch_id = generator.create_batch(count=10, sizes=[10])

        job = generator.jobs[batch_id]
        assert store.stored == 10
        assert job.status is BatchStatus.COMPLETE
        assert job.error_message is None

    def test_the_database_record_says_the_same(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        """The DB branch is the one production runs."""
        import uuid
        from contextlib import contextmanager

        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        from nonogram.db.models import Base, Batch

        engine = create_engine(f"sqlite:///{tmp_path / 'batches.db'}")
        Base.metadata.create_all(engine)
        factory = sessionmaker(bind=engine)

        @contextmanager
        def scope():
            db = factory()
            try:
                yield db
                db.commit()
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()

        _script(monkeypatch, _made_then(7, _abandonment()), [])
        store = _Store()
        generator = BatchGenerator(puzzle_review_service=store, session_factory=scope)

        batch_id = generator.create_batch(count=20, sizes=[10])

        with scope() as db:
            row = db.get(Batch, uuid.UUID(batch_id))
            assert row.status == BatchStatus.COMPLETE.value
            assert row.puzzle_count == 7
            assert "stopped early" in row.error_message
        assert store.stored == 7
