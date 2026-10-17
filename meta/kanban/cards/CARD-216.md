# CARD-216: A puzzle's given cells are stored with it, and the player shows them as locked marks

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/216-given-cells-player
**Worktree:** —
**Source:** owner's Google Doc "Nonograms - Print layout", 2026-10-13 ("## Puzzle generator — include black\\white cells in the puzzle grid to make it uniquely solvable"; "## Infrastructure — make for now solver under the admin panel (when we click on the puzzle) and add to generator an option … as POC"); owner decision 2026-10-13 via AskUserQuestion — "Cut them now as POC cards" (the option covered the algorithm, the rendering **and** the player)
**Idea:** —
**Wave:** —
**Depends on:** CARD-214
**Touches:** src/nonogram/db/models.py, migrations/versions/, src/nonogram/admin/app.py, src/nonogram/admin/templates/puzzle_solve.html, src/nonogram/admin/static/solver.js, src/nonogram/admin/static/solver_state.js, src/nonogram/admin/static/admin.css, tests/test_puzzle_solver_givens.py, tests/test_puzzle_solver_page.py, tests/test_admin_import_consistency.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**Current behaviour (verified by reading the code).**

- `db.models.Puzzle` (`db/models.py:51`) stores `grid` (JSON `list[list[bool]]`),
  `clues_rows`, `clues_cols`, extent, scores, tier, strategies, status. There is
  **no** column for pre-revealed cells.
- The player page (`/puzzles/<id>/solve`) embeds the clues as JSON from
  `compute_clues` of the stored grid (ADR-0038/R3) and the solution behind the
  admin door (ADR-0038/R6). Every cell starts undecided: `solver_state.js`'s
  board is built from the extent alone, and every cell is markable, undoable
  and resettable.
- The error counter counts marks that disagree with the solution; the solved
  predicate requires every cell settled and no `?` left.

**What changes.**

1. **Storage.** A `givens` JSON column on `puzzles` (nullable, `None` = no
   givens), holding CARD-214's `list[list[bool | None]]` shape, with an
   Alembic migration under `migrations/versions/`. Expand-only: existing rows
   read as no givens, nothing is backfilled. The generation path writes the
   column when the reveal policy produced givens.
2. **The player receives them.** The page embeds `givens` alongside the clues,
   validated the same way the clues payload already is (shape against the
   extent, each given equal to the solution's own cell — a contradictory given
   is a broken row, and the page must say so rather than render a puzzle that
   cannot be solved).
3. **Locked marks.** A given cell starts in its revealed state and **cannot be
   changed**: clicks, drags, the brush menu, Region, undo, redo and Reset all
   leave it alone. It is drawn so it reads as *given*, not as the player's own
   mark (a distinguishable treatment — e.g. the filled given slightly inset or
   a different fill token, the white given as the printed dot; keep it within
   the design tokens, and keep contrast adequate).
4. **Counters.** A given is not the player's work: it never counts as an error,
   and the percent-correct figure (CARD-187) counts it as already correct, so a
   puzzle with 3 givens does not open at 0 %. The solved predicate is unchanged
   — givens are already settled, correctly, by definition.
5. **Hints.** CARD-183's hint reveals one line-logic-deducible cell; it must
   never "reveal" a cell that is already given.
6. **Resume.** CARD-185's per-browser resume must not restore a stored board
   that contradicts the givens (an older local record for the same puzzle): on
   mismatch, the givens win and the rest of the record is kept.
7. **State logic stays pure** (ADR-0038/R4): "which cells are locked" is state,
   and the lock must be enforced in the state module — not only in the DOM
   handlers, or a keyboard path will bypass it.

## Acceptance criteria

- **AC-1** (happy, storage): *Given* a generated puzzle with givens, *when* it
  is stored and read back, *then* its `givens` match what generation produced;
  *and given* a pre-existing row, *when* it is read, *then* its givens are
  empty. (test: `TestPuzzleGivens_RoundTripAndLegacyRowsReadEmpty`)
- **AC-2** (happy, render): *Given* a puzzle with one filled and one white
  given, *when* the player page loads, *then* those two cells show their
  revealed state in the given treatment, and every other cell is undecided.
  (test: `TestSolverGivens_ShowsRevealedCells`)
- **AC-3** (happy, locked): *Given* such a puzzle, *when* the player clicks,
  drags over, Region-drags over, undoes, redoes or Resets a given cell, *then*
  its state never changes. (test: `TestSolverGivens_LockedAgainstEveryAction`)
- **AC-4** (happy, counters): *Given* such a puzzle at load, *when* the
  counters are read, *then* errors are 0 and the percent-correct figure already
  counts the givens as correct. (test: `TestSolverGivens_CountAsCorrectNotAsWork`)
- **AC-5** (happy, solved): *Given* a puzzle with givens, *when* every
  remaining cell is marked correctly, *then* it is solved and the solved
  animation runs. (test: `TestSolverGivens_SolvableToCompletion`)
- **AC-6** (edge, hint): *Given* a puzzle with givens, *when* a hint is asked
  for, *then* the revealed cell is never one of the givens. (test:
  `TestSolverGivens_HintSkipsGivens`)
- **AC-7** (edge, resume): *Given* a stored local board for the same puzzle that
  marks a given cell differently, *when* the page reopens, *then* the given's
  state wins and the rest of the board is restored. (test:
  `TestSolverGivens_ResumeCannotOverrideAGiven`)
- **AC-8** (edge, malformed row): *Given* a row whose givens are the wrong
  shape or contradict its grid, *when* the player page is requested, *then* the
  page reports the broken row (the panel's existing error surface) rather than
  rendering an unsolvable puzzle. (test: `TestSolverGivens_RefusesABrokenRow`)
- **AC-9** (guard, no givens): *Given* any puzzle without givens, *when* the
  player page loads and is played, *then* every existing behaviour — marking,
  undo/redo, errors, percent, hints, resume, zoom, circles — is unchanged.
  (test: the existing `test_puzzle_solver_*.py` suite)

## Guardrails

- G-1: Clues still come from `compute_clues` of the stored grid; the client
  never re-derives them (ADR-0038/R3; test: `TestSolverPage_ShowsTheClues`).
- G-2: Hand-written JS/CSS only, no framework or build step (ADR-0038/R1).
- G-3: The lock lives in the pure state module, not only in event handlers
  (ADR-0038/R4).
- G-4: No request per mark (ADR-0038/R2; test:
  `TestSolverMarking_NoRequestPerMark`).
- G-5: Book assembly still never writes a puzzle's grid, clues, tier or
  strategies — the only new writer of `givens` is generation (ADR-0033/R1).
- G-6: The migration is expand-only and reversible; existing rows are not
  backfilled, and the puzzles table's other columns are untouched.
- G-7: Interactive play stays behind the admin door (CON-015/CON-016, CON-021,
  ADR-0038/R6) — no public surface is added here.
- G-8: Styling from tokens only (test: `test_the_stylesheet_uses_tokens_not_literals` (and, for a rule added by a card, a per-rule check like `test_the_region_toggles_pressed_look_comes_from_tokens`)).

## System contract

_Assembled 2026-10-17 by `system_rules.py --card CARD-216 --root meta/architecture` (58 rules, `card_scope: touches`) for the registry delta of the same day. A projection — fix the source artifact, never this list._

**Carried notes on these rules** (recorded context, not derivable from the registry):

- **INV-002** — CARD-214 adds the "given its givens" clause; that amendment is unrelated to the
  2026-10-17 delta and is still outstanding.

- ADR-0024/R1 — A repaired random-mode grid is accepted only after a fresh solver run on its own re-derived clues reports solution_count exactly 1. The orchestrator never assumes u… (check: test: PropertyTest_Recovery_AcceptedGridsHaveRealVerdictsWithinOneBound)
- ADR-0024/R2 — Repairs and redraws advance the same RetryCounter bounded by MAX_RETRY_ATTEMPTS (30 since ADR-0002/R1; 20 when this rule was written). K, the consecutive-repair lim… (check: test: TestRecovery_RepairAttemptsCountAgainstRetryBound)
- ADR-0024/R3 — A repair flips exactly one filled cell and one empty cell of the parent grid, both inside the witness-disagreement set (falling back to the undecided mask only when… (check: test: TestRecovery_RepairKeepsFilledCountExact)
- ADR-0024/R4 — The repair's pair choice is a deterministic function of the grid and the solver's witnesses — the region's filled and empty cells ranked by (row, column) — and draw… (check: review-lens)
- ADR-0024/R5 — The repair policy (POL-006) fires only for random mode. Library mode recovers by POL-001 redraw and image mode by POL-002 pixel nudge; neither ever repairs. (check: review-lens)
- ADR-0033/R1 — Book assembly references puzzles by id and never changes a puzzle's grid, clues, difficulty tier or strategies; the only puzzle field it may write is the book-membe… (check: review-lens)
- ADR-0038/R1 — The puzzle player's client is hand-written JavaScript and CSS served as static files by the admin panel. There is no front-end framework, no build step, no npm tool… (check: review-lens)
- ADR-0038/R2 — Marking, undo, redo, the error count and the solved check run entirely in the browser. A loaded player page issues no network request per mark. (check: test: TestSolverMarking_NoRequestPerMark)
- ADR-0038/R3 — The player page's clues are embedded as JSON from compute_clues of the stored grid (the one encoder). The client never re-derives clues from the solution. (check: test: TestSolverPage_ShowsTheClues)
- ADR-0038/R4 — The player's state logic (board, strokes, undo/redo history, error count, solved predicate) lives in a pure module with no DOM access, separate from rendering. (check: review-lens)
- ADR-0038/R5 — pyproject.toml package-data for nonogram.admin includes static/*.js alongside templates/*.html and static/*.css, so the player's script ships in every built wheel. (check: review-lens)
- ADR-0038/R6 — Only the admin panel's player, behind the CON-015 / CON-016 door, may ship a puzzle's solution grid to the browser. A public or reader-facing player must not send t… (check: review-lens)
- ADR-0038/R7 — Browser tests use pytest-playwright with Chromium, declared only in a dev-only extra in pyproject.toml. It is never added to project.dependencies or to the admin ex… (check: review-lens)
- ADR-0038/R8 — Browser tests run locally, against Chromium installed by `playwright install chromium`. When Chromium is not installed, browser tests fail or skip loudly, with a na… (check: review-lens)

_44 further rules the lens returned are scoped `src/nonogram/**` (package-wide), so they match every card in the project and narrow to nothing. They are deliberately NOT listed: measured on this board, a ~53-rule contract produced 6-12 real verdict lines out of 53 (CARD-200/203/204), while the 10- and 13-rule contracts of CARD-242/CARD-241 produced 10 and 13 — full coverage. Owner decision 2026-10-17: ship the curated form. The package-wide scoping is the root cause and is recorded in `meta/kanban/backlog.md`._

## Architecture context

- **FR:** FR-044 (the player), FR-011 (export readiness), FR-030 (persisted
  puzzle record).
- **ADR:** ADR-0038/R1–R6, ADR-0033/R1, ADR-0024 (the policy CARD-214 extends).
- **CON:** CON-015, CON-016, CON-021.
- **Components:** COMP-009 (admin panel + player), COMP-010 (persistence),
  `migrations/` (the new column).
- **Trace:** `meta/architecture/trace.yml` — not updated by this card.

## Design context

- **Design system:** `static/tokens.css` + `static/admin.css` (no
  `meta/design/` in this repo); every value is a token
  (`test_the_stylesheet_uses_tokens_not_literals` (and, for a rule added by a card, a per-rule check like `test_the_region_toggles_pressed_look_comes_from_tokens`)).
- **UI components:** `.player-cell` gains a given treatment next to the
  existing `data-state` swatches (filled / empty / maybe / unknown); the white
  given's dot should read like the printed one (CARD-215).
- **Screens:** `/puzzles/<id>/solve`.
- **Standards:** the given treatment must be distinguishable from the player's
  own marks without relying on colour alone, and keep CARD-182's tap targets.

## Worktree notes

**DB-mode tests skip silently.** Without a `nonogram_test` database the
DB-mode tests skip green — use `sqlite_session_scope` for the regression tests
of the new column so they actually run in this environment.

