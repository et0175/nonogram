# CARD-056: Formalize an ADR/invariant for admin puzzle uniqueness and quality metrics

**Status:** ready
**Priority:** P3
**Category:** tech-debt
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/056-adr-admin-generation-guarantees
**Worktree:** —
**Source:** meta/review/20260910T170025Z.yml#F-009
**Idea:** —
**Wave:** —
**Depends on:** CARD-049, CARD-050
**Touches:** meta/architecture/decisions/adr/, meta/architecture/domain/aggregates.yml
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

`system_rules.py --scope 'src/nonogram/**'` returns 8 rules today, none of which
constrain `quality_score`, `recognizability`, or uniqueness verification outside
the `orchestrator.Puzzle` aggregate itself (`INV-002`, currently
`scope_unmapped_model` since `trace.yml` doesn't exist). Admin's generation
paths construct puzzle data as plain dicts, never instantiating
`orchestrator.Puzzle`, so even a resolved `INV-002` would not mechanically reach
them. This absence is the structural reason the bugs CARD-049/CARD-050 fix could
ship and persist without any system-contract check ever catching them — the
same pattern as CARD-048 from the previous review round, here for a
substantially more consequential area.

**This card depends on CARD-049 and CARD-050 landing first** — write the rule
against what the fixed behavior actually is, not against a still-hypothetical
fix.

1. Write a new ADR (or extend an existing one — `ADR-0013` difficulty-scoring or
   a new one, implementer's judgment) with a `## Rules` block stating, in the
   project's existing rule-YAML format (see `ADR-0022`'s `## Rules` section for
   the exact shape):
   - A rule that every puzzle stored via `puzzle_review.add_puzzle` must have
     passed a solver-verified uniqueness check, scoped to cover
     `src/nonogram/admin/**` (not just `orchestrator.py`/`sourcing/**` the way
     `ADR-0022/R4` is scoped today).
   - A rule stating what `quality_score`/`recognizability` are actually defined
     as post-CARD-050 (real measurement for image mode; whatever CARD-050 chose
     for random mode — a real metric or explicit `None`), scoped similarly.
2. If `trace.yml` still doesn't exist by the time this card runs, note in the
   ADR's own text that the rule is declared but not yet mechanically checkable
   until synthesis reaches this component — same honesty `ADR-0022/R3`/`R4`
   already model for their own scope gaps (see the previous review's CARD-048).

## Acceptance criteria

- **AC-1** — given the ADR is written, when
  `system_rules.py --root meta/architecture --scope 'src/nonogram/admin/**'` is
  run, then the new rule(s) appear in the matched set.
- **AC-2** — the ADR's stated rules match what CARD-049/CARD-050 actually
  implemented (not what was originally proposed, if the implementation diverged
  during those cards).

## Engineering constraints

None — documentation-only change to the architecture model, no production code
touched.
