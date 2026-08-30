"""COMP-008 tests: the loopback bind, the absent auth check, and the router.

    AC-052  TestWebServer_BindsLoopbackOnlyByDefault
    AC-053  TestWebServer_ProcessesRequestsWithoutAuthentication

Both classes drive a *real* socket. That is not this suite's usual preference —
every other adapter test calls a function — but the two criteria are statements
about a socket, and there is no way to check "bound to 127.0.0.1 and refusing
every other interface" without one. In particular, AC-052 is deliberately
**not** checked by reading ``server.server_address`` back: that asserts the
constructor received the argument the test itself passed, which is equally true
of a server bound to ``0.0.0.0`` by a typo. What is checked is what the kernel
did with it.

How AC-052 is made non-vacuous
------------------------------
Proving a negative ("nothing answers on the LAN address") needs the test to
know its own method can detect a positive. So every non-loopback probe below is
run twice: once against the loopback-bound server under test, and once against
a *control* server this module binds to ``0.0.0.0`` on purpose. The control
must show that the host's non-loopback address is reachable and that the probe
can see a port genuinely occupied on it; if it cannot — a host with no
non-loopback interface, a firewall that swallows even the wildcard-bound server
— the test skips rather than passing on evidence it never gathered. A green run
therefore always means "the method worked, and the server under test failed the
probe."

Two independent probes are used, because they fail for different reasons:

* **connect** — open a TCP connection to ``<lan-ip>:<port>`` and try to speak
  HTTP. This is AC-052's own wording ("refuses connections arriving on any
  other interface"); on a host with a drop-style firewall the refusal shows up
  as a timeout rather than ``ECONNREFUSED``, and either way nothing served.
* **bind** — try to bind a fresh socket to ``<lan-ip>:<port>`` while the server
  holds that port. Succeeding proves the server never claimed that interface,
  and the control (which does claim it) must fail with ``EADDRINUSE``. This one
  is deterministic and firewall-independent, and it needs a socket built
  *without* ``SO_REUSEADDR`` — the option ``http.server`` sets by default is
  exactly what lets a specific-address bind slip past a wildcard-bound socket
  on BSD, which would make the probe answer "free" for a ``0.0.0.0`` server.

The rest of the module covers what the failure matrix in
``meta/kanban/cards/CARD-019.md`` declares (F-1 through F-12), the form page,
and the two boundaries guardrail G-4 draws.
"""

from __future__ import annotations

import ast
import http.client
import inspect
import re
import socket
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import closing, contextmanager
from pathlib import Path
from typing import NamedTuple

import pytest

from nonogram import cli, difficulty, export, web
from nonogram.web import handler, pages, server

# The ``web -> cli`` guard lives in the CLI's test module because that is where
# the ADR-0007 rank table lives; AC-059 exercises it here alongside its three
# siblings, so the module is imported rather than the guard reimplemented.
from tests import test_cli as cli_tests

#: Cap on any single request in this module. Loopback answers in microseconds;
#: this only bounds a genuinely stuck exchange so a failure is a failure rather
#: than a hung suite.
_PROBE_TIMEOUT_S = 3.0

#: Cap on an interface probe that is *expected* to find nothing. A refusal
#: comes back immediately, so this budget is only ever spent when the host
#: silently drops the packet instead — and both the control probe and the probe
#: under test use it, so the comparison the test rests on stays symmetric.
_INTERFACE_TIMEOUT_S = 1.5

#: How often the serve loop checks whether it has been asked to stop. The
#: stdlib default of 0.5s would be paid on every test's teardown here; the
#: server under test is never asked to be responsive, only to stop promptly.
_POLL_INTERVAL_S = 0.01

_WEB_SOURCES = sorted(Path(web.__file__).parent.rglob("*.py"))

#: The names and literals a challenge is actually written with (AC-053).
#: Symbolic names first, because that is how a status is normally spelled here;
#: the two integers catch the hand-written form.
_AUTH_STATUS_NAMES = frozenset(
    {"UNAUTHORIZED", "FORBIDDEN", "PROXY_AUTHENTICATION_REQUIRED"}
)
_AUTH_STATUS_CODES = frozenset({401, 403, "401", "403"})


def _docstring_nodes(tree: ast.Module) -> frozenset[int]:
    """``id()`` of every docstring constant in ``tree``.

    A source scan that cannot tell a docstring from code reads an explanation
    of why something is absent as evidence that it is present. Collected by
    identity rather than by value so that a *code* string which happens to
    equal a docstring is still examined.
    """
    docstrings: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(
            node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef
        ):
            continue
        first = node.body[0] if node.body else None
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            docstrings.add(id(first.value))
    return frozenset(docstrings)


def _auth_vocabulary_hits(source: str, name: str = "<source>") -> list[str]:
    """Every place ``source`` writes authentication vocabulary in *code*.

    Lifted out of ``test_the_package_contains_no_authentication_vocabulary`` so
    the scan itself can be shown to discriminate, against fabricated sources,
    rather than only ever being run over a package that is expected to be
    clean — a scan that had silently stopped matching would look identical.

    The header name is compared case-insensitively (AC-062). HTTP field names
    are case-insensitive (RFC 9110 §5.1), so ``send_header("www-authenticate",
    …)`` is the same challenge as ``WWW-Authenticate`` and the earlier
    case-sensitive ``in`` walked straight past it.
    """
    hits: list[str] = []
    tree = ast.parse(source)
    docstrings = _docstring_nodes(tree)
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in _AUTH_STATUS_NAMES:
            hits.append(f"{name}:{node.lineno} names HTTPStatus.{node.attr}")
        if isinstance(node, ast.Name) and node.id in _AUTH_STATUS_NAMES:
            hits.append(f"{name}:{node.lineno} names {node.id}")
        if isinstance(node, ast.Constant) and id(node) not in docstrings:
            if node.value in _AUTH_STATUS_CODES:
                hits.append(f"{name}:{node.lineno} uses the literal {node.value!r}")
            if isinstance(node.value, str) and "www-authenticate" in node.value.lower():
                hits.append(f"{name}:{node.lineno} writes a challenge header")
    return hits


def _web_component_imports() -> set[str]:
    """The ``nonogram`` components ``web/`` imports, read off disk.

    A local re-derivation rather than an import of ``tests.test_cli``'s
    machinery: this one answers "what does the package's own docstring claim
    about its imports" (AC-060), which is a different question from the ADR-0007
    rank rule that test file enforces, and the two must not degenerate together.
    """
    names: set[str] = set()
    for path in _WEB_SOURCES:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                names.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                base = node.module or ""
                if node.level:
                    base = f"nonogram.web.{base}" if base else "nonogram.web"
                if not base:
                    continue
                names.add(base)
                names.update(f"{base}.{alias.name}" for alias in node.names)
    return {
        parts[1]
        for name in names
        if (parts := name.split("."))[0] == "nonogram" and len(parts) > 1
    }


# --------------------------------------------------------------------------
# Running-server helpers
# --------------------------------------------------------------------------


class _Response(NamedTuple):
    """One response, fully read, so the connection can be closed before asserts.

    ``headers`` is the parsed ``HTTPMessage`` rather than ``dict(getheaders())``
    so that ``in`` and ``[]`` are case-insensitive, as HTTP field names are
    (RFC 9110 §5.1). A plain dict keyed on the wire spelling made
    ``"WWW-Authenticate" not in response.headers`` a check on one spelling out
    of many (AC-062); the message object makes it a check on the header.
    """

    status: int
    headers: http.client.HTTPMessage
    body: bytes


@contextmanager
def _running(server_obj: server.LoopbackHTTPServer) -> Iterator[server.LoopbackHTTPServer]:
    """Serve ``server_obj`` on a background thread for the block's duration."""
    thread = threading.Thread(
        target=server_obj.serve_forever, kwargs={"poll_interval": _POLL_INTERVAL_S}, daemon=True
    )
    thread.start()
    try:
        yield server_obj
    finally:
        server_obj.shutdown()
        server_obj.server_close()
        thread.join(timeout=5)


@pytest.fixture
def running_server() -> Iterator[server.LoopbackHTTPServer]:
    """The server under test, on a kernel-chosen port.

    Port 0 rather than :data:`server.DEFAULT_PORT` so the suite never races
    another test — or a developer's own ``nonogram serve`` — for a fixed port.
    The bind *address* is not parameterised, because it is not a parameter:
    that is the property AC-052 is about.
    """
    with _running(web.create_server(0)) as running:
        yield running


def _wildcard_control() -> server.LoopbackHTTPServer:
    """A control server bound to every interface — the probes' calibration.

    The same handler and the same class, differing only in the one thing under
    test. ``0.0.0.0`` is deliberate here and appears nowhere in ``src/``.
    """
    return server.LoopbackHTTPServer(("0.0.0.0", 0), handler.WebUIRequestHandler)


def _request(
    port: int,
    method: str = "GET",
    path: str = "/",
    headers: dict[str, str] | None = None,
    body: bytes | None = None,
) -> _Response:
    """One request over loopback, read to completion."""
    conn = http.client.HTTPConnection(server.LOOPBACK_HOST, port, timeout=_PROBE_TIMEOUT_S)
    try:
        conn.request(method, path, body=body, headers=headers or {})
        response = conn.getresponse()
        return _Response(response.status, response.headers, response.read())
    finally:
        conn.close()


def _raw_exchange(port: int, request: bytes) -> bytes:
    """Send bytes the ``http.client`` API cannot express; read until close.

    A send that fails part-way is not an error here: the stdlib answers an
    over-long request line or an excess of headers and closes the connection
    while the rest of the request is still on its way, which is the behaviour
    those cases are asserting. What was sent before the close is enough to have
    provoked the response, so the read proceeds either way.
    """
    with closing(
        socket.create_connection((server.LOOPBACK_HOST, port), timeout=_PROBE_TIMEOUT_S)
    ) as sock:
        try:
            sock.sendall(request)
        except (BrokenPipeError, ConnectionResetError):
            pass
        received = b""
        try:
            while chunk := sock.recv(4096):
                received += chunk
        except ConnectionResetError:
            pass
    return received


# --------------------------------------------------------------------------
# AC-052 — the loopback bind
# --------------------------------------------------------------------------


def _non_loopback_address() -> str | None:
    """This host's own non-loopback IPv4 address, or ``None`` if it has none.

    Found by asking the routing table which local address would be used to
    reach a public one. The socket is UDP and is never sent on, so this needs
    no network and produces no traffic; a machine with no route at all reports
    no address and the caller skips.
    """
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("8.8.8.8", 53))
        address = str(probe.getsockname()[0])
    except OSError:
        return None
    finally:
        probe.close()
    return None if address.startswith("127.") else address


def _serves_on(address: str, port: int) -> bool:
    """Whether an HTTP server answers at ``address:port`` from this host."""
    try:
        with closing(
            socket.create_connection((address, port), timeout=_INTERFACE_TIMEOUT_S)
        ) as sock:
            sock.sendall(b"GET / HTTP/1.0\r\n\r\n")
            return sock.recv(16).startswith(b"HTTP/")
    except OSError:
        # ``ConnectionRefusedError`` (the port is closed on that interface) and
        # ``TimeoutError`` (a drop-style firewall) are the same answer here:
        # nothing served.
        return False


def _port_is_free_on(address: str, port: int) -> bool:
    """Whether ``address:port`` can still be bound while a server runs.

    Deliberately a bare socket with no ``SO_REUSEADDR``: with that option set —
    and ``http.server`` sets it — BSD lets a specific-address bind succeed even
    though a wildcard socket already holds the port, which would make this
    probe answer "free" for a ``0.0.0.0`` server and destroy the point of it.
    The control in the test below is what proves the probe still discriminates
    on this host.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((address, port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


class TestWebServer_BindsLoopbackOnlyByDefault:
    """AC-052 — *given* the web UI server started with its default
    configuration, *when* it binds its listening socket, *then* the socket is
    bound to 127.0.0.1 and refuses connections arriving on any other interface.

    "Default configuration" is the whole configuration: there is no host option
    to leave at a default, which
    :meth:`test_no_api_in_the_package_can_widen_the_bind_address` pins.
    """

    def test_loopback_is_served(self, running_server: server.LoopbackHTTPServer) -> None:
        """The positive half — it does listen, so the negatives mean something."""
        assert _serves_on(server.LOOPBACK_HOST, running_server.server_port) is True

    def test_no_other_interface_is_served(
        self, running_server: server.LoopbackHTTPServer
    ) -> None:
        """Nothing answers on this host's LAN address, though the control does."""
        address = _non_loopback_address()
        if address is None:
            pytest.skip("host has no non-loopback IPv4 address to probe")

        with _running(_wildcard_control()) as control:
            if not _serves_on(address, control.server_port):
                pytest.skip(f"{address} is unreachable from this host even when bound")
            assert _serves_on(address, running_server.server_port) is False

    def test_the_port_stays_free_on_every_other_interface(
        self, running_server: server.LoopbackHTTPServer
    ) -> None:
        """The firewall-independent half: the kernel never gave it that address.

        A port a server has claimed cannot be bound again; one it never claimed
        can. The control binds ``0.0.0.0`` and must therefore make the same
        probe fail — if it does not, this host cannot tell the two cases apart
        and the test says so instead of passing.
        """
        address = _non_loopback_address()
        if address is None:
            pytest.skip("host has no non-loopback IPv4 address to probe")

        control = _wildcard_control()
        try:
            if _port_is_free_on(address, control.server_port):
                pytest.skip("this host does not refuse a specific bind over a wildcard one")
        finally:
            control.server_close()

        assert _port_is_free_on(address, running_server.server_port) is True

    def test_no_api_in_the_package_can_widen_the_bind_address(self) -> None:
        """The bind address is a constant, not an argument (ADR-0020, F-9).

        AC-052 is only a property of the *code* if there is no supported way to
        call it that gives a different answer. ``create_server`` takes a port
        and nothing else, and ``serve_on`` takes the server that port produced
        — a ``host=`` keyword on either would move the criterion out of the
        server and into every call site.

        Both are pinned by exact signature rather than by "has no host
        argument", and the whole public surface is then swept for a
        host-shaped parameter, so a *third* entry point added later is covered
        without this test being edited.
        """
        assert list(inspect.signature(web.create_server).parameters) == ["port"]
        assert list(inspect.signature(web.serve_on).parameters) == ["server"]

        for name in web.__all__:
            member = getattr(web, name)
            if not callable(member):
                continue
            parameters = set(inspect.signature(member).parameters)
            assert not parameters & {"host", "address", "bind", "interface"}, name

    def test_no_module_in_the_package_names_another_bind_address(self) -> None:
        """And no module reaches around that API either.

        The signature check above covers the front door; this covers a literal
        ``"0.0.0.0"`` or an ``INADDR_ANY`` appearing anywhere in ``src/`` — the
        way a "just for testing" widening actually gets in.

        ``_WEB_SOURCES`` is asserted non-empty first (AC-059): it is a glob
        evaluated once at import, and a loop over an empty list reports green
        while checking nothing.
        """
        assert _WEB_SOURCES, "no web adapter sources found"
        for path in _WEB_SOURCES:
            source = path.read_text(encoding="utf-8")
            for token in ("0.0.0.0", "INADDR_ANY", "getfqdn", "gethostname"):
                assert token not in source, f"{path.name} mentions {token}"

    def test_the_loopback_host_constant_is_loopback(self) -> None:
        """Pins the constant, so a typo cannot slip past the probes above.

        ``0.0.0.0`` would fail them; ``127.0.0.2``, on a host where the whole
        127/8 block is local, might not. This is the cheap check for that class
        of edit and a complement to the behavioural tests, never a substitute —
        alone it would be exactly the read-back assertion AC-052 must not rest
        on.
        """
        assert server.LOOPBACK_HOST == "127.0.0.1"


# --------------------------------------------------------------------------
# AC-053 — no authentication
# --------------------------------------------------------------------------


class TestWebServer_ProcessesRequestsWithoutAuthentication:
    """AC-053 — *given* a request to any web UI endpoint with no Authorization
    header or session credentials, *when* the request is handled, *then* it is
    processed normally, since the server enforces no authentication check.

    The absence of the check is the decision (NFR-003, BCON-0001), so it is
    tested as an absence: no response can be a challenge, and the presence of a
    credential cannot change a response at all.
    """

    def test_a_bare_request_is_served(self, running_server: server.LoopbackHTTPServer) -> None:
        """No Authorization header, no cookie: the form comes back."""
        response = _request(running_server.server_port)

        assert response.status == 200
        assert b"<form" in response.body

    @pytest.mark.parametrize(
        "headers",
        [
            pytest.param({}, id="nothing"),
            pytest.param({"Authorization": "Bearer nonsense"}, id="bearer"),
            pytest.param({"Authorization": "Basic bm9wZTpub3Bl"}, id="basic"),
            pytest.param({"Cookie": "session=whatever"}, id="cookie"),
        ],
    )
    def test_credentials_change_nothing(
        self, running_server: server.LoopbackHTTPServer, headers: dict[str, str]
    ) -> None:
        """A credential is not merely accepted — it is not read.

        Same status, same bytes, whether a credential is sent, a wrong one is
        sent, or none is. A server that validated credentials and happened to
        accept these would still be one this criterion forbids.
        """
        baseline = _request(running_server.server_port)
        response = _request(running_server.server_port, headers=headers)

        assert response.status == baseline.status == 200
        assert response.body == baseline.body

    def test_no_endpoint_ever_challenges(
        self, running_server: server.LoopbackHTTPServer
    ) -> None:
        """"Any endpoint" includes the ones that fail: a 404 is not a 401.

        The unauthenticated path has to stay unauthenticated where it is least
        watched — the miss case — so the routed path, an unrouted path and the
        form's own action are all checked for the two statuses and the one
        header that would mean an auth check had appeared.
        """
        for path in ("/", "/no-such-page", pages.FORM_ACTION):
            response = _request(running_server.server_port, path=path)

            assert response.status not in (401, 403), path
            assert "WWW-Authenticate" not in response.headers, path

    def test_the_package_contains_no_authentication_vocabulary(self) -> None:
        """Read off the source: no auth machinery is written down anywhere.

        A deliberately *cheap complement* to the three behavioural tests above,
        and it does not claim to be more than that. It cannot see a challenge
        assembled at runtime — ``HTTPStatus(200 + 201)`` and
        ``"WWW-Auth" + "enticate"`` pass it unchanged, which is precisely why
        AC-053 rests on the requests above and not on this. What it does catch
        is the realistic version: a later card reaching for ``401`` or
        ``HTTPStatus.UNAUTHORIZED`` by hand.

        Read from the AST rather than from the raw text, because prose about
        the absence (this docstring included, and the ones in ``handler.py``
        that explain why there is no ``403``) is exactly what a source-text
        scan cannot tell apart from the thing itself. Docstrings are therefore
        excluded by node identity and only real code is examined: status
        *literals*, attribute names, and the header string as it would actually
        be written. The earlier substring form banned the bare strings
        ``"401"``/``"403"`` anywhere in the package, prose included, so its own
        explanation would have tripped it.

        What that does **not** buy is immunity from a benign *code* literal:
        ``_MAX_BODY_BYTES = 403`` still fails this test, because a status in
        this package is written as a plain integer and there is no way to tell
        one position from another without teaching the scan the shape of every
        call that could carry one. Two integers out of the whole range are
        affected and the failure message names the line, so the answer is to
        spell that constant differently — never to widen this scan, which is
        the edit that would quietly end the guard.

        The scan itself lives in :func:`_auth_vocabulary_hits` so that
        ``TestAuthScan_IsCaseInsensitiveOnHeaderNames`` can show it firing on a
        fabricated source; run only over a package expected to be clean, a scan
        that had stopped matching would look exactly like this one passing.
        """
        assert _WEB_SOURCES, "no web adapter sources found"
        for path in _WEB_SOURCES:
            hits = _auth_vocabulary_hits(path.read_text(encoding="utf-8"), path.name)
            assert not hits, hits[0]


# --------------------------------------------------------------------------
# The router and the declared failure behaviour (the card's failure matrix)
# --------------------------------------------------------------------------


def test_the_route_table_is_keyed_on_method_and_path() -> None:
    """The router's shape, which CARD-020 extends rather than replaces."""
    assert set(handler.ROUTES) == {("GET", "/")}


def test_a_query_string_does_not_change_the_route(
    running_server: server.LoopbackHTTPServer,
) -> None:
    """``/?x=1`` is the ``/`` route: the table matches paths, not URLs."""
    assert _request(running_server.server_port, path="/?anything=1").status == 200


@pytest.mark.parametrize(
    "path",
    [
        pytest.param("/no-such-page", id="unknown"),
        pytest.param("/favicon.ico", id="favicon"),
        # The form's own action, CARD-020's POST endpoint: it has no GET route
        # today and must not quietly acquire one.
        pytest.param("/generate", id="the-post-endpoint-has-no-get"),
        # A traversal attempt, to show nothing here maps a path onto a file:
        # the handler does not inherit ``SimpleHTTPRequestHandler``, so this is
        # a miss like any other rather than a read.
        pytest.param("/../pyproject.toml", id="traversal"),
        # Markup in the path, because the 404 body echoes the path back. Until
        # this case existed the `b"<"` assertion below was vacuous: not one of
        # the four paths above contains a `<`, so it held equally for a handler
        # that reflected markup verbatim — which is what the handler did.
        pytest.param("/<script>alert(document.domain)</script>", id="markup"),
    ],
)
def test_an_unrouted_path_is_a_plain_404(
    running_server: server.LoopbackHTTPServer, path: str
) -> None:
    """F-7: one short text response, no traceback, no file, no markup echoed.

    ``text/plain`` alone makes a reflected script inert only for a client that
    believes the header, so the body is escaped *and* the response says
    ``nosniff``: two independent reasons rather than one.
    """
    response = _request(running_server.server_port, path=path)

    assert response.status == 404
    assert response.headers["Content-Type"] == "text/plain; charset=utf-8"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert b"<" not in response.body
    assert b">" not in response.body


def test_the_markup_case_really_reaches_the_handler(
    running_server: server.LoopbackHTTPServer,
) -> None:
    """Guard the guard: the escaped path is echoed, not silently dropped.

    ``b"<" not in body`` above would also hold for a handler that stopped
    echoing the path at all, or for a request the stdlib rejected before the
    router ran — and neither would be evidence about escaping. This shows the
    path arrived, was echoed, and arrived escaped.
    """
    response = _request(running_server.server_port, path="/<script>")

    assert response.status == 404
    assert b"&lt;script&gt;" in response.body


def test_the_server_keeps_serving_after_a_miss(
    running_server: server.LoopbackHTTPServer,
) -> None:
    """F-7: a 404 is not a crash — the next request is served normally."""
    _request(running_server.server_port, path="/no-such-page")

    assert _request(running_server.server_port).status == 200


def test_post_is_not_implemented_in_this_card(
    running_server: server.LoopbackHTTPServer,
) -> None:
    """F-5, guardrail G-5: submission is CARD-020's, and says so honestly.

    ``BaseHTTPRequestHandler`` answers a method with no ``do_*`` with 501, so
    the form posts to an endpoint that reports itself unimplemented rather than
    to one this card half-built.
    """
    response = _request(
        running_server.server_port, method="POST", path=pages.FORM_ACTION, body=b"size=10"
    )

    assert response.status == 501
    assert not hasattr(handler.WebUIRequestHandler, "do_POST")


def test_a_body_sent_with_a_get_is_never_read(
    running_server: server.LoopbackHTTPServer,
) -> None:
    """F-5's numeric bound: exactly zero bytes of request body are read.

    Sent raw so the body really is on the wire, with a ``Content-Length`` a
    body-reading handler would have to honour. This one answers from the route
    table without touching ``rfile`` — and, the part that matters, closes the
    connection afterwards, so the unread body cannot be parsed as a second
    request. Exactly one response comes back, not two.
    """
    body = b"x" * 4096
    request = (
        b"GET / HTTP/1.1\r\nHost: 127.0.0.1\r\nContent-Length: %d\r\n\r\n" % len(body)
    ) + body

    received = _raw_exchange(running_server.server_port, request)

    assert received.startswith(b"HTTP/1.0 200 OK")
    assert received.count(b"HTTP/1.0 200 OK") == 1


@pytest.mark.parametrize(
    ("request_bytes", "status"),
    [
        # F-4: an unparseable request line.
        pytest.param(b"this is not a request line\r\n\r\n", b" 400 ", id="malformed-line"),
        # F-4: a version token that is not a version at all.
        pytest.param(b"GET / HTTP/ABC\r\n\r\n", b" 400 ", id="unparseable-version"),
        # F-10: a *well-formed* version this server does not speak. This is the
        # case that refuted the matrix's original F-4 row, which declared 400
        # for it. The stdlib parses "9.9" fine and answers 505 — a different
        # status for a different failure, and the row now says so.
        pytest.param(b"GET / HTTP/9.9\r\n\r\n", b" 505 ", id="unsupported-version"),
        # F-4's request-line bound, comfortably past it. The exact edge is
        # pinned by test_the_declared_size_bounds_are_exact below.
        pytest.param(
            b"GET /" + b"x" * 70000 + b" HTTP/1.0\r\n\r\n", b" 414 ", id="over-long-uri"
        ),
        # F-4's header-count bound, comfortably past it (the edge is 99/100).
        pytest.param(
            b"GET / HTTP/1.0\r\n" + b"".join(b"X-%d: 1\r\n" % n for n in range(150)) + b"\r\n",
            b" 431 ",
            id="too-many-headers",
        ),
        # F-4's third bound and the *second* cause of a 431: one header line
        # over _MAXLINE ("Line too long"), which is a different failure from
        # too many headers wearing the same status.
        pytest.param(
            b"GET / HTTP/1.0\r\nX-Long: " + b"a" * 70000 + b"\r\n\r\n",
            b" 431 ",
            id="over-long-header-value",
        ),
    ],
)
def test_the_stdlib_rejects_a_bad_request_line_before_the_router(
    running_server: server.LoopbackHTTPServer, request_bytes: bytes, status: bytes
) -> None:
    """F-4 and F-10: each declared status, pinned against a live socket.

    All six are ``BaseHTTPRequestHandler.parse_request``'s answers rather than
    this card's, and an inherited default that has been read is still a
    declaration — which is the reason to pin it: the matrix originally declared
    ``400`` for an unsupported HTTP version and the stdlib answers ``505``. A
    row asserted from memory rather than from the wire is how that survived,
    so every declared status is exercised here and every declared *bound* is
    exercised at its edge in the test below.
    """
    received = _raw_exchange(running_server.server_port, request_bytes)

    assert status in received, received[:120]


def _request_line_of(total_bytes: int) -> bytes:
    """A request line of exactly ``total_bytes``, CRLF included."""
    suffix = b" HTTP/1.0\r\n"
    line = b"GET /" + b"x" * (total_bytes - len(b"GET /") - len(suffix)) + suffix
    assert len(line) == total_bytes
    return line


def _header_line_of(total_bytes: int) -> bytes:
    """One header line of exactly ``total_bytes``, CRLF included."""
    name = b"X-Long: "
    line = name + b"a" * (total_bytes - len(name) - len(b"\r\n")) + b"\r\n"
    assert len(line) == total_bytes
    return line


@pytest.mark.parametrize(
    ("request_bytes", "status", "note"),
    [
        # Request line: the largest accepted line is 65536 bytes including its
        # CRLF. Accepted means *routed* — "/xxx..." is no route, so the honest
        # answer is a 404 from this card's own router, which is also the proof
        # that the request got past parse_request at all.
        pytest.param(_request_line_of(65536) + b"\r\n", b" 404 ", "accepted", id="uri-at-limit"),
        pytest.param(_request_line_of(65537) + b"\r\n", b" 414 ", "refused", id="uri-over-limit"),
        # Header count: _MAXHEADERS is 100, but http.client.parse_headers
        # appends the terminating CRLF to the very list it length-checks, so
        # the ceiling on real header *fields* is 99. This is the bound the
        # matrix declared as "<= 100" and the wire refuted twice.
        pytest.param(
            b"GET / HTTP/1.0\r\n" + b"".join(b"X-%d: 1\r\n" % n for n in range(99)) + b"\r\n",
            b" 200 ",
            "accepted",
            id="99-headers",
        ),
        pytest.param(
            b"GET / HTTP/1.0\r\n" + b"".join(b"X-%d: 1\r\n" % n for n in range(100)) + b"\r\n",
            b" 431 ",
            "refused",
            id="100-headers",
        ),
        # Header line length: the same _MAXLINE as the request line, applied
        # per header line. A single over-long *value* is the second, distinct
        # cause of a 431.
        pytest.param(
            b"GET / HTTP/1.0\r\n" + _header_line_of(65536) + b"\r\n",
            b" 200 ",
            "accepted",
            id="header-line-at-limit",
        ),
        pytest.param(
            b"GET / HTTP/1.0\r\n" + _header_line_of(65537) + b"\r\n",
            b" 431 ",
            "refused",
            id="header-line-over-limit",
        ),
    ],
)
def test_the_declared_size_bounds_are_exact(
    running_server: server.LoopbackHTTPServer,
    request_bytes: bytes,
    status: bytes,
    note: str,
) -> None:
    """F-4's three numeric bounds, each probed on both sides of its edge.

    A bound is only declared if something would notice it moving. The tests
    above send 70000 bytes and 150 headers — comfortably past every limit, and
    therefore green for *any* limit at or below those figures, which is how the
    matrix came to declare "headers <= 100" when the wire refuses 100. Each
    bound is pinned here at N (accepted) and N+1 (refused) instead, so the
    declaration and the behaviour cannot drift apart again.

    The sizes are counted in *whole line bytes, CRLF included*, because that is
    what the standard library measures: ``readline(_MAXLINE + 1)`` and then
    ``len(line) > _MAXLINE``.
    """
    received = _raw_exchange(running_server.server_port, request_bytes)

    assert status in received, (note, received[:120])


def test_a_client_that_disconnects_does_not_take_the_server_down(
    running_server: server.LoopbackHTTPServer,
) -> None:
    """F-3: exactly one connection is affected and the server keeps serving."""
    sock = socket.create_connection(
        (server.LOOPBACK_HOST, running_server.server_port), timeout=_PROBE_TIMEOUT_S
    )
    sock.sendall(b"GET / HTTP/1.0\r\n\r\n")
    sock.close()  # gone before the response is read

    assert _request(running_server.server_port).status == 200


def test_a_lost_connection_is_reported_without_a_traceback(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """F-3's other half: a dropped client is one line, a real bug stays loud.

    Driven directly rather than through a socket, because a genuine
    mid-response disconnect is a race — whether the kernel has torn the
    connection down before the handler's ``write`` returns is not something a
    test can pin. What *is* pinnable is the branch that decides, so it is
    exercised with one of each kind of exception it has to tell apart.
    """
    quiet = web.create_server(0)
    try:
        try:
            raise BrokenPipeError(32, "Broken pipe")
        except BrokenPipeError:
            quiet.handle_error(object(), ("127.0.0.1", 1))
        captured = capsys.readouterr()
        assert "disconnected" in captured.err
        assert "Traceback" not in captured.err

        try:
            raise ValueError("a real bug in the handler")
        except ValueError:
            quiet.handle_error(object(), ("127.0.0.1", 1))
        assert "Traceback" in capsys.readouterr().err
    finally:
        quiet.server_close()


def test_a_busy_port_raises_rather_than_rebinding() -> None:
    """F-2: no retry, no port scan, no silent share of a live socket."""
    first = web.create_server(0)
    try:
        with pytest.raises(OSError):
            web.create_server(first.server_port)
    finally:
        first.server_close()


def test_an_out_of_range_port_raises_the_stdlib_overflow_error() -> None:
    """F-1: the reason ``cli._run_serve`` catches ``OverflowError`` as well.

    CPython's socket layer rejects a port outside 0..65535 with an
    ``OverflowError``, which is *not* an ``OSError`` — a catch written for bind
    failures alone would let ``--port 99999`` reach the user as a traceback.
    """
    with pytest.raises(OverflowError):
        web.create_server(99999)


def test_the_server_releases_the_port_when_it_stops() -> None:
    """F-6: closing releases the socket, so a restart on the same port works."""
    first = web.create_server(0)
    port = first.server_port
    first.server_close()

    reopened = web.create_server(port)
    try:
        assert reopened.server_port == port
    finally:
        reopened.server_close()


# --------------------------------------------------------------------------
# F-6 — the serve loop itself (shutdown and port release)
# --------------------------------------------------------------------------


class _StubServer:
    """A server that only knows how to fail, so the loop's own paths are visible.

    :func:`web.serve_on` is three lines of *policy* — swallow the interrupt,
    close the socket whatever happens — and every one of them is about an
    outcome a real socket cannot be asked to produce on cue. Driving a stub is
    what makes them checkable: without this, ``serve_on``'s body was never
    executed by the suite at all, and deleting the whole ``try/except/finally``
    left every test green.
    """

    server_port = 12345

    def __init__(self, outcome: BaseException | None) -> None:
        self._outcome = outcome
        self.closed = 0
        self.served = 0

    def serve_forever(self) -> None:
        self.served += 1
        if self._outcome is not None:
            raise self._outcome

    def server_close(self) -> None:
        self.closed += 1


def test_an_interrupt_stops_serving_without_a_traceback(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """F-6: Ctrl-C is a deliberate stop — swallowed, and the port released.

    The ``KeyboardInterrupt`` must not escape (``nonogram serve`` exits 0, not
    with a traceback) and ``server_close`` must still run, or the listening
    socket outlives the process's intent to stop.
    """
    stub = _StubServer(KeyboardInterrupt())

    assert web.serve_on(stub) is None  # type: ignore[arg-type]

    assert stub.served == 1
    assert stub.closed == 1
    assert "127.0.0.1:12345" in capsys.readouterr().out


def test_an_unexpected_failure_still_releases_the_port() -> None:
    """F-6's other half: the ``finally`` covers every path out, not just Ctrl-C.

    An exception ``serve_on`` does not expect is a bug and stays loud — it is
    re-raised, not swallowed like the interrupt — but the port is released on
    the way out regardless, so a dying process does not leave the socket held.
    """
    stub = _StubServer(ValueError("a bug inside the serve loop"))

    with pytest.raises(ValueError):
        web.serve_on(stub)  # type: ignore[arg-type]

    assert stub.closed == 1


def test_a_clean_return_from_the_loop_also_releases_the_port() -> None:
    """``shutdown()`` from another thread returns normally; the port still goes."""
    stub = _StubServer(None)

    assert web.serve_on(stub) is None  # type: ignore[arg-type]

    assert stub.closed == 1


# --------------------------------------------------------------------------
# F-11 — the idle connection timeout
# --------------------------------------------------------------------------

#: The timeout the *test's* handlers use. The shipped one is 30s (asserted
#: below); waiting that out in the suite would be absurd, so the boundary is
#: exercised at a scaled-down value and the shipped constant is pinned
#: separately.
_TEST_IDLE_TIMEOUT_S = 0.25

#: How many silent connections the probe opens. Enough that a leak is a
#: measurable jump in ``threading.active_count()`` rather than a rounding
#: error, small enough to be instant.
_SILENT_CONNECTIONS = 8


class _ImpatientHandler(handler.WebUIRequestHandler):
    """The shipped handler with its timeout scaled down for the suite."""

    timeout = _TEST_IDLE_TIMEOUT_S


class _PatientHandler(handler.WebUIRequestHandler):
    """The handler *without* a timeout — the state this card shipped in.

    Present as the probe's control: it is what the thread-count measurement
    must be able to catch, and if it does not, the measurement proves nothing
    about the fixed handler either.
    """

    timeout = None


@contextmanager
def _silent_connections(port: int, count: int) -> Iterator[list[socket.socket]]:
    """Open ``count`` connections that never send a byte, and close them after."""
    sockets = [
        socket.create_connection((server.LOOPBACK_HOST, port), timeout=_PROBE_TIMEOUT_S)
        for _ in range(count)
    ]
    try:
        yield sockets
    finally:
        for sock in sockets:
            sock.close()


def _threads_settle_to(baseline: int, budget_s: float) -> bool:
    """Whether the process's live-thread count is back to ``baseline`` in time."""
    deadline = time.monotonic() + budget_s
    while threading.active_count() > baseline and time.monotonic() < deadline:
        time.sleep(0.01)
    return threading.active_count() <= baseline


def test_the_shipped_handler_declares_an_idle_timeout() -> None:
    """F-11: the bound the matrix declares is the one the code carries.

    A class attribute rather than a call: ``StreamRequestHandler.setup`` reads
    ``self.timeout`` and applies it with ``settimeout``. ``None`` — the value
    before this fix — means the request-line read blocks forever.
    """
    assert handler.WebUIRequestHandler.timeout == handler.IDLE_TIMEOUT_S
    assert handler.IDLE_TIMEOUT_S == 30


def test_a_silent_connection_is_dropped_instead_of_holding_a_thread() -> None:
    """F-11: a client that connects and says nothing does not hold a thread.

    Run against a control first, exactly as the AC-052 probes are. A handler
    with no timeout must *fail* this measurement — otherwise the measurement
    cannot see a held thread and its passing against the fixed handler would
    mean nothing. If the control settles anyway (a host that tears the
    connections down for its own reasons) the test skips rather than passing on
    evidence it never gathered.

    ``ThreadingHTTPServer`` gives every accepted connection its own unbounded
    daemon thread, so "held" is directly observable as
    ``threading.active_count()`` never coming back down.
    """
    control = server.LoopbackHTTPServer((server.LOOPBACK_HOST, 0), _PatientHandler)
    with _running(control):
        # Counted with the serve loop already running, so the baseline is
        # "this server, idle" and the only thing the probe can move is the
        # per-connection handler threads.
        baseline = threading.active_count()
        with _silent_connections(control.server_port, _SILENT_CONNECTIONS):
            held = not _threads_settle_to(baseline, budget_s=4 * _TEST_IDLE_TIMEOUT_S)
    if not held:
        pytest.skip("this host does not keep an untimed idle connection open")

    under_test = server.LoopbackHTTPServer((server.LOOPBACK_HOST, 0), _ImpatientHandler)
    with _running(under_test):
        baseline = threading.active_count()
        with _silent_connections(under_test.server_port, _SILENT_CONNECTIONS):
            assert _threads_settle_to(baseline, budget_s=20 * _TEST_IDLE_TIMEOUT_S)

        assert _request(under_test.server_port).status == 200


def test_an_idle_connection_is_closed_from_the_server_side() -> None:
    """F-11, the client's view: the socket is closed, not merely forgotten.

    A thread count returning to baseline could in principle mean the handler
    thread ended while the connection lingered. What the client sees is the
    stronger statement, and the one a browser's abandoned preconnect actually
    depends on: end-of-file, from the server, without the client having sent
    anything at all.
    """
    quiet = server.LoopbackHTTPServer((server.LOOPBACK_HOST, 0), _ImpatientHandler)
    with _running(quiet):
        with closing(
            socket.create_connection(
                (server.LOOPBACK_HOST, quiet.server_port), timeout=_PROBE_TIMEOUT_S
            )
        ) as sock:
            started = time.monotonic()
            assert sock.recv(64) == b""
            elapsed = time.monotonic() - started

        assert elapsed < _PROBE_TIMEOUT_S


# --------------------------------------------------------------------------
# F-12 — the Host header
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "host",
    [
        pytest.param("127.0.0.1", id="bare-ipv4"),
        pytest.param("127.0.0.1:{port}", id="ipv4-with-port"),
        pytest.param("localhost", id="bare-name"),
        pytest.param("localhost:{port}", id="name-with-port"),
        pytest.param("[::1]", id="bare-ipv6"),
        pytest.param("[::1]:{port}", id="ipv6-with-port"),
    ],
)
def test_a_loopback_host_header_is_served(
    running_server: server.LoopbackHTTPServer, host: str
) -> None:
    """F-12: every name a browser can legitimately reach this server by works.

    The port is part of the header and is deliberately *not* compared: it is
    whatever ``--port`` chose, and a browser echoes back whatever it dialled.
    Only the name is the access-control question.
    """
    response = _request(
        running_server.server_port,
        headers={"Host": host.format(port=running_server.server_port)},
    )

    assert response.status == 200
    assert b"<form" in response.body


@pytest.mark.parametrize(
    "host",
    [
        pytest.param("evil.example.com", id="foreign-name"),
        pytest.param("evil.example.com:8765", id="foreign-name-with-port"),
        # The shape a rebinding attack actually arrives in: a name the attacker
        # controls, resolving to 127.0.0.1, so the connection is genuinely
        # loopback and the bind address alone says nothing about it.
        pytest.param("rebind.attacker.test", id="rebound-name"),
        # Prefix/suffix games against a naive substring check.
        pytest.param("127.0.0.1.evil.example.com", id="suffixed-loopback"),
        pytest.param("notlocalhost", id="prefixed-name"),
        pytest.param("", id="empty"),
        # A ``Host`` is an authority, not a URL. ``urlsplit`` reads the host
        # component of all three of these as loopback — which it genuinely is,
        # so none of them was ever a hole — but a header carrying userinfo or a
        # path is not a host name, and accepting it would make the set of
        # accepted header *values* unbounded while F-12 declares exactly three
        # accepted *names*. The reversal that would be a hole,
        # ``127.0.0.1@evil.example.com``, was already refused and stays here to
        # prove the narrowing did not replace the parse with a substring test.
        pytest.param("user:pass@127.0.0.1", id="userinfo"),
        pytest.param("evil.example.com@127.0.0.1", id="userinfo-lookalike"),
        pytest.param("127.0.0.1/../evil", id="path-component"),
        pytest.param("127.0.0.1@evil.example.com", id="reversed-userinfo"),
    ],
)
def test_a_foreign_host_header_is_refused_before_routing(
    running_server: server.LoopbackHTTPServer, host: str
) -> None:
    """F-12: a request naming another host is answered 400 and never routed.

    This is the half of the access control a loopback bind cannot provide. The
    kernel stops a *network* peer, but the browser the user is already running
    is on this host, and any page it loads can aim a request at
    ``http://127.0.0.1:<port>/`` — under a hostname the attacker controls,
    which is what makes the reply readable to that page.

    Refused with ``400``, not ``401``/``403``: nothing was authenticated and
    nothing was forbidden to a principal. The request named a host this server
    does not answer to, which makes it malformed (AC-053 is untouched — see
    ``test_no_endpoint_ever_challenges``).
    """
    response = _request(running_server.server_port, headers={"Host": host})

    assert response.status == 400
    assert response.status not in (401, 403)
    assert "WWW-Authenticate" not in response.headers
    assert b"<form" not in response.body


def test_a_refused_host_is_not_echoed_as_markup(
    running_server: server.LoopbackHTTPServer,
) -> None:
    """The rejection body names the host, and escapes it, exactly as the 404 does."""
    response = _request(
        running_server.server_port, headers={"Host": "<script>alert(1)</script>"}
    )

    assert response.status == 400
    assert b"&lt;script&gt;" in response.body
    assert b"<" not in response.body


@pytest.mark.parametrize(
    "version",
    [
        pytest.param(b"HTTP/1.0", id="http-1.0"),
        # RFC 7230 §5.4 requires 400 here. The leniency is applied to *every*
        # version on purpose, and the row says so rather than resting on the
        # HTTP/1.0 half alone: it is stated here so a later card that reads
        # "HTTP/1.0 clients may omit it" does not conclude 1.1 is refused.
        pytest.param(b"HTTP/1.1", id="http-1.1"),
    ],
)
def test_a_request_with_no_host_header_at_all_is_served(
    running_server: server.LoopbackHTTPServer, version: bytes
) -> None:
    """F-12's deliberate gap: an absent ``Host`` passes, on any version.

    Sent raw, because ``http.client`` always supplies the header. The check is
    against the browser-mediated attack, and a browser cannot suppress the
    header — ``Host`` is a forbidden header name to ``fetch``/XHR, so an absent
    one is never the attacker's shape. Refusing a request that omits one would
    break an HTTP/1.0 client (``curl --http1.0``, and this module's own AC-052
    interface probes, which is the evidence chain that would break) for no
    security gain.
    """
    received = _raw_exchange(running_server.server_port, b"GET / " + version + b"\r\n\r\n")

    assert received.startswith(b"HTTP/1.0 200 OK")


@pytest.mark.parametrize(
    ("hosts", "expected"),
    [
        # RFC 7230 §5.4: more than one Host field is a bad request. Both orders
        # are checked because reading only the *first* header accepts one of
        # them and refuses the other — which is exactly the asymmetry this
        # test exists to remove.
        pytest.param((b"127.0.0.1", b"evil.example.com"), b"HTTP/1.0 400", id="local-then-foreign"),
        pytest.param((b"evil.example.com", b"127.0.0.1"), b"HTTP/1.0 400", id="foreign-then-local"),
        # Two *different* loopback names still disagree about which name the
        # request used, so they are refused too.
        pytest.param((b"127.0.0.1", b"localhost"), b"HTTP/1.0 400", id="two-loopback-names"),
        # One value repeated says nothing new — served.
        pytest.param((b"127.0.0.1", b"127.0.0.1"), b"HTTP/1.0 200", id="repeated-identical"),
    ],
)
def test_duplicate_host_headers_are_refused_unless_they_agree(
    running_server: server.LoopbackHTTPServer, hosts: tuple[bytes, ...], expected: bytes
) -> None:
    """F-12: *every* ``Host`` is read, not just the first.

    Sent raw, because ``http.client``'s header mapping cannot express a
    repeated field. Not browser-reachable — page-controlled JavaScript cannot
    add a second ``Host`` any more than it can remove the first — and there is
    no proxy in front of a loopback socket to disagree with about which one is
    authoritative. Pinned anyway because CARD-020's ``POST /generate``
    inherits this check, and "the first one wins" is the shape that turns into
    a request-smuggling difference the moment anything sits in front of it.
    """
    request = b"GET / HTTP/1.0\r\n" + b"".join(b"Host: " + h + b"\r\n" for h in hosts) + b"\r\n"

    received = _raw_exchange(running_server.server_port, request)

    assert received.startswith(expected), received[:120]


def test_the_host_check_runs_before_the_router(
    running_server: server.LoopbackHTTPServer,
) -> None:
    """A foreign host gets 400 on *every* path, routed or not — 400, not 404.

    Ordering is the property: a check that ran after routing would leave each
    new route responsible for remembering it, which is how CARD-020's
    ``POST /generate`` would end up writing files for a cross-origin form post.
    """
    for path in ("/", "/no-such-page", pages.FORM_ACTION):
        response = _request(
            running_server.server_port, path=path, headers={"Host": "evil.example.com"}
        )

        assert response.status == 400, path


def test_the_allowlist_is_the_three_loopback_names() -> None:
    """Pinned literally, for the same reason ``_ADAPTERS`` is (ADR-0019).

    An allowlist that grows quietly is not an allowlist. Adding a fourth name
    — a LAN address "just for testing from my phone" — has to be a deliberate
    edit to this line, reviewed as the change to NFR-003's access control that
    it is.
    """
    assert handler.ALLOWED_HOSTS == {"localhost", "127.0.0.1", "::1"}


# --------------------------------------------------------------------------
# The form page (FR-017) and the G-4 boundary
# --------------------------------------------------------------------------


def test_the_form_page_is_served_as_html(
    running_server: server.LoopbackHTTPServer,
) -> None:
    """The 200 path's headers, ``nosniff`` included.

    ``_respond``'s docstring says ``nosniff`` is sent on *every* response, and
    only the 404 params were pinning it — the inverse of where it matters most
    once CARD-020 renders a result page built from user input.
    """
    response = _request(running_server.server_port)

    assert response.status == 200
    assert response.headers["Content-Type"] == "text/html; charset=utf-8"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert int(response.headers["Content-Length"]) == len(response.body)
    assert response.body.startswith(b"<!DOCTYPE html>")


def _form_field_names() -> set[str]:
    """Every ``name="..."`` in the form page — the fields a submission posts."""
    return set(re.findall(r'name="([^"]+)"', pages.FORM_PAGE))


def test_the_form_offers_the_same_option_surface_as_the_cli() -> None:
    """CON-007: both interfaces expose the same options.

    Compared against ``cli.build_parser``'s own ``generate`` destinations
    rather than against a list written here, so an option a later card adds to
    one adapter and forgets in the other shows up as a failure. That divergence
    is the cost ADR-0019 accepted when it chose two parallel adapters over a
    shared request-assembly layer — and it is only *accepted* if somebody
    notices it happening.

    ``image`` is the one deliberate difference: a file upload is a multipart
    form control, which is CARD-021's work (guardrail G-5). It is asserted as
    an exact singleton rather than filtered away, so the gap cannot grow
    quietly.
    """
    argv_options = set(vars(cli.build_parser().parse_args(["generate"]))) - {
        "command",
        "handler",
    }

    assert argv_options - _form_field_names() == {"image"}
    assert _form_field_names() - argv_options == set()


def test_the_form_lists_every_registered_export_format() -> None:
    """Read from COMP-007's registry, exactly as ``--export``'s choices are."""
    for fmt in export.FORMATS:
        assert f'value="{fmt}"' in pages.FORM_PAGE


def test_the_form_lists_every_difficulty_tier_plus_an_unset_choice() -> None:
    """A ``<select>`` needs an explicit "not chosen"; argv just omits the flag."""
    for tier in difficulty.Tier:
        assert f">{tier}</option>" in pages.FORM_PAGE
    assert '<option value="">' in pages.FORM_PAGE


def test_the_form_constrains_no_value_in_the_browser() -> None:
    """Guardrail G-4: an out-of-range value must reach the domain.

    ``min``/``max``/``required``/``pattern`` on an input would have the browser
    reject it first — the same mistake as putting ``choices=`` on
    ``--difficulty`` (ADR-0010), and the domain error AC-050 is about would
    never be raised. ``size`` and ``density`` are plain text inputs for exactly
    that reason.
    """
    for attribute in ("min=", "max=", "required", "pattern="):
        assert attribute not in pages.FORM_PAGE


def test_the_web_package_imports_no_domain_validator() -> None:
    """ADR-0019/R1: no rule about a value lives in the adapter.

    A weak check by construction — it cannot prove the absence of logic — but
    it catches the specific way this boundary erodes: importing the domain's
    validators into the adapter "to give a nicer message" instead of letting
    the value travel inward and come back as a ``NonogramError``.

    ``_WEB_SOURCES`` is asserted non-empty first (AC-059): this loop is cited
    as the enforcement of ADR-0019/R1, and an empty glob would have it certify
    that rule by reading nothing.
    """
    assert _WEB_SOURCES, "no web adapter sources found"
    for path in _WEB_SOURCES:
        source = path.read_text(encoding="utf-8")
        for token in ("validate_size", "validate_density", "parse_tier"):
            assert token not in source, f"{path.name} references {token!r}"


def test_the_web_package_raises_nothing() -> None:
    """The adapter translates failures; it never originates one.

    Every error a web request can produce is either the standard library's (a
    malformed request line, a bind failure) or the domain's, raised inward and
    caught here for rendering. A ``raise`` statement anywhere in ``web/`` would
    mean this package had grown a judgement of its own — which is exactly what
    guardrail G-4 and ADR-0019/R1 put inward of it.

    ``_WEB_SOURCES`` is asserted non-empty first (AC-059): this loop is cited
    as the enforcement of guardrail G-4, and an empty glob would have it
    certify that guardrail by parsing nothing.
    """
    assert _WEB_SOURCES, "no web adapter sources found"
    for path in _WEB_SOURCES:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        raises = [node for node in ast.walk(tree) if isinstance(node, ast.Raise)]
        assert not raises, f"{path.name} raises at line {raises[0].lineno}"


# --------------------------------------------------------------------------
# CARD-022 — the claims the package makes about itself, and the guards that
# were supposed to be checking them (AC-059..AC-062)
# --------------------------------------------------------------------------


class TestWebGuards_EveryStructuralLoopAssertsNonEmpty:
    """AC-059: no structural guard here can pass by looping over nothing.

    Each of these tests works by *enumerating* something discovered at import
    time — ``_WEB_SOURCES`` from a ``rglob``, the web modules from a filter over
    ``tests.test_cli._MODULES`` — and asserting a property of every item found.
    A loop over an empty collection asserts that property of nothing and reports
    green. That is how two tests cited by three consecutive review cycles as the
    enforcement of ADR-0019/R1 and guardrail G-4 came to be evidence for nothing
    at all: the glob was never asserted non-empty, so a rename of the package
    directory would have retired both guards silently.

    This class is the mutation those cycles never ran, made permanent. Each
    guard is invoked with its own collection emptied and must *fail*.
    """

    @pytest.mark.parametrize(
        "guard",
        [
            pytest.param(
                lambda: (
                    TestWebServer_BindsLoopbackOnlyByDefault()
                ).test_no_module_in_the_package_names_another_bind_address(),
                id="bind-address-sweep",
            ),
            pytest.param(
                lambda: (
                    TestWebServer_ProcessesRequestsWithoutAuthentication()
                ).test_the_package_contains_no_authentication_vocabulary(),
                id="auth-vocabulary-scan",
            ),
            pytest.param(
                test_the_web_package_imports_no_domain_validator, id="no-domain-validator"
            ),
            pytest.param(test_the_web_package_raises_nothing, id="raises-nothing"),
        ],
    )
    def test_a_source_sweep_fails_when_the_glob_finds_nothing(
        self, monkeypatch: pytest.MonkeyPatch, guard: Callable[[], None]
    ) -> None:
        """All four ``_WEB_SOURCES`` loops, each against an empty source list."""
        monkeypatch.setattr(f"{__name__}._WEB_SOURCES", [])

        with pytest.raises(AssertionError, match="no web adapter sources found"):
            guard()

    def test_the_web_to_cli_guard_fails_when_the_selector_matches_nothing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The fourth guard, whose empty collection is a *filter*, not a glob.

        ``test_the_web_adapter_never_imports_the_cli_adapter`` walks every module
        in the package and skips the ones that are not ``web``. The collection it
        actually consumes is that filtered set, so a selector that stopped
        matching — a renamed component, a moved package — would leave the loop
        with nothing to do and the ``web -> cli`` prohibition unchecked. Emptied
        here by handing it a module table with no web module in it.
        """
        monkeypatch.setattr(
            cli_tests, "_MODULES", {"nonogram.cli": cli_tests._MODULES["nonogram.cli"]}
        )

        with pytest.raises(AssertionError):
            cli_tests.test_the_web_adapter_never_imports_the_cli_adapter()

    def test_the_same_guard_passes_on_the_real_module_table(self) -> None:
        """The control: unmonkeypatched, it still passes — so the failure above
        is the emptying and not a broken call."""
        cli_tests.test_the_web_adapter_never_imports_the_cli_adapter()


class TestWebDocstrings_MatchTheShippedPackage:
    """AC-060: every factual claim ``web/__init__.py`` makes is true of the code.

    The COMP-008 docstring is the first thing anyone reads about this package,
    and it shipped saying two things that were not so: that the package imports
    the orchestrator (nothing under ``web/`` does), and that it performs request
    parsing and maps form fields onto ``GenerationRequest`` (CARD-019's guardrail
    G-5 excluded both; CARD-020 adds them). Prose is not usually testable, but
    *these* claims are — they are claims about imports and about routes.
    """

    def test_the_package_imports_exactly_what_the_docstring_names(self) -> None:
        """"the difficulty and export registries" — and nothing else outward."""
        assert _web_component_imports() - {"web"} == {"difficulty", "export"}

    def test_the_docstring_claims_no_import_the_package_does_not_make(self) -> None:
        """The specific false sentence, pinned so it cannot come back.

        One-directional on purpose: claiming an import obliges the import to
        exist, while making an import does not oblige a sentence. CARD-020 may
        well import the orchestrator, and this test is not a demand that it also
        phrase the docstring a particular way — only that it not describe an
        edge that is not there.
        """
        docstring = " ".join((web.__doc__ or "").split())
        imported = _web_component_imports()

        for component in ("orchestrator", "sourcing", "clues", "solver", "difficulty"):
            if f"imports the {component}" in docstring:
                assert component in imported, component

    def test_the_docstring_claims_no_responsibility_the_package_lacks(self) -> None:
        """Request parsing and the ``GenerationRequest`` mapping are forthcoming.

        Pinned as: the docstring still names the mapping (a reader needs to know
        where it went), and every sentence that names it also names the card that
        brings it. A present-tense claim would not.
        """
        text = " ".join((web.__doc__ or "").split())
        sentences = [s for s in text.split(". ") if "GenerationRequest" in s]

        assert sentences, "the docstring no longer says where the mapping lives"
        for sentence in sentences:
            assert "CARD-020" in sentence, sentence

    def test_the_package_really_does_no_request_mapping_yet(self) -> None:
        """The behavioural half of the claim above, so it is not prose-on-prose."""
        assert not hasattr(handler.WebUIRequestHandler, "do_POST")
        assert {method for method, _ in handler.ROUTES} == {"GET"}

        for path in _WEB_SOURCES:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
            docstrings = _docstring_nodes(tree)
            code = [
                node
                for node in ast.walk(tree)
                if isinstance(node, ast.Constant) and id(node) not in docstrings
            ]
            assert not any(
                isinstance(node.value, str) and "GenerationRequest" in node.value
                for node in code
            ), path.name


#: One request shape per status the standard library answers before ``do_GET``
#: is reached. Kept as raw bytes because ``http.client`` cannot express a
#: malformed request line, and keyed by the status each must provoke.
_STDLIB_ERROR_REQUESTS: dict[int, bytes] = {
    400: b"this is not a request line\r\n\r\n",
    414: b"GET /" + b"x" * 70000 + b" HTTP/1.0\r\n\r\n",
    431: b"GET / HTTP/1.0\r\n" + b"".join(b"X-%d: 1\r\n" % n for n in range(150)) + b"\r\n",
    501: b"POST / HTTP/1.0\r\nHost: 127.0.0.1\r\n\r\n",
    505: b"GET / HTTP/9.9\r\n\r\n",
}

#: The exact status line each must now produce. Spelled out rather than looked
#: up in ``BaseHTTPRequestHandler.responses``, so the reason phrase is asserted
#: against a second source and not against the handler's own table. Note the
#: 501: the standard library's reads ``501 Unsupported method ('POST')``, with
#: the request's method in the *reason phrase*.
_STDLIB_ERROR_STATUS_LINES: dict[int, bytes] = {
    400: b"HTTP/1.0 400 Bad Request",
    414: b"HTTP/1.0 414 URI Too Long",
    431: b"HTTP/1.0 431 Request Header Fields Too Large",
    501: b"HTTP/1.0 501 Not Implemented",
    505: b"HTTP/1.0 505 HTTP Version Not Supported",
}


class TestWebHandler_ErrorResponsesMatchTheDeclaredNosniffBound:
    """AC-061: ``_respond``'s "sent on every response" is literally true.

    Five statuses — 400, 414, 431, 501, 505 — are written before routing, by
    ``BaseHTTPRequestHandler.send_error``. Its own version replies ``text/html``
    with no ``X-Content-Type-Options`` and interpolates the request's method or
    version token into the body, so the docstring's claim was false for five of
    the nine statuses this adapter can produce, and the tests that pinned the
    header only ever looked at the four ``_respond`` writes.

    ``WebUIRequestHandler.send_error`` now funnels all five through ``_respond``.
    These tests pin the result on the wire rather than trusting the override:
    the statuses are unchanged, the header is present, and nothing from the
    request comes back.
    """

    @pytest.mark.parametrize("status", sorted(_STDLIB_ERROR_REQUESTS))
    def test_the_status_is_unchanged_and_carries_the_declared_header(
        self, running_server: server.LoopbackHTTPServer, status: int
    ) -> None:
        received = _raw_exchange(running_server.server_port, _STDLIB_ERROR_REQUESTS[status])
        head, _, body = received.partition(b"\r\n\r\n")
        lowered = head.lower()

        # A status line at all is part of the claim, and for 400 and 505 it is
        # new: ``parse_request`` assigns the parsed version only after accepting
        # it, so on those two paths ``request_version`` was still the HTTP/0.9
        # default and both ``send_response_only`` and ``end_headers`` no-op'd.
        # As CARD-019 shipped, the client got a bare HTML body with no status
        # line and no headers whatsoever — no Content-Type either, so "no
        # nosniff" understated it.
        # The reason phrase is written out here rather than read back from
        # ``handler.WebUIRequestHandler.responses``, which is the table the
        # handler itself formats from: re-deriving it there would assert only
        # that the same lookup was done twice.
        assert head.splitlines()[0] == _STDLIB_ERROR_STATUS_LINES[status], received[:120]
        assert b"x-content-type-options: nosniff" in lowered, received[:200]
        assert b"content-type: text/plain; charset=utf-8" in lowered, received[:200]
        assert b"<" not in body, body[:200]

    @pytest.mark.parametrize(
        ("request_bytes", "echo"),
        [
            pytest.param(b"POST / HTTP/1.0\r\n\r\n", b"POST", id="method"),
            pytest.param(
                b"<script>alert(1)</script> / HTTP/1.0\r\n\r\n", b"script", id="markup-method"
            ),
            pytest.param(b"GET / HTTP/9.9\r\n\r\n", b"9.9", id="version"),
        ],
    )
    def test_no_error_body_echoes_anything_off_the_wire(
        self, running_server: server.LoopbackHTTPServer, request_bytes: bytes, echo: bytes
    ) -> None:
        """The stdlib escapes what it reflects; this handler reflects nothing.

        Escaped markup in an ``text/html`` error body was inert, but inert by
        the standard library's escaping rather than by anything this package
        owns or tests. There is nothing to escape now.
        """
        received = _raw_exchange(running_server.server_port, request_bytes)

        assert echo not in received, received[:200]

    def test_a_head_request_gets_no_body(
        self, running_server: server.LoopbackHTTPServer
    ) -> None:
        """RFC 9110 §9.3.2 — and the one thing the stdlib's ``send_error`` did
        that a naive override would have lost."""
        received = _raw_exchange(running_server.server_port, b"HEAD / HTTP/1.0\r\n\r\n")
        head, _, body = received.partition(b"\r\n\r\n")

        assert b" 501 " in head.splitlines()[0], received[:120]
        assert b"content-length: 0" in head.lower(), received[:200]
        assert body == b"", body[:200]

    def test_the_routed_responses_still_carry_it_too(
        self, running_server: server.LoopbackHTTPServer
    ) -> None:
        """The other half of "every": the four statuses ``_respond`` already had.

        200 (the form), 404 (no route), and both 400s the ``Host`` check writes.
        Asserted here as one set so the claim is checked whole rather than one
        route at a time.
        """
        port = running_server.server_port
        responses = [
            _request(port),
            _request(port, path="/no-such-page"),
            _request(port, headers={"Host": "evil.example.com"}),
        ]
        raw_conflicting = _raw_exchange(
            port, b"GET / HTTP/1.0\r\nHost: 127.0.0.1\r\nHost: evil.example.com\r\n\r\n"
        )

        assert [r.status for r in responses] == [200, 404, 400]
        for response in responses:
            assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert b"x-content-type-options: nosniff" in raw_conflicting.lower()
        assert b" 400 " in raw_conflicting.splitlines()[0]


class TestAuthScan_IsCaseInsensitiveOnHeaderNames:
    """AC-062: a challenge header is detected however it is spelled.

    HTTP field names are case-insensitive (RFC 9110 §5.1), so
    ``send_header("www-authenticate", …)`` is a challenge exactly as
    ``WWW-Authenticate`` is. Both checks that look for one compared the wire
    spelling: the AST scan with ``"WWW-Authenticate" not in node.value``, and
    the behavioural assertion against a ``dict`` keyed on the header as sent.
    Either would have waved a lowercase challenge through.
    """

    @pytest.mark.parametrize(
        "spelling",
        ["WWW-Authenticate", "www-authenticate", "Www-Authenticate", "WWW-AUTHENTICATE"],
    )
    def test_the_source_scan_sees_every_spelling(self, spelling: str) -> None:
        source = f'def _challenge(self):\n    self.send_header({spelling!r}, "Basic")\n'

        assert _auth_vocabulary_hits(source, "fabricated.py") == [
            "fabricated.py:2 writes a challenge header"
        ]

    def test_the_source_scan_is_not_simply_always_positive(self) -> None:
        """The control. Without it the test above proves only that the scan
        returns something, not that it returns something *about the header*."""
        source = 'def _serve(self):\n    self.send_header("Content-Type", "text/plain")\n'

        assert _auth_vocabulary_hits(source, "fabricated.py") == []

    def test_the_source_scan_still_ignores_a_docstring(self) -> None:
        """The property the AST form was introduced for, kept while widening it:
        prose *about* the absent header must not read as the header."""
        source = '"""There is no www-authenticate here."""\n'

        assert _auth_vocabulary_hits(source, "fabricated.py") == []

    @pytest.mark.parametrize("spelling", ["WWW-Authenticate", "www-authenticate"])
    def test_a_response_carrying_the_header_is_detected(self, spelling: str) -> None:
        """The behavioural half, through the same accessor
        ``test_no_endpoint_ever_challenges`` uses.

        A handler that really does send the header is served over a real socket
        and the assertion that test makes is shown to catch it — for both
        spellings, which the previous ``dict(getheaders())`` could not.
        """

        class _ChallengingHandler(handler.WebUIRequestHandler):
            def do_GET(self) -> None:
                self.send_response(200)
                self.send_header(spelling, 'Basic realm="nonogram"')
                self.send_header("Content-Length", "0")
                self.end_headers()

        challenging = server.LoopbackHTTPServer(
            (server.LOOPBACK_HOST, 0), _ChallengingHandler
        )
        with _running(challenging) as running:
            response = _request(running.server_port)

        assert "WWW-Authenticate" in response.headers

    def test_the_shipped_handler_carries_no_such_header(
        self, running_server: server.LoopbackHTTPServer
    ) -> None:
        """The control for the probe above: the real server sends none (AC-053)."""
        assert "WWW-Authenticate" not in _request(running_server.server_port).headers
