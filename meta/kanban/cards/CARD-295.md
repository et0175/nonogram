# CARD-295: The puzzle page as operators — the grid, the frame, the clue digits and the band, drawn from the Layout it is handed

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/295-puzzle-page-as-operators
**Worktree:** — (removed at merge)
**Source:** ADR-0042 (DEC-048), 2026-10-25; CARD-293's spike §6 item 3. Cut by the architect/decompose pass that followed the ADR's acceptance.
**Idea:** —
**Wave:** 61
**Created wave:** 60
**Deferred waves:** 0
**Depends on:** CARD-294
**Touches:** src/nonogram/admin/book_pdf_generator.py, tests/test_book_puzzle_frame.py, tests/test_book_pdf_band.py, tests/test_book_cell_size.py
**Review score:** —
**Started:** 2026-10-26
**Closed:** 2026-10-26
**Actual:** —
**Merge commit:** `ec6e4a06`
**Blocked by:** —

## What to implement

The puzzle page — the book's dominant page kind — drawn as PDF content-stream
operators instead of a 25.2 MB raster bitmap written as a JPEG XObject.

The spike already prototyped exactly this page and measured it:
`scripts/card293_vector_probe.py`, **1.37 ms against 11.7 ms per page**, **407,976
B against 9,157,535 B for 24 pages**, and the clue digits rendered and read back
by poppler. This card productionizes that, consuming CARD-294's vocabulary.

1. **The grid** — cell lines, every-fifth-line rules, the outer border, at the
   weights and tones COMP-007's `Layout` states. See G-2: this card changes no
   weight.
2. **The frame** and the clue gutters.
3. **The clue digits**, set in the embedded face at the point size the layout
   gives, inside the clue cells.
4. **The band** — "Puzzle N · Tier" (ADR-0037/R1: the puzzle page never prints
   the picture's title; the answer key is the only place the title appears).

**Every coordinate, width and tone comes from `compute_layout` with the book's
PageSpec.** This card computes no geometry — ADR-0042/R3 restates ADR-0036/R2 for
exactly this reason: *a fresh renderer is where geometry gets re-derived by
accident.* If you need a number the `Layout` does not give you, that is a finding
to raise, not a number to compute here.

## Acceptance criteria

- **AC-1** (the page carries no bitmap): *Given* an interior whose puzzle pages
  are written by this card, *then* no puzzle page references an image XObject.
  (test: `TestPuzzlePage_CarriesNoImageXObject`. ADR-0042/R1's own derived test is
  CARD-298's, which checks *every* interior page kind at once; this one is the
  page-local control that fails first.)
- **AC-2** (the drawing is the layout's, not the writer's): *Given* a `Layout`,
  *then* every line position, stroke width and grey tone in the emitted content
  stream equals the value the `Layout` states, compared against an **independent**
  recomputation rather than against the writer's own output. (test:
  `PropertyTest_PuzzlePage_EveryCoordinateComesFromTheLayout` — genuinely
  multi-case over a seeded corpus of extents, trims and densities, with a minimum
  case count asserted inside the test so the corpus cannot silently shrink.)
- **AC-3** (the clue digits are right, and read by an engine that did not write
  them): *Given* a puzzle page, *then* each clue cell's digits match
  `clues.encode_line` for that row/column, read back from the rendered PDF by
  poppler. (test: `TestPuzzlePage_EveryClueDigitRendersWhereTheLayoutPutIt`. The
  spike did this with 540 digits; keep that order of magnitude.)
- **AC-4** (the band says what it always said): *Given* a puzzle page, *then* the
  band shows the number and tier and **not** the picture's title. (test:
  `TestPuzzlePage_BandCarriesNumberAndTierAndNeverTheTitle` — ADR-0037/R1.)
- **AC-5** (the interior shrinks, measured): *Given* the Book 1 corpus, *then*
  the written interior's puzzle-page bytes and generation time are recorded
  against the raster figures, and the direction matches the spike's. (**gate**:
  the two figures recorded with the load average at both ends, per CARD-292's
  AC-6 convention. A regression against the spike is a finding, not a rounding
  error.)

## Engineering constraints

- **EC(ADR-0042/R3):** the writer derives no geometry, for any page in any book
  profile — not a fallback, not a rounding, not a default when the `Layout` is
  silent. test: `PropertyTest_PuzzlePage_WriterDerivesNoGeometry` (multi-case: a
  `Layout` stub whose every accessor is recorded, asserting the stream contains no
  number the stub was not asked for).
- **EC(ADR-0042/R1):** no interior page this card writes references an image
  XObject, at any page count. test: AC-1's test, extended over the corpus.

## Guardrails

- **G-1: do not change a single rule weight or tone.** The instruction is
  unchanged by the owner's 2026-10-25 decision, but its **reason** is now the
  opposite of what it was, so read it again rather than from memory.
  **It was:** the weights were undecided, so nobody could ship them.
  **It now is:** the weights **are** decided — the owner chose 0.3 / 0.8 / 1.3 pt
  on CARD-293's proof, and ADR-0037/R2 carries them — but **CARD-227 is the card
  that lands them**, one wave after this one (wave 62). This card draws the grid
  at **the weights COMP-007 computes today**, so that the weight change arrives
  as one reviewable diff in one place instead of being smuggled into the medium
  change where no test is watching for it.
  There is also a concrete cost to grabbing it: **CARD-298 records the book
  baselines once**, deliberately after CARD-227, so a single recording captures
  both the medium and the widths. Shipping 0.3 pt here makes the phase pay for
  two baseline recordings and muddles which change moved which bytes.
- **G-2: do not touch `src/nonogram/export/**`.** The `Layout` is consumed, never
  changed. CON-019 holds the CLI and web exports byte-identical.
- **G-3: do not touch the cover or the dividers.** Raster by ADR-0042/R2 and by
  the owner's 2026-10-25 decision respectively. Read
  `meta/profiling/adr-0042-migration-census.md`'s "What is not in the set".
- **G-4: do not convert this file's pixel assertions wholesale.** The three test
  files in `Touches:` hold **50 pixel-reading sites** between them
  (`test_book_pdf_band.py` 41, `test_book_puzzle_frame.py` 7,
  `test_book_cell_size.py` 2). Convert the ones about **this page kind**, leave
  the rest, and do not reach into files this card does not own —
  `test_book_solved_answer_key.py` (47 sites) is CARD-297's.
- **G-5: no test deleted, renamed, skipped or merged — including `parametrize`
  ids.** The collected node-id set loses nothing. (**gate**: set difference with
  `-o addopts=''`; removals 0, additions named. **A reworded param id is a deleted
  node id** — CARD-282's fix round nearly shipped exactly that.)
- **G-6: corpus minimums are never lowered;** `tests/fixtures/**` is never
  regenerated.

## System contract (subset — the pipeline re-derives the full list at dispatch)

- ADR-0042/R1 — interior pages are operators; no image XObject (check: review-lens → CARD-298)
- ADR-0042/R3 — the writer consumes positions and derives none (check: review-lens)
- ADR-0042/R7 — no rule weight is set here; ADR-0037 is not revised (check: review-lens)
- ADR-0036/R2 — book page geometry is COMP-007's `compute_layout` with a PageSpec (check: review-lens)
- ADR-0037/R1 — the puzzle page never prints the picture's title (check: review-lens)
- CON-018 / INV-006 — the printed cell never falls below 4.75 mm (check: TestBookCellSize_HoldsTheFloor)
- CON-020 — no interior text below 10 pt, clue digits excepted — their size follows the cell (check: TestInteriorType_EveryFaceHoldsTheFloor)
- CON-019 — book geometry never changes the CLI's or web UI's exports (check: PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry)
- ADR-0039/R1 — a claim needs a control that CAN fail (check: review-lens)
- ADR-0006/R1 — the dependency baseline is exactly stdlib + Pillow + NumPy (check: TestDependencyBaseline_IsExactlyPillowAndNumpy)

## Architecture context

- **FR:** FR-033 (the puzzle page's band and line thresholds — **its figures are untouched here**, see G-1), FR-041 (the printed grid's rules)
- **NFR:** NFR-008
- **ADR:** ADR-0042 (R1, R3, R7), ADR-0036/R2, ADR-0037/R1, ADR-0039/R1
- **Components:** COMP-009; COMP-007's layout consumed
- **Trace:** meta/architecture/trace.yml

## Worktree notes

- `src/nonogram/admin/book_pdf_generator.py` is a `conflict.hotspot` and every
  card in this phase touches it — `run` serializes them whatever the wave says.
- The spike's 41-line content-stream assertion is the model for AC-2's shape, and
  it **passes at 0.48 pt and fails at 0.3 pt** (its AC-4), so it discriminates on
  exactly the quantity G-1 forbids changing. Reuse the shape, not the thresholds.

## [Routed in from CARD-294 cycle 2 — 2026-10-25, N-2] `_cap_height`'s three paths, two of them uncontrolled

**CORRECTED 2026-10-26: this is CARD-296's, not yours.** It was written here
first, on the orchestrator's claim that you are "the first card that centres
strings on `FontMetrics`". You are not: wave 61 is ordered **guide-first**, so
CARD-296 runs before you, and its item 3 draws *"the explanatory body text and
headings, in the embedded face"*. The full routing now lives on **CARD-296**.

**You inherit it only if CARD-296's round declines it** — which that card is
told to do explicitly rather than silently. Read the rest of this section as
background either way, because you set the clue digits in the same face and the
silent-zero hole below would reach them too.

CARD-294 fixed a real 10.8 % error in `_cap_height` (`src/nonogram/admin/book_vector.py`):
`font_metrics` had fallen back to `0.7 × ascender`, and the bundled DejaVuSans
ships `OS/2` **version 1, 86 bytes, with no `sCapHeight` at all**, so the
fallback was *always* what shipped — **650**/1000 em where FreeType measures
**729**. It now reads `H`'s own `glyf`/`loca` bounding box and reproduces
FreeType exactly. The existing poppler control had absorbed the error because
its tolerance is 15 % and the error was 12.2 %.

**What CARD-294 did NOT control, measured by its cycle 2 and inherited by you:**
the function has three reachable paths and the shipped face exercises exactly
one (`OS/2` v1; `indexToLocFormat` **1**, i.e. long `loca`). Uncontrolled:

1. the **`OS/2 ≥ 2` branch** — which CARD-294's card *states* as behaviour
   ("version ≥ 2 still wins where a face has it") and no test exercises;
2. the **short-`loca`** branch (`indexToLocFormat == 0`), reviewed against spec
   but never executed — there is no short-`loca` face in this repo;
3. **both raises.**

All three were judged **correct on review**, so this is missing controls, not
missing behaviour. One residual hole is real rather than cosmetic: **a v2+ face
with `sCapHeight = 0` returns 0 with no fallback and no error** — a silent zero
in the number every string on your pages is centred on.

**Why it is yours and not CARD-294's:** the project ships exactly one face, and
at CARD-294's merge *no module under `src/` imports `book_vector` at all*, so the
risk was nil and the control had no consumer to be written beside. You give it
one. If you centre anything on `cap_height`, the cheapest honest control is a
synthetic face per branch (a v2 `OS/2` carrying a real `sCapHeight`, one
carrying `0`, and a short-`loca` face) rather than a comment asserting the
branches work — CARD-294's own cycle 1 critical finding was a control that could
not fail, and its cycle 2 N-1 was a figure whose scope was hand-held.

If you decide these controls are not yours either, **say so with a reason and
name who owns them** rather than passing them on silently: a declaration that
outlives its hole is the defect this board gates on most.

## [DISPATCH 2026-10-26 — wave 61, orchestrator] The grid routine's direction has REVERSED

**CARD-296 is PARKED, not merged**, so `src/nonogram/admin/book_guide_vector.py`
and its `draw_line_diagram` are **not on main** — they exist only in a kept
worktree at `0b91ab18`. CARD-296's AC-4 says *"CARD-295 should consume it rather
than write a second one"*. **That is now backwards.** You write the routine; the
card that re-enters consumes yours.

So: make it **consumable**. A routine that takes a `Layout` plus what to draw and
knows nothing about a puzzle page specifically is one CARD-296 can adopt; one
shaped around your page is a second implementation by another name, and that is
exactly what CARD-296's AC-4 exists to prevent.

**What IS on main:** CARD-294's vocabulary, `src/nonogram/admin/book_vector.py`
— the embedded face, the operator set, `round_mark`, `write_vector_pdf`. Merged
`b850bbbd`. Consume it; do not rebuild it.

**You also inherit CARD-296's F-302**, because you are the card its AC-4 exists
to constrain. Its default-DENY guard over "which routines may read a `Layout`'s
grid" has a measured hole: a frozen dataclass with one `sheet: Layout` field and
a `stroke` method draws a **complete second ruled grid** and passes — the
annotation arm reads *function parameters* only, and the rebinding arm skips an
`AnnAssign` with no value, which is what a dataclass field is. Five more escape
at helper level (tuple unpack, a `Layout`-returning helper, walrus, comprehension
target, `for` target, unannotated default). If you build a guard of that kind,
build it without that hole — or name the limit **by its shape** and say who owns
closing it.

## [Correction to the round's own handback — 2026-10-26, orchestrator]

The round's item 6 ("CARD-297's reuse, as its card words it, does not reach")
is **false**, verified at the source and functionally: `AnswerTile` carries
`vertical_lines`/`horizontal_lines` as `tuple[GridLine, ...]`, and this round's
own `draw_grid_lines` takes **two `GridLine` sequences**, not a `Layout` —
`draw_ruled_grid` is just the `Layout` door onto it. An `AnswerTile`'s lines
drive it directly, with no `Layout` involved.

So the routine's reach is **wider than its author claimed**. This is the first
round in this wave to be wrong by understating its own work; the standing
pattern has been the reverse. Recorded on CARD-297, whose AC-3 needs no change.

## [CYCLE 1 — 2026-10-26] 8.0, NOT CERTIFIED (3 gating). **Card HELD between rounds** on the owner's decision

`meta/review/20261026T104006Z-CARD-295-cycle1.yml`, reviewed `675222c1` + the
main merge `a7f33021`. Cycle 1's own words: *"It is an 8. The implementation is
genuinely good and I found **no wrong number on any drawn page**."*

**The card is HELD, not parked** — committed, worktree kept, no work lost. The
owner chose to run **CARD-292 solo** on a quiet box first, because CARD-292 is a
timing card and every gate verdict this wave rested on figures whose reliability
it measures. CARD-295 resumes at its fix round afterwards.

### The number the phase was waiting for, and it inverts the orchestrator's advice

**The naive-conversion ratio post-cache is 14.54×, FASTER** — measured on HEAD at
identical load averages, with the cache removed in the same session as a control
(stream-per-file falls back to **0.69×**, reproducing the pre-cache 0.71×, so the
sign change is the cache and not the host):

| arm | min | vs ink | the artefact says |
|---|---:|---:|---|
| ink | 22.39 ms | 1.00× | 20.58 ms, 1.00× |
| stream, **a PDF per assertion** | **1.54 ms** | **14.54×** | 29.17 ms, **0.71×** |
| stream, one interior shared | 2.62 ms | 8.55× | 8.33× |
| stream, no file | 0.71 ms | 31.54× | 31.2× |

**And the inversion runs the other way from how I framed it to the owner.** I
said the saving depended on *sharing the written file*. Post-cache the **shared**
arm is the **slower** of the two file-writing arms, because it re-extracts a
24-page PDF per assertion. The surviving guidance is **"parse the shared PDF once
per fixture"**, not "share the file". **F-002 is gating because CARD-299's 283
sites are pointed at this artefact**, whose §3 headline and "item 1" now say the
opposite of what is true.

Credit where it is due: the artefact pins itself to `075b31d9 + this card's
changes`, says "re-run it rather than trusting the table", and its §3 item 2
**predicted ~14.7× to within 1 %**.

### The other two gating findings

- **F-001 (critical) — the cross-medium seam does not read the raster page.**
  `TestPuzzlePage_AgreesWithTheRasterTwin` reads only `hero.found` and
  `hero.layout`; nothing in the module reads raster ink. Mutation M10 reversed
  `png._draw_grid`'s major sort **and** shifted every vertical rule 7 device px,
  so the two media genuinely disagree about order *and* position → **35 passed**,
  while `test_book_puzzle_frame.py` went 2 failed. The class makes the claim AC-2
  already makes. The agreement *was* measured — in the price script's `claim` arm
  — **which nothing runs.** This is load-bearing precisely because it is the G-4
  defence.
- **F-003 (major) — the card's "name who owns them" clause was skipped.**
  `cap_height` appears once in the 2,715-line diff; the decline is substantively
  right (M6 reds 2 of 35, so the ascender/descender rule is held) but **no owner
  was named and no decline recorded**, against the card's own words. One
  paragraph closes it.

### F-004, and it is the third time this claim has failed

A `draw_dot` in `book_vector_draw` built from `begin_path`/`curve`/`close_path`/
`paint` passes **all three** guards. The curve guard matches a `c` *string
literal* that stays in `book_vector` whoever calls it; its companion keys on
`round_mark(`; `curve`/`paint` are in no watched name set. **Two merged prose
claims measured false**, including *"the day a page card draws a vector dot, the
second test here goes red"* — CARD-294's, which the orchestrator personally
endorsed at its merge gate, which CARD-296's fix round then partly retracted, and
which is now false again **by a third route**. CARD-295 made the hole *reachable*:
it created the first `ContentStream` holder outside the vocabulary.

### G-4: cycle 1 UPHOLDS the refusal, conditional on F-001

Its reasoning, which is better than the round's own: G-4 is already narrow
("this page kind"), and the page those three files assert on **is still the
raster page the book ships** until CARD-298 switches the medium — converting now
moves 50 pixel sites onto a page no book contains. The economics G-4 assumed are
gone regardless: those three files hold **13.60 s of 498.02 s convertible
(2.7 %)**, so even at 14.54× this buys **~1.6 %** of the phase's saving, while
`test_book_export_interior_cover.py` alone holds 344.29 s and is no page card's.
**The condition:** the refusal is only safe if the two halves cannot drift, and
F-001 is exactly that drift going unheld. If the board prefers G-4 executed, it
should be executed by **CARD-298 with the medium switch in one diff**.

### DECLINED — 2026-10-26, CARD-295 cycle 1 fix round (discharging the clause above)

**The `_cap_height` controls are not this card's, and this is the declaration
the clause demands.** CARD-296 did not take them; neither does CARD-295.
Cycle 1's F-003 was gating on exactly this omission, not on the decision.

**The reason.** This card centres no string on a cap height, so the controls
have no consumer here either. Every centred mark it draws goes through
`book_vector_draw.set_centred`, which centres vertically on the **ascender /
descender midpoint** — `_middle_em(metrics) = (ascent + descent) / 2000`, the
`928 / -236` the bundled face states — because that is what Pillow's `"m"`
anchor means, and ADR-0042 changes the medium, not the design. A cap-height
centring would put a digit's ink somewhere the raster page does not. That is
not an assertion about the code: cycle 1 planted it (its M6, centring on
`metrics.cap_height`) and it reds two of `tests/test_book_puzzle_page_vector.py`'s
tests, including the poppler placement — so the ascender/descender rule is
held at both ends, by an engine that did not write the page, and `cap_height`
is unreached from every mark on every page this card draws.

**Who owns them**, named by the rule rather than by one card, because two
cards have already been named and neither took them: **the next card that
centres a string on a `FontMetrics.cap_height`** owns the three branch
controls, because that is the card the controls would first have a consumer
on. Known candidates, as examples and not as the set:

- **CARD-296** on re-entry — parked at the time of writing; its item 3 sets
  "the explanatory body text and headings, in the embedded face", and the full
  routing already lives on that card;
- **CARD-297's answer-tile captions**, if CARD-296 stays parked past them;
- failing both, **CARD-294's own module** (`src/nonogram/admin/book_vector.py`),
  which is where the function and its three untested paths live.

**And the hole, named so it does not evaporate with the conditional:** a v2+
`OS/2` face carrying `sCapHeight = 0` makes `_cap_height` **return 0 with no
fallback and no error** — a silent zero in a number a future card will centre
strings on. The two uncontrolled branches (`OS/2 >= 2`; short `loca`,
`indexToLocFormat == 0`) and both raises are still uncontrolled, and the
project still ships exactly one face (`OS/2` v1, long `loca`), so the risk
stays nil until something centres on it. The cheapest honest control is still
a synthetic face per branch, as the routing above says.

## Worktree notes — CARD-295 cycle 1 fix round, 2026-10-26

The implementation round recorded none under the section above — its notes are the
`675222c1` commit message, which is where the merge pass should look. The fix
round's are here.

- **No `src/` file changed in the fix round.** Cycle 1 found no wrong number
  on any page, and all five findings it acted on were in the test tree or in
  the AC-5 artefact. `src/nonogram/export/png.py`,
  `src/nonogram/admin/book_vector{,_draw}.py` and
  `src/nonogram/admin/book_puzzle_vector.py` were each mutated for a control
  and restored, verified by sha256 against cycle 1's own recorded digests.
- **F-004 was declined rather than patched, and the reasoning is on the
  test.** The one-drawing-site invariant is evadable from the module this card
  created, and the three fixes so far each closed the spelling they were
  written against. The route is not closed again here; the two false merged
  sentences are retracted, the hole is named as a set
  (`TestVectorVocabulary_…`'s `UNWATCHED_MARKS`, held against
  `dir(ContentStream)`), and the owner is **CARD-298**, which reads every
  interior page kind's *written operators* — the one side of this question a
  source pattern cannot be fooled about.
- **One figure is owed on a quiet box**: this test file's wall clock.
  `meta/profiling/rank_durations.py`'s `RENDER_HEAVY_SNAPSHOT` entry no longer
  states one, and says why. The file's **bitmap** count is a count rather than
  a timing and is stated: one, shared by five tests.

## [FIX ROUND 1 PRE-GATE — 2026-10-26, orchestrator] PASSED

| check | result |
|---|---|
| **F-001, verified with a FOURTH shape** | an **asymmetric pure translation** — horizontal rules only, +5 px, no order, no extent, no weight, no deletion, no scale — reds exactly `test_the_ink_and_the_stream_rule_the_same_grid`. 1 failed / 39 passed. `png.py` restored, sha `d7cf3f91efd0413a`, matching cycle 1's own recorded digest. |
| `src/` | **unchanged** — `git diff -- src/` empty. Every production file mutated for a control was restored and sha-verified against cycle 1's digests. |
| collection | file 35 → **40**; full tree **9,332** = 9,326 + 6; **0 removed** |
| timing | **none taken**, as instructed. Load averaged **12–32** during the round, higher than the 19 the brief quoted. |

### The round declined F-004 and argued it rather than patching it

Asked for reasoning, it gave the one that holds: **the route is not closable by a
source pattern, and the three failures are the evidence rather than three
accidents.** Widening the tripwire to the *call* buys `curve` and leaves the
polygon route — already measured unclosable by CARD-296, since no vertex bound
separates a dot from a legitimate shape. And `line_to`/`paint` are how a page
draws *anything*, so holding them to one module **forbids the vocabulary's
ordinary use**. The only fact rather than a spelling is the **emitted operator**,
and extending that reading to every page kind is CARD-298's by ADR-0042/R1.

So: **CARD-296's conclusion adopted, CARD-298 named owner** — and instead of a
fourth guard it made the hole a **set** rather than a paragraph.
`test_the_unwatched_half_of_the_vocabulary_is_named` partitions
`dir(ContentStream)`, reads the watched half *from* the dots guard rather than
restating it, and asserts the unwatched five intersect `ALL_DRAW_METHODS` not at
all. It claims no coverage of the route; it claims the hole is **countable** and
that a sixth primitive forces a decision. A sixth primitive named `blob` — in no
Pillow set, so cycle 1's `ellipse` check could not see it — reds **only** that
cell.

**And it re-planted cycle 1's M5 to prove the decline honest**: the `draw_dot`
still passes all three guards plus the import equality, **247 passed**. A decline
that quietly started working would have been the worse outcome.

### Two corrections to my brief, both mine

1. **"the `git add -N` already in place must stay" — there is none.** `git diff
   --cached` is empty and the staged column is clean for every path. I asserted
   a mechanism the round then had to look for and not find.
2. **F-001's remedy said the snapshot comment "has already budgeted for" the new
   bitmap "(it says two)". It had not** — the two it named were AC-1's controls,
   so adding the seam naively would have made **three**. Sharing one fixture
   across all five raster consumers brought the module to **one** bitmap, and the
   comment now says one. The fix made the file cheaper, not dearer.
3. Minor: F-004's suggested widening *"hold `curve/begin_path/line_to/paint` to
   `book_vector.py` as `THE_CURVE_SITE` already is"* **would red on correct
   code** — `draw_frame` and `draw_grid_lines` are the ordinary callers.

### One figure owed to a quiet box

`tests/test_book_puzzle_page_vector.py`'s wall clock. The file moved in **both**
directions — the raster controls stopped drawing a page each, five tests were
added including a poppler run — so cycle 1's 0.46–0.59 s no longer describes it
and the round correctly took no replacement under load. `rank_durations.py` now
states the **bitmap count** (a counter) and drops the wall clock, saying why.

## [CYCLE 2 — 2026-10-26] **9.0, CERTIFIED**, 0 gating. G-4's condition is met

`meta/review/20261026T135745Z-CARD-295-cycle2.yml`, reviewed `defab5c7`.
Aggregate round counter **3 of 6**. *"It is a 9 and it is certifiable."*

**All three cycle-1 gating findings close**, each re-fired on the reviewer's own
mutants: F-001's seam now discriminates on stroke order, grid extent, rule count,
rule width and any non-uniform translation; F-002's addendum arithmetic checks out
(22.39/1.54 = 14.54, /2.62 = 8.55, /0.71 = 31.5, 17.621/0.833 = 21.15); F-005's
M9 now reds **exactly** the new equality where cycle 1 got 35 passed; F-006
confirmed to the pixel (+0.0833 px = 0.02 pt reds both AC-3 cells at 0.005 and
passes at 0.05). F-004's decline re-verified honest — M5 re-planted verbatim,
**247 passed**.

### G-4: the condition is MET, the refusal stands

Cycle 1 upheld the refusal *conditional on F-001*. The seam's one blind spot is a
**uniform** translation inside a seven-pixel window — the reviewer's fifth shape,
+3 px on both axes through both `_draw_grid` and `_draw_frame`, leaves this file
at 40 passed — and `test_book_puzzle_frame.py` catches that **16 ways**. The three
pixel-reading files may stay unconverted beside the stream half.

### The finding CARD-296 was parked waiting for

**The polygon route is CLOSED on the puzzle page.** A 32-gon filled disc planted
into `puzzle_page_stream` gives **7 failed / 14 errors**, because `marks_of` is
default-DENY and raises on the bare `m`/`l`/`h`/`f` lines a path emits. So
CARD-296's F-302 residue is a **cross-page** problem, not a per-page one — which
is exactly the evidence CARD-296's un-parking needs, and it strengthens the case
that ADR-0042/R1's derived check (CARD-298) is the right and only owner. The
reviewer also judged CARD-298 **not** unowned in practice: every page kind
reaching a page before wave 65 has its own artefact-side guard.

### THREE claims of mine corrected, and the third is a fact I never checked

1. **"the seam holds −2 as a constant"** — there is no `-2` in the assertion. The
   width-robust form was a deliberate and correct choice, because CARD-227 moves
   the weights next wave. The real criticism is sharper: the offset is **exactly
   derivable** as `-((heavy - 1) // 2)`, measured at widths 1–8 (run starts
   20,20,19,19,18,18,17,17), so it is **not** an even-width phenomenon — w=5
   offsets −2 just like w=6 — and the docstring's "even-width line-cap
   convention" is imprecise. An exact *and* width-robust equality was available.
2. **"the min-trim cell exercises the smallest type the book prints"** — it does
   not. `MIN_TRIM_CM = 10.0` and the suite ships a 10×10 cm book where a 30×30
   gets cell 23 / clue type **15**, against the fixture's 33 / 21. Residual there
   measured 0.0004 pt, so prose only.
3. **My brief-correction 3 was false, and I asserted it about the codebase
   without grepping it.** I wrote that widening the guard to hold
   `curve`/`begin_path`/`line_to`/`paint` to `book_vector.py` *"would red on
   correct code — `draw_frame` and `draw_grid_lines` are the ordinary callers"*.
   They call `stream.rectangle` and `stream.line`, neither in that family.
   Verified: every reference in `src/` is inside `book_vector.py`, the calls all
   within `round_mark`, and `line_to` has **no caller at all**. **The widening
   would be green today.** The *conclusion* (decline F-004) survives on the
   reviewer's own ground — a guard relaxed one wave later at CARD-296/CARD-229 is
   the fourth instance of the pattern — but my stated reason was invented. The
   merged docstring repeats the same present-tense claim (F-103).

### F-102, which is mine too

The DECLINED section was **not in `defab5c7`** — I reset the card out of the
branch commit (meta/kanban never enters a branch) and the 122 lines lived only in
the worktree. *"The one artefact whose whole point is to outlive the round"*
would not have. Synced to this file before the merge gate.

## [MERGED — 2026-10-26] `ec6e4a06`, and the gate found what two review cycles did not

**Merge gate, attempt 2: 9305 passed, 29 skipped, 0 failed, 0 errors.** Load
2.96 at start, 3.02 at end — the first use of CARD-292/AC-6's convention.

**Attempt 1 was RED**, three tests in `tests/test_book_export_interior_cover.py`,
and the card was certified at 9.0 with 0 gating findings when it happened. All
three came from one new line — `vector_puzzle_pages`' walk default,
`1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT` — which is an **eighth** guide-counting
expression and a **twenty-fourth** page position.

* **Both arms measured before attributing**, which is CARD-292's rule and the
  thing that card exists because nobody did: main carries **19**
  `GUIDE_PAGE_COUNT` loads, the merge result **20**, and the merge adds exactly
  one. Main alone was green.
* **The guards were right and the code was right.** All three are equalities
  built to red when a page position appears; the position one says so in its own
  failure message. Removing the default was the other route and was rejected:
  nothing in `src/` calls `vector_puzzle_pages`, only two tests do, but the walk
  reads `MODULE = src/nonogram/admin/book_pdf_generator.py` alone — so moving
  the expression into the tests would **hide** a page position from the guard
  rather than declare it.
* **Every figure re-measured, not bumped**, by calling the walks directly (a
  pure AST pass — seconds, against the ~470 s the enclosing file costs): sites
  23→24, expressions 7→8, cost sequence 760→**770**, 509→**517**, 203→**204**,
  201→**202**, derived drops (251, 306, 2, 201)→(**253, 313, 2, 202**), module
  call count 816→**832** in prose (deliberately never pinned — an equality there
  reds on any added call anywhere).
* **A trap worth recording.** The edit was applied as 16 replacements each
  anchored on copied text and asserted to occur exactly once, **not** a numeric
  replace: `203` and `201` appear on 10 and 12 lines of that file, almost all of
  them `CARD-201` / `F-201` / `F-203` identifiers. A find-and-replace would have
  corrupted the file silently and plausibly.

### What this says about certification, and it is not about this card

A 9.0 with **0 gating** did not mean "merges clean", because both review cycles
ran a **targeted selection** rather than the full suite. The gate caught a real
consequence of the diff that the round never looked for, and this is the second
time in wave 61 that the gate, not the review, was the thing that found it
(CARD-283's was the first, and that one turned out to be the orchestrator's own
broken `main`). The cheap fix is for a review's scope to include the structural
guard files that a card's `src/` changes touch — those guards are AST walks, not
renders, so they cost seconds. **Owner decision, not this card's to take.**

### One figure stated with its limit

The **29 skips are +2** against the 27 of the three preceding gates, and that
delta is **not attributed**. This card's own files contribute **zero** skips (the
new file runs 40 passed with poppler present, and its only skip mechanism is
`needs_poppler`), so it is main-side drift that would need a full `-rs` run to
place. Recorded rather than called benign, and routed to CARD-292 — whose own
notes already complain that three gate figures were "reported to the owner as a
fact about the tree, each unqualified".
