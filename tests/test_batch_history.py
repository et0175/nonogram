"""Tests for batch history and tracking feature (CARD-004h).

Every test here is about *metadata* — ids, sizes, themes, statuses, timestamps,
ordering. None needs a large batch, and until CARD-083 this file asked for 900
real unseeded draws per run to make those assertions, costing 30s of every
suite run. Counts are now the minimum `create_batch` accepts; the sizes a test
actually asserts on are unchanged, and the ones it does not are 15 (measured
0/200 abandonments, against 4/200 at 25x25 — see `tests/test_wave1_e2e.py`).

**Exact batch counts are no longer asserted.** CARD-083 made `generate_batch`
skip a candidate it had to abandon rather than losing the whole batch, so
`puzzle_count == count` is a promise the system deliberately stopped making.
What the tests pin instead is the claim that survives and is what they were
always about: the batch *tracks* how many puzzles it stored, and that number
agrees with the rows actually in it.
"""

import pytest
from datetime import datetime, timedelta
from nonogram.admin.batch_generator import get_batch_generator, BatchStatus, BatchJob


class TestBatchHistoryStorage:
    """Test batch persistence and history tracking."""

    @pytest.mark.unit
    def test_batch_stored_with_metadata(self, batch_generator_service):
        """Test that batch is stored with all required metadata."""
        batch_id = batch_generator_service.create_batch(
            count=10,
            sizes=[15, 20],
            theme='christmas'
        )

        job = batch_generator_service.get_batch_status(batch_id)

        assert job is not None
        assert job.batch_id == batch_id
        assert job.count == 10
        assert job.sizes == [15, 20]
        assert job.theme == 'christmas'
        assert job.created_at is not None
        # Synchronous generation completes immediately (async is CARD-004k)
        assert job.status == BatchStatus.COMPLETE

    @pytest.mark.unit
    def test_batch_tracks_completion_time(self, batch_generator_service):
        """Test that batch completion time is recorded."""
        batch_id = batch_generator_service.create_batch(count=10, sizes=[15])

        # Batch completes synchronously on create (generation happens in create_batch)
        job = batch_generator_service.get_batch_status(batch_id)

        assert job.completed_at is not None
        assert job.completed_at >= job.created_at
        assert job.status == BatchStatus.COMPLETE

    @pytest.mark.unit
    def test_batch_records_error_message(self, batch_generator_service):
        """Test that batch stores error message on failure."""
        batch_id = batch_generator_service.create_batch(count=10, sizes=[15])

        # Simulate error
        error_msg = "Database connection failed"
        batch_generator_service.jobs[batch_id].status = BatchStatus.ERROR
        batch_generator_service.jobs[batch_id].error_message = error_msg

        job = batch_generator_service.get_batch_status(batch_id)

        assert job.error_message == error_msg
        assert job.status == BatchStatus.ERROR

    @pytest.mark.unit
    def test_batch_tracks_puzzle_count(self, batch_generator_service, puzzle_review_service):
        """Test that batch tracks how many puzzles were stored."""
        batch_id = batch_generator_service.create_batch(count=10, sizes=[15])

        # `create_batch` already generates synchronously, so the explicit
        # call that used to sit here generated the batch a second time —
        # twice the draws, and a store holding twice as many rows as
        # `puzzle_count` claimed. Harmless while nothing compared the two;
        # CARD-083's `puzzle_count == len(stored)` assertion is what
        # surfaced it.

        job = batch_generator_service.get_batch_status(batch_id)

        # "Tracks how many were stored" — asserted against the rows that are
        # actually there, not against the number requested. Since CARD-083 a
        # batch may skip a candidate it had to abandon, so `== count` is a
        # promise the system deliberately stopped making; `== len(rows)` is the
        # claim this test was always about and is now unconditionally true.
        stored = batch_generator_service.get_batch_puzzles(batch_id, limit=100)
        assert job.puzzle_count == len(stored)
        assert 0 < job.puzzle_count <= 10


class TestBatchListAndFiltering:
    """Test batch list retrieval and filtering."""

    @pytest.mark.unit
    def test_get_all_batches(self, batch_generator_service):
        """Test retrieving all batches."""
        # Create multiple batches
        batch_id1 = batch_generator_service.create_batch(count=10, sizes=[15])
        batch_id2 = batch_generator_service.create_batch(count=10, sizes=[15])

        batches = list(batch_generator_service.jobs.values())

        assert len(batches) >= 2
        assert any(b.batch_id == batch_id1 for b in batches)
        assert any(b.batch_id == batch_id2 for b in batches)

    @pytest.mark.unit
    def test_filter_batches_by_status_complete(self, batch_generator_service):
        """Test filtering batches by COMPLETE status."""
        batch_id1 = batch_generator_service.create_batch(count=10, sizes=[15])
        batch_id2 = batch_generator_service.create_batch(count=10, sizes=[15])

        # Both batches complete synchronously after creation
        completed = [
            b for b in batch_generator_service.jobs.values()
            if b.status == BatchStatus.COMPLETE
        ]

        assert len(completed) >= 2
        assert any(b.batch_id == batch_id1 for b in completed)
        assert any(b.batch_id == batch_id2 for b in completed)

    @pytest.mark.unit
    def test_filter_batches_by_status_error(self, batch_generator_service):
        """Test filtering batches by ERROR status."""
        batch_id = batch_generator_service.create_batch(count=10, sizes=[15])

        # Mark as error
        batch_generator_service.jobs[batch_id].status = BatchStatus.ERROR
        batch_generator_service.jobs[batch_id].error_message = "Test error"

        errors = [
            b for b in batch_generator_service.jobs.values()
            if b.status == BatchStatus.ERROR
        ]

        assert any(b.batch_id == batch_id for b in errors)

    @pytest.mark.unit
    def test_filter_batches_by_status_pending(self, batch_generator_service):
        """Test filtering batches by status."""
        batch_id = batch_generator_service.create_batch(count=10, sizes=[15])

        # Batch completes synchronously (async generation is CARD-004k)
        job = batch_generator_service.get_batch_status(batch_id)
        assert job.status == BatchStatus.COMPLETE

        # Verify the batch exists and can be retrieved
        assert job.batch_id == batch_id

    @pytest.mark.unit
    def test_batch_list_sorted_by_date_newest_first(self, batch_generator_service):
        """Test that batch list is sorted by date (newest first)."""
        batch_id1 = batch_generator_service.create_batch(count=10, sizes=[15])

        # Create second batch slightly later
        import time
        time.sleep(0.01)
        batch_id2 = batch_generator_service.create_batch(count=10, sizes=[15])

        batches = sorted(
            batch_generator_service.jobs.values(),
            key=lambda b: b.created_at,
            reverse=True
        )

        # Newest should be first
        if len(batches) >= 2:
            assert batches[0].created_at >= batches[1].created_at


class TestBatchDetails:
    """Test batch detail retrieval."""

    @pytest.mark.unit
    def test_batch_detail_shows_all_metadata(self, batch_generator_service, puzzle_review_service):
        """Test that batch detail page has all metadata."""
        batch_id = batch_generator_service.create_batch(
            count=10,
            sizes=[10, 15, 20],
            theme='halloween'
        )

        # `create_batch` already generates synchronously, so the explicit
        # call that used to sit here generated the batch a second time —
        # twice the draws, and a store holding twice as many rows as
        # `puzzle_count` claimed. Harmless while nothing compared the two;
        # CARD-083's `puzzle_count == len(stored)` assertion is what
        # surfaced it.

        job = batch_generator_service.get_batch_status(batch_id)

        assert job.batch_id == batch_id
        assert job.count == 10
        assert job.sizes == [10, 15, 20]
        assert job.theme == 'halloween'
        assert job.status == BatchStatus.COMPLETE
        assert job.created_at is not None
        assert job.completed_at is not None
        assert 0 < job.puzzle_count <= 10  # CARD-083: may skip an abandoned candidate

    @pytest.mark.unit
    def test_batch_detail_includes_puzzle_list(self, batch_generator_service):
        """Test that batch detail includes list of puzzles in batch."""
        batch_id = batch_generator_service.create_batch(count=10, sizes=[15])

        # Puzzles are generated synchronously during create_batch
        job = batch_generator_service.get_batch_status(batch_id)
        puzzles = batch_generator_service.get_batch_puzzles(batch_id, limit=100)

        assert len(puzzles) == job.puzzle_count
        assert 0 < len(puzzles) <= 10
        assert all('grid' in p for p in puzzles)
        assert all('difficulty_score' in p for p in puzzles)
        assert all(p.get('batch_id') == batch_id for p in puzzles)


class TestBatchRetry:
    """Test batch retry functionality."""

    @pytest.mark.unit
    def test_retry_batch_uses_same_parameters(self, batch_generator_service):
        """Test that retry batch uses original parameters."""
        batch_id1 = batch_generator_service.create_batch(
            count=10,
            sizes=[15, 20],
            theme='christmas'
        )

        original_job = batch_generator_service.get_batch_status(batch_id1)

        # Simulate retry by creating new batch with same params
        batch_id2 = batch_generator_service.create_batch(
            count=original_job.count,
            sizes=original_job.sizes,
            theme=original_job.theme
        )

        new_job = batch_generator_service.get_batch_status(batch_id2)

        assert new_job.count == original_job.count
        assert new_job.sizes == original_job.sizes
        assert new_job.theme == original_job.theme

    @pytest.mark.unit
    def test_retry_creates_new_batch_id(self, batch_generator_service):
        """Test that retry creates a new batch ID, not reusing old one."""
        batch_id1 = batch_generator_service.create_batch(count=10, sizes=[15])

        # Simulate retry
        batch_id2 = batch_generator_service.create_batch(count=10, sizes=[15])

        assert batch_id1 != batch_id2
        assert batch_generator_service.get_batch_status(batch_id1) is not None
        assert batch_generator_service.get_batch_status(batch_id2) is not None


# Run with: pytest tests/test_batch_history.py -v
# Run just unit tests: pytest tests/test_batch_history.py -m unit -v
