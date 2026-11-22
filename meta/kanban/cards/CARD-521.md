# CARD-521: tests/README.md describes the suite as it is today

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/521-tests-readme
**Worktree:** ../PythonProject4-card-521
**Source:** roadmap wave 11, cut 2026-11-22 on the owner's "start the no-decision wave 11". IDEA-002.
**Idea:** IDEA-002
**Wave:** 90
**Created wave:** 90
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/README.md
**UI surface:** —
**Review score:** —
**Started:** 2026-11-22T11:26Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

IDEA-002: `tests/README.md` is still titled "Admin Panel Test Suite - Wave 1", and its opening sections (test file list, running, markers, fixtures, CI, coverage, troubleshooting, next steps) describe the suite of about 80 waves ago. Its later sections are current and are read by tests: the profiling-run section and the kill-matrix section, which CARD-516, CARD-315 and CARD-518 edited. The idea's other half, per-directory READMEs under `src/`, is closed without a change: CLAUDE.md already names `src/nonogram/__init__.py`'s docstring as the one component map, and a second map is what drifted before (CARD-261).

## What to implement

Re-verify first: which tests read `tests/README.md`, and which passages they hold (find them by `ast`/import, not text search). Then rewrite the stale sections to match the suite today: how to run it (the Makefile targets and the commands in CLAUDE.md), the markers actually registered, the fixtures and helpers that actually exist, the database arming and the per-worktree `*_test` database, the full-suite lock, and the expected skip reasons. Keep every passage a test reads, word for word unless the test is changed with it. Shorter is better: link to CLAUDE.md and the code instead of restating them.

## Acceptance criteria

* **AC-1**: the title and every section above the profiling section describe today's suite; every command, marker, fixture, file and path the README names exists (each checked, listed in the notes).
* **AC-2**: every test that reads tests/README.md still passes, run by node id; name them.
* **AC-3**: no figure is carried from memory: any count or time written is derived now, with how it was derived.
* **AC-4**: no code or test changes, unless a test that reads the README must follow a moved passage (name it). Net test count 0.

## Guardrails

* **G-1**: the profiling and kill-matrix sections keep their content; only their position or headings may change.
* **G-2**: no database URL, host or credential is written into the README; describe how to arm, not with what.

## Worktree notes
