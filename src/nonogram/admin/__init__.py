"""Admin panel services for nonogram platform."""

from .batch_generator import (
    BatchGenerator,
    BatchStatus as BatchStatus,
    BatchJob,
    GeneratedPuzzle,
    PuzzleMetrics,
    get_batch_generator,
)
from .puzzle_review import (
    PuzzleReviewService,
    PuzzleStatus,
    PuzzleFilter,
    PuzzleListResponse,
    get_puzzle_review_service,
)
from .book_manager import (
    BookManager,
    BookStatus,
    BookMetadata,
    Book,
    get_book_manager,
)

try:
    from .app import create_app
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
