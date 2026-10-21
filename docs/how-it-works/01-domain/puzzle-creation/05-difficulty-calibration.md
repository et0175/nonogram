# 05 — Difficulty calibration (CAP-004 / COMP-006)

> Scope: `src/nonogram/difficulty.py`, 592 lines. Plus POL-004's resample
> predicate, which lives in the orchestrator.

## Why the score is a ladder and not a formula

The question COMP-006 answers is *what kind of reasoning did this puzzle demand?*
— as a tier, and as a single number on the fixed 0..100 scale the export, the DB
column and POL-004's resample predicate have always carried.

ADR-0013 originally answered it with a weighted sum of solver signals (line-logic
coverage, backtracking amount, solve time, size, clue density). ADR-0029 replaced
that with a **strategy ladder**, and the replacement is what the code implements.
Two of ADR-0013's terms were deliberately removed, and each removal is a
constraint in its own right:

- **No clock.** NFR-007 / CON-014 / ADR-0029/R3: wall-clock solve time never
  enters the score, so the same seed grades the same on any machine.
  `SolveSignals.elapsed_seconds` exists and is "telemetry, and only telemetry …
  It is the one field here a second run on a slower machine changes, which is
  exactly why nothing graded may depend on it" (`solver/search.py:367`).
- **No size and no density term.** `orchestrator.py:1882` records the call-site
  consequence: "The clues are no longer passed — ADR-0029 took density out of the
  score."

`difficulty.py` is a pure function module (`:7`): no I/O, **no clock**, no
randomness, no module state, and — the important one — **no solver re-entry**.
Everything it needs was already measured by the one solve that produced the
candidate. The resample loop calls `score_difficulty` once per candidate, "so a
scorer that solved again would double the cost of every generation."

## The ladder, and the arithmetic

```
simple_overlap  <  line_dp  <  probe_contradiction        # difficulty.py:236 LADDER
```

Three rungs, spelled out here rather than imported from `nonogram.solver`
(`difficulty.py:228`) because ADR-0007 forbids the lateral import, and pinned
against `solver.RUNG_ORDER` from the test tree. `guess` is **not** a rung: a solve
that branched is reported as the `guess` *strategy*, never as a tier.

A puzzle's difficulty is the **hardest rung its one verifying solve needed**.
Within a rung, puzzles are ordered by the share of the grid that rung settled.
The 0..100 number is a derived *presentation* of that pair, not the grade itself
(`difficulty.py:25`):

```python
rung  = hardest rung with at least one cell settled at it
share = rung_cells[rung] / total_cells
score = band_low(rung) + share * band_width(rung)
```

`score_difficulty` (`:418`) is exactly that, with a clamp on each side:

```python
rung = hardest_rung(signals.rung_cells)
if rung is None:
    return SCORE_MIN
low, high = RUNG_BANDS[rung]
share = _clamp(signals.rung_cells[rung] / total_cells, 0.0, 1.0)
return _clamp(low + share * (high - low), SCORE_MIN, SCORE_MAX)
```

ADR-0029/R1's cross-rung monotonicity holds **structurally**, not by test: the
share is `<= 1` so a rung cannot outscore its own band's top, and a rung is
*present* only if it settled a cell, so its share is `> 0` and it cannot reach its
band's floor. Two puzzles at different top rungs therefore never overlap, whatever
their extents.

`hardest_rung` (`:398`) derives the rung from the **counts** rather than reading
the solver's own ordered `rungs` list, deliberately: "the two are the same fact
twice, and re-deriving it here from the one input the score already needs makes a
disagreement between them a test failure rather than a silent regrade." A rung
name this module does not know is ignored rather than raising, because "a solver
that grew a fourth rung would be a decision to take, not a crash to discover at
the scorer."

## Two tables, and why they must not be derived from each other

This is the subtlest thing in the module, and it is worth getting exactly right.

**Rung bands** — what `score_difficulty` reads (`difficulty.py:342`):

| Rung | Band |
|---|---|
| `simple_overlap` | `[0, 33]` |
| `line_dp` | `(33, 66]` |
| `probe_contradiction` | `(66, 100]` |

From `RUNG_OVERLAP_MAX_SCORE = 33.0` and `RUNG_LINE_DP_MAX_SCORE = 66.0`.

**Tier bands** — what `classify` reads (`difficulty.py:316`):

| Tier | Band |
|---|---|
| `Tier.EASY` | `[0, 33]` |
| `Tier.MEDIUM` | `(33, 90]` |
| `Tier.HARD` | `(90, 100]` |

From `EASY_MAX_SCORE = 33.0` and `MEDIUM_MAX_SCORE = 90.0`, ADR-0005's two
cutoffs — "the single tuning surface it asked for".

`RUNG_BANDS` used to be *zipped* from `TIER_BANDS`. `difficulty.py:342` records
why it no longer is, and the reason is the clearest statement of the module's
design in the file: the zip encoded ADR-0029's claim that **a tier *is* a rung**;
that claim is what made Medium unreachable; the cutoff move retired it. "Deriving
one table from the other now would re-assert it, and would make the next retune of
a tier cutoff silently re-scale every score."

So the two kinds of edit are different acts: **moving a rung boundary re-scales
every score; moving a tier cutoff re-files scores that do not change.**

### Where 90.0 came from, and what it did to Medium

`MEDIUM_MAX_SCORE` moved from `66.0` to `90.0` on the owner's decision of
2026-09-23 (CARD-137) — the recalibration ADR-0005 had been owed since ADR-0029.
`difficulty.py:212` states both the defect and the fix:

At 66.0 the cutoff coincided with a rung boundary, so Medium meant "topped out at
`line_dp`" — **measured at 5 puzzles in 300 on production.** At 90.0 it coincides
with nothing on the ladder and sits *inside* the probe rung's band. Re-derived
from the two tables: `(90 - 66) / (100 - 66)` = **70.6% of the grid**. So Medium
is now "a little non-trivial work" and Hard is "a lot", and a score of 70 and a
score of 95 are different tiers although both puzzles needed a probe.

`EASY_MAX_SCORE` is unchanged since ADR-0005 and still coincides with the top of
the bottom rung's band, which is what lets a full-share `simple_overlap` puzzle
score exactly 33.0 and stay Easy. **Easy therefore still means exactly "the
overlap rule finished it."**

No stored grade moved, because `RUNG_BANDS` — the table the *score* is built from
— was deliberately not touched.

## One classifier, enforced by an `ast` walk

```python
def classify(score: float) -> Tier:          # difficulty.py:464
    if score <= EASY_MAX_SCORE:   return Tier.EASY
    if score <= MEDIUM_MAX_SCORE: return Tier.MEDIUM
    return Tier.HARD
```

This is the only implementation of the band rule in the package, and that is
enforced by an `ast` walk in `tests/test_difficulty_tiers.py` (`:171`): "A module
that compared a score against `EASY_MAX_SCORE` itself would be a second classifier
that a retune could silently leave behind." Same shape of guard as the import
walk — the project's recurring answer to "two places that must agree".

The cutoffs belong to the **lower** band — 33.0 is Easy and 90.0 is Medium —
ADR-0005's inclusive-upper-bound reading, and what makes a full-share bottom rung
land on 33.0 as Easy rather than a third of a point outside it.

`classify` is total on the whole real line, not just on 0..100: a score below
`SCORE_MIN` reads as Easy and one above `SCORE_MAX` as Hard. `score_difficulty`
cannot produce either, "and a classifier that raised on them would only turn a
scale bug into a crash at the point furthest from its cause."

## The fourth tier that was retired on evidence

`Tier` has three members. ADR-0025 added a fourth, `GUESS`, keyed on the solve's
`branch_nodes` rather than on a number; ADR-0031 / CARD-098 retired it.

`difficulty.py:255` records the evidence rather than an argument: its measured
assignment rate was **zero everywhere anyone looked — 0 of 6,620 (ADR-0029), 0 of
462 (CARD-076), 0 of 16 stored rows** — and CARD-072 established *why*: no random
draw in the supported range branches at all after the solve's one-step lookahead
phase, so the tier was not merely rare but **unreachable from generation**.

ADR-0025's own argument for keeping it — a safety net for a future source that
does branch — is answered rather than dismissed: branching is still reported, as
the `guess` **strategy** (FR-029, `solver.STRATEGY_GUESS`). "The fact survives;
only the claim that it is a *difficulty* does not."

Retiring it collapsed two shapes the code had been carrying: `classify` lost its
second argument, and `Tier.band` stopped answering `None` for one member. Every
tier has a band again.

`_RETIRED_GUESS_TIER = "guess"` (`:513`) survives as a **reading rule only**: no
build writes it, `parse_tier` refuses it like any other unknown word, and nothing
migrates the rows that carry it. `tier_of_record` (`:516`) is the total,
never-raising reader for stored or submitted text; `parse_tier` (`:562`) is the
*input* rule that rejects, "because a user who typed `--difficulty extreme` needs
to be told (AC-021)."

## `Tier` is a `StrEnum`, and that is load-bearing

```python
class Tier(StrEnum):
    EASY = "easy"; MEDIUM = "medium"; HARD = "hard"
```

So the tier *is* its `--difficulty` spelling: "the value a user types, an export
payload carries and a PDF filename is built from are one string, with no lookup
table between them" (`:245`). `Tier.label` is the capitalised display form AC-020
uses — presentational, so a label may be renamed ("Hard" → "Expert") without
touching the enum *value* that every stored row, export payload and filename
depends on.

`cli.py` reads the vocabulary from `difficulty.Tier` rather than spelling it out
(`cli.py:313`), so `--help` cannot drift from what `parse_tier` accepts — and
carries **no** `choices=`, because AC-021 asks for an unsupported tier to be
rejected as a domain error with exit code 3 rather than an argparse usage error
with exit code 2.

## How the tier is used: POL-004 discards, it does not steer

CON-004 is restated at `difficulty.py:272`: "a tier is a bucket a *scored*
candidate fell into, never a construction target." Asking for `Tier.EASY` makes
the pipeline **discard** candidates that classified elsewhere; it does not steer a
grid toward being easy. `orchestrator.py:26` says the same from the other side:
"a requested tier never reaches the *sourcing* of a grid."

The predicate is one comparison, in one place:

```python
# orchestrator.py:1250  Puzzle.difficulty_in_requested_tier
if self.requested_tier is None:
    return True
return self.difficulty_tier is self.requested_tier
```

Two states are worth distinguishing. `requested_tier is None` means "no tier was
requested", which makes POL-004's check **vacuous rather than absent** — the loop
still runs, every candidate is still scored, and the first unique one is accepted.
And a candidate that has not been scored yet returns `False`, "so 'in tier' is
never claimed on the strength of a previous candidate's solve (AC-026)."

`Puzzle.difficulty_tier` (`orchestrator.py:1231`) classifies **on every read**
rather than storing the tier beside the score, "so the tier and the rule it comes
from cannot fall out of step with each other."

## Bounds and honest gaps

- **Heuristic bands, not a construction guarantee** (CON-004). The tier describes
  what the one verifying solve needed; it is not a promise about how a human will
  experience the puzzle.
- `score_difficulty` is total and refuses no input. A candidate with no rung
  attribution at all scores `SCORE_MIN`, and `:130` is careful about what that
  means: "that is the 'not a puzzle' case, which INV-002 has already discarded
  before anything calls this, so the number means nothing rather than meaning
  'easy'."
- **Two stale docstrings inside the codebase**, both describing the retired tier
  as live. `orchestrator.py:1054` says `branch_nodes` "decides `Tier.GUESS` on its
  own (EC-015)" and `:1279` says it is taken as a second argument "because it
  cannot be derived from the score"; `classify` has taken one argument since
  CARD-098. `export/__init__.py:187` says the difficulty value set "has four
  members, `"Guess"` among them" and that the filename "now also spells
  `cat-guess.pdf`". And `cli.py:315`'s shipped `--help` text still reads
  "…`guess` is for puzzles whose solve had to branch", which a user sees. The
  *code* on all three paths is correct; the prose is not.
- `SolveSignals.rung_cells` always carries all three rung names as keys
  (`_NO_RUNG_CELLS`, `solver/search.py:249`) so a consumer can index rather than
  `get`. It is all-zero, with `rungs` empty, for every clue set whose
  `solution_count` is not 1.
- **`src/nonogram/analysis/strategy_counter.py` is a second, parallel difficulty
  scorer and is not part of CAP-004.** It has no importer under `src/` and its
  vocabulary (`LINE_LOGIC`, `CONSTRAINT_PROPAGATION`, `BLOCK_ELIMINATION`,
  `POINTING_PAIRS`, `BACKTRACKING`, `AMBIGUITY`) does not match the shipped
  three-rung ladder at all. `src/nonogram/__init__.py:35` records it as a
  deliberately-kept prototype of the design in
  `docs/REQUIREMENTS/DIFFICULTY_ENGINE.md` "that nothing on the shipping path
  calls (CARD-053 kept it deliberately — the rescoring question it belongs to is
  still open)". See
  [10-persistence-and-the-unmodelled-edges.md](10-persistence-and-the-unmodelled-edges.md).

## Related

- [04-uniqueness-and-recovery.md](04-uniqueness-and-recovery.md) — where the rung tags come from
- [01-the-layered-pipeline.md](01-the-layered-pipeline.md) — POL-004's loop
- ADRs: [ADR-0005](../../../../meta/architecture/decisions/adr/0005-difficulty-tier-cutoffs.md) · [ADR-0013](../../../../meta/architecture/decisions/adr/0013-difficulty-scoring-formula.md) (superseded) · [ADR-0025](../../../../meta/architecture/decisions/adr/0025-requires-guessing-as-fourth-tier.md) (superseded) · [ADR-0029](../../../../meta/architecture/decisions/adr/0029-difficulty-by-strategy-ladder.md) · [ADR-0031](../../../../meta/architecture/decisions/adr/0031-retire-the-guess-tier.md)
