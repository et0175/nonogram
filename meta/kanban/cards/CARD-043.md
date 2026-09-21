# CARD-043: Clear error/success message when new image is uploaded

**Status:** ready
**Priority:** P2
**Category:** ux-polish
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/043-clear-message-on-upload
**Worktree:** —
**Source:** User feedback during wave 3 testing
**Idea:** —
**Wave:** 3
**Depends on:** CARD-038, CARD-041
**Touches:** src/nonogram/web/static/metadata.js
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Re-cut 2026-09-21 — and unlike its siblings, this one is genuinely undone

Checked against `main` at `77c15bf`. Every other card of this family turned out
to have shipped while sitting in Ready. **This one has not.**
`src/nonogram/web/static/metadata.js` contains no `clearResultMessage`, and
never mentions `data-result-container`. Its file-change listener clears the
metadata area and the size field (CARD-149) and nothing else.

### What already exists, and why it is not this

`pages.py` carries a script — CARD-038's — that empties
`[data-result-container]` when the form is **submitted**:

```js
form.addEventListener('submit', function() {
  const resultContainer = document.querySelector('[data-result-container]');
  if (resultContainer) resultContainer.innerHTML = '';
});
```

That fires at submit. This card is about the moment **before** it: the user has
an error on screen, picks a different picture, and the stale message should go
then — while they are still deciding what to change — not when they finally
press Generate.

### What changed underneath it since it was written

CARD-037 and CARD-044 landed after this card was drafted, and the page it
describes is no longer the page it was:

* A failed submission now **keeps its picture**, and the result page shows it
  (`GET /upload/<token>`).
* Selecting a new file must therefore leave the two in step: the message goes,
  and CARD-044's change-listener preview replaces the old picture. It would be
  wrong to clear the message and leave the previous picture on screen.
* The stale `upload_token` in the hidden field is **not** a problem — the
  handler prefers a newly uploaded file and only resolves the token when no
  file arrived (`handler.py:772`). Verified, so the card does not need to clear
  it, and should not pretend otherwise.

## What to implement

When a user uploads a new image, clear any previous error/success messages from the form. This prevents confusing the user with stale result messages from a previous generation attempt when they're about to try again with a new image.

**Flow:**
1. User generates puzzle → success/error message displays
2. User selects new image → message clears immediately (since they're starting fresh)
3. User adjusts settings + submits → new result displays

**Implementation:** In `metadata.js` file change listener, clear the result message container when new image selected.

## Acceptance criteria

- **AC-161** (clear on upload) — given a user who sees an error/success message, when they select a new image file, then the message is cleared.
  *test:* `TestWebUI_ClearsMessageOnNewImageUpload`

- **AC-162** (fresh start) — given a cleared message and new image, when the user adjusts settings + resubmits, then only the new result displays (no mixing).
  *test:* `TestWebUI_FreshMessageAfterNewUpload`

## Guardrails

- G-1: Only clear message when new image selected (not on form field changes)
- G-2: No JavaScript errors if result container missing
- G-3: Message clearing doesn't interfere with form persistence (CARD-037)

## Architecture context

- **FR:** FR-017
- **NFR:** NFR-003
- **ADR:** ADR-0020
- **Components:** COMP-008
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—
