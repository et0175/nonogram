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

**And an exemption is over a stated DIFFERENCE, not over a fact.** The first
cut of this file exempted three facts by *key*, and nothing constrained what
could differ inside one; review cycle 1 fired four mutants into the exempted
content and all four survived at ``23 passed`` — the panel flashing the
*empty* cells while this page flashed the filled ones, a panel sweep crossing
the board three times slower, and either sheet dropping the sweep from its
``prefers-reduced-motion`` block. That is the CARD-255 shape one level down:
the table had a shape constraint, the individual exemptions did not. So each
entry of :data:`DECLARED_DIVERGENCES` is a :class:`Divergence` that names the
difference, normalises it away, and leaves a **residue** that is held to
equality like any other fact (:func:`residue_disagreements`) — with a floor
that rejects an unreadable residue on either side, because two absences are
equal, and with one :data:`RESIDUE_CONTROLS` plant per exemption **per sheet**
held to the table by set equality. A fourth exemption added later inherits
all of that: it cannot be declared without a difference and a residue, the
residue arms are total over the table, and it reds until it ships a control
that plants real drift inside it.

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
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

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

#: The media query the reveal's no-motion half lives in, spelled out as far as
#: ``: reduce``. The bare ``@media (prefers-reduced-motion`` opener this used
#: to carry would also match a future ``: no-preference`` block and count it as
#: a reduce block (CARD-328 cycle 1, NIT-2) — harmless today but a fact read
#: off the wrong rule. Tightened, a sheet that renames its query reds on the
#: block count rather than silently measuring the other query.
REDUCED_MOTION = "@media (prefers-reduced-motion: reduce"


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
        for block in _blocks_at_depth_one(_css_code(text), REDUCED_MOTION)
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


def _selector_tail(selector: str) -> str:
    """The last compound of a descendant selector — *which* elements it hits.

    ``.player-board.is-solved .player-cell[data-state="filled"]`` and
    ``body[data-solved="true"] .player-cell[data-state="filled"]`` have the
    same tail and different leading hooks, which is the whole of the
    ``sweep.selector`` divergence: the hook is each page's own, the **target**
    is the thing the two players must agree about.
    """
    tokens = selector.split()
    return tokens[-1] if tokens else ""


def _selector_hook(selector: str) -> str:
    """Everything before :func:`_selector_tail` — the page-state hook."""
    return " ".join(selector.split()[:-1])


#: ``var(--x, <fallback>)`` — one custom property with a fallback argument.
#: Only a flat fallback (no nested parens), which is all either sheet writes;
#: a nested one would leave the text unnormalised and therefore *unequal*,
#: which reds rather than passes.
_VAR_FALLBACK = re.compile(r"var\(\s*(--[A-Za-z0-9_-]+)\s*,[^()]*\)")


def without_var_fallbacks(value: str) -> str:
    """``value`` with every ``var(--x, y)`` rewritten to ``var(--x)``.

    The normalisation behind the ``sweep.animation.delay`` declaration: the
    public sheet's ``, 0`` is the declared difference, so it is normalised
    *away* and what is left must be **equal**. Nothing else about the delay is
    exempted by it.
    """
    return _squeezed(_VAR_FALLBACK.sub(r"var(\1)", value))


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
    for block in _blocks_at_depth_one(code, REDUCED_MOTION):
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


#: What :func:`_measured` is reading — one fact of the compared surface.
_Fact = TypeVar("_Fact")


def _measured(fact: str, read: Callable[[], _Fact]) -> _Fact:
    """``read()``, with ``fact`` named if its parse collapses.

    MIN-2 of CARD-328's cycle 1: :func:`keyframes_body`, :func:`sweep_rule`
    and :func:`sweep_animation` raise inside themselves and the module-scoped
    ``surface`` fixture calls :func:`compared_surface`, so one broken parse
    reports as a fixture ERROR for every arm that wanted the surface. The
    ERRORs remain — handing the arms a sentinel surface instead would make
    "not found" something other than a failure, and that is a control this
    file will not trade — but the message now names the **fact** that stopped
    parsing instead of the fixture, and
    :meth:`TestPlayerLooksAgree_ADivergenceMustBeDeclared.test_the_compared_surface_parses_fact_by_fact`
    turns the same breakage into one named FAILED cell that says which fact it
    was.
    """
    try:
        return read()
    except (AssertionError, KeyError) as broke:
        raise AssertionError(f"{fact} did not parse: {broke}") from broke


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
    admin_sweep_selector, admin_sweep_value = _measured(
        "sweep.selector (admin.css)", lambda: sweep_rule(admin_css)
    )
    public_sweep_selector, public_sweep_value = _measured(
        "sweep.selector (player.css)", lambda: sweep_rule(public_css)
    )
    admin_sweep = _measured(
        "sweep.animation (admin.css)", lambda: sweep_animation(admin_sweep_value)
    )
    public_sweep = _measured(
        "sweep.animation (player.css)", lambda: sweep_animation(public_sweep_value)
    )

    def dot(label: str, text: str) -> str:
        found = _measured(
            f"dot.declarations ({label})", lambda: declarations(rules(text)[DOT])
        )
        return "; ".join(f"{name}: {found[name]}" for name in sorted(found))

    surface: dict[str, tuple[str, str]] = {
        "dot.declarations": (dot("admin.css", admin_css), dot("player.css", public_css)),
        f"keyframes.{SETTLE}": (
            _measured(
                f"keyframes.{SETTLE} (admin.css)", lambda: keyframes_body(admin_css, SETTLE)
            ),
            _measured(
                f"keyframes.{SETTLE} (player.css)", lambda: keyframes_body(public_css, SETTLE)
            ),
        ),
        f"keyframes.{FLASH}": (
            _measured(
                f"keyframes.{FLASH} (admin.css)", lambda: keyframes_body(admin_css, FLASH)
            ),
            _measured(
                f"keyframes.{FLASH} (player.css)", lambda: keyframes_body(public_css, FLASH)
            ),
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


# --------------------------------------------------------------------------
# The declaration — and what each declared difference has to leave standing.
#
# Cycle 1's IMP-1: this table used to exempt by KEY, and nothing constrained
# what could differ *within* an exempted key. Four mutants fired inside the
# three exempted facts all survived at 23 passed: the panel flashing the EMPTY
# cells while this page flashed the filled ones (the exact defect 2400501b
# existed to fix), a panel sweep crossing the board three times slower, and
# either sheet dropping the sweep from its prefers-reduced-motion block (an
# accessibility regression against this card's own Design-context standard).
# That is G-5's defect shape one level down — the table had a shape constraint,
# the individual exemptions did not.
#
# So an exemption does not name a fact. It names the DIFFERENCE, normalises it
# away, and what is LEFT — the residue — is compared like any other fact.
# --------------------------------------------------------------------------

#: A residue that could not be read, prefixed so either side carrying it is a
#: failure. Two unreadable residues are *equal*, so equality alone would let
#: "neither sheet does this any more" pass as agreement;
#: ``test_no_declared_divergence_has_an_unreadable_residue`` is the floor that
#: closes it.
UNREADABLE = "!!"


def _sweep_target(selector: str, _own_sweep_selector: str) -> str:
    """``sweep.selector``'s residue: **which cells** the sweep flashes.

    The declared difference is the leading page-state hook, so only the hook
    is normalised away — and only one hook's worth of it: a selector that is
    not ``<hook> <target>`` is unreadable rather than quietly truncated.
    """
    if len(selector.split()) != 2:
        return f"{UNREADABLE} not a `<page-state hook> <target>` selector: {selector!r}"
    return _selector_tail(selector)


def _delay_without_its_fallback(delay: str, _own_sweep_selector: str) -> str:
    """``sweep.animation.delay``'s residue: the delay, fallback normalised off.

    The ``, 0`` is the declared difference and nothing else about the delay
    is. A delay that no longer reads ``--player-wave`` at all is unreadable:
    the exemption is over a fallback, not over the diagonal.
    """
    normalised = without_var_fallbacks(delay)
    if "var(--player-wave)" not in normalised:
        return f"{UNREADABLE} the delay does not read --player-wave: {delay!r}"
    return normalised


def _how_the_sweep_is_quieted(coverage: str, own_sweep_selector: str) -> str:
    """``reduced-motion.coverage``'s residue: how this sheet quiets its OWN sweep.

    The two blocks legitimately cover different surfaces — the panel has
    toolbar and stage chrome to quiet and this page has none of it — so the
    selector *lists* are not comparable and never will be. What must agree is
    the invariant underneath: **each sheet's reduced-motion block names that
    sheet's own sweep selector, with the animation switched off**.

    The block is searched for the sheet's own sweep selector *exactly*, hook
    included — a block that quiets ``.player-board.is-solved .player-cell[…]``
    while the sweep has moved to another hook quiets nothing, which is a real
    regression and not a formatting difference. Only the value returned is
    normalised to the selector's tail, so the two sheets' residues are
    comparable at all; ``!important`` is normalised off because that is panel
    specificity, not a different switch.
    """
    target = _selector_tail(own_sweep_selector)
    for selector, body in _RULE.findall(coverage):
        group = [_squeezed(part) for part in selector.split(",") if part.strip()]
        if _squeezed(own_sweep_selector) not in group:
            continue
        animation = _squeezed(
            declarations(body).get("animation", "").replace("!important", "")
        )
        if animation != "none":
            return (
                f"{UNREADABLE} {target} is named but its animation is not "
                f"switched off: {animation!r}"
            )
        return f"{target} {{ animation: none }}"
    return (
        f"{UNREADABLE} {own_sweep_selector!r} is not named in this sheet's "
        f"reduced-motion block, so its sweep ({target}) is not quieted there"
    )


@dataclass(frozen=True)
class Divergence:
    """One declared divergence: what differs, why, and what must still agree.

    * ``reason`` — the sentence. The key says *what* differs; only the
      sentence says whether anyone decided it.
    * ``difference`` — the thing being normalised away, in a phrase.
    * ``residue`` — ``(this side's value, this side's sweep selector) -> what
      is left``. :func:`residue_disagreements` holds the two residues to
      **equality**, which is what turns an exemption from a licence over a
      fact into a licence over a stated difference.

    A fourth exemption added later cannot skip any of the three: the table's
    value type requires them, ``test_every_declared_divergence_…`` arms are
    total over the table, and :data:`RESIDUE_CONTROLS` is held to it by set
    **equality**, so a fourth entry reds until it ships a control that plants
    real drift inside it.
    """

    reason: str
    difference: str
    residue: Callable[[str, str], str]


#: The divergences that are allowed, each with the reason it is one and the
#: residue it still has to leave in agreement.
#:
#: This is the half of AC-4 a naive guard gets wrong, and the half CARD-255
#: teaches to constrain. It is not a licence to differ: it is a **frozen
#: declaration over keys that** :func:`compared_surface` **produces**, and
#: :class:`TestPlayerLooksAgree_ADivergenceMustBeDeclared` holds it from three
#: sides — an undeclared disagreement reds, a declared key that no longer
#: disagrees reds as a stale exemption, and a declared key whose residue stops
#: agreeing reds as drift *inside* the exemption.
DECLARED_DIVERGENCES: dict[str, Divergence] = {
    "sweep.selector": Divergence(
        reason=(
            "Different DOM hooks, for a stated reason. The panel keys the reveal "
            "on `.player-board.is-solved`, a class solver.js adds; the public page "
            "keys it on `body[data-solved=\"true\"]`, because play.js already "
            "writes that attribute on every render — so the reveal fires on the "
            "transition into solved and does not re-trigger while it stays solved, "
            "which is the same once-only reveal the class gives the panel. The "
            "LOOK is what agrees here; the hook it hangs on is each page's own. "
            "Only the hook is exempted: the residue — WHICH cells the sweep "
            "flashes — is compared, so a state-name refactor that aims one "
            "player's sweep at the empty cells reds instead of being absorbed."
        ),
        difference="the leading page-state hook, `.player-board.is-solved` vs `body[data-solved=\"true\"]`",
        residue=_sweep_target,
    ),
    "sweep.animation.delay": Divergence(
        reason=(
            "The public sheet writes `var(--player-wave, 0)` where the panel "
            "writes `var(--player-wave)`. A fallback, not a different delay: the "
            "public page's board is drawn by play.js, which sets the property on "
            "every cell, and the `, 0` keeps the calc() valid rather than invalid "
            "if a cell is ever reached before it is set. The step itself is "
            "compared separately as `sweep.animation.step` and must agree, so this "
            "exemption cannot hide a changed step. The fallback is also all that "
            "is exempted: the residue is the delay with every var() fallback "
            "normalised away, compared for equality, so a delay the step cannot "
            "see — a factor in front of the wave, say — reds."
        ),
        difference="the `, 0` fallback inside `var(--player-wave, 0)`",
        residue=_delay_without_its_fallback,
    ),
    "reduced-motion.coverage": Divergence(
        reason=(
            "The panel's reduced-motion block blankets the whole player — "
            "`.player-toolbar`, `.player-stage`, their descendants and the sweep — "
            "with `animation: none !important; transition: none !important`, "
            "because the panel has toolbar and stage chrome that animates. The "
            "public page has none of that chrome, so its block names only the two "
            "things that animate there: the banner and the sweep. Both switch the "
            "same reveal off; the surface each has to switch off differs. The "
            "block COUNT is compared separately as "
            "`reduced-motion.block-count` and must agree. The *lists* are what is "
            "exempted, and only them: the residue is each sheet's own sweep "
            "selector quieted in its own block, so either sheet dropping the "
            "sweep from its reduced-motion block reds instead of reading as "
            "chrome the other page does not have."
        ),
        difference="the selector lists (5 in the panel, 2 here) and `!important`",
        residue=_how_the_sweep_is_quieted,
    ),
}


def residues(surface: dict[str, tuple[str, str]]) -> dict[str, tuple[str, str]]:
    """``{declared key: (admin residue, public residue)}``.

    Each side's residue is read against **that side's own** sweep selector,
    taken from the surface rather than written down, because a sheet's
    reduced-motion block has to be read against the hook that sheet uses.
    A declared key the surface does not carry is skipped here and caught by
    ``test_every_declared_divergence_is_a_fact_the_guard_measures`` instead,
    so a missing key cannot masquerade as an unreadable residue.
    """
    admin_sweep_selector, public_sweep_selector = surface["sweep.selector"]
    return {
        key: (
            declared.residue(surface[key][0], admin_sweep_selector),
            declared.residue(surface[key][1], public_sweep_selector),
        )
        for key, declared in DECLARED_DIVERGENCES.items()
        if key in surface
    }


def residue_disagreements(surface: dict[str, tuple[str, str]]) -> dict[str, tuple[str, str]]:
    """Declared divergences whose **residue** does not agree — real drift
    inside an exemption, which is what IMP-1's four surviving mutants were."""
    return {key: pair for key, pair in residues(surface).items() if pair[0] != pair[1]}


# --------------------------------------------------------------------------
# The controls. One per declared divergence is not enough — a control is
# measured per exemption AND per sheet, because a residue computed from one
# tree twice would pass half of these. They plant on the real text, so a
# control cannot drift away from the file it is about, and they are the four
# cycle-1 probes (N1–N4) made executable.
# --------------------------------------------------------------------------


def _retarget_the_sweep(css: str) -> str:
    """``css`` with its sweep aimed at the EMPTY cells, not the filled ones.

    N1's shape: a state-name refactor in one sheet, and the two players
    disagree about what solving looks like.
    """
    selector, _ = sweep_rule(css)
    opener = f"{selector} {{"
    assert opener in css, f"the plant did not apply — no {opener!r} in this sheet"
    return css.replace(opener, f'{selector.replace("filled", "empty")} {{', 1)


def _slow_the_sweep(css: str) -> str:
    """``css`` with its sweep crossing the board three times slower (N2)."""
    _, value = sweep_rule(css)
    delay = sweep_animation(value)["delay"]
    assert delay in css, f"the plant did not apply — no {delay!r} in this sheet"
    return css.replace(delay, delay.replace("calc(", "calc(3 * ", 1), 1)


def _unquiet_the_sweep(css: str) -> str:
    """``css`` with the sweep dropped from its reduced-motion block (N3/N4)."""
    selector, _ = sweep_rule(css)
    blocks = _blocks_at_depth_one(css, REDUCED_MOTION)
    assert len(blocks) == 1, f"the plant did not apply — {len(blocks)} reduced-motion blocks"
    stripped = re.sub(rf",?\s*{re.escape(selector)}", "", blocks[0], count=1)
    assert stripped != blocks[0], "the plant did not apply — the block does not name the sweep"
    return css.replace(blocks[0], stripped, 1)


def _on_admin(mutate: Callable[[str], str]) -> Callable[[str, str], tuple[str, str]]:
    return lambda admin_css, public_css: (mutate(admin_css), public_css)


def _on_public(mutate: Callable[[str], str]) -> Callable[[str, str], tuple[str, str]]:
    return lambda admin_css, public_css: (admin_css, mutate(public_css))


#: ``{declared key: ((name, plant), …)}`` — per exemption, the drift it must
#: not be able to absorb. Held to :data:`DECLARED_DIVERGENCES` by set
#: **equality**, so a fourth exemption reds until it brings its own.
RESIDUE_CONTROLS: dict[str, tuple[tuple[str, Callable[[str, str], tuple[str, str]]], ...]] = {
    "sweep.selector": (
        ("the panel flashes the empty cells", _on_admin(_retarget_the_sweep)),
        ("the public page flashes the empty cells", _on_public(_retarget_the_sweep)),
    ),
    "sweep.animation.delay": (
        ("the panel's sweep is three times slower", _on_admin(_slow_the_sweep)),
        ("the public sweep is three times slower", _on_public(_slow_the_sweep)),
    ),
    "reduced-motion.coverage": (
        ("the panel stops quieting its sweep", _on_admin(_unquiet_the_sweep)),
        ("the public page stops quieting its sweep", _on_public(_unquiet_the_sweep)),
    ),
}

#: One case per (exemption, sheet). Flattened at module scope so each is its
#: own node id: a control bundled into one arm would short-circuit at the
#: first failing plant and say nothing about the rest.
_RESIDUE_CONTROL_CASES = [
    pytest.param(key, plant, id=f"{key}::{name}")
    for key, controls in RESIDUE_CONTROLS.items()
    for name, plant in controls
]

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
        """And it has to be: the two rules' TEXT differs today.

        ``admin.css`` writes the dot on one line, ``player.css`` over nine. A
        string comparison of the rules would fail on code style while the look
        agreed, which is why AC-1 asks for parsed declarations — and this arm
        is the premise of that reasoning, so it is stated where it can fail.

        **Like against like** (MIN-1 of cycle 1). This used to squeeze the
        admin operand and leave the public one raw, and a raw declaration body
        always begins with the whitespace after ``{`` while ``_squeezed``
        strips it — so the two could essentially never be equal and the arm
        could not fail. It was shown surviving a pure reformat of
        ``player.css``'s dot onto one line byte-identical to the admin's.
        Both operands are now raw: that reformat reds here, and the claim this
        arm carries is **only** that the two texts differ today, not that they
        must forever.
        """
        admin_text = rules(admin_css)[DOT]
        public_text = rules(public_css)[DOT]
        assert admin_text != public_text, (
            "the two dot rules are now byte-identical in text. Nothing is broken, "
            "but the premise of the parsed-declaration comparison is gone: say so "
            "rather than leaving this arm asserting it."
        )
        assert declarations(admin_text) == declarations(public_text)

    def test_reformatting_a_dot_rule_moves_no_declaration(self, public_css: str) -> None:
        """The claim the arm above cannot carry, held where it CAN fail.

        "The comparison is over declarations, not text" is a property of
        :func:`declarations`, not of how the two sheets happen to be laid out
        today: collapsing the public rule onto one line moves no pixel, and it
        must move no compared fact either. A text comparison would red on this
        reformat; the parse must not.
        """
        text = rules(public_css)[DOT]
        reformatted = _squeezed(text)
        assert reformatted != text, "the reformat did not apply — this control measures nothing"
        assert declarations(reformatted) == declarations(text)
        assert set(declarations(reformatted)) == DOT_PROPERTIES


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
            for key, declared in DECLARED_DIVERGENCES.items()
            if len(declared.reason.strip()) < _REASON_FLOOR
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

    def test_the_compared_surface_parses_fact_by_fact(
        self, admin_css: str, public_css: str
    ) -> None:
        """One named cell for a collapsed parse (MIN-2 of cycle 1).

        The helpers raise inside themselves and the ``surface`` fixture calls
        :func:`compared_surface`, so a broken regex reports as a fixture ERROR
        for every arm that wanted the surface. That stays — a surface handed
        out with sentinels where a fact should be would make "not found"
        something other than a failure. This arm does not depend on the
        fixture, so a collapsed parse always produces **one FAILED cell whose
        message names the fact**, and :func:`_measured` is what puts the fact's
        name in it.
        """
        try:
            compared_surface(
                admin_css, public_css, wave_settings(ADMIN_JS), wave_settings(PUBLIC_JS)
            )
        except AssertionError as broke:  # pragma: no cover - the red path
            pytest.fail(f"the compared surface did not parse — {broke}", pytrace=False)

    def test_every_declared_divergence_names_the_difference_it_normalises_away(
        self,
    ) -> None:
        """An exemption is over a stated DIFFERENCE, never over a fact.

        The shape constraint IMP-1 was missing: every entry carries the phrase
        naming what is normalised away and the callable that normalises it, so
        a fourth exemption cannot be declared as a bare reason the way these
        three were.
        """
        for key, declared in DECLARED_DIVERGENCES.items():
            assert isinstance(declared, Divergence), f"{key}: {type(declared).__name__}"
            assert declared.difference.strip(), f"{key}: no difference named"
            assert callable(declared.residue), f"{key}: no residue to compare"

    def test_every_declared_divergence_agrees_on_the_residue_it_leaves(
        self, surface: dict[str, tuple[str, str]]
    ) -> None:
        """The claim IMP-1 asked for: the exemptions are over differences.

        Normalise each declared difference away and what is **left** must
        agree. This is the arm the four cycle-1 probes survived for want of:
        the panel flashing the empty cells (``sweep.selector``'s residue is
        *which* cells), a three-times-slower panel sweep
        (``sweep.animation.delay``'s residue is the delay with the fallback
        gone) and either sheet dropping the sweep from its reduced-motion
        block (``reduced-motion.coverage``'s residue is that sheet's own sweep,
        quieted). Total over the table, so a fourth exemption is held to it
        the moment it is added.
        """
        found = residue_disagreements(surface)
        assert found == {}, {
            "drift inside a declared divergence": found,
            "what each exemption exempts": {
                key: DECLARED_DIVERGENCES[key].difference for key in found
            },
        }

    def test_no_declared_divergence_has_an_unreadable_residue(
        self, surface: dict[str, tuple[str, str]]
    ) -> None:
        """The floor under the equality above. Two absences are equal.

        If both sheets stopped quieting the sweep, both residues would read
        ``!! …`` and the equality would hold — agreement about nothing, the
        same vacuity ``DOT_PROPERTIES`` and ``WAVE_EXPRESSION`` guard against
        for the facts that agree outright.
        """
        unreadable = {
            f"{key} ({side})": value
            for key, pair in residues(surface).items()
            for side, value in (("admin.css", pair[0]), ("player.css", pair[1]))
            if value.startswith(UNREADABLE) or not value.strip()
        }
        assert unreadable == {}, unreadable

    def test_every_declared_divergence_carries_a_control_of_its_own(self) -> None:
        """Set **equality**, so a fourth exemption brings its own control.

        G-5 asks an exemption for a shape constraint *and* a control. The
        residue is the shape constraint; :data:`RESIDUE_CONTROLS` is the
        control, and holding the two tables to each other by equality is what
        makes the pairing structural rather than a habit three entries happen
        to follow.
        """
        assert set(RESIDUE_CONTROLS) == set(DECLARED_DIVERGENCES), {
            "declared with no control": sorted(set(DECLARED_DIVERGENCES) - set(RESIDUE_CONTROLS)),
            "a control for nothing declared": sorted(
                set(RESIDUE_CONTROLS) - set(DECLARED_DIVERGENCES)
            ),
        }
        empty = sorted(key for key, controls in RESIDUE_CONTROLS.items() if not controls)
        assert empty == [], f"an exemption whose control plants nothing: {empty}"

    @pytest.mark.parametrize(("key", "plant"), _RESIDUE_CONTROL_CASES)
    def test_real_drift_inside_a_declared_divergence_is_reported(
        self,
        admin_css: str,
        public_css: str,
        key: str,
        plant: Callable[[str, str], tuple[str, str]],
    ) -> None:
        """Per exemption, per sheet: the drift the exemption must not absorb.

        Each case plants real drift **inside** one declared divergence on one
        sheet's real text, then asserts two things in order:

        1. the key-level table still absorbs it — the disagreement set is
           still exactly the declared one, which is *why* the matching cycle-1
           probe survived at ``23 passed``;
        2. the residue reports it anyway.

        Assert 1 is not decoration: without it a plant that reds the key-level
        equality would pass this arm while proving nothing about the residue.
        """
        planted_admin, planted_public = plant(admin_css, public_css)
        assert (planted_admin, planted_public) != (admin_css, public_css), (
            "the plant did not apply — this control measures nothing"
        )
        planted = compared_surface(
            planted_admin, planted_public, wave_settings(ADMIN_JS), wave_settings(PUBLIC_JS)
        )
        absorbed = set(disagreements(planted))
        assert absorbed == set(DECLARED_DIVERGENCES), {
            "why this assert is here": (
                "the key-level table must still absorb this plant — that is WHY the "
                "matching cycle-1 probe survived at 23 passed. Red here means either "
                "the plant is not inside an exemption, or the live sheets have drifted "
                "already: read test_the_disagreements_are_exactly_the_declared_ones first."
            ),
            "disagreeing but not declared": sorted(absorbed - set(DECLARED_DIVERGENCES)),
            "declared but no longer disagreeing": sorted(set(DECLARED_DIVERGENCES) - absorbed),
        }
        found = residue_disagreements(planted)
        assert key in found, {
            "the exemption absorbed real drift": key,
            "residues": residues(planted),
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
