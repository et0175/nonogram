# CARD-363: The retrospective's two inputs are unguarded — the cycle marker is absent on 128 of the 231 scored cards, and nothing requires a wave's estimate to be in the unit the ratio needs

**Status:** in_progress
**Priority:** P1
**Category:** enabler
**Estimate:** 2c (0.5d)
**Complexity:** standard
**Skill:** python-pro
**Revision pending:** false
**TDD:** false
**Branch:** `card/363-the-review-record-guards`
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-363
**Source:** Measured at the station 2026-11-04 after five review artefacts in two waves had to be reconstructed from agents' hand-back messages. The measurement found the gap is not five cards but systemic, and that the orchestrator's own diagnosis of it was half wrong — see "What the measurement changed".
**Idea:** —
**Wave:** 76
**Created wave:** 75
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/test_kanban_review_record.py
**Review score:** —
**Started:** 2026-11-04T14:14Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## The measurement

> **⚠ EVERY FIGURE IN THE TABLE BELOW IS SUPERSEDED — and the `279` denominator never existed.** The correction tables that follow are the current reading: **291** done, **231** carrying a numeric score, **128** with no marker, **50** disagreeing, **3** naming no cycle. Confirmed a third time by this card's cycle-1 review, which re-derived all five with its own parser against both the branch tree and main's tip and got identical results. The original table is kept as the record of what the card was cut on (ADR-0039/R4 retracts the figure, not the history) — do not read a number off it.

As originally cut, over all **279** `done` cards carrying a `Review score` — **superseded**:

| | count |
|---|---|
| marker count disagrees with the cycle the card's own score names | **136** |
| **zero** `[Review N/M] Score:` markers at all | **152** |
| no review YAML on disk | **81** |
| the score text states its cycle (`cycle N of M`) | **210 of 281** — *corrected, see below* |

**Re-derive all five.** They are a dated reading and the sets matter more than the counts — and
one of them was already wrong when this card was cut.

> **[SECOND CORRECTION, 2026-11-04, by this card's own implementation round — and FOUR of the
> five figures below do not reproduce. Read this first; it supersedes the correction after it.]**
>
> | the card's figure | measured by the round | reproduces? |
> |---|---|---|
> | done cards with a score — **281** | **231** | no |
> | marker disagrees with the named cycle — **136** | **50** | no |
> | zero markers — **152** | **128** | no |
> | no review YAML on disk — **81** | **42** | no |
> | score names no cycle — **71** | **3** | no |
>
> **The denominator was the first defect.** 281 was `done` minus the cards whose `Review score`
> is exactly `—`, so it counted **~50–60 cards whose score field holds a PROSE SENTINEL** —
> *"merged without a review cycle, at the owner's call"*, *"(review skipped: cost card…)"*.
> Those cards were never reviewed, so **no cycle count exists for them to disagree with.** The
> honest population is "done **and** a numeric score", and the round asserts its split sums to
> the `done` total so the partition is not a judgement call.
>
> **And my first correction was wrong in the SAME DIRECTION BY THE SAME MECHANISM.** It replaced
> "279 of 279" with "71 cards state no cycle"; the real figure is **3** — CARD-029, CARD-035,
> CARD-066, each a bare score with no cycle text, named rather than counted. The 71 came from the
> inflated denominator **plus** reading only the `cycle N of M` spelling. Measured frequencies
> over the real population: **`cycle N/M` 169**, `cycle N of M` **19**, plus bare `cycle N`,
> `cN/M` and `N cycles`. **I corrected the arithmetic and kept the instrument that caused it.**
>
> **One figure of this card is derivation-dependent and should not be treated as settled.** Three
> measurements of "scored done cards" now exist — 281, 224 and 231 — each from a self-consistent
> partition that sums to the `done` total, differing only in **what counts as a numeric score**.
> **The module's own asserted bounds are the authority, not this card.**
>
> **What survives, and more strongly than the card claimed:** the score field covers **228 of
> 231** where the marker covers **103**. The direction of the fix is unchanged and the margin is
> wider than either of my figures implied.

> **[PREMISE CORRECTED AT THE WAVE-76 STATION, 2026-11-04, and the defect was the orchestrator's.]**
>
> **This card was cut claiming the score text states its cycle on "279 of 279" scored cards.
> Measured: 210 of 281.** Seventy-one closed cards state no cycle in their score field at all.
>
> **I never measured that figure. I asserted it.** The morning script that produced the other four
> computed the per-card cycle, then filtered `if named is not None` before counting the
> disagreements — so cards with no cycle in their score were silently excluded from every total,
> and their count was never printed. I wrote "279 of 279" because it made the argument tidy.
> **In a card whose subject is records that do not say what they claim.**
>
> **What survives, and it is still the card's point:** the score text covers **210** where the
> marker covers **129** (281 − 152). So the score field remains much the better source and the
> direction of the fix is unchanged. **What does not survive is "the numerator was available for
> the board's whole history"** — for **71** cards it is available in *neither* place, and no
> instrument can recover a cycle count nobody recorded.
>
> **That changes AC-1's shape and the change is load-bearing.** A guard asserting "marker count ==
> the cycle the score names" can only speak about cards whose score names one. **So the 71 are a
> third population**, alongside the 152 with no marker — and they need their own declared bound,
> not silent exclusion. Silently excluding them is precisely how this figure went wrong.

## What the measurement changed, including about my own diagnosis

The retrospective derives `cycles_used` by counting exactly `[Review N/max] Score:`. I had
diagnosed the absence of that marker as the reason wave 73 could export no calibration signal,
and wrote markers onto wave 74's three cards to fix it.

**The marker was never where the information lived.** The `Review score` field already states
the cycle — *"8.4 (cycle 2 of 3 — CERTIFIED)"* — on **228 of the 231** scored cards, while the
marker is present on **103**. (This sentence read *"279 of 279"* against *"127"* when the card was cut; both figures and their denominator are **retracted** — ADR-0039/R4.) So the numerator was available for the whole of the board's
history, in a field the extractor does not read.

**And the thing that actually blocked wave 73 was the DENOMINATOR, not the numerator.** Measured
per wave:

| wave | estimates in cycles? | ratio computable |
|---|---|---|
| 71 | no — `0.5d`, `0.75d` | **0 of 2** |
| 72 | no — `0.25d`, `2d` | **0 of 2** |
| 73 | no — `0.25d`, `0.5d`, `0.5d` | **0 of 3** |
| 74 | **yes** — `1c`, `1c`, `2c` | **3 of 3** |

Waves 71–73 had the cycle count all along and no **cycle estimate** to divide it by. So wave 73's
retrospective reached the right conclusion ("no signal exportable") for a reason that was only
half the cause, and wave 74's signal exists because the estimates were **restated in review
cycles at the wave open** — a decision made before any work happened — and not because markers
were written.

**That is what this card protects: the unit of the estimate, which is the scarce input.**

## What to implement

A new module, `tests/test_kanban_review_record.py`, holding two guards. Both read **tracked**
files only — card bodies — so neither depends on the untracked review YAMLs and neither reds on
a fresh clone.

1. **The marker agrees with the score.** For each card whose `Review score` names a cycle,
   assert the `[Review N/M] Score:` marker count equals that cycle number. **Scope it forward**
   from a stated card id or date and **declare the historical population as a measured bound**
   (ADR-0039/R3) — do not demand **128** cards of fabricated history (the figure was `152` when this card was cut; retracted), and do not silently exclude
   them either. Name the count in the bound so it cannot grow unremarked.
2. **A card that ran in a wave carries a cycle estimate.** For each card with a `Wave:` that is a
   number, assert its `Estimate` states an `Nc` term. Same forward scoping and the same declared
   bound for the pre-forge_1's ADR-0055 (upstream, not this board's — see CARD-367) population.

**Derive both populations from the card files** (ADR-0039/R2), never from a list. A card the walk
cannot classify — a `Review score` whose text states no cycle, say — is a **FAILURE**, not a
skip: that is the shape this whole family keeps producing.

## Acceptance criteria

- **AC-1** *Given* the card tree, *then* a card whose score names cycle N and carries ≠ N markers
  **reds by name**, demonstrated by planting one — and the unplanted tree is green.
  (test: named by the implementation; state it)
- **AC-2** *Given* a card stamped with a numeric `Wave` whose `Estimate` carries no `Nc` term,
  *then* it **reds by name**, demonstrated by planting one.
  (test: named by the implementation; state it)
- **AC-3** *Given* the historical populations, *then* **each of the THREE** is declared with its
  measured count and the declaration is asserted, so none can grow silently: the cards with **no
  marker**, the cards whose **marker disagrees** with the cycle their score names, and the cards
  whose **score names no cycle at all**. State all three as measured, not as the figures in this
  card — **one of which was wrong when the card was written.**
  **The third population is the one to get right**: a guard over "marker == the cycle the score
  names" is *undefined* for a card whose score names none, and excluding it silently is exactly
  the move that produced this card's own bad figure.
  (test: named by the implementation; state it)
- **AC-4** *Given* a card the walk cannot classify, *then* it is a **FAILURE and not a skip**
  (ADR-0039/R2), demonstrated.
  (test: named by the implementation; state it)
- **AC-5** *Given* both guards, *then* they read **only tracked files** under
  `meta/kanban/cards/`, verified both dynamically (every path opened is in `git ls-files`) and
  statically (no code string in the module names the review directory). State how you verified it.
  **The reason this AC originally gave was FALSE and is retracted:** it said `meta/review/*.yml`
  is "untracked by convention and absent in a fresh clone". Measured — **396 of them are
  tracked.** They match `.gitignore:102` *and* are in the index anyway, which is the same
  ignored-yet-tracked set `tests/test_check_ref_resolution.py` counts and the mechanism behind
  this board's "review YAMLs revive dead check refs" finding. **The constraint is still worth
  asserting**; it is simply asserted directly rather than inherited from a false premise.
  (test: named by the implementation; state it)

## Guardrails

- **G-1** — No `src/` change; this is board hygiene expressed as a test.
- **G-2** — **Do not fabricate history.** Writing markers onto the **128** marker-less scored cards would invent
  intermediate scores nobody recorded. Declare the bound instead.
- **G-3** — **`/Users/omelnikova/MyProjects/forge_1` is READ-ONLY.** The extractor that reads the
  marker lives there. If the real fix is "read the score field instead", that is a finding handed
  upstream with its measurement — not an edit.
- **G-4** — Do not loosen either guard to accommodate the historical population. AC-3 is the
  mechanism for that, and a bound without an asserted count is not a bound.
- **G-5** — No new runtime dependency (ADR-0006/R1); stdlib only.
- **G-6** — Take no timing measurements and report no durations.
- **G-7** — A full suite needs the board's lock (structured, worktree identity, **no pid**). Never
  set `NONOGRAM_IGNORE_FULL_SUITE_LOCK`, never redirect `NONOGRAM_FULL_SUITE_LOCK` — the guard
  fires in `pytest_configure` for **any** selection.

## System contract

- ADR-0039/R1 — a claim needs a control that can fail (check: review-lens)
- ADR-0039/R2 — a guard's set is derived from an authority the runtime can enumerate; where none
  exists it defaults to **deny** (check: review-lens)
- ADR-0039/R3 — a declaration carries a reason and a measured residue (check: review-lens)
- forge_1's ADR-0055 (upstream, not this board's — see CARD-367) — review cycles are the estimate unit (check: review-lens)

## Worktree notes

[Fix round, commit `db4febab`] **All seven cycle-1 findings closed**, one file
(`tests/test_kanban_review_record.py`), INV-023 clean, no `src/` change, stdlib only, `forge_1`
untouched. Module selection **61 passed / 0 skipped / 0 failed**. Full suite, unarmed, **lock held
for the duration**: **10329 passed / 27 skipped / 1 xfailed / 0 failed / 0 errors** — 27 being
26 bare-`DATABASE_URL` + 1 `setrlimit`, the unarmed reading exactly.

[Fix round] **CARD-370's cause is now MEASURED, not presumed.** Cycle 1's `10292 passed + 37 failed
= 10329` equals this run's clean pass count, so all 37 were lock refusals and nothing else. The
round waited ~28 minutes for CARD-348's **merge gate** (not its reviewer) to release, wrote the lock
itself before its own suite with all five fields and no pid, and removed it via an `EXIT` trap.
Neither override env var was touched.

[Fix round] **The round verified the reviewer's proposed F-001 shape instead of applying it, and one
part of it was wrong.** Making the partition sum `== len(scored_cards(tree))` with no absolute
**defangs it into a tautology**: `by_class` buckets every scored card by construction and an unknown
class raises `KeyError` rather than being dropped, so the sum can never differ — the `== 231` was its
only teeth, which is why the review measured it red in six of eleven plants. Replaced with the
**historical total `128 + 50 + 3 == 181`**, all three closure-invariant (a correctly closed card
lands in `AGREES`), biting on exactly what the absolute bit on. **House precedent supports this:**
`tests/test_book_pdf.py`'s card census already uses floors (`>= 300`, `>= 200`, `>= 10`) for this
reason, citing CARD-261's drift from a restated count — so the module is now consistent with the
tree rather than an exception to it.

[Fix round] Each loosened cell was shown to still kill its own degradation — **7 plants, 7 killed**:
done floor (291→290), scored floor (231→230), historical total (181→182), the names-a-cycle
identity, blind floor (209→206), first-ordinal floor (11→10), and a **compensating** plant holding
the total at 181 so only the names-a-cycle identity can catch it. The three historical bounds
(128 / 50 / 3) stayed equalities. F-001's own plant reproduced at **3 failed / 58 passed** before and
**61 passed** after, both for the reviewer's stamp and for the realistic house-style cycle-2 stamp.

[Fix round] **Five figures refuted, three of them mine or the reviewer's.**
**(a)** "Four asserted equalities grow by one" is **six** — and the review's own evidence paragraph
lists six while its headline said four; the orchestrator propagated "four" into the fix brief.
**(b)** The true count is **eight**: two further cells (`first_wrong == 11` and the
in-scope-ambiguity assertion) fire only if the closing score is written in **progression** style
(`7.75 (c1) → 8.5 (c2/3)`) rather than the single-ordinal house style, which plant H happened to
use, so neither showed. `first_wrong` is now a floor; the in-scope assertion was left
**deliberately strict**, with the cause and remedy in its message, because widening it would be the
loosening G-4 forbids. **⚠ CONSEQUENCE FOR THE MERGE GATE: write this card's closing score
single-ordinal.**
**(c)** The review's `spelling_census` "`cN` 5" is **4** cards (CARD-228, 239, 261, 264); its
companion "all 14 non-`cycle N` matches" reproduces exactly. Nothing in the module stated a `cN`
count, so nothing needed fixing.
**(d)** The module's **own** unflagged slip, which the reviewer missed: its docstring called the
291−231 gap "50 prose sentinels". The gap is **60** = 50 prose + 10 bare em-dash. The assertion was
already `== 60`; only the prose was wrong.
**(e)** **A defect in the round's own fix, caught by its own control:** the F-007 re-entry check was
first placed *after* `assert marker_disagreements(tree) == []`, so a planted re-entry (markers
1,2,1,2 — true count 4, `max` reads 2) redded guard 1 first **with no message at all** and a correct
card was accused with no explanation. Reordered before the guard and re-proven.

[Fix round] F-006 was **handled rather than narrowed**: the audit now wraps `Path.read_text` and
`open` and asserts the opened set is **exactly** the returned set. Proven to have teeth the old half
lacked — a planted stray `read_text` of `pyproject.toml` inside `read_card_tree` **passes** the old
returned-paths check (the file is tracked) and **reds** the new audit.

[Fix round] F-002 corrected the prose and changed no guard, re-deriving every figure (50 / 49 / 48 /
50→2 with CARD-192 and CARD-262 surviving / 0 regressions / era CARD-113..CARD-192, nothing after)
and attributing the measurement to CARD-369. F-004's reason restated as the module's own, confirmed
against `forge/skills/retrospective/SKILL.md`. F-005's base corrected — **212** of 231 are blind,
209 is of the **228** that name a cycle, `209 + 19 = 228`. F-007 disclosed in `cycle_named`'s
docstring with "not live" **measured** by a new assertion over in-scope cards' ordinals rather than
recalled in a comment.

[Fix round] Everything else reproduced exactly, re-derived on **both** the branch tree and main's
current tip (which had moved — CARD-348's certification landed) and identical on both.

[Review 1/3] Score: 7.75 — BACK TO THE ROUND (threshold 8.0). 1 Critical (F-001), 3 Important (F-002/003/004), 3 Minor. Artefact: `meta/review/CARD-363-cycle1.yml`. Merge-base `c021a10f`.

**This section did not exist and the marker was written by the orchestrator, not by the review's sync point.** That is the defect this very card asserts the absence of, and it occurred on this card — the strongest available evidence for the card's own premise. Counted as ONE cycle: this cycle did not reach its threshold, so the double-Score-line shape measured in F-002 does not apply.

[Review 1/3] **The title's figures were refuted and are retracted here** (ADR-0039/R4): it said `152 of 279 closed cards`; measured, it is **128 of the 231 scored cards**, against **291** done. The `279` denominator never existed — see CARD-369 and the fourth derivation it records.

[Review 1/3] The refutation HELD on all five figures, re-derived by the reviewer's own parser against both the branch tree and main's tip, **identical on both**: 291 done / 231 scored / 60 sentinel / 128 no-marker / 50 disagreeing / **3** naming no cycle (CARD-029, 035, 066). The module's classifier was ruled **correct and strictly better than both alternatives**: 231 numeric + 50 prose + 10 bare = 291, admitting every score and no sentinel.

[Review 1/3] Full suite, unarmed: 10292 passed / **37 failed** / 27 skipped (26 bare-`DATABASE_URL` + 1 `setrlimit` — the unarmed reading). **All 37 are lock contention**: CARD-348's reviewer took the full-suite lock mid-run, the refusal text appears 71 times, and all 37 sit in the four subprocess-spawning modules. The module under review contributed no failure. Not re-run — the lock was still held and was neither overridden nor redirected. Carded as **CARD-370**.

[Review 1/3] Three cards cut: **CARD-368** (nothing guards the three-copy estimate agreement — and `board.md` claimed THIS card did; that claim is retracted), **CARD-369** (the upstream cycle counter double-counts a threshold-reached cycle: 50 apparent disagreements collapse to **2** with zero regressions, era-bounded CARD-113..CARD-192), **CARD-370** (the lock contention above).

[Review 1/3] What the merge gate still owes, per the review: a full suite re-run **after** the closure stamp (the run F-001 reds) and after CARD-348 releases the lock; the AC→test mapping stated on the card, which the branch cannot carry under INV-023.
