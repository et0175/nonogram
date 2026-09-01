"""COMP-007 tests: the two-page PDF export and its answer key (FR-016).

AC / test-id mapping — the trace.yml names, kept traceable from these
pytest-idiomatic function names:

    AC-046  TestExport_WritesPDFPageOneBlankWithHeader
                -> test_export_writes_a_two_page_pdf*, test_page_one_*
    AC-047  TestExport_WritesPDFPageTwoAnswerKeyWithHeader
                -> test_page_two_*
    AC-048  TestExport_RejectsUnverifiedPuzzleForPDF
                -> test_export_rejects_an_unverified_puzzle_for_pdf*

The pages are asserted as *pixels*, through ``pdf.render_pages``, not by
decoding the written file: ADR-0006's baseline has no PDF reader in it, and
CARD-012 exposed the raster as an object precisely so that a second sink on it
could be tested without one (CON-006). What the file itself is asked for is the
things a reader can check without decoding an image — that it is a PDF, that its
page tree holds two pages, and that it is the size the layout meant at 300 DPI.

The other two things these tests hold down are the *filename* (ADR-0016 gives
the PDF a ``<name>-<difficulty>`` stem while the other four formats keep the
bare name, so one run can no longer assume one stem) and the promise that
nothing is ever overwritten (ADR-0017, guardrail G-5) — including past the first
collision and around a file that appears in between.

Nothing here writes outside ``tmp_path``.
"""

from __future__ import annotations

import ast
import re
import sys
import tomllib
from importlib import resources
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont, features

from nonogram import cli, difficulty, export, orchestrator
from nonogram.clues import compute_clues
from nonogram.errors import ExportRejected
from nonogram.export import layout as layout_module
from nonogram.export import pdf, png
from nonogram.export.layout import DPI, HeaderBand, Layout, compute_layout
from nonogram.orchestrator import GenerationRequest, Puzzle, export_puzzle, generate
from nonogram.solver import MANY

# --------------------------------------------------------------------------
# Helpers — same notation as tests/test_export_image.py: ``█`` filled, ``·`` empty.
# --------------------------------------------------------------------------

_FILLED = "█"

_WHITE = (255, 255, 255)
_BLACK = (0, 0, 0)

#: The score AC-046's ``"Medium"`` puzzle is pinned at: the middle of the
#: Medium band, so a retune of the cutoffs has to move a long way before this
#: test's tier changes meaning (ADR-0005's bands are 0-33 / 33-66 / 66-100).
MEDIUM_SCORE = 50.0

#: A4's two edges in PostScript points — 210 and 297mm at 72pt to the inch,
#: spelled out here rather than read from ``layout_module``. A page bound that
#: derives its sheet size from the module that sized the page asserts only that
#: the two agree; these literals are the second opinion that makes "it fits A4"
#: a claim about paper.
A4_SHORT_EDGE_PT = 210.0 / 25.4 * 72
A4_LONG_EDGE_PT = 297.0 / 25.4 * 72


def _a4_bounds_pt(geometry: Layout) -> tuple[float, float]:
    """A4's width and height in points, held the way this grid turns it.

    NFR-006: a grid wider than it is tall prints landscape, so the sheet's two
    bounds swap. Which way up is derived here from the grid's own extent rather
    than read off ``geometry.orientation``, so a page turned the wrong way is
    still measured against the sheet it was owed — and taking ``max`` of the
    two edges, which would pass either way round, is exactly what this must not
    do.
    """
    expected = "landscape" if geometry.columns > geometry.rows else "portrait"
    # The bounds below are an UPPER bound only, and that catches just half of
    # "turned the wrong way" (cycle-1 F-003, and the same hole F-002 found in
    # the image helper). A wrongly-landscape page overruns the portrait sheet
    # it was owed and is caught. A wrongly-PORTRAIT page is not: `_fit_cell`
    # shrinks the cell until the drawing fits the narrower sheet, so the
    # drawing comes out smaller and sits inside the landscape bound it is
    # measured against. Verified by mutation: with `_orientation_for` forced to
    # portrait, every PDF case still passed the bounds. Asserting the
    # orientation itself is what closes it.
    assert geometry.orientation == expected, (
        f"{geometry.columns}x{geometry.rows} printed {geometry.orientation}, "
        f"not the {expected} sheet NFR-006 owes it"
    )
    if geometry.columns > geometry.rows:
        return A4_LONG_EDGE_PT, A4_SHORT_EDGE_PT
    return A4_SHORT_EDGE_PT, A4_LONG_EDGE_PT


def _grid(*patterns: str) -> list[list[bool]]:
    return [[glyph == _FILLED for glyph in pattern] for pattern in patterns]


#: Exactly one solution — the 2x2 the orchestrator, JSON and image tests pin on.
#:
#:     ██
#:     █·
UNIQUE = _grid("██", "█·")

#: A grid with filled *and* empty cells in every row, so an answer key that
#: filled the wrong cells (or all of them) cannot pass by accident.
ANSWER = _grid("█·█·", "·██·", "██·█", "·█·█")


def _puzzle(
    out: Path | None,
    *,
    grid: list[list[bool]] | None = None,
    solution_count: int | None = 1,
    score: float | None = MEDIUM_SCORE,
    name: str | None = "cat",
    formats: tuple[str, ...] = (export.PDF,),
    **request_fields: object,
) -> Puzzle:
    """A puzzle at the point the pipeline would hand it to the export step.

    Built by driving the aggregate the way :func:`generate` does — record a
    candidate, report a verdict, record a score — so ``ready_for_export`` and
    ``difficulty_tier`` are only ever reached through the aggregate's own
    transitions. ``solution_count=None`` leaves the candidate unjudged, which is
    AC-048's case; ``score=None`` leaves it unscored, which is the untiered
    aggregate ADR-0016's filename has to cope with.
    """
    fields: dict[str, object] = {
        "mode": "random",
        "size": 2,
        "density": 50,
        "seed": 7,
        "export_formats": formats,
        "out": out,
    }
    fields.update(request_fields)
    request = GenerationRequest(**fields)  # type: ignore[arg-type]
    puzzle = Puzzle(request=request, seed=request.seed or 0, name=name)
    puzzle.record_candidate(grid if grid is not None else UNIQUE)
    if solution_count is not None:
        puzzle.confirm_uniqueness(solution_count)
    if score is not None:
        puzzle.record_difficulty(score)
    return puzzle


def _payload(
    grid: list[list[bool]],
    *,
    name: str | None = "cat",
    tier: str | None = "Medium",
) -> export.ExportPayload:
    """The payload COMP-002 would build for ``grid`` (INV-001 clues included)."""
    puzzle_clues = compute_clues(grid)
    return export.ExportPayload(
        grid=grid,
        row_clues=puzzle_clues.rows,
        column_clues=puzzle_clues.columns,
        seed=7,
        mode="random",
        name=name,
        difficulty=tier,
    )


def _written(directory: Path) -> list[Path]:
    return sorted(directory.iterdir()) if directory.exists() else []


def _layout_for(grid: list[list[bool]]) -> Layout:
    """The geometry COMP-007 computes for ``grid``'s clues."""
    return compute_layout(*compute_clues(grid))


def _band_for(grid: list[list[bool]]) -> HeaderBand:
    return layout_module.header_band(_layout_for(grid))


def _cell_centres(geometry: Layout, *, offset: int) -> list[tuple[int, int]]:
    """The centre pixel of every *grid* cell, ``offset`` pixels further down."""
    half = geometry.cell // 2
    return [
        (
            geometry.grid_left + column * geometry.cell + half,
            offset + geometry.grid_top + row * geometry.cell + half,
        )
        for row in range(geometry.rows)
        for column in range(geometry.columns)
    ]


def _has_ink(region: Image.Image) -> bool:
    """Is anything actually drawn in ``region``?

    Asked as "is any pixel dark" and not with ``Image.getbbox()``: these pages
    are ink on *white*, and white is non-zero, so a bounding box of non-zero
    pixels covers a blank page just as fully as a drawn one.
    """
    return region.convert("L").getextrema()[0] < 128


def _stamp(text: str, font: ImageFont.FreeTypeFont) -> bytes:
    """``text`` drawn on a small canvas, as bytes — a comparable glyph sample."""
    canvas = Image.new("L", (160, 120), 255)
    ImageDraw.Draw(canvas).text((10, 10), text, font=font, fill=0)
    return canvas.tobytes()


def _pdf_page_boxes(path: Path) -> list[str]:
    """Every page's ``/MediaBox``, read out of the file without a PDF library.

    One box per page, so the list's length is the page count and its contents
    are the page size in PostScript points. Deliberately a text scrape of
    Pillow's own uncompressed page objects rather than a parse: ADR-0006's
    dependency baseline has no PDF reader, and what these tests need to know
    about the *file* (as opposed to the pages, which are asserted as pixels) is
    only how many pages it has and how big they are.
    """
    boxes = re.findall(rb"/MediaBox \[[^\]]*\]", path.read_bytes())
    return [box.decode("ascii") for box in boxes]


def _page_boxes_as_numbers(path: Path) -> list[tuple[float, float, float, float]]:
    """Every page's ``/MediaBox`` in PostScript points, as four numbers.

    Read as numbers and not as the text of the box: Pillow writes each
    coordinate in its own shortest form (``220.8``, never ``220.80``), so a
    formatted expected string asserts as much about float repr as about the
    page, and changes meaning the moment a cell size does.

    All four coordinates, not just the far corner. A ``/MediaBox`` is
    ``[llx lly urx ury]``, so the near corner is as much part of the page as
    the far one: a box pinned only by ``(urx, ury)`` is the right *size* at an
    unasserted origin, and a page offset from the sheet's corner prints
    cropped. The whole-string comparison this replaced did assert the origin;
    dropping to two fields would have quietly given that up.
    """
    return [
        (
            float(box.split()[2]),
            float(box.split()[3]),
            float(box.split()[4]),
            float(box.split()[5]),
        )
        for box in _pdf_page_boxes(path)
    ]


# ==========================================================================
# The registry row — one row, and the CLI picks it up unedited
# ==========================================================================


def test_the_registry_knows_the_pdf_format() -> None:
    assert export.PDF in export.FORMATS
    assert len(set(export.FORMATS)) == len(export.FORMATS), "duplicate format name"

    row = export.for_format(export.PDF)

    assert row.name == export.PDF
    assert row.extension == ".pdf"
    assert row.render is pdf.render


def test_the_cli_accepts_pdf_without_being_edited() -> None:
    """``--export``'s choices come from the registry, so CARD-014's row is the
    whole of the adapter change (``cli.py`` is untouched by this card)."""
    args = cli.build_parser().parse_args(["generate", "--export", "pdf"])

    assert args.export_formats == ["pdf"]


# ==========================================================================
# AC-046 — TestExport_WritesPDFPageOneBlankWithHeader
# ==========================================================================


def test_export_writes_a_two_page_pdf(tmp_path: Path) -> None:
    """AC-046, end to end and unmocked.

    Pinned seed: at 10x10 / 50% density, seed 0's first candidate is already
    unique — the same pin the orchestrator, JSON and image tests document.
    Running the real pipeline is what makes "finalized, uniqueness-confirmed"
    the solver's word rather than the test's.
    """
    puzzle = generate(
        GenerationRequest(
            mode="random",
            size=10,
            density=50,
            seed=0,
            name="cat",
            export_formats=(export.PDF,),
            out=tmp_path,
        )
    )
    assert puzzle.ready_for_export is True

    paths = export_puzzle(puzzle)

    assert len(paths) == 1
    written = paths[0]
    assert written.suffix == ".pdf"
    assert _written(tmp_path) == [written]
    assert written.read_bytes().startswith(b"%PDF")
    assert len(_pdf_page_boxes(written)) == 2, "a one-page PDF is not an answer key"


def test_both_written_pages_carry_the_layouts_geometry_within_a4(tmp_path: Path) -> None:
    """Without the resolution the PDF writer assumes 72 DPI and the page comes
    out 4.17x too large — the ``pHYs`` tag's problem, one format along.

    Named for what it measures. The expected box is derived from the same
    :func:`compute_layout` and :func:`header_band` the exporter calls, so the
    first two assertions say "the writer did not corrupt the geometry, and the
    two sheets print alike" — not "the page is A4", which they cannot say
    without a second, independent statement of how big A4 is. The third
    assertion is that statement, and it is a *bound*, not an equality: a
    ``/MediaBox`` is the drawing's own size, so a 10x10 page is 100mm wide and
    correctly so. What A4 owes it is only that it fits.
    """
    puzzle = _puzzle(tmp_path, grid=ANSWER)
    geometry = _layout_for(ANSWER)
    band = _band_for(ANSWER)
    expected = (
        0.0,
        0.0,
        geometry.width / DPI * 72,
        (geometry.height + band.height) / DPI * 72,
    )

    boxes = _page_boxes_as_numbers(export_puzzle(puzzle)[0])

    assert boxes == [pytest.approx(expected), pytest.approx(expected)], (
        "the two sheets do not print alike, or one does not start at the sheet's corner"
    )
    sheet_width_pt, sheet_height_pt = _a4_bounds_pt(geometry)
    for _, _, width_pt, height_pt in boxes:
        assert width_pt <= sheet_width_pt, f"{width_pt}pt wide overruns A4's {sheet_width_pt}pt"
        assert height_pt <= sheet_height_pt, (
            f"{height_pt}pt tall overruns A4's {sheet_height_pt}pt"
        )


def _diagonal(width: int, height: int) -> list[list[bool]]:
    """Every third cell: a middling, realistic clue depth in both directions."""
    return [[(row + column) % 3 == 0 for column in range(width)] for row in range(height)]


def _alternating_rows(width: int, height: int) -> list[list[bool]]:
    """Rows alternately full and empty — a 1-cell row gutter and a column
    gutter half the grid's height, i.e. the tallest drawing a shape can make."""
    return [[row % 2 == 0 for _ in range(width)] for row in range(height)]


@pytest.mark.parametrize(
    ("width", "height", "pattern"),
    [
        pytest.param(10, 10, _diagonal, id="cap-bound"),
        pytest.param(30, 30, _diagonal, id="page-fit-bound"),
        pytest.param(10, 25, _alternating_rows, id="tall-drawing-height-bound"),
        pytest.param(10, 26, _alternating_rows, id="tall-drawing-worst-case"),
        # Cycle-1 F-003: every case above is square or tall, so `_a4_bounds_pt`'s
        # landscape branch was dead and all three orientation mutants killed zero
        # PDF tests — NFR-006 was uncovered in the one format that draws a band.
        pytest.param(26, 10, _alternating_rows, id="wide-drawing-landscape-sheet"),
        pytest.param(30, 12, _diagonal, id="wide-drawing-page-fit-bound"),
    ],
)
def test_a_titled_page_still_fits_a4_at_the_cell_sizes_nfr_005_produces(
    width: int, height: int, pattern
) -> None:
    """The PDF is the one format that adds a band above the drawing, so it is
    where NFR-005's larger cells have the least room to spare (AC-080, AC-081).

    Page fit reserves the band for every format (see ``layout._fit_cell``), so
    what this checks is that the reservation is the *right* one — that the band
    a titled page actually draws still lands on the sheet after the cell has
    been sized around it.

    The first two cases are the ends of the supported range, where the comfort
    cap binds and where page fit does. They are square and shallow-guttered,
    both fit with room to spare, and on their own they certified nothing: the
    third and fourth cases are the shapes that broke. A grid whose rows
    alternate full and empty draws a 1-cell row gutter and a gutter half its
    height deep, so it grows *down* — the only direction in which A4's 273mm of
    printable height can run out before its 186mm of width. At 25 and 26 rows
    the cap sits at 7.0 and 6.9mm, above the flat 6.5mm it replaced, and sizing
    the cell on the drawing alone put those pages 34 and 77 device pixels off
    the bottom of the sheet.
    """
    grid = pattern(width, height)
    geometry = _layout_for(grid)
    band = _band_for(grid)

    sheet_width_pt, sheet_height_pt = _a4_bounds_pt(geometry)

    assert (geometry.columns, geometry.rows) == (width, height)
    assert geometry.width <= round(sheet_width_pt / 72 * DPI)
    assert geometry.height + band.height <= round(sheet_height_pt / 72 * DPI)


def test_page_one_is_the_blank_puzzle_with_its_clues() -> None:
    """AC-046's "blank grid with clues": ink in both gutters, none in any cell.

    ``ANSWER`` is half filled, so a page-1 renderer that leaked the solution
    would blacken half of these sample points.
    """
    geometry = _layout_for(ANSWER)
    band = _band_for(ANSWER)

    page_one, _ = pdf.render_pages(_payload(ANSWER))

    pixels = page_one.convert("RGB")
    centres = [
        pixels.getpixel(point)
        for point in _cell_centres(geometry, offset=band.height)
    ]
    assert centres == [_WHITE] * (geometry.rows * geometry.columns)

    row_gutter = pixels.crop(
        (
            geometry.margin,
            band.height + geometry.grid_top,
            geometry.grid_left,
            band.height + geometry.grid_bottom,
        )
    )
    column_gutter = pixels.crop(
        (
            geometry.grid_left,
            band.height + geometry.margin,
            geometry.grid_right,
            band.height + geometry.grid_top,
        )
    )
    assert _has_ink(row_gutter), "the row-clue gutter is blank"
    assert _has_ink(column_gutter), "the column-clue gutter is blank"


def test_page_one_is_the_png_raster_under_a_header(tmp_path: Path) -> None:
    """CON-006, as pixels: the PDF's puzzle page *is* CARD-012's PNG.

    Not "looks like" — the same buffer, pasted below the header band. This is
    what makes the two formats of one puzzle incapable of drifting apart, and
    it is the reason this card adds no drawing code for the grid or the clues.
    """
    payload = _payload(ANSWER)
    band = _band_for(ANSWER)

    page_one, _ = pdf.render_pages(payload)
    raster = png.render_image(payload)

    below_the_band = page_one.crop((0, band.height, page_one.width, page_one.height))
    assert below_the_band.tobytes() == raster.tobytes()


def test_both_pages_carry_the_name_and_the_tier(tmp_path: Path) -> None:
    """AC-046 / AC-047's header, as the line it reads and as ink on the page."""
    payload = _payload(ANSWER, name="cat", tier="Medium")
    band = _band_for(ANSWER)

    assert pdf.header_text(payload) == "cat — Medium"

    page_one, page_two = pdf.render_pages(payload)

    banner_one = page_one.crop((0, 0, page_one.width, band.height))
    banner_two = page_two.crop((0, 0, page_two.width, band.height))
    assert _has_ink(banner_one), "the header band is blank"
    assert banner_one.tobytes() == banner_two.tobytes(), "the two headers differ"


def test_the_header_says_what_the_puzzle_is_called(tmp_path: Path) -> None:
    """The header is the *name*, not the filename: AC-044 keeps the name
    verbatim and ADR-0016's sanitization applies only on the way to a path."""
    puzzle = _puzzle(tmp_path, name="cat: 2026/rev 1")

    paths = export_puzzle(puzzle)

    assert paths[0].name == "cat-2026-rev-1-medium.pdf"
    assert puzzle.name == "cat: 2026/rev 1"


@pytest.mark.parametrize(
    ("name", "tier", "expected"),
    [
        pytest.param("cat", "Medium", "cat — Medium", id="both"),
        pytest.param("cat", None, "cat", id="unscored"),
        pytest.param(None, "Medium", "Medium", id="unnamed"),
        pytest.param(None, None, "", id="neither"),
    ],
)
def test_the_header_shows_the_halves_it_has(
    name: str | None, tier: str | None, expected: str
) -> None:
    """A hand-assembled payload can be missing either half; a header reading
    ``" — Medium"`` would be worse than one reading ``"Medium"``."""
    assert pdf.header_text(_payload(UNIQUE, name=name, tier=tier)) == expected


def test_a_titleless_puzzle_gets_no_header_band() -> None:
    """With nothing to say, the band is not reserved at all — the pages are the
    bare raster rather than a raster under a strip of white."""
    payload = _payload(ANSWER, name=None, tier=None)
    geometry = _layout_for(ANSWER)

    page_one, page_two = pdf.render_pages(payload)

    assert page_one.size == (geometry.width, geometry.height)
    assert page_two.size == page_one.size


def test_the_separator_is_stroked_by_choice_now_rather_than_by_necessity() -> None:
    """Why :func:`pdf._draw_header` still strokes the separator (guardrail G-2).

    It began as necessity: Pillow's default face is an ASCII subset and sets
    ``"—"`` as the same ``.notdef`` box a permanently-unassigned codepoint gets,
    so drawing the header in one ``draw.text`` call put tofu in the middle of
    every PDF this tool produced. CARD-032's bundled face removes that
    constraint — the second assertion is the proof that it did — but the rule
    stays: the stroke's geometry is a fixed fraction of the type size, so the
    separator looks the same at every size the header fitting can pick.

    Both halves are asserted so that neither claim in ``_draw_header``'s
    docstring can quietly go stale: if the default face ever grew an em dash the
    history would be wrong, and if the bundled face ever lost one the "by
    choice" would be wrong.
    """
    default_face = ImageFont.load_default(size=40)
    bundled_face = pdf._header_font(40)
    unassigned = "￾"

    assert _stamp("—", default_face) == _stamp(unassigned, default_face), (
        "Pillow's default face grew an em dash"
    )
    assert _stamp("-", default_face) != _stamp(unassigned, default_face), (
        "the sample proves nothing"
    )
    assert _stamp("—", bundled_face) != _stamp(unassigned, bundled_face), (
        "the bundled face lost its em dash"
    )


# ==========================================================================
# CARD-032 / ADR-0006 revision — the header sets a non-ASCII name
#
#   TestPdfHeader_RendersCyrillicName
#       -> test_a_cyrillic_header_sets_the_letters_and_not_notdef_boxes
#          test_the_header_band_of_a_cyrillic_name_is_not_a_row_of_tofu
#   TestPdfHeader_CyrillicNameStillReachesTheFilename
#       -> test_a_cyrillic_name_still_reaches_the_filename
#   TestDependencyBaseline_IsExactlyPillowAndNumpy
#       -> test_the_dependency_baseline_is_still_closed
#          test_the_font_ships_as_package_data_and_not_as_a_dependency
# ==========================================================================

#: Two permanently-unassigned codepoints (U+FFFE and U+FFFF are noncharacters,
#: guaranteed never to be assigned). Every face sets them as ``.notdef``, which
#: is what makes them the reference sample: a character that stamps like one of
#: these is tofu, whatever it was meant to be.
_UNASSIGNED = "￾"
_ALSO_UNASSIGNED = "￿"


def test_the_notdef_comparison_can_actually_tell_tofu_from_a_glyph() -> None:
    """The measuring stick, checked before it is used.

    Two *different* unassigned codepoints stamp identically — so the comparison
    reacts to what was drawn, not to which string was passed — while a covered
    character does not. Without both halves, "differs from an unassigned
    codepoint" would be satisfied by any two distinct strings and would prove
    nothing about coverage.

    The same technique on Pillow's default face is what verified the defect on
    2026-09-01: there, ``к`` stamped identically to ``￾`` while ``c`` did not.
    """
    bundled_face = pdf._header_font(40)
    default_face = ImageFont.load_default(size=40)

    assert _stamp(_UNASSIGNED, bundled_face) == _stamp(_ALSO_UNASSIGNED, bundled_face)
    assert _stamp("c", bundled_face) != _stamp(_UNASSIGNED, bundled_face)
    assert _stamp("к", default_face) == _stamp(_UNASSIGNED, default_face), (
        "the defect this card fixes was never there"
    )


@pytest.mark.parametrize(
    "letter",
    [pytest.param(glyph, id=f"U+{ord(glyph):04X}") for glyph in "котé"],
)
def test_a_cyrillic_header_sets_the_letters_and_not_notdef_boxes(letter: str) -> None:
    """The card's AC, at the face the header is actually drawn with.

    ``к``, ``о``, ``т`` and ``é`` are the four characters that were verified
    byte-identical to an unassigned codepoint on Pillow's default face. Each is
    asserted separately so a failure names the letter that regressed rather
    than reporting that "кот" changed somehow.
    """
    font = pdf._header_font(40)

    assert _stamp(letter, font) != _stamp(_UNASSIGNED, font)


def test_the_header_band_of_a_cyrillic_name_is_not_a_row_of_tofu() -> None:
    """The same claim about the *page*, which is where it has to hold.

    Font coverage is necessary but not sufficient: the header could still be
    drawn with some other face. So the two bands are rendered through
    :func:`pdf.render_pages` — the real path, both pages — and compared against
    a name of the same length made of unassigned codepoints. A header that
    tofu'd would produce the same three boxes and the same band.

    The second comparison is the control: two *different* unassigned names
    render the identical band, so the first comparison is reacting to the
    glyphs and not merely to the two names being different strings.
    """
    band = _band_for(ANSWER)
    width = _layout_for(ANSWER).width

    def banner(name: str, page: int) -> bytes:
        pages = pdf.render_pages(_payload(ANSWER, name=name))
        return pages[page].crop((0, 0, width, band.height)).tobytes()

    for page in (0, 1):
        assert banner("кот", page) != banner(_UNASSIGNED * 3, page), (
            "the Cyrillic name rendered as .notdef boxes"
        )
        assert banner(_UNASSIGNED * 3, page) == banner(_ALSO_UNASSIGNED * 3, page), (
            "the sample proves nothing — unassigned codepoints render differently"
        )


def test_a_cyrillic_name_still_reaches_the_filename(tmp_path: Path) -> None:
    """Guardrail G-3: the sanitizer is untouched by this card.

    Filenames were never part of the defect — ADR-0016's allow-list is
    Unicode-aware and passed ``кот`` through verbatim from the start — so the
    thing to prove about them is that nothing moved. The header is asserted
    alongside, because AC-044's "the name, verbatim" and ADR-0016's sanitized
    stem are two different strings that this card must keep telling apart.
    """
    puzzle = _puzzle(tmp_path, name="кот")

    path = export_puzzle(puzzle)[0]

    assert path.name == "кот-medium.pdf"
    assert puzzle.name == "кот"
    assert pdf.header_text(_payload(UNIQUE, name="кот")) == "кот — Medium"


def test_the_font_ships_as_package_data_and_not_as_a_dependency() -> None:
    """ADR-0006/R1's line, at both ends of it.

    The font must be *present* as package data — readable through the same
    resource lookup :func:`pdf._font_bytes` uses, and a real TTF rather than a
    placeholder — and it must have arrived without touching the installed
    dependency set. The licence is asserted beside it because shipping it is a
    real obligation of the DejaVu licence, not a nicety.

    The manifest is read here rather than trusting the packaging to have worked:
    a ``package-data`` entry that does not name the font builds a wheel that
    imports fine from a source checkout and raises on a real install.
    """
    manifest = tomllib.loads(
        (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(
            encoding="utf-8"
        )
    )
    package_data = manifest["tool"]["setuptools"]["package-data"]["nonogram.export"]

    assert "fonts/*.ttf" in package_data
    assert "fonts/LICENSE" in package_data

    # The real pin — same exact set comparison as
    # test_the_dependency_baseline_is_still_closed — so this test's own
    # docstring ("arrived without touching the installed dependency set") is
    # carried by this test's body, not borrowed from a sibling.
    dependencies = manifest["project"]["dependencies"]
    packages = {re.split(r"[<>=!~\[ ]", line)[0].lower() for line in dependencies}
    assert packages == {"pillow", "numpy"}

    # ``\x00\x01\x00\x00`` is a TrueType file's magic; the alternative is
    # ``true``/``ttcf``. Checked so an empty or truncated file fails here rather
    # than as a FreeType error inside a render.
    font_bytes = pdf._font_bytes()
    assert font_bytes[:4] == b"\x00\x01\x00\x00", font_bytes[:4]
    assert len(font_bytes) > 100_000, "that is not a Unicode font"

    licence = (
        resources.files(pdf.FONT_PACKAGE)
        .joinpath(pdf.FONT_LICENSE_RESOURCE)
        .read_text(encoding="utf-8")
    )
    assert "Bitstream Vera" in licence and "DejaVu" in licence


def test_a_missing_bundled_font_raises_instead_of_falling_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``_font_bytes``'s own docstring: a missing/unreadable resource must raise,
    never fall back to :func:`PIL.ImageFont.load_default`.

    Nothing else in the suite would fail if a future edit wrapped the read in a
    ``try``/``except`` that papered over the failure — that fallback is exactly
    the defect this card exists to fix, reinstated silently. This pins the
    designed error path directly.

    ``_font_bytes`` is ``lru_cache(maxsize=1)``, so the cache is cleared before
    pointing it at a resource that does not exist (otherwise the real bytes
    already cached would be served regardless of ``FONT_RESOURCE``) and cleared
    again afterwards, in a ``finally``, so the real bytes are back for every
    other test in this module rather than leaving the failure cached in their
    place.
    """
    pdf._font_bytes.cache_clear()
    monkeypatch.setattr(pdf, "FONT_RESOURCE", "fonts/NotAFont.ttf")
    try:
        with pytest.raises(FileNotFoundError):
            pdf._font_bytes()
    finally:
        pdf._font_bytes.cache_clear()


def test_the_header_font_propagates_the_failure_rather_than_falling_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The "never fall back" contract pinned at the layer that could actually break it.

    Its sibling above pins ``_font_bytes``. That is not the whole contract:
    ``load_default`` can only be *returned* from :func:`pdf._header_font`, so a
    ``try``/``except`` added there — not in ``_font_bytes`` — would reinstate the
    exact defect this card exists to fix while the sibling test stayed green.
    Cycle 2's review demonstrated precisely that by mutation: a fallback injected
    into ``_header_font`` survived the entire suite.

    So this asserts the error propagates all the way out of ``_header_font``, and
    that what comes back is never Pillow's default face.
    """
    pdf._header_font.cache_clear()
    pdf._font_bytes.cache_clear()
    monkeypatch.setattr(pdf, "FONT_RESOURCE", "fonts/NotAFont.ttf")
    try:
        with pytest.raises(FileNotFoundError):
            pdf._header_font(20)
    finally:
        pdf._font_bytes.cache_clear()
        pdf._header_font.cache_clear()


def test_the_shaping_caveat_matches_the_running_pillow() -> None:
    """The module docstring's Raqm caveat must not drift from the Pillow running.

    The caveat is written as a conditional — "a Pillow built without Raqm does no
    shaping or bidi" — plus the observation that this project's environment is such
    a build. The conditional is always true; the observation is not, and an
    unpinned observation about an install is exactly the kind of docstring claim
    review flagged three times on this card.

    So this pins only the part that can go stale. If Pillow ever gains Raqm here,
    Arabic and Hebrew names would start shaping and joining correctly and the
    caveat's account of the consequence would be wrong — that must fail loudly
    rather than sit in the source as a confident falsehood.

    Deliberately NOT asserted here: the rendered letterforms themselves. Comparing
    a solo glyph's bitmap against the same glyph inside a word is the obvious way
    to detect joining and it does not work — the two images differ because the
    second contains an extra glyph, not because anything joined. That check was
    written, failed for that reason, and was removed rather than tuned until green.
    """
    assert "Raqm" in (pdf.__doc__ or ""), "the caveat must exist for this to guard it"
    assert not features.check("raqm"), (
        "Pillow now reports Raqm support, so complex-script shaping and bidi are "
        "available and the module docstring's caveat about this environment is "
        "stale — update the docstring, and revisit whether Arabic/Hebrew names "
        "still set as isolated unjoined letterforms"
    )


def test_the_header_font_is_the_bundled_file_and_not_the_hosts(tmp_path: Path) -> None:
    """The output must not depend on which fonts the machine has installed.

    ``FreeTypeFont.path`` is what the face was loaded from; the header font is
    loaded from an in-memory buffer of the package's own bytes, so there is no
    host path in it at all. A face resolved by family name off the system font
    stack — the easy wrong turn here — would carry one, and would make this
    tool's PDFs differ between two machines.
    """
    font = pdf._header_font(40)

    assert not isinstance(font.path, (str, Path)), font.path
    assert font.getlength("кот") > 0


def test_the_header_draws_a_rule_between_the_two_halves() -> None:
    """The em dash as ink: a titled header carries more marks than its two
    words alone do, and the extra one sits between them."""
    band = _band_for(ANSWER)
    both, name_only = (
        pdf.render_pages(_payload(ANSWER, name="cat", tier=tier))[0].crop(
            (0, 0, _layout_for(ANSWER).width, band.height)
        )
        for tier in ("Medium", None)
    )

    assert both.tobytes() != name_only.tobytes()
    assert _has_ink(both) and _has_ink(name_only)


@pytest.mark.parametrize(
    "name",
    [
        pytest.param("cat", id="short"),
        pytest.param("a very long puzzle name that keeps going and going", id="long"),
        pytest.param("x" * 400, id="absurd"),
    ],
)
def test_the_header_stays_on_the_page_however_long_the_name_is(name: str) -> None:
    """``--name`` is arbitrary user text (AC-045 asks only that it not be
    blank), and a 2 mm-celled page is narrow. A header set past both edges
    would lose its ends — the one way a title can silently stop saying what the
    puzzle is called — so it is set smaller instead, and both margins stay
    clear.
    """
    band = _band_for(ANSWER)
    width = _layout_for(ANSWER).width
    edge = max(1, width // 100)

    page_one, page_two = pdf.render_pages(_payload(ANSWER, name=name))

    for page in (page_one, page_two):
        banner = page.crop((0, 0, width, band.height))
        assert _has_ink(banner), "the header did not survive being fitted"
        assert not _has_ink(banner.crop((0, 0, edge, band.height)))
        assert not _has_ink(banner.crop((width - edge, 0, width, band.height)))


# ==========================================================================
# AC-047 — TestExport_WritesPDFPageTwoAnswerKeyWithHeader
# ==========================================================================


def test_page_two_reveals_the_solution() -> None:
    """AC-047: every filled cell is inked and every empty one is not, so the
    answer key is the *puzzle's* solution and not a pattern of its own."""
    geometry = _layout_for(ANSWER)
    band = _band_for(ANSWER)

    _, page_two = pdf.render_pages(_payload(ANSWER))

    pixels = page_two.convert("RGB")
    drawn = [
        pixels.getpixel(point)
        for point in _cell_centres(geometry, offset=band.height)
    ]
    expected = [_BLACK if cell else _WHITE for row in ANSWER for cell in row]
    assert drawn == expected


def test_page_two_is_page_one_plus_the_solution() -> None:
    """The answer key is the same sheet, not a second drawing: everything
    outside the grid — the header, both clue gutters, the margins — is
    pixel-identical, so the two pages cannot disagree about the puzzle."""
    geometry = _layout_for(ANSWER)
    band = _band_for(ANSWER)
    grid_box = (
        geometry.grid_left,
        band.height + geometry.grid_top,
        geometry.grid_right,
        band.height + geometry.grid_bottom,
    )

    page_one, page_two = pdf.render_pages(_payload(ANSWER))

    blanked_one, blanked_two = page_one.copy(), page_two.copy()
    for page in (blanked_one, blanked_two):
        ImageDraw.Draw(page).rectangle(grid_box, fill=_WHITE)

    assert page_one.size == page_two.size
    assert blanked_one.tobytes() == blanked_two.tobytes()
    assert page_one.tobytes() != page_two.tobytes(), "the answer key is blank too"


def test_the_puzzle_page_never_depends_on_the_solution() -> None:
    """The strongest form of "page 1 is blank": byte-identical output for a
    payload carrying the real solution and one carrying no grid at all.

    Page 1 reaches only the clue sets — it is CARD-012's raster, which is handed
    the clues and never the grid — so the solution is not merely omitted from
    the first sheet, it is never read for it.
    """
    clues = compute_clues(ANSWER)
    solved = _payload(ANSWER)
    unsolved = export.ExportPayload(
        grid=[],
        row_clues=clues.rows,
        column_clues=clues.columns,
        seed=7,
        mode="random",
        name="cat",
        difficulty="Medium",
    )

    with_grid, without_grid = pdf.render_pages(solved)[0], pdf.render_pages(unsolved)[0]

    assert with_grid.tobytes() == without_grid.tobytes()


# ==========================================================================
# ADR-0016 — <name>-<difficulty>.pdf, and only for the PDF
# ==========================================================================


def test_the_pdf_is_named_after_the_puzzle_and_its_tier(tmp_path: Path) -> None:
    """ADR-0016's own example, ``cat-hard.pdf``: the file says what the puzzle
    is called *and* how hard it turned out, without being opened."""
    puzzle = _puzzle(tmp_path, name="cat", score=80.0)
    assert puzzle.difficulty_tier is difficulty.Tier.HARD

    assert export_puzzle(puzzle)[0].name == "cat-hard.pdf"


def test_the_filename_takes_the_tier_in_its_own_spelling(tmp_path: Path) -> None:
    """Lowercase on disk, capitalized on the page: ``Tier``'s value and its
    ``label`` are one string apart precisely so each can take the form it
    needs, and neither is a second spelling of the other."""
    puzzle = _puzzle(tmp_path, name="cat", score=MEDIUM_SCORE)

    path = export_puzzle(puzzle)[0]

    assert path.name == f"cat-{difficulty.Tier.MEDIUM.value}.pdf"
    assert difficulty.Tier.MEDIUM.label == "Medium"


def test_only_the_pdf_carries_the_tier_suffix(tmp_path: Path) -> None:
    """The per-format stem, as the property it exists for: ADR-0016 scopes its
    convention to the PDF and explicitly leaves FR-011/FR-012's filenames
    alone, so one run writes ``cat.json`` next to ``cat-medium.pdf``."""
    puzzle = _puzzle(
        tmp_path,
        name="cat",
        formats=(export.JSON, export.PNG, export.SVG, export.CSV, export.PDF),
    )

    paths = export_puzzle(puzzle)

    assert {path.suffix: path.stem for path in paths} == {
        ".json": "cat",
        ".png": "cat",
        ".svg": "cat",
        ".csv": "cat",
        ".pdf": "cat-medium",
    }


def test_a_pdf_name_cannot_write_outside_the_output_directory(tmp_path: Path) -> None:
    """ADR-0016's "both components sanitized", as the property that matters:
    ``--name`` is user input on its way into a path, and the tier joined to it
    goes through the very same sanitizer rather than a second one."""
    destination = tmp_path / "out"
    puzzle = _puzzle(destination, name="../../escaped")

    path = export_puzzle(puzzle)[0]

    assert path.parent == destination
    assert path.name == "escaped-medium.pdf"
    assert list(tmp_path.iterdir()) == [destination]


def test_an_unscored_puzzle_keeps_the_bare_name(tmp_path: Path) -> None:
    """Half a convention is not a filename: an aggregate assembled by hand and
    never scored is written as ``cat.pdf``, not ``cat-.pdf``."""
    puzzle = _puzzle(tmp_path, name="cat", score=None)
    assert puzzle.difficulty_tier is None

    assert export_puzzle(puzzle)[0].name == "cat.pdf"


def test_an_unnamed_aggregate_still_exports_under_the_card_007_convention(
    tmp_path: Path,
) -> None:
    """No name at all: the stand-in stem carries the run, and the tier is still
    joined to it — the two components are composed, not special-cased."""
    puzzle = _puzzle(tmp_path, name=None)

    path = export_puzzle(puzzle)[0]

    assert path.name.startswith("random-") and path.name.endswith("-medium.pdf")


# ==========================================================================
# ADR-0017 / guardrail G-5 — the suffix search, and never an overwrite
# ==========================================================================


def test_a_second_export_never_overwrites_the_first(tmp_path: Path) -> None:
    first = export_puzzle(_puzzle(tmp_path, grid=UNIQUE))[0]
    original = first.read_bytes()

    second = export_puzzle(_puzzle(tmp_path, grid=ANSWER))[0]

    assert first.name == "cat-medium.pdf"
    assert second.name == "cat-medium-1.pdf"
    assert first.read_bytes() == original, "the first export was overwritten"


def test_the_suffix_search_continues_past_the_first_collision(tmp_path: Path) -> None:
    """G-5's "several times over": the search does not stop at ``-1``."""
    names = [export_puzzle(_puzzle(tmp_path))[0].name for _ in range(4)]

    assert names == [
        "cat-medium.pdf",
        "cat-medium-1.pdf",
        "cat-medium-2.pdf",
        "cat-medium-3.pdf",
    ]
    assert len(_written(tmp_path)) == 4


def test_an_intervening_file_is_not_overwritten_either(tmp_path: Path) -> None:
    """The collision that appeared *between* two exports — the case a search
    that remembered its last suffix instead of asking the filesystem would
    walk straight over."""
    export_puzzle(_puzzle(tmp_path))
    intruder = tmp_path / "cat-medium-1.pdf"
    intruder.write_bytes(b"not a pdf")

    written = export_puzzle(_puzzle(tmp_path))[0]

    assert written.name == "cat-medium-2.pdf"
    assert intruder.read_bytes() == b"not a pdf"


def test_the_suffixed_export_is_a_whole_pdf(tmp_path: Path) -> None:
    """A collision changes where the file goes and nothing else about it."""
    export_puzzle(_puzzle(tmp_path))

    written = export_puzzle(_puzzle(tmp_path))[0]

    assert written.read_bytes().startswith(b"%PDF")
    assert len(_pdf_page_boxes(written)) == 2


# ==========================================================================
# AC-048 — TestExport_RejectsUnverifiedPuzzleForPDF (INV-002)
# ==========================================================================


def test_export_rejects_an_unverified_puzzle_for_pdf(tmp_path: Path) -> None:
    """AC-048 / INV-002. A candidate the solver has not judged is not
    exportable as a PDF, and nothing is written on the way to finding that out
    — no zero-byte file, no one-page document, nothing to clean up."""
    destination = tmp_path / "out"
    puzzle = _puzzle(destination, solution_count=None, score=None)

    with pytest.raises(ExportRejected, match="not ready for export"):
        export_puzzle(puzzle)

    assert _written(destination) == []


@pytest.mark.parametrize(
    "solution_count",
    [pytest.param(0, id="no-solutions"), pytest.param(MANY, id="many-solutions")],
)
def test_export_rejects_a_pdf_the_solver_did_not_call_unique(
    solution_count: int, tmp_path: Path
) -> None:
    """INV-002 is about *exactly* one solution: a candidate with none and one
    with many are both refused, on the solver's number alone — which matters
    twice here, an answer key for a puzzle with two solutions being wrong even
    where the puzzle sheet would have been fine."""
    destination = tmp_path / "out"
    puzzle = _puzzle(destination, solution_count=solution_count, score=None)

    with pytest.raises(ExportRejected):
        export_puzzle(puzzle)

    assert _written(destination) == []


def test_a_rejected_pdf_export_writes_none_of_the_other_formats(tmp_path: Path) -> None:
    """The gate is consulted once, before the first renderer runs, so a refused
    export cannot leave a partial set of files behind."""
    destination = tmp_path / "out"
    puzzle = _puzzle(
        destination,
        solution_count=None,
        score=None,
        formats=(export.JSON, export.PDF),
    )

    with pytest.raises(ExportRejected):
        export_puzzle(puzzle)

    assert _written(destination) == []


def test_a_rejected_pdf_export_reaches_the_user_as_exit_code_five(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AC-048 as the user meets it: a documented refusal and an exit code, not
    a traceback and not a half-written document."""
    unready = _puzzle(tmp_path, solution_count=None, score=None)
    monkeypatch.setattr(orchestrator, "generate", lambda request: unready)

    exit_code = cli.main(
        [
            "generate",
            "--size",
            "10",
            "--density",
            "50",
            "--export",
            "pdf",
            "--out",
            str(tmp_path),
        ]
    )

    assert exit_code == cli.ExitCode.EXPORT_REJECTED
    assert "not ready for export" in capsys.readouterr().err
    assert _written(tmp_path) == []


def test_the_pdf_renderer_is_not_a_second_gate() -> None:
    """Guardrail G-4, as source.

    INV-002 has one enforcement point (COMP-002, ADR-0007). A renderer that
    re-checked readiness would be the second one that rule exists to prevent —
    and the payload it is handed carries no readiness flag at all, which is
    what makes that structural rather than a convention.
    """
    source = Path(pdf.__file__ or "").read_text(encoding="utf-8")

    for forbidden in ("ready_for_export", "ExportRejected"):
        assert f"{forbidden}(" not in source and f".{forbidden}" not in source


# ==========================================================================
# Guardrail G-1 — Pillow's own PDF writer, and no new dependency
# ==========================================================================


def test_the_pdf_renderer_imports_pillow_and_nothing_third_party() -> None:
    """CON-006's mechanism, checked at the import line rather than in prose.

    Two assertions, because the exact list and the rule behind it are different
    claims. The first pins what this module actually reaches for — ``importlib``
    among them, which is how CARD-032's bundled font is read as *package data*
    (a data file is not a dependency; ADR-0006/R1). The second is the rule that
    outlives the list: every root outside Pillow and the package itself is a
    stdlib module, checked against the interpreter's own inventory rather than
    against a hand-kept set, so a genuinely third-party import cannot slip in
    by being added to the line above at the same time.
    """
    source = Path(pdf.__file__ or "").read_text(encoding="utf-8")
    roots = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            roots.add(node.module.split(".")[0])

    assert roots <= {
        "__future__",
        "functools",
        "importlib",
        "io",
        "pathlib",
        "typing",
        "PIL",
        "nonogram",
    }, roots
    assert roots - {"PIL", "nonogram"} <= set(sys.stdlib_module_names), roots


def test_the_dependency_baseline_is_still_closed() -> None:
    """G-1 / ADR-0006/R1 — ``TestDependencyBaseline_IsExactlyPillowAndNumpy``.

    ``reportlab``/``fpdf``/``weasyprint`` are the ones CARD-014 was told not to
    reach for; the assertion is stronger than a denylist and pins the whole
    runtime list, because "no new dependency" is the decision, not "not those
    three".

    CARD-032 is what makes this the *rule's* check and not just that card's
    guardrail. The ADR-0006 revision admits non-executable static assets as
    package data while leaving the installed dependency set exactly where it
    was, so this list staying at two entries is precisely what tells the two
    apart: a font arriving here instead of in ``package-data`` would be the
    revision being read as permission to bundle anything.
    """
    manifest = tomllib.loads(
        (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(
            encoding="utf-8"
        )
    )
    requirements = manifest["project"]["dependencies"]
    packages = {re.split(r"[<>=!~\[ ]", line)[0].lower() for line in requirements}

    assert packages == {"pillow", "numpy"}


def test_the_pages_are_rendered_without_touching_the_filesystem() -> None:
    """The raster-first shape CARD-012 established, one format along: the pages
    exist as objects, so a caller (and a test) can have the picture without a
    file, and ``write_pdf`` is the thin sink around them."""
    page_one, page_two = pdf.render_pages(_payload(ANSWER))

    assert isinstance(page_one, Image.Image) and isinstance(page_two, Image.Image)
    assert page_one.mode == page_two.mode == "RGB"


def test_write_pdf_reports_where_it_wrote(tmp_path: Path) -> None:
    """The same convenience ``png.write_png`` offers, and the same discarded
    return value through the registry's ``render``."""
    destination = tmp_path / "puzzle.pdf"

    assert pdf.write_pdf(_payload(UNIQUE), destination) == destination
    assert pdf.render(_payload(UNIQUE), tmp_path / "again.pdf") is None
    assert (tmp_path / "again.pdf").read_bytes().startswith(b"%PDF")
