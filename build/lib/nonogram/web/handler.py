"""The router: one ``(method, path)`` table and the handler that reads it.

ADR-0020 chose stdlib ``http.server`` over Flask/Bottle/``wsgiref``, so there is
no decorator registry and no framework dispatcher — routing is a dict, looked
up once per request. The table is keyed on ``(method, path)`` rather than on
path alone so that CARD-020 adds ``("POST", "/generate")`` as one row plus a
``do_POST`` that dispatches through this same function, instead of growing a
second dispatch mechanism beside it.

Why there is no ``do_POST`` here: this card renders the form and does not
submit it (guardrail G-5). ``BaseHTTPRequestHandler`` answers a method it has
no ``do_*`` for with ``501 Not Implemented``, which is the truthful status for
an endpoint that does not exist yet — truer than a ``405`` this card would
have to write code to produce, and it disappears the moment CARD-020 adds the
real handler. The *body* of that 501, and of the other four statuses the
standard library produces before routing, is written by this module's
:meth:`WebUIRequestHandler.send_error` rather than by the stdlib's, so that
every response really does carry ``nosniff`` and none of them echoes the
request back.

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
#: rebinding). Checking the ``Host`` header closes **DNS rebinding only**: a
#: request that reached this server under a name it does not answer to.
#:
#: It does **not** close the other browser-mediated reach. A page on any origin
#: can still aim a request at ``http://127.0.0.1:<port>/`` with an allowlisted
#: ``Host`` — a browser sets ``Host`` from the *target*, not from the page —
#: and be served (verified on the wire: ``Host: 127.0.0.1:<port>`` +
#: ``Origin: https://evil.example.com`` + ``Sec-Fetch-Site: cross-site`` →
#: ``200`` and the form). Nothing here reads ``Origin``, ``Referer`` or
#: ``Sec-Fetch-Site``. That is NFR-004 / CON-010, unimplemented, owned by
#: CARD-020, and must not be assumed closed by the card that adds
#: ``POST /generate``.
#:
#: This is an HTTP concern, not a domain rule: it is a fact about which *name*
#: the request used, decided before routing and answered with a status code
#: (guardrail G-4, ADR-0019/R1).
ALLOWED_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


def _host_is_local(host_header: str) -> bool:
    """Whether a ``Host`` header names this loopback server.

    The port is ignored — ``--port`` chooses it and a browser echoes whatever
    it dialled — so only the name is compared. Parsed with ``urlsplit`` rather
    than by splitting on ``":"`` so that a bracketed ``[::1]:8765`` is read as
    the host ``::1`` and not as ``[``; anything ``urlsplit`` cannot read as a
    host is not local, which is why a *bare* ``::1`` is refused (``urlsplit``
    returns ``None`` for it, and RFC 7230 §5.4 requires the brackets anyway).

    ``@`` and ``/`` are refused before parsing. A ``Host`` is an authority, not
    a URL: userinfo and a path have no meaning in it, and RFC 7230 §5.4 admits
    neither. ``urlsplit`` would read ``user:pass@127.0.0.1`` and
    ``127.0.0.1/../evil`` as loopback — correctly, since the *host component*
    of both really is loopback, so neither was ever a hole — and refusing the
    two characters is a narrowing of the accepted *shapes*, nothing more.

    What it is **not** is a bound on the accepted value set. ``urlsplit``
    splits on ``#`` and ``?`` exactly as it splits on ``@`` and ``/``, and
    neither is refused here: ``127.0.0.1#evil.example.com`` and
    ``localhost?evil`` are both read as loopback and served, and the port is
    never validated (``127.0.0.1:notaport`` is served too). The earlier
    rationale for this narrowing claimed it "keeps the two sets the same size";
    it does not, and the claim is withdrawn rather than repaired. What this
    function actually enforces is one sentence: *the host component, as*
    ``urlsplit`` *reads it, must be one of three names*. Bounding the shape
    space is EC-004's property and lands with CARD-020 (NFR-004); widening the
    check here is out of this function's scope on purpose.
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
        version and not only HTTP/1.0. That is deliberate: the rebinding attack
        this check closes is browser-mediated, and a browser cannot suppress
        the header (``Host`` is a forbidden header name to ``fetch``/XHR), so a
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

    def _respond(self, status: HTTPStatus | int, content_type: str, body: str) -> None:
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

        "Every response" is literal, and it is only literal because
        :meth:`send_error` funnels the standard library's own error statuses
        through here too. This adapter can produce seven distinct statuses —
        200, 400, 404, 414, 431, 501, 505 — and five of them (400, 414, 431,
        501, 505) were written by ``BaseHTTPRequestHandler.send_error`` before
        that override: ``text/html`` with no ``nosniff`` for three of them,
        and — on the 400 and 505 paths, where ``parse_request`` had not yet
        accepted a version — no status line and no headers whatsoever. The
        sentence above was false for all five.
        """
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if payload:
            self.wfile.write(payload)

    # ``send_error`` is the standard library's hook name, so the spelling is
    # not this module's choice, and neither is the signature.
    def send_error(
        self,
        code: int,
        message: str | None = None,
        explain: str | None = None,
    ) -> None:
        """Answer a request the standard library rejected, on this module's terms.

        ``BaseHTTPRequestHandler`` handles 400 (unparseable request line or
        version), 414 (over-long request line), 431 (too many header fields, or
        one over-long header line), 501 (a method with no ``do_*``) and 505 (a
        well-formed version this server does not speak) before ``do_GET`` is
        ever reached, and it writes all five through this hook. Its own version
        replies ``text/html`` with no ``X-Content-Type-Options`` and interpolates
        ``message``/``explain`` — which is where the request's own method and
        version token live — into that HTML body, and into the *status line*
        too: the stdlib's 501 reads ``501 Unsupported method ('POST')``.

        Routing them through :meth:`_respond` instead buys two things and costs
        nothing: ``nosniff`` and ``text/plain`` really are on *every* response,
        and nothing off the wire is echoed in a body or a reason phrase.
        ``message`` and ``explain`` are therefore accepted and deliberately
        dropped from the response. ``message`` still reaches the server's own
        log, exactly as before, so an operator debugging a client can still see
        what was sent; ``explain`` is a static canned string from
        ``responses`` and is dropped entirely — the stdlib logged only
        ``message`` too, so nothing was lost.

        One deliberate side effect: 431's reason phrase is now the canonical
        ``Request Header Fields Too Large`` for both of its causes, where the
        stdlib distinguished them as ``Too many headers`` and ``Line too
        long``. The two remain distinguishable in the log, not on the wire.
        That is the price of not echoing the request, and reason phrases are
        advisory per RFC 9112 §4.

        The ``request_version`` reset is what makes that possible for two of the
        five. ``parse_request`` assigns the *parsed* version only after it has
        accepted it, so on the 400 and 505 paths it is still the ``HTTP/0.9``
        default when the error is written — and ``send_response_only`` and
        ``end_headers`` both no-op for ``HTTP/0.9``. As shipped, those two
        statuses therefore reached the client as a bare body with **no status
        line and no headers at all**: not merely no ``nosniff`` but no
        ``Content-Type`` and no status either. Answering a request whose version
        could not be read with this server's own version is what RFC 9112 §2.3
        expects, and it is the only way "on every response" can be true.

        A ``HEAD`` has no ``do_HEAD``, so it arrives here as a 501; RFC 9110
        §9.3.2 forbids a body on the response to one, and the standard library
        suppresses it. So does this: the body is empty and ``Content-Length``
        is ``0``.
        """
        short = self.responses.get(code, ("", ""))[0]
        self.log_error("code %d, message %s", code, message if message else short)
        self.close_connection = True
        if self.request_version == "HTTP/0.9":
            self.request_version = self.protocol_version
        head = getattr(self, "command", None) == "HEAD"
        line = f"{int(code)} {short}".rstrip()
        self._respond(code, _TEXT, "" if head else f"{line}\n")

    def _serve_form(self) -> None:
        """``GET /`` — the option surface, rendered (FR-017).

        No credential is read on the way in and none is demanded on the way
        out: an ``Authorization`` header, a cookie, or neither all produce this
        same page (AC-053). The access control is the bind address plus the
        ``Host`` check in :meth:`_dispatch`, and nothing else — the first stops
        a network peer, the second stops DNS rebinding, a request steered here
        by a browser under a name that is not loopback (NFR-003, BCON-0001,
        F-8, F-12). Neither reads a credential, and there is nothing to
        authenticate. Neither closes browser-mediated *cross-origin* reach
        either: a page on any origin can still aim a request here with an
        allowlisted ``Host`` and be served (NFR-004 / CON-010, CARD-020).
        """
        self._respond(HTTPStatus.OK, _HTML, pages.FORM_PAGE)


#: The route table. One row today; CARD-020 adds ``("POST", "/generate")``.
#: Declared after the class because its values are unbound methods of it.
ROUTES: dict[tuple[str, str], Callable[[WebUIRequestHandler], None]] = {
    ("GET", "/"): WebUIRequestHandler._serve_form,
}
