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
- ~~**It selects nearly the same set for every card on this board.**~~ **FIXED the same day, and the
  cause was not what this paragraph assumed.** It was not a fact about the model's rules; it was one
  key. `system_rules.py` matches a rule to a card by context **before** it consults the rule's `code:`
  glob, and the branches short-circuit:

  ```python
  elif any(c in card_contexts for c in r.contexts): out.append(r)   # matched first
  elif _rule_matches_globs(r, card_globs): out.append(r)            # never reached
  ```

  31 of the model's rules carried `contexts: [CTX-001]` **alongside** a precise `code:` list — and
  none carried `contexts` alone. On a single-context project that key matches every card, so every
  precisely-scoped rule behaved as package-wide and its authored glob was decorative. `ADR-0037/R1`
  is scoped to **one file** and was reaching a card that never touches it.

  The key was removed from all 31 (2026-10-19); the globs were left exactly as their ADRs authored
  them. Measured effect: **CARD-247, a player-toolbar card, went from 16 rules to 11** — the book
  geometry and orchestrator-repair rules now land only on cards that touch those files — while
  **CARD-225, a book-layout card, keeps all of them** at 14. `ADR-0039` still reaches every card, and
  its own scope was *widened* to `["tests/**", "src/nonogram/**"]`, because the instances that cost
  the most cycles were claims in source docstrings. Validator: **0 errors**; no rule's globs match
  zero files, so nothing was silently retired.

## One trap, paid for during the writing of this file

A rule's `check.ref` is a **logical name**, not a Python symbol. It resolves through a mapping table at
the top of the owning test file — e.g. `tests/test_sourcing_random.py:18` carries
`AC-128  TestGenerateRandom_RefusesDensityZeroAndHundred  test_generate_random_refuses_density_zero_and_hundred`.
Grepping for `class <ref>` finds nothing and makes 20 of the model's 33 checks look dead. They are not.
**Resolve a ref through the owning file's table before concluding anything about enforcement** — the
first draft of this convention was built on that false reading and had to be withdrawn.

## A trap in rule 2, found while curating CARD-254 and CARD-255 (2026-10-20)

Rule 2 says to keep a `kind: test` rule whose ADR **declares a reach limit**, and names the idiom to
grep for: *"Reach, stated rather than implied"*. Two things make that grep fail silently, and both
bit on the first wave that used it:

1. **`system_rules.py`'s output does not carry the ADR's comment text at all.** The emitted rule
   carries `id`, `source_kind`, `statement`, `severity`, `scope`, `check` — and nothing else. A
   curation script that reads the tool's YAML can therefore *never* match the idiom, and drops every
   rule under rule 2. **Read the ADR files, not the tool output.**
2. **The idiom's case varies.** ADR-0036 and ADR-0037 write "Reach, stated rather than implied";
   **ADR-0039 writes "REACH, stated rather than implied"** in capitals. A case-sensitive grep keeps
   the first two and drops the third — which is to say, it drops exactly the rule family this whole
   convention exists to protect, for the third time (CARD-250, CARD-251, and nearly here).

The derivation that works: collect the ADR *files* whose text matches the idiom **case-insensitively**,
and keep every `kind: test` rule belonging to them. On CARD-254 that moves the contract from 5 kept to
**10**; on CARD-255 from 2 to **5**. Both cards are about guards — one removes a guard, one adds one —
so a contract without ADR-0039 would have been a contract missing its only relevant rule.

**Sanity check worth running every time**: if the card's `Touches` includes `tests/**` or
`src/nonogram/**` and ADR-0039 is *not* in the kept set, the derivation is broken, not the scope.
