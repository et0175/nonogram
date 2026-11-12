"""CARD-394 - the project's base stylesheet is held to the real Bootstrap.

The shared-UI preview (CARD-386) links ``player/shared-ui-base.css``, a small
hand-written file that stands in for the part of Bootstrap 5.3 the admin's
player page uses: the base rules (box sizing, ``[hidden]``, body, headings,
the button reset), the four classes ``btn`` / ``btn-outline-secondary`` /
``btn-danger`` / ``badge``, and ``alert`` (which ``solver.js`` creates when a
board cannot be drawn). The file's values were measured in Chromium against
the real Bootstrap; this module keeps it there.

THE FIDELITY CELL (``test_the_project_stylesheet_matches_the_real_bootstrap``).
At 390 and 1280 px it measures the computed layout styles and the bounding
rectangle of a sample of the page's elements: the 22 the CARD-386 reviewer
sampled (every button, the tier badge, the title, the toolbar, the stage and
the first cell), the ``html`` element (measured with motion not reduced, where
the real file makes scrolling smooth), the page's ``[hidden]`` elements, the error alert, and a plain
and a danger button in each of the states the page reaches (hover,
focus-visible, active, disabled). Styles must be equal; rectangles may differ
by ``RECT_TOLERANCE`` px, which is the layout engine's own rounding (1/64 px)
with room to spare, because the measured residue between the two stylesheets
is ZERO on every sampled element, in every state, at both widths (and, in the
author's wider run, on every element of the page and in the open-menu, confirm
and solved states).

What it compares against:

* with ``NONOGRAM_REAL_BOOTSTRAP=<path to the real bootstrap.min.css>`` it
  builds a second tree with that file published as ``base.css`` and compares live (the file is never
  committed); if the file is the one the table was recorded from (same sha256)
  it also asserts the table equals the live measurement, so the table cannot
  rot;
* without it, the cell is NOT skipped: it compares against ``FROZEN``, the
  real file's measured values, recorded once (provenance beside it).

``test_a_changed_stylesheet_reds_the_fidelity_check`` is the plant: dropping the
``[hidden]`` rule, or changing ``.btn`` padding, must red the same comparison.

Caveat, stated rather than hidden: the frozen rectangles include text widths,
so they hold on a machine whose font fallbacks resolve as on the recording
machine; on another machine ``NONOGRAM_REAL_BOOTSTRAP`` mode needs no table, and
a failing run's message says how to re-record it.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from tests.test_player_shared_ui_site import (  # noqa: F401 - fixtures are used by name
    browser_page,
    browser_type,
    bundle,
    fragment,
    open_play,
    preview_of,
)
from tests.test_public_player import REPO_ROOT
from tests.test_public_player_pages import _serve

REAL_ENV = "NONOGRAM_REAL_BOOTSTRAP"
BASE_CSS = REPO_ROOT / "player" / "shared-ui-base.css"
WIDTHS = (390, 1280)
RECT_TOLERANCE = 0.05

#: Where ``FROZEN`` came from: the real file -- the ``bootstrap.min.css`` of
#: the ``bootstrap@5.3.0`` the admin's ``base.html`` pins on jsDelivr, which is
#: deliberately never committed but is fetchable from that pinned URL, so a
#: re-record needs no local spike copy (CARD-423 re-recorded from it and
#: matched the sha256 below) -- measured by this module's ``measure`` on the
#: preview of the pages corpus' sweep puzzle.
PROVENANCE = {
    "file": "bootstrap.min.css (Bootstrap 5.3)",
    "sha256": "7f1d37f0d90b6385354c2ac10e2bb91563c46bd7a266ed351222ebcac8496c2a",
    "recorded": "2026-11-11",  # re-recorded by CARD-401 (compact toolbar, two-cell Region), CARD-403, CARD-404, CARD-409 (stage cap, capped clues, the answer line moved over the board) , CARD-411 (Keep and Wrong guess; the probe line a full control row), CARD-412 (the Wrong-guess offer), CARD-413 (How to play, one closed line), CARD-280 (Show grid; the solved banner) and CARD-423 (the compact toolbar's 44 px tap-target floor: the compact controls 36 -> 44 px tall, and the control block and board they reflow); same real file (sha256 verified against the bootstrap@5.3.0 that base.html pins), same browser, one macOS patch version later. CARD-426 did NOT re-record, and left this table exactly as it found it: in passing it set one field of one row at each width — "04 div puzzle-player-tool-menu"'s pointer-events — to none, and the owner's ruling of 2026-11-11 ("chrome should swallow the tap") put the brush menu's box back in charge of its own chrome, so that field is auto again at both widths and the two rows are byte-identical to their pre-CARD-426 form. Both edits were made by the property's index in PROPS, never by counting pipes, and each was certified against the real Bootstrap (the sha256 above) rather than argued: that one field was the module's whole output before the first edit — the run named exactly that difference at 390 and at 1280 and no other, rectangles included, which is also the measurement that the rule moved no layout, and the certification after the revert names no difference at all. CARD-427 DID re-measure, with the same real file (the sha256 above, fetched from the bootstrap@5.3.0 URL base.html pins and verified), the same browser and the same platform, and pasted the module's own printed rows: the owner's ruling of 2026-11-11 ("just appear the center of the screen on some background") moved the Wrong-guess offer out of the stage and into the viewport's centre, and the offer carries .player-explain, so row "27 div puzzle-player-offer" changed in SEVEN fields at each width -- margin 0px -> auto, padding 8px 12px -> 12px 16px, border-width 1px 0px 0px -> 2px, border-style solid none none -> solid, border-radius 0px -> 4px, position absolute -> fixed, background-color the 94% surface mix -> rgb(230, 239, 236) (--color-accent-tint). Its rectangle is unchanged (the offer is [hidden] when the census reads it, so 0|0|0|0), and the fresh measurement reproduced every OTHER row of both widths exactly, which is why `recorded` still names 2026-11-11: the table was re-certified whole and only that one row moved
    "browser": "Chromium 151.0.7922.34 (Playwright)",
    "platform": "macOS 26.7.2 arm64",
}

#: The CARD-386 reviewer's sample (22 elements on the sweep puzzle's page).
REVIEWER_SAMPLE = 'button,.badge,.player-head h1,.player-toolbar,.player-stage,td[data-row="0"][data-col="0"]'
#: This module's sample: the reviewer's, and what the page hides, and the error alert.
SAMPLE = f"{REVIEWER_SAMPLE},[hidden],.alert"

#: The computed properties that decide layout, and the colours and effects a state changes.
PROPS = (
    "display", "box-sizing", "margin", "padding", "border-width", "border-style", "border-radius",
    "font-size", "font-weight", "line-height", "flex", "align-items", "justify-content", "gap",
    "min-height", "text-align", "vertical-align", "white-space", "position",
    "color", "background-color", "border-top-color", "opacity", "box-shadow", "outline-style",
    "cursor", "pointer-events", "text-decoration-line", "text-transform", "scroll-behavior",
)

_READ = """(e, props) => {
  const cs = getComputedStyle(e), r = e.getBoundingClientRect();
  return [e.tagName.toLowerCase(), e.id || e.getAttribute('data-player-action') || (e.className.baseVal ?? e.className).split(' ')[0],
          [r.x, r.y, r.width, r.height].map((v) => Math.round(v * 100) / 100),
          props.map((p) => cs.getPropertyValue(p))];
}"""


def _row(read) -> str:
    _, _, rect, values = read
    return "|".join([*(f"{v:g}" for v in rect), *values])


def _settle(page) -> None:
    page.wait_for_timeout(300)  # the buttons transition colour for 150 ms


def measure(page, url: str, key: str, width: int) -> dict[str, str]:
    """label -> "x|y|w|h|<PROPS>" for the sample, the button states and the error alert."""
    page.set_viewport_size({"width": width, "height": 900})
    page.emulate_media(reduced_motion="no-preference")  # html's scroll-behavior is a fact of this setting
    open_play(page, url, key)
    _settle(page)
    # 22 when the CARD-386 reviewer sampled it; CARD-412 added the Wrong-guess
    # offer's two buttons (Mark it, No thanks), so the same sample is 24, and
    # CARD-280 the solved board's Show grid button, so it is 25.
    assert len(page.query_selector_all(REVIEWER_SAMPLE)) == 25, "the page is not the one the reviewer sampled"
    rows: dict[str, str] = {"html": _row(page.locator("html").evaluate(_READ, list(PROPS)))}
    for n, element in enumerate(page.query_selector_all(SAMPLE)):
        read = element.evaluate(_READ, list(PROPS))
        rows[f"{n:02d} {read[0]} {read[1]}"] = _row(read)
    def states(name: str, button, *, outside_click_ok: bool) -> None:
        # The confirmation closes on a click outside it, so its button is not "pressed" from a pointer start.
        for state in ("hover", "focus", "active", "pressed", "disabled"):
            if state == "pressed" and not outside_click_ok:
                continue
            page.mouse.move(0, 0)
            if state == "hover":
                button.hover()
            elif state == "focus":
                page.keyboard.press("Shift")  # a keyboard modality, so :focus-visible matches
                button.focus()
            elif state in ("active", "pressed"):
                if state == "pressed":
                    page.mouse.click(1, 1)  # back to a pointer modality: pressed, but not :focus-visible
                button.hover()
                page.mouse.down()
            else:
                button.evaluate("(b) => { b.disabled = true; }")
            _settle(page)
            rows[f"{state} {name}"] = _row(button.evaluate(_READ, list(PROPS)))
            page.mouse.move(0, 0)  # released away from the button: no click, so no side effect
            page.mouse.up()
            button.evaluate("(b) => { b.disabled = false; }")

    # An ENABLED outline button: Undo and Redo start out aria-disabled, which dims them.
    states("plain", page.locator('button[data-player-action="hint"]'), outside_click_ok=True)
    # The danger button lives in the reset confirmation: make a mark, press Reset.
    page.locator('td[data-row="0"][data-col="0"]').click()
    page.locator('[data-player-action="reset"]').click()
    states("danger", page.locator("button.btn-danger"), outside_click_ok=False)

    def break_the_board(route) -> None:  # a puzzle file whose clue count does not match: solver.js shows its alert
        body = route.fetch().json()
        body["clues"]["rows"] = []
        route.fulfill(json=body)

    page.route("**/puzzle/*.json", break_the_board)
    page.reload()
    page.wait_for_selector(".alert")
    _settle(page)
    rows["error alert"] = _row(page.locator(".alert").evaluate(_READ, list(PROPS)))
    page.unroute("**/puzzle/*.json")
    return rows


def differences(expected: dict[str, str], actual: dict[str, str]) -> list[str]:
    """Every row whose styles differ, or whose rectangle differs by more than the tolerance."""
    problems = [f"row set differs: {sorted(set(expected) ^ set(actual))}"] if expected.keys() != actual.keys() else []
    names = ("x", "y", "width", "height", *PROPS)
    for label in expected.keys() & actual.keys():
        for name, want, got in zip(names, expected[label].split("|"), actual[label].split("|")):
            if name in ("x", "y", "width", "height"):
                if abs(float(want) - float(got)) > RECT_TOLERANCE:
                    problems.append(f"{label}: {name} {want} != {got}")
            elif want != got:
                problems.append(f"{label}: {name} {want!r} != {got!r}")
    return sorted(problems)


def frozen_literal(width: int, rows: dict[str, str]) -> str:
    return "".join([f"    {width}: {{\n", *(f'        "{k}": "{v}",\n' for k, v in rows.items()), "    },\n"])


def measured_tree(site: Path, key: str, width: int, page) -> dict[str, str]:
    url, stop = _serve(site)
    try:
        return measure(page, url, key, width)
    finally:
        stop()


@pytest.mark.browser
@pytest.mark.parametrize("width", WIDTHS)
def test_the_project_stylesheet_matches_the_real_bootstrap(
    browser_page, bundle, fragment, tmp_path, width
) -> None:
    """AC-2: equal styles and rectangles (within RECT_TOLERANCE) at both widths, in each state."""
    root, keys, _ = bundle
    ours = preview_of(root, tmp_path / "ours", fragment, tmp_path).site_dir
    actual = measured_tree(ours, keys["sweep"], width, browser_page)
    expected = FROZEN[width]
    real = os.environ.get(REAL_ENV)
    if real is not None:
        real_file = Path(real)
        assert real_file.is_file(), f"{REAL_ENV} names no file: {real}"
        theirs = preview_of(root, tmp_path / "theirs", fragment, tmp_path).site_dir
        # CARD-399: the page links /base.css, so the real file replaces that one published file.
        (theirs / "base.css").write_bytes(real_file.read_bytes())
        live = measured_tree(theirs, keys["sweep"], width, browser_page)
        if hashlib.sha256(real_file.read_bytes()).hexdigest() == PROVENANCE["sha256"]:
            assert differences(FROZEN[width], live) == [], "FROZEN no longer equals the real file's measurement"
        expected = live
    assert len(expected) >= 1 + 24 + 9 + 1
    if real is not None and os.environ.get("NONOGRAM_PRINT_FROZEN"):
        print(f"\n# {PROVENANCE['file']} sha256 {hashlib.sha256(real_file.read_bytes()).hexdigest()}, "
              f"Chromium {browser_page.context.browser.version}\n" + frozen_literal(width, expected))
    problems = differences(expected, actual)
    assert problems == [], (
        f"{len(problems)} differences from the {'real file measured now' if real else 'FROZEN table'}. "
        f"If the stylesheet is at fault, fix it. If the browser or fonts moved, re-record: the table was "
        f"measured with {PROVENANCE['browser']} on {PROVENANCE['platform']}, this run is Chromium "
        f"{browser_page.context.browser.version}; text widths in the rectangles follow the machine's font "
        f"fallbacks. To re-record deliberately, run {REAL_ENV}=<the real bootstrap.min.css> "
        f"NONOGRAM_PRINT_FROZEN=1 pytest tests/test_player_base_css.py -s -k matches_the_real, paste the printed "
        f"rows over FROZEN, and update PROVENANCE (sha256, browser, platform, date). First problems: {problems[:5]}"
    )


@pytest.mark.browser
def test_a_changed_stylesheet_reds_the_fidelity_check(browser_page, bundle, fragment, tmp_path) -> None:
    """The plant: drop the ``[hidden]`` rule, or change ``.btn`` padding; the same comparison reds."""
    root, keys, _ = bundle
    original = BASE_CSS.read_text(encoding="utf-8")
    for label, planted in (
        ("no [hidden] rule", original.replace("[hidden] {\n  display: none !important;\n}\n", "")),
        ("wider .btn padding", original.replace("0.4rem 0.75rem", "0.4rem 0.9rem")),
    ):
        assert planted != original, label
        site = preview_of(root, tmp_path / label.replace(" ", "-"), fragment, tmp_path).site_dir
        (site / "base.css").write_text(planted, encoding="utf-8")
        actual = measured_tree(site, keys["sweep"], 1280, browser_page)
        assert differences(FROZEN[1280], actual) != [], label


# fmt: off
FROZEN: dict[int, dict[str, str]] = {
    390: {
        "html": "0|0|390|604.89|block|border-box|0px|0px|0px|none|0px|16px|400|normal|0 1 auto|normal|normal|normal|0px|start|baseline|normal|static|rgb(0, 0, 0)|rgba(0, 0, 0, 0)|rgb(0, 0, 0)|1|none|none|auto|auto|none|none|smooth",
        "00 h1 ": "16|16|178.28|36.48|block|border-box|0px 0px 4px|0px|0px|none|0px|30.4px|500|36.48px|0 1 auto|normal|normal|normal|auto|start|baseline|normal|static|rgb(28, 35, 51)|rgba(0, 0, 0, 0)|rgb(28, 35, 51)|1|none|none|auto|auto|none|none|auto",
        "01 span badge": "210.28|23|85.56|26.47|inline-block|border-box|0px|5.04px 8.64px|1px|solid|3px|14.4px|600|14.4px|0 1 auto|normal|normal|normal|0px|center|baseline|nowrap|static|color(srgb 0.531373 0.37451 0.135294)|color(srgb 0.979922 0.922039 0.822667)|color(srgb 0.970196 0.810196 0.551569)|1|none|none|auto|auto|none|none|auto",
        "02 div puzzle-player-controls": "16|63.48|358|125|flex|border-box|-9px 0px 16px|0px|0px|none|0px|16px|400|24.8px|0 1 auto|flex-start|normal|8px|0px|start|baseline|normal|static|rgb(28, 35, 51)|rgba(0, 0, 0, 0)|rgb(28, 35, 51)|1|none|none|auto|auto|none|none|auto",
        "03 button puzzle-player-tool-trigger": "16|63.48|44|44|flex|border-box|0px|6.4px 8px|1px|solid|3px|16px|600|24px|0 0 auto|center|center|8px|44px|center|middle|normal|static|rgb(28, 35, 51)|rgb(251, 248, 241)|rgb(127, 117, 95)|1|none|none|pointer|auto|none|none|auto",
        "04 div puzzle-player-tool-menu": "0|0|0|0|none|border-box|0px|8px|1px|solid|4px|16px|400|24.8px|0 1 auto|normal|normal|4px|0px|start|baseline|normal|absolute|rgb(28, 35, 51)|rgb(251, 248, 241)|rgb(127, 117, 95)|1|rgba(28, 35, 51, 0.22) 0px 12px 32px 0px|none|auto|auto|none|none|auto",
        "05 button player-tool-item": "0|0|0|0|flex|border-box|0px|4px 8px|0px|none|3px|16px|600|24.8px|0 1 auto|center|normal|8px|36px|left|baseline|normal|static|rgb(31, 95, 91)|rgb(230, 239, 236)|rgb(31, 95, 91)|1|none|none|pointer|auto|none|none|auto",
        "06 button player-tool-item": "0|0|0|0|flex|border-box|0px|4px 8px|0px|none|3px|16px|400|24.8px|0 1 auto|center|normal|8px|36px|left|baseline|normal|static|rgb(28, 35, 51)|rgba(0, 0, 0, 0)|rgb(28, 35, 51)|1|none|none|pointer|auto|none|none|auto",
        "07 button player-tool-item": "0|0|0|0|flex|border-box|0px|4px 8px|0px|none|3px|16px|400|24.8px|0 1 auto|center|normal|8px|36px|left|baseline|normal|static|rgb(28, 35, 51)|rgba(0, 0, 0, 0)|rgb(28, 35, 51)|1|none|none|pointer|auto|none|none|auto",
        "08 button player-tool-item": "0|0|0|0|flex|border-box|0px|4px 8px|0px|none|3px|16px|400|24.8px|0 1 auto|center|normal|8px|36px|left|baseline|normal|static|rgb(28, 35, 51)|rgba(0, 0, 0, 0)|rgb(28, 35, 51)|1|none|none|pointer|auto|none|none|auto",
        "09 button puzzle-player-region": "68|63.48|49|44|flex|border-box|0px|6.4px 8px|1px|solid|3px|16px|600|24px|0 1 auto|center|normal|8px|44px|center|middle|normal|static|rgb(28, 35, 51)|rgb(251, 248, 241)|rgb(127, 117, 95)|1|none|none|pointer|auto|none|none|auto",
        "10 p puzzle-player-solved": "0|0|0|0|none|border-box|0px|0px 4px|1px 1px 1px 3px|solid|3px|16px|400|24.8px|0 1 auto|center|normal|4px|36px|start|baseline|normal|static|rgb(28, 35, 51)|rgb(231, 239, 230)|rgb(47, 107, 58)|1|none|none|auto|auto|none|none|auto",
        "11 button undo": "125|63.48|44|44|flex|border-box|0px|6.4px 8px|1px|solid|3px|16px|600|24px|0 1 auto|center|center|8px|44px|center|middle|normal|static|rgb(28, 35, 51)|rgb(251, 248, 241)|rgb(127, 117, 95)|0.55|none|none|not-allowed|auto|none|none|auto",
        "12 button redo": "177|63.48|44|44|flex|border-box|0px|6.4px 8px|1px|solid|3px|16px|600|24px|0 1 auto|center|center|8px|44px|center|middle|normal|static|rgb(28, 35, 51)|rgb(251, 248, 241)|rgb(127, 117, 95)|0.55|none|none|not-allowed|auto|none|none|auto",
        "13 button reset": "229|63.48|44|44|flex|border-box|0px|6.4px 8px|1px|solid|3px|16px|600|24px|0 1 auto|center|center|8px|44px|center|middle|normal|static|rgb(28, 35, 51)|rgb(251, 248, 241)|rgb(127, 117, 95)|0.55|none|none|not-allowed|auto|none|none|auto",
        "14 div puzzle-player-confirm": "0|0|0|0|none|border-box|0px|12px 16px|1px|solid|4px|16px|400|24.8px|0 1 auto|normal|normal|normal|0px|start|baseline|normal|absolute|rgb(28, 35, 51)|rgb(251, 248, 241)|rgb(127, 117, 95)|1|rgba(28, 35, 51, 0.22) 0px 12px 32px 0px|none|auto|auto|none|none|auto",
        "15 button btn": "0|0|0|0|flex|border-box|0px|6.4px 12px|1px|solid|3px|16px|600|24px|0 1 auto|center|normal|8px|44px|center|middle|normal|static|rgb(255, 255, 255)|rgb(155, 59, 38)|rgb(155, 59, 38)|1|none|none|pointer|auto|none|none|auto",
        "16 button btn": "0|0|0|0|flex|border-box|0px|6.4px 12px|1px|solid|3px|16px|600|24px|0 1 auto|center|normal|8px|44px|center|middle|normal|static|rgb(28, 35, 51)|rgb(251, 248, 241)|rgb(127, 117, 95)|1|none|none|pointer|auto|none|none|auto",
        "17 button hint": "281|63.48|44|44|flex|border-box|0px|6.4px 8px|1px|solid|3px|16px|600|24px|0 1 auto|center|center|8px|44px|center|middle|normal|static|rgb(28, 35, 51)|rgb(251, 248, 241)|rgb(127, 117, 95)|1|none|none|pointer|auto|none|none|auto",
        "18 button btn": "16|115.48|44|44|flex|border-box|0px|6.4px 8px|1px|solid|3px|16px|600|24px|0 1 auto|center|center|8px|44px|center|middle|normal|static|rgb(28, 35, 51)|rgb(251, 248, 241)|rgb(127, 117, 95)|0.55|none|none|not-allowed|auto|none|none|auto",
        "19 button btn": "106.53|115.48|44|44|flex|border-box|0px|6.4px 8px|1px|solid|3px|16px|600|24px|0 1 auto|center|center|8px|44px|center|middle|normal|static|rgb(28, 35, 51)|rgb(251, 248, 241)|rgb(127, 117, 95)|1|none|none|pointer|auto|none|none|auto",
        "20 button puzzle-player-probe": "16|159.48|44|44|flex|border-box|0px|6.4px 8px|1px|solid|3px|16px|600|24px|0 1 auto|center|center|4px|44px|center|middle|normal|static|rgb(28, 35, 51)|rgb(251, 248, 241)|rgb(127, 117, 95)|1|none|none|pointer|auto|none|none|auto",
        "21 button btn": "0|0|0|0|none|border-box|0px|6.4px 8px|1px|solid|3px|16px|600|24px|0 1 auto|center|center|4px|44px|center|middle|normal|static|rgb(28, 35, 51)|rgb(251, 248, 241)|rgb(127, 117, 95)|1|none|none|pointer|auto|none|none|auto",
        "22 button btn": "0|0|0|0|none|border-box|0px|6.4px 8px|1px|solid|3px|16px|600|24px|0 1 auto|center|center|4px|44px|center|middle|normal|static|rgb(28, 35, 51)|rgb(251, 248, 241)|rgb(127, 117, 95)|1|none|none|pointer|auto|none|none|auto",
        "23 button btn": "0|0|0|0|none|border-box|0px|6.4px 8px|1px|solid|3px|16px|600|24px|0 1 auto|center|center|4px|44px|center|middle|normal|static|rgb(28, 35, 51)|rgb(251, 248, 241)|rgb(127, 117, 95)|1|none|none|pointer|auto|none|none|auto",
        "24 p puzzle-player-probe-note": "0|0|0|0|none|border-box|0px|0px|0px|none|0px|12.48px|400|12.48px|1 1 0px|normal|normal|normal|0px|start|baseline|normal|static|rgb(92, 96, 112)|rgba(0, 0, 0, 0)|rgb(92, 96, 112)|1|none|none|auto|auto|none|none|auto",
        "25 div puzzle-player": "16|204.48|358|362.08|block|border-box|0px|0px|0px|none|0px|16px|400|24.8px|0 1 auto|normal|normal|normal|0px|start|baseline|normal|static|rgb(28, 35, 51)|rgba(0, 0, 0, 0)|rgb(28, 35, 51)|1|none|none|auto|auto|none|none|auto",
        "26 td player-cell": "105.83|282.13|26.84|26.84|table-cell|border-box|0px|0px|0px 1px 1px 0px|solid|0px|14px|400|14px|0 1 auto|normal|normal|normal|0px|start|middle|normal|static|rgb(28, 35, 51)|rgb(255, 253, 248)|rgb(28, 35, 51)|1|none|none|pointer|auto|none|none|auto",
        "27 div puzzle-player-offer": "0|0|0|0|none|border-box|auto|12px 16px|2px|solid|4px|14.4px|400|22.32px|0 1 auto|center|normal|8px|0px|start|baseline|normal|fixed|rgb(28, 35, 51)|rgb(230, 239, 236)|rgb(31, 95, 91)|1|rgba(28, 35, 51, 0.22) 0px 12px 32px 0px|none|auto|auto|none|none|auto",
        "28 button btn": "0|0|0|0|inline-flex|border-box|0px|6.4px 12px|1px|solid|3px|16px|600|24px|0 1 auto|center|normal|4px|0px|center|middle|normal|static|rgb(28, 35, 51)|rgb(251, 248, 241)|rgb(127, 117, 95)|1|none|none|pointer|auto|none|none|auto",
        "29 button btn": "0|0|0|0|inline-flex|border-box|0px|6.4px 12px|1px|solid|3px|16px|600|24px|0 1 auto|center|normal|4px|0px|center|middle|normal|static|rgb(28, 35, 51)|rgb(251, 248, 241)|rgb(127, 117, 95)|1|none|none|pointer|auto|none|none|auto",
        "hover plain": "281|63.48|44|44|flex|border-box|0px|6.4px 8px|1px|solid|3px|16px|600|24px|0 1 auto|center|center|8px|44px|center|middle|normal|static|rgb(28, 35, 51)|rgb(241, 235, 221)|rgb(127, 117, 95)|1|none|none|pointer|auto|none|none|auto",
        "focus plain": "281|63.48|44|44|flex|border-box|0px|6.4px 8px|1px|solid|3px|16px|600|24px|0 1 auto|center|center|8px|44px|center|middle|normal|static|rgb(28, 35, 51)|rgb(241, 235, 221)|rgb(127, 117, 95)|1|none|solid|pointer|auto|none|none|auto",
        "active plain": "281|63.48|44|44|flex|border-box|0px|6.4px 8px|1px|solid|3px|16px|600|24px|0 1 auto|center|center|8px|44px|center|middle|normal|static|rgb(28, 35, 51)|rgb(241, 235, 221)|rgb(127, 117, 95)|1|rgba(108, 117, 125, 0.5) 0px 0px 0px 4px|solid|pointer|auto|none|none|auto",
        "pressed plain": "281|63.48|44|44|flex|border-box|0px|6.4px 8px|1px|solid|3px|16px|600|24px|0 1 auto|center|center|8px|44px|center|middle|normal|static|rgb(28, 35, 51)|rgb(241, 235, 221)|rgb(127, 117, 95)|1|none|none|pointer|auto|none|none|auto",
        "disabled plain": "281|63.48|44|44|flex|border-box|0px|6.4px 8px|1px|solid|3px|16px|600|24px|0 1 auto|center|center|8px|44px|center|middle|normal|static|rgb(92, 96, 112)|rgb(251, 248, 241)|rgb(214, 205, 185)|0.55|none|none|not-allowed|none|none|none|auto",
        "hover danger": "142|191.61|117.3|44|flex|border-box|0px|6.4px 12px|1px|solid|3px|16px|600|24px|0 1 auto|center|normal|8px|44px|center|middle|normal|static|rgb(255, 255, 255)|rgb(122, 45, 28)|rgb(122, 45, 28)|1|none|none|pointer|auto|none|none|auto",
        "focus danger": "142|191.61|117.3|44|flex|border-box|0px|6.4px 12px|1px|solid|3px|16px|600|24px|0 1 auto|center|normal|8px|44px|center|middle|normal|static|rgb(255, 255, 255)|rgb(122, 45, 28)|rgb(127, 117, 95)|1|none|solid|pointer|auto|none|none|auto",
        "active danger": "142|191.61|117.3|44|flex|border-box|0px|6.4px 12px|1px|solid|3px|16px|600|24px|0 1 auto|center|normal|8px|44px|center|middle|normal|static|rgb(255, 255, 255)|rgb(155, 59, 38)|rgb(155, 59, 38)|1|rgba(225, 83, 97, 0.5) 0px 0px 0px 4px|solid|pointer|auto|none|none|auto",
        "disabled danger": "142|191.61|117.3|44|flex|border-box|0px|6.4px 12px|1px|solid|3px|16px|600|24px|0 1 auto|center|normal|8px|44px|center|middle|normal|static|rgb(155, 59, 38)|rgb(251, 248, 241)|rgb(155, 59, 38)|0.55|none|none|not-allowed|none|none|none|auto",
        "error alert": "16|72.48|358|108.39|block|border-box|0px 0px 16px|16px|1px 1px 1px 4px|solid|4px|16px|400|24.8px|0 1 auto|normal|normal|normal|0px|start|baseline|normal|relative|rgb(28, 35, 51)|rgb(245, 230, 224)|rgb(155, 59, 38)|1|none|none|auto|auto|none|none|auto",
    },
    1280: {
        "html": "0|0|1280|617.55|block|border-box|0px|0px|0px|none|0px|16px|400|normal|0 1 auto|normal|normal|normal|0px|start|baseline|normal|static|rgb(0, 0, 0)|rgba(0, 0, 0, 0)|rgb(0, 0, 0)|1|none|none|auto|auto|none|none|smooth",
        "00 h1 ": "40|28|234.58|48|block|border-box|0px 0px 4px|0px|0px|none|0px|40px|500|48px|0 1 auto|normal|normal|normal|auto|start|baseline|normal|static|rgb(28, 35, 51)|rgba(0, 0, 0, 0)|rgb(28, 35, 51)|1|none|none|auto|auto|none|none|auto",
        "01 span badge": "290.58|40.77|85.56|26.47|inline-block|border-box|0px|5.04px 8.64px|1px|solid|3px|14.4px|600|14.4px|0 1 auto|normal|normal|normal|0px|center|baseline|nowrap|static|color(srgb 0.531373 0.37451 0.135294)|color(srgb 0.979922 0.922039 0.822667)|color(srgb 0.970196 0.810196 0.551569)|1|none|none|auto|auto|none|none|auto",
        "02 div puzzle-player-controls": "40|87|1200|62.58|flex|border-box|-9px 0px 16px|0px|0px|none|0px|16px|400|24.8px|0 1 auto|flex-start|normal|8px 16px|0px|start|baseline|normal|static|rgb(28, 35, 51)|rgba(0, 0, 0, 0)|rgb(28, 35, 51)|1|none|none|auto|auto|none|none|auto",
        "03 button puzzle-player-tool-trigger": "40|87|151|38.78|flex|border-box|0px|6.4px 8px|1px|solid|3px|16px|600|24px|1 0 auto|center|normal|8px|36px|center|middle|normal|static|rgb(28, 35, 51)|rgb(251, 248, 241)|rgb(127, 117, 95)|1|none|none|pointer|auto|none|none|auto",
        "04 div puzzle-player-tool-menu": "0|0|0|0|none|border-box|0px|8px|1px|solid|4px|16px|400|24.8px|0 1 auto|normal|normal|4px|0px|start|baseline|normal|absolute|rgb(28, 35, 51)|rgb(251, 248, 241)|rgb(127, 117, 95)|1|rgba(28, 35, 51, 0.22) 0px 12px 32px 0px|none|auto|auto|none|none|auto",
        "05 button player-tool-item": "0|0|0|0|flex|border-box|0px|4px 8px|0px|none|3px|16px|600|24.8px|0 1 auto|center|normal|8px|36px|left|baseline|normal|static|rgb(31, 95, 91)|rgb(230, 239, 236)|rgb(31, 95, 91)|1|none|none|pointer|auto|none|none|auto",
        "06 button player-tool-item": "0|0|0|0|flex|border-box|0px|4px 8px|0px|none|3px|16px|400|24.8px|0 1 auto|center|normal|8px|36px|left|baseline|normal|static|rgb(28, 35, 51)|rgba(0, 0, 0, 0)|rgb(28, 35, 51)|1|none|none|pointer|auto|none|none|auto",
        "07 button player-tool-item": "0|0|0|0|flex|border-box|0px|4px 8px|0px|none|3px|16px|400|24.8px|0 1 auto|center|normal|8px|36px|left|baseline|normal|static|rgb(28, 35, 51)|rgba(0, 0, 0, 0)|rgb(28, 35, 51)|1|none|none|pointer|auto|none|none|auto",
        "08 button player-tool-item": "0|0|0|0|flex|border-box|0px|4px 8px|0px|none|3px|16px|400|24.8px|0 1 auto|center|normal|8px|36px|left|baseline|normal|static|rgb(28, 35, 51)|rgba(0, 0, 0, 0)|rgb(28, 35, 51)|1|none|none|pointer|auto|none|none|auto",
        "09 button puzzle-player-region": "199|87|49|38.78|flex|border-box|0px|6.4px 8px|1px|solid|3px|16px|600|24px|0 1 auto|center|normal|8px|36px|center|middle|normal|static|rgb(28, 35, 51)|rgb(251, 248, 241)|rgb(127, 117, 95)|1|none|none|pointer|auto|none|none|auto",
        "10 p puzzle-player-solved": "0|0|0|0|none|border-box|0px|0px 12px|1px 1px 1px 3px|solid|3px|16px|400|24.8px|0 1 auto|center|normal|8px|36px|start|baseline|normal|static|rgb(28, 35, 51)|rgb(231, 239, 230)|rgb(47, 107, 58)|1|none|none|auto|auto|none|none|auto",
        "11 button undo": "264|87|92.19|38.78|flex|border-box|0px|6.4px 12px|1px|solid|3px|16px|600|24px|0 1 auto|center|normal|8px|36px|center|middle|normal|static|rgb(28, 35, 51)|rgb(251, 248, 241)|rgb(127, 117, 95)|0.55|none|none|not-allowed|auto|none|none|auto",
        "12 button redo": "364.19|87|89.33|38.78|flex|border-box|0px|6.4px 12px|1px|solid|3px|16px|600|24px|0 1 auto|center|normal|8px|36px|center|middle|normal|static|rgb(28, 35, 51)|rgb(251, 248, 241)|rgb(127, 117, 95)|0.55|none|none|not-allowed|auto|none|none|auto",
        "13 button reset": "461.52|87|92.77|38.78|flex|border-box|0px|6.4px 12px|1px|solid|3px|16px|600|24px|0 1 auto|center|normal|8px|36px|center|middle|normal|static|rgb(28, 35, 51)|rgb(251, 248, 241)|rgb(127, 117, 95)|0.55|none|none|not-allowed|auto|none|none|auto",
        "14 div puzzle-player-confirm": "0|0|0|0|none|border-box|0px|12px 16px|1px|solid|4px|16px|400|24.8px|0 1 auto|normal|normal|normal|0px|start|baseline|normal|absolute|rgb(28, 35, 51)|rgb(251, 248, 241)|rgb(127, 117, 95)|1|rgba(28, 35, 51, 0.22) 0px 12px 32px 0px|none|auto|auto|none|none|auto",
        "15 button btn": "0|0|0|0|flex|border-box|0px|6.4px 12px|1px|solid|3px|16px|600|24px|0 1 auto|center|normal|8px|36px|center|middle|normal|static|rgb(255, 255, 255)|rgb(155, 59, 38)|rgb(155, 59, 38)|1|none|none|pointer|auto|none|none|auto",
        "16 button btn": "0|0|0|0|flex|border-box|0px|6.4px 12px|1px|solid|3px|16px|600|24px|0 1 auto|center|normal|8px|36px|center|middle|normal|static|rgb(28, 35, 51)|rgb(251, 248, 241)|rgb(127, 117, 95)|1|none|none|pointer|auto|none|none|auto",
        "17 button hint": "562.28|87|60.94|38.78|flex|border-box|0px|6.4px 12px|1px|solid|3px|16px|600|24px|0 1 auto|center|normal|8px|36px|center|middle|normal|static|rgb(28, 35, 51)|rgb(251, 248, 241)|rgb(127, 117, 95)|1|none|none|pointer|auto|none|none|auto",
        "18 button btn": "639.22|87|25.33|38.78|flex|border-box|0px|6.4px 5px|1px|solid|3px|16px|600|24px|0 1 auto|center|normal|8px|36px|center|middle|normal|static|rgb(28, 35, 51)|rgb(251, 248, 241)|rgb(127, 117, 95)|0.55|none|none|not-allowed|auto|none|none|auto",
        "19 button btn": "711.08|87|25.33|38.78|flex|border-box|0px|6.4px 5px|1px|solid|3px|16px|600|24px|0 1 auto|center|normal|8px|36px|center|middle|normal|static|rgb(28, 35, 51)|rgb(251, 248, 241)|rgb(127, 117, 95)|1|none|none|pointer|auto|none|none|auto",
        "20 button puzzle-player-probe": "40|125.8|70.59|38.78|flex|border-box|0px|6.4px 12px|1px|solid|3px|16px|600|24px|0 1 auto|center|normal|4px|36px|center|middle|normal|static|rgb(28, 35, 51)|rgb(251, 248, 241)|rgb(127, 117, 95)|1|none|none|pointer|auto|none|none|auto",
        "21 button btn": "0|0|0|0|none|border-box|0px|6.4px 12px|1px|solid|3px|16px|600|24px|0 1 auto|center|normal|4px|36px|center|middle|normal|static|rgb(28, 35, 51)|rgb(251, 248, 241)|rgb(127, 117, 95)|1|none|none|pointer|auto|none|none|auto",
        "22 button btn": "0|0|0|0|none|border-box|0px|6.4px 12px|1px|solid|3px|16px|600|24px|0 1 auto|center|normal|4px|36px|center|middle|normal|static|rgb(28, 35, 51)|rgb(251, 248, 241)|rgb(127, 117, 95)|1|none|none|pointer|auto|none|none|auto",
        "23 button btn": "0|0|0|0|none|border-box|0px|6.4px 12px|1px|solid|3px|16px|600|24px|0 1 auto|center|normal|4px|36px|center|middle|normal|static|rgb(28, 35, 51)|rgb(251, 248, 241)|rgb(127, 117, 95)|1|none|none|pointer|auto|none|none|auto",
        "24 p puzzle-player-probe-note": "0|0|0|0|none|border-box|0px|0px|0px|none|0px|12.48px|400|12.48px|1 1 0px|normal|normal|normal|0px|start|baseline|normal|static|rgb(92, 96, 112)|rgba(0, 0, 0, 0)|rgb(92, 96, 112)|1|none|none|auto|auto|none|none|auto",
        "25 div puzzle-player": "40|165.58|1200|373.64|block|border-box|0px|0px|0px|none|0px|16px|400|24.8px|0 1 auto|normal|normal|normal|0px|start|baseline|normal|static|rgb(28, 35, 51)|rgba(0, 0, 0, 0)|rgb(28, 35, 51)|1|none|none|auto|auto|none|none|auto",
        "26 td player-cell": "129.83|243.22|28|28|table-cell|border-box|0px|0px|0px 1px 1px 0px|solid|0px|14px|400|14px|0 1 auto|normal|normal|normal|0px|start|middle|normal|static|rgb(28, 35, 51)|rgb(255, 253, 248)|rgb(28, 35, 51)|1|none|none|pointer|auto|none|none|auto",
        "27 div puzzle-player-offer": "0|0|0|0|none|border-box|auto|12px 16px|2px|solid|4px|14.4px|400|22.32px|0 1 auto|center|normal|8px|0px|start|baseline|normal|fixed|rgb(28, 35, 51)|rgb(230, 239, 236)|rgb(31, 95, 91)|1|rgba(28, 35, 51, 0.22) 0px 12px 32px 0px|none|auto|auto|none|none|auto",
        "28 button btn": "0|0|0|0|inline-flex|border-box|0px|6.4px 12px|1px|solid|3px|16px|600|24px|0 1 auto|center|normal|4px|0px|center|middle|normal|static|rgb(28, 35, 51)|rgb(251, 248, 241)|rgb(127, 117, 95)|1|none|none|pointer|auto|none|none|auto",
        "29 button btn": "0|0|0|0|inline-flex|border-box|0px|6.4px 12px|1px|solid|3px|16px|600|24px|0 1 auto|center|normal|4px|0px|center|middle|normal|static|rgb(28, 35, 51)|rgb(251, 248, 241)|rgb(127, 117, 95)|1|none|none|pointer|auto|none|none|auto",
        "hover plain": "562.28|87|60.94|38.78|flex|border-box|0px|6.4px 12px|1px|solid|3px|16px|600|24px|0 1 auto|center|normal|8px|36px|center|middle|normal|static|rgb(28, 35, 51)|rgb(241, 235, 221)|rgb(127, 117, 95)|1|none|none|pointer|auto|none|none|auto",
        "focus plain": "562.28|87|60.94|38.78|flex|border-box|0px|6.4px 12px|1px|solid|3px|16px|600|24px|0 1 auto|center|normal|8px|36px|center|middle|normal|static|rgb(28, 35, 51)|rgb(241, 235, 221)|rgb(127, 117, 95)|1|none|solid|pointer|auto|none|none|auto",
        "active plain": "562.28|87|60.94|38.78|flex|border-box|0px|6.4px 12px|1px|solid|3px|16px|600|24px|0 1 auto|center|normal|8px|36px|center|middle|normal|static|rgb(28, 35, 51)|rgb(241, 235, 221)|rgb(127, 117, 95)|1|rgba(108, 117, 125, 0.5) 0px 0px 0px 4px|solid|pointer|auto|none|none|auto",
        "pressed plain": "562.28|87|60.94|38.78|flex|border-box|0px|6.4px 12px|1px|solid|3px|16px|600|24px|0 1 auto|center|normal|8px|36px|center|middle|normal|static|rgb(28, 35, 51)|rgb(241, 235, 221)|rgb(127, 117, 95)|1|none|none|pointer|auto|none|none|auto",
        "disabled plain": "562.28|87|60.94|38.78|flex|border-box|0px|6.4px 12px|1px|solid|3px|16px|600|24px|0 1 auto|center|normal|8px|36px|center|middle|normal|static|rgb(92, 96, 112)|rgb(251, 248, 241)|rgb(214, 205, 185)|0.55|none|none|not-allowed|none|none|none|auto",
        "hover danger": "281|209.91|117.3|38.78|flex|border-box|0px|6.4px 12px|1px|solid|3px|16px|600|24px|0 1 auto|center|normal|8px|36px|center|middle|normal|static|rgb(255, 255, 255)|rgb(122, 45, 28)|rgb(122, 45, 28)|1|none|none|pointer|auto|none|none|auto",
        "focus danger": "281|209.91|117.3|38.78|flex|border-box|0px|6.4px 12px|1px|solid|3px|16px|600|24px|0 1 auto|center|normal|8px|36px|center|middle|normal|static|rgb(255, 255, 255)|rgb(122, 45, 28)|rgb(127, 117, 95)|1|none|solid|pointer|auto|none|none|auto",
        "active danger": "281|209.91|117.3|38.78|flex|border-box|0px|6.4px 12px|1px|solid|3px|16px|600|24px|0 1 auto|center|normal|8px|36px|center|middle|normal|static|rgb(255, 255, 255)|rgb(155, 59, 38)|rgb(155, 59, 38)|1|rgba(225, 83, 97, 0.5) 0px 0px 0px 4px|solid|pointer|auto|none|none|auto",
        "disabled danger": "281|209.91|117.3|38.78|flex|border-box|0px|6.4px 12px|1px|solid|3px|16px|600|24px|0 1 auto|center|normal|8px|36px|center|middle|normal|static|rgb(155, 59, 38)|rgb(251, 248, 241)|rgb(155, 59, 38)|0.55|none|none|not-allowed|none|none|none|auto",
        "error alert": "40|96|1200|58.8|block|border-box|0px 0px 16px|16px|1px 1px 1px 4px|solid|4px|16px|400|24.8px|0 1 auto|normal|normal|normal|0px|start|baseline|normal|relative|rgb(28, 35, 51)|rgb(245, 230, 224)|rgb(155, 59, 38)|1|none|none|auto|auto|none|none|auto",
    },
}
# fmt: on
