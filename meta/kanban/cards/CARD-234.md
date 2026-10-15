# CARD-234: The generated cover's title letters from packaged data, like the interior

**Status:** in_progress
**Priority:** P2
**Category:** bug
**Complexity:** standard
**Estimate:** 0.5d
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/234-cover-packaged-face
**Worktree:** ../PythonProject4-card-234
**Source:** found at CARD-221's implementation station, 2026-10-14 — the one place the interior's new "typography is deterministic" rule is still untrue
**Idea:** —
**Wave:** 40
**Depends on:** CARD-221 (which establishes the packaged face as the rule and the helper that returns it)
**Touches:** src/nonogram/admin/book_pdf_generator.py, tests/test_book_cover.py, tests/test_book_export_interior_cover.py
**Review score:** —
**Started:** 2026-10-15T08:44:16Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**Current behaviour (verified by reading the code).** `create_cover_page` draws a generated
title cover with a hardcoded host path and a silent fallback
(`src/nonogram/admin/book_pdf_generator.py:3180-3184`):

```python
# Try to load a nice font, fall back to default
try:
    title_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 72)
except OSError:
    # Fallback font
    title_font = ImageFont.load_default()
```

Two defects in five lines, and they compound:

1. **The path is macOS-only.** On the deployed Linux panel the `OSError` branch is taken every
   time, so a cover generated in production is lettered differently from one generated on the
   owner's Mac — the same class of defect CARD-221 closed for the interior, still open here.
2. **`load_default()` is called with no size**, so the 72 px the line asks for is silently
   dropped and the title is drawn in Pillow's small bitmap face. The title is then centred by
   its own measured bbox, so it does not overflow — it just comes out tiny, on the one page a
   buyer sees first. Nothing fails; nothing is logged. **Measured at CARD-221's review
   (2026-10-14, F-009): the fallback is a *sizeless* `load_default()` under a 72 px request,
   i.e. roughly a 10 px em.** So this is not "the cover letters in a different face off-host" —
   it is a cover whose title is about a seventh of its intended size. Write the AC against that
   figure, not against a vaguer one.

**What changes.** Letter the title from the same packaged face CARD-221 established for the
interior, at the size the code asks for. Keep a fallback only if a glyph is genuinely missing,
and if so name the glyph in a docstring rather than leaving a silent `except`. A book title is
user-supplied text, so unlike the interior its repertoire is **not** bounded — say what happens
for a title the packaged face cannot letter, and test it.

**Why it is its own card and not part of CARD-221.** Different file region, no baseline digests
it (the interior fixtures do not cover the cover), and CARD-221's acceptance criteria are all
about the interior. Folding it in would have widened a card that was already carrying two owner
blocks. CARD-221's notes flag it as the single place its candidate ADR ("the interior's
typography is deterministic") would not yet be true.

## Acceptance criteria

- **AC-1** (happy, determinism): *Given* a book title, *when* the cover is generated with the
  host's Arial available and again with `ImageFont.truetype` refusing every host path, *then*
  the two covers are byte-identical. (test: `TestBookCover_IsIdenticalWithAndWithoutHostFonts`)
- **AC-2** (happy, the size is honoured): *Given* the cover, *then* the title's drawn cap height
  corresponds to the size the code asks for, not to Pillow's default bitmap face — measured off
  the ink. (test: `TestBookCover_TitleIsDrawnAtTheSizeAsked`)
- **AC-3** (happy, still centred): *Given* titles of very different lengths, *then* each is
  centred on the page and none overflows the trim.
  (test: `TestBookCover_TitleStaysCentredAndInsideTheTrim`)
- **AC-4** (edge, a title the face cannot letter): *Given* a title with a character outside the
  packaged face's repertoire, *then* the stated behaviour happens (substitute, or refuse with a
  `NonogramError` — decide and document which) and it is **not** a silent tiny-type fallback.
  (test: `TestBookCover_UnletterableTitle`)
- **AC-5** (edge, an empty or whitespace title): *Given* such a title, *then* the cover is drawn
  without a crash and without a stray centred artefact.
  (test: `TestBookCover_EmptyTitle`)
- **AC-6** (guard, the uploaded-cover path is untouched): *Given* a book with an uploaded cover
  image, *then* nothing about its handling changes — this card only touches the generated one.
  (test: the existing uploaded-cover tests in `tests/test_book_export_interior_cover.py`)

## Guardrails

- G-1: No new font file and no new runtime dependency — the packaged face already ships
  (ADR-0006/R1) (test: `tests/test_export_pdf.py::test_the_dependency_baseline_is_still_closed`
  and `::test_the_font_ships_as_package_data_and_not_as_a_dependency`).
- G-2: INV-013 — the cover is not part of the interior and this card must not make it one
  (test: `PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage`).
- G-3: No silent `except` left behind. Every fallback either names its condition or is removed.
- G-4: CON-019 — CLI and web-UI exports stay byte-identical (test:
  `PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry`).
- G-5: Out of scope — the interior (CARD-221), the cover's design.

## System contract

- ADR-0006/R1 — runtime dependencies are exactly stdlib + Pillow + NumPy; packaged static
  assets are not a dependency change (check:
  `tests/test_export_pdf.py::test_the_dependency_baseline_is_still_closed`)
- CON-019 — book geometry never changes CLI/web exports (check:
  `PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry`)
- INV-013 — the interior holds no cover page (check:
  `PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage`)
- ADR-0036/R2 (check: review-lens)

## Architecture context

- **FR:** FR-043 as amended by CARD-135 (the cover is its own file, not an interior page).
- **ADR:** ADR-0006/R1, ADR-0036/R2. **Candidate rule:** CARD-221 proposes "the interior's
  typography is deterministic — every face it measures comes from packaged data, never from a
  host lookup". If the architect station adopts it, this card is what lets the rule be stated
  about the **book** rather than only the interior.
- **Components:** COMP-009.
- **Trace:** not updated by this card.

## Worktree notes

- [How it was found] Not by a failing test — by CARD-221's agent being asked to say which
  host-dependence gates it removed and which it kept, and why. The honest answer surfaced a
  host lookup nothing in the suite covers. Worth remembering as a method: asking what is *still*
  true after a change found a defect that asking what broke would not have.

- [Env] forge unknown — no executing plugin manifest resolvable and the project
  declares no `forge.min_version` (there is no `meta/.skills.yml`), so the skew
  comparison is a no-op rather than a pass. Recorded so a later diagnosis is possible.
- [Wave] 40, dispatched 2026-10-15. Paired with CARD-235: no shared path and no shared
  hotspot, so the two run concurrently under the owner's concurrency cap of 2.
