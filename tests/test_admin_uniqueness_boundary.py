"""CARD-080 — no write path can store a puzzle that is not uniquely solvable.

    AC-A  TestStorageBoundary_RefusesAnAmbiguousGrid
    AC-B  TestStorageBoundary_StoresAUniqueGridUnchanged
    AC-C  TestStorageBoundary_AsksTheSolverNotTheCaller
    AC-D  TestStorageBoundary_RefusesRatherThanStoringAnUnprovenGrid
    AC-E  TestStorageAudit_ReportsWithoutWriting

Uniqueness is the product's defining property (FR-006) and the solver is the
authority on it (CON-005). Until this card, ``add_puzzle`` was a storage method
that trusted its caller: its two live callers went through
``orchestrator.generate`` and so were sound, but that is an argument about
callers, not a property of the store. The twenty rows deleted on 2026-09-14 are
what the argument cost when a third caller appeared —
``image_to_puzzle.create_puzzle_from_image``, which derived a tier from the
grid's *size* and never solved anything.
"""

from __future__ import annotations

import random
import time
from types import SimpleNamespace

import pytest

from nonogram.admin.batch_generator import BatchStatus
from nonogram.admin.puzzle_review import MockGenerator, PuzzleReviewService
from nonogram.clues import compute_clues
from nonogram.errors import NotUniquelySolvable, SolverTimeout
from nonogram.orchestrator import GENERATION_BUDGET_SECONDS
from nonogram.solver import solve

#: One filled cell per row and per column on a 2x2 — which BOTH diagonals
#: satisfy. Exactly 2 of the 16 possible 2x2 grids are ambiguous and these are
#: they, which is why the fixtures this card had to fix were a one-cell change.
AMBIGUOUS_GRID = [[True, False], [False, True]]

#: The same shape, one cell different, and a real puzzle.
UNIQUE_GRID = [[True, True], [False, True]]


def _assert_the_fixtures_are_what_the_file_assumes() -> None:
    """Checked against the solver, not asserted in a comment.

    If a solver change made AMBIGUOUS_GRID unique, every AC-A test below would
    pass for the wrong reason — they would be exercising the happy path and
    asserting nothing.
    """
    assert solve(*compute_clues(AMBIGUOUS_GRID)).solution_count == 2
    assert solve(*compute_clues(UNIQUE_GRID)).solution_count == 1


def test_the_fixtures_are_what_this_file_assumes() -> None:
    _assert_the_fixtures_are_what_the_file_assumes()


def _add(service: PuzzleReviewService, grid, **overrides):
    """``add_puzzle`` with everything but the grid defaulted."""
    kwargs = dict(
        grid=grid,
        clues_rows=[list(run) for run in compute_clues(grid)[0]],
        clues_cols=[list(run) for run in compute_clues(grid)[1]],
        width=len(grid[0]),
        height=len(grid),
        theme="christmas",
        difficulty_score=40,
        difficulty_tier="easy",
        quality_score=80,
        recognizability="high",
        strategies_used=["simple_overlap"],
    )
    kwargs.update(overrides)
    return service.add_puzzle(**kwargs)


# --------------------------------------------------------------------------
# AC-A
# --------------------------------------------------------------------------


class TestStorageBoundary_RefusesAnAmbiguousGrid:
    def test_it_raises(self) -> None:
        service = PuzzleReviewService()

        with pytest.raises(NotUniquelySolvable):
            _add(service, AMBIGUOUS_GRID)

    def test_nothing_is_written(self) -> None:
        """The refusal is not a partial write with an exception on top."""
        service = PuzzleReviewService()

        with pytest.raises(NotUniquelySolvable):
            _add(service, AMBIGUOUS_GRID)

        assert service.puzzles == {}

    def test_the_refusal_says_what_was_wrong(self) -> None:
        """A caller reaching this has a bug; the message has to name it."""
        service = PuzzleReviewService()

        with pytest.raises(NotUniquelySolvable, match="2 or more solutions"):
            _add(service, AMBIGUOUS_GRID)

    def test_a_grid_that_is_not_a_grid_is_refused_too(self) -> None:
        """Not the AC's case, but the same boundary: storage will not take it."""
        service = PuzzleReviewService()

        for junk in ([], [[]], [[True, False], [True]], "not a grid"):
            with pytest.raises(NotUniquelySolvable):
                service.add_puzzle(
                    grid=junk, clues_rows=[], clues_cols=[], width=1, height=1,
                    theme="t", difficulty_score=1, difficulty_tier="easy",
                    quality_score=1, recognizability="high", strategies_used=[],
                )
        assert service.puzzles == {}


# --------------------------------------------------------------------------
# AC-B
# --------------------------------------------------------------------------


class TestStorageBoundary_StoresAUniqueGridUnchanged:
    def test_the_row_is_stored(self) -> None:
        service = PuzzleReviewService()

        puzzle_id = _add(service, UNIQUE_GRID)

        assert puzzle_id in service.puzzles

    def test_every_field_survives_the_guard(self) -> None:
        """The guard reads; it must not rewrite. Asserted field by field
        rather than "it did not raise", because a guard that quietly
        normalised what it checked would pass the weaker version."""
        service = PuzzleReviewService()

        puzzle_id = _add(
            service,
            UNIQUE_GRID,
            theme="halloween",
            difficulty_score=71,
            difficulty_tier="hard",
            quality_score=42,
            recognizability="low",
            strategies_used=["line_dp", "guess"],
            source_image="pumpkin.png",
        )

        stored = service.puzzles[puzzle_id]
        assert stored["grid"] == UNIQUE_GRID
        assert stored["theme"] == "halloween"
        assert stored["difficulty_score"] == 71
        assert stored["difficulty_tier"] == "hard"
        assert stored["quality_score"] == 42
        assert stored["recognizability"] == "low"
        assert stored["strategies_used"] == ["line_dp", "guess"]
        assert stored["source_image"] == "pumpkin.png"
        assert stored["status"] == "draft"


# --------------------------------------------------------------------------
# AC-C
# --------------------------------------------------------------------------


class TestStorageBoundary_AsksTheSolverNotTheCaller:
    def test_a_caller_cannot_talk_its_way_past_the_guard(self) -> None:
        """No flag, no column, no claim about the grid gets a non-puzzle in.

        The caller here supplies clue lists describing a *different*, uniquely
        solvable grid, and a full set of plausible grades. Trusting any of
        those is exactly the failure mode: the twenty deleted rows arrived with
        a tier and a score attached, both invented.
        """
        service = PuzzleReviewService()

        with pytest.raises(NotUniquelySolvable):
            service.add_puzzle(
                grid=AMBIGUOUS_GRID,
                clues_rows=[[2], [1]],          # UNIQUE_GRID's clues, not this grid's
                clues_cols=[[1], [2]],
                width=2,
                height=2,
                theme="christmas",
                difficulty_score=40,
                difficulty_tier="easy",
                quality_score=99,
                recognizability="high",
                strategies_used=["simple_overlap"],
            )

        assert service.puzzles == {}

    def test_the_guard_actually_enters_the_solver(self) -> None:
        """Not a shape check dressed up as a verdict — the solver is called."""
        import nonogram.admin.puzzle_review as module

        calls = []
        real = module.solve

        def counting_solve(*args, **kwargs):
            calls.append(1)
            return real(*args, **kwargs)

        module.solve = counting_solve
        try:
            _add(PuzzleReviewService(), UNIQUE_GRID)
        finally:
            module.solve = real

        assert len(calls) == 1, "one solve per stored row, and not zero"


# --------------------------------------------------------------------------
# AC-D
# --------------------------------------------------------------------------


class TestStorageBoundary_RefusesRatherThanStoringAnUnprovenGrid:
    def test_a_timed_out_solve_refuses(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """An unproven grid is not a proven puzzle.

        A timeout is a fact about the run, not about the grid — but storage
        asks only one question, *has this been proven?*, and "we ran out of
        time" is not a yes.
        """
        import nonogram.admin.puzzle_review as module

        def always_times_out(*args, **kwargs):
            raise SolverTimeout("deadline passed")

        monkeypatch.setattr(module, "solve", always_times_out)
        service = PuzzleReviewService()

        with pytest.raises(NotUniquelySolvable, match="could not be proven"):
            _add(service, UNIQUE_GRID)

        assert service.puzzles == {}

    def test_the_timeout_is_not_reported_as_an_ambiguous_grid(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The two refusals share a class; they must not share a message.
        One says the grid is not a puzzle, the other that nobody knows."""
        import nonogram.admin.puzzle_review as module

        monkeypatch.setattr(
            module, "solve", lambda *a, **k: (_ for _ in ()).throw(SolverTimeout("x"))
        )

        with pytest.raises(NotUniquelySolvable) as caught:
            _add(PuzzleReviewService(), UNIQUE_GRID)

        assert "solutions" not in str(caught.value)

    def test_the_refusal_carries_the_exception_that_caused_it(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A refusal this card calls unreachable is the one whose cause
        somebody will need.

        ``batch_generator`` logs the refusal with ``exc_info=True`` and the
        card points at that log as where the per-candidate detail lives. With
        no ``from``, the entry is a NotUniquelySolvable with nothing attached
        and the solver's own exception is gone (CARD-080 review cycle 2,
        F-008).
        """
        import nonogram.admin.puzzle_review as module

        planted = SolverTimeout("gave up at node 12345")
        monkeypatch.setattr(
            module, "solve", lambda *a, **k: (_ for _ in ()).throw(planted)
        )

        with pytest.raises(NotUniquelySolvable) as caught:
            _add(PuzzleReviewService(), UNIQUE_GRID)

        assert caught.value.__cause__ is planted

    def test_a_verdict_is_not_dressed_up_as_a_failure(self) -> None:
        """The mirror: an ambiguous grid is a *verdict*, not an exception, so
        it must carry no cause. Otherwise every refusal would look like
        something went wrong."""
        service = PuzzleReviewService()

        with pytest.raises(NotUniquelySolvable) as caught:
            _add(service, AMBIGUOUS_GRID)

        assert caught.value.__cause__ is None


# --------------------------------------------------------------------------
# AC-E
# --------------------------------------------------------------------------


class TestStorageAudit_ReportsWithoutWriting:
    def test_a_clean_store_reports_nothing(self) -> None:
        service = PuzzleReviewService()
        _add(service, UNIQUE_GRID)

        assert service.audit_uniqueness() == []

    def test_a_bad_row_that_predates_the_guard_is_reported(self) -> None:
        """The audit's whole reason to exist: the guard stops new bad rows and
        cannot say anything about the ones already there. Planted directly in
        the store, since ``add_puzzle`` can no longer put one there."""
        service = PuzzleReviewService()
        good = _add(service, UNIQUE_GRID)
        service.puzzles["legacy_bad"] = {"id": "legacy_bad", "grid": AMBIGUOUS_GRID}

        failures = service.audit_uniqueness()

        assert [puzzle_id for puzzle_id, _ in failures] == ["legacy_bad"]
        assert good not in [puzzle_id for puzzle_id, _ in failures]

    def test_the_audit_changes_nothing(self) -> None:
        """Reports. Does not quarantine, delete, or mark."""
        service = PuzzleReviewService()
        _add(service, UNIQUE_GRID)
        service.puzzles["legacy_bad"] = {"id": "legacy_bad", "grid": AMBIGUOUS_GRID}
        before = {k: dict(v) for k, v in service.puzzles.items()}

        service.audit_uniqueness()

        assert service.puzzles == before

    def test_the_report_says_why_each_row_failed(self) -> None:
        service = PuzzleReviewService()
        service.puzzles["ambiguous"] = {"id": "ambiguous", "grid": AMBIGUOUS_GRID}
        service.puzzles["malformed"] = {"id": "malformed", "grid": "not a grid"}

        reasons = dict(service.audit_uniqueness())

        assert "2 or more solutions" in reasons["ambiguous"]
        assert "not a readable grid" in reasons["malformed"]


# --------------------------------------------------------------------------
# Review cycle 1, F-001 — the audit's reader is not the write path's guard
# --------------------------------------------------------------------------

#: The same puzzle as ``UNIQUE_GRID``, stored the way an older writer left it.
#: A JSON column round-trips ``1``/``0`` as readily as ``true``/``false``, and
#: which one a row holds says nothing about whether it is a puzzle.
LEGACY_INT_GRID = [[1, 1], [0, 1]]

#: And the ambiguous one in the same encoding, so coercion cannot be mistaken
#: for "the audit stopped looking".
LEGACY_INT_AMBIGUOUS_GRID = [[1, 0], [0, 1]]


class TestStorageAudit_ReadsRowsTheWayTheReadPathDoes:
    """The audit ran the write path's guard, whose first step refuses a cell
    that is not a ``bool``. Right at a write boundary — a caller handing over
    something else has a bug — and wrong here, because the audit's entire
    subject is rows that older code wrote. It reported a uniquely solvable
    puzzle as a failure (review cycle 1, F-001).
    """

    def test_the_legacy_row_really_is_the_same_puzzle(self) -> None:
        """The premise, from the solver rather than from a comment. Without
        it, the test below could pass because the audit reports nothing at
        all."""
        assert compute_clues(LEGACY_INT_GRID) == compute_clues(UNIQUE_GRID)
        assert solve(*compute_clues(LEGACY_INT_GRID)).solution_count == 1

    def test_a_legacy_row_with_integer_cells_is_not_reported(self) -> None:
        service = PuzzleReviewService()
        service.puzzles["legacy_ints"] = {"id": "legacy_ints", "grid": LEGACY_INT_GRID}

        assert service.audit_uniqueness() == []

    def test_an_ambiguous_legacy_row_is_still_reported(self) -> None:
        """Coercing the cell type must not turn the audit into a pass."""
        service = PuzzleReviewService()
        service.puzzles["legacy_bad"] = {
            "id": "legacy_bad",
            "grid": LEGACY_INT_AMBIGUOUS_GRID,
        }

        assert [row_id for row_id, _ in service.audit_uniqueness()] == ["legacy_bad"]

    def test_the_write_path_still_refuses_the_same_cells(self) -> None:
        """The asymmetry is the decision, not a leftover: loosening the read
        path must not loosen the boundary this card exists to build."""
        service = PuzzleReviewService()

        with pytest.raises(NotUniquelySolvable, match="booleans"):
            _add(service, LEGACY_INT_GRID)

        assert service.puzzles == {}


class TestTheTwoGridReaders_AgreeWithEachOther:
    """``PuzzleReviewService._as_readable_grid`` reimplements
    ``regrade._as_grid`` rather than importing it — the same rule, read by two
    modules. The package's standing answer to duplicated logic is to
    cross-check the copies from the test tree (``solver.propagate.mask_runs``
    is the precedent), which is what keeps "they agree" a fact rather than an
    intention.
    """

    @staticmethod
    def _corpus() -> list:
        """Shapes and cell types a JSON column can actually hold."""
        rng = random.Random(80_001)
        cells = [True, False, 1, 0, None, "", "x", 0.0, 2, [], [0]]
        corpus: list = [
            [],
            [[]],
            [[True], []],
            "not a grid",
            None,
            42,
            {"rows": [[True]]},
            [[True, False], [True]],
            [[True], "no"],
            # A non-list row whose LENGTH MATCHES the first row's. Without
            # these the corpus never reaches the ``isinstance(line, list)``
            # check at all: every generated row is built as a list, and the two
            # hand-written odd rows above are caught by the width check and by
            # the outer isinstance instead. A reader that dropped the type
            # check would read "no" character by character and return
            # [[True, False], [True, True]] where regrade._as_grid returns
            # None — the exact drift this class exists to catch, and it was
            # invisible here (CARD-080 review cycle 2, F-007).
            [[True, False], "no"],
            [[True], 1],
            [[True, False], ("x", "y")],
            [[True, False, True], "abc"],
        ]
        for _ in range(300):
            height = rng.randint(1, 5)
            width = rng.randint(1, 5)
            grid = [[rng.choice(cells) for _ in range(width)] for _ in range(height)]
            if rng.random() < 0.2:
                grid[-1] = grid[-1][: rng.randint(0, width)]
            if rng.random() < 0.1:
                # Same idea, generated: a row that is not a list, sometimes at
                # the matching width and sometimes not.
                grid[rng.randrange(height)] = rng.choice(
                    ["x" * width, "x" * (width + 1), width, None, tuple([True] * width)]
                )
            corpus.append(grid)
        return corpus

    def test_the_corpus_covers_both_answers(self) -> None:
        """A corpus that was all-readable or all-unreadable would make the
        agreement test below vacuous."""
        corpus = self._corpus()
        assert len(corpus) >= 300

        readable = [c for c in corpus if PuzzleReviewService._as_readable_grid(c) is not None]
        assert len(readable) >= 50
        assert len(corpus) - len(readable) >= 50

    def test_the_corpus_reaches_the_row_type_check(self) -> None:
        """The specific hole F-007 was: every generated row was built as a
        list, so no case ever exercised ``isinstance(line, list)`` — the test
        agreed with itself. Asserted here rather than left to the generator's
        seed, and asserted at MATCHING width, which is the only shape that gets
        past the width check to reach the type check."""
        corpus = self._corpus()

        non_list_rows = [
            c
            for c in corpus
            if isinstance(c, list) and any(not isinstance(row, list) for row in c)
        ]
        assert len(non_list_rows) >= 10, "no candidate reaches the row-type check"

        def _width(row) -> int:
            return len(row) if hasattr(row, "__len__") else -1

        at_matching_width = [
            c
            for c in non_list_rows
            if isinstance(c[0], list)
            and any(
                not isinstance(row, list) and _width(row) == len(c[0]) for row in c[1:]
            )
        ]
        assert len(at_matching_width) >= 4, (
            "every non-list row is caught by the width check first, so the "
            "row-type check is still unreached"
        )

    def test_they_agree_on_every_case(self) -> None:
        from nonogram.admin import regrade

        for candidate in self._corpus():
            assert PuzzleReviewService._as_readable_grid(candidate) == regrade._as_grid(
                candidate
            ), candidate


# --------------------------------------------------------------------------
# Review cycle 1, F-002 — the audit's deadline argument was accepted, ignored
# --------------------------------------------------------------------------


class TestStorageAudit_HonoursTheBudgetItAccepts:
    """``audit_uniqueness(deadline_seconds=...)`` took a per-row budget and
    never passed it anywhere: the only solve it reached hardcoded
    ``GENERATION_BUDGET_SECONDS``. An operator raising the budget for a deeper
    audit would have seen no change and had no error to explain why.
    """

    @staticmethod
    def _recording_solve(monkeypatch) -> list:
        """Every deadline the module's ``solve`` is handed, as a budget."""
        import nonogram.admin.puzzle_review as module

        seen: list[float] = []
        real = module.solve

        def recorder(*args, deadline, **kwargs):
            seen.append(deadline - time.monotonic())
            return real(*args, deadline=deadline, **kwargs)

        monkeypatch.setattr(module, "solve", recorder)
        return seen

    def test_the_budget_reaches_the_solver(self, monkeypatch: pytest.MonkeyPatch) -> None:
        seen = self._recording_solve(monkeypatch)
        service = PuzzleReviewService()
        service.puzzles["row"] = {"id": "row", "grid": UNIQUE_GRID}

        service.audit_uniqueness(deadline_seconds=3.5)

        assert len(seen) == 1
        assert 3.0 < seen[0] <= 3.5

    def test_a_different_budget_is_a_different_deadline(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Two budgets, two deadlines — so a run that ignored the argument and
        happened to match one of them cannot pass."""
        seen = self._recording_solve(monkeypatch)
        service = PuzzleReviewService()
        service.puzzles["row"] = {"id": "row", "grid": UNIQUE_GRID}

        service.audit_uniqueness(deadline_seconds=2.0)
        service.audit_uniqueness(deadline_seconds=12.0)

        assert seen[1] - seen[0] > 9.0

    def test_the_default_is_the_generation_budget(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        seen = self._recording_solve(monkeypatch)
        service = PuzzleReviewService()
        service.puzzles["row"] = {"id": "row", "grid": UNIQUE_GRID}

        service.audit_uniqueness()

        assert abs(seen[0] - GENERATION_BUDGET_SECONDS) < 1.0

    def test_a_row_that_runs_out_of_budget_says_which_budget(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The reason is what the operator reads; naming the default when a
        different number was asked for is the same lie one layer up."""
        import nonogram.admin.puzzle_review as module

        monkeypatch.setattr(
            module, "solve", lambda *a, **k: (_ for _ in ()).throw(SolverTimeout("x"))
        )
        service = PuzzleReviewService()
        service.puzzles["row"] = {"id": "row", "grid": UNIQUE_GRID}

        reasons = dict(service.audit_uniqueness(deadline_seconds=0.25))

        assert "0.25" in reasons["row"]
        assert "could not be proven" in reasons["row"]

    def test_the_write_path_still_uses_the_generation_budget(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """ADR-0011's bound on the write boundary is not a caller's choice."""
        seen = self._recording_solve(monkeypatch)

        _add(PuzzleReviewService(), UNIQUE_GRID)

        assert abs(seen[0] - GENERATION_BUDGET_SECONDS) < 1.0


# --------------------------------------------------------------------------
# Review cycle 1, F-003 — the batch generator's refusal count had no reader
# --------------------------------------------------------------------------


class _StoreThatRefusesChosenCandidates:
    """A stand-in for the real store, refusing by position rather than by
    grid — the point under test is what the batch generator does with a
    refusal, not what makes the store raise."""

    def __init__(self, refuse_at: set) -> None:
        self._refuse_at = refuse_at
        self.seen = 0
        self.stored = 0

    def add_puzzle(self, **kwargs) -> str:
        index = self.seen
        self.seen += 1
        if index in self._refuse_at:
            raise NotUniquelySolvable("planted refusal")
        self.stored += 1
        return f"puzzle-{index}"


def _candidate():
    """What ``orchestrator.generate_batch`` hands the storing loop."""
    rows, columns = compute_clues(UNIQUE_GRID)
    return SimpleNamespace(
        grid=UNIQUE_GRID,
        clues=SimpleNamespace(rows=rows, columns=columns),
        width=2,
        height=2,
        difficulty_score=33,
        difficulty_tier="easy",
    )


def _delivering(count: int):
    """A stand-in for ``orchestrator.generate_batch`` that keeps its contract.

    Since CARD-093 the admin stores each puzzle from ``on_puzzle`` as the batch
    makes it, not from the returned list — so a fake that only returned a list
    would store nothing and every assertion below would be about an empty
    batch. It hands each candidate over, then returns them, as the real one does.
    """

    def fake(*, on_puzzle=None, **kwargs):
        puzzles = [_candidate() for _ in range(count)]
        for puzzle in puzzles:
            if on_puzzle is not None:
                on_puzzle(puzzle)
        return puzzles

    return fake


def _run_batch(monkeypatch, *, count: int, refuse_at: set):
    from nonogram import orchestrator as orchestrator_module
    from nonogram.admin.batch_generator import BatchGenerator, BatchJob, BatchStatus

    monkeypatch.setattr(
        orchestrator_module,
        "generate_batch",
        _delivering(count),
    )
    store = _StoreThatRefusesChosenCandidates(refuse_at)
    generator = BatchGenerator(puzzle_review_service=store)
    generator.jobs["batch-1"] = BatchJob(
        batch_id="batch-1",
        status=BatchStatus.GENERATING,
        total_count=count,
        sizes=[10],
        theme="christmas",
    )

    generator._generate_random_batch("batch-1")

    return generator.jobs["batch-1"], store


def _sqlite_session_scope(tmp_path):
    """A ``session_scope``-shaped factory over a throwaway SQLite file.

    The same shape ``app.py`` hands the generator in DB mode — a context
    manager that commits on the way out — because the DB branch of
    ``_update_batch_status`` never commits for itself and would otherwise look
    like it worked while writing nothing.
    """
    from contextlib import contextmanager

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from nonogram.db.models import Base

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

    return scope


class TestBatchGenerator_SaysOutLoudWhenTheStoreRefusedACandidate:
    """The refusal was counted into a local that nothing read, under a comment
    claiming the count was what told the owner something broke (review cycle
    1, F-003). The count is now carried onto the batch record, which the batch
    status page already renders.
    """

    def test_the_refusal_reaches_the_batch_record(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        job, store = _run_batch(monkeypatch, count=3, refuse_at={1})

        assert store.stored == 2
        assert job.puzzle_count == 2
        assert job.error_message is not None
        assert "1 of 3" in job.error_message
        assert "not uniquely solvable" in job.error_message

    def test_the_batch_is_not_thrown_away_over_one_bad_candidate(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Eleven real puzzles stored is eleven real puzzles; the note says
        what is missing rather than discarding what is not.

        Driven through ``create_batch`` rather than ``_generate_random_batch``,
        because that is where the decision actually lives: the inner method
        never assigns a status at all, so asserting "not ERROR" against it was
        an assertion that could not fail (CARD-080 review cycle 2, F-013). The
        real question is whether the wrapper's ``except`` swallows the batch or
        lets it complete — and whether the note survives the COMPLETE update
        that follows it. Count is 12 because a random batch refuses fewer
        than 10.
        """
        from nonogram import orchestrator as orchestrator_module
        from nonogram.admin.batch_generator import BatchGenerator

        monkeypatch.setattr(
            orchestrator_module,
            "generate_batch",
            _delivering(12),
        )
        generator = BatchGenerator(
            puzzle_review_service=_StoreThatRefusesChosenCandidates({4})
        )

        batch_id = generator.create_batch(count=12, sizes=[10])

        job = generator.jobs[batch_id]
        assert job.status is BatchStatus.COMPLETE
        assert job.completed_count == 12
        assert job.puzzle_count == 11
        # The COMPLETE update runs after the note is written; it must not
        # overwrite it, or the whole F-003 fix dies one frame above the code
        # that was reviewed.
        assert "1 of 12" in job.error_message

    def test_a_clean_batch_carries_no_note(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The note is a signal, so it must be silent when nothing happened —
        an alert on every batch is an alert on none."""
        job, store = _run_batch(monkeypatch, count=3, refuse_at=set())

        assert store.stored == 3
        assert job.puzzle_count == 3
        assert job.error_message is None

    def test_the_note_counts_every_refusal(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        job, _ = _run_batch(monkeypatch, count=4, refuse_at={0, 2, 3})

        assert job.puzzle_count == 1
        assert "3 of 4" in job.error_message

    def test_a_generator_shortfall_is_reported_as_a_different_thing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CARD-083: a candidate the *generator* abandoned is ordinary bad
        luck; a candidate the *store* refused is a bug. One "missing puzzles"
        number would make them indistinguishable, which is the state CARD-080
        put the refusal count into words to escape."""
        from nonogram import orchestrator as orchestrator_module
        from nonogram.admin.batch_generator import BatchGenerator, BatchJob

        # The generator returns 8 for a request of 10 — two were abandoned.
        monkeypatch.setattr(
            orchestrator_module,
            "generate_batch",
            _delivering(8),
        )
        generator = BatchGenerator(
            puzzle_review_service=_StoreThatRefusesChosenCandidates(set())
        )
        generator.jobs["batch-1"] = BatchJob(
            batch_id="batch-1",
            status=BatchStatus.GENERATING,
            total_count=10,
            sizes=[10],
            theme="christmas",
        )

        generator._generate_random_batch("batch-1")

        job = generator.jobs["batch-1"]
        assert job.puzzle_count == 8
        assert "2 of 10 candidates could not be made" in job.error_message
        assert "refused by the store" not in job.error_message

    def test_both_shortfalls_are_reported_side_by_side(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """They can happen in the same batch, and the note must not lose one."""
        from nonogram import orchestrator as orchestrator_module
        from nonogram.admin.batch_generator import BatchGenerator, BatchJob

        monkeypatch.setattr(
            orchestrator_module,
            "generate_batch",
            _delivering(8),
        )
        generator = BatchGenerator(
            puzzle_review_service=_StoreThatRefusesChosenCandidates({3})
        )
        generator.jobs["batch-1"] = BatchJob(
            batch_id="batch-1",
            status=BatchStatus.GENERATING,
            total_count=10,
            sizes=[10],
            theme="christmas",
        )

        generator._generate_random_batch("batch-1")

        note = generator.jobs["batch-1"].error_message
        assert "2 of 10 candidates could not be made" in note
        assert "1 of 8 generated candidates were refused" in note

    def test_a_full_batch_carries_no_shortfall_note(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The note is a signal; a batch that delivered what it promised must
        stay silent, or the alert is on every batch and therefore on none."""
        from nonogram import orchestrator as orchestrator_module
        from nonogram.admin.batch_generator import BatchGenerator, BatchJob

        monkeypatch.setattr(
            orchestrator_module,
            "generate_batch",
            _delivering(10),
        )
        generator = BatchGenerator(
            puzzle_review_service=_StoreThatRefusesChosenCandidates(set())
        )
        generator.jobs["batch-1"] = BatchJob(
            batch_id="batch-1",
            status=BatchStatus.GENERATING,
            total_count=10,
            sizes=[10],
            theme="christmas",
        )

        generator._generate_random_batch("batch-1")

        assert generator.jobs["batch-1"].error_message is None

    def test_the_refusal_reaches_the_batch_row_in_db_mode(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        """The legacy in-memory job and the ``batches`` row are two separate
        branches of the same method, and production runs the second one."""
        import uuid

        from nonogram import orchestrator as orchestrator_module
        from nonogram.admin.batch_generator import BatchGenerator
        from nonogram.db.models import Batch

        scope = _sqlite_session_scope(tmp_path)
        batch_id = str(uuid.uuid4())
        with scope() as db:
            db.add(
                Batch(
                    id=uuid.UUID(batch_id),
                    status="generating",
                    source="random",
                    total_count=3,
                    sizes=[10],
                    theme="christmas",
                )
            )

        monkeypatch.setattr(
            orchestrator_module,
            "generate_batch",
            _delivering(3),
        )
        generator = BatchGenerator(
            puzzle_review_service=_StoreThatRefusesChosenCandidates({2}),
            session_factory=scope,
        )

        generator._generate_random_batch(batch_id)

        with scope() as db:
            row = db.get(Batch, uuid.UUID(batch_id))
            assert row.puzzle_count == 2
            assert row.error_message is not None
            assert "1 of 3" in row.error_message
            assert row.status == "generating"

    def test_a_clean_batch_leaves_the_batch_row_quiet_in_db_mode(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        import uuid

        from nonogram import orchestrator as orchestrator_module
        from nonogram.admin.batch_generator import BatchGenerator
        from nonogram.db.models import Batch

        scope = _sqlite_session_scope(tmp_path)
        batch_id = str(uuid.uuid4())
        with scope() as db:
            db.add(
                Batch(
                    id=uuid.UUID(batch_id),
                    status="generating",
                    source="random",
                    total_count=3,
                    sizes=[10],
                    theme="christmas",
                )
            )

        monkeypatch.setattr(
            orchestrator_module,
            "generate_batch",
            _delivering(3),
        )
        generator = BatchGenerator(
            puzzle_review_service=_StoreThatRefusesChosenCandidates(set()),
            session_factory=scope,
        )

        generator._generate_random_batch(batch_id)

        with scope() as db:
            row = db.get(Batch, uuid.UUID(batch_id))
            assert row.puzzle_count == 3
            assert row.error_message is None


# --------------------------------------------------------------------------
# The generator that feeds the store
# --------------------------------------------------------------------------


class TestMockGenerator_ProducesPuzzlesAndNotJustGrids:
    """``MockGenerator`` ships in ``src/`` and is what 29 tests store.

    Until this card it emitted a random 50%-density grid, clues of random
    integers unrelated to it, and a random score and tier — the same defect as
    the function that wrote the twenty deleted rows, still in the package after
    that one was removed. These pin the three things that changed.
    """

    @pytest.fixture(scope="class")
    def batch(self):
        return MockGenerator(seed=2026).generate_batch(count=8, sizes=[10, 15], theme="christmas")

    def test_every_generated_grid_is_uniquely_solvable(self, batch) -> None:
        for puzzle in batch:
            assert solve(*compute_clues(puzzle["grid"])).solution_count == 1

    def test_the_clues_describe_the_grid_they_ship_with(self, batch) -> None:
        """They were random integers before, bearing no relation to the grid."""
        for puzzle in batch:
            rows, columns = compute_clues(puzzle["grid"])
            assert puzzle["clues_rows"] == [list(run) for run in rows]
            assert puzzle["clues_cols"] == [list(run) for run in columns]

    def test_the_grade_is_the_real_scorers_and_not_a_random_number(self, batch) -> None:
        from nonogram.difficulty import classify, score_difficulty
        import math

        for puzzle in batch:
            result = solve(*compute_clues(puzzle["grid"]))
            score = score_difficulty(result.signals)
            assert puzzle["difficulty_score"] == math.ceil(score)
            assert puzzle["difficulty_tier"] == classify(
                score, result.signals.branch_nodes
            ).value

    def test_it_keeps_drawing_until_the_solver_certifies_one(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The resample loop, pinned deterministically rather than by luck.

        ``test_every_generated_grid_is_uniquely_solvable`` above does not
        actually pin this: at density 0.65 a first draw is unique roughly nine
        times in ten, so with a fixed seed a batch of eight can be all-unique
        on first draw and the loop can be deleted with the suite still green —
        which is exactly what a mutation check showed. So the first two solves
        are forced to report an ambiguous grid, and what is asserted is that
        the generator drew again instead of returning one of them.
        """
        import nonogram.admin.puzzle_review as module

        real_solve = module.solve
        calls = []

        def solve_that_lies_twice(*args, **kwargs):
            result = real_solve(*args, **kwargs)
            calls.append(1)
            if len(calls) <= 2:
                return SimpleNamespace(solution_count=2, signals=result.signals)
            return result

        monkeypatch.setattr(module, "solve", solve_that_lies_twice)

        puzzles = MockGenerator(seed=7).generate_batch(count=1, sizes=[10])

        assert len(calls) == 3, "the generator accepted a grid the solver refused"
        assert solve(*compute_clues(puzzles[0]["grid"])).solution_count == 1

    def test_it_gives_up_loudly_rather_than_returning_an_unchecked_grid(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """MAX_DRAWS exhausted is a refusal, not a shrug.

        Returning the last draw would be the whole failure this card exists to
        prevent, one layer up from the store.
        """
        import nonogram.admin.puzzle_review as module

        real_solve = module.solve
        monkeypatch.setattr(
            module,
            "solve",
            lambda *a, **k: SimpleNamespace(
                solution_count=2, signals=real_solve(*a, **k).signals
            ),
        )

        with pytest.raises(NotUniquelySolvable, match="no uniquely solvable"):
            MockGenerator(seed=7).generate_batch(count=1, sizes=[10])

    def test_its_output_is_storable(self, batch) -> None:
        """The end-to-end statement: the generator and the guard agree."""
        service = PuzzleReviewService()
        for puzzle in batch:
            service.add_puzzle(
                grid=puzzle["grid"],
                clues_rows=puzzle["clues_rows"],
                clues_cols=puzzle["clues_cols"],
                width=puzzle["width"],
                height=puzzle["height"],
                theme=puzzle["theme"],
                difficulty_score=puzzle["difficulty_score"],
                difficulty_tier=puzzle["difficulty_tier"],
                quality_score=puzzle["quality_score"],
                recognizability=puzzle["recognizability"],
                strategies_used=puzzle["strategies_used"],
            )

        assert len(service.puzzles) == len(batch)
