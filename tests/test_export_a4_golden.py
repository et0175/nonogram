"""CARD-113's golden A4 tripwire: today's A4 output, pinned before any PageSpec lands.

    EC(ADR-0036/R1)  TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden
        -> test_layout_matches_the_a4_golden  (one parametrised case per clue set)
        -> test_the_layout_corpus_covers_both_orientations_and_both_regimes

    AC-180  TestCliExports_ByteIdenticalAfterBookGeometry
        -> test_seeded_30x30_writes_the_golden_png_svg_and_pdf

    (EC-020, the property AC-180 is an instance of, is
    ``tests/property/test_cli_exports_byte_identity.py``.)

ADR-0036 gives ``compute_layout`` an optional ``PageSpec`` for the book PDF
(CARD-114). ADR-0036/R1 and CON-019 require that a caller passing none — the
CLI, the web UI, every existing export — sees *exactly* today's A4 geometry and
writes exactly today's bytes. The goldens under ``tests/fixtures/a4_golden/``
were captured from ``main`` at CARD-113's base commit (named in each file's
``_header``), before any ``src/`` change; this module compares the live code to
them.

Regeneration command (read before running it)::

    ./.venv/bin/python -m tests.fixtures.a4_golden.regenerate --capture-from-clean-src

Regenerating is **never** how a red test here gets fixed (CARD-113 G-3). A red
test means the change under test moved the A4 geometry or the CLI's bytes,
which is the thing these tests exist to forbid; the fix belongs in that change.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from nonogram.export.layout import compute_layout
from nonogram.limits import MAX_SIZE, MIN_SIZE
from tests.fixtures.a4_golden import golden

#: The layout corpus's floor, asserted so the fixture cannot silently shrink.
REQUIRED_LAYOUT_CASES = 60

#: NFR-005's decided comfort points, as literals — an independent reading of
#: the cap, so the regime classification below does not ask ``layout`` which
#: regime it was in.
_COMFORT_MM = ((10, 9.0), (15, 8.0), (20, 7.5), (25, 7.0), (30, 6.5))
_DPI = 300

_LAYOUT_CASES: dict[str, Any] = golden.load(golden.LAYOUT_GOLDEN)["cases"]


def _clue_set(serialized: list[list[int]]) -> tuple[tuple[int, ...], ...]:
    return tuple(tuple(clue) for clue in serialized)


def _cap_px(larger_dimension: int) -> int:
    """The comfort cap in device pixels, from :data:`_COMFORT_MM` (truncated, as NFR-005 says)."""
    points = _COMFORT_MM
    if larger_dimension <= points[0][0]:
        millimetres = points[0][1]
    elif larger_dimension >= points[-1][0]:
        millimetres = points[-1][1]
    else:
        for (lo_cells, lo_mm), (hi_cells, hi_mm) in zip(points, points[1:], strict=False):
            if lo_cells <= larger_dimension <= hi_cells:
                share = (larger_dimension - lo_cells) / (hi_cells - lo_cells)
                millimetres = lo_mm + share * (hi_mm - lo_mm)
                break
    return int(millimetres / 25.4 * _DPI)


class TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden:
    """EC(ADR-0036/R1): no PageSpec means exactly today's A4 geometry, field by field."""

    @pytest.mark.parametrize("case_id", sorted(_LAYOUT_CASES))
    def test_layout_matches_the_a4_golden(self, case_id: str) -> None:
        case = _LAYOUT_CASES[case_id]
        live = golden.serialize_layout(
            compute_layout(_clue_set(case["row_clues"]), _clue_set(case["column_clues"]))
        )
        differences = golden.layout_differences(case["layout"], live)
        assert not differences, (
            f"ADR-0036/R1 broken: compute_layout without a PageSpec no longer "
            f"reproduces the A4 golden for {case_id}:\n  " + "\n  ".join(differences)
        )

    def test_the_layout_corpus_covers_both_orientations_and_both_regimes(self) -> None:
        """The golden exercises what R1 is about, and cannot silently shrink.

        Both NFR-006 orientations, both NFR-005 regimes (cell held at the
        comfort cap, cell held below it by page fit — classified against an
        independent reading of the cap), the whole 10..30 band on both axes,
        and AC-180's own 30x30.
        """
        layouts = [case["layout"] for case in _LAYOUT_CASES.values()]
        assert len(layouts) >= REQUIRED_LAYOUT_CASES, (
            f"the A4 golden needs >= {REQUIRED_LAYOUT_CASES} clue sets, it has {len(layouts)}"
        )
        assert golden.AC180_CASE_ID in _LAYOUT_CASES

        orientations = {layout["orientation"] for layout in layouts}
        assert orientations == {"portrait", "landscape"}, orientations

        cap_bound = [
            layout
            for layout in layouts
            if layout["cell"] == _cap_px(max(layout["rows"], layout["columns"]))
        ]
        page_fit_bound = [
            layout
            for layout in layouts
            if layout["cell"] < _cap_px(max(layout["rows"], layout["columns"]))
        ]
        assert len(cap_bound) >= 10, f"only {len(cap_bound)} cap-bound layouts"
        assert len(page_fit_bound) >= 10, f"only {len(page_fit_bound)} page-fit-bound layouts"
        assert {layout["orientation"] for layout in page_fit_bound} == {"portrait", "landscape"}

        for axis in ("rows", "columns"):
            extents = {layout[axis] for layout in layouts}
            assert min(extents) == MIN_SIZE and max(extents) == MAX_SIZE, (axis, extents)


class TestCliExports_ByteIdenticalAfterBookGeometry:
    """AC-180: the seeded 30x30's PNG, SVG and PDF match the pre-geometry golden."""

    def test_seeded_30x30_writes_the_golden_png_svg_and_pdf(self, tmp_path: Path) -> None:
        """``nonogram generate --size 30x30 --seed 42`` writes the golden bytes.

        The PNG and SVG are compared as written. The PDF is compared after
        zeroing the two timestamps Pillow stamps at save time — the one part of
        it that is not a function of the request; see ``golden.normalized_pdf``
        for what was measured and why nothing else is excluded.
        """
        golden_case = golden.load(golden.CLI_GOLDEN)["cases"][golden.AC180_CASE_ID]
        assert tuple(golden_case["request"]) == golden.AC180_REQUEST

        written = golden.run_cli(golden.AC180_REQUEST, tmp_path)

        assert set(written) == set(golden.EXPORT_FORMATS)
        for export_format in golden.EXPORT_FORMATS:
            assert written[export_format] == golden_case["exports"][export_format], (
                f"AC-180 broken: the seeded 30x30's {export_format.upper()} is not "
                f"byte-identical to the golden taken before the book geometry "
                f"(golden {golden_case['exports'][export_format]}, "
                f"now {written[export_format]})"
            )
