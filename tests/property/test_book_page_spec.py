"""CARD-115 standing properties of the book PageSpec builder (seeded corpora, no hypothesis).

    PropertyTest_BookPageSpec_ParityMovesMarginsNeverUsableSize
        For any stored trim and side margins in range and any clue set, an odd
        and an even page have the same usable width and height and the same
        ``book_cell_mm``; only the left and right margins swap (FR-030,
        ADR-0036 "Mirrored margins").
    PropertyTest_BookPageSpec_EmptyMarginsBuildTheCon018Sheet
        For any trim in range and any page, a book whose margins are empty,
        blank or missing builds exactly the sheet of the same book storing
        CON-018's margins (AC-178, CON-018).
    PropertyTest_BookPageSpec_CellNeverAboveStandardCell
        Every book cell is at most NFR-008's 7.5 mm.
"""

from __future__ import annotations

import random
from types import SimpleNamespace

from nonogram.admin.book_page_spec import book_cell_mm, book_page_spec
from nonogram.limits import MAX_SIZE, MIN_SIZE

SEED = 115


def _clue_set(rng: random.Random, lines: int, extent: int) -> tuple[tuple[int, ...], ...]:
    """``lines`` clues for lines ``extent`` cells long, of random depth (runs of 1)."""
    max_depth = (extent + 1) // 2
    return tuple((1,) * rng.randint(1, max_depth) for _ in range(lines))


def _random_stored(rng: random.Random) -> dict[str, str]:
    """Stored columns in range: KDP trims, side margins of 0.64..2.54 cm."""
    return {
        "trim_width_cm": f"{rng.uniform(15.0, 30.0):.2f}",
        "trim_height_cm": f"{rng.uniform(20.0, 48.0):.2f}",
        "gutter_margin_cm": f"{rng.uniform(0.64, 2.54):.2f}",
        "outside_margin_cm": f"{rng.uniform(0.64, 2.54):.2f}",
    }


def test_PropertyTest_BookPageSpec_ParityMovesMarginsNeverUsableSize() -> None:
    rng = random.Random(SEED)
    cases = 0
    for _ in range(300):
        book = SimpleNamespace(**_random_stored(rng))
        columns = rng.randint(MIN_SIZE, MAX_SIZE)
        rows = rng.randint(MIN_SIZE, MAX_SIZE)
        row_clues = _clue_set(rng, rows, columns)
        column_clues = _clue_set(rng, columns, rows)
        odd_page = rng.randrange(1, 400, 2)
        even_page = rng.randrange(2, 400, 2)
        odd = book_page_spec(book, odd_page)
        even = book_page_spec(book, even_page)

        assert odd.usable_width_mm == even.usable_width_mm
        assert odd.usable_height_mm == even.usable_height_mm
        assert (odd.left_margin_mm, odd.right_margin_mm) == (even.right_margin_mm, even.left_margin_mm)
        assert odd.left_margin_mm == odd.gutter_mm and even.right_margin_mm == even.gutter_mm
        assert book_cell_mm(odd, row_clues, column_clues) == book_cell_mm(even, row_clues, column_clues)
        cases += 1
    assert cases >= 300, "the corpus shrank"


def test_PropertyTest_BookPageSpec_EmptyMarginsBuildTheCon018Sheet() -> None:
    rng = random.Random(SEED + 1)
    empties = ({"gutter_margin_cm": None, "outside_margin_cm": None}, {"gutter_margin_cm": "", "outside_margin_cm": " "}, {})
    cases = 0
    for _ in range(300):
        trim = {k: v for k, v in _random_stored(rng).items() if k.startswith("trim")}
        page = rng.randint(1, 400)
        profile_sheet = book_page_spec(
            SimpleNamespace(**trim, gutter_margin_cm="1.27", outside_margin_cm="0.95"), page
        )
        assert (profile_sheet.gutter_mm, profile_sheet.outside_mm) == (12.7, 9.525)
        for empty in empties:
            assert book_page_spec(SimpleNamespace(**trim, **empty), page) == profile_sheet
            cases += 1
    assert cases >= 900, "the corpus shrank"


def test_PropertyTest_BookPageSpec_CellNeverAboveStandardCell() -> None:
    rng = random.Random(SEED + 2)
    cases = 0
    for _ in range(300):
        spec = book_page_spec(SimpleNamespace(**_random_stored(rng)), rng.randint(1, 400))
        columns = rng.randint(MIN_SIZE, MAX_SIZE)
        rows = rng.randint(MIN_SIZE, MAX_SIZE)
        cell = book_cell_mm(spec, _clue_set(rng, rows, columns), _clue_set(rng, columns, rows))
        assert 0 < cell <= 7.5
        cases += 1
    assert cases >= 300, "the corpus shrank"
