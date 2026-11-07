# CARD-386: A preview site built from the admin's own player files, with no overrides, for the owner to test

**Status:** done
**Priority:** P1
**Category:** feature
**Estimate:** 2c (1d)
<!-- Stated in review cycles at DRAFT time. The spike built a throwaway version of this in about an hour; the card makes it a repeatable assembler mode and a served-tree check. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/386-shared-ui-preview-site
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-386
**Source:** owner ruling 2026-11-06 after the shared-player spike: "yes to A and don't do differences override level until I test it". This card produces the site the owner tests: the admin's own look and behaviour on the public pages, NO override layer, NOT deployed.
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** CARD-385
**Touches:** player/assemble.py, scripts/assemble_player_site.py, scripts/preview_player_site.py, tests/test_player_shared_ui_site.py
<!-- The assembler and its driver are the only files that change; the live assembly path (the one deployed today) and its tests stay as they are, and the new mode is opt-in (a flag), so a deploy is unaffected until the owner decides. The author derives the exact list and names SCOPE+. -->
**Review score:** 8.5 (cycle 1/3 - CERTIFIED; fix round 075bffee not re-reviewed)
**Started:** 2026-11-07T08:00Z
**Closed:** 2026-11-07T11:25Z
**Actual:** —
**Merge commit:** 381c9a3b239fc971e68098453d25a5c9a6789582
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
* F-2: the usage paragraph's Check clause is replaced at assembly time; the assembler REFUSES a fragment where the clause (or any loader hook) is not found exactly once. Sentence (owner ruling 2026-11-07, review F-1; "beside the puzzle's title" was false on phones): "... the third reveals it, and each press writes its answer in the line at the top of the page." The tests measure the line's rectangle against the toolbar at 390 and 1280 px, and a plant of the old wording reds at 390.
* Banner name: a puzzle's title is in no served schema (EC-048), so the banner reads "Solved: Puzzle <key>" (player_bundle's neutral stand-in), never source_image.
* Old `nonogram-public:<key>` saves are not read (tested): the preview starts every visitor fresh.
* Finding: CARD-385's sweep boards (10x8, 7x6) are below `limits.MIN_SIZE`, so the real assembler refuses to serve them; this card's tests use 10x10 equivalents (seeds 1/0.6 and 3095/0.4, properties re-asserted), and its sweep reuses CARD-385's steps with the Hint step's press bound (3*90) scaled to 3*cells.
* Finding for the Bootstrap decision (G-3, item 2): the real Bootstrap 5.3 file (spike copy) passes the CARD-385 sweep and all AC-1/AC-5 tests here, but fails AC-392's `scan_site`: 3 foreign (the w3.org SVG namespace in its data-URIs and two licence-comment URLs) and 2 unclassifiable data-URI fragments. Vendoring it needs either a scan allowance or a stripped build. Tests use a one-rule stand-in. The scan also lists solver.js's relative `import './solver_state.js'` as unclassifiable; the test pins that one line as the only residue.
* Not touched: vercel.json, library/book pages, player.css, play.html, play.js, the default tree (byte-identical; tested). The preview tree keeps vercel.json's three rewrites unchanged.

Fix round 1 (review cycle 1: 8.5, 0 blockers).

* F-1 fixed: replacement sentence changed (see F-2 note above); the old tail is part of the refused-unless-found-once clause; tests: `test_the_line_the_usage_text_names_is_where_it_says_at_both_widths` (390 and 1280, from the DOM) and `test_the_old_wording_is_false_on_a_phone_and_the_check_sees_it`.
* F-2 (low) fixed: the fallback paragraph now says "(solver.js) did not load, or JavaScript is off."; the header reads "Puzzle" until the loader fills it; the tier chip starts hidden (it showed the template's placeholder "tier"); test `test_a_bad_address_shows_no_placeholder_header_chip_or_false_fallback`.
* F-6 (info): `scripts/preview_player_site.py` is UNCHANGED by this card (the diff against main is empty), so it was claimed in Touches without being touched; the card header is not edited.
* CARRIED, not fixed: F-4 - `tests/test_player_shared_ui_site.py` holds a fork of CARD-385's `step_hint` with the press bound scaled to 3*cells; an edit to CARD-385's `step_hint` will not reach the copy. A one-line follow-up in `tests/test_player_public_mode.py` deriving the bound from the grid would delete the fork.
* CARRIED: F-3 - the tests run on a one-rule Bootstrap stand-in; the owner sees the real Bootstrap, and 14 of 22 sampled rectangles differ at 1280 px (reviewer's measure), inherent to G-3. Real Bootstrap was run once by hand through the sweep and the page/landing tests (15 passed) and fails the AC-392 scan (see above).
* CARRIED: F-7 - the preview was never assembled or tested with `--analytics`.
* Owner ruling 2026-11-07: Bootstrap long-term is a small project stylesheet in a separate follow-up card (the orchestrator cuts it); this card keeps `--bootstrap` taking the real file at build time, never committed.

[Review 1/3] Score: 8.5 (threshold 8.0 reached; 0 blockers; PASS; certified). Reviewer-reported, not re-run by the merge gate; the gate was handed only the figure, the verdict and the carried findings (F-3, F-4, F-7 below; F-1, F-2 and F-6 are the items the fix round's notes above name as fixed), not the review file, so no further detail is restated here. The fix round 075bffee was NOT re-reviewed.

[Closing note, merge gate, merged `381c9a3b` (tip `075bffee`, main merged into the branch first as `e88a3ee1` with no conflict; staged `--no-ff` merge into main, parents `1dc46b31` and `e88a3ee1`)] What the merge delivers: an OPT-IN shared-UI preview mode in `player/assemble.py` and `scripts/assemble_player_site.py`, which assembles a site from the admin's own player files (the admin's `puzzle_solve.html` markup, `solver.js`, `solver_state.js`, `admin.css`, no override layer). The default/live assembly path is byte-identical (tested). NOT deployed; nothing to deploy. How the owner builds and tests it: the driver flags `--shared-ui` and `--bootstrap <the real Bootstrap file>` (taken at build time, never committed); renders are in `~/Documents/nonogram-reviews/CARD-386/` (preview-site, live-site, and the before/after 390 and 1280 px pages). Gate figures derived in this run: fast sanity first (admin_binding, suite_profile, check_ref_resolution, guard_integrity, collected_names, cli, kanban_review_record, player_shared_ui_site) 979 passed, 9 skipped (no DATABASE_URL); then the full ARMED suite from the main tree with the merge staged: 11483 passed, 1 skipped, 1 xfailed, 0 failed, 0 errors in 3449.46s; the one skip is the setrlimit platform gate; staged tree c17d68c0 == tree after the suite == committed tree; no hang-guard override (default 300 s); the full-suite lock was written and released by this gate, unchanged throughout. Accuracy: 1 distinct review ordinal over the Estimate's 2c = 1 / 2 = 0.500 review cycles per estimated cycle (wall-clock Actual not used, owner ruling). Size datum: `git diff --shortstat 1dc46b31 e88a3ee1` (merge-base after main was merged in, against the branch tip) = 5 files changed, 1280 insertions(+), 8 deletions(-) (player/assemble.py, scripts/assemble_player_site.py, tests/test_player_shared_ui_site.py new, docs/deploy/player.md, this card).

CARRIED (no new cards): F-3 the tests run on a one-rule Bootstrap stand-in; with the real file 14 of 22 sampled rectangles differ at 1280 px, inherent to G-3. F-4 `tests/test_player_shared_ui_site.py` holds a fork of CARD-385's `step_hint` with a 3*cells bound; a one-line follow-up in `tests/test_player_public_mode.py` deriving the bound from the grid would delete it (below the cut bar). F-7 never run the preview with `--analytics`.

OWNER items still open: (a) whether old `nonogram-public:<key>` saves should be migrated at deploy (they are not read; visitors start fresh); (b) whether the solved banner should read "Solved!" without the key (it reads "Solved: Puzzle <key>" now). The Bootstrap long-term decision moved to CARD-394 (a small repo-owned stylesheet replaces Bootstrap on the public player); this card keeps `--bootstrap` taking the real file at build time.
