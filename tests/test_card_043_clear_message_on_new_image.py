"""CARD-043 — choosing a different picture clears the last result.

    AC-161  selecting a new image clears the message that is on screen
    AC-162  the next submission shows only its own result

The moment this is about is *before* the submit. CARD-038 already empties the
result container when the form is submitted::

    form.addEventListener('submit', function() {
      document.querySelector('[data-result-container]').innerHTML = '';
    });

That fires when Generate is finally pressed. This card is the moment the user
picks a different picture and is still deciding what else to change — the stale
"nonogram refused this request" should not still be sitting there while they
choose.

What can be tested without a browser
------------------------------------
The behaviour is a listener, and this project runs no JavaScript (ADR-0006's
baseline has no engine; `node --check` parses and is opportunistic — CARD-105
covers making that real). So these tests assert the two things that are
checkable from Python and would each break the feature if wrong:

* the **server** ships a page whose result container is where the script
  expects it, on both the fresh form and the page a submission renders; and
* the **script** wires the clear into the file-change path rather than only
  into submit.

The second is a source assertion, which CARD-034 deleted three of for being
unfailable. This one is not: it names the function and the container together,
so removing either — which is exactly how the feature would regress — fails it.
The honest limit is that it cannot prove the listener *fires*, and the card
says so rather than implying otherwise.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from nonogram.web import pages
from tests.test_web_submission import _outcome
from tests.test_web_upload import (
    _png_bytes,
    _submit_multipart,
    running_server,  # noqa: F401 — fixture
)
from tests import test_web_server as web_tests


def _script() -> str:
    return (
        Path(__file__).parent.parent
        / "src" / "nonogram" / "web" / "static" / "metadata.js"
    ).read_text()


# --------------------------------------------------------------------------
# AC-161 — the container is there, and the script clears it on file change
# --------------------------------------------------------------------------


def test_both_pages_carry_the_result_container(running_server, tmp_path):
    """The script clears by selector; if the page stops carrying it, it stops.

    Asserted on the page a submission renders as well as the fresh form,
    because the stale message this card removes only ever exists on the former.
    """
    # The rendered attribute, not the bare name: `[data-result-container]`
    # also appears in the page's own inline script, so asserting the name
    # alone passes even when the container itself has gone (mutation check,
    # 2026-09-21).
    fresh = web_tests._request(running_server.server_port, path="/")
    assert b'data-result-container="true"' in fresh.body

    after = _submit_multipart(
        running_server.server_port,
        {"size": "5", "export_formats": ["json"]},
        file_content=_png_bytes(),
    )
    assert _outcome(after.body) == pages.FAILURE
    assert b'data-result-container="true"' in after.body


def test_the_script_clears_the_result_when_a_file_is_chosen():
    """AC-161 — the call is present at both places a file can be chosen.

    The script registers **two** change listeners: one for the no-File-API
    fallback and one for the real path. Both must clear, because both are
    "the user picked a different picture".

    This counts call sites rather than parsing handler bodies, and the reason
    is worth recording: the obvious regex — match each
    ``addEventListener("change", function() { … })`` and look inside — matches
    the two handlers as a *single* span, because the first one's closing brace
    is indented differently from the pattern's. It therefore reported one
    handler containing both bodies, and a mutant that removed the call from
    the path that actually runs still passed. A count cannot be fooled that
    way. It also cannot prove the listener *fires*; that needs the harness
    CARD-105 is about.
    """
    source = _script()

    assert "function clearResultMessage(" in source
    assert "[data-result-container]" in source
    assert source.count("clearResultMessage();") == 2, (
        "expected the clear at both change listeners (the File API path and "
        f"the fallback), found {source.count('clearResultMessage();')}"
    )


def test_clearing_the_message_also_refreshes_the_picture():
    """The message and the preview must not fall out of step.

    Since CARD-037 a failed submission keeps its picture and CARD-044 shows it.
    Removing the text while the previous picture stays on screen would be
    worse than leaving both, so the change path does the two together.
    """
    source = _script()

    change_handlers = re.findall(
        r'addEventListener\("change",\s*function\s*\([^)]*\)\s*\{(.*?)\n      \}\)',
        source,
        re.S,
    )
    clearing = [b for b in change_handlers if "clearResultMessage()" in b]
    assert clearing, "nothing clears the message on change"
    assert all(
        "clearMetadata()" in body or "displayImagePreview" in body
        for body in clearing
    ), "the message is cleared without the picture being dealt with"


def test_the_clear_is_guarded_when_the_container_is_absent():
    """G-2's shape: no JavaScript error when the element is not there.

    `GET /` and the result page both carry it today, but a page that did not
    must not throw — the script runs on every page that loads it.
    """
    source = _script()
    body = source[source.index("function clearResultMessage("):]
    body = body[: body.index("\n  }")]

    assert "if (" in body, "the container is used without being checked for"


# --------------------------------------------------------------------------
# AC-162 — the next submission shows only its own result
# --------------------------------------------------------------------------


def test_a_second_submission_carries_only_its_own_result(running_server, tmp_path):
    """Server-side half of AC-162: one outcome per page, never two.

    The script removes the old message in the browser; this is the guarantee
    underneath it — the page a submission renders is built fresh, so even with
    no JavaScript at all a result never accumulates.
    """
    first = _submit_multipart(
        running_server.server_port,
        {"size": "5", "export_formats": ["json"]},
        file_content=_png_bytes(),
    )
    assert _outcome(first.body) == pages.FAILURE

    second = _submit_multipart(
        running_server.server_port,
        {"size": "20", "export_formats": ["json"], "out": str(tmp_path)},
        file_content=_png_bytes(),
    )

    assert _outcome(second.body) == pages.SUCCESS
    assert second.body.count(b'data-outcome="') == 1, "two outcomes on one page"
    assert b"refused this request" not in second.body
