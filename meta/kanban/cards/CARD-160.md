# CARD-160: The admin panel opens any puzzle in a solver page with its clues

**Status:** blocked
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** —
**Worktree:** —
**Source:** owner design doc "Nonograms - Print layout" (Google Doc 1pJKF2qX6mC9qw4Cf9Nv3hblTDmtoHwP5Tb8wzK1_WqM), sections "Online solver", "Infrastructure", "V1"; raw-requirements.md Delta 2026-09-24 (a) and 2026-10-03 (a)
**Idea:** —
**Wave:** 31
**Depends on:** —
**Touches:** src/nonogram/admin/app.py, src/nonogram/admin/templates/puzzle_solve.html, src/nonogram/admin/static/solver.js, src/nonogram/admin/static/admin.css, src/nonogram/admin/templates/_puzzle_table.html, tests/test_puzzle_solver_page.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** architect delta — CON-002 ("no playable/interactive puzzle output") forbids this card as written, and the online solver has no FR yet. Needs /forge:architect: amend or supersede CON-002 for the admin-panel solver, add the solver FR with ACs, and an ADR for the client approach (see "Decisions this card needs"). Unblock after that delta, then re-run /forge:kanban decompose so the card cites the real FR.

## What to implement

The first slice of the online solver the owner's document asks for. V1 is
"only the solver for Book 1", built for now **inside the admin panel**:
clicking a puzzle opens it to be solved. Public hosting, QR codes and the
picture-to-puzzle generator are later phases.

This card builds the page and the data it needs. Marking cells is
CARD-161, and errors and the solved state are CARD-162.

1. **Route.** `GET /puzzle/<puzzle_id>/solve` renders `puzzle_solve.html`
   for a stored puzzle. Unknown id → the panel's 404. The puzzle is read
   through `puzzle_review.get_puzzle`; nothing is written.
2. **Data for the page.** Row and column clues come from the stored grid
   through the one encoder (`compute_clues`, the same call the storage
   boundary makes). Never re-derive clues another way. The page also needs
   the solution, for CARD-162's error count. For an admin-only POC it can
   ship inside the page. Name that choice in the ADR, because a public
   solver must not hand the answer to the browser.
3. **Board.** An empty grid of the puzzle's real width × height, with:
   - every fifth line heavier (the counting aid the printed pages use);
   - **row clues in boxes** to the left and **column clues in boxes**
     above, as the document's "clue numbers in box" sample shows;
   - a header reading "Puzzle <title>" and the tier ("MEDIUM"), mirroring
     the printed page header the document sketches.
   Size it to fit a laptop screen for the largest supported grids
   (`limits.MAX_SIZE` per side). Use tokens from `meta/design/` for every
   colour and spacing value.
4. **Entry point.** The puzzle detail modal (`_puzzle_table.html`) gets a
   "Solve" action linking to the page.
5. **State model only.** `solver.js` holds the board state, one of
   `unknown | filled | empty` per cell, and renders it. It has no input
   handling yet, beyond what's needed to prove the board renders from
   state. Keep the state logic separate from rendering, as a small pure
   module, so CARD-161/162 can test it.

## Acceptance criteria

- **AC-1:** Opening `/puzzle/<id>/solve` for a stored puzzle shows a grid
  of its exact width and height, with every row's and column's clues equal
  to `compute_clues(grid)`, a `(0,)` line shown as "0".
  *test: TestSolverPage_ShowsTheClues*
- **AC-2:** Every fifth grid line is drawn heavier, on both axes,
  including on non-square grids.
  *test: TestSolverPage_EmphasisesEveryFifthLine*
- **AC-3:** An unknown puzzle id returns the panel's 404, and the detail
  modal offers a link to the solver page.
  *test: TestSolverPage_UnknownPuzzleIs404; TestPuzzleDetail_OffersSolve*
- **AC-4:** All cells start `unknown`, and the rendered board matches the
  state the page script holds.
  *test: browser-level test per the ADR (see below)*

## Guardrails

- G-1: No new **runtime** dependency (ADR-0006/R1: stdlib + Pillow + NumPy).
  The client is plain JavaScript served as a static file, with no build
  step and no framework, unless the ADR decides otherwise.
- G-2: Nothing under `src/nonogram/solver/` changes. That is the uniqueness
  solver (COMP-005), a different thing from this player page.
- G-3: Read-only. No puzzle, book or batch row is written, and no progress
  is persisted (not requested).
- G-4: The panel stays loopback-only (CON-015). This card adds no public
  route, auth or hosting.

## Decisions this card needs (for the architect delta)

- **CON-002:** "no playable/interactive puzzle output". The owner's
  document now asks for exactly that. Amend it to allow the admin-panel
  solver, or supersede it.
- **Client approach (ADR):** vanilla JS in the Flask admin panel (the
  recommendation, fits G-1) versus a separate front end. The stale
  `nonogram-web/` directory has only build artefacts, so there is no
  source to reuse.
- **Browser testing:** `pytest-playwright` and Chromium are installed in
  the venv but declared nowhere and used by no test. Using them for the
  solver's interaction tests means adding them to the `dev` extra. That's
  a dev-only dependency decision, outside ADR-0006/R1's runtime baseline.
- **Solution in the page:** acceptable for an admin POC; must change before
  any public solver.

## Architecture context

- **FR:** — (none yet: the online solver needs an FR; see Blocked by)
- **CON:** CON-002 (conflicts), CON-015 (loopback), ADR-0006/R1 (dependency baseline)
- **Components:** COMP-009 (admin panel)
- **Trace:** meta/architecture/trace.yml

## Design context

- **Design system:** meta/design/: brief.md, tokens.css, components.md
- **UI components:** SolverBoard (new; register in components.md), clue boxes (new)
- **Screens:** /puzzle/<id>/solve
- **Reference:** puzzle-nonograms.com (owner's reference). The document's
  reference screenshots were not readable through the Drive text export,
  so check them before building.

## Worktree notes

- [Origin] Cut 2026-10-03 at the owner's request ("make cards for the
  solver") from the owner's design doc. Marked architectural: it is the
  first card of a new product surface, and its client structure is what
  CARD-161/162 copy.
