# CARD-236: The admin-local script tests stop spawning a subprocess per assertion

**Status:** in_progress
**Priority:** P2
**Category:** tech-debt
**Complexity:** standard
**Estimate:** 0.5d
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/236-admin-local-subprocess-cost
**Worktree:** ../PythonProject4-card-236
**Source:** CARD-217's profile, 2026-10-15 — `meta/profiling/suite-hotspots-20261015.md`
**Idea:** —
**Wave:** 44
**Depends on:** CARD-217
**Touches:** tests/test_start_admin_local.py and its two siblings, meta/profiling/
**Review score:** —
**Started:** 2026-10-17T15:40:28Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**Measured** (CARD-217): the admin-local script trio costs **117.16 s across 83 tests — 12.73%
of the suite's wall-clock**, and `tests/test_start_admin_local.py` alone is **51.17 s**, the
third-slowest file in the repo. The cost is subprocess spawning: these tests exercise launcher
shell scripts by running them.

**What to do.** Keep what each test proves and stop paying for a process per assertion. The
likely shapes, to be chosen on measurement:

1. Spawn once per *scenario* rather than once per assertion, and assert several facts about the
   one run.
2. Where a test only checks the script's **text** (a flag is passed, a default is set, a
   message is worded), read and parse the script instead of executing it — this project already
   prefers structural checks of that kind (`tests/test_cli.py` walks the package with `ast`).
3. Keep real execution for the cases that genuinely need it — the exit codes, the environment
   handling, anything where running it is the claim — and say which those are.

**What must not happen:** the launcher scripts are how the owner starts the panel locally, and
two earlier cards (CARD-150, CARD-152) fixed real defects in them. A faster test that stops
noticing a broken launcher is a bad trade. Every test that stops executing the script must be
replaced by one that would still catch the defect it was written for — name that defect in the
notes for each.

## Acceptance criteria

- **AC-1** (happy, the saving): *Given* the trio, *when* the suite is profiled again on a solo
  run by `rank_durations.py`, *then* their combined share is materially below 12.73% and the
  before/after is recorded. (test: `TestAdminLocalTests_ShareIsRecorded`)
- **AC-2** (guard, no claim lost): *Given* each test that stops spawning a process, *then* the
  defect it was written for is named, and a test still fails if that defect is reintroduced —
  shown with a mutant per converted test. (test: per-case, named in the notes)
- **AC-3** (guard, the real-execution set is explicit): *Given* the trio, *then* the tests that
  still execute the scripts are listed with the reason execution is the claim.
  (test: `TestAdminLocalTests_ExecutionSetIsDeclared`)
- **AC-4** (edge, a broken launcher is still caught): *Given* each of CARD-150's and CARD-152's
  original defects reintroduced into the scripts, *then* the suite reds.
  (test: `TestAdminLocalTests_StillCatchesTheOldDefects`)

## Guardrails

- G-1: The launcher scripts themselves are not edited by this card.
- G-2: No new dependency (ADR-0006/R1).
- G-3: The saving is measured by `rank_durations.py` on a solo run, CARD-217's method.
- G-4: Out of scope — the browser family (CARD-235) and the render-heavy files (CARD-218/219).

## System contract

- ADR-0006/R1 — no new runtime dependency (check:
  `tests/test_export_pdf.py::test_the_dependency_baseline_is_still_closed`)

## Architecture context

- **Components:** the local launcher scripts, tests only.
- **Trace:** not updated by this card.

## Worktree notes

- [The trap this card must avoid] CARD-150 and CARD-152 both fixed real launcher defects that
  these tests now guard. The point of the card is to pay less for that guard, not to weaken it,
  and AC-4 is the assertion that tells the difference.
- [Env] forge 2026.8.17 (no meta/.skills.yml — no min_version comparison)
- [Dispatch] Wave 44 slot, 2026-10-17T15:52Z — **owner instruction, swapped in for CARD-216** ("swap 216 for 236"), which was abandoned before its agent wrote anything and returned to `ready`. Footprint verified disjoint from CARD-222's (page-geometry code in `src/nonogram/{admin,export}` plus its own test files), so the two run concurrently with no conflict edge. Dependency CARD-217 is done — its solo profiling run is the measurement this card acts on.
