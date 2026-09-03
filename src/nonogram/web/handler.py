"""The router: one ``(method, path)`` table and the handler that reads it.

ADR-0020 chose stdlib ``http.server`` over Flask/Bottle/``wsgiref``, so there is
no decorator registry and no framework dispatcher — routing is a dict, looked
up once per request. The table is keyed on ``(method, path)`` rather than on
path alone, which is what let CARD-020 add ``("POST", "/generate")`` as one row
plus a ``do_POST`` that dispatches through the same function ``do_GET`` does,
instead of growing a second dispatch mechanism beside it.

A method with no ``do_*`` of its own — ``PUT``, ``DELETE``, ``HEAD`` — still
gets ``BaseHTTPRequestHandler``'s ``501 Not Implemented``. The *body* of that
501, and of the other four statuses the standard library produces before
routing, is written by this module's :meth:`WebUIRequestHandler.send_error`
rather than by the stdlib's, so that every response really does carry
``nosniff`` and none of them echoes the request back.

The one thing this module must *not* grow is a decision about a request's
*content*. Reading a form field is HTTP; judging whether ``size=5000`` is
allowed is the domain's (ADR-0019/R1, guardrail G-2). Everything this module
decides for itself is on the transport side of that line — the ``Host`` header,
the connection's idle timeout, how many bytes of body it is willing to read —
and each is answered with a status code or a closed socket by code that does
not know what a puzzle is. What :meth:`WebUIRequestHandler._generate` does with
the body it read is one call to :mod:`nonogram.web.submission` and two to the
orchestrator, and the whole of its own judgement is which of two pages to
render.

The orchestrator runs **on this request's own thread**, start to finish
(ADR-0021): no job store, no polling endpoint, no worker handoff, no streamed
response. What bounds the wait is the deadline the solver already carries
(ADR-0011) against ADR-0001's budget, and a second mechanism here would be a
second thing to keep correct for no criterion that needs it. The cost is
recorded rather than hidden: a browser that gives up first sees a dead
connection, and the generation it started runs to completion on a thread nobody
is reading any more.
"""

from __future__ import annotations

import html
import urllib.parse
from collections.abc import Callable, Sequence
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler

from nonogram import orchestrator
from nonogram.errors import NonogramError
from nonogram.web import pages, submission

__all__ = [
    "ALLOWED_HOSTS",
    "IDLE_TIMEOUT_S",
    "MAX_BODY_BYTES",
    "ROUTES",
    "WebUIRequestHandler",
]

_HTML = "text/html; charset=utf-8"
_TEXT = "text/plain; charset=utf-8"

#: Seconds a connection may stay silent before the standard library drops it
#: (F-11). ``socketserver.StreamRequestHandler.setup`` turns this into a
#: ``settimeout`` on the accepted socket, so a client that connects and never
#: sends a request line stops holding a thread. Generous enough that no real
#: browser request is at risk — the only thing being bounded is *silence*.
IDLE_TIMEOUT_S = 30

#: Most bytes of request body this adapter will read from one submission.
#: The form's own body is a few hundred bytes at the very outside — nine short
#: fields — so this is three orders of magnitude of headroom, and what it
#: actually bounds is a body nobody typed: ``Content-Length: 4000000000`` on a
#: loopback socket would otherwise be read into memory in full, because
#: ``http.server`` bounds request *lines* and header counts and nothing else.
#:
#: A transport bound like :data:`IDLE_TIMEOUT_S`, not a domain rule: it is
#: measured in bytes off the wire, answered with a status code, and says
#: nothing about what any field contains (ADR-0019/R1, guardrail G-2).
MAX_BODY_BYTES = 64 * 1024

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
#: ``Sec-Fetch-Site``. That is NFR-004 / CON-010, with acceptance criteria of
#: its own (AC-054..AC-058) and its own property (EC-004), and it is **still
#: unimplemented**: CARD-020 added ``POST /generate`` without closing it, which
#: it recorded rather than assumed — see that card's worktree notes. Until it
#: is closed, a page on any origin can make this server generate and write
#: files; nothing below should be read as evidence otherwise.
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
    space is EC-004's property (NFR-004), which is not implemented and was not
    implemented by CARD-020 either; widening the check here is out of this
    function's scope on purpose.
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
    laziness about keep-alive, and it matters more now than it did before there
    was a ``do_POST``: this handler reads a request body on exactly one route
    and declines to read one everywhere else — a body sent with a ``GET``, and
    whatever exceeds :data:`MAX_BODY_BYTES` on a ``POST``. A persistent
    connection plus an unread body is how a server desynchronises and starts
    answering the leftovers as the next request. Closing the connection makes
    that structurally impossible rather than carefully avoided.
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

    def do_POST(self) -> None:
        """Dispatch one ``POST`` through :data:`ROUTES`.

        The same three lines as :meth:`do_GET` and deliberately so: the
        ``Host`` check, the path lookup and the 404 are properties of a
        *request*, not of a method, and a second copy of them here is how one
        of the two drifts. A ``POST`` to a path with no row gets the same plain
        404 a ``GET`` to it does.
        """
        self._dispatch("POST")

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
        allowlisted ``Host`` and be served (NFR-004 / CON-010, unimplemented).
        """
        self._respond(HTTPStatus.OK, _HTML, pages.FORM_PAGE)

    def _read_body(self) -> bytes | None:
        """The request body, or ``None`` when it is too large to read.

        ``Content-Length`` is the only framing this endpoint accepts. A body
        arriving without one — or with one that is not a number — is read as no
        body at all rather than guessed at: this server speaks HTTP/1.0, where
        an unframed body has no defined end, and a request with no fields
        travels inward and is refused by the domain for having no grid extent,
        which is the same answer ``nonogram generate`` with no ``--size``
        gives.

        A declared length over :data:`MAX_BODY_BYTES` is refused before it is
        read. What *is* read first is the cap's worth of it, and that ordering
        is the point: a client still mid-send when the socket closes sees a
        reset instead of the response it was about to be given, so the refusal
        is drained enough to be delivered. The rest is discarded with the
        connection (see the class docstring on HTTP/1.0).
        """
        try:
            declared = int(self.headers.get("Content-Length", ""))
        except ValueError:
            return b""
        if declared <= 0:
            return b""
        body = self.rfile.read(min(declared, MAX_BODY_BYTES))
        return None if declared > MAX_BODY_BYTES else body

    def _generate(self) -> None:
        """``POST /generate`` — one submission, run to completion (FR-017).

        The whole of the web adapter's contribution to a generation, and it is
        four steps with no branch that is not visible here: read the body, map
        it onto a request, call the orchestrator, render one of two pages.
        Every value in that request is the form's, unexamined — a ``size`` of
        60 goes inward as 60 and comes back as the same domain error a
        ``--size 60`` argv earns (AC-050, guardrail G-2).

        The two orchestrator calls are the two ``cli._run_generate`` makes, in
        that order and with nothing between them: generation is pure and only
        the export touches the filesystem (CON-003). They share one ``try``,
        which is EC-003's whole mechanism — the exception is converted to a
        page *before* :meth:`_respond` is called, so a failure and a success
        are the same number of writes to the response stream, and a half-
        written success can never be followed by an error.

        Three failures are caught, and they are the three a submission can
        produce that are not a bug in this package:

        * a body this adapter cannot read as a request at all (a ``size`` box
          holding ``twenty``) — refused before the orchestrator is called, so
          an unreadable form never starts a generation;
        * any :class:`~nonogram.errors.NonogramError` (EC-003) — the whole
          hierarchy, caught at its base rather than one class at a time, which
          is the same reason ``cli.main`` catches it there: an error a later
          card adds is reported by this code without being edited into it;
        * the ``OSError`` an export write can raise, which is not a domain
          error and is caught here for exactly the reason
          ``cli._run_generate`` catches it around the same call — ``--out``
          pointing at something unusable is the user's to fix, and a traceback
          does not tell them so.

        Anything else really is unexpected. It is not caught, and the
        standard library's own machinery reports it: a stack trace on the
        server's stderr, and a dropped connection for the browser. A blanket
        ``except`` here would turn a bug in this package into a tidy page
        claiming the run was merely refused.
        """
        raw = self._read_body()
        if raw is None:
            self._respond(
                HTTPStatus.CONTENT_TOO_LARGE, _TEXT, "form submission too large\n"
            )
            return
        posted = submission.read(raw.decode("utf-8", "replace"))
        if posted.request is None:
            self._fail("The form could not be read.", posted.unreadable)
            return
        try:
            puzzle = orchestrator.generate(posted.request)
            written = orchestrator.export_puzzle(puzzle)
        except NonogramError as error:
            self._fail("nonogram refused this request.", [str(error)])
            return
        except OSError as error:
            self._fail("The puzzle was generated but could not be written.", [str(error)])
            return
        self._respond(
            HTTPStatus.OK, _HTML, pages.result_page(puzzle.name, puzzle.seed, written)
        )

    def _fail(self, summary: str, reasons: Sequence[str]) -> None:
        """Render one failure page (EC-003).

        A single funnel for all three failure paths above, so "a domain error
        reaches the browser as a structured page and never as a traceback" is
        one line of code rather than a habit repeated three times.

        The status is ``200``: the response *is* the report, and delivering it
        succeeded. Sorting domain outcomes into HTTP status families would be a
        second error taxonomy beside ``cli.exit_code_for``'s exit-code table —
        the adapter drift ADR-0019 names as the accepted cost of two adapters,
        and the one this card was told to not pay. This package has no table of
        error classes at all; what it shows is the error's own message, which
        is the same text ``cli._report`` prints.
        """
        self._respond(HTTPStatus.OK, _HTML, pages.failure_page(summary, reasons))


#: The route table: the form, and the submission it posts. Declared after the
#: class because its values are unbound methods of it, and keyed on the same
#: :data:`nonogram.web.pages.FORM_ACTION` the form's ``action`` is rendered
#: from, so the two cannot disagree about where a submission goes.
ROUTES: dict[tuple[str, str], Callable[[WebUIRequestHandler], None]] = {
    ("GET", "/"): WebUIRequestHandler._serve_form,
    ("POST", pages.FORM_ACTION): WebUIRequestHandler._generate,
}
