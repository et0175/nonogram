"""CARD-419 — the site-wide ``/how-to-solve`` page (COMP-011, FR-045).

One lesson page for every book: a six-step wizard with a guided 5x5 ("Try
one") and a probe demo built the way the player's Probe / Keep /
Contradiction transaction works (CARD-268). The page's script declares its two
grids, the probe square and the probe chain as JSON-shaped constants; this
module reads those bytes (never a restatement) and checks them with tools that
share no code with the page:

* both grids have exactly one solution, by the brute-force oracle
  (``tests/helpers/brute_force_oracle.py``), with clues derived here;
* the probe demo is TRUE: line logic alone (a solver written here over the
  oracle's own ``line_candidates``) stalls with exactly ``PROBE_OPEN`` open
  squares, the probe square is one of them, every chain step is forced by
  the line it names, the last line cannot fit, and with the probe square
  white line logic finishes the grid. A one-cell change to the grid fails
  this, which is the control.

Then the page itself, in Chromium over the assembled site: the wizard's
three ways to move (Next, a progress segment, the URL fragment), the guided
board's three marks and its "Show me", the probe demo end to end, and where
"Back to your puzzles" goes.

Acceptance criteria (CARD-419, local labels; registry ids at dispatch):
  AC-A  test_the_lesson_grids_have_exactly_one_solution,
        test_the_probe_demo_is_what_line_logic_forces
  AC-B  test_the_wizard_moves_by_next_by_segment_and_by_fragment,
        test_back_to_your_puzzles_returns_to_the_book_it_came_from
  AC-C  test_try_one_marks_black_white_and_maybe_and_show_me_solves_it
  AC-D  test_the_probe_demo_runs_like_the_players_probe
  AC-E  test_the_lesson_is_published_routed_and_names_no_book
  AC-F  test_the_lesson_uses_tokens_and_the_players_probe_colours (and the
        screenshots in the card's worktree notes)
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from tests.helpers.brute_force_oracle import count_solutions, line_candidates
from tests.test_public_player_pages import (  # noqa: F401 — fixtures used by name
    BOOK_TITLE_SERVED,
    PAGES_SETTLE_MS,
    PLAYER_DIR,
    REPO_ROOT,
    browser_page,
    browser_type,
    pages_bundle,
    pages_host,
    pages_site,
    rewrites,
)

SCRIPT = PLAYER_DIR / "how-to-solve.js"
PAGE = PLAYER_DIR / "how-to-solve.html"


def _constant(name: str):
    """One ``export const <name> = <JSON>;`` line of how-to-solve.js."""
    source = SCRIPT.read_text(encoding="utf-8")
    match = re.search(rf"^export const {name} = (.+);$", source, re.M)
    assert match is not None, f"how-to-solve.js declares no {name}"
    return json.loads(match.group(1))


def _cells(grid: list[str]) -> list[list[bool]]:
    return [[ch == "#" for ch in row] for row in grid]


def _clue(line) -> tuple[int, ...]:
    runs, run = [], 0
    for black in line:
        if black:
            run += 1
        elif run:
            runs.append(run)
            run = 0
    if run:
        runs.append(run)
    return tuple(runs) or (0,)


def _clues(grid: list[str]):
    cells = _cells(grid)
    rows = tuple(_clue(row) for row in cells)
    columns = tuple(_clue(column) for column in zip(*cells))
    return rows, columns


# --------------------------------------------------------------------------
# A line solver of this module's own, over the oracle's line_candidates
# --------------------------------------------------------------------------


def _fits(clue, known):
    """The arrangements of ``clue`` that agree with ``known`` (None = open)."""
    return [
        option
        for option in line_candidates(clue, len(known))
        if all(k is None or k == v for k, v in zip(known, option))
    ]


def _line(board, axis: str, index: int):
    if axis == "row":
        return list(board[index])
    return [row[index] for row in board]


def _set(board, axis: str, index: int, k: int, value: bool) -> None:
    if axis == "row":
        board[index][k] = value
    else:
        board[k][index] = value


def _fixpoint(grid: list[str], board):
    """Line logic to a fixpoint; ``None`` if some line cannot fit."""
    rows, columns = _clues(grid)
    board = [list(row) for row in board]
    lines = [("row", i, clue) for i, clue in enumerate(rows)] + [
        ("column", i, clue) for i, clue in enumerate(columns)
    ]
    changed = True
    while changed:
        changed = False
        for axis, index, clue in lines:
            known = _line(board, axis, index)
            fits = _fits(clue, known)
            if not fits:
                return None
            for k, value in enumerate(known):
                if value is None and all(option[k] == fits[0][k] for option in fits):
                    _set(board, axis, index, k, fits[0][k])
                    changed = True
    return board


def _probe_demo_problems(grid, open_count, cell, chain) -> list[str]:
    """Every way the probe demo's claims are false for ``grid`` (empty = true)."""
    problems = []
    rows, columns = _clues(grid)
    if count_solutions(rows, columns, limit=2) != 1:
        problems.append("not exactly one solution")
    height, width = len(grid), len(grid[0])
    stalled = _fixpoint(grid, [[None] * width for _ in range(height)])
    if stalled is None:
        return problems + ["line logic finds a contradiction from a blank board"]
    still_open = sum(value is None for row in stalled for value in row)
    if still_open != open_count:
        problems.append(f"line logic leaves {still_open} open, the page says {open_count}")
    r, c = cell
    if stalled[r][c] is not None:
        return problems + ["the probe square is not open after line logic"]

    board = [list(row) for row in stalled]
    board[r][c] = True
    for number, step in enumerate(chain):
        clue = (rows if step["axis"] == "row" else columns)[step["index"]]
        fits = _fits(clue, _line(board, step["axis"], step["index"]))
        last = number == len(chain) - 1
        if last:
            if fits:
                problems.append(f"the last line still fits ({len(fits)} ways)")
            continue
        if not fits:
            problems.append(f"step {number + 1}'s line already cannot fit")
            break
        for sr, sc, black in step["cells"]:
            k = sc if step["axis"] == "row" else sr
            on_line = sr == step["index"] if step["axis"] == "row" else sc == step["index"]
            if not on_line:
                problems.append(f"step {number + 1} sets a square off its own line")
            elif board[sr][sc] is not None:
                problems.append(f"step {number + 1} sets a square already known")
            elif not all(option[k] == bool(black) for option in fits):
                problems.append(f"step {number + 1}'s square ({sr},{sc}) is not forced")
            board[sr][sc] = bool(black)

    board = [list(row) for row in stalled]
    board[r][c] = False
    finished = _fixpoint(grid, board)
    if finished is None or finished != _cells(grid):
        problems.append("with the probe square white, line logic does not finish the grid")
    return problems


# ==========================================================================
# AC-A — the two boards are true puzzles
# ==========================================================================


def test_the_lesson_grids_have_exactly_one_solution() -> None:
    for name in ("TRY_GRID", "PROBE_GRID"):
        grid = _constant(name)
        assert len({len(row) for row in grid}) == 1, name
        rows, columns = _clues(grid)
        assert count_solutions(rows, columns, limit=2) == 1, name
    # Control: a grid this check must refuse — a 2x2 diagonal has two.
    assert count_solutions(((1,), (1,)), ((1,), (1,)), limit=2) == 2


def test_the_probe_demo_is_what_line_logic_forces() -> None:
    grid = _constant("PROBE_GRID")
    open_count = _constant("PROBE_OPEN")
    cell = _constant("PROBE_CELL")
    chain = _constant("PROBE_CHAIN")
    assert _probe_demo_problems(grid, open_count, cell, chain) == []

    # Controls: each claim can fail. One cell of the grid flipped, the open
    # count off by one, and a chain step that is not forced.
    flipped = [list(row) for row in grid]
    flipped[0][0] = "." if flipped[0][0] == "#" else "#"
    assert _probe_demo_problems(["".join(row) for row in flipped], open_count, cell, chain)
    assert _probe_demo_problems(grid, open_count + 1, cell, chain)
    wrong = json.loads(json.dumps(chain))
    wrong[0]["cells"][0][2] = 1 - wrong[0]["cells"][0][2]
    assert _probe_demo_problems(grid, open_count, cell, wrong)


def test_the_guided_steps_cover_the_try_grid() -> None:
    """Doing every TRY_STEPS step settles every black square of TRY_GRID."""
    grid = _constant("TRY_GRID")
    steps = _constant("TRY_STEPS")
    touched = {
        (r, c)
        for step in steps
        for r in range(len(grid))
        for c in range(len(grid[0]))
        if r in step["rows"] or c in step["columns"]
    }
    blacks = {(r, c) for r, row in enumerate(grid) for c, ch in enumerate(row) if ch == "#"}
    assert blacks <= touched
    assert len(steps) == 5


# ==========================================================================
# AC-E / AC-F — published, routed, generic, styled from tokens
# ==========================================================================


def test_the_lesson_is_published_routed_and_names_no_book(pages_site) -> None:
    report, _, _ = pages_site
    site = report.site_dir
    assert (site / "how-to-solve" / "index.html").is_file()
    assert (site / "how-to-solve.js").read_bytes() == SCRIPT.read_bytes()
    hits = [d for pattern, d in rewrites(site) if pattern.match("/how-to-solve")]
    assert hits == ["/how-to-solve/index.html"], hits

    html = PAGE.read_text(encoding="utf-8")
    script = SCRIPT.read_text(encoding="utf-8")
    # Generic: no book's words, and no hook that would pull a book in.
    for text in (html, script):
        assert BOOK_TITLE_SERVED not in text
        assert "data-pages-" not in text
        assert not re.search(r"christmas|anna|olga", text, re.I)
    # Static: no request, no storage.
    assert "fetch(" not in script and "XMLHttpRequest" not in script
    assert "localStorage" not in script and "sessionStorage" not in script
    # Served from the site root like the other pages (rewrites serve one
    # document at many paths, so a relative src would break).
    assert '<script type="module" src="/how-to-solve.js"></script>' in html
    assert 'href="/player.css"' in html and 'href="/tokens.css"' in html


def test_the_lesson_uses_tokens_and_the_players_probe_colours() -> None:
    tokens = set(
        re.findall(
            r"(--[a-z0-9-]+)\s*:",
            (REPO_ROOT / "src/nonogram/admin/static/tokens.css").read_text(encoding="utf-8"),
        )
    )
    css = (PLAYER_DIR / "player.css").read_text(encoding="utf-8")
    for name, text in (("how-to-solve.html", PAGE.read_text(encoding="utf-8")), ("css", css)):
        assert not re.search(r"#[0-9a-fA-F]{3,8}\b", text), name
        assert "rgb(" not in text and "hsl(" not in text, name
    defined = tokens | set(re.findall(r"(--[a-z0-9-]+)\s*:", css))
    used = set(re.findall(r"var\(\s*(--[a-z0-9-]+)", css))
    assert used - defined == set()

    # The probe edge is the player's: the same two expressions admin.css
    # gives --player-probe and --player-probe-ink.
    admin = (REPO_ROOT / "src/nonogram/admin/static/admin.css").read_text(encoding="utf-8")
    for ours, theirs in (("--hts-probe", "--player-probe"), ("--hts-probe-ink", "--player-probe-ink")):
        mine = re.search(rf"{ours}:\s*([^;]+);", css)
        player = re.search(rf"{theirs}:\s*([^;]+);", admin)
        assert mine and player, (ours, theirs)
        assert mine.group(1).strip() == player.group(1).strip(), (ours, theirs)


# ==========================================================================
# The page, in Chromium
# ==========================================================================


def _open(page, url: str, path: str = "/how-to-solve", referer: str | None = None) -> None:
    page.goto(f"{url}{path}", timeout=PAGES_SETTLE_MS, referer=referer)
    page.wait_for_function("() => window.howToSolve !== undefined", timeout=PAGES_SETTLE_MS)


def _visible_step(page) -> int:
    return page.evaluate(
        "() => [...document.querySelectorAll('[data-hts-step]')]"
        ".filter(s => !s.hidden).map(s => Number(s.dataset.htsStep))"
    )


@pytest.mark.browser
def test_the_wizard_moves_by_next_by_segment_and_by_fragment(browser_page, pages_host) -> None:
    url = pages_host[0]
    page = browser_page
    _open(page, url)
    assert _visible_step(page) == [1]
    assert page.locator("[data-hts-back]").is_hidden()
    assert page.locator("[data-hts-caption]").inner_text() == "Step 1 of 6 · The rules"

    page.locator("[data-hts-next]").click()
    page.wait_for_function("() => window.howToSolve.getStep() === 2", timeout=PAGES_SETTLE_MS)
    assert _visible_step(page) == [2]
    assert page.evaluate("() => location.hash") == "#2"
    assert page.locator("[data-hts-next]").inner_text() == "Next: What every arrangement agrees on"

    page.locator("[data-hts-goto='4']").click()
    page.wait_for_function("() => window.howToSolve.getStep() === 4", timeout=PAGES_SETTLE_MS)
    assert _visible_step(page) == [4]

    page.go_back()
    page.wait_for_function("() => window.howToSolve.getStep() === 2", timeout=PAGES_SETTLE_MS)
    assert _visible_step(page) == [2]

    # CARD-440: step 5 is the phone's line view, so the levels are step 6.
    _open(page, url, "/how-to-solve#5")
    assert _visible_step(page) == [5]
    assert page.locator("[data-hts-step='5'] h2").inner_text() == "Big puzzles on a phone"
    assert page.locator("[data-hts-next]").inner_text() == "Next: Levels and the promise"
    _open(page, url, "/how-to-solve#6")
    assert _visible_step(page) == [6]
    assert page.locator("[data-hts-next]").is_hidden()
    assert page.locator("[data-hts-back]").is_visible()
    # A fragment out of range is step 1, not a blank page.
    _open(page, url, "/how-to-solve#9")
    assert _visible_step(page) == [1]


def _cell(page, board: str, r: int, c: int):
    return page.locator(f"[data-hts-{board}-board] .hts-cell[data-row='{r}'][data-column='{c}']")


@pytest.mark.browser
def test_try_one_marks_black_white_and_maybe_and_show_me_solves_it(browser_page, pages_host) -> None:
    url = pages_host[0]
    page = browser_page
    _open(page, url)
    cell = lambda: _cell(page, "try", 0, 0)  # noqa: E731
    assert cell().get_attribute("data-state") == "unknown"
    cell().click()
    assert cell().get_attribute("data-state") == "filled"
    cell().click()
    assert cell().get_attribute("data-state") == "unknown"
    page.locator("[data-hts-brush='maybe']").click()
    cell().click()
    assert cell().get_attribute("data-state") == "maybe"
    assert "maybe" in cell().get_attribute("aria-label")
    page.locator("[data-hts-brush='empty']").click()
    cell().click()
    assert cell().get_attribute("data-state") == "empty"
    page.locator("[data-hts-try-reset]").click()
    assert cell().get_attribute("data-state") == "unknown"

    board = page.locator("[data-hts-try-board]")
    assert board.get_attribute("data-step") == "1"
    # Row 3 is step 1's line, lit; doing it by hand moves the guide on.
    for c in range(5):
        _cell(page, "try", 2, c).click()
    assert board.get_attribute("data-step") == "2"
    for _ in range(5):
        if board.get_attribute("data-solved") == "true":
            break
        page.locator("[data-hts-try-show]").click()
    assert board.get_attribute("data-solved") == "true"
    assert page.locator("[data-hts-try-tag]").inner_text() == "Solved"
    grid = _constant("TRY_GRID")
    cells = page.evaluate("() => window.howToSolve.getTryCells()")
    assert [["#" if s == "filled" else "." for s in row] for row in cells] == [list(r) for r in grid]


@pytest.mark.browser
def test_the_probe_demo_runs_like_the_players_probe(browser_page, pages_host) -> None:
    url = pages_host[0]
    page = browser_page
    _open(page, url, "/how-to-solve#4")
    phase = lambda: page.locator("[data-hts-probe-board]").get_attribute("data-phase")  # noqa: E731
    r, c = _constant("PROBE_CELL")
    target = lambda: _cell(page, "probe", r, c)  # noqa: E731
    open_count = _constant("PROBE_OPEN")
    unknown = page.locator("[data-hts-probe-board] .hts-cell[data-state='unknown']")
    assert unknown.count() == open_count
    assert target().get_attribute("data-target") == "true"

    # Before Probe, the target does nothing.
    target().click()
    assert phase() == "stuck"
    page.locator("[data-hts-probe-open]").click()
    assert phase() == "open"
    assert page.locator("[data-hts-probe-open]").get_attribute("aria-pressed") == "true"
    target().click()
    assert phase() == "following"
    assert target().get_attribute("data-state") == "filled"
    assert target().get_attribute("data-probe") == "true"

    chain = _constant("PROBE_CHAIN")
    for _ in chain:
        page.locator("[data-hts-probe-follow]").click()
    assert phase() == "broken"
    bad = chain[-1]
    selector = (
        f".hts-clue-column[data-column='{bad['index']}']"
        if bad["axis"] == "column"
        else f".hts-clue-row[data-row='{bad['index']}']"
    )
    assert "is-bad" in page.locator(f"[data-hts-probe-board] {selector}").get_attribute("class")
    probed = page.locator("[data-hts-probe-board] .hts-cell[data-probe]")
    assert probed.count() == 1 + sum(len(step["cells"]) for step in chain)

    page.locator("[data-hts-probe-keep]").click()
    assert phase() == "kept"
    page.locator("[data-hts-probe-contradiction]").click()
    assert phase() == "proved"
    assert probed.count() == 0
    assert target().get_attribute("data-state") == "empty"

    page.locator("[data-hts-probe-finish]").click()
    assert phase() == "solved"
    grid = _constant("PROBE_GRID")
    for rr, row in enumerate(grid):
        for cc, ch in enumerate(row):
            expected = "filled" if ch == "#" else "empty"
            assert _cell(page, "probe", rr, cc).get_attribute("data-state") == expected, (rr, cc)


@pytest.mark.browser
def test_back_to_your_puzzles_returns_to_the_book_it_came_from(browser_page, pages_host) -> None:
    url, _, _, slug = pages_host
    page = browser_page
    homes = page.locator("[data-hts-home]")

    _open(page, url, referer=f"{url}/b/{slug}")
    assert homes.count() == 2
    assert {homes.nth(i).get_attribute("href") for i in range(2)} == {f"/b/{slug}"}

    _open(page, url)
    assert {homes.nth(i).get_attribute("href") for i in range(2)} == {"/library"}

    # Another site's /b/ path is not this site's book.
    _open(page, url, referer=f"https://elsewhere.example/b/{slug}")
    assert {homes.nth(i).get_attribute("href") for i in range(2)} == {"/library"}
