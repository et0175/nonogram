"""EC-034 (INV-013), interior/cover half — CARD-135, extended by CARD-129.

    EC-034  PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage

For any book — any member count, tiers, grid extents, title, with or without an
uploaded cover — and on every export route (the generator's ``export_book``,
the Finalise download, ``POST /book/<id>/download-pdf`` and
``POST /book/<id>/generate-pdf``):

* the interior PDF holds no cover page — no interior page is the cover file's
  page;
* its page 1 is the guide page — the page parity counts from (FR-043);
* **each page's parity is its 1-based position in the interior** (CARD-116's
  half, added here): every page is the book's trim, and on every page that
  carries a drawing — the puzzle pages and the answer pages alike — the
  drawing sits where a page of that parity puts it, gutter margin on the
  binding side;
* its page count is today's content without the cover — guide, puzzles,
  SOLUTIONS divider and answers — and equals the count the export reports;
* **the page count finalise reads equals the interior PDF's page count**, and
  the cover never changes it (CARD-129's half, added here): the figure the
  Finalise screen reports — the one KDP's gutter table is read at, and the one
  a book is refused on when it needs a wider gutter than it stores — is the
  exported interior's own count, on every book and on both sides of a cover
  upload, together with the "before pairing" and answer-page figures beside
  it;
* exactly one cover file of one 2550 x 3300 px page is produced beside it,
  holding the uploaded cover when one is set, else the generated title cover.

The corpus is built by hand with a
seeded ``random.Random`` (no hypothesis — ADR-0006) and its size is asserted,
so it cannot silently shrink. Expected values are derived here, independently
of the generator: the page count from the book's make-up, the tier counts by
reading the tier strings, the expected drawing edge in millimetres from
CON-018's profile and FR-032's centring rule, and the PDFs read back with
Pillow's own parser.
"""

from __future__ import annotations

import random
import re
from collections import Counter
from io import BytesIO

import numpy as np
import pytest
from PIL import Image, ImageDraw

from nonogram import clues
from nonogram.admin import image_manager as image_manager_module
import nonogram.admin.book_manager as book_manager_module
from nonogram.admin.book_pdf_generator import (
    BookPDFGenerator,
    _folio_reserve_px,
    page_is_right_hand,
)
from tests.helpers.page_ink import drawing_of
from tests.helpers.pdf_pages import pdf_page_count, pdf_pages, same_page
from tests.helpers.two_up_ink import drawings_of

TRIM_PX = (2550, 3300)
ROUTES = ("generator", "finalise", "download-pdf", "generate-pdf")
CASES = 28
SEED = 135

#: How many of :data:`CASES` build a book, and therefore have a Finalise
#: screen whose page count CARD-129's half of EC-034 is about: every route but
#: ``generator``. Asserted as a floor at the end, so a corpus that stopped
#: exercising the book routes cannot make that clause pass vacuously.
FINALISE_CASES = CASES - CASES // len(ROUTES)

#: CON-018's Book 1 profile in millimetres — every book here is on it —
#: written out rather than imported, so the expected edge below is a second
#: implementation of FR-030/FR-032 and not a re-derivation.
GUTTER_MM = 0.5 * 25.4
# CON-018 as amended 2026-10-17 (CARD-222): outside 0.5 in, top 0.55 in,
# bottom 0.47 in, the gutter unchanged at 0.5 in — so the gutter and the
# outside margin are now equal and the mirrored-margin difference below is
# zero. The *side* each margin is on still differs by parity, which is what
# ``_expected_drawing_left_mm`` reads.
OUTSIDE_MM = 0.5 * 25.4
TOP_MM = 0.55 * 25.4
BOTTOM_MM = 0.47 * 25.4
USABLE_WIDTH_MM = 8.5 * 25.4 - GUTTER_MM - OUTSIDE_MM
USABLE_HEIGHT_MM = 11 * 25.4 - TOP_MM - BOTTOM_MM - 12.0
STANDARD_CELL_MM = 7.5
PX_PER_MM = 300 / 25.4

#: CARD-202's own packed-tile constants, written out here independently (not
#: imported from ``nonogram.export.layout``'s ``SOLVED_TILE_GAP_MM`` /
#: ``SOLVED_TILE_MAX_CELL_MM``): a packed page is always two tiles across,
#: each reserving its own 12 mm band (the puzzle page's own band height,
#: reused per slot) rather than one page-level band.
PACKED_GAP_MM = 4.0
PACKED_MAX_CELL_MM = 6.0
PACKED_BAND_MM = 12.0
PACKED_TILE_WIDTH_MM = (USABLE_WIDTH_MM - PACKED_GAP_MM) / 2
PACKED_USABLE_HEIGHT_MM = 11 * 25.4 - TOP_MM - BOTTOM_MM

#: FR-040's two-up minimum, and the usable height a page has left once it
#: reserves a band for each of two puzzles rather than one.
TWO_UP_MINIMUM_MM = 7.0
PAIR_HEIGHT_MM = 11 * 25.4 - TOP_MM - BOTTOM_MM - 2 * 12.0

#: CARD-204 Fix 4's fixed, universal folio reserve, in millimetres — derived
#: the same way :func:`_expected_drawing_left_mm` and ``Sheet.shared_cell_mm``
#: (``tests/property/test_book_pairing.py``) do: ``_folio_reserve_px`` is a
#: font-measurement helper (not FR-040's own formula), so it is imported
#: directly rather than reimplemented a third time; the geometric arithmetic
#: that *uses* it below is this module's own independent check.
RESERVE_MM = _folio_reserve_px(300) * 25.4 / 300


def _across(puzzle):
    """The drawing's width in cells: the row-clue gutter plus the grid."""
    return max(len(clue) for clue in puzzle["clues_rows"]) + puzzle["width"]


def _down(puzzle):
    """The drawing's height in cells: the column-clue gutter plus the grid."""
    return max(len(clue) for clue in puzzle["clues_cols"]) + puzzle["height"]


def _shared_cell_mm(first, second):
    """FR-040's shared cell for a pair on one page, in millimetres.

    The largest cell, capped at the standard cell, at which the wider of the
    two drawings fits the usable width and both drawings' heights fit the trim
    less its top and bottom margins and **two** bands. Written out here, like
    every other expected value in this file.

    **CARD-204 Fix 4 (owner decision, 2026-10-12, "fixed universal
    reserve").** ``second`` is always the lower slot in this module's own
    upper/lower convention (``_puzzle_page_plan``'s own order). Production's
    ``compute_pair_layout`` now always widens the fit when the lower slot's
    own natural spare at the unreserved cell is below the fixed reserve, so
    this oracle re-derives that same "only widen when needed" rule
    independently, in millimetres, never importing
    ``compute_pair_layout`` itself.
    """
    natural = min(
        STANDARD_CELL_MM,
        USABLE_WIDTH_MM / max(_across(first), _across(second)),
        PAIR_HEIGHT_MM / (_down(first) + _down(second)),
    )
    natural_spare_mm = USABLE_WIDTH_MM - _across(second) * natural
    if natural_spare_mm >= RESERVE_MM:
        return natural
    return min(
        STANDARD_CELL_MM,
        (USABLE_WIDTH_MM - RESERVE_MM) / max(_across(first), _across(second)),
        PAIR_HEIGHT_MM / (_down(first) + _down(second)),
    )


def _pairs(first, second):
    """INV-010: two adjacent puzzles share a page iff their tiers are equal and
    their shared cell is at least 7.0 mm."""
    levels = [_LEVEL.get(str(p["difficulty_tier"]).lower()) for p in (first, second)]
    if levels[0] is None or levels[0] != levels[1]:
        return False
    return _shared_cell_mm(first, second) >= TWO_UP_MINIMUM_MM


def _puzzle_page_plan(puzzles):
    """EC-027's in-order walk: the puzzles each puzzle page holds, in order."""
    plan, index = [], 0
    while index < len(puzzles):
        if index + 1 < len(puzzles) and _pairs(puzzles[index], puzzles[index + 1]):
            plan.append([puzzles[index], puzzles[index + 1]])
            index += 2
        else:
            plan.append([puzzles[index]])
            index += 1
    return plan


def _expected_drawing_left_mm(puzzle, page_number, cell_mm=None, *, is_lower=False):
    """Where interior page ``page_number`` puts this puzzle's left edge
    (FR-032, CARD-204 reading (b)).

    The drawing is ``clue depth + grid`` cells across at ``min(standard cell,
    page fit)``, right-aligned across the usable width — flush with the
    *outer* margin, mirrored by parity: flush right (gutter on the left) on
    a right-hand (odd) page, flush left (gutter on the right) on a left-hand
    one. ``cell_mm`` overrides the cell with the pair's shared one when the
    puzzle is a slot of a two-up page (FR-040); its drawing is right-aligned
    across the same usable width either way.

    **History (CARD-204 Fix 1/Fix 2, reverted by Fix 3, restored as a fixed
    constant by Fix 4 — owner decision, 2026-10-12, "fixed universal
    reserve").** ``is_lower`` (``True`` only for the lower slot of a two-up
    page — this helper's one caller never sets it for a single page or the
    upper slot) shifts the drawing :data:`RESERVE_MM` toward the gutter,
    re-deriving :func:`~nonogram.export.layout._slot_layout`'s own
    ``outer_reserve_px`` shift independently, in millimetres. Fix 3 had
    removed this entirely (a two-up page's lower slot sat at the plain
    flush position with no reserve); Fix 4 restores it as a *fixed* amount,
    never a page/book-specific one.
    """
    across = _across(puzzle)
    cell = (
        min(STANDARD_CELL_MM, USABLE_WIDTH_MM / across, USABLE_HEIGHT_MM / _down(puzzle))
        if cell_mm is None
        else cell_mm
    )
    spare = USABLE_WIDTH_MM - across * cell
    reserved = min(RESERVE_MM, max(spare, 0)) if is_lower else 0.0
    left_margin = GUTTER_MM if page_number % 2 else OUTSIDE_MM
    if page_number % 2:
        return left_margin + spare - reserved
    return left_margin + reserved


def _packed_cell_mm(group):
    """CARD-202's one shared cell for ``group`` (2 or 4 small answers), in mm.

    Independent of :func:`~nonogram.export.layout.compute_packed_solved_layout`
    (CLAUDE.md: prefer an independent second implementation): two equal
    tiles across, each reserving its own band, the largest cell at which
    every answer's own drawing fits its own tile below its own band, capped
    at :data:`PACKED_MAX_CELL_MM`.
    """
    rows = -(-len(group) // 2)  # ceil(len(group) / 2)
    tile_height = (
        PACKED_USABLE_HEIGHT_MM - (rows - 1) * PACKED_GAP_MM
    ) / rows
    drawing_height = tile_height - PACKED_BAND_MM
    return min(
        PACKED_MAX_CELL_MM,
        min(PACKED_TILE_WIDTH_MM / _across(p) for p in group),
        min(drawing_height / _down(p) for p in group),
    )


def _packed_column_left_mm(group, column, page_number):
    """Where packed page ``page_number``'s ``column`` (0 left, 1 right) puts
    the **least-padded** of its own answers' drawing left edges, or ``None``
    when ``column`` holds no answer at all (a lone leftover's packed page
    fills only column 0; column 1 is empty and has no ink to measure).

    A packed page's two columns can each hold more than one row (a 4-up
    page), and two rows need not agree on how much their own drawing is
    centred inside the shared tile — only the minimum (the widest answer in
    that column) is safe to compare against measured ink, since the other
    row's ink falls to its right.
    """
    indices = list(range(column, len(group), 2))
    if not indices:
        return None
    tile_left = (
        (GUTTER_MM if page_number % 2 else OUTSIDE_MM)
        + column * (PACKED_TILE_WIDTH_MM + PACKED_GAP_MM)
    )
    cell = _packed_cell_mm(group)
    spares = (PACKED_TILE_WIDTH_MM - _across(group[i]) * cell for i in indices)
    return tile_left + max(min(spares), 0.0) / 2


@pytest.fixture
def admin_app(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TESTING", "true")
    from nonogram.admin.app import create_app

    image_manager_module._image_manager = None
    # A fresh in-memory book store, restored afterwards: the module singleton
    # would otherwise carry this test's books (and their puzzle ids) into
    # every later test that builds an in-memory app.
    monkeypatch.setattr(
        book_manager_module, "_book_manager", book_manager_module.BookManager(session_factory=None)
    )
    app = create_app()
    app.config["TESTING"] = True
    app.config["BOOK_COVER_DIR"] = str(tmp_path / "covers")
    with app.app_context():
        yield app
    image_manager_module._image_manager = None


def _random_puzzle(rng, *, small=False, tier=None):
    """One puzzle of the corpus.

    ``small`` draws the extents from the range where two drawings *do* fit one
    page — with the single-run clues these grids produce, a pair needs
    ``(h1 + 1) + (h2 + 1) <= 236.35 / 7`` down and ``w + 1 <= 193.675 / 7``
    across — and ``tier`` fixes the grade, because a pair is offered only
    between equal tiers (INV-010). Together they are what puts **two-up pages
    on both parities** in this corpus: four small puzzles of one tier pair into
    interior pages 2 and 3, one left-hand and one right-hand.
    """
    if small:
        width, height = rng.randint(10, 20), rng.randint(10, 14)
    else:
        width, height = rng.randint(10, 30), rng.randint(10, 30)
    left, top = rng.randrange(width), rng.randrange(height)
    right, bottom = rng.randint(left + 1, width), rng.randint(top + 1, height)
    grid = [
        [left <= x < right and top <= y < bottom for x in range(width)]
        for y in range(height)
    ]
    found = clues.compute_clues(grid)
    return {
        "grid": grid,
        "clues_rows": [list(c) for c in found.rows],
        "clues_cols": [list(c) for c in found.columns],
        "width": width,
        "height": height,
        "difficulty_tier": (
            tier if tier is not None
            else rng.choice(["easy", "medium", "hard", "Easy", "Hard"])
        ),
    }


def _random_cover(rng):
    size = (rng.randint(400, 1400), rng.randint(600, 2000))
    art = Image.new("RGB", size, tuple(rng.randint(0, 110) for _ in range(3)))
    w, h = size
    ImageDraw.Draw(art).ellipse(
        (w // 4, h // 4, 3 * w // 4, h // 2),
        fill=tuple(rng.randint(160, 255) for _ in range(3)),
    )
    return art


def _random_case(rng, index):
    route = ROUTES[index % len(ROUTES)]  # every route, evenly
    low = 1 if route == "generate-pdf" else 0  # that route refuses an empty book
    # Every third case is drawn from the small-and-same-tier corner, where the
    # walk pairs: with extents and tiers both drawn freely a two-up page is
    # rare (the review's F-006), and one that lands on an *odd* interior page
    # rarer still, so the parity half of this property went unswept. A pairing
    # case of 3..4 puzzles takes pages 2 and 3 — both parities — and one of 3
    # ends with a puzzle printed alone on an odd page beside them.
    pairing = index % 3 == 1
    if pairing:
        tier = rng.choice(["easy", "medium", "hard", "Easy", "Hard"])
        puzzles = [
            _random_puzzle(rng, small=True, tier=tier) for _ in range(rng.randint(3, 4))
        ]
    else:
        puzzles = [_random_puzzle(rng) for _ in range(rng.randint(low, 3))]
    return {
        "route": route,
        "title": "Book " + "".join(rng.choice("ABCDEFGHJK") for _ in range(rng.randint(3, 12))),
        "puzzles": puzzles,
        "cover": _random_cover(rng) if rng.random() < 0.5 else None,
    }


def _expected_guide(puzzles):
    tiers = Counter(p["difficulty_tier"].lower() for p in puzzles)
    return BookPDFGenerator().create_guide_page(
        len(puzzles), tiers["easy"], tiers["medium"], tiers["hard"]
    )


#: Which level a stored tier word belongs to — written out here, like every
#: other expected value in this file, rather than imported from the code that
#: produces it.
_LEVEL = {"easy": 0, "medium": 1, "hard": 2}


def _as_the_interior_prints_them(case):
    """The case's puzzles in the order the exported interior holds them.

    A book runs easy, then medium, then hard (FR-041, INV-009), and since
    CARD-128 that grouping is made **at PDF time**, by the generator itself —
    so it holds for the ``generator`` route, which hands ``export_book`` a
    list with no book behind it, exactly as it holds for the routes whose
    books store a grouped order. One stable sort on the level alone, so two
    puzzles of one level keep the order they were submitted in.

    This decides only *which* puzzle each page holds. What the assertions below
    are about — that the page's parity is its 1-based position in the interior
    — is untouched by it, and is still checked on every page.
    """
    return sorted(
        case["puzzles"], key=lambda p: _LEVEL.get(str(p["difficulty_tier"]).lower(), 3)
    )


def _section_plan(puzzles, toc_pages=1):
    """The puzzle section: ``(page number, the puzzles on it)`` per page.

    Interior pages 1-2 are the guide (CARD-201's 2-page tutorial), then
    ``toc_pages`` pages of table of contents (CARD-200 — this module's own
    cases never hold enough puzzles to need more than the default one), and
    then each non-empty **named** level opens with a divider page of its own
    (TERM-031, CARD-128) followed by that level's pages as
    :func:`_puzzle_page_plan` walks them. A run of puzzles whose stored tier
    is no level at all opens no divider — there is no name to print on one —
    so it simply follows the last named level.

    Returns the puzzle pages only; the dividers are counted by their absence
    from the numbering (:func:`_divider_pages`).
    """
    pages, page_number = [], 3 + toc_pages
    index = 0
    while index < len(puzzles):
        level = _LEVEL.get(str(puzzles[index]["difficulty_tier"]).lower())
        run = [p for p in puzzles[index:]
               if _LEVEL.get(str(p["difficulty_tier"]).lower()) == level]
        # The order is grouped, so a level's run is contiguous and this is all
        # of it.
        if level is not None:
            page_number += 1  # the level's divider
        for group in _puzzle_page_plan(run):
            pages.append((page_number, group))
            page_number += 1
        index += len(run)
    return pages


def _divider_pages(puzzles):
    """How many divider pages the puzzle section opens: one per named level."""
    return len({
        level
        for level in (
            _LEVEL.get(str(p["difficulty_tier"]).lower()) for p in puzzles
        )
        if level is not None
    })


def _qualifies_for_packing(puzzle):
    """CARD-202's threshold, written out here rather than imported
    (:func:`~nonogram.admin.book_answer_key.qualifies_for_packing`):
    width<=15 and height<=20, both sides checked separately."""
    return puzzle["width"] <= 15 and puzzle["height"] <= 20


def _grouped_run(run):
    """A same-level qualifying run cut into CARD-202's own page groups:
    4 at a time while at least 4 remain, then 2 at a time while at least 2
    remain, then a lone 1 if one is left over (owner decision, resolved
    2026-10-08). Pure arithmetic over the run alone, independent of
    :func:`~nonogram.admin.book_answer_key.plan_small_answer_pages`
    (CLAUDE.md: prefer an independent second implementation)."""
    groups = []
    index = 0
    while index < len(run):
        remaining = len(run) - index
        take = 4 if remaining >= 4 else min(remaining, 2)
        groups.append(tuple(run[index : index + take]))
        index += take
    return groups


def _answer_section_plan(printed):
    """``printed``'s answers (the book's print order) grouped into answer
    pages exactly as CARD-202 packs them: one ``(kind, group)`` per page, in
    print order. ``kind`` is ``"full"`` for a large (non-qualifying) answer's
    own CARD-198 page (always a 1-tuple, drawn by ``solved_puzzle_page``) or
    ``"packed"`` for a CARD-202 packed page (a 1-, 2- or 4-tuple — a lone
    qualifying leftover still packs, with one slot empty, drawn by
    ``_packed_answer_page``; the two kinds of 1-tuple are drawn by different
    methods at different geometry and must not be conflated). A level change
    or a non-qualifying answer closes a run of qualifying answers (G-6).
    """
    plan = []
    run = []
    run_level = None
    for puzzle in printed:
        level = _LEVEL.get(str(puzzle["difficulty_tier"]).lower(), 3)
        if _qualifies_for_packing(puzzle) and run and level == run_level:
            run.append(puzzle)
            continue
        if run:
            plan.extend(("packed", group) for group in _grouped_run(run))
            run = []
        if _qualifies_for_packing(puzzle):
            run, run_level = [puzzle], level
        else:
            plan.append(("full", (puzzle,)))
    if run:
        plan.extend(("packed", group) for group in _grouped_run(run))
    return plan


def _expected_answer_pages(printed):
    """How many answer pages CARD-202's packing takes, for ``printed``."""
    return len(_answer_section_plan(printed))


#: ``data-interior-page-count="N"`` on the Finalise screen: the page count the
#: finalise step reads and checks KDP's gutter table at (CARD-129, EC-034).
_FINALISE_PAGE_COUNT = re.compile(r'data-interior-page-count="(\d+)"')
_FINALISE_UNPAIRED = re.compile(r'data-unpaired-page-count="(\d+)"')
_FINALISE_ANSWERS = re.compile(r'data-answer-page-count="(\d+)"')


def _finalise_figures(client, book_id):
    """The three interior figures the Finalise screen reports, as ints.

    ``(page count, before pairing, answer pages)``. The page count is the one
    CARD-129's gutter check is made against, which is why EC-034 asks for it
    to be the interior PDF's own — read off the screen the owner reads it off,
    not out of the function that produced it.
    """
    response = client.get(f"/book/{book_id}/finalize")
    assert response.status_code == 200, book_id
    page = response.get_data(as_text=True)
    found = [
        pattern.search(page)
        for pattern in (_FINALISE_PAGE_COUNT, _FINALISE_UNPAIRED, _FINALISE_ANSWERS)
    ]
    assert all(found), f"the Finalise screen reports no page count: {book_id}"
    return tuple(int(match.group(1)) for match in found)


def _export_through_route(app, case):
    """What one case's export produced, and what Finalise says about it.

    ``(interior bytes, cover bytes, reported page count or None, finalise)``.
    ``finalise`` is ``None`` for the ``generator`` route — that route hands
    ``export_book`` a list with no book behind it, so there is no Finalise
    screen to ask — and otherwise the figures that screen reports, read
    **twice**: once before this case's cover is uploaded and once after, which
    is EC-034's "the cover never changes it" (the two are asserted equal by
    the caller).
    """
    if case["route"] == "generator":
        export = BookPDFGenerator().export_book(
            case["puzzles"], case["title"], cover_image=case["cover"]
        )
        return (
            export.interior.getvalue(),
            export.cover.getvalue(),
            export.interior_page_count,
            None,
        )

    book_id = app.book_manager.create_book(
        title=case["title"],
        description="A property-test book.",
        theme="generic",
        target_audience="adults",
        size="21.59×27.94",
    )
    ids = [
        app.puzzle_review_service.add_puzzle(
            grid=p["grid"],
            clues_rows=p["clues_rows"],
            clues_cols=p["clues_cols"],
            width=p["width"],
            height=p["height"],
            theme="generic",
            difficulty_score=10,
            difficulty_tier=p["difficulty_tier"],
            quality_score=50,
            recognizability="medium",
            strategies_used=[],
        )
        for p in case["puzzles"]
    ]
    if ids:
        app.book_manager.add_puzzles_to_book(book_id, ids)

    client = app.test_client()
    before_the_cover = _finalise_figures(client, book_id)
    if case["cover"] is not None:
        png = BytesIO()
        case["cover"].save(png, format="PNG")
        png.seek(0)
        client.post(
            f"/book/{book_id}/finalize",
            data={"cover": (png, "cover.png")},
            content_type="multipart/form-data",
        )
    after_the_cover = _finalise_figures(client, book_id)

    parts = []
    for part in ("interior", "cover"):
        if case["route"] == "finalise":
            response = client.post(
                f"/book/{book_id}/finalize", data={"action": "download_pdf", "part": part}
            )
        else:
            response = client.post(f"/book/{book_id}/{case['route']}?part={part}")
        assert response.status_code == 200, (case["route"], part)
        assert response.mimetype == "application/pdf"
        parts.append(response.get_data())
    return parts[0], parts[1], None, (before_the_cover, after_the_cover)


def test_PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage(admin_app):
    rng = random.Random(SEED)
    cases = [_random_case(rng, i) for i in range(CASES)]
    seen = Counter()

    for number, case in enumerate(cases):
        label = f"case {number} ({case['route']}, {len(case['puzzles'])} puzzles, cover={case['cover'] is not None})"
        interior_bytes, cover_bytes, reported, finalise = _export_through_route(
            admin_app, case
        )
        interior = pdf_pages(interior_bytes)
        cover_pages = pdf_pages(cover_bytes)
        n = len(case["puzzles"])

        # Exactly one cover file of one trim-size page, holding the right cover.
        assert len(cover_pages) == 1, label
        (cover_page,) = cover_pages
        assert cover_page.size == TRIM_PX, label
        expected_cover = (
            case["cover"].resize(TRIM_PX)
            if case["cover"] is not None
            else BookPDFGenerator().create_cover_page(case["title"])
        )
        assert same_page(cover_page, expected_cover), label

        # Today's content with the cover gone: the 2-page guide (CARD-201),
        # the pages the puzzles take (two-up pairing can make them fewer than
        # the puzzles, FR-040), divider, and the answer section — one full
        # solved page per large answer (CARD-198) or 2-or-4 small answers
        # packed to a page (CARD-202, :func:`_expected_answer_pages`).
        printed = _as_the_interior_prints_them(case)
        plan = _puzzle_page_plan(printed)
        # CARD-200: the table of contents, one page, between the guide and
        # the puzzle section — only when there is a puzzle to list, the same
        # "only when there are puzzles" guard the SOLUTIONS divider and the
        # answer section already have. Always exactly one page here: every
        # case this module generates holds at most 4 puzzles (`_random_case`),
        # far under what one TOC page holds on this module's own Book 1
        # profile trim (`TRIM_PX`) — not re-derived from the font metrics
        # `book_pdf_generator._toc_entries_per_page` measures, the one place
        # in this file an independent reimplementation would just be that
        # same Pillow measurement a second time.
        expected_toc = 1 if n else 0
        section = _section_plan(printed, toc_pages=expected_toc)
        dividers = _divider_pages(printed)
        expected_answers = _expected_answer_pages(printed)
        expected_count = (
            2 + expected_toc + dividers + len(plan) + (expected_answers + 1 if n else 0)
        )
        assert len(interior) == expected_count, label
        assert pdf_page_count(interior_bytes) == expected_count, label
        if reported is not None:
            assert reported == expected_count, label

        # CARD-129's half of EC-034: **the page count finalise checks equals
        # the interior's page count**, for every book, and the cover never
        # changes it. The figure is read off the Finalise screen, which is
        # where the KDP gutter check takes it from (FR-030, ADR-0036's
        # clarification) — so a screen that went back to estimating the count
        # would fail here rather than at upload, which is the only other place
        # a wrong count shows up.
        if finalise is not None:
            before_the_cover, after_the_cover = finalise
            assert after_the_cover == before_the_cover, (
                f"{label}: the cover changed the interior's figures, "
                f"{before_the_cover} -> {after_the_cover}"
            )
            page_count, unpaired, answer_pages = after_the_cover
            assert page_count == expected_count, label
            assert page_count == len(interior), label
            # The other two figures the screen reports, against this module's
            # own walks: the same interior with every puzzle on a page of its
            # own (FR-040), and CARD-202's own packed-or-full answer count.
            assert answer_pages == expected_answers, label
            # CARD-200: the TOC's own term is unchanged by pairing/packing,
            # so it is part of the unpaired baseline too (the same
            # `toc_pages=toc_page_count` passed to every one of
            # `interior_stream`'s own `interior_page_count` calls).
            assert unpaired == 2 + expected_toc + dividers + n + (n + 1 if n else 0), label
            assert unpaired >= page_count, label
            seen["finalise count"] += 1
            seen[
                "finalise count with cover"
                if case["cover"] is not None
                else "finalise count without cover"
            ] += 1
            if unpaired > page_count:
                seen["finalise count with a shared page"] += 1

        # Page 1 is the guide page, and no interior page is the cover.
        assert same_page(interior[0], _expected_guide(case["puzzles"])), label
        for page_number, page in enumerate(interior, start=1):
            assert not same_page(page, cover_page), f"{label}: page {page_number} is the cover"
            assert page.size == TRIM_PX, f"{label}: page {page_number} is not the trim"

        # Each page's parity is its 1-based position in the interior (CARD-116).
        # Measured off the page: a right-hand (odd) page carries the gutter
        # margin on its left, so its drawing sits further right than the same
        # drawing on a left-hand page, by gutter - outside.
        def _measured(page_number, puzzle, drawing, cell_mm=None, *, is_lower=False):
            drawn_left_mm = drawing.left / PX_PER_MM
            expected_mm = _expected_drawing_left_mm(
                puzzle, page_number, cell_mm, is_lower=is_lower
            )
            assert abs(drawn_left_mm - expected_mm) < 0.1, (
                f"{label}: page {page_number} "
                f"({'right' if page_number % 2 else 'left'}-hand) "
                f"draws its puzzle at {drawn_left_mm:.3f} mm, not {expected_mm:.3f} mm"
            )
            seen["right-hand" if page_number % 2 else "left-hand"] += 1

        for page_number, group in section:
            drawings = drawings_of(interior[page_number - 1])
            assert len(drawings) == len(group), (
                f"{label}: page {page_number} holds {len(drawings)} drawing(s), "
                f"not {len(group)}"
            )
            shared = _shared_cell_mm(*group) if len(group) == 2 else None
            # The *lower* slot of a two-up page — the later puzzle, second in
            # the group — is the one CARD-204 Fix 4's fixed reserve shifts;
            # the upper slot and every single page keep the plain flush rule.
            for position, (puzzle, drawing) in enumerate(zip(group, drawings)):
                _measured(
                    page_number,
                    puzzle,
                    drawing,
                    shared,
                    is_lower=len(group) == 2 and position == 1,
                )
            make_up = "two-up page" if len(group) == 2 else "single page"
            seen[make_up] += 1
            # Both slots of a two-up page are centred across the usable width
            # of *that page's* parity, so the make-up and the parity are
            # counted together and both combinations are required below.
            seen[f"{make_up} {'right-hand' if page_number % 2 else 'left-hand'}"] += 1

        # The same clause on the answer pages. Since CARD-198 an *unpacked*
        # (single-answer) answer page is a full-page drawing —
        # solved_puzzle_page calls the same compute_layout as an unsolved
        # single page at that position — so it is measured exactly like one
        # of the puzzle section's own single pages, through the same
        # :func:`_expected_drawing_left_mm` and the same independent
        # :func:`drawing_of` reader (safe for a solved page's
        # ``.left``/``.top``, per that helper's own docstring, even though
        # ``.columns``/``.rows`` are not).
        #
        # CARD-202 packs some answers 2-or-4 to a page, and neither
        # `drawing_of` (one drawing) nor `drawings_of` (two, stacked
        # vertically) reads a 2-column packed tile — so a packed page's
        # parity is checked per column instead, against
        # :func:`_packed_column_left_mm`'s own independent tile model: the
        # page is split at its own horizontal centre (safely inside the gap
        # between the two tiles on either parity, since the margin
        # difference — gutter minus outside — is much smaller than the gap
        # zone the two tiles leave between them), and each half's own
        # leftmost ink column is measured directly.
        #
        # CARD-201 grows the guide to two pages, which shifts this section's
        # own start by one (4, not 3 — the same +1 ``expected_count`` above
        # applies). CARD-200 shifts it once more by the TOC's own length
        # (``expected_toc``, already computed above for ``expected_count``) —
        # one more front-matter section between the guide and the puzzle
        # section, the same term every other page position in this test
        # already carries.
        answer_page_number = 4 + expected_toc + dividers + len(plan)
        for kind, group in _answer_section_plan(printed):
            page = interior[answer_page_number - 1]
            right_hand = page_is_right_hand(answer_page_number)
            if kind == "full":
                (puzzle,) = group
                drawn_left_mm = drawing_of(page).left / PX_PER_MM
                expected_mm = _expected_drawing_left_mm(puzzle, answer_page_number)
                assert abs(drawn_left_mm - expected_mm) < 0.1, (
                    f"{label}: answer page {answer_page_number} "
                    f"({'right' if right_hand else 'left'}-hand) "
                    f"starts its drawing at {drawn_left_mm:.3f} mm, not {expected_mm:.3f} mm"
                )
                seen["single answer page"] += 1
            else:
                half = page.width // 2
                for column, (left, right) in enumerate(((0, half), (half, page.width))):
                    expected_mm = _packed_column_left_mm(
                        group, column, answer_page_number
                    )
                    if expected_mm is None:
                        continue  # a lone leftover's packed page: column empty
                    # CARD-200: the page's own folio now sits in the usable
                    # area's bottom-outer corner — inside the margin-free
                    # region, not the bottom margin itself (the folio's own
                    # anchor puts its glyph box's bottom edge exactly at
                    # ``usable_bottom``, one line above it) — so a plain
                    # leftmost-ink scan over the full page height would read
                    # the folio's own ink on whichever half it lands in
                    # (it is flush with the usable area's *outer* edge,
                    # often further out than a packed tile's own left edge).
                    # Cropped above ``BOTTOM_MM`` plus a few mm of headroom
                    # for one line of :data:`~nonogram.admin.book_pdf_generator.FOLIO_PT`
                    # text, which stays well clear of a packed tile's own
                    # bottom edge (every tile keeps its drawing inside the
                    # band below PACKED_BAND_MM and the usable height,
                    # never down into this margin at all).
                    bottom_limit = page.height - round((BOTTOM_MM + 6.0) * PX_PER_MM)
                    crop = page.crop((left, 0, right, bottom_limit))
                    ink = np.asarray(crop.convert("L")) < 128
                    cols_with_ink = np.where(ink.any(axis=0))[0]
                    assert cols_with_ink.size, (
                        f"{label}: packed answer page {answer_page_number} "
                        f"column {column} has no ink at all"
                    )
                    drawn_mm = (cols_with_ink.min() + left) / PX_PER_MM
                    assert abs(drawn_mm - expected_mm) < 0.5, (
                        f"{label}: packed answer page {answer_page_number} "
                        f"({'right' if right_hand else 'left'}-hand) column "
                        f"{column} starts its ink at {drawn_mm:.3f} mm, not "
                        f"{expected_mm:.3f} mm"
                    )
                seen["packed answer page"] += 1
            seen["right-hand" if right_hand else "left-hand"] += 1
            seen["answer page"] += 1
            answer_page_number += 1

        seen[case["route"]] += 1
        seen["with cover" if case["cover"] is not None else "without cover"] += 1
        seen["empty book" if n == 0 else "non-empty book"] += 1

    assert len(cases) >= CASES
    for route in ROUTES:
        assert seen[route] >= CASES // len(ROUTES) - 1, (route, seen)
    assert seen["with cover"] >= 5 and seen["without cover"] >= 5, seen
    assert seen["empty book"] >= 1 and seen["non-empty book"] >= 10, seen
    # Both parities really were measured, on both page kinds.
    assert seen["right-hand"] >= 10 and seen["left-hand"] >= 10, seen
    # Both page make-ups are in the corpus, so the page map above is exercised
    # in both directions rather than being a walk that never pairs — and a
    # two-up page was measured on **each parity**, which is the half a corpus
    # of freely drawn extents and tiers left to chance (CARD-127 review F-006):
    # a slot centred across the wrong page's usable width would be caught on
    # one parity only. (CARD-127's own corpora are where the walk's verdicts
    # are swept; what is swept here is where the drawings land.)
    assert seen["single page"] >= 5 and seen["two-up page"] >= 5, seen
    assert seen["two-up page right-hand"] >= 2, seen
    assert seen["two-up page left-hand"] >= 2, seen
    assert seen["single page right-hand"] >= 2 and seen["single page left-hand"] >= 2, seen
    # The answer pages were measured too — one page per large answer
    # (CARD-198) or 2-or-4 small answers packed to a page (CARD-202) — the
    # same shape of claim the puzzle-page loop above already makes, just
    # over the answer section instead. Both kinds of answer page are in the
    # corpus (the "small" pairing-corner cases are also small enough, at
    # width<=20, to sometimes qualify for packing at width<=15).
    assert seen["answer page"] >= 20, seen
    assert seen["single answer page"] >= 5, seen
    assert seen["packed answer page"] >= 1, seen
    # CARD-129: the finalise page count was really read, on enough books and
    # on both sides of the cover — a clause that only ran on the one route
    # that has no Finalise screen would pass vacuously. Three of the four
    # routes build a book, so 28 cases give 21 of them.
    assert seen["finalise count"] >= FINALISE_CASES >= 18, (
        f"the corpus checked the finalise count on only "
        f"{seen['finalise count']} books"
    )
    assert seen["finalise count with cover"] >= 4, seen
    assert seen["finalise count without cover"] >= 4, seen
    # And on at least one book whose pairing really shortened the interior, so
    # "before pairing" is compared against something other than the count.
    assert seen["finalise count with a shared page"] >= 3, seen


def test_page_numbers_start_at_one():
    """There is no interior page 0 — the cover is not a page of the interior."""
    with pytest.raises(ValueError):
        page_is_right_hand(0)
