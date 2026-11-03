"""CARD-332 — the panel learns the player's domain (owner, 2026-10-30).

    AC-1  Print setup stores a player domain with the book's print setup and
          shows it on return; a value that is not an absolute https:// origin
          re-renders with the field marked invalid and stores nothing
          (TestPlayerDomain_PrintSetupStoresTheBase,
           TestPlayerDomain_ARefusalStoresNothing)
    AC-2  the arrangement page shows `{base}/play/{key}` beside each puzzle,
          whose key is `player_bundle.puzzle_key` of that puzzle's stored grid
          (TestPlayerDomain_TheArrangementPageShowsTheRealLink)
    AC-3  a book with no stored domain says so, links to Print setup, and
          renders no URL built from a missing base
          (TestPlayerDomain_ABookWithNoDomainSaysSo)
    AC-4  no puzzle title, grid or solution cell reaches any link, attribute
          or copy target on that page
          (TestPlayerDomain_NothingButTheKeyReachesTheLink)
    EC    the key is computed through ADR-0041/R1's one implementation, for
          every puzzle, on every render; no second spelling of the recipe
          lives in `admin/` or in a template
          (TestPlayerDomain_OneRecipe)

**How the expected key is produced here, and why that matters.** Every
assertion about a rendered URL compares it against a key this file computes
**by hand from ADR-0041/R1's words** (:func:`key_by_hand`) — SHA-256 over
``"{width}x{height}:"`` and the cells in row-major order, truncated to ten hex
characters. It never calls :func:`~nonogram.admin.player_bundle.puzzle_key`,
because a test that derives its expectation from the function under test
agrees with that function however wrong both are. The one thing it does read
from the module is :data:`~nonogram.admin.player_bundle.KEY_LENGTH`, and only
to **assert** it is still ten: a change to the recipe's length must red this
file rather than be followed by it (R1 makes such a change breaking for every
printed book).

**The AC-4 control is a whitelist, not a leak scan.** CARD-282's own lesson
(see ``tests/test_player_bundle.py``'s header: a denylist of "leak shapes"
shipped green past a real leak) is that a guard searching for byte shapes the
writer could not emit proves nothing. So :func:`link_tokens` enumerates
**every** attribute value and text node the rendered link fragment actually
carries, and the test holds that set to an inventory it states: a token no
source claims is a failure, whatever it looks like. Its own ability to fail is
measured, not assumed — ``test_the_inventory_rejects_a_planted_title`` plants
the puzzle's title into a fragment of the same shape and watches the same
check fire.
"""

from __future__ import annotations

import hashlib
import html.parser
import random
import re

import pytest

from nonogram.admin.player_bundle import KEY_LENGTH
from nonogram.admin.print_specs import (
    PLAYER_DOMAIN_COLUMN,
    PrintSpecValidator,
    stored_player_domain,
)
from nonogram.clues import compute_clues

# The real panel in both storage modes, with a book store and a client on it.
from tests.test_book_arrange_size_filter import Panel, panel  # noqa: F401
from tests.test_book_plan_storage import AC198_MATRIX, _form, _input_value

#: ADR-0041/R1's base, as the owner wrote it in the request this card came
#: from. A literal, because it is the owner's value and not the code's.
BASE = "https://nonogram.adverax.io"

#: R1's truncation, transcribed from the ADR rather than imported, so the two
#: can be compared instead of agreeing by construction.
R1_KEY_LENGTH = 10


def key_by_hand(grid) -> str:
    """``grid``'s key, spelled out from ADR-0041/R1 rather than imported.

    The second implementation every expectation in this file is built from.
    """
    cells = "".join("1" if cell else "0" for row in grid for cell in row)
    text = f"{len(grid[0])}x{len(grid)}:{cells}"
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:R1_KEY_LENGTH]


def test_the_recipe_this_file_checks_against_is_still_the_shipped_one() -> None:
    """R1's length, from the two places that must agree about it."""
    assert KEY_LENGTH == R1_KEY_LENGTH


# --------------------------------------------------------------------------
# Books with grids of our own choosing
# --------------------------------------------------------------------------

#: Three distinct grids, so a route that keyed the wrong row — or keyed one
#: row and reused it — cannot pass. Each is its own picture, and no two share
#: an extent *and* a pattern.
GRIDS = {
    "angel": [
        [True, False, True],
        [False, True, False],
        [True, True, True],
    ],
    "star": [
        [False, True, False, True],
        [True, True, True, True],
        [False, True, False, True],
    ],
    "box": [
        [True, True],
        [True, True],
    ],
}


def add_grid(panel, grid, name, tier="easy") -> str:  # noqa: F811
    """One approved puzzle holding exactly ``grid``, named ``name``."""
    clues = compute_clues([[bool(cell) for cell in row] for row in grid])
    puzzle_id = panel.store.add_puzzle(
        grid=[[bool(cell) for cell in row] for row in grid],
        clues_rows=[list(clue) for clue in clues.rows],
        clues_cols=[list(clue) for clue in clues.columns],
        width=len(grid[0]),
        height=len(grid),
        theme="generic",
        difficulty_score=10,
        difficulty_tier=tier,
        quality_score=50,
        recognizability="medium",
        strategies_used=[],
        batch_id=None,
        source_image=f"{name}.png",
    )
    panel.store.approve_puzzle(puzzle_id)
    return puzzle_id


def book_of_grids(panel, names=("angel", "star", "box")) -> tuple:  # noqa: F811
    """A book holding one puzzle per named grid, in that order."""
    book_id = panel.books.create_book("Winter", "a book", "christmas", "adults")
    ids = [add_grid(panel, GRIDS[name], name) for name in names]
    panel.books.add_puzzles_to_book(book_id, ids)
    return book_id, ids


def set_domain(panel, book_id, domain) -> None:  # noqa: F811
    """Store ``domain`` on the book through the real Print setup route."""
    form = _form(150, (40, 40, 20), AC198_MATRIX)
    form["player_domain"] = domain
    response = panel.client.post(f"/book/{book_id}/setup-print", data=form)
    assert response.status_code == 302, response.get_data(as_text=True)[:400]


def setup_page(panel, book_id) -> str:  # noqa: F811
    response = panel.client.get(f"/book/{book_id}/setup-print")
    assert response.status_code == 200
    return response.get_data(as_text=True)


# --------------------------------------------------------------------------
# Reading the rendered arrangement page
# --------------------------------------------------------------------------

#: One rendered reader link, from `<div class="play-link ...">` to its close.
_PLAY_LINK = re.compile(r'<div class="play-link[^"]*">.*?</div>', re.S)


def play_links(markup: str) -> list[str]:
    """Every reader-link fragment on the page, in document order.

    **The fragment must contain no nested ``<div>``.** :data:`_PLAY_LINK` is
    non-greedy, so a nested element's ``</div>`` would end the match early and
    everything after it — a leak included — would be invisible to
    :func:`unexpected_in_link` (cycle 1, F-005). The shape fails loudly rather
    than silently today: :func:`shown_urls` would find no ``<code
    class="play-url">`` inside the truncated fragment and raise, reddening
    every AC-2 cell. Keep the link flat, or parse it with :class:`_Tokens`
    below instead of with the regex — do not "fix" ``shown_urls`` to tolerate
    a truncated fragment, which would leave the whitelist blind.
    """
    return _PLAY_LINK.findall(markup)


def shown_urls(markup: str) -> list[str]:
    """The URL each reader link shows, in document order."""
    return [
        re.search(r"<code class=\"play-url\">([^<]*)</code>", fragment).group(1)
        for fragment in play_links(markup)
    ]


class _Tokens(html.parser.HTMLParser):
    """Every attribute value and text node in a fragment, in document order."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.found: list[str] = []

    def handle_starttag(self, tag, attrs) -> None:
        self.found.append(tag)
        for name, value in attrs:
            self.found.append(name)
            if value is not None:
                self.found.append(value)

    def handle_data(self, data) -> None:
        if data.strip():
            self.found.append(data.strip())


def link_tokens(fragment: str) -> list[str]:
    """Everything ``fragment`` carries: tag names, attribute names and values, text.

    Deliberately **everything**, including class names — a whitelist that
    skipped an attribute because puzzle data "would not be put there" is the
    denylist CARD-282 already paid for. A stylesheet change that renames a
    class reds the test using this, and the fix is to state the new name.
    """
    parser = _Tokens()
    parser.feed(fragment)
    parser.close()
    return parser.found


def inventory(url: str, order: int) -> set[str]:
    """What a reader link is allowed to carry, stated in full.

    The URL, the order number the accessible names count with, and the fixed
    vocabulary of the markup. Nothing about the puzzle but its place in the
    book and the one-way key inside the URL.
    """
    return {
        "div",
        "span",
        "code",
        "button",
        "class",
        "type",
        "onclick",
        "aria-label",
        "title",
        "role",
        "aria-live",
        "status",
        "polite",
        # The three class attributes the link's markup carries, restated at
        # the merge gate when F-203 moved the live region off the URL's flex
        # line: ``.play-link`` became a plain block, the flex line moved into
        # a ``.play-link-row`` child, and the region gained ``d-block``. This
        # is the rename this helper's own docstring promises will red here,
        # and stating the new names is the whole of the fix — the four cells
        # that caught it are AC-4's leakage check doing its job.
        "play-copy-said text-muted d-block",
        "play-link small",
        "play-link-row d-flex align-items-center gap-2",
        "visually-hidden",
        "play-url",
        "btn btn-sm btn-outline-secondary",
        "button",
        "copyPlayUrl(this)",
        f"Reader link for puzzle {order}",
        f"Copy the reader link for puzzle {order}",
        "Copy this link",
        "Copy",
        url,
    }


def unexpected_in_link(fragment: str, url: str, order: int) -> list[str]:
    """Tokens in ``fragment`` that no source claims — AC-4's verdict."""
    allowed = inventory(url, order)
    return [token for token in link_tokens(fragment) if token not in allowed]


# --------------------------------------------------------------------------
# AC-1 — the field, stored and shown
# --------------------------------------------------------------------------


class TestPlayerDomain_PrintSetupStoresTheBase:
    """AC-1's first half, through the real route in both storage modes."""

    def test_a_new_book_has_no_domain_and_an_empty_field(self, panel) -> None:  # noqa: F811
        book_id, _ = book_of_grids(panel)

        html_text = setup_page(panel, book_id)

        assert _input_value(html_text, "player_domain") == ""
        assert stored_player_domain(panel.books.get_book(book_id)) is None

    def test_a_submitted_domain_is_stored_and_shown_on_return(self, panel) -> None:  # noqa: F811
        book_id, _ = book_of_grids(panel)

        set_domain(panel, book_id, BASE)

        assert stored_player_domain(panel.books.get_book(book_id)) == BASE
        assert _input_value(setup_page(panel, book_id), "player_domain") == BASE

    def test_one_domain_has_one_stored_spelling(self, panel) -> None:  # noqa: F811
        """A trailing slash and a shouted host are the same base, stored once.

        The column is joined to ``/play/<key>``, so two spellings would make
        two different printed URLs for one domain.
        """
        book_id, _ = book_of_grids(panel)

        set_domain(panel, book_id, "HTTPS://Nonogram.Adverax.IO/")

        assert stored_player_domain(panel.books.get_book(book_id)) == BASE

    def test_clearing_the_field_removes_the_stored_domain(self, panel) -> None:  # noqa: F811
        book_id, _ = book_of_grids(panel)
        set_domain(panel, book_id, BASE)

        set_domain(panel, book_id, "")

        assert stored_player_domain(panel.books.get_book(book_id)) is None

    def test_a_submission_without_the_field_leaves_the_stored_base_alone(
        self, panel  # noqa: F811
    ) -> None:
        """The older-client case, driven from a base that is SET.

        This is the state the defect is visible in. A text input always posts
        its name, so the field's presence is its own marker — but a route that
        read ``request.form.get("player_domain")`` and stored the result would
        read a missing field as ``None``, which is the value "cleared" writes,
        and the first save from any form that does not carry this control
        would silently wipe the base a printed run depends on.

        Driven from "no base" this cell could not fail: absent and cleared
        both leave NULL. Driven from a stored base, the two readings differ.
        """
        book_id, _ = book_of_grids(panel)
        set_domain(panel, book_id, BASE)

        # A submission with every other Print setup field and no domain at all.
        response = panel.client.post(
            f"/book/{book_id}/setup-print", data=_form(150, (40, 40, 20), AC198_MATRIX)
        )

        assert response.status_code == 302
        assert stored_player_domain(panel.books.get_book(book_id)) == BASE


class TestPlayerDomain_ARefusalStoresNothing:
    """AC-1's second half: refused, marked, and nothing written."""

    #: Each one is wrong in its own way: the scheme, a path, a bare host, a
    #: space, a credential, no host at all.
    REFUSED = [
        "http://nonogram.adverax.io",
        "https://nonogram.adverax.io/play",
        "nonogram.adverax.io",
        "https://nonogram adverax.io",
        "https://user:pass@nonogram.adverax.io",
        "https://",
    ]

    @pytest.mark.parametrize("entry", REFUSED)
    def test_a_refused_entry_stores_nothing_and_marks_the_field(
        self, panel, entry  # noqa: F811
    ) -> None:
        book_id, _ = book_of_grids(panel)
        set_domain(panel, book_id, BASE)
        before = panel.books.get_book(book_id)

        form = _form(150, (40, 40, 20), AC198_MATRIX, width="20.32", height="25.40")
        form["player_domain"] = entry
        response = panel.client.post(f"/book/{book_id}/setup-print", data=form)
        page = response.get_data(as_text=True)

        # Re-rendered, not redirected: the owner is still on the form.
        assert response.status_code == 200
        # Nothing stored — not the domain, and not the trim beside it, which
        # this submission also changed.
        after = panel.books.get_book(book_id)
        assert stored_player_domain(after) == BASE
        assert (after.trim_width_cm, after.trim_height_cm) == (
            before.trim_width_cm,
            before.trim_height_cm,
        )
        # Marked, by the pattern the plan fields established.
        tag = re.search(r'<input\b[^>]*\bid="player_domain"[^>]*>', page, re.S)
        assert tag, "no player-domain field on the re-rendered page"
        assert "is-invalid" in tag.group(0)
        assert 'aria-invalid="true"' in tag.group(0)
        assert 'id="player-domain-error"' in page
        # And carrying the owner's own entry back, so it can be corrected.
        assert _input_value(page, "player_domain") == entry

    def test_a_refused_domain_beside_a_good_plan_marks_only_its_own_field(
        self, panel  # noqa: F811
    ) -> None:
        """One refusal marks one box: the plan's inputs are untouched."""
        book_id, _ = book_of_grids(panel)

        form = _form(150, (40, 40, 20), AC198_MATRIX)
        form["player_domain"] = "ftp://nonogram.adverax.io"
        page = panel.client.post(
            f"/book/{book_id}/setup-print", data=form
        ).get_data(as_text=True)

        assert "is-invalid" in re.search(
            r'<input\b[^>]*\bid="player_domain"[^>]*>', page, re.S
        ).group(0)
        assert "is-invalid" not in re.search(
            r'<input\b[^>]*\bid="plan_count"[^>]*>', page, re.S
        ).group(0)
        assert 'id="plan-error"' not in page


# --------------------------------------------------------------------------
# The validator, over a corpus whose verdict is known by construction
# --------------------------------------------------------------------------


#: The corpus is composed from these three enumerated axes, each part carrying
#: the verdict it forces. The expectation is therefore produced by the
#: *generator*, not by the function under test — and the minimum case count
#: below is this product, so the corpus cannot silently shrink.
SCHEMES = [
    ("https://", True),
    ("HTTPS://", True),
    ("http://", False),
    ("ftp://", False),
    ("//", False),
    ("", False),
]

HOSTS = [
    ("nonogram.adverax.io", True),
    ("Nonogram.Adverax.IO", True),
    ("localhost", True),
    ("a.b.c.d.example", True),
    ("", False),
    ("-leading.io", False),
    ("trailing-.io", False),
    ("two..dots.io", False),
    ("has space.io", False),
    ("user:pass@host.io", False),
]

TAILS = [
    ("", True),
    ("/", True),
    (":8443", True),
    # The bound itself, from both sides, and the lowest port there is: an
    # off-by-one in ``1 <= port <= _MAX_PORT`` is a one-character edit that
    # ":0" and ":99999" alone would not have caught (cycle 1, F-008).
    (":1", True),
    (":65535", True),
    (":65536", False),
    (":0", False),
    (":99999", False),
    (":", False),
    ("/play", False),
    ("/play/073280edd0", False),
    ("?q=1", False),
    ("#top", False),
]

#: Every composition of the three axes, less the one that composes to nothing
#: at all. The minimum is this product rather than a figure typed under it, so
#: the corpus cannot silently shrink; the subtraction is *measured* by
#: :func:`corpus`, not taken on trust.
CORPUS_MINIMUM = len(SCHEMES) * len(HOSTS) * len(TAILS) - 1


def corpus(seed: int = 332):
    """Every (text, expected) composition, shuffled by a seeded Random.

    **One composition is dropped, and it is counted on the way out.** The
    empty scheme, the empty host and the empty tail compose to ``""``, which
    is not a refusal and never was: a blank field is "the owner cleared it",
    one of the two blank states the *route* tells apart (see
    ``test_blank_and_absent_are_not_refusals``). Grading it as invalid would
    be the generator asserting something the domain does not say. The
    assertion below is what keeps that exclusion from widening into a hole:
    exactly one composition may be blank.
    """
    built = [
        (f"{scheme}{host}{tail}", scheme_ok and host_ok and tail_ok)
        for scheme, scheme_ok in SCHEMES
        for host, host_ok in HOSTS
        for tail, tail_ok in TAILS
    ]
    cases = [(text, expected) for text, expected in built if text.strip()]
    assert len(built) - len(cases) == 1, "more than the blank composition was dropped"
    random.Random(seed).shuffle(cases)
    return cases


class TestPlayerDomain_TheValidatorAgreesWithItsConstruction:
    """The pure domain function, graded by how each case was built."""

    def test_every_composition_gets_the_verdict_it_was_built_with(self) -> None:
        cases = corpus()

        assert len(cases) >= CORPUS_MINIMUM, len(cases)
        # Both verdicts are really in it: a corpus of one answer grades nothing.
        assert sum(1 for _, ok in cases if ok) >= len(SCHEMES)
        assert sum(1 for _, ok in cases if not ok) >= len(SCHEMES)

        disagreed = [
            (text, expected, PrintSpecValidator.validate_player_domain(text))
            for text, expected in cases
            if PrintSpecValidator.validate_player_domain(text)[0] is not expected
        ]
        assert disagreed == [], disagreed[:10]

    def test_every_refusal_says_what_was_wrong(self) -> None:
        """A refusal with no message is a red border and nothing to read."""
        empty = [
            text
            for text, expected in corpus()
            if not expected
            and not (PrintSpecValidator.validate_player_domain(text)[1] or "").strip()
        ]
        assert empty == []

    def test_blank_and_absent_are_not_refusals(self) -> None:
        """They are the two states the ROUTE tells apart, not the validator."""
        for value in (None, "", "   "):
            assert PrintSpecValidator.validate_player_domain(value) == (True, None)


# --------------------------------------------------------------------------
# AC-2 — the real link beside each puzzle
# --------------------------------------------------------------------------


class TestPlayerDomain_TheArrangementPageShowsTheRealLink:
    """AC-2, against keys this file computes from ADR-0041/R1's words."""

    def test_each_puzzle_shows_base_play_key_of_its_own_grid(self, panel) -> None:  # noqa: F811
        names = ("angel", "star", "box")
        book_id, _ = book_of_grids(panel, names)
        set_domain(panel, book_id, BASE)

        markup = panel.page(book_id)

        expected = [f"{BASE}/play/{key_by_hand(GRIDS[name])}" for name in names]
        assert shown_urls(markup) == expected
        # Three distinct pictures, three distinct keys: a route that keyed one
        # row and reused it would pass an "all links present" check.
        assert len(set(expected)) == len(names)

    def test_the_link_is_read_only(self, panel) -> None:  # noqa: F811
        """Displayed and copyable, never an input: there is nothing to submit."""
        book_id, _ = book_of_grids(panel)
        set_domain(panel, book_id, BASE)

        for fragment in play_links(panel.page(book_id)):
            assert "<input" not in fragment
            assert "<form" not in fragment
            assert "<code" in fragment

    def test_a_changed_base_changes_every_link_and_no_key(self, panel) -> None:  # noqa: F811
        """The base is the book's; the key is the grid's. They move apart."""
        book_id, _ = book_of_grids(panel)
        set_domain(panel, book_id, BASE)
        before = shown_urls(panel.page(book_id))

        set_domain(panel, book_id, "https://nonogram-studio.co")

        after = shown_urls(panel.page(book_id))
        assert [url.rsplit("/", 1)[-1] for url in after] == [
            url.rsplit("/", 1)[-1] for url in before
        ]
        assert all(url.startswith("https://nonogram-studio.co/play/") for url in after)

    def test_a_puzzle_whose_stored_grid_cannot_be_read_costs_its_own_link_only(
        self, panel  # noqa: F811
    ) -> None:
        """One damaged row must not cost the owner the whole screen.

        The exporter's own posture for the same value. Constructed, not
        imagined: the grid is written to something no key can be computed from.
        """
        book_id, ids = book_of_grids(panel, ("angel", "star"))
        set_domain(panel, book_id, BASE)
        _damage_grid(panel, ids[0])

        markup = panel.page(book_id)

        assert "No reader link: this puzzle's stored grid could not be read." in markup
        # The healthy row still has its link, and it is still the right one.
        assert shown_urls(markup) == [f"{BASE}/play/{key_by_hand(GRIDS['star'])}"]


def _damage_grid(panel, puzzle_id) -> None:  # noqa: F811
    """Replace one puzzle's stored grid with a value that is not a grid."""
    if panel.scope is None:
        panel.store.puzzles[puzzle_id]["grid"] = "not a grid"
        return
    import uuid

    from nonogram.db.models import Puzzle

    with panel.scope() as db:
        row = db.query(Puzzle).filter(Puzzle.id == uuid.UUID(puzzle_id)).first()
        row.grid = "not a grid"


# --------------------------------------------------------------------------
# AC-3 — a book with no domain
# --------------------------------------------------------------------------


class TestPlayerDomain_ABookWithNoDomainSaysSo:
    """AC-3 — the failure this notice exists instead of is a printed guess."""

    def test_it_says_so_and_links_to_print_setup(self, panel) -> None:  # noqa: F811
        book_id, _ = book_of_grids(panel)

        markup = panel.page(book_id)

        assert 'id="no-player-domain"' in markup
        assert "No player domain is set for this book" in markup
        assert f"/book/{book_id}/setup-print" in markup

    def test_no_url_is_rendered_from_a_missing_base(self, panel) -> None:  # noqa: F811
        book_id, _ = book_of_grids(panel)

        markup = panel.page(book_id)

        assert play_links(markup) == []
        assert "/play/" not in markup
        # The two spellings of the failure this rules out, named so a future
        # reader sees they were checked rather than assumed.
        assert "None/play/" not in markup
        assert "/play/None" not in markup

    def test_the_notice_goes_away_when_a_base_is_set(self, panel) -> None:  # noqa: F811
        """The control for the cell above: it can tell the two states apart."""
        book_id, _ = book_of_grids(panel)
        set_domain(panel, book_id, BASE)

        markup = panel.page(book_id)

        assert 'id="no-player-domain"' not in markup
        assert len(play_links(markup)) == 3


# --------------------------------------------------------------------------
# AC-4 — nothing but the key reaches the link (ADR-0041/R2)
# --------------------------------------------------------------------------


class TestPlayerDomain_NothingButTheKeyReachesTheLink:
    """AC-4, as a whitelist on what the fragment carries — and its control."""

    def test_the_link_carries_nothing_a_source_does_not_claim(self, panel) -> None:  # noqa: F811
        names = ("angel", "star", "box")
        book_id, ids = book_of_grids(panel, names)
        set_domain(panel, book_id, BASE)
        # Titles a leak would be recognisable in, set through the real route.
        for order, puzzle_id in enumerate(ids, start=1):
            panel.books.set_puzzle_title(book_id, puzzle_id, f"Sleeping {names[order - 1]}")

        fragments = play_links(panel.page(book_id))

        assert len(fragments) == len(names)
        for order, (fragment, name) in enumerate(zip(fragments, names), start=1):
            url = f"{BASE}/play/{key_by_hand(GRIDS[name])}"
            assert unexpected_in_link(fragment, url, order) == []

    def test_the_inventory_rejects_a_planted_title(self, panel) -> None:  # noqa: F811
        """The control: the same check, on a fragment that really leaks.

        Built by planting the title into a fragment of the shape the template
        emits, so the thing being measured is the check's ability to fail —
        not a belief that it would.
        """
        book_id, ids = book_of_grids(panel, ("angel",))
        set_domain(panel, book_id, BASE)
        url = f"{BASE}/play/{key_by_hand(GRIDS['angel'])}"
        fragment = play_links(panel.page(book_id))[0]
        assert unexpected_in_link(fragment, url, 1) == []

        leaked = fragment.replace(
            '<code class="play-url">', '<code class="play-url" data-title="Sleeping angel">'
        )

        assert "Sleeping angel" in unexpected_in_link(leaked, url, 1)

    def test_the_inventory_rejects_a_planted_grid(self, panel) -> None:  # noqa: F811
        """And the second control: a solution cell, in the copy target itself."""
        book_id, _ = book_of_grids(panel, ("angel",))
        set_domain(panel, book_id, BASE)
        url = f"{BASE}/play/{key_by_hand(GRIDS['angel'])}"
        fragment = play_links(panel.page(book_id))[0]

        cells = "".join(
            "1" if cell else "0" for row in GRIDS["angel"] for cell in row
        )
        leaked = fragment.replace(url, f"{url}?g={cells}")

        assert unexpected_in_link(leaked, url, 1) != []

    def test_no_link_anywhere_on_the_page_carries_a_title_or_a_grid(
        self, panel  # noqa: F811
    ) -> None:
        """Every href on the page, not only the ones this card added.

        The page's own title editor is an ``<input value=...>`` and is the
        screen's purpose — AC-4 is about what a *link* and a copy target
        carry, which is what this enumerates.
        """
        book_id, ids = book_of_grids(panel, ("angel", "star"))
        set_domain(panel, book_id, BASE)
        for puzzle_id in ids:
            panel.books.set_puzzle_title(book_id, puzzle_id, "Sleeping angel")

        markup = panel.page(book_id)

        hrefs = re.findall(r'href="([^"]*)"', markup)
        assert hrefs, "no links on the page at all: the check measured nothing"
        for href in hrefs:
            # The base is the one thing a reader link is allowed to carry, so
            # it is REMOVED from the haystack rather than used to excuse the
            # href that carries it: `or "adverax" in href` passed every href
            # this card emits without reading it (cycle 1, F-004). What is
            # searched is what the base does not account for.
            tail = href.replace(BASE, "")
            assert "Sleeping" not in tail, href
            for name in ("angel", "star"):
                assert name not in tail.lower(), href
        for name in ("angel", "star"):
            cells = "".join(
                "1" if cell else "0" for row in GRIDS[name] for cell in row
            )
            assert cells not in markup


# --------------------------------------------------------------------------
# EC — one recipe, and only one
# --------------------------------------------------------------------------


class TestPlayerDomain_OneRecipe:
    """ADR-0041/R1: exactly one implementation computes the key."""

    def test_no_second_spelling_lives_in_admin_or_a_template(self) -> None:
        """The hash is spelled in ``player_bundle`` and nowhere else it could leak into.

        ``puzzle_review``'s ``_grid_fingerprint`` is a different value for the
        same cells (it writes the extent the other way round and does not
        truncate) and is named here so this check states what it allows rather
        than quietly tolerating it.
        """
        import pathlib

        import nonogram.admin as admin_pkg

        root = pathlib.Path(admin_pkg.__file__).parent
        spellings = {
            path.relative_to(root).as_posix()
            for path in list(root.rglob("*.py")) + list(root.rglob("*.html"))
            if "sha256" in path.read_text() or "hexdigest" in path.read_text()
        }

        assert spellings == {"player_bundle.py", "puzzle_review.py"}, spellings

    def test_the_rendered_key_is_recomputed_from_the_stored_grid_every_time(
        self, panel  # noqa: F811
    ) -> None:
        """Not cached: editing the stored grid moves the link on the next render.

        A key memoised at creation would pass every other cell in this file.
        """
        book_id, ids = book_of_grids(panel, ("angel",))
        set_domain(panel, book_id, BASE)
        assert shown_urls(panel.page(book_id)) == [
            f"{BASE}/play/{key_by_hand(GRIDS['angel'])}"
        ]

        _replace_grid(panel, ids[0], GRIDS["box"])

        assert shown_urls(panel.page(book_id)) == [
            f"{BASE}/play/{key_by_hand(GRIDS['box'])}"
        ]


def _replace_grid(panel, puzzle_id, grid) -> None:  # noqa: F811
    """Write ``grid`` over the puzzle's stored one, in either storage mode."""
    cells = [[bool(cell) for cell in row] for row in grid]
    if panel.scope is None:
        record = panel.store.puzzles[puzzle_id]
        record["grid"] = cells
        record["width"] = len(cells[0])
        record["height"] = len(cells)
        return
    import uuid

    from nonogram.db.models import Puzzle

    with panel.scope() as db:
        row = db.query(Puzzle).filter(Puzzle.id == uuid.UUID(puzzle_id)).first()
        row.grid = cells
        row.width = len(cells[0])
        row.height = len(cells)


# --------------------------------------------------------------------------
# The column itself
# --------------------------------------------------------------------------


class TestPlayerDomain_TheColumn:
    """What the store does with the value, below the screens."""

    def test_the_reader_answers_none_for_every_shape_of_no_domain(self) -> None:
        class _Row:
            pass

        row = _Row()
        for stored in (None, "", "   "):
            setattr(row, PLAYER_DOMAIN_COLUMN, stored)
            assert stored_player_domain(row) is None
        # And a row from before the column exists at all.
        assert stored_player_domain(_Row()) is None

    def test_the_storage_boundary_refuses_a_base_the_reader_would_refuse(
        self, panel  # noqa: F811
    ) -> None:
        """``PrintSpec`` has no validating construction, so its type proves nothing."""
        from nonogram.admin.print_specs import PrintSpec

        book_id, _ = book_of_grids(panel)
        spec = PrintSpec(
            trim_width_cm="21.59",
            trim_height_cm="27.94",
            player_domain="http://nonogram.adverax.io",
        )

        with pytest.raises(ValueError, match="player domain"):
            panel.books.set_print_spec(book_id, spec)

        assert stored_player_domain(panel.books.get_book(book_id)) is None


class TestPlayerDomain_Migration018:
    """The column's own history, as 011/015/017's tests pin theirs."""

    def _module(self):
        import importlib.util
        import pathlib

        path = (
            pathlib.Path(__file__).resolve().parent.parent
            / "migrations"
            / "versions"
            / "018_book_player_domain.py"
        )
        spec = importlib.util.spec_from_file_location("migration_018", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_it_follows_017_and_adds_nothing_else(self) -> None:
        module = self._module()

        assert (module.revision, module.down_revision) == ("018", "017")

    def test_it_states_no_default_and_no_backfill(self) -> None:
        """The column's shape is the card's decision, so it is held, not described.

        013 and 017 both carry a server default and an explicit backfill
        because every existing book already *is* their default. Nothing is
        true of a player domain — no base was ever chosen for any book — so a
        default here would write a value nobody chose into every row, and the
        screens would then build links from it.
        """
        import inspect

        source = inspect.getsource(self._module().upgrade)

        assert "server_default" not in source
        assert "update()" not in source
        assert "nullable=True" in source

    def test_the_upgrade_runs_and_leaves_an_existing_book_with_no_domain(
        self, tmp_path, monkeypatch
    ) -> None:
        """A book written before 018 keeps NULL, and the reader calls that "none".

        Run against a real SQLite file through alembic, from 017 forward, so
        the claim is about the migration and not about ``create_all``.
        """
        import sqlalchemy as sa

        from tests.test_book_page_spec import _alembic

        url = f"sqlite:///{tmp_path / 'migrate-018.db'}"
        command, config = _alembic(url, monkeypatch)
        command.upgrade(config, "017")
        engine = sa.create_engine(url)
        with engine.begin() as conn:
            conn.execute(
                sa.text(
                    "INSERT INTO books (id, title, puzzle_ids, puzzle_titles,"
                    " book_metadata, status) VALUES ('b1', 'Winter', '[]', '{}',"
                    " '{}', 'draft')"
                )
            )

        command.upgrade(config, "018")

        with engine.begin() as conn:
            stored = conn.execute(
                sa.text("SELECT player_domain FROM books WHERE id = 'b1'")
            ).scalar()
        assert stored is None

        class _Row:
            player_domain = stored

        assert stored_player_domain(_Row()) is None

        # And the column goes away again without touching the row beside it.
        command.downgrade(config, "017")
        with engine.begin() as conn:
            assert conn.execute(
                sa.text("SELECT title FROM books WHERE id = 'b1'")
            ).scalar() == "Winter"
            with pytest.raises(Exception):
                conn.execute(sa.text("SELECT player_domain FROM books"))
