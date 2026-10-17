# CARD-236 — what the admin-local script tests were actually paying for

CARD-217 measured the three admin-local script files at **117.16 s across 83
tests, 12.73 % of a 930.81 s suite** (`suite-hotspots-20261015.md`), with
`tests/test_start_admin_local.py` the third-slowest file in the repo, and
attributed the cost to "pure subprocess spawning". CARD-236 was cut to spawn
once per *scenario* instead of once per assertion, and to replace execution
with parsing wherever only the script's text was being checked.

**Neither was needed, because spawning is not the cost.** The cost is the
*first* `execve` of a newly created executable on a host running Microsoft
Defender's real-time protection. The tests wrote five fresh stub programs into
each test's own `tmp_path` and then ran them; sharing one stub directory across
the process takes the trio from **116.04 s to 13.38 s** of attributed time with
**all 83 tests still executing their script** and not one assertion changed.

Nothing in `meta/profiling`'s frozen artefacts was re-measured or regenerated
to produce this file: `suite-durations-20261015.txt` and
`suite-hotspots-20261015.md` are CARD-217's recordings and are read here, never
written.

## The host, and the honest status of every figure below

* Mac15,6 Apple M3 Pro, 11 cores, 18 GB, macOS 26.7.1 (Darwin 25.6.0 arm64),
  Python 3.14.3, pytest 9.1.1 — the same host CARD-217 and CARD-235 measured on
* `mdatp health --field real_time_protection_enabled` → **true**

**None of the timing runs below is a solo run, and G-3 is not met by this
card.** CARD-222's fix agent held `meta/kanban/.full-suite.lock` in a sibling
worktree through the whole measurement window; `ps -Ao pid,command | grep
pytest` was clean immediately before three of the six runs and showed that
suite before the other three. The 1-minute load average moved between 2.88 and
5.30 against a desktop holding Chrome, PyCharm and Defender. Both committed
artefacts record `solo run: no` and say why, and
`tests/test_admin_local_cost.py::TestAdminLocalTests_ShareIsRecorded::test_neither_artefact_claims_to_be_the_solo_profile_g3_asks_for`
fails if either header is edited to `yes` without a fresh measurement.

Read every second below as a loaded-host second. What survives the loading is
the *ratio*, for two reasons:

1. the gap is **8.67x** on the committed pair and 10.65x / 10.56x on the two
   others, against the ±20 % run-to-run band CARD-217 measured here;
2. the cost being removed is a synchronous **wait on another process**, not CPU
   work — the before run spent `user 5.05s, sys 5.74s` over 117.83 s of wall
   clock, i.e. **9 % of one core**. A CPU-contended host inflates both halves
   of a wait-bound comparison; it cannot manufacture an order of magnitude.

The settled figure is the orchestrator's quiet full-suite profile at the merge
gate. What it should show: the trio at **~13 s**, the suite's attributed time
down from 920.63 s to **~816 s**.

## The settled measurement — the orchestrator's solo run at the merge gate

Everything in the sections above was recorded **under contention** and says so. This section
is the solo measurement G-3 asked for, taken by the orchestrator on a quiet host after
CARD-222 had merged and with no agent, sibling worktree or other suite running.

**The trio alone, both halves measured solo and consecutively** (`pytest -q` total, three files,
no other process):

| | wall | tests |
|---|---|---|
| before, on `main` | **140.79 s** | 83 passed |
| after, this card | **13.73 s** | 83 passed |
| ratio | **10.25x** | same 83 node ids |
| trio + this card's own `test_admin_local_cost.py` | 14.37 s | 105 passed |

**Read the metric, not just the number.** 10.25x is *not* an improvement on the contended
8.67x reported above: the two are different measurements. The contended figures are
**attributed** time (pytest's summed per-test durations); these are pytest's **total wall**
for the same three files, which includes collection and fixture setup outside per-test
attribution. That is why the contended "before" of 116.04 s is *smaller* than this solo
"before" of 140.79 s, which would otherwise look impossible. The honest comparison is
ratio-to-ratio within one metric, and both metrics agree that the cost is gone.

**The suite, measured across two consecutive full-suite gates on the same host, same day:**

| | suite wall | tests |
|---|---|---|
| CARD-222's merge gate (before this card) | 924.53 s | 7873 passed, 9 skipped |
| CARD-236's merge gate (this card) | **784.64 s** | **7895 passed, 9 skipped** |
| delta | **-139.89 s (-15.1 %)** | **+22 tests** |

The suite got 15 % faster *while gaining 22 tests*. The solo trio delta
(140.79 - 13.73 = 127.06 s) independently accounts for 127 s of that 140 s, and the residual
12.83 s sits well inside the host variance already observed on **identical code** in this same
session: CARD-222's two gates measured 995 s and 928 s, a 67 s spread. Two independent
measurements agreeing to less than the host's own noise is the strongest claim available here.

**The trio's share of the suite, and a correction to this card's own projection.** Measured
from the merge gate's `--durations=0` output, the three files plus the new cost file attribute
**25.13 s of 784.64 s = 3.20 %**:

| file | attributed | duration lines |
|---|---|---|
| `test_start_admin_local.py` | 10.83 s | 36 |
| `test_run_admin_tests.py` | 6.46 s | 26 |
| `test_admin_local_cost.py` | 4.66 s | 12 |
| `test_setup_admin_local.py` | 3.18 s | 22 |
| **total** | **25.13 s** | 96 |

That is a **lower bound**: pytest omits durations under 5 ms, and about 219 of the 315 possible
phase entries for these 105 tests are not listed, worth at most ~1.1 s in total. So the true
share is **3.20-3.34 %**.

**This card projected 1.64 % and the measured figure is 3.20 % - the projection was optimistic
by a factor of 2, and that is recorded rather than quietly replaced.** The projection was
derived by scaling the contended attributed figures; it did not account for per-test setup and
teardown inside a full-suite run, where the host is loaded by 7895 other tests rather than idle.
Against CARD-217's recorded baseline the share still falls from **12.59 %** to **3.20 %**, a
3.9x reduction - a smaller win than projected, and a real one.

*(One small discrepancy noted in passing, not corrected here because it is CARD-217's
recording and this document only reads it: CARD-217's own figures give
117.16 / 930.81 = 12.59 %, while the number quoted as its headline is 12.73 %. The
re-derivation is stated here so a later reader is not puzzled by the 0.14 pp.)*

**Status of G-3 after this section: met.** The two `.txt` artefacts keep their
`solo run: no` headers, because they are honest records of contended runs and relabelling them
would make them lie; `test_neither_artefact_claims_to_be_the_solo_profile_g3_asks_for`
therefore still passes and still guards them. The solo measurement lives here instead.

## The measurement the diagnosis rests on

Three columns, each 5–6 runs of one `--check-only` run of
`scripts/start_admin_local.sh` through the suite's own harness, timed with
`time.perf_counter` in-process:

| column | per run | what differs |
|---|---|---|
| stubs written fresh into `tmp_path` (the pre-card harness) | **1.097, 1.186, 1.227, 1.305, 1.381 s** | five new executables per run |
| stubs reused from a directory a previous run had executed | **0.074, 0.084, 0.102, 0.120 s** | nothing else; same copy of the script, same throwaway root, same log |
| building the five stub files and not running them | **0.003, 0.003, 0.004, 0.005, 0.006 s** | — |

The first run of the "reused" column was itself 1.318 s, because at that point
the stubs were new. That is the whole finding in one line: **the cost is paid
once per stub file, not once per run.**

The controls that rule out "spawning is expensive on this host":

```
20x bash -c ':'                     0.081s total     ->  4 ms per spawn
20x ./.venv/bin/python -c 'pass'    0.366s total     -> 18 ms per spawn
```

A `--check-only` run spawns bash once, the two Docker stubs, the psql shim
(which execs a real interpreter), the `python` stub and the `alembic` stub — six
processes, ~40 ms of spawning by the rates above, and 0.074–0.120 s measured
once the files are known. The missing ~1.1 s was never the spawn.

## Before and after

`rank_durations.py`'s own output on the two committed artefacts, which are
trio-only runs (`card-236-trio-before.txt`, sha256
`3907bf5d6e27830bdf89bf4f4ba6b31bfb08d61712c60d6848201f231c4e9c98`;
`card-236-trio-after.txt`, sha256
`7abf5900d80691d7c6f339f158252441c50504df45ba2cedc7ebbe32882a353a`). To
reproduce either:

```bash
./.venv/bin/python meta/profiling/rank_durations.py \
    meta/profiling/card-236-trio-before.txt
```

| | tests | attributed | wall clock | ms/test |
|---|---|---|---|---|
| CARD-217, in the whole suite | 83 | 117.16 s | — | 1412 |
| **before** (this card, `card-236-trio-before.txt`) | 83 | **116.04 s** | 117.64 s | **1398** |
| **after** (this card, `card-236-trio-after.txt`) | 83 | **13.38 s** | 14.72 s | **161** |

The before column reproduces CARD-217's 117.16 s to within 1 %, which is what
makes the pair worth comparing at all. The other two pairs, same method, same
window:

| pair | before (attributed / wall) | after (attributed / wall) | ratio |
|---|---|---|---|
| 1 (committed) | 116.04 s / 117.64 s | 13.38 s / 14.72 s | 8.67x |
| 2 | 114.73 s / 116.97 s | 10.77 s / 12.42 s | 10.65x |
| 3 | 110.54 s / 112.20 s | 10.47 s / 11.64 s | 10.56x |

Pair 1 is the committed one because it is the conservative one: the largest
"after" against a mid "before".

**The share.** A trio-only artefact's attributed total *is* the trio, so its
own share is 100 % and useless. Putting the measured trio back into CARD-217's
suite with every other test left exactly as it recorded them:

* before: 117.16 / 920.63 = **12.73 %** (CARD-217's figure)
* after: 13.38 / (920.63 − 117.16 + 13.38) = 13.38 / 816.85 = **1.64 %**

That is a projection, labelled one here and in the test that checks it
(`projected_share_pct`). The merge gate's full-suite profile is what confirms
it.

### The three slowest tests of the trio, before and after

| test | before | after |
|---|---|---|
| `test_start_admin_local.py::test_the_decision_over_an_enumerated_corpus_of_url_shapes` | 14.13 s | 0.99 s |
| `test_run_admin_tests.py::TestRunAdminTests_KeepsItsArguments::test_each_test_type_and_option_reaches_pytest` | 10.36 s* | 0.70 s |
| `test_setup_admin_local.py::...::test_the_decision_over_a_pairwise_corpus_of_url_shapes` | 9.86 s* | 0.85 s |

(*CARD-217's figures for those two; this card's before artefact has them at the
same magnitude.) The corpus tests are the ones a conversion to parsing would
have hollowed out, and they are now the cheapest thing in the file to keep.

## What was changed

One function, `tests/test_start_admin_local.tool_dir`, and the two `run_script`
harnesses asking it for a stub directory instead of writing one per test:

* keyed on the stub **bodies**, so the siblings' set (`pytest` in place of
  `python`) and the `without_psql` set each get their own directory and no test
  can silently acquire a tool it was written without;
* `tempfile.mkdtemp` + `atexit.register(shutil.rmtree, ...)`, verified to leave
  nothing behind;
* the stubs are stateless — told what to do through `STUB_LOG`,
  `STUB_EXISTING_DBS`, `STUB_MISSING_DB`, `STUB_ALEMBIC_FAIL`,
  `STUB_PYTEST_FAIL` and appending to the log named there — which is what makes
  one copy safe to share;
* `tests/helpers/admin_scripts._real_tools_dir` does the same for the two
  symlinks `without_psql` needs.

**What is deliberately *not* shared:** the throwaway project root. The real
script, the no-op `.venv/bin/activate` and the call log stay inside each test's
`tmp_path`, so every test still copies and executes the real script and still
reads back only its own calls.

The scripts under `scripts/` are not edited by this card (G-1).

## Nothing was converted to parsing, and why

The card offered the trade; measurement made it unnecessary, and it would have
cost real coverage:

* **Parsing cannot see CARD-151's defects at all.** Both were a script that
  *named* the right database and handed psql a string psql cannot parse — a
  driver-qualified `postgresql+psycopg2://` URL taken whole as a database name,
  and a URL with no database answered by connecting to one named after the
  user. The suite's method is that the psql model
  (`tests/test_start_admin_local._PSQL_MODEL`, an independent `urllib.parse`
  reading of libpq's URI rules) logs *what psql would have connected to*. That
  log only exists if the script ran.
* **Nor CARD-150's quoting defect.** `test_alembics_own_message_reaches_the_output`
  reads the four-space-indented quote on the script's *own stdout*, because
  alembic's message merely leaking past the script to the terminal satisfies
  any weaker check. Stream separation is a property of a run.
* Six tests in the trio already assert on text alone and always did — the
  `scripts/README.md` checks and the three copies of the URL-resolution block
  read against each other. `TestAdminLocalTests_ExecutionSetIsDeclared` pins
  that set at exactly those six, derived from the tree with `ast`, so a later
  conversion cannot be slipped in silently. **No test was retired, so there is
  no named survivor to declare** (CARD-220's rule).

## The mutant matrix (AC-2 and AC-4)

Each of CARD-150's, CARD-151's, CARD-152's and CARD-168's original defects was
put back into the script **one at a time**, and the whole trio run twice: once
with the four test files restored byte for byte from `HEAD` (the pre-card
tests, verified with `cmp`), once with this card's tests. Scripts were restored
from byte copies after every mutant and verified with `filecmp.cmp`.

The baseline is green on both sides — 83 passed, 0 failed, with no mutant
applied, on the pre-card tests and on this card's tests — which is what makes a
red row mean anything.

| # | defect put back | script | pre-card tests red | this card's tests red | same set |
|---|---|---|---|---|---|
| M1 | CARD-150: bare `psql -c "SELECT 1"` on the local branch | `start_admin_local.sh` | 15 | 15 | yes |
| M2 | CARD-150: `export DATABASE_URL="$DEFAULT_DATABASE_URL"` over the caller's | `start_admin_local.sh` | 3 | 3 | yes |
| M3 | CARD-150: a failed migration warns and continues | `start_admin_local.sh` | 3 | 3 | yes |
| M4 | CARD-150 F-001: `2>&1` dropped, alembic's words not captured | `start_admin_local.sh` | 1 | 1 | yes |
| M5 | CARD-151: the `+driver` not stripped for psql | `start_admin_local.sh` | 8 | 8 | yes |
| M6 | CARD-151: a URL naming no database accepted | `start_admin_local.sh` | 6 | 6 | yes |
| M7 | CARD-152: bare `psql -c "SELECT 1"` on the local branch | `setup_admin_local.sh` | 10 | 10 | yes |
| M8 | CARD-152: `export DATABASE_URL` over the caller's | `run_admin_tests.sh` | 13 | 13 | yes |
| M9 | CARD-168: the test runner defaults to `nonogram_poc` | `run_admin_tests.sh` | 5 | 5 | yes |
| — | **control: no mutant** | — | **0** | **0** | yes |

The identical failing *sets* — not merely identical counts — are the evidence
for AC-2: for all 83 tests at once, and not only for converted ones, this
card's tests red on exactly the defects the pre-card tests red on.

`TestAdminLocalTests_StillCatchesTheOldDefects` is the standing version of the
same matrix: it puts each defect into a copy of the script, runs it through the
harness via `script_text`, and asserts the observable its named guard keys on
is now wrong — nine defects plus a three-script control, ~1 s in total, no
child pytest. The matrix above is the part that cannot be a standing test,
because it needs the pre-card test files.
