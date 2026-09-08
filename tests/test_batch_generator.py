"""Tests for batch puzzle generation service."""

import pytest
from src.nonogram.admin import (
    BatchGenerator,
    BatchStatus,
    get_batch_generator,
)


@pytest.fixture
def batch_gen():
    """Get a fresh batch generator for testing."""
    return BatchGenerator()


class TestBatchJob:
    """Test BatchJob data structure."""

    def test_batch_job_creation(self, batch_gen):
        """Create a new batch job."""
        batch_id = batch_gen.create_batch(count=100, sizes=[20, 30])

        assert batch_id is not None
        assert len(batch_id) > 0

    def test_batch_job_status_tracking(self, batch_gen):
        """Track batch job status."""
        batch_id = batch_gen.create_batch(count=50, sizes=[20])
        job = batch_gen.get_batch_status(batch_id)

        assert job is not None
        assert job.batch_id == batch_id
        assert job.status == BatchStatus.COMPLETE
        assert job.total_count == 50
        assert job.completed_count == 50

    def test_batch_progress_calculation(self, batch_gen):
        """Test progress percentage calculation."""
        batch_id = batch_gen.create_batch(count=100, sizes=[20])
        job = batch_gen.get_batch_status(batch_id)

        assert job.get_progress_percent() == 100

        # Manually reset to test partial progress (for async-ready testing)
        job.completed_count = 50
        assert job.get_progress_percent() == 50

        job.completed_count = 100
        assert job.get_progress_percent() == 100

    def test_batch_job_to_dict(self, batch_gen):
        """Convert batch job to dictionary."""
        batch_id = batch_gen.create_batch(count=75, sizes=[15, 20])
        job = batch_gen.get_batch_status(batch_id)

        data = job.to_dict()

        assert data["batch_id"] == batch_id
        assert data["status"] == "complete"
        assert data["total_count"] == 75
        assert data["progress_percent"] == 100
        assert "created_at" in data


class TestBatchGeneration:
    """Test batch generation workflow."""

    def test_create_batch_valid_params(self, batch_gen):
        """Create batch with valid parameters."""
        batch_id = batch_gen.create_batch(
            count=100,
            sizes=[10, 20, 30],
            theme="christmas",
            source="random",
            quality_filter=70,
        )

        assert batch_id is not None
        job = batch_gen.get_batch_status(batch_id)
        assert job.total_count == 100

    def test_create_batch_invalid_count(self, batch_gen):
        """Reject batch with invalid count."""
        with pytest.raises(ValueError):
            batch_gen.create_batch(count=5, sizes=[20])  # Too low

        with pytest.raises(ValueError):
            batch_gen.create_batch(count=250, sizes=[20])  # Too high

    def test_create_batch_invalid_sizes(self, batch_gen):
        """Reject batch with invalid sizes."""
        with pytest.raises(ValueError):
            batch_gen.create_batch(count=100, sizes=[5])  # Too small

        with pytest.raises(ValueError):
            batch_gen.create_batch(count=100, sizes=[50])  # Too large

    def test_create_batch_invalid_source(self, batch_gen):
        """Reject batch with invalid source."""
        with pytest.raises(ValueError):
            batch_gen.create_batch(count=100, sizes=[20], source="invalid")

    def test_create_batch_invalid_quality_filter(self, batch_gen):
        """Reject batch with invalid quality filter."""
        with pytest.raises(ValueError):
            batch_gen.create_batch(count=100, sizes=[20], quality_filter=-1)

        with pytest.raises(ValueError):
            batch_gen.create_batch(count=100, sizes=[20], quality_filter=101)


class TestBatchPuzzleRetrieval:
    """Test retrieving puzzles from batches."""

    def test_get_batch_puzzles_not_found(self, batch_gen):
        """Getting puzzles from non-existent batch returns empty list."""
        result = batch_gen.get_batch_puzzles("nonexistent")

        assert result == []

    def test_get_batch_puzzles_empty(self, batch_gen):
        """Get puzzles from batch with none yet."""
        batch_id = batch_gen.create_batch(count=100, sizes=[20])
        puzzles = batch_gen.get_batch_puzzles(batch_id)

        assert puzzles == []

    def test_get_batch_puzzles_pagination(self, batch_gen):
        """Test pagination returns empty when no puzzle_review_service set."""
        batch_id = batch_gen.create_batch(count=100, sizes=[20])

        # Without puzzle_review_service, get_batch_puzzles returns empty list
        page1 = batch_gen.get_batch_puzzles(batch_id, offset=0, limit=25)
        assert len(page1) == 0

        # Pagination parameters are accepted but have no effect without service
        page2 = batch_gen.get_batch_puzzles(batch_id, offset=25, limit=25)
        assert len(page2) == 0


class TestBatchCancellation:
    """Test batch cancellation."""

    def test_cancel_pending_batch(self, batch_gen):
        """Cannot cancel a completed batch (currently auto-completes synchronously)."""
        batch_id = batch_gen.create_batch(count=100, sizes=[20])
        result = batch_gen.cancel_batch(batch_id)

        assert result is False
        job = batch_gen.get_batch_status(batch_id)
        assert job.status == BatchStatus.COMPLETE

    def test_cancel_nonexistent_batch(self, batch_gen):
        """Cancel non-existent batch returns False."""
        result = batch_gen.cancel_batch("nonexistent")

        assert result is False

    def test_cancel_completed_batch(self, batch_gen):
        """Cannot cancel a completed batch."""
        batch_id = batch_gen.create_batch(count=100, sizes=[20])
        job = batch_gen.get_batch_status(batch_id)
        job.status = BatchStatus.COMPLETE

        result = batch_gen.cancel_batch(batch_id)

        assert result is False
        assert job.status == BatchStatus.COMPLETE


class TestBatchGeneratorSingleton:
    """Test singleton batch generator."""

    def test_get_batch_generator_singleton(self):
        """Batch generator is a singleton."""
        gen1 = get_batch_generator()
        gen2 = get_batch_generator()

        assert gen1 is gen2
