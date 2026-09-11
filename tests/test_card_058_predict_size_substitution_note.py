"""CARD-058: surface a visible note when ImageFile.predict_size() silently
substitutes a workable puzzle size instead of the CLI-style refusal
ADR-0022/R4 would give (see image_manager.py's SizeTooSmallForSource
handling). The substitution behavior itself is deliberate, accepted UX
(confirmed 2026-09-11) and unchanged by this card (G-2) — only its
visibility changes.

AC-1 — a batch image that hits the substitution path shows a visible note
       distinguishing the requested size from the size actually used, on
       both the preview and generate-confirmation pages.
AC-2 — a batch image that does NOT hit the substitution path shows no note,
       on both pages (no regression to the common case).
AC-3 — predict_size()'s returned (width, height) is unchanged for every
       image by this card.
"""

import re
import tempfile
from pathlib import Path

import pytest
from PIL import Image as PILImage, ImageDraw

from nonogram.admin.image_manager import ImageManager


def _normalized(body: str) -> str:
    """Collapse runs of whitespace (the HTML source's own indentation and
    line-wrapping inside a rendered sentence, e.g. "too\\n    small") to a
    single space, matching how a browser actually displays the text rather
    than how Jinja's template indentation happens to wrap the raw HTML
    source.
    """
    return re.sub(r"\s+", " ", body)


@pytest.fixture
def temp_images_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def _elongated_image_path(temp_images_dir) -> Path:
    """A 2000x100 (20:1) fully-inked image — steep enough that a small
    requested size (N/5:1 ceiling, e.g. N=10 -> 2:1 max) forces
    predict_size()'s SizeTooSmallForSource substitution path.
    """
    img = PILImage.new("L", (2000, 100), color=255)
    draw = ImageDraw.Draw(img)
    draw.rectangle([(0, 0), (1999, 99)], fill=0)
    path = temp_images_dir / "elongated.png"
    img.save(path)
    return path


def _normal_image_path(temp_images_dir) -> Path:
    """A roughly square, fully-inked image — never hits the substitution
    path at any of the three size modes.
    """
    img = PILImage.new("L", (500, 500), color=255)
    draw = ImageDraw.Draw(img)
    draw.rectangle([(50, 50), (450, 450)], fill=0)
    path = temp_images_dir / "normal.png"
    img.save(path)
    return path


class TestAC3PredictSizeUnchanged:
    def test_predict_size_still_returns_a_two_tuple_for_the_substitution_case(
        self, temp_images_dir
    ):
        manager = ImageManager(temp_dir=str(temp_images_dir))
        image = manager.add_image(str(_elongated_image_path(temp_images_dir)), "elongated.png")
        image.size_mode = "fixed"
        image.size_value = 10

        width, height = image.predict_size()
        assert (width, height) == (30, 10)

    def test_predict_size_still_returns_a_two_tuple_for_the_normal_case(
        self, temp_images_dir
    ):
        manager = ImageManager(temp_dir=str(temp_images_dir))
        image = manager.add_image(str(_normal_image_path(temp_images_dir)), "normal.png")

        width, height = image.predict_size()
        assert (width, height) == (20, 20)


class TestSizeSubstitutionUnit:
    def test_size_substitution_reports_requested_vs_used_when_triggered(
        self, temp_images_dir
    ):
        manager = ImageManager(temp_dir=str(temp_images_dir))
        image = manager.add_image(str(_elongated_image_path(temp_images_dir)), "elongated.png")
        image.size_mode = "fixed"
        image.size_value = 10

        substitution = image.size_substitution()
        assert substitution == {"requested": 10, "used": 30}
        # And predict_size()'s long edge matches "used".
        assert max(image.predict_size()) == substitution["used"]

    def test_size_substitution_is_none_for_the_common_case(self, temp_images_dir):
        manager = ImageManager(temp_dir=str(temp_images_dir))
        image = manager.add_image(str(_normal_image_path(temp_images_dir)), "normal.png")

        assert image.size_substitution() is None

    def test_size_substitution_is_none_for_the_degenerate_zero_dimension_case(self):
        """A (0, 0)-dimensioned image (CARD-045's degenerate-decode state)
        takes predict_size()'s ValueError fallback, not the
        SizeTooSmallForSource substitution path — there was never a real
        "requested" N to compare against a nonexistent picture, so this
        must not be reported as a substitution.
        """
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
        assert image.size_substitution() is None


class TestAC1And2TemplateVisibility:
    """Integration tests through the real Flask app, mirroring the
    existing degenerate-image integration test style in
    tests/test_image_batch_size_fix.py.
    """

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

    def test_preview_page_shows_the_note_when_substitution_happens(self, flask_client):
        client, img_mgr_module, tmp_path = flask_client
        self._add_elongated_image(img_mgr_module, tmp_path)

        response = client.get("/batch/preview-images")

        assert response.status_code == 200
        body = _normalized(response.data.decode("utf-8"))
        assert "too small for this picture" in body
        assert "Requested 10" in body and "using 30 instead" in body

    def test_preview_page_shows_no_note_for_a_normal_image(self, flask_client):
        client, img_mgr_module, tmp_path = flask_client
        self._add_normal_image(img_mgr_module, tmp_path)

        response = client.get("/batch/preview-images")

        assert response.status_code == 200
        body = _normalized(response.data.decode("utf-8"))
        assert "too small for this picture" not in body

    def test_generate_confirmation_page_shows_the_note_when_substitution_happens(
        self, flask_client
    ):
        client, img_mgr_module, tmp_path = flask_client
        self._add_elongated_image(img_mgr_module, tmp_path)

        response = client.get("/batch/generate-puzzles")

        assert response.status_code == 200
        body = _normalized(response.data.decode("utf-8"))
        assert "size adjusted" in body
        assert "too small for this picture" in body

    def test_generate_confirmation_page_shows_no_note_for_a_normal_image(
        self, flask_client
    ):
        client, img_mgr_module, tmp_path = flask_client
        self._add_normal_image(img_mgr_module, tmp_path)

        response = client.get("/batch/generate-puzzles")

        assert response.status_code == 200
        body = _normalized(response.data.decode("utf-8"))
        assert "size adjusted" not in body
        assert "too small for this picture" not in body
