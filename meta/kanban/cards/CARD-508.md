# CARD-508: Test-database hygiene: concurrent runs, the schema-once test run alone, engine globals restored, the connect-timeout flake

**Status:** ready
**Priority:** P3
**Category:** tech-debt
**Estimate:** 2c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/508-test-db-hygiene
**Worktree:** —
**Source:** roadmap wave 7 (cut 2026-11-20 on the owner's "go with option 2, start wave 7"). IDEA-031 (WSJF 3.33), IDEA-032, IDEA-140, IDEA-174 (1.92 each): the faults most likely to red a merge gate for no code reason. Two are marked unverified/partly in the backlog; expect some to be closed already.
**Idea:** IDEA-031, IDEA-032, IDEA-140, IDEA-174
**Wave:** 86
**Created wave:** 86
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/conftest.py, tests/test_card_156_db_fixture.py, tests/test_db_connect_timeout.py, tests/test_db_*.py
**UI surface:** —
**Review score:** —
**Blocked by:** —

## Why this card exists

1. **IDEA-031 (CARD-156 F-005).** Two test runs at once share one test database, and the per-session `DROP SCHEMA public` wipes the other run's schema mid-flight. Triage 2026-11-18: "partly"; the per-worktree `*_test` database resolution (CARD-378 family) separates runs in different worktrees; the remaining case, two runs in the SAME worktree (or two worktrees resolving the same name), was considered and skipped as CARD-378. Only the full-suite lock covers it.
2. **IDEA-032 (CARD-156 F-006).** The second `TestDbFixture_SchemaIsBuiltOncePerSession` test fails by design when run alone (`-k`, node id, `--lf`), because it compares against state the first records. Unverified.
3. **IDEA-140 (CARD-178 F-001/F-003).** Tests that reset `db.session`'s engine do not restore the module globals (`engine`, `SessionLocal`, `_engine_url`); CARD-252/254 added a guard. Not established whether the guard makes an autouse snapshot fixture unnecessary.
4. **IDEA-174.** tests/test_db_connect_timeout.py reported `1 error` once under host contention (2026-10-18), never reproduced since.

## What to implement

Re-verify each against main first, armed at this worktree's own `*_test` database where the item needs a database; drop any already closed with one line and its evidence.

1. IDEA-031: if two armed runs in one worktree can still wipe each other, make the session schema build safe against it (a session-level `pg_advisory_lock` around the build/drop, or refusing a second concurrent run with a clear message). Prove it with two concurrent armed runs of a small db_required selection. If the remaining case is not reachable, record why.
2. IDEA-032: make the second test self-contained (run it alone by node id: green), without weakening what the pair asserts together.
3. IDEA-140: decide by measurement whether the existing guard already restores or detects the globals (plant a test that resets the engine without restoring, see whether anything reds). Fix only if nothing catches it.
4. IDEA-174: try to reproduce under load (e.g. the DB file set in parallel with a CPU hog); if it does not reproduce in a stated number of runs, record that and drop it. If it does, widen the timing margin with its reason.

## Acceptance criteria

* **AC-1**: each item fixed with a control that reds, or dropped with its measured evidence.
* **AC-2**: unarmed, the full db_required set still skips with "DATABASE_URL is not set" (29); armed at this worktree's `_test` database, it passes with 0 skips. Report both with `-rfs`.
* **AC-3**: net test count at most +1; report it.

## Guardrails

* **G-1**: tests/conftest.py is a gate-wide file: the merge gate runs the full suite. Report skip counts and reasons with `-rfs`.
* **G-2**: never connect to the production database; armed runs use only this worktree's own `*_test` database on localhost. Never DROP anything that does not end in `_test`.

## Worktree notes
