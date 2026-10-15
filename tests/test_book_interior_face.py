"""The book interior letters from packaged data, so its geometry is the host's business no more (CARD-221).

Until this card ``book_pdf_generator._guide_face`` asked Pillow for the
**host's** Arial by path and fell back to Pillow's own built-in face, and every
reader-facing interior face but the band went through it: both guide pages, the
level and SOLUTIONS dividers, the table of contents. The folio's own
reservation, by contrast, already came from the **packaged** DejaVu Sans. So the
interior's row geometry was a function of what fonts the machine happened to
have while the space reserved for the page number was not — and a book's page
count selects its printed KDP gutter band (``book_kdp.kdp_page_band``), which
KDP *rejects a cover for* when it is wrong. Measured before the card, at Book
1's trim: a TOC page held 42 rows on Arial and 40 on the fallback, and the same
83-row list took 2 pages on one face and 3 on the other.

This module is the direct test of the fix: it exports and plans the same books
twice in one process — once with the host's Arial available, once with
``ImageFont.truetype`` made to refuse every host path, which is how the card's
measurements were taken — and asserts the two runs agree about every page's
pixels, the page count and the gutter band. It also pins the two facts the fix
rests on: the packaged face carries every character the interior prints, and no
face the interior draws with is read from a filesystem path at all.

**What AC-1 guarantees, stated exactly** (review cycle 1, F-005). These
tests prove the interior is identical **on one Pillow/FreeType build with
the host's font paths refused** — not "on any machine". The face is the
repository's now, but the rasteriser is the environment's:
``pyproject.toml`` floors Pillow at ``>=10.0`` with no ceiling, every
measurement here comes off ``getmetrics()``, and one pixel of ascent per
row is what separated 42 TOC rows from 41 when the face itself was the
host's. A FreeType bump can therefore still move a page count. Nothing in
this module detects that — what does is the baseline comparison in
``tests/test_book_pdf_memory.py``, which digests all thirteen interior
pages against ``book_baseline_card221.json`` with no face gate left to skip
it, so a rasteriser that redraws a glyph reds the suite on the machine that
bumped it. Bounding Pillow is an ADR-0006/R1 question, carded rather than
decided here.

**Each claim is backed by its own negative control**, because "two runs of
deterministic code agree" is exactly the kind of assertion that passes when it
has stopped testing anything. Every comparison below is run a second time
against a deliberately host-dependent face — the pre-card ``_guide_face``,
restored locally — and asserted to **disagree** there. A test that cannot tell
the fixed code from the code it fixed would be worthless, and these say so in
their own failure messages rather than in a comment.
"""

from __future__ import annotations

from importlib import resources
from io import BytesIO
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Tuple

import pytest
from PIL import Image, ImageDraw, ImageFont

from nonogram.admin import book_pdf_generator
from nonogram.admin.book_kdp import (
    kdp_min_gutter_cm,
    kdp_page_band,
    unpaired_interior_page_count,
)
from nonogram.admin.book_manager import Book, BookMetadata
from nonogram.admin.book_pdf_generator import (
    BAND_SEPARATOR,
    BookPDFGenerator,
    interior_page_count,
    type_px,
)
from nonogram.export.pdf import FONT_PACKAGE, FONT_RESOURCE

from tests.helpers.book_corpus import (
    BASELINE_PAGE_COUNT,
    baseline_puzzles,
    corpus_book,
    export_of,
    page_digests,
    puzzle,
)
from tests.helpers.pdf_pages import pdf_pages

# --------------------------------------------------------------------------
# What the card asks for, written out rather than imported
# --------------------------------------------------------------------------

#: The host path the interior asked Pillow for until this card.
ARIAL_PATH = "/System/Library/Fonts/Arial.ttf"

#: The resolution a book page is drawn at, written out here so this module's
#: own arithmetic is its own.
BOOK_DPI = 300

#: Every character the interior prints, as the strings it prints them in —
#: collected by ``test_the_recorded_repertoire_is_what_the_interior_draws``
#: below from a real export, so this constant cannot drift away from the page.
#: The four non-ASCII ones are the point of the list: ``·`` separates a band's
#: number from its tier (:data:`BAND_SEPARATOR`), ``—`` sets an answer
#: caption, ``–`` spans a TOC row's puzzle range and ``…`` ends a clipped
#: label.
NON_ASCII_INTERIOR_CHARACTERS = ("·", "—", "–", "…")


def packaged_face(size_px: int) -> ImageFont.FreeTypeFont:
    """The packaged face at ``size_px``, addressed as package data.

    The page's own lookup, reimplemented rather than imported (CLAUDE.md
    prefers an independent second implementation to re-deriving a value with
    the function under test).
    """
    data = resources.files(FONT_PACKAGE).joinpath(FONT_RESOURCE).read_bytes()
    return ImageFont.truetype(BytesIO(data), size=size_px)


def host_face(size_px: int) -> Any:
    """``_guide_face`` **as it stood before this card**: Arial, then Pillow's.

    Kept here as every comparison's negative control. It is the code CARD-221
    deleted, transcribed, so that each claim below can be shown to fail
    against it — which is what makes the same claim's green run on the real
    ``_guide_face`` evidence rather than a tautology.
    """
    try:
        return ImageFont.truetype(ARIAL_PATH, size_px)
    except OSError:  # pragma: no cover - only on a machine without Arial
        try:
            return ImageFont.load_default(size_px)
        except TypeError:  # pragma: no cover - Pillow < 10.1
            return ImageFont.load_default()


def host_offers_a_second_face() -> bool:
    """Whether **this** machine can tell the pre-card code's two faces apart.

    The one genuinely host-dependent question in this module, and it gates
    exactly one test: the negative control below restores the host lookup
    CARD-221 deleted and asserts that the interior's pages then *differ*
    between a host with Arial and one without. That contrast needs a host
    Arial which is not Pillow's own built-in face — true on the owner's Mac,
    false on the project's Linux deployment image (no Arial at all) and false
    under the off-host plugin the card's measurements were taken with, where
    both runs resolve the same fallback and nothing can move.

    Measured, not assumed: the same sample the removed ``font_fingerprint``
    digested, drawn at the guide title's own size in both faces and compared
    as pixels. Everything else in this module is host-independent and
    ungated, which is the point of the card.
    """
    try:
        arial = ImageFont.truetype(ARIAL_PATH, type_px(22.0, BOOK_DPI))
    except OSError:
        return False
    fallback = ImageFont.load_default(type_px(22.0, BOOK_DPI))

    def sample(face: Any) -> bytes:
        image = Image.new("L", (900, 120), 255)
        ImageDraw.Draw(image).text((0, 0), "How to Solve Nonograms", fill=0, font=face)
        return image.tobytes()

    return sample(arial) != sample(fallback)


def clear_font_caches() -> None:
    """Empty the module's two font caches (AC/EC/G gate, F-G1).

    ``book_pdf_generator._band_font`` is an ``lru_cache(maxsize=8)`` over
    ``(size,)`` and ``_band_font_bytes`` an ``lru_cache(maxsize=1)``, so a
    face or its bytes loaded under one font configuration is reused under
    the next one in the same process. Every comparison in this module runs
    both configurations in one process, which is exactly the case those
    caches cannot tell apart — so they are emptied at each boundary rather
    than trusted. ``_guide_face`` is deliberately uncached and needs none of
    this.
    """
    book_pdf_generator._band_font.cache_clear()
    book_pdf_generator._band_font_bytes.cache_clear()


def refuse_host_fonts(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make every ``ImageFont.truetype`` call that names a *path* fail.

    The off-host machine, simulated: on the project's own Linux deployment
    image there is no Arial at :data:`ARIAL_PATH`, and this is how the card's
    own measurements were taken. Broader than
    ``tests/test_book_interior_type_floor.py``'s ``without_arial``, which
    refuses that one path: a host face found under any other name would pass
    that and fail this, and the claim here is about host fonts as a class.

    A file object is passed through untouched — that is how the packaged face
    is addressed (``BytesIO`` over ``importlib.resources`` bytes), so this
    simulation leaves the fix itself alone, which is the only reason the
    comparison below can mean anything.

    **It clears the module's font caches, and that is load-bearing**
    (AC/EC/G gate, F-G1). ``_band_font`` is ``lru_cache(maxsize=8)`` and
    ``_band_font_bytes`` ``maxsize=1``, so a face loaded during the on-host
    half is still in the cache when the off-host half runs in the same
    process. With a host lookup mutated back in, that cache carried Arial
    across the boundary and **all four AC-1 comparisons stayed green against
    the restored defect** — the tests were comparing one run with itself.
    Clearing both caches on the way in is what makes the second half a
    second measurement. :func:`_both_faces` clears them on both sides of
    its own pair for the same reason — a face cached while the host was
    refused must not leak into whatever runs next.
    """
    original = ImageFont.truetype

    def truetype(font=None, *args, **kwargs):
        if isinstance(font, (str, bytes)):
            raise OSError(f"this host has no font at {font!r}")
        return original(font, *args, **kwargs)

    monkeypatch.setattr(ImageFont, "truetype", truetype)
    clear_font_caches()


def _interior(book_factory: Callable[[], Book], puzzles: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int, bytes]:
    """One book's exported interior: its page digests, page count and bytes."""
    written = export_of(BookPDFGenerator(book_factory()), puzzles)
    pages = pdf_pages(written)
    return page_digests(pages), len(pages), written


def _both_faces(measure: Callable[[], Any]) -> Tuple[Any, Any]:
    """``measure()`` with the host's fonts available, and again without them.

    It takes no ``monkeypatch`` on purpose (review cycle 1, F-006, which
    found it taking one it never used). The on-host half must run with
    **nothing** patched, so the only patch context here is the one this
    function opens and closes around the off-host half; a fixture passed in
    from the caller would be a patch that outlives it, and two halves
    sharing one context is how this comparison would quietly become
    self-fulfilling.
    """
    clear_font_caches()
    on_host = measure()
    with pytest.MonkeyPatch.context() as context:
        refuse_host_fonts(context)  # clears the caches itself, see F-G1 there
        off_host = measure()
    clear_font_caches()
    return on_host, off_host


# --------------------------------------------------------------------------
# AC-1 — the interior's geometry does not depend on the host
# --------------------------------------------------------------------------


def _min_trim_book() -> Book:
    """The baseline book's print specification at the 10x10 cm minimum trim.

    The tightest sheet ``book_page_spec`` lays out, where the guide page's
    fallback ladder, the TOC's capacity and the folio's own clearance are all
    at their most sensitive to a face's metrics — i.e. the book most likely
    to disagree between two faces if anything still does.
    """
    return Book(
        book_id="card-221-min-trim",
        metadata=BookMetadata(
            title="Winter Pictures",
            description="The book CARD-221's determinism test exports twice.",
            theme="generic",
            target_audience="adults",
            size="",
            page_count=0,
        ),
        trim_width_cm="10.00",
        trim_height_cm="10.00",
        gutter_margin_cm="0.95",
        outside_margin_cm="0.64",
    )


class TestBookInterior_GeometryIsIdenticalWithAndWithoutHostFonts:
    """AC-1 — the same book, exported with and without the host's Arial, is
    the same book: every page's digest, the interior's page count and the
    gutter band the count chooses.
    """

    def test_every_page_of_the_baseline_book_is_the_same_page_on_both_faces(self) -> None:
        """The whole interior, page for page, at the shipped Book 1 trim."""
        on_host, off_host = _both_faces(
            lambda: _interior(corpus_book, baseline_puzzles())
        )
        host_digests, host_pages, host_bytes = on_host
        bare_digests, bare_pages, bare_bytes = off_host

        assert host_pages == bare_pages == BASELINE_PAGE_COUNT, (
            f"the interior is {host_pages} pages with the host's fonts and "
            f"{bare_pages} without them"
        )
        for number, (with_host, without) in enumerate(
            zip(host_digests, bare_digests, strict=True), start=1
        ):
            assert with_host == without, (
                f"interior page {number} is a different page when the host's "
                "fonts are refused — some face the interior letters in is "
                "still resolved off the machine"
            )
        assert len(host_bytes) == len(bare_bytes), (
            "the two interiors are the same pages but not the same file: "
            f"{len(host_bytes)} bytes against {len(bare_bytes)}"
        )

    def test_the_minimum_trim_is_the_same_book_on_both_faces(self) -> None:
        """The same claim on the tightest sheet a book can be stored with.

        Measured separately from Book 1 because this is the trim where a
        face's metrics decide things Book 1's own slack hides: which of
        ``create_guide_page``'s five fallback forms is drawn, how many rows a
        TOC page holds, and whether ``_draw_folio`` finds room at all.
        """
        single = [puzzle("card221-mintrim", 20, 20, 5, "easy", "Solo")]
        on_host, off_host = _both_faces(lambda: _interior(_min_trim_book, single))
        host_digests, host_pages, _ = on_host
        bare_digests, bare_pages, _ = off_host

        assert host_pages == bare_pages, (
            f"the min-trim interior is {host_pages} pages with the host's "
            f"fonts and {bare_pages} without them"
        )
        assert host_digests == bare_digests, (
            "a page of the min-trim book differs between the two faces — the "
            f"first is page "
            f"{next(i for i, (a, b) in enumerate(zip(host_digests, bare_digests), 1) if a != b)}"
        )

    @pytest.mark.parametrize("count", [4, 83, 150])
    def test_the_page_count_and_its_gutter_band_agree_on_both_faces(self, count) -> None:
        """The defect as the owner would have met it: the printed gutter.

        The page count is what selects KDP's gutter band, and a book
        finalised on one machine and generated on another must not land in
        two different bands. Asserted through all three page-count paths at
        once — ``book_kdp.unpaired_interior_page_count`` (what finalise
        checks the stored gutter against), ``interior_page_count`` (the
        sheet-free bound) and the generator's own stream — and then through
        the band and the minimum gutter those counts choose.

        83 puzzles is the card's own measured case (a list of that many rows
        took 2 TOC pages on Arial and 3 on the fallback before CARD-205
        made the list structural); 150 is the corpus the gutter tests use,
        where the pre-CARD-205 rule put the count 3 pages apart.

        **None of those three counts witnesses anything, and the AC/EC/G
        gate was right to say so.** All three are Book 1 books whose
        structural list is eight rows against a capacity of 41 packaged, 42
        on Arial and 40 on Pillow's built-in face — one TOC page on every
        face, so this test passed with the pre-card host lookup fully
        restored. Face sensitivity at Book 1's trim begins at 42 rows, and
        no book in this suite has a TOC that spills. The witness is
        :meth:`test_a_toc_that_spills_on_one_face_but_not_the_other_still_agrees`
        below, which AC-2 was amended to name; these three stay because a
        page count that agrees across faces on the shapes the product
        actually ships is still worth asserting — they are the control, not
        the evidence.
        """
        puzzles = [
            puzzle(f"card221-count-{index}", 10, 10, 3, "easy", f"P{index}")
            for index in range(count)
        ]
        book = corpus_book(f"card-221-gutter-{count}")

        def measure() -> Tuple[int, int, Tuple[int, int], float]:
            stream = BookPDFGenerator(book).interior_stream(list(puzzles))
            unpaired = unpaired_interior_page_count(puzzles, book=book)
            sheet_free = interior_page_count(len(puzzles))
            return (
                unpaired,
                sheet_free,
                kdp_page_band(unpaired),
                kdp_min_gutter_cm(unpaired),
            ), stream.unpaired_page_count

        (on_host, on_host_stream), (off_host, off_host_stream) = _both_faces(measure)

        assert on_host == off_host, (
            "the page count, or the gutter band it chooses, depends on the "
            f"host's fonts: {on_host} with them, {off_host} without"
        )
        assert on_host_stream == off_host_stream == on_host[0], (
            "the generator's own unpaired page count must agree with KDP's "
            f"on both faces: {on_host_stream} / {off_host_stream} against "
            f"{on_host[0]}"
        )

    #: The smallest structural list that spills a TOC page at the smallest
    #: trim a book can be stored at — the one shape in reach whose PAGE
    #: COUNT, and therefore whose printed KDP gutter band, is face-dependent
    #: (AC-2, amended at the decompose station on the gate's finding).
    #: Measured on the 10.00 cm frame: capacity is **9 rows on the packaged
    #: face and 10 on Arial**, so ten rows are 2 TOC pages on one and 1 on
    #: the other. Ten rows is ``structural_toc_entry_count(4, …)`` — a
    #: four-level book, which ADR-0031's three stocked tiers do not produce
    #: today; that is the hypothesis this case makes and the only one, and
    #: it is made because every page-count caller reaches
    #: ``measured_toc_page_count`` with whatever row count its book has, so
    #: the arithmetic under test is the shipped arithmetic.
    SPILLING_LEVELS = 4

    #: 72 puzzles on 71 puzzle pages (one two-up pair) and 72 answer pages,
    #: chosen so the interior lands **exactly on KDP's 150/151 band edge**:
    #: with one TOC page it is 150 pages and the gutter minimum is 0.9525 cm,
    #: with two it is 151 and the minimum is 1.27 cm. So the extra page the
    #: face decides does not merely move a number — it moves the margin the
    #: cover is printed against, which is the defect this card exists to
    #: close, and the assertion below is on the band and the centimetres as
    #: well as the count.
    SPILLING_PUZZLES = 72
    SPILLING_PUZZLE_PAGES = 71

    def test_a_toc_that_spills_on_one_face_but_not_the_other_still_agrees(self) -> None:
        """AC-2's witness: the one shape whose gutter band the face decides.

        Composed of the real functions, on the real 10.00 cm frame
        (``MIN_TRIM_CM``): ``_toc_entries_per_page`` for the capacity,
        ``measured_toc_page_count`` for the split, ``interior_page_count``
        for the total — the sheet-free caller, fed this book's own page
        terms — and ``kdp_page_band``/``kdp_min_gutter_cm`` for what the
        total prints. Only the row count is hypothetical
        (:data:`SPILLING_LEVELS`), and it is derived through
        ``structural_toc_entry_count`` rather than written as a literal.

        The non-vacuity assertions are the point of the case: on the
        packaged face this frame really must hold 9 rows and really must
        split ten of them onto two pages. If a later change moves that
        capacity, this stops being a witness, and the test says so rather
        than passing because nothing spills any more. They are checked
        after the agreement, not before it, so that the two failures read
        as what they are — see the comment at each.
        """
        from nonogram.admin.book_pdf_generator import (
            _toc_entries_per_page,
            measured_toc_page_count,
            structural_toc_entry_count,
        )
        from nonogram.admin.book_kdp import _toc_frame_for

        frame = _toc_frame_for(SimpleNamespace(trim_height_cm="10.00"))
        rows = structural_toc_entry_count(self.SPILLING_LEVELS, self.SPILLING_PUZZLES)
        assert rows == 10, rows

        def measure():
            capacity = _toc_entries_per_page(frame, BOOK_DPI)
            toc_pages = measured_toc_page_count(rows, frame, BOOK_DPI)
            total = interior_page_count(
                self.SPILLING_PUZZLES,
                puzzle_pages=self.SPILLING_PUZZLE_PAGES,
                answer_pages=self.SPILLING_PUZZLES,
                level_dividers=3,
                toc_pages=toc_pages,
            )
            return capacity, toc_pages, total, kdp_page_band(total), kdp_min_gutter_cm(total)

        on_host, off_host = _both_faces(measure)

        # The claim first, so that a restored host lookup fails on what it
        # actually broke rather than on this case's own premise: under the
        # pre-card `_guide_face` the on-host half reads Arial's capacity of
        # 10 and the off-host half the fallback's 9, and it is the
        # disagreement that should be reported, not "ten rows no longer
        # spill".
        assert on_host == off_host, (
            "the TOC's page count — and with it the interior's total and the "
            "KDP gutter band the cover is printed against — depends on the "
            f"host's fonts: {on_host} with them, {off_host} without. On "
            "Arial this frame holds 10 rows and this list is one page; on "
            "the packaged face it holds 9 and the list is two"
        )

        # And this case is a witness only while these hold. They run after
        # the comparison because an agreement that is true for the wrong
        # reason — nothing spilling at all — is the one way the assertion
        # above could pass vacuously, and these are what say so.
        assert on_host[0] == 9, (
            f"the 10.00 cm frame holds {on_host[0]} TOC rows, not the 9 this "
            "case needs to be a witness: ten rows no longer spill here, and "
            "the comparison above has nothing face-dependent left to catch"
        )
        assert on_host[1] == 2, (
            f"{rows} rows are {on_host[1]} TOC page(s) on this frame, not the "
            "2 that make the page count face-dependent"
        )
        assert on_host[2] == 151 and on_host[3] == (151, 300), on_host
        assert interior_page_count(
            self.SPILLING_PUZZLES,
            puzzle_pages=self.SPILLING_PUZZLE_PAGES,
            answer_pages=self.SPILLING_PUZZLES,
            level_dividers=3,
            toc_pages=1,
        ) == 150, (
            "this case's own premise: one TOC page fewer puts this book at "
            "150 pages, the last page of KDP's first gutter band, so the "
            "split the face decides is the difference between a 0.9525 cm "
            "minimum gutter and a 1.27 cm one"
        )

    def test_the_comparison_can_tell_the_pre_card_face_from_this_one(
        self, monkeypatch
    ) -> None:
        """The negative control for every claim above (CLAUDE.md).

        Restores the host lookup this card deleted — :func:`host_face`, the
        pre-CARD-221 ``_guide_face`` transcribed — and runs the same two
        exports against it. They must **disagree**, on this host, which is
        what proves the three tests above are comparing something: if the
        off-host simulation did not reach the interior's faces at all, or if
        the digests were taken of something that ignores lettering, this
        would pass just as green as they do.

        It is the defect itself, reproduced in one assertion: interior pages
        that are different pixels depending on the machine. The pages that
        move are the seven the card's own baseline records
        (``book_baseline_card221.json``'s ``changed_pages``) — both guide
        pages, the TOC and the four dividers.

        **The one host gate in this module**, and it is above every assertion
        rather than in the middle of them because the whole test is the
        contrast it names: on a machine with no host Arial — the deployment
        image, or this suite run under the card's own off-host plugin — the
        pre-card code resolves one face in both runs and there is nothing for
        it to measure. See :func:`host_offers_a_second_face`.
        """
        if not host_offers_a_second_face():
            pytest.skip(
                "this host has no Arial distinguishable from Pillow's own "
                "face, so the pre-card lookup cannot be shown to depend on "
                "the machine here; the claims this controls are themselves "
                "host-independent and run everywhere"
            )
        monkeypatch.setattr(book_pdf_generator, "_guide_face", host_face)
        on_host, off_host = _both_faces(
            lambda: _interior(corpus_book, baseline_puzzles())
        )
        host_digests, _, _ = on_host
        bare_digests, _, _ = off_host

        moved = [
            number
            for number, (with_host, without) in enumerate(
                zip(host_digests, bare_digests, strict=True), start=1
            )
            if with_host != without
        ]
        assert moved == [1, 2, 3, 4, 6, 8, 10], (
            "with the pre-card host lookup restored, the pages that differ "
            "between a host with Arial and one without must be exactly the "
            "seven that lettered through it — the two guide pages, the table "
            f"of contents and the four dividers — and these moved: {moved}. "
            "If none moved, this host's Arial and Pillow's own face are "
            "indistinguishable and the tests above prove nothing here"
        )


# --------------------------------------------------------------------------
# The two facts the fix rests on
# --------------------------------------------------------------------------


class TestInteriorFace_ThePackagedFaceCoversWhatTheInteriorPrints:
    """``_guide_face``'s docstring claims the packaged face needs no escape
    hatch. This is that claim, glyph by glyph.

    A face that lacks a character draws ``.notdef`` — an empty box — so a
    missing glyph would be a printed defect on a page nobody would think to
    re-measure. The one real risk is the non-ASCII punctuation the interior
    sets (:data:`NON_ASCII_INTERIOR_CHARACTERS`), which is why the band's own
    separator was the reason the packaged face was introduced in the first
    place (CARD-197: U+00B7 is not in Pillow's embedded ASCII face, and a
    band set in that printed a box between the number and the tier).
    """

    @staticmethod
    def _rendered(character: str, face: ImageFont.FreeTypeFont) -> bytes:
        image = Image.new("L", (120, 120), 255)
        ImageDraw.Draw(image).text((12, 12), character, fill=0, font=face)
        return image.tobytes()

    def test_every_character_the_interior_prints_has_a_glyph(self) -> None:
        face = packaged_face(type_px(10.0, BOOK_DPI))
        # U+E000 is the first Private Use codepoint: no real face assigns it,
        # so whatever it draws *is* this face's .notdef box.
        notdef = self._rendered("", face)
        blank = self._rendered(" ", face)
        assert notdef != blank, (
            "the probe is broken: this face draws nothing at all for an "
            "unassigned codepoint, so a missing glyph cannot be told from a "
            "space and this test has no instrument"
        )

        printable = "".join(chr(code) for code in range(0x20, 0x7F))
        missing = [
            character
            for character in printable + "".join(NON_ASCII_INTERIOR_CHARACTERS)
            if character != " " and self._rendered(character, face) == notdef
        ]
        assert missing == [], (
            "the packaged face draws a .notdef box for "
            f"{[hex(ord(character)) for character in missing]} — the "
            "interior would print an empty box there, and `_guide_face`'s "
            "own docstring claims it needs no fallback for any of them"
        )

    def test_the_recorded_repertoire_is_what_the_interior_draws(
        self, monkeypatch
    ) -> None:
        """:data:`NON_ASCII_INTERIOR_CHARACTERS` is read off a real export.

        Without this, the list above is a hopeful transcription: a card that
        introduces a fifth special character would add it to a page and not
        to this file, and the coverage test would keep passing while the page
        printed a box. So the export is walked, every character it draws is
        collected, and anything outside printable ASCII must be in the list.
        """
        drawn: List[str] = []
        original = ImageDraw.ImageDraw.text

        def spy(self, xy, text, fill=None, font=None, *args, **kwargs):
            drawn.append(str(text))
            return original(self, xy, text, fill, font, *args, **kwargs)

        monkeypatch.setattr(ImageDraw.ImageDraw, "text", spy)
        generator = BookPDFGenerator(corpus_book("card-221-repertoire"))
        for _page in generator.interior_stream(baseline_puzzles()).pages:
            pass
        monkeypatch.setattr(ImageDraw.ImageDraw, "text", original)

        assert drawn, "the interior drew no text at all"
        unexpected = {
            character
            for line in drawn
            for character in line
            if not 0x20 <= ord(character) < 0x7F
            and character not in NON_ASCII_INTERIOR_CHARACTERS
        }
        assert unexpected == set(), (
            "the interior prints "
            f"{[hex(ord(character)) for character in sorted(unexpected)]}, "
            "which NON_ASCII_INTERIOR_CHARACTERS does not list — add it "
            "there so the coverage test above actually covers it"
        )
        # Non-vacuity: the band's own separator really is on the page, so the
        # walk above is looking at lettering and not at an empty list.
        assert any(BAND_SEPARATOR in line for line in drawn), (
            "no band was drawn, so this walk saw none of the interior's own "
            "non-ASCII punctuation"
        )


class TestInteriorFace_TheOneHostGateDiscriminates:
    """The gate this card adds is itself tested, in both directions.

    ``host_offers_a_second_face`` decides whether the negative control
    above can run at all, and a gate that answers wrongly is the quietest
    failure in a suite: answer ``False`` on a host that *could* run the
    contrast and the control disappears with nothing red, which is the
    "dead weight that hides the next real gap" AC-6 is about. Its verdict
    on any particular machine is host-dependent by definition and cannot be
    asserted here — what can, and what these tests do, is pin the
    **logic**, on all three of its paths: refuse every host path and it
    must say no (the exception); hand it a face that draws the sample
    exactly as Pillow's own does and it must say no (the comparison, which
    is the only reason this function rasterises anything); hand it a face
    that genuinely differs and it must say yes. All three hold on every
    host.

    Added in review cycle 1's mutation round, which asked for a set aimed
    at this function: before it, mutating the gate to ``return False``
    survived the whole suite in silence. The comparison branch was added in
    cycle 2 (N-001), which found it the one path still uncovered — the
    exception path having been the only way the gate had ever been seen to
    close.
    """

    def test_it_says_no_when_the_host_offers_no_face_at_all(self, monkeypatch) -> None:
        """The deployed Linux image's own case."""
        refuse_host_fonts(monkeypatch)
        assert host_offers_a_second_face() is False, (
            "with every host font path refused there is no second face to "
            "contrast, and the gate must close"
        )

    def test_it_says_yes_when_the_host_offers_a_face_that_really_differs(
        self, monkeypatch
    ) -> None:
        """The owner's Mac's case, without depending on the owner's Mac.

        The host lookup is pointed at the packaged face instead of Arial —
        a real, loadable face that is demonstrably not Pillow's built-in
        one — so this holds on a machine with no Arial too.
        """
        original = ImageFont.truetype

        def truetype(font=None, *args, **kwargs):
            if isinstance(font, (str, bytes)):
                return packaged_face(*args, **kwargs) if args or kwargs else packaged_face(12)
            return original(font, *args, **kwargs)

        monkeypatch.setattr(ImageFont, "truetype", truetype)
        assert host_offers_a_second_face() is True, (
            "the stand-in host face is the packaged DejaVu Sans, which draws "
            "the sample differently from Pillow's own face — the gate must "
            "open, or the negative control it guards can never run anywhere"
        )

    def test_it_says_no_when_the_host_face_loads_but_is_indistinguishable(
        self, monkeypatch
    ) -> None:
        """The branch the pixel comparison exists for (review cycle 2, N-001).

        A host that *has* a font at the path but whose font draws the sample
        exactly as Pillow's own built-in face does — the metric-compatible
        clone case, which is not hypothetical: Pillow's embedded Aileron is
        a Helvetica clone and so is Arial, and this card's own cycle-0
        measurements found the two drawing the guide page identically line
        for line. The gate must close, and it must close **through the
        comparison**, not through the ``except OSError`` that
        ``test_it_says_no_when_the_host_offers_no_face_at_all`` already
        covers. That is the whole reason this function samples pixels
        instead of asking ``os.path.exists``, and nothing exercised it.

        The stand-in is Pillow's own face returned from the host lookup, so
        the two sides of the comparison are the same face by construction;
        the call is recorded so the test can show the lookup really
        succeeded and the exception path was never taken.
        """
        original = ImageFont.truetype
        loaded: List[int] = []

        def truetype(font=None, *args, **kwargs):
            if isinstance(font, (str, bytes)):
                size = args[0] if args else kwargs.get("size", 12)
                loaded.append(size)
                return ImageFont.load_default(size)
            return original(font, *args, **kwargs)

        monkeypatch.setattr(ImageFont, "truetype", truetype)
        verdict = host_offers_a_second_face()

        assert loaded, (
            "the host lookup never ran, so this test exercised the "
            "exception path rather than the comparison it is here for"
        )
        assert verdict is False, (
            "the host's face draws this sample exactly as Pillow's own does, "
            "so there is no contrast for the negative control to measure and "
            "the gate must close — a gate that opens here would run that "
            "control on a machine where it cannot possibly find a difference"
        )

    def test_the_two_faces_it_compares_really_do_draw_differently(self) -> None:
        """Non-vacuity, for the two tests above: the sample discriminates.

        The yes-test hands the gate the packaged face as its stand-in host
        face and expects ``True``; the indistinguishable-test hands it
        Pillow's own and expects ``False``. Both rest on the premise that
        those two faces really do draw this sample differently — so if they
        did not, the yes-test would **fail** and there would be no way to
        tell a broken gate from a premise that never held. This measures
        the premise, so that failure can only mean the gate.
        """
        size = type_px(22.0, BOOK_DPI)
        packaged = Image.new("L", (900, 120), 255)
        ImageDraw.Draw(packaged).text(
            (0, 0), "How to Solve Nonograms", fill=0, font=packaged_face(size)
        )
        builtin = Image.new("L", (900, 120), 255)
        ImageDraw.Draw(builtin).text(
            (0, 0), "How to Solve Nonograms", fill=0, font=ImageFont.load_default(size)
        )
        assert packaged.tobytes() != builtin.tobytes()


class TestInteriorFace_NoFaceIsReadFromAHostPath:
    """Every face the interior draws with comes from packaged data.

    The structural statement of this card, beside AC-1's behavioural one: not
    "the two runs happen to agree" but "there is no host lookup left to
    disagree about". Asserted by watching ``ImageFont.truetype``'s own
    argument through a whole interior export — a path (``str``) is a host
    lookup, a file object is package data.

    ``ImageFont.load_default`` is deliberately allowed: a puzzle page's clue
    digits are set in Pillow's own embedded face, which is a dependency's
    package data and not the machine's (every baseline fixture in the chain
    treats it as machine-independent, and INV-006's cell floor is why those
    digits are CON-020's one exemption).
    """

    @pytest.mark.parametrize(
        ("shape", "book_factory", "puzzles_for"),
        [
            ("book1", lambda: corpus_book("card-221-no-host-path"), baseline_puzzles),
            ("min-trim", _min_trim_book, lambda: [
                puzzle("card221-nohost-mintrim", 20, 20, 5, "easy", "Solo")
            ]),
            ("spilling-toc", lambda: corpus_book("card-221-no-host-path-150"), lambda: [
                puzzle(f"card221-nohost-{index}", 10, 10, 3, "easy", f"P{index}")
                for index in range(150)
            ]),
        ],
        ids=["book1", "min-trim", "150-puzzles"],
    )
    def test_no_font_is_loaded_from_a_filesystem_path(
        self, monkeypatch, shape, book_factory, puzzles_for
    ) -> None:
        """Swept over every book shape this module builds (review cycle 1,
        F-004).

        One shape was enough to state the claim and not enough to hold it: a
        host lookup reachable only from a page the baseline book does not
        draw — the min-trim guide page's own fallback ladder, a TOC long
        enough to split, a label long enough for ``_clipped_to``'s ellipsis
        — would have passed a watch over Book 1 alone. These are the three
        shapes the module already constructs two tests above, so the sweep
        costs three lines and one more export each.

        **The caches are cleared first, and that is what makes the sweep
        real** (AC/EC/G gate, F-G1). ``_band_font``/``_band_font_bytes`` are
        ``lru_cache``\ d, so by the time the second parametrization runs the
        faces this export needs are already loaded and the watch sees no
        ``truetype`` call at all: against a host lookup mutated back in, a
        cold process killed only the first case and running the file
        together let the mutant survive it entirely. A watch that cannot see
        the call it is watching for is worse than no watch.
        """
        clear_font_caches()
        original = ImageFont.truetype
        paths: List[str] = []

        def truetype(font=None, *args, **kwargs):
            if isinstance(font, (str, bytes)):
                paths.append(str(font))
            return original(font, *args, **kwargs)

        monkeypatch.setattr(ImageFont, "truetype", truetype)
        generator = BookPDFGenerator(book_factory())
        drawn = 0
        for _page in generator.interior_stream(puzzles_for()).pages:
            drawn += 1
        monkeypatch.setattr(ImageFont, "truetype", original)

        if shape == "book1":
            assert drawn == BASELINE_PAGE_COUNT, (
                f"the walk drew {drawn} pages, not the book's {BASELINE_PAGE_COUNT}"
            )
        else:
            assert drawn > 0, f"the {shape} walk drew no page at all"
        assert paths == [], (
            f"the {shape} interior asked the host for a font at {paths} — "
            "every face it letters in must come from "
            "src/nonogram/export/fonts/ or from Pillow's own embedded face"
        )

    def test_the_watch_would_have_caught_the_pre_card_lookup(
        self, monkeypatch
    ) -> None:
        """The negative control: the same watch, on the code this card replaced."""
        clear_font_caches()
        monkeypatch.setattr(book_pdf_generator, "_guide_face", host_face)
        original = ImageFont.truetype
        paths: List[str] = []

        def truetype(font=None, *args, **kwargs):
            if isinstance(font, (str, bytes)):
                paths.append(str(font))
            return original(font, *args, **kwargs)

        monkeypatch.setattr(ImageFont, "truetype", truetype)
        generator = BookPDFGenerator(corpus_book("card-221-host-path-control"))
        for _page in generator.interior_stream(baseline_puzzles()).pages:
            pass
        monkeypatch.setattr(ImageFont, "truetype", original)

        assert ARIAL_PATH in paths, (
            "with the pre-card `_guide_face` restored the export must be "
            f"seen asking for {ARIAL_PATH}; it asked for {sorted(set(paths))}"
        )
