# Nonogram Generator — Requirements

## 1. Overview

A small tool that generates nonogram (picross) puzzles either **from an idea**
(a random or library picture) or **from a user-supplied image**, at a
**user-selected difficulty**, guaranteeing the result is a valid, uniquely
solvable puzzle.

Source material: `docs/monogram.md` (original idea notes) and
`docs/monogram_idea` (flow diagram). This document consolidates both into a
single spec and calls out gaps that need a decision before implementation.

## 2. Goals

- Produce nonograms that are **always solvable by logic** (no guessing) and
  have **exactly one solution**.
- Support two generation modes: **random/idea-based** and **image-based**.
- Let the user pick a **difficulty level** and a **grid size**.
- Export the puzzle in formats usable for printing and for other apps.
- Ship as a **CLI tool**: the user configures mode/size/difficulty and gets
  files written to disk. No web/GUI in v1.

## 3. Pipeline (from the diagram)

1. **Obtain a solution grid** — either generate one at random, pick one from a
   built-in image library (cat, house, heart, moon, …), or convert a
   user-uploaded image to a black/white pixel grid.
2. **Compute row and column clues** from the grid (run-length encoding of
   filled cells per row/column, e.g. `██·███··` → `2 3`).
3. **Build the puzzle** — the clues plus grid dimensions; the solution grid is
   hidden from the player.
4. **Solve programmatically** using constraint propagation + backtracking to
   enumerate solutions.
5. **Check solution count**:
   - exactly 1 → valid, keep it.
   - 0 → impossible, discard and regenerate.
   - \>1 → ambiguous, discard/regenerate or adjust the grid.
6. **Score difficulty** (optional but requested) using solver-derived signals
   and filter/regenerate until it matches the requested level.

## 4. Functional Requirements

### 4.1 Grid generation

- FR-1: Generate a random black/white grid at a configurable size, supporting
  **10×10 up to 50×50**.
- FR-2: Generate a grid from a built-in image library (e.g., cat, house,
  heart, moon).
- FR-3: Generate a grid from a user-uploaded image, converted to black/white
  pixels at the target puzzle resolution.
- FR-4: Support configuring grid density (approximate % of filled cells) for
  random generation.

### 4.2 Clue computation

- FR-5: Compute row clues and column clues from any solution grid via
  run-length encoding of contiguous filled runs.

### 4.3 Uniqueness / solvability

- FR-6: Implement a nonogram solver (constraint propagation + backtracking)
  that, given row/column clues, determines the number of valid solutions
  (0, 1, or many) without necessarily enumerating all of them exhaustively
  when the count exceeds 1 (fail fast once a second distinct solution is
  found).
- FR-7: If solution count ≠ 1, discard the candidate grid and regenerate
  (for random/idea mode) or reject with a clear error (for image mode, since
  the input image is fixed and can't be silently regenerated).
- FR-8: Puzzles must be solvable using pure logical deduction reachable by the
  solver's technique set — i.e., no puzzle should be accepted that requires
  the solver to fall back on backtracking/guessing to reach the unique
  solution, if a "no-guessing" guarantee is required for the selected
  difficulty (see 4.4).

### 4.4 Difficulty control

- FR-9: Expose a difficulty selector (e.g., Easy / Medium / Hard).
- FR-10: Estimate difficulty via a **heuristic score**: combine solver-derived
  signals into a single numeric score, then bucket into Easy/Medium/Hard by
  threshold ranges (tunable later without changing the solver). Signals to
  combine:
  - number of cells solvable by initial (line-only) logic before any
    backtracking is needed,
  - amount of backtracking/search required,
  - solver time,
  - puzzle size and clue density.
- FR-11: Regenerate or resample candidates until the produced puzzle's
  estimated score falls within the requested level's threshold range.

### 4.5 Export

- FR-12: Export the puzzle (clues + blank grid) as PNG and/or SVG, suitable
  for printing.
- FR-13: Export the underlying solution grid and clues as JSON and/or CSV.
- FR-14: **Out of scope for v1.** No playable/interactive puzzle output
  (web or mobile). Only the static exports in FR-12/FR-13. Revisit as a
  future idea if a UI is ever added.

### 4.6 Image-to-nonogram conversion

- FR-15: Accept a user-supplied raster image and convert it to a black/white
  grid at the requested puzzle dimensions using: downscale to target grid
  size, then **error-diffusion dithering** (e.g. Floyd–Steinberg) before
  binarizing each cell. Chosen over a flat brightness threshold to better
  preserve shading/gradients at small grid sizes.
- FR-16: After conversion, run the same uniqueness check (4.3). If the
  converted image does not yield a unique solution:
  1. Attempt automatic recovery by nudging a small, bounded number of cells
     (e.g. flip pixels near ambiguous regions) and re-checking, up to a
     capped number of attempts.
  2. If still not unique after the capped attempts, report failure to the
     user (do not silently keep altering the image beyond that cap) and let
     them retry with a different image or size.

## 5. Non-Functional Requirements

- NFR-1: Puzzle generation (including regenerate-on-failure loops) should
  complete in a reasonable interactive time for supported sizes (e.g., up to
  20×20 within a few seconds on typical hardware); larger sizes may be
  slower but should have a sane upper bound or timeout with a clear failure
  message.
- NFR-2: The regenerate loop (4.3/4.4) must have a maximum retry/iteration
  bound to avoid infinite loops when a request is infeasible (e.g., an
  overly dense random grid, or a difficulty level unreachable at the chosen
  size).
- NFR-3: Solver correctness is critical — an accepted puzzle must never
  actually have 0 or >1 solutions; false positives in the uniqueness check
  undermine the whole point of the tool.
- NFR-4: Exported files (PNG/SVG/JSON/CSV) must round-trip: the JSON/CSV
  representation must be sufficient to reconstruct the exact grid and clues.

## 6. Non-Goals / Out of Scope (unless later requested)

- Multiplayer, accounts, or persistence beyond local file export.
- Color/multi-value nonograms (this spec assumes classic black/white only).
- A full interactive solving UI — noted as optional/open in FR-14.

## 7. Decisions Log

All open questions from the initial review have been resolved:

| # | Question | Decision |
|---|----------|----------|
| 1 | Interactive puzzle output | Out of scope for v1 (FR-14) |
| 2 | Difficulty algorithm precision | Heuristic score/threshold, not technique-tier classification (FR-10/11) |
| 3 | Image conversion method | Resize + error-diffusion dithering (FR-15) |
| 4 | Regenerate-on-failure for image mode | Auto-adjust (bounded pixel nudges) first, then report failure (FR-16) |
| 5 | Target interface | CLI tool (Section 2, replaces `main.py` boilerplate) |
| 6 | Grid size limits | 10×10 to 50×50 (FR-1) |

## 8. Notes from Review

- The two source materials (`monogram.md` and the diagram image) are
  consistent on the core pipeline; the diagram adds detail the text doesn't
  cover: a built-in image library, adjustable density, difficulty as a
  visualized gradient, and "interactive puzzle" as an output format. These
  are folded into this document as FR-2, FR-4, and FR-14 respectively.
- Choosing a heuristic difficulty score (Decision 2) over technique-tier
  classification means FR-8's "no-guessing" guarantee is *not* strictly
  enforced by construction — it's an emergent property of the score
  thresholds. If a puzzle absolutely must never require backtracking to
  solve at "Easy," revisit FR-8 to add a hard technique-based gate on top of
  the score for that tier specifically.
- Auto-adjusting a user's uploaded image (Decision 4) means the exported
  puzzle's solution grid can differ slightly from their original picture.
  Worth surfacing to the user at export time (e.g., a diff count or
  preview) so it's not a silent surprise — not yet captured as a numbered
  requirement; add one before implementation if this matters.