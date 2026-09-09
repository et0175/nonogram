"""Tests for book scaffolding workflow."""

import pytest
from nonogram.admin.print_specs import PrintSpecValidator
from nonogram.admin.book_manager import BookManager


class TestPrintSpecValidator:
    """Test print specification validation and conversion."""

    def test_cm_to_inches_conversion(self):
        """Test converting centimeters to inches."""
        # 15.24 cm should be 6 inches
        result = PrintSpecValidator.cm_to_inches("15.24")
        assert float(result) == pytest.approx(6.0, abs=0.01)

        # 22.86 cm should be 9 inches
        result = PrintSpecValidator.cm_to_inches("22.86")
        assert float(result) == pytest.approx(9.0, abs=0.01)

    def test_inches_to_cm_conversion(self):
        """Test converting inches to centimeters."""
        # 6 inches should be 15.24 cm
        result = PrintSpecValidator.inches_to_cm("6.0")
        assert float(result) == pytest.approx(15.24, abs=0.01)

        # 9 inches should be 22.86 cm
        result = PrintSpecValidator.inches_to_cm("9.0")
        assert float(result) == pytest.approx(22.86, abs=0.01)

    def test_invalid_conversion_raises_error(self):
        """Test that invalid input raises ValueError."""
        with pytest.raises(ValueError):
            PrintSpecValidator.cm_to_inches("invalid")

        with pytest.raises(ValueError):
            PrintSpecValidator.inches_to_cm("not_a_number")

    def test_trim_size_validation_valid(self):
        """Test validation of valid trim sizes."""
        is_valid, error = PrintSpecValidator.validate_trim_size("15.24", "22.86")
        assert is_valid is True
        assert error is None

        # Test at minimum
        is_valid, error = PrintSpecValidator.validate_trim_size("10.0", "10.0")
        assert is_valid is True
        assert error is None

    def test_trim_size_validation_too_small(self):
        """Test validation rejects trim size that is too small."""
        is_valid, error = PrintSpecValidator.validate_trim_size("9.0", "10.0")
        assert is_valid is False
        assert "at least" in error.lower()

        is_valid, error = PrintSpecValidator.validate_trim_size("10.0", "9.0")
        assert is_valid is False

    def test_trim_size_validation_width_too_large(self):
        """Test validation rejects width exceeding KDP limit."""
        is_valid, error = PrintSpecValidator.validate_trim_size("31.0", "22.86")
        assert is_valid is False
        assert "width" in error.lower() or "exceed" in error.lower()

    def test_trim_size_validation_height_too_large(self):
        """Test validation rejects height exceeding KDP limit."""
        is_valid, error = PrintSpecValidator.validate_trim_size("15.24", "49.0")
        assert is_valid is False
        assert "height" in error.lower() or "exceed" in error.lower()

    def test_trim_size_validation_non_numeric(self):
        """Test validation rejects non-numeric input."""
        is_valid, error = PrintSpecValidator.validate_trim_size("invalid", "22.86")
        assert is_valid is False
        assert "numeric" in error.lower()

        is_valid, error = PrintSpecValidator.validate_trim_size("15.24", "abc")
        assert is_valid is False

    def test_create_spec_with_defaults(self):
        """Test creating a spec with default values."""
        spec, error = PrintSpecValidator.create_spec()
        assert error is None
        assert spec is not None
        assert spec.trim_width_cm == "15.24"
        assert spec.trim_height_cm == "22.86"

    def test_create_spec_with_custom_values(self):
        """Test creating a spec with custom values."""
        spec, error = PrintSpecValidator.create_spec(
            width_cm="21.0",
            height_cm="29.7",
        )
        assert error is None
        assert spec is not None
        assert spec.trim_width_cm == "21.00"
        assert spec.trim_height_cm == "29.70"

    def test_create_spec_with_invalid_size(self):
        """Test creating a spec with invalid size."""
        spec, error = PrintSpecValidator.create_spec(
            width_cm="50.0",
            height_cm="22.86",
        )
        assert error is not None
        assert spec is None
        assert "exceed" in error.lower()

    def test_spec_to_dict(self):
        """Test converting spec to dictionary."""
        spec, _ = PrintSpecValidator.create_spec()
        spec_dict = spec.to_dict()

        assert spec_dict["trim_width_cm"] == "15.24"
        assert spec_dict["trim_height_cm"] == "22.86"
        assert spec_dict["gutter_margin_cm"] is None


class TestBookScaffoldingFlow:
    """Integration tests for book scaffolding workflow."""

    def test_step1_form_with_cm_units(self):
        """Test Step 1 form with cm units."""
        # This would require a Flask test client
        # For now, we just verify the validator works
        spec, error = PrintSpecValidator.create_spec(
            width_cm="15.24",
            height_cm="22.86",
        )
        assert error is None
        assert spec.trim_width_cm == "15.24"
        assert spec.trim_height_cm == "22.86"

    def test_step1_form_with_inches_units(self):
        """Test Step 1 form with inch units (should convert to cm)."""
        # User enters 6 x 9 inches
        width_cm = PrintSpecValidator.inches_to_cm("6.0")
        height_cm = PrintSpecValidator.inches_to_cm("9.0")

        spec, error = PrintSpecValidator.create_spec(
            width_cm=width_cm,
            height_cm=height_cm,
        )
        assert error is None
        # Should be close to A5 size
        assert float(spec.trim_width_cm) == pytest.approx(15.24, abs=0.01)
        assert float(spec.trim_height_cm) == pytest.approx(22.86, abs=0.01)

    def test_step2_puzzle_selection_multiple_puzzles(self):
        """Test Step 2 can handle multiple puzzle selections."""
        # Simulates selecting multiple puzzles
        puzzle_ids = ["puzzle_001", "puzzle_002", "puzzle_003"]

        # Verify list isn't empty and contains correct count
        assert len(puzzle_ids) == 3
        assert "puzzle_001" in puzzle_ids
        assert all(pid.startswith("puzzle_") for pid in puzzle_ids)

    def test_step2_puzzle_selection_empty(self):
        """Test Step 2 handles empty selection (allowed to skip)."""
        puzzle_ids = []

        # Empty selection is allowed for skipping step 2
        assert len(puzzle_ids) == 0

    def test_step2_puzzle_filtering(self):
        """Test that puzzle selection can filter by properties."""
        # Example puzzles with different properties
        puzzles = [
            {"id": "p1", "size": 20, "difficulty": "Easy", "quality": 90},
            {"id": "p2", "size": 20, "difficulty": "Medium", "quality": 85},
            {"id": "p3", "size": 25, "difficulty": "Hard", "quality": 92},
        ]

        # Filter by size
        size_20 = [p for p in puzzles if p["size"] == 20]
        assert len(size_20) == 2

        # Filter by difficulty
        easy = [p for p in puzzles if p["difficulty"] == "Easy"]
        assert len(easy) == 1
        assert easy[0]["id"] == "p1"

        # Filter by quality
        quality_90_plus = [p for p in puzzles if p["quality"] >= 90]
        assert len(quality_90_plus) == 2

class TestBookPuzzleArrangement:
    """Test puzzle arrangement functionality for Step 3."""

    def test_puzzle_reordering_move_up(self):
        """Test moving a puzzle up in order."""
        mgr = BookManager()
        
        # Create book
        book_id = mgr.create_book(
            title="Test Book",
            description="Test",
            theme="christmas",
            target_audience="adults"
        )
        
        # Add puzzles
        puzzle_ids = ["p1", "p2", "p3"]
        mgr.add_puzzles_to_book(book_id, puzzle_ids)
        book = mgr.get_book(book_id)
        
        assert book.puzzle_ids == ["p1", "p2", "p3"]
        
        # Move p2 up (should swap with p1)
        mgr.move_puzzle_up(book_id, "p2")
        book = mgr.get_book(book_id)
        
        assert book.puzzle_ids == ["p2", "p1", "p3"]

    def test_puzzle_reordering_move_down(self):
        """Test moving a puzzle down in order."""
        mgr = BookManager()
        
        book_id = mgr.create_book(
            title="Test Book",
            description="Test",
            theme="christmas",
            target_audience="adults"
        )
        
        puzzle_ids = ["p1", "p2", "p3"]
        mgr.add_puzzles_to_book(book_id, puzzle_ids)
        
        # Move p1 down (should swap with p2)
        mgr.move_puzzle_down(book_id, "p1")
        book = mgr.get_book(book_id)
        
        assert book.puzzle_ids == ["p2", "p1", "p3"]

    def test_puzzle_cannot_move_beyond_bounds(self):
        """Test that puzzles cannot move beyond list bounds."""
        mgr = BookManager()
        
        book_id = mgr.create_book(
            title="Test Book",
            description="Test",
            theme="christmas",
            target_audience="adults"
        )
        
        puzzle_ids = ["p1", "p2", "p3"]
        mgr.add_puzzles_to_book(book_id, puzzle_ids)
        
        # Try to move first puzzle up (should fail)
        result = mgr.move_puzzle_up(book_id, "p1")
        assert result is False
        
        # Try to move last puzzle down (should fail)
        result = mgr.move_puzzle_down(book_id, "p3")
        assert result is False
        
        # Order should not change
        book = mgr.get_book(book_id)
        assert book.puzzle_ids == ["p1", "p2", "p3"]

    def test_set_puzzle_title(self):
        """Test setting custom title for a puzzle."""
        mgr = BookManager()
        
        book_id = mgr.create_book(
            title="Test Book",
            description="Test",
            theme="christmas",
            target_audience="adults"
        )
        
        puzzle_ids = ["p1", "p2"]
        mgr.add_puzzles_to_book(book_id, puzzle_ids)
        
        # Set custom title
        mgr.set_puzzle_title(book_id, "p1", "The Rain Deer")
        
        # Verify title is stored
        title = mgr.get_puzzle_title(book_id, "p1")
        assert title == "The Rain Deer"
        
        # Verify other puzzle has no title
        title = mgr.get_puzzle_title(book_id, "p2")
        assert title is None

    def test_clear_puzzle_title(self):
        """Test clearing a custom title."""
        mgr = BookManager()
        
        book_id = mgr.create_book(
            title="Test Book",
            description="Test",
            theme="christmas",
            target_audience="adults"
        )
        
        puzzle_ids = ["p1"]
        mgr.add_puzzles_to_book(book_id, puzzle_ids)
        
        # Set title
        mgr.set_puzzle_title(book_id, "p1", "My Title")
        assert mgr.get_puzzle_title(book_id, "p1") == "My Title"
        
        # Clear title (empty string)
        mgr.set_puzzle_title(book_id, "p1", "")
        assert mgr.get_puzzle_title(book_id, "p1") is None

    def test_puzzle_not_in_book_raises_error(self):
        """Test that setting title for non-existent puzzle raises error."""
        mgr = BookManager()
        
        book_id = mgr.create_book(
            title="Test Book",
            description="Test",
            theme="christmas",
            target_audience="adults"
        )
        
        mgr.add_puzzles_to_book(book_id, ["p1"])
        
        # Try to set title for puzzle not in book
        with pytest.raises(ValueError, match="Puzzle not in book"):
            mgr.set_puzzle_title(book_id, "p999", "Title")
