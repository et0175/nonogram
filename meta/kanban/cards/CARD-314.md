# CARD-314: A vector page's clue digits say so in the stream — CON-020's exemption survives the conversion instead of becoming unverifiable

**Status:** ready
**Priority:** P1
**Category:** enabler
**Estimate:** 0.5d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** CARD-299's implementation round 1, 2026-10-29 — its sharpest finding, measured on a real vector puzzle page. Cut on owner decision the same day.
**Idea:** —
**Wave:** —
**Created wave:** 66
**Deferred waves:** 0
**Depends on:** CARD-299
**Touches:** src/nonogram/admin/book_puzzle_vector.py, src/nonogram/admin/book_vector.py, tests/test_book_interior_type_floor.py, meta/architecture/requirements.yml
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## [SCOPE CORRECTED 2026-10-29, before dispatch — this is TWO page kinds, not one]

**CARD-299's review cycle 1 found that this card was cut with a one-kind brief, and
it was right.** The finding it inherited named only the vector *puzzle* page. Measured
by that review, joining every exempt face in the spy recording to its page's
`PageKind`:

```
exempt faces by (page kind, pt):   ('answer',10.56):64   ('answer',8.64):258
                                   ('puzzle',13.20):118  ('puzzle',8.64):204
sub-floor AND exempt:              ('answer',8.64):258   ('puzzle',8.64):204
```

**258 of the 462 exempt sub-floor faces are on ANSWER pages** — more than the puzzle
page's 204 — drawn 322× per book through `book_pdf_generator._write_clues`, which is
an `EXEMPT_CALLER`. And the orchestrator confirmed the vector answer writer draws
them too: **`src/nonogram/admin/book_answer_vector.py:403` calls
`draw_clue_digits(...)`**.

So CARD-299's guard, whose refusal is `assert kind.value != "puzzle"`, **does not
refuse an answer page** — the day `PageKind.ANSWER`'s declaration lifts it reads the
page and reports **258 false CON-020 violations**, which is the exact failure the
puzzle refusal exists to prevent.

**This card therefore covers the PUZZLE page and the ANSWER page**, and every AC
below should be read as "a vector page that draws clue digits" rather than "a vector
puzzle page". The raised finding was understated in three places — CARD-299's card,
`requirements.yml` and the ADR — and CARD-299's fix round is correcting all three.

## Why this card exists — CON-020 goes unverifiable the day a clue-digit page converts

**CON-020** is the 10 pt reader-facing interior type floor. Its exemption is **clue
digits inside clue cells**, whose size follows the cell (CON-018 / INV-006), and the
exemption is keyed on **the drawing function** — `png._draw_clues` / `_write_clues`.

CARD-299's round measured a real vector puzzle page, written by
`BookPDFGenerator.vector_puzzle_page` — **and its review then measured that the
answer page carries MORE of them** (see the scope correction above):

```
Tf operators:        205
distinct sizes (pt): [8.64, 14.16]
below the 10 pt floor: [8.64]
```

**The 8.64 pt faces are exactly the ones CON-020 exempts — and a PDF content stream
records no provenance.** A stream-read floor cannot tell an exempt clue digit from
body type. So CARD-299's `stream_faces` **refuses a vector puzzle page by name**
(default-DENY) rather than doing either wrong thing:

- reporting **205 false violations**, or
- exempting 8.64 pt **by its value** — which would exempt a body face that happened
  to measure 8.64 pt, turning a provenance exemption into a magic number.

That refusal is correct and it is a **hole with a date on it**: the day CARD-309
converts the puzzle page, CON-020 has no verifying reading for it. **CON-020 is a
`status: covered` row in `trace.yml` whose `tests:` list the validator actually
reads, and gate 3 there is `Severity.ERROR`** — so this is not a warning waiting to
happen.

## What to implement

1. **Mark the clue digits in the stream.** Give the vector puzzle writer a way to say
   *"this text run is a clue digit"* that survives into the written PDF and that a
   reader can recover — a marked-content tag (`/Artifact`, a `BDC`/`EMC` pair with a
   tag of the project's choosing) or whatever the writer can emit without a new
   dependency. **ADR-0006/R1 is closed**, so the answer must be stdlib + Pillow +
   NumPy.
2. **Let `stream_faces` stop refusing.** CARD-299's refusal is keyed on the page kind;
   replace it with a reading that **exempts by the mark, never by the size**. The
   distinction is the whole card: a provenance exemption must stay a provenance
   exemption.
3. **Keep the raster arm exactly as it is.** The spy-based reading
   (`TestInteriorType_OnlyPuzzleClueDigitsAreExempt`) is CON-020's verification while
   the page is a bitmap and must not be weakened — the two arms coexist until
   CARD-309 converts, and even then the cover stays raster.
4. **State the bound.** A mark the writer emits is a claim the writer makes. Say what
   happens if the mark is **missing** (the reading must fail, not exempt) and if it is
   **over-applied** (a body face wrongly marked must be caught by something — name
   what).

## Acceptance criteria

- **AC-1** (the exemption survives in the stream): *Given* a vector puzzle page,
  *then* its clue digits are recoverable from the written PDF as clue digits, and the
  10 pt floor is asserted over the **non-exempt** faces only.
- **AC-2** (exemption by mark, never by size): *Given* a body face that measures the
  same size as a clue digit, *then* it is **reported as a violation**. (**This is the
  card's central control** and it must fail without the fix: with a size-keyed
  exemption it passes.)
- **AC-3** (a missing mark fails closed): *Given* a vector puzzle page whose clue
  digits carry no mark, *then* the reading **fails** rather than exempting them or
  reporting 205 violations. Per ADR-0039/R2 an unanalysable shape is a FAILURE.
- **AC-4** (an over-applied mark is caught): *Given* a body face wrongly marked as a
  clue digit, *then* something reds — name it. **Two mutants per ADR-0039/R1**, one
  per direction.
- **AC-5** (the raster arm is untouched and still green): *Given* the branch, *then*
  `TestInteriorType_OnlyPuzzleClueDigitsAreExempt` and CON-020's other listed tests
  are unchanged and pass, and **CON-020's `trace.yml` row still resolves** — every
  listed test by its `def`/`class` line, because gate 3 is ERROR-level.
- **AC-6** (an owner render exists): *Given* a marked vector puzzle page, *then* a
  render is produced under `~/Documents/nonogram-reviews/CARD-314/` — a marked-content
  tag must not change a single visible mark, and the eyeball is how that is confirmed.

## Engineering constraints

- **EC(CON-020):** across a seeded corpus of vector puzzle pages spanning trims and
  grid sizes, every non-exempt face holds 10 pt and every clue digit is exempt **by
  its mark**, with a minimum case count asserted inside the test.

## Guardrails

- **G-1: do not change CON-020's statement.** A 10 pt reader-facing floor is a
  physical measure and is medium-independent. Only its *verification* changes here.
- **G-2: do not exempt by size, ever** — AC-2 exists to make that impossible to ship.
- **G-3: no new runtime dependency** (ADR-0006/R1); the mark must be emitted with
  stdlib + Pillow + NumPy. Verify the **substance**, not the dead
  `TestDependencyBaseline_…` ref.
- **G-4: do not weaken the raster/spy arm** while the page is still a bitmap.
- **G-5: the 21 book baselines must not move** unless the mark changes the written
  bytes — and if it does, **that is a finding to raise first**, because a
  marked-content tag should be invisible to a reader and the baselines are per-page
  digests. Say which before re-recording anything.
- **G-6: no test deleted, renamed, skipped or merged** — `parametrize` ids included.

## System contract (subset — the pipeline re-derives the full list at dispatch)

- CON-020 — the 10 pt interior type floor, clue digits inside clue cells exempt (check: CARD-184's test, re-expressed medium-gated by CARD-299; **`trace.yml` row is `status: covered`, so gate 3 is ERROR-level**)
- CON-018 / INV-006 — a clue digit's size follows its cell
- ADR-0042/R1-R2 — interior pages are operators; a raster page is declared (check: CARD-298's guard)
- ADR-0039/R1-R2 — a claim needs a control that CAN fail; an unanalysable shape is a FAILURE (check: review-lens)
- ADR-0006/R1 — the dependency baseline is exactly stdlib + Pillow + NumPy (check: **DEAD REF** — verify the substance; see CARD-307)

## Architecture context

- **FR:** FR-033, FR-043
- **ADR:** ADR-0042/R1-R2, ADR-0039/R1-R2
- **CON:** CON-020, CON-018
- **INV:** INV-006
- **Components:** COMP-009
- **Trace:** CON-020's row is `status: covered` with seven listed tests; if this card's work changes which test verifies the exemption, **re-stamp that row in the same commit**, because gate 3 is `Severity.ERROR` and a listed test with no definition breaks the build rather than warning.

## Worktree notes

- **This is the one card in the ADR-0042 phase that must touch `src/`** to keep a
  constraint verifiable. CARD-299 and CARD-312 are test-side; CARD-309 converts pages;
  this card makes the conversion **safe for CON-020**.
- **Ordering:** it can land before CARD-309, and probably should. If CARD-309 converts
  the puzzle page first, CON-020 is unverified for that page until this lands — so
  this card is a **prerequisite for the puzzle page's conversion**, not a follow-up.
  CARD-309's own notes should say so.
