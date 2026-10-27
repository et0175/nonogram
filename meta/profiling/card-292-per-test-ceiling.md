# CARD-292 — the per-test ceiling, measured

**Taken 2026-10-27** on Mac15,6 (Apple M3 Pro, 11 cores, 18 GB, macOS 26.7.1 /
Darwin 25.6.0 arm64), Python 3.14.3, pytest 9.1.1, in the worktree
`PythonProject4-card-292` on `card/292-measure-the-per-test-ceiling`, based on
`main` at `6e0aadca`. Every reading below names the instrument that took it and
the state of the host while it did.

**The headline, before the evidence.** The ~120 s boundary is real, it is a
**wall-clock per-test ceiling**, and **it is in this repository**:
`tests/hang_guard.py` arms `faulthandler.dump_traceback_later(HANG_SECONDS,
exit=True)` **per test** through a `pytest_runtest_protocol` hookwrapper, with
`HANG_SECONDS` defaulting to **120**. It was not a mystery, a harness quirk or
a coincidence of two figures: it is a guard this board wrote for CARD-097 and
then spent four waves rediscovering from its symptoms.

**And there is a SECOND, independent 120 s limit** that produces a
similar-looking truncation from outside the tree: the agent harness's own
default shell timeout, also 120 s. Both were measured. Telling them apart is
the triage rule at the end of this document.

---

## 1. The ceiling, bisected (AC-1)

### 1.1 What it is

`tests/hang_guard.py:41`

```python
HANG_SECONDS = float(os.getenv("NONOGRAM_TEST_HANG_SECONDS", "120"))
```

and `pytest_runtest_protocol` arms the alarm before each test and cancels it
after, so the bound covers **setup + call + teardown of one test**, not the
session. `faulthandler` with `exit=True` calls `_exit()` after writing the
stacks, which accounts for the whole symptom set CARD-292 was opened on:

| symptom the card recorded | what `exit=True` does |
|---|---|
| exit 1 | `_exit(1)` |
| **zero bytes** of pytest output | pytest's fd-level capture buffer is never flushed |
| `0 signals received` | it is not a signal; the process exits itself |
| `[ 57%]` + 5 dots, **no summary line** | the process dies mid-test, so no summary is ever written |
| 120.93 s / 120.98 s at two revisions, 50 ms apart | a fixed 120 s alarm plus interpreter start-up |

The guard announces itself in every run header — `hang guard: 120s per test;
stacks -> /var/folders/.../nonogram-test-hang.txt` — and that line is **hidden
by `pyproject.toml`'s `addopts = "-q"`**, which is why four rounds of
investigation never saw it. It appears as soon as a run is taken with
`-o addopts=''`.

**The stack dump the card needed was being written the whole time**, to
`$TMPDIR/nonogram-test-hang.txt`.

### 1.2 Wall clock, not CPU — and per test, not per process

Measured with `meta/profiling/card292_ceiling_probe.py` (kept out of `tests/`
per G-3, and named so `python_files` never collects it from a suite run; it
runs only when passed as an explicit path argument).

The decisive reading is that a test which **sleeps** is killed: at the kill
point the probe had accrued **0.31 s of CPU** against 120 s of wall clock.
The bound is wall clock.

### 1.3 The second limit, bisected — the agent harness's shell timeout

Same probe, same machine state, four readings minutes apart, each a shell call
with **no explicit timeout** except where stated:

| burn | shell `timeout` | outcome | load at start |
|---|---|---|---|
| 130 s | default | **cut from the foreground at 120 s** ("did not complete within its 120s timeout") | 7.62 |
| 130 s | explicit 300 s | **completed, 130.04 s** | 6.17 |
| 119 s | default | completed, 119.05 s | 5.54 |
| 121 s | default | **cut at 120 s** | — |

So the harness boundary is bracketed to **(119.6 s, 121.6 s]** of total shell
wall clock, i.e. 120 s, and the two arms of the 130 s pair differ **only** in
the `timeout` argument. This limit is per **shell invocation**: it is not
pytest's, not the tree's, and it does not move with load.

**This is what CARD-276 attributed to a card's diff twice.** A gate command
longer than two minutes, run through an agent's shell tool at its default,
returns a truncated log and a non-zero exit with no summary line — which is
exactly what a suite failure looks like.

### 1.4 The warm/cold page-cache mechanism: REFUTED

The card's standing explanation was *"inside a suite the module's 306 KB source
is in the page cache by the time this file runs, and standalone it is not;
`_plant` reads it from disk 144 times in that one test."* AC-1 asked for that
measured rather than repeated. Instrument:
`meta/profiling/card292_plant_reads.py`, which wraps `pathlib.Path.read_text`
and runs the test's body directly.

| figure | the card | **recomputed** |
|---|---|---|
| reads per run of that one test | 144 | **216** (108 × `book_pdf_generator.py`, 108 × `book_page_spec.py`) |
| module size | 306 KB | **389,177 bytes (380 KB)** |
| bytes read in the test | — | **44.8 MB** |
| **seconds spent inside `read_text`** | the whole mechanism | **0.0416 s — 0.039 % of the test's 107.19 s** |
| of which the first read of each path (the only ones that *can* be cold) | — | **0.0031 s** |

The refutation is not just the share, it is arithmetic: the first read of a path
**populates the page cache itself**, so a page-cache story has exactly **two**
reads to pay for out of 216. A cold cache cannot buy 22 s out of 3.1 ms.

**What the cost actually is**, by `cProfile` through the same door: of the
**2.8429 s** one `_page_positions` analysis took, **2.557 s (90 %)** was
`ast.get_source_segment` → `ast._splitlines_no_ff`, which **re-splits the whole
source with a regex on every call** — 675 calls per analysis over a 380 KB
module. The cost was quadratic in the module's size by construction, and it had
nothing to do with the disk.

### 1.5 The 4.61 → 11.74 load jump: still NOT attributed

The card recorded, with its mechanism open, that the 1-minute load average went
4.61 → 11.74 across the minute a single-core pytest started. **This card did
not close that question and does not claim to.** What it did establish is the
corrected premise: with **no pytest running at all** the 1-minute load average
on this box was observed between **4.17 and 10.02** across this card's own
readings (and the 15-minute figure as high as 14.37) (`vm.loadavg` recorded at both ends of every arm above). A load average
here is not a proxy for test contention, and the collection-I/O reading remains
a hypothesis without a measurement.

---

## 2. The suite's distribution against the ceiling (AC-2)

Derived by parsing `meta/profiling/suite-durations-20261023.txt` with
`meta/profiling/rank_durations.py`'s own `parse_artefact`, summing **all three
phases** per node id (because the guard's alarm wraps the whole protocol), and
keeping every test at or above **50 % of the ceiling = 60.00 s**.

**Every test within 50 % of the ceiling — two, and both in one class of one
file:**

| summed | file | test |
|---|---|---|
| **81.03 s** | `tests/test_book_export_interior_cover.py` | `TestBookPdfStructure_NoPositionCountsTheGuideWithoutTheTitlePage::test_each_door_axis_arm_catches_a_shape_the_other_misses` |
| **67.08 s** | `tests/test_book_export_interior_cover.py` | `TestBookPdfStructure_NoPositionCountsTheGuideWithoutTheTitlePage::test_every_door_shape_is_read_or_refused_and_never_silent` |

The next test down is `tests/test_kill_matrix.py::test_ac7_the_four_arm_grid_of_card_257_reproduces`
at **56.92 s**; it joins the list at a 47 % threshold.

**The domain of those two figures, which is part of them.** The artefact is of
commit `ae164099`, 2026-10-23, **before** CARD-276 grew that file from 90
collected tests to 127. Both rows are therefore **understatements** of today's
cost, and this card re-measured the dearer of them directly (§3) rather than
scaling the figure.

**The standing guard** is `tests/test_suite_profile.py::TestSuiteCeiling_TheCliffEdgeListIsDerived`:
the ceiling is read off `tests/hang_guard.py`'s **default literal by AST** (not
by import — `HANG_SECONDS` honours an environment variable, and this card's own
measurements set it to 0), the threshold is derived from it, and the frozen list
is asserted **equal** to a live derivation. Per G-2 no host figure is asserted:
what is pinned is the derivation and the list, not a duration.

---

## 3. The over-the-line test, cheapened (AC-3, AC-4)

### 3.1 The change

`segment()` inside `_page_positions` called `ast.get_source_segment`, which
re-splits the source per call. It now calls a module-level `_source_segment`
over a **memoised** line split (`_source_lines`, 8 entries). The slicing
arithmetic is unchanged and is held to the stdlib's answer by
`TestSourceSegment_TheMemoIsTheStdlibAnswer`.

Per analysis of the real module: **2.8429 s → 0.2864 s (9.9×)**, `cProfile`,
same process, same host.

### 3.2 The test, A/B/A/B interleaved under one machine state (G-7)

Each arm placed by sha and re-read before running; the hang guard set to 0 for
these four readings **so the before arm reports its cost instead of its kill
time** — the measurement nobody had taken, because under the shipped guard the
before arm can only ever report "≥ 120".

| round | arm | placed sha | **duration** | load at start |
|---|---|---|---|---|
| 1 | before | `2195845319532c61` | **113.02 s** | 6.26 |
| 1 | after | `94b224039c48ad98` | **32.02 s** | 21.55 |
| 2 | before | `2195845319532c61` | **111.67 s** | 24.78 |
| 2 | after | `94b224039c48ad98` | **30.44 s** | 21.17 |

`test_each_door_axis_arm_catches_a_shape_the_other_misses`:
**113.02 / 111.67 s → 32.02 / 30.44 s**, a **3.6×** reduction, and from **7 s
under the 120 s ceiling to 88 s under it**.

Within-arm reproducibility was 1.35 s (before) and 1.58 s (after) across a
machine state whose 1-minute load average moved 6.26 → 24.78 **while the before
arm moved only 1.35 s**, which is itself a datum: this test is CPU-bound on one
core and is far less load-sensitive than the card assumed.

**A fifth broken comparison, recorded because the method error is this card's
subject.** The card's "~99 s warm against ~121 s cold, straddling a ceiling
near 120 s" compares a **cost** with a **kill time**. 120.93 s is not what the
test took; it is where it was stopped. Nothing was known about its standalone
cost until the table above, and the real standalone figure is **113 s** — under
the ceiling, not over it.

### 3.3 AC-4: the four equalities, re-derived

Node id unchanged; the test still asserts all four, and all four figures
recomputed through the test module's own constants:

| equality | figure |
|---|---|
| `SILENT_WITHOUT_ONE_ARM["callee identity"]` | **23** |
| `SILENT_WITHOUT_ONE_ARM["door spelling"]` | **1** |
| `SILENT_WITHOUT_THE_DOOR_ARMS` (both arms off) | **30** |
| `kept` | **6** |
| (`DOOR_SHAPES` rows, for the arithmetic) | 36 |

---

## 4. The triage rule this buys (AC-6)

A red gate on this board has four candidate causes, and they are now
distinguishable in seconds rather than in an hour:

1. **A test hit the 120 s per-test ceiling.** Signature: exit 1, **no summary
   line**, no failure cells, and a fresh stack dump in
   `$TMPDIR/nonogram-test-hang.txt`. Read that file; it names the test. Re-run
   with `-o addopts=''` and the header will state the bound.
2. **The shell call hit the harness's 120 s timeout.** Signature: a truncated
   log, no summary line, and the harness's own message. Re-run with an explicit
   timeout (600 s maximum for a foreground call) or in the background.
3. **A rival pytest.** Signature: `ps -Ao command | grep -c '[m] pytest'` > 1 at
   either end of the run. This — **not** the load average — is what "quiet"
   means on this box, and `meta/kanban/.full-suite.lock` with CARD-255's
   foreign-holder guard is the only thing that enforces it.
4. **The tree.** Everything else, and it has **failure cells**. An exit code is
   not a verdict.

The convention that makes a gate row answer 1–3 is in `meta/kanban/config.yml`
under `test_command`, and is reproduced here verbatim so it outlives this
worktree — **see §6**.

---

## 5. What this card did NOT establish

* **The 4.61 → 11.74 load jump is still unattributed** (§1.5). The
  collection-I/O reading is a hypothesis with no measurement behind it.
* **The warm/cold gap is now measured and it is small.** Same revision, same
  machine state, back to back: **108.07 s in the whole file** (§7) against
  **113.02 / 111.67 s standalone** (§3.2) — **3-5 %**, not the ~18 % the card's
  "99 s warm against 121 s cold" implied, and the 121 s half of that pair was a
  kill time rather than a cost. **What causes the remaining 3-5 % is not
  established**; it is too small to matter against a 7 s margin, and a
  page-cache explanation is refuted (§1.4).
* **No mutant separated the two equivalence controls.** All three slicing
  deletions are killed by the seeded corpus **and** by the exhaustive
  small-source sweep. The draft docstring claimed the small sources caught what
  the corpus could not; that claim was **false** (the module is not all-ASCII)
  and has been narrowed in the test itself.
* **One surviving mutant, reported rather than hidden:** truncating
  `_source_lines`' result by its last element changes nothing either control
  sees, because the line regex's `$` alternative appends a final empty match
  that no node's `end_lineno` indexes. The last element of the split is dead,
  by construction of the pattern rather than by an untested path.
* **The claimed 1.7× spread between two "uncontended" whole-file runs IS
  resolved, and it was never a host spread** — see §7.2. The 467.30 s figure
  reproduces at 511.43 s (9.4 %, inside the ~19 % `tests/README.md` quotes);
  the ~270 s was a linear extrapolation from one `56 %` progress reading, and
  linear extrapolation is invalid on this file because 2 of its 127 tests hold
  38.9 % of its time. What remains unestablished is the **cause** of the 9.4 %
  between the two timed runs, which is ordinary host variance as far as this
  card can tell and was not chased further.

---

## 6. The AC-6 convention, verbatim

Two cards this wave nearly lost a review artefact that existed only as an
untracked file in a worktree scheduled for deletion. This block lives in
`meta/kanban/config.yml` under `test_command` — which is **board-side state, so
it is not committed on this card's branch** — and is reproduced here so it
survives the worktree.

```yaml
  # HOW A GATE RECORDS THE HOST (CARD-292 / AC-6, owner-facing convention).
  # A gate that reds under contention and greens idle is not a verdict about
  # the tree, and this board has argued about four such verdicts (CARD-218's
  # 101 skips, CARD-271's Page.goto, CARD-276's six identical deaths,
  # CARD-283's main-was-red). Every gate row therefore carries THREE host
  # cells, written into the gate's own output file BEFORE the first test runs
  # and again after the last:
  #
  #   load-start / load-end   `sysctl -n vm.loadavg`, both ends.
  #   rival-pytest            `pgrep -fc 'bin/python -m pytest'`, both ends.
  #                           THIS is the cell that decides whether the run was
  #                           quiet; the load averages are context. NOT
  #                           `ps -Ao command | grep -c '[m] pytest'`, which was
  #                           the idiom in use and which counts THIS AGENT'S OWN
  #                           `zsh -c` wrapper lines: measured 2026-10-27 it
  #                           returns 2 with no pytest running at all, so its
  #                           baseline moves with the shape of the command that
  #                           asks. pgrep counts processes and returns 0.
  #   per-test ceiling        whether any test's SUMMED setup+call+teardown
  #                           reached tests/hang_guard.py's HANG_SECONDS
  #                           (120 s), and the dearest test's figure.
  #
  # WHY rival-pytest AND NOT THE LOAD AVERAGE, measured on this box 2026-10-26
  # and re-derived 2026-10-27: with NO pytest running at all the 1-minute load
  # average here is 4.6-14.4 -- it is the owner's desktop (WindowServer,
  # IntelliJ, Chrome, a video decode), which the board does not get to
  # schedule. "Wait for a quiet box" was therefore waiting for something that
  # never arrives, and it held CARD-292 for a whole wave. The operative
  # definition of quiet is NO RIVAL PYTEST, which meta/kanban/.full-suite.lock
  # and CARD-255's foreign-holder guard already enforce and which nothing else
  # enforces.
  #
  # AND THE ONE THAT COST THE MOST: a gate command run through an agent's
  # shell tool inherits that tool's own wall-clock timeout, 120 s by default
  # on this harness. A run cut there returns a truncated log and a non-zero
  # exit with NO summary line -- indistinguishable from a suite failure, and
  # the thing CARD-276 attributed to a card's diff twice. Any gate invocation
  # longer than two minutes must pass an explicit timeout (600 s is this
  # harness's maximum for a foreground call) or run in the background. A gate
  # row with no summary line is a MEASUREMENT defect, never a tree verdict.
```

**AC-6's instance in this card's own gate** is §7's whole-file table: both load
averages, the rival-pytest count at both ends, and the per-test ceiling cell.

---

## 7. The whole file, both arms, one machine state (AC-3, AC-6's instance)

A single-file run, so no suite lock was required. `rival-pytest` below was
taken with the idiom this board had been using,
`ps -Ao command | grep -c '[m] pytest'`, where **1** is the probe's own
`zsh -c` wrapper line and **>1** would mean a rival — **and that instrument is
defective**, which this card found by using it: the same command returned
**2** with no pytest running at all later the same day, because it counts the
agent's own shell wrapper lines and their number depends on the shape of the
command that asks. `pgrep -fc 'bin/python -m pytest'` counts processes and
returned **0** on the same box in the same minute. The convention in §6 now
names pgrep. **The 1 / 1 cells below are therefore evidence that no rival
pytest ran only in the weaker sense that the count did not rise** — the two
arms were taken back to back by one script that ran nothing else, which is the
stronger argument for them.

| cell | **before** | **after** |
|---|---|---|
| placed sha (first 16) | `2195845319532c61` | `2117d8771b2bcb94` |
| collected | 127 | **132** |
| passed / skipped / failed | 127 / 0 / 0 | 132 / 0 / 0 |
| pytest exit | 0 | 0 |
| **pytest wall clock** | **511.43 s** | **104.12 s** |
| `/usr/bin/time` real / user / sys | 512.14 / 499.62 / 4.65 | 105.06 / 101.46 / 1.45 |
| load at start → end | 8.98 → 11.03 | 11.03 → 7.95 |
| **rival-pytest, start / end** | 1 / 1 | 1 / 1 |
| **tests at or over the 120 s ceiling** | **0** | **0** |
| **tests at or over 60 s (cliff edge)** | **2** | **0** |
| dearest test | **108.07 s** | **28.49 s** |

**AC-3 is met: the whole file completes with every test under the ceiling, and
nothing is left within 50 % of it.** The file went **511.43 s → 104.12 s
(4.9×) while gaining five tests**, and the two rows AC-2 derived from the
2026-10-23 artefact are the two rows that moved:

| test | before (in file) | after (in file) |
|---|---|---|
| `test_each_door_axis_arm_catches_a_shape_the_other_misses` | **108.07 s** | **28.49 s** (3.8×) |
| `test_every_door_shape_is_read_or_refused_and_never_silent` | **90.73 s** | **10.33 s** (8.8×) |

The derived cliff-edge list is therefore **reproduced live at the current
revision**, not merely parsed out of an old artefact: run the before arm today
and exactly those two tests, and no others, reach 60 s.

### 7.1 The guard is per TEST — demonstrated, not read off the source

Same probe, `-p tests.hang_guard` (the probe runs by explicit path, so
`tests/conftest.py` does not apply to it), guard at its shipped default:

| arm | shape | total wall | outcome |
|---|---|---|---|
| 1 | **3 tests of 45 s** in one process | **135.09 s** | **4 passed, exit 0** |
| 2 | **1 test of 130 s** | — | **exit 1, 446 bytes, 0 summary lines** |

Arm 1 ran **15 s over the bound in one process and nothing fired**, so the
bound is per test and not per process or per session. Arm 2 reproduced
CARD-276's symptom set exactly, and the dump it left names the test and the
line:

```
Timeout (0:02:00)!
Thread 0x00000001f515a1c0 (most recent call first):
  File ".../card292_ceiling_probe.py", line 79 in _pay
  File ".../card292_ceiling_probe.py", line 90 in test_one_burn
```

**Both arms were re-taken** after the probe was changed, and the change is
worth recording because the probe tripped a guard of exactly the kind this
card is about. The first version used `@pytest.mark.skipif` to select its mode;
`tests/test_suite_profile.py::TestSuiteTiming_CollectsTheSameWithAndWithoutTheLog::test_the_host_state_silences_elsewhere_are_exactly_the_measured_ones`
enumerates every environment-dependent skip condition in **`tests/` and
`meta/profiling/`** and holds the set to a frozen `MEASURED_SILENCES_ELSEWHERE`.
It resolves the tree through `git ls-files`, so the probe passed that guard
while untracked and **reddened it the moment it was committed**. The probe now
lets the mode decide what a test *pays* rather than whether it *runs*: no
skips, no host-state silence. Arm 1 re-read at **135.09 s** — the same figure
to the hundredth, now **4 passed** with no skip.

### 7.2 Two figures from other rounds, checked against this one

* **467.30 s** was recorded for this same file at 127 tests "on a quiet box".
  This run measured **511.43 s** for the same 127 tests with no rival pytest at
  either end — a **9.4 %** spread, inside the ~19 % `tests/README.md` quotes for
  two quiet-host runs. Both figures stand.
* **~270 s** was extrapolated for the same file from one observation of `56 %`
  at 2 min 33 s. **That extrapolation does not survive this measurement**, and
  the reason is in the distribution rather than in the host: `56 %` is 56 % of
  the **test count**, and 2 of this file's 127 tests held **198.80 s of its
  511.43 s (38.9 %)**. Linear extrapolation from a progress percentage assumes
  uniform per-test cost, and this file is the single most non-uniform in the
  suite. It was correctly flagged as a lead rather than a measurement, and it is
  **not** evidence of a 1.7× host spread.

---

## 8. This card's own pre-gate, carrying the §6 cells

Commit `58ed72ae`. The selection is **derived, not chosen**: every
`tests/test_*.py` that reads the tree or the profiling directory
(`grep -rln 'hang_guard\|rank_durations\|PROFILING\|rglob("*.py")\|ls-files'`),
passed to pytest as a **zsh array** whose length is printed, because an
unquoted `tr`-joined string reaches pytest as one path and exits 4 with "no
tests ran".

| cell | value |
|---|---|
| files selected | **29** (array length printed in the log) |
| collected | **2325** |
| passed / skipped / failed | **2310 / 15 / 0** — and 2310 + 15 = 2325 reconciles |
| pytest exit | 0 |
| wall clock | 316.24 s |
| load at start → end | 4.54 → 5.12 |
| **rival-pytest, start / end** (`pgrep -fc`) | **0 / 0** |
| tests at or over the 120 s ceiling | 0 |

**Every skip by name** (`-rs`), and both are the known baseline shapes:

* **14 ×** `tests/conftest.py:207` — *Database not reachable: DATABASE_URL is
  not set*.
* **1 ×** `tests/test_book_pdf_memory.py:1296` — `setrlimit(RLIMIT_AS)` refused
  by this kernel.

Earlier, narrower gate rows on the same commit, each with its collected count
taken by `--collect-only` under `-o addopts=''`:

| selection | collected | result |
|---|---|---|
| the two changed files **together** | 542 | 542 passed / 0 skipped / 0 failed |
| `test_suite_profile` + `test_guard_integrity` + `test_collected_names` | 590 | 590 passed / 0 skipped / 0 failed |
| `test_book_export_interior_cover` alone (after arm) | 132 | 132 passed, 104.12 s |
| `test_kill_matrix` | 76 | 76 passed, 111.64 s |

**Running the two changed files TOGETHER is what caught the §7.1 defect**: each
passed alone, so a per-file pre-gate would have missed it and the merge gate
would have charged the card for it.

### 8.1 The kill matrix over this card's own additions

Ten deletion mutants, each line-count-preserving, each deleting a mechanism one
of the new claims names. Attribution is per assertion, by the message that
fired.

| mutant | deletes | verdict | assertion that fired |
|---|---|---|---|
| M1 | the memo itself | **KILLED** | `len(splits) == 1` → *"the line split ran 9816 times"* |
| M2 | the UTF-8 encode, single-line branch | **KILLED** | the stdlib equality, at the module's line 3116 |
| M3 | the middle lines, multi-line branch | **KILLED** | the stdlib equality |
| M4 | the end-column slice, multi-line branch | **KILLED** | the stdlib equality |
| M5 | inclusivity at the threshold (`>=` → `>`) | **KILLED** | the boundary equality on the synthetic artefact |
| M6 | the default-DENY parse floor | **KILLED** | `pytest.raises` → *"DID NOT RAISE"* |
| M7 | the phase summing (call phase only) | **KILLED** | the boundary equality's two-phase row |
| M8 | the ceiling derivation's use of its argument | **KILLED** | *"a planted default of 45 came back as 120.0"* |
| M9 | a frozen node id's correctness | **KILLED** | the live-derivation equality, `gained`/`lost` named |
| **M10** | **the cheapening itself** (back to `ast.get_source_segment`) | **SURVIVES BY DESIGN** | none — 6 passed in **122.44 s** against the baseline's 10 s |

**M10 is the control, not a gap.** The change is a price change, so no claim
may red on it; its own evidence is the 122.44 s it took to pass.

**Two honest negatives**, both already in §5: no mutant separated the two
equivalence controls (M2–M4 die to each independently, so the small-source
sweep's claim of unique reach was false and has been narrowed in the test), and
truncating `_source_lines`' result by its last element **survives both**,
because the line pattern's `$` alternative appends a final empty match no
`end_lineno` indexes.
