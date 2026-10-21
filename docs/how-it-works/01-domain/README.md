# 01 — domain · what the system knows

The reader-centric group holding everything this system reasons about. It has one
aspect, because the system has one bounded context.

| Aspect | Context | Covers |
|---|---|---|
| [puzzle-creation/](puzzle-creation/) | **CTX-001 Puzzle Creation** | the whole pipeline — sourcing, clue derivation, uniqueness verification and recovery, difficulty calibration, export — plus book assembly, the puzzle player, the three inbound adapters and the one database |

## Why this group has one aspect, and the others do not exist

The skill's default group set is `domain` · `integrations` · `surface-api` ·
`operations`. Only `domain` is populated here, and that is a fact about the system
rather than a shortcut:

- **`integrations` would be empty.** `meta/architecture/domain/external_systems.yml`
  is `external_systems: []`, and `c4/context.puml` records that this is still
  correct after the admin panel landed: the Postgres database "is NOT an EXT-XXX —
  it is the system's own store, owned and migrated by this repository". The local
  filesystem is drawn as a boundary element "for readability only — per
  `external_systems.yml` it is infrastructure, NOT an EXT-XXX". Amazon KDP is a
  **print specification the book PDF meets** (CON-018), not an integration.
- **`surface-api` would duplicate, not separate.** The three inbound adapters are
  not an independently-evolving surface: ADR-0019 makes the web UI a *sibling* of
  the CLI inside one process, and the admin panel imports the same package into its
  own. All three are components of CTX-001 and the `ast` import guard treats them
  as one rank. Splitting them into a second aspect would cut one context in half,
  which the skill's "one aspect per bounded context" rule forbids and which the
  model does not support. They are
  [file 09](puzzle-creation/09-the-three-inbound-adapters.md) inside this aspect.
- **`operations` would be a perspective, not an aspect.** There is one deployed
  service, one database and one `start.sh`. What an operator needs is the
  *operational reading* of this same ground truth, which is exactly what
  [`perspectives/sre.md`](puzzle-creation/perspectives/sre.md) is for. A separate
  group would have had to restate the admin panel's mechanism to say anything at
  all.

A group with nothing real in it is not created here, so the numbering starts and
stops at `01`.

## Reading order

1. [01 — the layered pipeline](puzzle-creation/01-the-layered-pipeline.md) — the
   direction of every arrow in the system, and the `ast` walk that enforces it.
   Everything else assumes it.
2. Then either follow the pipeline in order
   ([02](puzzle-creation/02-sourcing-a-solution-grid.md) →
   [03](puzzle-creation/03-deriving-clues.md) →
   [04](puzzle-creation/04-uniqueness-and-recovery.md) →
   [05](puzzle-creation/05-difficulty-calibration.md) →
   [06](puzzle-creation/06-exporting-a-finished-puzzle.md)), or jump to the
   surface you are working on
   ([09](puzzle-creation/09-the-three-inbound-adapters.md)) or the book
   ([07](puzzle-creation/07-book-assembly-and-the-admin-panel.md)).
3. Per-role routes are in [the root README](../README.md).

Up one level: [the root overview](../README.md).
