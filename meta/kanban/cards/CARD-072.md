# CARD-072: Record the solving strategies a puzzle needs and save them with the puzzle

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 1.5d
**Complexity:** standard
**Revision pending:** false  _(revised 2026-09-18 on starting — see Revision)_
**Skill:** python-pro
**TDD:** red -> green -> mutation check (4 mutants, 2 survived and drove two more tests)
**Branch:** card/072-record-solving-strategies
**Worktree:** ../PythonProject4-CARD-072
**Source:** owner request 2026-09-12 ("save the strategies needed for solving together with the puzzle"), plus docs/GENERATION_ALGORITHM.md §6-§7; follow-up card, not decomposed from handoff.md
**Idea:** —
**Wave:** 1
**Depends on:** CARD-073 (merged ab851eb), CARD-076 (merged 76c1df4) — both landed; G-5 satisfied
**Touches:** src/nonogram/solver/search.py, src/nonogram/solver/propagate.py, src/nonogram/orchestrator.py (Puzzle aggregate, judge_candidate, record_candidate), src/nonogram/export/__init__.py, src/nonogram/export/json_export.py, src/nonogram/web/metadata.py, src/nonogram/admin/batch_generator.py, src/nonogram/admin/app.py, src/nonogram/admin/puzzle_review.py, src/nonogram/admin/templates/** (detail + list filter), tests/property/test_export_roundtrip.py, tests/test_solver.py or a new tests/test_solver_strategies.py, tests/property/test_solver_strategies.py (new), tests/test_batch_generator.py, tests/test_puzzle_review.py
**Review score:** — _(merged without a review cycle, at the owner's call)_
**Started:** 2026-09-18
**Closed:** 2026-09-18
**Actual:** 1d
**Merge commit:** 50996b6
**Blocked by:** —

## Revision — 2026-09-18, on starting

Four things had moved since the card was written on 2026-09-12. Three are
corrections of fact; one is the owner's decision.

**1. Both dependencies have landed, and item 1 is now almost nothing.**
CARD-073 (`ab851eb`) put the ladder on `SolveSignals`: `rungs`, the distinct
rungs the deciding solve used in ladder order, and `rung_cells`, the per-rung
counts. CARD-076 (`76c1df4`) built the classifier on top. So item 1 is not
"classify the deductions" — that work is done and shipped. It is: read
`verdict.signals.rungs` and append `guess` iff `branch_nodes > 0`. The
overlap-vs-DP re-derivation the item describes already exists in
`solver/propagate.py`; **do not write a second one** (ADR-0029/R2, G-5).

**2. `cross_line` is not a strategy, and the card still lists it.** Item 1's
enum has five members, one of which lost its name in the markdown and reads as
an empty bullet — that member was `cross_line`. ADR-0029 **removed it from the
ladder** on the grounds that it was never a technique but an artefact of sweep
order: a puzzle and its transpose scored differently, and a 7x7 sample moved
from `{simple_overlap 30, line_dp 6, cross_line 13}` to
`{simple_overlap 30, line_dp 15, cross_line 4}` under transposition. The
shipped ladder is three rungs — `simple_overlap` < `line_dp` <
`probe_contradiction` (`solver.RUNG_ORDER`) — plus `guess`, which is not a
rung and is keyed on `branch_nodes` (ADR-0025). Four values, not five. The
item is rewritten below rather than left to be read around.

**3. No new enum is needed.** Item 1 offers "the solver, or a new import-free
shared module next to `errors.py`". The names already live in the solver and
are exported (`RUNG_SIMPLE_OVERLAP`, `RUNG_LINE_DP`,
`RUNG_PROBE_CONTRADICTION`, `RUNG_ORDER`). `guess` is the only name this card
adds, and it belongs beside them. `analysis/strategy_counter.py` stays
untouched and unused, as G-2 says.

**4. The export surface — the owner's call, 2026-09-18: JSON only, CSV
untouched, no `SCHEMA_VERSION` bump.** The question was forced by CARD-079,
which deferred its `binarisation` field here so the two would cost one schema
change instead of two. Measured against the code: the JSON decoder reads the
fields it names and ignores the rest, so it takes both additively at v2; the
CSV decoder rejects unknown keys *and* refuses any version but its own
(ADR-0023/R2 — no best-effort read of an older document), so putting the
fields in CSV means v3 and every `.json` and `.csv` already exported stops
decoding in this build. The owner chose to keep every existing export
readable. So:

- **JSON gains `strategies` and `binarisation`**, additively, still v2.
- **CSV and PDF are untouched**, and `SCHEMA_VERSION` does not move
  (new guardrail **G-7**).
- `binarisation` comes with this card, from CARD-079's Revision 3.

## Why

A puzzle book needs to say what a solver must know to finish a puzzle, and
the admin review needs to filter on it. Today the pieces exist but nothing
connects them:

- The DB column `strategies_used` exists (`src/nonogram/db/models.py:63`,
  JSON, nullable) but is written as `[]` for random batches
  (`src/nonogram/admin/batch_generator.py:346`) and for image batches
  (`src/nonogram/admin/app.py:476`), and as a hardcoded sample
  `['LineLogic', 'ConstraintProp']` at
  `src/nonogram/admin/puzzle_review.py:730`.
- The JSON export (`src/nonogram/export/__init__.py`, `ExportPayload`
  at L95-146) carries no strategies at all.
- The only taxonomy in the repo, the `Strategy` enum in
  `src/nonogram/analysis/strategy_counter.py`, belongs to the orphaned
  `analysis/` package (CARD-053 may delete it) and is never fed by the
  real solver.

The real solver (`src/nonogram/solver/`) reasons with one placement DP per
line (`line_intersection`), a fixed-point sweep, probing, and branching
(`docs/GENERATION_ALGORITHM.md` §6-§7). So the strategies a puzzle needs
must be *derived from that solve*, not from a second solver.

**Sequencing (updated 2026-09-12 by the Increment 8..12 decompose).**
This card is **Increment 10's delivery card for FR-029** (persistence,
export and admin display of the strategies list — see
`meta/architecture/handoff.md#increment-10`; the scoring/tier half is
CARD-076 and the DB re-grade is CARD-077). The decision that gated item 1
has landed: ADR-0025 (DEC-030 — "requires guessing" is a fourth tier
`guess`, keyed on `branch_nodes >= 1`) and ADR-0029 (DEC-031 — the
strategy ladder `simple_overlap` < `line_dp` <  <
`probe_contradiction`) confirm the provisional taxonomy below as the
decided one (FR-029's `enum_provisional` note is closed by CARD-076).
Item 1 is therefore **unblocked**, but it now **depends on CARD-073
landing first**: that card puts the per-cell rung tags, the per-rung
counts and the ordered rung list on `SolveSignals` (ADR-0029/R2), so item
1 shrinks to reading that ordered list and appending `guess` iff
`branch_nodes > 0` (EC-017) — no second classifier in this card. Item 1
also follows CARD-076 so that the tier value `guess` and the strategy
`guess` derive from the same fact through the one classifier
(ADR-0025/R2). Items 2-4 (storage, export, display) can start once
CARD-073 is merged; they no longer need a provisional enum. Export
ordering with the other wave-2 schema touches: CARD-076 (`difficulty` may
be `guess`) -> this card (`strategies`) -> CARD-079 (`binarisation`).
Rules now binding on this card: ADR-0029/R2 (one derivation from the one
verifying solve — AC-135 is its check), ADR-0029/R3 / CON-014 (no clock
in the list — EC-018), ADR-0029/R4 (no `clues.py` import in the solver),
ADR-0025/R1 (`guess` present iff branched).

## What to implement

1. **The strategies list** *(rewritten by the Revision — the classification
   this item described is already shipped by CARD-073)*. The value is
   `signals.rungs` — the distinct rungs the deciding solve used, in ladder
   order — with `guess` appended iff `signals.branch_nodes > 0`. Four possible
   members, not the five the original text listed:
   - `simple_overlap` — settled by propagating the leftmost/rightmost overlap
     alone (`solver.RUNG_SIMPLE_OVERLAP`);
   - `line_dp` — settled only by the full placement intersection
     (`solver.RUNG_LINE_DP`);
   - `probe_contradiction` — forced because the opposite value contradicted
     (`solver.RUNG_PROBE_CONTRADICTION`);
   - `guess` — the search branched. Not a rung: ADR-0025 keys it on
     `branch_nodes`, and `signals.rungs` deliberately never contains it.

   `cross_line` is **gone** — ADR-0029 removed it as an artefact of sweep
   order, not a technique (Revision 2).

   Where the appending happens is this card's one real design choice, and it
   should happen **once**: on the aggregate (item 2), so that persistence,
   export and the admin all read the same tuple rather than three call sites
   each remembering to append `guess`. No re-solve, no second classifier
   (ADR-0013's no-re-entry rule, ADR-0029/R2, G-1, G-5).
2. **Aggregate:** expose `Puzzle.strategies` (`tuple[str, ...]`) on the
   orchestrator aggregate, recorded in `judge_candidate` off
   `verdict.signals` alongside `difficulty_score`
   (`src/nonogram/orchestrator.py:1167-1198`), and reset by
   `record_candidate` the same way the score is (`orchestrator.py:654-670`).
3. **Persistence + export:** `puzzle_review.add_puzzle(strategies_used=...)`
   receives the real list for random AND image batches
   (`batch_generator.py:335-346` and `app.py:465-476`); remove the
   hardcoded sample at `puzzle_review.py:730`; add `strategies` **and
   `binarisation`** to `ExportPayload` and to the JSON export
   (`src/nonogram/export/json_export.py`), additively, at the current
   `SCHEMA_VERSION`. **CSV and PDF are untouched and the version does not
   move** (Revision 4, owner's call, G-7). Web metadata
   (`src/nonogram/web/metadata.py`) shows strategies only if it already shows
   difficulty.
4. **Admin display:** show the strategies on the puzzle detail/review
   page and allow filtering the puzzle list by strategy — reuse the
   CARD-066 status-filter pattern (route param pinned to the enum, error
   branch, template select).

## Acceptance criteria

- **AC-1** — A puzzle solved by line logic in one sweep reports exactly
  the line strategies used and no  / `probe_contradiction` /
  `guess`; a puzzle whose solve branched reports `guess`. A
  property-style test over a seeded corpus (stdlib `random.Random`,
  minimum case count asserted in the test, no hypothesis) checks:
  `guess` in strategies iff `branch_nodes > 0`.
- **AC-2** — `strategies` is deterministic for a given clue set (same
  clues → same list), independent of wall-clock.
- **AC-3** *(widened by Revision 4)* — JSON export of a generated puzzle
  contains a `strategies` array and a `binarisation` value (`null` for random
  and library puzzles); both round-trip, in the style of
  `tests/property/test_export_roundtrip.py`. `SCHEMA_VERSION` is unchanged in
  both formats, and a CSV export of the same puzzle is byte-identical to what
  this build produced before the card — which is the check that G-7 held.
  *test:* `TestExport_JSONCarriesStrategiesAndBinarisation`
- **AC-4** — Admin: a random batch stores non-empty `strategies_used` for
  every puzzle; the puzzle list filters by strategy; the hardcoded sample
  at `puzzle_review.py:730` is gone.
- **AC-5** — No change to the solver's verdicts:
  `tests/property/test_solver_uniqueness.py` and `tests/test_solver.py`
  unchanged and passing; solve time on the 20x20 benchmark
  (`tests/bench_generate.py`) within noise.

## Guardrails

- G-1: Never re-run the search to classify — strategies come from the
  one deciding solve (ADR-0013 no-re-entry rule).
- G-2: Never import across capability modules; the enum lives in the
  solver (or a new import-free shared module next to `errors.py` /
  `limits.py`) — not in `analysis/strategy_counter.py`, which CARD-053
  may delete. `tests/test_cli.py`'s structural guard must stay green.
- G-3: Solver verdicts (`count`, `solution`) are untouched; the oracle in
  `tests/helpers/brute_force_oracle.py` is not edited.
- G-4: DB migration must keep existing rows valid — the column is already
  nullable; no NOT NULL, no backfill that rewrites accepted puzzles.
- G-5: Do not start item 1 before CARD-073 (rung tags on
  `SolveSignals`) and CARD-076 (the `(score, branch_nodes)` classifier)
  are merged; the enum members are the ADR-0029 ones — do not invent a
  second taxonomy or a second `guess` derivation (ADR-0025/R2,
  ADR-0029/R2).
- G-7 _(added by Revision 4, the owner's call)_: `SCHEMA_VERSION` does not
  move in either export format, and `csv_export.py` and the PDF renderer are
  not edited. Every `.json` and `.csv` already exported must still decode
  (ADR-0023/R2 gives a decoder no best-effort read of another version).
- G-6: Commit only your own files — the working tree carries a large
  standing set of unrelated staged/untracked changes; use explicit
  pathspecs.

## Worktree notes

### Delivered 2026-09-18

**Item 1 — the list.** `Puzzle.strategies`, set in `record_difficulty` from the
same solve's `signals.rungs`, with `guess` appended **once**, there. The append
asks `difficulty.classify` (through `difficulty_tier`) rather than re-reading
`branch_nodes`: ADR-0025/R2 allows one reader of that rule, and the two
derivations already in `admin/` both ask the classifier for exactly this
reason. So the tree now has three *callers* of one rule, not three rules —
and `regrade._strategies_used`'s own docstring asked for this ("CARD-072
persists the same list from the generation path; this is the derivation to
reuse").

**Item 2 — persistence.** Both batch paths pass `puzzle.strategies` instead of
`[]`. `add_puzzle`'s fallback — derive from its own uniqueness proof — stays as
the safety net it was written to be, but is no longer the normal path, so a
stored row's grade and strategies are now two readings of *one* solve rather
than of two that happened to agree. The sample generator's hardcoded
`['LineLogic', 'ConstraintProp']` is gone; it reports what its own certifying
solve needed, borrowing `PuzzleReviewService._strategies_of` rather than
copying it.

**Item 3 — export, JSON only (the owner's call, Revision 4).** `ExportPayload`
gains `strategies` and `binarisation` — the second inherited from CARD-079's
deferral — and both are written by `json_export.document` at the **existing**
`SCHEMA_VERSION`. `parse` reads them with `get`, so a document written before
they existed still decodes. CSV and the PDF are untouched and the version has
not moved (G-7), which is what keeps every `.json` and `.csv` the owner has
already exported readable.

**Item 4 — admin.** Display already existed (CARD-076/077 shipped the badges).
The filter is new: `PuzzleFilter.strategy`, matched as **membership** — "show
me the ones that need a guess" — in both storage modes, with the route
rejecting an unknown name the way CARD-066's status filter does (flash, then
ignore, so the page never looks like "your other filters matched nothing").

The database half is the one design note worth reading. `strategies_used` is a
JSON column, and the two databases this runs on disagree about how to look
inside one — Postgres wants JSONB containment, SQLite wants `json_each`. The
query matches the **quoted** name inside the serialized text
(`cast(...).like('%"guess"%')`), which both accept. That is exact rather than
approximate only because the vocabulary is closed: no name contains a quote or
a wildcard, and none is a substring of another. The test that keeps it honest
stores a foreign name (`guessing`, of the kind older writers really did store)
and asserts the filter does not match it.

**Tests.** New `tests/test_strategies.py`, 17 tests across the four items.
Mutation check — four mutants, restored from saved copies:

| mutant | caught by |
|---|---|
| `guess` never appended | **survived** → drove a new test |
| strategies not cleared on a new candidate | `..._are_cleared_when_a_new_candidate_arrives` |
| `strategies` dropped from the JSON document | three tests |
| database filter matches unquoted text | **survived** → drove a better test |

Both survivors were real gaps, and the first is the interesting one: **no
random draw in the supported range produces a puzzle whose solve needs to
branch** — line logic and probing finish them all — so `guess` is not
reachable through `generate` today, and a corpus test could only ever assert
half the rule. The append is now pinned directly on the aggregate. Worth
knowing beyond this card: the Guess tier is, on current evidence, unreachable
from random generation.

**Full suite: 3,468 passed, 0 failed.** `check_doc_references.py`: 230
resolved, 0 failed.

### Out-of-scope observations

1. **CARD-097 is diagnosed** (its card and the board line are updated in this
   branch). The suite stall is not a lock or a leaked session: the process
   blocks inside psycopg's `connect`, because Postgres.app waits on a macOS
   permission dialog and nothing sets `connect_timeout`. It bit this card
   twice — the second time in a new test of mine, which now clears
   `DATABASE_URL` explicitly so `create_app` cannot reach for whatever
   database the machine happens to run.
2. **`analysis/strategy_counter.py` is now provably dead** for this purpose:
   its `Strategy` enum is not the shipped vocabulary and nothing reads it.
   CARD-053 owns deleting it; this card did not touch it (G-2).
3. **`tests/test_admin_uniqueness_boundary.py`'s candidate stub** needed a
   `strategies` value, since the store now reads one. Added as a real member
   of the vocabulary rather than a placeholder.
