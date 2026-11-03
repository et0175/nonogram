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
**Wave:** 73
<!-- CARD-338's Wave: note, moved OFF the field line 2026-11-03 at the merge gate. It sat
     INSIDE the parsed value (`parse_card_fields` strips no HTML comment), so `Wave` read as
     `73 <!-- STAMPED ... -->` and `compute_poached`'s equality test (`fields.get("Wave") !=
     own_wave`) could match no other card's wave. This was the one live case this card's own
     census of 17 contaminated `Wave:` fields found, and it was its own.
     STAMPED 2026-10-31 at dispatch, opening wave 73. Wave 73. Head of the vector chain
     338 -> 336 -> 337 -> 322, cut 2026-10-31 at CARD-322's re-cut. Dispatched FIRST in its
     family because CARD-336's 2d is priced against a one-kind lift and the five-kind census
     is 225 rather than 151 -- reviewing 336 before this lands would judge it against a
     figure already known wrong. Intersection EMPTY against every other card on the board. -->
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
loop. <!-- STILL TRUE AT THIS WRITING, and now carries a pointer (fix round 2, cycle-2
M-103): the leaf property is not only prose here and on CARD-309:597 — it is ASSERTED by
`tests/test_book_pdf.py:3656`
(`TestAssemblyPoint_TheDirectionIsResolvedAndNotHidden::test_nothing_in_the_package_imports_the_assembly_point`,
measured green, that class 5 passed). CARD-322 item 1's option A ends it and reds that
cell; item 1 now names the consequence. If CARD-322 takes option A, this sentence and
CARD-309:597 are what must be re-pointed. --> Rebinding the module global in a session probe makes every default-constructed
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

**Measured at `f407c350`** (this branch's cut). <!-- AMENDED 2026-11-03 at the merge gate
(cycle-3 M-204). This parenthesis read "`main` has since moved on kanban and repo-hygiene
commits that touch no `src/` or `tests/` file, so the tree under measurement is main's".
That was true when written and is NOT true now: CARD-323 and CARD-332 both landed during
this card's review. -->
**`main`'s `src/` and `tests/` HAVE since moved, and the figures were re-checked against
the move rather than assumed safe.** Between `f407c350` and main's tip `fd9cbdfa`, eight
commits from CARD-323 and CARD-332 change **14** files under `src/`/`tests/`
(`admin/app.py` +97, `book_manager.py`, `player_bundle.py`, `print_specs.py`,
`db/models.py`, `static/admin.css`, two templates, and six test modules), derived with
`git diff --name-only f407c350..fd9cbdfa -- src tests`. **What was checked, and found
unaffected:** all **21** census modules (CARD-329's 20 plus
`tests/test_book_interior_type_floor.py`) and both modules every figure here is about
(`book_pdf_generator.py`, `book_interior_vector.py`) are in that diff **zero** times, so no
number on this card moves. What DID move is `app.py`'s line numbering — see the
cite-by-spelling note under *The finding that is not a figure* and in CARD-322 item 1's
table. This is a stronger statement than the sentence it replaces, which claimed safety by
asserting main had not moved. Instrument: `scratchpad/card338/probe_five_kinds.py` +
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
`BookPDFGenerator(book)` at four sites in `app.py`, one in `book_proof.py` and the bookless
module-level `_pdf_generator = BookPDFGenerator()` in `pdf_generator.py`, and the `app.py`
site **whose next statement is `return generator.export_interior(puzzles)`** is the interior
download path. <!-- CITED BY SPELLING, 2026-11-03 at this card's merge gate (cycle-3 M-204):
this sentence carried `app.py:841`, `:960`, `:5580`, `:5759` and CARD-332's merge moved the
last two to `:5673` and `:5852` — the `export_interior` one among them. CARD-322 item 1's
table is the enumeration of record. --> So CARD-322's re-cut §2 — *"the `src/` change is the five registry entries,
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
run in this worktree): **0 errors / 525 warnings before and after**, deterministic, with the
WARN **sets** matched by `comm` in both directions over 525 non-empty lines a side,
`^\s*\[WARN` not `^\[WARN`, and **both halves empty**.

**What the 525 are, corrected and measured at the merge gate (cycle-3 M-202).** This note
first said "the 525 is CARD-335's batched-grep timeout". The attribution to CARD-335 is
withdrawn — that card owns the opposite mechanism (a committed artefact making a *dead* ref
resolve) and its baseline is a different population at a different magnitude (108 → 107
dead-ref warnings). What the 525 are: **436** of them read *"existence could not be
determined — the search tool itself failed (git grep error)"*, from forge's own batched code
search; the remaining **89** are real warnings.

**And it IS a timeout — the gate measured it rather than asserting it either way, because
cycle 3 reported the opposite.** Cycle 3 observed that batches of 50/100 answer cleanly
while 150/200 return every name as `None`, and read that as proof it is *not* a timeout,
since a hand-run `git grep` with 200 patterns exits rc 0. Both halves of the observation
reproduce; the inference does not. `validators/utils._grep_batch` passes
`timeout=BATCH_TIMEOUT_BASE_S + BATCH_TIMEOUT_PER_NAME_S * len(names)` = **`10 + 0.1N`** to
`subprocess.run` and swallows the `TimeoutExpired` in a bare `except Exception: return
None, set()` — so a blown budget IS the all-`None` regime, and rc 0 from a hand-run grep is
expected, because `subprocess.run(timeout=)` kills the child the hand-run keeps.

Timed on this repository with **391** real check-ref-shaped names, the raw argv the
validator builds run with **no** timeout, beside `symbols_exist` run with the budget:

| N | raw `git grep -ow` | budget `10 + 0.1N` | `symbols_exist` wall | answers |
|---|---|---|---|---|
| 50 | 0.52 s | 15.0 s | 0.15 s | 50 True, **0 None** |
| 100 | 7.97 s | 20.0 s | 7.30 s | 100 True, **0 None** |
| 150 | **44.44 s** | 25.0 s | **25.01 s** | **150 None** |
| 200 | **141.24 s** | 30.0 s | **30.01 s** | **200 None** |

Every raw run exits **rc 0** with real matches (170 / 606 / 1997 / 5323 match lines), so the
tool is not failing — it is being killed. **`symbols_exist`'s wall time at the two failing
sizes equals its own budget to 0.01 s**, which is the timeout firing and nothing else, and
cycle 3's threshold sits exactly where the cost curve crosses the budget (under it at
N=100, 2.2× over it at N=150). `BATCH_SIZE` is **200**, so every real validator run on this
repository batches straight into the blown regime. The cost is super-linear in N because
`-ow` prints one line per occurrence.

**None of this weakens G-4**, and that is why it stays a Minor. G-4's claim is set
EQUALITY — *nothing was revived* — and a revived ref would change its own warning line and
make `comm -23` non-empty. The claim the blindness would degrade is the absolute one
("no dead refs"), which this card never makes. Raised as O-201 for whoever owns forge's
batching; a `BATCH_SIZE` at or below 100 would answer this repository cleanly today.
<!-- MEASURED 2026-11-03 at the merge gate, not inherited: the instrument is
     /private/tmp/.../scratchpad/m202/time2.py for the session, and the two constants and
     the bare `except Exception` are read from
     forge_1/forge/skills/architect-validate/scripts/validators/utils.py (read-only, G-6).
     The brief that ordered this fix predicted 8.6 s at N=100 and ~40 s at N=150; measured
     7.97 s and 44.44 s. Same conclusion, and the figures here are mine. --> The full suite was never run; every census call is file-scoped.

### Fix round 1 (cycle 1 scored 7.5, nothing a blocker) — three propagation defects

Cycle 1 broke nothing: every figure it re-fired reproduced to the digit, all six
guardrails held, and no figure in the diff was wrong. Cycle 1 graded **two `high`
(F-001, F-002) and one `medium` (F-003)** — this note first said "all three Importants",
which is one notch high on F-003 and was the single number in it that did not match its
source (cycle-2 M-105). All three are nonetheless the same **shape** — **the round
measured the right thing and then did not carry one correction into the places that
execute.**

* **F-001, CARD-322's item 1.** The blocker above was written into §2 and into item 0, not
  into item 1 — the one step that performs the `src/` change, which still claimed the walk
  already reaches the writers and routed the refutation back out as *"a finding about
  CARD-309"*. Round 1 made item 1 name the decision as CARD-322's own — move the
  generator's construction sites to `interior_generator`, or change the generator's
  default — and dropped the CARD-309 routing for the downstream-writer case, keeping it
  only for a cause this card did not measure.
  <!-- CORRECTED 2026-11-03 at the merge gate (cycle-3 M-201b). This bullet said, in the
       present tense, that item 1 "now names the decision … (move the SIX call sites …)".
       Item 1 carries NO count, which is the right fix — the restatement was the stale copy,
       and in the present tense it read as a description of the live text rather than as a
       record of a round. Put in the past tense and the count dropped, as item 1 drops it. -->
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

### Fix round 2 (cycle 2 scored 8.5, nothing a blocker) — the propagation set includes the fields

Cycle 2 unwound nothing: both census figures re-fired to the digit (`red=8 … conversion=8`
and `red=46 … conversion=46`), the unaccounted gate fires in four directions, 6/6 mutants
were killed, all three `validator` refs resolve, and the one Important was a metadata edit.
Cycle 2's one failing circuit was `system_contract_verdict` on a **fourth** instance of the
clause ADR-0039/R4 required retracted everywhere.

**The lesson, and it is this round's most transferable output.**

> **The propagation set for a retraction includes a card's METADATA FIELDS and the comments
> attached to them, not just its prose sections.**

Three passes read CARD-322's body for the refuted clause *"so no writer module is edited —
the src/ change is the five registry entries"* — cycle 1, fix round 1, and cycle 2 — and
**none of them read the `Touches:` field**, where a fourth copy sat. Prose sections are what
a reader scans; a metadata field is what a *program* reads, so it is the copy that can do
damage while looking like bookkeeping. The habit this round adds: after retracting a claim,
grep the card's **fields** for it before declaring the propagation complete.

**And the field was worse than unretracted — it was unparseable, which this round measured
and fixed.** `card_lint.parse_card_fields` strips no HTML comment and
`card_lint.extract_touches` splits on **commas**, so an inline `<!-- … -->` note sitting on
the `Touches:` line is read as part of the VALUE. Measured on CARD-322: **15 "globs" instead
of 8**, seven of them prose fragments, and the eighth was the declared ADR path concatenated
with the comment's opening — so `compute_excess` reported
`meta/architecture/decisions/adr/0042-…md` as **excess although the field declares it**, on
a card whose item 3 edits exactly that file. Moving the comment to its own line restores it:
**15 → 11 clean globs after the widening, `excess == []` for the full option-A file set.**
This is the same family as the card's own trap list — a census counts refs, not declaration
sites; here a parser counted commas, not paths.

* **F-101 (Important), both halves, closed at the field.** (a) The clause is struck through
  in place with an adjacent `WITHDRAWN` note pointing at §2's correction, per this card's
  carry-it-inline convention. (b) `Touches:` is **widened** by
  `src/nonogram/admin/app.py`, `book_proof.py` and `pdf_generator.py` rather than left
  narrow with a warning in item 1 — **chosen, not defaulted**: the field is read
  mechanically *at dispatch*, before item 1's decision is made, and forge's own
  `compute_excess` penalizes **under**-declaration only (an edited, undeclared file becomes
  `excess` → `grown`/`runaway`) while costing nothing for a declared file left untouched.
  Over-declaring is therefore the error that cannot red, so the conservative direction is to
  declare. The comment marks all three live only on option A, and tells a later round to
  narrow the field if option B is taken. The `CONFLICT EDGES` comment is re-derived and now
  records the **CARD-332** edge on `app.py` (CARD-332 declares it; wave 73, `in_progress`).
  Measured, that edge reaches **no** automatic consumer: `compute_poached` subtracts
  `conflict.hotspots` (which names `app.py`) from the sibling's set first, and only looks at
  siblings whose `Status` is `ready` AND whose `Wave` equals the card's — CARD-332 is
  `in_progress` and CARD-322's wave is `—`, so it is skipped twice over. The comment is the
  only record, which is why it is written as one.
* **M-101, the third instrument in the family.** `fidelity_to_the_end_state.py`'s docstring
  quoted AC-2 by the wording this card's own fix round 1 deleted, and its constant was still
  `ARTEFACT`. The question is kept in the form it was asked — that is what the experiment
  tested — under an **Asked / Answered** split that records the answer beside it, AC-2 is
  quoted as it now reads, and the constant is `DELITEM`, as `census_five_kinds.py` already
  renamed its own. Rename verified by `ast` over the file's `Name` nodes, not by text.
* **M-102, and the count was right only by coincidence.** The enumeration of
  "six `BookPDFGenerator(book)` call sites" **mislabels one member and omits another**:
  `pdf_generator.py:344` is `_pdf_generator = BookPDFGenerator()` — bookless, a
  module-level singleton evaluated at import — and the list missed
  **`book_pdf_generator.py:1912`** (`puzzle_page_plan`) entirely. Re-measured by
  `grep -rn 'BookPDFGenerator(' src/`: **seven** construction sites outside
  `interior_generator`, six `(book)` and one bookless. Item 1 now carries the sites as a
  table with what each builds, and §2's blockquote is corrected in place. Nothing in the
  conclusion moves — and one thing in the **costing** does: **only the `export_interior` site reaches a
  downstream interior write**, so option A is a larger edit than the refusal requires.
  `book_pdf_generator.py` was already declared, so the omitted site widens nothing.
* **M-103, upgraded on measurement: the leaf property is a LIVE TEST, not only prose.**
  Cycle 2 called this "not a defect, no cycle results". Measured, option A reds
  `tests/test_book_pdf.py:3656`
  (`TestAssemblyPoint_TheDirectionIsResolvedAndNotHidden::test_nothing_in_the_package_imports_the_assembly_point`,
  `importers == []`; that class measured **5 passed**), whose own docstring calls it the
  "load-bearing" one of CARD-309 AC-5's three facts. So option A owes CARD-309's AC-5 an
  argument, not a quiet edit. Item 1 names it. **Two further corrections to the finding
  itself:** the second card stating the property is **CARD-309:597** (`done`), **not
  CARD-337**, which states the rebinding and not the leaf — measured by
  `grep -rnE 'nothing in .?src/.? imports' meta/kanban/cards/` (two hits: CARD-338:43,
  CARD-309:597); and no import **cycle** results, so the cost is the guard and the claim.
* **M-104, proven session-independent.** Both instruments defaulted `CARD338_SCRATCH` to one
  session's `/private/tmp/claude-501/…/<session uuid>/` path while three cards tell a reader
  to run them. The default is now
  `Path(tempfile.gettempdir()) / f"card338-scratch-{ROOT.name}"` — `gettempdir()` honours
  `TMPDIR`, which macOS sets per-user, and the worktree's own name keeps two worktrees apart.
  Deterministic rather than `mkdtemp()` on purpose: the mutated trees are meant to be
  inspectable after a run, and each script removes its own. Proven by importing both modules:
  default resolves under `/var/folders/…/T/card338-scratch-PythonProject4-card-338`, asserted
  free of `claude-501` and of the session uuid, and `CARD338_SCRATCH` still overrides.
* **M-105.** The fix-round-1 record's "all three Importants" is corrected to two `high` and
  one `medium`, by id, above.

**One defect this round found in its OWN instrument, by running it — and the cheapest
finding of the card.** Mid-round, CARD-323's merge gate took
`meta/kanban/.full-suite.lock` (absent when this round opened, held from
`2026-11-03T16:54:46Z`). Run under a held lock, `prove_refusals.py` built nine mutated
trees, had every `pytest` call refused by the repository conftest, and printed
**"AC-1 NOT PROVED: 9 of 9 cases wrong"** — because for the eight refusal cases
`refused == must_refuse` held while `named` was empty (the lock message carries none of the
probe's assertion phrases), and the CONTROL refused when it must accept. **An environmental
refusal reported as a verdict about the instrument** — this card's own failure family, in
this card's own tooling, and the direction that lies: it manufactures nine findings out of
zero. Fixed: `prove_refusals.py` now carries `LOCK_REFUSAL` and, on seeing it, stops at the
**first** case, prints `COULD NOT MEASURE -- this is not a result about the probe`, echoes
the lock's own holder/why/worktree/age lines, and exits **3** — still non-zero, so the AC's
`validator` check correctly reads "not proved", but naming what it could not do, which is
AC-1's own standard applied to AC-1's own harness. **Proved against the real held lock, not
a simulation** (output above is CARD-323's gate). `fidelity_to_the_end_state.py` needed no
change: its `assert collected` already fails loudly with the subprocess output rather than
computing a number from nothing — confirmed by reading, and that is the asymmetry worth
keeping in mind, one instrument fails safe and its sibling did not.

**What this round could NOT re-verify, stated as a limit and not a pass.** Because the lock
was taken mid-round, `prove_refusals.py`'s **nine substantive cases were not re-run** after
the `CARD338_SCRATCH` change. What IS measured: both instruments import cleanly, the new
default resolves session-independently and is still overridable, `fresh_copy` built the
mutated tree under the new path and the `where_from` plugin confirmed the generator was
imported **from that copy** (`CARD338-IMPORTED-FROM /var/folders/…/T/card338-scratch-PythonProject4-card-338/trees/control-the-unmutated-tree/src/…`),
so the path change is exercised end to end up to the point pytest was refused. The nine
verdicts themselves are owed one re-run once the lock clears; nothing about them changed in
this round, and the exit code is non-zero either way.

**Two mechanisms recorded rather than fixed, both costumes of the same trap.**

1. **A `validator` check ref is live against DELETION and blind to a RENAME.** A path-shaped
   ref resolves through `git grep -lw <ref>`, which matches the ref inside the file's **own
   docstring** — so the file proves its own existence. Delete the file and the ref dies
   loudly; rename the symbol the ref is about and nothing notices. Recorded per cycle 2's
   instruction; the resolver is forge's and not this card's to change. Another instance of
   *a census counts refs, not declaration sites.*
2. **`git grep -E` honours neither `\b` nor `\s` — and cycle 2's own reviewer tripped on it
   while auditing this card, and said so.** `git grep -lnE '^\s*(def|class) …'` returned no
   hits; re-run with `[[:space:]]` it found a live `def`. The conclusion did not move, but the
   first answer was a **false negative produced by the tool**, on the exact quirk one of this
   card's instruments warns about. The warning is correct and insufficiently loud: a tool
   quirk that returns *fewer* rows is the dangerous direction, because an empty result reads
   as a clean bill of health. Every grep in this round used `[[:space:]]` or `ast`.

**Scope held.** `src/` **0 files** and `tests/` **0 files** over the whole branch and over
this round's delta (G-1, G-2); the round edited two card bodies and two instruments. The
full suite was NOT run — a sibling's merge gate owned it — and the only pytest call that
RAN was one file-scoped class (`TestAssemblyPoint_TheDirectionIsResolvedAndNotHidden`,
5 passed), named because M-103's upgrade depends on it; it ran in the window before
CARD-323's gate took the lock, and every call after that was refused by the conftest, which
is how the instrument defect above was found. `__pycache__` swept, `PYTHONDONTWRITEBYTECODE=1`,
every edit applied by exact text with its occurrence asserted `== 1` and SHA-256 recorded
either side.

**For the architect, out of this card's scope (recorded, not actioned).** Beyond cycle 2's
O-101 and O-102: the `Touches:` inline-comment collision above is **not** CARD-322's alone.
Censused over all **337** cards by running `extract_touches` on each: **20** cards have a
`<!--` inside the parsed `Touches:` value, of which **2 are not `done`/`skipped`** —
CARD-322 (fixed here) and **CARD-273** (`ready`, untouched: out of scope). The other 18 are
closed cards whose fields are now history. A first guess of "110 cards" came from a looser
heuristic in this round's own census and is **withdrawn**: it counted multi-word globs and
other fields' comments. The durable fix is in the parser or a card-lint rule, not in 20 card
bodies.

**And the mechanism is not specific to `Touches:`** — no field is stripped, so this
generalises to any field carrying an inline comment. Censused the same way: **17** cards
have a `<!--` inside the parsed **`Wave:`** value, and `Wave` is compared by **equality**
(`fields.get("Wave") != own_wave` in `compute_poached`), which is more brittle than
`Touches`' comma split — a contaminated wave can equal no other card's. It is **inert
today**, and that is measured rather than assumed: **0** of the 17 have `Status: ready`, and
`ready` is the only status `compute_poached` considers. CARD-338's own `Wave` is one of the
17. The general shape, for whoever fixes it: the parser hands a field's comment to every
consumer as part of the value, and each consumer then fails in its own idiom — `Touches`
silently drops a declared path, `Wave` silently stops matching.

### Fix round 3 (cycle 3 scored 9.0, CERTIFIED — zero Critical, zero Important, `system_contract_verdict: pass`) — the merge gate, and one finding half overruled on measurement

Cycle 3's four Minors are closed here. None of them moved a figure; two of them moved a
*claim about an instrument*, which is this card's subject, so both were re-measured rather
than edited.

* **M-201, three stale restatements of a refuted count.** CARD-322 §2's blockquote said
  *"those six call sites"* four lines after the same blockquote enumerated **seven** — now
  "those **seven** construction sites", with the "six `(book)` spellings" defence closed off
  in place (`interior_generator(book=None, pages=None)` takes no argument, so the bookless
  site converts too). §2's **heading** asserted the refuted clause unmarked while the
  `Touches:` copy was struck through — now struck, with a pointer to the correction
  blockquote below it. And this card's own fix-round-1 record described item 1, in the
  present tense, as naming "the six call sites"; item 1 carries **no** count, which is the
  right fix, so the record is in the past tense and the count is dropped. Item 1's table is
  the enumeration of record and was right throughout.
* **M-202, and the gate measured it rather than taking either side's word.** Half the
  finding stands: the **436 / 89** split is new, correct and kept, and the attribution to
  "CARD-335's batched-grep timeout" is withdrawn. Half does not: cycle 3's *"it is not a
  timeout"* is **refuted by measurement**, and the refutation is the finding's own threshold
  read correctly — `10 + 0.1N` against a super-linear cost curve, with `symbols_exist`'s
  wall time equal to its budget to 0.01 s at both failing sizes. The table is in the
  Guardrails note above. The brief that ordered this fix offered the budget explanation and
  invited its refutation by measurement; it was measured, it held, and two of the brief's
  own figures (8.6 s, ~40 s) are replaced by this gate's (7.97 s, 44.44 s).
* **M-203, the refusal discriminator is now per case.** `prove_refusals.py` scored a case
  `ok` on `bool(named)` — any member of one flat eight-phrase list, found anywhere on the
  assertion surface. That is set membership, not a discriminator: all five drop cases were
  satisfied by the same `'found no'`, and a case refusing for another reason still scored
  OK. `CASES` now carries a fourth element, each case's **own** expected phrase, and the
  five drop phrases carry the kind name (`found no declaration to lift for ['TOC']`), which
  makes them **mutually non-satisfiable** — asserted, not just claimed. One thing the fix
  needed that the finding did not name: pytest wraps a traceback at 80 columns and gutters
  each continuation with `E`, so a 43-character phrase is routinely split mid-phrase and a
  literal `in surface` test would have produced a **false negative** — the direction that
  lies. `flattened()` strips the gutter and collapses whitespace, still scoped to the
  assertion surface that cycle 1's F-005 bought.
* **And the re-run this card recorded as owed is now done.** Fix round 2 could not re-run
  `prove_refusals.py`'s nine substantive cases, because CARD-323's gate held the full-suite
  lock. This round holds it, so the lock refusal does not fire and the cases execute:
  **`AC-1 PROVED: 9 cases, 8 refusals each naming ITS OWN mechanism and 1 control
  accepted`**, exit 0, every case verified to have imported the generator from its own
  mutated copy. The eight refusals exit 3, the control exits 0.
* **M-204, two line citations that rotted mid-review — and the rule applied rather than the
  numbers patched.** CARD-332 merged while cycle 3 was reviewing and moved `app.py` by +97
  lines: `:5580` became `:5673` and `:5759` became `:5852`, re-derived here with
  `grep -rn 'BookPDFGenerator(' src/` on main's tip. `:5580` was the row item 1 marks *"the
  one site that writes an interior"*, so the **load-bearing** citation was the one that
  rotted, and silently. The sites are therefore cited by **spelling** — "the `app.py` build
  whose next statement is `return generator.export_interior(puzzles)`" — in CARD-322 item
  1's table, in §2's blockquote and in this card's *finding that is not a figure*; the line
  numbers survive only as a dated convenience line that is expected to rot. A name is
  stable across edits and self-verifying; a line number rots without a sound. The one place
  a rotted number is **kept** is the quotation of the withdrawn sentence, because a
  quotation of a retracted claim is history, and that is said where it sits.
* **The worktree note's premise was false and is replaced by a stronger one.** It said main
  "has since moved on kanban and repo-hygiene commits that touch no `src/` or `tests/`
  file". Measured, `git diff --name-only f407c350..fd9cbdfa -- src tests` is **14** files
  over eight commits from CARD-323 *and* CARD-332 (the brief said 13; 14 is what the diff
  says, the extra being that six test modules moved, not four). **What makes the figures
  safe is the check, not the claim:** all **21** census modules and both modules every
  figure here is about appear in that diff **zero** times.

**The gate's own finding, and it is a field, not a figure.** Checked before merging, as this
card's own lesson demands. `Wave:` carried its stamp comment **inside** the parsed value —
this card's census of 17 contaminated `Wave:` fields had already named it as one of the 17,
and it was the one live case left after main's `fd9cbdfa` sweep. Moved to its own line.
Then the same check on the three cards this branch edits found something the census had
*not* reached: main's `fd9cbdfa` repaired `Depends on` **board-wide** after a comment there
closed a real cycle (CARD-336's comment named CARD-337, which really depends on CARD-336),
and this card's fix round 1 wrote **new** inline comments into CARD-322's and CARD-337's
`Depends on` — authored after that repair, and landing into a field main had just cleaned.
`establish_dependencies_resolved` token-scans that value with `CARD-\d+`, so a card id in a
comment is an edge.

**Measured before repairing, in both readings, over all 340 cards:** the comment-stripped
reading gives 340 ordered / no cycle and the token scan gives 337 / cycle, **identically on
main's tip and on the merged tree** — this card adds **no** phantom edge, because its
comments spell the chain as bare `338 -> 336 -> 337 -> 322` and every `CARD-NNN` token in
them is already a real edge. So it was inert, by luck and not by design, exactly as this
card said of the `Wave:` family. Both lines are normalised to main's convention anyway.
The residual cycle (337 of 340) is pre-existing on main, confined to `done` cards
(CARD-218, CARD-220, the latter naming **itself**), and is outside this card's scope —
CARD-341 owns the lint. So are CARD-322's `Priority:`, `Estimate:` and `Complexity:`, which
carry comments on main and are untouched here.

**Scope held at the gate.** `src/` **0 files** and `tests/` **0 files** over the whole
branch, including this round. The node-id delta over the merged tree is **0 gained / 0
lost** — **10235** node ids collected on main's tip `fd9cbdfa` and **10235** on the merged
tree, `comm` empty in both directions with both sides asserted non-empty first. That is the
strong form of G-1 and G-2, and it is what a card touching neither directory must show:
anything else would mean the branch carried something its guardrails say it does not.
