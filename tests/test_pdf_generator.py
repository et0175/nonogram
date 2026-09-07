"""Tests for PDF generation service."""

import pytest
import os
from src.nonogram.admin.pdf_generator import BookPDFGenerator, get_pdf_generator


@pytest.fixture
def pdf_gen():
    """Get a fresh PDF generator for testing."""
    return BookPDFGenerator()


@pytest.fixture
def sample_book_metadata():
    """Sample book metadata for testing."""
    return {
        "title": "Christmas Nonograms 2026",
        "description": "Festive holiday puzzles for the whole family",
        "theme": "christmas",
        "target_audience": "seniors",
        "page_count": 50,
    }


@pytest.fixture
def sample_puzzle():
    """Sample puzzle for testing."""
    return {
        "puzzle_id": "puzzle_000001",
        "grid": [[True, False, True], [False, True, False], [True, True, True]],
        "clues_rows": [[1, 1], [1], [3]],
        "clues_cols": [[2], [2], [2]],
        "width": 3,
        "height": 3,
        "difficulty_tier": "Easy",
        "difficulty_score": 25,
        "quality_score": 85,
        "recognizability": "high",
        "strategies_used": ["line_logic"],
    }


class TestPDFGeneration:
    """Test PDF generation."""

    def test_pdf_generator_creation(self, pdf_gen):
        """Test PDF generator can be created."""
        assert pdf_gen is not None
        assert pdf_gen.PAGE_WIDTH > 0
        assert pdf_gen.PAGE_HEIGHT > 0

    def test_generate_single_puzzle_pdf(self, pdf_gen, sample_book_metadata, sample_puzzle):
        """Generate PDF with single puzzle."""
        puzzles = [sample_puzzle]

        pdf_bytes = pdf_gen.generate_book_pdf(sample_book_metadata, puzzles)

        assert pdf_bytes is not None
        assert len(pdf_bytes) > 0
        assert pdf_bytes.startswith(b"%PDF")  # PDF magic bytes

    def test_generate_multiple_puzzles_pdf(self, pdf_gen, sample_book_metadata, sample_puzzle):
        """Generate PDF with multiple puzzles."""
        puzzles = [sample_puzzle for _ in range(3)]

        pdf_bytes = pdf_gen.generate_book_pdf(sample_book_metadata, puzzles)

        assert pdf_bytes is not None
        assert len(pdf_bytes) > len(pdf_gen.generate_book_pdf(sample_book_metadata, [sample_puzzle]))

    def test_generate_pdf_to_file(self, pdf_gen, sample_book_metadata, sample_puzzle, tmp_path):
        """Generate PDF and save to file."""
        output_path = tmp_path / "test_book.pdf"

        result_path = pdf_gen.generate_book_pdf(
            sample_book_metadata,
            [sample_puzzle],
            output_path=str(output_path)
        )

        assert result_path == str(output_path)
        assert output_path.exists()
        assert output_path.stat().st_size > 0

        # Verify it's a valid PDF
        with open(output_path, "rb") as f:
            content = f.read()
            assert content.startswith(b"%PDF")

    def test_pdf_with_empty_puzzles(self, pdf_gen, sample_book_metadata):
        """Generate PDF with no puzzles."""
        pdf_bytes = pdf_gen.generate_book_pdf(sample_book_metadata, [])

        assert pdf_bytes is not None
        assert len(pdf_bytes) > 0

    def test_pdf_with_different_difficulties(self, pdf_gen, sample_book_metadata):
        """Generate PDF with puzzles of different difficulties."""
        puzzles = [
            {
                **{
                    "grid": [[True, False], [False, True]],
                    "clues_rows": [[1], [1]],
                    "clues_cols": [[1], [1]],
                    "width": 2,
                    "height": 2,
                },
                "difficulty_tier": tier,
                "difficulty_score": score,
                "quality_score": 80,
            }
            for tier, score in [("Easy", 25), ("Medium", 50), ("Hard", 75)]
        ]

        pdf_bytes = pdf_gen.generate_book_pdf(sample_book_metadata, puzzles)

        assert pdf_bytes is not None
        assert len(pdf_bytes) > 0

    def test_pdf_metadata_included(self, pdf_gen, sample_book_metadata, sample_puzzle):
        """Verify PDF is valid and contains expected structure."""
        pdf_bytes = pdf_gen.generate_book_pdf(sample_book_metadata, [sample_puzzle])

        # Verify PDF structure
        assert pdf_bytes.startswith(b"%PDF")
        assert b"endobj" in pdf_bytes
        assert b"%%EOF" in pdf_bytes

        # Verify it has reasonable size (content included)
        assert len(pdf_bytes) > 2000  # Should be at least a few KB

    def test_singleton_generator(self):
        """Test singleton pattern."""
        gen1 = get_pdf_generator()
        gen2 = get_pdf_generator()

        assert gen1 is gen2

    def test_large_grid_handling(self, pdf_gen, sample_book_metadata):
        """Test handling of larger puzzles."""
        large_puzzle = {
            "grid": [[True if (i + j) % 2 == 0 else False for j in range(20)] for i in range(20)],
            "clues_rows": [[10]] * 20,
            "clues_cols": [[10]] * 20,
            "width": 20,
            "height": 20,
            "difficulty_tier": "Hard",
            "difficulty_score": 75,
            "quality_score": 90,
        }

        pdf_bytes = pdf_gen.generate_book_pdf(sample_book_metadata, [large_puzzle])

        assert pdf_bytes is not None
        assert len(pdf_bytes) > 0

    def test_custom_metadata(self, pdf_gen):
        """Test with custom metadata variations."""
        metadata_variants = [
            {"title": "Spring Puzzles", "theme": "easter", "target_audience": "children"},
            {"title": "Halloween Spooky", "theme": "halloween", "target_audience": "adults"},
            {"title": "Love Nonograms", "theme": "valentine", "target_audience": "couples"},
        ]

        sample_puzzle = {
            "grid": [[True, False], [False, True]],
            "clues_rows": [[1], [1]],
            "clues_cols": [[1], [1]],
            "width": 2,
            "height": 2,
            "difficulty_tier": "Easy",
            "difficulty_score": 20,
            "quality_score": 75,
        }

        for metadata in metadata_variants:
            pdf_bytes = pdf_gen.generate_book_pdf(metadata, [sample_puzzle])
            assert pdf_bytes is not None
            assert len(pdf_bytes) > 0
