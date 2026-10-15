"""The generated title cover letters from packaged data, at the size asked (CARD-234).

    AC-1  TestBookCover_IsIdenticalWithAndWithoutHostFonts
    AC-2  TestBookCover_TitleIsDrawnAtTheSizeAsked
    AC-3  TestBookCover_TitleStaysCentredAndInsideTheTrim
    AC-4  TestBookCover_UnletterableTitle
    AC-5  TestBookCover_EmptyTitle

Until this card ``BookPDFGenerator.create_cover_page`` read the **host's**
Arial from ``/System/Library/Fonts/Arial.ttf`` at 72 px and, on the
``OSError``, called ``ImageFont.load_default()`` **with no size** — five lines
carrying two defects that compounded. The path exists only on macOS, so the
deployed Linux panel took the fallback on every cover it generated; and a
sizeless ``load_default()`` silently drops the size it was asked for, so the
title came out in Pillow's small bitmap face. The title was still centred by
its own measured bbox, so nothing overflowed, nothing failed and nothing was
logged: the one page a buyer sees first simply printed at **a cap height of
8 px where the packaged face sets 52** — about a seventh of its intended
size. CARD-221 closed this class of defect for the interior and recorded the
cover as the one place its rule was still untrue.

**Every measurement here is taken off the rendered ink**, never off a font
object this module built. Asserting that ``_cover_title_face`` returns a face
whose ``size`` is 72 would have passed on the defect too — ``load_default()``
also answers questions about itself — so each claim below crops the drawn
cover and measures the pixels, and the pre-card expression is transcribed and
measured the same way as every claim's negative control. The face the
expected figures come from is loaded here from :mod:`importlib.resources`
directly (:func:`packaged_face`), an independent second implementation of the
page's own lookup rather than a call to it (CLAUDE.md's test style).

**The AC-4 decision, recorded.** A title the packaged face cannot letter is
**refused** with :class:`nonogram.errors.UnletterableTitle`, naming each
character and its codepoint — it is not substituted and not drawn as the
``.notdef`` boxes FreeType would otherwise print. A book title is typed by
the owner, so its repertoire is unbounded, unlike the interior's; the cover
is the file KDP prints, bills for and sells; and a substitution ships a title
that is not the title, quietly, which is the same defect this card exists to
kill wearing a different costume.
"""

from __future__ import annotations

import random
from importlib import resources
from io import BytesIO
from typing import Any, List, Optional, Tuple

import pytest
from PIL import Image, ImageDraw, ImageFont

from nonogram.admin import book_pdf_generator
from nonogram.admin.book_pdf_generator import COVER_TITLE_PX, BookPDFGenerator
from nonogram.errors import NonogramError, UnletterableTitle
from nonogram.export.pdf import FONT_PACKAGE, FONT_RESOURCE

# --------------------------------------------------------------------------
# What the card asks for, written out rather than imported
# --------------------------------------------------------------------------

#: The host path the cover asked Pillow for until this card.
ARIAL_PATH = "/System/Library/Fonts/Arial.ttf"

#: The 8.5 x 11 in Book 1 trim at 300 DPI — the sheet a book with no stored
#: print specification is laid out on, which is every book in this module.
TRIM_PX = (2550, 3300)

#: A title of this module's own, long enough to measure and short enough to
#: fit any trim here.
BOOK_TITLE = "Winter Pictures"

#: All-caps, no ascender above the cap line and no descender below the
#: baseline, so the ink's height **is** the face's cap height at the size it
#: was asked for — the one measurement AC-2 is about.
CAP_SAMPLE = "HAMBURGEFONS"

#: Characters the packaged DejaVu Sans has no glyph for, measured against the
#: shipped file rather than assumed (see
#: :meth:`TestBookCover_UnletterableTitle.test_the_probe_agrees_with_the_shipped_font`,
#: which re-derives this list independently). U+4E2D is a CJK ideograph,
#: U+E000 the first Private Use codepoint, U+0009 a tab — a copy-paste
#: artefact, and the one of the three a real title plausibly carries.
UNLETTERABLE = ("中", "", "\t")

#: Titles the owner actually types, Cyrillic included (the owner's own
#: language; the packaged face covers it, so these must **not** be refused —
#: a repertoire gate that rejected real work would be worse than the defect).
LETTERABLE_TITLES = (
    "Winter Pictures",
    "Large Print Nonogram Puzzles for Adults",
    "Nonograms, Volume 2: Easy & Medium",
    "Зимние картинки",
    "Picross für Anfänger — Band 3",
    "100 Puzzles (10x10 to 25x25)",
)


def packaged_face(size_px: int) -> ImageFont.FreeTypeFont:
    """The packaged face at ``size_px``, addressed as package data.

    The cover's own lookup, reimplemented rather than imported: CLAUDE.md
    prefers an independent second implementation to re-deriving a value with
    the function under test, and every expected figure below comes from here.
    """
    data = resources.files(FONT_PACKAGE).joinpath(FONT_RESOURCE).read_bytes()
    return ImageFont.truetype(BytesIO(data), size=size_px)


def precard_face(size_px: int) -> Any:
    """``create_cover_page``'s font lookup **as it stood before this card**.

    Transcribed from the five lines CARD-234 deleted, kept as every claim's
    negative control: the host's Arial by path, and on the ``OSError`` a
    ``load_default()`` called with no size at all. The missing size is the
    point — that is why a cover generated off a Mac came out tiny.
    """
    try:
        return ImageFont.truetype(ARIAL_PATH, size_px)
    except OSError:  # pragma: no cover - only on a machine without Arial
        return ImageFont.load_default()


def ink_box(image: Image.Image) -> Optional[Tuple[int, int, int, int]]:
    """The bounding box of everything drawn on a white page, or ``None``.

    ``Image.getbbox`` finds non-**zero** pixels, and a cover is black on
    white, so the page is inverted first; without that every cover would
    report its full extent and none of the measurements below would mean
    anything.
    """
    return image.convert("L").point(lambda value: 255 - value).getbbox()


def drawn_ink_box(text: str, face: Any) -> Optional[Tuple[int, int, int, int]]:
    """``text``'s ink box when drawn in ``face`` on a canvas of its own.

    The expected figures' side of every comparison, measured the same way as
    the cover's but on a page this module draws itself.

    The canvas is measured from the text rather than fixed, because a fixed
    one is a trap: a 288 px square clipped ``HAMBURGEFONS`` after its sixth
    letter, which dropped the only two round letters in it, and the round
    letters are precisely the ones that overshoot the cap line — so the
    "expected" cap height came out 2 px short of the cover's and the
    comparison failed on the measurement rather than on the cover.
    """
    margin = 2 * COVER_TITLE_PX
    width = int(ImageDraw.Draw(Image.new("L", (1, 1))).textlength(text, font=face))
    page = Image.new("L", (width + 2 * margin, 4 * COVER_TITLE_PX), 255)
    ImageDraw.Draw(page).text((margin, COVER_TITLE_PX), text, fill=0, font=face)
    return ink_box(page)


def cap_height(box: Optional[Tuple[int, int, int, int]]) -> int:
    """The height of an ink box, or 0 when nothing was drawn."""
    return 0 if box is None else box[3] - box[1]


def clear_font_caches() -> None:
    """Empty the module's two font caches.

    ``book_pdf_generator._band_font`` is an ``lru_cache(maxsize=8)`` over
    ``(size,)`` and ``_band_font_bytes`` an ``lru_cache(maxsize=1)``, and the
    cover's face now comes through both. Every comparison in this module runs
    two font configurations in one process, which is exactly the case a cache
    cannot tell apart — the same trap CARD-221's F-G1 found, where a cached
    Arial carried across the boundary and made all four of that card's AC-1
    comparisons green against the defect they were meant to catch. So the
    caches are emptied at each boundary rather than trusted.
    """
    book_pdf_generator._band_font.cache_clear()
    book_pdf_generator._band_font_bytes.cache_clear()


def refuse_host_fonts(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make every ``ImageFont.truetype`` call that names a *path* fail.

    The deployed Linux panel, simulated: there is no Arial at
    :data:`ARIAL_PATH` there, so that is the branch every cover it generated
    took. A file object is passed through untouched, which is how the
    packaged face is addressed (a ``BytesIO`` over
    :mod:`importlib.resources` bytes) — so this simulation leaves the fix
    itself alone, which is the only reason the comparisons below can mean
    anything. It clears the font caches on the way in; see
    :func:`clear_font_caches` for why that is load-bearing.
    """
    original = ImageFont.truetype

    def truetype(font=None, *args, **kwargs):
        if isinstance(font, (str, bytes)):
            raise OSError(f"this host has no font at {font!r}")
        return original(font, *args, **kwargs)

    monkeypatch.setattr(ImageFont, "truetype", truetype)
    clear_font_caches()


def both_hosts(measure) -> Tuple[Any, Any]:
    """``measure()`` with the host's fonts available, and again without them.

    It takes no ``monkeypatch`` fixture on purpose: the on-host half must run
    with **nothing** patched, so the only patch context is the one this
    function opens and closes around the off-host half. Two halves sharing
    one context is how a comparison like this quietly becomes
    self-fulfilling.
    """
    clear_font_caches()
    on_host = measure()
    with pytest.MonkeyPatch.context() as context:
        refuse_host_fonts(context)
        off_host = measure()
    clear_font_caches()
    return on_host, off_host


def cover(title: str = BOOK_TITLE) -> Image.Image:
    """The generated title cover for ``title`` on the Book 1 trim."""
    return BookPDFGenerator().create_cover_page(title)


# --------------------------------------------------------------------------
# AC-1 — the cover does not depend on the host's fonts
# --------------------------------------------------------------------------


class TestBookCover_IsIdenticalWithAndWithoutHostFonts:
    """AC-1 — the same title, drawn with and without the host's Arial, is the
    same cover: the same pixels and a cover file of the same size.
    """

    @pytest.mark.parametrize("title", LETTERABLE_TITLES)
    def test_the_generated_cover_is_the_same_pixels_on_both_hosts(self, title) -> None:
        on_host, off_host = both_hosts(lambda: cover(title).tobytes())

        assert on_host == off_host, (
            f"the cover for {title!r} is a different page when the host's "
            "fonts are refused — its title is still lettered off the machine"
        )

    def test_the_cover_file_is_the_same_size_on_both_hosts(self) -> None:
        """The file, not just the page: AC-1's own wording.

        Compared by length rather than byte for byte because Pillow stamps
        every PDF it writes with a ``CreationDate``, so two files written a
        moment apart differ in those bytes alone whatever they draw — the
        same reason ``tests/test_book_interior_face.py`` compares the
        interior's file by length.
        """
        on_host, off_host = both_hosts(
            lambda: len(BookPDFGenerator().export_cover(BOOK_TITLE).getvalue())
        )

        assert on_host == off_host, (
            f"the cover file is {on_host} bytes with the host's fonts and "
            f"{off_host} without them"
        )

    def test_refusing_the_hosts_fonts_would_have_changed_the_old_cover(self) -> None:
        """The negative control, and it needs no host gate to have teeth.

        What the off-host half of the comparison above draws is asserted to
        be **unlike** what the pre-card lookup drew there — the sizeless
        ``load_default()`` branch, which is the branch the deployed panel
        took on every cover it generated. So the two green halves above are
        evidence that the lookup changed, not two runs of one unchanged code
        path agreeing with itself.
        """
        with pytest.MonkeyPatch.context() as context:
            refuse_host_fonts(context)
            fixed = ink_box(cover())
            old = drawn_ink_box(BOOK_TITLE, precard_face(COVER_TITLE_PX))

        assert fixed is not None and old is not None
        assert cap_height(fixed) != cap_height(old), (
            "with the host's fonts refused, the cover's title is the same "
            "height as the pre-card fallback drew it — this module cannot "
            "tell the fix from the defect and proves nothing"
        )

    def test_the_comparison_is_two_measurements_and_not_one_cache(self) -> None:
        """:func:`both_hosts` really does reload the face in its second half.

        CARD-221's F-G1: with the face left in ``_band_font``'s LRU, the
        off-host half is served the face the on-host half loaded and the
        comparison compares one run with itself. This asserts the clearing
        happens, so a refactor that drops it reds here by name instead of
        turning every AC-1 claim above into a tautology.
        """
        clear_font_caches()
        cover()
        assert book_pdf_generator._band_font.cache_info().currsize > 0, (
            "the cover drew a title without putting a face in the cache, so "
            "this guard is watching the wrong cache"
        )

        both_hosts(lambda: None)

        assert book_pdf_generator._band_font.cache_info().currsize == 0, (
            "both_hosts left a face in the cache, so its two halves can be "
            "served the same font object"
        )


# --------------------------------------------------------------------------
# AC-2 — the title is drawn at the size the code asks for
# --------------------------------------------------------------------------


class TestBookCover_TitleIsDrawnAtTheSizeAsked:
    """AC-2 — the title's drawn cap height is the packaged face's cap height
    at :data:`COVER_TITLE_PX`, and not Pillow's default bitmap face's.

    Measured off the ink on the cover itself. Asking the returned font object
    what size it is would pass on the defect: the pre-card code asked for 72
    px and got a face that answered about itself perfectly well while
    lettering at a seventh of that.
    """

    def test_the_titles_cap_height_is_the_packaged_faces_at_that_size(self) -> None:
        drawn = ink_box(cover(CAP_SAMPLE))
        expected = drawn_ink_box(CAP_SAMPLE, packaged_face(COVER_TITLE_PX))

        assert drawn is not None, "the cover drew no title at all"
        assert cap_height(drawn) == cap_height(expected), (
            f"the cover sets {CAP_SAMPLE!r} at a cap height of "
            f"{cap_height(drawn)} px where the packaged face at "
            f"{COVER_TITLE_PX} px sets {cap_height(expected)} px"
        )

    def test_the_size_asked_for_is_still_the_seventy_two_px_the_card_names(self) -> None:
        """The size itself, pinned, because every other claim scales with it.

        AC-2 compares the drawn cap height against the packaged face at
        :data:`COVER_TITLE_PX`, so both sides move together if that constant
        moves and the comparison would stay green at any size at all. 72 px
        is the number the pre-card code asked for and the number this card
        kept; changing it is the cover's visual design (G-5) and should red
        here so it is a decision rather than a drift.
        """
        assert COVER_TITLE_PX == 72

    def test_the_cap_height_is_a_real_fraction_of_the_em_it_asked_for(self) -> None:
        """The figure itself, so a face swap cannot quietly shrink the title.

        A 72 px em sets a 52 px cap in this face. Stated as a floor of 60%
        of the em rather than as the exact 52 px, because the exact pixel is
        the installed FreeType's business (CARD-221's F-005) while "a cap
        height is most of its em" is the face's — and 60% of the em is far
        above anything Pillow's default bitmap face can reach, which is the
        discrimination this test exists for.
        """
        measured = cap_height(ink_box(cover(CAP_SAMPLE)))

        assert measured >= 0.6 * COVER_TITLE_PX, (
            f"the title's cap height is {measured} px under a "
            f"{COVER_TITLE_PX} px request — the size is being dropped again"
        )

    def test_the_old_sizeless_fallback_was_about_a_seventh_of_this(self) -> None:
        """The defect, measured, as the card asked it to be stated.

        The pre-card off-host branch drew the title in a sizeless
        ``load_default()``. This pins how far apart the two are, so the test
        above is known to be discriminating and not merely satisfied.
        """
        fixed = cap_height(ink_box(cover(CAP_SAMPLE)))
        old = cap_height(drawn_ink_box(CAP_SAMPLE, ImageFont.load_default()))

        assert 0 < old < fixed / 5, (
            "the sizeless default face is not the small face this card says "
            f"it is: it sets {CAP_SAMPLE!r} at {old} px against the "
            f"packaged face's {fixed} px"
        )


# --------------------------------------------------------------------------
# AC-3 — the title is still centred, and still inside the trim
# --------------------------------------------------------------------------

#: How far the drawn **ink** may sit off the page's horizontal centre. The
#: page centres the title by its text bbox, which carries the first and last
#: glyph's side bearings and is halved with ``//``, so the ink itself lands a
#: bearing or so off centre. Measured across the corpus below: the worst case
#: is 13 px on a 2550 px page (0.5%), so a quarter of the em is a bound that
#: holds with room and still catches a title drawn from the page's edge.
CENTRE_TOLERANCE_PX = COVER_TITLE_PX // 4

#: How far the ink may sit off the page's vertical centre. Looser, and for a
#: reason that is not this card's to change (G-5): the page anchors the text
#: box's top, so where the ink starts depends on the title's own ascenders
#: and descenders. Worst case across the corpus is 28 px on a 3300 px page.
#: One em bounds it; moving the anchor to the ink would be cover design.
VERTICAL_TOLERANCE_PX = COVER_TITLE_PX

#: How many titles AC-3's corpus must hold, asserted inside the test so the
#: corpus cannot silently shrink (CLAUDE.md's test style: stdlib
#: ``random.Random``, no hypothesis).
TITLE_CORPUS_MINIMUM = 60

_TITLE_WORDS = (
    "Winter",
    "Pictures",
    "Nonogram",
    "Puzzles",
    "for",
    "Adults",
    "Large",
    "Print",
    "Volume",
    "Logic",
    "Grid",
    "Book",
    "100",
    "Easy",
    "Hard",
    "Picross",
    "Japanese",
    "Crosswords",
    "Brain",
    "Games",
    "Seniors",
    "Kids",
    "II",
    "Collection",
)


def title_corpus() -> List[str]:
    """A seeded corpus of book titles of very different lengths.

    Built word by word with ``random.Random(234)`` — stdlib, seeded, so the
    same titles are measured on every run and a failure names a title that
    can be reproduced. The lengths it spans are asserted by the test itself
    rather than hoped for, and so is the premise that every one of them fits
    the trim: a corpus that drifted into titles too wide for the page would
    otherwise turn AC-3's overflow claim into a measurement of nothing.
    """
    rng = random.Random(234)
    return [
        " ".join(rng.choice(_TITLE_WORDS) for _ in range(rng.randint(1, 6)))
        for _ in range(TITLE_CORPUS_MINIMUM + 20)
    ]


class TestBookCover_TitleStaysCentredAndInsideTheTrim:
    """AC-3 — titles of very different lengths are each centred on the page,
    and none of them runs off the trim.

    Overflow is checked against an **independently measured** advance width,
    not against the ink box: a title wider than the page is clipped by the
    canvas, so its ink box reports an edge that is inside the page while half
    the lettering is off it. The width comes from this module's own packaged
    face; the position comes from the drawn cover.
    """

    def test_every_title_in_the_corpus_is_centred_and_fits(self) -> None:
        titles = title_corpus()
        page = BookPDFGenerator()
        width, height = page.page_width_px, page.page_height_px
        measure = ImageDraw.Draw(Image.new("L", (1, 1)))
        face = packaged_face(COVER_TITLE_PX)

        assert len(titles) >= TITLE_CORPUS_MINIMUM, (
            f"AC-3's corpus is down to {len(titles)} titles, below the "
            f"{TITLE_CORPUS_MINIMUM} this test requires"
        )
        lengths = [len(title) for title in titles]
        assert min(lengths) <= 8 and max(lengths) >= 40, (
            "the corpus no longer spans 'very different lengths': it runs "
            f"{min(lengths)}..{max(lengths)} characters"
        )

        for title in titles:
            advance = measure.textlength(title, font=face)
            assert advance <= width, (
                f"the corpus has drifted: {title!r} is {advance} px wide on "
                f"a {width} px page, so this case measures clipping and not "
                "centring"
            )

            box = ink_box(page.create_cover_page(title))
            assert box is not None, f"no title was drawn for {title!r}"
            left, top, right, bottom = box

            assert abs(left - (width - right)) <= CENTRE_TOLERANCE_PX, (
                f"{title!r} is not centred: {left} px of page to its left "
                f"and {width - right} px to its right"
            )
            assert abs(top - (height - bottom)) <= VERTICAL_TOLERANCE_PX, (
                f"{title!r} sits {top} px from the top and "
                f"{height - bottom} px from the bottom"
            )
            assert 0 < left and right < width, (
                f"{title!r} reaches the trim edge ({box}) on a "
                f"{width} px page"
            )
            assert 0 < top and bottom < height, (
                f"{title!r} reaches the trim's top or bottom edge ({box})"
            )

    def test_the_longest_title_the_trim_holds_is_measured_and_not_assumed(self) -> None:
        """What "fits" means on this sheet, in characters, measured.

        AC-3's corpus is built to fit; this says where fitting stops, so the
        figure is in the suite rather than in a reviewer's head. Making a
        **wider** title fit — shrinking it, or breaking it over two lines —
        is the cover's visual design and is out of this card's scope (G-5):
        the pre-card code centred an over-wide title off the page edge and
        this card leaves that exactly as it found it. Recorded in CARD-234's
        Worktree notes for whoever picks the cover's design up.
        """
        page = BookPDFGenerator()
        measure = ImageDraw.Draw(Image.new("L", (1, 1)))
        face = packaged_face(COVER_TITLE_PX)
        line = (
            "Large Print Nonogram Logic Picture Puzzles for Adults and "
            "Seniors, Volume Two"
        )

        fits = max(
            length
            for length in range(1, len(line) + 1)
            if measure.textlength(line[:length], font=face) <= page.page_width_px
        )

        assert 55 <= fits <= 85, (
            f"a {page.page_width_px} px page holds {fits} characters of a "
            f"mixed-case title at {COVER_TITLE_PX} px — far from the 69 "
            "measured when this card was written, so the cover's type or "
            "its trim has moved and AC-3's corpus needs re-measuring"
        )
        assert measure.textlength(line, font=face) > page.page_width_px, (
            "the title chosen to demonstrate the limit now fits inside it"
        )


# --------------------------------------------------------------------------
# AC-4 — a title the packaged face cannot letter
# --------------------------------------------------------------------------


class TestBookCover_UnletterableTitle:
    """AC-4 — a title holding a character the packaged face has no glyph for
    is **refused**, by name, with a :class:`nonogram.errors.NonogramError`.

    The decision this card was asked to make and state. The interior's
    repertoire is bounded and covered glyph by glyph (CARD-221); a book title
    is typed by the owner, so its repertoire is not, and FreeType draws a
    ``.notdef`` box for anything the face lacks. Printing that on the cover
    file KDP prints and sells is the same silent defect this card removed,
    wearing a different costume — and so is substituting ``?`` or ``U+FFFD``,
    which ships a title that is not the title. So the characters are named
    and the owner retypes them.
    """

    @pytest.mark.parametrize("character", UNLETTERABLE)
    def test_a_title_the_face_cannot_letter_is_refused_by_name(self, character) -> None:
        with pytest.raises(UnletterableTitle) as refusal:
            cover(f"Winter {character} Pictures")

        message = str(refusal.value)
        assert repr(character) in message, (
            f"the refusal does not name the character at fault: {message}"
        )
        assert f"U+{ord(character):04X}" in message, (
            f"the refusal does not name the codepoint at fault: {message}"
        )

    def test_the_refusal_is_a_domain_error_and_not_a_bare_exception(self) -> None:
        """CLAUDE.md: every domain error funnels through ``NonogramError``."""
        with pytest.raises(NonogramError):
            cover("Winter 中")

    def test_it_refuses_instead_of_drawing_a_tiny_or_boxed_title(self) -> None:
        """AC-4's "and it is **not** a silent tiny-type fallback".

        The refusal is what makes this different from the defect: no cover
        comes back at all, so there is nothing drawn to inspect — and the
        same title drawn in the face anyway is shown to be the row of
        ``.notdef`` boxes that would have been printed.
        """
        title = "Winter 中"
        with pytest.raises(UnletterableTitle):
            cover(title)

        face = packaged_face(COVER_TITLE_PX)
        assert drawn_ink_box("中", face) == drawn_ink_box("", face), (
            "U+4E2D no longer draws this face's .notdef box, so this card's "
            "whole premise about it has changed"
        )

    @pytest.mark.parametrize("title", LETTERABLE_TITLES)
    def test_the_titles_the_owner_types_are_not_refused(self, title) -> None:
        """The gate must not reject real work — Cyrillic especially.

        A repertoire check that refused the owner's own language would be a
        worse defect than the one this card fixes. The packaged DejaVu Sans
        covers Latin, Latin Extended, Cyrillic, Greek and a title's
        punctuation, and this is that claim on titles rather than on a
        codepoint table.
        """
        assert ink_box(cover(title)) is not None, (
            f"{title!r} was accepted and then drew nothing"
        )

    def test_the_probe_agrees_with_the_shipped_font(self) -> None:
        """:data:`UNLETTERABLE` is read off the font, not transcribed.

        Each character this module calls unletterable draws the shipped
        face's own ``.notdef``, and each character of a letterable title does
        not — derived here from the font file rather than from
        ``_cover_title_face``, so the two implementations have to agree.
        """
        face = packaged_face(COVER_TITLE_PX)
        notdef = drawn_ink_box("", face)

        for character in UNLETTERABLE:
            assert drawn_ink_box(character, face) == notdef, (
                f"U+{ord(character):04X} has a glyph in the shipped face "
                "after all, so UNLETTERABLE is wrong about it"
            )
        for character in set("".join(LETTERABLE_TITLES)) - {" "}:
            assert drawn_ink_box(character, face) != notdef, (
                f"the shipped face has no glyph for U+{ord(character):04X}, "
                "which one of LETTERABLE_TITLES carries"
            )

    def test_the_repertoire_the_docstring_claims_is_the_shipped_faces(self) -> None:
        """``_cover_title_face``'s docstring names what the face does and does
        not cover. This is that sentence, measured against the shipped file.

        It matters because the sentence is what tells the owner whether a
        refusal is a bug or a title to retype: the face sets the Latin
        scripts, Cyrillic, Greek, Hebrew and Arabic, and it does not set CJK,
        kana, hangul, Thai or most emoji.
        """
        face = packaged_face(COVER_TITLE_PX)
        notdef = drawn_ink_box("\ue000", face)
        covered = {
            "Latin Extended": "\u0153",
            "Cyrillic": "\u0416",
            "Greek": "\u03b4",
            "Hebrew": "\u05d0",
            "Arabic": "\u0627",
            "a title's punctuation": "\u2014",
        }
        absent = {
            "CJK": "\u4e2d",
            "kana": "\u3042",
            "hangul": "\ud55c",
            "Thai": "\u0e01",
            "an emoji": "\U0001f642",
        }

        for script, character in covered.items():
            assert drawn_ink_box(character, face) != notdef, (
                f"the shipped face has no glyph for {script} "
                f"(U+{ord(character):04X}), which the docstring says it sets"
            )
        for script, character in absent.items():
            assert drawn_ink_box(character, face) == notdef, (
                f"the shipped face now sets {script} "
                f"(U+{ord(character):04X}), so the docstring's list of what "
                "it cannot letter is out of date"
            )

    def test_the_glyph_probe_can_tell_a_missing_glyph_from_a_blank_one(self) -> None:
        """The instrument ``_cover_title_face`` relies on, in both directions.

        A face that drew *nothing* for an unassigned codepoint would make a
        missing glyph indistinguishable from a space, and the gate would pass
        everything in silence — the quietest way for this card's fix to stop
        working. The shipped face draws a box, and a space is blank.
        """
        face = packaged_face(COVER_TITLE_PX)
        notdef = drawn_ink_box("", face)

        assert notdef is not None, (
            "the shipped face draws nothing at all for an unassigned "
            "codepoint, so a missing glyph cannot be told from a space and "
            "`_cover_title_face` has no instrument"
        )
        assert drawn_ink_box(" ", face) is None, (
            "a space inks the page in this face, so the gate would refuse "
            "every title with a space in it"
        )

    def test_an_unletterable_title_cannot_spoil_an_uploaded_cover(self) -> None:
        """AC-6's half of this claim: the uploaded path never looks at the title."""
        art = Image.new("RGB", (600, 800), (12, 34, 56))
        page = BookPDFGenerator().create_cover_page("Winter 中", art)

        assert page.size == TRIM_PX
        assert page.getpixel((TRIM_PX[0] // 2, TRIM_PX[1] // 2)) == (12, 34, 56)


# --------------------------------------------------------------------------
# AC-5 — an empty or whitespace-only title
# --------------------------------------------------------------------------


class TestBookCover_EmptyTitle:
    """AC-5 — a title with nothing in it draws the blank page it is: no
    crash, and no stray artefact centred on an otherwise empty cover.
    """

    @pytest.mark.parametrize("title", ["", " ", "   ", "\t", "\n", " \t\n "])
    def test_a_blank_title_draws_a_blank_cover(self, title) -> None:
        page = cover(title)

        assert page.size == TRIM_PX
        assert ink_box(page) is None, (
            f"the cover for {title!r} has something drawn on it at "
            f"{ink_box(page)}"
        )

    def test_a_lone_tab_would_otherwise_have_printed_a_box(self) -> None:
        """The guard is load-bearing, and this is the measurement that says so.

        U+0009 has no glyph of its own, so a face asked to draw it draws
        ``.notdef`` — a box, centred on an otherwise empty cover, which is
        exactly the "stray centred artefact" AC-5 names. A title of nothing
        but whitespace is therefore returned before any face is asked for.
        """
        face = packaged_face(COVER_TITLE_PX)

        assert drawn_ink_box("\t", face) == drawn_ink_box("", face), (
            "a tab no longer draws this face's .notdef box, so AC-5's guard "
            "is protecting against something that has changed"
        )

    def test_a_blank_title_still_writes_a_one_page_cover_file(self) -> None:
        """The blank cover is a cover: it still exports as one trim page."""
        written = BookPDFGenerator().export_cover("   ").getvalue()

        assert written.startswith(b"%PDF")
        assert len(written) > 0
