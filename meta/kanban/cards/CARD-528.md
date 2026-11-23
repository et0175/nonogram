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
**Review score:** 8.5 (cycle 2/3)
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

[Review 1/3] Score: 8.5, one gating finding, not certified. Re-derived: every root-file figure (CLAUDE.md 105, README.md 211, render.yaml 46, nonogram_admin.db 45, start.sh 45, three at 43); AC-3 98/98 identical on the same 40-merge sample; controls C1, C2, C6 red per assert; 224 passed, 0 skipped; test_impact_set.py +5. G-1 judged per narrowed file: nonogram_admin.db is opened by no src/ module; render.yaml, Dockerfile, docker-compose.yml, start.sh are read by tools the suite never runs. F-001 (Important, G-1): only dotfiles and .ini/.cfg/.toml/.lock are refused as tool config, so a new root package.json (or tsconfig.json, package-lock.json) narrows to 47 files because two tests name it to assert its absence from player/; node reads it by location, and a `"type": "module"` there changes how `tests/test_web_metadata.py`'s `node --check` parses metadata.js, a test the narrowed gate would not run. F-002 (medium): only one of the five ROOT_WALK_IDIOMS is planted in a test; `_Corpus.root_readers` scans test files but not helpers they import. F-003 (low): `_unanalysable_namer` cuts at any `#`, including one inside a string or a Makefile recipe. F-004 (low): a tool-config refusal's reason text names the generic rule. F-005 (info): helper docstrings mentioning CLAUDE.md lift 4 of 6 wave_close_only files on a CLAUDE.md change; safe, costs part of the saving.

### Fix round 1 (review 1, 2026-11-23)

Supersedes the "What changed" and "Root files after" paragraphs above where they differ.

- **F-001 (G-1), default inverted.** `_root_tool_config`/`ROOT_TOOL_CONFIG_SUFFIXES` are gone. A root-level file now narrows only if `_root_file_class` finds it in `ROOT_FILE_CLASSES`, a dict of name-glob classes (matched with `fnmatchcase`), each with its stated reason in the code: `prose` (`*.md`), `container` (`Dockerfile`, `Dockerfile.*`, `*.dockerfile`, `docker-compose*.yml/yaml`, `compose.yml/yaml`; docker is stubbed by `tests/helpers/admin_scripts.py`, never run), `hosting` (`Procfile`, `render.yaml`, `railway.json`, `runtime.txt`, `app.json`; read at deploy), `shell` (`*.sh`; runs only when invoked by name), `database` (`*.db`, `*.sqlite`, `*.sqlite3`; opened only by path). A dotfile is never admitted, even `.notes.md`. Anything else stays FULL `outside-known-roots`: `package.json`, `tsconfig.json`, `package-lock.json` all FULL on the real tree (measured).
- **F-002.** `_ROOT_CASES` parametrises `test_a_root_level_file_selects_its_namers_loaders_and_root_walkers` over 5 cases. Each case pairs one admitted class with one `ROOT_WALK_IDIOMS` spelling, so each class and each idiom has a case of its own. `_Corpus.root_readers` now scans the test-tree helpers too and follows them to their importers, as `naming()` does. The `Procfile` case puts its `parents[1].glob` walker in a helper that a test imports. On the real tree, no helper matches any idiom (measured by running the idioms over every non-test module under tests/).
- **F-003.** `_strip_hash_comment` cuts at a `#` only outside quotes and at the start of a line or after whitespace. This one rule applies to TOML, cfg, requirements and Makefiles; Python still goes through `_loading_text`. Cutting less keeps more text, which can only widen the selection. Hermetic cases cover a pyproject `x = "a # b GUIDE.md"` and a Makefile recipe `grep -c '#' GUIDE.md`; both give FULL `unanalysable`.
- **F-004.** The refusal detail now names the rule that refused the file: "a root-level file|dotfile no ROOT_FILE_CLASSES class admits; a tool (git, node, alembic, a package manager) may read it by location...". The rule id stays `outside-known-roots`, so the gate behaves as before (G-2). The cannot-model cases assert `ROOT_FILE_CLASSES` in the detail.
- **New, found while re-deriving.** With the less aggressive comment stripping, `scripts/impact_set.py` (which is in UNANALYSABLE) now named `Dockerfile`, `Procfile`, `render.yaml`, `railway.json` and `runtime.txt` through its own class table, which turned them FULL `unanalysable`. `_unanalysable_namer` now skips the selector itself. The names in its class table are names to match, not files it opens; the only root files it opens are the UNANALYSABLE entries, which are FULL anyway. The hermetic test copies the real selector into the fake tree; control C9 below covers this. A side effect, which only widens the selection: the selector still names these files as a `scripts/` referencer, so their selection includes the tests that name `scripts/impact_set.py` (5 extra files).
- **F-005.** No change, by the reviewer's ruling. Helper docstrings that mention CLAUDE.md lift 4 of the 6 `wave_close_only` files on a CLAUDE.md gate. This only widens the run.

**Root files, re-derived on the final tree** (34 tracked root files plus one untracked probe):

| Result | Files |
|---|---|
| Selection of 105 test files | CLAUDE.md |
| Selection of 211 | README.md |
| Selection of 51 | render.yaml |
| Selection of 48 | Dockerfile, Procfile, railway.json, runtime.txt |
| Selection of 45 | nonogram_admin.db, start.sh |
| Selection of 43 | ADMIN_SETUP.md, docker-compose.yml |
| FULL `outside-known-roots` | 5 dotfiles, alembic.ini |
| FULL `unanalysable` | Makefile, pyproject.toml, requirements.txt |
| FULL `no-reader` | 14 tracked `.md` files, plus the untracked `UNTRACKED_PROBE_528.md` |

Procfile, railway.json and runtime.txt are read by no test. Their 48 files are the always-on scanners plus the selector's own tests (the referencer side effect above).

**AC-3, re-derived:** the same sample as before (97 KNOWN_ROOTS paths from `git log main --merges -40`, each run singly, plus the 97 as one set). `34c94756`'s script and the final script were run against the final tree: 98 of 98 identical.
**Net count:** 10695 at the base, 10707 now. That is +12 for the card, +7 this round. The cannot-model test went from 4 to 7 cases (`.toolrc` became `.notes.md`, and `package.json` plus two `#` cases were added); the selects test went from 1 to 5 cases.

**Controls** (`/private/tmp/claude-501/card528/controls2.py`): each mutant was run against the class's 16 tests, then the file was restored, and `git diff --stat` was the same afterwards. All 23 went red:
- C1, root branch admits nothing: 10 red, `assert ['outside-known-roots'] == ['no-reader']`.
- C2a, dotfile refusal removed: `[.notes.md]` red, `assert derived.full`.
- C2b, `*.json` admitted: `[package.json]` red, `assert derived.full`.
- C2c, `*.ini` admitted: `[tool.ini]` red, `assert derived.full`.
- C3, the namer returns None: 3 GUIDE.md cases red, `assert derived.full`.
- C4, root walkers not added: 5 red, `assert 'tests/test_root_walker.py' in [...]`.
- C4h, helper following removed: `[Procfile]` red, same assert.
- C5, loader importers dropped: 5 red, `assert 'tests/test_imports_lonely.py' in [...]`.
- C6, comment stripping removed: 6 red, `assert 'FULL' != 'FULL'` (including the real CLAUDE.md test).
- C6q, naive `split("#")` restored: the quoted-`#` and Makefile-recipe cases red, `assert derived.full`.
- C7, no-reader FULL dropped: `[NOTES.md]` red.
- C8, detail without the rule name: 3 red, `assert 'ROOT_FILE_CLASSES' in '...'`.
- C9, self-skip removed: `[Dockerfile]` and `[Procfile]` red, `assert 'FULL' != 'FULL'`.
- One per class, its glob removed: prose 6 red; container, hosting, shell and database each red in their own case, `assert 'FULL' != 'FULL'`.
- One per `ROOT_WALK_IDIOMS` regex, removed: each idiom's own case red, `assert 'tests/test_root_walker.py' in [...]`.

**Gate:** `tests/test_impact_set.py` and `tests/test_wave_close_marker.py`, unarmed, with `-rfs`: 231 passed, 0 failed, 0 skipped.

[Review 2/3] Score: 8.5, one gating finding, not certified. Re-derived: 231 passed, 0 skipped; test_impact_set.py 200 -> 212; AC-3 on a different sample (merges 41-80, 111 KNOWN_ROOTS paths singly plus the set) 112/112 identical; 9 controls red at their cases; 79 non-literal root joins traced by ast, none reaching an admitted-class file; the prose, container, shell, database and hosting classes judged honest. Cycle-1 F-001, F-002, F-004 closed; F-003 closed for the reported cases. F-101 (Important, G-1/AC-2): the self-skip is in `_unanalysable_namer` but not `_referencers`, which finds the class table's literals in scripts/impact_set.py and counts the selector as a loader, so railway.json and runtime.txt (FULL no-reader in cycle 1) and a new app.json or compose.yml narrow to 48 files with no real reader; unpinned, all 212 tests stay green with `_referencers` skipping the selector. F-103 (minor): widening the self-skip to every .py owner, or cutting the owner loop to pyproject.toml and Makefile, survives every test. F-102 (low): `_strip_hash_comment` ignores backslash escapes and multi-line TOML strings.

### Fix round 2 (review 2, 2026-11-23)

**Correction to round 1.** Round 1 said the selector being counted as a `scripts/` referencer was a side effect that "only widens". That was wrong. For railway.json and runtime.txt, the selector's own class table was the only "reader", so the side effect turned FULL `no-reader` into a 48-file selection with no real reader. A new app.json or compose.yml would have done the same. This broke AC-2 and G-1 (F-101).

- **F-101.** New constant `NAME_TABLE_OWNERS = ("scripts/impact_set.py",)`. It is the one exemption, shared by both places that need it:
  - `_unanalysable_namer` skips `owner in NAME_TABLE_OWNERS`;
  - `_referencers` takes a `skip` argument, and `_derive_root_file` passes `skip=NAME_TABLE_OWNERS`.

  Asset derivation under the roots calls `_referencers` without `skip`, so it is unchanged (AC-3 below). New hermetic case: the real selector is copied into the fake repo, and a test there names the selector, as on the real tree. `runtime.txt`, spelled only in that copy, gives FULL `no-reader`.
  - The case builds its file names from pieces (`"runtime" + ".txt"`, `"Proc" + "file"`), so `tests/test_impact_set.py`, an always-on scanner, does not itself "name" the repo's real runtime.txt or Procfile. Before I did this, its fixture strings made both select 43 files.
- **F-103.** New cannot-model cases where `tests/conftest.py` and `setup.py` (the two UNANALYSABLE Python owners besides the selector) name `GUIDE.md`. Both give FULL `unanalysable`, with the owner named in the detail.
- **F-102.** `_strip_hash_comment` (one line at a time) is replaced by `_strip_hash_comments`, which works on the whole text:
  - a backslash inside `"` or `"""` escapes the next character;
  - `"""` and `'''` strings run across lines, and nothing inside them is cut;
  - a single-line quote left open at a newline closes there;
  - an unclosed triple quote keeps the rest of the file, so every doubtful case keeps text.

  New hermetic cases `x = "say \" # GUIDE.md"` and `x = """` / `# GUIDE.md` / `"""` both give FULL `unanalysable`.

**Root files, re-derived on the final tree** (34 tracked plus one untracked probe):

| Result | Files |
|---|---|
| Selection of 105 test files | CLAUDE.md |
| Selection of 211 | README.md |
| Selection of 46 | render.yaml |
| Selection of 45 | nonogram_admin.db, start.sh |
| Selection of 43 | ADMIN_SETUP.md, Dockerfile, docker-compose.yml (always-on scanners only; they are the namers) |
| FULL `outside-known-roots` | 5 dotfiles, alembic.ini |
| FULL `unanalysable` | Makefile, pyproject.toml, requirements.txt |
| FULL `no-reader` | Procfile, railway.json, runtime.txt, 14 tracked `.md` files, the untracked probe |

Files that do not exist on the tree: package.json, tsconfig.json and package-lock.json give FULL `outside-known-roots`; app.json and compose.yml give FULL `no-reader`.

**AC-3:** same sample as before, the 97 KNOWN_ROOTS paths from `git log main --merges -40`, each run singly plus all 97 as one set. Comparing `34c94756`'s script with the final script on the final tree: 98/98 identical.
**Net count:** 10695 at the base, 10712 now. That is +17 for the card, +5 this round: the cannot-model test went from 7 to 12 cases.

**Controls** (`/private/tmp/claude-501/card528/controls2.py`, output in `/private/tmp/claude-501/card528/controls6.out`). Each mutant was run against the class's 21 tests, then the file was restored, and `git diff --stat` was the same afterwards. All 28 went red. The new ones:
- C10, `_referencers` skip removed: `[runtime.txt]` red at `assert derived.full`.
- C11, self-skip widened to `owner.endswith('.py')`: the conftest and setup.py cases red at `assert derived.full`.
- C12, owner loop cut to pyproject.toml and Makefile: the same 2 cases red.
- C13, backslash escape ignored: the escaped-quote case red.
- C14, triple quotes ignored: the multi-line case red.
- C9, unanalysable self-skip removed: 3 red, including `[runtime.txt]` with `assert ['unanalysable'] == ['no-reader']`.

C1 to C8, the 5 class controls and the 5 idiom controls are all still red.

**Gate:** `tests/test_impact_set.py` and `tests/test_wave_close_marker.py`, unarmed, with `-rfs`: 236 passed, 0 failed, 0 skipped.
