"""Three curation amendments to the admin panel.

1 — a puzzle can be renamed from the review list; a blank name clears it.
2 — a puzzle card says which strategies a solver needs, read off the solver
    (stored when the list was recorded, re-derived from the grid when not).
3 — Curate → Batches: batches filtered by creation date, and a batch's own
    puzzle list — the review table without the filters.
"""

from __future__ import annotations

import re
import uuid
from contextlib import contextmanager
from datetime import datetime

import pytest

import nonogram.admin.image_manager as image_manager_module
from nonogram.admin.puzzle_review import (
    MAX_PUZZLE_NAME_LENGTH,
    STRATEGY_NAMES,
    PuzzleReviewService,
)

#: Uniquely solvable and line-solvable (tests/test_admin_regrade.py's fixture).
LINE_GRID = [
    [True, True, True, False, False],
    [True, False, False, False, True],
    [True, True, True, True, False],
    [False, False, True, False, False],
    [True, True, True, True, True],
]

#: Uniquely solvable, but the solve has to branch (tests/test_admin_regrade.py).
GUESS_GRID = [
    [False, False, True, True, False, False, True, True, False],
    [True, False, True, False, False, True, False, False, True],
    [True, False, False, True, False, False, True, False, False],
    [False, False, False, True, True, False, True, False, False],
    [False, True, False, False, True, False, False, False, False],
    [True, False, True, True, False, False, False, False, False],
    [False, True, False, True, True, False, False, False, False],
    [False, True, False, False, False, False, False, True, True],
    [False, True, False, False, False, False, False, False, False],
]

FULL_GRID = [[True] * 10 for _ in range(10)]


@pytest.fixture
def admin_app(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TESTING", "true")
    from nonogram.admin.app import create_app

    image_manager_module._image_manager = None
    app = create_app()
    app.config["TESTING"] = True
    with app.app_context():
        yield app
    image_manager_module._image_manager = None


def _add(service, grid=FULL_GRID, *, batch_id=None, source="p.png", strategies=None):
    return service.add_puzzle(
        grid=grid,
        clues_rows=[],
        clues_cols=[],
        width=len(grid[0]),
        height=len(grid),
        theme="test",
        difficulty_score=10,
        difficulty_tier="easy",
        quality_score=50,
        recognizability="medium",
        strategies_used=[] if strategies is None else strategies,
        batch_id=batch_id,
        source_image=source,
    )


def _batch(app):
    return app.batch_generator.create_batch(
        count=1, sizes=[10], theme="image", source="images", quality_filter=0
    )


def _sqlite_session_scope(tmp_path):
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


# --- 1: rename ---------------------------------------------------------------


def test_rename_sets_trims_and_clears_the_name():
    service = PuzzleReviewService()
    puzzle_id = _add(service)

    assert service.rename_puzzle(puzzle_id, "  Snowy   owl ")
    assert service.get_puzzle(puzzle_id)["puzzle_name"] == "Snowy owl"

    assert service.rename_puzzle(puzzle_id, "   ")
    assert service.get_puzzle(puzzle_id)["puzzle_name"] is None


def test_rename_refuses_a_name_that_is_too_long_and_changes_nothing():
    service = PuzzleReviewService()
    puzzle_id = _add(service)
    service.rename_puzzle(puzzle_id, "Owl")

    with pytest.raises(ValueError):
        service.rename_puzzle(puzzle_id, "x" * (MAX_PUZZLE_NAME_LENGTH + 1))
    assert service.get_puzzle(puzzle_id)["puzzle_name"] == "Owl"


def test_rename_of_an_unknown_puzzle_reports_not_found():
    assert PuzzleReviewService().rename_puzzle("puzzle_999999", "Owl") is False


def test_rename_works_against_the_database(tmp_path):
    service = PuzzleReviewService(session_factory=_sqlite_session_scope(tmp_path))
    puzzle_id = _add(service)

    assert service.rename_puzzle(puzzle_id, "Crab")
    assert service.get_puzzle(puzzle_id)["puzzle_name"] == "Crab"
    assert service.rename_puzzle(str(uuid.uuid4()), "Crab") is False
    assert service.rename_puzzle("not-a-uuid", "Crab") is False


def test_the_list_offers_a_rename_form_per_row(admin_app):
    puzzle_id = _add(admin_app.puzzle_review_service, source="crab.png")

    body = admin_app.test_client().get("/puzzles").get_data(as_text=True)

    assert f'action="/puzzle/{puzzle_id}/rename"' in body
    assert 'aria-label="Rename crab.png"' in body


def test_rename_route_returns_to_the_same_list_query(admin_app):
    puzzle_id = _add(admin_app.puzzle_review_service, source="crab.png")

    response = admin_app.test_client().post(
        f"/puzzle/{puzzle_id}/rename",
        data={"puzzle_name": "Hermit crab", "return_to": "status=draft&offset=0"},
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/puzzles?status=draft&offset=0")
    body = admin_app.test_client().get("/puzzles").get_data(as_text=True)
    assert re.search(r'class="name"[^>]*>Hermit crab<', body)
    assert '<div class="subtle">crab.png</div>' in body


def test_rename_route_reports_a_too_long_name(admin_app):
    puzzle_id = _add(admin_app.puzzle_review_service)
    client = admin_app.test_client()

    client.post(f"/puzzle/{puzzle_id}/rename", data={"puzzle_name": "x" * 500})

    assert admin_app.puzzle_review_service.get_puzzle(puzzle_id).get("puzzle_name") is None
    assert "at most" in client.get("/puzzles").get_data(as_text=True)


def test_an_action_from_a_batch_page_returns_to_that_batch(admin_app):
    batch_id = _batch(admin_app)
    puzzle_id = _add(admin_app.puzzle_review_service, batch_id=batch_id)

    response = admin_app.test_client().post(
        f"/puzzle/{puzzle_id}/rename",
        data={"puzzle_name": "Owl", "return_to": "offset=0", "return_batch": batch_id},
    )

    assert response.headers["Location"].endswith(f"/batches/{batch_id}?offset=0")


def test_a_malformed_return_batch_falls_back_to_the_review_list(admin_app):
    puzzle_id = _add(admin_app.puzzle_review_service)

    response = admin_app.test_client().post(
        f"/puzzle/{puzzle_id}/approve",
        data={"return_to": "", "return_batch": "//evil.example/x"},
    )

    assert response.headers["Location"].endswith("/puzzles")


# --- 2: strategies -----------------------------------------------------------


def test_the_store_records_the_solvers_strategies_when_the_caller_has_none():
    from nonogram.solver import RUNG_ORDER

    service = PuzzleReviewService()
    stored = service.get_puzzle(_add(service, LINE_GRID))["strategies_used"]

    assert stored, "the guard's own solve settled cells, so the list is not empty"
    assert set(stored) <= set(RUNG_ORDER)
    assert stored == sorted(stored, key=RUNG_ORDER.index), "ladder order"


def test_a_branching_grid_ends_its_list_with_guess():
    service = PuzzleReviewService()
    stored = service.get_puzzle(_add(service, GUESS_GRID))["strategies_used"]

    assert stored[-1] == "guess"


@pytest.mark.parametrize("grid", [LINE_GRID, GUESS_GRID, FULL_GRID])
def test_the_list_agrees_with_the_regrade_batchs_list(grid):
    """Two derivations of FR-029's list — the store's and the re-grade's — kept
    to one answer from here, where importing both is legal."""
    regrade = pytest.importorskip("nonogram.admin.regrade")
    service = PuzzleReviewService()

    stored = service.get_puzzle(_add(service, grid))["strategies_used"]

    assert stored == list(regrade.grade_stored_grid(grid).strategies)


def test_strategies_for_trusts_a_solver_written_list_and_resolves_an_invented_one():
    service = PuzzleReviewService()
    solver_written = _add(service, LINE_GRID, strategies=["line_dp"])
    invented = _add(service, LINE_GRID, strategies=["LineLogic", "ConstraintProp"])
    expected = service.get_puzzle(_add(service, LINE_GRID))["strategies_used"]

    assert service.strategies_for(service.get_puzzle(solver_written)) == ["line_dp"]
    assert service.strategies_for(service.get_puzzle(invented)) == expected
    assert set(expected) <= set(STRATEGY_NAMES)


def test_strategies_for_an_unreadable_grid_is_unknown():
    assert PuzzleReviewService().strategies_for({"grid": [[True], [True, False]]}) is None


def test_the_detail_api_carries_labelled_strategies(admin_app):
    puzzle_id = _add(admin_app.puzzle_review_service, GUESS_GRID)

    data = admin_app.test_client().get(f"/api/puzzle/{puzzle_id}/details").get_json()

    names = [s["name"] for s in data["strategies"]]
    assert names == admin_app.puzzle_review_service.get_puzzle(puzzle_id)["strategies_used"]
    assert data["strategies"][-1] == {"name": "guess", "label": "Guessing (trial and error)"}


def test_the_generated_puzzles_cards_show_the_strategies(admin_app):
    batch_id = _batch(admin_app)
    _add(admin_app.puzzle_review_service, GUESS_GRID, batch_id=batch_id)

    body = admin_app.test_client().get(f"/batch/{batch_id}/generated-puzzles").get_data(as_text=True)

    assert "<dt>Strategies</dt>" in body
    assert 'data-strategy="guess"' in body and "Guessing (trial and error)" in body


# --- 3: batches --------------------------------------------------------------


def test_the_navigation_lists_batches_under_curate(admin_app):
    body = admin_app.test_client().get("/batches").get_data(as_text=True)
    curate = body.split('<div class="group">Curate</div>')[1].split('<div class="group">')[0]
    assert '<a href="/batches" aria-current="page">Batches</a>' in curate


def test_batches_are_listed_newest_first_and_filtered_by_date(admin_app):
    generator = admin_app.batch_generator
    old, new = _batch(admin_app), _batch(admin_app)
    generator.jobs[old].created_at = datetime(2026, 9, 1, 23, 30)
    generator.jobs[new].created_at = datetime(2026, 9, 10, 8, 0)
    _add(admin_app.puzzle_review_service, batch_id=new, source="owl.png")
    client = admin_app.test_client()

    everything = client.get("/batches").get_data(as_text=True)
    assert everything.index(f"/batches/{new}") < everything.index(f"/batches/{old}")
    assert "owl.png" in everything

    only_old = client.get("/batches?date_from=2026-09-01&date_to=2026-09-01").get_data(as_text=True)
    assert f"/batches/{old}" in only_old and f"/batches/{new}" not in only_old

    from_later = client.get("/batches?date_from=2026-09-02").get_data(as_text=True)
    assert f"/batches/{new}" in from_later and f"/batches/{old}" not in from_later


def test_an_inverted_or_malformed_date_range_is_reported(admin_app):
    client = admin_app.test_client()
    assert "Filter error" in client.get("/batches?date_from=2026-09-10&date_to=2026-09-01").get_data(as_text=True)
    assert "Filter error" in client.get("/batches?date_from=tomorrow").get_data(as_text=True)


def test_a_batch_page_lists_only_its_puzzles_without_the_filters(admin_app):
    batch_id = _batch(admin_app)
    mine = _add(admin_app.puzzle_review_service, batch_id=batch_id, source="mine.png")
    _add(admin_app.puzzle_review_service, batch_id=_batch(admin_app), source="theirs.png")

    body = admin_app.test_client().get(f"/batches/{batch_id}").get_data(as_text=True)

    assert "Puzzles (1 total)" in body
    assert f'action="/puzzle/{mine}/approve"' in body
    assert "theirs.png" not in body
    assert 'id="puzzle_name"' not in body, "no filter form on a batch page"
    assert f'name="return_batch" value="{batch_id}"' in body
    assert 'id="puzzleDetailModal"' in body


@pytest.mark.parametrize("batch_id", ["not-a-uuid", "00000000-0000-0000-0000-000000000000"])
def test_an_unknown_batch_page_is_404(admin_app, batch_id):
    assert admin_app.test_client().get(f"/batches/{batch_id}").status_code == 404


def test_batch_listing_and_summaries_work_against_the_database(tmp_path):
    from nonogram.admin.batch_generator import BatchGenerator

    scope = _sqlite_session_scope(tmp_path)
    service = PuzzleReviewService(session_factory=scope)
    generator = BatchGenerator(puzzle_review_service=service, session_factory=scope)
    batch_id = generator.create_batch(count=1, sizes=[10], source="images")
    approved = _add(service, batch_id=batch_id, source="a.png")
    _add(service, batch_id=batch_id, source="b.png")
    service.approve_puzzle(approved)

    (job,) = generator.list_batches()
    assert job.batch_id == batch_id and job.source == "images"
    assert generator.list_batches(date_from="2000-01-01", date_to="2000-01-02") == []

    summary = service.batch_summaries([batch_id])[batch_id]
    assert (summary["total"], summary["approved"], summary["draft"]) == (2, 1, 1)
    assert summary["names"] == ["a.png", "b.png"]
