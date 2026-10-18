"""CARD-245 — the two routes the editor posts to, and what they refuse.

The store's half of this card is ``tests/test_puzzle_edit_store.py``; this file
is the panel's own boundary: ``POST /puzzle/<id>/edit/verify`` (grade it, store
nothing) and ``POST /puzzle/<id>/edit`` (store what was graded). The editor UI
that will call them is CARD-246.

Two kinds of test here, deliberately:

* the in-memory app, for the status codes and the flow — fast, and it cannot
  skip;
* ``TestPuzzleEditRoutes_OverTheRealDatabase``, which runs against the
  Postgres database ``tests/conftest.py`` migrates and truncates, so migration
  016's column and the DB write path are exercised on the engine production
  runs. It needs ``DATABASE_URL``; without it the suite's own fixture skips
  it, which is why the card's test selection is run with that variable set.
"""

from __future__ import annotations

import uuid

import pytest

from tests.test_puzzle_edit_store import (
    MINUS_CORNER_CLUES,
    MINUS_CORNER_SCORE,
    MINUS_CORNER_STRATEGIES,
    MINUS_CORNER_TIER,
    solid,
    solid_minus_corner,
    two_cell_diagonal,
)

VERIFY = "/puzzle/{}/edit/verify"
SAVE = "/puzzle/{}/edit"


@pytest.fixture
def admin_app(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("ADMIN_ALLOWED_HOST", raising=False)
    monkeypatch.setenv("TESTING", "true")
    from nonogram.admin.app import create_app

    app = create_app()
    app.config["TESTING"] = True
    return app


def seed(app, **overrides) -> str:
    payload = {
        "grid": solid(),
        "clues_rows": [[1]] * 10,
        "clues_cols": [[1]] * 10,
        "width": 10,
        "height": 10,
        "theme": "winter",
        "difficulty_score": 99,
        "difficulty_tier": "hard",
        "quality_score": 71,
        "recognizability": "high",
        "strategies_used": ["guess"],
        "source_image": "snowflake.png",
    }
    payload.update(overrides)
    return app.puzzle_review_service.add_puzzle(**payload)


def post(app, path: str, grid) -> tuple:
    response = app.test_client().post(path, json={"grid": grid})
    return response.status_code, response.get_json()


# --------------------------------------------------------------------------
# AC-5 / AC-1 — verify grades without storing; the save stores what was graded
# --------------------------------------------------------------------------


class TestPuzzleEditRoutes_VerifyThenSave:
    def test_verify_answers_with_the_grade_and_writes_nothing(self, admin_app):
        puzzle_id = seed(admin_app)
        store = admin_app.puzzle_review_service
        before = dict(store.get_puzzle(puzzle_id))

        code, body = post(admin_app, VERIFY.format(puzzle_id), solid_minus_corner())

        assert code == 200, body
        assert body["ok"] is True
        assert body["grade"]["difficulty_score"] == MINUS_CORNER_SCORE
        assert body["grade"]["difficulty_tier"] == MINUS_CORNER_TIER
        assert body["grade"]["strategies_used"] == MINUS_CORNER_STRATEGIES
        assert body["grade"]["clues_rows"] == MINUS_CORNER_CLUES
        assert store.get_puzzle(puzzle_id) == before

    def test_the_save_stores_the_verified_grid_and_rederives_everything(self, admin_app):
        puzzle_id = seed(admin_app)
        replacement = solid_minus_corner()

        assert post(admin_app, VERIFY.format(puzzle_id), replacement)[0] == 200
        code, body = post(admin_app, SAVE.format(puzzle_id), replacement)

        assert code == 200, body
        row = admin_app.puzzle_review_service.get_puzzle(puzzle_id)
        assert row["grid"] == replacement
        assert row["clues_rows"] == MINUS_CORNER_CLUES
        assert row["difficulty_score"] == MINUS_CORNER_SCORE
        assert row["difficulty_tier"] == MINUS_CORNER_TIER
        assert row["strategies_used"] == MINUS_CORNER_STRATEGIES
        assert row["manually_edited_at"] is not None
        assert body["puzzle"]["manually_edited_at"] == row["manually_edited_at"]

    def test_the_quality_score_is_still_there_afterwards(self, admin_app):
        puzzle_id = seed(admin_app, quality_score=71, recognizability="high")

        post(admin_app, VERIFY.format(puzzle_id), solid_minus_corner())
        post(admin_app, SAVE.format(puzzle_id), solid_minus_corner())

        row = admin_app.puzzle_review_service.get_puzzle(puzzle_id)
        assert (row["quality_score"], row["recognizability"]) == (71, "high")


# --------------------------------------------------------------------------
# the refusals, each with the code the panel already uses for its kind
# --------------------------------------------------------------------------


class TestPuzzleEditRoutes_Refusals:
    @pytest.mark.parametrize("path", [VERIFY, SAVE])
    def test_an_unknown_puzzle_is_a_404(self, admin_app, path):
        code, body = post(admin_app, path.format(uuid.uuid4()), solid_minus_corner())

        assert code == 404
        assert body["ok"] is False
        assert "not found" in body["message"].lower()

    @pytest.mark.parametrize("path", [VERIFY, SAVE])
    def test_a_puzzle_in_a_book_is_a_409_that_says_why(self, admin_app, path):
        """AC-4, and the wording approve and reject already use."""
        puzzle_id = seed(admin_app)
        admin_app.puzzle_review_service.assign_to_book([puzzle_id], str(uuid.uuid4()))

        code, body = post(admin_app, path.format(puzzle_id), solid_minus_corner())

        assert code == 409
        assert "in a book" in body["message"]

    @pytest.mark.parametrize("path", [VERIFY, SAVE])
    def test_a_grid_with_two_solutions_is_a_422_that_names_the_case(self, admin_app, path):
        """AC-2 at the boundary: the owner is told *why* it was refused."""
        puzzle_id = seed(admin_app)
        before = dict(admin_app.puzzle_review_service.get_puzzle(puzzle_id))

        code, body = post(admin_app, path.format(puzzle_id), two_cell_diagonal())

        assert code == 422
        assert "2 or more" in body["message"]
        assert admin_app.puzzle_review_service.get_puzzle(puzzle_id) == before

    @pytest.mark.parametrize("path", [VERIFY, SAVE])
    @pytest.mark.parametrize(
        "grid",
        [
            pytest.param([], id="empty"),
            pytest.param("not a grid", id="string"),
            pytest.param(None, id="none"),
            pytest.param([[1, 0]], id="integers"),
            pytest.param([[True], [True, True]], id="ragged"),
        ],
    )
    def test_a_malformed_grid_is_a_422(self, admin_app, path, grid):
        """AC-7 at the boundary."""
        puzzle_id = seed(admin_app)

        code, body = post(admin_app, path.format(puzzle_id), grid)

        assert code == 422
        assert "not a readable grid" in body["message"]

    @pytest.mark.parametrize("path", [VERIFY, SAVE])
    def test_a_body_that_is_not_json_at_all_is_a_422(self, admin_app, path):
        puzzle_id = seed(admin_app)

        response = admin_app.test_client().post(
            path.format(puzzle_id), data="grid=1",
            content_type="application/x-www-form-urlencoded",
        )

        assert response.status_code == 422
        assert response.get_json()["ok"] is False

    def test_a_save_whose_grid_moved_is_a_409(self, admin_app):
        """AC-6 at the boundary: the owner approved the grid they were shown."""
        puzzle_id = seed(admin_app)
        before = dict(admin_app.puzzle_review_service.get_puzzle(puzzle_id))
        post(admin_app, VERIFY.format(puzzle_id), solid_minus_corner())

        code, body = post(admin_app, SAVE.format(puzzle_id), solid(11, 11))

        assert code == 409
        assert "verify" in body["message"].lower()
        assert admin_app.puzzle_review_service.get_puzzle(puzzle_id) == before

    def test_a_save_with_no_verify_in_front_of_it_is_a_409(self, admin_app):
        puzzle_id = seed(admin_app)

        code, body = post(admin_app, SAVE.format(puzzle_id), solid_minus_corner())

        assert code == 409
        assert admin_app.puzzle_review_service.get_puzzle(puzzle_id)["grid"] == solid()

    @pytest.mark.parametrize("path", [VERIFY, SAVE])
    def test_a_get_is_not_allowed(self, admin_app, path):
        puzzle_id = seed(admin_app)

        assert admin_app.test_client().get(path.format(puzzle_id)).status_code == 405


# --------------------------------------------------------------------------
# the stamp where the score is shown
# --------------------------------------------------------------------------


class TestPuzzleEditSurfaces_TheQualityFigureSaysWhenItPredatesAnEdit:
    """The owner decision's last clause: surface the stamp where the score is.

    ``quality_score`` survives an edit, so a reader seeing one has to be able
    to tell whether it was measured before the grid changed.
    """

    #: The marker's server-rendered wording. Matched on rather than
    #: ``data-edited`` alone, because the detail panel's *script* carries that
    #: attribute inside a template literal on every page — asserting its
    #: absence would be asserting nothing (and said so, first time round).
    MARKER = "Hand-edited on "

    def test_the_list_row_carries_no_marker_before_an_edit(self, admin_app):
        seed(admin_app)

        body = admin_app.test_client().get("/puzzles").get_data(as_text=True)

        assert self.MARKER not in body

    def test_the_list_row_says_the_puzzle_was_hand_edited(self, admin_app):
        puzzle_id = seed(admin_app)
        post(admin_app, VERIFY.format(puzzle_id), solid_minus_corner())
        post(admin_app, SAVE.format(puzzle_id), solid_minus_corner())
        stamp = admin_app.puzzle_review_service.get_puzzle(puzzle_id)["manually_edited_at"]

        body = admin_app.test_client().get("/puzzles").get_data(as_text=True)

        assert self.MARKER in body
        assert f'{self.MARKER}{stamp[:10]}' in body
        assert "predates the edit" in body
        # The score itself is still on the page: the marker qualifies it, it
        # does not replace it.
        assert ">71<" in body

    def test_the_puzzle_card_reads_the_stamp_too(self, admin_app):
        """The detail panel is rendered client-side from ``/details``.

        Two halves, so neither can be true alone: the API hands the stamp out,
        and the script that builds the card reads that field.
        """
        puzzle_id = seed(admin_app)
        post(admin_app, VERIFY.format(puzzle_id), solid_minus_corner())
        post(admin_app, SAVE.format(puzzle_id), solid_minus_corner())
        client = admin_app.test_client()

        details = client.get(f"/api/puzzle/{puzzle_id}/details").get_json()
        page = client.get("/puzzles").get_data(as_text=True)

        assert details["puzzle"]["manually_edited_at"] is not None
        assert "puzzle.manually_edited_at" in page


# --------------------------------------------------------------------------
# the same flow over the database production runs
# --------------------------------------------------------------------------


@pytest.mark.db_required
class TestPuzzleEditRoutes_OverTheRealDatabase:
    """The write path on Postgres, through migration 016's column.

    ``client`` comes from ``tests/conftest.py``: it builds the app against the
    migrated test database this worktree owns (CARD-244) and truncates every
    table first.
    """

    def test_an_edit_posted_over_http_lands_in_the_database(self, app, client):
        store = app.puzzle_review_service
        assert store._session_factory is not None, "this test must be in DB mode"
        puzzle_id = seed(app)
        replacement = solid_minus_corner()

        verified = client.post(VERIFY.format(puzzle_id), json={"grid": replacement})
        saved = client.post(SAVE.format(puzzle_id), json={"grid": replacement})

        assert verified.status_code == 200, verified.get_json()
        assert saved.status_code == 200, saved.get_json()
        row = store.get_puzzle(puzzle_id)
        assert row["grid"] == replacement
        assert row["clues_rows"] == MINUS_CORNER_CLUES
        assert row["clues_cols"] == MINUS_CORNER_CLUES
        assert row["difficulty_score"] == MINUS_CORNER_SCORE
        assert row["difficulty_tier"] == MINUS_CORNER_TIER
        assert row["strategies_used"] == MINUS_CORNER_STRATEGIES
        assert row["manually_edited_at"] is not None
        assert row["quality_score"] == 71, "the score survives the edit (AC-8)"
        assert row["source_image"] == "snowflake.png", "G-3"

    def test_a_refused_edit_changes_no_row_in_the_database(self, app, client):
        store = app.puzzle_review_service
        puzzle_id = seed(app)
        before = store.get_puzzle(puzzle_id)

        refused = client.post(SAVE.format(puzzle_id), json={"grid": two_cell_diagonal()})

        assert refused.status_code == 422
        assert store.get_puzzle(puzzle_id) == before
        assert store.get_puzzle(puzzle_id)["manually_edited_at"] is None

    @staticmethod
    def _book(db_session) -> str:
        """A real ``books`` row — ``puzzles.book_id`` is a foreign key (CARD-103).

        Committed by hand: the ``db_session`` fixture yields the bare
        ``SessionLocal``, not the app's committing ``session_scope``, so a
        ``with`` block over it closes without writing anything.
        """
        from nonogram.db.models import Book

        book_id = uuid.uuid4()
        with db_session() as db:
            db.add(
                Book(
                    id=book_id, title="Winter nights", puzzle_ids=[],
                    puzzle_titles={}, book_metadata={},
                )
            )
            db.commit()
        return str(book_id)

    def test_a_booked_puzzle_is_refused_on_the_real_engine(self, app, client, db_session):
        store = app.puzzle_review_service
        puzzle_id = seed(app)
        store.assign_to_book([puzzle_id], self._book(db_session))

        refused = client.post(VERIFY.format(puzzle_id), json={"grid": solid_minus_corner()})

        assert refused.status_code == 409

    def test_the_column_is_really_in_the_migrated_schema(self, db_session):
        """The migration ran: 016's column exists on the table itself."""
        from sqlalchemy import inspect

        with db_session() as db:
            columns = {c["name"] for c in inspect(db.get_bind()).get_columns("puzzles")}

        assert "manually_edited_at" in columns
