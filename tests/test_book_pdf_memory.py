"""CARD-145 — the book PDF is written a page at a time (FR-041, FR-043, INV-013).

    AC (new)  TestBookPdfMemory_PeakDoesNotGrowWithPageCount
    AC (new)  TestBookPdfMemory_RealBookExportsUnderTheCap
    AC (new)  TestBookPdfMemory_PagesAreUnchanged
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

Cost: the corpus book is exported **once** for the whole module (a
module-scoped fixture), for a few seconds of real rendering and writing (up
somewhat since CARD-198, which gives every puzzle its own full answer page
instead of a shared packed tile); AC-2's executed cap adds three child
processes, and the whole file still runs well under a minute. The
150-puzzle book is never faked — a page count is the one thing a memory
test must not fake.
"""

from __future__ import annotations

import inspect
import json
import math
import os
import subprocess
import sys
import time
import tracemalloc
import weakref
from dataclasses import dataclass, field, replace
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

import numpy as np
import pytest
from PIL import Image, ImageDraw

from nonogram.admin.book_answer_key import Answer, PackedAnswerPage, answer_title, plan_small_answer_pages
from nonogram.admin.book_pdf_generator import (
    TITLE_PAGE_COUNT,
    FOLIO_PT,
    GUIDE_PAGE_COUNT,
    BookPDFGenerator,
    DividerPagePlan,
    PuzzlePagePlan,
    _answer_extent,
    _band_font,
    _degrade_infeasible_packed_pages,
    _folio_reserve_px,
    _pairable_tier,
    _qr_group_line_px,
    page_frame,
    qr_group_caption,
    qr_link,
    type_px,
)
from nonogram.export.layout import (
    INTERIOR_FOOTER_LINE_PT,
    compute_layout,
    compute_pair_layout,
    interior_frame,
    qr_group_insets,
    qr_slot,
)
from tests.helpers.book_corpus import (
    BASELINE_PAGE_COUNT,
    BASELINE_SHAPE,
    GUIDE_INTERIOR_PAGES,
    CORPUS_PAGE_COUNT,
    CORPUS_PUZZLE_COUNT,
    MATERIALISED_SHAPE,
    STREAMING_SHAPE,
    baseline_puzzles,
    corpus_book,
    corpus_puzzles,
    export_of,
    load_baseline,
    page_digest,
    page_digests,
)
from tests.helpers.page_ink import INK_LEVEL, drawing_of
from tests.helpers.pdf_pages import pdf_page_count, pdf_pages, same_page

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
    # CARD-206 adds the blank title / copyright page: a page factory
    # `interior_stream`'s own producer calls before the guide, so it is
    # wrapped by the instrument like every other one. It draws nothing, but
    # it still allocates a full-size bitmap, which is exactly the quantity
    # this module bounds.
    "create_title_page",
    "create_guide_page",
    "create_divider_page",
    # CARD-200 adds the table of contents page beside the guide and the
    # divider — the same "draw something generic on page_frame" shape, and
    # a page factory `interior_stream`'s own producer calls just like them.
    "create_toc_page",
    "_blank_page",
    "_two_up_page",
    # CARD-198 deleted "_answer_page" (the packed key's own page factory,
    # FR-042) along with the packed key itself — nothing in BookPDFGenerator
    # answers to that name any longer. "solved_puzzle_page" (CARD-197) is
    # its replacement in this list: since CARD-198 it draws a large,
    # unpacked answer's full page; CARD-202 adds "_packed_answer_page"
    # beside it for a page of 2 or 4 small answers — both are page factories
    # interior_stream's own answer-section loop now calls, depending on
    # which kind of page the packing walk planned.
    "solved_puzzle_page",
    "_packed_answer_page",
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


def _two_up_icon_boxes(pair, numbers, dpi) -> list:
    """Every placeholder-QR box a two-up page draws, in order (CARD-248).

    A two-up page's footer strip carries one group per puzzle, both measured
    on the **lower** slot's extent (the one whose ``usable_bottom`` is the
    sheet's bottom margin) at the insets
    :func:`~nonogram.export.layout.qr_group_insets` returns. Until CARD-248
    each *slot* was asked for a box of its own, which answered with the upper
    slot's midline box and nothing at all for the lower.

    The widest line is measured the way ``_two_up_page`` measures it — off
    this page's own two numbers — so the boxes returned here are the boxes
    that page really drew, which is what a mask has to be.
    """
    font = _band_font(type_px(INTERIOR_FOOTER_LINE_PT, dpi))
    widest = max(
        math.ceil(font.getlength(text))
        for number in numbers
        for text in (qr_group_caption(number), qr_link(number))
    )
    insets = qr_group_insets(pair.lower, widest, len(numbers))
    if insets is None:  # pragma: no cover - the walk refuses such a pair
        return []
    return [qr_slot(pair.lower, inset_px=inset) for inset in insets]


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


# --------------------------------------------------------------------------
# The instrument
# --------------------------------------------------------------------------


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
        peak: The largest live total seen, in bytes.
        seen: How many distinct pages were registered — a corpus-size guard,
            so a test cannot pass by measuring a book that was never built.
        page_bytes: The largest single page's cost, for the arithmetic that
            derives the old shape's peak from a measured constant rather than
            from a hard-coded one.
    """

    peak: int = 0
    seen: int = 0
    page_bytes: int = 0
    _live: Dict[int, int] = field(default_factory=dict)

    def watch(self, pages: Iterable[Image.Image]) -> Iterator[Image.Image]:
        """``pages``, costed as they go past and released immediately after."""
        for page in pages:
            self.track(page)
            yield page
            del page

    def track(self, page: Image.Image) -> None:
        """Register one page's bitmap and re-sample the live total."""
        key = id(page)
        if key in self._live:  # already registered, and still alive
            return
        cost = page.width * page.height * len(page.mode)
        self._live[key] = cost
        weakref.finalize(page, self._live.pop, key, None)
        self.seen += 1
        self.page_bytes = max(self.page_bytes, cost)
        self.peak = max(self.peak, sum(self._live.values()))

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
            if isinstance(page, Image.Image):
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
        assert big.seen > 16 * small.seen, "the two books must differ in size"
        assert big.peak == small.peak, (
            f"{big.seen} pages peaked at {big.peak_in_pages:.2f} page bitmaps, "
            f"{small.seen} pages at {small.peak_in_pages:.2f}"
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

    def test_the_same_instrument_sees_the_old_shape_grow(self):
        """Verify by revert: the probe measures the list shape as linear.

        The claim "peak does not grow with the page count" is only worth
        anything if the instrument would have said otherwise about the code
        this card replaced. ``interior_pages`` is still that shape — it returns
        every page in a list — so the same probe, over the same pages of the
        same book, is run across it here: the peak rises by exactly one page
        bitmap per page, which is the 25.2 MB-a-page growth the panel was
        killed by.

        This is the one test in the module that deliberately holds the old
        shape's whole cost — every page of the baseline book at once,
        **202 MB** of live bitmap (a figure predating CARD-128's level
        dividers, left as recorded). That is the point of it, and it is also
        why it is run on the twelve-page book and never on the 305-page one
        (CARD-198: up from 182), whose list would be 7.70 GB.
        """
        pages = BookPDFGenerator(corpus_book()).interior_pages(baseline_puzzles())
        assert len(pages) == BASELINE_PAGE_COUNT

        probe = LivePageBytes()
        peaks = []
        for page in pages:  # the list still holds every one of them
            probe.track(page)
            peaks.append(probe.peak)

        assert peaks == [
            (n + 1) * PAGE_BITMAP_BYTES for n in range(BASELINE_PAGE_COUNT)
        ], peaks
        assert probe.peak == BASELINE_PAGE_COUNT * PAGE_BITMAP_BYTES


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
        # comfortably under ``tests/hang_guard.py``'s 120 s per test, so a
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

    def test_one_cap_the_streaming_shape_survives_and_the_list_shape_dies_under(self):
        """AC-2's second half, **executed**: the same book, one cap, two fates.

        Two fresh interpreters — spawned, never forked, so neither starts
        inside this session's heap — install the same 807.8 MB bound before
        they import PIL, and then export the same 150-puzzle book. The
        streaming child finishes and reports 305 pages *read back out of the
        PDF it wrote*; the list child (``interior_pages``, then written) is
        killed by the cap partway through. Nothing about pytest is at risk:
        the process that dies is a child.

        The bound here is the child's own resident set, watched by a sentry
        thread that calls ``os._exit`` — a real process-level cap, enforced
        against the real process, and not an assertion over an instrumented
        allocation category. It is used because this machine's kernel refuses
        ``RLIMIT_AS`` outright (the twin test below says so with the kernel's
        own words); where ``RLIMIT_AS`` does work, the twin runs the same pair
        under the kernel's bound instead.

        **Why this is not a flake.** The cap is 32 page bitmaps; the streaming
        child measures ~7.80 of them (CARD-198: up from 5.97-6.73 on the
        smaller corpus) and the list shape needs ~307. Both margins are
        re-measured on every run, not trusted: the **export's own** cost —
        the streaming child's resident set less the floor child's, which is
        the half of that figure this code owns — is asserted
        (:data:`CHILD_EXPORT_COST_IN_PAGES`, CARD-237: the assertion used to
        be on the child's total, which drifts with CPython rather than with
        the export and so returned a false red on most full-suite runs), the
        platform's own floor is measured first and skips the test if it has
        grown into the cap (:func:`_habitable`), and the list child is
        required to die *by the cap* — the sentry's exit status and its marker
        on stderr — rather than merely to fail.
        """
        floor, streaming, materialised = _the_pair_under_one_cap(SENTRY_MECHANISM)

        _assert_the_streaming_child_fitted(streaming, floor)

        assert materialised.returncode == CHILD_OVER_CAP_EXIT, (
            "the list shape did not die of the cap: it ended with "
            f"{materialised.outcome}. AC-2's second half rests on it dying, "
            "and on dying for this reason — "
            f"{materialised.stderr.strip()[-500:]!r}"
        )
        assert "OVER THE CAP" in materialised.stderr
        assert materialised.report is None, (
            "the list shape reported a finished export under a cap it cannot "
            "fit — the cap is not being enforced"
        )

    def test_the_same_pair_under_an_address_space_cap_the_kernel_enforces(self):
        """The same two children, bounded by ``setrlimit(RLIMIT_AS)`` instead.

        The mechanism AC-2 really wants: the kernel refuses the memory, so the
        list shape raises :class:`MemoryError` (or dies) without any code of
        ours deciding that it should. It is kept beside the sentry rather than
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
        sentry twin above exists and carries the executed half here.
        """
        verdict = _address_space_cap_verdict()
        if verdict != "bites":
            pytest.skip(
                f"setrlimit(RLIMIT_AS) cannot bound a process on this "
                f"platform — {verdict}. AC-2's executed half is carried here "
                "by test_one_cap_the_streaming_shape_survives_and_the_list_"
                "shape_dies_under (a resident-set sentry) and by the "
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


class TestBookPdfMemory_PagesAreUnchanged:
    """Every exported page is the page the baseline recorded, to the pixel (G-1).

    The evidence is ``tests/helpers/book_corpus.BASELINE_FIXTURE``, currently
    ``tests/fixtures/book_baseline_card198.json`` (CARD-198 is this chain's
    seventh recording — CARD-167 and CARD-184 both superseded it in between
    without a mention here, a pre-existing gap in this docstring's own
    history that CARD-198 does not take on fixing), recorded by exporting
    ``tests/helpers/book_corpus.baseline_puzzles``, reading the pages back
    **out of the PDF** with the shared ``pdf_pages`` helper, and digesting each
    one's raw bitmap. It covers the whole path: draw, JPEG-encode, write,
    parse, decode.

    It was first recorded for CARD-145 at commit ``b4c523d``, the merge-base
    before a line of that card's production change existed, which is the shape
    of evidence a refactor needs. It has been succeeded five times since,
    never regenerated: by CARD-128, which made the interior print grouped by
    level with a divider page opening each; by CARD-144, whose frame (the
    owner's decision of 2026-09-23, not yet a formalised requirement) closes a
    book puzzle page's drawing off with one heavy rectangle; by CARD-149, which
    set the guide page's type at 11 pt derived from the page's own DPI instead
    of 6.7 pt of bare pixels (page 1 alone); by CARD-146, which carried
    CARD-144's frame onto the printed two-up page, which had still been
    printing bare (page 3 alone); and by CARD-147, which writes a
    black-and-white interior as ``DeviceGray``. Each is a deliberate change to
    what the export produces, which is the one case the CARD-145 fixture's own
    ``warning`` provides for, and each recording names the pages that moved
    under it.

    **CARD-147's recording is the first in the chain that moves no page at
    all**, and the test below is where that shows: its page comparison was
    green at CARD-147's implementation commit and only
    :meth:`test_the_interior_file_is_the_length_it_was_recorded_with` was red.
    A colour-space change does not move a page's decoded bitmap — the luma
    plane survives the JPEG round trip in either space, and ``pdf_pages``
    normalises a page to RGB before it is digested — so what the new baseline
    records is ``interior_bytes``, and the eleven unmoved digests are the
    evidence that the colour space moved and the ink did not.

    The comparison is exact — a sha256 of ``Image.tobytes()`` — and
    deliberately not ``pdf_pages.same_page``, which tolerates JPEG noise and a
    6-level mean difference and would hide precisely the kind of change this
    exists to catch.

    That fixture is never to be regenerated to make this test pass; it says so
    in its own ``warning`` field. Its four predecessors sit beside it,
    ``book_baseline_card145.json`` (the merge-base's eight pages),
    ``book_baseline_card128.json`` (the eleven pages the level dividers made),
    ``book_baseline_card144.json`` (the framed single pages) and
    ``book_baseline_card149.json`` (the guide page at book size), all left
    unregenerated. Each was superseded for the one reason that
    warning admits — a deliberate change to what a page prints — and every
    file in the chain says so.

    **The machine's own face costs nothing any more (CARD-221).** It used to
    cost seven of the thirteen pages: the guide pages, the TOC and the four
    dividers were lettered in ``ImageFont.truetype("…/Arial.ttf")`` with a
    ``load_default`` fallback, so a machine whose ``font_fingerprint``
    differed from the fixture's skipped those seven and compared the six that
    were drawn in the bundled band face and Pillow's built-in clue face —
    which on the project's own Linux deployment image, where Arial is not at
    that path, was the difference between six pages of G-1 evidence and none.
    Since CARD-221 every interior face is the packaged one, the fixture's
    ``font_dependent_pages`` is empty, and all thirteen pages are compared
    with no gate at all — on any **host font configuration**, which is the
    axis that gate was about. Not "on any machine": the figures are still a
    function of the installed Pillow/FreeType, which ``pyproject.toml``
    leaves unbounded at ``>=10.0``, and catching a move in *that* is this
    comparison's own job rather than something it is immune to (F-005). The ``same_face`` fixture, the skip,
    the warning and the import of ``font_fingerprint`` are gone with it; the
    measurement that justifies removing them is
    ``tests/test_book_interior_face.py``'s own export-twice comparison and
    the page-by-page record in ``book_baseline_card221.json``.
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
        return pdf_pages(exported_bytes)

    def test_the_book_still_has_the_page_count_it_was_recorded_with(
        self, baseline, exported
    ):
        assert baseline["page_count"] == BASELINE_PAGE_COUNT
        assert len(exported) == baseline["page_count"]

    def test_every_page_is_pixel_identical_to_the_recorded_one(self, baseline, exported):
        now = page_digests(exported)
        recorded = baseline["pages"]

        assert len(now) >= BASELINE_PAGE_COUNT, "the corpus cannot silently shrink"
        # CARD-221: the fixture names NO machine-lettered page, because there
        # is none left to name — every interior face is the packaged one. The
        # list is asserted empty rather than ignored, so a future card that
        # reintroduces a host lookup has to come back here and say so (and
        # bring back a gate of its own with the pages it covers).
        assert set(baseline["font_dependent_pages"]) == set(), (
            "the baseline names machine-lettered interior pages "
            f"{sorted(baseline['font_dependent_pages'])}, and this card's own "
            "claim is that the interior has none: if a host lookup is back, "
            "the gate this test used to carry has to come back with it"
        )

        compared = 0
        for number, (drawn, was) in enumerate(zip(now, recorded, strict=True), start=1):
            assert drawn == was, f"interior page {number} is not the page it was"
            compared += 1

        # Exact, not a floor: every page of the book is compared on every
        # machine now, so a comparison that quietly stopped covering one
        # would show up here instead of passing.
        assert compared == BASELINE_PAGE_COUNT, (
            f"compared {compared} of {BASELINE_PAGE_COUNT} pages — the whole "
            "book's pixel evidence is unconditional since CARD-221"
        )

    def test_the_interior_file_is_the_length_it_was_recorded_with(
        self, baseline, exported_bytes
    ):
        """F-7's other half: the same bytes, not only the same pixels.

        The new writer mirrors ``PdfImagePlugin._save``'s RGB path object for
        object, and the only thing that differs between the merge-base's file
        and this one is the two ``Info`` timestamps — four bytes of digits
        that do not change the file's length. A writer that re-encoded, chose
        another filter or emitted one object more would move this number long
        before it moved a pixel.

        Gated on the host's face until CARD-221, because the seven
        machine-lettered pages were inside this file and a different Arial
        gave their JPEG streams a different length. Ungated now: every page
        in the file is lettered from packaged data, so the length does not
        depend on what fonts the host has installed.

        **Not "the same number on every machine"** (AC/EC/G gate, F-G2 —
        and this docstring is the one place that overstatement mattered
        most, since this card names this test as what would catch a
        rasteriser change). The bytes are a JPEG encode of pages whose type
        is rasterised by the installed FreeType, and ``pyproject.toml``
        floors Pillow at ``>=10.0`` with no ceiling. A different build can
        move a glyph and with it this number — which is exactly what this
        assertion is for: it reds on the machine that moved, instead of the
        move reaching a printed book.
        """
        assert len(exported_bytes) == baseline["interior_bytes"]

    def test_the_corpus_covers_every_page_kind_the_interior_has(self, exported):
        """The evidence's own premise: fourteen pages, one of every kind.

        A baseline of fourteen identical blank pages would pass the
        comparison above and prove nothing — but so would fourteen *distinct*
        pages of the wrong kinds. Dropping a divider for a fifth answer page
        keeps them all distinct while the baseline silently stops covering
        the divider. So each kind is identified positively, and distinctness
        is kept beside it. The book prints grouped easy, medium, hard
        (INV-009, CARD-128), so the kinds run:

        * page 1 is the blank title / copyright page (CARD-206), identified
          by the one thing on it — nothing: it is the only page of the book
          with no ink at all, which the distinctness sweep at the end of this
          test could never say on its own;
        * pages 2 and 3 are the guide's own two pages (CARD-201), page 4 is
          the table of contents (CARD-200: this 4-puzzle book's TOC always
          fits one page), page 11 the SOLUTIONS divider, and pages 5, 7 and
          9 the "Easy", "Medium" and "Hard" level dividers — each compared
          against the page the generator draws for it;
        * page 6 is the two-up page (FR-040), the book's two easy 10x10s:
          each half of it carries its own complete 10x10 grid, which no
          single-puzzle page can do;
        * pages 8 and 10 are single-puzzle pages, and the 15x15 medium and the
          30x30 hard the baseline book declares are **read back off their
          ink** (``drawing_of``), not asked of the layout — in that order,
          because the levels print in that order;
        * pages 12-14 are answer pages (CARD-206's title page shifts the
          section by one more, on top of CARD-200's TOC and CARD-201's guide
          growth; CARD-202: Duck and
          Owl, both small enough to pack, share packed page 12; Tree, the
          only qualifying answer in its level, packs alone onto page 13;
          Snowflake, too large to qualify, still gets CARD-198's own full
          page 14) — each carries solid blocks of ink a filled cell wide,
          which no blank puzzle page or divider has anywhere on it (the
          guide pages have, since CARD-167/CARD-201: the worked example and
          the other line diagrams).
        """
        assert len(exported) == BASELINE_PAGE_COUNT
        generator = BookPDFGenerator(corpus_book())

        assert np.asarray(exported[0].convert("L")).min() == 255, (
            "interior page 1 is the blank title page (CARD-206) — no ink at all"
        )
        assert same_page(exported[1], generator.create_guide_page(4, 2, 1, 1, page_number=2))
        assert same_page(exported[2], generator.create_guide_page(4, 2, 1, 1, page_number=3))
        assert same_page(exported[10], generator.create_divider_page(11))
        for number, level in ((5, "Easy"), (7, "Medium"), (9, "Hard")):
            assert same_page(
                exported[number - 1], generator.create_divider_page(number, level)
            ), f"interior page {number} should be the {level!r} level divider"

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

        for number in (12, 13, 14):
            assert solid_ink_blocks(exported[number - 1]), (
                f"interior page {number} should be an answer page, whose "
                "filled cells are solid blocks of ink"
            )
        # Not pages 2-3: since CARD-167/CARD-201 the guide's own worked
        # example and line diagrams draw filled squares too. They are
        # identified positively above, as the pages the generator draws for
        # the guide, so they cannot pass for an answer page here. Not page
        # 4 either (CARD-200's TOC): a listing of plain text rows, no filled
        # cell on it at all. Not page 1 either (CARD-206's title page): it
        # carries no ink of any kind, asserted directly above.
        #
        # CARD-204 (SCOPE+): pages 6, 8 and 10 now also carry a placeholder
        # QR icon, whose checkerboard modules (~47 px square) are each
        # themselves a solid block at least FILLED_CELL_PROBE (20 px) wide —
        # masked out below before the check, the same "this is decoration,
        # not a cell" exclusion the AC-7 class already applies elsewhere,
        # so this still proves the *grid* carries no revealed cell rather
        # than being defeated by the icon's own, unrelated solid ink.
        plan = generator.section_plan(baseline_puzzles())

        def _icon_boxes(page_number: int) -> list:
            for entry in plan.pages:
                if entry.page_number != page_number:
                    continue
                spec = generator.page_spec(page_number)
                if entry.pair is None:
                    payload = plan.payloads[entry.numbers[0] - 1]
                    layout = compute_layout(payload.row_clues, payload.column_clues, spec)
                    icon = qr_slot(layout)
                    return [icon] if icon is not None else []
                return _two_up_icon_boxes(entry.pair, entry.numbers, generator.dpi)
            return []

        for number in (4, 5, 6, 7, 8, 9, 10, 11):
            page = exported[number - 1]
            boxes = _icon_boxes(number) if number in (6, 8, 10) else []
            if boxes:
                page = page.copy()
                draw = ImageDraw.Draw(page)
                for box in boxes:
                    draw.rectangle(
                        (box.left - 2, box.top - 2, box.right + 2, box.bottom + 2),
                        fill=(255, 255, 255),
                    )
            assert not solid_ink_blocks(page), (
                f"interior page {number} carries filled cells — it is an "
                "answer page, and the baseline no longer covers its kind"
            )

        for first in range(len(exported)):
            for second in range(first + 1, len(exported)):
                assert not same_page(exported[first], exported[second]), (
                    f"interior pages {first + 1} and {second + 1} are the same "
                    "page — the baseline no longer covers every page kind"
                )

    def test_the_digest_would_have_caught_a_changed_page(self):
        """The comparison has teeth: one flipped pixel changes the digest."""
        page = Image.new("RGB", (40, 40), "white")
        before = page_digests([page])
        page.putpixel((7, 9), (0, 0, 0))

        assert page_digests([page]) != before


# --------------------------------------------------------------------------
# CARD-204 AC-7 — every page that carries no drawing is byte-identical
# --------------------------------------------------------------------------


# CARD-221 removed CARD-204's AC-7b instrument from this file:
# ``_GUIDE_SCATTER_SHARE_CEILING`` (1% of a page), ``_GUIDE_SCATTER_GREY_TOLERANCE``
# (64 grey levels) and ``_one_pixel_displacement_outliers`` (a 3x3
# neighbourhood search), together with the test that used them,
# ``test_the_guide_pages_scatter_is_bounded_to_one_pixel_of_displacement``.
#
# What they measured was that CARD-204's *incidental, sub-pixel* scatter on
# the two guide pages stayed inside a bound: under 1% of the page differing
# (measured then: 0.183% and 0.192%), and every differing pixel explained by
# ink that had moved at most one pixel (0 outliers on either page). That claim
# cannot be restated after CARD-221, which deliberately re-letters both pages
# in the packaged face: re-measured at HEAD with the deleted instrument's
# own rule, page 1 differs from the CARD-200 recording in 7.596% of its
# pixels and page 2 in 10.531%, with 254,766 and 478,630 differing pixels
# that no 1 px displacement at its own 64-grey tolerance explains.
#
# It is not re-anchored at CARD-221's own pages either, and that was tried
# first: the deleted test's own ``moved > 0`` assertion exists precisely to
# stop the bound being measured against nothing, so a reference taken from
# the same render it is compared with would have made it vacuous (0 pixels
# differing) by that test's own definition. What replaces it is stronger and
# unconditional on any host font configuration: both guide pages are pixel for
# pixel against ``book_baseline_card221.json`` by
# ``TestBookPdfMemory_PagesAreUnchanged``, and
# ``test_the_guide_pages_are_the_documented_exception_not_an_unbounded_one``
# below keeps the "still the guide pages, still the same size, still not the
# CARD-200 pixels" claims and the stored images' own integrity check.


class TestBookPdfMemory_NonDrawingPagesAreByteIdentical:
    """AC-7 — the TOC and every divider are untouched by CARD-204; the guide
    pages carry one discovered, narrow exception.

    This card's right-alignment and QR-slot changes are meant to touch only
    pages whose drawing is placed by ``compute_layout``'s page-wide
    centring clause, and whose own puzzle has some horizontal spare to
    actually move by: on the baseline book that is just the two
    single-puzzle pages (7, 9) and the two-up page (5) — see
    ``STRICTLY_UNCHANGED_PAGES``'s own comment for why none of the three
    answer pages (11-13) is moved by this card either, each for its own,
    investigated reason. All four dividers (4, 6, 8, 10) confirm the
    untouched claim too: 0 pixels differ from ``book_baseline_card200.json``
    on any of them.

    **A third baseline, for the same reason the second one exists
    (CARD-205).** The TOC (3) used to sit in that "0 pixels differ from
    CARD-200" group, and legitimately did — until CARD-205, the card
    immediately after this one, replaced its per-puzzle listing with a
    structural one. That is a *later* card's deliberate ink change landing
    on a page this class had claimed as CARD-204's evidence — the same
    situation CARD-203's caption move created for pages 11-13 — and it gets
    the same treatment rather than an exemption: page 3 moves to
    ``CARD205_TOC_PAGE``, is compared just as strictly against
    ``book_baseline_card205.json``, and the attribution is itself measured
    (:meth:`test_the_toc_page_moved_under_card205_not_card204` asserts that
    CARD-200's and CARD-205's recordings of that page differ while
    CARD-204's still agrees with CARD-200's, which is what makes "CARD-205
    moved it, CARD-204 did not" a fact about three fixtures). Dropping it
    was rejected for the reason stated below: a page nobody compares is a
    page with no evidence.

    **Two pre-card baselines, not one (CARD-204 Fix 7, merge gate).** Until
    the merge gate this class compared all eight of those pages against
    CARD-200's recording and said, of each, that it "carries no drawing, so
    CARD-204 must leave it byte-identical to the CARD-200 baseline". For the
    three answer pages that sentence is now false *and* mis-attributed:
    CARD-203 — merged to main after this branch was cut — right-aligns their
    caption and lifts it to a fixed gap above the drawing, so they differ
    from CARD-200 for a reason that has nothing to do with this card. Of the
    two honest repairs (compare them against a baseline that includes
    CARD-203, or assert the CARD-203-attributed difference explicitly) this
    class does **both**, because each alone leaves a hole: the strict digest
    comparison moves to ``book_baseline_card203.json``, which is the last
    recording taken before this branch's own changes and the first that
    includes the caption move
    (:meth:`test_the_three_answer_pages_still_match_the_card203_baseline`),
    and the attribution is itself measured — those pages differ from
    CARD-200, and already differed in CARD-203's own recording
    (:meth:`test_the_three_answer_pages_moved_under_card203_not_this_card`),
    which is what makes "CARD-203 moved them" a fact about the fixtures
    rather than a sentence in a docstring. Dropping them from the comparison
    was rejected: a page nobody compares is a page with no evidence, and
    this class exists to produce evidence per page.

    **The two guide pages (1, 2) do not quite hold the same promise, and
    this is investigated, not assumed.** ``create_guide_page``'s worked
    examples and cell-state icons are drawn through
    ``example_line_layout``/``guide_icon_layout``, which call
    ``compute_layout`` on the book's own placed ``PageSpec`` — not to place
    themselves on the page (``draw_example_line`` crops tight to its own ink
    and the guide page pastes the crop at ``frame.left``, a fixed margin
    unrelated to this card), but to borrow the book's own cell pitch and
    rule widths for internal consistency (ADR-0036/R2, G-3: "no new
    placement arithmetic, only a narrower slice of what compute_layout
    already returns"). ``compute_layout``'s placed-page branch rounds each
    grid boundary independently (``_boundaries``'s own docstring: "within
    half a pixel"), and that per-boundary rounding depends on the *absolute*
    anchor's own fractional part — which this card's formula change moves,
    even though the crop that actually reaches the page is relative. Measured
    directly (git-stash diff against the pre-card renderer): pages 1 and 2
    move by a scatter of 1px rule-edge shifts inside the worked-example
    diagrams (roughly 15000 pixels of a 2550x3300 page, i.e. well under 1%,
    all accounted for by rules/fills shifting at most one device pixel);
    pages 3, 4, 6, 8 and 10 move by zero pixels. This is the same shape of
    "page 1 moved for a reason unrelated to its own content" the baseline
    chain has already absorbed twice (CARD-149's type-size fix, CARD-167's
    retitling) — flagged here and in this card's own Worktree notes for the
    architect/owner, not silently treated as in-scope for this card to
    eliminate (doing so would mean giving ``example_line_layout`` its own
    placement arithmetic, which G-3 forbids these helpers from having).

    **That exception is bounded, not merely described** (AC-7b, the
    owner's 2026-10-13 decision to “bound it with a test, then merge”):
    :meth:`test_the_guide_pages_scatter_is_bounded_to_one_pixel_of_displacement`
    asserts both halves of the measurement above — under 1% of the page
    differing at all, and every differing pixel explained by ink that
    moved at most one pixel — against the pre-card pixels themselves, so
    a later card that displaces these diagrams further fails here
    instead of inheriting the prose.
    """

    #: The baseline book's own page-kind split (CARD-200's recording;
    #: ``tests/helpers/book_corpus.py``'s own docstring, and
    #: ``TestBookPdfMemory_PagesAreUnchanged``'s positively-identified kinds
    #: above): the pages right-alignment never touches, and the ones
    #: CARD-204 deliberately repositions (and, on 5/7/9, adds a placeholder
    #: QR icon to). Two exceptions below, both measured (git-stash diff
    #: against the pre-card renderer), neither assumed:
    #:
    #: * **Pages 11 and 12** are CARD-202's own *packed* answer pages
    #:   (Duck+Owl share 11, Tree packs alone onto 12) —
    #:   ``_packed_tile_layout`` centres each tile across its **own** tile
    #:   width, a local formula FR-032's page-wide centring/right-alignment
    #:   clause was never about (this card's own investigation named
    #:   exactly two call sites for that clause, ``compute_layout`` and
    #:   ``_slot_layout`` — neither is this one): 0 pixels moved.
    #: * **Page 13** (Snowflake's own full, unpacked answer page) *does*
    #:   reuse ``compute_layout``. CARD-204 left it unmoved by a coincidence
    #:   of this puzzle's own geometry — its extent is exactly page-fit-bound
    #:   on both axes (AC-175's own case: the cell is fitted, not capped), so
    #:   its horizontal ``spare`` is exactly 0 and centring's
    #:   ``usable_left + spare / 2`` and right-alignment's flush formula
    #:   collapsed to the same pixel — and that card's own note said a
    #:   Snowflake-sized puzzle with any spare at all would move like pages
    #:   5/7/9 do.
    #:
    #:   **CARD-224 moves it, through the other axis.** That card floats
    #:   every placed drawing at 42% of its puzzle area's spare *height*,
    #:   and this page's vertical spare is not zero (the page-fit bound is
    #:   the width's; the puzzle area is one footer strip shallower than the
    #:   height the cell was fitted against), so the drawing — and with it
    #:   the caption CARD-203 hangs a fixed gap below it — sits lower on the
    #:   page. It is therefore no longer in the group below: see
    #:   :attr:`CARD224_FLOATED_PAGE`.
    #:
    #: **CARD-204 Fix 7 (merge gate): pages 11-13 are still unmoved BY THIS
    #: CARD, and are no longer compared against CARD-200.** Both statements
    #: above remain true and measured — but CARD-203 merged to main between
    #: this branch being cut and the merge gate running, and it moves all
    #: three answer pages (it right-aligns their caption and lifts it to a
    #: fixed gap above the drawing). "Byte-identical to CARD-200" is
    #: therefore false of them now, and was never CARD-204's to promise:
    #: they are compared against ``book_baseline_card203.json`` instead —
    #: see :attr:`CARD203_CAPTION_PAGES`.
    #: **CARD-205 removed interior page 3 (the TOC) from this group.** The
    #: group's claim is "byte-identical to CARD-200's recording", and it was
    #: true of the TOC right up to this card, which deliberately rewrites
    #: what that page says: the per-puzzle listing becomes a structural one
    #: (the guide, each level's heading and ``Puzzles N–M`` range, the
    #: solutions), with leader dots. That is not an exception to be excused
    #: here — it is another card's own change, exactly as CARD-203's caption
    #: move was for pages 11-13 — so page 3 moves to :attr:`CARD205_TOC_PAGE`
    #: and is compared, just as strictly, against CARD-205's own recording.
    #: The four level dividers stay: nothing in that card touches them, and
    #: ``test_every_divider_still_matches_the_card200_baseline`` is what says
    #: so. The *reason* that matters is that a divider and the TOC are the
    #: only two "front matter" page kinds, so dropping both would leave the
    #: group with nothing to prove.
    #: **CARD-206 (SCOPE+): every page number in this class is a number in
    #: the STORED recordings, not an index into this book's own export.**
    #: That card reserves the blank title / copyright page as interior page 1,
    #: so the page CARD-222 recorded as *n* is exported as *n +
    #: TITLE_PAGE_COUNT* now — and because the marks that share a page's
    #: footer band sit against its **outer** and **inner** edges, the shift
    #: mirrors them as well as changing the folio's digits. (Measured on the
    #: render, review cycle 1 F-103/F-104: on a page that carries the frame
    #: the folio itself is **centred** and does not move — it is the QR group
    #: and the grid-size label that change sides. On the guide, TOC, divider
    #: and answer pages, which carry no frame, the folio is the outer-corner
    #: mark and does mirror.) Every one
    #: of this class's live pages therefore differs from CARD-222's recording,
    #: and the forward reference each group owes its byte-identity to is
    #: CARD-206's own (:meth:`card206_baseline`), read at the live index. The
    #: attributions between the *stored* fixtures are statements about files
    #: and are untouched. The claim that nothing but the pagination moved is
    #: not this class's to make — it belongs to
    #: :class:`TestBookPdfMemory_ContentAboveTheFooterBandIsUnchanged`, which
    #: compares each page against the same unedited drawing function called at
    #: its pre-CARD-206 position with the footer band cropped away.
    #:
    #: The one page with no stored counterpart is the title page itself:
    #: it has no historical number, so it sits in no group below and its
    #: evidence is
    #: :meth:`TestBookPdfMemory_PagesAreUnchanged.test_the_corpus_covers_every_page_kind_the_interior_has`'s
    #: own "no ink of any kind" assertion plus the whole-book digest
    #: comparison beside it.
    LIVE_OFFSET = TITLE_PAGE_COUNT

    STRICTLY_UNCHANGED_PAGES = (4, 6, 8, 10)

    #: Interior page 3, the table of contents. CARD-205 rewrites its rows,
    #: so it is byte-identical to **CARD-205's** recording and deliberately
    #: not to CARD-200's — both halves asserted below, the second one so the
    #: attribution stays a measurement rather than a sentence.
    CARD205_TOC_PAGE = (3,)

    #: The three answer pages (CARD-202's two packed ones and Snowflake's
    #: full one). CARD-204 leaves them byte-identical — the reasons are the
    #: two bullets above, unchanged — but CARD-203 does not, so the baseline
    #: they owe that identity to is CARD-203's own recording, the last one
    #: taken before this branch's changes and the first one that includes
    #: the caption move. Compared exactly as strictly as the group above,
    #: against a different (later) fixture, rather than dropped from the
    #: comparison: a page nobody compares is a page with no evidence, and
    #: ``test_the_three_answer_pages_moved_under_card203_not_this_card``
    #: below keeps the attribution honest by asserting they *do* differ from
    #: CARD-200.
    CARD203_CAPTION_PAGES = (11, 12)

    #: Interior page 13, Snowflake's own full answer page. CARD-204 left it
    #: byte-identical by the zero-spare coincidence recorded above; CARD-224's
    #: 42% float moves it, because its *vertical* spare is not zero. It is
    #: kept in this class's own accounting — with its own fixture comparison
    #: and its own attribution test — rather than dropped from the page kinds
    #: this class produces evidence for, for the reason the paragraphs above
    #: give: a page nobody compares is a page with no evidence.
    CARD224_FLOATED_PAGE = (13,)
    GUIDE_PAGES = (1, 2)
    NON_DRAWING_PAGES = (
        STRICTLY_UNCHANGED_PAGES
        + CARD205_TOC_PAGE
        + CARD203_CAPTION_PAGES
        + CARD224_FLOATED_PAGE
        + GUIDE_PAGES
    )
    DRAWING_PAGES = (5, 7, 9)

    @pytest.fixture(scope="class")
    @classmethod
    def baseline(cls) -> Dict[str, Any]:
        """The **pre-CARD-204** recording, loaded directly rather than
        through ``load_baseline()`` — that helper now points at
        ``book_baseline_card204.json``, this card's own forward baseline,
        against which every page would trivially match itself. What this
        class needs is the *previous* card's evidence, to prove this
        card's own change reached only the pages it meant to.
        """
        fixtures_dir = Path(__file__).resolve().parent / "fixtures"
        with (fixtures_dir / "book_baseline_card200.json").open(encoding="utf-8") as handle:
            return json.load(handle)

    @pytest.fixture(scope="class")
    @classmethod
    def card203_baseline(cls) -> Dict[str, Any]:
        """CARD-203's own recording — the pre-CARD-204 evidence for the three
        pages CARD-203 itself moved (CARD-204 Fix 7).

        Loaded directly for the same reason :meth:`baseline` is, and kept
        beside it rather than replacing it: the TOC and the four dividers
        have owed their byte-identity to CARD-200 since this card was cut and
        still do, and re-pointing them at a later fixture would quietly widen
        what "untouched" is measured against.
        """
        fixtures_dir = Path(__file__).resolve().parent / "fixtures"
        with (fixtures_dir / "book_baseline_card203.json").open(encoding="utf-8") as handle:
            return json.load(handle)

    @pytest.fixture(scope="class")
    @classmethod
    def card204_baseline(cls) -> Dict[str, Any]:
        """CARD-204's own recording — the *other* half of the TOC's
        attribution (review cycle 1, F-002).

        ``test_the_toc_page_moved_under_card205_not_card204`` promised a fact
        about three fixtures and loaded two, which left "CARD-204 did not move
        it" narrated rather than measured — in the one class whose whole
        purpose is turning such claims into comparisons. Loaded directly by
        name for the same reason the other two are.
        """
        fixtures_dir = Path(__file__).resolve().parent / "fixtures"
        with (fixtures_dir / "book_baseline_card204.json").open(encoding="utf-8") as handle:
            return json.load(handle)

    @pytest.fixture(scope="class")
    @classmethod
    def card205_baseline(cls) -> Dict[str, Any]:
        """CARD-205's own recording — the evidence for the one page CARD-205
        itself moved, the table of contents.

        Loaded directly by name rather than through ``load_baseline()``,
        exactly as :meth:`baseline` and :meth:`card203_baseline` are, so
        that this class keeps naming the fixture each claim rests on. It
        happens to be what ``BASELINE_FIXTURE`` points at today; naming it
        here means the next card to record a forward baseline does not
        silently widen what "the TOC is unchanged" is measured against.
        """
        fixtures_dir = Path(__file__).resolve().parent / "fixtures"
        with (fixtures_dir / "book_baseline_card205.json").open(encoding="utf-8") as handle:
            return json.load(handle)

    @pytest.fixture(scope="class")
    @classmethod
    def card221_baseline(cls) -> Dict[str, Any]:
        """CARD-221's own recording — the evidence for the seven pages that
        card moved, which is every page the interior used to letter in the
        **host's** Arial (the two guide pages, the TOC and the four
        dividers).

        Loaded directly by name, like every other fixture this class names,
        so that each claim below still says which recording it rests on. It
        is what ``BASELINE_FIXTURE`` points at today; naming it here means
        the next card to record a forward baseline does not silently widen
        what "unchanged since CARD-221" is measured against.

        **The ``same_face`` fixture this replaces is gone.** It compared
        ``font_fingerprint()`` against the baseline's, and every comparison
        below skipped the machine-lettered pages where they differed; its
        condition — interior pixels that depend on the host's fonts — is
        what CARD-221 removed, and the comparisons below are unconditional
        on any host font configuration now. (Not on any Pillow/FreeType
        build — that lever is unbounded and these comparisons are what
        would catch it moving; F-005.)
        """
        fixtures_dir = Path(__file__).resolve().parent / "fixtures"
        with (fixtures_dir / "book_baseline_card221.json").open(encoding="utf-8") as handle:
            return json.load(handle)

    @pytest.fixture(scope="class")
    @classmethod
    def card222_baseline(cls) -> Dict[str, Any]:
        """CARD-222's own recording — the forward baseline every live
        comparison in this class now rests on.

        That card lands CON-018's amendment of 2026-10-17: three of the four
        margins move, so **every** page of the interior moves with them (its
        own ``changed_pages`` is all thirteen, the only recording in this
        chain for which that is true). The per-page attributions below are
        unchanged in kind — each still names the card that last moved its page
        and asserts the move against that card's stored fixture — but the
        card they name for the live page is this one, and the fixture that
        used to hold the live page is now asserted to *differ* from it. It is
        loaded by name, like every other fixture here, so each claim still
        says which recording it rests on.
        """
        fixtures_dir = Path(__file__).resolve().parent / "fixtures"
        with (fixtures_dir / "book_baseline_card222.json").open(encoding="utf-8") as handle:
            return json.load(handle)

    @pytest.fixture(scope="class")
    @classmethod
    def card206_baseline(cls) -> Dict[str, Any]:
        """CARD-206's own recording — the forward baseline every live
        comparison in this class now rests on.

        That card reserves the blank title / copyright page as interior page
        1, so **every** page of the interior moves one place later and flips
        parity with it (its own ``changed_pages`` is all fourteen, and its own
        note records that it therefore has no control page). The per-page
        attributions below are unchanged in kind — each still names the card
        that last moved its page and asserts the move against that card's
        stored fixture — but the card they name for the live page is this one,
        and CARD-222's fixture, which used to hold the live page, is now
        asserted to *differ* from it. Loaded by name, like every other fixture
        here, so each claim still says which recording it rests on.
        """
        fixtures_dir = Path(__file__).resolve().parent / "fixtures"
        with (fixtures_dir / "book_baseline_card206.json").open(encoding="utf-8") as handle:
            return json.load(handle)

    @pytest.fixture(scope="class")
    @classmethod
    def card248_baseline(cls) -> Dict[str, Any]:
        """CARD-248's own recording — the last one taken before CARD-224, and
        the evidence for the one page **this** card moves inside this class's
        own accounting (interior 13, Snowflake's full answer page).

        Loaded directly by name, like every other fixture here, so that the
        claim "nothing between CARD-222 and CARD-248 moved page 13, and
        CARD-224 did" is a fact about three files rather than a sentence.
        """
        fixtures_dir = Path(__file__).resolve().parent / "fixtures"
        with (fixtures_dir / "book_baseline_card248.json").open(encoding="utf-8") as handle:
            return json.load(handle)

    @pytest.fixture(scope="class")
    @classmethod
    def exported(cls) -> List[Image.Image]:
        return pdf_pages(export_of(BookPDFGenerator(corpus_book()), baseline_puzzles()))

    def test_every_divider_still_matches_the_card206_baseline(
        self, baseline, card221_baseline, card222_baseline, card206_baseline, exported
    ) -> None:
        """A divider carries one word and nothing else, so only a card that
        changes that word or the face it is set in may move it.

        **CARD-221 was such a card, and CARD-222 is another** — the first
        lettered the divider in the packaged face instead of the host's Arial,
        the second moved three of CON-018's four margins (2026-10-17), which
        moves the one word this page carries along with the text block it is
        centred in. So the live comparison is against CARD-222's recording and
        the attribution is asserted beside it rather than written down: each
        divider differs from the CARD-200 recording (the face moved it), then
        from CARD-221's (the margins moved it), and is identical to CARD-222's
        (nothing has moved it since). Before CARD-221 these pages owed their
        byte-identity to CARD-200 and the comparison skipped them wherever the
        host's face differed from the fixture's; it is unconditional now.
        """
        # The groups are numbered in the STORED recordings (see LIVE_OFFSET),
        # so they cover every page CARD-222's thirteen-page book had — one
        # fewer than this book's own fourteen, the missing one being
        # CARD-206's title page, which no earlier recording has a page for.
        stored_page_count = BASELINE_PAGE_COUNT - self.LIVE_OFFSET
        assert set(self.NON_DRAWING_PAGES) | set(self.DRAWING_PAGES) == set(
            range(1, stored_page_count + 1)
        ), "the split above must cover every stored baseline page exactly once"
        assert (
            len(self.NON_DRAWING_PAGES) + len(self.DRAWING_PAGES) == stored_page_count
        ), "...and exactly once: no page may sit in two groups at the same time"

        now = page_digests(exported)
        compared = 0
        for number in self.STRICTLY_UNCHANGED_PAGES:
            assert number in card221_baseline["changed_pages"], (
                f"interior page {number} is a divider lettered through "
                "_guide_face, so CARD-221's own recording must name it among "
                "the pages that card moved"
            )
            assert now[number - 1 + self.LIVE_OFFSET] != baseline["pages"][number - 1], (
                f"interior page {number} still matches the CARD-200 "
                "recording, so the packaged face never reached this divider "
                "— CARD-221's own change did not happen here"
            )
            assert now[number - 1 + self.LIVE_OFFSET] != card221_baseline["pages"][number - 1], (
                f"interior page {number} still matches the CARD-221 "
                "recording, so CON-018's amended margins never reached this "
                "divider — CARD-222's own change did not happen here"
            )
            assert now[number - 1 + self.LIVE_OFFSET] != (
                card222_baseline["pages"][number - 1]
            ), (
                f"stored page {number} is a level or SOLUTIONS divider, and "
                "CARD-206 moved it: its folio reads one number higher and "
                "sits in the opposite bottom corner. If it still matches "
                "CARD-222's recording, the title page never reached this "
                "divider"
            )
            assert now[number - 1 + self.LIVE_OFFSET] == (
                card206_baseline["pages"][number - 1 + self.LIVE_OFFSET]
            ), (
                f"stored page {number} is a level or SOLUTIONS divider — it "
                "carries one word and nothing else, so nothing after CARD-206 "
                "may move it off that card's baseline"
            )
            compared += 1
        assert compared == len(self.STRICTLY_UNCHANGED_PAGES), compared

    def test_the_toc_page_matches_the_card206_baseline(
        self, card205_baseline, card221_baseline, card222_baseline, card206_baseline,
        exported
    ) -> None:
        """The TOC's rows are CARD-205's wording, CARD-221's face and CARD-222's
        text block.

        Compared exactly as strictly as the dividers above, against the
        recording that holds both, rather than dropped from the comparison:
        a page nobody compares is a page with no evidence, and this class
        exists to produce evidence per page. The reference moved forward
        from CARD-205's recording to CARD-221's because that card re-set
        every row in the packaged face (the rows are 49 px tall on it
        against Arial's 48), and forward again to CARD-222's because
        CON-018's amended margins move the frame every row is set inside. The
        three-fixture attribution below says so rather than leaving either
        move unexplained. Face-gated until CARD-221; unconditional now.
        """
        now = page_digests(exported)
        for number in self.CARD205_TOC_PAGE:
            assert now[number - 1 + self.LIVE_OFFSET] != card205_baseline["pages"][number - 1], (
                f"interior page {number} still matches the CARD-205 "
                "recording — the packaged face never reached the table of "
                "contents, and CARD-221's own change did not happen here"
            )
            assert now[number - 1 + self.LIVE_OFFSET] != card221_baseline["pages"][number - 1], (
                f"interior page {number} still matches the CARD-221 "
                "recording — CON-018's amended margins never reached the "
                "table of contents, and CARD-222's own change did not happen "
                "here"
            )
            assert now[number - 1 + self.LIVE_OFFSET] != (
                card222_baseline["pages"][number - 1]
            ), (
                f"stored page {number} is the table of contents, and CARD-206 "
                "moved it with every other page: its folio reads one number "
                "higher and sits in the opposite bottom corner"
            )
            assert now[number - 1 + self.LIVE_OFFSET] == (
                card206_baseline["pages"][number - 1 + self.LIVE_OFFSET]
            ), (
                f"stored page {number} is the table of contents: CARD-205 "
                "rewrote its rows, CARD-221 re-set them in the packaged face, "
                "CARD-222 moved the frame they sit in, CARD-206 moved its "
                "page number and its folio's corner and nothing since has, "
                "so it must be byte-identical to the CARD-206 baseline"
            )

    def test_the_toc_page_moved_under_card205_not_card204(
        self, baseline, card204_baseline, card205_baseline, card221_baseline,
        card222_baseline, exported
    ) -> None:
        """The attribution, measured rather than written down — the same
        shape :meth:`test_the_three_answer_pages_moved_under_card203_not_this_card`
        uses for CARD-203's pages.

        Page 3 differs from CARD-200's recording, and that difference is
        already in CARD-205's own fixture, while CARD-204's recording still
        agrees with CARD-200 on it. So "CARD-205 moved it, CARD-204 did not"
        is a fact about the three fixtures, not a claim in a docstring.

        **All three fixtures are read** (review cycle 1, F-002): the
        CARD-204 half used to be asserted nowhere, which made the "not
        CARD-204" clause of this test's own name a sentence rather than a
        measurement. It is now the first assertion below, and it is the one
        that fails if a later card re-records CARD-204's fixture off a
        rewritten TOC.

        **The face gate that used to sit in the middle of this test is gone**
        (CARD-221). It was placed there rather than at the top because the
        attribution is a statement about *stored* recordings and holds on any
        machine, while the two comparisons that read this machine's own
        export were machine-lettered — the project's own "only the pinned
        figure is skipped, never the guardrail" rule, applied to the one test
        added to close F-002. Since the interior letters from packaged data
        those two comparisons hold on any host font configuration too — the
        clause above says "any machine" of a comparison between two *stored*
        fixtures, which really is machine-independent; this one reads this
        machine's own export and is only as portable as its Pillow/FreeType
        (F-005). The live page is
        compared against CARD-221's recording (which re-set every row in that
        face) with the move attributed to it, rather than against CARD-205's.
        """
        for number in self.CARD205_TOC_PAGE:
            card200_page = baseline["pages"][number - 1]
            card204_page = card204_baseline["pages"][number - 1]
            card205_page = card205_baseline["pages"][number - 1]
            assert card204_page == card200_page, (
                f"interior page {number} differs between the CARD-200 and "
                "CARD-204 recordings — CARD-204 then moved the table of "
                "contents too, and this card's own attribution of it is wrong"
            )
            assert card205_page != card200_page, (
                f"interior page {number} is identical in the CARD-200 and "
                "CARD-205 recordings — CARD-205 is then not what moved it, "
                "and this class's own split is mis-attributed"
            )

        now = page_digests(exported)
        for number in self.CARD205_TOC_PAGE:
            card200_page = baseline["pages"][number - 1]
            card205_page = card205_baseline["pages"][number - 1]
            card221_page = card221_baseline["pages"][number - 1]
            assert card221_page != card205_page, (
                f"interior page {number} is identical in the CARD-205 and "
                "CARD-221 recordings — CARD-221's packaged face is then not "
                "what re-set the table of contents, and the live comparison "
                "below is measured against the wrong fixture"
            )
            card222_page = card222_baseline["pages"][number - 1]
            assert card222_page != card221_page, (
                f"interior page {number} is identical in the CARD-221 and "
                "CARD-222 recordings — CON-018's amended margins are then not "
                "what moved the table of contents, and the live comparison "
                "below is measured against the wrong fixture"
            )
            assert now[number - 1 + self.LIVE_OFFSET] != card222_page
            assert now[number - 1 + self.LIVE_OFFSET] != card221_page
            assert now[number - 1 + self.LIVE_OFFSET] != card205_page
            assert now[number - 1 + self.LIVE_OFFSET] != card200_page

    def test_the_three_answer_pages_still_match_the_card206_baseline(
        self, card203_baseline, card222_baseline, card206_baseline, exported
    ) -> None:
        """CARD-204 Fix 7 — the same strict claim as the test above, against
        the fixture that legitimately holds the last move.

        **CARD-222 is that fixture now.** CARD-203 moved these three pages'
        captions and nothing between it and CARD-222 moved them again; then
        CON-018's amended margins (2026-10-17) moved the text block every
        answer tile is laid out in, so all three moved with it. Both halves
        are asserted: each page differs from CARD-203's recording and is
        identical to CARD-222's.

        None of these three is machine-lettered (the fixture's own
        ``font_dependent_pages`` is 1, 2, 3, 4, 6, 8, 10 — a packed slot's
        band and caption, and the folio, are all set in the packaged
        DejaVu Sans), so this comparison needs no face gate and runs
        everywhere.
        """
        now = page_digests(exported)
        recorded = card203_baseline["pages"]
        assert set(card203_baseline["font_dependent_pages"]).isdisjoint(
            self.CARD203_CAPTION_PAGES
        ), "an answer page became machine-lettered; this comparison now needs a face gate"
        for number in self.CARD203_CAPTION_PAGES:
            assert now[number - 1 + self.LIVE_OFFSET] != recorded[number - 1], (
                f"interior page {number} still matches the CARD-203 "
                "recording, so CON-018's amended margins never reached this "
                "answer page — CARD-222's own change did not happen here"
            )
            assert now[number - 1 + self.LIVE_OFFSET] != (
                card222_baseline["pages"][number - 1]
            ), (
                f"stored page {number} is an answer page, and CARD-206 moved "
                "it with every other page: its folio reads one number higher "
                "and sits in the opposite bottom corner"
            )
            assert now[number - 1 + self.LIVE_OFFSET] == (
                card206_baseline["pages"][number - 1 + self.LIVE_OFFSET]
            ), (
                f"stored page {number} is an answer page: CARD-203 moved its "
                "caption, CARD-222 moved the text block it sits in, CARD-206 "
                "moved its page number and its folio's corner and nothing "
                "since has, so it must be byte-identical to the CARD-206 "
                "baseline"
            )

    def test_the_three_answer_pages_moved_under_card203_not_this_card(
        self, baseline, card203_baseline, exported
    ) -> None:
        """The attribution itself, asserted rather than written down (CARD-204
        Fix 7): these three pages *do* differ from the CARD-200 baseline, and
        the difference is already present in CARD-203's own recording — which
        is what makes "CARD-203 moved them" a measurement and not a claim. If
        a later card moves them again, the test above fails; if CARD-203's
        caption move were somehow reverted, this one does.
        """
        now = page_digests(exported)
        for number in self.CARD203_CAPTION_PAGES:
            card200_page = baseline["pages"][number - 1]
            card203_page = card203_baseline["pages"][number - 1]
            assert card203_page != card200_page, (
                f"interior page {number} is identical in the CARD-200 and "
                "CARD-203 recordings — CARD-203 is then not what moved it, and "
                "this class's own split is mis-attributed"
            )
            assert now[number - 1 + self.LIVE_OFFSET] != card200_page

    def test_the_floated_answer_page_moved_under_this_card_and_nothing_before_it(
        self, card222_baseline, card248_baseline, exported
    ) -> None:
        """CARD-224's own attribution for interior 13, measured over three
        fixtures (the discipline this class applies to every other page it
        names).

        Snowflake's full answer page is drawn through ``compute_layout`` on
        the book's own sheet, so the 42% float reaches it: its drawing — and
        the caption CARD-203 hangs a fixed gap below that drawing — sit lower
        on the page than they did. Three claims, in the order that makes the
        attribution a measurement:

        1. CARD-222's and CARD-248's recordings of this page **agree** —
           nothing between those two cards moved it, so the move is not
           something this card inherited;
        2. the page as exported **differs** from CARD-248's recording — the
           move really happened here;
        3. the other two answer pages (11, 12) are *not* in this group and
           are still asserted byte-identical above, which is what makes the
           difference a property of the full-page drawing rather than of
           answer pages in general.
        """
        now = page_digests(exported)
        for number in self.CARD224_FLOATED_PAGE:
            assert card222_baseline["pages"][number - 1] == (
                card248_baseline["pages"][number - 1]
            ), (
                f"interior page {number} already differed between CARD-222 "
                "and CARD-248, so CARD-224 is not what moved it and this "
                "class's own split is mis-attributed"
            )
            assert now[number - 1 + self.LIVE_OFFSET] != card248_baseline["pages"][number - 1], (
                f"interior page {number} is still CARD-248's own page: the "
                "42% float never reached the full answer page, and this "
                "card's own accounting of which pages move is wrong"
            )

    def test_the_guide_pages_are_the_documented_exception_not_an_unbounded_one(
        self, baseline, exported
    ) -> None:
        """The guide pages are not byte-identical to the CARD-200 baseline
        (see this class's own docstring) — expected and documented. What is
        pinned here is that they are still the *guide* pages: same size,
        same page count, and still carrying the guide's own identifiable
        marks (the title, the worked examples) rather than having silently
        become blank or some other page's content. A real regression that
        actually broke the guide page's drawing would fail one of these,
        not hide behind the documented pixel-level exception above.

        **CARD-221 widened the exception and removed its bound.** Until that
        card the two pages differed from the CARD-200 recording only by a
        sub-pixel rounding scatter, and
        ``test_the_guide_pages_scatter_is_bounded_to_one_pixel_of_displacement``
        measured exactly that: under 1% of the page, every differing pixel
        explained by ink that moved at most 1 px. Re-lettering both pages in
        the packaged face is not a scatter — measured on this branch, page 1
        differs in 7.596% of its pixels and page 2 in 10.531%, with 254,766
        and 478,630 pixels that are not ink-moved-by-one — so that test is
        gone and this one keeps the claims that survive. What replaces it is
        stronger than a bound and unconditional on any host font
        configuration: both pages are compared pixel for pixel against
        CARD-221's own recording by
        ``TestBookPdfMemory_PagesAreUnchanged``.

        The two stored pre-card page images stay where they are (G-5 of that
        card: no earlier fixture is deleted), and the integrity check the
        deleted test opened with is kept below — they are only trustworthy as
        the exact pixels behind ``book_baseline_card200.json``'s own digests,
        and nothing else reads them now.
        """
        fixtures_dir = Path(__file__).resolve().parent / "fixtures"
        now = page_digests(exported)
        recorded = baseline["pages"]
        for number in self.GUIDE_PAGES:
            with Image.open(
                fixtures_dir / f"book_baseline_card200_guide_page{number}.jpg"
            ) as raw:
                pre = raw.convert("RGB")
            assert page_digest(pre) == recorded[number - 1], (
                f"the stored pre-card guide page {number} is not the page "
                "book_baseline_card200.json recorded — this fixture is only "
                "trustworthy as the pixels behind that digest"
            )
            assert now[number - 1 + self.LIVE_OFFSET]["size"] == recorded[number - 1]["size"], (
                f"interior page {number} changed size, not just its face"
            )
            assert now[number - 1 + self.LIVE_OFFSET] != recorded[number - 1], (
                f"interior page {number} is expected to differ from the "
                "CARD-200 baseline (see this class's docstring) — if it "
                "now matches exactly, this exception is stale and the "
                "class docstring/comment should be revisited"
            )

    def test_every_drawing_page_actually_moved(self, baseline, exported) -> None:
        """The negative control: AC-7 claims an exception for these pages,
        not a blanket "nothing changed" that this test file would hide."""
        now = page_digests(exported)
        recorded = baseline["pages"]
        for number in self.DRAWING_PAGES:
            assert now[number - 1 + self.LIVE_OFFSET] != recorded[number - 1], (
                f"interior page {number} carries a drawing and should have "
                "moved under CARD-204 (right-alignment, and on 5/7/9 a new "
                "QR placeholder icon) — it is still the CARD-200 baseline's "
                "own page, so this card's own change did not reach it"
            )


# --------------------------------------------------------------------------
# CARD-201 AC-6 — every page after the guide, shifted by one, unchanged
# --------------------------------------------------------------------------


def _ink_bbox_crop(image: Image.Image) -> Image.Image:
    """``image`` cropped tight to its own ink's bounding box.

    Used to compare two pages of the same content at two different interior
    positions: a book page's margins are mirrored by parity (ADR-0036), so
    the same content drawn one page later (the opposite parity) sits at a
    different *absolute* pixel offset — cropping to each page's own ink
    bounding box first cancels that known, legitimate shift out, leaving
    only whether the content itself agrees.
    """
    mask = np.asarray(image.convert("L")) < INK_LEVEL
    rows = np.flatnonzero(mask.any(axis=1))
    cols = np.flatnonzero(mask.any(axis=0))
    return image.crop((int(cols[0]), int(rows[0]), int(cols[-1]) + 1, int(rows[-1]) + 1))


#: How many pixels an ink bounding box's own measured edge may differ by
#: between two parities before :func:`_matches_shifted_content` treats it as
#: a real size disagreement rather than the bbox measurement's own rounding.
_BBOX_SLACK_PX = 2


def _matches_shifted_content(a: Image.Image, b: Image.Image) -> bool:
    """Whether two ink-bbox-cropped pages carry the same content.

    **Not** ``tests.helpers.pdf_pages.same_page``: that helper's ink-overlap
    check downsamples by 6 before comparing (fast, and tuned for telling a
    mostly-white page from another one, or a colour encode from a grayscale
    one of the *same* drawing at the *same* position). A blank puzzle page's
    own ink is almost entirely thin rules — one or two pixels wide — so a
    1 px rounding difference between two parities (measured while building
    this card: ``_two_up_page``'s and ``solved_puzzle_page``'s rules sit at
    most 1 px off between a page and the same content redrawn at the
    opposite parity) falls on a *different* side of a downsampling block
    often enough to read as a large chunk of disagreement at 6x reduction,
    even though the full-resolution pixel agreement is in fact above 99%.

    So this compares at full resolution instead: the mean absolute grey
    difference (same statistic ``same_page`` itself uses, just not
    downsampled) and the share of pixels whose difference exceeds half the
    ink threshold — both measured, on this card's own genuinely-matching
    pages, at a small fraction of the thresholds below; a changed clue, a
    missing fill or a relabelled band moves either figure by an order of
    magnitude, which is what :meth:`TestBookPdfMemory_EveryPageAfterTheGuideIsByteIdenticalShiftedByOne.test_the_comparison_has_teeth`
    pins.

    The two crops' sizes can themselves differ by a pixel: the ink bounding
    box's own edge is one more rounded measurement, taken independently on
    each page, so the box a page's content fills can come out a pixel wider
    or taller at the opposite parity even though nothing inside it moved by
    more than that. Within :data:`_BBOX_SLACK_PX` this compares the
    top-left-aligned overlap of the two (the only region both can hold an
    opinion about); past it, the crops disagree about something bigger than
    rounding and the sizes are left to differ in the failure message.
    """
    if abs(a.width - b.width) > _BBOX_SLACK_PX or abs(a.height - b.height) > _BBOX_SLACK_PX:
        return False
    width, height = min(a.width, b.width), min(a.height, b.height)
    grey_a = np.asarray(a.crop((0, 0, width, height)).convert("L"), dtype=np.int16)
    grey_b = np.asarray(b.crop((0, 0, width, height)).convert("L"), dtype=np.int16)
    diff = np.abs(grey_a - grey_b)
    return float(diff.mean()) < 8.0 and float((diff > 50).mean()) < 0.03


class TestBookPdfMemory_EveryPageAfterTheGuideIsByteIdenticalShiftedByOne:
    """AC-6 (G-2) — every page from the first puzzle/divider page onward
    keeps the same content it had before CARD-201; only its page number
    shifts by one.

    **Why this is not a byte-for-byte digest comparison against a pre-card
    fixture, unlike :class:`TestBookPdfMemory_PagesAreUnchanged` above.**
    Inserting the guide's second page flips the parity (recto/verso) of
    every page after it — an unavoidable fact of pagination, not a
    regression — and COMP-007 mirrors a book page's margins by parity
    (ADR-0036/the "Mirrored margins" clarification): the gutter and outside
    margins swap sides, so the same content's absolute ink position shifts
    sideways by (gutter - outside) and a handful of ruled lines round to a
    different pixel at the new, opposite parity. A sha256 of the raw bitmap
    would differ for that reason alone on *every* page, which is not what
    G-2 claims ("the same content... only its page number shifts") and
    would fail this test on the one thing it is not about — verified
    empirically while building this card: ``_blank_page`` at interior page 2
    and at interior page 3 for the same payload differ by thousands of
    pixels (the margin shift alone), even though neither function was
    touched (G-2).

    So instead: for each page from the first puzzle/divider page onward,
    this builds a "reference" page by calling the SAME, unedited drawing
    function (``_blank_page`` / ``_two_up_page`` / ``create_divider_page`` /
    ``solved_puzzle_page`` — G-2 forbids editing any of them) at the page
    number this content held *before* CARD-201 (one less than its real,
    exported position), and compares it against the real exported page —
    each cropped to its own ink's bounding box (:func:`_ink_bbox_crop`, which
    cancels the legitimate parity-mirrored margin shift out) and compared
    with :func:`_matches_shifted_content` (a full-resolution mean-difference
    comparison, not ``same_page``'s downsampled ink-overlap one — see that
    function's own docstring for why a blank puzzle page's thin rules need
    the distinction) rather than an exact digest. A changed clue, a wrong
    fill, a missing frame or a relabelled band would all still fail this
    comparison; only the documented margin shift and its sub-pixel rounding
    are tolerated.

    **What this class deliberately does NOT pin: either slot's absolute
    position** (cycle-4 review F-11, the one surviving mutant M4 — dropping
    CARD-204 Fix 4's three ``folio_reserve_px=_folio_reserve_px(...)``
    arguments from the reference geometry leaves this class green). That is
    not a tolerance that could be tightened: :func:`_ink_bbox_crop` crops
    each side to its own ink, per slot, so it cancels **any pure translation
    of a slot by construction** — which is exactly what this class needs,
    since the flush edge mirrors with parity (above). A 108 px sideways shift
    of the lower slot's whole drawing is therefore invisible here, by design;
    passing the production reserve into the reference is correctness hygiene
    for the helper, not coverage. The absolute lower-slot position IS pinned,
    by three other modules: ``tests/property/test_book_two_up.py``
    (``test_PropertyTest_BookTwoUp_LowerSlotKeepsTheWholeFixedReserve``),
    ``tests/property/test_book_export_interior.py``
    (``_expected_drawing_left_mm``) and ``tests/test_book_puzzle_frame.py``
    (``_expected_pair_boxes``). Read this class as "the same content", never
    as "in the same place".
    """

    @pytest.fixture(scope="class")
    @classmethod
    def generator(cls) -> BookPDFGenerator:
        return BookPDFGenerator(corpus_book())

    @pytest.fixture(scope="class")
    @classmethod
    def plan(cls, generator):
        return generator.section_plan(baseline_puzzles())

    @pytest.fixture(scope="class")
    @classmethod
    def exported(cls, generator, plan):
        return pdf_pages(export_of(generator, baseline_puzzles()))

    def _reference(self, generator, plan, entry):
        """The unedited drawing function's own output at the page number this
        content held under **CARD-201's own layout** — ``entry.page_number``
        less CARD-200's table of contents and CARD-206's title page.

        CARD-200 (SCOPE+): ``entry.page_number`` carries CARD-200's own
        table-of-contents offset (``plan.toc_page_count`` pages, inserted
        between the guide and this section) on top of CARD-201's own "+1"
        this class's own name is about.

        **CARD-206 (SCOPE+) moves which historical position this is, and
        says why.** This class compares a **whole page**, footer included, so
        it only works between two positions of the *same parity*: a page's
        grid-size label sits against its inner margin and its QR group in the
        footer's outer corner (CARD-223), so an odd shift puts both of them on
        the other side of the page — a difference this comparison is not about
        and should not be asked to absorb. (A pixel figure for two crops "of
        different widths" stood here and is gone: review cycle 1's F-101 class
        sweep re-derived it and it reproduced in no domain. The measurement is
        in CARD-206's fix-round-1 notes, where a figure no assertion reads
        belongs.) Before this card the shift was ``1 + toc_page_count``
        = 2, even by luck. Subtracting CARD-206's own ``TITLE_PAGE_COUNT``
        as well as CARD-201's "-1" would make it 3 — odd — so what is
        subtracted here is ``toc_page_count + TITLE_PAGE_COUNT`` = 2 instead:
        the two one-page front-matter insertions, which lands on **CARD-201's
        own shipped layout** (a real position, not a constructed one) and
        keeps the parity. CARD-201's own "+1" is no longer subtracted, so
        this class's reference is one page later than its name says; the
        pre-CARD-206 position, at the odd shift, is what
        :class:`TestBookPdfMemory_ContentAboveTheFooterBandIsUnchanged`
        compares against, with the footer band cropped out so the mirrored
        marks cannot enter.
        """
        old_number = entry.page_number - plan.toc_page_count - TITLE_PAGE_COUNT
        if isinstance(entry, DividerPagePlan):
            return generator.create_divider_page(old_number, entry.text)
        payloads = [plan.payloads[number - 1] for number in entry.numbers]
        if entry.pair is None:
            (payload,) = payloads
            return generator._blank_page(payload, entry.numbers[0], old_number)
        old_pair = compute_pair_layout(
            (payloads[0].row_clues, payloads[0].column_clues),
            (payloads[1].row_clues, payloads[1].column_clues),
            generator.page_spec(old_number),
            # CARD-204 Fix 4: production's own `puzzle_pages` always passes
            # the fixed folio reserve, so this reference must too — a
            # reference built without it would sit `_folio_reserve_px`
            # pixels off production's own lower slot, and the comparison
            # below would be tolerating a real displacement instead of
            # checking the content.
            folio_reserve_px=_folio_reserve_px(generator.dpi),
            # CARD-248: and the footer strip, for the same reason — without
            # it the reference pair is fitted into 29.878 mm more height than
            # production gives it, so every mark on it sits at a different y
            # and at a different cell.
            footer_reserve_px=interior_frame(
                generator.page_spec(old_number)
            ).footer_depth,
        )
        old_entry = replace(entry, page_number=old_number, pair=old_pair)
        return generator._two_up_page(old_entry, payloads)

    def test_every_puzzle_or_divider_page_matches_its_pre_card_content(
        self, generator, plan, exported
    ):
        checked = 0
        for entry in plan.pages:
            new_page = exported[entry.page_number - 1]
            reference = self._reference(generator, plan, entry)
            # The number interpolated is the one `_reference` actually built
            # at, and the layout it names is the one that position belongs to
            # (review cycle 1, F-105): this message said "pre-CARD-201" and
            # `page_number - 1` while the reference has been two pages back,
            # on CARD-201's own shipped layout, since this card re-pointed it.
            old_number = entry.page_number - plan.toc_page_count - TITLE_PAGE_COUNT
            assert _matches_shifted_content(_ink_bbox_crop(new_page), _ink_bbox_crop(reference)), (
                f"interior page {entry.page_number} does not match the content "
                f"its position under CARD-201's shipped layout ({old_number}) "
                "held"
            )
            checked += 1
        assert checked == len(plan.pages) >= 5, checked

    def test_the_solutions_divider_matches_its_pre_card_content(self, generator, plan, exported):
        # first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT +
        # toc_page_count + len(section) + 1 (book_pdf_generator.interior_stream,
        # which since review cycle 1's F-102 computes it exactly once); this
        # divider is one page before it. CARD-200 (SCOPE+): `toc_page_count`
        # is that card's own new term, and CARD-206's TITLE_PAGE_COUNT is
        # this one's; both are subtracted again below to land the reference
        # on CARD-201's own shipped layout, the same even shift this class's
        # `_reference` uses and for the same parity reason.
        new_number = 1 + TITLE_PAGE_COUNT + 2 + plan.toc_page_count + len(plan.pages)
        reference = generator.create_divider_page(new_number - plan.toc_page_count - TITLE_PAGE_COUNT, "SOLUTIONS")
        assert _matches_shifted_content(
            _ink_bbox_crop(exported[new_number - 1]), _ink_bbox_crop(reference)
        )

    def test_every_answer_page_matches_its_pre_card_content(self, generator, plan, exported):
        """CARD-202 note: an answer page is packed-or-full, not always full.

        Before CARD-202, every answer printed on a full page of its own, so
        the pre-CARD-201 reference for each one was a direct
        ``solved_puzzle_page`` call. CARD-202 packs small, same-tier answers
        2-or-4 to a page instead, so the reference must be built through
        whichever drawing function the real export actually used for that
        page — this reruns the same production walk ``interior_stream``
        itself runs (``plan_small_answer_pages``, then the same feasibility
        degrade pass) to find out which kind each page is, rather than
        assuming a full page and comparing the wrong drawing to the right
        one.
        """
        # CARD-200 (SCOPE+): `plan.toc_page_count` is this card's own new
        # term in `first_answer_page`'s own arithmetic.
        first_answer_page = 1 + TITLE_PAGE_COUNT + 2 + plan.toc_page_count + len(plan.pages) + 1
        titles = generator.custom_titles()
        payloads = list(zip(plan.ids, plan.payloads))

        answers = []
        for index, (_, payload) in enumerate(payloads):
            number = index + 1
            width, height = _answer_extent(payload, number)
            answers.append(
                Answer(number=number, width=width, height=height, level=_pairable_tier(payload))
            )
        answer_plan = _degrade_infeasible_packed_pages(
            plan_small_answer_pages(answers), payloads, generator.page_spec(first_answer_page)
        )

        checked = 0
        for index, entry in enumerate(answer_plan):
            new_number = first_answer_page + index
            old_number = new_number - plan.toc_page_count - TITLE_PAGE_COUNT
            if isinstance(entry, PackedAnswerPage):
                reference = generator._packed_answer_page(entry, payloads, old_number, titles)
            else:
                puzzle_id, payload = payloads[entry.number - 1]
                title = answer_title(titles.get(str(puzzle_id)), payload.name)
                reference = generator.solved_puzzle_page(payload, entry.number, old_number, title=title)
            assert _matches_shifted_content(
                _ink_bbox_crop(exported[new_number - 1]), _ink_bbox_crop(reference)
            ), f"answer page {new_number} does not match its pre-CARD-201 content"
            checked += 1
        assert checked == len(answer_plan) == 3, checked

    def test_the_comparison_has_teeth(self, generator):
        """Control: a genuinely different puzzle fails this same comparison."""
        plan = generator.section_plan(baseline_puzzles())
        entry = next(e for e in plan.pages if isinstance(e, PuzzlePagePlan) and e.pair is None)
        payload = plan.payloads[entry.numbers[0] - 1]
        real = generator._blank_page(payload, entry.numbers[0], entry.page_number - 1)
        other_payload = next(
            plan.payloads[e.numbers[0] - 1]
            for e in plan.pages
            if isinstance(e, PuzzlePagePlan) and e.pair is None and e is not entry
        )
        other = generator._blank_page(other_payload, entry.numbers[0], entry.page_number - 1)
        assert not _matches_shifted_content(_ink_bbox_crop(real), _ink_bbox_crop(other))


# --------------------------------------------------------------------------
# CARD-200 AC-8 — content above the new footer band is unchanged
# --------------------------------------------------------------------------


def _footer_band_height(dpi: int) -> int:
    """One folio line's own height, in pixels, at ``dpi`` (CARD-200)."""
    font = _band_font(type_px(FOLIO_PT, dpi))
    ascent, descent = font.getmetrics()
    return ascent + descent


def _above_footer(image: Image.Image, cutoff: int) -> Image.Image:
    """``image``, with every row at or below ``cutoff`` dropped (CARD-200).

    ``cutoff`` is the first row of the page's footer band — since CARD-222
    the frame's own footer rule, where it was a folio line above the usable
    bottom before (:func:`_footer_band_height`; see the ``cutoff`` fixture for
    why it moved). It is the same for every interior page of one
    book, because a book page's top/bottom margins (unlike its left/right
    ones) never move with parity (verified against
    ``book_page_spec.book_page_spec``'s own body, not assumed: only
    ``left_margin_mm`` depends on parity, and ``page_frame``'s own ``top``/
    ``bottom`` come from ``top_mm``/``height_mm``/``bottom_mm`` alone). A
    caption's own slack sits inside this same dropped band on a solved or
    packed answer page — deliberately: AC-8 is about the mark *above* the
    footer band, and the caption's own pixels are unedited by this card and
    already covered by ``tests/test_book_solved_answer_key.py``.
    """
    return image.crop((0, 0, image.width, max(cutoff, 0)))


class TestBookPdfMemory_ContentAboveTheFooterBandIsUnchanged:
    """AC-8 (G-3) — every mark above the new footer band is unedited by this card.

    The same "compare by content, not by raw bytes" technique
    :class:`TestBookPdfMemory_EveryPageAfterTheGuideIsByteIdenticalShiftedByOne`
    already uses for CARD-201's own shift (a book page's margins mirror by
    parity, ADR-0036, so a raw digest differs for that reason alone even
    where nothing else moved) — extended here two ways: the reference is
    built at ``entry.page_number`` minus CARD-206's own ``TITLE_PAGE_COUNT``
    (this card's own one-page insertion; it was CARD-200's
    ``toc_page_count`` until CARD-206 — see :meth:`_reference`), and both the real page and
    the reference are cropped to :func:`_above_footer` *before* the
    ink-bbox crop, so neither side's own folio digits (which legitimately
    differ between the two page numbers being compared) can ever enter the
    comparison. What is left to disagree is exactly the claim G-3 makes:
    the grid, the clues, the band and the answer caption.

    A genuinely different puzzle still fails this comparison
    (``test_the_comparison_has_teeth``), the same control
    :class:`TestBookPdfMemory_EveryPageAfterTheGuideIsByteIdenticalShiftedByOne`
    already keeps for the un-cropped version.

    **What this class deliberately does NOT pin: either slot's absolute
    position** (cycle-4 review F-11, the one surviving mutant M4 — dropping
    CARD-204 Fix 4's three ``folio_reserve_px=_folio_reserve_px(...)``
    arguments from the reference geometry (here: :meth:`_reference` and
    :meth:`_qr_boxes`) leaves this class green). That is
    not a tolerance that could be tightened: :func:`_ink_bbox_crop` crops
    each side to its own ink, per slot, so it cancels **any pure translation
    of a slot by construction** — which is exactly what this class needs,
    since the flush edge mirrors with parity (see the class named above). A
    108 px sideways shift
    of the lower slot's whole drawing is therefore invisible here, by design;
    passing the production reserve into the reference is correctness hygiene
    for the helper, not coverage. The absolute lower-slot position IS pinned,
    by three other modules: ``tests/property/test_book_two_up.py``
    (``test_PropertyTest_BookTwoUp_LowerSlotKeepsTheWholeFixedReserve``),
    ``tests/property/test_book_export_interior.py``
    (``_expected_drawing_left_mm``) and ``tests/test_book_puzzle_frame.py``
    (``_expected_pair_boxes``). Read this class as "the same content", never
    as "in the same place".
    """

    @pytest.fixture(scope="class")
    @classmethod
    def generator(cls) -> BookPDFGenerator:
        return BookPDFGenerator(corpus_book())

    @pytest.fixture(scope="class")
    @classmethod
    def plan(cls, generator):
        return generator.section_plan(baseline_puzzles())

    @pytest.fixture(scope="class")
    @classmethod
    def exported(cls, generator, plan):
        return pdf_pages(export_of(generator, baseline_puzzles()))

    @pytest.fixture(scope="class")
    @classmethod
    def cutoff(cls, generator) -> int:
        """The first row of the page's footer, which this class drops.

        **CARD-222 widens it from one folio line to the frame's own footer
        band.** CARD-200's footer was one line — the folio alone — so a line's
        height was the whole band. The frame the owner's artifact asks for
        gives that band three rows (the hairline, the grid-size label beside
        the folio, and the QR icon's reserved row), and the label's side flips
        with parity: it is set against the *inner* margin, which is the left of
        a right-hand page and the right of a left-hand one. This class
        compares a page with its opposite-parity twin and allows only a
        translation between them, so a mark that changes sides is not
        something it can absorb — and it is not something it is about either
        (AC-8 is the marks *above* the footer). The band's own top is
        ``interior_frame``'s footer rule, so that is the cut.
        """
        spec = generator.page_spec(1)
        band = interior_frame(spec).footer_rule.y
        line = page_frame(spec).bottom - _footer_band_height(generator.dpi)
        assert band < line, (
            "the frame's footer band must be deeper than CARD-200's one folio "
            f"line, or this cut is the wrong one: {band} against {line}"
        )
        return band

    def _reference(self, generator, plan, entry):
        """CARD-201's own trick, pointed at **this** card's own insertion:
        the position this content held before CARD-206's title page existed
        (``entry.page_number - TITLE_PAGE_COUNT``).

        It was the pre-CARD-200 position (``- toc_page_count``) until
        CARD-206. The two classes split the work by parity, deliberately:
        ``TITLE_PAGE_COUNT`` is 1, so this shift is **odd** and the two pages
        compared are opposite parities — which is why this class crops the
        footer band away and masks the QR icon and the header rule, and why
        it is the one that can state CARD-206's own G-2 claim ("the geometry
        is untouched; only positions shift"). The even-shift, whole-page
        comparison against CARD-201's own layout is
        :class:`TestBookPdfMemory_EveryPageAfterTheGuideIsByteIdenticalShiftedByOne`'s.
        """
        old_number = entry.page_number - TITLE_PAGE_COUNT
        if isinstance(entry, DividerPagePlan):
            return generator.create_divider_page(old_number, entry.text)
        payloads = [plan.payloads[number - 1] for number in entry.numbers]
        if entry.pair is None:
            (payload,) = payloads
            return generator._blank_page(payload, entry.numbers[0], old_number)
        old_pair = compute_pair_layout(
            (payloads[0].row_clues, payloads[0].column_clues),
            (payloads[1].row_clues, payloads[1].column_clues),
            generator.page_spec(old_number),
            # CARD-204 Fix 4: production's own `puzzle_pages` always passes
            # the fixed folio reserve, so this reference must too — a
            # reference built without it would sit `_folio_reserve_px`
            # pixels off production's own lower slot, and the comparison
            # below would be tolerating a real displacement instead of
            # checking the content.
            folio_reserve_px=_folio_reserve_px(generator.dpi),
            # CARD-248: and the footer strip, for the same reason — without
            # it the reference pair is fitted into 29.878 mm more height than
            # production gives it, so every mark on it sits at a different y
            # and at a different cell.
            footer_reserve_px=interior_frame(
                generator.page_spec(old_number)
            ).footer_depth,
        )
        old_entry = replace(entry, page_number=old_number, pair=old_pair)
        return generator._two_up_page(old_entry, payloads)

    def _qr_boxes(self, generator, plan, entry, page_number):
        """CARD-204: this entry's placeholder QR icon box(es) at ``page_number``.

``TITLE_PAGE_COUNT`` (1) is odd, so this class's
        own comparison — unlike
        :class:`TestBookPdfMemory_EveryPageAfterTheGuideIsByteIdenticalShiftedByOne`'s
        even shift of ``toc_page_count + TITLE_PAGE_COUNT`` — compares two
        *opposite* parities. (It was ``toc_page_count``, also 1 and also odd,
        until CARD-206 re-pointed this class at its own insertion.) The icon mirrors sides with parity by design (it lives in
        the gutter-side slack, CARD-204), so it is the one mark on this page
        that is **not** a plain translation between the two sides being
        compared — masked out below before the content comparison, the same
        way a folio digit (which also differs legitimately) is already kept
        out by cropping above the footer band first.
        """
        if isinstance(entry, DividerPagePlan):
            return []
        payloads = [plan.payloads[number - 1] for number in entry.numbers]
        spec = generator.page_spec(page_number)
        if entry.pair is None:
            (payload,) = payloads
            layout = compute_layout(payload.row_clues, payload.column_clues, spec)
            icon = qr_slot(layout)
            return [icon] if icon is not None else []
        pair = compute_pair_layout(
            (payloads[0].row_clues, payloads[0].column_clues),
            (payloads[1].row_clues, payloads[1].column_clues),
            spec,
            # The same fixed reserve production pairs with (CARD-204
            # Fix 4) — the lower slot's icon box moves with its drawing.
            folio_reserve_px=_folio_reserve_px(generator.dpi),
            # And CARD-248's footer strip, which is where both of a two-up
            # page's icons now are.
            footer_reserve_px=interior_frame(spec).footer_depth,
        )
        assert pair is not None
        return _two_up_icon_boxes(pair, entry.numbers, generator.dpi)

    def _frame_boxes(self, generator, page_number):
        """CARD-222: the frame's header rule, as a box to mask.

        The rule runs the page's whole text width, so it pins the ink bounding
        box ``_ink_bbox_crop`` normalises by to the usable area's own edges on
        **both** sides. The drawing underneath is flush with the outer margin
        and mirrors with parity, and its own half-rule overhang rounds to a
        different pixel on the two sides — measured: a 1 px difference in the
        crop's width, which is not a translation and so not something this
        comparison can absorb. Masked for the same reason the QR icon above
        is, and like it the rule has its own, direct evidence elsewhere
        (``tests/test_book_page_frame.py``'s AC-2: one y, one weight, on every
        puzzle page).

        The footer's own marks need no mask: the ``cutoff`` fixture drops the
        whole footer band before this comparison sees it.
        """
        rule = interior_frame(generator.page_spec(page_number)).header_rule
        return [
            SimpleNamespace(
                left=rule.left,
                top=rule.y - rule.width,
                right=rule.right,
                bottom=rule.y + rule.width,
            )
        ]

    @staticmethod
    def _masked(image: Image.Image, boxes) -> Image.Image:
        if not boxes:
            return image
        masked = image.copy()
        draw = ImageDraw.Draw(masked)
        for box in boxes:
            draw.rectangle(
                (box.left - 2, box.top - 2, box.right + 2, box.bottom + 2),
                fill=(255, 255, 255),
            )
        return masked

    def test_every_puzzle_or_divider_page_matches_above_the_footer(
        self, generator, plan, exported, cutoff
    ):
        """A two-up pair is compared slot by slot, not as one page.

        ``_ink_bbox_crop`` normalises a *whole* image to its own single ink
        bounding box, which is exactly the right cancellation for a page
        whose content is one rigid block that merely slides sideways with
        parity. That is true only when both slots share the same drawing
        width: each slot's own flush formula anchors at the usable area's
        outer edge on an ODD page (so *both* slots' ``drawing_right``
        always equals ``usable_right``, independent of either one's own
        width) but at the gutter-side edge on an EVEN page (so both
        ``drawing_left`` always equal ``usable_left``) — a slot narrower
        than its partner therefore sits at a *different* offset from the
        page's own ink-bbox-crop origin depending on which edge is flush,
        which flips between the two opposite parities this comparison
        checks. Splitting at the pair's own (parity-independent)
        upper/lower midline first, and cropping+comparing each slot's own
        ink bbox separately, cancels exactly that per-slot translation,
        regardless of whether the two puzzles share a width.

        **History (CARD-204 Fix 1, reverted by Fix 3).** Fix 1 introduced
        this split because it also pulled the *lower* slot back from the
        flush edge by a folio reserve that the upper slot never got,
        adding a second, reserve-driven source of the same kind of
        per-slot asymmetry on top of the width-driven one above. Fix 3
        removed that reserve entirely, but the split is kept: the
        width-driven asymmetry it also cancels is a structural property of
        mirrored-margin flush alignment (FR-030), not something Fix 1
        introduced or Fix 3 touches.
        """
        checked = 0
        for entry in plan.pages:
            old_number = entry.page_number - TITLE_PAGE_COUNT
            new_page = self._masked(
                exported[entry.page_number - 1],
                self._qr_boxes(generator, plan, entry, entry.page_number)
                + self._frame_boxes(generator, entry.page_number),
            )
            reference = self._masked(
                self._reference(generator, plan, entry),
                self._qr_boxes(generator, plan, entry, old_number)
                + self._frame_boxes(generator, old_number),
            )
            new_above = _above_footer(new_page, cutoff)
            reference_above = _above_footer(reference, cutoff)
            pair = getattr(entry, "pair", None)
            if pair is None:
                slots = ((new_above, reference_above),)
            else:
                # The midline is the pair's own usable_top/usable_bottom
                # boundary between the two slots — fixed by the book's top
                # and bottom margins alone (never mirrored by parity, see
                # _above_footer's own docstring), so it is the same split
                # point for the real page and the opposite-parity reference.
                midline = pair.upper.page.usable_bottom
                slots = (
                    (new_above.crop((0, 0, new_above.width, midline)),
                     reference_above.crop((0, 0, reference_above.width, midline))),
                    (new_above.crop((0, midline, new_above.width, new_above.height)),
                     reference_above.crop((0, midline, reference_above.width, reference_above.height))),
                )
            for slot_new, slot_reference in slots:
                assert _matches_shifted_content(
                    _ink_bbox_crop(slot_new), _ink_bbox_crop(slot_reference)
                ), (
                    f"interior page {entry.page_number}'s content above the "
                    "footer band does not match its pre-CARD-200 content"
                )
            checked += 1
        assert checked == len(plan.pages) >= 5, checked

    def test_the_guide_pages_match_above_the_footer(self, generator, exported, cutoff):
        """The guide's own two pages carry no TOC-driven shift at all
        (they are always interior pages 1-2) — this is a direct check that
        the folio alone is the only new mark on them (AC-1/G-3), not a
        shifted-content comparison.
        """
        for number in GUIDE_INTERIOR_PAGES:
            reference = generator.create_guide_page(4, 2, 1, 1, page_number=number)
            assert _matches_shifted_content(
                _ink_bbox_crop(_above_footer(exported[number - 1], cutoff)),
                _ink_bbox_crop(_above_footer(reference, cutoff)),
            ), f"interior page {number} (the guide) moved above its own footer band"

    def test_the_solutions_divider_matches_above_the_footer(
        self, generator, plan, exported, cutoff
    ):
        new_number = 1 + TITLE_PAGE_COUNT + 2 + plan.toc_page_count + len(plan.pages)
        old_number = new_number - TITLE_PAGE_COUNT
        reference = generator.create_divider_page(old_number, "SOLUTIONS")
        assert _matches_shifted_content(
            _ink_bbox_crop(_above_footer(exported[new_number - 1], cutoff)),
            _ink_bbox_crop(_above_footer(reference, cutoff)),
        )

    def test_every_answer_page_matches_above_the_footer(
        self, generator, plan, exported, cutoff
    ):
        first_answer_page = 1 + TITLE_PAGE_COUNT + 2 + plan.toc_page_count + len(plan.pages) + 1
        titles = generator.custom_titles()
        payloads = list(zip(plan.ids, plan.payloads))

        answers = []
        for index, (_, payload) in enumerate(payloads):
            number = index + 1
            width, height = _answer_extent(payload, number)
            answers.append(
                Answer(number=number, width=width, height=height, level=_pairable_tier(payload))
            )
        answer_plan = _degrade_infeasible_packed_pages(
            plan_small_answer_pages(answers), payloads, generator.page_spec(first_answer_page)
        )

        checked = 0
        for index, entry in enumerate(answer_plan):
            new_number = first_answer_page + index
            old_number = new_number - TITLE_PAGE_COUNT
            if isinstance(entry, PackedAnswerPage):
                reference = generator._packed_answer_page(entry, payloads, old_number, titles)
            else:
                puzzle_id, payload = payloads[entry.number - 1]
                title = answer_title(titles.get(str(puzzle_id)), payload.name)
                reference = generator.solved_puzzle_page(payload, entry.number, old_number, title=title)
            assert _matches_shifted_content(
                _ink_bbox_crop(_above_footer(exported[new_number - 1], cutoff)),
                _ink_bbox_crop(_above_footer(reference, cutoff)),
            ), f"answer page {new_number}'s content above the footer band does not match"
            checked += 1
        assert checked == len(answer_plan) == 3, checked

    def test_the_comparison_has_teeth(self, generator, cutoff):
        """Control: a genuinely different puzzle still fails this comparison."""
        plan = generator.section_plan(baseline_puzzles())
        entry = next(e for e in plan.pages if isinstance(e, PuzzlePagePlan) and e.pair is None)
        payload = plan.payloads[entry.numbers[0] - 1]
        real = generator._blank_page(payload, entry.numbers[0], entry.page_number)
        other_payload = next(
            plan.payloads[e.numbers[0] - 1]
            for e in plan.pages
            if isinstance(e, PuzzlePagePlan) and e.pair is None and e is not entry
        )
        other = generator._blank_page(other_payload, entry.numbers[0], entry.page_number)
        assert not _matches_shifted_content(
            _ink_bbox_crop(_above_footer(real, cutoff)),
            _ink_bbox_crop(_above_footer(other, cutoff)),
        )

    def test_the_crop_actually_removes_a_folio(self, generator, exported, cutoff):
        """Control: the crop is not a no-op — a folio really sits below it."""
        full = np.asarray(exported[-1].convert("L")) < INK_LEVEL
        cropped = np.asarray(_above_footer(exported[-1], cutoff).convert("L")) < INK_LEVEL
        assert full.sum() > cropped.sum(), (
            "cropping above the footer band removed no ink — the last "
            "answer page's own folio was not where this test expected it"
        )


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
        finally:
            held.clear()

    def test_the_interior_and_the_cover_are_two_files(self, export):
        interior, cover = export.interior.getvalue(), export.cover.getvalue()

        assert interior != cover
        assert pdf_page_count(interior) == BASELINE_PAGE_COUNT
        assert pdf_page_count(cover) == 1

    def test_the_interior_starts_at_the_title_page_and_holds_no_cover(self, export):
        """CARD-206: interior page 1 is the blank title page and the guide's
        own first page follows it (:data:`GUIDE_INTERIOR_PAGES`)."""
        interior = pdf_pages(export.interior.getvalue())
        (cover,) = pdf_pages(export.cover.getvalue())
        guide = BookPDFGenerator(corpus_book()).create_guide_page(4, 2, 1, 1)

        assert np.asarray(interior[0].convert("L")).min() == 255, (
            "interior page 1 is the blank title page — no ink of any kind"
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
        """The guide's page 1 is right-hand, and the two single-puzzle pages are not.

        Parity counts from interior page 1 — the guide's own first page,
        which is right-hand — and the cover file is never numbered (FR-043,
        INV-013, G-2). On Book 1 the binding-side gutter is 0.5 in and, since
        CON-018's amendment of 2026-10-17 (CARD-222), the outside margin is
        **0.5 in too** — so a page's usable area starts 150 px from the left
        whichever hand it is, where a left-hand page's used to start at
        112.5 px. The *width* of the two margins no longer tells the two
        parities apart (CON-018's own note on this); which side each mark
        sits on still does, and that is what the gaps below read.

        **CARD-224 (SCOPE+): the drawing cannot carry this signal at all any
        more, and the footer can.** CARD-204 read parity off the drawing's own
        flush edge (a right-hand page's grid ended exactly 150 px in from the
        trim's right edge, whatever the puzzle's width). This card centres the
        drawing again, and on CON-018 as amended the two side margins are
        equal — so a centred drawing lands on the *same* pixel column at
        either parity and its edges say nothing about which hand the page is.
        What still mirrors is the page furniture: CARD-223 puts the 2 cm QR
        placeholder in the footer's **outer** bottom corner (right on a
        right-hand page, left on a left-hand one) and CARD-222 puts the
        grid-size label on the **inner** side. The icon is a near-solid 2 cm
        block, by far the heaviest ink in the footer strip, so the parity is
        read as "which end of the footer strip holds that block" — ink, as
        before, and a quantity that is still a function of the page's own
        hand.

        **CARD-201 note (SCOPE+): this moved.** The baseline book's two
        single-puzzle pages are interior 6 and interior 8 now (up from 5 and
        7 before this card — the guide's own second page shifts everything
        after it by one), both **even**, so both must sit *left* of the
        middle — the opposite of their pre-CARD-201 parity. That is still
        the measurement that would break if the cover ever rejoined the
        interior's numbering: every interior page's parity would flip again,
        and these two would land 18.75 px to the *right* instead.

        **CARD-200 note (SCOPE+): this moved again.** The baseline book's
        1-page table of contents (its 4 entries fit Book 1's own trim's TOC
        capacity comfortably) sits between the guide and the puzzle section,
        so the two single-puzzle pages are interior 7 and interior 9 now
        (up from 6 and 8) — still both **odd** positions shifted from even
        ones by the TOC's own one-page insertion, so the parity each must
        show is now the *opposite* of CARD-201's own note: both now sit
        *right* of the middle, back to their original, pre-CARD-201 side.

        **CARD-206 note (SCOPE+): this moved a third time, the same way.**
        The blank title / copyright page is reserved as interior page 1, so
        the two single-puzzle pages are interior **8 and 10** now, both
        **even**, and their footer icon is back at the *left* end of the
        strip. Interior page 1 itself no longer carries the guide: it carries
        no ink at all, so the guide's own leftmost-ink reading below moves to
        the guide's first page, interior 2 — a **left-hand** page, whose
        usable area starts at the outside margin. On CON-018 as amended both
        side margins are 0.5 in, so the 150 px figure that reading asserts is
        unchanged; which margin it is has flipped, and the bound is the same.

        Measured off the ink alone: the drawing's own edges — its clue
        gutter's outer edge and its grid's right border — never
        ``book_page_spec`` or ``compute_layout``.
        """
        interior = pdf_pages(export.interior.getvalue())

        #: The 2 cm QR placeholder's own box (CARD-223) and the usable area's
        #: two edges, in this page's own pixels, written out rather than
        #: imported: 0.5 in margins and a 20 mm icon at 300 DPI.
        icon_px = round(20.0 / 25.4 * 300)
        usable_left, usable_right = 150, 2550 - 150
        for number in (8, 10):
            page = interior[number - 1]
            ink = np.asarray(page.convert("L")) < 128
            strip = ink[-icon_px:]
            at_the_left = strip[:, usable_left : usable_left + icon_px].sum()
            at_the_right = strip[:, usable_right - icon_px : usable_right].sum()
            # A left-hand (even) page's icon is at the left-hand end
            # (CARD-206: these two pages are even now).
            assert at_the_left > 4 * at_the_right, (
                f"interior page {number} is a left-hand page, so the "
                f"footer's 2 cm icon belongs at its left-hand end; the "
                f"strip holds {at_the_left} dark pixels there against "
                f"{at_the_right} at the right"
            )
            # And the drawing itself is centred, which is why it can no
            # longer be asked: both of its side gaps are the same.
            drawing = drawing_of(page)
            left_gap = drawing.left - usable_left
            right_gap = usable_right - drawing.grid_right
            assert abs(left_gap - right_gap) <= 4, (number, left_gap, right_gap)

        # And page 1 itself: the guide page's text starts at the gutter
        # margin, 150 px in, not at the 112.5 px outside margin a left-hand
        # page would give it.
        #
        # **CARD-201 note (SCOPE+): the lower bound widened.** Page 1's own
        # leftmost ink is now a diagram's frame (the basic-rule line or a
        # cell-state icon), not a letter — every framed drawing on this book
        # bleeds up to half a heavy rule past its own nominal edge by design
        # (``_stroke_drawing``'s own docstring; this suite's other guide-page
        # tests tolerate the same bleed as ``FRAME_BLEED_PX`` in
        # ``tests/test_book_guide_page_type.py``), which a letter's ink never
        # did. Measured at this book's own rule widths: 6 px short of 150,
        # comfortably inside a 10 px allowance.
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

        ``solved_puzzle_page`` (CARD-197) drew every answer page until
        CARD-202: it still draws a large (unpacked) answer's full page, but
        the baseline book's first answer page is now a packed one
        (``_packed_answer_page``, CARD-202), so both are forced to fail here
        — whichever one the walk reaches first still fails cleanly, and the
        baseline book's own packing shape (``tests/helpers/book_corpus.py``)
        still puts that first failure at the same twelfth page either way
        (CARD-200: up from the tenth — the table of contents' own one page,
        ahead of the puzzle section, shifts every later page by one;
        CARD-206: up from the eleventh, the blank title page's own one page,
        ahead of all of it).
        """
        written: List[int] = []
        write_page = BookPDFGenerator._write_page
        solved_puzzle_page = BookPDFGenerator.solved_puzzle_page
        packed_answer_page = BookPDFGenerator._packed_answer_page

        def counting(self, *args, **kwargs):
            written.append(1)
            return write_page(self, *args, **kwargs)

        def refuses(self, *args, **kwargs):
            raise ValueError("this answer will not draw")

        BookPDFGenerator._write_page = counting
        BookPDFGenerator.solved_puzzle_page = refuses
        BookPDFGenerator._packed_answer_page = refuses
        try:
            with pytest.raises(RuntimeError) as raised:
                export_of(BookPDFGenerator(corpus_book()), baseline_puzzles())
        finally:
            BookPDFGenerator._write_page = write_page
            BookPDFGenerator.solved_puzzle_page = solved_puzzle_page
            BookPDFGenerator._packed_answer_page = packed_answer_page

        assert "could not be drawn" in str(raised.value)
        # The blank title page (CARD-206), the 2-page guide (CARD-201), the
        # 1-page table of contents
        # (CARD-200), three level dividers, the two-up page, two
        # single-puzzle pages and the SOLUTIONS divider: eleven pages of a
        # planned fourteen were bytes in the buffer already (CARD-202: the
        # baseline book's answer section is now 3 packed-or-full pages, not
        # CARD-198's 4, but the first one — where this failure lands — is
        # still the twelfth page either way).
        assert written == [1] * 11, written

    def test_a_producer_that_yields_too_few_pages_never_reaches_the_trailer(self):
        """A short stream would leave the page tree pointing at nothing."""
        generator = BookPDFGenerator(corpus_book())
        blank = Image.new("RGB", (60, 80), "white")

        def two_of_three() -> Iterator[Image.Image]:
            yield blank
            yield blank

        with pytest.raises(RuntimeError) as raised:
            generator._write_pdf(two_of_three(), 3, mode="RGB")

        assert "interior has 2 pages, its page plan says 3" in str(raised.value)

    def test_a_producer_that_yields_too_many_is_refused_before_the_extra_page(self):
        """The surplus page has no object id, so it is refused, not written."""
        generator = BookPDFGenerator(corpus_book())
        blank = Image.new("RGB", (60, 80), "white")
        offered = []

        def four_of_three() -> Iterator[Image.Image]:
            for _ in range(4):
                offered.append(1)
                yield blank

        with pytest.raises(RuntimeError) as raised:
            generator._write_pdf(four_of_three(), 3, mode="RGB")

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
