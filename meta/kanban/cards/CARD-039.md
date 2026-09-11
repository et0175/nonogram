# CARD-039: Clear size field when new image is uploaded

**Status:** done
**Priority:** P3
**Category:** ux-polish
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/039-clear-size-on-upload
**Worktree:** —
**Source:** User feedback during wave 0–2 testing
**Idea:** —
**Wave:** 3
**Depends on:** CARD-034
**Touches:** src/nonogram/web/static/metadata.js
**Review score:** —
**Started:** 2026-09-04T00:00:00Z
**Closed:** 2026-09-08T10:59:21+03:00
**Actual:** n/a — reconciled, see Worktree notes
**Merge commit:** 96da6ac
**Blocked by:** —

## What to implement

When a user selects a new image file, the size field should be cleared. This prevents stale size suggestions from the previous image being used with the new one.

**Flow:**
1. User uploads Image A → suggestions for A appear
2. User selects Image B → size field clears (and new suggestions appear for B)
3. User picks new size for B → generates with B + new size

**Implementation:** In `metadata.js` file change listener, clear the size input field when a new image is selected.

## Acceptance criteria

- **AC-149** (clear size) — given a user who previously selected a size for one image, when they select a new image, then the size field is cleared.
  *test:* `TestWebUI_ClearsSizeOnNewImageSelect`

- **AC-150** (no interference) — given a user who manually entered a size, when they select a new image, then the size field clears and fresh suggestions appear for the new image.
  *test:* `TestWebUI_FreshSuggestionsForNewImage`

## Guardrails

- G-1: Only clear size field, not other form fields (difficulty, name, seed, etc.)
- G-2: No JavaScript errors if size field doesn't exist
- G-3: Suggestions still update properly for new image

## Architecture context

- **FR:** FR-017
- **NFR:** NFR-003
- **ADR:** ADR-0020
- **Components:** COMP-008
- **Trace:** meta/architecture/trace.yml

## Worktree notes

**2026-09-10 — reconciled against `main`, not merged normally.** Same
disconnected-history situation as CARD-038 (`git merge-base main
card/039-clear-size-on-upload` returns nothing). Notably, this card's actual
implementation commit (`5c5ae5e "feat(CARD-039): Clear size field when new
image is uploaded"`) exists in the repository — but it landed on the
**`card/037-persist-upload-retry`** branch, not on this card's own
`card/039-clear-size-on-upload` branch (which still points at CARD-041's tip,
`fff246f`, unchanged) — an apparent worktree/checkout mixup at implementation
time, on top of the history split.

`main`'s `clearSizeField()` (`src/nonogram/web/static/metadata.js:255-305`,
explicitly commented `// AC-149: Clear size field...` — this card's own AC id)
already satisfies this card's intent, introduced by the same `96da6ac` bulk
restore as CARD-038. Verified present on current `main`; closing as done with
`96da6ac` as the merge commit.

The orphaned worktree at `../PythonProject4-CARD-039` still exists on disk and
should be removed — left untouched pending explicit confirmation.
