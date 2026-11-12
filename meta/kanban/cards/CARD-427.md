# CARD-427: The hint and probe messages are hard to notice: a page-wide strip that vanishes on the next tap

**Status:** done
**Priority:** P2
**Category:** ux-polish
**Estimate:** 1c (0.5d)
<!-- LOWERED from 2c when the owner ruled D1/D2 (2026-11-11): a viewport-centred box needs no target tracking, so the card now DELETES `placeExplain`'s targeting path instead of fixing it, and the dismissal rule stays exactly as CARD-409 wrote it. What is left is a centred box, a background from the tokens, and the tests that move with them. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/427-centred-hint-message
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-427
**Source:** owner play-test findings, Google Doc "Гра - тест", 2026-11-11, items 3 and 4 (one card: the same strip, in both findings), with D1/D2 ruled by the owner the same day. Reproduced on production (https://nonogram.adverax.io) before drafting; the measurements below are mine, the finding is the owner's.
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** CARD-426
**Touches:** src/nonogram/admin/static/solver.js, src/nonogram/admin/static/admin.css, tests/test_puzzle_solver_hint.py, tests/test_puzzle_solver_probe.py
<!-- Derived 2026-11-11 by reading `solver.js`'s `placeExplain`, `replaceExplain` and `wireExplainDismiss`, and `admin.css`'s `.player-explain`. `tests/test_player_public_mode.py` and `tests/test_player_shared_ui_site.py` also name `player-explain` — name them in the brief, they may need re-pinning. -->
**Review score:** 9.0 (cycle 1)
**Started:** 2026-11-11T20:30:00Z
**Closed:** 2026-11-12T07:40:00Z
**Actual:** 1 review cycle + 2 orchestrator prose edits (wall clock excluded, owner ruling)
**Merge commit:** b389f8fa
**Blocked by:** —

## Why this card exists

The owner, playing on both desktop and mobile: *"Hint and contradiction/probing messages in both desktop and mobile versions are difficult to notice. I think we can bring them over the puzzle and add a noticeable background"*, and *"Desktop - Hint message is much longer than the puzzle"*.

Three mechanisms, all measured on production at 1440x900:

1. **It is page-wide.** `#puzzle-player-explain` measures **1360 px** against a board of **698 px** — nearly double. That is finding 4 exactly; a strip twice the width of the thing it is about does not read as attached to it.
2. **It is a glance, by an earlier decision.** `wireExplainDismiss` (CARD-409) clears the text on the **next pointer-down anywhere**, exempting only the hint and check buttons. On a phone the tap the reader makes *to act on the hint* is the tap that erases it. The sentence survives for a screen reader in `#puzzle-player-announce` (1 x 1 px, correct by design) — so the reader who can see it has the weakest version of it.
3. **The "over the board" placement often does not happen.** `placeExplain` positions the strip against `td.player-cell.is-hinted, .is-offered`, or against a single hinted ROW; a hinted **column** yields one lined cell per row (measured: 13 cells, 13 distinct rows), so `targets.length === 0` and the function **returns without placing anything**. Measured: `is-top` false and y = 568 on all three hint rungs, with the strip left where its default CSS puts it.

So "difficult to notice" is not a styling opinion: for a column hint the strip is unplaced, full-page-width, and gone on the next touch.

## Owner ruling, 2026-11-11

Asked whether the message should stop being a glance, the owner's answer: **"let it disappear. just appear the center of the screen on some background"**. So:

**D1 — it stays a glance.** `wireExplainDismiss` is unchanged: the next pointer-down anywhere still clears it, and the live region still keeps the sentence for a screen reader. CARD-409's decision stands; this card does not reopen it.

**D2 — it is centred in the viewport, over whatever is under it.** This supersedes the direction in the original finding ("bring them over the puzzle"): the ruling is the *screen's* centre, not the board's, which is a simpler rule and is independent of where the hint points.

**What the ruling removes.** `placeExplain` exists to track the hinted cells — it measures their span, decides `is-top`, and `replaceExplain` re-runs it on every redraw, resize and stage move. A viewport-centred box needs none of that, and the column-hint early return (mechanism 3 below) stops being a bug to fix and becomes a path to delete. Deleting it is part of this card, not a follow-up: leaving dead placement logic beside a centred box is how the next reader learns a rule that is no longer true.

**One consequence to state rather than discover.** Centred, the box can cover the cells the hint is about — including the highlighted column it names. That is acceptable under D1 precisely because it disappears on the next pointer-down: the reader reads, then taps, and the board is clear. The author does not add a dodge-the-target behaviour; if it turns out to matter in play, that is a new finding from the owner, not an author's guess.

## What to implement

1. **A contained box, centred in the viewport.** Not page-wide: today it measures 1360 px against a 698 px board. Fixed positioning, centred both ways, with a max width that keeps it readable on a phone and well short of the page on a desktop.
2. **A noticeable background,** from the theme tokens rather than a literal, with contrast checked in both themes (the page has a dark mode) — and the box must read as a message, not as part of the board.
3. **Delete the placement path the ruling makes dead:** `placeExplain`, its `is-top` class, `replaceExplain` and its callers. Keep `wireExplainDismiss` exactly as it is.
4. **The probe messages come with it** — the owner named hint and contradiction/probing together, and both write through this same strip, so both land centred without a second code path.

## Acceptance criteria

- **AC-1** (centred, contained): at 390x844, 844x390, 1280x720 and 1440x900, with a hint shown, the box's centre is within a pixel or two of the viewport's centre on both axes, and its width is at most the board's and well under the page's. (test: changed presentation cells in `tests/test_puzzle_solver_hint.py`; plant: restore the page-wide rule, or the old placement, and the cell reds.)
- **AC-2** (it still disappears, D1): a pointer-down anywhere but the hint and check controls clears it, and the live region keeps the sentence. (test: the existing `wireExplainDismiss` cells, which must pass **unchanged** — that is the evidence that this card did not reopen CARD-409.)
- **AC-3** (the dead path is gone, not orphaned): `placeExplain`, `is-top` and `replaceExplain` are absent from `solver.js` and from `admin.css`, and no test still names them. (test: the hint module's own cells after the change; evidence: a grep over `src/`, `tests/` and `player/` recorded in Worktree notes.)
- **AC-4** (the board does not move when it appears): at 390x844 and 1440x900 the board's box is identical with and without the box shown. (test: the existing board-does-not-move control, extended to this trigger.)
- **AC-5** (the probe messages too): a probe decision's message appears in the same centred box, with no second placement path. (test: a changed cell in `tests/test_puzzle_solver_probe.py`.)

**Net test count:** prefer 0 added — the hint module's existing presentation cells are the place for AC-1 and AC-2, and AC-3 removes claims rather than adding them. Deleting a test whose only subject was `placeExplain`'s targeting is expected, with the survivor named. State the net.

## Worktree notes

- **[Env / start gate]** forge version unresolved (no plugin manifest, no `meta/.skills.yml`); `make_probe.py start-gate` → exit 0, `decision: gate`, `source: test_command` — **exit 127 in a worktree** (no `.venv`): use `/Users/omelnikova/PycharmProjects/PythonProject4/.venv/bin/python`. Fork point `0d1a3430`.
- **[Impact scope]** Derive with `scripts/impact_set.py --gate --against main`, never from a standing note.
- **[Concurrency]** CARD-424 is `in_progress` in parallel and shares `src/nonogram/admin/static/{solver.js,admin.css}` — different regions: that card owns the brush menu's rules, `closeMenu()` and the dismissal exemption; this card owns `.player-explain`, `placeExplain`, `replaceExplain` and the probe/hint strip. Keep every edit inside those; anything else is a `SCOPE+` line.
- **[The frozen census does NOT apply to this card]** `tests/test_player_base_css.py` samples 29 elements in document order and **the explain strip is not among them** (the list runs ... 24 probe-note, 25 puzzle-player, 26 player-cell, 27 puzzle-player-offer, 28/29 btn). The strip is absolutely positioned, so it reflows none of the sampled elements either. If your change somehow moves a census row, that is a finding to report, not a table to edit.

- **[Ordering, 2026-11-11]** `Depends on:` names **CARD-426** — not a logical dependency but a serialization, enforced by the board rather than remembered. This card edits `src/nonogram/admin/static/solver.js` and `src/nonogram/admin/static/admin.css`; CARD-426 is in review on both files and will take a further round for the owner's chrome ruling, and CARD-424 is already queued behind it on the same stylesheet block. Three cards rewriting one stylesheet and one script at once is the case the board's serialize rule exists for. `start` gates on this field, so the queue holds without anyone re-reading the board.
- **[Owner ruling already recorded]** D1 and D2 are settled (see `## Owner ruling, 2026-11-11` above): the message stays a glance, and it is centred in the viewport. No decision is outstanding, and the estimate is 1c because the ruling deletes `placeExplain`'s targeting path rather than fixing it.

### [Implementation] the worktree's own record (synced by diff)

### Implementation, 2026-11-11 (wave 79)
**AC red→green**
- **AC-1** (centred, contained): test `test_the_line_moves_neither_the_toolbar_nor_the_board` (`TestSolverHintLadder_EveryPressChangesSomethingSeen`, `tests/test_puzzle_solver_hint.py`) red→green. Red read `position: 'absolute'`, `dy 283.125` at 390x844 — the strip where the stylesheet had left it, not centred.
- **AC-2** (it still disappears, D1): `wireExplainDismiss`'s **body is byte-identical** — the diff on it is one word of the comment above it (“the strip over the board” → “the box over the page”). The dismissal cells pass unchanged: the `Escape`/pointer-down arm inside the AC-1 cell, `TestSolverProbe_AWrongGuessOffersTheOtherColour`'s `Escape` / outside / undo loop, and `TestSolverBrushMenu`'s cell that names `wireExplainDismiss` as the shape it follows. None was edited.
- **AC-3** (the dead path is gone, not orphaned): the grep below is empty, and the hint and probe suites pass without it.
- **AC-4** (the board does not move): the same AC-1 cell's `empty == full == after` comparison over head, board, toolbar, counters and progress, now at **five** viewports.
- **AC-5** (the probe messages too): `test_the_offer_names_the_other_colour_and_marks_it_once` (`tests/test_puzzle_solver_probe.py`) red→green. Red (measured by restoring the old `.player-explain` rule and re-running) read `position: 'absolute'`, `width 980`, centre off by `dx 110, dy 286.72`. Green reads fixed, centred, `inside`. It goes through the shared `.player-explain` rule — no second placement path exists to write.
**Measured geometry** (rung 2, the longest sentence of the three; `documentElement.clientWidth/Height`, which is what a `position: fixed` box is centred in):
| viewport | box w x h | centre offset | board w | box / page |
|---|---|---|---|---|
| 390 x 844 | 358.00 x 72.66 | 0, 0 | 364.09 | 91.8% (gutter-bound) |
| 844 x 390 | 480.00 x 72.66 | 0, 0 | 364.09 | 56.9% |
| 1280 x 720 | 480.00 x 72.66 | 0, 0 | 444.02 | 37.5% |
| 1280 x 900 | 480.00 x 72.66 | 0, 0 | 592.45 | 37.5% |
| 1440 x 900 | 480.00 x 72.66 | 0, 0 | 592.45 | 33.3% |
The centre is exact, not within the two pixels the AC allows: `inset: 0; margin: auto` is a layout result, so there is no half-pixel from a translate.
**One deviation from AC-1's letter, stated rather than discovered in review.** AC-1 asks for a width “at most the board's” at all four sizes. That holds at 390 x 844, 1280 x 900 and 1440 x 900 — and it cannot hold at **844 x 390 or 1280 x 720**, where the board is scaled DOWN to Fit (364.09 px and 444.02 px) and a message capped to it would be narrower than the sentence can read. The cap is a reading measure, `min(30rem, 100vw - 2 x --space-4)`. The finding's complaint does not come back: it was 1360 px, **94% of the page** and nearly twice the board; this is 480 px and at most 56.9% of the page anywhere above a phone. The test asserts the three bounds it can hold honestly (a 16 px gutter at every size; ≤ 60% of the page from the landscape phone up; ≤ the board wherever the board is drawn at 100%), each with its measured figure in the comment beside it.
**Contrast, both themes.** There is **no dark mode on this page** — the brief's premise does not hold: `tokens.css` defines `:root` and `:root[data-theme="christmas"]` only, and no `prefers-color-scheme: dark` block exists in `tokens.css`, `admin.css` or `player/*.css` (the only one in the repo is `nonogram/web/pages.py`'s generation form, a different application). So “both themes” is read as the two that exist, and both are checked:
| pair | default | christmas |
|---|---|---|
| `--color-text` on `--color-accent-tint` (the sentence) | **13.40:1** | **12.48:1** |
| `--color-accent` edge on `--color-accent-tint` | 6.30:1 | 6.87:1 |
| `--color-accent` edge vs `--grid-paper` (the board under it) | **7.26:1** | **8.06:1** |
| `--color-accent` edge vs `--color-bg` (the page under it) | 6.50:1 | 6.83:1 |
| `--color-accent-tint` vs `--grid-paper` | 1.15:1 | 1.17:1 |
Said plainly: the sentence is far past AA at 13.40:1 / 12.48:1, and what separates the box from the board is the **2 px accent edge** (7.26:1 / 8.06:1, well past WCAG 1.4.11's 3:1 for a non-text boundary) plus `--shadow-modal` — not the tint, which is 1.15:1 against the board's paper and is a ground for the text, not a separator. An accent-FILLED ground was weighed and rejected: the same box carries the Wrong-guess offer's two `.btn-outline-secondary` buttons, whose Bootstrap tokens (`--bs-btn-bg: var(--color-surface)`) are built for a light ground, and AC-5 brings that message through this one rule on purpose.
**AC-3 grep** (`grep -rn "placeExplain\|replaceExplain\|is-top" src/ tests/ player/`): **no hits**. The identifiers are gone from the code *and* from the prose — the retirement is recorded in `admin.css`'s `.player-explain` comment, `solver.js`'s `showExplain` header and `tests/test_puzzle_solver_hint.py`'s retired-constant note, each describing the deleted behaviour without naming a function that no longer exists. `.player-stage-wrap { position: relative; }` went with them: the strip was the only thing positioned against it (`#puzzle-player-announce` is outside the wrapper; the tool menu and the confirm popover position against the toolbar).
**Net collected node ids: 0.** No test added, none deleted, none renamed, no parametrisation changed — `test_puzzle_solver_hint.py` 53 functions / 60 ids, `test_puzzle_solver_probe.py` 28 / 39, `test_player_public_mode.py` 38 / 79, `test_player_base_css.py` 2 / 3, all unchanged. Nothing to record in `ADDED_SINCE_BEFORE`. The one test whose only subject was the old targeting is not a function but the module constant `_STRIP_COVERS` (with `_SET_BOARD`, which existed only to drive it); both are deleted and the surviving claim is the centred, contained geometry in the same cell, `test_the_line_moves_neither_the_toolbar_nor_the_board`.
**Two pins that moved, both named here rather than quietly edited:**
1. `tests/test_player_base_css.py`'s FROZEN census **does** reach this change — the brief's check was right that `#puzzle-player-explain` is not sampled, but row **27 `div puzzle-player-offer` is**, and the offer carries `.player-explain`. The row changed in 7 fields at each width (`margin 0px→auto`, `padding 8px 12px→12px 16px`, `border-width 1px 0px 0px→2px`, `border-style solid none none→solid`, `border-radius 0px→4px`, `position absolute→fixed`, `background-color` the 94% surface mix `→rgb(230, 239, 236)`); its rectangle is unchanged (`0|0|0|0` — the offer is `[hidden]` when the census reads it). Re-recorded by the module's documented protocol, not hand-patched: `bootstrap.min.css` fetched from the `bootstrap@5.3.0` URL `base.html` pins, **sha256 verified equal to `PROVENANCE`**, and the run certified that our `shared-ui-base.css` still matches the real file exactly — every other row of both widths reproduced byte-for-byte, which is why `recorded` still says 2026-11-11. `PROVENANCE` carries the account.
2. `tests/test_player_public_mode.py::TestPublicMode_TheCensus::test_every_control_family_is_read_by_the_census` plants its ghost button at the literal anchor `"</div>\n</div>\n\n{# CARD-409"` — the opening of the template comment this card rewrites. Re-**pinned** to `{# CARD-427`; the claim is untouched and the cell still reds on an unswept control.
**Not done, deliberately:** no dodge-the-target behaviour (the ruling's own consequence), `wireExplainDismiss` not reopened, and nothing touched in CARD-424's region (`closeMenu`, the brush menu's rules, the dismissal's exemption selector).
**Verified with** (narrow set only, never the full suite or the lock — a foreign worktree was live): `tests/test_puzzle_solver_hint.py` + `tests/test_puzzle_solver_probe.py` (99 passed), and `tests/test_player_base_css.py` + `tests/test_player_public_mode.py` + `tests/test_player_shared_ui_site.py` + `tests/test_puzzle_solver_brush_menu.py`.

### [Orchestrator] three corrections the implementation made to my brief

- **"The page has a dark mode" — FALSE, and it was mine.** `tokens.css` defines `:root` and `:root[data-theme="christmas"]` only; there is no `prefers-color-scheme: dark` in `tokens.css`, `admin.css` or any `player/*.css` (the repo's only one is `nonogram/web/pages.py`'s generation form, a different app). I asserted a theme that does not exist and asked for contrast to be checked in it. Contrast was checked in the two themes that do: the sentence **13.40:1** default and **12.48:1** christmas, the accent edge against the board's paper **7.26:1 / 8.06:1** (past WCAG 1.4.11's 3:1). The tint is only 1.15:1 against `--grid-paper` — what makes the box noticeable is the edge, the shadow and being centred, not the ground. An accent-filled ground was weighed and rejected because the same box carries the offer's two `.btn-outline-secondary` buttons, whose Bootstrap tokens assume a light ground.
- **"The frozen census does not apply to this card" — HALF right, and the half I missed cost a re-record.** `#puzzle-player-explain` is indeed not sampled. But row **27 `div puzzle-player-offer` is**, and the offer carries `.player-explain` — so seven fields changed at each width (margin, padding, border-width, border-style, border-radius, position, background-color), rectangle unchanged (`0|0|0|0`, it is `[hidden]` when read). I had told the author that a moved census row would be "a finding to report, not a table to edit"; they reported it **and** handled it by the module's own protocol, fetching the pinned `bootstrap@5.3.0`, verifying its sha256 against `PROVENANCE`, and certifying that `shared-ui-base.css` still matches the real file exactly, with every other row of both widths reproduced byte-for-byte. That is the right answer to a brief that was wrong.
- **AC-1's "at most the board's width" cannot hold at two of the four ruled sizes.** Measured: the box is 480 x 72.66 px at every desktop size, 358 px on the phone. It is inside the board at 390x844, 1280x900 and 1440x900 — but at **844x390** and **1280x720** the board is scaled down to Fit and is *narrower than a readable line of text* (364.09 and 444.02 px), so the cap, which is a reading measure (`min(30rem, 100vw - 2 x --space-4)`), is wider. The owner's complaint does not return: it was 1360 px = **94% of the page**; this is at most **56.9%**. The cell asserts the three bounds it can hold honestly — a 16 px gutter at every size, ≤60% of the page from 844 up, and ≤ the board wherever the board is drawn at 100% — each with its measured figure beside it. An AC that cannot be true at every size it names is my drafting error, not an implementation shortfall.
- **[Re-pin, declared]** `test_every_control_family_is_read_by_the_census` plants its ghost button at the literal anchor `"{# CARD-409"` — the opening of the template comment this card rewrites — so it is re-pinned to `{# CARD-427`, claim untouched.
- **[Not verified by anyone]** the owner's eyeball on a real board. The box is centred over the puzzle and will cover cells the sentence names; that is the ruling's accepted consequence and the first thing to look at after the next publish.

- [Review 1/3] Score: 9.0 — forge:review, all three verdicts `pass`. **0 critical, 0 important**, 3 minor, 3 out-of-scope. Report `meta/review/20261111T224342Z-CARD-427-cycle1.yml`. **[Severity gate]** PASS.
- **[Review 1/3] the finding worth the owner's eye: the SOLVE CELEBRATION rides this same rule.** `#puzzle-player-explain` carries a third message the card never mentions — on a genuine solve the redraw calls `showExplain(praise)` ("Solved with no hints.") and clears it after `CELEBRATION_MS` (= `SWEEP_SPAN_MS` + 2000 = 4000 ms). It is therefore now drawn **centred over the picture at the moment the picture is revealed**. Measured rather than asserted, using rung 3's sentence as the praise's length class (234.2 x 50.3 px): it covers **4.0% of the board at 390x844, 7.7% at 844x390, 3.5% at 1280x900 and 1440x900**, and at none of them does it cover the board's own centre (the head and toolbar push the board up and left). The whole path was confirmed on a real solve: `position: fixed`, `z-index: 1030`, "Solved with no hints.", gone after the beat. Not gating — small, dismissible, and it also clears on the next pointer-down like every other message in that box. But it is a user-visible change at the payoff moment, covered by no AC, asserted by no test, and **outside the words of a ruling that named the hint and the contradiction/probing messages**. Taken to the owner rather than noted away, because this board's own history (CARD-163's "the name is the reward", CARD-280's solved board becoming the picture) says the payoff moment is one the owner cares about.
- **[Review 1/3] a guard by coupling, not by assertion.** At 844x390 and 1280x720 the only live width bound is "≤60% of the page" — the third bound (≤ the board) is gated on `height == 900 or width == 390`, so a 768 px box would be 1.7x the 444.02 px board at 1280x720 and the cell would stay green. It stays green in practice only because the cap is one global `min(30rem, …)`, so a widening regression also widens 1280x900 where bound 3 does bind. Real but narrow; the comment does not say so, and one clause closes it.
- **[Review 1/3] what it re-derived rather than read:** the deletion is complete (`grep` for `placeExplain|replaceExplain|is-top|--player-explain-top` across `src/`, `tests/`, `player/` is empty) and safe — it checked the one claim that mattered, that `#puzzle-player-announce` sits at template line 277 **outside** the wrapper which opens at 327, and that every other absolutely-positioned player selector anchors to its own `relative` ancestor; the centred box at **seven** viewports with centre offset 0,0 and no horizontal overflow; the census diff being **exactly two row lines**, both `27 div puzzle-player-offer`, with the seven claimed fields and `rgb(230, 239, 236)` decoding to `--color-accent-tint` exactly; and net 0 node ids from the diff carrying no added or removed `def`/`class`/`parametrize` line at all.
- **[Review 1/3] mutation check RAN: 5 mutants, 5 killed.** Notably the accent border's removal **survived the hint cell** and was killed by `test_the_project_stylesheet_matches_the_real_bootstrap` at both widths — the census is what pins the box's appearance, which is worth knowing before anyone edits that table casually.
- **[Review 1/3] coverage stated, not claimed:** no screenshots, runtime log, a11y log or visual diff were provided, so the rendered, console and automated-a11y checks did **not** run. The owner's standing habit of eyeballing a render on a real picture applies here more than usual.

### [OWNER RULING 2026-11-12] the solve praise stays centred with the rest

Asked what should happen to the solve celebration now that it rides this box — "Solved with no hints." centred over the picture for up to 4 seconds at the moment the picture is revealed — the owner chose **"Leave it centred with the rest."**

So: **one box, one rule, no second placement path**, which is what this card spent its effort deleting. The declined alternatives are recorded so nobody re-opens them: giving the celebration its own placement again (it would re-introduce the second path), and shortening or dropping the praise (it would trade away a beat deliberately built in CARD-280).

The measured facts behind the decision, so a later reader sees what was weighed: the praise covers **4.0% of the board at 390x844, 7.7% at 844x390, 3.5% at 1280x900 and 1440x900**, never the board's own centre (the head and toolbar push the board up and left), clears after `CELEBRATION_MS` (= `SWEEP_SPAN_MS` + 2000 = 4000 ms), and clears early on any pointer-down like every other message in that box.

**Nothing to implement.** The behaviour the owner chose is what the branch already does; this note exists so the next card does not read the absence of an AC as an oversight. The one thing still owed is the owner's own eyeball on a real picture — the review ran no screenshots, console log or automated a11y scan, and said so as coverage rather than as a pass.

- **[Build gate]** Derived selection: **202 files / 9002 tests (84.7%)** — much larger than its siblings because the card touches `puzzle_solve.html`, which reaches the book and PDF suites. Run 1: 8956 passed, 30 skipped, **2 failed** in 33:20. Run 2 of the lifted marked files: 11 passed.
  - The extra red was `tests/test_player_public_mode.py::TestPublicMode_TheSweep::test_every_control_is_driven_and_nothing_goes_wrong[chromium]` — **this card's own territory**, so it was chased rather than retried blind: it passes alone on the branch (10.3 s), in the implementer's narrow set (180 passed) and in the reviewer's (232 passed).
  - **Re-run of the identical selection on the identical head: 8957 passed, 1 failed** (the pre-existing `test_book_pdf_memory` host-calibration red), 28:22. The +1 is exactly the sweep test.
- **[Flaky gate members — a pattern now, not an incident]** Two different browser tests have now reddened two consecutive large gates and passed on re-run of the identical selection: `test_puzzle_solver_clues.py::TestPlayerNumerals_ColumnFloorIsTheWidestColumnNumeral::test_one_digit_column_numbers_keep_the_fit` on CARD-426 (34:06 failing against 26:17 and 26:33 passing) and this one (33:20 against 28:22). **In both cases the failing run was the slower one**, and both tests measure browser geometry. The common cause is most likely contention at this selection size rather than anything in either card. Worth a card if it recurs a third time; two observations with consistent timing are a pattern worth recording but not yet a diagnosis.
- **[Harness flaw, mine, fixed on the second attempt]** The gate script printed only pytest's last 30 lines, so run 1's assertion was lost. I "fixed" it once by capturing context around `FAILED ` and `_ test_` — markers that match pytest's **summary**, not its `____ TestClass.test_name ____` failure header — so the traceback was discarded a second time and I had to measure the test directly instead. It now writes the complete output to a file and prints the whole `= FAILURES =` section. **A red reported without its numbers is a red nobody can act on**, and I shipped that flaw twice.
- **[Done]** Merged `b389f8fa` on the gates. Estimate 1c against 1 review cycle — the only card in this set to meet its estimate, and the reason is the owner's ruling: it arrived before implementation and deleted work rather than adding it.
