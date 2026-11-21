# CARD-516: The kill matrix's own anchors and controls hold what they claim

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 2c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/516-kill-matrix-anchors
**Worktree:** ../PythonProject4-card-516
**Source:** roadmap wave 9, cut 2026-11-21 on the owner's "yes, start wave 9". IDEA-185, IDEA-187, IDEA-188 (one job: the AC-7 anchors) and IDEA-182, IDEA-184 (weak controls in the same instrument). Full texts: meta/kanban/backlog.md, the five CARD-260 items.
**Idea:** IDEA-182, IDEA-184, IDEA-185, IDEA-187, IDEA-188
**Wave:** 88
**Created wave:** 88
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/kill_matrix.py, tests/test_kill_matrix.py, tests/README.md
**UI surface:** —
**Review score:** —
**Started:** 2026-11-21T20:01Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

The kill matrix (CARD-260) checks whether tests red when the code they guard is broken. Its own checks are weaker than they read:

1. **Anchors (IDEA-185, 187, 188).** The AC-7 anchor in `tests/test_kill_matrix.py` holds another file (`tests/test_db_engine_lifecycle.py`) by absolute line numbers, checks its four arms only by membership (`set(arms) <= linenos`: any four asserts pass), and pins `src/nonogram/db/session.py` by a substring count. So any edit to the lifecycle file reds the kill-matrix tests (CARD-259 had to edit them), while a swap of arms or a reordered declaration may not red at all. Hold the arms by what they are (their own labels or messages, found by `ast`) and make the session.py pin structural.
2. **Weak controls (IDEA-182).** Five items (a)-(e); (a) is one assert on `GIT_COMMAND.pattern`; (d) and (e) are the AC-4 honest-path and AC-3 `Pass` routing gaps. Close what is still open with the smallest change; drop any that is already closed with one line.
3. **Spawn aliases and one exception class (IDEA-184).** `import subprocess as sp`, `run = subprocess.run` and `functools.partial(subprocess.run, ...)` are invisible to the import census; `_verification_failures` controls the absent-binary `OSError` but not a `shasum` that exits non-zero (`CalledProcessError`). The trailing mkdtemp/mutation-window clause is CARD-315's (still ready); leave it.

These items are from October; re-verify each against main before changing anything.

## Acceptance criteria

* **AC-1**: the AC-7 anchor finds its four arms without stored line numbers: inserting blank lines above them in a copy of `tests/test_db_engine_lifecycle.py` leaves it green, and swapping two arms reds it (both shown in the notes, on a scratch copy; the real file is not edited).
* **AC-2**: the session.py pin reds on a reordered declaration of the three globals and not on an appended name (control shown).
* **AC-3**: each IDEA-182 item (a)-(e) is closed with a named control, or dropped with one line saying why.
* **AC-4**: the three alias routes are either refused by the census with a control each, or named as a stated bound in the docstring; the `CalledProcessError` arm has its own control.
* **AC-5**: net test count at most +2; change existing tests in preference to adding. Report it.

## Guardrails

* **G-1**: `tests/test_db_engine_lifecycle.py` and `src/nonogram/db/session.py` are not edited.
* **G-2**: the kill matrix's measured results on its current selections are unchanged.
* **G-3**: CARD-315's window item is out of scope.

## Worktree notes

### [Implementation] 2026-11-21: anchors held by identity, IDEA-182 (a)-(e) closed, alias routes refused

**Premises re-verified before changing anything.** On a HEAD copy of the tree (`git archive HEAD`, under `/private/tmp/claude-501/card516/tree-head`, so the real files were never touched), with each mutation applied to the scratch copy only:
- Anchors: HEAD's `test_ac7_the_four_arm_grid_of_card_257_reproduces` **passes** with the names and heads arms' messages swapped (9 passed for `-k "ac5 or four_arm"`). That is the misattribution IDEA-188 described. Three blank lines above the preamble arm red HEAD's AC-7 test and AC-5 nodes `[2-1194]`..`[5-1529]` (5 failed). That is the IDEA-187 coupling.
- (a) F-502: with `GIT_COMMAND` respelled `(?:\S*/)?git(\s|$)`, HEAD's whole file passes except the lock-guard anchor (see the scratch-tree caveat below).
- (d) With `between[mutant.name] = shipped` in `Runner.run`, HEAD's `test_ac4_two_sequential_mutants_each_see_a_clean_shipped` stays green.
- (e) With `Pass.reraise` inverted, HEAD's `test_ac3_one_transformer_and_the_recording_pass_is_its_failing_state` stays green (1 passed).
- IDEA-184 shasum: with `CalledProcessError` dropped from `_verification_failures`' except, HEAD's file stays green except the lock-guard anchor.
- (b) F-402: with an added downstream empty-edit refusal in `run()`, HEAD's `test_g1_the_two_construction_refusals_each_have_a_control` stays green. The clause was true but nothing measured it.
- Scratch-tree caveat: `test_ac7_the_lock_guard_file_reproduces_130_of_130_pass_and_reached` was red in all three full-file runs on the HEAD scratch tree, under three unrelated mutations. I read that as an effect of the scratch tree (no `.git`), not of any mutation. I did not attribute it further. In the worktree it passes.
- (c) F-403 still held in a new form. `Runner.workdir`'s docstring said "the two tests". An `ast` census counts **three** tests that drive helpers without `run` (`test_ac1_the_planted_shifting_mutant_runs_green_and_reports_nothing`, `test_g5_a_restore_failure_still_restores_every_registered_path`, `test_g5_a_shasum_that_could_not_run_is_counted_as_a_failure`), and all three set `_workdir`.
- No item was already closed, so nothing was dropped.

**What changed, by name** (`tests/test_kill_matrix.py` unless stated):
- AC-1: `PREAMBLE, NAMES, HEADS, POINTER = 1194, ...` is replaced by `FOUR_ARM_LABELS` and `_four_arms()`. Each arm is the single assert of the anchored method whose predicate source matches the arm's regex **and** whose own message carries its phrase. The two must name the same node, and the four must stand in the recorded order. `_four_arm_grid(arms)` takes the derived arms. The membership check against `km.assert_linenos` is kept beside it. Today's derivation equals the old literals exactly: `{'preamble': 1194, 'names': 1270, 'heads': 1277, 'pointer': 1283}`.
- AC-5's positions: `NAMES_BLIND_OCCURRENCES` is replaced by `_names_blind_occurrences()`, which reads the string constants off the AST. `test_ac5_an_explicit_occurrence_hits_exactly_that_lineno` is parametrized on the occurrence alone (node IDs `[1]`..`[5]`, still 5 nodes). It now asserts that the NAMES-BLIND arm (`_four_arms()["preamble"]`) is occurrence 2 and no other. Consequence: an AC-7 identity failure also reds these five nodes, with the same message.
- AC-2: `_init_engine_declaration()` replaces `count("global engine, SessionLocal, _engine_url") == 2`. It requires that `_init_engine` has exactly one `global`, that its names begin with `INIT_ENGINE_DECLARED` in that order, and that its source starts with the text the NAMES-BLIND mutant replaces.
- (a) `test_ac4_restoring_uses_cp_p_backups_and_no_git_command_anywhere` asserts `GIT_COMMAND.pattern` in its own docstring and in `tests/README.md`.
- (b) `test_g1_the_two_construction_refusals_each_have_a_control` plants an edit-less mutant past the refusal (`object.__setattr__`) and asserts that its column equals SHIPPED's cell for cell.
- (c) `Runner.workdir`'s docstring (`tests/kill_matrix.py`) no longer gives a count. It states the rule and the lock-refusal bypass. `test_g5_a_finished_run_discards_its_temp_tree_and_a_failed_restore_keeps_it` enumerates the helper-driving tests from this file's AST. The helpers are derived from `Runner`: the methods that reach `workdir`, closed transitively. Each such test must assign `_workdir` itself.
- (d) `test_ac4_two_sequential_mutants_each_see_a_clean_shipped` asserts `matrix.label == f"SHIPPED after {name}"`.
- (e) `test_ac3_one_transformer_and_the_recording_pass_is_its_failing_state` builds both bodies through `Pass.reraise`.
- AC-4: `_aliased_spawn_imports` also refuses `import <spawn module> as <alias>` and a spawn-shaped name used as a value (Assign / call argument). The value rule is default-deny, except an `except` clause's type. `SPAWN_IMPORT_TARGET` plants all three routes plus an `except subprocess.CalledProcessError`. The literal in `test_g5_the_bare_name_spawn_import_census_catches_a_planted_import` gains three entries. `test_g5_a_shasum_that_could_not_run_is_counted_as_a_failure` adds a `shasum` that exits 1, and tells the two plants apart by the exception text in the finding. `_verification_failures`' docstring says so.
- `tests/README.md`: the AC-7 paragraph no longer recites addresses, and the G-5 paragraph names the four refused routes.

**AC-1 (scratch copies of `tests/test_db_engine_lifecycle.py` in `/private/tmp/claude-501/card516/tree-new`, a copy of this worktree; `-k "ac5 or four_arm"`):**
- Blank lines: three blank lines inserted above the preamble arm give **9 passed in 30.61s**, with the full 14-mutant grid run. The same edit reds HEAD (5 failed, above).
- Swap by labels: the names and heads messages exchanged give **6 failed**. The AC-7 red: `the names arm is not one assert that both checks '_names_shown_in\\(.*' and says 'does not name every global': the predicate is at [1270], the message at [1277]`. HEAD passed this same copy (9 passed).
- Swap by position: the heads block (with its `shown =` line) moved above the names assert gives **6 failed**: `the four arms stand in the order ['preamble', 'heads', 'names', 'pointer'] ... not ['preamble', 'names', 'heads', 'pointer']`. HEAD reds this one too (1 failed, membership): that shift did not overlap.

**AC-2 (`/private/tmp/claude-501/card516/ac2_demo.py`: `_init_engine_declaration()` with `SESSION_PY` pointed at scratch copies; the old pin evaluated beside it):**

| `session.py` copy | new pin | old pin |
|---|---|---|
| pristine | green | green |
| reorder in `_init_engine` | **RED** `_init_engine's global statement is ['global SessionLocal, engine, _engine_url'], not one statement starting 'global engine, SessionLocal, _engine_url'` | RED |
| append `_extra` in `_init_engine` | green | green |
| reorder in `reset_engine` | green | **RED** (spurious: not the statement the mutant edits) |
| append `_extra` in `reset_engine` | green | green |

**Controls.** Each one mutates the real file through `/private/tmp/claude-501/card516/control.py`, which restores from a `cp -p` backup and checks the sha256. `git diff --stat` afterwards showed only this card's three files.
- (a) `GIT_COMMAND` → `(?:\S*/)?git(\s|$)`: `test_ac4_restoring_...` RED, `GIT_COMMAND is '(?:\\S*/)?git(\\s|$)' and a prose restatement of it no longer says so`. The string-census test stays green.
- (b) A downstream `if not mutant.edits: raise MutantRefused("downstream: edits nothing")` in `run()`: `test_g1_the_two_construction_refusals_each_have_a_control` RED, `MutantRefused: downstream: edits nothing`.
- (c) The shasum test's two `_workdir` lines deleted: `test_g5_a_finished_run_...` RED, `['test_g5_a_shasum_that_could_not_run_is_counted_as_a_failure'] drive Runner helpers without a run and leave _workdir at a machine-wide temp directory nothing removes`.
- (d) `between[mutant.name] = shipped`: `test_ac4_two_sequential_...` RED, `MARK-ROT's between-mutants reading is labelled 'SHIPPED', so it was not the reading taken after that mutant`.
- (e) `Pass.reraise` → `self is Pass.RECORDING`: `test_ac3_one_transformer_...` RED, `assert 'raise' not in 'def f():...'`.
- Alias import branch off (`if False and alias.name`): the planted-import test RED, `found [... 'subprocess.run in Assign', 'subprocess.run in Call']` with `'subprocess as sp'` missing.
- Value rule off (`and False` in place of the `_SPAWN` search): the planted-import test RED, with `'subprocess.run in Assign'` and `'subprocess.run in Call'` missing.
- `except` exclusion removed: RED in both the planted-import test (an extra `'subprocess.CalledProcessError in Tuple'`) and the instrument's own WITHOUT half in `test_ac4_restoring_...` (`['subprocess.CalledProcessError in Tuple', 'subprocess.CalledProcessError in Tuple']`).
- `CalledProcessError` dropped from `_verification_failures`' except: `test_g5_a_shasum_...` RED, `subprocess.CalledProcessError: Command '['shasum', '-a', '256', ...` escapes.
- `OSError` dropped from it: the same test RED, `FileNotFoundError: [Errno 2] No such file or directory: 'shasum'`.

**G-1:** `tests/test_db_engine_lifecycle.py` and `src/nonogram/db/session.py` are not in the diff. **G-2:** the derived arms equal the old literals, and the 14-mutant grid and the 165-assert lock-guard anchor both pass unchanged. **G-3:** the mkdtemp / plant-window item is untouched.

**Timing:** `tests/test_kill_matrix.py` alone took **84.67 s** at HEAD (84 passed). The four-arm grid accounts for 26.83 s and the lock-guard anchor for 13.26 s.
After the change, the same file standing alone: **84 passed in 72.20 s**, with no lock held. The earlier post-change run took 91.20 s. Wall clock here measures machine load as much as the work: a second worktree's full suite started during this card.

**Gate** (unarmed, `-rfs`): `tests/test_kill_matrix.py` plus its neighbours. Those are `tests/test_wave_close_marker.py` (marker globs over these node IDs), `tests/test_db_engine_lifecycle.py` (the anchor's subject) and the four other files that read `tests/README.md`: `tests/test_db_url_driver.py`, `tests/test_cli.py`, `tests/test_guard_integrity.py`, `tests/test_full_suite_lock.py`, `tests/test_suite_profile.py`. Result: **991 passed, 1 failed, 2 skipped**. The two skips are `tests/conftest.py:290: Database not reachable: DATABASE_URL is not set`, the expected unarmed reason. The 1 failure, `test_suite_profile.py::TestSuiteCeiling_TheCliffEdgeListIsDerived::test_both_cliff_edge_rows_are_tests_the_suite_still_collects`, was its child pytest being refused by CARD-515's full-suite lock, as its own message said. Re-run alone after the lock cleared: **1 passed**. No armed run: the card asks for none, and the change touches no DB path. `tests/test_kanban_review_record.py` after the card edit: **71 passed**.

**Net test count (AC-5):** 10690 collected before and 10690 after, so **net 0**. No test was added. The five AC-5 nodes were re-keyed from `[N-lineno]` to `[N]`.
