# CARD-067: Preview cards — picture left, name and ink ratio right; live predicted output; remove a picture

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 0.75d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/067-preview-card-redesign
**Worktree:** —
**Source:** owner, 2026-09-12, items 1-3 of the admin console review ("put image preview to the left of the cards, puzzle name and add an aspect ratio to the right"; "when we change size, we need to update «Predicted output»"; "possibility to remove a picture from the job")
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/admin/templates/image_preview.html, src/nonogram/admin/app.py (a prediction endpoint and a remove route), src/nonogram/admin/image_manager.py (only if the ink ratio needs a helper — `remove_image` already exists), tests
**Review score:** —
**Started:** —
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
