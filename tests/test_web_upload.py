"""COMP-008 tests: the multipart upload branch (CARD-021).

    AC-049/upload           TestWebUpload_ConvertsUploadedImageThroughSamePipeline
    AC-050/upload           TestWebUpload_RejectsUndecodableUploadLikeCLI
    AC-boundary/multipart   TestWebUpload_ParsesBoundaryCollidingBodyExactly

These three reuse the running-server helpers ``tests.test_web_server`` built
for AC-052's socket tests and the page-reading helpers
``tests.test_web_submission`` built for its own AC-049/AC-050 — the same
reasons those modules give for importing rather than re-writing them apply
here unchanged: two copies of a request or assertion helper drift, and a
drifted copy is how a test starts asserting something about a request the
server never received.

What is new here is a *multipart* request builder, because none of the
existing helpers can express one: ``tests.test_web_submission._submit`` always
posts ``application/x-www-form-urlencoded`` (that is the whole of what CARD-020
needed), and this module's own upload-only fields (a file's bytes, a boundary)
have nowhere to go in it. :func:`_multipart_request` builds the body by hand,
byte for byte, rather than through the standard library's own
``email.generator`` — partly because the point of AC-boundary/multipart is to
control exactly which bytes land where (a boundary sequence embedded inside
the file part's own content, which a cooperative generator would go out of its
way not to produce), and partly so this test suite does not lean on the same
``email`` machinery ``nonogram.web.multipart`` is under test for building the
request it is about to parse.
"""

from __future__ import annotations

import html
import io
import json
import re
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest
from PIL import Image
from PIL.PngImagePlugin import PngInfo

from nonogram import web
from nonogram.web import multipart, pages, server

from tests import test_web_server as web_tests
from tests.test_web_submission import (
    _cli_error_message,
    _no_files_under,
    _outcome,
    _paths_on,
)

FIXTURES = Path(__file__).parent / "fixtures"
CORRUPT = FIXTURES / "corrupt.png"

#: The size AC-049/upload names.
_SIZE = 20

#: A boundary distinctive enough that no incidental byte sequence in a small
#: generated PNG could collide with it by accident — only the collision tests
#: below insert it into a part's content on purpose.
_BOUNDARY = "----NonogramCARD021TestBoundary"


@pytest.fixture
def running_server() -> Iterator[server.LoopbackHTTPServer]:
    """The server under test, on a kernel-chosen port.

    A local copy of the sibling modules' fixture, for the reason each of them
    already gives: a fixture is not importable as a fixture, only the helper
    it wraps is.
    """
    with web_tests._running(web.create_server(0)) as running:
        yield running


def _png_bytes(size: tuple[int, int] = (40, 40), fill: int = 0) -> bytes:
    """A tiny, fully-inked (or fully blank) greyscale PNG — square, so it fits
    a square grid request without tripping CON-012's aspect-ratio guard."""
    buffer = io.BytesIO()
    Image.new("L", size, fill).save(buffer, format="PNG")
    return buffer.getvalue()


def _png_bytes_containing(marker: bytes, size: tuple[int, int] = (40, 40)) -> bytes:
    """A real, decodable PNG whose encoded bytes also contain ``marker``.

    Stashed in a ``tEXt`` ancillary chunk (via Pillow's own ``PngInfo``) rather
    than spliced into the pixel data, so the file stays a valid image and this
    helper never has to know how PNG's own compressed data is laid out. Used to
    prove AC-boundary/multipart's guarantee holds for a request that also
    reaches the full pipeline (:func:`_png_bytes` alone would not contain the
    boundary — this is the version that does).
    """
    info = PngInfo()
    info.add_text("Comment", marker.decode("latin-1") * 4)
    buffer = io.BytesIO()
    Image.new("L", size, 0).save(buffer, format="PNG", pnginfo=info)
    content = buffer.getvalue()
    assert marker in content, "the marker did not survive PNG encoding"
    return content


def _multipart_request(
    fields: dict[str, str | list[str]],
    *,
    file_field: str = "image",
    filename: str = "upload.png",
    file_content: bytes,
    file_content_type: str = "image/png",
    boundary: str = _BOUNDARY,
) -> tuple[str, bytes]:
    """Build one ``multipart/form-data`` request by hand.

    Returns ``(content_type_header_value, body)`` — the two pieces a caller
    needs to hand to ``tests.test_web_server._request`` or to
    ``nonogram.web.multipart.read`` directly. Field order follows the ``dict``
    given, with the file part always last, mirroring how a browser lays out a
    form whose file control is rendered after the other fields
    (``nonogram.web.pages.FORM_PAGE``).
    """
    chunks: list[bytes] = []
    for name, value in fields.items():
        for one in value if isinstance(value, list) else [value]:
            chunks.append(f"--{boundary}\r\n".encode("ascii"))
            chunks.append(
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("ascii")
            )
            chunks.append(one.encode("utf-8"))
            chunks.append(b"\r\n")
    chunks.append(f"--{boundary}\r\n".encode("ascii"))
    chunks.append(
        (
            f'Content-Disposition: form-data; name="{file_field}"; '
            f'filename="{filename}"\r\n'
            f"Content-Type: {file_content_type}\r\n\r\n"
        ).encode("ascii")
    )
    chunks.append(file_content)
    chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode("ascii"))
    body = b"".join(chunks)
    return f"multipart/form-data; boundary={boundary}", body


def _submit_multipart(
    port: int, fields: dict[str, str | list[str]], **kwargs: object
) -> web_tests._Response:
    """Post a multipart request to the form's action, exactly as a browser
    would once ``nonogram.web.pages.FORM_PAGE`` carries a file control."""
    content_type, body = _multipart_request(fields, **kwargs)  # type: ignore[arg-type]
    return web_tests._request(
        port,
        method="POST",
        path=pages.FORM_ACTION,
        headers={"Content-Type": content_type},
        body=body,
    )


def _uploaded_temp_files() -> set[str]:
    """The names of every temp file this package's upload path has left
    behind — used to show CARD-021's step 5 (cleanup) actually happens rather
    than merely trusting the ``finally`` reads correctly."""
    return {
        entry.name
        for entry in Path(tempfile.gettempdir()).glob("nonogram-upload-*")
    }


# --------------------------------------------------------------------------
# AC-049/upload — the happy path
# --------------------------------------------------------------------------


class TestWebUpload_ConvertsUploadedImageThroughSamePipeline:
    """*Given* a ``multipart/form-data`` submission carrying a real PNG and
    size 20x20, *when* the form is submitted, *then* the upload is written to
    a temp file, passed to the same image sourcing path the CLI's ``--image``
    uses, and the page reports success with the written file paths."""

    def test_the_page_reports_success_and_names_the_written_file(
        self, running_server: server.LoopbackHTTPServer, tmp_path: Path
    ) -> None:
        before = _uploaded_temp_files()

        response = _submit_multipart(
            running_server.server_port,
            {
                "mode": "image",
                "size": f"{_SIZE}x{_SIZE}",
                "export_formats": ["json"],
                "out": str(tmp_path),
            },
            file_content=_png_bytes(),
        )

        assert response.status == 200
        assert response.headers["Content-Type"] == "text/html; charset=utf-8"
        assert _outcome(response.body) == pages.SUCCESS
        listed = _paths_on(response.body)
        assert len(listed) == 1
        written = Path(listed[0])
        assert written.is_file()
        assert written.suffix == ".json"

        # Step 5: the temp file the upload landed in is gone once the run
        # that consumed it is over, and nothing else's temp file was touched.
        assert _uploaded_temp_files() == before

    def test_the_grid_the_page_reports_came_from_the_upload_not_a_default(
        self, running_server: server.LoopbackHTTPServer, tmp_path: Path
    ) -> None:
        """A fully-inked source produces an all-filled grid; a blank one
        produces an all-empty grid. Submitting both and reading the exported
        JSON's solution back shows the *uploaded bytes* drove the puzzle,
        rather than the page merely reporting success on any input."""
        inked = _submit_multipart(
            running_server.server_port,
            {
                "mode": "image",
                "size": f"{_SIZE}x{_SIZE}",
                "export_formats": ["json"],
                "out": str(tmp_path / "inked"),
            },
            file_content=_png_bytes(fill=0),
        )
        blank = _submit_multipart(
            running_server.server_port,
            {
                "mode": "image",
                "size": f"{_SIZE}x{_SIZE}",
                "export_formats": ["json"],
                "out": str(tmp_path / "blank"),
            },
            file_content=_png_bytes(fill=255),
        )

        assert _outcome(inked.body) == pages.SUCCESS
        assert _outcome(blank.body) == pages.SUCCESS
        inked_grid = json.loads(Path(_paths_on(inked.body)[0]).read_text())["grid"]
        blank_grid = json.loads(Path(_paths_on(blank.body)[0]).read_text())["grid"]

        assert all(cell for row in inked_grid for cell in row)
        assert not any(cell for row in blank_grid for cell in row)


# --------------------------------------------------------------------------
# AC-050/upload — the negative path
# --------------------------------------------------------------------------


class TestWebUpload_RejectsUndecodableUploadLikeCLI:
    """*Given* a ``multipart/form-data`` submission whose uploaded file is
    not a decodable image, *when* the form is submitted, *then* the same
    ``UnreadableImage`` domain error the CLI would raise is surfaced as a
    structured failure and no files are written."""

    def test_the_page_reports_the_same_failure_the_cli_reports(
        self,
        running_server: server.LoopbackHTTPServer,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        corrupt_bytes = CORRUPT.read_bytes()
        before = _uploaded_temp_files()
        out = tmp_path / "web-out"

        response = _submit_multipart(
            running_server.server_port,
            {
                "mode": "image",
                "size": f"{_SIZE}x{_SIZE}",
                "export_formats": ["json"],
                "out": str(out),
            },
            file_content=corrupt_bytes,
            filename="corrupt.png",
        )

        assert response.status == 200
        assert _outcome(response.body) == pages.FAILURE
        (web_message,) = re.findall(rb"<li>([^<]+)</li>", response.body)
        web_message = html.unescape(web_message.decode())

        # No files were written for this run (AC-050/upload) — the directory
        # a successful run would have populated stays untouched or absent.
        assert _no_files_under(out)

        # Cleanup happens on the failure path too (the card's step 5).
        assert _uploaded_temp_files() == before

        # "The same domain error the CLI would raise": both messages are
        # UnreadableImage's own shape, and agree on everything but the path
        # the picture happened to land at — the web adapter's is a temp file
        # CARD-021 created, the CLI's is the fixture path given directly.
        cli_copy = tmp_path / "corrupt-for-cli.png"
        cli_copy.write_bytes(corrupt_bytes)
        cli_message = _cli_error_message(
            [
                "generate",
                "--mode", "image",
                "--image", str(cli_copy),
                "--size", f"{_SIZE}x{_SIZE}",
            ],
            capsys,
        )

        # Both messages are ``UnreadableImage``'s exact template — "cannot
        # read image '<path>': cannot identify image file '<path>'" — with the
        # *same* path repeated in both halves of each message. Comparing the
        # two messages for literal equality is not possible (each names its
        # own path: a temp file CARD-021 created for the web adapter, the
        # fixture copy given directly to the CLI), so what is asserted is the
        # template itself, once per message, which is "the same domain error"
        # actually means for a message that is allowed to differ only by path.
        _shape = re.compile(r"^cannot read image '(?P<path>.+)': cannot identify image file '(?P=path)'$")
        assert _shape.match(web_message), web_message
        assert _shape.match(cli_message), cli_message


# --------------------------------------------------------------------------
# AC-boundary/multipart
# --------------------------------------------------------------------------


class TestWebUpload_ParsesBoundaryCollidingBodyExactly:
    """*Given* a multipart body whose part boundary sequence also occurs
    inside the uploaded image's bytes, *when* the body is parsed, *then* the
    extracted file content is byte-for-byte identical to the uploaded file."""

    def test_every_byte_value_and_the_boundary_itself_survive_parsing(self) -> None:
        """The adversarial case, checked directly against the parser: content
        carrying every possible byte value (0..255) *and* the literal boundary
        sequence embedded mid-stream — not at the start of a line, so a
        correct parser must not mistake it for a delimiter."""
        marker = _BOUNDARY.encode("ascii")
        content = (
            bytes(range(256)) * 8
            + b"before"
            + marker
            + b"after"
            + bytes(range(255, -1, -1)) * 8
        )
        content_type, body = _multipart_request(
            {"mode": "image"}, file_content=content, boundary=_BOUNDARY
        )

        result = multipart.read(content_type, body)

        try:
            assert result.image_path is not None
            assert result.image_path.read_bytes() == content
        finally:
            if result.image_path is not None:
                result.image_path.unlink(missing_ok=True)

    def test_a_boundary_colliding_upload_still_converts_through_the_full_pipeline(
        self, running_server: server.LoopbackHTTPServer, tmp_path: Path
    ) -> None:
        """The same guarantee, exercised over a real socket with a file that
        also has to survive Pillow's own decoding — so AC-boundary/multipart
        and AC-049/upload both hold for the same request at once."""
        marker = _BOUNDARY.encode("ascii")
        content = _png_bytes_containing(marker)

        response = _submit_multipart(
            running_server.server_port,
            {
                "mode": "image",
                "size": f"{_SIZE}x{_SIZE}",
                "export_formats": ["json"],
                "out": str(tmp_path),
            },
            file_content=content,
            boundary=_BOUNDARY,
        )

        assert response.status == 200
        assert _outcome(response.body) == pages.SUCCESS
        listed = _paths_on(response.body)
        assert len(listed) == 1
        assert Path(listed[0]).is_file()