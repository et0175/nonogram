"""Tests for puzzle review and filtering service."""

import pytest
from src.nonogram.admin.puzzle_review import (
    PuzzleReviewService,
    PuzzleStatus,
    PuzzleFilter,
    PuzzleListResponse,
    get_puzzle_review_service,
)


@pytest.fixture
def review_service():
    """Get a fresh puzzle review service for testing."""
    return PuzzleReviewService()


@pytest.fixture
def sample_puzzle_data():
    """Sample puzzle data for testing."""
    return {
        "grid": [[True, False], [False, True]],
        "clues_rows": [[1], [1]],
        "clues_cols": [[1], [1]],
        "width": 2,
        "height": 2,
        "theme": "christmas",
        "difficulty_score": 45,
        "difficulty_tier": "Easy",
        "quality_score": 85,
        "recognizability": "high",
        "strategies_used": ["line_logic"],
    }


class TestPuzzleAddition:
    """Test adding puzzles to the service."""

    def test_add_puzzle(self, review_service, sample_puzzle_data):
        """Add a puzzle to the service."""
        puzzle_id = review_service.add_puzzle(**sample_puzzle_data)

        assert puzzle_id is not None
        assert puzzle_id.startswith("puzzle_")

    def test_add_multiple_puzzles(self, review_service, sample_puzzle_data):
        """Add multiple puzzles with unique IDs."""
        id1 = review_service.add_puzzle(**sample_puzzle_data)
        id2 = review_service.add_puzzle(**sample_puzzle_data)

        assert id1 != id2
        assert len(review_service.puzzles) == 2

    def test_added_puzzle_has_draft_status(self, review_service, sample_puzzle_data):
        """New puzzles start in draft status."""
        puzzle_id = review_service.add_puzzle(**sample_puzzle_data)
        puzzle = review_service.get_puzzle(puzzle_id)

        assert puzzle["status"] == PuzzleStatus.DRAFT.value


class TestPuzzleFiltering:
    """Test puzzle filtering."""

    def test_filter_by_size(self, review_service):
        """Filter puzzles by size."""
        # Add puzzles of different sizes
        review_service.add_puzzle(
            grid=[[True] * 10 for _ in range(10)],
            clues_rows=[[10]],
            clues_cols=[[10]],
            width=10,
            height=10,
            theme="christmas",
            difficulty_score=30,
            difficulty_tier="Easy",
            quality_score=75,
            recognizability="high",
            strategies_used=["line_logic"],
        )
        review_service.add_puzzle(
            grid=[[True] * 20 for _ in range(20)],
            clues_rows=[[20]],
            clues_cols=[[20]],
            width=20,
            height=20,
            theme="christmas",
            difficulty_score=50,
            difficulty_tier="Medium",
            quality_score=80,
            recognizability="high",
            strategies_used=["line_logic"],
        )

        # Filter by size 20x20
        filter_opts = PuzzleFilter(size=(20, 20))
        result = review_service.filter_puzzles(filter_opts)

        assert len(result.puzzles) == 1
        assert result.puzzles[0]["width"] == 20
        assert result.puzzles[0]["height"] == 20

    def test_filter_by_difficulty(self, review_service):
        """Filter puzzles by difficulty tier."""
        review_service.add_puzzle(
            grid=[[True] * 10 for _ in range(10)],
            clues_rows=[[10]],
            clues_cols=[[10]],
            width=10,
            height=10,
            theme="christmas",
            difficulty_score=25,
            difficulty_tier="Easy",
            quality_score=75,
            recognizability="high",
            strategies_used=["line_logic"],
        )
        review_service.add_puzzle(
            grid=[[True] * 20 for _ in range(20)],
            clues_rows=[[20]],
            clues_cols=[[20]],
            width=20,
            height=20,
            theme="christmas",
            difficulty_score=75,
            difficulty_tier="Hard",
            quality_score=80,
            recognizability="high",
            strategies_used=["line_logic", "backtracking"],
        )

        # Filter by Hard difficulty
        filter_opts = PuzzleFilter(difficulty="Hard")
        result = review_service.filter_puzzles(filter_opts)

        assert len(result.puzzles) == 1
        assert result.puzzles[0]["difficulty_tier"] == "Hard"

    def test_filter_by_quality(self, review_service):
        """Filter puzzles by minimum quality score."""
        review_service.add_puzzle(
            grid=[[True] * 10 for _ in range(10)],
            clues_rows=[[10]],
            clues_cols=[[10]],
            width=10,
            height=10,
            theme="christmas",
            difficulty_score=30,
            difficulty_tier="Easy",
            quality_score=65,
            recognizability="medium",
            strategies_used=["line_logic"],
        )
        review_service.add_puzzle(
            grid=[[True] * 10 for _ in range(10)],
            clues_rows=[[10]],
            clues_cols=[[10]],
            width=10,
            height=10,
            theme="christmas",
            difficulty_score=30,
            difficulty_tier="Easy",
            quality_score=90,
            recognizability="high",
            strategies_used=["line_logic"],
        )

        # Filter by quality >= 80
        filter_opts = PuzzleFilter(quality_min=80)
        result = review_service.filter_puzzles(filter_opts)

        assert len(result.puzzles) == 1
        assert result.puzzles[0]["quality_score"] == 90

    def test_filter_pagination(self, review_service):
        """Test pagination in filter results."""
        # Add 30 puzzles
        for i in range(30):
            review_service.add_puzzle(
                grid=[[True] * 10 for _ in range(10)],
                clues_rows=[[10]],
                clues_cols=[[10]],
                width=10,
                height=10,
                theme="christmas",
                difficulty_score=30 + i,
                difficulty_tier="Easy",
                quality_score=70 + i,  # Quality increases
                recognizability="high",
                strategies_used=["line_logic"],
            )

        # First page
        filter1 = PuzzleFilter(limit=10, offset=0)
        result1 = review_service.filter_puzzles(filter1)

        assert len(result1.puzzles) == 10
        assert result1.total_count == 30
        assert result1.has_more is True

        # Second page
        filter2 = PuzzleFilter(limit=10, offset=10)
        result2 = review_service.filter_puzzles(filter2)

        assert len(result2.puzzles) == 10
        assert result2.has_more is True

        # Third page
        filter3 = PuzzleFilter(limit=10, offset=20)
        result3 = review_service.filter_puzzles(filter3)

        assert len(result3.puzzles) == 10
        assert result3.has_more is False

    def test_filter_combined_criteria(self, review_service):
        """Filter with multiple criteria."""
        review_service.add_puzzle(
            grid=[[True] * 20 for _ in range(20)],
            clues_rows=[[20]],
            clues_cols=[[20]],
            width=20,
            height=20,
            theme="christmas",
            difficulty_score=45,
            difficulty_tier="Medium",
            quality_score=85,
            recognizability="high",
            strategies_used=["line_logic"],
        )
        review_service.add_puzzle(
            grid=[[True] * 30 for _ in range(30)],
            clues_rows=[[30]],
            clues_cols=[[30]],
            width=30,
            height=30,
            theme="christmas",
            difficulty_score=65,
            difficulty_tier="Hard",
            quality_score=92,
            recognizability="high",
            strategies_used=["line_logic", "backtracking"],
        )

        # Filter: size 20x20, difficulty Medium, quality >= 80
        filter_opts = PuzzleFilter(size=(20, 20), difficulty="Medium", quality_min=80)
        result = review_service.filter_puzzles(filter_opts)

        assert len(result.puzzles) == 1
        assert result.puzzles[0]["width"] == 20
        assert result.puzzles[0]["height"] == 20

    def test_invalid_filter_parameters(self, review_service):
        """Reject invalid filter parameters."""
        with pytest.raises(ValueError):
            review_service.filter_puzzles(PuzzleFilter(limit=0))

        with pytest.raises(ValueError):
            review_service.filter_puzzles(PuzzleFilter(limit=101))

        with pytest.raises(ValueError):
            review_service.filter_puzzles(PuzzleFilter(offset=-1))

        with pytest.raises(ValueError):
            review_service.filter_puzzles(PuzzleFilter(size=(5, 5)))

        with pytest.raises(ValueError):
            review_service.filter_puzzles(PuzzleFilter(quality_min=101))


class TestPuzzleApproval:
    """Test puzzle approval workflow."""

    def test_approve_puzzle(self, review_service, sample_puzzle_data):
        """Approve a puzzle."""
        puzzle_id = review_service.add_puzzle(**sample_puzzle_data)
        result = review_service.approve_puzzle(puzzle_id)

        assert result is True
        puzzle = review_service.get_puzzle(puzzle_id)
        assert puzzle["status"] == PuzzleStatus.APPROVED.value

    def test_reject_puzzle(self, review_service, sample_puzzle_data):
        """Reject a puzzle."""
        puzzle_id = review_service.add_puzzle(**sample_puzzle_data)
        result = review_service.reject_puzzle(puzzle_id)

        assert result is True
        puzzle = review_service.get_puzzle(puzzle_id)
        assert puzzle["status"] == PuzzleStatus.REJECTED.value

    def test_mark_in_book(self, review_service, sample_puzzle_data):
        """Mark puzzle as included in a book."""
        puzzle_id = review_service.add_puzzle(**sample_puzzle_data)
        result = review_service.mark_in_book(puzzle_id, "book_001")

        assert result is True
        puzzle = review_service.get_puzzle(puzzle_id)
        assert puzzle["status"] == PuzzleStatus.IN_BOOK.value
        assert puzzle["book_id"] == "book_001"

    def test_approve_nonexistent_puzzle(self, review_service):
        """Cannot approve non-existent puzzle."""
        result = review_service.approve_puzzle("nonexistent")

        assert result is False


class TestPuzzleRetrieval:
    """Test retrieving puzzles."""

    def test_get_puzzle(self, review_service, sample_puzzle_data):
        """Get a single puzzle by ID."""
        puzzle_id = review_service.add_puzzle(**sample_puzzle_data)
        puzzle = review_service.get_puzzle(puzzle_id)

        assert puzzle is not None
        assert puzzle["id"] == puzzle_id
        assert puzzle["theme"] == "christmas"

    def test_get_nonexistent_puzzle(self, review_service):
        """Getting non-existent puzzle returns None."""
        puzzle = review_service.get_puzzle("nonexistent")

        assert puzzle is None

    def test_get_approved_puzzles_for_book(self, review_service, sample_puzzle_data):
        """Get all puzzles approved for a specific book."""
        # Add puzzles
        id1 = review_service.add_puzzle(**sample_puzzle_data)
        id2 = review_service.add_puzzle(**sample_puzzle_data)
        id3 = review_service.add_puzzle(**sample_puzzle_data)

        # Mark for book 1
        review_service.mark_in_book(id1, "book_001")
        review_service.mark_in_book(id2, "book_001")

        # Mark for book 2
        review_service.mark_in_book(id3, "book_002")

        # Get puzzles for book 1
        book1_puzzles = review_service.get_approved_puzzles("book_001")

        assert len(book1_puzzles) == 2
        assert all(p["book_id"] == "book_001" for p in book1_puzzles)


class TestStats:
    """Test statistics tracking."""

    def test_get_stats(self, review_service, sample_puzzle_data):
        """Get statistics about puzzles."""
        # Add some puzzles
        id1 = review_service.add_puzzle(**sample_puzzle_data)
        id2 = review_service.add_puzzle(**sample_puzzle_data)
        id3 = review_service.add_puzzle(**sample_puzzle_data)

        # Change status
        review_service.approve_puzzle(id1)
        review_service.reject_puzzle(id2)

        stats = review_service.get_stats()

        assert stats["total"] == 3
        assert stats["draft"] == 1
        assert stats["approved"] == 1
        assert stats["rejected"] == 1


class TestSingleton:
    """Test singleton pattern."""

    def test_get_puzzle_review_service_singleton(self):
        """Service is a singleton."""
        svc1 = get_puzzle_review_service()
        svc2 = get_puzzle_review_service()

        assert svc1 is svc2


class TestPuzzleFilter:
    """Test PuzzleFilter data structure."""

    def test_filter_to_dict(self):
        """Convert filter to dictionary."""
        f = PuzzleFilter(size=(20, 20), difficulty="Hard", quality_min=80)
        d = f.to_dict()

        assert d["size"] == (20, 20)
        assert d["difficulty"] == "Hard"
        assert d["quality_min"] == 80

    def test_filter_from_dict(self):
        """Create filter from dictionary."""
        data = {"size": (20, 20), "difficulty": "Medium", "limit": 50}
        f = PuzzleFilter.from_dict(data)

        assert f.size == (20, 20)
        assert f.difficulty == "Medium"
        assert f.limit == 50


class TestPuzzleListResponse:
    """Test PuzzleListResponse data structure."""

    def test_response_to_dict(self):
        """Convert response to dictionary."""
        response = PuzzleListResponse(
            puzzles=[{"id": "p1"}],
            total_count=100,
            offset=0,
            limit=25,
            has_more=True,
        )
        d = response.to_dict()

        assert d["total_count"] == 100
        assert d["has_more"] is True
        assert len(d["puzzles"]) == 1
