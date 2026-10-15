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
**Review score:** 9.0 (cycle 1/3)
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
reds AC-1 and AC-4 [CORRECTED at review, see below — the implementation agent
wrote "AC-1 and AC-2"]; deleting the blank-title guard reds AC-5's tab cases;
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

- [Build gate] PASSED (full, 1026s) — 7123 passed, 84 skipped, 0 failed, under the repo
  full-suite lock (acquired 09:35:45Z after a 735 s wait behind CARD-235's solo profile,
  released 09:52:55Z). Not vacuous: 7123 tests executed.
  ⚠ Honest discrepancy with the implementation agent's report, which said "4 pre-existing
  skips": this run skipped 84. `DATABASE_URL` is unset on this host, so the DB-mode tests
  skip green — the known project condition. Pre-existing and not caused by this card, and
  none of CARD-234's own six ACs rests on a DB-mode test (they are all cover rendering), so
  no AC is silently unverified by it. Recorded because a skip count that moves by 80 between
  two reports of the "same" green suite is exactly the kind of thing that should not pass
  without a sentence.
- [System contract] section stale — refreshed from the model, but NARROWED deliberately, and
  the narrowing is the point rather than a shortcut:
  * The lens (`system_rules.py --card CARD-234`) returned **52 rules**. That is scope-glob
    breadth, not applicability: this card's `Touches:` now includes `src/nonogram/cli.py` and
    `src/nonogram/errors.py`, which match wide globs like `src/nonogram/**`, so rules about the
    solver's uniqueness property (CON-005), interactive play (CON-021) and the interior's type
    floor (CON-020) all matched a card that changes a cover font. Injecting 52 would buy 52
    shallow verdict lines.
  * **+ADR-0019/R1 (added, and a real catch the card's section missed):** the import-direction
    rule — no capability module may import `cli.py` — is directly applicable precisely because
    this card was forced to add a row to `cli.py` and a class to `errors.py`. Guard:
    `test_every_import_in_the_package_points_inward`.
  * **+ADR-0036/R1 (added):** `compute_layout` without a PageSpec yields today's A4 geometry and
    CLI/web output stays byte-identical — the sibling of CON-019 the card already names.
  * **CON-019 KEPT against the lens, which omitted it.** The procedure says a removed rule must
    stop being enforced, and that is right for a supersession — but this is a scope-glob miss,
    not a supersession: CON-019's own text says it exists "so forge:review checks it on every
    diff touching export/ or the book PDF", and this is a book-PDF diff. Enforcing it is
    following the rule, not overriding the tool.
  Injected floor for review: ADR-0006/R1, CON-019, INV-013, ADR-0036/R2, ADR-0019/R1, ADR-0036/R1.

- [Review 1/3] Score: 9.0 — crit: 0, imp: 0. Risk LOW, lane FAST. Threshold (8) reached
  and the severity gate is clear, so the success path is open. Adversarial verification of
  gating findings was SKIPPED because there were none to verify — the cap exists to bound
  fan-out over findings, and there is no finding here to refute.
- [Review 1/3] Step 8h checked 2 rules beyond the card's section (ADR-0019/R1, ADR-0036/R1)
  — legal and logged, not penalised: those are the two I injected after the lens refresh, and
  the card's frozen projection is what was stale. Coverage guard PASSES: all 4 ids in the
  card's own `## System contract` carry a verdict line, and the count line is present
  ("6 rules checked, 6 ✓ holds, 0 ⚠, 0 ✗").
- [8h spot-check] 3/3 sampled holds reproduced (ADR-0006/R1, CON-019, INV-013) — and the
  re-derivation caught something the verdicts' phrasing hid.
  **Method, stated honestly:** I re-derived these mechanically myself rather than spawning
  three skeptic subagents. The protocol's selection rule is deterministic (fresh `✓ holds`
  citing a named test first, in report order, capped at 3), and for a verdict whose whole
  evidence is "this named test is green", running the test IS the crisp re-derivation the
  protocol asks for — a subagent's opinion would be weaker evidence than the exit code. The
  independence that matters (not being anchored on the reviewer's prose) is preserved because
  a test result cannot be talked into agreeing.
  **What it caught:** every ref these three verdicts cite is a MODEL ALIAS, not a runnable
  pytest id. `-k TestDependencyBaseline_IsExactlyPillowAndNumpy` and
  `-k PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry` both collect **zero
  tests** — the names exist only inside comments and docstrings. A zero-collection run exits
  0, so a spot-check that trusted the alias would have recorded a pass having executed
  nothing. The real tests, found and run:
    * ADR-0006/R1 → `tests/test_export_pdf.py::test_the_dependency_baseline_is_still_closed`
      + `::test_the_font_ships_as_package_data_and_not_as_a_dependency` — 2 passed
    * CON-019 → `tests/property/test_cli_exports_byte_identity.py::test_property_cli_exports_byte_identical_whatever_the_book_geometry`
      + `::test_property_web_ui_exports_byte_identical_whatever_the_book_geometry` — 2 passed
    * INV-013 → `tests/property/test_book_export_interior.py::test_PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage` — 1 passed
  So the holds are genuinely reproduced (5 tests, 5 green on b8b929a) and the reviewer's
  substance was right; what does not re-derive is the CITATION FORM. This is the backlog's
  own "dead `check:` refs on mandatory rules" item — which names ADR-0006/R1 explicitly — now
  observed biting a live gate rather than sitting in a list. Not charged against this card.
- [Review 1/3] mutation revert discipline verified independently: `git diff --stat HEAD -- src
  tests` is clean in the worktree and the only outstanding change is this card file, so the
  reviewer's 6 mutants were all restored as it claimed.
- [Review 1/3] F-003 applied: the card's own mutation note said the pre-card lookup "reds AC-1
  and AC-2"; measured, it reds AC-1 and AC-4. Corrected in place above with the original
  wording preserved, because silently rewriting a claim is how a record stops being evidence.
  The reviewer's explanation is worth keeping: on a host that HAS Arial, Arial and DejaVu share
  a 52 px cap at 72 px, so AC-2 discriminates the dropped SIZE and AC-1 the wrong FACE. The
  division of labour was right; only the sentence was wrong.
- [AC/EC check] All criteria/constraints ✓ (evidence): 11 of 11 items demonstrated by a
  fresh-context gate agent, **zero skips** (every run used `-rs`), nothing modified.
  * AC-1 ✓ `tests/test_book_cover.py::TestBookCover_IsIdenticalWithAndWithoutHostFonts` — 9 passed.
    Non-vacuous: carries its own negative control plus the `_band_font` LRU cache guard, so the
    two halves cannot be one cached face compared with itself.
  * AC-2 ✓ `::TestBookCover_TitleIsDrawnAtTheSizeAsked` — 4 passed. Cap height measured off the
    rendered ink against an independently loaded packaged face; `COVER_TITLE_PX == 72` pinned
    separately so both sides of the comparison cannot scale together.
  * AC-3 ✓ `::TestBookCover_TitleStaysCentredAndInsideTheTrim` — 2 passed. Corpus minimum and
    length span asserted in-test; overflow measured against `textlength`, not the clippable ink box.
  * AC-4 ✓ `::TestBookCover_UnletterableTitle` — 15 passed. Probe cross-checked against the
    shipped font file; Cyrillic/Latin-Ext/Greek/Hebrew/Arabic asserted NOT refused.
  * AC-5 ✓ `::TestBookCover_EmptyTitle` — 8 passed over `"", " ", "   ", "\t", "\n", " \t\n "`.
  * AC-6 ✓ six uploaded-cover classes in `tests/test_book_export_interior_cover.py` — 21 passed.
    Weakening check: that file's diff is +20/−0, one appended method, no existing test edited,
    retargeted or deleted.
  * G-1 ✓ both real dependency-baseline tests green; structurally, no font file added
    (`--diff-filter=A` grep for `.ttf/.otf/.woff*/.pfb` empty) and `pyproject.toml` not in the diff.
  * G-2 ✓ INV-013's real property test green; its file is not in this card's changed-file list.
  * G-3 ✓ no named test, so verified by reading the src diff: the only `try`/`except` hits are the
    REMOVALS (`- try:`, `- except OSError:`); zero new `try`/`except`/`contextlib.suppress` in
    production code. Bounded claim, stated as such: this covers the diff's own lines only —
    pre-existing `except Exception` sites elsewhere in the file are untouched and not this card's.
  * G-4 ✓ both real CON-019 property tests green; their file is not in this card's changed-file list.
  * G-5 ✓ by diff inspection: the only interior-side touch is three added docstring lines on
    `_band_font` (body unchanged); the canvas and the centring block are unchanged CONTEXT lines,
    and `COVER_TITLE_PX = 72` keeps the old number verbatim. Bounded: a diff-scope check, not a
    statement about the cover's design globally.
  The unset `DATABASE_URL` undercuts nothing here — no item's evidence rests on a skipped test.
- [Deferral scan] clean — no `TODO`/`FIXME`/`later card`/`placeholder`/`for now` markers in the
  card's added lines. Nothing to capture to the backlog from the diff itself. (The three
  out-of-scope observations below are recorded obligations, not code-comment debt, and are
  carded separately rather than left as comments — which is why the scan has nothing to find.)
- [Docs] per-directory README step is a deliberate NO-OP, not a skipped step. Two reasons:
  the per-directory README convention is still an OPEN OWNER DECISION on the board's backlog,
  so generating `src/nonogram/README.md` and `src/nonogram/admin/README.md` would decide it by
  side effect; and the one README in this card's changed dirs, `tests/README.md`, does not
  enumerate test files, while its only current section is CARD-217's profiling method — which
  CARD-235, not this card, is the one to update.
- [Build gate] MERGE GATE FAILED (full, rebased onto 91518ad as 1ac46a8, 1062s) —
  **1 failed, 7195 passed, 11 skipped**. Failure:
  `tests/test_book_pdf_memory.py::TestBookPdfMemory_RealBookExportsUnderTheCap::test_one_cap_the_streaming_shape_survives_and_the_list_shape_dies_under`
  The export itself SUCCEEDED — returncode 0, outcome "written", 305 pages read back out of
  the file. What failed is the test's own **headroom guard**:
    `assert resident * CHILD_HEADROOM < CHILD_CAP_BYTES` → `280297472 * 3 < 807840000` → false
  i.e. the streaming child peaked at 280.3 MB where the guard needs under 269.3 MB. The
  assertion's own message says what tripping it means: "this test's verdict has started to
  depend on the interpreter's footprint rather than on the export's shape". It is a
  self-invalidation tripwire, not a statement that the export regressed.
- [Build gate] DIAGNOSIS — not this card, and established statically rather than by asserting
  "flaky". Three independent facts:
  1. **The cover is not in the measured path.** The capped child runs `STREAMING_SHAPE`, which
     `tests/helpers/book_corpus.py:790` resolves to `generator.export_interior(puzzles)` — and
     INV-013 guarantees the interior holds NO cover page. So `create_cover_page` and the new
     `_cover_title_face` are never invoked in the child whose resident set is measured.
     `create_cover_page` does appear in this file's `PAGE_FACTORIES` instrument list, which is
     why this needed checking rather than dismissing — but that list is the probe's coverage,
     and the pair-under-one-cap test is not the one that exercises `export_book`.
  2. **This card adds nothing at import time.** Its only module-level additions to
     `book_pdf_generator.py` are `from nonogram.errors import UnletterableTitle`,
     `COVER_TITLE_PX = 72`, `_UNASSIGNED_CODEPOINT = ""` and a function definition. No
     font is loaded until a cover is drawn. Cost in the child: bytes, not 11 MB.
  3. **The one file this card touches in the failing test's import path is comment-only.**
     Verified against the diff myself rather than taking the implementation agent's and the
     reviewer's word: `tests/helpers/book_corpus.py`'s two hunks are docstring and `#` prose
     recording that the cover no longer reads the host's Arial. Zero executable lines.
  **[RETRACTED 2026-10-15T10:45Z] The paragraph that stood here blamed the sibling CARD-235
  agent for running an unlocked full suite during this gate. That was false and the evidence
  to check it was in my own log.** My merge gate held the lock 10:15:47Z -> 10:33:29Z; that
  agent's profile started 10:33:43Z, fourteen seconds AFTER I released it. They never
  overlapped. The error: I ran `pgrep` at ~10:35Z, after my own gate had exited, saw its
  pytest, and read "running now" as "was running then" — without opening the log that gave
  the window. The lock is a working mutex and was never violated. What did share the window
  was that agent's targeted AC-3/AC-5 sweeps (10:10-10:25Z), which the brief explicitly
  exempts from the lock; if 422-node "targeted" family runs are too heavy for that exemption,
  that is a defect in the spec I wrote, not in its conduct. Kept rather than deleted because
  a retraction that erases what it retracts teaches nothing.
  **The real cause, and it is not load at all** — see the correlation note below.
- [Build gate] UNEXPLAINED, recorded rather than smoothed over: the skip count moved **84 → 11**
  between the pre-rebase gate and this one, on an identical code tree, with the collected total
  unchanged at 7207. So 73 tests that skipped in the first run executed in the second. Leading
  hypothesis is host contention — this project already has one test whose host-shared state
  makes it misbehave when another worktree runs — but I have not proved it, and I am not
  claiming it. It does not bear on this card's verdict either way: no CARD-234 AC rests on a
  DB-mode test (the AC/EC/G gate ran with `-rs` and reported zero skips across all 11 items).
- [Build gate] Procedure deviation, stated plainly: a failed test gate normally increments
  `build_attempts` and spawns a /fix agent. I did NOT, because there is nothing in this card to
  fix — the three facts above locate the failure outside the diff. The remedy is a re-run on a
  quiet host, and that re-run is the evidence; until it is green this card does NOT merge.
- [Build gate] CORRECTED DIAGNOSIS — the guard trips MORE on a quiet host, which inverts the
  obvious reading and kills my own proposed remedy. Four runs of the same test:
    09:20-09:35Z  CARD-235 branch, solo + locked (empty `ps` either side)  FAILED, 279.7 MB
    09:35-09:52Z  CARD-234 branch, locked                                  PASSED, 84 skipped
    10:15-10:33Z  CARD-234 branch rebased, locked                          FAILED, 280.3 MB, 11 skipped
    10:42Z        CARD-234 branch AND main, each run ALONE, locked          PASSED both
  The 09:20 run is the one that matters: solo, locked, on a branch carrying **no CARD-234
  code**, and it failed at 279.7 MB — 4% over the same bar my 280.3 MB cleared by. That datum
  came from the CARD-235 agent volunteering evidence against the convenient answer, which is
  worth recording as conduct.
  So: the failure is independent of this card (already proven statically) **and independent of
  concurrent load**. The live variable is how much of the suite actually EXECUTES. The only run
  that passed is the one where 73 more tests skipped — fewer tests running, less memory
  pressure, the spawned child's RSS stays under the 3x bar. That ties the unexplained 84 -> 11
  skip delta directly to the failure: they are two faces of one variable, not two mysteries.
  Consequence I got wrong and am correcting: "re-run it on a quiet host" is NOT the remedy. A
  quieter host runs MORE of the suite and fails HARDER. And my 10:42Z A/B, green on both trees,
  proves only that isolation is the one condition under which this test cannot discriminate
  anything — `_habitable`/6.75s alone was never the question. I ran the wrong experiment and it
  told me nothing; the control I actually need is a FULL suite on untouched main.
- [Build gate] STATUS: this card is NOT merged and will not be on this gate. Its own code is
  proven innocent on three static grounds plus the 09:20 control, but a red merge gate is a red
  merge gate, and the owner's standing rule is explicit that a red gate still blocks even when
  everything else passes. Next step is a full suite on untouched `main`: if that is also red on
  this test, the blocker is repo-level and sits ahead of every remaining card in the interior
  redesign, not ahead of this one — and that is an owner decision about the suite, not a
  CARD-234 fix. Queued behind the CARD-235 agent's locked AFTER profile and gate run.
- [Build gate] CORRECTION #2 — I had the skip gradient the wrong way round, and the error is in
  my own gate, not in the card. The CARD-235 agent's solo locked run reported **7167 passed,
  11 skipped, 1 failed** (the memory test the only failure), and notes that 11 is the NORMAL
  skip count on this host — CARD-217's profile recorded 9. So:
  * my rebased gate's **11 skipped is normal**;
  * my first gate's **84 skipped is the anomaly** — 73 tests DECLINED TO RUN in it.
  I had read this as "73 extra tests ran in the second run, raising pressure". Backwards. The
  run I reported to the owner as a clean pass ("7123 passed, 84 skipped, 0 failed") was a
  **partially-executed suite**, and the memory test's pass in it is worth exactly as much as
  the 73 tests that did not run. I presented that gate as green without noticing a 73-test
  hole in it; the hole was visible in the summary line I quoted.
  Worse, I cannot say WHICH 73, because neither of my gate runs passed `-rs` — so no skip
  reasons were recorded, and `-q` progress output carries no per-test attribution. The
  information is simply gone and both gates have to be re-run to recover it. Gate scripts now
  carry `-rs`; this should have been there from the first run, for exactly the reason the AC/EC
  gate was told to use it ("a skipped test proves nothing").
- [Build gate] Standing-rule fix I owe, from the CARD-235 agent's suggestion and my own brief's
  defect: the lock exemption for "targeted runs" is too loose. It let a legitimate 422-node,
  nine-minute family sweep run unlocked beside a gate. Better rule, to go into future card
  briefs: **take the lock for any pytest invocation expected to exceed ~60s, whatever selects
  it.** A `-k density` or a single file stays exempt; a 78-run loop or a whole-family sweep does
  not. The current wording made this the agent's judgement call when it should have been a
  measurable threshold.
