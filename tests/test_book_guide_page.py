"""The guide's page-count arithmetic, parity and worked-example narrative
(CARD-167, CARD-201; what survives CARD-229's retirement of the raster guide).

FR-041 (amended 2026-10-04), AC-324..AC-326 (CARD-167), CARD-201's card-level
AC-1, AC-3, AC-5 and AC-8. **CARD-229 retired the raster guide-page group of
this module** (G-6): the guide is a vector spread now, and every test that
measured the bitmap ``create_guide_page`` draws, by template-matching its
glyphs and diagrams, or by calling the raster painters, went with it; the
vector spread's claims are held in ``tests/test_book_guide_page_vector.py``
(the retirement table, each id with its named survivor, is in CARD-229's
Worktree notes). What stays is what never read that bitmap:

* the page-count arithmetic of the guide's two pages
  (``interior_page_count``), and the exported file's page count;
* the parity of every puzzle and answer drawing in an unequal-margin book,
  read off the rendered interior;
* the worked example's narrative, which is data (the line ``3 1`` on six
  squares), and the brute-force check that "keep what every arrangement
  agrees on" shows every legal placement of its own line.
"""

from __future__ import annotations

import dataclasses
import itertools
from typing import Dict, List, Tuple

import pytest
from PIL import Image

from nonogram.admin.book_pdf_generator import (
    GUIDE_TECHNIQUES_2,
    BookPDFGenerator,
    interior_page_count,
)
from tests.helpers.book_corpus import GUIDE_INTERIOR_PAGES, corpus_book, export_of, puzzle
from tests.helpers.page_ink import Drawing, drawing_of, frame_centre_of, ink_mask
from tests.helpers.pdf_pages import pdf_page_count, pdf_pages

#: The worked example's line: the clue 3 1 on six squares.
CLUE = (3, 1)
LENGTH = 6

#: The resolution a book page is drawn at.
BOOK_DPI = 300


def placements() -> List[Tuple[bool, ...]]:
    """Every line of :data:`LENGTH` squares whose runs are :data:`CLUE`."""
    found = []
    for line in itertools.product((False, True), repeat=LENGTH):
        runs = tuple(len(list(group)) for filled, group in itertools.groupby(line) if filled)
        if runs == CLUE:
            found.append(line)
    return found




def old_style_total(puzzle_count: int, dividers: int = None, pages: int = None, answers: int = None) -> int:
    """``interior_page_count``'s own formula with the pre-CARD-201 leading
    term (1 guide page, not 2) and **no front matter in front of it** —
    written out as the independent "before"
    this AC's "+1" claim is checked against, not derived from the function
    under test.

    CARD-206's blank title page is a separate ``+ 1`` at each call site, the
    same way CARD-200's table of contents already is: this helper is the
    pre-CARD-201 baseline and stays that, so each later front-matter card's
    own term stays visible as its own term.
    """
    d = min(3, puzzle_count) if dividers is None else dividers
    p = puzzle_count if pages is None else pages
    a = puzzle_count if answers is None else answers
    return 1 + d + p + (a + 1 if puzzle_count else 0)


class TestGuidePage_IsTwoPages:
    """AC-1 — the guide is exactly 2 pages, right before the first puzzle/divider page."""

    @pytest.mark.parametrize(
        ("count", "dividers", "pages", "answers"),
        [
            (0, None, None, None),
            (1, None, None, None),
            (6, None, None, None),
            (150, None, None, None),
            (6, 2, 4, 6),
            (0, 0, 0, 0),
        ],
    )
    def test_interior_page_count_adds_exactly_one_guide_page(self, count, dividers, pages, answers):
        # CARD-200 (SCOPE+): `toc_pages=0` isolates this AC's own "+1 guide
        # page" claim from the table of contents' own term, added to the
        # same formula by a later card — this test is about the guide's
        # delta alone, not the TOC's.
        # The second `+ 1` is CARD-206's blank title page — this AC's claim
        # is the guide's own "+1", so the title page's term is written beside
        # it rather than folded into `old_style_total`.
        assert interior_page_count(
            count, pages, answers, dividers, toc_pages=0
        ) == old_style_total(count, dividers, pages, answers) + 1 + 1


class TestGuidePage_PageTwoCarriesTheHarderTechniquesAndDifficultyLegend:
    """AC-3's one data claim: the arrangement comparison is verified.

    The class carried the raster page's diagram, pipeline and legend checks
    until CARD-229; what is left is the brute-force check of the
    ``GUIDE_TECHNIQUES_2`` constant itself, which reads no page.
    """

    def test_the_arrangement_comparison_is_verified_against_every_legal_placement(self):
        """Review cycle 1, F-1 (gating): brute-force, independent of
        ``GUIDE_TECHNIQUES_2``, that cell 2 really is filled in every legal
        placement of a run of 3 on a 5-cell line, and is the ONLY such cell —
        so the "certain" conclusion the comparison row draws is mathematically
        correct, not just plausible-looking. This recomputes placements from
        scratch (a plain loop over every start) rather than reading the
        constant under test, so a future edit that reintroduces an
        unverified placement/conclusion mismatch is caught here.
        """
        clue_length, line_length = 3, 5
        legal_starts = range(0, line_length - clue_length + 1)
        placements = [frozenset(range(start, start + clue_length)) for start in legal_starts]
        assert len(placements) == 3, "the worked example claims to show every legal placement"

        agreed_filled = frozenset.intersection(*placements)
        agreed_empty = frozenset(range(line_length)) - frozenset.union(*placements)
        assert agreed_filled == frozenset({2})
        assert agreed_empty == frozenset()

        # And the technique's own rows, read from the module, match exactly.
        technique = next(t for t in GUIDE_TECHNIQUES_2 if t.heading.startswith("2."))
        assert technique.clue == (3,)
        assert technique.length == line_length
        shown = [row.filled for row in technique.rows[:-1]]
        assert set(shown) == set(placements)
        assert technique.rows[-1].filled == agreed_filled


class TestGuidePage_ExtraPageShiftsEverythingByOneKeepingParity:
    """AC-5 — SOLUTIONS and the answer pages move one page later; every
    page's parity still equals its own 1-based position (FR-043/INV-013).

    The byte-identity half of this claim — every page from the first
    puzzle/divider page onward carries the *same content*, only shifted — is
    AC-6's own, much stronger, test
    (``TestBookPdfMemory_EveryPageAfterTheGuideIsByteIdenticalShiftedByOne``
    in ``tests/test_book_pdf_memory.py``). This class checks the page count
    and parity claims directly instead of re-deriving that proof.
    """

    @staticmethod
    @pytest.fixture(scope="class")
    def corpus() -> List[Dict[str, object]]:
        """3 easy, 2 medium, 1 hard — the AC's own example book.

        Sized 20 cells and up and no two the same within a tier: small
        enough to stay comfortably inside every stored trim, but too wide
        for two to share a two-up page (FR-040) — this test wants exactly
        6 puzzle pages (one per puzzle), not a pairing saving.
        """
        return (
            [puzzle(f"card201-ac5-easy-{n}", 20 + n, 20 + n, 3, "easy", f"Easy {n}") for n in range(3)]
            + [puzzle(f"card201-ac5-medium-{n}", 25 + n, 25 + n, 4, "medium", f"Medium {n}") for n in range(2)]
            + [puzzle("card201-ac5-hard-0", 30, 30, 5, "hard", "Hard 0")]
        )

    @staticmethod
    @pytest.fixture(scope="class")
    def export(corpus) -> bytes:
        return export_of(BookPDFGenerator(corpus_book("card-201-ac5")), corpus)

    def test_the_page_count_is_exactly_one_more_than_before_this_card(self, export, corpus):
        # 3 tiers, each non-empty: 3 dividers. 6 puzzles, none pairable
        # across tiers or at these sizes: 6 puzzle pages, 6 answer pages.
        # CARD-200 (SCOPE+): this book's 6-entry TOC is one more page on
        # Book 1's own trim (`corpus_book`) — named explicitly here so the
        # guide's own "+1" claim stays isolated from the TOC's own term,
        # the same discipline `test_interior_page_count_adds_exactly_one_guide_page`
        # above now uses.
        assert (
            pdf_page_count(export)
            # the guide's second page (CARD-201), the table of contents
            # (CARD-200) and the blank title page (CARD-206) — one term each.
            == old_style_total(6, dividers=3, pages=6, answers=6) + 1 + 1 + 1
        )
        assert pdf_page_count(export) == interior_page_count(6, 6, 6, 3)

    #: An **unequal**-margin book, for the one test below whose subject is the
    #: mirroring itself. On CON-018 as amended 2026-10-17 the gutter and the
    #: outside margin are both 0.5 in, so a drawing centred in the usable area
    #: (CARD-224) is centred on the *trim* as well, on both parities, and a
    #: page's side of the spread leaves no trace in its drawing's own x at all
    #: — the identity the registry's note on EC-032 warns a reviewer not to
    #: read as evidence. A 20 mm gutter against a 10 mm outside margin puts an
    #: odd page's drawing 5 mm (59 px) right of the trim's middle and an even
    #: page's the same distance left of it.
    MIRROR_GUTTER_MM = 20.0
    MIRROR_OUTSIDE_MM = 10.0

    @pytest.fixture(scope="class")
    def mirrored_pages(self, corpus) -> List[Image.Image]:
        book = dataclasses.replace(
            corpus_book("card-201-ac5-mirrored"),
            gutter_margin_cm=f"{self.MIRROR_GUTTER_MM / 10:.2f}",
            outside_margin_cm=f"{self.MIRROR_OUTSIDE_MM / 10:.2f}",
        )
        return pdf_pages(export_of(BookPDFGenerator(book), corpus))

    def test_every_pages_parity_still_equals_its_own_position(self, mirrored_pages):
        """A right-hand (odd) page's drawing sits right of the trim's middle,
        a left-hand (even) one left of it — read off puzzle AND answer pages
        alike, since CARD-198 both carry the same 20x20-style drawing shape
        this corpus's puzzles give.

        **What the sign is, and which book it is measured on.** Originally
        half the gutter/outside difference: the drawing was centred across the
        usable area, so an odd page's own centre sat that far right of the
        trim's. CARD-204 made the drawing flush with the *outer* margin and
        the offset became half the drawing's own spare, signed by parity;
        CARD-224 reverses that, so the original formula — half the margin
        difference, independent of the puzzle — is the rule again. But the
        2026-10-17 amendment made Book 1's two side margins **equal**, which
        makes that difference zero: on ``corpus_book``'s own profile a centred
        drawing is centred on the trim too, at either parity, and this test
        would have nothing to measure (measured: all 17 pages read an offset
        of 0 px). It is therefore stated on a book storing unequal margins
        (:attr:`MIRROR_GUTTER_MM`), which is the only configuration in which
        mirroring is observable at all — the owner's decision of 2026-10-17
        was to record that, not to restore the asymmetry by changing a margin.

        **A page whose drawing fills the text width has no spare**, and is
        still asserted here: under centring the offset is the margin
        difference's half whatever the drawing's own width, so a width-bound
        page mirrors exactly like any other. Only a page carrying no
        measurable drawing at all (a divider, the TOC) is skipped.
        """
        px_per_mm = BOOK_DPI / 25.4
        expected_offset = (
            (self.MIRROR_GUTTER_MM - self.MIRROR_OUTSIDE_MM) / 2 * px_per_mm
        )
        checked = 0
        for number, page in enumerate(mirrored_pages, start=1):
            if number in GUIDE_INTERIOR_PAGES:
                # A guide page is not a puzzle page, and its own diagrams
                # (the worked example, the pipeline's boxes) are ruled: a
                # PDF rasteriser's strokes of them read as a "drawing" where
                # the bitmap's do not, and the offset of that is not a puzzle
                # drawing's (CARD-343: page 3 read 160.5 px). They were
                # skipped here through ``drawing_of``'s ValueError in the
                # bitmap medium; they are now skipped for what they are, in
                # either. Every other page is read exactly as before, and
                # ``checked`` below still floors how many.
                continue
            try:
                drawing = drawing_of(page)
            except ValueError:
                continue
            offset = drawing_centre_x(page, drawing) - page.width / 2
            assert (offset > 0) == (number % 2 == 1), (
                f"interior page {number} is centred {offset:.1f} px off the "
                f"middle, the wrong side for {'an odd' if number % 2 else 'an even'} page"
            )
            # Centring makes the magnitude the margin difference's own half,
            # the same on every page whatever its puzzle (EC-032).
            assert abs(abs(offset) - expected_offset) <= 2, (number, offset)
            checked += 1
        # Every page carrying a drawing is now asserted, none skipped for
        # being width-bound (centring makes the offset independent of the
        # drawing's own width). Measured on this corpus: 12 of its 17 pages.
        # ``checked >= 12`` has zero slack in both media: 12 unlifted, and 12
        # probed (13 drawings read, minus page 3, a guide page skipped by name).
        assert checked >= 12, f"only {checked} pages carried a measurable drawing"


def drawing_centre_x(page: Image.Image, drawing: Drawing) -> float:
    """The middle of a framed drawing's two vertical **boundaries**, in pixels.

    ``Drawing.left`` and ``Drawing.grid_right`` are ink extents, and a PDF
    rasteriser's frame corner is mitred further out than the bitmap's.
    Measured on this test's book (CARD-343), ``left`` minus ``frame_left`` is
    -0.5 px raster and -2.5 px vector, a 2.0 px difference between media, and
    ``(left + grid_right) / 2`` reads about 2.0 px further left on the
    operators page than on the bitmap for the very same placement: 2.94 px
    against this test's 2 px bound in the vector medium and 0.94 in the raster
    one. Both ends are therefore read as the
    boundary their rule is centred on: the left from the frame's own side
    (``frame_centre_of``), the right from the width of the border's own run,
    so the reading is the same in either medium and the bound is unchanged.
    """
    left = frame_centre_of(page, drawing).frame_left
    band = ink_mask(page)[drawing.grid_top + 5 : drawing.grid_bottom - 4]
    full = band.all(axis=0)
    width = 0
    while drawing.grid_right + width < full.size and full[drawing.grid_right + width]:
        width += 1
    assert drawing.grid_right + width < full.size, "the grid's right border runs to the page edge"
    assert width, "the grid's right border is not a full-height rule here"
    right = drawing.grid_right + (width - 1) / 2
    return (left + right) / 2


#: The worked example's 4 steps (CARD-167's own authored narrative, G-1:
#: unchanged by this card), written out as (filled, crossed) pairs. Step 2's
#: exact cells withhold one already-implied fact for step 4 (a pedagogical
#: choice, not something :func:`placements` alone determines), so these are
#: transcribed rather than derived.
WORKED_EXAMPLE_FILLS: Tuple[Tuple[frozenset, frozenset], ...] = (
    (frozenset(), frozenset()),
    (frozenset({1, 2}), frozenset()),
    (frozenset({1, 2, 3}), frozenset({0, 4})),
    (frozenset({1, 2, 3, 5}), frozenset({0, 4})),
)


class TestGuideHelpers_GeneralisedSignatureReproducesTheOriginalWorkedExample:
    """AC-8 — the worked example's narrative is still a solution (G-1).

    The two pixel-identity cells that stood beside this one compared the
    raster painters with a raster page; CARD-229 retired them with the raster
    guide (G-6), and the vector page's own worked example is held by
    ``TestGuideSpread_TextComesFromTheConstants`` and
    ``TestGuidePage_WorkedExampleReusesTheGridRoutine``.
    """

    def test_the_four_steps_solve_the_line_from_the_clue_to_the_finished_line(self):
        """The narrative itself still holds (G-1): unchanged content, not
        just unchanged pixels — monotonic progress, ending on a real solution.
        """
        solutions = placements()
        assert len(solutions) == 3, "3 1 fits a row of 6 in three ways"
        steps = [frozenset(filled) for filled, _ in WORKED_EXAMPLE_FILLS]
        assert steps[0] == frozenset()
        every = frozenset(i for i in range(LENGTH) if all(line[i] for line in solutions))
        assert steps[1] == every
        for earlier, later in zip(steps, steps[1:]):
            assert earlier <= later
        finished = tuple(i in steps[-1] for i in range(LENGTH))
        assert finished in solutions
        crossed_at_3 = WORKED_EXAMPLE_FILLS[2][1]
        remaining = [line for line in solutions if not any(line[i] for i in crossed_at_3)]
        assert remaining == [finished]
