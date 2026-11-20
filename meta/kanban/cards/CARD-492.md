# CARD-492: Five small code-hygiene items: a script's hardcoded database, a helper's private imports, a private read, an upper-cased tier, and the margin minimum

**Status:** done
**Priority:** P3
**Category:** tech-debt
**Estimate:** 2c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/492-code-hygiene
**Worktree:** —
**Source:** roadmap rescore 2026-11-18, wave 4 (cut 2026-11-20; premises re-read against main the same day). IDEA-035, IDEA-038, IDEA-054, IDEA-062, IDEA-044, each WSJF 3.08-3.85 and 0.125 d: bundled because each alone is below sizing.min_estimate.
**Idea:** IDEA-035, IDEA-038, IDEA-054, IDEA-062, IDEA-044
**Wave:** 83
**Created wave:** 83
**Deferred waves:** 0
**Depends on:** —
**Touches:** scripts/diagnose_postgres.sh, tests/helpers/admin_scripts.py, tests/test_start_admin_local.py, src/nonogram/admin/puzzle_review.py, src/nonogram/admin/app.py, src/nonogram/admin/print_specs.py, src/nonogram/admin/templates/puzzle_solve.html
**UI surface:** admin solve page (tier badge, tab title)
**Review score:** 9.3 (cycle 1/3 - CERTIFIED)
**Started:** 2026-11-20T00:32Z
**Closed:** 2026-11-20T01:42Z
**Actual:** 1c — ratio 1/2 = 0.5
**Merge commit:** 31cfe1445387b1fe738667687fde78dcae75f233
**Blocked by:** —

## Why this card exists

1. **IDEA-035 (CARD-152).** scripts/diagnose_postgres.sh still greps for and suggests `nonogram_poc`, the defect CARD-150..152 removed from the other three scripts.
2. **IDEA-038 (CARD-152 F-005).** tests/helpers/admin_scripts.py imports private names from tests/test_start_admin_local.py (`_DOCKER_STUB`, `_PSQL_SHIM`, `_all_pairs`, …); renaming one breaks both suites.
3. **IDEA-054 (CARD-160 F-006).** app.py's `_board_page_payload` calls the private `PuzzleReviewService._as_readable_grid`.
4. **IDEA-062.** `puzzle_solve` passes `tier.value.upper()`, so the admin solve page's badge and tab title say "MEDIUM" where every other screen shows "medium".
5. **IDEA-044 (CARD-154).** `PrintSpecValidator.validate_margins` refuses nan/inf but accepts a margin below the 0.635 cm minimum ("0.5"). Unreachable from the UI today; a stored small margin makes Finalise fall back to "about N".

## What to implement

Re-verify each on main first; drop any already closed with one line in the notes.

1. diagnose_postgres.sh reads the database the way the other three scripts now do.
2. The shared names move to the helper (or a shared module) and both test files import them from there; no test file imports another test file's private name.
3. A public read on `PuzzleReviewService` (or a module function), and the route uses it; `_as_readable_grid` callers inside the class unchanged.
4. The solve page shows the tier as stored. Check every test that pins "MEDIUM"/upper-case and the public player (which must stay untouched, CARD-452 redid its title).
5. `validate_margins` refuses a value below the minimum with a message naming it; the minimum comes from the existing constant if there is one (find it), not a new literal.

## Acceptance criteria

* **AC-1**: one control per item where a test can hold it (items 3 and 5 each red when reverted; item 4's page test reds on `.upper()`); items 1 and 2 by a recorded run (`bash -n`, the two test files green).
* **AC-2**: the public player's pages and payloads byte-identical to main's (assemble and diff), since app.py and a template change.
* **AC-3**: net test count at most +2; report it.

## Guardrails

* **G-1**: the store's single solver call site rule (`test_there_is_exactly_one_solver_call_site_in_the_store`) still holds; puzzle_review.py gains a read, not a solve.
* **G-2**: gate: `make test-gate` (app.py changes widen it; take what it selects).

## Worktree notes

### Implementation (2026-11-20)

All five premises re-verified on the branch before any change, by recorded run: (1) `diagnose_postgres.sh` run with stub `psql` on PATH and `DATABASE_URL=.../nonogram_dev` exported: it listed databases and grepped for `nonogram_poc`, and with `nonogram_poc` absent `set -e` ended the script at that grep (exit 1); with it present it overwrote `DATABASE_URL` and connected to `.../nonogram_poc`. (2) ast scan: `tests/helpers/admin_scripts.py` imported `_DOCKER_STUB, _PSQL_SHIM, _all_pairs, _plain, tool_dir` from `tests.test_start_admin_local`, and nothing else imported private names from that file. (3) ast: `app.py` called `PuzzleReviewService._as_readable_grid` once. (4) the memory-mode solve page rendered `Puzzle 25×15 · MEDIUM - Nonogram admin` and badge `MEDIUM`. (5) `validate_margins("0.5", "1.27")` and `("1.27", "0.6")` returned `(True, None)`. None was already closed.

1. **IDEA-035.** `scripts/diagnose_postgres.sh` now carries the same DATABASE_URL resolution block as the other three scripts (an exported URL wins; default `.../nonogram_poc`, the panel's database), checks `$DB_NAME` (inside an `if`, so `set -e` no longer ends the script when the name is missing), connects with `"$PSQL_URL"`, and does not overwrite `DATABASE_URL`. Recorded runs with stub psql: an exported `nonogram_dev` URL, no URL, a `+psycopg2` URL with `?dbname=nonogram_dev`, and a URL naming no database each report and connect to the database the URL names, exit 0. `bash -n` clean. Held by changing two existing tests in `tests/test_setup_admin_local.py`: `test_the_three_copies_of_the_url_resolution_are_identical` now includes diagnose_postgres.sh (name kept, since `tests/test_admin_local_cost.py` pins it by node id) and `test_each_script_defaults_to_its_own_database` pins its default line.
2. **IDEA-038.** New `tests/helpers/admin_script_stubs.py` holds `PSQL_MODEL`, `DOCKER_STUB`, `PSQL_SHIM` (with `MODEL_PATH`), `tool_dir`, `plain` and `all_pairs`, moved unchanged from `tests/test_start_admin_local.py` except for the names (leading underscores dropped). That test file and `tests/helpers/admin_scripts.py` both import them from there; the test file's now-unused imports were removed. ast re-scan: no module imports a private name from `tests.test_start_admin_local` (`tests/test_admin_local_cost.py` still imports its public `DEFAULT_DB`, `connections`, `run_script`; out of scope). Two docstring references in `tests/test_admin_local_cost.py` were updated to the new location.
3. **IDEA-054.** `PuzzleReviewService.readable_grid` (public staticmethod, delegates to `_as_readable_grid`; no solve) is now what `_board_page_payload` calls. The in-class `_as_readable_grid` callers are unchanged; `test_there_is_exactly_one_solver_call_site_in_the_store` passes.
4. **IDEA-062.** `puzzle_solve` passes `tier.value` (as stored, "medium"), not `.upper()`. Pinned upper-case form found by ast over the tests: `tests/test_puzzle_solver_page.py` (`TestSolverPageHeader` x2, `test_ac323_...`, the browser test `test_the_drawn_page_keeps_the_name_out_of_the_header_until_the_banner_reveals_it`) and `tests/test_puzzle_editor_ui.py::...::test_the_editor_page_claims_no_difficulty_of_its_own`. All changed to the stored spelling. `tests/test_player_public_mode.py` (renders the template with `tier_label="MEDIUM"` itself) and `tests/test_player_shared_ui_site.py` (the public site) are the public player and were left alone.
5. **IDEA-044.** `PrintSpecValidator.validate_margins` refuses a gutter or outside margin below `MIN_SIDE_MARGIN_MM / 10` (the existing `book_page_spec.MIN_SIDE_MARGIN_MM`, 6.35 mm) with "`<label>` must be at least 0.635 cm". The bleed margin is still checked for finiteness only, because `book_page_spec` does not read it as a side margin. New test `tests/test_print_specs.py::TestMarginValidation_RefusesNonFiniteValues::test_a_side_margin_below_the_minimum_is_refused` (oracle literal 0.635; boundary 0.635 accepted, bleed 0.5 accepted).

**Controls** (each mechanism reverted, the named test red, the file restored, `git diff --stat` unchanged afterwards):
* Item 5, the minimum check deleted: `test_a_side_margin_below_the_minimum_is_refused` fails with `AssertionError: ('gutter_margin_cm', '0.5')`, a PrintSpec returned in place of the refusal.
* Item 3, the route back on `_as_readable_grid`: `TestSolverPageStoredRows::test_a_legacy_zero_one_grid_is_read_as_booleans` (an existing test, which now spies on `readable_grid`) fails with `AssertionError: the route did not read the grid through readable_grid`.
* Item 4, `.upper()` restored: 6 red, namely `test_header_reads_puzzle_size_and_the_tier[memory|sqlite]` (badge regex `assert None`), `test_header_reads_a_display_label_tier_too[memory|sqlite]` (`'>hard</span>' in ...`), and `test_ac323_...[memory|sqlite]` (`'Puzzle 25×15 MEDIUM' == 'Puzzle 25×15 medium'`).
* Item 1, diagnose_postgres.sh reverted to the base: `test_the_three_copies_of_the_url_resolution_are_identical` and `test_each_script_defaults_to_its_own_database` both fail with `AssertionError: ('diagnose_postgres.sh', [])`, because the block is absent.
* Item 2 has no revert to show: the old import names no longer exist. It is held by the ast scan and by the two suites passing.

**AC-2.** I assembled the public player from a `git archive` copy of the merge-base and from the branch, each with its own `scripts/assemble_player_site.py --bundle <main>/build/player-bundle`. `diff -rq` of the two 178-file trees is empty, exit 0. The template is untouched; the site renders `puzzle_solve.html` with its own `tier_label`.

**AC-3.** The collected count went from 10705 (merge-base) to 10706 (branch), so net +1: the margin test.

**Gate** (worktree, `-o addopts= -rfs`; DATABASE_URL unset unless marked armed):
* Non-browser, 678 passed, 0 failed, 0 skipped (32 browser tests deselected): test_start_admin_local, test_setup_admin_local, test_run_admin_tests, test_admin_local_cost, test_print_specs, test_puzzle_solver_page, test_puzzle_edit_store, test_admin_uniqueness_boundary, test_book_page_spec, test_book_scaffolding.
* Including browser tests, 403 passed, 0 failed, 0 skipped: test_puzzle_solver_page, test_puzzle_editor_ui, test_player_public_mode, test_cli (layering guard).
* 73 passed, 0 skipped: test_admin_import_consistency, test_card_063_limits, test_admin_tier_surfaces.
* Armed (DATABASE_URL=.../nonogram_test), 384 passed, 0 skipped: test_print_specs, test_puzzle_edit_store.

The full suite was not run here; it belongs to the orchestrator's `make test-gate`.

[Review 1/3] Score: 9.3, nothing gating, certified. Every re-measured figure reproduced (10705 -> 10706, each control's red list, the empty public-site diff over 178 files, the four script runs); item 2's eight moved definitions AST-identical; item 5 agrees with book_page_spec on 6007 decimal spellings; mutants on items 3-5 each red. Low findings fixed inline by the orchestrator: F-001 step 6 reported a working connection for a URL naming no database (psql fell back to the user's own database), now skipped with a warning; F-002 step 5 matched the name as a word anywhere in `\l` (an Owner column, a regex), now the first column whole and as a fixed string. Driven with a stub psql printing a real `\l` layout: `nonogram_dev` found; `nonogram_x` (present only as an Owner) and `nonogram` (a prefix) not found; a URL naming no database skips step 6. tests/test_setup_admin_local.py, test_start_admin_local.py, test_admin_local_cost.py: 82 passed. F-002's other half (step 5 asks localhost:5432, not the URL's server) left as is: its message names localhost:5432. F-003, F-004 info, not taken.


**Merge gate (orchestrator).** `make test-gate BASE=main` answered SELECTION: 9140 passed / 30 skipped (the expected unarmed count: 29 DATABASE_URL unset + 1 setrlimit) / 1 xfailed / 0 failed, plus 11 marked (wave_close_only) passed in the lifted files; 2 marked tests owed at the wave close.
