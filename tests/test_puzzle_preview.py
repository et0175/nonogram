"""Tests for puzzle preview modal feature (CARD-004i)."""

import pytest
import json


class TestPuzzlePreviewData:
    """Test puzzle preview data and rendering."""

    @pytest.mark.unit
    def test_puzzle_has_grid_for_preview(self, sample_puzzle):
        """Test that puzzle has grid data for preview."""
        if not sample_puzzle:
            pytest.skip("No sample puzzle generated")

        assert 'grid' in sample_puzzle
        assert isinstance(sample_puzzle['grid'], list)
        assert len(sample_puzzle['grid']) > 0

    @pytest.mark.unit
    def test_puzzle_has_clues_for_preview(self, sample_puzzle):
        """Test that puzzle has clues data for preview."""
        if not sample_puzzle:
            pytest.skip("No sample puzzle generated")

        assert 'clues_rows' in sample_puzzle
        assert 'clues_cols' in sample_puzzle
        assert isinstance(sample_puzzle['clues_rows'], list)
        assert isinstance(sample_puzzle['clues_cols'], list)

    @pytest.mark.unit
    def test_puzzle_grid_dimensions_match_clues(self, sample_puzzle):
        """Test that puzzle grid dimensions match clue counts."""
        if not sample_puzzle:
            pytest.skip("No sample puzzle generated")

        grid_height = len(sample_puzzle['grid'])
        clues_rows_count = len(sample_puzzle['clues_rows'])
        assert grid_height == clues_rows_count

        grid_width = len(sample_puzzle['grid'][0]) if grid_height > 0 else 0
        clues_cols_count = len(sample_puzzle['clues_cols'])
        assert grid_width == clues_cols_count

    @pytest.mark.unit
    def test_puzzle_has_difficulty_for_preview(self, sample_puzzle):
        """Test that puzzle has difficulty metrics for preview."""
        if not sample_puzzle:
            pytest.skip("No sample puzzle generated")

        assert 'difficulty_score' in sample_puzzle
        assert 'difficulty_tier' in sample_puzzle
        assert 1 <= sample_puzzle['difficulty_score'] <= 100
        assert sample_puzzle['difficulty_tier'] in ['Easy', 'Medium', 'Hard']

    @pytest.mark.unit
    def test_puzzle_has_quality_for_preview(self, sample_puzzle):
        """Test that puzzle has quality metrics for preview."""
        if not sample_puzzle:
            pytest.skip("No sample puzzle generated")

        assert 'quality_score' in sample_puzzle
        assert 1 <= sample_puzzle['quality_score'] <= 100

    @pytest.mark.unit
    def test_puzzle_size_matches_dimensions(self, sample_puzzle):
        """Test that puzzle size matches width/height."""
        if not sample_puzzle:
            pytest.skip("No sample puzzle generated")

        width = sample_puzzle['width']
        height = sample_puzzle['height']

        assert len(sample_puzzle['grid']) == height
        assert all(len(row) == width for row in sample_puzzle['grid'])

    @pytest.mark.unit
    def test_grid_contains_only_boolean_values(self, sample_puzzle):
        """Test that grid cells are only filled (True) or empty (False)."""
        if not sample_puzzle:
            pytest.skip("No sample puzzle generated")

        for row in sample_puzzle['grid']:
            for cell in row:
                assert isinstance(cell, (bool, int))
                assert cell in [True, False, 0, 1]


class TestGridRendering:
    """Test grid rendering for preview."""

    @pytest.mark.unit
    def test_grid_renders_for_small_puzzle(self, generator):
        """Test that grid renders for small puzzle (10x10)."""
        puzzles = generator.generate_batch(count=1, sizes=[10])
        if not puzzles:
            pytest.skip("Could not generate puzzle")

        puzzle = puzzles[0]
        assert len(puzzle['grid']) == 10
        assert all(len(row) == 10 for row in puzzle['grid'])

    @pytest.mark.unit
    def test_grid_renders_for_medium_puzzle(self, generator):
        """Test that grid renders for medium puzzle (20x20)."""
        puzzles = generator.generate_batch(count=1, sizes=[20])
        if not puzzles:
            pytest.skip("Could not generate puzzle")

        puzzle = puzzles[0]
        assert len(puzzle['grid']) == 20
        assert all(len(row) == 20 for row in puzzle['grid'])

    @pytest.mark.unit
    def test_grid_renders_for_large_puzzle(self, generator):
        """Test that grid renders for large puzzle (30x30)."""
        puzzles = generator.generate_batch(count=1, sizes=[30])
        if not puzzles:
            pytest.skip("Could not generate puzzle")

        puzzle = puzzles[0]
        assert len(puzzle['grid']) == 30
        assert all(len(row) == 30 for row in puzzle['grid'])


class TestCluesForPreview:
    """Test clue formatting for preview."""

    @pytest.mark.unit
    def test_clues_are_list_of_lists(self, sample_puzzle):
        """Test that clues are properly formatted as list of lists."""
        if not sample_puzzle:
            pytest.skip("No sample puzzle generated")

        clues_rows = sample_puzzle['clues_rows']
        clues_cols = sample_puzzle['clues_cols']

        assert isinstance(clues_rows, list)
        assert isinstance(clues_cols, list)

        # Each clue line should be a list of integers or tuple
        for row_clues in clues_rows:
            assert isinstance(row_clues, (list, tuple))
            assert all(isinstance(c, int) for c in row_clues)

        for col_clues in clues_cols:
            assert isinstance(col_clues, (list, tuple))
            assert all(isinstance(c, int) for c in col_clues)

    @pytest.mark.unit
    def test_empty_row_clue_is_zero(self, sample_puzzle):
        """Test that empty row/column has clue [0]."""
        # This tests the convention that empty lines encode to (0,)
        if not sample_puzzle:
            pytest.skip("No sample puzzle generated")

        # Empty rows should have clue [0]
        for i, row_clues in enumerate(sample_puzzle['clues_rows']):
            row_filled = any(sample_puzzle['grid'][i])
            if not row_filled:
                assert row_clues == (0,) or row_clues == [0]


class TestPuzzlePreviewAPI:
    """Test API endpoints for puzzle preview."""

    @pytest.mark.integration
    def test_get_single_puzzle_by_id(self, puzzle_review_service, sample_puzzle):
        """Test retrieving single puzzle by ID for preview."""
        if not sample_puzzle:
            pytest.skip("No sample puzzle generated")

        puzzle_id = puzzle_review_service.add_puzzle(
            grid=sample_puzzle['grid'],
            clues_rows=sample_puzzle['clues_rows'],
            clues_cols=sample_puzzle['clues_cols'],
            width=sample_puzzle['width'],
            height=sample_puzzle['height'],
            theme=sample_puzzle['theme'],
            difficulty_score=sample_puzzle['difficulty_score'],
            difficulty_tier=sample_puzzle['difficulty_tier'],
            quality_score=sample_puzzle['quality_score'],
            recognizability=sample_puzzle.get('recognizability', 'medium'),
            strategies_used=sample_puzzle.get('strategies_used', []),
        )

        puzzle = puzzle_review_service.get_puzzle(puzzle_id)

        assert puzzle is not None
        assert puzzle['id'] == puzzle_id
        assert puzzle['grid'] == sample_puzzle['grid']
        assert puzzle['clues_rows'] == sample_puzzle['clues_rows']
        assert puzzle['clues_cols'] == sample_puzzle['clues_cols']

    @pytest.mark.integration
    def test_puzzle_preview_has_all_required_fields(self, puzzle_review_service, sample_puzzle):
        """Test that puzzle preview has all fields needed for display."""
        if not sample_puzzle:
            pytest.skip("No sample puzzle generated")

        puzzle_id = puzzle_review_service.add_puzzle(
            grid=sample_puzzle['grid'],
            clues_rows=sample_puzzle['clues_rows'],
            clues_cols=sample_puzzle['clues_cols'],
            width=sample_puzzle['width'],
            height=sample_puzzle['height'],
            theme=sample_puzzle['theme'],
            difficulty_score=sample_puzzle['difficulty_score'],
            difficulty_tier=sample_puzzle['difficulty_tier'],
            quality_score=sample_puzzle['quality_score'],
            recognizability=sample_puzzle.get('recognizability', 'medium'),
            strategies_used=sample_puzzle.get('strategies_used', []),
        )

        puzzle = puzzle_review_service.get_puzzle(puzzle_id)

        required_fields = [
            'id', 'grid', 'clues_rows', 'clues_cols',
            'width', 'height', 'difficulty_score', 'difficulty_tier',
            'quality_score', 'theme'
        ]

        for field in required_fields:
            assert field in puzzle, f"Missing field: {field}"


# Run with: pytest tests/test_puzzle_preview.py -v
# Run just unit tests: pytest tests/test_puzzle_preview.py -m unit -v
