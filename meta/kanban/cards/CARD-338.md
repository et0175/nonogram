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
3. **Separate the instrument artefact from the measurement.** The `KeyError` reds from
   `delitem` sites without `raising=False` are the probe's own shadow, not the
   conversion's. Report the census **with them excluded and with them included**, and name
   the sites, so a downstream card prices the conversion and not the probe.
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
  `check: {kind: test}`
- **AC-2** — Given the extended probe over CARD-329's 20 modules, when the census runs,
  then the per-module failed+error counts are reported for all five kinds lifted, **split
  into conversion reds and probe-artefact reds**, with the `delitem` sites named.
  `check: {kind: test}`
- **AC-3** — Given the census, when the reds are grouped by message, then each group names
  a mechanism and an owning card, and **no group is left as "other"** — an unclassified
  group is a finding to raise, not a bucket to leave.
  `check: {kind: test}`
- **AC-4** — Given the third population (modules reaching the medium decision itself), when
  it is derived, then its membership is **derived rather than listed**, and the derivation
  reds when a new such module is added.
  `check: {kind: test}`
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
