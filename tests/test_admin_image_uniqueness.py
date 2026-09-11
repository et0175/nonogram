"""CARD-049: admin image-mode batch generation is routed through the
solver-verified pipeline (``orchestrator.generate``), not the unverified
``image_to_puzzle.create_puzzle_from_image`` helper.

Why a new file rather than extending ``tests/integration_tests.py``
---------------------------------------------------------------------
``tests/integration_tests.py`` is a hand-rolled report-printing script (its
functions take a ``report`` positional argument and it is driven via
``if __name__ == "__main__"``/``run_smoke_test``/``run_full_suite``, not
pytest fixtures), and it isn't even collected by pytest today — its filename
is ``integration_tests.py`` while ``pyproject.toml`` leaves
``python_files``/``python_functions`` at pytest's default
(``test_*.py``/``test_*``), which that name doesn't match, and it hard-codes
absolute paths into a sibling checkout
(``/Users/.../PythonProject4/silhouette/...``) that don't exist inside this
worktree. Bolting real pytest coverage onto it would mean rewriting its
report-harness shape for no benefit. A dedicated file exercising the real
Flask admin app (mirroring the fixture style already used by
``tests/e2e/test_admin_workflow.py``) is the direct way to get AC-1/AC-2/AC-3
covered.

AC-1 — every stored puzzle's grid is verified uniquely solvable by the real
       solver (not merely produced by image conversion).
AC-2 — an image that can't be made uniquely solvable within the nudge bound
       is recorded as a batch error and the rest of the batch still
       completes (no whole-request 500).
AC-3 — difficulty_score/difficulty_tier come from
       ``nonogram.difficulty.score_difficulty`` via real ``SolverSignals``
       (through ``orchestrator.generate``), not from grid size alone.
"""

import os
import re
import tempfile
from pathlib import Path

import pytest
from PIL import Image

from nonogram import clues as clue_derivation
from nonogram import difficulty
from nonogram import orchestrator
from nonogram.errors import GenerationAbandoned
from nonogram.solver import solve

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def admin_app():
    """Real Flask admin app, in-memory mode (no DATABASE_URL)."""
    os.environ.pop("DATABASE_URL", None)
    os.environ["TESTING"] = "true"
    from nonogram.admin.app import create_app

    app = create_app()
    app.config["TESTING"] = True
    app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

    with app.app_context():
        yield app


@pytest.fixture
def client(admin_app):
    return admin_app.test_client()


def _batch_id_from_redirect(location: str) -> str:
    match = re.search(r"/batch/([^/]+)/generated-puzzles", location)
    assert match, f"Unexpected redirect target: {location!r}"
    return match.group(1)


def _upload_and_generate(client, files):
    """Drive the real admin batch-image flow: upload then generate.

    ``files`` is a list of (path, upload_filename) pairs. Returns the
    generate-puzzles POST response (a redirect on success).
    """
    data = {}
    opened = [open(path, "rb") for path, _ in files]
    try:
        data["image_files"] = [(f, name) for f, (_, name) in zip(opened, files)]
        upload_response = client.post(
            "/batch/from-images", data=data, content_type="multipart/form-data"
        )
        assert upload_response.status_code == 302, upload_response.data
    finally:
        for f in opened:
            f.close()

    return client.post("/batch/generate-puzzles", data={}, follow_redirects=False)


def test_ac1_stored_puzzle_grid_is_solver_verified_uniquely_solvable(admin_app, client):
    """AC-1: a puzzle generated through the admin batch-image path has a grid
    the real solver confirms has exactly one solution — the same guarantee
    ``nonogram generate --mode image`` gives — not merely a grid produced by
    image conversion with nothing checking it.
    """
    response = _upload_and_generate(client, [(str(FIXTURES / "bird1.jpg"), "bird1.jpg")])
    assert response.status_code == 302
    batch_id = _batch_id_from_redirect(response.location)

    puzzles = admin_app.batch_generator.get_batch_puzzles(batch_id, offset=0, limit=100)
    assert puzzles, "expected at least one puzzle stored for the batch"

    puzzle = puzzles[0]
    grid = puzzle["grid"]
    clues_rows = puzzle["clues_rows"]
    clues_cols = puzzle["clues_cols"]

    # The stored clues must be exactly the run-length encoding of the stored
    # grid (INV-001) — an independent re-derivation, not a re-read of what
    # the admin code happened to store.
    expected_rows, expected_cols = clue_derivation.compute_clues(grid)
    assert tuple(tuple(r) for r in clues_rows) == expected_rows
    assert tuple(tuple(c) for c in clues_cols) == expected_cols

    # The real solver — the same one orchestrator.generate() itself calls via
    # judge_candidate — must confirm exactly one solution.
    result = solve(expected_rows, expected_cols)
    assert result.solution_count == 1
    assert result.is_unique


def test_ac2_abandoned_image_recorded_as_error_and_batch_continues(
    admin_app, client, monkeypatch
):
    """AC-2: an image whose conversion cannot be made uniquely solvable
    within the nudge bound is recorded in the batch's error list and the
    batch continues for the remaining images — not a whole-request 500.

    Exercised at the orchestrator boundary: ``orchestrator.generate`` is
    patched to raise ``GenerationAbandoned`` for one specific image
    (identified by its uploaded filename) and to run for real for the other,
    which is real evidence that failure handling is per-image without
    depending on finding a real picture that happens to defeat the nudge
    loop (fragile) or mocking away the code under test.
    """
    real_generate = orchestrator.generate

    def flaky_generate(request, **kwargs):
        if request.image_filename == "unsolvable.png":
            raise GenerationAbandoned(
                "the picture was never re-drawn and nudging it further is not "
                "attempted again"
            )
        return real_generate(request, **kwargs)

    monkeypatch.setattr(orchestrator, "generate", flaky_generate)

    response = _upload_and_generate(
        client,
        [
            (str(FIXTURES / "bird1.jpg"), "bird1.jpg"),
            (str(FIXTURES / "bird2.jpg"), "unsolvable.png"),
        ],
    )

    # Not a whole-request failure.
    assert response.status_code == 302
    batch_id = _batch_id_from_redirect(response.location)

    # The batch continued: the good image still produced a stored puzzle.
    puzzles = admin_app.batch_generator.get_batch_puzzles(batch_id, offset=0, limit=100)
    assert len(puzzles) == 1

    # The failure surfaced as a flashed error, not a crash — Flask's flash
    # messages are queued in the session and rendered on the next request.
    with client.session_transaction() as sess:
        flashed = sess.get("_flashes", [])
    error_messages = [msg for category, msg in flashed if category == "info"]
    assert any("unsolvable.png" in msg for msg in error_messages), flashed


def test_ac3_difficulty_comes_from_real_solver_signals_not_grid_size(admin_app, client):
    """AC-3: difficulty_score/difficulty_tier are what
    ``nonogram.difficulty.score_difficulty`` (via real ``SolverSignals``
    from ``orchestrator.generate``) produced, not a lookup keyed on grid
    size alone.

    Two independent checks distinguish this from the old
    ``image_to_puzzle.create_puzzle_from_image`` size-only formula:

    1. The stored tier is one of the real ``Tier`` StrEnum's lowercase
       values (``"easy"``/``"medium"``/``"hard"``) — the old code stored
       capitalized string literals (``"Easy"``/``"Medium"``/``"Hard"``)
       that were never derived from a score at all.
    2. The stored tier is exactly what ``difficulty.tier_for_score`` maps
       the stored score to — true by construction for the real pipeline
       (``Puzzle.difficulty_tier`` *is* ``tier_for_score(difficulty_score)``)
       but not for the old formula, whose "Easy" score band (20..50) mostly
       falls in the real pipeline's Medium band (33..66], so the two
       wouldn't agree if the size-only formula were still in play.
    """
    response = _upload_and_generate(client, [(str(FIXTURES / "bird1.jpg"), "bird1.jpg")])
    assert response.status_code == 302
    batch_id = _batch_id_from_redirect(response.location)

    puzzles = admin_app.batch_generator.get_batch_puzzles(batch_id, offset=0, limit=100)
    assert puzzles
    puzzle = puzzles[0]

    stored_tier = puzzle["difficulty_tier"]
    stored_score = puzzle["difficulty_score"]

    assert stored_tier in {t.value for t in difficulty.Tier}

    assert stored_score is not None
    assert difficulty.tier_for_score(stored_score).value == stored_tier
