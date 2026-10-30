"""FR-029's two engineering constraints, as properties over a seeded corpus.

CARD-318. ``requirements.yml`` named these two criteria

    EC-017  PropertyTest_SolveStrategies_GuessIffSearchBranched
    EC-018  PropertyTest_SolveStrategies_PureFunctionOfCluesAndPreservedEndToEnd

and no definition of either name existed anywhere in ``tests/``. They are
written here as

    EC-017  TestPropertySolveStrategies_GuessIffSearchBranched
    EC-018  TestPropertySolveStrategies_PureFunctionOfCluesAndPreservedEndToEnd

and ``requirements.yml`` is re-pointed at those names. The rename is not
cosmetic. ``pyproject.toml`` leaves ``python_classes`` at pytest's default,
``Test*``, so a class called ``PropertyTest_...`` is **silently never
collected** — no skip, no error, a green total. The registry's convention of
naming property tests ``PropertyTest_*`` is therefore unsatisfiable by any
class that actually runs; the ~40 sibling refs that use it resolve only because
the validator's check is a text search and the name appears in a module
docstring. See CARD-318's ``## Worktree notes``.

No ``hypothesis`` (ADR-0006/R1, ``CLAUDE.md``): the corpora below are built by
hand with stdlib ``random.Random`` and with structured families, and each test
asserts its own minimum case count — per arm where a property has two arms —
so the corpus cannot silently shrink to nothing and keep passing.
"""

from __future__ import annotations

import json
import random
import time
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from nonogram import clues, difficulty, export, solver
from nonogram.admin import regrade
from nonogram.admin.puzzle_review import PuzzleReviewService
from nonogram.errors import SolverTimeout
from nonogram.export import json_export
from nonogram.limits import MAX_SIZE, MIN_SIZE
from nonogram.orchestrator import GenerationRequest, generate

GUESS = solver.STRATEGY_GUESS

#: Per-solve budget for a corpus member. The supported range contains a
#: known-hard class (``CLAUDE.md``): random mid-density grids near
#: ``MAX_SIZE`` can take seconds, and two of the structured family below do.
#: A member that overruns is *counted and dropped*, never silently skipped —
#: the floors at the end of each test are what keep that honest.
BUDGET_SECONDS = 0.25


# --------------------------------------------------------------------------
# The corpus
# --------------------------------------------------------------------------
#
# Two families, because one of them cannot reach half of EC-017:
#
#   * seeded random grids — measured on this branch, 162 of 300 uniquely
#     solvable and **none** of them branched. ``tests/test_strategies.py``
#     records the same finding ("no random draw in the supported range was
#     found whose solve needs to branch"). This family feeds the settled arm.
#   * a structured stripe family, (row + column + offset) mod k — measured
#     15 branched / 58 settled / 5 over budget. This is the only family found
#     that reaches the branched arm at all.
#
# Both are needed and the floors below are stated per arm, so a change that
# made the branched arm unreachable fails the test instead of quietly
# reducing it to the settled half.


def _stripe_grids() -> list[list[list[bool]]]:
    """The structured family: the one that branches."""
    grids = []
    for side in range(8, MAX_SIZE - 9):
        for modulus in (2, 3, 4, 5, 6, 7):
            for offset in (0, 1):
                grids.append(
                    [
                        [(row + column + offset) % modulus < max(1, modulus // 2) for column in range(side)]
                        for row in range(side)
                    ]
                )
    return grids


def _random_grids(seed: int, count: int) -> list[list[list[bool]]]:
    """The seeded family: broad, and reliably settled."""
    rng = random.Random(seed)
    grids = []
    for _ in range(count):
        side = rng.choice((MIN_SIZE - 2, MIN_SIZE, MIN_SIZE + 2, MIN_SIZE + 5))
        density = rng.choice((0.3, 0.4, 0.5, 0.6, 0.7))
        grids.append([[rng.random() < density for _ in range(side)] for _ in range(side)])
    return grids


def _signals_of(grid: list[list[bool]]) -> solver.SolveSignals | None:
    """One solve of ``grid``'s clues, or ``None`` if it was not a usable case.

    ``None`` means either "not uniquely solvable" — EC-017 and EC-018 are both
    stated over *uniquely solvable* puzzles, so such a grid is outside the
    property — or "over budget", which is a measurement limit and not a fact
    about the property. Both are counted by the callers.
    """
    line_clues = clues.compute_clues(grid)
    try:
        result = solver.solve(
            line_clues.rows, line_clues.columns, deadline=time.monotonic() + BUDGET_SECONDS
        )
    except SolverTimeout:
        return None
    if result.solution_count != 1:
        return None
    return result.signals


def _the_rule(signals: solver.SolveSignals) -> tuple[str, ...]:
    """FR-029's list, written from the requirement's own words.

    G-5's independent second implementation. The production code has two
    derivations of this rule — ``orchestrator.record_difficulty`` and
    ``admin.regrade._strategies_used`` — and both are asserted against this
    one rather than against each other alone, because two implementations that
    drifted together would agree and still be wrong.

    FR-029: "the ORDERED list of solving strategies its verifying solve
    required ... `guess` is present if and only if the search branched
    (branch_nodes >= 1)".
    """
    return tuple(signals.rungs) + ((GUESS,) if signals.branch_nodes >= 1 else ())


@pytest.fixture(scope="module")
def aggregate():
    """One cheap generated puzzle, reused as the aggregate under test.

    ``record_difficulty`` only stores what it is handed, so the same aggregate
    can be asked about every corpus member in turn — which is how
    ``tests/test_strategies.py`` reaches the branching half too. Generating one
    per member would cost a solve each and measure nothing extra.
    """
    return generate(
        GenerationRequest(mode="random", width=MIN_SIZE, height=MIN_SIZE, density=40, seed=7)
    )


def _sqlite_scope(tmp_path):
    """A session factory over a throwaway SQLite file.

    G-8: this card must not reach the production database. The live admin runs
    on ``nonogram_poc``; a DB-mode test that reads ``DATABASE_URL`` would
    silently skip when ``nonogram_test`` is absent (G-7) and prove nothing, so
    the persistence arm of EC-018 is pinned to a real SQLite file instead.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from nonogram.db.models import Base

    engine = create_engine(f"sqlite:///{tmp_path / 'strategies.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)

    @contextmanager
    def scope():
        session = factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    return scope


class _DilatedClock:
    """A monotonic clock reporting ``factor`` times the elapsed time."""

    START = 1000.0

    def __init__(self, factor: float) -> None:
        self.factor = factor
        self.reads = 0

    def monotonic(self) -> float:
        self.reads += 1
        return self.START + self.reads * self.factor


# ==========================================================================
# EC-017
# ==========================================================================


class TestPropertySolveStrategies_GuessIffSearchBranched:
    """EC-017 (``PropertyTest_SolveStrategies_GuessIffSearchBranched``).

    For any uniquely solvable puzzle, ``guess`` is in its strategies list if
    and only if the verifying solve's ``branch_nodes`` is greater than zero —
    the list reports the solve that happened, never a threshold on the score
    (the same fact EC-015 states for the requires-guessing attribute).

    Both arms are asserted to be populated. That is the whole point: the
    *settled* arm is reachable from a random corpus and the *branched* arm is
    not, so a property test built only from random draws would assert the
    biconditional while never once observing it fail to hold trivially. A
    mutant that never appended ``guess`` passes such a test.
    """

    #: Floors, set below the measured counts (15 branched / 58 settled over
    #: the stripe family, plus 162 settled over 300 random draws) with room
    #: for solver-timing variation, and high enough that losing a family
    #: fails here rather than passing quietly.
    MIN_BRANCHED = 8
    MIN_SETTLED = 40

    def test_guess_is_present_exactly_when_the_search_branched(self, aggregate) -> None:
        branched = settled = 0
        unusable = 0

        for grid in _stripe_grids() + _random_grids(seed=11, count=120):
            signals = _signals_of(grid)
            if signals is None:
                unusable += 1
                continue

            # Three derivations of the same list: the requirement's words, and
            # the two the production code holds independently of each other.
            expected = _the_rule(signals)
            from_regrade = regrade._strategies_used(signals.rungs, signals.branch_nodes)
            aggregate.record_difficulty(
                difficulty.score_difficulty(signals), signals.branch_nodes, signals.rungs
            )
            from_aggregate = aggregate.strategies

            assert from_regrade == expected, (from_regrade, expected)
            assert from_aggregate == expected, (from_aggregate, expected)

            # The biconditional itself, on each derivation.
            did_branch = signals.branch_nodes >= 1
            assert (GUESS in from_aggregate) is did_branch, (
                signals.branch_nodes,
                from_aggregate,
            )
            assert (GUESS in from_regrade) is did_branch, (
                signals.branch_nodes,
                from_regrade,
            )

            if did_branch:
                branched += 1
                assert from_aggregate[-1] == GUESS, from_aggregate
            else:
                settled += 1
                assert GUESS not in from_aggregate, from_aggregate

        # Asserted per arm, not merely produced. A corpus that reached only
        # the settled arm would satisfy the biconditional vacuously on the
        # half that matters.
        assert branched >= self.MIN_BRANCHED, (branched, unusable)
        assert settled >= self.MIN_SETTLED, (settled, unusable)

    def test_the_list_never_names_guess_without_the_count_to_back_it(self) -> None:
        """The same rule from the other side, over hand-set counts rather than
        real solves — so the branched arm is reached for every ladder shape and
        not only the shapes the stripe family happens to produce.

        ``branch_nodes`` of 0 and 1 are the only two values the rule
        distinguishes, and 1 is the boundary ADR-0025 keys on.
        """
        ladders = [
            (),
            ("simple_overlap",),
            ("line_dp",),
            ("simple_overlap", "line_dp"),
            ("simple_overlap", "line_dp", "probe_contradiction"),
        ]
        checked = 0

        for ladder in ladders:
            for branch_nodes in (0, 1, 2, 74):
                recorded = regrade._strategies_used(ladder, branch_nodes)

                assert (GUESS in recorded) is (branch_nodes >= 1), (ladder, branch_nodes)
                assert tuple(name for name in recorded if name != GUESS) == ladder
                checked += 1

        assert checked == len(ladders) * 4 == 20, checked


# ==========================================================================
# EC-018
# ==========================================================================


class TestPropertySolveStrategies_PureFunctionOfCluesAndPreservedEndToEnd:
    """EC-018 (``PropertyTest_SolveStrategies_PureFunctionOfCluesAndPreservedEndToEnd``).

    For any clue set, the strategies list is a pure function of the clues:
    repeated solves of the same clues yield the same ordered list, elapsed
    wall-clock time is never an input to it (NFR-007, CON-014), and the list
    the aggregate records, the DB row stores and the JSON export carries are
    the same list — for every extent and every solve, not only the measured
    examples.

    Three claims, three tests, because a single test short-circuits at its
    first failing assert and one ``FAILED`` line would say nothing about the
    arms that never ran.
    """

    MIN_REPEATED = 30
    MIN_DILATED = 12
    MIN_END_TO_END = 6

    def test_repeated_solves_of_the_same_clues_give_the_same_ordered_list(self) -> None:
        """The purity half, on the real clock."""
        checked = 0

        for grid in _stripe_grids()[:40] + _random_grids(seed=23, count=40):
            line_clues = clues.compute_clues(grid)
            first = _signals_of(grid)
            if first is None:
                continue
            try:
                second = solver.solve(
                    line_clues.rows,
                    line_clues.columns,
                    deadline=time.monotonic() + BUDGET_SECONDS,
                )
            except SolverTimeout:
                continue

            assert _the_rule(first) == _the_rule(second.signals)
            # Ordered, not merely equal as a set: a derivation that sorted the
            # ladder would pass a set comparison.
            assert tuple(first.rungs) == tuple(second.signals.rungs)
            checked += 1

        assert checked >= self.MIN_REPEATED, checked

    def test_a_fifty_times_slower_clock_changes_no_list(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The "elapsed time is never an input" half, generalised past AC-136's
        single 20x20 clue set to every extent in the corpus.

        A deadline is passed on purpose. Without one the solver reads no clock
        at all — ``check_deadline`` returns immediately when ``deadline is
        None`` — so a dilated clock installed over a deadline-less solve is
        not an input to anything and the property would hold vacuously. The
        deadline here is far enough away that neither clock reaches it, so the
        two solves differ in what the clock *says* and in nothing else.
        """
        from nonogram.solver import propagate as propagate_module

        far = _DilatedClock.START + 1e9
        checked = 0
        reads_seen = 0

        for grid in _stripe_grids()[:30]:
            line_clues = clues.compute_clues(grid)
            lists = []
            for factor in (1.0, 50.0):
                clock = _DilatedClock(factor=factor)
                with monkeypatch.context() as patched:
                    patched.setattr(
                        propagate_module, "time", SimpleNamespace(monotonic=clock.monotonic)
                    )
                    try:
                        result = solver.solve(
                            line_clues.rows, line_clues.columns, deadline=far
                        )
                    except SolverTimeout:
                        lists = []
                        break
                if result.solution_count != 1:
                    lists = []
                    break
                lists.append(_the_rule(result.signals))
                reads_seen += clock.reads

            if len(lists) != 2:
                continue
            assert lists[0] == lists[1], lists
            checked += 1

        assert checked >= self.MIN_DILATED, checked
        # The clock was genuinely consulted; otherwise the dilation is a
        # no-op and this test is an expensive tautology.
        assert reads_seen > 0, reads_seen

    def test_the_aggregate_the_stored_row_and_the_export_hold_one_list(
        self, tmp_path
    ) -> None:
        """The end-to-end half: one list, three places, every extent.

        The store runs against a real SQLite file rather than its in-memory
        mode, because "the DB row stores it" is a claim about a column and the
        in-memory mode has no column (G-7/G-8).
        """
        service = PuzzleReviewService(session_factory=_sqlite_scope(tmp_path))
        checked = 0

        for side in (MIN_SIZE, MIN_SIZE + 2, MIN_SIZE + 5, MIN_SIZE + 8):
            for seed in (3, 7):
                try:
                    puzzle = generate(
                        GenerationRequest(
                            mode="random", width=side, height=side, density=40, seed=seed
                        )
                    )
                except Exception:
                    # An abandoned draw has no grade and so no list: outside
                    # the property, and counted by the floor below.
                    continue

                assert puzzle.grid is not None and puzzle.clues is not None
                from_aggregate = puzzle.strategies
                assert from_aggregate, "a graded puzzle names at least one rung"

                puzzle_id = service.add_puzzle(
                    grid=puzzle.grid,
                    clues_rows=list(puzzle.clues.rows),
                    clues_cols=list(puzzle.clues.columns),
                    width=side,
                    height=side,
                    theme="ec018",
                    difficulty_score=10,
                    difficulty_tier="easy",
                    quality_score=50,
                    recognizability="medium",
                    strategies_used=list(from_aggregate),
                    batch_id=None,
                    source_image=None,
                )
                from_row = tuple(service.get_puzzle(puzzle_id)["strategies_used"])

                path = tmp_path / f"p-{side}-{seed}.json"
                json_export.render(
                    export.ExportPayload(
                        grid=puzzle.grid,
                        row_clues=puzzle.clues.rows,
                        column_clues=puzzle.clues.columns,
                        seed=puzzle.seed,
                        mode=puzzle.mode,
                        width=side,
                        height=side,
                        density=puzzle.request.density,
                        strategies=from_aggregate,
                        binarisation=puzzle.binarisation,
                    ),
                    path,
                )
                from_export = tuple(json.loads(path.read_text())["strategies"])
                round_tripped = json_export.parse(json.loads(path.read_text())).strategies

                assert from_row == from_aggregate, (from_row, from_aggregate)
                assert from_export == from_aggregate, (from_export, from_aggregate)
                assert round_tripped == from_aggregate
                checked += 1

        assert checked >= self.MIN_END_TO_END, checked
