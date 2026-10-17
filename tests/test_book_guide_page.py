"""The guide page is "How to Solve Nonograms" with a worked example (CARD-167),
now a 2-page tutorial sourced from the owner's reference guide (CARD-201).

FR-041 (amended 2026-10-04), AC-324..AC-326 (CARD-167; ``TestGuidePage_TitledHowToSolveNonograms``
is the one survivor — the title it checks is unchanged by CARD-201, an owner
decision recorded in that card's Worktree notes). CARD-201's own card-level
acceptance criteria are AC-1..AC-8, one class each below (``TestGuidePage_CarriesAWorkedExampleOnOnePage``
and ``TestGuidePage_WorkedExampleLeavesPageCountAndParityUnchanged``, CARD-167's
own AC-325/AC-326 classes, are retired: their premise — the worked example is
on page 1, alone, and the guide is exactly interior page 1 — is no longer
true. AC-325's content is superseded by AC-2/AC-4 below; AC-326's by AC-5/AC-6
(the latter in ``tests/test_book_pdf_memory.py``); AC-8 below is the direct
replacement for AC-325's "pixel-identical worked example" half).

**Everything is read off pages.** The book is exported, its interior PDF read
back with ``tests.helpers.pdf_pages`` and its pages measured as pixels: a
title is found by searching the page for its own glyphs, a diagram by
rendering it afresh through the same project-wide painters
(:func:`~nonogram.admin.book_pdf_generator.example_line_layout`/
:func:`~nonogram.admin.book_pdf_generator.draw_example_line`,
:func:`~nonogram.admin.book_pdf_generator.guide_icon_layout`,
:func:`~nonogram.admin.book_pdf_generator._draw_pipeline_diagram`,
:func:`~nonogram.admin.book_pdf_generator._draw_difficulty_legend`) with this
file's own literal, written-out clue/length/fill/caption data and then
looking for that rendering on the page, and type sizes by measuring glyph
boxes. Every expected clue, length, filled/crossed cell set and verbatim
sentence below is **written out**, matching what
``docs/guides/how_to_solve_nonograms_v2.pdf`` and
``nonogram.admin.book_pdf_generator`` were read to contain while building
this card — not imported from the module under test, with the sole
exception of AC-8 (about the refactor of the painters themselves, so it
necessarily calls them) and the handful of purely mechanical sizing helpers
(``_guide_face``, ``type_px``, ``page_frame``, the two point-size constants)
no assertion here treats as "content".

**Why a diagram is checked by re-rendering it, not by decoding its pixels.**
A nonogram diagram with two or more adjacent filled cells draws no visible
rule between them (the same ink, "a heavy rule stays continuous across a
filled square" — :func:`draw_example_line`'s own docstring) — which is
exactly how a real puzzle page looks too, not a drawing defect. CARD-167's
own worked example sidestepped this by calibrating its column rules off its
*first* step, which it drew with every cell still undecided; none of
CARD-201's new diagrams have an undecided cell to calibrate from (several —
"Complete lines" chief among them — are entirely filled), so that technique
does not generalise to them. Rendering the same expected content through the
project's own already-tested painters and asking whether it appears on the
page (correlation for presence, exact pixel equality for AC-8's identity
claim) sidesteps decoding rules altogether and is no weaker a check: a wrong
clue, a wrong cell, or a wrong row order changes the rendered image and the
check fails.
"""

from __future__ import annotations

import itertools
from importlib import resources
from io import BytesIO
from typing import Dict, List, Optional, Tuple

import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont

from nonogram.admin.book_manager import Book, BookMetadata
from nonogram.admin.book_pdf_generator import (
    BookPDFGenerator,
    DifficultyLabel,
    ExampleStep,
    GUIDE_ASSUME_STEPS,
    GUIDE_TECHNIQUES_2,
    GuidePipelineStep,
    _draw_difficulty_legend,
    _draw_pipeline_diagram,
    _guide_face,
    _guide_rule_width,
    draw_example_line,
    example_line_layout,
    guide_icon_layout,
    interior_page_count,
    page_frame,
    type_px,
    wrap_words,
)

from tests.helpers.book_corpus import corpus_book, export_of, page_digest, puzzle
from tests.helpers.page_ink import drawing_of
from tests.helpers.pdf_pages import pdf_page_count, pdf_pages

# --------------------------------------------------------------------------
# What the acceptance criteria say, written out
# --------------------------------------------------------------------------

NEW_TITLE = "How to Solve Nonograms"
OLD_TITLE = "How to Use This Book"

#: Page 2's title (CARD-201).
TITLE_2 = "When the Puzzle Gets Harder"

#: The worked example's line (AC-325/AC-8): the clue 3 1 on six squares.
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
#: The pipeline/difficulty box painters letter in 14.4 pt (CARD-201's
#: ``DIVIDER_PT``-sized body face); mechanical sizing, not content.
BODY_PT = 11.0
LEADING_PT = 17.0

#: The first three words of each difficulty sentence
#: (``GUIDE_DIFFICULTY_LABELS``), written out rather than imported, as the
#: page would set them if it printed them. The owner's 2026-10-14 ruling
#: dropped those sentences from the printed page (CARD-221 fix 1) and
#: ``test_the_difficulty_legend_carries_its_three_labels_and_no_sentences``
#: looks for these to say so. Three words each, not one: a single word is a
#: small enough template to risk matching ink that is not it, and
#: ``wrap_words`` never breaks a word.
SENTENCE_OPENINGS = ("Squeezing and direct", "Needs deeper line", "Contradiction reasoning")

#: The size the guide page letters its body — and the pipeline diagram's own
#: labels — in, written out rather than imported, so the floor control below
#: separates the page's real size from the 6 pt stand-in regression.
GUIDE_BODY_POINTS = 11.0

#: The packaged face the guide page letters in since CARD-221, named the way
#: :mod:`nonogram.export.pdf` names its own package data and read through
#: :mod:`importlib.resources`, so this file still states the page's own lookup
#: a second time rather than importing it. It was
#: ``"/System/Library/Fonts/Arial.ttf"`` — the host path — until CARD-221.
FONT_PACKAGE = "nonogram.export.fonts"
FONT_RESOURCE = "DejaVuSans.ttf"
INK_THRESHOLD = 128

#: A row whose ink runs unbroken for longer than this is a ruled line.
RULE_RUN_PX = 60


def face(size_px: int) -> ImageFont.FreeTypeFont:
    """The face the guide page letters in, at ``size_px`` — the packaged one.

    One call, on every host (CARD-221). The Arial-by-path-then-Pillow ladder
    this reproduced was the page's own, and both ends of it are gone.
    """
    data = resources.files(FONT_PACKAGE).joinpath(FONT_RESOURCE).read_bytes()
    return ImageFont.truetype(BytesIO(data), size=size_px)


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


def ink_bands(mask: np.ndarray) -> List[Tuple[int, int]]:
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
    """The bands that are lines of type.

    Review cycle 1, F-4 (gating): a plain (unbordered) band with no ruled
    row at all is type, as before. A bordered box (``_draw_pipeline_diagram``'s
    box borders — and ``_draw_difficulty_box``'s own, until CARD-221 fix 1
    dropped that rule with the sentences it held) draws a border that
    touches every row of its own bounding area, which used to make
    ``is_ruled`` classify the WHOLE box — border, labels and sentences alike
    — as "ruled", silently dropping its interior text out of CON-020's floor
    check.

    Fixed by also looking *inside* an otherwise-ruled band for a genuinely
    bordered box's own structure and, when found, still checking its
    interior text — the border itself stays excluded (treated as a rule),
    but text drawn inside it is checked exactly like text anywhere else.
    ``drawn_bands`` (below) is intentionally left untouched: diagram look-up
    still needs the WHOLE box, border and text together, as one region to
    match a freshly rendered diagram against.

    **Why this does not just re-run ``is_ruled`` row by row.** A long box
    label at this page's own type size (e.g. "FOLLOW", "PROVED") can have a
    single row whose own glyphs' ink is contiguous for more than
    ``RULE_RUN_PX`` — ordinary letter shapes, not a rule — which briefly
    broke exactly that check (measured while fixing F-4): it carved one real
    line of label text into two row-fragments at that row, each then
    "measured" as if it were its own complete line, both nonsense values. A
    box's own border row needs no length threshold at all: it is, by
    construction, ink at *every single column* between its own left and
    right border strokes — something no line of text, however dense, does
    (there is always a blank margin before the first glyph and after the
    last, and gaps between words). So a border row is found structurally —
    first the box's own left/right border columns (ink on literally every
    row of the band), then any row that is 100% ink between a box's own pair
    of border columns — rather than by a run-length guess.
    """
    bands: List[Tuple[int, int]] = []
    for band in ink_bands(mask):
        if not is_ruled(mask, band):
            bands.append(band)
            continue
        top, bottom = band
        sub = mask[top : bottom + 1]
        border_cols = sub.all(axis=0)
        col_idx = np.flatnonzero(border_cols)
        if not col_idx.size:
            # No full-height vertical stroke at all -- not a bordered box,
            # just a dense diagram (e.g. a filled nonogram line). Unchanged
            # from before: the whole band stays excluded.
            continue

        # Group the full-height columns into contiguous strokes, then pair
        # them up left/right -- one pair per box (CARD-201's pipeline draws
        # 4 side-by-side boxes, so 4 pairs; the difficulty box draws 1).
        runs: List[Tuple[int, int]] = []
        start_c = prev_c = int(col_idx[0])
        for c in col_idx[1:]:
            c = int(c)
            if c == prev_c + 1:
                prev_c = c
            else:
                runs.append((start_c, prev_c))
                start_c = prev_c = c
        runs.append((start_c, prev_c))
        box_spans = list(zip(runs[0::2], runs[1::2]))

        def is_border_row(row_mask: np.ndarray) -> bool:
            for left_run, right_run in box_spans:
                lo, hi = left_run[1] + 1, right_run[0]
                if hi > lo and not row_mask[lo:hi].all():
                    return False
            return True

        interior = sub & ~border_cols
        start = None
        for offset, row in enumerate(range(top, bottom + 1)):
            border_row = is_border_row(sub[offset])
            has_interior_ink = interior[offset].any()
            if border_row or not has_interior_ink:
                if start is not None:
                    bands.append((start, row - 1))
                    start = None
            elif start is None:
                start = row
        if start is not None:
            bands.append((start, bottom))
    return bands


def drawn_bands(mask: np.ndarray) -> List[Tuple[int, int]]:
    """The bands that carry a ruled row: a diagram's own lines."""
    return [band for band in ink_bands(mask) if is_ruled(mask, band)]


def probe(text: str, font: ImageFont.ImageFont) -> np.ndarray:
    """``text``'s ink as a boolean mask cropped to its own box."""
    left, top, right, bottom = font.getbbox(text)
    scratch = Image.new("L", (right - left + 40, bottom - top + 40), 255)
    ImageDraw.Draw(scratch).text((20 - left, 20 - top), text, fill=0, font=font)
    mask = dark(scratch)
    rows, cols = np.flatnonzero(mask.any(axis=1)), np.flatnonzero(mask.any(axis=0))
    return mask[rows[0] : rows[-1] + 1, cols[0] : cols[-1] + 1]


def tight(mask: np.ndarray) -> np.ndarray:
    """``mask`` cropped tight to its own ink (``probe``'s crop, for any mask)."""
    rows, cols = np.flatnonzero(mask.any(axis=1)), np.flatnonzero(mask.any(axis=0))
    assert rows.size and cols.size, "a blank mask has no ink to crop to"
    return mask[rows[0] : rows[-1] + 1, cols[0] : cols[-1] + 1]


def diagram_mask(image: Image.Image) -> np.ndarray:
    """A freshly-rendered diagram's own ink, cropped tight (see ``tight``)."""
    return tight(dark(image))


def occurrences(page_mask: np.ndarray, template: np.ndarray, share: float = 0.9) -> int:
    """How many places on the page carry ``template``'s ink and little else.

    A window matches when at least ``share`` of the template's ink is inked on
    the page there (recall) *and* at least ``share`` of the page's ink inside
    the window is the template's (precision). Correlations by FFT, so every
    position of the page is tried. Neighbouring hits of one occurrence are
    merged by counting connected groups of matching positions.

    A small, feature-poor template (a single filled cell, say) can match many
    places inside *any* larger solid-black region on the page, so every call
    below restricts ``page_mask`` to the one band the content is expected at
    (``drawn_bands``'s own ordering) rather than searching the whole page.
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
    for top, bottom in ink_bands(hits):
        columns = np.flatnonzero(hits[top : bottom + 1].any(axis=0))
        groups += 1 + int((np.diff(columns) > 1).sum())
    return groups


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


#: A row at a line's foot holding less than this share of its busiest row's
#: ink is a descender row, not the body of the line.
TAIL_SHARE = 0.2


def baseline_row(counts: np.ndarray) -> int:
    """The 0-based row of a line's baseline, from its per-row ink counts."""
    rows = np.flatnonzero(counts >= TAIL_SHARE * counts.max())
    return int(rows[-1])


def cap_height_points(mask: np.ndarray, band: Tuple[int, int], reference: float) -> float:
    """A line of type's size in points, from its top to its baseline."""
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


def folio_reference() -> float:
    """A page number's top-to-baseline ink per em, in the page's own face.

    The folio (:func:`_draw_folio`) is the one mark a guide page sets in
    **digits alone**, and a digit does not reach the lowercase ascender
    :func:`text_reference`'s "Hdlk" probe measures to. Measured in the
    packaged face at a 400 px em: "Hdlk" inks 0.760 of the em down to its
    baseline and "1" only 0.730. So the folio — set at exactly CON-020's
    floor, ``FOLIO_PT`` = 10 pt, which is 31 px of digit on a 300 DPI page —
    reads 10.19 pt against its own probe and **9.79 pt** against the text
    probe, a false breach of the floor it sits exactly on.

    New in CARD-221 rather than changed: on Arial the two probes agreed to
    within a pixel ("Hdlk" 0.7175 against "1" 0.72), so one probe served for
    both and the folio measured 10.03 pt — inside the floor by 0.03 pt, by
    that face's own metrics rather than by anything this page does. The
    packaged face sets its ascenders above its cap height, as most faces do.
    """
    return top_to_baseline("1", face(REFERENCE_SIZE))


def page_lines(generator, page_number: int) -> Tuple[Image.Image, Dict[int, str]]:
    """A guide page, and the text of every line it sets **on the page itself**.

    Keyed by the row of the baseline each line is set on, so a band of ink
    can be measured against the extent of the glyphs that actually made it
    (CARD-221). A line's ink reaches from its own tallest glyph down to its
    own baseline, so "11 pt" is only recoverable from a band of ink when the
    probe it is divided by has that same extent: "agrees on" — a line the
    10 cm trim's page 2 wraps — tops out at x-height, and against an
    ascender-to-baseline probe it measures **8.21 pt** while being set at 11.
    One probe for the whole page was enough until CARD-221 only because no
    line of either guide page happened to lack an ascender when the page was
    lettered in Arial.

    Only the marks drawn straight onto the page are collected: a diagram is
    composed in its own image and pasted, so its own draw calls carry its own
    coordinates and would key a baseline this page never set. The two are
    told apart by the size of the surface each call draws on. The folio is
    skipped here as well — it is anchored on the frame's bottom edge rather
    than set on a line, and :func:`folio_band`/:func:`folio_reference` measure
    it.
    """
    frame = page_frame(generator.page_spec(page_number))
    original = ImageDraw.ImageDraw.text
    lines: Dict[int, str] = {}

    def spy(self, xy, text, fill=None, font=None, *args, **kwargs):
        surface = getattr(self, "_image", None)
        on_page = surface is not None and surface.size == (frame.width, frame.height)
        if on_page and font is not None and kwargs.get("anchor") in (None, "la"):
            ascent, _ = font.getmetrics()
            lines[int(round(xy[1])) + ascent] = str(text)
        return original(self, xy, text, fill, font, *args, **kwargs)

    ImageDraw.ImageDraw.text = spy
    try:
        page = generator.create_guide_page(
            999_999, 333_333, 333_333, 333_333, page_number=page_number
        )
    finally:
        ImageDraw.ImageDraw.text = original
    return page, lines


def line_reference(mask: np.ndarray, band: Tuple[int, int], lines: Dict[int, str]) -> Optional[float]:
    """The ink-to-baseline probe of the line that made ``band``, if known.

    ``None`` for a band no page-level line sets a baseline on — a pasted
    diagram's own ink — which the caller measures against the generic probe
    as before.
    """
    baseline = band[0] + baseline_row(mask[band[0] : band[1] + 1].sum(axis=1))
    for offset in (0, -1, 1):
        text = lines.get(baseline + offset)
        if text is not None and text.strip():
            return top_to_baseline(text, face(REFERENCE_SIZE))
    return None


def folio_band(bands: List[Tuple[int, int]], mask: np.ndarray, frame) -> int:
    """Which of ``bands`` is the folio: its index, asserted and not assumed.

    Structural rather than positional-by-faith. :func:`_draw_folio` anchors
    the page number ``"rb"``/``"lb"`` on the frame's own bottom edge at its
    own outer corner, so the folio's band is the last one and its last inked
    row is that edge — both asserted here, together with the ink sitting in
    the outer corner and being only a few digits wide, so a page that stops
    drawing a folio (or draws something else down there) fails this helper
    instead of quietly having one of its prose lines measured as digits.
    """
    index = len(bands) - 1
    top, bottom = bands[index]
    assert frame.bottom - 1 <= bottom <= frame.bottom, (
        f"the page's last band of ink runs to row {bottom}, and the folio is "
        f"anchored on the frame's own bottom edge at {frame.bottom}"
    )
    columns = np.flatnonzero(mask[top : bottom + 1].any(axis=0))
    width = int(columns.max() - columns.min() + 1)
    assert width <= 4 * (bottom - top + 1), (
        f"the band at the frame's bottom edge is {width} px wide, which is "
        "wider than a page number: it is not the folio"
    )
    assert columns.min() <= frame.left + width or columns.max() >= frame.right - width, (
        "the folio sits in the frame's own outer corner, and this band's ink "
        f"runs from {columns.min()} to {columns.max()} inside "
        f"{frame.left}..{frame.right}"
    )
    return index


def digit_reference() -> float:
    return top_to_baseline("31", ImageFont.load_default(size=REFERENCE_SIZE))


def gutter_glyph_points(layout, image: Image.Image, reference: float) -> List[float]:
    """The point size of every clue-digit glyph in ``image``'s own left gutter.

    ``image`` is a fresh render from :func:`example_line_layout`/
    :func:`draw_example_line`, so ``layout`` is already in hand: the grid's
    own left edge, in the *image's* coordinates, is the gap between
    ``layout``'s leftmost vertical line and the crop's own origin
    (``draw_example_line``'s own docstring: the image "starts at the
    drawing's left edge... minus a heavy rule of white", written out here
    rather than re-imported since it is the crop's documented contract, not
    an internal it hides). Left of that gap is the clue gutter.

    This does not reuse the project's own ``column_groups``-over-full-height
    rule-finder: a filled cell is ink the same full height as a rule, which
    is exactly why that approach needs a line with no filled cell to
    calibrate against (CARD-167's original worked example had one; none of
    CARD-201's new diagrams reliably do). The gutter has no such problem —
    its own border is read off by *rows* (always a true gap above and below
    the clue text, fill pattern or not), and the border columns it still
    carries are simply the outermost of the glyph groups found, dropped
    before measuring.
    """
    pad = layout.thick_rule
    xs = [line.position for line in layout.vertical_lines]
    left_origin = (layout.frame.left if layout.frame is not None else xs[0]) - pad
    grid_left = xs[0] - left_origin
    if grid_left <= 0:
        return []
    mask = dark(image)
    gutter = mask[:, :grid_left]
    width = gutter.shape[1]
    horizontal = column_groups(np.flatnonzero(gutter.sum(axis=1) >= 0.9 * width))
    assert len(horizontal) >= 2, "no clue box border found in the gutter"
    inner_top, inner_bottom = horizontal[0][-1] + 1, horizontal[-1][0] - 1
    core = gutter[inner_top : inner_bottom + 1]
    groups = column_groups(np.flatnonzero(core.any(axis=0)))[1:-1]
    points = []
    for group in groups:
        strip = core[:, group[0] : group[-1] + 1]
        rows = np.flatnonzero(strip.any(axis=1))
        points.append((rows[-1] - rows[0] + 1) / reference * POINTS_PER_INCH / BOOK_DPI)
    return points


def render_line(
    spec, clue: Tuple[int, ...], length: int, filled: frozenset = frozenset(), crossed: frozenset = frozenset()
):
    """One guide line through the project's own painters, layout and image both."""
    layout = example_line_layout(spec, clue, length)
    return layout, draw_example_line(layout, ExampleStep("", "", filled, crossed))


def render_icon(spec, filled: bool, crossed: bool) -> Image.Image:
    """One bare cell-state icon through :func:`guide_icon_layout`."""
    layout = guide_icon_layout(spec)
    return draw_example_line(
        layout,
        ExampleStep("", "", frozenset({0}) if filled else frozenset(), frozenset({0}) if crossed else frozenset()),
    )


def _boxed_difficulty_sentences(
    spec, labels, measure: int, text_font, text_size: int, leading: int
) -> Image.Image:
    """The difficulty box **as it was printed before CARD-221 fix 1**.

    ``_draw_difficulty_box``'s body, transcribed here rather than kept in
    the module under test: a ``measure``-wide bordered box, one column per
    label, each holding its name and then its one-sentence gloss wrapped to
    the column. The module no longer draws this and nothing should bring it
    back without a decision, so the only honest way to assert that the page
    does not carry it is to build it here and look for it. A second
    implementation of a drawing the source has deleted is exactly what
    CLAUDE.md asks for in place of re-deriving a value with the code under
    test — and it means the "no sentences on the page" claim fails loudly
    if the box returns, instead of passing because nobody draws it.
    """
    rule = _guide_rule_width(spec)
    pad = text_size
    gutter = pad
    column_w = (measure - 2 * pad - gutter * (len(labels) - 1)) // len(labels)
    bbox = text_font.getbbox("Mg")
    name_h = bbox[3] - bbox[1]
    columns = [[label.name, *wrap_words(label.text, text_font, column_w)] for label in labels]
    body_lines = max(len(lines) - 1 for lines in columns)
    height = pad * 2 + name_h + (pad // 2 + body_lines * leading if body_lines else 0)
    canvas = Image.new("RGB", (measure, height), "white")
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, measure - 1, height - 1), outline="black", width=rule)
    x = pad
    for lines in columns:
        draw.text((x, pad), lines[0], font=text_font, fill="black")
        y = pad + name_h + pad // 2
        for line in lines[1:]:
            draw.text((x, y), line, font=text_font, fill="black")
            y += leading
        x += column_w + gutter
    return canvas


def diagram_at(page_mask: np.ndarray, drawn: List[Tuple[int, int]], index: int, template: np.ndarray) -> int:
    """How many times ``template`` occurs inside ``drawn[index]``'s own band."""
    top, bottom = drawn[index]
    return occurrences(page_mask[top : bottom + 1], template)


def placements() -> List[Tuple[bool, ...]]:
    """Every line of :data:`LENGTH` squares whose runs are :data:`CLUE`."""
    found = []
    for line in itertools.product((False, True), repeat=LENGTH):
        runs = tuple(len(list(group)) for filled, group in itertools.groupby(line) if filled)
        if runs == CLUE:
            found.append(line)
    return found


# --------------------------------------------------------------------------
# AC-324 (CARD-167; survives CARD-201 unchanged — an owner decision)
# --------------------------------------------------------------------------


class TestGuidePage_TitledHowToSolveNonograms:
    """AC-324 — page 1's title reads "How to Solve Nonograms"; the old title is nowhere.

    **CARD-201 note.** The title text and its position (``frame.top``) are
    unchanged by this card (an owner-decision flag, resolved in this card's
    Worktree notes in favour of keeping it) — only what is drawn beneath it
    changed, which this class never looks at.
    """

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
# AC-1 — the guide section is exactly 2 pages
# --------------------------------------------------------------------------


def old_style_total(puzzle_count: int, dividers: int = None, pages: int = None, answers: int = None) -> int:
    """``interior_page_count``'s own formula with the pre-CARD-201 leading
    term (1 guide page, not 2) — written out as the independent "before"
    this AC's "+1" claim is checked against, not derived from the function
    under test.
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
        assert interior_page_count(
            count, pages, answers, dividers, toc_pages=0
        ) == old_style_total(count, dividers, pages, answers) + 1

    def test_the_exported_interior_opens_with_both_guide_pages_then_the_first_puzzle_or_divider(self):
        book_puzzles = [puzzle("card201-1", 10, 10, 3, "easy", "Picture 1")]
        export = export_of(BookPDFGenerator(corpus_book("card-201-ac1")), book_puzzles)
        pages = pdf_pages(export)
        assert len(pages) == interior_page_count(1)

        page_1, page_2, page_3 = dark(pages[0]), dark(pages[1]), dark(pages[2])
        assert occurrences(page_1, probe(NEW_TITLE, face(TITLE_PX))) == 1, (
            "interior page 1 is not titled the guide's own title"
        )
        assert occurrences(page_2, probe(TITLE_2, face(TITLE_PX))) == 1, (
            "interior page 2 is not titled the guide's own page-2 title"
        )
        assert occurrences(page_3, probe(NEW_TITLE, face(TITLE_PX))) == 0
        assert occurrences(page_3, probe(TITLE_2, face(TITLE_PX))) == 0, (
            "interior page 3 still carries a guide title: the guide is more than 2 pages"
        )


# --------------------------------------------------------------------------
# AC-2 — page 1: the basic rule, the three cell states, start with certainty
# --------------------------------------------------------------------------


class TestGuidePage_PageOneCarriesTheBasicTechniques:
    """AC-2 — page 1 carries the basic rule, the 3 cell states and 3 techniques.

    Every diagram is checked in the order :func:`create_guide_page` draws it
    (this class's own ``PAGE_ONE_...`` constants, written out — see the
    module docstring for why a diagram is checked by re-rendering and
    matching rather than by decoding its pixels).
    """

    @staticmethod
    @pytest.fixture(scope="class")
    def generator() -> BookPDFGenerator:
        return BookPDFGenerator(corpus_book("card-201-ac2"))

    @staticmethod
    @pytest.fixture(scope="class")
    def spec(generator):
        return generator.page_spec(1)

    @staticmethod
    @pytest.fixture(scope="class")
    def page_mask(generator) -> np.ndarray:
        return dark(generator.create_guide_page(4, 2, 1, 1, page_number=1))

    @staticmethod
    @pytest.fixture(scope="class")
    def drawn(page_mask) -> List[Tuple[int, int]]:
        found = drawn_bands(page_mask)
        assert len(found) == 9, (
            f"page 1 draws {len(found)} diagrams, not the 9 this class expects: "
            "1 basic-rule line, 3 cell-state icons, 1 complete-line, 3 squeeze "
            "rows, 1 mark-spaces line"
        )
        return found

    def test_the_basic_rule_is_3_2_1_on_8_squares_filled_and_crossed_as_the_guide_describes(
        self, spec, page_mask, drawn
    ):
        _, image = render_line(spec, (3, 2, 1), 8, frozenset({0, 1, 2, 4, 5, 7}), frozenset({3, 6}))
        assert diagram_at(page_mask, drawn, 0, diagram_mask(image)) == 1

    @pytest.mark.parametrize(
        ("index", "filled", "crossed"),
        [(1, False, False), (2, True, False), (3, False, True)],
    )
    def test_the_three_cell_state_icons_are_unknown_filled_and_empty_in_that_order(
        self, spec, page_mask, drawn, index, filled, crossed
    ):
        image = render_icon(spec, filled, crossed)
        assert diagram_at(page_mask, drawn, index, diagram_mask(image)) == 1

    def test_complete_lines_fills_every_one_of_10_squares(self, spec, page_mask, drawn):
        _, image = render_line(spec, (10,), 10, frozenset(range(10)), frozenset())
        assert diagram_at(page_mask, drawn, 4, diagram_mask(image)) == 1

    @pytest.mark.parametrize(
        ("index", "filled"),
        [
            (5, frozenset(range(8))),
            (6, frozenset(range(2, 10))),
            (7, frozenset(range(2, 8))),
        ],
    )
    def test_squeeze_from_both_ends_pushes_left_then_right_then_keeps_the_certain_overlap(
        self, spec, page_mask, drawn, index, filled
    ):
        _, image = render_line(spec, (8,), 10, filled, frozenset())
        assert diagram_at(page_mask, drawn, index, diagram_mask(image)) == 1

    def test_mark_spaces_crosses_the_cells_beside_a_completed_block(self, spec, page_mask, drawn):
        _, image = render_line(spec, (3,), 8, frozenset({2, 3, 4}), frozenset({1, 5}))
        assert diagram_at(page_mask, drawn, 8, diagram_mask(image)) == 1

    def test_every_diagram_is_drawn_at_the_books_own_cell_pitch(self, generator, spec, page_mask, drawn):
        """"at the book's own cell pitch" (AC-2): the same pitch a real puzzle
        page prints, measured independently off a real one.
        """
        corpus = [puzzle("card201-ac2-cell", 20, 20, 6, "easy", "Picture")]
        export = export_of(generator, corpus)
        pages = pdf_pages(export)
        book_cell_px = None
        for page in pages:
            try:
                drawing = drawing_of(page)
            except ValueError:
                continue
            if drawing.rows == 20:
                book_cell_px = drawing.cell
                break
        assert book_cell_px is not None, "no 20-row puzzle page found to measure the book's cell"

        _, complete_image = render_line(spec, (10,), 10, frozenset(range(10)), frozenset())
        diagram_width = diagram_mask(complete_image).shape[1]
        # 10 cells plus the frame's own two heavy rules either side (roughly
        # 2 cells' worth at this book's rule widths) — a loose bound, since
        # this test asks only that the diagram is at THIS book's pitch, not
        # that it reproduces the frame's own exact width to the pixel.
        assert 9.5 * book_cell_px <= diagram_width <= 12.5 * book_cell_px, (
            f"a 10-cell diagram is {diagram_width} px wide; this book's own "
            f"cell is {book_cell_px:.1f} px"
        )


# --------------------------------------------------------------------------
# Review cycle 3, F-21 — a bare_level 2 fallback must keep the cell-state
# headings even though it drops their pictures
# --------------------------------------------------------------------------


class TestGuidePage_CellStateHeadingsSurviveBareLevel2:
    """Review cycle 3, F-21 (gating) — `create_guide_page`'s cell-state block
    used an all-or-nothing `if bare_level >= 2: pass else: <heading AND
    picture>`, dropping "Unknown"/"Filled"/"Empty" together with their
    pictures. That contradicts the method's own docstring for `bare_level 2`
    ("the heading alone still names Unknown/Filled/Empty") and this card's
    own Fix-1 Worktree notes ("Owner decision 2"), and it is not
    hypothetical: that same note says a 10 x 10 cm square needs exactly
    this level on page 1, so this fires on a trim already in this project's
    named stored-trim set. The sibling `technique()` closure one entry later
    in the same method gets this right (heading unconditional, only the
    diagram gated by its own `draw_diagram` flag) — the fix makes the
    cell-state block follow the same shape.

    Forced with :func:`ten_cm_wide_book` at the minimum 10 cm height (the
    exact "10 x 10 cm square" the card's own notes name) and the largest
    counts the book prints, so nothing here fits more loosely than what
    this review found. Content is matched by rendering each word through
    the same face the page itself letters in and finding it by correlation
    (:func:`probe`/:func:`occurrences`, already used elsewhere in this file
    for exactly this purpose) rather than trusted at a fixed band index:
    at this trim one of the page's own diagrams (the basic-rule line) draws
    small enough that its border's longest run falls under this module's
    `RULE_RUN_PX`-equivalent heuristics in the sibling type-measuring
    module and can be miscounted as a line of type — observed while
    building this test — so a position-based assertion would have been
    fragile exactly where this finding lives; content-matching sidesteps it
    entirely.
    """

    @staticmethod
    @pytest.fixture(scope="class")
    def generator() -> BookPDFGenerator:
        return BookPDFGenerator(ten_cm_wide_book(MIN_TRIM_CM))

    @staticmethod
    @pytest.fixture(scope="class")
    def spec(generator):
        return generator.page_spec(1)

    @staticmethod
    @pytest.fixture(scope="class")
    def page_mask(generator) -> np.ndarray:
        return dark(
            generator.create_guide_page(999_999, 333_333, 333_333, 333_333, page_number=1)
        )

    def test_bare_level_2_really_drops_the_cell_state_pictures_here(self, spec, page_mask):
        """Negative control, checked first: proves this trim genuinely
        reaches `bare_level 2` (no cell-state icon is drawn at all), so the
        heading checks below are evidence of F-21's fix, not of a form
        roomy enough to draw everything anyway.
        """
        unknown_icon = diagram_mask(render_icon(spec, False, False))
        filled_icon = diagram_mask(render_icon(spec, True, False))
        empty_icon = diagram_mask(render_icon(spec, False, True))
        bands = drawn_bands(page_mask)
        hits = sum(
            occurrences(page_mask[top : bottom + 1, :], icon)
            for top, bottom in bands
            for icon in (unknown_icon, filled_icon, empty_icon)
        )
        assert hits == 0, (
            f"a cell-state icon was found {hits} time(s) on page 1 at the "
            "10 cm square trim -- this trim must drop every cell-state "
            "picture (bare_level 2) for the heading checks below to be "
            "testing what F-21 found"
        )

    @pytest.mark.parametrize("heading", ["Unknown", "Filled", "Empty"])
    def test_the_cell_state_heading_survives_with_its_picture_dropped(self, page_mask, heading):
        template = probe(heading, face(BODY_PX))
        bands = ink_bands(page_mask)
        hits = sum(occurrences(page_mask[top : bottom + 1, :], template) for top, bottom in bands)
        assert hits == 1, (
            f"{heading!r} was found {hits} time(s) on page 1 at the 10 cm "
            "square trim (bare_level 2) -- review cycle 3's F-21: the "
            "heading alone must survive even with its picture dropped, the "
            "same way create_guide_page's own docstring already promised"
        )


# --------------------------------------------------------------------------
# AC-3 — page 2: region splitting, arrangement comparison, the assume
# pipeline, the difficulty-label box
# --------------------------------------------------------------------------


class TestGuidePage_PageTwoCarriesTheHarderTechniquesAndDifficultyLegend:
    """AC-3 — page 2 carries the region split, the comparison, the pipeline
    and the difficulty legend.

    Named ``...AndDifficultyBox``, "its 3 sentences verbatim", until
    CARD-221 fix 1: the owner's 2026-10-14 ruling drops those sentences and
    the rule that boxed them, and the class is renamed rather than left
    naming a drawing the page no longer makes.
    """

    @staticmethod
    @pytest.fixture(scope="class")
    def generator() -> BookPDFGenerator:
        return BookPDFGenerator(corpus_book("card-201-ac3"))

    @staticmethod
    @pytest.fixture(scope="class")
    def spec(generator):
        return generator.page_spec(2)

    @staticmethod
    @pytest.fixture(scope="class")
    def page_mask(generator) -> np.ndarray:
        return dark(generator.create_guide_page(4, 2, 1, 1, page_number=2))

    @staticmethod
    @pytest.fixture(scope="class")
    def drawn(page_mask) -> List[Tuple[int, int]]:
        found = drawn_bands(page_mask)
        assert len(found) == 11, (
            f"page 2 draws {len(found)} diagrams, not the 11 this class "
            "expects: 2 region-split rows, 4 arrangement-comparison rows, "
            "the pipeline and the original 4-step worked example (AC-8's "
            "own content, recapped here). **12 until CARD-221 fix 1**, when "
            "the difficulty box still had a rule around it and counted as a "
            "drawing; its three labels are a line of type now, so they are "
            "in `type_bands` instead and the four worked-example rows have "
            "moved up one index"
        )
        return found

    def test_page_2_is_titled_when_the_puzzle_gets_harder(self, page_mask):
        title = type_bands(page_mask)[0]
        assert occurrences(page_mask[title[0] - 5 : title[1] + 6], probe(TITLE_2, face(TITLE_PX))) == 1

    @pytest.mark.parametrize(
        ("index", "crossed"),
        [(0, frozenset({3, 5})), (1, frozenset({3, 4, 5}))],
    )
    def test_the_region_split_rules_out_cells_the_remaining_run_cannot_reach(
        self, spec, page_mask, drawn, index, crossed
    ):
        _, image = render_line(spec, (2, 3), 10, frozenset(), crossed)
        assert diagram_at(page_mask, drawn, index, diagram_mask(image)) == 1

    @pytest.mark.parametrize(
        ("index", "filled"),
        [
            (2, frozenset({0, 1, 2})),
            (3, frozenset({1, 2, 3})),
            (4, frozenset({2, 3, 4})),
            (5, frozenset({2})),
        ],
    )
    def test_the_arrangement_comparison_shows_three_placements_then_what_they_agree_on(
        self, spec, page_mask, drawn, index, filled
    ):
        """Review cycle 1, F-1 (gating): this used to pin a clue=(3,),
        length=10 example showing only 3 of its 8 legal placements and
        concluding cell 4 was "certainly empty in every arrangement" — false
        (starts 2, 3 and 4, none of them shown, all cover cell 4). Fixed to
        clue=(3,), length=5, where a run of 3 has exactly 3 legal placements
        — the three rows pinned here (starts 0, 1, 2) are literally ALL of
        them, not a sample — and the fourth row is the one cell every one of
        those 3 agrees on. See
        test_the_arrangement_comparison_is_verified_against_every_legal_placement
        below for the brute-force cross-check, and the matching comment on
        ``GUIDE_TECHNIQUES_2`` in ``book_pdf_generator.py``.
        """
        _, image = render_line(spec, (3,), 5, filled, frozenset())
        assert diagram_at(page_mask, drawn, index, diagram_mask(image)) == 1

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

    def test_the_assume_follow_breaks_proved_pipeline_draws_its_four_boxes_in_order(
        self, generator, spec, page_mask, drawn
    ):
        body_size = type_px(BODY_PT, generator.dpi)
        text_font = _guide_face(body_size)
        steps = (
            GuidePipelineStep("ASSUME", "square"),
            GuidePipelineStep("FOLLOW", "dots"),
            GuidePipelineStep("BREAKS", "bang"),
            GuidePipelineStep("PROVED", "cross"),
        )
        image = _draw_pipeline_diagram(spec, steps, text_font, body_size)
        assert diagram_at(page_mask, drawn, 6, diagram_mask(image)) == 1

    def test_the_last_pipeline_box_has_a_complete_unclipped_border(self, generator, spec):
        """Review cycle 1, F-3 (gating): the last box's right border used to
        be drawn at ``x + box_w``, exactly the canvas's pixel width — one
        column past the last valid pixel, so Pillow clipped it and "PROVED"
        shipped with no visible right border; every earlier box's right
        border landed 1px into the arrow gutter instead of on the box. This
        renders the diagram directly (not through the full guide page) and
        pixel-checks every box for a complete, un-clipped rectangle on all 4
        sides, confirming the fix rather than assuming it.
        """
        body_size = type_px(BODY_PT, generator.dpi)
        text_font = _guide_face(body_size)
        steps = (
            GuidePipelineStep("ASSUME", "square"),
            GuidePipelineStep("FOLLOW", "dots"),
            GuidePipelineStep("BREAKS", "bang"),
            GuidePipelineStep("PROVED", "cross"),
        )
        image = _draw_pipeline_diagram(spec, steps, text_font, body_size)
        mask = dark(image)
        height, width = mask.shape

        # A column where every single row is ink can only be a box's left or
        # right vertical border (full height) -- the arrows, arrowheads and
        # icons never reach every row, measured directly rather than assumed.
        full_height_cols = [c for c in range(width) if mask[:, c].all()]
        runs: List[Tuple[int, int]] = []
        start = prev = None
        for c in full_height_cols:
            if start is None:
                start = prev = c
            elif c == prev + 1:
                prev = c
            else:
                runs.append((start, prev))
                start = prev = c
        if start is not None:
            runs.append((start, prev))

        assert len(runs) == 2 * len(steps), (
            f"expected {2 * len(steps)} full-height border strokes (left+right "
            f"of each of {len(steps)} boxes), found {len(runs)}: {runs}"
        )
        # The last box's right border is the canvas's own last column -- not
        # clipped off the edge, the exact defect F-3 fixed.
        assert runs[-1][1] == width - 1, (
            f"last box's right border ends at column {runs[-1][1]}, not the "
            f"canvas's last column {width - 1} -- it is being clipped"
        )
        # Every box is a complete rectangle: its top and bottom rows are
        # solid ink between its own two border strokes, not just two
        # disconnected vertical lines.
        for left, right in zip(runs[0::2], runs[1::2]):
            assert mask[0, left[0] : right[1] + 1].all(), "a box's top border has a gap"
            assert mask[height - 1, left[0] : right[1] + 1].all(), "a box's bottom border has a gap"

    def test_the_difficulty_legend_carries_its_three_labels_and_no_sentences(
        self, generator, spec, page_mask
    ):
        """What page 2 says about the difficulty labels, after CARD-221 fix 1.

        **This test was the xfail that carried that card's first open
        block.** Until the owner ruled (2026-10-14) it asserted the box's
        three sentences and was expected to fail: lettering the interior in
        the packaged face made page 2's captions form 4 px too tall for the
        Book 1 sheet (3192 px against a frame bottom of 3188), which dropped
        the whole page a fallback level and cost the reader the worked
        example's four step explanations and both technique notes as well.
        The owner's ruling drops the three sentences instead — 234 px bought
        against a 4 px deficit, so everything else on the page stays — and
        CARD-229 moves the difficulty legend into the guide's key strip,
        which is why this block and not another.

        So the claim is now the new fact, in both directions: the three
        **names** print, as a legend with no rule around it
        (``_draw_difficulty_legend``, whose own docstring says why the rule
        went with the sentences), and the bordered sentence box that used to
        stand here prints **nowhere on the page**. The sentences themselves
        are still carried by ``GUIDE_DIFFICULTY_LABELS`` for CARD-229 and
        still shown by the Finalise screen's preview, so "the page does not
        print them" is a claim that needs asserting rather than assuming.
        """
        frame = page_frame(spec)
        measure = frame.right - frame.left
        body_size = type_px(BODY_PT, generator.dpi)
        text_font = _guide_face(body_size)
        labels = (
            DifficultyLabel("EASY", "Squeezing and direct deductions are enough from start to finish."),
            DifficultyLabel(
                "MEDIUM",
                "Needs deeper line logic and may need contradiction for part of the grid.",
            ),
            DifficultyLabel("HARD", "Contradiction reasoning is needed through much of the grid."),
        )
        legend = _draw_difficulty_legend(labels, measure, text_font, body_size)
        # Searched over the whole page rather than inside one of `drawn`'s
        # bands: with its rule gone the legend is a line of **type**, so it
        # is no longer one of the page's diagrams at all (see the `drawn`
        # fixture's own count). Three words at their own column positions
        # are a specific enough template for `occurrences`' 0.9 precision
        # and recall on a page of 11 pt text.
        assert occurrences(page_mask, diagram_mask(legend)) == 1

        # And the other half, in two forms, because one of them is not
        # enough. **The drawing**: the bordered box, built here rather than
        # imported — one wrapped sentence per column, exactly as
        # `_draw_difficulty_box` drew it until this card — so a page that
        # went back to the old box fails here.
        boxed = _boxed_difficulty_sentences(
            spec, labels, measure, text_font, body_size, type_px(LEADING_PT, generator.dpi)
        )
        assert occurrences(page_mask, diagram_mask(boxed)) == 0, (
            "the bordered box of difficulty sentences is on the page: the "
            "owner's 2026-10-14 ruling dropped it, and the 4 px the page "
            "was over by have come back"
        )
        # **The words**: set in the page's own body face and looked for
        # anywhere on it, so a sentence redrawn in any other arrangement —
        # unruled, re-wrapped, one column or three — fails here too. Found
        # while mutating: a mutant that printed the glosses under the names
        # with no rule around them slipped past the template above, which
        # only knows the old drawing. Three words each: a single word is a
        # small enough template to risk matching ink that is not it, and
        # `wrap_words` never breaks a word, so the first three of a
        # sentence stay together on any measure wide enough to hold them.
        for opening in SENTENCE_OPENINGS:
            assert occurrences(page_mask, probe(opening, face(BODY_PX))) == 0, (
                f"page 2 prints {opening!r}: the difficulty sentences are "
                "back on the page the owner's ruling took them off"
            )

    def test_a_wrong_difficulty_label_does_not_match(self, generator, spec, page_mask):
        """The comparison has teeth: change one word and the match is gone.

        CARD-221 fix 1 re-aimed this from the sentences to the labels, which
        is where the verbatim claim lives now — a negative control that
        outlived its subject would have been deleted in the same commit as
        the thing it tested, and this one still has one.
        """
        frame = page_frame(spec)
        measure = frame.right - frame.left
        body_size = type_px(BODY_PT, generator.dpi)
        text_font = _guide_face(body_size)
        labels = (
            DifficultyLabel("EASY", "Squeezing and direct deductions are enough from start to finish."),
            DifficultyLabel("MEDIUM", "This sentence was never on the page."),
            DifficultyLabel("HARD", "Contradiction reasoning is needed through much of the grid."),
        )
        same = _draw_difficulty_legend(labels, measure, text_font, body_size)
        assert occurrences(page_mask, diagram_mask(same)) == 1, (
            "the legend prints names only, so changing a *sentence* must "
            "not change what is drawn — if this fails the sentences are "
            "back on the page"
        )

        wrong = (
            DifficultyLabel("EASY", labels[0].text),
            DifficultyLabel("MEDIUM", labels[1].text),
            DifficultyLabel("HARDER", labels[2].text),
        )
        image = _draw_difficulty_legend(wrong, measure, text_font, body_size)
        assert occurrences(page_mask, diagram_mask(image)) == 0

    def test_the_new_drawing_routines_tolerate_a_sizeless_fallback_face(self, spec):
        """Review cycle 1, F-2 (gating): ``_draw_pipeline_diagram`` and
        ``_draw_difficulty_legend`` must not read a size off the face they
        are handed.

        **What made that a live crash is gone (CARD-221).** ``_guide_face``
        used to be able to return an "unsized" face — no ``.size`` attribute
        at all — whenever Arial was not found *and* Pillow was older than
        10.1, a combination ``pyproject.toml``'s unbounded ``Pillow>=10.0``
        floor still permits; both routines read
        ``label_font.size``/``text_font.size`` directly and would have raised
        ``AttributeError`` the instant either ran on such a host. Since that
        card ``_guide_face`` returns the packaged face at the asked-for size
        on every host, so no face it can return lacks ``.size`` and the
        host-starvation route to this crash no longer exists.

        The test stays, and its claim is narrowed to what it always actually
        measured: these two routines take the size as a parameter and never
        read it off the font, so they work with **any** face-shaped object
        the module might hand them. It was never reproducible by starving
        Pillow of Arial anyway (this project's Pillow is >= 10.1): a stand-in
        face that genuinely has no ``.size`` is used instead — every method a
        real one has, just no ``.size``.

        Negative control, so this test has teeth: ``sizeless.size`` itself
        raises ``AttributeError`` below, proving the stand-in really lacks
        the attribute the old code crashed on — if a future edit
        reintroduced ``font.size`` inside either routine, this test would
        fail with that same ``AttributeError`` instead of passing silently.
        """

        class _SizelessFace:
            """Delegates every method to a real font except ``.size``."""

            def __init__(self, real):
                object.__setattr__(self, "_real", real)

            def __getattr__(self, name):
                if name == "size":
                    raise AttributeError("'_SizelessFace' object has no attribute 'size'")
                return getattr(object.__getattribute__(self, "_real"), name)

        real_font = _guide_face(type_px(BODY_PT, BOOK_DPI))
        sizeless = _SizelessFace(real_font)
        with pytest.raises(AttributeError):
            _ = sizeless.size  # the negative control: this double has teeth

        steps = (
            GuidePipelineStep("ASSUME", "square"),
            GuidePipelineStep("FOLLOW", "dots"),
            GuidePipelineStep("BREAKS", "bang"),
            GuidePipelineStep("PROVED", "cross"),
        )
        pipeline_image = _draw_pipeline_diagram(spec, steps, sizeless, type_px(BODY_PT, BOOK_DPI))
        assert pipeline_image.size[0] > 0 and pipeline_image.size[1] > 0

        labels = (
            DifficultyLabel("EASY", "Squeezing and direct deductions are enough from start to finish."),
            DifficultyLabel(
                "MEDIUM",
                "Needs deeper line logic and may need contradiction for part of the grid.",
            ),
            DifficultyLabel("HARD", "Contradiction reasoning is needed through much of the grid."),
        )
        frame = page_frame(spec)
        measure = frame.right - frame.left
        legend_image = _draw_difficulty_legend(
            labels, measure, sizeless, type_px(BODY_PT, BOOK_DPI)
        )
        assert legend_image.size[0] > 0 and legend_image.size[1] > 0


# --------------------------------------------------------------------------
# AC-4 — CON-020's 10 pt floor on both pages, at every stored trim
# --------------------------------------------------------------------------


class TestGuidePage_BothPagesHoldTheTypeFloorAtEveryStoredTrim:
    """AC-4 — every line of type, and a representative sample of diagram
    clue digits (one 1-digit, one 2-digit and one 3-digit clue), hold
    CON-020's 10 pt floor on both guide pages, at the three trims this
    project's own corpus already exercises the guide page at: Book 1, 6x9
    and the narrowest supported (10 cm) trim.

    Exhaustively re-measuring every clue digit of every diagram at every
    trim would reassert the same per-length pitch repeatedly (the floor is a
    property of the trim and the face, not of which particular clue is
    drawn) — the three clue arities below (1, 2 and 3 digits) are this
    page's only distinct shapes, so one of each is the floor's full surface.
    """

    @pytest.mark.parametrize(
        ("generator_factory", "page_numbers"),
        [
            (lambda: BookPDFGenerator(corpus_book("card-201-ac4-book1")), (1, 2)),
            (lambda: BookPDFGenerator(six_by_nine_book()), (1, 2)),
            (lambda: BookPDFGenerator(ten_cm_wide_book(20.0)), (1, 2)),
        ],
        ids=["book1", "6x9", "10cm-wide"],
    )
    def test_every_line_of_type_holds_10pt_on_both_pages(self, generator_factory, page_numbers):
        generator = generator_factory()
        reference = text_reference()
        digits = folio_reference()
        for page_number in page_numbers:
            page, lines = page_lines(generator, page_number)
            mask = dark(page)
            found = type_bands(mask)
            assert found, f"page {page_number} carries no type at all"
            # Each band against the probe whose extent its own glyphs have
            # (CARD-221): the line's own text where the page set one, the
            # folio's digits where it anchored the page number, and the
            # generic ascender-to-baseline probe for a pasted diagram's ink.
            folio = folio_band(found, mask, page_frame(generator.page_spec(page_number)))
            sizes = []
            for index, band in enumerate(found):
                if index == folio:
                    probe_ratio = digits
                else:
                    probe_ratio = line_reference(mask, band, lines) or reference
                sizes.append(cap_height_points(mask, band, probe_ratio))
            assert min(sizes) >= FLOOR_PT, (
                f"page {page_number}: a line of type measures {min(sizes):.2f} pt"
            )

    @pytest.mark.parametrize(
        ("generator_factory",),
        [
            (lambda: BookPDFGenerator(corpus_book("card-201-ac4-digits-book1")),),
            (lambda: BookPDFGenerator(six_by_nine_book()),),
            (lambda: BookPDFGenerator(ten_cm_wide_book(20.0)),),
        ],
        ids=["book1", "6x9", "10cm-wide"],
    )
    def test_a_1_2_and_3_digit_clue_each_hold_10pt_on_each_page(self, generator_factory):
        generator = generator_factory()
        digit_ref = digit_reference()
        # (page_number, clue, length) — one 1-digit, one 2-digit (page 1's
        # "Complete lines", clue 10) and one 3-digit (page 1's basic rule,
        # clue 3 2 1) clue.
        for page_number, clue, length in ((1, (3,), 8), (1, (10,), 10), (1, (3, 2, 1), 8), (2, (3,), 10)):
            spec = generator.page_spec(page_number)
            layout, image = render_line(spec, clue, length)
            points = gutter_glyph_points(layout, image, digit_ref)
            assert points, f"page {page_number}, clue {clue}: no clue glyph found"
            assert min(points) >= FLOOR_PT, (
                f"page {page_number}, clue {clue}: a clue digit measures {min(points):.2f} pt"
            )

    def test_a_regression_shrinking_a_boxs_label_text_is_still_caught_by_the_floor_check(self):
        """Review cycle 1, F-4 (gating), negative control. Before the fix,
        ``type_bands`` classified a bordered box's ENTIRE bounding area --
        border, labels and sentences alike -- as "ruled" (because its border
        touches every row) and excluded it wholesale, so a regression
        shrinking a box's own label text below CON-020's 10pt floor would
        NOT have been caught here, despite that being this test's one
        stated job (F-4's exact finding).

        **Re-aimed from the difficulty box to the pipeline diagram by
        CARD-221 fix 1.** The box this was written against no longer exists:
        the owner's 2026-10-14 ruling dropped the difficulty sentences and
        the rule that held them, so the guide's remaining bordered drawing
        with text inside it is ``_draw_pipeline_diagram``'s four boxes. The
        control is pointed there rather than retired, because the
        guarantee it holds is about the **classifier** and the page still
        draws a thing that can hide type behind a border. Keeping it aimed
        at a drawing the module had stopped making would have been the
        quieter failure of the two: a green negative control over a shape
        nothing prints.

        Both sides, so the instrument is shown to discriminate rather than
        only to report "below the floor": the same diagram lettered at the
        6 pt stand-in regression (never shipped —
        :data:`~nonogram.admin.book_pdf_generator.GUIDE_BODY_PT` is
        untouched) measures below CON-020's floor, and lettered at the
        page's own 11 pt it measures above it.

        **It measures with the generic ``text_reference`` probe on purpose,
        and that understates** (review cycle 1, F-008). A pipeline label is
        caps with no ascender, so an ascender-to-baseline probe recovers it
        small — the opposite direction from :func:`line_reference` and
        :func:`folio_reference`, which exist because an under-stated probe
        over-states a *size*. Here the error is the safe way round: it
        makes the floor check stricter, never more lenient. Measured on the
        real diagram at this trim: 11.05 pt at the page's own 11 pt against
        a 10.0 pt floor, so the margin this control runs on is 1.05 pt. A
        later card tightening CON-020 should read that 1.05 pt as probe
        slack rather than as headroom, and pass the labels' own
        ``top_to_baseline`` here if it needs the exact figure.
        """
        spec = BookPDFGenerator(six_by_nine_book()).page_spec(2)
        reference = text_reference()

        def measured(points: float) -> List[float]:
            size = type_px(points, BOOK_DPI)
            image = _draw_pipeline_diagram(spec, GUIDE_ASSUME_STEPS, _guide_face(size), size)
            mask = dark(image)
            found = type_bands(mask)
            assert found, (
                "the fixed classifier must still find SOME type inside the "
                "bordered boxes -- excluding them wholesale is the exact "
                "defect F-4 fixed"
            )
            return [cap_height_points(mask, band, reference) for band in found]

        assert min(measured(6.0)) < FLOOR_PT, (
            f"a box label shrunk to 6pt measured {min(measured(6.0)):.2f}pt by "
            "this classifier -- if that is >= FLOOR_PT the classifier is "
            "still missing the box's own text"
        )
        assert min(measured(GUIDE_BODY_POINTS)) >= FLOOR_PT, (
            "and at the size the page really letters these labels in, the "
            f"same classifier measures {min(measured(GUIDE_BODY_POINTS)):.2f}pt "
            "-- a control that called every size too small would prove "
            "nothing about the one that is"
        )


# --------------------------------------------------------------------------
# AC-5 — the extra page shifts everything by one, parity kept
# --------------------------------------------------------------------------


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

    @staticmethod
    @pytest.fixture(scope="class")
    def pages(export) -> List[Image.Image]:
        return pdf_pages(export)

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
            == old_style_total(6, dividers=3, pages=6, answers=6) + 1 + 1
        )
        assert pdf_page_count(export) == interior_page_count(6, 6, 6, 3)

    def test_every_pages_parity_still_equals_its_own_position(self, pages):
        """A right-hand (odd) page's drawing sits right of the trim's middle,
        a left-hand (even) one left of it — read off puzzle AND answer pages
        alike, since CARD-198 both carry the same 20x20-style drawing shape
        this corpus's puzzles give.

        **What the sign is, since CON-018's margins were amended** (CARD-222).
        It used to be half the gutter/outside difference: the drawing was
        centred across the usable area, so an odd page's own centre sat that
        far right of the trim's. Two things have happened since. CARD-204
        made the drawing flush with the *outer* margin, so the offset became
        half the drawing's own horizontal spare, signed by parity; and the
        2026-10-17 amendment made the gutter and the outside margin equal, so
        the margin difference — the term this test was originally written
        about — is now zero and contributes nothing. The spare does, on every
        page that has one, which is what this test now says.

        **A page whose drawing fills the text width has no spare and no side
        to be off**, and after the amendment some do: the usable width is
        3.175 mm narrower, so a drawing that had a few pixels of slack can now
        be width-bound to within a rounding pixel. Such a page is skipped
        rather than asserted either way — and the skipped set is bounded, so
        the test cannot quietly become vacuous.
        """
        checked = 0
        flush = []
        for number, page in enumerate(pages, start=1):
            try:
                drawing = drawing_of(page)
            except ValueError:
                continue
            offset = (drawing.left + drawing.grid_right) / 2 - page.width / 2
            if abs(offset) <= 2:
                # Width-bound: the drawing's spare is zero to within the one
                # rounding pixel each of its edges can move by.
                flush.append((number, offset))
                continue
            assert (offset > 0) == (number % 2 == 1), (
                f"interior page {number} is centred {offset:.1f} px off the "
                f"middle, the wrong side for {'an odd' if number % 2 else 'an even'} page"
            )
            checked += 1
        assert checked >= 6, f"only {checked} pages carried a measurable drawing"
        # Measured: six of this corpus's pages are width-bound on the
        # amended margins (9, 10, 12, 17, 18, 19 — the 20x20-style drawings,
        # each 1 px off the middle, which is the rounding and not a side).
        # The bound is that measurement, so a seventh fails here.
        assert len(flush) <= 6, (
            f"these pages' drawings fill the text width and so carry no "
            f"parity evidence at all: {flush}. Six is the amended margins' "
            "own cost, measured; more than that and this test is measuring "
            "almost nothing"
        )
        assert checked >= len(flush), (
            f"only {checked} pages carried parity evidence against "
            f"{len(flush)} that carried none — the corpus has stopped being "
            "mostly measurable"
        )


# --------------------------------------------------------------------------
# AC-8 — the generalised helpers reproduce the original worked example
# --------------------------------------------------------------------------


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
    """AC-8 — ``example_line_layout``/``draw_example_line`` called with the
    original ``(3, 1)``/``6`` arguments draw pixel-identical output to
    before the refactor that made them parameters.

    Checked twice: against an image built fresh by this same pair of
    functions (so a regression in either shows up immediately, independent
    of where the guide page happens to put the result), and against where
    the shipped guide page actually draws it now — page 2, the recap at the
    close of the 2-page tutorial (this card moved it off page 1 to make room
    for the new material; see this card's Worktree notes, STRUCTURE).
    """

    @staticmethod
    @pytest.fixture(scope="class")
    def generator() -> BookPDFGenerator:
        return BookPDFGenerator(corpus_book("card-201-ac8"))

    @staticmethod
    @pytest.fixture(scope="class")
    def step_images(generator) -> List[np.ndarray]:
        spec = generator.page_spec(2)
        layout = example_line_layout(spec, CLUE, LENGTH)
        return [
            diagram_mask(draw_example_line(layout, ExampleStep("", "", filled, crossed)))
            for filled, crossed in WORKED_EXAMPLE_FILLS
        ]

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

    def test_each_step_is_pixel_identical_to_a_fresh_render_of_the_same_call(self, step_images):
        """Idempotent: the same call, called twice, draws the same pixels —
        the premise the page-2 comparison below relies on.
        """
        generator = BookPDFGenerator(corpus_book("card-201-ac8-again"))
        spec = generator.page_spec(2)
        layout = example_line_layout(spec, CLUE, LENGTH)
        for (filled, crossed), expected in zip(WORKED_EXAMPLE_FILLS, step_images):
            again = diagram_mask(draw_example_line(layout, ExampleStep("", "", filled, crossed)))
            assert again.shape == expected.shape and np.array_equal(again, expected)

    def test_the_shipped_guide_page_draws_these_same_four_steps_pixel_identical_on_page_2(
        self, generator, step_images
    ):
        page = generator.create_guide_page(4, 2, 1, 1, page_number=2)
        mask = dark(page)
        drawn = drawn_bands(mask)
        assert len(drawn) >= 4, f"page 2 draws only {len(drawn)} diagrams; the recap is missing"
        # The recap is the last 4 drawings on the full form (after the
        # region split, the comparison, the pipeline and the difficulty box).
        recap = drawn[-4:]
        for (top, bottom), expected in zip(recap, step_images):
            found = tight(mask[top : bottom + 1])
            assert found.shape == expected.shape, (
                f"a recap step is {found.shape} px, the fresh render is {expected.shape} px"
            )
            assert np.array_equal(found, expected), "a recap step's pixels differ from a fresh render"
