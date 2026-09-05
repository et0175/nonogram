# Codebase Exploration Report
**Date:** 2026-09-05  
**Status:** Production Deployment with Next.js Integration

---

## Executive Summary

You've built a sophisticated **dual-stack system** combining:
1. **Python Core** (CLI + web adapter) - Layered pipeline for nonogram generation
2. **Next.js Frontend** - React UI deployed on Railway with Python backend
3. **E2E Tests** - Playwright-based browser automation tests
4. **Architecture Model** - Forge-based formal documentation

The system is **production-ready** and deployed on Railway.app with container orchestration.

---

## Current Architecture Overview

### 🐍 Python Core (src/nonogram/)
**Layered Pipeline Architecture** - One-way dependency flow, single bounded context

```
src/nonogram/
├── cli.py              # COMP-001: CLI adapter (argparse, no validation)
├── orchestrator.py     # COMP-002: Puzzle aggregate owner, workflow driver
├── sourcing/           # COMP-003: Grid sourcing (random, library, image)
├── clues.py            # COMP-004: Run-length encoding grid → clues
├── solver/             # COMP-005: Constraint propagation + backtracking
├── difficulty.py       # COMP-006: Heuristic difficulty scoring
├── export/             # COMP-007: PNG/SVG/JSON/CSV/PDF export
├── web/                # COMP-008: Web UI adapter (HTTP handler, form parsing)
├── errors.py           # Shared exception hierarchy (flat, import-free)
└── __main__.py         # Entry point
```

**Key Design Principle:** 
- Capabilities import only stdlib + Pillow + NumPy + errors
- No lateral imports between capabilities
- CLI and orchestrator only point inward
- Structural guards in tests prevent regressions

### 🎨 Next.js Frontend (nonogram-web/)
**React 18 + TypeScript** - Client-side form, server-side Python integration

```
nonogram-web/
├── app/                # Next.js App Router (v15)
│   ├── page.tsx        # Main generator form
│   ├── layout.tsx      # Root layout
│   └── components/     # React components (GeneratorForm, ResultDisplay)
├── api/                # API routes
│   └── generate.py     # Serverless API handler → Python orchestrator
├── e2e/                # Playwright E2E tests
├── public/             # Static assets
├── server.js           # Custom Node.js server (0.0.0.0 binding, port 8080)
├── next.config.js      # Next.js configuration
├── package.json        # Node dependencies
└── playwright.config.ts # E2E test configuration
```

**Technology Stack:**
- Runtime: Node.js 20 + Python 3.11
- Frontend: Next.js 15, React 18, TypeScript, Tailwind CSS
- Backend: Python 3.11, Pillow, NumPy, ReportLab
- Testing: Playwright E2E tests
- Deployment: Docker, Railway.app

### 📋 Bounded Context
**CTX-001: Puzzle Creation** - Single context, one aggregate (Puzzle)
- All 5 capabilities (CAP-001..005) act on one aggregate
- Cross-cutting invariants (uniqueness, clue consistency, difficulty tier)
- One ubiquitous language across sourcing → export

### 🔌 Capabilities Mapped

| ID | Capability | Component | Description |
|----|------------|-----------|-------------|
| CAP-001 | Puzzle sourcing | COMP-003 | Random/library/image grid acquisition |
| CAP-002 | Clue derivation | COMP-004 | Grid → row/column clues (RLE) |
| CAP-003 | Uniqueness verification | COMP-005 | Solver + auto-recovery (retry/nudge) |
| CAP-004 | Difficulty calibration | COMP-006 | Easy/Medium/Hard scoring + resampling |
| CAP-005 | Puzzle export | COMP-007 | PNG/SVG/JSON/CSV/PDF output |

---

## Recent Work (2026-08-27 → 2026-09-05)

### ✅ Completed

**Documentation Restructure**
- Organized 35+ docs into semantic directories
- Created INDEX.md, QUICK_START.md, STRUCTURE.txt for navigation
- Added README.md for each major section

**Deployment Enhancements**
- Fixed Python 3.11 compatibility (generic function syntax, TypeAlias)
- Custom Node.js server with explicit 0.0.0.0 binding (fixes port routing)
- Docker configuration for Railway.app deployment
- Environment variables: PYTHONPATH, PORT=8080, NODE_ENV=production

**Next.js Integration**
- API handler bridges Next.js form → Python orchestrator
- Form submission parsing (multipart + urlencoded)
- File upload support for image-based puzzle generation
- Temporary file cleanup after processing

**E2E Testing**
- Playwright test suite for browser automation
- Form interaction tests
- File generation and download verification
- Comprehensive NONOGRAM_WEB_TEST_REPORT.md

**Configuration Updates**
- Missing `mode=random` field in form → fixed
- Path serialization in API handler
- Output directory parameter passing to CLI
- CLI seed handling (bypass for 'random' value)

### 🔍 Issues Identified & Resolved

1. **Form Mode Field** - Form defaulting to image mode without mode field
   - **Fix:** Added hidden `mode=random` field
   
2. **Python Compatibility** - Generic syntax issues with 3.11
   - **Fix:** Changed `dict[K,V]` → `Dict[K,V]` (PEP 585)
   
3. **Server Binding** - Next.js not accessible externally
   - **Fix:** Custom server.js with `hostname: '0.0.0.0'`
   
4. **Path Handling** - Path objects not serializable to JSON
   - **Fix:** Convert Path to string in API response
   
5. **Deployment Logging** - Insufficient debugging info
   - **Fix:** Added comprehensive logging at all steps

---

## Current State Assessment

### ✅ Production-Ready
- CLI: Fully functional, all tests passing
- Python core: Layered architecture with strict dependencies
- Web UI: Deployed on Railway, end-to-end tested
- Docker: Container-based deployment verified
- Database: None (stateless design)

### ⚠️ Known Gaps (As-Built vs. Prescriptive)

**Documentation Gaps:**
- NFR thresholds (timeout values, max grid size constraints)
- Retry/resampling bounds (documented in code, not in requirements)
- Solver performance characteristics (heuristics vs. formal analysis)
- API rate limiting / SLA not documented

**Test Coverage:**
- E2E tests: Form submission, file download
- Missing: Edge cases (oversized images, corrupted uploads)
- Missing: Performance tests for large grids

**Prescriptive Unknowns:**
- Why single context vs. split (answered in contexts.yml reasoning)
- Retry/nudge bounds (arbitrary vs. tuned)
- Difficulty tier calibration thresholds

### 📊 Architecture Confidence
- **Descriptive (code → model):** HIGH - Code is clear, structure visible
- **Prescriptive (why & NFRs):** MEDIUM - Intent visible but thresholds undocumented

---

## Integration Points

### Python ↔ Next.js

**Request Flow:**
```
Browser Form
    ↓
Next.js Page (app/page.tsx)
    ↓
API Handler (api/generate.py)
    ↓
Python orchestrator.generate()
    ↓
File export (PNG/SVG/JSON/CSV/PDF)
    ↓
HTTP Response (paths to files)
    ↓
ResultDisplay Component (downloads/previews)
```

**Key Files:**
- `nonogram-web/api/generate.py` - Request handler, form parsing
- `src/nonogram/web/submission.py` - Form field validation
- `src/nonogram/web/multipart.py` - Multipart file upload parsing
- `src/nonogram/orchestrator.py` - Core generation workflow

### Configuration Binding

**Dockerfile:**
- Python 3.11-slim base
- Node.js 20 installed via deb.nodesource
- Installs Python dependencies with pip
- Builds Next.js with npm
- Runs custom server.js

**Environment:**
```
PYTHONPATH=/app/src         # Python module resolution
PORT=8080                    # Server port
NODE_ENV=production          # Next.js optimization
```

**Deployment (Railway):**
- Automatic container build from Dockerfile
- PORT 8080 exposed
- Git-based CI/CD

---

## Test Coverage

### Unit Tests (Python)
```
tests/
├── test_cli.py              # CLI interface + structural guards
├── test_*.py                # Component tests
├── property/                # Property-based uniqueness verification
├── fixtures/                # Test data (grids, expectations)
└── helpers/                 # Brute-force oracle for verification
```

### E2E Tests (Playwright)
```
nonogram-web/e2e/
├── form_submission.spec.ts  # Generate puzzle workflow
├── file_download.spec.ts    # Export file retrieval
├── ui_interaction.spec.ts   # Form field interactions
└── edge_cases.spec.ts       # Error handling, validation
```

### Test Results
- **Python suite:** 160 tests passing ✅
- **E2E suite:** All workflow tests passing ✅
- **Deployment:** Verified on Railway ✅

---

## Dependencies

### Python Runtime
```
Pillow>=10.0        # Image processing (resize, dithering)
numpy>=1.24         # Array operations (grid representation)
reportlab>=4.0      # PDF export
pytest>=8.3         # Testing (dev only)
```

### Node.js Runtime
```
next@15             # React framework
react@18            # UI library
typescript@5        # Type checking
tailwindcss@4       # CSS utilities
@playwright/test    # E2E testing
```

**Closed dependency set:** No third-party packages beyond documented list (design principle)

---

## Recent Commits (Top 20)

```
3e5196f docs: reorganize documentation structure
991cea2 test: add directory writability diagnostic endpoint
31a43e5 debug: add diagnostic info to API response
11b4646 feat: make generated files downloadable from browser
aebbc62 debug(api): add detailed command logging
3b7671d debug(api): add comprehensive logging for CLI output parsing
4dd6f21 fix(api): pass output directory parameter to CLI
da12a63 fix(api): handle 'random' seed value by not passing it to CLI
3cbb3a6 docs: add deployment fix summary and UI investigation notes
b0dd5b5 fix(python): use Python 3.11 compatible generic function syntax
8558e05 fix(python): use Python 3.11 compatible TypeAlias syntax
b5075d4 fix(server): add custom Next.js server with explicit 0.0.0.0 binding
73505dd fix(dockerfile): use bash shell for npm start command
7092961 fix(dockerfile): explicitly bind to 0.0.0.0 for external connections
41d4a2f fix(dockerfile): revert to npm start with NODE_ENV=production
...
```

---

## Next Steps & Recommendations

### 🔍 Forge Architecture Formalization
1. Run `/forge:reverse drift` to capture recent changes (e2e, deployment)
2. Reconcile Next.js integration into external_systems.yml
3. Add API contract from generate.py handler
4. Mine E2E tests for acceptance criteria

### 📝 Documentation Gaps to Fill
1. **NFR Thresholds** - Timeout limits, grid size bounds, retry bounds
2. **Performance Baseline** - Solver time vs. grid size
3. **API Contract** - Request/response schema, error codes
4. **Deployment SLOs** - Availability, response time targets

### ✅ Quality Assurance
1. Edge case testing (large uploads, rate limits)
2. Performance benchmarking (dense grids at 40x40+)
3. Load testing (concurrent puzzle generation)
4. Security audit (CORS, input validation, file handling)

### 🚀 Future Enhancements
1. Caching layer (generated puzzles, processed images)
2. Batch generation API
3. Puzzle sharing/publishing (storage layer)
4. Leaderboard (tracking difficulty completion)

---

## File Inventory Summary

| Directory | Files | Purpose |
|-----------|-------|---------|
| src/nonogram/ | 9 modules | Core logic (CLI, orchestrator, capabilities) |
| nonogram-web/ | app, api, e2e | Frontend UI, API bridge, E2E tests |
| tests/ | 34 test files | Unit tests, property tests, fixtures |
| meta/architecture/ | 18 YAML files | Formal architecture model (forge) |
| docs/ | 35+ files | Organized documentation |

---

## Deployment Checklist

- [x] Python core tested and working
- [x] Next.js frontend built and tested
- [x] Docker container builds successfully
- [x] Environment variables configured
- [x] Deployed to Railway.app
- [x] E2E tests passing
- [x] Documentation reorganized
- [ ] Load testing completed
- [ ] Security audit completed
- [ ] Performance benchmarks documented
- [ ] SLOs defined

---

**Generated:** 2026-09-05  
**Next Review:** After `/forge:reverse drift` completes  
**Owner:** Architecture Team