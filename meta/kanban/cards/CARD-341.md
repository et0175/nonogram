# CARD-341: A comment inside a card's parsed field is read as part of the value, and nothing says so

**Status:** skipped
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
**Review score:** n/a — **RETIRED** on the owner's 2026-11-09 tech-debt triage. No work is owed here.
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

**This is not one card's typo, and it is not confined to `Touches`.** Re-measured
2026-11-03 after CARD-332's gate refuted a narrower sweep of mine:

| | count |
|---|---|
| cards with a comment inside **some** parsed field | **45** |
| distinct fields affected | **11** |
| `Touches` / `Wave` / `Depends on` / `Estimate` / others | 19 / 16 / 13 / 8 / 10 |

**The severity is per-CONSUMER, not per-field, and that is the finding.** Measured against
the real consumers rather than assumed:

- **`Touches` is genuinely broken.** `card_lint.extract_touches` is a plain
  `value.split(",")` with **no comment stripping**, so fragments become globs and the last
  real path is welded to the comment's opening. CARD-332's gate measured **28 "globs" where
  15 are declared**, and quantified the live harm on CARD-322 (`ready`, the status
  `compute_poached` reads): its denominator becomes 15 instead of 8, so a partial poach of
  3-of-8 files scores **0.20 against a 0.3 threshold** where honestly it is 0.375 — **a
  partial poach silently hidden**.
- **`Depends on` survives corruption but INVENTS EDGES.** Its consumer scans the value for
  `CARD-\d+` tokens rather than splitting, so a comment cannot break it — but **every card id
  named inside the comment becomes a dependency**. Measured: **10 cards gained phantom edges,
  8 of them `ready`**.
- **`Revision pending` has no programmatic consumer found** — it appears only in
  `card_lint`'s field-name list, so the gate it controls is applied by an agent reading the
  card, which reads `true <!-- … -->` correctly. Benign today, and benign *by luck* rather
  than by design.

### The live harm this already caused, and the instrument that hid it

The phantom edges put a **cycle** in the board's dependency graph: CARD-336's comment named
CARD-337, and **CARD-337 really depends on CARD-336**. Measured over all 340 cards:

| reading | result |
|---|---|
| comment-stripped (the orchestrator's own Kahn script) | 340 ordered, **no cycle** |
| token-scan (what the consumer actually does) | **324 ordered, 16 unordered — CYCLE** |

**Every "Kahn clean, no cycle" reported during wave 73 was measured with the stripping
script**, so the instrument was more forgiving than the consumer and hid the defect for the
whole wave. That is the transferable lesson and it is worth more than the repair: **an
instrument more permissive than the consumer reports health the consumer will not see.**

Repaired by hand on `main`: the three live `Touches` cases, and the **eight `ready` cards**
whose `Depends on` produced phantom edges. Both readings now agree at 340/340, no cycle.
Still outstanding: the `done` cards (records, deliberately untouched) and CARD-322's
`Touches`, whose repair rides CARD-338's unmerged branch.

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

## RETIRED 2026-11-09 — tech-debt triage

A guard over the test tooling, not the book or the player; under the owner's rule (keep a test only if its claim is a live product decision) it is not worth building.
