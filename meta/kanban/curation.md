# Curating a card's System contract

_The decompose station reads this. Written 2026-10-19 after the waves 44–47 retrospective found the
previous convention dropping the one rule it most needed to keep — twice, on the two cards that then
produced ten instances of the family that rule exists to prevent._

## The rule

> **Curate in every in-scope rule whose enforcement does not reach the card's new code. Drop the rest.**

Concretely, from `system_rules.py --card CARD-NNN --root meta/architecture`:

1. **KEEP** every rule whose `check.kind` is `review-lens`. Nothing executes these. They are enforced
   only if a reviewer is told about them, which is what the contract is for.
2. **KEEP** every rule whose own ADR comment **declares a reach limit** — a `kind: test` check that
   says it does not reach code written later. Today that is `ADR-0039/R1–R3`, whose comments read
   *"they do not reach a guard written tomorrow… new guards are reached by the decompose lens and
   `forge:review` Step 8h"*. The idiom to grep for is *"Reach, stated rather than implied"*, which
   ADR-0039/R1 introduced and ADR-0036 and ADR-0037 have since followed.
3. **DROP** the remaining `kind: test` rules. The suite executes them on every gate, so listing them
   in the contract adds a line a reviewer must read and changes nothing about whether they hold.
4. **Declare the dropped count**, as before.

## Why this replaces "ship 6–14 by judgement"

The previous convention (owner, 2026-10-17) was right about the disease — a ~53-rule contract
measurably produces fake review coverage — and gave no cure but orchestrator judgement. That judgement
dropped `ADR-0039` on **CARD-250** (`Curated to 8; 49 dropped`) and on **CARD-251**
(`Curated to 10; 48 dropped`).

**Severity cannot be the discriminator and must not be re-graded to become one.** 60 of 61 rules in the
model are `mandatory`; `forge:review` defines a mandatory violation as gating and an advisory one as
`Minor`; and every one of the 13 rules nothing executes is genuinely binding — `ADR-0038/R6` and
`CON-021` are security, `ADR-0033/R1` is data integrity. Downgrading any of them would assert that
violating it is a minor matter. Severity answers *"does a violation gate?"*; curation asks *"must a
reviewer be told?"*. Different questions.

## Measured against the two cards that exposed the problem

| | projection | proposed keep | of which review-lens | reach-limited | shipped under the old convention |
|---|---|---|---|---|---|
| CARD-250 | 57 | **16** | 13 | ADR-0039/R1–R3 | 8 — **ADR-0039 dropped** |
| CARD-251 | 58 | **16** | 13 | ADR-0039/R1–R3 | 10 — **ADR-0039 dropped** |

Both would have carried ADR-0039. Both keep `ADR-0038/R1/R4/R7/R8` and `CON-021`, which the old
convention kept on CARD-250 by instinct and dropped on CARD-251.

**Two honest consequences, stated rather than discovered later:**

- **16 exceeds the old 6–14 band.** The band was a guess at a tolerable length; 16 is what the rule
  selects here. Prefer the rule and let the number be what it is — a contract whose length is derived
  is worth more than one whose length was chosen.
- **It selects nearly the same set for every card on this board.** That is not a defect of the rule but
  a fact about the model: the unenforced rules are a property of the area, not of the card. If that
  set ever shrinks it will be because dead enforcement was fixed, which is the right reason.

## One trap, paid for during the writing of this file

A rule's `check.ref` is a **logical name**, not a Python symbol. It resolves through a mapping table at
the top of the owning test file — e.g. `tests/test_sourcing_random.py:18` carries
`AC-128  TestGenerateRandom_RefusesDensityZeroAndHundred  test_generate_random_refuses_density_zero_and_hundred`.
Grepping for `class <ref>` finds nothing and makes 20 of the model's 33 checks look dead. They are not.
**Resolve a ref through the owning file's table before concluding anything about enforcement** — the
first draft of this convention was built on that false reading and had to be withdrawn.
