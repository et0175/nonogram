"""The admin panel is styled from meta/design/ and nowhere else (forge:ui).

meta/design/tokens.css is the single source of visual truth; the panel serves
a byte-identical mirror from its static folder. Templates carry no colour
literals (the one exception is the tier hue in _tier.html, pinned by
test_admin_tier_surfaces.py) and no emoji standing in for icons. A drifting
mirror or a template that smuggles a hex value back in fails here, so the
design system cannot quietly stop being the one that ships.

**The sweep reads the served JavaScript too, since CARD-250.** It did not,
and that is the hole item 4 of that card could have fallen through: the tier
hues are consolidated into ``_tier.html`` precisely because five copies of
one colour expression had drifted (CARD-076), and a tier-to-hue map written
in ``static/*.js`` would have been a sixth copy in a language that macro
cannot reach — invisible to a sweep that read only ``.css`` and ``.html``.
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


def _scripts() -> list[Path]:
    return sorted(_STATIC.glob("*.js"))


def _code_lines(path: Path):
    """``(line number, line)`` for the lines that are CODE.

    A whole-line ``//`` comment is prose, and these files explain at length
    why the colours are not in them — a sweep that read those sentences would
    fire on the file that documents the rule. A comment TRAILING code is not
    skipped, so a value cannot be hidden behind one. (Same discipline as
    ``tests/test_puzzle_editor_ui.py``'s reads of this file set.)
    """
    for number, line in enumerate(path.read_text().splitlines(), 1):
        if line.strip().startswith(("//", "*", "/*")):
            continue
        yield number, line


#: How a colour can be written INTO a script: a hex literal, a colour
#: function, or a reach for one of the design system's own colour tokens
#: (``--color-*``, ``--tier``, ``--grid-*``) or for an element's colour
#: properties. ``style.setProperty("--player-…")`` is deliberately outside
#: it: the player sets geometry custom properties that way and those are not
#: colours.
_COLOUR_IN_A_SCRIPT = re.compile(
    r"#[0-9a-fA-F]{6}\b|\brgba?\(|\bhsla?\(|\bcolor-mix\("
    r"|--color-|--tier\b|--grid-|style\.(?:color|background)"
)


#: A design token, as a value is allowed to reach for one.
_TOKEN = re.compile(r"var\(--[a-z0-9-]+\)")

#: What may stand AROUND the tokens in a value: the two functions these rules
#: use, their syntax, and the numbers/operators/percentages they take. A value
#: is token-only when striking every ``var(--…)`` out of it leaves nothing but
#: this — so ``rgb()``/``hsl()``, a hex literal and a bare named colour all
#: leave letters behind and are reported.
_VALUE_STRUCTURE = re.compile(r"(?:calc|color-mix|in|srgb)\b|[-+*/0-9.,%() ]")

#: Values that are neither a length nor a colour: the layout keywords these
#: rules declare. An explicit set and NOT "any bare keyword" — ``red`` is a
#: bare keyword too, and catching it is the point.
_KEYWORD_VALUES = {"inline-flex"}


def _declared_values(rule: str) -> list[str]:
    """The values of one single-line CSS rule's declarations, in order."""
    body = rule[rule.index("{") + 1:rule.rindex("}")]
    return [part.split(":", 1)[1].strip() for part in body.split(";") if ":" in part]


def _untokenised(values: list[str]) -> list[str]:
    """Those of ``values`` that are not tokens, or token-only expressions.

    A value passes when it is one of :data:`_KEYWORD_VALUES`, or it reaches
    for at least one ``var(--…)`` and striking every token out of it leaves
    only :data:`_VALUE_STRUCTURE`. ``calc()`` and ``color-mix()`` therefore
    pass only while every colour and length argument inside them is a token:
    a literal anywhere in one survives the strike.
    """
    return [
        value
        for value in values
        if value not in _KEYWORD_VALUES
        and (
            not _TOKEN.search(value)
            or _VALUE_STRUCTURE.sub("", _TOKEN.sub("", value)) != ""
        )
    ]


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


def test_no_served_script_decides_a_colour() -> None:
    """CARD-250 AC-9. The panel's colours are chosen in CSS, from the tokens;
    a script says WHICH state a thing is in (a data attribute, a class) and
    never what colour that state is.

    The case this was written for is the editor's recomputed tier: the tier
    word wears its tier's hue, and the hue is in ``admin.css`` keyed off the
    server's own tier string, because a ``{easy: "#27ae60", …}`` object in
    ``static/puzzle_edit.js`` would have been the sixth copy of an expression
    that has already drifted into two defects once (CARD-076) — in the one
    language ``_tier.html`` cannot be imported into, and the one file this
    sweep could not see.

    **What this does NOT cover,** since a guard that overstates itself is
    worse than none: a script may still pick a CLASS or a data attribute per
    tier, which is the shape CARD-250 uses and which this cannot distinguish
    from any other attribute write. What it rules out is a script deciding a
    colour VALUE — the thing that can disagree with the tokens. That the
    values agree is read off two live surfaces by
    ``tests/test_puzzle_editor_ui.py``'s
    ``TestPuzzleEditor_TheGradeWearsItsTierColour``.
    """
    offences = [
        f"{path.name}: {line_number}: {line.strip()[:60]}"
        for path in _scripts()
        for line_number, line in _code_lines(path)
        if _COLOUR_IN_A_SCRIPT.search(line)
    ]

    assert _scripts(), "the panel serves no scripts — this sweep reads nothing"
    assert offences == [], (
        "colours are decided in admin.css from tokens.css, never in a served "
        f"script: {offences}"
    )


def test_the_tier_hue_macro_is_still_the_only_exception() -> None:
    """The exception is ONE file and is named in one place. The template sweep
    above skips ``_tier.html`` by name; this asserts the skip is still earning
    its keep (that file really does carry the hues) so the exemption cannot
    outlive the thing it exempts, and that the hues it carries are the ones
    ``tokens.css`` declares as ``--color-tier-*``."""
    macro = (_TEMPLATES / "_tier.html").read_text()
    tokens = (_DESIGN / "tokens.css").read_text() if _DESIGN.exists() else (
        _STATIC / "tokens.css").read_text()

    hues = set(_HEX.findall(macro))
    declared = set(_HEX.findall(
        "\n".join(line for line in tokens.splitlines() if "--color-tier-" in line)))

    assert hues, "_tier.html no longer carries the tier hues — retire its exemption"
    assert hues <= declared, sorted(hues - declared)


def test_the_stylesheet_uses_tokens_not_literals() -> None:
    css = (_STATIC / "admin.css").read_text()
    literals = sorted(set(_HEX.findall(css)))
    assert literals == [], f"admin.css must reference tokens, not hex values: {literals}"


def test_the_region_toggles_pressed_look_comes_from_tokens() -> None:
    """CARD-211 G-4 — the Region toggle is the player toolbar's only
    accent-filled control, so its own rules are the one place a card could
    smuggle a literal in: every value they declare is a design token, or a
    ``calc()``/``color-mix()`` over design tokens, and the toggle's size
    comes from ``.player-toolbar .btn`` (--control-h), never a length of its
    own.

    The sweep above catches a hex colour anywhere in admin.css; this pins
    these rules, so a later edit cannot keep the file hex-free by reaching
    for an rgb()/hsl()/named colour or a hard-coded length here instead.

    **The toggle's FACE is pinned here too, since CARD-247.** That card
    replaced the word "Region" with three cells and styled them in rules of
    its own (``.player-brush-run``), whose values are ``inline-flex``, a
    ``calc()`` and a ``color-mix()`` — none of which a literal ``var(--``
    prefix test could ever have accepted. Collecting them by name while
    leaving that predicate alone would have left the declarations that colour
    the toggle pinned by nothing but the whole-file hex sweep, so the
    predicate is the one that moved: token-only, where a keyword has to be
    named in :data:`_KEYWORD_VALUES` to pass. A bare keyword is NOT accepted
    as a class, because ``color: red`` is one.

    The predicate is a branch nothing executes while every real rule is clean
    (ADR-0039/R1), so the control at the end drives the same two derivations
    over rules broken on purpose — one per way a literal can get in.
    """
    css = (_STATIC / "admin.css").read_text()
    rules = [
        line.strip()
        for line in css.splitlines()
        if line.strip().startswith((".player-region", ".player-brush-run"))
        and "{" in line and line.strip().endswith("}")
    ]
    # Pinned by name, like the clue gutters' rules below: a rule that stops
    # being collected (renamed, reformatted across lines, or deleted) is a
    # red test and not a silently smaller sweep.
    assert [rule.split("{")[0].strip() for rule in rules] == [
        ".player-region",
        '.player-region[aria-pressed="true"]',
        ".player-brush-run",
        ".player-brush-run .player-swatch + .player-swatch",
    ], rules
    for rule in rules:
        values = _declared_values(rule)
        assert values, rule
        offenders = _untokenised(values)
        assert offenders == [], (
            f"{rule.split('{')[0].strip()}: {offenders} are not design tokens "
            f"(or token-only calc()/color-mix()); a colour or a length here "
            f"belongs in tokens.css"
        )

    # The control. Each of these is a literal reaching into one of the four
    # rules above, in a form the whole-file hex sweep would NOT catch; the
    # predicate has to report every one of them, or it is pinning nothing.
    broken = {
        "a colour function": ".player-brush-run .player-swatch + .player-swatch "
                             "{ border-left-color: rgb(0, 0, 0); }",
        "a named colour": ".player-brush-run { border-left-color: red; }",
        "a hex literal": '.player-region[aria-pressed="true"] '
                         "{ background: #1a1a1a; }",
        "a bare length": ".player-region { padding-left: 8px; }",
        "a literal inside the mix": ".player-brush-run .player-swatch + "
                                    ".player-swatch { border-left-color: "
                                    "color-mix(in srgb, hsl(0 0% 10%) 28%, "
                                    "var(--grid-paper)); }",
        "a bare length inside the calc": ".player-brush-run .player-swatch + "
                                         ".player-swatch { margin-left: "
                                         "calc(1px + var(--border-width)); }",
    }
    for label, rule in broken.items():
        assert _untokenised(_declared_values(rule)) != [], (
            f"{label}: {rule} passed the token predicate, so the rule it is "
            f"supposed to enforce is narrative"
        )


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
    # Comments first: [^{}] crosses newlines, so a /* ... */ mentioning a
    # .player-… selector (the block above these rules discusses .is-right at
    # length) would otherwise be captured as part of the next selector.
    rules_only = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    blocks = re.findall(r"(\.player-[^{}]*?(?:is-right|tfoot)[^{}]*?)\{([^}]*)\}", rules_only)
    selectors = [selector.strip() for selector, _body in blocks]
    assert sorted(selectors) == [
        ".player-board .player-clue.is-row.is-right",
        ".player-board .player-clue.is-row.is-right .player-clue-num",
        ".player-board .player-corner.is-right",
        ".player-board tfoot .player-clue.is-col",
        ".player-board tfoot .player-corner",
    ], selectors
    gap = re.search(r"\.player-board \.player-clue\.is-row \.player-clue-num \{[^}]*?\s(\d\.\d+ch)\s",
                    rules_only)
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
