# CARD-521: tests/README.md describes the suite as it is today

**Status:** done
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/521-tests-readme
**Worktree:** —
**Source:** roadmap wave 11, cut 2026-11-22 on the owner's "start the no-decision wave 11". IDEA-002.
**Idea:** IDEA-002
**Wave:** 90
**Created wave:** 90
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/README.md
**UI surface:** —
**Review score:** 9.0 (cycle 2/3 - CERTIFIED)
**Started:** 2026-11-22T11:26Z
**Closed:** 2026-11-22T12:00Z
**Actual:** 1c — ratio 1/1 = 1.0
**Merge commit:** 5815bf057abbe39d163b9bc11e715aeefcb1534b
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

### Implementation (2026-11-22)

**Premise re-verified.** The title was "Admin Panel Test Suite - Wave 1"; the sections above the profiling section named only the four Wave 1 files, six markers of which two are applied by no test, a coverage run (`pytest-cov` is not installed: `import pytest_cov` raises ModuleNotFoundError), a CI section (no CI config is tracked), and `docs/ADMIN_FINDINGS.md` (absent). Troubleshooting and Next Steps, after the kill-matrix section, were stale too, and Troubleshooting carried a full database URL with a credential (removed, G-2).

**Readers of tests/README.md, found by `ast`** (every string constant naming README under `tests/` and `scripts/`, then the enclosing function resolved by walking the module AST):
- `tests/test_kill_matrix.py::test_ac4_restoring_uses_cp_p_backups_and_no_git_command_anywhere` reads the file and asserts `GIT_COMMAND.pattern` is in it (CARD-516).
- `tests/test_full_suite_lock.py::test_nothing_in_the_tree_sets_either_of_the_guards_env_switches` and `::test_an_executable_setter_under_an_allowlisted_prefix_is_still_caught` scan the tracked tree; `tests/README.md` is in `OVERRIDE_NAMERS`, allowed to name the lock switches.
- The other hits are not readers: `tests/test_cli.py` (a string case), `tests/helpers/admin_scripts.py` and `tests/test_start_admin_local.py` (scripts/README.md), and docstrings/comments in `test_full_suite_lock.py`, `test_guard_integrity.py`, `test_suite_profile.py`, `test_db_url_driver.py`, `full_suite_lock.py`.
All three readers: 3 passed before the edit and 3 passed after, by node id, unarmed.

**What changed.** `tests/README.md` only. Lines above the profiling section were rewritten: title "Test suite", Layout, Running it (Makefile targets table, `-o addopts=`/`-rfs`), Markers, Fixtures, The database: unarmed and armed, Expected skips, The full-suite lock, Troubleshooting (moved above the profiling section). Next Steps and the "Wave 1 Complete" footer were removed. G-1: the profiling and kill-matrix sections are byte-identical except one deletion, the two-line blockquote "The rest of this file predates wave 20 and describes the admin-panel tests only. This section is current ..." which became false once the top was rewritten (checked by `diff` of the section span HEAD vs branch: only those lines and the old Troubleshooting heading differ).

**AC-1, every name checked** (script `/private/tmp/claude-501/card521/ac1_check.txt`, all OK): paths CLAUDE.md, meta/architecture/requirements.yml, tests/property/test_solver_uniqueness.py, tests/e2e/README.md, tests/helpers/{brute_force_oracle,db,mock_generator,pdf_pages,pdf_vector,page_ink,round_ink,two_up_ink,qr_reader}.py, tests/fixtures/ and make_fixtures.py, tests/{conftest,hang_guard,database_guard,db_name,full_suite_lock,wave_close_marker,kill_matrix}.py, scripts/impact_set.py, scripts/run_admin_tests.sh, tests/test_book_pdf_memory.py, src; Makefile targets test, test-gate, test-marked, test-wave-close, test-impact, impact-set; pyproject `addopts = "-q"`, `pythonpath = ["src"]`, markers browser and wave_close_only and the `playwright install chromium` instruction; conftest markers db_required, unit, integration, e2e, slow, smoke, performance; conftest fixtures (by `ast`) db_session, app, client, puzzle_review_service, batch_generator_service, generator, sample_puzzle, sample_puzzles, cleanup_puzzles, test_db_url, _armed_database_is_ready, _assembled_default_interior_writers; functions _refuse_unless_test_database, pytest_runtest_setup, pytest_configure, full_suite_lock.acquire/release/is_full_suite, db_name.derive_test_database_name; quoted texts "Database not reachable: DATABASE_URL is not set", "Image fixtures not found in tests/fixtures/", "Refusing to set up the test database", "outside [a-z0-9_]", "Refusing to start"; the print-the-name command runs and prints a `nonogram_<slug>_<12 hex>_test` name. Marker usage by `ast` over tests/: smoke and performance applied by no test; unit/integration/e2e/slow carried by 3/4/2/5 files; `scripts/run_admin_tests.sh` selects on unit/integration/e2e/smoke. There is one conftest (`find tests -name conftest.py`).

**AC-3, figures.** The new text writes no counts or times. The only number-like facts are "12 hex" (`db_name.DIGEST_CHARACTERS = 12`) and "one test in test_book_pdf_memory.py" for the setrlimit skip, from the `-rfs` run below. Expected skip reasons derived now by an unarmed run of `tests/test_db_e2e_smoke.py tests/test_book_pdf_memory.py` with `-o addopts= -rfs`: 45 passed, 7 skipped: 6 "Database not reachable: DATABASE_URL is not set", 1 setrlimit(RLIMIT_AS) platform skip.

**AC-4.** No code or test changed. Net collected count 10692 before and 10692 after (`--collect-only -q -o addopts= tests/ | tail -1`).

**Control.** Both restatements of `(\S*/)?git(\s|$)` replaced in tests/README.md: `test_ac4_restoring_uses_cp_p_backups_and_no_git_command_anywhere` red with "AssertionError: GIT_COMMAND is '(\\S*/)?git(\\s|$)' and a prose restatement of it no longer says so: update the prose with the pattern", and the shown prose starts "# Test suite", so it read the new file. Restored from a copy; `cmp` identical.

**Gate (unarmed, -o addopts= -rfs).** `tests/test_full_suite_lock.py tests/test_kill_matrix.py` (the readers' whole files): 144 passed, 0 skipped, 0 failed. Not run armed: the card changes no database path.

[Review 1/3] Score: 8.5, one gating finding, not certified. Every Makefile target, marker, fixture, skip text, guard and lock behaviour the new text states matches the code; the three README readers pass (3 passed) and an `ast` walk found no other; G-2 clean; the deleted "predates wave 20" blockquote was right (F-004). F-001 (Important): "Export DATABASE_URL with that name and your local role" is wrong for every role but one: `_armed_database_plan` prepares only when DATABASE_URL equals `db_name.resolve_test_database_url(...)` character for character, so the derived name with any other role gives `'elsewhere'`, and the summary then says the suite "neither created nor migrated" a database that has this tree's name. F-002 (low): "Running it" and "Layout" restate CLAUDE.md and the Makefile (targets, no .venv in a worktree, the oracle import rule). F-003 (low): "Expected skips" was derived from two files; the poppler skips and the missing-`meta/design/` skip are not named. F-005 (out of scope, pre-existing): the profiling section's lock recipe hardcodes an absolute path to the main checkout.

### Fix round 1 (2026-11-22)

- **F-001.** "The database: unarmed and armed" was rewritten from `_armed_database_plan`. It now says the whole URL (trimmed) is compared with the resolved URL, not the name. It gives a one-liner that prints `_armed_database_plan(os.environ)[2] == 'prepare'` (True/False, no URL, no connection). For your own role or server: export `TEST_DATABASE_URL` and `DATABASE_URL` to the same URL with the derived name. Verified by calling the plan with no connection. Plan outputs: default resolved URL -> prepare; derived name under another role with only DATABASE_URL -> elsewhere; both set to the same URL -> prepare; a padded DATABASE_URL -> prepare; plain `nonogram_test` -> elsewhere; unset -> not-set. The one-liner itself printed False unset, True on the default URL, False with another role in DATABASE_URL only, and True with both set. G-2: grep for `postgres(ql)?://|@localhost|@127|:5432|password` in the README finds nothing.
- **F-002.** The Makefile target table, the worktree-venv sentence and the oracle import rule are replaced with pointers to `CLAUDE.md` (Commands, Architecture) and the Makefile's target comments. The section keeps only the `-o addopts=`/`-rfs` note, which neither file states.
- **F-003.** "Expected skips" now names the host-dependent skips, read from the skip marks: the poppler reasons from `NO_POPPLER`/`NO_POPPLER_PPM` in test_book_guide_page_vector.py, test_book_grid_rules.py, test_book_pdf_vector_primitives.py, test_book_puzzle_page_vector.py and test_book_solved_answer_key.py (tools looked up by `tests/helpers/pdf_vector.py`'s `PDFTOPPM`/`PDFTOTEXT`), and "meta/design/ is not shipped with the package" from test_admin_design_tokens.py.
- **F-005.** Not changed: the hardcoded main-checkout path in the profiling lock recipe is pre-existing and inside the G-1 span.
- Re-run after the fix (unarmed, `-o addopts= -rfs`): the 3 reader node ids, 3 passed; `tests/test_full_suite_lock.py tests/test_kill_matrix.py`, 144 passed, 0 skipped. Net collected count 10692 (unchanged).

[Review 2/3] Score: 9.0, nothing gating, certified. The README's arming one-liner and `_armed_database_plan` agree in all 11 environments tried (unset, default, padded, other role in DATABASE_URL only, both equal, custom `*_test` in both, custom non-`_test` in both (refused), TEST_DATABASE_URL only, padded TEST_DATABASE_URL, plain `nonogram_test`, blank); the own-role advice keeps the production guard and the `*_test` refusal. F-002 and F-003 resolved; every quoted skip reason matches the code; README readers 3 passed; G-2 clean. F-101 (low): "Two guards stand in front of the destructive fixtures" leaves out CARD-508's session lock, and Troubleshooting explains its "Refusing to set up the test database" prefix only as a non-`_test` URL. F-102 (low): "keep the derived name … per-worktree" holds only if TEST_DATABASE_URL is set per worktree (a value exported in a shell that moves trees prepares the other tree's database); "Nothing has to be created by hand." sits after the elsewhere case. F-103 (info): a prose mutant reddens nothing, by design (AC-4).

**Merge gate (orchestrator).** `make test-gate BASE=main` on `dc6eaf09` (main had not moved) answered SELECTION: 4840 passed / 20 skipped (unarmed) / 8 deselected / 1 xfailed / 0 failed in 14 min 12 s, then the marked run 6 passed. 7 marked tests are owed at the wave close.
