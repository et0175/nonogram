# CARD-378: Two actors in one worktree derive the SAME test database, and the schema rebuild is destructive — CARD-244's hazard reappears inside a checkout

**Status:** ready
**Priority:** P1
**Category:** enabler
**Estimate:** 1c (0.5d)
**Complexity:** standard
**Revision pending:** false
**Skill:** general-purpose
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** Measured 2026-11-05 during CARD-349's review. Cross-worktree isolation is intact and was verified; the failure is specifically two actors inside one worktree.
**Idea:** —
**Wave:** —
**Created wave:** 78
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/db_name.py, tests/conftest.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## The mechanism, measured

`db_name.derive_test_database_name` is a **pure function of the resolved repo root**. Verified:

| worktree | derived database |
|---|---|
| `PythonProject4` | `nonogram_pythonproject4_543f9f3f05e1_test` |
| `PythonProject4-card-349` | `nonogram_pythonproject4_card_349_34c3628d36d8_test` |

**Cross-worktree isolation is intact — that is CARD-244 working.** The defect is that *every process
in one worktree* names the **same** database, and `_test_database_tables` is not a read: it runs
`DROP SCHEMA public CASCADE`, `CREATE SCHEMA`, `alembic upgrade head`, plus a per-test `TRUNCATE`.

So two actors in one checkout do not merely contend — **each erases the other's schema mid-run.**
That is CARD-244's own stated hazard, word for word: *"each erased the other's schema mid-run, and
the suite's verdict became a property of what a sibling card happened to be doing."* CARD-244 fixed
it between worktrees; the board then started running two actors per worktree and it came back.

## Why it is worse than contention

**The red it produces is a missing-table error** — and that is a signature this board already has two
cards arguing about (CARD-349's hazard A/B, CARD-258's unexplained waves 47/48/50). A suite whose
schema was dropped under it fails in a way that looks exactly like a genuine defect in whatever diff
is under review. Measured consequence from CARD-349's review: the errors all name the fixture that
requested the schema, so the sibling's interference reads as the card's fix being broken.

**It self-heals**, like both of CARD-349's hazards: by the time anyone re-runs, the schema is back.
First run red, second green, cause invisible.

## Acceptance criteria

- **AC-1** — Two concurrent runs in one worktree cannot destroy each other's schema. Either the
  derived name includes something that distinguishes actors, or the destructive rebuild is serialised
  against actors in the same worktree. **Measure the cost of each before choosing** — a per-actor
  database multiplies an already-unreaped set (CARD-375: 67 on this host).
- **AC-2** — A plant proves it: run the destructive rebuild as one actor while a second actor in the
  same worktree holds a transaction, and assert the named outcome rather than a missing-table red.
  Restore from captured content.
- **AC-3** — The failure must be **attributable at the point of failure**, not diagnosable only by
  someone who already suspects it. A missing-table error caused by a sibling must not be
  indistinguishable from one caused by the diff — this is the whole reason the card is P1.
- **AC-4** — **G-8: `nonogram_poc` is the live panel's and must never be connected to, listed by
  connecting, or dropped.** Existence checks go through the `postgres` maintenance database. Every
  drop proved safe first on four properties: ends in `_test`, allowed by `_refusal_reason`, matches
  `_CREATABLE_NAME`, is neither `nonogram_poc` nor `nonogram_test`. No wildcard drop, ever.
- **AC-5** — Use the **Postgres.app** client by absolute path. The `psql` on `PATH` is Homebrew 15.19
  against an 18.1 server, so `psql -lqt` fails with `column d.daticulocale does not exist`; with
  stderr suppressed that reads as "no server" and has already cost one gate its armed arm.
- **AC-6** — Decide jointly with **CARD-377** whether the answer to both is simply **one actor per
  worktree**. If so, say that plainly and close the cheaper of the two.

## Worktree notes

(none yet)
