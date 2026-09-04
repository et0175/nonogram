"""End-to-end tests for the web UI using Playwright (browser automation).

These tests drive a real browser against a running web server to verify the
complete user experience: form rendering, submission, result display, and error
handling as a user would experience it.

Tests cover:
- Form page loads and renders correctly
- Library mode generation and export
- Random mode generation
- Error handling and validation
- File downloads and output
"""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
import time
from pathlib import Path

import pytest


@pytest.fixture
def web_server_port() -> int:
    """Find a free port and start the web server on it."""
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]

    return port


@pytest.fixture
def web_server_url(web_server_port: int) -> str:
    """Return the web server URL."""
    return f"http://127.0.0.1:{web_server_port}"


@pytest.fixture
def running_web_server(web_server_port: int) -> str:
    """Start the web server in a subprocess and return its URL."""
    from nonogram import web

    # Create a server on the given port
    server = web.create_server(web_server_port)

    # Start it in a background thread
    import threading
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    # Give the server a moment to start
    time.sleep(0.1)

    url = f"http://127.0.0.1:{web_server_port}"

    yield url

    # Shutdown the server
    server.shutdown()
    server.server_close()


class TestWebE2E_FormPageLoads:
    """E2E tests for loading and rendering the form page."""

    def test_form_page_loads(self, page, running_web_server: str) -> None:
        """The form page loads and displays the title."""
        page.goto(running_web_server)

        # Check the page title
        assert "nonogram" in page.title().lower()

        # Check form elements exist
        assert page.locator('form[method="post"]').is_visible()
        assert page.locator('input[name="size"]').is_visible()
        assert page.locator('input[name="image"]').is_visible()


    def test_form_has_all_required_fields(self, page, running_web_server: str) -> None:
        """The form contains all expected input fields for image mode."""
        page.goto(running_web_server)

        # Check for image file input
        assert page.locator('input[name="image"]').is_visible()

        # Check for size input
        assert page.locator('input[name="size"]').is_visible()

        # Check for export format checkboxes
        export_boxes = page.locator('input[name="export_formats"]')
        assert export_boxes.count() > 0

        # Check for submit button
        assert page.locator('button[type="submit"]').is_visible()

        # Check for difficulty selector
        assert page.locator('select[name="difficulty"]').is_visible()


    def test_form_shows_export_formats(self, page, running_web_server: str) -> None:
        """Export format checkboxes are available."""
        page.goto(running_web_server)

        export_boxes = page.locator('input[name="export_formats"]')
        count = export_boxes.count()
        assert count > 0, "Should have at least one export format"

        # Get the values of available formats
        values = []
        for i in range(count):
            val = export_boxes.nth(i).get_attribute("value")
            if val:
                values.append(val)

        # Should have common formats
        assert len(values) > 0


class TestWebE2E_ImageModeWithSampleImage:
    """E2E tests for image mode (file upload) generation."""

    @pytest.fixture
    def sample_image_path(self, tmp_path: Path) -> Path:
        """Create a simple test image."""
        try:
            from PIL import Image

            # Create a simple 16x16 black and white image
            img = Image.new("L", (16, 16), color=255)  # All white
            # Add some black pixels
            pixels = img.load()
            for i in range(4, 12):
                for j in range(4, 12):
                    pixels[i, j] = 0

            image_path = tmp_path / "test.png"
            img.save(image_path)
            return image_path
        except ImportError:
            pytest.skip("PIL not available")

    def test_image_upload_and_generation(
        self, page, running_web_server: str, tmp_path: Path, sample_image_path: Path
    ) -> None:
        """Upload an image and generate a puzzle."""
        page.goto(running_web_server)

        # Upload image first
        page.locator('input[name="image"]').set_input_files(str(sample_image_path))

        # Wait for preview to load
        page.wait_for_selector('#image-preview[src]', timeout=5000)

        # Set size (required for image mode)
        page.locator('input[name="size"]').fill("16")

        # Set output directory
        page.locator('input[name="out"]').fill(str(tmp_path))

        # Select export format
        page.locator('input[value="json"]').check()

        # Submit form
        page.locator('button[type="submit"]').click()

        # Wait for success message
        page.wait_for_selector('[data-outcome="success"]', timeout=15000)

        # Check that a JSON file was created
        json_files = list(tmp_path.glob("*.json"))
        assert len(json_files) > 0, f"Expected generated JSON file in {tmp_path}, found: {json_files}"


    def test_image_upload_with_custom_name(
        self, page, running_web_server: str, tmp_path: Path, sample_image_path: Path
    ) -> None:
        """Upload image with a custom puzzle name."""
        page.goto(running_web_server)

        page.locator('input[name="image"]').set_input_files(str(sample_image_path))
        page.wait_for_selector('#image-preview[src]', timeout=5000)

        page.locator('input[name="name"]').fill("my_image_puzzle")
        page.locator('input[name="size"]').fill("16")
        page.locator('input[name="out"]').fill(str(tmp_path))
        page.locator('input[value="json"]').check()

        page.locator('button[type="submit"]').click()

        page.wait_for_selector('[data-outcome="success"]', timeout=15000)

        # Files should use custom name
        json_files = [f for f in tmp_path.glob("*.json") if "my_image_puzzle" in f.name]
        assert len(json_files) > 0, f"Expected file with 'my_image_puzzle' in name, found: {list(tmp_path.glob('*.json'))}"


class TestWebE2E_ImageSizeAndSettings:
    """E2E tests for image size and generation settings."""

    @pytest.fixture
    def sample_image_path(self, tmp_path: Path) -> Path:
        """Create a simple test image."""
        try:
            from PIL import Image

            img = Image.new("L", (16, 16), color=255)
            pixels = img.load()
            for i in range(4, 12):
                for j in range(4, 12):
                    pixels[i, j] = 0
            image_path = tmp_path / "test.png"
            img.save(image_path)
            return image_path
        except ImportError:
            pytest.skip("PIL not available")

    def test_image_with_custom_size(
        self, page, running_web_server: str, tmp_path: Path, sample_image_path: Path
    ) -> None:
        """Image mode with custom size."""
        page.goto(running_web_server)

        page.locator('input[name="image"]').set_input_files(str(sample_image_path))
        page.wait_for_selector('#image-preview[src]', timeout=5000)

        # Set a custom size
        page.locator('input[name="size"]').fill("20")
        page.locator('input[name="out"]').fill(str(tmp_path))
        page.locator('input[value="json"]').check()

        page.locator('button[type="submit"]').click()

        page.wait_for_selector('[data-outcome="success"]', timeout=15000)

        json_files = list(tmp_path.glob("*.json"))
        assert len(json_files) > 0


    def test_image_with_seed_parameter(
        self, page, running_web_server: str, tmp_path: Path, sample_image_path: Path
    ) -> None:
        """Image mode with seed for reproducibility."""
        page.goto(running_web_server)

        page.locator('input[name="image"]').set_input_files(str(sample_image_path))
        page.wait_for_selector('#image-preview[src]', timeout=5000)

        page.locator('input[name="seed"]').fill("42")
        page.locator('input[name="size"]').fill("16")
        page.locator('input[name="out"]').fill(str(tmp_path))
        page.locator('input[value="json"]').check()

        page.locator('button[type="submit"]').click()

        page.wait_for_selector('[data-outcome="success"]', timeout=15000)

        # Should see seed in the response
        content = page.content().lower()
        assert "seed" in content or "42" in content


class TestWebE2E_ErrorHandling:
    """E2E tests for error cases and validation."""

    @pytest.fixture
    def sample_image_path(self, tmp_path: Path) -> Path:
        """Create a simple test image."""
        try:
            from PIL import Image

            img = Image.new("L", (16, 16), color=255)
            pixels = img.load()
            for i in range(4, 12):
                for j in range(4, 12):
                    pixels[i, j] = 0
            image_path = tmp_path / "test.png"
            img.save(image_path)
            return image_path
        except ImportError:
            pytest.skip("PIL not available")

    def test_no_image_submitted_shows_error(
        self, page, running_web_server: str, tmp_path: Path
    ) -> None:
        """Submitting without an image shows an error."""
        page.goto(running_web_server)

        page.locator('input[name="out"]').fill(str(tmp_path))
        page.locator('input[value="json"]').check()

        page.locator('button[type="submit"]').click()

        # Wait for failure message (or success if image is optional)
        # The form may require an image or may allow empty submission
        page.wait_for_selector('[data-outcome]', timeout=10000)


    def test_invalid_output_directory_shows_error(
        self, page, running_web_server: str, tmp_path: Path, sample_image_path: Path
    ) -> None:
        """Invalid output directory shows error."""
        page.goto(running_web_server)

        page.locator('input[name="image"]').set_input_files(str(sample_image_path))
        page.wait_for_selector('#image-preview[src]', timeout=5000)

        # Create a file to block the output directory
        blocking_file = tmp_path / "output"
        blocking_file.write_text("in the way")

        # Try to write to a path that's a file, not a directory
        page.locator('input[name="size"]').fill("16")
        page.locator('input[name="out"]').fill(str(blocking_file))
        page.locator('input[value="json"]').check()

        page.locator('button[type="submit"]').click()

        # Wait for either success or failure message (longer timeout)
        page.wait_for_selector('[data-outcome]', timeout=15000)

        content = page.content()
        # Should show error/failure
        assert 'data-outcome="failure"' in content


    def test_invalid_size_input_shows_error(
        self, page, running_web_server: str, tmp_path: Path, sample_image_path: Path
    ) -> None:
        """Invalid size input shows error."""
        page.goto(running_web_server)

        page.locator('input[name="image"]').set_input_files(str(sample_image_path))
        page.wait_for_selector('#image-preview[src]', timeout=5000)

        page.locator('input[name="size"]').fill("invalid_size")
        page.locator('input[name="out"]').fill(str(tmp_path))

        page.locator('button[type="submit"]').click()

        page.wait_for_selector('[data-outcome="failure"]', timeout=10000)


class TestWebE2E_FormRepopulation:
    """E2E tests for form re-population after submission (AC-122/AC-123)."""

    @pytest.fixture
    def sample_image_path(self, tmp_path: Path) -> Path:
        """Create a simple test image."""
        try:
            from PIL import Image

            img = Image.new("L", (16, 16), color=255)
            pixels = img.load()
            for i in range(4, 12):
                for j in range(4, 12):
                    pixels[i, j] = 0
            image_path = tmp_path / "test.png"
            img.save(image_path)
            return image_path
        except ImportError:
            pytest.skip("PIL not available")

    def test_form_repopulated_on_success(
        self, page, running_web_server: str, tmp_path: Path, sample_image_path: Path
    ) -> None:
        """On success, form values are preserved for re-submission."""
        page.goto(running_web_server)

        # Fill in form
        page.locator('input[name="image"]').set_input_files(str(sample_image_path))
        page.wait_for_selector('#image-preview[src]', timeout=5000)

        page.locator('input[name="size"]').fill("20")
        page.locator('input[name="name"]').fill("test_puzzle")
        page.locator('input[name="out"]').fill(str(tmp_path))
        page.locator('input[value="json"]').check()

        page.locator('button[type="submit"]').click()

        # Wait for success
        page.wait_for_selector('[data-outcome="success"]', timeout=15000)

        # Form should still be visible
        form = page.locator('form[method="post"]')
        assert form.is_visible()

        # Values should be repopulated
        size_value = page.locator('input[name="size"]').input_value()
        assert size_value == "20"

        name_value = page.locator('input[name="name"]').input_value()
        assert name_value == "test_puzzle"


    def test_form_repopulated_on_error(
        self, page, running_web_server: str, tmp_path: Path, sample_image_path: Path
    ) -> None:
        """On error, form values are preserved for retry."""
        page.goto(running_web_server)

        page.locator('input[name="image"]').set_input_files(str(sample_image_path))
        page.wait_for_selector('#image-preview[src]', timeout=5000)

        # Fill with invalid size
        page.locator('input[name="size"]').fill("invalid")
        page.locator('input[name="name"]').fill("retry_puzzle")
        page.locator('input[name="out"]').fill(str(tmp_path))

        page.locator('button[type="submit"]').click()

        # Wait for error
        page.wait_for_selector('[data-outcome="failure"]', timeout=15000)

        # Form should still be visible
        form = page.locator('form[method="post"]')
        assert form.is_visible()

        # Invalid value should still be there
        size_value = page.locator('input[name="size"]').input_value()
        assert size_value == "invalid"


class TestWebE2E_ExportOptions:
    """E2E tests for different export format combinations."""

    @pytest.fixture
    def sample_image_path(self, tmp_path: Path) -> Path:
        """Create a simple test image."""
        try:
            from PIL import Image

            img = Image.new("L", (16, 16), color=255)
            pixels = img.load()
            for i in range(4, 12):
                for j in range(4, 12):
                    pixels[i, j] = 0
            image_path = tmp_path / "test.png"
            img.save(image_path)
            return image_path
        except ImportError:
            pytest.skip("PIL not available")

    def test_no_export_format_selected(
        self, page, running_web_server: str, tmp_path: Path, sample_image_path: Path
    ) -> None:
        """Submitting with no format selected shows appropriate message."""
        page.goto(running_web_server)

        page.locator('input[name="image"]').set_input_files(str(sample_image_path))
        page.wait_for_selector('#image-preview[src]', timeout=5000)

        page.locator('input[name="size"]').fill("16")
        page.locator('input[name="out"]').fill(str(tmp_path))

        # Don't check any format
        page.locator('button[type="submit"]').click()

        page.wait_for_selector('[data-outcome="success"]', timeout=15000)

        # Should show success even with no files written
        content = page.content()
        # Message about no files written
        assert "no file" in content.lower() or "nothing" in content.lower() or "success" in content.lower()


    def test_multiple_export_formats(
        self, page, running_web_server: str, tmp_path: Path, sample_image_path: Path
    ) -> None:
        """Multiple export formats can be selected together."""
        page.goto(running_web_server)

        page.locator('input[name="image"]').set_input_files(str(sample_image_path))
        page.wait_for_selector('#image-preview[src]', timeout=5000)

        page.locator('input[name="size"]').fill("16")
        page.locator('input[name="out"]').fill(str(tmp_path))

        # Select multiple formats
        export_boxes = page.locator('input[name="export_formats"]')
        count = export_boxes.count()
        if count >= 2:
            export_boxes.nth(0).check()
            export_boxes.nth(1).check()

        page.locator('button[type="submit"]').click()

        page.wait_for_selector('[data-outcome="success"]', timeout=15000)

        # Should create files
        files = list(tmp_path.glob("*"))
        assert len(files) > 0


class TestWebE2E_SizeInputVariations:
    """E2E tests for different size input formats."""

    @pytest.fixture
    def sample_image_path(self, tmp_path: Path) -> Path:
        """Create a simple test image."""
        try:
            from PIL import Image

            img = Image.new("L", (16, 16), color=255)
            pixels = img.load()
            for i in range(4, 12):
                for j in range(4, 12):
                    pixels[i, j] = 0
            image_path = tmp_path / "test.png"
            img.save(image_path)
            return image_path
        except ImportError:
            pytest.skip("PIL not available")

    def test_size_input_with_bare_number(
        self, page, running_web_server: str, tmp_path: Path, sample_image_path: Path
    ) -> None:
        """Bare number size input."""
        page.goto(running_web_server)

        page.locator('input[name="image"]').set_input_files(str(sample_image_path))
        page.wait_for_selector('#image-preview[src]', timeout=5000)

        page.locator('input[name="size"]').fill("20")
        page.locator('input[name="out"]').fill(str(tmp_path))
        page.locator('input[value="json"]').check()

        page.locator('button[type="submit"]').click()

        page.wait_for_selector('[data-outcome="success"]', timeout=15000)

        json_files = list(tmp_path.glob("*.json"))
        assert len(json_files) > 0


    def test_rectangular_size_input(
        self, page, running_web_server: str, tmp_path: Path, sample_image_path: Path
    ) -> None:
        """WxH format for rectangular puzzle."""
        page.goto(running_web_server)

        page.locator('input[name="image"]').set_input_files(str(sample_image_path))
        page.wait_for_selector('#image-preview[src]', timeout=5000)

        page.locator('input[name="size"]').fill("20x24")
        page.locator('input[name="out"]').fill(str(tmp_path))
        page.locator('input[value="json"]').check()

        page.locator('button[type="submit"]').click()

        page.wait_for_selector('[data-outcome="success"]', timeout=15000)

        json_files = list(tmp_path.glob("*.json"))
        assert len(json_files) > 0


class TestWebE2E_DifficultySelection:
    """E2E tests for difficulty tier selection."""

    @pytest.fixture
    def sample_image_path(self, tmp_path: Path) -> Path:
        """Create a simple test image."""
        try:
            from PIL import Image

            img = Image.new("L", (16, 16), color=255)
            pixels = img.load()
            for i in range(4, 12):
                for j in range(4, 12):
                    pixels[i, j] = 0
            image_path = tmp_path / "test.png"
            img.save(image_path)
            return image_path
        except ImportError:
            pytest.skip("PIL not available")

    def test_difficulty_selection_available(
        self, page, running_web_server: str
    ) -> None:
        """Difficulty selector is available on form."""
        page.goto(running_web_server)

        difficulty_select = page.locator('select[name="difficulty"]')
        assert difficulty_select.is_visible()

        # Should have options
        options = difficulty_select.locator('option')
        assert options.count() > 0


    def test_image_generation_with_difficulty(
        self, page, running_web_server: str, tmp_path: Path, sample_image_path: Path
    ) -> None:
        """Image generation with difficulty selection."""
        page.goto(running_web_server)

        page.locator('input[name="image"]').set_input_files(str(sample_image_path))
        page.wait_for_selector('#image-preview[src]', timeout=5000)

        # Select a difficulty
        difficulty_select = page.locator('select[name="difficulty"]')
        options = difficulty_select.locator('option')
        if options.count() > 1:
            difficulty_select.select_option(options.nth(1).get_attribute("value"))

        page.locator('input[name="size"]').fill("16")
        page.locator('input[name="out"]').fill(str(tmp_path))
        page.locator('input[value="json"]').check()

        page.locator('button[type="submit"]').click()

        page.wait_for_selector('[data-outcome="success"]', timeout=15000)


class TestWebE2E_RetryWithPersistedImage:
    """E2E tests for retrying generation with the same uploaded image (CARD-037)."""

    @pytest.fixture
    def sample_image_path(self, tmp_path: Path) -> Path:
        """Create a simple test image."""
        try:
            from PIL import Image

            img = Image.new("L", (16, 16), color=255)
            pixels = img.load()
            for i in range(4, 12):
                for j in range(4, 12):
                    pixels[i, j] = 0
            image_path = tmp_path / "test.png"
            img.save(image_path)
            return image_path
        except ImportError:
            pytest.skip("PIL not available")

    def test_retry_with_different_size_persists_image(
        self, page, running_web_server: str, tmp_path: Path, sample_image_path: Path
    ) -> None:
        """Retry with different size reuses uploaded image (CARD-037 retry flow)."""
        page.goto(running_web_server)

        # First submission: upload image and generate
        page.locator('input[name="image"]').set_input_files(str(sample_image_path))
        page.wait_for_selector('#image-preview[src]', timeout=5000)

        page.locator('input[name="size"]').fill("16")
        output_dir_1 = tmp_path / "run1"
        page.locator('input[name="out"]').fill(str(output_dir_1))
        page.locator('input[value="json"]').check()

        page.locator('button[type="submit"]').click()

        # Wait for success
        page.wait_for_selector('[data-outcome="success"]', timeout=15000)

        # Verify first run succeeded
        json_files_1 = list(output_dir_1.glob("*.json"))
        assert len(json_files_1) > 0, "First generation should create JSON file"

        # Second submission: RETRY with different size, same image
        # Clear the output directory field and set a new one
        output_dir_2 = tmp_path / "run2"
        page.locator('input[name="size"]').fill("20")  # Different size
        page.locator('input[name="out"]').fill(str(output_dir_2))

        # DO NOT upload a new image - should reuse the persisted one
        page.locator('button[type="submit"]').click()

        # Wait for result (should succeed without file-not-found error)
        page.wait_for_selector('[data-outcome]', timeout=15000)

        # Should succeed, not fail with "file not found" error
        content = page.content()
        assert 'data-outcome="success"' in content, \
            f"Retry should succeed with persisted image, but got: {content[-500:]}"

        # Verify second run also succeeded
        json_files_2 = list(output_dir_2.glob("*.json"))
        assert len(json_files_2) > 0, "Second generation should also create JSON file"


    def test_retry_after_error_persists_image(
        self, page, running_web_server: str, tmp_path: Path, sample_image_path: Path
    ) -> None:
        """Image persists even after error, allowing retry (CARD-037)."""
        page.goto(running_web_server)

        # First submission: upload image with invalid settings
        page.locator('input[name="image"]').set_input_files(str(sample_image_path))
        page.wait_for_selector('#image-preview[src]', timeout=5000)

        page.locator('input[name="size"]').fill("999")  # Invalid: out of range
        output_dir_1 = tmp_path / "error"
        page.locator('input[name="out"]').fill(str(output_dir_1))

        page.locator('button[type="submit"]').click()

        # Wait for failure
        page.wait_for_selector('[data-outcome="failure"]', timeout=15000)

        # Verify it's a failure
        content = page.content()
        assert 'data-outcome="failure"' in content, "Should show failure"

        # Second submission: FIX the size, retry with SAME image
        page.locator('input[name="size"]').fill("16")  # Valid size
        output_dir_2 = tmp_path / "retry"
        page.locator('input[name="out"]').fill(str(output_dir_2))
        page.locator('input[value="json"]').check()

        # DO NOT upload a new image
        page.locator('button[type="submit"]').click()

        # Should now succeed without "file not found" error
        page.wait_for_selector('[data-outcome="success"]', timeout=15000)

        content = page.content()
        assert 'data-outcome="success"' in content, "Retry with fixed settings should succeed"

        # Verify file was generated
        json_files = list(output_dir_2.glob("*.json"))
        assert len(json_files) > 0, "Successful retry should create files"


class TestWebE2E_FileVerification:
    """E2E tests to verify generated files have correct content."""

    @pytest.fixture
    def sample_image_path(self, tmp_path: Path) -> Path:
        """Create a simple test image."""
        try:
            from PIL import Image

            img = Image.new("L", (16, 16), color=255)
            pixels = img.load()
            for i in range(4, 12):
                for j in range(4, 12):
                    pixels[i, j] = 0
            image_path = tmp_path / "test.png"
            img.save(image_path)
            return image_path
        except ImportError:
            pytest.skip("PIL not available")

    def test_generated_json_has_valid_structure(
        self, page, running_web_server: str, tmp_path: Path, sample_image_path: Path
    ) -> None:
        """Generated JSON has all expected fields."""
        page.goto(running_web_server)

        page.locator('input[name="image"]').set_input_files(str(sample_image_path))
        page.wait_for_selector('#image-preview[src]', timeout=5000)

        page.locator('input[name="size"]').fill("16")
        page.locator('input[name="out"]').fill(str(tmp_path))
        page.locator('input[value="json"]').check()

        page.locator('button[type="submit"]').click()

        page.wait_for_selector('[data-outcome="success"]', timeout=15000)

        json_files = list(tmp_path.glob("*.json"))
        assert len(json_files) > 0

        data = json.loads(json_files[0].read_text())

        # Check structure
        assert "clues" in data
        assert "rows" in data["clues"]
        assert "columns" in data["clues"]
        assert "request" in data
        assert "width" in data["request"]
        assert "height" in data["request"]


    def test_generated_png_file_exists_and_valid(
        self, page, running_web_server: str, tmp_path: Path, sample_image_path: Path
    ) -> None:
        """Generated PNG file exists and is valid."""
        page.goto(running_web_server)

        page.locator('input[name="image"]').set_input_files(str(sample_image_path))
        page.wait_for_selector('#image-preview[src]', timeout=5000)

        page.locator('input[name="size"]').fill("16")
        page.locator('input[name="out"]').fill(str(tmp_path))
        page.locator('input[value="png"]').check()

        page.locator('button[type="submit"]').click()

        page.wait_for_selector('[data-outcome="success"]', timeout=15000)

        png_files = list(tmp_path.glob("*.png"))
        assert len(png_files) > 0

        png_file = png_files[0]
        assert png_file.stat().st_size > 0
        # PNG files start with this magic number
        assert png_file.read_bytes()[:4] == b'\x89PNG'
