"""The router: one ``(method, path)`` table and the handler that reads it.

ADR-0020 chose stdlib ``http.server`` over Flask/Bottle/``wsgiref``, so there is
no decorator registry and no framework dispatcher — routing is a dict, looked
up once per request. The table is keyed on ``(method, path)`` rather than on
path alone so that CARD-020 adds ``("POST", "/generate")`` as one row plus a
``do_POST`` that dispatches through this same function, instead of growing a
second dispatch mechanism beside it.

Why there is no ``do_POST`` here: this card renders the form and does not
submit it (guardrail G-5). ``BaseHTTPRequestHandler`` answers a method it has
no ``do_*`` for with ``501 Unsupported method``, which is the truthful status
for an endpoint that does not exist yet — truer than a ``405`` this card would
have to write code to produce, and it disappears the moment CARD-020 adds the
real handler.

The one thing this module must *not* grow is a decision about a request's
*content*. Reading a form field is HTTP; judging whether ``size=5000`` is
allowed is the domain's (ADR-0019/R1, guardrail G-4).
"""

from __future__ import annotations

import urllib.parse
from collections.abc import Callable
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler

from nonogram.web import pages

__all__ = ["ROUTES", "WebUIRequestHandler"]

_HTML = "text/html; charset=utf-8"
_TEXT = "text/plain; charset=utf-8"


class WebUIRequestHandler(BaseHTTPRequestHandler):
    """COMP-008's request handler.

    Deliberately *not* a ``SimpleHTTPRequestHandler`` subclass: that class maps
    a request path onto a file on disk, and nothing in this UI is served from
    disk — the form is a string constant (ADR-0020, :mod:`nonogram.web.pages`).
    Inheriting from it would put the whole working directory one path-traversal
    bug away from a browser, to serve zero files.

    ``protocol_version`` is left at ``BaseHTTPRequestHandler``'s ``HTTP/1.0``
    default, so every connection is closed after one response. That is not
    laziness about keep-alive: this card never reads a request body, and a
    persistent connection plus an unread body is how a server desynchronises
    and starts answering the wrong request.
    """

    #: Shown in the ``Server:`` header instead of the stdlib's default.
    #: Cosmetic — nothing routes on it.
    server_version = "nonogram-web"

    # ``do_<METHOD>`` is the standard library's dispatch protocol, so the
    # capitalisation is not this module's choice.
    def do_GET(self) -> None:
        """Dispatch one ``GET`` through :data:`ROUTES`."""
        self._dispatch("GET")

    def _dispatch(self, method: str) -> None:
        """Look up ``(method, path)`` and run the route, or answer ``404``.

        The query string is split off before the lookup so that ``/?x=1`` and
        ``/`` are the same route — the router matches paths, not URLs. Nothing
        in this card reads the query itself; ``GET`` carries no options
        (CON-008's submission is a ``POST``), so the parsed query is discarded
        rather than kept as an unused attribute a later card might mistake for
        a supported input.
        """
        path = urllib.parse.urlsplit(self.path).path
        route = ROUTES.get((method, path))
        if route is None:
            self._respond(
                HTTPStatus.NOT_FOUND,
                _TEXT,
                f"no such page: {path}\n",
            )
            return
        route(self)

    def _respond(self, status: HTTPStatus, content_type: str, body: str) -> None:
        """Write one complete response: status line, headers, body.

        ``Content-Length`` is measured from the encoded bytes, not from
        ``len(body)`` — the form page is ASCII today but a puzzle name is not
        constrained to be (FR-015), and a character count would truncate the
        response for the first non-ASCII name CARD-020 echoes back.
        """
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _serve_form(self) -> None:
        """``GET /`` — the option surface, rendered (FR-017).

        No credential is read on the way in and none is demanded on the way
        out: an ``Authorization`` header, a cookie, or neither all produce this
        same page (AC-053). Loopback binding is the whole of the access control
        (NFR-003, BCON-0001).
        """
        self._respond(HTTPStatus.OK, _HTML, pages.FORM_PAGE)


#: The route table. One row today; CARD-020 adds ``("POST", "/generate")``.
#: Declared after the class because its values are unbound methods of it.
ROUTES: dict[tuple[str, str], Callable[[WebUIRequestHandler], None]] = {
    ("GET", "/"): WebUIRequestHandler._serve_form,
}
