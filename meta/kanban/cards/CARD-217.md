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
2026-10-03T08:32Z … 2026-10-08T07:28Z, *after* the wave-30 run, and they hold
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
gate should read ~7147 passed.
> **[Correction, AC/EC/G gate 2026-10-15]** Superseded by fix cycle 1: the file is
> **79 tests in 0.76 s**, so the gate should read **~7152**, and the card's own
> closing note already says so. Left in place because this block is the agent's
> verbatim record of what was true when it was written — but corrected here,
> because a merge gate reads top-down and would meet the stale figure first.
> Fix cycles must amend a superseded figure where it stands, not only append
> the new one further down. G-2: no new dependency. G-3: `tests/fixtures/**`
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


## Fix cycle 1 (review 9.0, four of eight minors)

**N-003 — the landmine.** `test_exactly_one_artefact_is_committed` asserted
there is exactly one `suite-durations-*.txt`, which would have gone red the
first time CARD-218/219/220/235/236 committed its own re-profile — the very
thing each is instructed to do. It also contradicted the dated naming
convention and this file's own `found[-1]` fixture. Replaced by four tests
saying what was actually meant:

- `test_at_least_one_artefact_is_committed`
- `test_every_committed_artefact_is_well_formed` — parametrised over *every*
  artefact: header complete, admissible, >6000 tests
- `test_every_artefact_has_a_hotspots_document` — the date-pairing rule
- `test_the_latest_artefact_is_the_one_the_hotspots_document_cites` — the
  real risk a multi-profile future introduces is a hotspots document quietly
  describing a superseded run, so the document must cite its source's sha256

Verified by scenario, not assertion. With a consistent second profile present
(`suite-durations-20261120.txt` + its hotspots doc) the file goes **81 passed**
— the parametrised tests simply expand to cover both. Removing that second
hotspots doc, or pointing it at the wrong sha, each reds
`test_the_latest_artefact_is_the_one_the_hotspots_document_cites`. The
scenario files were deleted; `git status --porcelain` confirms nothing left.

**N-002 — the unpinned constant.** `RENDER_HEAVY_SNAPSHOT` decides the
21.23 % that CARD-218/219 are now sized against, and dropping a path from it
survived all 74 tests. `--verify-render-set` already existed and nothing
called it. Added `test_the_frozen_render_set_still_matches_the_grep_that_
defines_it`, which calls `regrep_render_set(tests/)` and requires exact
agreement, plus `test_the_frozen_render_set_is_sorted_and_duplicate_free`.
New mutants **M14** (drop `tests/test_book_toc.py` from the snapshot) and
**M15** (unsort it) are both killed. Suite-wide: **15 mutants, 15 killed, 0
survivors.**

**N-001 — the contention argument was backwards.** The old caveat claimed the
sweep biased I/O-bound tests upward and so favoured the render hypothesis,
which lost. Wrong way round: the render set is in-process CPU work (176.82 s
call, 0.03 s teardown) while the **browser family is the wait-bound one**
(137.97 s of teardown blocked on another process), so CPU starvation inflates
the *winner*. Rewritten in both the hotspots document and the artefact header
around the two things that actually settle it:

- magnitude bound — ~4 min at 25 % rather than 76 % of a core is at most
  ~161 s of excess across the whole suite, against the **170.77 s** the
  family would have to shed to fall behind the render set (366.19 → 195.42);
- per-test teardown across all 422 browser tests — mean 0.327 s, median
  0.370 s, stdev 0.144 s, max 0.520 s, per-file means 0.198–0.413 s,
  histogram unimodal and massed at 0.3–0.5 s with no tail. A four-minute
  stall would have left a cluster of outliers. There is none, so the cost is
  structural.

**N-007 — two quotable figures.** The browser files' commit range ends
**2026-10-08T07:28Z**, not 04:19Z (I had sorted `+03:00` timestamps
lexically; the load-bearing "all after the wave-30 run" claim is unaffected).
And `tests/README.md`'s worked log line read 1071 s / 151 ms per test against
a real run of **931 s / 131 ms** — wrong arithmetic in the one document that
teaches the next person to re-measure. Both corrected, and the worked line's
timestamp aligned to the real 05:34:34Z.

Editing the artefact header changed its sha256
(`483c06b8…` → `7d204cf9…`); the hotspots document's citation was updated and
all 70 embedded ranking rows re-diffed against the script's stdout — identical.

**Also taken, unprompted (review bonus).** The browser family is defined
conservatively: three more files drive the same `browser_page` fixture
(`test_books_list_mobile.py` 4.71 s, `test_book_finalise_guide_preview_
layout.py` 2.78 s, `test_book_setup_print_mobile.py` 1.62 s), taking it to
375.30 s / **40.77 %**. Recorded as a caveat; the headline 39.78 % is the
floor and the margin is wider than stated, so no figure needed restating.

### Left open deliberately (per the coordinator)

- **N-004 — the file-share denominator is unpinned.** Real. Pinning derived
  shares is a design decision (which denominator is canonical, and what a
  future profile's shares are comparable *to*) and should not be rushed into
  a measurement card. Note for whoever takes it: `_pct` currently divides by
  attributed time, and the document says so at the point of use, so the
  present numbers are unambiguous — the gap is that nothing stops a later
  edit switching denominators silently.
- **N-005 — AC-5's two log tests skip off-host.** `meta/kanban/suite-timing.log`
  is gitignored (`*.log`), so a fresh checkout has none. Disclosed in the
  commit message and worked around by copying the main checkout's copy into
  the worktree so they run here. The format-contract tests (known-good /
  known-bad corpora, malformed detector) always run everywhere and carry the
  teeth; only the two "read the real log" tests are conditional.
- **N-006 — the admissibility check is blind to the contention that actually
  happened, and nothing calls it at profile time.** A known limit of the
  method: `is_admissible_profile` only reads what the header *claims*, and
  `other_pytest_processes` only sees competing **pytest** processes — neither
  would have noticed this run's macOS sweep, which was the contention that
  mattered. The solo-run guarantee is therefore "no competing suite", not "a
  quiet host"; the host-load caveat is prose, checked by a human, not a test.
  Anyone automating the next profile should sample load during the run rather
  than trusting the header.
- N-008 is a labelling point already handled by the existing labels.

- [Fix cycle 1 complete] 2026-10-15 — `492ac40`. 182 targeted tests pass; **15 mutants, 15
  killed**; **zero deleted lines across the whole card** against main (523/0, 21305/0, 253/0,
  112/0, 534/0), so G-1 is a fact about the diff rather than a claim.
  - **N-003 became four tests, and the replacement is better than the instruction.** The single
    `test_exactly_one_artefact_is_committed` is gone; in its place: at least one artefact
    exists, **every** committed artefact is well-formed (parametrised over all of them), every
    artefact has a dated hotspots document, and — the one that matters — **the latest artefact
    is the one the hotspots document cites, by sha256**. The agent's reasoning for that last
    one is the right reframing: in a multi-profile future the risk is not duplication, it is a
    hotspots document quietly describing a superseded run.
    **Verified by scenario rather than by assertion:** it created a consistent second profile,
    saw the file go to **81 passed** as the parametrised tests expanded to cover both, then
    deleted that profile's hotspots document and pointed its citation at a wrong sha — each
    reds the citation test. Scenario files removed and the tree verified clean afterwards.
  - **N-002: the render snapshot is pinned by the function that already existed.**
    `test_the_frozen_render_set_still_matches_the_grep_that_defines_it` calls `regrep_render_set`
    — written, working, and called by nothing — and requires exact agreement with
    `RENDER_HEAVY_SNAPSHOT`. Dropping `tests/test_book_toc.py` from the snapshot is now killed
    by it; unsorting the set is killed by both new tests.
  - **N-001: the caveat is rewritten in both the hotspots document and the artefact header**,
    around the two measurements that settle it — the ~161 s magnitude bound against the
    **170.77 s** the family would have to shed to fall behind (366.19 -> 195.42), and the
    per-test teardown distribution across all 422 browser tests (mean 0.327 s, median 0.370,
    stdev 0.144, max 0.520, per-file means 0.198–0.413, unimodal, no tail). As the agent puts
    it: a four-minute stall would have left a cluster of outliers, and there is none. All
    re-derived from the artefact rather than transcribed from the review.
  - **N-007: both figures corrected, and the agent found the cause of its own slip** — it had
    sorted `+03:00` timestamps **lexically**, so `zoom` (10:28+03:00 = 07:28Z) lost to
    `brush_menu` (07:19+03:00 = 04:19Z). The README's worked line now reads 931 s / 131 ms.
  - **Two knock-ons handled rather than left:** editing the artefact header changed its sha256,
    so the hotspots citation was updated and **all 70 embedded ranking rows re-diffed against
    the script's stdout — identical**, with determinism re-verified across two runs.
  - **The reviewer's bonus finding was taken as a caveat, not a restatement.** The three extra
    browser-driven files (`test_books_list_mobile.py` 4.71 s,
    `test_book_finalise_guide_preview_layout.py` 2.78 s, `test_book_setup_print_mobile.py`
    1.62 s) take the family to 375.30 s / **40.77%**, so **39.78% is now documented as a
    floor** — the margin over the render set is wider than stated, not narrower. No published
    figure needed changing, which is the right call.
  - **N-006 recorded as a known limit of the method**, and it is the one worth remembering: the
    solo-run guarantee is "no competing **suite**", not "a quiet host". Neither
    `is_admissible_profile` (which reads only what the header claims) nor
    `other_pytest_processes` (which sees only pytest) would have noticed the macOS sweep that
    actually contended with this run. Anyone automating the next profile should sample load
    **during** the run rather than trust the header.
  - N-004 and N-005 left with reasons in the notes; N-008 is a labelling point the existing
    labels already handle.
- [Note for the merge gate] This card adds 79 tests, so the gate should read **~7152 passed**,
  not 7073.

- [AC/EC/G gate] 2026-10-15 — **PASSED, no gating failure.** 22 further mutants (63 across the
  card now), 17 killed, 5 survivors — and the survivors cluster somewhere worth knowing about.
  `git status --porcelain -- src tests` empty; every scenario file removed by exact path and
  the directories re-listed.
  - **AC-3 verified the way a gate must.** The gate re-derived **every** figure in the
    conclusion from the artefact with its own parser — all 14 rows of the deciding table, the
    phase totals, the 10.4x gap, the top-50 share, the conservative-definition caveat, and the
    corrected commit-date range via `git log --diff-filter=A` — and every one matched. The
    claim four cards are now pointed by is the artefact's own arithmetic.
  - **The landmine is genuinely defused, and the gate extended the scenario rather than
    rebuilding it.** Reproducing the agent's scenario gave **exactly 81 passed**, with the two
    parametrised tests expanding by one each; deleting the second profile's document reds two
    tests, a wrong sha reds the citation test. The gate then added its own: **S4**, a newer
    profile whose document still cites the superseded run — the precise failure the test was
    reframed around — **killed**.
  - **The render snapshot is pinned in both directions.** Dropping a path reds with a message
    naming it (`added since freeze` / `gone since freeze`), and the gate's own probe — a new
    file containing `export_book` dropped into `tests/` — **also** reds. Symmetry is structural,
    not accidental.
  - **The rewritten contention caveat is correct, not merely different.** Both legs re-derived:
    render 176.82 s call / **0.03 s** teardown against the browser family's 137.97 s of 144.37
    (95.6%), so the wait-bound family is the browser one and CPU starvation inflates the
    winner; and the bound, 240 s at 25% = 60 CPU-s = 78.95 s wall, excess **161.05 s** against
    a **170.77 s** margin — charging every second of the sweep to the family still leaves
    205.19 s against 195.42 s.
  - **G-1 is a fact about the diff**: `--numstat` is 523/0, 21305/0, 253/0, 112/0, 534/0 —
    **zero deleted lines across the whole card**, and no pre-existing test file appears in the
    diff at all. The gate notes this is strictly stronger evidence than the card's own
    parenthetical "test", which resolves to nothing runnable and would need the full suite to
    check literally.
- [AC/EC/G gate — the findings, none gating, and the one that matters]
  - **F-1: nothing pins the hotspots document's body to the script's output.** Rewriting the
    headline in the prose (366.19 -> 166.19 s, 39.78% -> 19.78%) ships **79 passed**. So does
    falsifying a ranking row, and so does perturbing `_pct`'s denominator by 1%. The sha256
    citation pins **which artefact** the document derives from; it does not pin **what the
    document says about it**. Today's figures are right — checked twice, independently — so
    this is a regression risk rather than a defect, and it is six lines to close.
  - **The gate judged the orchestrator's deferral of N-004 "half honest", correctly.** The
    recorded reason addressed the denominator question, which genuinely is a design decision
    not to be rushed into a measurement card. But N-004's second half — "nothing checks the
    committed hotspots document against the script's output" — carries no design question at
    all, and the gate closed it by hand in one command. The reason as written let the design
    question carry a check that did not need it.
  - **F-2: the sha-citation test only checks `found[-1]`**, so a non-latest artefact's document
    can cite the wrong run unnoticed (scenario S5 survived). Harmless with one artefact; live
    the moment CARD-218 commits the second — which is the exact future N-003 was reframed
    around.
  - **F-3: `rank_files`'s tie-break is unpinned** while the identical one in `rank_tests` is.
    Not a live determinism hole (`sorted` is stable over an insertion order that is a pure
    function of the artefact), an untested asymmetry.
  - **F-4: "unimodal" is loose** — the histogram is `{0.0:41, 0.1:22, 0.2:37, 0.3:81, 0.4:141,
    0.5:100}`, strictly bimodal with a spike at ~0.0. The **load-bearing** half, "massed at
    0.3–0.5 with no tail", is exactly true, which is what the argument needs.
- [AC/EC/G gate — retro input, and the first one generalises past this card]
  - **63 mutants in, the five survivors cluster in exactly one place: derived numbers published
    in prose.** The code is well pinned; the committed document is pinned only by the hash of
    its input. **"Cite the source's hash" proves provenance, not arithmetic — they are different
    guarantees**, and every future measurement card needs both.
  - **"Verified by scenario, not by assertion" worked and should be reusable.** The agent's
    claim reproduced to the exact test count and the exact two reds, which made this gate cheap
    and let the gate *extend* the scenario instead of rebuilding it. A card that replaces one
    test with four should be expected to state its scenario and its numbers.
  - **A guardrail whose `(test: …)` is prose costs a gate cycle.** Cards whose guardrail is
    "change nothing" should cite the diff shape, which is better evidence and free.
  - **Self-contradicting cards are a merge-gate hazard**: this card carried both "74 tests /
    ~7147" and "79 / ~7152". Fix cycles must amend the earlier figure **in place**, not only
    append the corrected one. Done above.
