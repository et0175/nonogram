"""CARD-047: ImageFile._source_shape()'s ink-bounding-box decode moves from
the batch-preview render path to ImageManager.add_image() (upload time).

Before this card, ``_source_shape()``'s first call — a full PIL decode plus
a Pillow-native bounding-box scan (``nonogram.sourcing.image.source_shape``,
which deliberately avoids NumPy for this — see its own docstring)
— happened lazily, inside ``image_preview.html``/``generate_batch.html``'s
unpaginated ``{% for image in images %}`` template loops (``app.py``'s
``preview_batch_images``/``generate_batch_puzzles`` GET handlers). A batch of
up to 200 images (``ImageManager.MAX_DIMENSIONS`` allows up to 2000x2000px
each) paid up to 200 synchronous decodes on that render request.

AC-1 — the ink-bounding-box decode no longer happens on the render path: by
       the time a batch's images reach ``predict_size()`` in a template loop,
       the cache is already primed.
AC-2 — existing behavior (predicted size correctness, the ec18fb4 fix) is
       unchanged; only *when* the ink bounding box is computed moves (G-1).
"""

import tempfile
from pathlib import Path

import pytest
from PIL import Image as PILImage, ImageDraw

from nonogram.admin.image_manager import ImageManager


@pytest.fixture
def temp_images_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestAC1SourceShapePrimedAtUploadTime:
    def test_add_image_primes_the_source_shape_cache_immediately(
        self, temp_images_dir
    ):
        """The ink bounding box must already be cached the moment
        add_image() returns — before predict_size() or any render-time
        access is ever made.
        """
        img = PILImage.new("RGB", (100, 100), color="blue")
        img_path = temp_images_dir / "solid.png"
        img.save(img_path)

        manager = ImageManager(temp_dir=str(temp_images_dir))
        image = manager.add_image(str(img_path), "solid.png")

        assert image is not None
        assert getattr(image, "_cached_source_shape", None) is not None

    def test_decode_happens_during_add_image_not_on_first_render(
        self, temp_images_dir, monkeypatch
    ):
        """The distinguishing property this card changes: the underlying
        ink-bounding-box primitive must be called *during* add_image()
        itself, before any render-time predict_size() call — not merely
        "only once ever" (that weaker property already held before this
        card, since _source_shape()'s per-instance cache predates it, and
        would pass whether the decode happened at upload or at first
        render). Checking the count immediately after add_image() returns,
        before touching predict_size() at all, is what actually pins
        upload-time vs. render-time.
        """
        call_count = {"n": 0}

        from nonogram.sourcing import image as sourcing_image_module

        original = sourcing_image_module.source_shape

        def counting_source_shape(*args, **kwargs):
            call_count["n"] += 1
            return original(*args, **kwargs)

        monkeypatch.setattr(
            sourcing_image_module, "source_shape", counting_source_shape
        )

        img = PILImage.new("RGB", (100, 100), color="blue")
        img_path = temp_images_dir / "solid.png"
        img.save(img_path)

        manager = ImageManager(temp_dir=str(temp_images_dir))
        image = manager.add_image(str(img_path), "solid.png")
        assert image is not None

        # The decisive assertion: already decoded before any render-time
        # call. A lazy (pre-CARD-047) implementation would be 0 here.
        assert call_count["n"] == 1, (
            "source_shape() must be called during add_image() itself, "
            f"before any predict_size() call — was called {call_count['n']} "
            "times immediately after add_image() returned"
        )

        # And, as before, further calls from a batch template's
        # `{% for image in images %}` loop (once per image, per render)
        # must not trigger any additional decode — the cache already holds
        # the answer.
        for _ in range(5):
            image.predict_size()
        assert call_count["n"] == 1


class TestAC2PredictSizeBehaviorUnchanged:
    """G-1: predict_size()'s return value must be identical to before this
    card — only the timing of the ink-bbox computation moved, not the
    result. Reuses the same margin-fixture shape CARD-046's regression
    test established (a canvas whose aspect ratio genuinely differs from
    its drawn content's), so this pins the eager-priming change against
    exactly the scenario the earlier bugfix (ec18fb4) was about.
    """

    def test_predict_size_still_follows_ink_bounding_box_with_eager_priming(
        self, temp_images_dir
    ):
        canvas = PILImage.new("RGB", (300, 100), color="white")
        draw = ImageDraw.Draw(canvas)
        draw.rectangle([(10, 10), (90, 90)], fill="black")  # 81x81 ink box
        canvas_path = temp_images_dir / "margin.png"
        canvas.save(canvas_path)

        manager = ImageManager(temp_dir=str(temp_images_dir))
        image = manager.add_image(str(canvas_path), "margin.png")

        assert image is not None
        assert image.dimensions == (300, 100)
        # Cache is already primed by add_image() — predict_size() here
        # reads it rather than triggering a decode.
        width, height = image.predict_size()
        assert (width, height) == (20, 20)

    def test_predict_size_solid_borderless_image_unchanged(self, temp_images_dir):
        """Sanity check against the plain case (no margin): still returns
        the file's own aspect ratio, exactly as before this card.
        """
        img = PILImage.new("RGB", (1920, 1080), color="blue")
        img_path = temp_images_dir / "landscape.png"
        img.save(img_path)

        manager = ImageManager(temp_dir=str(temp_images_dir))
        image = manager.add_image(str(img_path), "landscape.png")

        assert image is not None
        width, height = image.predict_size()
        assert width == 20
        assert height == 11
