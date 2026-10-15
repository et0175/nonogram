# CARD-217: Profile the suite once, serialized, and commit the duration record the curation cards work from

**Status:** in_progress
**Priority:** P1
**Category:** tech-debt
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/217-suite-duration-profile
**Worktree:** ../PythonProject4-CARD-217
**Source:** owner request 2026-10-13 ("make cards for tests curation"), after the dispatcher's own cost analysis of `meta/kanban/suite-timing.log`
**Idea:** —
**Wave:** 39
**Created wave:** 37
**Deferred waves:** 0
**Depends on:** —
**Touches:** meta/profiling/, meta/kanban/suite-timing.log, tests/README.md
**Review score:** 9.0/10 (cycle 1/3) — clears the gate; 0 critical, 0 important, 8 minor. The reviewer re-derived every headline number independently and confirmed the conclusion.
**Started:** 2026-10-15T06:45:00Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**The measured problem (from `meta/kanban/suite-timing.log` + CARD-204's own full-suite runs).**

| wave | tests | duration | ms/test |
|------|-------|----------|---------|
| 30 | 5858 | 398s | 68 |
| 32 | 6083 | 587s | 97 |
| 34 | 6498 | 755s | 116 |
| 35 | 6618 | 770s | 116 |
| CARD-204 (2026-10-12) | 6854 | 986s | 144 |

Test count grew 17 % while wall-clock grew 148 %: the marginal test of the last
five waves costs about 5× the historical average. The suite is also the
dominant per-cycle cost by construction (`config.yml`'s own note:
`O(suite) × cycles × cards × max_concurrent`, and `test_scope: full`).

**Why this card exists before any curation card.** Nobody knows WHICH tests are
slow. Nothing in the repo records per-test durations — there is no
`--durations` artefact, no profile, no plugin. Every curation decision taken
without that list is a guess, and the two guesses already available are
plausible and contradictory:

- *the render hypothesis* — 19 test files render whole books or pages, and the
  suite contains 110 `interior(...)`, 68 `solved_puzzle_page`, 48
  `interior_stream`, 48 `render_pages`, 34 `puzzle_pages`, 30 `export_book`,
  30 `create_guide_page`, 25 `proof_pages` call sites, each materialising
  25 MB-class bitmaps;
- *the corpus hypothesis* — the project's property tests build large seeded
  corpora with stdlib `random.Random` and assert a minimum case count inside
  the test, so a few property tests may dominate instead.

This card settles it with a measurement, and leaves the measurement **on disk**
so the next person does not re-derive it.

**What to do.**

1. **Run the full suite exactly once, serialized**, from the main repo:
   `./.venv/bin/python -m pytest --durations=0 -q`
   **It must be the only suite running on the host.** Concurrent runs inflate
   every number — observed directly in wave 37, where CARD-204's and
   CARD-214's suites overlapped (both cards carry a `[Full-suite lock gap]`
   note). Check with `ps` before starting, and record in the artefact that the
   run was solo.
2. **Commit the artefact** as `meta/profiling/suite-durations-<YYYYMMDD>.txt`:
   the raw `--durations=0` output (call/setup/teardown phases included), plus a
   short header stating the commit sha, the host, the Python version, the wall
   clock, the pass/skip counts, and "solo run: yes".
3. **Derive and commit the three rankings** the curation cards consume, as
   `meta/profiling/suite-hotspots-<YYYYMMDD>.md`:
   - the 50 slowest individual tests, with their durations;
   - the 20 slowest files, with each file's share of total wall-clock;
   - the share of total wall-clock held by the 19 render-heavy files, which is
     what decides the render hypothesis above.
   Derive these from the artefact with a small script committed alongside it
   (`meta/profiling/rank_durations.py`) so the derivation is reproducible and
   nobody hand-counts it.
4. **Append the run to `meta/kanban/suite-timing.log`** in the existing format,
   noting it was a profiling run.
5. **Write the how-to-re-measure into `tests/README.md`** — that file is ~20
   waves stale (it is still titled "Admin Panel Test Suite - Wave 1" and names
   no book test file, per the backlog). This card does not rewrite it, but it
   adds the one section that keeps the profile repeatable: the command, the
   solo-run requirement, where the artefacts live, and the naming convention.
6. **No optimisation, no deletion, no test edits in this card.** It measures.
   CARD-218/219/220 act on what it finds.

## Acceptance criteria

- **AC-1** (happy): *Given* a quiet host, *when* the card's profiling run is
  executed, *then* `meta/profiling/suite-durations-<date>.txt` exists, carries
  the stated header fields, and its body is the suite's `--durations=0` output
  for a passing run. (test: `TestSuiteProfile_ArtefactExistsAndIsComplete`)
- **AC-2** (happy): *Given* the artefact, *when* `rank_durations.py` is run
  against it, *then* it prints the 50 slowest tests, the 20 slowest files with
  wall-clock shares, and the render-heavy files' total share — and re-running it
  on the same artefact gives byte-identical output. (test:
  `TestSuiteProfile_RankingIsDeterministic`)
- **AC-3** (happy): *Given* the rankings, *when* the hotspots document is read,
  *then* it states explicitly which of the two hypotheses the data supports,
  with the numbers that decide it. (verified by review, not a test — this is a
  written conclusion)
- **AC-4** (edge, solo run): *Given* another `pytest` process is running,
  *when* the profiling run is attempted, *then* it is not recorded as the
  profile — the card either waits or marks the artefact `solo run: no` and is
  re-run. (test: `TestSuiteProfile_RefusesToRecordAContendedRun`)
- **AC-5** (happy): *Given* the run completes, *when* `suite-timing.log` is
  read, *then* its last line is this run, in the file's existing format.
  (test: `TestSuiteTimingLog_FormatUnchanged`)

## Guardrails

- G-1: No test is edited, deleted, skipped or reordered by this card — it is a
  measurement only (test: the suite's pass/skip counts are identical to
  CARD-204's last recorded run, modulo cards merged in between).
- G-2: No new dependency, runtime or dev — `--durations` is stock pytest.
  `pytest-xdist`, `pytest-testmon` and profiling plugins are explicitly out of
  scope (ADR-0006/R1 for runtime; a dev-extra addition is its own decision).
- G-3: Do not touch `tests/fixtures/**` — the baseline chain carries
  "NEVER regenerate" warnings and is evidence, not a cost centre (see this
  card's own finding note below).
- G-4: `tests/README.md` gains one section; its stale content is not rewritten
  here (that is its own card, already in the backlog).

## Architecture context

- **FR:** — (test infrastructure; no FR traces to it)
- **ADR:** ADR-0006/R1 (the closed dependency baseline — G-2).
- **CON:** —
- **Components:** none (test tree only).
- **Trace:** not applicable.

## Worktree notes

- [Finding, 2026-10-13, before the card ran] The "retire the superseded golden
  baselines" idea was checked and **rejected as a cost measure**: all 13
  predecessor fixtures (`book_baseline_card128` … `card203`) are referenced
  only from docstrings and comments. The single file actually loaded is
  `tests/helpers/book_corpus.BASELINE_FIXTURE` (`load_baseline()`,
  `book_corpus.py:484`), currently `book_baseline_card203.json`. Deleting the
  predecessors would save zero seconds and would destroy deliberately-kept
  provenance (each fixture carries its own `warning` field forbidding
  regeneration, and the chain is documented in
  `test_book_pdf_memory.py:1225-1290`). The real duplication is duplicated
  *rendering*, not duplicated fixtures — which is what this card measures.

### Implementation agent's own records (verbatim, synced from the worktree 2026-10-15)

- [Finding, 2026-10-13, before the card ran] The "retire the superseded golden
  baselines" idea was checked and **rejected as a cost measure**: all 13
  predecessor fixtures (`book_baseline_card128` … `card203`) are referenced
  only from docstrings and comments. The single file actually loaded is
  `tests/helpers/book_corpus.BASELINE_FIXTURE` (`load_baseline()`,
  `book_corpus.py:484`), currently `book_baseline_card203.json`. Deleting the
  predecessors would save zero seconds and would destroy deliberately-kept
  provenance (each fixture carries its own `warning` field forbidding
  regeneration, and the chain is documented in
  `test_book_pdf_memory.py:1225-1290`). The real duplication is duplicated
  *rendering*, not duplicated fixtures — which is what this card measures.

### The run (2026-10-15)

930.81 s wall (`/usr/bin/time -p`: real 930.81, user 524.45, sys 71.86),
7073 passed / 9 skipped / 0 failed, 7082 tests timed, exit 0. **Solo: yes.**
Checked `ps` before (05:18:57Z) and after (05:34:45Z) — no other suite either
time; `meta/kanban/.full-suite.lock` was absent beforehand, held by this run
throughout, and released afterwards. Ran in the worktree, whose tree is
byte-identical to main at `56c716e` (`git diff --stat 56c716e HEAD` empty).
931 s sits between the two cleanest prior gates (CARD-212 1123 s, CARD-221
939 s), so the number is a normal one for this host.

A macOS management sweep + Spotlight re-index overlapped ~05:24–05:28Z (1-min
load peaked ~140, pytest's CPU share fell 76 %→25 %). No competing *suite*.
Recorded in the artefact header because it biases I/O-bound tests upward —
which favours the render hypothesis, and the render hypothesis still lost, so
the conclusion is safe in the direction that matters.

### The answer (AC-3)

**Neither hypothesis.** Between the two the render hypothesis is the stronger
(21.23 % vs 15.23 %), but both are dwarfed by a family the card did not name:

| group | time | share |
|---|---|---|
| `tests/test_puzzle_solver_*.py` (12 files, Chromium via a shared `browser_page` fixture) | **366.19 s** | **39.78 %** |
| render-heavy frozen set (29 paths) | 195.42 s | 21.23 % |
| `tests/property/*` | 140.19 s | 15.23 % |
| …counted in both of the above | 70.75 s | 7.68 % |
| render ∪ property (the card's two hypotheses together) | 264.86 s | 28.77 % |
| admin-local script trio | 117.16 s | 12.73 % |

Browser tests cost **868 ms** each; everything else costs **83 ms** — a
**10.4×** gap. Wave 30 was 68 ms/test overall; the non-browser suite today is
83 ms/test, i.e. barely slower. All twelve browser files were first committed
2026-10-03T08:32Z … 2026-10-08T04:19Z, *after* the wave-30 run, and they hold
69 % of the +533 s growth while being 34 % of the +1224 new tests. The
"marginal test costs 5× the average" effect is one family, not a trend.

Also: **96 % of the suite's teardown (137.97 s of 144.37 s) is that family**,
~0.33 s per test with no single test above 0.52 s — per-test browser-page
teardown, invisible in any "slowest tests" list.

### Notes for CARD-218/219/220

1. Biggest prize by far is the browser family (39.8 %, and 96 % of teardown).
   The lever is fixture scope / fewer page tear-downs, not rewriting tests.
2. Second: `tests/property/test_book_pdf_geometry.py` — 48.66 s in **four**
   tests, the densest spot in the suite.
3. The corpus hypothesis is largely a restatement of the render one; over half
   its time is render-heavy too. Not a separate line of work.
4. Fourth target: the admin-local script trio, 117.16 s / 83 tests of pure
   subprocess spawning.
5. No single test is worth deleting: slowest is 30.94 s (3.4 %); 6057 tests
   finish under 0.1 s and hold 7.4 % between them.

### Things found along the way

- **The card's own command is subtly wrong.** `pyproject.toml` already sets
  `addopts = "-q"`, so `-q` on the command line makes it `-qq`, at which
  pytest prints **no** `N passed … in Xs` summary line at all. The counts and
  wall clock had to come from `/usr/bin/time` and from counting node ids. The
  artefact header carries them, and `rank_durations.py` falls back to the
  header when the body has no summary. Documented in `tests/README.md`.
- **`--durations=0` is not enough.** pytest still hides anything under its
  0.005 s floor; across ~7000 tests that tail is big enough to distort every
  per-file share. `--durations-min=0` was added. Still stock pytest (G-2).
- **The card's "19 render-heavy files" is 29** (27 test modules + 2 helpers)
  by the grep the card itself describes. The larger set is what was measured,
  so 21.23 % is if anything generous to the render hypothesis.
- `meta/kanban/suite-timing.log` is gitignored by `.gitignore`'s blanket
  `*.log`, so it is **appended but not committed**, and a fresh worktree has
  none. The main checkout's copy was copied into the worktree so the two
  AC-5 tests that read it would actually run instead of skipping green.

### Guardrails

G-1 holds: no test edited, deleted, skipped or reordered. The suite's
7073/9 is identical to the CARD-221 gate on this same tree. This card *adds*
one new file, `tests/test_suite_profile.py` (74 tests, 0.47 s), so the next
gate should read ~7147 passed. G-2: no new dependency. G-3: `tests/fixtures/**`
untouched. G-4: `tests/README.md` gained one section, nothing rewritten.

### Mutants (13 applied, 13 killed, 0 survivors)

Harness patches `rank_durations.py`, runs `tests/test_suite_profile.py`,
restores. M1 drop the rank tie-break → `test_equal_durations_break_ties…`;
M2 `missing_header_fields`→`[]` and M3 `is_admissible_profile`→`True` → the
AC-4 header tests; M4 `other_pytest_processes`→`[]` → `test_detects_a_competing_suite`;
M5 `parse_header` doesn't stop at the table →
`test_a_comment_below_the_table_cannot_supply_a_header_field`; M6 node-id
regex `\S+` → `test_parametrised_ids_containing_spaces_survive_parsing`;
M7 render set ignored → `test_render_share_counts_only_the_frozen_set`;
M8 status regex `\w+` → `test_known_bad_lines_are_rejected`; M9 file rows
count phase records → `test_file_rows_count_tests_not_phase_records`;
M10 TOP_TESTS/TOP_FILES→10/5 → `test_report_lists_fifty_tests_and_twenty_files`;
M11 drop the header fallback → `test_header_is_used_when_the_body_has_no_summary`;
M12 `malformed_timing_lines` stops exempting comments →
`test_malformed_detector_finds_the_bad_line_among_good_ones`; M13
`timing_log_entries` keeps unparseable lines →
`test_a_commented_out_entry_is_not_counted_in_the_log`.

Two earlier mutants were **equivalent** and were replaced rather than left as
false survivors: removing the `^` from `TIMING_LOG_LINE` (redundant — the
pattern is used with `.match()`, which anchors at position 0 anyway) and
removing `parse_timing_line`'s blank/comment guard (redundant with that same
anchoring). Each masked the other, and removing both together still changed
nothing observable. M12/M13 above target the guard in `malformed_timing_lines`
and the filter in `timing_log_entries`, which are load-bearing.

Three real bugs were caught by these tests before hand-off: the `ps` matcher
fired on `tail -f pytest-output.log` (`pytest\b` matches before a hyphen —
now `(?:\s|$)`); the three-phases assertion ignored the 8 tests skipped at
setup, which carry only setup+teardown; and the module loader tripped
`@dataclass` by not registering the module in `sys.modules` first.

- [Implementation complete] 2026-10-15 — `13c3694` and `5ff9980`. **930.81 s wall, 7073 passed /
  9 skipped / 0 failed, 7082 tests timed, solo confirmed** (`ps` before and after; the
  `.full-suite.lock` absent, taken, released). 920.63 s of 930.81 (98.9%) attributed to
  individual tests. Ran in the worktree, whose tree is byte-identical to main at `56c716e`, and
  the artefact header says so.
- [AC-3 — **the answer is neither hypothesis the card proposed**]

  | group | time | share |
  |---|---|---|
  | **`tests/test_puzzle_solver_*.py`** — 12 files, Chromium through a shared `browser_page` fixture | **366.19 s** | **39.78%** |
  | render-heavy set (29 paths, not the card's 19) | 195.42 s | 21.23% |
  | `tests/property/*` | 140.19 s | 15.23% |
  | counted in both of the two above | 70.75 s | 7.68% |
  | **both card hypotheses together** | 264.86 s | 28.77% |
  | admin-local script trio | 117.16 s | 12.73% |

  Between the two the render hypothesis is the stronger (21.23% against 15.23%), and **over half
  the property time is itself render-heavy**, so the corpus hypothesis is largely a restatement
  of it rather than a rival. Both are dwarfed by a family the card never named.
- [AC-3 — why the cost per test doubled, which is the finding that matters]
  **A browser test costs 868 ms; everything else costs 83 ms — a 10.4x gap.** Wave 30 measured
  68 ms/test overall, and **the non-browser suite today is 83 ms/test**, barely slower. All
  twelve browser files were first committed between 2026-10-03 and 2026-10-08, *after* the
  wave-30 run, and they hold **69% of the +533 s of growth while being 34% of the +1224 new
  tests**. So "the marginal test of the last five waves costs 5x the historical average" was
  real as arithmetic and wrong as a diagnosis: it is **one family, not a trend**, and the rest
  of the suite has not meaningfully degraded.
  **96% of all teardown time (137.97 s of 144.37 s) belongs to that family** — about 0.33 s per
  test with no single test above 0.52 s. That cost is invisible in any slowest-tests list, which
  is exactly why nobody had found it.
- [AC-3 — the densest single spot] `tests/property/test_book_pdf_geometry.py`: **48.66 s in four
  tests.** Slowest single test 30.94 s (3.36% of the suite); top 50 tests = 32.1%; and **6057
  tests finish under 0.1 s and hold 7.4% between them** — the long tail is not the problem.
- [Three defects in the card's own instructions, found by following them]
  - **`-q` becomes `-qq`.** `pyproject.toml` already sets `addopts = "-q"`, so the card's `-q`
    doubles it and pytest prints **no** summary line at all. Counts came from `/usr/bin/time`
    and from counting node ids, and `rank_durations.py` now falls back to the header when the
    body has no summary.
  - **`--durations=0` is not enough**: pytest still hides everything under its 0.005 s floor,
    which across ~7000 tests distorts every per-file share. `--durations-min=0` added. Both are
    stock pytest, so G-2 holds.
  - The card's "19 render-heavy files" is **29** (27 modules + 2 helpers) by the card's own grep.
- [Contention caveat, recorded in the artefact rather than hidden] A macOS management sweep and
  a Spotlight re-index overlapped ~05:24–05:28Z; 1-minute load peaked near 140 and pytest's CPU
  share fell from 76% to 25%. **No competing suite at any point.** It biases I/O-bound tests
  upward, which favours the render hypothesis — and the render hypothesis still lost, so the
  conclusion is safe in the direction that matters. The agent reasoning about which way its own
  noise would push the answer is the right instinct.
- [Mutants] **13 applied, 13 killed, 0 survivors.** Two earlier mutants were **equivalent** and
  were replaced rather than logged as false survivors (a redundant `^` in a regex used with
  `.match()`, and a blank/comment guard that the same anchoring already made redundant) — each
  masked the other, and removing both together still changed nothing observable. The tests
  caught three real bugs before hand-off, including a `ps` matcher that fired on
  `tail -f pytest-output.log` because `pytest\b` matches before a hyphen, and one mutant that
  was **initially tautological** (comparing against the constant it was meant to pin) and
  survived until that was fixed.
- [Note for the next merge gate] This card **adds** `tests/test_suite_profile.py` (74 tests), so
  the gate should read **~7147 passed**, not 7073. G-1 holds: no existing test edited, deleted,
  skipped or reordered, and the profiling run's 7073/9 is identical to CARD-221's gate on the
  same tree.

- [Review cycle 1] 2026-10-15 — **9.0/10, clears the gate on cycle 1.** 0 critical, 0 important,
  8 minor. Report: `meta/review/20261015T060200Z-CARD-217-cycle1.yml`. 26 mutants.
  **The reviewer believes the conclusion, having re-derived it rather than read it:** they wrote
  their own parser against the committed artefact, importing nothing from `rank_durations.py`,
  and **every headline number reproduces exactly** — browser 366.19 s / 39.78% / 422 tests /
  868 ms; render-heavy 195.42 s / 21.23% / 1079; property 140.19 s / 15.23% / 184; overlap
  70.75 s; admin trio 117.16 s / 12.73%; non-browser 554.44 s / 6660 tests / 83 ms; browser
  teardown 137.97 of 144.37.
  - **No double counting**: the four families are pairwise disjoint, the one overlap is declared
    on its own line, `195.42 + 140.19 - 70.75 = 264.86` exactly, and every share uses the same
    denominator — the reviewer specifically checked that none silently switches between the
    920.63 s attributed and the 930.81 s wall clock.
  - **The committed rankings are byte-identical to the script's stdout** across all 82 rows, and
    the artefact is internally consistent (`21238 = 7074x3 + 8x2`, the 8 being tests skipped at
    setup, which carry no call phase) — i.e. not truncated.
  - **The render set's re-definition is honest and the browser family is conservative.**
    Re-running the card's own grep gives exactly the 29 frozen paths; and **three other
    `browser_page`-driven files sit outside the family** (9.11 s / 12 tests) — including them
    would raise it to 40.77%. The agent left 9 s on the table against its own conclusion.
  - **Both self-reported items are honest.** The two "equivalent" mutants really are equivalent:
    the reviewer fuzzed four implementations over **200,922 inputs** — structured
    prefix/suffix cross-products, every single-character substitution and insertion in a good
    line, and 200k random strings — with **0 differences on full groupdict**, not merely on
    None-ness. And M10's tautology was real and is really fixed. All 13 of the agent's own
    mutants were re-run and all 13 killed: its mutation report is accurate, not inflated.
- [Review cycle 1 — N-001: the contention argument is backwards, and the conclusion survives
  anyway] The card argues the sweep biased I/O-bound tests upward, favouring the render
  hypothesis, which still lost. **The exposure is the other way round:** the render set is
  in-process CPU work (176.82 s of `call`, 0.03 s of teardown) while the **browser family is the
  wait-bound one** (137.97 s of teardown blocked on another process), so a CPU-starving sweep
  inflates the *winner*. The reviewer supplied the two arguments that do hold and the document
  should carry instead: **(a)** a magnitude bound — about four minutes at 25% instead of 76% CPU
  is at most ~161 s of excess across the whole suite, where the browser family would have to
  shed **170.8 s** to lose; and **(b)** per-test teardown measured across all 422 browser tests
  is mean 0.327 s, median 0.370, stdev 0.144, per-file means 0.198–0.413, histogram unimodal —
  **no contention spike anywhere in the family**. The cost is structural, not an artefact.
- [Review cycle 1 — three real survivors, none gating, one of them aimed at the next four cards]
  - **N-003: `test_exactly_one_artefact_is_committed` will red the first time CARD-218, 219,
    220, 235 or 236 re-profiles** — which is exactly what every one of them is instructed to do
    to measure its saving. It also contradicts the dated naming convention and the `found[-1]`
    fixture in its own file. A landmine pointed at this card's own successors; fix before merge.
  - **N-002: `RENDER_HEAVY_SNAPSHOT` is pinned by nothing.** Dropping a path from it survives
    all 74 tests — and that constant is what decides the 21.23% the re-pointed CARD-218/219 are
    now sized against. `--verify-render-set` exists and works, and no test calls it.
  - **N-004:** swapping the file-share denominator `attributed` -> `wall_clock` survives; no
    share value is pinned anywhere, and nothing checks the committed hotspots document against
    `report(...)`.
  - Minor beyond those: **N-007** two prose slips — the browser files' date range ends
    2026-10-08T07:28Z, not 04:19Z (the load-bearing "all after wave 30" claim holds), and the
    README's worked log line shows 1071 s / 151 ms per test where the real run was 931 s /
    131 ms; **N-005** AC-5's two real-log tests skip silently off this host because the log is
    gitignored (disclosed and worked around); **N-006** the admissibility check is blind to the
    kind of contention that actually happened and nothing calls it at profile time; **N-008**
    shares are of attributed time where AC-2 says wall clock (labelled, 1.09% apart).
