# CARD-292: One test completes only on a quiet machine — the suite has a per-test ceiling nobody has measured, and this board has paid for it three times

**Status:** done
**Priority:** P1
**Category:** tech-debt
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/292-measure-the-per-test-ceiling
**Worktree:** — (removed at merge)
**Source:** orchestrator, 2026-10-24, from CARD-276's fix-round pre-gate. Found by chasing a phantom: I twice attributed a dying test run to CARD-276's diff before measuring both arms under the same conditions. The diff was never implicated; the host was.
**Idea:** —
**Wave:** 62
**Created wave:** 58
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/test_book_export_interior_cover.py, meta/profiling/card-292-per-test-ceiling.md, meta/kanban/config.yml
**Review score:** 7.0 → 7.0 → **8.5 cycle 3/3 CERTIFIED**, zero gating
**Started:** —
**Closed:** 2026-10-27
**Actual:** —
**Merge commit:** `714de66e`
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

## [CYCLE 1 — 2026-10-27] **7.0, NOT CERTIFIED**, 2 gating — and both are figures, not code

`meta/review/20261027T175441Z-CARD-292-cycle1.yml`, reviewed `98482d2c`.
**Every AC but one is MET and every guardrail is MET**; what blocks the 8 is the
card's own description of its own measurements. That is wave 50's family exactly,
on a card whose subject *is* measurement.

### The two gating findings

**F-001 — AC-6 is NOT MET, and it is the one cell the convention says decides
the verdict.** `card-292-per-test-ceiling.md:445` reports `rival-pytest 0 / 0`
labelled `(pgrep -fc)`. **BSD/macOS `pgrep` has no `-c` flag** — usage error,
exit 2, and an **empty** string inside `$(...)`. Line 343 goes further and says
in prose that it *"returned 0"*, which it cannot have. And the §6 block the
document calls **"verbatim"** prescribes the broken form, so it is already false
against main's `d61f0be1`, where the orchestrator corrected it to
`pgrep -f '…' | wc -l`. The orchestrator seeded this one; the reviewer verified
it and then audited **the whole class** — `sysctl -n vm.loadavg`, `/usr/bin/time`,
the §8 selection grep (reproduces 29 files verbatim), `--collect-only
-o addopts=''` (542), both probes and the cProfile door are all executable and
reproduce their own figures. `pgrep -fc` is the **only** non-executable
instrument. Separately, `ps -Ao command | grep -c '[m] pytest'` is defective but
the document *declares* it and declares what its cells therefore do and do not
show — the honest-bound shape, and **not** a finding.

**F-002 — a figure this card refuted, shipped four times into the standing test
tree.** `tests/test_book_export_interior_cover.py:1105, 6313, 6385, 6398` state
the module is **306 KB** — the exact figure §1.4 recomputes and strikes out
(`| module size | 306 KB | 389,177 bytes |`). Measured: **390,485 bytes**
(381 KB). Not seeded, and the orchestrator confirmed the attribution rather than
taking it: **0 occurrences at base `6e0aadca`, 4 at `98482d2c`** — the card added
all four. A docstring figure is a claim **no mutant can catch**, which is why
this is gating rather than prose.

### Eight non-gating findings, four of which move a number

- **F-003:** the "re-splits its **whole** source" mechanism is **false on Python
  3.14** — `ast.get_source_segment` passes `maxlines=end_lineno+1` — and the same
  file contradicts itself 70 lines later.
- **F-004:** "389,177 **bytes**" and "44.8 MB" are **character** counts.
- **F-005:** "675 calls per analysis" is attributed to the wrong function (673
  splits, 740 `get_source_segment`), and the "675 × 108 analyses" chain does not
  hold — measured **25,873**, i.e. ~240 per analysis.
- **F-006:** the headline **9.9× / 90 %** pair is **cProfile-inflated**;
  unprofiled it is **8.2× / 80 %**. The instrument's domain leaked into the
  figure, which is the card's own rule turned on itself.
- F-007 (unnamed denominator revision), F-008 (M10's declared-but-real "the price
  can silently return"), F-009 and F-010 (info).

### What the review re-derived rather than accepted

**AC-1 MET** — 3 × 45 s in one process re-measured at **135.05 s, 4 passed,
exit 0**; a 130 s test killed at 120 s having accrued **0.26 s** of CPU, zero
summary lines, the dump naming the probe; the header hidden under `-q` and
visible under `-o addopts=''`; the page-cache refutation reproduced (216 reads,
**2** cold, 0.0454 s). **AC-2 MET** — re-derived with the reviewer's **own
parser** rather than `rank_durations`: 60.00 s threshold, 81.03 / 67.08, next
56.92 at 47 %. **AC-3 MET** — after arm 29.38 / 10.94 s, before arm re-derived
**via M10** at 105.65 / 87.27 s. **AC-4 MET** — 23 / 1 / 30 / 6 over 36 rows,
node id unchanged. **AC-5 MET exactly** — 0 removals, 10 additions, 127→132,
405→410, 532→542. **AC-6 NOT MET** (F-001).

**G-1..G-7 all MET**, and G-4 **mechanically**: `git diff --name-only 6e0aadca
98482d2c -- src/` returns nothing and `--numstat -- src` is empty, read from git
rather than off a diffstat.

**Mutation work, one node id at a time so attribution is per assertion:** 9/9
killable mutants reproduced **with the exact cell the matrix names**. Both
declared negatives are **true as declared** — M2–M4 die to the seeded corpus and
to the exhaustive sweep independently, so nothing separates the two controls and
the card's narrowed claim is accurate; truncating `_source_lines` by its last
element survives all three. **M10's declared survival is proved rather than
merely humble**: reverting the cheapening leaves the file green at 105.65 / 87.27 s
against 29.38 / 10.94 s.

### The orchestrator's phantom left no trace

Seeded observation 2 was the withdrawn "+2 skips" routing. The reviewer grepped
the document and both test files for it and found **no consequence**: the "29" in
this card is a **file** count and reproduces. The 29-file pre-gate re-run at HEAD:
**2310 passed / 15 skipped / 0 failed**, exit 0, 303.62 s against the card's
316.24 s, both skips attributed by name. The card never chased it.

### Carried to the merge gate

`collected 2325` is a property of base `6e0aadca` and **will not reproduce
post-merge**, because the §8 selection includes `tests/test_book_difficulty_dots.py`
and `tests/test_book_pdf_vector_primitives.py`, which CARD-296 changed on main.
The two files **this** branch touches have **identical blob shas** at `6e0aadca`
and `db529c13`, so no content conflict is expected.

### Procedure

The full suite was **not** run and `meta/kanban/.full-suite.lock` was never taken
and does not exist. One env override, disclosed: `NONOGRAM_TEST_HANG_SECONDS=600`
for the **M10 arm only**, so the uncheapened test could report its cost instead of
being killed at 120 s; every other run used the shipped default.

## [FIX ROUND 1 — 2026-10-27] `db0e1a3e` — both gating findings closed, and the inflation's cause found

Three files: `tests/test_book_export_interior_cover.py`,
`meta/profiling/card-292-per-test-ceiling.md`,
`meta/profiling/card292_plant_reads.py`. `src/` and `pyproject.toml` zero diff
against base. Nothing under `meta/kanban/**` or `meta/review/**` committed.

### Behaviour unchanged, and it is PROVED rather than asserted

The test file was parsed at `98482d2c` and at HEAD, **every docstring stripped**,
and the `ast.dump`s compared — **identical**. So the whole test-tree change is
comments and docstrings. The only non-prose delta in the round is one local
renamed in the probe (`total_bytes` → `total_chars`) plus the label it prints.
This is the strongest claim in the round and it is the right way to make it.

### F-001 — closed in three parts, plus two additions the brief did not ask for

The failure was **reproduced** rather than taken from the review: `pgrep -fc` →
usage line on stderr, **exit 2**, `X=$(...)` → `X=[]`. Working form returns `0`.

* **Prescriptions corrected** in §4 and §6.
* **A second instance of the same class, which cycle 1 did not flag.** §4's
  triage rule still *prescribed* `ps -Ao command | grep -c '[m] pytest'` with the
  predicate `> 1` — and the round measured that baseline at **1**, where the card
  measured **2** and the orchestrator measured **3**. Three readings, three
  values, for a figure used as a constant. §4 no longer prescribes it. *A fix
  audits the defect class, not the instance* — this one did.
* **The prose claim is withdrawn, not reworded.** §7 said `pgrep -fc` "returned
  0"; the document now states it cannot have, with the trace inline.
* **§6's "verbatim" now holds by construction**: the block is **extracted
  programmatically** from `main:meta/kanban/config.yml`, not retyped, `diff`
  against its lines 42–88 is empty, and the section names the snapshot commit.
* **The `0 / 0` results cell is marked NOT ESTABLISHED, not relabelled.** The
  provenance cannot be recovered, and the document says so — including that the
  true value is almost certainly 0 and that *"almost certainly is not a
  measurement"*. **No provenance was invented**, which was the one way this fix
  could have made things worse.
* **A positive control for the instrument**, which is what closes F-001 properly
  rather than cosmetically: a cell reading 0 because it is **broken** and one
  reading 0 because the box is **quiet** are indistinguishable from the figure
  alone. So the working form was taken **both ways** — `0` with nothing running,
  and **`1` taken deliberately while §8.2's own run was in flight**. The cell can
  rise, and it rose.
* It also corrected cycle 1 on a detail, by reproducing instead of copying:
  cycle 1 quoted the usage line as `[-Lfilnoqvx]`, and `man pgrep`'s SYNOPSIS on
  this box reads `[-Lafilnoqvx]`. Neither carries a `c`; both spellings recorded.

### F-002 — closed, with the unit named

All four sites now read **381 KiB**, the exact byte figure beside the first.
`grep -rn "306 KB" tests/` is empty; the two surviving mentions elsewhere are
quotations of the refuted story, inside quote marks.

### THE CAUSE OF THE 9.9× INFLATION, which is the round's best finding

Cycle 1 said the headline pair was cProfile-inflated. The fix found **why**, and
it is worse than inflation: **the published pair was never two readings of one
instrument.** `0.2864 s` matches the **unprofiled** memoised arm (0.278–0.282 s)
and not the profiled one (0.7323 s), while `2.8429 s` matches the **profiled**
stdlib arm. A ratio was formed by dividing a profiled numerator by an unprofiled
denominator. **Which half is mislabelled cannot now be recovered**, and the
document says exactly that.

Measured properly, with both arms through one door:

| door | figure |
|---|---|
| no profiler, 3 readings back to back in one process | 2.2565 / 2.2575 / 2.2663 s → 0.2781 / 0.2814 / 0.2819 s = **8.0×** (8.11 / 8.02 / 8.04); split **87.7 %** by difference |
| `cProfile`, **both** arms profiled | 2.9691 → 0.7323 s = **4.05×**; `_splitlines_no_ff` **76.1 %** tottime, **80.2 %** cumtime |

So the round also **corrects cycle 1's own replacement figure** — cycle 1 offered
8.2 × / 80 %, the measurement is 8.0 × / 87.7 %. Earlier commit messages on the
branch carry `9.9×` and **cannot be rewritten**; the document is where the
correction lives, and it says so.

### F-003 — restated, not deleted, and the claim survives

`ast.get_source_segment` passes `maxlines=end_lineno+1`, so it splits a
**prefix**, not the whole source — the original mechanism statement was false and
the file contradicted itself 70 lines later. But the cost claim holds restated:
649 splits re-scan **127,608,978** characters of 389,177 = **50.5 %** per call,
so the cost is still ∝ calls × module size. **Same exponent, half the constant.**

### F-005 — the attribution was wrong in a way worth recording

**716** `_source_segment` calls, **649** reaching the split (67 nodes unlocated),
**740** `ast.get_source_segment` in total (716 + **24** from the file's two cold
sites), **673** splits. **675 is a figure neither function produces.** The chain:
**25,873** calls over **108** analyses = mean **240**, not 675 — and 675 × 108 is
2.8× the truth.

### F-008 — DECLINED, with the consequence stated

The optional AST control (assert `segment()` resolves to `_source_segment`) was
declined, and the reason is a good one: it would turn **M10 from §8.1's control
into a kill**, so the matrix row cycle 1 independently reproduced would no longer
describe the tree. The consequence is stated plainly rather than hidden — the
memo's **existence** is guarded (M1 dies), its **use at the one hot call site is
not**, so the file can return to ~113 s with **no cell firing** — and named for a
successor card, with the two cold stdlib sites at lines **1438** and **2913**.

### Its own additions mutated, including a declared SURVIVOR

The prose adds no mechanism (proved by the AST equality above), so there is no
mutant to plant for it — stated rather than invented. The probe's one non-prose
delta got two, line-count preserving, each on its own selection:

* **P1**, deleting the unit mechanism (`len(text)` → `len(text.encode())`):
  **SURVIVES** all 542. Its only control is running the probe and reading the
  label, which then prints 44,972,712 under a label saying characters. **Declared,
  not hidden.**
* **P2**, deleting the file's parseability: **KILLED, two cells**, both in
  `tests/test_suite_profile.py`.

That pair measures the guard's **reach**: `GUARDED_DIRECTORIES = ("tests",
"meta/profiling")` is live, but it guards **parseability and host-state silences,
not figures**. `git hash-object` on the restored probe equals the pre-mutation
copy, so what is committed is byte-identical to what was gated.

### Pre-gate

`-o addopts=''` throughout (never a bare `-q`), `NONOGRAM_TEST_HANG_SECONDS` and
`NONOGRAM_FULL_SUITE_LOCK` **unset for the whole round**, the board's lock never
taken and absent, full suite **not** run.

| | the two changed files TOGETHER | derived blast radius |
|---|---|---|
| collected | **542** (132 + 410) | **2325** (zsh array length 29) |
| passed / skipped / failed | **542 / 0 / 0** | **2310 / 15 / 0** |
| exit | 0 | 0 |
| wall | 122.62 s | 308.46 s |
| load, rival-pytest | 5.02 → 3.96, 0 / 0 | 3.96 → 8.03, 0 / 0 |

Skips by name: row 1 none; row 2 **14 ×** `conftest.py:207` and **1 ×**
`test_book_pdf_memory.py:1296` — the two baseline shapes. No test reached the
120 s ceiling: both rows ended with a summary line and exit 0, which the guard's
`_exit()` forbids. Confirmation re-run at the committed revision: 542 collected,
**542 passed**, exit 0, 131.51 s.

Running the two files together matters for a second reason beyond §7.1's
precedent: `meta/profiling` is inside `GUARDED_DIRECTORIES`, so that row is the
one that judges the probe edit.

## [CYCLE 2 — 2026-10-27] **7.0, NOT CERTIFIED**, 2 gating — and one of them is the orchestrator's

`meta/review/20261027T185852Z-CARD-292-cycle2.yml`, reviewed `db0e1a3e`.
**Eight of cycle 1's ten findings are closed and verified.** The reviewer's own
summary of the distance: one prose fix round, *"with F-201 and F-202 closed,
AC-6 is met and this is a 9."*

### F-201 (gating) — the replacement instrument is blind, and the fix was the ORCHESTRATOR's

`pgrep -f 'bin/python -m pytest' | wc -l` **cannot see a venv-launched pytest on
this box.** The venv's python is a macOS **framework** python: it re-execs
through `Python.app`, so a live run's argv is
`/Library/Frameworks/…/Python.app/Contents/MacOS/Python -m pytest …` and the
literal `bin/python` **never appears**. Re-measured by the orchestrator rather
than taken — a real venv pytest launched and sampled while alive:

| instrument | pytest running | idle |
|---|---|---|
| `pgrep -f 'bin/python -m pytest' \| wc -l` | **0** | 0 |
| `pgrep -f 'm pytest' \| wc -l` | **1** | 0 |

**This was the orchestrator's correction, at `d61f0be1`, and it was worse than
what it replaced.** `pgrep -fc` failed **loudly** (exit 2, usage line, empty
cell). Its replacement never errors and always reads 0 — a blind instrument that
looks like a working one. Every `rival-pytest: 0` cell recorded in this session,
including **CARD-296's pre-check and merge gate**, came from it; the values were
correct only because nothing was in fact running, which was confirmed separately
by `ps` at the time.

The round's newly added **positive control** is the casualty: *"1 taken
deliberately while §8.2's own run was in flight … the cell can rise, and it
rose"* is a reading that command **cannot have produced here**. The reviewer
could not establish whether it came from a different command or a differently
launched pytest — *the same shape as the §8 cell the round had just withdrawn*.

**Fixed on main in this commit, and this time with a truth table.** Four cases
measured, including the control that started all of this — a `zsh -c` whose own
argv mentions pytest:

| instrument | (d) wrapper only | (a) `-m pytest` | (b) console script | (c) idle |
|---|---|---|---|---|
| `pgrep -f 'pytest'` | **1 ← false positive** | 1 | 1 | 0 |
| `pgrep -fi 'python.*pytest'` | **1 ← false positive** | 1 | 1 | 0 |
| **`pgrep -f 'MacOS/Python.*pytest'`** | **0** | **1** | **1** | **0** |

Only the third passes all four, and it is now what `meta/kanban/config.yml`
prescribes, with its bound declared: it keys on the framework re-exec path, so a
non-framework venv would read 0 and be blind again. **The lesson that
generalises**: an instrument needs a **positive** control (it must rise) *and* a
**negative** one (it must not rise on the wrapper). A cell reading 0 because the
box is quiet and a cell reading 0 because the command is blind are identical from
the figure alone. §6 must be re-extracted after this commit.

### F-202 (gating) — the right counts, the wrong domain

The round's own F-005 correction ships a **wrong attribution** into a standing
docstring: **all 108** analyses of the dear test are over planted
~389,000-character texts, **none** is over the real module, and the 0–2 group's
texts are **not small** — the discriminator is the removed door arm, not text
size. *Counts exactly right, attribution wrong*, which is the same class as the
defect it was fixing.

### The 8.2× vs 8.0× conflict — resolved, and cycle 1 was the loose one

**Fix round 1 is right; cycle 1 was under-sampled rather than wrong.** Cycle 1
took **one** pair (8.18× → "8.2×"); the fix took three back to back
(8.11/8.02/8.04); the reviewer took three of its own in a fresh process —
**8.083 / 8.291 / 7.688, mean 8.010×** — a spread that straddles both published
figures and settles it. The two percentages are **two different quantities with
two different doors**, now both named: **87.7 %** is the split's share *by
difference* between unprofiled arms (reviewer measured 87.5 %); **80 %** was
cycle 1's cProfile *cumtime* share (reviewer measured 77.7 % cumtime / 73.7 %
tottime). And the withdrawal's load-bearing half is confirmed: the **profiled**
memoised arm is **0.7415 s**, nowhere near the published 0.2864 s — so the
original pair really did divide a profiled arm by an unprofiled one.

### The declarations, tested rather than read

- **The AST-equality claim is TRUE**, re-derived independently: sources differ by
  1,696 characters, 109 docstrings stripped each side, dumps byte-identical. The
  reviewer checked the one hole — the file parses *itself* at 4740/4817 — and
  confirmed both walks are structural and assert no `lineno`, so an
  attribute-free dump is the right control. **The strongest claim in the round.**
- **P1 survives as declared**, and its stated consequence is real (44,972,712
  bytes printed under a label saying characters). Judged **acceptable as a
  declared bound** — but with a remark worth keeping: *the bound's price was paid
  in the same round that declared it*, because F-201 and F-202 are both exactly
  the failure it permits. It earns no credit beyond honesty.
- **P2 killed in both named cells**, and the reviewer **disclosed its own slip**:
  its first attempt `sed`'d the wrong line, so nothing was planted and both cells
  passed **vacuously**; re-fired correctly. That disclosure is the difference
  between a kill matrix and a decoration.
- **Edge mutants on P2's claim**: the same syntax error in an **untracked** `.py`
  under `meta/profiling/` is **NOT caught**; in a **different tracked** probe it
  **is**. The door is `git ls-files`, and the ceiling probe's own comment already
  states that boundary.
- **M10 survives** because its cell calls `_source_segment` **directly** and
  never goes through the hot site — which is exactly the hole F-008 declares.

### F-008's decline — accepted

*"A declared bound, not a hole wearing a declaration."* Both of its reasons are
mechanically true, the consequence is proved by M1 and M10, and the two cold
sites a control would have to discriminate (**1438**, **2913**) are verified to
be the only remaining ones. **Only the owner is missing** → **F-203**: the
declared bound names "the obvious successor card" and there is no card and no
backlog entry, so **nothing owes the control**. Also **F-204**: the unit fix
missed `# (path, seconds, nbytes)` at `card292_plant_reads.py:59`.

### Procedure

Full suite **not** run; the board's lock never taken and absent; **no env
overrides at all** — the reviewer fired M10 against cells costing seconds rather
than cycle 1's 105 s arm. All output under `-o addopts=''`, skips attributed with
`-rs`, node ids throughout.

## [FIX ROUND 2 — 2026-10-27] `59e7b58a` — both gating closed, AC-6 met, and the reviewed HEAD was RED

### It refused the reviewer's remedy, and was right to

Cycle 2 prescribed `pgrep -f 'm pytest' | wc -l`. The fix round **measured it
first** and found it a **false positive** on a `zsh -c` wrapper, so it used the
verified form instead and said so in the document. The orchestrator re-measured
both: on a wrapper with **no pytest running**, cycle 2's remedy reads **1** and
the prescribed form reads **0**. *A fix that copies a reviewer's prescription
without measuring it is how this board loses rounds; this one did not.*

### F-201 — closed, with five cases and a new column that indicts the orchestrator

It added case **(d2)** — a `zsh -c` whose argv spells `.venv/bin/python -m
pytest` — and that column settles what the orchestrator's "fix" really was:

| instrument | (c) idle | (d) wrapper says *python -m pytest* | (d2) wrapper says *.venv/bin/python -m pytest* | (a) `-m pytest` | (b) console |
|---|---|---|---|---|---|
| `pgrep -f 'pytest'` | 0 | 1 FP | 1 FP | 1 | 1 |
| `pgrep -fi 'python.*pytest'` | 0 | 1 FP | 1 FP | 1 | 1 |
| `pgrep -f 'm pytest'` (cycle 2's remedy) | 0 | **1 FP** | 1 FP | 1 | **0 FN** |
| `pgrep -f 'bin/python -m pytest'` (the orchestrator's) | 0 | 0 | **1 FP** | **0 FN** | **0 FN** |
| **`pgrep -f 'MacOS/Python.*pytest'`** | **0** | **0** | **0** | **1** | **1** |

**Row 4 is wrong in BOTH directions** — 1 when nothing is running, 0 when
something is. *The exact inverse of an instrument.* Re-measured by the
orchestrator and now carried in `meta/kanban/config.yml`'s own table.

**The positive control is a trace that exists.** Taken inside the pre-gate script
itself, 30 s into §8.2's **own row 1** (pid 28140, alive) and again 60 s into row
2, with the literal output in the document: prescribed command **= 1**, the blind
form **= 0**, beside the live process's real argv. The **negative** control sits
next to it: idle box, wrapper alive, prescribed **0**, blind form **1**. An
instrument that can only rise is half a control; this one is shown to rise *and*
to stay down.

**§6 re-extracted programmatically** from `bd2128b5`, blob
`4a03afc785ab59c8d1e52afb89d145022c0a1248`, identical at `e4d33dfa` and main's
head, both named; 90 lines each side, **diff empty**, equal sha256. **Class
audit:** 18 mentions of a defective form survive and **none prescribes one** —
each is a `**Not** X`, a *REJECTED FORMS* row, a withdrawal trace, or a
truth-table row showing it fail. Both probes contain **no host instrument at
all**, so they could not have carried the defect.

### AC-6 — MET

The deciding cell is §8.2's `rival-pytest, start / end`. It holds because a **1
was reachable on the very command that produced the 0s**, shown twice in the same
script, and **unreachable** on a wrapper that merely mentions pytest. Cycle 2's
reason for NOT MET was exactly that a cell reading 0-quiet and 0-blind is not a
measurement; that is now excluded **in both directions**.

### F-202 — closed through a different door than the one that got it wrong

Re-measured with a wrapper capturing `_page_positions`' own `source` and
`door_arms` arguments — not the call counter that produced the bad attribution.
All 108 analyses are over **planted** texts (32 distinct lengths,
389,122–389,385 chars); **0** have `source is None`; **0** equal the real
module's text. It went further than cycle 2 and resolved the discriminator
exactly: the **36** expensive analyses all carry `door_arms=('callee identity',)`;
the **72** cheap ones are 36 × `('door spelling',)` + 36 × `()`. Decisive on the
real module too — **716** calls with that arm, **0** without.

### NEW, AND THE MOST IMPORTANT THING IN THE ROUND: the reviewed HEAD was RED

Row 2's first run returned **1 failed / 2309 passed / 15 skipped, exit 1**.
`tests/test_full_suite_lock.py::test_nothing_in_the_tree_sets_either_of_the_guards_env_switches`
scans the **whole tree** with `git grep` for the full-suite guard's two env
switch names, exempting `tests/README.md`, the guard, its own file, and prose
under `meta/kanban/cards/` and `meta/review/`. **`meta/profiling/` is not
exempt** — and **fix round 1's own "Procedure" paragraph spelled both names**,
written *after* its rows were taken. Attribution is exact: `git grep -l … 98482d2c`
has no `meta/profiling` entry, `… db0e1a3e` does, and `git log -S` names
`db0e1a3e`.

**Cycle 2 could not have caught it, because it carried row 2 forward instead of
re-running it.** So review cycle 2 scored a tree that was red on its own declared
blast radius. Fix round 1's safety argument — *"not a `*.py`, so outside
`_guarded_sources`"* — was true of **one** guard; the tree has another.

**Fixed by not naming the switches.** Widening that guard's exempt prefixes was
the alternative and is **G-1's shape** — a guard relaxed to admit the thing that
tripped it.

### Pre-gate

| cell | row 1 (two changed files together) | row 2 (derived blast radius) |
|---|---|---|
| collected | **542** (132 + 410) | **2325** (zsh array length 29) |
| passed / skipped / failed | **542 / 0 / 0** | **2310 / 15 / 0** |
| exit / summary lines | 0 / **1** | 0 / **1** |
| wall | 126.74 s | 295.69 s |
| load start → end | 5.26 → 4.58 | 4.58 → 10.16 |
| rival-pytest start / end | **0 / 0** | **0 / 0** |
| same cell, in flight | **1** (blind form 0) | **1** (blind form 0) |
| at/over the 120 s ceiling | 0 | 0 |

Skips by name: row 1 **none**; row 2 = **14 ×** `conftest.py:207` and **1 ×**
`test_book_pdf_memory.py:1296`. **A third run was taken after the last
substantive document edit** — *this round's own lesson applied to itself* —
2310 / 15 / 0, exit 0, 288.37 s. Against the **committed** text the three
tree-reading cells re-ran **3 passed in 21.42 s**, and
`git grep … 59e7b58a -- meta/profiling` is clean.

### Behaviour

**Prose only, proved.** `tests/test_book_export_interior_cover.py`:
docstring-stripped `ast.dump` byte-identical at `db0e1a3e` and HEAD (109
docstrings each side, `dump_sha cacfd93827a6d51cb1daf580` both) while sources
differ by **610** characters. `tests/test_suite_profile.py` and
`card292_ceiling_probe.py` byte-identical. The one non-prose delta is a
**write-only** loop variable in the probe: the full `ast.dump` differs in exactly
one token (`id='nbytes'`→`id='nchars'`), the name has **no `Load` occurrence**
anywhere, and re-running the probe reprints 216 reads / 2 paths / 44,824,752
characters — a **third** independent reading inside the declared band. **This
round adds no mechanism, so there is no mutant to plant — stated, not invented.**

`NONOGRAM_TEST_HANG_SECONDS` and `NONOGRAM_FULL_SUITE_LOCK` **unset** for every
run and printed from the environment before the first test; the board's lock
never taken and absent; full suite **not** run.

### Could not establish, in those words

Whether any cell **other** than the full-suite-lock one among the 29 files reads
a `.md` path — the reach of the guard that bit is measured, the absence of a
second is not, and it is declared as a bound rather than claimed. Where fix round
1's claimed positive-control `1` came from — unchanged from cycle 2, and the
paragraph is **replaced by a trace actually taken** rather than defended. Whether
the prescribed pattern works on a **non-framework** venv.

## [CYCLE 3 — 2026-10-27] **CERTIFIED, 8.5**, zero gating

`meta/review/20261027T204514Z-CARD-292-cycle3.yml`, reviewed `59e7b58a`. The last
cycle of three. **Both of cycle 2's gating findings are closed, and each was
re-derived through a door the card did not use.** AC-1..AC-6 **all MET**,
G-1..G-7 **all MET**.

### AC-6 is MET, established rather than read

Deciding cell: §8.2's `rival-pytest, start / end` through
`pgrep -f 'MacOS/Python.*pytest' | wc -l`. The reviewer did not read the card's
trace — it took its own: the cell **rises** (1 at t=40 s and t=140 s inside its
own blast-radius run, live argv and pid printed) while the blind form read **0
throughout a 321 s pytest**, and it **stays down** (0 on three distinct `zsh -c`
wrappers, including one spelling `.venv/bin/python -m pytest`, which makes the
predecessor read 1). **So a 0 from that cell is now informative**, which is
exactly what cycles 1 and 2 said it was not.

### The blast radius was RE-RUN, not carried — and it is green

**2310 passed / 15 skipped / 0 failed**, collected 2325, exit 0, one summary
line, 321.22 s, load 9.41 → 10.21. Skips by name: **14 ×** `conftest.py:207`,
**1 ×** `test_book_pdf_memory.py:1296`. Zero at or over the 120 s ceiling,
derived from §1.1's **kill signature** (exit 1 + zero summary lines) rather than
from a timer. Switch-name attribution exact in all three directions: absent
`98482d2c`, present `db0e1a3e`, gone `59e7b58a`, and all 54 remaining tracked
namers at HEAD are exempt.

### The declared bound is CLOSED by enumeration

Fix round 2 could not establish whether any cell other than the full-suite-lock
one reads a `.md` path. **Exactly one does**, and it is the one that bit:
`test_nothing_in_the_tree_sets_either_of_the_guards_env_switches` runs
`["git","grep","-l",…]` with **no pathspec at all**, exempting three exact paths
plus `.md`/`.yml` under `meta/kanban/cards/` and `meta/review/`. Two further
cells touch `meta/profiling/` non-`.py` files **by name only** —
`_tracked_under_guard` returns every tracked path but `_guarded_sources` filters
`.endswith(".py")`, and its one unfiltered consumer **symlinks** rather than
reads. **Nothing globs `*.md`.** So that selection is sensitive to
`meta/profiling/` for **two tokens of text and the set of paths** — nothing else.

### The §6 ruling, which went against the orchestrator on a narrower charge

The orchestrator disclosed that it had changed `config.yml` *after* fix round 2
snapshotted §6 from `bd2128b5`. **The reviewer declined the broad charge and
found a narrow one**, having measured first: §6 is verbatim at the commit it
names (`diff` empty, sha256 equal to the digest the document publishes, blob
identical at `bd2128b5` and `e4d33dfa`), and *"holding a committed artefact to
track a sibling file a different agent edits afterwards is a rule no card could
satisfy."* What it found against is **one clause written in the present tense
about a thing the card does not own** — *"and is unchanged at `main`'s head"* —
true when written, **false at the revision this card merges into**. **F-301,
minor.** **F-302**, also minor: §7's (d) column reproduces only for a wrapper the
document never shows, and §6's snapshot labels a different one.

### F-303 — a cell of the ORCHESTRATOR's own table did not reproduce

Cycle 2's remedy `pgrep -f 'm pytest'` is also a **false NEGATIVE** on the
`.venv/bin/pytest` console-script launch: it reads **0**, because that argv holds
`bin/pytest` and never ` -m pytest`. `meta/kanban/config.yml` and this card both
recorded **1**. Re-measured and corrected in this commit. **The orchestrator had
measured that 0 an hour earlier in the same session and transcribed a 1** — which
is precisely why the table exists, and it makes cycle 2's remedy wrong in **both**
directions, strengthening the fix round's refusal of it.

### Things the review strengthened rather than accepted

* **AST equality, with a control the round lacked**: instead of only deleting
  docstrings, it **canonicalised** them — identical dumps, **18,620** nodes
  identical, **1,685** non-docstring constants identical, and **exactly one
  docstring changed** (`TestSourceSegment_TheMemoIsTheStdlibAnswer`, line 6322 —
  F-202's own correction). Door disclosed: its absolute `dump_len` differs from
  the card's by 30 characters, a method difference, identity being the claim.
* **"Write-only" verified, not accepted**: `nchars` occurs once with ctx `Store`,
  **0** `Load`, and `nbytes` is gone from the file — so F-204 really is fixed as
  a class.
* **F-202 closed through a THIRD door, statically**: 36 `DOOR_SHAPES` × 2
  `DOOR_ARMS` removed singly + 36 with `door_arms=()` = **108**, each routed
  through `_plant`, which returns `source.replace(DERIVED_POSITION, body) + extra`
  after asserting a 3-line body — so `source` is never `None` and never the
  unmodified module **by construction**, not by sampling.
* **Mutation**: the round adds no mechanism and that is **true**, but two cells
  were re-fired anyway. **P2′** (unbalanced `(` on the line fix round 2 actually
  changed) kills both named cells separately. **M-SW** — one guard switch *name*
  planted in a tracked `meta/profiling` file — reds exactly
  `test_full_suite_lock.py:614` with the assertion the card quotes. Both restored
  with `git hash-object` equal to the tracked blob, and **no env switch was set
  anywhere** in the review.

### Could not establish, in those words

Whether the card's trace pids **28140 / 28719** were the processes claimed — *a
past pid leaves no instrument* — though the same control on the reviewer's own
pids gives the same readings and argv shape, and the card is **not charged** for
the gap. Whether the prescribed pattern works on a **non-framework** venv (it
would not, by the mechanism, and the document declares that bound). The
provenance of §8's withdrawn `0 / 0`, unchanged. Why the stripped dump lengths
differ by 30 characters.

### What the merge gate owes

Re-derive **2325** at the merge commit; **run the full suite**; re-check
`git grep -l` for the two switch names on the **merged** tree — one command, and
the one this card has now paid for twice. F-301/F-302 are two one-line prose
edits; F-303 and F-305 are the orchestrator's. **CARD-302 still owes F-008's
control.**

## [MERGED — 2026-10-27] `714de66e` — and the gate confirmed the card's own figure

**Merge gate: 9378 passed, 27 skipped, 0 failed, 0 errors, 1270.34 s (21:10).**
Host cells through the verified instrument: load **7.59 → 7.85**, rival-pytest
**0 → 0**. Both skips attributed by name (26 × `conftest.py:207`, 1 ×
`test_book_pdf_memory.py:1296`); **27 is the baseline exactly**. The
switch-name scan on the **merged** tree — the check this card paid for twice —
returns 57 files, every one inside the guard's exempt prefixes, **nothing under
`meta/profiling/`**.

### The suite-level confirmation, which is a different domain from the claim

| gate | wall | collected |
|---|---|---|
| CARD-296, taken on this box **before** the cheapening | **1670.57 s** | 9368 passed / 27 skipped |
| CARD-292, **after** | **1270.34 s** | 9378 passed / 27 skipped |

**400.23 s faster, 24.0 %, on ten *more* tests.** The card measured its saving at
the **file** level as 511.43 → 104.12 = **407.31 s**; the **suite** delta is
**400.23 s**. They agree to **7.08 s, 1.7 %**. A figure measured on one file and
re-measured as a whole-suite wall clock is exactly the cross-domain agreement
this card spent three cycles learning to demand of itself — and the +10 matches
AC-5's audited `removals 0, additions 10`.

### What was unmet or uncertified at merge, stated

- **F-301 and F-302 shipped UNCERTIFIED.** `max_cycles` was spent, so no reviewer
  saw them. Both are prose in the document, neither adds or changes a mechanism
  or an assertion, and `tests/`/`src/` are **byte-identical** to the certified
  revision `59e7b58a` — so cycle 3's AST-equality verdict holds by construction.
- **F-303 and F-305 were the orchestrator's**, both fixed on main before the
  merge: a mis-transcribed cell in the board's own truth table, and CARD-302
  missing from the board.
- **CARD-302 owns the one declared bound.** The memo's *existence* is guarded;
  its *use at the hot call site* is not, so this file can return to ~113 s with
  **no cell firing** — 7 s under the ceiling this card existed to clear.
- **Three "could not establish" items stand**, unchanged and recorded: the
  provenance of §8's withdrawn `0 / 0`; whether the prescribed instrument works
  on a non-framework venv (by its mechanism it would not, and the bound is
  declared); and whether fix round 1's claimed positive-control `1` was ever
  taken — *a past pid leaves no instrument*.

### Why this card was worth three cycles

It was dispatched to measure an unknown ceiling and found the ceiling was
**never unknown**: `tests/hang_guard.py`, armed per test with `exit=True`, hidden
because `addopts = "-q"` suppresses the header line that announces it. CARD-097
wrote it; four waves rediscovered it from its symptoms. The stack dump the board
needed was being written to `$TMPDIR` the whole time. A **second** 120 s limit
lives outside the tree, in the agent shell's own default timeout — which is what
CARD-276 attributed to a card's diff **twice**.

And the mechanism it was dispatched to confirm was **refuted arithmetically**: a
page-cache story has two cold reads to pay for, at 3.1 ms, and cannot buy 22 s.
The real cost was `ast.get_source_segment` re-splitting a prefix of the source on
every call. The headline 9.9× was a **profiled numerator over an unprofiled
denominator**; through one door it is **8.0×** unprofiled and **4.05×** with both
arms profiled.

**The pattern worth keeping.** Three consecutive rounds produced an instrument
defect on a card whose subject is measurement — `pgrep -fc` (not a flag on this
platform), the orchestrator's `pgrep -f 'bin/python -m pytest'` (blind *and*
false-positive — wrong in both directions), and a positive-control reading no
command could have produced. What finally closed it was not a better pattern but
a **truth table with both controls**: an instrument must be shown to **rise** and
to **stay down**, because a cell reading 0 because the box is quiet and a cell
reading 0 because the command is blind are identical from the figure alone.
