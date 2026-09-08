# CARD-004n: PDF Generation & Download

**Status**: Pending  
**Priority**: High  
**Wave**: 2  
**Size**: Medium (8 points)

## Description

PDF generation is implemented but may have issues with layout, metadata, and performance on large books. Improve PDF generation to be robust and user-friendly.

## Acceptance Criteria

- [ ] AC-1: PDF downloads with correct filename: "book-title-YYYY-MM-DD.pdf"
- [ ] AC-2: PDF contains all puzzles from book in correct order
- [ ] AC-3: Each puzzle has grid, clues (rows and columns), and difficulty label
- [ ] AC-4: PDF page layout is clean (margins, proper spacing, no overlaps)
- [ ] AC-5: Large books (200 puzzles) generate successfully
- [ ] AC-6: PDF metadata (title, author) set correctly
- [ ] AC-7: Optional: include solution pages (checkbox to toggle)
- [ ] AC-8: If PDF generation fails, error message shown instead of blank download
- [ ] AC-9: PDF generation takes <30 seconds locally, <90 seconds on Render

## Test Requirements

**Unit Tests**:
- PDF layout calculation (pages, breaks)
- Puzzle grid to PDF coordinate conversion
- Metadata generation

**E2E Tests**:
- Create book → generate PDF → file downloads
- Large book (200 puzzles) → PDF generates without timeout
- PDF contains all puzzles

**Playwright Tests**:
- Click "Generate PDF" → download starts
- Verify PDF opens and is readable

## Dependencies

- Book management (CARD-004m)
- ReportLab already in dependencies

## Worktree Notes

- Test PDF with different book sizes
- Implement page breaks for large books
- Add PDF metadata (title, author, creation date)
- Add error handling for PDF generation failures
- Consider lazy generation (async) for very large books
