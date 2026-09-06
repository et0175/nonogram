# v2 Roadmap: Major Features (Strategy-Based Difficulty + Book Generation)
**Version:** 2.0.0 (Post-v1)  
**Status:** PLANNING PHASE  
**Timeline:** Research (2026-09-06 → 2026-09-20), Implementation (2026-09-20 onward)  
**Goal:** Monetization-ready book generation + smart difficulty analysis

---

## Overview

v2 adds two major capabilities to transform v1's one-off puzzle generator into a **book publishing platform**:

1. **Difficulty Engine** - Analyze puzzles by solving strategies (not heuristics)
2. **Book Curation Workflow** - Generate → Review → Curate → Export for KDP

---

## Phase 1: Research & Documentation (2026-09-06 → 2026-09-20)

### **Research Track 1: Difficulty Analysis**
**Owner:** You  
**Deliverable:** `meta/architecture/inputs/v2-difficulty-engine.md`

**Tasks:**
- [ ] Define core solving strategies (line logic, constraint prop, backtracking, etc.)
- [ ] Gather empirical data: Generate 100+ puzzles, count strategies, measure difficulty
- [ ] Establish thresholds: When is a puzzle "Easy" vs "Hard"?
- [ ] Measure performance impact: How much overhead does strategy counting add?
- [ ] Check image-mode specifics: Do image puzzles have different strategy patterns?

**Deadline:** 2026-09-13

**Output:**
- Empirical data (spreadsheet with strategy counts)
- Strategy taxonomy (5-10 core strategies defined)
- Difficulty thresholds (Easy: count < X, Medium: X-Y, Hard: > Y)
- Performance baseline (overhead < 20%)

---

### **Research Track 2: KDP Format & Workflow**
**Owner:** You  
**Deliverable:** `meta/architecture/inputs/kdp-format.md` + `v2-batch-generation.md`

**Tasks (KDP Research):**
- [ ] Study Amazon KDP specifications (page size, margins, PDF format)
- [ ] Download 3-5 sample puzzle books from KDP
- [ ] Reverse-engineer book layout (puzzles per page, spacing, solutions)
- [ ] Document page mockup (what does a typical puzzle page look like?)

**Tasks (Workflow Definition):**
- [ ] Define book metadata (title, difficulty, puzzle count, etc.)
- [ ] Define puzzle selection criteria (quality, difficulty, size, image quality)
- [ ] Document curation workflow (generate → review → approve → curate → export)
- [ ] Answer architecture questions (persistence model, book representation, etc.)

**Deadline:** 2026-09-20

**Output:**
- KDP format specification
- Book curation workflow diagram
- Book metadata schema
- Architecture decisions (what to build first)

---

## Phase 2: Architecture Planning (2026-09-20 → 2026-09-27)

### **Design Decisions Needed**

Before any coding, document:

**DEC-029: Strategy Counting in Solver**
```
Question: How to extract strategy count from solver?
Options:
  A: Instrument solver to count strategies during solve
  B: Replay solve with separate strategy analyzer
  C: Extract from solver's internal state
Decision: (Your choice, informed by difficulty research)
```

**DEC-030: Persistence Model**
```
Question: Where do generated puzzles live during curation?
Options:
  A: Local filesystem (user manages files)
  B: Database (server stores, metadata tracked)
  C: Hybrid (files on disk, JSON manifest)
Decision: (Your choice, informed by workflow research)
Rationale: Affects v2 architecture significantly
```

**DEC-031: Book Representation**
```
Question: Is Book a domain aggregate or rendering utility?
Options:
  A: Book is first-class aggregate (domain model, version control, storage)
  B: Book is rendering helper ("render this list of puzzles as PDF")
Decision: (Your choice, informed by workflow research)
```

### **New Requirements (FR-029 → FR-032)**

From difficulty analysis:
- FR-029: "Analyze puzzle strategies to determine difficulty" (CAP-006)
- FR-030: "Score puzzle quality based on solver characteristics" (CAP-006)

From batch workflow:
- FR-031: "Store generated puzzles for later review" (CAP-007)
- FR-032: "Curate puzzles into a book" (CAP-007)
- FR-033: "Generate PDF for Amazon KDP export" (CAP-008)

---

## Phase 3: Implementation (2026-09-27 onward)

### **Track 1: Difficulty Engine**

**Sprint 1 (Week 1):**
- [ ] Create `src/nonogram/analysis/` module
- [ ] Implement strategy counter in solver
- [ ] Unit tests for strategy counting

**Sprint 2 (Week 2):**
- [ ] Integrate strategy analyzer into orchestrator
- [ ] Replace (or complement) heuristic with strategy score
- [ ] E2E tests: verify Easy/Medium/Hard classification

**Deliverable:** CAP-006 (Puzzle Analysis) working

---

### **Track 2: Book Curation**

**Sprint 1 (Week 1):**
- [ ] Design PuzzleLibrary aggregate (if needed)
- [ ] Implement puzzle storage (file-based or DB, per DEC-030)
- [ ] Build puzzle metadata schema

**Sprint 2 (Week 2):**
- [ ] Implement curation workflow (approve/reject UI)
- [ ] Add filtering (by difficulty, size, quality)

**Sprint 3 (Week 3):**
- [ ] PDF generation for KDP
- [ ] Export/download book as PDF

**Deliverable:** CAP-007 + CAP-008 working

---

### **Track 3: UI/UX for v2**

**New Pages/Components:**
- [ ] Puzzle Library view (browse generated puzzles)
- [ ] Puzzle Review page (quality/difficulty assessment)
- [ ] Book Editor (curate puzzles into collection)
- [ ] PDF Preview (before export)

---

## High-Level Architecture (Tentative)

```
New Aggregates:
├── PuzzleLibrary (generated puzzles pending review)
│   ├── Puzzle
│   │   ├── grid
│   │   ├── strategy_count
│   │   ├── difficulty (Easy/Medium/Hard)
│   │   ├── quality_score
│   │   ├── status (pending | approved | rejected)
│   │   └── notes (user review comments)
│
└── Book (curated collection for KDP)
    ├── title, author, description
    ├── PuzzleReference[] (selected puzzles)
    ├── metadata
    └── status (draft | ready_for_kdp | published)

New Capabilities:
├── CAP-006: Puzzle Analysis (strategy count, difficulty, quality score)
├── CAP-007: Puzzle Review & Curation (approval workflow, filtering)
└── CAP-008: Book Assembly & Export (PDF generation for KDP)

New External Systems:
├── Amazon KDP (export PDF, publish books)
└── (Optional) File storage (for puzzle files)
```

---

## Success Criteria for v2

### **Difficulty Engine**
- [ ] Strategy count accurately predicts perceived difficulty
- [ ] Can distinguish Easy/Medium/Hard puzzles
- [ ] Overhead < 20% (generation speed acceptable)

### **Book Curation**
- [ ] Can generate 50+ puzzles, review, and curate into a book
- [ ] Book PDF valid for Amazon KDP upload
- [ ] User can control difficulty/size/quality distribution

### **Monetization**
- [ ] First book published on KDP
- [ ] End-to-end workflow works (generate → curate → export → publish)
- [ ] User can do this independently (minimal manual steps)

---

## Post-v2 Future Ideas

These are **v3+** (not v2):
- Difficulty analyzer with machine learning
- Multi-language puzzles
- User community (sharing books)
- Advanced curation (AI suggestions)
- Performance optimization (faster generation)

---

## Timeline at a Glance

```
2026-09-06   v1 testing begins
2026-09-13   v1.0.0 released | v2 research due
2026-09-20   v2 architecture finalized
2026-09-27   v2 implementation begins
2026-10-11   v2.0.0 released (target, subject to change)
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Amazon KDP requirements unclear | Research early (2026-09-13); verify with real books |
| Strategy counting too slow | Measure overhead; optimize if needed before v2 launch |
| Book curation too complex for users | Start simple (basic approve/reject); iterate based on feedback |
| Monetization doesn't work | Publish test book, gather real KDP data before investing heavily |

---

## Open Questions

- **Automation:** Should app auto-rate puzzles, or is manual review mandatory?
- **Volume:** How many books to publish? What's the revenue model?
- **Discovery:** Will KDP readers find puzzle books in a crowded market?
- **Differentiation:** What makes your books special? (Strategy analysis? Image sourcing?)

---

**Next Step:** Start research tracks (difficulty engine, KDP format) this week. Reconvene 2026-09-20 for architecture planning.
