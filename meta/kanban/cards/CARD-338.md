# CARD-338: The instrument that can measure the end state does not exist, and the one that exists measures a fifth of it

**Status:** in_progress
**Priority:** P1
**Category:** enabler
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** `card/338-the-five-kind-probe-and-the-measured-floor`
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-338
**Source:** CARD-322's re-cut, 2026-10-31, judgement call 3. The re-cut found that CARD-329's session probe lifts `PageKind.PUZZLE` **alone**, built the two-line extension itself, ran the five-kind census, and then declined to absorb it — describing it in prose in all three resulting cards instead. It asked whether to card it. **Carded, because three cards describing the same undelivered instrument in prose is how CARD-309 happened.**
**Idea:** —
**Wave:** 73 <!-- STAMPED 2026-10-31 at dispatch, opening wave 73. Wave 73. Head of the vector chain 338 -> 336 -> 337 -> 322, cut 2026-10-31 at CARD-322's re-cut. Dispatched FIRST in its family because CARD-336's 2d is priced against a one-kind lift and the five-kind census is 225 rather than 151 -- reviewing 336 before this lands would judge it against a figure already known wrong. Intersection EMPTY against every other card on the board. -->
**Created wave:** 72
**Deferred waves:** 0
**Depends on:** —
**Touches:** scratchpad/card338/, meta/kanban/cards/CARD-336.md, meta/kanban/cards/CARD-337.md, meta/kanban/cards/CARD-322.md
**Review score:** —
**Started:** 2026-10-31T12:18:26+00:00
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

CARD-329 built a declaration-lifting session probe
(`scratchpad/card329/probe_puzzle_operators.py`) and it is the only instrument on this
board that can see a converted interior page. **It lifts one kind.** Its own docstring
says so at `:16-21`, and says why:

> Why PUZZLE alone and not the other three interior kinds: … would measure a **REFUSAL**,
> not a converted page, and that is a different experiment.

**That reason is no longer true, and the re-cut pass measured it.** The refusal comes from
one line — `src/nonogram/admin/book_pdf_generator.py:4545`,
`self.pages = NO_DOWNSTREAM_WRITERS if pages is None else pages` — so every generator a
test builds as `BookPDFGenerator(book)` has no downstream writers and refuses the four
non-puzzle vector kinds. CARD-309's assembly point already exports the full set
(`book_interior_vector.py:116`, `DOWNSTREAM_WRITERS`), and that module is a **leaf that
nothing in `src/` imports**, which is what keeps the dependency a direction rather than a
loop. Rebinding the module global in a session probe makes every default-constructed
generator assembled. Two lines.

**Why that matters more than its size.** Three cards — CARD-336, CARD-337 and the
re-scoped CARD-322 — each carry a premise about *the tree after conversion*, and the only
way to measure such a premise is to **stand the counterfactual up**. That is the whole of
this board's subclass-B premise failure: five consecutive cards found their own premise
false, and two reviews independently ruled that the vector family's premises are
"inferences about a tree that does not exist yet", measurable only by building it. This
card builds it once, so three cards stop inferring.

## The measured gap — and whose measurement it is

**Everything in this section was measured by CARD-322's re-cut pass and has NOT been
re-derived by the orchestrator.** It is recorded as that pass's reading, with its
instrument named, and **item 1 below is to re-derive it** — not because it is doubted, but
because this card's entire value is that figures about the converted tree stop being
inherited. Over the identical 20 modules of CARD-329's census:

| | `PUZZLE` only | all five kinds |
|---|---|---|
| modules red | 17 / 20 | **18 / 20** |
| failed + error | **151** | **225** |
| passed | 1224 | 1150 |

Population B is unchanged module for module; the whole **+74** lands in population A, and
the pass bounded it rather than guessing:

- By `ast`, **three** modules reference `_RASTER_DECLARATIONS` directly with **17**
  `monkeypatch.delitem` sites, of which only **two** pass `raising=False`. The rest raise
  `KeyError` once the probe has removed the key — an **instrument artefact**, capped at
  **+13**.
  <!-- REFUTED 2026-11-03 by this card's own item 3; recorded here as the pass's claim.
       The artefact is 0: the identical KeyErrors fire on the E1 tree with no probe loaded.
       And "+13" has no stated step — 17 − 2 = 15 SITES that can raise, of which two name
       DIVIDER, leaving 13 sites; the census separately counts 13 REDS (export_interior 5,
       type_floor 1, pdf 7). Two quantities, neither derived from the other: one site
       produces 5 reds and two (test_book_pdf.py:3747, :3774) are loop delitems over 4+
       kinds each. The +74 share is +11. -->
- In the **six** population-A modules with no `delitem` site at all, the four extra kinds
  add **+61 measured reds**: `solved_answer_key` **1 → 33**, `export_interior_cover`
  **2 → 15**, `pdf_memory` 23 → 29, `guide_page` 1 → 5, `pdf_band` 23 → 26, and
  **`interior_face` 0 (green) → 2**.

**That last row is the sharpest fact here.** `interior_face` is one of the three modules
CARD-329 reports as **fully green** under its probe. Green under a one-kind lift, red
under five. A module reported green by the only available instrument is exactly what
nobody re-checks.

### And a twenty-second module, in neither population

`tests/test_book_interior_type_floor.py` reads **3 failed / 48 passed** under
CARD-329's own PUZZLE-only probe and appears in neither population A nor B. It reaches the
hazard through **the medium decision itself** — a third population both of CARD-329's
filters are structurally blind to (the pass derived four such modules by `ast`; this is the
one outside the census). It carries CON-020's type-floor arm, which is in CARD-322's
system contract.

**So CARD-329's "the arithmetic closes, so nothing is left for a reader to discover" is
true of the 20 modules it chose and not of the tree.** That is a statement about a census's
frame, not a defect in CARD-329 — its arithmetic does close over its own population, which
I verified at its gate. Honest residue by the pass's reading: **154** PUZZLE-only, **228**
at the real end state.

## What to implement

1. **Re-derive the table above** with your own extension, before reading the pass's
   figures as anything but a hypothesis. State the instrument. If your figures differ,
   that is the finding and this card's first output.
2. **Build the extension as a probe that cannot silently measure nothing.** CARD-329's
   probe asserts it found a declaration to lift and refuses otherwise — *"either the tree
   is already converted … and this probe measures nothing"*. Yours must refuse the same
   way for **each** of the five kinds **and** for the writer rebinding: a probe that
   rebinds a global that has been renamed, or lifts a kind already absent, must **fail
   loudly**, never run green over a tree it did not change. Prove it by running the probe
   against a tree where the rebinding target is renamed, and showing it refuses.
3. **Separate the `delitem` residue from the rest of the measurement — and MEASURE which
   side it is on rather than assuming.** <!-- CORRECTED 2026-11-03 by this card's own
   execution; the brief's premise was that these reds are the probe's shadow, and the first
   thing item 3 did was refute it. -->
   The `KeyError` reds from `delitem` sites without `raising=False` were briefed as the
   probe's own shadow. **They are not:** `fidelity_to_the_end_state.py` counted the
   identical KeyErrors on the E1 tree — five entries deleted in `src/`, no probe loaded at
   all — so the probe's artefact is **0** and these are the conversion's residue. Report
   the census with the residue **labelled as its own share** and the sites named, so a
   downstream card prices it as work; do **not** report a `conversion = red − residue`
   column, which is the under-pricing this item exists to prevent.
4. **Classify the +74 by cause, not by count.** Run with `--tb=line` and group by message.
   The pass sampled exactly one cause and it was **new** — `test_book_export_interior.py:546`
   reds with *"no vector guide writer is reachable from BookPDFGenerator … the card that
   converts the guide page (CARD-309) owes the expected side here"*, an **expected-side
   gap** rather than a reader seam, whose message names a card that no longer owns it. One
   sample is not a classification.
5. **Write the resulting floor into CARD-336, CARD-337 and CARD-322**, replacing the prose
   description of this instrument in each with a reference to it and a measured number.
   CARD-322's item 0 already asks for exactly this figure; satisfy it here rather than
   making that card re-derive it on a tree three merges later.

## Acceptance criteria

- **AC-1** — Given the probe, when it is loaded against a tree where any one of the five
  declarations is already absent, or where the writer-rebinding target does not exist by
  name, then it **fails with a message naming what it could not do**, and does not run the
  session green.
  `check: {kind: validator, ref: scratchpad/card338/prove_refusals.py}`
- **AC-2** — Given the extended probe over CARD-329's 20 modules, when the census runs,
  then the per-module failed+error counts are reported for all five kinds lifted, with the
  **`delitem` residue split out as its own column and the sites named** — and, per item 3
  and the `Item 3` worktree note below, reported as a *share of* the conversion's cost, not
  as a probe artefact deducted from it.
  `check: {kind: review-lens}` — owner: whoever reviews this card. The census **reports**;
  it asserts no pass/fail, so a `validator` ref here would be the dishonest kind.
- **AC-3** — Given the census, when the reds are grouped by message, then each group names
  a mechanism and an owning card, and **no group is left as "other"** — an unclassified
  group is a finding to raise, not a bucket to leave.
  `check: {kind: validator, ref: scratchpad/card338/classify_reds.py}`
- **AC-4** — Given the third population (modules reaching the medium decision itself), when
  it is derived, then its membership is **derived rather than listed**, and the derivation
  reds when a new such module is added.
  `check: {kind: validator, ref: scratchpad/card338/derive_medium_population.py}`
- **AC-5** — Given CARD-336, CARD-337 and CARD-322, when this card lands, then each carries
  the measured floor and none describes this instrument as something it will build.
  `check: {kind: review-lens}` — owner: whoever reviews this card.

## Guardrails

- **G-1** — `src/` is not touched. This card builds an instrument; it converts nothing and
  changes no production medium. If the two-line rebinding turns out to need a source edit,
  **stop and raise it** — that would make this a conversion card and it is not.
- **G-2** — `tests/` is not edited. The reds this card measures are the *input* to three
  other cards; repairing one here would take work those cards are priced for and leave a
  census measured against a tree nobody else sees.
- **G-3** — **Do not commit a measurement dump.** The resolver is a `git grep -lw` text
  search over tracked files excluding only `meta/architecture` and `*.md`, so a committed
  census spelling test names **revives dead check refs** — live on `main` across ~245 files
  and carded as **CARD-335**. Keep every dump in the session scratchpad; commit only the
  probe, and only as `.py`.
- **G-4** — The validator of record must read the same before and after. Compare the WARN
  **sets** with `comm` in both directions, asserting both line counts non-zero first — the
  validator indents WARN two spaces, so `^\[WARN` matches nothing and `comm` then compares
  empty with empty and reports clean. An empty `comm -23` half is the proof that nothing was
  revived.
- **G-5** — Do not run the full suite; the censuses here are file-scoped. Never set
  `NONOGRAM_IGNORE_FULL_SUITE_LOCK`.
- **G-6** — `/Users/omelnikova/MyProjects/forge_1` is read-only.

## Notes

**Why this is a card and not a line in CARD-336.** The instrument is small, but three cards
depend on it and its characteristic failure mode is *measuring nothing while reading green*
— which is the failure this board has hit repeatedly (an AC satisfiable by an empty diff; a
guard whose scan hunted byte shapes the writer cannot emit; a mutant that read as surviving
because a stripped `PATH` turned three tests into skips). An instrument three cards will
quote deserves its own judgement rather than arriving as a side-deliverable of the first
card that needed it.

**Chain.** This card is at the head: **338 → 336 → 337 → 322**. It shares no file with any
of them — its only tracked output is a new probe under `scratchpad/card338/` plus the three
card bodies — so it does not serialize on content; it serializes because its output is their
floor.

**What it deliberately does not do.** It does not decide any disposition. Every red it
measures belongs to CARD-336 (the placed-edge mechanism), CARD-337 (the seams and the
non-seam mechanisms) or CARD-322 (the conversion itself). Its deliverable is a number each
of them can trust and a probe each of them can run.

## Worktree notes

**Measured at `f407c350`** (this branch's cut; `main` has since moved on kanban and
repo-hygiene commits that touch no `src/` or `tests/` file, so the tree under measurement
is main's). Instrument: `scratchpad/card338/probe_five_kinds.py` +
`census_five_kinds.py`, one file-scoped pytest run per module, `-o addopts=` as two argv
items, `-rfs` as one flag, the full environment inherited, bytecode off and `__pycache__`
swept at both ends. Two interruptions cost this round its first two attempts; the figures
below survived because they were written down before the third.

### Item 1 — the table re-derived

| over CARD-329's 20 modules | `PUZZLE` only | all five kinds |
|---|---|---|
| modules red | 17 / 20 | **18 / 20** |
| failed + error | **151** | **225** |
| passed | 1224 | **1150** |
| skipped | 1 | 1 |

**Every figure the re-cut pass reported reproduced**, including the sharpest row —
`tests/test_book_interior_face.py` is **0 (green)** under the PUZZLE-only probe and **2**
under five kinds — and the per-module +74: `export_interior` +5, `arrange_page_breaks` +1,
`export_interior_cover` +13, `guide_page` +4, `interior_face` +2, `pdf` +8, `pdf_band` +3,
`pdf_ink_mode` 0, `pdf_memory` +6, `proof_pages` 0, `solved_answer_key` +32,
`trim_persistence` 0. Population B is unchanged module for module. The one skip is the
`setrlimit(RLIMIT_AS)` gate at `tests/test_book_pdf_memory.py:1297`, attributed from
`-rfs`; neither database gate fired, because every run is file-scoped.

**Three figures did not reproduce**, and each is written into the cards that shared it:

1. **The end-state residue is 233, not 228.** The 22nd module is red at **3** under the
   PUZZLE-only probe (reproducing the pass) and at **8** under five kinds; the 228 added
   its one-kind reading to the five-kind 225.
2. **The `delitem` artefact is 0, and the claim was wrong in direction** — see item 3
   below.
3. **Seven uncontaminated modules move, not six** (ten population-A modules carry no
   `delitem` site; seven moved). Their deltas still sum to **+61**.

### Item 2 — AC-1, proved rather than asserted

`prove_refusals.py`, nine cases, each against a copy of `src/` mutated **on disk** and
imported via `-o pythonpath=`, each verifying the module really came from the copy before
trusting its verdict. Eight refuse and name what they could not do: the five
kind-already-absent cases (*"found no declaration to lift for [X]"*), the renamed
rebinding target (*"cannot rebind … no such name"*), a partial writer set (*"has no writer
for ['guide']"*), and the one a `hasattr` check would pass straight through — a
constructor that has stopped reading the global (*"does not hold the rebound writer set …
measures nothing"*). The ninth is a control on the unmutated tree, accepted, so "refuses
everything" cannot pass as "refuses the right things".

### Item 3 — AC-2, and the half the re-cut could not do

`fidelity_to_the_end_state.py` stands the end state up a second way, on disk, without the
probe: **E1** = the five entries deleted; **E2** = E1 plus the default writer set
assembled.

| module | E0 as committed | E1 drop | E2 drop+assemble | probe |
|---|---|---|---|---|
| `tests/property/test_book_export_interior.py` | 0 | 7 (5 KE) | 7 (5 KE) | **7 (5 KE)** |
| `tests/test_book_interior_type_floor.py` | 0 | **25** (1 KE) | 8 (1 KE) | **8 (1 KE)** |

Two readings follow, and both matter more than the census:

* **The probe is faithful: probe − E2 = ±0 on both modules.** The in-process instrument
  reproduces the on-disk end state exactly.
* **The `delitem` `KeyError`s are the conversion's residue, not the probe's shadow.** E1
  carries them with no probe loaded. Calling them an instrument artefact under-prices
  CARD-322 by up to 13.
* **E1 − E2 = 17 reds in one module**, which is the finding below.

### Item 4 — AC-3, no "other" group

`classify_reds.py` maps every red to a named mechanism with an owning card and **exits
non-zero on a cause no rule matches**. 210 of the 233 print a `--tb=line` cause and all
210 classify into fifteen groups. The largest are the medium-blind read that returns empty
(**64**) and the pixel oracle handed a `ContentStream` (**38** via `tests/helpers/page_ink.py`,
**27** in CARD-331's module, **23** in the test modules themselves, **2** via
`two_up_ink.py`); the reader seam proper is **11** unprotected `KeyError: b'XObject'` plus
**2** of CARD-329's named `PageMediumRefused`. The expected-side gap the pass sampled is
**1 red**, not a family.

**The other 23 were an instrument blind spot, found and closed rather than bucketed.**
`-rfs` leaves ERRORs out of the short summary and `--tb=line` prints them in another shape,
so a walk that reads only `--tb=line` saw 210 of 233. Re-run with `-rEfs`: all 23 are
fixture-raised ERRORs (`pdf_band` 10, `pdf_memory` 13) of mechanisms already named — 21 ×
`AttributeError: 'ContentStream' object has no attribute 'tobytes'/'width'` and 2 ×
`assert 5 == (14 + 1)`. `census_five_kinds.py` now prints `unaccounted` as its own column
so the gap can never again sit between two totals.

### Item 5 — AC-4, derived and proved to red

`derive_medium_population.py`'s filter is *a module whose AST names the medium decision
itself* (`page_medium`, `PageMedium`, `_RASTER_DECLARATIONS`). Four modules name it;
`test_book_export_interior.py` and `test_book_pdf.py` are in population A,
`test_book_difficulty_dots.py` in B, and **`test_book_interior_type_floor.py` is the one in
neither** — the third population, derived, not listed. The assertion runs in the direction
that catches a module which *should* be in the population, and it was proved to red: a
synthetic module naming `page_medium`, added to an **overlay copy** of `tests/` (G-2 — the
real tree is not edited), makes the derivation fail with *"a module reaches the medium
hazard through the medium decision and no card has priced it"*.

### The finding that is not a figure

**`interior_generator` has ZERO call sites in `src/`.** Production builds
`BookPDFGenerator(book)` at `app.py:841`, `:960`, `:5580`, `:5759`, `book_proof.py:764` and
`pdf_generator.py:344`, and `:5580` is `generator.export_interior(puzzles)` — the interior
download path. So CARD-322's re-cut §2 — *"the `src/` change is the five registry entries,
and nothing else"* — is **false as measured**: the E1/E2 column above prices the difference
at 17 reds in a single module, every one of them `_drawn_downstream`'s refusal. Written
into CARD-322 §2 as an inline correction. **G-1 held**: this card edited no `src/` file; it
raised the question instead of answering it, which is what G-1 asks for.

### Guardrails

`src/` untouched; `tests/` untouched (the AC-4 proof used an overlay copy); no census dump
committed — only `.py` under `scratchpad/card338/`, and the committed files name test
*modules* only, every one of which is already tracked on `main` in
`scratchpad/card329/measure_probe.py`, `meta/profiling/` and `meta/review/`, so the
resolver's search space gains no name. Validator of record (the `forge_1` copy, read-only,
run in this worktree): **0 errors / 525 warnings before and after** — the 525 is CARD-335's
batched-grep timeout, reproducible and predating this card — with the WARN **sets** matched
by `comm` in both directions over 525 non-empty lines a side, `^\s*\[WARN` not `^\[WARN`,
and **both halves empty**. The full suite was never run; every census call is file-scoped.

### Fix round 1 (cycle 1 scored 7.5, nothing a blocker) — three propagation defects

Cycle 1 broke nothing: every figure it re-fired reproduced to the digit, all six
guardrails held, and no figure in the diff was wrong. All three Importants were the same
shape — **the round measured the right thing and then did not carry one correction into
the places that execute.**

* **F-001, CARD-322's item 1.** The blocker above was written into §2 and into item 0, not
  into item 1 — the one step that performs the `src/` change, which still claimed the walk
  already reaches the writers and routed the refutation back out as *"a finding about
  CARD-309"*. Item 1 now names the decision as CARD-322's own (move the six call sites to
  `interior_generator`, or change the generator's default) and the CARD-309 routing is
  dropped for the downstream-writer case, kept only for a cause this card did not measure.
* **F-002, the instrument.** ADR-0039/R4's retraction clause was applied to four card
  bodies and to `classify_reds.py`'s M1 rule, and not to `census_five_kinds.py`, which is
  the one place a downstream round reads a NUMBER from: it printed
  `conversion = red − artefact`, understating `test_book_interior_type_floor.py` as 7
  (it is 8) and `test_book_pdf.py` as 39 (it is 46), 13 reds over the 21 modules. The
  column is now `delitem=` beside a `conversion=` that is the full red count.
  `derive_delitem_sites.py` carried the identical framing and was not named by cycle 1;
  R4 says *everywhere*, so it is corrected too.
* **F-003, this card's own ACs.** AC-1..AC-4 carried `check: {kind: test}` with no `ref:`,
  unreachable under G-2 by construction, and `kind: test` is the one kind a reader takes
  as mechanically verified. Re-typed: three `validator` refs naming the instruments that
  exit non-zero, and `review-lens` for AC-2, whose census reports and asserts nothing. All
  three `validator` refs resolve under the resolver's own command
  (`git grep -lw <ref> -- . ':(exclude)meta/architecture' ':(exclude)*.md'`), 1 file each.

**AC-3's mechanical reach went from 210/233 to all of it.** The 23 ERROR-shaped reds were
disclosed honestly in prose and attributed by hand; they are now parsed by the census into
the same dump shape (`-rEfs`, `error_causes()`), classified by the same `RULES` table, and
any red still unattributed exits the census non-zero. Measured on the two modules that
carry all 23: `unaccounted=0`, 55 classified against 55 counted, both scripts exit 0.

**G-1 and G-2 held again** (0 files under `src/`, `tests/` not edited) and **G-4 was
re-measured both sides of this round**: 0 errors / 525 warnings, 525 unique `^\s*\[WARN`
lines a side, `comm -23` and `comm -13` both empty.
