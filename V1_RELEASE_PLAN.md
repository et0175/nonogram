# v1 Release Plan
**Target:** This week (2026-09-06 to 2026-09-13)
**Status:** APPROVED
**Stakeholders:** You + 1 other user (testing feedback)
**Philosophy:** Ship MVP + pragmatic polish. Iterate based on real usage.

## v1 Scope (Frozen)

### ✅ Must Have (Core Functionality)
- Random puzzle generation (size 10-30)
- Image upload + dithering
- Difficulty selection (Easy/Medium/Hard)
- Export formats (JSON, PNG, SVG, CSV, PDF)
- Next.js web UI deployed on Railway

### 🔧 Fixes & Improvements (This Week)
- [ ] Fix output directory bug (API doesn't honor output_dir on remote)
- [ ] Improve size suggestions: 10×10, 20×20, 30×30 (not 10, 11, 12)
- [ ] Remove dark mode (light only)
- [ ] Clean up src/nonogram/web/ (remove unused files)

### ❌ Out of Scope (v2 or Later)
- Difficulty analyzer (strategy-based)
- Batch puzzle generation
- Book curation workflow
- Database persistence
- Puzzle storage/library

## v1 Tasks (Priority Order)

### Day 1-2: Bug Fixes
1. Fix output directory bug
2. Clean up src/nonogram/web/ (remove pages.py, server.py)

### Day 3: UX Polish
1. Better size suggestions (10, 20, 30)
2. Remove dark mode

### Day 4: Testing
1. Happy path testing (all formats, both modes)
2. Document test results

### Day 5: Release
1. Update README & create CHANGELOG entry
2. Tag v1.0.0

## v1 Success Criteria
- [ ] Output directory bug fixed
- [ ] Size suggestions improved
- [ ] Dark mode removed
- [ ] src/web cleanup done
- [ ] Happy path tests pass
- [ ] v1.0.0 tagged
- [ ] README updated
- [ ] Other user can generate puzzles

## Estimated Time: 3 hours (1 day of focused work)

## After v1: v2 Research
Once v1 is live:
- Research Amazon KDP format (1-2 hours)
- Document difficulty analysis approach
- Define book curation workflow
- Plan v2 architecture (2026-09-20)
