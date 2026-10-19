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
from pathlib import Path

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
    def test_a_puzzle_in_a_book_this_panel_cannot_name_is_a_409_that_says_why(
        self, admin_app, path
    ):
        """AC-4, as CARD-251 narrowed it, and the wording approve and reject use.

        **G-10, the retirement and its survivors.** Until CARD-251 this test
        booked a puzzle with any uuid and asserted the 409 for both routes.
        The owner has since asked for a booked puzzle to be editable behind a
        confirmation that NAMES the book, so that assertion's behaviour is
        gone and its survivors are
        ``TestBookedEditRoutes_TheConfirmationIsTheServers`` (the save still
        writes nothing — it is a confirmation that is missing, not a refusal
        that is gone) and ``TestBookedEditRoutes_ARegradeIsRefusedAtTheVerify``
        (the verify still refuses what would move the book's structure).

        What is left here is the membership with no book to name — the
        empty-string ``book_id`` a migration can leave behind — which is still
        this 409, in these words, on both routes.
        """
        puzzle_id = seed(admin_app)
        admin_app.puzzle_review_service.assign_to_book([puzzle_id], "")

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

    #: The marker's own class. ``badge rec`` is the *recognisability* chip's
    #: class, keyed by ``data-level``, and the marker borrowed it: it rendered
    #: as a second, identically grey chip in the same row, which is the one
    #: thing it must not look like, and the stylesheet had no rule that could
    #: tell them apart (review cycle 1, F-012). It has its own class now, and
    #: the two assertions below are both needed — one that the template asks
    #: for the class, one that the stylesheet answers.
    MARKER_CLASS = "badge edited"

    def test_the_marker_wears_its_own_class_and_not_recognisabilitys(self, admin_app):
        puzzle_id = seed(admin_app)
        post(admin_app, VERIFY.format(puzzle_id), solid_minus_corner())
        post(admin_app, SAVE.format(puzzle_id), solid_minus_corner())

        body = admin_app.test_client().get("/puzzles").get_data(as_text=True)
        marker = body[body.index(self.MARKER) - 400 : body.index(self.MARKER)]

        assert f'class="{self.MARKER_CLASS}"' in marker, marker
        assert 'class="badge rec"' not in marker, marker
        # The recognisability chip is still on the row, still keyed its own way.
        assert 'class="badge rec" data-level=' in body

    def test_the_stylesheet_styles_that_class(self):
        """Without this rule the marker is a bare grey chip the owner cannot
        tell from the recognisability one beside it — and the panel is checked
        by eye, so an unstyled marker is a defect no route assertion sees."""
        css = (
            Path(__file__).resolve().parents[1]
            / "src" / "nonogram" / "admin" / "static" / "admin.css"
        ).read_text(encoding="utf-8")

        rules = [line for line in css.splitlines() if line.startswith(".badge.edited")]

        assert rules, ".badge.edited has no rule in admin.css"
        assert "var(--color-warning)" in rules[0], rules[0]

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
# the flow's one deployment coupling, said where the knob is
# --------------------------------------------------------------------------


class TestPuzzleEdit_TheWorkerCountIsCoupledToTheTwoPhaseFlow:
    """Review cycle 1, F-007: the coupling has to be findable from the knob.

    The verify's proof lives on the ``PuzzleReviewService`` instance in the
    serving process, so a verify on worker A and an approve on worker B gives
    ``EditNotVerified``. It fails closed — nothing ungraded is stored — but an
    operator raising ``WEB_CONCURRENCY`` has no way to connect the two unless
    the script says so next to the flag. The default is **not** changed here;
    ``tests/test_admin_serving.py`` still owns that assertion.
    """

    @staticmethod
    def _start_script() -> str:
        return (Path(__file__).resolve().parents[1] / "start.sh").read_text(encoding="utf-8")

    def test_the_workers_flag_is_preceded_by_the_two_phase_note(self):
        script = self._start_script()
        workers_at = script.index("--workers")
        preamble = script[:workers_at]

        assert "WEB_CONCURRENCY" in preamble
        assert "/puzzle/<id>/edit/verify" in preamble, (
            "start.sh does not name the flow the worker count is coupled to"
        )
        # Close enough to the flag to be read with it, not 60 lines up.
        assert preamble.rindex("WEB_CONCURRENCY") > workers_at - 900

    def test_the_default_is_still_one_worker(self):
        """Unchanged by this card; asserted so the note cannot arrive with a bump."""
        assert '--workers "${WEB_CONCURRENCY:-1}"' in self._start_script()


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


# --------------------------------------------------------------------------
# CARD-251 — a booked puzzle is editable behind a confirmation that names the
# book. The routes' half; the store's rules are
# ``tests/test_puzzle_edit_store.py``'s CARD-251 section and the page's are
# ``tests/test_puzzle_editor_ui.py``'s.
#
#   AC-2/AC-8  the unconfirmed save answers `needs_confirmation` and the row
#              does not move — asserted by driving the real route and reading
#              the row, which is what makes the client's allow-list entry a
#              fact rather than a claim (Trap 3)
#   AC-4       the regrade refusal, at the verify route
#   AC-5       the extent refusal, at the save route
#   AC-6       a published book is named, with its status
#   AC-7       approve, reject, restore and delete still refuse a booked puzzle
#   AC-9       a split two-up page is ANNOUNCED and an approved edit stores
# --------------------------------------------------------------------------


def _grid(picture: str) -> list[list[bool]]:
    """A grid from a ``#``/``.`` picture — one row per line."""
    return [[cell == "#" for cell in line] for line in picture.strip().splitlines()]


#: Three 10x10 grids, all uniquely solvable and all **Easy** (score 33.0 — the
#: whole Easy band is that one point, ADR-0029's 2026-09-13 correction), whose
#: clue gutters are 3, 4 and 5 boxes deep. They were found with a seeded
#: ``random.Random(251)`` search over density-45 grids and are written out as
#: literals so the fixture costs no search; every property the tests lean on —
#: the extent, the tier and the depth — is asserted in
#: :class:`TestBookedEdit_TheDepthFixtureIsWhatItClaims`.
#:
#: The depths are what AC-9 drives, and they are the card's own measured
#: boundary on the Book 1 profile: two equal-tier 10x10 puzzles pair at a
#: shared cell of 7.500 mm at depth 3, still pair at 7.129 mm at depth 4, and
#: **do not pair at depth 5** — the page splits and every folio after it moves.
DEPTH_3 = _grid("""
###.#..#..
.##....##.
.##....##.
.##.##...#
..#...##.#
.#.....#.#
.#..#.####
..#..#.##.
...#..###.
.###..#..#
""")
DEPTH_4 = _grid("""
...#..#..#
..##.#.#..
.........#
#...#.#.#.
#.....####
##.##...#.
#....####.
#.#.##....
.##.###...
....######
""")
DEPTH_5 = _grid("""
#...#.....
######..##
.#####.#.#
#.#.#..#.#
.##.#.#.##
#.##..####
.##..##.#.
#.###....#
.....#...#
#####...#.
""")


def gutter_depth(clue_set) -> int:
    """The deepest line of a clue set, written here rather than imported.

    ``layout._gutter_depth`` is COMP-007's private helper and is the one the
    pairing walk uses; this is the same one line, so the fixture's claim about
    its own depth is not checked against the function whose verdict it is
    setting up.
    """
    return max(len(clue) for clue in clue_set)


def seed_with_real_clues(app, grid, **overrides) -> str:
    """A stored puzzle whose ``clues_*`` columns match its grid.

    Every other seed in this file stores deliberately wrong clue columns, so
    that an edit carrying them over would show. AC-9 cannot: the book's
    pairing is measured from the stored clue columns
    (``BookPDFGenerator._payload``), so a row whose clues are ``[[1]] * 10``
    would be measured as a one-box-deep puzzle whatever its grid looks like.
    """
    from nonogram.clues import compute_clues

    rows, columns = compute_clues(grid)
    return seed(
        app,
        grid=grid,
        clues_rows=[list(clue) for clue in rows],
        clues_cols=[list(clue) for clue in columns],
        width=len(grid[0]),
        height=len(grid),
        difficulty_tier="easy",
        difficulty_score=33,
        strategies_used=["simple_overlap"],
        **overrides,
    )


@pytest.fixture
def books(admin_app):
    """The panel's book manager, emptied before and after.

    In memory mode ``get_book_manager`` hands back a module-level singleton
    (``book_manager._book_manager``), so books outlive the ``admin_app``
    fixture and would leak between tests.
    """
    manager = admin_app.book_manager
    manager.books.clear()
    yield manager
    manager.books.clear()


def a_book(books, puzzle_ids, *, title="Winter Pictures", published=False) -> str:
    """A real draft book holding ``puzzle_ids``, through the panel's own path.

    ``create_book`` stores CON-018's Book 1 print profile, which is the
    profile the card's pairing measurements were taken on.
    """
    book_id = books.create_book(
        title=title, description="Winter pictures", theme="christmas",
        target_audience="adults",
    )
    assert books.add_puzzles_to_book(book_id, list(puzzle_ids)) is True
    if published:
        # Straight onto the stored status: `update_book_status` runs the
        # readiness gate, and what AC-6 is about is a published book's
        # confirmation, not how a book reaches that status.
        books.books[book_id].status = "published"
    assert books.get_book(book_id).puzzle_ids == list(puzzle_ids)
    return book_id


def post_save(app, puzzle_id, grid, *, confirmed=None) -> tuple:
    """``POST /puzzle/<id>/edit``, with or without the confirmation."""
    body = {"grid": grid}
    if confirmed is not None:
        body["confirmed"] = confirmed
    response = app.test_client().post(SAVE.format(puzzle_id), json=body)
    return response.status_code, response.get_json()


class TestBookedEdit_TheDepthFixtureIsWhatItClaims:
    """The three grids above, measured — so AC-9's boundary is not a story.

    Without this, a later edit to any of the three pictures could change what
    AC-9 is driving while AC-9 went on passing for a different reason.
    """

    @pytest.mark.parametrize(
        "grid, depth",
        [(DEPTH_3, 3), (DEPTH_4, 4), (DEPTH_5, 5)],
        ids=["depth-3", "depth-4", "depth-5"],
    )
    def test_each_grid_is_a_10x10_easy_puzzle_of_the_depth_it_is_named_for(
        self, admin_app, grid, depth
    ):
        from nonogram.clues import compute_clues

        rows, columns = compute_clues(grid)
        assert (len(grid[0]), len(grid)) == (10, 10)
        assert max(gutter_depth(rows), gutter_depth(columns)) == depth
        # Easy, and uniquely solvable — the store's own gate answers both, and
        # it refuses anything that is not a puzzle.
        puzzle_id = seed_with_real_clues(admin_app, grid)
        code, body = post(admin_app, VERIFY.format(puzzle_id), grid)
        assert code == 200, body
        assert body["grade"]["difficulty_tier"] == "easy"


class TestBookedEditRoutes_TheConfirmationIsTheServers:
    """AC-2 / G-1 at the boundary: the flag is the server's, and it names the book."""

    def test_an_unconfirmed_save_answers_needs_confirmation_and_stores_nothing(
        self, admin_app, books
    ):
        puzzle_id = seed(admin_app, difficulty_tier="easy")
        book_id = a_book(books, [puzzle_id])
        before = dict(admin_app.puzzle_review_service.get_puzzle(puzzle_id))
        assert post(admin_app, VERIFY.format(puzzle_id), solid_minus_corner())[0] == 200

        code, body = post_save(admin_app, puzzle_id, solid_minus_corner())

        assert code == 409, body
        assert body["reason"] == "needs_confirmation"
        assert body["book"]["id"] == book_id
        assert body["book"]["title"] == "Winter Pictures"
        assert body["book"]["status"] == "draft"
        assert body["book"]["published"] is False
        assert admin_app.puzzle_review_service.get_puzzle(puzzle_id) == before

    def test_the_confirmed_save_stores(self, admin_app, books):
        puzzle_id = seed(admin_app, difficulty_tier="easy")
        a_book(books, [puzzle_id])
        assert post(admin_app, VERIFY.format(puzzle_id), solid_minus_corner())[0] == 200

        code, body = post_save(admin_app, puzzle_id, solid_minus_corner(), confirmed=True)

        assert code == 200, body
        row = admin_app.puzzle_review_service.get_puzzle(puzzle_id)
        assert row["grid"] == solid_minus_corner()
        assert row["manually_edited_at"] is not None

    @pytest.mark.parametrize(
        "confirmed", ["true", 1, "yes", [True], {}], ids=["string", "one", "word", "list", "dict"]
    )
    def test_only_json_true_confirms(self, admin_app, books, confirmed):
        """Failure matrix F-9. A truthy value is not an answer to a question."""
        puzzle_id = seed(admin_app, difficulty_tier="easy")
        a_book(books, [puzzle_id])
        assert post(admin_app, VERIFY.format(puzzle_id), solid_minus_corner())[0] == 200

        code, body = post_save(
            admin_app, puzzle_id, solid_minus_corner(), confirmed=confirmed)

        assert (code, body["reason"]) == (409, "needs_confirmation")
        assert admin_app.puzzle_review_service.get_puzzle(puzzle_id)["grid"] == solid()

    def test_the_verify_answer_names_the_book_too(self, admin_app, books):
        """So the owner meets the question WITH the grade, and not only after
        pressing Approve."""
        puzzle_id = seed(admin_app, difficulty_tier="easy")
        book_id = a_book(books, [puzzle_id])

        code, body = post(admin_app, VERIFY.format(puzzle_id), solid_minus_corner())

        assert code == 200, body
        assert body["book"]["id"] == book_id
        assert body["book"]["title"] == "Winter Pictures"

    def test_an_unbooked_puzzles_verify_names_no_book(self, admin_app):
        """The control: ``book`` is absent when there is no book, so the two
        assertions above are about the membership and not about the key."""
        puzzle_id = seed(admin_app, difficulty_tier="easy")

        code, body = post(admin_app, VERIFY.format(puzzle_id), solid_minus_corner())

        assert code == 200, body
        assert body.get("book") is None

    def test_a_book_whose_title_cannot_be_read_still_needs_the_flag(
        self, admin_app, books
    ):
        """Failure matrix F-4: the title is presentation, the guard is the flag.

        The ``book_id`` points at no readable book — a deleted row — so the
        question names the id and says the title could not be read. The save
        is still refused without the flag, and still stores with it.
        """
        puzzle_id = seed(admin_app, difficulty_tier="easy")
        book_id = a_book(books, [puzzle_id])
        books.books.pop(book_id)
        assert post(admin_app, VERIFY.format(puzzle_id), solid_minus_corner())[0] == 200

        code, body = post_save(admin_app, puzzle_id, solid_minus_corner())

        assert (code, body["reason"]) == (409, "needs_confirmation")
        assert body["book"]["id"] == book_id
        assert body["book"]["title"] is None
        assert post_save(
            admin_app, puzzle_id, solid_minus_corner(), confirmed=True)[0] == 200


class TestBookedEdit_APublishedBookIsNamedInTheQuestion:
    """AC-6: a published book's puzzle needs the INV-008 confirmation it
    already requires, and the question says which book it is and that it is
    published.

    Trap 1: ``in_a_book()`` cannot tell a draft book from a published one — it
    is ``book_id is not None or status == IN_BOOK`` and nothing more — so "ask
    once for every book" would be a coarser instrument than the panel already
    has. The flag is the same one; what differs is what the question says, and
    that is what lets the page word the published case as INV-008's.
    """

    def test_the_question_names_the_book_and_its_published_status(
        self, admin_app, books
    ):
        puzzle_id = seed(admin_app, difficulty_tier="easy")
        book_id = a_book(books, [puzzle_id], title="Winter Nights", published=True)
        before = dict(admin_app.puzzle_review_service.get_puzzle(puzzle_id))
        assert post(admin_app, VERIFY.format(puzzle_id), solid_minus_corner())[0] == 200

        code, body = post_save(admin_app, puzzle_id, solid_minus_corner())

        assert (code, body["reason"]) == (409, "needs_confirmation")
        assert body["book"]["title"] == "Winter Nights"
        assert body["book"]["status"] == "published"
        assert body["book"]["published"] is True
        assert admin_app.puzzle_review_service.get_puzzle(puzzle_id) == before

    def test_a_draft_books_question_does_not_say_published(self, admin_app, books):
        """The control that can fail: the two cases are told apart, so the
        assertion above is about the status and not about the key's presence."""
        puzzle_id = seed(admin_app, difficulty_tier="easy")
        a_book(books, [puzzle_id], title="Winter Nights")

        post(admin_app, VERIFY.format(puzzle_id), solid_minus_corner())
        _code, body = post_save(admin_app, puzzle_id, solid_minus_corner())

        assert body["book"]["published"] is False
        assert body["book"]["status"] == "draft"

    def test_the_confirmation_stores_in_a_published_book_too(self, admin_app, books):
        """AC-6 is about which confirmation is required, not about a second
        refusal: the owner's answer stores the edit."""
        puzzle_id = seed(admin_app, difficulty_tier="easy")
        a_book(books, [puzzle_id], published=True)
        post(admin_app, VERIFY.format(puzzle_id), solid_minus_corner())

        code, _body = post_save(
            admin_app, puzzle_id, solid_minus_corner(), confirmed=True)

        assert code == 200
        assert admin_app.puzzle_review_service.get_puzzle(puzzle_id)["grid"] == (
            solid_minus_corner())

    def test_the_books_own_membership_rule_is_untouched(self, admin_app, books):
        """INV-008 itself: this card moves no membership, so a published
        book's ``add_puzzles_to_book`` still refuses without ITS confirmation."""
        puzzle_id = seed(admin_app, difficulty_tier="easy")
        other = seed(admin_app, difficulty_tier="easy", source_image="other.png")
        book_id = a_book(books, [puzzle_id], published=True)

        outcome = books.add_puzzles_reporting_refusals(book_id, [other])

        assert outcome.needs_confirmation is True
        assert books.get_book(book_id).puzzle_ids == [puzzle_id]


class TestBookedEdit_OnlyEditingWasOpened:
    """AC-7 / G-4: editing is the only action this card opens.

    Approve, reject, restore and delete still refuse a puzzle a book holds,
    and the three routes that do it are unchanged. Both halves, so neither is
    true alone: the refusal is read off each route, and the EDIT that now
    succeeds on the same puzzle is read beside it — otherwise a store that
    refused everything would pass this.
    """

    @pytest.mark.parametrize("action", ["approve", "reject"])
    def test_approve_and_reject_still_refuse_a_booked_puzzle(
        self, admin_app, books, action
    ):
        puzzle_id = seed(admin_app, difficulty_tier="easy")
        a_book(books, [puzzle_id])

        response = admin_app.test_client().post(
            f"/puzzle/{puzzle_id}/{action}",
            headers={"Accept": "application/json"},
        )

        assert response.status_code == 409
        assert f"Cannot {action} a puzzle that is in a book" in response.get_data(
            as_text=True)

    #: The two flash sentences, as those routes spell them today (delete's
    #: says "puzzle", restore's says "a puzzle"); read off the routes rather
    #: than reconstructed, so this test cannot pass on a sentence it wrote.
    _REFUSES = {
        "restore": "Cannot restore a puzzle that is in a book",
        "delete": "Cannot delete puzzle that is in a book",
    }

    @pytest.mark.parametrize("action", ["restore", "delete"])
    def test_restore_and_delete_still_refuse_a_booked_puzzle(
        self, admin_app, books, action
    ):
        """These two answer with a flash and a redirect rather than JSON, so
        the refusal is read off the followed page."""
        puzzle_id = seed(admin_app, difficulty_tier="easy")
        # Delete reaches its book question only for a rejected puzzle — a
        # draft one is refused earlier, for not being rejected — so the
        # premise is set up rather than assumed.
        admin_app.puzzle_review_service.puzzles[puzzle_id]["status"] = "rejected"
        a_book(books, [puzzle_id])
        assert admin_app.puzzle_review_service.get_puzzle(puzzle_id)["status"] == (
            "rejected")

        response = admin_app.test_client().post(
            f"/puzzle/{puzzle_id}/{action}", follow_redirects=True)
        page = response.get_data(as_text=True)

        assert self._REFUSES[action] in page
        assert admin_app.puzzle_review_service.get_puzzle(puzzle_id) is not None

    def test_editing_the_same_puzzle_does_go_through(self, admin_app, books):
        """The control the four refusals above need: this card opened one
        door, and it is open."""
        puzzle_id = seed(admin_app, difficulty_tier="easy")
        a_book(books, [puzzle_id])

        post(admin_app, VERIFY.format(puzzle_id), solid_minus_corner())
        code, _body = post_save(
            admin_app, puzzle_id, solid_minus_corner(), confirmed=True)

        assert code == 200


class TestBookedEdit_TheFifthReasonIsTrueNotListed:
    """AC-8 / Trap 3 / G-6: the client's allow-list stays TRUE.

    ``storeStateIsKnown`` in ``static/puzzle_edit.js`` is an allow-list of the
    answers that provably never write; everything else leaves the store's
    state unknown and asks for a reload, and the inversion was deliberate so
    that "the fifth refusal reason, whenever it is added, fails safe instead
    of lying". This card adds the fifth — three, in fact — and listing a
    string is a CLAIM. So each new reason is driven through the real route and
    the row is read afterwards: nothing stored, no ``manually_edited_at``.
    """

    @staticmethod
    def _a_refusal(admin_app, books, reason):
        """Drive the real save route into ``reason`` and hand back the row before."""
        if reason == "needs_confirmation":
            puzzle_id = seed(admin_app, difficulty_tier="easy")
            a_book(books, [puzzle_id])
            post(admin_app, VERIFY.format(puzzle_id), solid_minus_corner())
            return puzzle_id, lambda: post_save(
                admin_app, puzzle_id, solid_minus_corner())
        if reason == "regrade_in_a_book":
            puzzle_id = seed(admin_app, difficulty_tier="medium")
            # Verified while nothing held it, then booked: the path that
            # reaches the STORE's own regrade refusal (failure matrix F-2).
            post(admin_app, VERIFY.format(puzzle_id), solid_minus_corner())
            a_book(books, [puzzle_id])
            return puzzle_id, lambda: post_save(
                admin_app, puzzle_id, solid_minus_corner(), confirmed=True)
        assert reason == "extent_changed"
        puzzle_id = seed(admin_app, difficulty_tier="easy")
        post(admin_app, VERIFY.format(puzzle_id), solid(12, 15))
        return puzzle_id, lambda: post_save(admin_app, puzzle_id, solid(12, 15))

    @pytest.mark.parametrize(
        "reason", ["needs_confirmation", "regrade_in_a_book", "extent_changed"])
    def test_each_new_reason_really_writes_nothing(self, admin_app, books, reason):
        puzzle_id, save = self._a_refusal(admin_app, books, reason)
        store = admin_app.puzzle_review_service
        before = dict(store.get_puzzle(puzzle_id))

        code, body = save()

        assert body["reason"] == reason, (code, body)
        assert code in (409, 422), (code, body)
        after = store.get_puzzle(puzzle_id)
        assert after == before
        assert after["manually_edited_at"] is None
        assert after["grid"] == before["grid"]

    def test_the_vocabulary_holds_the_three_new_reasons(self):
        from nonogram.admin.app import EDIT_REFUSAL_REASONS

        for reason in ("needs_confirmation", "regrade_in_a_book", "extent_changed"):
            assert reason in EDIT_REFUSAL_REASONS
        # And the four that were there before are still there: this card adds
        # reasons, it retires none (G-10).
        for reason in ("not_unique", "not_verified", "in_a_book", "not_found"):
            assert reason in EDIT_REFUSAL_REASONS

    def test_in_a_book_is_still_a_reason_the_routes_emit(self, admin_app):
        """``in_a_book`` did not become dead vocabulary: a book this panel
        cannot NAME is still refused outright, because the question has to
        name the book (STRUCTURE, failure matrix F-10)."""
        puzzle_id = seed(admin_app, difficulty_tier="easy")
        admin_app.puzzle_review_service.assign_to_book([puzzle_id], "")

        code, body = post(admin_app, VERIFY.format(puzzle_id), solid_minus_corner())

        assert (code, body["reason"]) == (409, "in_a_book")


class TestBookedEditRoutes_ARegradeIsRefusedAtTheVerify:
    """AC-4 at the boundary: the owner learns it WITH the grade, not after.

    The refusal carries both tiers and the book, and it is the verify that
    gives it — so there is no Approve to press and nothing was stored.
    """

    def test_the_verify_refuses_and_names_both_tiers_and_the_book(
        self, admin_app, books
    ):
        puzzle_id = seed(admin_app, difficulty_tier="medium")
        a_book(books, [puzzle_id], title="Winter Pictures")
        before = dict(admin_app.puzzle_review_service.get_puzzle(puzzle_id))

        code, body = post(admin_app, VERIFY.format(puzzle_id), solid_minus_corner())

        assert code == 409, body
        assert body["reason"] == "regrade_in_a_book"
        assert "medium" in body["message"].lower()
        assert "easy" in body["message"].lower()
        assert body["book"]["title"] == "Winter Pictures"
        # No grade came back, so the page has nothing to offer an Approve for.
        assert "grade" not in body
        assert admin_app.puzzle_review_service.get_puzzle(puzzle_id) == before

    def test_the_same_tier_verifies_and_then_stores(self, admin_app, books):
        """The control: the refusal above is the tier change, not the book."""
        puzzle_id = seed(admin_app, difficulty_tier="easy")
        a_book(books, [puzzle_id])

        assert post(admin_app, VERIFY.format(puzzle_id), solid_minus_corner())[0] == 200
        assert post_save(
            admin_app, puzzle_id, solid_minus_corner(), confirmed=True)[0] == 200


class TestEditRoutes_AReplacementKeepsTheStoredExtent:
    """AC-5 at the boundary, booked and unbooked alike (Trap 2, G-5)."""

    def test_a_differently_shaped_replacement_is_refused(self, admin_app):
        puzzle_id = seed(admin_app, difficulty_tier="easy")
        before = dict(admin_app.puzzle_review_service.get_puzzle(puzzle_id))
        post(admin_app, VERIFY.format(puzzle_id), solid(12, 15))

        code, body = post_save(admin_app, puzzle_id, solid(12, 15))

        assert code == 422, body
        assert body["reason"] == "extent_changed"
        assert "10x10" in body["message"]
        assert "15x12" in body["message"]
        assert admin_app.puzzle_review_service.get_puzzle(puzzle_id) == before

    def test_a_booked_puzzle_refuses_it_with_the_confirmation_given(
        self, admin_app, books
    ):
        puzzle_id = seed(admin_app, difficulty_tier="easy")
        a_book(books, [puzzle_id])
        post(admin_app, VERIFY.format(puzzle_id), solid(12, 15))

        code, body = post_save(
            admin_app, puzzle_id, solid(12, 15), confirmed=True)

        assert (code, body["reason"]) == (422, "extent_changed")
        assert admin_app.puzzle_review_service.get_puzzle(puzzle_id)["grid"] == solid()


class TestBookedEdit_ASplitPairIsAnnouncedBeforeApprove:
    """AC-9 / G-3 — the second mechanism, which the tier rule does not reach.

    ``compute_pair_layout`` is computed FROM THE CLUES, so a denser picture
    means deeper clue gutters, a taller drawing, and at some depth the pair
    stops fitting: the page splits in two and every folio after it moves. The
    tier is unchanged and so is the extent, so neither AC-4 nor AC-5 sees it.

    **Owner decision, 2026-10-19: tell, do not refuse.** The verify answer
    says the page count would change and names the puzzle this one shares its
    page with; Approve stays available and an approved edit stores. Refusing
    was offered and declined — it would block any repaint that deepens a
    paired puzzle's clues, which is most real edits.

    **Both halves are asserted here on purpose.** A test that only read the
    warning would pass equally against an implementation that refused, which
    is precisely the collapse G-3 forbids.
    """

    @staticmethod
    def _pair(admin_app, books):
        """A book of two 10x10 Easy puzzles that share one page at depth 4."""
        first = seed_with_real_clues(admin_app, DEPTH_4, source_image="first.png")
        second = seed_with_real_clues(admin_app, DEPTH_4, source_image="second.png")
        a_book(books, [first, second])
        return first, second

    def test_a_split_pair_is_announced_and_the_approved_edit_stores(
        self, admin_app, books
    ):
        first, _second = self._pair(admin_app, books)

        code, body = post(admin_app, VERIFY.format(first), DEPTH_5)

        # Half one: the warning. The page count would change, and the answer
        # names the puzzle this one shares its page with.
        assert code == 200, body
        pages = body["book"]["pages"]
        assert pages["known"] is True
        assert pages["changes"] is True
        assert (pages["before"], pages["after"]) == (1, 2)
        assert pages["partner"] == "second.png"

        # Half two: Approve is still available, and an approved edit stores.
        code, saved = post_save(admin_app, first, DEPTH_5, confirmed=True)

        assert code == 200, saved
        assert admin_app.puzzle_review_service.get_puzzle(first)["grid"] == DEPTH_5

    def test_a_replacement_that_still_pairs_announces_no_change(
        self, admin_app, books
    ):
        """The measured boundary's other side, and this test's own control:
        depth 4 still pairs (at a shared cell already shrunk to 7.129 mm), so
        there is nothing to warn about — which is what makes the warning above
        a statement about the geometry and not about every booked edit."""
        first, _second = self._pair(admin_app, books)

        code, body = post(admin_app, VERIFY.format(first), DEPTH_4)

        assert code == 200, body
        pages = body["book"]["pages"]
        assert pages["known"] is True
        assert pages["changes"] is False
        assert (pages["before"], pages["after"]) == (1, 1)

    def test_a_shallower_replacement_also_keeps_the_page(self, admin_app, books):
        """Depth 3 pairs at the full 7.500 mm cap: the pair survives a
        replacement in the other direction too."""
        first, _second = self._pair(admin_app, books)

        _code, body = post(admin_app, VERIFY.format(first), DEPTH_3)

        assert body["book"]["pages"]["changes"] is False

    def test_an_unpaired_booked_puzzle_has_no_partner_to_name(
        self, admin_app, books
    ):
        """A book of one puzzle: the page count cannot change, so the answer
        says so and names nobody."""
        only = seed_with_real_clues(admin_app, DEPTH_4)
        a_book(books, [only])

        _code, body = post(admin_app, VERIFY.format(only), DEPTH_5)

        pages = body["book"]["pages"]
        assert pages["changes"] is False
        assert pages["partner"] is None

    def test_a_book_that_cannot_be_measured_says_so_rather_than_claiming(
        self, admin_app, books
    ):
        """Failure matrix F-5. The book's stored print specification cannot be
        laid out, so the walk raises and the effect is reported UNKNOWN —
        with Approve still available. Claiming "the page count does not
        change" out of a failed measurement is the lie the warning exists to
        prevent."""
        first, _second = self._pair(admin_app, books)
        book = books.books[next(iter(books.books))]
        book.trim_width_cm = "not a number"

        code, body = post(admin_app, VERIFY.format(first), DEPTH_5)

        assert code == 200, body
        pages = body["book"]["pages"]
        assert pages["known"] is False
        assert pages["changes"] is None
        # And the edit still goes through: an unmeasurable neighbour is no
        # reason to refuse what the tier and the extent already permit.
        assert post_save(admin_app, first, DEPTH_5, confirmed=True)[0] == 200

    def test_the_unknown_answer_is_not_what_a_measurable_book_gives(
        self, admin_app, books
    ):
        """The control for the test above: the same book, measured, answers
        ``known`` — so "unknown" is the broken specification and not this
        route's standing answer."""
        first, _second = self._pair(admin_app, books)

        _code, body = post(admin_app, VERIFY.format(first), DEPTH_5)

        assert body["book"]["pages"]["known"] is True
