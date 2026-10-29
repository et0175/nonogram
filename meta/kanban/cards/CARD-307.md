# CARD-307: Node-id check refs read as alive without resolving to a definition — the false alives named, the honest gaps demoted, and the ones held up only by bookkeeping given a table

<!-- RETITLED 2026-10-29 on owner decision. The retired title was "A `path::nodeid` check ref is structurally dead on this board — 30 of them read as mechanically checked, and the validator cannot resolve any of them", and it was wrong in both halves: the count was 30 against a measured 23, and 20 of those 23 DO resolve. It is retired rather than adjusted because the lesson is that **a title carrying a figure goes stale** — this one did within a day, while three cards landed docstring tables that fixed most of its subject incidentally. The new title names the MECHANISM and the three outcomes, which do not drift: a ref can read alive without resolving to a definition; the repair is to name the false alives, demote the honest gaps, and give a table to the refs held up only by bookkeeping. No number appears in it on purpose. -->

**Status:** skipped
**Priority:** P1
**Category:** tech-debt
**Estimate:** 0.5d <!-- RE-SCOPED 2026-10-29 from 1d, after the third premise re-measurement. 1d was priced against "30 refs the validator cannot resolve". Measured over all four authorities: 580 refs, 23 in node-id form, and 20 of the 23 already resolve through docstring tables CARD-284/291/294 landed incidentally. The live work is FOUR table entries across two files (tests/test_player_bundle.py, which spells zero of its own three node ids, and tests/test_export_pdf.py) plus THREE refs to decide -- two honestly dead, one the board's only true false-alive. Within sizing.min_estimate 0.25d. -->
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
**Closed:** 2026-10-29 (cut, not built)
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

**So the defect is almost never a dead ref — it is a FALSE ALIVE**, and *that*
conclusion survived every re-measurement even as the figures did not. The card's
framing had it backwards, and the inverted framing matters: a round told to "repair
thirty dead refs" would look for warnings and find a handful.
<!-- The figures that stood here (31 of 33) are SUPERSEDED by the third census
below, which read all four authorities: 23 node-id refs, 20 of them resolving. Kept
as the shape of the finding rather than deleted, because the direction -- false
alive, not dead ref -- is what two wrong counts both pointed at. -->

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

## [PREMISE RE-MEASURED A THIRD TIME — 2026-10-29, after CARD-308's round. The headline is WRONG and the card is MUCH SMALLER.]

CARD-308's round contradicted this card's figures; the orchestrator re-derived
them from all four authorities and **the round is right**. This card's title and
its "30 refs" framing no longer describe the board.

**What the earlier censuses missed.** The 469-ref figure omitted **`trace.yml`'s
`tests:` lists — 510 refs, the single largest authority** — and
`requirements.yml`'s block-form `check:` entries. Counting all four:

```
adr inline check: {kind: test}       44
requirements.yml  test:              401
requirements.yml  block-form check:   10
trace.yml         tests:             510      <- omitted entirely before
DISTINCT TOTAL                       580      (was reported as 469)
  node-id form                        23      (was reported as 33)
  bare-name form                     557
```

**And the node-id partition is nothing like the headline: 20 of the 23 resolve.**

```
defined in its own module   20     <- the docstring tables CARD-284/291/294 landed
no definition anywhere       3
reported dead, test exists   0
```

So this card's **retired title** — *"30 of them read as mechanically checked, and
the validator cannot resolve any of them"* — was **stale and never right in that
form**. A round briefed on it would hunt thirty refs and find three. The title was
replaced on 2026-10-29 with one that carries no figure, for exactly this reason.

### The actual live scope, enumerated

**Three refs with no definition, all in `tests/test_public_player_pages.py`:**

| ref (tail) | resolvers | class |
|---|---|---|
| `test_assembled_site_is_self_contained` | **0** | honestly dead — the validator reports it correctly |
| `test_pages_work_with_analytics_blocked` | **0** | honestly dead — reported correctly |
| `test_no_homegrown_tracking` | 3 review YAMLs | **the only true FALSE ALIVE on the board** |

**Four refs defined but RESOLVED FROM AFAR — a third shape neither this card nor
its briefs named, and the round's real find.** Their own module never spells the
`path::name`, so something else resolves them:

- `tests/test_player_bundle.py` spells **ZERO** of its own **three** node ids.
  Two of them (`…match_the_encoder`, `…readonly_and_deterministic`) are resolved
  by **exactly two CARD-218 review YAMLs and nothing else** — prune two files
  under `meta/review/` and both go dead with no code change. The third
  (`…clean_of_answers`) survives only because **another module's** table
  (`tests/test_public_player.py`) happens to carry it.
- `tests/test_export_pdf.py` spells **zero** of its one — ADR-0042/R4, with **57**
  resolvers of which exactly one (`tests/test_admin_serving.py`) is code.

**So the repair is four docstring-table entries across two files, plus three refs
to resolve — not thirty.** `tests/test_player_bundle.py` is the priority: it is the
only module on the board carrying node-id refs with **no** in-module resolver and
**no** second code resolver.

### What this does to the card

- **AC-1's enumeration stands and gets cheaper**, but its partition must include
  **RESOLVED_FROM_AFAR** — defined, alive, and resolved only by bookkeeping — which
  neither of this card's two earlier partitions had. That class is invisible to
  "dead or alive" *and* to "has a definition", which is why it survived two censuses.
- **The bare-name respelling repair is mostly already done**, by three cards that
  did it incidentally. Report that rather than re-doing it.
- **Estimate drops.** 1d was priced against thirty refs. Four table entries and
  three decisions is closer to **0.5d**, and the remaining judgement — whether 20
  shim-resolved refs are an acceptable end state — is a question for the owner, not
  work.
- **The two honestly-dead refs are the correct state** and may be the right place
  to stop: per ADR-0039 an honest gap is fixable and a phantom one is not, so
  demoting them to `review-lens` with a recorded reason is a **success**, and
  writing tests merely to retire warnings is not.

**Method note, because this card's premise has now been wrong three times.** The
first census used a regex that over-counted; the second omitted the largest
authority; both were corrected only when something else measured the same thing.
**Derive from all four authorities, and cross-check the count against a second
implementation before writing a figure onto a card.**

---

## CUT 2026-10-29 — the measurement that retired this card

**This card is skipped, not done. No code was written. It is kept because the
measurement that killed it is the useful artefact, and because twelve other cards
carry a "see CARD-307" pointer — they land here and are routed on below.**

The card was re-measured a fourth time before dispatch. Three of its four figures
held. The fourth finding killed it: **it is aimed at a population that produces no
warnings, and the population it dismissed in a parenthesis produces all of them.**

### What held

Derived by walking `requirements.yml`, the ADR `check:` entries and `trace.yml`'s
`tests:` lists, splitting on commas the way `split_check_ref` does:

- **23 distinct node-id refs** on the board — the card's figure, confirmed.
- **20 of them are defined in their own file and resolve** — confirmed.
- **4 table entries across 2 files** (`tests/test_player_bundle.py` ×3,
  `tests/test_export_pdf.py` ×1, neither spelling its own node id) — confirmed.

### What killed it

**1. The node-id population produces ZERO warnings.** Run on the validator of
record at `main` (`0 error(s), 100 warning(s)`): not one of the 100 names a node-id
ref. The card's title claims a `path::nodeid` ref is *"structurally dead on this
board"*. It is not, and has not been since the docstring tables landed.

**2. AC-5 was satisfied by the bug it was written to catch.** It required that
dead-ref warnings for node-id refs *"fall to zero"*. They were already zero —
including for three refs with **no definition anywhere**. The defect was never that
warnings existed; it was that they did not, while three refs had nothing behind
them. An AC that the defect satisfies is worse than no AC.

**3. The "three refs to decide" are not what the card says.** It calls them *"two
honestly dead, one the board's only true false-alive."* All three are **CARD-285's**
— `test_assembled_site_is_self_contained`, `test_pages_work_with_analytics_blocked`,
`test_no_homegrown_tracking` — and all three are **defined on CARD-285's branch**
(`:2397`, `:2577`, `:2679`). None is honestly dead. They become ordinary live refs on
that card's merge. Live work here: **zero**.

**4. The real dead-ref population is the shape this card set aside.** Of the 100
warnings, **23 are DEAD check refs**, and every one is a **bare class name** —
`TestGenerateRandom_*`, `TestSolveStrategies_*`, `TestPuzzleReview_*`,
`TestBookAnswerKey_*`, `PropertyTest_SolveStrategies_*` — across FR-001, FR-028,
FR-029, FR-032, FR-035, FR-040 and FR-042. None has a `class` definition anywhere in
`tests/`. This card dismissed them as *"25 unrelated to this week's work"*. They are
23, and they are the only dead-ref population there is.

**5. All four table entries were a shim by the card's own admission** (item 5). They
exist only to give a text search something to find. The honest repair is to the
predicate, which is forge-side — now **CARD-319**.

### A sixth thing, found on the way and owned by nobody until now

**The validator does not check ADR rule check refs at all.**
`TestDependencyBaseline_IsExactlyPillowAndNumpy` — ADR-0006/R1's ref, with zero
definitions in this repo — appears **nowhere** in the validator's output. Neither
does any other ADR rule ref. The dead-ref check covers AC/EC `test:` keys only.

That is why twelve cards carry hand-written `**DEAD REF**` notes in their System
contract sections: **no gate has ever checked those refs, so humans have been doing a
gate's job by hand.** Routed to CARD-319.

### Where this card's work went

| was CARD-307's | now | what |
|---|---|---|
| the 7 phantom `test:` keys | **CARD-316** | rejected alternatives, retired ACs, one forward declaration — delete the key, write no test |
| re-pointing refs to tests that exist | **CARD-317** | FR-001 ×4, FR-042 ×2, **and ADR-0006/R1's pointer** — plus the stale bound the dead ref was hiding |
| the FR-029 coverage gap | **CARD-318** | 10 refs, genuinely unwritten |
| the predicate repair (item 5) | **CARD-319** | forge-side: a text search standing in for a definition check, and ADR rule refs going unchecked |

**Nothing is lost by skipping this card.** Nothing declares `Depends on: CARD-307`.
The twelve "see CARD-307" pointers are prose and still navigable — they land on this
section, which routes them. They were deliberately **not** rewritten: twelve
mechanical edits to live cards, to repoint a pointer that still works, is the kind of
churn that breaks something quietly.

### The method note worth keeping

The first instrument built for this re-measurement used `\b` in a `git grep -E`
pattern. **`\b` is undefined in POSIX ERE and silently matches nothing**, so every
definition check came back empty and all 23 refs classified identically as false
alives. A second instrument counted `^\[WARN` against output that indents its
warnings two spaces, and reported `0 errors, 0 warnings` for a run that produced 100.
**Both looked like clean results.** Every figure above comes from an instrument
proven in both directions first — it finds a name known to exist and rejects a
nonsense one — which is the only reason the error was caught rather than shipped.
