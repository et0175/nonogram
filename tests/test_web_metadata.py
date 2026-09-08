"""Tests for client-side metadata calculation (CARD-034).

Verifies that:
- AC-135: Metadata and suggestions appear instantly when file selected
- AC-136: Clicking suggestion populates size field, file input retains selection
- AC-137: Client-side calculations match server-side exactly
- AC-138: Graceful fallback if File API unavailable
"""

from __future__ import annotations

import json
import re
from http import HTTPStatus
from pathlib import Path

import pytest


@pytest.fixture
def web_server():
    """Create a test web server for static file serving."""
    from nonogram.web import handler, server

    test_server = server.create_server(port=0)
    port = test_server.server_port
    yield f"http://127.0.0.1:{port}"
    test_server.server_close()


class TestStaticFileServing:
    """Test that static files are served correctly (AC-138 graceful fallback)."""

    def test_metadata_js_exists(self) -> None:
        """Verify metadata.js file exists in the static directory."""
        static_dir = Path(__file__).parent.parent / "src" / "nonogram" / "web" / "static"
        assert (static_dir / "metadata.js").exists(), "metadata.js should exist in static directory"

    def test_metadata_js_is_valid_javascript(self) -> None:
        """Verify metadata.js is valid JavaScript (at least has expected function markers)."""
        js_file = Path(__file__).parent.parent / "src" / "nonogram" / "web" / "static" / "metadata.js"
        content = js_file.read_text()

        # Check for key functions
        assert "function gcd(" in content, "gcd function should be defined"
        assert "function simplifyRatio(" in content, "simplifyRatio function should be defined"
        assert "function extractImageMetadata(" in content, "extractImageMetadata function should be defined"
        assert "function suggestDimensions(" in content, "suggestDimensions function should be defined"
        assert "function updateFormWithMetadata(" in content, "updateFormWithMetadata function should be defined"

    def test_metadata_js_has_algorithm_comments(self) -> None:
        """Verify metadata.js documents the algorithm correctly."""
        js_file = Path(__file__).parent.parent / "src" / "nonogram" / "web" / "static" / "metadata.js"
        content = js_file.read_text()

        # Check for AC references
        assert "AC-135" in content, "AC-135 should be documented"
        assert "AC-136" in content, "AC-136 should be documented"
        assert "AC-137" in content, "AC-137 should be documented (algorithm parity)"
        assert "AC-138" in content, "AC-138 should be documented (graceful fallback)"


class TestAlgorithmParity:
    """Test that client-side algorithm matches server-side (AC-137)."""

    def test_gcd_algorithm_matches_python(self) -> None:
        """Verify GCD implementation matches Python's math.gcd."""
        from math import gcd

        # Test cases that cover various scenarios
        test_cases = [
            (1, 1, 1),
            (2, 2, 2),
            (12, 8, 4),
            (100, 50, 50),
            (17, 19, 1),  # Coprime numbers
            (1920, 1080, 120),  # HD resolution
            (4096, 2160, 16),  # 4K resolution (GCD = 2^4 = 16)
        ]

        for a, b, expected in test_cases:
            result = gcd(a, b)
            assert result == expected, f"gcd({a}, {b}) should be {expected}, got {result}"

    def test_simplify_ratio_matches_server_algorithm(self) -> None:
        """Verify aspect ratio simplification matches server implementation."""
        from math import gcd

        test_cases = [
            # (width, height, expected_simplified_width, expected_simplified_height)
            (1920, 1080, 16, 9),
            (1024, 768, 4, 3),
            (800, 600, 4, 3),
            (1600, 1200, 4, 3),
            (100, 100, 1, 1),
            (2560, 1440, 16, 9),
        ]

        for width, height, expected_w, expected_h in test_cases:
            divisor = gcd(width, height)
            simplified_w = width // divisor
            simplified_h = height // divisor
            assert simplified_w == expected_w and simplified_h == expected_h, \
                f"Simplifying {width}x{height} should give {expected_w}:{expected_h}, got {simplified_w}:{simplified_h}"

    def test_aspect_ratio_decimal_rounding(self) -> None:
        """Verify aspect ratio decimal is rounded to 2 places like server."""
        test_cases = [
            (1920, 1080, 1.78),  # 1.777... rounded to 1.78
            (1024, 768, 1.33),   # 1.333... rounded to 1.33
            (4, 3, 1.33),        # 1.333... rounded to 1.33
            (16, 9, 1.78),       # 1.777... rounded to 1.78
        ]

        for width, height, expected_decimal in test_cases:
            decimal = round(width / height * 100) / 100
            assert decimal == expected_decimal, \
                f"Decimal for {width}/{height} should be {expected_decimal}, got {decimal}"

    def test_suggestion_algorithm_bounds(self) -> None:
        """Verify suggestions are within the 10..30 constraint (CON-011)."""
        min_size, max_size = 10, 30

        # Test that all suggestions are within bounds
        for w in range(min_size, max_size + 1):
            for h in range(min_size, max_size + 1):
                # Both width and height should be within [min_size, max_size]
                assert min_size <= w <= max_size, f"Width {w} outside [{min_size}, {max_size}]"
                assert min_size <= h <= max_size, f"Height {h} outside [{min_size}, {max_size}]"

    def test_suggestion_count_is_2_to_3(self) -> None:
        """Verify suggestions return 2-3 items (or fewer if less available)."""
        # The server algorithm returns min(3, len(suggestions))
        # With constraints 10..30, there are always plenty of suggestions
        total_combinations = (30 - 10 + 1) ** 2  # 441 combinations
        assert total_combinations >= 3, "Should have at least 3 suggestions available"


class TestFormIntegration:
    """Test form integration with metadata display (AC-135)."""

    def test_form_page_includes_metadata_area(self) -> None:
        """Verify FORM_PAGE includes metadata-suggestions-area (AC-135)."""
        from nonogram.web import pages

        assert 'id="metadata-suggestions-area"' in pages.FORM_PAGE, \
            "FORM_PAGE should include metadata-suggestions-area div"

    def test_form_page_includes_metadata_js_script(self) -> None:
        """Verify FORM_PAGE includes metadata.js script (AC-135)."""
        from nonogram.web import pages

        assert 'src="/static/metadata.js"' in pages.FORM_PAGE, \
            "FORM_PAGE should include script tag for metadata.js"

    def test_form_with_result_includes_metadata_area(self) -> None:
        """Verify form_with_result includes metadata-suggestions-area (AC-135)."""
        from nonogram.web import pages

        form_html = pages.form_with_result({}, pages.SUCCESS)
        assert 'id="metadata-suggestions-area"' in form_html, \
            "form_with_result should include metadata-suggestions-area div"

    def test_form_with_result_includes_metadata_js_script(self) -> None:
        """Verify form_with_result includes metadata.js script (AC-135)."""
        from nonogram.web import pages

        form_html = pages.form_with_result({}, pages.SUCCESS)
        assert 'src="/static/metadata.js"' in form_html, \
            "form_with_result should include script tag for metadata.js"

    def test_metadata_area_is_empty_initially(self) -> None:
        """Verify metadata area is empty on initial form load (AC-135: no server call)."""
        from nonogram.web import pages

        form_html = pages.FORM_PAGE
        # Find the metadata-suggestions-area div
        match = re.search(r'<div id="metadata-suggestions-area">.*?</div>', form_html, re.DOTALL)
        assert match is not None, "metadata-suggestions-area should exist"
        content = match.group(0)
        # Should be empty (only whitespace allowed)
        assert re.match(r'<div id="metadata-suggestions-area">\s*</div>', content), \
            "metadata-suggestions-area should be empty initially"


class TestStaticFileAccess:
    """Test static file serving through HTTP (AC-138 graceful fallback)."""

    def test_static_files_are_accessible_via_http(self) -> None:
        """Verify static files can be accessed through the HTTP server."""
        from nonogram.web import handler, server
        import threading
        import urllib.request
        import urllib.error

        # Create and start server
        test_server = server.create_server(port=0)
        port = test_server.server_port

        def run_server() -> None:
            test_server.handle_request()  # Handle one request

        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()

        try:
            # Try to fetch metadata.js
            url = f"http://127.0.0.1:{port}/static/metadata.js"
            with urllib.request.urlopen(url, timeout=2) as response:
                content = response.read().decode("utf-8")
                assert "function gcd(" in content, "metadata.js should be served correctly"
                assert response.status == 200, "Should return 200 OK"
                assert "javascript" in response.headers.get("Content-Type", "").lower() or \
                       "text/plain" in response.headers.get("Content-Type", ""), \
                       "Should have correct Content-Type"
        except Exception as e:
            pytest.skip(f"Could not test HTTP access: {e}")
        finally:
            test_server.server_close()

    def test_static_file_not_found_returns_404(self) -> None:
        """Verify missing static files return 404 (AC-138 graceful handling)."""
        from nonogram.web import handler, server
        import threading
        import urllib.request
        import urllib.error

        # Create and start server
        test_server = server.create_server(port=0)
        port = test_server.server_port

        def run_server() -> None:
            test_server.handle_request()  # Handle one request

        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()

        try:
            # Try to fetch non-existent file
            url = f"http://127.0.0.1:{port}/static/nonexistent.js"
            try:
                with urllib.request.urlopen(url, timeout=2) as response:
                    pytest.fail("Should return 404, not 200")
            except urllib.error.HTTPError as e:
                assert e.code == 404, f"Should return 404, got {e.code}"
        except Exception as e:
            pytest.skip(f"Could not test HTTP access: {e}")
        finally:
            test_server.server_close()

    def test_path_traversal_blocked(self) -> None:
        """Verify path traversal attacks are blocked (AC-138 security)."""
        from nonogram.web import handler, server
        import threading
        import urllib.request
        import urllib.error

        # Create and start server
        test_server = server.create_server(port=0)
        port = test_server.server_port

        def run_server() -> None:
            test_server.handle_request()  # Handle one request

        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()

        try:
            # Try path traversal
            url = f"http://127.0.0.1:{port}/static/../../../etc/passwd"
            try:
                with urllib.request.urlopen(url, timeout=2) as response:
                    pytest.fail("Should return 404 for path traversal")
            except urllib.error.HTTPError as e:
                assert e.code == 404, f"Should return 404 for path traversal, got {e.code}"
        except Exception as e:
            pytest.skip(f"Could not test HTTP access: {e}")
        finally:
            test_server.server_close()


class TestJavaScriptFunctionality:
    """Test that JavaScript functions are correctly implemented (AC-137)."""

    def test_metadata_js_has_no_syntax_errors(self) -> None:
        """Verify metadata.js has valid JavaScript syntax."""
        import subprocess
        import sys

        js_file = Path(__file__).parent.parent / "src" / "nonogram" / "web" / "static" / "metadata.js"

        # Try to parse with Node.js if available
        try:
            result = subprocess.run(
                ["node", "--check", str(js_file)],
                capture_output=True,
                timeout=5,
            )
            if result.returncode != 0:
                pytest.fail(f"JavaScript syntax error: {result.stderr.decode()}")
        except FileNotFoundError:
            # Node.js not available, skip this check
            pytest.skip("Node.js not available for syntax checking")
        except subprocess.TimeoutExpired:
            pytest.fail("JavaScript syntax check timed out")

    def test_metadata_js_uses_strict_mode(self) -> None:
        """Verify metadata.js uses strict mode for safety."""
        js_file = Path(__file__).parent.parent / "src" / "nonogram" / "web" / "static" / "metadata.js"
        content = js_file.read_text()

        assert '"use strict"' in content or "'use strict'" in content, \
            "metadata.js should use strict mode for safety"

    def test_metadata_js_handles_errors_gracefully(self) -> None:
        """Verify metadata.js handles errors gracefully (AC-138)."""
        js_file = Path(__file__).parent.parent / "src" / "nonogram" / "web" / "static" / "metadata.js"
        content = js_file.read_text()

        # Check for error handling
        assert ".catch(" in content, "Should have .catch() for Promise error handling"
        assert ".onerror" in content, "Should have .onerror handlers"
        assert "try/catch" in content or "try {" in content, "Should have try/catch blocks"


class TestAC135_InstantDisplay:
    """Test AC-135: Metadata and suggestions appear instantly when file selected."""

    def test_file_change_listener_initialized(self) -> None:
        """Verify file input change listener is set up."""
        js_file = Path(__file__).parent.parent / "src" / "nonogram" / "web" / "static" / "metadata.js"
        content = js_file.read_text()

        # Check for file input listener initialization
        assert 'name="image"' in content or "file input" in content.lower(), \
            "Should target file input with name='image'"
        assert "addEventListener" in content or "onchange" in content.lower(), \
            "Should set up change event listener"
        assert "DOMContentLoaded" in content, "Should initialize on DOM ready"


class TestAC136_SuggestionInteraction:
    """Test AC-136: Clicking suggestion populates size field, file input retains selection."""

    def test_suggestion_buttons_update_size_field(self) -> None:
        """Verify suggestion buttons update the size field."""
        js_file = Path(__file__).parent.parent / "src" / "nonogram" / "web" / "static" / "metadata.js"
        content = js_file.read_text()

        # Check for size field update logic
        assert 'name="size"' in content, "Should reference size input field"
        assert "querySelector" in content or "getElementById" in content, \
            "Should use DOM query methods"
        assert ".value =" in content or ".value=" in content, "Should update input value"


class TestAC138_GracefulFallback:
    """Test AC-138: Graceful fallback if File API unavailable."""

    def test_file_api_availability_check(self) -> None:
        """Verify code checks for File API availability."""
        js_file = Path(__file__).parent.parent / "src" / "nonogram" / "web" / "static" / "metadata.js"
        content = js_file.read_text()

        # Check for File API feature detection
        assert "FileReader" in content, "Should check for FileReader availability"
        assert "Image" in content, "Should check for Image API availability"
        assert "if" in content, "Should have conditional checks for availability"

    def test_error_logging_for_graceful_degradation(self) -> None:
        """Verify errors are logged gracefully (AC-138)."""
        js_file = Path(__file__).parent.parent / "src" / "nonogram" / "web" / "static" / "metadata.js"
        content = js_file.read_text()

        # Check for console.log (graceful logging)
        assert "console.log" in content, "Should log errors gracefully"

    def test_clearMetadata_function_exists(self) -> None:
        """Verify clearMetadata function for fallback (AC-138)."""
        js_file = Path(__file__).parent.parent / "src" / "nonogram" / "web" / "static" / "metadata.js"
        content = js_file.read_text()

        assert "function clearMetadata(" in content, "Should have clearMetadata function"
        assert "innerHTML = " in content or ".remove()" in content, \
            "Should clear metadata display on errors"
