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

import ast
import inspect
import os
import re
import socket
import subprocess
import sys
import textwrap
import threading
import tokenize
import warnings
from contextlib import closing, contextmanager
from pathlib import Path

import pytest
from werkzeug.serving import make_server
from werkzeug.test import EnvironBuilder

from nonogram.admin import app as admin_app
from tests.helpers import undefined_table_report as diagnostic

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


# --------------------------------------------------------------------------
# CON-016's check ref (revised 2026-09-14, ADR-0030 / CARD-085)
# --------------------------------------------------------------------------


class TestAdminPanel_RefusesEveryRequestTheDoorInForceDoesNotAdmit:
    """CON-016 over **both** doors, which is what the revised wording states.

    CARD-081 wrote CON-016 as one rule about the ``Host`` header, and
    ``TestAdminPanel_RefusesRequestsThatDidNotAddressThisMachine`` above is
    still exactly that rule — untouched, and still run. What it cannot see is
    the mode ADR-0030 added: with ``ADMIN_ALLOWED_HOST`` set, the panel answers
    a hostname that names no machine of ours, which the old class had no way to
    express and would have had no reason to.

    That gap is why this class exists rather than an edit up there. A
    constraint whose only check exercises one of its two modes reports green
    while the other mode is unverified — the aspirational-green pattern, on a
    security constraint (CARD-085 review F-002).

    The clause both modes share, and the one that matters most, is **exclusivity**:
    no configuration serves a request on the strength of naming a loopback host
    *and* another on the strength of a credential. A panel with both doors open
    would make ``Host: localhost`` a password bypass.
    """

    REMOTE = "nonogram-admin.onrender.com"
    PASSWORD = "a-password-long-enough-to-boot"

    @staticmethod
    def _basic(user: str, password: str) -> dict[str, str]:
        import base64

        token = base64.b64encode(f"{user}:{password}".encode()).decode()
        return {"Authorization": f"Basic {token}"}

    @pytest.fixture
    def local_client(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("ADMIN_ALLOWED_HOST", raising=False)
        monkeypatch.delenv("DATABASE_URL", raising=False)
        application = admin_app.create_app()
        with application.test_client() as client:
            yield client

    @pytest.fixture
    def deployed_client(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("ADMIN_ALLOWED_HOST", self.REMOTE)
        monkeypatch.setenv("ADMIN_USER", "operator")
        monkeypatch.setenv("ADMIN_PASSWORD", self.PASSWORD)
        monkeypatch.setenv("SECRET_KEY", "a-real-production-secret")
        monkeypatch.delenv("DATABASE_URL", raising=False)
        application = admin_app.create_app()
        with application.test_client() as client:
            yield client

    def test_the_default_door_is_the_loopback_one(self, local_client) -> None:
        assert local_client.get("/", headers={"Host": "127.0.0.1"}).status_code == 200
        assert (
            local_client.get("/", headers={"Host": self.REMOTE}).status_code == 404
        )

    def test_the_default_door_asks_for_no_credential(self, local_client) -> None:
        response = local_client.get("/", headers={"Host": "localhost"})
        assert "WWW-Authenticate" not in response.headers

    def test_the_deployed_door_admits_only_the_configured_host(
        self, deployed_client
    ) -> None:
        credential = self._basic("operator", self.PASSWORD)
        assert (
            deployed_client.get(
                "/", headers={"Host": self.REMOTE, **credential}
            ).status_code
            == 200
        )
        for elsewhere in ("evil.example.com", f"{self.REMOTE}.evil.com"):
            assert (
                deployed_client.get(
                    "/", headers={"Host": elsewhere, **credential}
                ).status_code
                == 404
            ), elsewhere

    @pytest.mark.parametrize("host", ["localhost", "127.0.0.1", "[::1]:5000"])
    def test_the_doors_are_exclusive_so_loopback_is_not_a_bypass(
        self, deployed_client, host
    ) -> None:
        """The clause the whole revision turns on.

        Behind a proxy the ``Host`` header is written by the caller and
        ``REMOTE_ADDR`` is the proxy, so neither establishes that a request is
        local. Serving a loopback ``Host`` in deployed mode would hand anyone a
        way past the password.
        """
        response = deployed_client.get(
            "/", headers={"Host": host, **self._basic("operator", self.PASSWORD)}
        )
        assert response.status_code == 404

    def test_the_deployed_door_refuses_without_the_credential(
        self, deployed_client
    ) -> None:
        response = deployed_client.get("/", headers={"Host": self.REMOTE})
        assert response.status_code == 401

    def test_the_deployed_door_refuses_what_another_site_started(
        self, deployed_client
    ) -> None:
        """ADR-0030/R2 — the admin's copy of CON-010."""
        response = deployed_client.post(
            "/regrade",
            headers={
                "Host": self.REMOTE,
                **self._basic("operator", self.PASSWORD),
                "Sec-Fetch-Site": "cross-site",
            },
        )
        assert response.status_code == 403

    def test_a_missing_host_header_is_refused_in_both_modes(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """HTTP/1.1 requires one; a request without it is not a browser.

        Built at the WSGI environ level because the test client always supplies
        a Host — the same reason the CARD-081 class builds its version this way.
        """
        assert admin_app._hostname_of(None) is None
        assert admin_app._host_is_local(None) is False
        assert admin_app._host_is_the_configured_remote(None, self.REMOTE) is False


# --------------------------------------------------------------------------
# CARD-258 — the diagnostic that makes the next `relation "puzzles" does not
# exist` name what it was talking to
# --------------------------------------------------------------------------
#
# Why here. Four build gates (waves 47, 48, 50) reported the same five
# failures in `TestAdminPanel_RefusesRequestsThatDidNotAddressThisMachine`
# above — `relation "puzzles" does not exist`, solo, guard-enforced, green on
# a re-run of the same commit. Two explanations have been offered and both are
# dead (CARD-252's `reset_engine()` is in the tree and CARD-256's gates still
# ran red then green on it). This card does not try to fix that hazard. It
# makes the next occurrence carry the four things no traceback currently
# shows, so the sixth occurrence is a datum rather than a fifth re-run; the
# tests for it sit in the file whose failures are the motive.

#: What a probe subprocess needs on its path: the tree (for ``tests.*``) and
#: ``src`` (for ``nonogram.*``). A probe's rootdir is its own temp directory,
#: so pyproject's ``pythonpath = ["src"]`` does not reach it.
_SUBPROCESS_PYTHONPATH = os.pathsep.join(
    [str(Path(__file__).resolve().parent.parent),
     str(Path(__file__).resolve().parent.parent / "src")]
)

#: The import path a ``-p`` argument takes to load the diagnostic. The probes
#: below are run with and without it, and that pair is the control: AC-2 asks
#: for a diagnostic that can be shown *absent*.
_DIAGNOSTIC_MODULE = "tests.helpers.undefined_table_report"

#: A URL with a listener behind it on no host anybody runs: port 1. Used only
#: to make the capture path fail on purpose (AC-5). It ends in ``_test`` so it
#: passes the conftest refusal the capture consults, and it names a database
#: that has never existed — never ``nonogram_poc`` (G-2).
_CAPTURE_HAS_NO_SERVER_URL = (
    "postgresql://postgres:postgres@127.0.0.1:1/card258_capture_has_no_server_test"
)

#: Provokes the real error against a schema it created and dropped itself.
#:
#: ``public`` is never touched: the table is made in ``card258_probe``, the
#: search_path is pointed there, and the schema is dropped under it — so the
#: query is the shape the gate failures have, a connection looking where it
#: was told for a ``puzzles`` that is not there, without erasing the schema
#: the rest of the suite shares.
_PROBE_UNDEFINED_TABLE = '''
    import os

    from sqlalchemy import create_engine

    from nonogram.db import session as app_session
    from tests import db_name


    def test_a_query_against_a_schema_this_test_dropped_itself():
        url = db_name.resolve_test_database_url(os.environ, db_name.REPO_ROOT)
        # So that the module-global engine exists and has been reset once:
        # group 2 of the report is about that object, and a probe that never
        # built one would leave that branch unmeasured.
        os.environ["DATABASE_URL"] = url
        app_session.reset_engine()
        app_session.get_session().close()

        engine = create_engine(
            app_session.normalized_url(url), **app_session._engine_options(url)
        )
        connection = engine.connect()
        connection.exec_driver_sql("DROP SCHEMA IF EXISTS card258_probe CASCADE")
        connection.exec_driver_sql("CREATE SCHEMA card258_probe")
        connection.exec_driver_sql("CREATE TABLE card258_probe.puzzles (id integer)")
        connection.commit()
        connection.exec_driver_sql("SET search_path TO card258_probe")
        connection.exec_driver_sql("DROP SCHEMA card258_probe CASCADE")
        connection.commit()
        connection.exec_driver_sql("SELECT 1 FROM puzzles")
'''

#: A name the destructive fixtures are not allowed to touch, behind a port
#: nothing listens on. Invented, never any database that exists, and the two
#: outcomes it can produce are distinguishable: ``NOT OPENED`` means the
#: suite's refusal fired before anything was opened, ``FAILED`` would mean the
#: capture tried to connect.
_CAPTURE_REFUSED_URL = (
    "postgresql://postgres:postgres@127.0.0.1:1/nonogram_refused_by_design"
)

#: Provokes the error on a database that is **not** the one the capture
#: resolves to, which is the other half of the card's one-line proof.
#:
#: The same host and credentials, a different database: PostgreSQL's
#: maintenance database, which every installation has and which this suite
#: already opens in order to create its own (``conftest._MAINTENANCE_DATABASE``).
#: Nothing there is created, written to or dropped -- the statement fails on
#: its first relation lookup, which is the whole point of choosing it.
_PROBE_FAILING_CONNECTION_ELSEWHERE = '''
    import os

    from sqlalchemy import create_engine
    from sqlalchemy.engine import make_url

    from nonogram.db import session as app_session
    from tests import db_name


    def test_a_query_on_a_database_that_is_not_the_suites():
        resolved = db_name.resolve_test_database_url(os.environ, db_name.REPO_ROOT)
        # render_as_string, not str(): str() renders the password as *** and
        # the engine would then be unable to authenticate.
        elsewhere = make_url(resolved).set(database="postgres").render_as_string(
            hide_password=False
        )
        engine = create_engine(
            app_session.normalized_url(elsewhere),
            **app_session._engine_options(resolved),
        )
        engine.connect().exec_driver_sql("SELECT 1 FROM puzzles")
'''

#: An ordinary assertion failure — AC-3's selection.
_PROBE_ORDINARY_ASSERTION = '''
    def test_an_ordinary_assertion_failure():
        left = 1
        right = 2
        assert left == right
'''

#: A pass and a skip — AC-4's selection, skip profile included.
_PROBE_PASSING_AND_SKIPPED = '''
    import pytest


    def test_this_one_passes():
        assert True


    @pytest.mark.skip(reason="the skip profile is half of AC-4")
    def test_this_one_skips():
        raise AssertionError("never runs")
'''

#: The error class with nothing behind it: no cursor, no connection, and a
#: capture URL pointing at a port nothing listens on. AC-5's selection, and
#: deliberately free of any database so it runs wherever the suite does.
_PROBE_CAPTURE_CANNOT_CONNECT = '''
    import psycopg2.errors


    def test_an_undefined_table_the_hook_can_find_no_database_for():
        raise psycopg2.errors.UndefinedTable('relation "puzzles" does not exist')
'''


def _without_durations(output: str) -> str:
    """``output`` with every ``N.NNs`` duration replaced by a fixed token.

    The only thing that moves between two runs of the same selection is how
    long it took, and the byte comparisons below are about everything else.
    Erasing the figure is also the only way to compare without recording one.
    """
    return re.sub(r"\d+\.\d+s", "<duration>s", output)


def _without_addresses(output: str) -> str:
    """``output`` with every ``0x...`` object address replaced by a token.

    Two processes print different ``id()`` values for the same objects, and a
    default traceback prints a few of them (SQLAlchemy's ``self =`` lines).
    They are the only other thing that moves between two runs of the same
    selection, so the AC-1 comparison erases them and says so; the AC-3 and
    AC-4 comparisons need no such thing and do not use this.
    """
    return re.sub(r"0x[0-9a-f]+", "0x<address>", output)


def _probe_run(
    directory: Path,
    filename: str,
    source: str,
    *,
    with_hook: bool,
    env_overrides: dict[str, str] | None = None,
) -> str:
    """Run one throwaway test file under a subprocess pytest.

    ``directory`` is its own rootdir, so this tree's ``conftest.py`` — and
    with it CARD-255's lock guard, which must never be disturbed — is not
    loaded at all. The hook therefore arrives by ``-p`` or not at all, and
    "not at all" is the control.
    """
    path = Path(directory) / filename
    path.write_text(textwrap.dedent(source), encoding="utf-8")
    command = [
        sys.executable, "-m", "pytest", str(path),
        "--no-header", "-p", "no:cacheprovider",
    ]
    if with_hook:
        command += ["-p", _DIAGNOSTIC_MODULE]
    env = {**os.environ, "PYTHONPATH": _SUBPROCESS_PYTHONPATH}
    env.update(env_overrides or {})
    completed = subprocess.run(
        command, cwd=str(directory), capture_output=True, text=True,
        timeout=300, env=env,
    )
    return _without_durations(completed.stdout + completed.stderr)


def _without_the_diagnostic_section(output: str) -> str:
    """``output`` with the diagnostic's own section block removed.

    Used to hold the rest of the report byte-identical: AC-1 asks that the
    test still fail with its original traceback intact, and the way to show
    that is to take the addition back out and compare what is left.
    """
    kept: list[str] = []
    dropping = False
    for line in output.splitlines(keepends=True):
        if dropping:
            if line.startswith("="):
                dropping = False
            else:
                continue
        if diagnostic.SECTION_NAME in line and line.lstrip().startswith("-"):
            dropping = True
            continue
        kept.append(line)
    return "".join(kept)


#: The labels AC-1 requires, one per group of the card's four.
_FOUR_GROUPS = (
    "group-1 failing-connection:",
    "group-2 app-engine:",
    "group-3 process:",
    "group-4 capture-connection:",
)


@pytest.fixture(scope="module")
def undefined_table_probe_runs(tmp_path_factory) -> tuple[str, str]:
    """The provoking probe, run twice: with the diagnostic and without it."""
    directory = tmp_path_factory.mktemp("card258_undefined_table")
    with_hook = _probe_run(
        directory, "probe_undefined_table.py", _PROBE_UNDEFINED_TABLE,
        with_hook=True,
    )
    without_hook = _probe_run(
        directory, "probe_undefined_table.py", _PROBE_UNDEFINED_TABLE,
        with_hook=False,
    )
    return with_hook, without_hook


class TestUndefinedTableReport_NamesWhatTheFailingConnectionWasTalkingTo:
    """CARD-258. The next ``relation "puzzles" does not exist`` says what it
    was talking to: which database, which engine, which process and thread,
    and what the schema held at that moment.
    """

    @pytest.mark.db_required
    def test_the_report_carries_the_four_groups(
        self, undefined_table_probe_runs
    ) -> None:
        """AC-1, first half: all four of the card's groups are in the report."""
        with_hook, _ = undefined_table_probe_runs

        assert diagnostic.SECTION_NAME in with_hook, with_hook
        for label in _FOUR_GROUPS:
            assert label in with_hook, (label, with_hook)

    @pytest.mark.db_required
    def test_the_report_names_the_database_the_failing_connection_was_on(
        self, undefined_table_probe_runs
    ) -> None:
        """AC-1: concrete values, not labels with nothing behind them.

        The derived database name (CARD-244) appears against the *failing*
        connection, a backend pid is a number, and the schema question is
        answered — which is the one-line proof the card is asking for.
        """
        from tests import db_name

        with_hook, _ = undefined_table_probe_runs
        expected = db_name.derive_test_database_name(db_name.REPO_ROOT)

        failing = _section_line(with_hook, "group-1 failing-connection:")
        assert f"dbname={expected}" in failing, failing
        assert re.search(r"backend_pid=\d+", failing), failing

        statement = _section_line(with_hook, "group-1 failing-statement:")
        assert statement.endswith("SELECT 1 FROM puzzles"), statement

        schema = _section_line(with_hook, "group-4 schema-now:")
        assert "to_regclass('public.puzzles')=" in schema, schema

        # The server's own view of the failing backend, which is the one datum
        # here that does not come through libpq -- so it is a cross-check on
        # the line above and not a second reading of it.
        server = _section_line(with_hook, "group-4 failing-backend-from-server:")
        assert f"datname={expected}" in server, server
        assert "query=SELECT 1 FROM puzzles" in server, server

        # The one-line proof the card asks for, either way round.
        verdict = _section_line(with_hook, "group-4 verdict:")
        assert verdict.endswith("MATCH"), verdict

    @pytest.mark.db_required
    def test_the_report_names_the_engine_its_pool_and_the_reset_count(
        self, undefined_table_probe_runs
    ) -> None:
        """AC-1, group 2 — down to the counter the card asks for."""
        with_hook, _ = undefined_table_probe_runs

        engine = _section_line(with_hook, "group-2 app-engine:")
        assert re.search(r"id=0x[0-9a-f]+", engine), engine
        assert "pool=" in engine, engine
        assert "reset_engine_calls=1" in engine, engine

    @pytest.mark.db_required
    def test_the_report_names_the_process_the_thread_and_the_werkzeug_question(
        self, undefined_table_probe_runs
    ) -> None:
        """AC-1, group 3 — and the card's "confirm rather than assume"."""
        with_hook, _ = undefined_table_probe_runs

        process = _section_line(with_hook, "group-3 process:")
        assert re.search(r"pid=\d+", process), process
        assert "hook_thread=" in process, process
        assert "alive_threads=" in process, process

        frames = _section_line(with_hook, "group-3 traceback:")
        assert "werkzeug_frames=" in frames, frames

    @pytest.mark.db_required
    def test_the_capture_answers_while_the_failing_connection_cannot(
        self, undefined_table_probe_runs
    ) -> None:
        """The trap, measured.

        The connection that raised is in an aborted transaction — the report
        says so, from libpq and without a query — and the capture answers
        anyway, because it is a different connection. An implementation that
        asked the failing connection would print ``InFailedSqlTransaction``
        here instead of a database name.
        """
        with_hook, _ = undefined_table_probe_runs

        failing = _section_line(with_hook, "group-1 failing-connection:")
        assert "txn_status=INERROR" in failing, failing

        capture = _section_line(with_hook, "group-4 capture-connection:")
        assert "current_database=" in capture, capture
        assert "search_path=" in capture, capture
        assert "FAILED" not in capture, capture
        assert "InFailedSqlTransaction" not in with_hook, with_hook

    @pytest.mark.db_required
    def test_the_original_traceback_is_intact_and_the_control_can_fail(
        self, undefined_table_probe_runs
    ) -> None:
        """AC-1's second half and AC-2 in one comparison.

        Take the section back out and the two runs are byte-identical: the
        diagnostic adds a section and changes nothing else. The same
        comparison is AC-2's control — without the hook the section is not
        there to take out, and every assertion above reads a line of it.
        """
        with_hook, without_hook = undefined_table_probe_runs

        assert "relation \"puzzles\" does not exist" in without_hook, without_hook
        assert diagnostic.SECTION_NAME not in without_hook, without_hook
        for label in _FOUR_GROUPS:
            assert label not in without_hook, (label, without_hook)
        assert _without_addresses(
            _without_the_diagnostic_section(with_hook)
        ) == _without_addresses(without_hook)

    @pytest.mark.db_required
    def test_a_connection_on_the_wrong_database_is_a_one_line_proof(
        self, tmp_path: Path
    ) -> None:
        """The verdict's MISMATCH arm -- the card's headline scenario.

        The next occurrence "either proves the connection was attached to the
        wrong database, or proves it was attached to the right one". The probe
        the tests above read measures the second. This measures the first, and
        without it MISMATCH would be a branch nothing in the suite ever took.
        """
        from tests import db_name

        output = _probe_run(
            tmp_path, "probe_elsewhere.py", _PROBE_FAILING_CONNECTION_ELSEWHERE,
            with_hook=True,
        )
        expected = db_name.derive_test_database_name(db_name.REPO_ROOT)

        failing = _section_line(output, "group-1 failing-connection:")
        assert "dbname=postgres" in failing, failing

        server = _section_line(output, "group-4 failing-backend-from-server:")
        assert "datname=postgres" in server, server

        verdict = _section_line(output, "group-4 verdict:")
        assert f"capture-dbname={expected}" in verdict, verdict
        assert verdict.endswith("MISMATCH"), verdict

    def test_an_ordinary_assertion_failure_is_byte_identical(
        self, tmp_path: Path
    ) -> None:
        """AC-3. The hook fires on the exception class and on nothing else."""
        with_hook = _probe_run(
            tmp_path, "probe_assertion.py", _PROBE_ORDINARY_ASSERTION,
            with_hook=True,
        )
        without_hook = _probe_run(
            tmp_path, "probe_assertion.py", _PROBE_ORDINARY_ASSERTION,
            with_hook=False,
        )

        assert "1 failed" in without_hook, without_hook
        assert with_hook == without_hook

    def test_a_passing_run_with_a_skip_is_byte_identical(
        self, tmp_path: Path
    ) -> None:
        """AC-4. Nothing on the happy path, skip profile included."""
        with_hook = _probe_run(
            tmp_path, "probe_passing.py", _PROBE_PASSING_AND_SKIPPED,
            with_hook=True,
        )
        without_hook = _probe_run(
            tmp_path, "probe_passing.py", _PROBE_PASSING_AND_SKIPPED,
            with_hook=False,
        )

        assert "1 passed, 1 skipped" in without_hook, without_hook
        assert with_hook == without_hook

    def test_a_capture_that_cannot_connect_is_named_not_swallowed(
        self, tmp_path: Path
    ) -> None:
        """AC-5. The diagnostic never masks the defect it was built for."""
        output = _probe_run(
            tmp_path, "probe_no_server.py", _PROBE_CAPTURE_CANNOT_CONNECT,
            with_hook=True,
            env_overrides={"TEST_DATABASE_URL": _CAPTURE_HAS_NO_SERVER_URL},
        )

        # The test's own failure, still reported and still first.
        assert "UndefinedTable" in output, output
        assert "1 failed" in output, output
        # …and the capture's failure, named.
        capture = _section_line(output, "group-4 capture-connection:")
        assert "FAILED" in capture, capture
        assert "card258_capture_has_no_server_test" in capture, capture
        # …while the groups that need no connection still answer.
        assert _section_line(output, "group-3 process:"), output

    def test_the_capture_will_not_connect_to_a_database_the_suite_refuses(
        self, tmp_path: Path
    ) -> None:
        """G-2, with a control that can fail.

        The capture asks the suite's own refusal (``conftest._refusal_reason``)
        before it opens anything, so a ``TEST_DATABASE_URL`` naming a database
        the destructive fixtures may not touch is reported and never connected
        to. Remove that consult and this test reds with ``FAILED`` in place of
        ``NOT OPENED`` -- which is the difference between a refusal and an
        attempt.
        """
        output = _probe_run(
            tmp_path, "probe_refused.py", _PROBE_CAPTURE_CANNOT_CONNECT,
            with_hook=True,
            env_overrides={"TEST_DATABASE_URL": _CAPTURE_REFUSED_URL},
        )

        capture = _section_line(output, "group-4 capture-connection:")
        assert "NOT OPENED" in capture, capture
        assert "FAILED" not in capture, capture
        assert "nonogram_refused_by_design" in capture, capture
        assert "1 failed" in output, output

    def test_the_diagnostic_is_registered_in_this_very_run(
        self, pytestconfig
    ) -> None:
        """AC-2's other half: wired into *this* suite, not only into a ``-p``.

        Reds the moment the conftest stops registering it, which no subprocess
        measurement above can see.
        """
        manager = pytestconfig.pluginmanager

        assert manager.hasplugin(diagnostic.PLUGIN_NAME)
        assert manager.get_plugin(diagnostic.PLUGIN_NAME) is diagnostic

    def test_the_plugin_implements_exactly_one_hook_and_it_is_the_failure_one(
        self,
    ) -> None:
        """G-4, structurally.

        The byte comparisons above show this selection pays nothing. This is
        the general half: the module defines one hook, and it is the one
        pytest calls only when an exception is being reported. A
        ``pytest_runtest_setup`` added here would be a per-test tax levied
        forever, and it would red this.
        """
        tree = ast.parse(Path(diagnostic.__file__).read_text(encoding="utf-8"))
        hooks = {
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("pytest_")
        }

        assert hooks == {"pytest_exception_interact"}

    @pytest.mark.parametrize(
        ("error", "found"),
        [
            pytest.param("undefined_table_with_a_sqlstate", True, id="pgcode"),
            pytest.param("undefined_table_without_a_sqlstate", True, id="class"),
            pytest.param("wrapped_undefined_table", True, id="wrapped"),
            pytest.param("undefined_column", False, id="another-sqlstate"),
            pytest.param("plain_programming_error", False, id="no-sqlstate"),
            pytest.param("assertion_error", False, id="an-assertion"),
            pytest.param("nothing", False, id="no-exception"),
        ],
    )
    def test_the_detector_fires_on_the_error_class_and_nothing_else(
        self, error: str, found: bool
    ) -> None:
        """Each arm of the detector, and each arm's negative.

        Two spellings reach the same verdict and they are both live: the real
        error carries ``pgcode`` **and** the class, while a hand-built one
        carries only the class — so neither arm can be deleted on the grounds
        that the other covers it.
        """
        assert (diagnostic.undefined_table_error(_fabricate(error)) is not None) is found

    def test_nothing_in_src_calls_the_reset_counter(self) -> None:
        """G-1. The accessor is additive: the test tree is its only caller.

        Enumerated from ``src`` by AST rather than read, so a call added
        anywhere under it reds this — including one written after this card.
        """
        src = Path(__file__).resolve().parent.parent / "src"
        sources = sorted(src.rglob("*.py"))
        assert sources, "the sweep matched no sources"

        callers = []
        for path in sources:
            with warnings.catch_warnings():
                # A stray escape sequence somewhere under src is somebody
                # else's defect, not this test's warning to emit.
                warnings.simplefilter("ignore")
                tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                name = func.attr if isinstance(func, ast.Attribute) else getattr(
                    func, "id", None
                )
                if name == "reset_count":
                    callers.append(f"{path}:{node.lineno}")

        assert callers == []


def _section_line(output: str, label: str) -> str:
    """The diagnostic's line beginning ``label``, or ``""`` if there is none."""
    for line in output.splitlines():
        if line.startswith(label):
            return line
    return ""


def _fabricate(kind: str):
    """One exception per arm of :func:`undefined_table_error`'s decision.

    Built by hand rather than provoked, because the point is the decision and
    not the database: two of these shapes (a wrapped error, an error with no
    ``pgcode`` at all) are exactly what a provoked one is not.
    """
    import psycopg2.errors
    from sqlalchemy import exc as sa_exc

    if kind == "nothing":
        return None
    if kind == "assertion_error":
        return AssertionError("1 == 2")
    if kind == "undefined_table_without_a_sqlstate":
        return psycopg2.errors.UndefinedTable('relation "puzzles" does not exist')
    if kind == "undefined_column":
        return _with_sqlstate(psycopg2.errors.UndefinedColumn("no such column"), "42703")
    if kind == "plain_programming_error":
        return psycopg2.ProgrammingError("something else entirely")
    if kind == "undefined_table_with_a_sqlstate":
        return _with_sqlstate(
            psycopg2.errors.UndefinedTable('relation "puzzles" does not exist'),
            "42P01",
        )
    if kind == "wrapped_undefined_table":
        # A real exception object, because ``__cause__`` will not take
        # anything else — which is also why the sqlstate arm has to be put in
        # front of a wrapper rather than a chain.
        inner = psycopg2.errors.UndefinedTable('relation "puzzles" does not exist')
        outer = sa_exc.ProgrammingError("SELECT 1 FROM puzzles", {}, inner)
        outer.__cause__ = inner
        return outer
    raise AssertionError(f"unknown fabrication: {kind!r}")


class _WithSqlstate:
    """A psycopg2 error with a settable ``pgcode``.

    ``psycopg2.Error.pgcode`` is a read-only C attribute, so the only way to
    put the sqlstate arm of the detector in front of a value is to wrap one.
    The wrapper keeps the real class, which is what makes the pair of arms
    distinguishable at all.
    """

    def __init__(self, error, sqlstate: str) -> None:
        self._error = error
        self.pgcode = sqlstate

    def __getattr__(self, name: str):
        return getattr(self._error, name)


def _with_sqlstate(error, sqlstate: str):
    return _WithSqlstate(error, sqlstate)
