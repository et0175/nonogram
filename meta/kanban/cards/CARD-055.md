# CARD-055: Confine MockGenerator's random metrics to test-only reach

**Status:** done
**Priority:** P3
**Category:** tech-debt
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** relocation — output pinned byte-identical at 4 seeds; 2 mutants on the repointed patch targets, both caught
**Branch:** card/055-mockgenerator-test-only
**Worktree:** ../PythonProject4-CARD-055
**Source:** meta/review/20260910T170025Z.yml#F-007
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/admin/puzzle_review.py (the class moves out), tests/helpers/mock_generator.py (new), tests/conftest.py, tests/test_batch_generation_e2e.py, tests/test_wave3_e2e.py, tests/test_admin_uniqueness_boundary.py, tests/test_strategies.py
**Review score:** — _(merged without a review cycle, at the owner's call)_
**Started:** 2026-09-22
**Closed:** 2026-09-22
**Actual:** 0.25d
**Merge commit:** df192c1
**Blocked by:** —

## Re-cut 2026-09-22 — the reachability claim is stale, the two-field claim is not

Checked against `main` at `b164c19`.

**What the card gets right, still.** `quality_score` and `recognizability` are
**still invented**, at `puzzle_review.py:1600-1601`:

```python
'quality_score': self.rng.randint(1, 100),
'recognizability': self.rng.choice(['low', 'medium', 'high']),
```

**What it gets wrong.**

- **Line numbers.** The class is at **1496**, not 717-728; the file has grown
  by roughly 800 lines since the card was written.
- **"`MockGenerator(...)` is not instantiated anywhere… it is reachable only
  from `tests/test_wave3_e2e.py`" — no.** Six test files use it, and one of
  them is `tests/conftest.py`, where it backs a **shared fixture**
  (`MockGenerator(seed=2026)`, line 262). Per CARD-080's notes, **29 tests
  store its output**. The Touches line names one of the six.
- **"A third distinct 'fake metrics' implementation" is now an overstatement.**
  CARD-080 rewrote most of this class on 2026-09-14: the grid is resampled
  until the solver certifies exactly one solution, the clues come from
  `clues.compute_clues` on that grid, and the grade comes from that same solve
  through the real scorer and classifier. What is left inventing is precisely
  the two fields this card names — no more, and no less.

**Corroboration the card did not have.** CARD-080 reached the same conclusion
about *where* this class lives, from the other direction: its notes call out
`MockGenerator` as living "in `src/nonogram/admin/puzzle_review.py`, **not in
the test tree**" and as "still shipping in `src/`" after the equivalent defect
was deleted elsewhere. It fixed the invention it found and left the location
alone as out of scope. This card is that leftover.

**A finding to decide on, not silently keep.**
`tests/test_batch_generation_e2e.py:76-77` asserts

```python
assert 1 <= puzzle['quality_score'] <= 100
```

— a test pinning the *range of a random number*. It cannot fail while the
field is `rng.randint(1, 100)`, and it would be the first thing to fail if the
field ever became honest. G-1 as written ("do not change `MockGenerator`'s
behavior") preserves it. See the options below.

**Clean to move.** `puzzle_review.py`'s module-level imports of `compute_clues`,
`solve`, `score_difficulty` and `classify` are also used by the storage guard
at lines 329-334, so relocating the class removes no import and changes no
other part of the file. `tests/helpers/` already exists with `db.py` and
`brute_force_oracle.py`, so there is a convention to follow.

## What to implement

`puzzle_review.py`'s `MockGenerator` (around lines 717-728) assigns
`quality_score: self.rng.randint(1, 100)` and
`recognizability: self.rng.choice(['low', 'medium', 'high'])` — random values,
not measurements. Grep-verified: `MockGenerator(...)` is not instantiated
anywhere in `src/nonogram/admin/*.py` today — it is reachable only from
`tests/test_wave3_e2e.py`. Not a live bug, but a third distinct "fake metrics"
implementation in the codebase (alongside CARD-050's targets) that would be easy
to reach for by mistake when wiring up a new admin code path, given its name
reads as a legitimate generator option alongside the real ones
(`orchestrator.generate_batch`).

1. Move `MockGenerator` out of `src/nonogram/admin/puzzle_review.py` (production
   code) into a test-support location (e.g. `tests/helpers/` or inline in the
   test file(s) that use it), OR clearly gate it so it cannot be imported from a
   production route — implementer's judgment on which fits this codebase's
   existing test-helper conventions better.
2. Update `tests/test_wave3_e2e.py`'s import accordingly.

## The two open choices (re-cut 2026-09-22)

**Where it goes.** `tests/helpers/mock_generator.py`, beside `db.py` and
`brute_force_oracle.py` — the convention this repo already has. Six import
sites change; `conftest.py`'s fixture keeps its name and seed. The alternative
(gate it in place behind a `TYPE_CHECKING`/underscore convention) leaves it
importable from `src/` by anything that asks, which is the whole complaint.
**Recommended: move.**

**What to do about the two invented fields** — this is the decision:

- **Option 1 — move only (G-1 as written).** The randomness follows the class
  into the test tree, where a fake is unremarkable. The range assertion in
  `test_batch_generation_e2e.py` stays as it is: vacuous, but no longer
  asserting about `src/`.
- **Option 2 — move, and set both to `None`.** This is what CARD-050 decided
  for random mode: a puzzle with no measured quality reports `None`, not a
  number, and the UI renders that. It would make `MockGenerator` consistent
  with the pipeline it stands in for, and it turns the vacuous range assertion
  into a real one (`is None`) rather than leaving it. Costs a G-1 amendment
  and a check of what the 29 storing tests assert.

**Recommended: Option 1.** The card's title is "confine to test-only reach",
and once the class is in `tests/helpers/` the two fields are a test fixture's
arbitrary values, which is what a fixture is allowed to be. Option 2 is a real
improvement but it is CARD-050's argument extended to a mock, and it belongs in
its own card where the 29 assertions can be looked at properly — not bolted to
a 0.25d relocation.

## Acceptance criteria

- **AC-1** — `grep -rn "MockGenerator" src/` returns nothing: no production
  module defines, imports or names it.
- **AC-2** — the six test files that use it
  (`tests/conftest.py`, `tests/test_batch_generation_e2e.py`,
  `tests/test_wave3_e2e.py`, `tests/test_admin_uniqueness_boundary.py`,
  `tests/test_strategies.py`, and the fixture's consumers) import it from its
  new home, and the suite's pass/fail set is **identical** — 3,670 passed,
  26 skipped, 1 deselected.
  *(The original AC-2 said "the existing tests still pass unchanged in
  behavior" and named one file; six use it, 29 tests store its output.)*
- **AC-3** *(new)* — `MockGenerator`'s behaviour is byte-for-byte the same
  under Option 1: same seed, same draws, same output. The relocation is a move,
  not a rewrite — verified by generating a batch at a fixed seed before and
  after and comparing.

## Guardrails

- G-1: Do not change `MockGenerator`'s behavior (binding under Option 1; Option 2 amends it explicitly — see the re-cut) — this card only relocates it,
  it does not fix or improve its fakeness (that would be scope creep; the class
  is legitimately mock-only by design, it just shouldn't live where production
  code could accidentally reach it).

## Worktree notes

### Delivered 2026-09-22 — option 1 (move only)

`MockGenerator` now lives in `tests/helpers/mock_generator.py`, beside `db.py`
and `brute_force_oracle.py`. `grep -rn "MockGenerator" src/` returns nothing
(AC-1). **Suite: 3,670 passed, 26 skipped, 1 deselected — identical to `main`**
(AC-2).

**AC-3, measured rather than asserted.** A batch of 4 puzzles at each of seeds
2026, 42, 7 and 5 — 16 puzzles — was serialised before the move and after it:
`sha256 7950c67b…a414c` both times, byte for byte. The relocation changed no
draw, no ordering and no value.

### What the move actually required

The class is copied verbatim; only its imports were rebuilt. Two of them are
worth naming because the first attempt missed them:

- **`time`** — used for the solver deadline (`time.monotonic() +
  GENERATION_BUDGET_SECONDS`). Missing it failed at the first `generate_batch`
  call, not at import.
- **`PuzzleReviewService`** — the class calls
  `PuzzleReviewService._strategies_of(result)` rather than reimplementing the
  rule for appending `guess` (ADR-0025/R2). That is deliberate, per the comment
  at the call site, so the import came along. It is a private method reached
  from the test tree, which is the same shape as the rest of this suite's
  cross-checks.

An AST pass over the new module (every `Load` name minus every binding minus
builtins) is what caught both — worth more than reading the imports, since
`time` would otherwise have surfaced only at runtime.

### Two tests had to be repointed, and were then checked for bite

`test_it_keeps_drawing_until_the_solver_certifies_one` and
`test_it_gives_up_loudly_rather_than_returning_an_unchecked_grid` both
`monkeypatch.setattr(module, "solve", …)` against the module the class used to
live in. After the move the generator resolves `solve` from its new home, so
the patch missed and both failed — correctly. The target follows the class:
`import tests.helpers.mock_generator as module`.

**I over-applied that first.** The same `import nonogram.admin.puzzle_review as
module` line appears at eight places in that file; six of them patch the
storage guard and have nothing to do with the generator. Reverted those; the
final diff touches exactly the two that needed it.

A patch target that silently misses fails green just as easily as it fails red,
so both were mutation-checked in their new position:

| Mutant | Caught by |
|---|---|
| the resample loop drawn once (`range(1)`) | `…keeps_drawing…` |
| the uniqueness check disabled (`if False`) | both tests |

### Left undone, deliberately

`quality_score` and `recognizability` are still `rng.randint(1, 100)` and
`rng.choice([...])` — G-1, and the point of option 1: in the test tree an
arbitrary fixture value is a fixture value.

`tests/test_batch_generation_e2e.py:76` still asserts
`1 <= puzzle['quality_score'] <= 100`, which cannot fail while the field is a
draw from exactly that range. It is now a vacuous assertion about a test
helper rather than about `src/`, which is a smaller problem than it was, but it
is still an assertion that would break the moment the field became honest.
Making both fields `None` — CARD-050's decision for random mode, extended here
— is **option 2 on this card, filed rather than taken**: it needs the 29
storing tests looked at, which is not a 0.25d relocation.
