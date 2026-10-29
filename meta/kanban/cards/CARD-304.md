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
