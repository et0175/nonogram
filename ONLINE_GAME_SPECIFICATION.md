# Online Nonogram Solver Game - Specification

**Status:** REQUIREMENTS GATHERING (TBD with Anna)  
**Purpose:** Define game features for web-based nonogram solver  
**Owner:** Ольга (with Анна for feedback)  
**Deadline:** Feature list finalized by 2026-11-15 (launch post-MVP)  
**Timeline:** v3 feature (nice-to-have for Nov 15, full implementation in Dec)

---

## Overview

A web-based game where users can:
1. Select a nonogram from library
2. Click cells to mark them black/white
3. Solve the puzzle with feedback
4. See solution when done
5. Track progress & difficulty

---

## Core Features (MVP)

### 1.1 Puzzle Selection

**UI:**
- [ ] Browse puzzle library (filtered by difficulty)
- [ ] See puzzle preview (size, difficulty rating)
- [ ] Click "Play" to start

**Functional Requirements:**
- [ ] Display puzzles from database (nonograms table)
- [ ] Filter by: Difficulty (Easy/Medium/Hard), Size (10×10 / 20×20 / 30×30)
- [ ] Show puzzle stats: difficulty score, estimated solve time
- [ ] Random puzzle button (pick one for me)

### 1.2 Game Board

**UI:**
- [ ] Nonogram grid displayed
- [ ] Row/column clues visible and easy to read
- [ ] Current cell highlighted
- [ ] Keyboard shortcuts visible (help text)

**Functional Requirements:**
- [ ] Grid cells are clickable
- [ ] Support three states per cell:
  - [ ] Empty (white)
  - [■] Filled (black)
  - [?] Unknown/marked (gray X or dot, for notes)
- [ ] Right-click or keyboard toggle between states
- [ ] Clues remain visible while scrolling (sticky headers)
- [ ] Zoom in/out for large puzzles

### 1.3 Solve Mechanics

**Functional Requirements:**
- [ ] **Live validation**: Highlight rows/columns that are complete and correct
- [ ] **Partial validation**: When clicked, tell user if current state is valid (no conflicts)
- [ ] **Constraint checking**: Prevent invalid placements (if user tries to place cells that violate clues)
- [ ] **Undo/Redo**: Full move history
- [ ] **Clear board**: Start over (confirm before clearing)
- [ ] **Hint**: Reveal 1-5 cells (optional difficulty modifier)

### 1.4 Solution & Feedback

**Functional Requirements:**
- [ ] When user completes puzzle (all cells correct):
  - [ ] "Congratulations!" message
  - [ ] Show solve time (elapsed)
  - [ ] Show difficulty rating
  - [ ] Offer next puzzle button
  - [ ] Optional: Save score (name, time, difficulty)
  
- [ ] If user gets stuck:
  - [ ] "Show Solution" button (marks grid as failed)
  - [ ] "Give Up" button (same)
  - [ ] Option to review solution

### 1.5 Progress Tracking (Optional for MVP)

**Functional Requirements:**
- [ ] Track user's completed puzzles (no auth required yet; use browser localStorage)
- [ ] Display stats:
  - Total puzzles solved
  - Average solve time
  - Difficulty breakdown (Easy/Medium/Hard count)
  - Streak (consecutive days playing?)

---

## Questions for Anna (To Be Answered)

These need discussion to finalize the spec:

### **1. Gameplay Style**
- [ ] Should game enforce valid moves (prevent clicking invalid cells)?
  - Option A: Strict (can't make invalid moves) → easier, but less freedom
  - Option B: Permissive (allow any move, validate on submit) → harder, more freedom
  - **Anna's preference?**

### **2. Difficulty Modes**
- [ ] **Easy mode**: Can't make mistakes (guide the player)
  - Help: Highlight if row/column is complete & correct
  - Help: Prevent invalid moves
  
- [ ] **Hard mode**: No help, just raw puzzle solving
  - No validation until submit
  - No hints
  
- [ ] **Hint system**: Should there be hints?
  - Yes, but cost (1 free hint, then purchase)?
  - No hints?
  - **Anna's preference?**

### **3. Progression & Engagement**
- [ ] Should game have levels/progression?
  - Simple: Just pick any puzzle
  - Complex: Daily puzzles, achievement badges, leaderboard
  - **Anna's preference?**

- [ ] Should there be a timer/speed-run mode?
  - Yes, show timer, race against the clock
  - No, relaxed solving
  - **Anna's preference?**

### **4. Monetization**
- [ ] Should game be free, or have premium features?
  - Free to play (all puzzles free)
  - Freemium (few free, subscribe for more)
  - **Anna's preference?**

- [ ] What would premium unlock?
  - Unlimited daily puzzles
  - Hints
  - Custom difficulty packs
  - **Anna's preference?**

### **5. Mobile vs. Desktop**
- [ ] Should game be fully responsive (mobile-friendly)?
  - Yes, play on phone/tablet
  - Desktop-only for now
  - **Anna's preference?**

- [ ] Touch controls (tap to cycle through cell states)?
  - Precise (hold to mark with second state)
  - Quick (single tap = black, double tap = white, triple tap = clear)

### **6. Social Features**
- [ ] Should users be able to share solved puzzles?
  - Share score on social media
  - Share puzzle link (challenge friends)
  - **Anna's preference?**

### **7. Game Feel & Polish**
- [ ] Animations?
  - Smooth cell fill when marking
  - Confetti when puzzle complete
  - **Anna's preference?**

- [ ] Sound effects?
  - Click sound for cell marking
  - Victory sound when complete
  - **Anna's preference?**

---

## Nice-to-Have Features (Beyond MVP)

- [ ] Daily puzzle challenge (same puzzle for all users each day)
- [ ] Leaderboard (fastest times, most puzzles solved)
- [ ] User accounts (sign up, save progress across devices)
- [ ] Custom puzzles (upload your own image → generate nonogram → solve)
- [ ] Multiplayer (race a friend in real-time)
- [ ] Puzzle creation tool (design your own nonogram)
- [ ] Tournament mode (solve 10 puzzles, see ranking)
- [ ] Dark mode
- [ ] Accessibility (high contrast, large text, keyboard-only)

---

## Technical Architecture

**Status:** agreed 2026-10-23 (Ольга + Claude). Key decision: **one player app** serves both
the QR codes printed in books and online library browsing — same game, different entry points.
No login, no live database in the customer path, no new backend stack.

### One app, three routes

| Route | Purpose | Reached from |
|-------|---------|--------------|
| `/play/<puzzle-id>` | The game board itself (the only hard part to build; identical for every entry point) | Book landing, library, shared links |
| `/b/<book-slug>` | Per-book landing: "Puzzles from this book", tap one to play | **QR code printed in the book** |
| `/library` | Browse/filter all published puzzles (section 1.1) | Direct visits |

The book player and the online game are the same product at different entry points; the v3
features (library, progress, scores) grow inside this app, not beside it.

### **Frontend** — static, client-side, mobile-first
- [ ] Static client-side app (small React/Preact or vanilla TS — pick for maintainability; the
      empty `nonogram-web/` has only build leftovers, so this is a fresh small build either way)
- [ ] **Static hosting** (Cloudflare Pages / Vercel / Render static site): free, scales, and
      **no cold starts** — a QR scan from a book must load instantly. (The admin service on
      Render's free plan spins down when idle; a 30–60s cold start on first scan is the normal
      case there, not the edge case. Customer traffic therefore never touches the admin service.)
- [ ] All solve validation is **client-side**: checking a grid against the clues is trivial
      JS (no solution is sent — ADR-0038/R6). The Python solver is only needed at *generation*
      time, which happened before the book was printed — it is not in the play path at all.
- [ ] Game board component (grid rendering, cell interaction, three states, undo history)
- [ ] Mobile-first touch UI from day one — nearly every QR scan is a phone (thumb-sized cells,
      pinch-zoom; see Question 5)
- [ ] Progress tracking via `localStorage` (section 1.5), no accounts

### **Puzzle data** — static JSON exported on publish, no live DB reads
- [ ] Admin panel exports static JSON when a puzzle is published / a book is finalized:
  - [ ] library index (id, size, difficulty, preview metadata)
  - [ ] one file per puzzle (clues + metadata — **no solution**: ADR-0038/R6
        forbids any public surface from shipping a puzzle's answer to the
        browser; the player detects completion as "every clue satisfied",
        which for a uniquely-solvable puzzle *is* the solution)
  - [ ] one file per book (slug → ordered list of its puzzle ids)
- [ ] A printed book is frozen: its puzzles never change, so its JSON and QR links never break
- [ ] The admin panel and its Postgres stay private; a deploy there remains a deliberate
      decision (see `render.yaml` notes) and can never take the player down

### **Usage tracking** — no login, no stored IPs
- [ ] **Book slug in the QR URL** (`/b/<book-slug>`, distinct per book/edition) is the primary
      signal: which book drives visits, scans per book over time
- [ ] Privacy-friendly analytics script — Plausible (~€9/mo) or GoatCounter (free): visits,
      estimated uniques, country, device — cookieless, no consent banner needed
- [ ] Raw IPs are **not** stored: an IP is personal data under GDPR, and it's inaccurate anyway
      (mobile carrier NAT shares one IP across many people; one phone changes IPs constantly)
- [ ] Optional later: `play_events` table (append-only) + tiny endpoint, if game-level events
      (started / solved / gave up / solve time) are wanted beyond page analytics

### **Write-only API** — deferred until December features need it
Only scores / leaderboard / daily puzzle require a backend, and only for **writes**. These are
fire-and-forget POSTs after a puzzle is solved: a cold start delays a score submission by a few
seconds, never gameplay. The play path stays static and never depends on this service.
- [ ] POST `/api/games/solve` — submit completed puzzle (for scoring)
- [ ] GET `/api/games/leaderboard` — top scores (if included)
- [ ] games_scores table: user_id, puzzle_id, time_seconds, difficulty, status (solved/failed)
      — in the **existing** Postgres (`nonogram_poc`); no separate database
- [ ] games_daily_puzzle table: date, puzzle_id

---

## Success Criteria for MVP Launch (Post-Nov 15)

- [ ] Game loads a puzzle without errors
- [ ] Clicking cells toggles state (black/white/unknown)
- [ ] Undo/Redo works
- [ ] Can mark puzzle as complete
- [ ] Solution can be revealed
- [ ] Can play different puzzle sizes (10×10, 20×20, 30×30)
- [ ] Mobile-responsive (at least phone + desktop)
- [ ] No major performance issues (grid interaction is snappy)

---

## Questions for Implementation Planning

### **Build Complexity**
- **Estimated effort**: 40-80 hours (depending on feature scope)
- **Timeline**: 2-3 weeks after Nov 15 MVP
- **Bottleneck**: If solver validation is slow, needs optimization

### **Solver Integration**
- [x] **Answered (2026-10-23, see Technical Architecture):** the Python solver is not used at
      play time. Validation is comparing the player's grid against the clues —
      trivial client-side JS, instant at any grid size, works offline. (Not against a stored
      solution: ADR-0038/R6 keeps the answer out of any public page.) The solver's job
      (guaranteeing unique solvability) is done at generation time, before the book is printed.

### **Backend Work Needed**
- [ ] Admin panel: static JSON export on puzzle publish / book finalization (library index,
      per-puzzle files, per-book files) — this replaces puzzle-fetching API endpoints
- [ ] Deferred to the write-API phase (December, see Technical Architecture):
  - New tables in existing Postgres (games_scores, daily_puzzle)
  - API endpoint for scoring; leaderboard query (if included)
  - Periodic task: pick daily puzzle each day (if included)

---

## Phase Timeline (Post-MVP)

| Phase | Dates | Work |
|-------|-------|------|
| **Design** | Nov 16-20 | Finalize spec with Anna |
| **Backend** | Nov 21-27 | API + DB tables |
| **Frontend** | Nov 28 - Dec 11 | Game board + UI |
| **Polish** | Dec 12-18 | Testing, bug fixes, performance |
| **Launch** | Dec 20+ | v3.0.0 release |

---

## Decision Log

**To be filled in after discussion with Anna:**

| Question | Options | Decision | Rationale |
|----------|---------|----------|-----------|
| Strict vs. Permissive | A / B | ___ | ___ |
| Hints? | Yes / No | ___ | ___ |
| Progression? | Simple / Complex | ___ | ___ |
| Timer/Speed? | Yes / No | ___ | ___ |
| Mobile? | Yes / Desktop-only | ___ | ___ |
| Monetization? | Free / Freemium | ___ | ___ |

---

## Current Status

🔍 **Awaiting feedback from Anna** on core features above.

Once decisions are made, this document will be updated with final spec.

---

**Next Steps:**
1. Share this document with Anna
2. Discuss each question
3. Fill in Decision Log
4. Create kanban cards for game development (post-Nov 15)
5. Begin design phase Dec 1

