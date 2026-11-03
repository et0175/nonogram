# CARD-341: A comment inside a card's parsed field is read as part of the value, and nothing says so

**Status:** ready
**Priority:** P2
**Category:** tech-debt
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** general-purpose
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** CARD-338 fix round 2, 2026-11-03. Cycle 2 reported a stale clause in `CARD-322.md`'s `Touches:` comment as a prose-retraction miss. The fix round measured it and found the premise understated: the comment is not metadata *beside* the value, it is *inside* it.
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** tests/test_suite_profile.py, meta/kanban/cards/
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

`parse_card_fields` strips no HTML comment, and `extract_touches` splits the value on
**commas**. So an inline `<!-- … -->` written on a `Touches:` line is parsed as part of the
field: the comment's fragments become "globs", and — the part that does damage — **the last
real path is concatenated with the comment's opening and stops matching itself.**

Measured on `CARD-322.md` by CARD-338's fix round: **15 "globs" instead of 8**, seven of them
prose fragments, and `compute_excess` reported a declared ADR path as **excess although the
field declares it** — on a card whose own work edits that file.

**This is not one card's typo.** Measured across the board 2026-11-03:

| | count |
|---|---|
| cards with `<!--` inside the parsed `Touches:` value | **21** |
| of those, not `done`/`skipped` | **3** — CARD-273, CARD-322, CARD-339 |
| cards with `<!--` inside the parsed `Wave:` value | **17** |
| of those, `ready` (the only status `compute_poached` considers) | **0** |

All three live ones were damaged in the same way and have been repaired by hand:
`CARD-339` parsed to **4 real paths out of 7** (the orchestrator's own card, written hours
after the lesson that produced it), and `CARD-273`'s eaten glob was **`tests/**`** — a card
declaring the whole test tree, with that declaration corrupted. `CARD-322`'s repair rides
CARD-338's branch.

The `Wave:` instances are **inert today** rather than safe: that field is compared by
**equality**, which is more brittle than a comma split, and nothing but the current statuses
keeps it harmless.

## Why hand-repair is the wrong fix

Twenty-one bodies were repaired or are repairable one at a time, and **nothing stops the
twenty-second.** The convention that produced them is a good one — a field that needs
justification should carry it — so the answer is not "stop writing comments" but "make the
machine and the convention agree".

Two places could hold the durable fix:

- **The parser**, in `forge_1` — which **this board never edits**, so it is reportable, not
  available here.
- **A lint cell on this board**, which is available and is what this card builds.

## What to implement

1. **A guard that reds when any card's parsed field carries an inline comment.** Derive the
   field set rather than listing it — every `**Name:**` header line a card carries, not just
   `Touches:` and `Wave:`, because the parser strips comments from none of them.
2. **Report the consequence, not just the presence.** For `Touches:`, say how many globs the
   comma split yields against how many are real paths, and name the path that got
   concatenated — that is the number a reader must act on.
3. **Prove it discriminates**, in both directions: a card with a comment on its own line
   passes, the same card with the comment moved onto the field reds, and the message names
   the card and the field.
4. **Decide what to do about the existing `done` cards and say why.** They are historical
   records; this board does not retract those (the same reasoning that keeps CARD-304's
   one-place guard scoped to `config.yml` rather than the tree). A guard that reds on 18
   closed cards is a guard nobody can keep green — so either scope it to non-terminal
   statuses, or baseline the closed set, and **state which and why** rather than picking one
   silently.

## Acceptance criteria

- **AC-1** — Given every card file, when each parsed field is read, then any field whose value
  contains `<!--` is reported with its card, its field name, and for `Touches:` the real-paths
  versus comma-split counts.
  `check: {kind: test}`
- **AC-2** — Given a card with its comment on its own line, when the guard runs, then it
  passes; and given the same comment moved onto the field line, then it **reds**, naming the
  card and field. Both directions demonstrated by a measured plant and restore.
  `check: {kind: test}`
- **AC-3** — Given the terminal-status cards, when the guard's scope is chosen, then the
  choice is recorded with its reason, and the guard is green on the tree as it stands.
  `check: {kind: test}`

## Guardrails

- **G-1** — `src/` is not touched. This is a lint cell over `meta/kanban/cards/`.
- **G-2** — **Do not rewrite twenty-one card bodies.** The three live ones are already
  repaired; the terminal ones are records. If the guard's scope forces a body edit, the scope
  is wrong.
- **G-3** — `/Users/omelnikova/MyProjects/forge_1` is read-only. The parser's behaviour is the
  fact this card works around, not something to change.
- **G-4** — Do not write a check ref into a tracked file where it could pass for a `def`/`class`
  line; this guard reads card files, which is the resolver's own hazard area (CARD-335).

## Notes

**The generalisation worth keeping**, and the reason this got three passes deep before anyone
saw it: a prose section is what a **reader** scans, so a contradiction there gets noticed. A
field is what a **program** reads — so a stale or malformed value there can do damage while
looking like bookkeeping, and it is invisible to exactly the review technique that catches
everything else.
