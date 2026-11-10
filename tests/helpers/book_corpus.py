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
produce: the guide (CARD-201: 2 pages), a level divider (TERM-031, CARD-128), a
single-puzzle page, a two-up page (FR-040), the SOLUTIONS divider and the
answer section (FR-042). Since CARD-202 three of its puzzles (Duck, Owl,
Tree) qualify for packing (width<=15, height<=20) and pack onto two pages
(Duck+Owl 2-up, Tree alone 2-up), while the fourth (Snowflake, 30x30) still
gets CARD-198's own full page — three answer pages, not the four pages
CARD-198 alone would have drawn, and not the three pages the pre-CARD-198
packed key drew either (one per *level*, a different three). Twelve interior
pages in all (CARD-201: up from eleven — the guide's second page), still
every one of them a different kind of drawing. That is
the book :data:`BASELINE_FIXTURE` records, and the one AC-3 compares page for
page.

:func:`corpus_puzzles` is the **large** book — a seeded corpus of 150 puzzles
(no ``hypothesis``: stdlib ``random.Random``, per CLAUDE.md), grouped by tier
the way INV-009 groups a real book, each one too large for two-up pairing to
shorten the interior. Since CARD-201 it yields a roughly 306-page interior:
2 guide + 3 level dividers + 150 puzzle pages + the SOLUTIONS divider + 150
answer pages — one per puzzle, where the former packed key took only 27. That
is the "150-page book" AC-1 and AC-2 talk about, and it is a real export —
the page count is never faked.

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

**Determinism, and the host gate that is gone (CARD-221).** Nothing here reads
a clock, a database or a dict whose order is not fixed: the grids are computed,
the ids and names are literals, the tiers are positional, and the sizes come
from a seeded ``Random`` drawn in a fixed order. **Nor does anything read the
host's fonts any more.** Until CARD-221 the guide pages, the dividers and the
TOC were lettered in whatever Arial ``ImageFont.truetype`` found on the
machine, with Pillow's built-in face as a fallback, so those pages' pixels —
and, through the TOC's own row height, a book's page count and its printed KDP
gutter — were a function of the host. This module therefore carried a
``font_fingerprint()`` of that face over a hand-transcribed
``MACHINE_FACE_SIZES`` tuple, and every fixture carried the digest and the
list of pages a mismatched machine had to skip. All three are **removed**:
``_guide_face`` now returns the packaged DejaVu Sans
(``src/nonogram/export/fonts/``, ADR-0006/R1 package data) that the band and
the folio were already set in, so every page of this book is comparable on
any **host font configuration** — not on any machine: the pages are still
rasterised by the installed Pillow/FreeType, which ``pyproject.toml`` leaves
unbounded at ``>=10.0``, and catching a move in that is what the digest
comparison is for rather than something it is immune to (CARD-221's F-005).
``book_baseline_card221.json``'s own ``font_dependent_pages`` is empty.

The measurement that justifies removing them, rather than an argument that it
ought to be safe: ``tests/test_book_interior_face.py`` exports this same book
twice in one process — once with the host's Arial available, once with
``ImageFont.truetype`` made to refuse every host path — and finds every page's
digest, the page count and the chosen gutter band identical; and the
page-by-page comparison recorded in ``book_baseline_card221.json``'s
``why_a_new_baseline`` shows that exactly the seven pages lettered through
``_guide_face`` moved under that card and the other six are byte-identical to
CARD-205's digests. The **generated title cover** is deliberately outside this
helper's reach — the cover is a separate file, no baseline digests it, and
``MACHINE_FACE_SIZES`` never covered its size — and it asked the host for
Arial at 72 px until CARD-234 gave it the same packaged face, measured by
``tests/test_book_cover.py`` rather than from here.
"""

from __future__ import annotations

import hashlib
import json
import random
import sys
import time
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Sequence

from PIL import Image

from nonogram import clues
from nonogram.admin.book_manager import Book, BookMetadata

#: CON-018's Book 1 profile in millimetres, written out here rather than
#: imported, exactly as ``tests/test_book_pdf.py`` writes it out. The outside
#: margin moved 0.375 -> 0.5 in with the 2026-10-17 amendment (CARD-222), which
#: makes it equal to the gutter: the corpus book stores both, so a parity
#: assertion made on *this* book is an identity and not evidence that mirroring
#: works (CON-018's own note; `tests/test_book_page_frame.py` proves the
#: mirroring on a book with unequal stored margins instead).
BOOK1_WIDTH_MM = 8.5 * 25.4
BOOK1_HEIGHT_MM = 11 * 25.4
GUTTER_MM = 0.5 * 25.4
OUTSIDE_MM = 0.5 * 25.4

#: The one recorded baseline of the corpus book still read (CARD-206's: its
#: first page and its file metadata). The older recordings in the chain, and
#: the pixel-digest comparison against this one, were retired on 2026-11-09
#: when the owner's layout polish moved every page; git history keeps them.
BASELINE_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "book_baseline_card206.json"

#: The guide's own two interior pages, written out rather than derived from
#: the generator's own constants. Since CARD-206 reserved the blank title /
#: copyright page as interior page 1 (FR-043, INV-013 as amended 2026-10-17)
#: the guide follows it on pages **2 and 3** — a verso and a recto, which is
#: what lets the two pages face each other.
#:
#: ``BookPDFGenerator.create_guide_page`` takes an interior position and
#: counts which half of the tutorial to draw from ``TITLE_PAGE_COUNT``, so
#: these are the two numbers a test hands it when it wants the guide's first
#: and second page. Shared by the files that letter, measure and compare those
#: pages (``test_book_guide_page.py``, ``test_book_pdf_memory.py``; the raster
#: ``test_book_guide_page_type.py`` was retired by CARD-229), so a later
#: front-matter card moves them in one place.
GUIDE_INTERIOR_PAGES = (2, 3)

#: How many pages the baseline book's interior holds, asserted by the tests
#: that use it so the corpus cannot silently shrink (CLAUDE.md). Eleven until
#: CARD-198 took the packed answer key (three pages, one per level) to one
#: full solved page per puzzle (twelve); CARD-202 packed Duck+Owl and Tree
#: back onto two pages instead of three, back down to eleven; CARD-201 then
#: grew the guide from one page to two, back up to twelve; CARD-200 then
#: inserts a 1-page table of contents (this book's four puzzles fit Book 1's
#: own trim's TOC capacity with room to spare) immediately after the guide,
#: up to **thirteen**; CARD-206 then reserves the blank title / copyright
#: page as interior page 1, up to **fourteen**; the closing thank-you page
#: after the key (owner, 2026-11-10) takes it to **fifteen**.
BASELINE_PAGE_COUNT = 15

#: How many puzzles the large corpus holds, and the interior that follows:
#: 1 blank title page (CARD-206) + 2 guide (CARD-201) + **1** TOC page +
#: 3 level dividers + 150 puzzle pages
#: + SOLUTIONS + 150 answer pages (CARD-198: one per puzzle, where the
#: packed key took 27).
#:
#: The TOC term was 4 until CARD-205 (CARD-200 listed one row per puzzle:
#: 150 entries at Book 1's own ~43-entries-per-page capacity). CARD-205's
#: structural list is eight rows for this three-level corpus — the guide,
#: three headings with their ranges, the solutions — which is one page on
#: any trim, so this interior is three pages shorter than it was. Still
#: measured off ``book_pdf_generator``'s own
#: ``structural_toc_entry_count``/``_toc_entries_per_page`` rather than
#: guessed, and still asserted against the live page plan by the tests that
#: use it.
CORPUS_PUZZLE_COUNT = 150
CORPUS_TOC_PAGE_COUNT = 1
CORPUS_PAGE_COUNT = (
    1 + 2 + CORPUS_TOC_PAGE_COUNT + 3 + CORPUS_PUZZLE_COUNT + 1 + CORPUS_PUZZLE_COUNT
)


def _cm(millimetres: float) -> str:
    """A trim or margin as the ``books`` table stores it: centimetres, 2 dp."""
    return f"{millimetres / 10:.2f}"


def corpus_book(book_id: str = "card-145") -> Book:
    """A book on CON-018's Book 1 profile, with no custom puzzle titles.

    The same stored print specification both corpora are exported on, so a
    page's geometry is the book's and not a default that happened to agree
    with it.

    Its ``created_at`` is fixed (owner, 2026-11-09): interior page 1 now
    prints the copyright year from it, and a book stamped "now" would move
    that page's golden every New Year.
    """
    return Book(
        book_id=book_id,
        created_at=datetime(2026, 11, 9),
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
    30x30, SOLUTIONS, and the answer section. Since CARD-202, Duck and Owl
    (10x10) and Tree (15x15) all qualify for packing (width<=15, height<=20)
    while Snowflake (30x30) does not: Duck+Owl share one 2-up packed page,
    Tree packs onto its own 2-up page alone (its level has no other qualifying
    answer to join it), and Snowflake still gets CARD-198's full page — three
    answer pages, not four. Eleven pages in all, three of them level dividers.

    Four puzzles behind the SOLUTIONS divider, now three answer pages,
    is also no longer "the puzzle section's page count minus the two-up
    pairing, plus one": puzzles 2 and 3 (Duck, Owl) share both their *puzzle*
    page (FR-040) and, since CARD-202, their packed *answer* page — the one
    link between the two sections this book happens to exercise, though the
    two pairings are decided independently (INV-010's same-tier-neighbour
    rule for puzzle pages, CARD-202's qualifies-and-same-level rule for
    answer pages) and are not guaranteed to agree in general.
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
    INV-009 groups a book in and, since CARD-128, the order that gives the
    puzzle section three divider pages.
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


# CARD-221 removed ``MACHINE_FACE_SIZES`` and ``font_fingerprint()`` from this
# module. They existed because the guide pages, the dividers and the TOC were
# lettered in the **host's** Arial (CARD-146/CARD-147 built the mechanism;
# CARD-149 and CARD-200 re-derived the tuple as the sizes it transcribed
# moved), so a fixture's recorded pixels could only be compared on a machine
# whose face matched: the fingerprint was that face's digest at each size the
# pages asked for, and ``font_dependent_pages`` named the pages a mismatched
# machine skipped.
#
# The condition is measurably gone, not argued away: ``_guide_face`` returns
# the packaged DejaVu Sans, so every interior page is lettered from this
# repository's own package data, and
# ``tests/test_book_interior_face.py``'s
# ``TestBookInterior_GeometryIsIdenticalWithAndWithoutHostFonts`` exports this
# book with the host's Arial available and again with ``ImageFont.truetype``
# refusing every host path and finds every page's digest, the page count and
# the chosen gutter band identical. ``book_baseline_card221.json``'s
# ``font_dependent_pages`` is therefore empty, and nothing in the test tree
# gates on a face any more (``tests/test_book_toc.py``'s own
# ``_lettered_as_recorded`` went with it).
#
# Two things this removal deliberately does NOT claim. (1) The **generated
# title cover** is not covered from here at all: the cover is a separate
# file, INV-013 keeps it out of the interior, no baseline digests it, and
# this tuple never covered its size. It read the host's Arial at 72 px until
# CARD-234 — recorded in CARD-221's notes as work outside that card — and now
# letters from the same packaged face, which ``tests/test_book_cover.py``
# measures. (2) A puzzle page's clue digits come from Pillow's own embedded face
# rather than from this repository; that was always on the
# machine-independent side of this line (every predecessor fixture's own
# note), and it is a dependency's package data, not the host's.


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
    from nonogram.admin.book_interior_vector import interior_generator
    from tests.helpers.pdf_pages import pdf_page_count

    imported = resident_bytes()
    # CARD-322: through the assembly point, as production's writing site does.
    # This runs in a CHILD interpreter that imports the package afresh, so the
    # test tree's conftest rebind of the generator's default writer set is not
    # in force here, and a bare ``BookPDFGenerator(book)`` would refuse the
    # guide page (ADR-0042/R1, D8).
    generator = interior_generator(corpus_book())

    if shape == BASELINE_SHAPE:
        # The reference bitmap is a section divider: the interior's only page
        # that is still a full-size bitmap (CARD-322 -- the guide page this
        # used to draw is operators now).
        page = generator.create_divider_page(4)
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
        # CARD-147: written in the book's own interior colour space, so the
        # two shapes under the cap write the same file and differ only in when
        # they release a page.
        written = generator._write_pdf(
            iter(pages),
            len(pages),
            mode=generator.interior_bitmap_mode,
            # CARD-298: the list shape has no `InteriorStream` to read the
            # kinds off, so it asks the generator for the same plan the
            # streaming shape above writes from — the two shapes must write
            # the same file, which is this helper's whole point.
            kinds=generator.interior_stream(puzzles).page_kinds,
        ).getvalue()
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
