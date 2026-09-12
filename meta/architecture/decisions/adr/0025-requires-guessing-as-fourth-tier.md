# ADR-0025: "Requires guessing" is a fourth difficulty tier, not a flag

**Status:** Accepted
**Date:** 2026-09-12
**Deciders:** Puzzle Creator (project owner)
**Revised:** —
**Migration:** on-touch
**Pattern:** —
**API-Posture:** —

## Context

FR-026 (2026-09-12) makes two things explicit that the difficulty model had
left implicit. First, a puzzle solved entirely by line logic must be graded
across the *whole* difficulty scale by how much line reasoning it needed
(sweeps to fixed point, first-sweep share, lines that needed the full
placement DP), so that two line-solvable puzzles of different depth land in
different bands (AC-118, AC-119). Second, whether a puzzle *requires guessing*
— the search branched at least once — must be an explicit attribute of the
scored result. EC-015 pins the meaning of that attribute: it is set if and
only if the solver's `branch_nodes` for the solve is greater than zero. It is a
fact about the solve, never a threshold on a score (AC-120, AC-121). FR-026
deliberately leaves open whether the attribute is a boolean *beside* the tier
or a *tier of its own*; DEC-030 is that question.

The answer is not cosmetic. Today `Tier` is a three-member `StrEnum`
(`easy`/`medium`/`hard`) in `src/nonogram/difficulty.py`, and
`tier_for_score` is the single classifier: a tier is a bucket a scored
candidate fell into, drawn from ADR-0005's 33/66 tertile bands on ADR-0013's
0..100 scale. That one attribute is read by every surface the project has:
`--difficulty` on the CLI (FR-008/FR-010, AC-020/AC-021) and the web form,
POL-004's resample predicate ("score outside the requested tier's band"), the
JSON/CSV export (ADR-0023's schema), the PDF filename
`<name>-<difficulty>.pdf` (ADR-0016, with the held DEC-026 revision pending),
the admin review's tier filter and the DB tier column. Whichever shape the
attribute takes, all of those consumers change; the question is whether they
gain a *value* or a *second field*.

The product reason recorded at intake bounds the choice: printed puzzle books
need puzzles that are always logically solvable but graded in depth. A book
editor's request is "give me Hard puzzles that never need a guess". Under
ADR-0013's current formula the only route into Medium and Hard is
backtracking, which is exactly backwards for that workflow — and AC-023
("zero backtracking scores at the easiest end") is already flagged as
contradicted by FR-026 for the same reason.

The formula that replaces ADR-0013, and what becomes of ADR-0005's 33/66
cutoffs on the new scale, is DEC-031 — which depends on this decision because
whether branching puzzles must be *ordered on the scale at all* changes the
formula's term list. NFR-007/CON-014 (the tier decision is a pure function of
structural solve signals, never of elapsed time) hold under either
alternative and are not at issue here. CARD-072 (record the strategies a
puzzle needs and save them with it) also waits on this: its strategy list and
the tier must derive from the same solve facts.

## Decision

We adopt **guessing_as_separate_tier**: the tier enum becomes **Easy, Medium,
Hard, Guess**. Easy/Medium/Hard grade *line-solvable* puzzles by reasoning
depth across the whole 0..100 scale; any solve with `branch_nodes >= 1` is
classified **Guess** by that fact alone, regardless of its score. Easy,
Medium and Hard therefore never contain a puzzle that needs a guess, and
`--difficulty hard` promises a logically solvable, deep puzzle — the book
workflow in one word.

Concretely:

- **Classification takes `(score, branch_nodes)`.** `tier_for_score(score)`
  alone can no longer classify a result; the single classifier lives in
  COMP-006 (`difficulty.py`) and takes both inputs. It applies EC-015 first
  (`branch_nodes > 0` → `Tier.GUESS`) and the score bands only to the
  remainder. There is one classifier, as today, so a retune cannot move a band
  without moving the classification with it.
- **POL-004 stays a single tier test.** The resample predicate remains "the
  candidate's tier is not the requested tier"; requesting `guess` is a
  legitimate request the loop can satisfy, and requesting any other tier
  discards branching candidates by the same one comparison.
- **Enum value `guess`, display label "Guess".** The value is what the user
  types, the export carries and the filename is built from — it is the
  contract. The label is presentational, produced by `Tier.label` as today,
  and may be renamed later (e.g. to "Expert") without changing the value or
  any stored data.
- **Cutoffs are untouched here.** The 33/66 tertiles of ADR-0005 stay as
  written until DEC-031 re-draws them on the new scale; this ADR fixes the
  *tier model* (three score bands plus one solve-fact tier), not the bands'
  positions.

We chose this over the flag because one attribute, one selector on every
surface is what the stated product reason asks for. The flag alternative is
the lower-cost change to the enum, but it moves the cost onto every consumer:
each must read two attributes to answer the one question the user asks, and
`--difficulty hard` alone could return a puzzle that needs guessing — a
silent failure of the book workflow's core promise. The enum growth is real
work but mechanical, and DEC-026 already queues the same filename work.

## Alternatives considered

### guessing_flag_beside_tiers

The scored result carries `requires_guessing: bool` next to a tier still drawn
from three score bands; branching puzzles are graded on the same scale as
line-solvable ones, so DEC-031's formula must keep a branch term. Requesting
"no guessing" needs a second selector (`--no-guessing`, a web checkbox, a
second admin filter), and POL-004 gains a second predicate counted against
the same retry bound. Its merits are real: ADR-0005's pure model — "a tier is
a bucket a scored candidate fell into" — survives with only its cutoffs
touched; `Tier`, the export schema and the filename convention keep their
three values; and a one-guess and a many-guess puzzle still differ in score.
Rejected because it forces every consumer to read two attributes to describe
the one thing the user cares about, and because `--difficulty hard` on its own
would no longer promise a logically solvable puzzle — the book workflow would
need an extra flag on every request and every surface, which is precisely the
shape the intake asked us to avoid.

## Consequences

### Positive

- One attribute, one selector: `--difficulty hard` *is* "logically solvable,
  deep". The CLI, the web form, the admin filter, the export and the filename
  each gain one enum value instead of a second field, and POL-004 stays a
  single tier comparison.
- "Logically solvable" becomes a property of the tier rather than a flag to
  remember to check, so no consumer can accidentally ship a guessing puzzle
  under a Hard label.
- DEC-031 can define its scale over line-solvable puzzles only — where the
  intake names the signals — and the branch term with its size-relative
  normalisation problem (ADR-0013's hardest part) drops out of the formula.
- Classification remains a pure function of structural solve signals
  (`score`, `branch_nodes`), so NFR-007/CON-014 hold by construction and
  EC-015's property test has a single function to pin.

### Negative

- ADR-0005's "tier = score band" model breaks for one member: Guess is keyed
  by a solve fact, not a score. `tier_for_score` cannot stand alone any more,
  and every `Tier` consumer must handle a fourth member — `parse_tier` and its
  error message (AC-021 lists "the three that exist"), the web form's options,
  ADR-0023's export schema (`difficulty` may now be `"guess"`), ADR-0016's
  filename (`<name>-guess.pdf`, and DEC-026's held revision gains the same
  fourth value), the admin status/tier filters and the DB tier column.
- No grading *inside* Guess: a puzzle needing one guess and one needing many
  land in the same tier. A score may still be exported beside the tier if
  DEC-031 keeps a branch term, but the tier does not show the difference.
- Two existing criteria are contradicted outright and must be re-worded as a
  follow-up in `requirements.yml` (not done here): AC-023 (already flagged
  CONTRADICTED under FR-009) and AC-020's three-tier listing under FR-008.
- Stored puzzles graded under the three-tier model keep a tier that may be
  wrong under this one (a branching puzzle sitting in Hard). Migration is
  on-touch: rows keep their tier until re-scored; the re-grade of stored
  scores is DEC-031's migration, since it is the formula change, not the tier
  model, that invalidates the numbers.

### Neutral

- ADR-0005 is revised by this decision (tier model), not superseded: its
  33/66 cutoffs stand until DEC-031 re-draws them; the revision note there
  should point here.
- ADR-0023's export schema gains a value, not a field; whether that needs a
  `SCHEMA_VERSION` bump is for the export change to decide by that ADR's own
  rule (bump only when an existing reader could not survive) — a reader that
  parses `difficulty` through `Tier(...)` would reject `"guess"`, so it
  likely does.
- The display label "Guess" is a presentation choice and may change; the
  enum value `guess` is the contract every stored row, export and filename
  depends on.
- Unblocked by this ADR: DEC-031 (formula and cutoffs on the new scale, with
  no branch term) and CARD-072 (strategies saved with the puzzle — "guess" is
  now both a strategy and a tier, derived from the same `branch_nodes` fact).

## Rules
```yaml
- id: ADR-0025/R1
  statement: A scored result whose solve reports branch_nodes > 0 is classified Tier.GUESS, and a result with branch_nodes == 0 is never Tier.GUESS, regardless of score (EC-015). The Easy, Medium and Hard tiers contain only line-solvable puzzles.
  scope: {contexts: [CTX-001], code: ["src/nonogram/difficulty.py", "src/nonogram/orchestrator.py"]}
  check: {kind: review-lens}   # becomes {kind: test, ref: PropertyTest_ScoreDifficulty_RequiresGuessingIffSearchBranched} once EC-015's test lands
  severity: mandatory
- id: ADR-0025/R2
  statement: Tier classification has exactly one implementation, in difficulty.py, taking (score, branch_nodes); no other module derives a tier from a score or from branch_nodes on its own.
  scope: {contexts: [CTX-001], code: ["src/nonogram/**"]}
  check: {kind: review-lens}
  severity: mandatory
```

## References

- DEC-030 (resolved by this ADR)
- CTX-001 (Puzzle Creation — owns the tier, the resample loop and every
  export surface the enum reaches)
- FR-026, EC-015, AC-118..AC-121 (the criteria this decision satisfies)
- FR-008, FR-009, FR-010, POL-004 (the tier selector and resample predicate
  this decision re-shapes); AC-020 and AC-023 (to be re-worded)
- NFR-007, CON-014 (pure-function-of-structural-signals rule, preserved)
- ADR-0005 (revised: tier model becomes three score bands plus one
  solve-fact tier; cutoffs untouched pending DEC-031)
- ADR-0013 (formula; its replacement is DEC-031, which depends on this ADR)
- ADR-0023 (export schema: `difficulty` may now be `"guess"`)
- ADR-0016 and held DEC-026 (PDF filename gains a fourth tier value)
- CARD-072 (strategies saved with the puzzle; depends on this ADR)
- `src/nonogram/difficulty.py` — `Tier`, `tier_for_score`, `parse_tier` as
  they stand before this decision

## History

- 2026-09-12: Created — resolves DEC-030 by making "requires guessing" a
  fourth tier (`guess`) keyed on `branch_nodes >= 1`, so that Easy/Medium/Hard
  grade only line-solvable puzzles and `--difficulty hard` promises a
  logically solvable one; chosen over a boolean flag beside the tier because
  the book workflow needs one attribute and one selector on every surface.
