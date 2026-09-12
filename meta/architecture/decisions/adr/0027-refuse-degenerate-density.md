# ADR-0027: Refuse degenerate density at the validation seam

**Status:** Accepted
**Date:** 2026-09-12
**Deciders:** Puzzle Creator (project owner)
**Revised:** —
**Migration:** rewrite
**Pattern:** —
**API-Posture:** —

## Context

FR-004 lets a random-generation request (FR-001) carry a target density as a
percentage, and AC-011 pins that an out-of-range request — its example is
150% — is rejected with an error before any grid is produced. The check that
enforces this is `validate_density` in `src/nonogram/sourcing/random_grid.py`,
a pure domain function placed inward of argparse per ADR-0010, and today it
accepts the closed interval 0..100 (`MIN_DENSITY = 0`, `MAX_DENSITY = 100`).

The two ends of that interval behave unlike every other value in it. A
request for density 0 draws an all-empty grid; a request for 100 draws an
all-filled one. Every row and column clue of the first is the empty-line
marker `(0,)`; every clue of the second is the full line length. Neither grid
leaves the solver anything to deduce, so both pass the uniqueness check
(FR-006) trivially and are scored as Easy (0.000 and 0.001 respectively).
Nothing downstream — uniqueness, difficulty, export, the admin batch path or
the book pipeline — refuses them, and the 2026-09-12 review
(docs/GENERATION_ALGORITHM.md §10.2, finding 2) confirmed that a request at
either end ships as a product artefact: a PDF page with a blank or solid grid.

The code disagrees with itself about this. The comment above `MIN_DENSITY` /
`MAX_DENSITY` (random_grid.py:78-84) states that 0 and 100 "are degenerate
puzzles that later pipeline stages (uniqueness, difficulty) will reject on
their own terms — they are not *invalid input*, which is all this module
judges." No later stage does any such thing, so the module has delegated a
rejection to a stage that does not perform it. FR-028 formalizes the
situation neutrally: one explicit rule must exist at the density-validation
seam, and under either resolution no later stage may reject on density
grounds and no module may claim that one does (AC-130). The requirement
carries both candidate criteria sets — AC-128/AC-133 for refusal,
AC-129/AC-134 for acceptance — exactly one of which survives this decision.

ADR-0003's ±3-point tolerance is also in play. It defines when a *drawn*
grid honours the *requested* density and says nothing about which requests
are legal, but its band is stated over the request range, so narrowing that
range changes the domain the band is applied over even though it changes no
constant.

## Decision

We will refuse density 0 and density 100 as `InvalidDensity` (the
`refuse_degenerate_density` alternative). The valid requested density becomes
1..99 inclusive: `MIN_DENSITY` moves to 1 and `MAX_DENSITY` to 99, and
`validate_density` raises before any grid is drawn, exactly as it already does
for 150%. The refusal lives at the one seam where every other out-of-range
request is refused (ADR-0010: domain validation inward of the CLI, never as an
argparse constraint), so it reaches the CLI through the same
`cli.exit_code_for` family as every other out-of-range request and needs no
new error class, no new exit code and no new place to look.

The reasoning is that an all-empty or all-filled grid carries no clue
information and is therefore not a puzzle. It passes the uniqueness check
only vacuously, and shipping it as an Easy puzzle makes every downstream
consumer — difficulty bands, book assembly, admin review — carry a degenerate
case forever. Refusing it in `validate_density` is the smallest honest fix:
one condition, one test, and an error message that tells the user what to do.
It also matches the intent the code already recorded — the misleading comment
was written on the assumption that these grids would be rejected somewhere —
and replaces that false claim with the rule itself rather than making the
rest of the pipeline honour the claim.

## Alternatives considered

### allow_degenerate_grids

Keep 0..100 and state explicitly — in FR-004, the `random_grid.py` docstring
and the CLI help — that the all-empty and all-filled grids are legal, uniquely
solvable Easy puzzles, pinned by AC-129 and AC-134. This is the zero-code
option: nothing that works today stops working, and it is consistent with
"the grid drives the picture" in the sense that a solid grid is a picture,
however dull. It was rejected because it turns a bug the review found into a
product feature: it ships a non-puzzle as an artefact (a blank or solid PDF
page with all-zero or full-length clues) and commits every present and future
consumer of a Puzzle to handling a case that no user asked for and no
difficulty scale can place meaningfully. It also contradicts both the review's
recommendation and the intent the code's own comment records — that these
grids were meant to be rejected. The saving is real but small (two pinning
tests versus one condition and two tests), and it buys a permanent liability.

## Consequences

### Positive

- The valid density range is one rule, stated in one place, and the code no
  longer claims that a stage which does not exist will do its work. AC-130's
  "verdict is made by `validate_density`" holds by construction.
- A non-puzzle can no longer enter the uniqueness, difficulty, export, batch
  or book pipelines; nothing downstream needs a special case for a grid with
  no clue information.
- The user gets the same shape of error, in the same exit-code family, for
  density 0 or 100 as for 150 — the message names the accepted range, so the
  fix is obvious.
- The batch generator and the web form get one consistent range to advertise
  instead of one that is technically accepted and practically useless at the
  ends.

### Negative

- An accepted input is narrowed. FR-004 / AC-011's "valid 0-100% range"
  wording becomes 1..99 (a follow-up edit in `requirements.yml`, not made
  here; AC-011's example value 150 stays outside both ranges, so the criterion
  itself is not invalidated). The CLI `--help` text for `--density`, the web
  form's numeric bounds and any admin batch preset must be audited for a
  literal 0 or 100 and brought in line — a request that used an extreme would
  otherwise start failing without warning.
- The boundary is a convention, not a cliff. Density 1 on a 10x10 grid rounds
  to a single filled cell, which is nearly as degenerate as density 0; the
  rule keeps *zero-information* grids out but does not promise that every
  accepted density yields an interesting puzzle. ADR-0003's tolerance still
  covers the rounding, not the meaning.
- `random_grid.py`'s comment at lines 78-84 and any test that pins 0 or 100
  as accepted must be rewritten, and AC-129 / AC-134 (the acceptance
  alternative's criteria) are retired from FR-028 without ever being
  implemented.

### Neutral

- `MIN_DENSITY` / `MAX_DENSITY` remain the single source of the range and
  are re-exported unchanged; callers that read the constants rather than
  restating them pick up 1..99 automatically. Migration is `rewrite` because
  the constants and the docstring must change together, and no stored data
  (exports, database rows, book PDFs) records a density outside 1..99 by
  construction — a puzzle generated at 0 or 100 before this ADR would still
  load, but nothing in the repository depends on one.
- `generate_batch`'s hardcoded density 50 is unaffected. The admin batch path
  and the web submission path both reach the same `validate_density` and gain
  the rule without code of their own.
- ADR-0003 is touched, not superseded: its ±3-point band and its constant are
  unchanged, and its History gains a note that the band now applies over
  requests in 1..99. ADR-0010 is unaffected — the refusal stays a domain
  function, not an argparse `choices=` or `type=` constraint.
- FR-028's `criteria_by_alternative` resolves to the refuse set: AC-128 and
  AC-133 survive, AC-130 continues to hold, AC-129 and AC-134 are dropped.
  This is what unblocks card cutting (`blocks: [decompose]` on DEC-034).

## Rules
```yaml
- id: ADR-0027/R1
  statement: The valid requested density for random generation is 1..99 inclusive. Density 0 and 100 are refused as InvalidDensity by validate_density before any grid is drawn; MIN_DENSITY and MAX_DENSITY are the only statement of that range.
  scope: {contexts: [CTX-001], code: ["src/nonogram/sourcing/random_grid.py"]}
  check: {kind: test, ref: TestGenerateRandom_RefusesDensityZeroAndHundred}
  severity: mandatory
- id: ADR-0027/R2
  statement: The verdict on a requested density is made only at the validate_density seam. No later pipeline stage (uniqueness, difficulty, export, batch) rejects a request on density grounds, and no module's documentation claims that one does.
  scope: {contexts: [CTX-001], code: ["src/nonogram/**"]}
  check: {kind: test, ref: TestGenerateRandom_DegenerateDensityVerdictIsMadeAtValidateDensitySeam}
  severity: mandatory
```

## References

- DEC-034 (resolved by this ADR)
- CTX-001 (Puzzle Creation)
- FR-028 (the density-ends rule; `criteria_by_alternative` resolves to the
  refuse set), FR-004 / AC-011 (density range; wording follow-up to 1..99)
- AC-128, AC-133 (surviving criteria), AC-130 (holds under every
  alternative), AC-129, AC-134 (retired)
- ADR-0003 (random-density tolerance; History note — band applies over 1..99)
- ADR-0010 (validation placement — the refusal stays inward of argparse)
- docs/GENERATION_ALGORITHM.md §10.2 finding 2 (the review that surfaced this)
- `src/nonogram/sourcing/random_grid.py` — `validate_density`,
  `MIN_DENSITY`, `MAX_DENSITY`, and the comment at lines 78-84 this ADR
  replaces

## History

- 2026-09-12: Created — refused density 0 and 100 as InvalidDensity at the
  validate_density seam (valid range 1..99), in favour of documenting the
  all-empty / all-filled grid as a legal Easy puzzle, because a grid with no
  clue information is not a puzzle and the code's own comment already
  promised a rejection that no stage performed.
