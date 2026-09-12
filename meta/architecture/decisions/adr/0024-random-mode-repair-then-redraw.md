# ADR-0024: Random-mode recovery repairs the candidate, then redraws

**Status:** Accepted
**Date:** 2026-09-12
**Deciders:** Puzzle Creator (project owner)
**Revised:** —
**Migration:** rewrite
**Pattern:** —
**API-Posture:** —

## Context

In random mode the pipeline draws a grid from the injected `random.Random`
(ADR-0015), derives its clues (FR-005), and asks the solver (ADR-0009) whether
those clues have exactly one solution (FR-006). When they do not, FR-007 and
POL-001 today react in one way: discard the candidate and draw a fresh grid,
under the single 20-attempt bound ADR-0002 fixes (`MAX_RETRY_ATTEMPTS`, INV-003,
enforced by `run_bounded` in the orchestrator). Because the clues come from a
real grid, the failing verdict in random mode is always MANY — a count of 0
cannot occur — so every failure is an *ambiguity*: two or more grids satisfy
the same clues.

docs/GENERATION_ALGORITHM.md §10.2 records that this reaction has poor odds
exactly where it matters. Mid-density grids at 30x30 and above are rarely
unique on a fresh draw, and abandonment after 20 attempts (`GenerationAbandoned`,
POL-005) is a real outcome for such requests. Each redraw re-rolls the same odds
from scratch and throws away what the previous solve learned. FR-024 changes
what the solver can tell the orchestrator: alongside `solution_count`,
`solution` and `signals`, the result now carries the grid-shaped mask of cells
line logic left undecided at its first propagation fixed point, and — on MANY —
a second witness solution distinct from the first. The cells on which the two
witnesses disagree are a subset of that mask (EC-011), and, because two
solutions of the same row clues have equal filled counts per row, every row the
witnesses disagree on holds both a filled and an empty cell of the parent grid.
The ambiguity is therefore *locatable*, and usually a handful of cells.

FR-025 asks how random-mode recovery should use this. Three shapes are on the
table: keep redrawing (the status quo), REPAIR the current candidate by
flipping one filled cell and one empty cell inside the ambiguity region and
re-verifying, or a hybrid in which both reactions fire under one counter. A
sub-choice is folded in: whether the repair draws its pair from the
witness-disagreement set or from the wider undecided mask.

Several things hold regardless of the choice and are not decided here. Every
recovered grid — redrawn or repaired — is re-verified by the real solver before
it can be accepted (CON-005, INV-002, AC-112): the orchestrator never assumes
uniqueness. Redraws and repairs count against the ONE ADR-0002 bound (INV-003,
AC-113, EC-013) — there is no second bound. A repaired grid keeps the filled
count exact, so FR-004's requested density is preserved by construction rather
than by ADR-0003's tolerance (AC-114), and it differs from its parent only
inside the region (AC-132). Library and image modes are untouched — image mode
has its own recovery (POL-002's pixel nudge, which FR-013 now also drives from
the FR-024 mask). Whatever the repair does must be a deterministic function of
the seed and the region (ADR-0015, NFR-007's spirit), never of host state, so
the same seed replays the same lineage. `SolverTimeout` (ADR-0011) and invalid
input propagate through `run_bounded` unchanged and are never retried.

## Decision

We will adopt **`redraw_then_repair`**: on a MANY verdict for a random-mode
candidate the orchestrator first REPAIRS the current grid and re-verifies it,
up to K consecutive times on the same lineage; if the lineage is still not
unique after K repairs, the candidate is discarded and a fresh grid is drawn
from the same injected rng (POL-001), and recovery continues from there.

The mechanism, pinned so that AC-111/AC-132/AC-114 have one reading:

- **Region.** The repair draws its pair from the *witness-disagreement set* —
  the cells on which the solver's two witnesses (FR-024) differ. Only if that
  set contains no filled/empty pair of the parent grid (which the per-row
  filled-count argument in Context says cannot happen for a genuine
  disagreement, but which the code must not assume) does the repair fall back
  to the wider first-fixed-point undecided mask. Cells outside the chosen
  region are never touched.
- **Flip.** Exactly one cell that is filled in the parent becomes empty and
  exactly one cell that is empty in the parent becomes filled, both inside the
  region. The filled count of the repaired grid equals its parent's, so the
  density the request asked for holds by construction.
- **Pair choice.** Deterministic given the grid and the witnesses, with no rng
  draw: the region's filled cells and empty cells are each ranked by (row,
  column) and the first of each is taken. The same seed therefore replays the
  same repair lineage on every machine (ADR-0015).
- **Re-verify.** The repaired grid's clues are re-derived (FR-005) and solved
  in full through the same judge path as any other candidate — the real solver
  forms the verdict (CON-005), and the orchestrator's `confirm_uniqueness`
  gate is the only acceptance point (INV-002). A repaired grid is never
  assumed unique because it was repaired.
- **Escape.** K consecutive repairs on one lineage without a unique verdict
  end the lineage: the grid is discarded and POL-001 redraws. K is a named
  tunable constant beside `MAX_RETRY_ATTEMPTS` in the orchestrator, initial
  value **3**, to be recalibrated once a seeded corpus has been measured. K is
  a *split* of the one budget, not a second bound.
- **Bound.** Every repair and every redraw advances the same `RetryCounter`
  ADR-0002 already bounds at 20 (INV-003). When it is exhausted the run
  abandons with the existing `GenerationAbandoned` (POL-005), whichever kind
  of attempt came last.

Domain-model reading: POL-006 (`RepairCandidateOnUniquenessFailure`, CMD-014,
EVT-015) becomes the repair policy for random mode; POL-001 stays for the
redraw and for library mode, where nothing changes.

This is the owner's choice over the surfacing default (`pure_repair`), and the
reason is worth recording: a repair lineage has no monotonic-progress
guarantee — a pair flip can open a new ambiguity elsewhere — and under a shared
bound one bad lineage could consume the whole request. The K-then-redraw rule
keeps repair's upside (it targets the located ambiguity directly, at the cost
of one solve per attempt, the same as a redraw) while buying a cheap escape
back to redraw's independent-sample property. Pure redraw, the status quo,
discards the solver's knowledge of where the ambiguity is and re-rolls poor odds
on exactly the mid-density grids where abandonment is observed today.

## Alternatives considered

### pure_redraw

Keep today's reaction: discard the candidate and call the random source again
with the same rng; POL-006 is never enabled and FR-024's mask is consumed only
by the image nudge (FR-013). Its merits are real — zero change to `run_bounded`
and POL-001, every existing seed's replay is preserved, and each attempt is an
independent sample, so no pathological candidate can burn the budget. It was
rejected as wasteful: it throws away a grid that was ambiguous in a handful of
cells and re-rolls odds that are poor exactly where it matters (mid-density
30x30+ grids, where §10.2 shows abandonment after 20 attempts is a real
outcome), and it ignores the ambiguity locator FR-024 was added for. AC-111,
AC-132 and AC-114 would simply be dropped.

### pure_repair

POL-006 replaces POL-001 for random mode: on MANY, flip one pair inside the
region of the CURRENT candidate, re-derive clues, re-solve, and repeat on the
repaired grid until the count is 1 or the single counter of 20 is exhausted.
This was the surfacing default and the intake's own recommendation: one
reaction, one counter, no interleaving rule — the least machinery that uses the
locator. It was rejected by the owner because attempts on a repair lineage are
correlated: a pair flip can open a new ambiguity elsewhere, so there is no
monotonic-progress guarantee, and under the shared bound a bad lineage can in
principle spend all 20 attempts on one candidate a fresh draw would have
escaped — with the abandonment then reading as a repair failure rather than a
sampling failure, and no escape hatch short of exhausting the request. The
chosen hybrid keeps everything this alternative does well (the same region
rule, the same deterministic pair choice, the same exact-density flip) and
adds only the escape.

### redraw_then_repair (chosen — ordering variant rejected)

policies.yml sketched the hybrid as POL-001 firing first and POL-006 following.
That ordering was rejected within the chosen alternative: redrawing *before*
repairing discards the very candidate whose ambiguity the solver has just
located, so the first reaction to a MANY verdict is the repair, and the redraw
is the escape after K repairs on one lineage fail. The hybrid's acknowledged
cost — an interleaving constant nobody has measured a need for yet, and a
harder-to-explain abandonment message — is accepted; K is named, initial, and
explicitly scheduled for recalibration against a seeded corpus, and the
abandonment message keeps ADR-0002's uniform `GenerationAbandoned`.

## Consequences

### Positive

- The ambiguity FR-024 locates is acted on directly: a switching block is
  broken by one pair flip, so the expected number of solves to reach
  uniqueness on a nearly-right grid is small, where pure redraw's is unbounded
  in expectation on mid-density grids. Each repair costs one solve — the same
  as one redraw.
- Density holds exactly on every repaired grid by construction (one filled
  cell out, one empty cell in), with no reliance on ADR-0003's ±3-point
  tolerance; and the change is local, so the picture of a nearly-right grid
  survives — which matters for library-derived and book workflows.
- The K-then-redraw rule caps the cost of a correlated lineage at K solves
  before the independent-sample property of a fresh draw is restored; no
  candidate can eat the whole request.
- The repair is a deterministic function of the grid and the witnesses with no
  rng draw, so ADR-0015's reproducibility extends to the repair lineage
  unchanged: the same seed produces the same accepted grid on every machine,
  and the rng stream itself is not perturbed by repairs.
- One bound, one primitive: repairs are attempts inside the existing
  `run_bounded` loop and the existing counter, so INV-003 and POL-005 need no
  new machinery and AC-113's "both kinds in one counter" is structural.

### Negative

- Every existing random seed that ever hit MANY now maps to a different
  accepted grid. ADR-0015's reproducibility is per-version anyway, but an
  export's recorded seed no longer regenerates a pre-change puzzle.
- K is chosen without measurement. Three consecutive repairs is a guess about
  how often a lineage converges versus wanders; it may prove too tight
  (escaping lineages one flip from unique) or too loose (spending budget on
  wandering ones). The recalibration is owed, not optional, and needs a
  seeded corpus that records per-seed lineage outcomes.
- `run_bounded` gains a branch: the attempt callable must know whether the
  current candidate is a fresh draw or a repair of the previous one, and how
  many consecutive repairs it has had. The retry tests must cover both kinds of
  attempt inside one counter (AC-113) and the K boundary on both sides.
- The abandonment message is harder to make exact. `GenerationAbandoned` still
  names the attempt count and the bound, but "20 attempts" now mixes redraws
  and repairs; a user reading the message cannot tell how many distinct grids
  were tried.
- The fallback to the wider undecided mask, kept for safety, is a second
  region rule that AC-111/AC-132 do not distinguish from the primary one; a
  test must force it explicitly or it is dead code with a latent bug.

### Neutral

- Sequencing: FR-024's solver change (mask and second witness on `SolveResult`)
  must land before this ADR can be implemented — a requirement dependency, not
  a DEC dependency. The FR-024 card is cut first.
- Image mode is unaffected: its recovery remains POL-002's pixel nudge, now
  driven from the same FR-024 mask (FR-013), under its own 5-attempt cap.
  Library mode keeps POL-001 unchanged.
- Domain model: POL-006 becomes the repair policy for random mode (CMD-014
  `RepairCandidate`, EVT-015 `CandidateRepaired`, always followed by a fresh
  CMD-005 solve); POL-001 stays for the redraw. FR-007's mechanism note and
  POL-001's rationale should be re-worded to say "repair, then redraw after K"
  for random mode.
- Related ADR revisions (recorded here; those files are not rewritten):
  - **ADR-0002** — History: repairs and redraws share the one 20-attempt
    bound; K is an interleaving split of that budget, not a second bound.
    The 20 and the 5 stand.
  - **ADR-0009** — History: the solver contract gains, on `SolveResult`, the
    first-fixed-point undecided mask and, on MANY, a second witness distinct
    from the first (FR-024). Strategy, fail-fast on the second solution (the
    second solution the search already stops on IS the second witness) and
    the ADR-0014 oracle cross-check are unchanged.
  - **ADR-0012** — History: the boundary rule is extended — the mask and the
    witnesses cross the module boundary as grid-shaped `list[list[bool]]`
    structures, never as the internal bitmask pair (EC-012).
- Observability worth adding when the card lands: a per-run count of repairs
  versus redraws (and of lineages that hit K) in the orchestrator's run
  summary, since that is exactly the data the K recalibration needs.
- A future decision may want the repair lineage recorded in export provenance
  (which attempts were repairs). Not decided here; ADR-0023's schema is
  untouched.

## Rules

```yaml
- id: ADR-0024/R1
  statement: A repaired random-mode grid is accepted only after a fresh solver run on its own re-derived clues reports solution_count exactly 1. The orchestrator never assumes uniqueness from the fact that a grid was repaired.
  scope: {contexts: [CTX-001], code: ["src/nonogram/orchestrator.py"]}
  check: {kind: test, ref: PropertyTest_Recovery_AcceptedGridsHaveRealVerdictsWithinOneBound}
  severity: mandatory
- id: ADR-0024/R2
  statement: Repairs and redraws advance the same RetryCounter bounded by MAX_RETRY_ATTEMPTS (20). K, the consecutive-repair limit on one lineage, is a named constant beside it and is never a second bound; exhausting the counter raises GenerationAbandoned whichever kind of attempt came last.
  scope: {contexts: [CTX-001], code: ["src/nonogram/orchestrator.py"]}
  check: {kind: test, ref: TestRecovery_RepairAttemptsCountAgainstRetryBound}
  severity: mandatory
- id: ADR-0024/R3
  statement: A repair flips exactly one filled cell and one empty cell of the parent grid, both inside the witness-disagreement set (falling back to the undecided mask only when that set holds no filled/empty pair), so the filled count is preserved and no cell outside the region changes.
  scope: {contexts: [CTX-001], code: ["src/nonogram/orchestrator.py"]}
  check: {kind: test, ref: TestRecovery_RepairKeepsFilledCountExact}
  severity: mandatory
- id: ADR-0024/R4
  statement: The repair's pair choice is a deterministic function of the grid and the solver's witnesses — the region's filled and empty cells ranked by (row, column) — and draws nothing from the injected Random or from host state, so a seed replays the same repair lineage everywhere.
  scope: {contexts: [CTX-001], code: ["src/nonogram/orchestrator.py"]}
  check: {kind: review-lens}
  severity: mandatory
- id: ADR-0024/R5
  statement: The repair policy (POL-006) fires only for random mode. Library mode recovers by POL-001 redraw and image mode by POL-002 pixel nudge; neither ever repairs.
  scope: {contexts: [CTX-001], code: ["src/nonogram/orchestrator.py"]}
  check: {kind: review-lens}
  severity: mandatory
```

## References

- DEC-029 (resolved by this ADR)
- CTX-001 (Puzzle Creation — the only affected context; COMP-002 orchestrator
  is the single enforcement point)
- FR-025 (the requirement this ADR decides), FR-024 (the ambiguity locator it
  consumes), FR-007 / POL-001 (the redraw it retains), FR-004 (density
  preserved by construction)
- AC-111, AC-132, AC-114 (repair-containing criteria — survive), AC-112,
  AC-113 (hold under every alternative); EC-013, EC-011, EC-012
- INV-002, INV-003, CON-005; POL-005, POL-006, CMD-014, EVT-015, EVT-006
- ADR-0002 (retry bounds — revised by History entry recorded above),
  ADR-0009 / ADR-0012 (solver contract and boundary rule — FR-024 revisions
  recorded above), ADR-0003 (density tolerance, not relied on for repaired
  grids), ADR-0011 (SolverTimeout propagates, never retried), ADR-0015
  (reproducibility — repair is rng-free)
- docs/GENERATION_ALGORITHM.md §8.1, §10 (the evidence for poor redraw odds)
- `src/nonogram/orchestrator.py` — `run_bounded`, `RetryCounter`,
  `MAX_RETRY_ATTEMPTS` (K is added beside it)

## History

- 2026-09-12: Created — resolves DEC-029. Owner chose `redraw_then_repair`
  over the surfacing default `pure_repair`: repair the current candidate from
  the witness-disagreement set up to K=3 consecutive times, then redraw, all
  under ADR-0002's single 20-attempt bound; K is an initial value pending
  corpus measurement. Migration `rewrite`: today's pure-redraw loop in the
  orchestrator must be brought to this decision once FR-024's solver change
  has landed.
