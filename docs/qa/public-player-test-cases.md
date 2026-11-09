# Public player — manual test cases (COMP-011 / FR-045)

> **Production changed under these cases on 2026-11-09.** They were written against
> `player/play.js`, which CARD-399 deleted on 2026-11-08; `/play/<key>` is now the
> admin player in public mode, and that went live on 2026-11-09. The *expectations*
> mostly survive — it is the same shared state module and the same rules — but the
> hooks and some of the controls do not. Measured on the live page that day:
>
> - the four brushes are a **menu** behind `#puzzle-player-tool-trigger`, not four
>   always-visible buttons (so PP-10's "read the toolbar left to right" needs the
>   menu opened first);
> - the solved banner is `#puzzle-player-solved` and the lock is `.is-solved` on the
>   table and the toolbar; there is no `body[data-solved]` (PP-52, PP-53);
> - the hint's sentence is `#puzzle-player-announce` and the explain region, not
>   `.player-hint-say` (PP-44 to PP-48);
> - **PP-40 is wrong as written**: a row's numbers do not circle when its runs are
>   merely filled. Marking the row's gaps white circled 3 numbers where filling
>   alone circled 0 — the module's rule, and the admin's behaviour too;
> - the error count, the progress percent and Check are **absent from the DOM**
>   (element count 0), which is a stronger result than PP-56 asks for;
> - probe mode is **live** (PP-60 to PP-70 are no longer `n/a`), and the probe
>   marker is `data-probe` on the cell.
>
> CARD-400 to CARD-413 will change this UI again — they are the fourteen findings
> cards, none merged, all now live as gaps. Rewriting these cases is best done
> after them.

**What this is.** A human-runnable catalogue for the public player: the static
site at `/play/<key>`, `/b/<slug>` and `/library`. Written 2026-11-06, against
`main` at that date and against production as it then served.

**What this is not: the gate.** Almost every rule below is already pinned by a
Playwright or source test, and those tests — not this page — are what a card is
merged on. Each case therefore names its **Gate**: the automated test that fails
if the behaviour regresses. Where a case has no gate it says
**manual-only** and why, and those are the cases worth your time:

- the **deployed** site, which no test reaches (the suite drives an assembled
  tree on a local host);
- a **real finger on glass** — a pinch, a drag that pans, a tap that is 44 px of
  thumb rather than 44 px of CSS;
- **legibility**: whether two marks on one small cell can actually be told apart
  by eye, which a contrast ratio bounds but does not settle;
- a **printed QR code** scanned by a phone camera.

> The suite is the better instrument for everything else. If a case below
> disagrees with its gate, the gate is right about what the code does and this
> page is stale — fix this page, and say so in the run notes.

## Running them

Two targets, and a case says which it needs.

**A local tree** (fast, no deploy, uncounted):

```bash
./.venv/bin/python scripts/assemble_player_site.py --bundle build/player-bundle --out build/site
./.venv/bin/python scripts/preview_player_site.py            # build/site on http://localhost:8081
```

The preview server applies `vercel.json`'s rewrites, so `/play/<key>` and
`/b/<slug>` work; `python -m http.server` answers 404 on both and only
`/library` appears to work, which reads as a broken tree when the tree is fine.

**Production**: `https://nonogram.adverax.io` — see `docs/deploy/player.md` for
what is published there and how it got there. A production run is a **smoke**
run (PP-50 to PP-54), not the whole catalogue.

**Fixtures.** Any key from `/library` works. Observed in the 2026-10-29 bundle
and answering 200 on production on 2026-11-06:

| Use | Key |
|---|---|
| small, easy — marking, hints, solving | `/play/33fa80994c` (10×10 easy), `/play/40556cfb69` (10×10 easy) |
| large — zoom, gutters, phone | `/play/52603b6dee` (30×30), `/play/b688158317` (30×29) |
| book landing | `/b/6578fe3f67` |

**State.** Play state is one `localStorage` entry per puzzle,
`nonogram-public:<key>`. To start clean: devtools → Application → Local Storage →
delete the entry, or run `localStorage.clear()` in the console. There is no
account and no server state, so nothing else needs resetting.

**Devices.** Where a case says *phone*, use a real device or an emulated one at
390×844 (portrait) and 844×390 (landscape). The landscape width matters: see
PP-25.

**Recording a run.** Date, target (local tree + commit, or production
deployment id), device, and for each case `pass` / `fail` / `n/a` with what you
saw. A failure that reproduces becomes a card; a failure that does not is still
worth writing down with the exact steps.

---

## A. Getting to a board

### PP-01 — a puzzle link draws its board
**Steps.** Open `/play/33fa80994c`.
**Expected.** Header reads `Puzzle 10×10` and a tier chip; the board is drawn
with a clue gutter on each axis; the toolbar, the hint bar and the usage
paragraph are all visible. The page title is `Puzzle 10×10 · Nonogram`.
**No puzzle name anywhere** — the picture's name *is* the answer, so the site
does not serve one.
**Gate.** `tests/test_public_player.py::test_play_page_renders_and_marks`.

### PP-02 — a mistyped key fails softly
**Steps.** Open `/play/zzzz`, then `/play/0000000000`, then `/play/`.
**Expected.** A sentence, no board, no dead controls: the first is "this address
names no puzzle", the second "this puzzle is not on the site". Nothing throws
into the console.
**Gate.** `test_an_unknown_or_malformed_key_draws_no_board`.

### PP-03 — the library filters
**Steps.** Open `/library`. Use the size and tier filters.
**Expected.** Tiles are thumb-sized, each wears its tier, the filtered count is
announced, and **no tile carries a puzzle name**.
**Gate.** `tests/test_public_player_pages.py::test_library_filters_the_index`,
`test_no_puzzle_title_reaches_either_listing`.

### PP-04 — the book landing
**Steps.** Open `/b/6578fe3f67`.
**Expected.** The book's **title** shows (the one declared exemption, owner
2026-10-28), the puzzles are listed in book order and each links to its
`/play/<key>`.
**Gate.** `test_book_landing_lists_and_links`, `test_the_book_landing_shows_the_books_title`.

### PP-05 — an unknown book slug
**Steps.** Open `/b/0000000000`.
**Expected.** A soft landing: a sentence, no error page, no empty frame.
**Gate.** `test_unknown_slug_lands_softly`.

### PP-06 — the page without its script
**Steps.** Block `play.js` (devtools → Network → block request URL), reload.
**Expected.** The fallback paragraph stays ("the player script did not load");
**no toolbar, no hint bar, no zoom buttons** — a page whose script never ran
shows no dead controls.
**Manual-only.** The gate covers the assembled markup, not a blocked asset.

---

## B. Brushes and marking

### PP-10 — four brushes, in the panel's order
**Steps.** Read the toolbar left to right.
**Expected.** Black, White, Maybe, Clear — the admin player's own menu order —
each with a swatch previewing what it paints. Exactly one is checked at a time.
**Gate.** `tests/test_public_player_maybe.py::TestPublicMaybe_FourToolsInTheAdminsOrder`,
`TestPublicMaybe_OneToolIsCheckedAtATime`.

### PP-11 — the Black cycle
**Steps.** With Black, tap one cell three times.
**Expected.** black → white (a **centred dot**, not a cross) → blank.
**Gate.** `test_play_page_renders_and_marks`.

### PP-12 — the Maybe cycle
**Steps.** With Maybe, tap one cell twice.
**Expected.** a "?" glyph in the accent colour on a faint ground, then blank.
The glyph is the admin panel's glyph, not a tint of its own.
**Gate.** `TestPublicMaybe_TheBrushMarksACell`,
`tests/test_public_player_agreement.py::TestPlayerLooksAgree_TheMaybeMarkIsTheSameMark`.

### PP-13 — the White brush previews a dot
**Steps.** Look at the White swatch, then mark a cell with it.
**Expected.** The swatch shows the same dot the cell gets. (This diverged once —
the page drew a cross on the cell and the panel a dot — and the owner chose the
dot on 2026-10-30.)
**Gate.** `TestPlayerLooksAgree_TheWhiteBrushPreviewsTheDot`,
`test_the_empty_mark_is_a_dot_and_solving_is_revealed`.

### PP-14 — switching brushes restarts the cycle
**Steps.** Tap a cell with Black once. Switch to White. Tap the **same** cell.
**Expected.** The second tap marks white rather than continuing Black's cycle —
a repeat tap counts only when the brush is the same one.
**Gate.** `test_the_brush_region_and_touch_bindings_are_the_modules`.

### PP-15 — a mouse drag is one stroke
**Steps.** With a mouse and Black, drag along five cells of a row. Press Undo
once.
**Expected.** All five fill on the drag; **one** Undo clears all five.
**Gate.** `test_play_page_renders_and_marks`.

### PP-16 — undo, redo, reset
**Steps.** Make three marks. Undo twice, Redo once, press Reset, then Undo.
**Expected.** Each button is disabled exactly when it has nothing to do; Reset
clears the board and **Undo brings the marks back** (it is a recorded stroke,
not a wipe); the reset is announced in the live region.
**Gate.** `test_play_page_renders_and_marks`, `test_every_player_control_is_in_the_ec_050_walk`.

### PP-17 — the keyboard
**Steps.** Press `Ctrl`/`Cmd`+`Z`, then `Shift`+`Ctrl`/`Cmd`+`Z`.
**Expected.** Undo and redo. No other key does anything — the zoom buttons
deliberately bind none, because the admin's do not either.
**Gate.** `test_every_player_control_is_in_the_ec_050_walk`.

---

## C. Region (the touch arm)

### PP-20 — with Region off, a touch drag pans the page
**Steps.** *Phone.* On a 30×30 board with Region **off**, drag across cells.
**Expected.** The page/board scrolls; **no cell is marked**, not even the one the
finger started on.
**Gate.** `test_a_touch_or_pen_drag_marks_only_while_region_is_armed`.
**Also manual:** that it *feels* like a scroll rather than a fight.

### PP-21 — with Region on, a touch drag marks
**Steps.** *Phone.* Press Region (it shows pressed), then drag across five cells.
**Expected.** Five cells marked, one undo step, and **Region disarms itself** —
it is one-shot: "a drag ended", not "a cell changed".
**Gate.** same as PP-20.

### PP-22 — Region and the brush are independent
**Steps.** Press Region, then pick a different brush.
**Expected.** Region stays armed and the brush changed; pressing Region never
changes the brush. The Region button's three swatches preview the **current**
brush.
**Gate.** `test_the_brush_region_and_touch_bindings_are_the_modules`.

### PP-23 — a mouse never needs Region
**Steps.** With Region off and a mouse, drag.
**Expected.** It marks. Region is a touch/pen rule only.
**Gate.** as PP-20.

---

## D. The crosshair

### PP-24 — hovering lights the cross
**Steps.** *Mouse.* Hover a cell near the middle of a 30×30 board.
**Expected.** Its whole row and column tint, **and so do the two clue boxes**;
a filled cell in the cross stays clearly filled; a circled clue number stays
circled (the ring is a border, the tint a background).
**Gate.** `tests/test_public_player_crosshair.py::TestPublicCrosshair_HoverHighlightsTheCross`,
`tests/test_public_player_circles.py::TestPublicCircles_ACrossedClueStillShowsItsCircle`.

### PP-25 — the gutter corner keeps it
**Steps.** Hover a cell, then move the pointer onto its clue box, then onto the
corner, then off the stage entirely.
**Expected.** The cross **stays** while the pointer is anywhere on the stage —
including the clue boxes and the padding — and clears only when the pointer
leaves the stage. (Looking from a cell to its clue must not put the line out.)
**Gate.** `TestPublicCrosshair_HoverHighlightsTheCross` (the stage cases).

### PP-26 — the no-hover phone
**Steps.** *Phone.* Tap a cell. Lift. Look.
**Expected.** The cross is painted from the touch and **stays after the finger
lifts**, so it is visible between taps. It follows a finger that moves.
**Gate.** `TestPublicCrosshair_TouchIsNeverHalfPainted`.

### PP-27 — a pinch has no crosshair
**Steps.** *Phone.* Put one finger on a cell (a cross appears), add a second and
spread.
**Expected.** The cross **goes out** as the second finger lands, nothing follows
the spread, nothing is left when both lift, and a single tap crosses again.
**Gate.** `TestPublicZoom_APinchZoomsAndPaintsNothing`, `TestPublicCrosshair_TouchIsNeverHalfPainted`.

### PP-28 — the cross is right when zoomed and scrolled
**Steps.** Zoom to 300%, scroll the stage both ways, hover a cell.
**Expected.** The cross is on the cell **under the pointer** — not one off.
**Gate.** `TestPublicCrosshair_ItLandsOnTheCellUnderThePointerWhenZoomedAndScrolled`.

### PP-29 — hovering changes nothing
**Steps.** Hover across many cells. Watch Undo and the devtools Network panel.
**Expected.** Undo stays as it was, no stroke recorded, **no request** — the
crosshair is one CSS class on elements already on the page.
**Gate.** `TestPublicCrosshair_HoverRecordsNoStroke`, `TestPublicCrosshair_ItReadsNoBoard`.

---

## E. Zoom

### PP-30 — the buttons and the readout
**Steps.** Open a 30×30 board. Press `+` until it stops, then `−` until it stops.
**Expected.** The readout starts at **100%** and steps in 25-point steps to
**300%**; `+` is disabled at 300%, `−` at 100%; the cells grow, and the clue
numerals grow with them.
**Gate.** `tests/test_public_player_zoom.py::TestPublicZoom_TheControlsChangeTheZoom`,
`TestPublicZoom_TheBoundsComeFromTheModule`.

### PP-31 — the anchor
**Steps.** Note a cell at the centre of the stage. Press `+` twice.
**Expected.** That cell is still where you were looking — the zoom anchors on
the centre of the stage's visible box rather than jumping to a corner.
**Gate.** `TestPublicZoom_TheAnchoredScrollIsTheModules`.

### PP-32 — the clue gutters stay in view
**Steps.** *Phone,* 30×30, zoom to 300% and scroll into the middle of the board.
**Expected.** The board never hides its own clue gutters behind them; the stage
scrolls rather than the numbers scrolling away permanently.
**Gate.** `TestPublicZoom_AZoomedGutterNeverCoversTheBoard`,
`TestPublicZoom_TheGutterRuleHoldsOverItsOperands`.

### PP-33 — a pinch zooms and marks nothing
**Steps.** *Phone,* Region **armed** (the harder case), pinch out starting on a
cell.
**Expected.** The board zooms; **no cell is marked** — not the cells under the
fingers, and not even the cell the first finger went down on when it lifts. The
readout follows the pinch.
**Gate.** `TestPublicZoom_APinchZoomsAndPaintsNothing`.
**Also manual:** that the pinch tracks the fingers smoothly.

### PP-34 — zoom is a view, not a move
**Steps.** Zoom to 200%, mark a cell, reload the page.
**Expected.** The mark is restored; the zoom is back at **100%**. Zoom records
no stroke, never enters Undo, and is never saved.
**Gate.** `TestPublicZoom_ZoomRecordsNoStroke`, `test_resume_is_local_and_the_page_writes_nowhere`.

### PP-35 — the browser's own pinch still works
**Steps.** *Phone.* Pinch on the page **outside** the board (the header, the
paragraph below).
**Expected.** The browser's page zoom responds — the page deliberately keeps it
(no `user-scalable=no`), and `touch-action` is taken away only from board cells
while Region is armed.
**Manual-only.** Browser-level zoom is outside the suite's reach.

### PP-36 — the landscape toolbar, a known residue
**Steps.** *Phone,* landscape at 844×390. Look at the toolbar.
**Expected (today).** It wraps to **two rows**. This is the owner's open residue
from CARD-324: the group needs about 889 px to stay one row, so 844, 852 and 874
all wrap. **Record it; do not file it** — three layouts that would fit were
measured and deliberately not shipped.
**Gate.** `TestPublicZoom_TheLandscapeToolbarIsOneRow` pins the measured bound
(and reds by design on any new toolbar button, which is why the Hint control
sits under the board).

---

## F. Circled clue numbers

### PP-40 — marks circle their numbers
**Steps.** On a 10×10 board, complete one row's runs correctly.
**Expected.** That row's clue numbers get a ring as the marks account for them;
the ring is a thin border on the number.
**Gate.** `tests/test_public_player_circles.py::TestPublicCircles_TheMarksCircleTheNumbers`.

### PP-41 — circles follow undo, redo and reset
**Steps.** Undo the row, redo it, reset the board.
**Expected.** The rings follow the **recorded** board every time; a drag's
preview does not circle anything until the drag is released.
**Gate.** `TestPublicCircles_TheyFollowUndoRedoAndReset`.

### PP-42 — circled is not solved
**Steps.** Take a line clued `1 2` and mark the 2-run to the **left** of the
1-run.
**Expected.** Both numbers circle, and the board is **not** announced solved.
The circles are a readout; solving is an exact clue check.
**Gate.** `TestPublicCircles_CirclesAreNotTheSolvedCheck`.

### PP-43 — circles at 300% and scrolled
**Steps.** Zoom to 300%, scroll, inspect a circled number.
**Expected.** The ring is still on its number, still legible, not clipped and
not drifting off the numeral.
**Gate.** `TestPublicCircles_StayLegibleAndInPlaceWhenZoomedAndScrolled`,
`TestPublicCircles_AnInPlaceRingIsMeasuredNotAssumed`.

---

## G. The hint

### PP-44 — the three rungs
**Steps.** On a fresh `/play/33fa80994c`, press **Hint** three times.
**Expected.** 1st — a sentence pointing at a row or column, and that line lights
up. 2nd — the same line, with the reason it decides a cell ("every run in this
row is placed", "the N-run must overlap in the middle", or the general form).
3rd — the cell is **marked** (black or white) and named in the sentence, and it
is marked as a hint.
**Gate.** `tests/test_public_player_hint.py::TestPublicHint_RungsOneAndTwoPointAndExplain`,
`TestPublicHint_RungThreeDerivesTheCell`.

### PP-45 — a hint is one undo step and is counted
**Steps.** Watch "Hints: N" across the three presses, then press Undo once.
**Expected.** The count rises **only** on the rung-3 press; one Undo removes the
hinted cell; the count falls back. Reload: the **mark and the count** survive —
the hint flag is in the save, so a reload does not demote a derived cell to a
plain mark. The *highlight* does not survive, and should not: it is view state,
like the lit line and the zoom.
**Gate.** `TestPublicHint_AHintIsOneUndoStep`.

### PP-46 — any mark restarts the ladder
**Steps.** Press Hint once (a line lights), then mark any cell yourself, then
press Hint again.
**Expected.** The lit line and the sentence clear on your mark, and the next
press is **rung 1** again, describing the board as it now is.
**Gate.** `TestPublicHint_TheLadderIsTheModules`.

### PP-47 — exhausted reveals nothing
**Steps.** Reach a board where no single line forces a cell (a puzzle needing a
contradiction probe; or construct one). Press Hint repeatedly.
**Expected.** Every rung says the same sentence — *the clues decide nothing more
by themselves* — and **no cell is ever revealed**. The button stays enabled
while any cell is undecided, because that sentence has to be sayable.
**Gate.** `TestPublicHint_ExhaustedRevealsNothing`.
**Why it matters:** the admin player follows that sentence with a reveal; this
page cannot, because that branch is the one that reads the answer.

### PP-48 — a wrong mark is not called wrong
**Steps.** Mark a cell wrongly (a filled cell where the clues cannot allow one),
then press Hint.
**Expected.** The page does **not** tell you the mark is wrong and shows no error
count. It skips the line your mark contradicts and hints from another line — and
names the line it read. A hint may therefore follow from your wrong mark.
**Gate.** `TestPublicHint_AContradictingLineIsSkipped`.
**Declared, not a defect:** surfacing "this line cannot be right" would be the
error count the owner declined.

### PP-49 — the hint and the other marks coexist
**Steps.** With a line lit by rung 1, hover a cell on that line (mouse), and look
at a hinted cell that is also circled/crossed.
**Expected.** The lit line, the crosshair tint and the hinted cell are each
distinguishable, and all show at once.
**Gate.** `TestPublicHint_ThreeMarksCoexist`,
`TestPublicHint_StayLegibleAndInPlaceWhenZoomedAndScrolled`.
**Also manual:** by eye, on a phone, which is the judgement a ratio cannot make.

---

## H. Saving, resuming, solving

### PP-50 — the save is local and per puzzle
**Steps.** Mark three cells, reload. Open a different puzzle, mark one, go back.
**Expected.** Each board resumes with its own marks and its own undo history.
devtools shows one `nonogram-public:<key>` entry per puzzle and nothing else.
**Gate.** `test_resume_is_local_and_the_page_writes_nowhere`.

### PP-51 — nothing is ever written to a server
**Steps.** Open devtools → Network, filter to XHR/fetch, then play: mark, drag,
undo, reset, zoom, hint.
**Expected.** Exactly **one** request for the whole session — the `GET` of
`puzzle/<key>.json`. No POST, no beacon, no third-party asset, no analytics
(counting is off on this tree).
**Gate.** `test_no_write_request_for_any_interaction`,
`test_the_page_carries_no_answer_and_no_third_party_asset`.

### PP-52 — solving is announced and revealed
**Steps.** Finish a 10×10 easy puzzle (by hand, or by pressing Hint at rung 3
repeatedly).
**Expected.** The "Solved" banner appears, the filled cells flash the success
colour in a **diagonal sweep** ending in ink (about 0.8 s), and the frame reads
as success. Mark one cell wrongly afterwards and the banner goes.
**Gate.** `test_solved_fires_on_clue_satisfaction_only`,
`test_the_empty_mark_is_a_dot_and_solving_is_revealed`.

### PP-53 — reduced motion
**Steps.** Turn on the OS "reduce motion" setting, solve a board.
**Expected.** Banner and success frame appear; **no sweep, no flash**.
**Gate.** the reduced-motion half of `test_the_empty_mark_is_a_dot_and_solving_is_revealed`.

### PP-54 — a tampered save is refused, not replayed
**Steps.** In the console, overwrite the save's clues with another puzzle's, then
reload: `localStorage.setItem("nonogram-public:33fa80994c", "{}")`.
**Expected.** The board draws **blank** rather than replaying somebody else's
marks, and nothing throws.
**Gate.** `test_a_save_or_a_puzzle_file_the_page_cannot_trust_is_refused`.

---

## I. The page has no answer (spot checks a human can make)

### PP-55 — the served puzzle file
**Steps.** Open `https://nonogram.adverax.io/puzzle/33fa80994c.json`.
**Expected.** Exactly five fields — `clues`, `height`, `key`, `tier`, `width`.
**No solution, and no puzzle title**: the title is in no served schema at all.
**Gate.** `test_served_tree_is_clean_of_answers`,
`test_the_picture_name_is_dropped_and_the_books_title_is_not` (the assembled
tree) — **manual-only against production**, which is the point of running it
here.

### PP-56 — the page's own source
**Steps.** View source on `/play/<key>`; search `play.js` for `solution`.
**Expected.** The document carries no puzzle and no answer; the script holds no
solution grid before or after any number of hints. The hint derives from the
clues, which ADR-0041/R2 permits — R2 is a rule about what an asset *carries*
(owner ruling, 2026-11-06).
**Gate.** `TestPublicHint_TheAssetGainsNothing`, `TestPublicHint_TheHeaderClaimIsTrue`.

### PP-57 — the shared module is the panel's, byte for byte
**Steps.** Compare the live file with the panel's:
```bash
curl -s https://nonogram.adverax.io/solver_state.js | shasum -a 256
shasum -a 256 src/nonogram/admin/static/solver_state.js
```
**Expected.** Identical digests (ADR-0041/R3).
**Gate.** `test_the_state_module_and_tokens_are_byte_identical_copies` (against
the assembler) — **manual-only against production**.

---

## J. After a publish (the smoke run)

Run this after every deploy, in order; `docs/deploy/player.md` is the record to
append to.

1. `/library`, one `/play/<key>`, one `/b/<slug>` — all 200, all render (PP-01,
   PP-03, PP-04).
2. PP-55 — the served puzzle file still carries exactly five fields.
3. PP-57 — the module's digest still matches the panel's.
4. One board played to solved on a phone (PP-52), Region armed once (PP-21),
   one pinch (PP-33), one hint ladder (PP-44).
5. Counting: unless the tree was assembled with `--analytics`, the Network panel
   shows **no** third-party request (PP-51).

---

## K. Probe mode — **not on `main` as of 2026-11-06**

CARD-380 is in flight (`card/380-public-probe-mode`); `play.js`, `play.html` and
`player.css` contain no probe code yet. These cases are written from the card's
decided design so the run is ready when it lands; until then every one of them
is **n/a — feature absent**, and that is the expected result.

### PP-60 — a probe is opened and its marks are marked as provisional
Open a probe, mark cells with Black, White and Maybe.
**Expected.** Each cell keeps its ordinary mark **and** gains the probe look —
the admin's **dashed outline**, never a ground tint (owner, 2026-11-06). Cells
marked before the probe carry nothing.

### PP-61 — Contradiction restores the board exactly
With N marks inside a probe over a board B, press Contradiction.
**Expected.** The board equals B cell for cell, the probe closes, no outline
remains.

### PP-62 — Keep commits without touching a cell
Press Keep.
**Expected.** Every cell's mark is unchanged, every outline is gone, the probe
is closed.

### PP-63 — one probe at a time
Press Probe again while one is open.
**Expected.** No second probe opens.

### PP-64 — undo inside a probe, and past its start
Undo repeatedly.
**Expected.** Probe strokes pop first and their outlines clear with them; undoing
past the start leaves the probe **open and empty**, and the next mark belongs to
it; a stroke made before the probe does not come back *inside* it on redo.

### PP-65 — a reload abandons an open probe
With an open probe holding marks, reload.
**Expected.** The pre-probe board, no probe open, the pre-probe undo history
intact — the save never contains probe strokes, and the page says so where the
controls are.

### PP-66 — solving inside a probe commits it
Reach the solved state with probe marks.
**Expected.** The probe commits itself: no outline remains, and the solved banner
behaves exactly as in PP-52 (owner-confirmed, 2026-11-06 — a hypothesis that
reaches the whole picture was correct, because every published puzzle has exactly
one solution).

### PP-67 — the circles see probe marks as marks
**Expected.** The circled set is the same as for the same marks made outside a
probe.

### PP-68 — Reset clears the probe too
**Expected.** Board, history and any open probe, all cleared.

### PP-69 — the four marks coexist on one cell
A probed cell that is also crossed by the crosshair, under a lit hint line, with
a circled clue number.
**Expected.** All of them are visible and tellable apart, at 100% and at 300%,
on a phone. **This is the case the automated bound cannot settle alone**, and a
collision here is a stop-and-report to the owner, not a restyle.

### PP-70 — the controls are reachable and outside the toolbar
**Expected.** None of Probe / Keep / Contradiction is in `.player-toolbar` (the
toolbar's one-row bound is pinned and reds on any new button there), each is at
least 44 px in its touch dimension, and all are reachable at 300% zoom and at a
scrolled offset.

---

## Related

- `docs/how-it-works/01-domain/puzzle-creation/11-the-public-player.md` — how
  each of these features works and why it is shaped that way
- `docs/deploy/player.md` — what is published where, and the publish recipe
- `scripts/preview_player_site.py` — the rewrite-aware local server these cases
  assume
- `meta/architecture/decisions/adr/0041-public-player-static-bundle-and-hash-urls.md`
  — R1..R7, the rules most of the expectations above are restatements of
