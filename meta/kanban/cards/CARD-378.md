# CARD-378: Two actors in one worktree derive the SAME test database, and the schema rebuild is destructive — CARD-244's hazard reappears inside a checkout

**Status:** skipped
**Priority:** P1 <!-- was the priority when cut; the card is retired, not deprioritised -->
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
**Review score:** n/a — **RETIRED into CARD-377** on 2026-11-05 under the owner's cut bar. No work was done and none is owed.
**Started:** —
**Closed:** 2026-11-05
**Actual:** none — retired before any work, superseded by a convention.
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

## RETIRED 2026-11-05 — closed by a convention the owner had already adopted

**This card was obsolete before it was committed, and that is the finding.**

Its premise is correct and measured: `derive_test_database_name` is a pure function of the resolved
repo root, so every process in one worktree names the **same** database, while
`_test_database_tables` runs `DROP SCHEMA public CASCADE` → `CREATE SCHEMA` → `alembic upgrade head`.
Two actors in one checkout therefore erase each other's schema mid-run — CARD-244's hazard verbatim,
returning inside a worktree because CARD-244 isolated worktrees and the board then began running two
actors per worktree. Cross-worktree isolation was verified intact (`…_543f9f3f05e1_test` for main
against `…_card_349_34c3628d36d8_test` for the card worktree).

**It is retired because the owner closed the cause, not the symptom.** Instructions for card work now
route through the orchestrator, therefore **one actor per worktree**, therefore no two actors to
collide. Building a per-actor database naming scheme would have been the expensive answer to a
question already settled — and worse, it would have multiplied an already-unreaped set (CARD-375:
**67** `*_test` databases on this host, one of which has a live worktree).

**Why this retirement is on the record rather than a deletion.** The owner measured the board's card
spawn ratio at up to **7× against one card closed per wave** and named the mechanism: every finding
became a card. This card and CARD-377 were cut **P1, as a pair, for a hazard the owner had closed by
convention while I was writing them.** A card can be obsolete before it is committed, and that is a
sharper instance of the spawn problem than CARD-376's over-ceremony — there the card was merely too
big for its fix; here the card was answering a question that no longer existed.

**What survives, and where:** the measured mechanism is preserved in CARD-377's re-scoped body as the
reason the convention is load-bearing, and the one piece of residue the convention does **not** close
— that the same-worktree pass-through is **silent**, so the convention has no control that can fail —
is CARD-377's AC-1 and AC-2. Nothing measured here is lost; only the card is.
