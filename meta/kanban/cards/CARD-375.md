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
**Touches:** tests/db_name.py, scripts/
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## The accumulation

CARD-244 derives a **per-worktree** test database name, so each worktree gets its own — which is
what makes concurrent cards safe. `_ensure_test_database` creates it on demand. **Nothing has ever
removed one.**

Measured on this host with the Postgres.app client: **67** databases matching `%_test`. Exactly
**one** corresponds to a worktree that currently exists. The rest name worktrees removed under the
standing tidy rule — which removes the directory and leaves the database.

**CARD-349 widens the reach slightly and says so.** Before it, an armed run touching only unmarked
tests created nothing (and red). Now it creates one. So strictly more worktrees end up with a
database — but those runs were broken before, so that is the fix rather than a regression, and the
count **per worktree** is still exactly one either way.

## Why P3 and not lower

Each is small (`nonogram_poc`, for contrast, is ~8.4 MB) and none is reachable by the suite, so
nothing is broken today. It is on the board because:

- it is a **monotonically growing** resource with no counterpart that shrinks it, which is the shape
  that eventually breaks something far from its cause
- a stale database is exactly the **stale-schema hazard** CARD-348's gate met (`alembic_version` 017
  against head 018): a name that gets *reused* by a new worktree hashing to the same value would
  inherit a schema nobody migrated
- the tidy rule already removes the worktree, so the asymmetry is in the rule, not in anyone's
  discipline

## Acceptance criteria

- **AC-1** — A reaper removes a `*_test` database **only** when no worktree resolves to its name.
  The set of live names is **derived** from `git worktree list` through
  `db_name.derive_test_database_name`, never from a pattern over the database list
  (ADR-0039/R2, defaulting to deny: a name it cannot attribute is **kept**, not dropped).
- **AC-2** — Every drop is proved safe first, on the four properties CARD-349's round used: the name
  ends in `_test`, `_refusal_reason` allows it, it matches `_CREATABLE_NAME`, and it is neither
  `nonogram_poc` nor `nonogram_test`. **No wildcard or pattern-matched drop anywhere.**
- **AC-3** — **G-8 holds absolutely: `nonogram_poc` is the live panel's and must never be connected
  to, listed-by-connecting, or dropped.** Existence checks go through the `postgres` maintenance
  database. State what was verified about it.
- **AC-4** — A plant proves the deny-default: a database whose name cannot be attributed to any
  worktree **survives** the reaper, and the matched control (an attributable dead name) is removed.
- **AC-5** — Decide whether the reaper runs at the tidy rule's site (worktree removal) or as a
  standalone sweep, and give the reason. **Prefer the tidy site**: that is where the asymmetry is, and
  a sweep has to re-derive what the tidy step already knows.
- **AC-6** — Re-derive the 67 rather than carrying it, and use the **Postgres.app** client by absolute
  path, not the one on `PATH` (a 15 client cannot list an 18 server: `psql -lqt` fails with
  `column d.daticulocale does not exist`, and with stderr suppressed that reads as "no server").

## Worktree notes

(none yet)
