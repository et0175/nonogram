# CARD-023: Narrow the supported grid range to 10..30 project-wide, with a measured 30x30 deadline fixture

**Status:** done
**Priority:** P1
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/023-grid-range-10-to-30
**Worktree:** ../PythonProject4-card-023
**Source:** meta/architecture/handoff.md#increment-5
**Idea:** —
**Wave:** 16
**Depends on:** —
**Touches:** src/nonogram/sourcing/random_grid.py, src/nonogram/sourcing/library.py, src/nonogram/sourcing/image.py, src/nonogram/difficulty.py, tests/test_timeout.py, tests/test_sourcing_random.py, tests/test_sourcing_library.py, tests/test_sourcing_image.py, tests/test_orchestrator.py, tests/test_cli.py, README.md
**Review score:** 8.0 (cycle 1/3, gates passed)
**Started:** 2026-08-31T07:40:00Z
**Closed:** 2026-08-31T08:30:00Z
**Actual:** 0.1d
**Merge commit:** 5e9f2de
**Blocked by:** —

## What to implement

CON-011 narrows the supported grid range from 10..50 to **10..30 inclusive**, project-wide
and for every source mode. This card makes that one change — the range only. Grid extent
stays a single scalar `size` here; the `(width, height)` pair is CARD-027's work.

The range is a **print-legibility** limit, not a performance one: beyond about 30 cells a
side the printed cell drops under ~6 mm (`docs/cell_size.md`, NFR-005) and stops being
comfortable to mark by hand.

Concretely:

1. **`src/nonogram/sourcing/random_grid.py`** — `MAX_SIZE = 50` becomes `MAX_SIZE = 30`.
   `MIN_SIZE` is unchanged at 10. The module docstring's statement of the supported range
   and `validate_size`'s error text move with the constant. This is the single normative
   definition; `library.generate` and `image.generate` already delegate to
   `random_grid.validate_size`, so both inherit the narrowing without restating it — keep
   it that way (ADR-0022/R2: one pure domain validator, inward of the CLI).
2. **`src/nonogram/difficulty.py`** — `MAX_SUPPORTED_CELLS = 50 * 50` becomes `30 * 30`,
   and the two docstrings that spell the range as "10x10..50x50" (lines ~256 and ~406)
   move with it. **Only the constant moves.** Whether area is the right normalizer for a
   rectangle is a deliberately open question that no card in this increment decides — see
   G-3.
3. **Stale range prose in the sourcing modules** — `library.py`'s "supported 10..50 range"
   and `image.py`'s "at 10..50 cells there is no resolution to spare". Both are normative
   statements about the supported range in modules this card owns; update them.
4. **The deadline fixture (AC-084) — a MEASUREMENT, not a substitution.** See below.

### The AC-084 measurement — the known breakage this card exists to own

`tests/test_timeout.py` is AC-038's fixture and uses `size=50` in **four** places (lines
167, 193, 218, 239). At `MAX_SIZE = 30` those requests become *invalid*: they fail with
`SizeOutOfRange` **before the solver is ever entered**, so the file would go red and the
ADR-0011 cooperative-deadline mechanism would look broken when it is not.

AC-038 is superseded by AC-084, which asks for a **30x30 request using a seed measured to
drive the solver past the deadline**. Replacing `50` with `30` and hoping is not the task.
The task is:

- Find, by measurement, a `(seed, density)` inside 30x30 whose solve genuinely exceeds the
  30s budget — the mid-density band is the known-hard class (CARD-004's performance
  findings; CARD-018 subsequently strengthened line logic, so the old 50x50 parameters are
  not a guide to what is hard at 30x30 today).
- Record in `## Worktree notes` **what was measured**: the seeds tried, the densities, and
  the observed times. The next person to disturb this fixture — it has now been disturbed
  three times (CARD-006 built it, CARD-018 re-checked it, this card breaks it) — must not
  have to rediscover the search.
- Rename the class and its module docstring header from `TestGenerate_50x50_...` to
  `TestGenerate_30x30_RespectsTimeoutBound`, and update the AC reference AC-038 -> AC-084.
- Keep BOTH halves of the fixture: the "solver *can* finish, returns a real exportable
  puzzle" case and the "solver *cannot* finish, raises `SolverTimeout`" case.

⚠ **If no 30x30 seed exceeds the budget** within a reasonable search, that is a finding,
not a licence to fake one. Raise `[BLOCKER]` and escalate to the decompose station (G-6).
Do not monkeypatch the deadline down, do not weaken the solver, do not delete the
"cannot finish" half.

### Other sites this narrowing breaks — schedule them, do not discover them

- `tests/test_sourcing_image.py:312` — asserts `random_grid.MAX_SIZE == 50` directly.
- `tests/test_orchestrator.py:425` — a literal error string, `SizeOutOfRange("grid size
  must be between 10 and 50")`.
- `tests/test_cli.py:302` — `("--size", "51")` as the "one past the maximum" case in the
  ADR-0010 "argparse parses, it does not judge" table. 51 is still out of range at
  `MAX_SIZE = 30`, so the test still passes — but it no longer *means* what it was written
  to mean. Move it to `31`.
- `tests/test_sourcing_random.py` lines 72 and 112 use `random_grid.MAX_SIZE` /
  `MIN_SIZE` symbolically and follow the constant automatically. Confirm they still assert
  something (a boundary test that reads the constant it is testing proves less than one
  that names the number — consider pinning `30` explicitly beside the symbolic use).
- `README.md` — wherever it documents `--size`'s supported range.

## Acceptance criteria

- **AC-084** (NFR-001, supersedes AC-038)
  - given: a 30x30 random-grid generation request (the largest supported grid under
    CON-011) using a seed measured to drive the solver past the deadline
  - when: generation runs
  - then: it completes within 30s or fails clearly with a `SolverTimeout` error
    (cooperative deadline enforced inside the solver — ADR-0011) — it never hangs
    indefinitely
  - kind: boundary
  - test: `TestGenerate_30x30_RespectsTimeoutBound`

Note on AC-068/AC-069/AC-070 (FR-019's boundary criteria at 30): those are phrased over a
`(width, height)` pair and belong to CARD-027, which introduces the pair. This card is
verified at the scalar boundary by the existing `validate_size` tests, re-pinned to 30.

## Engineering constraints

- **EC(ADR-0022/R2):** For every source mode (random, built-in library, uploaded image), a
  requested size outside 10..30 is rejected by the one shared pure domain validator before
  any grid is produced, and the CLI applies no range check of its own — for every integer
  in a wide band around both bounds, not only for the four hand-picked examples.
  test: `PropertyTest_SizeRange_EverySourceModeRejectsSizeOutside10To30`

  (CARD-027 generalizes this property to independent width and height under EC-005's name,
  `PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30`; this card's
  scalar version is its predecessor, not a duplicate to keep alongside it.)

## Guardrails

- G-1: Do not edit `src/nonogram/clues.py`, `src/nonogram/solver/**` — COMP-004 and
  COMP-005 need no change for this increment; the range is a property of the request, not
  of the solver (test: PropertyTest_Solver_NeverFalsePositiveUniqueness).
- G-2: ADR-0001's numbers are unchanged. The 30s hard deadline and the 5s p95 budget for
  <=20x20 keep their values — only NFR-001's *size ceiling* moves (50x50 -> 30x30), and
  ADR-0001 is not reopened by this (test: BenchGenerate_20x20_p95Under5s).
- G-3: Out of scope — do not change `difficulty.py`'s area-based normalizer (`total_cells`,
  `size_pressure`) or the tier weights. Only the `MAX_SUPPORTED_CELLS` constant moves with
  the range. Whether area is the right normalizer once grids are rectangular is
  deliberately left open by the increment and is decided by no card here (test: the
  existing tests/test_difficulty.py and tests/test_difficulty_tiers.py suites).
- G-4: Out of scope — grid extent stays one scalar in this card. Do not introduce a
  `(width, height)` pair, `--size NxM` parsing, or a `validate_extent` function; those are
  CARD-027's (FR-018, ADR-0022/R1).
- G-5: Do not edit `src/nonogram/export/**`, `src/nonogram/orchestrator.py`,
  `tests/test_export_json.py`, `tests/test_export_csv.py`, `tests/test_export_image.py`,
  `tests/test_export_pdf.py`, `tests/property/test_export_roundtrip.py` — owned by CARD-024
  and CARD-025 this wave. (`orchestrator.py:177`'s `DEFAULT_DEADLINE` docstring still says
  "50x50 maximum size"; it is updated by CARD-027, which owns that file.)
- G-6: The AC-084 fixture must be MEASURED. Do not substitute a monkeypatched or shrunken
  deadline for a real 30x30 seed, do not weaken the solver or the deadline to manufacture a
  timeout, and do not drop the "solver cannot finish" half of the fixture. If no seed
  inside 30x30 exceeds the 30s budget, raise `[BLOCKER]` and escalate rather than editing
  the mechanism under test (test: TestGenerate_30x30_RespectsTimeoutBound).

## System contract

- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its
  current solution grid (US-004, FR-005). (check: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has
  confirmed exactly one solution (US-005, FR-011). (check:
  TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF)
- INV-003 — A puzzle's automatic-retry counter (regenerate attempts for random/library
  mode, resample attempts for difficulty matching, or pixel-nudge attempts for image
  mode) never exceeds its configured maximum bound (NFR-002). (check:
  TestNudge_ReportsFailureAtCap, TestRegenerate_StopsAtMaxRetryBound,
  TestResample_StopsAtMaxRetryBound, TestRetryLoop_BoundedIterations)
- INV-004 — A puzzle's grid width and height each lie within 10..30 cells inclusive, in
  every source mode and at every point in its regenerate/resample/nudge lifecycle
  (US-016, CON-011, FR-019). (check: TestGenerateRandom_AcceptsMaxSide30,
  TestGenerateRandom_RejectsSideAbove30, TestGenerateRandom_RejectsSideBelow10)
- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted
  as unique must never actually have 0 or more than 1 solutions. This is the mandatory
  correctness property the whole tool depends on. (check:
  PropertyTest_Solver_NeverFalsePositiveUniqueness)
- CON-009 — The web UI's HTTP server binds its listening socket to 127.0.0.1 (loopback)
  only, and refuses connections arriving on any other interface. Restates NFR-003/AC-052
  as a gate-enforced mandatory constraint — a `check:` the system contract actually
  collects — so BCON-0001's socket-reach half is discharged by more than a threshold
  visible only in requirements.yml. (check: TestWebServer_BindsLoopbackOnlyByDefault)
- CON-010 — The web UI's HTTP server refuses any request the browser itself marks as
  cross-site (a Sec-Fetch-Site value other than same-origin/none, or an Origin header
  naming a non-loopback host), and refuses any absolute-form request target whose
  authority is not a loopback name (NFR-004). Restates NFR-004 as a gate-enforced
  mandatory constraint — a `check:` the system contract actually collects — so
  BCON-0001's browser-mediated-reach half is discharged too, not only its socket-reach
  half (CON-009): binding to 127.0.0.1 alone does not stop this, since a browser sets
  Host from the request's target url, not from the page's origin. (check:
  PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest)
- CON-011 — Each grid side is 10 to 30 cells inclusive. 30 replaces 50 as MAX_SIZE
  project-wide and applies to every source mode (random, built-in library, uploaded
  image) and to both inbound adapters (CLI and web UI). This supersedes the 10..50 range
  FR-001 carried; FR-001 is marked status: superseded, superseded_by: FR-019, and FR-019
  restates the behaviour over the narrowed range. (check:
  PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30)
- CON-012 — A generation request whose grid aspect ratio differs from the uploaded
  source image's by more than 2x is refused with an explanatory error rather than
  converted (FR-021). The centred crop of FR-020 retains exactly min(r_src, r_tgt) /
  max(r_src, r_tgt) of the source with r = width/height, so this is exactly the rule
  "never silently discard more than half the user's picture". Retaining exactly 50% (a
  ratio difference of exactly 2x) is ACCEPTED — the boundary is inclusive. (check:
  PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore)
- ADR-0019/R1 — The web UI adapter (src/nonogram/web/) contains HTTP concerns only —
  routing, form rendering, request parsing, and mapping onto
  orchestrator.GenerationRequest — and no domain logic or validation, mirroring cli.py;
  it may import the orchestrator but no capability module may import it or cli.py.
  (check: test_every_import_in_the_package_points_inward)
- ADR-0022/R1 — Grid extent crosses module boundaries as a (width, height) pair. No
  public function signature, request field, or export field reduces a grid's extent to a
  single scalar "size", and no source mode constructs a grid from one integer. (check:
  review-lens)
- ADR-0022/R2 — Each grid side is validated to 10..30 inclusive, as a pure domain
  function inward of the CLI adapter, for every source mode. The CLI parses the --size
  NxM form but never enforces the range itself. (check:
  TestValidateExtent_RejectsSideAboveThirty)
- ADR-0022/R3 — An uploaded image is fitted to the requested grid's aspect ratio by a
  centred crop, never by stretching and never by padding. A request whose grid and
  source aspect ratios differ by more than 2x is refused rather than cropped. (check:
  TestFitImage_RefusesRatioMismatchBeyondTwice)


## Architecture context

- **FR:** FR-019, NFR-001
- **NFR:** NFR-001, NFR-005 (rationale only — the print-legibility reason for the 30 bound)
- **CON:** CON-011
- **ADR:** ADR-0001, ADR-0010, ADR-0011, ADR-0022
- **Components:** COMP-003, COMP-006
- **Trace:** meta/architecture/trace.yml

## Worktree notes


- **[Env]** forge 2026.8.17 (meets `forge.min_version: 2026.8.17`, skew gate clean).
- **[Drift gate]** ⚠ unprocessed external drift touches two of this card's files —
  `src/nonogram/difficulty.py` and `src/nonogram/sourcing/random_grid.py` have
  events in `meta/drift-pending.yml` (dated 2026-08-27/28, i.e. predating the
  CARD-018 and CARD-022 merges). `drift.gate` is unset, so the default `warn`
  applies: proceeding, noted rather than blocking. The events look stale rather
  than live, but nobody has reconciled them — `/forge:reverse drift` would clear
  the signal.

### CARD-023 implementation (python-pro)

#### The AC-084 measurement search

Method: the technique the file already uses — real request, real grid, real
clues, real solver; only `orchestrator.GENERATION_BUDGET_SECONDS` scaled. Two
passes: a coarse sweep at a 2 s budget to find the hard band, then a
confirmation pass at ADR-0001's real 30 s, then a per-candidate solve
measurement to prove the timeout is one hard solve rather than accumulated
retries. All numbers on darwin/arm64, CPython 3.14.3, `size=30`, `mode=random`.

**Pass 1 — coarse sweep, budget 2.0 s, densities 40/45/50/55/60 x seeds 0..19
(100 requests).**

| density | result |
|---|---|
| 40 | 20/20 timed out at 2.0 s |
| 45 | 20/20 timed out at 2.0 s |
| 50 | 19/20 timed out at 2.0 s; seed 10 finished in 0.588 s (4 attempts) |
| 55 | 20/20 finished, all under 0.4 s |
| 60 | 20/20 finished, all under 0.4 s |

**Pass 2 — confirmation at the real 30 s budget.**

| density | seed | outcome |
|---|---|---|
| 40 | 0,1,2,3,4 | `SolverTimeout` at 30.000 s (all five) |
| 45 | 0,1,2,3,4 | `SolverTimeout` at 30.000 s (all five) |
| 50 | 0 | `GenerationAbandoned` after 20 attempts, 7.34 s |
| 50 | 1 | `GenerationAbandoned` after 20 attempts, 7.44 s |
| 50 | 2 | `GenerationAbandoned` after 20 attempts, 10.21 s |
| 50 | 3 | `GenerationAbandoned` after 20 attempts, 10.65 s |
| 50 | 7 | finished in 5.13 s, 8 attempts, unique |
| 75 | 1 | finished, unique, first candidate |

**Pass 3 — is it one hard solve, or twenty easy ones?** Reproduced each
request's *first* candidate (`random_grid.generate(30, d, random.Random(seed))`,
exactly how `orchestrator.generate` draws it) and solved that one grid alone
with a 60 s deadline:

| density | seed | first candidate alone |
|---|---|---|
| 40 | 7 | **still running at 60 s** |
| 40 | 0 | **still running at 60 s** |
| 45 | 0 | solved in 57.75 s (2 solutions, 2930 branch nodes) |
| 50 | 7 | solved in 0.037 s (2 solutions, 25 branch nodes) |
| 75 | 1 | solved in 0.003 s (1 solution, 0 branch nodes) |

**Settled on: `size=30, density=40, seed=7`.** Density 40 is the measured hard
class at 30x30 and its *first candidate alone* outruns 60 s — twice ADR-0001's
whole budget — so the scaled-down 0.25 s budget expires on real solver work,
inside the first solve, with no retry accumulation in the story. Seed 7 keeps
continuity with the fixture CARD-006 wrote; nothing distinguishes it (every
seed measured at density 40 outran the budget), and that is recorded in the
constant's comment so the next person does not think it is magic.

**The finding worth carrying forward:** density 50, CARD-004's hard class at
50x50 and the value this fixture used since CARD-006, is *easy* at 30x30 after
CARD-018 — candidates solve in tens of milliseconds and the request ends in
`GenerationAbandoned` (no unique grid in 20 tries), not `SolverTimeout`.
Substituting 30 for 50 and keeping density 50 would have produced a red test
with a confusing error, or worse, a passing one for the wrong reason. The
hard band at 30x30 today is roughly **density 40-45**; 55+ is line-solvable.

**Overshoot re-measured at 30x30** (the number the module docstring quotes):
0.335 / 0.380 / 0.708 ms past a 250 ms budget, over three runs.

**Anti-vacuity guard added.** `test_the_hard_fixtures_first_candidate_alone_outruns_a_budget`
reproduces the first candidate and asserts the solver cannot finish it inside
1.0 s (60x under the measured >60 s). This fixture has now been disturbed three
times; the next solver improvement that makes seed 7 easy will turn this test
red with a docstring saying *re-measure*, instead of silently hollowing out the
timeout half. Cost: ~1 s of suite time.

#### What changed

Source (the narrowing itself):

- `src/nonogram/sourcing/random_grid.py` — `MAX_SIZE = 50` -> `30`; `MIN_SIZE`
  untouched. Module docstring now states 10..30 explicitly and names itself the
  single normative definition (ADR-0022/R2); the `MIN_SIZE`/`MAX_SIZE` comment
  carries CON-011's print-legibility rationale (NFR-005). `validate_size`'s
  error text already interpolated the constants, so it moved for free.
- `src/nonogram/difficulty.py` — `MAX_SUPPORTED_CELLS = 50 * 50` -> `30 * 30`
  and the two "10x10..50x50" docstrings (~256, ~406). Nothing else: the
  area-based normalizer, `size_pressure` and the tier weights are untouched
  (G-3). The stale `docs/requirements.md decision 6` citation on that constant
  was repointed at CON-011, which is the norm that actually governs now.
- `src/nonogram/sourcing/library.py` — the "supported 10..50 range" paragraph.
  Its arithmetic moved with the range: exact magnifications of the 16-cell
  template inside 10..30 are now **16 alone** (was 16/32/48), and "the other 38
  supported sizes" became "the other 20" (21 supported sizes, one degenerate).
- `src/nonogram/sourcing/image.py` — "at 10..50 cells" -> "10..30", and the
  `square_crop_box` docstring's "resized to at most 50 cells" -> 30.
- No restatement of the range was added to `library.py` or `image.py`; both
  still delegate to `random_grid.validate_size` (ADR-0022/R2 kept).

Tests, the sites the card scheduled:

- `tests/test_timeout.py` — the AC-084 rework above. Class renamed
  `TestGenerate_50x50_...` -> `TestGenerate_30x30_RespectsTimeoutBound`, module
  docstring header AC-038 -> AC-084 with a paragraph on why the size moved and
  what was measured, `HARD_DENSITY` 50 -> 40 with the measurement recorded in
  its comment, new `HARD_SEED`/`MAX_SUPPORTED_SIZE`/`_hard_request()` so the
  four request sites are one definition. **Both halves kept**: the can-finish
  case still runs unmocked under the real 30 s budget and asserts a verified,
  exportable, 30-cell puzzle; the cannot-finish case still raises
  `SolverTimeout`.
- `tests/test_sourcing_image.py` — `MAX_SIZE == 50` -> `== 30`; the shared-rule
  parametrization gained `31` (`[9, 31, 51, None]`); the AC-009 dimension sweep
  `[10, 17, 25, 50]` -> `[10, 17, 25, 30]`.
- `tests/test_orchestrator.py` — the literal `"grid size must be between 10 and
  50"` -> `10 and 30`.
- `tests/test_cli.py` — `("--size", "51")` -> `("--size", "31")`, so the
  "one past the maximum" row means one past the maximum again.
- `tests/test_sourcing_random.py` — the two AC boundary tests renamed to the
  30 vocabulary (`..._accepts_max_side_30`, `..._rejects_size_above_30`) and,
  per the card's note, they now **name the number as well as read the
  constant**: `assert random_grid.MAX_SIZE == 30` beside the symbolic use, and
  the above-range case checks both 31 (one past) and 60 (the size AC-003 was
  written around). Size corpora retargeted: `[10, 11, 25, 49, 50]` ->
  `[10, 11, 25, 29, 30]`, `(10, 11, 17, 20, 33, 49, 50)` ->
  `(10, 11, 17, 20, 23, 29, 30)`, `[10, 20, 50]` -> `[10, 20, 30]` (x2), and
  the out-of-range parametrization gained `31`.
- `tests/test_sourcing_library.py` — `DEGENERATE_SIZES` now derives from
  `random_grid.MIN_SIZE/MAX_SIZE` (it was a hard-coded `range(10, 51)`), which
  makes it `(16,)`; the two tests reading it updated (counts 38/41 -> 20/21,
  `assert size in (16, 32, 48)` -> `assert size == 16`) and pinned to the
  literal 10..30 alongside the symbolic range, same reasoning as above.
  `test_an_exact_magnification_replicates_the_template_block_by_block` now
  drives `library.render(template, 32, CANONICAL_THRESHOLD)` instead of
  `library.generate("house", 32, ...)`: 32 is no longer a requestable size, and
  16 — the only exact magnification left in range — is the identity, which
  would prove nothing about block replication. The geometry core is documented
  as taking an already-validated size, so the multiplication is now exercised
  where it lives while the request range stays enforced by the tests that own
  it.

New test:

- `tests/property/test_size_range.py` — the EC's named property test,
  `PropertyTest_SizeRange_EverySourceModeRejectsSizeOutside10To30`, which did
  not exist. Per CLAUDE.md there is no `hypothesis`: it builds a seeded corpus
  with `random.Random` — every integer in `range(-20, 81)` plus 120 seeded
  far-away magnitudes — and asserts a minimum case count inside the test so the
  corpus cannot silently shrink. For all three source modes it asserts (a)
  every out-of-range integer is refused, (b) the refusal message is *byte for
  byte* `random_grid.validate_size`'s, which is what distinguishes "shares the
  one validator" from "raises the same exception class", (c) `None` is a domain
  error and not a `TypeError`, (d) every in-range integer is accepted and gives
  a grid of exactly that size, and (e) the CLI parses every one of those
  integers unchanged, so no part of the range is enforced at the adapter
  (ADR-0010, ADR-0022/R2). Each mode is called with real arguments (a real
  template key, a real image fixture), so a refusal cannot be an artefact of a
  missing input. Runs in 0.26 s.

#### Deviations from the predicted `Touches:`

- `SCOPE+ tests/property/test_size_range.py` — the card's engineering
  constraint names `PropertyTest_SizeRange_EverySourceModeRejectsSizeOutside10To30`
  as its `test:`, and no such test existed anywhere in the tree. An AC/EC whose
  named test does not exist is not satisfied, so it was written. New file, no
  existing test removed or weakened.
- `README.md` was in `Touches:` but **needed no change**: it documents the
  install and the doc index only, and never states `--size`'s range. Left
  untouched rather than edited for the sake of the list.
- `tests/test_sourcing_library.py` was in `Touches:` and did need changes, but
  more of them than the card anticipated (the whole file was built on a
  hard-coded `range(10, 51)` and on 32/48 being requestable) — detailed above.

#### Out of scope, deliberately left (flagged, not fixed)

- `docs/requirements.md` still says "10x10 up to 50x50" (line 47) and
  "Grid size limits | 10x10 to 50x50 (FR-1)" (line 150). It is the raw intake
  spec, not in `Touches:`, and CON-011/FR-019 supersede FR-001 in
  `requirements.yml` — but it is now the last place in the repo asserting the
  old range and will read as a contradiction. Worth a follow-up card or an
  intake amendment.
- `docs/cell_size.md`, cited by the card as NFR-005's rationale, **does not
  exist** in the tree. The `MAX_SIZE` comment therefore cites NFR-005 by name
  rather than a dangling path.
- Untouched per G-1/G-5, all still carrying "50x50" prose that CARD-024/025/027
  own: `src/nonogram/orchestrator.py:177` (`DEFAULT_DEADLINE`),
  `src/nonogram/solver/{search,propagate}.py`,
  `src/nonogram/export/{layout,svg,json_export}.py`, and the export tests plus
  `tests/property/test_export_roundtrip.py`. Note that
  `test_export_roundtrip.py`'s `_EDGE_SIZES = (1, 2, 3, 10, 49, 50)` is
  deliberately *outside* the request range already (it draws grids directly,
  not through `random_grid.generate`), so the narrowing does not break it —
  but its docstring's "10x10..50x50 request range" is now stale.
  `tests/property/test_solver_uniqueness.py:105` has the same stale sentence
  for the same reason.

#### Guardrail compliance

- **G-1** `clues.py` / `solver/**` untouched (`git diff --stat` confirms).
- **G-2** ADR-0001's numbers unchanged: `GENERATION_BUDGET_SECONDS` is still
  30.0 and its pinning test still asserts that literal.
- **G-3** only `MAX_SUPPORTED_CELLS` moved in `difficulty.py`; `total_cells`,
  `size_pressure` and the tier weights are byte-identical.
- **G-4** grid extent is still one scalar `size`; no `(width, height)` pair, no
  `--size NxM`, no `validate_extent`.
- **G-5** `export/**`, `orchestrator.py` and the five export test files
  untouched.
- **G-6** the fixture is MEASURED (three passes above), the deadline was not
  monkeypatched lower than the file's pre-existing `SHORT_BUDGET_SECONDS = 0.25`
  (unchanged), the solver was not weakened, and the "cannot finish" half is
  intact — plus a new premise test that fails loudly if it ever becomes vacuous.

#### Suite

`./.venv/bin/python -m pytest` -> **1299 passed, 1 xfailed** in ~35 s
(baseline before this card: 1292 passed, 1 xfailed; net +7 = +9 from the new
property file, +1 premise test, -3 from parametrizations that lost out-of-range
cases). No test was skipped, xfailed or deleted to get there.

### Orchestrator notes

- **[Scope]** Independently confirmed. G-1 clean (`clues.py`, `solver/**` absent
  from the diff). G-2 clean (`GENERATION_BUDGET_SECONDS` still 30.0,
  `SHORT_BUDGET_SECONDS` still 0.25 — the fixture was made hard by measurement,
  not by dialing the budget down). G-4 clean (0 width/height additions — extent
  is still a scalar, CARD-027's work did not leak in).
- **[Build gate]** PASSED — full suite independently re-run in the worktree's own
  venv: **1299 passed, 1 xfailed**, exit 0 (baseline 1292/1).
- **[AC-084 verification]** The measurement was re-derived from scratch rather
  than accepted. Reproducing the fixture's first candidate and solving it alone:
  `SolverTimeout after 45.00s` — the first candidate outruns 45s, i.e. one and a
  half times ADR-0001's entire 30s budget. Genuinely hard, not manufactured.
  The agent's headline finding also reproduces, and is the reason this card
  needed a measurement rather than a substitution. At 30x30 seed 7:
  density 50 (the OLD fixture's density) solves in **0.039s**; density 45 in
  18.2s; density 40 times out. So the naive fix — swap 50 -> 30 and keep density
  50 — would have produced a fixture solving in 39 MILLISECONDS while claiming
  to exercise "the solver cannot finish in time". A ~500x miss. CARD-018's
  probing/restart work moved the hard band at 30x30 down to ~40-45%; 50%+ is now
  line-solvable.

- **[Review 1/3]** Score: 8.0 — crit: 0, imp: 2. Report:
  `meta/review/20260831T064006Z-CARD-023-cycle1.yml` (synced from worktree).
  Score clears min_score 8 but the SEVERITY GATE blocks on Important findings,
  so this goes to a fix cycle regardless of score.
  System contract: 13 rules checked, 2 ✓ holds, 11 ⚠ unchecked (9
  no_eligible_fact; 2 check_ref_missing — CON-011 and ADR-0022/R2 both name
  pair-shaped successor checks that are CARD-027's work), 0 ✗ violated.
  All 6 guardrails verified. AC-084 confirmed satisfied BY MEASUREMENT: the
  reviewer bounded the fixture's first candidate at **≥150s still running** — 5x
  ADR-0001's budget, better than the ≥60s the implementer recorded.
- **[Bookkeeping]** ⚠ My own error, found by the reviewer: the notes sync
  appended the worktree's ENTIRE card file rather than just its notes section,
  duplicating every section from `## What to implement` to `## Architecture
  context`. A parser reading "the last section of each name" would have got the
  duplicate instead of the implementer's notes. Rebuilt: card proper + the
  agent's real notes + these orchestrator notes, verified by section-header
  counts (1 each) and by confirming every distinctive note survived. Backup of
  the corrupted version kept in the session scratchpad.
- **[Review sync]** 1 report(s) → meta/review/.
- **[Adversarial]** F-001 CONFIRMED as a real gap but **re-graded Important →
  Minor**, and the review's own numbers corrected: the recorded bound is >60s
  (2x the budget), not the ≥150s/5x the review claimed from its own probe, so
  the blind window needs a **30-60x** solver improvement rather than 5-150x —
  a materially smaller exposure. The skeptic also established the test never
  goes vacuous inside that window: at 8s per candidate the 0.25s scaled budget
  still expires mid-solve on real work. What becomes false is the guard's
  docstring claim, not the mechanism it guards.
- **[Adversarial]** F-002 CONFIRMED on facts but **re-graded Important → Minor**.
  The loop is a plain nested `for`, not a `parametrize`, so the duplicated 900
  re-runs a byte-identical assertion — no case count or test id collapses, and
  min/interior/max still sweep all five densities. CLAUDE.md's "corpus can't
  silently shrink" rule governs SEEDED RANDOM corpora; this is a hand-enumerated
  deterministic sweep, so the spirit applies but not the letter. One genuinely
  false sentence (the "50x50 ... largest supported grid" docstring).
- **[Severity gate]** 0 CONFIRMED critical, 0 CONFIRMED important after
  adversarial verification (both Importants re-graded to Minor by independent
  skeptics). Score 8.0 >= min_score 8. **Gate PASSES** — no fix cycle required.
  The two Minors are fixed anyway below: they are cheap, in scope, and this card's
  own subject is the accuracy of range statements.
- **[Scope finding]** The F-002 skeptic surfaced something larger than the
  finding it was checking: **12 files still assert the old 10..50 / 50x50 range**.
  CARD-023 is FORBIDDEN from fixing most of them — G-1 blocks
  `solver/{propagate,search}.py`, G-5 blocks `export/{layout,svg,json_export}.py`
  and `orchestrator.py`. Five more sit in test files outside this card's
  `Touches:`. This is cross-cutting cleanup that needs its own card; absorbing it
  here would breach two guardrails. Raised as a follow-up rather than done.
- **[Follow-up cut]** CARD-029 created for the stale-range sweep this card's
  guardrails blocked (P3, 0.25d, trivial, depends CARD-023 + CARD-025). It
  covers 6 source files and 4 test files plus `docs/requirements.md`.
  Two deliberate exclusions recorded on it: `export/layout.py` goes to CARD-025
  instead (that card already owns the file and is rewriting its cell-size rule,
  so two cards editing it back to back is the overlap the dispatcher exists to
  prevent) — and the four HISTORICAL "50x50" references this card wrote to
  explain the narrowing must survive, since a blind find-and-replace would
  destroy exactly the record that makes the next range change safe.
  Verified before cutting: this is documentation drift, NOT a numeric defect.
  `_CLUE_FONT_RATIO = 0.62` is sized for a two-digit clue and 30 is still two
  digits, so every constant justified by "50" remains correct at 30.
- **[8h spot-check]** 2/2 sampled holds reproduced (INV-004, ADR-0019/R1) by an
  independent skeptic re-deriving each verdict's cited evidence: constants print
  10/30; `library.py:349` and `image.py:310` both call `random_grid.validate_size`
  with no restated bounds, and `random_grid.py:86` is the SOLE `SizeOutOfRange`
  raise site in `src/`; 266 tests across four suites, exit 0; the structural
  guard 14 passed over a verified non-empty 29-module walk that excludes
  `tests/`. Its own AST scan found 16 cross-component edges with one flagged —
  `cli.py -> web`, the documented `_LAUNCH_EDGE` exemption, pre-existing on main.
  **It also found a latent defect neither review nor implementation caught**:
  `difficulty.py:261-262` restates the range as `10*10`/`30*30` and had to be
  HAND-SYNCED in this diff, with no test binding it to `random_grid.MAX_SIZE`.
  Not a second gate (it clamps, never raises — so INV-004 still holds), but a
  second definition that can drift silently. Fixed in `64f0fda`; see below.
- **[AC/EC check]** GATE: **8 verified, 0 violated, 0 unverified**. An
  `## Engineering constraints` section exists (one item).
  AC-084 verified by independent measurement, not assertion: the fixture's first
  candidate does NOT finish at a 25s ceiling, while the naive substitution
  (density 50, seed 7) finishes in **41.6ms with 2 solutions** — so it would
  have ended in `GenerationAbandoned`, not `SolverTimeout`. ~600x miss.
  The "can finish" half asserts a real puzzle (`ready_for_export`,
  `solution_count == 1`, 30 rows), not merely the absence of an exception.
  EC(ADR-0022/R2) proved non-vacuous **by mutation**: a plugin restoring
  `MAX_SIZE = 50` turned all three source modes red with "DID NOT RAISE".
  G-6 verified by `git show main:` comparison — `GENERATION_BUDGET_SECONDS`
  30.0 and `SHORT_BUDGET_SECONDS` 0.25 both byte-identical to main. The only
  budget-shaped constant ADDED is `PREMISE_BUDGET_SECONDS = 1.0`, a guard rather
  than a lowered deadline. G-1/G-3/G-4/G-5 all verified mechanically.
- **[Scope]** ⚠ Two deviations from the predicted `Touches:`, both recorded late
  and now committed in `64f0fda`:
  `SCOPE+ tests/test_difficulty.py` — edited by the cycle-1 fix for F-002's
  sweep collapse. G-3 names that suite as its own `test:`, so the edit is in
  scope, but I did not log the deviation when I made it; the AC/EC gate flagged
  the gap independently.
  `SCOPE+ tests/property/test_size_range.py` — already declared by the
  implementer as the EC's missing named test; the spot-check's drift finding
  added one more test to it.

- **[Merge]** Merged to main as `5e9f2de` (--no-ff). Merge gate: full suite on the
  MERGED tree = **1300 passed, 1 xfailed**, matching the branch result.
  128 staged user files (pic1/ x47, pictures/ x21, docs/, templates/) were
  unstaged before the merge so the merge commit could not sweep them in, then
  restored — including the four files carrying a staged/worktree split, each
  verified byte-for-byte against its pre-merge backup. The branch touched none
  of them (verified by set intersection before merging).
