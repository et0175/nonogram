"""CARD-065: small follow-ups from CARD-061..064.

AC-1 — a share prints as a whole percent rounded DOWN, in the batch results
       and on the preview, so a grid keeping less than MIN_KEPT_SHARE never
       reads "90%".
AC-2 — the batch form's preset labels say what each preset does, checked
       against SIZE_PRESETS rather than restated literals.
AC-3 — the two puzzle filters are labelled in cells, not pixels.
"""

import re
from pathlib import Path

import pytest
from PIL import Image as PILImage

import nonogram.admin.image_manager as image_manager_module
from nonogram.admin.image_manager import MIN_KEPT_SHARE, SIZE_PRESETS, floor_percent

TEMPLATES = Path(__file__).resolve().parents[1] / "src" / "nonogram" / "admin" / "templates"


def _normalized(body: str) -> str:
    return re.sub(r"\s+", " ", body)


@pytest.mark.parametrize(
    "share, shown",
    [
        (0.897, "89%"),
        (0.8999, "89%"),
        (0.8869, "88%"),
        (0.9, "90%"),
        (0.6, "60%"),
        (1.0, "100%"),
    ],
)
def test_ac1_a_share_is_rounded_down(share, shown):
    assert floor_percent(share) == shown


def test_ac1_the_threshold_itself_reads_ninety():
    """0.9 must not fall to 89% — the boundary is inclusive."""
    assert floor_percent(MIN_KEPT_SHARE) == "90%"


@pytest.fixture
def admin_client(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TESTING", "true")
    from nonogram.admin.app import create_app

    image_manager_module._image_manager = None
    app = create_app()
    app.config["TESTING"] = True
    with app.app_context():
        yield app.test_client()
    image_manager_module._image_manager = None


def _upload(client, tmp_path, shape, default_size="medium"):
    path = tmp_path / "picture.png"
    PILImage.new("L", shape, color=0).save(path)
    with open(path, "rb") as handle:
        response = client.post(
            "/batch/from-images",
            data={
                "image_files": [(handle, "picture.png")],
                "default_size": default_size,
            },
            content_type="multipart/form-data",
        )
    assert response.status_code == 302, response.data


def test_ac1_the_preview_never_rounds_a_share_up(admin_client, tmp_path):
    """c4's shape (116x262) at Medium: 10x20 keeps 88.5% of it. Rounding to
    nearest would print 89%, which reads as "almost fits" for a picture the
    batch is about to move to Large."""
    _upload(admin_client, tmp_path, (116, 262))

    body = _normalized(admin_client.get("/batch/preview-images").get_data(as_text=True))

    assert "would cut this picture (keeps 88%)" in body
    assert "keeps 89%" not in body


def test_ac2_the_preset_labels_match_the_preset_table(admin_client, tmp_path):
    """Small says "short side", Medium and Large say "long side", each with
    the value the route will actually apply."""
    body = _normalized(admin_client.get("/batch/select-images").get_data(as_text=True))

    for preset in ("small", "medium", "large"):
        value, mode = SIZE_PRESETS[preset]
        side = "short" if mode == "short" else "long"
        assert f"{value} cells on the {side} side" in body, preset


@pytest.mark.parametrize("name", ["puzzles_list.html", "book_select_puzzles.html"])
def test_ac3_the_filters_are_labelled_in_cells(name):
    source = (TEMPLATES / name).read_text(encoding="utf-8")
    assert "Size (cells)" in source
    assert "Size (px)" not in source


def test_ac3_the_rendered_puzzle_filter_says_cells(admin_client):
    body = admin_client.get("/puzzles").get_data(as_text=True)
    assert "Size (cells)" in body


def test_ac7_the_dead_image_selection_template_is_gone():
    """No route rendered it and no template included it; it carried its own
    copy of the S/M/L presets through a JavaScript applyDefaultSize()."""
    assert not (TEMPLATES / "image_selection.html").exists()
