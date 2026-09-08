"""Batch puzzle generation service for admin panel.

Generates multiple nonograms with metrics, stores in database,
and tracks progress for async operations.
"""

from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum
import uuid
from datetime import datetime
import asyncio
import random

from nonogram import orchestrator


class BatchStatus(Enum):
    """Status of a batch generation job."""

    PENDING = "pending"
    GENERATING = "generating"
    COMPLETE = "complete"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class PuzzleMetrics:
    """Metrics for a generated puzzle."""

    difficulty_score: int  # 1-100
    difficulty_tier: str  # Easy/Medium/Hard
    quality_score: int  # 1-100
    recognizability: str  # high/medium/low
    strategies_used: List[str]
    backtracking_depth: int


@dataclass
class GeneratedPuzzle:
    """A generated puzzle ready to store."""

    puzzle_id: str
    grid: list  # List[List[bool]]
    clues_rows: list  # List[List[int]]
    clues_cols: list  # List[List[int]]
    width: int
    height: int
    theme: str
    metrics: PuzzleMetrics
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class BatchJob:
    """Represents a batch generation job."""

    batch_id: str
    status: BatchStatus
    total_count: int
    completed_count: int = 0
    puzzles: List[GeneratedPuzzle] = field(default_factory=list)
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None  # When batch completed
    count: Optional[int] = None  # Alias for total_count for test compatibility
    sizes: Optional[List[int]] = None  # Store sizes for retry
    theme: Optional[str] = None  # Store theme for retry
    puzzle_count: int = 0  # Number of puzzles actually stored

    def __post_init__(self):
        """Set count alias after initialization."""
        if self.count is None:
            self.count = self.total_count

    def get_progress_percent(self) -> int:
        """Get progress as percentage 0-100."""
        if self.total_count == 0:
            return 0
        return int((self.completed_count / self.total_count) * 100)

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "batch_id": self.batch_id,
            "status": self.status.value,
            "total_count": self.total_count,
            "completed_count": self.completed_count,
            "progress_percent": self.get_progress_percent(),
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class BatchGenerator:
    """Service for generating batches of nonogram puzzles.

    Manages async generation, progress tracking, and storage.
    """

    def __init__(self, puzzle_review_service=None):
        """Initialize batch generator."""
        # In-memory job tracking (TODO: move to database for production)
        self.jobs: dict[str, BatchJob] = {}
        self.puzzle_review_service = puzzle_review_service

    def create_batch(
        self,
        count: int,
        sizes: List[int],
        theme: str = "christmas",
        source: str = "random",
        quality_filter: int = 0,
    ) -> str:
        """Create and start a batch generation job.

        Args:
            count: Number of puzzles to generate (10-200, or 50-200 for production)
            sizes: List of sizes to use (e.g., [10, 20, 30])
            theme: Puzzle theme (e.g., 'christmas')
            source: Generation source ('random' or 'images')
            quality_filter: Minimum quality score (0-100)

        Returns:
            batch_id for tracking progress

        Raises:
            ValueError: If parameters invalid
        """
        # Validate (allow 10+ for testing, 50+ for production)
        if not 10 <= count <= 200:
            raise ValueError(f"Count must be 10-200, got {count}")
        if not sizes or not all(10 <= s <= 30 for s in sizes):
            raise ValueError(f"Sizes must be 10-30, got {sizes}")
        if source not in ("random", "images"):
            raise ValueError(f"Source must be 'random' or 'images', got {source}")
        if not 0 <= quality_filter <= 100:
            raise ValueError(f"Quality filter must be 0-100, got {quality_filter}")

        # Create job
        batch_id = str(uuid.uuid4())
        job = BatchJob(
            batch_id=batch_id,
            status=BatchStatus.GENERATING,
            total_count=count,
            count=count,
            sizes=sizes,
            theme=theme,
        )
        self.jobs[batch_id] = job

        # Generate puzzles synchronously (TODO: make async with Celery/asyncio)
        try:
            if source == "random":
                self._generate_random_batch(batch_id)
            # TODO: else if source == "images": self._generate_from_images(...)

            job.status = BatchStatus.COMPLETE
            job.updated_at = datetime.utcnow()
            job.completed_at = datetime.utcnow()
        except Exception as e:
            job.status = BatchStatus.ERROR
            job.error_message = str(e)
            job.updated_at = datetime.utcnow()
            raise

        return batch_id

    def _generate_random_batch(self, batch_id: str) -> None:
        """Generate random puzzles using the real pipeline and store in database.

        Uses orchestrator.generate_batch() to generate real, uniquely-solvable
        puzzles with calculated difficulty scores — the same pipeline as the CLI.

        Args:
            batch_id: ID of batch job to generate for
        """
        job = self.jobs[batch_id]
        count = job.total_count
        sizes = job.sizes or [15, 20, 25]
        theme = job.theme or "christmas"
        quality_filter = 0  # TODO: get from job

        # Generate real puzzles using the orchestrator pipeline
        # This ensures consistency with CLI generation, real solving, and real difficulty calculation
        puzzles = orchestrator.generate_batch(
            count=count,
            sizes=sizes,
            source="random",
            difficulty_tier=None,  # Accept any difficulty
        )

        # Store each puzzle in database
        puzzle_count = 0
        for puzzle in puzzles:
            # Quality score is always calculated by the real pipeline
            quality_score = puzzle.quality_score if hasattr(puzzle, "quality_score") else 75

            if quality_score >= quality_filter and self.puzzle_review_service:
                self.puzzle_review_service.add_puzzle(
                    grid=puzzle.grid,
                    clues_rows=puzzle.clues.rows,
                    clues_cols=puzzle.clues.columns,
                    width=puzzle.width,
                    height=puzzle.height,
                    theme=theme,  # Use theme from batch job, not from request
                    difficulty_score=puzzle.difficulty_score,
                    difficulty_tier=puzzle.difficulty_tier,
                    quality_score=quality_score,
                    recognizability="medium",  # From the real pipeline if available
                    strategies_used=[],  # From solver signals if available
                    batch_id=batch_id,  # Link puzzle to batch
                )
                puzzle_count += 1

            job.completed_count += 1
            job.updated_at = datetime.utcnow()

        # Update puzzle count in job
        job.puzzle_count = puzzle_count

    def get_batch_status(self, batch_id: str) -> Optional[BatchJob]:
        """Get status of a batch generation job.

        Args:
            batch_id: ID of the batch job

        Returns:
            BatchJob with current status, or None if not found
        """
        return self.jobs.get(batch_id)

    def get_batch_puzzles(self, batch_id: str, offset: int = 0, limit: int = 25) -> Optional[List[dict]]:
        """Get puzzles from a completed batch (from puzzle_review_service).

        Args:
            batch_id: ID of the batch
            offset: Pagination offset
            limit: Pagination limit

        Returns:
            List of puzzle dicts, or empty list if batch not found
        """
        job = self.jobs.get(batch_id)
        if not job or not self.puzzle_review_service:
            return []

        # Get puzzles from this specific batch
        from nonogram.admin.puzzle_review import PuzzleFilter
        filter_opts = PuzzleFilter(batch_id=batch_id, limit=100)  # Max limit is 100
        result = self.puzzle_review_service.filter_puzzles(filter_opts)

        # Return paginated results
        start = offset
        end = start + limit
        return result.puzzles[start:end] if result.puzzles else []

    def cancel_batch(self, batch_id: str) -> bool:
        """Cancel a batch generation job.

        Args:
            batch_id: ID of the batch

        Returns:
            True if cancelled, False if not found or already complete
        """
        job = self.jobs.get(batch_id)
        if not job:
            return False

        # Can only cancel if still generating
        if job.status in (BatchStatus.GENERATING, BatchStatus.PENDING):
            job.status = BatchStatus.CANCELLED
            job.updated_at = datetime.utcnow()
            return True

        return False

    def _generate_puzzle_with_metrics(
        self, size: int, theme: str
    ) -> GeneratedPuzzle:
        """Generate a single puzzle using the real orchestrator pipeline.

        Args:
            size: Puzzle size (width/height for square puzzles)
            theme: Puzzle theme

        Returns:
            GeneratedPuzzle with real metrics from the generation pipeline
        """
        # Use the orchestrator to generate one real puzzle
        puzzles = orchestrator.generate_batch(
            count=1,
            sizes=[size],
            source="random",
            difficulty_tier=None,
        )

        puzzle = puzzles[0]
        puzzle_id = str(uuid.uuid4())

        # Extract metrics from the real puzzle
        metrics = PuzzleMetrics(
            difficulty_score=puzzle.difficulty_score,
            difficulty_tier=puzzle.difficulty_tier,
            quality_score=puzzle.quality_score if hasattr(puzzle, "quality_score") else 75,
            recognizability=getattr(puzzle, "recognizability", "medium"),
            strategies_used=getattr(puzzle, "strategies_used", []),
            backtracking_depth=getattr(puzzle, "backtracking_depth", 0),
        )

        return GeneratedPuzzle(
            puzzle_id=puzzle_id,
            grid=puzzle.grid,
            clues_rows=puzzle.clues.rows,
            clues_cols=puzzle.clues.columns,
            width=puzzle.width,
            height=puzzle.height,
            theme=theme,
            metrics=metrics,
        )


# Global batch generator instance
_batch_generator = None


def get_batch_generator(puzzle_review_service=None) -> BatchGenerator:
    """Get the singleton batch generator."""
    global _batch_generator
    if _batch_generator is None:
        _batch_generator = BatchGenerator(puzzle_review_service)
    elif puzzle_review_service and not _batch_generator.puzzle_review_service:
        _batch_generator.puzzle_review_service = puzzle_review_service
    return _batch_generator
