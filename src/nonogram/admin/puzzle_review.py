"""Puzzle review and filtering service for admin panel.

Handles filtering puzzles by various criteria and managing approval/rejection.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


class PuzzleStatus(Enum):
    """Status of a puzzle in the curation workflow."""

    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"
    IN_BOOK = "in_book"


@dataclass
class PuzzleFilter:
    """Filters for puzzle queries."""

    size: Optional[int] = None  # e.g., 20 (width/height)
    difficulty: Optional[str] = None  # 'Easy', 'Medium', 'Hard'
    quality_min: Optional[int] = None  # 1-100
    theme: Optional[str] = None
    status: Optional[str] = None
    limit: int = 25
    offset: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary for API."""
        return {
            "size": self.size,
            "difficulty": self.difficulty,
            "quality_min": self.quality_min,
            "theme": self.theme,
            "status": self.status,
            "limit": self.limit,
            "offset": self.offset,
        }

    @staticmethod
    def from_dict(data: dict) -> "PuzzleFilter":
        """Create PuzzleFilter from dictionary."""
        return PuzzleFilter(
            size=data.get("size"),
            difficulty=data.get("difficulty"),
            quality_min=data.get("quality_min"),
            theme=data.get("theme"),
            status=data.get("status"),
            limit=data.get("limit", 25),
            offset=data.get("offset", 0),
        )


@dataclass
class PuzzleListResponse:
    """Response for puzzle list queries."""

    puzzles: List[Dict[str, Any]]
    total_count: int
    offset: int
    limit: int
    has_more: bool

    def to_dict(self) -> dict:
        """Convert to dictionary for API."""
        return {
            "puzzles": self.puzzles,
            "total_count": self.total_count,
            "offset": self.offset,
            "limit": self.limit,
            "has_more": self.has_more,
        }


class PuzzleReviewService:
    """Service for reviewing and filtering puzzles.

    In production, this would query a database. For now, uses in-memory storage.
    """

    def __init__(self):
        """Initialize puzzle review service."""
        # In-memory puzzle storage (TODO: move to database)
        self.puzzles: Dict[str, Dict[str, Any]] = {}
        self._next_id = 1

    def add_puzzle(
        self,
        grid: list,
        clues_rows: list,
        clues_cols: list,
        width: int,
        height: int,
        theme: str,
        difficulty_score: int,
        difficulty_tier: str,
        quality_score: int,
        recognizability: str,
        strategies_used: List[str],
    ) -> str:
        """Add a puzzle to the store.

        Args:
            grid: Nonogram grid (List[List[bool]])
            clues_rows: Row clues (List[List[int]])
            clues_cols: Column clues (List[List[int]])
            width: Grid width
            height: Grid height
            theme: Puzzle theme
            difficulty_score: Difficulty score (1-100)
            difficulty_tier: Difficulty tier (Easy/Medium/Hard)
            quality_score: Quality score (1-100)
            recognizability: Recognizability (high/medium/low)
            strategies_used: List of strategy names

        Returns:
            puzzle_id
        """
        puzzle_id = f"puzzle_{self._next_id:06d}"
        self._next_id += 1

        self.puzzles[puzzle_id] = {
            "id": puzzle_id,
            "grid": grid,
            "clues_rows": clues_rows,
            "clues_cols": clues_cols,
            "width": width,
            "height": height,
            "theme": theme,
            "difficulty_score": difficulty_score,
            "difficulty_tier": difficulty_tier,
            "quality_score": quality_score,
            "recognizability": recognizability,
            "strategies_used": strategies_used,
            "status": PuzzleStatus.DRAFT.value,
            "created_at": datetime.utcnow().isoformat(),
        }

        return puzzle_id

    def filter_puzzles(self, filter_opts: PuzzleFilter) -> PuzzleListResponse:
        """Filter puzzles based on criteria.

        Args:
            filter_opts: PuzzleFilter with criteria

        Returns:
            PuzzleListResponse with filtered puzzles
        """
        # Validate filter
        if filter_opts.limit < 1 or filter_opts.limit > 100:
            raise ValueError("Limit must be 1-100")
        if filter_opts.offset < 0:
            raise ValueError("Offset must be >= 0")
        if filter_opts.size and not (10 <= filter_opts.size <= 30):
            raise ValueError("Size must be 10-30")
        if filter_opts.quality_min and not (0 <= filter_opts.quality_min <= 100):
            raise ValueError("Quality min must be 0-100")

        # Filter puzzles
        filtered = []
        for puzzle_id, puzzle in self.puzzles.items():
            # Size filter
            if filter_opts.size and puzzle["width"] != filter_opts.size:
                continue

            # Difficulty filter
            if (
                filter_opts.difficulty
                and puzzle["difficulty_tier"] != filter_opts.difficulty
            ):
                continue

            # Quality filter
            if (
                filter_opts.quality_min
                and puzzle["quality_score"] < filter_opts.quality_min
            ):
                continue

            # Theme filter
            if filter_opts.theme and puzzle["theme"] != filter_opts.theme:
                continue

            # Status filter
            if filter_opts.status and puzzle["status"] != filter_opts.status:
                continue

            filtered.append(puzzle)

        # Sort by quality descending (best first)
        filtered.sort(key=lambda p: p["quality_score"], reverse=True)

        # Paginate
        total = len(filtered)
        start = filter_opts.offset
        end = start + filter_opts.limit
        paginated = filtered[start:end]

        has_more = end < total

        return PuzzleListResponse(
            puzzles=paginated,
            total_count=total,
            offset=filter_opts.offset,
            limit=filter_opts.limit,
            has_more=has_more,
        )

    def get_puzzle(self, puzzle_id: str) -> Optional[Dict[str, Any]]:
        """Get a single puzzle by ID.

        Args:
            puzzle_id: ID of puzzle to retrieve

        Returns:
            Puzzle dict, or None if not found
        """
        return self.puzzles.get(puzzle_id)

    def approve_puzzle(self, puzzle_id: str) -> bool:
        """Mark puzzle as approved for book inclusion.

        Args:
            puzzle_id: ID of puzzle to approve

        Returns:
            True if approved, False if not found
        """
        if puzzle_id not in self.puzzles:
            return False

        self.puzzles[puzzle_id]["status"] = PuzzleStatus.APPROVED.value
        return True

    def reject_puzzle(self, puzzle_id: str) -> bool:
        """Mark puzzle as rejected.

        Args:
            puzzle_id: ID of puzzle to reject

        Returns:
            True if rejected, False if not found
        """
        if puzzle_id not in self.puzzles:
            return False

        self.puzzles[puzzle_id]["status"] = PuzzleStatus.REJECTED.value
        return True

    def mark_in_book(self, puzzle_id: str, book_id: str) -> bool:
        """Mark puzzle as included in a specific book.

        Args:
            puzzle_id: ID of puzzle
            book_id: ID of book

        Returns:
            True if marked, False if not found
        """
        if puzzle_id not in self.puzzles:
            return False

        self.puzzles[puzzle_id]["status"] = PuzzleStatus.IN_BOOK.value
        self.puzzles[puzzle_id]["book_id"] = book_id
        return True

    def get_approved_puzzles(self, book_id: str) -> List[Dict[str, Any]]:
        """Get all puzzles approved for a specific book.

        Args:
            book_id: ID of the book

        Returns:
            List of puzzles in the book
        """
        return [
            p
            for p in self.puzzles.values()
            if p.get("status") == PuzzleStatus.IN_BOOK.value
            and p.get("book_id") == book_id
        ]

    def get_stats(self) -> Dict[str, int]:
        """Get statistics about puzzles in storage.

        Returns:
            Dict with counts by status
        """
        stats = {
            "total": len(self.puzzles),
            "draft": 0,
            "approved": 0,
            "rejected": 0,
            "in_book": 0,
        }

        for puzzle in self.puzzles.values():
            status = puzzle["status"]
            if status in stats:
                stats[status] += 1

        return stats


# Global puzzle review service instance
_puzzle_review_service = PuzzleReviewService()


def get_puzzle_review_service() -> PuzzleReviewService:
    """Get the singleton puzzle review service."""
    return _puzzle_review_service
