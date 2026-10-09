"""CARD-201, review cycle 3, F-22 — the pipeline connector arrow's real layout.

``tests/test_book_finalise_guide_preview.py`` reads the Finalise screen's guide
preview as a string of HTML (``html.parser.HTMLParser``) — it proves the right
*content* is there, never how a browser lays it out. F-22 is a CSS defect:
``.guide-pipeline-step + .guide-pipeline-step::before`` (``static/admin.css``)
draws the connecting arrow between two pipeline-step boxes, but
``.guide-pipeline-step`` is itself ``display: flex; flex-direction: column``,
so the ``::before`` used to be inserted as that box's own FIRST flex child —
stacked above the step's own label, inside the box it is attached to, not a
connector sitting between two boxes. No string-level test can see this: the
HTML the server sends never changes, only how the browser paints it. This is
a real Chromium test (pytest-playwright, ADR-0038/R7/R8, the same tier
``tests/test_book_setup_print_mobile.py`` uses) for exactly that reason, with
``browser_page``/``browser_type`` imported from ``tests/test_puzzle_solver_page.py``
rather than copied, per that module's own docstring.

**What a browser's own layout proves wrong about the bug, measured two ways:**

1. Before the fix every step after the first was measurably TALLER than the
   first (the in-flow arrow added its own line to the box) — the first step
   has no ``::before`` at all (``:first-child`` is never a match for
   ``X + X``), so it is the one honest "what this box looks like with no
   arrow" reference every other step is compared against.
2. Before the fix the ``::before``'s own computed ``position`` was ``static``
   (the sheet set none, so initial value), meaning it is laid out in normal
   flow *inside* the box; after the fix it is ``absolute``, taken out of flow
   and centred over the gap between two boxes by its own ``left``/``transform``
   — read directly off ``getComputedStyle(el, '::before')``, which Chromium
   resolves to real pixel values for exactly this kind of check.

Both signals are read straight from the live, real-browser layout — not
parsed HTML, not a hand-reimplemented box model.
"""

from __future__ import annotations

import threading

import pytest

import nonogram.admin.book_manager as book_manager_module
from nonogram.admin.book_manager import BookManager
from tests.test_puzzle_solver_page import browser_page, browser_type  # noqa: F401

#: Wide enough that all 4 of GUIDE_ASSUME_STEPS' boxes sit on one row (measured
#: while building this test: narrower viewports wrap the 4th step to a new
#: row, which is a real, separate ``flex-wrap`` behaviour this test does not
#: concern itself with — only the connector's own placement between two
#: boxes that ARE on the same row).
DESKTOP = {"width": 1000, "height": 1000}


@pytest.fixture
def live_finalize(monkeypatch):
    """The real panel, served on loopback, at a draft book's Finalise screen.

    Memory mode, one draft book with no puzzles: the guide preview's
    pipeline diagram is static content, present on every Finalise screen
    regardless of the book's own membership.
    """
    from werkzeug.serving import make_server

    monkeypatch.setenv("TESTING", "true")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(book_manager_module, "_book_manager", BookManager(session_factory=None))
    from nonogram.admin.app import create_app

    app = create_app()
    app.config["TESTING"] = True
    book_id = app.book_manager.create_book("Winter", "a book", "generic", "adults")
    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/book/{book_id}/finalize"
    finally:
        server.shutdown()
        thread.join()


#: Reads every ``.guide-pipeline-step``'s own box (``getBoundingClientRect``)
#: and, for every one but the first, the connector's computed geometry: its
#: own ``position``, and — resolving ``left``/``top`` against the step's own
#: border-box origin and ``transform``'s ``translate`` against the pseudo's
#: own resolved width/height, exactly as the browser itself composites it —
#: the connector's real viewport centre.
_PIPELINE_GEOMETRY = """() => {
  const steps = [...document.querySelectorAll('.guide-pipeline-step')];
  return steps.map((el, index) => {
    const rect = el.getBoundingClientRect();
    const style = getComputedStyle(el);
    const before = getComputedStyle(el, '::before');
    const borderLeft = parseFloat(style.borderLeftWidth) || 0;
    const borderTop = parseFloat(style.borderTopWidth) || 0;
    const result = {
      index,
      left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom,
      height: rect.height,
      beforePosition: before.position,
      arrowCenter: null,
    };
    if (before.content !== 'none') {
      const match = /matrix\\(([^,]+),([^,]+),([^,]+),([^,]+),([^,]+),([^,]+)\\)/.exec(before.transform);
      const tx = match ? parseFloat(match[5]) : 0;
      const ty = match ? parseFloat(match[6]) : 0;
      const left = rect.left + borderLeft + (parseFloat(before.left) || 0) + tx;
      const top = rect.top + borderTop + (parseFloat(before.top) || 0) + ty;
      const width = parseFloat(before.width) || 0;
      const height = parseFloat(before.height) || 0;
      result.arrowCenter = { x: left + width / 2, y: top + height / 2 };
    }
    return result;
  });
}"""


@pytest.mark.browser
class TestFinalisePipelinePreview_ArrowIsAConnectorNotAFlexChild:
    """F-22: the arrow sits between two pipeline-step boxes, not inside one."""

    @pytest.fixture
    def geometry(self, browser_page, live_finalize):  # noqa: F811
        errors: list[str] = []
        browser_page.on("pageerror", lambda exc: errors.append(str(exc)))
        browser_page.set_viewport_size(DESKTOP)
        browser_page.goto(live_finalize)
        browser_page.wait_for_selector(".guide-pipeline-step")
        geometry = browser_page.evaluate(_PIPELINE_GEOMETRY)
        assert errors == [], errors
        # GUIDE_ASSUME_STEPS is ASSUME/FOLLOW/BREAKS/PROVED — 4 steps, so 3
        # connectors (every step but the first).
        assert len(geometry) == 4, (
            f"found {len(geometry)} pipeline steps, not the 4 this test expects "
            "(re-check GUIDE_ASSUME_STEPS before trusting the indices below)"
        )
        return geometry

    def test_no_step_is_stretched_tall_by_an_in_flow_arrow(self, geometry):
        """Before the fix, every step but the first was taller than the
        first by roughly the arrow glyph's own line height, because the
        arrow was laid out as that box's own first flex child. The first
        step never carries a ``::before`` at all (``X + X`` never matches a
        ``:first-child``), so it is this test's own "no arrow" reference.
        """
        reference_height = geometry[0]["height"]
        assert geometry[0]["beforePosition"] == "static", (
            "sanity check: the first step must carry no ::before content at "
            "all, or the reference height below proves nothing"
        )
        for step in geometry[1:]:
            assert step["height"] == pytest.approx(reference_height, abs=1.0), (
                f"step {step['index']} is {step['height']:.1f} px tall against "
                f"the first step's {reference_height:.1f} px -- a taller step "
                "is the in-flow-arrow symptom F-22 found, not a connector "
                "sitting beside the box"
            )

    def test_the_connector_is_out_of_flow(self, geometry):
        """The mechanism of the fix: ``position: absolute`` (not the
        pre-fix ``static``) is what removes the arrow from this box's own
        flex layout in the first place.
        """
        for step in geometry[1:]:
            assert step["beforePosition"] == "absolute", (
                f"step {step['index']}'s connector has position: "
                f"{step['beforePosition']!r}, not 'absolute' -- it is still "
                "laid out in this box's own flex flow, which is the bug"
            )

    def test_the_connector_sits_strictly_between_the_two_boxes(self, geometry):
        """Not just "out of flow somewhere" — its own measured centre must
        fall in the gap between the previous box's right edge and this
        box's left edge, and be vertically centred on the row rather than
        pinned to the box's own top (where normal flow would have put it).

        Only checked for a pair genuinely on the same visual row (same
        ``top``): ``.guide-pipeline`` is ``flex-wrap: wrap`` inside a
        ``max-width: 68ch`` preview card, so the 4th of
        ``GUIDE_ASSUME_STEPS``' boxes wraps to a row of its own at this
        viewport regardless of this fix — "between the previous box and
        this one" is not a meaningful question across a wrap, and is not
        what F-22 is about.
        """
        same_row = [
            (previous, step)
            for previous, step in zip(geometry, geometry[1:])
            if previous["top"] == step["top"]
        ]
        assert same_row, "no two consecutive steps share a row -- nothing here to check"
        for previous, step in same_row:
            assert step["arrowCenter"] is not None, f"step {step['index']} drew no connector at all"
            x, y = step["arrowCenter"]["x"], step["arrowCenter"]["y"]
            assert previous["right"] < x < step["left"], (
                f"step {step['index']}'s connector centres at x={x:.1f}, not "
                f"between the previous box's right edge ({previous['right']:.1f}) "
                f"and this box's left edge ({step['left']:.1f})"
            )
            row_mid = (step["top"] + step["bottom"]) / 2
            assert y == pytest.approx(row_mid, abs=6.0), (
                f"step {step['index']}'s connector centres at y={y:.1f}, not "
                f"near the row's own vertical middle ({row_mid:.1f}) -- this is "
                "the pinned-to-the-top-of-the-box symptom of the pre-fix "
                "in-flow arrow"
            )
