# CARD-304: ADR-0039/R4 has no executing check — a figure's instrument is held by a lens, not by the tree

**Status:** in progress
**Priority:** P2
**Category:** enabler
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/304-an-executing-check-for-figures
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-304
**Source:** wave 62's retrospective (2026-10-28), which promoted the wave's dominant finding family into **ADR-0039/R4**. The rule ships with `check: {kind: review-lens}` and this card owes the flip to an executing check — an ADR check ref that names a planned test reads as mechanically checked while checking nothing.
**Idea:** —
**Wave:** 67
**Created wave:** 62
**Deferred waves:** 3 <!-- CORRECTED 2026-10-30 by the waves 63-65 retrospective. It read 0. This card was created in wave 62 BY wave 62's own retrospective, which promoted the figures family into ADR-0039/R4 and left R4's flip to an executing check owed here. It then sat unscheduled through waves 63, 64 and 65 while that same family produced EIGHT more gating findings across five cards. The counter never moved because cmd-retrospective Step 4c increments only tech-debt cards IN THE CURRENT WAVE SCOPE, and this card is Category: enabler and was in no wave's scope - so it aged invisibly by construction. Stamped into wave 67 on owner decision. -->
**Depends on:** —
**Touches:** tests/test_suite_profile.py, meta/kanban/config.yml, meta/architecture/decisions/adr/0039-guard-coverage-claims-need-controls.md <!-- CORRECTED 2026-10-30: `meta/kanban/config.yml` was MISSING from the declaration while AC-1 and AC-2 are ABOUT it -- AC-1 executes every shell command config.yml prescribes for a host cell, AC-2 turns its five-case truth table into machine-readable data. The implementation round is editing it, correctly. Caught by inspecting the worktree, not by the card. Third footprint-declaration defect of the day: CARD-220 over-broad (`tests/**`), CARD-308 over-broad (`tests/**` + `adr/**`), this one under-declared. The pattern belongs in the retrospective's touches-drift calibration rather than being fixed one card at a time. -->
**Review score:** 8.0 (cycle 1/3) — fix round 1 at `2583783b`; **review cycle 2 running**, narrowly scoped to the instruments the fix round added, its rewritten refutation criterion, and its edit to CARD-308's frozen census
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this exists

**ADR-0039/R4 is the only one of that ADR's four rules with no executing check.**
R1, R2 and R3 each name a test that fails if their discipline regresses; R4 names
a `review-lens`, because nothing in the tree can today decide whether a committed
number names a live instrument. That is stated honestly in R4's own comment rather
than papered over with a hopeful ref — and **this card is what makes that honesty
temporary.**

What R4 says: *a figure is a claim, and the instrument that produced it is part of
it… a reading that cannot distinguish "the quantity is zero" from "the instrument
is blind" is not a measurement.*

**The family it was promoted from cost 6 of wave 62's 7 gating findings** across
two cards and six review cycles. Full provenance, with each finding's measured
truth, is in ADR-0039's `## Promotion — 2026-10-28` section — **read it before
designing anything here**; it is the specification.

## The hard part, named up front

**A general "every figure names a live instrument" check is not writable** and this
card must not pretend otherwise. A number in prose has no machine-readable link to
the command that produced it. So the deliverable is **not** a universal checker;
it is the **narrowest executing check that would have caught wave 62's instances**,
plus an honest statement of what it still cannot see.

The three shapes the wave actually produced, in descending tractability:

1. **A named instrument that is not executable on this host.** `pgrep -fc` — BSD
   has no `-c`; exit 2 and an empty `$(...)` cell. **This one is checkable**: a
   convention file (`meta/kanban/config.yml`) that *prescribes* commands can have
   every prescribed command extracted and executed for its exit status. That is a
   real check with a real failure mode.
2. **A named instrument that runs but is blind.** `pgrep -f 'bin/python -m pytest'`
   reads 0 whether or not pytest is running. **Checkable only with a control pair**:
   the convention must carry a positive and a negative case and the check must run
   both. `config.yml` already carries that truth table (five cases) as *prose* —
   turning it into data the check executes is the obvious first increment.
3. **A ratio whose halves come from different instruments, runs or baselines.**
   **Not checkable from the text.** Declare it as R4's lens-only residue.

## Acceptance criteria

- **AC-1** (prescribed commands execute): *Given* every shell command
  `meta/kanban/config.yml` prescribes for a host cell, *then* a test extracts it
  and asserts it **exits 0** — so a flag that does not exist on this platform reds
  the suite instead of yielding an empty cell. (test: a new cell in
  `tests/test_suite_profile.py`; **gate**: `pgrep -fc` planted back and shown to red.)
- **AC-2** (the control pair is data, not prose): *Given* `config.yml`'s five-case
  truth table, *then* it is machine-readable and a test runs the prescribed
  instrument against **at least** the positive case (a real pytest alive) and the
  negative case (a `zsh -c` whose argv merely mentions pytest), asserting it rises
  on the first and not on the second. (test: named; **gate**: the previous blind
  form planted and shown to red on the positive case.)
- **AC-3** (the residue is declared, not implied): *Given* the shapes AC-1 and AC-2
  cannot reach — a ratio mixing domains, a point estimate for a spread quantity, a
  refuted figure surviving in a second place — *then* R4's comment names them as
  lens-only, and this card's notes record why each is unreachable. **A check that
  claims the whole rule is exactly the defect the rule describes.**
- **AC-4** (R4's ref flips, honestly): *Given* AC-1 and AC-2 land, *then*
  ADR-0039/R4's `check:` becomes `{kind: test, ref: <the cell>}` **with a REACH
  comment stating what it executes and what it does not** — the shape R1 already
  uses (*"this ref executes and fails if THAT guard's discipline regresses; it does
  not reach a guard written tomorrow"*). If only AC-1 lands, the ref flips for that
  half and the comment says so.
- **AC-5** (no test retired): collected node-id set loses nothing; additions named.
  <!-- CONTRADICTED BY HEAD 2026-10-30, cycle 2's F-107, and it is the ONE AC that HEAD
  literally falsifies. Fix round 1 made a deliberate rename that its own brief prescribed
  (F-009) and its own discipline line forbade: two `parametrize` ids retired, two added.
  So the node-id set DOES lose something, and the raw symmetric difference is 2 REMOVED /
  8 ADDED, not the "6 additions, 0 deletions" the record states -- that figure is
  net-of-rename. The commit message discloses the rename; the AC and the summary did not.
  AC-5 is therefore read as: no test retired WITHOUT an accounted successor, and both the
  raw and the net delta must be stated. Recorded here rather than silently re-worded,
  because the card whose subject is figures that read true while being false must not
  carry one in its own acceptance criteria. -->
  **Param ids count.**

## Guardrails

- **G-1: do not weaken R4 to fit the check.** If the executing check can only cover
  the first shape, **narrow the CHECK's stated reach, never the rule's statement.**
  A rule trimmed to what is conveniently verifiable is how this family survived
  three waves inside a brief that carried no check.
- **G-2: the check must be able to fail, and you must show it failing.** Plant
  `pgrep -fc` back for AC-1 and the blind `bin/python -m pytest` form for AC-2 and
  record the red. This is ADR-0039/R1 applied to this card's own work — a control
  that cannot fail is narrative.
- **G-3: probes stay OUT of `tests/`** where they would join a frozen census —
  `meta/profiling/rank_durations.py`'s render set is grepped over `tests/**/*.py`
  and asserted as an equality, and the guard enumerating `tests` **and**
  `meta/profiling` resolves the tree through `git ls-files`.
- **G-4: do not name the full-suite guard's two env switch variables in a tracked
  file under `meta/profiling/`.** A separate guard scans the whole tree for them and
  does not exempt that directory. CARD-292 paid for this twice.
- **G-5: AC-2 launches a real pytest.** It must not take the board's
  `meta/kanban/.full-suite.lock`, and it must be cheap — a `--collect-only` is
  enough to make the cell rise.
- **G-6: no new dependency** (ADR-0006/R1: stdlib + Pillow + NumPy).

## Worktree notes

- **The instrument this card is about is in use.** `config.yml` currently prescribes
  `pgrep -f 'MacOS/Python.*pytest' | wc -l`, verified across five cases on
  2026-10-28, with its bound declared: it keys on the macOS framework re-exec path,
  so a venv built from a non-framework python would read 0 and be blind again.
  **AC-2's check would catch exactly that** on a machine where it is true — which is
  the strongest argument for this card and the reason it is an enabler rather than
  tech-debt.
- **Prior art for the shape**: `tests/test_suite_profile.py` already holds a
  derived-and-asserted census (`RENDER_HEAVY_SNAPSHOT`) and the
  `MEASURED_SILENCES_ELSEWHERE` guard that resolves the tree through `git ls-files`.
  This check belongs beside them, not in a new file.

---

## Implementation — `ca7c8c56` → `e7af05d1`

**`config.yml` gains `review.host_cells:`** — a **JSON document inside a YAML block
scalar**, and the reason is this card's own subject: **PyYAML is not in ADR-0006/R1's
baseline** (nothing in `pyproject.toml` declares it; it is in the venv incidentally), so
importing it would gate the check on a package a bare checkout lacks — and a hand-rolled
YAML reader would be *"one more unproven instrument inside the file about unproven
instruments."* It carries 3 host cells, the rival-pytest truth table's **7** cases with
what each claims and how to create it, and the **6 rejected instruments** with verdicts.
The prose no longer restates any command; it points at the data.

**`tests/test_suite_profile.py`** gains `TestHostCells_ThePrescribedInstrumentsExecuteAndRespond`
— 16 methods, **29 node ids**, beside the existing census guards as the card asked.

### Two harnesses, because R4 is about the difference between them

AC-1 asks **executability** (`set -o pipefail`, judge the exit status); AC-2 asks
**responsiveness** (no pipefail, judge the reading). **One harness would red a blind form
for the wrong reason** — *"it exited 1"* instead of *"it did not rise while a real pytest
was alive."* And `pipefail` is what makes AC-1 mean anything: `pgrep -fc` was prescribed
*inside* `| wc -l`, and without it the pipeline exits 0 while the cell comes back empty.
The cost is declared as a bound in the data: a grep/pgrep prescription exits 1 on a
legitimate empty match, so it cannot be stored as a host cell at all without conflating
"blind" with "quiet" — which is *why* the awk form, exiting 0 on no match, is the storable
one.

Readings are **deltas** against a baseline taken before and re-taken after each probe; a
baseline that moved is a **refusal to judge** (retried up to 4×), and the failure prints
the process lines the instrument matched, **derived from the prescription by dropping its
counting stage** so the diagnostic cannot describe a different query from the number.

### The planted reds

**AC-1**, both restored with the blob hash verified identical, needle unique, no `git stash`:
`pgrep -fc 'python.* -m pytest'` planted → exit 2, empty stdout, two cells red; and the
brief's second instance `pgrep -f … | wc -l` → **exit 1**, cause measured independently —
`-f` is case-sensitive and a live run's `argv[0]` is `…/MacOS/Python`, with **no lowercase
`python` anywhere in it.**

**AC-2**, and its second plant is the strongest single result on this card.
The blind form planted *inside* the executable harness → the positive case red:
*"a real pytest was alive and the prescribed cell read 0 against a baseline of 0."*
Then the **vacuity control**: reverting the near-miss wrapper to `': <text>; sleep N'`
made the visibility cells red (`argv ''`) **while the three negatives passed vacuously
beside them** — because **`zsh` execs its last command, so the near-miss does not exist in
`ps` at all, and "did not rise" proves nothing.** Every negative is now judged *only after*
visibility is asserted. That is a vacuity this card found in its own controls.

### AC-3's residue, AC-4's flip, AC-5's census

Nine residue items, each with why it is **unreachable rather than deferred** — a figure in
prose generally (no machine-readable link from a number to the command that made it); a
ratio whose halves came from different runs; a point estimate for a spread quantity
(syntactically identical to a correct one); a figure stale at another revision; a refuted
figure surviving elsewhere; a **mis-stated instrument warning** (no artefact in the tree at
all); one-off shell commands that are not prescriptions; **any host but this one** (BSD
spellings asserted *unconditionally*, no `skipif`, so a foreign host reds — AC-1's intent
and equally its bound).

**Residue item 9 is RECLASSIFIED by fix round 1 (F-006): it was never residue.** The sandbox
deselect is a **declared accommodation**, not an unreachable shape — residue is what R4's lens
cannot check; a deselect is a choice about what to run. Fix round 1 narrowed it from 18 of 29
node ids to the four `rival_matrix`-dependent methods, **11 of the class's 35**, leaving **24
running in both sandbox copies where 0 did before**, comparison green at 127 passed. The code
now states it as an accommodation with that measured scope, and **the `config.yml` symlink now
earns its place and more**: it is what those 24 node ids *read*, not merely what lets the copy
collect. The round struck its own earlier sentence about judging the convention from inside the
sandbox being vacuous — for a data assertion *about* `config.yml`, the real file is the right
file, and a copy would only let two sandbox runs agree about a file neither is judging.

R4's `check:` flipped to three bare names in R1's shape, all verified to resolve, with
`--verify-refs` reporting `dead_check_ref: []` post-commit. **R4's statement is untouched**
(G-1). Census **410 → 439, 0 lost**, all 29 additions named — **true of the implementation round,
and superseded by fix round 1's rename: see AC-5's comment above.** **Zero skips**, confirmed with
`-rs` printing nothing. Validator 0 errors / 100 warnings.

## It answered the orchestrator's question by refuting the orchestrator's answer

The brief asked whether the `ps`/`pgrep` prescription can be made correct at all, or
belongs in AC-3's residue. **Answer: it already is correct, for the board's own runs.**
Measured with the near-miss proved present each time, the prescribed **awk** form rises by
exactly 1 for a real `python -m pytest` and is flat on **all four** near-misses — including
the framework-path wrapper that retired its predecessor and the search tool that *the act
of measuring spawns*. One measured blindness (a run via `.venv/bin/pytest`) is now a
declared bound asserted in **both** directions, tolerable only because `review.test_command`
starts pytest as `-m pytest`, which a new cell asserts.

**And it declined to widen the instrument to `/pytest/`** — which does see that case —
because *"widening without the control for the direction you widened into is how this cell
got its last two defects."*

**So the orchestrator's conclusion was wrong.** After measuring five probe variants at one
instant and getting 0, 3, 2, 0, 2 against a ground truth of one, it concluded *"no
one-liner gets this right, so the gate scripts record the PID list instead."* **It had
tested five forms it invented and never the one `config.yml` already prescribed.** The PID
list is the right **diagnostic** — and is now what these failure messages print — but *"a
gate row needs a figure, and a figure needs an instrument with controls,"* which is what
this card gives it. A generalisation drawn from five self-authored samples while the
documented instrument sat unexamined is the same sampling error as every other figure
corrected on this board today.

## Six more corrections it measured, two of them the orchestrator's briefs

- **`pgrep -fc` does not read 0** — the brief's table says it does. It produces **no
  reading at all**: exit 2, empty stdout. Sharper, and the distinction AC-1 turns on.
- **The lock must be checked in the MAIN checkout.** `ls meta/kanban/.full-suite.lock`
  *inside a card worktree never sees it* — the round did that first, got "No such file",
  and then had a run refused naming the main checkout's path. **The orchestrator wrote
  that worktree-relative check into roughly six briefs today**, telling agents to run a
  blind instrument for exactly R4's reason.
- **`config.yml`'s truth table had a wrong cell and the summary sentence inherited it** —
  row 6 recorded (b) = 1; measured, it is **0**, by the same mechanism the table records
  three rows above. *"ONLY THE LAST ROW PASSES ALL FIVE"* → it passes four. Corrected in
  place with the correction stated.
- **A declared bound outlived its instrument** — the "DECLARED BOUND" paragraph is true of
  the *retired* pgrep form and **false** of the awk form in the file.
- **The card's own Worktree notes were stale**, naming a prescription retired one revision
  earlier — and the card's strongest argument rested on the retired form.
- **The truth table is 7 cases, not the 5 the ACs and the brief both say.**
- **The module docstring's cost figure is ~2× stale** (16.5–16.7 s, 2026-10-16, against
  30.4–34.0 s now *without* the new class). Re-measurement added **with its domain** rather
  than replacing theirs, because two cards were sized against the old one.

---

## Review cycle 1 — **8.0, PASSES `min_score: 8`** — but one finding falsifies a committed ADR sentence

Eleven findings. The reviewer answered all seven brief questions **with witnesses it built
itself**, two of which the implementation round did not have.

### The split is necessary, proved orthogonal in both directions

- `ps -Ao comm= | awk '/pytest$/' | wc -l` — **executable, exit 0, well-shaped integer,
  and totally blind** (`comm` is `Python` here). Planted: 28 passed, **only AC-2's positive
  control red**. So AC-2 is not redundant.
- The prescribed awk with `| grep -c .` — **reads correctly in every truth-table case** yet
  exits 1 on a quiet host. AC-1 reds it, AC-2 passes it entirely. So AC-1 is not redundant.
- **A stronger argument than the round's own**: planting `pgrep -fc` reds `…_exits_zero`
  but leaves `…_prints_its_declared_shape` **GREEN**, because `wc` prints `0`. **Pipefail
  is the only thing between that cell and an empty figure.**

### F-001 (high) — the vacuity fix is parametrized over all four negatives but substantively covers three

`test_each_near_miss_probe_is_visible_to_ps` **is** parametrized over d, d2, d3, e, b. But
for **(e)** the assertion reads `_argv_of(proc.pid)` — the `zsh` that owns the pipeline —
and **the wrapper's own argv carries the pattern**, so it is satisfied whether or not a
search tool exists. Mutant: give the grep an unknown flag so it dies on arrival → **29/29
pass with no search tool on the host.** A second mutant with `grep -q` behaves the same.

**Two tracked sentences are therefore false**: `config.yml`'s *"that immunity is now
asserted rather than reasoned"*, and **ADR-0039/R4's REACH comment** — *"Each near-miss is
asserted VISIBLE in `ps`."* The underlying claim is **true** (the reviewer's own harness
proved the grep child present and the cell flat); the tree simply does not assert it.
**Three-line fix** — the grep row is already enumerable via `ps -eo pid=,ppid=,command=`.

**This is the card's own subject landing on the card**: a claim that reads true while being
false, committed into the very ADR comment the card exists to make executable.

### F-004 — "every probe IS killed" is false, and it pollutes the host for other cards

After a clean 29-passed run: **four orphan `sleep 30` and one orphan `grep … -m pytest`**,
all reparented to pid 1. `proc.kill()` signals the wrapper only. **On a board at
concurrency 5 this injects case (e)'s own false-positive shape into the host for 30 s per
run** — so this card's probes can corrupt a *sibling card's* rival-pytest reading. Fix:
`start_new_session=True` + `os.killpg`.

### F-005 — the hang guard can turn a broken control into no verdict at all

The whole matrix builds inside the **first** node that requests it, and `hang_guard.py`
arms 120 s in `pytest_runtest_protocol` — which wraps setup — with `exit=True`. Three
invisible negatives cost **93.30 s** on that one node; with five visibility cases the
ceiling is **150 s**, past the guard. A broken negative control would then present as **no
summary line** rather than three named reds — which `config.yml` itself calls *"a
MEASUREMENT defect, never a tree verdict."* Realized need is ~15× smaller.

### The rest

- **F-002** the visibility assertion has no *standing* control; its sibling new instrument
  in the same card ships exactly that control, so the asymmetry is internal.
- **F-006** the sandbox deselect is **over-broad by 18 of 29 node ids** — narrowed to the
  four matrix-dependent methods, the comparison stayed green. The symlink buys collection
  and nothing else.
- **F-007** `config.yml` names five test functions and **nothing asserts any resolves** —
  the selector keys on the *presence* of a field, never its value, so a rename leaves a
  silently dead reference. **The first of the three shapes this card exists to catch,
  inside the file it just made machine-readable.**
- **F-008** AC-1's declared cost is overstated: `<form> || [ $? -eq 1 ]` exits 0 on a
  legitimate empty match **and still reds `pgrep -fc`**, whose usage failure is exit **2**.
  The strong argument was already in the file — grep's *readings* are wrong (the normalized
  form read **2** with no pytest running) — not that its exit status is unstorable.
- **F-003 / F-011** the new cost band is already exceeded (35.22 s, 37.85 s against a
  declared 30.4–34.0), and a wall-clock class figure sits beside session-time module
  totals. Residue item 3's own shape, on this card.
- **F-009 / F-010** a test name carries no scope while its docstring does, and three
  byte-identical copies of the prescription exist in the tree; one residue heading
  contradicts its body.

### Two answers that corrected the brief's premises

**The unconditional BSD assertions are a FEATURE**, and my question presupposed otherwise:
**there is no CI in this repo at all** — neither `.github/workflows/` nor `ci/` exists — so
"cannot pass on Linux CI" is hypothetical, a `skipif` would make "verified here"
unfalsifiable (R4's exact defect), and the module already forbids one globally. Worth
naming in whatever brief first proposes a Linux runner.

**The awk form behaves exactly as reported**, reproduced with a second implementation that
never imports the module under review: **+1** on a real `-m pytest`, **flat on (b), (d),
(d2), (d3), (e)**, each probe's presence proved by a process-tree walk. *"The
orchestrator's 'no one-liner gets this right' is correctly refuted."*

### And it declined to transcribe the prescription into its own report

Because two prior review YAMLs do, which is F-009's subject. It also flagged inside its own
YAML that the ~14 test names it spells — every one verified against a real `def` — **will
make those names read as alive after a future rename**, because `meta/review/**` sits inside
the resolver's text search. The hazard declared by the report that creates it.

---

## Fix round 1 — `74debef2` (main merge) → `2583783b`

All eleven cycle-1 findings addressed, correctly attributed to the orchestrator, or already
resolved on `main`. **F-010 needed nothing** — the card rewrite had already dropped the
contradicting heading. **F-006's card-side half is done above.** Nothing pushed, nothing
rebased, no `git stash` (the worktree's stash list stayed at 4, all pre-existing from other
branches). The lock was absent at the absolute main-checkout path at start and at end.

**The merge.** ADR-0039 **auto-merged cleanly** — CARD-308's new section lands near line 209,
R4's rule block near 512 — so both sides are present unaltered and the conflict I predicted in
R4's region did not occur. The one conflict was in the card file itself, resolved in favour of
`main`: the card record is the orchestrator's.

### F-001: the sentence is now true, and the code is what made it true

`_wait_until_visible` gained a third branch. For `search-tool` it requires **a child of the
spawned process whose argv carries the pattern and whose `$1` is not a shell** — *the same field
the instrument's immunity itself turns on*. New `_children_of` (walks
`ps -eo pid=,ppid=,command=`) and `_is_a_shell`.

- **M-A, the reviewer's own mutant** (the grep given a flag it does not have, so it dies on
  arrival): survived before at 29/29. **Now KILLED** — `…is_visible_to_ps[e]` reds with *"the
  probe never became observable"*, plus the orphan test. 2 failed / 33 passed.
- **M-C** (the new branch deleted, so (e) falls back to the wrapper's own pid): **KILLED by the
  standing control in both directions.** The fix cannot be reverted silently.
- **G-1 verified**: one hunk in the ADR, `@@ -541,10 +541,29 @@`, and **no `-`/`+` line touches
  `statement:`, `scope:` or `severity:`.** R4's normative text is unedited.
- Neither sentence was weakened to match the code. Both now say *the search tool*, naming the
  child and the `$1`-is-not-a-shell test, with why an assertion on the wrapper held regardless.

**It also refuted the cycle-1 reviewer:** the second mutant, `grep -q`, is **not discriminating
at all** — under `-q` the grep still blocks on the pipe, so a real child exists (observed) and
it survives the fix *legitimately*. Only the die-on-arrival form separates the two codes.
Listing `grep -q` as a second F-001 witness **reads as independent corroboration and is not**.

### F-002, F-004, F-005, F-007

- **F-002** — `VISIBILITY_CONTROL_PROBES`: four planted probes at **one shared budget**, two
  that must be seen and two that must not, one pair per branch. Same budget both directions, so
  an invisible row cannot pass merely because the budget is short. **M-D** (`_wait_until_visible`
  made unable to return `""`): **KILLED**.
- **F-004 — orphans: five before, zero after.** `start_new_session=True` on all three spawn
  shapes, `os.killpg` in `rival_matrix`'s `finally`. Before: four `sleep 30` + one orphan grep,
  all ppid 1. After: **0**, also after a clean 445-passed module run. **Shown, then also
  asserted** by `test_a_probe_leaves_no_orphan_behind`, which enumerates the children while the
  probe lives (requiring ≥ 2 so it cannot measure nothing). **M-E** (`os.killpg` reverted to
  `proc.kill()`): **KILLED**.
- **F-005** — `PROBE_VISIBLE_TIMEOUT` 30.0 → **5.0**, with the reason in the code: five cases at
  30 s put the first node's ceiling at 150 s past `hang_guard`'s 120 s, whose action produces
  **no summary line** — *"a MEASUREMENT defect, never a tree verdict."*
- **F-007 caught a dead reference on its first run.** The new
  `test_the_named_tests_in_config_yml_all_resolve` resolves by **definition**, not mention, with
  a negative control that must *not* resolve and a minimum-count assertion. Its first run went
  red on `config.yml:86`, the reference F-009's own rename had just orphaned — **the positive
  control arriving unasked**. **M-F** (rename a named test): KILLED, message names the dead ref.
  **M-G** (make `test_command` a real `def`): KILLED, the allowlist cannot grow to hide a
  reference. A measurement forced a change en route: the unanchored `test_[a-z0-9_]{3,}` read
  `test_configure` out of `pytest_configure` and `test_suite_profile` out of a module **path**.

### Finding 12 — not in the review: a healthy tree going red because of a sibling card

`test_a_rejected_instrument_is_still_refuted_on_this_host[pgrep -f]` **failed on a clean tree.**
`pgrep -f` without `-c` prints a **PID list**, so the instant any argv spells
`python.* -m pytest` it exits 0 printing a pid, `isdigit()` is true, and the old criterion read
the rejection as **no longer refuted**. What spelled it: this module's own (d)/(d2) near-miss
wording **and CARD-306's shell wrapper** (pid 1806). Reproduced deterministically by planting
`zsh -c ': python -m pytest …'`. **On a board at concurrency 5 this is a gate going red for a
reason that is not about the tree** — this card's own defect family, one layer out, and the
second time today that a probe's shape has leaked into a sibling's reading (F-004 was the first).

Criterion replaced with what the rejections actually claim, in two parts: (1) the instrument does
not produce the prescribed cell's reading — *keeping* the stale-rejection property the old one
reached for; (2) nothing it matched is a run the prescribed cell would count
(`_is_a_real_pytest_run`, the awk's two halves **reimplemented natively**, per the project's
`mask_runs` precedent). **Declared bound, in the docstring**: half (2) is strong while a real
`-m pytest` is alive and weak while none is; half (1) carries the row either way. **M-H** (a
"rejected" instrument swapped for one that *does* produce the prescribed reading): **KILLED**.
Self-inflicted and caught before shipping: the first `VISIBILITY_CONTROL_TEXT` was case (d)'s
own wording, planting that very shape; it is now a string no instrument's pattern matches.

### It edited another card's frozen baseline — and says so

The merge brought CARD-308's `tests/test_check_ref_resolution.py`, whose census went red:
**`CENSUS 580 → 583`, `DEFINED 389 → 392`**. Derived as a **symmetric difference against `main`
(`0ea64cf3`)**: exactly **three refs in, nothing out** — R4's three, the only direction a flip
from `review-lens` to `test` can move it — each resolved to a real `def` line **read off the
line, not text-searched**. Both baselines updated with that record and **deliberately without
naming the three refs in that file**, since its own G-2 would otherwise make it one of their
resolvers; CARD-308's file:line precedent followed. **Cycle 2 is confirming this** — it is
someone else's instrument.

### Text corrections, and the one rename

F-003/F-011: the module docstring's cost band is now a **list of domains**, each with host, date,
node-id count and run count, and every module total named as **pytest-reported session time** —
`30.4–34.0 s` (4 runs, 410/439 ids), `35.2`/`37.9 s` (2 runs, cycle 1, above that ceiling, which
is why the shape changed), **`37.6–39.0 s` over 6 runs (this round, 445 ids, a sibling card's
gate live for part of it)**. The class is **5.3–5.8 s session / 6.2–6.7 s wall**, both readings
named and the wall-vs-session confusion stated as the reason. Conclusion unchanged: the class
sits inside the module's spread, so no delta for it is claimable.

F-008: the brief's correction adopted and **re-measured rather than carried** — bare `pgrep -fc`
→ exit **2**; `|| [ $? -eq 1 ]` → exit **1**, still red because 2 ≠ 1; the normalized grep form
→ exit 0. So *"cannot be stored here at all"* is struck, and the bound restated as the exclusion
it is: AC-1's pipefail criterion excludes **any** instrument signalling emptiness through exit
status, **correct ones included** (the same awk with `| grep -c .` measured correct in both
directions and still unstorable). The preference for awk now rests on the false-positive
measurement instead: **`ps -Ao command= | grep -c '[m] pytest'` read 3** at an instant when the
prescribed cell read 1 and exactly one real `-m pytest` was alive — CARD-306's gate, and both
false positives were the measuring agent's own wrappers.

**One deliberate rename, flagged rather than buried** — my own F-009 prescribed it and my own
discipline line forbade renames. `…_is_written_in_one_place[…]` →
`…_is_written_in_one_place_in_config_yml[…]`: two ids out, two in, same assertion, scope now in
the name as well as the docstring. The old name resolves to **0** `def` lines, while `main`'s
cycle-1 review YAML still spells it — a prose mention in a historical record, with R4's `check:`
never having named it and `--verify-refs` clean. **Cycle 2 is checking that this is inert**,
because this board has measured a synced review YAML silencing a live dead-ref warning.

### Numbers

**Node ids 439 → 445 NET.** Cycle 2 re-derived the **raw** symmetric difference as **2 removed /
8 added**; the 6/0 below is net-of-rename, which the commit message disclosed and this summary did
not. Both figures are now stated, labelled. The 6 net additions are (the orphan test, the
config-ref resolver, and the four
visibility-control rows), 0 deletions, plus the one rename above. **Zero skips, and that is
derived** — `-rs` printed no skip section on the class (35 passed), the module (445 passed) or
the three guard modules (77 passed); the suite-wide **27 is explicitly not confirmed**, because
that needs the full suite, which the brief forbade. Runtime as ranges above. **No load figure.**
Validators (the `forge_1` copy, read-only): **100 WARN, 0 ERROR**; `--verify-refs` →
`dead_check_ref: []`, `check_refs_verified: true`. Seven mutants, all out of tree via
`git archive`, needle uniqueness asserted before each edit, blob hash recorded and re-verified
after each restore, `__pycache__` swept, worktree never modified.

Housekeeping: the worktree carried an **untracked byte-identical duplicate** of the cycle-1
report under the `20261029T…` name that `main` holds as `20261030T…`; it was moved to the
session scratchpad rather than deleted or committed, and nothing references it. Two of eight
module runs showed `2 failed, 443 passed` whose names were lost to a truncated `tail` — chased
down rather than left: it is finding 12, now gone, with six consecutive 445-passed runs after.

- [Fix 1] All 11 findings addressed; F-001's two sentences made true with M-A killed and a
  standing control in both directions; a 12th finding found and fixed; one cycle-1 mutant refuted
  as non-discriminating.
- [Review 2/3] Dispatched — narrowly scoped to the five new instruments, the rewritten refutation
  criterion and its declared bound, and the edit to CARD-308's frozen census. The round's own
  reason, which I accept: **a fix round that adds instruments should not be the round that
  vouches for them.**

---

## Review cycle 2 — **8.5** (cycle 1: 8.0; `min_improvement: 0.5` met **exactly**)

`meta/review/20261030T120000Z-CARD-304-cycle2.yml`. Reviewed `2583783b` on base `74debef2`.
Nine findings. **Its verdict was "land it"; the orchestrator overrode that and took fix round 2** —
see the reason at the bottom of this section.

**What it confirmed, by re-deriving rather than reading:**
- **F-001's two sentences are true and R4's normative text is untouched.** Replaying cycle 1's
  *surviving* mutant (the grep given a bad flag) now **reds** `…visible_to_ps[e]` where cycle 1
  got 29/29 green. G-1: one hunk, **every changed line a `#` comment**, nothing touching
  `statement:`, `scope:`, `severity:` or `check:`.
- **`grep -q` really is non-discriminating** — under `-q` the grep child still carries the pattern
  in its argv, so the fixed branch finds it legitimately; only the bad-flag form leaves no child.
  **Fix round 1's correction to the committed cycle-1 report stands.**
- **`_children_of` survives embedded whitespace, structurally**: `split(maxsplit=2)` with the
  command column last cannot shift; multi-space runs come back byte-identical to `ps -o command=`;
  a 1034-char argv was untruncated through a pipe; right-aligned pids are eaten by `str.split`.
  Truncating the argv and dropping the parentage filter both red.
- **CENSUS/DEFINED is exactly three in, zero out** — re-derived independently by running CARD-308's
  own `_declared_refs()`/`_verdicts()` against out-of-tree archives of both commits; all three in
  DEFINED with `def` lines. **G-2 intact (23 passed), and its counterfactual confirmed**: naming
  the three refs in that file **reds G-2**, so the unnamed form was necessary, not stylistic.
  Updating the frozen baseline was right — it went red and *forced* the derivation.
- The **≥2 orphan floor is right and tight** (child count exactly 2 over 12 trials), and the orphan
  claim re-derives from a pre-fix archive: **five before, zero after.**
- Sandbox deselect **11 of 35, 24 participating**; comparison **127 passed**; validators **100 WARN
  / 0 ERROR**, `dead_check_ref: []`, `unparseable_sources: []`.

### The four findings that decided the override

**F-101 (high) — a row that cannot red, and the mechanism nobody had named.**
> **BSD `pgrep` excludes the invoking process *and all its ancestors* unless `-a`.**

So the test's own runner — always a real `-m pytest`, which the prescribed cell counts (it reads 2
from inside a run) — is **invisible to every pgrep form in the list**, and half (1) of fix round 1's
new criterion is **structurally incapable** of reddening on the `[pgrep -f]` row. Proved both ways
with the same stale instrument: **killed by half (2) alone while CARD-306's gate was live**, naming
its pids; **survived at 2 passed on a quiet host.** So the declared bound — *"half (1) carries the
row either way"* — **is false for that row**, and the docstring says otherwise. Half (1) *is* real
for the `-fc` row.

**F-104 (medium) — F-005's failure mode re-entered through the F-004 fix.**
`test_a_probe_leaves_no_orphan_behind` **measures a wait, not a kill**: with
`start_new_session=False` on one site it still **passed**, in **65 s against ~5 s**, because
`proc.wait(timeout=60)` waits the probes out. With all six sites, **the 120 s hang guard fired —
15 dots, no summary line** — *exactly* the no-verdict mode F-005 was raised to remove, because
`_kill_group`'s 60 s wait multiplies by up to 24 spawns in one fixture node. **The exposure was
moved, not shrunk.**

**F-103 (medium) — `_is_a_shell` is hand-written, permissive by default, uncontrolled, and never
exercised.** `/etc/shells` exists, has **7 entries, and all 7 agree with the heuristic** — so
deriving it changes no present answer and makes the set checkable, which is what ADR-0039/R2 asks
for (mandatory, `tests/**` in scope). False negatives measured: `env zsh`, `/usr/bin/env sh`,
`/bin/bash-5.2`, a shebang wrapper; false positive `/usr/bin/ssh`. **Its mutant does not red** —
`return False` leaves 35 passed; only `return True` reds — so it is controlled **only in the
harmless direction**, and its default on an unrecognised shape is a **silent pass in exactly the
direction F-001 was about**. And 12 trials × 30 polls showed the case-(e) child set constant: zsh's
pre-exec window **never appears**, so the guard is never exercised.

**F-102 (medium) — the native reimplementation is faithful today and has no control.** Zero
divergences against the awk over every live `ps` row and a 20-case corpus — but **the awk is read
from `config.yml` at runtime while the two halves are frozen in Python and nothing compares them**,
and `_is_a_real_pytest_run` → `return False` **survives**. The project's `mask_runs` precedent is
cross-checked from the test tree; this copy is not.

### Five carried figures measured wrong, two of them mine

1. **"439 → 445, 6 additions, 0 deletions"** is **net-of-rename**; raw is **2 removed / 8 added**.
   Corrected above, with AC-5.
2. **"each new instrument carries a mutant that reds it"** is **false** for `_is_a_shell` and
   `_is_a_real_pytest_run` — and the orphan test's own subject escapes its coverage.
3. The **class cost band 5.3–5.8 s / 6.2–6.7 s** is exceeded in **both directions one day old**:
   4.95/4.99/5.31 s session and 5.54/5.61/6.51 s wall quiet; 5.64/5.87/5.96 and 6.65/6.74/7.13 with
   a sibling gate live. **The class figure never got the domain treatment the module figures got.**
4. The **module band 37.6–39.0 s** measured 37.28 / 38.62 / 39.09 / **40.30** s — outside at both
   ends. (445 passed, 0 skips, every run.)
5. `config.yml`'s **"reading 3 against a true 1"** is **not reproducible**: 2 vs 1 with a gate live,
   1 vs 0 quiet. **Contention-dependent, no domain stated.** The *argument* stands; the figure does
   not.

### F-105 — the silencer, measured on this card rather than feared

The rename's orphaned name is **inert today**: 0 `def` lines, spelled in exactly one tracked file
(the cycle-1 YAML), absent from the census, never named by R4. But with that dead name planted into
R4's `check:` list, the result is **`[]` while the cycle-1 YAML is present, and the warning appears
the moment that one file is moved aside.** This board's known mechanism, now demonstrated.
CARD-319 owns the resolver.

### Process

**CARD-306's merge gate took the lock at 21:34:29Z mid-cycle**, and CARD-255's foreign-holder guard
collapsed **every worktree run to 0 collected tests** — *a 0-collected run is not a green run*, and
the reviewer recognised it rather than banking it. Work moved to an out-of-tree `git archive` with
blob hashes recorded, labelled by phase. **That interference is also what made F-101's both-ways
measurement possible**: the stale instrument could only be shown killed *while a sibling gate was
live*. Twelve mutants, all out of tree, blobs restored to the commit's own hashes, no `git stash`
(list still 4), no orphans left behind.

**One instrument defect of the orchestrator's, before the sync.** My own pre-sync dead-ref check on
this YAML reported **26 of 26 symbols dead**, because I wrote `\b` in a BSD ERE pattern, where it is
undefined and silently matches nothing — **the single trap I have put in every brief today.**
Re-run with a proved instrument (positive and negative control stated): **7 apparent dead, all 7
artefacts of my own over-broad regex** — module *paths* (`test_suite_profile`,
`test_check_ref_resolution`), `config.yml` **keys** (`test_command`, `test_scope`, which are the
card's own negative control and *must not* resolve), a line-wrapped class fragment, the
`pytest_configure` fragment, and a prose placeholder. **Zero genuine dead refs**, so the sync is
safe — and the over-broad shape is the same one fix round 1 had already had to narrow in the card's
own resolver.

- [Review 2/3] Score: 8.5 ✓ threshold reached, improvement +0.5 (min_improvement met exactly)
- [Fix 2] **Dispatched against the reviewer's own "land it" verdict.** Four instruments in this card
  are blind, uncontrolled, or both: a row that cannot red on a quiet board, a guard whose permissive
  default is uncontrolled and never exercised, a predicate with no control and no cross-check, and a
  test that measures a wait instead of a kill while re-entering the hang-guard mode F-005 removed.
  **This is the card whose entire purpose is to stop figures whose instrument cannot distinguish
  "the quantity is zero" from "the instrument is blind."** Landing four of those from this card
  would be the same mistake as shipping the false ADR sentence fix round 1 was dispatched to repair.
  Cycle 3 remains.
