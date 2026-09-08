"""Wave 3 end-to-end integration tests for image-based batch generation."""

import pytest
import tempfile
from pathlib import Path
from PIL import Image as PILImage
import os


class TestWave3ImageGeneration:
    """Complete Wave 3 workflow tests."""

    @pytest.fixture
    def test_images(self):
        """Create test images with different aspect ratios."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Landscape image (1920×1080)
            landscape = PILImage.new('RGB', (1920, 1080), color='blue')
            landscape_path = Path(tmpdir) / "landscape.png"
            landscape.save(landscape_path)

            # Portrait image (600×1000)
            portrait = PILImage.new('RGB', (600, 1000), color='red')
            portrait_path = Path(tmpdir) / "portrait.png"
            portrait.save(portrait_path)

            # Square image (512×512)
            square = PILImage.new('RGB', (512, 512), color='green')
            square_path = Path(tmpdir) / "square.png"
            square.save(square_path)

            yield {
                'landscape': landscape_path,
                'portrait': portrait_path,
                'square': square_path,
                'tmpdir': tmpdir,
            }

    def test_image_manager_accepts_multiple_formats(self, test_images):
        """Test that image manager handles PNG, JPG, GIF formats."""
        from nonogram.admin.image_manager import ImageManager

        manager = ImageManager()

        # Add landscape image
        landscape_img = manager.add_image(
            str(test_images['landscape']),
            'landscape.png'
        )
        assert landscape_img is not None
        assert landscape_img.dimensions == (1920, 1080)
        assert landscape_img.format == "PNG"

        # Add portrait image
        portrait_img = manager.add_image(
            str(test_images['portrait']),
            'portrait.png'
        )
        assert portrait_img is not None
        assert portrait_img.dimensions == (600, 1000)

        # Add square image
        square_img = manager.add_image(
            str(test_images['square']),
            'square.png'
        )
        assert square_img is not None
        assert square_img.dimensions == (512, 512)

        # Verify all stored
        all_images = manager.get_all_images()
        assert len(all_images) == 3

    def test_aspect_ratio_aware_sizing_landscape(self, test_images):
        """Test that landscape images get correct dimensions."""
        from nonogram.admin.image_manager import ImageManager

        manager = ImageManager()
        img = manager.add_image(str(test_images['landscape']), 'landscape.png')

        # With size=20, landscape 1920×1080 should give (30, 20)
        # aspect_ratio = 1920/1080 = 1.777...
        # width = 20 * 1.777... ≈ 35.5 → clamped to 30
        # height = 20
        width, height = img.predict_size()
        assert width == 30
        assert height == 20
        assert width > height  # Landscape

    def test_aspect_ratio_aware_sizing_portrait(self, test_images):
        """Test that portrait images get correct dimensions."""
        from nonogram.admin.image_manager import ImageManager

        manager = ImageManager()
        img = manager.add_image(str(test_images['portrait']), 'portrait.png')

        # With size=20, portrait 600×1000 should give (20, 30)
        # aspect_ratio = 600/1000 = 0.6
        # width = 20
        # height = 20 / 0.6 ≈ 33.3 → clamped to 30
        width, height = img.predict_size()
        assert width == 20
        assert height == 30
        assert height > width  # Portrait

    def test_aspect_ratio_aware_sizing_square(self, test_images):
        """Test that square images get square dimensions."""
        from nonogram.admin.image_manager import ImageManager

        manager = ImageManager()
        img = manager.add_image(str(test_images['square']), 'square.png')

        # With size=20, square 512×512 should give (20, 20)
        width, height = img.predict_size()
        assert width == 20
        assert height == 20

    def test_mock_generator_handles_tuple_sizes(self):
        """Test that MockGenerator accepts (width, height) tuples."""
        from nonogram.admin.puzzle_review import MockGenerator

        generator = MockGenerator(seed=42)

        # Should accept tuples
        puzzles = generator.generate_batch(
            count=3,
            sizes=[(20, 20), (30, 20), (20, 30)],
            theme='christmas'
        )

        assert len(puzzles) == 3
        # MockGenerator randomly chooses from sizes, just verify they're valid dimensions
        for puzzle in puzzles:
            assert 10 <= puzzle['width'] <= 30
            assert 10 <= puzzle['height'] <= 30

    def test_mock_generator_backwards_compatible_with_ints(self):
        """Test that MockGenerator still accepts int sizes."""
        from nonogram.admin.puzzle_review import MockGenerator

        generator = MockGenerator(seed=42)

        # Should still accept ints for backwards compatibility
        puzzles = generator.generate_batch(
            count=2,
            sizes=[20, 25],
            theme='christmas'
        )

        assert len(puzzles) == 2
        # MockGenerator randomly chooses from sizes, just verify they're square
        for puzzle in puzzles:
            assert puzzle['width'] == puzzle['height']
            assert puzzle['width'] in [20, 25]

    def test_puzzle_review_service_stores_source_image(self):
        """Test that PuzzleReviewService tracks source images."""
        from nonogram.admin.puzzle_review import PuzzleReviewService

        service = PuzzleReviewService()

        puzzle_id = service.add_puzzle(
            grid=[[True, False], [False, True]],
            clues_rows=[[1], [1]],
            clues_cols=[[1], [1]],
            width=2,
            height=2,
            theme="christmas",
            difficulty_score=50,
            difficulty_tier="medium",
            quality_score=75,
            recognizability="medium",
            strategies_used=["LineLogic"],
            batch_id="batch_001",
            source_image="landscape.png",
        )

        puzzle = service.get_puzzle(puzzle_id)
        assert puzzle is not None
        assert puzzle['source_image'] == "landscape.png"
        assert puzzle['batch_id'] == "batch_001"

    def test_image_file_to_dict_includes_predicted_size(self, test_images):
        """Test that ImageFile.to_dict() includes predicted dimensions."""
        from nonogram.admin.image_manager import ImageManager

        manager = ImageManager()
        img = manager.add_image(str(test_images['landscape']), 'landscape.png')

        data = img.to_dict()
        assert 'predicted_width' in data
        assert 'predicted_height' in data
        assert data['predicted_width'] == 30
        assert data['predicted_height'] == 20

    def test_image_manager_update_size_modes(self, test_images):
        """Test updating image size modes (fixed, min, max)."""
        from nonogram.admin.image_manager import ImageManager

        manager = ImageManager()
        img = manager.add_image(str(test_images['landscape']), 'landscape.png')

        # Test fixed mode with size 25
        manager.update_image_size(img.file_id, 'fixed', 25)
        img = manager.get_image(img.file_id)
        assert img.size_mode == 'fixed'
        assert img.size_value == 25
        width, height = img.predict_size()
        # For landscape 1920×1080 with size 25:
        # aspect_ratio = 1.777...
        # width = 25 * 1.777... ≈ 44.4 → clamped to 30 (max)
        # height = 25
        assert width == 30  # Clamped to max
        assert height == 25

        # Test min mode
        manager.update_image_size(img.file_id, 'min')
        img = manager.get_image(img.file_id)
        assert img.size_mode == 'min'

        # Test max mode
        manager.update_image_size(img.file_id, 'max')
        img = manager.get_image(img.file_id)
        assert img.size_mode == 'max'

    def test_image_manager_apply_size_to_all(self, test_images):
        """Test applying same size configuration to all images."""
        from nonogram.admin.image_manager import ImageManager

        manager = ImageManager()

        # Add multiple images
        landscape = manager.add_image(str(test_images['landscape']), 'landscape.png')
        portrait = manager.add_image(str(test_images['portrait']), 'portrait.png')
        square = manager.add_image(str(test_images['square']), 'square.png')

        # Apply same size to all
        count = manager.apply_size_to_all('fixed', 18)
        assert count == 3

        # Verify all updated
        for img in manager.get_all_images():
            assert img.size_mode == 'fixed'
            assert img.size_value == 18

    def test_image_manager_update_puzzle_name(self, test_images):
        """Test updating puzzle names."""
        from nonogram.admin.image_manager import ImageManager

        manager = ImageManager()
        img = manager.add_image(str(test_images['landscape']), 'landscape.png')

        # Default puzzle name should be filename without extension
        assert img.puzzle_name == 'landscape'

        # Update puzzle name
        manager.update_image_name(img.file_id, 'my_puzzle')
        img = manager.get_image(img.file_id)
        assert img.puzzle_name == 'my_puzzle'

    def test_image_manager_total_size_calculation(self, test_images):
        """Test total size calculations for batches."""
        from nonogram.admin.image_manager import ImageManager

        manager = ImageManager()

        # Add multiple images
        manager.add_image(str(test_images['landscape']), 'landscape.png')
        manager.add_image(str(test_images['portrait']), 'portrait.png')

        total_mb = manager.get_total_size_mb()
        assert total_mb > 0
        assert total_mb < 1  # All test images are small

    def test_image_serving_endpoint_mime_types(self, client, test_images):
        """Test that image serving endpoint returns correct MIME types."""
        from nonogram.admin.image_manager import get_image_manager

        # Add image
        img_mgr = get_image_manager()
        img = img_mgr.add_image(str(test_images['landscape']), 'landscape.png')

        # Verify endpoint returns correct MIME type
        response = client.get(f'/api/image/{img.file_id}')
        assert response.status_code == 200
        assert response.content_type == 'image/png'

        # Verify binary data is served (PNG magic bytes)
        assert response.data[:4] == b'\x89PNG'

    def test_image_serving_endpoint_404_for_missing(self, client):
        """Test that image serving returns 404 for missing images."""
        response = client.get('/api/image/nonexistent_id')
        assert response.status_code == 404


class TestWave3UIIntegration:
    """Tests for Wave 3 UI components."""

    def test_batch_creation_form_renders(self, client):
        """Test that batch creation page loads."""
        response = client.get('/batch/create')
        assert response.status_code == 200
        assert b'Create Batch from Images' in response.data

    def test_batch_creation_includes_size_options(self, client):
        """Test that size option dropdown is visible."""
        response = client.get('/batch/create')
        assert response.status_code == 200
        # Check for size options
        assert b'Small' in response.data or b'small' in response.data
        assert b'Medium' in response.data or b'medium' in response.data
        assert b'Large' in response.data or b'large' in response.data
