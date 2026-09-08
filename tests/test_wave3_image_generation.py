"""Wave 3 tests: Image-based batch generation."""

import pytest
from pathlib import Path
import tempfile
from PIL import Image


class TestImageSelection:
    """Tests for image selection and upload (CARD-004p)."""

    @pytest.mark.integration
    def test_image_selection_page_loads(self, client):
        """Test that image selection page renders."""
        response = client.get("/batch/select-images")
        assert response.status_code == 200
        # TODO: assert "select images" in response.data.decode()

    @pytest.mark.integration
    def test_upload_images_to_batch(self, client):
        """Test uploading multiple images."""
        # TODO: Create temp images
        # TODO: POST to /batch/select-images
        # TODO: Verify images stored in session
        pass

    @pytest.mark.integration
    def test_remove_image_from_selection(self, client):
        """Test removing an image from selected batch."""
        # TODO: Upload 3 images
        # TODO: Remove image 2
        # TODO: Verify only 2 remain
        pass

    @pytest.mark.integration
    def test_mixed_formats_in_directory(self, client):
        """Test directory with PNG, JPG, GIF files."""
        # TODO: Create temp directory with all 3 formats
        # TODO: Select directory
        # TODO: Verify all 3 formats accepted
        pass


class TestImagePreview:
    """Tests for image preview and size selection (CARD-004q)."""

    @pytest.mark.integration
    def test_preview_page_shows_images(self, client):
        """Test that preview page displays selected images."""
        # TODO: Upload images
        # TODO: GET /batch/preview-images
        # TODO: Verify thumbnails and dimensions shown
        pass

    @pytest.mark.integration
    def test_size_option_fixed(self, client):
        """Test fixed size option."""
        # TODO: Set size to 20 for image
        # TODO: Verify output shows "20×20" puzzle
        pass

    @pytest.mark.integration
    def test_size_option_min(self, client):
        """Test minimum size prediction."""
        # TODO: Select "Min" for large image
        # TODO: Verify predicted size is reasonable (10-15)
        pass

    @pytest.mark.integration
    def test_size_option_max(self, client):
        """Test maximum size prediction."""
        # TODO: Select "Max" for image
        # TODO: Verify predicted size is reasonable (20-30)
        pass

    @pytest.mark.integration
    def test_apply_size_to_all_images(self, client):
        """Test applying same size to all images."""
        # TODO: Upload 3 images
        # TODO: Set size 18 and click "Apply to all"
        # TODO: Verify all show "Size: 18×18"
        pass

    @pytest.mark.integration
    def test_edit_puzzle_name(self, client):
        """Test editing puzzle name (defaults to filename)."""
        # TODO: Image: "sunset.jpg"
        # TODO: Default puzzle_name: "sunset"
        # TODO: Edit to "sunset_puzzle"
        # TODO: Verify name updated
        pass

    @pytest.mark.integration
    def test_invalid_size_shows_error(self, client):
        """Test error when size outside valid range."""
        # TODO: Set size to 35 (too large)
        # TODO: Verify error badge appears
        # TODO: Verify Generate button disabled
        pass


class TestImageGeneration:
    """Tests for image-to-puzzle generation (CARD-004r)."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_generate_batch_from_images(self, batch_generator_service):
        """Test full workflow: images → puzzles."""
        # TODO: Create 3 test images
        # TODO: Call batch_generator.create_batch_from_images([...])
        # TODO: Verify 3 puzzles created
        # TODO: Verify batch status is COMPLETE
        pass

    @pytest.mark.integration
    def test_batch_tracks_original_images(self, batch_generator_service):
        """Test that original image paths are stored."""
        # TODO: Generate batch from images
        # TODO: Get puzzle
        # TODO: Verify puzzle.original_image_path set
        pass

    @pytest.mark.integration
    def test_error_handling_bad_image(self, batch_generator_service):
        """Test graceful handling of unsolvable images."""
        # TODO: Create 3 images, 1 unsolvable (all black, etc.)
        # TODO: Generate batch
        # TODO: Verify 2 puzzles created
        # TODO: Verify error message for failed image
        # TODO: Error: "Can't generate solvable nonogram"
        pass

    @pytest.mark.integration
    def test_progress_tracking(self, batch_generator_service):
        """Test batch progress updates."""
        # TODO: Generate batch with 5 images
        # TODO: Verify progress increments: 1/5, 2/5, 3/5, etc.
        pass

    @pytest.mark.integration
    def test_batch_with_mixed_formats(self, batch_generator_service):
        """Test batch with PNG, JPG, GIF images."""
        # TODO: Create images in all 3 formats
        # TODO: Generate batch from mixed directory
        # TODO: Verify all generated successfully
        pass

    @pytest.mark.integration
    def test_image_size_validation(self, batch_generator_service):
        """Test max size enforcement (2MB per image)."""
        # TODO: Create image > 2MB
        # TODO: Try to generate batch
        # TODO: Verify error: "Image exceeds 2MB limit"
        pass


class TestSourceImagePreview:
    """Tests for showing source images in puzzle preview (CARD-004s)."""

    @pytest.mark.integration
    def test_puzzle_detail_shows_source_image(self, client):
        """Test that puzzle detail displays original image."""
        # TODO: Generate puzzle from image
        # TODO: GET /puzzle/{puzzle_id}/detail
        # TODO: Verify response includes original_image_url
        pass

    @pytest.mark.integration
    def test_source_image_served_via_api(self, client):
        """Test image serving endpoint."""
        # TODO: Generate puzzle from image
        # TODO: GET /api/puzzle/{puzzle_id}/image
        # TODO: Verify image returned (PNG/JPG)
        pass

    @pytest.mark.integration
    def test_missing_image_shows_fallback(self, client):
        """Test graceful handling when original image deleted."""
        # TODO: Generate puzzle from image
        # TODO: Delete original image file
        # TODO: GET /puzzle/{puzzle_id}/detail
        # TODO: Verify fallback: "Original image not available"
        pass

    @pytest.mark.integration
    def test_image_caching(self, client):
        """Test image caching headers."""
        # TODO: GET /api/puzzle/{puzzle_id}/image
        # TODO: Verify ETag or Cache-Control headers set
        pass

    @pytest.mark.integration
    def test_puzzle_list_shows_images(self, client):
        """Test image display in puzzle list view."""
        # TODO: Generate batch from images
        # TODO: GET /puzzles
        # TODO: Verify each puzzle shows thumbnail
        pass


class TestBatchWorkflow:
    """End-to-end workflow tests (all Wave 3 cards together)."""

    @pytest.mark.e2e
    @pytest.mark.slow
    def test_complete_wave3_workflow(self, batch_generator_service, puzzle_review_service):
        """Test complete workflow: Select → Preview → Generate → Verify."""
        # TODO: CARD-004o: Verify random mode not available
        # TODO: CARD-004p: Upload 3 images
        # TODO: CARD-004q: Set mixed sizes (18, min, max)
        # TODO: CARD-004r: Generate batch
        # TODO: CARD-004s: View puzzle with source image
        # TODO: Approve/reject puzzle
        # TODO: Verify in batch history
        pass


# Run with: pytest tests/test_wave3_*.py -v
# Run Wave 3 tests: pytest tests/test_wave3_*.py -v
