# CARD-217: Profile the suite once, serialized, and commit the duration record the curation cards work from

**Status:** ready
**Priority:** P1
**Category:** tech-debt
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/217-suite-duration-profile
**Worktree:** —
**Source:** owner request 2026-10-13 ("make cards for tests curation"), after the dispatcher's own cost analysis of `meta/kanban/suite-timing.log`
**Idea:** —
**Wave:** —
**Created wave:** 37
**Deferred waves:** 0
**Depends on:** —
**Touches:** meta/profiling/, meta/kanban/suite-timing.log, tests/README.md
**Review score:** —
**Started:** —
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

