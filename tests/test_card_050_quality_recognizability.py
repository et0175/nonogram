"""CARD-050: quality_score/recognizability must be real measurements, not
hardcoded fakes.

Before this card:
  * Image mode (``image_to_puzzle.py``, and — after CARD-049 relocated the
    production image-mode path — the copy of the same bug in ``app.py``'s
    ``generate_batch_puzzles``) scored purely from the *output grid's* fill
    density and hardcoded ``recognizability = "medium"``. It never looked at
    the source picture.
  * Random mode (``batch_generator.py``) fell back to the literal constant
    ``75`` for every puzzle, unconditionally, because
    ``orchestrator.Puzzle`` never had a ``quality_score`` attribute for the
    ``hasattr`` guard to find.

AC-1 — image-mode quality_score/recognizability come from a real comparison
       between the generated grid and the source picture
       (``nonogram.analysis.quality_metric.measure_quality``), not from
       output-grid density alone or a hardcoded string.
AC-2 — random-mode quality_score is either a real, defined measurement or
       explicitly ``None`` with the UI updated to match (this card chose the
       latter — see CARD-050's Worktree notes for the reasoning) — not the
       literal constant ``75`` for every puzzle.
AC-3 — ``src/nonogram/generation/random_generator.py`` no longer carries the
       ``from src.nonogram.analysis...`` import that only resolved by
       accident of how the test suite happens to be invoked. (The literal
       fix — swapping the prefix for ``from nonogram.analysis...`` —
       surfaced a real ADR-0007 violation once the import became visible to
       ``tests/test_cli.py``'s structural guard, so the actual fix removes
       the cross-capability import entirely; see the AC-3 section below and
       the module's own docstring for the full reasoning.)
       **AC-3's three tests were deleted by CARD-053 (2026-09-22) along with
       their subject — ``src/nonogram/generation/`` is gone from the tree.
       The criterion stays discharged; see the note at the foot of this
       file.**
"""

import ast
import os
import re
from pathlib import Path

import pytest
from PIL import Image

from nonogram.admin.batch_generator import BatchGenerator
from nonogram.admin.puzzle_review import PuzzleReviewService
from nonogram.analysis.quality_metric import measure_quality

FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# AC-1a: measure_quality() itself distinguishes a faithful conversion of a
# source picture from a degraded one — the property the wiring in app.py
# now relies on. (tests/test_quality_metric.py already exercises the
# function in isolation; this test is the specific "faithful vs. degraded
# conversion of the SAME source image differ meaningfully" scenario AC-1
# asks for.)
# ---------------------------------------------------------------------------


def _source_image() -> Image.Image:
    """A 10x10 black square on white — same picture used for both grids
    below, so any score difference is attributable to fidelity alone."""
    img = Image.new("L", (10, 10), 255)
    for y in range(2, 8):
        for x in range(2, 8):
            img.putpixel((x, y), 0)
    return img


def _faithful_grid() -> list:
    """Exact reproduction of _source_image()'s black square."""
    grid = [[False] * 10 for _ in range(10)]
    for y in range(2, 8):
        for x in range(2, 8):
            grid[y][x] = True
    return grid


def _degraded_grid() -> list:
    """A grid that has thrown away the silhouette: the square's outline is
    gone and most of its interior is empty, replaced by unrelated fill
    scattered across corners the source image has none of."""
    grid = [[False] * 10 for _ in range(10)]
    for x in range(10):
        grid[0][x] = True
        grid[9][x] = True
    for y in range(10):
        grid[y][0] = True
        grid[y][9] = True
    return grid


def test_ac1a_faithful_and_degraded_conversions_of_same_image_score_differently():
    source = _source_image()

    faithful = measure_quality(source, _faithful_grid())
    degraded = measure_quality(source, _degraded_grid())

    assert faithful.quality_score > degraded.quality_score
    # "differ meaningfully", not just "differ" — a token 1-point gap would
    # not distinguish a real per-image measurement from noise.
    assert faithful.quality_score - degraded.quality_score >= 20

    assert faithful.recognizability.value != degraded.recognizability.value


# ---------------------------------------------------------------------------
# AC-1b: the real admin batch-image path (app.py's generate_batch_puzzles,
# where CARD-049 relocated production image-mode generation) stores exactly
# what measure_quality() independently computes for the same source
# picture and the same stored grid — proof the *production* code calls the
# real metric rather than the old density-only formula or a hardcoded
# "medium". A hardcoded "medium"/density-based value would only coincide
# with an independent measure_quality() recomputation by chance.
# ---------------------------------------------------------------------------


@pytest.fixture
def admin_app(monkeypatch):
    """Real Flask admin app, in-memory mode (no DATABASE_URL) — mirrors the
    fixture ``tests/test_admin_image_uniqueness.py`` (CARD-049) uses."""
    # CARD-109: monkeypatch rather than os.environ.pop — popping cleared the
    # variable for the rest of the session too, so whether a later test saw a
    # database depended on whether this one had run first.
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TESTING", "true")
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


def test_ac1b_image_mode_batch_stores_real_measure_quality_output(admin_app, client):
    image_path = FIXTURES / "bird1.jpg"

    with open(image_path, "rb") as f:
        upload_response = client.post(
            "/batch/from-images",
            data={"image_files": [(f, "bird1.jpg")]},
            content_type="multipart/form-data",
        )
    assert upload_response.status_code == 302, upload_response.data

    response = client.post("/batch/generate-puzzles", data={}, follow_redirects=False)
    assert response.status_code == 302, response.data
    batch_id = _batch_id_from_redirect(response.location)

    puzzles = admin_app.batch_generator.get_batch_puzzles(batch_id, offset=0, limit=100)
    assert puzzles, "expected at least one puzzle stored for the batch"
    puzzle = puzzles[0]

    # Independent recomputation, not a re-read of what the admin code
    # happened to store: open the same source picture fresh and measure the
    # stored grid against it, exactly as AC-1 asks for.
    independent = measure_quality(Image.open(image_path), puzzle["grid"])

    assert puzzle["quality_score"] == independent.quality_score
    assert puzzle["recognizability"] == independent.recognizability.value

    # Guard against the old bugs regressing silently: a real per-image
    # score is not a hardcoded "medium", and 1-100 (never the density-only
    # formula's degenerate cases) is a real int, not None.
    assert isinstance(puzzle["quality_score"], int)
    assert 1 <= puzzle["quality_score"] <= 100
    assert puzzle["recognizability"] in {"high", "medium", "low"}


# ---------------------------------------------------------------------------
# AC-2: random-mode quality_score is explicitly None (this card's chosen
# option 3b), never the old unconditional constant 75, and the
# now-meaningless quality_filter no longer silently drops every candidate
# (or raises TypeError comparing None to an int).
# ---------------------------------------------------------------------------


@pytest.fixture
def batch_gen():
    """In-memory BatchGenerator + PuzzleReviewService — no Postgres
    required, unlike the DB-backed ``app``/``client`` fixtures."""
    review_service = PuzzleReviewService(session_factory=None)
    return BatchGenerator(puzzle_review_service=review_service, session_factory=None)


def test_ac2_random_mode_quality_score_is_none_not_75(batch_gen):
    batch_id = batch_gen.create_batch(
        count=10,
        sizes=[12],
        theme="test",
        source="random",
        quality_filter=0,
    )

    puzzles = batch_gen.get_batch_puzzles(batch_id, offset=0, limit=100)
    assert len(puzzles) == 10

    quality_scores = [p["quality_score"] for p in puzzles]
    recognizabilities = [p["recognizability"] for p in puzzles]

    # Not "both exactly 75" (the AC's own phrasing) — every one of them is
    # explicitly None, the option this card chose, rather than a fabricated
    # number indistinguishable from a real measurement.
    assert all(score is None for score in quality_scores)
    assert all(rec is None for rec in recognizabilities)
    assert not any(score == 75 for score in quality_scores)


def test_ac2_quality_filter_no_longer_drops_or_crashes_random_batches(batch_gen):
    """A high quality_filter used to be inert-by-construction (every
    candidate scored exactly 75, so a filter <= 75 kept everything and a
    filter > 75 dropped everything uniformly). Now that quality_score is
    None, ``None >= quality_filter`` would raise TypeError if the filter
    were still applied — assert instead that every candidate the
    orchestrator produced is stored, regardless of the (meaningless, for
    random mode) filter value.
    """
    batch_id = batch_gen.create_batch(
        count=10,
        sizes=[12],
        theme="test",
        source="random",
        quality_filter=80,
    )

    job = batch_gen.get_batch_status(batch_id)
    assert job.status.value == "complete"

    puzzles = batch_gen.get_batch_puzzles(batch_id, offset=0, limit=100)
    assert len(puzzles) == 10


# ---------------------------------------------------------------------------
# AC-2 regression (cycle-2 review finding): the None-quality_score guard
# clauses in batch_status.html:144 and generated_puzzles.html:65 (added in
# commit 2ef1e60, fixing the exact same quality-badge line that had already
# needed a fix once before, in 40b8c98) previously had zero test coverage —
# the two tests above only assert against BatchGenerator's data layer, never
# against rendered HTML. Drives a real random-mode batch through the actual
# Flask routes and asserts on the rendered response body, so a future edit
# to either template that reintroduces "Quality: None" or "0/100" fails the
# suite instead of only surfacing in a manual eyeball of the admin UI.
# ---------------------------------------------------------------------------


def test_ac2_batch_status_and_generated_puzzles_pages_render_none_quality_as_na(
    admin_app, client
):
    batch_id = admin_app.batch_generator.create_batch(
        count=10,
        sizes=[12],
        theme="test",
        source="random",
        quality_filter=0,
    )

    puzzles = admin_app.batch_generator.get_batch_puzzles(
        batch_id, offset=0, limit=100
    )
    assert puzzles and all(p["quality_score"] is None for p in puzzles), (
        "precondition: random-mode puzzles must have quality_score is None "
        "for this to be a meaningful regression test"
    )

    batch_status_response = client.get(f"/batch/{batch_id}")
    assert batch_status_response.status_code == 200
    batch_status_body = batch_status_response.get_data(as_text=True)
    assert "Quality: None" not in batch_status_body
    assert "0/100" not in batch_status_body
    assert "N/A" in batch_status_body

    generated_puzzles_response = client.get(f"/batch/{batch_id}/generated-puzzles")
    assert generated_puzzles_response.status_code == 200
    generated_puzzles_body = generated_puzzles_response.get_data(as_text=True)
    assert "Quality: None" not in generated_puzzles_body
    assert "0/100" not in generated_puzzles_body
    assert "N/A" in generated_puzzles_body


# ---------------------------------------------------------------------------
# AC-3's three tests were DELETED by CARD-053 (2026-09-22) together with their
# subject, ``src/nonogram/generation/random_generator.py``.
#
# They were: ``test_ac3_random_generator_has_no_src_prefixed_import_statement``
# (the file carries no ``from src.nonogram...`` import),
# ``test_ac3_random_generator_no_longer_laterally_imports_analysis`` (nor any
# ``nonogram.analysis`` import, which is what kept ADR-0007's structural guard
# green), and
# ``test_ac3_reimplemented_difficulty_formula_matches_the_original_independently``
# (``_difficulty_from_strategy_flags`` cross-checked against
# ``analysis.strategy_counter.calculate_difficulty_from_strategies``, in the
# shape ``mask_runs`` is cross-checked against ``clues.encode_line``).
#
# All three parsed or imported a file that no longer exists, so they could only
# be deleted or rewritten into assertions about absence. CARD-050's AC-3 stays
# discharged on its own record: the import it was about was fixed in
# CARD-050 (merge 62f8c62), and the file it was about is gone. The guard those
# tests protected is not weakened — ``tests/test_cli.py::
# test_every_import_in_the_package_points_inward`` walks the whole package on
# disk, so it covers what is left without naming any file.
# ---------------------------------------------------------------------------
