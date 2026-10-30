# CARD-314: A vector page's clue digits say so in the stream — CON-020's exemption survives the conversion instead of becoming unverifiable

**Status:** in progress
**Priority:** P1
**Category:** enabler
**Estimate:** 0.5d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/314-clue-digits-say-so-in-the-stream
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-314
**Source:** CARD-299's implementation round 1, 2026-10-29 — its sharpest finding, measured on a real vector puzzle page. Cut on owner decision the same day.
**Idea:** —
**Wave:** 68 <!-- STAMPED 2026-10-30 on owner decision, dispatched with CARD-220. This card had NO wave while being P1, 0.5d, and the self-declared prerequisite of CARD-309 -- which is wave 68 and whose `Depends on` lists only 298/299/306, all merged. So 309 read as runnable while its real blocker was invisible to the dispatcher, because the constraint lives in PROSE on 309's card ('raise it rather than proceeding') and not in a field. The owner asked which of 220/309 to take next; the measured answer was neither. -->
**Created wave:** 66
**Deferred waves:** 0
**Depends on:** CARD-299
**Touches:** src/nonogram/admin/book_vector.py, src/nonogram/admin/book_vector_draw.py, tests/helpers/pdf_vector.py, tests/test_book_interior_type_floor.py, tests/test_book_pdf_vector_primitives.py, tests/test_book_puzzle_page_vector.py, tests/test_book_solved_answer_key.py, meta/architecture/trace.yml <!-- CORRECTED at implementation from `git diff --numstat 4d164f62..7f40f30f`. The declaration was wrong in three ways. (1) It named `book_puzzle_vector.py`; the mark actually lives in **`book_vector_draw.py`**, one chokepoint serving BOTH page kinds, which is why the card's two-kind scope costs nothing extra. (2) It named `requirements.yml`; the card touches **`trace.yml`** instead and leaves requirements.yml byte-unchanged -- G-1 says only the VERIFICATION changes, and verification lives in trace.yml. (3) It was short by four test files, every one a structural default-DENY guard that refused an operator or member nobody had classified: the vector-primitives mark guard, the puzzle-page operator reader and state-operator count, and the answer-key door probe plus its emitted-operator set (16->18 and 8->10 members). **Each guard behaved correctly and each is now classified with its own measurement rather than silenced**, and two were strengthened -- the answer-key module now asserts the mark is on answer pages and NOT on the TOC, per kind. -->
**Review score:** — (implemented `7f40f30f`)
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

---

## Implementation — `4d164f62` → `7f40f30f`, 2 commits, 8 files, +1248/−86

Nothing to merge — the worktree was cut at `main`'s tip, CARD-306 included. Lock checked by
absolute path before every run and **never present**; **no run collected 0 tests**, so every count
below is a real collection. Nothing pushed, merged or rebased.

### The mark, and why that form

`/ClueDigit BMC … EMC` — a PDF 1.7 §14.6 marked-content sequence, emitted by the one clue-digit
drawer and **by nothing else in the package**. **One pair per clue set, not per digit** — 2
operators on a 30×30 instead of 1080.

**`BMC`, not `BDC`**, with the reasoning recorded: `BDC` carries a property list, and the only two
options here are an empty dictionary (saying nothing a bare tag doesn't) or an `/MCID` into a
structure tree — **and the interior writes no `/StructTreeRoot`**, so an `/MCID` would be a dangling
reference claiming a tagged-PDF conformance the file does not have. **The rejected alternative is
recorded in the constant's comment**: a second `/Font` resource alias would have carried provenance
with **no new operator and no blast radius at all**, and was rejected because a resource name names
*which face to set in* — overloading it to also mean *what this text is for* collides with the next
card that embeds a second face. **The blast radius was the price of the honest mechanism**, and it
is reported in full in the `Touches` correction above.

**G-3 by substance, not by the dead ref**: `pyproject.toml` diff **empty**; every added import is
stdlib or intra-project; the third-party import set is unchanged.

### AC-2, the central control — and it plants at a size it reads off the page

The body face is planted **outside every bracket**, at exactly the size the clue digits on **that
same page** measure — **read off the page rather than written as `8.64`, so the two cannot drift.**
Mutant: swap the mark test for a size equality. **5 failed, 42 passed** (AC-2 on both kinds, AC-3's
two tests, and the EC) against 47 passed unmutated.

### The two bounds, one mutant each

| direction | mutant | result |
|---|---|---|
| **missing mark fails closed** (AC-3) | the mark assertion short-circuited | **2 failed, 45 passed** |
| **over-applied, wrong page** (AC-4) | the negative assertion short-circuited | **1 failed, 46 passed** |
| **over-applied, wrong code** (AC-4) | a second emitter planted in the frame drawer | **2 failed, 45 passed** |

A missing mark **fails, never exempts** (ADR-0039/R2), and an unbalanced bracket raises out of the
reader *and* the writer refuses to write such a page — so it cannot ship and then be found.

**The negative control is the good part.** A drawer that opens one pair **per digit** — a different
but **equally correct** carrier of the same claim — leaves **46 of 47 green, every AC-bearing test
among them**. The one that rises is the deliberate economy assertion. **That division is correct and
was unstated**, so the second commit states it in the test. This is a near-miss control doing
exactly what it is for: distinguishing *wrong* from *differently right*.

### Figures re-derived — and the card's table is one book of two

The card's exempt-face table **reproduces exactly on book 1**, but the module walks **two** books,
and the second contributes **644 more** exempt sub-floor faces at four sizes the card never
mentions — **1106 across both**. The card's *direction* holds either way: answer 580 against puzzle
526. The EC corpus (3 trims × 6 grid sizes) carries **3557 exempt faces over 11 distinct point
sizes**, and **four of the eleven are ABOVE the floor and still exempt** — *a clue digit does not
stop being one on a larger trim*, which is the clearest statement yet of why a size key was never
an option.

### G-5 — the baselines did not move, and the mechanism is stated

**0 files under `tests/fixtures/` changed; 21 baselines present before and after.** Nothing to
raise. The reason: **all seven `PageKind` values are still declared raster exceptions, so no vector
page reaches the interior export at all.**

### AC-6 — the owner render, measured by an engine that wrote neither file

Marked against unmarked, rendered with poppler at 150 dpi: **0 differing pixels of 2,103,750**, max
absolute difference **0**, ink pixels **107,962** on both, extracted text layer **identical** at 550
characters. Bytes **+26, or +0.007%**. **A marked-content tag changes not one visible mark**, which
is exactly what AC-6 exists to confirm.

### `trace.yml` re-stamped in the same commit

CON-020's row gains three classes and a dated amendment note. **All 10 listed tests resolve to a
`class` line, 0 dead refs** — which matters because **gate 3 there is `Severity.ERROR`**, so a
listed test with no definition breaks the build rather than warning. `requirements.yml` untouched.

### Six things measured wrong in the card or my brief

1. **The card's scope-correction premise is STALE.** It says CARD-299's guard *"does not refuse an
   answer page"*. At the fork point that is **false** — CARD-299's fix round already derives the
   clue-digit kind set from `src/` with `ast` and already covers both kinds, with the answer-page
   test live. **My brief's instruction was still right** (read every AC as *a vector page that draws
   clue digits*), but **nothing was one-kind on arrival.**
2. **The exempt-face table is book 1 only**, presented as if it were the whole recording.
3. **`stream_faces` could never have been tested against a real vector page, and CARD-299's tests
   never needed one** — the existing helper only makes a page *claim* to be vector while the stream
   it reads is still the raster page's, with no type operators at all. CARD-299's refusal fired on
   the page **kind**, before any reading, so this never showed. The round split the reader and added
   one that calls production's own writers. **Lifting the puzzle page's raster declaration does not
   work as a substitute** — measured: the page arrives as an image, because **the page conversion is
   CARD-309's.**
4. **My `Touches` list was short by five files** — corrected above.
5. **One existing test would have gone silently vacuous**: it wraps a reader to prove the stream arm
   was reached, and the arm now reads through a different function, so the wrapper would have
   recorded nothing **and the test would have claimed the arm was never reached.** Body updated
   under the same name.
6. **Two test names now sit slightly off their bodies, and G-6 is why.** They assert the
   **missing-mark** refusal rather than the kind refusal. The names still read true — the page *is*
   refused rather than read — and **G-6 forbids renaming**, so they were kept and said so in both
   docstrings. **A reviewer should know the names predate what they now test.**

### Numbers

**Node ids 317 → 330 across the four vector modules: +13 added, 0 removed, 0 renamed**, two of the
13 being new `parametrize` ids. **G-6 holds**: 0 test defs removed, no `skip`/`xfail` marker added.
**Skips by name: exactly one** — `test_book_pdf_memory.py`'s `setrlimit(RLIMIT_AS)` the kernel
refuses; **0 `DATABASE_URL`-gated skips in this radius.** Runtime as ranges with conditions: the
floor module **2.3–3.1 s**; the whole blast radius **1239 passed, 1 skipped in ~198 s**; and the
round measured its own **run-to-run spread at ~15%** on a fixed 8-module set (54 s against 62 s), so
it states single figures as ±15% rather than publishing them bare. No load figure.
