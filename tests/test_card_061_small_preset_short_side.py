"""CARD-061: admin's "small" batch preset takes 10 as the grid's SHORT side
and lets the long side follow the picture, instead of a bare N=10 that
``derive_extent`` floors to a forced 10x10 square for every picture (the
floor, MIN_SIZE, is also the smallest N).

AC-1 — a ~1.5:1 picture at "small" predicts 15x10 (landscape) / 10x15
       (portrait).
AC-2 — a square picture predicts 10x10; a picture too elongated for a
       10-cell short side under the 30-cell cap is judged at Large instead
       (CARD-064: moved to Large, or skipped when Large would cut it too).
AC-3 — "fixed"-mode extents are unchanged; the "large" preset moves from
       25 to 30 (owner decision, 2026-09-11).
AC-4 — the "short" mode never leaves 10..30, across a seeded corpus of
       ratios in both orientations.
AC-5 — end to end through the admin batch routes, a "small" 1.5:1 picture
       is generated as a 15x10 puzzle, and the preview page's save round
       trip keeps the mode.
"""

import random
import re
from datetime import datetime
from pathlib import Path

import pytest
from PIL import Image as PILImage

from nonogram.admin.image_manager import (
    CANNOT_FIT,
    FITS,
    MIN_KEPT_SHARE,
    MOVED_TO_LARGE,
    ImageFile,
)
from nonogram.sourcing.random_grid import MAX_SIZE, MIN_SIZE, derive_extent


def _image(width: int, height: int, size_mode: str = "short", size_value: int = 10) -> ImageFile:
    """An ImageFile whose source shape is exactly ``(width, height)``.

    ``file_path`` does not exist, so ``_source_shape`` takes its documented
    fallback to ``dimensions`` — the shape under test, with no decode.
    """
    image = ImageFile(
        file_id="card061",
        filename="card061.png",
        original_filename="card061.png",
        file_path="/nonexistent/card061.png",
        file_size=0,
        dimensions=(width, height),
        format="PNG",
        uploaded_at=datetime.now(),
    )
    image.size_mode = size_mode
    image.size_value = size_value
    return image


def _retained(src_w: int, src_h: int, grid_w: int, grid_h: int) -> float:
    """Share of the picture an aspect-preserving centre crop to the grid's
    shape keeps, computed independently of the code under test. It uses
    integer cross-products: a ratio of ratios lands on 0.8999999999999999
    for exact 90% cases such as 200x60 at 30x10, which then straddle
    MIN_KEPT_SHARE."""
    a, b = src_w * grid_h, grid_w * src_h
    return min(a, b) / max(a, b)


def _normalized(body: str) -> str:
    return re.sub(r"\s+", " ", body)


class TestAC1SmallFollowsThePicture:
    def test_landscape_one_and_a_half_to_one_is_15x10(self):
        image = _image(300, 200)
        assert image.predict_size() == (15, 10)
        assert image.size_fit().status == FITS

    def test_portrait_is_the_transpose(self):
        assert _image(200, 300).predict_size() == (10, 15)

    def test_the_owners_c11_shape(self):
        """c11.jpg's ink bounding box, 229x149 (1.54:1)."""
        image = _image(229, 149)
        assert image.predict_size() == (15, 10)
        assert _retained(229, 149, *image.predict_size()) > 0.97
        # The bare-N path this replaces: forced square, ~65% kept.
        assert derive_extent(10, None, 229, 149) == (10, 10)
        assert _retained(229, 149, 10, 10) < 0.66


class TestAC2SquareAndOverTheCap:
    def test_square_stays_10x10(self):
        image = _image(500, 500)
        assert image.predict_size() == (10, 10)
        assert image.size_fit().status == FITS

    def test_four_to_one_is_skipped(self):
        """No 10-cell short side fits under the cap, and Large's 30x10 keeps
        only 75% of the picture — under MIN_KEPT_SHARE — so since CARD-064
        it is skipped rather than generated with a note."""
        fit = _image(400, 100).size_fit()
        assert fit.extent == derive_extent(30, None, 400, 100) == (30, 10)
        assert fit.chosen is None
        assert fit.status == CANNOT_FIT

    def test_portrait_four_to_one(self):
        fit = _image(100, 400).size_fit()
        assert fit.extent == (10, 30)
        assert fit.status == CANNOT_FIT

    def test_beyond_six_to_one_still_lands_in_range(self):
        fit = _image(800, 100).size_fit()
        assert fit.extent == (30, 10)
        assert fit.status == CANNOT_FIT

    def test_over_the_cap_but_large_keeps_the_shape(self):
        """Short side 15 on a 2.5:1 picture would need a 38-cell long side;
        Large's 30x12 keeps all of it, so the picture moves to Large."""
        fit = _image(250, 100, size_value=15).size_fit()
        assert fit.chosen is None
        assert (fit.extent, fit.status) == ((30, 12), MOVED_TO_LARGE)

    def test_degenerate_shape_is_not_a_substitution(self):
        image = _image(0, 0)
        assert image.predict_size() == (10, 10)
        assert image.size_fit().status == FITS


# (source shape, N, extent) — "fixed"-mode answers pinned from before CARD-061.
FIXED_MODE_EXPECTATIONS = [
    ((300, 200), 20, (20, 13)),
    ((300, 200), 25, (25, 17)),
    ((200, 300), 20, (13, 20)),
    ((229, 149), 20, (20, 13)),
    ((229, 149), 25, (25, 16)),
    ((229, 149), 30, (30, 20)),
    ((300, 200), 30, (30, 20)),
    ((500, 500), 20, (20, 20)),
    # (400, 100) at 20 and 25 cut the 4:1 picture to 50% and 62%; since
    # CARD-064 it is skipped instead (tests/test_card_064_thin_pictures.py).
]


@pytest.mark.parametrize("shape, n, extent", FIXED_MODE_EXPECTATIONS)
def test_ac3_fixed_mode_is_unchanged(shape, n, extent):
    image = _image(*shape, size_mode="fixed", size_value=n)
    assert image.predict_size() == extent
    assert image.size_fit().status == FITS


def test_ac4_short_mode_stays_in_range_across_a_seeded_corpus():
    rng = random.Random(61)
    cases = followed = other = 0
    for _ in range(3000):
        ratio = rng.uniform(1.0, 5.9)
        short_edge = rng.randint(40, 600)
        long_edge = round(short_edge * ratio)
        w, h = (long_edge, short_edge) if rng.random() < 0.5 else (short_edge, long_edge)
        short_value = rng.randint(MIN_SIZE, MAX_SIZE)

        image = _image(w, h, size_value=short_value)
        fit = image.size_fit()
        gw, gh = fit.extent
        context = (w, h, short_value, gw, gh, fit.status)
        cases += 1

        assert MIN_SIZE <= gw <= MAX_SIZE and MIN_SIZE <= gh <= MAX_SIZE, context
        assert (gw >= gh) if w >= h else (gh >= gw), context
        if fit.status == FITS:
            followed += 1
            assert min(gw, gh) == short_value, context
            assert _retained(w, h, gw, gh) >= 0.95, context
        else:
            # The short side had no grid under the cap; Large was judged.
            other += 1
            assert fit.chosen is None, context
            assert max(gw, gh) == MAX_SIZE, context
            kept_enough = _retained(w, h, gw, gh) >= MIN_KEPT_SHARE
            assert kept_enough == (fit.status == MOVED_TO_LARGE), context

    assert cases == 3000
    assert followed >= 300 and other >= 300, (followed, other)


# --- AC-5 and the page round trip: the real Flask admin app ----------------


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
        yield app, app.test_client(), image_manager_module
    image_manager_module._image_manager = None


def _fully_inked(tmp_path: Path, width: int, height: int) -> Path:
    path = tmp_path / f"inked_{width}x{height}.png"
    PILImage.new("L", (width, height), color=0).save(path)
    return path


def _upload(client, path: Path, default_size: str) -> None:
    with open(path, "rb") as f:
        response = client.post(
            "/batch/from-images",
            data={"image_files": [(f, path.name)], "default_size": default_size},
            content_type="multipart/form-data",
        )
    assert response.status_code == 302, response.data


@pytest.mark.parametrize(
    "preset, expected",
    [("small", ("short", 10)), ("medium", ("fixed", 20)), ("large", ("fixed", 30))],
)
def test_batch_presets_map_to_size_modes(admin_client, tmp_path, preset, expected):
    _, client, module = admin_client
    _upload(client, _fully_inked(tmp_path, 300, 200), preset)
    (image,) = module.get_image_manager().get_all_images()
    assert (image.size_mode, image.size_value) == expected


def test_ac5_small_preset_generates_a_15x10_puzzle_end_to_end(admin_client, tmp_path):
    app, client, _ = admin_client
    _upload(client, _fully_inked(tmp_path, 300, 200), "small")

    response = client.post("/batch/generate-puzzles", data={}, follow_redirects=False)
    assert response.status_code == 302
    match = re.search(r"/batch/([^/]+)/generated-puzzles", response.location)
    assert match, response.location

    (puzzle,) = app.batch_generator.get_batch_puzzles(match.group(1), offset=0, limit=10)
    grid = puzzle["grid"]
    assert (len(grid[0]), len(grid)) == (15, 10)


def test_preview_page_keeps_the_short_mode_through_its_save_round_trip(
    admin_client, tmp_path
):
    """The per-image dropdown used to render with no selected option, so the
    page's own submit posted every image back as its first option — which
    would have turned "short" back into fixed-10, the forced square."""
    _, client, module = admin_client
    _upload(client, _fully_inked(tmp_path, 300, 200), "small")
    (image,) = module.get_image_manager().get_all_images()

    body = _normalized(client.get("/batch/preview-images").get_data(as_text=True))
    assert '<option value="short" selected>' in body
    assert '<option value="fixed" selected>' not in body
    assert "15×10" in body

    response = client.post(
        "/batch/preview-images",
        data={
            "save_config": "1",
            f"mode_{image.file_id}": "short",
            f"value_{image.file_id}": "12",
            f"name_{image.file_id}": image.puzzle_name,
        },
    )
    assert response.status_code == 302
    assert (image.size_mode, image.size_value) == ("short", 12)
    assert image.predict_size() == (18, 12)


def test_preview_page_keeps_the_auto_mode_through_its_save_round_trip(
    admin_client, tmp_path
):
    """The same dropdown bug silently turned the "auto" preset (max mode)
    into fixed-20 on save; it now survives."""
    _, client, module = admin_client
    _upload(client, _fully_inked(tmp_path, 300, 200), "auto")
    (image,) = module.get_image_manager().get_all_images()
    assert image.size_mode == "max"

    body = _normalized(client.get("/batch/preview-images").get_data(as_text=True))
    assert '<option value="max" selected>' in body

    response = client.post(
        "/batch/preview-images",
        data={
            "save_config": "1",
            f"mode_{image.file_id}": "max",
            f"value_{image.file_id}": str(image.size_value),
            f"name_{image.file_id}": image.puzzle_name,
        },
    )
    assert response.status_code == 302
    assert image.size_mode == "max"
    assert image.predict_size() == (30, 20)


def test_a_picture_too_elongated_for_any_size_is_marked_on_both_pages(
    admin_client, tmp_path
):
    """4:1 at "small": since CARD-064 skipped with a message, instead of
    CARD-061's over-the-cap note."""
    _, client, _ = admin_client
    _upload(client, _fully_inked(tmp_path, 400, 100), "small")

    preview = _normalized(client.get("/batch/preview-images").get_data(as_text=True))
    assert "this picture will be skipped" in preview
    assert "Too elongated for this short side" not in preview

    confirm = _normalized(client.get("/batch/generate-puzzles").get_data(as_text=True))
    assert "will be skipped" in confirm
