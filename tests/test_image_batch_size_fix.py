"""Test image batch workflow with size configuration changes.

This test verifies the fix for the issue where puzzle sizes weren't being
respected when users adjusted configurations between batch generations.
"""

from datetime import datetime

import pytest
from pathlib import Path
from PIL import Image as PILImage
from io import BytesIO
import tempfile

from nonogram.admin.image_manager import (
    FITS,
    MOVED_TO_LARGE,
    SIZE_PRESETS,
    ImageFile,
    ImageManager,
)


class TestImageBatchSizeConfiguration:
    """Test image batch size configuration across workflow iterations."""

    @pytest.fixture
    def temp_images_dir(self):
        """Create a temporary directory with test images."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def test_image_files(self, temp_images_dir):
        """Generate sample test images for testing."""
        images = []
        sizes = [(100, 100), (200, 150), (150, 200)]  # Different aspect ratios

        for i, (width, height) in enumerate(sizes):
            # Create simple test image
            img = PILImage.new('RGB', (width, height), color=(73, 109, 137))
            img_path = temp_images_dir / f"test_image_{i}.png"
            img.save(str(img_path))
            images.append(str(img_path))

        return images

    def test_image_manager_size_configuration_persistence(self, test_image_files):
        """Test that size configurations persist correctly in ImageManager."""
        image_mgr = ImageManager(temp_dir=str(Path(test_image_files[0]).parent))

        # Step 1: Add images
        loaded_images = []
        for img_path in test_image_files:
            img = image_mgr.add_image(img_path, Path(img_path).name)
            assert img is not None
            loaded_images.append(img)

        assert len(loaded_images) == 3

        # Step 2: Set sizes to 10 (first configuration)
        for img in loaded_images:
            image_mgr.update_image_size(img.file_id, "fixed", 10)

        # Verify first configuration. size_value lands on the picture's own
        # longer axis (FR-023, ADR-0022/R4). At 10 that is also the floor, so
        # the grid would be 10x10 for every picture: the square one fits,
        # while a 4:3 one would lose a quarter of itself and moves up to
        # Large instead (CARD-064) — 30 on its longer axis.
        retrieved_images = image_mgr.get_all_images()
        for img in retrieved_images:
            assert img.size_mode == "fixed"
            assert img.size_value == 10
            width, height = img.predict_size()
            if img.dimensions[0] == img.dimensions[1]:
                assert (width, height) == (10, 10)
                assert img.size_fit().status == FITS
            else:
                assert max(width, height) == 30
                assert img.size_fit().status == MOVED_TO_LARGE

        # Step 3: Change sizes to 20 (second configuration)
        for img in retrieved_images:
            image_mgr.update_image_size(img.file_id, "fixed", 20)

        # Verify second configuration
        retrieved_images = image_mgr.get_all_images()
        for img in retrieved_images:
            assert img.size_mode == "fixed"
            assert img.size_value == 20
            width, height = img.predict_size()
            # Max dimension should be 20
            assert max(width, height) == 20

        # Step 4: Clear and reload (simulating fresh workflow)
        image_mgr.clear_all()
        assert len(image_mgr.get_all_images()) == 0

    def test_image_manager_singleton_cleared_between_workflows(self, test_image_files):
        """Test that ImageManager can be cleared to prevent stale data."""
        from nonogram.admin.image_manager import _image_manager as module_image_mgr
        from nonogram.admin import image_manager

        # Reset the global singleton
        image_manager._image_manager = None

        # First workflow
        mgr1 = image_manager.get_image_manager()
        for img_path in test_image_files:
            mgr1.add_image(img_path, Path(img_path).name)

        assert len(mgr1.get_all_images()) == 3

        # Set sizes to 10
        for img in mgr1.get_all_images():
            mgr1.update_image_size(img.file_id, "fixed", 10)

        # Verify sizes
        for img in mgr1.get_all_images():
            assert img.size_value == 10

        # Clear (as done after batch generation)
        mgr1.clear_all()
        assert len(mgr1.get_all_images()) == 0

        # Second workflow - should be clean
        for img_path in test_image_files:
            mgr1.add_image(img_path, Path(img_path).name)

        # New images should have default size_value of 20
        for img in mgr1.get_all_images():
            assert img.size_value == 20  # Default

        # Now set to 15
        for img in mgr1.get_all_images():
            mgr1.update_image_size(img.file_id, "fixed", 15)

        # Verify new configuration took effect
        for img in mgr1.get_all_images():
            assert img.size_value == 15

        # Cleanup
        mgr1.clear_all()

    def test_size_modes_affect_prediction(self, test_image_files):
        """Test that different size modes produce different predictions."""
        image_mgr = ImageManager(temp_dir=str(Path(test_image_files[0]).parent))

        # Add one image
        img = image_mgr.add_image(test_image_files[0], Path(test_image_files[0]).name)

        # Test fixed mode with value 15
        image_mgr.update_image_size(img.file_id, "fixed", 15)
        retrieved = image_mgr.get_image(img.file_id)
        width_fixed, height_fixed = retrieved.predict_size()
        assert min(width_fixed, height_fixed) == 15

        # Test min mode
        image_mgr.update_image_size(img.file_id, "min", 0)
        retrieved = image_mgr.get_image(img.file_id)
        width_min, height_min = retrieved.predict_size()
        assert width_min >= 10  # Should be at least minimum

        # Test max mode
        image_mgr.update_image_size(img.file_id, "max", 0)
        retrieved = image_mgr.get_image(img.file_id)
        width_max, height_max = retrieved.predict_size()
        assert width_max <= 30  # Should respect maximum

        image_mgr.clear_all()

    def test_apply_size_to_all_images(self, test_image_files):
        """Test applying same size configuration to all images."""
        image_mgr = ImageManager(temp_dir=str(Path(test_image_files[0]).parent))

        # Add images
        for img_path in test_image_files:
            image_mgr.add_image(img_path, Path(img_path).name)

        # Apply size to all
        count = image_mgr.apply_size_to_all("fixed", 25)
        assert count == 3

        # Verify all updated
        for img in image_mgr.get_all_images():
            assert img.size_mode == "fixed"
            assert img.size_value == 25

        image_mgr.clear_all()


class TestImageBatchPage1Defaults:
    """Test that page 1 size selection is applied to loaded images."""

    @pytest.fixture
    def admin_client(self, monkeypatch):
        """The real admin app in memory (CARD-065): these tests used to
        re-implement the route's preset loop, with their own copy of the
        preset table, so they stayed green whatever the app did."""
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setenv("TESTING", "true")
        from nonogram.admin import image_manager as img_mgr_module
        from nonogram.admin.app import create_app

        img_mgr_module._image_manager = None
        app = create_app()
        app.config["TESTING"] = True
        with app.app_context():
            yield app.test_client(), img_mgr_module
        img_mgr_module._image_manager = None

    def _upload(self, client, tmp_path, default_size, shape=(200, 150)):
        path = tmp_path / "picture.png"
        PILImage.new("RGB", shape, color=(73, 109, 137)).save(str(path))
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

    @pytest.mark.parametrize("preset", sorted(SIZE_PRESETS))
    def test_page1_preset_reaches_the_images(self, admin_client, tmp_path, preset):
        """Each preset, through the real upload route, checked against the one
        preset table the route itself uses."""
        client, img_mgr_module = admin_client
        self._upload(client, tmp_path, preset)

        value, mode = SIZE_PRESETS[preset]
        (image,) = img_mgr_module.get_image_manager().get_all_images()
        assert image.size_mode == mode
        if mode != "max":  # "max" derives its own value from the picture
            assert image.size_value == value

    def test_page1_small_puts_its_value_on_the_short_side(self, admin_client, tmp_path):
        """Small on a 4:3 picture: 10 on the short side, long side follows."""
        client, img_mgr_module = admin_client
        self._upload(client, tmp_path, "small")

        (image,) = img_mgr_module.get_image_manager().get_all_images()
        assert image.predict_size() == (13, 10)

    def test_page1_large_puts_its_value_on_the_long_side(self, admin_client, tmp_path):
        """Large on the same picture: 30 on the long side, short side derived.

        30 x 150/200 is 22.5, and Python's round() breaks that tie to even, so
        the short side is 22 — the tie ADR-0022/R4's own property test pins.
        """
        client, img_mgr_module = admin_client
        self._upload(client, tmp_path, "large")

        (image,) = img_mgr_module.get_image_manager().get_all_images()
        assert image.predict_size() == (30, 22)

    def test_page1_auto_size_uses_max_mode(self, tmp_path):
        """Test that selecting 'Auto' on page 1 applies 'max' mode."""
        from nonogram.admin import image_manager as img_mgr_module
        img_mgr_module._image_manager = None

        img = PILImage.new('RGB', (200, 200), color=(73, 109, 137))
        img_path = tmp_path / "test.png"
        img.save(str(img_path))

        mgr = img_mgr_module.get_image_manager(temp_dir=str(tmp_path))
        mgr.add_image(str(img_path), Path(img_path).name)

        # Simulate page 1 size selection: "auto" -> "max" mode
        for image in mgr.get_all_images():
            mgr.update_image_size(image.file_id, "max", 0)

        # Verify max mode
        image = mgr.get_all_images()[0]
        assert image.size_mode == "max"
        width, height = image.predict_size()
        assert width <= 30 and height <= 30  # Max mode respects maximum

        mgr.clear_all()


class TestImageBatchWorkflowIntegration:
    """Integration tests for the complete image batch workflow."""

    def test_workflow_size_changes_scenario(self, tmp_path):
        """Test the exact scenario: upload, set size 10, generate, change to 20, regenerate."""
        from nonogram.admin import image_manager as img_mgr_module

        # Reset singleton
        img_mgr_module._image_manager = None

        # Create test images
        images = []
        for i in range(2):
            img = PILImage.new('RGB', (100, 100), color=(73, 109, 137))
            img_path = tmp_path / f"test_{i}.png"
            img.save(str(img_path))
            images.append(str(img_path))

        # STEP 1: First workflow - upload and set to size 10
        mgr = img_mgr_module.get_image_manager(temp_dir=str(tmp_path))

        for img_path in images:
            mgr.add_image(img_path, Path(img_path).name)

        # Set all to size 10
        for img in mgr.get_all_images():
            mgr.update_image_size(img.file_id, "fixed", 10)

        # Verify configuration
        batch_1_images = mgr.get_all_images()
        for img in batch_1_images:
            assert img.size_value == 10
            width, height = img.predict_size()
            assert min(width, height) == 10

        # Extract sizes (as done in app.py line 287-289)
        sizes_1 = sorted(list(set(img.size_value if img.size_mode == "fixed" else 20 for img in batch_1_images)))
        assert sizes_1 == [10]

        # Simulate batch generation completing and clearing
        mgr.clear_all()

        # STEP 2: Second workflow - reload, change to size 20, regenerate
        # Reload images
        for img_path in images:
            mgr.add_image(img_path, Path(img_path).name)

        # Set all to size 20 (new configuration)
        for img in mgr.get_all_images():
            mgr.update_image_size(img.file_id, "fixed", 20)

        # Verify new configuration
        batch_2_images = mgr.get_all_images()
        for img in batch_2_images:
            assert img.size_value == 20
            width, height = img.predict_size()
            assert min(width, height) == 20

        # Extract sizes for batch creation
        sizes_2 = sorted(list(set(img.size_value if img.size_mode == "fixed" else 20 for img in batch_2_images)))
        assert sizes_2 == [20]

        # Verify sizes are different between workflows
        assert sizes_1 != sizes_2
        assert sizes_1 == [10]
        assert sizes_2 == [20]

        mgr.clear_all()


class TestPredictSizeDegenerateInput:
    """CARD-045: ``predict_size()`` must not crash on a degenerate image.

    ``ImageManager.add_image`` (image_manager.py:240-246) defaults
    ``dimensions`` to ``(0, 0)`` and only overwrites it inside a bare
    ``except Exception: pass`` around a second, independent
    ``PILImage.open()`` — so ``dimensions=(0, 0)`` is a documented, reachable
    state for a "successfully added" image whose second decode failed.
    ``_source_shape()`` falls back to that same ``(0, 0)`` when it can't
    re-read the file either, and ``derive_extent(stated, None, 0, 0)`` used
    to raise an uncaught ``ValueError`` (AC-1).
    """

    def _degenerate_image(self, *, file_path: str = "/nonexistent/does-not-exist.png") -> ImageFile:
        """An ``ImageFile`` in the exact state ``add_image``'s silent
        second-decode failure leaves behind: ``dimensions == (0, 0)`` and a
        ``file_path`` that can't be re-read, so ``_source_shape()`` also
        falls back to ``(0, 0)`` rather than a real ink bounding box.
        """
        return ImageFile(
            file_id="deadbeef",
            filename="deadbeef.png",
            original_filename="broken.png",
            file_path=file_path,
            file_size=0,
            dimensions=(0, 0),
            format="PNG",
            uploaded_at=datetime.utcnow(),
        )

    def test_predict_size_zero_dimensions_returns_safe_fallback(self):
        """AC-1: predict_size() on a (0, 0)-dimensioned image returns a
        valid (width, height) tuple inside [MIN_SIZE, MAX_SIZE] on both
        sides instead of raising ValueError.

        Against the pre-CARD-045 code this raises
        ``ValueError: a source's own shape has a positive extent on both
        axes, got 0x0`` out of ``derive_extent`` — uncaught, because the
        surrounding ``except`` clauses only covered ``SizeTooSmallForSource``
        and ``NonogramError``, and a plain ``ValueError`` is neither.
        """
        from nonogram.sourcing.random_grid import MAX_SIZE, MIN_SIZE

        image = self._degenerate_image()

        # Pre-fix: raises ValueError here. Post-fix: returns a safe fallback.
        width, height = image.predict_size()

        assert MIN_SIZE <= width <= MAX_SIZE
        assert MIN_SIZE <= height <= MAX_SIZE

    @pytest.mark.parametrize("size_mode", ["fixed", "min", "max"])
    def test_predict_size_zero_dimensions_safe_for_every_size_mode(self, size_mode):
        """AC-1 holds across all three size modes, not just the default."""
        from nonogram.sourcing.random_grid import MAX_SIZE, MIN_SIZE

        image = self._degenerate_image()
        image.size_mode = size_mode

        width, height = image.predict_size()

        assert MIN_SIZE <= width <= MAX_SIZE
        assert MIN_SIZE <= height <= MAX_SIZE

    def test_predict_size_real_image_unaffected(self, tmp_path):
        """G-1 guardrail: a real, positive-dimension picture must keep
        following its own ratio exactly as before — the fix must only
        close the degenerate-input gap, not touch the ink-bbox/derive_extent
        behaviour for a working image.
        """
        img_path = tmp_path / "real.png"
        PILImage.new("RGB", (200, 100), color=(10, 20, 30)).save(img_path)

        image_mgr = ImageManager(temp_dir=str(tmp_path))
        image = image_mgr.add_image(str(img_path), "real.png")
        assert image is not None
        image_mgr.update_image_size(image.file_id, "fixed", 20)

        width, height = image.predict_size()

        # 200x100 is 2:1 landscape; the longer axis (width) lands exactly on
        # the stated size and the shorter axis follows the picture's ratio -
        # unchanged from ec18fb4's behaviour for a real picture.
        assert width == 20
        assert height == 10

        image_mgr.clear_all()


class TestPredictSizeNonogramErrorBranchNotDead:
    """AC-3: the old ``except NonogramError: return (stated, stated)``
    branch at image_manager.py:120 was dead code (the card's own analysis:
    ``stated`` is always pre-clamped before ``derive_extent`` runs, so
    ``validate_extent(stated, stated)`` can never raise, and the only other
    ``NonogramError`` subclass ``derive_extent`` can raise -
    ``SizeTooSmallForSource`` - is already caught by the preceding clause).
    CARD-045 removes it; this asserts it no longer exists as source text
    rather than re-deriving "unreachable" by re-running the same analysis.
    """

    def test_dead_nonogram_error_branch_removed(self):
        import inspect

        from nonogram.admin.image_manager import ImageFile

        source = inspect.getsource(ImageFile.predict_size)

        assert "except NonogramError" not in source


class TestBatchPreviewDegenerateImageIntegration:
    """AC-2: a degenerate image in a batch must not 500 the whole page.

    Exercises the two unprotected GET render loops the card calls out
    (app.py's ``preview_batch_images`` and ``generate_batch_puzzles``,
    which both call ``image.predict_size()`` once per image inside
    ``render_template`` with no per-image try/except) via the real Flask
    test client, not just the unit-level ``predict_size()`` call.
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

    def _add_degenerate_image(self, img_mgr_module, tmp_path):
        """Load one real, valid image through the normal ``add_image`` path
        and then put it into the exact degenerate state described in the
        card: ``dimensions`` reset to ``(0, 0)`` and the cached source
        shape (what ``_source_shape()`` would have fallen back to had its
        own re-decode of the file also failed) likewise ``(0, 0)`` -
        simulating ``add_image``'s silent second-decode failure without
        needing to actually corrupt a file on disk.
        """
        img_path = tmp_path / "batch_broken.png"
        PILImage.new("RGB", (150, 150), color=(5, 5, 5)).save(img_path)

        mgr = img_mgr_module.get_image_manager(temp_dir=str(tmp_path))
        image = mgr.add_image(str(img_path), "batch_broken.png")
        assert image is not None

        image.dimensions = (0, 0)
        image._cached_source_shape = (0, 0)
        return mgr, image

    def test_preview_batch_images_get_survives_degenerate_image(self, flask_client):
        """AC-2: GET /batch/preview-images renders 200 for the whole batch
        even with a degenerate image in it (pre-fix: 500, ValueError raised
        from inside the Jinja render at image_preview.html's
        ``image.predict_size()`` call)."""
        client, img_mgr_module, tmp_path = flask_client
        self._add_degenerate_image(img_mgr_module, tmp_path)

        response = client.get("/batch/preview-images")

        assert response.status_code == 200

    def test_generate_batch_puzzles_get_survives_degenerate_image(self, flask_client):
        """AC-2: GET /batch/generate-puzzles renders 200 for the whole batch
        even with a degenerate image in it (pre-fix: 500, same ValueError
        from generate_batch.html's ``image.predict_size()`` call)."""
        client, img_mgr_module, tmp_path = flask_client
        self._add_degenerate_image(img_mgr_module, tmp_path)

        response = client.get("/batch/generate-puzzles")

        assert response.status_code == 200

    def test_preview_batch_images_mixed_batch_all_render(self, flask_client):
        """A batch of one good image plus one degenerate image still
        renders 200 for the whole batch (AC-2's "not just the broken
        image" framing) rather than only surviving a single-image batch."""
        client, img_mgr_module, tmp_path = flask_client
        mgr, _broken = self._add_degenerate_image(img_mgr_module, tmp_path)

        good_path = tmp_path / "batch_good.png"
        PILImage.new("RGB", (120, 80), color=(9, 9, 9)).save(good_path)
        good = mgr.add_image(str(good_path), "batch_good.png")
        assert good is not None

        response = client.get("/batch/preview-images")

        assert response.status_code == 200
