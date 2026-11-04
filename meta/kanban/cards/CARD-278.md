# CARD-278: `_blind_propagation` blinds one propagation path of two, so the test named for the branch checkpoint passes without it

**Status:** done
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
**Review score:** 8.8 (cycle 1 of 3 — CERTIFIED)
**Started:** 2026-11-04T03:41Z
**Closed:** 2026-11-04T05:29Z
**Actual:** A **derived size datum**, not a clock reading. Landed on main: **2 files, 427 insertions / 27 deletions** — `tests/test_timeout.py` **329/23** and this card **98/4** — with **1 test added, 0 lost, 0 retargeted** (`ast` walk of the file's test functions across the merge, agreeing with pytest's own whole-suite collection) and **0 lines of `src/`** (G-1). The implementation commit alone is **312/19 in one test file**, which is the figure the gate's M-1 corrected from the 309 the item-4 note claimed. **The wall-clock figure is excluded**, under the owner's ruling that wall-clock actuals are unusable for estimate calibration because the clock measures the **queue** rather than the work — this card's round sat behind two concurrent cards and its gate waited 935s on another worktree's lock, neither of which is work done on it. The size datum above substitutes for it. **Estimated 1c (0.25d) and certified on cycle 1 of a 3-cycle budget, so the cycle estimate was exact** — a calibration datum the last retrospective could not export at 0-of-3 cycle coverage. The one duration recorded anywhere here is the suite's own wall-clock as pytest printed it (1459.80s), quoted as a gate fact; **nothing in this card's code was timed**, per G-5.
**Merge commit:** `5f702d65` — merged `--no-ff` onto `9913c3b5`, one kanban-only commit (`board.md` + CARD-346/347/348) past the `217f15b6` the gate opened on; that commit touches no `tests/` and no `src/`, so the gated tree's baseline is unaffected. Gated tree `142f8867`; merge-base `d1a18baa`. **Full suite on the gated tree, `DATABASE_URL` armed, `-o addopts=` and `-rEfs`, under the board's own lock held as this worktree (no pid — identity is the worktree): 10234 passed / 0 failed / 0 errors / 1 skipped / 1 xfailed, exit 0, 1459.80s.** **Not vacuous:** passed + skipped + xfailed = 10234 + 1 + 1 = **10236 = the collected count exactly**. **Skips attributed from `-rEfs`, not from memory — and the count is 1, not the 27 of earlier gates:** the single skip is the `setrlimit(RLIMIT_AS)` platform gate in `tests/test_book_pdf_memory.py`. The bare-`DATABASE_URL` check fired **zero** times and the per-worktree `*_test` resolution gate fired **zero** times, which is the positive evidence that the arming took: the 26 tests that skip unarmed were **executed**, not skipped green. (27 is the *unarmed* baseline; arming it and still seeing 26 bare-`DATABASE_URL` skips would have been the finding, and that is not what happened.) **Node-id delta, derived by whole-suite collection with `-o addopts=` on both sides: 10235 → 10236, 0 lost and 1 gained**, the gained id being exactly `tests/test_timeout.py::test_the_blind_set_is_derived_from_the_solvers_own_call_graph` — cross-checked by an independent `ast` walk naming the same single addition, so two instruments agree on the set and not merely on the total. **G-1 verified on the merged tree:** `git diff --name-only main...HEAD -- src/` empty and `git status --porcelain src/` clean, so every mutant the round and the reviewer planted into `src/` was restored byte-identically. **The gate's first full run was red at 5 failed, and it was not this card.** All five were one parametrized class in `tests/test_admin_binding.py` — a file **byte-identical to main's**, in a card whose whole footprint is `tests/test_timeout.py` — failing on `FATAL: database "nonogram_pythonproject4_card_278_a6c1379e5711_test" does not exist`. That class carries **no `db_required` marker**, so `conftest.py`'s create-if-missing path, which is gated on that marker, never covered it: it read the armed `DATABASE_URL`, enabled DB persistence and connected **before** any marked test created the database. Re-run after a marked test had created it: **14 passed**. **This is a sibling of the stale-schema hazard and demonstrably not that hazard** — a migration had indeed landed recently (CARD-332, 2026-11-01, `migrations/versions`), which is exactly when that hazard is live, but the signature is a missing **database** rather than CARD-338's missing **column**, and `books.player_domain` was already present in this worktree's schema when checked. Run 2 on the same tree, after the database existed, is the green above. **Worth carding:** arming `DATABASE_URL` in a worktree whose derived `*_test` database has never been created reds any test that reads `DATABASE_URL` without carrying `db_required`, and it self-heals — the signature that trains a re-run instead of a look. **Card conflict resolved by taking main's metadata header and the branch's body, verified by diff rather than eyeballed:** both sides split at the first section heading, the resolved header byte-identical to main's and the resolved body byte-identical to the branch's, with the adopted header delta being exactly `Status: in_progress`, the quoted `Branch:` value, the retired-branch-name HTML comment and `Started:`. The rebase took **no conflict beyond that one file**.
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

<!-- MARKERS WRITTEN POST-HOC BY THE ORCHESTRATOR 2026-11-04, and the provenance matters.
     The retrospective derives `cycles_used` by counting EXACTLY the `[Review N/max] Score:`
     line, which cmd-review-cycle.md's SYNC POINT writes once per completed review cycle. This
     wave's reviews were dispatched DIRECTLY as agents rather than through that command, so no
     marker was ever written -- the same data-quality defect wave 73's retrospective reported,
     now in its second consecutive wave, and the reason that retro could export NO calibration
     signal at 0-of-3 cycle coverage.
     These lines are not fabricated: each cycle genuinely ran and its verdict is recorded twice
     over -- in this card's `Review score` field ("cycle N of 3") and in the untracked review
     YAML under meta/review/. The markers restate what those artefacts already say, in the one
     spelling the retro's extractor matches. A marker that drops the `/M` denominator does NOT
     match, which is why they are written in full. -->

[Review 1/3] Score: 8.8 — CERTIFIED on cycle 1 of a 3-cycle budget. 0 gating findings; two Importants (I-1 the co-location split, I-2 the card-file conflict) and three Minors, all folded in at the merge gate. Review artefact: meta/review/CARD-278-cycle1.yml.


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
- **[Do not run the full suite]** Leave `NONOGRAM_FULL_SUITE_LOCK` **unset** for file-scoped runs;
  redirect it only to probe the lock mechanism itself. An earlier version of this note said to redirect
  it to a scratch path for *every* pytest — wrong advice, though it harmed nothing on this card:
  `tests/conftest.py`'s `pytest_configure` calls `tests/full_suite_lock.py`'s `pytest_configure`
  unconditionally, so the guard fires for **any** selection and not only a full suite, and a redirect
  therefore blinds a file-scoped run to a gate that *is* holding the lock. `tests/README.md` already
  says the switch "is not a thing to reach for by hand". The merge gate runs the full suite, under the
  real lock.
- **[Use the committed instrument]** `tests/kill_matrix.py`, documented in `tests/README.md` from line
  453. Do not write another. Both passes, ANY-RED, and report the **domain** of every figure — the
  denominator is the target file's `ast.Assert` node count, never the collected-test count. In the
  recording pass a mutant can exit pytest 0 while the matrix records FAIL cells; CARD-264 hit that six
  times.
- **[Item 3: the body was widened to the docstring, not the docstring narrowed to the body]** The
  isolation sentence — *"the only thing left that can raise is …"* — is kept and made **true**, which is
  the only option G-2 leaves: narrowing it would have satisfied the docstring by deleting the control.
  The round kept the clause *verbatim*, ending it at "the branch-node check"; the merge gate's M-2
  replaced that singular attribution with the branch-side checks named **collectively**, because the
  raise is attributable to all four and one of them is level-3 probing rather than a branch node — the
  phrasing AC-1 had used all along. The test's body is unchanged by that edit. `_blind_propagation` now blinds every propagation-side deadline
  site reachable from `solve`, and the prose added around it says what the helper derives and why
  `solve` and not `_search` is the root. One neighbouring docstring became honest with **no edit at
  all**: `test_the_search_checks_the_deadline_at_every_branch_node`'s *"every clock read during this
  solve comes from the top of the search loop"* was false at HEAD for the same reason, and is now true.
- **[Item 4: measured, and shipped rather than proposed]** The standing form the card asks to cost out
  is the derivation itself, and AC-2 already requires it ("derived from the code rather than listed by
  hand"), so there was no cheaper variant to propose. Cost, as a **size** datum (G-5 forbids a clock
  reading): **312 insertions / 19 deletions in one file**, of which **134 lines are code** with
  docstrings excluded — 98 lines of derivation helpers and substitution machinery and 36 lines of the
  standing control, `test_the_blind_set_is_derived_from_the_solvers_own_call_graph`. No new dependency,
  no `src/` change, no new skip. **Declared bounds on the derivation — five, of which the last two were
  undeclared when the round closed and were added at the merge gate (review I-1):**
  - it resolves callees by name across the package (sound only while no two solver modules share a
    top-level name — asserted);
  - it folds nested functions into their enclosing top-level function (an over-approximation, the
    deny-safe direction);
  - it sees only *syntactic* calls, so a deadline check reached through a function held in a variable
    would escape it;
  - **the co-location split itself.** `_propagation_side_deadline_sites` partitions the derived set by
    module co-location: a site defined outside the search module is blinded, one defined alongside the
    search is *assumed to be* the checkpoint under test. So a new **non-branch** deadline check added
    *inside* the search module escapes the blinding. Demonstrated, not argued: a planted
    `check_deadline` in `solve`'s prologue leaves the branch-checkpoint test **green** under the
    four-site branch mutant;
  - **the caller premise.** The helper asserts that a derived site **is** an attribute of the search
    module; it never asserts that **all of that site's reachable callers** are defined there. True
    today — every caller of `propagate` / `propagate_overlap` in the solve path (`solve`, `_probe`,
    `_lookahead`) lives in `search.py`, so substituting through that one namespace blinds every path —
    but **true, not guarded**.
  **CARD-345 owns closing both of the last two.** Where a derived site cannot be blinded — absent from
  the search module's namespace, or carrying no `deadline` parameter — the helper raises rather than
  proceeding (ADR-0039/R2's default-to-deny).
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
