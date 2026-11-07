# CARD-399: Retire the separate public play.js implementation and its tests — the shared-UI mode becomes the default, and a test stays only if its claim is a live decision

**Status:** ready
**Priority:** P2
**Category:** ops
**Estimate:** 8c (2.5d)
<!-- Over the 3c target on purpose and said so: the default switch and the deletion are small; the cost is the CLAIM AUDIT of about 350 feature tests (probe 57, hint 70, zoom 39, circles 31, crosshair 39, maybe 15, agreement 98 test functions, 1,000 or so collected node ids once parametrised) where every retirement needs a named survivor with a plant. If the first cycle shows it does not fit, the split is: (a) the audit table only, as a committed document with every node id classified and the survivors verified, no deletion (reviewable on its own), then (b) the default switch, the deletions and the retirements by that table. (b) must not start before the owner's go. -->
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** owner statement 2026-11-07: for the public player they "stopped the implementation of those features and just copy them" (design A: the public pages run the admin's own solver.js, solver_state.js, admin.css and tokens.css; CARD-385 done, CARD-386 done, CARD-394 ready), therefore "why not delete the tests" of the separate play.js implementation. The owner's standing rule for tests: a test is kept only if its claim is a live decision. This card also retires CARD-384 (parked: the crosshair colour and cell-size alignment of the OLD play.js has no subject once play.js is gone).
**Idea:** —
**Wave:** —
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** CARD-394, the owner's go after testing the shared-UI preview, and a deploy of the shared-UI mode to production
<!-- NOT dispatchable until all three hold. Production (deployment nonogram-studio-qu83cb3hw) still serves play.js today and must not be left untested while it does: the owner rules WHEN the shared-UI mode is deployed; this card's step 2 (deleting play.js) runs only after that deploy has been observed working. The audit (step 1) may run earlier because it deletes nothing. -->
**Touches:** player/play.js, player/player.css, player/play.html, player/assemble.py, scripts/assemble_player_site.py, tests/test_public_player_probe.py, tests/test_public_player_hint.py, tests/test_public_player_zoom.py, tests/test_public_player_circles.py, tests/test_public_player_crosshair.py, tests/test_public_player_maybe.py, tests/test_public_player_agreement.py, tests/test_public_player.py, tests/test_public_player_pages.py, tests/test_player_public_mode.py, tests/test_player_shared_ui_site.py, tests/test_player_bundle.py, docs/deploy/player.md, meta/kanban/cards/CARD-384.md, meta/profiling/card-399-claim-audit.md
<!-- Derived; the author re-derives from the tree after CARD-394 merges. Conflict edges: CARD-394 (assemble.py, tests/test_player_shared_ui_site.py, docs/deploy/player.md) must be merged first; CARD-389 (docs/deploy/player.md, test_player_bundle.py) is in its gate and must merge first; CARD-395's marker registry must not name any file this card deletes (it does not: the public-player family is deliberately outside it). -->
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

Since CARD-385/386 the admin's `solver.js` can run with no solution (public mode) and the assembler can build a preview site that serves the admin's own player files on the public pages. Once that mode is the production default, the public page's features (zoom, crosshair, circles, hint, probe, maybe) are the ADMIN solver's features, already tested against `solver.js` by the admin family (`tests/test_puzzle_solver_zoom.py`, `_probe`, `_hint`, `_fifth_rule`, `_maybe`, `_marking`, `_brush_menu`, `_crosshair`, ...). The separate tests of `player/play.js` then prove claims about a file nobody ships. They are also the single largest block of the gate: measured on the CARD-388 gate run (contended, summed seconds), the seven feature files are 917.1 s, 19.9 % of the suite, and `test_public_player_agreement.py` (the CARD-328 duplicate-look guard, 98 tests) has no subject at all once there is one implementation.

The measured block, by file (summed seconds, tests collected): probe 495.2 (101), hint 201.5 (175), zoom 126.9 (39), circles 61.7 (86), crosshair 24.5 (70), agreement 3.7, maybe 3.6 = **917.1 s**; kept or decided per node id: `test_player_public_mode.py` 313.5 s (240.1 s of it are 27 mutant arms), `test_public_player_pages.py` 11.5, `test_public_player.py` 8.3, `test_player_shared_ui_site.py` 28.0, `test_player_bundle.py` 8.6.

## What to implement

1. **The claim audit (before any deletion).** For EVERY collected node id of the seven feature files and of every test in `test_public_player.py`, `test_public_player_pages.py` and `test_player_public_mode.py` that names `play.js`, `player.css` or `play.html`, write one row in `meta/profiling/card-399-claim-audit.md`: the node id, its claim (from the AC in its docstring), and exactly one of:
   * **RETIRE-TWIN**: the claim also holds of `solver.js` on the shared-UI page and a named SURVIVOR proves it. The survivor must (a) exist (resolved by `ast`, not by text search), (b) pass on the shared-UI tree, (c) carry a plant that reds it when the claim is broken (the plant run and its red result are recorded in the row).
   * **RETIRE-MOOT**: the claim is about play.js's own structure or about the duplication itself (all of `test_public_player_agreement.py`, the CARD-328 "looks held to the admin's" guard, CARD-384's alignment): no subject remains. The row says which file made the claim true and that it is deleted.
   * **KEEP-LIVE**: the claim is a live decision about the public site, not about the implementation (see the keep list below).
   * **CONVERT**: a live claim stated against play.js that the shared-UI page also owes; the test is re-pointed at the shared-UI tree and kept.
   * **LOST**: a claim with NO admin twin and not live. Reported to the owner in the card, NOT deleted until the owner rules (the list is expected to be short; the public page's narrow-phone layout under the sentence-below-the-board and 1-px width sweeps of `test_public_player_probe.py` / `_hint.py` are the likely members, because the admin page has a different layout: that is exactly what the audit is for).
2. **Switch and delete.** The shared-UI mode of CARD-386 becomes the default assembly output; the byte-identical-copy rule (ADR-0041/R3) is unchanged and extended to the files now copied; `player/play.js`, `player/player.css`, `player/play.html` and the assembly code that only served them (`PLAYER_FILES` entries, the old `play_page` path, the CLI flag that selected the opt-in mode) are deleted. `player/pages.js`, `book.html`, `library.html`, `vercel.json` stay unless the audit shows otherwise. Production is deployed with the new default by the OWNER's decision first; this step is merged only after that deploy is observed.
3. **Retire by the table.** Delete exactly the rows classified RETIRE-TWIN / RETIRE-MOOT, convert the CONVERT rows, leave KEEP-LIVE and LOST. `CARD-384` is closed as moot with a one-line note (this card retires it).
4. **Docs.** `docs/deploy/player.md` and the how-it-works player page say the public site runs the admin's own player files and name the one implementation.

### The keep list (live decisions; these MUST survive, each with its plant)

* ADR-0041/R2: no solution in any served file in any encoding (`test_player_public_mode.py` and the served-tree scan in `test_player_shared_ui_site.py`); the sealed solution getter of the public mode.
* ADR-0041/R3: byte-identity of every copied file (`solver.js`, `solver_state.js`, `admin.css`, `tokens.css` and any new copy).
* ADR-0041/R4: progress in localStorage only, no network write.
* Routes `/play/<key>`, `/b/<slug>`, `/library` with the 404 control; the key set of the served puzzle JSON; the landing address computed once (CARD-389).
* The 27 mutant arms of `test_player_public_mode.py` that retarget today at play.js text: each is audited like any other row (a mutant of a file that no longer ships is RETIRE-MOOT, its twin is the arm that mutates `solver.js`'s public-mode path, which CARD-385 owns); arms of live claims stay.

## Acceptance criteria

* **AC-1** (every claim classified, none dropped silently): the audit table lists every collected node id of the audited files exactly once with exactly one class; the set of node ids in the table equals the set collected at the audit's commit (derived, not counted); an unclassified id, a duplicate or an id not collected reds. (test: new `tests/test_public_player_retirement_audit.py` reading the table; plants: delete a row, add a ghost row.)
* **AC-2** (every retirement has a living survivor with a plant): for each RETIRE-TWIN row the survivor named exists once by `ast`, is collected, and its plant file/mutation is recorded with its red result; a row naming a survivor that is itself retired reds. (test: same module; plant: a row pointing at a deleted test.)
* **AC-3** (the live public claims survive): the keep-list node ids are collected after the retirement and green; each keep-list claim still reds under its plant (R2: a solution key added to a served file; R3: one byte changed in a copy; R4: a `fetch` added; 404 control; key-set drift). (test: the existing live tests plus the plants re-run; evidence in Worktree notes.)
* **AC-4** (the default is the shared-UI mode and the deleted files are gone): the assembled default tree contains no `play.js`, `player.css` or `play.html`, links the admin's own files, and passes the CARD-386 served-tree scan; `git ls-files player/` has none of the three; no source or test names them. (test: `tests/test_player_shared_ui_site.py` cells re-pointed; a grep-style census cell reading `git ls-files`.)
* **AC-5** (LOST claims go to the owner): the card lists each LOST claim with the evidence that no twin exists; none is deleted without the owner's ruling recorded in Worktree notes. (evidence: review-lens; the audit table's LOST rows are exactly the not-deleted ones, asserted by AC-1's module.)
* **AC-6** (measured gate saving): from a solo `--durations` run before and after, the seconds removed per audited file are stated by script (not hand-summed) and compared with the 917.1 s planning figure from the contended run; the net node-id removals equal the RETIRE rows (set difference both ways).
* **AC-7** (no coverage moves silently): every removed node id is in the audit table as RETIRE; no other node id is removed, skipped or xfailed; corpus floors in surviving tests are unchanged (CARD-220 AC-4 collector).

## Guardrails

* **G-1** Nothing is deleted before the owner's go, the deploy and CARD-394.
* **G-2** The R2 / R3 / R4 live claims and their plants are untouchable; if the audit cannot name a plant for a keep-list claim, the claim is reported, not retired.
* **G-3** Retirement by the owner's rule only: "a test is kept only if its claim is a live decision" is applied per claim with evidence, never per file by seconds.
* **G-4** No edit to the admin files (`solver.js`, `admin.css`, `tokens.css`) and none to `dispatcher.state`.

## System contract

* ADR-0041/R2 — no solution in any public asset (check: AC-3, the served-tree scan)
* ADR-0041/R3 — byte-identical build-time copies and plain hand-written JS/CSS (check: AC-3, AC-4)
* ADR-0041/R4 — progress stays in localStorage (check: AC-3)
* CARD-328 — superseded by this card for the duplicated looks (check: AC-1 classifies every agreement test RETIRE-MOOT or states why not)

## Worktree notes

(none yet)
