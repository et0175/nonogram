"""End-to-end tests for batch generation and puzzle storage."""

import pytest
from nonogram.generation import get_generator
from nonogram.admin.puzzle_review import get_puzzle_review_service


class TestBatchGenerationE2E:
    """Test complete batch generation workflow."""

    def test_batch_generation_and_storage(self):
        """Generate puzzles and store in database."""
        # Generate batch
        generator = get_generator(seed=2026)
        puzzles = generator.generate_batch(
            count=50,
            sizes=[10, 15, 20, 25, 30],
            theme='christmas'
        )

        assert len(puzzles) == 50, "Should generate 50 puzzles"
        assert all(p['theme'] == 'christmas' for p in puzzles)

        # Store puzzles
        review_service = get_puzzle_review_service()
        initial_stats = review_service.get_stats()

        for puzzle in puzzles:
            review_service.add_puzzle(
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

        # Verify storage
        final_stats = review_service.get_stats()

        assert final_stats['draft'] >= initial_stats['draft'] + 50, \
            f"Should have 50 more draft puzzles. Before: {initial_stats['draft']}, After: {final_stats['draft']}"
        assert final_stats['total'] >= initial_stats['total'] + 50, \
            f"Should have 50 more total puzzles. Before: {initial_stats['total']}, After: {final_stats['total']}"

    def test_puzzle_metrics_are_valid(self):
        """Verify generated puzzles have valid metrics."""
        generator = get_generator(seed=42)
        puzzles = generator.generate_batch(count=50, sizes=[15, 20])

        for puzzle in puzzles:
            # Verify grid
            assert isinstance(puzzle['grid'], list)
            assert len(puzzle['grid']) == puzzle['height']

            # Verify clues
            assert isinstance(puzzle['clues_rows'], list)
            assert isinstance(puzzle['clues_cols'], list)

            # Verify metrics
            assert 1 <= puzzle['difficulty_score'] <= 100, \
                f"Difficulty score out of range: {puzzle['difficulty_score']}"
            assert puzzle['difficulty_tier'] in ['Easy', 'Medium', 'Hard'], \
                f"Invalid difficulty tier: {puzzle['difficulty_tier']}"
            assert 1 <= puzzle['quality_score'] <= 100, \
                f"Quality score out of range: {puzzle['quality_score']}"
            assert puzzle['theme'] in ['christmas', 'halloween', 'easter', 'valentine', 'generic']
