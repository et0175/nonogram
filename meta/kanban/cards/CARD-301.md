# CARD-301: NFR-001's 5-second p95 gate has never run — `bench_generate.py` is not a file pytest opens, and its docstring says it is

**Status:** in progress
**Priority:** P1
**Category:** tech-debt
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/301-the-bench-file-pytest-never-opens
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-301
**Source:** orchestrator, 2026-10-25, from CARD-294's fix round 1. The guard that round built for its own critical finding (`tests/test_collected_names.py`) found a **second instance of the same family on the day it was written**, in a file belonging to no card. Independently re-measured by the orchestrator before this card was cut.
**Idea:** —
**Wave:** 64 <!-- assigned 2026-10-28. HARD contention, not a preference: CARD-301 declares meta/architecture/requirements.yml, and so does CARD-299 at wave 66 (measured intersection: exactly that path), so 66 is excluded. CARD-297 (w64) and CARD-298 (w65) intersect its three files EMPTY, so both are free. 64 chosen because at 0.5d against CARD-297's 1d it does not extend the wave, and because what it restores is a MEASUREMENT -- NFR-001's 5-second p95 gate has never executed, so every wave landing before it ships against an unverified performance threshold, waves 64-67 included. A gate is worth most early. -->
**Created wave:** 60
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/bench_generate.py, meta/architecture/requirements.yml, tests/test_collected_names.py, tests/test_nfr001_generation_time.py, meta/architecture/trace.yml <!-- amended 2026-10-29: the new module is the file route 2 cannot be taken without, declared by the round rather than hidden, and accepted by cycle 1 (+1 path, 0 src, 0 pyproject); trace.yml added when cycle 1's F-3 made its repair part of this card -->
**Review score:** 7.0 cycle 1/3 (not certified; F-1/F-2/F-3 required, fix round 1 running)
**Started:** 2026-10-29
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this is P1

**A performance requirement has been reading as verified while its verifier has
never executed once.**

`tests/bench_generate.py` declares three module-level `test_*` functions, one of
them the verifier for **NFR-001/AC-037** — the 5-second p95 generation bound. Its
own docstring states that it *"runs inside `pytest -q` with the rest of the
suite"*. It does not. Measured twice, independently:

- the fix round: a bare `pytest --collect-only` from the repo root collects
  **9,224** tests and **none** is in that file;
- the orchestrator, separately: `pytest --collect-only -q | grep -c bench_generate`
  = **0**.

The cause is the same one that produced CARD-294's cycle-1 critical finding, one
level over: pytest's `python_files` default is `test_*.py`/`*_test.py`, and
`bench_generate.py` matches neither. `pyproject.toml`'s
`[tool.pytest.ini_options]` sets only `testpaths` and `addopts`, so the default
applies. CARD-294's cycle 1 only ran the file by naming it on the command line,
which is exactly how a file like this stays invisible: every deliberate
invocation works, and the suite never touches it.

**This is the same defect class as CARD-294's F-1 and it is worth saying plainly:
one card's guard found another card's hole within hours of existing.** That is the
argument for the guard, and this card is the first thing it caught.

## What to implement

1. **Decide where AC-037's verifier lives, and make it run.** The two routes are
   not equivalent and the choice is the card's real content:
   - rename the file to a `test_*.py` spelling so the suite collects it — but
     note this touches the **frozen render-set snapshot** that CARD-294's G-7 and
     `tests/test_suite_profile.py` reason about, and it adds a benchmark's wall
     clock to every full-suite run, which this board has spent three cards
     cheapening (CARD-218, CARD-219, CARD-287);
   - or move AC-037's assertion into a file the suite already opens and leave
     the bench script as a deliberate standalone, keeping its three functions as
     a profiling entry point.
   The second is probably right — a p95 benchmark inside the gate is a flaky gate
   — but **measure the suite-cost consequence of the first before declining it**,
   because "probably right" is how this board gets claims wider than their
   controls.
2. **Correct the docstring either way.** It currently asserts a falsehood about
   its own execution, which is the class of defect `TestGuardProse_*` exists to
   catch and which four cards have now been gated on.
3. **Re-check the other two functions in the file.** Only AC-037 was traced; the
   other two may verify nothing anybody claims, in which case say so rather than
   preserving them by default.
4. **Unpin it from the guard.** `tests/test_collected_names.py::…::test_the_files_pytest_never_opens_are_the_two_known_ones`
   currently pins `tests/bench_generate.py` (with `tests/integration_tests.py`, a
   standalone script by design) **with its reason**. When this card resolves the
   file, that pin must shrink to one entry in the same commit — a pin outliving
   its hole is the declaration-outliving-its-hole defect, and this board has
   gated on it repeatedly.

## Acceptance criteria

- **AC-1** (the requirement's verifier executes): *Given* a bare `pytest` run
  from the repo root with no file named on the command line, *then* NFR-001/AC-037's
  verifier is collected and runs, **or** AC-037's `test:` names a different
  verifier that is. (test: a `--collect-only` assertion naming the resolved node
  id; the existing `test_collected_names.py` guard must agree.)
- **AC-2** (the pin shrinks with the hole): *Given* the resolution, *then*
  `test_the_files_pytest_never_opens_are_the_two_known_ones` holds **one**
  entry, changed in the same commit as the mechanism, and still **reds** when a
  third uncollected file is planted. (test: the named test plus its mutation.)
- **AC-3** (the docstring stops lying): *Given* the file as it ships, *then* no
  docstring in it claims an execution context it does not have. (test:
  `TestGuardProse_EveryNamedControlExists`' family, or a named successor.)
- **AC-4** (the suite cost is measured, not assumed): *Given* whichever route is
  taken, *then* the decision records the benchmark's wall clock and what adding
  it to every full-suite run would cost, measured rather than estimated — and if
  the route declines collection, that figure is the reason. (**gate**: the
  measurement on the card.)

## Guardrails

- G-1: **No production behaviour change.** `git diff --name-only main...HEAD -- src/`
  must be empty. This card changes what runs, never what the generator does.
- G-2: Do not change `pyproject.toml`'s `python_files`/`python_classes` to make
  this file collect. Widening the global pattern to catch one file would pull in
  every other non-test module under `testpaths` and is the blunt instrument this
  board would have to undo later; CARD-294's guard reads pytest's **effective**
  patterns, so it would silently follow the widening rather than object to it.
- G-3: No new runtime dependency (ADR-0006/R1); stdlib + Pillow + NumPy.
- G-4: Do not weaken `tests/test_collected_names.py`'s default-deny rule or its
  5,000-name floor to accommodate this file. The pin is the designed route.

## Architecture context

- **NFR:** NFR-001 (AC-037, the 5 s p95 bound; note AC-038 beside it is already
  `status: superseded` because 50×50 became invalid at `MAX_SIZE=30`)
- **ADR:** ADR-0039 (R1 controls that can fail, R2 default-deny)
- **Components:** COMP-002
- **Trace:** meta/architecture/trace.yml

## [Premise RE-MEASURED at dispatch — 2026-10-29, orchestrator] confirmed, and one thing the card does not say

**The hole is real and still open.** Re-measured on main `6b0dfa30`, with
`-o addopts=''` so the `addopts = "-q"` stacking trap cannot swallow the output:
a bare run collects **9,570** tests (up from the card's 9,224 as the board has
landed cards) and **0** are in `tests/bench_generate.py`. The card's two
measurements hold.

**What the card does not say, and it changes route selection: the gate is
`@pytest.mark.xfail(strict=True)`.** `test_20x20_p95_is_under_5s` carries a
marker whose reason is CARD-006/CARD-018's density sweep — *"Still over on
every seed at 35/38/40%, and 4-of-5 at 42% … do not remove it on partial
data."* So **AC-037 is not merely unverified, it is known MISSED and recorded as
missed**, and collecting the file does not verify NFR-001: under `strict=True`
a collected gate asserts the requirement is **still** unmet, and would RED the
suite on the day the solver got fast enough. That is a worthwhile gate — it is
the thing that forces the marker's removal rather than letting it rot — but it
is a different claim from the one AC-1 reads like, and the card must not report
NFR-001 as verified on resolution. **G-5 (new, below) forbids removing the
marker as part of this card.**

**Three falsehoods in that docstring, not one.** Item 2 says "correct the
docstring"; the measured list is:

1. *"it runs inside `pytest -q` with the rest of the suite"* — it collects 0.
2. *"see `tests/conftest.py` for why a file named `bench_generate.py` is
   collected at all"* — **`tests/conftest.py` says nothing about it.** Its only
   near-match is `config.addinivalue_line("markers", "performance: …")` at
   `:110`, and no `python_files` setting exists anywhere in the repo
   (`pyproject.toml:86-93` sets `minversion`, `testpaths`, `addopts`,
   `pythonpath`, `markers` — that is all). The docstring points at a mechanism
   that does not exist, which is why the first claim reads as load-bearing.
3. *"This is a gate … and it fails when the cap is missed"* — inverted by the
   `xfail(strict=True)`: as written it fails when the cap is **met**.

**AC-037's `test:` ref resolves to nothing.** `requirements.yml:5414` names
`BenchGenerate_20x20_p95Under5s`. That string exists in exactly **one** file —
`tests/bench_generate.py`, at its own `:3` and `:139`, both of them prose. It is
not a class, not a function, not a node id. So AC-1's second branch ("or
AC-037's `test:` names a different verifier that is") is not an alternative to
be considered — **the ref is broken either way and this card is the one that
fixes it**, to a real node id a `git grep -w` can find. Same family as
[the board's standing rule] that a planned ref reads as a mechanically checked
one.

- **G-5 (added at dispatch): do not remove or weaken the `xfail(strict=True)`
  marker, and do not touch `P95_CAP_SECONDS`, `CORPUS`, `_P95_RANK` or
  `_ALLOWED_OVER_CAP`.** The marker's own reason forbids removal on partial
  data, and this card is about *where the verifier lives and whether it runs* —
  not about the solver's performance. A card that makes AC-037 green by
  reshaping the corpus has taken CARD-018's scope and broken a requirement's
  record of being missed.
- **AC-5 (added at dispatch): the record stops reading as verified.** *Given*
  the resolution, *then* AC-037's `test:` is a node id that `git grep -w`
  resolves in `tests/`, and the criterion's state — verified / known-missed —
  is stated where a reader of `requirements.yml` sees it, not only in a pytest
  marker. (test: the collect-only assertion of AC-1 extended to assert the ref
  string resolves; **gate**: the ref re-grepped at merge.)

## [Implementation round 2026-10-29 — route 2, and the hole was invisible to BOTH gates]

Branch `card/301-the-bench-file-pytest-never-opens`, 3 commits (`575436f7`,
`a7f0945b`, `6f721e57`), worktree clean. **Verified by the orchestrator rather
than relayed**, all with `-o addopts=''`:

- footprint exactly 4 paths; `git diff --name-only main...HEAD -- src/` **empty**
  (G-1); `pyproject.toml` **0** diff lines (G-2); all four blobs match HEAD
- a bare `--collect-only` collects **9580** against main's **9570** — **+10
  reconciling exactly** to the ten new node ids — and `grep -c bench_generate`
  is **0**. The card's central claim is true by the only instrument that can
  see it
- the card's named tests by node id: **599 passed, 1 xfailed, 0 skipped**
  (48.41 s), `-rs` printing no SKIPPED section. The xfail is AC-037's gate, by
  design
- the pin shrank to one entry (`tests/test_collected_names.py:488`); AC-037's
  ref is now a real node id with `status: unmet` beside it

**Route 2**: AC-037's wrapper moved to `tests/test_nfr001_generation_time.py`;
the corpus, cap, statistic and timing stayed in `bench_generate.py`, which
becomes an honest standalone with a `__main__` door. G-5 held — AC-037 was not
made green.

### The finding the card did not anticipate: both gates were blind, and each one's blind spot was the other's premise

Chasing a figure that did not reproduce (the round reported the validator at
"56 warnings"; both arms actually read **0 errors / 108 warnings** and the two
outputs are **byte-identical**, so its conclusion was right and only its number
wrong) turned up something nobody had checked: **the validator never flagged
AC-037's dead ref at all.** `BenchGenerate_20x20_p95Under5s` has no `def` and no
`class` anywhere in the repo, yet the validator's own search reads it as ALIVE:

```
git grep -lw BenchGenerate_20x20_p95Under5s -- . ':(exclude)meta/architecture' ':(exclude)*.md'
→ tests/bench_generate.py   exit=0
```

Both matches are prose in that one file — a docstring line at `:3` and a
`# AC-037 — …` banner at `:139`. `validators/utils.symbol_exists()` is
`git grep -lw`: a **text** search. Its own docstring claims `-w` resolves a name
"to its `def test_x` definition", which is false — `-w` only enforces word
boundaries. AC-038's genuinely absent ref right beside it **is** flagged, so the
instrument works; here it was satisfied by the file's own comment about itself.

**So this hole survived because it was invisible to both gates at once:** pytest
never opened the file (`python_files` defaults), so the test could not run; and
the ref check reads `tests/` as text, so the file's prose kept the ref looking
alive. `meta/review` and `meta/profiling` can be excluded from that search;
**`tests/` cannot**, because it is the only place the search must look.

**The residue outlives the fix.** The round keeps one prose line naming the new
node id in `tests/bench_generate.py:3`. Measured: exclude the whole module
holding the `def` and `git grep -lw test_20x20_p95_is_under_5s` **still exits
0** on that line. Whether AC-5's own control inherits the blindness — it asserts
the registry names the right *string*, not that the string is a definition — is
with review cycle 1, not prejudged here.

### Two further results from the round, worth keeping

- **A strict xfail cannot witness its own instrument.** Mutant M7 renamed
  `gate_verdict` out of the benchmark; the gate raised `AttributeError`, `xfail`
  absorbed it exactly as it absorbs a missed cap, and the gate reported
  **XFAIL — green**. So "the verifier is collected and runs" does not establish
  that the measurement happened. A control outside the marker was added
  (`test_the_benchmarks_own_instrument_still_measures_a_request`). Residual
  named rather than left implied: nothing cheap catches a correct-looking but
  wrong timing.
- **AC-037 is further from met than the censored gate can say.** Uncensored
  under a production-shaped 30 s budget, p95 reads **24.881 s**; the gate can
  only ever report "≥ 5.001 s". Sizing information for CARD-018.

### Owed at merge, outside this card's Touches

- `meta/architecture/trace.yml:539` still carries the retired label
  `BenchGenerate_20x20_p95Under5s`. **Correction, 2026-10-29:** the orchestrator
  called this list "mechanically-read" and that was wrong. All three gates in
  `validators/trace.py::_check_covered_tests` are guarded by
  `if entry.get("status") != "covered": continue`, and NFR-001 is
  `status: partial` — so the label is **latent, not live**, and nothing reads it
  today. Cycle 1 caught the overstatement and supplied the second edge that
  makes it worth fixing anyway: the day NFR-001 flips to `covered`, gate 2
  **ERRORs** loudly on the missing AC-037 linkage while gate 3 **silently
  accepts** the dead label, because `cs.exists()` is `git grep -lw` and this
  card's own new module now text-matches that retired string at `:388` and
  `:441`. The card relocated the camouflage into its own new file.
- `meta/architecture/decisions/adr/0001-...md:23` cites the old path as a node
  id (prose — that ADR has no `check:` key, verified)

### One brief line of the orchestrator's was wrong

The dispatch brief said not to commit under `meta/`. The round committed
`meta/architecture/requirements.yml`, which is in this card's `Touches` and
without which AC-5 cannot be satisfied, and it measured three card-branch
precedents carrying that same file (`d579f491`, `daaa2f2f`, `7d86a869`) — all
three verified. The exclusion is about `meta/kanban` and `meta/review`. **The
round was right and the brief was over-broad.**

## [AC-4's measurement — transcribed by the orchestrator 2026-10-29]

**AC-4's gate is "the measurement on the card", and the figures were not on it.**
The round put them in the module docstring and `requirements.yml` because the
dispatch brief told it not to commit under `meta/` — the orchestrator's error,
not the round's. Transcribed here so the gate has something to read. Every row
was **independently re-derived by review cycle 1**; where the two differ, both
are given, and the spread is the honest precision of the figure.

| figure | round | cycle 1 re-derived |
|---|---|---|
| gate call time | 14.0 s (13.85–14.22, five readings) | **13.91 s, 14.12 s** |
| the module's whole cost | 14.03 s over **30** setup/call/teardown rows | **14.15 s / 30** |
| share of a full suite | 0.98 % | **0.99 %** |
| tests in that profile individually slower | 14, slowest 81.03 s | **14, 81.03 s** |
| full corpus, early exit disabled, 5 s budget | 40.79 s, 6/20 over cap, p95 5.001 s | **41.61 s, 6/20, p95 5.001 s** |
| uncensored 30 s-budget sweep | 122.04 s, p95 **24.881 s** | **122.67 s, p95 24.966 s**, one censored at 30.003 s |

**The suite denominator is quoted, not measured, and is labelled as such** —
1433.47 s from `meta/profiling/suite-durations-20261023.txt`, the board's last
committed profile. Cycle 1 confirmed the labelling is honest: it names its
artefact and does not read as re-measured.

**Route 1's cost, which is what AC-4 exists to decide.** Route 1 (rename to a
`test_*.py` spelling) costs the same seconds — it collects the same functions —
**plus committed references to the path `tests/bench_generate.py` go dead.** The
round counted **seven** over `docs` and `meta`; cycle 1 found an **eighth** the
round's pathspec could not see, `src/nonogram/orchestrator.py:338`, which G-1
forbids this card to touch. So the conclusion is *strengthened* while the
round's scope hid a ref — recorded as F-5 rather than waved through. Route 2
keeps seven of the eight true as written. It is **not** a render-set issue:
`tests/bench_generate.py` is not in `RENDER_HEAVY_SNAPSHOT`, neither
new/changed file matches any of the eight render idioms, and
`test_the_frozen_render_set_still_matches_the_grep_that_defines_it` passes.

Two further measured points that bear on the route: the uncensored sweep at
**122.04 s is past `hang_guard.py`'s 120 s per-test ceiling**, so `measure()`
and `report()` must stay standalone; and the capped gate cannot reach that
ceiling (20 requests × 5 s with a measured ≤ 2 ms overshoot ⇒ a ~100 s bound,
which cycle 1 notes sits only 17 % under the ceiling — F-10, minor).

**And the asymmetry the card got backwards.** The card reasoned that "a p95
benchmark inside the gate is a flaky gate". Measured on this corpus it is not
flaky at all — the verdict is reached with no sample near the decision
boundary, in three independent runs. The real asymmetry is the opposite one:
the gate is **cheapest while red** (14.0 s, early exit at sample 6) and **most
expensive as it approaches green** (41.61 s for the full corpus). The cost grows
exactly as the gap closes.

## [Review cycle 1 — 7.0, not certified]

Report: `meta/review/20261029T025000Z-CARD-301-cycle1.yml` (10 findings, 16
mutation rows, `yaml.safe_load` clean). **Three important findings, all a few
lines, and the first is the one that matters:**

- **F-1 — the card's own G-5 guard does not pin what its docstring claims.**
  Reproduced independently by the orchestrator: one line-count-preserving
  change, `DENSITIES = (30, 40, 50, 60)` → `(50, 60, 70, 80)`, leaves the corpus
  guard **green** (still 20 unique pairs, rank 19, allowed 1, cap 5.0) and the
  only red is `FAILED test_20x20_p95_is_under_5s [XPASS(strict)]` — whose marker
  message ends *"do not remove it on partial data"*. **9 passed, 1 failed in
  0.27 s.** A future round swaps the band in good faith, reads that red as *"the
  cap is met, remove the marker"*, and NFR-001 ships recorded as **met** over an
  80 %-density corpus — the exact outcome G-5 was added at dispatch to prevent,
  reached *through* the guard the card points at. (Context: density 50 times at
  0.008–0.041 s and density 60 at 0.004–0.011 s, against density 40 at
  7.5–30.0 s.)
- **F-2 — rename the pin's test**, whose name still says "two" over an assertion
  holding one. The round's reason for keeping it inverts the mechanism:
  `code_search()` excludes `meta/architecture` and `*.md`, so `meta/review` is
  the validator's **haystack, never a source of refs** — a review YAML can make
  a dead ref look alive but can never produce a finding when a name it quotes
  goes away. Neither validator arm's output mentions the test name at all.
- **F-3 — repair `trace.yml:539`** (see the correction above; latent, not live).

**Two of the orchestrator's own readings were corrected by cycle 1, and both
corrections stand:** the `trace.yml` "mechanically-read" overstatement above,
and the suspicion that AC-5's control shares the validator's blindness — it does
**not**. `test_the_registry_names_this_module_and_every_ref_resolves` resolves
each ref against `globals()` filtered by `callable`, a real definition check and
strictly stronger than `git grep -lw`; the rename mutant kills it. Verified
directly at `tests/test_nfr001_generation_time.py:412-420`.

**Cycle 1 also re-derived the round's own M7 finding and sharpened an
attribution** (F-7): under M7 the new instrument control *passes* — it calls
`_time_one_request`, which M7 does not touch — so the mutant it actually kills
is M13, and the killer under M7 is the declared-names assertion. Reasoning
sound, attribution off.

**Mutants: 15 fired, 13 killed at the named cell, 2 survived.** Step 8f's full
campaign is `deferred(cost)` under the cost ladder — three important findings
all touch tests the fix round will change.

## Worktree notes

—
