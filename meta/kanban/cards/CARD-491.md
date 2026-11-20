# CARD-491: The registry and two docs catch up: the panel's memory cap as an NFR, Tier's member count, and the scripts README

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/491-registry-docs
**Worktree:** ../PythonProject4-card-491
**Source:** roadmap rescore 2026-11-18, wave 4 (cut 2026-11-20; premises re-read against main the same day). IDEA-009 WSJF 3.59 (shrunk at the cut: CARD-145/237 already built the checks, only the NFR is missing), IDEA-029 WSJF 3.08, IDEA-081 WSJF 3.08.
**Idea:** IDEA-009, IDEA-029, IDEA-081
**Wave:** 83
**Created wave:** 83
**Deferred waves:** 0
**Depends on:** —
**Touches:** meta/architecture/requirements.yml, tests/test_difficulty_tiers.py, scripts/README.md, docs/deploy/render.md
**UI surface:** —
**Review score:** —
**Started:** 2026-11-20T01:49Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

1. **IDEA-009.** The deployed panel's 512 MB limit is in no NFR. The checks exist (tests/test_book_pdf_memory.py, CARD-145 and CARD-237: live page-bitmap bytes, the capped real-book export, the memory guards), so the export cannot quietly break the cap, but the registry names no requirement they verify.
2. **IDEA-029.** requirements.yml's Tier `enum_note` says ADR-0025 fixes `guess` "as the fourth member" and that `difficulty.Tier` has "four members"; tests/test_difficulty_tiers.py narrates ADR-0025 in comments. Re-read what Tier has today and correct both to it.
3. **IDEA-081 (CARD-168 F-001..F-003).** scripts/README.md "Manual Commands" defaults DATABASE_URL to `nonogram_poc` and runs `pytest tests/test_wave1_*.py …` (check those files exist); render.md's env table omits `PYTHONUNBUFFERED` (set in render.yaml, which the service ignores — memory: Render is dashboard-managed); the 2026-09-23 incident evidence render.md cites.

## What to implement

1. One NFR for the panel's memory cap whose `check:` names existing tests in tests/test_book_pdf_memory.py, by name, each confirmed as a `def`/`class` by `ast` (never a text hit). No new test.
2. The enum_note and the test comments state Tier's real members, read from code.
3. The Manual Commands block uses the test database the suite accepts and names test files that exist; render.md's table gains PYTHONUNBUFFERED with a line that render.yaml is not what the service runs; F-003 settled one way or the other in the notes.

## Acceptance criteria

* **AC-1**: the new NFR's check ref resolves (tests/test_check_ref_resolution.py green; any frozen census it holds re-derived as sets, not pasted) and the validator reports no new finding.
* **AC-2**: every `pytest` path in the Manual Commands block exists (`ls`), and the block's default URL is one the guard accepts.
* **AC-3**: net test count 0.

## Guardrails

* **G-1**: prose/meta card: gate by `make test-gate` (impact selection) plus tests/test_check_ref_resolution.py, tests/test_kanban_review_record.py and any trace/registry reader that the NFR edit reaches (name them).
* **G-2**: never connect to production to fill a render.md value; mark it `TODO(owner)` instead.

## Worktree notes
