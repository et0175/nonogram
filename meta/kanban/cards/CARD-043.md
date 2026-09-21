# CARD-043: Clear error/success message when new image is uploaded

**Status:** done
**Priority:** P2
**Category:** ux-polish
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** red -> green -> mutation check (5 mutants, all caught — two only after the tests were fixed)
**Branch:** card/043-clear-message-on-upload
**Worktree:** ../PythonProject4-CARD-043
**Source:** User feedback during wave 3 testing
**Idea:** —
**Wave:** 3
**Depends on:** CARD-038, CARD-041
**Touches:** src/nonogram/web/static/metadata.js
**Review score:** — _(merged without a review cycle, at the owner's call)_
**Started:** 2026-09-21
**Closed:** 2026-09-21
**Actual:** 0.25d
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

### Delivered 2026-09-21

**`clearResultMessage()` in `metadata.js`**, called from **both** change
listeners — the File API path and the no-File-API fallback. Both are "the user
picked a different picture", and the stale result goes at that moment rather
than waiting for the submit CARD-038 already handles.

**Paired with the picture.** The clear sits beside `clearMetadata()` in the
change path, because since CARD-037 a failed submission keeps its picture and
CARD-044 puts it on the page. Removing the message alone would strand the
previous preview beside a form claiming nothing had happened.

**The stale `upload_token` is left alone, deliberately.** Verified rather than
assumed: the handler prefers a newly uploaded file and only resolves the token
when none arrived (`handler.py:772`), so a new choice already wins. Clearing
it would be invented work.

### The mutation check found two flaws in the tests, not the code

Both tests passed, both would have kept passing through a regression:

* **`data-result-container` appears twice in the page** — once as the
  element's attribute and once inside the page's own inline script, which
  queries it. Asserting the bare name passed even with the container renamed
  away. Fixed to assert `data-result-container="true"`, the rendered attribute.
* **The handler regex matched both listeners as one span.** The first
  listener's closing brace is indented differently from the pattern, so the
  non-greedy match ran from the first listener's opening to the *second*
  listener's close and reported a single handler containing both bodies. A
  mutant that removed the call from the path that actually runs still passed,
  because the fallback's call was inside the same captured text.

The second was replaced with a **count of call sites** rather than a cleverer
regex. A count cannot be fooled the way the regex was, and it is honest about
being a count: the test says in as many words that it cannot prove the listener
fires, and points at CARD-105 for the harness that could.

### Tests

`tests/test_card_043_clear_message_on_new_image.py`, 5 tests: the container
present on both the fresh form and the page a submission renders, the clear
wired at both listeners, the message and picture dealt with together, the
guard for a page without the container, and the server-side half of AC-162 —
a page carries exactly one outcome, so a result cannot accumulate even with no
JavaScript at all.

**Full suite: 3,672 passed, 0 failed.** `node --check` validates the script.
