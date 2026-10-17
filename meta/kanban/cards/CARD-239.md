# CARD-239: The timing-log guards' remaining bounds, and the one place that reads the log on purpose

**Status:** review
**Priority:** P2
**Category:** tech-debt
**Complexity:** standard
**Estimate:** 1d
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/239-timing-guard-bounds
**Worktree:** ../PythonProject4-card-239
**Source:** CARD-238's five review cycles, 2026-10-15/16 — every item below was measured there and deliberately deferred rather than discovered here
**Idea:** —
**Wave:** 42
**Depends on:** —
**Touches:** tests/test_suite_profile.py, meta/profiling/rank_durations.py, .gitignore, pyproject.toml
**Review score:** 8.0 (c1) → **7.5** (c2/3) — below min_score 8, min_improvement missed, trajectory DOWN
**Started:** 2026-10-16T20:45:00Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** — (escalation resolved 2026-10-17 by owner decision: split — fix F-202, record F-201, card the taint step as CARD-242)

## What to implement

CARD-238 removed the host coupling and built an audit that makes a guard's spelling set
falsifiable. It shipped with bounds recorded as controls, deliberately, under an owner stop rule
after five review cycles. This card closes them.

**Read CARD-238 first** — in particular its retrospective-material note, which states the rule the
whole exercise produced: *a set a guard consults needs a completeness test written before the set,
and a claim about coverage needs a control that can fail.* Every item here is an application of
that rule, and the card is not done if it closes the items while minting a new unfalsifiable claim.
CARD-238's own history is the warning: five passes, and four of them did exactly that.

### 1. The directory-construction spellings (F-501) — the one with a surviving mutant

The audit polices the spellings that **read** a directory. Nothing polices the spellings that
**build** one: only the `/` BinOp is recognised. Measured — `_live_log_references` returns `[]` for

```python
os.listdir(os.path.join(REPO_ROOT, "meta", "kanban"))       # and the hoisted form
REPO_ROOT.joinpath("meta", "kanban").iterdir()
os.listdir(os.path.join(os.getcwd(), "meta", "kanban"))
```

while the `/` and `Path.cwd() / …` spellings are caught. Compounded with the except-handler bound
below, a mutant in CARD-238's own declined-Option-2 shape (names no log, skips on absence) survives
end to end at **250 passed, rc=0** — and its own verdict is `1 SKIPPED` without a log and
`1 PASSED` with one, which is the CARD-234-green / CARD-235-red flip verbatim.

Do it the way CARD-238's audit did, not by hand: make the construction spellings **an audited
projection** — a `KIND_JOINER` group over the same derived surface, so `join`, `joinpath` and
anything else the stdlib offers for assembling a path must land in a set or an exclusion with a
reason. Then narrow `_live_log_references`' docstring, which currently claims "a listing of that
directory by any spelling `STDLIB_DIRECTORY_SURFACE` classifies as one" — true of readers, false
of builders.

### 2. The version-gated set members (F-502)

`test_a_spelling_the_guards_use_is_a_real_stdlib_name` exempts `KIND_NEITHER` "and no others", so
`glob0`, `glob1`, `is_junction`, `isjunction` and `isdevdrive` must exist on the running
interpreter. Measured by deleting exactly those five attributes in a pytest plugin: red at exactly
that list. `glob0`/`glob1` are deprecated in CPython **and were added by CARD-238's last cycle**, so
an interpreter upgrade is the likely trigger.

The fix is to derive each set as `_classified(KIND) & frozenset(_stdlib_directory_surface())` — a
spelling nobody can write cannot be a hole. Note it is **not** the one-liner it looks like: the four
sets are hard-coded frozensets at roughly lines 1135 / 1161 / 1182 / 2145, defined *before*
`_stdlib_directory_surface` and `_classified`, so this needs a reordering. That is exactly why
CARD-238 recorded it instead of attempting it after a passing review.

**Settle the version floor while you are here.** `pyproject.toml:9` declares
`requires-python = ">=3.9"`; CLAUDE.md says Python >=3.14. The suite's actual floor is written down
twice, differently. Pick one, make the other follow, and say which is authoritative.

### 3. The remaining bounds and inaccuracies, all measured in CARD-238

- **F-306**: `.card238-tracked` is consulted at any root including `REPO_ROOT` and is neither
  tracked nor gitignored, so a stray copy at the repo root would silently replace `git ls-files` as
  the guard's file set. Add it to `.gitignore` and ignore one found at `REPO_ROOT`.
- **F-308**: a module-level `pytest.skip(..., allow_module_level=True)` in
  `tests/test_suite_profile.py` silences the module including both guard classes — irreducible from
  inside one module, because the comparison is itself one of the silenced tests. **A second guard
  module closes it**, and that is the only route. Doing so also closes F-306's cousin and the
  asymmetry where one module guards 221 sources.
- **The three pre-existing silences** recorded in `MEASURED_SILENCES_ELSEWHERE` are recorded, not
  fixed, because G-4 forbade editing those modules. **Two of them are CARD-238's own defect one
  module over** — a host-state skip on real filesystem state. Fix them, and strike them from the
  baseline (the equality goes red if you fix one without striking it, which is the point).
- **F-405**: that baseline's header says "Every **host-state** silence" and "These **three**" over
  four entries, one of which it itself calls "not filesystem state at all". Same habit in
  miniature, in the card whose subject was false claims.
- **The module docstring says "331 tests"** over a module that collects **341**, and CARD-238's own
  claim-sweep row A16 asserts that sentence was corrected. The one sweep row found wrong on
  measurement.
- **Two exclusion reasons are plausible-sounding and wrong**: `popen` sits under "it names no
  directory" and `system` under "not the filesystem", but `os.popen("ls " + str(KANBAN))` is both.
  And `subprocess` is outside `_SURFACE_NAMESPACES` entirely — excluded by not being looked at —
  which matters because shelling out to list files is **this module's own idiom** (six `git ls-files`
  listings per its docstring). Either audit the namespace list or state the non-claim explicitly.
- **`_unwrapped` peels only single-argument calls**, so `os.path.relpath(KANBAN, REPO_ROOT)` is not
  seen through. The audit polices *which names* are wrappers; nothing polices *which call shapes*
  the peel accepts. Either accept arity > 1 when the first argument resolves, or add it to
  `MEASURED_STRUCTURAL_MISSES` so the bound goes red when the peel grows.
- **The meta-guard rebinds module globals** with `setattr` (restored in `finally`). Correct today
  and the most valuable test CARD-238 added, but it is shared mutable global state in the unit tier:
  under `pytest-xdist` or `pytest-randomly` another test reading `_LISTERS` mid-window sees a
  narrowed set. Pass the sets as a defaulted parameter instead, or record the constraint.

### 4. The thing that should read the log on purpose

CARD-238 deleted the only mechanism that would ever notice a malformed line in the live log — and
that mechanism **worked**: it is how CARD-217's bad entry was found. Declining to replace it was
right for that card (G-4 scoped it to the test module), but the gap is real and the log is
demonstrably accumulating shapes the parser mis-reads.

Add a deliberate `rank_durations.py --check-log` subcommand: the one place that reads the owner's
log on purpose, run when someone asks rather than as a side effect of the suite. It settles the
rate-recovery question in the place that actually reads the log for real, and it is the correct home
for the check a test should never have been doing.

**Do not make the suite depend on it.** The whole point of CARD-238 is that the suite judges code,
not hosts.

### 5. The doc drift CARD-238 could not reach

`skills/kanban/references/cmd-run.md`'s SUITE TIMING step and `tests/README.md`'s format section
both document the timing line **without** the parenthesised-trailing-note form, so they now
understate the legal format — and `cmd-run.md` is the one place that would stop the next
bare-trailing-prose line being written. Note `cmd-run.md` lives in the forge skills
(`~/MyProjects/forge_1`), **outside this repository**: fix `tests/README.md` here and raise the
`cmd-run.md` drift with the owner rather than editing their tooling.

## Acceptance criteria

- **AC-1** (happy, builders are audited like readers): *Given* the derived stdlib surface, *then*
  every path-construction spelling it offers sits in a guard set or in an explicit exclusion
  carrying a reason, proved by a test that fails when a member is in neither — and the join and
  joinpath forms measured as missed in CARD-238 are now caught, each with a control that is caught
  WITH its set member and missed WITHOUT it.
  (test: `TestSuiteTiming_NoTestReadsTheLiveLog::test_every_construction_spelling_is_classified`,
  plus per-spelling controls in `REINTRODUCTIONS`)
- **AC-2** (guard, F-501's mutant dies): *Given* the surviving compound mutant from CARD-238's
  cycle 5 — `os.path.join` construction plus an `except`-handler skip, naming no log, planted in a
  tracked guarded source — *then* it is caught. Report which guard halves fire.
  (test: evidenced by a planted-and-reverted mutant, quoted)
- **AC-3** (guard, the suite survives a lower interpreter): *Given* an interpreter lacking
  `glob0`, `glob1`, `is_junction`, `isjunction` and `isdevdrive`, *then* the module is green —
  demonstrated by deleting those attributes in a plugin, as CARD-238's review did, not by reasoning.
  And *then* the version floor is declared in exactly one place.
  (test: `test_a_spelling_the_guards_use_is_a_real_stdlib_name` under attribute deletion)
- **AC-4** (happy, the module-level skip hole is closed): *Given* a module-level
  `pytest.skip(..., allow_module_level=True)` on host state in the guard module, *then* it is
  reported — which requires a second guard module, since one module cannot judge itself.
  (test: the new module's own guard, evidenced by a planted mutant)
- **AC-5** (guard, the three recorded silences are fixed and struck): *Given*
  `MEASURED_SILENCES_ELSEWHERE`, *then* the two entries that are genuine host-state skips are fixed
  in their own modules and removed from the baseline, and the equality still goes red in both
  directions. (test: `test_the_host_state_silences_elsewhere_are_exactly_the_measured_ones`)
- **AC-6** (happy, the log has a deliberate reader): *Given* `rank_durations.py --check-log`,
  *then* it reports malformed lines in the live log and exits non-zero on finding one, and **no
  test invokes it**. (test: `TestCheckLog_*` over constructed logs, plus a structural assertion
  that no test calls the subcommand)
- **AC-7** (guard, no claim without a control): *Given* this card's diff, *then* every claim it
  writes or leaves standing about what is caught, reported or seen is pinned by a control that can
  fail, or deleted — recorded in a sweep **file** under `meta/review/`, not narrated.
  (test: the sweep file is the evidence; CARD-238's cycle-5 sweep is the format)

## Guardrails

- G-1: **Do not write, move, rename or normalise `meta/kanban/suite-timing.log`.** Standing owner
  decision from CARD-238; the `--check-log` subcommand READS it and must never write it.
- G-2: coverage up, not down. CARD-238 left 341 tests in that module; nothing may be removed.
- G-3: the accepted/rejected **language** of the timing-line parser does not change. CARD-238
  established an identity over 40,214 constructed lines; a change here must preserve it and show
  the measurement.
- G-4: do not weaken the audit to make a member fit. If a spelling genuinely belongs in an
  exclusion, it goes there **with a reason**, which is a decision on the record.
- G-5: `cmd-run.md` lives outside this repository — do not edit the owner's forge skills. Raise the
  drift instead.
- G-6: no `src/**` change; no new runtime dependency (ADR-0006/R1).

## System contract

- ADR-0006/R1 — runtime dependencies are exactly stdlib + Pillow + NumPy (check:
  `tests/test_export_pdf.py::test_the_dependency_baseline_is_still_closed`)

## Architecture context

- **FR:** — (untraced test-integrity card; its done-ness is the ACs above)
- **Components:** — (tests and the profiling harness only)
- **Trace:** not updated by this card.

## Worktree notes

- [Why TDD is true on this card] Every AC here is of the form "a test exists that fails when X
  returns". That cannot be evidenced without driving each guard red against the current code first
  — the same reason CARD-238 carried `TDD: true`.
- [The one thing that would make this card fail the way CARD-238 nearly did] Closing these bounds
  while writing a new claim nothing can falsify. CARD-238 needed five cycles because four of them
  did precisely that, and the pattern was only broken when a pass was required to sweep its own
  claims and found three of its own. AC-7 exists for that reason and is not a formality.
- [Measured figures carried over, so nothing here needs re-deriving] the join forms return `[]`; the
  compound mutant survives at 250 passed; the five version-gated members red the suite when deleted;
  `subprocess` is outside the audited namespaces; `os.path.relpath(KANBAN, REPO_ROOT)` is unseen;
  the module docstring says 331 against 341 collected.

### Implementation notes (from the worktree, 2026-10-17)

**Env.** Worktree `../PythonProject4-card-239`, branch `card/239-timing-guard-bounds`,
based on `436717e`. One commit: **`46a5d31`**. Nothing under `meta/kanban/` is committed; these
notes are left uncommitted for the orchestrator. Deliverables committed:
`tests/test_suite_profile.py`, `tests/test_guard_integrity.py` (new), `meta/profiling/rank_durations.py`,
`meta/review/CARD-239-claim-sweep.md`, `tests/test_sourcing_image.py`, `tests/README.md`,
`.gitignore`, `pyproject.toml`.

**Scope, wider than `Touches:` and recorded rather than tolerated.** The card predicted
`tests/test_suite_profile.py`, `meta/profiling/rank_durations.py`, `.gitignore`, `pyproject.toml`.
Three files are outside it and each is required by an AC: `tests/test_guard_integrity.py` (AC-4 —
a second guard module is the only route, as the card itself states), `tests/test_sourcing_image.py`
(AC-5 — "fixed in their own modules"), `tests/README.md` (part 5, named in the card's body).
`meta/review/CARD-239-claim-sweep.md` is AC-7's artefact.

**Sweep file: `meta/review/CARD-239-claim-sweep.md`** — 33 PINNED, 6 DELETED, 7 RECORDED as
bounds with controls, 0 `[BLOCKER]`. **Five claims were found false on measurement**: two written
in this pass and caught by controls this card wrote (`PLATFORM_GATED_SPELLINGS` carried `info`,
which is a property and not on the surface; `_MODULE_SCOPE_SILENCERS` carried `skip_module`, which
does not exist in pytest, and `fail`, which errors loudly rather than silencing — the F-403 shape
in my own pass, twice), and three survivors of CARD-238's own sweep (A-9, D-2, F-13 below).

**Mutant methodology.** Every verdict below comes from a **fresh `pytest` process per mutant**,
with the mutated file restored from a byte copy taken before planting and the md5 verified after.
The batched-run false-KILLED finding from this project's review station is why.

#### Red → green, per AC

- **AC-1** (builders audited like readers) — `TestSuiteTiming_NoTestReadsTheLiveLog::test_every_construction_spelling_is_classified`.
  Red first by measurement, not by reasoning: with `with_segments` left in the pure-arithmetic
  exclusion the test names it — `['with_segments (base.with_segments(*components))']`, module
  3 failed / 350 passed — and green once classified. The four forms the card quotes went
  `[]` → caught: `os.path.join` inline, hoisted, and rooted at `os.getcwd()` →
  `['listdir() of meta/kanban']`; `REPO_ROOT.joinpath(...).iterdir()` → `['iterdir() of meta/kanban']`.
  **Four more nobody had listed are caught too**, each with a control:
  `Path(ROOT, "meta", "kanban")`, `with_segments`, `os.sep.join([...])`, and a glob under a joined
  directory. Every joiner control names **no log**, because the two `os.path.join`/`joinpath`
  entries already in `REINTRODUCTIONS` were caught through their log *filename* and so measured
  nothing about the spelling — `test_the_control_for_each_spelling_depends_on_the_set` now covers
  the joiners and holds that line.
- **AC-2** (F-501's mutant dies) — planted end to end in `tests/test_clues.py`: `os.path.join`
  construction, `os.listdir` filtered to `*.log`, the read in a `try/except (FileNotFoundError,
  IndexError)` with `pytest.skip`, naming no log. **Pre-fix: 341 passed, rc=0** (CARD-238 as
  merged, both files restored from `git show HEAD:`); function-level, both halves blind
  (`_live_log_references` → `[]`, `_conditional_silences` → `[]`). **Post-fix: 2 failed / 400
  passed.** Halves that fire: the **path guard** —
  `{'tests/test_clues.py': ['listdir() of meta/kanban']}` — and the **behavioural comparison**
  transitively. The **silence half does not fire**: the skip is reached from an `except` handler,
  which every rule in `_conditional_silences` is blind to (CARD-238's recorded bound, pinned in
  `NOT_A_CONDITIONAL_SILENCE`). Stated rather than rounded up. `tests/test_clues.py` restored,
  md5 `942627df2b6df5a003bf52775ab1d398`, `git diff --stat` empty.
- **AC-3** (the suite survives a lower interpreter) —
  `test_a_spelling_the_guards_use_is_a_real_stdlib_name` under a plugin that deletes `glob0`,
  `glob1`, `is_junction`, `isjunction`, `isdevdrive` before collection. **Red: 1 failed, 340
  passed**, naming exactly those five. **Green: 388 passed, 0 failed** across both guard modules.
  The plugin lives in the scratchpad and is not committed. The test is restated as a **subset**
  claim against `PLATFORM_GATED_SPELLINGS` — the only direction that can hold on every host — so a
  typo (`listdirs`) is still red while a 3.9 run is green.
- **AC-4** (the module-level skip hole) — new module `tests/test_guard_integrity.py`,
  `TestGuardModule_CannotGoQuietAboveItsOwnGuards`. Mutant: the log-keyed
  `pytest.skip(..., allow_module_level=True)` planted at module scope in
  `tests/test_suite_profile.py`. Its own verdict: **`1 skipped in 0.03s`, rc=0** — 398 guards gone,
  run green. **Killed by both mechanisms**: the import probe
  (`importing test_suite_profile.py did not finish: Skipped: no timing log on this host`) and the
  AST rule (`('tests/test_suite_profile.py', 'skip() at module scope', ...)`) — 2 failed / 40
  passed / 1 skipped. **The mutual direction is measured too**: a module-scope skip planted in the
  new module makes `test_the_host_state_silences_elsewhere_are_exactly_the_measured_ones` red,
  naming it. Both restored, md5s verified.
- **AC-5** (the recorded silences fixed and struck) —
  `test_the_host_state_silences_elsewhere_are_exactly_the_measured_ones`, measured red in the
  "fixed but unstruck" direction **one entry at a time** before either was struck. The two are
  `tests/test_sourcing_image.py`'s `not picture.is_file()` and `not PICTURES.is_dir()`: the
  25-picture corpus is **committed** (`git ls-files pictures` lists 25) and the same module asserts
  it is exactly those 25 files unconditionally a thousand lines above, so the skips could only ever
  fire on a checkout that had lost a tracked file — the one case those tests most need to report.
  `SILENCES_FIXED_BY_CARD_239` keeps the record, and
  `test_a_silence_this_card_fixed_is_still_one_the_detector_would_report` keeps the shape
  exercised after the fix. The third entry (`not _DESIGN.exists()`) stays **with a corrected
  reason**: it is about packaging, not about this host, and belongs to forge:ui's card.
- **AC-6** (the log has a deliberate reader) — `TestCheckLog_TheDeliberateReader`, seven tests over
  logs the tests construct, red before `check_log_report` existed. It reports malformed lines
  (CARD-217's real bare-trailing-note line is named, status 1), accepts the parenthesised form
  (status 0), and answers the rate-recovery question with a non-vacuity control
  (`rate recovered: 0 of 1` on a bracket-bearing line that does not parse).
  **No test invokes the subcommand** —
  `test_no_guarded_source_invokes_the_check_log_subcommand` over every `*.py` under the guarded
  trees, with four fabricated positive controls and a **shape-keyed** exemption for the
  `add_argument` registration (a filename exemption would be inherited by any test added to the
  ranker tomorrow) plus its own control. `--check-log` has **no default path**, deliberately:
  a default would put the owner's log's path into a file the AC-1 guard walks, which is review
  cycle 2's MUT-R verbatim.
- **AC-7** (no claim without a control) — the sweep file above. Three rows are corrections of
  sentences this card found false, each with the measurement.

#### Closed by mechanism

- **The construction spellings (F-501).** An audited projection whose membership is measured
  against the library's own behaviour, not enumerated: `_measured_path_builders` calls every
  path-algebra spelling the probed namespaces offer on a base and two components and reads what
  comes back. Seven builders on this host; `with_segments` is one nobody had thought of.
- **The version-gated members (F-502).** `_guard_set(KIND) = _classified(KIND) & surface`, with
  the four sets reordered below `_stdlib_directory_surface`/`_classified`. The projection equality
  can no longer fail, so the claim that the sets are *derived* is a separate test that reads this
  module's own source (`test_the_guard_sets_are_derived_and_not_hand_written`) — it was red on its
  first run at `_HOST_STATE_PROBES`, the fifth set, which was still hand-written.
- **F-306.** `_files_under_guard` takes the untrusted root as a parameter and ignores the manifest
  there; `.card238-tracked` is in `.gitignore` with the reason. Measured both ways on a root the
  test owns, so the control needed no write into the repository.
- **F-308.** The second module, with mutual coverage measured in both directions.
- **F-405, and the module docstring's "331 tests".** The baseline header is rewritten to what the
  detector reports and carries no count; the docstring's test count is **deleted rather than
  updated**, because `--collect-only -q` answers it in a second and a number in prose cannot go red.
- **The meta-guard's global rebinding.** The sets are a defaulted `Spellings` parameter. The reason
  is labelled **reasoned, not measured** — neither `pytest-xdist` nor `pytest-randomly` is in the
  dependency baseline, so the interleaving cannot be demonstrated here. The same defect in the new
  module's own meta-guard was found by the sweep and fixed the same way.
- **Two wrong exclusion reasons.** `popen` and `system` moved to a reason that is true, and the
  non-claim it states is pinned by two new `MEASURED_STRUCTURAL_MISSES` entries.

#### Named limits, each with the control that proves it open

- **A builder living only in the top-level `os` namespace** would not be found by the behavioural
  probe. `os` is excluded **by measurement**: probing it made `os.popen("base", "meta", "kanban")`
  fork a shell. Such a name would still have to be classified with a reason
  (`test_every_spelling_the_stdlib_offers_is_classified` is red on an unclassified name in any
  namespace), so what is lost is the behavioural second opinion, not the default-deny.
- **`os.path.relpath(KANBAN, REPO_ROOT)` is unseen** — `_unwrapped` peels one-argument calls only.
  New `MEASURED_STRUCTURAL_MISSES` entry; red the day the peel grows. Not fixed, and the reason is
  measured: widening the peel to "first argument of any arity" hands `Path(ROOT, "meta", "kanban")`
  to the listing rule as `ROOT`. The constructor half is fixed instead, via `_component_arguments`.
- **Shelling out is unseen**, by `os.popen`, `os.system` or `subprocess`. Two new
  `MEASURED_STRUCTURAL_MISSES` entries. `_SURFACE_NAMESPACES` is deliberately **not** widened to
  `subprocess`: thirty names whose classification nothing could measure either, and shelling out to
  list files is this module's own idiom (six `git ls-files` listings).
- **The except-handler skip is not reported by the silence detector** — CARD-238's bound, confirmed
  by AC-2's mutant: the compound mutant dies to the path guard, not to the silence half.
- **The env-var path with no literal in the source** still survives both halves. CARD-238's
  recorded survivor; not re-measured here.
- **The three argparse lines wiring `--check-log` are executed by no test**, because AC-6 forbids
  it. They are asserted structurally (the option registered once, `default=None`, the function
  called once). A rename is red; a logic error inside the three lines is not.
- **`NOT_A_PATH_WRAPPER` discriminates for one of its three entries, not three** — found false on
  measurement, and false on CARD-238 as merged too, so a cycle-5 survivor rather than something
  this card broke. `KANBAN.joinpath("cards")` and `KANBAN.with_name("profiling")` are one-*argument*
  attribute calls, so the peel takes the string and letting either name into the set changes
  nothing. Corrected three ways: the sentence rewritten; `NON_WRAPPERS_THE_SET_DECIDES = ("dirname",)`
  recorded as an **equality** that is red if the peel grows; and the discriminating power the
  sentence claimed now supplied by `test_a_path_arithmetic_name_is_peeled_only_if_it_is_in_the_set`,
  generated from the table over all 18 path-arithmetic names in both wrapper shapes.

#### Version floor

**`pyproject.toml` is authoritative**, and the floor is **`>=3.14`**. It is the machine-readable
declaration, it is what an installer enforces, and CLAUDE.md is a document about it. CLAUDE.md
already said 3.14 and is unchanged; `pyproject.toml`'s `requires-python` moved `>=3.9` → `>=3.14`.
A **third** statement of the floor nobody had noticed was also wrong: the PyPI classifier said
`Programming Language :: Python :: 3.9+`, so two of the three agreed with each other and not with
the interpreter anyone runs. It now reads `3.14`. Both are pinned by
`TestTheInterpreterFloor` (floor vs CLAUDE.md's `python3.14 -m venv`, floor vs the classifier, and
floor vs the running interpreter) — red before the change with the message naming both numbers.

#### Measurements of the card's own figures

- **341, not "more than 341".** `tests/test_suite_profile.py` collects exactly **341** on
  `436717e` — the dispatcher's note that CARD-228 had pushed it higher is wrong; CARD-228 added
  tests elsewhere. After this card: **398** collected, **zero removed** (verified by `ast`-diffing
  the test function names against `git show HEAD:`: 7 added, 0 gone). New module: **42**.
- **341 passed, not 250**, for the compound mutant's end-to-end survival against CARD-238 as
  merged. 341 is what that module collects, so the mutant survived *every* test in it; 250 was
  presumably a narrower selection in the cycle-5 worktree. Same conclusion, and the
  function-level measurement (both halves returning `[]`) is the decisive part either way.
- Every other figure the card carried over reproduced: the three join forms return `[]`; the five
  version-gated members red the suite when deleted; `subprocess` is outside the audited
  namespaces; `os.path.relpath(KANBAN, REPO_ROOT)` is unseen; the module docstring said 331 over 341.

#### Guardrails

- **G-1 HELD.** The worktree has no `meta/kanban/suite-timing.log` (gitignored, fresh checkout) and
  nothing here creates one; `AC-5`'s work needed no log and `--check-log` only ever calls
  `read_text`. The **main** repository's log was neither read nor written by this card: it stands at
  md5 `be3dfae8a428d62aec0087926c89b44d`, 3016 bytes, mtime Oct 16 23:41 — consistent with the two
  dispatcher appends mentioned in the brief (CARD-238 recorded 2802 bytes before them). I have no
  earlier md5 of my own to compare, which is stated rather than implied.
- **G-2 HELD, measured** — see the counts above; zero test functions removed.
- **G-3 HELD by construction.** `TIMING_LOG_LINE` is byte-identical; the ranker's diff is purely
  additive (`_RATE_BRACKET`, `check_log_report`, the argparse wiring), so the 40,214-line
  accept/reject identity CARD-238 established is untouched rather than re-measured.
- **G-4 HELD.** Three names moved into a **new** kind with a measured reason; two had their reason
  corrected; nothing was moved into `KIND_NEITHER` to make a test pass. The one place members were
  removed from a set is the new module's own `_MODULE_SCOPE_SILENCERS`, where `skip_module` was
  measured not to exist in pytest and `fail` measured to error loudly rather than silence — both
  with the reason written into the set.
- **G-5 HELD.** `skills/kanban/references/cmd-run.md` not touched. **Raised:** it is the one file
  the dispatcher actually reads at a merge gate, it documents neither the legal parenthesised
  post-bracket note nor the illegality of a bare one, and it is therefore still the place the next
  bare-trailing-prose line will come from. `tests/README.md` is fixed here and now says both, with
  the writer named.
- **G-6 HELD.** No `src/**` change. No new runtime dependency — `pyproject.toml`'s only edits are
  `requires-python` and the classifier; `tests/test_export_pdf.py::test_the_dependency_baseline_is_still_closed`
  green. New imports are stdlib only (`typing.NamedTuple`; and in the new module `ast`,
  `importlib.util`, `re`, `sys`, `tomllib`, `pathlib`, `types`).

#### Build gate (not the merge gate — the full suite is the dispatcher's)

`tests/test_suite_profile.py` + `tests/test_guard_integrity.py` + `tests/test_sourcing_image.py` +
`tests/test_cli.py` + `tests/test_export_pdf.py` → **728 passed** in 28.09s. The two guard modules
alone: **440 passed** in ~18s. Under the lower-interpreter plugin: **388 passed, 0 failed.**

### Review cycle 2 — cycle 1's two Important findings applied (2026-10-17)

Cycle 1 scored **8.0**, no Critical, and failed the severity gate on two Important findings.
Both were in `tests/test_guard_integrity.py` — the module AC-4 required — and **both were
recorded as PINNED in the sweep**, so they were AC-7 failures and not only defects. The sweep
held on 31 of the 33 rows the reviewer sampled and was decorative at exactly the two rows about
the new module's own rules. That is the card's own stated failure mode happening one module in,
and it is written that way in the sweep's new header rather than softened.

Nothing in the first module's verified work was touched: AC-1's projection, AC-2's compound
mutant and its honest three-halves split, AC-3, AC-5's struck silences, the `relpath` trade, `os`
excluded by measurement, the three argparse lines as a structural-only bound, and the
"reasoned, not measured" label on the xdist/randomly interleaving all stand as merged.
`TIMING_LOG_LINE` is still byte-identical to `main` (G-3, re-diffed).

**F-001 — `_MODULE_SCOPE_SILENCERS` was swept as default-deny and was not. Closed by
mechanism.** The sentence was inverted: what was enumerated was what is *reported*, and the rule
passes every module-scope statement it does not recognise. Reproduced the reviewer's four
measurements against `46a5d31` exactly — `raise unittest.SkipTest(...)` → `[]`, `os._exit(0)`
under a host-state `if` → `[]`, a module-scope call into a local helper that skips → `[]`,
`collect_ignore = [...]` → `[]`. A *literal* default-deny is unavailable here and the module now
says so: a test module's module scope is legitimately full of imports, constants and helper
defs, so reporting everything unrecognised reports everything. So the completeness question was
moved into the two halves it can be answered in.

- **Derived where an authority exists.** `_pytest_surface()` reads `dir(pytest)` under the same
  two mechanical filters `_stdlib_directory_surface` uses — public, callable — measuring **88
  public names, 84 callable** on pytest 9.1.1. All 84 are classified in
  `_PYTEST_CLASSIFICATION` with a grouped reason, and `_pytest_silencers()` is
  `{KIND_SILENCER} & _pytest_surface()` → `['exit', 'importorskip', 'skip', 'xfail']`. A new
  pytest silencer must now land in a set or in an exclusion with a reason, exactly as a new
  `dir(os)` name must one module over.
- **Explicit members with reasons for the rest**, because no `dir()` is an authority for them:
  `_NON_PYTEST_SILENCERS` = `SkipTest`, `_exit`; `_MODULE_SCOPE_SILENCING_BINDINGS` =
  `pytestmark`, `collect_ignore`, `collect_ignore_glob` (a binding is not a call at all).
  Each has a control that is caught WITH its member and missed WITHOUT it.
- **Recorded as measured misses**, named rather than implied to be covered:
  `MEASURED_MODULE_SCOPE_MISSES` — the helper-indirection case, and the silencer bound to a new
  name and called through the alias. Same shape as the other module's
  `MEASURED_STRUCTURAL_MISSES`, red the day the rule grows past one.

Closed **by mechanism**: `unittest.SkipTest`, `os._exit`, `collect_ignore`,
`collect_ignore_glob`. **Recorded misses**, still open and now with controls: helper
indirection, the aliased callable. Three sentences (the module docstring's bullet, the set's own
comment, and the baseline's "Every module-scope silence in the guarded tree") now say what the
rule does, and sweep row **D-6** no longer says PINNED.

**F-002 — AC-6's rule missed a shell string and its control certified a copy. Fixed by
widening, not by recording.** Reproduced the reviewer's split exactly: a subprocess argv
`control=True DEPLOYED=True`, `main()` directly `True/True`, a shell string
`control=True DEPLOYED=False`, `shell=True` `True/False`. RC-1 is closed first — the rule is one
module-level function, `_check_log_invocations`, and all three tests call it, the
`_live_log_references` shape — and then the predicate is the **substring** form, because a
command line is one string with the option inside it. Three exemptions, each keyed on shape and
each with its own control: `add_argument`'s arguments; `error(...)` on a receiver that registers
arguments somewhere in the same source, which is how `rank_durations.py:673` names the option in
its own usage message and is **not borrowable without building a real parser** (`reporter.error`
on a receiver that registers nothing **is** reported, and that is a positive control, not an
exempt one); and a module-scope binding plus any bare string expression, i.e. a docstring.
`test_the_invocation_rule_is_the_one_the_guard_runs` reads this module's own source and is red if
any test in the class asks the question by walking `ast` itself again. Sweep row **E-3** now
records that three of its four controls discriminated and the shell-string one measured a copy.

**Minors, both carried as sweep rows with their measurement** (D-12, A-12), on the same terms as
A-9, D-2 and F-13.

- **F-003, the emptied-module floor.** `tests/test_suite_profile.py` declares **94** test
  methods, so `>= 60` permitted 34 going with the probe green — "emptied" and "60" are not the
  same claim. Two assertions now and each says only what it can: a **derived** equality with no
  number in it (what the import produced equals what the file's source declares, so a guard that
  fails to materialise at import is *named* — measured red by `del`-ing one method), and a
  **floor at 90** that is labelled a hand-maintained number near the real count rather than a
  measurement, for the emptying case the equality cannot see. Deletion is G-2's and is enforced
  where it can be, by the dispatcher's `ast` diff.
- **F-004, the garbled second reference.** Fixed at the root rather than deduped at the report:
  `_assembles_path_components` turns the `_string_values` fold off for a call whose name is in
  the audited joiner projection, since a joiner's arguments are separate path components; the
  fold is kept where the receiver is a string literal, which is the shape that is genuinely
  concatenation. The inline and hoisted glob forms now both return exactly
  `["glob('*.log') under meta/kanban"]`, and the `"".join` taint chain still resolves.

**The reviewer's two surviving mutants, re-run.** Each in its own fresh `pytest` process, planted
in `tests/test_clues.py`, restored from a byte copy with md5 `942627df2b6df5a003bf52775ab1d398`
verified and `git diff --stat` empty after each.

- `os.system("python meta/profiling/rank_durations.py --check-log meta/kanban/suite-timing.log")`
  — cycle 1: **GREEN, 1 passed, SURVIVED**. Now: **RED (killed)**, naming
  `{'tests/test_clues.py': ["_m_os.system('python meta/profiling/rank_durations.py --check-log
  meta/kanban/su"]}`. Planted inside a module-scope `def` that is never called, so the AST rule
  sees the shell-out and **no process ever runs it** — G-1 is not approached, let alone touched.
- `raise unittest.SkipTest("no timing log on this host")` at module scope, keyed on a path that
  does not exist — cycle 1: `[]`, unreported. Now: **RED (killed)**, naming
  `('tests/test_clues.py', 'SkipTest() at module scope', "not
  _m_os.path.exists('/nonexistent-timing-log')")`. Its own verdict, measured in this tree:
  **`1 skipped in 0.06s`, rc=0** — 386 tests in that module gone and the run green, the F-308
  verdict verbatim. (The same module in an isolated sandbox: `1 skipped in 0.00s`, rc=0, which is
  the reviewer's figure reproduced. One earlier attempt of mine reported a collection error
  instead; that was my plant sitting above `from __future__ import annotations` and is recorded
  here rather than quietly dropped.)

**Six further mutants, proving the new mechanisms can fail** — each in a fresh process, restored
from a byte copy with the md5 verified (`ec4fcfb02a531917bfa114f37c650a12` /
`74d75c46cd843be807fbec733f15187a`):

| mutant | verdict |
| --- | --- |
| drop `fail` from the pytest classification | RED — `assert ['fail'] == []` |
| classify `skip_module` KIND_SILENCER | RED — `assert ['skip_module'] == []` (D-4's own member) |
| make `_MODULE_SCOPE_SILENCERS` a literal frozenset again | RED — the derived-set structural test |
| empty the `bindings` set | RED — 8 failed, naming `pytestmark` and both `collect_ignore` forms |
| narrow the `--check-log` predicate back to the equality | RED — 4 failed: two shell strings, the f-string command, the non-parser `error` |
| restore the joiner fold | RED — the F-004 control, naming `glob('metakanban*.log') under meta/kanban` |

**Counts.** `tests/test_suite_profile.py` **398 → 399**, `tests/test_guard_integrity.py`
**42 → 69**, total **440 → 468 passed** in 18.49s. `ast`-diff of test function names against
`HEAD`: +1/−0 and +9/−0, so **nothing removed** (G-2);
`test_the_definition_shape_is_not_an_invocation` kept its name while widening from one control to
four, so the name-level diff stays clean. Build gate, five modules: **728 → 756 passed** in
27.58s. **G-1 HELD** — the main repository's log is still md5
`be3dfae8a428d62aec0087926c89b44d`. **G-3 HELD** — `TIMING_LOG_LINE` re-diffed against
`main:meta/profiling/rank_durations.py`, byte-identical; `meta/profiling/rank_durations.py` is
not touched by this cycle at all. **G-6 HELD** — no `src/**` change, no new import of any kind.

**What is NOT claimed, and is stated here rather than left to be inferred.** The module-scope
rule is an *enumerated* rule and now says so in every place it describes itself; its derived half
is complete against the installed pytest only, and a KIND_NOT_A_SILENCER name an older or newer
pytest lacks is not reported (G-10 in the sweep). The `error(...)` exemption trusts a shape, and
a source that builds a real parser, registers something on it and then hands the option to that
parser's `error` is exempt — the half that matters is measured from the other side (G-11). Two
module-scope routes stay open as recorded misses with controls (G-8, G-9). The emptied-module
floor is a number somebody will have to edit, and it is labelled as one.

### Final pass — the owner's split applied (2026-10-17)

No cycle 3. One bounded pass on the closed list the split names: **F-202 closed by
mechanism**, **F-201 recorded as a bound and carded as CARD-242**, and the four Minors
corrected. Nothing else in either module was touched, and no exemption was widened or
narrowed — `_check_log_invocations`' logic is byte-identical to `e9f0e8f`. The one change
that would have re-opened the loop, giving that rule the sibling's taint step, is
deliberately **not** here; it is CARD-242's, and the bound below is what stops that card
closing the route quietly.

**Closed by mechanism — F-202, `__test__ = False`.** `__test__` is a member of
`_MODULE_SCOPE_SILENCING_BINDINGS` now, carrying the measurement as its reason, with a
control in `MODULE_SCOPE_SILENCES`. Re-measured here rather than relayed, pytest 9.1.1:
the victim module alone is `collected 0 items` / `no tests ran`, **rc=5**; beside one
other module it is **`1 passed in 0.10s`, rc=0** — two failing guards gone and the
session green. The reviewer's note that the control then comes free was **verified, not
assumed**: `test_every_binding_it_names_has_a_control` and
`test_the_control_for_each_binding_depends_on_the_set` both parametrise from the set, so
the new member brought its own two cases and needed no new machinery — but it does need
the control itself, since the first of those tests is red on a member with none. Measured
both ways through the deployed rule: the control is reported **WITH** the member
(`[('__test__', '')]`) and `[]` **WITHOUT** it. Reported on *any* binding of the name
rather than only a falsy one, on purpose: every member of this set is value-blind, and a
value test would be a fourth exemption in the module whose review history is about
exemptions.

**The mutant, re-run.** `__test__ = False` planted in `tests/test_clues.py` immediately
after `from __future__ import annotations` (the position cycle 2 recorded a false start
at), in its own fresh `pytest` process:
`test_no_guarded_module_silences_itself_at_module_scope` is **RED**, naming
`(('tests/test_clues.py', '__test__', ''),)` against `MEASURED_MODULE_SCOPE_SILENCES`'s
empty tuple — **1 failed, 76 passed in 1.90s**. Cycle 2 measured the same plant as
SURVIVED at 468 passed with both guard modules green. Restored from a byte copy, md5
`942627df2b6df5a003bf52775ab1d398` re-verified, `git diff -- tests meta/review
meta/profiling pyproject.toml` back to the two intended files.

**Recorded as a bound — F-201, and it is CARD-242's.** New `MEASURED_CHECK_LOG_MISSES`,
the shape `MEASURED_MODULE_SCOPE_MISSES` already had, asserted `== []` by
`test_the_disclosed_check_log_misses_are_still_misses`. First entry: the command line
hoisted into a module-scope constant and executed — cycle 2's M2, `SURVIVED at 854
passed` where the inline M3 was KILLED. Both the constant and the sweep rows (**E-9**,
**G-16**) name CARD-242, and the bound is **measured non-vacuous**: the deployed rule
returns `[]` for that entry, while the same rule with its module-scope exemption narrowed
to value equality — one of the two closures CARD-242 can take — returns
`["CMD = 'python meta/profiling/rank_durations.py <the option> PATH'"]`. So that card
cannot close the route without this test going red and this entry being struck, which is
the whole point of recording it rather than leaving it in a report.

**Recorded as a bound — F-203's real bound.** Second entry of the same constant: an
`error(...)` on any receiver that an `add_argument(...)` call names too. Measured `[]`
against the deployed rule with **no `ArgumentParser` anywhere**, and the exempt `error`
executing what it was handed. The mechanism is *not* narrowed — that is the same
exemption F-201 is about, and therefore CARD-242's.

**Recorded as bounds — F-206's four routes.** `MEASURED_MODULE_SCOPE_MISSES` goes from
two entries to six, each measured `[]` against the deployed rule and each under the
existing parametrised bound: a call into an **imported** helper that skips (a different
and wider reason than the local one — the rule cannot read a body that is not in the
file); `globals()["pytestmark"] = …` (the target is a Subscript, not a Name);
`getattr(pytest, "skip")(…)` (the call's function is itself a call, so there is no last
name component); and `raise SystemExit(0)`, an exact alias of the enumerated `exit`,
recorded rather than closed because its verdict is the loud one — measured here as a real
pytest module, `INTERNALERROR> SystemExit: 0`, `no tests ran`, **rc=3**. Non-claims
**G-8** (rewritten: local *or imported*, two different reasons), **G-13**, **G-14**,
**G-15**.

**The corrected wordings.** Each was false as stated, and each is replaced by what holds:

- **F-203.** The card's cycle-2 sentence *"not borrowable without building a real
  parser"* and the rule's docstring *"Not borrowable without actually building a parser
  that registers arguments"* are **false**: `maker().add_argument("--z")` beside
  `maker().error("… the option …")` is exempt with no parser built and the two calls not
  even on the same object, because the match is on the receiver's *unparsed text*. And
  *"the exempt shape executes nothing"* is a property of `argparse.ArgumentParser`, not of
  the exemption, which is keyed on two method **names**: a class with an
  `add_argument`-named method and an `error` that calls `os.system(c)` is exempt and
  executes. The docstring and sweep row **G-11** now say that; this card's cycle-2
  sentence is superseded by sweep row **E-10**.
- **F-205.** *"No `dir()` is an authority for them"* is **false of `SkipTest`**:
  `"SkipTest" in` public-callable `dir(unittest)` → **True** under this module's own two
  filters, so `dir(unittest)` is as much an authority for it as `dir(pytest)` is for
  `pytest.skip`. It holds for `_exit` (fails the public filter) and for the four bindings
  (not callables at all). The comment is split: `SkipTest` is a member **by choice** —
  one name in one namespace against a whole second classification table — and the cost of
  the choice, that the unittest half carries no completeness audit, is the claim that
  replaces the false one. No measurable miss follows (unittest's other silencing names are
  decorators; `unittest.main()` raises `SystemExit` loudly). Sweep row **D-15**.
- **F-204.** The sweep's header counts are now what they are: **hand-maintained, counted
  mechanically**, with the `grep` that reproduces every number written beside them, the
  three overlapping rows (**B-4**, **D-4**, **F-7**) named, and the buckets stated as
  **not a partition**. The reviewer's figure is confirmed — PINNED was 32 against a
  declared 37 — and the two count lines deliberately differ (13 rows carry the token,
  15 are found false, because **B-4** and **D-2** state their falsification in their own
  words). Not derived, and that is said to be a decision: deriving needs one canonical
  verdict token per row, and three rows honestly carry two. Sweep row **F-14**.
- **The out-of-scope leftover**, closed while here: the `MODULE_SCOPE_SILENCES` comment at
  the `importorskip` control still asserted *"that is what default-deny means"* in the
  present tense — the last standing copy of the sentence cycle 1 falsified. It now says
  what the rule does (an enumerated rule reports what it enumerates), and says that it
  said the other thing until this pass. Lines 54/344/769 already referred to it in the
  past tense and are untouched.

**Counts and guardrails.** `tests/test_guard_integrity.py` **69 → 77** collected, so the
loop is **468 → 476 passed** in 18.8s and nothing was removed (**G-2**): +1 binding
discrimination case, +4 module-scope misses, +2 check-log misses, +1 positive control.
`tests/test_suite_profile.py` is **not touched at all** this pass; `meta/profiling/` is
not touched, so **G-3** holds by construction and `TIMING_LOG_LINE` is still
byte-identical to `main`. **G-1 HELD** — the main repository's log is md5
`be3dfae8a428d62aec0087926c89b44d` before and after, re-checked after the mutant; the new
controls spell their destination `PATH` and the one that shells out does so inside a
`def` that nothing calls. **G-6 HELD** — no `src/**`, no new import of any kind,
`cmd-run.md` untouched. The full suite is **not** run here; it is the merge gate's.

### Orchestrator log

- [Why TDD is true on this card] Every AC here is of the form "a test exists that fails when X
- [The one thing that would make this card fail the way CARD-238 nearly did] Closing these bounds
- [Measured figures carried over, so nothing here needs re-deriving] the join forms return `[]`; the
- [Why TDD is true on this card] Every AC here is of the form "a test exists that fails when X
- [The one thing that would make this card fail the way CARD-238 nearly did] Closing these bounds
- [Measured figures carried over, so nothing here needs re-deriving] the join forms return `[]`; the
- [Env] forge unknown (no resolvable plugin manifest; no meta/.skills.yml)
- [Dispatch] started 2026-10-16T20:45Z, after CARD-228 merged rather than beside it. **The owner
- [Scope] 8 files, THREE beyond the card's `Touches:` — and each is required by an AC the card itself writes: `tests/test_guard_integrity.py` (new; AC-4 says a second module is the ONLY route, because one module cannot judge its own module-level skip), `tests/test_sourcing_image.py` (AC-5: "fixed in their own modules"), `tests/README.md` (part 5). My read, passed to the reviewer to agree or not: this is an **under-specified `Touches:` at decompose time**, not scope growth — the card's own body prescribes all three — and the agent recorded it rather than letting it read as excess. `[Touches drift]` recalibration, not a contract violation. Note the known overlap with CARD-236 on `meta/profiling/`: CARD-236 is not started, so no live conflict, but it will rebase.
- [Build gate] 341 → **398** in tests/test_suite_profile.py, **zero test functions removed** (the agent `ast`-diffed names against `git show HEAD:`), plus a new 42-test module. Its own build gate over the files it touched: 728 passed. Verified by me independently: 341 on main, 398 here.
- [Guard] **G-1 verified by md5, and the agent's caveat is the right one.** The main repo's `suite-timing.log` stands at `be3dfae8a428d62aec0087926c89b44d`, 3016 bytes — matching what the agent reported, and consistent with the two well-formed entries I appended at this wave's merge gates. It said plainly that it holds no earlier md5 of its own, so its claim is "unchanged since I started" and not "unchanged ever". That is the honest form of that claim.
- [Correction to MY OWN dispatch brief] I told the agent "the file now collects more than 341 — CARD-228 merged since. Measure, do not trust the number." **The instruction was right and my premise was wrong**: `tests/test_suite_profile.py` collects exactly **341** on `436717e`. CARD-228 added its tests to `test_book_difficulty_dots.py` and `test_book_interior_type_floor.py`, not here. I verified 341 on main myself after the agent said so. It also corrected a second carried figure: the compound mutant survives at **341 passed, not 250** — 341 is what that module collects, so it survived *every* test in it; 250 was presumably a narrower selection in CARD-238's cycle-5 worktree. Same conclusion, better number. **That is the fourth and fifth time today a downstream agent corrected a figure I passed on**, which is now a pattern about me and not about them: I have been relaying measurements from reports without re-deriving them.
- [AC-7 working as designed] the sweep found **five claims false on measurement, and two were the agent's OWN, written in this pass and caught by controls this card wrote** — `PLATFORM_GATED_SPELLINGS` carried `info` (a property, not on the surface), and `_MODULE_SCOPE_SILENCERS` carried `skip_module` (**which does not exist in pytest**) and `fail` (errors loudly, so not a silencer). That is the F-403 shape twice inside the pass meant to end it — and the sweep caught both before review did. If this holds up under review it is the strongest evidence yet that CARD-238's 2.7 days bought a real mechanism rather than a habit.
- [Found in passing] a **third** version-floor statement nobody had noticed: the PyPI classifier said `Python :: 3.9+`. So two of three statements agreed with each other and not with the interpreter anyone runs. `pyproject.toml` is now authoritative at `>=3.14`, CLAUDE.md already agreed, and all three are pinned by `TestTheInterpreterFloor`.
- [Review 1/3] dispatched with AC-7's sweep audit as priority 1, on the grounds that if the sweep is decorative the card has reproduced the CARD-238 defect one level of abstraction higher — which is the only way this card can fail quietly. Also asked to judge the one gap the agent named itself (three argparse lines no test executes, asserted structurally only because AC-6 forbids invoking the subcommand) and the one claim it labelled **reasoned, not measured** (the xdist/randomly interleaving, undemonstrable because neither is in the dependency baseline).
- [Raised for the owner, G-5] `cmd-run.md` in `~/MyProjects/forge_1` is **not** edited, correctly. But it is the one file the dispatcher reads at a merge gate, and it documents neither the legal parenthesised post-bracket note nor the illegality of a bare one — **so it is still where the next malformed timing line will come from.** `tests/README.md` now documents both, with the writer named and the `--check-log` invocation shown. I nearly wrote such a line myself today and caught it only by running it through the committed regex.
- [Review 1/3] **8.0, severity gate FAILS** on 2 Important, 0 Critical. Risk MEDIUM, lane DEEP.
- [Review 1/3] **the sweep is NOT decorative — 31 of 33 PINNED rows held the sample, and every one of
- [Review 1/3] it also **confirmed the two claims the sweep caught in its own pass are real** — M5
- [Review 1/3] **F-001 (Important): `_MODULE_SCOPE_SILENCERS` is swept as default-deny and is not.**
- [Review 1/3] **F-002 (Important): AC-6's no-invocation guard misses a shell string, and its control
- [Fix 2] dispatched. On F-001 I told the agent **not** to attempt the reviewer's first option as
- [Fix 2] `098a19c` + `e9f0e8f`. **Both Important findings closed by MECHANISM, not by narrowing** — and I verified the two decisive mutants myself on disk rather than relaying them, each planted and reverted with `tests/test_clues.py` restored to md5 `942627df2b6df5a003bf52775ab1d398`: the `os.system(... --check-log meta/kanban/suite-timing.log)` shell string is now **RED** at `test_no_guarded_source_invokes_the_check_log_subcommand`, and a module-scope `raise unittest.SkipTest(...)` under a host-state `if` (planted after `from __future__`, so it is legal and truly at module scope) is now **RED** at `test_no_guarded_module_silences_itself_at_module_scope`. Both survived cycle 1.
- [Fix 2] F-001's three halves, which is the shape my brief prescribed and the agent implemented: **derived** where an authority exists — `_pytest_surface()` over `dir(pytest)` under the same public+callable filters the first module uses (88 public, 84 callable on pytest 9.1.1, all 84 classified with grouped reasons), red on an unclassified name, a phantom, or the set reverting to a literal; **explicit members with reasons and discriminating controls** where no `dir()` could ever supply them (`SkipTest`, `os._exit`, and the three *bindings* `pytestmark`/`collect_ignore`/`collect_ignore_glob` — a binding is not a call, so no surface enumerates it); and **recorded misses** for what remains (helper indirection, and a silencer aliased then called). Closed by mechanism: `unittest.SkipTest`, `os._exit`, `collect_ignore`, `collect_ignore_glob`.
- [Fix 2] F-002 closed at the root cause first: the rule is now ONE function (`_check_log_invocations`) that all three tests call, with the **substring** predicate, and `test_the_invocation_rule_is_the_one_the_guard_runs` reads this module's own source and goes red if any test in the class walks `ast` itself again — which is the defect cycle 1 found (a control certifying a copy of the predicate) made structurally impossible rather than merely fixed.
- [Fix 2] **two things the agent flagged rather than hid, both honest and both passed to the reviewer to judge rather than accepted by me**: the emptied-module floor is 90 and NOT derived — it declined to derive it from `git show main:…` because that would put a git/`main`-ref dependency, and a possible skip, into the module whose entire subject is removing host dependence from verdicts (that reasoning looks right to me, and it is paired with a derived equality so the floor is the weaker half of a two-part check); and the `error(...)` exemption trusts a *shape*, with the discriminating half measured (`error` on a non-parser IS reported). It also flagged that it hand-counted the sweep's new totals and asked for a re-tally.
- [Fix 2] a near-miss it reported rather than quietly fixing, and the right call: its first shell-string control carried the literal `meta/kanban/suite-timing.log`, and **the other module's AC-1 guard immediately reported it** — that guard working exactly as designed, on this card's own author. The committed control spells the destination `PATH`. It also recorded a false start (a plant above `from __future__` produced a collection error, not a skip) instead of dropping it.
- [Review 2/3] dispatched in **confirmation mode**, as cycle 1's reviewer judged appropriate: the delta is confined to two test files and the sweep, and `rank_durations.py` was not touched this cycle. Priority 1 is whether closing the two findings minted a third claim wider than its mechanism — the card's own subject, and the fix added three new mechanisms and seven new sweep rows. It was told to try to BORROW the `error(...)` exemption, to re-tally the hand-counted sweep, and to check that nothing hid behind `test_the_definition_shape_is_not_an_invocation` keeping its name while widening from one control to four.
- [Review 2/3] **7.5** — below `min_score: 8`, `min_improvement` missed, trajectory **DOWN** from 8.0.
  Severity gate FAILS on **two new Important findings, both in the family this card exists to close**,
  both grounded in planted-and-reverted mutants with discriminating controls.
- [Review 2/3] **F-201: the module-scope-binding exemption absorbs a real invocation — and it
  re-opens the exact route cycle 1's F-002 was about, through the exemption added to fix it.** Cycle 1
  found the guard matching an equality and missing a shell string; the fix widened the predicate to a
  substring match, then exempted *every* module-scope `ast.Assign` unconditionally on its value. So
  hoisting cycle 1's own killed mutant into a module-scope constant makes it survive: M3 (inline)
  KILLED, **M2 (hoisted) SURVIVED at 854 passed, rc=0**. The hole is exactly `NAME = "<command line>"`
  at module scope — the most idiomatic spelling in this repo, and the one shape that looks covered
  because `ARGV = [...]` sits in the positive controls. The missing discriminator is the one the
  sibling rule already has: **does the bound name reach an executor?** `_live_log_references` answers
  that with its taint step; this rule reimplemented the shape and dropped that half.
- [Review 2/3] **F-202: `__test__ = False` silences a guarded module with a green session, and it is
  in neither the enumerated set nor the recorded misses.** I verified this myself in a sandbox rather
  than relaying it: a module with two failing guards plus one other module collects as **`1 passed`,
  rc=0** — both failures silently gone. Planted in `tests/test_clues.py` it took **386 tests to
  nothing with 468 passed and both guard modules green**. That is the F-308 verdict in its quietest
  form — quieter than `collect_ignore` (which only works in conftest.py) and quieter than `SkipTest`
  (which at least prints `1 skipped`). The rule's own standard forecloses the "nobody writes that"
  defence, since it reports `importorskip`/`xfail` with the comment "Not a spelling anyone in this
  tree writes, and reported anyway". No live `__test__` exists in the tree (223 files grepped).
- [Review 2/3] **what cycle 2 DID hold, re-derived rather than trusted**: `_pytest_surface()` is exact
  (88 public / 84 callable / 84 classified / 0 unclassified / 0 phantom, and the filters genuinely are
  the same two the first module applies — the reviewer hunted for a pytest silencer outside the set
  and found none); both recorded misses are genuinely open with a red-able bound; the RC-1 pin is real
  (≥3 callers, zero re-derivers); F-004's fix was verified **differentially over 283 sources with zero
  differences**; and G-2 was re-derived at name AND body level, +1/−0 and +9/−0, nothing hiding behind
  the kept test name.
- [Review 2/3] it **agreed with both flagged bounds**: the undrived floor of 90 is the correct
  resolution (deriving from a `main` ref would put a git dependency and a possible skip inside the
  module whose subject is removing host dependence from verdicts), and F-005's dismissal with G-12 is
  right. It also answered the hand-counted sweep: rows 56 → 67, but **PINNED is 32 not 37** (net +1
  against a declared +4), and the four buckets are not a partition. Minor, since every row carries its
  own checkable verdict — but pointed, because row F-6 DELETED a prose count on the grounds that "a
  count in prose cannot go red", and the header table is four prose counts.
- [Review 2/3] **the generalisable rule it extracted, which is the most valuable thing in this report
  and belongs in the retrospective's promotion pass:** *an **exemption** is a claim, and it needs the
  same control a set member needs — caught WITH it, missed WITHOUT it, and the residue recorded as a
  bound.* Both of this cycle's defects are exactly that rule unmet: `_check_log_invocations`' three
  exemptions have controls for what they *exempt* and none for what they must not **absorb**, and the
  binding set has no completeness substitute for the audit it opted out of. This is a sharper
  statement than either CARD-238's or CARD-228's, because it names the *exemption* — the construct
  both of those cards reached for as the honest escape hatch — as itself needing a falsifier.
- [Escalated] 2026-10-17T00:30Z — **score below min_score, min_improvement missed, trajectory down,
  and family regression attributed to the previous fix.** · station: **architect/owner** · the
  reviewer's own words: a third cycle would be "the loop asked to audit the exemptions it just
  wrote", and it recommends not running one automatically. Worktree and branch KEPT.
- [Escalated] **neither finding is a live violation today** — no `__test__` exists anywhere in the
  tree, and no hoisted-constant invocation exists either — and the card's substantive work is sound
  across two cycles of adversarial checking: the first module's derived surface, AC-1/2/3/5, the
  deliberate `--check-log` reader, the version floor (including the third statement nobody had
  noticed), and the struck host-state silences. What is unmet is the *completeness of the new
  module's own exemptions*.
- [Escalation resolved] 2026-10-17, **owner decision: SPLIT.** One bounded pass doing **only F-202**,
  whose control comes free from the existing parametrised pair and which closes the quietest hole in
  the suite; **F-201 recorded as a measured bound with a control**; the taint step carded as
  **CARD-242**. No cycle 3 — the reviewer's objection stands that a third cycle would be the loop
  auditing the exemptions it just wrote, which is how CARD-238 reached five.

### Orchestrator log

- [Why TDD is true on this card] Every AC here is of the form "a test exists that fails when X
- [The one thing that would make this card fail the way CARD-238 nearly did] Closing these bounds
- [Measured figures carried over, so nothing here needs re-deriving] the join forms return `[]`; the
- [Why TDD is true on this card] Every AC here is of the form "a test exists that fails when X
- [The one thing that would make this card fail the way CARD-238 nearly did] Closing these bounds
- [Measured figures carried over, so nothing here needs re-deriving] the join forms return `[]`; the
- [Why TDD is true on this card] Every AC here is of the form "a test exists that fails when X
- [The one thing that would make this card fail the way CARD-238 nearly did] Closing these bounds
- [Measured figures carried over, so nothing here needs re-deriving] the join forms return `[]`; the
- [Env] forge unknown (no resolvable plugin manifest; no meta/.skills.yml)
- [Dispatch] started 2026-10-16T20:45Z, after CARD-228 merged rather than beside it. **The owner
- [Scope] 8 files, THREE beyond the card's `Touches:` — and each is required by an AC the card itself writes: `tests/test_guard_integrity.py` (new; AC-4 says a second module is the ONLY route, because one module cannot judge its own module-level skip), `tests/test_sourcing_image.py` (AC-5: "fixed in their own modules"), `tests/README.md` (part 5). My read, passed to the reviewer to agree or not: this is an **under-specified `Touches:` at decompose time**, not scope growth — the card's own body prescribes all three — and the agent recorded it rather than letting it read as excess. `[Touches drift]` recalibration, not a contract violation. Note the known overlap with CARD-236 on `meta/profiling/`: CARD-236 is not started, so no live conflict, but it will rebase.
- [Build gate] 341 → **398** in tests/test_suite_profile.py, **zero test functions removed** (the agent `ast`-diffed names against `git show HEAD:`), plus a new 42-test module. Its own build gate over the files it touched: 728 passed. Verified by me independently: 341 on main, 398 here.
- [Guard] **G-1 verified by md5, and the agent's caveat is the right one.** The main repo's `suite-timing.log` stands at `be3dfae8a428d62aec0087926c89b44d`, 3016 bytes — matching what the agent reported, and consistent with the two well-formed entries I appended at this wave's merge gates. It said plainly that it holds no earlier md5 of its own, so its claim is "unchanged since I started" and not "unchanged ever". That is the honest form of that claim.
- [Correction to MY OWN dispatch brief] I told the agent "the file now collects more than 341 — CARD-228 merged since. Measure, do not trust the number." **The instruction was right and my premise was wrong**: `tests/test_suite_profile.py` collects exactly **341** on `436717e`. CARD-228 added its tests to `test_book_difficulty_dots.py` and `test_book_interior_type_floor.py`, not here. I verified 341 on main myself after the agent said so. It also corrected a second carried figure: the compound mutant survives at **341 passed, not 250** — 341 is what that module collects, so it survived *every* test in it; 250 was presumably a narrower selection in CARD-238's cycle-5 worktree. Same conclusion, better number. **That is the fourth and fifth time today a downstream agent corrected a figure I passed on**, which is now a pattern about me and not about them: I have been relaying measurements from reports without re-deriving them.
- [AC-7 working as designed] the sweep found **five claims false on measurement, and two were the agent's OWN, written in this pass and caught by controls this card wrote** — `PLATFORM_GATED_SPELLINGS` carried `info` (a property, not on the surface), and `_MODULE_SCOPE_SILENCERS` carried `skip_module` (**which does not exist in pytest**) and `fail` (errors loudly, so not a silencer). That is the F-403 shape twice inside the pass meant to end it — and the sweep caught both before review did. If this holds up under review it is the strongest evidence yet that CARD-238's 2.7 days bought a real mechanism rather than a habit.
- [Found in passing] a **third** version-floor statement nobody had noticed: the PyPI classifier said `Python :: 3.9+`. So two of three statements agreed with each other and not with the interpreter anyone runs. `pyproject.toml` is now authoritative at `>=3.14`, CLAUDE.md already agreed, and all three are pinned by `TestTheInterpreterFloor`.
- [Review 1/3] dispatched with AC-7's sweep audit as priority 1, on the grounds that if the sweep is decorative the card has reproduced the CARD-238 defect one level of abstraction higher — which is the only way this card can fail quietly. Also asked to judge the one gap the agent named itself (three argparse lines no test executes, asserted structurally only because AC-6 forbids invoking the subcommand) and the one claim it labelled **reasoned, not measured** (the xdist/randomly interleaving, undemonstrable because neither is in the dependency baseline).
- [Raised for the owner, G-5] `cmd-run.md` in `~/MyProjects/forge_1` is **not** edited, correctly. But it is the one file the dispatcher reads at a merge gate, and it documents neither the legal parenthesised post-bracket note nor the illegality of a bare one — **so it is still where the next malformed timing line will come from.** `tests/README.md` now documents both, with the writer named and the `--check-log` invocation shown. I nearly wrote such a line myself today and caught it only by running it through the committed regex.
- [Review 1/3] **8.0, severity gate FAILS** on 2 Important, 0 Critical. Risk MEDIUM, lane DEEP.
- [Review 1/3] **the sweep is NOT decorative — 31 of 33 PINNED rows held the sample, and every one of
- [Review 1/3] it also **confirmed the two claims the sweep caught in its own pass are real** — M5
- [Review 1/3] **F-001 (Important): `_MODULE_SCOPE_SILENCERS` is swept as default-deny and is not.**
- [Review 1/3] **F-002 (Important): AC-6's no-invocation guard misses a shell string, and its control
- [Fix 2] dispatched. On F-001 I told the agent **not** to attempt the reviewer's first option as
- [Fix 2] `098a19c` + `e9f0e8f`. **Both Important findings closed by MECHANISM, not by narrowing** — and I verified the two decisive mutants myself on disk rather than relaying them, each planted and reverted with `tests/test_clues.py` restored to md5 `942627df2b6df5a003bf52775ab1d398`: the `os.system(... --check-log meta/kanban/suite-timing.log)` shell string is now **RED** at `test_no_guarded_source_invokes_the_check_log_subcommand`, and a module-scope `raise unittest.SkipTest(...)` under a host-state `if` (planted after `from __future__`, so it is legal and truly at module scope) is now **RED** at `test_no_guarded_module_silences_itself_at_module_scope`. Both survived cycle 1.
- [Fix 2] F-001's three halves, which is the shape my brief prescribed and the agent implemented: **derived** where an authority exists — `_pytest_surface()` over `dir(pytest)` under the same public+callable filters the first module uses (88 public, 84 callable on pytest 9.1.1, all 84 classified with grouped reasons), red on an unclassified name, a phantom, or the set reverting to a literal; **explicit members with reasons and discriminating controls** where no `dir()` could ever supply them (`SkipTest`, `os._exit`, and the three *bindings* `pytestmark`/`collect_ignore`/`collect_ignore_glob` — a binding is not a call, so no surface enumerates it); and **recorded misses** for what remains (helper indirection, and a silencer aliased then called). Closed by mechanism: `unittest.SkipTest`, `os._exit`, `collect_ignore`, `collect_ignore_glob`.
- [Fix 2] F-002 closed at the root cause first: the rule is now ONE function (`_check_log_invocations`) that all three tests call, with the **substring** predicate, and `test_the_invocation_rule_is_the_one_the_guard_runs` reads this module's own source and goes red if any test in the class walks `ast` itself again — which is the defect cycle 1 found (a control certifying a copy of the predicate) made structurally impossible rather than merely fixed.
- [Fix 2] **two things the agent flagged rather than hid, both honest and both passed to the reviewer to judge rather than accepted by me**: the emptied-module floor is 90 and NOT derived — it declined to derive it from `git show main:…` because that would put a git/`main`-ref dependency, and a possible skip, into the module whose entire subject is removing host dependence from verdicts (that reasoning looks right to me, and it is paired with a derived equality so the floor is the weaker half of a two-part check); and the `error(...)` exemption trusts a *shape*, with the discriminating half measured (`error` on a non-parser IS reported). It also flagged that it hand-counted the sweep's new totals and asked for a re-tally.
- [Fix 2] a near-miss it reported rather than quietly fixing, and the right call: its first shell-string control carried the literal `meta/kanban/suite-timing.log`, and **the other module's AC-1 guard immediately reported it** — that guard working exactly as designed, on this card's own author. The committed control spells the destination `PATH`. It also recorded a false start (a plant above `from __future__` produced a collection error, not a skip) instead of dropping it.
- [Review 2/3] dispatched in **confirmation mode**, as cycle 1's reviewer judged appropriate: the delta is confined to two test files and the sweep, and `rank_durations.py` was not touched this cycle. Priority 1 is whether closing the two findings minted a third claim wider than its mechanism — the card's own subject, and the fix added three new mechanisms and seven new sweep rows. It was told to try to BORROW the `error(...)` exemption, to re-tally the hand-counted sweep, and to check that nothing hid behind `test_the_definition_shape_is_not_an_invocation` keeping its name while widening from one control to four.
- [Review 2/3] **7.5** — below `min_score: 8`, `min_improvement` missed, trajectory **DOWN** from 8.0.
- [Review 2/3] **F-201: the module-scope-binding exemption absorbs a real invocation — and it
- [Review 2/3] **F-202: `__test__ = False` silences a guarded module with a green session, and it is
- [Review 2/3] **what cycle 2 DID hold, re-derived rather than trusted**: `_pytest_surface()` is exact
- [Review 2/3] it **agreed with both flagged bounds**: the undrived floor of 90 is the correct
- [Review 2/3] **the generalisable rule it extracted, which is the most valuable thing in this report
- [Escalated] 2026-10-17T00:30Z — **score below min_score, min_improvement missed, trajectory down,
- [Escalated] **neither finding is a live violation today** — no `__test__` exists anywhere in the
- [Escalation resolved] 2026-10-17, **owner decision: SPLIT.** One bounded pass doing **only F-202**,
- [Fix 3, the owner's split] `5d1ee06`, loop **468 → 476 passed**, nothing removed. **Its hardest instruction was to leave F-201 alone, and it did** — I verified that rather than trusting it, by AST-comparing `_check_log_invocations` between `e9f0e8f` and HEAD with docstrings stripped: **identical**. `tests/test_suite_profile.py` was not touched by this pass at all; the delta is the guard module and the sweep. A pass that does less is what ends a loop, and this one did.
- [Fix 3] F-202 closed by mechanism, and the agent **corrected the reviewer's "the control comes free" claim rather than relying on it**: half true — both binding tests do parametrise from the set, so the member needs no new machinery, but `test_every_binding_it_names_has_a_control` is red on a member with no control, so the control had to be added explicitly. Measured through the deployed rule: reported WITH the member, `[]` WITHOUT it. The `__test__` mutant that SURVIVED in cycle 2 at 468 passed is now **RED at 1 failed / 76 passed**. It also re-measured the verdict itself: alone `rc=5`, beside one other module **`1 passed`, rc=0**.
- [Fix 3] it **declined a fourth exemption on purpose and said why**: `__test__` is reported on any binding of the name, not only a falsy one, because every member of that set is value-blind and a value test would have been a fourth exemption in the module whose entire review history is about exemptions. That is the new rule being applied rather than cited.
- [Fix 3] **F-201's recorded bound is measured NON-VACUOUS, which is the cleverest thing in the card**: the deployed rule returns `[]`, while the same rule with its module-scope exemption narrowed to value equality — one of CARD-242's two candidate closures — returns the hoisted command line. So **CARD-242 cannot close the route without this test going red**, which is exactly CARD-242's own AC-5. The bound polices its own successor.
- [Fix 3] **I corrected one thing the pass got wrong, and it matters beyond this card.** F-201's status was written as `dismissed`; I changed it to `deferred` with a `status_note`. `dismissed` is what forge:retrospective's review-learning export mines into the cross-project `review_false_positives` signal, which forge:review then consults to avoid re-flagging known-dismissed patterns. F-201 is a real, measured finding deferred to CARD-242 by owner decision, not a false positive — recording it as dismissed would teach **every future review on every project** not to flag an exemption that absorbs what it guards, which is the exact opposite of this card's lesson. The same distinction was drawn correctly on this card's cycle 1 and on CARD-228's cycle 3; this pass regressed it.
- [Fix 3] it also declined to commit the cycle-2 YAML on the branch, because main already tracks it at `473cc70` and committing it there would create an add/add conflict at merge — correct, and it told me to sync the statuses instead, which I did.
- [AC/EC/G gate] dispatched. AC-7 is the item it was told to weigh hardest: two cycles found four claims that failed its test, so the question is not whether the sweep exists but whether it is TRUE NOW. It was also told that recorded bounds are a legitimate outcome here by owner decision, and that what to check is that each is measured, **non-vacuous**, and disclosed rather than implied — with F-201's self-policing bound called out as the one worth verifying.
- [AC/EC/G gate] **PASS — every AC (1-7) and every guardrail (G-1..G-6) demonstrated**, no `unverified`,
  no `violated`. 14 mutants, each in its own fresh process, each restored from a byte copy with md5
  re-verified; final restoration audit clean. Four results worth keeping:
  * **G-2 was re-derived, not relayed** — the gate measured 341 on `main` itself (the figure my dispatch
    brief got wrong) → 399 at HEAD, `ast` name diff 87 → 95 with **0 removed**, and then swept the 87
    shared functions at **body level**, finding exactly one with fewer statements:
    `test_the_control_for_each_spelling_depends_on_the_set`, which lost the `setattr`/`finally` global
    rebinding (that was F-10's fix) while keeping its assert and gaining the joiner parametrisation.
  * **G-3 by construction, not by inspection** — `TIMING_LOG_LINE` AST-identical to main, and a full
    top-level comparison of `rank_durations.py` with docstrings stripped: two things added
    (`_RATE_BRACKET`, `check_log_report`), **nothing removed**, and only `main`'s argparse wiring
    changed. No parsing function was touched, so the 40,214-line identity is preserved by construction.
  * **G-4 the strengthening direction only** — a per-name diff of `_SURFACE_CLASSIFICATION` against main:
    membership identical, three names moved **out of** `KIND_NEITHER` into the new `KIND_JOINER`, two
    reasons corrected, and **nothing moved into `KIND_NEITHER`**. So the audit was not weakened to fit
    a member, measured rather than asserted.
  * **AC-6 exercised for real** — it ran `--check-log` by hand on three logs it constructed: well-formed
    → rc=0; **CARD-217's bare-trailing-note line → `malformed: 1`, rc=1**; the parenthesised note →
    clean. And the md5 of all three was unchanged after each run, so the reader really only reads.
- [AC/EC/G gate] it declined to round up two things, and both are the right call:
  * **the recorded bounds are real holes, and one is idiomatic** — F-201's survivor is
    `NAME = "<command line>"` at module scope then executed, the most ordinary spelling in this repo,
    and it survives at 476 passed today. So **CARD-242 is load-bearing, not bookkeeping.**
  * **one blemish inside AC-7's own artefact**, which I then fixed: sweep row **E-8** read PINNED while
    its own text carried "not borrowable without actually building a parser" — the sentence row E-10 two
    lines below records as FOUND FALSE, and E-9 records E-8's third exemption as false too. The sweep's
    own precedent settles it: D-6 and E-3 were **demoted** from PINNED when falsified. E-8 is now
    demoted the same way, naming E-9 and E-10, with the false clause struck in place and a pointer
    rather than deleted. `9665673`. A reader sampling E-8 alone would have taken a falsified claim as
    holding — the defect the sweep exists to prevent, committed inside the sweep.
- [Merge gate] rebased onto main `dfdaabb`. **The rebase hit an add/add conflict and it was my fault**:
  I had copied `meta/review/CARD-239-claim-sweep.md` into the main repo and committed it while the
  branch also creates it. Resolved to the commit being applied at each step (`--theirs` is the applied
  commit during a rebase, not the upstream) and verified afterwards that the E-8 demotion survived and
  that main's corrected cycle-2 YAML — the `dismissed` → `deferred` fix — is untouched, since the branch
  does not carry that file. The agent had warned about exactly this shape for the cycle-2 YAML and
  avoided it; I created it for the sweep file.
