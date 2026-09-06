# Book Format Research & Specification (Amazon KDP)

**Status:** PRE-IMPLEMENTATION RESEARCH  
**Purpose:** Define KDP format requirements before PDF generation  
**Owner:** Ольга  
**Deadline:** 2026-10-15 (before CARD-011: Final PDF)  
**Blocks:** CARD-008 (PDF generator), CARD-011 (final book)

---

## Goal

Reverse-engineer Amazon KDP requirements by analyzing real puzzle books so we can generate PDFs that are:
- ✅ KDP-compliant (specs match)
- ✅ Print-ready (margins, fonts, quality)
- ✅ Sales-ready (look professional, seniors-friendly)

---

## Phase 1: Research (by 2026-09-30)

### 1.1 Download Real Puzzle Books from KDP

**Action:** Find 3-5 puzzle books on Amazon KDP matching our target:
- Christmas/holiday theme (or similar)
- Targeting adults/seniors
- Similar size/puzzle count (50-200 puzzles)

**Collect Data:**
- [ ] Book title, author, ASIN, price, page count
- [ ] Trim size (common: 8.5"×11", 6"×9")
- [ ] Paper orientation (portrait/landscape)
- [ ] Number of puzzles per page (1? 2? 4?)
- [ ] Puzzle sizes (all 20×20? mixed?)
- [ ] Spacing/margins (top, bottom, left, right)
- [ ] Font choice for puzzle labels
- [ ] Solution placement (end of book? back? separate?)
- [ ] Cover design (screenshot if possible)
- [ ] Page numbering style
- [ ] Difficulty labels visible? (Easy, Medium, Hard)

**Deliverable:** `research/kdp-book-samples.md` with analysis table:

| Book Title | Trim Size | Puzzles/Page | Margin Top | Font | Price | Notes |
|-----------|-----------|-------------|-----------|------|-------|-------|
| Example Book 1 | 8.5×11 | 1 | 0.5" | Arial 14pt | $9.99 | Solutions at end |
| Example Book 2 | 6×9 | 2 | 0.25" | Courier 11pt | $5.99 | No solutions |

---

### 1.2 Amazon KDP Official Specifications

**Research from:** https://kdp.amazon.com/help

**Collect:**
- [ ] Trim sizes available
- [ ] Minimum/maximum page count (affects pricing tiers?)
- [ ] PDF requirements (resolution DPI, file size limits)
- [ ] Image requirements (color mode, file format)
- [ ] Font embedding rules
- [ ] Bleed/margin requirements
- [ ] Cover template specs (dimensions, safe zone, spines)
- [ ] ISBN requirements (optional vs. required)
- [ ] Pricing calculator (how does page count affect profit margin?)

**Deliverable:** `research/kdp-official-specs.md` documenting all requirements

---

### 1.3 Page Mockup Design

**Create mockups for:**

1. **Title Page**
   - Book title
   - Author name
   - Decoration (Christmas theme visual)
   - ISBN (if used)

2. **Typical Puzzle Page**
   - 1 or 2 puzzles (TBD from research)
   - Grid size (all 20×20 or mixed?)
   - Puzzle clues (row/column numbers clearly visible)
   - Difficulty label (Easy/Medium/Hard)
   - Page number

3. **Solutions Page(s)**
   - Solutions for puzzles
   - Same layout as puzzle pages but filled in
   - Page numbers

**Deliverable:** `research/page-mockups.md` with ASCII/visual mockups

---

## Phase 2: Specification (by 2026-10-15)

### 2.1 PDF Generation Specification

**Input parameters for CARD-008 (PDF Generator):**

```yaml
BookPDFConfig:
  trim_size: "8.5x11" | "6x9" | custom
  orientation: "portrait" | "landscape"
  puzzles_per_page: 1 | 2
  margins:
    top: 0.5"
    bottom: 0.5"
    left: 0.5"
    right: 0.5"
  fonts:
    title: "Arial 28pt bold"
    body: "Arial 12pt"
    puzzle_clue: "Courier 10pt"
  include_solutions: true | false
  solutions_at_end: true | false
  difficulty_labels: true | false
  page_numbering: true | false
  
  cover:
    image_url: "path/to/cover.jpg"
    title: "Christmas Nonograms"
    author: "Ольга"
    
  puzzles: [
    {id: "...", grid: [...], clues_h: [...], clues_v: [...], difficulty: "Easy", size: "20x20"},
    ...
  ]
```

**Output:** Single PDF file, KDP-ready

### 2.2 Quality Checklist

Before CARD-011 (final PDF), verify:

- [ ] Page count is optimal for KDP pricing tier
- [ ] Margins are correct (no content near edges)
- [ ] Fonts are embedded (not subset)
- [ ] Images (cover, grid lines) are 300 DPI
- [ ] PDF is not compressed (clear text/lines)
- [ ] Color mode is correct (grayscale or RGB as per KDP)
- [ ] Page numbering is consistent
- [ ] Solutions match puzzles (spot-check 5 puzzles)
- [ ] Difficulty distribution is balanced (easy/medium/hard roughly equal)
- [ ] Cover looks professional
- [ ] No stray artifacts (grid glitches, missing clues, etc.)

---

## Phase 3: Implementation Decisions

### 3.1 Trim Size Decision

**Options:**
- 8.5"×11" (US Letter) — larger, easier to read
- 6"×9" (standard trade) — smaller, cheaper to print, more portable
- A4 — European standard

**Recommendation:** 8.5"×11" for seniors (larger puzzles = easier to read)

**Decision:** _______________  (to be decided after research)

---

### 3.2 Puzzles Per Page

**Options:**
- 1 puzzle per page — more spacious, easier for seniors, more pages (higher cost)
- 2 puzzles per page — compact, fewer pages (lower cost)
- Mixed — vary based on puzzle size

**Recommendation:** 1 puzzle per page (seniors target, better usability)

**Decision:** _______________  (to be decided after research)

---

### 3.3 Solutions Inclusion

**Options:**
- Include solutions at end of book — helpful, adds pages/cost
- Separate PDF for solutions — users download separately
- No solutions — users need to figure it out

**Recommendation:** Include solutions at end (helpful for all ages)

**Decision:** _______________  (to be decided after research)

---

## Phase 4: Testing & Validation

### 4.1 Generate Test Book PDF

**By 2026-10-15:**
- [ ] Use CARD-008 (PDF generator) to create sample 10-page book
- [ ] Verify formatting matches spec
- [ ] Print first 3 pages (check quality, readability, margins)
- [ ] Compare to real KDP books (does it look professional?)

### 4.2 KDP Preview

**By 2026-10-20:**
- [ ] Upload test PDF to KDP draft
- [ ] Use KDP's preview tool to check rendering
- [ ] Look for formatting issues (page breaks, text overflow, etc.)
- [ ] Request Anna's feedback: "Does this look good to you?"

---

## Deliverables

By **2026-10-15**, this document should include:

1. ✅ **kdp-book-samples.md** — Analysis of 3-5 real books
2. ✅ **kdp-official-specs.md** — Amazon KDP requirements documented
3. ✅ **page-mockups.md** — Visual mockups of title, puzzle, solutions pages
4. ✅ **Filled-in decisions** above (trim size, puzzles/page, solutions)
5. ✅ **Test book PDF** — Sample generated PDF
6. ✅ **KDP preview feedback** — Anna's approval

---

## Open Questions

- **Glossy vs. matte cover?** (Research what works on KDP)
- **Color or B&W?** (B&W cheaper; puzzles don't need color)
- **Hardcover or softcover?** (KDP offers both; softcover cheaper)
- **Pricing?** (Research similar books; depends on page count + production cost)
- **ISBN?** (KDP can assign free ASIN; optional ISBN from Bowker costs $)

---

**Status:** 🔍 RESEARCH PHASE  
**Owner:** Ольга  
**Next Step:** Start book research by 2026-09-20

