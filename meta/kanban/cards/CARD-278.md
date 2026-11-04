# CARD-278: `_blind_propagation` blinds one propagation path of two, so the test named for the branch checkpoint passes without it

**Status:** in_progress
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1c (0.25d)
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** `card/278-the-timeout-cards-tail`
<!--The previous value, card/278-blind-propagation-misses-overlap, named a branch that was never cut: `git branch --list '*278*'` found no such ref at wave 74's open. A ready card carrying a Branch is a stale field, not a resumable attempt. -->
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-278
**Source:** Found 2026-10-23 by the adversarial skeptic that **refuted** CARD-264's cycle-2 finding I-1. It was not what that skeptic was looking for: while proving that `CLAUDE.md:50`'s timeout sentence is true, it ran a combined mutant nobody had run and the result was a test passing for the wrong reason. Reported rather than absorbed, because CARD-264 was at cycle 3 of a 3-cycle budget and a last-cycle widening ships its final edit uncertified (the wave-48 rule).
**Idea:** —
**Wave:** 74
**Depends on:** —
**Touches:** tests/test_timeout.py
**Review score:** —
**Started:** 2026-11-04T03:41Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## The defect, measured before it was written down

`tests/test_timeout.py:479-485` —
`test_the_branch_checkpoint_alone_stops_a_search_propagation_would_not` — has a docstring claiming
*"the only thing left that can raise is the branch-node check"*. **That is false at HEAD.**

The helper `_blind_propagation` (`tests/test_timeout.py:424-451`) monkeypatches
`search_module.propagate` and **only** that. But `src/nonogram/solver/search.py:694` calls
`propagate_overlap(board, ..., deadline)` with the **real** deadline, and `propagate_overlap` carries its
own deadline check at `src/nonogram/solver/propagate.py:1129`. So the search still has a live
propagation-side raise site while the test believes it has none, and `propagate.py:1129` raises
**first**.

**Demonstrated, not argued.** Under a combined line-count-preserving mutant that neutralises **all four**
branch-side check sites (`search.py:1180`, `:1259`, `:1418`, `:1728`), this test **still passes**. A test
whose entire subject is *"the branch checkpoint alone"* survives the deletion of every branch checkpoint.

## Why this is the board's recurring defect family and not a nit

ADR-0039/R1: *a claim the guard makes needs a control that can fail — caught WITH, missed WITHOUT.* This
test's name and docstring claim the branch checkpoint is what stops the search; its body cannot fail when
that checkpoint is gone. It is the same family as CARD-206's empty `GEOMETRY_DOORS` member, CARD-262's
uncontrolled `AsyncFor`/`NamedExpr`, CARD-264's dead `validate_size` token and CARD-264's own two
name-claims-more-than-body controls — but with a cause worth naming on its own: **an isolation helper
that blinds one path of two.** A mock is a claim about what is reachable, and this one was never
measured against the call graph.

Worth stating because it is the generalisable half: `_blind_propagation` is *correct* about the function
it names. The defect is that `search.py` reaches the deadline through **two** functions and the helper
knows about one. Nothing in the suite compares the set of deadline-raise sites reachable from `_search`
against the set the helper blinds.

## What to implement

1. **Blind both paths.** `_blind_propagation` must also stub `propagate_overlap` (or whatever the helper's
   author judges the honest equivalent). Derive the set of raise sites reachable from the search rather
   than hard-coding two: `check_deadline` has exactly **six** call sites in `src/nonogram/solver/` and
   `SolverTimeout` is raised from exactly one place, `propagate.py:221` — but **re-derive that yourself**,
   because a figure in a card is a claim whose only control is recomputation, and this board has been
   wrong about this very count before (CARD-264's brief said four; it is six).
2. **Make the test fail without the thing it names.** After the fix, neutralising all four branch-side
   check sites must **red** this test. That is the acceptance, and it is a measurement, not a reading.
3. **Narrow the docstring to what the body proves**, or widen the body to what the docstring claims —
   and say which you chose. Do not leave a docstring asserting an isolation the helper does not provide.
4. **Consider the standing form, and only propose it.** The durable version of this is a control holding
   *the helper's blind set* to *the raise sites reachable from the code under test*, so a new deadline
   check in a new function reds the helper instead of silently escaping it. Measure whether that is
   cheap. If it is not, say so with the measurement and leave it — a proposal with a number beats a
   mechanism nobody asked for.

## Acceptance criteria

- **AC-1** *Given* `tests/test_timeout.py`'s branch-checkpoint test, *then* neutralising **all four**
  branch-side `check_deadline` call sites in `src/nonogram/solver/search.py` makes it **red**, and the
  unmutated run is green — both states demonstrated on disk, with the mutants line-count preserving.
  (test: `test_the_branch_checkpoint_alone_stops_a_search_propagation_would_not`)
- **AC-2** *Given* the same test, *then* its docstring's isolation claim is true of the helper as
  shipped: every deadline-raise site reachable from `_search` other than the branch checkpoint is
  blinded, and the set was **derived from the code** rather than listed by hand (ADR-0039/R2).
  (test: `test_the_blind_set_is_derived_from_the_solvers_own_call_graph`)
- **AC-3** *Given* the six `check_deadline` call sites, *then* the card states the count it measured and
  the method it measured it with — and the figure is **re-derived**, not copied from this card.
  (evidence: the card's own measurement)
- **AC-4** *Given* the fix, *then* `tests/test_timeout.py` passes unedited in every other respect — the
  other sixteen tests in the file are not weakened, retargeted or deleted to make room.
  (gate: `tests/test_timeout.py`)

## Guardrails

- G-1: **No `src/` change.** The solver's six check sites and its one raise site are correct; this is a
  defect in a *test helper's* model of them. A fix that edits `src/nonogram/solver/**` has misdiagnosed
  the card.
- G-2: **Do not weaken the test to make it honest.** Deleting the isolation claim and the test's
  distinguishing power would satisfy the docstring trivially and lose the control. AC-1 is the guard
  against that: the test must *red* without the branch checkpoint.
- G-3: `nonogram_poc` is never created, dropped, connected to or truncated; `_refuse_unless_test_database`
  is neither widened nor bypassed.
- G-4: No new runtime dependency (ADR-0006/R1); stdlib only.
- G-5: Take no timing measurements and report no durations — other work may share this machine. Note the
  irony and respect it anyway: this is a card about a **timeout** test, and the thing it must not do is
  measure time. The suite's own timeout tests use an injected clock for exactly this reason; use theirs.

## System contract

- ADR-0039/R1 — a claim needs a control that can fail: caught WITH the mechanism, missed WITHOUT it
  (check: `test_the_control_for_each_spelling_depends_on_the_set`)
- ADR-0039/R2 — a guard's set is derived from an authority the runtime can enumerate, not hand-written;
  where none exists it defaults to deny (check: `test_the_guard_sets_are_derived_and_not_hand_written`)
- ADR-0038/R8 — tests fail or skip **loudly**, never silently; a fix here must not add a skip
  (check: review-lens)

## Architecture context

- **ADR:** ADR-0011 (the cooperative deadline and its two checkpoints) is the mechanism under test;
  ADR-0039/R1–R2 are the rules the defect breaks.
- **Components:** none changed. This card edits one test file.
- **Trace:** `meta/architecture/trace.yml` — unchanged; no requirement's verifying test moves.

## Worktree notes

- **[The mutant that found it, so it can be re-run rather than re-invented]** Neutralise all four of
  `search.py:1180`, `:1259`, `:1418`, `:1728` at once (`check_deadline(deadline)` → `pass  # MUTANT: …`,
  preserving the line count) and run `tests/test_timeout.py` alone. ~~Today: **17 passed, exit 0**.~~
  (**Retracted — see the AC-3 note below.**) After
  this card: that test must red. The single-site version of the same mutant on `propagate.py:983` already
  reds two other tests today, which is how the propagation-side checkpoint is pinned — leave that intact.
- **[AC-3: the figures, re-derived — and one of this card's own retracted (ADR-0039/R4)]** Method: an
  `ast` walk of `src/nonogram/solver/**/*.py` — `ast.Call` nodes whose `func` resolves by `Name.id` or
  `Attribute.attr` to `check_deadline`, and `ast.Raise` nodes whose exception resolves to
  `SolverTimeout`. Never a text grep: `git grep -E` is POSIX ERE and honours neither `\b` nor `\s`, so a
  word-boundary grep here misreads in silence.
  - `check_deadline`: **1 definition** (`propagate.py`, `check_deadline`) and **6 call sites** —
    `propagate.propagate`, `propagate.propagate_overlap`, `search._search`, `search._expand`,
    `search._descend`, `search._probe_fixed_point`. **This card's six was right.** CARD-264's four was
    the wrong figure; this is an independent re-derivation, not an inheritance of the correction.
  - `SolverTimeout`: raised from **exactly one** place in the solver package, inside `check_deadline`.
    Right. That is what licenses reducing "can raise on the deadline" to "calls `check_deadline`", and
    the implementation asserts it rather than assuming it.
  - **Retracted figure:** the note above claimed the combined four-site mutant left
    `tests/test_timeout.py` at *"17 passed, exit 0"*. Re-run on the implementation commit **before any
    edit**, that same mutant gives **1 failed, 16 passed, exit 1**. The red is the *neighbouring*
    counting test `test_the_search_checks_the_deadline_at_every_branch_node`, at
    `assert clock.reads >= result.signals.branch_nodes` (4 >= 6) — the clock reads it still saw were
    `propagate_overlap`'s, through the very leak this card is about. The card's **central** claim
    survives untouched and is what the fix addresses: the named test
    `test_the_branch_checkpoint_alone_stops_a_search_propagation_would_not` itself **passed** under the
    mutant. Read this paragraph, not the struck figure.
  - **AC-2 names the wrong root.** Derived from `_search`, the reachable deadline sites are
    `{propagate, _search, _expand, _descend}` — `propagate_overlap` is **not** among them, because it
    is called from `solve`'s ADR-0029 level-1 prologue, *before* the search is entered. A derivation
    rooted literally at `_search`, as AC-2 words it, reproduces the defect. The implementation roots at
    `solve`, the entry point the test actually calls; that yields all six and is a strict superset of
    AC-2's set, so AC-2 is met and exceeded. The card body's own item 4 already says the right thing —
    "the raise sites reachable from *the code under test*".
- **[Why single-site mutants hid this]** Each of the five non-`propagate.py:983` sites survives alone,
  which looks like five uncovered sites and is not: the branch checkpoint is pinned **collectively** —
  either `search.py:1180` or `:1418` alone satisfies the counting test. Only the *combined* mutant
  separates "the concept is covered" from "this test covers it", and only after that does the
  `propagate_overlap` leak become visible. Run combined mutants when a mechanism is deliberately
  redundant; single-site readings will mislead you in both directions.
- **[Restore `src/` byte-identically]** The mutants touch files this card must not change. `cp -p`
  backups with the manifest built up front, a shell `trap` armed on the restore, and restoration verified
  by `shasum -a 256 -c` **and** `diff -q` **and** `git status --porcelain`. The skeptic that found this
  did exactly that and its evidence is in CARD-264's notes.
- **[Do not run the full suite]** Export `NONOGRAM_FULL_SUITE_LOCK` to a scratch path for every pytest so
  the board's own lock is never read, written or created. The merge gate runs the full suite.
- **[Use the committed instrument]** `tests/kill_matrix.py`, documented in `tests/README.md` from line
  453. Do not write another. Both passes, ANY-RED, and report the **domain** of every figure — the
  denominator is the target file's `ast.Assert` node count, never the collected-test count. In the
  recording pass a mutant can exit pytest 0 while the matrix records FAIL cells; CARD-264 hit that six
  times.
- **[Item 3: the body was widened to the docstring, not the docstring narrowed to the body]** The
  isolation sentence — *"the only thing left that can raise is the branch-node check"* — is kept
  verbatim and made **true**, which is the only option G-2 leaves: narrowing it would have satisfied the
  docstring by deleting the control. `_blind_propagation` now blinds every propagation-side deadline
  site reachable from `solve`, and the prose added around it says what the helper derives and why
  `solve` and not `_search` is the root. One neighbouring docstring became honest with **no edit at
  all**: `test_the_search_checks_the_deadline_at_every_branch_node`'s *"every clock read during this
  solve comes from the top of the search loop"* was false at HEAD for the same reason, and is now true.
- **[Item 4: measured, and shipped rather than proposed]** The standing form the card asks to cost out
  is the derivation itself, and AC-2 already requires it ("derived from the code rather than listed by
  hand"), so there was no cheaper variant to propose. Cost, as a **size** datum (G-5 forbids a clock
  reading): **309 insertions / 19 deletions in one file**, of which **134 lines are code** with
  docstrings excluded — 98 lines of derivation helpers and substitution machinery and 36 lines of the
  standing control, `test_the_blind_set_is_derived_from_the_solvers_own_call_graph`. No new dependency,
  no `src/` change, no new skip. **Declared bound on the derivation:** it resolves callees by name
  across the package (sound only while no two solver modules share a top-level name — asserted), folds
  nested functions into their enclosing top-level function (an over-approximation, the deny-safe
  direction), and sees only *syntactic* calls, so a deadline check reached through a function held in a
  variable would escape it. Where a derived site cannot be blinded — absent from the search module's
  namespace, or carrying no `deadline` parameter — the helper raises rather than proceeding
  (ADR-0039/R2's default-to-deny).
- **[Kill-matrix readings, both passes, with their domain]** Instrument: `tests/kill_matrix.py` (no
  second one written). Selection: the named test alone. Mutant `BRANCH4`: the four branch-side calls
  neutralised together, line-count preserving.
  - **WITHOUT the fix** (HEAD's helper, restored from captured content afterwards): `BRANCH4` **exit 0
    with 1 reached and 0 FAIL** in *both* passes — a true survivor, which is the defect.
  - **WITH the fix:** `BRANCH4` **exit 1 with 6 reached and 0 FAIL** in both passes. `SHIPPED` is
    `0 FAIL of 6 reached, pytest exit 0` either way.
  - **Domain of those figures:** the denominator is the target file's `ast.Assert` node count — 26 at
    HEAD, 41 after — never a collected-test count (1). The `0 FAIL` at exit 1 is the instrument's own
    documented out-of-domain kill: this test fails inside a `pytest.raises` block, which is not an
    `ast.Assert`, so no cell can account for it. `exit 1 / 0 FAIL` and `exit 0 / 0 FAIL` are the two
    readings that must not be conflated, and they are what separates WITH from WITHOUT here.
  - A plain `-rEfs` run of the file agrees: **18 passed** unmutated; under `BRANCH4`, **3 failed,
    15 passed** — the named test, the neighbouring counting test, and the new control (whose
    `assert branch_side` premise correctly reports that the branch checkpoint no longer exists).
  - The propagation-side pin is intact: the single-site mutant on `propagate`'s own checkpoint still
    reds exactly `test_propagation_checks_the_deadline_at_every_fixed_point_sweep` and
    `test_propagation_stops_at_the_sweep_after_the_deadline_passes` (**2 failed, 16 passed**).
  - Every `src/` restore verified byte-identical by `shasum -a 256` **and** `diff -q` **and**
    `git status --porcelain src/` (empty).
