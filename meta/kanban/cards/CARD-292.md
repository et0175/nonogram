# CARD-292: One test completes only on a quiet machine — the suite has a per-test ceiling nobody has measured, and this board has paid for it three times

**Status:** ready
**Priority:** P1
**Category:** tech-debt
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/292-measure-the-per-test-ceiling
**Worktree:** —
**Source:** orchestrator, 2026-10-24, from CARD-276's fix-round pre-gate. Found by chasing a phantom: I twice attributed a dying test run to CARD-276's diff before measuring both arms under the same conditions. The diff was never implicated; the host was.
**Idea:** —
**Wave:** 62
**Created wave:** 58
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/test_book_export_interior_cover.py, meta/profiling/card-292-per-test-ceiling.md, meta/kanban/config.yml
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this is P1 when it is nobody's feature

**This board has paid for this condition three times and never named it.**

* **CARD-218's merge gate** reported **101 skips against a baseline of 27** — 74 transient Postgres timeouts under load average ~5.8. Every one re-ran green. The gate's own finding was its skip count, and an orchestrator spent a round establishing the 74 were noise.
* **CARD-271's merge gate** red on a `Page.goto` timeout in a file the card never touched, reproduced green three times afterwards.
* **CARD-276's fix-round pre-gate, 2026-10-24**: a whole-file run that had passed at **104 passed / 393.54 s** hours earlier stopped at `[ 57%]` with no summary line, **at both revisions of the card**, six runs, identical stopping point. I attributed it to the card's diff **twice** before measuring both arms under the same conditions.

Three cards, three gates, one underlying condition: **the suite's cost per test is close enough to a hard ceiling that whether a run completes depends on what else is running on the machine.** Nobody has measured the ceiling, and nothing on the board states how close anything sits to it. That is why a measurement card is P1: **until the ceiling is known, every gate verdict on this board carries an unquantified chance of being about the host rather than the tree.**

## What is measured already — the premise, so this card starts from numbers

Taken 2026-10-24 on Mac15,6 (Apple M3 Pro, 11 cores, 18 GB, macOS 26.7.1, Python 3.14.3, pytest 9.1.1):

| observation | measurement |
|---|---|
| `test_each_door_axis_arm_catches_a_shape_the_other_misses` run **alone** | **120.93 s** at `31897571`, **120.98 s** at `ced5e648` — then exit 1, **zero bytes of output**, `0 signals received`, 166 MB / 141 MB peak RSS |
| the same test **warm, inside a whole-file run** | **99.21 s** (the fix round's own `--durations` reading) |
| the file's 33-test sibling partition | **119.51 s, 33 passed** — half a second under |
| the whole file, quiet machine, earlier the same day | **104 passed, 393.54 s** ✅ |
| the whole file, loaded machine, **both revisions** | `[ 57%]` + 5 dots, exit 1, **no summary line** — 6 runs, byte-identical |
| machine state when the runs died | **load average 12–20**, **zero python processes**; top consumers PyCharm 19.9 %, a `claude` process up 2d 2h 15.4 %, IntelliJ IDEA 12.2 % |

**THE MECHANISM, identified 2026-10-24 after four wrong attributions by the
orchestrator — read this before the table above, because the table's load
column is a red herring.** The test completes **inside a full suite** and dies
as a **single-file run**, at *both* revisions, independent of load:

* CARD-282's merge gate ran the whole suite at load 4.43 → 3.71 — **9122 passed,
  0 failed, 1880.81 s** — and that suite **includes this file in its entirety**.
  The test passed there.
* The same file, run alone in CARD-276's worktree at load 3.04, stops **inside**
  that test at 77 of 126 reported, with every earlier test green.
* Verified with the arms identifying themselves (`collected 104` = pre-fix,
  `collected 126` = post-fix): **both arms stop in the same test at the same
  77.**

So the cost is **~99 s warm against ~121 s cold**, straddling a ceiling near
120 s: inside a suite the module's 306 KB source is in the page cache by the
time this file runs, and standalone it is not. ``_plant`` reads it from disk
**144 times** in that one test.

**Four attributions I made and withdrew**, recorded because the method error is
the card's real subject: (1) "the round pushed the test over" — false, it fails
at the pre-fix revision; (2) "the whole file passed before and not after" —
false, the pre-fix bytes fail too; (3) "it is machine load" — false, it fails at
load 3.0 where it passed at similar load; and (4) "both arms are identical,
therefore exonerated" — the right conclusion on a **broken measurement**, since
both arms printed `[ 57%]`, meaning 126 collected, so arm 2 was never the
pre-fix file. **Every one of those comparisons lacked a check that the arm was
the arm.** The run that settled it printed the placed sha *and* the collected
count before testing anything.

**Ruled out:** memory (166 MB peak against 18 GB), a `pytest-timeout` plugin (not installed), a `timeout` in `pyproject.toml` (absent), a signal (`0 signals received`), and the card's diff (both arms identical).

**Not established, and this card's first job:** *what* the ~120 s ceiling actually is. A per-test watchdog, a harness limit on a child process, or a coincidence of two independent 120 s figures. **Do not assume; measure it.**

## What to implement

1. **Find the ceiling and name it.** Write a throwaway probe **outside `tests/`** that sleeps or spins for a parameterised duration under pytest, and bisect the boundary. Report what it is (per-test? per-process? per-shell?), whether it is wall clock or CPU, and whether it moves with load. **If it turns out not to be a fixed ceiling at all** — e.g. the test is simply load-sensitive and the 120 s figures coincide — say so; that is a finding, not a failure, and it changes the remedy.
2. **Publish the suite's distribution against it.** From `meta/profiling/suite-durations-20261023.txt`, list **every test within 50 % of the ceiling**, with its file and its duration. The board needs to know how many cliff-edge tests exist, not just that one does. (`test_each_door_axis_arm_catches_a_shape_the_other_misses` at ~99 s and `tests/test_book_export_interior_cover.py`'s guard class at 14,258 ms/test are the known candidates; **derive the list, do not extend this one by hand.**)
3. **Cheapen the one test that is over the line.** Its cost is **three readings per row** over a table the previous card grew. CARD-276's own round proposed this and had no budget: *"that test's three-readings-per-row shape cheapened — it is more expensive on its own than this round's entire addition."* The card's G-6 forbids durations as *its* claim; this card's subject **is** the duration, so that guardrail does not apply here.
4. **Make a gate verdict say whether the host was quiet.** A merge gate that reds under load and greens idle is not a verdict. Record the load average at gate start and end beside the result, so the next orchestrator spends minutes rather than an hour distinguishing a tree failure from a host one. (`meta/kanban/config.yml` is in `Touches` for this and nothing else.)

## Acceptance criteria

- **AC-1** (the ceiling is measured, not assumed): *Given* a parameterised probe outside `tests/`, *then* the card states what the ~120 s boundary is, with the bisection that found it and whether it is wall clock or CPU — **and confirms or refutes the warm/cold mechanism above by measuring `_plant`'s 144 reads directly** (time them with the page cache warm and after dropping it, or count the syscalls). A hypothesis with a test beats a cause with a story: the orchestrator produced four of the latter. (**gate**: the probe and its readings recorded; no new standing test — a test that asserts a host property would red on a different machine.)
- **AC-2** (the distribution is derived): *Given* the committed duration artefact, *then* every test within 50 % of the ceiling is listed with its file and duration, **derived by parsing the artefact** rather than by extending a hand-written list. (test: `TestSuiteCeiling_TheCliffEdgeListIsDerived` in `tests/test_suite_profile.py`'s style — an equality against a live derivation, like `RENDER_HEAVY_SNAPSHOT`, so the list cannot go stale silently.)
- **AC-3** (the over-the-line test completes): *Given* `tests/test_book_export_interior_cover.py` on a **quiet** machine, *then* the whole file completes with every test under the ceiling, and the previously-over test is **named with its before and after cost**. (**gate**: a whole-file run with the load average recorded at both ends; "quiet" is defined in the card as a measured figure, not a feeling.)
- **AC-4** (guard, no coverage bought back cheap): *Given* the cheapened test, *then* **its claims are unchanged** — the four equalities it asserts (`callee identity` 23, `door spelling` 1, both arms off 30, `kept` 6) still hold and are still asserted. (test: the test itself, node id unchanged; **gate**: the four figures re-derived.)
- **AC-5** (guard, no test deleted, renamed, skipped or merged — **including parametrize ids**): *Given* the touched files, *then* the collected node-id set loses nothing. (**gate**: set difference with `-o addopts=''`, removals 0, additions named. **Param ids count**: a reworded id is a deleted cell, which CARD-282's fix round nearly shipped.)
- **AC-6** (the gate records the host): *Given* a merge gate or wave smoke test, *then* its recorded result carries the load average at start and end. (**gate**: the convention documented and used once in this card's own gate.)

## Guardrails

- **G-1: do not cheapen a test by guarding less.** AC-4 is the whole point: the four equalities stay, their figures stay derived, and the controls that kill on them stay killable. A cheaper test that checks less is a regression wearing a speed-up.
- **G-2: do not assert a host property in a standing test.** The ceiling is a fact about this machine; a test that encodes it reds on a different one. Measure it in the card, derive the cliff-edge list from the artefact, and let the standing test guard the *derivation* rather than the *value* (AC-2's shape).
- **G-3: probes stay OUT of `tests/`.** `meta/profiling/rank_durations.py:45` defines the frozen render set by grepping eight idioms over `tests/**/*.py`, and `tests/test_suite_profile.py:482` asserts the live grep **equal** to a 33-entry snapshot — a probe under `tests/` naming `interior(` reds the suite, and `tests/test_book_export_interior_cover.py` is **in** that snapshot.
- **G-4: do not edit `src/**`.** This is a test-cost card. A production change is a finding to raise.
- **G-5: no new runtime dependency** (ADR-0006/R1: stdlib + Pillow + NumPy). **No `pytest-timeout`** — adding a plugin to measure a limit changes the thing being measured, and it is not in the dependency baseline.
- **G-6: corpus minimums are never lowered**; `tests/fixtures/**` is never regenerated.
- **G-7: measure both arms under the same conditions.** The card exists because I did not. Every before/after figure here is taken back to back on one machine state, with the load average recorded, or it is not a comparison.

## Architecture context

- **FR/CON:** none. Suite cost and gate honesty; no requirement's verifying test changes.
- **ADR:** ADR-0039/R1 (AC-4's claims need controls that can fail), ADR-0039/R2 (AC-2's derived list).
- **Components:** none — test tree and the kanban config.
- **Trace:** not applicable.

## Worktree notes

- **Scheduling.** `tests/test_book_export_interior_cover.py` is also CARD-276's (in flight), CARD-287's (344.29 s, 24.4 % of the suite) and inside CARD-273's `tests/**`. **This card serializes against all three**, and the natural order is **after CARD-276 merges** — it is the card that grew the test, and this one cheapens it. CARD-287's own subject is the same file's dominant class, so these two should be read together before either is dispatched.
- **Why P1 and not P2.** Nothing here is a feature and nothing a customer sees. It is P1 because it is **about whether this board's verdicts mean anything**: three gates have already been argued about on evidence that turned out to be the host, and the next one will be too. The cheapest fix is to know the number.
- **The phantom, recorded as the method lesson.** Both of my wrong attributions compared **a quiet run from hours earlier against a loaded run from minutes earlier**. The controlled version — both revisions back to back, nothing else running — took one command and settled it immediately. Running both arms under one machine state is not a refinement; it is the measurement.

## [A FOURTH instance, 2026-10-26 — added before dispatch so this card starts from complete evidence]

This card's "Why this is P1" lists three gates that paid for the unmeasured
ceiling. **Today added a fourth, and it is the cleanest of them**, because the
confounder was isolated rather than guessed at.

**CARD-283's merge gate** came back `1 failed / 9259 passed / 27 skipped` on
`tests/test_guard_integrity.py::TestGuardModule_CannotGoQuietAboveItsOwnGuards::test_no_guarded_module_silences_itself_at_module_scope`.
The card was nearly charged with it. It was **not** the card: the orchestrator
ran **both arms** — the same test alone on the branch (1 failed) and on **main**
alone (1 failed) — which established in two commands that `main` itself was red,
from the orchestrator's own `meta/profiling/measure_raster_share.py` committed in
`431f00c2` with `sys.exit()` at module scope. Fixed at `fcd03c99`.

**Why it belongs here rather than in a postmortem.** The three instances above
are all *host* noise; this one is *tree* breakage. They are indistinguishable at
the gate — both arrive as "the gate went red and the card is the suspect" — and
the only thing that separated them was a two-arm measurement that costs seconds
and that this board adopted after CARD-276 spent an hour not doing it. A ceiling
measurement that tells a reader **when a red is worth re-running versus worth
bisecting** is therefore worth more than a number: it is the first half of a
triage rule the board currently applies from memory.

**What this wave decided on gate figures, for scale.** `9160 / 27 / 0`
(CARD-276), `9227 / 27 / 0` (CARD-294), `9260 / 27 / 0` (CARD-283) — each
reported by the orchestrator to the owner as a fact about the tree, each
unqualified by any statement of how close the run sat to the ceiling. If this
card's measurement shows the margin is thin, those three verdicts were luckier
than they read.

**Two fresh data points this card may use**, both taken on a quiet box with the
suite lock redirected, both already in `meta/kanban/suite-timing.log`:

- `tests/test_book_export_interior_cover.py` whole-file: **467.30 s for 127
  tests** complete, against the card's recorded observation of the same file
  **dying around 120 s at two different revisions** under load. The same file,
  the same machine, two conditions.
- The full suite at **1601 s / 9287 collected** (CARD-283's gate) against
  **1534 s / 9254** (CARD-294's) — 173 ms/test against 166 ms/test, a 4 %
  spread between two runs eleven hours apart with no suite-cost work between
  them.

**Unchanged and still true:** this card must run **solo**. `tests/README.md`
says a contended run "tells you nothing at all" and that two quiet-host runs of
near-identical suites differ by ~19 %. It is queued behind CARD-295's review
cycle for exactly that reason, not behind its merge.

## [What "quiet" measured as, 2026-10-26 — AC-3 asked for a figure and this is one]

AC-3 requires *"'quiet' is defined in the card as a measured figure, not a
feeling"*. The orchestrator spent this wave waiting for a quiet box before
dispatching this card, re-reading `uptime` and deferring. **That wait was
founded on a wrong premise, and measuring it is this card's business.**

Taken on the board's own machine while CARD-295's merge gate ran:

| when | 1-min load | what was running |
|---|---|---|
| gate not yet started | **4.61** (4.38 / 4.52) | **no pytest at all** |
| ~60 s after gate start | **11.74** (8.66 / 6.29) | one pytest, 97.3 % of **one** core |

And the process table ~34 s in, sorted by CPU: the gate's own
`python -m pytest` at **97.3 %** was the **only** Python process on the box —
no rival pytest, no Chromium, no node. Everything above 2 % besides it was the
owner's desktop: `WindowServer` 36.6 %, `IntelliJ IDEA` 17.1 %, `loginwindow`
11.5 %, `AppleUserHIDDrivers` 9.5 %, `Claude.app` 8.5 %, the `claude` CLI 7.6 %,
two Chrome helpers 6.8 % and 4.0 %, `PyCharm` 2.9 %, Microsoft Defender 2.6 %,
and a `VTDecoderXPCService` 2.4 % (a video decode, 20 min elapsed).

**Three things follow, and the first two are corrections.**

1. **A load average on this box is not a proxy for test contention.** With zero
   test processes running the figure was 4.61. "Wait for the load to fall before
   dispatching" is waiting for the owner's desktop to be closed, which is not a
   thing the board gets to schedule. The orchestrator held this card for that.
2. **The operative definition of quiet is "no rival pytest", not "low load"** —
   and the board already has a control that enforces exactly that and nothing
   else: `meta/kanban/.full-suite.lock` with CARD-255's foreign-holder guard.
   The guard refuses a run while *another worktree* holds the lock; it says
   nothing about WindowServer, and on this evidence it should not.
3. **The 4.61 → 11.74 jump is NOT attributed here.** A single-core pytest cannot
   add seven to a load average. The likely reading is collection I/O — macOS
   counts uninterruptible I/O wait as runnable, and collection reads thousands
   of files — but this card is the one that gets to measure it rather than tell
   a story about it, and the orchestrator has already produced four stories on
   this exact subject (see the fourth instance above). **Recorded as an
   observation with its mechanism open**, which is what AC-1 asks of the ~120 s
   boundary too.

**AC-6 has its first instance.** CARD-295's merge gate recorded the load average
at both ends, written into the gate's own output file before the first test ran.
That is the convention AC-6 asks to see used once; it cost one `uptime` call.

**A caution for AC-3's whole-file run.** The 467.30 s figure above was taken
"on a quiet box". On this evidence that phrase needs restating as what was
actually true of it — lock held, no rival pytest — because if it meant "low load
average" it was never true at all, and the comparison against the file *dying
around 120 s* would be comparing two things that differ in an unrecorded way.
G-7 is the guardrail this would breach.
