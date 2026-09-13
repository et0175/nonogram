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

from types import SimpleNamespace

import pytest

from nonogram.admin.puzzle_review import MockGenerator, PuzzleReviewService
from nonogram.clues import compute_clues
from nonogram.errors import NotUniquelySolvable, SolverTimeout
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
