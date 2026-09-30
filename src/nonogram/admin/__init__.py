"""Admin panel services for nonogram platform."""

from nonogram.admin.batch_generator import (
    BatchGenerator,
    BatchStatus as BatchStatus,
    BatchJob,
    GeneratedPuzzle,
    PuzzleMetrics,
    get_batch_generator,
)
from nonogram.admin.puzzle_review import (
    PuzzleReviewService,
    PuzzleStatus,
    PuzzleFilter,
    PuzzleListResponse,
    get_puzzle_review_service,
)
from nonogram.admin.book_manager import (
    BookManager,
    BookStatus,
    BookMetadata,
    Book,
    get_book_manager,
)

try:
    from nonogram.admin.app import create_app
except ImportError:
    create_app = None

__all__ = [
    # Batch generation
    "BatchGenerator",
    "BatchStatus",
    "BatchJob",
    "GeneratedPuzzle",
    "PuzzleMetrics",
    "get_batch_generator",
    # Puzzle review
    "PuzzleReviewService",
    "PuzzleStatus",
    "PuzzleFilter",
    "PuzzleListResponse",
    "get_puzzle_review_service",
    # Book management
    "BookManager",
    "BookStatus",
    "BookMetadata",
    "Book",
    "get_book_manager",
    # Flask app
    "create_app",
]
