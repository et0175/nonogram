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
**Review score:** —
**Started:** 2026-10-16T20:45:00Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

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

### Orchestrator log

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
