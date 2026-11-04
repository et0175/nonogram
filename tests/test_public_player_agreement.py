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

The Maybe mark, and why it is here at all (CARD-339)
----------------------------------------------------
The dot and the reveal were in the compared surface from the first commit. The
**Maybe mark was not** — this module contained the string ``maybe`` zero times
until CARD-339, measured at that card's decompose station. So when the two
sheets came to disagree about it (the admin drew a "?" glyph in the accent
token on the cell and the swatch; this page drew a tint and no glyph), nothing
reported it: it did not diverge *past* a guard, it diverged where no guard was
looking, and it reached a render — ``~/Documents/nonogram-reviews/CARD-323/``,
which is where the owner saw it — before it reached a test. CARD-323 measured
it, refused to force it (its own AC-4 made re-declaring the rule a finding
against itself) and routed it; the owner decided on 2026-11-03 that the public
page gains the glyph; CARD-339 added it and widened this surface so the next
drift in that mark reds here instead.

**And the glyph was the symptom, so the glyph alone is not the fix.** The marks
are now **censused** rather than assumed: :func:`mark_census` enumerates every
cell state ``solver_state.js`` declares (:func:`cell_states` — the authority the
runtime can enumerate, ADR-0039/R2) against both hooks and both sheets, and
:meth:`TestPlayerLooksAgree_TheOtherMarksAreCensusedNotAssumed.test_every_census_fact_is_compared_routed_or_agreeing`
requires every fact of it to be one of three things: **compared** here,
**agreeing** outright, or **routed** — named in :data:`SIBLING_FINDINGS` with a
sentence and a measured figure, because a divergence in a rendered mark that no
owner has decided is a finding and not a worktree call (see the section below,
which says so in as many words). A fact that is none of the three reds, and a
routed finding that stops diverging reds too. That is what keeps "the Maybe
mark agrees" from being read as "the marks agree".

:data:`SIBLING_FINDINGS` is **not** a second :data:`DECLARED_DIVERGENCES`, and
the difference is worth stating because the two look alike. A declared
divergence is a fact **inside** the compared surface that is *allowed* to
differ for a decided reason. A routed finding is a fact **outside** it that
*does* differ, that nobody has decided, and that this guard pins **as
diverging**. Nothing is exempted by being routed: the compared surface stays
exactly as wide as it is, and the census is what makes its edge visible.

**What "pinned" buys, stated narrowly because a first draft of this paragraph
overclaimed it** (CARD-339 cycle 1, F-3, falsified by plant rather than by
reading). The classification is held in both directions — a seventh fact that
starts diverging reds as unclassified, and a routed fact that *stops* diverging
reds as a stale entry. The **content** of a routed divergence is NOT held:
changing the admin's filled-swatch ``border-color``, or repainting the public
Clear swatch in ink, leaves each fact diverging and the arm green. Only the two
Maybe papers are value-pinned, and only by hand-written literals in
:meth:`TestPlayerLooksAgree_TheOtherMarksAreCensusedNotAssumed.test_the_paper_under_the_maybe_mark_is_a_routed_finding_and_not_an_exemption`
— and **"the two Maybe papers" is two facts but not four sides**, found by plant
in CARD-339 cycle 2, the same way the sentence above it was found. Of the four
fact-sides, **three** are held: the *cell*'s two sides by the written-out
literals, and the *swatch*'s **public** side transitively, through that arm's
closing ``census[cell][1] == census[swatch][1]``. The swatch's **admin** side is
held only to *differing from this page's* — plant a background on ``admin.css``'s
Maybe swatch (it declares none today, so the fact falls through to
``.player-swatch``'s ``--grid-paper``) and the census moves while every arm in
this module stays green. That fourth side is **CARD-346's** with the rest.
:data:`DECLARED_DIVERGENCES` has the counterpart this table lacks —
:data:`RESIDUE_CONTROLS`, which exists because CARD-328's cycle-1 review raised
it as IMP-1 — and **CARD-346 owes this registry the same**, derived rather than
written down. Until it lands, "routed" means classified, not pinned by value.

What this module does **not** do
--------------------------------
It changes no rendered pixel, and it is not allowed to. If it ever finds a
real disagreement, that is a **finding for the owner**: the admin and the
public page disagreeing about a mark is the defect ``2400501b`` existed to
fix, and deciding which side is right is not a worktree call.

It also does not widen ``COPIED_FROM_ADMIN`` or soften ADR-0041/R3. Making
``admin.css`` a byte-identical copy is a different and much larger decision
(the two sheets are not interchangeable) and belongs to the architect station.

CARD-339's check refs, by node id
---------------------------------
Written out in full, path and name on one line each, for the reason
``tests/test_public_player.py``'s own table gives: the architecture validator
resolves a check ref by a TEXT search for the whole ``path::name`` string, so a
ref wrapped across two lines reads as dead however green the test is.

* AC-1 — ``tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheMaybeMarkIsTheSameMark``
* AC-2 — ``tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheMaybeMarkIsTheSameMark::test_a_one_sided_change_to_the_maybe_mark_is_reported``
* AC-2 — ``tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheMaybeMarkIsTheSameMark::test_a_glyph_deleted_from_this_page_is_a_failure_and_not_an_absence``
* AC-3 — ``tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheMaybeMarkIsTheSameMark::test_the_maybe_mark_is_a_fact_this_guard_compares``
* AC-4 — ``tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheOtherMarksAreCensusedNotAssumed::test_the_paper_under_the_maybe_mark_is_a_routed_finding_and_not_an_exemption``
* AC-5 — ``tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheOtherMarksAreCensusedNotAssumed::test_every_census_fact_is_compared_routed_or_agreeing``

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
#: The pure module ADR-0041/R3 copies byte-identically into the public site. It
#: is read here for ONE thing: the set of cell states, which is the authority
#: :func:`mark_census` is derived from. Read from ``src/`` rather than from
#: ``player/`` on purpose — the admin's is the original and the copy's equality
#: to it is ``player/assemble.py``'s claim, asserted elsewhere, not a premise
#: this file should quietly lean on.
STATE_MODULE = _REPO / "src" / "nonogram" / "admin" / "static" / "solver_state.js"


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


#: ``export const NAME = "value";`` in ``solver_state.js``.
_STATE_CONST = re.compile(r'export const ([A-Z_]+) = "([a-z]+)";')

#: Its frozen state list.
_STATE_LIST = re.compile(r"export const CELL_STATES = Object\.freeze\(\[([^\]]+)\]\);")


def cell_states() -> list[str]:
    """Every cell state the shared module declares, in its own order.

    The authority ADR-0039/R2 asks for: the set the census is total over is
    **enumerated from the module both players import**, never written down
    here, so a fifth state added to ``solver_state.js`` is **enumerated**
    rather than left outside — four more facts, not none. What then happens is
    worth stating precisely rather than overclaiming: if one sheet styles it
    and the other does not, those facts diverge and red as undeclared; if
    neither styles it, both papers fall through to the hook's base rule, the
    facts agree, and that is the correct answer rather than a hole. The claim
    is totality over the states, not that an unstyled state is a defect.

    Reimplemented rather than imported: ``tests/test_public_player_maybe.py``
    reads the same constant for its own purpose and imports this module's CSS
    parser, so importing its reader back would be a cycle. Thirteen lines of
    regex, which is the trade CLAUDE.md's ``mask_runs`` precedent names.
    """
    text = STATE_MODULE.read_text(encoding="utf-8")
    values = dict(_STATE_CONST.findall(text))
    listed = _STATE_LIST.search(text)
    assert listed is not None, "solver_state.js does not declare CELL_STATES as a frozen array"
    names = [name.strip() for name in listed.group(1).split(",") if name.strip()]
    assert names, "CELL_STATES is empty"
    resolved = [values[name] for name in names]
    assert len(set(resolved)) == len(resolved), resolved
    return resolved


#: The Maybe mark's glyph, per hook — the fact CARD-339 put in this surface.
#: Both sheets spell the selector identically, so like :data:`DOT` it is a
#: lookup key and not a compared fact. The glyph is an ``::after`` for the
#: reason the dot is: the cell's background is its paper, and a mark painted
#: into it cannot be sized from the cell's own box.
MAYBE_CELL_GLYPH = '.player-cell[data-state="maybe"]::after'
MAYBE_SWATCH_GLYPH = '.player-swatch[data-state="maybe"]::after'

#: The anti-vacuity floor for the two glyph comparisons, written here
#: independently of either sheet — :data:`DOT_PROPERTIES`' discipline, applied
#: to the mark CARD-339 added. Declaration-set equality is vacuously true when
#: both parses come back empty, so each side is held to its property set as
#: well as to the other side.
#:
#: The two sets differ from each other **by design and not by drift**: the cell
#: glyph is a block sized from the cell (``text-align`` centres it in the
#: cell's box), the swatch glyph is a flex box filling 1em of button chrome.
#: The admin declares them that way too, so each set is compared against *the
#: same hook in the other sheet* and never across hooks.
MAYBE_CELL_GLYPH_PROPERTIES = frozenset(
    {"content", "display", "font-size", "line-height", "font-weight", "text-align", "color"}
)
MAYBE_SWATCH_GLYPH_PROPERTIES = frozenset(
    {
        "content",
        "position",
        "inset",
        "display",
        "align-items",
        "justify-content",
        "font-size",
        "font-weight",
        "line-height",
        "color",
    }
)

#: What the mark *is*, written out independently of either sheet. Equality
#: alone would stay green if both sheets were changed to draw "!" in the ink
#: token together, and "the two agree" is not the claim AC-1 makes — the claim
#: is that this page draws the admin's mark.
MAYBE_GLYPH_CONTENT = '"?"'
MAYBE_GLYPH_COLOUR = "var(--color-accent)"

#: The floor the cell glyph's ``font-size`` reads. It is declared in
#: ``admin.css`` and in ``player.css``, **not** in the ``tokens.css`` R3 copies
#: byte-identically, so the two declarations could read equal while rendering
#: at different sizes. Compared as its own fact (``numeral-floor.value``) for
#: exactly that reason.
NUMERAL_FLOOR = "--player-numeral-min"


def custom_property(text: str, name: str) -> str:
    """The one value ``text`` declares for custom property ``name``.

    "Exactly one declaration" is half the claim, as it is for the wave setter:
    a second one is a second place the value is decided. A ``var(--name)``
    *reference* is a value and never matches, because :func:`declarations`
    keys a declaration by its own property.
    """
    found = [
        value
        for _, body in _RULE.findall(_css_code(text))
        for prop, value in declarations(body).items()
        if prop == name
    ]
    assert len(found) == 1, f"{name}: expected one declaration, found {len(found)}"
    return found[0]


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

    def rule(fact: str, selector: str, label: str, text: str) -> str:
        """One rule's declarations, normalised into a comparable string."""
        found = _measured(f"{fact} ({label})", lambda: declarations(rules(text)[selector]))
        return "; ".join(f"{name}: {found[name]}" for name in sorted(found))

    def dot(label: str, text: str) -> str:
        return rule("dot.declarations", DOT, label, text)

    surface: dict[str, tuple[str, str]] = {
        "dot.declarations": (dot("admin.css", admin_css), dot("player.css", public_css)),
        # CARD-339. The Maybe mark, per hook — the two facts whose absence from
        # this dict is the defect that card exists to fix. Read exactly as the
        # dot is read: by the selector both sheets spell the same way, into a
        # declaration set, with a property-set floor under each side.
        "maybe.cell.glyph.declarations": (
            rule("maybe.cell.glyph.declarations", MAYBE_CELL_GLYPH, "admin.css", admin_css),
            rule("maybe.cell.glyph.declarations", MAYBE_CELL_GLYPH, "player.css", public_css),
        ),
        "maybe.swatch.glyph.declarations": (
            rule("maybe.swatch.glyph.declarations", MAYBE_SWATCH_GLYPH, "admin.css", admin_css),
            rule("maybe.swatch.glyph.declarations", MAYBE_SWATCH_GLYPH, "player.css", public_css),
        ),
        # The token the cell glyph's font-size reads, which lives in each sheet
        # rather than in the copied tokens.css: without this fact the two
        # declarations could read equal and render at different sizes.
        "numeral-floor.value": (
            _measured(
                f"numeral-floor.value (admin.css)",
                lambda: custom_property(admin_css, NUMERAL_FLOOR),
            ),
            _measured(
                f"numeral-floor.value (player.css)",
                lambda: custom_property(public_css, NUMERAL_FLOOR),
            ),
        ),
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



# --------------------------------------------------------------------------
# The marks, censused (CARD-339 item 4 / AC-5).
#
# The compared surface above is a list of facts somebody chose to put in it,
# and the Maybe mark's drift is what that costs: a mark nobody added was a mark
# nobody compared, and nothing said so. The census is the answer to that shape
# rather than to that instance. It enumerates every state the shared module
# declares against both hooks and both sheets, and every fact it produces has
# to be one of three things — COMPARED above, AGREEING outright, or ROUTED in
# SIBLING_FINDINGS with a sentence and a measured figure. A fourth kind of fact
# does not exist, so a sibling gap can no longer be silent.
# --------------------------------------------------------------------------


def _cascade(text: str, selector: str) -> dict[str, str]:
    """Every flat rule of ``text`` spelled exactly ``selector``, cascaded.

    In document order, later declarations winning, which is what CSS does with
    a selector declared twice. :func:`rules` keeps only the LAST body, and that
    is not good enough here: ``admin.css`` declares ``.player-cell`` twice and
    the base ``background`` is in the first of them, so a reader that took
    ``rules()[".player-cell"]`` would find the admin's cells had no paper.
    """
    found: dict[str, str] = {}
    for selector_text, body in _RULE.findall(_css_code(text)):
        if _squeezed(selector_text) == selector:
            found.update(declarations(body))
    return found


def mark_paper(text: str, hook: str, state: str) -> dict[str, str]:
    """What ``text`` paints the ``state`` mark's own box with, on ``hook``.

    The state rule's own declarations, with ``background`` resolved against the
    hook's base rule — because "declares no background" and "declares the
    base's background" are the SAME paper and must not read as a divergence.
    ``admin.css`` omits the rule where ``player.css`` writes it out, three
    times over, and a census that reported those three would be three
    findings nobody can act on standing beside the two that matter.
    """
    own = _cascade(text, f'{hook}[data-state="{state}"]')
    base = _cascade(text, hook)
    painted = dict(own)
    painted["background"] = own.get("background") or base.get(
        "background", f"{UNREADABLE} neither {hook}[data-state=\"{state}\"] nor {hook} paints"
    )
    return painted


def mark_glyph(text: str, hook: str, state: str) -> dict[str, str]:
    """What ``text`` draws ON the ``state`` mark, on ``hook`` — its ``::after``.

    ``{}`` when there is none, which is a real answer and not an absence: "the
    admin draws a mark here and this page draws nothing" is precisely the
    divergence CARD-339 was raised for, and it is also still true of the White
    swatch (see :data:`SIBLING_FINDINGS`).
    """
    return _cascade(text, f'{hook}[data-state="{state}"]::after')


#: The two hooks a mark is drawn on: a board cell, and the brush button's
#: preview of it. Both sheets use these two class names and no others, which is
#: what makes the public swatch a preview of the public cell at all.
MARK_HOOKS = (".player-cell", ".player-swatch")

#: What is read for each (hook, state): the paper under the mark and the glyph
#: on it. Two facts, because they fail independently — the Maybe mark's glyph
#: was missing while its paper was merely different, and the White swatch is
#: the reverse.
_MARK_FACTS = (("paper", mark_paper), ("glyph", mark_glyph))


def mark_census(admin_css: str, public_css: str, states: list[str]) -> dict[str, tuple[str, str]]:
    """``{fact: (admin value, public value)}`` for every mark both sheets draw.

    Total over ``states`` x :data:`MARK_HOOKS` x :data:`_MARK_FACTS`, and
    ``states`` is :func:`cell_states`' reading of ``solver_state.js`` rather
    than a list kept here (ADR-0039/R2): a fifth cell state arrives in this
    dict as four unclassified facts and reds.

    Takes text so the controls can feed it synthetic sheets, exactly as
    :func:`compared_surface` does.
    """

    def value(read, text: str, hook: str, state: str) -> str:
        found = read(text, hook, state)
        return "; ".join(f"{name}: {found[name]}" for name in sorted(found))

    return {
        f"{hook}.{state}.{fact}": (
            value(read, admin_css, hook, state),
            value(read, public_css, hook, state),
        )
        for hook in MARK_HOOKS
        for state in states
        for fact, read in _MARK_FACTS
    }


#: Which census facts the compared surface already carries, and under which
#: key. Hand-written and then **held to the surface**, so a renamed fact reds
#: here instead of quietly dropping a mark out of coverage.
MARKS_IN_THE_COMPARED_SURFACE = {
    ".player-cell.empty.glyph": "dot.declarations",
    ".player-cell.maybe.glyph": "maybe.cell.glyph.declarations",
    ".player-swatch.maybe.glyph": "maybe.swatch.glyph.declarations",
}


@dataclass(frozen=True)
class RoutedFinding:
    """One censused divergence that is MEASURED and UNDECIDED.

    Not a :class:`Divergence`, and the distinction is the whole point of
    having a second table rather than a fourth entry in the first one:

    * a :class:`Divergence` is a fact **inside** the compared surface that is
      *allowed* to differ, because somebody decided it should;
    * a :class:`RoutedFinding` is a fact **outside** it that *does* differ,
      that nobody has decided, and that this guard pins **as diverging — its
      content is not held**. Do not read the word "pinned" more widely than
      that: see the module docstring's paragraph on what it buys, and
      **CARD-346**, which owes this table the derived residue control
      :data:`RESIDUE_CONTROLS` already gives the other one.

    Nothing is exempted by being routed. The compared surface is exactly as
    wide as it was; the census is what makes its edge visible, and these
    entries are the owner's queue rather than this file's permission.

    * ``reason`` — what differs and why it is the owner's call, not a
      worktree's. Held to :data:`_REASON_FLOOR`, like a declared divergence's.
    * ``measured`` — the figure. "It looks worse" is not a finding; a contrast
      ratio or a count is. Held to carrying a digit.
    """

    reason: str
    measured: str


#: The divergences the census finds that nobody has decided. CARD-339 measured
#: every one of them; it decided none of them, because
#: ``test_public_player_agreement.py``'s own standing rule is that two players
#: disagreeing about a mark is a finding for the owner and deciding which side
#: is right is not a worktree call — the rule CARD-323 followed to produce
#: CARD-339, and the one CARD-339 follows here rather than widening past its
#: own mark.
SIBLING_FINDINGS: dict[str, RoutedFinding] = {
    ".player-cell.maybe.paper": RoutedFinding(
        reason=(
            "The admin's Maybe cell has NO background rule, so it draws the glyph on the "
            "board's paper; this page draws it on --color-surface-hover, the tint that stood "
            "in for the glyph before CARD-339 added one. The owner's decision of 2026-11-03 "
            "was that the public page GAINS the glyph; it said nothing about the tint, and "
            "CARD-339's G-2 forbids that card touching the background either it or CARD-323 "
            "owns. So the tint is measured and left standing, pinned here: a rendered-pixel "
            "question the owner has not been asked is not a worktree call, and declaring it "
            "in DECLARED_DIVERGENCES would be exactly the exemption CARD-339's G-3 names as "
            "the defect arriving one level up."
        ),
        measured=(
            "The tint alone is 1.169:1 against a blank cell (--color-surface-hover #f1ebdd "
            "vs --grid-paper #fffdf8, WCAG 2.1 relative luminance) — invisible, which is the "
            "owner's original finding. Its cost to the mark that IS now drawn: the '?' reads "
            "6.207:1 on this page against 7.258:1 in the admin. Both clear AA's 4.5:1; only "
            "the admin's clears AAA's 7:1."
        ),
    ),
    ".player-swatch.maybe.paper": RoutedFinding(
        reason=(
            "The swatch half of the same undecided tint, and it is CARD-323's one CSS line: "
            "that card matched the swatch to the cell so the brush button would stop "
            "previewing the wrong mark, which is right and stays right. It diverges from the "
            "admin for the same single reason the cell does, so it is routed with the cell "
            "and must be decided with it — resolving one and not the other would make the "
            "button stop previewing the cell, which is the defect CARD-323 closed."
        ),
        measured=(
            "1.018:1 against the Clear swatch (--color-surface-hover #f1ebdd vs "
            "--color-surface-sunken #efe9dc) — the two beige squares the owner could not "
            "tell apart in ~/Documents/nonogram-reviews/CARD-323/. The '?' CARD-339 adds is "
            "now what distinguishes them, at 6.207:1 on the tint."
        ),
    ),
    ".player-swatch.empty.glyph": RoutedFinding(
        reason=(
            "The same defect shape CARD-339 exists to fix, one state over, and found by this "
            "census rather than by a render: the admin's White swatch previews the cell's "
            "dot as an ::after and this page's draws nothing at all, so the brush button "
            "shows a plain square for a mark the board draws a dot for. Deliberately NOT "
            "taken by CARD-339 — its own instruction is not to widen silently past the Maybe "
            "mark, and adding a mark to a button is the same owner-facing decision the Maybe "
            "glyph needed an owner for. Owner: the board owner, via this card's reviewer. "
            "This is the strongest candidate for the follow-up card."
        ),
        measured=(
            "The dot the admin's swatch draws is --color-text-secondary #5c6070 at 28% of "
            "the box, 6.144:1 on the swatch's paper. Without it, this page's White and Clear "
            "swatches are two plain squares 1.19:1 apart (--grid-paper #fffdf8 vs "
            "--color-surface-sunken #efe9dc) — a hair ABOVE the 1.169:1 the owner already "
            "called indistinguishable for the Maybe cell, and in the same indistinguishable "
            "band as it. (The comparative ran backwards in CARD-339's first draft, which "
            "said 'below'. Both figures were right and the word was not; the arm below "
            "checks a `measured` field for a digit and cannot catch a wrong comparative.)"
        ),
    ),
    ".player-swatch.unknown.paper": RoutedFinding(
        reason=(
            "The Clear swatch's own paper: --color-surface-sunken here, --grid-paper in the "
            "admin (which declares no rule for the state, so the swatch's base paper shows). "
            "A deliberate choice on this page, as far as the sheets say — the public swatch "
            "is 1em of button chrome and a sunken square reads as 'erase' beside three "
            "marked ones — but nobody recorded deciding it, and it is half of why the White "
            "and Clear swatches sit as close together as they do. Routed with the finding "
            "above, which it cannot be decided apart from."
        ),
        measured=(
            "1.19:1 between the two sheets' Clear swatches (--color-surface-sunken #efe9dc "
            "vs --grid-paper #fffdf8), and the same 1.19:1 between this page's Clear and "
            "White swatches."
        ),
    ),
    ".player-cell.filled.paper": RoutedFinding(
        reason=(
            "CARD-270's hairline, which the admin has and this page does not: every filled "
            "cell there draws a --player-rule inset box-shadow in --player-thin just inside "
            "its own box, so a run of filled cells crossing a major rule, the frame or a "
            "clue gutter does not merge into one blob where the heavy rule exists to help "
            "the player count (the owner's finding of 2026-10-22). The same board is drawn "
            "here with the same ink, at the same every-fifth major rule, so the same blob is "
            "reachable. Not taken by CARD-339: it is a second owner-facing mark on a second "
            "state, --player-thin is declared in admin.css rather than in the tokens.css "
            "ADR-0041/R3 copies, so the token is not even reachable from this sheet, and the "
            "fix needs the pixel sampling tests/test_puzzle_solver_fifth_rule.py does for "
            "the panel. Owner: the board owner, via this card's reviewer."
        ),
        measured=(
            "One declaration and 1 px: 'box-shadow: inset 0 0 0 var(--player-rule) "
            "var(--player-thin)' in the admin, nothing here. --player-thin is "
            "color-mix(in srgb, var(--grid-ink) 28%, var(--grid-paper)), declared at "
            "admin.css's --player-thin and in no file the public site is served."
        ),
    ),
    ".player-swatch.filled.paper": RoutedFinding(
        reason=(
            "The admin sinks the Black swatch's border into its fill (border-color: "
            "var(--grid-ink)) so the button shows one solid ink square; this page leaves the "
            "base --color-border-strong edge around the ink. Cosmetic, one declaration, and "
            "nobody decided it either way. Routed rather than taken for the same reason as "
            "the rest: CARD-339's brief is the Maybe mark, and a swatch's border is the "
            "owner's eye, not a test's."
        ),
        measured=(
            "One declaration: 'border-color: var(--grid-ink)' present in the admin, absent "
            "here, so the border stays --color-border-strong #7f755f (3.9:1 on surface) "
            "around a --grid-ink #1c2333 fill."
        ),
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
def census(admin_css: str, public_css: str) -> dict[str, tuple[str, str]]:
    return mark_census(admin_css, public_css, cell_states())


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




class TestPlayerLooksAgree_TheMaybeMarkIsTheSameMark:
    """CARD-339 AC-1/AC-2/AC-3 — the "?" is one mark, drawn twice.

    The admin drew it and this page did not, and the reason the divergence
    reached a render is that none of the arms above looked at it. Arm by arm
    for the reason AC-1's class states, and **both sheets searched in every
    one**: half a guard passes half the mutants, which is the defect shape
    this whole file exists to catch.

    AC-1 asks for the glyph "verified against the admin's own declarations,
    derived rather than retyped". That is what these arms are: nothing below
    writes a font-size, an inset or a flex rule down. The two property sets
    and :data:`MAYBE_GLYPH_CONTENT`/:data:`MAYBE_GLYPH_COLOUR` are written
    here, and they are the anti-vacuity floor rather than the comparison —
    :data:`DOT_PROPERTIES`' exact role, for the exact reason: two empty parses
    are equal and mean nothing.
    """

    def test_the_cell_glyph_is_declared_once_in_each_sheet(
        self, admin_css: str, public_css: str
    ) -> None:
        assert rule_count(admin_css, MAYBE_CELL_GLYPH) == 1, "admin.css: not found once"
        assert rule_count(public_css, MAYBE_CELL_GLYPH) == 1, "player.css: not found once"

    def test_the_swatch_glyph_is_declared_once_in_each_sheet(
        self, admin_css: str, public_css: str
    ) -> None:
        assert rule_count(admin_css, MAYBE_SWATCH_GLYPH) == 1, "admin.css: not found once"
        assert rule_count(public_css, MAYBE_SWATCH_GLYPH) == 1, "player.css: not found once"

    def test_the_admin_sheet_declares_the_cell_glyphs_properties(self, admin_css: str) -> None:
        found = declarations(rules(admin_css)[MAYBE_CELL_GLYPH])
        assert set(found) == MAYBE_CELL_GLYPH_PROPERTIES, sorted(found)

    def test_the_public_sheet_declares_the_cell_glyphs_properties(self, public_css: str) -> None:
        found = declarations(rules(public_css)[MAYBE_CELL_GLYPH])
        assert set(found) == MAYBE_CELL_GLYPH_PROPERTIES, sorted(found)

    def test_the_admin_sheet_declares_the_swatch_glyphs_properties(self, admin_css: str) -> None:
        found = declarations(rules(admin_css)[MAYBE_SWATCH_GLYPH])
        assert set(found) == MAYBE_SWATCH_GLYPH_PROPERTIES, sorted(found)

    def test_the_public_sheet_declares_the_swatch_glyphs_properties(self, public_css: str) -> None:
        found = declarations(rules(public_css)[MAYBE_SWATCH_GLYPH])
        assert set(found) == MAYBE_SWATCH_GLYPH_PROPERTIES, sorted(found)

    def test_the_two_cell_glyph_declaration_sets_are_equal(
        self, admin_css: str, public_css: str
    ) -> None:
        """AC-1's claim for the board, and AC-2's public-only plant lands here."""
        assert declarations(rules(admin_css)[MAYBE_CELL_GLYPH]) == declarations(
            rules(public_css)[MAYBE_CELL_GLYPH]
        )

    def test_the_two_swatch_glyph_declaration_sets_are_equal(
        self, admin_css: str, public_css: str
    ) -> None:
        """AC-1's claim for the brush button."""
        assert declarations(rules(admin_css)[MAYBE_SWATCH_GLYPH]) == declarations(
            rules(public_css)[MAYBE_SWATCH_GLYPH]
        )

    def test_the_mark_both_glyphs_draw_is_a_question_mark_in_the_accent_token(
        self, admin_css: str, public_css: str
    ) -> None:
        """Written out independently, so "the same" cannot be "the same wrong".

        Equality alone would stay green if both sheets were changed together
        to draw "!" in the ink token, and AC-1's claim is not that the two
        agree — it is that this page draws *the admin's mark*.
        """
        for label, text in (("admin.css", admin_css), ("player.css", public_css)):
            for selector in (MAYBE_CELL_GLYPH, MAYBE_SWATCH_GLYPH):
                found = declarations(rules(text)[selector])
                assert found["content"] == MAYBE_GLYPH_CONTENT, f"{label} {selector}: {found}"
                assert found["color"] == MAYBE_GLYPH_COLOUR, f"{label} {selector}: {found}"

    def test_the_numeral_floor_the_cell_glyph_reads_agrees_in_both_sheets(
        self, admin_css: str, public_css: str
    ) -> None:
        """The hole the derived declaration would otherwise open.

        The cell glyph's font-size reads ``var(--player-numeral-min)``, and
        that token is declared in each stylesheet rather than in the
        ``tokens.css`` ADR-0041/R3 copies byte-identically. So the two
        font-size declarations can read **equal** while rendering at different
        sizes, which is agreement about the text and not about the mark. Both
        sides are also held to declaring it exactly once: a second declaration
        is a second place the size is decided.
        """
        for label, text in (("admin.css", admin_css), ("player.css", public_css)):
            assert NUMERAL_FLOOR in declarations(rules(text)[MAYBE_CELL_GLYPH])["font-size"], (
                f"{label}: the cell glyph no longer reads {NUMERAL_FLOOR}, so comparing it "
                "measures nothing"
            )
        assert custom_property(admin_css, NUMERAL_FLOOR) == custom_property(
            public_css, NUMERAL_FLOOR
        )

    def test_the_maybe_mark_is_a_fact_this_guard_compares(
        self, surface: dict[str, tuple[str, str]]
    ) -> None:
        """CARD-339's AC-3, as its own named cell.

        The card's measured premise was that this module contained the string
        ``maybe`` zero times. This arm is the statement that it no longer does,
        in the only form that can fail: the two facts are in the surface
        :func:`disagreements` is total over, so from here the mark can only be
        *declared* or *reported*, never overlooked.
        """
        assert "maybe.cell.glyph.declarations" in surface
        assert "maybe.swatch.glyph.declarations" in surface
        assert "numeral-floor.value" in surface
        for key in ("maybe.cell.glyph.declarations", "maybe.swatch.glyph.declarations"):
            assert key not in DECLARED_DIVERGENCES, (
                f"{key} is declared as an allowed divergence. CARD-339's G-3: an exemption "
                "added to make that card green is the defect it exists to fix, one level up."
            )
            admin_value, public_value = surface[key]
            assert admin_value.strip() and public_value.strip(), (key, surface[key])

    #: AC-2's plants, one per (hook, direction). Each is a substitution on the
    #: REAL text of one sheet, the idiom
    #: :meth:`TestPlayerLooksAgree_ADivergenceMustBeDeclared.test_a_fourth_divergence_in_the_compared_surface_is_reported`
    #: already uses, so a control cannot drift away from the file it is about —
    #: and so that an ADMIN-side plant never writes into ``src/`` (CARD-339's
    #: G-1). Both directions, because a guard that read ``player.css`` on both
    #: sides of the comparison would pass every public-only plant.
    MAYBE_PLANTS = {
        "the public cell glyph loses the accent token": (
            "maybe.cell.glyph.declarations",
            _on_public(lambda css: css.replace(
                'text-align: center; color: var(--color-accent); }',
                'text-align: center; color: var(--color-text); }',
            )),
        ),
        "the admin cell glyph is drawn half the size": (
            "maybe.cell.glyph.declarations",
            _on_admin(lambda css: css.replace(
                "calc(var(--player-cell) * 0.6)", "calc(var(--player-cell) * 0.3)"
            )),
        ),
        "the public swatch glyph stops centring the mark": (
            "maybe.swatch.glyph.declarations",
            _on_public(lambda css: css.replace(
                "display: flex; align-items: center; justify-content: center;",
                "display: flex; align-items: start; justify-content: start;",
            )),
        ),
        "the admin swatch glyph draws an exclamation mark": (
            "maybe.swatch.glyph.declarations",
            _on_admin(lambda css: css.replace(
                '.player-swatch[data-state="maybe"]::after { content: "?";',
                '.player-swatch[data-state="maybe"]::after { content: "!";',
            )),
        ),
    }

    @pytest.mark.parametrize("name", sorted(MAYBE_PLANTS))
    def test_a_one_sided_change_to_the_maybe_mark_is_reported(
        self, admin_css: str, public_css: str, name: str
    ) -> None:
        """AC-2: a divergence in either look, planted in either direction, reds.

        Two assertions in order, and the second is the one with teeth: the
        plant must appear as an **undeclared** disagreement, so a plant that
        the exemption table happened to absorb would fail here rather than
        pass as "something reddened".
        """
        key, plant = self.MAYBE_PLANTS[name]
        planted_admin, planted_public = plant(admin_css, public_css)
        assert (planted_admin, planted_public) != (admin_css, public_css), (
            f"the plant {name!r} did not apply — this control measures nothing"
        )
        found = disagreements(
            compared_surface(
                planted_admin, planted_public, wave_settings(ADMIN_JS), wave_settings(PUBLIC_JS)
            )
        )
        assert key in found, {name: sorted(found)}
        assert set(found) - set(DECLARED_DIVERGENCES) == {key}, {
            "the plant was absorbed or reached further than one fact": sorted(
                set(found) - set(DECLARED_DIVERGENCES)
            )
        }

    @pytest.mark.parametrize(
        "selector", [MAYBE_CELL_GLYPH, MAYBE_SWATCH_GLYPH], ids=["cell", "swatch"]
    )
    def test_a_glyph_deleted_from_this_page_is_a_failure_and_not_an_absence(
        self, admin_css: str, public_css: str, selector: str
    ) -> None:
        """The third direction, which equality cannot carry.

        Deleting the rule does not make the two sides *differ* — it makes one
        side unreadable, and "not found" has to be a failure here rather than
        a silent half-measurement. That is :func:`_measured`'s whole job, so
        the plant is asserted to raise with the FACT's name in the message.
        """
        rule_text = rules(public_css)[selector]
        planted = public_css.replace(f"{selector} {{{rule_text}}}", "", 1)
        assert planted != public_css, "the plant did not apply — this control measures nothing"
        with pytest.raises(AssertionError) as broke:
            compared_surface(
                admin_css, planted, wave_settings(ADMIN_JS), wave_settings(PUBLIC_JS)
            )
        assert "maybe" in str(broke.value) and "player.css" in str(broke.value), str(broke.value)


class TestPlayerLooksAgree_TheOtherMarksAreCensusedNotAssumed:
    """CARD-339 item 4 / AC-5 — the other marks are measured, not assumed.

    The compared surface is a list somebody chose, and the Maybe mark is what
    choosing costs. This class is the answer to the SHAPE rather than to that
    instance: every fact of :func:`mark_census` must be compared, agreeing, or
    routed, so the next sibling gap arrives as a red cell with a name instead
    of as a render the owner notices.
    """

    def test_the_census_is_derived_from_the_module_both_players_import(self) -> None:
        """ADR-0039/R2: the set is enumerated, never written down.

        ``solver_state.js`` is the authority — the module ADR-0041/R3 copies
        byte-identically into the public site, so it is the one place the two
        players cannot disagree about what the states ARE. A fifth state added
        there is enumerated rather than left outside; see
        :meth:`test_a_fifth_cell_state_is_enumerated_rather_than_left_outside_the_census`
        for what that does and does not establish.
        """
        states = cell_states()
        assert len(states) >= 4, states
        assert "maybe" in states and "filled" in states, states
        assert sorted(set(states)) == sorted(states), states

    def test_the_census_is_not_vacuous(self, census: dict[str, tuple[str, str]]) -> None:
        """Anti-vacuity: an empty census classifies nothing and would pass."""
        assert len(census) == len(MARK_HOOKS) * len(cell_states()) * 2, sorted(census)
        assert ".player-cell.maybe.glyph" in census
        assert ".player-swatch.empty.glyph" in census
        drawn = [key for key, pair in census.items() if any(pair)]
        assert len(drawn) >= 10, drawn

    def test_every_census_fact_is_compared_routed_or_agreeing(
        self, census: dict[str, tuple[str, str]]
    ) -> None:
        """The claim, and both directions of it in one equality.

        An unclassified divergence is a mark drifting where nothing is looking
        — the defect CARD-339 was raised for, stated here about every mark
        rather than about the one that already happened. A routed finding that
        stops diverging is the stale-exemption shape: somebody fixed it and
        left the queue entry standing.

        **What this arm does NOT establish**, said here because the word
        "routed" invites the wider reading and CARD-339's cycle 1 caught it
        being made: it compares the **classification**, never the value. A
        routed fact whose two sides change — the admin's filled-swatch
        ``border-color`` taking another token, the public Clear swatch
        repainted in ink — still diverges, and this stays green. The derived
        residue that would close that is **CARD-346**.
        """
        compared = set(MARKS_IN_THE_COMPARED_SURFACE)
        diverging = {key for key, pair in census.items() if pair[0] != pair[1]}
        assert diverging & compared == set(), {
            "a fact the compared surface carries is diverging here": sorted(diverging & compared),
            "read": "test_the_disagreements_are_exactly_the_declared_ones first",
        }
        assert diverging == set(SIBLING_FINDINGS), {
            "diverging, and nobody has even been asked": sorted(
                diverging - set(SIBLING_FINDINGS) - compared
            ),
            "routed, but no longer diverging": sorted(set(SIBLING_FINDINGS) - diverging),
            "what each routed finding measured": {
                key: SIBLING_FINDINGS[key].measured
                for key in sorted(set(SIBLING_FINDINGS) - diverging)
            },
        }

    def test_every_compared_mark_names_a_fact_the_surface_really_carries(
        self, census: dict[str, tuple[str, str]], surface: dict[str, tuple[str, str]]
    ) -> None:
        """The shape constraint over the OTHER table, and the CARD-255 lesson.

        A census fact claiming to be covered by a surface key that does not
        exist reads as coverage and is none: exactly what
        ``test_every_declared_divergence_is_a_fact_the_guard_measures`` holds
        :data:`DECLARED_DIVERGENCES` to, applied to the table that claims the
        marks are looked at.
        """
        unknown = sorted(set(MARKS_IN_THE_COMPARED_SURFACE) - set(census))
        assert unknown == [], f"claimed compared, but not a mark the census reads: {unknown}"
        missing = sorted(
            key for key, fact in MARKS_IN_THE_COMPARED_SURFACE.items() if fact not in surface
        )
        assert missing == [], f"claimed compared, but the surface has no such fact: {missing}"

    def test_no_mark_is_both_compared_and_routed(self) -> None:
        """A fact cannot be in the surface and in the owner's queue at once.

        If it were, the queue entry would be the exemption CARD-339's G-3
        forbids, wearing the census's clothes.
        """
        both = sorted(set(MARKS_IN_THE_COMPARED_SURFACE) & set(SIBLING_FINDINGS))
        assert both == [], f"compared AND routed: {both}"

    def test_every_routed_finding_carries_a_reason_and_a_measured_figure(self) -> None:
        """What a routed finding costs, so the queue cannot rot into a note.

        The reason floor is :data:`DECLARED_DIVERGENCES`' own, and the figure
        is what makes it actionable: "it looks worse" is not a finding, a
        contrast ratio or a count is. CARD-339's G-3 asks a declared
        divergence for a reason and a measured residue; this holds the routed
        table to the same two things, so routing is not the cheaper door.

        **Its floor is a digit, and that is all it is.** A figure that is right
        and a sentence that reads it backwards both pass here — which happened
        once, in the `.player-swatch.empty.glyph` entry above, and was caught
        by a reviewer rather than by this arm. Stated rather than left to be
        rediscovered.
        """
        thin = sorted(
            key
            for key, found in SIBLING_FINDINGS.items()
            if len(found.reason.strip()) < _REASON_FLOOR
        )
        assert thin == [], f"a routed finding without a stated reason: {thin}"
        unmeasured = sorted(
            key
            for key, found in SIBLING_FINDINGS.items()
            if not any(char.isdigit() for char in found.measured)
        )
        assert unmeasured == [], f"a routed finding with no figure in it: {unmeasured}"

    def test_the_paper_under_the_maybe_mark_is_a_routed_finding_and_not_an_exemption(
        self, census: dict[str, tuple[str, str]]
    ) -> None:
        """The one CARD-339 measured, decided NOT to decide, and pinned.

        The owner's decision of 2026-11-03 was that the public page gains the
        glyph. It said nothing about the tint under it, and the admin's Maybe
        cell has no background rule at all — so the mark now agrees and the
        paper it sits on does not. This arm is why that is not silent: it reds
        if either sheet changes its Maybe paper, in either direction, and its
        message carries the figure the owner needs.

        It is deliberately **not** a :data:`DECLARED_DIVERGENCES` entry. That
        table means "allowed, for a decided reason", and nobody has decided
        this; an entry there would be the exemption CARD-339's G-3 names as
        the defect it exists to fix, arriving one level up.

        **And this is the ONLY value-pinning in the routed table**, which is
        worth knowing before trusting the word "pinned" elsewhere: the two
        literals below are written out by hand, they cover two of the six
        routed facts, and the other four are held to diverging and nothing
        more. **CARD-346** owes the table a derived residue per entry, the way
        :data:`RESIDUE_CONTROLS` does for :data:`DECLARED_DIVERGENCES`.

        **Narrower still, and read this before trusting "two of the six":** two
        facts are four *sides*, and this arm holds **three** of them. The two
        literals are written for ``.player-cell.maybe.paper`` only, so the
        cell's admin and public sides are both pinned by value. The swatch's
        **public** side is pinned transitively, by the closing
        ``census[cell][1] == census[swatch][1]`` — CARD-323's claim that the
        button previews the cell. Nothing here holds the swatch's **admin**
        side beyond ``census[key][0] != census[key][1]``, i.e. to *diverging
        from this page's*: ``admin.css`` declares no background on its Maybe
        swatch, so that side falls through to ``.player-swatch``'s
        ``--grid-paper``, and planting one there moves the census with this arm
        and the classification arm both green (CARD-339 cycle 2, by plant; the
        counter-plant on the public side reds through the equality above).
        **That fourth side is CARD-346's**, with the rest of the residue.
        """
        for key in (".player-cell.maybe.paper", ".player-swatch.maybe.paper"):
            assert key in SIBLING_FINDINGS, key
            assert census[key][0] != census[key][1], {
                "this finding is closed and the queue entry is stale": key,
                "what it measured": SIBLING_FINDINGS[key].measured,
            }
        assert census[".player-cell.maybe.paper"][0] == "background: var(--grid-paper)", census[
            ".player-cell.maybe.paper"
        ]
        assert (
            census[".player-cell.maybe.paper"][1] == "background: var(--color-surface-hover)"
        ), census[".player-cell.maybe.paper"]
        # The swatch previews the cell, which is CARD-323's claim and still
        # holds: whatever the paper is, it is the SAME paper on both hooks of
        # this page. Decided apart, the button would stop previewing the cell.
        assert census[".player-cell.maybe.paper"][1] == census[".player-swatch.maybe.paper"][1]

    #: The census's own controls: one plant per direction, on the real text.
    CENSUS_PLANTS = {
        "a sibling mark starts diverging (the public cell loses its ink)": (
            _on_public(lambda css: css.replace(
                '.player-cell[data-state="filled"] { background: var(--grid-ink); }',
                '.player-cell[data-state="filled"] { background: var(--color-accent); }',
            )),
            ".player-cell.filled.paper",
        ),
        "a sibling mark starts diverging (the admin\'s Clear swatch is tinted)": (
            _on_admin(lambda css: css.replace(
                '.player-swatch { position: relative;',
                '.player-swatch[data-state="unknown"] { background: var(--color-accent); }\n'
                ".player-swatch { position: relative;",
            )),
            ".player-swatch.unknown.paper",
        ),
    }

    @pytest.mark.parametrize("name", sorted(CENSUS_PLANTS))
    def test_a_change_to_a_sibling_mark_moves_the_census(self, name: str) -> None:
        """The control (ADR-0039/R1) for the census's reading itself.

        A plant on one sheet's real text must change the fact it is aimed at.
        Asserted as a difference from the live census rather than against a
        written-down expectation, so a plant this reading cannot see fails
        here instead of being quietly tolerated — and one direction per sheet,
        because a census computed from one tree twice would pass half of them.
        """
        plant, key = self.CENSUS_PLANTS[name]
        admin_css = ADMIN_CSS.read_text(encoding="utf-8")
        public_css = PUBLIC_CSS.read_text(encoding="utf-8")
        planted_admin, planted_public = plant(admin_css, public_css)
        assert (planted_admin, planted_public) != (admin_css, public_css), (
            f"the plant {name!r} did not apply — this control measures nothing"
        )
        live = mark_census(admin_css, public_css, cell_states())
        planted = mark_census(planted_admin, planted_public, cell_states())
        assert planted[key] != live[key], (name, key, live[key], planted[key])

    def test_a_fifth_cell_state_is_enumerated_rather_than_left_outside_the_census(
        self, admin_css: str, public_css: str
    ) -> None:
        """ADR-0039/R2's totality, and **only** what it really buys.

        The census is total over :func:`cell_states`, so a state added to the
        shared module arrives as four more facts rather than as none, and
        :meth:`test_every_census_fact_is_compared_routed_or_agreeing` is then
        total over those too: if one sheet styles the new state and the other
        does not, they diverge and red as undeclared.

        **What this does NOT establish, said here rather than left implied:**
        a state *neither* sheet styles agrees, because both papers fall
        through to the hook's base rule — and that is the right answer, not a
        hole. ``unknown`` is exactly that case in the admin today. So the
        claim is totality over the enumeration, never "an unstyled state is a
        defect", and this arm measures the first.
        """
        states = cell_states() + ["pencilled"]
        planted = mark_census(admin_css, public_css, states)
        assert len(planted) == len(MARK_HOOKS) * len(states) * 2, sorted(planted)
        assert ".player-cell.pencilled.paper" in planted
        # It is unreadable on BOTH sides rather than merely absent, which is
        # what keeps "nobody styled it" from reading as agreement: an
        # unclassified state's paper carries the UNREADABLE marker.
        for hook in MARK_HOOKS:
            admin_value, public_value = planted[f"{hook}.pencilled.paper"]
            assert admin_value == public_value, (hook, admin_value, public_value)
            assert UNREADABLE not in admin_value, (
                "the hook's base rule stopped painting, which is a real failure and not "
                "this control's subject"
            )



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
        assert len(surface) >= 15, sorted(surface)
        assert "dot.declarations" in surface
        assert f"keyframes.{FLASH}" in surface
        assert "sweep.animation.step" in surface
        assert "wave.expression" in surface
        # CARD-339. Named here as well as in their own class, because THIS is
        # the arm that says what the surface is, and the Maybe mark's absence
        # from it is the defect that card was raised for: a floor that did not
        # name the mark would let it fall back out of the surface in silence.
        assert "maybe.cell.glyph.declarations" in surface
        assert "maybe.swatch.glyph.declarations" in surface
        assert "numeral-floor.value" in surface

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
