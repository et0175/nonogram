"""CARD-325 — the public player's crosshair: the one admin control that reads no board.

Hovering a cell on the admin player tints that cell's row, its column and
their two clue boxes (CARD-267). ``wireCrosshair`` in
``src/nonogram/admin/static/solver.js`` is **pure DOM over the stage**: no cell
state, no history, no clue data, no solution. That is why it is the easiest
admin control to bring to ``/play/<key>`` — and why this module's first job is
to *prove* it stayed that way here (AC-2), because ADR-0041/R2 forbids any
public asset from carrying a solution cell and a crosshair that read the board
would be a different feature with a different safety argument.

The duplication is the owner's recorded decision (2026-10-30): two UI layers,
not a shared one. ``tests/test_public_player_agreement.py`` is the check that
keeps it honest (AC-6, ``TestPlayerLooksAgree_TheCrosshairMakesTheSameDecisions``);
nothing here imports from ``src/``.

CARD-267's four recorded decisions, and where each is tested
------------------------------------------------------------
``solver.js`` records four decisions in its CROSSHAIR comment block and in
``wireCrosshair`` itself. They are followed, not rediscovered:

#. **the gutter corner** (and every non-cell point of the stage: a clue box,
   the stage's padding) *keeps the crosshair where it was*. Only leaving the
   stage clears it. -> ``TestPublicCrosshair_HoverHighlightsTheCross``
   (``test_a_clue_box_and_the_corner_keep_the_crosshair_where_it_was``) and, on
   the agreement side, AC-6.
#. **the no-hover phone case**: a touch crosshair follows the finger from
   ``pointerdown`` through every move and STAYS after the finger lifts, so it
   is seen between taps. -> ``TestPublicCrosshair_TouchIsNeverHalfPainted``
   and, for a drag in progress (AC-4's choice), ``TestPublicCrosshair_ADragKeepsTheDecision``.
#. **why an exempt touch**: a released touch pointer fires ``pointerleave``
   at once, so a leave handler that did not exempt touch would undo every touch
   crosshair at the moment it was made. The pointer TYPE is read in the leave
   handler and nowhere else. -> ``TestPublicCrosshair_TouchIsNeverHalfPainted``
   (the test records that the leave really fired, so the exemption is
   exercised and not assumed).
#. **a remembered position with nothing painted is the half-painted
   crosshair**: admin's ``redraw()`` calls ``forget()``. This page draws its
   table ONCE (``drawBoard`` has one call site) so there is no redraw to hook,
   and the divergence is declared in the agreement file. The refusal is kept
   by a different construction: the "already there" shortcut is taken only
   when the DOM still shows the cross painted, so a stale memory cannot
   suppress a repaint. -> ``test_a_remembered_position_with_nothing_painted_repaints``.

The gap this card closed: zoom (CARD-324) and scrolling (AC-7)
--------------------------------------------------------------
This card was written before zoom merged. Zoom rescales the stage, makes it
scroll on both axes and gives the pinch ownership of two-pointer input; no AC
said what the crosshair does there. The decision, stated once:

* The crosshair finds its cell with the **browser's hit test**
  (``document.elementFromPoint``), the same call marking uses, never with
  geometry it computes. A hit test is correct at every zoom and every scroll
  offset by construction; arithmetic over ``scrollLeft`` and the cell pitch is
  how a crosshair lands one cell off at 300%. AC-7 proves it at the zoom
  maximum and at a scrolled stage, and (landscape) a scrolled page.
* **Two or more touch/pen pointers down is a pinch, and a pinch has no
  crosshair**: none starts when the second finger lands (the first finger's
  ``pointerdown`` had already painted one, so it is taken off), none follows
  the fingers, and none is left when they lift. Crossing resumes at the next
  single pointer. This is decided on the crosshair's own count of pointers and
  reads none of ``play.js``'s pinch state, so it also covers two fingers that
  began on a clue box (which ``play.js`` leaves to the browser).
* ``touch-action`` stays ``auto`` (owner decision 2026-11-05): nothing here
  depends on it.
* No toolbar control is added, and nothing is persisted (CON-021).

Where each claim is answered
----------------------------
Tree tests read ``player/`` off disk; browser tests (``@pytest.mark.browser``)
own what only a real engine answers and refuse LOUDLY when Chromium is absent
(ADR-0038/R8) through CARD-160's own fixtures, imported by name.

Tests, by node id (FR-045, CARD-325's ACs)
------------------------------------------
Written out in full, one per line, because the architecture validator resolves
a check ref by a TEXT search for the whole ``path::name`` string.

* AC-1 — ``tests/test_public_player_crosshair.py::TestPublicCrosshair_HoverHighlightsTheCross``
* AC-2 — ``tests/test_public_player_crosshair.py::TestPublicCrosshair_ItReadsNoBoard``
* AC-3 — ``tests/test_public_player_crosshair.py::TestPublicCrosshair_HoverRecordsNoStroke``
* AC-4 — ``tests/test_public_player_crosshair.py::TestPublicCrosshair_ADragKeepsTheDecision``
* AC-5 — ``tests/test_public_player_crosshair.py::TestPublicCrosshair_TouchIsNeverHalfPainted``
* AC-6 — ``tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheCrosshairMakesTheSameDecisions``
* AC-7 (added by this card, the zoom gap) — ``tests/test_public_player_crosshair.py::TestPublicCrosshair_ItLandsOnTheCellUnderThePointerWhenZoomedAndScrolled``
"""

from __future__ import annotations

import re

import pytest

from tests.test_public_player import (  # noqa: F401 — fixtures used by name
    GRIDS,
    PLAYER_DIR,
    _cell_centre,
    _drag,
    _filled_cells,
    _open,
    _pen_drag,
    _prefill,
    _save,
    _state,
    _touch_drag,
    browser_type,
    bundle,
    host,
    site,
)
from tests.test_public_player_zoom import (  # noqa: F401
    LANDSCAPE,
    PHONE,
    SETTLE_MS,
    _bounds,
    _open_max,
    _percent,
    _press,
    _solve_state,
    _touch,
)

import tests.test_puzzle_solver_page as _solver_page

PLAY_JS = PLAYER_DIR / "play.js"
PLAYER_CSS = PLAYER_DIR / "player.css"
PLAY_HTML = PLAYER_DIR / "play.html"

@pytest.fixture
def browser_page(request):
    """This module's own ``browser_page``: CARD-160's, plus a ``pageerror`` collector.

    Review cycle 1 (F-5): an exception thrown inside a crosshair handler is
    swallowed by the browser, so a mutant whose ``moveTo(null)`` throws
    (no null guard) looked green. Every uncaught page exception now fails the
    test that provoked it (at teardown, which pytest reports as that test's
    ERROR). Deliberately NOT in the shared fixtures other modules use. The
    loud refusal when Chromium is absent (ADR-0038/R8) is kept verbatim.
    """
    try:
        import pytest_playwright  # noqa: F401
    except ImportError:
        pytest.fail(_solver_page._PLAYWRIGHT_MISSING, pytrace=False)
    page = request.getfixturevalue("page")
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    yield page
    assert errors == [], f"the page threw: {errors}"


# --------------------------------------------------------------------------
# Reading the source: a small, honest JS reader
# --------------------------------------------------------------------------
#
# AC-2 is a claim about SOURCE TEXT ("references no cell state, no history,
# no clue data and no payload field"), so it is answered by reading the
# source, structurally. No JS parser is in the dependency baseline, so this is
# a deliberately small scanner: it blanks comments and string CONTENTS (kept
# aside to be checked as strings), keeps template ``${...}`` expressions as
# code, brace-matches a named definition and lists the identifiers that
# definition uses without declaring. It is DEFAULT-DENY (ADR-0039/R2): a free
# reference is an error unless it is on a short allowlist, so a reference to a
# name nobody thought to ban is still refused.


def _scan(src: str) -> tuple[str, list[str]]:
    """``(code, strings)``: ``src`` without comments, string bodies emptied."""
    code: list[str] = []
    strings: list[str] = []
    i, n = 0, len(src)
    while i < n:
        ch = src[i]
        if src.startswith("//", i):
            while i < n and src[i] != "\n":
                i += 1
        elif src.startswith("/*", i):
            i = src.index("*/", i) + 2
        elif ch in "'\"":
            j, buf = i + 1, []
            while src[j] != ch:
                if src[j] == "\\":
                    buf.append(src[j : j + 2])
                    j += 2
                    continue
                buf.append(src[j])
                j += 1
            strings.append("".join(buf))
            code.append(ch + ch)
            i = j + 1
        elif ch == "`":
            j, buf = i + 1, []
            code.append("``")
            while src[j] != "`":
                if src[j] == "\\":
                    buf.append(src[j : j + 2])
                    j += 2
                    continue
                if src.startswith("${", j):
                    depth, k = 1, j + 2
                    while depth:
                        depth += {"{": 1, "}": -1}.get(src[k], 0)
                        k += 1
                    code.append(" " + src[j + 2 : k - 1] + " ")
                    buf.append("${}")
                    j = k
                    continue
                buf.append(src[j])
                j += 1
            strings.append("".join(buf))
            i = j + 1
        else:
            code.append(ch)
            i += 1
    return "".join(code), strings


def _matching(text: str, start: int, opener: str, closer: str) -> int:
    depth = 0
    for index in range(start, len(text)):
        if text[index] == opener:
            depth += 1
        elif text[index] == closer:
            depth -= 1
            if depth == 0:
                return index
    raise AssertionError(f"unbalanced {opener}{closer} from {start}")


def definition(code: str, name: str) -> str | None:
    """The top-level definition of ``name`` (function or const arrow), or None."""
    fn = re.search(rf"(?m)^(?:export\s+)?function\s+{re.escape(name)}\s*\(", code)
    if fn is not None:
        params_end = _matching(code, code.index("(", fn.start()), "(", ")")
        body_start = code.index("{", params_end)
        return code[fn.start() : _matching(code, body_start, "{", "}") + 1]
    const = re.search(rf"(?m)^const\s+{re.escape(name)}\s*=", code)
    if const is not None:
        arrow = code.index("=>", const.end())
        after = code[arrow + 2 :].lstrip()
        if after.startswith("{"):
            open_at = code.index("{", arrow)
            return code[const.start() : _matching(code, open_at, "{", "}") + 1]
        return code[const.start() : code.index(";", arrow) + 1]
    return None


_KEYWORDS = frozenset(
    "const let var function return if else for of in while do break continue new typeof instanceof "
    "this null undefined true false throw try catch finally switch case default void delete await async "
    "class extends super yield".split()
)


def free_references(body: str) -> set[str]:
    """Identifiers ``body`` uses and does not declare (properties excluded)."""
    declared: set[str] = set()
    ident = r"[A-Za-z_$][\w$]*"
    for m in re.finditer(rf"\b(?:const|let|var)\s+({ident})", body):
        declared.add(m.group(1))
    for m in re.finditer(r"\b(?:const|let|var)\s*\[([^\]]*)\]", body):
        declared.update(re.findall(ident, m.group(1)))
    for m in re.finditer(rf"\bfunction\s+({ident})\s*\(([^)]*)\)", body):
        declared.add(m.group(1))
        declared.update(re.findall(ident, m.group(2)))
    for m in re.finditer(r"\(([^()]*)\)\s*=>", body):
        declared.update(re.findall(ident, m.group(1)))
    for m in re.finditer(rf"(?<![\w$)])({ident})\s*=>", body):
        declared.add(m.group(1))
    used = set(re.findall(rf"(?<![\w$.]){ident}", body))
    return used - declared - _KEYWORDS


#: The functions the crosshair IS: its wiring, the selector helper it paints
#: through, and the two DOM-only helpers it shares with marking. A reference
#: from one of these into any other top-level name is outside the claim.
CROSSHAIR_SOURCE = ("wireCrosshair", "crossedParts", "cellUnder", "isAt")

#: What the crosshair may use without declaring: the DOM, a number cast, a map
#: of pointer ids to types, and its own members. Everything else is refused.
ALLOWED_FREE = frozenset({"document", "Number", "Map", *CROSSHAIR_SOURCE})

#: The ONLY properties and methods the crosshair may read or call, default-deny
#: (ADR-0039/R2; review cycle 1 F-1: a blacklist let ``.attributes``,
#: ``.className``, ``classList.contains``, ``getAttribute``, ``getAttributeNames``,
#: ``.children`` and ``.nextElementSibling`` through, each a way to read what a
#: cell or clue box says without naming state). Derived from what the four
#: functions really use: the pointer event's position, type and id; a hit test;
#: a selector query; ``closest``; toggling the one marker class; a set of ids;
#: and the cell's ``data-row`` / ``data-col`` (``dataset`` keys are checked
#: separately). A new need is a one-word addition here, which is the point.
ALLOWED_PROPERTIES = frozenset(
    {"addEventListener", "querySelector", "querySelectorAll", "closest", "classList", "toggle",
     "elementFromPoint", "dataset", "row", "col", "clientX", "clientY", "pointerType",
     "isPrimary", "pointerId", "set", "delete", "clear", "size"}
)

#: ``data-*`` attributes the crosshair may name: positions, never state.
ALLOWED_DATA_ATTRIBUTES = frozenset({"data-row", "data-col", "data-line"})

#: Substrings no selector string may contain: the cell state, the clue
#: numerals, and anything that names a solution.
FORBIDDEN_STRING_PARTS = ("data-state", "player-clue-num", "solution", "state", "unknown", "filled")


def crosshair_violations(js_source: str) -> list[str]:
    """Every way ``js_source``'s crosshair reads something it must not."""
    code, _ = _scan(js_source)
    problems: list[str] = []
    for name in CROSSHAIR_SOURCE:
        if definition(code, name) is None:
            problems.append(f"{name}: not defined")
    stripped_definitions = {n: definition(code, n) for n in CROSSHAIR_SOURCE}
    raw = {n: _raw_definition(js_source, n) for n in CROSSHAIR_SOURCE}
    for name, body in stripped_definitions.items():
        if body is None:
            continue
        for ref in sorted(free_references(body) - ALLOWED_FREE):
            problems.append(f"{name}: free reference {ref!r}")
        # A spread (``...x``) is not a property read, hence the lookarounds.
        for prop in sorted(set(re.findall(r"(?<!\.)\.(?!\.)\s*([A-Za-z_$][\w$]*)", body)) - ALLOWED_PROPERTIES):
            problems.append(f"{name}: property {prop!r}")
        # A computed member (``el["attributes"]``, ``el[key]``) names its
        # property at run time and cannot be allowlisted; only a numeric index
        # (isAt's ``a[0]``) is read.
        if re.search(r"[\w$)\]]\[(?!\s*\d+\s*\])", body):
            problems.append(f"{name}: computed member access")
        for key in re.findall(r"\.dataset\s*\.\s*([A-Za-z_$][\w$]*)", body):
            if key not in {"row", "col", "line"}:
                problems.append(f"{name}: dataset.{key}")
    for name, text in raw.items():
        if text is None:
            continue
        _, strings = _scan(text)
        for string in strings:
            for part in FORBIDDEN_STRING_PARTS:
                if part in string:
                    problems.append(f"{name}: string {string!r} names {part!r}")
            for attribute in re.findall(r"data-[a-z-]+", string):
                if attribute not in ALLOWED_DATA_ATTRIBUTES:
                    problems.append(f"{name}: string {string!r} names {attribute!r}")
    return problems


def _raw_definition(js_source: str, name: str) -> str | None:
    """``name``'s definition from the comment-stripped but string-KEEPING text."""
    # Comments are removed by a pass that leaves strings alone, so the
    # definition can be located and its strings read.
    out: list[str] = []
    i, n = 0, len(js_source)
    while i < n:
        ch = js_source[i]
        if js_source.startswith("//", i):
            while i < n and js_source[i] != "\n":
                i += 1
        elif js_source.startswith("/*", i):
            i = js_source.index("*/", i) + 2
        elif ch in "'\"`":
            j = i + 1
            while js_source[j] != ch:
                j += 2 if js_source[j] == "\\" else 1
            out.append(js_source[i : j + 1])
            i = j + 1
        else:
            out.append(ch)
            i += 1
    text = "".join(out)
    return definition(text, name)


def _plant(js_source: str, statement: str) -> str:
    """``js_source`` with ``statement`` as the first line of wireCrosshair's body."""
    head = re.search(r"(?m)^function\s+wireCrosshair\s*\([^)]*\)\s*\{", js_source)
    assert head is not None, "wireCrosshair is not defined"
    return js_source[: head.end()] + f"\n  {statement}\n" + js_source[head.end() :]


# --------------------------------------------------------------------------
# Reading the page
# --------------------------------------------------------------------------


def _dims(page) -> tuple[int, int]:
    """``(height, width)`` of the drawn board, from the DOM."""
    return tuple(
        page.evaluate(
            "() => [document.querySelectorAll('tbody tr').length,"
            " document.querySelectorAll('thead th.is-col').length]"
        )
    )


def _crossed(page) -> dict:
    """Everything carrying ``.is-crossed``, sorted into kinds."""
    return page.evaluate(
        """() => {
          const marked = [...document.querySelectorAll('.is-crossed')];
          const of = (selector) => marked.filter((el) => el.matches(selector));
          const line = (el) => Number(el.dataset.line);
          return {
            cells: of('td.player-cell').map((el) => [Number(el.dataset.row), Number(el.dataset.col)]),
            rowClues: of('th.player-clue.is-row').map(line),
            colClues: of('th.player-clue.is-col').map(line),
            other: marked.length
              - of('td.player-cell').length - of('th.player-clue.is-row').length
              - of('th.player-clue.is-col').length,
          };
        }"""
    )


def _cross_of(height: int, width: int, row: int, col: int) -> dict:
    cells = {(row, c) for c in range(width)} | {(r, col) for r in range(height)}
    return {"cells": sorted(cells), "rowClues": [row], "colClues": [col], "other": 0}


def _normalised(reading: dict) -> dict:
    return {
        "cells": sorted(tuple(c) for c in reading["cells"]),
        "rowClues": sorted(reading["rowClues"]),
        "colClues": sorted(reading["colClues"]),
        "other": reading["other"],
    }


NOTHING = {"cells": [], "rowClues": [], "colClues": [], "other": 0}


def _assert_crossed_at(page, row: int, col: int) -> None:
    height, width = _dims(page)
    assert _normalised(_crossed(page)) == _cross_of(height, width, row, col), (row, col)


def _assert_nothing_crossed(page) -> None:
    assert _normalised(_crossed(page)) == NOTHING


def _full_or_none(page):
    """The AC-5 invariant, as a probe: a COMPLETE cross or nothing at all.

    Returns ``(row, col)`` of the cross, or ``None``. Anything between — a
    row without its column, a cell without its clue, a lone clue box — fails.
    """
    height, width = _dims(page)
    reading = _normalised(_crossed(page))
    if reading == NOTHING:
        return None
    assert len(reading["rowClues"]) == 1 and len(reading["colClues"]) == 1, f"half a cross: {reading}"
    row, col = reading["rowClues"][0], reading["colClues"][0]
    assert reading == _cross_of(height, width, row, col), f"half a cross: {reading}"
    return row, col


def _centre_in_stage(page, row: int, col: int) -> None:
    """Scroll the stage so the cell is as near its middle as the range allows.

    A cell below the fold or behind a sticky gutter cannot be pointed at, and a
    test that points at the wrong place reads "no crosshair" as a failure of
    the crosshair. Only the stage's own scroll is touched, which is the thing
    a pointer cannot do for itself.
    """
    page.evaluate(
        """([row, col]) => {
          const stage = document.querySelector('[data-player-stage]');
          const cell = stage.querySelector(`td[data-row="${row}"][data-col="${col}"]`).getBoundingClientRect();
          const box = stage.getBoundingClientRect();
          stage.scrollLeft += (cell.left + cell.width / 2) - (box.left + box.width / 2);
          stage.scrollTop += (cell.top + cell.height / 2) - (box.top + box.height / 2);
        }""",
        [row, col],
    )


def _move(page, row: int, col: int) -> None:
    _centre_in_stage(page, row, col)
    page.mouse.move(*_cell_centre(page, row, col))


def _move_off_the_stage(page) -> None:
    page.mouse.move(2, 2)


def _box_centre(page, selector: str):
    box = page.query_selector(selector).bounding_box()
    return box["x"] + box["width"] / 2, box["y"] + box["height"] / 2


def _touch_tap(page, row: int, col: int, *, end: str = "touchEnd") -> None:
    session = page.context.new_cdp_session(page)
    try:
        x, y = _cell_centre(page, row, col)
        _touch(session, "touchStart", [(x, y)])
        _touch(session, end, [])
    finally:
        session.detach()
    page.wait_for_timeout(SETTLE_MS)


def _record_leaves(page) -> None:
    """Record every ``pointerleave`` the stage sees, with its pointer type."""
    page.evaluate(
        """() => {
          window.__leaves = [];
          document.querySelector('[data-player-stage]').addEventListener(
            'pointerleave', (e) => window.__leaves.push(e.pointerType));
        }"""
    )


def _leaves(page) -> list[str]:
    return page.evaluate("() => window.__leaves")


# ==========================================================================
# AC-1 — hover highlights the cross
# ==========================================================================


@pytest.mark.browser
class TestPublicCrosshair_HoverHighlightsTheCross:
    """AC-1, and CARD-267's first decision (the gutter corner)."""

    @pytest.mark.parametrize(
        "where",
        ["top-left", "top-right", "bottom-left", "bottom-right", "inside"],
    )
    def test_hovering_a_cell_marks_its_row_its_column_and_both_clues(self, browser_page, host, where) -> None:
        """The oblong board (25 wide, 15 tall), so a row/column swap shows.

        The four corners are the edge cases: a clue picked by DOM order, or
        an off-by-one at the first or last line, lights the wrong box exactly
        there. Expected markers are built from the cell's own coordinates and
        the board's measured dimensions, never from the page's answer.
        """
        page = browser_page
        _open(page, host, host[2]["oblong"])
        height, width = _dims(page)
        assert (height, width) == (15, 25)
        row, col = {
            "top-left": (0, 0),
            "top-right": (0, width - 1),
            "bottom-left": (height - 1, 0),
            "bottom-right": (height - 1, width - 1),
            "inside": (4, 11),
        }[where]
        _assert_nothing_crossed(page)
        _move(page, row, col)
        _assert_crossed_at(page, row, col)

    def test_the_crosshair_follows_the_pointer_and_only_one_cross_exists(self, browser_page, host) -> None:
        page = browser_page
        _open(page, host, host[2]["oblong"])
        for row, col in [(2, 3), (2, 4), (9, 4), (0, 0), (14, 24), (14, 0)]:
            _move(page, row, col)
            _assert_crossed_at(page, row, col)

    def test_leaving_the_stage_clears_every_marker(self, browser_page, host) -> None:
        page = browser_page
        _open(page, host, host[2]["oblong"])
        _move(page, 6, 6)
        assert _full_or_none(page) == (6, 6)
        _move_off_the_stage(page)
        _assert_nothing_crossed(page)

    def test_a_clue_box_and_the_corner_keep_the_crosshair_where_it_was(self, browser_page, host) -> None:
        """CARD-267's first decision: looking from a cell to its clue must not
        put the line out. A clue box, the gutter corner and the stage's own
        padding are all points on the stage that are not a cell."""
        page = browser_page
        _open(page, host, host[2]["oblong"])
        _move(page, 5, 7)
        _assert_crossed_at(page, 5, 7)
        for selector in (
            'th.player-clue.is-row[data-line="5"]',
            'th.player-clue.is-col[data-line="7"]',
            'th.player-clue.is-row[data-line="12"]',  # a clue of ANOTHER line lights nothing
            "th.player-clue.is-corner",
        ):
            page.mouse.move(*_box_centre(page, selector))
            _assert_crossed_at(page, 5, 7)
        # ...and the stage's own border-box edge, which is not a cell either.
        box = page.query_selector("[data-player-stage]").bounding_box()
        page.mouse.move(box["x"] + 0.5, box["y"] + 0.5)
        _assert_crossed_at(page, 5, 7)


# ==========================================================================
# AC-2 — the crosshair reads no board (structural)
# ==========================================================================


class TestPublicCrosshair_ItReadsNoBoard:
    """AC-2, asserted over the SOURCE, default-deny, with controls that can fail."""

    def test_the_crosshair_is_defined_and_wired_to_the_stage_alone(self) -> None:
        source = PLAY_JS.read_text(encoding="utf-8")
        code, _ = _scan(source)
        for name in CROSSHAIR_SOURCE:
            assert definition(code, name) is not None, f"{name} is not defined in play.js"
        calls = re.findall(r"\bwireCrosshair\s*\(([^)]*)\)", code)
        # The definition's own `function wireCrosshair(stage)` is one match;
        # the call in start() is the other, and BOTH name the stage only.
        assert calls and all(c.strip() == "stage" for c in calls), calls
        assert len(calls) == 2, f"expected the definition and exactly one call: {calls}"

    def test_it_references_no_cell_state_history_clue_data_or_payload_field(self) -> None:
        """The shipped crosshair uses nothing outside a short allowlist.

        Default-deny over FREE references (a name the crosshair uses and does
        not declare), over property reads, over ``dataset`` keys and over the
        selector strings it builds. A name nobody thought to ban —
        ``history``, ``payload``, ``shown``, ``board``, ``cells``,
        ``isClueSolved``, ``localStorage``, ``fetch`` — is refused because it
        is not on the list, not because it is on another.
        """
        assert crosshair_violations(PLAY_JS.read_text(encoding="utf-8")) == []

    @pytest.mark.parametrize(
        "plant",
        [
            "const h = history.done;",
            "const p = payload.rows;",
            "const s = shown.cells[0];",
            "const b = board;",
            "const c = cells[0];",
            "const k = isClueSolved(history.board, payload.rows, payload.columns);",
            "const n = window.publicPlayer.getBoard();",
            "const g = localStorage.getItem('k');",
            "fetch('/x');",
            "const t = stage.querySelector('.player-clue').textContent;",
            "const d = stage.querySelector('td').dataset.state;",
            "const q = stage.querySelector('[data-state=\"filled\"]');",
            "const z = stage.querySelector('.player-clue-num');",
            "const a = stage.querySelector('[data-answer]');",
            "const u = UNKNOWN;",
            "const m = strokeOf(null, 1, 1);",
            "const f1 = stage.attributes;",
            "const f2 = stage.className;",
            "const f3 = stage.classList.contains('is-solved');",
            "const f4 = stage.getAttribute('data-' + 'st' + 'ate');",
            "const f5 = stage.getAttributeNames();",
            "const f6 = stage.children[0];",
            "const f7 = stage.nextElementSibling;",
            "const f8 = stage['attri' + 'butes'];",
        ],
        ids=[
            "history", "payload", "shown", "board", "cells", "isClueSolved", "publicPlayer",
            "localStorage", "fetch", "clue-text", "dataset-state", "data-state-selector",
            "clue-numeral", "unlisted-data-attribute", "UNKNOWN", "strokeOf",
            "attributes", "className", "classList-contains", "getAttribute-concatenated",
            "getAttributeNames", "children", "nextElementSibling", "computed-member",
        ],
    )
    def test_a_planted_reference_is_reported(self, plant) -> None:
        """The control CAN fail: each plant goes into the real source's
        wireCrosshair and the real source, unplanted, is clean in this run."""
        source = PLAY_JS.read_text(encoding="utf-8")
        assert crosshair_violations(source) == [], "the matched control: the shipped source is clean"
        assert crosshair_violations(_plant(source, plant)) != [], plant

    def test_a_reference_in_a_shared_helper_is_reported_too(self) -> None:
        """``cellUnder`` and ``isAt`` are shared with marking; the claim covers them."""
        source = PLAY_JS.read_text(encoding="utf-8")
        needle = 'return cell ? [Number(cell.dataset.row), Number(cell.dataset.col)] : null;'
        assert source.count(needle) == 1
        planted = source.replace(needle, "return cell ? [Number(cell.dataset.state), Number(cell.dataset.col)] : null;")
        assert crosshair_violations(planted) != []

    def test_no_network_request_and_no_external_reference_is_added(self) -> None:
        """ADR-0038/R2 and the page's no-third-party rule, over the whole file:
        the puzzle file's one ``fetch`` is the only one, and the crosshair's
        own source has none (the default-deny test above holds the second)."""
        code, strings = _scan(PLAY_JS.read_text(encoding="utf-8"))
        assert len(re.findall(r"\bfetch\s*\(", code)) == 1
        for banned in ("XMLHttpRequest", "sendBeacon", "WebSocket", "EventSource", "importScripts"):
            assert banned not in code
        assert not [s for s in strings if re.search(r"https?://|//cdn|analytics", s)]
        css = PLAYER_CSS.read_text(encoding="utf-8")
        assert not re.search(r"url\(\s*['\"]?(?:https?:)?//", css)
        assert not re.search(r"@import", css)


# ==========================================================================
# AC-3 — it paints nothing
# ==========================================================================


def _everything_but_the_crosshair(page) -> dict:
    """Every attribute of every board element, with ``.is-crossed`` taken
    out of the class list, plus the history and the save."""
    return page.evaluate(
        """() => {
          const strip = (el) => ({
            tag: el.tagName,
            attrs: Object.fromEntries([...el.attributes].map((a) => [
              a.name,
              a.name === 'class'
                ? a.value.split(/\\s+/).filter((c) => c !== 'is-crossed').join(' ')
                : a.value])),
          });
          const done = window.publicPlayer.getHistory();
          return {
            elements: [...document.querySelectorAll('.player-board, .player-board *')].map(strip),
            done: done.done.length, undone: done.undone.length,
            save: localStorage.getItem(window.publicPlayer.saveKey),
            solved: document.body.dataset.solved,
          };
        }"""
    )


@pytest.mark.browser
class TestPublicCrosshair_HoverRecordsNoStroke:
    """AC-3."""

    def test_pointer_movement_across_the_whole_board_changes_nothing_but_the_marker(
        self, browser_page, host
    ) -> None:
        page = browser_page
        grid = GRIDS["min"]
        key = host[2]["min"]
        text = _save(key, grid, _filled_cells(grid)[:3])
        _prefill(page, host, key, text)
        before = _everything_but_the_crosshair(page)
        assert before["done"] == 1 and before["save"] is not None, "the save must be non-trivial"
        height, width = _dims(page)
        for row in range(height):
            for col in range(width):
                _move(page, row, col)
                assert _full_or_none(page) == (row, col)
        page.mouse.move(*_box_centre(page, "th.player-clue.is-corner"))
        _move_off_the_stage(page)
        _assert_nothing_crossed(page)
        assert _everything_but_the_crosshair(page) == before

    def test_the_save_and_the_history_survive_a_reload_untouched_by_hovering(self, browser_page, host) -> None:
        page = browser_page
        key = host[2]["min"]
        _open(page, host, key)
        _move(page, 1, 1)
        assert page.evaluate("(k) => localStorage.getItem(k)", f"nonogram-public:{key}") is None
        assert page.evaluate("() => window.publicPlayer.getHistory().done.length") == 0

    def test_hovering_makes_no_request(self, browser_page, host) -> None:
        """ADR-0038/R2 for the crosshair: nothing leaves the page, no analytics."""
        page = browser_page
        _open(page, host, host[2]["min"])
        seen: list[str] = []
        page.on("request", lambda request: seen.append(request.url))
        height, width = _dims(page)
        for row in range(height):
            for col in range(width):
                _move(page, row, col)
        _move_off_the_stage(page)
        _touch_tap(page, 0, 0)
        assert seen == [], seen


# ==========================================================================
# AC-4 — the drag case
# ==========================================================================


@pytest.mark.browser
class TestPublicCrosshair_ADragKeepsTheDecision:
    """AC-4: **which of CARD-267's four decisions applies to a drag.**

    The second one — *the cell under the pointer, from ``pointerdown`` and
    through every move of the gesture* (the touch/no-hover case), together with
    the rule it shares with the mouse: a gesture is crossed **from the moment
    it starts**, and the crosshair follows the dragged-over cell. It does not
    freeze at the cell the drag began on and it does not wait for the first
    move. Marking is untouched: the drag still records the one stroke it
    recorded before.
    """

    def test_a_mouse_drag_is_crossed_at_every_cell_it_visits_and_still_marks(self, browser_page, host) -> None:
        page = browser_page
        _open(page, host, host[2]["oblong"])
        path = [(3, 2), (3, 3), (3, 4), (3, 5)]
        page.mouse.move(*_cell_centre(page, *path[0]))
        page.mouse.down()
        _assert_crossed_at(page, *path[0])
        for cell in path[1:]:
            page.mouse.move(*_cell_centre(page, *cell))
            _assert_crossed_at(page, *cell)
        page.mouse.up()
        # Released while still over the stage: the crosshair is where the
        # pointer is, and the drag it accompanied marked exactly its path.
        _assert_crossed_at(page, *path[-1])
        assert page.evaluate("() => window.publicPlayer.getHistory().done.length") == 1
        assert [_state(page, r, c) for r, c in path] == ["filled"] * len(path)

    def test_a_press_alone_crosses_the_cell_before_any_move(self, browser_page, host) -> None:
        """The edge the card's `pointerdown` clause exists for. A touch has no
        hover move before its press, so the press must do it."""
        page = browser_page
        _open(page, host, host[2]["oblong"])
        _touch_tap(page, 7, 9)
        _assert_crossed_at(page, 7, 9)

    def test_a_pen_drag_follows_the_pen_across_the_board(self, browser_page, host) -> None:
        """Pen with Region off reaches the whole drag branch (see _pen_drag)."""
        page = browser_page
        _open(page, host, host[2]["oblong"])
        _pen_drag(page, [(2, 2), (2, 3), (4, 3)])
        _assert_crossed_at(page, 4, 3)

    def test_a_touch_drag_leaves_the_cross_on_the_last_cell_it_reached(self, browser_page, host) -> None:
        page = browser_page
        _open(page, host, host[2]["oblong"])
        _touch_drag(page, [(5, 5), (5, 6), (5, 7)])
        page.wait_for_timeout(SETTLE_MS)
        position = _full_or_none(page)
        assert position is not None, "a touch drag left no crosshair at all"
        assert position[0] == 5 and position[1] in (5, 6, 7), position

    def test_a_drag_that_ends_off_the_stage_with_a_mouse_clears_the_cross(self, browser_page, host) -> None:
        """Only leaving the stage clears (decision 1), and a mouse drag
        released outside it has left."""
        page = browser_page
        _open(page, host, host[2]["oblong"])
        page.mouse.move(*_cell_centre(page, 3, 3))
        page.mouse.down()
        page.mouse.move(*_cell_centre(page, 3, 4))
        _move_off_the_stage(page)
        page.mouse.up()
        _assert_nothing_crossed(page)


# ==========================================================================
# AC-5 — no hover, no half-crosshair
# ==========================================================================


@pytest.mark.browser
class TestPublicCrosshair_TouchIsNeverHalfPainted:
    """AC-5, and decisions 2, 3 and 4."""

    @pytest.mark.parametrize("end", ["touchEnd", "touchCancel"])
    def test_a_touch_crosshair_stays_after_the_finger_lifts(self, browser_page, host, end) -> None:
        """Decisions 2 and 3. The leave is recorded so the exemption is
        EXERCISED: a test in which no leave fired would pass a handler that
        cleared on every leave."""
        page = browser_page
        _open(page, host, host[2]["oblong"])
        _record_leaves(page)
        _touch_tap(page, 8, 10, end=end)
        assert "touch" in _leaves(page), "the touch pointer never left the stage, so the exemption was not exercised"
        _assert_crossed_at(page, 8, 10)

    def test_a_second_tap_moves_the_cross_and_leaves_only_one(self, browser_page, host) -> None:
        page = browser_page
        _open(page, host, host[2]["oblong"])
        _touch_tap(page, 1, 1)
        _touch_tap(page, 12, 20)
        _assert_crossed_at(page, 12, 20)

    def test_a_mouse_leave_still_clears_what_a_touch_leave_does_not(self, browser_page, host) -> None:
        """The exemption is for touch ONLY: the same board, a mouse pointer."""
        page = browser_page
        _open(page, host, host[2]["oblong"])
        _move(page, 8, 10)
        _assert_crossed_at(page, 8, 10)
        _move_off_the_stage(page)
        _assert_nothing_crossed(page)

    def test_full_or_none_holds_at_every_step_of_a_mixed_session(self, browser_page, host) -> None:
        page = browser_page
        _open(page, host, host[2]["oblong"])
        steps = [
            lambda: _move(page, 3, 3),
            lambda: page.mouse.move(*_box_centre(page, "th.player-clue.is-corner")),
            lambda: _touch_tap(page, 10, 20),
            lambda: _move(page, 0, 24),
            lambda: _move_off_the_stage(page),
            lambda: _touch_tap(page, 14, 0, end="touchCancel"),
            lambda: page.mouse.down(),
            lambda: page.mouse.up(),
            lambda: _press(page, "in"),
            lambda: _press(page, "out"),
        ]
        for step in steps:
            step()
            _full_or_none(page)

    def test_a_remembered_position_with_nothing_painted_repaints(self, browser_page, host) -> None:
        """Decision 4, by CONSTRUCTION: strip the markers behind the crosshair's
        back (what a redraw would do) and move onto the very cell it remembers.
        The shortcut "already there, do nothing" would leave the board with a
        position remembered and nothing painted; it must paint afresh."""
        page = browser_page
        _open(page, host, host[2]["oblong"])
        _move(page, 6, 6)
        _assert_crossed_at(page, 6, 6)
        page.evaluate(
            "() => document.querySelectorAll('.is-crossed').forEach((el) => el.classList.remove('is-crossed'))"
        )
        _assert_nothing_crossed(page)
        x, y = _cell_centre(page, 6, 6)
        page.mouse.move(x + 1, y + 1)
        _assert_crossed_at(page, 6, 6)

    def test_the_rules_do_not_depend_on_hover(self) -> None:
        """A no-hover device never matches :hover, so a crosshair drawn by it
        would be a half-painted one. The crosshair is a class the script sets."""
        css = PLAYER_CSS.read_text(encoding="utf-8")
        rules = re.findall(r"([^{}]*is-crossed[^{}]*)\{", re.sub(r"/\*.*?\*/", "", css, flags=re.S))
        assert rules, "no crosshair rule found"
        assert not [r for r in rules if ":hover" in r or ":focus" in r]
        code, _ = _scan(PLAY_JS.read_text(encoding="utf-8"))
        assert definition(code, "wireCrosshair") is not None


# ==========================================================================
# The look: from tokens, distinct from the Maybe cell
# ==========================================================================


def _declarations_of(css: str, needle: str) -> list[tuple[str, str]]:
    plain = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    found = []
    for selector, body in re.findall(r"([^{}]+)\{([^{}]*)\}", plain):
        if needle in selector:
            found.extend((selector.strip(), d.strip()) for d in body.split(";") if d.strip())
    return found


class TestPublicCrosshair_TheLookIsTokensOnly:
    """G-6. Every crosshair value is a design token or a token-only color-mix."""

    def test_every_crosshair_value_is_a_token(self) -> None:
        css = PLAYER_CSS.read_text(encoding="utf-8")
        rules = _declarations_of(css, "is-crossed") + [
            (selector, declaration)
            for selector, declaration in _declarations_of(css, "")
            if declaration.startswith("--player-cross")
        ]
        assert len(rules) >= 5, rules  # three rules, two derived values
        assert rules, "no crosshair rule found"
        for selector, declaration in rules:
            value = declaration.split(":", 1)[1]
            assert not re.search(r"#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(|\boklch\(|\d+px", value), (selector, declaration)
            assert "var(--" in value, (selector, declaration)

    def test_the_crosshair_only_ever_sets_a_background(self) -> None:
        """A tint cannot be read as a circle, a dot or a glyph: different channels."""
        css = PLAYER_CSS.read_text(encoding="utf-8")
        for selector, declaration in _declarations_of(css, "is-crossed"):
            assert declaration.split(":")[0].strip() == "background", (selector, declaration)


def _rgb255(text: str) -> tuple[float, float, float]:
    """A computed ``rgb(...)`` or ``color(srgb ...)`` as 0-255 channels."""
    r, g, b = (float(v) for v in re.findall(r"[\d.]+", text)[:3])
    scale = 255 if text.startswith("color(") else 1
    return (r * scale, g * scale, b * scale)


def _distance(one, other) -> float:
    return sum((a - b) ** 2 for a, b in zip(one, other)) ** 0.5


def _token_rgb() -> dict[str, tuple[float, float, float]]:
    css = (PLAYER_DIR.parent / "src" / "nonogram" / "admin" / "static" / "tokens.css").read_text(encoding="utf-8")
    return {
        name: tuple(float(int(hexa[i : i + 2], 16)) for i in (0, 2, 4))
        for name, hexa in re.findall(r"(--[\w-]+)\s*:\s*#([0-9a-fA-F]{6})\s*;", css)
    }


@pytest.mark.browser
class TestPublicCrosshair_TheTintStaysApart:
    """The tint is distinct from the Maybe cell's ground (the card's design
    context) and a crossed filled cell stays the darkest thing on the board."""

    def test_a_crossed_cell_is_not_the_colour_of_a_maybe_cell(self, browser_page, host) -> None:
        page = browser_page
        grid = GRIDS["min"]
        key = host[2]["min"]
        _prefill(page, host, key, _save(key, grid, [(0, 0)], state="maybe"))
        assert _state(page, 0, 0) == "maybe"
        ground = "(r, c) => getComputedStyle(document.querySelector(`td[data-row='${r}'][data-col='${c}']`)).backgroundColor"
        maybe_colour = page.evaluate(f"({ground})(0, 0)")
        _move(page, 2, 2)
        crossed_unmarked = page.evaluate(f"({ground})(2, 3)")
        assert _state(page, 2, 3) == "unknown"
        assert crossed_unmarked != maybe_colour
        # F-3 (review cycle 1): "!=" alone passes a tint one step off the Maybe
        # ground. The floor is DERIVED: the design system's own two
        # near-identical warm grounds, --color-surface-hover (the Maybe ground)
        # and --color-surface-sunken, are 3.0 apart in sRGB (euclidean, 0-255),
        # and those are the pair it deliberately treats as the same quiet
        # family. The crosshair must be at least TWICE that far from the Maybe
        # ground, or it is the same family too. The real tint is 11.0 away
        # (rgb 235,233,230 against 241,235,221), a margin of 1.8x over the floor.
        tokens = _token_rgb()
        floor = 2 * _distance(tokens["--color-surface-hover"], tokens["--color-surface-sunken"])
        assert _rgb255(maybe_colour) == tokens["--color-surface-hover"], "the Maybe ground is the token"
        assert _distance(_rgb255(crossed_unmarked), _rgb255(maybe_colour)) >= floor, (crossed_unmarked, maybe_colour, floor)
        # ...and a crossed unmarked cell is not the uncrossed paper either.
        _move_off_the_stage(page)
        assert page.evaluate(f"({ground})(2, 3)") != crossed_unmarked

    def test_a_crossed_filled_cell_keeps_its_dark_ground(self, browser_page, host) -> None:
        page = browser_page
        grid = GRIDS["min"]
        key = host[2]["min"]
        # A filled cell that shares a line with a light one, so BOTH are crossed
        # by the same cross and can be compared under it.
        r, c, blank = next(
            (rr, cc, (rr, other))
            for rr, cc in _filled_cells(grid)
            for other in range(len(grid[0]))
            if not grid[rr][other]
        )
        _prefill(page, host, key, _save(key, grid, [(r, c)]))
        # Chromium reports a color-mix() as ``color(srgb 0.26 0.27 0.3)`` (0..1)
        # and a plain token as ``rgb(255, 253, 248)`` (0..255): one scale first.
        luma = (
            "(r, c) => { const text = getComputedStyle(document.querySelector("
            "`td[data-row='${r}'][data-col='${c}']`)).backgroundColor;"
            " const [R, G, B] = text.match(/[\\d.]+/g).slice(0, 3).map(Number)"
            ".map((v) => (text.startsWith('color(') ? v * 255 : v));"
            " return 0.2126 * R + 0.7152 * G + 0.0722 * B; }"
        )
        _move(page, r, c)
        assert _state(page, *blank) != "filled"
        crossed_filled = page.evaluate(f"({luma})({r}, {c})")
        crossed_light = page.evaluate(f"({luma})({blank[0]}, {blank[1]})")
        assert crossed_light > crossed_filled + 100, (crossed_filled, crossed_light)


# ==========================================================================
# AC-7 — zoomed, scrolled, and pinched (the gap this card closed)
# ==========================================================================


def _zoom_to_max(page) -> None:
    maximum = _bounds(page)["max"]
    for _ in range(64):
        if _percent(page) >= maximum:
            break
        _press(page, "in")
    assert _percent(page) == maximum


def _scroll_stage(page, fraction: float = 0.5) -> tuple[float, float]:
    """Scroll the stage to ``fraction`` of its range on both axes; return the offsets."""
    left, top = page.evaluate(
        """(f) => {
          const s = document.querySelector('[data-player-stage]');
          s.scrollLeft = (s.scrollWidth - s.clientWidth) * f;
          s.scrollTop = (s.scrollHeight - s.clientHeight) * f;
          return [s.scrollLeft, s.scrollTop];
        }""",
        fraction,
    )
    return left, top


def _reachable_cells(page) -> list[dict]:
    """Cells wholly inside the part of the stage a pointer can actually reach:
    inside its client box, right of the row-clue gutter and below the column
    clue band (a pinned gutter covers the cells beneath it)."""
    return page.evaluate(
        """() => {
          const stage = document.querySelector('[data-player-stage]');
          const box = stage.getBoundingClientRect();
          const left = box.left + stage.clientLeft, top = box.top + stage.clientTop;
          const right = left + stage.clientWidth, bottom = top + stage.clientHeight;
          const pinnedRight = Math.max(left, ...[...document.querySelectorAll('th.is-row')]
            .filter((th) => getComputedStyle(th).left !== 'auto').map((th) => th.getBoundingClientRect().right));
          const pinnedBottom = Math.max(top, ...[...document.querySelectorAll('th.is-col')]
            .filter((th) => getComputedStyle(th).top !== 'auto').map((th) => th.getBoundingClientRect().bottom));
          return [...document.querySelectorAll('td.player-cell')].map((td) => {
            const r = td.getBoundingClientRect();
            return { row: Number(td.dataset.row), col: Number(td.dataset.col),
                     l: r.left, t: r.top, r: r.right, b: r.bottom,
                     ok: r.left >= pinnedRight + 1 && r.top >= pinnedBottom + 1
                         && r.right <= right - 1 && r.bottom <= bottom - 1 };
          }).filter((c) => c.ok);
        }"""
    )


def _sample(cells: list[dict], count: int = 6) -> list[dict]:
    """Spread ``count`` cells across what is reachable: both extremes first."""
    ordered = sorted(cells, key=lambda c: (c["row"], c["col"]))
    if len(ordered) <= count or count == 1:
        return ordered[:count]
    picks = {0, len(ordered) - 1}
    picks.update(round(i * (len(ordered) - 1) / (count - 1)) for i in range(count))
    return [ordered[i] for i in sorted(picks)]


def _clue_overlaps_the_line(page, cell: dict) -> bool:
    """The highlighted column clue sits over the column's own cells and the
    highlighted row clue beside the row's — the RIGHT clue, in view."""
    return page.evaluate(
        """({row, col}) => {
          const rect = (el) => el.getBoundingClientRect();
          const cell = rect(document.querySelector(`td[data-row="${row}"][data-col="${col}"]`));
          const colClue = rect(document.querySelector('th.is-col.is-crossed'));
          const rowClue = rect(document.querySelector('th.is-row.is-crossed'));
          const across = (a0, a1, b0, b1) => Math.min(a1, b1) - Math.max(a0, b0) > 1;
          return document.querySelector('th.is-col.is-crossed').dataset.line === String(col)
            && document.querySelector('th.is-row.is-crossed').dataset.line === String(row)
            && across(cell.left, cell.right, colClue.left, colClue.right)
            && across(cell.top, cell.bottom, rowClue.top, rowClue.bottom);
        }""",
        {"row": cell["row"], "col": cell["col"]},
    )


@pytest.mark.browser
class TestPublicCrosshair_ItLandsOnTheCellUnderThePointerWhenZoomedAndScrolled:
    """AC-7 — added by this card (the card predates zoom).

    The crosshair lands on the cell UNDER the pointer at the zoom maximum, at
    a scrolled stage, and at a scrolled page; and a two-pointer pinch neither
    starts a crosshair nor leaves one.
    """

    def _land_on_each(self, page, cells: list[dict]) -> int:
        assert cells, "no reachable cell: the test would pass vacuously"
        landed = 0
        for cell in cells:
            # Two points per cell, each 3 px inside an opposite corner: an
            # error of one cell pitch or of the scroll offset cannot hide.
            for x, y in ((cell["l"] + 3, cell["t"] + 3), (cell["r"] - 3, cell["b"] - 3)):
                page.mouse.move(x, y)
                _assert_crossed_at(page, cell["row"], cell["col"])
                assert _clue_overlaps_the_line(page, cell), cell
                landed += 1
        return landed

    @pytest.mark.parametrize(
        ("viewport", "fraction"),
        [("desktop", 0.0), ("phone", 0.5), ("phone", 0.75), ("phone", 1.0)],
    )
    def test_it_lands_on_the_cell_at_the_zoom_maximum_at_any_stage_scroll(
        self, browser_page, host, viewport, fraction
    ) -> None:
        """At 390 px and 300% the row gutter is wider than the stage and lets
        go (CARD-324), so at scroll 0 no whole cell is reachable on the phone:
        the unscrolled baseline is taken on a desktop viewport instead, and
        the phone is taken at three scrolled offsets."""
        page = browser_page
        if viewport == "phone":
            _open_max(page, host)
        else:
            page.set_viewport_size({"width": 1440, "height": 900})
            _open(page, host, host[2]["max"])
        _zoom_to_max(page)
        left, top = _scroll_stage(page, fraction)
        if fraction:
            assert left > 0 and top > 0, "the stage did not scroll: the offset arm would be vacuous"
        cells = _sample(_reachable_cells(page))
        assert self._land_on_each(page, cells) >= 4

    def test_it_lands_on_the_cell_after_the_zoom_moved_the_scroll_itself(self, browser_page, host) -> None:
        """Zoom anchors the scroll (anchoredScroll), so after a zoom the stage
        is scrolled by the module and not by this test."""
        page = browser_page
        _open_max(page, host)
        _scroll_stage(page, 0.3)
        _zoom_to_max(page)
        assert page.evaluate("() => document.querySelector('[data-player-stage]').scrollLeft") > 0
        self._land_on_each(page, _sample(_reachable_cells(page)))

    def test_it_lands_on_the_cell_when_the_page_itself_has_scrolled(self, browser_page, host) -> None:
        """A phone on its side: the toolbar wraps and the page can scroll as
        well as the stage. The largest zoom at which a whole cell is still
        reachable inside the scrolled viewport is used (at 300% the column
        clue band alone can be taller than a 390 px screen)."""
        page = browser_page
        page.set_viewport_size(LANDSCAPE)
        _open(page, host, host[2]["max"])
        _zoom_to_max(page)
        _scroll_stage(page, 0.5)
        scrolled = page.evaluate("() => { window.scrollTo(0, 400); return window.scrollY; }")
        assert scrolled > 0, "the page cannot scroll at this viewport: the page-scroll arm would be vacuous"

        def in_view():
            return [
                c for c in _reachable_cells(page)
                if 0 <= c["t"] and c["b"] <= LANDSCAPE["height"] and 0 <= c["l"] and c["r"] <= LANDSCAPE["width"]
            ]

        for _ in range(12):
            if len(in_view()) >= 2:
                break
            _press(page, "out")
            page.evaluate("() => window.scrollTo(0, 400)")
        cells = in_view()
        assert len(cells) >= 2, "no reachable cell inside the scrolled viewport at any zoom"
        assert _percent(page) > _bounds(page)["min"], "the page-scroll arm ran unzoomed"
        assert page.evaluate("() => window.scrollY") > 0
        self._land_on_each(page, _sample(cells, 4))

    def test_a_crosshair_painted_before_a_zoom_survives_it_whole(self, browser_page, host) -> None:
        """Zoom is a view: pressing it re-paints nothing and rewrites nothing."""
        page = browser_page
        _open_max(page, host)
        _touch_tap(page, 6, 1)
        before = _full_or_none(page)
        assert before == (6, 1)
        _press(page, "in")
        assert _full_or_none(page) == before

    # -- the pinch ----------------------------------------------------------

    def _pinch(self, page, steps_check) -> None:
        """Two fingers, the first on a cell, spreading. ``steps_check(stage)``
        runs after every stage of the stream. The first finger never moves
        (see test_public_player_zoom's _pinch for why)."""
        session = page.context.new_cdp_session(page)
        try:
            x, y = _cell_centre(page, 6, 0)
            start, end = 80, 160
            assert 0 < x and x + end < PHONE["width"]
            _touch(session, "touchStart", [(x, y)])
            page.wait_for_timeout(100)
            steps_check("first finger down")
            _touch(session, "touchStart", [(x, y), (x + start, y)])
            page.wait_for_timeout(100)
            steps_check("second finger down")
            _touch(session, "touchMove", [(x, y), (x + end, y)])
            page.wait_for_timeout(SETTLE_MS)
            steps_check("spreading")
            _touch(session, "touchEnd", [])
        finally:
            session.detach()
        page.wait_for_timeout(SETTLE_MS)
        steps_check("lifted")

    def test_a_pinch_neither_starts_a_crosshair_nor_leaves_one(self, browser_page, host) -> None:
        page = browser_page
        _open_max(page, host)
        zoom_before = _percent(page)
        seen: dict[str, dict] = {}

        def check(stage_name: str) -> None:
            seen[stage_name] = _normalised(_crossed(page))

        self._pinch(page, check)
        assert _percent(page) > zoom_before, "the pinch did not zoom, so every arm below is vacuous"
        # The first finger's pointerdown paints a cross (decision 2: a gesture
        # is crossed from the moment it starts); the SECOND finger takes it
        # off, nothing follows the spread, and nothing is left behind.
        assert seen["first finger down"] != NOTHING
        assert seen["second finger down"] == NOTHING
        assert seen["spreading"] == NOTHING
        assert seen["lifted"] == NOTHING

    def test_a_pinch_takes_off_a_crosshair_an_earlier_tap_left(self, browser_page, host) -> None:
        page = browser_page
        _open_max(page, host)
        _touch_tap(page, 2, 3)
        assert _full_or_none(page) == (2, 3)
        seen: dict[str, dict] = {}
        self._pinch(page, lambda name: seen.__setitem__(name, _normalised(_crossed(page))))
        assert seen["second finger down"] == NOTHING and seen["lifted"] == NOTHING

    def test_crossing_resumes_after_a_pinch(self, browser_page, host) -> None:
        """The suppression is for the pinch and nothing longer."""
        page = browser_page
        _open_max(page, host)
        self._pinch(page, lambda name: None)
        _assert_nothing_crossed(page)
        cell = _sample(_reachable_cells(page), 1)[0]
        session = page.context.new_cdp_session(page)
        try:
            # A touch pinch can leave the BROWSER's own pinch-zoom engaged
            # (touch-action stays auto, owner 2026-11-05: measured here as a
            # visual-viewport scale of 1.28 after the pinch), and a CDP touch
            # is placed in the visual viewport, so a layout-space point is
            # translated by its offset. That is the harness's coordinates and
            # not the crosshair's: the page reports the pointer's clientX/Y
            # and the crosshair hit-tests exactly there.
            dx, dy = page.evaluate("() => [visualViewport.offsetLeft, visualViewport.offsetTop]")
            x, y = (cell["l"] + cell["r"]) / 2 - dx, (cell["t"] + cell["b"]) / 2 - dy
            _touch(session, "touchStart", [(x, y)])
            _touch(session, "touchEnd", [])
        finally:
            session.detach()
        page.wait_for_timeout(SETTLE_MS)
        _assert_crossed_at(page, cell["row"], cell["col"])

    def test_a_third_finger_neither_paints_nor_follows(self, browser_page, host) -> None:
        """Two fingers are a pinch; three are still no crosshair, whether the
        third lands or moves. (Review cycle 1, E14.)"""
        page = browser_page
        _open_max(page, host)
        session = page.context.new_cdp_session(page)
        try:
            x, y = _cell_centre(page, 6, 0)
            third = (x, y + 60)
            _touch(session, "touchStart", [(x, y)])
            _touch(session, "touchStart", [(x, y), (x + 80, y)])
            page.wait_for_timeout(100)
            _assert_nothing_crossed(page)
            _touch(session, "touchStart", [(x, y), (x + 80, y), third])
            page.wait_for_timeout(100)
            _assert_nothing_crossed(page)
            _touch(session, "touchMove", [(x, y), (x + 80, y), (third[0] + 30, third[1])])
            page.wait_for_timeout(SETTLE_MS)
            _assert_nothing_crossed(page)
            _touch(session, "touchEnd", [])
        finally:
            session.detach()

    def test_a_pen_counts_toward_a_pinch(self, browser_page, host) -> None:
        """play.js counts touch AND pen as the pinch's pointers, so the crosshair
        does too. One finger, then a pen press: two pointers, no crosshair.
        (Review cycle 1, E09.)"""
        page = browser_page
        _open_max(page, host)
        session = page.context.new_cdp_session(page)
        try:
            x, y = _cell_centre(page, 6, 0)
            _touch(session, "touchStart", [(x, y)])
            page.wait_for_timeout(100)
            assert _full_or_none(page) == (6, 0), "the finger alone is crossed: the arm below is not vacuous"
            pen = {"pointerType": "pen", "button": "left", "buttons": 1, "clickCount": 1}
            session.send("Input.dispatchMouseEvent", {"type": "mousePressed", "x": x + 60, "y": y, **pen})
            page.wait_for_timeout(100)
            _assert_nothing_crossed(page)
            session.send("Input.dispatchMouseEvent", {"type": "mouseReleased", "x": x + 60, "y": y, **pen})
            _touch(session, "touchEnd", [])
        finally:
            session.detach()

    def test_a_finger_counts_toward_a_pinch_that_a_pen_began(self, browser_page, host) -> None:
        """The mirror of the pen test: a pen is down, then a finger lands. The
        finger's primary resets only the TOUCH entries, so the pen still counts."""
        page = browser_page
        _open_max(page, host)
        session = page.context.new_cdp_session(page)
        try:
            x, y = _cell_centre(page, 6, 0)
            pen = {"pointerType": "pen", "button": "left", "buttons": 1, "clickCount": 1}
            session.send("Input.dispatchMouseEvent", {"type": "mousePressed", "x": x, "y": y, **pen})
            page.wait_for_timeout(100)
            assert _full_or_none(page) == (6, 0), "the pen alone is crossed: the arm below is not vacuous"
            _touch(session, "touchStart", [(x + 60, y)])
            page.wait_for_timeout(100)
            _assert_nothing_crossed(page)
            _touch(session, "touchEnd", [])
            session.send("Input.dispatchMouseEvent", {"type": "mouseReleased", "x": x, "y": y, **pen})
        finally:
            session.detach()

    def test_a_lost_pen_pointerup_does_not_stick_a_pinch(self, browser_page, host) -> None:
        """A pen pointerup that never reaches the stage leaves a stale entry; the
        next primary pen press must clear it rather than count it as a second
        pointer. Synthetic PointerEvents, because a real pen cannot lose its
        own release."""
        page = browser_page
        _open_max(page, host)
        press = (
            "([id, x, y]) => document.querySelector('[data-player-stage]').dispatchEvent("
            "new PointerEvent('pointerdown', {pointerType: 'pen', isPrimary: true, pointerId: id,"
            " clientX: x, clientY: y, bubbles: true, cancelable: true}))"
        )
        release = (
            "([id, x, y]) => document.querySelector('[data-player-stage]').dispatchEvent("
            "new PointerEvent('pointerup', {pointerType: 'pen', isPrimary: true, pointerId: id,"
            " clientX: x, clientY: y, bubbles: true, cancelable: true}))"
        )
        ax, ay = _cell_centre(page, 6, 0)
        bx, by = _cell_centre(page, 7, 1)
        page.evaluate(press, [71, ax, ay])
        assert _full_or_none(page) == (6, 0)
        page.evaluate(press, [72, bx, by])  # 71's pointerup was lost
        assert _full_or_none(page) == (7, 1), "a stale pen entry stuck the pinch"
        page.evaluate(release, [72, bx, by])

    def test_a_pinch_marks_nothing_and_records_no_stroke(self, browser_page, host) -> None:
        """G-5 from the crosshair's side: its listeners add no input."""
        page = browser_page
        key = _open_max(page, host)
        before = _solve_state(page, f"nonogram-public:{key}")
        self._pinch(page, lambda name: None)
        after = _solve_state(page, f"nonogram-public:{key}")
        assert after["states"] == before["states"] and after["done"] == before["done"]
