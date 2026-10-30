# CARD-314: A vector page's clue digits say so in the stream — CON-020's exemption survives the conversion instead of becoming unverifiable

**Status:** done
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
**Review score:** **8.5 (cycle 1/3) — CERTIFIES**, 12 findings, none a defect in shipped behaviour; **three fix rounds**, the third discharging a cross-card census the gate caught.
**Started:** 2026-10-30T05:20:00Z (wave 68 dispatch)
**Closed:** 2026-10-30T08:33:00Z
**Actual:** 0.4d — **~3h 13m wall clock**, dispatch to merge, which is the instrument: implementation, one review cycle, three fix rounds and two gate runs (the first red). Against a 0.5d estimate that is **0.8×** — under, and the comparison is only sound against cards measured the same way.
**Merge commit:** `8762beed` (gated tree `8d70e2b0`)
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
| **over-applied, wrong code** (AC-4) | a second emitter planted in the frame drawer | **2 failed, 45 passed** — **SITE-DEPENDENT, see below** |

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

### M4's figure is site-dependent, and that is the correction it needed

**CORRECTED 2026-10-30, by the orchestrator, because the figure is card-resident.** The AC-4
over-application row reports **2 failed / 45 passed** for *"a second emitter planted in the frame
drawer"* — **without naming a plant line**, and cycle 1's reviewer got **4 failed / 43 passed**
from a **folio-drawer** plant of the same shape. Both readings are real; **the split is a function
of where the second emitter goes**, because a plant that brackets nothing leaves AC-3's refusal
unable to fire — which is the same mechanism fix round 1 measured under F-006.

Fix round 2 searched `tests/`, `src/` and `docs/` for every spelling of this figure and found
**none**: it exists only on this card. **So the figure is restated here as what it is** — a
site-dependent split whose plant line was never recorded — rather than as a reproducible
measurement. **A mutant split without its plant site is not independently checkable**, which is
this card's own subject applied to its own record.

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

---

## Review cycle 1 — **8.5 / 10, CERTIFIES**, 12 findings, **none a defect in shipped behaviour**

`meta/review/20261030T060000Z-CARD-314-cycle1.yml` (synced under the timestamped convention; the
round wrote it unstamped). Every finding is a **control gap or a claim-accuracy issue** — which is
precisely why a fix round is worth taking on this card and not on another: **this is the card that
makes an exemption provable, so an uncontrolled control is the one defect it cannot ship.**

**Run conditions, stated rather than assumed.** The lock **was held** at start (CARD-304's merge
gate). All 18 mutants ran from an **out-of-tree archive**, where the guard passed honestly because
that tree has no lock of its own — **no override environment variable anywhere**, which is the
standing rule. When the lock cleared the reviewer **re-ran the 733-test radius in the real worktree
lock-free and got an identical reading** — the control proving the archive's numbers transfer.
**No run collected 0 tests.**

### F-001 — the card's own thesis, one notch down, and nothing would notice

**Replacing the tag test with `bool(stack)` — exempt inside *any* marked-content sequence — passes
all 733 tests.** AC-2 proves the exemption is **not by size**; the corollary, **"by THIS mark, not
by any bracket"**, has **no control that can fail.** And the risk is concrete: **`/Artifact` is the
standard PDF idiom** for the next decorative run anyone brackets, and the moment one appears every
face inside it becomes exempt. **A provenance exemption that accepts any provenance is a magic
bracket instead of a magic number** — the same defect this card was cut to remove, one level down.
~4 lines.

### What the brief asked, answered with measurements

- **Can a clue digit reach the stream unmarked? No** — the drawer is the only caller of the entry
  writer, and its only two callers are the puzzle and answer writers, **derived by grep**. A mutant
  drawing the first entry *outside* the bracket reds 5.
- **Can the mark be forged? Yes in principle, caught in practice — but NOT by the guard that claims
  it (F-006).** A raw operator-row append planted in the answer writer **did not red**
  `test_only_the_clue_digit_drawer_emits_the_mark`; **AC-3's instrument caught it incidentally.** So
  the guard's name asserts something it does not perform.
- **The emitter set is DERIVED** — a directory glob, 26 files, exact set equality with a
  non-emptiness guard, scope gap measured at **0 files today**. Hand-chosen: the directory, and the
  assumption that *emitting* means *calling the method* — which is exactly the gap F-006 fell through.
- **Compression round-trip verified off the written file** (`BMC 1`, 204 of 209 faces exempt), and
  the writer's refusal sits on the real export path. **Nesting works as documented and is completely
  unmeasured (F-002)** — `stack.pop()` → `stack.clear()` survives all 733.
- **No guard was silenced — proved, not read.** A planted **public** stream member reds **6 tests
  across 2 modules**; a planted **private** one reds 0. The stroker set is **unmoved at eight**.
- **All ten `trace.yml` refs resolve by `class` line, 0 dead**; `requirements.yml` **byte-unchanged**
  (G-1). **G-5's mechanism holds, not just its count**: `PageKind` has 7 values and all 7 are
  declared, undeclared `[]`.
- **The card's scope-correction premise is stale — confirmed.** Re-derived out of tree at the fork
  point: the guard reads against a derived kind set that evaluates to both kinds, and the answer-page
  test is live. **The round was right and the card's paragraph describes a state that had already
  stopped existing.**
- **The render reproduces**: **0 differing pixels of 2,103,750**, max abs diff 0, text layer
  byte-identical, **+26 bytes** — and the reviewer looked at the page: band, grid, clue digits, frame
  rules, footer, folio, QR group all present.
- **Every re-derived figure is exact**: 462 / 644 / **1106**, answer **580** vs puzzle **526**; the EC
  corpus's 18 pages, **3557** exempt faces, **11** distinct sizes, **4 above the floor** (10.56,
  11.04, 12.96, 13.20), 2629 below, 67 non-exempt at min 10.08; node ids **317 → 330, +13 / 0 / 0**;
  and all four of the card's own mutant splits reproduce.

### The other findings

**F-003 — a shipped assertion that cannot fail, and it is dead twice over**: an `or True` makes it
unconditional, **and its left operand is always False anyway**, because it tests the tag's *value*
against a set of *attribute names*. It sits **inside the class that holds the mark's authorship**.
**F-005 — the 46/47 split is module-scoped and reads as whole-radius**: across 733 tests the same
per-digit drawer reds **4 tests in 2 modules**, the three extra being this card's own operator-economy
derivations. **The division is still correct** — all four are economy claims and **no AC-bearing test
rises**. **F-007 — the round's own correction #5 overstates its hazard**: proven by mutant, that test
would have gone **RED**, not silently vacuous. **F-008** — AC-2's docstring describes a plant through
the stream's text method when it is appended as a raw operator row. **F-011 — the "1080 operators on a
30×30" economy figure is measured nowhere**: real 30×30s give **449–468** and the rendered page
**204**. **F-010** — "each reclassification carries its own measurement" is one guard too broad: one is
a filing decision whose measurement lives in another module. **F-009** — a dead local and its `del`.
And the card's **M4 figure is plant-site-dependent with its line unnamed**, so it is **not
independently checkable** — the reviewer's own plant site gives 4/43 against the card's 2/45.

### F-004 — WITH THE OWNER, because it asks to break this card's own G-6

The two tests whose names now sit off their bodies. **The reviewer ruled against the round**: the
names are true only of the **mutated** page the test builds; of the page **this card ships**, the
opposite is true **and is the card's headline**. It argues **G-6's purpose — coverage cannot vanish —
is not violated by a *declared* rename**, and that CON-020's `covered` trace row is exactly where
someone resolves which test means what. **G-6 forbids renaming in plain words**, so this is not the
round's to settle and not the orchestrator's.

- [Review 1/3] Score: 8.5 ✓ threshold reached, certifies, 0 defects in shipped behaviour
- [Fix 1] Dispatched on F-001, F-002, F-003, F-005, F-006, F-007, F-008, F-009, F-010, F-011 and the
  unnamed M4 plant site. **F-004 excluded and escalated.**

---

## Fix round 1 — `7f40f30f` → `d5a5affc`, 4 files, +337/−28

Ten of twelve findings discharged in-tree. **Nothing in shipped behaviour changed**: the only `src/`
edit is a docstring, the 21 baselines are byte-identical, and the render stands — **no new eyeball
owed.** Lock checked by absolute path before every one of 18 runs, absent each time; **no run
collected 0.**

### F-001 — the control exists now, and the mutant that used to survive reds

| tree | mutant | result |
|---|---|---|
| `7f40f30f` | the tag test → `bool(stack)` | **733 passed, 0 failed — survives** (reproduced cycle 1 exactly) |
| fixed | same | **1 failed, 736 passed**, riser = the new test **and only it** |

Two directions in one test: the same face under `/Artifact BMC` against `/ClueDigit BMC`, and — on a
**real puzzle page** — a sub-floor face inside `/Artifact` comes back **reported, not exempted.**
The planted size is **read off the page**, not written as a literal.

### F-006 — the review UNDERSTATED this, in the harder direction

**This is the thing fix round 1 found that cycle 1 got wrong.** Cycle 1 said the forgery *"is caught
in practice, but not by the guard that claims it"*. Measured with a **balanced** plant — the mark
operator *and* its closer appended as raw rows — on `7f40f30f`:

- floor module alone: **47 passed, 0 failed**
- whole 733-test radius: **733 passed, 0 failed**

**So the general raw-append forgery was caught by nothing.** Cycle 1's own mutant reddened 2 only
because its plant left AC-3's refusal unable to fire — **a forgery that brackets nothing is
invisible.** `7f40f30f` had **three** surviving mutants, not two.

Fixed: **1 failed, 736 passed.** Two new tests, and **the guard's claim narrowed to what it
performs** (a *call* to the emitting method), naming the literal check beside it and naming what
neither reaches (a token assembled at runtime — kept small because the operator list is private).
The scope test measures the hand-chosen directory against **every file under `src/nonogram/` whose
text names the stream type** — **0 difference at this commit** — with a planted probe file as its
positive control and the same file naming something else as its negative. **And it reads the AST with
docstrings excluded, because a text grep reds on the drawer's own prose** — a trap measured, not
guessed. The operator pattern uses an **explicit delimiter class, not `\b`.**

### F-002 — nesting, documented four times and controlled nowhere

`stack.pop()` → `stack.clear()` **survived all 733**; now reds exactly one new test. The load-bearing
case is **the face after the inner closer** — still inside the outer sequence, so still exempt,
which is precisely what a flag gets wrong.

### F-003, and the restated figures each with their domain

F-003's dead assertion is **deleted**, with a comment saying why **both halves** were dead; nothing
remains to mutate. **F-005**: re-derived at both scopes — floor module **1/46**, whole radius
**4/729**, risers named — and the economy comment now states **4/733 with 1/47 named as its
one-module reading**, with each of the three extra risers gaining a docstring line saying a per-digit
mark reds there **by design** and is an economy claim, not a correctness one. **F-011**: the
540/1080 figure was measured nowhere; re-derived, the bound on a 30×30 is **at most 900 entries**,
the EC corpus's three 30×30 pages set **456 / 449 / 468**, and the baseline page sets **204**. Both
sites now state it as a bound with the measurements beside it. **F-008**, **F-007** (downgraded to
what was measured — the hazard was a **RED**, not a silent vacuum), **F-010** (narrowed: one of the
four is a filing decision whose measurement lives in another module, now pointed at by name), and
**F-009** all corrected.

### Instrument proofs, both ways

Positive: the three mutants above each red **exactly one** new test and nothing else. Negative,
**all 51 passing in the floor module**: a same-meaning different-spelling rewrite; an equivalent pop;
and a literal planting the operators as **inner substrings** of longer words, which the boundary rule
must not match.

### Guardrails and figures

**G-1** `requirements.yml` byte-unchanged. **All ten CON-020 trace refs resolve by `class` line with
their line numbers reported, 0 dead** — which matters because **gate 3 there is `Severity.ERROR`**.
**G-5: all 21 baselines unmoved**, `git status --porcelain tests/fixtures/` empty. **G-6**: nothing
deleted, renamed, skipped or merged. **Node ids over the three touched modules: 179 → 183, raw +4 /
0 removed / 0 renamed, net +4** — all four new `def`s, none parametrised; radius 733 → 737.
**Skips: 0** in that radius under both conditions. **CORRECTED by fix round 2: the 733/737 radius
figure does not reproduce.** No import-derived file set reproduces it — the nine test modules naming
the stream modules or the vector reader collect **716** (712 before round 1's +4), and adding the
interior-cover module gives 849, with no single further book module supplying the missing 21. Round
2 therefore **states its radius explicitly rather than quoting an inherited one**. **Round 1's
delta is unaffected** — `+4 raw / 0 removed / net +4` re-derives, because a delta survives a
mis-stated denominator. This is the day's dominant family once more: a figure carried without its
domain, inside the card that exists to stop exactly that. Runtime as ranges with conditions, ±15%
host spread, **no load figure**. Mutants out of tree, needle uniqueness asserted, blob shas restored
and asserted back, `diff -rq` against a pristine extract empty, **no `git stash`**.

### Open after this round

**F-004** untouched by instruction — now **authorised by the owner** (see below). **F-012** untouched
and rated a nit, its non-vacuity carried by a companion floor whose margin is real: **3557 exempt
faces against a 1000 floor.** And **the card's M4 figure is still not independently checkable** — it
reports 2/45 for "the frame drawer" **without naming a plant line**, while the reviewer's
folio-drawer plant gives 4/43. That figure is the orchestrator's, on the card.

## OWNER DECISION 2026-10-30 — G-6 overridden for two test names, declared

**The owner has authorised a declared rename of exactly the two tests cycle 1's F-004 names.** G-6
remains in force for everything else.

The reasoning accepted: **the names are true only of the mutated page the test builds; of the page
this card ships the opposite is true, and that opposite is the card's headline.** G-6 exists so
coverage cannot vanish, which a *declared* rename does not do — and CON-020's `covered` trace row is
exactly where someone resolves which test means what.

**The condition attached:** the node-id delta must be stated **raw and net**. This card has had **0
removed** until now, and a rename is **2 removed and 2 added, not zero** — netting it away is the
defect this board corrected twice today on other cards.

- [Fix 2] Dispatched on the rename alone, with the trace row re-stamped and every reference derived.

---

## Fix round 2 — `d5a5affc` → `8d6ce8f7`, 1 file, +54/−23. **F-004 discharged under the owner's override.**

**No `src/` file touched at all**, so no byte of any page moves, **the 21 baselines are unmoved** and
**no render is owed**. `requirements.yml` byte-unchanged (G-1). Lock absent before every run; no run
collapsed to 0 collected.

### The two renames, with the reasoning for each name

Both in `TestInteriorType_TheStreamArmIsReached`:

1. `…_refuses_rather_than_reading_its_clue_digits` → **`…_with_no_clue_digit_mark_is_refused`**.
   The body drops the mark at its one chokepoint and asserts the reader raises, so the **new name
   names the helper the body actually uses** — condition and name become the same fact. The old
   clause *"rather than reading its clue digits"* was **the pre-card contract CARD-299 shipped and
   this card reversed**: the page it ships **is** read.
2. `…_answer_page_refuses_too` → **`…_answer_page_with_no_clue_digit_mark_is_refused_too`**. `_too`
   is kept deliberately, because the test's reason for existing is **kind coverage** — 258 of book
   1's 462 exempt sub-floor faces are on answer pages against the puzzle page's 204 — but the name
   **no longer implies the shipped answer page is refused.**

### The delta, stated the way the owner's override required

**Raw: 2 removed, 2 added. Net: 0** (radius 716 → 716). **Not netted away**: the card stood at 0
removed until now, and **two node ids a reader may hold a reference to no longer exist.** No
`parametrize` id moved — the delta listing is exactly those four lines.

### References derived, and one that was already broken

Every tree-wide hit for each old name was resolved. **In-tree code: one, and it was dead before this
round** — the puzzle test's own docstring cross-referenced a `:meth:` **that has never existed**,
shipped by the implementation commit. Fixed in passing.

**`trace.yml` carries CLASS names only, so neither old name appears and the re-stamp was not owed** —
the file is byte-unchanged against both `d5a5affc` and `main`. And the round **declined cycle 1's
fallback suggestion** of writing method names into that file's note, for the right reason: *"the
check-ref search is a text search, so a method name written into trace.yml prose is exactly the
mechanism that revives a dead ref later."* **All ten CON-020 refs re-resolved by `class` line, 0
dead**, each with its line reported; gate 3's `Severity.ERROR` is not at risk.

Past cycles' review YAMLs and CARD-299's card keep the old names **as historical records** —
*"rewriting a past cycle's measurement would falsify what was measured under which name."*

### Both renamed tests shown red on their missing-mark mutant, with a near-miss that must not rise

- **Harness negative control**, unmutated extract: **51 passed** — it does not red on its own.
- **Positive**: `exempt` read off the **size** instead of the mark — *literally the "exempt 8.64 pt
  by its value" wrong answer the reader's own message names* — **7 failed / 44 passed, both renamed
  tests among the risers**, one on its anti-vacuity guard and one on `DID NOT RAISE`.
- **Near miss**: the same wrong answer at a threshold **no face on these pages reaches** — **10
  failed / 41 passed and neither renamed test rises.** So the pair is keyed on the exemption
  actually appearing on a mark-less page, **not on the reader merely being touched.**

### Four things it measured wrong, two of them mine

1. **The stale-note attribution was mine.** My brief said fix round 1 left the note; `git blame` puts
   it on **the implementation commit**. **Round 1 is clean here** and never touched these two tests,
   exactly as it reported.
2. **A dead `:meth:` cross-reference shipped by the implementation commit** — fixed in passing.
3. **Round 1's 733/737 radius does not reproduce** — corrected above.
4. **Cycle 1's riser count for the size-keyed mutant has moved from 5 to 7, for a named reason**: fix
   round 1 added two tests that rise on it. **A figure that moved because the tree grew, with the
   growth named** — which is the honest form.

**Skips: none** — 0 in the 716-test radius and 0 in all three extract conditions. Runtime as ranges
with conditions, ±15% host spread, no load figure. Mutants out of tree, blob recorded and **asserted
back**, needle unique, `__pycache__` swept, **no `git stash`**.

- [Fix 2] `8d6ce8f7` — **eleven of cycle 1's twelve findings discharged in-tree**; the twelfth was the
  card-resident M4 figure, corrected above by the orchestrator.
- [Gate] Merge gate next, held only until CARD-269's review cycle 2 reports — the gate takes the
  scope-blind lock and would collapse that review's runs to 0 collected.

---

## Merge gate round 1 — **RED, 2 failed**, and the cause was this card's own unpaid bookkeeping

Gate at `368b1997`: **2 failed, 9846 passed, 27 skipped, 1 xfailed** in 22:10. AC/EC **68 passed, 0
skipped**; **G-5's 21 book baselines unmoved**; `src`+`tests` byte-identical to the gated commit.

Both failures were in **CARD-308's frozen ref census**, and both were **+3**: `DEFINED` measured
**395** against baseline 392, `TRACE_TESTS` **513** against 510. The three are this card's own — the
implementation commit re-stamped CON-020's trace row with three added classes and **nobody updated
CARD-308's baselines.**

**Nobody inside a review cycle could have.** `tests/test_check_ref_resolution.py` is not in this
card's impact radius, so **the per-cycle scope was structurally unable to see it and the merge gate
is exactly what did** — the two-tier design working as designed, and worth recording on the day the
lock that tier costs blinded three rounds.

### Fix round 3 — `368b1997` → `8d70e2b0`, and the brief was wrong about the count

**THREE baselines moved, not two.** `CENSUS` is asserted **inside the same test**, three statements
*after* the `TRACE_TESTS` assert — so **the first failure short-circuited it and CENSUS never
appeared in the gate log at all.** Updating only the two the log named would have **re-reddened that
same node on the next gate with a fresh `(586, …)` surprise.** That is a latent failure found by
reading the test rather than the log, and it saved a whole 22-minute gate.

**The base was chosen for a reason and the reason is checkable**: the merge's **second parent**, i.e.
`main` exactly as merged in — defensible **not because it is nearby but because it reproduces all
three stored baselines byte-identically**. Derivation ran out of tree, loading **each tree's own
copy** of CARD-308's module and calling its own `_declared_refs()` / `_verdicts()` / `_fingerprint()`
— no reimplementation.

**The symmetric difference is the same set for all three classes: exactly three enter, nothing
leaves.** All three are declared by **`trace.yml` alone** — no `requirements.yml`, no ADR — so
`586 = 583 + 3` with **no term cancelling**, and the other authorities are unmoved. *"One declaration
event arriving with its definitions already in place — the one direction that needs no repair."*

**Proved in both directions, two mutants, out of tree.** Removing one `tests:` entry gives 2 entering
on both classes; renaming one `class` line gives 2 entering on `DEFINED` **while `TRACE_TESTS` stays
at 513** with 3 entering. **Both differ from the clean tree and from each other — same count, different
digest — so the declaration half and the definition half are independently measured.** A derivation
blind to either would have reported 3-in on at least one mutant.

All three resolve to real `class` lines **read off the line, not text-searched**, and all three are
live: `-k` on them gives **25 passed**. **All ten CON-020 refs re-resolve after fix round 2's
rename, 0 dead.** The three refs are **deliberately not named** in the baseline comments, and G-2's
own test passing is the mechanical proof of it. **Node-id delta 0/0 raw and net** — the change is
comments and three literals.

### Two more corrections, both mine

1. **The brief said two baselines; it is three.** Corrected above.
2. **The brief cited the wrong precedent commit** for the file:line-without-names convention — it is
   CARD-304's fix round **1**, not round 2; round 2 does not touch that file.

### Flagged, deliberately not acted on

**`ADR-0039:275,287` still states the census as 580.** CARD-304 moved it to 583 and did not re-stamp
the ADR either, so it is **now stale by +6**. The round's judgement, which I accept: *"a mechanical
fix round is the wrong place to re-stamp an ADR"* — and the ADR frames it as an as-of-a-named-tree
figure, so it is a historical measurement rather than a false claim. **But ADR-0039/R4 is the rule
that a figure recomputed and refuted is retracted everywhere it was written, and this is a stale
figure inside ADR-0039 itself.** Recorded on CARD-319.

---

## Merge gate round 2 — **GREEN**, merged `8762beed`

Gated commit **`8d70e2b0`**. **9848 passed · 27 skipped · 1 xfailed · 0 failed** in **21:16**;
AC/EC by node id **68 passed · 0 skipped**; **21 baselines unmoved**; `src`+`tests` **byte-identical**
to the gated commit, before the merge and on `main` after. All 27 skips read from the log.

**The empty failure list is trustworthy this time, and that is the point of the repair**: the gate now
prints the verdict line beside it, so *"no failures listed"* and *"0 failed"* corroborate each other
rather than the first standing alone.

### What this card ends up having been

**CON-020's exemption was keyed on the drawing function, and a PDF content stream records no
provenance.** CARD-299 therefore refused a vector page **by name** rather than report ~205 false
violations or exempt 8.64 pt **by its value** — correct, and a hole with a date on it. This card
closes it: the clue digits now **say so in the stream**, and the exemption is **by the mark, never by
the size**. The proof that it matters is in the EC corpus — **four of eleven exempt sizes are ABOVE
the floor**, because a clue digit does not stop being one on a larger trim, which is why a size key
was never an option.

**Its own thesis came back at it twice.** Cycle 1 measured that replacing the tag test with
`bool(stack)` — exempt inside **any** bracket — passed all 733 tests: **a provenance exemption that
accepts any provenance is a magic bracket instead of a magic number.** Then fix round 1 measured the
review **understated** its sibling finding: a *balanced* raw-append forgery survived the **entire**
radius, so that tree had **three** surviving mutants, not two. Both are closed with controls that red.

### Three orchestrator figures corrected on this card

The scope-correction premise was **stale** (CARD-299's fix round already covered both page kinds);
`Touches` was **wrong in three ways and short by five files**; and **M4's mutant split is
site-dependent** with its plant line never recorded — 2/45 against a reviewer's 4/43 from a different
site. All three were my figures, not the rounds'.

### The gate earned its place today

Round 1 went **red on bookkeeping no review cycle could have seen** — three trace refs this card
added, against CARD-308's frozen census, in a module outside this card's impact radius. **The
per-cycle scope was structurally blind to it; the gate was not.** And the fix round then found a
**third** baseline the gate log could not show, because it is asserted after the one that
short-circuited.

**Not closed here, by design:** ADR-0042/R1 stays unflipped — all seven `PageKind` values are still
declared raster, so **nothing in production changes medium today**. This card makes CARD-309's
conversion **safe for CON-020**; it does not perform it.
