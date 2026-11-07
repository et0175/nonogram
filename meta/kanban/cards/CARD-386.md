# CARD-386: A preview site built from the admin's own player files, with no overrides, for the owner to test

**Status:** in_progress
**Priority:** P1
**Category:** feature
**Estimate:** 2c (1d)
<!-- Stated in review cycles at DRAFT time. The spike built a throwaway version of this in about an hour; the card makes it a repeatable assembler mode and a served-tree check. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** owner ruling 2026-11-06 after the shared-player spike: "yes to A and don't do differences override level until I test it". This card produces the site the owner tests: the admin's own look and behaviour on the public pages, NO override layer, NOT deployed.
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** CARD-385
**Touches:** player/assemble.py, scripts/assemble_player_site.py, scripts/preview_player_site.py, tests/test_player_shared_ui_site.py
<!-- The assembler and its driver are the only files that change; the live assembly path (the one deployed today) and its tests stay as they are, and the new mode is opt-in (a flag), so a deploy is unaffected until the owner decides. The author derives the exact list and names SCOPE+. -->
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

Step 2 of design A of the spike (`~/Documents/nonogram-reviews/spike-shared-player/REPORT.md`). CARD-385 makes the admin's `solver.js` and `solver_state.js` run with no solution. This card assembles a site that actually uses them: copies of `solver.js`, `admin.css`, `solver_state.js` and `tokens.css`, a thin generated shell reading `puzzle/<key>.json`, and the book landing and library pages as today, so the owner can open `/play/<key>` and judge the admin look and behaviour on the public pages BEFORE deciding which differences (cell-size floor, compact rings, one-row toolbar, Hint and Probe under the board, and so on) are worth an override layer.

## What to implement

1. **A new, opt-in assembler mode** (a flag on `scripts/assemble_player_site.py`, delegating to `player/assemble.py`; the default path is byte-for-byte unchanged) that writes `play/index.html` from the admin's own template or its markup (the spike rendered `puzzle_solve.html` through Jinja with a 9-line base; the assembler is stdlib-only, so either render once at build time in the SCRIPT with Jinja, or move the toolbar markup out as a static fragment: choose, justify, and keep one source of truth for that markup), the admin's `solver.js` and `solver_state.js` and `admin.css` and `tokens.css` as byte-identical copies (extend the byte-identity table and the assembly-time equality check to the two new files), a loader that builds the payload `{id: key, width, height, rows, columns, mode: "public"}` from `puzzle/<key>.json`, and `/b/<slug>`, `/library` unchanged.
2. **Bootstrap for the preview only.** `admin.css` relies on Bootstrap 5.3 (54 `--bs-` references; the admin loads it from a CDN, the public site bans external references). For this PREVIEW, place a copy of Bootstrap's stylesheet in the assembled tree from a path the author names (the spike used `experiment/bootstrap.min.css`); it is NOT committed to the repository in this card and the preview is never deployed. Whether Bootstrap is vendored into the repo or replaced by a small button stylesheet is a separate owner decision touching the dependency baseline (ADR-0006/R1); record it in the closing note.
3. **A served-tree check for the new mode** (reuse the existing served-tree scans): the output contains no solution string, every `puzzle/<key>.json` carries exactly `clues, height, key, tier, width`, no external `http(s)` reference except none, no `fetch`/XHR/`sendBeacon` in the copied JS, the `.player-site` marker, the preview server serves `/play/<key>`, `/b/<slug>` and `/library`, headless Chromium loads a real puzzle with zero page errors and the CARD-385 sweep passes against THIS assembled tree.
4. **Do not delete or edit anything of the current public player.** `play.js`, `player.css`, `play.html` and their tests stay. The owner tests the preview next to the live look.

## Acceptance criteria

* **AC-1** *Given* the new flag and the exported bundle, *then* a site is assembled whose `/play/<key>` page runs the admin's `solver.js` with the admin's `admin.css`, with no override stylesheet, and a real puzzle plays to the solved banner in headless Chromium with zero page errors and zero non-GET requests. (test: `tests/test_player_shared_ui_site.py`, named by the implementation)
* **AC-2** *Given* the assembled tree, *then* the byte-identity table covers `solver.js`, `admin.css`, `solver_state.js` and `tokens.css`, and a plant that edits a copy reds. (test: named by the implementation)
* **AC-3** *Given* the assembled tree, *then* no served file contains a solution string, the puzzle JSON key set is exactly `clues, height, key, tier, width`, and a plant that adds a solution key reds. (test: named by the implementation)
* **AC-4** *Given* the default (no flag), *then* the assembler's output and every existing assembler and public-player test are unchanged. (test: the existing modules, node ids compared)
* **AC-5** *Given* the preview, *then* the QR landing and library pages still work and the URLs keep their shapes (`/play/<key>`, `/b/<slug>`, `/library`). (test: named by the implementation)
* **AC-6** *Given* the preview folder, *then* the author renders it at 390 and 1280 px next to the live look (the current `player.css` page) for the owner to compare, in `~/Documents/nonogram-reviews/CARD-386/`, and lists in the report the visible differences it finds (no fix, no override). (check: review-lens, a report not a test)

## Guardrails

* **G-1** No override layer: no stylesheet that changes `admin.css`'s look, and no edit to the admin files.
* **G-2** Not deployed, and no change to the live assembly path or to `docs/deploy/player.md` beyond a note that the preview mode exists.
* **G-3** Bootstrap is not committed to the repo here.
* **G-4** No test deleted, renamed, skipped or merged; node-id set difference; controls that can fail; the full suite is the merge gate.

## System contract

* ADR-0041/R2 — no public asset carries a solution (check: AC-3 and CARD-385's sweep)
* ADR-0041/R3 — byte-identical build-time copies (check: AC-2)
* ADR-0006/R1 — dependency baseline closed (check: review-lens: Bootstrap stays out of the repo)


## Carried from CARD-385's review (2026-11-07), for this card's author

* **F-2** In public mode the admin template's usage paragraph `#puzzle-player-hint` still says "...the third reveals it; Check highlights the row of the first wrong mark..." and is visible; Check does not exist there. This card's assembled page must show a usage line that is true for the public player (the sentence is the owner's call; the author proposes one and says so).
* **F-3** is fixed in CARD-385's fix round (Hint stays enabled where no line decides and says the clues decide nothing more); verify it on the assembled page.
* The solved banner's picture name is blank in CARD-385's test shell: the real shell must provide the puzzle's public title (never `source_image`; `player_bundle` already falls back to a neutral title).
* Old public saves (`nonogram-public:<key>`) are never read under the admin's key `nonogram-player:<id>`: the preview starts every visitor fresh; the owner decides at deploy whether a migration is worth it.

## Worktree notes

Author round 1 (branch card/386-shared-ui-preview-site, 2026-11-07).

* Markup source (item 1 choice): the DRIVER renders the admin's own `puzzle_solve.html` with Jinja (base replaced by a bare content block) and hands the HTML to `player/assemble.py` in memory (`main(argv, shared_ui_fragment=...)`; `assemble(shared_ui=SharedUi(fragment, bootstrap))`). One source of markup (the admin's), the assembler stays stdlib-only, and the driver still writes no file (the existing `test_the_assembly_helper_drives_the_assembler_and_writes_nothing_itself` forbids it, so a temp file was not an option). Per-puzzle holes (header size, tier chip, banner name, tab title) are filled by the shell's loader from `puzzle/<key>.json`; the tier hue is `var(--color-tier-*)` from tokens.css.
* F-2: the usage paragraph's Check clause is replaced at assembly time; the assembler REFUSES a fragment where the clause (or any loader hook) is not found exactly once. Proposed sentence (owner's call): "... the third reveals it, and each press writes its answer in the line beside the puzzle's title."
* Banner name: a puzzle's title is in no served schema (EC-048), so the banner reads "Solved: Puzzle <key>" (player_bundle's neutral stand-in), never source_image.
* Old `nonogram-public:<key>` saves are not read (tested): the preview starts every visitor fresh.
* Finding: CARD-385's sweep boards (10x8, 7x6) are below `limits.MIN_SIZE`, so the real assembler refuses to serve them; this card's tests use 10x10 equivalents (seeds 1/0.6 and 3095/0.4, properties re-asserted), and its sweep reuses CARD-385's steps with the Hint step's press bound (3*90) scaled to 3*cells.
* Finding for the Bootstrap decision (G-3, item 2): the real Bootstrap 5.3 file (spike copy) passes the CARD-385 sweep and all AC-1/AC-5 tests here, but fails AC-392's `scan_site`: 3 foreign (the w3.org SVG namespace in its data-URIs and two licence-comment URLs) and 2 unclassifiable data-URI fragments. Vendoring it needs either a scan allowance or a stripped build. Tests use a one-rule stand-in. The scan also lists solver.js's relative `import './solver_state.js'` as unclassifiable; the test pins that one line as the only residue.
* Not touched: vercel.json, library/book pages, player.css, play.html, play.js, the default tree (byte-identical; tested). The preview tree keeps vercel.json's three rewrites unchanged.

