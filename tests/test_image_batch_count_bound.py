"""CARD-094 AC-3 — the image batch refuses the same selections at preview as at generate.

CARD-088 lowered the batch ceiling from 200 to 50 and made ``create_batch`` read
``MAX_BATCH_COUNT`` instead of repeating the number. The image preview route
kept its own ``> 200`` and the batch form kept saying "Up to 200 pictures", so a
selection of 51-200 pictures passed preview and was refused one step later, at
generate. One bound, read in every place that states it.

The ceiling is patched down to 2 so the test uploads three tiny pictures rather
than fifty-one: a route that still compared against a literal would accept
three and fail here.
"""

from __future__ import annotations

import pytest
from PIL import Image as PILImage

from nonogram import orchestrator


@pytest.fixture
def admin_app(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TESTING", "true")
    import nonogram.admin.image_manager as image_manager_module

    image_manager_module._image_manager = None
    from nonogram.admin.app import create_app

    app = create_app()
    app.config["TESTING"] = True
    with app.app_context():
        yield app
    image_manager_module._image_manager = None


def _upload(client, tmp_path, count: int) -> None:
    files = []
    for index in range(count):
        path = tmp_path / f"picture-{index}.png"
        PILImage.new("L", (200, 200), color=0).save(path)
        files.append((open(path, "rb"), path.name))
    try:
        response = client.post(
            "/batch/from-images",
            data={"image_files": files},
            content_type="multipart/form-data",
        )
    finally:
        for handle, _ in files:
            handle.close()
    assert response.status_code == 302


def _preview(client) -> str:
    return client.post("/batch/preview-images", data={}).get_data(as_text=True)


def test_a_selection_over_the_ceiling_is_refused_at_preview(admin_app, monkeypatch, tmp_path):
    import nonogram.admin.app as app_module

    monkeypatch.setattr(app_module, "MAX_BATCH_COUNT", 2)
    client = admin_app.test_client()
    _upload(client, tmp_path, 3)

    body = _preview(client)

    assert "Invalid image count: 3" in body
    assert "Must be 1-2 images" in body


def test_a_selection_at_the_ceiling_is_not_refused(admin_app, monkeypatch, tmp_path):
    import nonogram.admin.app as app_module

    monkeypatch.setattr(app_module, "MAX_BATCH_COUNT", 2)
    client = admin_app.test_client()
    _upload(client, tmp_path, 2)

    body = _preview(client)

    assert "Invalid image count" not in body


def test_the_batch_form_states_the_real_ceiling(admin_app):
    body = admin_app.test_client().get("/batch/create").get_data(as_text=True)

    assert f"Up to {orchestrator.MAX_BATCH_COUNT} pictures per batch" in body
    assert "200 pictures" not in body
