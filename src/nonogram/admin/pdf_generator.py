"""PDF generation service for nonogram books.

Generates publication-ready PDFs from puzzle data and book metadata.
"""

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.pdfgen import canvas
from io import BytesIO
from datetime import datetime
import os


class BookPDFGenerator:
    """Generate PDF books from puzzles and metadata."""

    # Page setup
    PAGE_WIDTH = letter[0]  # 8.5 inches
    PAGE_HEIGHT = letter[1]  # 11 inches
    MARGIN = 0.5 * inch
    CONTENT_WIDTH = PAGE_WIDTH - (2 * MARGIN)
    CONTENT_HEIGHT = PAGE_HEIGHT - (2 * MARGIN)

    # Colors
    COLOR_PRIMARY = HexColor("#2c3e50")
    COLOR_ACCENT = HexColor("#e74c3c")
    COLOR_TEXT = HexColor("#333333")
    COLOR_LIGHT = HexColor("#ecf0f1")

    def __init__(self):
        """Initialize PDF generator."""
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Setup custom paragraph styles."""
        self.styles.add(ParagraphStyle(
            name="BookTitle",
            parent=self.styles["Heading1"],
            fontSize=28,
            textColor=self.COLOR_PRIMARY,
            spaceAfter=12,
            alignment=1,  # Center
            fontName="Helvetica-Bold"
        ))

        self.styles.add(ParagraphStyle(
            name="BookSubtitle",
            parent=self.styles["Normal"],
            fontSize=14,
            textColor=self.COLOR_ACCENT,
            spaceAfter=6,
            alignment=1,  # Center
            fontName="Helvetica"
        ))

        self.styles.add(ParagraphStyle(
            name="BookBody",
            parent=self.styles["Normal"],
            fontSize=10,
            textColor=self.COLOR_TEXT,
            spaceAfter=6,
            leading=12
        ))

        self.styles.add(ParagraphStyle(
            name="BookLabel",
            parent=self.styles["Normal"],
            fontSize=8,
            textColor=self.COLOR_TEXT,
            spaceAfter=3,
            fontName="Helvetica-Bold"
        ))

    def generate_book_pdf(self, book_metadata, puzzles, output_path=None):
        """Generate a complete book PDF.

        Args:
            book_metadata: Dict with title, description, theme, target_audience
            puzzles: List of puzzle dicts with grid, clues, difficulty, quality
            output_path: Optional path to save PDF. If None, returns BytesIO

        Returns:
            PDF bytes if output_path is None, else writes to file and returns path
        """
        if output_path:
            pdf_buffer = open(output_path, "wb")
        else:
            pdf_buffer = BytesIO()

        doc = SimpleDocTemplate(
            pdf_buffer,
            pagesize=letter,
            rightMargin=self.MARGIN,
            leftMargin=self.MARGIN,
            topMargin=self.MARGIN,
            bottomMargin=self.MARGIN,
            title=book_metadata.get("title", "Nonogram Book")
        )

        # Build story (content)
        story = []

        # Add title page
        story.extend(self._create_title_page(book_metadata))

        # Add table of contents page
        story.append(PageBreak())
        story.extend(self._create_table_of_contents(book_metadata, puzzles))

        # Add puzzle pages
        story.append(PageBreak())
        for i, puzzle in enumerate(puzzles, 1):
            story.extend(self._create_puzzle_page(i, len(puzzles), puzzle))
            if i < len(puzzles):
                story.append(PageBreak())

        # Add back matter
        story.append(PageBreak())
        story.extend(self._create_back_matter(book_metadata))

        # Build PDF
        doc.build(story)

        if output_path:
            pdf_buffer.close()
            return output_path
        else:
            pdf_buffer.seek(0)
            return pdf_buffer.getvalue()

    def _create_title_page(self, metadata):
        """Create title page content."""
        story = []

        # Spacing
        story.append(Spacer(self.CONTENT_WIDTH, 1.5 * inch))

        # Title
        title = Paragraph(metadata.get("title", "Nonogram Puzzle Book"), self.styles["BookTitle"])
        story.append(title)

        # Theme badge
        theme = metadata.get("theme", "generic").upper()
        story.append(Paragraph(f"<b>{theme} EDITION</b>", self.styles["BookSubtitle"]))

        story.append(Spacer(self.CONTENT_WIDTH, 0.3 * inch))

        # Description
        desc = Paragraph(metadata.get("description", ""), self.styles["BookBody"])
        story.append(desc)

        story.append(Spacer(self.CONTENT_WIDTH, 0.5 * inch))

        # Metadata
        meta_text = f"""
        <font size=9>
        <b>Target Audience:</b> {metadata.get('target_audience', 'General')}<br/>
        <b>Puzzle Count:</b> {metadata.get('page_count', '0')} puzzles<br/>
        <b>Generated:</b> {datetime.now().strftime('%B %d, %Y')}<br/>
        </font>
        """
        story.append(Paragraph(meta_text, self.styles["BookBody"]))

        return story

    def _create_table_of_contents(self, metadata, puzzles):
        """Create table of contents."""
        story = []

        story.append(Paragraph("Table of Contents", self.styles["Heading1"]))
        story.append(Spacer(self.CONTENT_WIDTH, 0.2 * inch))

        # TOC entries
        toc_text = "<br/>".join([
            f"<b>Puzzle {i}:</b> Difficulty: {puzzle.get('difficulty_tier', 'N/A')} | "
            f"Size: {puzzle.get('width', 0)}×{puzzle.get('height', 0)} | "
            f"Quality: {puzzle.get('quality_score', 0)}/100"
            for i, puzzle in enumerate(puzzles, 1)
        ])

        story.append(Paragraph(toc_text, self.styles["BookBody"]))

        return story

    def _create_puzzle_page(self, puzzle_num, total, puzzle):
        """Create a single puzzle page."""
        story = []

        # Puzzle header
        header = f"Puzzle {puzzle_num} of {total}"
        story.append(Paragraph(header, self.styles["Heading2"]))

        # Puzzle metadata
        meta = f"""
        <font size=8>
        Difficulty: <b>{puzzle.get('difficulty_tier', 'N/A')}</b> |
        Size: <b>{puzzle.get('width', 0)}×{puzzle.get('height', 0)}</b> |
        Quality: <b>{puzzle.get('quality_score', 0)}/100</b>
        </font>
        """
        story.append(Paragraph(meta, self.styles["BookBody"]))
        story.append(Spacer(self.CONTENT_WIDTH, 0.15 * inch))

        # Grid visualization
        grid = puzzle.get("grid", [[]])
        grid_table = self._create_grid_table(grid)
        story.append(grid_table)

        story.append(Spacer(self.CONTENT_WIDTH, 0.2 * inch))

        # Clues
        story.append(Paragraph("Clues", self.styles["Heading3"]))

        clues_row = f"""
        <font size=8>
        <b>Row Clues:</b> {', '.join(str(c) for c in puzzle.get('clues_rows', []))}<br/>
        <b>Column Clues:</b> {', '.join(str(c) for c in puzzle.get('clues_cols', []))}
        </font>
        """
        story.append(Paragraph(clues_row, self.styles["BookBody"]))

        # Solution notice
        story.append(Spacer(self.CONTENT_WIDTH, 0.1 * inch))
        story.append(Paragraph(
            "<i>Solution available in answer key (back of book)</i>",
            self.styles["BookBody"]
        ))

        return story

    def _create_grid_table(self, grid):
        """Create a puzzle grid table for display."""
        if not grid or len(grid) == 0:
            return Paragraph("(No grid available)", self.styles["BookBody"])

        # Create table data - empty cells for display
        # In production, could render actual puzzle images
        size = len(grid)
        cell_size = min(3, 5 / size)  # Responsive cell sizing

        # Build table with border styling
        data = [["" for _ in range(size)] for _ in range(size)]

        table = Table(data, colWidths=[cell_size * 0.9] * size, rowHeights=[cell_size * 0.9] * size)

        table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cccccc")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("BACKGROUND", (0, 0), (-1, -1), HexColor("#f9f9f9")),
        ]))

        return table

    def _create_back_matter(self, metadata):
        """Create back matter (about, solutions, etc.)."""
        story = []

        story.append(Paragraph("About This Book", self.styles["Heading1"]))
        story.append(Spacer(self.CONTENT_WIDTH, 0.1 * inch))

        about_text = f"""
        <font size=9>
        This {metadata.get('theme', 'nonogram').capitalize()} puzzle book contains carefully curated nonogram
        puzzles designed for {metadata.get('target_audience', 'puzzle enthusiasts')}.
        Each puzzle is rated by difficulty and quality to provide a progressive solving experience.
        <br/><br/>
        <b>Difficulty Levels:</b><br/>
        • <b>Easy:</b> Uses basic line logic and constraint propagation<br/>
        • <b>Medium:</b> Requires more complex deduction techniques<br/>
        • <b>Hard:</b> Challenges experienced solvers with backtracking and ambiguity<br/>
        <br/>
        <b>How to Solve:</b><br/>
        Use the row and column clues to determine which cells should be filled.
        A clue like "3 2" means there are groups of 3 and 2 consecutive filled cells,
        with at least one empty cell between them.
        <br/><br/>
        <b>Generated:</b> {datetime.now().strftime('%B %d, %Y')}<br/>
        <b>Total Puzzles:</b> {metadata.get('page_count', 0)}<br/>
        </font>
        """
        story.append(Paragraph(about_text, self.styles["BookBody"]))

        return story


# Singleton instance
_pdf_generator = BookPDFGenerator()


def get_pdf_generator():
    """Get the singleton PDF generator."""
    return _pdf_generator
