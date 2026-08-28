# CARD-005: Pipeline orchestrator and regenerate-on-failure loop

**Status:** review
**Priority:** P1
**Category:** feature
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/005-orchestrator-regenerate-loop
**Worktree:** ../PythonProject4-card-005
**Source:** meta/architecture/handoff.md#increment-1
**Idea:** —
**Wave:** 4
**Depends on:** CARD-003, CARD-004
**Touches:** src/nonogram/orchestrator.py, tests/test_orchestrator.py
**Review score:** —
**Started:** 2026-08-28T07:22:29Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

COMP-002 (Pipeline Orchestrator) — the thin layer that owns the `Puzzle` aggregate
(AGG-001) and is the **single enforcement point** for its invariants (ADR-0007). Every
later card that adds a loop (difficulty resample CARD-010, pixel nudge CARD-016) extends
this module, so the shape laid down here is the shape they copy.

1. **The `Puzzle` aggregate.** One instance per generation request, carrying mode, size,
   density, grid, clues, uniqueness verdict, retry counters, and the `ready_for_export`
   flag. It is **not** re-created per retry — that is exactly why INV-003's retry counter is
   one invariant on one aggregate (see aggregates.yml AGG-001).
2. **The generation pipeline.** `source grid (CARD-003) → compute clues (CARD-002) →
   solve for uniqueness (CARD-004) → mark ready`. Inject the seeded `random.Random`
   (ADR-0015) built from the `--seed` flag so the whole pipeline is reproducible.
3. **POL-001 AutoRegenerateOnUniquenessFailure (FR-007).** When the uniqueness check
   reports `solution_count != 1` in random/library mode, discard the candidate and generate
   a new one automatically — no user interaction.
4. **POL-005 AbandonAfterMaxRetries + INV-003 (NFR-002).** The loop is bounded at
   **20 attempts** (ADR-0002). At the bound, abandon with a clear `GenerationAbandoned`
   error rather than retrying again. Implement the bound as one shared, counted loop
   primitive: CARD-010's resample and CARD-016's nudge both reuse it, and INV-003 must have
   exactly one home.
5. **INV-002 export gate.** `ready_for_export` is set only after the uniqueness check
   confirms exactly one solution. The gate lives here, not in COMP-007 (ADR-0007's
   single-enforcement-point rule; trace.yml FR-011/FR-016 notes) — export cards call it.

## Acceptance criteria

- **AC-018** (happy, POL-001) — given a freshly generated random or library grid whose
  uniqueness check reports `solution_count != 1`, when the auto-regenerate policy evaluates,
  then a new candidate grid is generated automatically without user interaction and
  re-checked.
  *test:* `TestRegenerate_FiresOnUniquenessFailure`
- **AC-019** (boundary, INV-003, POL-005) — given a candidate that has already been
  regenerated up to the configured maximum retry bound, when another uniqueness failure
  occurs, then generation is abandoned and a clear error is reported instead of retrying
  again.
  *test:* `TestRegenerate_StopsAtMaxRetryBound`
- **AC-039** (boundary, INV-003) — given a generation request whose candidates never pass
  the uniqueness or difficulty check, when the retry loop runs, then it stops after at most
  the configured maximum retry count (20 regenerate/resample attempts, 5 pixel-nudge
  attempts — ADR-0002) and reports a clear failure instead of looping indefinitely.
  *test:* `TestRetryLoop_BoundedIterations`

## Guardrails

- G-1: Do not edit `src/nonogram/solver/**`, `src/nonogram/clues.py`,
  `src/nonogram/sourcing/**` — CARD-002/003/004's deliverables. The orchestrator composes
  them; if one of them needs a change to be composable, that is an escalation, not an edit
- G-2: INV-003 has exactly one home — this module (trace.yml NFR-002 note). Do not scatter
  retry counting into the sourcing or solver modules
- G-3: The uniqueness verdict is the solver's; the orchestrator must not re-derive,
  second-guess or short-circuit it (CON-005 is mandatory and is verified in CARD-004)
- G-4: No persistence — the `Puzzle` aggregate lives only for the duration of one process
  and the export file is the sole durable artifact (CON-003)
- G-5: Out of scope — no difficulty scoring or resample loop (FR-008/009/010, Increment 2),
  no pixel-nudge loop (FR-013, Increment 3), no export renderers (CARD-007 onward), no
  timeout enforcement (ADR-0011, CARD-006)

## System contract

- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions (check: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (check: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (check: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF)
- INV-003 — A puzzle's automatic-retry counter (regenerate, resample, pixel-nudge) never exceeds its configured maximum bound (check: TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestNudge_ReportsFailureAtCap, TestRetryLoop_BoundedIterations)

## Architecture context

- **FR:** FR-007
- **NFR:** NFR-002
- **INV:** INV-002, INV-003
- **POL:** POL-001, POL-005
- **ADR:** ADR-0002, ADR-0007, ADR-0015
- **Components:** COMP-002 (Pipeline Orchestrator), COMP-003, COMP-005 (consumed)
- **Trace:** meta/architecture/trace.yml

## Worktree notes

[Follow-up from CARD-001 review, cycle 2] The ADR-0007 import-direction guard in tests/test_cli.py
checks 3 of the 4 directional edges (nothing imports cli; capability packages don't import each
other laterally; errors.py imports nothing back) but not the 4th: a capability module importing
`nonogram.orchestrator` (outward). This card is where a real orchestrator↔capability import
relationship first exists — either extend the guard to the general invariant
(`rank(imported) > rank(importer)` for every discovered module, replacing the three special-case
tests) as part of this card, or confirm orchestrator.py's own imports stay one-directional and
leave a note for whichever card first adds capability→orchestrator coupling.

### Implementation summary (CARD-005)

`src/nonogram/orchestrator.py` now has a body: the `Puzzle` aggregate (AGG-001), the shared
counted-loop primitive (`RetryCounter` + `run_bounded`), and `generate()` — the
`source → clues → solve → mark ready` pipeline with POL-001's automatic regenerate and
POL-005's abandonment. `tests/test_orchestrator.py` (44 tests) covers it; the three ACs have
named tests and both INV-002 and INV-003 are tested directly, not incidentally.

Full suite: **582 passed in 3.6s** (535 before this card; +47 net, no regressions, no test
skipped or weakened). Every test is deterministic — the pipeline's randomness is the injected
`random.Random` and the two unmocked end-to-end tests are pinned to specific seeds.

Actual touches: the predicted `src/nonogram/orchestrator.py` + `tests/test_orchestrator.py`,
plus `tests/test_cli.py` — see STRUCTURE-8. No file under `src/nonogram/solver/**`,
`src/nonogram/clues.py` or `src/nonogram/sourcing/**` was modified (G-1 held; the three
capability modules composed without needing a single change, so no decomposition defect).

### Structural decisions

- **STRUCTURE-1: one mutable `Puzzle` per request, candidate state replaced in place —**
  because AGG-001 says so, and because it is the only shape in which INV-003's counter is
  *one* invariant on *one* instance. `generate()` builds the aggregate before the loop and
  returns the same object the loop mutated; a per-attempt aggregate would have made the
  retry count a property of the last attempt instead of the request. `test_one_aggregate_spans_every_retry`
  pins this by asserting the returned puzzle reports all four attempts, not one.
- **STRUCTURE-2: `RetryCounter` + `run_bounded(counter, attempt, reason=…)` as the retry
  primitive —** the loop kind is data (`kind`, `bound`) and the attempt is a no-argument
  callable returning the accepted candidate or `None`. CARD-010 (resample) and CARD-016
  (nudge) add a counter field next to `Puzzle.regenerate` and their own attempt callable;
  they do not add a second loop, and — because `record_attempt()` is the only way to advance
  a counter and refuses to pass `bound` — they cannot add a second way to count (G-2).
  Deliberately *not* a retry framework: no strategies, no backoff, no predicates, no
  registry. Two future call sites need a counted loop and one abandonment error; that is
  exactly what exists.
- **STRUCTURE-3: only the uniqueness verdict is a retry; every exception ends the run —**
  the attempt callable turns `solution_count != 1` into `None` and does nothing else. This
  is what keeps a future `SolverTimeout` (CARD-006) from being retried 20 times; see F-4 in
  the failure matrix for the ADR-0002/ADR-0001 justification, and
  `test_a_solver_timeout_is_not_treated_as_a_uniqueness_failure` for the guard.
- **STRUCTURE-4: the counter advances at the *start* of an attempt —** so an attempt that
  raises part-way through still consumes its budget. A budget refunded by a crash would let
  a deterministically-crashing attempt loop forever, which is precisely what NFR-002 forbids.
- **STRUCTURE-5: the seed is resolved once, in `generate`, and recorded on the aggregate —**
  `request.seed` or `secrets.randbits(64)` (ADR-0015), then one `random.Random` threaded into
  every sourcing call. Recording the *effective* seed is what makes an unseeded run
  reproducible after the fact (and gives FR-012's export the field it needs later); printing
  it stays COMP-001's job. Because the one instance is threaded through the whole loop, the
  *sequence* of discarded candidates is reproducible too, not just the first one.
- **STRUCTURE-6: `sourcing.for_mode(mode)` is resolved once, before the loop —** an unknown
  mode is a wiring bug and must fail immediately rather than after burning the retry budget
  (F-6). The mode-specific argument list is assembled at the call site inside the attempt,
  which is the seam CARD-008/CARD-015 extend.
- **STRUCTURE-7: INV-002 is a flag plus a gate method on the aggregate —**
  `ready_for_export` is written *only* by `confirm_uniqueness()` and only for
  `solution_count == 1`; `record_candidate()` closes it again, so a verified candidate never
  vouches for its replacement. `require_ready_for_export()` raises `ExportRejected` and is
  the single call COMP-007 makes before writing anything (ADR-0007's single-enforcement-point
  rule) — the gate is here, not in export code that does not exist yet.
- **STRUCTURE-8 (scope): `tests/test_cli.py` was edited, beyond the predicted Touches.**
  Three reasons, all forced: (a) `test_orchestrator_generate_is_a_signature_only` asserted
  `generate()` raises `NotImplementedError` — this card's whole job is to make that false, so
  the test had to go; (b) the `captured_requests` fixture built `orchestrator.Puzzle()` with
  no arguments, which an aggregate with a required request and seed cannot support; (c) the
  ADR-0007 guard follow-up below. No production file outside the predicted set was touched.
- **STRUCTURE-9 (deliberate non-decision): no default `--size`/`--density`.** Neither the
  requirements nor any ADR names one, so inventing "20x20 at 30%" here would be an unsourced
  requirement smuggled in through the orchestrator. `nonogram generate` with no size is
  therefore rejected by CARD-003's domain check with a clear message (F-5). Whichever card
  decides the defaults owns adding them; this one does not guess.

### Resolution of the ADR-0007 import-guard follow-up

**Extended to the general invariant, as the reviewer recommended.** The three special-case
tests (`test_nothing_inward_of_the_adapter_imports_the_adapter`,
`test_capability_packages_never_import_each_other_laterally`,
`test_the_shared_error_hierarchy_reaches_into_nothing`) are replaced by one
`test_every_import_in_the_package_points_inward`, which applies
`rank(imported) > rank(importer)` to every module the on-disk walk finds. That single
comparison covers all four directional edges, including the 4th (capability → orchestrator)
that had no real instance in the package until this card gave COMP-002 a body.

Why extending rather than noting: `tests/test_cli.py` had to be edited for this card
regardless (STRUCTURE-8), so the "editing a guard outside Touches is itself a scope
violation" horn of the dilemma does not apply — the file is already in the diff, and leaving
the weaker three-edge guard in a file being edited for exactly this reason would be the
stranger choice. The guard is also this card's own safety net: the orchestrator is the first
module with a real capability relationship, and the general rule is what stops a later card
from closing the loop the wrong way.

Two exemptions are encoded, both about identity rather than direction: a module importing its
own component (`solver.search` → `solver.propagate`) is internals, not layering; and the
package root `nonogram`, which shows up in the walk for every `from nonogram import x`,
re-exports nothing (already pinned by `test_package_root_imports_no_submodule`) so importing
it couples the importer to nothing.

The rule is applied through a pure helper, `_outward_imports({module: components})`, so it can
be — and is — exercised against a fabricated package: one parametrized test shows it rejecting
each of the five forbidden edges (including capability → orchestrator), and another shows it
accepting the arrows the component diagram does draw. Without that, a rank table that had
silently degenerated would let the on-disk test pass on an empty result.

Orchestrator imports were also confirmed one-directional independently of the guard:
`nonogram.orchestrator` imports `clues`, `solver`, `sourcing` and `errors`, and nothing
imports it except `nonogram.cli`.

## Failure matrix

Every boundary this card's pipeline can fail at. "Retried?" means: does the bounded loop
discard the candidate and source another one (POL-001), or does the run end?

| # | Trigger | Detected by | Retried? | Aggregate state afterwards | Observable outcome |
|---|---------|-------------|----------|-----------------------------|--------------------|
| F-1 | Candidate has `solution_count == MANY` (≥2) | `solver.solve` (COMP-005), verdict taken as given (G-3) | **Yes** — POL-001 | `grid`/`clues` replaced by the next candidate; `solution_count` cleared; `ready_for_export` stays `False`; `regenerate.attempts` +1 | Nothing user-visible; the loop continues silently (FR-007: no user interaction) |
| F-2 | Candidate has `solution_count == 0` | same | **Yes** — identical handling to F-1 | same as F-1 | same as F-1. The policy fires on `!= 1`, not on "more than one". Unreachable from a real sourced grid (a grid always solves its own clues), so it is a defensive path, tested by injecting the verdict |
| F-3 | 20th candidate rejected (bound reached, INV-003) | `RetryCounter.exhausted` inside `run_bounded` | **No** — POL-005 abandons | `attempts == bound == 20`; last rejected candidate still attached (diagnostic only); `ready_for_export` `False`; whole aggregate then dropped — the caller never receives it | `GenerationAbandoned` naming the count, the bound and what to change (`--size`/`--density`/`--seed`); `cli` maps it to exit 4 `GENERATION_FAILED` |
| F-4 | `SolverTimeout` from the deadline mechanism (ADR-0011, **CARD-006** — not implemented here) | the solver raises; the attempt callable does not catch it | **No** — propagates out of the loop on the spot | attempt counted (the budget is not refunded), aggregate dropped | `SolverTimeout` reaches the CLI unchanged (exit 4). **Justification (G-5):** a timeout is a statement about the *run's* time budget, not about the candidate, so retrying it 20 times would spend 20 full ADR-0001 deadlines on one request — exactly the worst case the bound exists to prevent. ADR-0002 is explicit that the attempt bound and the wall-clock deadline "operate together but independently". Pinned now by `test_a_solver_timeout_is_not_treated_as_a_uniqueness_failure` so CARD-006 cannot land the conflation by accident |
| F-5 | Invalid `--size` / `--density` (incl. absent) | `sourcing.random_grid.validate_*` on the first attempt (ADR-0010: domain rule, inward of the CLI) | **No** — `SizeOutOfRange` / `InvalidDensity` propagate | attempt 1 counted, aggregate dropped | exit 3 `INVALID_INPUT`. An invalid request does not become valid by being asked 20 times, and retrying would turn a one-line input error into a 20-attempt failure |
| F-6 | `--mode` with no registered source (wiring bug) | `sourcing.for_mode`, resolved **before** the loop starts | **No** — `ValueError`, and no attempt is consumed | counter still at 0, no candidate sourced | Plain `ValueError` (not a `NonogramError`): a bad mode is rejected by argparse `choices` at the adapter, so one arriving here is a pipeline bug, reported as `INTERNAL_ERROR`, not as an infeasible request |
| F-7 | Any other exception mid-attempt (bug, `MemoryError`, `KeyboardInterrupt`) | not caught anywhere in this module | **No** | the interrupted attempt **is** counted — `RetryCounter` advances at the *start* of an attempt, so a crash cannot refund budget and a repeatedly-crashing attempt can never loop forever | the exception propagates unchanged; the CLI reports non-`NonogramError`s as a traceback (already covered by `test_non_domain_exceptions_are_not_swallowed`) |
| F-8 | Run interrupted at any point (F-3..F-7, or the process is killed) | — | — | **No state survives.** The aggregate is a local of `generate()`, reachable only through its return value, so a failed run leaves nothing behind — no partial puzzle, no cache, no file (CON-003, G-4). Pinned by `test_a_run_writes_no_files` / `test_an_abandoned_run_writes_nothing` | Nothing to clean up; the next run starts from a fresh aggregate and a fresh counter |
| F-9 | Export attempted on an unverified puzzle | `Puzzle.require_ready_for_export()` — INV-002's single enforcement point | n/a | unchanged | `ExportRejected` (exit 5). The gate lives here so COMP-007 has one thing to call, and it is closed again whenever a new candidate is recorded — an old verdict never vouches for a new grid |
| F-10 | A caller advances a counter past its bound by hand | `RetryCounter.record_attempt()` | n/a | counter unchanged | `RuntimeError` naming INV-003 — deliberately *not* `GenerationAbandoned`: abandonment is a domain outcome the loop reports, overshooting is a programming error in the pipeline |
| F-11 | No `--seed` given | `generate` draws one from `secrets.randbits(64)` (ADR-0015) | n/a | `Puzzle.seed` always holds the effective seed | Not a failure — recorded so the run is reproducible after the fact. Echoing it to the user is COMP-001's job in a later card; the value is on the aggregate now |

Two non-failures worth stating, because a later card could mistake them for
bugs: a density of 0 or 100 yields a degenerate but genuinely *unique* grid and
so passes the gate on attempt 1 (they are valid input per CARD-003, not
generation failures); and the retry counter is deliberately **not** reset
between calls to `run_bounded`, so INV-003's bound applies to the whole
generation request rather than to one invocation of the primitive.

[Scope] Predicted Touches (orchestrator.py, test_orchestrator.py) plus tests/test_cli.py (outside prediction — see STRUCTURE-8 for the 3 forced reasons: a stale NotImplementedError test, a fixture building Puzzle() with no args, and the ADR-0007 guard extension). No file under solver/**, clues.py, or sourcing/** touched (G-1 held). 4 actual files vs 2 predicted — flagging for reviewer judgment per the scope gate rather than silently accepting the explanation.
[Build gate] PASSED (full, independently re-run by orchestrator: 582 passed, 0 failed, no regressions vs the pre-CARD-005 535).
