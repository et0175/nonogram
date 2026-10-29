# CARD-307: A `path::nodeid` check ref is structurally dead on this board — 30 of them read as mechanically checked, and the validator cannot resolve any of them

**Status:** ready
**Priority:** P1
**Category:** tech-debt
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** CARD-291's implementation round, 2026-10-29, which discovered it while clearing its own five refs; the general form stated in §7 item 2 of that round's report and independently reproduced by the orchestrator. Related: ADR-0032/R3's precedent, CARD-294/FR-045's docstring-table fix. Cut by the orchestrator on owner decision.
**Idea:** —
**Wave:** 66
**Created wave:** 65
**Deferred waves:** 0
**Depends on:** —
**Touches:** meta/architecture/requirements.yml, meta/architecture/decisions/adr/**, tests/** (one docstring table per affected module), meta/architecture/trace.yml
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

**The mechanism, measured.** The architecture validator resolves a
`check: {kind: test, ref: …}` by `symbol_exists()`, which is
`git grep -lw <ref> -- . ':(exclude)meta/architecture' ':(exclude)*.md'` — a
**text search over the whole `path::name` string**. A pytest node id is never a
code identifier, so for any ref of the form `tests/foo.py::test_bar` the string
appears in **no code file** and the ref reads as a **DEAD check ref** however
green the test is.

CARD-291 proved this the expensive way: it wrote five tests, collected them,
passed them, and the validator still reported all five refs dead — **108
warnings, one more than `main`'s 107**, because flipping ADR-0032/R3 to a node id
*added* a dead ref. Only a third commit cleared them, by writing a "Tests, by node
id" table into the test module's docstring so the validator's `git grep` has
something to find, plus a two-direction test holding the table to the registry.
Measured after that commit: **107 → 102**, five dead refs gone, zero warnings
added.

**So the board is carrying 30 check refs of this shape, 25 of them unrelated to
this week's work** — `TestGenerateRandom_*`, `TestSolveStrategies_*`,
`PropertyTest_SolveStrategies_*`, `TestBookAnswerKey_*`, and two
`tests/test_public_player_pages.py::…` refs. Each reads as mechanically checked.
Some have real tests behind them and are merely unresolvable; some may have no
test at all. **Those two cases are indistinguishable from the outside, which is
the whole defect.**

This matters because `kind: test` exists precisely to mean *mechanically checked*,
as opposed to `kind: review-lens`. An instrument that cannot resolve the refs it
is given makes `kind: test` weaker than it reads — the same class of defect as
`adr-check-refs-must-be-honest`, from the other direction.

## What to implement

1. **Enumerate every `path::nodeid` check ref on the board**, derived — walk
   `requirements.yml` and `meta/architecture/decisions/adr/**` for `check:` entries
   whose `ref` contains `::`. Do not hand-list; the count must come from the files.
2. **Partition them by what is actually behind each one**, with the partition
   itself machine-derived, into: **(a)** a real definition that collects and passes;
   **(b)** a real definition that does not collect (wrong path, renamed, a
   `python_classes` prefix trap — see the note below); **(c)** nothing at all.
   Resolve each with `git grep -nE '(class|def)[[:space:]]+<name>'` **and**
   `--collect-only`, **never** with `git grep -lw`.
3. **For (a): give each module a docstring node-id table**, CARD-291's and
   CARD-294's shape, plus **one test per module** holding the table to the registry
   in both directions — every registry ref for this module resolves to a
   module-level definition in it, **and** every such ref appears in the docstring.
   CARD-291's `test_the_registrys_check_refs_for_this_card_all_resolve` is the
   reference implementation; copy its construction, including the
   `__module__ == __name__` filter, which is what stops an imported `test_` name
   from satisfying it.
4. **For (b) and (c): fix or demote, and say which.** A renamed test gets its ref
   corrected; a ref with nothing behind it is either written or **demoted to
   `kind: review-lens` with the reason recorded**. Per ADR-0039 an honest gap is
   fixable and a phantom one is not — so **demotion is a success here, not a
   retreat.** Do not write a test merely to retire a warning.
5. **Decide whether the repair belongs forge-side instead, and record the
   decision.** The honest fix is for `symbol_exists()` to resolve a ref against a
   **definition** rather than a text match — but that code is in
   `/Users/omelnikova/MyProjects/forge_1/forge/skills/architect-validate/`, **not
   in this repo**. This card cannot change it. State plainly in the card whether
   the per-module tables are the end state or a shim, because a shim that is never
   labelled becomes the end state by default.

## Acceptance criteria

- **AC-1** (the enumeration is derived and complete): *Given* the registry and the
  ADR set, *then* every `check:` ref containing `::` is listed with its partition
  class, and the list is produced by a walk, not by hand. (**Derived**, per
  ADR-0039/R2: a `check:` shape the walk cannot classify is a **FAILURE**, never a
  silent omission.)
- **AC-2** (no ref both passes pytest and reads dead): *Given* the branch, *then*
  for every class-(a) ref the validator reports no dead-ref warning **and** the ref
  resolves to a module-level definition — the two directions asserted separately,
  so neither can stand in for the other.
- **AC-3** (the table cannot outlive a rename): *Given* any affected module,
  *then* renaming one of its named tests reds that module's own table test, and
  deleting one line from its docstring table reds it too — **two mutants, one per
  direction.** CARD-291's reds at `:2033` (`missing`) and `:2036` (`unnamed`) are
  the model.
- **AC-4** (class (c) is honest): *Given* every ref with nothing behind it, *then*
  it is either a written test or an explicitly demoted `review-lens` with a
  recorded reason — and **no ref is left as `kind: test` with no definition**.
- **AC-5** (the count moves in the right direction, measured on the validator of
  record): *Given* `main` and the branch, *then* the validator's dead-ref warnings
  for `path::nodeid` refs fall to **zero** and **no warning of any other kind is
  added** — warning **sets** diffed line by line, not counts compared. Run the
  `forge_1` copy (see G-2).

## Engineering constraints

- **EC:** across every module that gains a table, the table's contents equal the
  set of registry refs pointing at that module — neither direction slack, derived
  from `requirements.yml` rather than restated in the test.

## Guardrails

- **G-1: a falling warning count is NOT evidence of repair.** This board has a
  measured instance of a warning disappearing while nothing was fixed (108 → 107
  from a synced review YAML; see CARD-308). Every cleared warning must be
  corroborated by `git grep -nE '(def|class)[[:space:]]+<name>'`.
- **G-2: use the `forge_1` validator**
  (`/Users/omelnikova/MyProjects/forge_1/forge/skills/architect-validate/scripts/validate.py`),
  **not** the forge plugin cache. The cache reports a phantom
  `[ERROR] ADR-0025 circular supersession` — it counts "supersedes" and
  "superseded by" as two edges. The honest error count on this board is **0**, and
  both CARD-291's and CARD-298's rounds quoted the cache's figure. State which
  binary produced any number you report.
- **G-3: do not write a test to retire a warning.** A test with no subject is worse
  than a demoted lens, because it reads as coverage.
- **G-4: `_` is a word character, so `git grep -w PropertyTest_Foo` does NOT match
  `def test_PropertyTest_Foo`.** This board's naming convention walks straight into
  that hole — measured on EC-029. Use a substring grep or `-w` on the full
  `test_`-prefixed symbol, and confirm the hit is a `def`/`class` line.
- **G-5: `python_classes` is matched as a PREFIX, not a glob** (`startswith`;
  `fnmatch` only if the option contains `*?[`), and `python_files` defaults to
  `test_*.py`/`*_test.py`. A bare `PropertyTest_` class collects **zero** tests
  here (CARD-294's F-1), and a module outside the `python_files` patterns is never
  opened at all (CARD-301). Both are class-(b) causes — look for them.
- **G-6: no test deleted, renamed, skipped or merged except where item 4 corrects a
  ref, and then say so by name.** (**gate**: node-id set difference with
  `-o addopts=''`.)

## System contract (subset — the pipeline re-derives the full list at dispatch)

- ADR-0039/R1 — a claim needs a control that CAN fail (check: review-lens)
- ADR-0039/R2 — a guard's set is derived from an enumerable authority; an unanalysable shape is a FAILURE (check: review-lens)
- ADR-0006/R1 — the dependency baseline (check: **DEAD REF, and the limit case** — `TestDependencyBaseline_IsExactlyPillowAndNumpy` has ZERO definitions anywhere, yet resolves via 110+ files: `backlog-scored.yml`, ~107 `meta/review/*.yml` spanning CARD-030→CARD-251, and prose in `tests/test_export_pdf.py` and `tests/test_puzzle_editor_ui.py`. **The two `tests/` mentions alone defeat any `meta/review` exclusion**, so this ref is unfixable by narrowing the pathspec — it is class (c) and the honest outcome is to write the test or demote the rule's check.)

## Architecture context

- **ADR:** ADR-0039/R1-R2, ADR-0032/R3 (the precedent flip), ADR-0006/R1 (the limit case), ADR-0042 (several of whose rules are lenses awaiting refs)
- **Trace:** meta/architecture/trace.yml — rows whose `check:` changes class are re-stamped. **Note**: `trace.yml`'s own `tests:` list is NOT mechanically read where `status: partial` — `validators/trace.py::_check_covered_tests` gates all three of its checks on `status == "covered"`. Do not report a `partial` row's test list as verified.

## Worktree notes

- The warning *"requirement has no tests yet (status: partial)"* is a **different**
  warning: it fires on `status: partial` in `trace.yml` **alone**, has nothing to do
  with check refs, and does not clear when tests land. Two review cycles have
  already misread it as a missing `tests:` key. Do not try to clear it here.

## [Amended 2026-10-29 after CARD-291's review cycle 1 — the resolve-guard has a second hole]

CARD-291's cycle 1 found it (F-001) and the orchestrator reproduced it: **a check
ref that resolves to a SKIPPED function reads as mechanically checked while the
criterion never runs.** Measured on CARD-291's branch — with
`@pytest.mark.skip` above one of its five criteria the whole file reported *"36
passed, 1 skipped"* and the module's own resolve-guard stayed **green**, because
the guard asserts that a module-level callable of that name *exists*, not that it
executes.

**So item 3's per-module guard is under-specified as written.** Every resolve-guard
this card writes must assert **three** things, not two:

1. every registry ref for the module resolves to a module-level definition in it;
2. every such ref appears in the module's docstring table (the half the validator's
   `git grep` reads);
3. **no resolved function carries a `skip` or `skipif` mark** — `skipif` included,
   because a condition that is true today is a skip today whatever it reads like.

CARD-291 shipped the reference implementation in commit `2eb93c2a`: a module-level
`_silenced(refs, namespace)` helper, kept **out** of the resolve test so its control
can drive it over a **synthetic namespace**. That separation is load-bearing and not
stylistic: at HEAD no function carries a skip mark, so a control asserting over the
real tree would pass whatever the helper did — `return []` included. Its control
also pins that a **live** function is not claimed (which is what stops a
deny-everything helper from passing the two positive assertions) and that a ref
naming nothing stays the `missing` case, so the two assertions cannot stand in for
each other.

Both directions were proved to bite before CARD-291 merged: a skip mark on a
criterion reds the resolve test; `_silenced` short-circuited to `return []` reds the
control.

**Add to AC-3:** the two mutants it requires become **three** — rename a named test
(reds `missing`), delete a docstring table line (reds `unnamed`), and **skip-mark a
named test** (reds `silenced`). A module whose guard passes all three is honestly
checked; one that passes the first two is where this card started.
