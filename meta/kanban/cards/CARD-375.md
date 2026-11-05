# CARD-375: One `*_test` database is created per worktree and nothing ever removes them — 67 on this host, one of which has a live worktree

**Status:** ready
**Priority:** P3
**Category:** ops
**Estimate:** 1c (0.5d)
**Complexity:** standard
**Revision pending:** false
**Skill:** general-purpose
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** CARD-349's round, 2026-11-04, which re-derived the count at 66 as a residue of its own change and declined to widen scope. The orchestrator measured **67** immediately after — the difference being the round's own run, exactly as it disclosed.
**Idea:** —
**Wave:** —
**Created wave:** 78
**Deferred waves:** 0
**Depends on:** CARD-349
**Touches:** scripts/, tests/
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## RE-SCOPED 2026-11-05 under the owner's cut bar — it stays a card, and here is why

Trimmed from six acceptance criteria to four. **It remains a card for one reason: the fix executes
`DROP DATABASE`.** The simplest shape — "the tidy rule drops the database when it removes the
worktree" — would make it a convention, and a convention that runs `DROP DATABASE` by hand is
exactly where a mistake reaches `nonogram_poc`. **The safety proof has to be code, with a test that
can fail.** That is the arm of the cut bar this clears.

## The accumulation, measured

CARD-244 derives a **per-worktree** test database name, which is what makes concurrent cards safe.
`_ensure_test_database` creates one on demand. **Nothing has ever removed one.**

Measured on this host with the Postgres.app client: **67** databases matching `%_test`, of which
exactly **one** has a worktree that still exists. The rest name worktrees removed under the standing
tidy rule — which removes the directory and leaves the database. So the asymmetry is in the rule,
not in anyone's discipline.

Nothing is broken today: each is small (`nonogram_poc`, for scale, is ~8.4 MB) and none is reachable
by the suite. It is on the board because the set **grows monotonically with no counterpart that
shrinks it**, and because a name that gets *reused* by a new worktree hashing to the same value would
inherit a schema nobody migrated — the stale-schema hazard CARD-348's gate met at `alembic_version`
017 against head 018.

## Acceptance criteria

- **AC-1** — A reaper removes a `*_test` database **only** when no worktree resolves to its name. The
  live set is **derived** from `git worktree list` through `db_name.derive_test_database_name`, never
  by pattern-matching the database list. **Deny-default (ADR-0039/R2): a name it cannot attribute is
  KEPT, not dropped.** Say where it runs — the tidy site or a sweep — and why; prefer the tidy site,
  since that is where the asymmetry is and a sweep must re-derive what the tidy step already knows.
- **AC-2** — Every drop is proved safe **in code** before it is issued, on all four properties: the
  name ends in `_test`, `_refusal_reason` allows it, it matches `_CREATABLE_NAME`, and it is neither
  `nonogram_poc` nor `nonogram_test`. **No wildcard or pattern-matched drop anywhere.**
- **AC-3** — A plant proves the deny-default: an unattributable name **survives** the reaper, and the
  matched control (an attributable dead name) is removed. Both in the same run — a reaper that only
  ever keeps is as useless as one that only ever drops.
- **AC-4** — **G-8 absolute: `nonogram_poc` is the live panel's.** Never connect to it, never list by
  connecting to it, never drop it. Existence checks go through the `postgres` maintenance database.
  State what was verified about it, as CARD-349's round did — size unchanged and zero connections at
  both ends.

## Two notes, not criteria

- **Re-derive the 67**; it moves. CARD-349's round measured 66 and the orchestrator measured 67 an
  hour later, the difference being that round's own armed run creating one — exactly as it disclosed.
- **Use the Postgres.app client by absolute path**
  (`/Applications/Postgres.app/Contents/Versions/latest/bin/psql`). The `psql` on `PATH` is Homebrew
  **15.19** against an **18.1** server, so `psql -lqt` fails with `column d.daticulocale does not
  exist` — the connection succeeds and only the listing query fails, and with stderr suppressed that
  reads as "no server". That instrument failure has already cost one card's gates their armed arm.

## Worktree notes

(none yet)
