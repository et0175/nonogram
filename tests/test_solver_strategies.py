"""FR-029's registry criteria, each under the name ``requirements.yml`` names.

CARD-318. FR-029's criteria carried ten dead ``test:`` refs — names no
definition in ``tests/`` ever had. The behaviour was **not** missing: CARD-072
built all of it and covered it in ``tests/test_strategies.py``, but under its
own card-local names (``test_strategies_*``), so the registry's refs never
resolved and every criterion read as mechanically checked.

This file is the repair. One class per registry criterion, named exactly as the
registry names it, asserting that criterion's own ``given``/``then`` and
nothing wider:

    AC-135  TestGenerate_StrategiesRecordedFromTheOneVerifyingSolve
    AC-136  TestSolveStrategies_SameCluesSameListUnderDilatedClock
    AC-137  TestSolveStrategies_GuessPresentWhenSearchBranched
    AC-138  TestSolveStrategies_GuessAbsentForLineSolvable
    AC-139  TestBatchGenerator_PersistsRealStrategiesUsedForRandomAndImage
    AC-140  TestExport_JSONCarriesStrategiesInOrder
    AC-141  TestPuzzleReview_FiltersListByStrategy
    AC-143  TestPuzzleReview_DetailShowsStrategiesInOrder

AC-142 is **not** here, deliberately. Its ``then`` says an unknown strategy
value is "refused ... and no puzzles are listed"; the shipped route
(``admin/app.py``, the ``strategy`` branch) reports the unknown value and then
*ignores* it, listing every puzzle — the CARD-066 status-filter shape, chosen
for the reason its comment gives. The AC and the code disagree about the
product, which is an owner's call and not a thing to settle by writing a test
to whichever one is easier to assert. See CARD-318's ``## Worktree notes``.

Relation to ``tests/test_strategies.py``
----------------------------------------
That file is CARD-072's and stays the broader coverage: ladder vocabulary,
ladder order, the clearing of a stale list, the CSV non-regression, the
substring-safety of the database filter. This file is narrower on purpose — it
pins the registry's exact wording so a reader of ``requirements.yml`` who
follows a ``test:`` ref lands on the criterion they just read. Where a sibling
there covers the same ground more broadly, the class below says so.
"""

from __future__ import annotations

import dataclasses
import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from nonogram import clues, export, solver
from nonogram.admin import puzzle_review
from nonogram.admin.batch_generator import BatchGenerator
from nonogram.admin.puzzle_review import PuzzleReviewService
from nonogram.export import json_export
from nonogram.limits import MAX_SIZE, MIN_SIZE
from nonogram.orchestrator import GenerationRequest, generate

GUESS = solver.STRATEGY_GUESS
FIXTURES = Path(__file__).parent / "fixtures"


# --------------------------------------------------------------------------
# Clue sets, measured rather than hoped for
# --------------------------------------------------------------------------
#
# Both are 20x20 — the extent AC-136 names — and both are uniquely solvable.
# They differ in the one fact FR-029's `guess` member keys on, which is why
# they are a pair and not one grid used twice:
#
#   _SETTLED_20  branch_nodes == 0, rungs ('simple_overlap',)   ~0.002s
#   _BRANCHED_20 branch_nodes == 74, rungs ('probe_contradiction',) ~0.1s
#
# The counts are asserted below rather than trusted: a solver change that made
# `_BRANCHED_20` line-solvable would otherwise turn AC-137 into a test that
# passes while checking nothing (its `given` would no longer hold), which is
# the precise failure mode this card exists to remove.


def _settled_grid() -> list[list[bool]]:
    """A 20x20 grid whose solve needs no branching at all."""
    return [[(row * MAX_SIZE + column) % 3 != 0 for column in range(20)] for row in range(20)]


def _branched_grid() -> list[list[bool]]:
    """A 20x20 grid that is uniquely solvable only after the search branches."""
    return [[(row + column) % 4 < 2 for column in range(20)] for row in range(20)]


def _solve(grid: list[list[bool]], **kwargs: object) -> solver.SolveResult:
    line_clues = clues.compute_clues(grid)
    return solver.solve(line_clues.rows, line_clues.columns, **kwargs)  # type: ignore[arg-type]


def _strategies_of(result: solver.SolveResult) -> tuple[str, ...]:
    """FR-029's list as the aggregate records it: the solve's ladder, plus
    ``guess`` exactly when the search branched (ADR-0025/R1).

    Written out here rather than imported from the orchestrator on purpose
    (G-5): the orchestrator's ``record_difficulty`` is the code under test for
    AC-137/AC-138, so re-deriving the expected value with it would assert
    nothing. This is the rule as FR-029's statement words it.
    """
    return tuple(result.signals.rungs) + ((GUESS,) if result.signals.branch_nodes > 0 else ())


class _DilatedClock:
    """A monotonic clock that reports elapsed time multiplied by ``factor``.

    The solver reads a clock in exactly one place — ``solver.propagate``'s
    deadline check — so substituting the ``time`` module there is the whole of
    "the host is slower". Modelled on ``tests/test_timeout.py``'s ``_FakeClock``
    and its ``_install_clock``, which is this suite's established way to make a
    clock an input rather than an accident.
    """

    START = 1000.0

    def __init__(self, factor: float) -> None:
        self.factor = factor
        self.reads = 0

    def monotonic(self) -> float:
        self.reads += 1
        # Each read advances the apparent clock by `factor` ticks, so a solve
        # that performs N deadline checks looks `factor` times slower.
        return self.START + self.reads * self.factor


def _install_clock(monkeypatch: pytest.MonkeyPatch, clock: _DilatedClock) -> _DilatedClock:
    from nonogram.solver import propagate as propagate_module

    monkeypatch.setattr(
        propagate_module, "time", SimpleNamespace(monotonic=clock.monotonic)
    )
    return clock


def _stored(service: PuzzleReviewService, strategies: list[str]) -> str:
    """One stored puzzle carrying ``strategies``.

    A solid block: uniquely solvable, so ``add_puzzle``'s CARD-080 gate
    passes, and cheap to solve. The same helper shape ``tests/test_strategies.py``
    uses, duplicated rather than imported — a test module is not an API.
    """
    grid = [[True] * MIN_SIZE for _ in range(MIN_SIZE)]
    return service.add_puzzle(
        grid=grid,
        clues_rows=[],
        clues_cols=[],
        width=MIN_SIZE,
        height=MIN_SIZE,
        theme="test",
        difficulty_score=10,
        difficulty_tier="easy",
        quality_score=50,
        recognizability="medium",
        strategies_used=strategies,
        batch_id=None,
        source_image="p.png",
    )


@pytest.fixture
def admin_app(monkeypatch: pytest.MonkeyPatch):
    """The real Flask admin, in-memory mode.

    ``DATABASE_URL`` is deleted rather than left ambient (CARD-109): with it
    set, ``create_app`` builds a database-backed admin against whatever is
    configured on the machine, and these tests would be measuring that instead.
    G-8: nothing here may reach the production ``nonogram_poc``.
    """
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TESTING", "true")
    from nonogram.admin import image_manager as image_manager_module
    from nonogram.admin.app import create_app

    image_manager_module._image_manager = None
    app = create_app()
    app.config["TESTING"] = True
    app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024
    with app.app_context():
        yield app


# ==========================================================================
# AC-135 — the list comes off the one solve that confirmed the puzzle
# ==========================================================================


class TestGenerate_StrategiesRecordedFromTheOneVerifyingSolve:
    """AC-135. The registry's ``given`` reads "a random-mode request at 20x20,
    density 40, seed 42". **That request does not generate**: measured on this
    branch it raises ``GenerationAbandoned`` after 30 attempts, and 20x20 at
    density 40 on other seeds raises ``SolverTimeout`` — the known-hard class
    ``CLAUDE.md`` warns about. The extent is corrected to 15x15 in
    ``requirements.yml`` with a note; the ``then`` is untouched and is what is
    asserted here.
    """

    REQUEST = GenerationRequest(mode="random", width=15, height=15, density=40, seed=42)

    def test_the_list_is_the_verifying_solves_own_ladder(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The recorded list is the *accepted candidate's* solve, not some
        other solve's — and the solver is entered once per candidate, never a
        second time for the same one (ADR-0013's no-re-entry rule, ADR-0029/R2).
        """
        observed: list[tuple[tuple[str, ...], int]] = []
        real = solver.solve

        def counting(*args: object, **kwargs: object) -> solver.SolveResult:
            result = real(*args, **kwargs)  # type: ignore[arg-type]
            observed.append((tuple(result.signals.rungs), result.signals.branch_nodes))
            return result

        from nonogram import orchestrator as orchestrator_module

        monkeypatch.setattr(orchestrator_module.solver, "solve", counting)
        puzzle = generate(self.REQUEST)

        assert observed, "the generator must have entered the solver at all"
        # The accepted candidate is the last one judged: `generate` returns as
        # soon as a candidate passes, so no solve happens after it. That is
        # what "exactly once for the accepted candidate" is observable as.
        rungs, branch_nodes = observed[-1]
        assert puzzle.strategies == rungs + ((GUESS,) if branch_nodes else ())

    def test_the_list_is_non_empty_and_drawn_only_from_the_enum(self) -> None:
        """Both halves of the ``then``'s first clause.

        ``tests/test_strategies.py::test_strategies_use_only_the_ladder_vocabulary``
        states the vocabulary half over twelve seeds; this states it for the
        criterion's own request, together with non-emptiness, which that file
        asserts separately.
        """
        puzzle = generate(self.REQUEST)

        assert puzzle.strategies, "a graded puzzle needed at least one rung"
        assert set(puzzle.strategies) <= set(solver.RUNG_ORDER) | {GUESS}


# ==========================================================================
# AC-136 — the same clues give the same list however slow the host looks
# ==========================================================================


class TestSolveStrategies_SameCluesSameListUnderDilatedClock:
    """AC-136. One fixed 20x20 clue set, solved twice: once under a clock
    reporting ordinary elapsed time and once under a clock reporting fifty
    times as much. The two lists must be identical element for element.

    This is the criterion EC-018's determinism half generalises, and it is the
    one that cannot be stated by re-solving alone: re-solving under the *same*
    clock shows repeatability, not clock-independence. The dilation is what
    makes "elapsed wall-clock time is never an input" (NFR-007, CON-014) an
    assertion rather than a hope.
    """

    #: A deadline no dilation in this test can reach, so the two solves differ
    #: in what the clock *says* and in nothing else. Without it the solve would
    #: not read a clock at all — measured: ``check_deadline`` returns at once
    #: when ``deadline is None``, so a deadline-less solve reads zero times and
    #: a dilated clock installed over it changes nothing. Stating AC-136 on a
    #: deadline-less solve would therefore have been vacuous.
    FAR_DEADLINE = _DilatedClock.START + 1e9

    def test_the_two_lists_are_identical_element_for_element(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        grid = _settled_grid()
        assert len(grid) == 20 and len(grid[0]) == 20, "AC-136's extent"

        with monkeypatch.context() as at_1x:
            ordinary = _install_clock(at_1x, _DilatedClock(factor=1.0))
            first = _solve(grid, deadline=self.FAR_DEADLINE).signals.rungs

        with monkeypatch.context() as at_50x:
            dilated = _install_clock(at_50x, _DilatedClock(factor=50.0))
            second = _solve(grid, deadline=self.FAR_DEADLINE).signals.rungs

        assert tuple(first) == tuple(second), (first, second)
        # Asserted, not assumed. If the clock were never read the two solves
        # would be the same solve and this would prove nothing — which is
        # exactly what happened on the first run of this test, before the
        # deadline was passed.
        assert ordinary.reads > 0, ordinary.reads
        assert dilated.reads > 0, dilated.reads
        # And the dilation really was 50x on the elapsed time each reported.
        assert dilated.monotonic() - dilated.START > 50 * (
            ordinary.monotonic() - ordinary.START
        ) / 2

    def test_the_list_is_also_stable_without_any_clock_substitution(self) -> None:
        """The control arm. Both solves above run against a fake clock, so a
        bug that only appears under the real one would hide. Solving twice on
        the real clock costs milliseconds for this grid and closes that gap.
        """
        grid = _settled_grid()

        assert tuple(_solve(grid).signals.rungs) == tuple(_solve(grid).signals.rungs)


# ==========================================================================
# AC-137 / AC-138 — `guess` tracks branching, and only branching
# ==========================================================================


class TestSolveStrategies_GuessPresentWhenSearchBranched:
    """AC-137. A uniquely solvable puzzle whose solve branched carries
    ``guess``.

    ``tests/test_strategies.py`` could only reach this half at the aggregate,
    by calling ``record_difficulty`` directly, because its docstring records
    that no random draw in the supported range was found whose solve branches.
    A **constructed** clue set reaches it through the real solver instead, so
    the ``given`` is a solve that genuinely branched rather than a hand-set
    count.
    """

    def test_a_branching_solve_names_a_guess(self) -> None:
        result = _solve(_branched_grid())

        # The `given`, asserted: unique, and the search branched.
        assert result.solution_count == 1, result.solution_count
        assert result.signals.branch_nodes >= 1, result.signals.branch_nodes

        assert GUESS in _strategies_of(result)

    def test_the_aggregate_records_the_guess_for_such_a_solve(self) -> None:
        """The same fact where FR-029 says the list is *recorded* — the one
        place the append happens (``orchestrator.record_difficulty``).
        """
        from nonogram import difficulty

        result = _solve(_branched_grid())
        puzzle = generate(
            GenerationRequest(mode="random", width=MIN_SIZE, height=MIN_SIZE, density=40, seed=7)
        )

        puzzle.record_difficulty(
            difficulty.score_difficulty(result.signals),
            result.signals.branch_nodes,
            result.signals.rungs,
        )

        assert GUESS in puzzle.strategies
        assert puzzle.strategies[-1] == GUESS, "a guess is not a rung; it sorts last"


class TestSolveStrategies_GuessAbsentForLineSolvable:
    """AC-138. A uniquely solvable puzzle that reached its solution with
    ``branch_nodes`` 0 does **not** carry ``guess``.

    The negative arm of the same rule, and the one a threshold on the score
    cannot recover (EC-015).
    """

    def test_a_settled_solve_names_no_guess(self) -> None:
        result = _solve(_settled_grid())

        assert result.solution_count == 1, result.solution_count
        assert result.signals.branch_nodes == 0, result.signals.branch_nodes

        assert GUESS not in _strategies_of(result)
        assert _strategies_of(result) == tuple(result.signals.rungs)

    def test_the_aggregate_records_no_guess_for_such_a_solve(self) -> None:
        puzzle = generate(
            GenerationRequest(mode="random", width=MIN_SIZE, height=MIN_SIZE, density=40, seed=7)
        )
        assert puzzle.branch_nodes == 0, "seed 7 at 10x10 is line-solvable"

        assert GUESS not in puzzle.strategies


# ==========================================================================
# AC-139 — both admin batch paths persist the real list
# ==========================================================================


class TestBatchGenerator_PersistsRealStrategiesUsedForRandomAndImage:
    """AC-139. Every stored row's ``strategies_used`` holds that puzzle's real
    non-empty list — never ``[]`` and never the sample
    ``['LineLogic', 'ConstraintProp']``.

    ``tests/test_strategies.py::test_a_random_batch_stores_the_strategies_of_every_puzzle``
    covers the random path. The **image** path is a different call site
    (``admin/app.py``'s ``generate_batch_puzzles``) that writes the same column
    from the same aggregate field, and nothing covered it: the two are asserted
    together here because the AC names both and a fix to one has never implied
    the other.

    Why the stored row is not enough, measured
    -----------------------------------------
    ``add_puzzle`` **derives** the list from its own uniqueness proof whenever
    the caller hands it an empty one. So a generator that passed ``[]`` still
    produces rows whose column holds a real non-empty list, and a row-only
    assertion cannot tell the two apart: mutants that replaced both call sites'
    ``list(puzzle.strategies)`` with ``[]`` left an all-row check **green**.
    The AC's words are "that puzzle's real ... list", so what has to be
    observed is the value the *generator handed over*, and both tests below
    spy on the hand-off as well as reading the row back.
    """

    SAMPLE = ["LineLogic", "ConstraintProp"]

    @staticmethod
    def _spy_on(service: PuzzleReviewService) -> list[object]:
        """Record the ``strategies_used`` every ``add_puzzle`` call is given.

        The store's fallback is a genuine safety net and is not being removed;
        it just has to stop hiding its callers.
        """
        handed_over: list[object] = []
        real = service.add_puzzle

        def spying(*args: object, **kwargs: object):
            handed_over.append(kwargs.get("strategies_used"))
            return real(*args, **kwargs)  # type: ignore[arg-type]

        service.add_puzzle = spying  # type: ignore[method-assign]
        return handed_over

    def _assert_row_is_a_real_list(self, row: dict) -> None:
        names = row["strategies_used"]
        assert names, row["id"]
        assert names != self.SAMPLE, row["id"]
        assert set(names) <= set(puzzle_review.STRATEGY_NAMES), names

    def test_a_random_batch_stores_a_real_list_for_every_row(self) -> None:
        store = PuzzleReviewService()
        handed_over = self._spy_on(store)
        generator = BatchGenerator(puzzle_review_service=store)

        # Ten is the smallest random batch the admin accepts (CARD-094).
        generator.create_batch(count=10, sizes=[MIN_SIZE], source="random")
        stored = list(store.puzzles.values())

        assert len(stored) == 10, len(stored)
        for row in stored:
            self._assert_row_is_a_real_list(row)

        # The generator's own contribution, not the store's fallback.
        assert len(handed_over) == 10, handed_over
        for names in handed_over:
            assert names, "the batch generator handed the store an empty list"
            assert set(names) <= set(puzzle_review.STRATEGY_NAMES), names

    def test_an_image_batch_stores_a_real_list_for_every_row(
        self, admin_app
    ) -> None:
        """The image half, through the real upload-then-generate flow.

        Driven the way ``tests/test_admin_image_uniqueness.py`` drives it,
        because the column is written inside a Flask route and there is no
        narrower seam to call.
        """
        handed_over = self._spy_on(admin_app.puzzle_review_service)
        client = admin_app.test_client()
        with open(FIXTURES / "bird1.jpg", "rb") as handle:
            upload = client.post(
                "/batch/from-images",
                data={"image_files": [(handle, "bird1.jpg")]},
                content_type="multipart/form-data",
            )
        assert upload.status_code == 302, upload.data

        response = client.post("/batch/generate-puzzles", data={}, follow_redirects=False)
        assert response.status_code == 302, response.data
        match = re.search(r"/batch/([^/]+)/generated-puzzles", response.location or "")
        assert match, response.location

        stored = admin_app.batch_generator.get_batch_puzzles(
            match.group(1), offset=0, limit=100
        )
        assert stored, "the image batch stored no puzzle, so the column is untested"
        for row in stored:
            self._assert_row_is_a_real_list(row)

        # The route's own contribution, for the reason in the class docstring.
        assert handed_over, "the image route never reached add_puzzle"
        for names in handed_over:
            assert names, "the image route handed the store an empty list"
            assert set(names) <= set(puzzle_review.STRATEGY_NAMES), names


# ==========================================================================
# AC-140 — the JSON payload carries the list, in order
# ==========================================================================


class TestExport_JSONCarriesStrategiesInOrder:
    """AC-140. A puzzle whose strategies list is
    ``[simple_overlap, line_dp, guess]``, exported as JSON and decoded back:
    the payload's ``strategies`` array equals the list in the same order.

    The literal triple matters and is why this is not simply
    ``tests/test_strategies.py::test_export_json_carries_strategies_and_binarisation``:
    that test compares against whatever a random puzzle produced, so it cannot
    fail on an order bug (both sides would be reordered together), and `guess`
    is not reachable through ``generate`` at all. A fixed, ordered,
    three-member list with ``guess`` last is the only shape that pins order.
    """

    STRATEGIES = ("simple_overlap", "line_dp", GUESS)

    def _payload(self) -> export.ExportPayload:
        grid = [[True] * MIN_SIZE for _ in range(MIN_SIZE)]
        line_clues = clues.compute_clues(grid)
        return export.ExportPayload(
            grid=grid,
            row_clues=line_clues.rows,
            column_clues=line_clues.columns,
            seed=42,
            mode="random",
            width=MIN_SIZE,
            height=MIN_SIZE,
            density=100,
            strategies=self.STRATEGIES,
            binarisation=None,
        )

    def test_the_written_array_is_the_list_in_order(self, tmp_path) -> None:
        path = tmp_path / "p.json"
        json_export.render(self._payload(), path)

        document = json.loads(path.read_text())

        assert document["strategies"] == list(self.STRATEGIES)

    def test_the_decoded_payload_is_the_list_in_order(self, tmp_path) -> None:
        """The round trip, which is the half FR-012 is about."""
        path = tmp_path / "p.json"
        json_export.render(self._payload(), path)

        decoded = json_export.parse(json.loads(path.read_text()))

        assert decoded.strategies == self.STRATEGIES

    def test_a_reordered_list_is_a_different_payload(self, tmp_path) -> None:
        """Order is load-bearing, stated as a discrimination: the same three
        names in a different order must produce a different document.

        What this does and does not catch, **measured** rather than claimed.
        It reds on a renderer that drops the key (mutant M3). It does **not**
        red on a renderer that sorts (mutant M4), because
        ``sorted(reversed(STRATEGIES))`` is ``reversed(STRATEGIES)`` for this
        fixture — the sorting mutant is caught one test up, by
        ``test_the_written_array_is_the_list_in_order``, which M4 does red.
        So the pair is what pins order, not either test alone; this one's own
        job is a renderer that emits a constant list whatever it is handed.
        """
        reversed_payload = dataclasses.replace(
            self._payload(), strategies=tuple(reversed(self.STRATEGIES))
        )
        path = tmp_path / "r.json"
        json_export.render(reversed_payload, path)

        document = json.loads(path.read_text())

        assert document["strategies"] == list(reversed(self.STRATEGIES))
        assert document["strategies"] != list(self.STRATEGIES)


# ==========================================================================
# AC-141 — the puzzle list filters by strategy
# ==========================================================================


class TestPuzzleReview_FiltersListByStrategy:
    """AC-141. An admin review holding 3 puzzles whose lists contain ``guess``
    and 4 whose lists do not; filtered by strategy ``guess``, exactly the 3 are
    listed.

    ``tests/test_strategies.py::test_the_puzzle_list_filters_by_strategy``
    states the same rule over one puzzle of each kind. The registry's counts
    are kept here because an off-by-one in the filter — returning the first
    match, or every row once any row matches — passes a 1-and-1 corpus and
    fails this one.
    """

    def test_exactly_the_three_guessing_puzzles_are_listed(self) -> None:
        service = PuzzleReviewService()
        guessing = {
            _stored(service, ["simple_overlap", GUESS]),
            _stored(service, ["line_dp", GUESS]),
            _stored(service, ["simple_overlap", "line_dp", "probe_contradiction", GUESS]),
        }
        plain = {
            _stored(service, ["simple_overlap"]),
            _stored(service, ["line_dp"]),
            _stored(service, ["probe_contradiction"]),
            _stored(service, ["simple_overlap", "line_dp"]),
        }
        assert len(guessing) == 3 and len(plain) == 4, "the `given`'s corpus"

        response = service.filter_puzzles(
            puzzle_review.PuzzleFilter(strategy=GUESS, limit=50)
        )
        listed = {row["id"] for row in response.puzzles}

        assert listed == guessing
        assert not listed & plain


# ==========================================================================
# AC-143 — the detail page shows the list in order
# ==========================================================================


class TestPuzzleReview_DetailShowsStrategiesInOrder:
    """AC-143. A stored puzzle whose list is ``[line_dp, probe_contradiction]``:
    its admin review detail page shows ``line_dp`` followed by
    ``probe_contradiction``, in that order.

    ``tests/test_admin_rename_strategies_batches.py::test_the_generated_puzzles_cards_show_the_strategies``
    asserts the names are *present* on this page; it cannot fail on order,
    because it checks one name. The order is the whole of AC-143, so it is
    asserted as the position of one rendered name relative to the other.
    """

    STRATEGIES = ["line_dp", "probe_contradiction"]

    def test_the_rendered_page_shows_them_in_the_stored_order(self, admin_app) -> None:
        batch_id = admin_app.batch_generator.create_batch(
            count=1, sizes=[MIN_SIZE], theme="image", source="images", quality_filter=0
        )
        puzzle_id = _stored(admin_app.puzzle_review_service, list(self.STRATEGIES))
        admin_app.puzzle_review_service.puzzles[puzzle_id]["batch_id"] = batch_id

        body = admin_app.test_client().get(
            f"/batch/{batch_id}/generated-puzzles"
        ).get_data(as_text=True)

        first = body.find('data-strategy="line_dp"')
        second = body.find('data-strategy="probe_contradiction"')
        assert first != -1, "line_dp is not on the page at all"
        assert second != -1, "probe_contradiction is not on the page at all"
        assert first < second, (first, second)

    def test_the_detail_api_carries_them_in_the_stored_order(self, admin_app) -> None:
        """The same list through the JSON the page's detail panel reads, which
        is where an order bug would be introduced once rather than per
        template.
        """
        puzzle_id = _stored(admin_app.puzzle_review_service, list(self.STRATEGIES))

        data = admin_app.test_client().get(
            f"/api/puzzle/{puzzle_id}/details"
        ).get_json()

        assert [entry["name"] for entry in data["strategies"]] == self.STRATEGIES
