"""CARD-058 made admin's silent size substitution visible. CARD-064 replaced
the substitution itself: a size that would cut the picture now moves to
Large, or — as for the 20:1 picture below — the picture is skipped with a
message. These tests keep CARD-058's intent (nothing about a picture's size
changes silently) against the new behaviour.

AC-1 — a picture whose chosen size cannot be used is visibly marked on both
       the preview and the generate-confirmation pages.
AC-2 — a picture that fits its chosen size carries no mark on either page.
AC-3 — ``predict_size()`` still returns a (width, height) pair for both.
"""

import re
import tempfile
from pathlib import Path

import pytest
from PIL import Image as PILImage, ImageDraw

from nonogram.admin.image_manager import CANNOT_FIT, FITS, MIN_KEPT_SHARE, ImageManager


def _normalized(body: str) -> str:
    """Collapse runs of whitespace (the HTML source's own indentation and
    line-wrapping inside a rendered sentence) to a single space, matching
    how a browser displays the text.
    """
    return re.sub(r"\s+", " ", body)


@pytest.fixture
def temp_images_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def _elongated_image_path(temp_images_dir) -> Path:
    """A 2000x100 (20:1) fully-inked image — too elongated for any supported
    grid: even Large's 30x10 keeps 15% of it."""
    img = PILImage.new("L", (2000, 100), color=255)
    draw = ImageDraw.Draw(img)
    draw.rectangle([(0, 0), (1999, 99)], fill=0)
    path = temp_images_dir / "elongated.png"
    img.save(path)
    return path


def _normal_image_path(temp_images_dir) -> Path:
    """A roughly square, fully-inked image — fits every size mode."""
    img = PILImage.new("L", (500, 500), color=255)
    draw = ImageDraw.Draw(img)
    draw.rectangle([(50, 50), (450, 450)], fill=0)
    path = temp_images_dir / "normal.png"
    img.save(path)
    return path


class TestAC3PredictSize:
    def test_predict_size_for_a_picture_that_cannot_fit(self, temp_images_dir):
        manager = ImageManager(temp_dir=str(temp_images_dir))
        image = manager.add_image(str(_elongated_image_path(temp_images_dir)), "elongated.png")
        image.size_mode = "fixed"
        image.size_value = 10

        assert image.predict_size() == (30, 10)

    def test_predict_size_for_the_normal_case(self, temp_images_dir):
        manager = ImageManager(temp_dir=str(temp_images_dir))
        image = manager.add_image(str(_normal_image_path(temp_images_dir)), "normal.png")

        assert image.predict_size() == (20, 20)


class TestSizeFitUnit:
    def test_a_twenty_to_one_picture_cannot_fit(self, temp_images_dir):
        manager = ImageManager(temp_dir=str(temp_images_dir))
        image = manager.add_image(str(_elongated_image_path(temp_images_dir)), "elongated.png")
        image.size_mode = "fixed"
        image.size_value = 10

        fit = image.size_fit()
        assert fit.status == CANNOT_FIT
        assert fit.kept < MIN_KEPT_SHARE
        assert fit.extent == image.predict_size()

    def test_the_common_case_fits(self, temp_images_dir):
        manager = ImageManager(temp_dir=str(temp_images_dir))
        image = manager.add_image(str(_normal_image_path(temp_images_dir)), "normal.png")

        assert image.size_fit().status == FITS

    def test_the_degenerate_zero_dimension_case_fits_quietly(self):
        """A (0, 0)-dimensioned image (CARD-045's degenerate-decode state) has
        no shape to judge: the smallest square, reported as fitting rather
        than as a change nobody asked about."""
        from datetime import datetime

        from nonogram.admin.image_manager import ImageFile

        image = ImageFile(
            file_id="deadbeef",
            filename="deadbeef.png",
            original_filename="broken.png",
            file_path="/nonexistent/does-not-exist.png",
            file_size=0,
            dimensions=(0, 0),
            format="PNG",
            uploaded_at=datetime.utcnow(),
        )

        assert image.predict_size() == (10, 10)
        assert image.size_fit().status == FITS


class TestAC1And2TemplateVisibility:
    """Integration tests through the real Flask app."""

    @pytest.fixture
    def flask_client(self, tmp_path, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)

        from nonogram.admin import image_manager as img_mgr_module
        from nonogram.admin.app import create_app

        img_mgr_module._image_manager = None

        app = create_app(debug=True)
        app.config["TESTING"] = True
        client = app.test_client()

        yield client, img_mgr_module, tmp_path

        img_mgr_module._image_manager = None

    def _add_elongated_image(self, img_mgr_module, tmp_path):
        mgr = img_mgr_module.get_image_manager(temp_dir=str(tmp_path))
        image = mgr.add_image(str(_elongated_image_path(tmp_path)), "elongated.png")
        assert image is not None
        mgr.update_image_size(image.file_id, "fixed", 10)
        return mgr, image

    def _add_normal_image(self, img_mgr_module, tmp_path):
        mgr = img_mgr_module.get_image_manager(temp_dir=str(tmp_path))
        image = mgr.add_image(str(_normal_image_path(tmp_path)), "normal.png")
        assert image is not None
        return mgr, image

    def test_preview_page_marks_a_picture_that_will_be_skipped(self, flask_client):
        client, img_mgr_module, tmp_path = flask_client
        self._add_elongated_image(img_mgr_module, tmp_path)

        response = client.get("/batch/preview-images")

        assert response.status_code == 200
        body = _normalized(response.data.decode("utf-8"))
        assert "this picture will be skipped" in body

    def test_preview_page_shows_no_mark_for_a_normal_image(self, flask_client):
        client, img_mgr_module, tmp_path = flask_client
        self._add_normal_image(img_mgr_module, tmp_path)

        response = client.get("/batch/preview-images")

        assert response.status_code == 200
        body = _normalized(response.data.decode("utf-8"))
        assert "will be skipped" not in body
        assert "would cut this picture" not in body

    def test_generate_confirmation_page_marks_a_picture_that_will_be_skipped(
        self, flask_client
    ):
        client, img_mgr_module, tmp_path = flask_client
        self._add_elongated_image(img_mgr_module, tmp_path)

        response = client.get("/batch/generate-puzzles")

        assert response.status_code == 200
        body = _normalized(response.data.decode("utf-8"))
        assert "will be skipped" in body

    def test_generate_confirmation_page_shows_no_mark_for_a_normal_image(
        self, flask_client
    ):
        client, img_mgr_module, tmp_path = flask_client
        self._add_normal_image(img_mgr_module, tmp_path)

        response = client.get("/batch/generate-puzzles")

        assert response.status_code == 200
        body = _normalized(response.data.decode("utf-8"))
        assert "will be skipped" not in body
        assert "moved to Large" not in body
