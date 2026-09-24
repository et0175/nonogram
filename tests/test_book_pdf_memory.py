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
:class:`LivePageBytes` counts **live page-bitmap bytes**: it wraps the page
producer, keeps a :mod:`weakref` to every page it passes on together with that
page's ``width * height * len(mode)``, and samples the sum of the pages still
alive each time a new one is produced. CPython's refcounting makes "the
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

The instrument is proved non-vacuous before it is trusted:
:meth:`TestBookPdfMemory_PeakDoesNotGrowWithPageCount.test_the_same_instrument_sees_the_old_shape_grow`
runs it over ``interior_pages`` — the list-returning API the export used to go
through, still present for the callers that want every page — and watches the
peak grow by one page bitmap per page. Same probe, same pages, same book: only
the shape differs.

Peak is not O(1), and this module does not claim it is
-------------------------------------------------------
The page bitmaps are O(one page). The written PDF is not: it accumulates in
the returned ``BytesIO`` at a measured ~0.46 MB per page, so a 179-page
interior still holds ~82 MB of compressed output at the end. That is 55x
better than 25.2 MB a page and it fits the envelope with the request around
it, but it is a real linear term and
:meth:`TestBookPdfMemory_RealBookExportsUnderTheCap.test_the_residual_linear_term_is_the_written_file_and_it_is_small`
measures and states it rather than letting the module read as a claim of
constant memory.

Cost: the corpus book is exported **once** for the whole module (a
module-scoped fixture), for about 7 seconds of real rendering and writing;
the whole file runs in well under a minute. The 150-puzzle book is never
faked — a page count is the one thing a memory test must not fake.
"""

from __future__ import annotations

import itertools
import resource
import time
import tracemalloc
import weakref
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Iterator, List

import numpy as np
import pytest
from PIL import Image

from nonogram.admin.book_pdf_generator import BookPDFGenerator
from tests.helpers.book_corpus import (
    BASELINE_PAGE_COUNT,
    CORPUS_PAGE_COUNT,
    CORPUS_PUZZLE_COUNT,
    baseline_puzzles,
    corpus_book,
    corpus_puzzles,
    export_of,
    font_fingerprint,
    load_baseline,
    page_digests,
)
from tests.helpers.page_ink import drawing_of
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

#: What a streaming export is allowed to hold in page bitmaps. Two, not one:
#: the writer holds the page it is encoding, and the instrument's own sample
#: is taken at the moment the next page has just been built — so a shape that
#: overlapped two pages by one step would still be within this cap, and a
#: shape that kept a third would not. Stated in page bitmaps because that is
#: the unit the defect is measured in; in megabytes it is 50.5.
PEAK_CAP_IN_PAGES = 2

#: The book title the cover file carries (AC-4).
BOOK_TITLE = "Winter Pictures"


# --------------------------------------------------------------------------
# The instrument
# --------------------------------------------------------------------------


@dataclass
class LivePageBytes:
    """How many bytes of page bitmap are alive at once, sampled exactly.

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

    Attributes:
        peak: The largest live total seen, in bytes.
        seen: How many pages went past — a corpus-size guard, so a test cannot
            pass by measuring a book that was never built.
        page_bytes: The largest single page's cost, for the arithmetic that
            derives the old shape's peak from a measured constant rather than
            from a hard-coded one.
    """

    peak: int = 0
    seen: int = 0
    page_bytes: int = 0
    _live: Dict[int, int] = field(default_factory=dict)
    _keys: Iterator[int] = field(default_factory=itertools.count)

    def watch(self, pages: Iterable[Image.Image]) -> Iterator[Image.Image]:
        """``pages``, costed as they go past and released immediately after."""
        for page in pages:
            self.track(page)
            yield page
            del page

    def track(self, page: Image.Image) -> None:
        """Register one page's bitmap and re-sample the live total."""
        cost = page.width * page.height * len(page.mode)
        key = next(self._keys)
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
    """One export, with what it cost: the file, the probe and the wall clock."""

    data: bytes
    probe: LivePageBytes
    seconds: float


def _measured(export) -> MeasuredExport:
    """Run ``export()`` with the probe interposed on the real export path.

    ``BookPDFGenerator._write_pdf`` is the one seam every export goes through
    — ``export_interior``, ``export_cover`` and ``export_book`` all hand it a
    page producer and a page count — so wrapping its producer measures what a
    route really does, restoring the class afterwards whether or not the
    export raised.
    """
    probe = LivePageBytes()
    original = BookPDFGenerator._write_pdf

    def patched(self, pages, page_count):
        return original(self, probe.watch(pages), page_count)

    BookPDFGenerator._write_pdf = patched
    try:
        started = time.perf_counter()
        data = export()
        elapsed = time.perf_counter() - started
    finally:
        BookPDFGenerator._write_pdf = original
    return MeasuredExport(data=data, probe=probe, seconds=elapsed)


@pytest.fixture(scope="module")
def corpus_export() -> MeasuredExport:
    """The 150-puzzle book, exported end to end once for the whole module.

    A real export of a real book: 150 puzzles, none of which pairs two-up, so
    the interior is 1 guide + 150 puzzle pages + 1 divider + 27 answer pages =
    179 pages of 25.2 MB bitmap each. Roughly seven seconds; shared, because
    two tests need it and neither needs its own copy.
    """
    return _measured(
        lambda: export_of(BookPDFGenerator(corpus_book()), corpus_puzzles())
    )


@pytest.fixture(scope="module")
def small_export() -> MeasuredExport:
    """The eight-page baseline book, exported the same way, for comparison."""
    return _measured(
        lambda: export_of(BookPDFGenerator(corpus_book()), baseline_puzzles())
    )


# --------------------------------------------------------------------------
# AC-1 — peak does not grow with the page count
# --------------------------------------------------------------------------


class TestBookPdfMemory_PeakDoesNotGrowWithPageCount:
    """A 179-page book's peak page-bitmap memory is a small book's peak.

    "Within a small constant" is stated in **page bitmaps**, not megabytes,
    because a page bitmap is the unit the defect was measured in: the old
    shape's peak was one page bitmap per page, and what this asserts is that
    the difference between a 179-page book and an 8-page one is under one.
    """

    def test_one_page_costs_what_the_card_says(self, small_export):
        """The premise, measured: a Book 1 page is 25,245,000 bytes."""
        assert small_export.probe.page_bytes == PAGE_BITMAP_BYTES
        assert PAGE_BITMAP_BYTES == 25_245_000  # 24.1 MiB, the card's figure

    def test_a_big_books_peak_is_a_small_books_peak(self, small_export, corpus_export):
        small, big = small_export.probe, corpus_export.probe

        assert small.seen == BASELINE_PAGE_COUNT
        assert big.seen == CORPUS_PAGE_COUNT
        assert big.seen > 20 * small.seen, "the two books must differ in size"
        assert big.peak - small.peak < PAGE_BITMAP_BYTES, (
            f"{big.seen} pages peaked at {big.peak_in_pages:.2f} page bitmaps, "
            f"{small.seen} pages at {small.peak_in_pages:.2f}"
        )

    def test_neither_book_holds_more_than_the_cap(self, small_export, corpus_export):
        for export in (small_export, corpus_export):
            assert export.probe.peak <= PEAK_CAP_IN_PAGES * PAGE_BITMAP_BYTES, (
                f"{export.probe.seen} pages peaked at "
                f"{export.probe.peak_in_pages:.2f} page bitmaps"
            )

    def test_the_same_instrument_sees_the_old_shape_grow(self):
        """Verify by revert: the probe measures the list shape as linear.

        The claim "peak does not grow with the page count" is only worth
        anything if the instrument would have said otherwise about the code
        this card replaced. ``interior_pages`` is still that shape — it returns
        every page in a list — so the same probe, over the same pages of the
        same book, is run across it here. Six pages is enough to see a line
        and cheap enough to draw: the peak rises by exactly one page bitmap
        per page, which is the 25.2 MB-a-page growth the panel was killed by.
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
# AC-2 — a real 150-puzzle book exports under the cap
# --------------------------------------------------------------------------


class TestBookPdfMemory_RealBookExportsUnderTheCap:
    """A 150-puzzle book exports to a valid 179-page PDF inside the envelope.

    **The criterion as the card wrote it cannot be tested honestly, and this
    is the honest version.** The card asks for "a 150-page book exports
    successfully under a memory cap that the current code fails". The second
    half of that sentence cannot be executed once the current code is gone —
    there is nothing left to fail it — and the only way to make a cap bite for
    real, ``setrlimit(RLIMIT_AS)`` under pytest, is a platform-dependent flake
    that would take the whole session down with it rather than one test.

    What is measured instead, all of it real:

    1. A 150-puzzle book is exported end to end, and the file that comes out
       is a valid PDF whose page tree holds the 179 pages the plan declared.
       The page count is never faked — the pages are drawn.
    2. Its measured peak live page-bitmap memory is under a cap stated as a
       small multiple of one page bitmap.
    3. The old shape's peak for **this same book** is derived from the
       instrument's own measured per-page constant — not from a literal — and
       shown to exceed the 512 MB envelope by a wide margin. That is the "a
       cap the current code fails" half, as arithmetic over a measured number
       rather than as a process that has to be killed to prove it.
    4. The residual linear term — the written file, which does grow with the
       page count — is measured and stated, so the module claims what the code
       has and not a constant it does not.
    """

    def test_the_book_really_exports_and_the_file_holds_every_page(self, corpus_export):
        assert corpus_export.probe.seen == CORPUS_PAGE_COUNT
        assert pdf_page_count(corpus_export.data) == CORPUS_PAGE_COUNT
        assert CORPUS_PUZZLE_COUNT >= 150, "the card's book is 150 puzzles"
        assert CORPUS_PAGE_COUNT >= 150, "the card's book is 150+ pages"

    def test_its_peak_page_memory_is_under_the_cap(self, corpus_export):
        probe = corpus_export.probe

        assert probe.peak <= PEAK_CAP_IN_PAGES * PAGE_BITMAP_BYTES, (
            f"peaked at {probe.peak_in_pages:.2f} page bitmaps "
            f"({probe.peak / 1e6:.1f} MB) over {probe.seen} pages"
        )

    def test_the_old_shape_would_not_have_fitted_the_envelope(self, corpus_export):
        """The half of the criterion that is arithmetic, over a measured constant.

        The list shape held every page at once — which
        ``test_the_same_instrument_sees_the_old_shape_grow`` measures directly
        — so its peak for this book is the page count times the per-page cost
        the probe measured on this very export. Nothing here is hard-coded but
        the envelope itself.
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
        """Peak memory is O(one page) + O(the file), and the file is the term.

        The PDF accumulates in the ``BytesIO`` the export returns, so the true
        peak is the page bitmap plus however much of the file has been written
        — a real linear term of well under a megabyte a page. It is asserted
        here at two bounds: it must stay under 1 MB a page (or the compression
        has changed), and the whole envelope — peak bitmaps plus the finished
        file — must fit the panel's 512 MB with room for the request around
        it.
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
        assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss > 0  # RSS exists

    def test_a_real_book_exports_in_seconds_not_minutes(self, corpus_export):
        """CARD-145 item 4's measurement, kept live (see the card's notes).

        The card feared a route that "looks dead for two minutes" and asked
        for a progress mechanism. A 179-page book exports in single-digit
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
    """Every exported page is the page the merge-base drew, to the pixel (G-1).

    The evidence is ``tests/fixtures/book_baseline_card145.json``, recorded
    from commit ``b4c523d`` — the merge-base, before a line of this card's
    production change existed — by exporting
    ``tests/helpers/book_corpus.baseline_puzzles`` with the untouched code,
    reading the pages back **out of the PDF** with the shared
    ``pdf_pages`` helper, and digesting each one's raw bitmap. It covers the
    whole path: draw, JPEG-encode, write, parse, decode.

    The comparison is exact — a sha256 of ``Image.tobytes()`` — and
    deliberately not ``pdf_pages.same_page``, which tolerates JPEG noise and a
    6-level mean difference and would hide precisely the kind of change this
    exists to catch.

    That fixture is never to be regenerated to make this test pass; it says so
    in its own ``warning`` field.
    """

    @pytest.fixture(scope="class")
    def baseline(self) -> Dict[str, Any]:
        recorded = load_baseline()
        if font_fingerprint() != recorded["font_fingerprint"]:
            pytest.skip(
                "the guide page and the SOLUTIONS divider are lettered in a "
                "different face on this machine than the one the baseline was "
                "recorded on, so their pixels cannot be compared; see the "
                "fixture's font_fingerprint_note"
            )
        return recorded

    @pytest.fixture(scope="class")
    def exported(self) -> List[Image.Image]:
        return pdf_pages(
            export_of(BookPDFGenerator(corpus_book()), baseline_puzzles())
        )

    def test_the_book_still_has_the_page_count_it_was_recorded_with(
        self, baseline, exported
    ):
        assert baseline["page_count"] == BASELINE_PAGE_COUNT
        assert len(exported) == baseline["page_count"]

    def test_every_page_is_pixel_identical_to_the_recorded_one(
        self, baseline, exported
    ):
        now = page_digests(exported)
        recorded = baseline["pages"]

        assert len(now) >= BASELINE_PAGE_COUNT, "the corpus cannot silently shrink"
        for number, (drawn, was) in enumerate(zip(now, recorded, strict=True), start=1):
            assert drawn == was, f"interior page {number} is not the page it was"

    def test_the_corpus_covers_every_page_kind_the_interior_has(self, exported):
        """The evidence's own premise: eight pages, one of every kind.

        A baseline of eight identical blank pages would pass the comparison
        above and prove nothing. These eight are the guide page, a
        single-puzzle page, a two-up page, a single-puzzle page, the SOLUTIONS
        divider and three answer pages — asserted by the one thing that tells
        them apart without re-deriving them from the generator: no two of them
        are the same page.
        """
        assert len(exported) == BASELINE_PAGE_COUNT
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
    """

    @pytest.fixture(scope="class")
    def export(self):
        return BookPDFGenerator(corpus_book()).export_book(
            baseline_puzzles(), BOOK_TITLE
        )

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
        """The guide page is right-hand, and page 2 and page 4 are left-hand.

        Parity counts from interior page 1 — the guide page, which is
        right-hand — and the cover file is never numbered (FR-043, INV-013,
        G-2). On Book 1 the binding-side gutter is 0.5 in and the outside
        margin 0.375 in, so a right-hand page's usable area starts 150 px from
        the left and a left-hand page's 112.5 px, and a drawing centred across
        that area sits 18.75 px right of the trim's middle on a right-hand
        page and 18.75 px left of it on a left-hand one.

        The baseline book's two single-puzzle pages are interior 2 and
        interior 4, both **even**, so both must sit left of the middle. That
        is the measurement that would break if the cover ever rejoined the
        interior's numbering: every interior page's parity would flip, and
        these two would land 18.75 px to the *right* instead.

        Measured off the ink alone: the drawing's own edges — its clue
        gutter's outer edge and its grid's right border — never
        ``book_page_spec`` or ``compute_layout``.
        """
        interior = pdf_pages(export.interior.getvalue())
        middle = interior[0].width / 2

        for number in (2, 4):
            drawing = drawing_of(interior[number - 1])
            offset = (drawing.left + drawing.grid_right) / 2 - middle
            assert -25 < offset < -12, (
                f"interior page {number} is centred {offset:.1f} px off the "
                "middle; a left-hand page is about -18.75"
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

    def test_a_page_that_fails_at_page_6_of_8_hands_the_caller_nothing(self):
        """Five pages were already in the buffer, and no file came out.

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
        # Guide, two single-puzzle pages, the two-up page and the divider:
        # five pages of a planned eight were bytes in the buffer already.
        assert written == [1] * 5, written

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
