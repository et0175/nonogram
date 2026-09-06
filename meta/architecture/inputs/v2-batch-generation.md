# v2: Batch Puzzle Generation (Book Curation Workflow)
**Status:** PRE-ARCHITECTURE RESEARCH  
**Purpose:** Define book format and curation workflow before architecture  
**Context:** Amazon KDP monetization goal  
**Timeline:** KDP research by 2026-09-13, workflow definition by 2026-09-20

---

## Goal

Create a **book curation workflow** that allows you to:
1. Generate many puzzles (random + images)
2. Review each puzzle (quality, difficulty, image quality)
3. Select/reject puzzles based on criteria
4. Curate into a "Book" (collection of puzzles)
5. Export to PDF for Amazon KDP

**Why this matters:** Not all generated puzzles are suitable for a book. Image puzzles especially need review.

---

## Phase 1: KDP Format Research (by 2026-09-13)

### **What to Research**

**Amazon KDP Specifications:**
- [ ] Puzzle book trim size (common: 8.5"×11", 6"×9", other?)
- [ ] Paper orientation (portrait vs. landscape)
- [ ] Margin requirements (top, bottom, left, right)
- [ ] Page count implications (min/max, pricing tiers)
- [ ] PDF specifications (resolution, fonts, colors)
- [ ] Cover design requirements
- [ ] ISBN/metadata (does KDP handle this?)

**Puzzle Layout on Page:**
- [ ] Puzzles per page (for 20×20, 30×30, etc.)
- [ ] Spacing/padding around puzzles
- [ ] Solution placement (included? back of book? separate PDF?)
- [ ] Difficulty labels (Easy/Medium/Hard visible?)

**Sample Books:**
- [ ] Download 3-5 puzzle books from KDP
- [ ] Measure: page size, puzzle density, layout
- [ ] Screenshot typical page (for reference)

**Deliverable:**
- Document in: `meta/architecture/inputs/kdp-format.md`
- Include: page mockups, specifications, sample analysis

---

## Phase 2: Curation Workflow Definition (by 2026-09-20)

### **What You'll Define**

**Book Metadata:**
- [ ] Title, author, description
- [ ] Target difficulty level (all Easy? Mix?)
- [ ] Target size distribution (all 20×20? Mix?)
- [ ] Puzzle count (50, 100, 200?)
- [ ] Pricing (what works on KDP?)

**Puzzle Selection Criteria:**
- [ ] Quality score: What makes a puzzle "good quality"?
- [ ] Difficulty: Should all puzzles in a book be same difficulty?
- [ ] Size: Should all puzzles be same size or mixed?
- [ ] Image quality: Does the image look good when dithered?
- [ ] Variety: How many from random vs. image mode?

**Curation Workflow:**
```
User generates puzzles (batch mode)
     ↓
System stores each puzzle with:
  - quality_score (auto-calculated)
  - difficulty_score (Easy/Medium/Hard)
  - image_quality (if image mode)
  - user_rating (optional: 1-5 stars)
     ↓
User browses puzzles:
  - See thumbnail preview
  - Read difficulty/quality metadata
  - Filter by: difficulty, size, quality threshold
     ↓
User curates collection:
  - "Approve" this puzzle for book
  - "Reject" this puzzle
  - "Maybe" (undecided)
     ↓
User finalizes book:
  - Confirm 50 puzzles for "Easy" book
  - Arrange in order (or auto-arrange)
  - Generate PDF
     ↓
Export to KDP
```

**Key Decision:** How many puzzles in a book?
- 50 puzzles? (typical workbook size)
- 100 puzzles?
- Depends on: trim size, puzzle size, KDP page count pricing

---

## Phase 3: Architecture Questions (Answer by 2026-09-20)

Once you understand the workflow, answer:

### **Persistence (Storage)**
- [ ] Where do generated puzzles live?
  - Option A: Local files (user manages in folder)
  - Option B: Database (server stores puzzles)
  - Option C: Hybrid (files + metadata in DB)
- [ ] Who owns the data? (user? app?)
- [ ] How long are puzzles kept? (permanent or ephemeral?)

### **Book Representation**
- [ ] Is Book an aggregate (domain model) or utility (render operation)?
- [ ] Does Book need version control? (draft → finalized)
- [ ] Can user save multiple books?

### **File Format**
- [ ] How to represent a Book? (JSON manifest? PDF directly?)
- [ ] Can user export to KDP in one click?

### **Generation Mode**
- [ ] Batch generation speed: OK to generate 50 at once (might take minutes)?
- [ ] Or generate 1-at-a-time + user manually approves each?
- [ ] Progress feedback needed? (show "generating puzzle 23/50")

---

## Open Questions

### **Monetization**
- [ ] Price point on KDP? ($5.99? $9.99?)
- [ ] Profit margin? (KDP takes % cut, paper cost?)
- [ ] Is monetization even viable? (Research actual KDP earnings)

### **Content Strategy**
- [ ] How many books to publish? (1? 10? 100?)
- [ ] How often? (weekly? monthly?)
- [ ] Genre specialization? (kids puzzles? adult? mixed?)

### **User Experience**
- [ ] Will users curate themselves, or use auto-curation?
- [ ] Can app suggest "this puzzle is high quality, include it"?
- [ ] What makes a puzzle "good" for KDP readers? (Need user research)

---

## Deliverables (by 2026-09-20)

**1. KDP Format Document** (`kdp-format.md`)
- Page sizes, margins, puzzle density
- Sample analysis from 3-5 real books

**2. Curation Workflow Diagram**
- Flowchart: generate → review → approve → curate → PDF

**3. Book Metadata Schema**
```yaml
Book:
  title: string
  author: string
  description: string
  difficulty: Easy | Medium | Hard | Mixed
  size_distribution: "all 20x20" | "mixed 10-30"
  puzzles: [Puzzle reference list]
  created_at: datetime
  status: draft | ready_for_kdp | published
```

**4. Architecture Questions Answered**
- Persistence approach chosen
- Book representation decided
- Generation workflow defined

---

## Not for v1

These are **v2 only:**
- No batch generation in v1
- No curation workflow in v1
- No book export in v1
- v1 is one-off generation only

---

**Next Action:** Research KDP this week. Document findings by 2026-09-13. Define workflow by 2026-09-20.
