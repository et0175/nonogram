# Puzzle Generation Algorithm — as implemented

**Status:** Reference, reverse-engineered from the code on `main` as of 2026-09-12.
**Supersedes for algorithm questions:** `docs/REQUIREMENTS/NONOGRAM_GENERATION_REQUIREMENTS.md`
(which describes an Otsu-threshold pipeline that was never built — see §11).
**Formal basis:** ADR-0001, 0002, 0003, 0005, 0011, 0013, 0015, 0022 under
`meta/architecture/decisions/adr/`; POL-001..POL-005 in `meta/architecture/domain/policies.yml`.

Every claim below carries a `file:line` anchor into `src/nonogram/` so it can be checked
against the source. Line numbers are those of the commit this document was written against.

---

## 1. What the generator promises

1. **Uniqueness.** A puzzle is returned only when the solver has counted *exactly one* solution
   to its clues. This is enforced at a single point (`orchestrator.py:674-688`) and gated at
   export (`orchestrator.py:734-750`).
2. **Bounded retries.** Three counters — regenerate, resample, pixel-nudge — each with a fixed
   cap, all advanced through one primitive (`orchestrator.py:409-501`).
3. **Bounded time.** One 30-second monotonic deadline per request, shared by every solve the
   request performs (`orchestrator.py:192`, `:1159`).
4. **Reproducibility.** One `random.Random` seeded once per request; the seed is recorded on the
   returned puzzle (`orchestrator.py:1146-1147`). See §10 finding 3 for the one caveat.
5. **Density.** Random grids honour the requested percentage within ±3 points — by construction,
   not by checking (`sourcing/random_grid.py:398-438`).

---

## 2. Pipeline overview

```
GenerationRequest (unvalidated, from CLI/web/admin)
  │
  ├─ resolve name            NameContext.name_for            orchestrator.py:1128
  ├─ parse difficulty tier   difficulty.parse_tier           orchestrator.py:1132-1136
  ├─ resolve extent (W,H)    _resolved_extent                orchestrator.py:1144, 780-813
  ├─ seed → random.Random    request.seed or secrets.randbits(64)   orchestrator.py:1146-1147
  ├─ deadline = now + 30 s                                    orchestrator.py:1159
  │
  └─ bounded loop(s) ──► attempt:
        source grid  ─►  compute clues  ─►  solve (count ≤ 2)  ─►  score
        (§4)             (§5)               (§6)                    (§7)
        list[list[bool]] tuple[tuple[int]]  SolveResult             float 0..100
                                            │
                       solution_count != 1 ─┴─► reject (regenerate / nudge)
                       score outside tier ──────► reject (resample)
  │
  ▼
Puzzle aggregate: grid, clues, solution_count, difficulty_score, seed, extent, counters
```

**Boundary types** (ADR-0012): a grid crosses every module boundary as `list[list[bool]]`,
row-major, `True` = filled; clues as `tuple[tuple[int, ...], ...]`, one tuple per line, with a
line of no filled cells encoded as `(0,)` — never `()` (`clues.py:47-48`). The solver's internal
bitmasks never leave the solver package.

---

## 3. Request resolution

All three of name, tier and extent are resolved **once**, before the aggregate exists, and are
never touched by a retry (`orchestrator.py:1126-1154`).

### 3.1 Extent — `(width, height)`

`_resolved_extent` (`orchestrator.py:780-813`) distinguishes three shapes of request:

| Request | Rule |
|---|---|
| both sides stated (`--size WxH`) | validated as given, each side independently in 10..30 (`random_grid.py:109-124`); the source's own shape is never consulted |
| one side stated (bare `--size N`) | completed from the source's shape by `random_grid.derive_extent` (`random_grid.py:243-358`) |
| neither | rejected with the shared range message |

**Bare-N derivation** (`random_grid.py:182-217`): N lands on the *longer* axis of the source's
own shape; the other side is `max(10, round(N * short / long))`. There is deliberately no upper
clamp — the derived side is ≤ N ≤ 30 by construction.

**Refusal** (`random_grid.py:150-179, 328-358`): if holding the short side at 10 would make the
centred crop keep less than half the source (exact integer test `2*kept >= whole`), the request
is refused with `SizeTooSmallForSource`, naming the smallest N that would work. The threshold is
exactly `N/5 : 1` (2:1 at N=10, 6:1 at N=30).

Each mode reports its own shape (`sourcing/__init__.py:85-89`): random → `(1, 1)` (a square,
`random_grid.py:127-147`); library → the template's cell extent, 16×16 today
(`library.py:245-273`); image → the **ink bounding box** in pixels, not the file's extent
(`image.py:503-555`).

### 3.2 Seed and deadline

- `seed = request.seed if given else secrets.randbits(64)`; one `random.Random(seed)` is passed
  as the last argument to every source call (`orchestrator.py:1146-1147, 1215`).
- `deadline = time.monotonic() + 30.0`, fixed once and handed to every `solver.solve` the
  request makes, retries included (`orchestrator.py:1159, 1188-1190`). It is a per-request
  budget, not per-solve: 20 retries cannot stretch it.

---

## 4. Sources (COMP-003)

Dispatch is a closed table of three callables (`sourcing/__init__.py:62-66`); the orchestrator
assembles each mode's argument list (`orchestrator.py:816-867`).

### 4.1 Random — `sourcing/random_grid.py:398-438`

```
validate_extent(width, height); validate_density(density)   # 0..100 inclusive
filled = round(width * height * density / 100)              # filled_target, :375-382
flat   = [True] * filled + [False] * (cells - filled)
rng.shuffle(flat); reshape to rows
```

Because the filled count is fixed before any draw, the only density error is the rounding of a
fractional cell: at most `0.5 / cells`, i.e. half a percentage point at 10×10. This is how
ADR-0003's ±3-point tolerance is met — nothing in the retry loop measures density.

Density 0 and 100 are *valid* inputs (`random_grid.py:78-84`) and produce all-empty / all-filled
grids. See §10 finding 2.

### 4.2 Library — `sourcing/library.py`

- Four templates (`cat`, `heart`, `house`, `moon`), each drawn as 16×16 ASCII art and parsed
  once (`library.py:141, 197-202`).
- **Rescale by exact area coverage** (`library.py:276-344`): each target cell maps back onto the
  rectangle of template cells it covers; `coverage` returns integer numerators over a shared
  denominator `16*16`, so "wholly inside" and "wholly outside" are exact at every extent. The
  two axes rescale independently — a non-square explicit `WxH` **stretches** the template
  (deliberate; ADR-0022/R3's crop rule is about user pictures, not built-in shapes).
- **Threshold** (`library.py:347-369`): a cell is filled iff `numerator >= threshold * denominator`.
- **The only randomness** is that threshold, drawn `rng.uniform(0.35, 0.65)` per attempt
  (`library.py:149-150, 411-415`). That is what "regenerate" means for a deterministic source:
  the same cat, a slightly fatter or leaner outline. Fully covered / uncovered cells never change.
- At **16×16** every coverage fraction is 0 or 1, so a retry renders the identical grid
  (`library.py:80-95`). See §10 finding 8.

### 4.3 Image — `sourcing/image.py:615-698`

Order is prescribed by ADR-0022 and is load-bearing (the request is judged *before* any crop):

| Step | Function | Detail |
|---|---|---|
| 1 | `random_grid.validate_extent` | range check before the file is touched (`:694`) |
| 2 | `load_greyscale` (`:216-262`) | `Image.open` + `load`; EXIF orientation applied; RGBA/LA/PA or `transparency` composited onto **white**; converted to mode `L`. Every Pillow failure → `UnreadableImage` |
| 3 | `ink_bounding_box` (`:276-326`) | ink = grey value **strictly below 128** (`INK_THRESHOLD`, `:200`); LUT + `getbbox`; no ink at all → whole extent |
| 4 | `validate_aspect_ratio` (`:445-500`) | on the **ink box**, not the file: refuse with `ImageNeedsManualCrop` when a centred crop to the grid's ratio would keep < 50% of it. Exact integers: `kept = min(sw*th, sh*tw)`, `whole = max(...)`, accept iff `2*kept >= whole` (inclusive at exactly 2×) |
| 5 | `greyscale.crop(box)` | trim blank margin to the ink box (FR-022, best-effort — it does not guarantee no blank rows/columns after resize) |
| 6 | `fit_crop_box` (`:357-422`) | largest **centred** sub-rectangle with the grid's aspect ratio; exactly one axis cropped; floor division; odd leftover pixel goes to the far side |
| 7 | `resize((W, H), LANCZOS, box=crop)` (`:587-591`) | crop and resize in one call, one grey level per cell |
| 8 | `convert("1", dither=FLOYDSTEINBERG)` (`:594`) | Pillow's built-in Floyd–Steinberg error diffusion |
| 9 | `to_grid` (`:597-612`) | `numpy.asarray(bilevel) == 0` → black pixel is a filled cell |

The `rng` argument is accepted for the uniform calling convention and **never drawn from**
(`:641-648`): the same file at the same extent always converts to the same grid. That is why
image mode does not enter the regenerate loop (§8.3).

Scope note (CON-013): calibrated for high-contrast silhouettes; photographs convert without
complaint but nothing is tuned for them.

---

## 5. Clue derivation (COMP-004) — `clues.py`

`encode_line` (`clues.py:64-84`) run-length encodes the filled runs of one line, returning
`(0,)` for a line with none. `compute_clues` (`:87-102`) applies it to every row and, via
`zip(*grid, strict=True)`, every column — a ragged grid raises rather than silently truncating.

---

## 6. Uniqueness solver (COMP-005) — `solver/`

**Question answered:** does this clue set have 0, 1, or ≥2 solutions? `solution_count` is
`0`, `1` or `MANY == 2` (`search.py:136`); the search stops the instant a second distinct
solution is recorded.

### 6.1 Representation — `propagate.py:443-541`

Each line is a pair of ints `(filled, empty)`; bit *i* set means cell *i* is known filled /
known empty. Row masks (column bits) and column masks (row bits) are kept in parallel and only
ever written together. `Board.clone` is four shallow list copies — the backtracking undo.

### 6.2 Line logic — `line_intersection` (`propagate.py:174-319`)

Input: canonical runs (empty marker stripped to `()`, `:147-171`), line length, known masks.
Output: `(filled_in_every_placement, empty_in_every_placement, placement_count)` or `None`
when no placement is consistent.

- Cheap rejections: runs plus mandatory gaps longer than the line → `None`; empty clue → one
  placement, every cell empty, unless something is already known filled; fully decided line →
  compare `mask_runs(known_filled)` to the clue directly (`:224-240`).
- Otherwise a DP over states `(pos, run_index)`, evaluated from the end of the line backwards.
  Each state stores the *union* of filled cells, the *union* of empty cells, and the placement
  count over all placements of runs `idx..` in cells `pos..`. Two transitions per state:
  leave `pos` empty (only if not known filled); or start run `idx` at `pos` (only if none of
  its cells is known empty and the cell after it is not known filled, or the run ends the line
  and is the last run) (`:265-312`). States that cannot fit the remaining runs are skipped via
  the `need[]` prefix (`:261-273`).
- A cell that is in the filled union but never in the empty union is filled in every placement,
  and vice versa (`:314-319`).

### 6.3 Propagation — `propagate` (`propagate.py:544-702`)

Sweep all dirty rows, then all dirty columns; every newly decided cell dirties the perpendicular
line; repeat until a sweep dirties nothing. Returns `False` the moment any line admits no
placement. At the fixed point every line admits ≥1 placement, so a fully decided board *is* a
solution. `board.decided` counts settled cells; per-line `placements` are cached for the
branching heuristic. The deadline is checked at the top of every sweep (`:610`).

A per-solve memo `LineCache` (`:347-440`) keyed by packed `(known_empty << length) | known_filled`
per line, cleared wholesale at 60 000 entries (`:106`); semantically invisible.

### 6.4 Search — `solve` and `_search` (`search.py:270-528`)

```
canonicalise clues; if Σ row runs ≠ Σ column runs → 0 solutions        :348-349
propagate from blank; contradiction → 0                                  :364-368
line_logic_cells = board.decided                                          :373
fully decided → 1 solution (verified)                                     :375-376
for round in 0, 1, 2, ...:                                                :381-389
    (probe_width, node_limit) = _SEARCH_ROUNDS[round] or last width × 3^k  :177-188, 438-443
    result = _search(root.clone(), ...)
    if result is not CUT_OFF: break        # a cut-off round's findings are discarded
count = len(solutions) ∈ {0, 1, 2}
```

Restart schedule `_SEARCH_ROUNDS` (`:177-183`):

| round | probe width | node limit |
|---|---|---|
| 0 | none (plain descent) | 400 |
| 1 | 8 | 400 |
| 2 | 16 | 1 200 |
| 3 | 32 | 3 600 |
| 4 | 64 | 10 800 |
| 5+ | 64 | ×3 per round, unbounded |

**Node expansion** (`_expand`, `:531-667`):

- *Round 0* (`_descend`, `:700-748`): pick the most constrained unknown cell — the least-placement
  line, then the least-placement perpendicular line through it (`_branch_cell`, `:782-858`);
  try the better-supported value first (`_preferred_value`, `:751-779`, support = product of
  surviving placements in row × column); if it survives propagation, push the *other* value as
  an unpropagated `_Pending` sibling (`:420-436`). If it contradicts, the other value is forced
  (a deduction, not a guess).
- *Rounds ≥ 1*: **probe** the `probe_width` most constrained unknown cells (ranked by
  row placements × column placements, `_probe_candidates`, `:861-897`). For each, assign both
  values on clones and propagate. Both contradict → node refuted. One contradicts → the other is
  forced, the pass restarts on the new board. Neither → the pair is a branch candidate, scored
  by `min(gain) * (cells+1) + sum(gain)`. A pass that forces nothing branches on the best pair
  (round 1) or a hash-diversified pair (`_diversified`, `:918-943`) so a restart walks a
  different tree.

**Why it is sound** (`search.py:39-66`): propagation only writes cells every placement agrees
on, so a contradicting probe proves no solution assigns that value; forcing the opposite
discards nothing. Both children of a branch always come from the same board (a pass that forced
anything restarts before its pool is used). Sibling subtrees differ in the branch cell, so two
recorded solutions are distinct. Cut-off rounds are thrown away whole.

**Self-check** (`_verified_grid`, `:960-988`): every completed board is re-encoded line by line
with `mask_runs` (`propagate.py:322-344`) and compared to the clues it was solved from, in both
orientations, before it counts. A mismatch raises `RuntimeError` — a solver defect, never a
puzzle outcome.

**Deadline** is checked at every node pop (`:496`) and every propagation sweep; past it,
`SolverTimeout` is raised and no verdict exists.

**Signals** (`SolveSignals`, `:197-248`): `line_logic_cells`, `total_cells`, `branch_nodes`
(nodes expanded by the *deciding* round only), `backtracks` (refuted assignments), `elapsed_seconds`.

**Independent verification:** `tests/property/test_solver_uniqueness.py` cross-checks the solver
against two brute-force counters in `tests/helpers/brute_force_oracle.py`, which imports only
`nonogram.clues`.

---

## 7. Difficulty score (COMP-006) — `difficulty.py`

Pure function of the solve's signals and the clues; never re-solves.

Normalised signals (`:437-478`), each in 0..1, larger = harder:

| signal | formula |
|---|---|
| `line_logic_gap` | `1 - line_logic_cells / total_cells` |
| `branch_pressure` | `min(1, branch_nodes / total_cells)` |
| `time_pressure` | `min(1, elapsed / (total_cells * 5/400))` (budget: 5 s per 400 cells, `:275`) |
| `size_pressure` | `(total_cells - 100) / (900 - 100)`, clamped |
| `density_pressure` | `1 - |density - 0.5| / 0.5` where density = Σ row clues / cells |

Score (`:481-535`), weights from `SIGNAL_WEIGHTS` (`:332-338`):

```
effort = 0.40 * line_logic_gap + 0.45 * branch_pressure + 0.15 * time_pressure
relief = 1 - 0.15 * (1 - size_pressure) - 0.15 * (1 - density_pressure)     # ∈ [0.70, 1]
score  = clamp(100 * effort * relief, 0, 100)
```

A puzzle solved by line logic alone has gap 0 and pressure 0, so scores ≤ 15 regardless of size.

Tiers (`:143-144, 211-228`): Easy `[0, 33]`, Medium `(33, 66]`, Hard `(66, 100]`. Cutoffs belong
to the lower band. `parse_tier` is case- and whitespace-insensitive (`:231-255`).

---

## 8. Retry policies (COMP-002)

All bounded loops use one primitive: `RetryCounter` (`orchestrator.py:409-455`) refuses to
advance past its bound; `run_bounded` (`:458-501`) calls an attempt until it returns a
non-`None` candidate, then raises `GenerationAbandoned` with the count, the bound and a reason.
Counters live on the `Puzzle` aggregate and are **never reset** during a request.

One attempt is `judge_candidate` (`:1167-1198`): record grid + clues → `solver.solve` with the
shared deadline → `confirm_uniqueness` (reject if count ≠ 1) → `score_difficulty` on the same
solve's signals → record score. This is the only `solver.solve` call in the module, so every
grid — fresh, re-rendered, uploaded or nudged — is judged identically.

### 8.1 Regenerate (POL-001) — bound 20

Random and library modes. A candidate whose clues have 0 or ≥2 solutions is discarded and the
source is called again with the same `rng` (`:1200-1215`).

### 8.2 Resample (POL-004) — bound 20, **shared budget**

Only when `--difficulty` is given. The resample loop *wraps* the regenerate loop
(`:1217-1230, 1280-1284`): one resample round runs the regenerate loop to obtain a unique
candidate, then keeps it only if `Tier.contains(score)`. Because neither counter resets, **at
most 20 grids are ever sourced per request**, however the two rejection causes divide them. An
exhausted inner loop propagates its own abandonment. Without a tier the check is vacuous and the
first unique candidate is returned.

### 8.3 Pixel nudge (POL-002/POL-003) — bound 5, image mode only

Image mode converts **exactly once** and never enters the loops above (`:1232-1238`). If the
conversion is not unique:

- attempt *n* (1..5) flips the best *n* cells of the **original** conversion — cumulative from
  the conversion, not from the previous nudge — and the result is fully re-solved
  (`:1246-1275`; `image.nudge`, `image.py:862-929`).
- Cell ranking (`nudge_cells`, `image.py:785-859`): (1) participation in 2×2 "switching" blocks
  (`# .` / `. #` diagonals), descending; (2) number of orthogonal neighbours with the other
  value, descending; (3) Chebyshev distance from the grid centre, ascending; (4) row, column.
  Greedy selection with a Chebyshev spacing of 1 between chosen cells; if spacing cannot supply
  enough cells the rest of the ranking fills in.
- At the cap: `GenerationAbandoned` saying the picture was never re-drawn and the tool has
  stopped altering it (`:914-960`).
- A conversion that is unique but **outside the requested tier** is not nudged; the run is
  abandoned immediately (`:1276-1277`).

### 8.4 What is never retried

`SolverTimeout`, `SizeOutOfRange`, `InvalidDensity`, `UnknownLibraryImage`, `UnreadableImage`,
`ImageNeedsManualCrop`, `InvalidPuzzleName`, `UnsupportedDifficulty` all propagate out of the
loops unchanged (`:40-50, 477-478`). A timeout says nothing about the candidate, and an invalid
request does not become valid by being asked again.

---

## 9. The admin panel's layer on top

Outside the orchestrator, but it changes what a batch user sees.

- **Size presets** (`admin/image_manager.py:30-35`): `small` = 10 on the short side with the
  long side following the picture (a full pair, since `derive_extent` cannot express this);
  `medium` = bare 20; `large` = bare 30; `auto` = bare N where N = `min(long_edge_px // 2, 30)`
  (≥ 2 source pixels per cell); `min` = that minus 5 (`:215-256`).
- **Fit policy** (`:26, 165-200`): the chosen grid must keep ≥ 90% of the ink box
  (`MIN_KEPT_SHARE`, integer cross-product share). Otherwise the picture moves to the Large
  preset's grid (`MOVED_TO_LARGE`) if that keeps enough, else it is skipped (`CANNOT_FIT`).
  This is stricter than the sourcing module's own 50% refusal.
- **Abandonment retry** (`admin/app.py:40-77`, `image_manager.py:258-300`): if
  `orchestrator.generate` raises `GenerationAbandoned` at the predicted extent, the batch retries
  at the long-side −1 and +1 neighbours (ordered by how much of the picture each keeps), at most
  2 extra full runs; any other `NonogramError` on a neighbour ends the retry and the first
  abandonment is reported.
- **Random batches** (`admin/batch_generator.py:310-315` → `orchestrator.generate_batch`,
  `orchestrator.py:1287-1347`): count 1..200, a size drawn per puzzle from the list with an
  **unseeded** `random.Random`, density **hardcoded to 50**, tier `None`. The per-puzzle seed is
  drawn inside `generate` but is not persisted to the database.

---

## 10. Correctness review

Method: full read of the modules above; targeted probes; and the suites
`tests/property/test_solver_uniqueness.py`, `test_solver.py`, `test_orchestrator.py`,
`test_resample.py`, `test_nudge.py`, `test_sourcing_{random,library,image}.py`,
`test_difficulty.py`, `test_timeout.py` — **515 passed, 16 failed** on this tree, every failure
accounted for below (findings 5 and 6).

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
- **Retry accounting.** ≤ 20 grids sourced per request; ≤ 5 nudges; timeouts and invalid input
  never consume a retry; the deadline is per request.
- **Density.** Rounding-only error, inside ±3 points at every supported extent.
- **Aspect logic.** `derive_extent`'s half-retention predicate and `validate_aspect_ratio` are
  the same integer arithmetic, both inclusive at 2×, so a derived extent always passes the guard.

### 10.2 Defects and gaps

| # | Severity | Finding | Where |
|---|---|---|---|
| 1 | Low — latent bug | `generate_batch` checks `difficulty_tier` against enum **names** (`EASY`, `MEDIUM`, `HARD`), so `"Easy"` and `"easy"` raise `ValueError` even though the docstring says `"Easy"` and `parse_tier` is case-insensitive. Every caller passes `None` today. Fix: validate with `difficulty.parse_tier`. | `orchestrator.py:1322` |
| 2 | Medium — spec gap | Density 0 and 100 are accepted and yield all-empty / all-filled grids that pass the uniqueness check (score 0.000 / 0.001, tier Easy). `random_grid.py:78-82` says later stages reject them; none does. Decide whether to reject in `validate_density` or document them as allowed. | `random_grid.py:83-84` |
| 3 | Low — reproducibility caveat | `time_pressure` (weight 0.15) makes the score, hence the tier, machine-dependent. With `--difficulty` requested the same seed can keep or resample a boundary candidate differently on a slower machine. ADR-0015's "same seed replays the same run" holds unconditionally only without a tier. | `difficulty.py:275, 469` |
| 4 | Low — docstring drift | `random_grid.py:86-90` says the regenerate loop "is expected to read `DENSITY_TOLERANCE_POINTS`". It never does and never needs to; the bound is structural. | `random_grid.py:86-90` |
| 5 | Medium — stale pinned tests | Three nudge tests pin `tests/fixtures/bands.png` at 10×10 as needing exactly 2 nudges. On this tree it converts uniquely on the first solve (0 nudges). The ink box is the whole 32×32 file, so the FR-022 trim is not the cause; the untrimmed conversion is unique too. Either the fixture bytes or the resize/dither path changed since the pin was taken. The nudge mechanism itself passes its scripted tests. | `tests/test_nudge.py:322-340` and the two cap tests on the same fixture |
| 6 | Info — environment | 13 tests in `tests/test_sourcing_image.py` fail with `FileNotFoundError` for `pictures/`: the corpus the trim criteria are measured over is not on disk. | `tests/test_sourcing_image.py` |
| 7 | Info — flaky | `tests/test_timeout.py` passed 17/17 in isolation twice; one earlier run in a larger batch showed two exit-code assertions failing. Timing-dependent. | `tests/test_timeout.py` |
| 8 | Info — undocumented | Library mode at exactly 16×16 has no boundary cells, so a non-unique template spends 20 identical solves before abandoning. Documented only in the module docstring. | `library.py:80-95` |

---

## 11. Where this differs from the other documents

| Topic | `NONOGRAM_GENERATION_REQUIREMENTS.md` / `DIFFICULTY_ENGINE.md` say | Code does |
|---|---|---|
| Binarisation | Otsu threshold with a 50% fallback | Floyd–Steinberg dither after LANCZOS resize; grey < 128 is used only to find the ink box |
| Cell mapping | ~20 px per cell, majority vote | one resize to W×H cells, then dither |
| Rejection rules | reject grids with blank rows/cols or fill outside 20–80% | none; blank-line avoidance is best-effort via the trim |
| Quality score | 0–100 with accept ≥ 50 | no quality score on the core `Puzzle`; admin random batches store `None` |
| Difficulty | tiers at 70/85 on the quality score; `DIFFICULTY_ENGINE.md`'s strategy-count formula | ADR-0013 `100·effort·relief`, tiers at 33/66 (§7). The strategy-count formula exists only in the orphaned `analysis/strategy_counter.py` |
| Retry | "reject and retry with different settings" | POL-001/002/004 with caps 20/5/20 (§8) |
| Image limits | 100–2000 px, ≤ 2 MB, format allowlist | only a 2 MB cap, and only in the admin upload path |
| Determinism | same image and settings → same grid | true for image mode; random and library are seed-driven by design |
