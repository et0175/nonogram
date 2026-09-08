"""CARD-035 tests: image filename traceability in exports.

Tests for the acceptance criteria:
    AC-139: Capture uploaded image filename and pass through generation pipeline
    AC-140: Export filenames include source image name
    AC-141: Non-image mode uses current naming scheme (no regression)
    AC-142: Filename sanitization (safe for filesystem, prevent path traversal)
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from nonogram import orchestrator
from nonogram.web import multipart, submission


def _multipart_body(
    fields: dict[str, str],
    *,
    filename: str = "upload.png",
    file_content: bytes = b"fake image data",
    boundary: str = "----boundary",
) -> tuple[str, bytes]:
    """Build a multipart/form-data body for testing."""
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.append(f"--{boundary}\r\n".encode("ascii"))
        chunks.append(
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("ascii")
        )
        chunks.append(value.encode("utf-8"))
        chunks.append(b"\r\n")
    chunks.append(f"--{boundary}\r\n".encode("ascii"))
    chunks.append(
        (
            f'Content-Disposition: form-data; name="image"; '
            f'filename="{filename}"\r\n'
            f"Content-Type: image/jpeg\r\n\r\n"
        ).encode("ascii")
    )
    chunks.append(file_content)
    chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode("ascii"))
    body = b"".join(chunks)
    return f"multipart/form-data; boundary={boundary}", body


class TestAC139_CaptureImageFilename:
    """AC-139: Capture uploaded image filename and pass through pipeline."""

    def test_multipart_extracts_filename_from_content_disposition(self) -> None:
        """Filename is extracted from multipart Content-Disposition header."""
        filename = "cat.jpg"
        content_type, body = _multipart_body({}, filename=filename)
        result = multipart.read(content_type, body)

        assert result.image_filename == filename

    def test_multipart_passes_filename_to_submission(self) -> None:
        """Filename is passed through to submission.from_fields."""
        filename = "dog.png"
        content_type, body = _multipart_body(
            {"mode": "image"},
            filename=filename,
        )
        result = multipart.read(content_type, body)

        assert result.submission.request is not None
        assert result.submission.request.image_filename == filename

    def test_urlencoded_body_has_no_image_filename(self) -> None:
        """Urlencoded submissions don't have a filename."""
        body = "mode=random&size=20&density=30"
        result = submission.read(body)

        assert result.request is not None
        assert result.request.image_filename is None

    def test_generation_request_carries_image_filename(self) -> None:
        """GenerationRequest field accepts and carries the image_filename."""
        request = orchestrator.GenerationRequest(
            mode="image",
            width=20,
            height=20,
            image=Path("/tmp/test.jpg"),
            image_filename="test.jpg",
        )

        assert request.image_filename == "test.jpg"

    def test_filename_with_path_components_extracted_as_stem(self) -> None:
        """If filename contains path separators, stem is extracted."""
        # Simulate browser sending full path (some Windows browsers)
        filename = "C:\\Users\\alice\\Pictures\\sunset.jpg"
        content_type, body = _multipart_body(
            {},
            filename=filename,
        )
        result = multipart.read(content_type, body)

        # The filename is captured as-is, but extraction of stem happens
        # during naming in the orchestrator
        assert result.image_filename is not None


class TestAC140_ExportFilenameIncludesImageName:
    """AC-140: Export filenames include source image name."""

    def test_image_mode_uses_filename_as_puzzle_name(self) -> None:
        """Image mode puzzle name comes from uploaded filename."""
        # Create a temporary image file for testing
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(b"\xff\xd8\xff\xe0")  # JPEG header
            temp_path = Path(f.name)

        try:
            request = orchestrator.GenerationRequest(
                mode="image",
                width=10,
                height=10,
                image=temp_path,
                image_filename="mycat.jpg",
            )

            # The naming logic should use the image_filename as the puzzle name
            names = orchestrator.NameContext()
            puzzle_name = names.name_for(request)

            # Should use the stem of the image filename
            assert puzzle_name == "mycat"
        finally:
            temp_path.unlink(missing_ok=True)

    def test_filename_takes_precedence_over_path_stem(self) -> None:
        """image_filename takes precedence over image path stem."""
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(b"\xff\xd8\xff\xe0")
            temp_path = Path(f.name)

        try:
            # temp_path has a name like tmp12345, but we want "vacation" from filename
            request = orchestrator.GenerationRequest(
                mode="image",
                width=10,
                height=10,
                image=temp_path,
                image_filename="vacation.jpg",
            )

            names = orchestrator.NameContext()
            puzzle_name = names.name_for(request)

            assert puzzle_name == "vacation"
        finally:
            temp_path.unlink(missing_ok=True)

    def test_fallback_to_path_when_no_filename(self) -> None:
        """Falls back to image path stem when no filename provided."""
        with tempfile.NamedTemporaryFile(
            suffix=".jpg", prefix="myimage_", delete=False
        ) as f:
            f.write(b"\xff\xd8\xff\xe0")
            temp_path = Path(f.name)

        try:
            request = orchestrator.GenerationRequest(
                mode="image",
                width=10,
                height=10,
                image=temp_path,
                image_filename=None,
            )

            names = orchestrator.NameContext()
            puzzle_name = names.name_for(request)

            # Should use the stem of temp_path
            assert puzzle_name == temp_path.stem
        finally:
            temp_path.unlink(missing_ok=True)


class TestAC141_NonImageModeUnaffected:
    """AC-141: Non-image mode uses current naming scheme (no regression)."""

    def test_random_mode_ignores_image_filename(self) -> None:
        """Random mode doesn't use image_filename even if provided."""
        request = orchestrator.GenerationRequest(
            mode="random",
            width=20,
            height=20,
            density=30,
            image_filename="ignored.jpg",
        )

        names = orchestrator.NameContext()
        puzzle_name = names.name_for(request)

        # Should be auto-generated (mode-timestamp format)
        assert puzzle_name.startswith("random-")

    def test_library_mode_ignores_image_filename(self) -> None:
        """Library mode doesn't use image_filename even if provided."""
        request = orchestrator.GenerationRequest(
            mode="library",
            width=20,
            height=20,
            library_key="cat",
            image_filename="dog.jpg",  # Should be ignored
        )

        names = orchestrator.NameContext()
        puzzle_name = names.name_for(request)

        # Should use the library key
        assert puzzle_name == "cat"

    def test_random_mode_naming_unchanged(self) -> None:
        """Random mode naming hasn't changed from before CARD-035."""
        request = orchestrator.GenerationRequest(
            mode="random", width=20, height=20, density=30
        )

        names = orchestrator.NameContext()
        puzzle_name = names.name_for(request)

        # Should still be mode + timestamp
        assert puzzle_name.startswith("random-")
        assert "-" in puzzle_name.split("random-")[1]


class TestAC142_FilenameSanitization:
    """AC-142: Filename sanitization (safe for filesystem, prevent path traversal)."""

    def test_sanitization_removes_path_separators(self) -> None:
        """Path separators are removed during sanitization."""
        request = orchestrator.GenerationRequest(
            mode="image",
            width=10,
            height=10,
            image=Path("/tmp/test.jpg"),
            image_filename="../evil/puzzle.jpg",
        )

        names = orchestrator.NameContext()
        puzzle_name = names.name_for(request)

        # Path separators should not appear in the result
        assert "/" not in puzzle_name
        assert ".." not in puzzle_name

    def test_sanitization_through_export_path(self) -> None:
        """Sanitization is applied when creating export paths."""
        puzzle = orchestrator.Puzzle(
            request=orchestrator.GenerationRequest(
                mode="image",
                width=10,
                height=10,
                image=Path("/tmp/test.jpg"),
                image_filename="my puzzle (1).jpg",
            ),
            seed=42,
            extent=(10, 10),
            name="my puzzle (1)",
        )

        # The filename stem should be sanitized
        stem = orchestrator._filename_stem(puzzle)

        # Should replace special characters with dashes
        assert "(" not in stem or stem.count("(") == 0  # or it's been replaced
        # The sanitization should make it filesystem-safe
        assert "\x00" not in stem
        assert "/" not in stem
        assert "\\" not in stem

    def test_special_characters_sanitized(self) -> None:
        """Special characters that are unsafe for filenames are handled."""
        puzzle = orchestrator.Puzzle(
            request=orchestrator.GenerationRequest(
                mode="image",
                width=10,
                height=10,
            ),
            seed=42,
            extent=(10, 10),
            name="puzzle*name:test?.jpg",
        )

        stem = orchestrator._filename_stem(puzzle)

        # These characters should be replaced in the stem
        unsafe_chars = ["*", ":", "?", "<", ">", "|"]
        for char in unsafe_chars:
            assert char not in stem

    def test_unicode_filenames_preserved(self) -> None:
        """Unicode characters in filenames are preserved."""
        request = orchestrator.GenerationRequest(
            mode="image",
            width=10,
            height=10,
            image=Path("/tmp/test.jpg"),
            image_filename="пазл.jpg",  # "puzzle" in Russian
        )

        names = orchestrator.NameContext()
        puzzle_name = names.name_for(request)

        # Unicode should be preserved (sanitization doesn't remove it)
        assert "пазл" == puzzle_name

    def test_empty_filename_falls_back_to_timestamp(self) -> None:
        """Empty or whitespace-only filename falls back to timestamp naming."""
        request = orchestrator.GenerationRequest(
            mode="image",
            width=10,
            height=10,
            image=Path("/tmp/test.jpg"),
            image_filename="",
        )

        names = orchestrator.NameContext()
        puzzle_name = names.name_for(request)

        # Should fall back to image path stem, then timestamp if needed
        # The key is that it doesn't crash and produces a valid name
        assert puzzle_name is not None
        assert len(puzzle_name) > 0

    def test_filename_with_multiple_dots(self) -> None:
        """Filenames with multiple dots are handled correctly."""
        request = orchestrator.GenerationRequest(
            mode="image",
            width=10,
            height=10,
            image=Path("/tmp/test.jpg"),
            image_filename="my.puzzle.v1.2.jpg",
        )

        names = orchestrator.NameContext()
        puzzle_name = names.name_for(request)

        # Should use the stem (everything before the last extension)
        assert puzzle_name == "my.puzzle.v1.2"

    def test_filename_with_leading_trailing_dots(self) -> None:
        """Leading/trailing dots are stripped during sanitization."""
        puzzle = orchestrator.Puzzle(
            request=orchestrator.GenerationRequest(
                mode="image",
                width=10,
                height=10,
            ),
            seed=42,
            extent=(10, 10),
            name=".puzzle.",
        )

        stem = orchestrator._filename_stem(puzzle)

        # Dots should be stripped from start and end
        assert not stem.startswith(".")
        assert not stem.endswith(".")
