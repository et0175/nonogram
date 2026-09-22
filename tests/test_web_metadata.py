"""Tests for client-side metadata calculation (CARD-034).

Verifies that:
- AC-135: Metadata and suggestions appear instantly when file selected
- AC-136: Clicking suggestion populates size field, file input retains selection
- AC-137: Client-side calculations match server-side exactly
- AC-138: Graceful fallback if File API unavailable
"""

from __future__ import annotations

import json
import math
import re
from http import HTTPStatus
from pathlib import Path

import pytest

from nonogram.limits import MAX_SIZE, MIN_SIZE


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
    """AC-138, minus the half that was never true.

    The criterion read "no error if File API unavailable; suggestions shown
    after submission as before (CARD-031 fallback)". There has never been such
    a fallback: CARD-031's server-side rendering had zero call sites from the
    day it was written, and CARD-104 deleted it. A browser without the File API
    gets no metadata at all — before that deletion and after it.

    The second clause is retired in the card. What is tested here is the first:
    the script looks before it leaps, and says so in the console rather than
    throwing.
    """

    def test_file_api_availability_check(self) -> None:
        """Verify code checks for File API availability."""
        js_file = Path(__file__).parent.parent / "src" / "nonogram" / "web" / "static" / "metadata.js"
        content = js_file.read_text()

        # CARD-034 deleted two assertions from here that could not fail:
        # `"Image" in content` is satisfied by the word inside
        # `extractImageMetadata`, and `"if" in content` is true of every
        # JavaScript file ever written. What is left is a grep too, but a
        # grep for something that would genuinely be absent if the feature
        # detection were removed.
        assert "FileReader" in content, "Should check for FileReader availability"

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


# ---------------------------------------------------------------------------
# CARD-105 — AC-137 checked by running both implementations, not by reading them
#
# ``TestAlgorithmParity`` above asserts Python against Python: its "gcd matches"
# test calls ``math.gcd`` and compares it to hardcoded numbers, and the rest
# greps metadata.js for function names. That keeps two implementations of one
# algorithm in step by review, which is where every other drift in this
# repository started.
#
# These run the JavaScript. ``node`` is opportunistic and stays undeclared —
# ADR-0006's baseline is stdlib + Pillow + NumPy and this does not change it —
# so its absence skips, exactly as test_metadata_js_has_no_syntax_errors does.
# ---------------------------------------------------------------------------

#: The three functions the suggestion algorithm is made of, in metadata.js.
_PARITY_FUNCTIONS = ("gcd", "simplifyRatio", "suggestDimensions")

#: Source (width, height) pairs to compare over. Ties, extremes and the
#: project's own fixture ratios; the count is asserted in the test so the
#: corpus cannot silently shrink to nothing and leave a green test behind.
_RATIO_CORPUS = [
    (1000, 1000),   # 1:1 — every square 10x10..30x30 ties at error 0.0
    (1024, 768),    # 4:3
    (1920, 1080),   # 16:9
    (768, 1024),    # 3:4
    (1080, 1920),   # 9:16
    (2560, 1440),   # 16:9 again, reached through a different gcd
    (3000, 1000),   # 3:1 — past the widest grid the range allows
    (1000, 3000),   # 1:3
    (640, 480),     # 4:3, small
    (563, 980),     # the ratio FR-021's own test fixture uses
    (1234, 4321),   # coprime, extreme
    (100, 101),     # near-square, ties broken by a hair
    (999, 1000),    # near-square the other way
    (16, 9),        # already simplified on the way in
    (7, 3),         # coprime, inside the range
    (30, 10),       # exactly representable as a grid
]


def _extract_js_function(source: str, name: str) -> str:
    """Cut ``function <name>(...) {...}`` out of *source* by brace matching.

    The point of reading the shipped file rather than restating the algorithm
    is that a copy in this test would agree with itself forever (G-3). The cost
    is that this depends on the file's shape, so it fails loudly — a missing
    function or an unbalanced body raises here rather than quietly comparing
    nothing.
    """
    marker = f"function {name}("
    start = source.find(marker)
    if start == -1:
        raise AssertionError(
            f"metadata.js no longer defines `{marker}` — the parity harness "
            "reads the shipped source, so it has to be updated with it"
        )

    depth = 0
    for index in range(source.index("{", start), len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    raise AssertionError(f"unbalanced braces in metadata.js's `{name}`")


def _parity_harness(js_source: str) -> str:
    """The extracted functions plus a driver that prints JSON on stdout.

    The driver builds its argument the way ``extractImageMetadata`` does —
    ``simplifyRatio`` returns an **array** while ``suggestDimensions`` reads
    ``.width``/``.height``, and production reconciles the two. A harness that
    passes the array straight through gets ``undefined``, so every ratio error
    is ``NaN``, so the comparator returns ``NaN``, so ``sort`` leaves insertion
    order alone — and every ratio then "returns" the first three candidates,
    [10,10], [10,11], [10,12]. That failure looks like a total disagreement
    between the two implementations and is entirely the harness's fault.
    """
    functions = "\n\n".join(
        _extract_js_function(js_source, name) for name in _PARITY_FUNCTIONS
    )
    return functions + """

const cases = JSON.parse(process.argv[2]);
const results = cases.map(function (pair) {
  const width = pair[0];
  const height = pair[1];
  const simplified = simplifyRatio(width, height);
  const decimal = Math.round((width / height) * 100) / 100;
  const metadata = {
    width: width,
    height: height,
    aspectRatio: {
      width: simplified[0],
      height: simplified[1],
      decimal: decimal,
    },
  };
  return suggestDimensions(metadata, MIN_SIZE, MAX_SIZE);
});
console.log(JSON.stringify(results));
"""


class TestAlgorithmParity_ByExecution:
    """AC-137, by running both implementations over the same ratios.

    **Why the tie-break agrees.** At 1:1 every square from 10x10 to 30x30 has a
    ratio error of exactly 0.0 — a 21-way tie — so the answer is decided
    entirely by what each sort does with equal keys. Both keep insertion order:
    Python's ``list.sort`` is stable by guarantee, and ``Array.prototype.sort``
    has been stable **since ES2019**. Before that V8 used an unstable sort for
    arrays longer than 10 elements and this exact case would have diverged. The
    agreement is a property of both languages' sorts, not a coincidence of the
    numbers, and it is worth stating because nothing in either file says it.

    ``node`` is opportunistic: absent, these skip (G-1).
    """

    @staticmethod
    def _js_suggestions(tmp_path, cases):
        """Run metadata.js's algorithm over *cases*; skip if node is absent."""
        import subprocess

        js_file = (
            Path(__file__).parent.parent
            / "src"
            / "nonogram"
            / "web"
            / "static"
            / "metadata.js"
        )
        harness = tmp_path / "parity_harness.js"
        harness.write_text(
            f"const MIN_SIZE = {MIN_SIZE};\nconst MAX_SIZE = {MAX_SIZE};\n\n"
            + _parity_harness(js_file.read_text())
        )

        try:
            completed = subprocess.run(
                ["node", str(harness), json.dumps(cases)],
                capture_output=True,
                timeout=30,
                text=True,
            )
        except FileNotFoundError:
            pytest.skip("Node.js not available — the parity check needs it to run metadata.js")
        except subprocess.TimeoutExpired:
            pytest.fail("the JavaScript parity harness timed out")

        if completed.returncode != 0:
            pytest.fail(f"the parity harness failed to run:\n{completed.stderr}")
        return json.loads(completed.stdout)

    def test_the_harness_extracts_all_three_functions_with_real_bodies(self) -> None:
        """AC-5: an extractor that found nothing must not pass by comparing nothing."""
        js_file = (
            Path(__file__).parent.parent
            / "src"
            / "nonogram"
            / "web"
            / "static"
            / "metadata.js"
        )
        source = js_file.read_text()

        for name in _PARITY_FUNCTIONS:
            extracted = _extract_js_function(source, name)
            assert extracted.startswith(f"function {name}(")
            assert extracted.endswith("}")
            assert "return" in extracted, f"`{name}` came out without a body"
            assert extracted.count("{") == extracted.count("}"), name

        assert len(_RATIO_CORPUS) >= 12, "the parity corpus has shrunk"
        assert (1000, 1000) in _RATIO_CORPUS, "the 21-way tie case must stay in the corpus"

    def test_the_two_implementations_suggest_the_same_dimensions(self, tmp_path) -> None:
        """AC-1, AC-2, AC-4 — same three pairs, in the same order, per ratio."""
        from nonogram.web.metadata import (
            AspectRatio,
            ImageMetadata,
            suggest_dimensions,
        )

        cases = [list(pair) for pair in _RATIO_CORPUS]
        js_results = self._js_suggestions(tmp_path, cases)
        assert len(js_results) == len(_RATIO_CORPUS)

        disagreements = []
        for (width, height), from_js in zip(_RATIO_CORPUS, js_results):
            divisor = math.gcd(width, height)
            aspect = AspectRatio(
                width=width // divisor,
                height=height // divisor,
                decimal=round((width / height), 2),
            )
            from_python = [
                list(pair)
                for pair in suggest_dimensions(
                    ImageMetadata(width=width, height=height, aspect_ratio=aspect)
                )
            ]
            if from_python != from_js:
                disagreements.append(
                    f"  {width}x{height} (={aspect.width}:{aspect.height}): "
                    f"python={from_python} javascript={from_js}"
                )

        assert not disagreements, (
            "metadata.py and metadata.js suggest different dimensions (AC-137):\n"
            + "\n".join(disagreements)
        )

    def test_the_tie_break_agrees_where_every_candidate_ties(self, tmp_path) -> None:
        """AC-2, AC-6 — 1:1, where all 21 squares have ratio error exactly 0.0.

        Asserted separately from the corpus sweep because this is the case that
        distinguishes a stable sort from an unstable one: with an unstable sort
        the three returned squares would be whatever the sort happened to leave
        in front, and the two languages would not have to agree.
        """
        from nonogram.web.metadata import (
            AspectRatio,
            ImageMetadata,
            suggest_dimensions,
        )

        from_js = self._js_suggestions(tmp_path, [[1000, 1000]])[0]
        from_python = [
            list(pair)
            for pair in suggest_dimensions(
                ImageMetadata(
                    width=1000,
                    height=1000,
                    aspect_ratio=AspectRatio(width=1, height=1, decimal=1.0),
                )
            )
        ]

        assert from_python == from_js, (
            f"the 1:1 tie-break differs: python={from_python} javascript={from_js}"
        )
        assert from_python == [[MIN_SIZE, MIN_SIZE], [MIN_SIZE + 1, MIN_SIZE + 1],
                               [MIN_SIZE + 2, MIN_SIZE + 2]], (
            "both kept insertion order on a 21-way tie; if this changed, one of "
            f"the two sorts stopped being stable: {from_python}"
        )
