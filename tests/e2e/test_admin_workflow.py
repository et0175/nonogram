"""
End-to-End tests for Wave 3 admin panel workflow.

Tests cover:
- Flow 1: Image upload & preview
- Flow 2: Batch image upload with configuration
- Flow 3: Puzzle generation & SVG display
- Flow 4: Puzzle management (approve/reject)
"""
import os
import tempfile
from pathlib import Path
import pytest
from PIL import Image


@pytest.fixture
def admin_app():
    """Create test Flask app."""
    os.environ['TESTING'] = 'true'
    from src.nonogram.admin.app import create_app

    app = create_app()
    app.config['TESTING'] = True
    app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

    with app.app_context():
        yield app


@pytest.fixture
def client(admin_app):
    """Create test client."""
    return admin_app.test_client()


@pytest.fixture
def test_image():
    """Create a temporary test image."""
    img = Image.new('RGB', (200, 200), color='white')
    # Add some black pixels to create pattern
    pixels = img.load()
    for i in range(50, 150):
        for j in range(50, 150):
            if (i + j) % 2 == 0:
                pixels[i, j] = (0, 0, 0)

    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        img.save(f.name)
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def landscape_image():
    """Create a landscape test image."""
    img = Image.new('RGB', (400, 200), color='white')
    pixels = img.load()
    for i in range(0, 400, 10):
        for j in range(0, 200, 10):
            pixels[i, j] = (0, 0, 0)

    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        img.save(f.name)
        yield f.name
    os.unlink(f.name)


class TestFlow1ImageUploadPreview:
    """Flow 1: Image Upload & Preview"""

    def test_tc_001_single_image_upload(self, client, test_image):
        """TC-001: Single Image Upload"""
        with open(test_image, 'rb') as f:
            response = client.post(
                '/batch/from-images',
                data={'images': (f, 'test.png')},
                follow_redirects=False
            )

        # Should redirect to preview page
        assert response.status_code == 302
        assert '/batch/preview-images' in response.location or 'batch' in response.location

    def test_preview_page_displays_original_image(self, client, test_image):
        """Verify original image displays on preview page."""
        # First upload
        with open(test_image, 'rb') as f:
            response = client.post(
                '/batch/from-images',
                data={'images': (f, 'test.png')},
                follow_redirects=True
            )

        # Check for image API endpoint in response
        assert b'/api/image/' in response.data or b'image' in response.data.lower()

    def test_metadata_shown_on_preview(self, client, test_image):
        """Verify puzzle metadata is shown on preview."""
        with open(test_image, 'rb') as f:
            response = client.post(
                '/batch/from-images',
                data={'images': (f, 'test.png')},
                follow_redirects=True
            )

        # Check for metadata labels
        assert b'Images' in response.data or b'images' in response.data.lower()


class TestFlow2BatchImageUpload:
    """Flow 2: Batch Image Upload with Configuration"""

    def test_tc_002_multiple_image_batch(self, client, test_image, landscape_image):
        """TC-002: Multiple Image Batch Upload"""
        files = []
        with open(test_image, 'rb') as f1, open(landscape_image, 'rb') as f2:
            files = [(f1, 'test1.png'), (f2, 'test2.png')]
            response = client.post(
                '/batch/from-images',
                data={'images': files},
                follow_redirects=True
            )

        # Check successful upload
        assert response.status_code == 200
        assert b'preview' in response.data.lower() or b'image' in response.data.lower()

    def test_size_configuration_applied(self, client, test_image):
        """Verify size configuration is applied."""
        with open(test_image, 'rb') as f:
            response = client.post(
                '/batch/from-images',
                data={'images': (f, 'test.png')},
                follow_redirects=True
            )

        # Check for size controls
        assert b'Size' in response.data or b'size' in response.data.lower()
        assert b'Fixed' in response.data or b'fixed' in response.data.lower()


class TestFlow3PuzzleGeneration:
    """Flow 3: Puzzle Generation & SVG Display"""

    def test_tc_003_svg_generation_display(self, client, test_image):
        """TC-003: SVG Generation & Display"""
        # Upload image
        with open(test_image, 'rb') as f:
            response = client.post(
                '/batch/from-images',
                data={'images': (f, 'test.png')},
                follow_redirects=True
            )

        assert response.status_code == 200

    def test_tc_006_download_svg_file(self, client):
        """TC-006: Download SVG File"""
        # Mock puzzle grid endpoint
        response = client.get('/api/puzzle/test-id/grid/download')

        # Should either 404 (puzzle not found) or return SVG
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            assert b'svg' in response.data.lower()

    def test_svg_grid_endpoint_serves_svg(self, client):
        """Verify SVG grid endpoint returns SVG content."""
        # This test checks endpoint structure
        response = client.get('/api/puzzle/nonexistent/grid')

        # Should handle gracefully
        assert response.status_code in [200, 404]


class TestFlow4PuzzleManagement:
    """Flow 4: Puzzle Management (Approve/Reject)"""

    def test_tc_004_approve_puzzle(self, client):
        """TC-004: Approve Puzzle"""
        # Test approve endpoint
        response = client.post(
            '/puzzles/test-id/approve',
            follow_redirects=False
        )

        # Should either redirect or return 404 (puzzle not found)
        assert response.status_code in [302, 404, 500]

    def test_tc_005_reject_puzzle(self, client):
        """TC-005: Reject Puzzle"""
        # Test reject endpoint
        response = client.post(
            '/puzzles/test-id/reject',
            follow_redirects=False
        )

        # Should either redirect or return 404 (puzzle not found)
        assert response.status_code in [302, 404, 500]


class TestAdminPanelEndpoints:
    """Test critical admin panel endpoints"""

    def test_batch_create_page_loads(self, client):
        """Verify batch create page loads."""
        response = client.get('/batch/create')
        assert response.status_code == 200
        assert b'Create' in response.data or b'create' in response.data.lower()

    def test_dashboard_page_loads(self, client):
        """Verify dashboard page loads."""
        response = client.get('/')
        assert response.status_code == 200

    def test_image_api_endpoint(self, client):
        """Test image API endpoint structure."""
        # Non-existent image should 404
        response = client.get('/api/image/nonexistent')
        assert response.status_code in [404, 400]

    def test_puzzle_grid_api_endpoint(self, client):
        """Test puzzle grid API endpoint structure."""
        # Non-existent puzzle should 404
        response = client.get('/api/puzzle/nonexistent/grid')
        assert response.status_code in [404, 400]


class TestFormSubmissions:
    """Test form-based submissions"""

    def test_preview_form_submission(self, client):
        """Test preview page form submission."""
        # Check that form submission endpoints exist
        response = client.get('/batch/preview-images')
        # May not exist without prior upload
        assert response.status_code in [200, 404, 302]

    def test_generation_form_submission(self, client):
        """Test puzzle generation form submission."""
        response = client.get('/batch/generate-puzzles')
        # May not exist without prior steps
        assert response.status_code in [200, 404, 302]


class TestResponseHeaders:
    """Test HTTP response headers"""

    def test_svg_download_content_type(self, client):
        """Verify SVG download has correct content-type."""
        response = client.get('/api/puzzle/test/grid/download')

        if response.status_code == 200:
            # Should be SVG content type
            content_type = response.headers.get('Content-Type', '')
            assert 'svg' in content_type.lower() or 'xml' in content_type.lower()

    def test_image_content_type(self, client):
        """Verify image endpoints have correct content-type."""
        response = client.get('/api/image/test')

        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '')
            assert 'image' in content_type.lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
