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
import uuid
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
        """Every rule, with placeholders filled, as ``(method, url)``.

        Built with Werkzeug's own ``url_for``-style builder rather than by
        string-replacing ``<converter:name>`` by hand: the builder is the same
        code that routes the request, so a URL it produces is one the map
        matches by construction. The hand-rolled version this replaces read
        ``rule._converters`` — a private attribute — and could silently emit a
        URL matching nothing (CARD-085 review F-004).
        """
        sample = {
            "int": 1,
            "float": 1.0,
            "path": "x/y",
            "uuid": uuid.UUID("3f2504e0-4f89-11d3-9a0c-0305e82c3301"),
            "string": "x",
            "any": "x",
            "default": "x",
        }
        adapter = application.url_map.bind(REMOTE)
        urls = []
        for rule in application.url_map.iter_rules():
            # Try each sample type per argument and keep the first the builder
            # accepts. Which converter a rule uses is the map's business, not
            # this test's — asking the builder is how that stays true when a
            # route changes its converter.
            values: dict[str, object] = {}
            for argument in rule.arguments:
                for candidate in ("uuid", "int", "float", "path", "string"):
                    values[argument] = sample[candidate]
                    try:
                        adapter.build(rule.endpoint, values, method=None)
                    except Exception:
                        continue
                    break
            try:
                url = adapter.build(rule.endpoint, values, method=None)
            except Exception:  # pragma: no cover - a rule that cannot be built
                continue
            method = "POST" if "POST" in rule.methods else "GET"
            urls.append((method, url))
        return urls

    def test_the_sweep_builds_urls_the_router_actually_matches(
        self, deployed_app
    ) -> None:
        """The assertion that makes the next test mean anything.

        ``before_request`` fires for a URL matching *no* rule — Flask stores the
        routing exception and runs the hooks anyway — so the hook returns 401
        for ``/this-matches-nothing`` exactly as it does for a real route.
        A sweep that only asserted 401 would therefore pass just as happily on
        forty malformed URLs, which is what the first version of it did.

        Here every swept URL is matched against the map before it is used, so
        "401" in the next test means "this real, routable endpoint is behind
        the credential".
        """
        from werkzeug.exceptions import NotFound, MethodNotAllowed

        urls = self._concrete_urls(deployed_app)
        assert len(urls) >= 30, f"the URL map looks wrong: {len(urls)} rules"

        adapter = deployed_app.url_map.bind(REMOTE)
        unmatchable = []
        for method, url in urls:
            try:
                adapter.match(url, method=method)
            except MethodNotAllowed:
                pass  # the rule exists; only this verb is not on it
            except NotFound:
                unmatchable.append(f"{method} {url}")

        assert unmatchable == [], (
            "the sweep built URLs that match no route, so asserting 401 on "
            "them would prove nothing:\n" + "\n".join(unmatchable)
        )

    def test_an_unmatched_url_also_returns_401_which_is_why_the_guard_exists(
        self, deployed_client
    ) -> None:
        """Pin the fact the guard above compensates for.

        If Flask ever stopped running ``before_request`` for unroutable URLs,
        this flips to 404 and the guard becomes unnecessary — better to be told
        than to keep a check whose reason has quietly expired.
        """
        response = deployed_client.get(
            "/this-url-matches-no-rule-at-all", headers={"Host": REMOTE}
        )
        assert response.status_code == 401

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
# AC-8 — the credential is not, by itself, evidence the operator asked
# --------------------------------------------------------------------------


class TestAdminAuth_RefusesRequestsAnotherSiteStarted:
    """The defence HTTP Basic auth does not provide (review F-001).

    A browser caches the credential per origin and replays it on a cross-site
    form POST, so once the panel is reachable "carries the password" and "the
    operator asked for this" are different statements. Without this, any page
    the operator's browser loads can aim a form at ``POST /regrade`` and
    rewrite every stored grade — which after CARD-084 keeps no copy.
    """

    @pytest.mark.parametrize(
        "headers, label",
        [
            pytest.param(
                {"Origin": "https://evil.example.com", "Sec-Fetch-Site": "cross-site"},
                "the full attack shape",
                id="hostile-origin-and-cross-site",
            ),
            pytest.param(
                {"Sec-Fetch-Site": "cross-site"}, "fetch metadata alone", id="cross-site"
            ),
            pytest.param(
                {"Origin": "https://evil.example.com"}, "origin alone", id="hostile-origin"
            ),
            pytest.param(
                {"Sec-Fetch-Site": "same-site"},
                "a sibling domain is not this origin",
                id="same-site",
            ),
            pytest.param(
                {"Origin": f"https://{REMOTE}.evil.com"},
                "the configured host as a prefix",
                id="origin-near-miss",
            ),
            pytest.param(
                {"Origin": "null"}, "an opaque origin has no host", id="origin-null"
            ),
        ],
    )
    def test_a_cross_site_write_is_refused_despite_valid_credentials(
        self, deployed_client, headers, label
    ) -> None:
        response = deployed_client.post(
            "/regrade", headers={"Host": REMOTE, **basic(USER, PASSWORD), **headers}
        )
        assert response.status_code == 403, label

    @pytest.mark.parametrize(
        "headers, label",
        [
            pytest.param(
                {"Origin": f"https://{REMOTE}", "Sec-Fetch-Site": "same-origin"},
                "the panel's own form posting back",
                id="same-origin",
            ),
            pytest.param(
                {"Sec-Fetch-Site": "none"}, "a typed URL or a bookmark", id="none"
            ),
            pytest.param({}, "curl, or Render's health probe", id="no-fetch-metadata"),
            pytest.param(
                {"Origin": f"https://{REMOTE}:443"},
                "the port is not part of the question",
                id="same-origin-with-port",
            ),
        ],
    )
    def test_the_operators_own_requests_still_work(
        self, deployed_client, headers, label
    ) -> None:
        response = deployed_client.post(
            "/regrade", headers={"Host": REMOTE, **basic(USER, PASSWORD), **headers}
        )
        assert response.status_code != 403, label

    @pytest.mark.parametrize(
        "pair",
        [
            pytest.param(
                [("Sec-Fetch-Site", "same-origin"), ("Sec-Fetch-Site", "cross-site")],
                id="allowed-then-foreign",
            ),
            pytest.param(
                [("Sec-Fetch-Site", "cross-site"), ("Sec-Fetch-Site", "same-origin")],
                id="foreign-then-allowed",
            ),
            pytest.param(
                [("Origin", f"https://{REMOTE}"), ("Origin", "https://evil.example.com")],
                id="own-origin-then-foreign",
            ),
            pytest.param(
                [("Origin", "https://evil.example.com"), ("Origin", f"https://{REMOTE}")],
                id="foreign-then-own-origin",
            ),
        ],
    )
    def test_a_smuggled_second_value_does_not_get_past(
        self, deployed_client, pair
    ) -> None:
        """A request carrying two values that disagree has no single answer.

        Both orders, because the two are not symmetric under every possible
        reading: putting the allowed value first is what defeats a check that
        stops at the first, and putting it last defeats one that stops at the
        last.

        Under WSGI these arrive folded into one comma-joined value, which is
        why the implementation splits on commas rather than trusting
        ``get_all`` to yield two elements — a mutation restricting that loop to
        its first element changed nothing, because there was never a second.
        """
        headers = [("Host", REMOTE), *basic(USER, PASSWORD).items(), *pair]
        response = deployed_client.post("/regrade", headers=headers)
        assert response.status_code == 403

    def test_the_gateway_folds_repeats_which_is_why_splitting_is_the_check(
        self, deployed_app
    ) -> None:
        """Pin the platform fact the implementation depends on.

        If a future gateway stops folding repeated headers into one value, this
        flips and the comma-splitting becomes belt-and-braces rather than the
        load-bearing part — better to be told by a failing test than to keep a
        comment explaining a fact that has changed.
        """
        from werkzeug.test import EnvironBuilder
        from werkzeug.wrappers import Request

        environ = EnvironBuilder(
            path="/",
            headers=[("Sec-Fetch-Site", "same-origin"), ("Sec-Fetch-Site", "cross-site")],
        ).get_environ()

        values = Request(environ).headers.get_all("Sec-Fetch-Site")

        assert values == ["same-origin, cross-site"], (
            "WSGI is expected to fold repeated headers into one comma-joined "
            f"value; got {values!r}"
        )

    @pytest.mark.parametrize(
        "method, url, extra, label",
        [
            pytest.param("GET", "/", {}, "a link from a chat message", id="link-to-root"),
            pytest.param(
                "GET", "/puzzles", {}, "a link to a deep page", id="link-to-page"
            ),
            pytest.param(
                "GET",
                "/",
                {"Origin": "https://evil.example.com"},
                "a navigation carrying an Origin",
                id="navigation-with-origin",
            ),
        ],
    )
    def test_a_cross_site_top_level_get_navigation_is_still_served(
        self, deployed_client, method, url, extra, label
    ) -> None:
        """The operator's most natural way in must keep working.

        A link to the panel in Slack, an email, or another tab arrives with
        ``Sec-Fetch-Site: cross-site``, and refusing it would break that flow
        for nothing: every route here that changes anything is a POST
        (``GET /regrade`` previews through a savepoint and rolls it back), so a
        cross-site GET has nothing to trigger. This is the fetch-metadata
        Resource Isolation Policy's standard carve-out.

        The third case is deliberate rather than incidental. A browser does not
        send ``Origin`` on a GET navigation at all, so this shape comes from a
        non-browser client — which does not have the operator's cached
        credentials, and is therefore not the attack this defends against. The
        standard policy does not consult ``Origin`` for navigations either.
        """
        response = deployed_client.open(
            url,
            method=method,
            headers={
                "Host": REMOTE,
                **basic(USER, PASSWORD),
                "Sec-Fetch-Site": "cross-site",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Dest": "document",
                **extra,
            },
        )
        assert response.status_code != 403, label

    @pytest.mark.parametrize(
        "method, url, extra, label",
        [
            pytest.param(
                "POST", "/regrade", {}, "a cross-site form post", id="form-post"
            ),
            pytest.param(
                "POST",
                "/puzzle/3f2504e0-4f89-11d3-9a0c-0305e82c3301/delete",
                {},
                "a cross-site form delete",
                id="form-delete",
            ),
            pytest.param(
                "GET", "/", {"Sec-Fetch-Dest": "iframe"}, "framed", id="iframe"
            ),
            pytest.param(
                "GET", "/", {"Sec-Fetch-Dest": "image"}, "loaded as an img", id="image"
            ),
            pytest.param(
                "GET", "/", {"Sec-Fetch-Mode": "cors"}, "a cross-site fetch", id="cors"
            ),
        ],
    )
    def test_the_carve_out_does_not_let_the_attack_back_in(
        self, deployed_client, method, url, extra, label
    ) -> None:
        """Each of the carve-out's three conditions, defeated one at a time.

        The method test is the one that matters most: a cross-site *form
        submission* is also a navigation to a document, so without it the
        exemption would re-open precisely what this class exists to close.
        """
        response = deployed_client.open(
            url,
            method=method,
            headers={
                "Host": REMOTE,
                **basic(USER, PASSWORD),
                "Sec-Fetch-Site": "cross-site",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Dest": "document",
                **extra,
            },
        )
        assert response.status_code == 403, label

    def test_an_anonymous_cross_site_caller_still_learns_only_401(
        self, deployed_client
    ) -> None:
        """The check runs after the credential, on purpose.

        An unauthenticated scanner sees exactly what it saw before this fix —
        401 — so the refusal vocabulary does not widen for people who have not
        authenticated.
        """
        response = deployed_client.post(
            "/regrade",
            headers={"Host": REMOTE, "Origin": "https://evil.example.com"},
        )
        assert response.status_code == 401

    def test_local_mode_does_not_gain_the_check(self, local_client) -> None:
        """G-1: loopback-only behaviour is still byte-for-byte CARD-081's.

        The panel is unreachable from any browser but this machine's, and the
        machine's own browser posting to it is same-origin anyway.
        """
        response = local_client.post(
            "/regrade",
            headers={"Host": "localhost", "Sec-Fetch-Site": "cross-site"},
        )
        assert response.status_code != 403

    def test_the_fetch_site_allowlist_agrees_with_the_web_adapters(self) -> None:
        """Two short allowlists that agree is the intended shape (ADR-0007).

        ``admin`` may not import ``web`` laterally, so the frozenset is
        reimplemented — and this is the seam that keeps the copy honest,
        exactly as ``test_the_allowlist_and_the_web_adapters_agree`` does for
        ``ALLOWED_HOSTS`` in ``tests/test_admin_binding.py``.
        """
        from nonogram.web.handler import ALLOWED_FETCH_SITES as web_sites

        assert admin_app.ALLOWED_FETCH_SITES == web_sites


# --------------------------------------------------------------------------
# AC-4 (extended) — a password that is present but useless is not a password
# --------------------------------------------------------------------------


class TestAdminAuth_RefusesToBootWithAGuessablePassword:
    """Presence was the right check for a panel nobody could reach (F-003).

    Once ``ADMIN_ALLOWED_HOST`` is set the password is the entire defence,
    nothing in this package rate-limits guesses, and ``ADMIN_USER`` defaults to
    ``admin`` — so the other half of the credential is usually known.
    """

    @pytest.fixture(autouse=True)
    def _remote_configured(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv(admin_app.REMOTE_HOST_VAR, REMOTE)
        monkeypatch.setenv("SECRET_KEY", REAL_KEY)
        monkeypatch.delenv("DATABASE_URL", raising=False)

    @pytest.mark.parametrize("password", ["a", "admin", "hunter2", "x" * 15])
    def test_a_short_password_is_fatal(
        self, monkeypatch: pytest.MonkeyPatch, password
    ) -> None:
        monkeypatch.setenv(admin_app.ADMIN_PASSWORD_VAR, password)

        with pytest.raises(admin_app.AdminConfigurationError) as caught:
            admin_app.create_app()

        assert str(admin_app.MIN_ADMIN_PASSWORD_LENGTH) in str(caught.value)

    def test_the_boundary_itself_boots(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Exactly ``MIN_ADMIN_PASSWORD_LENGTH`` is enough — the limit, not limit+1."""
        monkeypatch.setenv(
            admin_app.ADMIN_PASSWORD_VAR, "x" * admin_app.MIN_ADMIN_PASSWORD_LENGTH
        )

        assert admin_app.create_app() is not None

    def test_local_mode_imposes_no_floor(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """G-1 again: none of this exists for a loopback-only panel."""
        monkeypatch.delenv(admin_app.REMOTE_HOST_VAR, raising=False)
        monkeypatch.setenv(admin_app.ADMIN_PASSWORD_VAR, "a")

        assert admin_app.create_app() is not None


# --------------------------------------------------------------------------
# F-006 — the wildcard CORS grant does not follow the panel onto the internet
# --------------------------------------------------------------------------


def test_deployed_mode_does_not_advertise_a_wildcard_cors_grant(
    deployed_client,
) -> None:
    """Written when "any origin" meant "this browser"; it no longer does."""
    response = deployed_client.get("/", headers={"Host": REMOTE, **basic(USER, PASSWORD)})

    assert "Access-Control-Allow-Origin" not in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff", (
        "the security headers in the same hook are not what this removes"
    )


def test_local_mode_keeps_the_headers_it_always_had(local_client) -> None:
    """G-1: the wildcard was added for Chrome on loopback and stays there."""
    response = local_client.get("/", headers={"Host": "localhost"})

    assert response.headers["Access-Control-Allow-Origin"] == "*"


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
