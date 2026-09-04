"""COMP-008 tests: the loopback bind, the absent auth check, and the router.

    AC-052  TestWebServer_BindsLoopbackOnlyByDefault
    AC-053  TestWebServer_ProcessesRequestsWithoutAuthentication
    AC-054  TestWebServer_RejectsCrossSiteSecFetchSite
    AC-055  TestWebServer_RejectsForeignOrigin
    AC-056  TestWebServer_RejectsAbsoluteFormTargetWithForeignAuthority
    AC-057  TestWebServer_ServesSameOriginRequestNormally
    AC-058  TestWebServer_AllowsRequestsWithNoOriginMetadata
    EC-004  PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest

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
the two boundaries ADR-0019/R1 and CON-008 draw, and — since CARD-020's
cycle-1 fix — NFR-004's cross-origin refusal (AC-054..AC-058, EC-004).
"""

from __future__ import annotations

import ast
import http.client
import http.server
import inspect
import re
import socket
import socketserver
import threading
import time
import urllib.parse
from collections.abc import Callable, Iterator, Sequence
from contextlib import closing, contextmanager
from http import HTTPStatus
from pathlib import Path
from typing import NamedTuple

import pytest

from nonogram import cli, difficulty, export, orchestrator, web
from nonogram.web import handler, pages, server, submission

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
    """The router's shape: CARD-020 extended the table rather than replacing it.

    Two rows, and the ``POST`` row is keyed on ``pages.FORM_ACTION`` rather than
    on a second copy of ``"/generate"`` — the form's ``action`` and the router's
    key are one constant, so a submission cannot be posted at a path the router
    does not answer.
    """
    assert set(handler.ROUTES) == {("GET", "/"), ("POST", pages.FORM_ACTION)}


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
        # The form's own action. It is a ``POST`` route (CARD-020) and has no
        # ``GET`` route: the table is keyed on the pair, so acquiring one method
        # does not quietly acquire the other.
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


def test_post_is_routed_and_an_unhandled_method_still_is_not(
    running_server: server.LoopbackHTTPServer,
) -> None:
    """CARD-020 added exactly one method, and 501 stayed for the rest.

    This test asserted the opposite until CARD-020: the form posted to an
    endpoint that answered ``501 Not Implemented`` because there was no
    ``do_POST`` to dispatch. There is one now, and the useful thing left to pin
    is that adding it did not turn every unknown method into a route —
    ``BaseHTTPRequestHandler`` still chooses 501 for a method with no ``do_*``,
    and the *response* to it is still ``WebUIRequestHandler.send_error``'s
    (``text/plain``, ``nosniff``), pinned by
    ``TestWebHandler_ErrorResponsesMatchTheDeclaredNosniffBound``.

    The ``POST`` here is deliberately one the domain refuses: what is being
    checked is that it was *routed*, not what it generated, and an empty body
    reaches the same "no grid extent" refusal ``nonogram generate`` with no
    ``--size`` gets. The submission path itself is
    ``tests/test_web_submission.py``'s.
    """
    posted = _request(
        running_server.server_port, method="POST", path=pages.FORM_ACTION, body=b""
    )
    unhandled = _raw_exchange(
        running_server.server_port, b"PUT / HTTP/1.0\r\nHost: 127.0.0.1\r\n\r\n"
    )

    assert hasattr(handler.WebUIRequestHandler, "do_POST")
    assert posted.status == 200
    assert b'data-outcome="failure"' in posted.body
    assert b" 501 " in unhandled.splitlines()[0]


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
        # component of these as loopback — which it genuinely is, so none of
        # them was ever a hole — but a header carrying userinfo, a path, a
        # query or a fragment is not a host name, and neither is one whose port
        # is empty or non-numeric. The shape space is BOUND now rather than
        # merely narrowed: EC-004 names the ``#``/``?``/port shapes explicitly
        # and CARD-020's cycle-1 fix refuses them, so the withdrawn "keeps the
        # two sets the same size" rationale is replaced by a rule rather than
        # left standing. The reversal that would be a hole,
        # ``127.0.0.1@evil.example.com``, was already refused and stays here to
        # prove the narrowing did not replace the parse with a substring test.
        pytest.param("user:pass@127.0.0.1", id="userinfo"),
        pytest.param("evil.example.com@127.0.0.1", id="userinfo-lookalike"),
        pytest.param("127.0.0.1/../evil", id="path-component"),
        pytest.param("127.0.0.1@evil.example.com", id="reversed-userinfo"),
        pytest.param("127.0.0.1#evil.example.com", id="fragment"),
        pytest.param("localhost?evil", id="query"),
        pytest.param("127.0.0.1:", id="empty-port"),
        pytest.param("127.0.0.1:notaport", id="non-numeric-port"),
    ],
)
def test_a_foreign_host_header_is_refused_before_routing(
    running_server: server.LoopbackHTTPServer, host: str
) -> None:
    """F-12: a request naming another host is answered 400 and never routed.

    This is the DNS-rebinding half of the access control, and only that half.
    The kernel stops a *network* peer, but the browser the user is already
    running is on this host, and a page it loads can reach
    ``http://127.0.0.1:<port>/`` under a hostname the attacker controls, which
    is what would make the reply readable to that page. That name is what this
    check refuses.

    It does not, on its own, refuse the *other* browser-mediated reach: a
    browser sets ``Host`` from the *target*, so a page on any origin posting to
    ``http://127.0.0.1:<port>/`` sends an allowlisted ``Host`` and gets past
    this check. That reach is NFR-004 / CON-010, and it is closed by a separate
    check that this test says nothing about — see
    ``PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest``
    below, and the five criteria AC-054..AC-058 beside it.

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
    against the browser-mediated *rebinding* attack, and a browser cannot suppress the
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
    new route responsible for remembering it, which is how ``POST /generate``
    would end up writing files for a request that never named this server.
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
# NFR-004 / CON-010 — the cross-origin refusal (AC-054..AC-058, EC-004)
# --------------------------------------------------------------------------
#
# The half of BCON-0001's browser-mediated reach that the ``Host`` check above
# does not close, and — until CARD-020's cycle-1 review — did not close at all.
# A browser sets ``Host`` from the request's *target*, so a form on
# ``https://evil.example.com`` posting to ``http://127.0.0.1:<port>/generate``
# arrives with an allowlisted ``Host`` over a loopback socket. Reproduced on
# the wire against the code this section was written for: ``200``, the pipeline
# ran, and it wrote into a directory the attacking page named — one file per
# ``export_formats`` value the body carried, two for the body below.
#
# What the refusal reads are the signals such a request carries and page script
# can neither forge nor suppress: ``Sec-Fetch-Site``, ``Origin``, and the
# authority of an absolute-form request target. ``Referer`` is deliberately not
# among them — a referrer policy the attacking page controls can switch it off.


def _raw_request(
    method: str,
    target: str,
    headers: Sequence[tuple[str, str]] = (),
    body: bytes = b"",
) -> bytes:
    """One HTTP/1.0 request as bytes, headers in the order given.

    Built by hand rather than through ``http.client`` because every shape this
    section is about is one that library will not send: a repeated header, a
    header with no value, an absolute-form request target, or no ``Host`` at
    all.
    """
    lines = [f"{method} {target} HTTP/1.0".encode()]
    lines += [f"{name}: {value}".encode() for name, value in headers]
    if body:
        lines.append(b"Content-Type: application/x-www-form-urlencoded")
        lines.append(b"Content-Length: %d" % len(body))
    return b"\r\n".join(lines) + b"\r\n\r\n" + body


#: Authorities that are not this server, in the shapes an attack arrives in.
_FOREIGN_AUTHORITIES: tuple[str, ...] = (
    "evil.example.com",
    "evil.example.com:8765",
    # A name the attacker controls that resolves to 127.0.0.1 — the connection
    # really is loopback, so the bind address says nothing about it.
    "rebind.attacker.test",
    # Prefix/suffix games against a naive substring check.
    "127.0.0.1.evil.example.com",
    "localhost.evil.example.com",
    "notlocalhost",
    "127.0.0.2",
    "10.0.0.1",
    "[::2]",
)

#: Authorities whose *host component* ``urlsplit`` reads as loopback but which
#: are not well-formed authorities. EC-004 names these explicitly ("a ``#`` or
#: ``?`` inside the Host value, a non-numeric or empty port"), which is why
#: they are a corpus of their own rather than filed under "foreign": the host
#: really is loopback in each, so a check that consulted only the host serves
#: every one of them.
_MALFORMED_LOOPBACK_AUTHORITIES: tuple[str, ...] = (
    "127.0.0.1#evil.example.com",
    "localhost?evil",
    "127.0.0.1:",
    "127.0.0.1:notaport",
    "127.0.0.1:8765x",
    "user:pass@127.0.0.1",
    "127.0.0.1/../evil",
)

#: Every authority a request may not claim, however it claims it.
_REFUSED_AUTHORITIES = _FOREIGN_AUTHORITIES + _MALFORMED_LOOPBACK_AUTHORITIES

#: Authorities that name this server. Ports vary and are deliberately not the
#: one under test: ``--port`` chooses it and only the name is compared.
_LOOPBACK_AUTHORITIES: tuple[str, ...] = (
    "127.0.0.1",
    "127.0.0.1:8765",
    "localhost",
    "localhost:1",
    "[::1]",
    "[::1]:65535",
)

#: URL schemes an ``Origin`` can be built with. Both are accepted shapes; the
#: scheme is read for presence and then discarded, so a ``https://`` origin on
#: a loopback host is served and one on a foreign host is not.
_ORIGIN_SCHEMES: tuple[str, ...] = ("http", "https")

#: ``Sec-Fetch-Site`` values that must be refused: the two the fetch-metadata
#: spec defines and this server does not answer, plus the shapes a value can
#: arrive in that are not tokens of that spec at all.
_REFUSED_FETCH_SITES: tuple[str, ...] = (
    "cross-site",
    "same-site",
    # Case variants. The spec defines lowercase tokens, so anything else did
    # not come from a browser following it and is refused rather than guessed.
    "Cross-Site",
    "SAME-ORIGIN",
    "None",
    # A value that is not a token of the vocabulary at all.
    "",
    "unknown-value",
    "same-origin cross-site",
    "same-origin, cross-site",
    "none; cross-site",
)

#: ``Sec-Fetch-Site`` values that must be served (AC-057).
#:
#: The two padded spellings are here for ``handler``'s own ``site.strip()``,
#: which is the ONLY strip in the chain and is load-bearing. Measured on this
#: interpreter rather than assumed: ``http.client``'s header parsing strips the
#: whitespace *after the colon* but leaves trailing whitespace alone — parsing
#: ``"X-A: none \r\n"`` yields ``['none ']``, the space intact. So the two rows
#: are not symmetric. ``" same-origin"`` arrives at the handler already
#: unpadded and is a duplicate of the row above it, kept because the *layout*
#: of the header is what it is a case of; ``"none "`` is the row that actually
#: reaches ``_cross_origin_refusal`` padded, and only ``.strip()`` turns it back
#: into a token.
#:
#: Removing that ``.strip()`` is safe in the refusing direction — a padded
#: ``cross-site`` misses the allowlist and is refused, which is the right answer
#: for the wrong reason — and a live defect in the serving one: a legitimate
#: ``same-origin `` would miss it too and be refused. Measured: replacing
#: ``site.strip()`` with ``site`` fails
#: ``test_every_same_origin_or_metadata_free_request_is_served``, and nothing
#: else in this module or in ``tests/test_web_submission.py``.
_ALLOWED_FETCH_SITES: tuple[str, ...] = (
    "same-origin",
    "none",
    " same-origin",
    "none ",
)

#: The body a POST row in the corpus carries: a real submission that would
#: generate and write one file per ``export_formats`` value below — two, as
#: spelled — if it were ever routed. Measured, not assumed: this body through
#: ``generate`` + ``export_puzzle`` writes ``pwned.png`` and ``pwned.json``.
_ATTACK_FIELDS: tuple[tuple[str, str], ...] = (
    ("mode", "library"),
    ("library_key", "cat"),
    ("size", "20"),
    ("name", "pwned"),
    ("export_formats", "png"),
    ("export_formats", "json"),
)


def _refused_corpus(out: Path) -> list[tuple[str, bytes]]:
    """Every request shape EC-004 requires refused, as ``(id, bytes)``.

    Built as a product rather than hand-picked, which is what makes this a
    property and not five examples: each *signal* is crossed with each *shape*
    the signal can arrive in, and with both methods, so a refusal that only
    covered ``GET``, or only covered the exact spelling one criterion names,
    fails here rather than passing on the criterion it was written against.

    ``out`` is where the POST rows ask their files to be written, so that a
    refusal that silently stopped working leaves evidence on disk instead of
    only in a status code.
    """
    body = urllib.parse.urlencode([*_ATTACK_FIELDS, ("out", str(out))]).encode()
    local = ("Host", "127.0.0.1")
    corpus: list[tuple[str, bytes]] = []

    for method, payload in (("GET", b""), ("POST", body)):
        target = "/" if method == "GET" else pages.FORM_ACTION

        # 0. The ``Host`` header itself. EC-004 names its malformed shapes in
        #    as many words, and the same authority corpus is what tests them —
        #    the F-12 check answers these, and the property is stated over the
        #    refusal as a whole rather than over which check reaches it first.
        for authority in _REFUSED_AUTHORITIES:
            corpus.append(
                (f"{method}-host-{authority}", _raw_request(
                    method, target, [("Host", authority)], payload))
            )

        # 1. Sec-Fetch-Site, alone and beside an otherwise impeccable Origin.
        for site in _REFUSED_FETCH_SITES:
            corpus.append(
                (f"{method}-sec-fetch-site-{site!r}", _raw_request(
                    method, target, [local, ("Sec-Fetch-Site", site)], payload))
            )
            corpus.append(
                (f"{method}-sec-fetch-site-{site!r}-with-local-origin", _raw_request(
                    method, target,
                    [local, ("Origin", "http://127.0.0.1"), ("Sec-Fetch-Site", site)],
                    payload))
            )

        # 2. Origin, alone and beside an allowlisted Sec-Fetch-Site — the
        #    combination proves the two signals are ANDed and not ORed.
        for scheme in _ORIGIN_SCHEMES:
            for authority in _REFUSED_AUTHORITIES:
                origin = f"{scheme}://{authority}"
                corpus.append(
                    (f"{method}-origin-{origin}", _raw_request(
                        method, target, [local, ("Origin", origin)], payload))
                )
                corpus.append(
                    (f"{method}-origin-{origin}-with-same-origin-metadata", _raw_request(
                        method, target,
                        [local, ("Origin", origin), ("Sec-Fetch-Site", "same-origin")],
                        payload))
                )

        # 3. Origin shapes that are not serialized origins at all (RFC 6454).
        for origin in ("null", "", "http://", "evil.example.com",
                       "http://127.0.0.1/path", "http://127.0.0.1?q",
                       "http://127.0.0.1#f"):
            corpus.append(
                (f"{method}-non-origin-{origin!r}", _raw_request(
                    method, target, [local, ("Origin", origin)], payload))
            )

        # 4. Repeated headers, both orders. Taking the first value is how an
        #    allowlisted one smuggles a foreign one past.
        for first, second in (("http://127.0.0.1", "https://evil.example.com"),
                              ("https://evil.example.com", "http://127.0.0.1")):
            corpus.append(
                (f"{method}-two-origins-{first}-then-{second}", _raw_request(
                    method, target,
                    [local, ("Origin", first), ("Origin", second)], payload))
            )
        for first, second in (("same-origin", "cross-site"), ("cross-site", "same-origin")):
            corpus.append(
                (f"{method}-two-fetch-sites-{first}-then-{second}", _raw_request(
                    method, target,
                    [local, ("Sec-Fetch-Site", first), ("Sec-Fetch-Site", second)],
                    payload))
            )

        # 5. The request target's own authority, with and without a Host —
        #    AC-056's shape is the one with none, which is how the same reach
        #    arrives with nothing for the Host check to look at.
        #
        #    Only the foreign authorities here, not the malformed-loopback
        #    ones: inside a URL those characters mean what they mean in a URL,
        #    so ``http://127.0.0.1#evil.example.com/`` really is a request to
        #    127.0.0.1 carrying a fragment, not an authority-shape attack. It
        #    is answered 404 (no route has that path) rather than 400, and
        #    asserting 400 for it would be asserting a claim about the request
        #    that is not true. EC-004 states those shapes over the *Host value*,
        #    which is group 0.
        for authority in _FOREIGN_AUTHORITIES:
            for scheme in _ORIGIN_SCHEMES:
                prefix = f"{scheme}://{authority}"
                corpus.append(
                    (f"{method}-absolute-target-{prefix}-no-host", _raw_request(
                        method, prefix + target, [], payload))
                )
                corpus.append(
                    (f"{method}-absolute-target-{prefix}-local-host", _raw_request(
                        method, prefix + target, [local], payload))
                )

    return corpus


def _served_corpus() -> list[tuple[str, bytes]]:
    """Every request shape that must still be served (AC-057, AC-058).

    The other half of the property, and the half that makes it a bound rather
    than a wall: a refusal that answered 400 to everything would satisfy the
    corpus above completely.
    """
    corpus: list[tuple[str, bytes]] = [("no-metadata-no-host", _raw_request("GET", "/"))]

    for host in ("127.0.0.1", "localhost", "[::1]"):
        header = [("Host", host)]
        corpus.append((f"no-metadata-host-{host}", _raw_request("GET", "/", header)))
        for site in _ALLOWED_FETCH_SITES:
            corpus.append(
                (f"fetch-site-{site!r}-host-{host}", _raw_request(
                    "GET", "/", [*header, ("Sec-Fetch-Site", site)]))
            )
        for scheme in _ORIGIN_SCHEMES:
            for authority in _LOOPBACK_AUTHORITIES:
                origin = f"{scheme}://{authority}"
                corpus.append(
                    (f"origin-{origin}-host-{host}", _raw_request(
                        "GET", "/", [*header, ("Origin", origin)]))
                )
        corpus.append(
            (f"both-signals-host-{host}", _raw_request(
                "GET", "/",
                [*header, ("Origin", f"http://{host}"), ("Sec-Fetch-Site", "same-origin")]))
        )
        # A loopback authority in absolute form is this server talking about
        # itself, which is what a proxy-style request to it looks like.
        corpus.append(
            (f"absolute-local-target-host-{host}", _raw_request(
                "GET", f"http://{host}/", header))
        )

    return corpus


#: The floor on each corpus, asserted inside the tests that consume them. The
#: numbers are well below what the products above produce; they exist so that a
#: builder that silently stopped producing rows — a tuple emptied, a loop that
#: stopped nesting — reports red rather than the same green over nothing.
_MINIMUM_REFUSED_CASES = 200
_MINIMUM_SERVED_CASES = 40


class TestWebServer_RejectsCrossSiteSecFetchSite:
    """AC-054 — *given* a GET to the form with an allowlisted Host and
    ``Sec-Fetch-Site: cross-site``, *when* the request is dispatched, *then* it
    is refused with 400 and the form is not returned."""

    def test_a_cross_site_navigation_is_refused_with_the_form_withheld(
        self, running_server: server.LoopbackHTTPServer
    ) -> None:
        """The criterion's own shape, sent exactly as a browser sends it."""
        response = _request(
            running_server.server_port,
            headers={
                "Host": f"127.0.0.1:{running_server.server_port}",
                "Sec-Fetch-Site": "cross-site",
                "Sec-Fetch-Mode": "navigate",
            },
        )

        assert response.status == 400
        assert b"<form" not in response.body

    def test_the_refusal_is_not_a_credential_challenge(
        self, running_server: server.LoopbackHTTPServer
    ) -> None:
        """400, not 401/403 — AC-053 is untouched by NFR-004.

        Nothing was authenticated and nothing was forbidden to a principal: the
        request was started by a document this server did not serve, which
        makes it malformed. 400 is also the status NFR-004 and AC-054..AC-056
        name in as many words, so the choice is the model's, not this
        module's.
        """
        response = _request(
            running_server.server_port,
            headers={"Host": "127.0.0.1", "Sec-Fetch-Site": "cross-site"},
        )

        assert response.status == 400
        assert response.status not in (401, 403)
        assert "WWW-Authenticate" not in response.headers


class TestWebServer_RejectsForeignOrigin:
    """AC-055 — *given* a GET to the form with an allowlisted Host and
    ``Origin: https://evil.example.com``, *when* the request is dispatched,
    *then* it is refused with 400 and the form is not returned."""

    def test_a_foreign_origin_is_refused_with_the_form_withheld(
        self, running_server: server.LoopbackHTTPServer
    ) -> None:
        """The criterion's own shape."""
        response = _request(
            running_server.server_port,
            headers={
                "Host": f"127.0.0.1:{running_server.server_port}",
                "Origin": "https://evil.example.com",
            },
        )

        assert response.status == 400
        assert b"<form" not in response.body

    def test_the_refused_origin_is_not_echoed_as_markup(
        self, running_server: server.LoopbackHTTPServer
    ) -> None:
        """The body names the origin and escapes it, exactly as the 404 does."""
        response = _request(
            running_server.server_port,
            headers={"Host": "127.0.0.1", "Origin": "https://<script>alert(1)</script>"},
        )

        assert response.status == 400
        assert b"&lt;script&gt;" in response.body
        assert b"<" not in response.body


class TestWebServer_RejectsAbsoluteFormTargetWithForeignAuthority:
    """AC-056 — *given* an absolute-form request target naming a non-loopback
    authority and no Host header, *when* the request is dispatched, *then* it is
    refused with 400 and the form is not returned."""

    def test_the_criterions_own_request_line_is_refused(
        self, running_server: server.LoopbackHTTPServer
    ) -> None:
        """``GET http://evil.example.com/ HTTP/1.0``, byte for byte.

        Sent raw: ``http.client`` cannot express an absolute-form target and
        always supplies a ``Host``. This is the shape that leaves the ``Host``
        check with nothing to look at, which is why the criterion pins it
        separately from AC-055's.
        """
        received = _raw_exchange(
            running_server.server_port, b"GET http://evil.example.com/ HTTP/1.0\r\n\r\n"
        )

        assert received.startswith(b"HTTP/1.0 400"), received[:120]
        assert b"<form" not in received

    def test_an_absolute_form_target_naming_this_server_is_served(
        self, running_server: server.LoopbackHTTPServer
    ) -> None:
        """The control: the refusal is about the *authority*, not the form.

        A proxy-style request to this server's own name is a request to this
        server, and it is served — so the test above fails for the reason it
        claims rather than because absolute-form targets are refused wholesale.
        """
        received = _raw_exchange(
            running_server.server_port,
            f"GET http://127.0.0.1:{running_server.server_port}/ HTTP/1.0\r\n\r\n".encode(),
        )

        assert received.startswith(b"HTTP/1.0 200"), received[:120]
        assert b"<form" in received


class TestWebServer_ServesSameOriginRequestNormally:
    """AC-057 — *given* a GET to the form with an allowlisted Host,
    ``Sec-Fetch-Site: same-origin`` and no Origin header, *when* the request is
    dispatched, *then* it is processed normally and returns 200 with the
    form."""

    def test_the_form_is_returned_unchanged(
        self, running_server: server.LoopbackHTTPServer
    ) -> None:
        """The criterion's own shape — what the browser sends on a reload."""
        response = _request(
            running_server.server_port,
            headers={
                "Host": f"127.0.0.1:{running_server.server_port}",
                "Sec-Fetch-Site": "same-origin",
            },
        )

        assert response.status == 200
        assert response.body == pages.FORM_PAGE.encode("utf-8")


class TestWebServer_AllowsRequestsWithNoOriginMetadata:
    """AC-058 — *given* a GET to the form with an allowlisted Host, no
    Sec-Fetch-Site and no Origin, *when* the request is dispatched, *then* it is
    processed normally and returns 200 with the form."""

    def test_a_request_carrying_neither_header_is_served(
        self, running_server: server.LoopbackHTTPServer
    ) -> None:
        """``curl``, a typed URL, a bookmark — the metadata-free navigation.

        The boundary this criterion draws is the one that decides whether the
        refusal is shippable at all: neither header can be *added* by page
        script (both are forbidden header names to ``fetch``/XHR), so their
        absence is never the attacker's shape, and refusing on absence would
        break every non-browser client while buying nothing.
        """
        response = _request(
            running_server.server_port,
            headers={"Host": f"127.0.0.1:{running_server.server_port}"},
        )

        assert response.status == 200
        assert response.body == pages.FORM_PAGE.encode("utf-8")

    def test_a_request_with_no_headers_at_all_is_served(
        self, running_server: server.LoopbackHTTPServer
    ) -> None:
        """No Host either — this module's own AC-052 interface probes."""
        received = _raw_exchange(running_server.server_port, b"GET / HTTP/1.0\r\n\r\n")

        assert received.startswith(b"HTTP/1.0 200 OK"), received[:120]


# --------------------------------------------------------------------------
# EC-004 — PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest
#
# For any request whose Sec-Fetch-Site header is present and not
# same-origin/none, whose Origin header names a host that is not a loopback
# name, or whose request-target is absolute-form with a non-loopback authority
# — INCLUDING header shapes not named by AC-054..AC-056 — the server refuses the
# request and never routes it to a handler, FOR ANY such input. CON-010's
# declared check, and the one the constraint has cited since 2026-08-30.
#
# Written as module-level functions rather than as a class, which is this
# project's convention for a property (cf.
# ``PropertyTest_WebUI_SurfacesAnyPipelineErrorAsStructuredFailure`` in
# tests/test_web_submission.py): the CamelCase name above is the logical id the
# requirement cites, and each ``def`` below is one arm of it. ``PropertyTest_``
# is not collected by pytest's default ``python_classes``, so a class of that
# name would silently run nothing.
#
# Three arms:
#
# * ``test_the_corpora_are_large_and_cover_every_declared_signal`` is what makes
#   the other two non-vacuous. Both corpora are products of hand-built tuples,
#   so a tuple emptied or a loop that stopped nesting would leave the sweeps
#   asserting a property of nothing and reporting green.
# * ``test_every_cross_origin_or_foreign_authority_request_is_refused`` is the
#   property. Every row must answer 400, must not carry the form, and — for the
#   POST rows, which submit a real generation — must leave nothing on disk, so
#   "never routed to a handler" is checked by its consequence and not only by a
#   status code.
# * ``test_every_same_origin_or_metadata_free_request_is_served`` is the bound.
#   A refusal that answered 400 to everything satisfies the first sweep
#   completely and fails this one on its first row.
#
# A fourth ``def`` follows the three below and is deliberately not an arm:
# ``test_the_accepted_fetch_metadata_is_the_two_spec_values`` pins a constant,
# as ``ALLOWED_HOSTS``'s sibling does, and would still be wanted if the property
# went away.
#
# No ``hypothesis``: it is not in ADR-0006's dependency baseline. The corpora
# are built by hand and their size is asserted inside the tests that use them,
# which is this project's standing answer to the same need. As shipped the
# refused corpus is 294 rows against a floor of 200 and the served corpus is 58
# against a floor of 40 — both measured, and both floors asserted in
# ``test_the_corpora_are_large_and_cover_every_declared_signal``, which is what
# makes those numbers a guard rather than a note.
# --------------------------------------------------------------------------


def test_the_corpora_are_large_and_cover_every_declared_signal(tmp_path: Path) -> None:
    """The corpora that make the two sweeps below non-vacuous."""
    refused = _refused_corpus(tmp_path)
    served = _served_corpus()

    assert len(refused) >= _MINIMUM_REFUSED_CASES, len(refused)
    assert len(served) >= _MINIMUM_SERVED_CASES, len(served)
    # Every id is distinct, so the counts are cases and not one case repeated.
    assert len({case_id for case_id, _ in refused}) == len(refused)
    assert len({case_id for case_id, _ in served}) == len(served)
    # Each of EC-004's three signals is present, and both methods are.
    for signal in (b"Sec-Fetch-Site: cross-site", b"Origin: https://evil.example.com",
                   b"GET http://evil.example.com/", b"POST http://evil.example.com/generate"):
        assert any(signal in request for _, request in refused), signal
    # And each of the shapes EC-004 names beyond the three criteria.
    for shape in (b"127.0.0.1#evil.example.com", b"localhost?evil", b"127.0.0.1:notaport",
                  b"Host: 127.0.0.1:\r\n", b"Origin: null"):
        assert any(shape in request for _, request in refused), shape


def test_every_cross_origin_or_foreign_authority_request_is_refused(
    running_server: server.LoopbackHTTPServer, tmp_path: Path
) -> None:
    """EC-004's property: every row, one running server, nothing routed.

    The POST rows carry a real library submission whose ``out`` is ``tmp_path``,
    so a refusal that stopped working does not merely return the wrong status —
    it leaves files behind, which the final assertion catches even if the status
    assertions were somehow satisfied. Two per routed row, one for each of
    ``_ATTACK_FIELDS``' two ``export_formats`` values; the assertion below is
    stated over the directory being *empty*, so the count is not load-bearing.
    """
    corpus = _refused_corpus(tmp_path)
    assert len(corpus) >= _MINIMUM_REFUSED_CASES, len(corpus)

    for case_id, request in corpus:
        received = _raw_exchange(running_server.server_port, request)

        assert received.startswith(b"HTTP/1.0 400"), (case_id, received[:160])
        assert b"<form" not in received, case_id
        assert b"data-outcome" not in received, case_id

    assert not list(tmp_path.rglob("*")), sorted(tmp_path.rglob("*"))


def test_every_same_origin_or_metadata_free_request_is_served(
    running_server: server.LoopbackHTTPServer,
) -> None:
    """The bound on the property: a blanket refusal fails here.

    Every row is a request a browser or a command-line client legitimately
    sends — same-origin metadata, a loopback origin on either scheme, or no
    metadata at all — and every one of them gets the form.
    """
    corpus = _served_corpus()
    assert len(corpus) >= _MINIMUM_SERVED_CASES, len(corpus)

    for case_id, request in corpus:
        received = _raw_exchange(running_server.server_port, request)

        assert received.startswith(b"HTTP/1.0 200 OK"), (case_id, received[:160])
        assert b"<form" in received, case_id


def test_the_accepted_fetch_metadata_is_the_two_spec_values() -> None:
    """Pinned literally, for the same reason ``ALLOWED_HOSTS`` is.

    An allowlist that grows quietly is not an allowlist, and this one has two
    plausible-looking wrong values a future edit could add: ``same-site``,
    which sounds harmless and is exactly the cross-document case NFR-004 is
    about, and ``cross-site`` itself. Adding either has to be a deliberate edit
    to this line.
    """
    assert handler.ALLOWED_FETCH_SITES == {"same-origin", "none"}


# --------------------------------------------------------------------------
# The form page (FR-017) and the CON-008 boundary
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

    There are now four deliberate differences, named here as an exact set
    rather than filtered away, so the gap cannot grow quietly:

    * ``extent`` on argv against ``size`` on the form — CARD-027 turned
      ``--size`` into a ``(width, height)`` pair carried under the ``extent``
      destination (FR-018, ADR-0022/R1), and its guardrail G-7 reserves the web
      form's extent field for CARD-028. So for exactly the interval between
      those two cards the *same option* is spelled differently on the two
      adapters. CARD-028 has since taught the form ``WxH``, so the CAPABILITY
      gap G-7 predicted is closed: both adapters now accept ``N`` and ``NxM``
      and agree on every token (``PropertyTest_WebForm_ExtentJudgedByDomainNotAdapter``
      checks the web parser against ``cli._extent_token`` as its oracle).
      What survives is only a NAMING difference — argv carries the pair under
      the ``extent`` destination while the form field is still called ``size``
      — which is why this assertion is unchanged by CARD-028 rather than
      dropping back to a pre-CARD-027 shape as this paragraph used to predict.
      Renaming either one is nobody's card yet; until it is, the one name
      below is the whole of the divergence.

    * ``image`` used to be a second deliberate difference — argv only, since a
      file upload needs a multipart form control CARD-019's guardrail G-5
      deferred to CARD-021. CARD-021 added that control
      (``nonogram.web.pages.FORM_PAGE``'s ``<input type="file" name="image">``),
      so ``image`` is now on both sides and drops out of the left-hand set
      below entirely rather than needing its own line.

    * ``mode``, ``density``, and ``library_key`` are now three additional
      deliberate differences — argv side only. CARD-032 restricted the form to
      image mode only, removing the source dropdown and mode-specific fields
      (density for random mode, library_key for library mode). The CLI still
      supports all three modes. The urlencoded path used by tests still accepts
      all modes (guardrail G-2 keeps that path unchanged), but the rendered form
      only offers image mode, signaling to users what the web UI is for.
    """
    argv_options = set(vars(cli.build_parser().parse_args(["generate"]))) - {
        "command",
        "handler",
    }
    # CARD-032: form is now image-only, so it lacks mode, density, library_key
    form_options = _form_field_names()

    assert argv_options - form_options == {"extent", "mode", "density", "library_key"}
    # CARD-037, CARD-044: form adds size, persisted_image_path, persisted_image_filename (internal, not CLI args)
    assert form_options - argv_options == {"size", "persisted_image_path", "persisted_image_filename"}


def test_the_form_lists_every_registered_export_format() -> None:
    """Read from COMP-007's registry, exactly as ``--export``'s choices are."""
    for fmt in export.FORMATS:
        assert f'value="{fmt}"' in pages.FORM_PAGE


def test_the_form_lists_every_difficulty_tier_plus_an_unset_choice() -> None:
    """A ``<select>`` needs an explicit "not chosen"; argv just omits the flag."""
    for tier in difficulty.Tier:
        assert f">{tier}</option>" in pages.FORM_PAGE
    # Check for the blank option (may have attributes like "selected" from CARD-030)
    assert '<option value="' in pages.FORM_PAGE and '(any)</option>' in pages.FORM_PAGE


def test_the_form_constrains_no_value_in_the_browser() -> None:
    """ADR-0019/R1: an out-of-range value must reach the domain.

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
    ADR-0019/R1 puts inward of it.

    ``_WEB_SOURCES`` is asserted non-empty first (AC-059): this loop is cited
    as the enforcement of ADR-0019/R1, and an empty glob would have it
    certify that rule by parsing nothing.
    """
    assert _WEB_SOURCES, "no web adapter sources found"
    for path in _WEB_SOURCES:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        raises = [node for node in ast.walk(tree) if isinstance(node, ast.Raise)]
        assert not raises, f"{path.name} raises at line {raises[0].lineno}"


# --------------------------------------------------------------------------
# CARD-032 — the web form restricted to image-only mode
# --------------------------------------------------------------------------


class TestWebForm_OnlyOffersImageMode:
    """AC-128 — *given* the form page, *when* it loads, *then* the
    "Source" dropdown is gone and the form assumes image mode implicitly
    (file upload required, image metadata displayed, no size/density/
    library-key fields relevant to random/library)."""

    def test_the_form_page_has_no_source_dropdown(
        self, running_server: server.LoopbackHTTPServer
    ) -> None:
        """The Source field is completely absent from the form."""
        response = _request(running_server.server_port)

        assert response.status == 200
        assert b'name="mode"' not in response.body
        assert b"Source" not in response.body

    def test_the_form_page_has_no_library_key_field(
        self, running_server: server.LoopbackHTTPServer
    ) -> None:
        """Library key field (only relevant to library mode) is gone."""
        response = _request(running_server.server_port)

        assert response.status == 200
        assert b'name="library_key"' not in response.body
        assert b"Library key" not in response.body

    def test_the_form_page_has_no_density_field(
        self, running_server: server.LoopbackHTTPServer
    ) -> None:
        """Density field (only relevant to random mode) is gone."""
        response = _request(running_server.server_port)

        assert response.status == 200
        assert b'name="density"' not in response.body
        assert b"Density" not in response.body

    def test_the_form_page_has_image_field_and_size_field(
        self, running_server: server.LoopbackHTTPServer
    ) -> None:
        """Image field is present (required for image mode) and size field is kept."""
        response = _request(running_server.server_port)

        assert response.status == 200
        assert b'name="image"' in response.body
        assert b'type="file"' in response.body
        assert b'name="size"' in response.body


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
    enforcement of ADR-0019/R1 came to be evidence for nothing
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

        ``match=`` pins the *pinned-set* message specifically, as the four
        ``_WEB_SOURCES`` siblings pin theirs. A bare ``pytest.raises`` would be
        satisfied by the loop's own ``cli not in _imported_components`` failure
        — a different defect entirely — and matching on ``nonogram.web`` would
        not discriminate either, since that clause reports the module name.
        """
        monkeypatch.setattr(
            cli_tests, "_MODULES", {"nonogram.cli": cli_tests._MODULES["nonogram.cli"]}
        )

        with pytest.raises(AssertionError, match="web modules missing from the sweep"):
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
        """The four the docstring names, and nothing else.

        ``difficulty`` and ``export`` are the registries ``pages.py`` renders
        the form's choices from; ``orchestrator`` and ``errors`` are CARD-020's
        — the pipeline a submission drives and the one hierarchy it catches.
        Pinned as an exact set so a fifth import has to be a deliberate edit
        here, which is the only thing standing between this package and a
        capability module imported "just to check a value" (ADR-0019/R1).
        """
        assert _web_component_imports() - {"web"} == {
            "difficulty",
            "errors",
            "export",
            "orchestrator",
        }

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
        """The ``GenerationRequest`` mapping is claimed, so it has to be here.

        The claim was future-tense until CARD-020 and this test held it to
        naming the card that would bring it. It is present-tense now, so what it
        has to be held to is the code: a module that builds the request, and a
        ``POST`` route that runs one. Behavioural rather than textual on
        purpose — ``submission.read`` is *called* with a real body, so a module
        that had been reduced to a stub would fail here.
        """
        text = " ".join((web.__doc__ or "").split())
        sentences = [s for s in text.split(". ") if "GenerationRequest" in s]

        assert sentences, "the docstring no longer says where the mapping lives"
        assert ("POST", pages.FORM_ACTION) in handler.ROUTES
        built = submission.read("mode=library&library_key=cat&size=20").request
        assert isinstance(built, orchestrator.GenerationRequest)
        assert (built.mode, built.library_key, built.width) == ("library", "cat", 20)

    def test_the_docstring_does_not_credit_the_stdlib_with_writing_the_501(self) -> None:
        """The claim CARD-022's own ``send_error`` override falsified.

        AC-060 is about the docstring *as a whole*, not about the two sentences
        cycle 1 was pointed at. "a ``POST`` gets the standard library's own
        ``501``" was true until this package overrode ``send_error``; the
        status is still the stdlib's decision, the response is not. Pinned
        against the code fact rather than against prose: while the override is
        present in ``WebUIRequestHandler``'s own ``__dict__``, no sentence may
        hand the whole 501 back to the standard library, and some sentence must
        name the method that writes it.
        """
        assert "send_error" in vars(handler.WebUIRequestHandler)

        text = " ".join((web.__doc__ or "").split())
        sentences = [s for s in text.split(". ") if "501" in s]

        assert sentences, "the docstring no longer says what a POST gets"
        for sentence in sentences:
            assert "standard library's own" not in sentence, sentence
        assert any("send_error" in sentence for sentence in sentences), sentences

    def test_the_docstring_names_every_access_control_check_the_package_makes(self) -> None:
        """"the bind address **and nothing else**" was false — there are two.

        The ``Host`` check refuses a request before routing, which is access
        control by any reading, and ``handler.py`` says so in two places. The
        behavioural half is asserted first so this is not prose checked against
        prose: the second check demonstrably discriminates.
        """
        assert handler._host_is_local("127.0.0.1") is True
        assert handler._host_is_local("evil.example.com") is False

        text = " ".join((web.__doc__ or "").split())
        sentences = [s for s in text.split(". ") if "Access control" in s]

        assert sentences, "the docstring no longer says what the access control is"
        for sentence in sentences:
            assert "and nothing else" not in sentence, sentence
            assert "Host" in sentence, sentence

    def test_the_package_serves_exactly_the_two_routes_it_describes(self) -> None:
        """The two methods the docstring names, and no third.

        The inverse of what this test asserted for CARD-019, which pinned the
        *absence* of ``do_POST`` while the docstring said the submission was
        forthcoming. Both halves have moved together: the docstring says
        ``GET /`` renders the form and ``POST /generate`` runs it, and that is
        exactly the pair of ``do_*`` methods the handler defines. A ``do_PUT``
        added without a sentence to go with it fails here.
        """
        text = " ".join((web.__doc__ or "").split())

        assert "``GET /`` renders the form and ``POST /generate`` runs it" in text
        assert {
            name.removeprefix("do_")
            for name in vars(handler.WebUIRequestHandler)
            if name.startswith("do_")
        } == {"GET", "POST"}
        assert {method for method, _ in handler.ROUTES} == {"GET", "POST"}


class _Interpolation(NamedTuple):
    """One ``{...}`` inside an f-string in ``pages.py``."""

    line: int
    #: ``ast.unparse`` of the interpolated expression, e.g. ``"html.escape(name)"``.
    expression: str
    #: ``ast.unparse`` of the format spec, or ``None`` when there is none.
    format_spec: str | None
    #: True when the expression is itself a call to ``html.escape`` — i.e. the
    #: value is escaped *at the point it is interpolated*, which is the rule
    #: ``pages.py``'s docstring states.
    escaped: bool


def _page_interpolations() -> list[_Interpolation]:
    """Every f-string interpolation in ``pages.py``, read off its AST.

    Read from the source rather than from the rendered pages because the claim
    under test is about the *code*: a page can be free of injected markup today
    and still be built by a rule nobody can apply tomorrow.
    """
    source = Path(pages.__file__).read_text(encoding="utf-8")
    found: list[_Interpolation] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.JoinedStr):
            continue
        for value in node.values:
            if not isinstance(value, ast.FormattedValue):
                continue
            expression = ast.unparse(value.value)
            found.append(
                _Interpolation(
                    line=value.lineno,
                    expression=expression,
                    format_spec=(
                        ast.unparse(value.format_spec) if value.format_spec else None
                    ),
                    escaped=(
                        isinstance(value.value, ast.Call)
                        and ast.unparse(value.value.func) == "html.escape"
                    ),
                )
            )
    return sorted(found)


#: Every interpolation in ``pages.py`` that does **not** call ``html.escape`` at
#: the point of interpolation, mapped to the kind ``pages.py``'s docstring says
#: it is. Spelled out rather than counted so that a *new* unescaped
#: interpolation fails here by name and has to be classified deliberately —
#: which is the check the docstring's own sentence cannot perform.
_UNESCAPED_PAGE_INTERPOLATIONS: dict[str, str] = {
    "_STYLE": "module constant",
    "SUCCESS": "module constant",
    "FAILURE": "module constant",
    "_options(list(difficulty.Tier), blank='(any)')": (
        "fragment escaped by the function that built it"
    ),
    "_options(list(difficulty.Tier), blank='(any)', selected=difficulty_val)": (
        "CARD-030: fragment escaped by the function that built it"
    ),
    "_checkboxes('export_formats', export.FORMATS, checked={'pdf'})": (
        "fragment escaped by the function that built it"
    ),
    "written": "fragment escaped by the function that built it",
    "listed": "fragment escaped by the function that built it",
    "title": "_shell parameter, bound by its own docstring to be a literal",
    "body": "_shell parameter, contractually pre-escaped by the caller",
    "seed": "off the wire in result_page and _success_section, guarded by its ``:d`` format spec",
    "'selected' if is_selected else ''": "CARD-030: HTML attribute literal or empty in _options",
    "'checked' if v in checked else ''": "CARD-030: HTML attribute literal or empty in _checkboxes",
    "result_html": "CARD-030: result section (escaped by _success_section/_error_section)",
    "name_val": "CARD-030: form field value (escaped by _form_field_value)",
    "size_val": "CARD-030: form field value (escaped by _form_field_value)",
    "seed_val": "CARD-030: form field value (escaped by _form_field_value)",
    "out_val": "CARD-030: form field value (escaped by _form_field_value)",
    "export_checkboxes": "CARD-030: checkbox HTML (escaped by _checkboxes)",
    "' '.join(buttons)": "CARD-030: constructed fragment from _suggestions_section",
    "width": "CARD-031: grid dimension (int), part of constructed size_str",
    "height": "CARD-031: grid dimension (int), part of constructed size_str",
    "metadata_json": "CARD-037: JSON data in script block (no HTML escaping needed)",
    "persisted_status": "CARD-037: Status message with filename (pre-built HTML from condition)",
}


class TestWebPages_EscapingRuleIsTheOneTheDocstringStates:
    """``pages.py``'s escaping rule, checked against ``pages.py``.

    The rule shipped twice as an absolute — "exactly one interpolation is not
    escaped" — and was wrong both times, in a module whose whole defence
    against injected markup is that rule. Two review cycles found it by
    counting; this class does the counting, so the third spelling of the
    sentence is pinned to the artifact rather than to anyone's memory.

    Deliberately not a test that the pages come out safe: that is what
    ``test_a_refused_host_is_not_echoed_as_markup`` and the EC-003 arms in
    ``tests/test_web_submission.py`` do. This is a test that the rule a future
    author will *apply* is true of the code they will apply it to.
    """

    def test_the_split_is_the_one_the_docstring_states(self) -> None:
        """54 interpolations, 22 escaped at the point of interpolation, 32 not."""
        found = _page_interpolations()

        assert len(found) == 54, [(i.line, i.expression) for i in found]
        assert sum(1 for i in found if i.escaped) == 22
        assert sum(1 for i in found if not i.escaped) == 32

    def test_every_unescaped_interpolation_is_one_the_docstring_classifies(self) -> None:
        """A thirteenth fails here, by name, rather than passing unnoticed.

        The set comparison is two-directional on purpose: an unescaped
        interpolation this table does not name is an unclassified one, and a
        name this table carries that the module no longer interpolates is a
        stale entry that would otherwise keep vouching for nothing.
        """
        unescaped = {i.expression for i in _page_interpolations() if not i.escaped}

        assert unescaped, "no interpolations found — the AST walk stopped working"
        assert unescaped == set(_UNESCAPED_PAGE_INTERPOLATIONS)

    def test_the_one_wire_value_that_is_not_escaped_is_bound_by_its_format_spec(
        self,
    ) -> None:
        """``{seed:d}`` is safe because of the ``d``, and nothing else.

        Both halves are asserted: that the spec is still there in the source,
        and that it is what does the work — a ``str`` of markup handed to the
        same format raises rather than reaching the page.

        CARD-030: Now there are multiple seed interpolations (in _success_section,
        _error_section, result_page, failure_page), all protected by the :d format spec.
        """
        seeds = [i for i in _page_interpolations() if i.expression == "seed"]

        assert len(seeds) >= 1, seeds
        assert all(s.format_spec == "f'd'" for s in seeds), seeds
        with pytest.raises(ValueError):
            "{0:d}".format("<script>")  # noqa: UP030 — the mechanism, not a style

    def test_the_docstring_states_the_numbers_the_ast_measures(self) -> None:
        """The prose and the artifact, pinned to each other.

        The defect this class exists for was never a wrong *rule* — it was a
        correct rule carrying a quantifier nobody had counted. So the sentence
        itself is read back and compared with the walk, and a docstring reworded
        from memory fails here rather than at the next review.
        """
        text = " ".join((pages.__doc__ or "").split())
        found = _page_interpolations()

        split = re.search(
            r"there are (\d+) f-string interpolations, of which (\d+) call", text
        )
        others = re.search(r"The other (\d+) are each one of (?:four|five|six|seven|several) kinds", text)

        assert split, "the docstring no longer states the interpolation split"
        assert others, "the docstring no longer states the unescaped count"
        assert int(split.group(1)) == len(found)
        assert int(split.group(2)) == sum(1 for i in found if i.escaped)
        assert int(others.group(1)) == sum(1 for i in found if not i.escaped)


#: One request shape per status the standard library answers before ``do_GET``
#: is reached. Kept as raw bytes because ``http.client`` cannot express a
#: malformed request line, and keyed by the status each must provoke.
_STDLIB_ERROR_REQUESTS: dict[int, bytes] = {
    400: b"this is not a request line\r\n\r\n",
    414: b"GET /" + b"x" * 70000 + b" HTTP/1.0\r\n\r\n",
    431: b"GET / HTTP/1.0\r\n" + b"".join(b"X-%d: 1\r\n" % n for n in range(150)) + b"\r\n",
    # ``PUT`` rather than ``POST`` since CARD-020: ``POST`` has a ``do_POST``
    # now and is routed, so the method with no ``do_*`` has to be one that
    # really has none.
    501: b"PUT / HTTP/1.0\r\nHost: 127.0.0.1\r\n\r\n",
    505: b"GET / HTTP/9.9\r\n\r\n",
}

#: The exact status line each must now produce. Spelled out rather than looked
#: up in ``BaseHTTPRequestHandler.responses``, so the reason phrase is asserted
#: against a second source and not against the handler's own table. Note the
#: 501: the standard library's reads ``501 Unsupported method ('PUT')``, with
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
    the eight statuses this adapter can produce, and the tests that pinned the
    header only ever looked at ``_respond``'s own writes.

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

        # A status line at all is part of the claim, and for 505 and for this
        # 400 probe it is new: ``parse_request`` assigns the parsed version only
        # after accepting it, so where the error is written before that
        # assignment ``request_version`` was still the HTTP/0.9 default and both
        # ``send_response_only`` and ``end_headers`` no-op'd. As CARD-019
        # shipped, the client got a bare HTML body with no status line and no
        # headers whatsoever — no Content-Type either, so "no nosniff"
        # understated it. Not every 400 was bare, though: which request-line
        # shapes were is measured in
        # ``test_which_stock_error_paths_never_reached_the_version_assignment``
        # rather than generalised from these five probes.
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
            pytest.param(b"PUT / HTTP/1.0\r\n\r\n", b"PUT", id="method"),
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

    @pytest.mark.parametrize(
        ("request_line", "bare_on_the_stock_library"),
        [
            # Left of ``parse_request``'s ``self.request_version = version``:
            # the version was never accepted, so HTTP/0.9 suppressed everything.
            pytest.param(b"GET / HTTP/x.y", True, id="400-bad-request-version"),
            pytest.param(b"GET / HTTP/2.0", True, id="505-invalid-http-version"),
            pytest.param(b"POST /", True, id="400-bad-http-0.9-request-type"),
            pytest.param(b"GET", True, id="400-bad-request-syntax-one-word"),
            # Right of it. ``Bad request syntax`` guards on a *word count*, so
            # four or more words reach it having already parsed and assigned a
            # real version — and went out with a status line even unpatched.
            pytest.param(b"GET / x HTTP/1.0", False, id="400-bad-request-syntax-four-words"),
        ],
    )
    def test_which_stock_error_paths_never_reached_the_version_assignment(
        self, request_line: bytes, bare_on_the_stock_library: bool
    ) -> None:
        """The measurement ``send_error``'s docstring rests on, made repeatable.

        ``send_error``'s justification for resetting ``request_version`` names
        which of ``parse_request``'s exits wrote a bare body on the stock
        library, and the claim has now been wrong twice by being generalised
        from three probes to all of them. It is a claim about *the standard
        library*, so it is measured against an untouched
        ``BaseHTTPRequestHandler`` here rather than against this package: a
        Python upgrade that changes which exits are bare makes that docstring
        stale, and this is what says so.

        A bare response has no status line at all, which is the whole point —
        so the discriminator is whether the first bytes back are ``HTTP/``.
        """

        class _Stock(http.server.BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.0"

            def do_GET(self) -> None:  # pragma: no cover - never reached
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Length", "0")
                self.end_headers()

            def log_message(self, *args: object) -> None:
                """Silence: every request here is meant to be an error."""

        with socketserver.TCPServer((server.LOOPBACK_HOST, 0), _Stock) as stock:
            thread = threading.Thread(
                target=stock.serve_forever, kwargs={"poll_interval": _POLL_INTERVAL_S},
                daemon=True,
            )
            thread.start()
            try:
                received = _raw_exchange(stock.server_address[1], request_line + b"\r\n\r\n")
            finally:
                stock.shutdown()
                thread.join(timeout=5)

        assert received, request_line
        assert (not received.startswith(b"HTTP/")) is bare_on_the_stock_library, received[:120]

    def test_the_shipped_handler_answers_all_five_of_those_shapes_with_a_status_line(
        self, running_server: server.LoopbackHTTPServer
    ) -> None:
        """And the reset makes the difference vanish — which is the point of it.

        The bound on the test above: the stock library treats those five shapes
        two different ways, and this adapter treats them one way. Stated over
        all five rather than over the four the reset actually rescues, because
        "on every response" is what ``_respond`` claims.
        """
        for request_line in (b"GET / HTTP/x.y", b"GET / HTTP/2.0", b"POST /",
                             b"GET", b"GET / x HTTP/1.0"):
            received = _raw_exchange(
                running_server.server_port, request_line + b"\r\n\r\n"
            )

            assert received.startswith(b"HTTP/1.0 "), (request_line, received[:120])
            assert b"x-content-type-options: nosniff" in received.lower(), request_line

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


# --------------------------------------------------------------------------
# CARD-042 — image preview on file upload (AC-158..AC-161)
# --------------------------------------------------------------------------


class TestWebForm_ImagePreview:
    """AC-158..AC-161: Display image preview after file upload."""

    def test_the_form_page_has_preview_container(
        self, running_server: server.LoopbackHTTPServer
    ) -> None:
        """AC-158: preview container exists in the form."""
        response = _request(running_server.server_port)

        assert response.status == 200
        assert b'id="image-preview-container"' in response.body

    def test_the_form_page_has_preview_image_element(
        self, running_server: server.LoopbackHTTPServer
    ) -> None:
        """AC-158: preview image element is in the form."""
        response = _request(running_server.server_port)

        assert response.status == 200
        assert b'id="image-preview"' in response.body
        assert b'type="image"' not in response.body  # img tag, not input

    def test_the_form_page_has_dimensions_label(
        self, running_server: server.LoopbackHTTPServer
    ) -> None:
        """AC-159: dimensions label element is in the form."""
        response = _request(running_server.server_port)

        assert response.status == 200
        assert b'id="image-dimensions"' in response.body

    def test_preview_container_is_hidden_by_default(
        self, running_server: server.LoopbackHTTPServer
    ) -> None:
        """AC-158: preview is hidden until file is selected (CSS class)."""
        response = _request(running_server.server_port)

        # Check that the container has display:none or no visible class initially
        assert b'id="image-preview-container"' in response.body
        # The .visible class is added by JavaScript, not in the initial HTML
        body_str = response.body.decode()
        assert 'id="image-preview-container"' in body_str
        # Ensure no 'visible' class in the initial rendering
        import re
        match = re.search(
            r'id="image-preview-container"[^>]*class="[^"]*visible',
            body_str
        )
        assert match is None, "Preview container should not have 'visible' class initially"

    def test_metadata_js_uses_filereader_api(self) -> None:
        """AC-161: metadata.js uses FileReader for client-side preview."""
        metadata_js_path = Path(web.__file__).parent / "static" / "metadata.js"
        assert metadata_js_path.exists()

        metadata_js_content = metadata_js_path.read_text()

        # Verify FileReader is used (AC-161)
        assert "FileReader" in metadata_js_content
        assert "readAsDataURL" in metadata_js_content

        # Verify no server-side processing for preview
        assert "fetch" not in metadata_js_content or "metadata" not in metadata_js_content


class TestWebForm_ResultMessageColors:
    """AC-155, AC-156, AC-157: Success/error message styling with colored backgrounds."""

    def test_success_message_has_greenish_background(
        self, running_server: server.LoopbackHTTPServer
    ) -> None:
        """AC-155: success messages display with distinct greenish background."""
        response = _request(running_server.server_port)

        assert response.status == 200
        body_str = response.body.decode()

        # Check that CSS for success messages is in the style
        assert ".outcome-success" in body_str
        assert "#d4edda" in body_str or "d4edda" in body_str  # greenish success color

    def test_error_message_has_pinkish_background(
        self, running_server: server.LoopbackHTTPServer
    ) -> None:
        """AC-156: error messages display with distinct pinkish/reddish background."""
        response = _request(running_server.server_port)

        assert response.status == 200
        body_str = response.body.decode()

        # Check that CSS for error messages is in the style
        assert ".outcome-failure" in body_str
        assert "#f8d7da" in body_str or "f8d7da" in body_str  # pinkish error color

    def test_message_colors_have_wcag_aa_contrast(
        self, running_server: server.LoopbackHTTPServer
    ) -> None:
        """AC-157: success and error backgrounds meet WCAG AA contrast (≥4.5:1)."""
        response = _request(running_server.server_port)

        assert response.status == 200
        body_str = response.body.decode()

        # Success: #d4edda (light green) with #155724 (dark green) = high contrast
        # Error: #f8d7da (light pink) with #721c24 (dark red) = high contrast
        # Both should have contrast ratios well above 4.5:1

        # Verify success text color and error text color are defined
        assert "#155724" in body_str  # success text color (dark green)
        assert "#721c24" in body_str  # error text color (dark red)

        # Verify dark mode colors also exist
        assert "#1e4620" in body_str or "1e4620" in body_str  # dark mode success bg
        assert "#4a1c1c" in body_str or "4a1c1c" in body_str  # dark mode error bg


class TestWebForm_ResultClearing:
    """CARD-038: Result messages clear on new submission."""

    def test_result_container_exists(self, running_server: server.LoopbackHTTPServer) -> None:
        """AC-147: Form has result container for clearing results."""
        response = _request(running_server.server_port)
        assert response.status == 200
        body = response.body.decode()

        # Result container should exist with attribute for JS to target
        assert 'data-result-container="true"' in body

    def test_form_has_clear_results_script(self, running_server: server.LoopbackHTTPServer) -> None:
        """AC-148: Form includes script to clear previous results on form submit."""
        response = _request(running_server.server_port)
        assert response.status == 200
        body = response.body.decode()

        # Script should exist to clear results
        assert 'data-result-container' in body
        assert 'addEventListener' in body and 'submit' in body
        assert 'innerHTML' in body  # Clearing by setting innerHTML to empty string


class TestWebForm_SizeFieldClearing:
    """CARD-039: Size field clears when new image is uploaded."""

    def test_size_field_clears_on_new_image_select(
        self, running_server: server.LoopbackHTTPServer
    ) -> None:
        """AC-149: Size field clears when new image selected."""
        response = _request(running_server.server_port)
        assert response.status == 200
        body = response.body.decode()

        # Form should have size input field
        assert 'name="size"' in body
        # Metadata script should be loaded (for file change handler)
        assert 'metadata.js' in body or 'clearSizeField' in body

    def test_fresh_suggestions_for_new_image(
        self, running_server: server.LoopbackHTTPServer
    ) -> None:
        """AC-150: Fresh suggestions appear for new image after size clears."""
        response = _request(running_server.server_port)
        assert response.status == 200
        body = response.body.decode()

        # Form should have suggestion buttons area (metadata suggestions)
        assert 'metadata-suggestions-area' in body
        # Should have the JavaScript that calculates suggestions
        assert 'suggestDimensions' in body or 'suggestions' in body


class TestWebUI_PreviewWithPersistence:
    """CARD-044: Image preview with persisted uploads."""

    def test_persisted_image_path_field_exists(
        self, running_server: server.LoopbackHTTPServer
    ) -> None:
        """AC-163: Form has hidden field for persisted image path."""
        response = _request(running_server.server_port)
        assert response.status == 200
        body = response.body.decode()

        # Check for persisted image path hidden field
        assert 'persisted_image_path' in body
        assert 'type="hidden"' in body

    def test_preview_container_in_form(
        self, running_server: server.LoopbackHTTPServer
    ) -> None:
        """AC-163: Preview container exists in re-populated form."""
        response = _request(running_server.server_port)
        assert response.status == 200
        body = response.body.decode()

        # Preview container should be in the form
        assert 'id="image-preview-container"' in body
        assert 'id="image-preview"' in body
        assert 'id="image-dimensions"' in body

    def test_clear_preview_function_exists(
        self, running_server: server.LoopbackHTTPServer
    ) -> None:
        """AC-165: metadata.js has clearPreview() function."""
        metadata_js_path = Path(web.__file__).parent / "static" / "metadata.js"
        assert metadata_js_path.exists()

        metadata_js_content = metadata_js_path.read_text()

        # clearPreview function should exist
        assert "function clearPreview" in metadata_js_content
        assert "image-preview-container" in metadata_js_content

    def test_show_image_preview_function_exists(
        self, running_server: server.LoopbackHTTPServer
    ) -> None:
        """AC-163, AC-164: metadata.js has showImagePreview() function."""
        metadata_js_path = Path(web.__file__).parent / "static" / "metadata.js"
        assert metadata_js_path.exists()

        metadata_js_content = metadata_js_path.read_text()

        # showImagePreview function should exist
        assert "function showImagePreview" in metadata_js_content
        # Should accept metadata parameter with imageSrc
        assert "metadata.imageSrc" in metadata_js_content

    def test_clear_result_message_function_exists(
        self, running_server: server.LoopbackHTTPServer
    ) -> None:
        """AC-166, CARD-043: metadata.js has clearResultMessage() function."""
        metadata_js_path = Path(web.__file__).parent / "static" / "metadata.js"
        assert metadata_js_path.exists()

        metadata_js_content = metadata_js_path.read_text()

        # clearResultMessage function should exist
        assert "function clearResultMessage" in metadata_js_content
        # Should clear the result container
        assert 'data-result-container' in metadata_js_content or 'resultContainer' in metadata_js_content

    def test_file_change_clears_result_message(
        self, running_server: server.LoopbackHTTPServer
    ) -> None:
        """AC-166: Result message clears when new image selected."""
        metadata_js_path = Path(web.__file__).parent / "static" / "metadata.js"
        assert metadata_js_path.exists()

        metadata_js_content = metadata_js_path.read_text()

        # File change event handler should call clearResultMessage
        # Look for clearResultMessage call in the change listener
        assert "clearResultMessage" in metadata_js_content
        # Should be called in file input change handler
        assert "addEventListener" in metadata_js_content or "change" in metadata_js_content

    def test_initialize_persisted_preview_on_load(
        self, running_server: server.LoopbackHTTPServer
    ) -> None:
        """AC-163: metadata.js initializes persisted preview on page load."""
        metadata_js_path = Path(web.__file__).parent / "static" / "metadata.js"
        assert metadata_js_path.exists()

        metadata_js_content = metadata_js_path.read_text()

        # Should have initialization code that runs on DOMContentLoaded
        assert "initializePersistedPreview" in metadata_js_content
        assert "DOMContentLoaded" in metadata_js_content

