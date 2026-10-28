# ADR-0039: A test guard's coverage claim is only as wide as the control that can fail

**Status:** Accepted
**Date:** 2026-10-17
**Deciders:** Puzzle Creator (project owner)
**Revised:** 2026-10-28 (R4 added — the family's fourth measurement, on figures rather than guards)
**Migration:** on-touch
**Pattern:** —
**API-Posture:** —

## Context

CON-005 is the one mandatory-severity constraint in the model, and ADR-0014 answered it by
requiring an independent brute-force oracle for the solver's uniqueness verdict. That pattern —
a claim is worth what the thing that could refute it is worth — has since been applied far
beyond the solver: this project's test tree now carries structural guards that make assertions
about *themselves*, auditing the package for a second drawing site, for a test that reads the
owner's gitignored timing log, for a module that silences itself above its own guards.

Those guards have a recurring defect, and it has been measured rather than suspected. Across
three cards and ten review cycles — CARD-238 cycles 1–5, CARD-228 cycles 1–3, CARD-239
cycles 1–2 — nineteen gating findings reduce to one sentence: a guard's stated coverage was
wider than the mechanism that enforced it. Two of those cards escalated. The pattern is not a
property of any one component: it appeared in a timing-log audit, in a page-geometry guard, and
in a module-scope-silencing guard, written at different times for different subsystems.

The family has already been promoted once. On 2026-10-05 a wave-33 retrospective wrote it into
the kanban implementation brief as "a comment or docstring claim about what a test catches needs
a mutant proving it". It did not bite, and the wave-40/41 retrospective diagnosed why in two
parts: living in a brief, it carried no `check:`, so nothing executed it; and its wording was
satisfiable while the defect persisted, because a mutant *inside* a claimed region passes while
the claim's *scope* stays unbounded. The 2026-10-16 approval to promote it into the model with a
check was not executed, and wave 42 then paid for the family across its two most expensive cards.

Two further facts bound the solution space. First, waves 41 and 42 produced three successively
sharper statements of the family rather than one — the later ones are not restatements, and each
names a mechanism the earlier one permitted. Second, the discriminator for whether such a guard
converges has been observed twice *within single cards*: the halves whose sets derive from an
authority (`dir(os)` and friends; `dir(ImageDraw.ImageDraw)`) were sound from their first pass,
while the sibling halves in the same cards, over surfaces with no enumerable authority, took
three cycles and two. EC-001's discipline — a property needs something independent to check it
against — is the standing precedent, but it is stated for the solver and nowhere generalised.

## Decision

We adopt three standing rules of the model, R1–R3 below, each checked by a test that exists and
executes in this repository today, and each stating its own reach rather than implying
repo-wide enforcement.

Three rules rather than one clause-bearing rule, because the observed failure modes are distinct
and separately satisfiable: CARD-239 honoured the completeness discipline and broke the exemption
discipline in the same module, and a single rule would have carried one `check:` ref for three
mechanisms that no single test can fail for. Each rule's check points at a test the paying cards
built, so the family is enforced by the mechanism its own provenance produced — which is the one
thing the 2026-10-05 promotion lacked.

The rules' checks cover the guards that exist. They do not reach a guard written tomorrow, and
R1–R3 say so in their own comments instead of implying otherwise; new guards are reached by the
decompose lens (6c4) and `forge:review` Step 8h until they carry audits of their own. Overclaiming
the reach here would commit, inside the rule meant to prevent it, precisely the defect the rule
is about.

## Alternatives considered

### One rule with three clauses
A single statement requiring that a guard derive its set or default-deny, carry a completeness
test written before the set, give every member and exemption a control, and record residue as a
bound. Rejected on the mechanics of the collector and the lens rather than on the content, which
is the same: there is no single test in this repository that fails for all three clauses, so the
rule would have had to pick one ref and leave two mechanisms unchecked. It would also hand every
card touching `tests/**` all three clauses regardless of applicability, which is how the
2026-10-05 brief promotion became background noise rather than a constraint.

### Defer, and build a repo-wide guard audit first
A meta-test that walks `tests/**`, finds every guard consulting a set, and asserts each carries a
completeness test and a discriminating control — then one rule pointing at that audit. This is
the strongest available check and would reach guards nobody has written yet. Rejected as the
*first* step, not as an idea: it is a card's worth of work, and the family has cost a wave each
time it stayed unpromoted, including the wave in which this very promotion was already approved.
Recorded as follow-up work instead, with these rules in force meanwhile.

### Leave it in the implementation brief and strengthen the wording
The 2026-10-05 approach, with sharper language. Rejected because the diagnosis of its failure was
specific and is not a wording problem: a brief carries no `check:`, so nothing executes it, and no
amount of rewording gives a brief a failing test.

## Consequences

### Positive
- The family gains three executing checks where it previously had none. A regression in the
  discipline of the guards that taught it now fails a test run rather than waiting for a reviewer
  to notice it a fourth time.
- The authority test (R2) is cheap to apply before a guard is written and was validated twice
  within single cards, which is stronger evidence than a promoted rule usually carries at
  promotion time.
- R3 names the construct that both earlier statements of the family reached for as their honest
  escape hatch. An exemption now carries the same burden of proof as a set member, which is where
  CARD-239's two cycles went.
- The decompose lens can hand a card the rules its `Touches:` intersect, so a card editing
  `tests/**` inherits the family's cost as a constraint rather than re-learning it.

### Negative
- Three mandatory rules scoped to `tests/**` is three more standing rules the lens hands every
  card that touches the test tree, including cards for which they are formally applicable and
  practically irrelevant. The cost is real and is accepted in exchange for not paying the family's
  price a fourth time.
- The checks are specific tests, not a repo-wide audit, so a guard written tomorrow is covered by
  judgement rather than by mechanism until the deferred audit exists. This is stated in the rules
  and remains the honest limit of this decision.
- R2's default-deny prescription is not free: making the unparseable a failure reddens honest code
  that the guard cannot analyse, and each such site then needs an exemption with a reason — which
  R3 then makes answerable for its own control. The discipline is self-reinforcing and therefore
  not cheap to adopt in a new guard.

### Neutral
- Three check refs now exist in the trace surface and will appear in `--verify-refs` output; two
  live in `tests/test_suite_profile.py` and one in `tests/test_book_difficulty_dots.py`, so a
  rename in either file is a dead-ref diagnostic rather than a silent loss.
- `Migration: on-touch` — guards already in `tests/**` that predate these rules are brought into
  line when a card next touches them, not in a sweep. Existing guards that do follow the rules are
  their provenance and need nothing.
- A repo-wide guard audit is now recorded follow-up work; when it exists, these rules' checks
  should be re-pointed at it and their stated reach widened accordingly — which is itself an
  application of R1 to this ADR.

## References

- DEC-042 (resolved by this ADR)
- CTX-001 (the single bounded context; the rules are scoped to its test tree)
- CON-005 (uniqueness must never produce a false positive — the standing precedent for
  claim-versus-mechanism in this model)
- EC-001 (the property CON-005 is tested by, and the narrowest prior instance of this discipline)
- ADR-0014 (uniqueness correctness oracle — the same reasoning, stated for the solver only)
- Provenance: CARD-238 cycles 1–5, CARD-228 cycles 1–3, CARD-239 cycles 1–2; nineteen gating
  findings, two escalations. Retrospective sections: `meta/kanban/retro.md` "Waves 40–41" and
  "Wave 42".

## History

- 2026-10-17: Created — resolves DEC-042. Promotes a finding family measured across three cards
  and ten review cycles into three standing rules with executing checks. Supersedes, in substance,
  the 2026-10-05 promotion of the same family into the kanban implementation brief, which carried
  no check and whose wording was satisfiable while the defect persisted.
- 2026-10-28: **R4 added** — promotes the same family's fourth measurement, this time on
  **figures rather than guards**, from wave 62's retrospective. R1 already said the sentence
  (*"a claim whose control cannot fail is narrative, not coverage"*) and **did not bite**: of
  wave 62's 7 gating findings, 6 were this family and **4 lived outside R1–R3's scope** — two
  in `meta/profiling/**`, one in `meta/kanban/**`, one unfiled — while the three inside
  `tests/**` were prose claims about numbers, not a guard's coverage claim over a set. So the
  cause was scope **and** subject, and the remedy is a sibling rule rather than a duplicate or
  a third scope widening. Provenance: CARD-292 cycle 1 F-001/F-002, cycle 2 F-201/F-202;
  CARD-287 cycle 1 F-287-01/-02/-03.

## Scope revision — 2026-10-19

R1–R3 were authored with `code: ["tests/**"]`, on the reading that a guard is a test. Waves 46–47
measured otherwise: of the ten instances of this family, the ones that cost the most review cycles
were claims written in **source docstrings and comments** about what a test catches — `puzzle_edit.js`'s
header and `inFlightIs`, `app.py`'s and `puzzle_review.py`'s `Returns:` blocks — which `tests/**` does
not reach. That is also the reading this ADR's own Context records from the wave-33 promotion: *"a
comment or docstring claim about what a test catches needs a mutant proving it"*.

The three scopes therefore now read `["tests/**", "src/nonogram/**"]`. The statements are unchanged.

Separately and mechanically, the `contexts: [CTX-001]` key was removed from these and 28 other rule
scopes across the model on the same day. On a single-context project that key matched every card
before the `code:` glob was ever consulted (`system_rules.py`: the contexts branch short-circuits the
glob branch), so every precisely-scoped rule was behaving as package-wide. Removing it is what makes
the authored globs load-bearing — including these two.

## Promotion — 2026-10-28: the family's fourth measurement, on figures

The 2026-10-19 revision above widened R1–R3 from `tests/**` because waves 46–47 measured that
the costly instances were claims in **source docstrings**. Wave 62 is the same discovery one
layer out: the costly instances were **figures in artefacts**, and they were costly in a
specific way — they were not wrong about the code, they were wrong about *how they had been
measured*.

What it cost, measured rather than suspected. Two cards, six review cycles, **7 gating findings
of which 6 are this family**:

| finding | the claim | what it actually was |
|---|---|---|
| CARD-292 c1 F-001 | a host cell reported through `pgrep -fc` | **not a flag on this platform** — exit 2, and an *empty* cell inside `$(...)` |
| CARD-292 c2 F-201 | its replacement, `pgrep -f 'bin/python -m pytest'` | **blind** — reads 0 whether or not pytest runs, because the venv's framework python re-execs through `Python.app`; and false-*positive* on a wrapper naming it. Wrong in both directions |
| CARD-292 c2 F-202 | "the right counts" | right counts, **wrong domain** — all 108 analyses were over planted texts, none over the real module |
| CARD-287 c1 F-287-01 | `get_source_segment` "re-splits the **whole** source" | a **bounded prefix**, mean 81.1 % — and the claim sat **300 lines from its own retraction in the same file** |
| CARD-287 c1 F-287-02 | "predicted 15.04, measured 15.19 — **1.0 %**" | **two compensating errors**: an over-measuring instrument subtracted from a *superseded* baseline. Honest figure 6–8 % |
| CARD-287 c1 F-287-03 | the capture is "the guard's **entire** observable answer" | **seven axes missing**, and "ten configurations" was 12 calls of which 4 were captured in full |

Three further facts decided the rule's wording rather than being decoration:

- **An instrument that cannot rise is indistinguishable from a quiet box.** `pgrep -fc`'s
  successor reported `0` for an entire session and nobody could tell, because *every* reading was
  0 and the box genuinely was quiet. What closed it was a **truth table with both controls** —
  five cases including a `zsh -c` whose own argv merely *mentions* pytest — now carried in
  `meta/kanban/config.yml`. Hence R4's positive **and** negative control.
- **A ratio's halves can come from different instruments.** CARD-292's published 9.9× speed-up
  divided a *profiled* numerator by an *unprofiled* denominator; through one door it is 8.0×.
  CARD-287 then repeated the shape at smaller scale. Hence R4's domain clause.
- **Three stations quoted three points for one quantity.** Cycle 2 said 22.0 %, fix round 2 said
  21.2 %, cycle 3 measured 21.30 / 21.52 / 21.86 and established the honest answer is a **band**,
  21.2–22.0 %, because the denominator carries 5.5 % run-to-run spread. A point estimate for a
  quantity with that spread is the defect, not any one of the points.

**The second family stays unpromoted and is recorded here as the one to watch**: *a refuted figure
must be retracted everywhere it was written.* One gating instance (four docstrings carrying the
306 KB that the same round had struck out) plus CARD-287's reinstatement. R4's last sentence states
it, but it has not yet been paid for twice in two cards — if it recurs it earns its own rule rather
than a clause.

## Rules

```yaml
- id: ADR-0039/R1
  statement: >-
    A set a guard consults needs a completeness test written before the set, and
    any claim the guard makes about what it catches needs a control that can fail:
    caught WITH the set member present, missed WITHOUT it. A claim whose control
    cannot fail is narrative, not coverage, and must be narrowed to what is
    measured or deleted.
  scope: {code: ["tests/**", "src/nonogram/**"]}
  check: {kind: test, ref: test_the_control_for_each_spelling_depends_on_the_set}
  # tests/test_suite_profile.py — the CARD-238 artefact this rule generalises: a
  # control must be caught WITH its set member and missed WITHOUT it, which is a
  # guard on the guards' discriminating power. REACH, stated rather than implied:
  # this ref executes and fails if THAT guard's discipline regresses; it does not
  # reach a guard written tomorrow. New guards are reached by the decompose lens
  # (6c4) and forge:review Step 8h until the deferred repo-wide guard audit exists.
  severity: mandatory
- id: ADR-0039/R2
  statement: >-
    A guard's set is derived from an authority the runtime can enumerate, not
    hand-written. Where no such authority exists, the guard defaults to deny:
    a shape it cannot analyse is a FAILURE, never a silent pass, and the
    unanalysable sites become named exemptions under ADR-0039/R3.
  scope: {code: ["tests/**", "src/nonogram/**"]}
  check: {kind: test, ref: test_the_guard_sets_are_derived_and_not_hand_written}
  # tests/test_suite_profile.py. The discriminator was observed twice WITHIN single
  # cards: halves deriving from dir(os)/dir(ImageDraw.ImageDraw) were sound from the
  # first pass, while sibling halves over surfaces with no enumerable authority took
  # three cycles and two. A completeness test over a hand-enumerated set of syntactic
  # shapes is not a completeness test, because no authority enumerates the shapes.
  # Same stated reach as R1.
  severity: mandatory
- id: ADR-0039/R3
  statement: >-
    An exemption is a claim. Every exemption a guard grants carries a control for
    what it must NOT absorb — caught with the exemption removed, missed with it in
    place — is held to an equality against the sites that exist today, and records
    whatever it still cannot see as a measured bound with its own failing control.
  scope: {code: ["tests/**", "src/nonogram/**"]}
  check: {kind: test, ref: test_the_dingbat_exemption_is_only_for_a_module_that_cannot_draw}
  # tests/test_book_difficulty_dots.py — an equality against the modules that carry
  # the codepoint today, plus a second assertion that the exempt module cannot draw,
  # so the exemption can neither grow to cover a drawing module nor outlive its
  # reason. CARD-239 cycle 2 is the counter-example this rule exists for: the fix for
  # a too-narrow predicate added an exemption that re-opened the same route one hoist
  # later, and its controls tested only what it exempted. Same stated reach as R1.
  severity: mandatory
- id: ADR-0039/R4
  statement: >-
    A figure is a claim, and the instrument that produced it is part of it. Every
    figure committed to code, to a card or to an artefact names its instrument, and
    that instrument must be executable on the host that recorded the figure and
    demonstrated to respond to what it measures: a POSITIVE control that it rises,
    and a NEGATIVE control that it does not rise on a near-miss. A reading that
    cannot distinguish "the quantity is zero" from "the instrument is blind" is not
    a measurement. A figure's DOMAIN — which population, which revision, which arm —
    is part of the figure; a ratio whose halves come from different instruments,
    different runs or different baselines is not a ratio. A figure recomputed and
    refuted is retracted everywhere it was written.
  scope: {code: ["tests/**", "src/nonogram/**", "meta/profiling/**", "meta/kanban/**"]}
  check: {kind: review-lens}
  # NO EXECUTING CHECK TODAY, stated rather than implied: nothing in the tree can
  # decide whether a committed number names a live instrument, so a test ref here
  # would read as mechanically checked while checking nothing. The lens carries it
  # (decompose 6c4 writes it into a card's System contract; forge:review Step 8h
  # holds the diff to it) and **CARD-304 owes the flip** to an executing check over
  # the artefact directories. The scope is WIDER than R1–R3 on purpose: wave 62
  # measured 4 of its 7 gating findings OUTSIDE `tests/**` + `src/nonogram/**`.
  severity: mandatory
```
