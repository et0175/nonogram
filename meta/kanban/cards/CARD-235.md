# CARD-235: The browser tests stop paying for a page they throw away, 40% of the suite

**Status:** review
**Priority:** P1
**Category:** tech-debt
**Complexity:** standard
**Estimate:** 1d
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/235-browser-fixture-scope
**Worktree:** ../PythonProject4-card-235
**Source:** CARD-217's profile, 2026-10-15 — `meta/profiling/suite-hotspots-20261015.md`
**Idea:** —
**Wave:** 40
**Depends on:** CARD-217 (the measurement; do not start before it merges)
**Touches:** tests/conftest.py, tests/test_puzzle_solver_*.py (12 files), meta/profiling/
**Review score:** —
**Started:** 2026-10-15T08:44:16Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**Measured, not supposed** (CARD-217, a solo 930.81 s run of 7082 timed tests):

- `tests/test_puzzle_solver_*.py` — 12 files driving Chromium through a shared `browser_page`
  fixture — is **366.19 s, 39.78% of the suite's wall-clock**.
- **A browser test costs 868 ms; every other test costs 83 ms. A 10.4x gap.**
- **96% of the suite's entire teardown time — 137.97 s of 144.37 s — is this family**, at about
  0.33 s per test, with no single test above 0.52 s. The cost is per-test page teardown, which
  is why it appears in no slowest-tests list and why nobody found it before.
- Wave 30 measured 68 ms/test overall; **the non-browser suite today is 83 ms/test**. All twelve
  of these files were first committed between 2026-10-03 and 2026-10-08, after that run, and
  they hold **69% of the +533 s of growth while being 34% of the +1224 new tests**.

So the suite did not get slow. One family arrived and it is expensive per test.

**What to do.** Reduce the number of page set-ups and tear-downs, **not** the number of tests
and not what any test asserts. The lever named by the profile is **fixture scope**: a
`browser_page` created per test pays Chromium's page lifecycle ~420 times. Candidate shapes, to
be chosen on measurement rather than taste:

1. A module- or class-scoped page with per-test state reset (navigate + clear storage), where
   the tests in that module do not mutate anything a reset cannot undo.
2. A shared browser/context with per-test pages only where a test genuinely needs isolation.
3. Leaving a file alone entirely where its tests depend on a fresh page in ways a reset cannot
   reproduce — and saying which files those are, with the reason.

**The risk is the whole card.** Shared browser state is how a suite acquires order-dependence:
tests that pass alone and fail together, or worse, pass together and fail alone. This project
already has one test (`test_web_upload.py`) whose host-shared state makes it fail when another
worktree runs, and it is in the backlog precisely because that class of defect is expensive.
Any scope change must be proved not to have introduced order-dependence, not merely observed to
be green once.

## Acceptance criteria

- **AC-1** (happy, the saving): *Given* the browser family, *when* the suite is profiled again
  by `meta/profiling/rank_durations.py` on a solo run, *then* the family's share is materially
  below 39.78% and the hotspots document records the before and after.
  (test: `TestBrowserFixtures_FamilyShareIsRecorded`)
- **AC-2** (guard, no test lost): *Given* the twelve files, *then* the collected test count and
  every test's node id are unchanged — this card changes fixtures, never coverage.
  (test: `TestBrowserFixtures_NoTestAddedOrRemoved`)
- **AC-3** (guard, no order-dependence): *Given* any file whose page scope changed, *when* its
  tests run in **reverse** order and again in a **shuffled** order with a recorded seed, *then*
  all pass. (test: `TestBrowserFixtures_OrderIndependent`)
- **AC-4** (guard, isolation where it is needed): *Given* a test that mutates page state a reset
  cannot undo, *then* it still gets its own page, and the fixture states which category each
  file is in. (test: `TestBrowserFixtures_IsolationIsDeclaredPerFile`)
- **AC-5** (happy, each test alone): *Given* each changed file, *when* any single test in it is
  run **alone**, *then* it passes — the failure mode where a test silently depends on a
  predecessor's navigation. (test: `TestBrowserFixtures_EveryTestPassesAlone`)
- **AC-6** (edge, a failing test does not poison its neighbours): *Given* a deliberately failed
  test on a shared page, *then* the tests after it in the same module still pass.
  (test: `TestBrowserFixtures_AFailureDoesNotCascade`)

## Guardrails

- G-1: No test's assertions change. This card may change set-up and teardown only; a diff that
  touches an `assert` is out of scope and must be reported instead.
- G-2: ADR-0038/R7 pins Chromium; this card does not change the browser or the runner.
- G-3: The saving is measured by the committed `rank_durations.py` on a **solo** run, by
  CARD-217's own method — not by a stopwatch and not on a shared host.
- G-4: No new dependency (ADR-0006/R1); `pytest-playwright` is already installed.
- G-5: Out of scope — the render-heavy files (CARD-218/219) and the admin-local script trio
  (CARD-236).

## System contract

- ADR-0038/R7 — the player's tests run under Chromium (check: review-lens)
- ADR-0038/R1 — the player is plain JS with no build step (check: review-lens)
- ADR-0006/R1 — no new runtime dependency (check:
  `tests/test_export_pdf.py::test_the_dependency_baseline_is_still_closed`)

## Architecture context

- **FR:** FR-044 (the player), whose tests these are.
- **ADR:** ADR-0038/R1, ADR-0038/R7.
- **Components:** COMP-008 (the admin panel's player surface) — tests only.
- **Trace:** not updated by this card.

## Worktree notes

- [Why this is P1 and ahead of the curation cards] It is 39.78% of the suite against the render
  family's 21.23%, and the gate runs once per card and once per wave. CARD-218/219/220 were cut
  on the render hypothesis before anyone had measured; CARD-217 measured, and this is where the
  time actually is.

- [Env] forge unknown — no executing plugin manifest resolvable and the project
  declares no `forge.min_version` (there is no `meta/.skills.yml`), so the skew
  comparison is a no-op rather than a pass. Recorded so a later diagnosis is possible.
- [Wave] 40, dispatched 2026-10-15. Paired with CARD-234: no shared path and no shared
  hotspot, so the two run concurrently under the owner's concurrency cap of 2.

### CARD-235 implementation summary

**The lever was not fixture scope, and nothing's page scope changed.** The card
named three candidate shapes and said to choose on measurement. Measurement
says the premise was wrong, so the answer is shape 3 for all twelve files:

- **One Chromium page lifecycle costs 57 ms**, not 330 ms (`new_context` +
  `new_page` + close, 20 iterations against a launched Chromium; with a shared
  context it is 57 ms too, so the cost is the page, not the context).
  Collapsing it for all 422 tests is worth ~24 s — 2.6 % — and it would land in
  *setup*, where the family spent only 30.70 s in total.
- **The 0.33 s per test was `socketserver.serve_forever`'s 0.5 s poll
  interval.** The per-test `live` fixture serves the real panel on a thread and
  stops it with `server.shutdown()`, which cannot return until the serve loop
  next wakes. Every test paid a uniform 0–0.5 s wait. Worth 126 s, and nothing
  a test can observe: `shutdown()` + `join()` mean the server is stopped before
  the fixture returns either way.
- CARD-217's own evidence says so in hindsight — teardown "mean 0.327 s … max
  0.520 s", bimodal with the mass at 0.3–0.5 s and "no tail at all, stopping
  dead at 0.520 s". A hard ceiling with a flat spread under it is a bounded
  poll wait; a browser teardown would have a tail. Its 41-test near-zero
  cluster is the family's non-browser tests, which never ask for `live`.
- The repo already knew this: `tests/test_web_server.py` has carried
  `_POLL_INTERVAL_S = 0.01` from the start, commented "The stdlib default of
  0.5s would be paid on every test's teardown here". This fixture never got the
  memo.

**0.05 s, not the neighbour's 0.01 s — and that choice cost a run to find.**
Copying 0.01 s was the first attempt. Its full-suite profile showed teardown
collapsing as predicted (137.97 → 3.33 s) while the family's *call* rose 42 %
(197.52 → 279.99 s) with the rest of the suite flat at 83 → 84 ms/test, so it
was not host drift. A solo locked back-to-back A/B over all twelve files
(`meta/profiling/card-235-poll-interval-ab.txt`):

| poll | family total | call | teardown |
|---|---|---|---|
| 0.5 (stdlib) | 507.80 s | 345.20 s | 129.93 s |
| **0.05** | **283.37 s** | **246.11 s** | **11.88 s** |
| 0.01 | 372.34 s | 339.08 s | 3.69 s |

0.01 s buys 8.19 s more teardown and costs 92.97 s of call: at 100 Hz the serve
thread takes the GIL from a main thread driving Chromium through synchronous
RPC, so a handoff lands mid-round-trip. A second two-round A/B on the
call-heaviest file, run in a different order, ranks the three the same way. At
20 Hz the cost is gone and 91 % of the saving remains. The rejected 0.01 s
profile is committed as `card-235-durations-poll-001.txt` because it is the
measurement that rejected it.

**Before and after** (`meta/profiling/card-235-browser-teardown.md`; both solo
full-suite runs holding `meta/kanban/.full-suite.lock`, both fed to the
committed `rank_durations.py`, G-3):

| | before | after | change |
|---|---|---|---|
| family | 366.19 s / 39.78 % | **256.57 s / 29.78 %** | −109.62 s, −10.00 points |
| family teardown | 137.97 s | **11.62 s** | −126.35 s (0.327 → 0.028 s per test) |
| whole-suite teardown | 144.37 s | 17.14 s | — |
| family / rest of suite | 0.660 | **0.424** | −36 % relative |
| suite wall clock | 930.81 s | 871.02 s | −59.79 s |

The share is read with a caveat and the ratio is given beside it: the rest of
the suite drifted 83 → 90 ms/test between the two runs, which inflates the
denominator and flatters the share. The ratio cancels that drift, and the
family's `call` rose +10.8 % against the remainder's +8.4 % — the same drift, so
the chosen interval costs the test bodies nothing. The whole of the saving is
the teardown line.

**AC-4, the per-file category table.** All twelve are `own-page`; the
declaration and each file's reason live in
`tests/test_puzzle_solver_page.PAGE_ISOLATION`, and
`TestBrowserFixtures_IsolationIsDeclaredPerFile` greps each file for the
mechanism its reason claims, so a copied reason fails.

| file | category | why a reset cannot reproduce it |
|---|---|---|
| brush_menu | own-page | reloads mid-test to assert the brush survives a reload |
| clues | own-page | sets the viewport 29 times; a leftover viewport changes the next board's layout |
| hint | own-page | viewport, plus a console listener that would accumulate |
| marking | own-page | `page.route` interceptors (corrupted payload, aborted solver.js), a context request listener, four page listeners, a reload |
| maybe | own-page | viewport and a page listener; also the family's 30.9 s test |
| mirror | own-page | crosses the phone/desktop breakpoint by viewport and asserts the localStorage save survives it |
| page | own-page | defines the fixtures; `page.route` plus request/console/pageerror/requestfailed listeners; viewport at both 1440×900 and 390×844 |
| percent | own-page | reloads to assert the percentage is restored; console listener |
| phone | own-page | is *about* the 390×844 viewport — sets it eight times, asserts computed styles of it |
| progress | own-page | reads and writes the localStorage save six times; six page listeners |
| resume | own-page | writes, corrupts and restores the localStorage save eight times, and reloads |
| zoom | own-page | viewport 20 times, persists zoom to localStorage, reloads to prove restoration |

`page.on(...)` handlers and `page.route` interceptors accumulate on a page and
are never undone by navigating, so on a shared page a later test's console
output lands in an earlier test's list — cross-talk that reports as green.

**Order-independence (AC-3/5/6).** Shuffle seed **20261015**, recorded in
`tests/test_browser_fixture_scope.SHUFFLE_SEED` and in the record. All 422
family tests passed in reverse order and in that shuffled order; 78 single-test
runs passed alone (all 67 tests of the changed file, plus one per other file);
a deliberate failure on one page leaves its neighbours passing. Each sweep was
run at 0.01 s first and re-run at the chosen 0.05 s — both green, and both are
noted in the records.

**Scope notes (declared, not hidden).**

1. Two files outside the card's `Touches:` were edited, both tests/docs:
   `tests/test_browser_fixture_scope.py` is new and holds the six named AC
   tests (it is *not* named `test_puzzle_solver_*` on purpose — that prefix is
   `rank_durations.BROWSER_FAMILY_PREFIX`, so a thirteenth file under it would
   join the family being measured and inflate the number AC-1 is about);
   `tests/README.md` gains a paragraph on why a second profile in one day is
   named after its card. No `src/**` change at all.
2. The after artefact is not `suite-durations-<date>.txt`:
   `tests/test_suite_profile.py` enforces one profile per eight-digit date and
   pairs it with its hotspots document, and CARD-217 already holds today's.
3. These guard tests add ~33 s to the suite (four of them spawn a child pytest,
   because "in reverse order", "alone" and "after a failure" are claims about a
   run) against the ~126 s returned. The exhaustive sweeps are committed
   records, not suite runs.

**Guardrails.** G-1: no `assert` in any of the 422 tests was touched — the
whole diff to `test_puzzle_solver_page.py` is one `threading.Thread` kwarg plus
additive constants and comments. G-2: Chromium and pytest-playwright unchanged.
G-3: both profiles solo under the lock; the one run that shared the host was
killed and nothing from it recorded. G-4: no dependency added. G-5: the
render-heavy files and the admin-local trio were not touched.

**Merge gate: GREEN.** `7174 passed, 11 skipped, 17031 warnings in 926.58s`,
rc=0, 0 failed, 0 errors — full suite, nothing deselected, 11:00:15Z–11:15:46Z,
solo under `meta/kanban/.full-suite.lock`, `ps` empty either side. Logged to
`meta/kanban/suite-timing.log`.

**Reported, not fixed — a flaky guard this card ran into, three times.**
`tests/test_book_pdf_memory.py::TestBookPdfMemory_RealBookExportsUnderTheCap::test_one_cap_the_streaming_shape_survives_and_the_list_shape_dies_under`
fails on *most* full suites on this host and passed on the gate. It spawns a
child interpreter under an `RLIMIT_AS` cap of 808 MB and requires 3× headroom —
the child's peak under 269.3 MB — and it measured 279.7 MB, 276.1 MB and
(CARD-234's gate) 280.3 MB before passing on the fourth run of an unchanged
tree. One pass in four, all with the normal 11 skips, so it is a guard sitting
~3 % over its own threshold rather than a regression in anybody's branch. Its
own message says "this test's verdict has started to depend on the
interpreter's footprint rather than on the export's shape", and it passes alone
in 6.75 s — isolation is the condition in which it cannot discriminate at all.

Not this card's: it is in the render-heavy frozen set that G-5 excludes, and it
sorts before both the new file and the whole browser family, so it finishes
before any line this card changed is reached. **Suggested as its own card:** the
defect is the 3× constant, not the export. The claim being protected is that
the streaming shape fits where the materialised shape does not, and the
materialised shape dies by orders of magnitude — a 3× margin on the surviving
half is not what carries that claim. Widen the cap or take the factor to ~2.5×,
and say in the comment what it protects against. Until then expect roughly a
3-in-4 spurious red per full-suite gate.

**One calibration note for whoever reads these numbers next.** Two consecutive
full-suite runs of the *identical* tree came in at 871.02 s and 931.17 s — a
60 s, 6.9 % spread, CARD-217's variance warning reproducing itself. No
wall-clock saving is claimed anywhere in this card for that reason. Every claim
is a within-run ratio: the family's share of attributed time, and its cost
relative to the rest of the suite. Both are immune to the drift that makes the
wall clock unusable as evidence.

- [Scope gate] IN_SCOPE. 10 changed files; the only one outside `Touches:` is `tests/README.md`
  (~10%, under the ~25% mark), and `tests/test_browser_fixture_scope.py` is a NEW file, which
  SCOPE DISCIPLINE explicitly permits. Predicted `tests/conftest.py` was NOT needed — a
  prediction is not a contract, and not touching it is the better outcome.
  Note the new file's name is deliberate, not careless: `test_puzzle_solver_*` is
  `rank_durations.BROWSER_FAMILY_PREFIX`, so a thirteenth file under that prefix would have
  joined the very family AC-1 measures and inflated the number. Worth recording as the kind of
  detail a scope gate would otherwise flag as a naming inconsistency.
- [Guard] G-1 verified mechanically by the orchestrator before spending a reviewer on it:
  `git diff main...HEAD -- tests/test_puzzle_solver_page.py` touches no `assert` statement —
  the only `assert` strings in the diff sit inside docstring prose — and no `def test` or
  `class Test` was added or removed, so the pre-existing node ids are intact. The whole
  behavioural change across the twelve files is ONE line: a `poll_interval` kwarg on the
  `threading.Thread`.
- [Build gate] the implementer's own merge gate on this branch: **7174 passed, 11 skipped,
  0 failed, rc=0 in 926.58s**, full suite, nothing deselected, solo under the lock, against the
  exact committed tree (HEAD 11:00:10Z, gate 11:00:15Z). The orchestrator will re-run the gate
  on the REBASED tree at `done`, since that is the state that actually ships.
- [Premise] ⚑ THE CARD'S PREMISE WAS WRONG, and this is the headline rather than a footnote.
  CARD-235 was cut on "the lever is fixture scope / the cost is Chromium's page lifecycle".
  Measurement rejected both: one page lifecycle is **57 ms**, and the 0.33 s/test was
  `socketserver.serve_forever`'s **0.5 s poll interval** in the per-test `live` fixture, which
  `server.shutdown()` cannot return ahead of. **No file's page scope changed** — all twelve are
  declared `own-page` with a per-file reason, which is the card's explicitly legitimate outcome
  and the one measurement chose: a sixth of the saving for the whole of the risk.
  CARD-217's own data said so in hindsight — teardown "mean 0.327s … max 0.520s … no tail at
  all, stopping dead at 0.520s". A hard ceiling with a flat spread beneath it is a bounded poll
  wait; a browser teardown would have had a tail. And the repo already knew: `tests/test_web_server.py`
  has carried `_POLL_INTERVAL_S = 0.01` from the start, commented that "the stdlib default of
  0.5s would be paid on every test's teardown here". This fixture never got the memo.
  Recorded here because the next test-cost card should start from the profile, not from a
  hypothesis — which is exactly what CARD-217 was cut to provide.
