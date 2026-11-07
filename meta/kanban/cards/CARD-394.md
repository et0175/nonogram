# CARD-394: A small project stylesheet replaces Bootstrap on the public player — the four classes and the base reset, owned by the repo

**Status:** ready
**Priority:** P2
**Category:** enabler
**Estimate:** 2c (1d)
<!-- Stated in review cycles at DRAFT time. The arithmetic is small (4 classes + the reboot rules the page relies on); the cost is the FIDELITY test against the real Bootstrap file, which the reviewer of CARD-386 measured: a bare `[hidden]` rule alone already differs on 14 of 22 sampled elements at 1280 px. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** owner ruling 2026-11-07 on CARD-386's review (reviewer's recommendation, accepted): "Small project stylesheet" for how the public site gets Bootstrap's styling long-term. CARD-386 assembles the admin's own player files into a preview site and takes the REAL Bootstrap file from the owner's machine at build time (never committed). Real Bootstrap 5.3 is 233 KB, fails AC-392's served-tree scan (3 foreign references: the w3.org SVG namespace, getbootstrap.com, the licence URL on GitHub; plus 2 unclassifiable data-URI fragments), and a CDN is out (ADR-0041 bans external references).
**Idea:** —
**Wave:** —
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** CARD-386
**Touches:** player/assemble.py, scripts/assemble_player_site.py, player/bootstrap-lite.css, tests/test_player_shared_ui_site.py, tests/test_player_bootstrap_lite.py, docs/deploy/player.md
<!-- The stylesheet's file name and place are the author's to pick under player/ (it must be hand-written, repo-owned, and carry no third-party text); the list above is the starting point. The live assembly path (the one deployed today) stays untouched: this card changes the OPT-IN shared-UI mode only. -->
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

The shared-UI preview (CARD-386) serves the admin's own `solver.js`, `solver_state.js`, `tokens.css` and `admin.css` on the public pages. `admin.css` relies on Bootstrap 5.3: the assembled page uses four Bootstrap classes (`btn`, `btn-outline-secondary`, `btn-danger`, `badge`) plus Bootstrap's base reset rules (`[hidden]`, box-sizing, margins, form-control resets). Today the preview needs the owner to supply the real Bootstrap file at build time. That cannot be the deployed state: the file cannot be committed (it fails the served-tree scan and ADR-0006/ADR-0041/R3), and loading it from a CDN is banned by ADR-0041. The owner chose to replace only Bootstrap's part with a small stylesheet the repo owns.

## What to implement

1. **A hand-written stylesheet** (starting point: `player/bootstrap-lite.css`) covering exactly what the assembled page uses: derive the used selectors from the assembled page (the admin template's markup + `solver.js`'s created elements) with a script, NOT from memory; cover the four classes' normal, hover, focus-visible, active and disabled states as the page reaches them, the badge, and the reboot rules the layout depends on. No third-party text copied (a licence-bearing paste is the defect this card exists to avoid): write the rules from the measured computed styles of the real Bootstrap in a browser.
2. **Wire it into the opt-in mode:** the assembler places the stylesheet in the shared-UI tree in the position `bootstrap.min.css` had; the `--bootstrap <file>` flag stays as an optional override for the owner's own fidelity comparison and is never the default. The default (live) assembly path stays byte-identical (CARD-386 AC-4 holds).
3. **A fidelity test against real Bootstrap that the suite can run without committing it:** when a real Bootstrap file is supplied through an environment variable the test compares computed styles and bounding rectangles of a sampled set of elements (at least the 22 the CARD-386 reviewer sampled, at 390 px and 1280 px, in the states above) between the project stylesheet and the real file, with a stated tolerance derived from the measured residue; when the variable is unset the comparison cell is NOT skipped silently: it runs against a frozen table of the real file's measured values recorded in the test (computed once from the real file, with the provenance written beside the table).
4. **The served-tree scan passes on the real preview tree** with no carve-out: the scan reports no foreign reference and nothing unclassifiable that is not already the pinned `solver.js` relative import.
5. **Docs:** `docs/deploy/player.md` says the preview mode no longer needs a Bootstrap file; ADR-0041/R3's wording ("plain hand-written JavaScript and CSS") is checked and not edited unless a sentence became false.

## Acceptance criteria

* **AC-1** (no third-party stylesheet in the tree): the assembled preview tree contains no `bootstrap` file by default and links exactly the three stylesheets of CARD-386 G-1 (`tokens.css`, `admin.css`, the project stylesheet); the stylesheet text contains no licence header and no URL. (test: the CARD-386 module's cells re-pointed, plus a plant that appends a `https://` reference and reds the scan.)
* **AC-2** (fidelity): every sampled element's computed style for the properties that decide layout (display, box-sizing, margin, padding, border, font, line-height, width/height, flex) and its bounding rectangle equal the real Bootstrap's within the stated tolerance at both widths and in each state; a plant that drops the `[hidden]` rule or changes `.btn` padding reds it. (test: the new module.)
* **AC-3** (the page still plays): CARD-385's browser sweep and the CARD-386 solved-banner test pass on the tree with the project stylesheet. (test: CARD-386's cells, unchanged expectations.)
* **AC-4** (default path unchanged): the live assembly output is byte-identical before and after. (test: CARD-386 AC-4's cell.)
* **AC-5** (owner can still compare): with `--bootstrap <real file>` the preview builds as before. (test: the existing flag cell.)

## Guardrails

* **G-1** No override layer and no edit to the admin files (`admin.css`, `solver.js`, `tokens.css`): the project stylesheet replaces only Bootstrap's part.
* **G-2** Not deployed; no change to `vercel.json` or the live assembly path.
* **G-3** No Bootstrap text in the repository, in the stylesheet, in a test fixture or in a comment.
* **G-4** No test deleted, renamed, skipped or merged; node-id set difference; the fidelity cell can fail (plants).

## System contract

* ADR-0041/R2 — no solution in any public asset (check: CARD-386 AC-3's scan, unchanged)
* ADR-0041/R3 — byte-identical build-time copies and plain hand-written CSS (check: CARD-386 AC-2; review-lens on the stylesheet's text)
* ADR-0006/R1 — dependency baseline closed (check: review-lens: nothing third-party enters the repo)

## Worktree notes

(none yet)
