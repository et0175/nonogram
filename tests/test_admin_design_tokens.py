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


def test_the_region_toggles_pressed_look_comes_from_tokens() -> None:
    """CARD-211 G-4 — the Region toggle is the player toolbar's only
    accent-filled control, so its own rule is the one place this card could
    have smuggled a literal in: every value it declares is a var(--token),
    and its size comes from ``.player-toolbar .btn`` (--control-h), never a
    length of its own.

    The sweep above catches a hex colour anywhere in admin.css; this pins the
    rule itself, so a later edit cannot keep the file hex-free by reaching
    for an rgb()/named colour or a hard-coded height here instead.
    """
    css = (_STATIC / "admin.css").read_text()
    rules = [line.strip() for line in css.splitlines() if line.strip().startswith(".player-region")]
    assert rules, "admin.css no longer styles the Region toggle (.player-region)"
    for rule in rules:
        body = rule[rule.index("{") + 1:rule.rindex("}")]
        values = [part.split(":", 1)[1].strip() for part in body.split(";") if ":" in part]
        assert values, rule
        for value in values:
            assert value.startswith("var(--"), f"{rule}: {value!r} is not a design token"


def test_the_panel_serves_both_stylesheets(admin_app) -> None:
    client = admin_app.test_client()
    for name in ("tokens.css", "admin.css"):
        response = client.get(f"/static/{name}")
        assert response.status_code == 200, name
        assert response.get_data(as_text=True) == (_STATIC / name).read_text()
    body = client.get("/").get_data(as_text=True)
    assert 'href="/static/tokens.css"' in body
    assert 'href="/static/admin.css"' in body


def test_the_boards_second_clue_gutters_come_from_tokens() -> None:
    """CARD-212 G-7 — the rules this card adds to the board are the two that
    draw a clue gutter on the far side of an axis: the right-hand row gutter
    (.player-clue.is-row.is-right / .player-corner.is-right, which CARD-193's
    mirror now shares) and the bottom column gutter (the tfoot rules). Every
    length and colour they declare is a var(--token) or a calc() over one —
    the only bare numbers allowed are the multipliers the left/top rules
    already use for the same quantities (a 0.5ch text pad, 0.2 of the cell).

    The file-wide sweep above catches a hex colour anywhere in admin.css;
    this pins these rules, so a later edit cannot keep the file hex-free by
    reaching for an rgb()/named colour or a hard-coded rule width in the one
    place this card could have smuggled one in.

    The one bare length that stays is the 1.45 ch gap the right-hand row
    gutter mirrors onto the other side of its numbers: the SAME typographic
    constant the left-hand rule already carries (.player-clue.is-row
    .player-clue-num), read out of that rule here rather than repeated, so
    the two cannot drift apart without this failing.
    """
    css = (_STATIC / "admin.css").read_text()
    blocks = re.findall(r"(\.player-[^{}]*?(?:is-right|tfoot)[^{}]*?)\{([^}]*)\}", css)
    selectors = [selector.strip() for selector, _body in blocks]
    assert sorted(selectors) == [
        ".player-board .player-clue.is-row.is-right",
        ".player-board .player-clue.is-row.is-right .player-clue-num",
        ".player-board .player-corner.is-right",
        ".player-board tfoot .player-clue.is-col",
        ".player-board tfoot .player-corner",
    ], selectors
    gap = re.search(r"\.player-board \.player-clue\.is-row \.player-clue-num \{[^}]*?\s(\d\.\d+ch)\s", css)
    assert gap, "admin.css no longer sets the row numbers' own gap"
    allowed = {"none", "left", "top", "0", "0.5ch", "calc(var(--player-cell) * 0.2)", gap.group(1)}
    for selector, body in blocks:
        values = [part.split(":", 1)[1].strip() for part in body.split(";") if ":" in part]
        assert values, selector
        for value in values:
            if value in allowed:
                continue
            assert re.fullmatch(r"var\(--[a-z-]+\)(?: solid var\(--[a-z-]+\))?", value), (
                f"{selector.strip()}: {value!r} is not a design token")
