"""The re-grade page exists on this machine only.

CARD-077's re-grade rewrites every stored grade with no undo; its own page
tells the operator to take a snapshot first. That is an operator step run
from the machine that holds the backup, not a button on the panel the
internet reaches. So when the deployed door is open (``ADMIN_ALLOWED_HOST``
set, CARD-085) the two ``/regrade`` routes answer 404 and neither the
sidebar nor the dashboard mentions them. In loopback mode nothing changes:
CARD-077's own tests keep running against the page as it was.
"""

from __future__ import annotations

import base64

import pytest

from nonogram.admin import app as admin_app

REMOTE = "nonogram-admin.onrender.com"
USER = "olga"
PASSWORD = "correct-horse-battery-staple"
REAL_KEY = "a-long-random-production-secret"


def _basic(user: str, password: str) -> dict:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


DEPLOYED_HEADERS = {"Host": REMOTE, **_basic(USER, PASSWORD)}


@pytest.fixture
def deployed_client(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(admin_app.REMOTE_HOST_VAR, REMOTE)
    monkeypatch.setenv(admin_app.ADMIN_USER_VAR, USER)
    monkeypatch.setenv(admin_app.ADMIN_PASSWORD_VAR, PASSWORD)
    monkeypatch.setenv("SECRET_KEY", REAL_KEY)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    application = admin_app.create_app()
    application.config["TESTING"] = True
    with application.test_client() as client:
        yield client


@pytest.fixture
def local_client(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv(admin_app.REMOTE_HOST_VAR, raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TESTING", "true")
    application = admin_app.create_app()
    application.config["TESTING"] = True
    with application.test_client() as client:
        yield client


class TestDeployed:
    def test_the_preview_is_not_there(self, deployed_client) -> None:
        assert deployed_client.get("/regrade", headers=DEPLOYED_HEADERS).status_code == 404

    def test_the_write_is_not_there_either(self, deployed_client) -> None:
        """The button's target, not just the page with the button.

        A 404 on GET alone would hide the door and leave it unlocked; the
        POST is the route that rewrites grades, so it is the one that matters.
        """
        response = deployed_client.post(
            "/regrade", headers={**DEPLOYED_HEADERS, "Sec-Fetch-Site": "same-origin"}
        )
        assert response.status_code == 404

    def test_the_navigation_does_not_mention_it(self, deployed_client) -> None:
        body = deployed_client.get("/", headers=DEPLOYED_HEADERS).get_data(as_text=True)
        assert body.count('href="/regrade"') == 0, "sidebar and dashboard both link it locally"
        assert "Re-grade" not in body


class TestLocalIsUnchanged:
    def test_the_navigation_offers_it(self, local_client) -> None:
        body = local_client.get("/", headers={"Host": "127.0.0.1"}).get_data(as_text=True)
        assert body.count('href="/regrade"') == 2, "the sidebar link and the dashboard button"

    def test_the_page_answers(self, local_client) -> None:
        # No database in this fixture, so the route explains and redirects —
        # but it is reachable, which is the point.
        response = local_client.get("/regrade", headers={"Host": "127.0.0.1"})
        assert response.status_code == 302
