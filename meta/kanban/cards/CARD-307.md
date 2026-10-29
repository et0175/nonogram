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

## [Amended 2026-10-29 at CARD-291's merge — the inverse direction, measured]

While writing back FR-046's trace row the orchestrator counted `trace.yml` over all
75 links, and found a defect pointing the **other** way from this card's subject:

```
32 covered, 43 partial
of the 43 partial rows, 42 LIST tests (only CON-017 lists none) -- 409 test refs in all
the largest partial row is FR-044 with EIGHTY-FIVE tests
of the 32 COVERED rows, NINE list no tests at all
```

Two things follow, and the second is new work for this card.

**1. `status: partial` carries almost no information about whether a requirement has
tests**, so the `[WARN] requirement has no tests yet (status: partial)` warning it
drives is noise on 42 rows. (This also corrects CARD-291 cycle 1's figures, which
reported "40 partial rows with no tests and three that list tests" — that does not
reproduce. The conclusion was right; the numbers were not.)

**2. ~~Nine rows say `covered` and list nothing.~~ WITHDRAWN 2026-10-29 — this was
the orchestrator's error, and the code says so.** The nine are
`CON-001..008` and `CON-013`, **all CON ids**, and `_check_covered_tests`'s gate 1
errors **only for `FR` ids**: *"NFR/CON are often covered structurally (benchmarks,
ADRs, deploy config) — don't force tests on them."* So an empty `tests:` list on a
covered CON row is **sanctioned behaviour, not a hole**, and calling it "the mirror
of this card's defect" was wrong. Measured: of the 9, **zero** are FR ids.

What survives from that paragraph is the **gate-severity fact**, which is useful to
this card for a different reason: on a `covered` row, gate 3 — a listed test with no
definition — is **`Severity.ERROR`**, not a warning. So a covered row is the one
place on this board where a dead test ref **breaks the build** rather than adding a
line. It still resolves through the same `git grep -w` text search, so it carries the
same false-alive hole; it just fails louder when it fails.

**Add to this card's scope**, since it is the same question in the same file and a
separate card would have to re-derive the same census:

- **enumerate the nine** `covered`-with-no-tests rows, derived from `trace.yml`
  rather than listed here, and partition them like the check refs: a row verified by
  something the `tests:` key cannot express (a golden file, a byte-identity
  tripwire, a review lens) is a **documentation** fix — say what verifies it; a row
  verified by nothing is a **status** fix — it is not covered;
- **and decide what `partial` is for**, because a status that 42 rows carry while
  holding 409 test refs is not a signal. Either it means "some ACs lack tests" and
  the rows are wrong, or it means nothing and the warning should go. Do not flip
  rows one at a time: CARD-291 deliberately left FR-046 `partial` rather than make a
  board-wide convention change from inside one card, and that restraint is the
  reason this is here.

**AC-1 is widened** accordingly, but narrower than first written: the derived
enumeration covers a `check:`/`tests:` ref with nothing behind it, **and** must
partition `covered` rows by id kind, because an empty `tests:` list is a defect on an
`FR` row and deliberately permitted on an `NFR`/`CON` one. A guard that flags all of
them re-reports nine sanctioned rows as findings — which is the same failure as a
guard that flags none.

## [Amended 2026-10-29 by CARD-298's fix round — the cheap repair this card was about to miss]

**A dead node-id ref is usually fixable by RESPELLING IT AS A BARE NAME, not by
writing a docstring table.** CARD-298's fix round found this by refusing the
orchestrator's brief, which had dictated the node-id spelling for ADR-0042/R2's
flip. Measured on that branch, same tree, same binary (the validator of record):

| spelling of R2's `check:` ref | errors | warnings |
|---|---|---|
| `review-lens` (before) | 0 | 107 |
| `tests/test_book_pdf.py::test_every_raster_page_is_declared_with_its_reason` | 0 | **108** — a fresh `DEAD check ref` |
| `test_every_raster_page_is_declared_with_its_reason` | 0 | **107**, warning sets byte-identical |

Reproduced by the orchestrator under the validator's own pathspec:

```
git grep -lw "tests/test_book_pdf.py::test_every_raster_page_is_declared_with_its_reason" \
    -- . ':(exclude)meta/architecture' ':(exclude)*.md'     ->  nothing
git grep -lw "test_every_raster_page_is_declared_with_its_reason" \
    -- . ':(exclude)meta/architecture' ':(exclude)*.md'     ->  tests/test_book_pdf.py
git grep -nE "^def test_every_raster_page_is_declared_with_its_reason" -- tests/
    ->  tests/test_book_pdf.py:1793        # a REAL definition
```

**Why: `git grep -lw <bare identifier>` matches the `def` line itself.** The node-id
form can only ever match prose that happens to quote it. So the bare name is the
**only spelling of a `kind: test` ref that this validator can resolve honestly** —
and ADR-0042/R5's own comment already said so in the same file (*"Every other live
`kind: test` ref in this model is a bare name for the same reason"*).

**What this changes for item 3.** The per-module docstring table is **not** the
default repair. CARD-291 needed one because its five refs live in
`requirements.yml` **as node ids** and that file is excluded from the search, so
nothing in code could ever spell them — but even there, respelling them as bare
names would have resolved them without a table. Thirty tables is far more work
than thirty respellings, and a table is one more thing to drift.

**So partition the repair, not just the refs:**

- **bare-name respelling** where the test's name is **unique in the tree** — the
  cheap, no-new-machinery fix. Verify uniqueness; do not assume it.
- **docstring table** only where a bare name would be **ambiguous** (two tests
  sharing a name across files) or where the file/location is itself load-bearing to
  the rule. Then the table plus CARD-291's two-direction guard is right, and the
  skip-mark clause above applies.
- State the loss honestly either way: **a bare name drops the file**, so a ref no
  longer says where its test lives, and a rename to a colliding name becomes
  possible. That is a real cost of the validator's design, not of this choice.

## And the mirror image: a node-id ref that reads ALIVE on prose alone

**ADR-0042/R4** names `tests/test_export_pdf.py::test_the_dependency_baseline_is_still_closed`.
Measured: **57 tracked files** contain that literal string under the validator's
pathspec — review YAMLs, the scored backlog, profiling logs — and **not one is a
definition**. A real `def` does exist, at `tests/test_export_pdf.py:1249`, so R4's
answer is currently *correct*; its **mechanism is not**. Delete or rename that test
and R4 keeps reporting alive off the 57 prose hits.

That is the same shape as ADR-0006/R1 (zero definitions, 110+ prose resolvers)
except the answer happens to be right, which makes it harder to find and no less
broken. **Both belong in this card's class (c)/false-alive partition**, and R4 is
one more reason AC-1's enumeration must classify by **whether the resolving hit is a
definition**, never by whether `git grep` exits 0. ADR-0042/R5's comment already
flags R4 "for whoever next touches R4"; this card is that owner.

## [PREMISE RE-MEASURED at wave-66 opening — 2026-10-29, orchestrator. The card's own figures were wrong.]

This card was cut from a round's report and said *"30 of them read as mechanically
checked"* with *"25 not from this week's cards"*. **Derived from the files instead
— and the characterisation, not just the count, was wrong.**

Method: walk every `check: {kind: test, ref: …}` in `meta/architecture/decisions/adr/**`
and every `test:` key in `requirements.yml`; for each ref, run the validator's own
`git grep -lw <whole string>` under its real pathspec, and separately look for a
`def`/`class` definition. (Note for whoever repeats this: **do not put `\b` in the
definition regex** — it is undefined in POSIX ERE, which `git grep` uses, so it
silently matches nothing. That bug produced a first census claiming every ref was
undefined, including ones verified by hand minutes earlier.)

```
verifying refs in the model        469      (47 `check:` + 422 `test:`)
  bare-name form                   436      <- the board's overwhelming norm
  node-id form                      33      <- the anomaly this card is about

of the 33 node-id refs:
   2   reported DEAD and no test exists        <- the HONEST state; nothing to fix
   2   falsely ALIVE on prose, NO test at all  <- the worst class
  29   falsely ALIVE on prose, a test exists   <- mechanism broken, answer right
   0   reported dead while a test exists
```

**So the defect is almost never a dead ref — it is a FALSE ALIVE.** 31 of 33 read as
mechanically checked, and only 2 are reported dead at all. The card's framing had it
backwards, and the inverted framing matters: a round told to "repair 30 dead refs"
would look for warnings and find two.

**The two with nothing behind them** are `test_no_homegrown_tracking` (ADR-0041/R6
and its `requirements.yml` twin — 4 prose resolvers, no definition anywhere) and,
reported honestly dead, `test_assembled_site_is_self_contained` and
`test_pages_work_with_analytics_blocked`. Those four are the real gaps; the other 29
are a spelling problem.

**And 436 refs already use the bare name**, which the validator resolves to the
`def` line itself. That is the strongest argument for the respelling repair above:
the node-id refs are not a convention, they are 7 % of the model deviating from it.

**A third category this card must not flatten.** CARD-291's five are in the
"falsely alive, test exists" bucket by the mechanical test, but their resolver is a
**deliberate docstring node-id table paired with a two-direction guard** that
asserts each ref resolves to a real definition *and* appears in the table. That is a
shim with a control, not an accident — and `tests/test_public_player.py` carries the
same pattern. **Partition those out and leave them alone**; they are the model for
the ambiguous cases, not work.

**AC-1 is amended again**: the enumeration must classify every node-id ref into
these five buckets (honest gap · false-alive-no-test · false-alive-test-exists ·
guarded-shim · reported-dead-test-exists), because "dead or alive" is the
distinction that hid the problem.

## [Added 2026-10-29 after CARD-298's review cycle 2 — ADR-0042/R2's new ref is a shim, and it is already revived]

The partition above gains a live member, and it was created **by this board's own
pipeline within the day**.

CARD-298 flipped ADR-0042/R2 from `review-lens` to
`check: {kind: test, ref: test_every_raster_page_is_declared_with_its_reason}` — a
**bare name**, correctly, because the node-id spelling measures as a dead ref.
Measured on `main` the same day, under the validator's own pathspec:

```
git grep -lw "test_every_raster_page_is_declared_with_its_reason" \
    -- . ':(exclude)meta/architecture' ':(exclude)*.md'
→ meta/review/20261029T073500Z-CARD-298-cycle1.yml     # CARD-298's OWN cycle-1 review report

git grep -lE "^[[:space:]]*(def|class)[[:space:]]+test_every_raster_page_…" -- tests/
→ nothing on main — the test lives on CARD-298's branch
```

So **right now R2's ref reads alive on `main` with no test behind it at all**, and
the sole resolver is the review report the orchestrator synced. Once CARD-298
merges the test arrives and the answer becomes right — but the **mechanism stays
prose**, exactly as with ADR-0042/R4: delete or rename the test later and R2 keeps
reporting alive off the review YAML.

The excludes are built at `validators/utils.py:336-338` as exactly
`[":(exclude)<arch_root>", ":(exclude)*.md"]`, so `meta/review/**`,
`meta/kanban/**` and `meta/profiling/**` are all in domain.

**Do not "fix" this by changing the spelling.** The alternative is strictly worse —
a fresh DEAD ref, measured at 107 → 108. R2 belongs in the **bare-name-respelling**
partition as an *already-done* instance whose resolution is nonetheless prose, and
this card's enumeration should report it that way rather than as repaired. It is
the clearest available example of why the repair is forge-side: a correctly-spelled
bare-name ref, a real test, and a resolution that still does not look at the
definition.
