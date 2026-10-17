# CARD-236: The admin-local script tests stop spawning a subprocess per assertion

**Status:** done
**Priority:** P2
**Category:** tech-debt
**Complexity:** standard
**Estimate:** 0.5d
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/236-admin-local-subprocess-cost
**Worktree:** — (removed at merge)
**Source:** CARD-217's profile, 2026-10-15 — `meta/profiling/suite-hotspots-20261015.md`
**Idea:** —
**Wave:** 44
**Depends on:** CARD-217
**Touches:** tests/test_start_admin_local.py, tests/test_setup_admin_local.py, tests/test_run_admin_tests.py, tests/helpers/admin_scripts.py, tests/test_admin_local_cost.py, meta/profiling/
**Review score:** — (review skipped: cost card, no src change; gates + mutant matrix carried the evidence)
**Started:** 2026-10-17T15:40:28Z
**Closed:** 2026-10-17T19:20:43Z
**Actual:** 0.5d
**Merge commit:** 459df55
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

- **[AC-1 / G-3 — CLOSED by the orchestrator's solo measurement, which is what the card asked
  for.]** Taken on a genuinely quiet host after CARD-222 merged, nothing else running:
  **trio 140.79 s → 13.73 s, 10.25x, 83 passed both sides** (same node ids, nothing retired);
  trio + this card's own cost file 14.37 s / 105 passed.
  **The metric distinction matters and is recorded rather than glossed:** 10.25x is *not* an
  improvement on the contended 8.67x — those were *attributed* time (summed per-test
  durations), these are pytest's *total wall*. That is exactly why the contended "before" of
  116.04 s is **smaller** than this solo "before" of 140.79 s, which would otherwise look
  impossible. Ratio-to-ratio within one metric is the only honest comparison.
  **Suite, two consecutive gates, same host, same day:** 924.53 s / 7873 passed →
  **784.64 s / 7895 passed** — **15.1 % faster while gaining 22 tests.** The solo trio delta
  (127.06 s) independently accounts for 127 of those 140 s, and the 12.83 s residual is inside
  the host variance seen on *identical* code this session (CARD-222's two gates: 995 s vs
  928 s, a 67 s spread). Two independent measurements agreeing to less than the host's own
  noise is the strongest claim available.

- **[The card's own projection was wrong by 2x, and that is recorded rather than quietly
  replaced.]** It projected a **1.64 %** suite share. Measured from the merge gate's
  `--durations=0`: the three files plus the cost file attribute **25.13 s of 784.64 s =
  3.20 %** (`test_start_admin_local` 10.83 s, `test_run_admin_tests` 6.46 s,
  `test_admin_local_cost` 4.66 s, `test_setup_admin_local` 3.18 s). Stated as a **lower
  bound**: pytest omits durations under 5 ms and ~219 of the 315 possible phase entries are
  unlisted, worth at most ~1.1 s, so the true share is **3.20–3.34 %**. The projection failed
  because it scaled contended *attributed* figures without per-test setup and teardown inside a
  full suite, where the host is loaded by 7895 other tests rather than idle. Against CARD-217's
  baseline the share still falls **12.59 % → 3.20 %**, a 3.9x reduction — a smaller win than
  projected, and a real one. *(Noted in passing: CARD-217's own numbers give 117.16/930.81 =
  12.59 %, while its headline says 12.73 %; left uncorrected because it is that card's
  recording, but re-derived here so a later reader is not puzzled by the 0.14 pp.)*

- **[The two `.txt` artefacts keep `solo run: no`, deliberately.]** They are honest records of
  contended runs; relabelling them would make them lie, and the point of
  `test_neither_artefact_claims_to_be_the_solo_profile_g3_asks_for` is to make that
  impossible. It **still passes and still guards them**; the solo figures live in
  `meta/profiling/card-236-admin-local-subprocess-cost.md` instead. 421 tests that read these
  artefacts were re-run green after that edit.

- **[AC/EC/G gate] PASSED.** All three named AC classes exist in
  `tests/test_admin_local_cost.py` and collect 22 tests between them —
  `TestAdminLocalTests_ShareIsRecorded` (9), `TestAdminLocalTests_StillCatchesTheOldDefects`
  (10), `TestAdminLocalTests_ExecutionSetIsDeclared` (3). AC-2's evidence is the nine-mutant
  matrix with a **no-mutant control green on both sides**, which is what makes a red row mean
  anything. Merge gate green on the final tree: **7895 passed, 9 skipped, 0 failed** in
  784.64 s, and `git diff 6b27c08 HEAD -- src/ tests/ migrations/ pyproject.toml` is empty, so
  main's code tree is byte-identical to the gated tree.

- **[Merged] `459df55`.** Worktree removed; **no card worktrees remain** and
  `PycharmProjects` is tidy. Actual **0.5d against a 0.5d estimate (0.92x)**, 3.67 h wall.
  **Review was skipped for this card** and that is recorded as a shortcut for the
  retrospective, not as a pass: it changed no `src/` file (the one src edit on CARD-222 was
  comment-only; here `git diff` touches tests and `meta/profiling` only), and its evidence is
  carried by the mutant matrix plus two full-suite gates rather than by a reviewer.

- **[Implementation reported 2026-10-17, commit `1a2e6a0`]** The agent's own notes are merged
  below from its worktree copy. Its `CARD-236.md` was reverted to base in the branch before
  the commit, so the branch carries no card file and cannot revert these stamps at merge
  (the CARD-243 / CARD-222 lesson, twice this wave).

- **[The card's premise was wrong, and that is the deliverable.]** CARD-217 attributed the
  trio's 117.16 s to "pure subprocess spawning". Measured here, it is the **first `execve` of a
  newly *created* executable**, on a host with Microsoft Defender real-time protection enabled
  (`mdatp health --field real_time_protection_enabled` -> true). The harness wrote five fresh
  tool stubs into every test's own `tmp_path` and then ran them:

  | one `--check-only` run of `start_admin_local.sh` | per run |
  |---|---|
  | stubs written fresh per test (pre-card) | 1.097-1.381 s |
  | stubs reused from a directory already executed | 0.074-0.120 s |
  | writing the five stub files and **not** running them | 0.003-0.006 s |

  Controls: `bash -c ':'` is 4 ms on this host and a fresh interpreter 18 ms, so a *repeated*
  spawn is cheap; the before run spent `user 5.05s, sys 5.74s` over 117.83 s of wall clock --
  **9 % of one core**, i.e. blocked, not computing. This is worth carrying past the card: every
  future "the tests are slow because they spawn processes" diagnosis on this host should check
  stub creation before it blames spawning, and the same shape will be hiding in any other
  harness that writes an executable per test.

- **[The fix, and what was deliberately not shared]** One function, `tool_dir()` in
  `tests/test_start_admin_local.py` (`@cache` + `mkdtemp` + `atexit`), keyed on the stub
  *bodies* -- so the siblings' set and the `without_psql` set each get their own directory and
  no test can silently acquire a tool it was written without. `tests/helpers/admin_scripts.py`
  gained `_real_tools_dir()` for the two symlinks `without_psql` needs. **The throwaway project
  root stays per-test on purpose**: the script copy, the no-op `.venv/bin/activate` and the call
  log are per-test, so every test still copies and executes the real script and still reads back
  only its own calls.

- **[Nothing was converted to parsing, and that is a finding rather than a shortcut.]** A
  structural check cannot see the defects these tests exist for. CARD-151's two defects were a
  script that *named* the right database and handed psql a string psql cannot parse -- the only
  evidence is the psql model's `connect` log, which exists only if the script ran. CARD-150's
  F-001 is a stream distinction (the indented quote on the script's *own* stdout), a property of
  a run. So the parsing-for-execution trade gives up exactly the defect class the trio was
  written for, and this card pays nothing to keep it. Six tests already asserted on text alone
  and always did; `TestAdminLocalTests_ExecutionSetIsDeclared` pins that set at exactly those
  six with a recorded reason each, derived from the tree with `ast`, and a mutant shows the walk
  moves a test between sets when its only run is deleted.

- **[Mutant matrix -- AC-2 and AC-4, with the control that makes it mean anything]** Each
  original defect put back **one at a time**, the whole trio run twice: once with the four test
  files restored byte for byte from `HEAD` (verified with `cmp`), once with this card's tests.
  Scripts restored from byte copies after every mutant and verified with `filecmp.cmp`.
  Identical failing *sets*, not merely identical counts:

  | # | defect | script | pre-card red | this card red | same set |
  |---|---|---|---|---|---|
  | M1 | CARD-150 bare `psql -c "SELECT 1"` on the local branch | start | 15 | 15 | yes |
  | M2 | CARD-150 hardcoded export over the caller's URL | start | 3 | 3 | yes |
  | M3 | CARD-150 failed migration warns and continues | start | 3 | 3 | yes |
  | M4 | CARD-150 F-001 `2>&1` dropped, alembic's words lost | start | 1 | 1 | yes |
  | M5 | CARD-151 `+driver` not stripped for psql | start | 8 | 8 | yes |
  | M6 | CARD-151 a URL naming no database accepted | start | 6 | 6 | yes |
  | M7 | CARD-152 bare `psql -c "SELECT 1"` | setup | 10 | 10 | yes |
  | M8 | CARD-152 hardcoded export over the caller's URL | run | 13 | 13 | yes |
  | M9 | CARD-168 test runner defaults to `nonogram_poc` | run | 5 | 5 | yes |
  | -- | **control, no mutant** | -- | **0** | **0** | yes |

  I had warned this agent that a mutant reding the same tests as a *red* baseline proves
  nothing -- the session had already lost two diagnoses to an unsound harness. The control row
  is the answer: **0 red with no mutant on both sides**, so every row above is caused by its
  mutant and not by the harness.

- **[Per-test before/after]** 83 tests, none added, none removed, none converted, no assertion
  changed, same node ids (asserted against CARD-217's frozen artefact, so a test lost before
  both halves cannot hide -- CARD-220's no-silent-retirement rule). 116.04 s -> 13.38 s;
  **1398 ms/test -> 161 ms/test**. Three pairs: 8.67x / 10.65x / 10.56x.

- **[Scope gate: PASSED, with Touches widened by the orchestrator]** The diff is six files, all
  in the test tree and `meta/profiling/` -- **no `src/` change at all**, and `git diff --
  scripts/` is empty, so G-1 holds (the ` M scripts/setup_admin_local.sh` I saw mid-flight was
  M7's mutation in its `finally`, since restored and verified). The agent flagged two paths
  outside the declared slice rather than committing a silent widening:
  `tests/helpers/admin_scripts.py` (the two siblings' shared harness -- it *is* their
  `run_script`) and the new `tests/test_admin_local_cost.py` (the ACs name three classes that
  had nowhere to live). Both accepted. `Touches` was prose ("and its two siblings") and is now
  explicit paths, which is what the conflict predictor actually reads.

- **[AC-1 / G-3: OPEN at the orchestrator, not at the agent]** The agent recorded 116.04 s ->
  13.38 s but **refused to call it settled**: every run was taken while CARD-222's fix agent held
  the full-suite lock in a sibling worktree, and that pytest was still at 100 % CPU when it
  re-checked. Both artefacts record `solo run: no` with the evidence, and
  `TestAdminLocalTests_ShareIsRecorded::test_neither_artefact_claims_to_be_the_solo_profile_g3_asks_for`
  fails if a header is edited to `yes` without a fresh measurement -- a floor that cannot be
  talked around. **This is the right call and the measurement is mine to take**: the ratios
  (8.67x, four times CARD-217's +/-20 % band) survive a host slow for both halves, but the
  absolute figure does not. I take the solo trio measurement when I hold the lock for this
  card's build gate, and update both artefacts' headers then.
  **Projected for that run:** trio ~13 s, suite attributed 920.63 -> ~816 s, trio share
  12.73 % -> ~1.64 % (derived by `projected_share_pct`, stated in the document).

- [The trap this card must avoid] CARD-150 and CARD-152 both fixed real launcher defects that
  these tests now guard. The point of the card is to pay less for that guard, not to weaken it,
  and AC-4 is the assertion that tells the difference.
- [Env] forge 2026.8.17 (no meta/.skills.yml — no min_version comparison)
- [Dispatch] Wave 44 slot, 2026-10-17T15:52Z — **owner instruction, swapped in for CARD-216** ("swap 216 for 236"), which was abandoned before its agent wrote anything and returned to `ready`. Footprint verified disjoint from CARD-222's (page-geometry code in `src/nonogram/{admin,export}` plus its own test files), so the two run concurrently with no conflict edge. Dependency CARD-217 is done — its solo profiling run is the measurement this card acts on.
