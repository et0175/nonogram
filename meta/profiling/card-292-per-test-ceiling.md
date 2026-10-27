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
| module size | 306 KB | **390,485 bytes on disk = 381 KiB**, and **389,177 characters** |
| **characters** read in the test | — | **44,824,752 characters** (44.8 M; **44,972,712 bytes** = 45.0 MB = 42.9 MiB, if encoded) |
| **seconds spent inside `read_text`** | the whole mechanism | **0.0416 s — 0.039 % of the BEFORE arm's 107.19 s** (§3.2's uncheapened test) |
| the same, **re-taken at HEAD `98482d2c`** 2026-10-27 | — | **0.0305 s — 0.115 % of the AFTER arm's 26.45 s** (second reading in the same hour: 0.0322 s, 0.122 % — read timings at this magnitude vary run to run and the refutation does not turn on them) |
| of which the first read of each path (the only ones that *can* be cold) | — | **0.0031 s** (before arm); **0.0023 s** over 2 reads at HEAD |

**Two corrections to that table, from review cycle 1, because this card's
subject is instrument domains.**

* **The unit (F-004).** `card292_plant_reads.py` sums `len(text)` *after*
  `read_text` has decoded, so what it counts is **characters**, not bytes. The
  module is not all-ASCII — the first non-ASCII character is on line 3 — so the
  two differ by 0.3 %: **389,177 characters** against **390,485 bytes** on
  disk. The rows above now say which is which, and the probe's own output label
  was changed from `bytes read` to `characters read`. Nothing downstream moves;
  the defect was that a label claimed a domain its instrument does not measure.
* **The denominator's revision (F-007).** `107.19 s` is the
  **before** arm's cost, and the first draft's cell did not say so. The probe
  at HEAD reports the same 216 reads against the **after** arm, which is the
  row added above. Both shares refute the same story, and the refutation does
  not depend on which: a page-cache story has **2** reads of 216 to pay for,
  and those 2 cost **0.0023 s**.

The refutation is not just the share, it is arithmetic: the first read of a path
**populates the page cache itself**, so a page-cache story has exactly **two**
reads to pay for out of 216. A cold cache cannot buy 22 s out of 3.1 ms.

### 1.4b What the cost actually is — and what the first draft said about it

The conclusion of this subsection never moved: the cost is
`ast.get_source_segment` → `ast._splitlines_no_ff`, it is quadratic-ish in the
module's size by construction, and it has nothing to do with the disk. But
**three of the figures and the mechanism sentence were wrong**, and review
cycle 1 was right about every one of them (F-003, F-005, F-006). Every figure
below was **re-derived in fix round 1 on 2026-10-27**, on this box, through the
door named in its own row.

**The mechanism, corrected (F-003).** `ast.get_source_segment` does **not**
re-split the whole source on every call. CPython 3.14.3's `ast.py` passes
`maxlines=end_lineno+1`, and `ast._splitlines_no_ff` **breaks out of its
`finditer` loop** at `maxlines`, so each call re-splits the source *from the
start up to the node's own end line* — a **prefix**, not the whole text. The
first draft said "whole" here and at two places in
`tests/test_book_export_interior_cover.py` — the memo's own comment and the
equivalence class's docstring — while a third comment in that same class, about
70 lines below the second, said "up to the node's line". A reader checking
either against `ast.py` would have found one file contradicting itself. All
three now say the same, correct thing, and the one that was already right is
the wording that was kept.

**The cost shape survives the correction**, because what a call pays is the
node's **position**, and the nodes are spread through the file. Counted over
one analysis of the unplanted module with a counting shim around
`ast._splitlines_no_ff` and **no profiler**:

| counted per one unplanted analysis | **measured** |
|---|---|
| calls through `_page_positions`' `segment()` door | **716** |
| of those, reaching `ast._splitlines_no_ff` | **649** (the other 67 nodes carry no location and return early) |
| `ast.get_source_segment` calls in the analysis **in total** | **740** — the 716 above plus **24** from this file's two other, cold call sites (lines 1438 and 2913) |
| `ast._splitlines_no_ff` calls in the analysis in total | **673** |
| characters re-scanned by the door's 649 splits | **127,608,978** |
| that, as a share of the module per call | **50.5 %** of its 389,177 characters |

So the total is proportional to calls × module size: **quadratic in the
module's size** for a sweep whose call count grows with it, at **half** the
constant a whole-source split per call would carry. Same exponent, half the
constant.

**The figure that was attributed to the wrong function (F-005).** The first
draft said "**675** calls per analysis" of `ast.get_source_segment`. **675 is
not a figure either function produces here**: the split count is **673** and
the `get_source_segment` count is **740**. It is within 2 of the former and 65
short of the latter it was attributed to. Corrected in this document and in
both docstrings that carried it.

**And the chain that did not reconcile (F-005).** The same draft invited
675 × 108 = **72,900** calls for the dear test. Measured over the real test
with the same shim: **25,873** door calls over **108** analyses — a mean of
**240**. Counted *per analysis* the reason is plain:

| the dear test's 108 analyses | **measured** |
|---|---|
| over the **real** module | **36**, at **716–721** calls each = **25,852** (99.9 % of all the calls) |
| over the **small planted** texts | **72**, at **0–2** calls each = **21** |

**A per-analysis figure taken from one analysis may not be multiplied by the
analysis count.** 108 is exactly right; 675 was a property of one particular
analysis whose domain the draft did not state.

**What one analysis costs, through two instruments, both named (F-006)** — and
this is the card's own rule turned on itself, because the first draft published
a **mixed** pair:

| instrument | stdlib arm | memoised arm | ratio | the split's share |
|---|---|---|---|---|
| **no profiler**, three readings back to back in one process | **2.2565 / 2.2575 / 2.2663 s** | **0.2781 / 0.2814 / 0.2819 s** | **8.0×** (8.11 / 8.02 / 8.04) | **87.7 %** of the stdlib arm, by difference between the two arms |
| `cProfile`, **both** arms profiled | **2.9691 s** | **0.7323 s** | **4.05×** | **76 %** of `tottime` in `ast._splitlines_no_ff`; **80 %** by `cumtime` |
| the first draft's published pair | **2.8429 s** | **0.2864 s** | 9.9× | 90 % |

**The honest headline is 8.0× and 87.7 %, unprofiled**, and that is what this
document and both docstrings now state. The draft's **9.9× / 90 % pair is
withdrawn.** It was labelled `cProfile` for both arms, but it cannot be two
readings of one instrument: `0.2864 s` is the magnitude of the **unprofiled**
memoised arm (0.278–0.282 s measured) and nowhere near the profiled one
(0.7323 s), while `2.8429 s` is the magnitude of the **profiled** stdlib arm
(2.9691 s measured) and well above the unprofiled one (2.26 s). **Which door
the 0.2864 s was actually taken through can no longer be established** — the
run is past and the draft left no second trace. What *is* established is that
the published pair is not internally consistent, and the arithmetic gives it
away without any re-measurement: 108 × 2.8429 s = **307 s** against §3.2's
measured before-cost of **113.02 s** for the whole test, a factor of 2.7.

Sign, order and mechanism were never in doubt, and the cliff-edge conclusion
does not move. The ratio and the share did.

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

Per analysis of the real module, **unprofiled**, three readings back to back
in one process on one host: **2.2565 s → 0.2781 s**, a **8.0×** reduction
(8.11 / 8.02 / 8.04). Under `cProfile` with **both** arms profiled it is
**2.9691 s → 0.7323 s (4.05×)**, with `ast._splitlines_no_ff` at **76 %** of
the stdlib arm's `tottime`. **The unprofiled pair is the one this document
headlines**; §1.4b records the mixed, `cProfile`-inflated 9.9× / 90 % pair the
first draft published, why it is withdrawn, and what about it could not be
established.

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
3. **A rival pytest.** Signature: `pgrep -f 'bin/python -m pytest' | wc -l`
   **> 0** at either end of the run. **Not** `pgrep -fc` — BSD/macOS `pgrep`
   has no `-c` flag: usage error, exit 2, and an **empty** cell inside
   `$(...)` (§7). And **not** `ps -Ao command | grep -c '[m] pytest'`, whose
   baseline is not a constant: it counts this agent's own `zsh -c` wrapper
   lines, and with **no pytest running at all** it returned **1** in fix
   round 1, **2** when this card first measured it, and **3** for the
   orchestrator an hour later (all three recorded in
   `meta/kanban/config.yml`) — the count depends on the shape of the command
   that asks. This cell — **not** the load average — is what "quiet" means on
   this box, and `meta/kanban/.full-suite.lock` with CARD-255's
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
* **The cheapening can silently return, and nothing reds** (review cycle 1,
  F-008). M10 is a declared survivor **by design** — reverting a price change
  must not red a claim, and G-2 forbids asserting a duration — but the
  consequence deserves stating plainly rather than living as a matrix row. The
  memo's *existence* is guarded: `test_the_split_is_computed_once_per_distinct_text`
  kills M1. Its **use at the one hot call site is not**, so this file's cost
  can return to §3.2's **113 s** with no cell firing anywhere in the suite.
  Review cycle 1 offered a control that would close it without asserting a
  duration — assert by AST that `_page_positions`' `segment()` closure resolves
  to `_source_segment` — and explicitly allowed declining it. **This card
  declines it**, for two reasons stated rather than implied: a fix round whose
  mandate is the card's figures should not add a claim that changes what the
  test tree asserts, and such a control would turn M10 from §8.1's *control*
  into a kill, so the matrix row review cycle 1 independently reproduced would
  no longer describe the tree. The file's two remaining stdlib call sites
  (lines 1438 and 2913) are cold paths that correctly stay on the stdlib, so
  the control would also have to discriminate them. **Recorded here as a known,
  bounded, unguarded price**, and it is the obvious successor card if this file
  ever climbs again.
* **One surviving mutant, reported rather than hidden:** truncating
  `_source_lines`' result by its last element changes nothing either control
  sees, because the line regex's `$` alternative appends a final empty match
  that no node's `end_lineno` indexes. The last element of the split is dead,
  by construction of the pattern rather than by an untested path.
* **No figure a probe prints is guarded by the tree, and this was measured
  rather than assumed** (§8.2). `meta/profiling` *is* inside
  `GUARDED_DIRECTORIES`, and a syntax error in a probe reds two named cells in
  `tests/test_suite_profile.py` — so the guard is live. But a mutant that
  changes what a probe **reports** (bytes where it says characters) leaves the
  whole 542-test selection green. Probe output is a claim whose only control is
  re-running the probe and reading it; this document is where that reading has
  to be recorded, and every probe figure in it names the run it came from.
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

**This is a snapshot of `main` at `d77fa29c`, and it is verbatim as of fix round 1
(2026-10-27).** The first draft of this section claimed "verbatim" while
prescribing `pgrep -fc`, and was therefore already false against the correction
`main` landed at `d61f0be1` (review cycle 1, F-001). The block below was
**extracted from `main:meta/kanban/config.yml` rather than retyped**, so the
claim holds by construction; anyone re-checking it should diff it against that
path at that commit. The convention itself is board-side state and will keep
moving — a snapshot that names its commit is honest, a snapshot that calls
itself "the convention" is not.

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
  #   rival-pytest            `pgrep -f 'bin/python -m pytest' | wc -l`, both
  #                           ends. NOT `pgrep -fc` -- BSD/macOS pgrep has no
  #                           -c flag and exits with a usage error, which in a
  #                           `$(...)` cell silently yields an EMPTY host cell
  #                           rather than a count. Found 2026-10-27 the first
  #                           time this convention was executed.
  #                           THIS is the cell that decides whether the run was
  #                           quiet; the load averages are context. NOT
  #                           `ps -Ao command | grep -c '[m] pytest'`, which was
  #                           the idiom in use and which counts THIS AGENT'S OWN
  #                           `zsh -c` wrapper lines: measured 2026-10-27 it
  #                           returns 2-3 with no pytest running at all, so its
  #                           baseline moves with the shape of the command that
  #                           asks -- measured 2 by CARD-292 and 3 by the
  #                           orchestrator an hour later, which is the point.
  #                           pgrep counts processes and returns 0.
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

**AC-6's demonstrated instance is §8.2** — the fix-round pre-gate, whose
`rival-pytest` cells were taken through the working
`pgrep -f 'bin/python -m pytest' | wc -l`, at both ends, beside both load
averages and the per-test-ceiling cell. §7's whole-file table is the *first*
instance and carries all three cells, but its rival-pytest cells were taken
through the defective `ps` idiom and are declared as such there (§7's F-001 inset), and
§8's `0 / 0` cells are **withdrawn as not established** (§8). A convention
is demonstrated by an instance whose instrument can produce its figures, so
§8.2 is the one that counts.

---

## 7. The whole file, both arms, one machine state (AC-3, AC-6's first instance)

A single-file run, so no suite lock was required. `rival-pytest` below was
taken with the idiom this board had been using,
`ps -Ao command | grep -c '[m] pytest'`, where **1** is the probe's own
`zsh -c` wrapper line and **>1** would mean a rival — **and that instrument is
defective**, which this card found by using it: the same command returned
**2** with no pytest running at all later the same day, and **1** again in fix
round 1, because it counts the agent's own shell wrapper lines and their number
depends on the shape of the command that asks.

**And the replacement this section first named was itself broken** — review
cycle 1, F-001. The first draft of the paragraph above went on to say
that `pgrep -fc 'bin/python -m pytest'` *"counts processes and returned **0**
on the same box in the same minute"*. **It cannot have returned 0.**
BSD/macOS `pgrep` has no `-c` flag: it prints a usage line to **stderr** and
exits **2**, and inside a `$(...)` host cell it yields an **empty string**
rather than a count — which is the silent-empty-cell failure AC-6 exists to
prevent, committed inside AC-6's own artefact. Re-derived in fix round 1 on
this box:

```
$ pgrep -fc 'bin/python -m pytest'; echo "exit=$?"
usage: pgrep [-Lfilnoqvx] [-d delim] [-F pidfile] [-G gid]
             [-P ppid] [-U uid] [-g pgrp] [-t tty] [-u euid]
             pattern ...
exit=2
$ X=$(pgrep -fc 'bin/python -m pytest' 2>/dev/null); echo "X=[$X]"
X=[]
$ pgrep -f 'bin/python -m pytest' | wc -l
       0
```

Neither spelling of the flag list contains a `c`: the **usage line** the
command itself prints reads `[-Lfilnoqvx]`, and `man pgrep`'s **SYNOPSIS** on
this box reads `[-Lafilnoqvx]`. (The two disagree about `-a`, which is its own
small lesson about reading a manual instead of the binary, and is irrelevant
here.) **The working form is `pgrep -f 'bin/python -m pytest' | wc -l`**, and
that is what §4 and §6 now prescribe. The sentence claiming the broken form
returned 0 is **withdrawn**: no reading was ever taken through it, because no
reading can be. §8 carries the same defect as a results cell, and §8.2 is the
re-take.

**And the working form has a positive control, which a host cell needs as much
as an assertion does.** A cell that reads 0 because it is broken and a cell
that reads 0 because the box is quiet are indistinguishable from the figure
alone — which is exactly how `pgrep -fc` survived into a results table. So the
replacement was checked both ways on this box in fix round 1: **0** with no
pytest running, and **1** taken deliberately while this fix round's own
pre-gate (§8.2) was running in the background. The cell can rise, and it rose.

**The 1 / 1 cells below are therefore evidence that no rival pytest ran only in
the weaker sense that the count did not rise** — the two arms were taken back
to back by one script that ran nothing else, which is the stronger argument for
them.

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
| **rival-pytest, start / end** | **NOT ESTABLISHED** — withdrawn, see below |
| tests at or over the 120 s ceiling | 0 |

**Every skip by name** (`-rs`), and both are the known baseline shapes:

* **14 ×** `tests/conftest.py:207` — *Database not reachable: DATABASE_URL is
  not set*.
* **1 ×** `tests/test_book_pdf_memory.py:1296` — `setrlimit(RLIMIT_AS)` refused
  by this kernel.

**The `rival-pytest` cell of that table is withdrawn, not corrected** (review
cycle 1, F-001). It was recorded as `0 / 0` labelled `pgrep -fc`, and §7's F-001 inset
shows that command cannot produce a count on this platform: it exits 2 with a
usage error and yields an **empty** string inside `$(...)`. So either the
`0 / 0` came from a different command than its label states, or no reading was
taken at all. **This card cannot now establish which.** The run is past, its
log carries no second trace of the host cell, and *inventing* a provenance for
a figure would be a worse defect than the one being fixed — which is the whole
subject of this document. So the cell is marked NOT ESTABLISHED rather than
silently relabelled. The true value is almost certainly **0** — nothing else on
this box ran pytest that afternoon, and the §7 arms were taken by one script
that ran nothing else — but "almost certainly" is not a measurement, and this
card does not get to promote it to one. **§8.2 re-takes the whole pre-gate at
the fix-round revision with the working instrument**; that is AC-6's
demonstrated instance.

**What the `collected 2325` row is a property of** (review cycle 1,
F-009/F-010). The selection is **derived at base `6e0aadca`**, and that count
is a property of that base: two of the 29 files —
`tests/test_book_difficulty_dots.py` and
`tests/test_book_pdf_vector_primitives.py` — were changed on `main` by
CARD-296's merge (blob shas differ at `6e0aadca` and at `main`'s `d77fa29c`),
so **2325 will not reproduce post-merge**. The two files *this* branch touches
are unaffected: `tests/test_book_export_interior_cover.py` and
`tests/test_suite_profile.py` have **identical blob shas** at `6e0aadca` and at
`d77fa29c`, so no content conflict is expected. Separately, the table above was
taken at `58ed72ae`, two commits before the cycle-1 HEAD, so the document edit
that landed at `98482d2c` shipped without a gate of its own; §8.2 closes that
gap for every commit on this branch, this fix round's included.

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

---

### 8.2 Fix round 1's own pre-gate — AC-6's demonstrated instance

Review cycle 1 scored this card **7 / 10, NOT CERTIFIED**, on two gating
findings that were both **figures** rather than code (F-001, F-002). This row
is fix round 1's gate over those corrections, taken on **2026-10-27** at
`98482d2c` plus the fix-round edits, in one script that ran the two rows back
to back and nothing else. It is **AC-6's demonstrated instance**: every host
cell below was taken with a command that *can* produce it, and the
`rival-pytest` instrument was checked in both directions first (§7's F-001
inset).

| cell | **row 1: the two changed test files together** | **row 2: the derived blast radius** |
|---|---|---|
| selection | `tests/test_book_export_interior_cover.py` + `tests/test_suite_profile.py` | the §8 grep's **29** files (array length printed) |
| collected (`--collect-only -o addopts=''`) | **542** (132 + 410) | **2325** |
| passed / skipped / failed | **542 / 0 / 0** | **2310 / 15 / 0** — and 2310 + 15 = 2325 reconciles |
| pytest exit | 0 | 0 |
| wall clock | **122.62 s** | **308.46 s** |
| `load-start → load-end` (`sysctl -n vm.loadavg`, 1-minute) | 5.02 → 3.96 | 3.96 → 8.03 |
| **`rival-pytest`, start / end** (`pgrep -f 'bin/python -m pytest' \| wc -l`) | **0 / 0** | **0 / 0** |
| tests at or over the 120 s per-test ceiling | **0** | **0** |

**Why the ceiling cell reads 0 without a second instrument.** §1.1 established
the kill signature: the guard calls `_exit()`, so a run that hits it ends with
**exit 1 and zero summary lines**. Both rows ended with a summary line and
exit 0, so no test reached the bound. Row 1's 122.62 s is the *session*, not a
test — which is the distinction §7.1 demonstrated and the one CARD-276 lost.

**Every skip by name** (`-rs`, under `-o addopts=''` so the count line and
`-rs` both survive — an explicit `-q` would stack with `pyproject.toml`'s to
`-qq` and print neither). Row 1 had **none**. Row 2's 15 are the two known
baseline shapes and nothing else:

* **14 ×** `tests/conftest.py:207` — *Database not reachable: DATABASE_URL is
  not set*.
* **1 ×** `tests/test_book_pdf_memory.py:1296` — `setrlimit(RLIMIT_AS)` refused
  by this kernel.

**Row 1 is run as a pair on purpose.** Each of these two files passes alone,
and the §7.1 defect — the probe's `@pytest.mark.skipif` reddening
`MEASURED_SILENCES_ELSEWHERE` — only appears when they run **together**,
because the guard lives in one file and the cause in the other. It is also the
row that covers `meta/profiling/`: `GUARDED_DIRECTORIES` in
`tests/test_suite_profile.py` is `("tests", "meta/profiling")`, resolved
through `git ls-files`, so this fix round's edit to
`meta/profiling/card292_plant_reads.py` is inside a guarded territory and row 1
is what judges it.

**Mutating fix round 1's own changes.** The rule is that every addition is
mutated by **deleting** the mechanism its claims name, line-count preserving,
and measured **per assertion**. Most of this round has no mechanism to delete:

* `tests/test_book_export_interior_cover.py` is **prose only**. Proved
  mechanically rather than asserted: parse the file at `98482d2c` and at this
  revision, strip every docstring, and the two **`ast.dump`s are identical**.
  No assertion, constant, control or call site changed, so there is no mutant
  to plant and no claim-vs-mutant question to answer — the figures in those
  comments are claims whose control is **recomputation**, which is what §1.4b
  is.
* This document is prose.
* `meta/profiling/card292_plant_reads.py` carries the round's one non-prose
  delta: a local renamed (`total_bytes` → `total_chars`) and the label it
  prints. Two mutants were planted there, both line-count preserving, each run
  on its own selection:

| mutant | deletes | verdict | cells |
|---|---|---|---|
| **P1** | the unit itself — `len(text)` → `len(text.encode())`, so the probe counts **bytes** under a label that now says characters | **SURVIVES** | none. Row 1's full 542 — **542 passed, exit 0**. The probe is its own and only control: run under P1 it prints **44,972,712** (the byte total) where the unplanted probe prints **44,824,752** (the character total) |
| **P2** | the file's parseability — one unbalanced `(` on the renamed line | **KILLED, 2 cells in one class** | `tests/test_suite_profile.py::TestSuiteTiming_CollectsTheSameWithAndWithoutTheLog::test_the_host_state_silences_elsewhere_are_exactly_the_measured_ones` and `::test_the_outcomes_are_identical_with_and_without_the_log`, both with *`SyntaxError: '(' was never closed`* at the probe's own line; 2 failed, 125 passed |

**What that pair measures is the guard's reach, and it is worth stating
because it is this card's subject.** `GUARDED_DIRECTORIES` is
`("tests", "meta/profiling")`, so the probes *are* inside a guarded territory
— P2 proves the guard is live there and not decorative. But what it guards is
**parseability and host-state silences, not figures**: P1 changes what the
probe *reports* and the whole suite stays green. A probe's output is a claim
whose only control is **re-running the probe and reading it**, and the tree
cannot be made to do that for us.

**Order of operations, stated because it decides what the gate covers.** Rows
1 and 2 were taken **first**, on the clean fix-round tree. P1 and P2 were
planted **after** them, each run on its own selection, and the file was then
restored from the copy taken before P1 — `git hash-object` on the restored file
equals the copy's, so the committed probe is **byte-identical to the state rows
1 and 2 ran against**. Nothing else the guard reads moved after the rows: the
test file was not touched again, and the only later edits are to this document,
which is not a `*.py` and so is outside `_guarded_sources`.

**Procedure.** `meta/kanban/.full-suite.lock` was **never taken and does not
exist**; `NONOGRAM_FULL_SUITE_LOCK` and `NONOGRAM_TEST_HANG_SECONDS` were both
**unset** for every run in this fix round — no run here re-used §3.2's
hang-guard override, and nothing in this round needed it. The full suite was
**not** run; that is the merge gate's step, not this one.
