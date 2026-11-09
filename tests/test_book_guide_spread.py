"""CARD-229 — the "How to Solve" facing spread, and CARD-393's Play online line.

The guide is interior pages 2 (a verso) and 3 (a recto), set in the puzzle
pages' own frame: each technique a row of two columns, the three cell marks and
the difficulty legend one key strip, one cell size for every example, and, under
the intro, one sentence naming the Play online page when the book prints one.

**Every figure here is read from the written file** (ADR-0042/R6): the text and
the rules off the content streams, and "the Play page's real number" off the
page that carries its heading. The writer's own claims (the floor, the record
against the stream, one grid routine, nothing invented) are
``tests/test_book_guide_page_vector.py``'s; this file is what needs a whole
exported interior beside the guide: the puzzle page whose frame the guide must
share, the Play page whose number it names, the book's own page kinds.

Test budget (owner, 2026-11-07, "fewer tests"): the cells below are the ones
CARD-229's and CARD-393's acceptance criteria name, one per criterion, and the
raster guide-page group they retire is listed with a named survivor each in the
card's Worktree notes.
"""

from __future__ import annotations

import copy
import dataclasses
import re
from typing import Dict, List, Tuple

import pytest

from nonogram.admin import book_guide_vector as guide_vector
from nonogram.admin import book_pdf_generator
from nonogram.admin.book_guide_vector import (
    CLUE_DIGIT,
    guide_pages,
)
from nonogram.admin.book_interior_vector import interior_generator
from nonogram.admin.book_pdf_generator import (
    GUIDE_CELL_STATES,
    GUIDE_DIFFICULTY_LABELS,
    GUIDE_LEADING_PT,
    GUIDE_BODY_PT,
    GUIDE_TECHNIQUES_1,
    GUIDE_TECHNIQUES_2,
    BookPDFGenerator,
    page_is_right_hand,
)
from nonogram.difficulty import Tier
from tests.helpers import pdf_vector
from tests.helpers.book_corpus import baseline_puzzles, corpus_book, corpus_puzzles

#: The counts the corpus guide is drawn with, and the Play page it names.
COUNTS = dict(puzzle_count=24, easy_count=8, medium_count=8, hard_count=8, play_page=170)

PLAY_DOMAIN = "https://nonogram.adverax.io"

#: A stroked rectangle: ``x y w h re S``.
_OUTLINED = re.compile(
    r"(?P<x>-?\d+(?:\.\d+)?) (?P<y>-?\d+(?:\.\d+)?) "
    r"(?P<w>\d+(?:\.\d+)?) (?P<h>\d+(?:\.\d+)?) re S"
)


def _spread_book(domain=PLAY_DOMAIN, trim_mm=None):
    book = copy.copy(corpus_book())
    book.player_domain = domain
    if trim_mm is not None:
        book.trim_width_cm = f"{trim_mm[0] / 10:.2f}"
        book.trim_height_cm = f"{trim_mm[1] / 10:.2f}"
    return book


def _interior(book, puzzles):
    """``(plan stream, content streams of the written file)``."""
    generator = interior_generator(book)
    walk = generator.interior_stream(puzzles)
    return walk, pdf_vector.content_streams(generator.export_interior(puzzles).getvalue())


def _guide_text(stream: str) -> List[str]:
    return [text for _, _, _, text in pdf_vector.placed_text(stream)]




class TestGuideSpread_SitsOnPagesTwoAndThree:
    """AC-1: the guide is interior pages 2 and 3, a verso and a recto, and they face."""

    def test_the_guide_is_interior_pages_two_and_three_and_they_face(self):
        for puzzles in (corpus_puzzles(3), baseline_puzzles()):
            book = _spread_book()
            book.gutter_margin_cm, book.outside_margin_cm = "1.60", "1.00"
            walk, streams = _interior(book, puzzles)
            kinds = [kind.value for kind in walk.page_kinds]

            assert kinds[:3] == ["title", "guide", "guide"]
            assert kinds[3] == "toc"
            assert not page_is_right_hand(2) and page_is_right_hand(3)
            for number in (2, 3):
                assert _guide_text(streams[number - 1])[-1] == str(number)
            # The band carries the running head; the page's own title follows it.
            assert _guide_text(streams[1])[:2] == ["How to Solve", "How to Solve Nonograms"]
            assert _guide_text(streams[2])[:2] == ["How to Solve", "When the Puzzle Gets Harder"]
            assert not any(
                "How to Use This Book" in text for n in (2, 3) for text in _guide_text(streams[n - 1])
            )
            verso_rule = pdf_vector.frame_rules(streams[1])[0]
            recto_rule = pdf_vector.frame_rules(streams[2])[0]
            assert recto_rule[0] > verso_rule[0], "the gutter side is the recto's left"
            assert recto_rule[1] > verso_rule[1]
            assert recto_rule[1] - recto_rule[0] == verso_rule[1] - verso_rule[0]


class TestGuideSpread_SharesThePuzzlePagesFrame:
    """AC-2: margins, header-rule row and footer-rule row are a puzzle page's."""

    def test_the_two_rules_and_the_margins_are_the_puzzle_pages(self):
        walk, streams = _interior(_spread_book(), corpus_puzzles(4))
        kinds = [kind.value for kind in walk.page_kinds]
        for guide_number in (2, 3):
            same_side = next(
                number
                for number, kind in enumerate(kinds, start=1)
                if kind == "puzzle" and number % 2 == guide_number % 2
            )
            guide, puzzle = streams[guide_number - 1], streams[same_side - 1]

            assert pdf_vector.frame_rules(guide) == pdf_vector.frame_rules(puzzle), (guide_number, same_side)
            header, footer = pdf_vector.frame_rules(guide)
            assert footer[2] < header[2], "PDF y grows upward: the footer is lower"
            # The title is a puzzle page's band line: the same size and the same
            # baseline as the identity ("Puzzle N ...") a puzzle page sets there.
            title = pdf_vector.placed_text(guide)[0]
            identity = next(
                item for item in pdf_vector.placed_text(puzzle) if item[3].startswith("Puzzle ")
            )
            assert (title[2], title[1]) == (identity[2], identity[1]), (title, identity)
            # The body's left edge is the rule's own left end: the margin.
            body_left = min(x for x, y, _, _ in pdf_vector.placed_text(guide) if y < header[2] and y > footer[2])
            assert abs(body_left - header[0]) < 0.01, (guide_number, body_left, header[0])


#: The page of Book 1's spread this file reads the columns off, written out
#: here from the sheet's own numbers: a 2250 px usable width (8.5 in trim less
#: the 0.375 in gutter and 0.5 in outside margin, at 300 DPI), of which the
#: example column takes at most 55 % (1237 px), so every example (widest 1075 px
#: at the 7.5 mm book cell) keeps that cell and the text column keeps the rest.
BOOK1_SPREAD = {"cell_px": 88, "example_px": 1075, "text_px_at_least": 1100}


def _outline_strokes(stream: str) -> List[Tuple[float, float, float, float, float]]:
    """The heavier outlines around playable squares: ``(stroke, x, y, width, height)``.

    The stroked rectangles drawn at the page's heaviest rectangle stroke: the
    pipeline's boxes are stroked lighter, and a diagram's frame and cell lines
    are lines, not rectangles.
    """
    rectangles: List[Tuple[float, float, float, float, float]] = []
    state = 0.0
    for line in stream.split("\n"):
        width = re.fullmatch(r"(\d+(?:\.\d+)?) w", line)
        if width:
            state = float(width.group(1))
            continue
        match = _OUTLINED.fullmatch(line)
        if match:
            rectangles.append(
                (state, float(match["x"]), float(match["y"]), float(match["w"]), float(match["h"]))
            )
    heaviest = max(stroke for stroke, *_ in rectangles)
    # The frame (clue boxes and squares together) is stroked at the same border
    # weight on the same row; the squares' outline is the one that starts
    # furthest right.
    rows: Dict[float, Tuple[float, float, float, float, float]] = {}
    for rect in rectangles:
        if rect[0] == heaviest and (rect[2] not in rows or rect[1] > rows[rect[2]][1]):
            rows[rect[2]] = rect
    return list(rows.values())


def _outlines(stream: str) -> List[Tuple[float, float, float, float]]:
    """:func:`_outline_strokes` without the stroke: ``(x, y, width, height)``."""
    return [rect[1:] for rect in _outline_strokes(stream)]




def _round_marks(stream: str) -> List[Tuple[float, float, bool]]:
    """Every round mark on the page as ``(x of its top, y of its top, solid)``.

    A round mark is the ``m`` ... four ``c`` ... ``h`` path ``round_mark``
    writes; *solid* is whether the fill tone set before it was ink (``0 g``)
    rather than paper (``1 g``).
    """
    marks: List[Tuple[float, float, bool]] = []
    fill = 0.0
    lines = stream.split("\n")
    for index, line in enumerate(lines):
        tone = re.fullmatch(r"(\d+(?:\.\d+)?) g", line)
        if tone:
            fill = float(tone.group(1))
        start = re.fullmatch(r"(-?\d+(?:\.\d+)?) (-?\d+(?:\.\d+)?) m", line)
        if start and index + 5 < len(lines) and lines[index + 1].endswith(" c") and lines[index + 4].endswith(" c"):
            marks.append((float(start.group(1)), float(start.group(2)), fill == 0.0))
    return marks






def _guide_sources(play_page: int) -> List[str]:
    """Every string the guide may set, from the ``GUIDE_*`` constants alone."""
    found: List[str] = []

    def collect(value) -> None:
        if isinstance(value, str):
            found.append(value)
        elif isinstance(value, (tuple, list, frozenset)):
            for item in value:
                collect(item)
        elif dataclasses.is_dataclass(value) and not isinstance(value, type):
            for field in dataclasses.fields(value):
                collect(getattr(value, field.name))

    for name in dir(book_pdf_generator):
        if name.startswith(("GUIDE_", "GUIDE2_", "WORKED_EXAMPLE_")) and name != "GUIDE_PLAY_SENTENCE":
            collect(getattr(book_pdf_generator, name))
    found.append(book_pdf_generator.guide_play_sentence(play_page))
    return found


class TestGuideSpread_TextComesFromTheConstants:
    """AC-6: every sentence the pages set is a piece of an existing ``GUIDE_*`` string."""

    def test_no_prose_is_written_in_the_drawing_code(self):
        # Every drawn line, by kind: prose, headings and legend names must be a
        # run of one stored string (a wrapped line is a piece of its sentence);
        # what is not a stored string is either a count line the page builds
        # from the book's own numbers, a folio, a clue digit, or the pipeline's
        # two ASCII icon glyphs, each named below.
        sources = _guide_sources(170)
        counted = re.compile(r"(This book contains \d+ puzzles:|(Easy|Medium|Hard): \d+)")
        stray: List[str] = []
        generator = BookPDFGenerator(corpus_book())
        for page in guide_pages(
            generator.page_spec, generator.dpi, **COUNTS
        ):
            for face in page.faces:
                if face.kind in (CLUE_DIGIT, "folio"):
                    continue
                if face.kind == "pipeline label" and face.text in ("...", "!"):
                    continue
                if counted.fullmatch(face.text):
                    continue
                if not any(face.text in source for source in sources):
                    stray.append(face.text)
        assert stray == []

    def test_every_diagram_is_the_constants_diagram(self):
        """The diagrams drawn are the diagrams the lesson teaches, read cell by cell.

        Each example is located by its playable squares' outline; its filled
        and crossed squares are read back off the stream as column indices, and
        held to **literals written out here** (the guide's own lesson, not the
        constants under test) and to one brute force: the squeeze's "certain"
        row is the overlap of every placement of ``8`` on ten squares, which
        this recomputes. A same-size mutant (one filled square moved, a range
        shifted) therefore reds where a count of marks would not.
        """
        _, streams = _interior(_spread_book(), corpus_puzzles(4))
        diagonal = re.compile(r"(\S+) (\S+) m (\S+) (\S+) l S")

        def diagrams(stream: str):
            """``(columns, filled, crossed)`` of every example, top of the page first."""
            lines = stream.split("\n")
            fills = [
                tuple(float(v) for v in m.groups())
                for line in lines
                if (m := re.fullmatch(r"(\S+) (\S+) (\S+) (\S+) re f", line))
            ]
            crosses = [
                tuple(float(v) for v in m.groups())
                for m in diagonal.finditer(stream)
                if m.group(1) != m.group(3) and m.group(2) != m.group(4)
            ]
            found = []
            for ox, oy, width, cell in sorted(_outlines(stream), key=lambda o: -o[1]):
                columns = round(width / cell)
                filled = {
                    round((x - ox) / cell)
                    for x, y, w, h in fills
                    if abs(y - oy) < cell and abs(h - cell) < 1 and ox - 1 <= x < ox + width
                }
                crossed = {
                    int((min(x1, x2) - ox) / cell)
                    for x1, y1, x2, y2 in crosses
                    if oy - 1 <= min(y1, y2) and max(y1, y2) <= oy + cell + 1 and ox - 1 <= min(x1, x2) < ox + width
                }
                found.append((columns, frozenset(filled), frozenset(crossed)))
            return found

        none = frozenset()

        def span(a: int, b: int) -> frozenset:
            return frozenset(range(a, b))

        # The squeeze: every placement of a run of 8 on a line of 10, by brute force.
        placements = [span(start, start + 8) for start in range(10 - 8 + 1)]
        certain = frozenset.intersection(*placements)
        assert certain == span(2, 8)

        first = [
            (8, frozenset({0, 1, 2, 4, 5, 7}), frozenset({3, 6})),  # 3 2 1: runs 3, 2, 1 with gaps
            (10, span(0, 10), none),  # complete line
            (10, placements[0], none),  # squeeze: as far left
            (10, placements[-1], none),  # as far right
            (10, certain, none),  # what both agree on
            (8, frozenset({2, 3, 4}), frozenset({1, 5})),  # 3 done: its neighbours empty
        ]
        second = [
            (10, none, frozenset({3, 5})),  # region split
            (10, none, frozenset({3, 4, 5})),
            (5, frozenset({0, 1, 2}), none),  # every placement of 3 on 5
            (5, frozenset({1, 2, 3}), none),
            (5, frozenset({2, 3, 4}), none),
            (5, frozenset({2}), none),  # the one cell they agree on
            (6, none, none),  # worked example, 3 1 on 6: the clue
            (6, frozenset({1, 2}), none),  # overlap
            (6, frozenset({1, 2, 3}), frozenset({0, 4})),  # gap
            (6, frozenset({1, 2, 3, 5}), frozenset({0, 4})),  # solved
        ]
        # Book 1 draws the first page whole and the second with the worked
        # example (asserted: an empty ``if`` here would be a vacuous pass).
        assert any("1  The clue" in text for text in _guide_text(streams[2]))



_PLAY_NUMBER = re.compile(r"Scan the code on page (\d+)\.")


def _sentence_lines(placed, sentence: str):
    """The consecutive lines of ``placed`` that set ``sentence`` (it wraps on a narrow trim)."""
    words = sentence.split()
    for start in range(len(placed)):
        joined, taken = [], 0
        for item in placed[start:]:
            line = item[3]
            if not line or " ".join(words[taken : taken + len(line.split())]) != line:
                break
            joined.append(item)
            taken += len(line.split())
            if taken == len(words):
                return joined
    return []


def _sentence_page(streams: List[str]) -> int:
    """The page number the first guide page's Play sentence names."""
    text = " ".join(_guide_text(streams[1]))
    found = _PLAY_NUMBER.findall(text)
    assert len(found) == 1, text
    return int(found[0])


class TestGuidePage_NamesThePlayPage:
    """AC-393.1: the sentence, with the page number exactly, under the intro."""

    def test_the_sentence_names_page_167_below_the_intro_and_above_the_first_heading(self):
        from nonogram.admin.book_pdf_generator import GUIDE_INTRO, GUIDE_PLAY_SENTENCE

        generator = BookPDFGenerator(corpus_book())
        page = guide_vector.guide_page(generator.page_spec(2), generator.dpi, 2, play_page=167)
        text = [(y, t) for _, y, _, t in pdf_vector.placed_text("\n".join(page.stream.operators))]
        by_text = {t: y for y, t in text}
        sentence = GUIDE_PLAY_SENTENCE.format(page=167)

        assert "Every puzzle in this book can also be played online." in sentence
        assert sentence in by_text, [t for _, t in text]
        # PDF y grows upward: below the intro is a smaller y, above the first
        # technique heading is a larger one.
        assert by_text[GUIDE_INTRO] > by_text[sentence] > by_text[GUIDE_TECHNIQUES_1[0].heading]


class TestGuidePage_PlayPageNumberIsTheRealOne:
    """AC-393.2: the number printed is the Play page's number in the exported file."""

    @pytest.mark.parametrize(
        "puzzles,trim_mm",
        [
            (corpus_puzzles(4), None),
            (corpus_puzzles(5), None),
            (baseline_puzzles(), (152.4, 228.6)),
            (corpus_puzzles(5), (127.0, 203.2)),
        ],
        ids=["four", "five", "baseline-6x9", "five-5x8"],
    )
    def test_the_guide_names_the_page_that_carries_the_play_heading(self, puzzles, trim_mm):
        from nonogram.admin.book_pdf_generator import TOC_TITLE
        from nonogram.admin.book_play_vector import PLAY_HEADING, PLAY_TITLE

        def carries_the_play_heading(text: List[str]) -> bool:
            # The designed page wraps its title over lines; the plain fallback
            # sets PLAY_HEADING whole. The contents page lists "Play online" as
            # a row, which is not the page itself.
            if TOC_TITLE in text:
                return False
            return PLAY_HEADING in text or PLAY_TITLE in " ".join(text)

        _, streams = _interior(_spread_book(trim_mm=trim_mm), puzzles)
        carrying = [
            number
            for number, stream in enumerate(streams, start=1)
            if carries_the_play_heading(_guide_text(stream))
        ]

        assert carrying != [] and len(carrying) == 1, carrying
        assert _sentence_page(streams) == carrying[0]
        assert carrying[0] % 2 == 1, "the Play page is a right-hand page"




class TestGuidePage_NoPlayPageNoLine:
    """AC-393.3: no stored domain, no line, and the pages are exactly the guide without it."""

    def test_a_book_with_no_domain_prints_the_guide_without_the_sentence(self):
        from nonogram.admin.book_guide_spread import spread_page

        puzzles = corpus_puzzles(4)
        _, with_domain = _interior(_spread_book(), puzzles)
        _, without = _interior(_spread_book(domain=None), puzzles)
        generator = BookPDFGenerator(_spread_book(domain=None))

        assert not any("played online" in text for n in (2, 3) for text in _guide_text(without[n - 1]))
        for number in (2, 3):
            expected = spread_page(generator.page_spec(number), generator.dpi, number)
            assert without[number - 1].rstrip("\n") == "\n".join(expected.stream.operators), number
        # And the sentence is the one thing the domain adds to the first page.
        added = [t for t in _guide_text(with_domain[1]) if t not in _guide_text(without[1])]
        assert added and all("online" in t or "page" in t or "Scan" in t or "code" in t for t in added)


class TestGuidePage_TheLineFitsEveryTrim:
    """AC-393.4: still two pages, and the line overlaps no other mark, on every trim."""

    @pytest.mark.parametrize(
        "trim_mm",
        [None, (152.4, 228.6), (127.0, 203.2), (100.0, 100.0)],
        ids=["book1", "6x9", "5x8", "10x10cm"],
    )
    def test_the_guide_is_two_pages_and_the_sentence_overlaps_nothing(self, trim_mm):
        puzzles = corpus_puzzles(4)
        walk, streams = _interior(_spread_book(trim_mm=trim_mm), puzzles)
        metrics = guide_vector.interior_face_metrics()

        assert [kind.value for kind in walk.page_kinds].count("guide") == 2
        placed = pdf_vector.placed_text(streams[1])
        sentence = _sentence_lines(
            placed, book_pdf_generator.guide_play_sentence(_sentence_page(streams))
        )
        assert sentence, "the guide's first page does not carry the sentence"

        def box(item):
            x, y, size, text = item
            return (
                x,
                y + metrics.descent * size / 1000.0,
                x + metrics.advance(text) * size,
                y + metrics.ascent * size / 1000.0,
            )

        others = [box(item) for item in placed if item not in sentence]
        sx0 = min(box(item)[0] for item in sentence)
        sx1 = max(box(item)[2] for item in sentence)
        sy0 = min(box(item)[1] for item in sentence)
        sy1 = max(box(item)[3] for item in sentence)
        for x0, y0, x1, y1 in others:
            assert x1 <= sx0 or x0 >= sx1 or y1 <= sy0 or y0 >= sy1, (x0, y0, x1, y1)
        for rect in re.finditer(
            r"(?P<x>-?\d+(?:\.\d+)?) (?P<y>-?\d+(?:\.\d+)?) (?P<w>\d+(?:\.\d+)?) (?P<h>\d+(?:\.\d+)?) re [fS]",
            streams[1],
        ):
            x, y = float(rect["x"]), float(rect["y"])
            right, top = x + float(rect["w"]), y + float(rect["h"])
            assert right <= sx0 or x >= sx1 or top <= sy0 or y >= sy1, rect.group(0)


class TestGuidePage_CarriesNoQr:
    """AC-393.6: the guide carries the sentence and no code (ADR-0041/R8)."""

    def test_the_sentence_adds_text_and_no_ink_to_the_guide(self):
        generator = BookPDFGenerator(corpus_book())
        for number in (2, 3):
            kwargs = dict(puzzle_count=4, easy_count=1, medium_count=1, hard_count=2)
            with_line = guide_vector.guide_page(
                generator.page_spec(number), generator.dpi, number, play_page=167, **kwargs
            )
            without = guide_vector.guide_page(
                generator.page_spec(number), generator.dpi, number, **kwargs
            )
            # Everything but the text operators is the page without the line.
            text_operators = {"BT", "ET", "Tf", "Td", "Tj", "g"}
            drawn_ink = lambda page: {
                name: count
                for name, count in pdf_vector.operator_tally("\n".join(page.stream.operators)).items()
                if name not in text_operators
            }

            assert drawn_ink(with_line) == drawn_ink(without), number
            assert b"/Image" not in guide_vector.write_guide_pdf([with_line], 1).getvalue()
