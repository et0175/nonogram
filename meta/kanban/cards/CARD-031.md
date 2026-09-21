# CARD-031: Show image metadata and suggested puzzle dimensions after upload

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/031-image-metadata
**Worktree:** —
**Source:** User feedback during CARD-021 testing
**Idea:** —
**Wave:** —
**Depends on:** CARD-021
**Touches:** src/nonogram/web/pages.py, src/nonogram/web/handler.py, src/nonogram/sourcing/image.py, tests/test_web_upload.py
**Review score:** —
**Started:** —
**Closed:** 2026-09-21
**Actual:** —
**Merge commit:** _(with CARD-104)_
**Blocked by:** —

## What to implement

After a user uploads an image, display:
1. **Image aspect ratio** (e.g., "3:2", "1:1", "16:9") — helps user understand the shape
2. **Suggested puzzle dimensions** — recommend grid width/height based on the image's aspect ratio and the 10..30 constraint (e.g., "For a 3:2 image, try 30x20 or 20x13")

This helps users make informed choices about the grid size before generation, reducing trial-and-error.

## Acceptance criteria

- **AC-125** (metadata) — given an uploaded image, when the form displays after upload, then the page shows the image's aspect ratio (as a ratio like "4:3" and as decimal like "1.33") below the file input.
  *test:* **retired 2026-09-21** — no server-rendered aspect ratio exists; CARD-034's `/static/metadata.js` shows it client-side, covered by `tests/test_web_metadata.py`

- **AC-126** (suggestions) — given an uploaded image at a known aspect ratio, when the form renders, then it displays 2–3 suggested grid dimensions that fit that ratio within the 10..30 constraint, ordered by how closely they match the image.
  *test:* **retired 2026-09-21** — as above; `test_suggestion_count_is_2_to_3` covers the rule in `tests/test_web_metadata.py`

- **AC-127** (integration) — given a user who selects a suggested dimension, when they submit the form, the generation uses that size and the image sourcing applies the aspect-ratio crop as designed (ADR-0022, unchanged).
  *test:* **retired 2026-09-21** — the suggestion buttons set the `size` input client-side; generation from a typed size is covered many times over

## Guardrails

- G-1: The image sourcing logic is unchanged — suggestions are advisory only
- G-2: No changes to image upload, parsing, or validation (CARD-021's work)
- G-3: Suggested dimensions must always be within 10..30 per side (CON-011)

## Architecture context

- **FR:** FR-017, FR-003
- **NFR:** NFR-003
- **ADR:** ADR-0022 (image aspect ratio and cropping)
- **Components:** COMP-008 (web UI), COMP-003 (sourcing — unchanged)
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—

### Closed 2026-09-21 by CARD-104 — the criteria are retired, not met

This card's AC-125 and AC-126 describe the **server** rendering an aspect ratio
and suggested dimensions. That was never true of a page anyone loaded:

* `pages._metadata_section` and `pages._suggestions_section` were written and
  **never called** — zero call sites in `src/`.
* `form_with_result` took `image_metadata_str` and `suggestions` and
  interpolated neither.
* `handler._generate` ran `extract_metadata`, `format_aspect_ratio` and
  `suggest_dimensions` on every image upload and **discarded the results**,
  inside `except (ImportError, Exception): pass` — a catch that swallows
  everything, which is why it stayed invisible.

The need was met later and differently: **CARD-034** shows the ratio and the
suggestion buttons client-side from `/static/metadata.js`, covered by
`tests/test_web_metadata.py`. So the user-visible behaviour these criteria
asked for does exist — just not where they said, and not from this code.

**CARD-104 deleted the unreachable path** at the owner's decision: both section
builders, both unused parameters, and the handler block with its catch-all. The
`.metadata` / `.suggestions` / `.suggestion-button` CSS stays, because
`metadata.js` writes exactly those classes.

`src/nonogram/web/metadata.py` also stays: `extract_metadata` and
`suggest_dimensions` are still exercised by `tests/test_web_metadata.py`'s
parity tests, which check the Python and JavaScript algorithms agree.
