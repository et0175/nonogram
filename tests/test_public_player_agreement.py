"""The public player's duplicated looks are held to the admin player's.

CARD-328. Two looks — the white mark (a centred dot) and the solved reveal
(a banner that settles in and a diagonal flash across the filled cells) —
exist **twice** in this tree: once in ``src/nonogram/admin/static/admin.css``
+ ``solver.js`` for the panel's player, and once in ``player/player.css`` +
``play.js`` for the public one. ``2400501b`` made the second match the first
on 2026-10-30 and justified the duplication correctly: ADR-0041/R3 copies
``solver_state.js`` and ``tokens.css`` byte-identically **and nothing else**,
so the admin's rule is *the look this matches, not a file this one reads*.

That reasoning is right, and it is also the whole problem. R3 mandates
byte-identical copying **because copies drift**, and these two behaviours sit
outside that protection, parallel-maintained, with nothing checking they stay
in agreement. This module is that check.

Why it reads ``src/`` from the test tree
----------------------------------------
The public page can never import from ``src/`` — it is a static site, and
``player/assemble.py``'s ``COPIED_FROM_ADMIN`` is the only channel between the
two trees. The **test tree** can read both files, and that is the precedent
CLAUDE.md names for exactly this situation: ``solver/propagate.py``'s
``mask_runs`` deliberately reimplements a clue-encoding check rather than
importing ``clues.py``, and is cross-checked against ``clues.encode_line``
*from the test tree*, where the import is legal. Nothing here writes to
``src/``.

What agrees, and what is allowed to differ
------------------------------------------
A guard asserting "the two sheets are the same" would be **FALSE** — the
public page has no panel chrome, and three things in the compared surface
differ for stated reasons. So the surface is split in two, and **both halves
are mechanical**:

* every compared fact is **derived** from the four files
  (:func:`compared_surface`), never written down here;
* the facts that disagree are computed (:func:`disagreements`) and asserted
  **equal** to :data:`DECLARED_DIVERGENCES`, which carries a reason per entry.

So a fourth divergence appears as an undeclared key and **reds**, and a
declared divergence that stops diverging reds too — a stale exemption is as
much a defect as an undeclared one.

**Why the declaration has a shape constraint and a control**, stated here
because this is where a reader meets it: an exemption with no shape
constraint and no control is the defect CARD-255 shipped — two executable
setters sat under its exempted path prefixes and its test stayed green.
:class:`TestPlayerLooksAgree_ADivergenceMustBeDeclared` therefore requires
every declared key to be a key the extractor actually produces, requires
every declared key to actually diverge, and feeds the comparison synthetic
sheet text in **both** directions (a planted fourth divergence must be
reported; a declared divergence removed must be reported) so the set equality
is not the only thing holding the claim up.

What this module does **not** do
--------------------------------
It changes no rendered pixel, and it is not allowed to. If it ever finds a
real disagreement, that is a **finding for the owner**: the admin and the
public page disagreeing about a mark is the defect ``2400501b`` existed to
fix, and deciding which side is right is not a worktree call.

It also does not widen ``COPIED_FROM_ADMIN`` or soften ADR-0041/R3. Making
``admin.css`` a byte-identical copy is a different and much larger decision
(the two sheets are not interchangeable) and belongs to the architect station.

How this file is verified
-------------------------
TDD is off on this card deliberately: the behaviour already shipped, so a
guard over it is green on its first run by construction and "watch it fail"
is meaningless. **Mutation carries the weight** — CARD-328's AC-5/AC-6 mutant
table in ``meta/kanban/cards/CARD-328.md`` records eight mutants, two per
sheet for the dot and two at the sweep's edge, each with the arm it reds.
Both sides of every pair are mutated on purpose: *a guard that read only one
sheet would pass half of them*, which is the exact defect shape this file
exists to catch.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
ADMIN_CSS = _REPO / "src" / "nonogram" / "admin" / "static" / "admin.css"
ADMIN_JS = _REPO / "src" / "nonogram" / "admin" / "static" / "solver.js"
PUBLIC_CSS = _REPO / "player" / "player.css"
PUBLIC_JS = _REPO / "player" / "play.js"


# --------------------------------------------------------------------------
# Parsing. No CSS parser is in the dependency baseline (stdlib + Pillow +
# NumPy), so these are regexes and brace walks over the file text — the idiom
# tests/test_admin_design_tokens.py already uses to read these stylesheets,
# followed rather than replaced by a second one.
# --------------------------------------------------------------------------

#: A ``/* … */`` comment, in CSS. Stripped before any rule is looked up:
#: ``player.css``'s own prose quotes the admin selector it matches, and a
#: lookup that read the sentence explaining the rule would find the sentence.
#: Stripping can only *remove* braces, so it never unbalances the walk.
_CSS_COMMENT = re.compile(r"/\*.*?\*/", re.S)

#: One flat ``selector { declarations }``. ``[^{}]`` on both sides is what
#: keeps it flat: an ``@media`` block's own braces never match, so the scan
#: yields the rules *inside* it keyed by their own selector text.
_RULE = re.compile(r"([^{}]+)\{([^{}]*)\}")


def _squeezed(text: str) -> str:
    """``text`` with every run of whitespace collapsed to one space."""
    return " ".join(text.split())


def _css_code(text: str) -> str:
    """``text`` with its comments removed."""
    return _CSS_COMMENT.sub("", text)


def _js_code_lines(path: Path):
    """``(line number, line)`` for the lines of ``path`` that are CODE.

    A whole-line ``//`` comment is prose, and both scripts explain at length
    what they set and why; a sweep that read those sentences would find the
    comment that documents the rule rather than the rule. A comment TRAILING
    code is not skipped, so nothing can hide behind one. Same discipline as
    ``tests/test_admin_design_tokens.py``'s ``_code_lines``.
    """
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip().startswith(("//", "*", "/*")):
            continue
        yield number, line


def _blocks_at_depth_one(text: str, opener: str) -> list[str]:
    """The inner text of every top-level ``<opener>…{ … }`` block in ``text``.

    A brace walk rather than a regex, because the bodies nest (``@media`` holds
    rules; ``@keyframes`` holds stops). Written here and not imported, which is
    this repo's standing preference for a second implementation.
    """
    found: list[str] = []
    for start in (m.start() for m in re.finditer(re.escape(opener), text)):
        brace = text.find("{", start)
        if brace < 0:
            continue
        depth = 0
        for index in range(brace, len(text)):
            if text[index] == "{":
                depth += 1
            elif text[index] == "}":
                depth -= 1
                if depth == 0:
                    found.append(text[brace + 1:index])
                    break
    return found


def rules(text: str) -> dict[str, str]:
    """``{normalised selector: declaration block}`` for ``text``'s flat rules.

    A selector that appears twice is kept as its *last* body; the callers that
    care assert uniqueness themselves (:func:`rule_count`), because "exactly
    one rule declares this" is a claim worth failing on rather than silently
    resolving.
    """
    return {
        _squeezed(selector): body
        for selector, body in _RULE.findall(_css_code(text))
    }


def rule_count(text: str, selector: str) -> int:
    """How many flat rules in ``text`` carry exactly ``selector``."""
    return sum(
        1
        for found, _ in _RULE.findall(_css_code(text))
        if _squeezed(found) == selector
    )


def declarations(body: str) -> dict[str, str]:
    """``{property: value}`` for one declaration block.

    Order- and formatting-insensitive **by construction** — which is the point
    of AC-1: one sheet writes the dot on a single line and the other over
    nine, so a comparison of rule *text* would be a comparison of code style.
    """
    out: dict[str, str] = {}
    for part in body.split(";"):
        if ":" not in part:
            continue
        name, value = part.split(":", 1)
        out[name.strip()] = _squeezed(value)
    return out


def keyframes_body(text: str, name: str) -> str:
    """The normalised body of ``@keyframes <name>`` in ``text``."""
    blocks = _blocks_at_depth_one(_css_code(text), f"@keyframes {name}")
    assert len(blocks) == 1, f"@keyframes {name}: expected one block, found {len(blocks)}"
    return _squeezed(blocks[0])


def reduced_motion_blocks(text: str) -> list[str]:
    """The normalised inner text of each ``prefers-reduced-motion`` block."""
    return [
        _squeezed(block)
        for block in _blocks_at_depth_one(_css_code(text), "@media (prefers-reduced-motion")
    ]


def _top_level_tokens(value: str) -> list[str]:
    """``value`` split on whitespace that is **not** inside parentheses.

    So ``player-solved-flash calc(2 * var(--duration-base)) var(--ease)
    calc(var(--player-wave) * 12ms)`` is four tokens, not nine. An independent
    tokeniser, not a match against the formula we expect to find: the expected
    formula is the thing under comparison, so baking it into the parser would
    make the parser agree with whichever sheet it was written from.
    """
    tokens: list[str] = []
    current: list[str] = []
    depth = 0
    for char in _squeezed(value):
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        if char == " " and depth == 0:
            if current:
                tokens.append("".join(current))
                current = []
            continue
        current.append(char)
    if current:
        tokens.append("".join(current))
    return tokens


#: The keyframes the diagonal flash plays. The sweep rule is found by *this*
#: — by what it does — and never by its selector, because the selector is a
#: DECLARED divergence: a guard that looked the rule up by the admin's
#: selector would simply not find the public one, and "not found" must be a
#: failure here rather than a silent half-measurement.
FLASH = "player-solved-flash"

#: The banner's keyframes.
SETTLE = "player-solved-in"


def sweep_rule(text: str) -> tuple[str, str]:
    """``(selector, animation value)`` of the one rule that plays the flash.

    Reduced-motion blocks are excluded from the search: they turn the
    animation *off* and are compared separately, as their own fact.
    """
    code = _css_code(text)
    for block in _blocks_at_depth_one(code, "@media (prefers-reduced-motion"):
        code = code.replace(block, "")
    found = [
        (_squeezed(selector), _squeezed(declarations(body)["animation"]))
        for selector, body in _RULE.findall(code)
        if FLASH in declarations(body).get("animation", "")
    ]
    assert len(found) == 1, f"expected one rule playing {FLASH}, found {len(found)}"
    return found[0]


def sweep_animation(value: str) -> dict[str, str]:
    """The flash shorthand decomposed into the parts AC-2 compares.

    ``animation: <name> <duration> <easing> <delay>`` — four positional
    tokens, as both sheets write it. ``step`` is the ``* 12ms`` factor pulled
    back out of the delay, so the step can be compared even while the delay
    itself carries a declared divergence (the public page's ``, 0`` fallback).
    """
    tokens = _top_level_tokens(value)
    assert len(tokens) == 4, f"animation shorthand is not four tokens: {tokens}"
    name, duration, easing, delay = tokens
    step = re.search(r"\*\s*([0-9.]+m?s)\s*\)?$", delay)
    return {
        "name": name,
        "duration": duration,
        "easing": easing,
        "delay": delay,
        "step": step.group(1) if step else "",
    }


#: How each player tells a cell where it sits in the diagonal. ``play.js``
#: wraps the value in ``String(…)`` and ``solver.js`` does not, which is a
#: JavaScript spelling rather than a difference in the wave: ``setProperty``
#: stringifies either way. The wrapper is normalised off, the expression is
#: not.
_WAVE_SETTER = re.compile(r'setProperty\(\s*"--player-wave"\s*,\s*(?P<value>[^;]*?)\s*\)\s*;')
_STRING_WRAPPER = re.compile(r"^String\((?P<inner>.*)\)$")


def wave_settings(path: Path) -> list[str]:
    """Every ``--player-wave`` expression ``path`` sets, normalised.

    A **list**, not a single value, because "there is exactly one setter" is
    half the claim: a second one elsewhere in the file would be a second place
    the wave is decided, and the whole lesson of CARD-255 is that the thing
    nobody counted is where the extra executable copy lives.
    """
    found = []
    for _, line in _js_code_lines(path):
        for match in _WAVE_SETTER.finditer(line):
            value = _squeezed(match.group("value"))
            wrapper = _STRING_WRAPPER.match(value)
            found.append(_squeezed(wrapper.group("inner")) if wrapper else value)
    return found


# --------------------------------------------------------------------------
# The compared surface, and the declaration.
# --------------------------------------------------------------------------

#: The dot's selector. Identical in both sheets, so it is a lookup key and
#: not a compared fact.
DOT = '.player-cell[data-state="empty"]::after'

#: The seven properties the dot is made of, written here independently of
#: either sheet. This is the **anti-vacuity** control for AC-1: declaration-set
#: equality is vacuously true when both parses come back empty, so a guard
#: whose regex stopped matching tomorrow would report perfect agreement about
#: nothing. Both sides are held to this set as well as to each other.
DOT_PROPERTIES = frozenset(
    {"content", "display", "width", "height", "margin", "border-radius", "background"}
)

#: What the wave is, written here independently of either script.
WAVE_EXPRESSION = "row + col"


def compared_surface(
    admin_css: str, public_css: str, admin_js_waves: list[str], public_js_waves: list[str]
) -> dict[str, tuple[str, str]]:
    """``{fact: (admin value, public value)}`` — the whole compared surface.

    Every entry is derived from the text handed in. The keys are the surface:
    :func:`disagreements` is total over them, so a fact that starts to differ
    can only be *declared* or *reported*, never overlooked.

    It takes text (and the already-extracted wave lists) rather than paths so
    that the controls can feed it synthetic sheets — a planted divergence is
    then a string substitution, never a file written into the tree.
    """
    admin_sweep_selector, admin_sweep_value = sweep_rule(admin_css)
    public_sweep_selector, public_sweep_value = sweep_rule(public_css)
    admin_sweep = sweep_animation(admin_sweep_value)
    public_sweep = sweep_animation(public_sweep_value)

    def dot(text: str) -> str:
        found = declarations(rules(text)[DOT])
        return "; ".join(f"{name}: {found[name]}" for name in sorted(found))

    surface: dict[str, tuple[str, str]] = {
        "dot.declarations": (dot(admin_css), dot(public_css)),
        f"keyframes.{SETTLE}": (
            keyframes_body(admin_css, SETTLE),
            keyframes_body(public_css, SETTLE),
        ),
        f"keyframes.{FLASH}": (
            keyframes_body(admin_css, FLASH),
            keyframes_body(public_css, FLASH),
        ),
        "sweep.selector": (admin_sweep_selector, public_sweep_selector),
        "reduced-motion.block-count": (
            str(len(reduced_motion_blocks(admin_css))),
            str(len(reduced_motion_blocks(public_css))),
        ),
        "reduced-motion.coverage": (
            " || ".join(reduced_motion_blocks(admin_css)),
            " || ".join(reduced_motion_blocks(public_css)),
        ),
        "wave.expression": (
            " | ".join(admin_js_waves),
            " | ".join(public_js_waves),
        ),
    }
    for part in ("name", "duration", "easing", "delay", "step"):
        surface[f"sweep.animation.{part}"] = (admin_sweep[part], public_sweep[part])
    return surface


def disagreements(surface: dict[str, tuple[str, str]]) -> dict[str, tuple[str, str]]:
    """Those entries of ``surface`` whose two sides are not equal."""
    return {key: pair for key, pair in surface.items() if pair[0] != pair[1]}


#: The divergences that are allowed, each with the reason it is one.
#:
#: This is the half of AC-4 a naive guard gets wrong, and the half CARD-255
#: teaches to constrain. It is not a licence to differ: it is a **frozen
#: declaration over keys that** :func:`compared_surface` **produces**, and
#: :class:`TestPlayerLooksAgree_ADivergenceMustBeDeclared` holds it from both
#: sides — an undeclared disagreement reds, and a declared key that no longer
#: disagrees reds as a stale exemption.
DECLARED_DIVERGENCES: dict[str, str] = {
    "sweep.selector": (
        "Different DOM hooks, for a stated reason. The panel keys the reveal "
        "on `.player-board.is-solved`, a class solver.js adds; the public page "
        "keys it on `body[data-solved=\"true\"]`, because play.js already "
        "writes that attribute on every render — so the reveal fires on the "
        "transition into solved and does not re-trigger while it stays solved, "
        "which is the same once-only reveal the class gives the panel. The "
        "LOOK is what agrees here; the hook it hangs on is each page's own."
    ),
    "sweep.animation.delay": (
        "The public sheet writes `var(--player-wave, 0)` where the panel "
        "writes `var(--player-wave)`. A fallback, not a different delay: the "
        "public page's board is drawn by play.js, which sets the property on "
        "every cell, and the `, 0` keeps the calc() valid rather than invalid "
        "if a cell is ever reached before it is set. The step itself is "
        "compared separately as `sweep.animation.step` and must agree, so this "
        "exemption cannot hide a changed step."
    ),
    "reduced-motion.coverage": (
        "The panel's reduced-motion block blankets the whole player — "
        "`.player-toolbar`, `.player-stage`, their descendants and the sweep — "
        "with `animation: none !important; transition: none !important`, "
        "because the panel has toolbar and stage chrome that animates. The "
        "public page has none of that chrome, so its block names only the two "
        "things that animate there: the banner and the sweep. Both switch the "
        "same reveal off; the surface each has to switch off differs. The "
        "block COUNT is compared separately as "
        "`reduced-motion.block-count` and must agree."
    ),
}

#: The shortest a reason may be. A reason is the entire value an exemption
#: buys: the key says what differs, and only the sentence says whether anyone
#: decided it. A one-word "ok" is the exemption CARD-255 shipped.
_REASON_FLOOR = 120


@pytest.fixture(scope="module")
def admin_css() -> str:
    return ADMIN_CSS.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def public_css() -> str:
    return PUBLIC_CSS.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def surface(admin_css: str, public_css: str) -> dict[str, tuple[str, str]]:
    return compared_surface(
        admin_css, public_css, wave_settings(ADMIN_JS), wave_settings(PUBLIC_JS)
    )


class TestPlayerLooksAgree_TheDotIsDeclarationForDeclarationTheSame:
    """CARD-328 AC-1 — the white mark agrees exactly, and mechanically.

    One arm per claim, deliberately: a test short-circuits at its first
    failing assert, so a single method bundling the anti-vacuity check with
    the equality would report one ``FAILED`` line that says nothing about
    which of them the mutant reached.
    """

    def test_the_rule_is_declared_once_in_each_sheet(
        self, admin_css: str, public_css: str
    ) -> None:
        """Both sheets are searched. Half a guard passes half the mutants."""
        assert rule_count(admin_css, DOT) == 1, "admin.css: the dot rule is not found once"
        assert rule_count(public_css, DOT) == 1, "player.css: the dot rule is not found once"

    def test_the_admin_sheet_declares_the_seven_properties(self, admin_css: str) -> None:
        found = declarations(rules(admin_css)[DOT])
        assert set(found) == DOT_PROPERTIES, sorted(found)

    def test_the_public_sheet_declares_the_seven_properties(self, public_css: str) -> None:
        found = declarations(rules(public_css)[DOT])
        assert set(found) == DOT_PROPERTIES, sorted(found)

    def test_the_two_declaration_sets_are_equal(
        self, admin_css: str, public_css: str
    ) -> None:
        """The claim itself: property names AND values, in both sheets.

        The mutant pairs of AC-5 land here — ``28%`` and
        ``var(--color-text-secondary)``, changed in each sheet in turn.
        """
        assert declarations(rules(admin_css)[DOT]) == declarations(rules(public_css)[DOT])

    def test_the_comparison_is_over_declarations_and_not_over_rule_text(
        self, admin_css: str, public_css: str
    ) -> None:
        """And it has to be: the two rules' TEXT differs and always will.

        ``admin.css`` writes the dot on one line, ``player.css`` over nine. A
        string comparison of the rules would fail on code style while the look
        agreed, which is why AC-1 asks for parsed declarations. This arm is
        what stops a later simplification turning the parse into
        ``admin_rule == public_rule``.
        """
        assert _squeezed(rules(admin_css)[DOT]) != rules(public_css)[DOT]
        assert declarations(rules(admin_css)[DOT]) == declarations(rules(public_css)[DOT])


class TestPlayerLooksAgree_TheSweepSharesItsKeyframesAndItsStep:
    """CARD-328 AC-2 — the solved reveal's shared parts agree.

    Found by what the rule does (it plays :data:`FLASH`) and not by its
    selector, which is a declared divergence. Arm by arm, for the reason
    AC-1's class states.
    """

    def test_the_banner_keyframes_agree(self, admin_css: str, public_css: str) -> None:
        assert keyframes_body(admin_css, SETTLE) == keyframes_body(public_css, SETTLE)

    def test_the_flash_keyframes_agree(self, admin_css: str, public_css: str) -> None:
        assert keyframes_body(admin_css, FLASH) == keyframes_body(public_css, FLASH)

    def test_neither_keyframes_body_is_empty_in_either_sheet(
        self, admin_css: str, public_css: str
    ) -> None:
        """Anti-vacuity: two empty parses are equal and mean nothing."""
        for name in (SETTLE, FLASH):
            for label, text in (("admin.css", admin_css), ("player.css", public_css)):
                body = keyframes_body(text, name)
                assert "{" in body and ":" in body, f"{label}: @keyframes {name} parsed to {body!r}"

    def test_the_sweep_rule_is_found_once_in_each_sheet(
        self, admin_css: str, public_css: str
    ) -> None:
        """``sweep_rule`` asserts the count; this names it as its own arm."""
        assert sweep_rule(admin_css)[1].startswith(FLASH)
        assert sweep_rule(public_css)[1].startswith(FLASH)

    def test_the_sweep_plays_the_same_keyframes_in_both(
        self, admin_css: str, public_css: str
    ) -> None:
        admin = sweep_animation(sweep_rule(admin_css)[1])
        public = sweep_animation(sweep_rule(public_css)[1])
        assert admin["name"] == public["name"] == FLASH

    def test_the_sweep_duration_formula_agrees(
        self, admin_css: str, public_css: str
    ) -> None:
        admin = sweep_animation(sweep_rule(admin_css)[1])
        public = sweep_animation(sweep_rule(public_css)[1])
        assert admin["duration"] == public["duration"]
        assert "var(--duration-base)" in admin["duration"], admin["duration"]

    def test_the_sweep_easing_agrees(self, admin_css: str, public_css: str) -> None:
        admin = sweep_animation(sweep_rule(admin_css)[1])
        public = sweep_animation(sweep_rule(public_css)[1])
        assert admin["easing"] == public["easing"]
        assert "var(--ease)" in admin["easing"], admin["easing"]

    def test_the_per_cell_step_agrees(self, admin_css: str, public_css: str) -> None:
        """The ``* 12ms`` factor — the sweep's edge, and AC-6's first mutant.

        Extracted back out of the delay so it is compared on its own: the
        delay as written carries a declared divergence (the public page's
        ``, 0`` fallback), and a step hidden behind that exemption is exactly
        what the exemption must not be able to buy.
        """
        admin = sweep_animation(sweep_rule(admin_css)[1])
        public = sweep_animation(sweep_rule(public_css)[1])
        assert re.fullmatch(r"[0-9.]+m?s", admin["step"]), admin
        assert admin["step"] == public["step"]


class TestPlayerLooksAgree_BothPlayersSetTheSameWave:
    """CARD-328 AC-3 — both players compute the diagonal the same way.

    ``--player-wave`` is the only part of the reveal that lives in script. The
    two sheets could agree perfectly on the flash and still sweep in different
    directions if the scripts disagreed, so the formula is read off the source
    of both.
    """

    def test_each_player_sets_the_wave_exactly_once(self) -> None:
        """The shape constraint. A second setter is a second decision."""
        assert len(wave_settings(ADMIN_JS)) == 1, wave_settings(ADMIN_JS)
        assert len(wave_settings(PUBLIC_JS)) == 1, wave_settings(PUBLIC_JS)

    def test_both_players_set_the_wave_to_the_same_expression(self) -> None:
        """AC-6's second mutant lands here — ``row + col`` to ``row``."""
        assert wave_settings(ADMIN_JS) == wave_settings(PUBLIC_JS)

    def test_the_wave_is_the_cells_row_plus_its_column(self) -> None:
        """Written out independently, so "the same" cannot be "the same wrong".

        Equality alone would stay green if both scripts were changed to
        ``row`` together; a diagonal is what the flash is for.
        """
        assert wave_settings(ADMIN_JS) == [WAVE_EXPRESSION]
        assert wave_settings(PUBLIC_JS) == [WAVE_EXPRESSION]


class TestPlayerLooksAgree_ADivergenceMustBeDeclared:
    """CARD-328 AC-4 — the divergences are declared, not discovered.

    The guard's set is derived and total over :func:`compared_surface`; this
    class is what makes the exemption table an assertion rather than a note.
    """

    def test_the_compared_surface_is_not_empty_and_names_both_looks(
        self, surface: dict[str, tuple[str, str]]
    ) -> None:
        """Anti-vacuity for the set equality below: an empty surface has no
        disagreements, so a broken extractor would otherwise read as perfect
        agreement."""
        assert len(surface) >= 12, sorted(surface)
        assert "dot.declarations" in surface
        assert f"keyframes.{FLASH}" in surface
        assert "sweep.animation.step" in surface
        assert "wave.expression" in surface

    def test_every_declared_divergence_is_a_fact_the_guard_measures(
        self, surface: dict[str, tuple[str, str]]
    ) -> None:
        """The shape constraint, and the CARD-255 lesson in one line.

        A declaration naming something outside the compared surface exempts
        nothing and hides everything: it reads as a considered allowance while
        the surface it names is never looked at.
        """
        unknown = sorted(set(DECLARED_DIVERGENCES) - set(surface))
        assert unknown == [], f"declared, but not a fact this guard compares: {unknown}"

    def test_every_declared_divergence_carries_a_reason(self) -> None:
        thin = sorted(
            key
            for key, reason in DECLARED_DIVERGENCES.items()
            if len(reason.strip()) < _REASON_FLOOR
        )
        assert thin == [], f"an exemption without a stated reason: {thin}"

    def test_the_disagreements_are_exactly_the_declared_ones(
        self, surface: dict[str, tuple[str, str]]
    ) -> None:
        """The claim. Both directions in one equality.

        An undeclared disagreement is drift between two parallel-maintained
        looks — the thing ADR-0041/R3's byte-identical copying exists to stop
        and that these two looks sit outside of. A declared key that no longer
        disagrees is a stale exemption, which is how an exemption set rots
        into a licence.
        """
        found = disagreements(surface)
        assert set(found) == set(DECLARED_DIVERGENCES), {
            "undeclared": {key: found[key] for key in sorted(set(found) - set(DECLARED_DIVERGENCES))},
            "declared but no longer diverging": sorted(set(DECLARED_DIVERGENCES) - set(found)),
        }

    def test_a_fourth_divergence_in_the_compared_surface_is_reported(
        self, admin_css: str, public_css: str
    ) -> None:
        """The positive control: AC-4's "a fourth divergence reds", exercised.

        The live files agree, so the only way to show this guard CAN fail is
        to hand it a sheet that does not. The planted change is a string
        substitution on the real text, so the control cannot drift away from
        the file it is about, and it plants the divergence in a fact that is
        **not** declared — the dot's geometry — which is precisely what must
        not be absorbable by the exemption table.
        """
        planted = public_css.replace("width: 28%;", "width: 31%;", 1)
        assert planted != public_css, "the plant did not apply — this control measures nothing"
        found = disagreements(
            compared_surface(
                admin_css, planted, wave_settings(ADMIN_JS), wave_settings(PUBLIC_JS)
            )
        )
        assert "dot.declarations" in found
        assert set(found) - set(DECLARED_DIVERGENCES) == {"dot.declarations"}

    def test_a_declared_divergence_that_stops_diverging_is_reported(
        self, admin_css: str, public_css: str
    ) -> None:
        """The other direction: the control for the stale-exemption arm.

        Rewrite the public sweep's selector to the panel's own, and
        ``sweep.selector`` stops being a disagreement. The set equality must
        notice that too, or an exemption could outlive its reason unremarked.
        """
        admin_selector, _ = sweep_rule(admin_css)
        public_selector, _ = sweep_rule(public_css)
        planted = public_css.replace(public_selector, admin_selector)
        assert planted != public_css, "the plant did not apply — this control measures nothing"
        found = disagreements(
            compared_surface(
                admin_css, planted, wave_settings(ADMIN_JS), wave_settings(PUBLIC_JS)
            )
        )
        assert "sweep.selector" not in found
        assert set(DECLARED_DIVERGENCES) - set(found) == {"sweep.selector"}

    def test_the_guard_reads_both_trees_and_not_one_of_them_twice(self) -> None:
        """The defect shape this file exists to catch, asserted about itself.

        A guard that read ``player.css`` on both sides of every comparison
        would be green forever and would pass four of CARD-328's eight
        mutants. The four paths are named here, and they are two trees.
        """
        assert ADMIN_CSS.is_file() and ADMIN_JS.is_file()
        assert PUBLIC_CSS.is_file() and PUBLIC_JS.is_file()
        assert {ADMIN_CSS.parent, PUBLIC_CSS.parent} != {ADMIN_CSS.parent}
        assert "admin" in ADMIN_CSS.parts and "admin" not in PUBLIC_CSS.parts
