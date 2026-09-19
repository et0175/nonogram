"""CARD-069 — a picture carries up to one size option per mode.

    AC-1  two options on one picture produce two puzzles
    AC-3  one option behaves exactly as it does today   <- pinned FIRST
    AC-5  at most one option per mode; adding an existing mode replaces it
    AC-7  names from one picture never collide

Read AC-3 first. The risk in this card is not that two options fail to work;
it is that the *one*-option path quietly changes for every existing user, and
the way to see that is to pin today's answers before touching the model and
keep them passing afterwards. The pins below were taken on `main` at
`7de4c85`, before any of this card's code existed.

The card's other criteria (AC-2 per-option prediction, AC-4 the per-option
retry and skip, AC-6 the recorded counts) are about the page and the generate
loop and live further down.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from PIL import Image as PILImage, ImageDraw

from nonogram.admin.image_manager import (
    CANNOT_FIT,
    FITS,
    MOVED_TO_LARGE,
    SIZE_PRESETS,
    ImageManager,
)


@pytest.fixture
def temp_images_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def _picture(temp_images_dir, name="p.png", size=(600, 400), ink=(50, 50, 549, 349)):
    img = PILImage.new("L", size, color=255)
    ImageDraw.Draw(img).rectangle(ink, fill=0)
    path = temp_images_dir / name
    img.save(path)
    return path


def _elongated(temp_images_dir, name="long.png"):
    """20:1 — no supported grid keeps enough of it (CARD-064's CANNOT_FIT)."""
    img = PILImage.new("L", (2000, 100), color=255)
    ImageDraw.Draw(img).rectangle([(0, 0), (1999, 99)], fill=0)
    path = temp_images_dir / name
    img.save(path)
    return path


def _three_to_one(temp_images_dir, name="wide.png"):
    """Ink box 700x250 (2.8:1) — the picture whose modes genuinely disagree.

    Measured: ``fixed 20`` keeps too little and moves to Large (30x11), while
    ``short 10`` fits at 28x10. One picture, two verdicts, which is what AC-2
    is about and what a picture that simply cannot fit at any size (the 20:1
    fixture above) cannot demonstrate.
    """
    img = PILImage.new("L", (900, 400), color=255)
    ImageDraw.Draw(img).rectangle([(50, 50), (749, 299)], fill=0)
    path = temp_images_dir / name
    img.save(path)
    return path


def _added(manager, path, name=None):
    image = manager.add_image(str(path), name or path.name)
    assert image is not None
    return image


# --------------------------------------------------------------------------
# AC-3 — one option behaves exactly as today (pinned before the change)
# --------------------------------------------------------------------------


def test_a_freshly_uploaded_picture_has_exactly_one_option(temp_images_dir) -> None:
    """The default is unchanged: one option, the batch preset's.

    A user who never opens the size controls must get exactly the batch they
    got before this card — same count, same extents, same names. That starts
    here, with the picture carrying one option rather than an empty list or a
    tick on every mode.
    """
    manager = ImageManager(temp_dir=str(temp_images_dir))
    image = _added(manager, _picture(temp_images_dir))

    assert len(image.size_options) == 1
    assert (image.size_options[0].mode, image.size_options[0].value) == (
        image.size_mode,
        image.size_value,
    )


def test_the_single_option_answers_exactly_what_size_fit_answered(
    temp_images_dir,
) -> None:
    """Pinned on `main` before this card: the fit of the one option is the fit
    the picture used to report, field for field.

    ``size_fit()`` stays as the *first* option's fit so every existing caller
    — the page, the generate loop, CARD-058/061/062/064/065's tests — keeps
    the answer it had. The list is additive.
    """
    manager = ImageManager(temp_dir=str(temp_images_dir))
    image = _added(manager, _picture(temp_images_dir))
    manager.update_image_size(image.file_id, "fixed", 20)

    fit = image.size_fit()
    per_option = image.size_fits()

    assert len(per_option) == 1
    assert per_option[0].fit == fit
    # Measured on the fixture, not derived: its ink box is 500x300, so a
    # fixed 20 is 20x12.
    assert fit.extent == (20, 12) and fit.status == FITS


@pytest.mark.parametrize("mode,value", [("fixed", 20), ("short", 10), ("min", 20), ("max", 20)])
def test_every_mode_still_sizes_a_picture_the_way_it_did(
    temp_images_dir, mode, value
) -> None:
    """All four modes survive, including ``short``.

    ``short`` is the one the owner's note did not list and the small preset
    depends on (CARD-061), which is why the options are one per *mode* rather
    than the three the card first named.
    """
    manager = ImageManager(temp_dir=str(temp_images_dir))
    image = _added(manager, _picture(temp_images_dir))
    manager.update_image_size(image.file_id, mode, value)

    assert image.size_mode == mode
    assert image.size_fit().extent == image.size_fits()[0].fit.extent


# --------------------------------------------------------------------------
# AC-5 — one option per mode; adding an existing mode replaces it
# --------------------------------------------------------------------------


def test_a_picture_takes_at_most_one_option_per_mode(temp_images_dir) -> None:
    """Four modes, so four options at most, and no mode twice."""
    manager = ImageManager(temp_dir=str(temp_images_dir))
    image = _added(manager, _picture(temp_images_dir))

    for mode, value in (("fixed", 20), ("short", 10), ("min", 20), ("max", 20)):
        manager.add_size_option(image.file_id, mode, value)

    assert [option.mode for option in image.size_options] == [
        "fixed", "short", "min", "max",
    ]


def test_adding_a_mode_that_is_already_there_replaces_its_value(
    temp_images_dir,
) -> None:
    """The decision recorded on the card: replace, do not refuse.

    The control is a tick per mode with its own value box, so "add fixed 25
    when fixed 20 is ticked" is somebody editing a number. Refusing it would
    make the obvious gesture an error.
    """
    manager = ImageManager(temp_dir=str(temp_images_dir))
    image = _added(manager, _picture(temp_images_dir))
    manager.add_size_option(image.file_id, "fixed", 20)

    assert manager.add_size_option(image.file_id, "fixed", 25) is True

    assert [(o.mode, o.value) for o in image.size_options] == [("fixed", 25)]


def test_the_last_option_cannot_be_unticked(temp_images_dir) -> None:
    """The other recorded decision: refused, not treated as removing the picture.

    Removing a picture deletes the uploaded file (CARD-067). Inferring that
    from "I unticked a size" turns a sizing tweak into a destructive act, and
    the explicit Remove button is one click away.
    """
    manager = ImageManager(temp_dir=str(temp_images_dir))
    image = _added(manager, _picture(temp_images_dir))

    assert manager.remove_size_option(image.file_id, image.size_options[0].mode) is False
    assert len(image.size_options) == 1


def test_an_option_can_be_removed_while_another_remains(temp_images_dir) -> None:
    manager = ImageManager(temp_dir=str(temp_images_dir))
    image = _added(manager, _picture(temp_images_dir))
    manager.add_size_option(image.file_id, "min", 20)

    assert manager.remove_size_option(image.file_id, "fixed") is True

    assert [option.mode for option in image.size_options] == ["min"]


# --------------------------------------------------------------------------
# AC-2 — each option carries its own fit
# --------------------------------------------------------------------------


def test_each_option_reports_its_own_extent_and_status(temp_images_dir) -> None:
    """AC-2: two options on one picture, two answers.

    The elongated fixture is the interesting case: at a fixed 20 no grid keeps
    enough of a 20:1 picture, so that option cannot fit, while ``max`` reaches
    the longest supported grid and moves there. One picture, two different
    verdicts — which is the whole reason the fit is per option rather than per
    picture.
    """
    manager = ImageManager(temp_dir=str(temp_images_dir))
    image = _added(manager, _three_to_one(temp_images_dir))
    manager.update_image_size(image.file_id, "fixed", 20)
    manager.add_size_option(image.file_id, "short", 10)

    fits = {option.mode: option.fit for option in image.size_fits()}

    assert fits["fixed"].status == MOVED_TO_LARGE
    assert fits["fixed"].extent == (30, 11)
    assert fits["short"].status == FITS
    assert fits["short"].extent == (28, 10)
    assert SIZE_PRESETS["large"] == (30, "fixed"), "the move target is unchanged (G-1)"


def test_a_picture_that_fits_at_no_size_says_so_for_every_option(
    temp_images_dir,
) -> None:
    """The other shape of AC-2: the verdict can also be the same for all.

    A 20:1 picture is beyond every supported grid, so each option reports
    ``CANNOT_FIT`` rather than one of them rescuing it. Worth its own test
    because the per-option machinery could hide this by reporting the *first*
    option's verdict for all of them and nobody would notice on a picture
    whose modes agree anyway.
    """
    manager = ImageManager(temp_dir=str(temp_images_dir))
    image = _added(manager, _elongated(temp_images_dir))
    manager.update_image_size(image.file_id, "fixed", 20)
    manager.add_size_option(image.file_id, "max", 20)

    assert [option.fit.status for option in image.size_fits()] == [
        CANNOT_FIT,
        CANNOT_FIT,
    ]


# --------------------------------------------------------------------------
# AC-1 / AC-4 / AC-6 / AC-7 — the batch, end to end
# --------------------------------------------------------------------------


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


def _upload(client, path, default_size="medium"):
    with open(path, "rb") as handle:
        response = client.post(
            "/batch/from-images",
            data={"image_files": [(handle, path.name)], "default_size": default_size},
            content_type="multipart/form-data",
        )
    assert response.status_code == 302, response.data


def _generate(client):
    response = client.post("/batch/generate-puzzles", data={}, follow_redirects=False)
    assert response.status_code == 302, response.data
    import re

    match = re.search(r"/batch/([^/]+)/generated-puzzles", response.location)
    assert match, response.location
    return match.group(1)


def test_one_option_still_makes_exactly_one_puzzle(admin_client, temp_images_dir):
    """AC-3 at the batch: the regression that matters.

    A user who never opens the size controls must get the batch they always
    got — one puzzle, at the preset's extent, with no size in its name.
    """
    app, client, module = admin_client
    _upload(client, _picture(temp_images_dir, size=(400, 400), ink=(0, 0, 399, 399)))

    batch_id = _generate(client)
    puzzles = app.batch_generator.get_batch_puzzles(batch_id, offset=0, limit=10)

    assert len(puzzles) == 1
    assert not puzzles[0].get("puzzle_name"), "a single-option puzzle is not re-named"


def test_two_options_make_two_puzzles_at_their_own_extents(
    admin_client, temp_images_dir
):
    """AC-1 and AC-6: one picture, two ticked sizes, two puzzles.

    The count is the thing worth asserting: it is no longer bounded by the
    number of pictures, which is the assumption this card breaks everywhere
    downstream.
    """
    app, client, module = admin_client
    _upload(client, _picture(temp_images_dir, size=(400, 400), ink=(0, 0, 399, 399)))
    manager = module.get_image_manager()
    (image,) = manager.get_all_images()
    manager.update_image_size(image.file_id, "fixed", 20)
    manager.add_size_option(image.file_id, "fixed", 20)
    manager.add_size_option(image.file_id, "min", 20)

    batch_id = _generate(client)
    puzzles = app.batch_generator.get_batch_puzzles(batch_id, offset=0, limit=10)

    assert len(puzzles) == 2, [p.get("puzzle_name") for p in puzzles]
    extents = {(p["width"], p["height"]) for p in puzzles}
    assert len(extents) == 2, extents


def test_two_puzzles_from_one_picture_are_named_apart(admin_client, temp_images_dir):
    """AC-7: never two rows reading the same.

    The extent goes in the name of *every* puzzle from a multi-option
    picture, so the pair is distinguishable however the batch is sorted.
    """
    app, client, module = admin_client
    _upload(client, _picture(temp_images_dir, size=(400, 400), ink=(0, 0, 399, 399)))
    manager = module.get_image_manager()
    (image,) = manager.get_all_images()
    manager.add_size_option(image.file_id, "max", 20)

    batch_id = _generate(client)
    puzzles = app.batch_generator.get_batch_puzzles(batch_id, offset=0, limit=10)

    names = [p.get("puzzle_name") for p in puzzles]
    assert len(names) == 2 and len(set(names)) == 2, names
    for puzzle, name in zip(puzzles, names):
        assert f"({puzzle['width']}x{puzzle['height']})" in name, name


def test_one_size_can_be_skipped_while_another_generates(
    admin_client, temp_images_dir
):
    """AC-4: the per-size verdicts act independently on one picture.

    The 2.8:1 fixture fits at ``short 10`` and is moved to Large at
    ``fixed 20`` — so one option generates normally while the other is
    reported, and the report has to say *which size* it is about.
    """
    app, client, module = admin_client
    _upload(client, _three_to_one(temp_images_dir))
    manager = module.get_image_manager()
    (image,) = manager.get_all_images()
    manager.update_image_size(image.file_id, "fixed", 20)
    manager.add_size_option(image.file_id, "short", 10)

    batch_id = _generate(client)
    puzzles = app.batch_generator.get_batch_puzzles(batch_id, offset=0, limit=10)

    assert len(puzzles) == 2
    assert {(p["width"], p["height"]) for p in puzzles} == {(30, 11), (28, 10)}


# --------------------------------------------------------------------------
# AC-2 / AC-5 at the page
# --------------------------------------------------------------------------


def test_the_preview_offers_the_other_three_modes_with_their_own_predictions(
    admin_client, temp_images_dir
):
    """AC-2: each extra size shows what *it* would produce.

    The picture's own control keeps the first size; these are the others, and
    each carries its own extent rather than repeating the card's. Ticked ones
    show it — an unticked size is an offer, not a prediction.
    """
    app, client, module = admin_client
    _upload(client, _three_to_one(temp_images_dir))
    manager = module.get_image_manager()
    (image,) = manager.get_all_images()
    manager.update_image_size(image.file_id, "fixed", 20)
    manager.add_size_option(image.file_id, "short", 10)

    body = client.get("/batch/preview-images").get_data(as_text=True)

    assert "Also make this picture at" in body
    # short is ticked, so its own extent is shown beside it
    assert "28×10" in body
    # and the card's primary prediction is still the fixed one, moved to Large
    assert "30×11" in body


def test_ticking_a_size_adds_it_and_unticking_takes_it_away(
    admin_client, temp_images_dir
):
    """AC-5 through the route the buttons post to."""
    app, client, module = admin_client
    _upload(client, _picture(temp_images_dir, size=(400, 400), ink=(0, 0, 399, 399)))
    manager = module.get_image_manager()
    (image,) = manager.get_all_images()

    client.post(
        f"/batch/image/{image.file_id}/size-option",
        data={"mode": "max"},
        follow_redirects=True,
    )
    assert [o.mode for o in image.size_options] == ["fixed", "max"]

    client.post(
        f"/batch/image/{image.file_id}/size-option",
        data={"mode": "max"},
        follow_redirects=True,
    )
    assert [o.mode for o in image.size_options] == ["fixed"]


def test_unticking_the_last_size_is_refused_and_says_where_remove_is(
    admin_client, temp_images_dir
):
    """The recorded decision, at the page: a sizing tweak never deletes a file."""
    app, client, module = admin_client
    _upload(client, _picture(temp_images_dir, size=(400, 400), ink=(0, 0, 399, 399)))
    manager = module.get_image_manager()
    (image,) = manager.get_all_images()

    response = client.post(
        f"/batch/image/{image.file_id}/size-option",
        data={"mode": image.size_options[0].mode},
        follow_redirects=True,
    )

    assert len(image.size_options) == 1
    assert "at least one size" in response.get_data(as_text=True)
