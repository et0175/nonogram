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

    Supports both in-memory storage (legacy, for backward compatibility) and
    database-backed storage (when session_factory is provided).
    """

    def __init__(self, puzzle_review_service=None, session_factory=None):
        """Initialize batch generator.

        Args:
            puzzle_review_service: PuzzleReviewService instance for storing puzzles
            session_factory: Optional callable that yields a DB session.
                           If None, uses in-memory dict storage (legacy mode).
                           If provided, uses database backend.
        """
        self._session_factory = session_factory
        # In-memory job tracking (used only in legacy mode when session_factory is None)
        self.jobs: dict[str, BatchJob] = {}
        self.puzzle_review_service = puzzle_review_service

    def _update_batch_status(self, batch_id: str, status: Optional[BatchStatus] = None, **fields) -> None:
        """Update batch status in legacy or DB mode.

        Args:
            batch_id: ID of the batch
            status: New BatchStatus, or None to keep current
            **fields: Additional fields to update (completed_count, error_message, etc.)
        """
        if self._session_factory is None:
            # Legacy mode: update in-memory job
            job = self.jobs.get(batch_id)
            if job:
                if status:
                    job.status = status
                for key, value in fields.items():
                    if hasattr(job, key):
                        setattr(job, key, value)
                job.updated_at = datetime.utcnow()
        else:
            # DB mode: update Batch row
            from nonogram.db.models import Batch

            with self._session_factory() as db:
                batch = db.query(Batch).filter(Batch.id == batch_id).first()
                if batch:
                    if status:
                        batch.status = status.value if isinstance(status, BatchStatus) else status
                    for key, value in fields.items():
                        if key == "completed_count":
                            batch.completed_count = value
                        elif key == "error_message":
                            batch.error_message = value
                        elif key == "puzzle_count":
                            batch.puzzle_count = value
                        elif key == "completed_at":
                            batch.completed_at = value
                    batch.updated_at = datetime.utcnow()

    def create_batch(
        self,
        count: int,
        sizes: List[int],
        theme: str = "christmas",
        source: str = "random",
        quality_filter: int = 0,
    ) -> str:
        """Create and start a batch generation job (legacy in-memory or DB-backed).

        Args:
            count: Number of puzzles to generate (1-200 for images, 10-200 for random)
            sizes: List of sizes to use (e.g., [10, 20, 30])
            theme: Puzzle theme (e.g., 'christmas')
            source: Generation source ('random' or 'images')
            quality_filter: Minimum quality score (0-100)

        Returns:
            batch_id for tracking progress

        Raises:
            ValueError: If parameters invalid
        """
        # Validate count based on source
        # Images: allow 1-200 (count = number of images)
        # Random: require 10-200 (count = number to generate)
        if source == "images":
            if not 1 <= count <= 200:
                raise ValueError(f"Image batch count must be 1-200, got {count}")
        else:
            if not 10 <= count <= 200:
                raise ValueError(f"Random batch count must be 10-200, got {count}")
        if not sizes or not all(10 <= s <= 30 for s in sizes):
            raise ValueError(f"Sizes must be 10-30, got {sizes}")
        if source not in ("random", "images"):
            raise ValueError(f"Source must be 'random' or 'images', got {source}")
        if not 0 <= quality_filter <= 100:
            raise ValueError(f"Quality filter must be 0-100, got {quality_filter}")

        batch_id = str(uuid.uuid4())

        if self._session_factory is None:
            # Legacy mode: in-memory BatchJob
            job = BatchJob(
                batch_id=batch_id,
                status=BatchStatus.GENERATING,
                total_count=count,
                count=count,
                sizes=sizes,
                theme=theme,
            )
            self.jobs[batch_id] = job

            # Generate puzzles synchronously
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
        else:
            # DB mode: create Batch row with status=generating
            from nonogram.db.models import Batch

            try:
                # 1. Insert Batch row with status=generating before generation starts
                with self._session_factory() as db:
                    batch = Batch(
                        id=batch_id,
                        status=BatchStatus.GENERATING.value,
                        source=source,
                        total_count=count,
                        completed_count=0,
                        puzzle_count=0,
                        sizes=sizes,
                        theme=theme,
                        quality_filter=quality_filter,
                    )
                    db.add(batch)
                    db.flush()

                # 2. Generate puzzles (each one commits individually)
                if source == "random":
                    self._generate_random_batch(batch_id)
                # TODO: else if source == "images": self._generate_from_images(...)

                # 3. Mark batch complete
                self._update_batch_status(
                    batch_id,
                    BatchStatus.COMPLETE,
                    completed_at=datetime.utcnow(),
                )
            except Exception as e:
                self._update_batch_status(
                    batch_id,
                    BatchStatus.ERROR,
                    error_message=str(e),
                )
                raise

        return batch_id

    def _generate_random_batch(self, batch_id: str) -> None:
        """Generate random puzzles using the real pipeline and store.

        Uses orchestrator.generate_batch() to generate real, uniquely-solvable
        puzzles with calculated difficulty scores — the same pipeline as the CLI.

        Works in both legacy and DB-backed modes.

        Args:
            batch_id: ID of batch job to generate for
        """
        if self._session_factory is None:
            # Legacy mode: read from in-memory job
            job = self.jobs[batch_id]
            count = job.total_count
            sizes = job.sizes or [15, 20, 25]
            theme = job.theme or "christmas"
            quality_filter = 0  # TODO: get from job
        else:
            # DB mode: fetch from database
            from nonogram.db.models import Batch

            with self._session_factory() as db:
                batch = db.query(Batch).filter(Batch.id == batch_id).first()
                if not batch:
                    raise ValueError(f"Batch {batch_id} not found")
                count = batch.total_count
                sizes = batch.sizes or [15, 20, 25]
                theme = batch.theme or "christmas"
                quality_filter = batch.quality_filter or 0

        # Generate real puzzles using the orchestrator pipeline
        puzzles = orchestrator.generate_batch(
            count=count,
            sizes=sizes,
            source="random",
            difficulty_tier=None,  # Accept any difficulty
        )

        # Store each puzzle
        puzzle_count = 0
        for i, puzzle in enumerate(puzzles):
            # Quality score is always calculated by the real pipeline
            quality_score = puzzle.quality_score if hasattr(puzzle, "quality_score") else 75

            if quality_score >= quality_filter and self.puzzle_review_service:
                self.puzzle_review_service.add_puzzle(
                    grid=puzzle.grid,
                    clues_rows=puzzle.clues.rows,
                    clues_cols=puzzle.clues.columns,
                    width=puzzle.width,
                    height=puzzle.height,
                    theme=theme,
                    difficulty_score=puzzle.difficulty_score,
                    difficulty_tier=puzzle.difficulty_tier,
                    quality_score=quality_score,
                    recognizability="medium",
                    strategies_used=[],
                    batch_id=batch_id,
                )
                puzzle_count += 1

            # Update progress
            if self._session_factory is None:
                # Legacy mode
                job = self.jobs[batch_id]
                job.completed_count += 1
                job.updated_at = datetime.utcnow()
            else:
                # DB mode: update completed_count after each puzzle
                self._update_batch_status(batch_id, completed_count=i + 1)

        # Final update with puzzle count
        if self._session_factory is None:
            job = self.jobs[batch_id]
            job.puzzle_count = puzzle_count
        else:
            self._update_batch_status(batch_id, puzzle_count=puzzle_count)

    def get_batch_status(self, batch_id: str) -> Optional[BatchJob]:
        """Get status of a batch generation job (legacy or DB-backed).

        Args:
            batch_id: ID of the batch job

        Returns:
            BatchJob with current status, or None if not found
        """
        if self._session_factory is None:
            # Legacy mode: check in-memory jobs
            return self.jobs.get(batch_id)
        else:
            # DB mode: query database
            from nonogram.db.models import Batch

            with self._session_factory() as db:
                batch = db.query(Batch).filter(Batch.id == batch_id).first()
                if not batch:
                    return None

                # Convert Batch row to BatchJob for backward compatibility
                return BatchJob(
                    batch_id=str(batch.id),
                    status=BatchStatus(batch.status),
                    total_count=batch.total_count,
                    completed_count=batch.completed_count,
                    puzzle_count=batch.puzzle_count,
                    error_message=batch.error_message,
                    created_at=batch.created_at,
                    updated_at=batch.updated_at,
                    completed_at=batch.completed_at,
                    sizes=batch.sizes,
                    theme=batch.theme,
                )

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
