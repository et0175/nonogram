"""FR-029 — the strategies a puzzle's one verifying solve needed.

    AC-1  TestStrategies_ReportsWhatTheSolveNeeded
          -> test_strategies_reports_what_the_solve_needed*
    AC-2  TestStrategies_DeterministicForAClueSet
          -> test_strategies_are_deterministic_for_a_clue_set

What this file is about. A puzzle book has to say what a solver must know to
finish a puzzle, and the admin review has to filter on it. The list is not
computed here and not computed twice: CARD-073 put the ladder the deciding
solve climbed on ``SolveSignals.rungs`` (ADR-0029/R2), and this card's whole
mechanism is to carry that onto the aggregate with ``guess`` appended when the
search branched — which ADR-0025 keys on ``branch_nodes``, not on a rung.

So the tests below are mostly about *wiring and vocabulary*, and they say so:
what is worth pinning is that there is exactly one derivation, that ``guess``
tracks branching rather than a threshold, and that a new candidate clears the
old answer. The ladder's own correctness belongs to CARD-073's tests.
"""

from __future__ import annotations

import json
import random
from contextlib import contextmanager

import pytest

from nonogram import clues, difficulty, export, solver
from nonogram.admin import puzzle_review
from nonogram.admin.batch_generator import BatchGenerator
from nonogram.admin.puzzle_review import MockGenerator, PuzzleReviewService
from nonogram.export import csv_export, json_export
from nonogram.errors import GenerationAbandoned
from nonogram import orchestrator
from nonogram.orchestrator import GenerationRequest, generate

GUESS = "guess"


def _puzzle(**overrides: object):
    fields: dict[str, object] = {
        "mode": "random",
        "width": 10,
        "height": 10,
        "density": 40,
        "seed": 7,
    }
    fields.update(overrides)
    return generate(GenerationRequest(**fields))  # type: ignore[arg-type]


def _sqlite_scope(tmp_path):
    """A session factory over a throwaway SQLite file, as the admin tests use."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from nonogram.db.models import Base

    engine = create_engine(f"sqlite:///{tmp_path / 'admin.db'}")
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


def _payload(puzzle) -> export.ExportPayload:
    """The payload the orchestrator would hand a renderer for this puzzle."""
    assert puzzle.grid is not None and puzzle.clues is not None
    return export.ExportPayload(
        grid=puzzle.grid,
        row_clues=puzzle.clues.rows,
        column_clues=puzzle.clues.columns,
        seed=puzzle.seed,
        mode=puzzle.mode,
        width=puzzle.request.width,
        height=puzzle.request.height,
        density=puzzle.request.density,
        strategies=puzzle.strategies,
        binarisation=puzzle.binarisation,
    )


def _verdict(grid: list[list[bool]]) -> solver.SolveResult:
    line_clues = clues.compute_clues(grid)
    return solver.solve(line_clues.rows, line_clues.columns)


# --------------------------------------------------------------------------
# AC-1 — the list is the solve's own ladder, plus `guess` when it branched
# --------------------------------------------------------------------------


def test_strategies_reports_what_the_solve_needed() -> None:
    """The aggregate carries the rungs the deciding solve actually used.

    Not a re-derivation and not a second opinion: the value is
    ``signals.rungs`` for the solve that confirmed this very grid, which is
    what ADR-0029/R2 means by "one derivation from the one verifying solve".
    Asserted by re-solving the finished puzzle's own clues and comparing —
    the same grid must give the same ladder, because nothing else in the
    pipeline is allowed to have an opinion about it.
    """
    puzzle = _puzzle()

    assert puzzle.grid is not None
    assert puzzle.strategies == tuple(_verdict(puzzle.grid).signals.rungs) + (
        (GUESS,) if _verdict(puzzle.grid).signals.branch_nodes else ()
    )
    assert puzzle.strategies, "a solved puzzle needed at least one rung"


def test_strategies_use_only_the_ladder_vocabulary() -> None:
    """Four names, and no fifth invented here.

    ``cross_line`` was in this card's first draft and is *not* a strategy:
    ADR-0029 removed it from the ladder as an artefact of sweep order — a
    puzzle and its transpose scored differently under it. The shipped
    vocabulary is ``solver.RUNG_ORDER`` plus ``guess``.
    """
    permitted = set(solver.RUNG_ORDER) | {GUESS}

    for seed in range(12):
        puzzle = _puzzle(seed=seed)
        assert set(puzzle.strategies) <= permitted, puzzle.strategies


def test_strategies_list_the_rungs_in_ladder_order_with_guess_last() -> None:
    """Order is the ladder's, so "the hardest thing this needs" is the last
    entry — which is what a book's difficulty note wants to read.

    ``guess`` sorts last because it is not a rung at all: it is the search
    admitting the ladder ran out.
    """
    rank = {name: index for index, name in enumerate(solver.RUNG_ORDER)}
    rank[GUESS] = len(rank)

    for seed in range(12):
        strategies = _puzzle(seed=seed).strategies
        positions = [rank[name] for name in strategies]
        assert positions == sorted(positions), strategies
        assert len(set(strategies)) == len(strategies), strategies


def test_strategies_name_a_guess_exactly_when_the_search_branched() -> None:
    """AC-1's own words, and ADR-0025/R1: ``guess`` is present iff the solve
    branched. A threshold on the score cannot recover this — EC-015 — so it
    has to travel as its own fact.
    """
    seen_both = {True: 0, False: 0}

    for seed in range(40):
        puzzle = _puzzle(seed=seed, width=12, height=12, density=45)
        assert puzzle.branch_nodes is not None
        branched = puzzle.branch_nodes > 0
        assert (GUESS in puzzle.strategies) is branched, (
            seed, puzzle.branch_nodes, puzzle.strategies
        )
        seen_both[branched] += 1

    assert seen_both[False], "the corpus must contain a puzzle that never branched"


def test_a_branching_solve_appends_guess_and_a_settled_one_does_not() -> None:
    """The append rule itself, at the level where it lives.

    The corpus test above checks the *iff* over real runs, but it cannot check
    the branching half: no random draw in the supported range was found whose
    solve needs to branch — line logic and probing finish them all — so
    ``guess`` is not reachable through ``generate`` today. Recording the rule
    only through runs would therefore assert half of it, and a mutant that
    never appended ``guess`` passed every other test in this file.

    So it is exercised directly on the aggregate, which is the one place the
    append happens. ``branch_nodes`` of 1 is what ADR-0025 keys ``Tier.GUESS``
    on; the score is held constant across the pair so the tier is the only
    thing that moves.
    """
    settled = _puzzle()
    ladder = ("simple_overlap", "line_dp")

    settled.record_difficulty(12.0, 0, ladder)
    assert settled.strategies == ladder

    settled.record_difficulty(12.0, 1, ladder)
    assert settled.strategies == (*ladder, GUESS)

    # The tier does not move with it — since CARD-098 branching is a strategy
    # and the tier is the score's band, so both records above classify alike.
    assert settled.difficulty_tier is difficulty.classify(12.0)


def test_strategies_are_cleared_when_a_new_candidate_arrives() -> None:
    """A rejected candidate's answer must not survive onto the next one.

    The aggregate is reused across attempts, so every judged fact is reset by
    ``record_candidate`` — the score, the counts, the masks. A stale
    strategies list would be the worst of them: it reads as a fact about the
    puzzle that was exported, and would be a fact about one that was thrown
    away.
    """
    puzzle = _puzzle()
    assert puzzle.strategies

    assert puzzle.grid is not None
    puzzle.record_candidate([row[:] for row in puzzle.grid])

    assert puzzle.strategies == ()


# --------------------------------------------------------------------------
# AC-2 — deterministic for a clue set
# --------------------------------------------------------------------------


def test_strategies_are_deterministic_for_a_clue_set() -> None:
    """Same clues, same list — on every run and every machine.

    The ladder comes from the solve's deductions, which are a function of the
    clue set alone; nothing in it reads a clock (CON-014, EC-018). Stated over
    a seeded corpus rather than one puzzle, because "deterministic" is a claim
    about every clue set and a single example could be luck.
    """
    rng = random.Random(4)
    checked = 0

    for _ in range(25):
        size = rng.choice((10, 12, 15))
        density = rng.choice((35, 45, 55))
        try:
            first = _puzzle(
                seed=rng.randrange(10_000), width=size, height=size, density=density
            )
        except GenerationAbandoned:
            # A draw the retry budget could not make unique. It has no grade
            # and so no strategies; skipping it keeps the corpus honest
            # instead of steering the sizes towards the easy ones.
            continue
        assert first.grid is not None
        again = _verdict(first.grid).signals.rungs

        assert tuple(again) == tuple(
            name for name in first.strategies if name != GUESS
        )
        checked += 1

    # Asserted, not merely produced (CLAUDE.md's corpus rule): a run where
    # every draw was abandoned would otherwise pass having checked nothing.
    assert checked >= 20, checked


# --------------------------------------------------------------------------
# AC-3 — the JSON export carries both fields, additively
# --------------------------------------------------------------------------


def test_export_json_carries_strategies_and_binarisation(tmp_path) -> None:
    """AC-3: the two fields reach the file and come back.

    Both ride at the **current** ``SCHEMA_VERSION``. JSON's decoder reads the
    fields it names and ignores the rest, so a field can be added without
    invalidating a document written before it existed — which is why this
    card's owner chose JSON-only over a version bump that would have made
    every previously exported file undecodable (ADR-0023/R2 gives a decoder no
    best-effort read of another version).
    """
    puzzle = _puzzle()
    path = tmp_path / "p.json"
    payload = _payload(puzzle)
    json_export.render(payload, path)

    document = json.loads(path.read_text())
    assert document["version"] == json_export.SCHEMA_VERSION
    assert document["strategies"] == list(puzzle.strategies)
    assert document["binarisation"] is None, "a random puzzle binarised nothing"

    decoded = json_export.parse(document)
    assert decoded.strategies == puzzle.strategies
    assert decoded.binarisation is None


def test_export_json_still_reads_a_document_written_before_these_fields(
    tmp_path,
) -> None:
    """The other half of "additive": an older file must still decode.

    A document written by a build that had never heard of ``strategies``
    carries neither key and the same ``version``. If the decoder demanded
    them, keeping the version fixed would have been a lie and the owner's
    choice would have bought nothing.
    """
    document = json_export.document(_payload(_puzzle()))
    del document["strategies"]
    del document["binarisation"]

    decoded = json_export.parse(document)

    assert decoded.strategies == ()
    assert decoded.binarisation is None


def test_export_csv_is_untouched_by_this_card(tmp_path) -> None:
    """Guardrail G-7, as a check rather than a promise.

    CSV's decoder rejects unknown keys and refuses any version but its own, so
    the fields could not be added there without a bump. The version is pinned
    here, and the rendered text is checked to carry neither field — so a later
    edit that "just adds one column" fails this instead of silently
    invalidating every CSV the owner has already exported.
    """
    path = tmp_path / "p.csv"
    csv_export.render(_payload(_puzzle()), path)
    text = path.read_text()

    assert csv_export.SCHEMA_VERSION == 2
    assert "strategies" not in text
    assert "binarisation" not in text
    assert csv_export.decode(text).strategies == ()


def test_a_real_export_run_writes_the_strategies_it_used(tmp_path) -> None:
    """End to end, through ``export_puzzle`` rather than a hand-built payload.

    The test above proves the renderer writes what it is given; this proves the
    orchestrator gives it the right thing. The two are worth separating because
    the payload has eleven fields and the interesting failure — carrying a
    default where a real value existed — passes every renderer test.
    """
    puzzle = _puzzle(export_formats=["json"], out=tmp_path)

    orchestrator.export_puzzle(puzzle)

    written = next(tmp_path.glob("*.json"))
    document = json.loads(written.read_text())
    assert document["strategies"] == list(puzzle.strategies)
    assert document["strategies"], "a graded puzzle names at least one rung"
    assert document["binarisation"] is None


# --------------------------------------------------------------------------
# AC-4 — what the admin stores
# --------------------------------------------------------------------------


def test_a_random_batch_stores_the_strategies_of_every_puzzle() -> None:
    """AC-4: the column holds a real list for every row a batch writes.

    It held ``[]`` from both generation paths until this card. The store then
    fell back to deriving the list from its own uniqueness proof — correct,
    but it meant the recorded strategies came from a *different* call to the
    solver than the recorded grade, and only by luck the same one. Now the
    aggregate carries the deciding solve's ladder and the batch passes it
    through, so grade and strategies are two readings of one solve.
    """
    store = PuzzleReviewService()
    generator = BatchGenerator(puzzle_review_service=store)

    # Ten is the smallest random batch the admin accepts (CARD-094's one
    # bound), so it is the cheapest run that exercises the real path.
    batch_id = generator.create_batch(count=10, sizes=[10], source="random")
    stored = list(store.puzzles.values())

    assert len(stored) == 10, len(stored)
    for puzzle in stored:
        names = puzzle["strategies_used"]
        assert names, puzzle["id"]
        assert set(names) <= set(puzzle_review.STRATEGY_NAMES), names
    assert batch_id


def test_the_sample_generator_no_longer_invents_strategy_names() -> None:
    """The hardcoded ``['LineLogic', 'ConstraintProp']`` is gone.

    Those names were never produced by this system's solver, and they were
    written into the same column the real pipeline uses — so nothing
    downstream could tell a demo row from a generated one. The sample
    generator now reports what its own certifying solve needed.
    """
    puzzles = MockGenerator(seed=5).generate_batch(count=2, sizes=[10])

    for puzzle in puzzles:
        names = puzzle["strategies_used"]
        assert names
        assert set(names) <= set(puzzle_review.STRATEGY_NAMES), names


# --------------------------------------------------------------------------
# AC-4 (second half) — filtering the puzzle list by strategy
# --------------------------------------------------------------------------


def _stored(service, strategies: list[str]) -> str:
    """One stored puzzle carrying ``strategies``, in whichever mode ``service``
    is in. The grid is a solid block: uniquely solvable, so ``add_puzzle``'s
    CARD-080 gate passes, and cheap to solve."""
    grid = [[True] * 10 for _ in range(10)]
    return service.add_puzzle(
        grid=grid,
        clues_rows=[],
        clues_cols=[],
        width=10,
        height=10,
        theme="test",
        difficulty_score=10,
        difficulty_tier="easy",
        quality_score=50,
        recognizability="medium",
        strategies_used=strategies,
        batch_id=None,
        source_image="p.png",
    )


def _filtered(service, strategy: str) -> set[str]:
    response = service.filter_puzzles(
        puzzle_review.PuzzleFilter(strategy=strategy, limit=50)
    )
    return {puzzle["id"] for puzzle in response.puzzles}


def test_the_puzzle_list_filters_by_strategy() -> None:
    """AC-4: "show me the puzzles that need a guess".

    The filter matches a puzzle that *needs* the named strategy, which is
    membership in its list rather than equality with it — a puzzle needing
    ``simple_overlap`` and ``guess`` answers both filters, because both are
    true of it.
    """
    service = PuzzleReviewService()
    plain = _stored(service, ["simple_overlap"])
    guessy = _stored(service, ["simple_overlap", "line_dp", "guess"])

    assert _filtered(service, "guess") == {guessy}
    assert _filtered(service, "simple_overlap") == {plain, guessy}
    assert _filtered(service, "probe_contradiction") == set()


def test_the_puzzle_list_filters_by_strategy_against_the_database(tmp_path) -> None:
    """The same filter in the other storage mode, which is a different query.

    In-memory it is a membership test in Python; against a database it is SQL
    over a JSON column, and the two have to agree. Run on SQLite here and on
    Postgres in production — which is exactly why the query cannot use either
    dialect's JSON operators.
    """
    service = PuzzleReviewService(session_factory=_sqlite_scope(tmp_path))
    plain = _stored(service, ["simple_overlap"])
    guessy = _stored(service, ["line_dp", "guess"])

    assert _filtered(service, "guess") == {guessy}
    assert _filtered(service, "line_dp") == {guessy}
    assert _filtered(service, "simple_overlap") == {plain}


def test_a_strategy_name_is_never_matched_as_a_substring(tmp_path) -> None:
    """The database query matches whole names, not text anywhere in the row.

    It works by looking for the quoted name inside the serialized list, so
    this is the assertion that keeps that honest: a row whose *source image*
    is called ``guess.png`` is not a row that needs a guess.
    """
    service = PuzzleReviewService(session_factory=_sqlite_scope(tmp_path))
    # A name no version of this solver ever produced, of the kind older demo
    # and test writers really did store (``LineLogic``, ``backtracking``), and
    # chosen so that ``guess`` is a substring of it. A query that looked for
    # the bare name instead of the quoted one would call this row a puzzle
    # that needs a guess.
    foreign = _stored(service, ["guessing"])
    real = _stored(service, ["guess"])

    assert _filtered(service, "guess") == {real}
    assert foreign not in _filtered(service, "guess")


def test_the_puzzle_list_route_offers_the_filter_and_ignores_an_unknown_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The route half of AC-4, including the branch that is easy to forget.

    An unknown strategy is reported and then dropped — the same shape CARD-066
    gave the status filter, and for the same reason: filtering on a name the
    vocabulary does not contain would show an empty page that reads as "your
    other filters matched nothing".
    """
    from nonogram.admin.app import create_app

    # In-memory mode, explicitly. `create_app` reads DATABASE_URL, so a test
    # that leaves it to the ambient environment builds a *database-backed*
    # admin against whatever database happens to be configured on the machine
    # — which is how this test first stalled for ten minutes against a local
    # Postgres. The filter under test is storage-agnostic and has its own
    # database-mode test above.
    monkeypatch.delenv("DATABASE_URL", raising=False)

    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()

    page = client.get("/puzzles")
    body = page.get_data(as_text=True)
    assert page.status_code == 200
    assert 'id="strategy"' in body
    assert 'value="probe_contradiction"' in body

    unknown = client.get("/puzzles?strategy=LineLogic", follow_redirects=True)
    assert unknown.status_code == 200
    assert "Unknown strategy" in unknown.get_data(as_text=True)
