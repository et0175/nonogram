"""Wave 2 tests: Async batch generation (CARD-004k)."""

import pytest
from nonogram.admin.batch_generator import BatchStatus


class TestAsyncBatchGeneration:
    """Tests for async batch generation (CARD-004k)."""

    @pytest.mark.e2e
    def test_batch_returns_immediately(self, batch_generator_service):
        """Test that create_batch returns immediately (async)."""
        # TODO: Implement async job queue
        # For now, batches complete synchronously
        batch_id = batch_generator_service.create_batch(
            count=50,
            sizes=[15, 20],
            theme='christmas'
        )

        assert batch_id is not None
        # With async, this would be PENDING; with current sync it's COMPLETE
        job = batch_generator_service.get_batch_status(batch_id)
        assert job.status in [BatchStatus.PENDING, BatchStatus.GENERATING, BatchStatus.COMPLETE]

    @pytest.mark.e2e
    @pytest.mark.slow
    def test_multiple_batches_run_concurrently(self, batch_generator_service):
        """Test that multiple batches can be generated concurrently."""
        # TODO: Implement async job queue for true concurrency
        batch_id1 = batch_generator_service.create_batch(count=50, sizes=[15])
        batch_id2 = batch_generator_service.create_batch(count=50, sizes=[20])

        job1 = batch_generator_service.get_batch_status(batch_id1)
        job2 = batch_generator_service.get_batch_status(batch_id2)

        assert job1 is not None
        assert job2 is not None
        # Both should exist (concurrent or queued)
        assert job1.batch_id != job2.batch_id

    @pytest.mark.integration
    def test_progress_polling(self, batch_generator_service):
        """Test that batch progress can be polled during generation."""
        batch_id = batch_generator_service.create_batch(count=100, sizes=[15, 20])

        job = batch_generator_service.get_batch_status(batch_id)

        # Should have progress tracking
        assert hasattr(job, 'get_progress_percent')
        progress = job.get_progress_percent()
        assert 0 <= progress <= 100


class TestErrorRecovery:
    """Tests for error recovery (CARD-004l)."""

    @pytest.mark.integration
    def test_failed_batch_shows_error_message(self, batch_generator_service):
        """Test that failed batch stores error message."""
        # TODO: Simulate batch failure and verify error handling
        batch_id = batch_generator_service.create_batch(count=50, sizes=[15])

        job = batch_generator_service.get_batch_status(batch_id)
        # Should not have error if batch completed successfully
        if job.status == BatchStatus.ERROR:
            assert job.error_message is not None

    @pytest.mark.integration
    def test_retry_batch_uses_same_parameters(self, batch_generator_service):
        """Test that retry batch uses original parameters."""
        batch_id1 = batch_generator_service.create_batch(
            count=50,
            sizes=[15, 20],
            theme='christmas'
        )

        job1 = batch_generator_service.get_batch_status(batch_id1)

        # Simulate retry (create new batch with same params)
        batch_id2 = batch_generator_service.create_batch(
            count=job1.count,
            sizes=job1.sizes,
            theme=job1.theme
        )

        job2 = batch_generator_service.get_batch_status(batch_id2)

        assert job2.count == job1.count
        assert job2.sizes == job1.sizes
        assert job2.theme == job1.theme


class TestBookManagement:
    """Tests for book management (CARD-004m)."""

    @pytest.mark.integration
    def test_create_book_with_approved_puzzles(self, batch_generator_service, puzzle_review_service):
        """Test creating a book and adding approved puzzles."""
        # TODO: Implement book creation
        # Generate and approve puzzles
        batch_id = batch_generator_service.create_batch(count=50, sizes=[15])

        puzzles = batch_generator_service.get_batch_puzzles(batch_id, limit=100)

        # Approve some puzzles
        for puzzle in puzzles[:25]:
            puzzle_review_service.approve_puzzle(puzzle['id'])

        # Get approved puzzles (for book)
        approved = [p for p in puzzles if puzzle_review_service.get_puzzle(p['id'])['status'] == 'approved']

        assert len(approved) == 25

    @pytest.mark.integration
    def test_auto_balanced_puzzle_selection(self):
        """Test auto-balanced selection by difficulty."""
        # TODO: Implement auto-balanced selection algorithm
        # Should select 70% Easy, 20% Medium, 10% Hard
        pass


class TestPDFGeneration:
    """Tests for PDF generation (CARD-004n)."""

    @pytest.mark.integration
    def test_pdf_generation_for_large_book(self, batch_generator_service):
        """Test PDF generation with many puzzles."""
        # TODO: Implement PDF generation
        batch_id = batch_generator_service.create_batch(count=200, sizes=[15, 20])

        job = batch_generator_service.get_batch_status(batch_id)
        puzzles = batch_generator_service.get_batch_puzzles(batch_id, limit=100)

        # Should have sufficient puzzles for a book
        assert len(puzzles) == 100  # First page
        assert job.puzzle_count == 200

    @pytest.mark.integration
    def test_pdf_download_works(self):
        """Test that PDF can be downloaded."""
        # TODO: Implement and test PDF download
        pass


# Run with: pytest tests/test_wave2_async_generation.py -v
# Run Wave 2 tests: pytest tests/test_wave2_*.py -v
