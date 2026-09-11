# CARD-040: Implement suggestion algorithm (metadata.py module)

**Status:** done
**Priority:** P2
**Category:** bugfix
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/040-suggestion-algorithm
**Worktree:** —
**Source:** User testing feedback & CARD-031 gap
**Idea:** —
**Wave:** —
**Depends on:** CARD-031 (supposed to exist, missing)
**Touches:** src/nonogram/web/metadata.py (new), tests/test_web_metadata.py
**Review score:** —
**Started:** —
**Closed:** 2026-09-08T10:59:21+03:00
**Actual:** n/a — reconciled, see Worktree notes
**Merge commit:** 96da6ac
**Blocked by:** —

## What to implement

CARD-031 created references to `nonogram.web.metadata` module with functions `extract_metadata()`, `format_aspect_ratio()`, and `suggest_dimensions()`, but the module itself was never created. The handler.py code tries to import it and fails silently.

This card implements the missing module with:

1. **extract_metadata(image_path)** — read image dimensions, return AspectRatio
2. **format_aspect_ratio(ratio)** — format as "WxH (decimal)" for display
3. **suggest_dimensions(image_metadata)** — generate 2-3 grid suggestions tailored to image size

**Suggestion algorithm:**
- Generate all grids 10..30 that match the image's aspect ratio
- Score by ratio match quality (prefer exact matches)
- **Prioritize larger grids (20–30) for high-res images**
- Prioritize smaller grids (10–15) for low-res images
- Return top 2-3 suggestions

## Acceptance criteria

- **AC-151** (extract) — given an image file, extract width/height and calculate aspect ratio.
  *test:* `TestMetadata_ExtractsDimensions`

- **AC-152** (format) — format aspect ratio as both ratio ("4:3") and decimal ("1.33").
  *test:* `TestMetadata_FormatsAspectRatio`

- **AC-153** (suggest) — generate 2-3 dimension suggestions within 10..30, ordered by ratio match.
  *test:* `TestMetadata_SuggestsDimensions`

- **AC-154** (size-aware) — larger images suggest larger grids (closer to 30x30); smaller images suggest smaller grids (closer to 10x10).
  *test:* `TestMetadata_SuggestionsScaledByImageSize`

## Guardrails

- G-1: No new runtime dependencies (use Pillow which is already a dep)
- G-2: Algorithm deterministic (same image = same suggestions every time)
- G-3: All suggestions within 10..30 constraint (CON-011)

## Architecture context

- **FR:** FR-017
- **NFR:** NFR-003
- **ADR:** ADR-0006, ADR-0019
- **Components:** COMP-008
- **Trace:** meta/architecture/trace.yml

## Worktree notes

**2026-09-10 — reconciled against `main`, not merged normally.** Same
disconnected-history situation as CARD-038/039/041. This card's own branch
(`card/040-suggestion-algorithm`) does carry real implementation commits
(`35b3bf8 "feat(CARD-040): Implement suggestion algorithm (metadata.py
module)"`, `1364275 "fix(CARD-040): Replace sourcing import with PIL to fix
architectural violation"`), but on a history with no path to current `main`.

`src/nonogram/web/metadata.py` already exists on `main` with all three
functions this card specified — `extract_metadata()`, `suggest_dimensions()`,
`format_aspect_ratio()` — brought in by the same `96da6ac` bulk restore, whose
commit message explicitly notes "Restored 153 silhouette images from CARD-040
backup". Verified present on current `main`; closing as done with `96da6ac` as
the merge commit.

No orphaned worktree for this card (`Worktree: —` already, per the card's
pre-existing field) — only the branch is orphaned, no disk cleanup needed.
