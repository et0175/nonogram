"""Wave 1 comprehensive E2E tests: batch history, preview, bulk operations.

Batch sizes are the minimum ``create_batch`` accepts (10), deliberately.

These tests are about history, preview and bulk operations; generation is a
dependency they lean on, not their subject. But every puzzle in a batch is a
real unseeded draw through the whole pipeline, and a random 20x20 at density 50
genuinely fails to be uniquely solvable within POL-001's 20 regenerate attempts
about **1 time in 300** (measured over 300 draws per size: 0/300 at 15x15,
1/300 at 20x20). ``orchestrator.generate_batch`` has no per-candidate
tolerance — one ``GenerationAbandoned`` ends the whole batch — so the counts
this file asks for are also its exposure to that.

At the 350 draws this file used to make, the chance of at least one spurious
failure per suite run was around 40%, which is what had been showing up as "a
flaky e2e test" that moved between tests run to run. At 60 draws it is nearer
10%. Not zero: the remaining exposure is a real product behaviour, not a test
defect, and whether a batch should skip an abandoned candidate and continue is
an owner decision recorded on CARD-082 rather than something these tests should
paper over.

No assertion changed: each still checks ``puzzle_count == count``, which is the
claim, at a count that costs 5x fewer dice rolls to make.
"""

import pytest
from nonogram.admin.puzzle_review import PuzzleFilter


class TestBatchHistoryE2E:
    """E2E tests for batch history feature (CARD-004h)."""

    @pytest.mark.e2e
    def test_generate_batch_appears_in_history(self, batch_generator_service, puzzle_review_service):
        """Test that generated batch appears in history."""
        # Generate batch
        batch_id = batch_generator_service.create_batch(
            count=10,
            sizes=[15, 20],
            theme='christmas'
        )

        # `create_batch` already generates synchronously, so the explicit
        # call that used to sit here generated the batch a second time —
        # twice the draws, and a store holding twice as many rows as
        # `puzzle_count` claimed. Harmless while nothing compared the two;
        # CARD-083's `puzzle_count == len(stored)` assertion is what
        # surfaced it.

        # Verify batch in history
        job = batch_generator_service.get_batch_status(batch_id)
        assert job is not None
        assert job.status.name == 'COMPLETE'
        assert job.puzzle_count == 10

    @pytest.mark.e2e
    def test_batch_history_shows_multiple_batches(self, batch_generator_service, puzzle_review_service):
        """Test that multiple batches appear in history."""
        # Generate two batches
        batch_id1 = batch_generator_service.create_batch(count=10, sizes=[15])
        batch_id2 = batch_generator_service.create_batch(count=10, sizes=[20])

        # `create_batch` already generates synchronously, so the explicit
        # call that used to sit here generated the batch a second time —
        # twice the draws, and a store holding twice as many rows as
        # `puzzle_count` claimed. Harmless while nothing compared the two;
        # CARD-083's `puzzle_count == len(stored)` assertion is what
        # surfaced it.

        # Verify both in history
        batches = [
            b for b in batch_generator_service.jobs.values()
            if b.batch_id in [batch_id1, batch_id2]
        ]

        assert len(batches) == 2
        assert any(b.batch_id == batch_id1 for b in batches)
        assert any(b.batch_id == batch_id2 for b in batches)

    @pytest.mark.e2e
    def test_batch_history_filters_by_status(self, batch_generator_service, puzzle_review_service):
        """Test filtering batch history by status."""
        # Create batches - both complete synchronously
        batch_id1 = batch_generator_service.create_batch(count=10, sizes=[15])
        batch_id2 = batch_generator_service.create_batch(count=10, sizes=[20])

        # Filter for complete (both should be complete now)
        from nonogram.admin.batch_generator import BatchStatus
        complete_batches = [
            b for b in batch_generator_service.jobs.values()
            if b.status == BatchStatus.COMPLETE
        ]

        assert len(complete_batches) >= 2
        assert any(b.batch_id == batch_id1 for b in complete_batches)
        assert any(b.batch_id == batch_id2 for b in complete_batches)


class TestPuzzlePreviewE2E:
    """E2E tests for puzzle preview modal (CARD-004i)."""

    @pytest.mark.e2e
    def test_preview_puzzle_before_approval(self, puzzle_review_service, sample_puzzle):
        """Test previewing puzzle before making approval decision."""
        if not sample_puzzle:
            pytest.skip("No sample puzzle")

        # Add puzzle
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

        # Get preview data
        puzzle = puzzle_review_service.get_puzzle(puzzle_id)

        # Verify preview has grid and clues
        assert 'grid' in puzzle
        assert 'clues_rows' in puzzle
        assert 'clues_cols' in puzzle
        assert 'difficulty_score' in puzzle

    @pytest.mark.e2e
    def test_approve_from_preview_modal(self, puzzle_review_service, sample_puzzle):
        """Test approving puzzle from preview modal."""
        if not sample_puzzle:
            pytest.skip("No sample puzzle")

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

        # Get preview, then approve from modal
        puzzle = puzzle_review_service.get_puzzle(puzzle_id)
        assert puzzle['status'] == 'draft'

        # Approve
        puzzle_review_service.approve_puzzle(puzzle_id)

        # Verify approved
        puzzle = puzzle_review_service.get_puzzle(puzzle_id)
        assert puzzle['status'] == 'approved'

    @pytest.mark.e2e
    def test_reject_from_preview_modal(self, puzzle_review_service, sample_puzzle):
        """Test rejecting puzzle from preview modal."""
        if not sample_puzzle:
            pytest.skip("No sample puzzle")

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

        # Get preview, then reject from modal
        puzzle = puzzle_review_service.get_puzzle(puzzle_id)
        assert puzzle['status'] == 'draft'

        # Reject
        puzzle_review_service.reject_puzzle(puzzle_id)

        # Verify rejected
        puzzle = puzzle_review_service.get_puzzle(puzzle_id)
        assert puzzle['status'] == 'rejected'

    @pytest.mark.e2e
    def test_preview_all_puzzle_sizes(self, generator):
        """Test preview works for all puzzle sizes (10x10 to 30x30)."""
        sizes = [10, 15, 20, 25, 30]

        for size in sizes:
            puzzles = generator.generate_batch(count=1, sizes=[size])
            if not puzzles:
                pytest.skip(f"Could not generate {size}x{size} puzzle")

            puzzle = puzzles[0]
            assert len(puzzle['grid']) == size
            assert all(len(row) == size for row in puzzle['grid'])


class TestBulkOperationsE2E:
    """E2E tests for bulk operations (CARD-004j)."""

    @pytest.mark.e2e
    def test_bulk_approve_multiple_puzzles(self, puzzle_review_service, sample_puzzles):
        """Test bulk approving multiple puzzles."""
        if not sample_puzzles or len(sample_puzzles) < 5:
            pytest.skip("Need at least 5 puzzles")

        # Add 5 puzzles
        puzzle_ids = []
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
            puzzle_ids.append(puzzle_id)

        # Bulk approve all
        for puzzle_id in puzzle_ids:
            puzzle_review_service.approve_puzzle(puzzle_id)

        # Verify all approved
        for puzzle_id in puzzle_ids:
            puzzle = puzzle_review_service.get_puzzle(puzzle_id)
            assert puzzle['status'] == 'approved'

    @pytest.mark.e2e
    def test_bulk_reject_multiple_puzzles(self, puzzle_review_service, sample_puzzles):
        """Test bulk rejecting multiple puzzles."""
        if not sample_puzzles or len(sample_puzzles) < 5:
            pytest.skip("Need at least 5 puzzles")

        # Add 5 puzzles
        puzzle_ids = []
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
            puzzle_ids.append(puzzle_id)

        # Bulk reject all
        for puzzle_id in puzzle_ids:
            puzzle_review_service.reject_puzzle(puzzle_id)

        # Verify all rejected
        for puzzle_id in puzzle_ids:
            puzzle = puzzle_review_service.get_puzzle(puzzle_id)
            assert puzzle['status'] == 'rejected'

    @pytest.mark.e2e
    def test_bulk_operations_with_filter(self, puzzle_review_service, sample_puzzles):
        """Test bulk operations on filtered puzzles."""
        if not sample_puzzles or len(sample_puzzles) < 10:
            pytest.skip("Need at least 10 puzzles")

        # Add 10 puzzles
        for puzzle in sample_puzzles[:10]:
            puzzle_review_service.add_puzzle(
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

        # Filter by size. A (width, height) pair, not a bare 15: extent has
        # crossed this boundary as a pair since CARD-027 (ADR-0022/R1), and
        # this was the last scalar call left in the repository — it raised
        # `TypeError: cannot unpack non-iterable int object` inside
        # `filter_puzzles` on every run, which is why this test had been
        # failing rather than flaking (CARD-082).
        filter_opts = PuzzleFilter(size=(15, 15), limit=100)
        result = puzzle_review_service.filter_puzzles(filter_opts)

        # The filter has to match something, or the two loops below iterate
        # over nothing and assert nothing. sample_puzzles draws from
        # [10, 15, 20], so some 15x15 rows exist by construction.
        assert result.puzzles, "the size filter matched nothing; the test is vacuous"
        assert all(p['width'] == 15 and p['height'] == 15 for p in result.puzzles)

        # Bulk approve all matching
        for puzzle in result.puzzles:
            puzzle_review_service.approve_puzzle(puzzle['id'])

        # Verify all matching puzzles are approved
        for puzzle in result.puzzles:
            verified = puzzle_review_service.get_puzzle(puzzle['id'])
            assert verified['status'] == 'approved'

    @pytest.mark.e2e
    def test_bulk_approve_updates_statistics(self, puzzle_review_service, sample_puzzles):
        """Test that bulk operations update statistics."""
        if not sample_puzzles or len(sample_puzzles) < 5:
            pytest.skip("Need at least 5 puzzles")

        initial_stats = puzzle_review_service.get_stats()
        initial_approved = initial_stats.get('approved', 0)

        # Add and approve 5 puzzles
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
            puzzle_review_service.approve_puzzle(puzzle_id)

        final_stats = puzzle_review_service.get_stats()
        final_approved = final_stats.get('approved', 0)

        assert final_approved >= initial_approved + 5


class TestCompleteWorkflowWave1:
    """Test complete workflow combining all Wave 1 features."""

    @pytest.mark.e2e
    @pytest.mark.slow
    def test_complete_wave1_workflow(self, batch_generator_service, puzzle_review_service):
        """Test complete workflow: generate → preview → bulk approve."""
        # 1. Generate batch
        batch_id = batch_generator_service.create_batch(
            count=10,
            sizes=[15, 20],
            theme='christmas'
        )

        # 2. Verify batch in history (generation happens during create_batch)
        job = batch_generator_service.get_batch_status(batch_id)
        assert job.puzzle_count == 10

        # 3. Get puzzles from batch
        puzzles = batch_generator_service.get_batch_puzzles(batch_id, limit=100)
        assert len(puzzles) == 10

        # 4. Preview first puzzle (verify grid and clues available)
        first_puzzle = puzzles[0]
        assert 'grid' in first_puzzle
        assert 'clues_rows' in first_puzzle
        assert 'difficulty_score' in first_puzzle
        assert first_puzzle['batch_id'] == batch_id

        # 5. Bulk approve all puzzles (simulation)
        puzzle_ids = [p['id'] for p in puzzles]
        for puzzle_id in puzzle_ids:
            puzzle_review_service.approve_puzzle(puzzle_id)

        # 6. Verify all approved
        final_stats = puzzle_review_service.get_stats()
        assert final_stats['approved'] >= 10


# Run with: pytest tests/test_wave1_e2e.py -v
# Run just E2E tests: pytest tests/test_wave1_e2e.py -m e2e -v
# Run slow tests: pytest tests/test_wave1_e2e.py -m slow -v
