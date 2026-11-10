"""CARD-145 — the book PDF is written a page at a time (FR-041, FR-043, INV-013).

    AC (new)  TestBookPdfMemory_PeakDoesNotGrowWithPageCount
    AC (new)  TestBookPdfMemory_RealBookExportsUnderTheCap
    AC (new)  TestBookPdfMemory_TheBaselineBooksPages
    AC (new)  TestBookPdfMemory_InteriorAndCoverStillSeparate

CARD-237 adds the tests of this module's own memory tripwires — the four
``TestMemoryGuard_*`` classes beside the capped pair — after the headroom
assertion was found to be measuring the capped child's total resident set
(dominated by CPython's own footprint, and drifting with it) where it meant to
measure the export's marginal cost.

The defect: a book page is 2550 x 3300 px RGB — **25,245,000 bytes** — and the
export used to build every page into a list before writing any of them, so
peak memory was that figure times the page count. The deployed panel has
512 MB; a 20-page book already exceeded it and the worker was OOM-killed with
no traceback. This module measures that the shape is gone.

How memory is measured here, and why it is measured that way
-------------------------------------------------------------
:class:`LivePageBytes` counts **live page-bitmap bytes**: it registers every
page the export makes — the ones that pass the writer's producer and the ones
a page factory returns — against that page's ``width * height * len(mode)``
and a :mod:`weakref` that unregisters it the instant it dies, and samples the
sum of the pages still alive each time one is registered, which is the moment
a new page has just been built. CPython's refcounting makes "the
previous page is gone before the next is built" a fact the instrument observes
directly, not a sample it might miss, so the peak is exact and means the same
number on any machine.

The two obvious instruments were both tried and both rejected, with the
measurements that rejected them:

*Resident set size.* Allocator- and platform-dependent, and ``malloc`` rarely
returns freed pages to the OS, so the figure differs between this laptop and
any CI box and drifts with unrelated allocations. It does see Pillow's
buffers (four 2550 x 3300 RGB images moved ``ru_maxrss`` by 134 MB against
101 MB of bitmap) — it is just not a number a test can assert on.

*:mod:`tracemalloc`.* Blind to exactly the thing this card is about. Pillow
allocates image buffers in C, outside Python's allocator: the same four images
that cost 100,980,000 bytes of bitmap moved ``tracemalloc``'s traced total by
**35,421 bytes**, three parts in ten thousand. A memory test built on it would
pass on the old code too.

What the instrument is attached to
-----------------------------------
:func:`_measured` replaces ``BookPDFGenerator._write_pdf`` with one that
interposes the probe between the producer and the writer, then calls the real
export route (``export_interior``/``export_book``) — so what is measured is
the production path as a caller reaches it, not a hand-assembled imitation of
it.

The writer's seam alone would be **blind in one direction**, and that blindness
is the reason :data:`PAGE_FACTORIES` exists. A page that is built before the
writer is constructed and held across the whole write never passes the
producer, so a probe wrapped around the producer would never see it — a cover
rendered ahead of the interior and kept alive beside every page of it would
measure 1.00 page bitmaps and look perfect. So :func:`_measured` also wraps
every method that *returns* a whole page and registers what it returns.
Registration is idempotent (:meth:`LivePageBytes.track` keys on ``id(page)``),
so a page that is both built by a factory and passed through the writer is
counted once.
:meth:`TestBookPdfMemory_InteriorAndCoverStillSeparate.test_a_page_built_outside_the_writer_is_still_seen`
holds exactly that cover and measures 2.00, which is the non-vacuity proof for
the cover half of the bound.

The instrument is proved non-vacuous before it is trusted:
:meth:`TestBookPdfMemory_PeakDoesNotGrowWithPageCount.test_the_same_instrument_sees_the_old_shape_grow`
runs it over ``interior_pages`` — the list-returning API the export used to go
through, still present for the callers that want every page — and watches the
peak grow by one page bitmap per page. Same probe, same pages, same book: only
the shape differs.

What the measured peak is, and what it is not
----------------------------------------------
Every number this module asserts is about **the pages the panel retains**:
the probe sees a page when a ``BookPDFGenerator`` method returns it or hands
it to the writer, and it measures that no page survives the call that builds
the next one. That figure is **one page bitmap**, exactly, and it is the
property this card is about.

It is not the process's peak, and this module does not claim it is. Two other
terms are live at the same time, both measured:

* **COMP-007's transient second bitmap.** :meth:`~nonogram.admin.book_pdf_generator.BookPDFGenerator._blank_page`
  calls :func:`nonogram.export.pdf.render_pages`, which builds *two* full-size
  pages from one payload — the blank one and a solved one it has no use for
  — and binds ``blank, _ = render_pages(...)``, so the discarded page is
  alive until that frame returns. ``render_pages`` is a COMP-007 function,
  not a generator method, so it is outside :data:`PAGE_FACTORIES` by
  construction and the probe never sees it (a bespoke one-off probe wrapping
  ``render_pages`` itself, run once to produce the figures CARD-145 recorded
  here, measured a peak of 50,490,000 B — 2.00 page bitmaps — on the book
  of that time; CARD-198 changed only the *answer* section, which this
  transient term has nothing to do with, so the figure is unaffected by this
  card and was not re-run). It is a constant, not a per-page term: every
  puzzle page pays it, none of them accumulates it, and it is the
  merge-base's code untouched (G-1).
* **The written PDF.** It accumulates in the returned ``BytesIO`` at a
  measured ~0.38 MB per page on the 305-page corpus book (CARD-198: up from
  ~0.45 MB per page on the smaller 182-page corpus this figure was first
  measured against, each puzzle's own answer page now carrying real ink
  instead of a packed key sharing a tile's ink across several puzzles), so
  a 305-page interior holds 116,112,809 B of compressed output at the end
  — measured directly, not derived. That *is* a linear term, and
  :meth:`TestBookPdfMemory_RealBookExportsUnderTheCap.test_the_residual_linear_term_is_the_written_file_and_it_is_small`
  measures and states it rather than letting the module read as a claim of
  constant memory.

So the process's page-size envelope for the 305-page corpus book is **50.5 MB
of bitmap + 110.7 MB of file = 161.2 MB** (CARD-198: up from 132.3 MB on the
182-page book this module first measured, the file term growing with the
corpus — 31 % of the 512 MB instance on the same decimal-MB reading, still
comfortably inside it, and not the 25.2 MB a naive "one page bitmap" reading
of the bitmap-only assertions would suggest for the file term too.
Peak is **O(one retained page) + O(a transient constant) + O(the file)** —
the child-process resident-set range CARD-145 originally measured
end-to-end (150.8-169.9 MB over five runs, on the smaller corpus) was not
re-run for CARD-198's larger one; the shape of the claim — bounded, and
linear only in the file term — is what :class:`TestBookPdfMemory_RealBookExportsUnderTheCap`
still measures live, against the real 305-page book, on every run.

The medium (CARD-355, ADR-0042/R1 and R6)
-----------------------------------------
Everything above was written when every interior page was a bitmap. Once a
kind is written as operators the page is a
:class:`~nonogram.admin.book_vector.ContentStream` and has no bitmap, so the
memory claim is **re-expressed, not rasterised**:

* a page that is still a bitmap (the cover, the dividers) is costed in bytes
  exactly as before, and ``peak == one page bitmap`` keeps its teeth on it;
* an operators page costs **zero** bitmap bytes
  (:func:`bitmap_bytes_of`) and its retention is the medium-blind count
  :attr:`LivePageBytes.peak_pages`, asserted equal to one;
* nothing here asks poppler for a bitmap to measure
  (:class:`TestBookPdfMemory_TheMemoryClaimsDisposition`) -- a number measured
  that way would be a fact about poppler, not about the generator.

The pixel and byte comparisons against raster-era recordings are retired for
an operators page with a named survivor, determinism of the stream
(:class:`TestBookPdfMemory_AnOperatorsPageIsTheSameStreamEveryExport`), and the
"same content at a shifted position" comparisons draw their reference in the
medium the export used (``reference_*_page``). The figure this docstring's
history carried for the old shape's list ("202 MB") is retracted in
``test_the_same_instrument_sees_the_old_shape_grow``.

Cost: the corpus book is exported **once** for the whole module (a
module-scoped fixture), for a few seconds of real rendering and writing (up
somewhat since CARD-198, which gives every puzzle its own full answer page
instead of a shared packed tile); AC-2's executed cap adds three child
processes, and the whole file still runs well under a minute. The
150-puzzle book is never faked — a page count is the one thing a memory
test must not fake.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import os
import subprocess
import sys
import time
import tracemalloc
import weakref
from collections import Counter
from dataclasses import dataclass, field, replace
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple, Union

import numpy as np
import pytest
from PIL import Image

from nonogram.admin.book_answer_key import PACKED_FOUR_UP
from nonogram.admin.book_answer_key import PACKED_MAX_HEIGHT, PACKED_MAX_WIDTH
from nonogram.admin.book_pdf_generator import (
    BookPDFGenerator,
    PageKind,
    PageMedium,
    page_medium,
)
from nonogram.difficulty import Tier
from tests.helpers.book_corpus import (
    BASELINE_PAGE_COUNT,
    BASELINE_SHAPE,
    GUIDE_INTERIOR_PAGES,
    CORPUS_PUZZLE_COUNT,
    MATERIALISED_SHAPE,
    STREAMING_SHAPE,
    baseline_puzzles,
    corpus_book,
    corpus_puzzles,
    export_of,
    load_baseline,
    page_digests,
)
from nonogram.admin.book_vector import ContentStream, write_vector_pdf
from tests.helpers import pdf_pages as pdf_pages_module
from tests.helpers import pdf_vector
from tests.helpers.page_ink import (
    INK_LEVEL,
    drawing_of,
)
from tests.helpers.pdf_pages import pdf_page_count, pdf_pages, page_image, same_page

#: The deployed panel's memory envelope — the number this card exists to fit
#: inside, and the first one the project has stated (CARD-145's Architecture
#: context: "the deployed panel's memory envelope").
ENVELOPE_BYTES = 512 * 1024 * 1024

#: One Book 1 page at 300 DPI: 2550 x 3300 px, three bytes a pixel. Written
#: out rather than read off a page, so the test's arithmetic and the code's
#: are independent; :func:`test_one_page_costs_what_the_card_says` pins the
#: two together.
PAGE_BITMAP_BYTES = 2550 * 3300 * 3

#: What a streaming export **retains**, in page bitmaps: **exactly one**.
#:
#: This is the measured value, not a bound with room in it. The sample is
#: taken the moment a page is registered — which is the moment the *next* page
#: has just been built — and at that moment the page before it is already
#: gone, because every frame between the producer and the writer drops its
#: reference before the following page is built (``produce()``'s ``del page``,
#: :func:`~nonogram.admin.book_pdf_generator._as_planned`'s, the probe's own,
#: and — the load-bearing one — the ``del page`` in ``_write_pdf``'s loop,
#: whose loop variable is the only reference the other frames cannot drop).
#: Replacing any one of them raises the measured peak to exactly 2.00, so the
#: assertion is an equality: a cap of "at most two" is satisfied by the shape
#: this card exists to remove one ``del`` away from, and would not fail.
#: Measured stable at 1.00 on the 12-page book, on the 305-page book and on
#: ``export_book``'s two files, with and without the cycle detector.
#:
#: **"Retains" is the exact word, and it is narrower than "the process holds
#: one page bitmap at a time".** What this pins is that no page survives the
#: call that builds the next one — a property of the panel's own frames, and
#: the one that turned 4.52 GB into a constant. Inside a single puzzle-page
#: build the process does hold a second full-size bitmap: COMP-007's
#: ``render_pages`` returns a blank page and a solved page, and ``_blank_page``
#: keeps the discarded one until its frame exits. Registering both of them
#: measures a peak of **50,490,000 B = 2.00 page bitmaps** — on the 12-page
#: book (14 pages registered, re-measured for CARD-198: up from 13 on the
#: 11-page book this figure was first recorded against — the two extra
#: single-puzzle pages that call ``_blank_page`` are unchanged by this card,
#: only the answer section grew) and unchanged on the 305-page corpus one
#: (455 registered, re-measured; was 332 on the 182-page corpus), which is
#: what makes it a constant rather than a term that grows with the book. So
#: the honest *process* figure is two bitmaps; the
#: honest *retention* figure, and the only one an assertion in this module is
#: about, is one. The module docstring carries the numbers.
PEAK_IN_PAGES = 1

#: A second, looser line of defence, kept for the messages it produces and for
#: a shape that is wrong by more than one page. It is not what pins the
#: property — :data:`PEAK_IN_PAGES` is. In megabytes it is 50.5.
PEAK_CAP_IN_PAGES = 2

#: Every method of ``BookPDFGenerator`` that returns a whole book page.
#:
#: :func:`_measured` wraps each of these so the probe sees a page **at the
#: moment it is built**, not only if it passes the writer's producer. Without
#: that, a page built outside the writer and held across a write — which is
#: precisely the failure the cover half of the bound (failure matrix F-6) is
#: about — would be invisible to the instrument. The list is the drawing
#: methods, not the encoders: a method belongs here when it returns a page-size
#: :class:`PIL.Image.Image` a caller could hold.
PAGE_FACTORIES = (
    "create_cover_page",
    "create_divider_page",
    # CARD-311: the divider the interior walk actually asks for -- the owner's
    # uploaded picture fitted to the page, or the drawn page above. A page
    # factory in its own right (it builds the fitted bitmap itself).
    "divider_page",
    # The approved solutions mockup: the Solutions opener ``divider_page``
    # draws for the SOLUTIONS slot when no picture is stored (a rule,
    # "PUZZLES 1-N", "Solutions" and a blurb). It allocates a full-size
    # bitmap of its own, so it is wrapped like the drawn divider beside it.
    "create_solutions_opener",
    # The owner's 2026-11-09 polish: a level's divider in the opener's style
    # (rule, "PUZZLES a-b", the level's name, its dots), drawn by
    # ``divider_page`` for a level slot with no picture. Its own bitmap.
    "create_level_divider",
    # The puzzle, answer, guide, contents and title pages are operators
    # (ADR-0042); their raster writers were deleted on 2026-11-09.
)

#: The corpus book's interior, in pages, as this module counts it.
#:
#: ``tests.helpers.book_corpus.CORPUS_PAGE_COUNT`` still counts CARD-198's one
#: answer page per puzzle (308). Every corpus answer is within
#: ``PACKED_MAX_WIDTH`` x ``PACKED_MAX_HEIGHT``, so it packs ``PACKED_FOUR_UP`` to a page within its tier
#: (CARD-202's "always 4-up, 2-up only for a leftover"): ceil(50 / 4) = 13
#: pages for each of the three 50-puzzle tiers, 39 in all, and the interior is
#: 1 + 2 + 1 TOC + 3 dividers + 150 puzzle pages + SOLUTIONS + 39 + 1 closing
#: thank-you page (owner, 2026-11-10) = 198 pages.
#: Counted here, from the corpus's own sizes and the packing constants, rather
#: than in the shared helper (outside this module's edit), and still asserted
#: against the pages the export really draws and the file really holds.
_CORPUS_TIER_COUNTS = Counter(puzzle["difficulty_tier"] for puzzle in corpus_puzzles())
assert all(
    puzzle["width"] <= PACKED_MAX_WIDTH and puzzle["height"] <= PACKED_MAX_HEIGHT
    for puzzle in corpus_puzzles()
), "a corpus answer no longer packs: re-derive CORPUS_PAGE_COUNT"
CORPUS_ANSWER_PAGE_COUNT = sum(
    -(-count // PACKED_FOUR_UP) for count in _CORPUS_TIER_COUNTS.values()
)
CORPUS_PAGE_COUNT = (
    1 + 2 + 1 + len(_CORPUS_TIER_COUNTS) + CORPUS_PUZZLE_COUNT + 1 + CORPUS_ANSWER_PAGE_COUNT
    + 1  # the closing thank-you page (owner, 2026-11-10)
)

#: The book title the cover file carries (AC-4).
BOOK_TITLE = "Winter Pictures"


#: The side, in device pixels, of the square of solid ink a page must hold for
#: :func:`solid_ink_blocks` to call it filled. A filled answer cell on the
#: baseline book's smallest answer page is 37.7 px across, and the thickest
#: thing a blank puzzle page draws is a heavy grid rule a few pixels wide, so
#: 20 sits with a factor of nearly two of clearance either side: measured, the
#: baseline's three answer pages hold 40,598, 34,972 and 30,621 such squares
#: and its other five pages hold none at all.
FILLED_CELL_PROBE = 20


def solid_ink_blocks(page: Image.Image, side: int = FILLED_CELL_PROBE) -> int:
    """How many ``side`` x ``side`` squares of ``page`` are ink all the way through.

    What tells an answer page from a blank puzzle page by looking at it: a
    revealed solution fills whole cells, and nothing else the interior draws —
    a rule, a clue digit, a band's lettering, a divider's word — is solid over
    a square that wide. Measured off the page's own pixels, with nothing asked
    of the generator.

    A summed-area table over the ink mask, so every position is tested in one
    pass rather than 8 million crops.
    """
    ink = (np.asarray(page.convert("L")) < INK_LEVEL).astype(np.int64)
    totals = np.pad(ink.cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    square = (
        totals[side:, side:]
        - totals[:-side, side:]
        - totals[side:, :-side]
        + totals[:-side, :-side]
    )
    return int((square == side * side).sum())


class ReadInterior(List[Image.Image]):
    """The pages of one file as bitmaps, and the medium each was WRITTEN in.

    ``media[i]`` is what the file says page ``i`` is (``pdf_vector.page_media``),
    kept beside the bitmap because the bitmap alone cannot say: a poppler
    render of operators and a JPEG decode are both an ``Image``. A comparison
    against a stored raster-era digest needs to know which it holds.
    """

    media: List[str]


def interior_pages_of(data: bytes) -> ReadInterior:
    """Every page of ``data`` as the bitmap it draws, with the medium each was WRITTEN in.

    ``tests.helpers.pdf_pages.pdf_pages`` reads the pages; this adds
    ``pdf_vector.page_media`` (default-DENY: a page that is neither raster nor
    vector is a failure), read off the FILE and never inferred from a kind, so
    the same call is right on the unlifted tree (every page raster) and on the
    lifted one.

    CARD-355 history, kept because the number matters: before this card the
    shared reader returned page 1's render for every operators page after the
    first (``rendered_page`` read back ``sorted(glob("page-*.png"))[0]`` (PNG
    then, PGM since CARD-415) from a scratch directory shared across pages).
    Measured on the baseline book under
    the five-kind lift -- 4 raster pages (the dividers) and 10 operators pages
    -- the 9 operators pages after the first (page 1 itself was right: it is the
    blank title page) all came back as that blank render, 0 ink each. This
    module carried a reader of its own while the helper was defective; the
    helper is fixed (SCOPE+ ``tests/helpers/pdf_vector.py``) and
    :class:`TestBookPdfMemory_TheSharedReaderReadsEachPageForItself` holds it.
    """
    media = pdf_vector.page_media(data)
    unclassified = [
        n
        for n, m in enumerate(media, 1)
        if m not in (pdf_vector.RASTER, pdf_vector.VECTOR)
    ]
    assert not unclassified, f"pages {unclassified} are neither raster nor vector"
    images = ReadInterior(pdf_pages(data))
    images.media = media
    assert len(images) == len(media)
    return images


def _is_vector(kind: PageKind) -> bool:
    return page_medium(kind) is PageMedium.VECTOR


def reference_guide_page(generator: BookPDFGenerator, page_number: int) -> Image.Image:
    """The 4-puzzle baseline book's guide page ``page_number``, as the assembled
    guide writer draws it, rendered from its own one-page file."""
    return page_image(
        generator.pages.guide(
            generator.page_spec(page_number),
            generator.dpi,
            page_number,
            puzzle_count=4,
            easy_count=2,
            medium_count=1,
            hard_count=1,
        )
    )


#: The baseline book's fifteen interior pages, by kind, written out by hand
#: (CARD-355): the title page, the two guide pages, the TOC, "Easy", the
#: two-up page, "Medium", the 15x15, "Hard", the 30x30, SOLUTIONS, the
#: three answer pages and the closing thank-you page (owner, 2026-11-10).
#: Which medium each page is WRITTEN in is read off the
#: file (``pdf_vector.page_media``) and must equal what ``page_medium``
#: declares for the kind (ADR-0039/R2).
BASELINE_PAGE_KINDS = (
    PageKind.TITLE, PageKind.GUIDE, PageKind.GUIDE, PageKind.TOC,
    PageKind.DIVIDER, PageKind.PUZZLE, PageKind.DIVIDER, PageKind.PUZZLE,
    PageKind.DIVIDER, PageKind.PUZZLE, PageKind.DIVIDER,
    PageKind.ANSWER, PageKind.ANSWER, PageKind.ANSWER,
    PageKind.CLOSING,
)


def declared_media_of_the_baseline() -> List[str]:
    """``BASELINE_PAGE_KINDS`` read through the generator's own registry."""
    return [
        pdf_vector.VECTOR if _is_vector(kind) else pdf_vector.RASTER
        for kind in BASELINE_PAGE_KINDS
    ]


# --------------------------------------------------------------------------
# The instrument
# --------------------------------------------------------------------------


#: A book page as this tree hands one around (CARD-355): the bitmap a raster
#: page is, or the operators a vector page is.
Page = Union[Image.Image, ContentStream]


def bitmap_bytes_of(page: Page) -> int:
    """The bitmap ``page`` holds, in bytes -- **zero for operators**.

    This is the whole of CARD-355's disposition of the memory claim, as code
    rather than as a comment: a :class:`~nonogram.admin.book_vector.ContentStream`
    is a list of operator strings and has no bitmap, so there is nothing for
    "peak page-bitmap memory" to measure about it, and the instrument says so
    instead of rasterising it. The alternative -- ``interior_images`` /
    ``page_image`` -- would hand the probe a bitmap *poppler* produced, and the
    number would be a fact about poppler.
    :meth:`TestBookPdfMemory_TheMemoryClaimsDisposition.test_the_probe_never_asks_poppler_for_a_bitmap`
    holds the line.

    Default-deny (ADR-0039/R2): a page of any other type is refused, so a
    third medium cannot be costed at zero by omission.
    """
    if isinstance(page, Image.Image):
        return page.width * page.height * len(page.mode)
    if isinstance(page, ContentStream):
        return 0
    raise TypeError(
        f"a book page is a bitmap or a content stream; {type(page).__name__} "
        "is neither, and costing it at zero would hide it from the bound"
    )


@dataclass
class LivePageBytes:
    """How many bytes of **registered** page bitmap are alive at once, exactly.

    "Registered" is the whole qualification: this counts the pages it is shown
    — those a :data:`PAGE_FACTORIES` method returns and those that pass the
    writer's producer — and nothing else. A page-size bitmap built and dropped
    inside a call it is never shown, such as the solved page COMP-007's
    ``render_pages`` discards, is outside the total by construction. That makes
    this an instrument for what the panel **retains**, which is the property
    this card is about; the module docstring carries the process figure.

    :meth:`watch` sits between a page producer and whatever consumes it. Each
    page that goes past is costed at ``width * height * len(mode)`` — the
    bitmap Pillow holds for it — and registered against a
    :func:`weakref.finalize` that removes it the instant the last reference to
    that page goes away. The sum of what is still registered, sampled whenever
    a new page arrives, is the live total; :attr:`peak` is the largest such
    sample.

    It holds no page itself: the loop in :meth:`watch` deletes its own
    reference after yielding, so the instrument cannot be the thing that keeps
    a page alive and cannot make a streaming export look like a buffering one.

    :meth:`track` may also be called directly — :func:`_measured` calls it on
    what every page factory returns, so a page that never passes a producer is
    still costed. Registration is therefore **idempotent**: the key is
    ``id(page)``, so the same live page registered twice is one entry, and a
    page can only be released once. (An id is unique among *live* objects, and
    the finalizer has removed a dead page's entry before its id can be
    reused.)

    Attributes:
        peak: The largest live total seen, in bytes **of bitmap** (zero for an
            operators page, :func:`bitmap_bytes_of`).
        peak_pages: The largest number of registered pages alive at once, of
            either medium (CARD-355).
        seen: How many distinct pages were registered — a corpus-size guard,
            so a test cannot pass by measuring a book that was never built.
        bitmaps_seen, streams_seen: ``seen`` split by medium.
        page_bytes: The largest single page's cost, for the arithmetic that
            derives the old shape's peak from a measured constant rather than
            from a hard-coded one.
    """

    peak: int = 0
    seen: int = 0
    page_bytes: int = 0
    #: CARD-355: the largest number of registered pages alive at once, **in
    #: either medium**. ``peak`` is a quantity of bitmap and a content-stream
    #: page has none (:func:`bitmap_bytes_of`), so under ADR-0042/R1 the
    #: retention of an operators page is only visible as a count.
    peak_pages: int = 0
    bitmaps_seen: int = 0
    streams_seen: int = 0
    _live: Dict[int, int] = field(default_factory=dict)

    def watch(self, pages: Iterable[Page]) -> Iterator[Page]:
        """``pages``, costed as they go past and released immediately after."""
        for page in pages:
            self.track(page)
            yield page
            del page

    def track(self, page: Page) -> None:
        """Register one page and re-sample the live totals."""
        key = id(page)
        if key in self._live:  # already registered, and still alive
            return
        cost = bitmap_bytes_of(page)
        self._live[key] = cost
        weakref.finalize(page, self._live.pop, key, None)
        self.seen += 1
        if isinstance(page, Image.Image):
            self.bitmaps_seen += 1
        else:
            self.streams_seen += 1
        self.page_bytes = max(self.page_bytes, cost)
        self.peak = max(self.peak, sum(self._live.values()))
        self.peak_pages = max(self.peak_pages, len(self._live))

    @property
    def peak_in_pages(self) -> float:
        """The peak as a number of page bitmaps — the unit the defect is in."""
        return self.peak / self.page_bytes if self.page_bytes else 0.0


@dataclass(frozen=True)
class MeasuredExport:
    """One export, with what it cost: what it returned, the probe, the clock.

    ``data`` is whatever the export route returned — the interior's ``bytes``
    for :func:`~tests.helpers.book_corpus.export_of`, a
    :class:`~nonogram.admin.book_pdf_generator.BookExport` for
    ``export_book`` — so a measured call is the same call, not a narrowed one.
    """

    data: Any
    probe: LivePageBytes
    seconds: float


def _measured(export) -> MeasuredExport:
    """Run ``export()`` with the probe on the real export path, twice over.

    Two seams, because one of them alone has a blind spot:

    ``BookPDFGenerator._write_pdf`` is the seam every export goes through —
    ``export_interior``, ``export_cover`` and ``export_book`` all hand it a
    page producer and a page count — so wrapping its producer measures what a
    route really does with the pages it writes.

    :data:`PAGE_FACTORIES` are the methods that *build* a page. They are
    wrapped too, because a page built before the writer exists and held across
    the write never passes that producer: the writer's seam would measure it
    as absent. With both, a page is registered whichever way it comes into
    existence, and :meth:`LivePageBytes.track`'s ``id``-keyed registry makes
    the overlap free — the ordinary case, where a factory's page is yielded
    straight to the writer, is one entry and one release.

    The class is restored whether or not the export raised.
    """
    probe = LivePageBytes()
    original = BookPDFGenerator._write_pdf
    factories = {name: getattr(BookPDFGenerator, name) for name in PAGE_FACTORIES}

    def patched(self, pages, page_count, **kwargs):
        # ``**kwargs`` carries CARD-147's required ``mode=`` through unread:
        # which colour space the file is written in is none of the probe's
        # business, and swallowing it here would make a measured interior
        # export write a different file from an unmeasured one.
        return original(self, probe.watch(pages), page_count, **kwargs)

    def tracking(drawn):
        def wrapper(self, *args, **kwargs):
            page = drawn(self, *args, **kwargs)
            if isinstance(page, (Image.Image, ContentStream)):
                probe.track(page)
            return page

        return wrapper

    BookPDFGenerator._write_pdf = patched
    for name, drawn in factories.items():
        setattr(BookPDFGenerator, name, tracking(drawn))
    try:
        started = time.perf_counter()
        data = export()
        elapsed = time.perf_counter() - started
    finally:
        BookPDFGenerator._write_pdf = original
        for name, drawn in factories.items():
            setattr(BookPDFGenerator, name, drawn)
    return MeasuredExport(data=data, probe=probe, seconds=elapsed)


@pytest.fixture(scope="module")
def corpus_export() -> MeasuredExport:
    """The 150-puzzle book, exported end to end once for the whole module.

    A real export of a real book: 150 puzzles, none of which pairs two-up, so
    the interior is 1 guide + 3 dividers + 150 puzzle pages + 1 SOLUTIONS
    divider + 150 answer pages (CARD-198: one per puzzle, where the former
    packed key took 27) = :data:`~tests.helpers.book_corpus.CORPUS_PAGE_COUNT`
    (305) pages of 25.2 MB bitmap each. A few seconds; shared, because two
    tests need it and neither needs its own copy.
    """
    return _measured(
        lambda: export_of(BookPDFGenerator(corpus_book()), corpus_puzzles())
    )


@pytest.fixture(scope="module")
def small_export() -> MeasuredExport:
    """The baseline book (:data:`BASELINE_PAGE_COUNT` pages), exported the same way, for comparison."""
    return _measured(
        lambda: export_of(BookPDFGenerator(corpus_book()), baseline_puzzles())
    )


# --------------------------------------------------------------------------
# The instrument's own coverage
# --------------------------------------------------------------------------


class TestBookPdfMemory_TheInstrumentWrapsEveryPageFactory:
    """:data:`PAGE_FACTORIES` is complete, and stays complete.

    The list is six hand-written method names. A page-returning method added
    later — CARD-128's divider work is the next one due in this module — and
    left out of it would be **invisible** to the factory seam: a caller that
    built its page ahead of a write and held it across one would measure a
    perfect 1.00 and the cover half of the bound (failure matrix F-6) would
    silently stop being measured. Nothing about the instrument notices that,
    so it is asserted here instead of trusted.

    The premise the assertion rests on is that every page factory is
    annotated ``-> Image.Image``. All six are, and a seventh written in the
    same house style will be; one that is not would have to be added to
    :data:`PAGE_FACTORIES` by hand anyway, and this test's own message is
    where a reader is told so.
    """

    def test_every_page_returning_method_is_in_page_factories(self):
        annotated = {
            name
            for name, member in vars(BookPDFGenerator).items()
            if callable(member)
            and _returns_a_page(member)
        }

        assert annotated, (
            "no method of BookPDFGenerator is annotated '-> Image.Image' any "
            "more — the premise PAGE_FACTORIES is checked against is gone, "
            "and the list must be re-derived by hand"
        )
        assert annotated == set(PAGE_FACTORIES), (
            "PAGE_FACTORIES and the page-returning methods have drifted: "
            f"not wrapped by the instrument = {sorted(annotated - set(PAGE_FACTORIES))}, "
            f"listed but no longer a page factory = {sorted(set(PAGE_FACTORIES) - annotated)}. "
            "A page factory outside the instrument is a page the cover half "
            "of the bound (F-6) cannot see being held."
        )


def _returns_a_page(member: Any) -> bool:
    """Whether ``member``'s return annotation is :class:`PIL.Image.Image`."""
    try:
        annotation = inspect.signature(member).return_annotation
    except (TypeError, ValueError):
        return False
    return annotation is Image.Image or annotation in ("Image.Image", "Image")


# --------------------------------------------------------------------------
# AC-1 — peak does not grow with the page count
# --------------------------------------------------------------------------


class TestBookPdfMemory_PeakDoesNotGrowWithPageCount:
    """A 305-page book's peak page-bitmap memory is a small book's peak.

    "Within a small constant" is stated in **page bitmaps**, not megabytes,
    because a page bitmap is the unit the defect was measured in: the old
    shape's peak was one page bitmap per page, and what this asserts is that
    the difference between a 305-page book (CARD-198: up from 182, since the
    answer section now takes one page per puzzle instead of a packed tile)
    and a 12-page one is under one.

    Non-growth is necessary and not sufficient, and this class asserts both
    halves: a shape that held a *constant* two pages would not grow with the
    page count either, and is one missing ``del`` away — so the peak is also
    pinned to its exact measured value, one page bitmap (:data:`PEAK_IN_PAGES`).
    """

    def test_one_page_costs_what_the_card_says(self, small_export):
        """The premise, measured twice over: a Book 1 page is 25,245,000 bytes.

        Once off the live page the probe costed, and once off the page the
        merge-base recorded in the baseline fixture — two sources for the same
        number, neither of them this module's own arithmetic.
        """
        assert small_export.probe.page_bytes == PAGE_BITMAP_BYTES

        recorded = load_baseline()["pages"][0]
        width, height = recorded["size"]
        assert recorded["mode"] == "RGB"
        assert width * height * len(recorded["mode"]) == PAGE_BITMAP_BYTES

    def test_a_big_books_peak_is_a_small_books_peak(self, small_export, corpus_export):
        small, big = small_export.probe, corpus_export.probe

        assert small.seen == BASELINE_PAGE_COUNT
        assert big.seen == CORPUS_PAGE_COUNT
        # 13x since the packing limit was raised (198 pages against 15); it
        # was 16x while every corpus answer took a page of its own (308).
        assert big.seen > 13 * small.seen, "the two books must differ in size"
        assert big.peak == small.peak, (
            f"{big.seen} pages peaked at {big.peak_in_pages:.2f} page bitmaps, "
            f"{small.seen} pages at {small.peak_in_pages:.2f}"
        )
        # CARD-355: and in the medium-blind unit, which is the only one an
        # operators page is visible in.
        assert big.peak_pages == small.peak_pages, (
            f"{big.seen} pages peaked at {big.peak_pages} live pages, "
            f"{small.seen} pages at {small.peak_pages}"
        )

    def test_neither_book_holds_more_than_one_page_bitmap(
        self, small_export, corpus_export
    ):
        """The retained peak is exactly one page bitmap — an equality, not a cap.

        A cap of two is what "at most one page is retained" looks like when
        the writer's loop variable is still bound while the next page is
        built, which is the shape this card removes: it measures 2.00 exactly,
        so an assertion of ``<= 2`` passes on it. The equality is the one with
        teeth; the cap is kept beside it for the second line of defence and
        for the message.

        What is being measured is the pages the **panel** holds across a page
        boundary, not the process's page-size bitmaps: COMP-007's
        ``render_pages`` holds a second one transiently inside a puzzle-page
        build, outside :data:`PAGE_FACTORIES` and so outside this number. It
        is a constant and does not change what this asserts; see
        :data:`PEAK_IN_PAGES`.
        """
        for export in (small_export, corpus_export):
            probe = export.probe
            assert probe.peak <= PEAK_CAP_IN_PAGES * PAGE_BITMAP_BYTES, (
                f"{probe.seen} pages peaked at "
                f"{probe.peak_in_pages:.2f} page bitmaps"
            )
            assert probe.peak == PEAK_IN_PAGES * PAGE_BITMAP_BYTES, (
                f"{probe.seen} pages peaked at {probe.peak_in_pages:.2f} page "
                f"bitmaps, not {PEAK_IN_PAGES:.2f} — a page is being held "
                "across the call that builds the next one"
            )
            # CARD-355: the same equality for the pages of EITHER medium. A
            # content-stream page holds no bitmap, so the byte equality above
            # cannot see one being held; the count can.
            assert probe.peak_pages == PEAK_IN_PAGES, (
                f"{probe.seen} pages peaked at {probe.peak_pages} live pages, "
                f"not {PEAK_IN_PAGES} -- a page (of either medium) is being "
                "held across the call that builds the next one"
            )

    def test_the_same_instrument_sees_the_old_shape_grow(self):
        """Verify by revert: the probe measures the list shape as linear.

        The claim "peak does not grow with the page count" is only worth
        anything if the instrument would have said otherwise about the code
        this card replaced. ``interior_pages`` is still that shape — it returns
        every page in a list — so the same probe, over the same pages of the
        same book, is run across it here: the peak rises by exactly one page
        bitmap per *bitmap* page (25.2 MB each, the growth the panel was killed
        by), and the live page count by one per page in either medium.

        This is the one test in the module that deliberately holds the old
        shape's whole cost — every page of the baseline book at once. CARD-355
        RETRACTS the figure this paragraph used to carry ("202 MB" of live
        bitmap, predating CARD-128's level dividers): it was never
        re-derived, and under ADR-0042/R1 it is not one number -- it is
        ``PAGE_BITMAP_BYTES`` times however many of the book's pages are still
        bitmaps, which this test counts by ``isinstance`` instead of
        quoting. That is the point of it, and it is also
        why it is run on the twelve-page book and never on the 305-page one
        (CARD-198: up from 182), whose list would be 7.70 GB.
        """
        pages = BookPDFGenerator(corpus_book()).interior_pages(baseline_puzzles())
        assert len(pages) == BASELINE_PAGE_COUNT

        # CARD-355 / ADR-0042/R6: the pages arrive in whichever medium their
        # kind declares, and they are costed AS THEY ARE -- a bitmap by its
        # own size, operators by nothing -- never rasterised first. The count
        # of bitmaps is read here by ``isinstance``, a second reading that
        # shares no code with the probe's own costing.
        is_bitmap = [isinstance(page, Image.Image) for page in pages]
        assert all(
            isinstance(page, (Image.Image, ContentStream)) for page in pages
        ), "a page that is neither medium would be costed at nothing"

        probe = LivePageBytes()
        peaks = []
        live = []
        for page in pages:  # the list still holds every one of them
            probe.track(page)
            peaks.append(probe.peak)
            live.append(probe.peak_pages)

        # Retention, in the medium-blind unit: the list holds every page, so
        # the live count rises by exactly one per page, bitmap or operators.
        assert live == list(range(1, BASELINE_PAGE_COUNT + 1)), live
        # Bytes, in the unit the defect was measured in: one page bitmap per
        # *bitmap* page, nothing for an operators page.
        assert peaks == [
            sum(is_bitmap[: n + 1]) * PAGE_BITMAP_BYTES
            for n in range(BASELINE_PAGE_COUNT)
        ], peaks
        assert probe.peak == sum(is_bitmap) * PAGE_BITMAP_BYTES
        assert probe.bitmaps_seen == sum(is_bitmap)
        assert probe.streams_seen == BASELINE_PAGE_COUNT - sum(is_bitmap)
        assert sum(is_bitmap) >= 1, "the book's dividers are bitmaps in either tree"


class TestBookPdfMemory_TheMemoryClaimsDisposition:
    """CARD-355 / ADR-0042/R6 -- what happens to "peak page-bitmap memory" once
    a page is operators, DECIDED AND ASSERTED.

    **Disposition: re-expressed, in two halves, and never measured through a
    rasteriser.**

    1. *Bitmaps stay bytes.* A page that is still a bitmap (the cover, the
       dividers) is costed exactly as before, by its own width x height x
       channels, and the exact equality ``peak == one page bitmap`` keeps its
       teeth on those pages.
    2. *Operators are retention, not bytes.* A
       :class:`~nonogram.admin.book_vector.ContentStream` has no bitmap, so
       its bitmap cost is **zero** (:func:`bitmap_bytes_of`) and the claim
       about it becomes the medium-blind one: no page of either medium
       survives the call that builds the next, ``peak_pages == 1``.

    **What was refused, and the measurement behind it.** Wrapping the old-shape
    test's ``interior_pages`` list in ``interior_images`` would have made the
    probe count 25.2 MB bitmaps that *poppler* drew for pages the generator
    drew as a few hundred operator strings; the asserted number would then be
    a fact about poppler. The first test below runs the probe with the
    rasteriser wired to raise, so that substitution cannot be made without
    this class going red; the second proves the tripwire is live.

    **What survives of the process-level claim.** The capped-child tests in
    :class:`TestBookPdfMemory_RealBookExportsUnderTheCap` are fresh
    interpreters and do not inherit a ``-p`` lift, so they measure the
    tree as it is committed; that is stated here rather than assumed.
    """

    @pytest.fixture
    def rasteriser_is_wired_to_raise(self, monkeypatch):
        class Rasterised(Exception):
            """Something asked poppler for a bitmap."""

        def refuse(*args, **kwargs):
            raise Rasterised("a page was rasterised by poppler")

        monkeypatch.setattr(pdf_vector, "rendered_page", refuse)
        monkeypatch.setattr(pdf_pages_module.pdf_vector, "rendered_page", refuse)
        return Rasterised

    @staticmethod
    def _a_content_stream() -> ContentStream:
        # CARD-355 review F-002: NOT empty. An empty stream costs zero under
        # any costing (``len(operators)`` included), so a control on it could
        # not tell the disposition from a probe that prices operators.
        stream = ContentStream(width_px=2550, height_px=3300, dpi=300)
        stream.stroke_width(2.0)
        stream.line(150, 300, 2400, 300)
        stream.line(150, 400, 2400, 400)
        assert len(stream.operators) >= 3, "the control stream must carry operators"
        return stream

    def test_a_content_stream_page_costs_no_bitmap(self):
        """The half-claim "operators cost zero bytes", with its control."""
        probe = LivePageBytes()
        stream = self._a_content_stream()
        bitmap = Image.new("RGB", (2550, 3300), "white")

        probe.track(stream)
        assert (probe.peak, probe.peak_pages, probe.streams_seen) == (0, 1, 1)

        # Control, same probe, same run: a bitmap IS costed, so the zero above
        # is the medium's and not a probe that costs nothing.
        probe.track(bitmap)
        assert probe.peak == PAGE_BITMAP_BYTES == bitmap_bytes_of(bitmap)
        assert (probe.peak_pages, probe.bitmaps_seen) == (2, 1)

    def test_a_page_of_no_known_medium_is_refused_not_costed_at_zero(self):
        """Default-deny (ADR-0039/R2): the third medium is a failure."""
        with pytest.raises(TypeError, match="neither"):
            bitmap_bytes_of(b"%PDF-1.4")  # type: ignore[arg-type]

    def test_the_probe_never_asks_poppler_for_a_bitmap(
        self, rasteriser_is_wired_to_raise
    ):
        """Measuring the old shape, and a streaming export, reads no rasteriser."""
        generator = BookPDFGenerator(corpus_book())
        pages = generator.interior_pages(baseline_puzzles())
        probe = LivePageBytes()
        for page in pages:
            probe.track(page)
        measured = _measured(lambda: export_of(generator, baseline_puzzles()))

        assert probe.seen == BASELINE_PAGE_COUNT == measured.probe.seen
        assert measured.probe.peak == PEAK_IN_PAGES * PAGE_BITMAP_BYTES
        assert measured.probe.peak_pages == PEAK_IN_PAGES

    def test_the_rasteriser_tripwire_is_live(self, rasteriser_is_wired_to_raise):
        """Control for the test above, same fixture: the substitution it
        forbids -- ``page_image`` over an operators page -- does raise."""
        with pytest.raises(rasteriser_is_wired_to_raise):
            pdf_pages_module.page_image(self._a_content_stream())

    def test_a_held_content_stream_is_seen_by_the_count_and_not_by_the_bytes(self):
        """The reason ``peak_pages`` exists: a retained operators page is
        invisible to the byte peak, and the count is the instrument that sees it."""
        probe = LivePageBytes()
        held = [self._a_content_stream() for _ in range(3)]
        for stream in held:
            probe.track(stream)

        assert probe.peak == 0
        assert probe.peak_pages == 3
        del held


# --------------------------------------------------------------------------
# The cap, actually enforced: one book, two shapes, two child processes
# --------------------------------------------------------------------------
#
# Everything above measures *live page bitmaps inside this process*. That is
# the right instrument for the shape, and the wrong one for the word "cap":
# nothing above bounds a process, so "a memory cap that the current code
# fails" was arithmetic over a measured constant and not an executed outcome.
#
# What follows executes it. A fresh interpreter — never a fork of this one,
# whose heap and imports would already be inside the bound — installs a memory
# cap **before it imports PIL or draws anything**, and is then asked for one of
# the three shapes in ``tests.helpers.book_corpus``. Under **one** cap:
#
#   * the streaming export of the 150-puzzle book succeeds and reports the page
#     count it read back out of the written file;
#   * the same interior materialised into a list first — ``interior_pages``,
#     which is the shape this card removed from the export path — dies.
#
# Two mechanisms, because the obvious one does not work everywhere (see
# :func:`_address_space_cap_verdict`), and the platform guard says which half of
# AC-2 is therefore not executed rather than passing silently.


#: The exit status the resident-set sentry uses when it kills its own process.
#: Substituted into :data:`_CHILD_PROGRAM` below, so the two cannot drift.
CHILD_OVER_CAP_EXIT = 91

#: The memory cap those children run under: **32 page bitmaps**,
#: 807,840,000 B (770 MiB).
#:
#: **Derived from measurement, and deliberately not 512 MB.** The instance size
#: is the wrong number for this cap: the streaming child needs ~199 MB
#: (CARD-198: up from ~160 MB on the smaller 182-page corpus), and
#: pitting that plus an interpreter's own footprint against 512 MB would make
#: the test's verdict depend on how much address space CPython, NumPy and
#: Pillow happen to reserve on the machine it runs on — which is the flake this
#: card must not ship. The cap is instead placed in the middle of a gap that is
#: orders of magnitude wide, and stated — like every other number here — in
#: page bitmaps:
#:
#: ===================================== ================= ==================
#: measured on this machine               bytes             page bitmaps
#: ===================================== ================= ==================
#: interpreter + imports, nothing drawn   62.1-62.5 MB      2.46-2.47
#: + the corpus book and one page          102.6 MB          4.06  (the floor)
#: the streaming child's peak RSS         ~199.0 MB         ~7.88
#: **the cap**                            **807.8 MB**      **32**
#: the list shape: 305 bitmaps + file     ~7.82 GB          ~309.8
#: ===================================== ================= ==================
#:
#: Re-measured for CARD-198 on the card's own 305-page corpus book (up from
#: 182): the streaming child's peak RSS moved from 150.8-169.9 MB to ~199 MB,
#: because the one linear term — the file accumulating in the returned
#: ``BytesIO`` — is now 116.1 MB where it was 82.0 MB (every puzzle's own
#: full answer page now carries real ink, where the packed key shared a
#: tile's ink across several puzzles); the floor and the interpreter's own
#: footprint are unaffected, since neither scales with the page count.
#:
#: So the cap sits **4.06x above** the streaming measurement and **9.7x
#: below** what the list shape needs — still not marginal on either side,
#: and the gap closed only on the streaming side, from the 4.7x it was
#: before. Neither verdict can turn on an interpreter's footprint: the
#: platform's own floor is 4.06 page bitmaps, 12.7 % of the cap. Both
#: margins are re-measured on every run and asserted
#: (:data:`CHILD_EXPORT_COST_IN_PAGES`, :data:`CHILD_FLOOR_SHARE`) rather than
#: trusted from this table. CARD-237 re-aimed the first of those two at the
#: export's marginal cost — ``streaming.resident - floor.resident``, the row of
#: this table that is about this code — rather than at the streaming child's
#: total, which is dominated by the interpreter's own footprint; that constant
#: carries the numbers.
CHILD_CAP_IN_PAGES = 32
CHILD_CAP_BYTES = CHILD_CAP_IN_PAGES * PAGE_BITMAP_BYTES

#: What the **export itself** may cost the capped child, in page bitmaps: the
#: streaming child's resident set *minus the floor child's*, measured in the
#: same run under the same cap.
#:
#: **Why the marginal cost and not the child's total (CARD-237).** The total is
#: ``floor + export``, and the floor — interpreter, imports, the corpus book,
#: one page — is the larger half and grows with CPython, not with this code. A
#: bound on the total therefore drifts onto its own threshold as the
#: interpreter grows: the predecessor of this constant required the total to
#: clear the cap by 3x, recorded 4.06x measured at CARD-198, and by CARD-237
#: measured 2.9x (276-280 MB under a full suite) — a false red on roughly three
#: full-suite runs in four, on trees with no export change in them. The
#: marginal cost does not drift, because when the floor grows it is subtracted
#: from both terms.
#:
#: **The bound, against the measurement (CARD-237, this machine):**
#:
#: ========================================= ================= ==============
#: measured, floor and streaming in one run   bytes             page bitmaps
#: ========================================= ================= ==============
#: the floor child (the subtrahend)           107.3-110.6 MB    4.25-4.38
#:   (floor range WIDENED at the AC gate, 2026-10-15, from 110.0-110.6 /
#:   4.36-4.38: one of the gate's seven solo runs measured 4.25 bitmaps,
#:   below the recorded bottom, making the floor's observed spread 1.031x
#:   rather than 1.005x. It is widened here rather than left to be
#:   corrected a third time — this card has already had to widen the
#:   EXPORT's range at the bottom once, and an under-recorded range in
#:   this table is what sized the bound that flaked. The argument is
#:   unaffected: 1.031x against the export's 3.5x is still two orders of
#:   separation, and the floor stays 1.8x clear of CHILD_FLOOR_SHARE.)
#: the streaming child's total RSS            178.7-258.5 MB    7.08-10.24
#: **the export's marginal cost**             **46.9-148.1 MB** **1.86-5.87**
#: the same, on the worst red run on record   ~165.5 MB         ~6.56
#: **the bound below**                        **403.9 MB**      **16**
#: the list shape's own peak                 ~7.75 GB          ~307
#: ========================================= ================= ==============
#:
#: The six runs of the pair taken while this constant was chosen — solo,
#: whole-file, and three times inside the whole suite — measured the marginal
#: cost at 2.70, 3.22, 3.41, 3.44, 5.04 and 5.87 page bitmaps, against a floor
#: that moved by 0.6 MB across all six; six more taken in CARD-237's review
#: cycle, all solo on a quiet host, measured 1.86, 2.54, 3.21, 3.42, 3.52 and
#: 3.67 against a floor that moved by 0.6 MB again — so the recorded range is
#: 1.86-6.56 bitmaps, a 3.5x spread, while the floor's is 1.005x.
#: **That spread is the instrument's own,
#: not the export's**, and it is the reason the bound is not placed just above
#: the smallest figure: ``ru_maxrss`` is a *peak*, and how much of 307 pages'
#: worth of freed bitmap the allocator hands back to the OS depends on what
#: else is resident at the time — which is exactly why the old bound failed
#: inside a busy suite and passed solo, and why the quiet-run figure is the
#: wrong one to size against. The figure the bound is sized against is instead
#: the largest on record: the worst red total the card recorded, 276.1 MB, is
#: ~6.56 bitmaps of export against the floor measured here, and that is the
#: number halved below.
#:
#: **Why 16.** It is the largest bound that keeps the two guards' arithmetic
#: closed: 16 page bitmaps, plus the 8 that :data:`CHILD_FLOOR_SHARE` permits
#: the floor to be, is 24 of the cap's 32 — so whenever both guards pass, the
#: streaming child is *proved* to fit the cap with a quarter of it unused. That
#: is the whole-child margin the old constant asserted directly, reconstructed
#: from two halves, neither of which drifts with CPython. Against the
#: measurements it sits **2.4x above the largest export cost on record** (the
#: ~6.56 bitmaps derived above, itself 1.1x the largest measured here) and 19x
#: below the shape this test exists to separate the export from. Like every RSS
#: figure in this module (see the module docstring on why RSS may not be
#: asserted on as a *shape*) it is a bound on an order of
#: magnitude: the export is 1.9-6.6 bitmaps and constant in the page count, the
#: regression it must catch is ~307 and linear in it, and the bound sits in the
#: empty two orders of magnitude between them — close enough to the export that
#: retaining as few as 9-14 of the book's 307 pages is already red. (Both figures
#: corrected at review cycle 2 from "3-6" and "10-13": the table above was
#: re-measured during the cycle-1 fix and its range widened at the bottom to 1.86,
#: so the sensitivity floor is a BAND, 9.4-14.1 pages, not a number. It moves with
#: the instrument because `16 - measured` is what the guard can still catch.) Measured
#: on the real pair with the streaming child's reported figure inflated by hand
#: (CARD-237's own mutants): 12 pages retained passed at 15.9 bitmaps, 14
#: failed at 17.88, and the whole book retained failed at 309.92.
#: :class:`TestMemoryGuard_StillFailsWhenTheExportItselfRegresses` keeps that
#: evidence live: it pins both *edges* of the comparison (strictly under the
#: constant passes, exactly at it fails) and, since those two are expressed in
#: the constant and so hold for any value of it, one absolute fact about the
#: value — that it stays under a tenth of the book, in the empty band between
#: the export and the regression. CARD-237 review cycle 1 added that third
#: assertion; before it, nothing in the file would have noticed the bound
#: being widened.
CHILD_EXPORT_COST_IN_PAGES = 16
CHILD_EXPORT_COST_BYTES = CHILD_EXPORT_COST_IN_PAGES * PAGE_BITMAP_BYTES

#: The share of the cap the platform's own floor — interpreter, imports, one
#: page — may take before the cap stops being able to tell a *shape* apart from
#: a *footprint*. Over this, the test skips rather than reports either verdict.
#: Measured 12.7 % here (CARD-198: was 11.9 %; the floor itself barely moved,
#: so this is almost entirely the cap's own fixed denominator).
CHILD_FLOOR_SHARE = 0.25

#: Ask the kernel to bound the child's address space. The honest mechanism —
#: the process really cannot get the memory — and the one AC-2 wants. It is not
#: available everywhere: see :func:`_address_space_cap_verdict`.
RLIMIT_MECHANISM = "rlimit"

#: Bound the child's resident set with a sentry thread of its own that calls
#: ``os._exit`` the moment ``ru_maxrss`` crosses the cap. Also a process-level
#: bound — the process really dies, and the export really does not finish — but
#: enforced by the child rather than by the kernel, so it works where
#: ``RLIMIT_AS`` does not. RSS is a poor instrument for measuring a *shape*
#: (this module's docstring says why, with the numbers); it is a fine one for
#: separating ~199 MB from ~7.8 GB (CARD-198's own figures; was 160 MB from
#: 4.6 GB on the smaller corpus).
SENTRY_MECHANISM = "sentry"


#: The child. ``python -c`` and not ``-m``, because the cap has to go on before
#: the first import: a module's own body would have pulled in PIL and NumPy
#: while the process was still unbounded.
_CHILD_PROGRAM = """\
import json
import os
import resource
import sys
import threading
import time

shape, mechanism, cap = sys.argv[1], sys.argv[2], int(sys.argv[3])


def resident():
    used = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return used if sys.platform == "darwin" else used * 1024


if mechanism == "rlimit":
    resource.setrlimit(resource.RLIMIT_AS, (cap, cap))
elif mechanism == "sentry":

    def over_the_cap():
        while True:
            if resident() > cap:
                os.write(2, b"OVER THE CAP\\n")
                os._exit(OVER_CAP_EXIT)
            time.sleep(0.02)

    threading.Thread(target=over_the_cap, daemon=True).start()
else:
    raise SystemExit("unknown cap mechanism: " + mechanism)

from tests.helpers.book_corpus import capped_export_report

try:
    report = capped_export_report(shape)
except MemoryError:
    report = {"shape": shape, "outcome": "memory-error", "resident": resident()}
report["cap"] = cap
report["mechanism"] = mechanism
sys.stdout.write("REPORT " + json.dumps(report))
""".replace("OVER_CAP_EXIT", str(CHILD_OVER_CAP_EXIT))


#: Does ``RLIMIT_AS`` exist, can it be lowered, and does the kernel enforce it?
#: Three separate questions, and a platform can answer yes, no, no. Stdlib
#: only, no imports, so the answer is about the kernel and not about NumPy.
_PROBE_PROGRAM = """\
import resource
import sys

cap = int(sys.argv[1])
try:
    resource.setrlimit(resource.RLIMIT_AS, (cap, cap))
except (AttributeError, OSError, ValueError) as refused:
    sys.stdout.write(
        "the kernel refuses it: setrlimit(RLIMIT_AS, %d) raised %s: %s"
        % (cap, type(refused).__name__, refused)
    )
    raise SystemExit(0)
try:
    held = bytearray(cap * 2)
except MemoryError:
    sys.stdout.write("bites")
    raise SystemExit(0)
sys.stdout.write(
    "it is accepted and not enforced: %d bytes allocated under a %d byte cap"
    % (len(held), cap)
)
"""


@dataclass(frozen=True)
class CappedChild:
    """One child process's outcome: how it ended, and what it reported."""

    shape: str
    mechanism: str
    returncode: int
    report: Optional[Dict[str, Any]]
    stderr: str
    seconds: float

    @property
    def outcome(self) -> str:
        """``written`` / ``drawn`` / ``memory-error``, or how it died."""
        if self.report is not None:
            return str(self.report["outcome"])
        return f"died with exit status {self.returncode}"


def _child_environment() -> Dict[str, str]:
    """This interpreter's own import path, handed to the child.

    ``pythonpath = ["src"]`` in ``pyproject.toml`` and the rootdir pytest puts
    on ``sys.path`` are what make ``nonogram`` and ``tests.helpers`` importable
    here; passing the live ``sys.path`` is what makes them importable there,
    under the editable install or a bare checkout alike.
    """
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join(path for path in sys.path if path)
    return environment


@lru_cache(maxsize=None)
def _capped_child(shape: str, mechanism: str) -> CappedChild:
    """Run one shape in a fresh, capped interpreter. Cached: each pair runs once."""
    started = time.perf_counter()
    finished = subprocess.run(
        [sys.executable, "-c", _CHILD_PROGRAM, shape, mechanism, str(CHILD_CAP_BYTES)],
        capture_output=True,
        text=True,
        env=_child_environment(),
        # Comfortably over the 3.8 s the slowest of the three takes here, and
        # comfortably under ``tests/hang_guard.py``'s 300 s per test, so a
        # wedged child is reported as a child that hung and not as a test that
        # did.
        timeout=90,
    )
    elapsed = time.perf_counter() - started

    report = None
    marker = finished.stdout.find("REPORT ")
    if marker >= 0:
        report = json.loads(finished.stdout[marker + len("REPORT ") :])
    return CappedChild(
        shape=shape,
        mechanism=mechanism,
        returncode=finished.returncode,
        report=report,
        stderr=finished.stderr[-2000:],
        seconds=elapsed,
    )


@lru_cache(maxsize=None)
def _address_space_cap_verdict() -> str:
    """``"bites"``, or why ``RLIMIT_AS`` cannot enforce this cap here.

    Measured, never assumed from ``sys.platform``: the probe sets the cap and
    then asks for twice it, and only a :class:`MemoryError` counts as the
    kernel enforcing the bound.
    """
    finished = subprocess.run(
        [sys.executable, "-c", _PROBE_PROGRAM, str(CHILD_CAP_BYTES)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if finished.returncode != 0:
        return (
            f"the probe child died with exit status {finished.returncode}: "
            f"{finished.stderr.strip()[-400:]}"
        )
    return finished.stdout.strip()


def _habitable(mechanism: str) -> CappedChild:
    """The floor child, and the skip when the platform's own footprint is the story.

    Interpreter, imports, the corpus book and a single page, under the same cap
    — the least a capped export can possibly cost. If *that* cannot run, or
    takes more than :data:`CHILD_FLOOR_SHARE` of the cap, then whatever the
    other two children then do is a fact about this platform's footprint rather
    than about the export's shape, and a pass or a fail would both be
    misleading. So the test skips and says which half of AC-2 went unexecuted.
    """
    floor = _capped_child(BASELINE_SHAPE, mechanism)
    if floor.returncode != 0 or floor.report is None or floor.outcome != "drawn":
        pytest.skip(
            f"a child under the {mechanism} cap of {CHILD_CAP_BYTES} B cannot "
            f"even import the stack and draw one page ({floor.outcome}); "
            f"{floor.stderr.strip()[-300:]!r}. AC-2's executed half — that the "
            "streaming export survives a cap the list shape dies under — is "
            "NOT run on this platform; only the arithmetic derivation in "
            "test_the_old_shape_would_not_have_fitted_the_envelope stands."
        )
    assert floor.report["page_bytes"] == PAGE_BITMAP_BYTES, (
        "the floor child reported a page of "
        f"{floor.report['page_bytes']} bytes — it did not draw a Book 1 page, "
        "so its measurement is not the floor this cap was derived against"
    )
    if floor.report["resident"] > CHILD_CAP_BYTES * CHILD_FLOOR_SHARE:
        pytest.skip(
            f"this platform's floor (interpreter, imports and one page) is "
            f"{floor.report['resident'] / 1e6:.1f} MB, over "
            f"{CHILD_FLOOR_SHARE:.0%} of the {CHILD_CAP_BYTES / 1e6:.0f} MB "
            "cap, so the cap can no longer tell an export's shape apart from "
            "the platform's footprint. AC-2's executed half is NOT run here; "
            "the arithmetic derivation stands."
        )
    return floor


def _the_pair_under_one_cap(
    mechanism: str,
) -> Tuple[CappedChild, CappedChild, CappedChild]:
    """The floor child, the streaming child and the list child, one cap, in order.

    The floor is the first element because it is a *measurement*, not only a
    precondition: :func:`_habitable` spawns it on every run anyway, and
    subtracting it from the streaming child's resident set is what turns
    "the child fitted" into "the export fitted" (CARD-237). Before CARD-237
    this function threw it away.
    """
    floor = _habitable(mechanism)
    return (
        floor,
        _capped_child(STREAMING_SHAPE, mechanism),
        _capped_child(MATERIALISED_SHAPE, mechanism),
    )


def _export_marginal_cost(streaming: CappedChild, floor: CappedChild) -> int:
    """What the **export** cost the capped child: its resident set, less the floor's.

    Both children ran in a fresh interpreter under the same cap, and the floor
    one did everything the streaming one does except the export — imports, the
    corpus book, one drawn page. So the difference is the export's own term,
    and it is the only part of either figure this code is responsible for.
    """
    assert streaming.report is not None and floor.report is not None
    return int(streaming.report["resident"]) - int(floor.report["resident"])


def _assert_the_export_fitted_with_room(
    streaming: CappedChild, floor: CappedChild
) -> int:
    """The self-invalidation tripwire, aimed at the export (CARD-237). Returns it.

    If the export's own marginal cost ever approaches the cap, then the two
    verdicts this test reports stop being about the export's *shape*, and the
    test says so by failing. Its counterpart in the other direction — the
    floor swallowing the cap — is :func:`_habitable`'s skip, which is
    untouched: the quantity moved, the mechanism did not.

    The margin is returned so a caller can report it (and so a test can check
    *which* quantity was asserted on, rather than trusting the source).
    """
    marginal = _export_marginal_cost(streaming, floor)
    assert marginal < CHILD_EXPORT_COST_BYTES, (
        f"the export itself cost {marginal / 1e6:.1f} MB "
        f"({marginal / PAGE_BITMAP_BYTES:.2f} page bitmaps) in the capped "
        f"child — the streaming child's {streaming.report['resident'] / 1e6:.1f} MB "
        f"less the floor child's {floor.report['resident'] / 1e6:.1f} MB — "
        f"against a bound of {CHILD_EXPORT_COST_IN_PAGES} page bitmaps "
        f"({CHILD_EXPORT_COST_BYTES / 1e6:.0f} MB). The export, not the "
        "interpreter, has grown into the cap, so this test's verdict is no "
        "longer about the export's shape"
    )
    return marginal


def _assert_the_streaming_child_fitted(
    child: CappedChild, floor: CappedChild
) -> None:
    """Half one: the 150-puzzle book really exported, under the cap, with room."""
    assert child.returncode == 0, (
        f"the streaming export died under the {child.mechanism} cap of "
        f"{CHILD_CAP_BYTES / 1e6:.0f} MB ({child.outcome}): "
        f"{child.stderr.strip()[-500:]}"
    )
    assert child.report is not None and child.report["outcome"] == "written"
    assert child.report["page_count"] == CORPUS_PAGE_COUNT, (
        "the capped child wrote "
        f"{child.report['page_count']} pages, not {CORPUS_PAGE_COUNT} — the "
        "page count is read back out of the file it wrote, never from the plan"
    )
    marginal = _assert_the_export_fitted_with_room(child, floor)
    # Printed, not only asserted: AC-5 records this margin from full-suite runs
    # (``-rP`` shows it for a passing test), which is how a drift like the one
    # CARD-237 fixed is seen coming next time instead of arriving as a red gate.
    print(
        f"CARD-237 margin [{child.mechanism}]: export "
        f"{marginal / PAGE_BITMAP_BYTES:.2f} page bitmaps "
        f"({marginal / 1e6:.1f} MB) of a {CHILD_EXPORT_COST_IN_PAGES}-bitmap "
        f"bound; floor {floor.report['resident'] / PAGE_BITMAP_BYTES:.2f} "
        f"({floor.report['resident'] / CHILD_CAP_BYTES:.1%} of the cap, "
        f"{CHILD_FLOOR_SHARE:.0%} permitted); streaming total "
        f"{child.report['resident'] / 1e6:.1f} MB"
    )


# --------------------------------------------------------------------------
# AC-2 — a real 150-puzzle book exports under the cap
# --------------------------------------------------------------------------


class TestBookPdfMemory_RealBookExportsUnderTheCap:
    """A 150-puzzle book exports to a valid 305-page PDF inside the envelope.

    The card asks for "a 150-page book exports successfully **under a memory
    cap that the current code fails**". Both halves are covered here, and the
    class is explicit about which of them is *executed* and which is
    *arithmetic*, because they are not the same kind of evidence.

    **Executed** — one cap, two fresh interpreters, two outcomes
    (``test_one_cap_the_streaming_shape_survives_and_the_list_shape_dies_under``
    and its ``RLIMIT_AS`` twin). A child installs a memory cap of 32 page
    bitmaps *before it imports anything*, then exports this very book: the
    streaming shape finishes and reports the 305 pages read back out of the
    file it wrote, and the list shape — ``interior_pages``, the shape this card
    removed from the export path — is killed by the cap partway through. That
    is "a cap the current code fails" as a process that dies, not as a
    multiplication. The earlier objection to ``setrlimit`` was right about an
    *in-process* cap and wrong about a subprocess one: a child that dies takes
    nothing with it.

    **Arithmetic, and kept** — ``test_the_old_shape_would_not_have_fitted_the_envelope``
    derives the list shape's peak for this same book from the instrument's own
    measured per-page constant (305 x 25,245,000 = 7.70 GB, CARD-198: up from
    182 x 25,245,000 = 4.59 GB) against the 512 MB envelope. It is the only
    evidence that reaches the *deployed* number rather than a test cap, it
    costs nothing, and it runs on every platform — including the ones where
    the executed half can only skip.

    What is measured in this process, alongside:

    1. A 150-puzzle book is exported end to end, and the file that comes out
       is a valid PDF whose page tree holds the 305 pages the plan declared.
       The page count is never faked — the pages are drawn.
    2. Its measured peak live page-bitmap memory — what the *panel* retains
       across a page boundary — is one page bitmap. The process holds a second
       one transiently inside a puzzle-page build, which is COMP-007's and is
       accounted for in :data:`PEAK_IN_PAGES`'s note.
    3. The residual linear term — the written file, which does grow with the
       page count — is measured and stated, so the module claims what the code
       has and not a constant it does not.
    """

    def test_the_book_really_exports_and_the_file_holds_every_page(self, corpus_export):
        assert corpus_export.probe.seen == CORPUS_PAGE_COUNT
        assert pdf_page_count(corpus_export.data) == CORPUS_PAGE_COUNT
        assert CORPUS_PUZZLE_COUNT >= 150, "the card's book is 150 puzzles"
        assert CORPUS_PAGE_COUNT >= 150, "the card's book is 150+ pages"

    def test_its_peak_page_memory_is_one_page_bitmap(self, corpus_export):
        """The 305-page book retains one page bitmap, exactly, end to end.

        "Retains" rather than "holds": this is the peak over the pages the
        panel itself keeps, which is what stopped growing with the page count.
        COMP-007's ``render_pages`` holds a second full-size bitmap transiently
        inside each puzzle-page build — a measured constant of 50,490,000 B for
        this book as for the 12-page one — and :data:`PEAK_IN_PAGES` records it.
        """
        probe = corpus_export.probe

        assert probe.peak == PEAK_IN_PAGES * PAGE_BITMAP_BYTES, (
            f"peaked at {probe.peak_in_pages:.2f} page bitmaps "
            f"({probe.peak / 1e6:.1f} MB) over {probe.seen} pages"
        )

    # RETIRED by CARD-322 (G-5 exception 2, item 6). `test_one_cap_the_streaming_shape_survives_and_the_list_shape_dies_under`:
    # its "list shape dies" half has almost no subject once the interior is operators (the only full-size
    # bitmaps left are the dividers and the cover), and the marginal-cost figure it rested on is unstable
    # (-7372800 B and -5603328 B measured by two readers). SURVIVOR: TestBookPdfMemory_PeakDoesNotGrowWithPageCount
    # (::test_a_big_books_peak_is_a_small_books_peak, ::test_neither_book_holds_more_than_one_page_bitmap), which
    # reads the medium-blind live-page unit. PLANT RUN (direct call, CARD-322): holding every page alive in
    # _write_pdf reds both ("308 pages peaked at 308 live pages, 14 pages at 14"; "14 pages peaked at 4.00 page
    # bitmaps"); clean tree green. The RLIMIT_AS twin skips on this platform, so after this retirement only the
    # in-process cells are executed here.


    def test_the_same_pair_under_an_address_space_cap_the_kernel_enforces(self):
        """The same two children, bounded by ``setrlimit(RLIMIT_AS)`` instead.

        The mechanism AC-2 really wants: the kernel refuses the memory, so the
        list shape raises :class:`MemoryError` (or dies) without any code of
        ours deciding that it should. It was kept beside the (since retired, CARD-322) sentry test rather than
        instead of it because **it is not available everywhere**, and the
        probe that decides is a measurement, not a platform name: a child sets
        the cap and then asks for twice it, and only a :class:`MemoryError`
        counts.

        On this machine it skips, and the skip message carries the kernel's
        own refusal. Measured on macOS 26.6.2 (Darwin 25.6.0, arm64):
        ``RLIMIT_AS`` and ``RLIMIT_RSS`` are the same constant (5), and the
        kernel returns ``EPERM`` for **every** soft limit below 1 TiB —
        ``ulimit -v`` fails in the shell for the same reason. So there is no
        address-space cap to be had here at any value, let alone one this book
        could be measured against; ``RLIMIT_DATA`` is refused the same way.
        That is a platform fact, not a property of this book, which is why the
        retired sentry twin carried the executed half here; since CARD-322 the in-process cells of PeakDoesNotGrowWithPageCount do.
        """
        verdict = _address_space_cap_verdict()
        if verdict != "bites":
            pytest.skip(
                f"setrlimit(RLIMIT_AS) cannot bound a process on this "
                f"platform — {verdict}. AC-2's executed half is carried here "
                "by TestBookPdfMemory_PeakDoesNotGrowWithPageCount (the "
                "medium-blind live-page peak; the resident-set sentry test "
                "that used to carry it was retired by CARD-322) and by the "
                "arithmetic derivation; the kernel-enforced address-space "
                "version of it is NOT run on this machine."
            )

        floor, streaming, materialised = _the_pair_under_one_cap(RLIMIT_MECHANISM)

        _assert_the_streaming_child_fitted(streaming, floor)

        died = materialised.returncode != 0
        refused = (
            materialised.report is not None
            and materialised.report["outcome"] == "memory-error"
        )
        assert died or refused, (
            "the list shape finished under an address-space cap it cannot "
            f"fit: {materialised.outcome}, "
            f"{materialised.stderr.strip()[-500:]!r}"
        )

    def test_the_old_shape_would_not_have_fitted_the_envelope(self, corpus_export):
        """The half of the criterion that is arithmetic, over a measured constant.

        The list shape held every page at once — which
        ``test_the_same_instrument_sees_the_old_shape_grow`` measures directly
        — so its peak for this book is the page count times the per-page cost
        the probe measured on this very export. Nothing here is hard-coded but
        the envelope itself.

        This stays beside the executed cap
        (``test_one_cap_the_streaming_shape_survives_and_the_list_shape_dies_under``)
        rather than being replaced by it. The executed test proves the two
        shapes fall on opposite sides of *a* cap, chosen so neither verdict is
        marginal; only this one reaches the **deployed** 512 MB number, and
        only this one runs where a child process cannot be capped at all.
        """
        probe = corpus_export.probe
        old_shape_peak = probe.seen * probe.page_bytes

        assert old_shape_peak > ENVELOPE_BYTES * 8, (
            f"{probe.seen} pages x {probe.page_bytes} bytes = "
            f"{old_shape_peak / 1e9:.2f} GB against a {ENVELOPE_BYTES / 1e6:.0f} MB envelope"
        )
        assert probe.peak < ENVELOPE_BYTES / 10

    def test_the_residual_linear_term_is_the_written_file_and_it_is_small(
        self, corpus_export
    ):
        """Peak memory is O(pages) + O(the file), and the file is the linear term.

        The PDF accumulates in the ``BytesIO`` the export returns — a real
        linear term of well under a megabyte a page — while the bitmap side is
        a constant. It is asserted here at two bounds: the file must stay under
        1 MB a page (or the compression has changed), and the envelope — the
        bitmaps plus the finished file — must fit the panel's 512 MB with room
        for the request around it.

        **The bitmap term this asserts on is the retained one, and the process
        holds one more.** ``probe.peak`` is 25,245,000 B, the page the panel
        keeps; COMP-007's ``render_pages`` holds a second one transiently
        inside a puzzle-page build (see :data:`PEAK_IN_PAGES`), so the process
        figure for this book is 50,490,000 B of bitmap + 82,015,934 B of file
        = **132.3 MB**, about a quarter of the instance. Both readings clear
        the half-envelope bound asserted below by a wide margin, which is why
        the assertion is left as it is rather than loosened or re-aimed: it is
        a bound on the panel's own term, and the constant that sits beside it
        is stated rather than folded in.
        """
        probe = corpus_export.probe
        per_page = len(corpus_export.data) / probe.seen

        assert per_page < 1_000_000, f"{per_page / 1e6:.2f} MB per page written"
        whole_envelope = probe.peak + len(corpus_export.data)
        assert whole_envelope < ENVELOPE_BYTES / 2, (
            f"{probe.seen} pages: {probe.peak / 1e6:.1f} MB of bitmap + "
            f"{len(corpus_export.data) / 1e6:.1f} MB of file"
        )

    def test_tracemalloc_would_not_have_measured_any_of_this(self):
        """Why the instrument is what it is, kept live rather than asserted once.

        Pillow allocates a page's bitmap in C. If a future Pillow ever moved
        those buffers into Python's allocator, ``tracemalloc`` would become a
        usable instrument and this module's central design choice would be
        worth revisiting — so the claim is measured here rather than left in a
        docstring to rot.
        """
        tracemalloc.start()
        try:
            before = tracemalloc.get_traced_memory()[0]
            pages = [Image.new("RGB", (2550, 3300), "white") for _ in range(4)]
            for page in pages:
                page.load()
            traced = tracemalloc.get_traced_memory()[0] - before
        finally:
            tracemalloc.stop()

        bitmap = 4 * PAGE_BITMAP_BYTES
        assert traced < bitmap / 100, (
            f"tracemalloc saw {traced} bytes of {bitmap} bytes of bitmap — it "
            "can now see Pillow's buffers, so this module's instrument choice "
            "should be revisited"
        )

    def test_a_real_book_exports_in_seconds_not_minutes(self, corpus_export):
        """CARD-145 item 4's measurement, kept live (see the card's notes).

        The card feared a route that "looks dead for two minutes" and asked
        for a progress mechanism. A 305-page book (CARD-198: up from 182)
        exports in single-digit seconds on this machine, which is why item 4
        was deferred rather than
        built. This is the number that decision rests on; if it ever stops
        being true, the decision is due for review and this says so by
        failing.
        """
        assert corpus_export.seconds < 60, (
            f"{corpus_export.probe.seen} pages took "
            f"{corpus_export.seconds:.1f}s — progress reporting (CARD-145 item 4) "
            "was deferred on the measurement that this is a seconds-long request"
        )


# --------------------------------------------------------------------------
# CARD-237 — the guard above measures the export, and still has teeth
# --------------------------------------------------------------------------
#
# The two tripwires that decide whether the capped pair's verdict means
# anything — :func:`_assert_the_export_fitted_with_room` and
# :func:`_habitable`'s skip — are themselves tested here, because CARD-237 is
# a card about one of them having measured the wrong quantity for two releases
# without anyone noticing until it went red.
#
# The real children are expensive, so only the test that *must* see the real
# numbers (AC-1) spawns them, through the same ``lru_cache`` the capped tests
# use, and without the 7.8 GB list child. Everything that needs a resident set
# this host does not happen to have — an inflated floor, an inflated export —
# constructs a :class:`CappedChild` with that figure in it and hands it to the
# guard directly. The guard is a pure function of two reports, so the
# construction is the honest seam: no monkeypatching of the measurement path,
# and nothing injected anywhere the real test can reach it.


def _a_child_reporting(shape: str, resident: int, **extra: Any) -> CappedChild:
    """A :class:`CappedChild` carrying a stated resident set, for the guard tests.

    Not a stub of the measurement — a *constructed figure* the pure guard is
    asked to judge, so a resident set this machine does not produce (a floor
    that has swallowed the cap, an export that has regressed to the list
    shape's order) can still be judged. Nothing here reaches
    :func:`_capped_child`.
    """
    report: Dict[str, Any] = {
        "shape": shape,
        "outcome": "drawn" if shape == BASELINE_SHAPE else "written",
        "imported": 62_500_000,
        "resident": resident,
        "cap": CHILD_CAP_BYTES,
        "mechanism": SENTRY_MECHANISM,
    }
    if shape == BASELINE_SHAPE:
        report["page_bytes"] = PAGE_BITMAP_BYTES
    else:
        report["page_count"] = CORPUS_PAGE_COUNT
        report["file_bytes"] = 117_589_739
    report.update(extra)
    return CappedChild(
        shape=shape,
        mechanism=SENTRY_MECHANISM,
        returncode=0,
        report=report,
        stderr="",
        seconds=0.0,
    )


#: The largest export cost on record for this machine, in page bitmaps: the
#: worst red run the card measured (a streaming total of 276.1 MB against the
#: 107.3-110.6 MB floor this host reports), the figure
#: :data:`CHILD_EXPORT_COST_IN_PAGES` is sized against.
#:
#: **Why a recorded constant and not this run's measurement (CARD-237 review
#: cycle 1).** :class:`TestMemoryGuard_InterpreterGrowthDoesNotTripTheGuard`
#: needs a pair whose *total* the old ``resident * 3 < CHILD_CAP_BYTES`` bound
#: would have refused, and the floor it pins that pair at is the largest
#: :data:`CHILD_FLOOR_SHARE` permits, so the export term has to carry the
#: total past ``CHILD_CAP_BYTES / 3`` — 2.67 page bitmaps of export — on its
#: own. The first version of that test carried the *live* measurement there,
#: and 2.67 bitmaps is **inside** what the live measurement reports: the
#: smallest figure on record when the constant was chosen was 2.70 bitmaps —
#: a 1.2 % margin — the review cycle then measured 65.5-67.1 MB (2.59-2.66
#: bitmaps) on five of eleven quiet solo runs, every one of them a red, and
#: this fix's own six re-measurements spread 1.86-3.67 with two under the
#: threshold. So the demonstration's own
#: precondition was a coin toss on a quiet host. Below, the same demonstration
#: clears the threshold by 2.46x of the export (1.36x of the total) and cannot
#: flake at all, because nothing in it is measured. The live measurement keeps
#: the half it can carry robustly — that this host's own export passes the new
#: guard — in a test of its own.
WORST_RECORDED_EXPORT_IN_PAGES = 6.56
WORST_RECORDED_EXPORT_BYTES = int(WORST_RECORDED_EXPORT_IN_PAGES * PAGE_BITMAP_BYTES)


class TestMemoryGuard_HeadroomIsMeasuredAgainstTheFloor:
    """AC-1: the tripwire's quantity is the export's cost, not the child's total.

    Checked two ways, because either alone is weak. First on the **real** pair
    from this run — the same floor child :func:`_habitable` already spawns and
    the same streaming child the capped test judges — asserting that the figure
    the guard returns is the difference between the two residents and that the
    difference is materially smaller than the total. Then behaviourally, on two
    constructed pairs with **identical streaming totals** and different floors:
    a bound on the total could not tell them apart, and this one gives them
    opposite verdicts.
    """

    def test_the_guard_reports_the_difference_between_the_two_children(self):
        floor = _habitable(SENTRY_MECHANISM)
        streaming = _capped_child(STREAMING_SHAPE, SENTRY_MECHANISM)
        assert streaming.report is not None, (
            f"the streaming child did not report: {streaming.outcome}, "
            f"{streaming.stderr.strip()[-300:]!r}"
        )

        marginal = _assert_the_export_fitted_with_room(streaming, floor)

        assert marginal == streaming.report["resident"] - floor.report["resident"], (
            "the guard asserted on something other than the export's marginal "
            f"cost: it reported {marginal} B where the two children measured "
            f"{streaming.report['resident']} B and {floor.report['resident']} B"
        )
        assert marginal > 0, (
            "the export's marginal cost came out non-positive "
            f"({marginal} B) — the floor child is not a floor under this "
            "streaming child, so the subtraction means nothing"
        )
        assert floor.report["resident"] > PAGE_BITMAP_BYTES, (
            f"this host's floor is {floor.report['resident'] / 1e6:.1f} MB, "
            "under one page bitmap — if the floor were really that small the "
            "total and the marginal cost would be the same number and AC-1 "
            "would be vacuous here"
        )
        assert marginal < streaming.report["resident"] - PAGE_BITMAP_BYTES

    def test_two_children_with_the_same_total_get_opposite_verdicts(self):
        """The same streaming total, two floors — so only the marginal can decide."""
        total = 30 * PAGE_BITMAP_BYTES  # just inside the cap, in both pairs
        small_floor = _a_child_reporting(BASELINE_SHAPE, 10 * PAGE_BITMAP_BYTES)
        large_floor = _a_child_reporting(BASELINE_SHAPE, 20 * PAGE_BITMAP_BYTES)
        streaming = _a_child_reporting(STREAMING_SHAPE, total)

        # 20 page bitmaps of export, over the bound: the export is the problem.
        with pytest.raises(AssertionError, match="the export itself cost"):
            _assert_the_export_fitted_with_room(streaming, small_floor)

        # 10 page bitmaps of export under the very same total: fine.
        assert (
            _assert_the_export_fitted_with_room(streaming, large_floor)
            == 10 * PAGE_BITMAP_BYTES
        )


class TestMemoryGuard_InterpreterGrowthDoesNotTripTheGuard:
    """AC-2: the drift that produced CARD-237's false red no longer produces one.

    The floor is inflated to just under the most :data:`CHILD_FLOOR_SHARE`
    permits — 201.96 MB, i.e. the largest footprint under which this test will
    still render a verdict at all — and carries
    :data:`WORST_RECORDED_EXPORT_IN_PAGES` of export, the largest cost on
    record for this machine. The old tripwire asserted
    ``resident * 3 < CHILD_CAP_BYTES``, so it is computed here too and shown to
    fail on exactly this pair: that is the false red, reproduced, and then not
    reproduced by the guard that replaced it.

    **The pair is constructed, not measured (CARD-237 review cycle 1).** This
    class's first version built the pair from *this run's* export measurement,
    which made its own vacuity guard — "the old bound would have refused this
    pair" — a live comparison against a threshold of 2.67 page bitmaps, a
    figure the export measurement routinely comes in under: 1.86-3.67 bitmaps
    across six quiet re-measurements here, and red on five of eleven quiet
    solo runs of the committed tree. That is the very defect class this card
    exists to remove — a bound inside the instrument's own spread — with the
    polarity inverted: a busy host raises the measured ``ru_maxrss`` peak and
    so *helps*, which is why every full-suite run passed and only the
    single-file run this file is debugged with failed. The recorded worst case
    clears the same threshold by 2.46x and is deterministic. A bigger floor
    could not have rescued the live version: to carry even a 2.70-bitmap
    export past the old bound the floor would have to be 203.8 MB, which
    :data:`CHILD_FLOOR_SHARE` forbids.

    What the live measurement *can* carry robustly is the other half — that
    this host's own export passes the new guard — and that is
    :meth:`test_this_hosts_measured_export_passes_the_new_guard` below.
    """

    def test_a_floor_at_the_edge_of_the_share_still_passes(self):
        grown_floor_bytes = int(CHILD_CAP_BYTES * CHILD_FLOOR_SHARE) - 1
        grown_floor = _a_child_reporting(BASELINE_SHAPE, grown_floor_bytes)
        worst_export = _a_child_reporting(
            STREAMING_SHAPE, grown_floor_bytes + WORST_RECORDED_EXPORT_BYTES
        )

        old_tripwire_quantity = worst_export.report["resident"] * 3
        assert old_tripwire_quantity > CHILD_CAP_BYTES, (
            "this pair no longer reproduces CARD-237's false red: a floor of "
            f"{grown_floor_bytes / 1e6:.1f} MB carrying the worst recorded "
            f"export of {WORST_RECORDED_EXPORT_BYTES / 1e6:.1f} MB totals "
            f"{worst_export.report['resident'] / 1e6:.1f} MB, which the old 3x "
            "bound on the total would have accepted — so AC-2 proves nothing"
        )

        assert (
            _assert_the_export_fitted_with_room(worst_export, grown_floor)
            == WORST_RECORDED_EXPORT_BYTES
        )

    def test_this_hosts_measured_export_passes_the_new_guard(self):
        """The live half: whatever this run measures, the new guard accepts it.

        No constructed figure and no reproduction of the old bound — just the
        real pair under the real cap, through the real guard. This is the half
        of AC-2 a measurement can carry: every export figure on record,
        1.86-6.56 page bitmaps, is 2.4x or more under
        :data:`CHILD_EXPORT_COST_IN_PAGES`, so the instrument's spread cannot
        reach the threshold — where in the version this replaced the spread
        straddled it.
        """
        real_floor = _habitable(SENTRY_MECHANISM)
        real_streaming = _capped_child(STREAMING_SHAPE, SENTRY_MECHANISM)
        measured_export = _export_marginal_cost(real_streaming, real_floor)

        assert (
            _assert_the_export_fitted_with_room(real_streaming, real_floor)
            == measured_export
        )


class TestMemoryGuard_StillFailsWhenTheExportItselfRegresses:
    """AC-3: the new bound catches a real regression — it does not tolerate all.

    Three regressions, at three sizes, so the bound is shown to have teeth and
    to have them where they matter rather than only against the absurd case:
    the list shape's own order of magnitude, a shape that retains a *fraction*
    of the book's pages, and one byte over the bound. All three are measured
    against a floor at the *largest* footprint the floor-share guard permits,
    so none of them can be caught merely by the total having grown — each one
    is caught by the export's own term, which is the only thing that changed.
    """

    @staticmethod
    def _floor_and_export(marginal: int) -> Tuple[CappedChild, CappedChild]:
        floor_bytes = int(CHILD_CAP_BYTES * CHILD_FLOOR_SHARE) - 1
        return (
            _a_child_reporting(BASELINE_SHAPE, floor_bytes),
            _a_child_reporting(STREAMING_SHAPE, floor_bytes + marginal),
        )

    def test_an_export_at_the_list_shapes_order_of_magnitude_fails(self):
        """The regression this whole file exists to catch: every page retained."""
        floor, regressed = self._floor_and_export(
            CORPUS_PAGE_COUNT * PAGE_BITMAP_BYTES
        )

        with pytest.raises(AssertionError) as refused:
            _assert_the_export_fitted_with_room(regressed, floor)

        assert "the export itself cost" in str(refused.value)
        assert f"{CORPUS_PAGE_COUNT}.00 page bitmaps" in str(refused.value)

    def test_an_export_that_retains_a_fraction_of_the_book_fails(self):
        """Not only the absurd case: 20 of 307 pages retained is already red.

        Measured against the export this host really costs, so the regression
        is the retention and nothing else. 20 pages is 6.5 % of the book — two
        orders of magnitude short of the list shape, and the bound still bites.
        The smallest retention it bites on, from the same measurement, is
        reported by the assertion below if it ever stops being far smaller
        than the book.
        """
        retained = 20
        real = _export_marginal_cost(
            _capped_child(STREAMING_SHAPE, SENTRY_MECHANISM),
            _habitable(SENTRY_MECHANISM),
        )
        smallest_caught = (CHILD_EXPORT_COST_BYTES - real) / PAGE_BITMAP_BYTES
        assert smallest_caught < retained < CORPUS_PAGE_COUNT / 10, (
            f"on this host the bound first bites at {smallest_caught:.1f} "
            f"retained pages of {CORPUS_PAGE_COUNT}; this test's {retained} is "
            "no longer the modest regression it is written to be"
        )
        floor, regressed = self._floor_and_export(
            real + retained * PAGE_BITMAP_BYTES
        )

        with pytest.raises(AssertionError, match="the export itself cost"):
            _assert_the_export_fitted_with_room(regressed, floor)

    def test_the_bound_is_where_the_constant_says_it_is(self):
        """One byte either side of :data:`CHILD_EXPORT_COST_BYTES`, plus its value.

        The two edge assertions pin *where the comparison sits* — strictly
        under the constant passes, exactly at it fails — and nothing more:
        both sides are expressed in the constant, so they hold for any value
        of it. (Confirmed in CARD-237's review cycle 1 by mutation: at
        ``CHILD_EXPORT_COST_IN_PAGES = 320`` this test stayed green while
        three sibling tests went red.) So the value itself is pinned here too,
        absolutely: the bound has to stay in the empty band between the export
        (1.9-6.6 bitmaps, constant in the page count) and the regression it exists
        to catch (one bitmap per page of the book, linear in it), and a bound
        of a tenth of the book or more is out of that band: at a tenth, a
        shape retaining a couple of dozen of the book's pages would already
        pass the guard that exists to refuse exactly that.
        """
        under_floor, under = self._floor_and_export(CHILD_EXPORT_COST_BYTES - 1)
        over_floor, over = self._floor_and_export(CHILD_EXPORT_COST_BYTES)

        assert (
            _assert_the_export_fitted_with_room(under, under_floor)
            == CHILD_EXPORT_COST_BYTES - 1
        )
        with pytest.raises(AssertionError, match="the export itself cost"):
            _assert_the_export_fitted_with_room(over, over_floor)

        assert CHILD_EXPORT_COST_IN_PAGES < CORPUS_PAGE_COUNT / 10, (
            f"the bound is {CHILD_EXPORT_COST_IN_PAGES} page bitmaps against a "
            f"{CORPUS_PAGE_COUNT}-page book — a tenth of the book or more is "
            "no longer in the empty band between the export's own cost and the "
            "retention this file exists to catch, so the two edge assertions "
            "above are pinning a comparison that has stopped meaning anything"
        )


class TestMemoryGuard_StillSkipsWhenTheFloorSwallowsTheCap:
    """AC-4 / G-3: the self-invalidation mechanism is retained, not replaced.

    CARD-237 moved the tripwire's quantity, and the obvious way to get that
    wrong is to leave the test able to render a verdict on a platform whose own
    footprint has eaten the cap — because a marginal cost stays small however
    large the floor grows. It must not: over :data:`CHILD_FLOOR_SHARE`,
    :func:`_habitable` skips, with the message it already had.

    The floor child is replaced here rather than constructed around, because
    the skip lives inside :func:`_habitable` and that is the one place the
    measurement is reached from.
    """

    def test_a_floor_over_the_share_skips_with_its_existing_message(
        self, monkeypatch
    ):
        swollen = int(CHILD_CAP_BYTES * CHILD_FLOOR_SHARE) + 1
        monkeypatch.setattr(
            sys.modules[__name__],
            "_capped_child",
            lambda shape, mechanism: _a_child_reporting(BASELINE_SHAPE, swollen),
        )

        with pytest.raises(pytest.skip.Exception) as skipped:
            _habitable(SENTRY_MECHANISM)

        message = str(skipped.value)
        assert "this platform's floor (interpreter, imports and one page) is" in message
        assert f"over {CHILD_FLOOR_SHARE:.0%} of the" in message
        assert "AC-2's executed half is NOT run here" in message
        assert f"{swollen / 1e6:.1f} MB" in message

    def test_a_floor_just_under_the_share_does_not_skip(self, monkeypatch):
        """The skip is a bound, not a blanket: one byte under it, the test runs."""
        permitted = int(CHILD_CAP_BYTES * CHILD_FLOOR_SHARE) - 1
        monkeypatch.setattr(
            sys.modules[__name__],
            "_capped_child",
            lambda shape, mechanism: _a_child_reporting(BASELINE_SHAPE, permitted),
        )

        assert _habitable(SENTRY_MECHANISM).report["resident"] == permitted


# --------------------------------------------------------------------------
# AC-3 — every page is pixel-identical to the same page before this card
# --------------------------------------------------------------------------


class TestBookPdfMemory_TheBaselineBooksPages:
    """The baseline book (``tests/helpers/book_corpus``): its page count, the
    medium each page is written in, and one page of every kind the interior
    has, each identified positively.

    The pixel record this class used to compare every raster page against
    (``book_baseline_card206.json``'s digests) was retired on 2026-11-09: the
    owner's new level dividers moved every raster page it recorded.
    """

    @pytest.fixture(scope="class")
    @classmethod
    def baseline(cls) -> Dict[str, Any]:
        return load_baseline()

    @pytest.fixture(scope="class")
    @classmethod
    def exported_bytes(cls) -> bytes:
        return export_of(BookPDFGenerator(corpus_book()), baseline_puzzles())

    @pytest.fixture(scope="class")
    @classmethod
    def exported(cls, exported_bytes) -> List[Image.Image]:
        return interior_pages_of(exported_bytes)

    def test_the_book_still_has_the_page_count_it_was_recorded_with(
        self, baseline, exported
    ):
        # One page more than CARD-206 recorded: the closing thank-you page
        # after the key (owner, 2026-11-10), and nothing else.
        assert baseline["page_count"] + 1 == BASELINE_PAGE_COUNT
        assert len(exported) == BASELINE_PAGE_COUNT

    def test_every_page_is_in_the_medium_its_kind_is_declared_in(self, exported):
        """Read off the file, against ``BASELINE_PAGE_KINDS`` read through the
        registry."""
        assert len(exported) == len(BASELINE_PAGE_KINDS) == BASELINE_PAGE_COUNT
        assert exported.media == declared_media_of_the_baseline()

    def test_the_corpus_covers_every_page_kind_the_interior_has(self, exported):
        """Fifteen pages, one of every kind, each identified positively and
        all distinct. The book prints grouped easy, medium, hard (INV-009):

        * page 1 is the title / copyright page, pages 2 and 3 the guide's two
          pages, page 4 the table of contents, page 11 the Solutions opener,
          and pages 5, 7 and 9 the Easy (puzzles 1-2), Medium (3) and Hard (4)
          level dividers — each compared against the page the generator
          draws for it;
        * page 6 is the two-up page (FR-040), the book's two easy 10x10s:
          each half of it carries its own complete 10x10 grid, which no
          single-puzzle page can do;
        * pages 8 and 10 are single-puzzle pages, and the 15x15 medium and the
          30x30 hard the baseline book declares are **read back off their
          ink** (``drawing_of``), not asked of the layout — in that order,
          because the levels print in that order;
        * pages 12-14 are the packed answer pages, one per level (Duck and
          Owl; Tree; Snowflake) — each carries solid blocks of ink a filled
          cell wide, which no blank puzzle page has;
        * page 15 is the closing thank-you page (owner, 2026-11-10), compared
          against the page the generator draws for it.
        """
        assert len(exported) == BASELINE_PAGE_COUNT
        generator = BookPDFGenerator(corpus_book())

        assert np.asarray(exported[0].convert("L")).min() < 255, (
            "interior page 1 is the title / copyright page (owner, 2026-11-09)"
        )
        assert same_page(exported[0], page_image(generator.vector_title_contents(4, 1)))
        assert same_page(exported[1], reference_guide_page(generator, 2))
        assert same_page(exported[2], reference_guide_page(generator, 3))
        # The SOLUTIONS divider is the approved mockup's Solutions opener
        # since that change (a rule, "PUZZLES 1-4", "Solutions", a blurb).
        assert same_page(
            exported[10], generator.create_solutions_opener(11, len(baseline_puzzles()))
        )
        for number, level, puzzles in (
            (5, Tier.EASY, (1, 2)),
            (7, Tier.MEDIUM, (3, 3)),
            (9, Tier.HARD, (4, 4)),
        ):
            assert same_page(
                exported[number - 1],
                generator.create_level_divider(number, level, puzzles),
            ), f"interior page {number} should be the {level.label!r} level divider"

        for number, side in ((8, 15), (10, 30)):
            drawing = drawing_of(exported[number - 1])
            assert (drawing.columns, drawing.rows) == (side, side), (
                f"interior page {number} should be the book's {side}x{side} "
                "puzzle printed alone"
            )

        two_up = exported[5]
        upper = two_up.crop((0, 0, two_up.width, two_up.height // 2))
        lower = two_up.crop((0, two_up.height // 2, two_up.width, two_up.height))
        for half, drawing in (("upper", drawing_of(upper)), ("lower", drawing_of(lower))):
            assert (drawing.columns, drawing.rows) == (10, 10), (
                f"the {half} half of interior page 6 should carry one of the "
                "two 10x10 puzzles the two-up page pairs"
            )

        assert same_page(exported[14], page_image(generator.vector_closing_page(15, False))), (
            "interior page 15 should be the closing thank-you page"
        )

        for number in (12, 13, 14):
            assert solid_ink_blocks(exported[number - 1]), (
                f"interior page {number} should be an answer page, whose "
                "filled cells are solid blocks of ink"
            )
        # Pages 1-3, 5, 7, 9 and 11 are identified positively above (title,
        # guide, level dividers, Solutions opener); the guide diagrams and the
        # openers' bold type and dots are solid ink, so they are not probed.
        # Page 4 (TOC) and the puzzle pages carry no filled cell.
        for number in (4, 6, 8, 10):
            assert not solid_ink_blocks(exported[number - 1]), (
                f"interior page {number} carries filled cells — it is an "
                "answer page, and the baseline no longer covers its kind"
            )

        for first in range(len(exported)):
            for second in range(first + 1, len(exported)):
                assert not same_page(exported[first], exported[second]), (
                    f"interior pages {first + 1} and {second + 1} are the same "
                    "page — the baseline no longer covers every page kind"
                )

class TestBookPdfMemory_TheSharedReaderReadsEachPageForItself:
    """CARD-355 SCOPE+ regression: ``rendered_page`` returns the page it was asked for.

    The defect: one scratch directory, a fixed output prefix, and a read-back of
    ``sorted(glob("page-*.png"))[0]`` -- so after page 1 was rendered every
    later page in the same directory came back as page 1. The two pages here
    carry different ink at different places; the independent second reading is
    poppler itself, called directly into a fresh directory per page with no
    help from the helper under test.
    """

    @staticmethod
    def _two_pages() -> bytes:
        first = ContentStream(width_px=300, height_px=400, dpi=100)
        first.stroke_width(2.0)
        first.line(20, 50, 280, 50)
        second = ContentStream(width_px=300, height_px=400, dpi=100)
        second.stroke_width(2.0)
        second.line(150, 20, 150, 380)
        return write_vector_pdf([first, second], 2).getvalue()

    @staticmethod
    def _poppler_alone(data: bytes, page: int, directory: Path) -> np.ndarray:
        directory.mkdir(parents=True, exist_ok=True)
        source = directory / "alone.pdf"
        source.write_bytes(data)
        subprocess.run(
            [pdf_vector.PDFTOPPM, "-r", "100", "-f", str(page), "-l", str(page),
             "-gray", "-png", str(source), str(directory / "alone")],
            check=True, capture_output=True,
        )
        (png,) = sorted(directory.glob("alone-*.png"))
        with Image.open(png) as image:
            return np.asarray(image.convert("L"), dtype=np.int16)

    def test_page_two_is_not_page_one_and_is_poppler_own_page_two(self, tmp_path):
        data = self._two_pages()
        shared = tmp_path / "shared"
        one = pdf_vector.rendered_page(data, 100, 1, out_dir=shared)
        two = pdf_vector.rendered_page(data, 100, 2, out_dir=shared)
        alone_one = self._poppler_alone(data, 1, tmp_path / "a1")
        alone_two = self._poppler_alone(data, 2, tmp_path / "a2")

        # the pages really differ, or the test could not tell them apart
        assert not np.array_equal(alone_one, alone_two)
        assert not np.array_equal(one, two), "page 2 came back as page 1"
        assert np.array_equal(two, alone_two)

    def test_control_page_one_through_the_same_shared_directory_is_its_own_render(
        self, tmp_path
    ):
        """Matched control, green on the defective helper too: page 1 is the one
        page the old read-back got right, so a red on page 2 is the defect's."""
        data = self._two_pages()
        shared = tmp_path / "shared"
        one = pdf_vector.rendered_page(data, 100, 1, out_dir=shared)
        pdf_vector.rendered_page(data, 100, 2, out_dir=shared)
        assert np.array_equal(one, self._poppler_alone(data, 1, tmp_path / "a1"))

    def test_the_shared_reader_returns_each_operators_page_its_own_render(self, tmp_path):
        data = self._two_pages()
        pages = pdf_pages(data, dpi=100, out_dir=tmp_path / "shared")

        assert len(pages) == 2
        assert np.array_equal(
            np.asarray(pages[0].convert("L"), dtype=np.int16),
            self._poppler_alone(data, 1, tmp_path / "a1"),
        )
        assert np.array_equal(
            np.asarray(pages[1].convert("L"), dtype=np.int16),
            self._poppler_alone(data, 2, tmp_path / "a2"),
        )
        assert not np.array_equal(
            np.asarray(pages[0].convert("L")), np.asarray(pages[1].convert("L"))
        )


class TestBookPdfMemory_AnOperatorsPageIsTheSameStreamEveryExport:
    """CARD-355 -- what "byte identity" means once a page is operators.

    A byte comparison across a medium change is a claim about **determinism**,
    not about pixels. The recordings this module compares against are digests
    of decoded JPEG bitmaps from the raster era; an operators page has no such
    bitmap, and its poppler render cannot equal one. What a page that is
    operators can be identical TO is *itself on another export*: the same book
    exported twice writes the same content stream, operator for operator
    (:func:`pdf_vector.content_streams`), and therefore the same pixels under a
    fixed rasteriser.

    The control is in the same class: :func:`_streams_agree` is handed one
    page's stream with a single character changed and must say no.
    """

    @pytest.fixture(scope="class")
    @classmethod
    def twice(cls) -> Tuple[bytes, bytes]:
        return (
            export_of(BookPDFGenerator(corpus_book()), baseline_puzzles()),
            export_of(BookPDFGenerator(corpus_book()), baseline_puzzles()),
        )

    @staticmethod
    def _streams_agree(first: List[str], second: List[str]) -> bool:
        return len(first) == len(second) and all(
            hashlib.sha256(a.encode()).digest() == hashlib.sha256(b.encode()).digest()
            for a, b in zip(first, second)
        )

    def test_the_same_book_writes_the_same_operators_every_time(self, twice):
        first, second = (pdf_vector.content_streams(data) for data in twice)

        assert len(first) == BASELINE_PAGE_COUNT
        assert self._streams_agree(first, second)

    def test_the_same_book_is_the_same_length_every_time(self, twice):
        first, second = twice
        assert len(first) == len(second)
        assert pdf_vector.page_media(first) == pdf_vector.page_media(second)

    def test_the_same_book_renders_to_the_same_pixels_every_time(self, twice):
        digests = [page_digests(interior_pages_of(data)) for data in twice]
        assert digests[0] == digests[1]

    def test_the_comparison_has_teeth(self, twice):
        """Control, same run: one changed character in one stream is a
        disagreement, and so is one dropped page -- on a page of either medium."""
        streams = pdf_vector.content_streams(twice[0])
        for index in range(len(streams)):
            changed = list(streams)
            changed[index] = changed[index][:-1] + (
                " " if changed[index][-1:] != " " else "\n"
            )
            assert not self._streams_agree(streams, changed), (
                f"a changed byte on page {index + 1} was not noticed"
            )
        assert not self._streams_agree(streams, streams[:-1])
        assert self._streams_agree(streams, list(streams)), "and an equal pair agrees"

# --------------------------------------------------------------------------
# AC-4 — the interior and the cover are still two files
# --------------------------------------------------------------------------


class TestBookPdfMemory_InteriorAndCoverStillSeparate:
    """INV-013 survives the restructure: two files, parity from interior page 1.

    ``export_book`` now writes both files through the streaming writer, so
    this is the one place that checks the restructure did not merge them,
    shorten the interior, or move the guide page off page 1 (G-2).

    It is also the **only** place ``export_book``'s own memory is measured.
    ``export_book`` does not delegate to ``export_interior``: it has its own
    ``interior_stream`` + ``_write_pdf`` pair, so the interior route's
    measurement says nothing about it. The export here therefore runs inside
    the probe, and the class asserts the cover half of the bound (failure
    matrix F-6) on the value a route really gets back.
    """

    @pytest.fixture(scope="class")
    @classmethod
    def measured(cls) -> MeasuredExport:
        return _measured(
            lambda: BookPDFGenerator(corpus_book()).export_book(
                baseline_puzzles(), BOOK_TITLE
            )
        )

    @pytest.fixture(scope="class")
    @classmethod
    def export(cls, measured):
        return measured.data

    def test_the_whole_book_holds_one_page_bitmap_at_a_time(self, measured):
        """Both files, thirteen pages, one retained page bitmap — the cover keeps none.

        ``export_book`` writes the interior and then the cover, and the peak
        over the pair is the same single page bitmap either file costs alone.
        The thirteen pages are :data:`BASELINE_PAGE_COUNT`'s twelve interior
        pages (CARD-198: up from eleven) and the cover, counted by the
        instrument, so a measurement over a book that was never drawn
        cannot pass this.

        As everywhere in this module, the number is what the **panel** retains
        across a page boundary. COMP-007's ``render_pages`` holds a second
        full-size bitmap transiently inside each puzzle-page build, which is
        outside :data:`PAGE_FACTORIES` and outside this measurement; it is a
        constant, it is the merge-base's code, and :data:`PEAK_IN_PAGES`
        carries its measured value.

        **What this measures is that ``export_book`` holds no page itself**,
        and not that it calls the two in that order: swapping the statements,
        folding them back into one ``BookExport(...)`` call with ``cover=``
        first, and making ``_cover_page`` eager all still measure 1.00 (failure
        matrix F-6). What moves the number is a page bound in ``export_book``
        — ``cover_page = self.create_cover_page(...)`` held across the interior
        write measures 2.00 and fails here, which is the positive control for
        this assertion.

        This is what the old shape would have failed loudest: materialising
        the interior inside ``export_book`` — the list this card removed —
        measures **13.00** page bitmaps on this twelve-page book (CARD-198:
        up from eleven), 328 MB, and 7.70 GB on the 305-page one (CARD-198:
        up from 182).
        """
        probe = measured.probe

        assert probe.seen == BASELINE_PAGE_COUNT + 1, "twelve interior pages and a cover"
        assert probe.page_bytes == PAGE_BITMAP_BYTES
        assert probe.peak == PEAK_IN_PAGES * PAGE_BITMAP_BYTES, (
            f"export_book peaked at {probe.peak_in_pages:.2f} page bitmaps "
            f"over {probe.seen} pages"
        )
        # CARD-355: and the medium-blind count, for the pages that hold no bitmap.
        assert probe.peak_pages == PEAK_IN_PAGES, (
            f"export_book held {probe.peak_pages} pages at once over "
            f"{probe.seen} pages"
        )

    def test_a_page_built_outside_the_writer_is_still_seen(self):
        """The instrument is not vacuous about the cover — the F-6 mutant, run.

        F-6's failure mode is a cover page built *before* the interior is
        written and held alive beside every page of it. Such a page never
        passes ``_write_pdf``'s producer, so a probe wrapped around the
        producer alone would not see it and would still measure 1.00 —
        which is why :func:`_measured` wraps the page factories too
        (:data:`PAGE_FACTORIES`).

        Here that cover is built and held across a real interior export. The
        measured peak is 2.00 page bitmaps: the held cover plus whichever
        interior page is alive. The same run through a producer-only probe is
        what would have read 1.00.
        """
        generator = BookPDFGenerator(corpus_book())
        held: List[Image.Image] = []

        def build_the_cover_first_and_keep_it() -> bytes:
            held.append(generator.create_cover_page(BOOK_TITLE))
            return export_of(generator, baseline_puzzles())

        measured = _measured(build_the_cover_first_and_keep_it)
        try:
            assert measured.probe.seen == BASELINE_PAGE_COUNT + 1
            assert measured.probe.peak == 2 * PAGE_BITMAP_BYTES, (
                f"a cover held across the interior measured "
                f"{measured.probe.peak_in_pages:.2f} page bitmaps — the "
                "instrument cannot see a page built outside the writer, so "
                "the cover half of the bound is not being measured"
            )
            assert measured.probe.peak_pages == 2, (
                f"a cover held across the interior measured "
                f"{measured.probe.peak_pages} live pages, not 2"
            )
        finally:
            held.clear()

    def test_the_interior_and_the_cover_are_two_files(self, export):
        interior, cover = export.interior.getvalue(), export.cover.getvalue()

        assert interior != cover
        assert pdf_page_count(interior) == BASELINE_PAGE_COUNT
        assert pdf_page_count(cover) == 1

    def test_the_interior_starts_at_the_title_page_and_holds_no_cover(self, export):
        """CARD-206: interior page 1 is the title page and the guide's
        own first page follows it (:data:`GUIDE_INTERIOR_PAGES`).

        The owner replaced the blank page with the title and copyright page
        on 2026-11-09, so page 1 now carries ink: it is read as **text**
        (the book's title and the copyright line, set from the content
        stream) with no folio, and it is still not the cover."""
        interior = interior_pages_of(export.interior.getvalue())
        (cover,) = pdf_pages(export.cover.getvalue())
        guide = reference_guide_page(
            BookPDFGenerator(corpus_book()), GUIDE_INTERIOR_PAGES[0]
        )

        title_texts = [
            text for *_, text in pdf_vector.placed_text(
                pdf_vector.content_streams(export.interior.getvalue())[0]
            )
        ]
        assert corpus_book().metadata.title in title_texts, title_texts
        assert any(text.startswith("Copyright") for text in title_texts), title_texts
        assert not any(text.strip().isdigit() for text in title_texts), (
            "interior page 1 is the title page — it prints no folio"
        )
        assert same_page(interior[GUIDE_INTERIOR_PAGES[0] - 1], guide)
        for number, page in enumerate(interior, start=1):
            assert not same_page(page, cover), f"interior page {number} is the cover"

    def test_the_reported_counts_are_the_interiors_own(self, export):
        """The counts come off the page plan now — they must still be the file's."""
        assert export.interior_page_count == pdf_page_count(export.interior.getvalue())
        assert export.interior_page_count == BASELINE_PAGE_COUNT
        # CARD-202: Duck+Owl pack onto one page, Tree packs alone onto
        # another, Snowflake keeps its own full page — 3, not CARD-198's 4.
        assert export.answer_page_count == 3
        # The two-up page (FR-040) and CARD-202's own packing saving (one
        # fewer answer page than CARD-198's one-per-puzzle) together now.
        assert export.pages_saved == 2

    def test_parity_still_counts_from_interior_page_1(self, export):
        """Parity counts from interior page 1, and the cover is never numbered
        (FR-043, INV-013, G-2).

        On Book 1 both side margins are 0.5 in (CON-018 as amended), so a
        centred drawing lands on the same columns at either parity; what
        mirrors is the footer's grid-size label, set on the page's **inner**
        side. The baseline book's two single-puzzle pages are interior 8 and
        10, both even (left-hand), so the label sits at the right-hand end of
        the footer line. Interior page 2, the guide's first page, is
        left-hand too: its leftmost ink starts at the 0.5 in margin. Measured
        off the ink alone.
        """
        interior = interior_pages_of(export.interior.getvalue())

        #: The footer line's rows        interior = interior_pages_of(export.interior.getvalue())

        #: The footer line's rows and the usable area's two edges, in this
        #: page's own pixels, written out rather than imported: 0.5 in margins
        #: at 300 DPI, and the line the grid-size label and the folio are set
        #: on, 38 px (one 9 pt gap; 274 px with the 20 mm reserved row before
        #: CARD-392) above the bottom margin.
        usable_left, usable_right = 150, 2550 - 150
        line_bottom = 3300 - 141 - 38
        label_zone = 400
        for number in (8, 10):
            page = interior[number - 1]
            ink = np.asarray(page.convert("L")) < 128
            strip = ink[line_bottom - 42 : line_bottom + 1]
            at_the_left = strip[:, usable_left : usable_left + label_zone].sum()
            at_the_right = strip[:, usable_right - label_zone : usable_right].sum()
            # A left-hand (even) page's gutter is on its right, so the
            # grid-size label (the inner side) is at the right-hand end
            # (CARD-206: these two pages are even now).
            assert at_the_right > 4 * at_the_left, (
                f"interior page {number} is a left-hand page, so the "
                f"footer's grid-size label belongs at its right-hand end; "
                f"the line holds {at_the_right} dark pixels there against "
                f"{at_the_left} at the left"
            )
            # And the drawing itself is centred, which is why it can no
            # longer be asked: both of its side gaps are the same.
            drawing = drawing_of(page)
            left_gap = drawing.left - usable_left
            right_gap = usable_right - drawing.grid_right
            assert abs(left_gap - right_gap) <= 4, (number, left_gap, right_gap)

        # And the guide's first page: its leftmost ink (a diagram's rule,
        # which bleeds up to half a heavy rule past its nominal edge) starts
        # at the 150 px margin.
        ink = np.asarray(interior[GUIDE_INTERIOR_PAGES[0] - 1].convert("L")) < 128
        leftmost = int(np.where(ink.any(axis=0))[0].min())
        assert 139 < leftmost < 160, leftmost


# --------------------------------------------------------------------------
# The failure matrix — streaming means bytes exist before the export succeeds
# --------------------------------------------------------------------------


class TestBookPdfMemory_NothingHalfWrittenEscapes:
    """The two failures streaming introduces, and what the writer does with them.

    Building a list first meant every page existed before a byte did, so an
    export either failed with nothing written or succeeded. Writing a page at
    a time means bytes exist before the export is known to succeed, and the
    object table is laid out before the pages arrive. Both new failure modes
    are declared on the card's failure matrix, and this is where they are
    measured.
    """

    def test_a_page_that_fails_at_page_12_of_14_hands_the_caller_nothing(self):
        """Ten pages were already in the buffer, and no file came out.

        The mechanism is that the buffer is a local of ``_write_pdf`` and is
        returned only after the trailer: a failure mid-walk propagates and
        takes the partial bytes with it, unreferenced. What this measures is
        both halves — that real bytes had been written (so the test is not
        passing on a failure that happened too early to matter) and that the
        caller got an exception rather than a truncated PDF.

        Both answer writers (full and packed) are forced to fail, so the
        first answer page, the twelfth, is where the walk stops.
        """
        written: List[int] = []
        handed: List[Any] = []
        write_page = BookPDFGenerator._write_page
        write_pdf = BookPDFGenerator._write_pdf

        def counting(self, *args, **kwargs):
            written.append(1)
            return write_page(self, *args, **kwargs)

        def handing_over(self, pages, page_count, **kwargs):
            # CARD-355: the medium-blind count. ``_write_page`` is the RASTER
            # page writer only; an operators page goes through the vector
            # writer and is invisible to it. Every page, in either medium, is
            # handed to ``_write_pdf`` by the producer, so what reached the
            # writer is counted at that seam.
            def counted() -> Iterator[Any]:
                for page in pages:
                    handed.append(type(page))
                    yield page

            return write_pdf(self, counted(), page_count, **kwargs)

        def refuses(*args, **kwargs):
            raise ValueError("this answer will not draw")

        generator = BookPDFGenerator(corpus_book())
        generator.pages = replace(
            generator.pages, answer=refuses, packed_answer=refuses
        )
        BookPDFGenerator._write_page = counting
        BookPDFGenerator._write_pdf = handing_over
        try:
            with pytest.raises(RuntimeError) as raised:
                export_of(generator, baseline_puzzles())
        finally:
            BookPDFGenerator._write_page = write_page
            BookPDFGenerator._write_pdf = write_pdf

        assert "could not be drawn" in str(raised.value)
        # The blank title page (CARD-206), the 2-page guide (CARD-201), the
        # 1-page table of contents
        # (CARD-200), three level dividers, the two-up page, two
        # single-puzzle pages and the SOLUTIONS divider: eleven pages of a
        # planned fourteen were bytes in the buffer already (CARD-202: the
        # baseline book's answer section is now 3 packed-or-full pages, not
        # CARD-198's 4, but the first one — where this failure lands — is
        # still the twelfth page either way).
        first_eleven = (
            PageKind.TITLE, PageKind.GUIDE, PageKind.GUIDE, PageKind.TOC,
            PageKind.DIVIDER, PageKind.PUZZLE, PageKind.DIVIDER,
            PageKind.PUZZLE, PageKind.DIVIDER, PageKind.PUZZLE,
            PageKind.DIVIDER,
        )
        assert len(handed) == len(first_eleven) == 11, handed
        # And each arrived in the medium its kind is declared in -- a second
        # reading of the same eleven pages, by type against by registry.
        assert [issubclass(t, Image.Image) for t in handed] == [
            page_medium(kind) is PageMedium.RASTER for kind in first_eleven
        ], handed
        # The raster writer saw exactly the raster ones.
        assert written == [1] * sum(
            page_medium(kind) is PageMedium.RASTER for kind in first_eleven
        ), written

    #: The kind the bitmap stand-in pages are filed under. CARD-379 (M3): these
    #: two tests claim a COUNT tripwire, not a medium, and they hand
    #: ``_write_pdf`` a ``PIL`` page; ``_write_pdf`` refuses a bitmap filed under
    #: a vector-declared kind ("page 1 is a vector puzzle page, but arrived as
    #: Image"), which is what the puzzle kind they used to name becomes once
    #: ADR-0042/R1's five conversions land. CARD-354 met the same refusal and
    #: filed its raster twin under DIVIDER; the mechanism applies, the kind
    #: does not: the divider's declaration expires with CARD-231, so it is a
    #: temporary home. The cover is raster PERMANENTLY (ADR-0042/R2,
    #: ``expires_with=()``), so a bitmap filed under it stays legal in every
    #: tree and the test never has to move again.
    _BITMAP_KIND = PageKind.COVER

    def _the_kind_is_a_declared_bitmap(self) -> None:
        """The precondition, asserted: the stand-in's kind IS a bitmap kind."""
        assert page_medium(self._BITMAP_KIND) is PageMedium.RASTER, (
            f"{self._BITMAP_KIND} is no longer a declared bitmap, so these "
            "tests' bitmap pages would be refused for their MEDIUM and not "
            "tested for their COUNT"
        )

    def test_a_producer_that_yields_too_few_pages_never_reaches_the_trailer(self):
        """A short stream would leave the page tree pointing at nothing."""
        generator = BookPDFGenerator(corpus_book())
        self._the_kind_is_a_declared_bitmap()
        blank = Image.new("RGB", (60, 80), "white")

        def two_of_three() -> Iterator[Image.Image]:
            yield blank
            yield blank

        with pytest.raises(RuntimeError) as raised:
            generator._write_pdf(
                two_of_three(), 3, mode="RGB", kinds=(self._BITMAP_KIND,) * 3
            )

        assert "interior has 2 pages, its page plan says 3" in str(raised.value)

    def test_a_producer_that_yields_too_many_is_refused_before_the_extra_page(self):
        """The surplus page has no object id, so it is refused, not written."""
        generator = BookPDFGenerator(corpus_book())
        self._the_kind_is_a_declared_bitmap()
        blank = Image.new("RGB", (60, 80), "white")
        offered = []

        def four_of_three() -> Iterator[Image.Image]:
            for _ in range(4):
                offered.append(1)
                yield blank

        with pytest.raises(RuntimeError) as raised:
            generator._write_pdf(
                four_of_three(), 3, mode="RGB", kinds=(self._BITMAP_KIND,) * 3
            )

        assert "interior has at least 4 pages, its page plan says 3" in str(
            raised.value
        )
        assert offered == [1] * 4, "the fourth page was asked for, then refused"

    def test_the_plan_tripwires_still_run_before_a_byte_is_written(self):
        """"the page plan prints ..." fires from ``interior_stream`` itself.

        It is the one tripwire whose timing this card could have weakened:
        before, it ran before any page was built; now it must still run before
        the caller opens a file. It does — it raises from the eager half of
        ``interior_stream``, so no writer has been constructed at all.
        """
        generator = BookPDFGenerator(corpus_book())
        walk = BookPDFGenerator.puzzle_pages
        BookPDFGenerator.puzzle_pages = (
            lambda self, payloads, *args, **kwargs: walk(
                self, payloads, *args, **kwargs
            )[:-1]
        )
        try:
            with pytest.raises(RuntimeError) as raised:
                generator.interior_stream(baseline_puzzles())
        finally:
            BookPDFGenerator.puzzle_pages = walk

        assert "the page plan prints" in str(raised.value)

