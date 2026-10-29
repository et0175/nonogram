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
**Review score:** —
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

R4's `check:` flipped to three bare names in R1's shape, all verified to resolve, with
`--verify-refs` reporting `dead_check_ref: []` post-commit. **R4's statement is untouched**
(G-1). Census **410 → 439, 0 lost**, all 29 additions named. **Zero skips**, confirmed with
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
