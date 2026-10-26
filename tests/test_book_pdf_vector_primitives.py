"""CARD-294 — the interior's drawing vocabulary, read back by poppler.

    AC-2  every primitive is found, where the writer said, by an engine that
          did not write the file
          TestVectorPrimitives_AnIndependentEngineFindsEachShape
    AC-3  the round shape's price, with the measurement that establishes it
          TestVectorPrimitives_TheRoundMarkIsAccurateAtThePrintedDotSize
          TestVectorPrimitives_TheRoundMarkCostsSevenOperators
    AC-4  type size is physical points, never pixels
          TestVectorPrimitives_PointSizeIsIndependentOfDpi
    EC(ADR-0042/R5)  the face is embedded once per document, whatever the
          page count
          TestPropertyTest_VectorFont_EmbeddedOncePerDocumentAcrossPageCounts
    F-2   the widths the viewer lays glyphs out from are the face's own, read
          back by FreeType rather than by this project
          TestVectorFontMetrics_FreeTypeAgreesWithTheSfntReader
    F-4   every /FontDescriptor and /Font entry states the face's own metric
          TestVectorFontObjects_TheDescriptorStatesTheFacesOwnMetrics

Why this file is shaped the way it is
-------------------------------------

**The control is poppler, and that is the point of the card.** CARD-293 proved
the mechanism cheap but proved it with its own reader; AC-2 is explicit that a
writer checked only against its own reader demonstrates that two of this
project's functions agree. ``tests/helpers/pdf_vector.py`` keeps the two kinds
of reader visibly apart, and which instrument each claim rests on is stated per
claim rather than once for the file:

* **where a shape lands and how it is inked** — AC-2 — is measured on a raster
  ``pdftoppm`` produced and a text layer ``pdftotext`` produced: a second
  implementation of the whole PDF specification, written by other people;
* **the operator prices and the radial-error figures** — AC-3 — are measured on
  the *emitted stream*, re-parsed by a second implementation of the scanner
  (the regular expressions here against the hand-written one in
  ``scripts/card294_curve_price.py``);
* **the face's own metrics** are measured against **FreeType**, through
  :mod:`PIL.ImageFont`, because the ``/Widths`` poppler lays glyphs out from
  are the writer's own numbers — so a poppler render cannot falsify them. That
  is review cycle 1's F-2, and
  ``TestVectorFontMetrics_FreeTypeAgreesWithTheSfntReader`` is the answer;
* **the descriptor's entries against those metrics** are read back with
  ``PIL.PdfParser``, the convenient reader, because the claim there is that the
  writer states what the reader read — a question about this project only.

The sentence this paragraph replaced said every shape claim here was made on a
poppler raster. Review cycle 1 measured that as false of AC-3, which is why the
instrument is now named per claim.

**Nothing here draws a page** (G-1). The fixtures are a line, a rectangle, a
tone, a round mark and one string on an otherwise empty sheet, which is the
whole of what a vocabulary is. A puzzle page, a guide page and a table of
contents are CARD-295, CARD-296 and CARD-297.

**There is no ``hypothesis``.** The EC's property test builds its corpus by
hand with stdlib :class:`random.Random` and asserts its own minimum case count,
so the sweep cannot silently shrink.
"""

from __future__ import annotations

import math
import random
import re
import struct
from io import BytesIO
from pathlib import Path

import numpy as np
import pytest
from PIL import ImageFont

from nonogram.admin import book_vector
from nonogram.admin.book_vector import (
    BEZIER_CIRCLE_KAPPA,
    POINTS_PER_INCH,
    ROUND_MARK_OPERATORS,
    ContentStream,
    ContentStreamError,
    UnrepresentableText,
    interior_face_bytes,
    interior_face_metrics,
    write_vector_pdf,
)
from nonogram.export.layout import (
    DPI,
    HEADER_BAND_MM,
    MIN_DIFFICULTY_DOT_MM,
    difficulty_dots,
)
from tests.helpers import pdf_vector

MM_PER_INCH = 25.4

#: Why a test may be skipped, said once and loudly. A host with no poppler has
#: no independent engine, and AC-2's claim is *about* the independent engine —
#: so the honest state is "not checked here", never "checked and fine".
NO_POPPLER = "poppler (pdftoppm/pdftotext) is not installed: AC-2's independent engine is absent"

needs_poppler = pytest.mark.skipif(
    pdf_vector.PDFTOPPM is None or pdf_vector.PDFTOTEXT is None, reason=NO_POPPLER
)

#: The sheet every fixture draws on: a quarter of the book's trim, at the
#: book's own DPI, so a coordinate in these tests is the same kind of number a
#: ``Layout`` hands a page card.
SHEET_PX = 600


def _sheet(dpi: float = DPI) -> ContentStream:
    return ContentStream(width_px=SHEET_PX, height_px=SHEET_PX, dpi=dpi)


def _pdf(*pages: ContentStream) -> bytes:
    return write_vector_pdf(list(pages), len(pages)).getvalue()


def _mm_to_px(millimetres: float, dpi: float = DPI) -> float:
    return millimetres * dpi / MM_PER_INCH


def _encoded_characters() -> dict[int, str]:
    """``{byte code: character}`` for every byte the interior's codec defines.

    Derived from the codec here as well, rather than imported from
    ``book_vector._encoded_codepoints`` — the whole point of the FreeType
    comparison is that neither side of it is the module under test.
    """
    found: dict[int, str] = {}
    for code in range(32, 256):
        try:
            found[code] = bytes([code]).decode(book_vector.TEXT_ENCODING)
        except UnicodeDecodeError:
            continue
    return found


# --------------------------------------------------------------------------
# AC-2 — an engine that did not write the file finds each shape
# --------------------------------------------------------------------------


@needs_poppler
class TestVectorPrimitives_AnIndependentEngineFindsEachShape:
    """AC-2, the card's load-bearing control.

    Each primitive is drawn alone, at coordinates stated in the test, and then
    **poppler** is asked where the ink is. The tolerance is one device pixel
    either way, which is the rasteriser's own rounding of a path edge onto a
    pixel grid and not slack given to the writer: a shape placed a millimetre
    wrong is 12 pixels wrong at 300 DPI and fails by an order of magnitude.

    Every test here begins by establishing that the render has ink at all
    (:func:`~tests.helpers.pdf_vector.ink_box` asserts it), because a blank
    page passes "no ink outside the shape" trivially.
    """

    SLACK = 1

    @staticmethod
    def _render(stream: ContentStream, tmp_path: Path, dpi: int = DPI) -> np.ndarray:
        return pdf_vector.rendered_page(_pdf(stream), dpi, out_dir=tmp_path)

    def test_a_stroked_line_is_rendered_where_the_writer_put_it(self, tmp_path):
        sheet = _sheet()
        sheet.stroke_width(3.0)
        sheet.line(200, 100, 200, 500)
        page = self._render(sheet, tmp_path)

        left, top, right, bottom = pdf_vector.ink_box(page)
        assert abs((left + right) / 2 - 200) <= self.SLACK, (left, right)
        assert abs(top - 100) <= self.SLACK and abs(bottom - 500) <= self.SLACK
        # A 3 pt line at 300 DPI is 12.5 device pixels. Derived here from the
        # definition of a point rather than written as 12, so the arithmetic
        # is in the test and not in a constant.
        expected = 3.0 * DPI / POINTS_PER_INCH
        assert abs((right - left + 1) - expected) <= 2 * self.SLACK, (left, right)

    def test_a_stroked_rectangle_is_hollow_and_a_filled_one_is_not(self, tmp_path):
        stroke_pt = 2.0
        hollow, solid = _sheet(), _sheet()
        hollow.stroke_width(stroke_pt)
        hollow.rectangle(100, 100, 500, 400)
        solid.rectangle(100, 100, 500, 400, paint="fill")

        outline = self._render(hollow, tmp_path / "a")
        filled = self._render(solid, tmp_path / "b")

        # A fill stops at the path; a stroke straddles it, so the outlined
        # arm reaches half a stroke further on every side. Derived from the
        # declared width rather than read off the render.
        half = stroke_pt / 2 * DPI / POINTS_PER_INCH
        assert pdf_vector.ink_box(filled) == pytest.approx((100, 100, 500, 400), abs=2)
        assert pdf_vector.ink_box(outline) == pytest.approx(
            (100 - half, 100 - half, 500 + half, 400 + half), abs=2
        )
        middle = (250, 300)
        assert outline[middle] > pdf_vector.INK_LEVEL, "a stroked rectangle has paper inside it"
        assert filled[middle] <= pdf_vector.INK_LEVEL, "a filled rectangle does not"

    def test_a_declared_grey_arrives_as_that_grey(self, tmp_path):
        """The ``g`` operator's tone, measured on the render.

        0.35 is the tone ADR-0037/R2's amended cell rule carries, and poppler
        resolved it to grey 89 on CARD-293's proof pages — ``round(255 * 0.35)``
        exactly. The expectation is re-derived from the operand here rather
        than copied from that document.
        """
        sheet = _sheet()
        sheet.fill_grey(0.35)
        sheet.rectangle(100, 100, 500, 400, paint="fill")
        page = self._render(sheet, tmp_path)

        inside = page[200:300, 200:300]
        assert int(inside.min()) == int(inside.max()) == round(255 * 0.35)

    def test_the_round_mark_renders_round_where_the_writer_centred_it(self, tmp_path):
        """A curve, found by an engine that has never heard of this module.

        Three separate claims, because "there is ink near the middle" is not
        roundness: the ink's bounding box is the declared diameter, its area
        is the circle's area, and **every** inked pixel's distance from the
        declared centre is within a pixel of the declared radius or inside it.
        A square of the same bounding box fails the second; a diamond fails
        the third.
        """
        radius = 60
        sheet = _sheet()
        sheet.fill_grey(0.0)
        sheet.round_mark(300, 300, radius)
        page = self._render(sheet, tmp_path)

        left, top, right, bottom = pdf_vector.ink_box(page)
        assert (left, top, right, bottom) == pytest.approx(
            (300 - radius, 300 - radius, 300 + radius, 300 + radius), abs=self.SLACK
        )

        mask = pdf_vector.ink_mask(page)
        assert int(mask.sum()) == pytest.approx(math.pi * radius**2, rel=0.01)

        rows, columns = np.nonzero(mask)
        distance = np.hypot(rows - 300.0, columns - 300.0)
        assert float(distance.max()) <= radius + 2 * self.SLACK, float(distance.max())

    def test_an_outlined_round_mark_keeps_paper_inside_it(self, tmp_path):
        """``paint="both"`` — the shape an *unfilled* difficulty dot is.

        The one property the glyph's meaning rests on
        (``DifficultyDots.__post_init__``: "an outlined dot still has white
        inside it"), asserted on the render rather than on the operator.
        """
        stroke_pt = 2.0
        sheet = _sheet()
        sheet.fill_grey(1.0)
        sheet.stroke_grey(0.0)
        sheet.stroke_width(stroke_pt)
        sheet.round_mark(300, 300, 60, paint="both")
        page = self._render(sheet, tmp_path)

        # A stroke straddles its path, so the ink reaches half a stroke past
        # the radius on each side. Derived rather than guessed: 2 pt at 300 DPI
        # is 8.33 device pixels, so the box is 60 + 4.17 from the centre.
        reach = 60 + stroke_pt / 2 * DPI / POINTS_PER_INCH
        assert pdf_vector.ink_box(page) == pytest.approx(
            (300 - reach, 300 - reach, 300 + reach, 300 + reach), abs=2
        )
        assert page[300, 300] > pdf_vector.INK_LEVEL, "the ring closed"

    def test_the_text_poppler_reads_back_is_the_text_that_was_shown(self, tmp_path):
        """The face, its ``/Widths`` and its ``/Encoding``, all at once.

        ``·`` (U+00B7) is in the string on purpose: it is the character
        ``band_identity`` sets between a puzzle's number and its tier, it is
        *not* ASCII, and it is the one that would come back as a ``.notdef``
        box if the encoding were wrong. A base-14 substitution would still
        extract this string, which is why AC-1's own test checks the face
        instead — this one checks that what was shown is what a reader gets.
        """
        sheet = _sheet()
        sheet.text("Puzzle 12 · Easy", 50, 300, 12.0)

        extracted = pdf_vector.extracted_text(_pdf(sheet), out_dir=tmp_path)

        assert "Puzzle 12 · Easy" in extracted, repr(extracted)

    def test_the_text_is_inked_on_the_baseline_the_writer_named(self, tmp_path):
        """And it is *ink*, at the stated place — not only a text layer.

        A PDF can carry a text layer that draws nothing (a clipped or
        white-on-white text object extracts perfectly), so the text claim is
        made twice: once through ``pdftotext`` above and once on the raster
        here. The expected box is derived from the face's own advance and the
        declared size, not from the render.
        """
        size_pt = 12.0
        # All capitals and no descender, so the ink's top edge *is* the cap
        # height and its foot *is* the baseline. "Puzzle 12" would not do:
        # its `l` is an ascender, which stands above the cap height, and
        # measuring a cap height against it is how that claim reads 17 % off.
        word = "HARD"
        sheet = _sheet()
        sheet.text(word, 50, 300, size_pt)
        page = self._render(sheet, tmp_path)

        left, top, right, bottom = pdf_vector.ink_box(page)
        metrics = interior_face_metrics()
        em_px = size_pt * DPI / POINTS_PER_INCH
        advance_px = metrics.advance(word) * em_px
        # Ink starts at or after the pen, by the first glyph's left side
        # bearing — never before it, which is the half that would catch a sign
        # error. A fifth of an em bounds the bearing of any letter in this face.
        assert 0 <= left - 50 <= 0.2 * em_px, (left, em_px)
        assert abs((right - left) - advance_px) <= 0.1 * advance_px, (right - left, advance_px)
        # The baseline: capitals sit above it, and `12` has no descender, so
        # the ink's foot is the baseline to within a pixel or two.
        assert abs(bottom - 300) <= 3, bottom
        cap_px = metrics.cap_height / 1000.0 * size_pt * DPI / POINTS_PER_INCH
        assert abs((300 - top) - cap_px) <= 0.15 * cap_px, (300 - top, cap_px)

    def test_no_interior_page_the_vocabulary_writes_carries_an_image(self, tmp_path):
        """ADR-0042/R1, for the pages this vocabulary writes.

        Not the ADR's owed guard over the whole interior — that is
        ``test_no_interior_page_carries_an_image_xobject`` and belongs to the
        card that converts the pages (CARD-295 onward). What is in scope here
        is that the *vocabulary* never puts one there, which is a property of
        this writer and is checked on the file it produces.
        """
        sheet = _sheet()
        sheet.round_mark(300, 300, 20)
        sheet.text("x", 10, 10, 10.0)

        keys_per_page = pdf_vector.page_resource_keys(_pdf(sheet))
        # The floor, which review cycle 1's F-6 is about: a bare ``for`` over
        # this list asserts nothing at all if the reader hands back an empty
        # one, and the reader is ``PIL.PdfParser`` — the convenient half. One
        # page in, one page's resources out.
        assert len(keys_per_page) == 1, keys_per_page
        for keys in keys_per_page:
            assert keys == {"ProcSet", "Font"}, keys

    def test_the_engine_disagrees_when_the_writer_is_wrong(self, tmp_path):
        """Control: the instrument above can fail.

        The same claims are made against a shape drawn 50 pixels off and a
        round mark replaced by a rectangle of its bounding box. If these
        passed, every assertion above would be measuring nothing. This is
        ADR-0039/R1 — a claim needs a control that *can* fail — spent on the
        control rather than on the claim.
        """
        moved = _sheet()
        moved.stroke_width(3.0)
        moved.line(250, 100, 250, 500)
        left, _, right, _ = pdf_vector.ink_box(self._render(moved, tmp_path / "a"))
        assert abs((left + right) / 2 - 200) > self.SLACK

        square = _sheet()
        square.fill_grey(0.0)
        square.rectangle(240, 240, 360, 360, paint="fill")
        mask = pdf_vector.ink_mask(self._render(square, tmp_path / "b"))
        assert int(mask.sum()) != pytest.approx(math.pi * 60**2, rel=0.01)


# --------------------------------------------------------------------------
# AC-3 — the round shape's price
# --------------------------------------------------------------------------


class TestVectorPrimitives_TheRoundMarkCostsSevenOperators:
    """AC-3's first half: the price in operators, counted off the stream.

    ``scripts/card294_curve_price.py`` reports the same number with a
    hand-written scanner; this counts it with a regular expression. Two
    implementations, because a price is a claim.
    """

    def test_a_round_mark_is_one_moveto_four_curves_a_close_and_a_paint(self):
        sheet = _sheet()
        sheet.round_mark(300, 300, 60)

        tokens = pdf_vector.operator_tokens(sheet.render().decode("cp1252"))

        assert tokens == ["m", "c", "c", "c", "c", "h", "f"]
        assert len(tokens) == ROUND_MARK_OPERATORS

    def test_the_paint_operator_is_the_only_thing_the_fill_choice_changes(self):
        tallies = {}
        for paint, operator in (("stroke", "S"), ("fill", "f"), ("both", "B")):
            sheet = _sheet()
            sheet.round_mark(300, 300, 60, paint=paint)
            tokens = pdf_vector.operator_tokens(sheet.render().decode("cp1252"))
            assert len(tokens) == ROUND_MARK_OPERATORS
            assert tokens[-1] == operator
            tallies[paint] = tokens[:-1]
        assert len(set(map(tuple, tallies.values()))) == 1, tallies

    def test_a_curve_is_six_numbers_and_one_operator(self):
        """The bare primitive, which is what every round shape is built of."""
        sheet = _sheet()
        sheet.begin_path(0, 0)
        sheet.curve(10, 20, 30, 40, 50, 60)

        emitted = sheet.operators[-1]

        assert re.fullmatch(rf"({pdf_vector.NUMBER} ){{6}}c", emitted), emitted

    def test_pdf_offers_no_shorter_spelling_in_this_vocabulary(self):
        """The comparison AC-3's verdict needs: what the other shapes cost.

        A straight line is 3 operators, a rectangle 2, a string 6. So a round
        mark at 7 is the most expensive primitive in the vocabulary — by one
        operator over a string — and not by the order of magnitude a "curves
        are awkward" verdict would need. Asserted rather than narrated,
        because the comparison is the finding.
        """
        costs = {}
        for name, draw in (
            ("line", lambda s: s.line(10, 10, 10, 500)),
            ("rectangle", lambda s: s.rectangle(10, 10, 500, 500)),
            ("text", lambda s: s.text("Puzzle 12", 10, 10, 10.0)),
            ("round mark", lambda s: s.round_mark(300, 300, 60)),
        ):
            sheet = _sheet()
            draw(sheet)
            costs[name] = len(pdf_vector.operator_tokens(sheet.render().decode("cp1252")))

        assert costs == {"line": 3, "rectangle": 2, "text": 6, "round mark": 7}
        assert costs["round mark"] == max(costs.values())


class TestVectorPrimitives_TheRoundMarkIsAccurateAtThePrintedDotSize:
    """AC-3's second half: is four Béziers accurate enough for a dot?

    The verdict has to be about *the dot the book prints*, so the sizes come
    from ``nonogram.export.layout.difficulty_dots`` — the one measurement
    behind every difficulty glyph in the book — and not from a size chosen
    here. Its floor is ``MIN_DIFFICULTY_DOT_MM``, below which it draws
    nothing; its ceiling on a puzzle page is ``DIFFICULTY_DOT_RATIO`` of a
    ``HEADER_BAND_MM`` band, asked of the function rather than multiplied out.

    The error is measured on the **control points the writer actually
    emitted**, read back out of the content stream: an error computed from
    ``BEZIER_CIRCLE_KAPPA`` alone would be a fact about a constant, and a
    transposed control point would pass it.
    """

    SAMPLES = 2000

    @staticmethod
    def _printed_dot_diameters_px() -> dict[str, float]:
        band_px = round(_mm_to_px(HEADER_BAND_MM))
        cap = difficulty_dots(0, 0, 40 * band_px, band_px - 1, filled=2, total=3)
        assert cap is not None
        return {
            "floor": _mm_to_px(MIN_DIFFICULTY_DOT_MM),
            "band cap": float(cap.diameter),
        }

    @staticmethod
    def _emitted_curves(radius_px: float) -> list[tuple[float, ...]]:
        """The ``m``/``c`` operands of one round mark, in points.

        Parsed out of the stream, so what is measured is what was written.
        """
        sheet = _sheet()
        sheet.round_mark(300, 300, radius_px)
        stream = sheet.render().decode("cp1252")
        numbers = rf"({pdf_vector.NUMBER})"
        start = re.search(rf"(?m)^{numbers} {numbers} m$", stream)
        assert start is not None, stream
        here = (float(start.group(1)), float(start.group(2)))
        segments = []
        for match in re.finditer(rf"(?m)^{' '.join([numbers] * 6)} c$", stream):
            operands = tuple(float(group) for group in match.groups())
            segments.append(here + operands)
            here = operands[4:6]
        return segments

    def _worst_radial_error(self, radius_px: float) -> float:
        """Worst distance from the true circle, over all four emitted cubics.

        An independent sampler: de Casteljau over the written operands, with
        the centre taken as the midpoint of the extreme operands rather than
        as the number handed in, so a mark drawn around the wrong point is a
        failure of the *roundness* claim too.
        """
        segments = self._emitted_curves(radius_px)
        assert len(segments) == 4, segments
        xs = [value for seg in segments for value in seg[0::2]]
        ys = [value for seg in segments for value in seg[1::2]]
        center_x = (min(xs) + max(xs)) / 2.0
        center_y = (min(ys) + max(ys)) / 2.0
        radius_pt = (max(xs) - min(xs)) / 2.0
        worst = 0.0
        for x0, y0, x1, y1, x2, y2, x3, y3 in segments:
            for index in range(self.SAMPLES + 1):
                t = index / self.SAMPLES
                u = 1.0 - t
                weights = (u**3, 3 * u * u * t, 3 * u * t * t, t**3)
                x = sum(w * p for w, p in zip(weights, (x0, x1, x2, x3)))
                y = sum(w * p for w, p in zip(weights, (y0, y1, y2, y3)))
                worst = max(worst, abs(math.hypot(x - center_x, y - center_y) - radius_pt))
        return worst / radius_pt

    def test_the_four_cubics_never_leave_the_circle_by_three_parts_in_ten_thousand(self):
        """The approximation's own error, measured on a large radius.

        Large, so the stream's 0.001 pt coordinate rounding is negligible
        beside it and what is measured is the Bézier and nothing else. The
        bound is the figure the shipped kappa produces — 2.7253e-4 of the
        radius — and it is held tight: 3e-4 passes and 2e-4 would not, which
        is what makes this a measurement rather than a formality.
        """
        relative = self._worst_radial_error(1000.0)

        assert relative <= 3.0e-4, relative
        assert relative >= 2.0e-4, (
            f"{relative} is better than the shipped kappa can do: either the "
            "kappa changed or this sampler is not sampling the curve"
        )

    #: The bound the verdict is stated at: device pixels at 1200 DPI, a press
    #: RIP — the resolution CARD-293 measured the owner's rule weights at.
    #: Measured 0.0082 at the floor dot and 0.0248 at the band cap, so a
    #: thirtieth of a pixel is tight: it passes by 20 % and the sampler's own
    #: control below shows it can fail.
    MAX_ERROR_DEVICE_PX_AT_1200 = 1 / 30

    def test_the_error_at_every_printed_dot_size_is_under_a_thirtieth_of_a_pixel(self):
        """The verdict, at the sizes that actually print.

        The claim is stated in device pixels at 1200 DPI because "0.0005 mm"
        means nothing on its own and an accuracy claim that does not name its
        resolution says nothing at all.

        Note which figure is bigger. The pure approximation costs 2.722e-4 of
        the radius; at the **floor** dot the measured figure is 3.457e-4 —
        *worse*, because at a 0.5 mm radius the stream's own 0.001 pt
        coordinate rounding is no longer negligible beside the Bézier. So the
        round mark's accuracy at print size is limited by the number format,
        not by the curve, which is the finding AC-3 asked for.
        """
        worst_by_dot = {}
        for name, diameter_px in self._printed_dot_diameters_px().items():
            relative = self._worst_radial_error(diameter_px / 2.0)
            radius_mm = diameter_px / 2.0 * MM_PER_INCH / DPI
            error_px_at_1200 = relative * radius_mm / MM_PER_INCH * 1200
            worst_by_dot[name] = error_px_at_1200
            assert error_px_at_1200 < self.MAX_ERROR_DEVICE_PX_AT_1200, (
                name,
                error_px_at_1200,
            )
        assert set(worst_by_dot) == {"floor", "band cap"}, worst_by_dot
        # The small dot's *relative* error is the larger of the two: the
        # rounding term does not shrink with the radius while the Bézier's
        # does. Pinned, because it is the half of the finding a reader would
        # otherwise have to take on trust.
        assert worst_by_dot["floor"] < worst_by_dot["band cap"]

    def test_the_sampler_would_notice_a_wrong_curve(self):
        """Control, caught: the sampler above is not satisfied by any four cubics.

        Four straight segments through the same four quadrant points — a
        kappa of zero, which is the degenerate case the approximation is an
        improvement on — must fail the bound by two orders of magnitude.
        Without this, "the error is small" could be a property of the sampler.
        """
        radius = 1000.0
        diamond = [
            (0.0, radius, 0.0, radius, radius, 0.0, radius, 0.0),
            (radius, 0.0, radius, 0.0, 0.0, -radius, 0.0, -radius),
            (0.0, -radius, 0.0, -radius, -radius, 0.0, -radius, 0.0),
            (-radius, 0.0, -radius, 0.0, 0.0, radius, 0.0, radius),
        ]
        worst = 0.0
        for x0, y0, x1, y1, x2, y2, x3, y3 in diamond:
            for index in range(self.SAMPLES + 1):
                t = index / self.SAMPLES
                u = 1.0 - t
                weights = (u**3, 3 * u * u * t, 3 * u * t * t, t**3)
                x = sum(w * p for w, p in zip(weights, (x0, x1, x2, x3)))
                y = sum(w * p for w, p in zip(weights, (y0, y1, y2, y3)))
                worst = max(worst, abs(math.hypot(x, y) - radius))
        assert worst / radius > 0.25, worst / radius

    def test_the_shipped_kappa_is_the_one_that_keeps_the_diameter_exact(self):
        """Why 4(sqrt(2)-1)/3 and not the smaller-error 0.5519150244935105.

        The shipped kappa puts each cubic's own midpoint exactly on the
        circle, so the mark's bounding box is exactly the declared diameter
        and the error is one-signed — the mark is never *smaller* than asked
        for. That matters because ``difficulty_dots`` states a diameter and
        ``DifficultyDots`` reasons about whether two dots touch. Measured, not
        asserted from the constant: the extreme operand of the emitted mark is
        the declared radius to the stream's own rounding.
        """
        radius_px = 400.0
        segments = self._emitted_curves(radius_px)
        xs = [value for seg in segments for value in seg[0::2]]
        sheet = _sheet()
        assert (max(xs) - min(xs)) / 2.0 == pytest.approx(
            sheet.to_points(radius_px), abs=0.001
        )
        # And the four quadrant points are on the circle exactly, which is the
        # property the min-max kappa gives up.
        assert BEZIER_CIRCLE_KAPPA == pytest.approx(4 * (math.sqrt(2) - 1) / 3)
        assert BEZIER_CIRCLE_KAPPA > 0.5519150244935105


# --------------------------------------------------------------------------
# AC-4 — points, never pixels
# --------------------------------------------------------------------------


class TestVectorPrimitives_PointSizeIsIndependentOfDpi:
    """AC-4 — the vector sibling of ``TestDividerPage_PointSizeIsIndependentOfDpi``.

    The raster path has to round a point size into whole device pixels and
    back (``type_px``), so that test's expectation carries the rounding. Here
    there is nothing to round: the ``Tf`` operand *is* the point size, and the
    assertion is an equality rather than an approximation. That difference is
    the reason AC-4 exists as its own criterion.
    """

    SIZES = (6.0, 10.0, 10.08, 14.4, 24.0)
    DPIS = (72, 300, 600, 1200)

    def test_the_tf_operand_is_the_same_at_every_dpi(self):
        by_dpi = {}
        for dpi in self.DPIS:
            sheet = ContentStream(
                width_px=_mm_to_px(216, dpi), height_px=_mm_to_px(279, dpi), dpi=dpi
            )
            for index, size in enumerate(self.SIZES):
                sheet.text(f"line {index}", 10, 10 + 10 * index, size)
            by_dpi[dpi] = pdf_vector.type_sizes(sheet.render().decode("cp1252"))

        assert set(map(tuple, by_dpi.values())) == {self.SIZES}

    def test_the_same_point_size_lands_on_the_same_physical_place(self):
        """The other half: the *position* does scale, because paper does not.

        A page card hands positions in device pixels, so the same physical
        place is a different pixel at a different DPI — and must come out as
        the same number of points. Without this, "the size is in points" could
        be true of a stream that put the text somewhere else.
        """
        places = set()
        for dpi in self.DPIS:
            sheet = ContentStream(
                width_px=_mm_to_px(216, dpi), height_px=_mm_to_px(279, dpi), dpi=dpi
            )
            sheet.text("x", _mm_to_px(20, dpi), _mm_to_px(30, dpi), 10.0)
            match = re.search(
                rf"({pdf_vector.NUMBER}) ({pdf_vector.NUMBER}) Td",
                sheet.render().decode("cp1252"),
            )
            assert match is not None
            places.add((round(float(match.group(1)), 1), round(float(match.group(2)), 1)))

        assert len(places) == 1, places
        (x, y), = places
        assert x == pytest.approx(20 / MM_PER_INCH * POINTS_PER_INCH, abs=0.1)
        assert y == pytest.approx((279 - 30) / MM_PER_INCH * POINTS_PER_INCH, abs=0.1)

    def test_a_stroke_width_is_points_too(self):
        """ADR-0037/R2's weights are points, and this is where they survive.

        The owner's 0.3 / 0.8 / 1.3 pt is the design ADR-0042 made printable,
        and it is printable precisely because the operand does not pass
        through a device pixel. 0.3 pt rounds to 1 device pixel at 300 DPI —
        the dropout the amendment refused — so a writer that took pixels
        could not express it at all.
        """
        for dpi in self.DPIS:
            sheet = ContentStream(width_px=100, height_px=100, dpi=dpi)
            for width in (0.3, 0.8, 1.3):
                sheet.stroke_width(width)
            assert pdf_vector.stroke_widths(sheet.render().decode("cp1252")) == [
                0.3,
                0.8,
                1.3,
            ]

    #: The DPI the comparison renders at. Fixed, so that the only thing
    #: varying between the two files is the DPI their *writer* was built with.
    RENDER_DPI = 300

    @needs_poppler
    def test_two_writers_at_different_dpis_print_the_same_physical_type(self, tmp_path):
        """The independent half of AC-4, and the writer is what varies.

        **The version this replaces could not fail on a writer defect.** It
        built one ``ContentStream``, wrote one ``data``, and rendered *that
        same byte string* at 300 and at 600, asserting the ink doubled — a
        property of poppler's rasteriser, true of any PDF that renders text
        at all. Measured in review cycle 1: multiplying the ``Tf`` operand by
        ``self.dpi / 72`` — the exact "multiplied by DPI somewhere
        downstream" defect AC-4 exists to exclude — redded three tests in
        this file and not that one.

        Here the two files come from two *writers*, at 300 and 1200 DPI, with
        the same page in millimetres, the same baseline in millimetres and
        the same ``size_pt``; each is rendered at the same
        :attr:`RENDER_DPI`, and the cap height has to come out the same
        number of pixels. A writer that let its DPI into the point size
        writes 100 pt on one and 400 pt on the other, and the two renders
        disagree by a factor of four.

        The expected height is the face's own ``cap_height`` at the stated
        size, so the claim is not merely "the two agree" — two equally wrong
        writers agree — but "they agree *on the number the face states*".
        """
        page_mm, left_mm, baseline_mm, size_pt = 100.0, 20.0, 60.0, 24.0
        heights = {}
        for writer_dpi in (300, 1200):
            sheet = ContentStream(
                width_px=_mm_to_px(page_mm, writer_dpi),
                height_px=_mm_to_px(page_mm, writer_dpi),
                dpi=writer_dpi,
            )
            sheet.text(
                "HARD",
                _mm_to_px(left_mm, writer_dpi),
                _mm_to_px(baseline_mm, writer_dpi),
                size_pt,
            )
            page = pdf_vector.rendered_page(
                _pdf(sheet), self.RENDER_DPI, out_dir=tmp_path / str(writer_dpi)
            )
            _, top, _, bottom = pdf_vector.ink_box(page)
            heights[writer_dpi] = bottom - top

        cap_px = (
            interior_face_metrics().cap_height
            / 1000.0
            * size_pt
            / POINTS_PER_INCH
            * self.RENDER_DPI
        )
        assert heights[300] == pytest.approx(heights[1200], abs=2), heights
        for writer_dpi, height in heights.items():
            assert height == pytest.approx(cap_px, abs=2), (writer_dpi, height, cap_px)


# --------------------------------------------------------------------------
# EC(ADR-0042/R5) — the face is embedded once per document
# --------------------------------------------------------------------------


class TestPropertyTest_VectorFont_EmbeddedOncePerDocumentAcrossPageCounts:
    """EC(ADR-0042/R5): one embedded face per *file*, never per page.

    **The name is ``TestPropertyTest_…`` and the prefix is load-bearing.**
    This repository configures no ``python_classes``, so pytest's default
    ``Test*`` applies, and review cycle 1 measured this class — spelled
    ``class PropertyTest_…`` — as collecting **zero tests**: no skip, no
    error, just absent from a green total, with the card's test table and
    ADR-0042/R5's own comment citing a node id that did not exist. The
    collectable spelling for a class-shaped property test in this tree is
    ``tests/test_print_specs.py``'s
    ``TestPropertyTest_TrimInchesShown_InsideLimitsAndAccepted``, and this
    follows it. ``tests/test_collected_names.py`` is what makes the next one
    of these fail instead of pass.

    A corpus of books across page counts, built by hand with stdlib
    :class:`random.Random` because this tree carries no ``hypothesis``, with
    its own minimum case count asserted inside the tests so the sweep cannot
    silently shrink.

    The load-bearing figure is the **per-page cost in font bytes, which is
    zero**: a writer that embedded the face per page would still carry
    "exactly one ``/FontFile2`` per page" and would grow by 379 KB a page, so
    the count alone is not the rule. The slope is what the rule is about, and
    it is measured as a slope — across page counts, from the file sizes.
    """

    SEED = 294
    MIN_CASES = 24
    #: Enough pages that a per-page font would show up as megabytes, and
    #: enough different counts that one slope fits all of them.
    PAGE_COUNTS = (1, 2, 3, 5, 8, 13, 21, 34)

    @classmethod
    def _corpus(cls, seed: int, cases: int) -> list[list[ContentStream]]:
        """``cases`` books of random page counts, each page carrying text.

        Text on every page matters: a face embedded per *text object* rather
        than per page is the other way R5 can be broken, so no page is blank
        and some pages carry several strings.
        """
        rng = random.Random(seed)
        books = []
        for _ in range(cases):
            pages = []
            for _ in range(rng.choice(cls.PAGE_COUNTS)):
                sheet = _sheet()
                for index in range(rng.randint(1, 6)):
                    sheet.text(f"Puzzle {rng.randint(1, 450)} · page", 20, 40 + 20 * index, 10.0)
                sheet.stroke_width(rng.choice((0.3, 0.8, 1.3)))
                sheet.line(20, 300, 580, 300)
                if rng.random() < 0.5:
                    sheet.round_mark(300, 400, rng.randint(6, 42))
                pages.append(sheet)
            books.append(pages)
        return books

    def test_every_book_in_the_corpus_embeds_the_face_exactly_once(self):
        books = self._corpus(self.SEED, self.MIN_CASES)
        assert len(books) >= self.MIN_CASES, len(books)
        assert sum(len(pages) for pages in books) >= 2 * self.MIN_CASES

        face = interior_face_bytes()
        seen_counts = set()
        for pages in books:
            data = write_vector_pdf(pages, len(pages)).getvalue()
            faces = pdf_vector.embedded_faces(data)
            assert len(faces) == 1, (len(pages), len(faces))
            assert faces[0] == face
            seen_counts.add(len(pages))
        assert len(seen_counts) >= 5, seen_counts

    def test_a_page_costs_no_font_bytes(self):
        """The slope, which is the rule — not the count.

        One text-bearing page is added at a time and the file's growth is
        compared against the face. A per-page face would make the slope
        379 KB; the measured slope has to be a tiny fraction of that, and the
        bound is stated as a fraction of the face so it cannot drift with the
        face's size.
        """
        face_bytes = len(write_vector_pdf([], 0).getvalue())
        sizes = []
        for count in self.PAGE_COUNTS:
            pages = []
            for index in range(count):
                sheet = _sheet()
                sheet.text(f"Puzzle {index} · Easy", 20, 40, 10.0)
                pages.append(sheet)
            sizes.append((count, len(write_vector_pdf(pages, count).getvalue())))

        (first_count, first_size), (last_count, last_size) = sizes[0], sizes[-1]
        slope = (last_size - first_size) / (last_count - first_count)
        compressed_face = face_bytes  # an empty file is the font plus the shell
        assert slope < compressed_face / 100, (slope, compressed_face)
        assert slope > 0, "a page that costs nothing at all was not written"

    def test_a_per_page_face_would_be_caught(self):
        """Control, caught: what the measurement looks like when R5 is broken.

        One file per page, concatenated in size — the shape a writer that
        embedded the face per page would have — has a slope of the whole
        compressed face, which the bound above rejects by two orders of
        magnitude.
        """
        per_page = []
        for count in self.PAGE_COUNTS:
            sheet = _sheet()
            sheet.text("Puzzle 1 · Easy", 20, 40, 10.0)
            one = len(write_vector_pdf([sheet], 1).getvalue())
            per_page.append((count, one * count))

        (first_count, first_size), (last_count, last_size) = per_page[0], per_page[-1]
        slope = (last_size - first_size) / (last_count - first_count)
        empty = len(write_vector_pdf([], 0).getvalue())
        assert slope > empty / 100, (slope, empty)


# --------------------------------------------------------------------------
# F-2 — the face's metrics, against an engine that did not read them
# --------------------------------------------------------------------------


class TestVectorFontMetrics_FreeTypeAgreesWithTheSfntReader:
    """The sfnt reader's numbers, re-derived by FreeType.

    **Why a second engine and not a render.** ``FontMetrics.advance`` and the
    PDF ``/Widths`` array are built from one dictionary, and the only
    measurement of a string's width compares the writer's advance against a
    poppler render that poppler laid out *from the writer's own*
    ``/Widths``. Both sides of that comparison therefore move together.
    Review cycle 1 measured the consequence: replacing every entry of
    ``/Widths`` with a constant **600** left the whole claim-bearing suite at
    89 passed, 0 failed, and 300 redded exactly one test — a discrimination
    window of about a factor of two on the primary product of 934 lines of
    hand-written sfnt parsing, under a docstring that says the advance is
    "the width the viewer will use, not an estimate of it".

    FreeType is the independent implementation, reached through
    :mod:`PIL.ImageFont` — Pillow is already in the dependency baseline
    (stdlib + Pillow + NumPy), so ADR-0006/R1 is untouched. It reads the same
    ``hmtx``/``cmap`` with other people's code, and at ``size=1000`` its
    advances are PDF's own glyph-space unit, so the comparison needs no
    scaling of this project's own devising.

    What it cannot check: ``FontBBox``, which FreeType exposes per glyph
    rather than per face through this API. That one is controlled only as
    "the descriptor states what the reader read" —
    :class:`TestVectorFontObjects_TheDescriptorStatesTheFacesOwnMetrics` —
    and is named here rather than left to look covered.
    """

    #: Every encoded code must agree to the unit. Not a tolerance: both sides
    #: round the same integer ``hmtx`` entry by the same scale, so any
    #: disagreement at all is a disagreement about the table.
    EXACT = 0.5

    #: FreeType reports ascent and descent as whole pixels at the size asked
    #: for, rounding outwards from the ``hhea`` values this reader scales, so
    #: one unit of slack is the rounding and not slack for the reader.
    ROUNDING = 1

    @staticmethod
    def _freetype():
        return ImageFont.truetype(BytesIO(interior_face_bytes()), 1000)

    def test_every_encoded_width_is_the_width_freetype_measures(self):
        metrics = interior_face_metrics()
        face = self._freetype()
        compared = {}
        for code, character in _encoded_characters().items():
            compared[code] = (metrics.widths_1000[code], face.getlength(character))

        # The floor: cp1252 defines 219 of the 224 codes in 32..255, and the
        # five it leaves undefined are the ones `encode_text` cannot produce.
        # Without this a reader that returned nothing would pass.
        assert len(compared) == 219, len(compared)
        wrong = {
            code: pair for code, pair in compared.items() if abs(pair[0] - pair[1]) > self.EXACT
        }
        assert wrong == {}, wrong

    def test_the_comparison_above_would_notice_a_constant_width_array(self):
        """Control: the mutation that passed 89/89 in cycle 1 reds here.

        The defect is applied to a *copy* of the metrics rather than to the
        module, because a control that edits the module under test is not a
        control. 600 is the constant cycle 1 used; it is within a factor of
        two of this face's mean advance, which is why nothing else caught it.
        """
        face = self._freetype()
        constant = {code: 600 for code in _encoded_characters()}
        disagreements = [
            code
            for code, character in _encoded_characters().items()
            if abs(constant[code] - face.getlength(character)) > self.EXACT
        ]
        assert len(disagreements) > 100, len(disagreements)

    def test_the_ascent_descent_and_cap_height_are_the_faces_own(self):
        """And the vertical metrics, which position every baseline.

        ``cap_height`` is the one that was wrong. The reader used to fall back
        to seven tenths of the ascender when ``OS/2`` carried no
        ``sCapHeight`` — which is this face's case, its ``OS/2`` being
        version 1 — giving 650/1000 em where FreeType measures 729. The
        0.15 relative tolerance of
        ``test_the_text_is_inked_on_the_baseline_the_writer_named`` absorbs a
        10.8 % error, so nothing caught it in round 1. It is now read from
        the ``H`` glyph's own ``yMax`` and asserted here to the unit.
        """
        metrics = interior_face_metrics()
        face = self._freetype()
        ascent, descent = face.getmetrics()
        assert abs(metrics.ascent - ascent) <= self.ROUNDING, (metrics.ascent, ascent)
        assert abs(abs(metrics.descent) - descent) <= self.ROUNDING, (metrics.descent, descent)
        # FreeType's own box for a flat capital, in the same 1000-unit em:
        # `getbbox` counts down from the ascender, so the cap height is the
        # ascent less the box's top edge.
        _, top, _, _ = face.getbbox("H")
        assert metrics.cap_height == pytest.approx(ascent - top, abs=self.ROUNDING), (
            metrics.cap_height,
            ascent - top,
        )

    def test_the_two_winansi_divergences_are_the_measured_ones(self):
        """F-5: ``cp1252`` is ``/WinAnsiEncoding`` **except** at two codes.

        The module used to state the identity as exact, twice. PDF 1.7 Annex
        D.2 differs from CP-1252 at ``0xA0`` (``space``, not ``nbspace``) and
        ``0xAD`` (``hyphen``, not ``softhyphen``). There is no stdlib table
        of WinAnsi to enumerate against, so the set is explicit with a reason
        per member — and each member gets a control: the inkless one here,
        the inking one in
        ``TestVectorVocabulary_RefusesWhatItCannotDraw``.
        """
        assert set(book_vector.WINANSI_DIVERGENCES) == {0xA0, 0xAD}
        metrics = interior_face_metrics()
        # The accepted divergence is accepted *because* it inks nothing
        # different: WinAnsi's `space` and the codec's `nbspace` set the same
        # blank at the same advance, measured off the face rather than
        # asserted from the comment that says so.
        assert metrics.widths_1000[0xA0] == metrics.widths_1000[0x20]
        assert book_vector.REFUSED_BY_WINANSI == {"\u00ad"}


# --------------------------------------------------------------------------
# F-4 — the font objects state the face's own numbers
# --------------------------------------------------------------------------


class TestVectorFontObjects_TheDescriptorStatesTheFacesOwnMetrics:
    """Every ``/FontDescriptor`` and ``/Font`` entry, read back and compared.

    Review cycle 1's F-4: each of these entries carried a prose rationale and
    none had a control. Measured there, one mutation at a time:
    ``Flags=32`` -> ``4``, ``CapHeight`` -> ``1000``, ``Ascent``/``Descent``
    -> ``0``, ``Length1`` -> ``1`` each left 89 passed. Only ``Encoding`` was
    controlled, by ``pdftotext``.

    The instrument is ``PIL.PdfParser`` — the convenient reader — and that is
    the right choice *here*, because the claim is "the writer states what the
    reader read", a question about two of this project's own functions. That
    the reader read the face correctly is
    :class:`TestVectorFontMetrics_FreeTypeAgreesWithTheSfntReader`'s, against
    FreeType. The two together are what makes the chain
    face -> reader -> descriptor checked end to end.

    What a control cannot reach from this host is named rather than implied:
    poppler renders and extracts identically with ``Flags=4``, and ``qpdf``,
    ``mutool`` and ``gs`` are not installed, so the *behavioural* claim in
    ``_write_face``'s docstring — that a viewer needs the non-symbolic bit to
    honour ``/WinAnsiEncoding`` — is untested against the viewers it is about
    (Acrobat, a press RIP). What is tested is that the value this writer
    emits is 32 and stays 32.
    """

    @staticmethod
    def _written() -> bytes:
        sheet = _sheet()
        sheet.text("Puzzle 12 · Easy", 20, 40, 10.0)
        return _pdf(sheet)

    def test_the_descriptor_states_the_metrics_the_reader_read(self):
        data = self._written()
        metrics = interior_face_metrics()
        descriptors = pdf_vector.font_objects(data, "FontDescriptor")
        assert len(descriptors) == 1, descriptors
        descriptor = descriptors[0]

        assert descriptor["FontName"] == book_vector.FACE_BASE_FONT
        assert descriptor["Ascent"] == metrics.ascent
        assert descriptor["Descent"] == metrics.descent
        assert descriptor["CapHeight"] == metrics.cap_height
        assert descriptor["FontBBox"] == list(metrics.bbox)
        assert descriptor["ItalicAngle"] == 0
        # PDF 1.7 §9.8.2, bit 6 (value 32) is Nonsymbolic. A viewer that read
        # 4 (Symbolic) is told to consult the font's own (3, 0) cmap instead
        # of /WinAnsiEncoding. Pinned, not verified against such a viewer —
        # the class docstring says which instruments are absent.
        assert descriptor["Flags"] == 32, (
            "Flags must be the non-symbolic bit for /WinAnsiEncoding to be "
            "honoured; got %r" % (descriptor["Flags"],)
        )
        assert descriptor["StemV"] == 80

    def test_the_embedded_stream_declares_the_faces_real_length(self):
        """``/Length1`` is the uncompressed size, and it is checkable.

        A viewer that trusts ``/Length1`` over the Flate stream's own end
        reads a truncated face; ``1`` passed every test in cycle 1.
        """
        lengths = pdf_vector.font_file_lengths(self._written())
        assert lengths == [len(interior_face_bytes())], lengths

    def test_the_font_dictionary_states_every_encoded_width(self):
        """The ``/Widths`` array itself, entry by entry, against the reader.

        With :class:`TestVectorFontMetrics_FreeTypeAgreesWithTheSfntReader`
        holding the reader against FreeType, this closes the chain: the array
        a viewer lays glyphs out from is FreeType's own numbers, by two
        independent steps rather than by one self-consistent one.
        """
        fonts = pdf_vector.font_objects(self._written(), "Font")
        assert len(fonts) == 1, fonts
        font = fonts[0]
        metrics = interior_face_metrics()

        assert font["Subtype"] == "TrueType"
        assert font["Encoding"] == "WinAnsiEncoding"
        assert font["BaseFont"] == book_vector.FACE_BASE_FONT
        assert font["BaseFont"] not in book_vector.BASE_14_FACES
        assert font["FirstChar"] == metrics.first_char
        assert font["LastChar"] == metrics.last_char
        widths = font["Widths"]
        assert len(widths) == metrics.last_char - metrics.first_char + 1 == 224
        assert widths == [
            metrics.widths_1000.get(code, 0)
            for code in range(metrics.first_char, metrics.last_char + 1)
        ]
        # The five codes cp1252 leaves undefined are the zeroes, and no more
        # than those — so "0 is fine, nothing can reach it" stays checkable.
        assert {code for code, width in enumerate(widths, metrics.first_char) if width == 0} == {
            0x81,
            0x8D,
            0x8F,
            0x90,
            0x9D,
        }


# --------------------------------------------------------------------------
# The vocabulary's own refusals
# --------------------------------------------------------------------------


class TestVectorVocabulary_RefusesWhatItCannotDraw:
    """Each refusal has a case, so none of them is a comment.

    They matter more than usual here: a page card consuming this vocabulary
    writes a *printed* artefact, and every one of these failures would
    otherwise reach paper — as a tofu box, an invisible shape or a silent
    nothing — where it cannot be fixed.
    """

    def test_a_character_the_encoding_cannot_carry_is_refused_by_name(self):
        sheet = _sheet()
        with pytest.raises(UnrepresentableText, match="U\\+043A"):
            sheet.text("кот", 10, 10, 10.0)

    def test_a_soft_hyphen_is_refused_because_winansi_would_ink_it(self):
        """F-5's decision, and it is a refusal.

        ``U+00AD`` SOFT HYPHEN is invisible in a source string and
        ``cp1252`` encodes it happily to ``0xAD`` — which
        ``/WinAnsiEncoding`` sets as ``hyphen``. A conforming viewer
        therefore prints a visible hyphen nobody asked for, and a page card's
        strings come from puzzle names and titles that may be pasted or
        imported. That is neither refused nor faithful, and it is ink that
        cannot be fixed after the book is printed — which is
        :class:`UnrepresentableText`'s whole argument, so the third case is
        resolved into the first.
        """
        sheet = _sheet()
        with pytest.raises(UnrepresentableText, match="U\\+00AD"):
            sheet.text("co\u00adoperate", 10, 10, 10.0)

    def test_the_other_winansi_divergence_is_accepted_and_sets_nothing(self):
        """Control, the other way: the inkless divergence is *not* refused.

        ``0xA0`` is WinAnsi's ``space`` against the codec's ``nbspace``, so
        the glyph differs in name and in nothing a reader can see. Refusing
        it would be the refusal over-reaching, which is what this case
        catches.
        """
        sheet = _sheet()
        sheet.text("Puzzle\u00a012", 10, 10, 10.0)
        assert len(sheet.operators) == 1

    @pytest.mark.parametrize(
        "mangle, expected",
        [
            pytest.param(lambda face: face[:2048], "'GPOS' table runs to", id="truncated"),
            pytest.param(lambda face: b"", "too short to hold", id="empty"),
            pytest.param(
                lambda face: b"OTTO" + face[4:], "sfnt version is b'OTTO'", id="a CFF sfnt"
            ),
            pytest.param(
                lambda face: face[:4] + (5000).to_bytes(2, "big") + face[6:],
                "not self-consistent",
                id="an inflated table count",
            ),
            pytest.param(
                lambda face: face.replace(b"OS/2", b"XXXX", 1),
                "carries no 'OS/2' table",
                id="a table the reader needs, missing",
            ),
        ],
    )
    def test_a_face_that_is_not_a_truetype_sfnt_is_refused(self, mangle, expected):
        """F-7: loudly, and as this module's own error type.

        Measured in review cycle 1, before this existed: a face truncated to
        2 KB and an empty one each raised a raw ``struct.error`` from inside
        private parsing, and an ``OTTO``-tagged (CFF) sfnt and an inflated
        table count were accepted **silently** — the OTTO case writing a
        381,528-byte file with CFF bytes inside ``/FontFile2``, which is for
        TrueType outlines only.

        The reach is test-only today: ``face_bytes`` exists so AC-1's control
        can embed something else, and no page card can reach it. The bound is
        closed rather than declared because it is two checks, and because the
        silent half produced a spec-invalid file.
        """
        with pytest.raises(ContentStreamError, match=re.escape(expected)):
            book_vector.font_metrics(mangle(interior_face_bytes()))

    def test_the_characters_the_interior_really_sets_are_all_carried(self):
        """Control: the refusal above is not simply "non-ASCII is refused".

        ``·`` is the separator ``band_identity`` sets, ``—`` is
        ``HEADER_SEPARATOR``'s em dash, ``é`` is in a puzzle name. All three
        are outside ASCII and all three must pass, or the refusal would be
        rejecting the interior's own repertoire.
        """
        sheet = _sheet()
        for text in ("Puzzle 12 · Easy", "cat — Medium", "café", "1234567890"):
            sheet.text(text, 10, 10, 10.0)
        assert len(sheet.operators) == 4

    @pytest.mark.parametrize(
        "draw",
        [
            pytest.param(lambda s: s.round_mark(10, 10, 0), id="a dot with no radius"),
            pytest.param(lambda s: s.round_mark(10, 10, -5), id="a negative radius"),
            pytest.param(lambda s: s.stroke_width(-1), id="a negative stroke"),
            pytest.param(lambda s: s.text("x", 0, 0, 0), id="type at nothing"),
            pytest.param(lambda s: s.fill_grey(1.5), id="a tone past paper"),
            pytest.param(lambda s: s.stroke_grey(-0.1), id="a tone past black"),
            pytest.param(lambda s: s.rectangle(0, 0, 1, 1, paint="dither"), id="an unknown paint"),
        ],
    )
    def test_each_refusal_fires(self, draw):
        sheet = _sheet()
        with pytest.raises(ContentStreamError):
            draw(sheet)

    def test_a_page_short_of_its_plan_is_a_failure_not_a_short_file(self):
        """The object table is laid out from the count, as ``_write_pdf``'s is."""
        with pytest.raises(ContentStreamError, match="3 pages and 1 arrived"):
            write_vector_pdf([_sheet()], 3)
        with pytest.raises(ContentStreamError, match="page 2 arrived"):
            write_vector_pdf([_sheet(), _sheet()], 1)

    def test_a_page_at_no_resolution_is_refused(self):
        with pytest.raises(ContentStreamError):
            ContentStream(width_px=10, height_px=10, dpi=0)

    def test_a_number_never_reaches_the_stream_in_exponent_form(self):
        """PDF has no exponent form, and Python's float formatting does.

        A coordinate small enough for ``repr`` to spell ``1e-05`` would be
        read by a viewer as ``1`` followed by a syntax error — a page that
        silently loses its ink. Swept over sizes that straddle the point where
        ``repr`` switches.
        """
        for pixels in (1e-7, 1e-5, 0.0001, 0.5, 1.0, 1e5, 1e7):
            sheet = ContentStream(width_px=1e7, height_px=1e7, dpi=DPI)
            sheet.line(pixels, pixels, pixels * 2, pixels * 2)
            assert "e" not in sheet.operators[-1].replace("re", ""), sheet.operators[-1]


# --------------------------------------------------------------------------
# What this card could not close, said out loud
# --------------------------------------------------------------------------


class TestVectorVocabulary_TheRoundMarkRouteTheOldGuardCannotSee:
    """A finding, carded rather than left for a later reader to trip over.

    ``tests/test_book_difficulty_dots.py``'s
    ``TestDifficultyDots_HasExactlyOneDrawingSite`` asserts that exactly one
    function in the package puts a round mark on a page, and it does so by
    walking ``src/nonogram/**/*.py`` for calls to Pillow's ellipse family.
    :meth:`ContentStream.round_mark` is a **fifth route** that walk cannot
    see: it is not a Pillow call at all.

    That guard is not wrong today — nothing calls ``round_mark``, so there is
    still one round mark in the package — and it is not this card's to widen,
    because widening it means deciding where the *vector* difficulty glyph
    lives, which is CARD-295/296's. What this card can do is make the route
    visible and countable, so the day a page card draws a vector dot the
    decision is taken rather than slipped past.

    So: the vocabulary is the one place a ``c`` operator is written and the
    one place ``round_mark`` is called, and both are asserted here over the
    same tree.

    **How far this reaches, stated rather than implied.** It is a pattern
    match over source text, not a derived enumeration, so it is *narrower*
    than ADR-0039/R2 would want of a guard that had to stand alone — a curve
    assembled by string concatenation, or a round mark reached through
    ``getattr``, is invisible to it, exactly as the Pillow walk's own
    docstring says of its four routes. It is not trying to be that guard. It
    is a **tripwire on two spellings**: ``round_mark(`` outside the
    vocabulary, and a ``c`` operator written in a module that is not this one.

    **Corrected 2026-10-26 (CARD-296 review cycle 1, F-1), because it reached
    further in this docstring than in the tree.** This paragraph used to say
    "the day a page card draws a vector dot, the second test here goes red",
    and CARD-296 declined its AC-3 partly on that promise. Both were measured
    false: ``ContentStream`` also carries ``begin_path``/``line_to``/
    ``close_path``/``paint``, an arbitrary polygon builder that emits only
    ``m``, ``l``, ``h`` and a paint operator, and a 32-gon filled disc planted
    on the guide's difficulty legend passed **248 tests** — this class
    included. A polyline disc is also *cheaper* than four Béziers, so it is
    the likelier route for CARD-229's dots, which makes the gap the opposite
    of theoretical.

    So the honest statement of this tripwire is: **it fires on a curve, not on
    a round shape.** The polyline route is a **named limit** here and is
    closed where the ink is: a page card bounds the vertices of every subpath
    its own pages write, off the written stream
    (``tests/test_book_guide_page_vector.py``'s
    ``TestGuidePage_DifficultyLegendCarriesNoRoundShapeToday``, counting
    through ``tests/helpers/pdf_vector.subpath_vertices`` so each page card of
    the phase inherits the instrument). That bound is per page kind, so a page
    kind with no such control is uncovered; **CARD-298** owns ADR-0042/R1's
    derived check over every page kind and is where this becomes one check
    instead of one per card.

    When either test here does go red, the response is to grow
    ``TestDifficultyDots_HasExactlyOneDrawingSite`` a fifth route rather than
    to relax this one. A tripwire that fires on the ordinary spelling of the
    thing it is watching for is worth having; it is not a proof, and is not
    claimed as one.
    """

    PACKAGE = Path(book_vector.__file__).parent.parent
    #: The one module allowed to emit a curve operator.
    THE_CURVE_SITE = "nonogram/admin/book_vector.py"

    def _sources(self) -> dict[str, str]:
        found = {
            str(path.relative_to(self.PACKAGE.parent)): path.read_text(encoding="utf-8")
            for path in sorted(self.PACKAGE.rglob("*.py"))
        }
        assert len(found) > 20, "the package walk found almost nothing"
        return found

    def test_the_curve_operator_is_written_in_exactly_one_module(self):
        """A ``c`` operator in a Python string is how a second round shape arrives."""
        writers = {
            path
            for path, source in self._sources().items()
            if re.search(r'f?"[^"\n]*\{[^"\n]*\} c"', source)
            or re.search(r'"\s*c\\n"', source)
        }

        assert writers == {self.THE_CURVE_SITE}, writers

    def test_the_round_mark_primitive_is_defined_once_and_called_nowhere_yet(self):
        """G-1, mechanically: a vocabulary card that drew a page would fail this.

        When a page card calls ``round_mark`` this test goes red, which is the
        intended alarm: it is the moment
        ``TestDifficultyDots_HasExactlyOneDrawingSite`` has to grow a fifth
        route, and the moment this test should be replaced by that one rather
        than relaxed.

        **It is the alarm for this primitive, not for a round shape** — a dot
        approximated out of ``line_to`` calls never touches ``round_mark`` and
        is invisible here, measured (CARD-296 cycle 1, F-1). See the class
        docstring for the limit and for where the polyline route is bounded.
        """
        callers = {
            path
            for path, source in self._sources().items()
            if "round_mark(" in source and path != self.THE_CURVE_SITE
        }

        assert callers == set(), callers
        assert self._sources()[self.THE_CURVE_SITE].count("def round_mark(") == 1


# --------------------------------------------------------------------------
# CARD-294 cycle 2, N-2 — ``_cap_height``'s branches, one face each
# --------------------------------------------------------------------------
#
# Routed to CARD-296 (see that card's "[Routed in from CARD-294 cycle 2]"
# section) because CARD-296 runs first in wave 61 and is the first consumer:
# it centres every clue digit of the guide's line diagrams on
# ``FontMetrics.cap_height``, DejaVu setting its figures to cap height.
#
# ``_cap_height`` has three reachable paths and two refusals, and the bundled
# face exercises exactly ONE path -- ``OS/2`` version 1 with no
# ``sCapHeight``, read through a long ``loca``. Everything else was
# uncontrolled, including the branch CARD-294's own card states as behaviour
# ("version >= 2 still wins where a face has it"), and including a real hole:
# a version-2 face stating ``sCapHeight = 0`` came back as a cap height of
# zero with no fallback and no error.
#
# The faces below are synthetic and hold only the four tables ``_cap_height``
# reads -- ``OS/2``, ``head``, ``loca`` and ``glyf``. The ``cmap`` is a
# parameter of that function rather than a table it parses, so a dict stands
# in for it; nothing here needs a real font, and a real font cannot be made to
# take four of these five paths at all.


def _sfnt(tables: dict[str, bytes]) -> bytes:
    """A minimal TrueType-tagged sfnt holding exactly ``tables``.

    The offset table's ``searchRange``/``entrySelector``/``rangeShift`` are
    derived from the table count the same way ``_sfnt_tables`` derives them to
    check it, because that check refuses a directory that is not
    self-consistent -- so a synthetic face has to be as well-formed in that
    respect as a real one.
    """
    names = sorted(tables)
    count = len(names)
    selector = count.bit_length() - 1
    header = struct.pack(
        ">4sHHHH",
        b"\x00\x01\x00\x00",
        count,
        2**selector * 16,
        selector,
        count * 16 - 2**selector * 16,
    )
    directory = b""
    body = b""
    offset = 12 + 16 * count
    for tag in names:
        payload = tables[tag]
        directory += struct.pack(">4sIII", tag.encode("latin-1"), 0, offset, len(payload))
        offset += len(payload)
        body += payload
    return header + directory + body


def _os2(version: int, cap_height: int | None) -> bytes:
    """An ``OS/2`` table of ``version``, with or without an ``sCapHeight``.

    ``sCapHeight`` lives at byte 88 and exists from version 2, so a table
    carrying one is 90 bytes or more and one that does not is short -- the
    bundled DejaVuSans ships 86. Both halves of ``_cap_height``'s own
    condition (``version >= 2 and length >= 90``) are therefore expressible.
    """
    table = bytearray(96 if cap_height is not None else 86)
    table[0:2] = struct.pack(">H", version)
    if cap_height is not None:
        table[88:90] = struct.pack(">h", cap_height)
    return bytes(table)


def _head(*, long_loca: bool) -> bytes:
    """A ``head`` table whose ``indexToLocFormat`` (byte 50) says which ``loca``."""
    table = bytearray(54)
    table[50:52] = struct.pack(">h", 1 if long_loca else 0)
    return bytes(table)


def _glyf(y_max: int, *, at: int = 0, size: int = 64) -> bytes:
    """A ``glyf`` table whose glyph at ``at`` has ``y_max`` as its ``yMax``.

    A glyph description opens with ``numberOfContours`` and then ``xMin``,
    ``yMin``, ``xMax``, ``yMax``, so ``yMax`` is at offset 8 of the record --
    which is the one field ``_cap_height`` reads.
    """
    table = bytearray(size)
    table[at + 8 : at + 10] = struct.pack(">h", y_max)
    return bytes(table)


class TestVectorCapHeight_EveryBranchHasItsOwnFace:
    """CARD-294 N-2: one synthetic face per reachable path, and per refusal.

    The claim each test makes is narrow on purpose -- "this path returns this
    number, and the other reading of the same bytes does not" -- because the
    defect N-2 names is not a wrong answer, it is a branch nobody could see
    taken.
    """

    #: The ``cmap`` ``_cap_height`` takes as an argument: ``H`` is glyph 1.
    H_IS_GLYPH_ONE = {ord("H"): 1}

    #: A long ``loca`` putting glyph 1's outline at bytes 0..32 of ``glyf``.
    LOCA_LONG = struct.pack(">III", 0, 0, 32)

    #: A ``loca`` whose SHORT reading puts glyph 1's outline at 0..32 and whose
    #: LONG reading of the same twelve bytes is ``start=1048576, end=0`` -- an
    #: empty, out-of-range extent. That asymmetry is deliberate: it is what
    #: makes ``indexToLocFormat`` load-bearing rather than incidental.
    LOCA_SHORT = struct.pack(">HHHHHH", 0, 0, 16, 0, 0, 0)

    #: The ``yMax`` the synthetic ``H`` is given, and the value every face
    #: that falls through to the glyph measurement must return.
    GLYPH_Y_MAX = 1493

    #: The ``sCapHeight`` the version-2 faces state. Deliberately NOT equal to
    #: :attr:`GLYPH_Y_MAX`, so "the OS/2 field won" and "the glyph was
    #: measured" are distinguishable answers.
    STATED_CAP_HEIGHT = 700

    def _face(
        self,
        *,
        version: int = 1,
        cap_height: int | None = None,
        long_loca: bool = True,
        loca: bytes | None = None,
        glyf: bytes | None = None,
    ) -> bytes:
        return _sfnt(
            {
                "OS/2": _os2(version, cap_height),
                "head": _head(long_loca=long_loca),
                "loca": loca if loca is not None else self.LOCA_LONG,
                "glyf": glyf if glyf is not None else _glyf(self.GLYPH_Y_MAX),
            }
        )

    # -- path 1: a version >= 2 OS/2 that states a cap height ---------------

    def test_a_version_two_face_with_a_stated_cap_height_is_believed(self):
        """The branch CARD-294's card states as behaviour and never exercised.

        Controlled by :attr:`STATED_CAP_HEIGHT` differing from
        :attr:`GLYPH_Y_MAX`: delete the ``OS/2`` branch from ``_cap_height``
        and this returns 1493 instead of 700.
        """
        face = self._face(version=2, cap_height=self.STATED_CAP_HEIGHT)

        assert book_vector._cap_height(face, self.H_IS_GLYPH_ONE) == (
            self.STATED_CAP_HEIGHT
        )

    def test_a_version_one_face_measures_its_own_H_instead(self):
        """The one path the bundled face takes, now stated rather than implied."""
        face = self._face(version=1, cap_height=None)

        assert book_vector._cap_height(face, self.H_IS_GLYPH_ONE) == self.GLYPH_Y_MAX

    def test_a_version_two_table_too_short_to_hold_the_field_is_not_read(self):
        """``version >= 2`` is not enough: the table has to be long enough.

        An 86-byte table claiming version 2 would read bytes 88..90 of a table
        that stops at 86 -- which is a neighbouring table's bytes, not a cap
        height. ``_cap_height``'s condition is ``and``-ed on the length for
        this case, and nothing exercised it.
        """
        face = self._face(version=2, cap_height=None)

        assert book_vector._cap_height(face, self.H_IS_GLYPH_ONE) == self.GLYPH_Y_MAX

    # -- the hole N-2 named: a stated zero ---------------------------------

    def test_a_stated_cap_height_of_zero_falls_through_and_is_never_returned(self):
        """CARD-294 N-2's one real residual hole, closed by CARD-296.

        A font tool that did not measure the field writes ``0``. Returning it
        put a zero into ``/CapHeight`` and into the half-cap-height a page
        card centres a digit against -- silently, with no fallback and no
        error. The face still has an ``H``, so there is something to measure.
        """
        face = self._face(version=2, cap_height=0)

        assert book_vector._cap_height(face, self.H_IS_GLYPH_ONE) == self.GLYPH_Y_MAX

    def test_a_stated_negative_cap_height_falls_through_too(self):
        """The same rule, from the other side of zero.

        ``sCapHeight`` is a signed field, so a malformed face can state a
        negative one; it is no more a cap height than a zero is. The guard is
        ``> 0`` rather than ``!= 0`` so this case goes the same way, and this
        is the control that says so.
        """
        face = self._face(version=2, cap_height=-200)

        assert book_vector._cap_height(face, self.H_IS_GLYPH_ONE) == self.GLYPH_Y_MAX

    # -- path 3: the short loca --------------------------------------------

    def test_a_short_loca_face_is_read_with_the_short_offsets(self):
        face = self._face(long_loca=False, loca=self.LOCA_SHORT)

        assert book_vector._cap_height(face, self.H_IS_GLYPH_ONE) == self.GLYPH_Y_MAX

    def test_the_same_loca_bytes_read_as_long_offsets_are_refused(self):
        """What makes ``indexToLocFormat`` load-bearing, measured.

        The same twelve ``loca`` bytes as the test above, with
        ``indexToLocFormat`` flipped to 1. Delete the ``long_loca`` branch and
        one of these two tests reds whichever way the branch is collapsed.
        """
        face = self._face(long_loca=True, loca=self.LOCA_SHORT)

        with pytest.raises(ContentStreamError) as refusal:
            book_vector._cap_height(face, self.H_IS_GLYPH_ONE)

        assert "no outline" in str(refusal.value)

    # -- the two refusals ---------------------------------------------------

    def test_a_face_with_neither_a_stated_cap_height_nor_an_H_is_refused(self):
        """The first raise: nothing to read and nothing to measure."""
        face = self._face(version=1, cap_height=None)

        with pytest.raises(ContentStreamError) as refusal:
            book_vector._cap_height(face, {})

        assert "no OS/2 sCapHeight and no 'H'" in str(refusal.value)

    def test_an_H_with_an_empty_outline_is_refused(self):
        """The second raise: ``loca`` gives the glyph no extent at all.

        An empty ``loca`` entry is how a font says "this glyph is blank", and
        a blank ``H`` has no cap line. Guessing one is what this function
        exists to stop, so it refuses rather than returning the zero that the
        ``glyf`` bytes at that offset would have given.
        """
        face = self._face(loca=struct.pack(">III", 0, 32, 32))

        with pytest.raises(ContentStreamError) as refusal:
            book_vector._cap_height(face, self.H_IS_GLYPH_ONE)

        assert "no outline" in str(refusal.value)

    # -- and which path the shipped face really takes -----------------------

    def test_the_bundled_face_takes_the_glyph_path_through_a_long_loca(self):
        """The one path that was controlled, now named rather than assumed.

        Read out of the face's own bytes here, with this file's own ``struct``
        calls rather than through ``book_vector``'s reader, so the statement
        "the bundled face exercises exactly one of these paths" is a
        measurement of the face and not a restatement of the module.
        """
        face = interior_face_bytes()
        count = struct.unpack(">H", face[4:6])[0]
        tables = {}
        for index in range(count):
            base = 12 + 16 * index
            tag, _sum, offset, length = struct.unpack(">4sIII", face[base : base + 16])
            tables[tag.decode("latin-1")] = (offset, length)

        os2_at, os2_length = tables["OS/2"]
        head_at, _ = tables["head"]

        assert struct.unpack(">H", face[os2_at : os2_at + 2])[0] == 1
        assert os2_length < 90
        assert struct.unpack(">h", face[head_at + 50 : head_at + 52])[0] == 1
        assert interior_face_metrics().cap_height > 0
