# CARD-419: A site-wide, interactive "How to solve" page: a five-step wizard with a guided puzzle and a probe demo

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 2c (1d)
<!-- Basis: one new static page and its script, one row in assemble.py's served-files table and one rewrite in vercel.json; the content exists (docs/guides/how-to-solve-nonograms.md, the book's guide spread). The cost is the two interactive boards and their tests. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** owner request 2026-11-10 (project thread "Design the book QR landing page"): "we need How to solve page… make it interactive?", "if we'll have more books, then how to solve should be generic", "I'm fine with question marks", "add a contradiction-probing part, look how it's done with the player", "make it as wizard steps".
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** CARD-268, CARD-339
<!-- CARD-268 (done) is the player's Probe / Keep / Contradiction transaction this page teaches; CARD-339 (done) is the "?" mark. CARD-418's landing links here. -->
**Touches:** player/how-to-solve.html (new), player/how-to-solve.js (new), player/player.css, player/assemble.py, player/vercel.json, player/library.html, tests/test_public_player_pages.py, meta/architecture/requirements.yml, docs/how-it-works/01-domain/puzzle-creation/11-the-public-player.md
<!-- A starting point, not the boundary: grep the whole tests tree for PLAYER_FILES, the vercel rewrites and the published-pages census (the analytics snippet counts every published .html). -->
**Review score:** — (no review cycle; merged on the owner's request)
**Started:** 2026-11-10T10:30Z
**Closed:** 2026-11-10T11:41Z
**Actual:** about 30 min (CARD-419) of one owner session
**Merge commit:** 871ec258
**Blocked by:** —

## Why this card exists

A reader who scans the book's QR code and has never solved a nonogram has nowhere on the site to learn how. The printed book has a guide spread (pages 2-3), and `docs/guides/how-to-solve-nonograms.md` has the reader-facing text of the three techniques, but the site has no page for either. The owner wants one page for **the whole site**, not one per book, because more books are planned, and wants it interactive, built as a step-by-step wizard.

The design of record is the canvas "Book QR landing page" (https://claude.ai/artifact/7nXaVdkyQ8raJNZ2bPV1fk), board "How to solve (wizard, 5 steps)".

## What to implement

1. **The page.** `/how-to-solve`, a static page in `player/`, served through `assemble.py`'s files table with a `vercel.json` rewrite like `/library`. **It names no book.** The top link and the last step's button say "Back to your puzzles": back to the `/b/<slug>` page the reader came from when there is one (the referring path, never a stored value), otherwise `/library`.
2. **A wizard of five steps,** one screen each, with a progress bar of five segments at the top ("Step 2 of 5 · Squeeze from both ends"), each segment a button that jumps to its step, and Back / "Next: <name>" at the bottom. The step is kept in the URL fragment (`#2`), so the browser's Back button works and a step can be linked to.
   1. **The rules + "Try one".** The clue rule in two sentences, then a guided 5×5 (the tree: rows 1 3 5 1 3, columns 1 / 2 1 / 5 / 2 1 / 1) with the player's three marks: **Black, White (the grey dot) and Maybe ("?")**, named and drawn as in the player. Five guided steps light the line(s) each step is about; "Show me" does the step; solving it shows "You solved it: a little tree."
   2. **Squeeze from both ends.** The row-of-10, clue-8 picture: "Pushed left" and "Pushed right" rows drawn as **"?"** squares (the player's Maybe), the overlap black.
   3. **What every arrangement agrees on.** The text from the guide (crosses become "white squares"). Optional: a small picture of the arrangements of "3 2" with one known white square, if it fits the step.
   4. **Probe, and watch it break.** The text names the player's own buttons (Probe, Keep, Contradiction), then a demo built the way the player does it (CARD-268): Probe opens a transaction; every mark made while it is open gets the player's dashed amber edge (`--player-probe`, `--player-probe-ink`); Contradiction takes them all back; Keep keeps them. The demo grid is a real 5×5 that line logic leaves with 8 open squares: solution `#.#.# / ..... / #...# / #..## / .###.`, rows 1 1 1 / 0 / 1 1 / 1 2 / 3, columns 1 2 / 1 / 1 1 / 2 / 1 2. Probing row 3, column 2 black forces row 5 col 2 white, row 3 col 1 white, row 5 cols 3-5 black, and column 1 ("1 2") has no room left: contradiction. That square is then white, and line logic finishes the puzzle.
   5. **The levels and the promise.** What Easy, Medium and Hard need, in the guide's wording (Medium may already need step 4 for part of the grid, CARD-137's cutoff), then "Every puzzle here has exactly one solution. You never have to guess, and there is never a second answer.", then "Back to your puzzles".
3. **Links in.** CARD-418's landing footer; the library page gets the same link. Linking it from the player's "How to play" line (CARD-413) is the player thread's call, not this card's.
4. **No storage.** The page keeps nothing between visits: the boards reset on reload.

## Acceptance criteria

(The ids below are local labels; the registry ids are assigned at dispatch.)

- **AC-A** (the two boards are true puzzles): the "Try one" grid and the probe grid each have exactly one solution, checked against the independent brute-force oracle (`tests/helpers/brute_force_oracle.py`), and the probe grid's line-logic fixpoint leaves exactly the 8 squares the text says, with the probe square leading to a line that cannot fit. The page's clue numbers are derived from the grids in the test, never typed twice. (control: changing one cell of either grid reds it.)
- **AC-B** (the wizard): every step is reachable by Next, by its progress segment and by `#n` in the URL; Back on step 1 is absent; the last step's button goes to the referring `/b/<slug>` and to `/library` with no referrer.
- **AC-C** (the guided board): Black, White and Maybe each set the tapped square to that mark, tapping again with the same mark clears it, "Show me" completes the current step, and the solved message appears exactly when the board matches the solution.
- **AC-D** (the probe demo): marks made after Probe carry the dashed edge; Contradiction removes every one of them and leaves the probe square white; Keep at the contradiction explains why it cannot be right; the finish fills the solution.
- **AC-E** (generic): the page's served text names no book, series or author, and the assembled site serves it at `/how-to-solve` for a site with any number of books, including none.
- **AC-F** (layout): at 390 px each step fits without horizontal scroll, every control is at least 44 px with a visible focus, and the boards' squares are real buttons with names ("Row 3, column 2, black"). (check: Playwright screenshots of each step at 390 and 1280 for the owner's eye.)

## Guardrails

- **G-1** Static only: no fetch, no storage, no analytics beyond the one counting snippet every published page already carries (CARD-285).
- **G-2** The marks, their names and the probe's edge colours are the player's: read them from the player's CSS tokens, not new colours, so the page and the player cannot drift. If the player changes them (another thread owns the player), this page follows.
- **G-3** The text follows `docs/guides/how-to-solve-nonograms.md`; if the page's wording diverges, update the guide in the same commit or say why not.
- **G-4** Add tests for the new page; one control per AC that can fail; report the net test count.

## Architecture context

- **FR:** FR-045 (the public player site). **Components:** COMP-011, `player/assemble.py` (served files and rewrites).
- **Decisions this follows:** CARD-268 (the probe as a transaction, dashed edge), CARD-339 (the "?" mark), CARD-137 (the Medium/Hard cutoff the levels step describes), the book guide spread's wording.

## Worktree notes

- Built in the cloud thread "Design the book QR landing page" on branch book-landing-how-to-solve (commit 371a363a), merged to main as 871ec258 on the owner's "merge please".
- player/how-to-solve.html + how-to-solve.js, served at /how-to-solve (assemble.PLAYER_FILES row, vercel.json rewrite, docs/deploy/player.md `lesson` URL shape). Five steps chosen by the URL hash (#1..#5); "Back to your puzzles" returns to a same-site referrer, else /library.
- Step 3's guided 5x5 uses "?" for Maybe like the player; step 4's probe demo mirrors the player's Probe / Contradiction / Keep with the same probe colours (--hts-probe / --hts-probe-ink use admin.css's expressions).
- SVG is never built with the SVG namespace URL (the served-JS foreign-URL scan flags it); no colour literals in player files.
- Tests: tests/test_how_to_solve_page.py (9, browser).
- Left open (not done here): requirements.yml AC registry rows for the page.
