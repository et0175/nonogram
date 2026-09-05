# v2 Roadmap: Major Features (Strategy-Based Difficulty + Book Generation)
**Version:** 2.0.0 (Post-v1)
**Status:** PLANNING PHASE
**Timeline:** Research (2026-09-06 → 2026-09-20), Implementation (2026-09-20 onward)
**Goal:** Monetization-ready book generation + smart difficulty analysis

## Overview

v2 adds two major capabilities:

1. **Difficulty Engine** - Analyze puzzles by solving strategies (not heuristics)
2. **Book Curation Workflow** - Generate → Review → Curate → Export for Amazon KDP

## Phase 1: Research & Documentation (NOW → 2026-09-20)

### Research Track 1: Difficulty Analysis
**Tasks:**
- [ ] Define core solving strategies (line logic, constraint prop, backtracking, etc.)
- [ ] Gather empirical data: Generate 100+ puzzles, count strategies, measure difficulty
- [ ] Establish thresholds: When is a puzzle "Easy" vs "Hard"?
- [ ] Measure performance impact: How much overhead does strategy counting add?
- [ ] Check image-mode specifics: Do image puzzles have different patterns?

**Deliverable:** Empirical data + strategy taxonomy + thresholds
**Deadline:** 2026-09-13

### Research Track 2: Amazon KDP Format & Workflow
**Tasks:**
- [ ] Study Amazon KDP specifications (page size, margins, PDF format)
- [ ] Download 3-5 sample puzzle books from KDP
- [ ] Reverse-engineer book layout (puzzles per page, spacing, solutions)
- [ ] Define curation workflow (generate → review → approve → curate → export)

**Deliverable:** KDP format spec + workflow diagram + book schema
**Deadline:** 2026-09-20

## Phase 2: Architecture Planning (2026-09-20 → 2026-09-27)

**Architecture Decisions Needed:**
- How to extract strategy count from solver?
- Where do generated puzzles live (file-based vs database)?
- Is Book a domain aggregate or rendering utility?
- How to represent books for KDP export?

**New Capabilities:**
- CAP-006: Puzzle Analysis (strategy count, difficulty score)
- CAP-007: Puzzle Review & Curation (approval workflow)
- CAP-008: Book Assembly & Export (PDF generation)

## Phase 3: Implementation (2026-09-27 onward)

**Sprint 1:** Difficulty engine core
**Sprint 2:** Difficulty engine E2E testing
**Sprint 3:** Book storage & metadata
**Sprint 4:** Curation workflow UI
**Sprint 5:** PDF generation & KDP export

## Timeline at a Glance

```
2026-09-06   v1 testing begins + v2 research starts (NOW)
2026-09-13   v1.0.0 released | difficulty research due
2026-09-20   v2 architecture finalized
2026-09-27   v2 implementation begins
2026-10-11   v2.0.0 released (target)
```

## Success Criteria

### Difficulty Engine
- [ ] Strategy count accurately predicts difficulty
- [ ] Can distinguish Easy/Medium/Hard
- [ ] Overhead < 20%

### Book Curation
- [ ] Generate 50+ puzzles, review, curate into book
- [ ] Book PDF valid for Amazon KDP
- [ ] User controls difficulty/size/quality distribution

### Monetization
- [ ] First book published on KDP
- [ ] End-to-end workflow works independently

## Next Step
Start research tracks this week. Reconvene 2026-09-20 for v2 architecture planning.
