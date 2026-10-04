"""The guide page is "How to Solve Nonograms" with a worked example (CARD-167).

FR-041 (amended 2026-10-04), AC-324..AC-326, one class each.

**Everything is read off pages.** The book is exported, its interior PDF read
back with ``tests.helpers.pdf_pages`` and page 1 measured as pixels: the title
is found by searching the page for the title's own glyphs, the worked example's
lines by their ruled rows, each square's state by how much of it is ink, and
type sizes by measuring glyph boxes. Nothing here reads the step list, the
title constant or a type size from :mod:`nonogram.admin.book_pdf_generator`;
the numbers the criteria give (the two titles, the clue ``3 1`` on six squares,
the 10 pt floor, CON-018's margins) are written out below.

AC-326 needs the same book exported with the old guide page and with the new
one. The old page is :func:`old_guide_page`, a test-local transcription of
``create_guide_page`` as it stood before this card (title "How to Use This
Book", the count breakdown and three instruction lines), patched in for one
export of the same book.
"""

from __future__ import annotations

import itertools
from typing import Dict, List, Sequence, Tuple

import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont

from nonogram.admin.book_manager import Book, BookMetadata
from nonogram.admin.book_pdf_generator import BookPDFGenerator, page_frame

from tests.helpers.book_corpus import corpus_book, export_of, page_digest, puzzle
from tests.helpers.page_ink import drawing_of
from tests.helpers.pdf_pages import pdf_page_count, pdf_pages, same_page

# --------------------------------------------------------------------------
# What the acceptance criteria say, written out
# --------------------------------------------------------------------------

NEW_TITLE = "How to Solve Nonograms"
OLD_TITLE = "How to Use This Book"

#: The worked example's line (AC-325): the clue 3 1 on six squares.
CLUE = (3, 1)
LENGTH = 6

#: CON-020's floor, in points.
FLOOR_PT = 10.0

#: The resolution a book page is drawn at, and points per inch.
BOOK_DPI = 300
POINTS_PER_INCH = 72.0

#: The title's and the body's size on the guide page at the Book 1 trim
#: (CARD-149's 22 pt and 11 pt), as whole pixels at 300 DPI.
TITLE_PX = round(22 * BOOK_DPI / POINTS_PER_INCH)
BODY_PX = round(11 * BOOK_DPI / POINTS_PER_INCH)

ARIAL = "/System/Library/Fonts/Arial.ttf"
INK_THRESHOLD = 128

#: A row whose ink runs unbroken for longer than this is a ruled line.
RULE_RUN_PX = 300

#: CON-018's margins in pixels at 300 DPI: 0.5 in gutter (left on the
#: right-hand page 1) and 0.375 in elsewhere.
GUTTER_PX = 150
OUTSIDE_PX = 112.5


def face(size_px: int) -> ImageFont.ImageFont:
    """The face the guide page letters in, at ``size_px`` (Arial, or Pillow's)."""
    try:
        return ImageFont.truetype(ARIAL, size_px)
    except OSError:  # pragma: no cover - only on a machine without Arial
        return ImageFont.load_default(size_px)


# --------------------------------------------------------------------------
# The books
# --------------------------------------------------------------------------


def three_easy_20x20() -> List[Dict[str, object]]:
    """AC-324's book content: three easy 20x20 puzzles."""
    return [puzzle(f"card167-{n}", 20, 20, 6, "easy", f"Picture {n}") for n in (1, 2, 3)]


def six_by_nine_book() -> Book:
    """A 6 x 9 in book on CON-018's margins."""
    return Book(
        book_id="card-167-6x9",
        metadata=BookMetadata(
            title="Six by Nine",
            description="CARD-167's second trim.",
            theme="generic",
            target_audience="adults",
            size="",
            page_count=0,
        ),
        trim_width_cm=f"{6 * 2.54:.2f}",
        trim_height_cm=f"{9 * 2.54:.2f}",
        gutter_margin_cm="1.27",
        outside_margin_cm="0.95",
    )


#: The smallest trim a book may be stored with (``book_page_spec.MIN_TRIM_CM``),
#: written out rather than imported.
MIN_TRIM_CM = 10.0


def ten_cm_wide_book(height_cm: float) -> Book:
    """A book at the minimum 10 cm width on CON-018's margins."""
    return Book(
        book_id=f"card-167-10x{height_cm:g}",
        metadata=BookMetadata(
            title="Ten Wide",
            description="CARD-167's narrowest trim.",
            theme="generic",
            target_audience="adults",
            size="",
            page_count=0,
        ),
        trim_width_cm=f"{MIN_TRIM_CM:.2f}",
        trim_height_cm=f"{height_cm:.2f}",
        gutter_margin_cm="1.27",
        outside_margin_cm="0.95",
    )


def old_guide_page(
    self: BookPDFGenerator,
    puzzle_count: int,
    easy_count: int,
    medium_count: int,
    hard_count: int,
    page_number: int = 1,
) -> Image.Image:
    """``create_guide_page`` as it stood before CARD-167, transcribed."""
    frame = page_frame(self.page_spec(page_number))
    guide = Image.new("RGB", (frame.width, frame.height), "white")
    draw = ImageDraw.Draw(guide)
    title_font = face(round(22 * self.dpi / POINTS_PER_INCH))
    text_font = face(round(11 * self.dpi / POINTS_PER_INCH))
    leading = round(17 * self.dpi / POINTS_PER_INCH)
    draw.text((frame.left, frame.top), OLD_TITLE, fill="black", font=title_font)
    lines = [
        f"This book contains {puzzle_count} puzzles.",
        "",
        "Difficulty Levels:",
        f"  Easy:   {easy_count} puzzles",
        f"  Medium: {medium_count} puzzles",
        f"  Hard:   {hard_count} puzzles",
        "",
        "Instructions:",
        "  1. Fill in the grid based on the clues",
        "  2. Check your work against the answer key",
        "  3. Have fun!",
    ]
    y = frame.top + round(36 * self.dpi / POINTS_PER_INCH)
    for line in lines:
        draw.text((frame.left, y), line, fill="black", font=text_font)
        y += leading
    return guide


@pytest.fixture(scope="module")
def new_export() -> bytes:
    """AC-324's book, exported as the code stands."""
    return export_of(BookPDFGenerator(corpus_book("card-167")), three_easy_20x20())


@pytest.fixture(scope="module")
def old_export() -> bytes:
    """The same book, exported with the pre-CARD-167 guide page patched in."""
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(BookPDFGenerator, "create_guide_page", old_guide_page)
        return export_of(BookPDFGenerator(corpus_book("card-167")), three_easy_20x20())


@pytest.fixture(scope="module")
def new_pages(new_export) -> List[Image.Image]:
    return pdf_pages(new_export)


@pytest.fixture(scope="module")
def old_pages(old_export) -> List[Image.Image]:
    return pdf_pages(old_export)


# --------------------------------------------------------------------------
# Measuring a page
# --------------------------------------------------------------------------


def dark(image: Image.Image) -> np.ndarray:
    return np.asarray(image.convert("L")) < INK_THRESHOLD


def bands(mask: np.ndarray) -> List[Tuple[int, int]]:
    """``(top, bottom)`` of each run of inked rows."""
    rows = np.flatnonzero(mask.any(axis=1))
    if not rows.size:
        return []
    breaks = np.flatnonzero(np.diff(rows) > 1)
    starts = np.concatenate(([rows[0]], rows[breaks + 1]))
    ends = np.concatenate((rows[breaks], [rows[-1]]))
    return [(int(a), int(b)) for a, b in zip(starts, ends)]


def longest_run(row: np.ndarray) -> int:
    padded = np.concatenate(([False], row, [False])).astype(np.int8)
    edges = np.flatnonzero(np.diff(padded))
    return int((edges[1::2] - edges[0::2]).max()) if edges.size else 0


def is_ruled(mask: np.ndarray, band: Tuple[int, int]) -> bool:
    return max(longest_run(mask[row]) for row in range(band[0], band[1] + 1)) > RULE_RUN_PX


def type_bands(mask: np.ndarray) -> List[Tuple[int, int]]:
    """The bands that are lines of type (no ruled row in them)."""
    return [band for band in bands(mask) if not is_ruled(mask, band)]


def drawn_bands(mask: np.ndarray) -> List[Tuple[int, int]]:
    """The bands that carry a ruled row: the worked example's lines."""
    return [band for band in bands(mask) if is_ruled(mask, band)]


def probe(text: str, font: ImageFont.ImageFont) -> np.ndarray:
    """``text``'s ink as a boolean mask cropped to its own box."""
    left, top, right, bottom = font.getbbox(text)
    scratch = Image.new("L", (right - left + 40, bottom - top + 40), 255)
    ImageDraw.Draw(scratch).text((20 - left, 20 - top), text, fill=0, font=font)
    mask = dark(scratch)
    rows, cols = np.flatnonzero(mask.any(axis=1)), np.flatnonzero(mask.any(axis=0))
    return mask[rows[0] : rows[-1] + 1, cols[0] : cols[-1] + 1]


def occurrences(page_mask: np.ndarray, template: np.ndarray, share: float = 0.9) -> int:
    """How many places on the page carry ``template``'s ink and little else.

    A window matches when at least ``share`` of the template's ink is inked on
    the page there (recall) *and* at least ``share`` of the page's ink inside
    the window is the template's (precision). Correlations by FFT, so every
    position of the page is tried. Neighbouring hits of one occurrence are
    merged by counting connected groups of matching positions.
    """
    height, width = page_mask.shape
    th, tw = template.shape
    shape = (height + th, width + tw)
    page = page_mask.astype(np.float64)
    temp = template[::-1, ::-1].astype(np.float64)
    spectrum = np.fft.rfft2(page, shape)
    overlap = np.fft.irfft2(spectrum * np.fft.rfft2(temp, shape), shape)
    window = np.fft.irfft2(spectrum * np.fft.rfft2(np.ones_like(temp), shape), shape)
    overlap = overlap[th - 1 : height, tw - 1 : width]
    window = window[th - 1 : height, tw - 1 : width]
    ink = template.sum()
    hits = (overlap >= share * ink) & (overlap >= share * np.maximum(window, 1))
    if not hits.any():
        return 0
    groups = 0
    for top, bottom in bands(hits):
        columns = np.flatnonzero(hits[top : bottom + 1].any(axis=0))
        groups += 1 + int((np.diff(columns) > 1).sum())
    return groups


#: A row at a line's foot holding less than this share of its busiest row's
#: ink is a descender row, not the body of the line.
TAIL_SHARE = 0.2


def baseline_row(counts: np.ndarray) -> int:
    """The 0-based row of a line's baseline, from its per-row ink counts."""
    rows = np.flatnonzero(counts >= TAIL_SHARE * counts.max())
    return int(rows[-1])


def cap_height_points(mask: np.ndarray, band: Tuple[int, int], reference: float) -> float:
    """A line of type's size in points, from its top to its baseline.

    The baseline is the band's last row once the sparse rows at its foot are
    dropped — descenders: rows holding less than :data:`TAIL_SHARE` of the
    band's busiest row — and the top of a line is its capitals' and
    ascenders' height. ``reference`` is the face's own top-to-baseline height
    per em, measured on a probe, so the result is a measurement of the line.
    """
    top, bottom = band
    baseline = top + baseline_row(mask[top : bottom + 1].sum(axis=1))
    em_px = (baseline - top + 1) / reference
    return em_px * POINTS_PER_INCH / BOOK_DPI


def top_to_baseline(text: str, font: ImageFont.ImageFont) -> float:
    """``text``'s top-to-baseline ink height per em, measured at a large size."""
    baseline = baseline_row(probe(text, font).sum(axis=1))
    return (baseline + 1) / font.size


REFERENCE_SIZE = 400


def text_reference() -> float:
    return top_to_baseline("Hdlk", face(REFERENCE_SIZE))


def digit_reference() -> float:
    return top_to_baseline("31", ImageFont.load_default(size=REFERENCE_SIZE))


def column_groups(columns: np.ndarray) -> List[List[int]]:
    if not columns.size:
        return []
    groups, current = [], [int(columns[0])]
    for value in columns[1:]:
        if value == current[-1] + 1:
            current.append(int(value))
        else:
            groups.append(current)
            current = [int(value)]
    groups.append(current)
    return groups


def read_lines(mask: np.ndarray) -> List[Dict[str, object]]:
    """The worked example's drawn lines: each one's clue glyphs and square states.

    Vertical rules are the columns inked over (nearly) a band's whole height.
    A filled square is such a column too, so the rules are read off the
    **first** line — whose squares :meth:`test_the_steps_solve_the_line_from_the_clue_to_the_finished_line`
    asserts are all empty — and every later line is checked to span exactly
    the same columns before those rules are applied to it. The first rule is
    the frame's left side, the rest bound the squares, and the clue sits
    between the first two.
    """
    found = drawn_bands(mask)
    if not found:
        return []
    first = mask[found[0][0] : found[0][1] + 1]
    rules = column_groups(np.flatnonzero(first.sum(axis=0) >= 0.9 * first.shape[0]))
    extent = column_groups(np.flatnonzero(first.any(axis=0)))
    span = (extent[0][0], extent[-1][-1])
    lines = []
    for top, bottom in found:
        strip = mask[top : bottom + 1]
        inked = np.flatnonzero(strip.any(axis=0))
        width = strip[:, span[0] : span[1] + 1].any(axis=0).sum()
        horizontal = column_groups(np.flatnonzero(strip.sum(axis=1) >= 0.9 * width))
        inner_top = horizontal[0][-1] + 1
        inner_bottom = horizontal[-1][0] - 1
        states = []
        for left, right in zip(rules[1:], rules[2:]):
            inset = 6
            cell = strip[inner_top + inset : inner_bottom - inset + 1, left[-1] + 1 + inset : right[0] - inset]
            share = cell.mean()
            states.append("filled" if share > 0.8 else "crossed" if share > 0.02 else "empty")
        gutter = strip[inner_top : inner_bottom + 1, rules[0][-1] + 1 : rules[1][0]]
        glyphs = []
        for blob in column_groups(np.flatnonzero(gutter.any(axis=0))):
            piece = gutter[:, blob[0] : blob[-1] + 1]
            rows = np.flatnonzero(piece.any(axis=1))
            glyphs.append(piece[rows[0] : rows[-1] + 1])
        lines.append(
            {
                "rules": len(rules),
                "rule_widths": [len(rule) for rule in rules],
                "span": (int(inked[0]), int(inked[-1])),
                "states": states,
                "glyphs": glyphs,
            }
        )
    return lines


def read_digit(glyph: np.ndarray) -> Tuple[str, int]:
    """The digit (in Pillow's default face, the clue face) ``glyph`` best matches.

    Returns ``(digit, height_px)``. Each digit is rendered at the size that
    gives it ``glyph``'s height and compared by intersection over union.
    """
    best, best_score = "", -1.0
    for digit in "0123456789":
        ratio = probe(digit, ImageFont.load_default(size=REFERENCE_SIZE)).shape[0] / REFERENCE_SIZE
        size = max(1, round(glyph.shape[0] / ratio))
        for trial in (size - 1, size, size + 1):
            reference = probe(digit, ImageFont.load_default(size=trial))
            h = min(reference.shape[0], glyph.shape[0])
            w = max(reference.shape[1], glyph.shape[1])
            a = np.zeros((h, w), bool)
            b = np.zeros((h, w), bool)
            a[:, : glyph.shape[1]] = glyph[:h]
            b[:, : reference.shape[1]] = reference[:h]
            score = (a & b).sum() / max((a | b).sum(), 1)
            if score > best_score:
                best, best_score = digit, score
    return best, glyph.shape[0]


def placements() -> List[Tuple[bool, ...]]:
    """Every line of :data:`LENGTH` squares whose runs are :data:`CLUE`."""
    found = []
    for line in itertools.product((False, True), repeat=LENGTH):
        runs = tuple(len(list(group)) for filled, group in itertools.groupby(line) if filled)
        if runs == CLUE:
            found.append(line)
    return found


def frame_px(width: int, height: int) -> Tuple[float, float, float, float]:
    """Page 1's usable area from CON-018's margins: (left, top, right, bottom)."""
    return GUTTER_PX, OUTSIDE_PX, width - OUTSIDE_PX, height - OUTSIDE_PX


# --------------------------------------------------------------------------
# AC-324
# --------------------------------------------------------------------------


class TestGuidePage_TitledHowToSolveNonograms:
    """AC-324 — page 1's title reads "How to Solve Nonograms"; the old title is nowhere."""

    def test_the_exported_interior_page_1_is_titled_how_to_solve_nonograms(self, new_pages):
        mask = dark(new_pages[0])
        title = type_bands(mask)[0]
        assert occurrences(mask[title[0] - 5 : title[1] + 6], probe(NEW_TITLE, face(TITLE_PX))) == 1, (
            "the first line of interior page 1 is not the title "
            f"{NEW_TITLE!r} set at {TITLE_PX} px"
        )

    def test_the_old_title_appears_nowhere_on_page_1(self, new_pages):
        mask = dark(new_pages[0])
        for size in (TITLE_PX, BODY_PX):
            assert occurrences(mask, probe(OLD_TITLE, face(size))) == 0, (
                f"{OLD_TITLE!r} is printed on interior page 1 at {size} px"
            )

    def test_the_search_finds_the_old_title_on_the_old_page(self, old_pages):
        """The search above can see a title: it finds the old one where it was."""
        mask = dark(old_pages[0])
        assert occurrences(mask, probe(OLD_TITLE, face(TITLE_PX))) == 1
        assert occurrences(mask, probe(NEW_TITLE, face(TITLE_PX))) == 0


# --------------------------------------------------------------------------
# AC-325
# --------------------------------------------------------------------------


class TestGuidePage_CarriesAWorkedExampleOnOnePage:
    """AC-325 — one line, its clue, solved step by step, on page 1 alone, >= 10 pt."""

    @pytest.fixture(scope="class")
    def lines(self, new_pages) -> List[Dict[str, object]]:
        mask = dark(new_pages[0])
        return read_lines(mask)

    def test_page_1_draws_the_line_of_six_squares_at_each_step(self, lines):
        assert len(lines) == 4, f"page 1 carries {len(lines)} drawn lines, not 4 steps"
        assert len({line["span"] for line in lines}) == 1, "the four lines are not aligned"
        for number, line in enumerate(lines, start=1):
            # The frame's left side and the 7 boundaries of 6 squares.
            assert line["rules"] == LENGTH + 2, f"step {number}: {line['rules']} rules"
            assert len(line["states"]) == LENGTH

    def test_the_lines_are_ruled_like_the_books_puzzle_pages(self, lines, new_pages):
        """ADR-0037/R2 on the example: thin >= 0.25 mm, heavy = 2 x thin.

        Measured on the first line (no square filled): the frame's side and
        the grid's two edges and its every-5th boundary are heavy, the rest
        thin — and the two widths are the widths the rules of the book's own
        20x20 puzzle page (interior page 3) measure on the same page scan.
        """
        widths = lines[0]["rule_widths"]
        thin = min(widths)
        assert thin >= 0.25 / 25.4 * BOOK_DPI, f"the thin rule is {thin} px"
        heavy = 2 * thin
        assert widths == [heavy, heavy, thin, thin, thin, thin, heavy, heavy], widths

        puzzle_page = dark(new_pages[2])
        runs = np.array([longest_run(column) for column in puzzle_page.T])
        full = column_groups(np.flatnonzero(runs >= 0.9 * runs.max()))
        assert {len(rule) for rule in full} == {thin, heavy}

    def test_every_step_carries_the_clue_3_1(self, lines):
        for number, line in enumerate(lines, start=1):
            digits = "".join(read_digit(glyph)[0] for glyph in line["glyphs"])
            assert digits == "31", f"step {number}'s clue reads {digits!r}"

    def test_the_steps_solve_the_line_from_the_clue_to_the_finished_line(self, lines):
        steps = [line["states"] for line in lines]
        solutions = placements()
        assert len(solutions) == 3, "3 1 fits a row of 6 in three ways"

        # From the clue: nothing decided.
        assert steps[0] == ["empty"] * LENGTH
        # The overlap: exactly the squares every placement fills.
        every = [all(line[i] for line in solutions) for i in range(LENGTH)]
        assert [state == "filled" for state in steps[1]] == every
        assert "crossed" not in steps[1]
        # Each step keeps what the one before decided.
        for earlier, later in zip(steps, steps[1:]):
            for before, after in zip(earlier, later):
                assert before == "empty" or before == after
        # The finished line: every square decided, and its runs are the clue.
        finished = steps[-1]
        assert "empty" not in finished
        filled = tuple(state == "filled" for state in finished)
        assert filled in solutions
        # The gap step: once a crossed square rules placements out, exactly
        # one remains, and it is the finished line.
        crossed = [i for i, state in enumerate(steps[2]) if state == "crossed"]
        remaining = [line for line in solutions if not any(line[i] for i in crossed)]
        assert remaining == [filled]

    def test_nothing_of_the_example_reaches_interior_page_2(self, new_pages, old_pages):
        page_2 = new_pages[1]
        assert not drawn_bands(dark(page_2)), "interior page 2 carries a ruled line"
        assert page_digest(page_2) == page_digest(old_pages[1])

    def test_every_mark_on_page_1_sits_inside_its_usable_area(self, new_pages):
        page = new_pages[0]
        mask = dark(page)
        rows, cols = np.flatnonzero(mask.any(axis=1)), np.flatnonzero(mask.any(axis=0))
        left, top, right, bottom = frame_px(*page.size)
        assert left <= cols[0] and cols[-1] <= right
        assert top <= rows[0] and rows[-1] <= bottom

    def test_every_line_of_type_on_page_1_holds_10pt(self, new_pages):
        """Each line measured from its top to its baseline.

        The premise, which this test also enforces: every line of the page's
        copy reaches cap height (a capital, a digit or an ascender). A line of
        x-height letters only would measure about 0.72 of its size and fail
        here, which is a copy problem to fix (CARD-167 reworded step 2 so that
        "way." no longer wraps onto a line of its own at the Book 1 trim).
        """
        mask = dark(new_pages[0])
        reference = text_reference()
        sizes = [cap_height_points(mask, band, reference) for band in type_bands(mask)]
        assert len(sizes) >= 9
        assert min(sizes) >= FLOOR_PT, f"a line of type measures {min(sizes):.2f} pt"
        # And the measurement measures: the body is 11 pt, the title 22.
        assert sizes[0] == pytest.approx(22, abs=0.8)
        assert sorted(sizes)[len(sizes) // 2] == pytest.approx(11, abs=0.6)

    def test_every_clue_digit_holds_10pt(self, lines):
        reference = digit_reference()
        assert len(lines) == 4
        for number, line in enumerate(lines, start=1):
            # "3" and "1": a gutter read as empty must not pass for small type.
            assert len(line["glyphs"]) == 2, f"step {number}: {len(line['glyphs'])} clue glyphs"
            for glyph in line["glyphs"]:
                points = glyph.shape[0] / reference * POINTS_PER_INCH / BOOK_DPI
                assert points >= FLOOR_PT, f"step {number}: a clue digit is {points:.2f} pt"

    def test_the_6x9_trim_carries_the_whole_example_inside_its_frame(self):
        generator = BookPDFGenerator(six_by_nine_book())
        page = generator.create_guide_page(150, 50, 50, 50)
        mask = dark(page)
        assert page.size == (1800, 2700)
        lines = read_lines(mask)
        assert len(lines) == 4
        assert lines[0]["states"] == ["empty"] * LENGTH
        finished = tuple(state == "filled" for state in lines[-1]["states"])
        assert "empty" not in lines[-1]["states"] and finished in placements()
        rows, cols = np.flatnonzero(mask.any(axis=1)), np.flatnonzero(mask.any(axis=0))
        left, top, right, bottom = frame_px(*page.size)
        assert left <= cols[0] and cols[-1] <= right
        assert top <= rows[0] and rows[-1] <= bottom
        reference = text_reference()
        sizes = [cap_height_points(mask, band, reference) for band in type_bands(mask)]
        assert min(sizes) >= FLOOR_PT
        assert occurrences(mask, probe(NEW_TITLE, face(TITLE_PX))) == 1
        # The clue digits hold the floor and the rules are the book's (thin
        # >= 0.25 mm, heavy = 2 x thin) on this trim too.
        digit_ref = digit_reference()
        for number, line in enumerate(lines, start=1):
            assert len(line["glyphs"]) == 2, f"step {number}: {len(line['glyphs'])} clue glyphs"
            for glyph in line["glyphs"]:
                points = glyph.shape[0] / digit_ref * POINTS_PER_INCH / BOOK_DPI
                assert points >= FLOOR_PT, f"step {number}: a clue digit is {points:.2f} pt"
        widths = lines[0]["rule_widths"]
        thin = min(widths)
        assert thin >= 0.25 / 25.4 * BOOK_DPI, f"the thin rule is {thin} px"
        heavy = 2 * thin
        assert widths == [heavy, heavy, thin, thin, thin, thin, heavy, heavy], widths

    @pytest.mark.parametrize(
        ("height_cm", "type_lines", "form"),
        [
            # 10 x 10 cm: only the short labels fit -- the title and the
            # four one-line labels ("1. The clue" .. "4. Solved").
            (10.0, 5, "short labels"),
            # 10 x 14 cm: the full captions fit without the explanation --
            # the title and the captions wrapped to 3, 3, 3 and 1 lines.
            (14.0, 11, "full captions alone"),
        ],
    )
    def test_the_10cm_trim_holds_10pt_in_its_fallback_forms(self, height_cm, type_lines, form):
        """CON-020 on the two fallback forms, at the minimum 10 cm width.

        The line count identifies the form measured, so the floor is shown on
        each form rather than on whichever one the page happened to pick. The
        title is set below 22 pt here (it is wider than a 10 cm measure); this
        test does not reach the clamp that keeps it at or above the body size,
        which no stored trim is narrow enough to engage.
        """
        page = BookPDFGenerator(ten_cm_wide_book(height_cm)).create_guide_page(
            999_999, 333_333, 333_333, 333_333
        )
        mask = dark(page)
        found = type_bands(mask)
        assert len(found) == type_lines, (
            f"10 x {height_cm:g} cm sets {len(found)} lines of type, not the "
            f"{type_lines} of the {form} form"
        )
        reference = text_reference()
        sizes = [cap_height_points(mask, band, reference) for band in found]
        assert min(sizes) >= FLOOR_PT, f"a line of type measures {min(sizes):.2f} pt"
        lines = read_lines(mask)
        assert len(lines) == 4
        digit_ref = digit_reference()
        for number, line in enumerate(lines, start=1):
            assert len(line["glyphs"]) == 2, f"step {number}: {len(line['glyphs'])} clue glyphs"
            for glyph in line["glyphs"]:
                points = glyph.shape[0] / digit_ref * POINTS_PER_INCH / BOOK_DPI
                assert points >= FLOOR_PT, f"step {number}: a clue digit is {points:.2f} pt"


# --------------------------------------------------------------------------
# AC-326
# --------------------------------------------------------------------------


class TestGuidePage_WorkedExampleLeavesPageCountAndParityUnchanged:
    """AC-326 — old guide page vs new: same page count, guide = page 1, parity kept."""

    def test_both_interiors_hold_the_same_number_of_pages(self, old_export, new_export):
        assert pdf_page_count(old_export) == pdf_page_count(new_export)
        # Guide, "Easy" divider, 3 puzzles, SOLUTIONS, one answer page.
        assert pdf_page_count(new_export) >= 7

    def test_the_guide_page_is_exactly_interior_page_1_in_each(self, old_pages, new_pages):
        generator = BookPDFGenerator(corpus_book("card-167"))
        assert same_page(old_pages[0], old_guide_page(generator, 3, 3, 0, 0))
        assert same_page(new_pages[0], generator.create_guide_page(3, 3, 0, 0))
        assert not same_page(old_pages[0], new_pages[0])
        # Page 2 is the same page in both: no guide page continues onto it.
        assert page_digest(old_pages[1]) == page_digest(new_pages[1])

    def test_every_later_page_is_the_same_page_with_the_same_parity(self, old_pages, new_pages):
        assert len(old_pages) == len(new_pages)
        for number in range(2, len(new_pages) + 1):
            assert page_digest(old_pages[number - 1]) == page_digest(new_pages[number - 1]), (
                f"interior page {number} differs between the two exports"
            )
        # Parity, observed: a right-hand (odd) page's drawing sits right of
        # the trim's middle by half the gutter/outside difference, a
        # left-hand one left of it.
        puzzles = 0
        for number, page in enumerate(new_pages, start=1):
            try:
                drawing = drawing_of(page)
            except ValueError:
                continue
            if drawing.rows != 20:
                continue
            puzzles += 1
            offset = (drawing.left + drawing.grid_right) / 2 - page.width / 2
            assert (offset > 0) == (number % 2 == 1), (
                f"interior page {number} is centred {offset:.1f} px off the middle"
            )
        assert puzzles == 3
