"""CARD-064: when the chosen size would cut a thin picture (its grid keeps
less than ``MIN_KEPT_SHARE`` of the ink bounding box), admin moves it up to
Large and says so; when Large would cut it too, the picture is skipped with
a message.

AC-1 — c5's shape at Medium moves to Large (10x30), with a visible note.
AC-2 — a 5:1 picture cannot fit: a message in the preview, no generate()
       call, listed as skipped; the other pictures still generate.
AC-3 — pictures that fit keep exactly today's extent, with no note.
AC-4 — the threshold is one constant, and moving it moves what is flagged.
AC-5 — status and extent agree with the share actually kept, across a
       seeded corpus.
"""

import random
import re
from datetime import datetime
from pathlib import Path

import pytest
from PIL import Image as PILImage

import nonogram.admin.image_manager as image_manager_module
from nonogram import orchestrator
from nonogram.admin.image_manager import (
    CANNOT_FIT,
    FITS,
    MIN_KEPT_SHARE,
    MOVED_TO_LARGE,
    ImageFile,
)
from nonogram.errors import GenerationAbandoned
from nonogram.limits import MAX_SIZE, MIN_SIZE


def _image(width: int, height: int, mode: str = "fixed", value: int = 20) -> ImageFile:
    """An ImageFile whose source shape is exactly ``(width, height)``; the
    file does not exist, so ``_source_shape`` falls back to ``dimensions``.
    Defaults to the Medium preset (fixed 20)."""
    image = ImageFile(
        file_id="card064",
        filename="card064.png",
        original_filename="card064.png",
        file_path="/nonexistent/card064.png",
        file_size=0,
        dimensions=(width, height),
        format="PNG",
        uploaded_at=datetime.now(),
    )
    image.size_mode, image.size_value = mode, value
    return image


def _kept(source: tuple, grid: tuple) -> float:
    """Share of the picture a crop to ``grid``'s shape keeps, independently
    of the code under test. It uses integer cross-products, so exact
    boundary cases compare exactly against MIN_KEPT_SHARE."""
    a, b = source[0] * grid[1], grid[0] * source[1]
    return min(a, b) / max(a, b)


def _normalized(body: str) -> str:
    return re.sub(r"\s+", " ", body)


class TestAC1MovedToLarge:
    def test_c5_shape_at_medium_moves_to_large(self):
        """c5.jpg's ink bounding box, 162x469 (1:2.9)."""
        fit = _image(162, 469).size_fit()
        assert fit.status == MOVED_TO_LARGE
        assert fit.chosen == (10, 20)
        assert round(fit.chosen_kept, 2) == 0.69
        assert fit.extent == (10, 30)
        assert fit.kept >= MIN_KEPT_SHARE

    @pytest.mark.parametrize("shape, large", [((116, 262), (13, 30)), ((186, 439), (13, 30))])
    def test_c4_and_c9_shapes_at_medium(self, shape, large):
        fit = _image(*shape).size_fit()
        assert (fit.status, fit.extent) == (MOVED_TO_LARGE, large)

    def test_a_short_side_with_no_grid_under_the_cap_moves_to_large(self):
        fit = _image(250, 100, "short", 15).size_fit()
        assert fit.chosen is None
        assert (fit.status, fit.extent) == (MOVED_TO_LARGE, (30, 12))


class TestAC2CannotFit:
    @pytest.mark.parametrize(
        "mode, value", [("fixed", 20), ("fixed", 30), ("short", 10), ("max", 0), ("min", 0)]
    )
    def test_five_to_one_cannot_fit_at_any_setting(self, mode, value):
        fit = _image(500, 100, mode, value).size_fit()
        assert fit.status == CANNOT_FIT
        assert fit.extent == (30, 10)
        assert fit.kept < MIN_KEPT_SHARE

    @pytest.mark.parametrize("value", [20, 25])
    def test_the_old_4_to_1_fixed_pins_now_cannot_fit(self, value):
        """CARD-061 pinned (400, 100) at fixed 20 and 25 as 20x10 (50% kept)
        and 25x10 (62%); since CARD-064 it cannot fit: Large keeps 75%."""
        fit = _image(400, 100, "fixed", value).size_fit()
        assert fit.chosen == (value, 10)
        assert (fit.status, fit.extent) == (CANNOT_FIT, (30, 10))

    def test_the_status_is_in_the_api_view(self):
        assert _image(500, 100).to_dict()["size_status"] == CANNOT_FIT
        assert _image(300, 200).to_dict()["size_status"] == FITS


#: (shape, mode, value, extent) — all keep ≥ 90%, so CARD-064 changes nothing.
FITTING = [
    ((300, 200), "fixed", 20, (20, 13)),
    ((300, 200), "fixed", 25, (25, 17)),
    ((200, 300), "fixed", 20, (13, 20)),
    ((229, 149), "fixed", 20, (20, 13)),
    ((229, 149), "fixed", 30, (30, 20)),
    ((500, 500), "fixed", 20, (20, 20)),
    ((300, 200), "short", 10, (15, 10)),
    ((200, 300), "short", 10, (10, 15)),
    ((500, 500), "short", 10, (10, 10)),
    ((300, 200), "short", 12, (18, 12)),
    ((300, 200), "max", 0, (30, 20)),
]


@pytest.mark.parametrize("shape, mode, value, extent", FITTING)
def test_ac3_a_picture_that_fits_keeps_its_extent(shape, mode, value, extent):
    image = _image(*shape, mode, value)
    fit = image.size_fit()
    assert (fit.status, fit.extent, image.predict_size()) == (FITS, extent, extent)


class TestTheBoundaryIsInclusiveAndSymmetric:
    @pytest.mark.parametrize("shape", [(100, 90), (90, 100)])
    def test_exactly_the_threshold_fits_in_both_orientations(self, shape):
        """10x10 keeps exactly 90% of a 10:9 picture, either way round."""
        fit = _image(*shape, "fixed", 10).size_fit()
        assert fit.kept == MIN_KEPT_SHARE
        assert (fit.status, fit.extent) == (FITS, (10, 10))


class TestAC4Threshold:
    def test_moving_the_constant_moves_what_is_flagged(self, monkeypatch):
        c4 = (116, 262)  # keeps 89% at Medium
        assert _image(*c4).size_fit().status == MOVED_TO_LARGE

        monkeypatch.setattr(image_manager_module, "MIN_KEPT_SHARE", 0.85)
        assert _image(*c4).size_fit().status == FITS

        monkeypatch.setattr(image_manager_module, "MIN_KEPT_SHARE", 0.99)
        # 20x13 keeps 97.5% of a 1.5:1 picture; Large's 30x20 keeps all of it.
        assert _image(300, 200).size_fit().status == MOVED_TO_LARGE


def test_ac5_status_agrees_with_the_share_kept():
    rng = random.Random(64)
    counts = {FITS: 0, MOVED_TO_LARGE: 0, CANNOT_FIT: 0}
    for _ in range(3000):
        ratio = rng.uniform(1.0, 8.0)
        short_edge = rng.randint(40, 600)
        long_edge = round(short_edge * ratio)
        source = (long_edge, short_edge) if rng.random() < 0.5 else (short_edge, long_edge)
        mode, value = rng.choice(
            [
                ("fixed", rng.randint(MIN_SIZE, MAX_SIZE)),
                ("short", rng.randint(MIN_SIZE, MAX_SIZE)),
                ("max", 0),
                ("min", 0),
            ]
        )
        fit = _image(*source, mode, value).size_fit()
        w, h = fit.extent
        context = (source, mode, value, fit)
        counts[fit.status] += 1

        assert MIN_SIZE <= w <= MAX_SIZE and MIN_SIZE <= h <= MAX_SIZE, context
        assert abs(_kept(source, fit.extent) - fit.kept) < 1e-9, context
        chosen_ok = fit.chosen is not None and _kept(source, fit.chosen) >= MIN_KEPT_SHARE
        if fit.status == FITS:
            assert chosen_ok and fit.extent == fit.chosen, context
        else:
            assert not chosen_ok, context
            assert max(w, h) == MAX_SIZE, context  # Large's grid
            assert (fit.kept >= MIN_KEPT_SHARE) == (fit.status == MOVED_TO_LARGE), context

    assert sum(counts.values()) == 3000
    assert min(counts.values()) >= 100, counts


# --- the real Flask admin batch flow -----------------------------------------


@pytest.fixture
def admin_client(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TESTING", "true")
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


def _upload(client, paths, default_size="medium") -> None:
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


def _generate(client):
    response = client.post("/batch/generate-puzzles", data={}, follow_redirects=False)
    assert response.status_code == 302
    match = re.search(r"/batch/([^/]+)/generated-puzzles", response.location)
    assert match, response.location
    with client.session_transaction() as sess:
        flashed = [message for _, message in sess.get("_flashes", [])]
    return match.group(1), flashed


def test_ac1_a_thin_picture_is_moved_to_large_end_to_end(admin_client, tmp_path):
    app, client = admin_client
    _upload(client, [_fully_inked(tmp_path, 162, 469, "candle.png")])

    preview = _normalized(client.get("/batch/preview-images").get_data(as_text=True))
    assert "The chosen size (10×20) would cut this picture (keeps 69%)" in preview
    assert "using Large (10×30)" in preview
    confirm = _normalized(client.get("/batch/generate-puzzles").get_data(as_text=True))
    assert "moved to Large" in confirm

    batch_id, flashed = _generate(client)
    (puzzle,) = app.batch_generator.get_batch_puzzles(batch_id, offset=0, limit=10)
    assert (len(puzzle["grid"][0]), len(puzzle["grid"])) == (10, 30)
    # G-2: the batch results say so too, not only the preview.
    assert (
        "candle.png: moved up to Large — the chosen size 10x20 would cut it (keeps 69%)"
    ) in flashed


def test_a_retry_below_the_threshold_says_how_much_it_keeps(
    admin_client, tmp_path, monkeypatch
):
    """CARD-062's ±1 retry may land under MIN_KEPT_SHARE. It is kept (it
    rescues real pictures, e.g. b3 at Small), but the result line says what
    share of the picture the stored grid keeps."""
    app, client = admin_client
    # 441x1442 at Small: no 10-cell short side fits under 30, so it moves to
    # Large's 10x30 (92%); abandon that, and the only neighbour is 10x29 (89%).
    _upload(client, [_fully_inked(tmp_path, 441, 1442, "tall.png")], "small")
    real_generate = orchestrator.generate

    def abandon_large(request, **kwargs):
        if (request.width, request.height) == (10, 30):
            raise GenerationAbandoned("abandoned at 10x30 (simulated)")
        return real_generate(request, **kwargs)

    monkeypatch.setattr(orchestrator, "generate", abandon_large)
    batch_id, flashed = _generate(client)

    (puzzle,) = app.batch_generator.get_batch_puzzles(batch_id, offset=0, limit=10)
    assert (len(puzzle["grid"][0]), len(puzzle["grid"])) == (10, 29)
    assert "tall.png: moved up to Large — the chosen size can't keep its shape" in flashed
    assert (
        "tall.png: generated at 10x29 — 10x30 had no unique solution; "
        "it keeps 89% of the picture"
    ) in flashed


def test_ac2_a_picture_that_cannot_fit_is_skipped_end_to_end(
    admin_client, tmp_path, monkeypatch
):
    app, client = admin_client
    _upload(
        client,
        [
            _fully_inked(tmp_path, 500, 100, "strip.png"),
            _fully_inked(tmp_path, 200, 200, "square.png"),
        ],
    )
    strip = next(
        i for i in image_manager_module.get_image_manager().get_all_images()
        if i.original_filename == "strip.png"
    )

    preview = _normalized(client.get("/batch/preview-images").get_data(as_text=True))
    assert "even Large keeps only 60% of it) — this picture will be skipped" in preview
    assert f"/api/image/{strip.file_id}/cropped" not in preview
    confirm = _normalized(client.get("/batch/generate-puzzles").get_data(as_text=True))
    assert "will be skipped" in confirm

    calls = []
    real_generate = orchestrator.generate

    def recording(request, **kwargs):
        calls.append(request.image_filename)
        return real_generate(request, **kwargs)

    monkeypatch.setattr(orchestrator, "generate", recording)
    batch_id, flashed = _generate(client)

    assert calls == ["square.png"]
    assert len(app.batch_generator.get_batch_puzzles(batch_id, offset=0, limit=10)) == 1
    assert (
        "strip.png skipped: too elongated for any supported size "
        "(even Large keeps only 60%)"
    ) in flashed
