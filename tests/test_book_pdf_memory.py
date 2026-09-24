"""CARD-145 — the book PDF is written a page at a time (FR-041, FR-043, INV-013).

    AC (new)  TestBookPdfMemory_PeakDoesNotGrowWithPageCount
    AC (new)  TestBookPdfMemory_RealBookExportsUnderTheCap
    AC (new)  TestBookPdfMemory_PagesAreUnchanged
    AC (new)  TestBookPdfMemory_InteriorAndCoverStillSeparate

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
  since FR-042 — and binds ``blank, _ = render_pages(...)``, so the discarded
  page is alive until that frame returns. ``render_pages`` is a COMP-007
  function, not a generator method, so it is outside :data:`PAGE_FACTORIES` by
  construction and the probe never sees it. Registering **both** pages it
  returns and running the real export measures **10 pages and a peak of
  50,490,000 B — 2.00 page bitmaps — on the 11-page baseline book**, and **332
  pages and the same 50,490,000 B on the 182-page corpus book**. It is a
  constant, not a per-page term: every puzzle page pays it, none of them
  accumulates it, and it is the merge-base's code untouched (G-1).
* **The written PDF.** It accumulates in the returned ``BytesIO`` at a
  measured ~0.45 MB per page, so a 182-page interior holds 82,015,934 B of
  compressed output at the end. That *is* a linear term, and
  :meth:`TestBookPdfMemory_RealBookExportsUnderTheCap.test_the_residual_linear_term_is_the_written_file_and_it_is_small`
  measures and states it rather than letting the module read as a claim of
  constant memory.

So the process's page-size envelope for a 182-page book is **50.5 MB of
bitmap + 81.9 MB of file = 132.3 MB**, about a quarter of the 512 MB
instance — 26 % on the same decimal-MB reading that made the old figure
21 % — and not the 107.1 MB a "one page bitmap" reading of the assertions
gives.
Measured end to end, a child process exporting that book peaks at
**150.8-169.9 MB** resident over five runs, interpreter and imports included.
Peak is **O(one retained page) + O(a transient constant) + O(the file)**.

Cost: the corpus book is exported **once** for the whole module (a
module-scoped fixture), for about 7 seconds of real rendering and writing;
AC-2's executed cap adds three child processes, about 6 seconds, and the
whole file runs in well under a minute. The 150-puzzle book is never faked —
a page count is the one thing a memory test must not fake.
"""

from __future__ import annotations

import inspect
import json
import os
import subprocess
import sys
import time
import tracemalloc
import warnings
import weakref
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

import numpy as np
import pytest
from PIL import Image

from nonogram.admin.book_pdf_generator import BookPDFGenerator
from tests.helpers.book_corpus import (
    BASELINE_PAGE_COUNT,
    BASELINE_SHAPE,
    CORPUS_PAGE_COUNT,
    CORPUS_PUZZLE_COUNT,
    MATERIALISED_SHAPE,
    STREAMING_SHAPE,
    baseline_puzzles,
    corpus_book,
    corpus_puzzles,
    export_of,
    font_fingerprint,
    load_baseline,
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
#: Measured stable at 1.00 on the 11-page book, on the 182-page book and on
#: ``export_book``'s two files, with and without the cycle detector.
#:
#: **"Retains" is the exact word, and it is narrower than "the process holds
#: one page bitmap at a time".** What this pins is that no page survives the
#: call that builds the next one — a property of the panel's own frames, and
#: the one that turned 4.52 GB into a constant. Inside a single puzzle-page
#: build the process does hold a second full-size bitmap: COMP-007's
#: ``render_pages`` returns a blank page and a solved page, and ``_blank_page``
#: keeps the discarded one until its frame exits. Registering both of them
#: measures a peak of **50,490,000 B = 2.00 page bitmaps** — on the 11-page
#: book (13 pages registered) and unchanged on the 182-page one (332
#: registered), which is what makes it a constant rather than a term that
#: grows with the book. So the honest *process* figure is two bitmaps; the
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
    "create_guide_page",
    "create_divider_page",
    "_blank_page",
    "_two_up_page",
    "_answer_page",
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

    def patched(self, pages, page_count):
        return original(self, probe.watch(pages), page_count)

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
    the interior is 1 guide + 150 puzzle pages + 1 divider + 27 answer pages =
    182 pages of 25.2 MB bitmap each. Roughly seven seconds; shared, because
    two tests need it and neither needs its own copy.
    """
    return _measured(
        lambda: export_of(BookPDFGenerator(corpus_book()), corpus_puzzles())
    )


@pytest.fixture(scope="module")
def small_export() -> MeasuredExport:
    """The eleven-page baseline book, exported the same way, for comparison."""
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
    """A 182-page book's peak page-bitmap memory is a small book's peak.

    "Within a small constant" is stated in **page bitmaps**, not megabytes,
    because a page bitmap is the unit the defect was measured in: the old
    shape's peak was one page bitmap per page, and what this asserts is that
    the difference between a 182-page book and an 11-page one is under one.

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
        assert big.seen > 15 * small.seen, "the two books must differ in size"
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
        shape's whole cost — all eight pages of the baseline book at once,
        **202 MB** of live bitmap. That is the point of it, and it is also why
        it is run on the eleven-page book and never on the 182-page one, whose
        list would be 4.5 GB.
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
#: is the wrong number for this cap: the streaming child needs ~160 MB, and
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
#: interpreter + imports, nothing drawn   62.1 MB           2.46
#: + the corpus book and one page          96.1 MB           3.81  (the floor)
#: the streaming child's peak RSS         150.8-169.9 MB    5.97-6.73
#: **the cap**                            **807.8 MB**      **32**
#: the list shape: 182 bitmaps + file     ~4.68 GB          ~182
#: ===================================== ================= ==================
#:
#: So the cap sits **4.7x above** the largest streaming measurement and
#: **5.7x below** what the list shape needs — close to the geometric middle of
#: the two (which is 34.7 page bitmaps). Neither half is marginal, and neither
#: verdict can turn on an interpreter's footprint: the platform's own floor is
#: 3.81 page bitmaps, 11.9 % of the cap. Both margins are re-measured on every
#: run and asserted (:data:`CHILD_HEADROOM`, :data:`CHILD_FLOOR_SHARE`) rather
#: than trusted from this table.
CHILD_CAP_IN_PAGES = 32
CHILD_CAP_BYTES = CHILD_CAP_IN_PAGES * PAGE_BITMAP_BYTES

#: How much of the cap the streaming child must leave unused, as a divisor: its
#: measured peak times this must still fit. Measured 4.7x on this machine, so a
#: required 3x has room in it and still fails long before the shape does.
CHILD_HEADROOM = 3

#: The share of the cap the platform's own floor — interpreter, imports, one
#: page — may take before the cap stops being able to tell a *shape* apart from
#: a *footprint*. Over this, the test skips rather than reports either verdict.
#: Measured 11.9 % here.
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
#: separating 160 MB from 4.6 GB.
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


def _the_pair_under_one_cap(mechanism: str) -> Tuple[CappedChild, CappedChild]:
    """The streaming child and the list child, under the same cap, in order."""
    _habitable(mechanism)
    return (
        _capped_child(STREAMING_SHAPE, mechanism),
        _capped_child(MATERIALISED_SHAPE, mechanism),
    )


def _assert_the_streaming_child_fitted(child: CappedChild) -> None:
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
    resident = child.report["resident"]
    assert resident * CHILD_HEADROOM < CHILD_CAP_BYTES, (
        f"the streaming child peaked at {resident / 1e6:.1f} MB against a "
        f"{CHILD_CAP_BYTES / 1e6:.0f} MB cap — under {CHILD_HEADROOM}x of "
        "headroom, so this test's verdict has started to depend on the "
        "interpreter's footprint rather than on the export's shape"
    )


# --------------------------------------------------------------------------
# AC-2 — a real 150-puzzle book exports under the cap
# --------------------------------------------------------------------------


class TestBookPdfMemory_RealBookExportsUnderTheCap:
    """A 150-puzzle book exports to a valid 182-page PDF inside the envelope.

    The card asks for "a 150-page book exports successfully **under a memory
    cap that the current code fails**". Both halves are covered here, and the
    class is explicit about which of them is *executed* and which is
    *arithmetic*, because they are not the same kind of evidence.

    **Executed** — one cap, two fresh interpreters, two outcomes
    (``test_one_cap_the_streaming_shape_survives_and_the_list_shape_dies_under``
    and its ``RLIMIT_AS`` twin). A child installs a memory cap of 32 page
    bitmaps *before it imports anything*, then exports this very book: the
    streaming shape finishes and reports the 182 pages read back out of the
    file it wrote, and the list shape — ``interior_pages``, the shape this card
    removed from the export path — is killed by the cap partway through. That
    is "a cap the current code fails" as a process that dies, not as a
    multiplication. The earlier objection to ``setrlimit`` was right about an
    *in-process* cap and wrong about a subprocess one: a child that dies takes
    nothing with it.

    **Arithmetic, and kept** — ``test_the_old_shape_would_not_have_fitted_the_envelope``
    derives the list shape's peak for this same book from the instrument's own
    measured per-page constant (182 x 25,245,000 = 4.59 GB) against the 512 MB
    envelope. It is the only evidence that reaches the *deployed* number rather
    than a test cap, it costs nothing, and it runs on every platform — including
    the ones where the executed half can only skip.

    What is measured in this process, alongside:

    1. A 150-puzzle book is exported end to end, and the file that comes out
       is a valid PDF whose page tree holds the 182 pages the plan declared.
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
        """The 182-page book retains one page bitmap, exactly, end to end.

        "Retains" rather than "holds": this is the peak over the pages the
        panel itself keeps, which is what stopped growing with the page count.
        COMP-007's ``render_pages`` holds a second full-size bitmap transiently
        inside each puzzle-page build — a measured constant of 50,490,000 B for
        this book as for the 11-page one — and :data:`PEAK_IN_PAGES` records it.
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
        streaming child finishes and reports 182 pages *read back out of the
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
        child measures 5.97-6.73 of them and the list shape needs ~182. Both
        margins are re-measured on every run, not trusted: the streaming
        child's headroom is asserted (:data:`CHILD_HEADROOM`), the platform's
        own floor is measured first and skips the test if it has grown into
        the cap (:func:`_habitable`), and the list child is required to die
        *by the cap* — the sentry's exit status and its marker on stderr —
        rather than merely to fail.
        """
        streaming, materialised = _the_pair_under_one_cap(SENTRY_MECHANISM)

        _assert_the_streaming_child_fitted(streaming)

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

        streaming, materialised = _the_pair_under_one_cap(RLIMIT_MECHANISM)

        _assert_the_streaming_child_fitted(streaming)

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
        for a progress mechanism. A 182-page book exports in single-digit
        seconds on this machine, which is why item 4 was deferred rather than
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
# AC-3 — every page is pixel-identical to the same page before this card
# --------------------------------------------------------------------------


class TestBookPdfMemory_PagesAreUnchanged:
    """Every exported page is the page the baseline recorded, to the pixel (G-1).

    The evidence is ``tests/fixtures/book_baseline_card128.json``, recorded by
    exporting
    ``tests/helpers/book_corpus.baseline_puzzles`` with the untouched code,
    reading the pages back **out of the PDF** with the shared
    ``pdf_pages`` helper, and digesting each one's raw bitmap. It covers the
    whole path: draw, JPEG-encode, write, parse, decode.

    The comparison is exact — a sha256 of ``Image.tobytes()`` — and
    deliberately not ``pdf_pages.same_page``, which tolerates JPEG noise and a
    6-level mean difference and would hide precisely the kind of change this
    exists to catch.

    That fixture is never to be regenerated to make this test pass; it says so
    in its own ``warning`` field. It has a predecessor beside it,
    ``book_baseline_card145.json``, recorded from commit ``b4c523d`` — the
    merge-base, before a line of CARD-145's production change existed — which
    is left unregenerated and which this one supersedes for the one reason
    that warning admits: CARD-128 deliberately changed what the interior holds
    (grouped by level, a divider page opening each), so no page of that
    recording is where it was. Both files say so.

    **The machine's own face costs five pages of evidence, not eleven.** Only
    interior page 1 (the guide) and the four divider pages — 2, 4 and 6 for
    the levels (CARD-128) and 8 for SOLUTIONS — are lettered in
    ``ImageFont.truetype("…/Arial.ttf")`` with a ``load_default`` fallback; the
    other six are drawn in the bundled band face and Pillow's built-in clue
    face and are comparable on any machine. So a fingerprint mismatch skips
    **those five pages** and compares the rest, rather than taking the whole
    book's pixel evidence down with it — which on the project's own Linux
    deployment image, where Arial is not at that path, is the difference
    between six pages of G-1 evidence and none.
    """

    @pytest.fixture(scope="class")
    @classmethod
    def baseline(cls) -> Dict[str, Any]:
        return load_baseline()

    @pytest.fixture(scope="class")
    @classmethod
    def same_face(cls, baseline) -> bool:
        """Whether this machine letters the guide and the divider as recorded."""
        return font_fingerprint() == baseline["font_fingerprint"]

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

    def test_every_page_is_pixel_identical_to_the_recorded_one(
        self, baseline, exported, same_face
    ):
        now = page_digests(exported)
        recorded = baseline["pages"]
        machine_face = set(baseline["font_dependent_pages"])

        assert len(now) >= BASELINE_PAGE_COUNT, "the corpus cannot silently shrink"
        assert machine_face == {1, 2, 4, 6, 8}, (
            "the fixture names the guide page, the three level dividers and "
            "the SOLUTIONS divider as the machine-lettered pages; if that "
            "changed, the baseline's font_dependent_pages must be re-derived"
        )

        compared = 0
        skipped: List[int] = []
        for number, (drawn, was) in enumerate(zip(now, recorded, strict=True), start=1):
            if number in machine_face and not same_face:
                skipped.append(number)  # see the fixture's font_fingerprint_note
                continue
            assert drawn == was, f"interior page {number} is not the page it was"
            compared += 1

        # Exact for the case that actually ran, not a floor both cases satisfy.
        # `>= 6` is the honest count only on a machine whose face differs; on
        # the recording machine the truth is `== 11`, and a floor of six there
        # would stay green while two pages of G-1 evidence quietly stopped
        # being compared.
        expected = BASELINE_PAGE_COUNT - (0 if same_face else len(machine_face))
        assert compared == expected, (
            f"compared {compared} of {BASELINE_PAGE_COUNT} pages, expected "
            f"{expected} on a machine whose face "
            f"{'matches' if same_face else 'differs from'} the baseline's"
        )

        # A green run on a machine with another Arial must say on its face
        # that it is two pages short of the evidence, rather than reporting
        # PASS as if it had compared the book.
        if skipped:
            warnings.warn(
                f"G-1 evidence incomplete: interior pages {skipped} were not "
                f"compared ({compared} of {BASELINE_PAGE_COUNT} pages checked). "
                "This machine letters the guide page and the SOLUTIONS divider "
                "in a different face from the baseline's; see the fixture's "
                "font_fingerprint_note.",
                stacklevel=2,
            )

    def test_the_interior_file_is_the_length_it_was_recorded_with(
        self, baseline, exported_bytes, same_face
    ):
        """F-7's other half: the same bytes, not only the same pixels.

        The new writer mirrors ``PdfImagePlugin._save``'s RGB path object for
        object, and the only thing that differs between the merge-base's file
        and this one is the two ``Info`` timestamps — four bytes of digits
        that do not change the file's length. A writer that re-encoded, chose
        another filter or emitted one object more would move this number long
        before it moved a pixel.

        Gated on the face, because the two machine-lettered pages are inside
        this file: a different Arial gives their JPEG streams a different
        length.
        """
        if not same_face:
            pytest.skip(
                "the guide page and the SOLUTIONS divider are lettered in a "
                "different face here, so the file's length is not the recorded "
                "one; see the fixture's font_fingerprint_note"
            )
        assert len(exported_bytes) == baseline["interior_bytes"]

    def test_the_corpus_covers_every_page_kind_the_interior_has(self, exported):
        """The evidence's own premise: eleven pages, one of every kind.

        A baseline of eleven identical blank pages would pass the comparison
        above and prove nothing — but so would eleven *distinct* pages of the
        wrong kinds. Dropping a divider for a fourth answer page keeps them
        all distinct while the baseline silently stops covering the divider.
        So each kind is identified positively, and distinctness is kept beside
        it. The book prints grouped easy, medium, hard (INV-009, CARD-128), so
        the kinds run:

        * pages 1 and 8 are the guide page and the SOLUTIONS divider, and
          pages 2, 4 and 6 the "Easy", "Medium" and "Hard" level dividers —
          each compared against the page the generator draws for it;
        * page 3 is the two-up page (FR-040), the book's two easy 10x10s:
          each half of it carries its own complete 10x10 grid, which no
          single-puzzle page can do;
        * pages 5 and 7 are single-puzzle pages, and the 15x15 medium and the
          30x30 hard the baseline book declares are **read back off their
          ink** (``drawing_of``), not asked of the layout — in that order,
          because the levels print in that order;
        * pages 9, 10 and 11 are answer pages, one per level: each carries
          solid blocks of ink a filled cell wide, which no blank puzzle page,
          guide or divider has anywhere on it.
        """
        assert len(exported) == BASELINE_PAGE_COUNT
        generator = BookPDFGenerator(corpus_book())

        assert same_page(exported[0], generator.create_guide_page(4, 2, 1, 1))
        assert same_page(exported[7], generator.create_divider_page(8))
        for number, level in ((2, "Easy"), (4, "Medium"), (6, "Hard")):
            assert same_page(
                exported[number - 1], generator.create_divider_page(number, level)
            ), f"interior page {number} should be the {level!r} level divider"

        for number, side in ((5, 15), (7, 30)):
            drawing = drawing_of(exported[number - 1])
            assert (drawing.columns, drawing.rows) == (side, side), (
                f"interior page {number} should be the book's {side}x{side} "
                "puzzle printed alone"
            )

        two_up = exported[2]
        upper = two_up.crop((0, 0, two_up.width, two_up.height // 2))
        lower = two_up.crop((0, two_up.height // 2, two_up.width, two_up.height))
        for half, drawing in (("upper", drawing_of(upper)), ("lower", drawing_of(lower))):
            assert (drawing.columns, drawing.rows) == (10, 10), (
                f"the {half} half of interior page 3 should carry one of the "
                "two 10x10 puzzles the two-up page pairs"
            )

        for number in (9, 10, 11):
            assert solid_ink_blocks(exported[number - 1]), (
                f"interior page {number} should be an answer page, whose "
                "filled cells are solid blocks of ink"
            )
        for number in (1, 2, 3, 4, 5, 6, 7, 8):
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

    def test_the_digest_would_have_caught_a_changed_page(self):
        """The comparison has teeth: one flipped pixel changes the digest."""
        page = Image.new("RGB", (40, 40), "white")
        before = page_digests([page])
        page.putpixel((7, 9), (0, 0, 0))

        assert page_digests([page]) != before


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
        """Both files, nine pages, one retained page bitmap — the cover keeps none.

        ``export_book`` writes the interior and then the cover, and the peak
        over the pair is the same single page bitmap either file costs alone.
        The nine pages are the eight interior pages and the cover, counted by
        the instrument, so a measurement over a book that was never drawn
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
        measures **12.00** page bitmaps on this eleven-page book, 303 MB, and
        4.6 GB on the 182-page one.
        """
        probe = measured.probe

        assert probe.seen == BASELINE_PAGE_COUNT + 1, "eight interior pages and a cover"
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

    def test_the_interior_starts_at_the_guide_page_and_holds_no_cover(self, export):
        interior = pdf_pages(export.interior.getvalue())
        (cover,) = pdf_pages(export.cover.getvalue())
        guide = BookPDFGenerator(corpus_book()).create_guide_page(4, 2, 1, 1)

        assert same_page(interior[0], guide)
        for number, page in enumerate(interior, start=1):
            assert not same_page(page, cover), f"interior page {number} is the cover"

    def test_the_reported_counts_are_the_interiors_own(self, export):
        """The counts come off the page plan now — they must still be the file's."""
        assert export.interior_page_count == pdf_page_count(export.interior.getvalue())
        assert export.interior_page_count == BASELINE_PAGE_COUNT
        assert export.answer_page_count == 3
        assert export.pages_saved == 1  # the one two-up page (FR-040)

    def test_parity_still_counts_from_interior_page_1(self, export):
        """The guide page is right-hand, and the two single-puzzle pages are not.

        Parity counts from interior page 1 — the guide page, which is
        right-hand — and the cover file is never numbered (FR-043, INV-013,
        G-2). On Book 1 the binding-side gutter is 0.5 in and the outside
        margin 0.375 in, so a right-hand page's usable area starts 150 px from
        the left and a left-hand page's 112.5 px, and a drawing centred across
        that area sits 18.75 px right of the trim's middle on a right-hand
        page and 18.75 px left of it on a left-hand one.

        The baseline book's two single-puzzle pages are interior 5 and
        interior 7 since CARD-128 gave each of its three levels a divider
        page, both **odd**, so both must sit right of the middle. That is the
        measurement that would break if the cover ever rejoined the interior's
        numbering: every interior page's parity would flip, and these two
        would land 18.75 px to the *left* instead.

        Measured off the ink alone: the drawing's own edges — its clue
        gutter's outer edge and its grid's right border — never
        ``book_page_spec`` or ``compute_layout``.
        """
        interior = pdf_pages(export.interior.getvalue())
        middle = interior[0].width / 2

        for number in (5, 7):
            drawing = drawing_of(interior[number - 1])
            offset = (drawing.left + drawing.grid_right) / 2 - middle
            assert 12 < offset < 25, (
                f"interior page {number} is centred {offset:.1f} px off the "
                "middle; a right-hand page is about +18.75"
            )

        # And page 1 itself: the guide page's text starts at the gutter
        # margin, 150 px in, not at the 112.5 px outside margin a left-hand
        # page would give it.
        ink = np.asarray(interior[0].convert("L")) < 128
        leftmost = int(np.where(ink.any(axis=0))[0].min())
        assert 145 < leftmost < 160, leftmost


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

    def test_a_page_that_fails_at_page_9_of_11_hands_the_caller_nothing(self):
        """Eight pages were already in the buffer, and no file came out.

        The mechanism is that the buffer is a local of ``_write_pdf`` and is
        returned only after the trailer: a failure mid-walk propagates and
        takes the partial bytes with it, unreferenced. What this measures is
        both halves — that real bytes had been written (so the test is not
        passing on a failure that happened too early to matter) and that the
        caller got an exception rather than a truncated PDF.
        """
        written: List[int] = []
        write_page = BookPDFGenerator._write_page
        answer_page = BookPDFGenerator._answer_page

        def counting(self, *args, **kwargs):
            written.append(1)
            return write_page(self, *args, **kwargs)

        def refuses(self, *args, **kwargs):
            raise ValueError("this answer will not draw")

        BookPDFGenerator._write_page = counting
        BookPDFGenerator._answer_page = refuses
        try:
            with pytest.raises(RuntimeError) as raised:
                export_of(BookPDFGenerator(corpus_book()), baseline_puzzles())
        finally:
            BookPDFGenerator._write_page = write_page
            BookPDFGenerator._answer_page = answer_page

        assert "could not be drawn" in str(raised.value)
        # Guide, three level dividers, the two-up page, two single-puzzle
        # pages and the SOLUTIONS divider: eight pages of a planned eleven
        # were bytes in the buffer already.
        assert written == [1] * 8, written

    def test_a_producer_that_yields_too_few_pages_never_reaches_the_trailer(self):
        """A short stream would leave the page tree pointing at nothing."""
        generator = BookPDFGenerator(corpus_book())
        blank = Image.new("RGB", (60, 80), "white")

        def two_of_three() -> Iterator[Image.Image]:
            yield blank
            yield blank

        with pytest.raises(RuntimeError) as raised:
            generator._write_pdf(two_of_three(), 3)

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
            generator._write_pdf(four_of_three(), 3)

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
