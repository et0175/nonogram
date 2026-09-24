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
produce: the guide page, a level divider (TERM-031, CARD-128), a
single-puzzle page, a two-up page (FR-040), the SOLUTIONS divider and three
answer pages of the packed key (FR-042). Eleven interior pages, every one of
them a different kind of drawing. That is the
book :data:`BASELINE_FIXTURE` records, and the one AC-3 compares page for
page.

:func:`corpus_puzzles` is the **large** book — a seeded corpus of 150 puzzles
(no ``hypothesis``: stdlib ``random.Random``, per CLAUDE.md), grouped by tier
the way INV-009 groups a real book, each one too large for two-up pairing to
shorten the interior. It yields a 182-page interior: 1 guide + 3 level
dividers + 150 puzzle pages + the SOLUTIONS divider + 27 answer pages. That is
the "150-page book" AC-1 and AC-2 talk about, and it is a real export — the
page count is never faked.

**The same book, exported inside a capped child process.**
:func:`capped_export_report` exports :func:`corpus_puzzles` in whatever
process calls it, in either the streaming shape or the list shape this card
removed, and reports the page count it read back out of the file and the
process's own high-water resident set. ``tests/test_book_pdf_memory.py``
calls it in a fresh interpreter that has installed a memory cap first, which
is how AC-2's "under a memory cap that the current code fails" is executed
rather than derived. Both shapes are the production calls — ``export_interior``
and ``interior_pages`` — so the capped run exports the same book the
in-process measurements do.

**Determinism.** Nothing here reads a clock, a database or a dict whose order
is not fixed: the grids are computed, the ids and names are literals, the tiers
are positional, and the sizes come from a seeded ``Random`` drawn in a fixed
order. The one thing that is *not* fixed is the system font the guide page and
the divider are lettered in — ``book_pdf_generator`` asks Pillow for Arial and
falls back to its built-in face — so :func:`font_fingerprint` pins that too,
and the fixture carries it. A machine that letters those two pages differently
cannot be compared against a baseline recorded on one that does not **on those
two pages**; the other six are drawn in the bundled band face and Pillow's own
built-in one, so they are comparable on any machine, and the fixture names
which two are which (``font_dependent_pages``) rather than putting the whole
book's evidence behind one skip.
"""

from __future__ import annotations

import hashlib
import json
import random
import sys
import time
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

#: Where the recorded per-page evidence of the interior's pages lives.
#:
#: CARD-145's own fixture, recorded from the merge-base, is still beside it and
#: still unregenerated — but it no longer describes this book: CARD-128 made
#: the interior print grouped by level and open each level with a divider page
#: (INV-009, TERM-031), which is the one reason that fixture's ``warning``
#: allows a successor to be recorded. Both files carry the reasoning; this
#: constant names the current one.
BASELINE_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "book_baseline_card128.json"

#: How many pages the baseline book's interior holds, asserted by the tests
#: that use it so the corpus cannot silently shrink (CLAUDE.md). Eight until
#: CARD-128 gave its three levels a divider page each.
BASELINE_PAGE_COUNT = 11

#: How many puzzles the large corpus holds, and the interior that follows:
#: 1 guide + 3 level dividers + 150 puzzle pages + SOLUTIONS + 27 answer pages.
CORPUS_PUZZLE_COUNT = 150
CORPUS_PAGE_COUNT = 182


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

    **They are deliberately not in print order.** Since CARD-128 the book
    prints grouped easy, then medium, then hard (INV-009), so this list — hard
    first — exercises the grouping as well as the page kinds: the interior
    runs guide, "Easy", the two-up page, "Medium", the 15x15, "Hard", the
    30x30, SOLUTIONS, and one answer page per level. Eleven pages, three of
    them level dividers.

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
    per level — and, since CARD-128, the puzzle section three divider pages.
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


#: Every size the machine-face interior pages are lettered at: the guide
#: page's title (48) and its body text (28), and the SOLUTIONS divider's word
#: (60). The cover's 72 is deliberately absent: the cover is a separate file
#: and the interior baseline holds no page of it. One size is not enough,
#: because a face can differ at one size and agree at another (hinting, bitmap
#: strikes), and a fingerprint that agreed at 48 while the divider's 60
#: differed would let a page be compared that cannot be.
#:
#: **Hand-transcribed from three call sites, with nothing in the code tying
#: them together.** They are the three
#: ``ImageFont.truetype("/System/Library/Fonts/Arial.ttf", N)`` calls in
#: ``src/nonogram/admin/book_pdf_generator.py``:
#:
#: * ``create_guide_page`` — ``title_font``, size **48**
#: * ``create_guide_page`` — ``text_font``, size **28**
#: * ``create_divider_page`` — ``divider_font``, size **60**
#:
#: The sizes are integer literals at those call sites, not named constants, so
#: there is nothing to import; if one of them moves, this tuple has to be
#: re-derived by hand or the fingerprint stops covering the face those two
#: pages are really drawn in.
#:
#: **Editing this tuple is a baseline change, not a test tweak.** It is what
#: :func:`font_fingerprint` digests, so a changed tuple makes ``same_face``
#: false on every machine — which silently turns off the pixel comparison of
#: interior pages 1 and 5 *and* the whole byte-length assertion in
#: ``tests/test_book_pdf_memory.py``, with every test still green. That is
#: G-1 evidence disappearing without anyone touching
#: ``tests/fixtures/book_baseline_card145.json``, where the "NEVER regenerate"
#: warning lives. Treat a change here as a re-recording of the fixture: the
#: same justification, and the fixture's own ``font_fingerprint`` re-recorded
#: alongside it.
MACHINE_FACE_SIZES = (48, 28, 60)


def font_fingerprint() -> str:
    """A digest of the face the guide page and the divider are lettered in.

    ``book_pdf_generator`` asks Pillow for Arial by path and falls back to
    ``ImageFont.load_default()`` when it is not there, so those two pages'
    pixels depend on the machine. This draws the guide page's own title with
    the same call, at **each** of :data:`MACHINE_FACE_SIZES`, into a small
    image, and digests the three together: two machines with the same
    fingerprint letter those two pages identically, and two with different
    fingerprints cannot compare *those two pages* at all. The other six pages
    of the baseline book are lettered in the bundled face and in Pillow's own
    built-in one, so they are comparable everywhere — which is why the fixture
    records ``font_dependent_pages`` and the comparison skips only those.
    """
    digests: List[str] = []
    for size in MACHINE_FACE_SIZES:
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", size)
        except OSError:
            font = ImageFont.load_default()
        sample = Image.new("RGB", (900, 120), "white")
        ImageDraw.Draw(sample).text(
            (0, 0), "How to Use This Book", fill="black", font=font
        )
        digests.append(hashlib.sha256(sample.tobytes()).hexdigest())
    return hashlib.sha256(" ".join(digests).encode("ascii")).hexdigest()


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


# --------------------------------------------------------------------------
# The same book, exported inside a child process that is under a memory cap
# --------------------------------------------------------------------------
#
# AC-2 asks for "a 150-page book exports successfully under a memory cap that
# the current code fails". Both halves of that sentence want a *process* that
# a cap can kill, which is what these three shapes are for: a fresh
# interpreter installs the cap before it imports anything, then asks for one
# of them and reports what it cost. ``tests/test_book_pdf_memory.py`` runs the
# children and owns the cap's derivation; what lives here is only the work
# they do, so the capped run and the in-process run export the same book
# through the same two calls.

#: Import the stack, build one page, drop it, report. The **floor** a capped
#: child cannot go below on any platform: interpreter + PIL + numpy + the
#: corpus book + a single page bitmap. It is measured so a cap can be shown to
#: have room over the platform's own footprint rather than over a guess.
BASELINE_SHAPE = "baseline"

#: ``export_interior`` — the shape this card ships: no page survives the call
#: that builds the next one.
STREAMING_SHAPE = "stream"

#: ``interior_pages`` into a list, then written — the shape this card removed
#: from the export path and which :meth:`BookPDFGenerator.interior_pages` can
#: still produce for a caller that asks for it. This is "the current code" of
#: AC-2's second half, run rather than reasoned about.
MATERIALISED_SHAPE = "list"


def resident_bytes() -> int:
    """This process's high-water resident set, in bytes.

    ``ru_maxrss`` is bytes on Darwin and kibibytes on Linux — the one
    normalisation every reader of that field has to do. Imported inside the
    function because :mod:`resource` is POSIX-only and this module is imported
    by tests that have nothing to do with process memory.

    This is RSS, and ``tests/test_book_pdf_memory.py`` is explicit that RSS is
    not a number a test may *assert a shape on*. It is used only where it is
    the right instrument: as the quantity a process-level cap is enforced
    against, with orders of magnitude between the two outcomes it separates.
    """
    import resource

    used = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return used if sys.platform == "darwin" else used * 1024


def capped_export_report(shape: str) -> Dict[str, Any]:
    """Do ``shape``'s work in **this** process and report what it cost.

    Called in a child interpreter that has already installed a memory cap, so
    it deliberately catches nothing: a shape that cannot fit the cap must die
    or raise :class:`MemoryError` at the caller, which is the whole point of
    running it here rather than in the test process.

    The page count in the report is read back **out of the written PDF's page
    tree**, never taken from the page plan — a memory test must not fake a
    page count, and the capped run is the one most tempted to.
    """
    from nonogram.admin.book_pdf_generator import BookPDFGenerator
    from tests.helpers.pdf_pages import pdf_page_count

    imported = resident_bytes()
    generator = BookPDFGenerator(corpus_book())

    if shape == BASELINE_SHAPE:
        page = generator.create_guide_page(4, 2, 1, 1)
        page_bytes = page.width * page.height * len(page.mode)
        del page
        return {
            "shape": shape,
            "outcome": "drawn",
            "imported": imported,
            "page_bytes": page_bytes,
            "resident": resident_bytes(),
        }

    puzzles = corpus_puzzles()
    started = time.perf_counter()
    if shape == STREAMING_SHAPE:
        written = generator.export_interior(puzzles).getvalue()
    elif shape == MATERIALISED_SHAPE:
        pages = generator.interior_pages(puzzles)  # the shape this card removed
        written = generator._write_pdf(iter(pages), len(pages)).getvalue()
        del pages
    else:
        raise ValueError(f"unknown export shape: {shape!r}")

    return {
        "shape": shape,
        "outcome": "written",
        "imported": imported,
        "page_count": pdf_page_count(written),
        "file_bytes": len(written),
        "seconds": time.perf_counter() - started,
        "resident": resident_bytes(),
    }
