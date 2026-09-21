"""CARD-044 — after a submission you can see the picture you are retrying with.

    AC-163  the preview appears on the page a submission renders
    AC-164  choosing a new file replaces it
    AC-165  (inverted) a failure KEEPS the preview, because it keeps the picture
    AC-166  choosing a new file clears the previous result message

Two things had to be re-read before any of this could be written.

**The result page had no preview markup at all.** `#image-preview-container`
and its siblings were in `FORM_PAGE` only; `form_with_result` — the page every
submission renders — did not carry them, so `metadata.js` looked up an element
that was not there. The card blamed a missing change event; that was half of
it.

**AC-165 asked for the opposite of what is now right.** It wanted the preview
cleared when generation fails. That was correct while a failed submit destroyed
the upload: the preview would have been showing a picture the server no longer
had. CARD-037 keeps the picture for the retry, so clearing it would show an
error and no picture while the file waits in the store. The criterion is
inverted here, and the card records why.

The browser holds an opaque token, never a path, so the picture comes back
through `GET /upload/<token>` — which resolves through the same store and
answers for nothing it did not mint.
"""

from __future__ import annotations

import re

import pytest

from nonogram.web import pages, uploads
from tests.test_web_submission import _outcome
from tests.test_web_upload import (
    _png_bytes,
    _submit_multipart,
    running_server,  # noqa: F401 — fixture
)
from tests import test_web_server as web_tests


def _token_on(body: bytes) -> str | None:
    match = re.search(rb'name="upload_token"\s+value="([^"]*)"', body)
    return match.group(1).decode() if match else None


def _preview_src(body: bytes) -> str | None:
    match = re.search(rb'id="image-preview"[^>]*\ssrc="([^"]*)"', body)
    return match.group(1).decode() if match else None


@pytest.fixture(autouse=True)
def _clean_store():
    uploads.clear()
    yield
    uploads.clear()


def _failed_submit(port):
    """A picture the server keeps, refused for a reason a retry could fix."""
    return _submit_multipart(
        port, {"size": "5", "export_formats": ["json"]}, file_content=_png_bytes()
    )


# --------------------------------------------------------------------------
# AC-163 — the preview is on the page, pointing at the retained upload
# --------------------------------------------------------------------------


def test_the_result_page_carries_the_preview_markup(running_server):
    """The half the card missed: there was nowhere for a preview to appear."""
    response = _failed_submit(running_server.server_port)

    assert b'id="image-preview-container"' in response.body
    assert b'id="image-preview"' in response.body


def test_the_preview_points_at_the_retained_upload(running_server):
    response = _failed_submit(running_server.server_port)

    token = _token_on(response.body)
    assert token
    assert _preview_src(response.body) == f"/upload/{token}"


def test_the_route_serves_the_picture_that_was_uploaded(running_server):
    sent = _png_bytes()
    response = _failed_submit(running_server.server_port)
    token = _token_on(response.body)

    served = web_tests._request(running_server.server_port, path=f"/upload/{token}")

    assert served.status == 200
    assert served.body == sent
    assert served.headers["Content-Type"] == "image/png"


def test_a_fresh_form_has_no_preview_source(running_server):
    """`GET /` holds nothing, so its preview starts empty as it always did."""
    response = web_tests._request(running_server.server_port, path="/")

    assert b'id="image-preview-container"' in response.body
    assert not _preview_src(response.body)


# --------------------------------------------------------------------------
# AC-165, inverted — the preview outlives a failure, because the picture does
# --------------------------------------------------------------------------


def test_a_second_failure_still_shows_the_picture(running_server):
    first = _failed_submit(running_server.server_port)
    token = _token_on(first.body)

    second = _submit_multipart(
        running_server.server_port,
        {"size": "7", "export_formats": ["json"], "upload_token": token},
        filename="",
        file_content=b"",
    )

    assert _outcome(second.body) == pages.FAILURE
    assert _preview_src(second.body) == f"/upload/{token}", "the retry lost its picture"


def test_a_success_leaves_no_preview_behind(running_server, tmp_path):
    """The retention ends on success, so the picture must stop being served."""
    first = _failed_submit(running_server.server_port)
    token = _token_on(first.body)

    second = _submit_multipart(
        running_server.server_port,
        {"size": "20", "export_formats": ["json"], "out": str(tmp_path),
         "upload_token": token},
        filename="",
        file_content=b"",
    )

    assert _outcome(second.body) == pages.SUCCESS
    assert not _preview_src(second.body)
    served = web_tests._request(running_server.server_port, path=f"/upload/{token}")
    assert served.status == 404


def test_an_undecodable_upload_leaves_no_preview(running_server):
    """CARD-037 releases a picture that can never work; the preview goes too."""
    response = _submit_multipart(
        running_server.server_port,
        {"size": "20", "export_formats": ["json"]},
        file_content=b"not an image at all",
    )

    assert _outcome(response.body) == pages.FAILURE
    assert not _preview_src(response.body)


# --------------------------------------------------------------------------
# the route answers for nothing it did not mint
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "suffix",
    [
        "not-a-real-token",
        "../../etc/passwd",
        "..%2f..%2fetc%2fpasswd",
        "",
    ],
)
def test_the_route_refuses_anything_it_did_not_mint(running_server, suffix):
    served = web_tests._request(running_server.server_port, path=f"/upload/{suffix}")

    assert served.status == 404, served.status


def test_the_route_refuses_a_path_it_was_handed(running_server, tmp_path):
    """The CARD-037 property, restated at the new surface.

    A readable picture on disk, named by path where a token belongs. The store
    is not a path lookup, so this is a token nobody minted.
    """
    planted = tmp_path / "readable.png"
    planted.write_bytes(_png_bytes())

    served = web_tests._request(
        running_server.server_port, path=f"/upload/{planted}"
    )

    assert served.status == 404
    assert served.body != planted.read_bytes()
