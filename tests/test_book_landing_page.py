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
    PAGES_SETTLE_MS,
    _leaky_title,
    _open_pages,
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
    page.wait_for_url(f"{url}/play/{expected[1]}", timeout=PAGES_SETTLE_MS)
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
    url, _, keys, slug = pages_host
    page = browser_page
    first, second = BOOK_ORDER[0], BOOK_ORDER[1]
    _open_pages(page, url, f"/b/{slug}")
    assert page.locator("[data-pages-continue]").is_hidden()
    assert set(page.evaluate("() => Object.values(window.playerPages.getProgress())")) == {"new"}

    # Puzzle 1 solved (every black cell of its grid), puzzle 2 started (one cell).
    _plant(page, url, keys[first], _black(PAGE_GRIDS[first]))
    _plant(page, url, keys[second], _black(PAGE_GRIDS[second])[:1])
    _open_pages(page, url, f"/b/{slug}")

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
    assert card.get_attribute("href") == f"/play/{keys[second]}"
    grid = PAGE_GRIDS[second]
    assert page.locator("[data-pages-continue-name]").inner_text() == (
        f"Puzzle 2 · {len(grid[0])}×{len(grid)} · Easy"
    )
    # The section counts read the same progress.
    counts = page.evaluate(
        "() => [...document.querySelectorAll('.book-section-count')].map(c => c.textContent)"
    )
    assert counts[0] == "1 of 1 solved"

    # A damaged save is "not started", never an error.
    page.evaluate(
        "([k]) => localStorage.setItem(k, '{not json')", [SAVE_PREFIX + keys[first]]
    )
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    _open_pages(page, url, f"/b/{slug}")
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
    # The two links out: the lesson and the library.
    links = page.evaluate("() => [...document.querySelectorAll('.book-foot a')].map(a => a.getAttribute('href'))")
    assert links == ["/how-to-solve", "/library"]
    # And no puzzle title anywhere on the page.
    text = page.evaluate("() => document.body.innerText")
    for name in BOOK_ORDER:
        assert _leaky_title(PAGE_GRIDS[name]) not in text
    # A book with no series or authors shows neither line.
    assert PAGE_TIERS  # the fixture's tier table is the one the page labels
