# CARD-234: The generated cover's title letters from packaged data, like the interior

**Status:** review
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

- [Scope] src/nonogram/admin/book_pdf_generator.py, src/nonogram/cli.py,
  src/nonogram/errors.py, tests/helpers/book_corpus.py, tests/test_book_cover.py,
  tests/test_book_export_interior_cover.py, tests/test_cli.py
- [Scope gate] ⚠ GROWN — 4 of 7 changed files (57%) sit outside this card's `Touches:`
  (`cli.py`, `errors.py`, `test_cli.py`, `tests/helpers/book_corpus.py`), well over the
  ~25% mark. NOT escalated, and the reasoning is on the record rather than implied:
  * `comp_spread` could not be measured at all — this project's `trace.yml` is
    requirement-keyed and carries no `components[].code` globs, so the metric the gate
    leans on hardest is unavailable here. Said plainly instead of scored as zero.
  * The excess is forced, not opportunistic. `tests/test_cli.py`'s
    `test_every_domain_error_has_an_exit_code` closes the error hierarchy over the
    exit-code map, so AC-4's new `NonogramError` subclass CANNOT be added without one
    additive row in `errors.py` and one in `cli.py` — the suite reds otherwise. That is
    SCOPE DISCIPLINE's additive-entry case, not scope growth.
  * `tests/helpers/book_corpus.py` is comment-only: two blocks CARD-221 wrote asserting
    the cover still reads the host's Arial, which this card makes false.
  The reviewer gets the SCOPE NOTE and judges necessity; the gate detects, it does not decide.
- [Scope gate] poach metric is DEGENERATE against CARD-220 and was disregarded:
  CARD-220's `Touches:` is the single glob `tests/**`, so its matched/min ratio is 1/1
  = 100% for ANY card that touches any test file, and every card does. This is a defect
  in CARD-220's footprint breadth, not a slicing defect in this card — carded below.
- [Guard] no structural guardrail to hit: G-1/G-2/G-3/G-4 are behavioral and G-5 names
  components ("the interior", "the cover's design"), not paths. Guardrail evidence is
  therefore the AC/EC/G gate's job, not this gate's.

### Implementation, 2026-10-15

**What changed.** `create_cover_page`'s five lines — the hardcoded
`/System/Library/Fonts/Arial.ttf` and the bare `except OSError:
ImageFont.load_default()` — are gone. The generated title cover now letters
through `_cover_title_face(book_title)`, a new module function beside the
class that returns `_band_font(COVER_TITLE_PX)`: the packaged DejaVu Sans
CARD-221 gave the interior and CARD-197 gave the band, reused rather than
wrapped in a lookup of its own (ADR-0006/R1 package data, no new font file and
no new dependency — G-1). `COVER_TITLE_PX = 72` is the size the old code
already asked for, kept verbatim; the cover's visual design is untouched
(G-5). There is **no fallback left at all**, so G-3 is satisfied by removal
rather than by documentation: the one face is this repository's.

Measured here, and it is the figure the card asked to be written against: the
packaged face at 72 px sets a cap height of **52 px**, the pre-card sizeless
`load_default()` sets **8 px** — a seventh, as CARD-221's F-009 recorded.

**AC-4 decision: refuse, do not substitute.** A title holding a character the
packaged face has no glyph for raises `nonogram.errors.UnletterableTitle`
(new, `INVALID_INPUT` group), naming each character and its codepoint. Why
refuse: a book title is typed by the owner so its repertoire is unbounded,
unlike the interior's; the cover is the file KDP prints, bills for and sells;
and both alternatives are the same defect this card exists to kill wearing a
different costume — printing FreeType's `.notdef` boxes is silent, and
substituting `?`/`U+FFFD`/a transliteration ships a title that is *not the
title*, quietly. A refusal is loud, names the fix, and reaches the owner
through the export route's existing `PDF_EXPORT_FAILED` flash ("the details
are in the panel's log"), where the characters are named with a traceback.
Measured repertoire (pinned by a test, not assumed): the face sets Latin,
Latin Extended, **Cyrillic** (the owner's own language), Greek, Hebrew,
Arabic and a title's punctuation; it does not set CJK, kana, hangul, Thai or
most emoji. Glyph presence is asked of the face by drawing the character and
comparing it with the face's own `.notdef` (U+E000), because Pillow exposes no
character map.

**AC-5 needed a guard, and the measurement says why.** A title of nothing but
whitespace now returns the blank page before a face is asked for. Without it a
title of one tab drew a `.notdef` box centred on an otherwise empty cover —
U+0009 has no glyph of its own — which is exactly the "stray centred artefact"
AC-5 names. Spaces and newlines were always blank.

**Tests** (`tests/test_book_cover.py`, new, 38 cases; every figure measured off
the rendered ink, never off a font object the test built, and every expected
value from an independently loaded packaged face):

| AC | Test | Status |
|----|------|--------|
| AC-1 | `TestBookCover_IsIdenticalWithAndWithoutHostFonts` | pass |
| AC-2 | `TestBookCover_TitleIsDrawnAtTheSizeAsked` | pass |
| AC-3 | `TestBookCover_TitleStaysCentredAndInsideTheTrim` | pass |
| AC-4 | `TestBookCover_UnletterableTitle` | pass |
| AC-5 | `TestBookCover_EmptyTitle` | pass |
| AC-6 | existing uploaded-cover tests in `tests/test_book_export_interior_cover.py`, plus a new `test_the_uploaded_cover_is_used_whatever_the_title_holds` there | pass |

AC-1 clears `_band_font`/`_band_font_bytes` at each host boundary and asserts
that it does (CARD-221's F-G1: a cached face made that card's AC-1
comparisons green against the defect they were meant to catch). AC-3's corpus
is 80 seeded `random.Random(234)` titles with a minimum case count and a
length span asserted inside the test, and overflow is checked against an
independently measured advance width rather than the ink box, because a title
wider than the page is clipped by the canvas and its ink box then reports an
edge that is inside the page.

**Mutation-checked**, each mutant red by name: restoring the pre-card lookup
reds AC-1 and AC-2; deleting the blank-title guard reds AC-5's tab cases;
disabling the glyph gate reds AC-4; changing `COVER_TITLE_PX` reds AC-2's
`test_the_size_asked_for_is_still_the_seventy_two_px_the_card_names` (added
for exactly that, since every other AC-2 claim scales with the constant).

**Guardrails.** G-1 — no font file added, no dependency added;
`tests/test_export_pdf.py`'s two baseline tests pass. G-2 — the cover is
untouched as an interior page; INV-013's property test passes. G-3 — the
silent `except` is removed, not replaced; the module has no fallback face
left. G-4 — CON-019's property test passes. G-5 — the interior is untouched
and the cover's design (its 72 px, its centring rule, its colours) is exactly
as found.

`SCOPE+ src/nonogram/errors.py` — AC-4 refuses with a `NonogramError`
subclass, which the card names as an option, and this is the flat import-free
hierarchy CLAUDE.md says every domain error funnels through. Purely additive:
one class.

`SCOPE+ src/nonogram/cli.py` + `SCOPE+ tests/test_cli.py` — forced by
`test_every_domain_error_has_an_exit_code`, which closes the hierarchy over
the exit-code map: a new error must be grouped or the suite reds. One row each,
`INVALID_INPUT`, with the comment the neighbouring rows carry ("no CLI path
raises it; INTERNAL_ERROR is reserved for a mapping gap").

`SCOPE+ tests/helpers/book_corpus.py` — two comment blocks stated, as of
CARD-221, that "the generated title cover still reads the host's Arial at
72 px". This card makes that false. Comments only; no behaviour.

**Observations for the orchestrator, not fixed here.**
1. *A title wider than the page still runs off it.* The page centres the title
   by its measured bbox with no fitting step, so a title past the trim's
   capacity is centred off both edges. Measured at the Book 1 trim (2550 px,
   72 px type): **69 characters** of a mixed-case title fit; at the 10 cm
   minimum trim it is roughly a third of that. Pre-existing and unchanged —
   shrinking or wrapping a title is the cover's visual design (G-5) and the
   interior's guide title already has a shrink-to-fit pattern that could be
   borrowed. Pinned honestly by
   `test_the_longest_title_the_trim_holds_is_measured_and_not_assumed`.
2. *The refusal reaches the owner only through the log.* `app.py`'s export
   routes flash the generic `PDF_EXPORT_FAILED` and log the traceback, so the
   named characters are in the panel's log rather than on screen. Surfacing a
   `NonogramError`'s own message on those routes is an `app.py` change and
   outside this card's Touches.
3. *A tab inside a title refuses; a title of only whitespace does not.*
   `"A\tB"` is refused (U+0009 has no glyph) while `"\t"` draws the blank
   cover AC-5 asks for. Both branches are documented and tested; if the owner
   would rather have tabs folded to spaces, that is a title-normalisation
   decision for the Finalise screen, not for the drawing code.
