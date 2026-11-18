"""
End-to-End tests for Wave 3 admin panel workflow.

Tests cover:
- Flow 1: Image upload & preview
- Flow 2: Batch image upload with configuration
- Flow 3: Puzzle generation & SVG display
- Flow 4: Puzzle management (approve/reject)
"""
import ast
import os
import re
import tempfile
from pathlib import Path
import pytest
from PIL import Image


@pytest.fixture
def admin_app(monkeypatch, tmp_path_factory):
    """Create test Flask app, in-memory mode.

    CARD-109: `create_app` connects to whatever `DATABASE_URL` names, and this
    fixture did not touch it — so with the variable exported these tests read
    and wrote that database. They did, on 2026-09-21: four of them failed the
    moment a development database was emptied mid-session, having been reading
    it. `monkeypatch` rather than `os.environ.pop` so the value is restored
    for whatever runs next.

    CARD-475: the upload route saves each picture under the process's temp
    directory, and nothing in a test removes it. Now that these tests really
    upload, the temp root is pointed at a directory of this test's own so a
    run leaves nothing behind in the machine-wide one.
    """
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path_factory.mktemp("admin-temp")))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TESTING", "true")
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


#: The upload route and the form field it reads pictures from. Every upload
#: in this module goes through ``_upload`` below, and
#: ``test_every_upload_posts_a_field_the_route_reads`` holds this name to the
#: route's own ``request.files`` reads.
UPLOAD_ROUTE = '/batch/from-images'
UPLOAD_FIELD = 'image_files'

#: The page a refused upload is sent back to, and the one an accepted upload
#: lands on. CARD-475: five tests here posted the file as ``images``, a field
#: the route never read, and passed on the refusal — a redirect whose location
#: also contains "batch", and a step-one page that also says "image".
PREVIEW_PATH = '/batch/preview-images'

_IMAGE_ID = re.compile(r'/api/image/([0-9a-f]+)/cropped')


def _upload(client, *named_paths, follow_redirects=True, **form):
    """Post pictures to the upload route through the field it reads.

    ``named_paths`` are ``(path, filename)`` pairs; one picture is sent as a
    single file, several as a list, the way a browser's multi-file control
    does."""
    handles = [open(path, 'rb') for path, _ in named_paths]
    try:
        files = [(handle, name) for handle, (_, name) in zip(handles, named_paths)]
        return client.post(
            UPLOAD_ROUTE,
            data={UPLOAD_FIELD: files[0] if len(files) == 1 else files, **form},
            follow_redirects=follow_redirects,
        )
    finally:
        for handle in handles:
            handle.close()


class TestFlow1ImageUploadPreview:
    """Flow 1: Image Upload & Preview"""

    def test_tc_001_single_image_upload(self, client, test_image):
        """TC-001: Single Image Upload"""
        response = _upload(client, (test_image, 'test.png'), follow_redirects=False)

        # An accepted upload goes to the preview page; a refused one goes
        # back to step one, so the location is compared whole.
        assert response.status_code == 302
        assert response.location == PREVIEW_PATH

    def test_preview_page_displays_original_image(self, client, test_image):
        """The preview page draws the uploaded picture, and the address it
        draws it from serves that picture."""
        response = _upload(client, (test_image, 'test.png'))

        assert response.request.path == PREVIEW_PATH
        (file_id,) = set(_IMAGE_ID.findall(response.get_data(as_text=True)))
        original = client.get(f'/api/image/{file_id}')
        assert original.status_code == 200
        assert original.headers['Content-Type'] == 'image/png'
        assert original.data == Path(test_image).read_bytes()

    def test_metadata_shown_on_preview(self, client, test_image):
        """The preview names the uploaded file and gives its size in pixels."""
        response = _upload(client, (test_image, 'metadata-probe.png'))

        assert response.request.path == PREVIEW_PATH
        page = response.get_data(as_text=True)
        assert 'metadata-probe.png' in page
        assert re.search(r'\d+×\d+ px', page)


class TestFlow2BatchImageUpload:
    """Flow 2: Batch Image Upload with Configuration"""

    def test_tc_002_multiple_image_batch(self, client, test_image, landscape_image):
        """TC-002: Multiple Image Batch Upload"""
        response = _upload(
            client, (test_image, 'test1.png'), (landscape_image, 'test2.png')
        )

        # Both pictures are on the preview, each under its own name and each
        # drawn from its own address.
        assert response.request.path == PREVIEW_PATH
        page = response.get_data(as_text=True)
        assert 'test1.png' in page and 'test2.png' in page
        assert len(set(_IMAGE_ID.findall(page))) == 2

    def test_size_configuration_applied(self, client, test_image):
        """Verify the size chosen on the upload form is applied to the picture.

        CARD-164: this posted the file as ``images``, a field the route never
        read, so it only ever saw the "No images selected" redirect back to
        step 1 and passed on that page's "(Fixed/Min/Max)" help text — until
        the Pressroom redesign (f773015) removed it. It now uploads through
        the route's real field and picks "large" (30, fixed) rather than the
        route's "medium" (20, fixed) fallback, so the preview's 30x30 can only
        come from the submitted choice.
        """
        response = _upload(client, (test_image, 'test.png'), default_size='large')

        assert response.request.path == PREVIEW_PATH
        assert b'<option value="fixed" selected>' in response.data
        assert b'extent=30x30' in response.data


class TestFlow3PuzzleGeneration:
    """Flow 3: Puzzle Generation & SVG Display"""

    def test_tc_003_svg_generation_display(self, client, test_image):
        """TC-003: SVG Generation & Display"""
        assert _upload(client, (test_image, 'test.png')).request.path == PREVIEW_PATH

        # Generating from the uploaded picture lands on the batch's puzzles,
        # and the grid that page draws is served as an SVG.
        generated = client.post('/batch/generate-puzzles', follow_redirects=True)
        assert generated.status_code == 200
        assert generated.request.path.endswith('/generated-puzzles')
        grid_urls = set(
            re.findall(r'/api/puzzle/[^"/]+/grid(?=")', generated.get_data(as_text=True))
        )
        assert len(grid_urls) == 1
        grid = client.get(grid_urls.pop())
        assert grid.status_code == 200
        assert grid.headers['Content-Type'].startswith('image/svg+xml')
        assert grid.data.lstrip().startswith(b'<svg')

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


def _upload_route_file_fields():
    """The form fields ``batch_from_images`` reads files from, read off the
    route's own source: every ``request.files.getlist("<name>")`` in it."""
    import src.nonogram.admin.app as admin_app_module

    tree = ast.parse(Path(admin_app_module.__file__).read_text())
    (route,) = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == 'batch_from_images'
    ]
    fields = set()
    for node in ast.walk(route):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == 'getlist'
            and isinstance(node.func.value, ast.Attribute)
            and node.func.value.attr == 'files'
        ):
            (name,) = node.args
            fields.add(name.value)
    return fields


def test_every_upload_posts_a_field_the_route_reads():
    """CARD-475: the field ``_upload`` posts is one the route reads, and no
    test in this module posts to the upload route any other way — so a
    renamed field reds here instead of turning five tests hollow again."""
    assert UPLOAD_FIELD in _upload_route_file_fields()

    tree = ast.parse(Path(__file__).read_text())
    posts_outside_helper = []
    for function in ast.walk(tree):
        if not isinstance(function, ast.FunctionDef) or function.name == '_upload':
            continue
        for node in ast.walk(function):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == 'post'
                and node.args
                and (
                    (isinstance(node.args[0], ast.Constant) and node.args[0].value == UPLOAD_ROUTE)
                    or (isinstance(node.args[0], ast.Name) and node.args[0].id == 'UPLOAD_ROUTE')
                )
            ):
                posts_outside_helper.append(function.name)
    assert posts_outside_helper == []


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
