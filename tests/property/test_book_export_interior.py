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

    A book runs easy, then medium, then hard (FR-041, INV-009; CARD-126), so a
    submission whose tiers are drawn at random is *stored* grouped, and page
    ``2 + index`` holds the index-th puzzle of the grouped order. The
    ``generator`` route takes a list straight into ``export_book`` with no book
    behind it, so it prints what it was handed.

    This decides only *which* puzzle each page holds. What the assertions below
    are about — that the page's parity is its 1-based position in the interior
    — is untouched by it, and is still checked on every page.
    """
    if case["route"] == "generator":
        return list(case["puzzles"])
    return sorted(
        case["puzzles"], key=lambda p: _LEVEL.get(str(p["difficulty_tier"]).lower(), 3)
    )


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
        # divider, one answer page per puzzle.
        plan = _puzzle_page_plan(_as_the_interior_prints_them(case))
        expected_count = 1 + len(plan) + (n + 1 if n else 0)
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

        for offset, group in enumerate(plan):
            page_number = 2 + offset
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

        for index, puzzle in enumerate(_as_the_interior_prints_them(case)):
            page_number = 3 + len(plan) + index  # this puzzle's answer page
            _measured(page_number, puzzle, drawing_of(interior[page_number - 1]))

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


def test_page_numbers_start_at_one():
    """There is no interior page 0 — the cover is not a page of the interior."""
    with pytest.raises(ValueError):
        page_is_right_hand(0)
