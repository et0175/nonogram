# CARD-037: Persist uploaded image for retry without re-upload

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/037-persist-upload-retry
**Worktree:** —
**Source:** User feedback during wave 0–2 testing
**Idea:** —
**Wave:** —
**Depends on:** CARD-031
**Touches:** src/nonogram/web/handler.py, src/nonogram/web/submission.py, src/nonogram/web/pages.py, tests/test_web_server.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Re-cut 2026-09-21 — the work is salvaged, and it must not be re-applied as written

**The feature is still not on `main`.** `persisted_image_path` appears nowhere
in `src/`. Confirmed again today, not inherited from the 2026-09-10 note.

**The patch this card pointed at had evaporated.** The note below names
`/private/tmp/claude-501/…/7153fc65-…/scratchpad/CARD-037-uncommitted-work.patch`
as the preserved copy and says "do not force-remove until the patch is
confirmed". That file no longer exists — the scratchpad belonged to a session
that has since been cleaned up — so for some time the only copy of this work
was the uncommitted diff in a worktree everyone kept meaning to tidy away.

It is now saved as **`meta/ops/CARD-037-uncommitted-work-20260921.patch`**, in
git, where it cannot evaporate. 70 lines: `handler.py` (+22), `pages.py` (+1),
`tests/test_web_server.py` (+48, four tests including
`test_persisted_image_path_preserved_on_resubmit` and
`test_persisted_field_clears_after_success`).

### The salvaged design has a hole, and that is why it is a rebuild

```python
if image_path is None and "persisted_image_path" in fields:
    persisted_list = fields.get("persisted_image_path", [])
    if persisted_list and persisted_list[0]:
        persisted_path = Path(persisted_list[0])
        if persisted_path.exists() and persisted_path.is_file():
            image_path = persisted_path
```

`fields` is the submitted body — `multipart.read`'s text parts, or `parse_qs`
of a urlencoded body. Every one of its values is chosen by whoever sent the
request. So this accepts **a filesystem path from the client** and, if the file
exists, opens it as the picture to convert.

That is an arbitrary-file-read primitive: a crafted POST naming any readable
path on the server is accepted, and any readable *image* is converted into a
puzzle and handed back. The failure is also a disclosure — "this path exists
and is an image" is distinguishable from "it does not".

The same hazard was rejected deliberately elsewhere in this adapter: a
urlencoded `image=<path>` field is **not** read as a picture, precisely so a
form cannot name a server-side path (recorded in CARD-032's AC-130 test). This
patch reintroduces it under a different field name.

**So the retry mechanism must not round-trip a path.** The rebuild should hand
the browser an **opaque token** — a random id the server maps to the temp file
it already holds — so a returned value can only ever name a file this session
uploaded. The client never learns or supplies a path.

### The branch is retired

`card/037-persist-upload-retry` was 499 commits behind `main`, last commit
`feat(CARD-039)` from early September, on the same orphaned line as every other
superseded branch. Retired as `card/037-superseded-2026-09-04`; the worktree is
removed. The salvaged patch is the inheritance, not the branch.

### What the salvaged tests are worth

More than the implementation. They state what the feature has to do — the path
survives a failed submit, and is cleared after a success — and those statements
are design-independent. Read them, keep their intent, and write them against
whatever the token mechanism turns out to be.

## What to implement

When a user uploads an image and encounters an error (invalid ratio, too many retry attempts, etc.) or wants to regenerate with different settings (size, difficulty, name), they currently must re-upload the image. This creates friction and a poor UX.

Instead, keep the uploaded temp file available across retry attempts, allowing the user to:
1. Upload image once
2. Adjust size/difficulty/name/output-directory
3. Resubmit form without re-uploading
4. If error, repeat steps 2–3

**Technical approach:**
- Store temp file path in session/form state (hidden field or cookie)
- Check if resubmission references an existing temp file
- Reuse temp file for subsequent generation attempts
- Clean up after success OR after max retry attempts exceeded
- Validate temp file still exists before reuse

## Acceptance criteria

- **AC-143** (persist) — given an uploaded image and a generation error, when the form is re-rendered with inline error, then the temp file is retained and available for retry.
  *test:* `TestWebUpload_PersistsImageAcrossRetries`

- **AC-144** (reuse) — given a persisted temp file and a form resubmission with different size/difficulty, when the form is submitted, then the same image file is used for generation without requiring a new upload.
  *test:* `TestWebUpload_ReusesPersistedImageOnRetry`

- **AC-145** (cleanup) — given a successful generation or max retry attempts exceeded, when the session ends, then the temp file is deleted (no orphaned files).
  *test:* `TestWebUpload_CleansUpAfterSuccess`

- **AC-146** (validation) — given a persisted temp file reference, when the form is submitted, then the system validates the file still exists and is readable before reuse (handles race conditions).
  *test:* `TestWebUpload_ValidatesPersistedFileStillExists`

## Guardrails

- G-1: No new runtime dependencies
- G-2: Temp file cleanup happens even on errors or aborted requests
- G-3: Persisted file reference validated before reuse (security)
- G-4: Max file persistence time enforced (prevent disk space issues)

## Architecture context

- **FR:** FR-017 (web UI)
- **NFR:** NFR-003
- **ADR:** ADR-0019, ADR-0020, ADR-0021
- **Components:** COMP-008 (web UI)
- **Trace:** meta/architecture/trace.yml

## Worktree notes

**2026-09-10 — investigated as part of reconciling CARD-038/039/040/041/042/044
against `main`.** Unlike its siblings, this card is genuinely **not done** —
staying `ready`, not being closed.

Its branch (`card/037-persist-upload-retry`) exists but never received an
actual `feat(CARD-037)` implementation commit (`git log --all` finds none
anywhere in the repository) — the branch tip (`5c5ae5e`) turned out to be
CARD-039's commit, landed here by an apparent worktree/checkout mixup at
implementation time (see CARD-039's own notes), not this card's own work.

`main`'s current `src/nonogram/web/*.py` has no `persisted_image_path` field,
no session/hidden-field temp-file reuse across retries, and no test for it —
confirmed by grep, none of the `96da6ac` bulk restore's files carried this
feature in either. `CARD-044`'s branch (a different, later card) did add a
`persisted_image_path` hidden field and `initializePersistedPreview()` as part
of *bridging* this card with the preview feature — but that specific piece
also did not survive into `main` (see CARD-044's notes) — so there is nothing
to reconcile here; this is real, outstanding work.

A stray worktree exists on disk at `../PythonProject4-CARD-037` (pointing at
the orphaned `5c5ae5e`, i.e., CARD-039's commit, not this card's) — it should
be removed before starting fresh, since a normal `start CARD-037` would create
a new worktree off current `main` anyway.

**2026-09-11 — update: the worktree is NOT clean, and removal was correctly
refused.** `git worktree remove` on this path fails (`fatal: ... contains
modified or untracked files`) because it holds **real, substantive, never-
committed implementation work** for this exact card:
`src/nonogram/web/handler.py` (persisted-path reuse + conditional cleanup on
success/error), `src/nonogram/web/pages.py` (the `persisted_image_path` hidden
field), and `tests/test_web_server.py` (4 new tests, `TestWebForm_ImagePersistence`,
covering AC-143/144/145/146). This is meaningfully further along than "never
implemented" — it was implemented and simply never committed before the
history split.

**Preserved** at
`/private/tmp/claude-501/-Users-omelnikova-PycharmProjects-PythonProject4/7153fc65-6545-4f37-8efc-99569009eea7/scratchpad/CARD-037-uncommitted-work.patch`
(124 lines) before any further action, so it survives regardless of what
happens to this worktree.

**Not applied to `main` as-is** — it's written against the old lineage's
`handler.py` structure (variable names `image_path`/`media_type`/`fields` at
specific call sites); `main`'s current `handler.py` should be diffed against
this patch before reuse to confirm it still applies cleanly or needs
adaptation. Treat this as a strong starting draft for CARD-037's real
implementation, not a drop-in patch.

The worktree itself (still holding this uncommitted diff) is left in place —
removing it now would require `--force` and would discard this work with no
recovery beyond the preserved patch file. Do not force-remove until the patch
has been reviewed/reapplied against current `main`.
