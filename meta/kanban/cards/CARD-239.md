# CARD-239: The timing-log guards' remaining bounds, and the one place that reads the log on purpose

**Status:** in_progress
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
- [Env] forge unknown (no resolvable plugin manifest; no meta/.skills.yml)
- [Dispatch] started 2026-10-16T20:45Z, after CARD-228 merged rather than beside it. **The owner
  approved starting this card alongside CARD-240, and I held it deliberately**: it edits
  `tests/test_suite_profile.py`, and CARD-228's final pass was changing the very file that test's
  frozen render-set grep scans (`rank_durations.RENDER_API_PATTERN`, applied to the raw text of
  every file under `tests/`). CARD-228 ended up at 0 matches so the collision never materialised —
  but that was not knowable in advance, and the same shape cost CARD-213 a merge gate earlier today.
  Starting from a base that already contains `08eecf3` costs ~20 minutes and removes the question.
