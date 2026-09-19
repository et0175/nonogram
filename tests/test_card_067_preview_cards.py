"""CARD-067 — the preview card's remaining three criteria.

    AC-1  the picture sits to the LEFT of the card's fields, not above them
    AC-2  each card states the picture's ink ratio
    AC-5  a picture can be removed from the job

The other three criteria (AC-3, AC-4, AC-6 — live predicted output, and no
sizing arithmetic in JavaScript) shipped on `main` while this card waited, in
`db4e0dc` and `f773015`. They are not re-tested here: `_size_fit_prediction.html`
and its own tests own them, and a second copy of that claim would be a second
thing to keep true. See the card's Revision.

**The ratio is the ink box's, not the file's.** `ImageFile._source_shape()` is
the extent the sizing actually follows (FR-022 — the picture's ink bounding
box, not its paper), so a ratio read off the file would contradict the
predicted size on any picture with a margin. The fixtures below include
exactly that case, because it is the one where the two answers differ.
"""

from __future__ import annotations

import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest
from PIL import Image as PILImage, ImageDraw

from nonogram.admin.image_manager import ImageFile, ImageManager


@pytest.fixture
def temp_images_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def _margined_image(temp_images_dir, name: str = "margined.png") -> Path:
    """A 4:3 *file* whose ink is 2:1 — the case the two ratios disagree on.

    600x450 of paper with a 400x200 block of ink in the middle. A ratio taken
    from the file says 1.33:1; the sizing follows the ink box and says 2.00:1.
    """
    img = PILImage.new("L", (600, 450), color=255)
    draw = ImageDraw.Draw(img)
    draw.rectangle([(100, 125), (499, 324)], fill=0)
    path = temp_images_dir / name
    img.save(path)
    return path


def _square_image(temp_images_dir, name: str = "square.png") -> Path:
    img = PILImage.new("L", (400, 400), color=255)
    draw = ImageDraw.Draw(img)
    draw.rectangle([(50, 50), (349, 349)], fill=0)
    path = temp_images_dir / name
    img.save(path)
    return path


def _degenerate_image() -> ImageFile:
    """The state a silently-failed second decode leaves behind (CARD-045):
    ``dimensions == (0, 0)`` and a path that cannot be re-read, so
    ``_source_shape`` falls back to ``(0, 0)`` too.

    Not an all-paper picture — that is *not* degenerate. ``ink_bounding_box``
    returns the whole frame when it finds no ink, so a blank sheet has a
    perfectly good shape and a perfectly good ratio (CARD-079 met the same
    fallback from the other side). The branch this test covers is reached only
    when there is no readable picture at all.
    """
    return ImageFile(
        file_id="deadbeef",
        filename="deadbeef.png",
        original_filename="broken.png",
        file_path="/nonexistent/does-not-exist.png",
        file_size=0,
        dimensions=(0, 0),
        format="PNG",
        uploaded_at=datetime.now(timezone.utc),
    )


# --------------------------------------------------------------------------
# AC-2 — the ink ratio
# --------------------------------------------------------------------------


def test_the_ink_ratio_describes_the_box_the_sizing_follows(temp_images_dir) -> None:
    """AC-2: the ratio explains the predicted size instead of contradicting it.

    The fixture is 4:3 as a file and 2:1 as ink. The card shows 2.00:1,
    because that is the shape `size_fit()` derives its extent from — a
    reviewer comparing the two numbers has to find them consistent, which is
    the whole point of putting the ratio on the card.
    """
    manager = ImageManager(temp_dir=str(temp_images_dir))
    image = manager.add_image(str(_margined_image(temp_images_dir)), "margined.png")

    assert image.ink_ratio() == "2.00:1"
    assert image.ink_box() == "400×200 px"


def test_the_ink_ratio_of_a_square_picture_is_one_to_one(temp_images_dir) -> None:
    """The ordinary case, and the one a reader checks the format against."""
    manager = ImageManager(temp_dir=str(temp_images_dir))
    image = manager.add_image(str(_square_image(temp_images_dir)), "square.png")

    assert image.ink_ratio() == "1.00:1"


def test_an_unreadable_picture_states_no_ratio() -> None:
    """A degenerate shape has no ratio, and says so rather than dividing by it.

    An em dash, not ``"0.00:1"`` and not a crash: the card is a description of
    the picture, and "there is nothing here to measure" is the honest one. The
    row exists — the batch page still has to render it — which is why this
    cannot simply raise.
    """
    image = _degenerate_image()

    assert image.ink_ratio() == "—"
    assert image.ink_box() == "unreadable"


def test_a_picture_that_is_all_paper_still_has_a_ratio(temp_images_dir) -> None:
    """The neighbouring case, pinned so the two are not confused.

    An all-paper sheet is not degenerate: ``ink_bounding_box`` falls back to
    the whole frame when it finds no ink, so the shape is the file's and the
    ratio is real. Worth its own test because "blank" sounds like the
    degenerate case and is not.
    """
    blank = temp_images_dir / "blank.png"
    PILImage.new("L", (300, 200), color=255).save(blank)
    manager = ImageManager(temp_dir=str(temp_images_dir))
    image = manager.add_image(str(blank), "blank.png")

    assert image.ink_ratio() == "1.50:1"


def test_the_ratio_is_read_from_the_cached_shape_not_a_fresh_decode(
    temp_images_dir,
) -> None:
    """Both helpers go through ``_source_shape``, which caches.

    Asserted because the alternative — each helper opening the file itself —
    costs a decode per card per render and would drift from the sizing the
    moment either read a different box.
    """
    manager = ImageManager(temp_dir=str(temp_images_dir))
    image = manager.add_image(str(_margined_image(temp_images_dir)), "margined.png")

    # Warm the cache, then take the file away. A helper that opened the file
    # itself would now answer differently — or raise.
    assert image.ink_ratio() == "2.00:1"
    Path(image.file_path).unlink()

    assert image.ink_ratio() == "2.00:1"
    assert image.ink_box() == "400×200 px"


# --------------------------------------------------------------------------
# AC-1 / AC-2 — how the card is laid out
# --------------------------------------------------------------------------


def _preview_markup() -> str:
    return Path("src/nonogram/admin/templates/image_preview.html").read_text(
        encoding="utf-8"
    )


def test_the_picture_sits_left_of_the_cards_fields() -> None:
    """AC-1, the owner's first item: "image preview to the left of the cards".

    The page put the thumbnail *above* the fields until this card. Asserted on
    the markup rather than on a rendered screenshot: what makes it a left-hand
    column is that the picture and the fields are two columns of one row, and
    that is a structural fact a test can hold.
    """
    markup = _preview_markup()
    body = markup[markup.index("card-body") :]

    row = body.index('class="row')
    picture = body.index("_size_fit_box.html")
    fields = body.index("Puzzle name")

    assert row < picture < fields, (
        "the picture and the fields must be two columns of one row, picture first"
    )
    assert re.search(r'class="col-\w*-?5[^"]*"[^>]*>\s*(<!--.*?-->\s*)?<div class="thumb', body, re.S), (
        "the picture column is missing; see AC-1"
    )


def test_the_card_states_the_ink_ratio_beside_the_name() -> None:
    """AC-2 at the page: the number reaches the card, with the box as its title."""
    markup = _preview_markup()

    assert "ink_ratio()" in markup
    assert "ink_box()" in markup


# --------------------------------------------------------------------------
# AC-5 — removing a picture
# --------------------------------------------------------------------------


def test_removing_a_picture_drops_that_one_and_leaves_the_others(
    temp_images_dir,
) -> None:
    """AC-5, and the review's F-003: *that* picture, not *a* picture.

    Cycle 1 of the retired branch had a test that could not tell "removes the
    requested picture" from "removes the first one". Three pictures, and the
    middle one is removed, so neither mistake passes.
    """
    manager = ImageManager(temp_dir=str(temp_images_dir))
    first = manager.add_image(str(_square_image(temp_images_dir, "a.png")), "a.png")
    middle = manager.add_image(str(_square_image(temp_images_dir, "b.png")), "b.png")
    last = manager.add_image(str(_square_image(temp_images_dir, "c.png")), "c.png")

    assert manager.remove_image(middle.file_id) is True

    remaining = [image.file_id for image in manager.get_all_images()]
    assert remaining == [first.file_id, last.file_id]
    assert not Path(middle.file_path).exists(), "the temp file goes with the row"


def test_removing_an_unknown_picture_is_refused_not_guessed(temp_images_dir) -> None:
    manager = ImageManager(temp_dir=str(temp_images_dir))
    manager.add_image(str(_square_image(temp_images_dir)), "square.png")

    assert manager.remove_image("no-such-id") is False
    assert len(manager.get_all_images()) == 1


@pytest.fixture
def flask_client(tmp_path, monkeypatch):
    """The admin in memory, with its own image store — the harness
    ``tests/test_card_058_*`` uses, for the same reason: these criteria are
    about a rendered page and a route, not about the store in isolation."""
    monkeypatch.delenv("DATABASE_URL", raising=False)

    from nonogram.admin import image_manager as img_mgr_module
    from nonogram.admin.app import create_app

    img_mgr_module._image_manager = None
    app = create_app(debug=True)
    app.config["TESTING"] = True

    yield app.test_client(), img_mgr_module

    img_mgr_module._image_manager = None


def test_the_page_offers_a_remove_control_for_each_picture(
    flask_client, tmp_path
) -> None:
    """AC-5 at the page: a POST form per picture, aimed at that picture.

    Rendered rather than grepped from the template, because the action comes
    from ``url_for`` and a template grep would pass on a route that does not
    exist. Two pictures, so "per picture" is visible: each form names its own
    file id, which is also what stops the button removing the first row
    whatever was clicked (cycle 1's F-003).
    """
    client, img_mgr_module = flask_client
    manager = img_mgr_module.get_image_manager(temp_dir=str(tmp_path))
    first = manager.add_image(str(_square_image(tmp_path, "a.png")), "a.png")
    second = manager.add_image(str(_square_image(tmp_path, "b.png")), "b.png")

    body = client.get("/batch/preview-images").get_data(as_text=True)

    assert f"/batch/image/{first.file_id}/remove" in body
    assert f"/batch/image/{second.file_id}/remove" in body
    assert body.lower().count('method="post"') >= 2


def test_posting_the_remove_form_drops_that_picture_and_returns_to_the_page(
    flask_client, tmp_path
) -> None:
    """AC-5 end to end, through the route the form posts to."""
    client, img_mgr_module = flask_client
    manager = img_mgr_module.get_image_manager(temp_dir=str(tmp_path))
    keep = manager.add_image(str(_square_image(tmp_path, "keep.png")), "keep.png")
    drop = manager.add_image(str(_square_image(tmp_path, "drop.png")), "drop.png")

    response = client.post(
        f"/batch/image/{drop.file_id}/remove", follow_redirects=True
    )

    assert response.status_code == 200
    assert [image.file_id for image in manager.get_all_images()] == [keep.file_id]
    assert "drop.png" in response.get_data(as_text=True), "the page says what it did"


def test_removing_a_picture_that_is_already_gone_says_so(
    flask_client, tmp_path
) -> None:
    """A stale page's button must not look like it worked.

    The row is gone either way, so the redirect is the same; what differs is
    that the user is told, rather than shown a success message for a removal
    that did not happen.
    """
    client, img_mgr_module = flask_client
    img_mgr_module.get_image_manager(temp_dir=str(tmp_path))

    response = client.post("/batch/image/no-such-id/remove", follow_redirects=True)

    assert response.status_code == 200
    assert "no longer in this batch" in response.get_data(as_text=True)
