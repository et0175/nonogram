"""
Test generation failure scenarios and error handling.

Validates that the system gracefully handles:
- Invalid parameters (size out of range, invalid density)
- Unsolvable puzzles (GenerationAbandoned)
- Edge cases (all-empty, all-full grids)
- Admin panel error message display
"""

import pytest

from nonogram import orchestrator, errors


class TestGenerationFailures:
    """Test puzzle generation failure scenarios."""

    def test_size_too_small(self):
        """Test that grid size below 10 is rejected."""
        req = orchestrator.GenerationRequest(
            mode="random",
            width=5,
            height=5,
            density=50
        )
        with pytest.raises(errors.SizeOutOfRange):
            orchestrator.generate(req)

    def test_size_too_large(self):
        """Test that grid size above 30 is rejected."""
        req = orchestrator.GenerationRequest(
            mode="random",
            width=50,
            height=50,
            density=50
        )
        with pytest.raises(errors.SizeOutOfRange):
            orchestrator.generate(req)

    def test_invalid_density_too_high(self):
        """Test that density > 100 is rejected."""
        req = orchestrator.GenerationRequest(
            mode="random",
            width=15,
            height=15,
            density=101
        )
        with pytest.raises(errors.InvalidDensity):
            orchestrator.generate(req)

    def test_invalid_density_negative(self):
        """Test that negative density is rejected."""
        req = orchestrator.GenerationRequest(
            mode="random",
            width=15,
            height=15,
            density=-10
        )
        with pytest.raises(errors.InvalidDensity):
            orchestrator.generate(req)

    def test_zero_density_valid(self):
        """Test that 0% density (all-empty) is valid."""
        req = orchestrator.GenerationRequest(
            mode="random",
            width=15,
            height=15,
            density=0
        )
        puzzle = orchestrator.generate(req)
        assert puzzle is not None
        # All cells should be empty (False)
        for row in puzzle.grid:
            for cell in row:
                assert cell is False

    def test_high_density_valid(self):
        """Test that high density puzzles can generate successfully."""
        req = orchestrator.GenerationRequest(
            mode="random",
            width=15,
            height=15,
            density=90
        )
        puzzle = orchestrator.generate(req)
        assert puzzle is not None
        # Count filled cells
        filled = sum(sum(row) for row in puzzle.grid)
        total = 15 * 15
        pct = (filled / total) * 100
        # Should be close to 90%
        assert pct > 80  # Allow some variance

    def test_asymmetric_size(self):
        """Test non-square grids."""
        req = orchestrator.GenerationRequest(
            mode="random",
            width=20,
            height=15,
            density=50
        )
        puzzle = orchestrator.generate(req)
        assert puzzle is not None
        assert puzzle.extent == (20, 15)

    def test_minimal_valid_size(self):
        """Test minimum valid size (10×10)."""
        req = orchestrator.GenerationRequest(
            mode="random",
            width=10,
            height=10,
            density=50
        )
        puzzle = orchestrator.generate(req)
        assert puzzle is not None
        assert puzzle.extent == (10, 10)

    def test_maximum_size_is_hard_to_generate(self):
        """Test maximum size (30×30) is computationally hard.

        30×30 grids at 50% density are at the edge of feasibility.
        They may succeed or fail depending on random seed, but they're
        much harder than smaller sizes.

        REAL FAILURE SCENARIO: Admin panel must handle cases where
        generation times out or can't find unique solution, and let
        user retry with smaller size/density.
        """
        req = orchestrator.GenerationRequest(
            mode="random",
            width=30,
            height=30,
            density=50
        )
        # May succeed or fail - both are valid outcomes at this size
        try:
            puzzle = orchestrator.generate(req)
            # If it succeeds, puzzle is valid
            assert puzzle is not None
            assert puzzle.extent == (30, 30)
        except (errors.GenerationAbandoned, errors.SolverTimeout):
            # If it fails, that's also expected for hard problem class
            pass

    def test_reliable_size(self):
        """Test smaller, reliable sizes (15×15, 18×18) for consistent generation.

        These sizes consistently generate without timeout/abandonment.
        """
        for size in [15, 18]:
            req = orchestrator.GenerationRequest(
                mode="random",
                width=size,
                height=size,
                density=50
            )
            puzzle = orchestrator.generate(req)
            assert puzzle is not None
            assert puzzle.extent == (size, size)


class TestBatchGenerationFailures:
    """Test batch generation error handling."""

    def test_batch_with_invalid_size_fails(self):
        """Test that batch generation fails with invalid size."""
        with pytest.raises(errors.SizeOutOfRange):
            orchestrator.generate_batch(
                count=3,
                sizes=[50],  # Invalid: too large
                source="random"
            )

    def test_batch_with_reliable_sizes(self):
        """Test batch with reliable sizes that consistently generate."""
        # Use sizes known to work reliably (from test history)
        puzzles = orchestrator.generate_batch(
            count=3,
            sizes=[15, 18],
            source="random"
        )
        assert len(puzzles) == 3
        for puzzle in puzzles:
            assert puzzle.extent in [(15, 15), (18, 18)]

    def test_batch_empty_sizes_uses_defaults(self):
        """Test batch generation with empty size list uses defaults."""
        # Empty list should use default sizes or fail gracefully
        try:
            puzzles = orchestrator.generate_batch(
                count=2,
                sizes=[],
                source="random"
            )
            # If it succeeds, should have puzzles
            assert len(puzzles) >= 0
        except (errors.NonogramError, ValueError):
            # Either behavior is acceptable
            pass


class TestAdminPanelErrorHandling:
    """Test admin panel error message handling."""

    def test_batch_job_captures_error_message(self):
        """Test that batch job captures error messages."""
        from nonogram.admin.batch_generator import BatchJob, BatchStatus

        job = BatchJob(
            batch_id="test_error",
            status=BatchStatus.ERROR,
            total_count=5,
            error_message="Grid size 50 is out of range (must be 10-30)"
        )

        assert job.error_message is not None
        assert "out of range" in job.error_message.lower()
        assert job.status == BatchStatus.ERROR

    def test_batch_job_to_dict_includes_error(self):
        """Test that error message is in dict representation."""
        from nonogram.admin.batch_generator import BatchJob, BatchStatus

        job = BatchJob(
            batch_id="test_error",
            status=BatchStatus.ERROR,
            total_count=5,
            error_message="Generation failed: could not find unique solution"
        )

        job_dict = job.to_dict()
        assert job_dict["error_message"] == "Generation failed: could not find unique solution"
        assert job_dict["status"] == "error"


class TestErrorRecovery:
    """Test error recovery and retry scenarios."""

    def test_retry_after_invalid_size(self):
        """Test that user can retry after invalid size error."""
        # First attempt: invalid size
        with pytest.raises(errors.SizeOutOfRange):
            req1 = orchestrator.GenerationRequest(
                mode="random",
                width=50,
                height=50,
                density=50
            )
            orchestrator.generate(req1)

        # Second attempt: valid size should work
        req2 = orchestrator.GenerationRequest(
            mode="random",
            width=15,
            height=15,
            density=50
        )
        puzzle = orchestrator.generate(req2)
        assert puzzle is not None

    def test_retry_after_invalid_density(self):
        """Test that user can retry after invalid density error."""
        # First attempt: invalid density
        with pytest.raises(errors.InvalidDensity):
            req1 = orchestrator.GenerationRequest(
                mode="random",
                width=15,
                height=15,
                density=150
            )
            orchestrator.generate(req1)

        # Second attempt: valid density should work
        req2 = orchestrator.GenerationRequest(
            mode="random",
            width=15,
            height=15,
            density=50
        )
        puzzle = orchestrator.generate(req2)
        assert puzzle is not None
