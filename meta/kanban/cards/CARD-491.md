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

- [Impl] 2026-11-20. Three edits, each premise re-verified on the branch first.
  1. **IDEA-009, the memory-limit NFR.** Premise held: no requirement named tests/test_book_pdf_memory.py's checks or the 512 MB limit. Added **NFR-009** (category performance, metric `book_export_peak_memory`) after NFR-008, with AC-418..AC-421 (AC-417 was the highest id), plus a `covered` trace.yml row. The `test:` refs are four classes, each one `ast` ClassDef in tests/test_book_pdf_memory.py and nowhere else: `TestBookPdfMemory_RealBookExportsUnderTheCap`, `TestBookPdfMemory_PeakDoesNotGrowWithPageCount`, `TestMemoryGuard_StillFailsWhenTheExportItselfRegresses`, `TestBookPdfMemory_InteriorAndCoverStillSeparate` (19 passed, 1 skipped: the RLIMIT_AS twin, "kernel refuses it" on macOS). The threshold says only what those tests assert: one retained page bitmap, equal peaks on the 12-page and 305-page books (the condition says this is not a proof for every page count), bitmap plus file under half of 512 MB, and the old shape over 512 MB. No new test.
     tests/test_check_ref_resolution.py: the base reproduced all nine pins. I diffed every class as SETS with the module's own `_verdicts`/`_declared_refs`/`_fingerprint`, before and after the edit: CENSUS 599 -> 603, TRACE_TESTS 511 -> 515 and DEFINED 474 -> 478, each OUT 0 and IN exactly those four refs. The other six classes did not change. The pins were updated with notes that name no ref (G-2).
     Validator of record (forge_1 validate.py): 0 errors and 105 warnings before and after. The sorted finding sets are identical, so there is no new finding.
     Control 1: NFR-009 removed from requirements.yml and trace.yml, new pins kept. Red: `test_a_ref_with_a_real_definition_is_not_reported` ("the 'defined' class moved: measured (474, ...), baseline (478, ...)") and `test_the_trace_tests_lists_agree_with_an_independent_reading` ("trace.yml's tests: refs moved: (511, ...) against baseline (515, ...)"). The CENSUS assert in that test sits after the TRACE_TESTS assert, so control 1 cannot reach it. Control 2 does: AC-421's ref misspelled to a name no def holds, in requirements.yml only. Red: CENSUS ("the census moved: (604, ...) against baseline (603, ...)") and honest-dead ("moved: measured (12, ...), baseline (11, ...)"). Both mutants were restored; afterwards the module showed 26 passed and `git diff --stat` matched the pre-control figures.
  2. **IDEA-029, Tier.** Premise held: `list(difficulty.Tier)` imports as EASY, MEDIUM, HARD (three members). `difficulty.LADDER == solver.RUNG_ORDER` (three rungs) and `solver.STRATEGY_GUESS == "guess"`, which is appended iff branch_nodes > 0 (orchestrator, admin/regrade, admin/puzzle_review). The requirements.yml enum_note now says `guess` is the fourth STRATEGY. ADR-0025 made it a tier, and ADR-0031/CARD-098 retired that tier. EC-015, which the note cited as live, is retired and is now named as retired. `difficulty.Tier` has three members, citing `test_tiers_three_bands_and_no_fourth_tier`. In tests/test_difficulty_tiers.py I changed six comments/docstrings that described ADR-0025 as current: the `classify` comment, `test_classification_and_the_band_table_never_disagree`, `test_a_tier_is_its_flag_value_and_carries_a_display_label`, `test_the_tool_supports_exactly_the_four_tiers_adr_0025_names`, `test_the_cli_help_names_the_fourth_tier_and_says_what_it_means`, and one section header. Evidence that no assertion changed: the module's `ast.dump` with docstrings blanked is equal to HEAD's. Test names are unchanged (renaming would change node ids); the two historical names now say so in their docstrings. There is no mechanism to revert, so there is no red control for this item.
  3. **IDEA-081.** F-002 partly stale: every pytest path in Manual Commands exists (`ls`: tests/test_wave1_e2e.py, tests/test_wave2_async_generation.py, test_batch_history/puzzle_preview/bulk_operations). The real defects were these. "Run all tests" ran two files. The block's `nonogram_poc` default is refused by `database_guard.verdict` (measured: allowed=False). `--cov` needs pytest-cov, which is not installed and not in the dev extra. The fix keeps the `nonogram_poc` export for Flask. Before the tests, the block now exports the URL the suite derives (`tests.db_name.resolve_test_database_url(os.environ)`; the one-liner was run from the worktree). `database_guard.verdict` accepts it (allowed=True), and it ends in `_test`, as conftest requires. "Run the whole suite" is now `python -m pytest`, the wave lines name their files, and the coverage line says pytest-cov is missing. F-001: render.md's env table gains a `PYTHONUNBUFFERED` row (set by `render.yaml` to "1", and `render.yaml` is not what the dashboard-managed service runs; dashboard value TODO(owner)). **F-003 settled:** the observations are recorded second-hand in the repo: meta/kanban/backlog.md's 2026-09-23 DEPLOYMENT item, CARD-168's card and commit 1abc08c3 (2026-09-23). The quoted Werkzeug log lines have no source but render.md itself. render.md now says so, with a TODO(owner) to keep a copy if Render still has the log. No connection to production or Render.
  - Out of scope, noted only: `nonogram generate --difficulty`'s help (src/nonogram/cli.py) still says "guess is for puzzles whose solve had to branch" as if `guess` were a tier.
- [Gate] Unarmed (`-o addopts= -rfs`): tests/test_check_ref_resolution.py, test_difficulty_tiers.py, test_difficulty.py, the registry readers test_approval_guess_gate.py, test_book_page_packing_doc.py, test_grid_bound_agreement.py, test_nfr001_generation_time.py, test_public_player.py and test_public_player_pages.py, the scripts/README.md readers test_start_admin_local.py, test_setup_admin_local.py, test_admin_local_cost.py and test_full_suite_lock.py, plus test_kanban_review_record.py and test_impact_set.py: **646 passed, 1 xfailed, 0 skipped, 0 failed**. Net collected count 10706 -> 10706 (0).
