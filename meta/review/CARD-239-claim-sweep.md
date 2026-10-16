# CARD-239 — claim sweep

**AC-7.** Every claim this card writes or leaves standing about what is caught,
reported or seen, either **PINNED** by a named control that can fail,
**DELETED**, or **RECORDED** as a bound with the control that keeps the bound
honest. Format copied from `meta/review/CARD-238-cycle5-claim-sweep.md`, which
is the cycle that worked.

Written 2026-10-17, against the worktree at `card/239-timing-guard-bounds`.
Every "measured" below is a figure this sweep produced by executing something,
not by reading code. Mutant verdicts all come from a **fresh `pytest` process
per mutant**, with the mutated file restored from a byte copy and the md5
verified — this project's review station measured on 2026-10-16 that several
mutants run from one parent process produce false KILLED verdicts.

| counts | |
| --- | --- |
| PINNED | 33 |
| DELETED | 6 |
| RECORDED as a bound, with a control | 7 |
| **found false on measurement during the sweep** | **5** |
| `[BLOCKER]` | 0 |

The five found false are rows **A-9**, **B-4**, **D-2**, **D-4** and **F-13**.
Two are mine, written in this pass (B-4, D-4) and both were caught by controls
this card wrote rather than by a reviewer; three are survivors of CARD-238's
own sweep (A-9, D-2, F-13).

---

## A. The construction spellings (F-501, AC-1)

| # | claim | verdict |
| --- | --- | --- |
| A-1 | "every path-construction spelling the library offers sits in a guard set or in an exclusion carrying a reason" | **PINNED** — `test_every_construction_spelling_is_classified`. Non-vacuous by measurement: with `with_segments` moved back into the pure-arithmetic exclusion the test is red naming it (`['with_segments (base.with_segments(*components))']`), and the module goes 3 failed / 350 passed. Restored from a byte copy, md5 `23275e1fd73f610421a2a8ed661c8023` verified. |
| A-2 | "which spellings build a path is measured, not judged" | **PINNED** — the same test calls every public callable the probed namespaces offer on a base and two components and reads the result. Seven builders measured: `Path`, `PosixPath`, `PurePath`, `PurePosixPath`, `join`, `joinpath`, `with_segments`. |
| A-3 | "the probe cannot pass by finding nothing" | **PINNED** — two non-vacuity assertions inside it (`len(builders) >= 5`, and `join`/`joinpath` present), so a probe that swallowed every exception would be red rather than green. |
| A-4 | "a KIND_JOINER member that builds nothing is red" | **PINNED** — the `idle` half of the same test; this is the F-403 direction (a set declaring a width no control can fail on). |
| A-5 | "the four join forms CARD-238 measured as missed are now caught" | **PINNED** — four entries in `REINTRODUCTIONS`, each measured `[]` before and `['listdir() of meta/kanban']` / `['iterdir() of meta/kanban']` after. Four more forms nobody had listed are caught too and have controls: `Path(ROOT, "meta", "kanban")`, `with_segments`, `os.sep.join([...])`, and a glob under a joined directory. |
| A-6 | "each joiner control is caught WITH its set member and missed WITHOUT it" | **PINNED** — `test_the_control_for_each_spelling_depends_on_the_set`, parametrised over `_LISTERS | _GLOBBERS | _JOINERS`. This is why the joiner controls name no log: the two `os.path.join`/`joinpath` entries that were already in `REINTRODUCTIONS` are caught through their log *filename*, so they measured nothing about the construction spelling — the F-403 shape one layer out. |
| A-7 | `_live_log_references`' "a listing of that directory by any spelling `STDLIB_DIRECTORY_SURFACE` classifies as one" | **DELETED and replaced.** It was true of readers and false of builders. The replacement names both halves and quotes the four forms that used to return `[]`. |
| A-8 | "`os.path.join`'s receiver is not a path component" | **PINNED** — `_PATH_METHOD_JOINERS`, derived from the surface's own namespace labels (`dir(pathlib.Path)` offers `joinpath`, `dir(os.path)` offers `join`). Measured, not reasoned: prepending every attribute joiner's receiver made `os.path` itself a component and the glob control went red. |
| A-9 | `NOT_A_PATH_WRAPPER`'s "each of these is a measured miss *because* the name is classified KIND_NEITHER; let one into the set and the control goes red" | ⚠ **FOUND FALSE on measurement — a cycle-5 survivor.** True of 1 of 3. `KANBAN.joinpath("cards")` and `KANBAN.with_name("profiling")` are one-*argument* attribute calls, so the peel's one-argument branch takes the string `"cards"` and its no-argument branch does not apply: adding either name to `_PATH_WRAPPERS` changes nothing. Verified false on CARD-238 as merged as well, so this card did not break it. Corrected three ways: the sentence is rewritten to what holds; `NON_WRAPPERS_THE_SET_DECIDES = ("dirname",)` records which one the set decides, as an **equality** that goes red if the peel grows; and the discriminating power the sentence claimed is now supplied by `test_a_path_arithmetic_name_is_peeled_only_if_it_is_in_the_set`, generated from the table over all 18 path-arithmetic names in both wrapper shapes — 36 controls, each asserting the name is NOT peeled and WOULD be if it were in the set. |
| A-10 | "the sets are the audited table's projection and cannot be hand-edited" | **PINNED** — `test_the_guard_sets_are_derived_and_not_hand_written` reads this module's own source with `ast` and is red if any of the five assignments becomes a literal. It was red on its first run, at `_HOST_STATE_PROBES`, which was still a hand-written frozenset — so the test found the fifth set before the author did. |
| A-11 | "`test_the_listing_sets_are_exactly_the_classified_spellings` bounds the sets" | **DELETED as stated.** With derived sets that equality holds by construction. The claim is replaced by A-10, which can fail; the equality itself stays (G-2: nothing removed) with its standing written down as "cannot fail while the sets are derived at all". |

## B. The version-gated members (F-502, AC-3)

| # | claim | verdict |
| --- | --- | --- |
| B-1 | "the module is green on an interpreter lacking `glob0`, `glob1`, `is_junction`, `isjunction`, `isdevdrive`" | **PINNED by demonstration, not by reasoning** — a pytest plugin deletes exactly those five attributes before collection. Before: **1 failed, 340 passed**, at `test_a_spelling_the_guards_use_is_a_real_stdlib_name`, naming exactly the five. After: **388 passed, 0 failed** across both guard modules. The plugin lives outside the repository (scratchpad) and is not committed. |
| B-2 | "a spelling nobody can write cannot be a hole" | **PINNED** — `_guard_set` intersects each projection with the live surface, and `test_the_listing_sets_are_exactly_the_classified_spellings` compares against `_guard_set`, not `_classified`. |
| B-3 | "a typo in the table is still reported" | **PINNED** — `test_a_spelling_the_guards_use_is_a_real_stdlib_name`, restated as a **subset** claim against `PLATFORM_GATED_SPELLINGS`. An invented `listdirs` is red; a 3.9 run is green. The subset direction is the only one that can hold on every host, and the benign direction is stated as not claimed rather than implied. |
| B-4 | `PLATFORM_GATED_SPELLINGS` "is not a dumping ground" | **PINNED** — the same test asserts every entry carries a reason and names something the table classifies. It was red on its first run at `info`, an entry the author had invented (`Path.info` is a property, not a callable, so it is not on the surface at all). My own pass, caught by my own control. |
| B-5 | "a control for a spelling this host lacks is not collected rather than skipped" | **PINNED** — `REINTRODUCTIONS_ON_THIS_HOST`, filtered by `_needs_a_spelling_this_host_lacks`, and measured under the deletion plugin: the three affected controls disappear and nothing goes quiet. |
| B-6 | "the floor is declared in exactly one place" | **PINNED** — `test_the_floor_is_declared_in_pyproject_and_followed_by_the_guidance` and `test_the_pypi_classifier_states_the_same_floor`. Red before the change (`pyproject.toml declares requires-python >= 3.9 and CLAUDE.md's setup uses [(3, 14)]`). **pyproject.toml is authoritative**; CLAUDE.md and the PyPI classifier follow it. The classifier was a *third* statement of the floor (`Python :: 3.9+`) that the card had not noticed. |

## C. The compound mutant (AC-2)

| # | claim | verdict |
| --- | --- | --- |
| C-1 | "the surviving compound mutant from CARD-238's cycle 5 is caught" | **PINNED by a planted-and-reverted mutant.** Shape: `os.path.join` construction of the kanban directory, `os.listdir` filtered to `*.log`, the read wrapped in `try/except (FileNotFoundError, IndexError)` with `pytest.skip`, naming no log, planted in `tests/test_clues.py`. **Pre-fix** (CARD-238 as merged, both files restored from `git show HEAD:`): **341 passed, rc=0** — the whole guard module green. **Post-fix: 2 failed / 400 passed**, `tests/test_clues.py` restored, md5 `942627df2b6df5a003bf52775ab1d398` verified. |
| C-2 | "which guard halves fire" | **MEASURED, and one of them does not.** The path guard fires: `{'tests/test_clues.py': ['listdir() of meta/kanban']}`. The behavioural comparison fires transitively (`{'FAILED', 'PASSED'} != {'PASSED'}`). The **silence half does not** — the skip is reached from an `except` handler and every rule in `_conditional_silences` reads conditions. That is CARD-238's recorded except-handler bound, pinned in `NOT_A_CONDITIONAL_SILENCE`, and it is stated here rather than rounded up to "caught by both halves". |
| C-3 | the card's "survives end to end at 250 passed" | **MY MEASUREMENT DIFFERS, and the conclusion does not.** Running the whole module against CARD-238 as merged with the mutant planted gives **341 passed, rc=0**, not 250 — 341 is what that module collects, so the mutant survives *every* test in it. 250 was presumably a narrower selection in the cycle-5 worktree. Function-level, pre-fix: `_live_log_references` → `[]` **and** `_conditional_silences` → `[]`, i.e. both halves blind, which is the part that matters. |
| C-4 | "the mutant's own verdict is the CARD-234/CARD-235 flip" | **PINNED by measurement** — on this log-less worktree the planted test reports **`1 skipped`**, rc=0. |

## D. The second guard module (F-308, AC-4)

| # | claim | verdict |
| --- | --- | --- |
| D-1 | "a module-scope `pytest.skip(..., allow_module_level=True)` in the guard module is reported" | **PINNED by a planted mutant, killed by both mechanisms.** Planted the log-keyed form verbatim. Import probe: `importing test_suite_profile.py did not finish: Skipped: no timing log on this host`. AST rule: `('tests/test_suite_profile.py', 'skip() at module scope', "not (REPO_ROOT / 'meta' / 'kanban' / 'suite-timing.log').exists()")`. **2 failed, 40 passed, 1 skipped.** Restored, md5 verified. |
| D-2 | "pytest reports `found no collectors` for both guard classes" (carried from CARD-238) | ⚠ **not what this host reports.** Measured: the silenced module reports **`1 skipped in 0.03s`, rc=0** — 398 guards gone, run green. The sentence is **DELETED** and replaced with that measurement. Same defect, different presentation; the claim as written could not be reproduced. |
| D-3 | "the two modules judge each other, so neither is its own judge" | **PINNED in both directions by two mutants.** The other direction: a module-scope skip planted in `tests/test_guard_integrity.py` makes `test_the_host_state_silences_elsewhere_are_exactly_the_measured_ones` red, naming `('tests/test_guard_integrity.py', '<module>', "not (REPO_ROOT / 'meta' / 'design').is_dir()")`. Restored, md5 `5631a73e0bf2dd713ba6ed7eca0f7a06` verified. |
| D-4 | `_MODULE_SCOPE_SILENCERS`' first draft, `{skip, exit, importorskip, xfail, fail, skip_module}` | ⚠ **FOUND FALSE on measurement, in my own pass.** `test_every_silencer_it_names_has_a_control` was red at `['fail', 'skip_module', 'xfail']`. **`skip_module` does not exist in pytest at all** — a member nobody can write, which is the F-403 shape and exactly what CARD-238's cycle 4 shipped. `fail` is not a silencer either: at module scope it raises during collection, which pytest reports as an **error** — loud, which is the opposite of what makes a silence dangerous. Both **DELETED**, with the reason written into the set's comment; `xfail` kept and given a control. |
| D-5 | "every silencer the rule names has a control, and each control depends on the membership" | **PINNED** — `test_every_silencer_it_names_has_a_control` and `test_the_control_for_each_silencer_depends_on_the_set`, the CARD-238 pattern, parametrised from the set itself. |
| D-6 | "the module-scope rule is default-deny" | **PINNED** — nine positive controls including three idioms nobody in this tree writes (`importorskip`, `xfail`, `sys.exit`), six negative controls, and the baseline is an **equality against an empty tuple**, so a new module-scope silence anywhere under the guarded trees is red rather than unnoticed. The completeness claim is carried by the rule's shape, not by the list: nothing enumerates the ways a module can go quiet, so what is enumerated is what is *allowed*. |
| D-7 | "the `if __name__ == '__main__':` exemption is not borrowable" | **PINNED** — `test_the_main_guard_exemption_is_keyed_on_the_guard_and_not_on_exit`: the same `sys.exit(0)` one indentation level out is reported. The exemption exists because the rule found two real files, `tests/integration_tests.py` and `tests/fixtures/a4_golden/regenerate.py`, which call `sys.exit` under that guard — pytest imports a module under its own name, so that branch never runs. |
| D-8 | "the independent mechanism is independent" | **PINNED by construction and stated** — the import probe needs no parser, the AST rule is written in this module and imports nothing from the module it judges. A guard that consulted the other module's detector would be silenced by the same edit; that is the reason, and it is in the docstring. |

## E. The deliberate reader (AC-6)

| # | claim | verdict |
| --- | --- | --- |
| E-1 | "`--check-log` reports malformed lines and exits non-zero on finding one" | **PINNED** — `TestCheckLog_TheDeliberateReader`, seven tests over logs the tests construct, including CARD-217's real bare-trailing-note line (named and `status == 1`) and the same sentence parenthesised (`status == 0`). |
| E-2 | "it answers the rate-recovery question in the place that reads the log for real" | **PINNED** — `test_it_reports_how_many_rated_lines_give_their_rate_back` and, for non-vacuity, `test_a_rated_line_that_does_not_parse_is_counted_as_a_loss` (`rate recovered: 0 of 1`), so the two counters cannot be measuring the same thing twice. |
| E-3 | "no test invokes the subcommand" | **PINNED** — `test_no_guarded_source_invokes_the_check_log_subcommand` over every `*.py` under `tests/` and `meta/profiling/`, with four fabricated positive controls (a subprocess argv, `main([...])`, a shell string, an argv list) and one negative (the `add_argument` registration). The exemption is keyed on **shape**, not on a filename, and has its own control (`test_the_definition_shape_is_not_an_invocation`) — a filename exemption would be inherited by any test added to the ranker tomorrow. |
| E-4 | "the suite does not depend on it" | **PINNED** — E-3, plus `check_log_report` taking the log's *text* rather than a path, so nothing in the suite can reach a file through it. |
| E-5 | "the subcommand is wired to that function" | **RECORDED as a bound.** AC-6 forbids a test invoking the subcommand, so the three lines of argparse wiring are asserted **structurally** (`test_the_subcommand_is_wired_to_that_function`: the option is registered exactly once, with `default=None`, and `check_log_report` is called exactly once in `main`) and are **not executed by any test**. A rename that left the option pointing at nothing is red; a logic error inside those three lines is not. The limit is in the test's own comment. |
| E-6 | "`--check-log` has no default path" | **PINNED** — the same test asserts `default=None` in the registration. This is not cosmetic: a default would put the owner's gitignored log's path into `meta/profiling/rank_durations.py`, which is one of the two territories the AC-1 guard walks — review cycle 2's MUT-R verbatim. |
| E-7 | "it never writes" | **RECORDED, not pinned.** `check_log_report` takes a string and `main`'s branch calls `read_text`; there is no write to assert the absence of. Verified by reading the three lines and by G-1's md5 check below, which is the measurement that matters. |

## F. The bounds and inaccuracies (part 3)

| # | claim | verdict |
| --- | --- | --- |
| F-1 | F-306: "a stray `.card238-tracked` at the repo root cannot decide the verdict" | **PINNED** — `test_a_manifest_at_the_repo_root_is_ignored`, both directions, on a root the test owns (the untrusted root is a parameter precisely so that measuring it does not mean writing a gitignored file into the owner's checkout). Plus the `.gitignore` entry, with the reason. |
| F-2 | AC-5: "the two genuine host-state silences are fixed and struck" | **PINNED** — `test_the_host_state_silences_elsewhere_are_exactly_the_measured_ones` was measured red with them fixed and unstruck, in two steps (one entry at a time), before they were struck. They were skips keyed on the presence of the **committed** 25-picture corpus, in a module that asserts that corpus is exactly 25 files unconditionally a thousand lines above — so they contradicted their own module. |
| F-3 | "the detector would still report those shapes if they came back" | **PINNED** — `test_a_silence_this_card_fixed_is_still_one_the_detector_would_report`, generated from `SILENCES_FIXED_BY_CARD_239` in the in-body form, where the *condition* has to be recognised as host state. Without it, striking an entry would leave the shape unexercised. |
| F-4 | F-405: the baseline header's "Every **host-state** silence" and "These **three**" over four entries | **DELETED and rewritten.** The header now says what the detector reports (it is wider than host state in its mark half), carries no count, and says why the third remaining entry is recorded rather than fixed. |
| F-5 | "the third recorded silence is not fixed, and that is a decision" | **RECORDED** — `tests/test_admin_design_tokens.py`'s `not _DESIGN.exists()`. Its reason is about *packaging* (`meta/design/` is not shipped with the wheel), not about this host, and the question it raises — whether the admin panel's token mirror should be checked against a directory the package does not ship — belongs to forge:ui's card. The reason is corrected in the baseline; it was filed alongside two entries it is not the same shape as. |
| F-6 | the module docstring's "331 tests" over a 341-test module | **DELETED**, not updated — a count in prose cannot go red, `--collect-only -q` answers it in a second, and this is the one row of CARD-238's own sweep that was found wrong on measurement. The per-cycle test counts in the same paragraph are deleted with it; the dated cost figures stay, because a dated observation is not a standing claim. |
| F-7 | `popen` under "it names no directory" and `system` under "not the filesystem" | **DELETED and rewritten.** Both are false of `os.popen("ls " + str(KANBAN))`. The honest reason — these rules do not read command text — is now their classification, and it is **PINNED from the other side** by two new `MEASURED_STRUCTURAL_MISSES` entries (the `os.popen` and `subprocess` shell-outs), so the non-claim goes red the day a rule here starts reading argv. |
| F-8 | `subprocess` "is outside the audited namespaces" | **RECORDED as an explicit non-claim with a control.** The namespace list is not widened: `dir(subprocess)` would add thirty names whose classification nothing could measure either. Shelling out to list a directory is **this module's own idiom** (six `git ls-files` listings behind `_files_under_guard`), and the bound is a control rather than a sentence. |
| F-9 | `_unwrapped` peels only single-argument calls, so `os.path.relpath(KANBAN, REPO_ROOT)` is unseen | **RECORDED as a bound with a control** — a new `MEASURED_STRUCTURAL_MISSES` entry, red the day the peel grows. Not fixed, and the reason is measured rather than preferred: widening the peel to "the first argument of any arity" hands `Path(ROOT, "meta", "kanban")` to the listing rule as `ROOT`. The constructor half of the problem is fixed instead, by `_component_arguments`. |
| F-10 | the meta-guard's `setattr` on module globals | **FIXED, and the reason is labelled REASONED rather than measured.** The sets are a defaulted `Spellings` parameter now. Neither `pytest-xdist` nor `pytest-randomly` is in the dependency baseline, so the interleaving cannot be demonstrated here, and the docstring says so instead of implying a measurement. The same defect in the new module's own meta-guard was caught by this row and fixed the same way. |
| F-11 | doc drift, `tests/README.md` | **FIXED** — the parenthesised-trailing-note form is documented with an example, the bare form is documented as rejected with the writer named, and the `--check-log` invocation is shown. |
| F-13 | `_looks_like_an_entry`'s "optionally followed by a single ` [<N>ms/test]` and nothing else" | ⚠ **FOUND FALSE on measurement — another cycle-1 survivor.** The independent validator takes the note's span to the **last** `)` in the line, so it also accepts a parenthesised note after the rate bracket. The grammar in its docstring understated what it accepts, which matters because that function is the second implementation the regex is played off against. Corrected in place, with the route named and with the one thing that *is* still rejected (a bare trailing note) stated. No behaviour change: `test_the_parser_agrees_with_an_independent_validator` was green before and after, which is the point — the two agreed by two different routes and only the description was wrong. |
| F-12 | doc drift, `skills/kanban/references/cmd-run.md` | **RAISED, not fixed.** It lives in `~/MyProjects/forge_1`, outside this repository, and G-5 forbids editing the owner's forge skills. It is the one place the dispatcher actually reads at a merge gate, and it still documents only the bracket-terminated form — so the next bare-trailing-prose line is still unprevented there. In the worktree notes. |

## G. The non-claims, stated because they are the thing this card is about

| # | non-claim | the control that proves it is open |
| --- | --- | --- |
| G-1 | A builder living only in the top-level `os` namespace would not be found by the behavioural probe. | `_PROBED_NAMESPACES` excludes `os`, **by measurement**: probing it made `os.popen("base", "meta", "kanban")` fork a shell (`DeprecationWarning: This process is multi-threaded, use of fork()`). Such a name would still have to be classified with a reason — `test_every_spelling_the_stdlib_offers_is_classified` is red on an unclassified name in any namespace — so what is lost is the behavioural second opinion on that classification, not the default-deny. |
| G-2 | The surface is the *running* interpreter's. | Carried from CARD-238, unchanged: a platform offering a name this host does not makes the completeness audit red until it is classified, which is the audit working. |
| G-3 | The except-handler skip is not reported by the silence detector. | `NOT_A_CONDITIONAL_SILENCE`'s entry, and C-2's measurement of the compound mutant. |
| G-4 | The env-var path with no literal in the source survives both halves. | CARD-238's recorded survivor, re-stated and untouched here; its failure mode is loud (an unset variable fails rather than skips). Not re-measured by this card. |
| G-5 | `os.path.relpath(KANBAN, REPO_ROOT)` is unseen. | F-9's control. |
| G-6 | Shelling out to list the directory is unseen, by `os.popen`, `os.system` or `subprocess`. | F-7's and F-8's controls. |
| G-7 | The three argparse lines wiring `--check-log` are not executed by any test. | E-5. |

## H. Guardrails

| G | verdict |
| --- | --- |
| G-1 (do not touch `meta/kanban/suite-timing.log`) | **HELD.** The worktree has no such file (gitignored, fresh checkout) and nothing in this card creates one. The main repository's log: md5 verified unchanged at the end of the card — see the worktree notes. `--check-log` only ever calls `read_text`. |
| G-2 (coverage up, not down) | **HELD, measured.** `tests/test_suite_profile.py` **341 → 398** collected; **zero** test functions removed, verified by `ast`-diffing the function names against `git show HEAD:` (7 added, 0 gone). Two tests' *claims* were restated in place (A-11, A-9); neither was deleted. New module `tests/test_guard_integrity.py`, **42** collected. Total **440**. |
| G-3 (the parser's accepted language does not change) | **HELD, and by construction:** `TIMING_LOG_LINE` is byte-identical. The only change to `meta/profiling/rank_durations.py` is additive — a new `_RATE_BRACKET` pattern, a new `check_log_report`, and the argparse wiring — so the 40,214-line identity CARD-238 established is untouched rather than re-measured. |
| G-4 (do not weaken the audit to make a member fit) | **HELD.** Three names moved into a *new* kind with a measured reason, two had their reason corrected, and nothing was moved into KIND_NEITHER to make a test pass. The one place a member was removed from a set — `skip_module` and `fail`, in the new module — is D-4, where the member was measured not to exist and not to silence. |
| G-5 (`cmd-run.md` is outside this repository) | **HELD.** Not touched; raised instead (F-12). |
| G-6 (no `src/**` change, no new runtime dependency) | **HELD.** `src/**` untouched; the only `pyproject.toml` changes are `requires-python` and a classifier. New imports are stdlib only (`typing.NamedTuple` in the guard module; `ast`, `importlib.util`, `re`, `sys`, `tomllib`, `pathlib`, `types` in the new one). |
