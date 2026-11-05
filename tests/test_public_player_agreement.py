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
reading). The classification is held in both directions — a sixth fact that
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

CARD-348's check refs, by node id
---------------------------------
Same discipline, same reason: the validator resolves a check ref by a TEXT
search for the whole ``path::name`` string, so each is written on one line.

* AC-1 — ``tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheWhiteBrushPreviewsTheDot::test_the_two_swatch_dot_declaration_sets_are_equal``
* AC-2 — ``tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheWhiteBrushPreviewsTheDot::test_a_one_sided_change_to_the_swatch_dot_is_reported``
* AC-2 — ``tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheWhiteBrushPreviewsTheDot::test_a_swatch_dot_deleted_from_this_page_is_a_failure_and_not_an_absence``
* AC-3 — ``tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheOtherMarksAreCensusedNotAssumed::test_every_census_fact_is_compared_routed_or_agreeing``
* AC-3 — ``tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheWhiteBrushPreviewsTheDot::test_the_white_mark_is_a_fact_this_guard_compares``
* AC-4 — ``tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheWhiteBrushPreviewsTheDot::test_the_four_brush_buttons_are_mutually_distinguishable``

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
#: The design tokens both sheets name their colours by. ADR-0041/R3 copies
#: this file byte-identically into the public site too, so it is the one place
#: the two players cannot disagree about what a token IS. Read from ``src/``
#: for :data:`STATE_MODULE`'s reason: the admin's is the original, and the
#: copy's equality to it is ``player/assemble.py``'s claim, asserted elsewhere.
#: Read for ONE thing: CARD-348 AC-4's contrast figures, which have to be
#: recomputable from this file rather than copied off a card.
TOKENS_CSS = _REPO / "src" / "nonogram" / "admin" / "static" / "tokens.css"


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

#: The White mark's dot on the brush button — the fact CARD-348 moved OUT of
#: :data:`SIBLING_FINDINGS` and into this surface. The admin has previewed the
#: cell's dot on its White swatch since the panel player shipped and this page
#: drew nothing there, so the brush button showed a plain square for the mark
#: the board draws a dot for: CARD-339's defect, one state over, found by that
#: card's census rather than by a render. Both sheets spell the selector
#: identically, so like :data:`DOT` it is a lookup key and not a compared fact.
EMPTY_SWATCH_GLYPH = '.player-swatch[data-state="empty"]::after'

#: The anti-vacuity floor for the swatch dot, written here independently of
#: either sheet — :data:`DOT_PROPERTIES`' discipline applied to the mark
#: CARD-348 adds, and for its reason: declaration-set equality is vacuously
#: true when both parses come back empty.
#:
#: It differs from :data:`DOT_PROPERTIES` **by design and not by drift**, the
#: way the two Maybe property sets differ from each other: a board cell sizes
#: its own dot as a block, and 1em of button chrome cannot, so the swatch's is
#: an absolutely positioned box centred by ``margin: auto`` inside ``inset: 0``.
#: The admin declares it that way, so each set is compared against *the same
#: hook in the other sheet* and never across hooks.
EMPTY_SWATCH_GLYPH_PROPERTIES = frozenset(
    {
        "content",
        "position",
        "inset",
        "width",
        "height",
        "margin",
        "border-radius",
        "background",
    }
)

#: What the White mark *is*, written out independently of either sheet, for
#: :data:`MAYBE_GLYPH_CONTENT`'s reason: equality alone stays green if both
#: sheets are changed together, and AC-1's claim is not "the two agree" — it is
#: that this page draws **the admin's** mark. A round dot, 28% of its box, in
#: the secondary ink.
EMPTY_GLYPH_CONTENT = '""'
EMPTY_GLYPH_INK = "var(--color-text-secondary)"
EMPTY_GLYPH_EXTENT = "28%"
EMPTY_GLYPH_RADIUS = "50%"

#: The brush button itself. Both swatch marks are ``position: absolute;
#: inset: 0``, so this box has to be the containing block they resolve
#: against; CARD-339 gave it ``position: relative`` for the "?" and CARD-348
#: re-declares nothing (its G-2). "Already there" is a premise, though, and
#: :meth:`TestPlayerLooksAgree_TheWhiteBrushPreviewsTheDot.test_the_swatch_is_the_containing_block_both_marks_resolve_against`
#: is where it can fail.
SWATCH = ".player-swatch"

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
        # CARD-348. The White mark on the brush button — the census fact that
        # was ROUTED until this card, because the admin previewed the cell's
        # dot there and this page drew nothing. Read exactly as the two above
        # are: by the selector both sheets spell the same way, into a
        # declaration set, with a property-set floor under each side.
        "empty.swatch.glyph.declarations": (
            rule("empty.swatch.glyph.declarations", EMPTY_SWATCH_GLYPH, "admin.css", admin_css),
            rule("empty.swatch.glyph.declarations", EMPTY_SWATCH_GLYPH, "player.css", public_css),
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
    divergence CARD-339 was raised for, and it was still true of the White
    swatch until **CARD-348** closed it. That fact is now COMPARED
    (:data:`MARKS_IN_THE_COMPARED_SURFACE`) rather than routed, so ``{}`` on
    either side of it reds here instead of sitting in the owner's queue.
    """
    return _cascade(text, f'{hook}[data-state="{state}"]::after')


#: The two hooks a mark is drawn on: a board cell, and the brush button's
#: preview of it. Both sheets use these two class names and no others, which is
#: what makes the public swatch a preview of the public cell at all. The
#: second is :data:`SWATCH`, named rather than spelled twice: CARD-348 needed
#: the same hook for the brush button's containing block, and two literals for
#: one hook is the drift this module exists to catch, one level down.
MARK_HOOKS = (".player-cell", SWATCH)

#: What is read for each (hook, state): the paper under the mark and the glyph
#: on it. Two facts, because they fail independently — the Maybe mark's glyph
#: was missing while its paper was merely different, and the White swatch was
#: the reverse of that (its glyph missing while its paper already agreed, which
#: is what CARD-348 fixed).
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
    # CARD-348 moved this one here out of SIBLING_FINDINGS. Removing a routed
    # entry is as load-bearing as adding one: the census asserts
    # `diverging == set(SIBLING_FINDINGS)`, so leaving it routed after the two
    # sides agreed would red as a stale entry, and leaving it out of BOTH
    # tables would red as unclassified.
    ".player-swatch.empty.glyph": "empty.swatch.glyph.declarations",
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


# ==========================================================================
# CARD-348 — the White brush previews the dot it paints
#
# The reading, the figures, and the arms. Everything below is DERIVED: the
# declarations from the two sheets, the colours from :data:`TOKENS_CSS`, the
# states from ``solver_state.js``. The only values written out here are the
# anti-vacuity floors, for :data:`DOT_PROPERTIES`' stated reason.
# ==========================================================================

#: ``var(--token)`` on its own — a bare reference, with no fallback. A value
#: that is anything else (a literal, a ``color-mix``, a reference with a
#: fallback) is returned unresolved, which is what makes an unresolvable
#: colour visible as itself instead of as a silent zero.
_VAR_REFERENCE = re.compile(r"^var\(\s*(--[A-Za-z0-9_-]+)\s*\)$")

#: ``--token: #rrggbb;`` in ``tokens.css``.
_TOKEN_HEX = re.compile(r"--([A-Za-z0-9_-]+)\s*:\s*(#[0-9a-fA-F]{6})\s*;")


def token_colours(text: str) -> dict[str, str]:
    """``{--token: #rrggbb}`` for every flat colour ``text`` declares.

    Flat on purpose: a token defined by ``color-mix`` is not a hex and is not
    pretended to be one. :func:`swatch_look` leaves such a value unresolved
    and the arms that read it say so rather than measuring zero.
    """
    return {f"--{name}": value.lower() for name, value in _TOKEN_HEX.findall(_css_code(text))}


def _resolved(value: str, colours: dict[str, str]) -> str:
    """``value`` as a hex when it is a bare token reference, else unchanged."""
    match = _VAR_REFERENCE.match(_squeezed(value))
    return colours.get(match.group(1), value) if match else value


def _channel(value: float) -> float:
    return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4


def relative_luminance(colour: str) -> float:
    """WCAG 2.1 relative luminance of ``#rrggbb``.

    Written from the specification rather than imported: no colour library is
    in the dependency baseline (stdlib + Pillow + NumPy), and a second
    implementation is this repo's standing preference anyway. Every contrast
    figure this card and CARD-339 recorded was derived this way, so they have
    to be reproducible from here and not only from a card's prose.
    """
    digits = colour.lstrip("#")
    assert len(digits) == 6, f"not a #rrggbb colour: {colour!r}"
    red, green, blue = (int(digits[at : at + 2], 16) / 255 for at in (0, 2, 4))
    return 0.2126 * _channel(red) + 0.7152 * _channel(green) + 0.0722 * _channel(blue)


def contrast_ratio(one: str, other: str) -> float:
    """WCAG 2.1 contrast ratio between two ``#rrggbb`` colours."""
    first, second = relative_luminance(one), relative_luminance(other)
    return (max(first, second) + 0.05) / (min(first, second) + 0.05)


def swatch_look(css: str, colours: dict[str, str], state: str) -> dict[str, str]:
    """What ``css`` makes the brush button for ``state`` look like.

    ``paper`` is the swatch's own background resolved against the hook's base
    rule — :func:`mark_paper`'s rule, for its reason — and ``mark`` is the
    whole normalised ``::after``, or ``"(nothing drawn)"`` when there is no
    such rule. ``ink`` is what the mark is drawn IN: a dot's own
    ``background``, since the dot's box *is* the mark, or a glyph's ``color``.
    """
    own = _cascade(css, f'{SWATCH}[data-state="{state}"]')
    base = _cascade(css, SWATCH)
    paper = own.get("background") or base.get("background", "")
    glyph = _cascade(css, f'{SWATCH}[data-state="{state}"]::after')
    ink = glyph.get("background") or glyph.get("color", "")
    return {
        "paper": _resolved(paper, colours),
        "paper token": _squeezed(paper) or "(no rule paints it)",
        "mark": "; ".join(f"{name}: {glyph[name]}" for name in sorted(glyph))
        or "(nothing drawn)",
        "ink": _resolved(ink, colours),
    }


def _exactly_once(css: str, old: str, new: str) -> str:
    """``css`` with ``old`` replaced by ``new``, asserting it occurred once.

    The discipline every plant in this file follows, made a function because
    the swatch dot and the cell dot share seven of their eight declarations:
    an anchor that is *nearly* unique would plant into the wrong rule and the
    arm would still see "something reddened".
    """
    found = css.count(old)
    assert found == 1, f"the plant's anchor occurs {found} times, not once: {old!r}"
    return css.replace(old, new, 1)


#: AC-4's floor, and it is WCAG 2.1's own: 1.4.11 Non-text Contrast asks 3:1
#: of a graphical object a user has to perceive. A brush swatch is exactly
#: that — it is not text, and the player has to tell four of them apart.
GRAPHICAL_CONTRAST_FLOOR = 3.0


class TestPlayerLooksAgree_TheWhiteBrushPreviewsTheDot:
    """CARD-348 AC-1/AC-2/AC-4 — the White button shows the mark it paints.

    The same shape as :class:`TestPlayerLooksAgree_TheMaybeMarkIsTheSameMark`
    and for the same reasons: one arm per claim, both sheets searched in every
    one, and **nothing below retypes a declaration**. AC-1 asks for the dot
    "derived from the admin's declarations rather than retyped"; what makes
    that true is that the comparison's expected value IS the admin's parse.
    :data:`EMPTY_SWATCH_GLYPH_PROPERTIES` and the four
    ``EMPTY_GLYPH_*`` constants are the anti-vacuity floor, not the
    comparison — :data:`DOT_PROPERTIES`' exact role.
    """

    def test_the_swatch_dot_is_declared_once_in_each_sheet(
        self, admin_css: str, public_css: str
    ) -> None:
        """Both sheets are searched. Half a guard passes half the mutants."""
        assert rule_count(admin_css, EMPTY_SWATCH_GLYPH) == 1, "admin.css: not found once"
        assert rule_count(public_css, EMPTY_SWATCH_GLYPH) == 1, "player.css: not found once"

    def test_the_admin_sheet_declares_the_swatch_dots_properties(self, admin_css: str) -> None:
        found = declarations(rules(admin_css)[EMPTY_SWATCH_GLYPH])
        assert set(found) == EMPTY_SWATCH_GLYPH_PROPERTIES, sorted(found)

    def test_the_public_sheet_declares_the_swatch_dots_properties(self, public_css: str) -> None:
        found = declarations(rules(public_css)[EMPTY_SWATCH_GLYPH])
        assert set(found) == EMPTY_SWATCH_GLYPH_PROPERTIES, sorted(found)

    def test_the_two_swatch_dot_declaration_sets_are_equal(
        self, admin_css: str, public_css: str
    ) -> None:
        """AC-1's claim. Both of AC-2's plants land here as well as in the guard."""
        assert declarations(rules(admin_css)[EMPTY_SWATCH_GLYPH]) == declarations(
            rules(public_css)[EMPTY_SWATCH_GLYPH]
        )

    def test_the_mark_both_swatches_draw_is_a_round_dot_in_the_secondary_ink(
        self, admin_css: str, public_css: str
    ) -> None:
        """Written out independently, so "the same" cannot be "the same wrong".

        Equality alone stays green if both sheets are changed together to draw
        a square in the accent token, and AC-1's claim is not that the two
        agree — it is that this page draws *the admin's* mark.
        """
        for label, text in (("admin.css", admin_css), ("player.css", public_css)):
            found = declarations(rules(text)[EMPTY_SWATCH_GLYPH])
            assert found["content"] == EMPTY_GLYPH_CONTENT, f"{label}: {found}"
            assert found["background"] == EMPTY_GLYPH_INK, f"{label}: {found}"
            assert found["border-radius"] == EMPTY_GLYPH_RADIUS, f"{label}: {found}"
            assert found["width"] == found["height"] == EMPTY_GLYPH_EXTENT, f"{label}: {found}"

    def test_the_swatch_is_the_containing_block_both_marks_resolve_against(
        self, admin_css: str, public_css: str
    ) -> None:
        """Item 3 of the card — already true, and now held where it can fail.

        Both swatch marks are ``position: absolute; inset: 0``, so they
        resolve against the nearest positioned ancestor. ``player.css``'s
        ``.player-swatch`` already carries ``position: relative`` — CARD-339
        added it for the "?" — so this card re-declares nothing (its G-2).
        But "already there" is a premise this card leans on, and a premise
        belongs where it can fail: drop that one declaration and both marks
        land in the page's top-left corner while **every** declaration-set
        equality in this class stays green, because the two sheets would still
        agree about the ``::after`` itself.
        """
        for label, text in (("admin.css", admin_css), ("player.css", public_css)):
            base = _cascade(text, SWATCH)
            assert base.get("position") == "relative", (
                f"{label}: {SWATCH} is not a containing block (position is "
                f"{base.get('position')!r}), so its absolutely positioned marks resolve "
                "against the initial containing block and leave the button"
            )
            for selector in (EMPTY_SWATCH_GLYPH, MAYBE_SWATCH_GLYPH):
                found = declarations(rules(text)[selector])
                assert found["position"] == "absolute", (label, selector, found)
                assert found["inset"] == "0", (label, selector, found)

    def test_the_brush_button_previews_the_mark_the_board_draws(self, public_css: str) -> None:
        """The defect in one sentence: the button must show the mark it paints.

        Not the comparison against the admin — that is AC-1 above — but the
        claim *within this page*, which is what CARD-323 established for the
        Maybe swatch and what a brush button is for: the White swatch and the
        White cell draw the same round mark in the same ink. Only the mark is
        compared, because the placement legitimately differs (a board cell
        sizes its own block; 1em of button chrome needs an absolute box).
        """
        cell = declarations(rules(public_css)[DOT])
        swatch = declarations(rules(public_css)[EMPTY_SWATCH_GLYPH])
        shared = ("content", "width", "height", "margin", "border-radius", "background")
        assert {name: cell[name] for name in shared} == {
            name: swatch[name] for name in shared
        }, {"the cell draws": cell, "the button previews": swatch}
        # And the placement really is the only difference, so "only the mark is
        # compared" is a statement about these two rules and not a hedge.
        assert set(cell) - set(swatch) == {"display"}, (sorted(cell), sorted(swatch))
        assert set(swatch) - set(cell) == {"position", "inset"}, (sorted(cell), sorted(swatch))

    def test_the_white_mark_is_a_fact_this_guard_compares(
        self, surface: dict[str, tuple[str, str]], census: dict[str, tuple[str, str]]
    ) -> None:
        """AC-3 — the fact moved from routed to compared, and the move is total.

        Four statements, because each fails for a different reason: the fact
        is in the surface :func:`disagreements` is total over; it is **not**
        exempted there (AC-5 — ``DECLARED_DIVERGENCES`` gains nothing); it is
        **not** still in the owner's queue; and the census now sees the two
        sides agreeing. Neither parse is empty, which is what keeps the third
        from being vacuous.
        """
        key = "empty.swatch.glyph.declarations"
        assert key in surface, sorted(surface)
        assert key not in DECLARED_DIVERGENCES, (
            f"{key} is declared as an allowed divergence. CARD-348's G-3: an exemption "
            "added to make this card green is the defect it exists to fix, one level up."
        )
        admin_value, public_value = surface[key]
        assert admin_value.strip() and public_value.strip(), (key, surface[key])
        assert ".player-swatch.empty.glyph" not in SIBLING_FINDINGS, (
            "the finding is closed and the queue entry is stale — see "
            "test_every_census_fact_is_compared_routed_or_agreeing, which reds on it"
        )
        assert MARKS_IN_THE_COMPARED_SURFACE[".player-swatch.empty.glyph"] == key
        assert census[".player-swatch.empty.glyph"][0] == census[".player-swatch.empty.glyph"][1]

    #: AC-2's two plants, one per direction, each a substitution on the REAL
    #: text of one sheet — :data:`TestPlayerLooksAgree_TheMaybeMarkIsTheSameMark.MAYBE_PLANTS`'
    #: idiom, so a control cannot drift away from the file it is about, and so
    #: that the admin-side plant never writes into ``src/`` (G-1).
    #:
    #: Both anchors carry ``inset: 0; width: 28%``, which is the swatch dot's
    #: and **not** the cell dot's: the two rules share seven of eight
    #: declarations, so a shorter anchor would plant into the board's mark and
    #: red the wrong fact. :func:`_exactly_once` is what says so out loud.
    WHITE_PLANTS = {
        "the public swatch dot is drawn in the board's ink": (
            "empty.swatch.glyph.declarations",
            _on_public(lambda css: _exactly_once(
                css,
                "inset: 0; width: 28%; height: 28%; margin: auto; border-radius: 50%; "
                "background: var(--color-text-secondary);",
                "inset: 0; width: 28%; height: 28%; margin: auto; border-radius: 50%; "
                "background: var(--grid-ink);",
            )),
        ),
        "the admin swatch dot is drawn as a square": (
            "empty.swatch.glyph.declarations",
            _on_admin(lambda css: _exactly_once(
                css,
                "inset: 0; width: 28%; height: 28%; margin: auto; border-radius: 50%;",
                "inset: 0; width: 28%; height: 28%; margin: auto; border-radius: 0;",
            )),
        ),
    }

    @pytest.mark.parametrize("name", sorted(WHITE_PLANTS))
    def test_a_one_sided_change_to_the_swatch_dot_is_reported(
        self, admin_css: str, public_css: str, name: str
    ) -> None:
        """AC-2: a divergence in the swatch dot, planted either way, reds.

        Two assertions in order, and the second is the one with teeth: the
        plant must appear as an **undeclared** disagreement, so a plant the
        exemption table absorbed fails here rather than passing as "something
        reddened".
        """
        key, plant = self.WHITE_PLANTS[name]
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

    def test_a_swatch_dot_deleted_from_this_page_is_a_failure_and_not_an_absence(
        self, admin_css: str, public_css: str
    ) -> None:
        """The third direction, which equality cannot carry.

        Deleting the rule does not make the two sides *differ* — it makes one
        side unreadable, and "not found" has to be a failure rather than a
        silent half-measurement. That is :func:`_measured`'s job, so the plant
        is asserted to raise with the FACT's name in the message. It is also
        the exact state this page was in before this card, which is why the
        arm is worth having: back then nothing raised, because the fact was
        not in the surface at all.
        """
        rule_text = rules(public_css)[EMPTY_SWATCH_GLYPH]
        planted = _exactly_once(
            public_css, f"{EMPTY_SWATCH_GLYPH} {{{rule_text}}}", ""
        )
        with pytest.raises(AssertionError) as broke:
            compared_surface(
                admin_css, planted, wave_settings(ADMIN_JS), wave_settings(PUBLIC_JS)
            )
        assert "empty.swatch.glyph" in str(broke.value), str(broke.value)
        assert "player.css" in str(broke.value), str(broke.value)

    def test_the_four_brush_buttons_are_mutually_distinguishable(
        self, public_css: str
    ) -> None:
        """AC-4 — measured from the tokens, pair by pair, and recorded.

        The figures are the deliverable, so they are **computed** here from
        :data:`TOKENS_CSS` through this module's own WCAG 2.1 reading, over
        the states ``solver_state.js`` declares. ``measured`` carries the whole
        table into every failure message, which is what "recorded, not
        asserted" means in a test: the numbers survive the run either way.

        The claim is narrow and it is this card's: **three of the six pairs
        are separated by paper alone and three are not**, so the other three
        are separated by their MARKS. Before this card the White/Clear pair
        was separated by neither — 1.190:1 of paper and no mark on either —
        which is the defect. A pair separated by neither reds here.
        """
        colours = token_colours(TOKENS_CSS.read_text(encoding="utf-8"))
        looks = {state: swatch_look(public_css, colours, state) for state in cell_states()}
        measured = {
            "each swatch": looks,
            "paper vs paper": {},
            "mark on its own paper": {},
        }
        for state, look in looks.items():
            if look["mark"] != "(nothing drawn)":
                measured["mark on its own paper"][state] = round(
                    contrast_ratio(look["ink"], look["paper"]), 3
                )
        pairs = [
            (one, other)
            for index, one in enumerate(looks)
            for other in list(looks)[index + 1 :]
        ]
        for one, other in pairs:
            measured["paper vs paper"][f"{one} vs {other}"] = round(
                contrast_ratio(looks[one]["paper"], looks[other]["paper"]), 3
            )

        # Anti-vacuity: four states, four papers that really resolved to a hex.
        assert len(looks) >= 4, measured
        for state, look in looks.items():
            assert look["paper"].startswith("#"), (state, measured)

        for one, other in pairs:
            by_paper = measured["paper vs paper"][f"{one} vs {other}"]
            by_mark = looks[one]["mark"] != looks[other]["mark"]
            assert by_paper >= GRAPHICAL_CONTRAST_FLOOR or by_mark, {
                "two brush buttons a player cannot tell apart": f"{one} vs {other}",
                "measured": measured,
            }
        for state, ratio in measured["mark on its own paper"].items():
            assert ratio >= GRAPHICAL_CONTRAST_FLOOR, {
                "a mark that cannot be seen on the swatch it is drawn on": state,
                "measured": measured,
            }
        # And the half that is this card's reason to exist, stated so it can
        # fail: at least one pair is distinguished by a mark and not by paper.
        on_marks_alone = [
            f"{one} vs {other}"
            for one, other in pairs
            if measured["paper vs paper"][f"{one} vs {other}"] < GRAPHICAL_CONTRAST_FLOOR
        ]
        assert on_marks_alone, measured
        for pair in on_marks_alone:
            one, other = pair.split(" vs ")
            assert looks[one]["mark"] != looks[other]["mark"], {
                "separated by neither paper nor mark": pair,
                "measured": measured,
            }


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
        once, in the `.player-swatch.empty.glyph` entry (removed by CARD-348,
        which closed that finding), and was caught by a reviewer rather than by
        this arm. Stated rather than left to be rediscovered.
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
        literals below are written out by hand, they cover two of the five
        routed facts, and the other three are held to diverging and nothing
        more. **CARD-346** owes the table a derived residue per entry, the way
        :data:`RESIDUE_CONTROLS` does for :data:`DECLARED_DIVERGENCES`.

        **Narrower still, and read this before trusting "two of the five":** two
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

        **Anchored on the dot rule itself, and it had to be** (CARD-348). This
        plant used to read ``public_css.replace("width: 28%;", …, 1)`` — the
        FIRST ``width: 28%`` in the sheet. That was the board dot's only while
        the board dot was the only 28% mark in the file; CARD-348 added the
        White swatch's dot, which is the same mark in a smaller box and sits
        **earlier** in the sheet, so the plant silently moved to the swatch and
        this arm reported ``empty.swatch.glyph.declarations`` instead of
        ``dot.declarations``. It failed loudly, which is the control working —
        but a nearly-unique anchor is a hazard whatever it does this run, so
        the anchor is now the rule's own body, which :func:`rules` resolves by
        selector and :func:`_exactly_once` holds to one occurrence.
        """
        rule_text = rules(public_css)[DOT]
        planted = _exactly_once(
            public_css, rule_text, rule_text.replace("width: 28%", "width: 31%", 1)
        )
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


# ==========================================================================
# CARD-325 AC-6 — the crosshair makes the same decisions
# ==========================================================================
#
# The crosshair is the first look in this file that is BEHAVIOUR rather than a
# rule in a sheet: ``wireCrosshair`` in ``solver.js`` and the public page's own
# ``wireCrosshair`` in ``play.js`` are two implementations of CARD-267's four
# recorded decisions, and nothing but this class says they still agree. It
# joins this file (CARD-328's one home for the pattern) and does NOT start a
# parallel guard: same shape, same discipline — every compared fact is DERIVED
# from the two sources, the facts that disagree are computed and asserted equal
# to a table of DECLARED divergences with a reason each, and a stale
# declaration is as much a defect as an undeclared divergence.
#
# The facts are read from the sources' TEXT, as everything else here is. That
# is a statement about what is held: the *wiring* (which events move or clear
# the crosshair, what survives a leave, what is marked), not the pixels.
# tests/test_public_player_crosshair.py holds the behaviour in a real browser.

_CROSSHAIR_ADMIN_JS = ADMIN_JS
_CROSSHAIR_PUBLIC_JS = PUBLIC_JS


def _crosshair_source(js_path: Path) -> tuple[str, str]:
    """``(wireCrosshair's text, crossedParts's text)`` from ``js_path``,
    comments gone and strings KEPT (an event name is a string)."""
    from tests.test_public_player_crosshair import _raw_definition

    source = js_path.read_text(encoding="utf-8")
    wire = _raw_definition(source, "wireCrosshair")
    parts = _raw_definition(source, "crossedParts")
    assert wire is not None and parts is not None, f"{js_path.name} lacks a crosshair"
    return wire, parts


def _balanced(text: str, open_at: int) -> int:
    depth = 0
    for index in range(open_at, len(text)):
        depth += {"{": 1, "}": -1}.get(text[index], 0)
        if depth == 0:
            return index
    raise AssertionError("unbalanced braces")


def _local_function(text: str, name: str) -> str | None:
    """A function or arrow ``name`` declared INSIDE ``text`` (any indent), whole.

    An arrow with an expression body ends at its ``;``; one with a block body
    at its closing brace. A ``const`` that is not an arrow is not a function.
    """
    declared = re.search(rf"\bfunction\s+{name}\s*\(", text)
    if declared is not None:
        open_at = text.index("{", declared.end())
        return text[declared.start() : _balanced(text, open_at) + 1]
    declared = re.search(rf"\bconst\s+{name}\s*=", text)
    if declared is None:
        return None
    head = re.match(r"\s*(?:\([^()]*\)|[A-Za-z_$][\w$]*)\s*=>\s*", text[declared.end() :])
    if head is None:
        return None
    body_at = declared.end() + head.end()
    if text[body_at] == "{":
        return text[declared.start() : _balanced(text, body_at) + 1]
    return text[declared.start() : text.index(";", body_at) + 1]


def _handlers(wire: str) -> dict[str, str]:
    """``{event: handler text}`` for every ``addEventListener("event", …)``.

    A handler is an identifier (looked up among the function's own locals) or
    an inline arrow. The same event registered twice is an error here: the
    facts below would silently read one of them.
    """
    found: dict[str, str] = {}
    for m in re.finditer(r"\.addEventListener\(\s*\"(\w+)\"\s*,\s*", wire):
        rest = wire[m.end() :]
        if rest.startswith("("):
            open_at = rest.index("{")
            depth = 0
            for index in range(open_at, len(rest)):
                depth += {"{": 1, "}": -1}.get(rest[index], 0)
                if depth == 0:
                    body = rest[: index + 1]
                    break
        else:
            name = re.match(r"([A-Za-z_$][\w$]*)", rest)
            assert name is not None, rest[:40]
            body = _local_function(wire, name.group(1)) or ""
        assert m.group(1) not in found, f"{m.group(1)} registered twice"
        found[m.group(1)] = body
    return found


def _reaches(wire: str, body: str, target: str, depth: int = 4) -> bool:
    """Whether ``body`` calls ``target(`` directly or through a local function."""
    if re.search(rf"\b{target}\s*\(", body):
        return True
    if depth == 0:
        return False
    for called in set(re.findall(r"\b([A-Za-z_$][\w$]*)\s*\(", body)):
        local = _local_function(wire, called)
        if local is not None and local != body and _reaches(wire, local, target, depth - 1):
            return True
    return False


def _mentions(wire: str, body: str, word: str, depth: int = 4) -> bool:
    if re.search(rf"\b{word}\b", body):
        return True
    if depth == 0:
        return False
    for called in set(re.findall(r"\b([A-Za-z_$][\w$]*)\s*\(", body)):
        local = _local_function(wire, called)
        if local is not None and local != body and _mentions(wire, local, word, depth - 1):
            return True
    return False


def crosshair_facts(wire: str, parts: str) -> dict[str, str]:
    """Every compared fact of one implementation's crosshair, as a string."""
    handlers = _handlers(wire)
    moves = sorted(e for e, h in handlers.items() if _reaches(wire, h, "moveTo"))
    clears = sorted(e for e, h in handlers.items() if _reaches(wire, h, "clear"))
    leave = handlers.get("pointerleave", "")
    survivors = sorted(re.findall(r"pointerType\s*===\s*\"(\w+)\"\s*\)\s*return", leave))
    mover = next(
        (_local_function(wire, n) for n in re.findall(r"\b([A-Za-z_$][\w$]*)\s*\(", wire)
         if (_local_function(wire, n) or "").count("moveTo(") and "cellUnder" in (_local_function(wire, n) or "")),
        "",
    )
    toggles = sorted(set(re.findall(r"classList\.toggle\(\s*\"([^\"]+)\"", wire)))
    selectors = sorted(set(re.findall(r"`([^`]*)`", parts)))
    return {
        "events.listened": ",".join(sorted(handlers)),
        "events.that_move_the_crosshair": ",".join(moves),
        "events.that_clear_the_crosshair": ",".join(clears),
        "leave.survivors": ",".join(survivors),
        "pointer_type.is_read_in": ",".join(sorted(e for e, h in handlers.items() if _mentions(wire, h, "pointerType"))),
        "a_non_cell_hit.moves_nothing": str(bool(re.search(r"!==\s*null\s*\)\s*moveTo\(", mover))),
        "marker.class": ",".join(toggles),
        "marked.selectors": " | ".join(selectors),
        "event.is_prevented": str("preventDefault" in wire),
        "event.is_stopped": str("stopPropagation" in wire or "stopImmediatePropagation" in wire),
        "position.is_forgotten_on_redraw": str("forget" in wire),
        "already_there.needs_the_cross_painted": str(bool(re.search(r"isAt\([^)]*\)\s*&&\s*is[A-Z]\w*\(", wire))),
    }


def crosshair_disagreements(admin_js: str, public_js: str) -> dict[str, tuple[str, str]]:
    """The facts on which the two crosshairs differ: ``{fact: (admin, public)}``."""
    from tests.test_public_player_crosshair import _raw_definition

    def facts(source: str) -> dict[str, str]:
        wire = _raw_definition(source, "wireCrosshair")
        parts = _raw_definition(source, "crossedParts")
        assert wire is not None and parts is not None
        return crosshair_facts(wire, parts)

    admin, public = facts(admin_js), facts(public_js)
    assert admin.keys() == public.keys()
    return {k: (admin[k], public[k]) for k in admin if admin[k] != public[k]}


#: What the public crosshair does DIFFERENTLY from the admin's, each with the
#: decision it rests on. Five entries in two groups, and only the first group is
#: about zoom: the first three (``events.listened``, ``events.that_clear_the_crosshair``,
#: ``pointer_type.is_read_in``) exist because the public page has a pinch the
#: crosshair had to be told about (CARD-324, AC-7); the last two
#: (``position.is_forgotten_on_redraw`` and ``already_there.needs_the_cross_painted``)
#: are one decision seen twice, CARD-267's fourth, because this page draws its
#: table once and has no redraw to forget after. An entry is over a stated DIFFERENCE (the pair of
#: values), not over a fact: see :func:`test_the_declared_values_are_the_stated_difference`.
DECLARED_CROSSHAIR_DIVERGENCES: dict[str, tuple[tuple[str, str], str]] = {
    "events.listened": (
        ("pointerdown,pointerleave,pointermove", "pointercancel,pointerdown,pointerleave,pointermove,pointerup"),
        "The public crosshair counts the fingers that are down, so it needs to hear "
        "them lift (pointerup, pointercancel). The admin's has no such count: its "
        "pinch is handled in solver.js's marking code and wireCrosshair never "
        "learns of it. Why the public one counts: CARD-325 AC-7, a pinch neither "
        "starts a crosshair nor leaves one.",
    ),
    "events.that_clear_the_crosshair": (
        ("pointerleave", "pointerdown,pointerleave"),
        "A second finger landing (pointerdown) takes the crosshair the first "
        "finger's pointerdown had painted OFF, because two fingers are a pinch and "
        "a pinch has no crosshair (CARD-325 AC-7; zoom is CARD-324). The admin's "
        "crosshair clears only on pointerleave, and the question what a pinch "
        "does to it was not asked there: routed as a finding, not edited (G-2).",
    ),
    "pointer_type.is_read_in": (
        ("pointerleave", "pointerdown,pointerleave"),
        "CARD-267 decision 3 reads the pointer TYPE in the leave handler only. "
        "The public page reads it in pointerdown as well, to tell a finger (which "
        "can be one of two in a pinch) from a mouse (which never is). The leave "
        "handler's own rule, touch exempt, is the SAME and is held equal in "
        "leave.survivors.",
    ),
    "position.is_forgotten_on_redraw": (
        ("True", "False"),
        "CARD-267 decision 4: the admin's redraw() replaces every cell and calls "
        "forget(). The public page draws its table ONCE (drawBoard has a single "
        "call site, asserted by test_the_public_page_has_no_redraw_to_forget_after), "
        "so there is no redraw to hook. The refusal the decision exists for, a "
        "remembered position with nothing painted, is kept by the next entry.",
    ),
    "already_there.needs_the_cross_painted": (
        ("False", "True"),
        "The compensation for the entry above: the public 'already there, do "
        "nothing' shortcut is taken only when the DOM still shows the cross, so a "
        "stale memory can never suppress a repaint. Without forget() to rely on, "
        "this is how decision 4 is kept (browser-held by "
        "test_a_remembered_position_with_nothing_painted_repaints).",
    ),
}


class TestPlayerLooksAgree_TheCrosshairMakesTheSameDecisions:
    """CARD-325 AC-6."""

    def test_the_disagreements_are_exactly_the_declared_ones(self) -> None:
        admin = _CROSSHAIR_ADMIN_JS.read_text(encoding="utf-8")
        public = _CROSSHAIR_PUBLIC_JS.read_text(encoding="utf-8")
        found = crosshair_disagreements(admin, public)
        assert {k: v for k, v in found.items()} == {k: v[0] for k, v in DECLARED_CROSSHAIR_DIVERGENCES.items()}

    def test_the_declared_values_are_the_stated_difference(self) -> None:
        """A declaration is over the PAIR of values, so content drifting inside
        an exempted fact reds (CARD-328's lesson, one level down)."""
        for fact, (pair, reason) in DECLARED_CROSSHAIR_DIVERGENCES.items():
            assert pair[0] != pair[1], f"{fact} is declared but does not diverge"
            assert len(reason) >= _REASON_FLOOR, f"{fact}: a reason is a sentence, not a word"

    def test_the_four_decisions_are_compared_facts_and_agree(self) -> None:
        """The four cases of the card's item 1, by the fact that carries each."""
        admin = _CROSSHAIR_ADMIN_JS.read_text(encoding="utf-8")
        public = _CROSSHAIR_PUBLIC_JS.read_text(encoding="utf-8")
        a, p = (crosshair_facts(*_crosshair_source(path)) for path in (_CROSSHAIR_ADMIN_JS, _CROSSHAIR_PUBLIC_JS))
        # 1. the gutter corner: a hit that is not a cell moves nothing, and only
        #    leaving the stage clears (the extra public clear is declared).
        assert a["a_non_cell_hit.moves_nothing"] == p["a_non_cell_hit.moves_nothing"] == "True"
        assert "pointerleave" in a["events.that_clear_the_crosshair"].split(",")
        assert "pointerleave" in p["events.that_clear_the_crosshair"].split(",")
        # 2. the no-hover phone: pointerdown and pointermove move it.
        assert a["events.that_move_the_crosshair"] == p["events.that_move_the_crosshair"] == "pointerdown,pointermove"
        # 3. the exempt touch: the leave handler spares touch, and ONLY touch.
        assert a["leave.survivors"] == p["leave.survivors"] == "touch"
        # 4. the remembered position: declared (see the table).
        assert "position.is_forgotten_on_redraw" in DECLARED_CROSSHAIR_DIVERGENCES
        # and what is marked, and with what, is one thing.
        assert a["marker.class"] == p["marker.class"] == "is-crossed"
        assert a["marked.selectors"] == p["marked.selectors"]
        assert a["event.is_prevented"] == p["event.is_prevented"] == "False"
        assert a["event.is_stopped"] == p["event.is_stopped"] == "False"
        assert admin and public

    def test_the_facts_are_not_vacuous(self) -> None:
        """An extractor that returned empty strings on both sides would agree."""
        for path in (_CROSSHAIR_ADMIN_JS, _CROSSHAIR_PUBLIC_JS):
            facts = crosshair_facts(*_crosshair_source(path))
            for fact in ("events.listened", "events.that_move_the_crosshair", "leave.survivors", "marked.selectors", "marker.class"):
                assert facts[fact], (path.name, fact)
            assert facts["marked.selectors"].count("data-row") == 1 and facts["marked.selectors"].count("data-line") == 2

    def test_the_public_page_has_no_redraw_to_forget_after(self) -> None:
        """The premise of the declared 'forget' divergence, held: if the public
        page ever redraws its table, decision 4 is no longer kept by
        construction alone and this reds, naming the declaration to revisit."""
        code = "\n".join(line for _, line in _js_code_lines(PUBLIC_JS))
        assert len(re.findall(r"\bdrawBoard\s*\(", code)) == 2, "drawBoard: its definition and ONE call"
        assert len(re.findall(r"\breplaceChildren\s*\(", code)) == 2, "only drawBoard and fail() replace the stage's children"

    # -- the controls: both sides, and the edge decisions -------------------

    @pytest.mark.parametrize(
        ("side", "old", "new", "moves"),
        [
            ("admin", 'if (event.pointerType === "touch") return;', "", "leave.survivors"),
            ("public", 'if (event.pointerType === "touch") return;', "", "leave.survivors"),
            ("admin", 'if (event.pointerType === "touch") return;', 'if (event.pointerType === "pen") return;', "leave.survivors"),
            ("public", 'if (event.pointerType === "touch") return;', 'if (event.pointerType === "pen") return;', "leave.survivors"),
            ("admin", 'container.addEventListener("pointerdown", follow);', "", "events.that_move_the_crosshair"),
            ("public", 'stage.addEventListener("pointermove", follow);', "", "events.that_move_the_crosshair"),
            ("admin", "if (position !== null) moveTo(position);", "moveTo(position);", "a_non_cell_hit.moves_nothing"),
            ("public", "if (position !== null) moveTo(position);", "moveTo(position);", "a_non_cell_hit.moves_nothing"),
            ("admin", 'part.classList.toggle("is-crossed", on)', 'part.classList.toggle("is-cross", on)', "marker.class"),
            ("public", 'part.classList.toggle("is-crossed", on)', 'part.classList.toggle("is-cross", on)', "marker.class"),
            ("admin", 'th.player-clue.is-col[data-line="${col}"]', 'th.player-clue.is-col[data-line="${row}"]', "marked.selectors"),
            ("public", 'th.player-clue.is-row[data-line="${row}"]', 'th.player-clue.is-row[data-line="${col}"]', "marked.selectors"),
        ],
        ids=[
            "admin-touch-no-longer-exempt", "public-touch-no-longer-exempt",
            "admin-pen-exempt-not-touch", "public-pen-exempt-not-touch",
            "admin-pointerdown-no-longer-moves", "public-pointermove-no-longer-moves",
            "admin-a-gutter-hit-now-moves", "public-a-gutter-hit-now-moves",
            "admin-marker-renamed", "public-marker-renamed",
            "admin-column-clue-by-the-wrong-index", "public-row-clue-by-the-wrong-index",
        ],
    )
    def test_a_one_sided_change_to_a_decision_is_reported(self, side, old, new, moves) -> None:
        """Each edge mutant moves one fact on ONE side and the comparison reports
        it; the unmutated pair, in this same run, reports only the declared set
        (the matched control, asserted first)."""
        admin = _CROSSHAIR_ADMIN_JS.read_text(encoding="utf-8")
        public = _CROSSHAIR_PUBLIC_JS.read_text(encoding="utf-8")
        baseline = crosshair_disagreements(admin, public)
        assert set(baseline) == set(DECLARED_CROSSHAIR_DIVERGENCES), "the matched control"
        source = admin if side == "admin" else public
        assert source.count(old) == 1, f"the plant must apply exactly once: {old!r}"
        planted = source.replace(old, new)
        found = crosshair_disagreements(planted, public) if side == "admin" else crosshair_disagreements(admin, planted)
        assert found != baseline
        assert moves in found and found[moves] != baseline.get(moves, ("", "")), (moves, found.get(moves))

    def test_a_second_listener_for_one_event_is_refused_and_not_read_past(self) -> None:
        """Was the parametrized case ``public-leave-registered-twice``, split out
        so that no test body has an early ``return`` (CARD-238's detector counts
        one as a host-state silence). A second ``pointerleave`` listener would
        make the facts silently read one of the two, so extraction refuses it;
        the matched control is the shipped pair extracting cleanly first."""
        admin = _CROSSHAIR_ADMIN_JS.read_text(encoding="utf-8")
        public = _CROSSHAIR_PUBLIC_JS.read_text(encoding="utf-8")
        assert set(crosshair_disagreements(admin, public)) == set(DECLARED_CROSSHAIR_DIVERGENCES), "the matched control"
        old = 'stage.addEventListener("pointercancel", lift);'
        assert public.count(old) == 1, f"the plant must apply exactly once: {old!r}"
        planted = public.replace(old, old + '\n  stage.addEventListener("pointerleave", () => clear());')
        with pytest.raises(AssertionError, match="registered twice"):
            crosshair_disagreements(admin, planted)

    def test_a_declared_divergence_that_stops_diverging_is_reported(self) -> None:
        """The stale-exemption arm: make the public side forget on redraw like
        the admin and ``position.is_forgotten_on_redraw`` stops diverging, which
        the set equality must notice."""
        admin = _CROSSHAIR_ADMIN_JS.read_text(encoding="utf-8")
        public = _CROSSHAIR_PUBLIC_JS.read_text(encoding="utf-8")
        planted = public.replace("function wireCrosshair(stage) {", "function wireCrosshair(stage) {\n  const forget = () => {};", 1)
        assert crosshair_disagreements(admin, planted).keys() == crosshair_disagreements(admin, public).keys() - {
            "position.is_forgotten_on_redraw"
        }

    # -- the look -----------------------------------------------------------

    def test_the_crosshair_sheet_rules_agree_and_the_tint_is_a_declared_difference(
        self, admin_css: str, public_css: str
    ) -> None:
        """Same three selectors and the same one property; the tint and the ink
        derived from it differ in ONE stated way, and the residue is held."""
        selectors = (".player-cell.is-crossed", '.player-cell.is-crossed[data-state="filled"]', ".player-clue.is-crossed")
        admin_rules, public_rules = rules(admin_css), rules(public_css)
        for selector in selectors:
            assert rule_count(admin_css, selector) == rule_count(public_css, selector) == 1, selector
            a, p = declarations(admin_rules[selector]), declarations(public_rules[selector])
            assert set(a) == set(p) == {"background"}, selector
        # The tint. Admin: --color-surface-hover. Public: 9% of --color-text in
        # --grid-paper, because the public Maybe cell's ground IS
        # --color-surface-hover and the panel's hint line is
        # --color-accent-tint, and the card's design context requires the
        # crosshair to stay distinct from both.
        def stage_rule(css: str) -> dict[str, str]:
            """The ONE ``.player-stage`` rule that declares the tint (the
            selector has several rules; ``rules`` keeps only the last)."""
            owners = [
                declarations(body)
                for selector, body in _RULE.findall(_css_code(css))
                if _squeezed(selector) == ".player-stage" and "--player-cross:" in body
            ]
            assert len(owners) == 1, owners
            return owners[0]

        a_stage, p_stage = stage_rule(admin_css), stage_rule(public_css)
        assert a_stage["--player-cross"] == "var(--color-surface-hover)"
        assert p_stage["--player-cross"] == "color-mix(in srgb, var(--color-text) 9%, var(--grid-paper))"
        maybe_paper = declarations(public_rules['.player-cell[data-state="maybe"]'])["background"]
        assert maybe_paper == "var(--color-surface-hover)"
        assert p_stage["--player-cross"] != maybe_paper, "the public tint must stay distinct from the Maybe ground"
        hint_tints = [
            declarations(body)["--player-hint-line"]
            for selector, body in _RULE.findall(_css_code(admin_css))
            if _squeezed(selector) == ".player-stage" and "--player-hint-line:" in body
        ]
        assert hint_tints == ["var(--color-accent-tint)"], hint_tints
        assert p_stage["--player-cross"] not in hint_tints, "...and from the hint line's tint"
        # The RESIDUE of the ink: with each side's tint name factored out, the
        # mix is the same expression.
        def residue(text: str, tint: str) -> str:
            return text.replace(tint, "<TINT>")

        assert residue(a_stage["--player-cross-ink"], "var(--color-surface-hover)") == residue(
            p_stage["--player-cross-ink"], "var(--player-cross)"
        ) == "color-mix(in srgb, <TINT> 16%, var(--grid-ink))"


# ==========================================================================
# CARD-326 (SCOPE+: this file is not in the card's Touches; the card's premise
# note of 2026-11-05 names it) - the circles are the same look
# ==========================================================================
#
# Circled clue numbers are the second look in this file that the public page
# REIMPLEMENTS from the admin's (``admin.css`` + ``solver.js``'s CARD-188, and
# ``player.css`` + ``play.js``'s CARD-326): which numbers circle is the shared
# module's (``circledClues``, byte-identical by ADR-0041/R3), and everything
# that DRAWS the circle is two copies. Same discipline as the crosshair class
# above: every compared fact is DERIVED from the four sources, the facts that
# disagree are computed and asserted equal to a table of DECLARED divergences,
# and an entry is over the PAIR of values (found admin value, found public
# value), so content drifting inside a declared fact reds as well as a new fact.
#
# Why there are divergences at all, in one sentence: the panel gives every clue
# number a cell-tall slot (a 0.6-cell numeral, 0.88-cell ring) and this page's
# clue gutters are compact (a 0.42-cell numeral at line-height 1.1, a 0.35em
# gap between row numbers) and are pinned by tests/test_public_player_zoom.py,
# so the rings are fitted to the gutters instead of the gutters to the rings.

_CIRCLE_SELECTORS = {
    "number": ".player-board .player-clue-num",
    "ring": ".player-board .player-clue-num::before",
    "circled": ".player-board .player-clue-num.is-circled::before",
    "cap": ".player-board .player-clue.is-col .player-clue-num::before",
}
_CIRCLE_VARIABLES = ("--player-circle", "--player-circle-w", "--player-circle-clear", "--player-ring-gap")
_ABSENT = "(none)"


def _merged_declarations(css: str, selector: str) -> dict[str, str]:
    """Every declaration of every flat rule whose selector is exactly ``selector``."""
    merged: dict[str, str] = {}
    for found, body in _RULE.findall(_css_code(css)):
        if _squeezed(found) == selector:
            merged.update(declarations(body))
    return merged


def _paint_circles(js_source: str) -> str:
    from tests.test_public_player_crosshair import _raw_definition

    text = _raw_definition(js_source, "paintCircles")
    assert text is not None, "no paintCircles"
    return text


def circle_facts(css: str, js_source: str) -> dict[str, str]:
    """Every compared fact of one page's circles, as a string."""
    ring = _merged_declarations(css, _CIRCLE_SELECTORS["ring"])
    facts: dict[str, str] = {}
    facts["number.position"] = _merged_declarations(css, _CIRCLE_SELECTORS["number"]).get("position", _ABSENT)
    for prop in ("content", "position", "pointer-events", "box-sizing", "width", "height", "left", "top", "border", "border-radius", "--player-ring"):
        facts[f"ring.{prop}"] = ring.get(prop, _ABSENT)
    facts["circled.border-color"] = _merged_declarations(css, _CIRCLE_SELECTORS["circled"]).get("border-color", _ABSENT)
    board = _merged_declarations(css, ".player-board")
    for name in _CIRCLE_VARIABLES:
        facts[f"board.{name}"] = board.get(name, _ABSENT)
    facts["column_ring.is_capped"] = str(bool(_merged_declarations(css, _CIRCLE_SELECTORS["cap"])))
    painter = _paint_circles(js_source)
    code = "\n".join(line for _, line in _js_code_lines_of(js_source))
    facts["marker.class"] = ",".join(sorted(set(re.findall(r'classList\.toggle\(\s*"([^"]+)"', painter))))
    facts["marker.value"] = ",".join(re.findall(r'classList\.toggle\(\s*"[^"]+"\s*,\s*([^)]*)\)', painter))
    facts["marker.source_call"] = " | ".join(sorted(re.findall(r"\bcircledClues\(([^)]*)\)", code)))
    facts["painter.pairs_twin_gutters"] = str("twins" in painter)
    facts["digit_count.is_set_by_script"] = str("--player-clue-digits" in code)
    return facts


def _js_code_lines_of(source: str):
    for number, line in enumerate(source.splitlines(), 1):
        if not line.strip().startswith(("//", "*", "/*")):
            yield number, line


def circle_disagreements(admin_css_text: str, public_css_text: str, admin_js: str, public_js: str) -> dict[str, tuple[str, str]]:
    admin, public = circle_facts(admin_css_text, admin_js), circle_facts(public_css_text, public_js)
    assert admin.keys() == public.keys()
    return {k: (admin[k], public[k]) for k in admin if admin[k] != public[k]}


#: What the public circles do DIFFERENTLY from the admin's, each over the PAIR
#: of values found and each with the decision it rests on. Nine entries in
#: three groups. MEASURED, this round (2026-11-05, a real Chromium over the
#: assembled site, tests/test_public_player_circles.py): public ring height
#: 14.98 px at the 1440 px desktop's 100% and 44.97 px at the 300% maximum
#: (1.05em of a 14.27 px numeral, scaling 3.002x); the smallest gap between two
#: neighbouring rings on the 390 px phone 1.00 px (row) and 0.59 px (column) at
#: 100%, 3.11 px and 1.77 px at 300%, against the 0.25 px floor.
DECLARED_CIRCLE_DIVERGENCES: dict[str, tuple[tuple[str, str], str]] = {
    "board.--player-circle": (
        ("calc(var(--player-cell) * 0.88)", "1.05em"),
        "The ring's height. The panel's numeral is 0.6 of a cell with a cell-tall slot "
        "per number, so 0.88 of a cell encloses it (1.47 numerals); this page's numeral "
        "is 0.42 of a cell stacked at line-height 1.1, where 0.88 of a cell would be "
        "2.1 numerals tall and overlap its neighbours. 1.05em is a little under the "
        "1.1em a column number's line box is tall, so stacked rings never overlap "
        "(measured: 0.59 px apart at the phone's 100%).",
    ),
    "board.--player-circle-w": (
        ("max(var(--border-width), calc(var(--player-cell) * 0.06))", "max(var(--border-width), calc(var(--player-cell) * 0.035))"),
        "The ring's line. Inside a 1.05em ring a line 0.06 of a cell thick (1.7 px at "
        "the 28 px cell floor) would touch the digit; 0.035 of a cell is 1 px there "
        "(the --border-width floor binds) and scales with the zoom (3 px at 300%).",
    ),
    "board.--player-circle-clear": (
        ("calc(var(--player-cell) * 0.05)", "calc(var(--player-cell) * 0.02)"),
        "The clearance between digit and ring on each side, narrower for the same "
        "reason: two neighbouring row numbers sit 0.35em apart on this page and the "
        "two rings' clearance plus line must fit inside that gap (measured: 1.00 px "
        "clear at the phone's 100%).",
    ),
    "board.--player-ring-gap": (
        ("0.25px", _ABSENT),
        "The panel declares the least gap between two rings as a custom property its "
        "ring width is capped by. This page caps nothing, so it declares no property; "
        "the same 0.25 px is RING_GAP_FLOOR_PX in tests/test_public_player_circles.py "
        "with its measured residue and a control that fails just past it.",
    ),
    "ring.--player-ring": (
        (
            "max(var(--player-circle), calc(var(--player-clue-digits, 1) * 1ch + 2 * (var(--player-circle-clear) + var(--player-circle-w))))",
            _ABSENT,
        ),
        "The panel sizes the ring's pill from the digit count a script sets "
        "(--player-clue-digits) and caps column rings at the next column's heavy rule. "
        "Here the ring reads the number's own width (ring.width), so there is no "
        "script-set property (the token census in tests/test_public_player_pages.py "
        "refuses an undefined custom property) and nothing to cap.",
    ),
    "ring.width": (
        ("var(--player-ring)", "calc(100% + 2 * (var(--player-circle-clear) + var(--player-circle-w)))"),
        "The ring is the number's width plus clearance and line on each side (100% is "
        "the number's box), never the panel's max(circle, digits-in-ch + ...): a "
        "one-digit ring here is a narrow pill so two row rings fit in the gutter's "
        "existing 0.35em gap.",
    ),
    "ring.left": (
        ("calc(50% - var(--player-ring) / 2)", "calc(-1 * (var(--player-circle-clear) + var(--player-circle-w)))"),
        "The same placement written for the other width: centred on the number in the "
        "panel, hanging out by clearance plus line on the left here (the right is the "
        "width's other half), which is the same centring.",
    ),
    "column_ring.is_capped": (
        ("True", "False"),
        "The panel's column numbers are zero-width boxes, so its column ring is capped "
        "at the distance to the next column's heavy rule (CARD-196). Here a column "
        "number is a block as wide as its text, centred in a cell-wide column, so no "
        "ring can reach the next column (measured: the widest column ring on the 30 x "
        "30 fixture is 62.8 px at 300% in a 103 px cell).",
    ),
    "digit_count.is_set_by_script": (
        ("True", "False"),
        "See ring.--player-ring: the page sets no property from a script, only the "
        "class (marker.class), so what a script can say about a circle is one bit.",
    ),
    "painter.pairs_twin_gutters": (
        ("True", "False"),
        "CARD-212 gave the panel a second, mirrored row gutter, so each clue number "
        "can have a twin span that must circle with it. This page has one gutter per "
        "axis (and its painter, held to a closed vocabulary by tests/test_public_"
        "player_circles.py, has no loop over twins to get wrong).",
    ),
}


class TestPlayerLooksAgree_TheCirclesAreTheSameLook:
    """CARD-326 (GAP 2): the circles' look, the marker and the module call."""

    def _sources(self) -> tuple[str, str, str, str]:
        return (
            ADMIN_CSS.read_text(encoding="utf-8"),
            PUBLIC_CSS.read_text(encoding="utf-8"),
            ADMIN_JS.read_text(encoding="utf-8"),
            PUBLIC_JS.read_text(encoding="utf-8"),
        )

    def test_the_disagreements_are_exactly_the_declared_pairs(self) -> None:
        found = circle_disagreements(*self._sources())
        assert found == {k: v[0] for k, v in DECLARED_CIRCLE_DIVERGENCES.items()}

    def test_a_declaration_is_a_real_divergence_with_a_reason_over_a_fact_the_extractor_makes(self) -> None:
        admin_css_text, _, admin_js, _ = self._sources()
        facts = circle_facts(admin_css_text, admin_js)
        for fact, (pair, reason) in DECLARED_CIRCLE_DIVERGENCES.items():
            assert fact in facts, f"{fact} is declared but the extractor does not produce it"
            assert pair[0] != pair[1], f"{fact} is declared but does not diverge"
            assert len(reason) >= _REASON_FLOOR, f"{fact}: a reason is a sentence, not a word"

    def test_the_facts_that_agree_are_enumerated_and_not_empty(self) -> None:
        """Both sheets saying nothing would agree; so the agreeing facts are the
        extractor's keys minus the declared ones, each a real value on BOTH sides."""
        admin_css_text, public_css_text, admin_js, public_js = self._sources()
        a, p = circle_facts(admin_css_text, admin_js), circle_facts(public_css_text, public_js)
        agreeing = sorted(set(a) - set(DECLARED_CIRCLE_DIVERGENCES))
        assert agreeing == [
            "circled.border-color", "marker.class", "marker.source_call", "marker.value",
            "number.position", "ring.border", "ring.border-radius", "ring.box-sizing", "ring.content",
            "ring.height", "ring.pointer-events", "ring.position", "ring.top",
        ]
        for fact in agreeing:
            assert a[fact] == p[fact] and a[fact] not in {"", _ABSENT, "False"}, (fact, a[fact])
        assert p["circled.border-color"] == "var(--grid-ink)"
        assert p["marker.class"] == "is-circled"
        assert p["marker.source_call"] == "history.board, payload.rows, payload.columns"

    def test_the_declared_ring_sizes_are_the_stated_ratio(self) -> None:
        """The first declaration's prose says 1.47 numerals and 2.1 numerals: derived here
        from the two sheets' own numbers, not written into the reason alone."""
        admin_css_text, public_css_text, _, _ = self._sources()
        ring = float(re.search(r"\* ([\d.]+)\)", DECLARED_CIRCLE_DIVERGENCES["board.--player-circle"][0][0]).group(1))
        assert ring == 0.88
        panel_numeral = float(
            re.search(r"font-size: max\(var\(--player-numeral-min\), calc\(var\(--player-cell\) \* ([\d.]+)\)\)", admin_css_text).group(1)
        )
        page_numeral = float(re.search(r"\.player-clue \{[^}]*font-size: calc\(var\(--player-cell\) \* ([\d.]+)\)", public_css_text).group(1))
        assert (panel_numeral, page_numeral) == (0.6, 0.42)
        assert round(ring / panel_numeral, 2) == 1.47
        assert round(ring / page_numeral, 1) == 2.1
        public_ring_em = float(DECLARED_CIRCLE_DIVERGENCES["board.--player-circle"][0][1].removesuffix("em"))
        line_height = float(re.search(r"\.player-clue \{[^}]*line-height: ([\d.]+);", public_css_text).group(1))
        assert public_ring_em < line_height, "a column number's ring must be shorter than its line box"
        assert round(line_height - public_ring_em, 2) == 0.05

    # -- the controls: both sides, and the decisions that are held equal ----

    @pytest.mark.parametrize(
        ("side", "target", "old", "new", "moves"),
        [
            ("admin", "css", "border-radius: calc(var(--player-circle) / 2);", "border-radius: 0;", "ring.border-radius"),
            ("public", "css", "border-radius: calc(var(--player-circle) / 2);", "border-radius: 0;", "ring.border-radius"),
            ("admin", "css", ".player-board .player-clue-num.is-circled::before { border-color: var(--grid-ink); }",
             ".player-board .player-clue-num.is-circled::before { border-color: var(--color-accent); }", "circled.border-color"),
            ("public", "css", ".player-board .player-clue-num.is-circled::before { border-color: var(--grid-ink); }",
             ".player-board .player-clue-num.is-circled::before { border-color: var(--color-accent); }", "circled.border-color"),
            ("admin", "css", "pointer-events: none; box-sizing: border-box;", "box-sizing: border-box;", "ring.pointer-events"),
            ("public", "css", "pointer-events: none; box-sizing: border-box;", "box-sizing: border-box;", "ring.pointer-events"),
            ("admin", "css", "height: var(--player-circle);", "height: 20px;", "ring.height"),
            ("public", "css", "height: var(--player-circle);", "height: 20px;", "ring.height"),
            ("admin", "js", 'span.classList.toggle("is-circled", circled[axis][line][k])', 'span.classList.toggle("is-ringed", circled[axis][line][k])', "marker.class"),
            ("public", "js", 'span.classList.toggle("is-circled", circled[axis][line][k])', 'span.classList.toggle("is-ringed", circled[axis][line][k])', "marker.class"),
            ("admin", "js", 'span.classList.toggle("is-circled", circled[axis][line][k])', 'span.classList.toggle("is-circled", true)', "marker.value"),
            ("public", "js", 'span.classList.toggle("is-circled", circled[axis][line][k])', 'span.classList.toggle("is-circled", true)', "marker.value"),
            ("admin", "js", "circledClues(history.board, payload.rows, payload.columns)", "circledClues(shown, payload.rows, payload.columns)", "marker.source_call"),
            ("public", "js", "circledClues(history.board, payload.rows, payload.columns)", "circledClues(shown, payload.rows, payload.columns)", "marker.source_call"),
        ],
        ids=[
            "admin-ring-square", "public-ring-square",
            "admin-circle-in-accent", "public-circle-in-accent",
            "admin-ring-takes-the-pointer", "public-ring-takes-the-pointer",
            "admin-ring-fixed-height", "public-ring-fixed-height",
            "admin-marker-renamed", "public-marker-renamed",
            "admin-everything-circled", "public-everything-circled",
            "admin-reads-the-preview", "public-reads-the-preview",
        ],
    )
    def test_a_one_sided_change_to_a_held_fact_is_reported(self, side, target, old, new, moves) -> None:
        """Each plant moves one AGREEING fact on one side and the comparison
        reports it; the unplanted pair, in this same run, reports only the
        declared set (the matched control, asserted first)."""
        admin_css_text, public_css_text, admin_js, public_js = self._sources()
        baseline = circle_disagreements(admin_css_text, public_css_text, admin_js, public_js)
        assert set(baseline) == set(DECLARED_CIRCLE_DIVERGENCES), "the matched control"
        texts = {"admin": {"css": admin_css_text, "js": admin_js}, "public": {"css": public_css_text, "js": public_js}}
        text = texts[side][target]
        assert text.count(old) == 1, f"the plant must apply exactly once: {old!r} ({text.count(old)})"
        texts[side][target] = text.replace(old, new)
        found = circle_disagreements(texts["admin"]["css"], texts["public"]["css"], texts["admin"]["js"], texts["public"]["js"])
        assert moves in found and moves not in baseline, (moves, sorted(found))

    def test_a_declared_divergence_that_stops_diverging_is_reported(self) -> None:
        """The stale-exemption arm: give the public sheet the panel's ring height
        and ``board.--player-circle`` stops diverging, which the set equality must notice."""
        admin_css_text, public_css_text, admin_js, public_js = self._sources()
        assert public_css_text.count("  --player-circle: 1.05em;") == 1
        planted = public_css_text.replace("  --player-circle: 1.05em;", "  --player-circle: calc(var(--player-cell) * 0.88);")
        found = circle_disagreements(admin_css_text, planted, admin_js, public_js)
        assert "board.--player-circle" not in found
        assert set(found) == set(DECLARED_CIRCLE_DIVERGENCES) - {"board.--player-circle"}

    def test_a_declared_value_that_drifts_inside_its_fact_is_reported(self) -> None:
        """An exemption is over the PAIR: the public ring height drifting to another
        em still diverges from the panel, and the PAIR comparison is what reds."""
        admin_css_text, public_css_text, admin_js, public_js = self._sources()
        planted = public_css_text.replace("  --player-circle: 1.05em;", "  --player-circle: 1.2em;")
        found = circle_disagreements(admin_css_text, planted, admin_js, public_js)
        assert "board.--player-circle" in found
        assert found["board.--player-circle"] != DECLARED_CIRCLE_DIVERGENCES["board.--player-circle"][0]
        assert found != {k: v[0] for k, v in DECLARED_CIRCLE_DIVERGENCES.items()}
