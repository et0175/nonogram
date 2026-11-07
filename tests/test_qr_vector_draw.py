"""CARD-388: ``book_vector_draw.draw_qr``, read back from rendered ink.

The drawer is checked two ways that do not share its code. The pixel half hands
the finished PDF to poppler (an engine that did not write it) and decodes what
it painted with ``tests/helpers/qr_reader.py``, which was written from the QR
standard and shares nothing with the encoder. The geometry half reads the
operators back and rebuilds the matrix from the rectangles, so "the ink is
identical" is compared against the input matrix, not against the drawer.

Positions are the caller's (ADR-0036/R2): every box below is a literal chosen
here, standing in for what ``export/layout.py`` will give CARD-390.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from nonogram.admin import book_qr
from nonogram.admin.book_vector import ContentStream
from nonogram.admin.book_vector import write_vector_pdf
from nonogram.admin.book_vector_draw import (
    MIN_MODULE_MM,
    QR_QUIET_MODULES,
    QrBox,
    QrModuleTooSmall,
    draw_qr,
)
from tests.helpers import pdf_vector, qr_reader

URL = "https://nonogram.adverax.io/b/0123456789"
DPI = 300
PAGE_PX = 600
MM_PER_INCH = 25.4
TWO_CM_PX = 20 / MM_PER_INCH * DPI  # the square the book prints the code in

#: ``x y w h re`` then ``f``: the only shape of path this drawer emits.
RECTANGLE = re.compile(
    r"^(-?\d+(?:\.\d+)?) (-?\d+(?:\.\d+)?) (-?\d+(?:\.\d+)?) (-?\d+(?:\.\d+)?) re f$"
)


def _page(dpi: float = DPI, side_px: float = PAGE_PX) -> ContentStream:
    return ContentStream(width_px=side_px, height_px=side_px, dpi=dpi)


def _rectangles(stream: ContentStream) -> list[tuple[float, float, float, float]]:
    """Every filled rectangle as ``(left, top, right, bottom)`` in device px."""
    out = []
    pt_to_px = stream.dpi / 72.0
    for row in stream.operators:
        found = RECTANGLE.match(row)
        if found:
            x, y, w, h = (float(v) for v in found.groups())
            left, bottom = x * pt_to_px, stream.height_px - y * pt_to_px
            out.append((left, bottom - h * pt_to_px, left + w * pt_to_px, bottom))
    return out


def _render(stream: ContentStream, tmp_path: Path, dpi: int):
    assert pdf_vector.PDFTOPPM is not None, "poppler is the independent renderer"
    data = write_vector_pdf([stream], 1).getvalue()
    return pdf_vector.rendered_page(data, dpi, out_dir=tmp_path)


def _box_for_module_mm(modules: int, module_mm: float, left=100.0, top=120.0) -> QrBox:
    return QrBox(left, top, (modules + 2 * QR_QUIET_MODULES) * module_mm / MM_PER_INCH * DPI)


class TestQrVectorDraw_RenderedCodeDecodes:
    def test_the_two_centimetre_code_decodes_from_poppler_pixels(self, tmp_path) -> None:
        stream = _page()
        draw_qr(stream, book_qr.encode_text(URL), QrBox(150.0, 150.0, TWO_CM_PX))
        assert qr_reader.read_image(_render(stream, tmp_path, DPI)) == URL

    @pytest.mark.parametrize("dpi", [150, 200, 600])
    def test_it_decodes_at_other_render_resolutions(self, tmp_path, dpi) -> None:
        stream = _page()
        draw_qr(stream, book_qr.encode_text(URL), QrBox(150.0, 150.0, TWO_CM_PX))
        assert qr_reader.read_image(_render(stream, tmp_path, dpi)) == URL

    def test_the_smallest_admitted_code_decodes_at_a_phone_like_resolution(
        self, tmp_path
    ) -> None:
        # 0.4 mm modules rendered at 150 dpi are about 2.4 px each: far below
        # what a phone camera delivers, so a pass here is a floor, not a claim
        # that a phone reads it (the figure's own docstring says so).
        text = "https://" + "a" * 66
        modules = book_qr.encode_text(text)
        stream = _page()
        draw_qr(stream, modules, _box_for_module_mm(len(modules), 0.4))
        assert qr_reader.read_image(_render(stream, tmp_path, 150)) == text

    def test_the_page_carries_vector_operators_and_no_image(self, tmp_path) -> None:
        stream = _page()
        draw_qr(stream, book_qr.encode_text(URL), QrBox(150.0, 150.0, TWO_CM_PX))
        data = write_vector_pdf([stream], 1).getvalue()
        assert pdf_vector.page_resource_keys(data) == [set()] or all(
            "XObject" not in keys for keys in pdf_vector.page_resource_keys(data)
        )
        operators = pdf_vector.operator_tokens(pdf_vector.content_streams(data)[0])
        assert set(operators) <= {"g", "re", "f"}


class TestQrVectorDraw_RefusesAModuleTooSmallToRead:
    def test_a_module_under_the_minimum_raises_and_writes_nothing(self) -> None:
        modules = book_qr.encode_text(URL)
        stream = _page()
        with pytest.raises(QrModuleTooSmall):
            draw_qr(stream, modules, _box_for_module_mm(len(modules), 0.399))
        assert stream.operators == ()

    def test_a_box_of_exactly_the_minimum_is_drawn_and_decodes(self, tmp_path) -> None:
        # 0.4 is written here, not imported: the recorded minimum is a claim.
        assert MIN_MODULE_MM == 0.4
        modules = book_qr.encode_text(URL)
        stream = _page()
        draw_qr(stream, modules, _box_for_module_mm(len(modules), 0.4))
        assert stream.operators
        assert qr_reader.read_image(_render(stream, tmp_path, DPI)) == URL

    def test_the_longest_text_fits_the_two_centimetre_square(self) -> None:
        modules = book_qr.encode_text("h" * book_qr.MAX_BYTES)
        stream = _page()
        draw_qr(stream, modules, QrBox(150.0, 150.0, TWO_CM_PX))
        assert stream.operators

    def test_the_real_address_in_a_one_centimetre_square_is_refused(self) -> None:
        stream = _page()
        with pytest.raises(QrModuleTooSmall):
            draw_qr(stream, book_qr.encode_text(URL), QrBox(0.0, 0.0, TWO_CM_PX / 2))
        assert stream.operators == ()

    def test_a_non_square_matrix_or_an_empty_box_writes_nothing(self) -> None:
        stream = _page()
        with pytest.raises(ValueError):
            draw_qr(stream, [[True, False], [True]], QrBox(0.0, 0.0, 200.0))
        with pytest.raises(ValueError):
            draw_qr(stream, book_qr.encode_text(URL), QrBox(0.0, 0.0, 0.0))
        assert stream.operators == ()


class TestQrVectorDraw_QuietZoneIsInsideTheBox:
    @pytest.mark.parametrize(
        "box",
        [
            QrBox(150.0, 150.0, TWO_CM_PX),
            QrBox(0.0, 0.0, 300.0),
            QrBox(333.3, 41.7, 251.9),
            QrBox(10.0, 300.0, 280.0),
        ],
    )
    def test_ink_stays_inside_and_four_modules_clear_of_every_edge(self, box) -> None:
        modules = book_qr.encode_text(URL)
        stream = _page()
        draw_qr(stream, modules, box)
        rectangles = _rectangles(stream)
        module = box.side / (len(modules) + 2 * QR_QUIET_MODULES)
        tolerance = 1e-2  # PDF numbers are written to a few decimals
        assert rectangles
        lefts, tops, rights, bottoms = zip(*rectangles)
        assert min(lefts) >= box.left - tolerance
        assert min(tops) >= box.top - tolerance
        assert max(rights) <= box.left + box.side + tolerance
        assert max(bottoms) <= box.top + box.side + tolerance
        # The finder patterns put ink on all four sides, so the clearance is
        # exactly four modules there and never less anywhere.
        assert min(lefts) - box.left == pytest.approx(4 * module, abs=tolerance)
        assert min(tops) - box.top == pytest.approx(4 * module, abs=tolerance)
        assert box.left + box.side - max(rights) == pytest.approx(4 * module, abs=tolerance)
        assert box.top + box.side - max(bottoms) == pytest.approx(4 * module, abs=tolerance)

    def test_the_rectangles_rebuild_exactly_the_input_matrix(self) -> None:
        modules = book_qr.encode_text(URL)
        box = QrBox(150.0, 150.0, TWO_CM_PX)
        stream = _page()
        draw_qr(stream, modules, box)
        size = len(modules)
        module = box.side / (size + 2 * QR_QUIET_MODULES)
        origin_x = box.left + QR_QUIET_MODULES * module
        origin_y = box.top + QR_QUIET_MODULES * module
        rebuilt = [[False] * size for _ in range(size)]
        for left, top, right, bottom in _rectangles(stream):
            row = round((top - origin_y) / module)
            assert round((bottom - origin_y) / module) == row + 1, "one row tall"
            for column in range(round((left - origin_x) / module), round((right - origin_x) / module)):
                assert not rebuilt[row][column], "no module is inked twice"
                rebuilt[row][column] = True
        assert rebuilt == [list(row) for row in modules]
        dark = sum(cell for row in modules for cell in row)
        assert len(_rectangles(stream)) < dark, "adjacent modules are merged into runs"

    def test_the_ink_is_pure_black(self) -> None:
        stream = _page()
        draw_qr(stream, book_qr.encode_text(URL), QrBox(150.0, 150.0, TWO_CM_PX))
        assert stream.operators[0] == "0 g"
        assert all(RECTANGLE.match(row) for row in stream.operators[1:])
