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
the authority and fetch-metadata a request claims (NFR-004, CON-010), the
connection's idle timeout, how many bytes of body it is willing to read — and
each is answered with a status code or a closed socket by code that does not
know what a puzzle is. What :meth:`WebUIRequestHandler._generate` does with
the body it read is one call to :mod:`nonogram.web.submission` or
:mod:`nonogram.web.multipart` (CARD-021's branch on ``Content-Type``, still a
transport fact and not a domain one) and two to the orchestrator, and the
whole of its own judgement is which of two pages to
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
import mimetypes
import urllib.parse
from collections.abc import Callable, Sequence
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from pathlib import Path

from nonogram import orchestrator
from nonogram.errors import NonogramError
from nonogram.web import multipart, pages, submission

# For re-populating form fields after submission (CARD-030)
_TYPE_CHECKED = dict[str, list[str]]

__all__ = [
    "ALLOWED_FETCH_SITES",
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
#: fields — so this is two orders of magnitude of headroom, and what it
#: actually bounds is a body nobody typed: ``Content-Length: 4000000000`` on a
#: loopback socket would otherwise be read into memory in full, because
#: ``http.server`` bounds request *lines* and header counts and nothing else.
#:
#: A transport bound like :data:`IDLE_TIMEOUT_S`, not a domain rule: it is
#: measured in bytes off the wire, answered with a status code, and says
#: nothing about what any field contains (ADR-0019/R1, guardrail G-2).
MAX_BODY_BYTES = 50 * 1024 * 1024  # 50 MB for large image uploads

#: Host names a request may name (F-12). Loopback binding stops a *network*
#: peer, but not the browser the user is already running: any page it loads can
#: aim a request at ``http://127.0.0.1:8765/``, and a name an attacker controls
#: that resolves to 127.0.0.1 would make the reply same-origin readable (DNS
#: rebinding). Checking the ``Host`` header closes **DNS rebinding only**: a
#: request that reached this server under a name it does not answer to.
#:
#: The same three names are what an ``Origin`` header and an absolute-form
#: request target are compared against too (:func:`_origin_is_local`,
#: :meth:`WebUIRequestHandler._cross_origin_refusal`): all three answer one
#: question — which authority does this request claim — and a single allowlist
#: is what stops them from drifting into three notions of "local".
#:
#: This is an HTTP concern, not a domain rule: it is a fact about which *name*
#: the request used, decided before routing and answered with a status code
#: (ADR-0019/R1, guardrail G-2).
ALLOWED_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})

#: The ``Sec-Fetch-Site`` values this server answers (NFR-004, CON-010,
#: AC-054, AC-057). ``same-origin`` is the form posting back to the page it was
#: served from; ``none`` is a user-initiated navigation with no initiator
#: document at all — a typed URL, a bookmark. The two values the fetch-metadata
#: spec defines and this set omits, ``same-site`` and ``cross-site``, both say
#: the request was started by a document this server did not serve, which is
#: the whole of the attack (NFR-004's rationale).
#:
#: Compared exactly, after stripping surrounding whitespace and nothing else.
#: These are lowercase tokens by specification, so a value spelled any other
#: way did not come from a browser following it and is refused rather than
#: guessed at — which is also what makes EC-004's "for any such input" property
#: checkable: the accepted set is two literals wide.
ALLOWED_FETCH_SITES = frozenset({"same-origin", "none"})


def _port_is_well_formed(authority: str) -> bool:
    """Whether ``authority``'s port component is absent or a run of digits.

    Named by EC-004 among the shapes a refusal must cover. ``127.0.0.1:`` (an
    empty port) and ``127.0.0.1:notaport`` (a non-numeric one) are both read by
    ``urlsplit`` as the *host* ``127.0.0.1``, so a check consulting only the
    host component serves them. Neither is a well-formed authority — RFC 3986
    §3.2.3 admits digits and nothing else — so neither is served.

    The split is taken after the last ``]`` so the colons inside a bracketed
    IPv6 literal are not mistaken for the port separator.
    """
    after_brackets = authority.rsplit("]", 1)[-1]
    _, colon, port = after_brackets.rpartition(":")
    if not colon:
        return True
    return port.isascii() and port.isdigit()


def _host_is_local(host_header: str) -> bool:
    """Whether an authority names this loopback server.

    Used for all three authorities a request can carry: the ``Host`` header,
    the request target's when it arrives in absolute form, and — through
    :func:`_origin_is_local` — the ``Origin`` header's.

    The port's *value* is ignored: ``--port`` chooses it and a browser echoes
    back whatever it dialled, so only the name is compared. Its *shape* is not
    ignored (:func:`_port_is_well_formed`). Parsed with ``urlsplit`` rather
    than by splitting on ``":"`` so that a bracketed ``[::1]:8765`` is read as
    the host ``::1`` and not as ``[``; anything ``urlsplit`` cannot read as a
    host is not local, which is why a *bare* ``::1`` is refused (``urlsplit``
    returns ``None`` for it, and RFC 7230 §5.4 requires the brackets anyway).

    ``@``, ``/``, ``#`` and ``?`` are refused before parsing. An authority is
    not a URL: userinfo, a path, a query and a fragment have no meaning in one
    and RFC 7230 §5.4 admits none of them, but ``urlsplit`` splits all four off
    and so reads ``user:pass@127.0.0.1``, ``127.0.0.1/../evil``,
    ``127.0.0.1#evil.example.com`` and ``localhost?evil`` as loopback. The host
    component of each of those genuinely is loopback, so none was a hole; they
    are refused because a value carrying any of the four is not a host name,
    and EC-004 names the ``#`` and ``?`` shapes explicitly.

    What this enforces is therefore one sentence: *the value must be a bare
    authority — no userinfo, path, query or fragment, and a port that is absent
    or all digits — whose host component is one of three names.*
    """
    if any(char in host_header for char in "@/#?"):
        return False
    if not _port_is_well_formed(host_header):
        return False
    try:
        hostname = urllib.parse.urlsplit(f"//{host_header}").hostname
    except ValueError:
        return False
    return hostname in ALLOWED_HOSTS


def _origin_is_local(origin: str) -> bool:
    """Whether an ``Origin`` header names a loopback authority (NFR-004).

    An ``Origin`` is a *serialized origin* — ``scheme "://" host [":" port]``
    and nothing more (RFC 6454 §6.1) — so a value carrying a path, a query or a
    fragment is not one, and the opaque origin ``null`` has no host at all.
    Each of those is refused: the header is compared against the shape it is
    defined to have rather than mined for a host substring.

    The scheme is read for presence and then discarded, and so is the port,
    exactly as the ``Host`` check discards it. NFR-004 states the rule over the
    host — "an ``Origin`` header naming a host that is not a loopback name" —
    and a page served from another port on loopback is not the reach this
    closes: BCON-0001 puts one user on one machine, and a second local HTTP
    server is already inside that boundary.
    """
    value = origin.strip()
    try:
        split = urllib.parse.urlsplit(value)
    except ValueError:
        return False
    if not split.scheme or split.path or split.query or split.fragment:
        return False
    return _host_is_local(split.netloc)


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

    def _cross_origin_refusal(self) -> str | None:
        """Why this request is cross-site or names a foreign authority — or ``None``.

        NFR-004 / CON-010, and the half of BCON-0001's browser-mediated reach
        that the ``Host`` check does not close. A browser sets ``Host`` from
        the request's *target*, so a form on ``https://evil.example.com``
        posting to ``http://127.0.0.1:8765/generate`` arrives with an
        allowlisted ``Host`` and, on nothing but that check, is served — and
        since ``POST /generate`` exists, "served" means the pipeline runs and
        writes files at a path the attacking page chose. The attack needs no
        reply, so the same-origin policy and CORS never come into it.

        What a browser *does* attach to such a request is what this reads.
        Three signals, each refused with ``400`` (AC-054, AC-055, AC-056):

        * an **absolute-form request target** whose authority is not loopback,
          which is how the same reach arrives with no ``Host`` header at all to
          check (AC-056). ``urlsplit`` would also find an authority in a target
          beginning ``//``, and this refuses that shape as well — defensively,
          not because it can arrive: ``http.server``'s own ``parse_request``
          collapses a leading ``//`` to ``/`` before ``do_GET`` is called, so
          on this standard library that arm is unreachable and untested on the
          wire;
        * a **``Sec-Fetch-Site``** other than :data:`ALLOWED_FETCH_SITES`;
        * an **``Origin``** whose host is not a loopback name.

        Every value of each header is read, not just the first, for the reason
        the ``Host`` check reads every one: a request carrying two that
        disagree has no single answer, and taking the first is how an
        allowlisted value smuggles a foreign one past.

        Neither header can be *set* by page script — both are forbidden header
        names to ``fetch``/XHR — so a request carrying neither is not the
        attacker's shape and is served (AC-058). That is what keeps ``curl``, a
        typed URL and this module's own HTTP/1.0 probes working.

        "Cannot be *suppressed*" would be too strong for ``Origin``, and the
        distinction is worth stating because it is what makes "absent means
        served" safe rather than lucky. A cross-origin GET may legitimately
        carry no ``Origin`` at all — a ``no-cors`` fetch, an ``<img>``, a
        top-level navigation — so absence is not proof of anything on its own.
        It does not have to be: the Fetch standard requires an ``Origin`` on
        every cross-origin request whose method is not ``GET``/``HEAD``, plain
        ``<form method=post>`` included, and the only route here that writes
        files is ``POST /generate``. A cross-origin GET carrying neither header
        reaches ``GET /`` and a constant string. On any browser implementing
        fetch metadata (Chrome 76+, Firefox 90+, Safari 16.4+),
        ``Sec-Fetch-Site: cross-site`` catches that GET case as well.

        ``Referer`` is deliberately not consulted: it is suppressible by a
        referrer policy the attacking page controls, so a rule resting on it
        would be one the attacker can switch off.

        A method with no ``do_*`` never reaches this check at all.
        ``BaseHTTPRequestHandler`` answers ``PUT``, ``DELETE``, ``PATCH``,
        ``OPTIONS`` and ``HEAD`` with ``501`` before :meth:`_dispatch` runs —
        measured on the wire, with a cross-site ``Origin`` and
        ``Sec-Fetch-Site`` attached and nothing written. EC-004's operative
        clause ("refuses the request and never routes it to a handler") holds
        for each of them by that different mechanism, so NFR-004's literal
        ``400`` is a statement about the two routed methods. Moving the check
        ahead of the standard library's method dispatch would mean overriding
        ``handle_one_request``, which buys no security and costs stdlib
        coupling; AC-054..AC-058 are all ``GET``/``POST``-stated, and the
        property corpus covers those two methods for the same reason.

        Returns:
            The refusal, phrased for the response body, or ``None`` when the
            request claims no foreign authority.
        """
        target = urllib.parse.urlsplit(self.path).netloc
        if target and not _host_is_local(target):
            return f"unrecognised request-target authority: {target}"
        for site in self.headers.get_all("Sec-Fetch-Site") or []:
            if site.strip() not in ALLOWED_FETCH_SITES:
                return f"cross-site request: {site.strip()}"
        for origin in self.headers.get_all("Origin") or []:
            if not _origin_is_local(origin):
                return f"foreign origin: {origin.strip()}"
        return None

    def _dispatch(self, method: str) -> None:
        """Check where the request came from, then route it or answer ``404``.

        The query string is split off before the lookup so that ``/?x=1`` and
        ``/`` are the same route — the router matches paths, not URLs. Nothing
        in this card reads the query itself; ``GET`` carries no options
        (CON-008's submission is a ``POST``), so the parsed query is discarded
        rather than kept as an unused attribute a later card might mistake for
        a supported input.

        The ``Host`` check comes first (F-12), then
        :meth:`_cross_origin_refusal` (NFR-004, CON-010). Both are decided
        before any route runs and both answer ``400``: a request naming a host
        this server does not answer to, or started by a document it did not
        serve, is malformed — not a refused credential. There is still no
        ``401``, no ``403`` and nothing to authenticate (AC-053), and ``400``
        is the status NFR-004 and AC-054..AC-056 name.

        *Every* ``Host`` header is read, not just the first. RFC 7230 §5.4
        forbids more than one, and a message carrying two that disagree has no
        single answer to "which name did this request use" — so it is refused
        before either is compared. Repeating one identical value says nothing
        new and is served.

        A request with *no* ``Host`` at all still reaches
        :meth:`_cross_origin_refusal`, which is where AC-056's absolute-form
        target is caught, and is otherwise served, on **every** protocol
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
        refusal = self._cross_origin_refusal()
        if refusal is not None:
            self._respond(HTTPStatus.BAD_REQUEST, _TEXT, f"{html.escape(refusal)}\n")
            return
        path = urllib.parse.urlsplit(self.path).path

        # Handle /static/ prefix for static assets (CARD-034)
        if method == "GET" and path.startswith("/static/"):
            static_file = path[8:]  # Remove "/static/" prefix
            self._serve_static(static_file)
            return

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
        through here too. This adapter can produce eight distinct statuses —
        200, 400, 404, 413, 414, 431, 501, 505. Four are written by this
        module's own calls to this method (200, 400, 404, 413) and five by
        ``BaseHTTPRequestHandler.send_error`` before that override (400, 414,
        431, 501, 505); 400 is on both lists, since it is both the router's
        answer to a foreign host or origin and the standard library's to an
        unparseable request line. The sentence above was false for all five on
        the stock library, in two different ways: 414, 431 and 501 arrived as
        ``text/html`` with no ``nosniff``, while 505 and *three of the four
        request-line shapes that earn a* 400 arrived with no status line and no
        headers whatsoever. :meth:`send_error` says which shapes those are, and
        why the fourth is not one of them.
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

        The ``request_version`` reset is what makes that possible on the paths
        where the version was never accepted. ``parse_request`` assigns the
        *parsed* version (``self.request_version = version``) only after it has
        accepted it, and ``send_response_only`` and ``end_headers`` both no-op
        for ``HTTP/0.9`` — so an error written before that assignment reached
        the client as a bare body with **no status line and no headers at all**:
        not merely no ``nosniff`` but no ``Content-Type`` and no status either.

        Which errors those are, measured against this interpreter's own
        ``parse_request`` rather than reasoned from the shape of the code:

        * ``Bad request version`` (400) and ``Invalid HTTP version`` (505) both
          leave from inside the version-parsing branch, before the assignment —
          bare;
        * ``Bad HTTP/0.9 request type`` (400), a two-word request line, never
          enters that branch — bare;
        * ``Bad request syntax`` (400) is reached from **both** sides of the
          assignment, because its guard is a word count: a one-word request line
          skips the branch and is bare, while a line of four or more words has
          already parsed and assigned a real version, so it goes out with a
          status line and headers even on the stock library.

        The reset is therefore a no-op on that last shape and load-bearing on
        the other four. Answering a request whose version could not be read with
        this server's own version is what RFC 9112 §2.3 expects, and it is the
        only way "on every response" can be true.

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
        same page (AC-053). The access control is three checks and nothing
        else, none of which reads a credential because there is nothing to
        authenticate: the bind address stops a network peer (NFR-003), the
        ``Host`` check in :meth:`_dispatch` stops DNS rebinding — a request
        steered here by a browser under a name that is not loopback (F-8,
        F-12) — and :meth:`_cross_origin_refusal` stops a request some other
        page started (NFR-004, CON-010, BCON-0001).
        """
        self._respond(HTTPStatus.OK, _HTML, pages.FORM_PAGE)

    def _serve_static(self, path: str) -> None:
        """``GET /static/<file>`` — serve static assets (CARD-034).

        Serves static files (JavaScript, CSS, etc.) from the nonogram/web/static/
        directory. Only files within the static directory are served to prevent
        path traversal attacks. The path parameter should be the relative path
        within the static directory.

        Returns a 404 if the file is not found or contains invalid path traversal
        characters.
        """
        # Prevent path traversal attacks
        if ".." in path or path.startswith("/"):
            self._respond(HTTPStatus.NOT_FOUND, _TEXT, "not found\n")
            return

        # Construct the file path
        base_dir = Path(__file__).parent / "static"
        file_path = (base_dir / path).resolve()

        # Verify the resolved path is within the static directory
        try:
            file_path.relative_to(base_dir)
        except ValueError:
            # Path is outside the static directory
            self._respond(HTTPStatus.NOT_FOUND, _TEXT, "not found\n")
            return

        # Check if the file exists
        if not file_path.is_file():
            self._respond(HTTPStatus.NOT_FOUND, _TEXT, "not found\n")
            return

        # Read and serve the file
        try:
            with open(file_path, "rb") as f:
                content = f.read()

            # Determine the content type
            content_type, _ = mimetypes.guess_type(str(file_path))
            if content_type is None:
                content_type = "application/octet-stream"

            # Add charset for text files
            if content_type.startswith("text/"):
                content_type += "; charset=utf-8"

            # Send response with binary content
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except (OSError, IOError):
            self._respond(HTTPStatus.NOT_FOUND, _TEXT, "not found\n")

    def _read_body(self) -> bytes | None:
        """The request body, or ``None`` when it is too large to read.

        ``Content-Length`` is the only framing this endpoint accepts. A body
        arriving without one — or with one that is not a number — is read as no
        body at all rather than guessed at: this server speaks HTTP/1.0, where
        an unframed body has no defined end, and a request with no fields
        travels inward and is refused by the domain for having no grid extent,
        which is the same answer ``nonogram generate`` with no ``--size``
        gives.

        A declared length over :data:`MAX_BODY_BYTES` is answered with ``413``
        after at most the cap's worth of it has been read, and none of it is
        ever acted on. That ordering is the point rather than an accident: a
        client still mid-send when the socket closes sees a reset instead of
        the response it was about to be given, so the refusal is drained enough
        to be delivered. The rest is discarded with the connection (see the
        class docstring on HTTP/1.0).
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

        "Read the body" is now two branches rather than one call (CARD-021):
        a ``Content-Type: multipart/form-data`` request — the shape a browser
        sends once the form carries a file control — is read by
        :func:`nonogram.web.multipart.read`, which lands the uploaded part in
        a temp file and hands back its path alongside the mapped submission;
        every other ``Content-Type`` — including none at all — is read as
        urlencoded text exactly as before CARD-021 (guardrail G-3). A
        multipart body is *not* decoded as UTF-8 before parsing, where a
        urlencoded one always is: an uploaded picture's bytes are binary, and
        text-decoding them first is exactly the kind of corruption
        AC-boundary/multipart's byte-for-byte check would catch.

        Whatever temp file that branch produced is this method's to remove
        once the run is over — the ``finally`` below covers every way "over"
        can happen: a page rendered, a domain error, an ``OSError``, or an
        exception this method does not catch at all. That last case is why
        cleanup is a ``finally`` and not one more line at the end of the
        happy path: a bug three lines from here must not leak the file the
        same way it must not corrupt the response.

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
          holding ``twenty``, an ``export_formats`` value no renderer is
          registered under, a ``%00`` in any field) — refused before the
          orchestrator is called, so an unreadable form never starts a
          generation;
        * any :class:`~nonogram.errors.NonogramError` (EC-003) — the whole
          hierarchy, caught at its base rather than one class at a time, which
          is the same reason ``cli.main`` catches it there: an error a later
          card adds is reported by this code without being edited into it;
        * an ``OSError`` from either call, which is not a domain error —
          ``--out`` naming a file, or a directory the user cannot write, is
          theirs to fix and a traceback does not tell them so.

        That last arm is **wider than the one ``cli._run_generate`` has**, and
        the difference is deliberate rather than parallel: the CLI wraps only
        ``export_puzzle``, because widening it there once reported a missing
        picture as "export rejected" (cli.py's own note on that fix). Here the
        two calls share one ``try``, which is EC-003's whole mechanism — the
        exception becomes a page *before* :meth:`_respond` is called, so a
        failure and a success are the same single write to the response stream
        — so the message must be true of an ``OSError`` from *either* call, and
        it says a file could not be read or written rather than naming the
        export. Only the export raises one in practice: ``sourcing/image.py``
        converts every way reading the uploaded temp file can fail into
        ``UnreadableImage``, a ``NonogramError``, so the image CARD-021 now
        fills ``GenerationRequest.image`` with does not change which arm this
        is; the wording does not depend on that staying true either way.

        Anything else really is unexpected. It is not caught, and the
        standard library's own machinery reports it: a stack trace on the
        server's stderr, and a dropped connection for the browser. A blanket
        ``except`` here would turn a bug in this package into a tidy page
        claiming the run was merely refused. What that costs is bounded by
        refusing the two shapes measured to reach it — an unregistered export
        format and a ``%00`` in a field — both in :mod:`nonogram.web.submission`
        and both reported through ``unreadable``, which is the first arm above.

        CARD-030: Instead of redirecting to success/failure pages, results are
        displayed inline on the form page. The form is re-rendered with submitted
        values preserved and a collapsible result section showing the outcome.
        """
        raw = self._read_body()
        if raw is None:
            self._respond(
                HTTPStatus.CONTENT_TOO_LARGE, _TEXT, "form submission too large\n"
            )
            return
        content_type = self.headers.get("Content-Type", "")
        media_type = content_type.split(";", 1)[0].strip().lower()
        image_path: Path | None = None
        fields: _TYPE_CHECKED = {}

        # Parse the body to extract submission and fields
        image_filename: str | None = None
        persisted_image_path: str | None = None
        persisted_image_filename: str | None = None  # Original filename for retry
        newly_uploaded_image_path: Path | None = None  # Track newly uploaded vs persisted
        if media_type == "multipart/form-data":
            parsed = multipart.read(content_type, raw)
            posted = parsed.submission
            newly_uploaded_image_path = parsed.image_path
            image_path = parsed.image_path
            image_filename = parsed.image_filename
            fields = parsed.fields  # Extract fields for form re-population
            # Get persisted image path from hidden form field for retry without re-upload (CARD-037)
            persisted_image_path_list = fields.get("persisted_image_path", [])
            persisted_image_path = persisted_image_path_list[0] if persisted_image_path_list else None
            # Get original filename for display on retry
            persisted_image_filename_list = fields.get("persisted_image_filename", [])
            persisted_image_filename = persisted_image_filename_list[0] if persisted_image_filename_list else None
        else:
            posted = submission.read(raw.decode("utf-8", "replace"))
            # For urlencoded, re-parse to extract fields for form re-population
            fields = urllib.parse.parse_qs(raw.decode("utf-8", "replace"))
            persisted_image_path_list = fields.get("persisted_image_path", [])
            persisted_image_path = persisted_image_path_list[0] if persisted_image_path_list else None
            persisted_image_filename_list = fields.get("persisted_image_filename", [])
            persisted_image_filename = persisted_image_filename_list[0] if persisted_image_filename_list else None
            image_path = None

        # Use persisted image path if no new image was uploaded (CARD-037 retry flow)
        if image_path is None and persisted_image_path:
            try:
                image_path = Path(persisted_image_path)
                # Use original filename from form field if available
                if not image_filename and persisted_image_filename:
                    image_filename = persisted_image_filename
                elif not image_filename and persisted_image_path:
                    # Fallback: extract from path if no stored filename
                    image_filename = Path(persisted_image_path).name
            except Exception as e:
                # If persisted path is invalid, continue without it
                pass

        # Extract image metadata for form display (CARD-031)
        # Extract even on errors to preserve suggestions and preview
        image_metadata_str = ""
        suggestions: list[tuple[int, int]] = []
        if image_path is not None:
            try:
                from nonogram.web import metadata as web_metadata
                img_metadata = web_metadata.extract_metadata(image_path)
                image_metadata_str = web_metadata.format_aspect_ratio(img_metadata.aspect_ratio)
                suggestions = web_metadata.suggest_dimensions(img_metadata)
            except (ImportError, Exception):
                # If metadata extraction fails or module unavailable, continue without suggestions
                pass

        # Prepare persisted image metadata for display (CARD-037)
        persisted_metadata: dict | None = None
        if image_path is not None:
            try:
                from nonogram.web import metadata as web_metadata
                from PIL import Image
                import base64
                import io
                img_metadata = web_metadata.extract_metadata(image_path)
                # Create data URL for client-side preview
                # Detect MIME type from file extension
                suffix = image_path.suffix.lower()
                mime_type = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "gif": "gif", "webp": "webp"}.get(suffix[1:] if suffix else "jpeg", "jpeg")
                with open(image_path, "rb") as f:
                    img_data = base64.b64encode(f.read()).decode("utf-8")
                    persisted_metadata = {
                        "width": img_metadata.width,
                        "height": img_metadata.height,
                        "imageSrc": f"data:image/{mime_type};base64,{img_data}",
                    }
            except Exception:
                pass

        try:
            # Move newly uploaded image to a stable cache location if we'll use it for CARD-037 retry
            # This allows the image to persist across retry attempts without re-upload.
            original_temp_path = newly_uploaded_image_path  # Keep original for cleanup
            if newly_uploaded_image_path is not None and newly_uploaded_image_path.exists():
                try:
                    import shutil
                    import uuid
                    # Copy temp file to a persistent cache that won't be auto-cleaned
                    # Use .cache/nonogram in user's home directory with a session ID
                    cache_dir = Path.home() / ".cache" / "nonogram"
                    cache_dir.mkdir(parents=True, exist_ok=True)
                    # Keep original filename but with a session ID to avoid collisions
                    session_id = str(uuid.uuid4())[:8]
                    cached_image_path = cache_dir / f"{session_id}_{newly_uploaded_image_path.name}"
                    shutil.copy2(newly_uploaded_image_path, cached_image_path)
                    # Update image_path to point to the cached copy for persisting
                    if image_path == newly_uploaded_image_path:
                        image_path = cached_image_path
                    # Keep newly_uploaded_image_path pointing to the original temp file so it gets deleted
                except Exception:
                    # If caching fails, just keep using the temp file
                    pass

            # Fix posted.request to include persisted image path (CARD-037 retry flow)
            if posted.request is not None and posted.request.image is None and image_path is not None:
                # Build a new request with the persisted image path
                from dataclasses import replace
                # Submission is not a dataclass, so create a new one with the updated request
                updated_request = replace(posted.request, image=image_path)
                posted = submission.Submission(request=updated_request, unreadable=posted.unreadable)
            if posted.request is None:
                self._fail_inline(
                    fields,
                    "The form could not be read.",
                    posted.unreadable,
                    image_metadata_str=image_metadata_str,
                    suggestions=suggestions,
                    persisted_image_path=str(image_path) if image_path else "",
                    persisted_image_metadata=persisted_metadata,
                    image_filename=image_filename or "",
                    persisted_image_filename=image_filename or "",
                )
                return
            try:
                puzzle = orchestrator.generate(posted.request)
                written = orchestrator.export_puzzle(puzzle)
            except NonogramError as error:
                self._fail_inline(
                    fields,
                    "nonogram refused this request.",
                    [str(error)],
                    image_metadata_str=image_metadata_str,
                    suggestions=suggestions,
                    persisted_image_path=str(image_path) if image_path else "",
                    persisted_image_metadata=persisted_metadata,
                    image_filename=image_filename or "",
                    persisted_image_filename=image_filename or "",
                )
                return
            except OSError as error:
                self._fail_inline(
                    fields,
                    "A file for this request could not be read or written.",
                    [str(error)],
                    image_metadata_str=image_metadata_str,
                    suggestions=suggestions,
                    persisted_image_path=str(image_path) if image_path else "",
                    persisted_image_metadata=persisted_metadata,
                    image_filename=image_filename or "",
                    persisted_image_filename=image_filename or "",
                )
                return
            # CARD-030: Render form with success result inline instead of redirect
            # CARD-037: Keep image file for retry attempts
            self._respond(
                HTTPStatus.OK,
                _HTML,
                pages.form_with_result(
                    fields,
                    pages.SUCCESS,
                    puzzle_name=puzzle.name,
                    seed=puzzle.seed,
                    paths=written,
                    image_metadata_str=image_metadata_str,
                    suggestions=suggestions,
                    persisted_image_path=str(image_path) if image_path else "",
                    persisted_image_metadata=persisted_metadata,
                    image_filename=image_filename or "",
                    persisted_image_filename=image_filename or "",
                ),
            )
        except Exception:
            pass
        finally:
            # Clean up temporary image file if it was created from multipart upload
            # but NOT if it's a persisted file from CARD-037 retry flow.
            # Only delete the newly uploaded file from THIS request, not persisted ones.
            if newly_uploaded_image_path is not None and newly_uploaded_image_path.exists():
                try:
                    newly_uploaded_image_path.unlink()
                except OSError:
                    # Ignore errors during cleanup
                    pass

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

    def _fail_inline(
        self,
        fields: _TYPE_CHECKED,
        summary: str,
        reasons: Sequence[str],
        image_metadata_str: str = "",
        suggestions: list[tuple[int, int]] | None = None,
        persisted_image_path: str = "",
        persisted_image_metadata: dict | None = None,
        image_filename: str = "",
        persisted_image_filename: str = "",
    ) -> None:
        """Render one failure with inline form (CARD-030).

        Like :meth:`_fail`, but returns the form page with the error result
        embedded inline instead of a standalone failure page. The form is
        re-populated with the submitted values so the user can correct and retry.

        The status is ``200``: the response *is* the report, and delivering it
        succeeded.

        CARD-037: Passes persisted_image_path and metadata so the uploaded file
        persists across retry attempts with a visible preview.
        """
        self._respond(
            HTTPStatus.OK,
            _HTML,
            pages.form_with_result(
                fields,
                pages.FAILURE,
                error_summary=summary,
                error_reasons=reasons,
                image_metadata_str=image_metadata_str,
                suggestions=suggestions or [],
                persisted_image_path=persisted_image_path,
                persisted_image_metadata=persisted_image_metadata,
                image_filename=image_filename,
                persisted_image_filename=persisted_image_filename,
            ),
        )

#: The route table: the form, and the submission it posts. Declared after the
#: class because its values are unbound methods of it, and keyed on the same
#: :data:`nonogram.web.pages.FORM_ACTION` the form's ``action`` is rendered
#: from, so the two cannot disagree about where a submission goes.
ROUTES: dict[tuple[str, str], Callable[[WebUIRequestHandler], None]] = {
    ("GET", "/"): WebUIRequestHandler._serve_form,
    ("POST", pages.FORM_ACTION): WebUIRequestHandler._generate,
}
