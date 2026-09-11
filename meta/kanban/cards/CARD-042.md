# CARD-042: Display image preview after upload

**Status:** done
**Priority:** P2
**Category:** enhancement
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/042-image-preview
**Worktree:** —
**Source:** User testing feedback (wave 3)
**Idea:** —
**Wave:** 3
**Depends on:** CARD-032 (image-only form)
**Touches:** src/nonogram/web/pages.py, tests/test_web_server.py
**Review score:** —
**Started:** —
**Closed:** 2026-09-08T10:59:21+03:00
**Actual:** n/a — reconciled, see Worktree notes
**Merge commit:** 96da6ac
**Blocked by:** —

## What to implement

Display a small thumbnail preview of the uploaded image below the file input field, helping users confirm they selected the correct image before generation.

The preview should:
1. Appear immediately after file selection (client-side, via File API)
2. Display a downsampled thumbnail (max 150x150 px or similar)
3. Include the original image dimensions label (e.g., "2048×1536")
4. Remain visible until a new image is uploaded (consistent with CARD-037)
5. Work client-side (no server round-trip needed)

## Acceptance criteria

- **AC-158** (preview display) — given a user who selects an image file, when the file is selected, then a thumbnail preview appears below the file input showing the image scaled to fit a 150×150 box.
  *test:* `TestWebForm_ShowsImagePreviewOnUpload`

- **AC-159** (dimensions label) — given the preview is displayed, when it renders, then it shows the original image dimensions (e.g., "2048×1536") in a caption or alt text.
  *test:* `TestWebForm_PreviewShowsOriginalDimensions`

- **AC-160** (persistence) — given a preview is shown for image A, when the user selects image B without clearing, then the preview updates to show image B (and the dimensions label updates).
  *test:* `TestWebForm_PreviewUpdatesOnNewUpload`

- **AC-161** (client-side) — the preview is generated using the File API (FileReader.readAsDataURL or equivalent) with no server interaction.
  *test:* `TestWebForm_PreviewIsClientSide` (or code inspection)

## Guardrails

- G-1: Use FileReader (or equivalent File API) client-side only — no server processing for preview
- G-2: Preview size capped at 150×150 px to avoid layout bloat
- G-3: Preview persists across form interactions (consistent with CARD-037's image persistence)
- G-4: No new runtime dependencies (use browser's native File API)

## Architecture context

- **FR:** FR-017 (web UI)
- **NFR:** NFR-003 (UX polish)
- **ADR:** ADR-0019 (adapter scope)
- **Components:** COMP-008 (web UI)
- **Trace:** meta/architecture/trace.yml

## Worktree notes

**2026-09-10 — reconciled against `main`, not merged normally.** Same
disconnected-history situation as the rest of this wave. This card's own
branch (`card/042-image-preview`) carries a real implementation commit
(`5164238 "feat(CARD-042): Add client-side image preview on file upload"`),
but on a history with no path to current `main`.

`main`'s `src/nonogram/web/static/metadata.js` already has the thumbnail
preview this card specifies — a 150×150 box, original-dimensions label,
appearing on file selection (`showImagePreview()`, `image-preview-container`/
`image-preview` elements) — brought in by the same `96da6ac` bulk restore.
Verified present on current `main`; closing as done with `96da6ac` as the
merge commit.

Note for CARD-044: the *selection-time* preview (this card) works on `main`,
but the *persisted-on-page-reload* preview CARD-044 was specifically about did
NOT survive into `main` — see that card's own Worktree notes.

No orphaned worktree for this card (`Worktree: —` already) — only the branch
is orphaned, no disk cleanup needed.
