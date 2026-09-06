# v1 Release Plan
**Target:** Next week (2026-09-09 to 2026-09-13)  
**Status:** APPROVED  
**Stakeholders:** You + 1 other user (testing feedback)  
**Philosophy:** Ship MVP + pragmatic polish. Iterate based on real usage.

---

## v1 Scope (Frozen)

### ✅ Must Have (Core Functionality)
- [x] Random puzzle generation (size 10-30)
- [x] Image upload + dithering
- [x] Difficulty selection (Easy/Medium/Hard)
- [x] Export formats (JSON, PNG, SVG, CSV, PDF)
- [x] Next.js web UI deployed on Railway
- [x] API bridge (form → Python core)

### 🔧 Fixes & Improvements (This Week)
- [ ] Fix output directory bug (API doesn't honor output_dir on remote)
- [ ] Improve size suggestions: 10×10, 20×20, 30×30 (not 10, 11, 12)
- [ ] Remove dark mode (light only)
- [ ] Clean up src/nonogram/web/ (remove unused files)
- [ ] Test happy path end-to-end

### ❌ Out of Scope (v2 or Later)
- Difficulty analyzer (strategy-based)
- Batch puzzle generation
- Book curation workflow
- Database persistence
- Puzzle storage/library
- Any KDP-specific features

---

## v1 Tasks (Priority Order)

### **Day 1-2: Bug Fixes**

**Task 1.1: Fix Output Directory Bug**
```
Issue: Puzzle files generated but not saved to output_dir on remote
Location: nonogram-web/api/generate.py (line 60 area)
Steps:
1. Read api/generate.py to see how output_dir is handled
2. Check if it's passed to orchestrator.generate()
3. Verify it's passed to orchestrator.export_puzzle()
4. If missing, add output_dir to both calls
5. Test locally: nonogram generate --size 20 --output-dir /tmp/test
6. Deploy to Railway and test
Acceptance: Files appear in specified directory on both local and remote
```

**Task 1.2: Clean Up src/nonogram/web/**
```
What to remove:
- src/nonogram/web/pages.py (not used by API handler)
- src/nonogram/web/server.py (not used; we have custom server.js)
What to keep:
- src/nonogram/web/handler.py (used by api/generate.py)
- src/nonogram/web/submission.py (form parsing)
- src/nonogram/web/multipart.py (file upload parsing)
- src/nonogram/web/__init__.py
Steps:
1. Verify pages.py and server.py are truly unused (grep in api/generate.py)
2. Delete them
3. Update __init__.py if needed
4. Run tests to ensure nothing breaks
Acceptance: App still works, 2 fewer files
```

### **Day 3: UX Polish**

**Task 2.1: Better Size Suggestions**
```
Current: 10, 11, 12 (linear)
Desired: 10, 20, 30 (logarithmic, spans full range)
Location: nonogram-web/app/components/GeneratorForm.tsx
Steps:
1. Find where size input is defined (likely a range or select)
2. Change default value from 20 to 10 (or keep if already set)
3. Add size suggestions as helper text or preset buttons
4. Display: "Suggested: 10×10 (small), 20×20 (medium), 30×30 (large)"
5. Test in browser at localhost:3000
Acceptance: User sees 3 size options and can click them
```

**Task 2.2: Remove Dark Mode**
```
Location: nonogram-web/app/globals.css or tailwind.config.js
Steps:
1. Remove `dark:` utility classes from components
2. Set `color-scheme: light` in CSS
3. Remove dark theme variables (if any)
4. Test in browser (should be light only)
Acceptance: No dark mode toggle, page is light regardless of user preference
```

### **Day 4: Testing**

**Task 3.1: Happy Path Testing**
```
Test Plan:
1. Random mode:
   - Generate 10×10, 20×20, 30×30
   - Download all formats (JSON, PNG, SVG, CSV, PDF)
   - Verify files are valid (open in viewers, parse JSON)
   
2. Image mode:
   - Upload test image (include small, medium, large)
   - Generate puzzles
   - Download all formats
   
3. Error cases:
   - Invalid size (< 10, > 30)
   - Oversized image
   - Corrupted file upload
   
4. Output directory:
   - Test output_dir works on both local and remote
   - Files appear in correct location
   
Documentation:
- Record results in TEST_RESULTS_v1.md
- Screenshot successful downloads
- Note any issues found
Acceptance: All tests pass, document any minor issues found (v2 backlog)
```

### **Day 5: Release**

**Task 4.1: Documentation**
```
Updates:
- Update README.md with v1 status
- Add CHANGELOG.md entry: "v1.0.0: Initial release"
- Document known limitations (if any)
- Add deployment notes

Create:
- TEST_RESULTS_v1.md (test results)
- V2_ROADMAP.md (placeholder for next phase)
```

**Task 4.2: Tag Release**
```
Git steps:
git tag -a v1.0.0 -m "v1.0.0: Initial MVP release - random/image puzzle generation"
git push origin v1.0.0
Verify: GitHub shows release tag
```

---

## v1 Success Criteria

| Criterion | Status | Notes |
|-----------|--------|-------|
| **Output directory bug fixed** | [ ] | Files appear in correct location |
| **Size suggestions improved** | [ ] | UI shows 10, 20, 30 options |
| **Dark mode removed** | [ ] | Light-only UI |
| **src/web cleanup done** | [ ] | Unused files removed |
| **Happy path tests pass** | [ ] | All formats download & validate |
| **v1.0.0 tagged** | [ ] | Release is git-tagged |
| **README updated** | [ ] | v1 status documented |
| **Other user can generate puzzles** | [ ] | Real feedback collected |

---

## v1 Known Limitations (Not Bugs)

Document these as "works as designed" in v1:
- [ ] No puzzle storage (one-off generation only)
- [ ] No batch generation
- [ ] No curation workflow
- [ ] No difficulty analyzer (uses heuristic scoring)
- [ ] No database persistence
- [ ] Output files stored temporarily, not archived

---

## v1 Deployment Checklist

Before releasing to production:
- [ ] Test all changes locally first
- [ ] Run tests: `npm run test:e2e` (nonogram-web/)
- [ ] Build Docker: `docker build -t nonogram:v1 .`
- [ ] Verify Docker runs locally
- [ ] Deploy to Railway (git push origin main)
- [ ] Smoke test on production URL
- [ ] Share URL with other user for testing

---

## Estimated Time

| Task | Time | Notes |
|------|------|-------|
| Fix output directory | 30 min | Likely one-liner |
| Clean up src/web | 15 min | Just deletion |
| Size suggestions | 30 min | UI tweak |
| Remove dark mode | 15 min | CSS changes |
| Happy path testing | 1 hour | Manual testing |
| Documentation | 30 min | README + changelog |
| **Total** | **3 hours** | 1 day of focused work |

---

## What to Do With Feedback

Once your user generates puzzles and provides feedback:

**If "bug found":**
- Document in `V1_ISSUES_FOUND.md`
- Decide: Fix in v1 hotfix or defer to v2?
- Critical (crashes, data loss) → hotfix
- Nice-to-have (UI polish) → v2 backlog

**If "feature request":**
- Add to `V2_ROADMAP.md` under "Inspired by User Feedback"

**If "works great":**
- Document success in `RELEASE_NOTES_v1.md`

---

## After v1: v2 Planning

Once v1 is live (2026-09-13):

**Week of 2026-09-13:**
- [ ] You research Amazon KDP format (1-2 hours)
- [ ] Document findings in: `meta/architecture/inputs/kdp-requirements.md`
- [ ] Create workflow diagram (generate → review → curate → PDF)

**Week of 2026-09-20:**
- [ ] Gather v2 requirements
- [ ] Plan PuzzleLibrary aggregate
- [ ] Create v2 architecture decisions (DEC-027, DEC-028)
- [ ] Finalize v2 roadmap

**Week of 2026-09-27:**
- [ ] Start v2 development (coding begins)

---

## Roll-Call (Team)

- **You:** All v1 tasks
- **Other user:** Testing & feedback
- **Me (Claude):** Supporting documentation, architecture planning

---

**Status:** 🟢 APPROVED  
**Next Step:** Start with Task 1.1 (output directory bug)  
**Timeline:** 2026-09-09 to 2026-09-13  
**Follow-up:** v2 planning begins 2026-09-13
