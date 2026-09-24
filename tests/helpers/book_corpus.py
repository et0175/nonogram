"""The books CARD-145's memory tests export, built the same way every time.

CARD-145 changes *when* an interior page is released, never what is drawn on
it (G-1). Proving that needs the same book twice — once exported by the code
as it stood at the merge-base, recorded as a fixture of per-page digests, and
once by the streaming path — so the book's construction lives here rather than
in the test that compares the two. A book built twice from two copies of the
same literals is a book that can silently stop being the same book.

Two corpora, for two different questions:

:func:`baseline_puzzles` is the **small, complete** book — four puzzles that
between them make the interior hold one of every page kind the generator can
produce: the guide page, a single-puzzle page, a two-up page (FR-040), the
SOLUTIONS divider and three answer pages of the packed key (FR-042). Eight
interior pages, every one of them a different kind of drawing. That is the
book :data:`BASELINE_FIXTURE` records, and the one AC-3 compares page for
page.

:func:`corpus_puzzles` is the **large** book — a seeded corpus of 150 puzzles
(no ``hypothesis``: stdlib ``random.Random``, per CLAUDE.md), grouped by tier
the way INV-009 groups a real book, each one too large for two-up pairing to
shorten the interior. It yields a 179-page interior: 1 guide + 150 puzzle
pages + 1 divider + 27 answer pages. That is the "150-page book" AC-1 and
AC-2 talk about, and it is a real export — the page count is never faked.

**Determinism.** Nothing here reads a clock, a database or a dict whose order
is not fixed: the grids are computed, the ids and names are literals, the tiers
are positional, and the sizes come from a seeded ``Random`` drawn in a fixed
order. The one thing that is *not* fixed is the system font the guide page and
the divider are lettered in — ``book_pdf_generator`` asks Pillow for Arial and
falls back to its built-in face — so :func:`font_fingerprint` pins that too,
and the fixture carries it. A machine that letters those two pages differently
cannot be compared against a baseline recorded on one that does not.
"""

from __future__ import annotations

import hashlib
import json
import random
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Sequence

from PIL import Image, ImageDraw, ImageFont

from nonogram import clues
from nonogram.admin.book_manager import Book, BookMetadata

#: CON-018's Book 1 profile in millimetres, written out here rather than
#: imported, exactly as ``tests/test_book_pdf.py`` writes it out.
BOOK1_WIDTH_MM = 8.5 * 25.4
BOOK1_HEIGHT_MM = 11 * 25.4
GUTTER_MM = 0.5 * 25.4
OUTSIDE_MM = 0.375 * 25.4

#: Where the recorded per-page evidence of the merge-base's pages lives.
BASELINE_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "book_baseline_card145.json"

#: How many pages the baseline book's interior holds, asserted by the tests
#: that use it so the corpus cannot silently shrink (CLAUDE.md).
BASELINE_PAGE_COUNT = 8

#: How many puzzles the large corpus holds, and the interior that follows.
CORPUS_PUZZLE_COUNT = 150
CORPUS_PAGE_COUNT = 179


def _cm(millimetres: float) -> str:
    """A trim or margin as the ``books`` table stores it: centimetres, 2 dp."""
    return f"{millimetres / 10:.2f}"


def corpus_book(book_id: str = "card-145") -> Book:
    """A book on CON-018's Book 1 profile, with no custom puzzle titles.

    The same stored print specification both corpora are exported on, so a
    page's geometry is the book's and not a default that happened to agree
    with it.
    """
    return Book(
        book_id=book_id,
        metadata=BookMetadata(
            title="Winter Pictures",
            description="The book CARD-145's memory tests export.",
            theme="generic",
            target_audience="adults",
            size="",
            page_count=0,
        ),
        trim_width_cm=_cm(BOOK1_WIDTH_MM),
        trim_height_cm=_cm(BOOK1_HEIGHT_MM),
        gutter_margin_cm=_cm(GUTTER_MM),
        outside_margin_cm=_cm(OUTSIDE_MM),
    )


def _gutter_grid(columns: int, rows: int, depth: int) -> List[List[bool]]:
    """A grid whose row **and** column clues are exactly ``depth`` entries deep.

    The same construction ``tests/test_book_pdf.py`` uses: every other cell
    filled along both axes, stopped after ``depth`` runs, so a line that
    carries any ink carries ``depth`` isolated single cells.
    """
    limit = 2 * depth - 1
    if limit > min(columns, rows):
        raise ValueError(f"a {columns}x{rows} grid cannot carry {depth}-deep clues")
    return [
        [x % 2 == 0 and x < limit and y % 2 == 0 and y < limit for x in range(columns)]
        for y in range(rows)
    ]


def puzzle(
    puzzle_id: str,
    columns: int,
    rows: int,
    depth: int,
    tier: str,
    name: str,
) -> Dict[str, Any]:
    """One book puzzle, in the shape the review service hands the generator."""
    grid = _gutter_grid(columns, rows, depth)
    found = clues.compute_clues(grid)
    return {
        "id": puzzle_id,
        "grid": grid,
        "clues_rows": [list(clue) for clue in found.rows],
        "clues_cols": [list(clue) for clue in found.columns],
        "width": columns,
        "height": rows,
        "puzzle_name": name,
        "difficulty_tier": tier,
    }


def baseline_puzzles() -> List[Dict[str, Any]]:
    """Four puzzles whose interior holds one of every page kind.

    Puzzle 1 is a 30x30 Hard: far too large to pair, so it prints alone.
    Puzzles 2 and 3 are 10x10 Easies side by side, which is the one
    arrangement the pairing walk turns into a two-up page (FR-040). Puzzle 4
    is a 15x15 Medium, alone again because its neighbours' tiers differ.

    Three tiers in three runs also gives the packed answer key three pages,
    each opening a level (FR-042), behind the SOLUTIONS divider.
    """
    return [
        puzzle("card145-1", 30, 30, 9, "hard", "Snowflake"),
        puzzle("card145-2", 10, 10, 3, "easy", "Duck"),
        puzzle("card145-3", 10, 10, 3, "easy", "Owl"),
        puzzle("card145-4", 15, 15, 4, "medium", "Tree"),
    ]


def corpus_puzzles(
    count: int = CORPUS_PUZZLE_COUNT, seed: int = 145
) -> List[Dict[str, Any]]:
    """A seeded corpus of ``count`` puzzles, grouped by tier like a real book.

    Sizes are drawn from a seeded ``random.Random`` so the corpus is the same
    on every run and on every machine, and they are 18x18 or 20x20 with 6-deep
    clues — large enough that no two of them share a page however their tiers
    fall, so the interior's length is the puzzle count and not a verdict of the
    pairing walk. Tiers run Easy, then Medium, then Hard, which is the order
    INV-009 groups a book in and the order that gives the packed key one run
    per level.
    """
    if count < 3:
        raise ValueError(f"the corpus is grouped into three tiers, not {count}")
    rng = random.Random(seed)
    tiers = ["easy", "medium", "hard"]
    puzzles: List[Dict[str, Any]] = []
    for index in range(count):
        tier = tiers[index * len(tiers) // count]
        side = rng.choice((18, 20))
        puzzles.append(
            puzzle(f"card145-corpus-{index + 1}", side, side, 6, tier, f"Picture {index + 1}")
        )
    return puzzles


# --------------------------------------------------------------------------
# Per-page evidence
# --------------------------------------------------------------------------


def page_digest(page: Image.Image) -> Dict[str, Any]:
    """One page's identity: its size, its mode and its raw pixels' sha256.

    Digests rather than images, because a 2550x3300 RGB page is 25.2 MB and a
    fixture is not a place to keep eight of them. ``Image.tobytes`` is the
    decoded bitmap itself, so two pages with the same digest are the same page
    to the pixel — no tolerance, unlike ``pdf_pages.same_page``, which allows
    JPEG noise and would hide exactly the change this evidence exists to catch.
    """
    return {
        "size": list(page.size),
        "mode": page.mode,
        "sha256": hashlib.sha256(page.tobytes()).hexdigest(),
    }


def page_digests(pages: Sequence[Image.Image]) -> List[Dict[str, Any]]:
    """:func:`page_digest` for every page, in page order."""
    return [page_digest(page) for page in pages]


def font_fingerprint() -> str:
    """A digest of the face the guide page and the divider are lettered in.

    ``book_pdf_generator`` asks Pillow for Arial by path and falls back to
    ``ImageFont.load_default()`` when it is not there, so those two pages'
    pixels depend on the machine. This draws the guide page's own title with
    the same call, at the same size, into a small image, and digests it: two
    machines with the same fingerprint letter those pages identically, and two
    with different fingerprints cannot be compared page for page at all.
    """
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 48)
    except OSError:
        font = ImageFont.load_default()
    sample = Image.new("RGB", (900, 80), "white")
    ImageDraw.Draw(sample).text((0, 0), "How to Use This Book", fill="black", font=font)
    return hashlib.sha256(sample.tobytes()).hexdigest()


def load_baseline() -> Dict[str, Any]:
    """The recorded merge-base evidence, as it sits in the fixture file."""
    with BASELINE_FIXTURE.open(encoding="utf-8") as handle:
        return json.load(handle)


def export_of(generator, puzzles: Sequence[Dict[str, Any]]) -> bytes:
    """``generator``'s interior PDF for ``puzzles``, as bytes.

    One call, so the recorder and the test that checks against it cannot
    differ in how they asked for the file.
    """
    written: BytesIO = generator.export_interior(list(puzzles))
    return written.getvalue()
