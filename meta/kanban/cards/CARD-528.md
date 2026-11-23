# CARD-528: The impact selector resolves CLAUDE.md and other root files to their readers instead of the full suite

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/528-impact-root-files
**Worktree:** ../PythonProject4-card-528
**Source:** roadmap wave 14, cut 2026-11-23 on the owner's "pick a no-decision wave from the backlog". IDEA-193 (CARD-261 build-gate finding).
**Idea:** IDEA-193
**Wave:** 93
**Created wave:** 93
**Deferred waves:** 0
**Depends on:** —
**Touches:** scripts/impact_set.py, tests/test_impact_set.py
**UI surface:** —
**Review score:** —
**Started:** 2026-11-23T08:10Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

`scripts/impact_set.py` picks which tests a merge gate runs. A path outside `KNOWN_ROOTS` (`src/`, `tests/`, `meta/`, `docs/`, `scripts/`, `migrations/`) returns FULL. Re-run on 2026-11-23: `impact_set.py CLAUDE.md` prints FULL, rule outside-known-roots. Failing closed is correct in direction, since an unmodelled path must never narrow the selection. But CLAUDE.md is read by known tests (`tests/test_cli.py`'s `TestComponentMap_*` hold it), so a CLAUDE.md-only change runs about 10,000 tests where a handful would do. The backlog triage found the same for README.md, Procfile, runtime.txt and render.yaml.

## What to implement

1. Re-verify the premise for each root-level tracked file: list them with `git ls-files` and record what the selector prints for each today.
2. For a root file whose readers can be derived the way the selector already derives readers elsewhere (tests that open the file by path, resolved by `ast`), resolve to those readers. A root file with no derivable readers stays FULL, and so does anything in `UNANALYSABLE` (Makefile, pyproject.toml and the like). Apply the selector's existing rule, not a hand-written list of root files.
3. Update the selector's docstring/comments where they state that a root-level `.md` stays FULL.

## Acceptance criteria

* **AC-1**: `impact_set.py CLAUDE.md` prints a selection that includes every test that reads CLAUDE.md, derived and not hand-listed, and does not print FULL. Control: reverting the change makes a named test red.
* **AC-2**: a root file no test reads, and every `UNANALYSABLE` file, still prints FULL. A test covers one of each, with a new untracked root file standing in for "unknown".
* **AC-3**: no path under `KNOWN_ROOTS` changes its selection. Compare the selector's output before and after over a fixed sample of at least 20 changed paths drawn from recent merges, and state the sample in the notes.
* **AC-4**: report the net test count; extend `tests/test_impact_set.py`'s existing tests where they fit.

## Guardrails

* **G-1**: the selector must never narrow on a path it cannot model. Where unsure, FULL.
* **G-2**: the gate scripts (`make test-gate`, the marker deferral) are otherwise unchanged.

## Worktree notes

### Implementation notes (2026-11-23)

**Premise, re-verified by a recorded run** (`derive()` on each of the 34 root-level `git ls-files` entries, base `34c94756`): all 31 non-UNANALYSABLE root files printed FULL `outside-known-roots`; Makefile, pyproject.toml and requirements.txt printed FULL `unanalysable`. Confirmed.

**What changed** (`scripts/impact_set.py`):
- `_classify_pre`: a root-level path (no `/`) whose suffix is not in `OUTSIDE_ROOT_DERIVABLE` is no longer refused for its location, unless `_root_tool_config` holds.
- `_root_tool_config` + `ROOT_TOOL_CONFIG_SUFFIXES` (`.ini .cfg .toml .lock`) and any dotfile: a class rule for files a tool (git, pytest, alembic, a package manager) reads by location. These stay FULL `outside-known-roots` even when a test names them (alembic.ini is named by tests, but the alembic CLI reads it from the cwd). G-1.
- `_derive_root_file` (called from `_derive_one`): FULL `unanalysable` when `_unanalysable_namer` finds an UNANALYSABLE file naming it outside a comment (pyproject `readme = "README.md"` would be that case; pyproject's comment mentioning CLAUDE.md is not); else the tests that name it (`_Corpus.naming`) plus the importers of `src/` modules that load it and the namers of chain assets/scripts (`_referencers`), the same machinery files under the roots get; FULL `no-reader` when that is empty.
- `_Corpus.root_readers` + `ROOT_WALK_IDIOMS`: tests that walk the repo root itself (`REPO_ROOT.iterdir()`, `os.listdir(".")`, `Path(".").glob(...)`), added by `derive` for any root-level change. Today all 6 matches are already always-on scanners, so it adds nothing on this tree; it exists so a future non-scanner root walker is not narrowed away.
- The `OUTSIDE_ROOT_DERIVABLE` comment that said a root-level `.md` stays FULL is rewritten.

**Root files after** (same run, final tree): CLAUDE.md 105 files, README.md 211, render.yaml 46, nonogram_admin.db 45, start.sh 45, ADMIN_SETUP.md / Dockerfile / docker-compose.yml 43 (= the always-on scanners, which are their only namers); dotfiles and alembic.ini stay FULL `outside-known-roots`; the three UNANALYSABLE stay FULL `unanalysable`; the other 18 (15 root `.md` files plus Procfile, runtime.txt, railway.json) now say FULL `no-reader` (unchanged verdict, honest rule). Procfile, runtime.txt and railway.json are named by no test, so the triage hope for them does not materialise.

**AC-1**: `test_claude_md_selects_every_test_that_reads_it` (real tree) finds CLAUDE.md's readers independently by `ast` (string constants in `tests/**/test_*.py`), asserts `tests/test_cli.py` among them, and asserts `derive(["CLAUDE.md"])` is not FULL and contains all of them. Hermetic: `test_a_root_level_file_selects_its_namers_loaders_and_root_walkers`.
**AC-2**: `test_a_root_level_file_it_cannot_model_stays_full_with_its_reason` (replaces `test_a_root_level_prose_file_stays_full_with_its_reason`), 4 cases: a new untracked `NOTES.md` nobody reads -> `no-reader`; `.toolrc` and `tool.ini` named by a test -> `outside-known-roots`; `GUIDE.md` named by a test and by pyproject's `readme` -> `unanalysable`. Every UNANALYSABLE entry is still held by the existing `test_every_unanalysable_path_falls_back_to_full`.
**AC-3**: sample = every path changed by the 40 most recent merge commits on main (`git log main --merges -40`, first-parent diff, from `8f799d5b` back to `9b22bf2a`): 102 distinct paths, 97 under KNOWN_ROOTS. Each of the 97 derived singly, plus the 97 as one set, with the pre-change script (`git show 34c94756:scripts/impact_set.py`) and the final one, against the same final tree: 98/98 identical (93 selections, 4 FULL: tests/conftest.py unanalysable, tests/database_guard.py conftest-closure, two migrations; the combined set FULL migrations+unanalysable).
**AC-4**: collected 10695 before, 10700 after: net +5 (one test replaced by a 4-case parametrisation, two tests added).

**Controls** (each mechanism removed in `scripts/impact_set.py`, the 9 class tests run, file restored, `git diff --stat` unchanged after):
- C1 root branch in `_classify_pre` removed: 4 red, incl. `test_claude_md_selects_every_test_that_reads_it` `AssertionError: [Reason(path='CLAUDE.md', rule='outside-known-roots', ...)] assert not True`, and the hermetic `assert 'FULL' != 'FULL'`.
- C2 `_root_tool_config` returns False: `[.toolrc]` and `[tool.ini]` red at `assert derived.full` (`assert False`).
- C3 `_unanalysable_namer` returns None: `[GUIDE.md]` red at `assert derived.full`.
- C4 root walkers not added: `assert 'tests/test_root_walker.py' in [...]` red.
- C5 loader importers dropped: `assert 'tests/test_imports_lonely.py' in [...]` red.
- C6 comment stripping dropped: hermetic `assert 'FULL' != 'FULL'` and the real CLAUDE.md test red (`rule='unanalysable', detail='named by pyproject.toml...'`).
- C7 `no-reader` FULL dropped: `[NOTES.md]` red at `assert derived.full`.
- Not separately controlled: `assert name in str(derived.reasons[0])` (carried from the replaced test) and `assert 'tests/test_orphan.py' not in selected` (a narrowness check, no mechanism to remove).

**Gate**: `tests/test_impact_set.py` + `tests/test_wave_close_marker.py` (the tests that load `impact_set` by path, found by `ast`; `tests/test_public_player_pages.py` names it only in a docstring), unarmed, `-rfs`: 224 passed, 0 failed, 0 skipped. G-2: `gate_verdict`, `lift`, `subject_files` and the Makefile untouched; a root-file FULL still carries `outside-known-roots`/`no-reader`/`unanalysable`, the rule ids the lift already knew.

**Not modelled (declared)**: a test building a root file's name from pieces (`"CLAUDE" + ".md"`), and a root walker whose receiver matches none of `ROOT_WALK_IDIOMS`; `changed_from_git` still sweeps untracked files only under src/ and tests/, so a new untracked root file reaches the selector only when passed explicitly.
