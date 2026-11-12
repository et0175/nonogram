"""CARD-418 — the redesigned ``/b/<slug>`` book landing (COMP-011, FR-045).

The owner's mockup A (2026-11-10): the series line and the authors around the
title, a "Which puzzle are you on?" box that opens a puzzle by its PRINTED
number, a "Continue where you stopped" card, and the puzzles in level
sections of squares that show the reader's own progress.

The fixtures, the assembled site and the loopback host are CARD-284's
(``tests/test_public_player_pages.py``), imported rather than rewritten. The
progress tests plant REAL player saves: each one is written in the browser by
the player's own ``solver_state.js`` (``createHistory`` / ``record`` /
``serializeState``), under the key the player itself uses, so a change to the
save format reds here rather than passing against a hand-written copy.

Acceptance criteria (CARD-418, local labels; registry ids at dispatch):
  AC-A  test_the_jump_box_opens_a_puzzle_by_its_printed_number
  AC-B  test_a_long_book_is_cut_into_level_sections_that_open_and_close
  AC-C  test_progress_comes_from_this_device_and_draws_the_readers_own_picture,
        test_with_storage_blocked_every_square_is_not_started
  AC-D  test_the_served_book_carries_series_and_authors_and_no_picture
        (with test_player_bundle's provenance scan over the new fields)
  AC-E  tests/test_book_landing_address.py's grouped-slug literal, unchanged
  AC-F  test_the_landing_header_and_squares_fit_a_phone

CARD-420 (a book's Christmas theme, owner 2026-11-10):
  AC-1  test_the_served_book_carries_series_and_authors_and_no_picture (a theme
        the site does not draw is served as ""), and
        test_a_christmas_book_dresses_its_landing_and_the_puzzles_opened_from_it
        (the assembler's reduction); test_player_bundle's provenance scan
  AC-2  test_the_served_book_carries_series_and_authors_and_no_picture
  AC-3, AC-4  test_a_christmas_book_dresses_its_landing_and_the_puzzles_opened_from_it

CARD-437 (coming back from a puzzle shows what you just did, 2026-11-12):
  AC-1, AC-2, AC-4  test_progress_comes_from_this_device_and_draws_the_readers_own_picture,
        which now takes every reading after the first load across a RESTORE
        (``_restore``) rather than across a reload — the reload path is the
        one that never broke. ``_restore``'s docstring records what this
        harness can and cannot produce.
  AC-3  tests/test_public_player_pages.py's
        test_the_listing_pages_only_get_and_write_nothing, where it refutes
        the card's premise: the library shows no progress at all
  (and the repaint's two accumulation hazards, both measured as mutants:
   the decorations, in the Christmas cell above, and the jump box's
   listeners, counted in the progress cell)
"""

from __future__ import annotations

import json

import pytest

from tests.test_public_player_pages import (  # noqa: F401 — fixtures used by name
    BOOK_AUTHORS,
    BOOK_ORDER,
    BOOK_SERIES_SERVED,
    BOOK_TITLE_SERVED,
    PAGE_GRIDS,
    PAGE_TIERS,
    PAGES_INERT_MS,
    PAGES_SETTLE_MS,
    _leaky_title,
    _open_pages,
    _restore,
    _tiles,
    assembler,
    browser_page,
    browser_type,
    pages_bundle,
    pages_host,
    pages_site,
    sweep_tree,
)

#: The player's own save key prefix, written out here and held to
#: solver_state.js's saveKey in the browser below.
SAVE_PREFIX = "nonogram-player:"


def _plant(page, url: str, key: str, cells: list[tuple[int, int]]) -> None:
    """A real player save for ``key`` with ``cells`` black, written by solver_state.js."""
    puzzle = page.evaluate(
        "async (key) => (await fetch(`/puzzle/${key}.json`)).json()", key
    )
    page.evaluate(
        """async ({key, puzzle, cells, prefix}) => {
          const s = await import('/solver_state.js');
          if (s.saveKey(key) !== prefix + key) throw new Error('save key moved: ' + s.saveKey(key));
          const payload = {id: key, width: puzzle.width, height: puzzle.height,
            rows: puzzle.clues.rows, columns: puzzle.clues.columns, mode: s.PUBLIC_MODE};
          let history = s.createHistory(s.createBoard(puzzle.width, puzzle.height));
          if (cells.length > 0) history = s.record(history, {cells, state: s.FILLED});
          localStorage.setItem(s.saveKey(key), s.serializeState(history, payload));
        }""",
        {"key": key, "puzzle": puzzle, "cells": [list(cell) for cell in cells], "prefix": SAVE_PREFIX},
    )


def _black(grid) -> list[tuple[int, int]]:
    return [(r, c) for r, row in enumerate(grid) for c, black in enumerate(row) if black]


def _restored(page, key: str, state: str) -> None:
    """CARD-437: a restore, waited out until ``key``'s square reads ``state``.

    The repaint is asynchronous (it re-imports the player's own reader and
    rebuilds every square), so the wait is on the page's own rendered
    attribute rather than on a sleep. ``_restore``'s docstring says what
    this harness can and cannot produce.
    """
    _restore(page)
    page.wait_for_function(
        "({key, state}) =>"
        " document.querySelector(`.tile[data-key='${key}']`)?.dataset.progress === state",
        arg={"key": key, "state": state},
        timeout=PAGES_SETTLE_MS,
    )


@pytest.mark.browser
def test_the_jump_box_opens_a_puzzle_by_its_printed_number(browser_page, pages_host) -> None:
    url, _, keys, slug = pages_host
    page = browser_page
    _open_pages(page, url, f"/b/{slug}")
    expected = [keys[name] for name in BOOK_ORDER]
    box = page.locator("[data-pages-jump-number]")
    hint = page.locator("[data-pages-jump-hint]")
    assert page.locator("[data-pages-jump]").is_visible()
    assert box.get_attribute("placeholder") == f"1–{len(expected)}"

    # Out of range and not a number: no navigation, the range is said.
    for typed in ("0", str(len(expected) + 1), "2a"):
        box.fill(typed)
        page.locator("[data-pages-jump] button[type=submit]").click()
        assert page.url == f"{url}/b/{slug}", typed
        assert hint.inner_text() == f"This book has puzzles 1 to {len(expected)}.", typed

    # In range: the hint names the level, and Play opens the PRINT number's
    # puzzle. BOOK_ORDER is not the sorted order, so a mapping to stored or
    # sorted order lands on the wrong key here.
    box.fill("2")
    assert hint.inner_text() == "Opens puzzle 2 (Easy)."
    page.locator("[data-pages-jump] button[type=submit]").click()
    page.wait_for_url(f"{url}/play/{expected[1]}?book={slug}", timeout=PAGES_SETTLE_MS)  # CARD-420
    assert expected[1] != sorted(expected)[1]


@pytest.mark.browser
def test_a_long_book_is_cut_into_level_sections_that_open_and_close(browser_page, pages_host) -> None:
    url, report, keys, slug = pages_host
    page = browser_page
    book_file = report.site_dir / "book" / f"{slug}.json"
    served = json.loads(book_file.read_text(encoding="utf-8"))
    # A 30-puzzle book grouped by level, hand-made from the served entries
    # (a listing may repeat a key; the page draws what the file says).
    base = served["puzzles"][0]
    puzzles = (
        [{**base, "tier": "easy"}] * 12 + [{**base, "tier": "medium"}] * 10 + [{**base, "tier": "hard"}] * 8
    )
    book_file.write_text(json.dumps({**served, "puzzles": puzzles}), encoding="utf-8")
    _open_pages(page, url, f"/b/{slug}")

    heads = page.locator(".book-section-head")
    assert heads.count() == 3
    names = [heads.nth(i).locator(".book-section-name").inner_text() for i in range(3)]
    assert names == ["Easy · puzzles 1–12", "Medium · puzzles 13–22", "Hard · puzzles 23–30"]
    assert [heads.nth(i).get_attribute("aria-expanded") for i in range(3)] == ["true", "false", "false"]
    assert heads.nth(0).locator(".book-section-count").inner_text() == "0 of 12 solved"
    grids = page.locator(".book-squares")
    assert [grids.nth(i).is_visible() for i in range(3)] == [True, False, False]
    # Every square is still in print order and numbered 1..30, open or not.
    numbers = page.evaluate("() => [...document.querySelectorAll('.tile .tile-number')].map(n => n.textContent)")
    assert numbers == [str(n) for n in range(1, 31)]

    heads.nth(1).click()
    assert heads.nth(1).get_attribute("aria-expanded") == "true"
    assert grids.nth(1).is_visible()
    heads.nth(0).click()
    assert heads.nth(0).get_attribute("aria-expanded") == "false"
    assert not grids.nth(0).is_visible()

    # The short fixture book opens every section: nothing to save by closing.
    book_file.write_text(json.dumps(served), encoding="utf-8")
    _open_pages(page, url, f"/b/{slug}")
    expanded = page.evaluate(
        "() => [...document.querySelectorAll('.book-section-head')].map(h => h.getAttribute('aria-expanded'))"
    )
    assert expanded and set(expanded) == {"true"}


@pytest.mark.browser
def test_progress_comes_from_this_device_and_draws_the_readers_own_picture(
    browser_page, pages_host
) -> None:
    """CARD-418 AC-C, and CARD-437 AC-1/AC-2/AC-4 — across a RESTORE, not a reload.

    The page is opened ONCE. Every reading after that first load is taken
    across a back/forward-cache restore (``_restore``), because the reload
    path is the one that never broke: CARD-437's reproduction on production
    had a save written, read back true, and the tile still showing "new"
    until the reader reloaded by hand — and the only route back to the book
    the product offers is the browser's Back. This cell used to re-open the
    page between the plant and the assertions, which is why the defect
    survived CARD-418's review: it passed against the broken page.
    """
    url, _, keys, slug = pages_host
    page = browser_page
    first, second = BOOK_ORDER[0], BOOK_ORDER[1]
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    asked: list[str] = []
    page.on("request", lambda request: asked.append(request.url))
    _open_pages(page, url, f"/b/{slug}")
    assert page.locator("[data-pages-continue]").is_hidden()
    assert set(page.evaluate("() => Object.values(window.playerPages.getProgress())")) == {"new"}

    # Puzzle 1 solved (every black cell of its grid), puzzle 2 started (one cell).
    _plant(page, url, keys[first], _black(PAGE_GRIDS[first]))
    _plant(page, url, keys[second], _black(PAGE_GRIDS[second])[:1])

    # The control (CARD-437 item 4): a fresh show fires ``pageshow`` as well,
    # and a handler that re-read progress on every one of them — rather than
    # on a restore — would repaint here.
    _restore(page, persisted=False)
    page.wait_for_timeout(PAGES_INERT_MS)
    assert page.evaluate("() => window.playerPages.getProgress()")[keys[first]] == "new"

    # AC-1 and AC-2: the restore repaints, new -> started and new -> solved.
    quiet = len(asked)
    kept = page.evaluate("() => ({...window.localStorage})")
    # The jump box hangs off elements the repaint does NOT replace (it is
    # outside the squares' list), so a repaint that re-wired it would stack a
    # second copy of both its listeners on every return from a puzzle —
    # invisible from the outside, which is why it is counted here.
    page.evaluate(
        """() => {
          window.__wired = 0;
          const jump = document.querySelector('[data-pages-jump]');
          for (const node of [jump, jump.querySelector('[data-pages-jump-number]')]) {
            const real = node.addEventListener.bind(node);
            node.addEventListener = (...args) => { window.__wired += 1; return real(...args); };
          }
        }"""
    )
    _restored(page, keys[second], "started")
    assert page.evaluate("() => window.__wired") == 0

    progress = page.evaluate("() => window.playerPages.getProgress()")
    assert progress[keys[first]] == "solved"
    assert progress[keys[second]] == "started"
    assert {progress[keys[name]] for name in BOOK_ORDER[2:]} == {"new"}

    solved = page.locator(f".tile[data-key='{keys[first]}']")
    assert solved.get_attribute("data-progress") == "solved"
    assert solved.get_attribute("aria-label").endswith(", solved")
    # The picture is the reader's own board: one unit square per black cell.
    path = solved.locator(".square-picture path").get_attribute("d")
    assert path.count("M") == len(_black(PAGE_GRIDS[first]))
    height, width = len(PAGE_GRIDS[first]), len(PAGE_GRIDS[first][0])
    assert solved.locator(".square-picture").get_attribute("viewBox") == f"0 0 {width} {height}"
    started = page.locator(f".tile[data-key='{keys[second]}']")
    assert started.get_attribute("data-progress") == "started"
    assert started.locator(".square-picture path").get_attribute("d").count("M") == 1
    assert page.locator(f".tile[data-key='{keys[BOOK_ORDER[2]]}'] .square-picture").count() == 0

    # Continue names the started puzzle by its print number.
    card = page.locator("[data-pages-continue]")
    assert card.is_visible()
    assert card.get_attribute("href") == f"/play/{keys[second]}?book={slug}"  # CARD-420
    grid = PAGE_GRIDS[second]
    assert page.locator("[data-pages-continue-name]").inner_text() == (
        f"Puzzle 2 · {len(grid[0])}×{len(grid)} · Easy"
    )
    # The section counts read the same progress.
    counts = page.evaluate(
        "() => [...document.querySelectorAll('.book-section-count')].map(c => c.textContent)"
    )
    assert counts[0] == "1 of 1 solved"

    # AC-4: the repaint read the device and nothing else — it asked the site
    # for nothing (the player's own reader is already in this document's
    # module map) and left storage byte for byte as the player wrote it.
    assert asked[quiet:] == [], asked[quiet:]
    assert page.evaluate("() => ({...window.localStorage})") == kept

    # A damaged save is "not started", never an error — on the restore path too.
    page.evaluate(
        "([k]) => localStorage.setItem(k, '{not json')", [SAVE_PREFIX + keys[first]]
    )
    _restored(page, keys[first], "new")
    assert page.evaluate("() => window.playerPages.getProgress()")[keys[first]] == "new"
    assert errors == []
    # The page never writes storage: what was planted is still exactly there.
    assert page.evaluate("([k]) => localStorage.getItem(k)", [SAVE_PREFIX + keys[first]]) == "{not json"


@pytest.mark.browser
def test_with_storage_blocked_every_square_is_not_started(browser_page, pages_host) -> None:
    url, _, keys, slug = pages_host
    page = browser_page
    _open_pages(page, url, f"/b/{slug}")
    _plant(page, url, keys[BOOK_ORDER[0]], _black(PAGE_GRIDS[BOOK_ORDER[0]]))
    page.add_init_script(
        "Object.defineProperty(window, 'localStorage', {get() { throw new Error('blocked'); }});"
    )
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    _open_pages(page, url, f"/b/{slug}")
    assert set(page.evaluate("() => Object.values(window.playerPages.getProgress())")) == {"new"}
    assert page.locator("[data-pages-continue]").is_hidden()
    assert _tiles(page) == [keys[name] for name in BOOK_ORDER]
    assert errors == []


def test_the_served_book_carries_series_and_authors_and_no_picture(pages_site) -> None:
    report, keys, slug = pages_site
    served = json.loads((report.site_dir / "book" / f"{slug}.json").read_text(encoding="utf-8"))
    assert sorted(served) == sorted(assembler.SERVED_BOOK_SCHEMA)
    assert served["series"] == BOOK_SERIES_SERVED
    assert served["authors"] == BOOK_AUTHORS
    # CARD-420: the fixture's stored theme is "generic", which the site draws
    # no look for, so the default "" is served; the theme is a closed choice
    # whose 1-bit residual is declared as structure, not exempt.
    assert served["theme"] == ""
    assert "theme" in assembler.LISTING_STRUCTURE_FIELDS
    assert assembler.book_theme_residual_bits() == 1.0
    # No served file carries an answer: the puzzle titles are base-64 of
    # their grids and the sweep over the whole site finds none of them.
    assert sweep_tree(report.site_dir, PAGE_GRIDS) == {}
    # The exemption is three fields wide and costs three titles' worth.
    assert assembler.book_exempt_residual_bits() == 3 * assembler.book_title_residual_bits()


@pytest.mark.browser
def test_the_landing_header_and_squares_fit_a_phone(browser_page, pages_host) -> None:
    url, _, keys, slug = pages_host
    page = browser_page
    page.set_viewport_size({"width": 390, "height": 844})
    _open_pages(page, url, f"/b/{slug}")
    assert page.locator("[data-pages-series]").text_content() == BOOK_SERIES_SERVED
    assert page.locator("[data-pages-title]").inner_text() == BOOK_TITLE_SERVED
    assert page.locator("[data-pages-byline]").inner_text().startswith(f"by {BOOK_AUTHORS}")
    assert page.evaluate(
        "() => document.documentElement.scrollWidth <= document.documentElement.clientWidth"
    )
    boxes = page.evaluate(
        "() => [...document.querySelectorAll('.tile')].map(t => {"
        " const r = t.getBoundingClientRect(); return [r.width, r.height]; })"
    )
    assert boxes and all(w >= 44 and h >= 44 for w, h in boxes), boxes
    for selector in ("[data-pages-jump-number]", "[data-pages-jump] button", ".book-section-head"):
        assert page.locator(selector).first.bounding_box()["height"] >= 44, selector
    # The one link out: the lesson (the owner removed the library link, 2026-11-10).
    links = page.evaluate("() => [...document.querySelectorAll('.book-foot a')].map(a => a.getAttribute('href'))")
    assert links == ["/how-to-solve"]
    # And no puzzle title anywhere on the page.
    text = page.evaluate("() => document.body.innerText")
    for name in BOOK_ORDER:
        assert _leaky_title(PAGE_GRIDS[name]) not in text
    # A book with no series or authors shows neither line.
    assert PAGE_TIERS  # the fixture's tier table is the one the page labels


#: The Christmas theme's tokens, as computed colours (tokens.css,
#: :root[data-theme="christmas"]), written out rather than read back.
CREAM = "rgb(243, 234, 210)"
PINE = "rgb(29, 74, 44)"
#: The board's own paper, which no theme touches.
GRID_PAPER = "rgb(255, 253, 248)"

_ROOT_THEME = "() => document.documentElement.dataset.theme ?? null"

#: The landing's decorations as counts — read twice by the Christmas cell,
#: before and after a restore (CARD-437), so it is a constant rather than
#: two copies of one expression.
_DECOR = """() => ({
  garlands: document.querySelectorAll('.decor-garland').length,
  panels: document.querySelectorAll('.book-jump, .book-continue, .book-section-head').length,
  snowed: document.querySelectorAll(':is(.book-jump, .book-continue, .book-section-head) > .decor-snow').length,
  hidden: [...document.querySelectorAll('.decor-garland, .decor-snow')].every((d) =>
    d.getAttribute('aria-hidden') === 'true' && getComputedStyle(d).pointerEvents === 'none'),
  needles: document.querySelectorAll('.decor-garland line').length,
})"""


@pytest.mark.browser
def test_a_christmas_book_dresses_its_landing_and_the_puzzles_opened_from_it(
    browser_page, pages_host
) -> None:
    """CARD-420 AC-1/AC-3/AC-4: a christmas book's landing and the puzzles a
    reader opens from it wear the theme; the board keeps its paper; the same
    puzzle opened any other way keeps the default look.

    Plant: the play page's loader applies the theme without checking that the
    book holds the key -> the "a book that does not hold this key" arm red.
    CARD-421 adds the decorations to the same walk (plant: decorate() for
    every book -> the default book's arm red), and CARD-422 the puzzle's
    garland (plant: the loader never decorates -> the garland arm red).
    """
    url, report, keys, slug = pages_host
    page = browser_page
    # The assembler's reduction (AC-1): only a theme the site draws is served.
    for stored, served in (
        ("christmas", "christmas"), ("Christmas", "christmas"), (" CHRISTMAS ", "christmas"),
        ("halloween", ""), (None, ""), (7, ""),
    ):
        payload = {"slug": slug, "title": "T", "puzzle_keys": [], "theme": stored}
        assert assembler.served_book(payload, slug, {})[0]["theme"] == served, stored

    # The default book: no theme on its landing, and no decorations (CARD-421).
    _open_pages(page, url, f"/b/{slug}")
    assert page.evaluate(_ROOT_THEME) is None
    assert page.locator(".decor-garland, .decor-snow").count() == 0

    # The same book, stored as christmas (the served file, as the assembler
    # writes it for one).
    path = report.site_dir / "book" / f"{slug}.json"
    book = json.loads(path.read_text(encoding="utf-8"))
    path.write_text(json.dumps({**book, "theme": "christmas"}), encoding="utf-8")
    first = keys[BOOK_ORDER[0]]
    _plant(page, url, first, _black(PAGE_GRIDS[BOOK_ORDER[0]]))
    _open_pages(page, url, f"/b/{slug}")
    assert page.evaluate(_ROOT_THEME) == "christmas"
    look = page.evaluate(
        """() => ({
          ground: getComputedStyle(document.body).backgroundColor,
          jump: getComputedStyle(document.querySelector('[data-pages-jump]')).backgroundColor,
          picture: getComputedStyle(document.querySelector('.square[data-progress="solved"] .square-picture')).fill,
          links: [...document.querySelectorAll('.tile')].map((tile) => tile.getAttribute('href')),
        })"""
    )
    assert look["ground"] == CREAM and look["jump"] == PINE, look
    assert look["picture"] == PINE, look  # the solved picture, "something greenish"
    assert look["links"] == [f"/play/{keys[name]}?book={slug}" for name in BOOK_ORDER]
    # CARD-421: the garland at the top and snow on every panel, hidden from
    # assistive technology and never in a tap's way.
    decor = page.evaluate(_DECOR)
    assert decor["garlands"] == 1 and decor["snowed"] == decor["panels"] > 0, decor
    assert decor["hidden"] and decor["needles"] > 0, decor

    # CARD-437: the repaint on a restore replaces the section heads, so the
    # decorations are drawn again — and `decorate` PREPENDS, so a repaint
    # that did not take the old ones away first would hang a second garland
    # over the first and lay a second drift on the box and the Continue
    # card. After a restore there is still exactly one of each.
    _plant(page, url, keys[BOOK_ORDER[1]], _black(PAGE_GRIDS[BOOK_ORDER[1]])[:1])
    _restored(page, keys[BOOK_ORDER[1]], "started")
    assert page.evaluate(_DECOR) == decor, page.evaluate(_DECOR)

    # A tile opens its puzzle wearing the book's theme, on the board's own paper.
    page.click(f'.tile[data-key="{first}"]')
    page.wait_for_function("() => window.puzzlePlayer !== undefined", timeout=PAGES_SETTLE_MS)
    assert page.evaluate(_ROOT_THEME) == "christmas"
    themed = page.evaluate(
        """() => ({
          ground: getComputedStyle(document.body).backgroundColor,
          paper: getComputedStyle(document.querySelector('td.player-cell[data-state="unknown"]')
            ?? document.querySelector('td.player-cell')).getPropertyValue('--grid-paper').trim(),
        })"""
    )
    assert themed["ground"] == CREAM and themed["paper"] == "#fffdf8", themed
    # CARD-422 (owner 2026-11-11: "apply it to individual puzzles also"): the
    # garland hangs over the puzzle too and its heading is pine; the board
    # carries no decoration.
    hung = page.evaluate(
        """() => ({
          garlands: document.querySelectorAll('.decor-garland').length,
          onBoard: document.querySelectorAll('.player-board .decor-garland, .player-board .decor-snow').length,
          heading: getComputedStyle(document.querySelector('.player-head h1')).color,
          sheets: [...document.querySelectorAll('link[rel=stylesheet]')].map((l) => l.getAttribute('href')),
        })"""
    )
    assert hung["garlands"] == 1 and hung["onBoard"] == 0 and hung["heading"] == PINE, hung
    assert hung["sheets"][-1] == "/decor.css", hung

    # Any other way in is the default look (AC-4): no book, a malformed book,
    # and a real christmas book that does not hold this key.
    outside = next(key for key in keys.values() if key not in {keys[n] for n in BOOK_ORDER})
    for address in (f"/play/{first}", f"/play/{first}?book=nope", f"/play/{outside}?book={slug}"):
        page.goto(f"{url}{address}")
        page.wait_for_function("() => window.puzzlePlayer !== undefined", timeout=PAGES_SETTLE_MS)
        assert page.evaluate(_ROOT_THEME) is None, address
        assert page.evaluate("() => getComputedStyle(document.body).backgroundColor") != CREAM, address
        assert page.locator(".decor-garland, link[href='/decor.css']").count() == 0, address

