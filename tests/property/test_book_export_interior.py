"""EC-034 (INV-013), interior/cover half — CARD-135.

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
* exactly one cover file of one 2550 x 3300 px page is produced beside it,
  holding the uploaded cover when one is set, else the generated title cover.

CARD-129 owns the finalise page-count half. The corpus is built by hand with a
seeded ``random.Random`` (no hypothesis — ADR-0006) and its size is asserted,
so it cannot silently shrink. Expected values are derived here, independently
of the generator: the page count from the book's make-up, the tier counts by
reading the tier strings, the expected drawing edge in millimetres from
CON-018's profile and FR-032's centring rule, and the PDFs read back with
Pillow's own parser.
"""

from __future__ import annotations

import random
from collections import Counter
from io import BytesIO

import pytest
from PIL import Image, ImageDraw

from nonogram import clues
from nonogram.admin import image_manager as image_manager_module
import nonogram.admin.book_manager as book_manager_module
from nonogram.admin.book_pdf_generator import BookPDFGenerator, page_is_right_hand
from tests.helpers.page_ink import drawing_of
from tests.helpers.pdf_pages import pdf_page_count, pdf_pages, same_page
from tests.helpers.two_up_ink import drawings_of

TRIM_PX = (2550, 3300)
ROUTES = ("generator", "finalise", "download-pdf", "generate-pdf")
CASES = 28
SEED = 135

#: CON-018's Book 1 profile in millimetres — every book here is on it —
#: written out rather than imported, so the expected edge below is a second
#: implementation of FR-030/FR-032 and not a re-derivation.
GUTTER_MM = 0.5 * 25.4
OUTSIDE_MM = TOP_MM = BOTTOM_MM = 0.375 * 25.4
USABLE_WIDTH_MM = 8.5 * 25.4 - GUTTER_MM - OUTSIDE_MM
USABLE_HEIGHT_MM = 11 * 25.4 - TOP_MM - BOTTOM_MM - 12.0
STANDARD_CELL_MM = 7.5
PX_PER_MM = 300 / 25.4

#: FR-040's two-up minimum, and the usable height a page has left once it
#: reserves a band for each of two puzzles rather than one.
TWO_UP_MINIMUM_MM = 7.0
PAIR_HEIGHT_MM = 11 * 25.4 - TOP_MM - BOTTOM_MM - 2 * 12.0


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
    """
    return min(
        STANDARD_CELL_MM,
        USABLE_WIDTH_MM / max(_across(first), _across(second)),
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


# --------------------------------------------------------------------------
# FR-042's packed answer key, written out here (CARD-134 / CARD-133)
# --------------------------------------------------------------------------

#: A page holds six answers while every answer on it is at most 20 cells on
#: its longest side, and four once one of them is longer (INV-011).
SIX_UP, FOUR_UP, SIX_UP_LONGEST_SIDE = 6, 4, 20

#: CARD-133's tile geometry in millimetres. An answer page carries **no title
#: band**, so its usable height is the trim less the top and bottom margins
#: only — which is why it is not :data:`USABLE_HEIGHT_MM`.
ANSWER_TILE_GAP_MM = 2.0
ANSWER_CAPTION_MM = 6.0
ANSWER_HEADING_MM = 6.0
ANSWER_MAX_CELL_MM = 5.0
ANSWER_USABLE_HEIGHT_MM = 11 * 25.4 - TOP_MM - BOTTOM_MM

#: How far the leftmost *ink* of a grid may sit from the geometric edge the
#: arithmetic below predicts. A grid's border is a heavy rule — twice the thin
#: one, and a book page's thin rule is held at 0.25 mm (ADR-0037/R2) — stroked
#: on the boundary it marks, so its ink reaches a little left of it. 0.3 mm
#: covers that with room to spare and is still an order of magnitude below the
#: 3.175 mm (gutter − outside) a page laid out on the wrong parity would be out
#: by, which is what this measurement is for.
ANSWER_EDGE_TOLERANCE_MM = 0.3


def _answer_capacity(answers):
    """FR-042's tiling for the answers on one page."""
    if any(max(p["width"], p["height"]) > SIX_UP_LONGEST_SIDE for p in answers):
        return FOUR_UP
    return SIX_UP


def _level_of(puzzle):
    return _LEVEL.get(str(puzzle["difficulty_tier"]).lower())


def _answer_page_plan(puzzles):
    """FR-042's walk: ``(answers, capacity, heading)`` per answer page.

    The rule written out again rather than asked of the walk under test: the
    next answer joins the current page when it is of the same level *and* the
    page with it stays within the capacity it would then have, and otherwise
    opens a new one; the first page of a level's run carries that level's
    heading, later pages of the run carry none.
    """
    grouped, current = [], []
    for puzzle in puzzles:
        if current:
            joined = current + [puzzle]
            if _level_of(puzzle) == _level_of(current[0]) and len(joined) <= (
                _answer_capacity(joined)
            ):
                current = joined
                continue
            grouped.append(current)
        current = [puzzle]
    if current:
        grouped.append(current)

    pages, previous = [], object()
    for answers in grouped:
        level = _level_of(answers[0])
        pages.append((answers, _answer_capacity(answers), level != previous))
        previous = level
    return pages


def _expected_answer_left_mm(answers, page_number, capacity, heading):
    """Where an answer page puts the left edge of its leftmost grid.

    CARD-133's arithmetic in millimetres: the usable area is two tiles across
    with a 2 mm gap between them, each grid is drawn at the largest square cell
    its tile can hold (capped at 5 mm) and centred across that tile, and the
    page's left margin is the gutter on a right-hand (odd) page and the outside
    margin on a left-hand one. That last term is what this measurement is for:
    a key laid out for the wrong side of the spread lands ``gutter - outside``
    away from it.

    The answer is the **widest** of the tiles in the page's left column — fill
    order is left to right, so those are the answers at even positions — since
    a wider grid is centred with less spare beside it and so reaches further
    left than its neighbours above and below.
    """
    tile_rows = capacity // 2
    tile_width = (USABLE_WIDTH_MM - ANSWER_TILE_GAP_MM) / 2
    heading_mm = ANSWER_HEADING_MM + ANSWER_TILE_GAP_MM if heading else 0.0
    tile_height = (
        ANSWER_USABLE_HEIGHT_MM - heading_mm - (tile_rows - 1) * ANSWER_TILE_GAP_MM
    ) / tile_rows
    left_margin = GUTTER_MM if page_number % 2 else OUTSIDE_MM

    def grid_left_mm(puzzle):
        columns, rows = puzzle["width"], puzzle["height"]
        cell = min(
            ANSWER_MAX_CELL_MM,
            tile_width / columns,
            (tile_height - ANSWER_CAPTION_MM) / rows,
        )
        return left_margin + max(tile_width - columns * cell, 0.0) / 2

    return min(grid_left_mm(puzzle) for puzzle in answers[0::2])


def _ink_left_px(page):
    """The x of the leftmost inked pixel of ``page``.

    On an answer page that is the leftmost grid of the left tile column: a
    caption is one short line of 3.5 mm type centred in its own tile, a level
    heading the same centred on the page, and the narrowest grid the key can
    print — 10 cells at the 5 mm cap, 50 mm — is wider than either and so
    starts further left.
    """
    box = page.convert("L").point(lambda value: 255 if value < 128 else 0).getbbox()
    assert box is not None, "the page carries no ink"
    return box[0]


def _expected_drawing_left_mm(puzzle, page_number, cell_mm=None):
    """Where interior page ``page_number`` puts this puzzle's left edge (FR-032).

    The drawing is ``clue depth + grid`` cells across at ``min(standard cell,
    page fit)``, centred across the usable width, whose left margin is the
    gutter on a right-hand (odd) page and the outside margin on a left-hand
    one. ``cell_mm`` overrides the cell with the pair's shared one when the
    puzzle is a slot of a two-up page (FR-040); its drawing is centred across
    the same usable width either way.
    """
    across = _across(puzzle)
    cell = (
        min(STANDARD_CELL_MM, USABLE_WIDTH_MM / across, USABLE_HEIGHT_MM / _down(puzzle))
        if cell_mm is None
        else cell_mm
    )
    spare = USABLE_WIDTH_MM - across * cell
    left_margin = GUTTER_MM if page_number % 2 else OUTSIDE_MM
    return left_margin + max(spare, 0.0) / 2


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


def _section_plan(puzzles):
    """The puzzle section: ``(page number, the puzzles on it)`` per page.

    The guide page is interior page 1, and then each non-empty **named** level
    opens with a divider page of its own (TERM-031, CARD-128) followed by that
    level's pages as :func:`_puzzle_page_plan` walks them. A run of puzzles
    whose stored tier is no level at all opens no divider — there is no name
    to print on one — so it simply follows the last named level.

    Returns the puzzle pages only; the dividers are counted by their absence
    from the numbering (:func:`_divider_pages`).
    """
    pages, page_number = [], 2
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


def _export_through_route(app, case):
    """(interior bytes, cover bytes, reported page count or None) for ``case``."""
    if case["route"] == "generator":
        export = BookPDFGenerator().export_book(
            case["puzzles"], case["title"], cover_image=case["cover"]
        )
        return export.interior.getvalue(), export.cover.getvalue(), export.interior_page_count

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
    if case["cover"] is not None:
        png = BytesIO()
        case["cover"].save(png, format="PNG")
        png.seek(0)
        client.post(
            f"/book/{book_id}/finalize",
            data={"cover": (png, "cover.png")},
            content_type="multipart/form-data",
        )

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
    return parts[0], parts[1], None


def test_PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage(admin_app):
    rng = random.Random(SEED)
    cases = [_random_case(rng, i) for i in range(CASES)]
    seen = Counter()

    for number, case in enumerate(cases):
        label = f"case {number} ({case['route']}, {len(case['puzzles'])} puzzles, cover={case['cover'] is not None})"
        interior_bytes, cover_bytes, reported = _export_through_route(admin_app, case)
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

        # Today's content with the cover gone: guide, the pages the puzzles
        # take (two-up pairing can make them fewer than the puzzles, FR-040),
        # divider, and the pages the packed answer key takes (FR-042).
        printed = _as_the_interior_prints_them(case)
        plan = _puzzle_page_plan(printed)
        section = _section_plan(printed)
        dividers = _divider_pages(printed)
        key = _answer_page_plan(printed)
        expected_count = 1 + dividers + len(plan) + (len(key) + 1 if n else 0)
        assert len(interior) == expected_count, label
        assert pdf_page_count(interior_bytes) == expected_count, label
        if reported is not None:
            assert reported == expected_count, label

        # Page 1 is the guide page, and no interior page is the cover.
        assert same_page(interior[0], _expected_guide(case["puzzles"])), label
        for page_number, page in enumerate(interior, start=1):
            assert not same_page(page, cover_page), f"{label}: page {page_number} is the cover"
            assert page.size == TRIM_PX, f"{label}: page {page_number} is not the trim"

        # Each page's parity is its 1-based position in the interior (CARD-116).
        # Measured off the page: a right-hand (odd) page carries the gutter
        # margin on its left, so its drawing sits further right than the same
        # drawing on a left-hand page, by gutter - outside.
        def _measured(page_number, puzzle, drawing, cell_mm=None):
            drawn_left_mm = drawing.left / PX_PER_MM
            expected_mm = _expected_drawing_left_mm(puzzle, page_number, cell_mm)
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
            for puzzle, drawing in zip(group, drawings):
                _measured(page_number, puzzle, drawing, shared)
            make_up = "two-up page" if len(group) == 2 else "single page"
            seen[make_up] += 1
            # Both slots of a two-up page are centred across the usable width
            # of *that page's* parity, so the make-up and the parity are
            # counted together and both combinations are required below.
            seen[f"{make_up} {'right-hand' if page_number % 2 else 'left-hand'}"] += 1

        # The same clause on the answer pages. A packed answer page carries no
        # full-page drawing to measure, so what is measured is its **leftmost
        # grid** — the leftmost ink on the page — against CARD-133's tiling
        # written out in this module. That tiling starts at the page's own
        # parity's left margin, which is the clause this loop is here for.
        for offset, (answers, capacity, heading) in enumerate(key):
            page_number = 3 + dividers + len(plan) + offset
            drawn_left_mm = _ink_left_px(interior[page_number - 1]) / PX_PER_MM
            expected_mm = _expected_answer_left_mm(
                answers, page_number, capacity, heading
            )
            assert abs(drawn_left_mm - expected_mm) < ANSWER_EDGE_TOLERANCE_MM, (
                f"{label}: answer page {page_number} "
                f"({'right' if page_number % 2 else 'left'}-hand) "
                f"starts its key at {drawn_left_mm:.3f} mm, not {expected_mm:.3f} mm"
            )
            seen["right-hand" if page_number % 2 else "left-hand"] += 1
            seen["answer page"] += 1
            seen[f"{capacity}-up answer page"] += 1
            if heading:
                seen["headed answer page"] += 1

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
    # The answer pages were measured too, at both of FR-042's tilings and with
    # a level heading, so the tile arithmetic above is exercised in every shape
    # it takes rather than only on the six-up page a small book happens to get.
    assert seen["answer page"] >= 20, seen
    assert seen["6-up answer page"] >= 5 and seen["4-up answer page"] >= 5, seen
    assert seen["headed answer page"] >= 10, seen


def test_page_numbers_start_at_one():
    """There is no interior page 0 — the cover is not a page of the interior."""
    with pytest.raises(ValueError):
        page_is_right_hand(0)
