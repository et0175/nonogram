"""The guide's page-count arithmetic and worked-example narrative
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
* the worked example's narrative, which is data (the line ``3 1`` on six
  squares), and the brute-force check that "keep what every arrangement
  agrees on" shows every legal placement of its own line.
"""

from __future__ import annotations

import itertools
from typing import Dict, List, Tuple

import pytest

from nonogram.admin.book_pdf_generator import (
    GUIDE_TECHNIQUES_2,
    BookPDFGenerator,
    PageKind,
    interior_page_count,
)
from tests.helpers.book_corpus import corpus_book, export_of, puzzle
from tests.helpers.pdf_pages import pdf_page_count

#: The worked example's line: the clue 3 1 on six squares.
CLUE = (3, 1)
LENGTH = 6


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

    CARD-206's title page is a separate ``+ 1`` at each call site, the
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
        # The second `+ 1` is CARD-206's title page — this AC's claim
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
    directly; every page's parity is held by
    ``tests/test_book_page_numbers.py``'s
    ``TestBookPageNumbers_ParityHoldsWithTheTocInserted`` (each folio's and
    size label's side against ``page_is_right_hand``).
    """

    @staticmethod
    @pytest.fixture(scope="class")
    def corpus() -> List[Dict[str, object]]:
        """3 easy, 2 medium, 1 hard — the AC's own example book.

        Sized 20 cells and up and no two the same within a tier: too wide
        for two to share a two-up page (FR-040) — this test wants exactly
        6 puzzle pages (one per puzzle), not a pairing saving. Their answers
        pack (every legal size does since 2026-11-09), so the answer term is
        read off the book's own page kinds rather than assumed.
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
        # across tiers or at these sizes: 6 puzzle pages. The answer pages
        # are however many the packing walk laid (4 measured: the tiers pack
        # apart), counted off the plan's kinds.
        kinds = BookPDFGenerator(corpus_book("card-201-ac5")).interior_stream(corpus).page_kinds
        answers = sum(kind is PageKind.ANSWER for kind in kinds)
        assert 0 < answers < 6, answers
        # CARD-200 (SCOPE+): this book's 6-entry TOC is one more page on
        # Book 1's own trim (`corpus_book`) — named explicitly here so the
        # guide's own "+1" claim stays isolated from the TOC's own term,
        # the same discipline `test_interior_page_count_adds_exactly_one_guide_page`
        # above now uses.
        assert (
            pdf_page_count(export)
            # the guide's second page (CARD-201), the table of contents
            # (CARD-200) and the title page (CARD-206) — one term each.
            == old_style_total(6, dividers=3, pages=6, answers=answers) + 1 + 1 + 1
        )
        assert pdf_page_count(export) == interior_page_count(6, 6, answers, 3)


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
