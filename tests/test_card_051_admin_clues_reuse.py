"""CARD-051: ``image_to_puzzle.generate_clues`` stops reimplementing
run-length clue encoding and delegates to the canonical
``nonogram.clues.compute_clues`` (ADR-0012), matching how ``app.py`` already
calls ``clues.encode_line`` elsewhere.

AC-1 — for any grid ``create_puzzle_from_image`` produces, the computed
       clues are byte-for-byte identical to ``nonogram.clues.compute_clues``
       for the same grid, and match the old local ``encode_line``
       implementation's behavior (pinned against a corpus of real silhouette
       images already used elsewhere in this test tree).
AC-2 — a ragged grid raises a clear, named error (``ValueError``, matching
       ``compute_clues``'s ``zip(..., strict=True)`` guard) rather than an
       uncontrolled ``IndexError``.
"""

from pathlib import Path

import pytest

from nonogram import clues as clue_derivation
from nonogram.admin.image_to_puzzle import create_puzzle_from_image, generate_clues

FIXTURES = Path(__file__).parent / "fixtures"


def _old_encode_line(line):
    """Independent oracle: the exact pre-CARD-051 local ``encode_line``
    this test pins the new delegating implementation against, so a
    regression in ``nonogram.clues`` itself would still be caught here
    rather than the test tautologically re-deriving from the same function
    under test.
    """
    clues = []
    count = 0
    for cell in line:
        if cell:
            count += 1
        elif count > 0:
            clues.append(count)
            count = 0
    if count > 0:
        clues.append(count)
    return tuple(clues) if clues else (0,)


def _old_generate_clues(grid):
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    row_clues = tuple(_old_encode_line(grid[i]) for i in range(height))
    col_clues = tuple(
        _old_encode_line([grid[i][j] for i in range(height)]) for j in range(width)
    )
    return row_clues, col_clues


class TestAC1ClueEncodingMatchesCanonicalModule:
    def test_simple_synthetic_grid(self):
        grid = [
            [True, True, False, True],
            [False, False, False, False],
            [True, False, True, True],
        ]
        row_clues, col_clues = generate_clues(grid)
        expected = clue_derivation.compute_clues(grid)
        assert row_clues == expected.rows
        assert col_clues == expected.columns

    def test_all_empty_grid_uses_empty_line_marker(self):
        grid = [[False, False], [False, False]]
        row_clues, col_clues = generate_clues(grid)
        assert row_clues == ((0,), (0,))
        assert col_clues == ((0,), (0,))

    @pytest.mark.parametrize(
        "fixture_name", ["bird1.jpg", "dolphin1.jpg", "dove1.jpg"]
    )
    def test_real_silhouette_images_match_canonical_module_and_old_behavior(
        self, fixture_name
    ):
        from nonogram.admin.image_to_puzzle import image_to_grid

        image_path = FIXTURES / fixture_name
        assert image_path.exists(), f"missing test fixture: {image_path}"

        grid = image_to_grid(str(image_path), (20, 20))
        assert grid is not None

        row_clues, col_clues = generate_clues(grid)

        # Matches the canonical module directly.
        expected = clue_derivation.compute_clues(grid)
        assert row_clues == expected.rows
        assert col_clues == expected.columns

        # Matches the old, now-removed local reimplementation's behavior —
        # pinning that the switch to compute_clues() didn't silently change
        # what puzzles this function actually produces.
        old_rows, old_cols = _old_generate_clues(grid)
        assert row_clues == old_rows
        assert col_clues == old_cols

    def test_create_puzzle_from_image_stores_clues_matching_canonical_module(self):
        image_path = FIXTURES / "bird1.jpg"
        puzzle = create_puzzle_from_image(str(image_path), target_width=15, target_height=15)
        assert puzzle is not None

        expected = clue_derivation.compute_clues(puzzle["grid"])
        assert tuple(puzzle["clues_rows"]) == expected.rows
        assert tuple(puzzle["clues_cols"]) == expected.columns


class TestAC2RaggedGridRaisesNamedError:
    def test_ragged_grid_raises_value_error_not_index_error(self):
        ragged_grid = [
            [True, False, True],
            [False, True],  # short row
            [True, True, False],
        ]
        with pytest.raises(ValueError):
            generate_clues(ragged_grid)

    def test_ragged_grid_error_matches_compute_clues_behavior(self):
        ragged_grid = [[True, False], [False]]
        with pytest.raises(ValueError) as generate_clues_exc:
            generate_clues(ragged_grid)
        with pytest.raises(ValueError) as compute_clues_exc:
            clue_derivation.compute_clues(ragged_grid)
        # Same guard (zip(..., strict=True)) produces the same error type.
        assert type(generate_clues_exc.value) is type(compute_clues_exc.value)
