"""The owner's layout polish of 2026-11-09, pinned on the shipped defaults.

Several older modules measure the book with the previous layout switched back
on (``tests/helpers/legacy_book_layout.py``); this module is where the new
defaults themselves are asserted, so none of them is only ever tested off:

* no frame around the clues on a book page (``BOOK_PUZZLE_FRAME``);
* every answer up to ``limits.MAX_SIZE`` packs (``PACKED_MAX_WIDTH/HEIGHT``);
* no rule under an answer page's running head;
* a level's divider drawn in the Solutions opener's style;
* the guide's neighbouring filled squares parted by the solved join's grey;
* the guide's promise sentence.
"""

from __future__ import annotations

import re

import numpy as np

from nonogram.admin import book_answer_key, book_page_spec as page_spec_module
from nonogram.admin import book_pdf_generator as generator_module
from nonogram.admin.book_answer_key import Answer, qualifies_for_packing
from nonogram.admin.book_answer_vector import draw_running_head
from nonogram.admin.book_guide_vector import draw_line_diagram
from nonogram.admin.book_page_spec import book_page_spec
from nonogram.admin.book_pdf_generator import (
    GUIDE_PROMISE,
    BookPDFGenerator,
    ExampleStep,
    _SOLVED_GRID_GRAY,
    example_line_layout,
    page_frame,
)
from nonogram.admin.book_vector import ContentStream, interior_face_metrics
from nonogram.admin.book_vector_draw import as_grey
from nonogram.difficulty import Tier
from nonogram.export.layout import compute_layout
from nonogram.limits import MAX_SIZE
from tests.helpers import pdf_vector
from tests.helpers.book_corpus import corpus_book


class TestLayoutPolish_NoFrameAroundTheClues:
    def test_the_book_spec_is_unframed_and_lays_out_no_frame(self) -> None:
        assert page_spec_module.BOOK_PUZZLE_FRAME is False
        for page_number in (1, 2, 7, 8):
            spec = book_page_spec(None, page_number)
            assert spec.framed is False
            layout = compute_layout(((1,),) * 15, ((1,),) * 15, spec)
            assert layout.frame is None

    def test_the_guides_lines_keep_their_clue_box(self) -> None:
        layout = example_line_layout(book_page_spec(None, 2), (3, 1), 6)
        assert layout.frame is not None


class TestLayoutPolish_EveryAnswerPacks:
    def test_the_threshold_is_the_largest_supported_size(self) -> None:
        assert book_answer_key.PACKED_MAX_WIDTH == MAX_SIZE
        assert book_answer_key.PACKED_MAX_HEIGHT == MAX_SIZE
        assert qualifies_for_packing(Answer(number=1, width=MAX_SIZE, height=MAX_SIZE, level=None))
        assert qualifies_for_packing(Answer(number=1, width=25, height=30, level=None))


class TestLayoutPolish_TheRunningHeadHasNoRule:
    def test_the_running_head_sets_text_and_strokes_nothing(self) -> None:
        generator = BookPDFGenerator(corpus_book())
        frame = page_frame(generator.page_spec(9))
        stream = ContentStream(width_px=frame.width, height_px=frame.height, dpi=generator.dpi)
        draw_running_head(stream, frame, 9, (1, 2, 3, 4), Tier.EASY, interior_face_metrics())
        tokens = set(pdf_vector.operator_tokens(stream.render().decode("latin-1")))
        assert "Tj" in tokens
        assert not tokens & {"l", "S", "re"}, sorted(tokens)


class TestLayoutPolish_LevelDividerMatchesTheSolutionsOpener:
    def test_the_walk_asks_for_the_opener_style_divider(self) -> None:
        assert generator_module.LEVEL_DIVIDER_OPENER is True
        generator = BookPDFGenerator(corpus_book())
        drawn = generator.divider_page("easy", 5, "Easy", puzzle_range=(1, 68))
        expected = generator.create_level_divider(5, Tier.EASY, (1, 68))
        assert drawn.tobytes() == expected.tobytes()
        assert drawn.tobytes() != generator.create_divider_page(5, "Easy").tobytes()

    def test_its_ink_sits_on_the_left_like_the_openers(self) -> None:
        generator = BookPDFGenerator(corpus_book())
        page = generator.create_level_divider(5, Tier.MEDIUM, (69, 125))
        opener = generator.create_solutions_opener(5, 160)
        ink = np.asarray(page.convert("L")) < 128
        opener_ink = np.asarray(opener.convert("L")) < 128
        # The same rule at the same place opens both pages.
        first_row = int(np.nonzero(ink.any(axis=1))[0][0])
        assert first_row == int(np.nonzero(opener_ink.any(axis=1))[0][0])
        assert int(np.nonzero(ink.any(axis=0))[0][0]) == int(np.nonzero(opener_ink.any(axis=0))[0][0])

    def test_each_level_draws_its_own_dots(self) -> None:
        generator = BookPDFGenerator(corpus_book())
        pages = [generator.create_level_divider(5, tier, (1, 2)) for tier in Tier]
        inks = [int((np.asarray(page.convert("L")) < 128).sum()) for page in pages]
        # One more solid dot per rank, the name aside: the pages all differ.
        assert len({page.tobytes() for page in pages}) == len(pages)
        assert all(ink > 0 for ink in inks)


class TestLayoutPolish_GuideSeparatesNeighbouringFilledSquares:
    def test_two_neighbouring_filled_squares_are_parted_in_the_join_grey(self) -> None:
        layout = example_line_layout(book_page_spec(None, 2), (3,), 5)
        stream = ContentStream(width_px=layout.width, height_px=layout.height, dpi=300)
        draw_line_diagram(stream, layout, ExampleStep("", "", frozenset({0, 1, 2}), frozenset()))
        text = stream.render().decode("latin-1")
        greys = [float(value) for value in re.findall(r"([0-9.]+) G\b", text)]
        assert any(abs(value - as_grey(_SOLVED_GRID_GRAY)) < 1e-3 for value in greys), greys

    def test_a_lone_filled_square_draws_no_join(self) -> None:
        layout = example_line_layout(book_page_spec(None, 2), (1,), 5)
        lone = ContentStream(width_px=layout.width, height_px=layout.height, dpi=300)
        draw_line_diagram(lone, layout, ExampleStep("", "", frozenset({2}), frozenset()))
        pair = ContentStream(width_px=layout.width, height_px=layout.height, dpi=300)
        draw_line_diagram(pair, layout, ExampleStep("", "", frozenset({2, 3}), frozenset()))
        lone_lines = pdf_vector.operator_tokens(lone.render().decode("latin-1")).count("l")
        pair_lines = pdf_vector.operator_tokens(pair.render().decode("latin-1")).count("l")
        assert pair_lines == lone_lines + 1


class TestLayoutPolish_GuidePromise:
    def test_the_promise_is_one_sentence_naming_both_facts(self) -> None:
        assert "just one solution" in GUIDE_PROMISE
        assert "picture" in GUIDE_PROMISE
