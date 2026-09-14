"""CARD-085 — the admin panel's two mutually exclusive doors.

    TestAdminAuth_LocalModeIsUnchanged                  (AC-1, G-1)
    TestAdminAuth_DeployedModeRequiresACredential       (AC-2)
    TestAdminAuth_DeployedModeHasNoLoopbackBypass       (AC-3)
    TestAdminAuth_RefusesToBootMisconfigured            (AC-4)
    TestAdminAuth_EveryRouteIsBehindTheCredential       (AC-5)
    TestAdminAuth_ComparesBothHalvesWithoutShortCircuit (AC-6)

CARD-081 made the admin answer only to this machine, because it has no
authentication and a route that rewrites every stored grade. That is still the
default. This card adds one alternative: a single configured hostname, behind a
credential — and the two are exclusive, so there is never a request that is
admitted by the weaker of the two rules.

The env vars are set through ``monkeypatch`` in every test. They are read once,
inside ``create_app``, so a test that forgot to set one would silently exercise
the other mode; each fixture below therefore names every variable it depends
on, including the ones it deliberately unsets.
"""

from __future__ import annotations

import ast
import base64
import inspect
from pathlib import Path

import pytest

from nonogram.admin import app as admin_app

REMOTE = "nonogram-admin.onrender.com"
USER = "olga"
PASSWORD = "correct-horse-battery-staple"
REAL_KEY = "a-long-random-production-secret"


def basic(user: str, password: str) -> dict[str, str]:
    """An HTTP Basic ``Authorization`` header, built the way a browser does."""
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


@pytest.fixture
def local_client(monkeypatch: pytest.MonkeyPatch):
    """The default panel: loopback only, no credential (CARD-081)."""
    monkeypatch.delenv(admin_app.REMOTE_HOST_VAR, raising=False)
    monkeypatch.delenv(admin_app.ADMIN_PASSWORD_VAR, raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    application = admin_app.create_app()
    application.config["TESTING"] = True
    with application.test_client() as client:
        yield client


@pytest.fixture
def deployed_app(monkeypatch: pytest.MonkeyPatch):
    """The panel configured for remote access, correctly."""
    monkeypatch.setenv(admin_app.REMOTE_HOST_VAR, REMOTE)
    monkeypatch.setenv(admin_app.ADMIN_USER_VAR, USER)
    monkeypatch.setenv(admin_app.ADMIN_PASSWORD_VAR, PASSWORD)
    monkeypatch.setenv("SECRET_KEY", REAL_KEY)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    application = admin_app.create_app()
    application.config["TESTING"] = True
    return application


@pytest.fixture
def deployed_client(deployed_app):
    with deployed_app.test_client() as client:
        yield client


# --------------------------------------------------------------------------
# AC-1 / G-1 — the default is untouched
# --------------------------------------------------------------------------


class TestAdminAuth_LocalModeIsUnchanged:
    """With no remote host configured, this card is invisible.

    CARD-081's own test class is the real assertion here and it runs unmodified
    (G-1). These restate the two ends of it against the new code path, so a
    refactor that accidentally routed local mode through the credential check
    fails in this file too, next to the change that would have caused it.
    """

    @pytest.mark.parametrize("host", ["localhost", "127.0.0.1:8888", "[::1]:5000"])
    def test_this_machine_is_served_with_no_credential(
        self, local_client, host
    ) -> None:
        assert local_client.get("/", headers={"Host": host}).status_code == 200

    @pytest.mark.parametrize("host", [REMOTE, "evil.example.com", "10.0.0.4"])
    def test_anywhere_else_is_refused_with_a_404(self, local_client, host) -> None:
        assert local_client.get("/", headers={"Host": host}).status_code == 404

    def test_no_challenge_is_ever_issued(self, local_client) -> None:
        """Local mode must not advertise a credential it does not check.

        A ``WWW-Authenticate`` here would invite someone to send a password
        that nothing validates — the worst of both designs.
        """
        for host in ("localhost", REMOTE, "evil.example.com"):
            response = local_client.get("/", headers={"Host": host})
            assert "WWW-Authenticate" not in response.headers


# --------------------------------------------------------------------------
# AC-2 — the deployed door needs the credential
# --------------------------------------------------------------------------


class TestAdminAuth_DeployedModeRequiresACredential:
    """At the configured hostname, the password is the whole of the defence."""

    def test_the_right_credential_is_served(self, deployed_client) -> None:
        response = deployed_client.get(
            "/", headers={"Host": REMOTE, **basic(USER, PASSWORD)}
        )
        assert response.status_code == 200

    @pytest.mark.parametrize(
        "headers, label",
        [
            pytest.param({}, "absent", id="no-header"),
            pytest.param(basic(USER, ""), "empty password", id="empty-password"),
            pytest.param(basic("", PASSWORD), "empty user", id="empty-user"),
            pytest.param(basic(USER, "wrong"), "wrong password", id="wrong-password"),
            pytest.param(basic("nobody", PASSWORD), "wrong user", id="wrong-user"),
            pytest.param(
                basic(USER, PASSWORD + " "), "trailing space", id="near-miss-password"
            ),
            pytest.param(
                {"Authorization": "Basic not-valid-base64!!"},
                "malformed",
                id="malformed",
            ),
            pytest.param(
                {"Authorization": f"Bearer {PASSWORD}"}, "wrong scheme", id="bearer"
            ),
        ],
    )
    def test_anything_else_is_401(self, deployed_client, headers, label) -> None:
        response = deployed_client.get("/", headers={"Host": REMOTE, **headers})
        assert response.status_code == 401, label

    def test_the_401_carries_a_challenge_so_a_browser_prompts(
        self, deployed_client
    ) -> None:
        """Without this header a browser shows a blank error, not a login box.

        The one refusal in this module that is deliberately legible: reaching
        the configured hostname already proves the caller knows the service is
        there, so naming what is missing costs nothing the 404 was protecting.
        """
        response = deployed_client.get("/", headers={"Host": REMOTE})

        challenge = response.headers.get("WWW-Authenticate", "")
        assert challenge.startswith("Basic "), challenge
        assert 'realm="Nonogram admin"' in challenge

    def test_a_wrong_credential_never_reaches_the_database(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """G-5: the refusal is free, and the proof is an unusable database.

        ``DATABASE_URL`` points at a black-holed address. A 401 that took the
        normal view path would raise ``OperationalError`` or hang; one that
        returns promptly did not open a socket. This is the same probe that
        established the Render 404s were not a database fault.
        """
        monkeypatch.setenv(admin_app.REMOTE_HOST_VAR, REMOTE)
        monkeypatch.setenv(admin_app.ADMIN_USER_VAR, USER)
        monkeypatch.setenv(admin_app.ADMIN_PASSWORD_VAR, PASSWORD)
        monkeypatch.setenv("SECRET_KEY", REAL_KEY)
        monkeypatch.setenv(
            "DATABASE_URL", "postgresql://nobody:nobody@203.0.113.1:5432/nope"
        )

        application = admin_app.create_app()
        with application.test_client() as client:
            response = client.get("/puzzles", headers={"Host": REMOTE})

        assert response.status_code == 401


# --------------------------------------------------------------------------
# AC-3 — the door that is shut is really shut
# --------------------------------------------------------------------------


class TestAdminAuth_DeployedModeHasNoLoopbackBypass:
    """``Host: localhost`` is not a password.

    The failure this class exists to prevent: keeping CARD-081's loopback
    branch alive alongside the credential branch, so that a caller who writes
    ``Host: localhost`` is admitted by the rule that asks for nothing. Behind a
    proxy the ``Host`` header is written by the caller and ``REMOTE_ADDR`` is
    the proxy, so neither can distinguish a local request from a forged claim
    of one — which is why deployed mode *replaces* the loopback rule instead of
    adding to it.
    """

    @pytest.mark.parametrize("host", ["localhost", "127.0.0.1", "[::1]:5000"])
    def test_a_loopback_host_is_refused_even_with_the_right_credential(
        self, deployed_client, host
    ) -> None:
        response = deployed_client.get(
            "/", headers={"Host": host, **basic(USER, PASSWORD)}
        )
        assert response.status_code == 404

    @pytest.mark.parametrize("host", ["localhost", "127.0.0.1"])
    def test_a_loopback_host_is_not_even_offered_the_challenge(
        self, deployed_client, host
    ) -> None:
        """404 and no challenge: it is the wrong host, not a missing password."""
        response = deployed_client.get("/", headers={"Host": host})

        assert response.status_code == 404
        assert "WWW-Authenticate" not in response.headers

    @pytest.mark.parametrize(
        "host",
        [
            pytest.param(f"{REMOTE}.evil.com", id="configured-host-as-a-prefix"),
            pytest.param(f"evil.com:80@{REMOTE}", id="configured-host-after-an-at"),
            pytest.param(f"evil.{REMOTE}", id="configured-host-as-a-suffix"),
            pytest.param("", id="empty"),
        ],
    )
    def test_a_near_miss_hostname_is_refused(self, deployed_client, host) -> None:
        """The deployed door is an equality test, not a substring one."""
        response = deployed_client.get(
            "/", headers={"Host": host, **basic(USER, PASSWORD)}
        )
        assert response.status_code == 404

    def test_the_configured_host_is_matched_case_insensitively(
        self, deployed_client
    ) -> None:
        """DNS is case-insensitive, so a capital must not 404 inexplicably."""
        response = deployed_client.get(
            "/", headers={"Host": REMOTE.upper(), **basic(USER, PASSWORD)}
        )
        assert response.status_code == 200

    def test_the_port_is_ignored_but_its_shape_is_not(self, deployed_client) -> None:
        response = deployed_client.get(
            "/", headers={"Host": f"{REMOTE}:443", **basic(USER, PASSWORD)}
        )
        assert response.status_code == 200

        malformed = deployed_client.get(
            "/", headers={"Host": f"{REMOTE}:evil", **basic(USER, PASSWORD)}
        )
        assert malformed.status_code == 404


# --------------------------------------------------------------------------
# AC-4 — a misconfigured deploy does not boot
# --------------------------------------------------------------------------


class TestAdminAuth_RefusesToBootMisconfigured:
    """The failure mode this prevents is the only unrecoverable one.

    A build that dies is fixed in a minute. A panel that came up reachable and
    unauthenticated has already been reachable and unauthenticated, and no
    later fix undoes who visited it.
    """

    @pytest.fixture(autouse=True)
    def _remote_configured(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv(admin_app.REMOTE_HOST_VAR, REMOTE)
        monkeypatch.delenv("DATABASE_URL", raising=False)

    def test_no_password_is_fatal(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(admin_app.ADMIN_PASSWORD_VAR, raising=False)
        monkeypatch.setenv("SECRET_KEY", REAL_KEY)

        with pytest.raises(admin_app.AdminConfigurationError) as caught:
            admin_app.create_app()

        assert admin_app.ADMIN_PASSWORD_VAR in str(caught.value)

    def test_an_empty_password_is_fatal_too(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """``ADMIN_PASSWORD=`` is how a forgotten value actually looks."""
        monkeypatch.setenv(admin_app.ADMIN_PASSWORD_VAR, "")
        monkeypatch.setenv("SECRET_KEY", REAL_KEY)

        with pytest.raises(admin_app.AdminConfigurationError):
            admin_app.create_app()

    def test_the_development_secret_key_is_fatal(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A key published in this repository cannot sign a reachable session."""
        monkeypatch.setenv(admin_app.ADMIN_PASSWORD_VAR, PASSWORD)
        monkeypatch.delenv("SECRET_KEY", raising=False)

        with pytest.raises(admin_app.AdminConfigurationError) as caught:
            admin_app.create_app()

        assert "SECRET_KEY" in str(caught.value)

    def test_setting_the_key_to_the_dev_value_explicitly_is_also_fatal(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The check is on the value, not on whether the variable was set."""
        monkeypatch.setenv(admin_app.ADMIN_PASSWORD_VAR, PASSWORD)
        monkeypatch.setenv("SECRET_KEY", admin_app.DEV_SECRET_KEY)

        with pytest.raises(admin_app.AdminConfigurationError):
            admin_app.create_app()

    def test_a_correct_configuration_boots(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(admin_app.ADMIN_PASSWORD_VAR, PASSWORD)
        monkeypatch.setenv("SECRET_KEY", REAL_KEY)

        application = admin_app.create_app()

        assert application.config["SESSION_COOKIE_SECURE"] is True, (
            "the deployed panel is served over HTTPS, so its session cookie "
            "must not also be offered over a plaintext downgrade"
        )

    def test_local_mode_boots_with_neither(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """G-1: none of this applies to the default configuration."""
        monkeypatch.delenv(admin_app.REMOTE_HOST_VAR, raising=False)
        monkeypatch.delenv(admin_app.ADMIN_PASSWORD_VAR, raising=False)
        monkeypatch.delenv("SECRET_KEY", raising=False)

        application = admin_app.create_app()

        assert application.config["SECRET_KEY"] == admin_app.DEV_SECRET_KEY


# --------------------------------------------------------------------------
# AC-5 — every route, not just the one the test happened to pick
# --------------------------------------------------------------------------


class TestAdminAuth_EveryRouteIsBehindTheCredential:
    """A ``before_request`` hook covers everything by construction — assert it.

    Picking ``/`` and calling it done would pass just as well against a
    per-route decorator applied to every route but one. This walks the URL map
    instead, so a route added tomorrow is covered by a test written today.
    """

    @staticmethod
    def _concrete_urls(application) -> list[tuple[str, str]]:
        """Every rule, with placeholders filled, as ``(method, url)``."""
        sample = {
            "int": "1",
            "float": "1.0",
            "path": "x/y",
            "uuid": "3f2504e0-4f89-11d3-9a0c-0305e82c3301",
            "string": "x",
            "default": "x",
        }
        urls = []
        for rule in application.url_map.iter_rules():
            if rule.endpoint == "static":
                continue
            url = rule.rule
            for argument in rule.arguments:
                converter = rule._converters[argument].__class__.__name__.lower()
                key = next(
                    (k for k in sample if k in converter and k != "default"), "default"
                )
                url = url.replace(f"<{argument}>", sample[key])
                for prefix in ("int:", "float:", "path:", "uuid:", "string:"):
                    url = url.replace(f"<{prefix}{argument}>", sample[key])
            method = "POST" if "POST" in rule.methods else "GET"
            urls.append((method, url))
        return urls

    def test_no_route_is_reachable_without_the_credential(
        self, deployed_app, deployed_client
    ) -> None:
        urls = self._concrete_urls(deployed_app)
        assert len(urls) >= 30, f"the URL map looks wrong: {len(urls)} rules"

        served = [
            f"{method} {url}"
            for method, url in urls
            if deployed_client.open(
                url, method=method, headers={"Host": REMOTE}
            ).status_code
            != 401
        ]

        assert served == [], (
            "these answered something other than 401 with no credential:\n"
            + "\n".join(served)
        )

    @pytest.mark.parametrize(
        "method, url",
        [
            pytest.param("POST", "/regrade", id="rewrites-every-stored-grade"),
            pytest.param("GET", "/regrade", id="previews-the-rewrite"),
            pytest.param("GET", "/puzzles", id="lists-the-puzzles"),
            pytest.param("POST", "/batch/create", id="generates-a-batch"),
        ],
    )
    def test_the_routes_that_matter_by_name(
        self, deployed_client, method, url
    ) -> None:
        """The generated sweep above is the real assertion; these are the
        names a reader checks first, spelled out so the card's claim about
        ``POST /regrade`` is legible without running anything."""
        response = deployed_client.open(url, method=method, headers={"Host": REMOTE})
        assert response.status_code == 401


# --------------------------------------------------------------------------
# AC-6 — both halves, every time
# --------------------------------------------------------------------------


class TestAdminAuth_ComparesBothHalvesWithoutShortCircuit:
    """A wrong username must cost the same work as a wrong password."""

    def test_both_halves_are_actually_checked(self, deployed_client) -> None:
        """Neither half alone opens the door."""
        right_user_wrong_password = deployed_client.get(
            "/", headers={"Host": REMOTE, **basic(USER, "nope")}
        )
        wrong_user_right_password = deployed_client.get(
            "/", headers={"Host": REMOTE, **basic("nobody", PASSWORD)}
        )

        assert right_user_wrong_password.status_code == 401
        assert wrong_user_right_password.status_code == 401

    def test_the_comparison_is_constant_time_and_has_no_early_return(self) -> None:
        """Structural, because timing is not observable in a unit test.

        Two claims, both read off the parsed function: every comparison goes
        through ``hmac.compare_digest`` (never ``==``), and there is exactly
        one ``return`` — so no path exits before both halves have been
        compared. The natural spelling this rules out is
        ``if user != expected: return False``, which leaks which half was
        wrong through how quickly the answer comes back.
        """
        source = inspect.getsource(admin_app._credential_is_correct)
        tree = ast.parse(source.lstrip())
        function = tree.body[0]

        compare_digest_calls = [
            node
            for node in ast.walk(function)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "compare_digest"
        ]
        returns = [node for node in ast.walk(function) if isinstance(node, ast.Return)]
        comparisons = [
            node for node in ast.walk(function) if isinstance(node, ast.Compare)
        ]

        assert len(compare_digest_calls) == 2, "one per half of the credential"
        assert len(returns) == 1, (
            "an early return is how a timing difference gets in: both halves "
            "must be compared before anything is returned"
        )
        assert comparisons == [], (
            "a bare == or != on a credential is the thing compare_digest "
            "exists to replace"
        )

    def test_a_non_ascii_password_is_refused_rather_than_fatal(
        self, deployed_client
    ) -> None:
        """``compare_digest`` raises ``TypeError`` on non-ASCII ``str``.

        Comparing UTF-8 bytes is what keeps that from being a 500 that anyone
        can trigger by typing a non-Latin character into the browser's login
        box — an availability bug reachable without any credential at all.
        """
        response = deployed_client.get(
            "/", headers={"Host": REMOTE, **basic("Ольга", "пароль")}
        )
        assert response.status_code == 401


# --------------------------------------------------------------------------
# AC-7 / G-2 — the deployment declares the variables and commits no values
# --------------------------------------------------------------------------


def test_render_declares_the_variables_without_their_values() -> None:
    """``render.yaml`` names what to set; Render's dashboard holds the values.

    Read as text rather than parsed, deliberately: the thing being asserted is
    that the *file* does not contain a secret, and a YAML parse would look
    only at the values it understood.
    """
    render_yaml = (Path(__file__).resolve().parent.parent / "render.yaml").read_text()

    for variable in (
        admin_app.REMOTE_HOST_VAR,
        admin_app.ADMIN_USER_VAR,
        admin_app.ADMIN_PASSWORD_VAR,
        "SECRET_KEY",
        "DATABASE_URL",
    ):
        assert variable in render_yaml, f"{variable} is not declared for the deploy"

    assert render_yaml.count("sync: false") >= 3, (
        "the secret-bearing variables must be declared sync: false so Render "
        "prompts for them instead of reading a value out of this repository"
    )
    assert admin_app.DEV_SECRET_KEY not in render_yaml
