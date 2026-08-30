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
allowed is the domain's (ADR-0019/R1, guardrail G-4). The two checks this
module does make — the ``Host`` header and the connection's idle timeout — are
on the opposite side of that line: both are facts about the *transport*, both
are answered with a status code or a closed socket, and neither knows what a
puzzle is.
"""

from __future__ import annotations

import html
import urllib.parse
from collections.abc import Callable
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler

from nonogram.web import pages

__all__ = ["ALLOWED_HOSTS", "IDLE_TIMEOUT_S", "ROUTES", "WebUIRequestHandler"]

_HTML = "text/html; charset=utf-8"
_TEXT = "text/plain; charset=utf-8"

#: Seconds a connection may stay silent before the standard library drops it
#: (F-11). ``socketserver.StreamRequestHandler.setup`` turns this into a
#: ``settimeout`` on the accepted socket, so a client that connects and never
#: sends a request line stops holding a thread. Generous enough that no real
#: browser request is at risk — the only thing being bounded is *silence*.
IDLE_TIMEOUT_S = 30

#: Host names a request may name (F-12). Loopback binding stops a *network*
#: peer, but not the browser the user is already running: any page it loads can
#: aim a request at ``http://127.0.0.1:8765/``, and a name an attacker controls
#: that resolves to 127.0.0.1 would make the reply same-origin readable (DNS
#: rebinding). Checking the ``Host`` header closes the browser-mediated half of
#: the access control that the bind address alone cannot.
#:
#: This is an HTTP concern, not a domain rule: it is a fact about which *name*
#: the request used, decided before routing and answered with a status code
#: (guardrail G-4, ADR-0019/R1).
ALLOWED_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


def _host_is_local(host_header: str) -> bool:
    """Whether a ``Host`` header names this loopback server.

    The port is ignored — ``--port`` chooses it and a browser echoes whatever
    it dialled — so only the name is compared. Parsed with ``urlsplit`` rather
    than by splitting on ``":"`` so that ``[::1]:8765`` and a bare ``::1`` are
    both read correctly, and anything ``urlsplit`` cannot read at all is not
    local.

    ``@`` and ``/`` are refused before parsing. A ``Host`` is an authority, not
    a URL: userinfo and a path have no meaning in it, and RFC 7230 §5.4 admits
    neither. ``urlsplit`` would read ``user:pass@127.0.0.1`` and
    ``127.0.0.1/../evil`` as loopback — correctly, since the *host component*
    of both really is loopback, so neither was ever a hole — but that makes the
    set of accepted header *values* unbounded in shape while the set of
    accepted *names* is exactly three. Refusing the two characters keeps the
    two sets the same size, which is what row F-12 declares.
    """
    if "@" in host_header or "/" in host_header:
        return False
    try:
        hostname = urllib.parse.urlsplit(f"//{host_header}").hostname
    except ValueError:
        return False
    return hostname in ALLOWED_HOSTS


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

    #: Per-connection socket timeout (F-11). Without it
    #: ``StreamRequestHandler.setup`` leaves the socket blocking and the
    #: ``rfile.readline`` that reads the request line waits forever, so every
    #: client that connects and says nothing holds one of
    #: ``ThreadingHTTPServer``'s daemon threads for the life of the process.
    #: With it, the stdlib's ``handle_one_request`` catches the expiry, sets
    #: ``close_connection`` and lets the thread end.
    timeout = IDLE_TIMEOUT_S

    # ``do_<METHOD>`` is the standard library's dispatch protocol, so the
    # capitalisation is not this module's choice.
    def do_GET(self) -> None:
        """Dispatch one ``GET`` through :data:`ROUTES`."""
        self._dispatch("GET")

    def _dispatch(self, method: str) -> None:
        """Check the ``Host``, then look up ``(method, path)`` or answer ``404``.

        The query string is split off before the lookup so that ``/?x=1`` and
        ``/`` are the same route — the router matches paths, not URLs. Nothing
        in this card reads the query itself; ``GET`` carries no options
        (CON-008's submission is a ``POST``), so the parsed query is discarded
        rather than kept as an unused attribute a later card might mistake for
        a supported input.

        The ``Host`` check comes first (F-12). A header naming anything but
        loopback gets ``400`` and no route runs: it is a request that reached
        this server under a name it does not answer to, which is a malformed
        request, not a refused credential — there is still no ``401``, no
        ``403`` and nothing to authenticate (AC-053).

        *Every* ``Host`` header is read, not just the first. RFC 7230 §5.4
        forbids more than one, and a message carrying two that disagree has no
        single answer to "which name did this request use" — so it is refused
        before either is compared. Repeating one identical value says nothing
        new and is served.

        A request with *no* ``Host`` at all is served, on **every** protocol
        version and not only HTTP/1.0. That is deliberate: the attack this
        check closes is browser-mediated, and a browser cannot suppress the
        header (``Host`` is a forbidden header name to ``fetch``/XHR), so a
        missing one is never the attacker's shape. Refusing it would only cost
        HTTP/1.0 clients — ``curl --http1.0``, and this module's own AC-052
        interface probes, which send ``GET / HTTP/1.0`` with no ``Host``.

        The 404 body escapes the path it echoes. The response is
        ``text/plain`` and carries ``nosniff``, so markup in it is inert twice
        over rather than once (F-7).
        """
        host_headers = self.headers.get_all("Host") or []
        if len(set(host_headers)) > 1:
            self._respond(
                HTTPStatus.BAD_REQUEST,
                _TEXT,
                "conflicting host headers\n",
            )
            return
        if host_headers and not _host_is_local(host_headers[0]):
            self._respond(
                HTTPStatus.BAD_REQUEST,
                _TEXT,
                f"unrecognised host: {html.escape(host_headers[0])}\n",
            )
            return
        path = urllib.parse.urlsplit(self.path).path
        route = ROUTES.get((method, path))
        if route is None:
            self._respond(
                HTTPStatus.NOT_FOUND,
                _TEXT,
                f"no such page: {html.escape(path)}\n",
            )
            return
        route(self)

    def _respond(self, status: HTTPStatus, content_type: str, body: str) -> None:
        """Write one complete response: status line, headers, body.

        ``Content-Length`` is measured from the encoded bytes, not from
        ``len(body)`` — the form page is ASCII today but a puzzle name is not
        constrained to be (FR-015), and a character count would truncate the
        response for the first non-ASCII name CARD-020 echoes back.

        ``X-Content-Type-Options: nosniff`` is sent on every response, so a
        declared ``text/plain`` stays text however the body reads. The bodies
        that echo anything from the request are escaped as well; the header is
        the belt to that pair of braces, and it costs one line for every route
        a later card adds rather than one decision per route.
        """
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _serve_form(self) -> None:
        """``GET /`` — the option surface, rendered (FR-017).

        No credential is read on the way in and none is demanded on the way
        out: an ``Authorization`` header, a cookie, or neither all produce this
        same page (AC-053). The access control is the bind address plus the
        ``Host`` check in :meth:`_dispatch` — the second closes the one path the
        first cannot, a request steered here by a browser under a name that is
        not loopback (NFR-003, BCON-0001, F-8, F-12). Neither reads a
        credential, and there is nothing to authenticate.
        """
        self._respond(HTTPStatus.OK, _HTML, pages.FORM_PAGE)


#: The route table. One row today; CARD-020 adds ``("POST", "/generate")``.
#: Declared after the class because its values are unbound methods of it.
ROUTES: dict[tuple[str, str], Callable[[WebUIRequestHandler], None]] = {
    ("GET", "/"): WebUIRequestHandler._serve_form,
}
