"""CARD-323 — the public player's fourth brush: Maybe ("?").

The public page offered three brushes and the admin player four. That was a
**scope choice** and not a constraint, and the difference it rested on is worth
stating because it is the line the next player cards are on either side of:
``solver_state.js``'s ``isSolved``, ``errorCount``, ``solvedPercent`` and
``hintCell`` all take ``solution``, which this page by design never has
(ADR-0038/R6, ADR-0041/R2), so no counter and no hint is reachable here at all.
A **brush** takes nothing of the sort. Every transition Maybe needs was already
in the module ADR-0041/R3 makes the two players share byte-for-byte, and
``player/player.css`` already carried the mark's cell background, and the glyph
the admin drew beside it became CARD-339. The owner reversed
the scope choice on 2026-10-30; this module is the gate on the reversal.

Where each AC is answered, and why there
----------------------------------------
Two tiers, the split following ``tests/test_public_player.py``'s own:

* **tree tests** (AC-2, AC-4) read ``player/`` and the admin template off disk.
  "the four tools are in the admin's order" and "the look is declared once" are
  statements about *files*, and a browser adds nothing to either;
* **browser tests** (AC-1, AC-3, AC-5, ``@pytest.mark.browser``) own what only
  a real engine can answer: the mark a click leaves, the radio group's state
  and the reload. They refuse **LOUDLY** when Chromium is absent (ADR-0038/R8)
  because they take CARD-160's own ``browser_page`` / ``browser_type``
  fixtures, imported below rather than rewritten — those call ``pytest.fail``,
  never ``skip``.

The harness is imported, not rebuilt
------------------------------------
``bundle`` / ``site`` / ``host`` and the ``_open`` / ``_tap`` / ``_state``
helpers come from ``tests/test_public_player.py`` by name, which is the
mechanism that file already uses for CARD-160's browser fixtures and that
``tests/test_public_player_pages.py`` already uses for its helpers. **This is
the pattern the four sibling player cards (CARD-324..327) should follow**: one
test module per card, importing the assembled-site harness rather than standing
up a second server, so the site under test is the site every other public-player
test measures and a change to the assembler reaches all of them at once.

The CSS parser is imported too, from
``tests/test_public_player_agreement.py`` — the repo's standing preference is a
second *implementation* over a shared derivation of the value under test, and
what is shared here is neither: it is a regex-and-brace reader for a sheet
nothing in this module writes. A third CSS parser in the test tree would be
three things to keep right, not more evidence.

No ``hypothesis`` (not in the dependency baseline). AC-3's walk is a seeded
``random.Random`` corpus whose minimum case count is **derived from the page's
own tool set** rather than written down, so the corpus cannot shrink when the
tool set does.

How every claim here is held to a control that can fail
-------------------------------------------------------
ADR-0039/R1. The two tree tests each compute their answer through a named
function and then run the identical function over **mutated text**, asserting
the mutant is reported: a reordered ``play.html`` (AC-2), and four separate
plants in the stylesheet (AC-4) — a second cell rule, an extra rule added as an
``::after``, the swatch rule deleted, the swatch given a different value, and
since CARD-339 three more at the glyph it added (either glyph deleted, and the
swatch's mark changed).
The browser tests' control is the feature's own absence, and it was run: with
``TOOLS`` put back to ``[FILLED, EMPTY, UNKNOWN]`` and ``play.html``'s fourth
button left in place, AC-1, AC-3 and AC-5 all fail (the click handler's
``TOOLS.includes`` guard returns early, so the brush never changes and the
cell takes the previous brush's mark). The measurement is in CARD-323's report.

What CARD-339 changed here, and why that is not a regression in this card
-------------------------------------------------------------------------
This card measured a second thing and could not fix it: the admin draws a "?"
glyph in the accent token on its Maybe cell and swatch, and this page drew a
tint and no glyph. Fixing it would have re-declared the look AC-4 makes a
finding against this card, so it was routed to the owner, who decided on
2026-11-03 that the public page gains the glyph. CARD-339 added it.

**That lands squarely on AC-4's two arms, and by design.** :func:`maybe_rules`
is pseudo-element-blind, so the glyph is a second rule deciding the cell's look
and a second rule deciding the swatch's — which is exactly the shape this class
was built to catch, because at the time no card was allowed to add one. Both
arms were written with that hand-off in their failure messages. So the arms now
expect **two** rules per hook — the paper and the glyph — and what the glyph
*declares* is not re-asserted here: it is
``tests/test_public_player_agreement.py``'s
``TestPlayerLooksAgree_TheMaybeMarkIsTheSameMark``, which holds both glyphs to
``admin.css``'s own declarations, and a second copy of that claim here would be
a second copy of a guard rather than a second guard.

One nit left standing deliberately:
:meth:`TestPublicMaybe_TheLookIsDeclaredOnce.test_the_maybe_cell_look_is_one_rule_declaring_one_background`
now reads as a claim about the **paper** rule only, which is still one rule
declaring one background. The name is not renamed here because
``meta/kanban/cards/CARD-323.md`` cites it by name and that file is
outside CARD-339's ``Touches`` — and a rename would go dead under a check-ref
resolver that is a TEXT search. **CARD-347 takes both files and owes the
rename**; this note is the interim. (The count was "twice" until this gate:
a fixed-string count over ``CARD-323.md`` returns **1**, by two instruments,
at the commit this lands on. One citation is reach enough for the argument,
so the conclusion is unchanged — but cycle 2 *rewrote this very sentence* and
carried the figure through without re-deriving it, which is the same class of
defect as the miscounts that cycle was fixing. The fix is the count; the
lesson is that a rewritten sentence re-opens every figure inside it.)

Tests, by node id (FR-045, CARD-323's ACs)
------------------------------------------
Written out in full, path and name on one line each, for the reason
``tests/test_public_player.py``'s own table gives: the architecture validator
resolves a check ref by a TEXT search for the whole ``path::name`` string, so a
ref wrapped across two lines reads as dead however green the test is.

* AC-1 — ``tests/test_public_player_maybe.py::TestPublicMaybe_TheBrushMarksACell``
* AC-2 — ``tests/test_public_player_maybe.py::TestPublicMaybe_FourToolsInTheAdminsOrder``
* AC-3 — ``tests/test_public_player_maybe.py::TestPublicMaybe_OneToolIsCheckedAtATime``
* AC-4 — ``tests/test_public_player_maybe.py::TestPublicMaybe_TheLookIsDeclaredOnce``
* AC-5 — ``tests/test_public_player_maybe.py::TestPublicMaybe_AReloadRestoresMaybeMarks``

ADR-0041/R2, and what this module does and does not establish about it
----------------------------------------------------------------------
A Maybe mark is the player's own note. It is not derived from a solution — the
page has none — and this card adds no served field (G-2). Two assertions here
hold that rather than asserting it in prose: ``TestPublicMaybe_AReloadRestores
MaybeMarks`` compares the **key set** of a save made with the fourth brush
against the key set of a save made with the first, so a new channel in the save
reds; and the same class asserts the served ``puzzle/<key>.json`` the page
fetched carries exactly the fields ``play.js``'s ``readPayload`` reads. The
*whole* of R2 over the served tree stays where it already is — ``tests/test
_public_player.py::test_served_tree_is_clean_of_answers`` and
``::test_the_page_carries_no_answer_and_no_third_party_asset`` — which run over
this card's tree unchanged; duplicating that sweep here would be a second copy
of a guard, not a second guard.
"""

from __future__ import annotations

import json
import random
import re
from pathlib import Path

import pytest

from tests.test_public_player import (  # noqa: F401 — fixtures used by name
    GRIDS,
    PLAYER_DIR,
    REPO_ROOT,
    _open,
    _state,
    _tap,
    browser_page,
    browser_type,
    bundle,
    host,
    site,
)
from tests.test_public_player_agreement import _RULE, _css_code, _squeezed, declarations

ADMIN_TEMPLATE = REPO_ROOT / "src" / "nonogram" / "admin" / "templates" / "puzzle_solve.html"
STATE_MODULE = REPO_ROOT / "src" / "nonogram" / "admin" / "static" / "solver_state.js"
PUBLIC_PAGE = PLAYER_DIR / "play.html"
PUBLIC_CSS = PLAYER_DIR / "player.css"

#: One ``data-player-tool="…"`` attribute, wherever it sits.
_TOOL_ATTR = re.compile(r'data-player-tool="([a-z]+)"')

#: The hook :func:`admin_tool_order` slices the admin's brush menu on. Named
#: rather than inlined because it is the one string whose disappearance makes
#: this module's authority unreadable, and the failure has to say so: four
#: public-player test modules (CARD-323..327) each re-read this block, so a
#: rename on the written side turns into four failures at once and every one of
#: them has to name the cause. Declaring the coupling on the WRITTEN side is
#: CARD-324's obligation (see CARD-323's amended pattern point 4).
_ADMIN_MENU_HOOK = 'class="player-tool-menu"'


# ==========================================================================
# Reading the two authorities: the admin's menu, and the module's state set
# ==========================================================================


def tool_order(html: str) -> list[str]:
    """The ``data-player-tool`` values in ``html``, in document order.

    A list and not a set: the order **is** the claim AC-2 makes, and a set
    would make a reordered menu pass.
    """
    return _TOOL_ATTR.findall(html)


def admin_tool_order() -> list[str]:
    """The admin player's brush menu order, read from its own template.

    Sliced to the ``.player-tool-menu`` block rather than taken from the whole
    template, so a future ``data-player-tool`` on the trigger button (or
    anywhere else on that page) cannot silently join the sequence this card is
    held to.

    Every way the slice can fail names its cause, which is the point and not a
    courtesy: this reads a file in the **other** tree, four sibling modules
    will read the same block, and whoever breaks it is on the written side with
    none of this in front of them. A reorder reds as ``public [...] != admin
    [...]``; a wrapper ``div`` inside the menu truncates the slice and reds on
    the floor below; a rename of the hook reds on :data:`_ADMIN_MENU_HOOK`'s
    own assertion rather than as a bare ``ValueError: substring not found``,
    which is what ``str.index`` gave before CARD-323's round-1 fix.
    """
    text = ADMIN_TEMPLATE.read_text(encoding="utf-8")
    start = text.find(_ADMIN_MENU_HOOK)
    assert start != -1, (
        f"{_ADMIN_MENU_HOOK!r} is not in {ADMIN_TEMPLATE.name}: the admin brush menu's class "
        f"was renamed or moved, so the authority this module reads the tool order from is "
        f"gone. Re-point _ADMIN_MENU_HOOK at the block carrying the data-player-tool buttons "
        f"(the public player's test modules read it; this is not a defect in the admin page)."
    )
    end = text.find("</div>", start)
    assert end != -1, (
        f"{_ADMIN_MENU_HOOK!r} in {ADMIN_TEMPLATE.name} opens a block that never closes, so "
        f"the brush menu cannot be sliced out of it"
    )
    order = tool_order(text[start:end])
    assert len(order) >= 4, f"the admin menu reads as {order}, so it is not the authority"
    return order


def cell_states() -> list[str]:
    """``solver_state.js``'s ``CELL_STATES``, resolved to its string values.

    The module declares the array by identifier (``[UNKNOWN, FILLED, EMPTY,
    MAYBE]``), so the names are resolved against the file's own ``export
    const`` string declarations. Read from ``src/`` because that is the
    original; the copy the page actually serves is held byte-identical to it by
    ``tests/test_public_player.py::test_the_state_module_and_tokens_are_byte
    _identical_copies``, so reading either is reading both.
    """
    text = STATE_MODULE.read_text(encoding="utf-8")
    values = dict(re.findall(r'export const ([A-Z_]+) = "([a-z]+)";', text))
    match = re.search(r"export const CELL_STATES = Object\.freeze\(\[([^\]]+)\]\);", text)
    assert match is not None, "solver_state.js does not declare CELL_STATES as a frozen array"
    names = [name.strip() for name in match.group(1).split(",") if name.strip()]
    resolved = [values[name] for name in names]
    assert len(resolved) == len(names) and len(set(resolved)) == len(resolved), resolved
    return resolved


# ==========================================================================
# Reading the stylesheet: which rules decide a maybe mark's appearance
# ==========================================================================

#: The attribute selector that makes a rule *specific to* a maybe mark. A rule
#: without it (``.player-cell`` itself, which sets the paper) contributes to
#: every cell's appearance and is not what AC-4 counts: AC-4's subject is the
#: place where the fourth MARK's own look is decided.
_MAYBE_ATTR = '[data-state="maybe"]'


def maybe_rules(css: str, hook: str) -> list[tuple[str, str]]:
    """Every flat rule of ``css`` deciding a maybe ``hook``'s look.

    ``hook`` is ``.player-cell`` or ``.player-swatch``. A rule qualifies when
    its selector names the hook **and** carries ``[data-state="maybe"]``, which
    is deliberately pseudo-element-blind: ``…[data-state="maybe"]::after`` is a
    second place the mark's look is decided, and counting it is the whole
    point — the admin sheet draws its "?" exactly that way, so the card that
    copied that look across (CARD-339) reddened here rather than slipping past
    a selector-equality check, which is the hand-off working as built.

    Comments are stripped first (``_css_code``): ``player.css``'s own prose
    quotes the selectors it is talking about, and a reader that did not strip
    would find the sentence.
    """
    return [
        (_squeezed(selector), body)
        for selector, body in _RULE.findall(_css_code(css))
        if hook in _squeezed(selector) and _MAYBE_ATTR in _squeezed(selector)
    ]


#: What the mark draws, written here independently of either sheet, so "the
#: swatch matches the cell" cannot be satisfied by two rules drawing the same
#: wrong thing. The full declaration sets are compared against ``admin.css``
#: by ``tests/test_public_player_agreement.py``; these two are the floor.
MARK = '"?"'
MARK_TOKEN = "var(--color-accent)"


def _without_rule(css: str, selector: str) -> str:
    """``css`` with the one flat rule spelled ``selector`` removed.

    Written as a plant rather than a string literal because the two glyph rules
    are seven and ten declarations long, and a mutant carrying a copy of one
    would drift away from the sheet it is about the first time that sheet is
    reformatted — the hazard the four plants above avoid by being short.
    """
    bodies = [
        body
        for found, body in _RULE.findall(_css_code(css))
        if _squeezed(found) == selector
    ]
    assert len(bodies) == 1, f"{selector}: expected one rule to delete, found {len(bodies)}"
    return css.replace(f"{selector} {{{bodies[0]}}}", "", 1)


def look_report(css: str) -> dict[str, object]:
    """What ``css`` says about the maybe mark, as a comparable summary.

    One function, used on the real sheet and on every mutant, so the mutants
    are measured by the identical reading rather than by a second one.
    """
    cell = maybe_rules(css, ".player-cell")
    swatch = maybe_rules(css, ".player-swatch")
    return {
        "cell_rules": [selector for selector, _ in cell],
        "swatch_rules": [selector for selector, _ in swatch],
        "cell_declarations": [declarations(body) for _, body in cell],
        "swatch_declarations": [declarations(body) for _, body in swatch],
    }


# ==========================================================================
# AC-2 — four tools, in the admin's order
# ==========================================================================


class TestPublicMaybe_FourToolsInTheAdminsOrder:
    """AC-2 — ``.player-tools`` holds four brushes, ordered as the admin's menu.

    The order is asserted against ``templates/puzzle_solve.html`` rather than
    against a list spelled twice (ADR-0039/R2): a card that reorders the admin
    menu and forgets this page reds here, which a literal could not do.
    """

    def test_the_public_page_offers_the_admin_menus_four_tools_in_its_order(self) -> None:
        public = tool_order(PUBLIC_PAGE.read_text(encoding="utf-8"))
        admin = admin_tool_order()
        assert public == admin, f"public {public} != admin {admin}"
        # The authority is itself checked, so "they agree" cannot be two
        # sheets agreeing on a wrong set: the order is a permutation of the
        # module's four cell states, and no state is missing or repeated.
        assert sorted(admin) == sorted(cell_states()), (admin, cell_states())
        assert "maybe" in public, public

    def test_each_tool_is_a_radio_built_like_its_siblings(self) -> None:
        """The fourth button is its siblings' shape, not a near-miss of it.

        ``role="radio"`` and ``aria-checked`` are what make the group operable
        at all, and a swatch carrying the state is what draws the brush. Read
        per button so a missing attribute on the *new* one is what fails,
        rather than a count that four buttons satisfy either way.
        """
        html = PUBLIC_PAGE.read_text(encoding="utf-8")
        buttons = re.findall(r"<button[^>]*data-player-tool=[^>]*>.*?</button>", html, re.S)
        assert len(buttons) == len(tool_order(html)) == len(admin_tool_order()), buttons
        checked = []
        for button in buttons:
            tool = _TOOL_ATTR.search(button).group(1)
            assert 'role="radio"' in button, tool
            assert f'class="player-swatch" data-state="{tool}"' in button, tool
            assert 'aria-hidden="true"' in button, tool
            state = re.search(r'aria-checked="(true|false)"', button)
            assert state is not None, tool
            if state.group(1) == "true":
                checked.append(tool)
        # The served markup's own starting state: exactly one brush, and it is
        # the one play.js starts with (`let tool = FILLED`), so the page is not
        # momentarily lying before the first refresh() runs.
        assert checked == ["filled"], checked
        assert "let tool = FILLED;" in (PLAYER_DIR / "play.js").read_text(encoding="utf-8")

    def test_the_order_check_reports_a_reordered_page(self) -> None:
        """The control: the same reading over a page with Maybe moved last.

        Without this, ``public == admin`` is a claim whose failure mode nobody
        has seen. The mutant is the one a careless edit actually produces.
        """
        html = PUBLIC_PAGE.read_text(encoding="utf-8")
        maybe = re.search(r'\n *<button[^>]*data-player-tool="maybe".*?</button>', html, re.S)
        assert maybe is not None, "play.html has no maybe button to move"
        moved = html.replace(maybe.group(0), "") + maybe.group(0)
        assert tool_order(moved) != admin_tool_order(), tool_order(moved)
        assert sorted(tool_order(moved)) == sorted(admin_tool_order()), (
            "the mutant lost a button, so it would red for the wrong reason"
        )

    def test_the_tools_constant_is_the_markups_order(self) -> None:
        """``play.js``'s ``TOOLS`` and the DOM agree, by the constant's own word.

        The constant's comment says the order is the DOM's; this is what makes
        that sentence checkable. ``TOOLS`` holds identifiers, resolved through
        ``solver_state.js``'s exports exactly as :func:`cell_states` does.
        """
        script = (PLAYER_DIR / "play.js").read_text(encoding="utf-8")
        match = re.search(r"const TOOLS = \[([^\]]+)\];", script)
        assert match is not None, "play.js does not declare TOOLS as a flat array"
        values = dict(
            re.findall(r'export const ([A-Z_]+) = "([a-z]+)";', STATE_MODULE.read_text(encoding="utf-8"))
        )
        names = [name.strip() for name in match.group(1).split(",") if name.strip()]
        assert [values[name] for name in names] == tool_order(
            PUBLIC_PAGE.read_text(encoding="utf-8")
        ), names
        # And the names really are imported, not shadowed by a local literal.
        imports = re.search(r"import \{(.*?)\} from \"/solver_state\.js\";", script, re.S)
        assert imports is not None, "play.js does not import from the shared module"
        imported = {name.strip() for name in imports.group(1).replace("\n", "").split(",")}
        assert set(names) <= imported, sorted(set(names) - imported)


# ==========================================================================
# AC-4 — the look is declared once, and the swatch is its other half
# ==========================================================================


class TestPublicMaybe_TheLookIsDeclaredOnce:
    """AC-4 — the maybe mark's look is decided in one place per hook, per part.

    The card's premise is that the cell look **already shipped**, so this
    card's only legitimate CSS is the swatch half — which did *not* resolve
    before, because the shipped rule's selector is ``.player-cell``-scoped and
    a ``.player-swatch`` carrying the same state fell through to the base
    rule's paper. A second *paper* rule on either hook is still a finding
    against this card and still reds here.

    **The expected shape changed once, on 2026-11-03, and only once.** A glyph
    bolted on as an ``::after`` was a finding against this card too, because at
    the time no card was allowed to add one; the owner then decided the public
    page gains the admin's "?" and CARD-339 added it. So each hook now carries
    **two** rules — the paper and the glyph — and this class holds that shape
    and the relationship between the hooks. What the glyph *declares* is
    ``tests/test_public_player_agreement.py``'s
    ``TestPlayerLooksAgree_TheMaybeMarkIsTheSameMark``, which derives it from
    ``admin.css``; duplicating that here would be a second copy of a guard.

    What this does and does not mechanise, stated rather than implied: it holds
    each hook's paper to **one rule declaring one property**, which is the
    shape the pre-existing rule has and a shape no re-declaration can satisfy.
    It does not read git history, so "the rule that existed before this card"
    is established by that shape plus the card's own diff, not by a timestamp.
    """

    def test_the_maybe_cell_look_is_one_rule_declaring_one_background(self) -> None:
        """The paper is one rule declaring one background; the glyph is the second.

        This is the guard CARD-339's AC-1 tripped **first, and on both
        assertions**: :func:`maybe_rules` counts a ``::after`` rather than
        filtering it, so the glyph landed in ``cell_rules`` and in
        ``cell_declarations`` at once. Both messages named that hand-off, and
        the hand-off then arrived: the expected shape below is the taught one.

        The name now reads as a claim about the **paper** rule — still one
        rule, still one background — and the glyph is the second, *expected*
        place the look is decided. The two are asserted in document order,
        which is also specificity order: a glyph rule written above the paper
        rule would still paint, but the sheet would then decide the mark's look
        in an order its own comments do not describe, and that is worth
        failing on rather than tolerating.
        """
        report = look_report(PUBLIC_CSS.read_text(encoding="utf-8"))
        handoff = (
            "the maybe cell's look is not the paper rule followed by the glyph rule. A THIRD "
            "place the look is decided is the re-declaration AC-4 makes a finding against "
            "CARD-323; a MISSING glyph is CARD-339's AC-1 being reverted, and "
            "tests/test_public_player_agreement.py::"
            "TestPlayerLooksAgree_TheMaybeMarkIsTheSameMark is the guard that says what the "
            "glyph has to declare. Read as "
        )
        assert report["cell_rules"] == [
            '.player-cell[data-state="maybe"]',
            '.player-cell[data-state="maybe"]::after',
        ], f"{handoff}cell rules {report['cell_rules']}."
        paper, glyph = report["cell_declarations"]
        assert sorted(paper) == ["background"], (
            f"{handoff}the paper rule declares {sorted(paper)}."
        )
        assert glyph["content"] == MARK and glyph["color"] == MARK_TOKEN, (
            f"{handoff}the glyph draws {glyph.get('content')!r} in "
            f"{glyph.get('color')!r}."
        )

    def test_the_swatch_previews_the_cell_with_the_cells_own_value(self) -> None:
        """One swatch rule, and its value is the cell's.

        The swatch is the brush button's preview of the mark, so a swatch
        showing something the cell does not show would be a lie the suite
        could not see — which is why the equality, and not merely the
        rule's presence, is the assertion.
        """
        report = look_report(PUBLIC_CSS.read_text(encoding="utf-8"))
        assert report["swatch_rules"] == [
            '.player-swatch[data-state="maybe"]',
            '.player-swatch[data-state="maybe"]::after',
        ], report["swatch_rules"]
        cell_paper, cell_glyph = report["cell_declarations"]
        swatch_paper, swatch_glyph = report["swatch_declarations"]
        assert swatch_paper == cell_paper, (
            "the swatch stopped previewing the cell: the brush button's maybe paper reads as "
            f"{swatch_paper} and the cell's as {cell_paper}."
        )
        assert (swatch_glyph["content"], swatch_glyph["color"]) == (
            cell_glyph["content"],
            cell_glyph["color"],
        ), (
            "the swatch stopped previewing the cell's MARK: the button draws "
            f"{swatch_glyph.get('content')!r} in {swatch_glyph.get('color')!r} and the cell "
            f"draws {cell_glyph.get('content')!r} in {cell_glyph.get('color')!r}. That is "
            "CARD-339's AC-1, and this message is the one it reads."
        )
        # What may differ between the two, and the reason, asserted so it
        # cannot quietly become "they agree about everything": the glyph is
        # sized from the box it sits in — 0.6 x the board cell, --text-xs in
        # 1em of button chrome — exactly as admin.css sizes its own two. A
        # swatch glyph sized from --player-cell would be drawn from a token no
        # swatch sets, so it is the sizing, not the mark, that is the hook's.
        assert swatch_glyph["font-size"] != cell_glyph["font-size"], (
            swatch_glyph["font-size"],
            cell_glyph["font-size"],
        )
        # Tokens only (G-4): the value is a var(), not a colour.
        assert re.fullmatch(r"var\(--[a-z0-9-]+\)", cell_paper["background"]), cell_paper
        assert re.fullmatch(r"var\(--[a-z0-9-]+\)", cell_glyph["color"]), cell_glyph

    #: The plants this class is held to, each as ``(name, mutate)``. Every one
    #: is a defect somebody could really ship: the two cell plants are the two
    #: ways to re-declare the mark — flat, and as a pseudo-element — and the two
    #: swatch plants are losing the card's own line and getting its value wrong.
    #:
    #: The ``::after`` plant is named for the *arithmetic* it exercises, not for
    #: the ``?`` glyph, and deliberately: once CARD-339 lands, a glyph rule is
    #: the sheet's legitimate second cell rule, so this plant then appends a
    #: THIRD and still reports — green, but catching a duplicate rather than a
    #: forbidden shape. The name holds in both worlds; "a ? glyph as an
    #: ``::after``", which it was called before, stops describing it on that
    #: merge.
    MUTANTS = {
        "a second cell rule": lambda css: css
        + '\n.player-cell[data-state="maybe"] { background: var(--grid-ink); }\n',
        "an extra cell rule, as an ::after": lambda css: css
        + '\n.player-cell[data-state="maybe"]::after { content: "?"; color: var(--color-accent); }\n',
        "the swatch rule deleted": lambda css: css.replace(
            '.player-swatch[data-state="maybe"] { background: var(--color-surface-hover); }', ""
        ),
        "the swatch given another value": lambda css: css.replace(
            '.player-swatch[data-state="maybe"] { background: var(--color-surface-hover); }',
            '.player-swatch[data-state="maybe"] { background: var(--grid-ink); }',
        ),
        # CARD-339's three, added with the glyph: a plant per hook that takes
        # the mark away, and one that changes what it draws. The first two are
        # the AC-1 reversion this class's messages name; the third is the look
        # drifting while the shape stays right, which is the defect shape the
        # whole Maybe mark arrived with.
        "the cell glyph deleted": lambda css: _without_rule(
            css, '.player-cell[data-state="maybe"]::after'
        ),
        "the swatch glyph deleted": lambda css: _without_rule(
            css, '.player-swatch[data-state="maybe"]::after'
        ),
        "the swatch glyph draws another mark": lambda css: css.replace(
            '.player-swatch[data-state="maybe"]::after { content: "?";',
            '.player-swatch[data-state="maybe"]::after { content: "!";',
        ),
    }

    @pytest.mark.parametrize("name", sorted(MUTANTS))
    def test_the_reading_reports_each_planted_defect(self, name: str) -> None:
        """The control (ADR-0039/R1): every plant changes the report.

        Asserted as a difference from the real sheet's report rather than
        against a hand-written expectation, so a plant that this reading
        cannot see fails here instead of being quietly tolerated.
        """
        css = PUBLIC_CSS.read_text(encoding="utf-8")
        mutated = self.MUTANTS[name](css)
        assert mutated != css, f"the plant {name!r} did not change the sheet"
        assert look_report(mutated) != look_report(css), name


# ==========================================================================
# AC-1, AC-3, AC-5 — the browser half
# ==========================================================================

#: The served module's own MAYBE, asked of the page rather than written here.
_MAYBE_IN_PAGE = "async () => (await import('/solver_state.js')).MAYBE"

#: What the module says one click with the Maybe brush does to a blank cell,
#: and what a second click does. Computed in the page by the shared module, so
#: a test that passed because "maybe" happened to be the attribute value would
#: still have to agree with ``clickedState``.
_MAYBE_SEQUENCE_IN_PAGE = """async () => {
  const m = await import('/solver_state.js');
  const seq = [];
  let state = m.UNKNOWN;
  for (let k = 0; k < 2; k++) { state = m.clickedState(state, m.MAYBE, k > 0); seq.push(state); }
  return seq;
}"""


@pytest.mark.browser
class TestPublicMaybe_TheBrushMarksACell:
    """AC-1 — with Maybe chosen, a click leaves the module's MAYBE.

    Two halves, because either alone passes for the wrong reason: the DOM
    carries ``data-state="maybe"`` (what a player sees) **and** the recorded
    history holds one stroke whose state is the value the shared module
    exports (what the save and undo/redo are built on). The expected states
    are computed by the served ``solver_state.js`` inside the page, following
    ``test_play_page_renders_and_marks``.
    """

    def test_choosing_maybe_and_clicking_marks_the_cell_and_records_one_stroke(
        self, browser_page, host
    ) -> None:
        page = browser_page
        _open(page, host, host[2]["min"])
        maybe = page.evaluate(_MAYBE_IN_PAGE)
        assert maybe == "maybe", maybe

        page.click('[data-player-tool="maybe"]')
        assert page.evaluate("() => window.publicPlayer.getTool()") == maybe

        _tap(page, 3, 4)
        assert _state(page, 3, 4) == maybe
        history = page.evaluate("() => window.publicPlayer.getHistory()")
        assert len(history["done"]) == 1, history["done"]
        stroke = history["done"][0]["stroke"]
        assert stroke["state"] == maybe, stroke
        assert [list(cell) for cell in stroke["cells"]] == [[3, 4]], stroke
        # Nothing else moved: the brush paints the cell it was clicked on.
        board = page.evaluate("() => window.publicPlayer.getBoard()")
        assert board["cells"].count(maybe) == 1, board["cells"].count(maybe)

    def test_the_brushs_click_sequence_is_the_modules(self, browser_page, host) -> None:
        """"? then blank" — and the module is what says so.

        The Maybe brush's sequence is its own (``MAYBE_ORDER``: "?" -> blank ->
        "?"), not the three colour brushes' dark -> white -> blank. A page that
        routed Maybe through the colour order would mark a *white* cell on the
        second click and pass any assertion that only read the first.
        """
        page = browser_page
        _open(page, host, host[2]["min"])
        expected = page.evaluate(_MAYBE_SEQUENCE_IN_PAGE)
        assert expected == ["maybe", "unknown"], expected
        page.click('[data-player-tool="maybe"]')
        for step, state in enumerate(expected):
            _tap(page, 1, 1)
            assert _state(page, 1, 1) == state, step

    def test_a_drag_with_the_maybe_brush_marks_its_whole_line(self, browser_page, host) -> None:
        """A drag is a separate path through ``play.js`` and takes the brush too.

        ``dragStroke`` never reads a click sequence, so "the brush decides the
        mark" is a second statement for drags, and the one EC-050's own review
        measured as reachable-but-unexercised for the three brushes already
        there.
        """
        from tests.test_public_player import _drag

        page = browser_page
        _open(page, host, host[2]["min"])
        page.click('[data-player-tool="maybe"]')
        _drag(page, [(6, 1), (6, 2), (6, 3)])
        assert [_state(page, 6, col) for col in (1, 2, 3)] == ["maybe"] * 3


#: How many draws the seeded walk takes per tool the page offers. Six rather
#: than one because the claim is about *transitions* between tools, and a walk
#: of one draw per tool cannot reach most of the ordered pairs.
_MIN_DRAWS_PER_TOOL = 6


@pytest.mark.browser
class TestPublicMaybe_OneToolIsCheckedAtATime:
    """AC-3 — the radio group still behaves with a fourth member in it.

    Exactly one ``aria-checked="true"`` at any time, and it is the brush last
    chosen. Driven over the page's **own** tool set — the markup is the
    authority for what exists (ADR-0039/R2) — first once per tool in order,
    then as a seeded walk, so a pair the fixed order never produces (Maybe
    after Maybe, Maybe after Clear) is still reached.
    """

    @staticmethod
    def _checked(page) -> list[str]:
        return page.evaluate(
            """() => [...document.querySelectorAll('[data-player-tool]')]
                 .filter((b) => b.getAttribute('aria-checked') === 'true')
                 .map((b) => b.dataset.playerTool)"""
        )

    def test_choosing_each_tool_leaves_exactly_that_one_checked(self, browser_page, host) -> None:
        page = browser_page
        _open(page, host, host[2]["min"])
        tools = tool_order(PUBLIC_PAGE.read_text(encoding="utf-8"))
        assert page.evaluate("() => document.querySelectorAll('[data-player-tool]').length") == len(
            tools
        )
        # At load, before anything is clicked.
        assert self._checked(page) == ["filled"], self._checked(page)

        previous = "filled"
        for tool in tools:
            page.click(f'[data-player-tool="{tool}"]')
            assert self._checked(page) == [tool], (tool, self._checked(page))
            assert page.evaluate("() => window.publicPlayer.getTool()") == tool
            if tool != previous:
                assert previous not in self._checked(page), (previous, tool)
            previous = tool

        # The AC's own sentence, as its own step: Maybe unchecks the previous.
        page.click('[data-player-tool="filled"]')
        assert self._checked(page) == ["filled"]
        page.click('[data-player-tool="maybe"]')
        assert self._checked(page) == ["maybe"], self._checked(page)

    def test_a_seeded_walk_over_the_tools_never_checks_two(self, browser_page, host) -> None:
        """The corpus. Its floor is the tool set's size, not a literal.

        ``_MIN_DRAWS_PER_TOOL`` draws per tool the page declares, and every
        tool asserted to have been drawn at least once — so the walk cannot
        quietly shrink to three tools' worth of clicks when a fourth exists,
        which is the shape this board's "corpus that silently shrank" rule is
        about.
        """
        page = browser_page
        _open(page, host, host[2]["min"])
        tools = tool_order(PUBLIC_PAGE.read_text(encoding="utf-8"))
        draws = _MIN_DRAWS_PER_TOOL * len(tools)
        rng = random.Random(323)
        seen: list[str] = []
        for _ in range(draws):
            tool = tools[rng.randrange(len(tools))]
            page.click(f'[data-player-tool="{tool}"]')
            seen.append(tool)
            assert self._checked(page) == [tool], (tool, self._checked(page))
        assert len(seen) == draws >= _MIN_DRAWS_PER_TOOL * len(tools)
        assert set(seen) == set(tools), sorted(set(tools) - set(seen))


#: The save's whole key set, and one stroke's, spelled out. Deliberately
#: literals and not read back out of ``play.js``: the thing under test IS
#: ``serialize``, and a set derived from it would grow with it — which is
#: exactly how the first version of this test came to pass against a planted
#: ``fingerprint`` field. Held the same way the served ``puzzle/<key>.json``
#: is held at the end of this class, and derived once from ``serialize``'s own
#: object literal (``player/play.js:216-223``) when written.
_SAVE_FIELDS = ["columns", "done", "height", "key", "rows", "undone", "v", "width"]
_STROKE_FIELDS = ["cells", "state"]


@pytest.mark.browser
class TestPublicMaybe_AReloadRestoresMaybeMarks:
    """AC-5 — a maybe mark survives the page's own save and a reload.

    The public save is ``play.js``'s own (``serialize`` / ``deserialize``), not
    ``solver_state.js``'s — those two fingerprint ``payload.solution`` and
    cannot be called from a page that has no solution — so the fourth state
    surviving it is a statement about *this file's* code and nothing inherited.

    The two ADR-0041/R2 assertions this card owes sit here, because the save is
    the only new data path a fourth brush touches at all.
    """

    def test_maybe_marks_come_back_after_a_reload(self, browser_page, host) -> None:
        page = browser_page
        url, _, keys = host
        key = keys["min"]
        _open(page, host, key)
        maybe = page.evaluate(_MAYBE_IN_PAGE)

        page.click('[data-player-tool="maybe"]')
        marked = [(0, 0), (2, 5), (7, 7)]
        for row, col in marked:
            _tap(page, row, col)
        # Asserted BEFORE the reload too: "they came back" is vacuous if they
        # were never there, and an empty board restores to an empty board.
        assert [_state(page, *cell) for cell in marked] == [maybe] * len(marked)
        saved = page.evaluate(
            "(k) => window.localStorage.getItem(k)", page.evaluate("() => window.publicPlayer.saveKey")
        )
        assert saved is not None and maybe in saved, saved

        page.goto(f"{url}/play/{key}")
        page.wait_for_function("window.publicPlayer !== undefined")
        assert [_state(page, *cell) for cell in marked] == [maybe] * len(marked)
        history = page.evaluate("() => window.publicPlayer.getHistory()")
        assert [entry["stroke"]["state"] for entry in history["done"]] == [maybe] * len(marked)
        # And it is still a live board, not a restored picture: undo takes the
        # last mark back, which only works if the history replayed as steps.
        page.click('[data-player-action="undo"]')
        assert _state(page, *marked[-1]) == "unknown"

    def test_the_save_gains_no_field_for_the_fourth_brush(self, browser_page, host) -> None:
        """ADR-0041/R2 — the fourth brush opens no channel in the save.

        A Maybe mark is the player's own note and is not derived from any
        solution (the page has none to derive from). What a guard can still
        check is that the save's **shape** did not grow, and it is checked in
        **two arms, in this order**:

        * the **closed** arm — the save's key set and a stroke's key set are
          held to the literals :data:`_SAVE_FIELDS` and :data:`_STROKE_FIELDS`.
          Any new field reds here, whatever its value and *however* it got in;
        * the **differential** arm — the Maybe save's shape against the Black
          save's. This is not the closure (two outputs of the same
          ``serialize`` call share any field added unconditionally, so this arm
          alone passes a planted ``fingerprint``, measured); it is what proves
          the literal above was matched against two **real** saves of the same
          puzzle rather than one save read twice.

        The round-1 review of CARD-323 measured the differential-only version:
        ``fingerprint: payload.key.length`` planted into ``serialize``'s object
        literal survived at 218 passed, 0 failed. The literals are what ends
        that, and the docstring no longer claims a closure the comparison does
        not have.
        """
        page = browser_page
        url, _, keys = host
        key = keys["min"]

        def save_after(tool: str) -> dict:
            page.goto(f"{url}/play/{key}")
            page.wait_for_function("window.publicPlayer !== undefined")
            page.evaluate(
                "(k) => window.localStorage.removeItem(k)",
                page.evaluate("() => window.publicPlayer.saveKey"),
            )
            page.goto(f"{url}/play/{key}")
            page.wait_for_function("window.publicPlayer !== undefined")
            page.click(f'[data-player-tool="{tool}"]')
            _tap(page, 4, 4)
            text = page.evaluate(
                "(k) => window.localStorage.getItem(k)",
                page.evaluate("() => window.publicPlayer.saveKey"),
            )
            assert text is not None, tool
            return json.loads(text)

        black = save_after("filled")
        with_maybe = save_after("maybe")
        # Arm one, the closed one. Both saves, so a field that only the fourth
        # brush's path adds and one that every path adds red alike.
        for tool, save in (("maybe", with_maybe), ("filled", black)):
            assert sorted(save) == _SAVE_FIELDS, (tool, sorted(save))
            assert sorted(save["done"][0]) == _STROKE_FIELDS, (tool, save["done"][0])
        # Arm two, the differential: the control for the comparison itself. It
        # is reading two real saves of the same puzzle — the stroke's state is
        # the one thing that differs, and everything else matches.
        assert with_maybe["done"][0]["state"] == "maybe" != black["done"][0]["state"], with_maybe
        assert {k: v for k, v in with_maybe.items() if k != "done"} == {
            k: v for k, v in black.items() if k != "done"
        }

    def test_the_fetched_puzzle_file_still_carries_only_what_the_page_reads(
        self, browser_page, host
    ) -> None:
        """ADR-0041/R2 / G-2 — this card adds no served field.

        Read from the file the page actually fetched, and held to the field set
        ``play.js``'s ``readPayload`` destructures — so a field added to the
        served schema for the fourth brush's sake would red here rather than
        wait for the tree sweep to notice it is undecodable.
        """
        page = browser_page
        url, report, keys = host
        key = keys["min"]
        _open(page, host, key)
        served = json.loads((report.site_dir / "puzzle" / f"{key}.json").read_text(encoding="utf-8"))
        assert sorted(served) == ["clues", "height", "key", "tier", "width"], sorted(served)
        assert sorted(served["clues"]) == ["columns", "rows"], sorted(served["clues"])
        fetched = page.evaluate(
            "async (k) => Object.keys(await (await fetch(`/puzzle/${k}.json`)).json()).sort()", key
        )
        assert fetched == sorted(served), (fetched, sorted(served))
        # And the page's own frozen payload holds nothing more than those.
        payload = page.evaluate("() => window.publicPlayer.payload")
        assert sorted(payload) == ["columns", "height", "key", "rows", "tier", "width"], sorted(payload)
