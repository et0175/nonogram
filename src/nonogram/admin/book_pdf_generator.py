"""PDF generation service for book scaffolding.

Exports a book as two files (FR-043, INV-013): the interior PDF — guide page,
puzzles, SOLUTIONS divider and answers, with no cover page — and the cover
file, a single front-cover page.
"""

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, List, Tuple
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

from nonogram.difficulty import Tier, tier_of_record
from nonogram.export import ExportPayload
from nonogram.export.pdf import render_pages
from nonogram import clues


def tier_breakdown(puzzles: List[Dict[str, Any]]) -> "Counter[Tier]":
    """Count a book's puzzles by tier, however their rows spell it.

    One implementation for both places a book's difficulty breakdown is built —
    the PDF guide page here and the finalize screen in ``app.py`` — because two
    copies of it is how the defect below survived in both at once.

    Every count goes through :func:`nonogram.difficulty.tier_of_record` rather
    than comparing against a display label. A row written by the generation
    pipeline stores the enum *value* (``"easy"``), so the previous
    ``== "Easy"`` matched none of them: every generated book reported a 0/0/0
    breakdown, which reads as an empty book rather than as a broken reader
    (CARD-076 review F-002). Rows whose tier is missing or unrecognised are
    counted in no tier at all, so the totals never exceed the puzzle count.

    Returns a :class:`collections.Counter`, so every member of :class:`Tier`
    can be indexed without a ``get`` and reads
    0 when the book has none.
    """
    return Counter(
        tier
        for tier in (
            tier_of_record(puzzle.get("difficulty_tier")) for puzzle in puzzles
        )
        if tier is not None
    )


@dataclass(frozen=True)
class BookExport:
    """A book's export: the interior PDF and, beside it, the cover file.

    ``interior_page_count`` is the book's page count (FR-030 as amended by
    FR-043) — the interior's pages only; the cover file is never counted.
    """

    interior: BytesIO
    cover: BytesIO
    interior_page_count: int


def page_is_right_hand(page_number: int) -> bool:
    """Whether interior page ``page_number`` (1-based) is a right-hand page.

    Parity counts from the interior's page 1, the guide page, which is
    right-hand: odd pages are right-hand, even pages left-hand (FR-043).
    """
    if page_number < 1:
        raise ValueError(f"interior pages are numbered from 1, got {page_number}")
    return page_number % 2 == 1


class BookPDFGenerator:
    """Generates a book's interior PDF (guide, puzzles, answers) and cover file."""

    def __init__(self):
        """Initialize PDF generator."""
        self.dpi = 300  # Standard for printing
        self.page_width_px = int(8.5 * self.dpi)  # 8.5 inches (letter)
        self.page_height_px = int(11 * self.dpi)  # 11 inches (letter)

    def create_cover_page(self, book_title: str, cover_image: Optional[Image.Image] = None) -> Image.Image:
        """Create cover page image.

        Args:
            book_title: Title for the book
            cover_image: Optional pre-built cover image

        Returns:
            Cover page as PIL Image
        """
        if cover_image:
            # Use provided cover, resized to standard page size
            return cover_image.resize((self.page_width_px, self.page_height_px), Image.Resampling.LANCZOS)

        # Create blank cover with title
        cover = Image.new("RGB", (self.page_width_px, self.page_height_px), "white")
        draw = ImageDraw.Draw(cover)

        # Try to load a nice font, fall back to default
        try:
            title_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 72)
        except OSError:
            # Fallback font
            title_font = ImageFont.load_default()

        # Draw title centered on page
        title_bbox = draw.textbbox((0, 0), book_title, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (self.page_width_px - title_width) // 2
        title_y = (self.page_height_px - (title_bbox[3] - title_bbox[1])) // 2

        draw.text((title_x, title_y), book_title, fill="black", font=title_font)

        return cover

    def create_guide_page(
        self,
        puzzle_count: int,
        easy_count: int,
        medium_count: int,
        hard_count: int,
    ) -> Image.Image:
        """Create guide page image with difficulty summary.

        Args:
            puzzle_count: Total number of puzzles
            easy_count: Number of easy puzzles
            medium_count: Number of medium puzzles
            hard_count: Number of hard puzzles

        Three counts, one per tier, since CARD-098 retired ADR-0025's fourth.

        Returns:
            Guide page as PIL Image
        """
        guide = Image.new("RGB", (self.page_width_px, self.page_height_px), "white")
        draw = ImageDraw.Draw(guide)

        # Try to load fonts
        try:
            title_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 48)
            text_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 28)
        except OSError:
            title_font = ImageFont.load_default()
            text_font = ImageFont.load_default()

        # Draw title
        title = "How to Use This Book"
        draw.text((100, 100), title, fill="black", font=title_font)

        # Draw guide text
        guide_text = [
            f"This book contains {puzzle_count} puzzles.",
            "",
            "Difficulty Levels:",
            f"  Easy:   {easy_count} puzzles",
            f"  Medium: {medium_count} puzzles",
            f"  Hard:   {hard_count} puzzles",
            "",
            "Instructions:",
            "  1. Fill in the grid based on the clues",
            "  2. Check your work against the answer key",
            "  3. Have fun!",
        ]

        y = 250
        for line in guide_text:
            draw.text((100, y), line, fill="black", font=text_font)
            y += 50

        return guide

    def export_book(
        self,
        puzzles: List[dict],
        book_title: str,
        trim_width_cm: Optional[str] = None,
        trim_height_cm: Optional[str] = None,
        cover_image: Optional[Image.Image] = None,
    ) -> BookExport:
        """Export a book as its two files: the interior PDF and the cover file.

        The one entry point every export route goes through (FR-043, INV-013).
        The interior holds no cover page — its page 1 is the guide page — and
        the cover file is a single page at the book's page size holding the
        uploaded ``cover_image`` when one is given, otherwise the generated
        title cover. Front cover only: the KDP cover wrap (spine, back cover,
        bleed) is deferred.

        Args:
            puzzles: List of puzzle dicts (from puzzle_review service), in
                book order
            book_title: Title for the book (the generated cover's text)
            trim_width_cm: Trim width (informational, for metadata)
            trim_height_cm: Trim height (informational, for metadata)
            cover_image: The uploaded front-cover image, if one is set

        Returns:
            :class:`BookExport` — both files and the interior's page count.
        """
        pages = self.interior_pages(puzzles)
        cover = self.create_cover_page(book_title, cover_image)
        return BookExport(
            interior=self._save_pdf(pages),
            cover=self._save_pdf([cover]),
            interior_page_count=len(pages),
        )

    def generate_book_pdf(
        self,
        puzzles: List[dict],
        book_title: str,
        trim_width_cm: Optional[str] = None,
        trim_height_cm: Optional[str] = None,
    ) -> BytesIO:
        """The book's interior PDF alone — :meth:`export_book`'s ``interior``.

        Kept for callers that want only the interior. It carries no cover
        page, so there is no way left to produce the old single file whose
        page 1 was the cover (FR-043).
        """
        return self.export_book(
            puzzles, book_title, trim_width_cm, trim_height_cm
        ).interior

    def interior_pages(self, puzzles: List[dict]) -> List[Image.Image]:
        """Every page of the interior, in print order; no cover page.

        ``pages[n - 1]`` is interior page ``n``: page 1 is the guide page,
        a right-hand page (:func:`page_is_right_hand`), followed by the
        puzzle pages, the SOLUTIONS divider and the answer pages. The list's
        length is the book's page count (FR-030); the cover is never counted.
        """
        pages: List[Image.Image] = []

        # Calculate difficulty counts for guide
        counts = tier_breakdown(puzzles)

        # Add guide page
        guide = self.create_guide_page(
            len(puzzles),
            counts[Tier.EASY],
            counts[Tier.MEDIUM],
            counts[Tier.HARD],
        )
        pages.append(guide)

        # Add puzzle pages and collect answer pages
        answer_pages = []
        for puzzle in puzzles:
            try:
                # Build ExportPayload for this puzzle
                # Grid is already in the puzzle dict
                grid = puzzle.get("grid", [[]])
                clues_rows = puzzle.get("clues_rows", [])
                clues_cols = puzzle.get("clues_cols", [])

                payload = ExportPayload(
                    grid=grid,
                    row_clues=tuple(tuple(row) for row in clues_rows) if clues_rows else (),
                    column_clues=tuple(tuple(col) for col in clues_cols) if clues_cols else (),
                    seed=0,  # Seed for reproducibility (not available from book puzzles)
                    mode="random",  # Mode (not available from book puzzles)
                    width=puzzle.get("width"),
                    height=puzzle.get("height"),
                    name=puzzle.get("puzzle_name"),
                    difficulty=puzzle.get("difficulty_tier"),  # Display name, not score
                )

                # Render puzzle pages (blank + answer)
                blank_page, answer_page = render_pages(payload)
                pages.append(blank_page)
                answer_pages.append(answer_page)

            except Exception as e:
                # Log and skip this puzzle if it fails to render
                print(f"Failed to render puzzle {puzzle.get('id')}: {str(e)}")
                continue

        # Add a divider page before solutions
        if answer_pages:
            divider = Image.new("RGB", (self.page_width_px, self.page_height_px), "white")
            draw = ImageDraw.Draw(divider)
            try:
                divider_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 60)
            except OSError:
                divider_font = ImageFont.load_default()

            divider_text = "SOLUTIONS"
            bbox = draw.textbbox((0, 0), divider_text, font=divider_font)
            text_width = bbox[2] - bbox[0]
            x = (self.page_width_px - text_width) // 2
            y = (self.page_height_px - (bbox[3] - bbox[1])) // 2
            draw.text((x, y), divider_text, fill="black", font=divider_font)
            pages.append(divider)

            # Add all solution pages
            pages.extend(answer_pages)

        return pages

    def _save_pdf(self, pages: List[Image.Image]) -> BytesIO:
        """Write ``pages`` as one PDF, one image per page, rewound to 0."""
        # PIL's save_all only works with images in same format
        # Convert all to RGB if needed
        rgb_pages = []
        for page in pages:
            if page.mode != "RGB":
                page = page.convert("RGB")
            rgb_pages.append(page)

        # Save to BytesIO
        pdf_bytes = BytesIO()
        if rgb_pages:
            rgb_pages[0].save(
                pdf_bytes,
                format="PDF",
                save_all=True,
                append_images=rgb_pages[1:] if len(rgb_pages) > 1 else [],
                dpi=(self.dpi, self.dpi),
            )
        pdf_bytes.seek(0)

        return pdf_bytes
