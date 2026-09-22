# ADR-0034: A new book starts with a plan of 150 puzzles at 40/40/20

**Status:** Accepted
**Date:** 2026-09-22
**Deciders:** Puzzle Creator (project owner)
**Revised:** —
**Migration:** —
**Pattern:** —
**API-Posture:** —

## Context

FR-034 gives every book a stored distribution plan (TERM-029): a total puzzle count, an easy / medium / hard split that sums to 100% (INV-005), and a per-longest-side plan over the buckets ≤15, 16–20, 21–25 and 26–30, prefilled from the Book 1 size × difficulty matrix rescaled to the count and split. FR-035 needs the value a new book starts with before the owner enters anything on Print setup. POL-007 then re-derives the per-bucket plan when the split changes, unless a cell was edited by hand.

Three sources disagree. The owner's UI requirements (BK-UI-1) ask for 150 puzzles at 40% easy / 40% medium / 20% hard, and their worked per-bucket table (≤15: 20/7/0, 16–20: 30/27/6, 21–25: 10/20/12, 26–30: 0/6/12) is computed for that split. The Book 1 research matrix sums to 30/45/25 ("mixed book"). The research also names 40/40/20 as the beginner profile and 30/45/25 as the enthusiast profile, which suggests deriving the default from the book's audience. But the audience is a free-text column today (`target_audience`, values such as "seniors" and "general"), not an enumeration.

## Decision

We will start every new book with a plan of 150 puzzles at 40/40/20 (60 / 60 / 30), with the per-bucket plan prefilled from the Book 1 matrix rescaled to that split, as in BK-UI-1's worked table. Every value stays editable on Print setup. This is the owner's explicit BK-UI-1 value, and it needs no schema change. An audience-driven default can be added later on top of it: 40/40/20 would then become the "beginner" entry in that mapping, not a value this ADR would have to undo.

## Alternatives considered

### 150 at the research mix, 30/45/25
The prefill would be the research matrix itself, with no rescaling or rounding for the default. Rejected: it contradicts the owner's explicit BK-UI-1 default and the worked table built on it. A mixed book is still one edit away on Print setup.

### Derived from the book's audience
The audience field would become an enumeration (e.g. beginner, enthusiast), each value mapped to a stored default split, and a new book's plan would be prefilled from its audience. Rejected for now: it needs a migration from free-text audience to an enum, a mapping for existing values, and a POL-007-style rule for changing the audience after planning. The owner has also not confirmed the audience list or the mapping, so the option isn't concrete yet. It stays open as a later extension.

## Consequences

### Positive
- The default is exactly what the owner asked for, and BK-UI-1's worked table serves as ready-made acceptance data (AC-205).
- No migration: audience stays free text, and the default is a constant of book creation.
- An audience mapping can be added later without changing this default's behaviour for beginner books.

### Negative
- A book meant for experienced solvers starts easy-heavy, so the owner has to re-plan it by hand on Print setup each time.
- The per-bucket prefill needs rescaling and rounding even for the default (FR-034's largest-remainder rule), so the default table is derived, not copied verbatim from the research matrix.

### Neutral
- FR-035's alternative-tagged criteria resolve: AC-204 (holds under every alternative) and AC-205 stay. AC-206 (30/45/25) and AC-207 (derived from audience) are retired unimplemented, following the FR-004 / ADR-0027 precedent.
- A later "audience sets the default" requirement would come in as a raw-requirements delta and a revision of this ADR.

## References

- DEC-036 (resolved by this ADR)
- CTX-001; AGG-002 Book (INV-005), POL-007, TERM-029
- FR-034, FR-035 (AC-204, AC-205; AC-206, AC-207 retired)
- docs/book_generation_req/book_admin_ui_requirements.md (BK-UI-1, BK-UI-2); docs/research/book-format-research.md §8
- ADR-0033 (Book assembly stays in CTX-001)

## History

- 2026-09-22: Created — new books default to 150 puzzles at 40/40/20 with the rescaled per-bucket prefill, per the owner's BK-UI-1; audience-driven defaults deferred.
