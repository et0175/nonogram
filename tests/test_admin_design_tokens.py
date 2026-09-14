"""The admin panel is styled from meta/design/ and nowhere else (forge:ui).

meta/design/tokens.css is the single source of visual truth; the panel serves
a byte-identical mirror from its static folder. Templates carry no colour
literals (the one exception is the tier hue in _tier.html, pinned by
test_admin_tier_surfaces.py) and no emoji standing in for icons. A drifting
mirror or a template that smuggles a hex value back in fails here, so the
design system cannot quietly stop being the one that ships.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
_ADMIN = _REPO / "src" / "nonogram" / "admin"
_TEMPLATES = _ADMIN / "templates"
_STATIC = _ADMIN / "static"
_DESIGN = _REPO / "meta" / "design"

_HEX = re.compile(r"#[0-9a-fA-F]{6}\b")


@pytest.fixture
def admin_app(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TESTING", "true")
    from nonogram.admin.app import create_app

    app = create_app()
    app.config["TESTING"] = True
    with app.app_context():
        yield app
# Pictographs, dingbat-emoji and the variation selector that turns a glyph
# into one. ✓ (U+2713) and ✕ (U+2715) are typographic marks and stay allowed.
_EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-⛿✅❌⬆-⬇️]")


def _templates() -> list[Path]:
    return sorted(_TEMPLATES.glob("*.html"))


@pytest.mark.skipif(not _DESIGN.exists(), reason="meta/design/ is not shipped with the package")
def test_the_served_tokens_are_the_design_systems_tokens() -> None:
    assert (_STATIC / "tokens.css").read_text() == (_DESIGN / "tokens.css").read_text(), (
        "src/nonogram/admin/static/tokens.css has drifted from "
        "meta/design/tokens.css — regenerate it (cp), never edit it by hand"
    )


def test_every_template_wears_the_design_system() -> None:
    offences = [
        f"{path.name}: {line_number}"
        for path in _templates()
        if path.name != "_tier.html"
        for line_number, line in enumerate(path.read_text().splitlines(), 1)
        if _HEX.search(line) and "data:image/svg+xml" not in line
    ]
    assert offences == [], f"colour literals belong in tokens.css, not templates: {offences}"


def test_no_template_uses_emoji_as_icons() -> None:
    offences = [
        f"{path.name}: {line_number}"
        for path in _templates()
        for line_number, line in enumerate(path.read_text().splitlines(), 1)
        if _EMOJI.search(line)
    ]
    assert offences == [], f"icons come from _icons.html, not the emoji table: {offences}"


def test_no_template_carries_its_own_stylesheet() -> None:
    offences = [path.name for path in _templates() if "<style" in path.read_text()]
    assert offences == [], f"page-local <style> blocks bypass admin.css: {offences}"


def test_the_stylesheet_uses_tokens_not_literals() -> None:
    css = (_STATIC / "admin.css").read_text()
    literals = sorted(set(_HEX.findall(css)))
    assert literals == [], f"admin.css must reference tokens, not hex values: {literals}"


def test_the_panel_serves_both_stylesheets(admin_app) -> None:
    client = admin_app.test_client()
    for name in ("tokens.css", "admin.css"):
        response = client.get(f"/static/{name}")
        assert response.status_code == 200, name
        assert response.get_data(as_text=True) == (_STATIC / name).read_text()
    body = client.get("/").get_data(as_text=True)
    assert 'href="/static/tokens.css"' in body
    assert 'href="/static/admin.css"' in body
