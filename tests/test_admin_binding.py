"""CARD-081 — the admin panel is reachable from this machine and nowhere else.

    AC-A  TestAdminPanel_BindsLoopbackOnlyByDefault
    AC-B  TestAdminPanel_DoesNotEnableTheDebuggerByDefault
    AC-C  TestAdminPanel_RefusesRequestsThatDidNotAddressThisMachine

Why this file exists at all: CARD-077's system contract asserted "admin action
bound to localhost like the rest of the admin (check: existing admin binding
tests)" and its review (cycle 1, F-003) found both halves false. There were no
admin binding tests — CON-009's declared check covers COMP-008's web server,
whose statement begins "The web UI's HTTP server" — and the admin's entry point
was ``app.run(host="0.0.0.0", port=5000, debug=True)``: every interface, plus a
Werkzeug console.

Deliberately shaped after ``tests/test_web_server.py``'s
``TestWebServer_BindsLoopbackOnlyByDefault`` rather than inventing a second
idiom for the same property, including its skip conditions — a host that cannot
tell a refused bind from a granted one says so instead of passing.

The one structural difference: the web adapter owns its socket, so the bind is
unreachable from outside. The admin runs under Flask, whose CLI owns ``--host``
(``ADMIN_SETUP.md`` documents ``flask --app nonogram.admin.app run``, which
defaults to loopback but can be widened with a flag this package cannot
remove). So the bind is tested here AND the Host-header refusal that stands
when the bind is widened.
"""

from __future__ import annotations

import inspect
import socket
import threading
import tokenize
from contextlib import closing, contextmanager
from pathlib import Path

import pytest
from werkzeug.serving import make_server
from werkzeug.test import EnvironBuilder

from nonogram.admin import app as admin_app

_INTERFACE_TIMEOUT_S = 2.0

#: Every admin source, swept for a widened bind address below. Evaluated once
#: at import and asserted non-empty inside the test that uses it — a glob that
#: silently matched nothing would report green while checking nothing.
_ADMIN_SOURCES = sorted(Path(admin_app.__file__).parent.rglob("*.py"))


# --------------------------------------------------------------------------
# Socket probes — same shapes as tests/test_web_server.py, same reasoning
# --------------------------------------------------------------------------


def _non_loopback_address() -> str | None:
    """This host's own non-loopback IPv4 address, or ``None`` if it has none."""
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
            sock.sendall(b"GET / HTTP/1.0\r\nHost: 127.0.0.1\r\n\r\n")
            return sock.recv(16).startswith(b"HTTP/")
    except OSError:
        return False


def _port_is_free_on(address: str, port: int) -> bool:
    """Whether ``address:port`` can still be bound while a server runs.

    A bare socket with no ``SO_REUSEADDR``, for the reason spelled out in
    ``test_web_server.py``: with that option set, BSD lets a specific-address
    bind succeed over a wildcard one, and the probe would answer "free" for a
    ``0.0.0.0`` server — destroying the point of it. The control below is what
    proves the probe still discriminates on this host.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((address, port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def _code_without_strings_or_comments(path: Path) -> str:
    """``path``'s source with every string literal and comment removed.

    So the sweep below reads what the module *does*, not what it says about
    itself. Tokenising rather than regex-stripping because a naive strip gets
    nested quotes and f-strings wrong, and a sweep that silently mangles its
    input reports green while checking something else.
    """
    pieces: list[str] = []
    with tokenize.open(path) as handle:
        for token in tokenize.generate_tokens(handle.readline):
            if token.type in (tokenize.STRING, tokenize.COMMENT):
                continue
            pieces.append(token.string)
    return "\n".join(pieces)


@contextmanager
def _running(host: str):
    """The real admin app on a real socket at ``host``, on an ephemeral port."""
    server = make_server(host, 0, admin_app.create_app(), threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


# --------------------------------------------------------------------------
# AC-A — the bind
# --------------------------------------------------------------------------


class TestAdminPanel_BindsLoopbackOnlyByDefault:
    """*Given* the admin panel started through its own entry point, *when* it
    binds its listening socket, *then* the socket is bound to 127.0.0.1 and
    nothing answers on any other interface.
    """

    def test_loopback_is_served(self) -> None:
        """The positive half — it does listen, so the negatives mean something."""
        with _running(admin_app.LOOPBACK_HOST) as server:
            assert _serves_on(admin_app.LOOPBACK_HOST, server.server_port) is True

    def test_no_other_interface_is_served(self) -> None:
        address = _non_loopback_address()
        if address is None:
            pytest.skip("host has no non-loopback IPv4 address to probe")

        with _running(admin_app.LOOPBACK_HOST) as server:
            with _running("0.0.0.0") as control:
                if not _serves_on(address, control.server_port):
                    pytest.skip(f"{address} is unreachable from this host even when bound")
                assert _serves_on(address, server.server_port) is False

    def test_the_port_stays_free_on_every_other_interface(self) -> None:
        """The firewall-independent half: the kernel never gave it that address."""
        address = _non_loopback_address()
        if address is None:
            pytest.skip("host has no non-loopback IPv4 address to probe")

        with _running("0.0.0.0") as control:
            if _port_is_free_on(address, control.server_port):
                pytest.skip("this host does not refuse a specific bind over a wildcard one")

        with _running(admin_app.LOOPBACK_HOST) as server:
            assert _port_is_free_on(address, server.server_port) is True

    def test_the_entry_point_passes_the_loopback_constant(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """``main()`` is what ``python -m nonogram.admin.app`` runs.

        The probes above prove a server bound to ``LOOPBACK_HOST`` is
        loopback-only; this is the other half of the claim — that the entry
        point is what hands it that address, rather than a default someone
        supplies at the call site.
        """
        captured: dict[str, object] = {}

        def fake_run(self, **kwargs):  # noqa: ANN001 - Flask.run's own signature
            captured.update(kwargs)

        monkeypatch.setattr("flask.Flask.run", fake_run)
        admin_app.main()

        assert captured["host"] == admin_app.LOOPBACK_HOST == "127.0.0.1"

    def test_no_api_in_the_module_can_widen_the_bind_address(self) -> None:
        """The bind address is a constant, not an argument.

        AC-A is only a property of the code if there is no supported way to
        call it that gives a different answer. ``main`` takes a port and
        nothing else; a ``host=`` keyword would move the criterion out of this
        module and into every call site.
        """
        assert list(inspect.signature(admin_app.main).parameters) == ["port"]

        for name in ("main", "create_app"):
            member = getattr(admin_app, name)
            parameters = set(inspect.signature(member).parameters)
            assert not parameters & {"host", "address", "bind", "interface"}, name

    def test_no_module_in_the_admin_package_names_another_bind_address(self) -> None:
        """And no module reaches around that entry point either.

        Covers a wildcard address appearing anywhere under ``admin/`` — the way
        a "just for testing" widening actually gets in, and exactly how the one
        this card removes survived for months.

        Swept over *code* rather than raw text: comments and docstrings are
        stripped first, because the module docstring this card wrote has to be
        able to say which address it replaced. ``test_web_server.py``'s version
        greps the raw source, which works there only because those modules
        never discuss the address they avoid — a constraint on prose, not on
        behaviour, and not one worth inheriting.
        """
        assert _ADMIN_SOURCES, "no admin sources found"
        for path in _ADMIN_SOURCES:
            code = _code_without_strings_or_comments(path)
            for token in ("0.0.0.0", "INADDR_ANY", "getfqdn", "gethostname"):
                assert token not in code, f"{path.name} names {token} in code"

    def test_the_loopback_host_constant_is_loopback(self) -> None:
        """A typo the probes might not catch.

        ``0.0.0.0`` would fail them; ``127.0.0.2``, on a host where the whole
        127/8 block is local, might not. Cheap complement to the behavioural
        tests, never a substitute — alone it would be the read-back assertion
        this AC must not rest on.
        """
        assert admin_app.LOOPBACK_HOST == "127.0.0.1"


# --------------------------------------------------------------------------
# AC-B — the debugger
# --------------------------------------------------------------------------


class TestAdminPanel_DoesNotEnableTheDebuggerByDefault:
    """A reachable Werkzeug console is remote code execution, not a leak.

    It was on together with the wildcard bind. The two were one defect and are
    fixed together, but they are independent properties and are tested apart.
    """

    def test_the_entry_point_does_not_ask_for_debug(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured: dict[str, object] = {}

        def fake_run(self, **kwargs):  # noqa: ANN001
            captured.update(kwargs)

        monkeypatch.setattr("flask.Flask.run", fake_run)
        admin_app.main()

        assert captured.get("debug") in (None, False)

    def test_a_default_app_is_not_in_debug_mode(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """With no FLASK_ENV saying otherwise — the state a bare run produces."""
        monkeypatch.delenv("FLASK_ENV", raising=False)

        assert admin_app.create_app().config["DEBUG"] is False

    def test_debug_is_still_available_when_asked_for(self) -> None:
        """Not a lockout: the opt-in path still works, it is just typed."""
        assert admin_app.create_app(debug=True).config["DEBUG"] is True


# --------------------------------------------------------------------------
# AC-C — the Host header, for when the bind is widened anyway
# --------------------------------------------------------------------------


class TestAdminPanel_RefusesRequestsThatDidNotAddressThisMachine:
    """The defence that survives ``flask run --host=0.0.0.0``.

    Flask's CLI owns ``--host`` and this package cannot take it away, so the
    bind alone cannot carry NFR-003 for the documented launch path. A request
    that did not address this machine is refused however it arrived.
    """

    @pytest.fixture
    def client(self):
        application = admin_app.create_app()
        application.config["TESTING"] = True
        with application.test_client() as client:
            yield client

    @pytest.mark.parametrize(
        "host",
        ["localhost", "localhost:5000", "127.0.0.1", "127.0.0.1:8888", "[::1]:5000"],
    )
    def test_a_request_addressed_to_this_machine_is_served(self, client, host) -> None:
        assert client.get("/", headers={"Host": host}).status_code == 200

    @pytest.mark.parametrize(
        "host",
        [
            pytest.param("evil.example.com", id="a-name"),
            pytest.param("192.168.1.50:5000", id="this-lan"),
            pytest.param("10.0.0.4", id="another-lan"),
            pytest.param("127.0.0.1.evil.com", id="loopback-as-a-prefix"),
            pytest.param("evil.com:80@127.0.0.1", id="loopback-after-an-at"),
            pytest.param("localhost.evil.com", id="localhost-as-a-prefix"),
        ],
    )
    def test_a_request_addressed_elsewhere_is_refused(self, client, host) -> None:
        assert client.get("/", headers={"Host": host}).status_code == 404

    def test_a_request_with_no_host_header_at_all_is_refused(self) -> None:
        """HTTP/1.1 requires one; a request without it is not a browser.

        Built at the WSGI environ level because the test client always supplies
        a Host, so it cannot express this case — which is also why the probe I
        first wrote for it passed for the wrong reason.
        """
        application = admin_app.create_app()
        environ = EnvironBuilder(path="/").get_environ()
        environ.pop("HTTP_HOST", None)
        environ["SERVER_NAME"] = "evil.example.com"
        environ["SERVER_PORT"] = "80"

        assert admin_app._host_is_local(None) is False
        with application.request_context(environ):
            from flask import request

            assert admin_app._host_is_local(request.headers.get("Host")) is False

    def test_the_refusal_does_not_announce_what_it_is_protecting(
        self, client
    ) -> None:
        """404, not 403: a refusal that distinguishes "wrong host" from "no
        such page" tells a scanner it found something."""
        elsewhere = client.get("/", headers={"Host": "evil.example.com"})
        missing = client.get("/no-such-page", headers={"Host": "127.0.0.1"})

        assert elsewhere.status_code == missing.status_code == 404

    def test_the_allowlist_and_the_web_adapters_agree(self) -> None:
        """Two short allowlists that agree is the intended shape (ADR-0007).

        ``admin`` may not import ``web`` laterally, so the frozenset is
        reimplemented. This test is the seam that keeps the copy honest — the
        import is legal here, in the test tree, exactly as
        ``solver/propagate.py``'s ``mask_runs`` is cross-checked against
        ``clues.encode_line`` from here rather than from ``src/``.
        """
        from nonogram.web.handler import ALLOWED_HOSTS as web_allowed
        from nonogram.web.handler import _host_is_local as web_host_is_local

        assert admin_app.ALLOWED_HOSTS == web_allowed

        # The allowlist is the easy half. These are the values where the two
        # could agree on the names and still disagree on the answer — every
        # one of them a shape urlsplit reads as loopback when it should not.
        for authority in (
            "localhost",
            "127.0.0.1:8888",
            "[::1]:5000",
            "evil.com:80@127.0.0.1",
            "127.0.0.1:",
            "127.0.0.1:evil",
            "127.0.0.1/../evil",
            "localhost?evil",
            "127.0.0.1#evil.example.com",
            "::1",
            "evil.example.com",
        ):
            assert admin_app._host_is_local(authority) is web_host_is_local(
                authority
            ), authority
