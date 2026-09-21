# CARD-044: Fix image preview with persisted uploads (bridges CARD-037, 042, 043)

**Status:** review
**Priority:** P1
**Category:** bugfix
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** red -> green
**Branch:** card/044-preview-with-persistence _(the 2026-09-04 branch of that name is retired as `card/044-superseded-2026-09-04`)_
**Worktree:** ../PythonProject4-CARD-044
**Source:** User testing feedback (wave 3 integration issue)
**Idea:** —
**Wave:** 3
**Depends on:** CARD-037, CARD-042
**Touches:** src/nonogram/web/pages.py (the result page has no preview markup), src/nonogram/web/static/metadata.js, possibly src/nonogram/web/handler.py (a route to serve a retained upload), tests
**Review score:** —
**Started:** 2026-09-21
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** — _(unblocked 2026-09-21 by CARD-037, which built the persistence differently — see the re-cut)_

## Re-cut 2026-09-21 — unblocked, and two of its four criteria no longer fit

CARD-037 landed the persistence this card waited on, but not the shape this
card assumed. There is no `persisted_image_path`, deliberately: the browser
gets an opaque `upload_token` and never a filesystem path, because the salvaged
design's hidden path field accepted any path the client sent. So every
criterion phrased over "the persisted image path" has to be re-read.

### The stated root cause is only half of it

> *Preview display only triggers on file input change events. When form
> re-renders with persisted_image_path, no change event fires → preview
> hidden.*

True, and beside a larger point. **The result page has no preview markup at
all.** `#image-preview-container`, `#image-preview` and `#image-dimensions`
live in `FORM_PAGE` only (pages.py:478-480); `form_with_result` — the page
every submission renders, success or failure — does not carry them.
`metadata.js`'s `displayImagePreview` looks the container up by id and finds
nothing. So the preview is not merely un-triggered after a submission; there is
nowhere for it to appear.

That has to be fixed whichever way the decision below goes, and it is probably
the whole of AC-164.

### AC-165 now contradicts CARD-037

> **AC-165** (clear on error) — *given a previous preview, when generation
> fails and form re-renders with error, then the preview clears.*

That was written when a failed submit destroyed the upload, so a preview left
on screen would have been showing a picture the server no longer had — a stale
preview, exactly as the card says. Since CARD-037 the server **does** still have
it, and the retry is the point. Clearing the preview on failure would now show
the owner an error and no picture, while the file sits in the store waiting to
be reused.

The criterion should be inverted — the preview **survives** a failure, because
the picture does — or retired. It cannot stand as written.

## The decision this card needs (for the owner)

AC-163 asks for the preview to appear on page load after a submission. The
browser holds a token, not an image, and cannot turn one into the other.

- **(a) Serve the retained upload by token.** A route — `GET /upload/<token>`
  — returns the file the token stands for, and `form_with_result` carries the
  preview container pointing at it. The token is already unguessable and
  resolves only to a file this process retained for this visitor, so it gives
  away nothing they did not just send. Small, and it makes AC-163 true as
  written.
- **(b) Retire AC-163.** No preview after a submission; it appears only when a
  file is chosen. The form still says which picture is held — a line of text
  naming it — without the server serving image bytes back at all.

**Recommendation: (a).** The retry is worth little if you cannot see what you
are retrying with, and a card whose entire subject is "the preview after a
failed submit" that answers "there isn't one" has not earned its P1. The route
is a dozen lines and the security question is already settled by the token.

## What to implement

The image preview (CARD-042) doesn't work with persisted uploads (CARD-037). When a user generates and gets an error, then selects a new image (or same image), the preview doesn't appear. 

**Root cause:** Preview display only triggers on file input change events. When form re-renders with persisted_image_path, no change event fires → preview hidden.

**Fix:** Refactor preview display logic to work on both file input change AND on page load when persisted image exists.

**Also fix:**
- Clear preview when form errors occur (prevent stale previews with error state)
- Integrate with CARD-043 (clear messages on new upload)

## Acceptance criteria

- **AC-163** (preview on page load) — given a persisted image in a form re-render, when the page loads, then the preview displays immediately (no file change needed).
  *test:* `TestWebUI_ShowsPreviewOnLoadWithPersistedImage`

- **AC-164** (preview on re-select) — given an error message and persisted image, when the user selects a new image, then the preview updates.
  *test:* `TestWebUI_UpdatesPreviewOnReselect`

- **AC-165** (clear on error) — given a previous preview, when generation fails and form re-renders with error, then the preview clears.
  *test:* `TestWebUI_ClearsPreviewOnGenerationError`

- **AC-166** (clear on new file) — given an error state, when user selects a new image, then both preview updates AND error message clears.
  *test:* `TestWebUI_ClearsErrorAndShowsNewPreview`

## Guardrails

- G-1: Preview works with persisted image path (file input hidden)
- G-2: No JavaScript errors if preview or persisted elements missing
- G-3: File input re-selection works (same file twice in a row)
- G-4: Doesn't break existing CARD-042 preview functionality

## Architecture context

- **FR:** FR-017
- **NFR:** NFR-003
- **ADR:** ADR-0020
- **Components:** COMP-008
- **Trace:** meta/architecture/trace.yml

## Worktree notes

**2026-09-10 — reverted from a false "done" state; this card is NOT actually
done on `main`.** The card previously claimed `Status: completed`,
`Merge commit: 1c6ed74`, `Closed: 2026-09-04T10:36:00Z` — all from a close-out
that happened on a git history with **no common ancestor with current `main`**
(`git merge-base main card/044-preview-with-persistence` returns nothing;
`git cat-file -t 1c6ed74` confirms the commit object exists but
`git log --oneline main | grep 1c6ed74` finds it on no branch reachable from
`main`). The implementation summary below is real work that happened — it is
kept as historical record — but it never reached the codebase that is
actually being developed on.

Checked directly: `main`'s current `src/nonogram/web/static/metadata.js` and
`pages.py` have **no** `persisted_image_path` field, no
`initializePersistedPreview()`, and no `TestWebUI_PreviewWithPersistence` test
class — none of this card's specific deliverable survived the `96da6ac` bulk
restore that brought its sibling cards' work back (CARD-038/039/040/041/042
were reconciled as done against that restore; this one's feature simply wasn't
in the backup being restored, or predates it).

Reverted to `ready`. Since CARD-037 (this card's other dependency) is also
confirmed not done on `main` (see its own notes), **this card cannot usefully
start until CARD-037 is re-implemented against current `main`** — the
persistence mechanism this card bridges into the preview doesn't exist yet
either.

A stray worktree exists on disk at `../PythonProject4-CARD-044` (pointing at
the orphaned `1c6ed74`/`2f40540`) — should be removed; left untouched pending
explicit confirmation.

### Implementation summary

Refactored metadata.js preview display logic:

1. **Extracted showImagePreview(metadata)** — reusable function that displays preview with given metadata (width, height, imageSrc)
2. **Added clearPreview()** — hides preview container when generation fails
3. **Added clearResultMessage()** — clears error/success messages when new image selected (CARD-043 integration)
4. **Added initializePersistedPreview()** — runs on page load to show preview if persisted image path exists
5. **Updated displayImagePreview()** — now calls showImagePreview() internally after FileReader completes
6. **Integrated with file change event** — now calls clearResultMessage() when new image selected

### Form updates

- Added `persisted_image_path` hidden field to both FORM_PAGE and form_with_result (CARD-037 integration)
- Added preview container elements to initial FORM_PAGE (AC-163)
- Updated test expectations for new form field

### Testing

- Added 7 new tests in TestWebUI_PreviewWithPersistence class verifying all ACs
- All 160 tests pass including new functionality
- Updated existing test to account for persisted_image_path field in form options

### Delivered 2026-09-21

**The result page carries the preview block.** That was the half the card
missed: `#image-preview-container` and its siblings were in `FORM_PAGE` only,
so after any submission `metadata.js` was looking up an element that did not
exist. `form_with_result` now emits the same block, and when an upload is
retained the `<img>` already has its `src` — **the picture is on screen before
any script runs**, which is a better answer than the card's "no change event
fires" framing suggested.

**`GET /upload/<token>`** serves the retained picture. It resolves through
`nonogram.web.uploads`, so it answers for nothing this process minted: a token
that never existed, one whose submission has since succeeded, and a filesystem
path handed in a token's place are all 404. There is no path arithmetic to get
wrong — the token is a dict key, not a name — which is why `../../etc/passwd`
and its percent-encoded twin are uninteresting rather than dangerous, and are
tested as such.

**The media type is read from the file's own first bytes.** A retained upload
has no extension (`tempfile.mkstemp` names it `nonogram-upload-XXXXXX`), so the
file is the only thing that knows; anything unrecognised is served as
`application/octet-stream`, which a browser declines to render. Nothing the
client said about the file is consulted, for the same reason the retry trusts a
token over a name.

### AC-165 is inverted, and the card explains why

It asked that the preview **clear** when generation fails. That was right when
a failed submit destroyed the upload — the preview would have been showing a
picture the server no longer had. CARD-037 keeps it, so clearing it would now
show an error and no picture while the file waits in the store to be reused.

The tests pin the inversion: a second failure still shows the picture, a
success shows none (the retention ended and the route 404s), and an
**undecodable** upload shows none either — CARD-037 releases a picture that can
never work, and the preview goes with it.

### AC-163's decision

Option (a), the owner's pick: serve the retained upload by token, rather than
retiring the criterion or naming the file in text. The retry is worth little if
you cannot see what you are retrying with.

### Tests

`tests/test_card_044_preview_after_submit.py`, 12 tests: the markup's presence,
the `src` pointing at the token, the bytes coming back intact with
`Content-Type: image/png`, a fresh `GET /` still starting empty, the three
survives/does-not-survive cases above, and five on the route refusing what it
never minted.

**Full suite: 3,644 passed, 0 failed.**

### The escaping guard, a third time

53 interpolations now — the same number it held before CARD-104, reached by a
different route, which the test's docstring says plainly so nobody reads it as
a restoration. Three new unescaped names classified: `preview_src` (built from
the already-escaped `token_val`), `preview_visible.strip()` (a class literal or
empty), and `preview_block` (the fragment built from both). That guard has now
caught three consecutive cards' changes to this module.
