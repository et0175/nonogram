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

## Technical Architecture (Preliminary)

### **Frontend** (React/Next.js)
- [ ] Game board component (grid rendering, cell interaction)
- [ ] Game state management (which cells are marked, undo history)
- [ ] Puzzle library page
- [ ] Leaderboard page (if included)
- [ ] User profile page (if included)

### **Backend API** (Python/Flask)
- [ ] GET `/api/games/puzzles` — list available puzzles
- [ ] GET `/api/games/puzzles/{id}` — get puzzle details
- [ ] POST `/api/games/solve` — submit completed puzzle (for scoring)
- [ ] GET `/api/games/leaderboard` — top scores (if included)

### **Database** (PostgreSQL)
- [ ] games_scores table: user_id, puzzle_id, time_seconds, difficulty, status (solved/failed)
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
- [ ] Should game use existing solver to validate moves?
  - Validate after each cell mark? (slow if grid is large)
  - Validate only on submit? (faster, but less feedback)
- [ ] Performance: Can solver handle 100+ validation checks per puzzle?

### **Backend Work Needed**
- [ ] New tables in database (games_scores, daily_puzzle)
- [ ] API endpoints for puzzle fetching + scoring
- [ ] Leaderboard query (if included)
- [ ] Periodic task: pick daily puzzle each day (if included)

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

