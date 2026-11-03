"""CARD-332 AC-2 — the reader link in a browser: its geometry, and Copy.

Two things only a browser can be asked about, both found by review rather
than by the suite: the row's layout (cycle 1, F-003 — the render caught a
defect no test then guarded) and what the Copy button says when it has
copied, or cannot (cycle 1, F-007).

Why the geometry is here at all
-------------------------------
The link itself is asserted in ``tests/test_book_player_domain.py``: that it
is there, that its key is ADR-0041/R1's, and that it carries nothing else.
None of that is a layout fact, and the defect this card's first render
exposed was only a layout fact — the 43-character URL sat in
``.item-info``'s flex row, widened the row's ``1fr`` column, and pushed the
title box and the row's buttons out of the card, with the whole suite green
through it. The fix is a placement (``.play-link`` is a third grid row of its
own, free to shrink) and a wrapping rule (``.play-url`` may break anywhere),
and **cycle 1 measured that nothing held them**: deleting both declarations
from ``admin.css`` left 159 tests passing, because the markup is
byte-identical with the CSS gone and only the geometry regresses.

So this is a real Chromium test (pytest-playwright, ADR-0038/R7), on the
harness ``tests/test_book_setup_print_mobile.py`` and
``tests/test_books_list_mobile.py`` already use — the fixtures that refuse
loudly when Playwright or Chromium is missing (ADR-0038/R8) are imported from
``tests/test_puzzle_solver_page.py`` rather than copied. It is a file of its
own rather than a cell added to either: both of those are this card's G-3
controls, left passing unchanged, and the browser family ``rank_durations``
measures is ``tests/test_puzzle_solver*`` (see
``tests/test_browser_fixture_scope.py``), which this name stays out of.

Two widths, because the two declarations bite at different ones
---------------------------------------------------------------
Measured on this build, first row, 43-character URL whose one line is 316 px
wide:

===========  =============  ==============  ====================
viewport     row box        ``.play-url``   page ``scrollWidth``
===========  =============  ==============  ====================
390 px       33 → 357       107 px          **401** px
1024 px      277 → 780      181 px          1024 px
1440 px      277 → 1092     316 px          1440 px
===========  =============  ==============  ====================

* At **390 px** the column is 107 px, far narrower than any line the URL can
  make, so ``overflow-wrap: anywhere`` is what keeps the text inside its box.
  Containment is *not* measured there: at 390 px this screen already puts
  ``.item-actions`` 44 px outside the row (401 > 390 — the page scrolls
  sideways) **with this card's fix in place and before it**, which is a
  pre-existing arrangement-screen defect at phone width and none of this
  card's business. Measured, named, and left to the card that owns it.
* At **1024 px** — the panel's ordinary desktop width, sidebar and all — the
  row holds its contents, so that is where "nothing ends outside the row" is a
  claim about this card rather than about that defect. The URL still wraps
  there (181 px of column against a 316 px line), so both declarations are
  load-bearing at this width too.
* At 1440 px the URL fits on one line and neither declaration does any work,
  which is why no cell measures there.

All of it is the browser's own geometry: an element's
``getBoundingClientRect`` and, for the clipping question, the measurement
``tests/test_book_setup_print_mobile.py`` uses — a box whose text is wider
than itself has ``scrollWidth > clientWidth``.
"""

from __future__ import annotations

import threading

import pytest

from nonogram.admin.book_manager import BookManager
from nonogram.admin.print_specs import PrintSpec
from nonogram.admin.puzzle_review import PuzzleReviewService
from tests.helpers.db import sqlite_session_scope
from tests.test_puzzle_solver_page import (  # noqa: F401
    _build_app,
    _expected_clues,
    _unique_grid,
    browser_page,
    browser_type,
)

#: Where ``overflow-wrap: anywhere`` is load-bearing (the column is 107 px).
PHONE = {"width": 390, "height": 844}

#: Where the row holds its own contents, so containment measures this card.
DESKTOP = {"width": 1024, "height": 900}

#: ADR-0041/R1's base as the owner wrote it, and as
#: ``tests/test_book_player_domain.py`` spells it: the 43-character URL the
#: first render was measured on is this base plus ``/play/`` plus a ten-hex
#: key.
BASE = "https://nonogram.adverax.io"

#: The shortest URL this measurement is worth taking on. The render that found
#: the defect had 43 characters; a shorter one would fit the column and
#: measure nothing.
URL_CHARACTERS_MIN = 40

#: A 6 x 9 in trim in cm — any trim ``set_print_spec`` accepts will do; the
#: spec is here only to carry the player domain onto the book.
TRIM = ("15.24", "22.86")

#: Three puzzles, so a placement that happens to work for the first row has to
#: work for the rest.
MEMBERS = 3

#: How far two edges may differ and still be "the same column". One device
#: pixel: the two boxes are placed by the same grid line, so the browser puts
#: them at the same subpixel offset, and the slack is for the rounding only.
EDGE_SLACK_PX = 1.0

_ROW_GEOMETRY = """() => [...document.querySelectorAll('.puzzle-list-item')].map((row) => {
  const box = (el) => {
    const b = el.getBoundingClientRect();
    return {left: b.left, right: b.right, top: b.top, bottom: b.bottom, width: b.width};
  };
  const url = row.querySelector('.play-url');
  return {
    row: box(row),
    link: box(row.querySelector('.play-link')),
    url: box(url),
    title: box(row.querySelector('.item-title input[type=text]')),
    actions: box(row.querySelector('.item-actions')),
    urlText: url.textContent.trim(),
    urlScrollWidth: url.scrollWidth,
    urlClientWidth: url.clientWidth,
  };
})"""


#: How many line boxes each shown URL's text occupies. The technique
#: ``tests/test_books_list_mobile.py`` uses for the same question: a Range over
#: the text node yields one rect per line it is laid out on.
_URL_LINES = """() => [...document.querySelectorAll('.play-url')].map((code) => {
  const range = document.createRange();
  range.selectNodeContents(code);
  return new Set([...range.getClientRects()].map((r) => Math.round(r.top))).size;
})"""


def _member(store, grid) -> str:
    """One approved puzzle whose clues are filled in, as a book member needs."""
    rows, cols = _expected_clues(grid)
    puzzle_id = store.add_puzzle(
        grid=grid,
        clues_rows=rows,
        clues_cols=cols,
        width=len(grid[0]),
        height=len(grid),
        theme="christmas",
        difficulty_score=20,
        difficulty_tier="easy",
        quality_score=50,
        recognizability="medium",
        strategies_used=[],
        batch_id=None,
        source_image="tree.png",
    )
    store.approve_puzzle(puzzle_id)
    return puzzle_id


@pytest.fixture
def live_arrangement(tmp_path, monkeypatch):
    """The real panel over SQLite on loopback, on a book that has a base stored."""
    from werkzeug.serving import make_server

    scope = sqlite_session_scope(tmp_path, "card-332-live.db")
    app = _build_app("sqlite", scope, monkeypatch)
    store = PuzzleReviewService(session_factory=scope)
    books = BookManager(session_factory=scope, puzzle_store=store)
    book_id = books.create_book("Winter", "A winter book.", "christmas", "adults")
    ids = [_member(store, _unique_grid(15, 15, seed=332 + n)) for n in range(MEMBERS)]
    assert books.add_puzzles_to_book(book_id, ids)
    assert len(books.get_book(book_id).puzzle_ids) == MEMBERS
    assert books.set_print_spec(
        book_id, PrintSpec(trim_width_cm=TRIM[0], trim_height_cm=TRIM[1], player_domain=BASE)
    )
    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/book/{book_id}/arrange-puzzles"
    finally:
        server.shutdown()
        thread.join()


def _open_at(page, url, viewport) -> list[str]:
    """``url`` at ``viewport``, collecting anything the console complains of."""
    errors: list[str] = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.set_viewport_size(viewport)
    page.goto(url)
    page.wait_for_selector(".puzzle-list-item .play-url")
    return errors


def _rows(page) -> list[dict]:
    """Every row's geometry, on a page that really shows long reader links.

    The measurement is only worth as much as what it was taken on, so the
    three rows and the URL in each are checked before any geometry is read
    from them.
    """
    measured = page.evaluate(_ROW_GEOMETRY)
    assert len(measured) == MEMBERS, measured
    for row in measured:
        assert row["urlText"].startswith(f"{BASE}/play/"), row["urlText"]
        assert len(row["urlText"]) >= URL_CHARACTERS_MIN, row["urlText"]
    return measured


@pytest.fixture
def phone_page(browser_page, live_arrangement):  # noqa: F811
    """The arrangement screen at 390 px, with a clean console."""
    errors = _open_at(browser_page, live_arrangement, PHONE)
    yield browser_page
    assert errors == [], errors


@pytest.fixture
def desktop_page(browser_page, live_arrangement):  # noqa: F811
    """The arrangement screen at 1024 px, with a clean console."""
    errors = _open_at(browser_page, live_arrangement, DESKTOP)
    yield browser_page
    assert errors == [], errors


@pytest.mark.browser
class TestArrangePlayLink_TheRowHoldsItsContents:
    """At 1024 px the link is a line of its own under the title, and no part
    of the row ends outside the row."""

    def test_the_link_sits_in_the_title_column(self, desktop_page) -> None:
        rows = _rows(desktop_page)

        offsets = [row["link"]["left"] - row["title"]["left"] for row in rows]
        assert all(abs(offset) <= EDGE_SLACK_PX for offset in offsets), offsets

    def test_the_link_sits_below_the_title(self, desktop_page) -> None:
        rows = _rows(desktop_page)

        tops = [(row["link"]["top"], row["title"]["bottom"]) for row in rows]
        assert all(link_top >= title_bottom for link_top, title_bottom in tops), tops

    def test_nothing_in_the_row_ends_outside_the_row(self, desktop_page) -> None:
        rows = _rows(desktop_page)

        escaped = [
            (name, part, row["row"])
            for row in rows
            for name in ("link", "url", "title", "actions")
            for part in [row[name]]
            if part["left"] < row["row"]["left"] - EDGE_SLACK_PX
            or part["right"] > row["row"]["right"] + EDGE_SLACK_PX
            or part["bottom"] > row["row"]["bottom"] + EDGE_SLACK_PX
        ]
        assert escaped == [], escaped


@pytest.mark.browser
class TestArrangePlayLink_TheUrlWrapsRatherThanSpill:
    """At 390 px the column is 107 px wide and the URL's one line would be
    316 px — ``overflow-wrap: anywhere``'s whole job."""

    def test_the_link_still_sits_in_the_title_column(self, phone_page) -> None:
        rows = _rows(phone_page)

        offsets = [row["link"]["left"] - row["title"]["left"] for row in rows]
        assert all(abs(offset) <= EDGE_SLACK_PX for offset in offsets), offsets

    def test_the_url_stays_inside_the_row(self, phone_page) -> None:
        # Measured both ways on this build: the wrapped URL ends at 297 px in
        # a row that ends at 357 px; with ``overflow-wrap`` gone its one
        # unbroken line is 316 px wide and ends at 506 px — 149 px outside the
        # card, which is the render's own defect. The second clause is
        # ``tests/test_book_setup_print_mobile.py``'s clipping measure, so a
        # future ``overflow: hidden`` cannot make this cell green by hiding
        # the spill instead of wrapping it.
        rows = _rows(phone_page)

        spilled = [
            (row["url"], row["row"])
            for row in rows
            if row["url"]["right"] > row["row"]["right"] + EDGE_SLACK_PX
            or row["url"]["left"] < row["row"]["left"] - EDGE_SLACK_PX
            or row["urlScrollWidth"] > row["urlClientWidth"] + EDGE_SLACK_PX
        ]
        assert spilled == [], spilled

    def test_the_url_is_broken_over_several_lines(self, phone_page) -> None:
        # The positive form of the same fact, because containment alone could
        # be had by a column wide enough to need no wrapping: four lines on
        # this build, one with the declaration gone.
        _rows(phone_page)

        lines = phone_page.evaluate(_URL_LINES)
        assert len(lines) == MEMBERS, lines
        assert all(count >= 2 for count in lines), lines


#: What each branch of ``copyPlayUrl`` says. Transcribed from the template,
#: not imported from it: a test that read the words out of the thing it checks
#: would agree with any words at all.
COPIED = "Copied"
NO_CLIPBOARD = "Copying needs a secure connection — select the link and copy it"

#: Record every text the first row's live region is given, in order.
_RECORD_SAID = """() => {
  window.__said = [];
  const node = document.querySelector('.puzzle-list-item .play-copy-said');
  new MutationObserver(() => {
    const text = node.textContent.trim();
    if (text) window.__said.push(text);
  }).observe(node, {childList: true, characterData: true, subtree: true});
}"""

#: How long a clipboard write on loopback may take before this is a failure.
#: Bounded so a regression reds in two seconds rather than in Playwright's
#: thirty.
_SAID_TIMEOUT_MS = 2000

#: How long Copy may take to become clickable (cycle 2, F-204). Every
#: ``click()`` in this module passes it, and the bound is measured rather than
#: defensive: deleting ``.play-url``'s ``overflow-wrap`` declaration reds
#: **five** cells here, not the three the round claimed, and two of the five
#: fail as Playwright click timeouts — the unbroken URL widens its row until
#: ``card-body`` covers the button, so the click retries for the default 30 s
#: (57 attempts) and the module's run goes 7.53 s -> 66.91 s. The cause is in
#: the first retry's message ("card-body ... intercepts pointer events"); the
#: other 56 only cost time. Bounded, that shape reports in two seconds with
#: the same readable cause.
_CLICK_TIMEOUT_MS = 2000


@pytest.mark.browser
class TestArrangePlayLink_CopySaysWhatHappened:
    """Every outcome of Copy reaches a live region, not only ``title``.

    ``title`` is a hover affordance: a screen reader does not announce it and
    a touch user never sees it, so before this the no-clipboard branch made
    the button look inert (cycle 1, F-007). The region is ``role="status"``
    with ``aria-live="polite"``, and these cells read its text — which is what
    a screen reader is given — rather than the title alone.
    """

    def _first_link(self, page):
        page.wait_for_selector(".puzzle-list-item .play-url")
        link = page.locator(".puzzle-list-item .play-link").first
        said = link.locator(".play-copy-said")
        # It starts silent: a live region that already held words would
        # announce the previous outcome instead of this one.
        assert said.inner_text().strip() == ""
        assert said.get_attribute("role") == "status"
        assert said.get_attribute("aria-live") == "polite"
        return link, said

    def test_a_copy_that_works_is_announced(self, desktop_page) -> None:
        desktop_page.context.grant_permissions(["clipboard-read", "clipboard-write"])
        link, _said = self._first_link(desktop_page)
        url = link.locator(".play-url").inner_text().strip()
        # Every text the region is given, recorded as it arrives. Read back
        # afterwards instead, and this cell would be a race against the
        # template's own 1.5 s reset: "Copied" is transient by design.
        desktop_page.evaluate(_RECORD_SAID)

        link.locator("button").click(timeout=_CLICK_TIMEOUT_MS)

        desktop_page.wait_for_function("() => window.__said.length > 0", timeout=_SAID_TIMEOUT_MS)
        assert desktop_page.evaluate("() => window.__said")[0] == COPIED
        # And it really copied the URL beside it, not something else.
        assert desktop_page.evaluate("() => navigator.clipboard.readText()").strip() == url

    def test_a_browser_with_no_clipboard_api_says_so(self, desktop_page) -> None:
        # The branch that said nothing a user could perceive. The API is
        # removed from the page rather than mocked out, so the branch is
        # reached the way an insecure context reaches it.
        desktop_page.evaluate(
            "() => Object.defineProperty(navigator, 'clipboard',"
            " {value: undefined, configurable: true})"
        )
        link, said = self._first_link(desktop_page)

        link.locator("button").click(timeout=_CLICK_TIMEOUT_MS)

        assert said.inner_text().strip() == NO_CLIPBOARD
        assert link.locator("button").get_attribute("title") == NO_CLIPBOARD

    def test_what_the_region_says_takes_no_width_from_the_url(self, phone_page) -> None:
        """The spoken region is off the URL's flex line (cycle 2, F-203).

        Measured at 390 px, where the column is narrowest, on the longest of
        the three messages — and on the branch that never clears, which is why
        geometry is worth a cell of its own here. ``copyPlayUrl`` resets the
        success message after 1.5 s; the two failure branches do not, because
        their words are an instruction to act on rather than a transient
        "Copied". So while the region was a fourth item on the URL's flex
        line, an insecure context squeezed ``.play-url`` from 98.98 px to
        30.50 px and left it there for as long as the page stayed open.

        The fix bounds rather than resets: the region cannot take width from
        the URL in any branch. This asserts the geometry the sibling cell
        above does not — it reads text, at 1024 px only — so a future return
        of the region to that line reds here instead of passing.
        """
        phone_page.evaluate(
            "() => Object.defineProperty(navigator, 'clipboard',"
            " {value: undefined, configurable: true})"
        )
        before = [row["url"]["width"] for row in _rows(phone_page)]
        link, said = self._first_link(phone_page)

        link.locator("button").click(timeout=_CLICK_TIMEOUT_MS)

        # It really is speaking the longest message, so the width below was
        # measured under the load that used to move it.
        assert said.inner_text().strip() == NO_CLIPBOARD
        after = [row["url"]["width"] for row in _rows(phone_page)]
        assert len(after) == len(before) == MEMBERS, (before, after)
        moved = [
            (was, now) for was, now in zip(before, after)
            if abs(now - was) > EDGE_SLACK_PX
        ]
        assert moved == [], moved
        # And the URL is still contained and still wrapped while it speaks:
        # an unsqueezed column would also be had by letting the row spill.
        spilled = [
            (row["url"], row["row"])
            for row in _rows(phone_page)
            if row["url"]["right"] > row["row"]["right"] + EDGE_SLACK_PX
            or row["urlScrollWidth"] > row["urlClientWidth"] + EDGE_SLACK_PX
        ]
        assert spilled == [], spilled
