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
``meta/kanban/cards/CARD-019.md`` declares (F-1 through F-9), the form page,
and the two boundaries guardrail G-4 draws.
"""

from __future__ import annotations

import ast
import http.client
import inspect
import re
import socket
import threading
from collections.abc import Iterator
from contextlib import closing, contextmanager
from pathlib import Path
from typing import NamedTuple

import pytest

from nonogram import cli, difficulty, export, web
from nonogram.web import handler, pages, server

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


# --------------------------------------------------------------------------
# Running-server helpers
# --------------------------------------------------------------------------


class _Response(NamedTuple):
    """One response, fully read, so the connection can be closed before asserts."""

    status: int
    headers: dict[str, str]
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
        return _Response(response.status, dict(response.getheaders()), response.read())
    finally:
        conn.close()


def _raw_exchange(port: int, request: bytes) -> bytes:
    """Send bytes the ``http.client`` API cannot express; read until close."""
    with closing(
        socket.create_connection((server.LOOPBACK_HOST, port), timeout=_PROBE_TIMEOUT_S)
    ) as sock:
        sock.sendall(request)
        received = b""
        while chunk := sock.recv(4096):
            received += chunk
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
        call it that gives a different answer. ``create_server`` and ``serve``
        therefore take a port and nothing else — a ``host=`` keyword would move
        the criterion out of the server and into every call site.
        """
        for function in (web.create_server, web.serve):
            assert list(inspect.signature(function).parameters) == ["port"], function

    def test_no_module_in_the_package_names_another_bind_address(self) -> None:
        """And no module reaches around that API either.

        The signature check above covers the front door; this covers a literal
        ``"0.0.0.0"`` or an ``INADDR_ANY`` appearing anywhere in ``src/`` — the
        way a "just for testing" widening actually gets in.
        """
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
        """Read off the source: COMP-008 cannot produce a challenge at all.

        The requests above show the endpoints that exist today are open; this
        shows there is no auth machinery in the package for a later card to
        reach for by accident. Same shape as the import guard — a property of
        the whole package, not of the routes one test happened to visit.
        """
        assert _WEB_SOURCES, "no web adapter sources found"
        for path in _WEB_SOURCES:
            source = path.read_text(encoding="utf-8")
            for token in ("WWW-Authenticate", "UNAUTHORIZED", "FORBIDDEN", "401", "403"):
                assert token not in source, f"{path.name} mentions {token}"


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
    ],
)
def test_an_unrouted_path_is_a_plain_404(
    running_server: server.LoopbackHTTPServer, path: str
) -> None:
    """F-7: one short text response, no traceback, no file ever served."""
    response = _request(running_server.server_port, path=path)

    assert response.status == 404
    assert response.headers["Content-Type"] == "text/plain; charset=utf-8"
    assert b"<" not in response.body


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


def test_a_malformed_request_line_is_a_400(
    running_server: server.LoopbackHTTPServer,
) -> None:
    """F-4: the stdlib rejects it before the router is ever reached."""
    received = _raw_exchange(
        running_server.server_port, b"this is not a request line\r\n\r\n"
    )

    assert b" 400 " in received


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
# The form page (FR-017) and the G-4 boundary
# --------------------------------------------------------------------------


def test_the_form_page_is_served_as_html(
    running_server: server.LoopbackHTTPServer,
) -> None:
    response = _request(running_server.server_port)

    assert response.status == 200
    assert response.headers["Content-Type"] == "text/html; charset=utf-8"
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
    """
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
    """
    for path in _WEB_SOURCES:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        raises = [node for node in ast.walk(tree) if isinstance(node, ast.Raise)]
        assert not raises, f"{path.name} raises at line {raises[0].lineno}"
