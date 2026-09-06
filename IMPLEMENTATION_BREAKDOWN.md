# POC Implementation Breakdown (By 2026-11-15)

**Status:** Planning  
**Owner:** Ольга (implementation lead) + Анна (QA/partner)  
**Last Updated:** 2026-09-06

---

## I. Critical Path (Blocking Dependencies)

```
1. Database Schema & Setup (blocking all downstream)
   ↓
2. Difficulty Calculator (needed for admin panel metrics)
   ↓
3. Quality Metric Calculator (needed for admin panel metrics)
   ↓
4. Admin Panel (blocking book generation)
   ↓
5. Book Generation & PDF Export (final deliverable)
   ↓
6. Website User Features (nice-to-have by 15.11)
   ↓
7. Web Solver Game (nice-to-have, requirements TBD)
```

**Critical Path Duration:** 70 days (6 Sept → 15 Nov)  
**Slack available:** ~10 days for testing/iteration

---

## II. Phased Breakdown

### **PHASE 1: Preparation (Sept 6-20)**

#### **Task 1.1: Database Setup (with Alembic Migrations)**
**Assigned to:** Ольга  
**Duration:** 4-5 hours  
**Blocking:** Everything else  
**Reference:** DATABASE_MIGRATIONS.md (complete guide)

**Part A: Local PostgreSQL Setup (1 hr)**
- [ ] Install PostgreSQL locally (or Docker: `docker run -d -p 5432:5432 postgres:15`)
- [ ] Create dev database: `createdb nonogram_poc`
- [ ] Create `.env` with `DATABASE_URL=postgresql://localhost:5432/nonogram_poc`

**Part B: Alembic Setup (1 hr)**
- [ ] Install: `pip install alembic sqlalchemy`
- [ ] Initialize: `alembic init migrations/`
- [ ] Update `migrations/alembic.ini` connection string
- [ ] Update `migrations/env.py` to import ORM models

**Part C: ORM Models (1 hr)**
- [ ] Create `src/nonogram/db/models.py` with:
  - [ ] User (id, email, subscription_tier, puzzles_generated_month, created_at)
  - [ ] Nonogram (id, name, theme, width, height, difficulty_score, difficulty_tier, quality_score, strategies_used, solution_grid, clues_rows, clues_cols, image_source_url, status, created_at)
  - [ ] Book (id, title, description, theme, target_audience, nonogram_ids, cover_image_url, pdf_url, page_count, status, kdp_asin, created_at)
  - [ ] GenerationHistory (id, user_id, puzzle_id, image_url, timestamp)
  - [ ] UserSelectedBook (user_id, puzzle_id, book_id, selected_at)
- [ ] Create `src/nonogram/db/__init__.py` (connection factory)
- [ ] Create `src/nonogram/db/session.py` (session management)

**Part D: Generate & Test Migration (1 hr)**
- [ ] Auto-generate: `alembic revision --autogenerate -m "Create initial schema"`
- [ ] Review generated migration file
- [ ] Run locally: `alembic upgrade head`
- [ ] Verify: `psql -d nonogram_poc -c "\dt"`
- [ ] Write migration tests

**Part E: Documentation (0.5 hr)**
- [ ] Create `docs/DATABASE_SCHEMA.md` (all tables + columns)
- [ ] Create `docs/MIGRATIONS.md` (migration log)
- [ ] Update `docs/DATABASE_SETUP.md` with:
  - Local dev instructions
  - Railway setup (env vars)
  - Dockerfile migration command: `RUN alembic upgrade head`
  - Backup procedures

**Acceptance:** Schema on local + Railway PostgreSQL; migrations work; Python ORM connects; docs complete

---

#### **Task 1.2: Difficulty Calculator (Strategy-Based)**
**Assigned to:** Ольга  
**Duration:** 8-12 hours (includes research)  
**Requires:** docs/guides/solving_techniques.md analysis  
**Blocking:** Admin panel metrics display  
**Breakdown:**

**1.2a - Research & Algorithm Design (2-3 hours)**
- [ ] Read `docs/guides/solving_techniques.md` and `solving_techniques.png`
- [ ] Identify 5-10 core strategies (Line Logic, Pointing Pairs, Box/Line Reduction, Constraint Propagation, Backtracking)
- [ ] Generate 20+ test nonograms manually
  - [ ] 5 Easy puzzles (1-5 strategies)
  - [ ] 5 Medium puzzles (6-12 strategies)
  - [ ] 5 Hard puzzles (13+ strategies)
- [ ] Instrument solver to count strategy invocations
- [ ] Establish thresholds:
  - Easy: strategy_count < 6
  - Medium: 6 ≤ strategy_count < 15
  - Hard: strategy_count ≥ 15
- [ ] Document in: `meta/architecture/inputs/v2-difficulty-engine.md`

**1.2b - Implementation (4-5 hours)**
- [ ] Create `src/nonogram/analysis/strategy_counter.py`
  - [ ] `count_strategies(grid, clues) → {"difficulty_score": 1-100, "difficulty_tier": "Easy|Medium|Hard", "strategies": [...], "backtrack_depth": int}`
- [ ] Integrate into orchestrator (`src/nonogram/orchestrator.py`)
  - [ ] Call strategy counter after solver runs
  - [ ] Attach to Puzzle aggregate
- [ ] Unit tests for strategy counter (8-10 tests)
- [ ] Integration tests (3-5 end-to-end)

**1.2c - Validation (1-2 hours)**
- [ ] Test against the 20 reference puzzles
- [ ] Verify thresholds (Easy/Medium/Hard split)
- [ ] Measure performance overhead (target: < 10% slowdown)

**Deliverable:** `src/nonogram/analysis/strategy_counter.py` + tests + documentation

---

#### **Task 1.3: Quality Metric Calculator**
**Assigned to:** Ольга  
**Duration:** 6-8 hours  
**Blocking:** Admin panel display (secondary metric)  
**Requirements from PROJECT_PLAN_POC.md §4.2:**
- Input: original image + generated grid
- Output: quality_score (1-100), visual_similarity %, recognizability (high/medium/low)

**Breakdown:**

**1.3a - Algorithm Design (2 hours)**
- [ ] Analyze dithering quality (Floyd-Steinberg faithfulness)
- [ ] Define quality criteria:
  - Visual similarity: pixel-to-pixel match % (compare original binary to grid)
  - Silhouette preservation: do major features remain recognizable?
  - Density match: is filled-cell ratio similar?
- [ ] Create 10 test images + expected quality scores
- [ ] Document algorithm in: `meta/architecture/inputs/quality-metric.md`

**1.3b - Implementation (3 hours)**
- [ ] Create `src/nonogram/analysis/quality_metric.py`
  - [ ] `measure_quality(original_image, puzzle_grid) → {"score": 1-100, "similarity": 0.0-1.0, "recognizability": "high|medium|low"}`
- [ ] Use Pillow to convert image to binary, compare pixel-wise
- [ ] Integrate into orchestrator
- [ ] Unit + integration tests

**1.3c - Validation (1 hour)**
- [ ] Test against 10 reference images
- [ ] Verify scores make intuitive sense

**Deliverable:** `src/nonogram/analysis/quality_metric.py` + tests

---

#### **Task 1.4: Admin Panel Design & Setup**
**Assigned to:** Ольга  
**Duration:** 4-5 hours  
**Requirements from PROJECT_PLAN_POC.md §VI:**

**1.4a - Design (2 hours)**
- [ ] Finalize UI mockups for three pages:
  1. Batch Generation form (count, sizes, theme, filters)
  2. Puzzle Review grid (preview, metrics, filter, checkbox)
  3. Book Parameters (title, cover, format, options)
- [ ] Design data flow (from generation → storage → selection → export)
- [ ] Identify API endpoints needed

**1.4b - Backend API Structure (2-3 hours)**
- [ ] Create API endpoints:
  - `POST /api/admin/generate-batch` — initiate batch generation
  - `GET /api/admin/puzzles` — list generated puzzles with metrics
  - `POST /api/admin/puzzles/{id}/approve` — mark for book
  - `GET /api/admin/books/{id}` — get selected puzzles
  - `POST /api/admin/books/{id}/generate-pdf` — export PDF
- [ ] Design request/response schemas (OpenAPI or JSON schema)
- [ ] Plan async task queue (batch generation takes time)

**Deliverable:** API spec + preliminary endpoints ready for implementation

---

### **PHASE 2: Admin Panel Implementation (Sept 20 - Oct 15)**

#### **Task 2.1: Backend - Batch Generation Service**
**Assigned to:** Ольга  
**Duration:** 8-10 hours  
**Depends on:** Tasks 1.1, 1.2, 1.3  

**Breakdown:**
- [ ] Create `src/nonogram/admin/batch_generator.py`
  - [ ] `generate_batch(count, sizes, theme, mode, quality_filter) → Batch`
  - [ ] Generate puzzles concurrently (use asyncio or threading)
  - [ ] Attach difficulty + quality scores to each
  - [ ] Store in database
  - [ ] Log progress
- [ ] Create Flask/FastAPI endpoint: `POST /api/admin/generate-batch`
- [ ] Add request validation + error handling
- [ ] Add background job support (Celery or asyncio queue)
- [ ] Tests: 5-8 covering various batch configs

**Deliverable:** Working batch generation with metrics

---

#### **Task 2.2: Backend - Puzzle Storage & Querying**
**Assigned to:** Ольга  
**Duration:** 4-5 hours  
**Depends on:** Task 1.1  

**Breakdown:**
- [ ] Implement ORM models for Puzzle, Book (SQLAlchemy or similar)
- [ ] Implement filtering: `GET /api/admin/puzzles?size=20x20&difficulty=Hard&quality_min=70`
- [ ] Implement selection: `POST /api/admin/puzzles/{id}/approve`
- [ ] Implement deselection: `DELETE /api/admin/puzzles/{id}`
- [ ] Tests: 8-10 covering all query/filter combinations

**Deliverable:** Puzzle storage + API working

---

#### **Task 2.3: Frontend - Admin Panel UI**
**Assigned to:** Ольга (or frontend dev if available)  
**Duration:** 12-16 hours  
**Tech Stack:** Next.js 15, React, Tailwind CSS  

**3 Pages:**
1. **Generate Batch Page** (2.3a, 3-4 hours)
   - Form: count, sizes (checkboxes), theme, source (random/images), quality filter
   - Submit button → calls `/api/admin/generate-batch`
   - Progress bar (polls `/api/admin/batch/{id}/status`)
   
2. **Review Page** (2.3b, 6-8 hours)
   - Grid of puzzles with preview image
   - Each card shows: size, difficulty, quality, status
   - Filters (size, difficulty, quality) at top
   - Checkbox to mark "for Book 1"
   - Count: "Selected: X / 200"
   
3. **Book Parameters Page** (2.3c, 3-4 hours)
   - Form: title, author, description, cover upload, format (A4/Letter), puzzles/page, include solutions
   - Preview button (shows first page)
   - Generate PDF button → calls `/api/admin/books/{id}/generate-pdf`

**Deliverable:** Three functional pages + routing

---

#### **Task 2.4: Book PDF Generation**
**Assigned to:** Ольга  
**Duration:** 6-8 hours  
**Depends on:** Tasks 1.1, 2.1  

**Breakdown:**
- [ ] Create `src/nonogram/export/pdf_book_generator.py`
  - [ ] Input: list of nonograms, book metadata (title, cover, format)
  - [ ] Output: single PDF file
  - [ ] Layout: 1-2 nonograms per A4 page
  - [ ] Include: page numbers, difficulty labels, optional solutions at end
  - [ ] Use ReportLab or similar
- [ ] Implement endpoint: `POST /api/admin/books/{id}/generate-pdf`
- [ ] Handle cover insertion
- [ ] Format for Amazon KDP specs
- [ ] Tests: 3-5 covering different configs

**Deliverable:** Working PDF book generation

---

#### **Task 2.5: Admin Panel Testing with Anna**
**Assigned to:** Ольга + Анна  
**Duration:** 4-6 hours  
**Checkpoint date:** 2026-10-15  

**Test Plan:**
- [ ] Generate 100 random puzzles, review metrics
- [ ] Filter by difficulty/quality
- [ ] Select 50 puzzles for test book
- [ ] Generate PDF
- [ ] Check PDF formatting (is it KDP-ready?)
- [ ] Record bugs/suggestions in `ADMIN_PANEL_TESTING.md`

**Gate:** All critical bugs fixed; panel is usable

---

### **PHASE 3: Book Generation (Oct 15-30)**

#### **Task 3.1: Generate 200+ Christmas Nonograms**
**Assigned to:** Ольга  
**Duration:** 8-12 hours  
**Depends on:** Task 2.5 (admin panel must be polished)  

**Breakdown:**
- [ ] Use admin panel to generate 250 puzzles:
  - Variety: mix of 10×10, 20×20, 30×30
  - Quality filter: only >= 70
  - Theme: Christmas (if seed/mode supports it, or manual naming)
- [ ] Manual quality review:
  - [ ] Download each PDF preview
  - [ ] Reject any that don't look good (image puzzles especially)
  - [ ] Select best 200 for book
- [ ] Organize by difficulty (roughly equal Easy/Medium/Hard)
- [ ] Arrange in book order

**Deliverable:** 200 approved nonograms selected for book

---

#### **Task 3.2: Book Cover & Metadata**
**Assigned to:** Ольга (+ Анна for design input)  
**Duration:** 4-6 hours  

**Breakdown:**
- [ ] Design or find book cover (Christmas theme, seniors-friendly)
- [ ] Create metadata:
  - Title: "Christmas Nonogram Puzzles for Adults" (or similar)
  - Author: Ольга (or business name)
  - Description: "50 hand-selected Christmas-themed nonogram puzzles, easy to hard"
- [ ] Add ISBN (KDP auto-assigns or manual lookup)
- [ ] Prepare cover image (Amazon KDP specs: usually 3000×4500 pixels, RGB)

**Deliverable:** Cover file + metadata ready for KDP

---

#### **Task 3.3: Final PDF Book**
**Assigned to:** Ольга  
**Duration:** 2-3 hours  

**Breakdown:**
- [ ] Use admin panel to generate final PDF with:
  - [ ] Cover page
  - [ ] 200 selected puzzles
  - [ ] Solutions (end of book or separate PDF)
  - [ ] Proper KDP formatting (margins, fonts, page count)
- [ ] Validate PDF (open in viewer, check page count, margins)
- [ ] Export from admin panel → download

**Deliverable:** Production-ready PDF book file

---

### **PHASE 4: Testing & Release (Nov 1-15)**

#### **Task 4.1: QA with Anna**
**Assigned to:** Анна + Ольга  
**Duration:** 4-6 hours  

**Test Plan:**
- [ ] Download final PDF
- [ ] Print first 10 pages (check quality)
- [ ] Solve 5 puzzles (verify they are solvable and consistent)
- [ ] Check difficulty labels (are Easy/Medium/Hard correct?)
- [ ] Check cover formatting
- [ ] Report any issues in `FINAL_QA_REPORT.md`

**Gate:** No critical issues; book is ready for KDP

---

#### **Task 4.2: Amazon KDP Preparation**
**Assigned to:** Ольга  
**Duration:** 3-4 hours  

**Breakdown:**
- [ ] Create Amazon KDP account (if not already done)
- [ ] Prepare KDP upload:
  - [ ] PDF file
  - [ ] Cover image
  - [ ] ISBN (optional; KDP can assign)
  - [ ] Metadata (title, description, keywords, category)
- [ ] Set price point ($5.99? $9.99?) based on page count/market research
- [ ] Upload to KDP (don't publish yet; keep in draft)

**Deliverable:** Book ready to publish on KDP

---

#### **Task 4.3: Website User Feature (Basic)**
**Assigned to:** Ольга  
**Duration:** 4-6 hours (if time permits)  

**Note:** This is lower priority than book. Implement if schedule allows.

**Breakdown:**
- [ ] Create user registration (email + password)
- [ ] Implement puzzle generation endpoint: `POST /api/generate` (photo upload)
- [ ] Track monthly usage (limit to 3 free)
- [ ] Add subscription checkout placeholder (Stripe)
- [ ] Frontend: simple upload form + preview

**Deliverable:** Basic website flow working (v1, polish later)

---

#### **Task 4.4: Documentation & Release Notes**
**Assigned to:** Ольга  
**Duration:** 2-3 hours  

**Breakdown:**
- [ ] Update README.md with POC achievements
- [ ] Create RELEASE_NOTES_POC.md:
  - Deliverables (book, website, solver status)
  - What works, what's pending
  - Known limitations
- [ ] Document admin panel user guide (for Anna)
- [ ] Tag release: `v2.0.0-poc` in git

**Deliverable:** Clear documentation of POC state

---

## III. Resource Allocation

| Role | Tasks | Est. Hours | Start | End |
|------|-------|-----------|-------|-----|
| **Ольга** | All technical work | 80-100 | 6 Sept | 15 Nov |
| **Анна** | QA, feedback, design input | 20-30 | 15 Oct | 15 Nov |

**Total project:** 100-130 hours

**Pace:** ~2-3 hours/day average (10-12 hours/week)

---

## IV. Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Difficulty engine too slow | Medium | High | Measure overhead early (Task 1.2c); optimize if > 15% |
| Quality metric inaccurate | Medium | Medium | Test on real images; adjust thresholds based on feedback |
| Admin panel UI too complex | Medium | High | Start simple (MVP features); iterate based on Anna's feedback |
| PDF generation formatting issues | Medium | Medium | Test early on real KDP samples; iterate format |
| Time runs out (15 Nov) | Low | Critical | Track weekly progress; cut scope (skip solver game if needed) |

---

## V. Scope Prioritization (If Time Runs Short)

**MUST HAVE by Nov 15:**
1. ✅ Book with 200 puzzles (highest priority — the business deliverable)
2. ✅ Admin panel (required to curate the book)
3. ✅ Difficulty + Quality calculators (required for admin metrics)
4. ✅ Database

**NICE TO HAVE by Nov 15:**
1. ⏳ Website user features (can launch in Dec)
2. ⏳ Solver game (can launch in Dec/Jan)
3. ⏳ Advanced admin features (filters, sorting, presets)

**CUT IF TIME RUNS OUT:**
1. Solver game (defer to v3)
2. User authentication on website (start simple with free puzzles)

---

## VI. Success Criteria (2026-11-15)

- [ ] PostgreSQL database running (Railway.app or local)
- [ ] Difficulty calculator working (strategy-based)
- [ ] Quality metric calculator working (image→grid fidelity)
- [ ] Admin panel deployed (generate, review, select, curate)
- [ ] Book PDF generation working
- [ ] 200 Christmas nonograms created + reviewed by Anna
- [ ] Book PDF uploaded to Amazon KDP (draft, ready to publish)
- [ ] Website basics ready (photo upload, PDF export)
- [ ] All documentation updated
- [ ] Zero critical bugs; known minor issues documented

---

**Next Action:** Start Task 1.1 (Database Setup) on 2026-09-06  
**Follow-up Check-in:** 2026-09-20 (end of Phase 1)  
**Final Gate:** 2026-11-08 (1 week before deadline for final polish)

