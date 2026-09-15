# Puzzle Generation Algorithm — as implemented

**Status:** Reference, verified against `main` at `41096cf` (2026-09-15). See *Refresh log* at the
end for what each refresh re-checked.
**Supersedes for algorithm questions:** `docs/REQUIREMENTS/NONOGRAM_GENERATION_REQUIREMENTS.md`
(which describes an Otsu-threshold pipeline that was never built — see §11).
**Formal basis:** ADR-0001, 0002, 0003, 0005, 0011, 0015, 0022, 0024, 0025, 0029 under
`meta/architecture/decisions/adr/`; POL-001..POL-006 in `meta/architecture/domain/policies.yml`.

**How to read the references.** Code is cited by *symbol*, relative to `src/nonogram/`:
`orchestrator.generate`, `solver.search._expand`, `sourcing.image.nudge_cells`. A nested
function is written through its parent (`orchestrator.generate.judge_candidate`). Line numbers
are deliberately not used: they went stale within three days the last time the orchestrator
grew. Every reference in this file is resolved mechanically by
`meta/ops/check_doc_references.py`, which prints the file and line each one points at today:

```
python meta/ops/check_doc_references.py docs/GENERATION_ALGORITHM.md
```

---

## 1. What the generator promises

1. **Uniqueness.** A puzzle is returned only when the solver has counted *exactly one* solution
   to its clues. The comparison is made in one place, `orchestrator.Puzzle.confirm_uniqueness`,
   and export refuses a puzzle that never passed it (`orchestrator.Puzzle.require_ready_for_export`).
2. **Bounded recovery.** Three counters — regenerate, resample, pixel-nudge — each with a fixed
   cap, all advanced through one primitive (`orchestrator.RetryCounter`, `orchestrator.run_bounded`).
   Random mode's repairs spend the same regenerate budget as its redraws (§8.2).
3. **Bounded time.** One `GENERATION_BUDGET_SECONDS` (30 s) monotonic deadline per request, shared
   by every solve the request performs. A batch has its own clock on top (`BATCH_BUDGET_SECONDS`, §9.1).
4. **Reproducibility.** One `random.Random` seeded once per request; the seed is recorded on the
   returned puzzle. Repairs draw nothing from it, so a seed replays the same redraws *and* the
   same repair lineages. The grade reads no clock, so it replays too (§7).
5. **Density.** Random grids honour the requested percentage within ±3 points — by construction,
   not by checking (`sourcing.random_grid.generate`). A repair preserves the filled count exactly.

---

## 2. Pipeline overview

```
GenerationRequest (unvalidated, from CLI / web / admin)
  │
  ├─ resolve name            orchestrator.NameContext.name_for
  ├─ parse difficulty tier   difficulty.parse_tier
  ├─ resolve extent (W,H)    orchestrator._resolved_extent
  ├─ seed → random.Random    request.seed or secrets.randbits(64)
  ├─ deadline = now + GENERATION_BUDGET_SECONDS
  │
  └─ bounded loop(s) ──► attempt (orchestrator.generate.attempt_candidate):
        grid  ─►  compute clues  ─►  solve (count ≤ 2)  ─►  grade
        (§4)      (§5)               (§6)                    (§7)
          ▲                            │
          │      solution_count != 1 ──┤
          │                            ├─ random mode, lineage < K ──► REPAIR: flip one pair
          └────────────────────────────┤     inside the witnesses' disagreement (§8.2)
                                       ├─ random at K, or library ──► REDRAW from the rng (§8.1)
                                       └─ image mode ───────────────► NUDGE the conversion (§8.4)
                  grade outside requested tier ─────────────────────► RESAMPLE (§8.3)
  │
  ▼
Puzzle aggregate: grid, clues, solution_count, difficulty score/tier, seed, extent,
                  counters, recovery tally
```

**Boundary types** (ADR-0012): a grid crosses every module boundary as `list[list[bool]]`,
row-major, `True` = filled; clues as `tuple[tuple[int, ...], ...]`, one tuple per line, with a
line of no filled cells encoded as `(0,)` — never `()` (`clues.EMPTY_LINE_CLUE`). The solver's
internal bitmasks never leave the solver package.

---

## 3. Request resolution

Name, tier and extent are resolved **once**, at the top of `orchestrator.generate`, before the
aggregate exists, and are never touched by a retry. An invalid name, tier or extent aborts
before a seed is drawn.

### 3.1 Extent — `(width, height)`

`orchestrator._resolved_extent` distinguishes three shapes of request:

| Request | Rule |
|---|---|
| both sides stated (`--size WxH`) | validated as given, each side independently in 10..30 (`sourcing.random_grid.validate_extent`); the source's own shape is never consulted |
| one side stated (bare `--size N`) | completed from the source's shape by `sourcing.random_grid.derive_extent` |
| neither | rejected with the shared range message |

**Bare-N derivation** (`sourcing.random_grid._derived_extent`): N lands on the *longer* axis of
the source's own shape; the other side is `max(10, round(N * short / long))`. There is
deliberately no upper clamp — the derived side is ≤ N ≤ 30 by construction.

**Refusal** (`sourcing.random_grid._keeps_half`, `sourcing.random_grid._smallest_workable_size`):
if holding the short side at 10 would make the centred crop keep less than half the source
(exact integer test `2*kept >= whole`), the request is refused with `SizeTooSmallForSource`,
naming the smallest N that would work. The threshold is exactly `N/5 : 1` (2:1 at N=10, 6:1 at N=30).

Each mode reports its own shape through `sourcing.shape_for_mode`: random → `(1, 1)`, a square
(`sourcing.random_grid.source_shape`); library → the template's cell extent, 16×16 today
(`sourcing.library.source_shape`); image → the **ink bounding box** in pixels, not the file's
extent (`sourcing.image.source_shape`).

### 3.2 Seed and deadline

- `seed = request.seed if given else secrets.randbits(64)`; one `random.Random(seed)` is passed
  as the last argument to every source call.
- `deadline = time.monotonic() + GENERATION_BUDGET_SECONDS`, fixed once and handed to every
  `solver.solve` the request makes, repairs and retries included. It is a per-request budget,
  not per-solve: no number of attempts can stretch it.

---

## 4. Sources (COMP-003)

Dispatch is a closed table of three callables (`sourcing.for_mode`); the orchestrator assembles
each mode's argument list (`orchestrator._source_arguments`).

### 4.1 Random — `sourcing.random_grid.generate`

```
validate_extent(width, height); validate_density(density)   # 0..100 inclusive
filled = round(width * height * density / 100)              # filled_target
flat   = [True] * filled + [False] * (cells - filled)
rng.shuffle(flat); reshape to rows
```

Because the filled count is fixed before any draw, the only density error is the rounding of a
fractional cell: at most `0.5 / cells`, i.e. half a percentage point at 10×10. This is how
ADR-0003's ±3-point tolerance (`DENSITY_TOLERANCE_POINTS`) is met — nothing in the retry loop
measures density.

Density 0 and 100 are *valid* inputs (`MIN_DENSITY`, `MAX_DENSITY`) and produce all-empty /
all-filled grids. See §10 finding 2.

### 4.2 Library — `sourcing.library`

- Four templates (`cat`, `heart`, `house`, `moon`), each drawn as `TEMPLATE_EDGE` (16) square
  ASCII art and parsed once (`sourcing.library.parse_art`, `sourcing.library._TEMPLATES`).
- **Rescale by exact area coverage** (`sourcing.library.coverage`): each target cell maps back
  onto the rectangle of template cells it covers; coverage is an integer numerator over a shared
  denominator `16*16`, so "wholly inside" and "wholly outside" are exact at every extent. The two
  axes rescale independently — a non-square explicit `WxH` **stretches** the template
  (deliberate; ADR-0022/R3's crop rule is about user pictures, not built-in shapes).
- **Threshold** (`sourcing.library.render`): a cell is filled iff `numerator >= threshold * denominator`.
- **The only randomness** is that threshold, drawn `rng.uniform(MIN_EDGE_THRESHOLD, MAX_EDGE_THRESHOLD)`
  (0.35..0.65) per attempt in `sourcing.library.generate`. That is what "regenerate" means for a
  deterministic source: the same cat, a slightly fatter or leaner outline. Fully covered or
  uncovered cells never change.
- At **16×16** every coverage fraction is 0 or 1, so a retry renders the identical grid (stated in
  the `sourcing.library` module docstring). See §10 finding 8.

Library mode never repairs (ADR-0024/R5): a non-unique template rendering is redrawn.

### 4.3 Image — `sourcing.image.generate`

Order is prescribed by ADR-0022 and is load-bearing (the request is judged *before* any crop):

| Step | Function | Detail |
|---|---|---|
| 1 | `sourcing.random_grid.validate_extent` | range check before the file is touched |
| 2 | `sourcing.image.load_greyscale` | `Image.open` + `load`; EXIF orientation applied; RGBA/LA/PA or `transparency` composited onto **white**; converted to mode `L`. Every Pillow failure → `UnreadableImage` |
| 3 | `sourcing.image.ink_bounding_box` | ink = grey value **strictly below** `INK_THRESHOLD` (128); LUT + `getbbox`; no ink at all → whole extent |
| 4 | `sourcing.image.validate_aspect_ratio` | on the **ink box**, not the file: refuse with `ImageNeedsManualCrop` when a centred crop to the grid's ratio would keep < 50% of it. Exact integers: `kept = min(sw*th, sh*tw)`, `whole = max(...)`, accept iff `2*kept >= whole` (inclusive at exactly 2×) |
| 5 | `greyscale.crop(box)` | trim blank margin to the ink box (FR-022, best-effort — it does not guarantee no blank rows/columns after resize) |
| 6 | `sourcing.image.fit_crop_box` | largest **centred** sub-rectangle with the grid's aspect ratio; exactly one axis cropped; floor division; odd leftover pixel goes to the far side |
| 7 | `sourcing.image.binarize` | `resize((W, H), LANCZOS, box=crop)` — crop and resize in one call, one grey level per cell — then `convert("1", dither=FLOYDSTEINBERG)`, Pillow's built-in error diffusion |
| 8 | `sourcing.image.to_grid` | `numpy.asarray(bilevel) == 0` → black pixel is a filled cell |

The `rng` argument is accepted for the uniform calling convention and **never drawn from**: the
same file at the same extent always converts to the same grid. That is why image mode does not
enter the regenerate loop (§8.4).

Scope note (CON-013): calibrated for high-contrast silhouettes; photographs convert without
complaint but nothing is tuned for them.

---

## 5. Clue derivation (COMP-004) — `clues`

`clues.encode_line` run-length encodes the filled runs of one line, returning `(0,)` for a line
with none. `clues.compute_clues` applies it to every row and, via `zip(*grid, strict=True)`,
every column — a ragged grid raises rather than silently truncating.

---

## 6. Uniqueness solver (COMP-005) — `solver`

**Question answered:** does this clue set have 0, 1, or ≥2 solutions? `solution_count` is
`0`, `1` or `MANY == 2` (`solver.search.MANY`); the search stops the instant a second distinct
solution is recorded.

### 6.1 Representation — `solver.propagate.Board`

Each line is a pair of ints `(filled, empty)`; bit *i* set means cell *i* is known filled /
known empty. Row masks (column bits) and column masks (row bits) are kept in parallel and only
ever written together (`solver.propagate.Board.assign`). `solver.propagate.Board.clone` is four
shallow list copies — the backtracking undo.

### 6.2 Line logic — `solver.propagate.line_intersection`

Input: canonical runs (empty marker stripped to `()`, `solver.propagate.canonical_clue`), line
length, known masks. Output: `(filled_in_every_placement, empty_in_every_placement, placement_count)`
or `None` when no placement is consistent.

- Cheap rejections: runs plus mandatory gaps longer than the line → `None`; empty clue → one
  placement, every cell empty, unless something is already known filled; fully decided line →
  compare `solver.propagate.mask_runs(known_filled)` to the clue directly.
- Otherwise a DP over states `(pos, run_index)`, evaluated from the end of the line backwards.
  Each state stores the *union* of filled cells, the *union* of empty cells, and the placement
  count over all placements of runs `idx..` in cells `pos..`. Two transitions per state:
  leave `pos` empty (only if not known filled); or start run `idx` at `pos` (only if none of
  its cells is known empty and the cell after it is not known filled, or the run ends the line
  and is the last run). States that cannot fit the remaining runs are skipped via a `need[]` prefix.
- A cell that is in the filled union but never in the empty union is filled in every placement,
  and vice versa.

### 6.3 Propagation — `solver.propagate.propagate`

Sweep all dirty rows, then all dirty columns; every newly decided cell dirties the perpendicular
line; repeat until a sweep dirties nothing. Returns `False` the moment any line admits no
placement. At the fixed point every line admits ≥1 placement, so a fully decided board *is* a
solution. `board.decided` counts settled cells; per-line `placements` are cached for the
branching heuristic. The deadline is checked at the top of every sweep
(`solver.propagate.check_deadline`).

A per-solve memo, `solver.propagate.LineCache`, is keyed by packed
`(known_empty << length) | known_filled` per line and cleared wholesale at `LINE_CACHE_LIMIT`
(60 000) entries; semantically invisible.

### 6.4 Search — `solver.search.solve` and `solver.search._search`

```
canonicalise clues; if Σ row runs ≠ Σ column runs → 0 solutions
propagate from blank; contradiction → 0
line_logic_cells = board.decided
fully decided → 1 solution (verified)
for round in 0, 1, 2, ...:
    (probe_width, node_limit) = _SEARCH_ROUNDS[round], or the last width with the limit × 3^k
    result = _search(root.clone(), ...)
    if result is not CUT_OFF: break        # a cut-off round's findings are discarded
count = len(solutions) ∈ {0, 1, 2}
```

Restart schedule `solver.search._SEARCH_ROUNDS`, then `_NODE_LIMIT_GROWTH` (×3) per round:

| round | probe width | node limit |
|---|---|---|
| 0 | none (plain descent) | 400 |
| 1 | 8 | 400 |
| 2 | 16 | 1 200 |
| 3 | 32 | 3 600 |
| 4 | 64 | 10 800 |
| 5+ | 64 | ×3 per round, unbounded |

**Node expansion** (`solver.search._expand`):

- *Round 0* (`solver.search._descend`): pick the most constrained unknown cell — the least-placement
  line, then the least-placement perpendicular line through it (`solver.search._branch_cell`);
  try the better-supported value first (`solver.search._preferred_value`, support = product of
  surviving placements in row × column); if it survives propagation, push the *other* value as
  an unpropagated `solver.search._Pending` sibling. If it contradicts, the other value is forced
  (a deduction, not a guess).
- *Rounds ≥ 1*: **probe** the `probe_width` most constrained unknown cells (ranked by row
  placements × column placements, `solver.search._probe_candidates`). For each, assign both
  values on clones and propagate. Both contradict → node refuted. One contradicts → the other is
  forced, the pass restarts on the new board. Neither → the pair is a branch candidate, scored
  by `min(gain) * (cells+1) + sum(gain)`. A pass that forces nothing branches on the best pair
  (round 1) or a hash-diversified pair (`solver.search._diversified`) so a restart walks a
  different tree.

**Why it is sound** (argued in the `solver.search` module docstring): propagation only writes
cells every placement agrees on, so a contradicting probe proves no solution assigns that value;
forcing the opposite discards nothing. Both children of a branch always come from the same board
(a pass that forced anything restarts before its pool is used). Sibling subtrees differ in the
branch cell, so two recorded solutions are distinct. Cut-off rounds are thrown away whole.

**Self-check** (`solver.search._verified_grid`): every completed board is re-encoded line by line
with `solver.propagate.mask_runs` and compared to the clues it was solved from, in both
orientations, before it counts. A mismatch raises `RuntimeError` — a solver defect, never a
puzzle outcome.

**Deadline** is checked at every node `solver.search._search` pops and every propagation sweep;
past it, `SolverTimeout` is raised and no verdict exists.

### 6.5 The strategy ladder and what the result carries (CARD-073, ADR-0029)

Before the search runs, the solve walks three **stratified fixed points** over one board, never
resetting it and never re-entering the solver. Each level runs its technique to exhaustion and
then hands the board to the next, so a cell's rung is the level at whose fixed point it was
first settled (`solver.propagate.RungTagger`):

| level | technique | where |
|---|---|---|
| `simple_overlap` | the leftmost/rightmost overlap rule **relative to the line's known cells** | `solver.propagate.overlap_extremes`, `solver.propagate.overlap_deduction`, `solver.propagate.propagate_overlap` |
| `line_dp` | the full placement intersection, i.e. `solver.propagate.line_intersection` | driven from `solver.search.solve` |
| `probe_contradiction` | one-step lookahead: a value whose propagation contradicts forces its opposite | `solver.search._lookahead`, `solver.search._probe_fixed_point` |

Monotone propagation is confluent, so the set of cells a level settles is a function of the clue
set alone. That is what makes a rung a property of the puzzle: a clue set and its transpose
produce identical rung counts (ADR-0029/R5, measured 250/250). `cross_line` is deliberately not a
rung — feeding information between rows and columns until nothing more can be deduced is what
propagation does at every level, and defining a rung by sweep index made grading depend on grid
orientation, which is the defect the 2026-09-12 ADR revision removed.

Between levels 2 and 3 a **bounded speculative round** (inside `solver.search.solve`) runs round
0's plain descent purely to detect an ambiguous clue set. Two verified distinct solutions is a
verdict on its own terms and returns immediately, so lookahead never runs for a candidate the
generator is about to discard. Anything else discards that round's findings *and* its counters,
exactly as an abandoned restart round is treated, and the solve continues into level 3 with
fresh counters.

**Attribution is scoped to real puzzles.** A clue set with no solution or several is not a puzzle,
has no grade and reports no rungs; the scrub is applied once, in `solve`'s local `finish`, for
every exit whose count is not 1. The undecided mask is *not* scrubbed, so AC-110 still holds.

**What `solver.search.SolveResult` carries:** `solution_count`, `solution`, `undecided_mask` (the
cells line logic left open at its first fixed point, reported for every verdict), `second_witness`
(on an ambiguous verdict, the second solution the fail-fast search already stops on), `rung_tags`
(per cell, or `None`), and the `witnesses` convenience pair (`solver.search.SolveResult.witnesses`).
All cross the boundary as grid-shaped lists; the internal bitmask pair never does. The mask and
the witnesses are what random-mode repair (§8.2) and image-mode nudge (§8.4) work from.

**Signals** (`solver.search.SolveSignals`): `line_logic_cells` (the levels 1+2 fixed point),
`total_cells`, `branch_nodes` (nodes expanded by the *deciding* round only), `backtracks`,
`elapsed_seconds`, plus `rung_cells` and the ordered `rungs` list — which **is** FR-029's
strategies list. `elapsed_seconds` is reported by the solver but is not part of what the grader
reads (§7).

**One measured consequence.** Because lookahead is a phase of the solve rather than search work,
it settles puzzles that previously needed a guess: across 6,620 uniquely-solvable random and
structured grids from 10x10 to 20x20, **none** required a real branch. Every puzzle the generator
produces is logically solvable, which is the product promise; ADR-0025's Guess tier is kept as a
measured-unreachable safety net rather than deleted.

**Independent verification:** `tests/property/test_solver_uniqueness.py` cross-checks the solver
against two brute-force counters in `tests/helpers/brute_force_oracle.py`, which imports only
`nonogram.clues`.

---

## 7. Difficulty grade (COMP-006) — `difficulty`

ADR-0029 (the strategy ladder) and ADR-0025 (the fourth tier) replaced ADR-0013's five-signal
weighted sum in CARD-076. There is no clock, no size and no density term anywhere in what
follows; the scorer never re-enters the solver.

**The grade is the hardest rung the one verifying solve required** (§6.5, `difficulty.hardest_rung`),
and the tier is that rung's band — unless the search branched, in which case it is `Tier.GUESS`
on that fact alone.

| rung | tier | band | means |
|---|---|---|---|
| `simple_overlap` | Easy | `[0, 33]` | the overlap rule finished the puzzle by itself |
| `line_dp` | Medium | `(33, 66]` | some line needed the full placement intersection |
| `probe_contradiction` | Hard | `(66, 100]` | some cell needed a refuted one-step probe |
| — (`branch_nodes >= 1`) | Guess | none | the search really had to branch (EC-015) |

The 0..100 number is a derived presentation (`difficulty.score_difficulty`), kept so the export,
the DB column and POL-004's predicate survive unchanged in type:

```
rung  = the hardest rung with at least one cell settled at it   (rung_cells, §6.5)
share = rung_cells[rung] / total_cells                          (ADR-0029's secondary count)
score = band_low(rung) + share * band_width(rung)
```

**The band edges are ADR-0005's cutoff constants, not idealised thirds** (`EASY_MAX_SCORE`,
`MEDIUM_MAX_SCORE`; ADR-0029, History 2026-09-13). The difference is a third of a point and it
decides 88% of the corpus: a puzzle topping out at `simple_overlap` has *every* settled cell at
that rung by definition, so its share is exactly 1.0 and its score is the top of the first band.
At a width of 33.33 that is 33.33, which is above `EASY_MAX_SCORE = 33.0`, so every Easy puzzle
would classify Medium and the Easy band would be empty. With the edges on the cutoffs — which are
*inclusive* upper bounds — it scores exactly 33.0 and classifies Easy, while any higher rung has a
strictly positive share and so scores strictly above its band's floor. That is what makes
ADR-0029/R1's cross-rung ordering strict by construction.

**Classification takes `(score, branch_nodes)`** and lives in exactly one place,
`difficulty.classify` (ADR-0025/R2). EC-015 is applied first; the bands only to the remainder.
`difficulty._tier_for_score` is private for the same reason: a score alone cannot tell Easy from
Guess. `tests/test_difficulty_tiers.py::test_no_module_but_difficulty_classifies_a_tier` walks the
package with `ast` and fails if a second module starts comparing a score against a cutoff or a
branch count against a number.

**Measured distribution** (CARD-076's AC-118 corpus: 292 uniquely-solvable random puzzles,
10x10..30x30, seeded):

| tier | rung | n | share of corpus | score range |
|---|---|---:|---:|---|
| Easy | `simple_overlap` | 258 | 88.4% | 33.000 (a single point) |
| Medium | `line_dp` | 8 | 2.7% | 36.667..59.400 |
| Hard | `probe_contradiction` | 26 | 8.9% | 68.116..98.640 |
| Guess | — | 0 | 0% | — |

Two things follow and are recorded rather than acted on (CARD-076 guardrail G-5). **Easy is a
single point on the scale** — every puzzle that never leaves overlap scores exactly 33.0, so the
within-rung ordering ADR-0005's owed recalibration is waiting on does not exist inside the
bottom band. And **`Tier.GUESS` is measured-unreachable** from the current sources: 0 of 6,620
grids in ADR-0029's sweep, 0 of 462 in CARD-076's pre-implementation measurement, 0 of 292 here.
The tier is kept deliberately (ADR-0025, History 2026-09-12) and its criteria are tested against
synthetic signal records, which is the only way to pose them. That corpus predates POL-006's
repair; a repaired grid is judged by the same solve and graded by the same ladder, so the rules
are unaffected, but the distribution has not been re-measured since.

Retired with ADR-0013 — none of these exist any more: <!-- historical -->
`SignalWeights`, `SIGNAL_WEIGHTS`, `NormalizedSignals`, `normalize_signals`, `clue_density`, <!-- historical -->
`SECONDS_PER_CELL_BUDGET`, `HARDEST_DENSITY`, `MIN_SUPPORTED_CELLS`, `MAX_SUPPORTED_CELLS`, `tier_for_score`. <!-- historical -->

`difficulty.SolverSignals` names three members — `total_cells`, `branch_nodes`, `rung_cells` —
and deliberately not `elapsed_seconds`: CON-014 holds because the scorer is never handed a
clock, not because it declines to read one.

`difficulty.parse_tier` is case- and whitespace-insensitive and its error message lists all four
tiers, read off the enum (AC-021). The empty string is a tier name that does not exist, not
"any tier" (CARD-070).

---

## 8. Recovery policies (COMP-002)

All bounded loops use one primitive: `orchestrator.RetryCounter` refuses to advance past its
bound; `orchestrator.run_bounded` calls an attempt until it returns a non-`None` candidate, then
raises `GenerationAbandoned` with the count, the bound and a reason. Counters live on the
`orchestrator.Puzzle` aggregate and are **never reset** during a request.

| Counter | Bound | Policies | Modes |
|---|---|---|---|
| `regenerate` | `MAX_REGENERATE_ATTEMPTS` = `MAX_RETRY_ATTEMPTS` = **30** | POL-001 redraw, POL-006 repair | random, library |
| `resample` | `MAX_RESAMPLE_ATTEMPTS` = `MAX_RETRY_ATTEMPTS` = **30** | POL-004 | random, library, only with `--difficulty` |
| `nudge` | `MAX_NUDGE_ATTEMPTS` = **5** | POL-002 / POL-003 | image |

Plus one constant that is **not** a bound: `MAX_CONSECUTIVE_REPAIRS` (K) = **5**, which splits the
regenerate budget between repairs and redraws (§8.2).

One judged attempt is `orchestrator.generate.judge_candidate`: record grid + clues →
`solver.solve` with the shared deadline → store the solve's undecided mask, witnesses and rung
tags on the aggregate → `orchestrator.Puzzle.confirm_uniqueness` (reject if count ≠ 1) → grade
the same solve's signals. This is the only `solver.solve` call in the module, so every grid —
fresh, repaired, re-rendered, uploaded or nudged — is judged identically (CON-005). The mask and
witnesses are stored *before* the uniqueness gate because a rejected candidate is exactly what
repair and nudge need them for.

### 8.1 Redraw (POL-001)

A candidate whose clues have 0 or ≥2 solutions is discarded and the source is called again with
the same `rng` (`orchestrator.generate.attempt_candidate`). This is the whole of library mode's
recovery, and random mode's once a repair lineage ends.

### 8.2 Repair, then redraw (POL-006, ADR-0024) — random mode only

A random candidate the solver reports `MANY` for is not thrown away at once. The solver found
two distinct solutions, so the ambiguity is *located*: the cells on which the two witnesses
disagree. The next attempt judges a repaired copy of the grid instead of drawing a fresh one.

**The repair** (`orchestrator.repair_candidate`), a pure function of the grid and the solver's
report — no rng draw, no clock:

- **Region.** The witness-disagreement set (`orchestrator._disagreement_mask`). Only if that set
  holds no filled/empty pair *of the parent grid* does the repair fall back to the first-fixed-point
  undecided mask. The fallback is a live path, not a defensive branch: it was measured firing in
  9 of 241 real `MANY` verdicts. `RecoveryLog.repairs_from_fallback_region` counts it.
- **Flip.** Exactly one filled cell becomes empty and exactly one empty cell becomes filled, both
  inside the region. The filled count is preserved exactly, so the requested density holds by
  construction (ADR-0024/R3).
- **Pair choice** (`orchestrator._region_cells`, `orchestrator._first_pair_in_region`). The region's
  cells in row-major order; the first filled and the first empty cell are taken. Deterministic,
  so the same seed replays the same lineage on every machine (ADR-0024/R4). The result is an
  `orchestrator.Repair` value naming both cells and the region.
- **Re-verify.** The repaired grid's clues are re-derived and it goes through the one
  `judge_candidate` path; a repaired grid is never assumed unique because it was repaired
  (ADR-0024/R1).

**The escape.** A chain of consecutive repairs on one grid is a *lineage*. After
`MAX_CONSECUTIVE_REPAIRS` (K = 5) repairs without a unique verdict the lineage is discarded and
the next attempt redraws (§8.1). A lineage also ends early when neither region holds a pair to
flip (`RecoveryLog.lineages_without_repairable_region`).

**One budget.** Every repair and every redraw advances the same `regenerate` counter
(ADR-0024/R2). A run can make at most 30 attempts of either kind, whichever came last raises
`GenerationAbandoned`. K is a split of that budget, never a second bound;
`tests/property/test_recovery_bound.py` holds the property over a seeded corpus. Setting K to 0
disables repair and reproduces the pure-redraw loop exactly, down to the rng draws — ADR-0024's
rollback switch.

**A lineage can cycle.** Flipping the first pair can hand back a grid the lineage already judged
(the rule flips a pair back). That is *counted*, not acted on (`RecoveryLog.repeated_attempts`,
using `orchestrator._lineage_key`); choosing a different pair would be a different rule from R4.
Measured rare: 7 of 233 repairs in CARD-091's scoping probe.

**What a run records** (`orchestrator.RecoveryLog`, on `Puzzle.recovery`): redraws, repairs,
repairs from the fallback region, lineages that reached K, lineages with no repairable region, and
repeated grids. Observability only — nothing reads these to decide anything.
`orchestrator.RecoveryLog.describe` renders them as one line, e.g.
`16 recovery attempts: 4 redraws, 12 repairs (0 from the undecided mask); 3 lineages reached the repair cap of 5, ...`.

**What it buys** — measured with `meta/ops/retry_bound_sweep.py` at 30x30, density 50, 100 seeded
requests per row (CARD-089, CARD-090, CARD-091):

| recovery | bound | success at 30x30 |
|---|---|---:|
| redraw only (K = 0) | 30 | 38% |
| repair, K = 3 | 20 | 85% |
| repair, K = 3 | 30 | 95% |
| **repair, K = 5 (shipped)** | **30** | **99%** |

At 25x25 every configuration with repair succeeds 100% (redraw only: 74%). Raw 30x30 draws are
uniquely solvable about 2.7% of the time; repair is most of why the pipeline is not. K = 5 also
removed the one request in a hundred that had reached the 30 s deadline at every retry bound: the
slowest 30x30 request fell from 30.0 s to 9.8 s. Timings are only comparable within one sweep run,
so the cards carry them; the success counts are seed-comparable across runs.

### 8.3 Resample (POL-004) — shared budget

Only when a tier is requested. The resample loop *wraps* the regenerate loop
(`orchestrator.generate.attempt_candidate_in_tier`): one resample round runs the regenerate loop
to obtain a unique candidate, then keeps it only if `difficulty.classify(score, branch_nodes)` is
the requested tier. Because neither counter resets, **at most 30 candidates are judged per request**
— redraws and repairs together — however the rejection causes divide them. A tier-rejected
candidate is unique, so it is never repaired: the next attempt redraws. An exhausted inner loop
propagates its own abandonment. Without a tier the check is vacuous and the first unique candidate
is returned.

Still **one** tier comparison since ADR-0025, which is what keeps the predicate simple with four
tiers: `guess` is a legitimate thing to request and every other tier discards branching
candidates by the same one line. `Tier.contains` is gone — a score alone can no longer classify
a result, so a second way to ask "is this score in that band" could only be wrong about the
fourth tier.

Worth knowing before requesting a tier: under ADR-0013 a line-solvable puzzle scored under 15
and `--difficulty easy` therefore always succeeded on the first candidate. Under the ladder Easy
means "never left the overlap rule", which is ~88% of random grids overall but only ~15% at
density 45, and Medium (`line_dp`) is ~3% overall. A request for Medium at an unlucky
extent/density will resample, and at a density where its rung does not occur it will exhaust the
budget and abandon. `--difficulty guess` cannot be filled at all on today's sources (§7).

**Which tier a request can satisfy depends on extent and density** — not because the score reads
either (ADR-0029/R3 keeps both out of it) but because they decide which puzzles *exist*. The
structural tension that makes a sparse grid uniquely solvable is the same tension that forces the
solver past overlap, so sparse unique puzzles are hard puzzles. Measured, 120 draws per cell,
before POL-006 (so "uniquely solvable" is per raw draw, not per request):

| extent | density | uniquely solvable | of those, Easy |
|---|---:|---:|---:|
| 12x12 | 45 | 28 (23%) | 8 (29%) |
| 12x12 | 60 | 106 (88%) | 105 (99%) |
| 15x15 | 45 | 8 (7%) | 1 (12%) |
| 15x15 | 60 | 92 (77%) | 90 (98%) |
| 20x20 | 45 | 2 (2%) | 0 (0%) |
| 20x20 | 60 | 76 (63%) | 73 (96%) |

So `--difficulty easy` at 15x15 density 45 must find roughly a 1-in-960 grid inside the retry
budget. Measured at the then-bound of 20 and before repair, it went from 9/10 successes before
the ladder to 0/10 after, while `hard` at the same extent went 0/10 to 9/10. The practical rule
for a book: generate Easy at density 50-60 and Hard at 45. Repair raises the chance of *some*
unique grid per request, but it does not change which tier a density produces; this table has not
been re-measured since CARD-074, CARD-090 or CARD-091.

### 8.4 Pixel nudge (POL-002/POL-003) — image mode only

Image mode converts **exactly once** and never enters the loops above: the regenerate and resample
counters stay at zero, because asking the source for a second candidate would return the first.
If the conversion is not unique:

- attempt *n* (1..5) flips the best *n* cells of the **original** conversion — cumulative from
  the conversion, not from the previous nudge — and the result is fully re-solved through
  `judge_candidate` (`sourcing.image.nudge`).
- Cell ranking (`sourcing.image.nudge_cells`): (1) participation in 2×2 "switching" blocks
  (`# .` / `. #` diagonals), descending; (2) number of orthogonal neighbours with the other
  value, descending; (3) Chebyshev distance from the grid centre, ascending; (4) row, column.
  Greedy selection with a Chebyshev spacing of `_NUDGE_SPACING` (1) between chosen cells; if
  spacing cannot supply enough cells the rest of the ranking fills in.
- At the cap: `GenerationAbandoned` saying the picture was never re-drawn and the tool has
  stopped altering it (`orchestrator._image_uniqueness_reason`).
- A conversion that is unique but **outside the requested tier** is not nudged; the run is
  abandoned immediately (`orchestrator._image_tier_reason`).

### 8.5 What is never retried

`SolverTimeout`, `SizeOutOfRange`, `InvalidDensity`, `UnknownLibraryImage`, `UnreadableImage`,
`ImageNeedsManualCrop`, `InvalidPuzzleName`, `UnsupportedDifficulty` all propagate out of the
loops unchanged (`orchestrator.run_bounded`). A timeout says nothing about the candidate, and an
invalid request does not become valid by being asked again.

---

## 9. Batches, and the admin panel's layer on top

Outside the single-request pipeline, but it decides what a batch user sees.

### 9.1 `orchestrator.generate_batch`

Runs `orchestrator.generate` once per requested puzzle — the same pipeline, repair included.

- **Count** `1..MAX_BATCH_COUNT` (50; CARD-088 lowered it from 200). The admin form defaults to
  `admin.app.DEFAULT_BATCH_COUNT` (15).
- **Per puzzle:** a size drawn from `sizes` with an **unseeded** `random.Random`; density
  **hardcoded to 50**; the tier, if given, validated once up front with `difficulty.parse_tier`.
  Each puzzle draws its own seed inside `generate`; the admin does not persist it.
- **The batch clock** (`BATCH_BUDGET_SECONDS`, 75 s, CARD-088) is read **before** each candidate,
  never during one, so a started puzzle always finishes: the true ceiling is
  `BATCH_BUDGET_SECONDS + GENERATION_BUDGET_SECONDS` = 105 s, which `tests/test_admin_serving.py`
  checks against the server's request timeout. Candidates never started are counted, not
  abandoned.
- **An abandoned candidate is skipped** (CARD-083): `GenerationAbandoned` from one puzzle is bad
  luck, not a broken batch. **`MAX_CONSECUTIVE_ABANDONMENTS` (3) in a row ends the batch** by
  raising `GenerationAbandoned` — at that rate the request is infeasible rather than unlucky.
  That raise does **not** return the puzzles already made in the call; see §10 finding 9.
- **`SolverTimeout` is not skipped.** It ends the batch, because swallowing it per candidate would
  leave a batch no time bound but its own clock. Whether a batch should survive a timeout too is
  CARD-083's open owner question.
- **The result** is an `orchestrator.BatchResult`: a `list` of puzzles carrying `abandoned` and
  `not_attempted` counts, and `stopped_early` when the clock rather than the count ended it. The
  two counts mean opposite things to whoever re-runs the batch — bad luck versus a request that
  will stop in the same place — so they are kept apart.
- **An empty result** raises instead of returning: one message when the clock stopped it before
  any puzzle, another when every candidate was abandoned (reachable only for `count` < 3; from 3
  up the consecutive rule fires first).

The admin's random batch (`admin.batch_generator.BatchGenerator._generate_random_batch`) calls it
with `source="random"` and `difficulty_tier=None`, falls back to sizes `[15, 20, 25]` when the
batch record has none, and stores the returned puzzles after the call. It writes the abandoned and
not-attempted counts onto the batch record as two separate notes.

### 9.2 Image batches

- **Size presets** (`admin.image_manager.SIZE_PRESETS`): `small` = 10 on the *short* side with the
  long side following the picture (handed on as a full pair, since `derive_extent` floors a derived
  side at 10); `medium` = bare 20; `large` = bare 30; `auto` = the largest bare N keeping at least
  2 source pixels per cell, `min(long_edge_px // 2, 30)`. A `min` size mode (about 5 below `auto`,
  floored at 10) exists in `admin.image_manager.ImageFile._own_extent` but is not a preset.
- **Fit policy** (`admin.image_manager.ImageFile.size_fit`): the chosen grid must keep at least
  `MIN_KEPT_SHARE` (90%) of the ink box, compared as integer cross-products so a picture and its
  transpose agree to the last bit (`admin.image_manager._kept_share`). Otherwise the picture moves
  to the Large preset's grid (`MOVED_TO_LARGE`) if that keeps enough, else it is skipped
  (`CANNOT_FIT`). This is stricter than the sourcing module's own 50% refusal.
- **Abandonment retry** (`admin.app._generate_image_puzzle`, `admin.image_manager.ImageFile.neighbour_extents`):
  if `orchestrator.generate` raises `GenerationAbandoned` at the predicted extent, the batch retries
  at the long-side −1 and +1 neighbours, ordered by how much of the picture each keeps (ties to the
  smaller extent), at most 2 extra full runs. A square extent only moves toward the picture's own
  shape. On the predicted extent any other error propagates at once; on a neighbour, any other
  `NonogramError` ends the retry and the first abandonment is reported.

---

## 10. Correctness review

Method: a full read of the modules above, targeted probes, and the suites
`tests/property/test_solver_uniqueness.py`, `tests/property/test_recovery_bound.py`,
`tests/test_solver.py`, `tests/test_orchestrator.py`, `tests/test_resample.py`,
`tests/test_nudge.py`, `tests/test_sourcing_random.py`, `tests/test_sourcing_library.py`,
`tests/test_sourcing_image.py`, `tests/test_difficulty.py`, `tests/test_difficulty_tiers.py`,
`tests/test_batch_abandonment.py`, `tests/test_timeout.py`. On `41096cf`: **692 passed, 1 failed**.
The failure is `test_the_admin_puzzle_list_gives_the_fourth_tier_a_badge_of_its_own`, which parses
an inline `background-color:` off the admin puzzle list's tier badge; the admin's design-system
commits changed that markup, and it fails identically on untouched `main`. It tests no generation
code. `tests/test_timeout.py` passed 17/17 on three consecutive runs.

### 10.1 Verified sound

- **Line DP.** Both transitions respect the known masks; the separating gap after a run is
  required unless the run ends the line; states are evaluated in reverse position order so every
  dependency is already computed; union masks yield exact intersections. The `need[]` skip only
  removes states with zero placements.
- **Fixed point.** A row re-dirtied by a column later in the same sweep sets `pending`, so
  another sweep runs; at return every line was examined in its final state.
- **Search.** Forced values come only from refuted opposites; both children of any branch derive
  from one board; sibling subtrees are disjoint so `len(solutions) == 2` means two distinct grids;
  cut-off rounds are discarded whole; node limits grow without bound so the search is complete.
  Every counted solution is re-verified with code independent of the DP.
- **Oracle.** The EC-001 property corpus against two independent brute-force counters passes.
- **Recovery accounting.** ≤ 30 attempts per request, redraws and repairs together; a repaired
  grid goes through the same solve as a drawn one; a lineage never exceeds K repairs; ≤ 5 nudges;
  timeouts and invalid input never consume an attempt; the deadline is per request
  (`tests/property/test_recovery_bound.py`, `tests/test_orchestrator.py`).
- **Repair preserves density.** One filled and one empty cell per flip, so the filled count of a
  repaired grid equals its parent's, and a repair draws nothing from the rng.
- **Density.** Rounding-only error, inside ±3 points at every supported extent.
- **Aspect logic.** `derive_extent`'s half-retention predicate and `validate_aspect_ratio` are
  the same integer arithmetic, both inclusive at 2×, so a derived extent always passes the guard.

### 10.2 Findings

Findings 1–8 were raised in the 2026-09-12 review; 9 and 10 in the 2026-09-15 refresh. Each
status was re-established on `41096cf` by re-running or re-reading the check.

| # | Status | Severity | Finding | Where |
|---|---|---|---|---|
| 1 | **Closed** — CARD-070, `3a86aeb`, `1500c1c` | Low — latent bug | `generate_batch` checked `difficulty_tier` against enum *names*, so `"Easy"` raised `ValueError`. It now delegates to `difficulty.parse_tier`, and `""` is refused on both paths rather than read as "any tier". Re-checked: `generate_batch(count=1, sizes=[10], difficulty_tier="Easy")` returns a puzzle. | `orchestrator.generate_batch` |
| 2 | **Open** — CARD-078, ready | Medium — spec gap | Density 0 and 100 are accepted and yield all-empty / all-filled grids that pass the uniqueness check, score 33.0 and classify Easy. The `sourcing.random_grid` module comment above `MIN_DENSITY` still says later stages reject such grids; none does. Decide whether to reject in `validate_density` or document them as allowed. Re-checked: both densities return `ready_for_export=True`, score 33.0, tier `easy`. | `sourcing.random_grid.validate_density` |
| 3 | **Closed** — CARD-076 | Low — reproducibility | `time_pressure` made the score, hence the tier, machine-dependent. Under ADR-0029 no clock term exists and `difficulty.SolverSignals` does not carry `elapsed_seconds`, so the defect cannot recur without a visible protocol change. | `difficulty.SolverSignals` |
| 4 | **Closed** — CARD-070, `3a86aeb` | Low — docstring drift | The `DENSITY_TOLERANCE_POINTS` comment said the regenerate loop "is expected to read" it. It now says the loop never has and never will: the bound is structural. | `DENSITY_TOLERANCE_POINTS` |
| 5 | **Closed** — CARD-070, `3a86aeb` | Medium — stale pins | Three nudge tests pinned `bands.png`, which converts uniquely at 10×10 and needs no nudge. The pins moved to a picture that actually dithers (`landscape.png`). Re-checked: `tests/test_nudge.py` passes in full. | `tests/test_nudge.py` |
| 6 | **Closed** — `f3ba719` | Info — environment | `tests/test_sourcing_image.py` failed with `FileNotFoundError` because the `pictures/` corpus its trim criteria are measured over was not on `main`. The 25-image corpus was committed to `main` on 2026-09-12, so a fresh clone has it; CARD-087 then made the synthetic fixtures in `tests/fixtures/` match what their tests assert. Re-checked: 117 passed in a clean worktree. | `tests/test_sourcing_image.py` |
| 7 | **Not reproduced** | Info — flaky | Two exit-code assertions in `tests/test_timeout.py` failed once in a large batch. CARD-070 could not reproduce it in five runs; this refresh passed 17/17 three times. Kept as a note, not a known flake. | `tests/test_timeout.py` |
| 8 | **Open**, unchanged | Info — undocumented | Library mode at exactly 16×16 has no boundary cells, so a non-unique template spends 30 identical solves before abandoning (library mode never repairs). Documented only in the module docstring. | `sourcing.library` |
| 9 | **Open** — new | Low — lost work | When `MAX_CONSECUTIVE_ABANDONMENTS` candidates in a row are abandoned, `generate_batch` raises, and the puzzles it had already produced in that call are discarded with the exception. The admin stores a random batch only after the call returns, so a 50-puzzle batch that abandons three in a row late loses everything it made. Rare at today's rates (1 abandonment in 100 requests at 30x30), but the loss is total when it happens. Recorded, not fixed (CARD-092 G-1). | `orchestrator.generate_batch`, `admin.batch_generator.BatchGenerator._generate_random_batch` |
| 10 | **Open** — new | Low — docstring drift | About fifteen comments and docstrings in `orchestrator` still describe the retry bound as 20 or a batch as up to 200 — among them `orchestrator.BatchResult`'s `abandoned` ("20 draws each"), `orchestrator._lineage_key` ("at most 20"), the `GENERATION_BUDGET_SECONDS` comment ("20 retries"), `orchestrator.generate`'s `Raises` section ("20 infeasible candidates"), and two comments inside `orchestrator.generate_batch` ("20 draws failed", "200 candidates x 30s"). The same `generate_batch` comment says 30x30 at density 50 "reaches the deadline rather than the retry bound", which CARD-091 measured no longer true (0 timeouts in 100). Code behaviour is correct; the prose is not. | `orchestrator` |

---

## 11. Where this differs from the other documents

| Topic | `NONOGRAM_GENERATION_REQUIREMENTS.md` / `DIFFICULTY_ENGINE.md` say | Code does |
|---|---|---|
| Binarisation | Otsu threshold with a 50% fallback | Floyd–Steinberg dither after LANCZOS resize; grey < 128 is used only to find the ink box |
| Cell mapping | ~20 px per cell, majority vote | one resize to W×H cells, then dither |
| Rejection rules | reject grids with blank rows/cols or fill outside 20–80% | none; blank-line avoidance is best-effort via the trim |
| Quality score | 0–100 with accept ≥ 50 | no quality score on the core `Puzzle`; admin random batches store `None` |
| Difficulty | tiers at 70/85 on the quality score; `DIFFICULTY_ENGINE.md`'s strategy-count formula | ADR-0029's strategy ladder: the hardest rung the one verifying solve required, plus the share of cells settled at it, with tiers on ADR-0005's 33/66 cutoffs and a fourth `guess` tier keyed on `branch_nodes` (§7). Closer to `DIFFICULTY_ENGINE.md`'s intent than ADR-0013 was, but it is a rung and not a count, and the formula in the orphaned `analysis/strategy_counter.py` is still not the one that runs |
| Retry | "reject and retry with different settings" | random mode *repairs* a non-unique grid inside the solver-located ambiguity up to K = 5 times, then redraws; library redraws; image nudges up to 5 cells; all within bounds of 30/30/5 (§8) |
| Image limits | 100–2000 px, ≤ 2 MB, format allowlist | only a 2 MB cap, and only in the admin upload path |
| Determinism | same image and settings → same grid | true for image mode; random and library are seed-driven by design, and a seed replays repairs too. The grade is machine-independent: no clock reaches the score or the tier decision (§7, EC-016) |

---

## Refresh log

| Date | Verified against | What was re-checked | What was not |
|---|---|---|---|
| 2026-09-12 | `main` at writing | whole document, written from a full read | — |
| 2026-09-13 | `064611c`, `3635ea4`, `5914b6d` | §6.5 solver ladder; §7 grade; §8.3 tier notes; finding 3 | §8 loop structure, §9 |
| 2026-09-14 | `8ccbda9` (CARD-090) | the retry bound's value wherever cited | everything else |
| 2026-09-15 | `41096cf` (CARD-092) | §8 rewritten for POL-006 repair and K; §9 rewritten for CARD-083/088 batches and re-verified for image batches; §10 findings re-established, 9 and 10 added; every code reference converted from line anchors to symbols and resolved by `meta/ops/check_doc_references.py`; §10's suites re-run | §7's measured distribution and §8.3's tier-by-density table predate repair and were not re-measured (both said so in place) |
