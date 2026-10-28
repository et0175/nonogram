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

#. **the title — and it is TWO fields, with opposite answers.**
   ``index.json`` and ``book/<slug>.json`` each carry a bundle ``title``, and
   CARD-283 served neither file rather than decide for them. Cycle 1 of this
   card's review gated on the two being argued as one, so they are separated
   everywhere below:

   * a **puzzle's** title is the picture's name. EC-048 forbids it by name on
     every asset the public site serves, CARD-282 recovered all 144 cells of
     a 12x12 answer out of a published one, and there is no decision
     procedure for "does this string carry a grid?". It is in no served
     schema, the sweep that proves the bundle dirty and the site clean runs
     over both listings here, and ``check_listing_capacity`` refuses to
     assemble if the name is added to a puzzle file or to the library index
     (``test_no_puzzle_title_reaches_either_listing``,
     ``test_the_listing_capacity_is_partitioned_and_can_fail``);
   * a **book's** display title is owner-authored editorial text served
     under **ADR-0041/R2's third exemption (owner decision, 2026-10-28)**,
     which is the authority and the only justification these tests cite.
     Fix round 1 wrote "EC-048's enumeration does not name it" here and
     cycle 2 measured that false — EC-048's fourth clause is R2's own "or
     data from which any solution cell is recoverable", which is not an
     enumeration anything can fail to be named in, and an FR cannot narrow
     a mandatory rule in any case. R2 was amended instead, exempting the
     title by SCOPE rather than by safety. ``/b/<slug>`` renders it as its
     heading, and the exemption's SCOPE and its COST are both measured —
     ``test_the_book_title_exemption_is_scoped_and_its_cost_is_measured``
     recovers a whole MIN_SIZE grid out of a served book title, which is what
     a declared residual looks like when it is measured instead of argued;
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
establishes "no listing ENTRY field carries anything a puzzle file does not",
not EC-048's one-cell threshold. Three residuals sit outside it and each is
declared where it lives: a book's ORDER and its MEMBERSHIP
(``assemble.py``'s ``LISTING_STRUCTURE_FIELDS``), and the book's display
TITLE, which is an exemption rather than a bound and is 2410.18 bits wide at
today's constants (``assemble.py``'s ``EXEMPT_LISTING_FIELDS``,
``book_title_residual_bits``).

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
import math
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

#: The fixture book's display title. Deliberately **editorial** — the exact
#: opposite of every PUZZLE title in this module, which is base-64 of its own
#: grid — because the two fields get opposite answers and a fixture that made
#: them both leaky could not tell "the exemption is scoped" from "the sweep
#: is broken".
#:
#: It carries a newline and a double space so that ``_book_title``'s
#: whitespace collapsing is exercised by the default fixture rather than only
#: by a case written for it, and a dash so the served value is not an ASCII
#: identifier by accident.
BOOK_TITLE = "Winter  Pictures\n— Volume Two"

#: What ``assemble.py`` must serve for :data:`BOOK_TITLE`: one line, single
#: spaces. Written out rather than derived with the function under test.
BOOK_TITLE_SERVED = "Winter Pictures — Volume Two"


def write_pages_bundle(
    root: Path, names=None, *, order=None, leaky: bool = True, book_title=None
) -> tuple[dict[str, str], str]:
    """A bundle at ``root`` holding one book. Returns ``({name: key}, slug)``.

    Every **puzzle** title is the base-64 of its own grid by default —
    CARD-282's measured leak — because a fixture titled "Snowy owl" would
    make every assertion below pass for the wrong reason.

    The **book's** title is :data:`BOOK_TITLE`, which is editorial text, and
    the difference is the point: the book's title is served (the owner's
    2026-10-28 decision) and a puzzle's is not, so a fixture whose book title
    was also base-64 of a grid could not distinguish "the exemption is
    scoped to the book file" from "the sweep stopped working". ``book_title``
    overrides it, which is how
    ``test_the_book_title_exemption_is_scoped_and_its_cost_is_measured``
    measures what the exemption costs.

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
        "title": BOOK_TITLE if book_title is None else book_title,
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


#: How long :func:`_open_pages` waits for a page to settle, in
#: milliseconds. Explicit, and ~10x the 0.1-0.24 s these calls actually take.
#:
#: Playwright's default is 30 s, and cycle 1 of this card's review MEASURED
#: what that costs: the mutant that stopped the not-found panel being shown
#: took **62.63 s** for this file against a 2.9 s baseline. Fix round 1's
#: comment attributed that to "two navigations each burned the full
#: default", and cycle 2 corrected it (F-010): the pages LOAD fine, so
#: ``goto`` returned promptly and the 30 s went on the SETTLE below, which
#: is where the mutant made the condition unreachable. Six browser nodes use
#: this helper, and on this board a shell call over ~2 minutes returns a
#: truncated log that is indistinguishable from a suite failure — so a
#: regression here used to buy minutes of ambiguity instead of a fast red.
#:
#: It bounds the navigation as well, which is the residual cycle 2 named:
#: ``goto`` carried no explicit timeout and kept the 30 s default, so a
#: genuinely hung fixture server — the one case that is NOT what cycle 1
#: measured — would still have burned it per node.
PAGES_SETTLE_MS = 3000


def _open_pages(page, url: str, path: str) -> None:
    page.goto(f"{url}{path}", timeout=PAGES_SETTLE_MS)
    page.wait_for_function(
        "() => window.playerPages !== undefined"
        " || !document.querySelector('[data-pages-notfound]').hidden",
        timeout=PAGES_SETTLE_MS,
    )


# ==========================================================================
# The three acceptance criteria (browser)
# ==========================================================================


@pytest.mark.browser
def test_book_landing_lists_and_links(browser_page, pages_host) -> None:
    """AC-387 — the QR landing titles the book and lists its puzzles in order.

    Four things now the AC has four clauses, and the order is the one with
    teeth: ``BOOK_ORDER`` is neither the sorted key order nor the whole
    library, so a page that sorted its tiles, or listed everything served,
    fails here. The link is then followed for real rather than read off the
    ``href``: tapping the second tile has to land on CARD-283's board for
    that key.

    The title clauses are the owner's 2026-10-28 decision, and they are a
    PAIR rather than one claim: the BOOK's display title heads the page, and
    no PUZZLE's title appears anywhere on it. The second is what keeps the
    first from being read as "titles are fine now" — the fixture's puzzle
    titles are base-64 of their own grids, so a page that showed one would
    publish an answer. The deeper reading of the heading (markup is text, a
    capped title does not scroll the phone sideways) is
    ``test_the_book_landing_shows_the_books_title``'s.
    """
    url, report, keys, slug = pages_host
    expected = [keys[name] for name in BOOK_ORDER]
    assert expected != sorted(expected), "the fixture's order is the sorted one"
    assert len(expected) < len(keys), "the fixture's book is not a strict subset"

    _open_pages(browser_page, url, f"/b/{slug}")
    assert _tiles(browser_page) == expected
    assert browser_page.evaluate("() => window.playerPages.slug") == slug

    # The book's display title heads the page (AC-387's first clause).
    assert browser_page.locator("[data-pages-title]").inner_text() == BOOK_TITLE_SERVED

    # And no PUZZLE title is anywhere on it (AC-387's third clause). Every
    # fixture puzzle title is base-64 of its own grid, so this is a real
    # negative rather than a search for a word nobody wrote.
    rendered = browser_page.evaluate("() => document.body.innerText")
    for name in BOOK_ORDER:
        assert _leaky_title(PAGE_GRIDS[name]) not in rendered, name

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
def test_the_listing_pages_only_get_and_write_nothing(browser_page, pages_host) -> None:
    """EC-050's half of these two pages: nothing leaves them (ADR-0041/R4).

    Every request either page makes is a same-origin GET, and filtering —
    the only interaction they have — issues none at all. Asserted as the
    METHOD and the ORIGIN of every request, never as a request count, which
    is the distinction CARD-283's own EC-050 test rests on.

    The name said ``issue_one_get`` until CARD-284's fix round, which is a
    count this body deliberately does not assert — and a node id is the
    string a gate log and a check ref quote, so it has to state the
    measurement rather than a stronger nearby property (cycle 1, F-011).
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

**Seven shapes over six mechanisms**: one per guard of ``isEntry`` — there
    are five — plus ``readListing``'s own wrapper, plus the SECOND EDGE of the
    one guard that is a range. Each is one edit from valid, and the unedited
    listing is the positive control in the same test.

    The count is written as an arithmetic against the source below rather
    than as prose, because the prose is what went wrong: this docstring said
    "four shapes, one per branch of ``isEntry`` plus the wrapper" over four
    cases, and ``isEntry`` has five guards — so two of them had no case at
    all, and the claim was not merely loose but counted a set it had not
    counted. Cycle 1 of this card's review killed the wrapper's mutant and
    then survived two EDGE mutants on the guards nothing read:

    * ``Number.isInteger`` appeared in no test at all — the ``extent-not-int``
      case below is its first reader. ``if (!Number.isInteger(extent))`` ->
      ``if (false && ...)`` survived 18/18;
    * the extent range was planted at ``MAX_SIZE + 1`` only, so
      ``extent < SIZE_BANDS[0].min`` -> ``... - 1`` survived 18/18. This repo
      had already named that exact hole once — ``tests/test_public_player.py``'s
      puzzle-file table calls ``MIN_SIZE - 1`` "the one value that reads it" —
      and did not carry it across the wire. The ``extent-below-min`` case is
      the carry.

    A third guard had no case either and no mutant was fired at it in cycle
    1: ``value`` not being an object at all. ``entry-is-null`` is it, and it
    is distinct from ``not-a-listing``, which reads the wrapper. ``null`` is
    the value that reads it *uniquely*: a string or a number falls through
    the destructuring and is refused by the key guard anyway, so it would
    leave the first guard unmeasured, while ``null`` throws on destructuring
    the moment that guard stops firing — so the page neither renders nor
    shows its panel, and this test reds on a settle timeout instead of
    passing for the wrong reason.

    What is NOT claimed, because it is not true: the first guard is three
    disjuncts (``null``, not an object, an array) and only the first of them
    has a case that reads it alone. A JSON array cannot carry the four
    properties the later guards read, so no case distinguishes the array
    disjunct from the key guard. The arithmetic below counts REFUSAL
    STATEMENTS, which is what it says.

    The new cases are declared against the GUARD they read, not just against
    "refused": the extents are built from ``MIN_SIZE`` and ``MAX_SIZE`` so a
    limits change moves them, and ``str(MIN_SIZE)`` is a value that is IN
    range as a number, so only the integer guard can refuse it — the
    non-integer form that same puzzle-file table uses.
    """
    report, keys, slug = pages_site
    index = report.site_dir / "index.json"
    good = json.loads(index.read_text(encoding="utf-8"))
    first = good["puzzles"][0]
    cases = {
        "not-a-listing": {"puzzles": {"a": 1}},
        "entry-is-null": {"puzzles": [first, None]},
        "bad-key": {"puzzles": [{**first, "key": "NOTAKEY"}]},
        "extent-above-max": {"puzzles": [{**first, "width": MAX_SIZE + 1}]},
        "extent-below-min": {"puzzles": [{**first, "height": MIN_SIZE - 1}]},
        "extent-not-int": {"puzzles": [{**first, "width": str(MIN_SIZE)}]},
        "bad-tier": {"puzzles": [{**first, "tier": "tqlhkuhxpmgj"}]},
    }
    # The two extent edges are one cell outside the supported range on either
    # side, and the non-integer is the string form of a value that IS in
    # range — so the integer branch is the only thing that can refuse it.
    assert cases["extent-above-max"]["puzzles"][0]["width"] == MAX_SIZE + 1
    assert cases["extent-below-min"]["puzzles"][0]["height"] == MIN_SIZE - 1
    assert cases["extent-not-int"]["puzzles"][0]["width"] == str(MIN_SIZE)
    assert MIN_SIZE <= int(cases["extent-not-int"]["puzzles"][0]["width"]) <= MAX_SIZE
    # "One per guard" is held to the CODE and not to the length of the
    # table — the shape test_a_book_the_schema_cannot_accept_is_refused_and
    # _named uses for served_book: a guard added to isEntry with no case reds
    # here, which is exactly what did NOT happen in the implementation round.
    # The arithmetic: one case per guard, plus readListing's wrapper, plus
    # the second edge of the range guard.
    source = (PLAYER_DIR / "pages.js").read_text(encoding="utf-8")
    body = re.search(r"export function isEntry\(value\) \{(.+?)\n\}", source, re.S)
    assert body is not None, "pages.js declares no isEntry"
    guards = len(re.findall(r"\breturn false\b", body.group(1))) + len(
        re.findall(r"\breturn tier ===", body.group(1))
    )
    assert guards == 5, guards
    extra = {"not-a-listing", "extent-below-min"}  # the wrapper, and the second edge
    assert extra <= set(cases)
    assert len(cases) == guards + len(extra), (sorted(cases), guards)

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


@pytest.mark.browser
def test_the_book_landing_shows_the_books_title(browser_page, pages_host) -> None:
    """The owner's 2026-10-28 decision, rendered (F-001).

    ``/b/<slug>`` is a book customer's first contact with the product seconds
    after scanning a code off paper, and the card's body always required the
    book's title there. Four things, because "it is on the page" is the
    weakest of them:

    #. the heading IS the book's served title, and the served title is the
       bundle's with whitespace collapsed;
    #. ``/library`` keeps its own heading — the exemption is for a book file,
       and the library has no book;
    #. the string is TEXT. A title with markup in it renders as characters:
       the heading gets no child element and no request leaves for the
       ``<img>`` in it. ``textContent``, never ``innerHTML``, on a heading a
       stranger reached by scanning a code off paper;
    #. a title at the full cap does not push the page sideways on a 390 px
       phone, which is the viewport nearly every visit arrives on.
    """
    url, report, keys, slug = pages_host
    book_file = report.site_dir / "book" / f"{slug}.json"
    served = json.loads(book_file.read_text(encoding="utf-8"))
    assert served["title"] == BOOK_TITLE_SERVED

    _open_pages(browser_page, url, f"/b/{slug}")
    heading = browser_page.locator("[data-pages-title]")
    assert heading.inner_text() == BOOK_TITLE_SERVED
    assert browser_page.evaluate("() => window.playerPages.title") == BOOK_TITLE_SERVED
    assert len(_tiles(browser_page)) == len(BOOK_ORDER)

    # The library's heading is its own, and its playerPages carries no title.
    _open_pages(browser_page, url, "/library")
    assert browser_page.locator("[data-pages-title]").count() == 0
    assert browser_page.locator(".player-head h1").inner_text() == "Library"
    assert browser_page.evaluate("() => window.playerPages.title") == ""

    # Markup in the title is text. The <img> would issue a request if the
    # string were parsed, so the request log is the second instrument.
    requested: list[str] = []
    browser_page.on("request", lambda request: requested.append(request.url))
    hostile = '<img src="/nope.png" onerror="window.pwned = 1"> & <b>bold</b>'
    book_file.write_text(
        json.dumps({**served, "title": hostile}, indent=2, sort_keys=True), encoding="utf-8"
    )
    _open_pages(browser_page, url, f"/b/{slug}")
    assert browser_page.locator("[data-pages-title]").inner_text() == hostile
    assert browser_page.evaluate("() => document.querySelector('[data-pages-title]').children.length") == 0
    assert browser_page.evaluate("() => window.pwned") is None
    assert [where for where in requested if "nope.png" in where] == [], requested

    # A title at the cap, on the phone the QR code is scanned with: it wraps,
    # it does not scroll. The control is in the same assertion pair — the
    # tiles are still there, so this is a laid-out page and not a blank one.
    browser_page.set_viewport_size({"width": 390, "height": 780})
    longest = "Verylongunbrokenbooktitleword" * 10
    capped = longest[: assembler.SERVED_TITLE_MAX_CHARS]
    book_file.write_text(
        json.dumps({**served, "title": capped}, indent=2, sort_keys=True), encoding="utf-8"
    )
    _open_pages(browser_page, url, f"/b/{slug}")
    assert browser_page.locator("[data-pages-title]").inner_text() == capped
    assert len(capped) == assembler.SERVED_TITLE_MAX_CHARS
    assert browser_page.evaluate(
        "() => document.documentElement.scrollWidth <= document.documentElement.clientWidth"
    ), "a capped title pushed the landing page sideways on a 390 px phone"
    assert len(_tiles(browser_page)) == len(BOOK_ORDER)

    # The PAGE's own cap, which is a separate mechanism from the assembler's
    # and until now had no reader: assemble.py truncates, so a served file
    # never tests it. A book file hand-edited after assembly does. pages.js's
    # TITLE_MAX_CHARS is the second half of the same
    # check-on-both-sides-of-the-wire rule isEntry lives under, and this is
    # the only shape that can red it.
    book_file.write_text(
        json.dumps({**served, "title": "y" * 10000}, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _open_pages(browser_page, url, f"/b/{slug}")
    shown = browser_page.locator("[data-pages-title]").inner_text()
    assert shown == "y" * assembler.SERVED_TITLE_MAX_CHARS, len(shown)
    assert browser_page.evaluate("() => window.playerPages.title.length") == (
        assembler.SERVED_TITLE_MAX_CHARS
    )


@pytest.mark.browser
def test_an_empty_book_renders_its_empty_note(browser_page, pages_host) -> None:
    """``book.html``'s empty paragraph, rendered in a browser for the first time.

    ``test_a_book_with_no_resolvable_puzzle_is_still_served_empty`` holds the
    assembler's half: a published slug keeps its page with an empty list. The
    markup half had never rendered — cycle 1 of this card's review named it
    (F-012) — so a page that threw while drawing an empty list, or that
    showed the NOT-FOUND panel instead, would have looked tested.

    The distinction is the whole point of AC-388: "this book's puzzles are
    not on the site yet" and "we have never heard of this book" must not be
    the same page. Both are asserted here, against each other.
    """
    url, report, keys, slug = pages_host
    book_file = report.site_dir / "book" / f"{slug}.json"
    served = json.loads(book_file.read_text(encoding="utf-8"))

    thrown: list[str] = []
    browser_page.on("pageerror", lambda error: thrown.append(str(error)))

    book_file.write_text(
        json.dumps({**served, "puzzles": []}, indent=2, sort_keys=True), encoding="utf-8"
    )
    _open_pages(browser_page, url, f"/b/{slug}")
    assert _tiles(browser_page) == []
    assert browser_page.locator("[data-pages-empty]").is_visible()
    assert (
        "None of this book's puzzles are on the site yet"
        in browser_page.locator("[data-pages-empty]").inner_text()
    )
    # NOT the not-found panel: the slug is real and printed on paper.
    assert not browser_page.locator("[data-pages-notfound]").is_visible()
    # The title still names the book, which is what makes the page useful.
    assert browser_page.locator("[data-pages-title]").inner_text() == BOOK_TITLE_SERVED
    assert browser_page.locator("[data-pages-count]").inner_text() == "0 puzzles"

    # The positive control, in the same test: the unedited file shows tiles
    # and no empty note, so "the note is up" cannot pass for free.
    book_file.write_text(json.dumps(served, indent=2, sort_keys=True), encoding="utf-8")
    _open_pages(browser_page, url, f"/b/{slug}")
    assert len(_tiles(browser_page)) == len(BOOK_ORDER)
    assert not browser_page.locator("[data-pages-empty]").is_visible()
    assert thrown == [], thrown


@pytest.mark.browser
def test_filtering_is_announced_in_a_live_region(browser_page, pages_host) -> None:
    """Filtering rewrites the page silently for a screen reader — it did (F-010).

    ``render()`` replaces the whole tile list, rewrites the count and reveals
    the empty note, and the controls stay put, so there is no focus change to
    notice and nothing is spoken. ``player.css`` already shipped CARD-283's
    ``.player-announce`` and ``pages.js`` did not use it.

    Held as the region's CONTENT after each interaction rather than as the
    presence of an attribute, because an ``aria-live`` node that is never
    written is the same silence with a tick beside it. The region's text is
    the page's own wording — the count element's, or the empty note's — so a
    third copy of the message cannot drift from what is on screen, and that
    is what the assertions compare it against.
    """
    url, report, keys, slug = pages_host
    _open_pages(browser_page, url, "/library")
    region = browser_page.locator("[data-pages-announce]")

    # It is in the document and it is a live region (CARD-283's note: a live
    # region has to be in the document to be announced reliably).
    assert region.count() == 1
    assert region.get_attribute("aria-live") == "polite"
    assert region.get_attribute("role") == "status"
    assert "player-announce" in (region.get_attribute("class") or "")

    def announced() -> str:
        return browser_page.evaluate(
            "() => document.querySelector('[data-pages-announce]').textContent"
        )

    def on_screen() -> str:
        return browser_page.evaluate(
            "() => document.querySelector('[data-pages-count]').textContent"
        )

    assert announced() == on_screen() == f"{len(PAGE_GRIDS)} puzzles"

    browser_page.locator("select[data-pages-filter='tier']").select_option("easy")
    assert announced() == on_screen() == "2 puzzles"
    assert announced() != f"{len(PAGE_GRIDS)} puzzles", "the region did not change"

    # The empty intersection announces the note the page shows, not a count.
    browser_page.locator("select[data-pages-filter='size']").select_option("large")
    assert _tiles(browser_page) == []
    note = browser_page.locator("[data-pages-empty]").inner_text()
    assert browser_page.locator("[data-pages-empty]").is_visible()
    assert announced() == " ".join(note.split())
    assert "No puzzle matches" in announced()

    browser_page.locator("[data-pages-clear]").click()
    assert announced() == on_screen() == f"{len(PAGE_GRIDS)} puzzles"

    # Focus is NOT moved into the rewritten content, which is the decision
    # this test records as well as the announcement: the reader is operating
    # a select, and taking the keyboard away from it to point at a list that
    # has just been redrawn would be worse than saying nothing. Asserted as
    # "focus is still the control" with the control focused first, because
    # select_option alone does not leave focus behind in every driver.
    tier_select = browser_page.locator("select[data-pages-filter='tier']")
    tier_select.focus()
    assert browser_page.evaluate("() => document.activeElement.dataset.pagesFilter") == "tier"
    tier_select.select_option("hard")
    assert announced() == on_screen() == "2 puzzles"
    assert browser_page.evaluate("() => document.activeElement.dataset.pagesFilter") == "tier"
    # ...and neither the list nor the region ever takes it.
    assert browser_page.evaluate(
        "() => document.activeElement.closest('[data-pages-list]') === null"
        " && !document.activeElement.hasAttribute('data-pages-announce')"
    )

    # And the book landing has one too, with the same wiring.
    _open_pages(browser_page, url, f"/b/{slug}")
    assert browser_page.locator("[data-pages-announce]").count() == 1
    assert announced() == f"{len(BOOK_ORDER)} puzzles"



# ==========================================================================
# EC-048's listing half: what the two listings may carry
# ==========================================================================


def test_no_puzzle_title_reaches_either_listing(pages_site, pages_bundle, tmp_path) -> None:
    """The PUZZLE title — the picture's name — removed from both listings.

    This test was ``test_no_title_reaches_either_listing`` until CARD-284's
    fix round. The rename is the finding: the old name claimed something
    wider than the code now does, because a book's own display title IS
    served (the owner's 2026-10-28 decision) while a puzzle's is forbidden by
    EC-048. The two fields are never argued as one here; the book's is
    ``test_the_book_title_exemption_is_scoped_and_its_cost_is_measured``'s.

    One sweep, both directions, exactly as CARD-283's own EC-048 test does
    it: the **bundle's** two listings must be dirty — every PUZZLE title in
    this fixture is base-64 of its own grid, and both listings carry those
    titles — and the **site's** must be clean. A sweep that had quietly
    stopped working cannot report this as a pass.

    The book's title is editorial here (:data:`BOOK_TITLE`), which is what
    keeps the site side of the sweep a statement about picture names: with a
    leaky book title the site would be dirty by design, and that case is
    measured in its own test rather than hidden in this one.

    The sweep therefore gets TWO controls rather than one, because the
    bundle's own book file cannot serve as one: ``BOOK_FILE_FIELDS`` is
    ``(puzzle_keys, slug, title)``, so a bundle book file holds keys and no
    puzzle metadata at all, and a puzzle title can only reach the SERVED book
    file through the entries this card inlines into it. So:

    #. the bundle's ``index.json`` must be dirty — it carries every puzzle's
       title, and that is the path CARD-282 measured;
    #. the leak is PLANTED into each served listing, in the shape the entries
       would have if the schema let a title through, and the sweep has to
       report both files. Without that, "the site is clean" would be
       indistinguishable from "the sweep does not read a listing".
    """
    report, keys, slug = pages_site
    bundle_root, _, _ = pages_bundle
    listings = (assembler.SITE_INDEX_FILE, f"book/{slug}.json")

    # Control 1 — the bundle's index really is dirty with puzzle titles.
    dirty = sweep_tree(bundle_root, PAGE_GRIDS)
    hits = [where for where in dirty if where.startswith(assembler.SITE_INDEX_FILE)]
    assert hits, "the control is dead: nothing recoverable in the bundle's index.json"
    assert len(hits) >= 2, hits  # more than one grid, so not one lucky match

    # Control 2 — the sweep reads BOTH served listings. The plant is one
    # title per entry, which is exactly what a schema that admitted the field
    # would have produced.
    named = {key: name for name, key in keys.items()}
    planted = tmp_path / "planted"
    for where in listings:
        payload = json.loads((report.site_dir / where).read_text(encoding="utf-8"))
        for entry in payload["puzzles"]:
            entry["title"] = _leaky_title(PAGE_GRIDS[named[entry["key"]]])
        target = planted / where
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    found = sweep_tree(planted, PAGE_GRIDS)
    assert {where.split(" [")[0] for where in found} == set(listings), found

    # And the site itself, unplanted, is clean.
    assert sweep_tree(report.site_dir, PAGE_GRIDS) == {}

    # And the puzzle title really is a declared field of both bundle files,
    # so this is not a defence against a field nobody writes.
    assert "title" in player_bundle.INDEX_ENTRY_FIELDS
    assert "title" in player_bundle.BOOK_FILE_FIELDS
    assert "title" not in assembler.SERVED_SCHEMA
    assert "title" not in assembler.SERVED_ENTRY_SCHEMA
    # Every entry of every served listing, in BOTH files, carries exactly the
    # entry schema — so no picture name travels inside a book file either,
    # which is the one place a reader might expect the exemption to reach.
    for where in (f"{assembler.SITE_INDEX_FILE}", f"book/{slug}.json"):
        payload = json.loads((report.site_dir / where).read_text(encoding="utf-8"))
        assert payload["puzzles"], where
        for entry in payload["puzzles"]:
            assert sorted(entry) == sorted(assembler.SERVED_ENTRY_SCHEMA), (where, entry)
    # The library index carries no title at ALL, book or picture: there is no
    # book for it to be the title of.
    index = json.loads((report.site_dir / assembler.SITE_INDEX_FILE).read_text(encoding="utf-8"))
    assert sorted(index) == sorted(assembler.SERVED_INDEX_SCHEMA)
    assert "title" not in index


def test_the_book_title_exemption_is_scoped_and_its_cost_is_measured(tmp_path) -> None:
    """The owner's 2026-10-28 exemption: what it serves, and what it costs.

    ADR-0039/R3 makes an exemption a claim that carries a control for what it
    must NOT absorb. Four halves, and the last two are the ones an exemption
    usually ships without:

    #. **it serves.** The bundle's book title reaches the served file, with
       whitespace collapsed, and the served value is written out here rather
       than recomputed with ``_book_title``;
    #. **it is bounded in scope.** A title moved to a puzzle file or to the
       library index is REFUSED by ``check_listing_capacity`` — so the
       picture name EC-048 forbids cannot ride in on the book's exemption,
       mechanically rather than by everyone remembering the distinction. Both
       directions: refused with the name in the wrong schema, accepted with
       it back where the decision put it;
    #. **it is bounded in length**, and that bound is NOT a capacity bound.
       A 240-character title is truncated to ``SERVED_TITLE_MAX_CHARS`` and
       the truncation is reported in ``narrowed``;
    #. **it costs what it costs, measured in a second domain.** The
       arithmetic is ``book_title_residual_bits()`` = 2410.18 bits. The
       measurement is in CELLS: a book named after the base-64 of one of its
       puzzles' answers publishes that answer, and the sweep recovers it off
       the served tree. That is the residual, demonstrated rather than
       argued, and the one thing the owner was told the decision buys.
    """
    # 1 — it serves, and the collapsing is the function's.
    root = tmp_path / "bundle"
    keys, slug = write_pages_bundle(root, order=BOOK_ORDER)
    clean = assembler.assemble(root, tmp_path / "clean")
    served = json.loads(
        (clean.site_dir / "book" / f"{slug}.json").read_text(encoding="utf-8")
    )
    assert sorted(served) == sorted(assembler.SERVED_BOOK_SCHEMA)
    assert served["title"] == BOOK_TITLE_SERVED
    assert BOOK_TITLE != BOOK_TITLE_SERVED, "the fixture exercises no collapsing"
    assert clean.narrowed == (), clean.narrowed
    # The page's own cap is the assembler's, read off the shipped bytes.
    assert _js_constant("TITLE_MAX_CHARS") == assembler.SERVED_TITLE_MAX_CHARS

    # 2 — the scope, both directions. The exemption is for ONE schema.
    assert assembler.EXEMPT_LISTING_FIELDS == ("title",)
    assert assembler.check_listing_capacity() is None
    for schema in ("SERVED_ENTRY_SCHEMA", "SERVED_INDEX_SCHEMA", "SERVED_SCHEMA"):
        original = getattr(assembler, schema)
        try:
            setattr(assembler, schema, (*original, "title"))
            # "scoped", not "scoped or not partitioned": none of these three
            # edits changes what the listings CARRY (the entry schema is
            # derived at import, and `title` is already carried by the book
            # file), so the scope refusal is the only one that can fire and
            # the match says so. A looser pattern would let the partition
            # message pass for the scope control.
            with pytest.raises(ValueError, match="is scoped"):
                assembler.check_listing_capacity()
        finally:
            setattr(assembler, schema, original)
        assert getattr(assembler, schema) == original, schema
    assert assembler.check_listing_capacity() is None

    # 3 — the length bound, and it is reported rather than silent.
    long_root = tmp_path / "long"
    _, long_slug = write_pages_bundle(
        long_root, order=BOOK_ORDER, book_title="z" * (assembler.SERVED_TITLE_MAX_CHARS * 2)
    )
    long_site = assembler.assemble(long_root, tmp_path / "long-site")
    long_served = json.loads(
        (long_site.site_dir / "book" / f"{long_slug}.json").read_text(encoding="utf-8")
    )
    assert long_served["title"] == "z" * assembler.SERVED_TITLE_MAX_CHARS
    assert long_site.narrowed == ((long_slug, "title"),), long_site.narrowed

    # 4 — the cost, in the second domain. Arithmetic first.
    #
    # The character space is recomputed here in a DIFFERENT domain from the
    # subtraction ``assemble.py`` does: the surrogate block is excluded
    # because those code points are not characters, which is measured by
    # trying to encode one rather than by trusting the number 2048. The fix
    # round's own kill instrument is why this paragraph exists — the first
    # version asserted only ``round(bits, 2) == 2410.18``, and a mutant that
    # moved TITLE_CODE_POINTS by ONE code point SURVIVED it, because one code
    # point out of a million is four decimal places below that rounding.
    surrogates = [point for point in range(0x110000) if 0xD800 <= point <= 0xDFFF]
    assert len(surrogates) == 2048
    for point in (0xD800, 0xDFFF):
        with pytest.raises(UnicodeEncodeError):
            chr(point).encode("utf-8")
    assert chr(0xD7FF).encode("utf-8") and chr(0xE000).encode("utf-8")
    assert assembler.TITLE_CODE_POINTS == 0x110000 - len(surrogates) == 1112064

    bits = assembler.book_title_residual_bits()
    assert bits > assembler.CAPACITY_CEILING_BITS, bits
    assert bits > MAX_SIZE * MAX_SIZE, (bits, MAX_SIZE * MAX_SIZE)
    assert round(bits, 2) == 2410.18, bits
    assert bits == assembler.SERVED_TITLE_MAX_CHARS * math.log2(
        0x110000 - len(surrogates)
    ), bits
    # Then cells. MIN_SIZE x MIN_SIZE is 100 cells; its base-64 is 20
    # characters, well inside the cap, so the whole grid comes back.
    leak = _leaky_title(PAGE_GRIDS["e10"])
    assert len(leak) <= assembler.SERVED_TITLE_MAX_CHARS, len(leak)
    leaky_root = tmp_path / "leaky"
    _, leaky_slug = write_pages_bundle(leaky_root, order=BOOK_ORDER, book_title=leak)
    leaky_site = assembler.assemble(leaky_root, tmp_path / "leaky-site")
    recovered = sweep_tree(leaky_site.site_dir, PAGE_GRIDS)
    assert sorted(recovered) == [f"book/{leaky_slug}.json [e10]"], recovered
    # The residual is the BOOK FILE's and only the book file's: the puzzle
    # files and the library index stay clean under the same plant, which is
    # what "bounded in scope" means in the tree rather than in the schema.
    assert not [where for where in recovered if where.startswith("puzzle/")]
    assert not [where for where in recovered if where.startswith("index.json")]
    # And the control for the sweep itself: with the editorial title, the
    # same tree is clean, so the hit above is the title and not the tree.
    assert sweep_tree(clean.site_dir, PAGE_GRIDS) == {}


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
    established: the partition holds today, a served listing field in no
    bucket is refused, and ``assemble`` refuses outright rather than merely
    having the function available (without the third half the call site could
    be deleted and the first two would stay green).

    CARD-284's fix round added a third bucket — the book title's exemption —
    so the partition is over three sets now, and "in more than one" has to be
    refused across all three rather than only between the first two: a set
    union would not notice a name counted twice.

    **Which test holds which of the exemption's two refusals, measured
    rather than cross-referenced.** Fix round 1's version of this docstring
    sent a reader to
    ``test_the_book_title_exemption_is_scoped_and_its_cost_is_measured``
    for both, and cycle 2 ran each refusal's deletion as its own pytest
    invocation (its C2-M01 and C2-M03): deleting the LIVENESS refusal reds
    only this test, and deleting the SCOPE refusal reds only that one. So
    scope is the exemption test's and **liveness is this test's own** — the
    closing ``no served schema carries`` block below, twenty lines down.
    Named here because "attribute by test, not by file" is a rule this board
    pays for when a pointer lands on a test that does not red.
    """
    assert assembler.check_listing_capacity() is None
    carried = (
        set(assembler.SERVED_INDEX_SCHEMA)
        | set(assembler.SERVED_BOOK_SCHEMA)
        | set(assembler.SERVED_ENTRY_SCHEMA)
    )
    buckets = (
        assembler.MIRRORED_FROM_PUZZLE_FILE,
        assembler.LISTING_STRUCTURE_FIELDS,
        assembler.EXEMPT_LISTING_FIELDS,
    )
    assert carried == {name for bucket in buckets for name in bucket}
    assert len(buckets) == 3
    for name in carried:
        assert sum(name in bucket for bucket in buckets) == 1, name
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

    # And a name in TWO buckets is refused too — "accounted twice" is not
    # accounted, and set union alone would not notice it. Fired for each
    # unordered pair of the three buckets, so a check written for only the
    # first two cannot pass this.
    pairs = {
        ("structural", "mirrored"): ("LISTING_STRUCTURE_FIELDS", "tier"),
        ("exempt", "structural"): ("EXEMPT_LISTING_FIELDS", "slug"),
        ("exempt", "mirrored"): ("MIRRORED_FROM_PUZZLE_FILE", "title"),
    }
    for where, (attribute, name) in pairs.items():
        monkeypatch.setattr(
            assembler, attribute, (*getattr(assembler, attribute), name)
        )
        with pytest.raises(ValueError, match="not partitioned"):
            assembler.check_listing_capacity()
        monkeypatch.undo()
        assert assembler.check_listing_capacity() is None, where
    assert len(pairs) == 3

    # An exemption for a field nothing serves is refused as well: ADR-0039/R3
    # holds an exemption to an equality against the sites that exist, and a
    # dead exemption is a claim nothing can check.
    monkeypatch.setattr(assembler, "SERVED_BOOK_SCHEMA", ("puzzles", "slug"))
    with pytest.raises(ValueError, match="no served schema carries"):
        assembler.check_listing_capacity()
    monkeypatch.undo()
    assert assembler.check_listing_capacity() is None


def test_the_served_index_is_key_sorted(pages_site) -> None:
    """``served_index``'s determinism claim, which had no control in cycle 1.

    Its docstring says the bytes are a function of the published SET and not
    of the walk order. Cycle 1 of this card's review measured that unheld:
    reversing the sort survived 51 nodes, because every AC-389 assertion
    wraps the rendered keys in ``sorted`` and
    ``test_the_static_half_of_the_site_does_not_vary_with_the_puzzles``
    excludes ``index.json`` from its byte comparison by design.

    Two shapes, so it is not one assertion's problem: the function's own
    output over an input in deliberately NON-sorted order, and the served
    file on disk. The book file is the control in the same test — its order
    is the BOOK's and must NOT be sorted, so a change that sorted everything
    reds here too.
    """
    report, keys, slug = pages_site
    # The function, over an input whose iteration order is the reverse.
    entries = {
        key: {"key": key, "width": MIN_SIZE, "height": MIN_SIZE, "tier": "easy"}
        for key in sorted(keys.values(), reverse=True)
    }
    assert list(entries) != sorted(entries), "the input is already sorted"
    assert [entry["key"] for entry in assembler.served_index(entries)["puzzles"]] == sorted(
        entries
    )

    # The file on disk.
    index = json.loads((report.site_dir / assembler.SITE_INDEX_FILE).read_text(encoding="utf-8"))
    listed = [entry["key"] for entry in index["puzzles"]]
    assert listed == sorted(keys.values())
    assert len(listed) == len(PAGE_GRIDS)

    # The control, in the same test: the BOOK's order is the book's, so a
    # rule that sorted every listing would be wrong rather than harmless.
    book = json.loads(
        (report.site_dir / "book" / f"{slug}.json").read_text(encoding="utf-8")
    )
    ordered = [entry["key"] for entry in book["puzzles"]]
    assert ordered == [keys[name] for name in BOOK_ORDER]
    assert ordered != sorted(ordered), "the fixture's book order is the sorted one"


def test_two_assemble_runs_are_byte_identical(tmp_path) -> None:
    """EC-049's shape one layer out, WITHIN one interpreter.

    An export's bytes are a function of the store (EC-049) so that a bundle
    diff is meaningful; nothing said the same of the assembled SITE, and
    cycle 1 of this card's review filed that as the collateral of F-004. So
    the same bundle assembled into two directories gives two trees equal
    file for file, name for name, byte for byte.

    **What this does NOT claim, because fix round 1 claimed it and cycle 2
    measured the gap:** this is not "EC-049's property at the layer that
    actually deploys". Both assembles run in ONE process, and a deploy diff
    is taken across two invocations. Cycle 2's C2-M28 is the case that tells
    them apart — ``sorted(entries)`` replaced by an order that is stable
    within a process and varies with ``PYTHONHASHSEED`` between them — and it
    SURVIVES this test. It is killed by
    ``test_the_served_index_is_key_sorted``, which therefore owns the
    cross-process half, and the two tests are a pair rather than a
    duplicate. What this test does hold, measured by C2-M27 (the marker text
    made to vary per call), is within-process variation of any served byte.

    Deliberately NOT a re-run of the same method: the first tree's walk is
    compared against the second's, and then one byte is planted ON DISK and
    the tree RE-WALKED, so the control exercises the same reader the claim
    does rather than mutating a dict the line above already read.
    """
    root = tmp_path / "bundle"
    write_pages_bundle(root, order=BOOK_ORDER)

    def tree(site):
        return {
            path.relative_to(site).as_posix(): path.read_bytes()
            for path in sorted(site.rglob("*"))
            if path.is_file()
        }

    one = tree(assembler.assemble(root, tmp_path / "one").site_dir)
    two = tree(assembler.assemble(root, tmp_path / "two").site_dir)
    assert one == two
    # Every data file the bundle feeds is in the comparison, which is what
    # cycle 1's F-004 found excluded one layer in.
    assert assembler.SITE_INDEX_FILE in one
    assert len([name for name in one if name.startswith("puzzle/")]) == len(PAGE_GRIDS)
    assert len([name for name in one if name.startswith("book/")]) == 1
    assert len(one) >= len(assembler.PLAYER_FILES) + len(PAGE_GRIDS) + 2

    # The control, through the reader rather than beside it: one byte
    # appended to the index ON DISK, the tree walked again by `tree`.
    index = tmp_path / "two" / assembler.SITE_INDEX_FILE
    index.write_bytes(index.read_bytes() + b" ")
    assert tree(tmp_path / "two") != one, (
        "the comparison would not notice a changed index"
    )


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
    # Served with its title and an empty list: the slug is printed on paper,
    # so the page exists and says whose book it is even with nothing in it.
    assert book == {"slug": slug, "title": BOOK_TITLE_SERVED, "puzzles": []}
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


def test_the_public_tile_is_registered_in_the_design_inventory() -> None:
    """The card's Design context asks for it, so it is held rather than hoped.

    ``meta/design/components.md`` is the panel's inventory and now carries
    one public-player section as well; cycle 1 of this card's review found
    the obligation undeclared and unmet (F-009), and the existing
    ``## PuzzleTile`` there is the ADMIN panel's book-selection tile, not
    this one. Both of those are asserted, because "a section exists" would
    pass on the admin entry.

    Completeness rather than presence, and derived from an authority the
    runtime can enumerate (ADR-0039/R2): every ``data-pages-*`` hook the two
    shipped documents actually use has to be named in the inventory, so a
    part added to the markup and not written down reds here. The control
    plants one hook the inventory cannot know about.
    """
    inventory = (REPO_ROOT / "meta/design/components.md").read_text(encoding="utf-8")
    assert "## Public player listing tile — PagesTile (CARD-284)" in inventory
    # Not the admin panel's tile: that section is still there and is a
    # different component, which is the confusion the finding names.
    assert "## PuzzleTile" in inventory
    admin = inventory.split("## PuzzleTile", 1)[1].split("\n## ", 1)[0]
    assert "book puzzle selection" in admin
    assert "data-pages" not in admin

    hooks = set()
    for name in ("book.html", "library.html"):
        page = (PLAYER_DIR / name).read_text(encoding="utf-8")
        hooks |= set(re.findall(r"(data-pages-[a-z-]+)", page))
    assert len(hooks) >= 10, sorted(hooks)

    def named(hook: str, text: str = inventory) -> bool:
        """Whether ``text`` names ``hook`` — at a word boundary.

        A plain ``in`` is what fix round 1's first version used and that
        round's own kill instrument SURVIVED it: renaming the inventory's
        ``data-pages-loading`` to ``data-pages-loadingx`` left the real hook
        a substring of the wrong one, so the drift guard read the typo as the
        thing it was looking for. ``data-pages-filter`` really is a prefix of
        ``data-pages-filters``, both are hooks, and both are named — so the
        boundary has to admit ``=`` and ``]`` and refuse a further letter.

        ``text`` is a parameter, and that is cycle 2's finding rather than a
        convenience. Fix round 1 wrote the sentence above with two controls
        that re-derived the same regex INLINE and never called this function,
        so reverting the boundary to ``hook in text`` left the test green
        (cycle 2's C2-M25) — and so did reverting it together with a typo on
        any hook the test does not spell out as a literal (C2-M25b). The
        controls below go through this function, over an inventory built
        here, which is the only shape a boundary claim can be held in.
        """
        return re.search(rf"{re.escape(hook)}(?![a-z-])", text) is not None

    missing = sorted(hook for hook in hooks if not named(hook))
    assert missing == [], missing

    # The boundary itself, THROUGH `named`, over inventories written here.
    # `in` passes the first of these and fails the second and third, which is
    # what makes them a control for the boundary rather than for the hook.
    assert not named("data-pages-nowhere")
    assert not named("data-pages-count", "a tile has [data-pages-countx] on it")
    assert named("data-pages-count", "a tile has [data-pages-count] on it")
    assert named("data-pages-count", "written as data-pages-count=\"3\" here")
    # And the genuine prefix pair the docstring cites, also through `named`:
    # a boundary that refused `s` would be wrong, not merely strict.
    assert {"data-pages-filter", "data-pages-filters"} <= hooks, sorted(hooks)
    assert named("data-pages-filter") and named("data-pages-filters")
    # The real document, in both directions, for the hook M24 was found on.
    assert "data-pages-loading" in hooks
    assert named("data-pages-loading")
    assert not named("data-pages-loadingx")


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
