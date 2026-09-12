# CARD-067: Preview cards — picture left, name and ink ratio right; live predicted output; remove a picture

**Status:** in_progress
**Priority:** P2
**Category:** feature
**Estimate:** 0.75d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/067-preview-card-redesign
**Worktree:** ../PythonProject4-CARD-067
**Source:** owner, 2026-09-12, items 1-3 of the admin console review ("put image preview to the left of the cards, puzzle name and add an aspect ratio to the right"; "when we change size, we need to update «Predicted output»"; "possibility to remove a picture from the job")
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/admin/templates/image_preview.html, src/nonogram/admin/app.py (a prediction endpoint and a remove route), src/nonogram/admin/image_manager.py (only if the ink ratio needs a helper — `remove_image` already exists), tests
**Review score:** —
**Started:** 2026-09-12T05:03:53Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why

Three complaints about **Batch: Preview Images & Select Sizes**:

1. The card stacks the picture above the name and the controls, so a batch
   of 20 is a lot of scrolling and the picture is small.
2. **The predicted output is stale.** It is rendered server-side; the page's
   JavaScript only shows or hides the size field (`updateSize`), so changing
   the mode or the value leaves the old prediction on screen until the page
   is saved and re-rendered. The number the user reads is then wrong — and
   since CARD-064 it also carries the "moved to Large" or "will be skipped"
   note, which is wrong with it.
3. There is no way to drop a picture from the job *in the UI*.
   `ImageManager.remove_image(file_id)` already exists
   (`image_manager.py:465`); no route calls it and no control offers it.

## What to implement

1. **Card layout.** Picture on the left, larger; on the right the puzzle
   name, the aspect ratio, the size controls and the predicted output. Keep
   it responsive (the page uses Bootstrap's grid; the cards are `col-md-6`).
2. **Aspect ratio = the ink bounding box** (owner's choice, 2026-09-12):
   the ratio the sizing actually uses (`ImageFile._source_shape()`), so the
   card explains the predicted size instead of contradicting it. Show it as
   a ratio, e.g. "1.54:1", with the box in pixels available on hover
   (`title`). A degenerate `(0, 0)` shape must not divide by zero — show
   "—".
3. **Live predicted output.** Add a read-only endpoint that answers "what
   would this size give for this picture?", e.g.
   `GET /api/image/<file_id>/predicted?mode=<fixed|short|min|max>&value=<n>`,
   returning the extent, the fit status, the chosen extent and the note
   text. The page calls it when the mode or value changes and replaces the
   predicted output and any note.
   - **The sizing rule must not be reimplemented in JavaScript.** CARD-063
     and CARD-064 exist because the range and the fit rule had drifted into
     copies; the endpoint keeps one source of truth. The JS only renders
     what it is given.
   - It is a preview: it must not change the stored configuration.
4. **Remove a picture.** The store method already exists
   (`ImageManager.remove_image`); this card adds the POST route and the
   control on the card. Check what `remove_image` does with the uploaded
   temp file and, if it leaves it behind, decide deliberately whether to
   delete it here or leave that to `clear_all`. Removing the last picture
   should land on the same "no images" path the page already has, not a
   broken page.

## Acceptance criteria

- **AC-1** — the rendered card has the picture on the left and the name,
  ratio, controls and predicted output on the right, and the page still
  renders with one picture, with twenty, and with a picture whose file is
  missing (the existing `onerror` placeholder path).
- **AC-2** — the ratio shown equals the ink bounding box's ratio for a
  picture with real margin (a fixture where the file ratio and the ink ratio
  differ), and reads "—" for a degenerate `(0, 0)` picture.
- **AC-3** — the prediction endpoint returns, for the same inputs, exactly
  what the page would render after a save: extent, status and note, for
  every mode, including a picture that moves to Large and one that cannot
  fit. Asserted against `ImageFile.size_fit()` rather than restated numbers.
- **AC-4** — the endpoint does not mutate state: the stored `size_mode` and
  `size_value` are unchanged after a call, and a later save still uses what
  the form posts.
- **AC-5** — removing a picture drops it from the job (gone from the page
  and from `get_all_images()`), leaves the others untouched, and removing
  the last one leaves a working page.
- **AC-6** — no sizing arithmetic in `metadata.js` or the page's inline
  script: a test greps the admin JS/templates for the giveaways (`derive`,
  `MIN_SIZE`-like literals, a short-side formula) and fails if the rule is
  duplicated.

## Guardrails

- G-1: No change to what size a picture gets. `size_fit()`,
  `MIN_KEPT_SHARE`, `SIZE_PRESETS` and `predict_size()` behave exactly as
  they do now; this card changes presentation, adds a read-only endpoint and
  adds removal.
- G-2: Do not reintroduce 10/30 (or any bound) as a literal in a template or
  in JavaScript — `nonogram.limits` is the one source (CARD-063).
- G-3: Keep CARD-064's statuses and wording: the moved-to-Large note, the
  skip message and the placeholder instead of a misleading crop.
- G-4: Admin-only; no edits under `sourcing/`, `orchestrator.py`, `cli.py`
  or the web adapter.

## Worktree notes

[Env] forge 2026.8.17 (no `meta/.skills.yml`, so no min_version comparison).
Built on `e6a5cd5`. CARD-066 is in review on its own branch and also touches
`app.py`, in a different route; `main` gets merged in here before this
card's own merge.

**One wording, two consumers.** The predicted size and its note moved from
Jinja into Python — `size_text(fit)` and `fit_note(fit)` in
`image_manager.py` — because the page and the new endpoint would otherwise
each spell the same sentence. `fit_note` returns `None` when the size fits,
else `{"level": "warning"|"danger", "text": ...}`. The wording is CARD-064's,
unchanged (G-3): the CARD-058/061/064/065 assertions on those sentences
still pass.

**Card layout (AC-1).** The card body is a row: `col-5` picture (the
existing cropped preview, or the skip placeholder), `col-7` name, ratio,
size controls, predicted output and a Remove button.

**Ink ratio (AC-2).** `ImageFile.ink_ratio()` → e.g. `"2.00:1"`, with
`ink_box()` (`"200×100 px"`) in the `title`. Both read `_source_shape()`,
so the ratio explains the predicted size rather than contradicting it; a
degenerate picture gives `"—"` and `"unreadable"`.

**Live prediction (AC-3/AC-4).** `GET /api/image/<file_id>/predicted?mode=&value=`
builds a throwaway `dataclasses.replace` copy (carrying the cached source
shape, so no re-decode), runs `size_fit()` on it and returns the extent,
status, size text and note. It never touches the stored configuration. An
unknown picture is 404; an unknown mode or a non-numeric value is 400.
`updateSize()` calls it on every change and writes the answer into the page.

**No sizing in JavaScript (AC-6).** The script sets text from the endpoint's
answer; a test greps the page's script for arithmetic giveaways and for
`/predicted`. This is the CARD-063/064 lesson applied: a copy of the rule in
JS would drift.

**Remove (AC-5).** `POST /batch/image/<file_id>/remove` calls the existing
`ImageManager.remove_image`, which already deletes the temp file, then
returns to the preview page — which, when the batch is empty, already
redirects to the upload page. The card's open question about the temp file
is answered: the store deletes it, nothing extra needed.

**Tests** — `tests/test_card_067_preview_cards.py`, 16 tests: layout order,
many pictures and a missing file, the ink ratio against a picture with a
margin (file 4:3, ink 2:1) and a degenerate one, endpoint parity with
`size_fit()` across all four modes plus moved-to-Large and cannot-fit,
no-mutation, 404/400 handling, page-and-endpoint wording parity, removal of
one picture, of the last picture, and of an unknown id, and the
no-arithmetic-in-JS grep.

**Runs**: the new file plus the CARD-047/058/061/062/063/064/065 tests,
`test_image_batch_size_fix`, `test_wave3_e2e`,
`test_wave3_image_generation`, `test_admin_image_uniqueness`,
`test_puzzles_list_pagination` and the import guard: 203 passed, 20 skipped.
Red check: against `main`'s `src/` the module cannot import `fit_note`.
Diff: 3 source files (+58 app, +58 image_manager, template restructured) and
the new test file. Commit `7ea0341`.

[Review 1/3] Score: 5.5 — crit: 0, imp: 3, minor: 3
[Review sync] 1 report(s) → meta/review/ (20260912T052045Z-CARD-067-cycle1.yml)
Cycle 1 summary: AC-1, AC-2, AC-4, AC-5 (in code), AC-6 and G-1..G-4 held;
AC-3 violated. Below the pass bar — three Important findings, all real:

1. **The endpoint and a save disagreed on an out-of-range value.**
   `_own_extent` *clamps* (`short&value=5` → short side 10); a save
   *silently ignores* anything outside MIN_SIZE..MAX_SIZE and keeps the
   stored value. So for a 300×200 picture stored at 20, the card predicted
   15×10 while saving that same form produced 30×20. Reachable in the
   browser, not a theoretical case: the page's submit handler calls
   `preventDefault()`, so the number input's `min`/`max` never validate and
   out-of-range values really are posted. My AC-3 test missed it by
   assigning `size_mode`/`size_value` directly instead of POSTing the form —
   the assignment bypassed the very validation that diverged.
2. **The live prediction had no request sequencing** — last *response* won,
   not last request. `applyToAll()` dispatched `change` on the mode select
   and then on the value input, so every card always had two requests in
   flight and the first carried the *old* value. Whichever landed last won,
   and a wrong number stuck until the card was touched again. This is the
   card's own complaint #2 reappearing in a new form.
3. **The AC-5 test could not distinguish correct removal** from "always
   remove `get_all_images()[0]`" — it removed the first of two pictures.
   Mutation confirmed: the mutant survived, 126 passed.

Minors: `size_text`'s "skipped" was pinned by nothing (the page↔endpoint
parity assertion is tautological — both call `size_text`); the error path
left the stale number sitting under "Could not refresh"; `int()` accepts
`-5`, `１２`, `" 20 "` and 10²⁰.

[Fix delta after cycle 1]
- **One rule, two callers.** `accepted_size_value(mode, value, current)` in
  `image_manager.py` is now the single answer to "what value would a save
  store?" — out of range, or an automatic mode, keeps the stored value.
  `ImageManager.update_image_size` applies it and the endpoint applies it,
  so the two cannot drift. This is the same move as `size_text`/`fit_note`
  earlier in this card, applied to the input side.
- **Request sequencing.** `refreshPrediction` takes a ticket per card and
  drops its answer if a newer request has started; `applyToAll` sets both
  fields and asks *once* instead of dispatching two changes. The error path
  now clears the number to "—" as well, since leaving the old one under
  "could not refresh" reads as a prediction for the new setting.
- **Tests**: AC-5 is parametrized over all three positions (first, middle,
  last), which kills the "always remove [0]" mutant; a new AC-3 test asks
  the endpoint and then POSTs the same out-of-range value through the real
  save route, comparing the answer with the resulting `size_fit()`; a direct
  pin on both `size_text` branches; and an AC-6 test for the sequencing
  guard and the single `updateSize` call in `applyToAll`.
The `int()` minor is answered by the parity fix rather than by more
validation: `-5` and 10²⁰ now behave exactly as a save behaves (stored value
kept), which is the property that matters. A full-width `１２` still parses
as 12, harmless and identical on both paths.

Delta commit `ac6db6d`; the card's own file: 25 passed. Mutation check in a
scratch copy (the worktree untouched), all four **killed** — including the
two the reviewer ran and found surviving:
- the remove route always dropping `get_all_images()[0]` (M4, survived at
  cycle 1);
- `size_text` answering "n/a" instead of "skipped" (M6, survived at cycle 1);
- the endpoint dropping `accepted_size_value` — the divergence itself;
- `refreshPrediction` losing its stale-answer guard.

`main` (carrying CARD-066, which also touches `app.py`) merged into this
branch before its own merge, as the Env note planned — no conflict, the two
routes are far apart. The card's file plus CARD-066's and the
CARD-061/063/064/065, pagination and import-guard suites: 239 passed.