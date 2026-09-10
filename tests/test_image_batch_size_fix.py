"""Test image batch workflow with size configuration changes.

This test verifies the fix for the issue where puzzle sizes weren't being
respected when users adjusted configurations between batch generations.
"""

import pytest
from pathlib import Path
from PIL import Image as PILImage
from io import BytesIO
import tempfile

from nonogram.admin.image_manager import ImageManager, ImageFile


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

        # Verify first configuration
        retrieved_images = image_mgr.get_all_images()
        for img in retrieved_images:
            assert img.size_mode == "fixed"
            assert img.size_value == 10
            width, height = img.predict_size()
            # Min dimension should be 10 (or close due to aspect ratio)
            assert min(width, height) == 10

        # Step 3: Change sizes to 20 (second configuration)
        for img in retrieved_images:
            image_mgr.update_image_size(img.file_id, "fixed", 20)

        # Verify second configuration
        retrieved_images = image_mgr.get_all_images()
        for img in retrieved_images:
            assert img.size_mode == "fixed"
            assert img.size_value == 20
            width, height = img.predict_size()
            # Min dimension should be 20
            assert min(width, height) == 20

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
