# CARD-363: The retrospective's two inputs are unguarded — the cycle marker is absent on 128 of the 231 scored cards, and nothing requires a wave's estimate to be in the unit the ratio needs

**Status:** done
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
**Wave:** 77 <!-- RE-STAMPED 2026-11-04. Was 76. Wave 76 was closed on the owner's instruction on CARD-348 alone while this card was mid-review-cycle-3 (the last max_cycles allows), so the wave was closed AROUND it rather than on it and its wave-76 attribution is withdrawn deliberately. Consequence recorded honestly: the cycle datum this card would have contributed -- a 2c estimate certifying on cycle 3, which would have been this board's first ratio that is neither 1.000 nor 0.500 -- is NOT in wave 76's retrospective row, and will land in wave 77's. Review cycle 3 was NOT cancelled; it continued running across the wave boundary. -->
**Created wave:** 75
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/test_kanban_review_record.py
**Review score:** 7.75 (cycle 3/3 — NOT CERTIFIED, ⚠ max cycles reached) — merged on the owner's instruction after a FOURTH pass with a changed remit, which is not a review cycle: cycles_used stays 3
**Started:** 2026-11-04T14:14Z
**Closed:** 2026-11-04T20:19Z
**Actual:** 3c — ratio 3/2 = **1.500**, NOT certified. **This is the board's first cycle ratio that is neither 1.000 nor 0.500**, which is exactly what this card's own `Wave` re-stamp note predicted it would contribute, and it therefore carries information about the SHAPE of the estimate error rather than only its presence: the card was priced at 2 review cycles and consumed 3 before escalating. The fourth pass is deliberately NOT counted — it ran past `max_cycles` on the owner's authorisation with a changed remit and wrote no `[Review N/M] Score:` marker, so `cycles_used` as the extractor reads it stays **3** and the marker count agrees with the cycle the score names. Counting it would have been this module's own defect committed on this module's own card. Sized by derived datum, **wall-clock excluded** per the owner's standing ruling that the clock measures the queue rather than the work: three review cycles and a fourth pass queued behind other cards' full-suite locks, and two 25-minute suites of this card's own are queue time by the same rule. Datum: 1 file, +2311/−0 (`tests/test_kanban_review_record.py`, new); **+68 test arms, 0 → 68**; 141 assertions across 30 test functions, every one classified against the five correct board operations.
**Merge commit:** `63f246a2`
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

[Merge gate, merged `63f246a2`] **CLOSED, NOT CERTIFIED — and the gate's own finding is that
the three review cycles could not have caught what the fourth pass found.** INV-023 freezes
`meta/kanban` on a card branch at the merge base, so this module's tree reader read cards that
predated every board write since the cut. Measured at the same commit, same module: **67 passed on
the branch, 2 failed / 65 passed against main's cards.** Three green cycles coexisted with a module
that would have turned main red on merge. Resolved at this gate by merging main into the branch
FIRST (`98d5e488`), after which the branch reads the real board and is green — the procedure every
future card touching a board census should inherit.

**What the fourth pass changed, under one rule applied to all 141 assertions** — can a correct board
operation move this value? Five cells moved off equality, each because the board writes it as a
correct operation: the `Wave`-comment census (**16 against `== 15`** on main, because wave 76's close
re-stamped this card's own `Wave` 76 → 77), the `Estimate`-comment census, an in-scope ban that
forbade the **dispatch convention by construction** while conceding in its own comment that it had no
members, `len(without) == 244` → a ceiling (CARD-310 is `ready` at `Wave: 67` with `0.5d`, so
dispatching it correctly re-prices it to 243), and `sentinel == 60` → a floor (an owner's-call merge
is a correct operation with 60 precedents). Every equality that remains carries the reason it cannot
move, written beside it.

**Proved by simulation rather than argument:** five correct board operations in eight variants —
closure, wave open on a `ready` card and on a pre-74 one, re-stamp, re-estimate in and out of scope,
re-cut with a new tracked card — each on a **git-initialised** copy of main's cards, each leaving the
module green, cards restored byte-clean. The same eight against the previous module red, the pre-74
wave open with a **third** failure nobody had listed, which is how `len(without)` became a ceiling.

**Four findings closed, each re-derived rather than carried:** F-202's 39/10 split restated as
**39 / 9 / 1** — 39 duplicate only the maximum, 9 the maximum and a value below, and exactly one
(CARD-192, ordinals `1,1,2`) below without it, so **48 of 49** and ONE counterexample rather than ten;
F-203's static half, measured blind to the module's own segment-built path idiom (a planted
`REPO_ROOT / "meta" / "review"` left all 67 green) and now segment-aware; F-204's capability loss,
disclosed per ADR-0039/R3 and measured on in-scope CARD-348 (the CARD-020 misread shape with markers
forged to agree is **fully green**, the matched control reds 4); F-205's missing control for guard 1's
third refusal arm, which is **live** — a bare `9.0` on in-scope CARD-348 reds five tests.

**Two of the orchestrator's framings retracted in place rather than edited away:** the CARD-020
citation (the retired spelling ban was **in-scope-only** and CARD-020 is **wave 13**, and the ban's
live in-scope set measures **EMPTY**, which is the stronger ADR-0039/R1 ground for removing it), and
the `cN` census, which is 4, 5 or 6 depending on the regex and now says which.

**MERGE GATE on the merged tree:** **10348 passed / 0 failed / 27 skipped / 1 xfailed**, skips the
baseline exactly and attributed off `-rEfs` — 26 bare-`DATABASE_URL` + 1 `setrlimit`, unarmed because
no local Postgres answers, so arming would have ERRORED the 26 rather than passing them. Reconciles
three ways: 10348 + 27 + 1 = **10376** = the branch's collection; 10376 − 10308 (main's) = **68**; and
68 is this module's own collection. Main's tree after the merge is byte-identical to the gated tree,
so this run is wave 77's smoke test by identity. Lock written by the gate (holder / why / absolute
worktree / commit / at, **no pid**), released by an `EXIT` trap and verified gone.

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

[Review 2/3] Score: 7.5 — **BACK TO THE ROUND** (threshold 8.0). 1 Critical gating (F-101),
1 Important (F-102), 3 Minor (F-103/104/105). Artefact: `meta/review/CARD-363-cycle2.yml`.
**Cycle 3 is the last `max_cycles` allows.**

[Review 3/3] Score: 7.75 — **NOT CERTIFIED. ⚠ max cycles reached.** 1 Critical gating (F-201),
4 Minor. Artefact: `meta/review/CARD-363-cycle3.yml`. **ESCALATED as a structural convergence
failure**, and the escalation is recorded as real rather than papered over: three consecutive cycles
each found the F-001/F-101 class surviving in cells the previous reviewer had not pointed at.

[Fourth pass, commit `91f18bed`] **The remit was met: 141 `assert` statements across 30 test
functions, every one classified.** **68 passed on BOTH trees** — the branch and main's cards — which
is the number that matters, since the branch alone was structurally incapable of showing F-201.
Pre-fix for comparison, same commit `d5273798`: 67 on the branch, **2 failed / 65 on main's cards**,
reproducing exactly. How main's tree was read: a detached `git worktree` on main with the branch's
module copied in, so `REPO_ROOT` (derived from `__file__`) resolves against main's checkout.

[Fourth pass] Verdicts: **21 floors / ceilings / subsets** (moved by a correct closure, wave open,
re-stamp, re-estimate or re-cut), **28 one-sided refusals** whose only mover is the defect the module
guards, **7 census equalities each with its written reason**, **5 structural identities flagged as
such**, plus anti-vacuity guards, fixture preconditions, plant assertions and literals. Three
equalities were converted that no prior cycle had named: `len(sentinel)`, `len(est)` and `len(wave)`.

[Fourth pass] **Simulation 2b is a finding nobody had listed, me included — a THIRD red cell.**
`len(without) == 244` is also moved by a correct board operation: **CARD-310 is `ready`, `Wave: 67`,
`Estimate: 0.5d`**, so dispatching it as the convention prescribes — re-stamp the wave forward, re-price
in review cycles — takes the set to 243. Verified independently by the orchestrator: the set is 244,
its maximum wave is 73, and CARD-310 is in it. Now a **ceiling**: growth is still the defect guard 2
reds, a shrink is the convention working. **This is the same fact as wave 76's retro note** that
CARD-310 carries a stale `Wave: 67` while `ready` — reached from the opposite direction.

[Fourth pass] **A consequence of INV-023 that the orchestrator's brief did not cover: a floor must
carry the MERGE-BASE figure, not main's.** Where the two trees disagree, `>= 16` would red on the
branch for no board reason. So the `Wave`-comment floor is `>= 15` with 16 named in the message, and
the rule is stated in the module docstring and applied to `done`, `scored`, `AGREES` and
`n_of_m_blind`.

[Fourth pass] **Five simulations, eight variants, all green against main's card tree** — closure (two
shapes), wave open (two), re-stamp, re-estimate (two), re-cut. Each on a git-initialised detached
worktree, restored from captured content, `git status` of the cards dir clean both ends. **No board
card was ever written.**

[Fourth pass] **⚠ CLOSURE SHAPE, measured:** simulation 1a (three markers, score naming **cycle 3**)
and 1b (a fourth `[Review 4/3]` marker with a score naming **cycle 4**) **both pass**. What is **not**
safe is a fourth marker with a score still naming cycle 3. This card carries markers 1, 2, 3, so its
closing score must name **cycle 3**.

[Fourth pass] **My own restatement of F-202 was off by one, in the same direction as the figure it
corrected.** Measured on main: of the 49 duplicated-ordinal cards, **39 duplicate only the maximum,
9 duplicate the maximum AND a value below, and exactly 1 (CARD-192, ordinals `1,1,2`) duplicates
below without duplicating it.** I wrote "10 duplicate the maximum and something below"; it is **9**.
The 48-of-49 clause reproduces. The no-discriminator ruling still rests on the stronger ground.

[Fourth pass] **A better ground for retiring the spelling ban than any card.** On main's unmodified
tree the ban's live **in-scope set is EMPTY** — so it was green and unreachable, an **ADR-0039/R1
gap**: a claim with no control that can fail. That is a stronger reason than CARD-020 or CARD-228,
and it supersedes my framing entirely. What the two out-of-scope cards still show is kept: order and
correctness are independent in both directions, on real cards.

[Fourth pass] **The `cN` census has THREE numbers, not two:** **4** by the module's own
`_CYCLE_ORDINAL`; **5** if the trailing `\b` is dropped, admitting CARD-026's commit sha `c08fe50`;
**6** if the `(?<![\w.])` lookbehind goes too, adding CARD-219. The module asserts none and the
docstring now says which regex each number belongs to.

[Fourth pass] F-203 closed by making the static half collect strings used as path **segments** (an
operand of `/`, an argument to `Path(…)`/`.joinpath(…)`) rather than scanning substrings — deliberately
scoped, because the violation messages say "review cycle" in prose and a substring scan would be the
self-seeing inspection one level up. F-204 disclosed with a method caveat: the plant must be placed on
a card whose score is **not** `cycle N of M`, or it reds for an unrelated reason. F-205's third refusal
arm now has its own control. Full suite at `91f18bed` under the lock: **10336 passed / 27 skipped /
1 xfailed / 0 failed / 0 errors**, unarmed (no local Postgres answers, so arming would have *errored*
the 26 rather than passing them), attribution 26 + 1 = 27.

[Review 3/3] **CONTINUATION PAST THE CEILING AUTHORISED BY THE OWNER**, 2026-11-04, with a
**changed remit** — not another pointed fix. Precedent: CARD-091 ran 20 true cycles against an
aggregate ceiling of 12 on human authorisation. The new remit is **exhaustive classification**: every
assertion in the module is classified as floor or equality against the question *"can a correct board
write move this?"*, with the reason written down, and the result proven against a simulated closure,
wave open, re-stamp, re-estimate and re-cut. The three prior fixes were each correct and each
incomplete **because they were scoped to what the last review named.**

[Review 3/3] **F-201 (Critical, gating) — and the trigger was the ORCHESTRATOR's own board
operation.** Independently re-derived on main, not taken from the review: **Wave-field comments = 16**
against a declared bound of `== 15`, and **in-scope-and-contaminated = `['CARD-363.md']`** against an
asserted `== []`. Cause: wave 76's close (`54704aed`) re-stamped **this card's own** `Wave` field from
`76` to `77 <!-- RE-STAMPED … -->`. That is the board's standing dispatch convention — fifteen cards
already carry such a note — so **merging this module as it stands would turn main red.**

[Review 3/3] The third of the three cells is the sharpest and does not count anything: it **forbids
any in-scope card from carrying a comment on its `Wave` field at all**, i.e. forbids the dispatch
convention by construction. Its own comment concedes it — *"none today; the assertion exists so the
twin above cannot go vacuous."* All three cells are **unchanged since the module's first commit**
`287f1982`, so none is a regression from any fix. **Not a one-off:** simulating wave 77 opening on two
of the cut-and-unwaved CARD-367…373 with the usual dispatch note reds the same two tests on the
pre-`54704aed` tree. The module is incompatible with the convention, not unlucky in one commit.

[Review 3/3] **Explicitly NOT the fix: removing the comment from CARD-363.** That would be the board
bending to the test. The convention is correct and the assertions are wrong.

[Review 3/3] **Why two green cycles coexisted with a red main, and it is structural.** INV-023 freezes
the branch's copy of `meta/kanban` at the merge base, so the module's own suite **cannot** see
F-201 — it reads a card tree that predates every board write since the cut. Module selection measures
**67 passed on the branch** and **2 failed / 65 passed against main's tip**. This is the same
mechanism as [[branch-card-copy-is-frozen]] and it means a board-census module's branch suite is
structurally incapable of gating it.

[Review 3/3] **Everything else cycle 3 was asked to adjudicate came back clean**, each verdict
re-fired pre/post rather than read: F-101(a) closed with teeth widened (and cycle 3 tested the *real*
cycle-3 closure shape, which no prior cycle did — a third marker newest-first `3,1,2` and mid-list
`1,3,2` both red pre-fix, both green post-fix); F-101(b) closed with teeth kept; order-free and
spelling-free confirmed; F-006 verified route by route (`os.open` escapes, five of six, and the
double count is harmless because both entries are the *same path string* so a set comparison cannot
see it); all four prose retractions in place and each checked against its source; `0c` reds naming a
zero with its matched control; both tautologies flagged; the count-vs-set disclosure honest with no
overclaim. The amend's tree-hash claim **verified** — `fa6b3fc7` and `d5273798` share tree
`a05b506e` and blob `a75f6407`, message-only — and **priced as a credit**: self-caught, counted, and
the source of the wrong number named.

[Review 3/3] **Declining the discriminator ruled RIGHT on stronger grounds than the round gave.**
Three positional statistics over the 49 duplicated-ordinal cards — last ordinal is the max 49/49,
last ordinal is a duplicated value 48/49, duplicated value equals the cycle the score names 49/49 —
are **all satisfied identically by a re-entry** of equal-length invocations. The separating fact
(invocation count) is recorded nowhere enumerable. **But the figure is wrong as written** (F-202): the
39/10 split holds only under one reading — 39 duplicate *only* the maximum, 10 duplicate the maximum
*and* something below — and exactly **one** card (CARD-192, ordinals `1,1,2`) duplicates below
without duplicating it. "10 duplicate below it" reads as ten counterexamples where there is one.

[Review 3/3] **Two framings of mine refuted.** My CARD-020 claim — that the old spelling ban "missed"
a genuine misread — is wrong twice over: the ban is **in-scope-only** and CARD-020 is **wave 13**, so
it never spoke about that card at all; and CARD-228 sits in the same `first_wrong` set with `max`
reading *correctly*, so one set carries two opposite verdicts. Retracted. Also a footnote on the
`cN` census: a raw regex count really is **5**, because CARD-026 matches on a commit sha in its score
text; the round's **4** counts genuine matches. Both right about different things, and the module
asserts neither — its own ordinal regex excludes the sha via the trailing `\b`.

[Review 3/3] **F-204, the one genuine capability loss, disclosed nowhere.** The marker-agreement cell
loses a degradation the spelling ban caught: an in-scope score in the CARD-020 shape **with markers
forged to agree with the misreading** was red pre-fix and is **fully green post-fix** (67 passed),
while the matched control — the same misread score with the real marker count — still reds. The trade
is still correct, because the ban bought it by reddening on correct progression closures, but two
*lesser* limits are documented and this one is not.

[Review 3/3] **F-203** — AC-5's static half is blind to the module's own path idiom: its needles are
`meta/review` and `/review/` while the module builds paths segment-by-segment, so adding
`REPO_ROOT / "meta" / "review"` to executable code leaves all 67 green; only the **dynamic** half
catches a read of it. **F-205** — guard 1 has three refusal arms and only two have a dedicated
control; the third is live (a bare `9.0` on in-scope CARD-348 reds five tests), so the gap is in the
demonstration, not the guard.

[Review 3/3] Full suite from the branch, unarmed, under the lock for its whole length:
**10335 passed / 27 skipped / 1 xfailed / 0 failed / 0 errors.** Skips off `-rEfs` as 26
bare-`DATABASE_URL` + 1 `setrlimit`, the unarmed reading. **Zero lock refusals — CARD-370 settled a
third time.** Cross-check: cycle 2 was 10329 with 61 module tests; 67 now, and `10329 + 6 = 10335`.
Cycle 3 also **refuted the fix round's "one constant red under a copied tree"** — it was an artefact
of copying cards without a repository around them, and initialising one makes the tracked-files test
pass, so there is no red to subtract.

[Review 3/3] **A process note the orchestrator owns:** a review told to re-derive against main's tip
can have its verdict changed by a commit landing mid-review — and this one did, by a re-stamp of the
card under review. Cycle 3 recorded main's sha at review **start and end** in its artefact. That
should be standard for any board-census module.

**⚠ RETRACTED — the placement constraint is lifted** (ADR-0039/R4). This marker was written below the cycle-1 line deliberately, and the paragraph below states why. The cycle-3 fix round (`d5273798`) made the ordinal comparison **order-free** and measured **both** placements green, so the constraint no longer exists. It is retracted here rather than deleted, because leaving it standing would be the exact defect this card charges elsewhere — a document asserting both states with the stale one first. **What survives: single-ordinal is still necessary.** The repeated-ordinal arm fires on upstream's threshold double-write, which is a real guard-1 violation, so the closing cycle must emit **one** `[Review N/M] Score:` line, not two. The superseded reasoning follows.

**⚠ [SUPERSEDED] This marker is written BELOW the cycle-1 line deliberately.** F-101(a) measured that the new
re-entry check compares *consecutive written ordinals*, so placing a later ordinal above an earlier
one reds the module — and this card's notes are ordered newest-first, which is the placement its own
history establishes. Until F-101(a) is fixed, the closing stamp must be **single-ordinal AND written
below** the preceding Score line.

[Review 2/3] **All seven cycle-1 findings are genuinely closed**, each verified by re-firing its own
control rather than by reading the report. The score is flat against 7.75 only because the gating
class this cycle existed to close **survived**.

[Review 2/3] **Item 1 ruled: the F-001 fix is a REAL fix and provably information-preserving.** The
three historical classes stay equalities, unclassifiable stays `== ()`, sentinel stays `== 60`, so
any growth in `scored` can only land in AGREES and the two new floors are **derivable** from the
surviving cells: `scored >= 181 + 50 = 231`, `done >= 231 + 60 = 291`. All seven plants re-fired and
killed; the compensating plant is caught by **four** cells, not the one the round claimed. Decisive
confirmation on the live tree: `db4febab` against main's current cards → 61 passed; `287f1982`
(pre-fix) against the same cards → **3 failed / 58 passed**, exactly cycle 1's three.

[Review 2/3] **Item 2 ruled: the round was RIGHT to refuse its reviewer, and is credited for it.**
`by_class` initialises one bucket per declared class and `classification` returns one of five
constants on every path, so an unknown class would `KeyError` — the reviewer's
`== len(scored_cards(tree))` is a **tautology, a loosening dressed as a fix**. The replacement
`128 + 50 + 3 == 181` is closure-invariant, proven identical on the branch tree and on main's tip
**across CARD-348's real closure**, and red in three of fourteen plants. The cited
`tests/test_book_pdf.py` precedent is **real** (≥300 card files / ≥200 done / ≥10 not-done); one
precision — the CARD-261 comment sits on the adjacent registry floor, not on the card-census lines.

[Review 2/3] **F-101 (Critical, gates) — the module still reds on CORRECT board operations, in two
places the round's closure-framed hunt could not reach.**
**(a)** The new re-entry check is **order-sensitive**: this card closed with the house-style
`8.5 (cycle 2/3 — CERTIFIED)` reds if the Score line is written *above* the cycle-1 line and passes
if written *below*. Nothing but position differs. The round's merge-gate warning
("write it single-ordinal") is therefore **not sufficient** — a second, undisclosed constraint on
*placement* decides whether main reds.
**(b)** Three equalities grow **at the next WAVE OPEN, not at a closure**: `len(waved) == 251`,
`len(with_cycles) == 7`, `{wave for with_cycles} == {74,75,76}`. Stamping `Wave: 77` on CARD-369 —
whose estimate is already `1c (0.5d)`, so the plant is the convention *working* — reds with the bare
message **`252`** and no explanation: the same "correct card accused with no explanation" defect the
round had just fixed for F-007. CARD-367…373 are cut and unwaved. Sharpest statement: **the module
contains both spellings of the same seven cards** — `>= 7` as an anti-vacuity floor in one test,
`== 7` as a bound in another.

[Review 2/3] **Item 3 ruled: the deliberately-strict cell IS a trap, but Minor, and a narrower
replacement exists.** It bans a *spelling* on which `max` is provably right and which the module's
own message admits is right. The round's G-4 reasoning fails: G-4 forbids loosening a guard to
accommodate the **historical population**, and this cell is not a historical bound but a proxy for
"guard 1 does not rest on the heuristic" — and the proxy is wrong, since CARD-020 lands in
`first_wrong` too and there `max` really does misread. Replacement: for every in-scope card, the
distinct marker ordinals are exactly `1..max` and the score's `max` equals that maximum — order-free,
spelling-free, and it folds into F-101(a)'s fix.

[Review 2/3] **F-006's audit has the teeth claimed PLUS four escape routes.** It wraps only
`Path.read_text` and `builtins.open`; measured in this interpreter (3.14.3), **`Path.open`,
`Path.read_bytes`, `io.open` and `os.open` all escape** — `io.open is builtins.open` is True, but
`Path.open` resolves `io.open` as a *module attribute*, which rebinding `builtins.open` never
reaches. The audit's own behaviour proves it: one `read_text` records **one** entry, not two. Four of
six routes escape and the one a helper would naturally write is among them. One extra spy line fixes
it.

[Review 2/3] **F-102 — four prose claims the record or the measurement refutes, and one is
remarkable.**
**(i)** **A fabricated quotation of this card.** A test docstring reads: *CARD-363 states "two cards
carry an inline comment on a parsed field today"*. **That sentence has never existed in CARD-363, in
any version, or anywhere under `meta/`** — a pickaxe search finds it in exactly one commit,
`287f1982`, the module's own first. In the module whose subject is records that do not say what they
claim.
**(ii)** **Comment stripping is INERT and cycle 1 endorsed the opposite.** Under the module's *own*
anchored regexes, stripping changes **0 of 365** Wave readings, 0 of 365 Estimate and 0 of 365
Review-score. `^(\d+)\b` reads `68 <!-- … -->` as 68 with the comment intact. Cycle 1 put this in
`verified_correct` by substituting a **bare-integer** reading for the module's anchored one.
**(iii)** `_MARKER`'s comment calls it "the ONE marker … writes once per completed review cycle"
while the module's own docstring forty lines above measures three upstream write sites and "a cycle
that reaches its threshold emits two". Both live, no retraction — the CARD-316 shape.
**(iv)** "The decision has no ADR file" is **false**: `forge_1`'s own
`adr/0055-estimate-in-review-cycles.md` exists, accepted. The true claim is the narrower one the test
measures — *this* repo tops out at 0042 — which is what CARD-367 and `dd380092` already say. The
pin's stated trigger ("the day someone writes it") is therefore already void.

[Review 2/3] **F-103/104/105 and the rest.** `Estimate: 0c` **passes** guard 2 (`0c`, `0c (0.5d)`,
`0.0c` all → `0.0`, which is not `None`) while the matched control `0.5d` reds — and a zero
denominator *is* no denominator, in the message's own words. `len(scored) + len(sentinel) ==
len(done)` is a **tautology** (sentinel is *defined* as `done` minus `is_scored`) presented as "what
keeps the pair honest under growth"; its structural twin is correctly flagged and this one is not.
The re-entry message **misattributes the board's measured dominant cause**: it fires on
`later <= earlier`, so a *duplicated* ordinal triggers it — which is upstream's threshold
double-write, the thing this module measures on 49 cards — and reports it as "the signature of a
manual review re-entry".

[Review 2/3] **The degradation NO cell catches**, which is the question a plant list cannot answer by
construction: every bound but population 3 is a **count**, not a set. Planting CARD-002 losing both
true markers while CARD-005 gains one fabricated marker matching its named cycle leaves every count
unchanged (128/50/3/181/60/16/251/7) and **all thirteen tree-tests green**. Not a regression from the
fix — the old absolutes would not have moved either — but the standing limit of a count-based bound,
and it deserves one sentence of disclosure.

[Review 2/3] **A figure of the ROUND's does not reproduce, and it is mine too — I relayed it.** The
round claimed every figure identical on the branch tree and main's tip. **Five differ**: done
291→292, scored 231→232, agreeing 50→51, blind 209→210, `cycle N/M` census 169→170, because
CARD-348 really closed between the two readings. Every cell the round argued is *closure-invariant*
**is** identical. So the claim is wrong in letter and right in substance — and main's tip is live
proof the fix was needed.

[Review 2/3] **A dispatch convention finding, and it is the orchestrator's to fix.** The branch
worktree's copy of `CARD-363.md` is **byte-identical to the merge-base copy** (sha256-verified),
because INV-023 keeps `meta/kanban` off the card branch. So a round reading its own card from its own
worktree reads a brief with **no cycle-1 verdict and none of main's later corrections** — which is
why the fabricated-quotation finding is priced as prose rather than as a process failure. Either the
brief must carry the card's current text, or the round must read the card from main.

[Review 2/3] Full suite, unarmed, **under the lock for its whole length**: **10329 passed / 27
skipped / 1 xfailed / 0 failed / 0 errors**, exit 0. Skips read off `-rEfs` as exactly two SKIPPED
lines — `[26] tests/conftest.py:207` + `[1] tests/test_book_pdf_memory.py:1297` = 27, the **unarmed**
reading (an armed run reading 27 would itself be a finding). **Zero lock refusals anywhere in the
output**, which settles CARD-370 a second time: cycle 1's `10292 + 37 = 10329` equals this clean pass
count. Module selection: 61 passed / 0 skipped on the branch, and 61 passed / 0 skipped against
main's current cards.

**This section did not exist and the marker was written by the orchestrator, not by the review's sync point.** That is the defect this very card asserts the absence of, and it occurred on this card — the strongest available evidence for the card's own premise. Counted as ONE cycle: this cycle did not reach its threshold, so the double-Score-line shape measured in F-002 does not apply.

[Review 1/3] **The title's figures were refuted and are retracted here** (ADR-0039/R4): it said `152 of 279 closed cards`; measured, it is **128 of the 231 scored cards**, against **291** done. The `279` denominator never existed — see CARD-369 and the fourth derivation it records.

[Review 1/3] The refutation HELD on all five figures, re-derived by the reviewer's own parser against both the branch tree and main's tip, **identical on both**: 291 done / 231 scored / 60 sentinel / 128 no-marker / 50 disagreeing / **3** naming no cycle (CARD-029, 035, 066). The module's classifier was ruled **correct and strictly better than both alternatives**: 231 numeric + 50 prose + 10 bare = 291, admitting every score and no sentinel.

[Review 1/3] Full suite, unarmed: 10292 passed / **37 failed** / 27 skipped (26 bare-`DATABASE_URL` + 1 `setrlimit` — the unarmed reading). **All 37 are lock contention**: CARD-348's reviewer took the full-suite lock mid-run, the refusal text appears 71 times, and all 37 sit in the four subprocess-spawning modules. The module under review contributed no failure. Not re-run — the lock was still held and was neither overridden nor redirected. Carded as **CARD-370**.

[Review 1/3] Three cards cut: **CARD-368** (nothing guards the three-copy estimate agreement — and `board.md` claimed THIS card did; that claim is retracted), **CARD-369** (the upstream cycle counter double-counts a threshold-reached cycle: 50 apparent disagreements collapse to **2** with zero regressions, era-bounded CARD-113..CARD-192), **CARD-370** (the lock contention above).

[Review 1/3] What the merge gate still owes, per the review: a full suite re-run **after** the closure stamp (the run F-001 reds) and after CARD-348 releases the lock; the AC→test mapping stated on the card, which the branch cannot carry under INV-023.
