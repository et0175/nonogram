"""CARD-284 — the QR landing and the library: ``/b/<slug>`` and ``/library``
around CARD-283's player (COMP-011, FR-045, ADR-0041).

The two doors into the same app. A printed QR code resolves to
``/b/<slug>``, an online visit to ``/library``, and both end at
``/play/<key>``, which is CARD-283's page and is not re-tested here.

The machinery is CARD-283's and is **imported rather than rewritten**: the
assembler loaded by path, the grid corpus, the leaky-title bundle writer, the
decoding sweep, the loopback host driven by the shipped ``vercel.json``, and
the Chromium fixtures that refuse loudly when the browser is absent
(ADR-0038/R8). A second copy of any of them would be a second thing to keep
true.

What this module measures, and what it does not
-----------------------------------------------
Two decisions CARD-283 deliberately left open were routed to this card, and
both are settled here with a control that can fail:

#. **the title.** ``index.json`` and ``book/<slug>.json`` each carry the
   bundle's free-text ``title``, and CARD-283 served neither file rather than
   decide for them. The decision taken is the same one it took for the puzzle
   files, for the same measured reason — CARD-282 recovered all 144 cells of a
   12x12 answer out of a published title, and there is no decision procedure
   for "does this string carry a grid?" — so **no title reaches either
   listing**. The listings are rebuilt from closed schemas like the puzzle
   files, and the sweep that proves the bundle dirty and the site clean is run
   over them here as well;
#. **CARD-282's F-8** — an export that fails part-way through leaves
   ``index.json`` naming puzzle files that were never written. It is closed by
   construction rather than by a check: every served listing entry *is* the
   served payload of that key's own puzzle file, so a listing naming an absent
   file is not possible. The bundle's own index is read as a second,
   independent instrument and every disagreement is named in the report —
   including the case where that index cannot be read at all, which makes
   every served key ``unlisted`` rather than making the instrument silent.

What it does **not** measure is named rather than left to look covered: no
render was eyeballed on a phone, and the capacity argument for the listings
establishes "no listing field carries anything a puzzle file does not", not
EC-048's one-cell threshold — the order a book's puzzles are listed in is a
declared residual, for the reason ``assemble.py``'s
``LISTING_STRUCTURE_FIELDS`` gives.

AC-390, AC-391 and AC-392 name node ids in this module and belong to
**CARD-285** (hosting and counting). They are not written here, and
``test_the_registrys_refs_for_this_file_resolve_or_are_card_285s`` holds that
split in both directions so the three cannot be forgotten or quietly claimed.

==============================
Tests, by node id (FR-045)
==============================
Written out in full — path and name on one line each — because the
architecture validator resolves a check ref by ``git grep -lw`` of the WHOLE
``path::name`` string over tracked, non-Markdown files, and this card wraps
each ref across two lines in its own body (CARD-283's F-1):

* AC-387 — ``tests/test_public_player_pages.py::test_book_landing_lists_and_links``
* AC-388 — ``tests/test_public_player_pages.py::test_unknown_slug_lands_softly``
* AC-389 — ``tests/test_public_player_pages.py::test_library_filters_the_index``
"""

from __future__ import annotations

import ast
import json
import re
import socketserver
import threading
from pathlib import Path

import pytest

from nonogram.admin import player_bundle
from nonogram.difficulty import Tier
from nonogram.limits import MAX_SIZE, MIN_SIZE
from tests.test_public_player import (  # noqa: F401 — fixtures used by name
    GRIDS,
    PLAYER_DIR,
    REPO_ROOT,
    _Host,
    _bundle_payload,
    _leaky_title,
    _public_key,
    assembler,
    browser_page,
    browser_type,
    rewrites,
    sweep_tree,
)
from tests.test_puzzle_solver_page import _unique_grid

# ==========================================================================
# A corpus that reads every filter option, and both ends of every size band
# ==========================================================================

#: One puzzle per (tier, size band) cell this card's filters can select, plus
#: **both edges of every band**: 16 and 17 straddle small/medium, 23 and 24
#: straddle medium/large. A corpus of three round sizes would leave every
#: band bound untested, which is the one-end-only hole CARD-283's review hit
#: three times in other functions.
#:
#: ``n30`` carries no tier at all, so "a tile with no chip" and "a tier filter
#: that must not keep it" are both real cases rather than hypotheses.
PAGE_GRIDS: dict[str, list[list[bool]]] = {
    "e10": _unique_grid(MIN_SIZE, MIN_SIZE, seed=2841),
    "h16": _unique_grid(16, 16, seed=2842),
    "m17": _unique_grid(17, 17, seed=2843),
    "e23": _unique_grid(23, 23, seed=2844),
    "h24": _unique_grid(24, 24, seed=2845),
    "n30": _unique_grid(MAX_SIZE, MAX_SIZE, seed=2846),
}

PAGE_TIERS = {
    "e10": "easy",
    "h16": "hard",
    "m17": "medium",
    "e23": "easy",
    "h24": "hard",
    "n30": "",
}

#: Which band each fixture must land in, written here so the test asserts an
#: expectation rather than re-deriving the rule it is checking.
PAGE_BANDS = {
    "e10": "small",
    "h16": "small",
    "m17": "medium",
    "e23": "medium",
    "h24": "large",
    "n30": "large",
}

#: The book's order. Deliberately NOT the sorted key order and a strict
#: SUBSET of the library, so "book order" is distinguishable from "every
#: served puzzle, sorted" — a listing that quietly sorted or that listed the
#: whole library would otherwise pass AC-387.
BOOK_ORDER = ("h24", "e10", "n30", "m17")


def write_pages_bundle(
    root: Path, names=None, *, order=None, leaky: bool = True
) -> tuple[dict[str, str], str]:
    """A bundle at ``root`` holding one book. Returns ``({name: key}, slug)``.

    Every title is the base-64 of its own grid by default — CARD-282's
    measured leak — because a fixture titled "Snowy owl" would make every
    assertion below pass for the wrong reason. The book's title is a leaky
    one too: this card serves a book file, so the book's own title is a
    channel of exactly the same shape as a puzzle's.

    The slug is computed by the exporter's own :func:`player_bundle.book_slug`
    rather than invented, so these fixtures live in the namespace the product
    has (the same reason CARD-283's ``_public_key`` is cross-checked).
    """
    names = list(PAGE_GRIDS) if names is None else list(names)
    order = list(names) if order is None else list(order)
    keys: dict[str, str] = {}
    entries = []
    for name in names:
        grid = PAGE_GRIDS[name]
        payload = _bundle_payload(
            grid,
            tier=PAGE_TIERS[name],
            title=_leaky_title(grid) if leaky else f"Picture {name}",
        )
        keys[name] = payload["key"]
        path = root / "puzzle" / f"{payload['key']}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        entries.append({field: value for field, value in payload.items() if field != "clues"})

    (root / "index.json").write_text(
        json.dumps({"puzzles": entries}, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    ordered = [keys[name] for name in order]
    slug = player_bundle.book_slug(ordered)
    book = {
        "slug": slug,
        "title": _leaky_title(PAGE_GRIDS[order[0]]) if leaky else "A book of pictures",
        "puzzle_keys": ordered,
    }
    assert set(book) == set(player_bundle.BOOK_FILE_FIELDS), sorted(book)
    path = root / "book" / f"{slug}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(book, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return keys, slug


@pytest.fixture
def pages_bundle(tmp_path):
    root = tmp_path / "bundle"
    keys, slug = write_pages_bundle(root, order=BOOK_ORDER)
    return root, keys, slug


@pytest.fixture
def pages_site(pages_bundle, tmp_path):
    """The assembled, deployable site — what a static host would serve."""
    root, keys, slug = pages_bundle
    report = assembler.assemble(root, tmp_path / "site")
    assert report.puzzle_count == len(keys), report
    assert report.book_count == 1, report
    return report, keys, slug


@pytest.fixture
def pages_host(pages_site):
    """The site on 127.0.0.1, with the shipped ``vercel.json``'s rewrites.

    CARD-283's ``_Host`` and ``rewrites`` verbatim: the rules this server
    routes by are read from the deploy config, so the two new doors are
    exercised through the same file the host reads rather than through a
    route hand-written into a fixture (ADR-0039/R2).
    """
    report, keys, slug = pages_site

    class Server(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True

    handler = type("Handler", (_Host,), {})
    directory = str(report.site_dir)
    server = Server(("127.0.0.1", 0), lambda *a: handler(*a, directory=directory))
    server.rewrites = rewrites(report.site_dir)
    thread = threading.Thread(
        target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True
    )
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}", report, keys, slug
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def _tiles(page) -> list[str]:
    """The keys of the tiles currently rendered, in rendered order."""
    return page.evaluate("() => [...document.querySelectorAll('.tile')].map(t => t.dataset.key)")


def _open_pages(page, url: str, path: str) -> None:
    page.goto(f"{url}{path}")
    page.wait_for_function(
        "() => window.playerPages !== undefined"
        " || !document.querySelector('[data-pages-notfound]').hidden"
    )


# ==========================================================================
# The three acceptance criteria (browser)
# ==========================================================================


@pytest.mark.browser
def test_book_landing_lists_and_links(browser_page, pages_host) -> None:
    """AC-387 — the QR landing lists the book's puzzles, in book order.

    Three things, and the order is the one with teeth: ``BOOK_ORDER`` is
    neither the sorted key order nor the whole library, so a page that sorted
    its tiles, or listed everything served, fails here. The link is then
    followed for real rather than read off the ``href``: tapping the second
    tile has to land on CARD-283's board for that key.
    """
    url, report, keys, slug = pages_host
    expected = [keys[name] for name in BOOK_ORDER]
    assert expected != sorted(expected), "the fixture's order is the sorted one"
    assert len(expected) < len(keys), "the fixture's book is not a strict subset"

    _open_pages(browser_page, url, f"/b/{slug}")
    assert _tiles(browser_page) == expected
    assert browser_page.evaluate("() => window.playerPages.slug") == slug

    # The book's numbering is its printed numbering: position, not a field.
    numbers = browser_page.evaluate(
        "() => [...document.querySelectorAll('.tile .tile-number')].map(n => n.textContent)"
    )
    assert numbers == [str(n) for n in range(1, len(expected) + 1)]

    # Tap the second tile and arrive at that puzzle's board.
    browser_page.locator(".tile").nth(1).click()
    browser_page.wait_for_function("() => window.publicPlayer !== undefined")
    assert browser_page.url.endswith(f"/play/{expected[1]}")
    assert browser_page.evaluate("() => window.publicPlayer.payload.key") == expected[1]


@pytest.mark.browser
def test_unknown_slug_lands_softly(browser_page, pages_host) -> None:
    """AC-388 — a stale or misprinted code gets a page, not a bare 404.

    Both halves the AC names: the not-found panel renders with a working way
    to the library, and **no script error is thrown**. The second is collected
    from the page rather than inferred — a page that threw while drawing the
    panel would still show the panel, because the panel is in the HTML.

    Two unknown shapes, because they fail on different paths: a well-formed
    slug the bundle does not have (the fetch 404s) and a slug-shaped-wrong
    path (no fetch is made at all). The published slug is the positive
    control in the same test, so "the panel is always up" cannot pass.
    """
    url, report, keys, slug = pages_host
    # Two lists, not one, because they answer different questions and
    # collapsing them is what made the first version of this test fail for
    # the wrong reason. ``thrown`` is the AC's "script error" — an uncaught
    # exception — and must be empty. ``logged`` is the console, where the
    # browser itself reports the 404 that IS the mechanism here; every entry
    # in it has to be one of those resource notices, so the exemption is
    # bounded rather than a blanket silence, and there has to be at least one
    # or the fetch never happened.
    thrown: list[str] = []
    logged: list[str] = []
    browser_page.on("pageerror", lambda error: thrown.append(str(error)))
    browser_page.on(
        "console",
        lambda message: logged.append(message.text) if message.type == "error" else None,
    )
    requested: list[str] = []
    browser_page.on("request", lambda request: requested.append(request.url))

    for path in (f"/b/{'0' * 10}", "/b/not-a-slug"):
        _open_pages(browser_page, url, path)
        panel = browser_page.locator("[data-pages-notfound]")
        assert panel.is_visible(), path
        link = panel.locator("a.pages-library-link")
        assert link.get_attribute("href") == "/library", path
        assert _tiles(browser_page) == [], path

    # The malformed path must not have been turned into a fetch: no /book/
    # request at all for it (CARD-283's own fix for the same defect shape —
    # reading the message on the page could not tell a 404 from a refusal).
    # Only LISTING requests are read, because the navigation to the malformed
    # path is itself a request carrying that path.
    listings = [request for request in requested if "/book/" in request]
    assert listings == [f"{url}/book/{'0' * 10}.json"], listings

    # The positive control: the real slug shows tiles and no panel.
    _open_pages(browser_page, url, f"/b/{slug}")
    assert not browser_page.locator("[data-pages-notfound]").is_visible()
    assert len(_tiles(browser_page)) == len(BOOK_ORDER)

    # And the library link goes somewhere: followed, not just asserted.
    _open_pages(browser_page, url, "/b/not-a-slug")
    browser_page.locator("a.pages-library-link").click()
    browser_page.wait_for_function("() => window.playerPages !== undefined")
    assert len(_tiles(browser_page)) == len(PAGE_GRIDS)

    assert thrown == [], thrown
    assert logged, "the browser logged no 404, so the unknown slug never fetched"
    assert [entry for entry in logged if "Failed to load resource" not in entry] == [], logged


@pytest.mark.browser
def test_library_filters_the_index(browser_page, pages_host) -> None:
    """AC-389 — filtering by tier or size keeps exactly the matching entries.

    "Exactly" is what the corpus is built for: every tier option and every
    size band has at least one member, both ends of every band are present
    (16/17 and 23/24), and one puzzle has no tier at all. So an off-by-one
    band bound, a filter that compares the wrong axis, or one that keeps an
    untiered puzzle under a named tier each fail on a case of their own rather
    than on none.

    The expectation is computed from ``PAGE_BANDS`` and ``PAGE_TIERS`` — the
    fixture's declarations — never from the page's own rule.
    """
    url, report, keys, slug = pages_host
    _open_pages(browser_page, url, "/library")
    everything = sorted(keys.values())
    assert sorted(_tiles(browser_page)) == everything

    tier_select = browser_page.locator("select[data-pages-filter='tier']")
    size_select = browser_page.locator("select[data-pages-filter='size']")

    def expect(*, tier="", size=""):
        return sorted(
            keys[name]
            for name in PAGE_GRIDS
            if (tier == "" or PAGE_TIERS[name] == tier)
            and (size == "" or PAGE_BANDS[name] == size)
        )

    for tier in ("easy", "medium", "hard"):
        tier_select.select_option(tier)
        wanted = expect(tier=tier)
        assert wanted, tier  # the corpus really has one, so the case is live
        assert sorted(_tiles(browser_page)) == wanted, tier
        assert keys["n30"] not in _tiles(browser_page), "an untiered puzzle was kept"
    tier_select.select_option("")
    assert sorted(_tiles(browser_page)) == everything

    for band in ("small", "medium", "large"):
        size_select.select_option(band)
        wanted = expect(size=band)
        assert len(wanted) == 2, band  # both ends of the band, by construction
        assert sorted(_tiles(browser_page)) == wanted, band
    size_select.select_option("")
    assert sorted(_tiles(browser_page)) == everything

    # The two filters compose, and an empty intersection shows the empty note
    # rather than silently everything.
    tier_select.select_option("easy")
    size_select.select_option("large")
    assert expect(tier="easy", size="large") == []
    assert _tiles(browser_page) == []
    assert browser_page.locator("[data-pages-empty]").is_visible()

    # Clearing restores all — through the button, which is the one path a
    # reader with two filters set actually takes.
    browser_page.locator("[data-pages-clear]").click()
    assert sorted(_tiles(browser_page)) == everything
    assert browser_page.evaluate("() => window.playerPages.getFilters()") == {
        "tier": "",
        "size": "",
    }
    assert not browser_page.locator("[data-pages-empty]").is_visible()


@pytest.mark.browser
def test_the_listing_pages_issue_one_get_and_write_nothing(browser_page, pages_host) -> None:
    """EC-050's half of these two pages: nothing leaves them (ADR-0041/R4).

    Every request either page makes is a same-origin GET, and filtering —
    the only interaction they have — issues none at all. Asserted as the
    METHOD and the ORIGIN of every request, never as a request count, which
    is the distinction CARD-283's own EC-050 test rests on.
    """
    url, report, keys, slug = pages_host
    seen: list[tuple[str, str]] = []
    browser_page.on("request", lambda request: seen.append((request.method, request.url)))

    for path in (f"/b/{slug}", "/library"):
        _open_pages(browser_page, url, path)
        assert len(_tiles(browser_page)) > 0, path
    assert seen, "no request was recorded at all, so this measures nothing"
    loaded = len(seen)

    # Every interaction either page has, after the last navigation finished.
    browser_page.locator("select[data-pages-filter='tier']").select_option("easy")
    browser_page.locator("select[data-pages-filter='size']").select_option("small")
    browser_page.locator("[data-pages-clear]").click()
    assert sorted(_tiles(browser_page)) == sorted(keys.values())
    assert seen[loaded:] == [], seen[loaded:]

    for method, requested in seen:
        assert method == "GET", (method, requested)
        assert requested.startswith(url), requested
    # The listing fetch really happened, so "no further request" is a
    # statement about a page that loaded rather than about one that did not.
    assert (f"{url}/index.json", f"{url}/book/{slug}.json") == (
        next(req for _, req in seen if req.endswith("/index.json")),
        next(req for _, req in seen if "/book/" in req),
    )


@pytest.mark.browser
def test_a_listing_the_page_cannot_trust_is_refused(browser_page, pages_site) -> None:
    """``readListing``/``isEntry`` are checks, so they need a listing to refuse.

    The page validates its own input even though ``assemble.py`` wrote it —
    deliberately twice, once on each side of the wire, for the reason play.js
    gives: a page that trusts its input is a page whose input decides what it
    does. That second check is only a mechanism if something exercises it, so
    a malformed listing is written into the served tree here and the page has
    to refuse it rather than draw a tile from it.

    Four shapes, one per branch of ``isEntry`` plus the wrapper, each one
    edit from valid; the unedited listing is the positive control in the
    same test.
    """
    report, keys, slug = pages_site
    index = report.site_dir / "index.json"
    good = json.loads(index.read_text(encoding="utf-8"))
    first = good["puzzles"][0]
    cases = {
        "not-a-listing": {"puzzles": {"a": 1}},
        "bad-key": {"puzzles": [{**first, "key": "NOTAKEY"}]},
        "bad-extent": {"puzzles": [{**first, "width": MAX_SIZE + 1}]},
        "bad-tier": {"puzzles": [{**first, "tier": "tqlhkuhxpmgj"}]},
    }

    class Server(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True

    handler = type("Handler", (_Host,), {})
    directory = str(report.site_dir)
    server = Server(("127.0.0.1", 0), lambda *a: handler(*a, directory=directory))
    server.rewrites = rewrites(report.site_dir)
    thread = threading.Thread(
        target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True
    )
    thread.start()
    url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        for name, payload in cases.items():
            index.write_text(json.dumps(payload), encoding="utf-8")
            _open_pages(browser_page, url, "/library")
            assert _tiles(browser_page) == [], name
            assert browser_page.locator("[data-pages-notfound]").is_visible(), name
            assert browser_page.evaluate("() => window.playerPages") is None, name
        index.write_text(json.dumps(good), encoding="utf-8")
        _open_pages(browser_page, url, "/library")
        assert sorted(_tiles(browser_page)) == sorted(keys.values())
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.mark.browser
def test_a_tile_is_a_thumb_target_and_wears_its_tier(browser_page, pages_host) -> None:
    """The one layout claim these pages make, measured at phone width.

    Nearly every visit to ``/b/<slug>`` arrives by scanning a code off paper,
    so a tile is the one thing a thumb has to hit. 44 px is the floor the
    page's own buttons use (CARD-283's ``.btn``).

    Both halves, because the first version of this test had only the second
    and the floor was DEAD: deleting ``.tile``'s ``min-height`` left every
    rendered tile over 44 px anyway, on this corpus, at this font size — the
    content happened to be tall enough. So the DECLARED floor is read off the
    computed style and held to 44 px, and the rendered box is held to the
    declared floor. A tile that is tall by accident now passes the second
    assertion and fails the first.

    The tier chip is measured in both directions in the same place, because
    "a chip is drawn" and "a chip is drawn only when there is a tier" are
    different claims and the untiered fixture is what separates them.
    """
    url, report, keys, slug = pages_host
    browser_page.set_viewport_size({"width": 390, "height": 780})
    _open_pages(browser_page, url, "/library")

    boxes = browser_page.evaluate(
        "() => [...document.querySelectorAll('.tile')].map(t => {"
        " const r = t.getBoundingClientRect();"
        " const s = getComputedStyle(t);"
        " return {key: t.dataset.key, w: r.width, h: r.height,"
        "  floor: parseFloat(s.minHeight) || 0,"
        "  tier: t.querySelector('.tile-tier')?.textContent ?? null}; })"
    )
    assert len(boxes) == len(PAGE_GRIDS)
    for box in boxes:
        assert box["floor"] >= 44, box  # the DECLARED floor, not the accident
        assert box["h"] >= box["floor"], box
        assert box["w"] >= 44, box
    # No horizontal page scroll at 390 px: the grid reflows, it does not
    # overflow (the stage's sideways scroll is the BOARD's trade-off, and a
    # page of tiles has no reason to take it).
    assert browser_page.evaluate(
        "() => document.documentElement.scrollWidth <= document.documentElement.clientWidth"
    )

    chips = {box["key"]: box["tier"] for box in boxes}
    assert chips[keys["n30"]] is None, "an untiered puzzle was given a chip"
    for name, tier in PAGE_TIERS.items():
        if tier != "":
            assert chips[keys[name]] == tier, name


# ==========================================================================
# EC-048's listing half: what the two listings may carry
# ==========================================================================


def test_no_title_reaches_either_listing(pages_site, pages_bundle) -> None:
    """The channel CARD-283 removed from the puzzle files, removed here too.

    One sweep, both directions, exactly as that card's own EC-048 test does
    it: the **bundle's** two listings must be dirty (every title in this
    fixture is base-64 of a grid, the book's included) and the **site's** must
    be clean. A sweep that had quietly stopped working cannot report this as a
    pass.
    """
    report, keys, slug = pages_site
    bundle_root, _, _ = pages_bundle

    # The control, named per file: the leak is in the bundle's listings, not
    # only somewhere in the bundle.
    dirty = sweep_tree(bundle_root, PAGE_GRIDS)
    for listing in ("index.json", f"book/{slug}.json"):
        hits = [where for where in dirty if where.startswith(listing)]
        assert hits, f"the control is dead: nothing recoverable in the bundle's {listing}"

    assert sweep_tree(report.site_dir, PAGE_GRIDS) == {}

    # And the title really is a declared field of both bundle files, so this
    # is not a defence against a field nobody writes.
    assert "title" in player_bundle.INDEX_ENTRY_FIELDS
    assert "title" in player_bundle.BOOK_FILE_FIELDS
    assert "title" not in assembler.SERVED_ENTRY_SCHEMA
    assert "title" not in assembler.SERVED_BOOK_SCHEMA


def test_a_listing_carries_only_values_already_on_a_puzzle_file(pages_site) -> None:
    """Why the listings add zero capacity: every value is already served.

    :data:`assembler.MIRRORED_FROM_PUZZLE_FILE` claims each entry field is a
    value the site already serves on that key's own ``puzzle/<key>.json``. It
    is claimed by construction (``listing_entry`` reads the served payload),
    and held here field by field over both listings — with a control that can
    fail, because an equality nobody can break is not one.
    """
    report, keys, slug = pages_site
    served = {
        key: json.loads((report.site_dir / "puzzle" / f"{key}.json").read_text(encoding="utf-8"))
        for key in keys.values()
    }
    listings = {
        "index.json": json.loads((report.site_dir / "index.json").read_text(encoding="utf-8")),
        f"book/{slug}.json": json.loads(
            (report.site_dir / "book" / f"{slug}.json").read_text(encoding="utf-8")
        ),
    }
    checked = 0
    for where, payload in listings.items():
        for entry in payload["puzzles"]:
            assert sorted(entry) == sorted(assembler.SERVED_ENTRY_SCHEMA), (where, entry)
            for field in assembler.MIRRORED_FROM_PUZZLE_FILE:
                assert entry[field] == served[entry["key"]][field], (where, field)
                checked += 1
    assert checked == len(assembler.MIRRORED_FROM_PUZZLE_FILE) * (
        len(keys) + len(BOOK_ORDER)
    ) >= 40

    # The control: one changed value in one entry has to break the equality.
    entry = dict(listings["index.json"]["puzzles"][0])
    entry["height"] = entry["height"] + 1
    assert entry["height"] != served[entry["key"]]["height"], "the comparison reads nothing"


def test_the_listing_capacity_is_partitioned_and_can_fail(monkeypatch, tmp_path) -> None:
    """``check_listing_capacity``'s default-deny, and that it is consulted.

    Three halves, the shape ``test_the_capacity_bound_is_derived_and_can_fail``
    established: the partition holds today, a served listing field in neither
    bucket is refused, and ``assemble`` refuses outright rather than merely
    having the function available (without the third half the call site could
    be deleted and the first two would stay green).
    """
    assert assembler.check_listing_capacity() is None
    carried = (
        set(assembler.SERVED_INDEX_SCHEMA)
        | set(assembler.SERVED_BOOK_SCHEMA)
        | set(assembler.SERVED_ENTRY_SCHEMA)
    )
    assert carried == set(assembler.MIRRORED_FROM_PUZZLE_FILE) | set(
        assembler.LISTING_STRUCTURE_FIELDS
    )
    assert not set(assembler.MIRRORED_FROM_PUZZLE_FILE) & set(
        assembler.LISTING_STRUCTURE_FIELDS
    )
    # The entry schema is DERIVED from the one served schema, not written
    # again: a field added there arrives here and has to be bucketed.
    assert assembler.SERVED_ENTRY_SCHEMA == tuple(
        name for name in assembler.SERVED_SCHEMA if name != "clues"
    )

    monkeypatch.setattr(
        assembler, "SERVED_BOOK_SCHEMA", (*assembler.SERVED_BOOK_SCHEMA, "note")
    )
    with pytest.raises(ValueError, match="not partitioned"):
        assembler.check_listing_capacity()
    with pytest.raises(ValueError, match="not partitioned"):
        assembler.assemble(None, tmp_path / "refused")
    assert not (tmp_path / "refused" / "library").exists()
    monkeypatch.undo()

    # And a name in BOTH buckets is refused too — "accounted twice" is not
    # accounted, and set union alone would not notice it.
    monkeypatch.setattr(
        assembler, "LISTING_STRUCTURE_FIELDS", (*assembler.LISTING_STRUCTURE_FIELDS, "tier")
    )
    with pytest.raises(ValueError, match="not partitioned"):
        assembler.check_listing_capacity()


# ==========================================================================
# CARD-282's F-8: a half-written bundle
# ==========================================================================


def test_a_listing_never_names_a_puzzle_the_site_does_not_serve(tmp_path) -> None:
    """F-8, decided: the listings degrade, and the degradation is named.

    The shape chosen of the three the card offered: **neither listing names a
    key whose file is absent**, because every entry IS a served payload, and
    every dropped key is reported. Measured over a bundle whose ``index.json``
    and book both name a puzzle file that was deleted — the exact state a
    ``_dump`` failure part-way through an export leaves behind.

    Both directions of the instrument, because a report that cannot say
    "nothing is wrong" differently from "I did not look" is not one:

    #. the complete bundle: nothing unresolved, nothing unlisted, and the
       missing key's tile present — the positive control;
    #. the half-written bundle: the tile gone from both listings, the key
       named in ``unresolved`` once per listing that declared it;
    #. a bundle with **no** ``index.json`` at all: every served key reported
       ``unlisted`` and the reason stated, rather than a silent pass.
    """
    root = tmp_path / "bundle"
    keys, slug = write_pages_bundle(root, order=BOOK_ORDER)
    whole = assembler.assemble(root, tmp_path / "whole")
    assert whole.unresolved == (), whole.unresolved
    assert whole.unlisted == (), whole.unlisted
    assert whole.index_unread is None
    served_book = json.loads(
        (whole.site_dir / "book" / f"{slug}.json").read_text(encoding="utf-8")
    )
    assert keys["n30"] in [entry["key"] for entry in served_book["puzzles"]]

    # Half-written: one puzzle file never landed. It is a member of the book
    # AND of the index, so both listings have to drop it.
    (root / "puzzle" / f"{keys['n30']}.json").unlink()
    half = assembler.assemble(root, tmp_path / "half")
    assert half.puzzle_count == len(keys) - 1
    assert sorted(half.unresolved) == sorted(
        [("index.json", keys["n30"]), (f"book/{slug}.json", keys["n30"])]
    ), half.unresolved
    assert half.unlisted == (), half.unlisted

    index = json.loads((half.site_dir / "index.json").read_text(encoding="utf-8"))
    book = json.loads((half.site_dir / "book" / f"{slug}.json").read_text(encoding="utf-8"))
    listed = {entry["key"] for entry in index["puzzles"]} | {
        entry["key"] for entry in book["puzzles"]
    }
    assert keys["n30"] not in listed
    # Every key either listing names has a file on the site. This is the
    # claim, and it is a statement about the tree rather than about the code.
    for key in listed:
        assert (half.site_dir / "puzzle" / f"{key}.json").is_file(), key
    # The book's remaining order is still the book's order, minus the hole.
    assert [entry["key"] for entry in book["puzzles"]] == [
        keys[name] for name in BOOK_ORDER if name != "n30"
    ]

    # No index at all: the instrument says so instead of saying nothing.
    (root / "index.json").unlink()
    blind = assembler.assemble(root, tmp_path / "blind")
    assert blind.index_unread is not None and "index.json" in blind.index_unread
    assert sorted(blind.unlisted) == sorted(
        key for name, key in keys.items() if name != "n30"
    )
    # ...and the served library is still complete and still 404-free, because
    # the guarantee never depended on that index.
    rebuilt = json.loads((blind.site_dir / "index.json").read_text(encoding="utf-8"))
    assert sorted(entry["key"] for entry in rebuilt["puzzles"]) == sorted(blind.unlisted)


def test_a_book_the_schema_cannot_accept_is_refused_and_named(tmp_path) -> None:
    """``served_book``'s every refusal branch, each with its own reason.

    The pairing CARD-283's cycle 2 arrived at (N-7): a case refused by a rule
    other than the one it is named for passes a truthiness assertion while its
    own rule's control is dead, so each case here declares the fragment of the
    reason it must be refused for.

    "Every branch" is held to the code and not to the length of the table —
    the ``raise ValueError`` statements in ``served_book`` are counted in the
    source, so a new branch with no case reds here.
    """
    root = tmp_path / "bundle"
    keys, slug = write_pages_bundle(root, order=BOOK_ORDER)
    good = json.loads((root / "book" / f"{slug}.json").read_text(encoding="utf-8"))
    cases = {
        "slug": ({**good, "slug": "NOTASLUG"}, "is not 10 lowercase hex characters"),
        "name": (
            {**good, "slug": player_bundle.book_slug(["0" * 10])},
            "but carries the slug",
        ),
        "keys-type": ({**good, "puzzle_keys": "abc"}, "puzzle_keys is not a list"),
        "keys-member": (
            {**good, "puzzle_keys": [*good["puzzle_keys"], "NOPE"]},
            "puzzle_keys[4] 'NOPE' is not 10 lowercase hex characters",
        ),
        "not-an-object": ([good], "the file is not a JSON object"),
    }
    for name, (payload, because) in cases.items():
        path = root / "book" / f"{slug}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        report = assembler.assemble(root, tmp_path / f"site-{name}")
        assert report.book_count == 0, name
        assert len(report.refused) == 1 and report.refused[0][0] == slug, (name, report.refused)
        assert because in report.refused[0][1], (name, because, report.refused[0][1])
        # A refused BOOK must not cost the library its puzzles.
        assert report.puzzle_count == len(keys), name
        assert not (report.site_dir / "book").exists(), name
    assert len({because for _, because in cases.values()}) == len(cases)

    tree = ast.parse((PLAYER_DIR / "assemble.py").read_text(encoding="utf-8"))
    branches = {
        node.name: sum(isinstance(child, ast.Raise) for child in ast.walk(node))
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "served_book"
    }
    assert branches == {"served_book": 3}, branches
    # Three raises, five cases: ``_key`` is reached twice with different
    # ``what`` values (the slug and a member of puzzle_keys), and the
    # not-an-object case is the first raise. Counted so the table cannot
    # shrink below the branch set.
    assert len(cases) > sum(branches.values())

    # The control for all of them: the unedited file is served.
    path = root / "book" / f"{slug}.json"
    path.write_text(json.dumps(good), encoding="utf-8")
    assert assembler.assemble(root, tmp_path / "site-good").book_count == 1


def test_a_book_with_no_resolvable_puzzle_is_still_served_empty(tmp_path) -> None:
    """A published slug keeps its page; the not-found panel is for a missing one.

    The distinction AC-388 rests on, and it is a decision rather than a
    detail: a QR code on paper resolves to a slug that exists, so "this book's
    puzzles are not on the site yet" and "we have never heard of this book"
    must not be the same page. The empty book is served with an empty list and
    every one of its keys is named unresolved.
    """
    root = tmp_path / "bundle"
    keys, slug = write_pages_bundle(root, order=BOOK_ORDER)
    for key in keys.values():
        (root / "puzzle" / f"{key}.json").unlink()
    report = assembler.assemble(root, tmp_path / "site")
    assert report.puzzle_count == 0
    assert report.book_count == 1
    book = json.loads((report.site_dir / "book" / f"{slug}.json").read_text(encoding="utf-8"))
    assert book == {"slug": slug, "puzzles": []}
    assert sorted(key for _, key in report.unresolved) == sorted(
        [keys[name] for name in BOOK_ORDER] + sorted(keys.values())
    )


# ==========================================================================
# The pages' own hand-written sets, held to the runtime's
# ==========================================================================


def _js_constant(name: str) -> object:
    """A JSON-shaped ``export const <name> = ...;`` out of ``pages.js``.

    Read from the shipped file rather than restated here, which is the only
    version of this cross-check that can fail: the assertion is against the
    bytes the browser runs. Two narrow transformations make the literal JSON —
    object keys are unquoted in the source, and a trailing comma is legal
    there and not here — over a value whose shape this module also asserts.
    """
    source = (PLAYER_DIR / "pages.js").read_text(encoding="utf-8")
    match = re.search(rf"^export const {name} = (.+?);$", source, re.S | re.M)
    assert match is not None, f"pages.js declares no {name}"
    text = re.sub(r"(\w+):", r'"\1":', match.group(1))
    text = re.sub(r",(\s*[\]}])", r"\1", text)
    return json.loads(text)


def test_the_size_bands_partition_the_supported_extent() -> None:
    """ADR-0039/R1 — the bands are limits.py's, and they cover it exactly.

    A static page cannot read ``limits.py``, so ``SIZE_BANDS`` holds numbers
    (the one place CLAUDE.md's "use limits.py rather than writing 10 or 30"
    cannot reach), and the equality lives here — the same arrangement
    ``play.js``'s key pattern and ``assemble.py``'s tier set live under.

    Completeness as well as equality: every supported side is in exactly one
    band, no gap and no overlap, which is what makes "exactly the matching
    entries remain" a statement about the whole range rather than about the
    corpus. The control plants a one-cell gap.
    """
    bands = _js_constant("SIZE_BANDS")
    span = MAX_SIZE - MIN_SIZE + 1
    assert span % len(bands) == 0, (
        f"{span} supported sides do not divide into {len(bands)} equal bands; "
        "the bands need re-deriving, not rounding"
    )
    width = span // len(bands)
    expected = [
        {"min": MIN_SIZE + index * width, "max": MIN_SIZE + (index + 1) * width - 1}
        for index in range(len(bands))
    ]
    assert [{"min": band["min"], "max": band["max"]} for band in bands] == expected
    assert bands[0]["min"] == MIN_SIZE and bands[-1]["max"] == MAX_SIZE

    def holding(side: int) -> list[str]:
        return [band["id"] for band in bands if band["min"] <= side <= band["max"]]

    for side in range(MIN_SIZE, MAX_SIZE + 1):
        assert len(holding(side)) == 1, (side, holding(side))
    # The control: one band narrowed by a cell leaves a side in no band.
    gapped = [dict(band) for band in bands]
    gapped[0]["max"] -= 1
    assert not [
        band for band in gapped if band["min"] <= gapped[0]["max"] + 1 <= band["max"]
    ], "the completeness check cannot see a gap"

    # And the fixture's own expectation agrees with the shipped rule, so
    # AC-389's expected sets are not derived from the page under test.
    for name, band in PAGE_BANDS.items():
        side = max(len(PAGE_GRIDS[name][0]), len(PAGE_GRIDS[name]))
        assert holding(side) == [band], (name, side)


def test_the_pages_tier_vocabulary_is_the_runtimes(pages_site) -> None:
    """ADR-0039/R2 — the tier options are the enum's, not a hand-written list.

    Held in three places at once, because the drift this closes is between
    them: the runtime enum, ``pages.js``'s ``TIERS``, and the ``<option>``
    values in ``library.html``. A tier added to the enum reds here instead of
    silently becoming a filter that matches nothing.
    """
    runtime = [tier.value for tier in Tier]
    assert _js_constant("TIERS") == runtime
    # The assembler's served set is the same vocabulary, so a served tier is
    # always a selectable one.
    assert sorted(assembler.SERVED_TIERS) == sorted(runtime)

    html = (PLAYER_DIR / "library.html").read_text(encoding="utf-8")
    block = re.search(r'<select data-pages-filter="tier">(.+?)</select>', html, re.S)
    assert block is not None, "library.html has no tier filter"
    values = re.findall(r'<option value="([^"]*)"', block.group(1))
    assert values == ["", *runtime], values

    bands = _js_constant("SIZE_BANDS")
    size = re.search(r'<select data-pages-filter="size">(.+?)</select>', html, re.S)
    assert size is not None, "library.html has no size filter"
    assert re.findall(r'<option value="([^"]*)"', size.group(1)) == [
        "",
        *[band["id"] for band in bands],
    ]

    # The served corpus only ever carries one of them or the blank.
    report, keys, _ = pages_site
    index = json.loads((report.site_dir / "index.json").read_text(encoding="utf-8"))
    assert {entry["tier"] for entry in index["puzzles"]} <= {"", *runtime}


# ==========================================================================
# The tree: static, token-only, routed by the shipped config
# ==========================================================================


def test_the_two_doors_are_routed_by_the_shipped_config(pages_site) -> None:
    """``vercel.json`` carries a rule for each door, read from the artefact.

    The fixture host routes by this file, so a door with no rule would fail
    the browser tests above — this test is what says *which* file those tests
    were driven by, and that the rule's destination is a page the site has.
    """
    report, _, _ = pages_site
    pairs = rewrites(report.site_dir)
    matched = {}
    for path, expected in (
        ("/play/0123456789", "/play/index.html"),
        ("/b/0123456789", "/b/index.html"),
        ("/library", "/library/index.html"),
    ):
        hit = [destination for pattern, destination in pairs if pattern.match(path)]
        assert hit == [expected], (path, hit)
        matched[path] = expected
        assert (report.site_dir / expected.lstrip("/")).is_file(), expected
    assert len(matched) == 3
    # A path no rule covers still has none, so the rules are rules and not a
    # catch-all that would hide a missing page.
    assert [d for pattern, d in pairs if pattern.match("/nothing/here")] == []


def test_the_listing_pages_carry_no_colour_literal_and_only_defined_tokens() -> None:
    """Colours belong to tokens.css, and every token these files use exists.

    The same rule CARD-283 holds its three files to, extended to this card's
    three — and with the hole that rule has closed for them: its ``used``
    pattern is ``var\\((--name)\\)`` and so cannot see ``var(--name,
    fallback)``, which is the form a tier hue is read through. Here a ``var(``
    is read whether or not it carries a fallback, and the control plants an
    undefined name inside a fallback form, where the narrower pattern would
    miss it.
    """
    tokens = set(
        re.findall(
            r"(--[a-z0-9-]+)\s*:",
            (REPO_ROOT / "src/nonogram/admin/static/tokens.css").read_text(encoding="utf-8"),
        )
    )
    assert len(tokens) >= 40, len(tokens)
    files = {
        name: (PLAYER_DIR / name).read_text(encoding="utf-8")
        for name in ("library.html", "book.html", "pages.js", "player.css")
    }

    def undefined_in(text: str) -> list[str]:
        # ``--player-width`` / ``--player-height`` are set on the board
        # element by play.js and so are declared in script rather than in
        # CSS, which is why they are named here — CARD-283's own rule names
        # them for the same reason.
        defined = tokens | {"--player-width", "--player-height"}
        defined |= set(re.findall(r"(--[a-z0-9-]+)\s*:", text))
        used = set(re.findall(r"var\(\s*(--[a-z0-9-]+)", text))
        return sorted(used - defined)

    for name, text in files.items():
        assert not re.search(r"#[0-9a-fA-F]{3,8}\b", text), name
        assert "rgb(" not in text and "hsl(" not in text, name
        assert undefined_in(text) == [], name

    css = files["player.css"]
    assert "var(--player-tier-hue," in css, "the fallback form is not exercised here"
    # The control, in the fallback form the narrower pattern cannot read.
    planted = css.replace("var(--player-tier-hue,", "var(--player-tier-hueu,")
    assert undefined_in(planted) == ["--player-tier-hueu"]
    assert sorted(re.findall(r"var\((--[a-z0-9-]+)\)", planted)) == sorted(
        re.findall(r"var\((--[a-z0-9-]+)\)", css)
    ), "the narrower pattern would have caught the plant, so it proves nothing"


def test_the_two_pages_add_nothing_to_the_package_and_no_toolchain() -> None:
    """ADR-0041/R3 — three more hand-written files, and still no build step.

    The published set is the authority (``PLAYER_FILES``), so a page added to
    ``player/`` and published reds nothing while one added and NOT published
    fails here — and the npm artefacts are refused by name.
    """
    for name in ("library.html", "book.html", "pages.js"):
        assert name in assembler.PLAYER_FILES, name
        assert (PLAYER_DIR / name).is_file(), name
    for forbidden in ("package.json", "node_modules", "package-lock.json", "tsconfig.json"):
        assert not (PLAYER_DIR / forbidden).exists(), forbidden
    manifest = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "player/" not in manifest and '"player"' not in manifest
    # The two pages are modules served from the site root, as play.html's is:
    # a relative src would break under the /b/<slug> and /library rewrites,
    # which serve one document at many paths.
    for name in ("library.html", "book.html"):
        page = (PLAYER_DIR / name).read_text(encoding="utf-8")
        assert '<script type="module" src="/pages.js"></script>' in page, name
        assert 'href="/player.css"' in page and 'href="/tokens.css"' in page, name
        assert "http://" not in page and "https://" not in page.replace(
            "https://openapi.vercel.sh", ""
        ), name


def test_the_registrys_refs_for_this_file_resolve_or_are_card_285s() -> None:
    """Every ``tests/test_public_player_pages.py::…`` ref, placed on purpose.

    The defect CARD-283 measured and this card inherits: the validator
    resolves a check ref by ``git grep -lw`` of the whole ``path::name``
    string, so a ref whose string appears nowhere in tracked code reads as
    verified at planning time and is not. Six refs name this file. Three are
    AC-387..389 and are defined here; three (AC-390..392) are CARD-285's and
    are deliberately absent.

    Both directions, so neither half can rot: a ref this file does not define
    must be one of the three named below, and a ref that IS defined here must
    be in the registry.
    """
    registry = (REPO_ROOT / "meta/architecture/requirements.yml").read_text(encoding="utf-8")
    here = Path(__file__).name
    refs = set(re.findall(rf"tests/{here}::(\w+)", registry))
    assert len(refs) >= 6, sorted(refs)

    source = Path(__file__).read_text(encoding="utf-8")
    defined = {
        node.name
        for node in ast.parse(source).body
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    }
    mine = {
        "test_book_landing_lists_and_links",
        "test_unknown_slug_lands_softly",
        "test_library_filters_the_index",
    }
    card_285 = {
        "test_assembled_site_is_self_contained",
        "test_pages_work_with_analytics_blocked",
        "test_no_homegrown_tracking",
    }
    assert mine <= defined, sorted(mine - defined)
    assert refs - defined == card_285, sorted(refs - defined)
    assert refs & defined == mine, sorted(refs & defined)

    # And the docstring's table carries each of mine as the whole path::name
    # string on one line, which is the only form the validator resolves.
    table = __doc__ or ""
    for name in sorted(mine):
        assert f"tests/{here}::{name}" in table, name
