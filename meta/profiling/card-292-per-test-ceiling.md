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
| over a **planted** text (the module's own characters, three lines swapped) | **108** — **all** of them; **32** distinct lengths, **389,122–389,385** chars |
| over the **real** module | **0** |
| keeping the **`callee identity`** arm | **36**, at **716–721** calls each = **25,852** (99.9 % of all the calls) |
| **without** that arm — 36 with it removed, 36 with **both** arms removed | **72**, at **0–2** calls each = **21** |

**A per-analysis figure taken from one analysis may not be multiplied by the
analysis count.** 108 is exactly right; 675 was a property of one particular
analysis whose domain the draft did not state.

**And the domain of those 108 was itself misstated — review cycle 2, F-202.**
Fix round 1 wrote that 36 of them run "over the real module" and the other 72
"over the small planted texts, at 0-2 calls each". **The counts above are
exactly right and that attribution is wrong on both halves**, which the table's
own figures refute without any new measurement: an analysis of the real module
makes **716** calls, so **721** cannot be one, and the 72 cheap analyses are
over texts of the *same* ~389,000 characters as the expensive 36. Re-measured
in fix round 2 through a **different door** than the call counter — a wrapper
that captures :meth:`_page_positions`' own ``source`` and ``door_arms``
arguments rather than counting inside it:

```
wall 27.81s   analyses 108   door calls 25873   mean 239.6
per-analysis door-call distribution:
  [(0, 53), (1, 17), (2, 2), (716, 1), (717, 13), (718, 8), (719, 10), (720, 3), (721, 1)]
analyses whose source IS None (the real module by default):   0
analyses whose source EQUALS the real module text exactly:    0
distinct source lengths: 32   range 389122 .. 389385
real module source length: 389177
HIGH (>100 calls):  n=36  calls 716-721  sum 25852
   their source lengths: 389122 .. 389385
   door_arms: {"explicit:'callee identity'": 36}
LOW  (<=100 calls): n=72  calls 0-2      sum 21
   their source lengths: 389122 .. 389385
   door_arms: {"explicit:'door spelling'": 36, 'explicit:NONE': 36}
```

**The discriminator is the `callee identity` arm**, and it is decisive on the
real module too — same shim, four calls, `source=None`:

```
segment() door calls on ONE UNPLANTED analysis:  716
same, door-spelling arm removed:                 716
same, callee-identity arm removed:                 0
same, both arms removed:                           0
```

That arm is the one that walks every `ast.Call` and so pays the `segment()`
door; the door-spelling arm anchors almost nothing on its own. **The
conclusion the wrong reason supported does not move** — 25,852 + 21 = 25,873,
the mean is still 240, and a per-analysis figure still may not be multiplied by
the analysis count. Only the reason changes, and the true one is a property of
the controls rather than of the texts. **Corrected in both places that carried
it** — here and the class docstring at
`tests/test_book_export_interior_cover.py:6330`. Those are the only two, and
the audit is over the phrase rather than over the subject it was about.
`grep -rn 'small planted' tests/ meta/profiling/` on the fixed branch returns
**three** lines and **none of them prescribes the wrong domain**: the quotation
inside this withdrawal (line 194 above), this sentence, and
`tests/README.md:609`, which uses the same two words about a different test on
a different axis and is outside this card's diff. No *claim* of the wrong
domain survives.

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
3. **A rival pytest.** Signature: `pgrep -f 'MacOS/Python.*pytest' | wc -l`
   **> 0** at either end of the run — **the third instrument this card has
   prescribed for this one cell, and the first that passes both controls**
   (§7's F-001/F-201 inset has the five-case truth table and the traces).
   **Not** `pgrep -fc` — BSD/macOS `pgrep` has no `-c` flag: usage error,
   exit 2, and an **empty** cell inside `$(...)`. And **not**
   `pgrep -f 'bin/python -m pytest' | wc -l`, which is **blind** here: this
   venv's `bin/python` is a macOS *framework* python and re-execs through
   `Python.app`, so a live run's argv begins
   `/Library/Frameworks/.../Python.app/Contents/MacOS/Python -m pytest` and
   the literal `bin/python` never appears — measured **0 with a real venv
   pytest alive**, and measured **1** against a mere `zsh -c` whose own argv
   mentions the pattern, so it is false-negative and false-positive at once.
   And **not** `ps -Ao command | grep -c '[m] pytest'`, whose baseline is not
   a constant: it counts this agent's own `zsh -c` wrapper lines, and with
   **no pytest running at all** it returned **1** in fix round 1, **2** when
   this card first measured it, and **3** for the orchestrator an hour later
   (all three recorded in `meta/kanban/config.yml`) — the count depends on
   the shape of the command that asks. This cell — **not** the load average
   — is what "quiet" means on this box, and `meta/kanban/.full-suite.lock`
   with CARD-255's foreign-holder guard is the only thing that enforces it.
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
  bounded, unguarded price — and the price is now OWED BY A NAMED CARD rather
  than by an intention.** Review cycle 2 (F-203) found that this bound named
  "the obvious successor card" while no such card existed, so nothing owed the
  control. **`CARD-302` — "The memo's USE is unguarded — the cheapening can
  silently return"** was created for it on `main` at `bd2128b5`, status
  `ready`, and carries the hot-site guard, the two cold sites staying legal,
  and an explicit decision about M10 as its own acceptance criteria. Its ACs
  are not restated here; they live on the card.
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

**This is a snapshot of `main` at `bd2128b5`, lines 42–131 of
`meta/kanban/config.yml`, and it is verbatim as of fix round 2 (2026-10-27).**
The blob it quotes landed at **`e4d33dfa`** — the commit that corrected the
rival-pytest prescription for the second time — and is identical at
`bd2128b5`: `git rev-parse e4d33dfa:meta/kanban/config.yml` and
`bd2128b5:meta/kanban/config.yml` are both
`4a03afc785ab59c8d1e52afb89d145022c0a1248`.

**`main` has since moved past that blob, and this section deliberately does not
track it** — a snapshot is of a revision, and a committed artefact cannot be
held to follow a sibling file other agents keep editing. Known movements after
the extraction: `5e440f2f` extended the truth table from four cases to five
(adding the `(d2)` column and naming all three rejected forms), and `01a411b6`
corrected one of its own cells. **§7 below carries the five-case form and is the
one to read for the instrument itself.**

*Cycle 3's F-301, recorded where it happened:* this paragraph previously ended
"and is unchanged at `main`'s head". That was **true when written and false by
the revision this card merges into** — a present-tense claim about a file this
card does not own, which is the same family as every other defect this document
has had to withdraw. It is now a statement about named commits only.

**This section has now been re-extracted twice, once per defective
instrument.** The first draft claimed "verbatim" while prescribing
`pgrep -fc`, already false against the correction `main` landed at `d61f0be1`
(review cycle 1, F-001). Fix round 1 re-extracted it at `d77fa29c` — verbatim
by construction, and faithfully reproducing a prescription that **could not
measure its own cell** (review cycle 2, F-201). So "verbatim" was true both
times and was never the property that mattered: *a snapshot inherits the
defects of what it snapshots.* The block below is again **extracted
programmatically rather than retyped** — `git show` piped through `sed -n
'42,131p'` straight into the fence — so the claim holds by construction, and
the diff that proves it is below the block rather than asserted. The
convention itself is board-side state and will keep moving — a snapshot that
names its commit is honest, a snapshot that calls itself "the convention" is
not.

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
  #   rival-pytest            `pgrep -f 'MacOS/Python.*pytest' | wc -l`, both
  #                           ends. > 0 means a rival run. THIS CELL HAS NOW
  #                           BEEN WRONG TWICE, so it carries the truth table
  #                           that earned it (measured 2026-10-27, four cases,
  #                           a real venv pytest launched both ways):
  #
  #                             instrument                      (d)  (a)  (b)  (c)
  #                             pgrep -f 'pytest'                1    1    1    0
  #                             pgrep -fi 'python.*pytest'       1    1    1    0
  #                             pgrep -f 'MacOS/Python.*pytest'  0    1    1    0
  #
  #                           (a) pytest via `python -m pytest`; (b) via the
  #                           `.venv/bin/pytest` console script; (c) nothing
  #                           running; (d) THE CONTROL -- only a `zsh -c`
  #                           whose own argv mentions pytest, which is the
  #                           false positive that started all of this. Only
  #                           the third row passes all four.
  #
  #                           TWO REJECTED FORMS, both of which LOOK like they
  #                           work:
  #                             `pgrep -fc ...`  -- BSD/macOS pgrep has no -c
  #                               flag. Exits 2 with a usage line, and in a
  #                               `$(...)` cell yields an EMPTY host cell, not
  #                               a count.
  #                             `pgrep -f 'bin/python -m pytest' | wc -l`
  #                               -- reads 0 WHETHER OR NOT pytest is running,
  #                               so it never errors and always looks fine.
  #                               The venv's python is a macOS FRAMEWORK
  #                               python: it re-execs through Python.app, so a
  #                               live run's argv is
  #                               `/Library/Frameworks/.../Python.app/Contents/MacOS/Python -m pytest ...`
  #                               and the literal `bin/python` never appears.
  #                               This was the correction for the first defect
  #                               and it was WORSE than what it replaced: the
  #                               first failed loudly, this one silently.
  #
  #                           DECLARED BOUND: the working pattern keys on the
  #                           framework-python re-exec path, so on a venv built
  #                           from a NON-framework python it would read 0 and
  #                           be blind again. It is verified on this box only.
  #                           Re-run the four cases before trusting it
  #                           elsewhere -- and note the lesson that actually
  #                           generalises: an instrument needs a POSITIVE
  #                           control (it must rise) AND a NEGATIVE one (it
  #                           must not rise on case (d)). A cell reading 0
  #                           because the box is quiet and a cell reading 0
  #                           because the command is blind are identical from
  #                           the figure alone.
  #                           THIS is the cell that decides whether the run was
  #                           quiet; the load averages are context. NOT
  #                           `ps -Ao command | grep -c '[m] pytest'`, which was
  #                           the idiom in use and which counts THIS AGENT'S OWN
  #                           `zsh -c` wrapper lines: measured 2026-10-27 it
  #                           returns 1-3 with no pytest running at all, so its
  #                           baseline moves with the shape of the command that
  #                           asks -- measured 2 by CARD-292, 3 by the
  #                           orchestrator an hour later, and 1 by CARD-292's
  #                           fix round. Three readings, three values, for a
  #                           figure that was being used as a constant.
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

**And the "verbatim" claim is checked rather than asserted**, which is the
whole point of extracting the block instead of retyping it:

```
$ sed -n '520,609p' meta/profiling/card-292-per-test-ceiling.md > doc_s6.txt
$ git -C <main> show bd2128b5:meta/kanban/config.yml | sed -n '42,131p' > main_cfg.txt
$ wc -l doc_s6.txt main_cfg.txt
      90 doc_s6.txt
      90 main_cfg.txt
$ diff doc_s6.txt main_cfg.txt
$ echo "exit=$?"
exit=0                                      <- DIFF EMPTY, verbatim HOLDS
$ shasum -a 256 doc_s6.txt main_cfg.txt
186f76e9cdce5d3b...  doc_s6.txt
186f76e9cdce5d3b...  main_cfg.txt
```

**AC-6's demonstrated instance is §8.2** — the fix-round pre-gate, whose
`rival-pytest` cells are taken through
`pgrep -f 'MacOS/Python.*pytest' | wc -l`, at both ends, beside both load
averages and the per-test-ceiling cell. **That is the instrument the block
above prescribes, and §8.2's cells were re-taken with it in fix round 2** —
the cells fix round 1 published for those rows were read through
`pgrep -f 'bin/python -m pytest' | wc -l`, which §7's inset shows is blind on
this box, so they are superseded there rather than carried. §7's whole-file
table is the *first* instance and carries all three cells, but its
rival-pytest cells were taken through the defective `ps` idiom and are
declared as such there (§7's F-001/F-201 inset), and §8's `0 / 0` cells are
**withdrawn as not established** (§8). A convention is demonstrated by an
instance whose instrument can produce its figures — **and which has been
shown to produce them, in both directions** — so §8.2 is the one that
counts.

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
here.) The sentence claiming the broken form returned 0 is **withdrawn**: no
reading was ever taken through it, because no reading can be. §8 carries the
same defect as a results cell, and §8.2 is the re-take.

**And the replacement fix round 1 named was broken too — review cycle 2,
F-201.** Fix round 1 prescribed `pgrep -f 'bin/python -m pytest' | wc -l`,
which is the last command in the trace above, and that command is **blind on
this box**: it reads **0 whether or not a pytest is running**, so it never
errors and always looks like a working instrument. The mechanism is in the
venv: `.venv/bin/python` is a macOS **framework** python, and a framework
python **re-execs itself through `Python.app`**, replacing `argv[0]`. A live
run's command line is therefore

```
/Library/Frameworks/Python.framework/Versions/3.14/Resources/Python.app/Contents/MacOS/Python -m pytest ...
```

and the literal `bin/python` never appears in it. So the `0` on the trace's
last line is **not** evidence that the box was quiet; it is what that command
returns always. **That correction was worse than the defect it fixed**:
`pgrep -fc` failed **loudly** — exit 2, a usage line, an empty cell — while
this one fails **silently**, and every `rival-pytest: 0` cell this card took
through it carries no information at all.

**The instrument this document now prescribes is
`pgrep -f 'MacOS/Python.*pytest' | wc -l`**, and it is prescribed because it
was **measured over five cases**, not because it reads plausibly. A counting
host cell needs **both** controls: a **positive** one (it must rise when a
rival is there) and a **negative** one (it must not rise on something that
merely *mentions* pytest). An instrument that can only rise is half a control,
and an instrument that can only read 0 is none. Measured on this box
**2026-10-27**, a real venv pytest launched both ways, two wrapper shapes and
idle:

| instrument | (c) idle | (d) a `zsh -c` whose argv says *pytest* | (d2) a `zsh -c` whose argv says *.venv/bin/python -m pytest* | (a) `python -m pytest` | (b) `.venv/bin/pytest` |
|---|---|---|---|---|---|
| `pgrep -f 'pytest'` | 0 | **1 ← false +** | **1 ← false +** | 1 | 1 |
| `pgrep -fi 'python.*pytest'` | 0 | 0 | **1 ← false +** | 1 | 1 |
| `pgrep -f 'bin/python -m pytest'` | 0 | 0 | **1 ← false +** | **0 ← false −** | **0 ← false −** |
| **`pgrep -f 'MacOS/Python.*pytest'`** | **0** | **0** | **0** | **1** | **1** |

**The five cases, as the literal commands they were taken against** (cycle 3's
F-302: the columns above were named by description, and `(d)` reproduces only
for a wrapper this document had never shown — two readers measuring "a `zsh -c`
whose argv says *pytest*" can pick different wrappers and get different cells,
which is exactly how `(d)` and `(d2)` came to differ):

```
(c)  nothing running
(d)  /bin/zsh -c 'sleep 8; : run the pytest suite'          # says pytest, NOT python
(d2) /bin/zsh -c 'sleep 6; : .venv/bin/python -m pytest tests/'
(a)  .venv/bin/python -m pytest -o addopts='' --collect-only -q
(b)  .venv/bin/pytest        -o addopts='' --collect-only -q
```

`(d)` is the shape that separates `pgrep -fi 'python.*pytest'` (reads **0** here,
because the wrapper never says *python*) from `pgrep -f 'pytest'` (reads **1**).
A wrapper that *does* say *python* — the orchestrator's own `(d)` when it
re-measured this table on `main` — makes that row read **1** instead. Both
readings are correct about their own wrapper, and that sensitivity is itself the
disqualification: an instrument whose answer depends on how a neighbouring
command happens to be worded is not measuring the box.

Only the last row is right in all five columns — and the row above it, fix
round 1's, is wrong in **three**: it is false-negative on both real pytests
and false-positive on a shell wrapper, which is the exact inverse of an
instrument. (d2) is not hypothetical: it is the shape of an asking command on this
harness, and the same shape is what gave the `ps | grep -c` idiom the moving
baseline recorded in §4.

**The positive control, taken while §8.2's own row 1 was in flight**, so the
trace is a reading of the gate this document publishes rather than a
demonstration beside it:

```
$ # the pre-gate script's own output, 30 s into ROW 1's pytest
host cells, START:
  [19:36:16Z] load={ 5.26 6.63 7.01 }  rival-pytest=0  (blind form=0)
POSITIVE CONTROL, taken while ROW 1's own pytest is in flight (pid 28140, alive=yes):
  its argv: /Library/Frameworks/Python.framework/Versions/3.14/Resources/Python.app/Contents/MacOS/Python -m pytest -o addopts= -rs tests/test_book_export_interior_cover.py tests/test_suite_profile.py
  pgrep -f 'MacOS/Python.*pytest' | wc -l   = 1      <- MUST RISE
  pgrep -f 'bin/python -m pytest'  | wc -l   = 0      <- the blind form, FALSE NEGATIVE
  pgrep -fl 'MacOS/Python.*pytest':
    28140 /Library/Frameworks/.../Python.app/Contents/MacOS/Python -m pytest -o addopts= -rs tests/test_book_export_interior_cover.py tests/test_suite_profile.py
POSITIVE CONTROL, second sample:
  rival-pytest=1   blind=0
host cells, END:
  [19:38:23Z] load={ 4.58 5.79 6.61 }  rival-pytest=0  (blind form=0)
ROW 1 exit=0  wall=126.74 s

$ # and again, 60 s into ROW 2's pytest over the 29-file selection
POSITIVE CONTROL, taken while ROW 2's own pytest is in flight (pid 28719, alive=yes):
  pgrep -f 'MacOS/Python.*pytest' | wc -l   = 1      <- MUST RISE
  pgrep -f 'bin/python -m pytest'  | wc -l   = 0      <- the blind form, FALSE NEGATIVE
```

**The negative control, taken on an idle box in the same script**, because an
instrument that can only rise is half a control:

```
$ # the same script, before row 1, with nothing of ours running
idle, before: rival-pytest=0
  wrapper argv: /bin/zsh -c sleep 20; : .venv/bin/python -m pytest tests/
  pgrep -f 'MacOS/Python.*pytest' | wc -l   = 0      <- must stay 0
  pgrep -f 'bin/python -m pytest'  | wc -l   = 1      <- the blind form, FALSE POSITIVE
  pgrep -fl 'MacOS/Python.*pytest':
                                                      <- nothing matched
  pgrep -fl 'bin/python -m pytest':
    28062 /bin/zsh -c sleep 20; : .venv/bin/python -m pytest tests/
  after kill: rival-pytest=0
```

**Declared bound on the instrument.** It keys on the **framework re-exec
path**, so on a venv built from a **non-framework** python there is no
`MacOS/Python` in the argv and this pattern would read 0 and be blind in
exactly the way its predecessor is. It is verified **on this box only**; the
five cases above are the check to re-run before trusting it elsewhere. That
bound is stated rather than papered over, because the lesson that actually
generalises is not the pattern — it is that **a cell reading 0 because the box
is quiet and a cell reading 0 because the command is blind are identical from
the figure alone**, and only a control taken where the cell is used can tell
them apart.

**The 1 / 1 cells below are therefore evidence that no rival pytest ran only in
the weaker sense that the count did not rise** — and weaker still, because
they were taken through the `ps` idiom, whose baseline *is* 1. The two arms
were taken back to back by one script that ran nothing else, which is the
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
the fix-round revision**; that is AC-6's demonstrated instance — and it has
now been re-taken **twice**, because fix round 1's re-take used
`pgrep -f 'bin/python -m pytest' | wc -l`, which review cycle 2 (F-201) showed
is blind on this box. A cell withdrawn for having no instrument is not fixed
by a second instrument that cannot rise either, and this one *was* the same
defect: §8's cell was an **empty** string wearing a label, §8.2's first
version was a **0** that would have been 0 with a rival pytest running. The
figures in §8.2 are fix round 2's, taken through
`pgrep -f 'MacOS/Python.*pytest' | wc -l` with both controls fired in the same
script.

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

### 8.2 The fix rounds' own pre-gate — AC-6's demonstrated instance

Review cycle 1 scored this card **7 / 10, NOT CERTIFIED** on two gating
findings that were both **figures** rather than code (F-001, F-002); review
cycle 2 scored it **7 / 10** again on two more of the same kind (F-201,
F-202). This is **fix round 2's** gate, taken on **2026-10-27** at `db0e1a3e`
plus the fix-round-2 edits, in one script that ran the two rows back to back
and nothing else. It is **AC-6's demonstrated instance**, and what that now
requires is one step stronger than it was: every host cell below was taken
with a command that *can* produce it **and that was shown to produce it, in
both directions, in this same script** — the positive control sampled while
row 1's own pytest was in flight and the negative control on the idle box
before it (§7's F-201 inset carries both traces and the five-case table).

**Fix round 1's figures for these two rows are superseded, not carried.** Its
`rival-pytest` cells read `0 / 0` through
`pgrep -f 'bin/python -m pytest' | wc -l`, which review cycle 2 proved blind
on this box, so those two cells were **0 by construction**. The rows were
re-run rather than re-labelled, because a cell taken through a blind
instrument is not a figure to relabel. Fix round 1's wall clocks are kept
beside the new ones so the re-run is visible as a re-run — and the re-run
earned its keep: the **first** attempt at row 2 in this round came back
**`1 failed, 2309 passed, 15 skipped`, exit 1**, on a cell fix round 1's own
document edit had reddened. That is below, under *Procedure*, and it is the
reason this table is taken on the tree as committed rather than before the
last edit.

| cell | **row 1: the two changed test files together** | **row 2: the derived blast radius** |
|---|---|---|
| selection | `tests/test_book_export_interior_cover.py` + `tests/test_suite_profile.py` | the §8 grep's **29** files (array length printed) |
| collected (`--collect-only -o addopts=''`) | **542** (132 + 410) | **2325** |
| passed / skipped / failed | **542 / 0 / 0** | **2310 / 15 / 0 — and 2310 + 15 = 2325 reconciles** |
| pytest exit | 0 | 0 |
| summary lines in the log | **1** | **1** |
| wall clock | **126.74 s** (pytest's own line: 125.99 s; fix round 1: 122.62 s) | **295.69 s** (pytest's own line: 294.57 s; fix round 1: 308.46 s) |
| `load-start → load-end` (`sysctl -n vm.loadavg`, 1-minute) | 5.26 → 4.58 | 4.58 → 10.16 |
| **`rival-pytest`, start / end** (`pgrep -f 'MacOS/Python.*pytest' \| wc -l`) | **0 / 0** | **0 / 0** |
| **the same cell, sampled while the row's own pytest was alive** | **1** — the positive control | **1** — taken again |
| **the blind form at that same instant** | **0** — false negative | **0** — false negative |
| tests at or over the 120 s per-test ceiling | **0** | **0** |

**Those four start/end cells are the ones AC-6 turns on, and this is why they
are now a measurement.** A `0` means "no rival pytest" only if a `1` was
reachable. In this script a `1` *was* reached — twice, from the rows'
own pytests — and the wrapper that merely mentions `pytest` did **not**
reach it. The same instant that reads **1** on the prescribed command reads
**0** on fix round 1's, which is the single sharpest statement available about
the difference between the two.

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

**Mutating fix round 2's own changes — and there is nothing to mutate, which
is stated rather than filled in.** Fix round 2 adds **no mechanism at all**,
and that is proved rather than claimed:

* `tests/test_book_export_interior_cover.py` is **prose only**, again by
  `ast.dump`: parsed at `db0e1a3e` and at this revision with every docstring
  stripped, the dumps are **byte-identical** — 109 docstrings each side,
  `dump_len 392100`, same dump sha — while the sources differ by **610**
  characters. The one changed docstring sentence is F-202's correction.
* `tests/test_suite_profile.py` and `meta/profiling/card292_ceiling_probe.py`
  are **byte-identical** to `db0e1a3e` (`SOURCE identical: True`).
* This document is prose.
* `meta/profiling/card292_plant_reads.py` carries F-204's unit fix: the
  `# (path, seconds, nbytes)` comment, plus the **loop target** at line 79
  that carried the same wrong unit — the class inside the file, not just the
  instance review cycle 2 named. The comment is prose; the rename is **inert,
  two ways**. Its full `ast.dump` differs in **exactly one token**
  (`id='nbytes'` → `id='nchars'`, 133 `Name` ids each side, and substituting
  the name back makes the dumps equal), and the binding has **no `Load`
  occurrence anywhere in the file** — it is a write-only loop variable, so no
  expression can read it. Re-running the probe prints the same **216** reads
  over **2** distinct paths and **44,824,752** characters.

So there is no mechanism to delete and no claim-vs-mutant question to answer.
**The alternative — inventing a mutant so the section has a row — is the
defect this document is about**, and fix round 1's P1/P2 above are the real
article because round 1 really did change a mechanism's label.

**Order of operations, stated because it decides what the gate covers.** In
each round the rows were taken **first**, on that round's clean tree. In fix
round 1, P1 and P2 were planted **after** them, each run on its own selection,
and the file was then restored from the copy taken before P1 — `git
hash-object` on the restored file equals the copy's, so the probe as committed
in round 1 is **byte-identical to the state rows 1 and 2 ran against**. In fix
round 2 **nothing was planted at all**: the two `.py` edits (the docstring and
the probe's unit) were made **before** the rows, so the rows ran against the
tree exactly as committed, and the only edits after them are to this document,
which is not a `*.py` and so is outside `_guarded_sources`.

**Procedure.** `meta/kanban/.full-suite.lock` was **never taken and does
not exist**; the full-suite guard's two environment switches —
`tests/full_suite_lock.py`'s `OVERRIDE` and `LOCK_PATH_VAR`, which this
document now deliberately does **not spell**, for the reason in the next
paragraph — and `NONOGRAM_TEST_HANG_SECONDS` were **unset** for every run in
**both** fix rounds. No run re-used §3.2's hang-guard override and nothing in
either round needed it, which the fix round 2 script printed as its first
three lines, from the environment, before the first test ran. The full suite
was **not** run; that is the merge gate's step, not this one. The interpreter
was checked rather than assumed: the shared venv's `python` resolves
`nonogram` to **`main`'s** `src` by default, so every run was invoked with the
worktree as cwd and the resolution printed —
`NONOGRAM_FILE .../PythonProject4-card-292/src/nonogram/__init__.py` — before
any figure was taken.

**And the sentence above this one used to spell those two switches, which made
row 2 RED — found by re-running it in fix round 2, not by reading.** This is
the sharpest thing in the section, so it is recorded rather than quietly
fixed. Fix round 1 argued that editing the document after its rows was safe
because the document "is not a `*.py` and so is outside `_guarded_sources`".
That is true of `tests/test_suite_profile.py`'s guard **and the tree has
another one**. `tests/test_full_suite_lock.py::test_nothing_in_the_tree_sets_either_of_the_guards_env_switches`
scans the **whole tree** with `git grep -l` for both switch names and exempts
only `tests/README.md`, the guard, its own test file, and prose under
`meta/kanban/cards/` and `meta/review/`. **`meta/profiling/` is not
exempt** — so fix round 1's Procedure paragraph, written after its rows had
been taken, made the card's own HEAD fail its own declared blast radius:

```
$ git grep -l -e <override> -e <lock path var> 98482d2c -- .   # before fix round 1
   ... no meta/profiling/ entry
$ git grep -l -e <override> -e <lock path var> db0e1a3e  -- .   # the reviewed HEAD
   db0e1a3e:meta/profiling/card-292-per-test-ceiling.md         <- introduced there
$ git log --oneline -S'<lock path var>' -- meta/profiling/card-292-per-test-ceiling.md
   db0e1a3e docs(profiling): every figure review cycle 1 refuted, re-derived ...
```

and row 2 at `db0e1a3e` plus fix round 2's first edits read

```
===== 1 failed, 2309 passed, 15 skipped, 683 warnings in 312.50s (0:05:12) =====
AssertionError: ['meta/profiling/card-292-per-test-ceiling.md'] name <override>
or <lock path var>; a tree that sets either one has neither an override nor a guard
tests/test_full_suite_lock.py:614: AssertionError
```

Review cycle 2 could not have caught it: it **carried row 2 forward** from
cycle 1 rather than re-running it, which it says it did and why. **Fixed by
not naming the switches**, because the alternative — adding `meta/profiling/`
to that guard's exempt prefixes — would widen a standing guard's allowlist to
accommodate this card's prose, which is G-1's shape and is not this card's
mandate. The row was then re-run to green; the table above carries the re-run.
**The generalising lesson is the one this card keeps paying for:** "outside
*the* guard" is not "outside *every* guard", and a post-gate edit is only free
if the gate's reach has been **measured** rather than reasoned about.

**So the blast radius was taken a THIRD time, after the last substantive edit
to this document**, which is the only way to stop arguing about the previous
sentence:

```
POST-EDIT GATE (the document is final; this run judges the tree as it will be committed)
NONOGRAM_TEST_HANG_SECONDS=[UNSET]   <the lock path var>=[UNSET]
lock file: ABSENT
array length: 29
collect: 2325 tests collected in 0.63s
START  load={ 4.87 7.03 7.12 }  rival-pytest=0
IN FLIGHT (pid 30945): rival-pytest=1   blind=0
END    load={ 4.08 6.01 6.64 }  rival-pytest=0
exit=0  wall=288.37 s
summary: ===== 2310 passed, 15 skipped, 683 warnings in 287.36s (0:04:47) =====
summary line count: 1
  SKIPPED [14] tests/conftest.py:207: Database not reachable: ...
  SKIPPED [1]  tests/test_book_pdf_memory.py:1296: setrlimit(RLIMIT_AS) refused ...
```

That run covers row 1's two files as well, because the 29-file selection
**contains** them, so one run closes both rows. **The residue, declared rather
than hidden:** this paragraph itself was written after that run. It adds no
`.py` and names neither switch, and both of those are checked rather than
asserted — `git grep -l` for the two names returns **nothing** under
`meta/profiling/`, and the one cell that reads this file tree-wide,
`tests/test_full_suite_lock.py::test_nothing_in_the_tree_sets_either_of_the_guards_env_switches`,
passes alone against the final text (`1 passed`, 0.21 s and 0.71 s on two readings). What I have **not**
established is that no *other* cell in those 29 files reads a `.md` path: the
reach of the one that bit is measured, the absence of a second is not, and
that is a declared bound rather than a claim.

