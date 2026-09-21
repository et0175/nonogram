"""CARD-037 — a rejected submission keeps its picture, without naming a path.

    AC-1  a failed generation returns a page carrying a token for the upload
    AC-2  resubmitting with that token and no file re-uses the same picture
    AC-3  a success releases the token and deletes the file
    AC-4  a token the server never minted is ignored
    AC-5  the store is bounded, and evicting deletes the file

Today a failed submit deletes the upload: the handler's ``finally`` unlinks it
whatever happened, so "fix the size and try again" means choosing the file
again. That is the whole of this card.

The design constraint is the interesting half. The work salvaged from the
2026-09-04 branch (`meta/ops/CARD-037-uncommitted-work-20260921.patch`) put the
**filesystem path** in a hidden form field and read it back:

    persisted_path = Path(fields["persisted_image_path"][0])
    if persisted_path.exists() and persisted_path.is_file():
        image_path = persisted_path

`fields` is whatever the client sent, so that accepts any path on the server and
opens it as a picture. This adapter refuses that elsewhere on purpose — a
urlencoded ``image=<path>`` is not read as a picture, which CARD-032's AC-130
test pins — so the retry uses an **opaque token** instead. The server maps a
random id to the file it already holds; the client never learns a path and
cannot supply one. ``test_a_path_submitted_as_a_token_is_not_opened`` is the
test that would fail if anyone reverted to the salvaged design.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from nonogram.web import pages, server, uploads
from tests.test_web_submission import _outcome
from tests.test_web_upload import (
    _png_bytes,
    _submit_multipart,
    _uploaded_temp_files,
    running_server,  # noqa: F401 — fixture
)


def _token_on(body: bytes) -> str | None:
    """The upload token the page carries, if any."""
    match = re.search(rb'name="upload_token"\s+value="([^"]*)"', body)
    return match.group(1).decode() if match else None


@pytest.fixture(autouse=True)
def _clean_store():
    """Each test starts with an empty store and leaves nothing behind."""
    uploads.clear()
    yield
    uploads.clear()


# --------------------------------------------------------------------------
# AC-1 / AC-2 — the retry
# --------------------------------------------------------------------------


def test_a_failed_submission_returns_a_token_for_its_upload(running_server):
    """A size the domain refuses, with a picture that was perfectly good."""
    response = _submit_multipart(
        running_server.server_port,
        {"size": "5", "export_formats": ["json"]},
        file_content=_png_bytes(),
    )

    assert _outcome(response.body) == pages.FAILURE
    assert _token_on(response.body), "the page offers no way to keep the upload"


def test_resubmitting_with_the_token_re_uses_the_picture(running_server, tmp_path):
    """AC-2: the second attempt carries no file, and still generates."""
    first = _submit_multipart(
        running_server.server_port,
        {"size": "5", "export_formats": ["json"]},
        file_content=_png_bytes(),
    )
    token = _token_on(first.body)

    second = _submit_multipart(
        running_server.server_port,
        {"size": "20", "export_formats": ["json"], "out": str(tmp_path),
         "upload_token": token},
        # No new file: a browser submitting an untouched file input sends an
        # empty part with an empty *filename*, which is what makes it "nothing
        # chosen" rather than a zero-byte upload.
        filename="",
        file_content=b"",
    )

    assert _outcome(second.body) == pages.SUCCESS
    assert list(tmp_path.iterdir()), "nothing was written"


def test_a_second_failure_keeps_the_picture_available(running_server):
    """Two bad sizes in a row must not cost the upload."""
    first = _submit_multipart(
        running_server.server_port,
        {"size": "5", "export_formats": ["json"]},
        file_content=_png_bytes(),
    )
    token = _token_on(first.body)

    second = _submit_multipart(
        running_server.server_port,
        {"size": "7", "export_formats": ["json"], "upload_token": token},
        filename="",
        file_content=b"",
    )

    assert _outcome(second.body) == pages.FAILURE
    assert _token_on(second.body) == token, "the token changed under a retry"
    assert uploads.resolve(token) is not None


# --------------------------------------------------------------------------
# AC-3 — a success ends the retention
# --------------------------------------------------------------------------


def test_a_success_releases_the_token_and_deletes_the_file(running_server, tmp_path):
    before = _uploaded_temp_files()
    first = _submit_multipart(
        running_server.server_port,
        {"size": "5", "export_formats": ["json"]},
        file_content=_png_bytes(),
    )
    token = _token_on(first.body)
    retained = uploads.resolve(token)
    assert retained is not None and retained.exists()

    _submit_multipart(
        running_server.server_port,
        {"size": "20", "export_formats": ["json"], "out": str(tmp_path),
         "upload_token": token},
        filename="",
        file_content=b"",
    )

    assert uploads.resolve(token) is None, "the token outlived its upload"
    assert not retained.exists(), "the temp file was left behind"
    assert _uploaded_temp_files() <= before


def test_a_plain_success_leaves_nothing_retained(running_server, tmp_path):
    """The ordinary path is unchanged: upload, generate, nothing kept."""
    before = _uploaded_temp_files()

    response = _submit_multipart(
        running_server.server_port,
        {"size": "20", "export_formats": ["json"], "out": str(tmp_path)},
        file_content=_png_bytes(),
    )

    assert _outcome(response.body) == pages.SUCCESS
    assert _uploaded_temp_files() <= before


# --------------------------------------------------------------------------
# AC-4 — the reason this is a token and not a path
# --------------------------------------------------------------------------


def test_a_token_the_server_never_minted_is_ignored(running_server):
    response = _submit_multipart(
        running_server.server_port,
        {"size": "20", "export_formats": ["json"], "upload_token": "not-a-real-token"},
        filename="",
        file_content=b"",
    )

    assert _outcome(response.body) == pages.FAILURE
    assert b"image" in response.body.lower()


def test_a_path_submitted_as_a_token_is_not_opened(running_server, tmp_path):
    """The salvaged design's hole, asserted shut.

    A real, readable image on disk, named the way the 2026-09-04 patch would
    have accepted it. The token store is not a path lookup, so it resolves to
    nothing and the request fails for want of a picture.
    """
    planted = tmp_path / "readable.png"
    planted.write_bytes(_png_bytes())

    response = _submit_multipart(
        running_server.server_port,
        {"size": "20", "export_formats": ["json"], "upload_token": str(planted)},
        filename="",
        file_content=b"",
    )

    assert _outcome(response.body) == pages.FAILURE
    assert planted.exists(), "the request reached a file it was handed by name"


def test_resolve_refuses_anything_it_did_not_mint(tmp_path):
    """The store's own contract, away from the server."""
    real = tmp_path / "x.png"
    real.write_bytes(_png_bytes())

    assert uploads.resolve(str(real)) is None
    assert uploads.resolve("") is None
    assert uploads.resolve(None) is None


def test_a_token_is_not_guessable_from_the_path(tmp_path):
    real = tmp_path / "x.png"
    real.write_bytes(_png_bytes())

    token = uploads.retain(real)

    assert len(token) >= 16
    assert real.name not in token and str(real) not in token
    assert uploads.retain(real) != token, "two retentions shared a token"


# --------------------------------------------------------------------------
# AC-5 — the store cannot grow without bound
# --------------------------------------------------------------------------


def test_the_store_evicts_the_oldest_and_deletes_its_file(tmp_path):
    paths = []
    tokens = []
    for n in range(uploads.MAX_RETAINED + 2):
        p = tmp_path / f"{n}.png"
        p.write_bytes(_png_bytes())
        paths.append(p)
        tokens.append(uploads.retain(p))

    assert uploads.resolve(tokens[0]) is None, "the oldest was kept"
    assert not paths[0].exists(), "an evicted upload was left on disk"
    assert uploads.resolve(tokens[-1]) is not None


def test_release_is_safe_to_call_twice(tmp_path):
    p = tmp_path / "x.png"
    p.write_bytes(_png_bytes())
    token = uploads.retain(p)

    uploads.release(token)
    uploads.release(token)

    assert uploads.resolve(token) is None
    assert not p.exists()


def test_resolve_forgets_a_file_that_vanished(tmp_path):
    """A temp sweeper, or a reboot, must not make the store lie."""
    p = tmp_path / "x.png"
    p.write_bytes(_png_bytes())
    token = uploads.retain(p)

    p.unlink()

    assert uploads.resolve(token) is None
