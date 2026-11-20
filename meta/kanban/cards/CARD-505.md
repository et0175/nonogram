# CARD-505: Three test-instrument costs: the wave-3 stub tests, the Makefile's PY default, the fifth-rule capture settle

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 2c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/505-test-instrument-costs
**Worktree:** ../PythonProject4-card-505
**Source:** roadmap wave 6 (cut 2026-11-20 on the owner's "please start the next wave"; premises re-read against main the same day). IDEA-172, IDEA-194, IDEA-208 (WSJF 2.31 each).
**Idea:** IDEA-172, IDEA-194, IDEA-208
**Wave:** 85
**Created wave:** 85
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/test_wave3_image_generation.py, tests/test_wave3_e2e.py, Makefile, CLAUDE.md, tests/test_puzzle_solver_fifth_rule.py
**UI surface:** —
**Review score:** 9.4 (cycle 1/3 - CERTIFIED)
**Started:** 2026-11-20T15:51Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

1. **IDEA-172.** Test functions whose body is only a docstring and `pass` carry no evidence but count as passes (or skips). Re-read 2026-11-20: tests/test_wave3_image_generation.py has 22 bare `pass` lines over fixtures `client` and `batch_generator_service`; tests/test_wave3_e2e.py has none now (the idea said 4, so that half may be closed). Whether these hold a DB fixture (and so sit in the 29-skip unarmed baseline) is unmeasured.
2. **IDEA-194.** Makefile `PY ?= ./.venv/bin/python`, which no card worktree has, so `make impact-set` / `make test-impact` / `make test-gate` exit 127 there unless `PY=` is passed. Still so on 2026-11-20.
3. **IDEA-208.** tests/test_puzzle_solver_fifth_rule.py `_quiet` waits `4 * _RESIZE_SETTLE` and then reads the draw count once; measured at CARD-271 to double the file's wall-clock (27.35 s vs about 13.4 s). Polling the draw count until it is stable is the deterministic cheaper shape.

## What to implement

Re-verify each first (ast for the stubs); drop any already closed with one line.

1. Delete the stub tests that assert nothing (owner's "fewer tests"); keep any that asserts something. Report which, and whether any was in the unarmed skip baseline. If the baseline moves, say the new figure and its reasons; the orchestrator updates the memory note.
2. The Makefile's PY default works from a card worktree (e.g. fall back to the main checkout's venv, found via `git rev-parse --git-common-dir`), and still prefers `./.venv/bin/python` where it exists. Update CLAUDE.md's "pass PY=" sentence to match.
3. `_quiet` polls the draw count until two reads agree (bounded), with no fixed `4 *` settle; measure the file's wall-clock before and after (three runs each).

## Acceptance criteria

* **AC-1**: no test function under tests/ whose body is only a docstring/`pass` (ast count before and after reported).
* **AC-2**: `make -n test-gate` from a card worktree with no PY resolves to an existing interpreter; from main it still names ./.venv/bin/python.
* **AC-3**: the fifth-rule file is green 3 runs in a row and faster (figures); control: a poll that returns after one read lets a planted late redraw through, or the existing assertions red under a planted too-early read (show one).
* **AC-4**: net test count reported (it goes down by the stubs deleted).

## Guardrails

* **G-1**: the Makefile change must not alter what `make test-gate` / `make test-wave-close` select or run; compare `make -n` output before and after from main.
* **G-2**: a deleted test is listed by node id in the notes.

## Worktree notes

### Implementation round (2026-11-20)

**Item 1: stub tests (IDEA-172).** An `ast` walk over tests/ counts module- and class-level test functions whose body is only an optional docstring plus `pass`. It found 24 before (22 in tests/test_wave3_image_generation.py, 2 in tests/test_wave2_async_generation.py) and 0 after. tests/test_wave3_e2e.py had none, so that half of IDEA-172 was already closed. A wider walk that also counts docstring-only and `...` bodies finds 13 more, all in tests/test_shared_fixture_controls.py. They are nested inside other functions as inputs to that file's controls, pytest does not collect them, and they were left alone. In test_wave3_image_generation.py, `TestImageSelection::test_image_selection_page_loads` asserts something and stays; the classes left empty and the unused imports went with the stubs.

Deleted, by node id (G-2):
- `tests/test_wave2_async_generation.py::TestBookManagement::test_auto_balanced_puzzle_selection`
- `tests/test_wave2_async_generation.py::TestPDFGeneration::test_pdf_download_works`
- `tests/test_wave3_image_generation.py::TestImageSelection::test_upload_images_to_batch`
- `tests/test_wave3_image_generation.py::TestImageSelection::test_remove_image_from_selection`
- `tests/test_wave3_image_generation.py::TestImageSelection::test_mixed_formats_in_directory`
- `tests/test_wave3_image_generation.py::TestImagePreview::test_preview_page_shows_images`
- `tests/test_wave3_image_generation.py::TestImagePreview::test_size_option_fixed`
- `tests/test_wave3_image_generation.py::TestImagePreview::test_size_option_min`
- `tests/test_wave3_image_generation.py::TestImagePreview::test_size_option_max`
- `tests/test_wave3_image_generation.py::TestImagePreview::test_apply_size_to_all_images`
- `tests/test_wave3_image_generation.py::TestImagePreview::test_edit_puzzle_name`
- `tests/test_wave3_image_generation.py::TestImagePreview::test_invalid_size_shows_error`
- `tests/test_wave3_image_generation.py::TestImageGeneration::test_generate_batch_from_images`
- `tests/test_wave3_image_generation.py::TestImageGeneration::test_batch_tracks_original_images`
- `tests/test_wave3_image_generation.py::TestImageGeneration::test_error_handling_bad_image`
- `tests/test_wave3_image_generation.py::TestImageGeneration::test_progress_tracking`
- `tests/test_wave3_image_generation.py::TestImageGeneration::test_batch_with_mixed_formats`
- `tests/test_wave3_image_generation.py::TestImageGeneration::test_image_size_validation`
- `tests/test_wave3_image_generation.py::TestSourceImagePreview::test_puzzle_detail_shows_source_image`
- `tests/test_wave3_image_generation.py::TestSourceImagePreview::test_source_image_served_via_api`
- `tests/test_wave3_image_generation.py::TestSourceImagePreview::test_missing_image_shows_fallback`
- `tests/test_wave3_image_generation.py::TestSourceImagePreview::test_image_caching`
- `tests/test_wave3_image_generation.py::TestSourceImagePreview::test_puzzle_list_shows_images`
- `tests/test_wave3_image_generation.py::TestBatchWorkflow::test_complete_wave3_workflow`

Skip baseline: none of the 24 sat in it. Before the deletion, a run of the three wave files unarmed (DATABASE_URL unset, `-rfs`) gave 50 passed, 0 skipped, so the unarmed baseline of 30 skips does not move. No registry names a deleted test: a text search found hits only in old meta/profiling duration logs and in a different, same-named test in tests/test_image_batch_size_fix.py. requirements.yml, trace.yml, test_collected_names.py, test_check_ref_resolution.py and wave_close_marker.py name none of them.

Net collected count (AC-4): 10711 before, 10687 after (`--collect-only -q -o addopts= tests/`), 24 fewer.

**Item 2: Makefile `PY` (IDEA-194).** `PY` now uses `./.venv/bin/python` where it exists. Otherwise it uses the main checkout's venv, found from `git rev-parse --git-common-dir` (`MAIN_VENV_PY`), and failing that the plain `./.venv/bin/python`. An explicit `PY=` still wins. The comment above `test-gate` and CLAUDE.md's "pass PY=" sentence were updated to match.
- G-1: from main, `make -n` for `test-gate BASE=main`, `test-wave-close`, `test-marked`, `test`, `impact-set` and `test-impact BASE=main` gives identical output under the old and the new Makefile (46 lines each, empty diff).
- AC-2: from this worktree with no `PY`, `make -n test-gate BASE=main` names /Users/omelnikova/PycharmProjects/PythonProject4/.venv/bin/python, which exists; `test-wave-close` and `test-marked` name the same interpreter. `PY=/usr/bin/true` still overrides it.
- Control: with the old Makefile (the mechanism removed), `make impact-set FILES=Makefile` in this worktree fails with `./.venv/bin/python: No such file or directory` and make error 127. With the new Makefile it exits 0 and prints FULL. No named test covers this; under the owner's test budget none was added.
- The old comment also told worktrees to set `PYTHONPATH=<worktree>/src`, and that advice was dropped. It was confirmed unnecessary: from this worktree, under pytest run by the main venv, `nonogram.__file__` resolves to this worktree's src/nonogram/__init__.py. The main venv's editable install is a plain `.pth` path entry, and pytest's `pythonpath = ["src"]` comes ahead of it. scripts/impact_set.py imports only the stdlib.

**Item 3: fifth-rule settle (IDEA-208).** `_quiet` in tests/test_puzzle_solver_fifth_rule.py no longer sleeps `4 * _RESIZE_SETTLE` and reads once. It runs `_QUIET` in the page: it reads the draw count, waits a page `setTimeout` of `RESIZE_SETTLE + 1` ms, and reads again until two reads agree, for at most `_QUIET_READS` (8) reads, and fails with a message if they never do. Spacing the reads with the page's own timer is what makes it sound: a debounced redraw pending at the first read is due before the read's own timer, so it fires first.
- Premise re-measured: CARD-271's "a capture leaves a redraw landing" no longer holds. A capture at 390 x 844 still fires one `resize` (one at 1440 x 900 fires none), but in neither case did the draw count move 400 ms later, because solver.js's `viewportChanged` redraws only when its size key changes. This is now in `_quiet`'s docstring. The wait stays, because whether a capture redraws is solver.js's behaviour to change.
- Timing, the whole file (pytest-reported seconds): before 23.71 / 21.89 / 23.16 s, after (committed tree) 12.23 / 11.01 / 11.38 s, 17 passed and 0 skipped every run.
- Control (AC-3): a late redraw was planted (a draw mark due one `RESIZE_SETTLE` later, set just before `_quiet` in `_board`). With the real poll: 17 passed. With `_quiet` replaced by a one-read poll: 5 failed, each with `AssertionError: the board was redrawn inside the capture window (draws 3 -> 4, stash restored: True), so this capture does not describe the table the geometry below is read off` (one reads `draws 1 -> 2`). The failing tests were `test_a_light_band_reads_across_the_fifth_rule[desktop-x]` and `[desktop-y]`, `test_leaving_a_filled_cell_at_the_boards_edge_the_first_pixel_is_the_hairline[desktop]` and `[phone]`, and `test_the_rules_against_paper_are_untouched`. A one-read poll without the plant stays green (17 passed), because today nothing is pending; that is why the plant was needed. The file was restored afterwards and the diff checked.

**Gate (unarmed, `-rfs`, committed tree).** One run of tests/test_wave3_image_generation.py, test_wave2_async_generation.py, test_wave3_e2e.py, test_collected_names.py, test_impact_set.py, test_wave_close_marker.py, test_cli.py and test_guard_integrity.py: 563 passed, 0 failed, 0 skipped. tests/test_puzzle_solver_fifth_rule.py: 17 passed, 0 skipped, in each of the 3 timed runs.

[Review 1/3] Score: 9.4, nothing gating, certified. Re-derived on archive copies: 24 stubs at the merge-base, 0 at head; the removed node ids are exactly the 24 listed and nothing was added; collected 10711 -> 10687; the deleted tests' fixtures only construct objects and keep live consumers; unarmed skip baseline unmoved. Makefile: `make -n` identical from main for every PY target (36 lines, empty diff); a worktree, a `make -C` subdirectory and a no-git tree all resolve as described. Fifth-rule: 22.7-24.5 s before, 13.7-15.3 s after; the poll is sound for a redraw pending at the first read (redraw runs synchronously in the debounce timer); a one-read poll reds under the plant, and so do reads spaced a third of the settle. F-001 (low) a main-checkout path holding a space makes the fallback pick a directory -- fixed inline by the orchestrator by narrowing the Makefile comment (no such path exists here; a PY with a space was already broken). F-002 (low) the one-read control's failure count is timing-dependent: the reviewer's four runs gave 1, 2, 2 and 1 failed, not always 5; read the "5 failed" above as one run of a 1-5 range, each run red. F-003 (info) a resize dispatched more than 1 ms after the first read would pass the poll; nothing fires one during `_quiet`, and `_board`'s draw-count assertion would red rather than pass.

**Merge gate (orchestrator).** `make test-gate BASE=main` answered FULL (the Makefile changed): 10656 passed / 30 skipped (the unarmed baseline: 29 DATABASE_URL unset + 1 setrlimit) / 1 xfailed / 0 failed, all 13 wave_close_only tests included; 10687 collected, as the notes say.
