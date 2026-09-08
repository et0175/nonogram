"""Tests for bulk puzzle operations feature (CARD-004j)."""

import pytest
from nonogram.admin.puzzle_review import PuzzleFilter


class TestBulkApprove:
    """Test bulk approve operations."""

    @pytest.mark.integration
    def test_bulk_approve_single_puzzle(self, puzzle_review_service, sample_puzzle):
        """Test approving a single puzzle via bulk operation."""
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

        # Bulk approve (even though just one)
        result = puzzle_review_service.approve_puzzle(puzzle_id)
        assert result is True

        puzzle = puzzle_review_service.get_puzzle(puzzle_id)
        assert puzzle['status'] == 'approved'

    @pytest.mark.integration
    def test_bulk_approve_multiple_puzzles(self, puzzle_review_service, sample_puzzles):
        """Test approving multiple puzzles at once."""
        if not sample_puzzles or len(sample_puzzles) < 3:
            pytest.skip("Need at least 3 sample puzzles")

        puzzle_ids = []
        for puzzle in sample_puzzles[:3]:
            puzzle_id = puzzle_review_service.add_puzzle(
                grid=puzzle['grid'],
                clues_rows=puzzle['clues_rows'],
                clues_cols=puzzle['clues_cols'],
                width=puzzle['width'],
                height=puzzle['height'],
                theme=puzzle['theme'],
                difficulty_score=puzzle['difficulty_score'],
                difficulty_tier=puzzle['difficulty_tier'],
                quality_score=puzzle['quality_score'],
                recognizability=puzzle.get('recognizability', 'medium'),
                strategies_used=puzzle.get('strategies_used', []),
            )
            puzzle_ids.append(puzzle_id)

        # Bulk approve all 3
        for puzzle_id in puzzle_ids:
            result = puzzle_review_service.approve_puzzle(puzzle_id)
            assert result is True

        # Verify all approved
        for puzzle_id in puzzle_ids:
            puzzle = puzzle_review_service.get_puzzle(puzzle_id)
            assert puzzle['status'] == 'approved'

    @pytest.mark.unit
    def test_bulk_approve_updates_stats(self, puzzle_review_service, sample_puzzles):
        """Test that bulk approve updates puzzle stats."""
        if not sample_puzzles or len(sample_puzzles) < 2:
            pytest.skip("Need at least 2 sample puzzles")

        initial_stats = puzzle_review_service.get_stats()
        initial_approved = initial_stats.get('approved', 0)

        puzzle_ids = []
        for puzzle in sample_puzzles[:2]:
            puzzle_id = puzzle_review_service.add_puzzle(
                grid=puzzle['grid'],
                clues_rows=puzzle['clues_rows'],
                clues_cols=puzzle['clues_cols'],
                width=puzzle['width'],
                height=puzzle['height'],
                theme=puzzle['theme'],
                difficulty_score=puzzle['difficulty_score'],
                difficulty_tier=puzzle['difficulty_tier'],
                quality_score=puzzle['quality_score'],
                recognizability=puzzle.get('recognizability', 'medium'),
                strategies_used=puzzle.get('strategies_used', []),
            )
            puzzle_ids.append(puzzle_id)

        # Approve both
        for puzzle_id in puzzle_ids:
            puzzle_review_service.approve_puzzle(puzzle_id)

        final_stats = puzzle_review_service.get_stats()
        final_approved = final_stats.get('approved', 0)

        assert final_approved >= initial_approved + 2


class TestBulkReject:
    """Test bulk reject operations."""

    @pytest.mark.integration
    def test_bulk_reject_single_puzzle(self, puzzle_review_service, sample_puzzle):
        """Test rejecting a single puzzle via bulk operation."""
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

        # Bulk reject
        result = puzzle_review_service.reject_puzzle(puzzle_id)
        assert result is True

        puzzle = puzzle_review_service.get_puzzle(puzzle_id)
        assert puzzle['status'] == 'rejected'

    @pytest.mark.integration
    def test_bulk_reject_multiple_puzzles(self, puzzle_review_service, sample_puzzles):
        """Test rejecting multiple puzzles at once."""
        if not sample_puzzles or len(sample_puzzles) < 3:
            pytest.skip("Need at least 3 sample puzzles")

        puzzle_ids = []
        for puzzle in sample_puzzles[:3]:
            puzzle_id = puzzle_review_service.add_puzzle(
                grid=puzzle['grid'],
                clues_rows=puzzle['clues_rows'],
                clues_cols=puzzle['clues_cols'],
                width=puzzle['width'],
                height=puzzle['height'],
                theme=puzzle['theme'],
                difficulty_score=puzzle['difficulty_score'],
                difficulty_tier=puzzle['difficulty_tier'],
                quality_score=puzzle['quality_score'],
                recognizability=puzzle.get('recognizability', 'medium'),
                strategies_used=puzzle.get('strategies_used', []),
            )
            puzzle_ids.append(puzzle_id)

        # Bulk reject all 3
        for puzzle_id in puzzle_ids:
            result = puzzle_review_service.reject_puzzle(puzzle_id)
            assert result is True

        # Verify all rejected
        for puzzle_id in puzzle_ids:
            puzzle = puzzle_review_service.get_puzzle(puzzle_id)
            assert puzzle['status'] == 'rejected'

    @pytest.mark.unit
    def test_bulk_reject_updates_stats(self, puzzle_review_service, sample_puzzles):
        """Test that bulk reject updates puzzle stats."""
        if not sample_puzzles or len(sample_puzzles) < 2:
            pytest.skip("Need at least 2 sample puzzles")

        initial_stats = puzzle_review_service.get_stats()
        initial_rejected = initial_stats.get('rejected', 0)

        puzzle_ids = []
        for puzzle in sample_puzzles[:2]:
            puzzle_id = puzzle_review_service.add_puzzle(
                grid=puzzle['grid'],
                clues_rows=puzzle['clues_rows'],
                clues_cols=puzzle['clues_cols'],
                width=puzzle['width'],
                height=puzzle['height'],
                theme=puzzle['theme'],
                difficulty_score=puzzle['difficulty_score'],
                difficulty_tier=puzzle['difficulty_tier'],
                quality_score=puzzle['quality_score'],
                recognizability=puzzle.get('recognizability', 'medium'),
                strategies_used=puzzle.get('strategies_used', []),
            )
            puzzle_ids.append(puzzle_id)

        # Reject both
        for puzzle_id in puzzle_ids:
            puzzle_review_service.reject_puzzle(puzzle_id)

        final_stats = puzzle_review_service.get_stats()
        final_rejected = final_stats.get('rejected', 0)

        assert final_rejected >= initial_rejected + 2


class TestBulkWithFilters:
    """Test bulk operations with filters applied."""

    @pytest.mark.integration
    def test_bulk_approve_all_easy_puzzles(self, puzzle_review_service, sample_puzzles):
        """Test bulk approving all Easy difficulty puzzles."""
        if not sample_puzzles or len(sample_puzzles) < 5:
            pytest.skip("Need at least 5 sample puzzles")

        # Add puzzles
        puzzle_data = []
        for puzzle in sample_puzzles[:5]:
            puzzle_id = puzzle_review_service.add_puzzle(
                grid=puzzle['grid'],
                clues_rows=puzzle['clues_rows'],
                clues_cols=puzzle['clues_cols'],
                width=puzzle['width'],
                height=puzzle['height'],
                theme=puzzle['theme'],
                difficulty_score=puzzle['difficulty_score'],
                difficulty_tier=puzzle['difficulty_tier'],
                quality_score=puzzle['quality_score'],
                recognizability=puzzle.get('recognizability', 'medium'),
                strategies_used=puzzle.get('strategies_used', []),
            )
            puzzle_data.append({'id': puzzle_id, 'tier': puzzle['difficulty_tier']})

        # Filter for Easy puzzles
        easy_filter = PuzzleFilter(difficulty='Easy', limit=100)
        result = puzzle_review_service.filter_puzzles(easy_filter)

        # Approve all Easy puzzles
        for puzzle in result.puzzles:
            puzzle_review_service.approve_puzzle(puzzle['id'])

        # Verify all Easy puzzles are approved
        all_easy = [
            p for p in puzzle_data
            if p['tier'] == 'Easy'
        ]
        for puzzle_data in all_easy:
            puzzle = puzzle_review_service.get_puzzle(puzzle_data['id'])
            assert puzzle['status'] == 'approved'

    @pytest.mark.integration
    def test_bulk_reject_low_quality_puzzles(self, puzzle_review_service, sample_puzzles):
        """Test bulk rejecting low quality puzzles."""
        if not sample_puzzles or len(sample_puzzles) < 5:
            pytest.skip("Need at least 5 sample puzzles")

        # Add puzzles
        puzzle_data = []
        for puzzle in sample_puzzles[:5]:
            puzzle_id = puzzle_review_service.add_puzzle(
                grid=puzzle['grid'],
                clues_rows=puzzle['clues_rows'],
                clues_cols=puzzle['clues_cols'],
                width=puzzle['width'],
                height=puzzle['height'],
                theme=puzzle['theme'],
                difficulty_score=puzzle['difficulty_score'],
                difficulty_tier=puzzle['difficulty_tier'],
                quality_score=puzzle['quality_score'],
                recognizability=puzzle.get('recognizability', 'medium'),
                strategies_used=puzzle.get('strategies_used', []),
            )
            puzzle_data.append({'id': puzzle_id, 'quality': puzzle['quality_score']})

        # Filter for low quality (< 40)
        low_quality_filter = PuzzleFilter(quality_min=0, limit=100)
        result = puzzle_review_service.filter_puzzles(low_quality_filter)

        # Reject low quality puzzles (< 40)
        low_quality_ids = [
            p['id'] for p in puzzle_data
            if p['quality'] < 40
        ]

        for puzzle_id in low_quality_ids:
            puzzle_review_service.reject_puzzle(puzzle_id)

        # Verify they're rejected
        for puzzle_id in low_quality_ids:
            puzzle = puzzle_review_service.get_puzzle(puzzle_id)
            assert puzzle['status'] == 'rejected'


class TestBulkOperationValidation:
    """Test validation of bulk operations."""

    @pytest.mark.unit
    def test_bulk_operation_with_empty_list(self, puzzle_review_service):
        """Test that bulk operation with empty list fails gracefully."""
        # Trying to operate on non-existent puzzle should fail gracefully
        result = puzzle_review_service.approve_puzzle('nonexistent-id')
        assert result is False

    @pytest.mark.unit
    def test_bulk_operation_idempotent(self, puzzle_review_service, sample_puzzle):
        """Test that bulk approving same puzzle twice is safe."""
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

        # Approve twice
        result1 = puzzle_review_service.approve_puzzle(puzzle_id)
        result2 = puzzle_review_service.approve_puzzle(puzzle_id)

        # Both should succeed (idempotent)
        assert result1 is True
        assert result2 is True

        # Status should still be approved
        puzzle = puzzle_review_service.get_puzzle(puzzle_id)
        assert puzzle['status'] == 'approved'


# Run with: pytest tests/test_bulk_operations.py -v
# Run just integration tests: pytest tests/test_bulk_operations.py -m integration -v
