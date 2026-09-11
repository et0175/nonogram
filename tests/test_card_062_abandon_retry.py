"""CARD-062: when the admin batch's predicted extent for a picture is
abandoned (not uniquely solvable within the pixel-nudge bound), the batch
retries at the long side -1/+1 before giving up.

AC-1 — an abandoned prediction with a solvable neighbour is stored at that
       neighbour.
AC-2 — the batch results name the picture and both extents.
AC-3 — prediction and both neighbours abandoned: today's error, the batch
       continues, at most 3 generate() calls.
AC-4 — any other error is not retried: one call.
AC-5 — success at the prediction: one call, unchanged output.
AC-6 — candidates stay in 10..30, keep the short side, follow the ordering
       rule.

``orchestrator.generate`` is patched at the orchestrator boundary to abandon
at chosen extents and run for real otherwise — the pattern
``test_admin_image_uniqueness.py::test_ac2_...`` uses — so the tests do not
depend on finding real pictures that happen to defeat the nudge loop.
"""

import random
import re
from datetime import datetime
from pathlib import Path

import pytest
from PIL import Image as PILImage

from nonogram import orchestrator
from nonogram.admin.image_manager import ImageFile
from nonogram.errors import GenerationAbandoned, UnreadableImage
from nonogram.sourcing.random_grid import MAX_SIZE, MIN_SIZE


def _image(width: int, height: int) -> ImageFile:
    """An ImageFile whose source shape is ``(width, height)`` (nonexistent
    file, so ``_source_shape`` falls back to ``dimensions``)."""
    return ImageFile(
        file_id="card062",
        filename="card062.png",
        original_filename="card062.png",
        file_path="/nonexistent/card062.png",
        file_size=0,
        dimensions=(width, height),
        format="PNG",
        uploaded_at=datetime.now(),
    )


class TestAC6NeighbourExtents:
    def test_landscape_orders_by_how_much_of_the_picture_is_kept(self):
        # Source 1.7:1 — 18x10 keeps 94.4%, 16x10 keeps 94.1%.
        assert _image(170, 100).neighbour_extents((17, 10)) == [(18, 10), (16, 10)]

    def test_the_shorter_neighbour_first_when_it_is_closer(self):
        # Source 1.62:1 — 16x10 keeps 98.8%, 18x10 keeps 90%.
        assert _image(162, 100).neighbour_extents((17, 10)) == [(16, 10), (18, 10)]

    def test_portrait_moves_the_height(self):
        # Source 1:1.3 — 10x14 keeps 92.9%, 10x12 keeps 92.3%.
        assert _image(100, 130).neighbour_extents((10, 13)) == [(10, 14), (10, 12)]

    def test_square_extent_uses_the_pictures_longer_axis(self):
        assert _image(150, 100).neighbour_extents((10, 10)) == [(11, 10)]
        assert _image(100, 150).neighbour_extents((10, 10)) == [(10, 11)]
        assert _image(100, 100).neighbour_extents((10, 10)) == [(11, 10)]

    def test_a_30_long_side_only_has_the_shorter_neighbour(self):
        assert _image(300, 200).neighbour_extents((30, 20)) == [(29, 20)]

    def test_degenerate_source_keeps_both_neighbours_in_plain_order(self):
        assert _image(0, 0).neighbour_extents((15, 10)) == [(14, 10), (16, 10)]

    def test_seeded_corpus_stays_in_range_and_keeps_the_short_side(self):
        rng = random.Random(62)
        cases = 0
        for _ in range(2000):
            w, h = rng.randint(MIN_SIZE, MAX_SIZE), rng.randint(MIN_SIZE, MAX_SIZE)
            src = (rng.randint(20, 800), rng.randint(20, 800))
            got = _image(*src).neighbour_extents((w, h))
            context = (w, h, src, got)
            cases += 1

            assert 1 <= len(got) <= 2, context
            assert (w, h) not in got and len(set(got)) == len(got), context
            long_is_width = w > h if w != h else src[0] >= src[1]
            for gw, gh in got:
                assert MIN_SIZE <= gw <= MAX_SIZE and MIN_SIZE <= gh <= MAX_SIZE, context
                assert abs(gw - w) + abs(gh - h) == 1, context
                assert (gw != w) == long_is_width, context
        assert cases == 2000


# --- AC-1..AC-5: the real Flask admin batch route ---------------------------


@pytest.fixture
def admin_client(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TESTING", "true")
    import nonogram.admin.image_manager as image_manager_module

    image_manager_module._image_manager = None
    from nonogram.admin.app import create_app

    app = create_app()
    app.config["TESTING"] = True
    with app.app_context():
        yield app, app.test_client()
    image_manager_module._image_manager = None


def _fully_inked(tmp_path: Path, width: int, height: int, name: str) -> Path:
    path = tmp_path / name
    PILImage.new("L", (width, height), color=0).save(path)
    return path


def _upload(client, paths, default_size="small") -> None:
    handles = [open(p, "rb") for p in paths]
    try:
        response = client.post(
            "/batch/from-images",
            data={
                "image_files": [(h, p.name) for h, p in zip(handles, paths)],
                "default_size": default_size,
            },
            content_type="multipart/form-data",
        )
    finally:
        for h in handles:
            h.close()
    assert response.status_code == 302, response.data


def _patch_generate(monkeypatch, abandon_at=(), fail_at=()):
    """Record every extent generate() is called with; abandon at
    ``abandon_at``, raise a non-abandon error at ``fail_at``, run for real
    otherwise."""
    calls = []
    real_generate = orchestrator.generate

    def fake(request, **kwargs):
        extent = (request.width, request.height)
        calls.append((request.image_filename, extent))
        if extent in fail_at:
            raise UnreadableImage("cannot read image: simulated")
        if extent in abandon_at:
            raise GenerationAbandoned(f"abandoned at {extent[0]}x{extent[1]} (simulated)")
        return real_generate(request, **kwargs)

    monkeypatch.setattr(orchestrator, "generate", fake)
    return calls


def _generate(client):
    response = client.post("/batch/generate-puzzles", data={}, follow_redirects=False)
    assert response.status_code == 302
    match = re.search(r"/batch/([^/]+)/generated-puzzles", response.location)
    assert match, response.location
    with client.session_transaction() as sess:
        flashed = [message for _, message in sess.get("_flashes", [])]
    return match.group(1), flashed


def _dims(puzzle) -> tuple:
    return len(puzzle["grid"][0]), len(puzzle["grid"])


def test_ac1_ac2_abandoned_prediction_is_rescued_by_a_neighbour(
    admin_client, tmp_path, monkeypatch
):
    app, client = admin_client
    # 300x200 at "small" predicts 15x10; neighbours ordered [16x10, 14x10].
    _upload(client, [_fully_inked(tmp_path, 300, 200, "wide.png")])
    calls = _patch_generate(monkeypatch, abandon_at={(15, 10)})

    batch_id, flashed = _generate(client)

    assert calls == [("wide.png", (15, 10)), ("wide.png", (16, 10))]
    (puzzle,) = app.batch_generator.get_batch_puzzles(batch_id, offset=0, limit=10)
    assert _dims(puzzle) == (16, 10)
    assert "wide.png: generated at 16x10 — 15x10 had no unique solution" in flashed


def test_ac3_all_abandoned_is_todays_error_and_the_batch_continues(
    admin_client, tmp_path, monkeypatch
):
    app, client = admin_client
    _upload(
        client,
        [
            _fully_inked(tmp_path, 300, 200, "wide.png"),
            _fully_inked(tmp_path, 200, 200, "square.png"),
        ],
    )
    calls = _patch_generate(monkeypatch, abandon_at={(15, 10), (16, 10), (14, 10)})

    batch_id, flashed = _generate(client)

    assert [e for name, e in calls if name == "wide.png"] == [(15, 10), (16, 10), (14, 10)]
    assert [e for name, e in calls if name == "square.png"] == [(10, 10)]
    puzzles = app.batch_generator.get_batch_puzzles(batch_id, offset=0, limit=10)
    assert [_dims(p) for p in puzzles] == [(10, 10)]
    assert "Error processing wide.png: abandoned at 15x10 (simulated)" in flashed
    assert not any("generated at" in message for message in flashed)


def test_ac4_other_errors_are_not_retried(admin_client, tmp_path, monkeypatch):
    app, client = admin_client
    _upload(client, [_fully_inked(tmp_path, 300, 200, "wide.png")])
    calls = _patch_generate(monkeypatch, fail_at={(15, 10)})

    batch_id, flashed = _generate(client)

    assert calls == [("wide.png", (15, 10))]
    assert app.batch_generator.get_batch_puzzles(batch_id, offset=0, limit=10) == []
    assert "Error processing wide.png: cannot read image: simulated" in flashed


def test_ac5_success_at_the_prediction_is_one_call(admin_client, tmp_path, monkeypatch):
    app, client = admin_client
    _upload(client, [_fully_inked(tmp_path, 300, 200, "wide.png")])
    calls = _patch_generate(monkeypatch)

    batch_id, flashed = _generate(client)

    assert calls == [("wide.png", (15, 10))]
    (puzzle,) = app.batch_generator.get_batch_puzzles(batch_id, offset=0, limit=10)
    assert _dims(puzzle) == (15, 10)
    assert not any("generated at" in message for message in flashed)


def test_ac2_more_than_three_adjustments_are_summarised(
    admin_client, tmp_path, monkeypatch
):
    app, client = admin_client
    _upload(client, [_fully_inked(tmp_path, 300, 200, f"wide{i}.png") for i in range(4)])
    _patch_generate(monkeypatch, abandon_at={(15, 10)})

    batch_id, flashed = _generate(client)

    assert len(app.batch_generator.get_batch_puzzles(batch_id, offset=0, limit=10)) == 4
    assert sum("generated at 16x10" in message for message in flashed) == 3
    assert "... and 1 more size adjustments" in flashed
