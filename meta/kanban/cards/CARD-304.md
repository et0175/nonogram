# CARD-304: ADR-0039/R4 has no executing check — a figure's instrument is held by a lens, not by the tree

**Status:** ready
**Priority:** P2
**Category:** enabler
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/304-an-executing-check-for-figures
**Worktree:** —
**Source:** wave 62's retrospective (2026-10-28), which promoted the wave's dominant finding family into **ADR-0039/R4**. The rule ships with `check: {kind: review-lens}` and this card owes the flip to an executing check — an ADR check ref that names a planned test reads as mechanically checked while checking nothing.
**Idea:** —
**Wave:** 67
**Created wave:** 62
**Deferred waves:** 3 <!-- CORRECTED 2026-10-30 by the waves 63-65 retrospective. It read 0. This card was created in wave 62 BY wave 62's own retrospective, which promoted the figures family into ADR-0039/R4 and left R4's flip to an executing check owed here. It then sat unscheduled through waves 63, 64 and 65 while that same family produced EIGHT more gating findings across five cards. The counter never moved because cmd-retrospective Step 4c increments only tech-debt cards IN THE CURRENT WAVE SCOPE, and this card is Category: enabler and was in no wave's scope - so it aged invisibly by construction. Stamped into wave 67 on owner decision. -->
**Depends on:** —
**Touches:** tests/test_suite_profile.py, meta/architecture/decisions/adr/0039-guard-coverage-claims-need-controls.md
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

## Worktree notes — CARD-304's implementation round (2026-10-29)

### What was built, and where

- **`meta/kanban/config.yml`** gains `review.host_cells:` — a **JSON document
  inside a YAML block scalar**. JSON because PyYAML is *not* in ADR-0006/R1's
  dependency baseline (nothing in `pyproject.toml` declares it; it is in this
  venv incidentally), so a test that imported it would gate the whole check on
  a package a bare checkout lacks, and a hand-rolled YAML reader would be one
  more unproven instrument inside the file about unproven instruments. The
  block carries the three host cells, the rival-pytest truth table's seven
  cases with what each one claims and how to create it, and the six rejected
  instruments with their verdicts.
- **`tests/test_suite_profile.py`** gains
  `TestHostCells_ThePrescribedInstrumentsExecuteAndRespond` beside the existing
  census guards, as the card's Worktree notes asked. Fifteen test methods,
  twenty-seven collected node ids.
- **`ADR-0039/R4`**'s `check:` flips from `{kind: review-lens}` to
  `{kind: test, ref: ...}` naming three of those methods, with a REACH comment
  in R1's shape. The hunk is confined to the `check:` line and its comment,
  because CARD-308 is editing the same file's commentary concurrently.

### The prose the data replaced, and the two figures in it that were wrong

The commands were restated in the prose at the top of the host-cell section.
They are now written **once**, in `host_cells:`, and
`test_each_prescribed_command_is_written_in_one_place` reds if either is
restated — which is the only corner of R4's "retracted everywhere it was
written" clause a tree can check.

Re-measuring the prose to write the data turned up two wrong figures in it,
both of the exact family R4 was promoted for:

1. **The truth table's own prescribed row had a wrong cell.** Row 6
   (`ps|awk first-token-is-python`) recorded **(b) = 1** — a real pytest
   started through `.venv/bin/pytest`. Measured 2026-10-29 against a live
   console-script run: it is **0**. The awk keys on ` -m pytest` and that
   run's argv is `.../MacOS/Python .../.venv/bin/pytest …`, which never holds
   the substring. This is the **same mechanism the table already records three
   rows up** for `pgrep -f 'm pytest'`, transcribed wrong into the row that
   replaced it. The summary sentence under the table inherited it: *"ONLY THE
   LAST ROW PASSES ALL FIVE"* — it passes four.
2. **A declared bound outlived the instrument it was about.** The paragraph
   beginning "DECLARED BOUND" said the working pattern keys on the
   framework-python re-exec path and would be blind on a non-framework venv.
   That is true of `pgrep -f 'MacOS/Python.*pytest'`, which case (d3)
   **retired**, and false of the `ps|awk` form that replaced it:
   `$1 ~ /[Pp]ython[0-9.]*$/` matches a plain `.venv/bin/python` as readily as
   the framework re-exec, so a non-framework venv is the one host shape this
   instrument is *not* bound by. Both are corrected in place with the
   correction stated, not silently.

The card's own Worktree notes were stale in the same way: they say `config.yml`
"currently prescribes `pgrep -f 'MacOS/Python.*pytest' | wc -l`". At `ca7c8c56`
it prescribes the `ps -eo command= | awk …` form; the pgrep form was retired by
case (d3) one revision earlier.

### Two traps this round measured, both of which make a control vacuous

- **A negative control that does not exist.** Written the obvious way —
  `zsh -c ': <text mentioning pytest>; sleep N'` — the wrapper **is not in
  `ps`** by the time anything looks: zsh execs its last command and the
  process's argv becomes `sleep N`. Measured: argv `'sleep 20'` for that
  shape, and the full `/bin/zsh -c : … -m pytest …` for
  `': <text>; sleep N & wait'`, which forks. A flat reading against an absent
  near-miss is a vacuous pass wearing a control's clothes, so every negative
  here is judged only after `test_each_near_miss_probe_is_visible_to_ps`
  asserts the probe's own argv.
- **A fourth false-positive source: the act of measuring.** A search tool
  (`grep`, `ugrep`, `rg`) carries the pattern in its own argv, so a probe that
  excludes only shells still counts one. It is case **(e)**, new here. The
  prescribed `ps|awk` form is immune because `$1` is then `/usr/bin/grep`, and
  that immunity is now asserted rather than reasoned.

### Why two harnesses and not one

Executability and responsiveness are different findings and R4's whole point is
that they are. So AC-1 runs a prescription with `set -o pipefail` and judges
the **exit status**; AC-2 runs the instrument **without** pipefail and judges
the **reading**. One harness would red a blind form for the wrong reason — "it
exited 1" instead of "it did not rise while a real pytest was alive".

`pipefail` is also what makes AC-1's criterion mean anything: the rejected
`pgrep -fc` form was prescribed *inside* a `| wc -l` pipeline, and without
pipefail the pipeline exits 0 while the cell comes back empty — exit 0 with an
empty cell being precisely the defect. Its cost, stated as a bound in the data:
a grep- or pgrep-based prescription exits 1 on a legitimate empty match, so it
cannot be stored as a host cell at all without conflating "blind" with "quiet".
The awk form exits 0 when it matches nothing, which is **why** it is the
storable one.

Readings are **deltas**, never absolutes. An absolute rival-pytest count is
host state — this board runs up to five cards concurrently and a sibling
worktree's gate counts, which is exactly what happened mid-measurement during
this round and produced a (d3) and (e) reading of 1 that belonged to CARD-308.
Each case is judged against a baseline taken immediately before it and re-taken
after it; a baseline that moved is a **refusal to judge**, retried up to four
times, and the failure that ends it prints the process lines the instrument
actually matched — which is the only thing that settles such an argument.

## AC-3 — the residue, each shape with the reason it is unreachable

A check that claimed the whole of R4 would be R4's own defect. These are the
shapes AC-1 and AC-2 do **not** reach. They stay with the lens (decompose 6c4,
`forge:review` Step 8h), and R4's comment names them.

1. **A figure in prose — the general case.** A number in a card, a retro, an
   ADR or a docstring has no machine-readable link to the command that produced
   it. `config.yml` is reachable *only* because it prescribes commands rather
   than reporting results; nothing generalises from that. **Unreachable, not
   deferred.**
2. **A ratio whose halves came from different instruments, runs or baselines.**
   (CARD-292's 9.9× — profiled numerator over unprofiled denominator; 8.0×
   through the other door.) The defect is in how the two numbers were
   *obtained*; the committed text retains nothing of their provenance, so there
   is no artefact to check. **Unreachable from the text.**
3. **A point estimate published for a quantity with run-to-run spread.**
   (22.0 % / 21.2 % / 21.30–21.86 %; and a 7.9–16.4 s band that two later
   rounds exceeded at 18.47 s and 22.84 s on the same machine within hours.) A
   single number is syntactically indistinguishable from a correct one;
   deciding it needs the spread, which is not recorded beside it.
   **Unreachable without re-running the measurement.**
4. **A figure correct at one revision and stale at another** — R4's DOMAIN
   clause. (An ADR occurrence count, right at one revision, wrong at the next.)
   Nothing records which revision a number was taken over, so staleness is
   undecidable from the figure. The nearest reachable thing is a *derived*
   census asserted as an equality, which is what `RENDER_HEAVY_SNAPSHOT` and
   `CLIFF_EDGE_SNAPSHOT` already do for their own sets — and that only works
   where an authority can re-derive the number.
5. **A refuted figure surviving in a second place.** Reachable **only** for a
   prescribed *command* inside one file, which
   `test_each_prescribed_command_is_written_in_one_place` now does. Not
   reachable for the figures those commands produce: four docstrings carrying a
   306 KB figure the same round struck out were a genuine instance and no check
   here would find them.
6. **A mis-stated instrument warning.** A brief claiming `grep -c '\[WARN'`
   returns no matches, when it returns 100 at exit 0 — the real failure being a
   `^` anchor in the claimant's own pattern. A wrong *warning* about an
   instrument costs verifications just as a wrong reading does, and there is no
   artefact in the tree for it at all.
7. **Instruments that are not shell commands.** `\b` inside a `git grep -E`
   pattern (undefined in POSIX ERE, silently matches nothing); `grep -cE
   "^\[WARN"` against output that indents its warnings; macOS having no
   `timeout`, whose `exit 127` reads as a clean `0/0`; a bare-name `git grep`
   handed a `path::name` node id. Each is a one-off command typed into a shell
   by an agent, not a prescription in a tracked file, so there is nothing to
   extract. The *only* reason the rival-pytest cell is reachable is that
   somebody wrote it down as a convention.
8. **Any host but this one.** The cells are BSD spellings (`ps -eo`,
   `sysctl -n vm.loadavg`), and the check asserts them **unconditionally** —
   there is no `skipif`, by construction: this module's
   `test_nothing_in_this_module_goes_quiet_on_a_condition` asserts it has none.
   So on a host lacking them the suite reds, which is AC-1's intent and equally
   its bound: the prescription is verified where the suite is green and nowhere
   else.
9. **The live-log sandbox comparison does not cover this class.** It is
   deselected there (`SANDBOX_DESELECTED`, with the reason stated beside it):
   the sandbox mirrors `tests/` and `meta/profiling/` only, so `config.yml` is
   absent in it, and the comparison asserts every sandboxed test PASSES. This
   class therefore carries its structural defence (its own planted controls)
   and not the behavioural one — the only guard in this module with one defence
   rather than two.

## Can the `ps`/`pgrep` prescription be made correct at all?

**Yes, and it already is — for the board's own runs, which is the whole of what
the cell is for.** Measured on this host 2026-10-29 with the near-miss proved
present each time, the prescribed `ps -eo command= | awk '$1 ~
/[Pp]ython[0-9.]*$/ && /-m pytest/' | wc -l` rises by exactly 1 for a real
`python -m pytest` and is flat for all four near-misses, including the
framework-path wrapper that retired its predecessor and the search tool that
the act of measuring spawns.

It has **one** measured blindness — a pytest started through the
`.venv/bin/pytest` console script — and that is a declared bound, asserted in
both directions so it cannot drift, and tolerable only because
`review.test_command` starts pytest as `-m pytest`, which
`test_the_board_starts_pytest_in_the_form_the_cell_can_see` now asserts. It was
**not** widened to `/pytest/` (which does see case (b)) because that counts any
python process whose argv merely mentions pytest and no control for that
direction has been measured — widening an instrument without the control for
the direction you widened into is how this cell got its last two defects.

So it belongs in AC-1/AC-2's executing coverage, not in AC-3's residue. What
does belong in the residue is the orchestrator's conclusion that "no one-liner
gets the count right on this host, so record the PID list instead": the PID
list is the right **diagnostic** and it is now what the failure messages print,
derived from the prescription by dropping its counting stage so the diagnostic
cannot describe a different query from the number. But a PID list is not a
cell: a gate row needs a figure, and a figure needs an instrument with
controls, which is what this card gives it.
