# CARD-008: Built-in image library sourcing

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/008-library-sourcing
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-2
**Idea:** —
**Wave:** 6
**Depends on:** CARD-003, CARD-006, CARD-007
**Touches:** src/nonogram/sourcing/library.py, src/nonogram/sourcing/__init__.py, src/nonogram/sourcing/templates/, src/nonogram/cli.py, src/nonogram/orchestrator.py, tests/test_sourcing_library.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

COMP-003's second grid source, and the lowest-risk card of Increment 2 — it reuses the
increment-1 pipeline wholesale with a different grid origin.

1. `sourcing/library.py` — a fixed, in-package library of named templates: at minimum
   `cat`, `house`, `heart`, `moon`. ADR-0007 **rejected** an entry-point plugin registry:
   the set is fixed in-package, so "extensible" means adding a template file, not
   registering a hook. Store templates as package data under `sourcing/templates/`.
2. Scale the template to the requested grid size. A template is a shape, not a fixed-size
   bitmap: `--size 20` with key `cat` must yield a 20x20 grid.
3. Unknown key → `UnknownLibraryImage` (from `errors.py`), a domain error raised inward of
   the CLI (ADR-0010), listing the available keys in the message.
4. Register `library` in `sourcing/__init__.py`'s mode dispatch table (one row), add
   `library` to `--mode`'s choices and a `--library-key` flag in `cli.py`, and let the
   orchestrator route mode `library` through POL-001's regenerate loop exactly as random
   mode does — the retry regenerates from the same template with a different tie-break, it
   does not switch key.

## Acceptance criteria

- **AC-005** (happy) — given the built-in library key `"cat"`, when a grid is requested from
  the library, then a grid matching the cat template at the target size is produced.
  *test:* `TestGenerateLibrary_ProducesCatGrid`
- **AC-006** (negative) — given an unknown library key `"dragon"` not present in the built-in
  library, when a grid is requested from the library, then the request is rejected with an
  unknown-library-image error and no grid is produced.
  *test:* `TestGenerateLibrary_RejectsUnknownKey`

## Guardrails

- G-1: Do not edit `src/nonogram/difficulty.py` — owned by CARD-009 this wave
- G-2: Do not edit `src/nonogram/export/**` — owned by CARD-012 and CARD-013 this wave
- G-3: Do not edit `src/nonogram/solver/**`, `src/nonogram/clues.py`, `pyproject.toml` —
  Increment 2 is additive on top of Increment 1: revert must be possible without touching
  the solver or the orchestrator's core generation logic (handoff Increment 2 Rollback)
- G-4: The orchestrator's core generation logic is unchanged — this card adds a dispatch row
  and a mode branch, it does not restructure the pipeline or the retry loop
  (test: TestRegenerate_FiresOnUniquenessFailure, TestRetryLoop_BoundedIterations)
- G-5: No plugin registry, entry-point hook or dynamic template discovery — the library set
  is fixed in-package by decision (ADR-0007, trace.yml FR-002 note)
- G-6: No new dependency — templates are package data read with stdlib/Pillow only
  (ADR-0006)

## System contract

- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions (check: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (check: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (check: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF)
- INV-003 — A puzzle's automatic-retry counter (regenerate, resample, pixel-nudge) never exceeds its configured maximum bound (check: TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestNudge_ReportsFailureAtCap, TestRetryLoop_BoundedIterations)

## Architecture context

- **FR:** FR-002
- **NFR:** —
- **ADR:** ADR-0007, ADR-0010
- **Components:** COMP-003 (Grid Sourcing — library path)
- **Trace:** meta/architecture/trace.yml

## Worktree notes

### Implementation summary (CARD-008)

**What landed**

- `src/nonogram/sourcing/templates/` — the template data, one module per shape
  (`cat`, `heart`, `house`, `moon`), each a docstring plus a single `ART` string
  of `#`/`.` ASCII art, all four drawn 16x16 (`library.TEMPLATE_EDGE`).
- `src/nonogram/sourcing/library.py` — parses the art, holds the fixed registry,
  rescales a template to any supported size, and exposes `generate(key, size,
  rng)`.
- `src/nonogram/sourcing/__init__.py` — one row: `LIBRARY: library.generate`,
  plus the `LIBRARY` constant and a `MODES` entry. The dispatch shape is
  unchanged.
- `src/nonogram/orchestrator.py` — a `library_key` field on `GenerationRequest`
  and a module-level `_source_arguments(request)` that returns the mode's
  leading arguments (`(size, density)` for random, `(key, size)` for library).
  The loop, the counter, the gate and `attempt_candidate`'s body are otherwise
  untouched; the one changed line inside it is `source(*source_arguments, rng)`
  in place of `source(request.size, request.density, rng)`. G-4 holds: no new
  loop, no new retry primitive, no branch on mode inside the loop.
- `src/nonogram/cli.py` — `library` added to `--mode`'s `choices`, a new
  `--library-key KEY` flag with **no** argparse `choices` (key membership is a
  domain rule, ADR-0010/AC-006), and one more field in the request literal.
  Three small edits, no parser restructuring — deliberately, since CARD-011 is
  queued against both this file and the orchestrator.
- `tests/test_sourcing_library.py` — 107 tests, including the two named ACs.

**Design: why `.py` files and not `.txt` package data.** The card asks for the
templates as package data under `sourcing/templates/`; a `.txt` per shape does
not survive packaging here. `pyproject.toml` declares no `package-data` and the
tree has no `MANIFEST.in`, so setuptools ships only `.py` files out of a
discovered package — verified by building a wheel with a probe `.txt` in that
directory and finding just the `__init__.py` inside. Fixing it properly means
editing `pyproject.toml`, which **G-3 forbids**. So the art rides in the one
file type the build is guaranteed to install, and a test enforces that those
modules stay inert data (no functions, classes, calls, or non-`__future__`
imports) rather than quietly becoming code. A wheel build confirms all five
template modules ship. If a later card is allowed to touch `pyproject.toml`,
converting these to `.txt` + `importlib.resources` is a ~10-line change.

**Design: rescaling.** A template is a shape, so `--size 20 --library-key cat`
gives a 20x20 cat. `coverage()` maps each target cell back onto the rectangle of
template cells it covers and computes the filled fraction of that rectangle as
an exact integer ratio — no floating point until the final comparison, so
"wholly inside the shape" and "wholly outside it" are recognised exactly at
every size. Nearest-neighbour was the alternative and is worse here: at a
non-integer ratio it drops whole template rows and columns, so a one-cell
whisker or window frame vanishes at `--size 11` while its neighbours double
(`test_scaling_does_not_lose_a_whole_row_of_the_shape` pins the difference: 5 of
16 template rows are never even read by nearest-neighbour at size 11). Pillow
was not needed and was not used; stdlib integer arithmetic only (G-6).

### The deterministic-template-vs-retry question

POL-001 discards a candidate whose clues have 0 or many solutions and asks the
source for another. A library template has nothing obvious to vary — the card
forbids switching key on retry — so a naive implementation hands the loop the
same grid 20 times, gets 20 identical verdicts, and abandons after 20x the
necessary work. That is the real question the card leaves open.

**What was done.** The card's own phrase, "a different tie-break", names the
free choice: not *which* shape, but *where its boundary falls*. A partially
covered target cell is precisely one the rasteriser must rule on — it is neither
inside nor outside the cat. So `render(template, size, threshold)` takes a
threshold on the coverage fraction, and `generate` draws it from
`[MIN_EDGE_THRESHOLD, MAX_EDGE_THRESHOLD] = [0.35, 0.65]` off the injected RNG —
one `rng.uniform` per attempt, after validation, so a rejected request still
consumes no randomness. A low threshold renders the shape a touch fatter, a high
one a touch leaner. Because the band is strictly inside `(0, 1)`, cells with
coverage 0 or 1 cannot move: the cat is the same cat on every attempt, only its
outline shifts, and the clues change enough that attempt 2 is a genuine second
chance rather than a repeat. At size 20 that is 95 movable cells out of 400.

**Why not the alternatives.**
- *Fully deterministic source, loop unchanged.* Correct but wasteful, and the
  abandonment message would read as "20 infeasible candidates" when there was
  only ever one.
- *Teach the loop that some sources are deterministic (bail after attempt 1).*
  This is the tempting fix and it is out of bounds: it restructures the retry
  loop, which G-4 explicitly forbids, and it would put knowledge of a source's
  statistical character inside COMP-002, which ADR-0007 keeps out of there.
- *Perturb the shape itself (dither the interior, jitter the whole raster).*
  Rejected: it varies more than the tie-break and would stop the output being
  "a grid matching the cat template" (AC-005).

**Consequences, stated rather than hidden.**
1. Library mode is reproducible on exactly random mode's terms — same seed, same
   `(key, size)`, same grid — but there is no seed-independent canonical "cat at
   20x20". `library.CANONICAL_THRESHOLD` (0.5, the band's midpoint) exists so a
   caller or test can render the unjittered shape deliberately.
2. At 16, 32 and 48 — the whole-number magnifications of a 16-cell template
   within the 10..50 range — every cell is wholly in or out, the threshold has
   nothing to act on, and a retry genuinely *is* a no-op. That is a property of a
   deterministic source, not a defect in POL-001, and it is pinned by a test
   (`test_at_an_exact_magnification_a_retry_is_honestly_a_no_op`) rather than
   left as a comment. The other 38 supported sizes — including 20 and 40, where
   the ratio only *looks* round (16/20 = 0.8) — do vary between attempts, also
   pinned by a test.
3. **Empirically the loop is never stressed anyway.** Every (key, size, seed)
   combination over all 4 keys, sizes 10..25 and seeds 0..2 — 192 runs — produced
   a uniquely-solvable puzzle on attempt 1. Library shapes are far more
   line-logic-friendly than random grids at comparable density, so the retry
   path is a correctness backstop here, not a hot path. Good news for the card,
   and the reason none of the above is worth more machinery than it got.

### RNG usage and the CARD-003 G-4 follow-up

The parent brief guessed this card would need no RNG. It needs exactly one draw
— the tie-break above — so the follow-up **is** applicable after all, and both
of its Minor gaps were closed as part of this card (they were cheap):

1. `from random import Random`/`SystemRandom` used to be unconditionally exempt
   from the from-import binding, which also un-flagged `Random().shuffle(x)` — a
   real ADR-0015 violation via a different import spelling. The exemption is
   gone. Nothing was lost: a legitimate `rng: Random` annotation is an
   `ast.Name`, not an `ast.Call`, so it was never the exemption that protected
   it. The pre-existing test proving the legitimate case still passes unchanged,
   and a new test proves `Random().shuffle(x)` is now caught.
2. `from random import *` is now reported as the single offence `random.*` — the
   import itself, since the scan cannot tell which of the names it binds gets
   called and must not therefore answer "none". New test.

`library.py` itself uses the `import random` spelling (for the `random.Random`
annotation only) and draws solely through the injected instance, so it passes
the guard on its own merits. The documented `getattr(random, "...")` blind spot
is untouched and still pinned by its test.

### Test results

`./.venv/bin/python -m pytest -q` → **745 passed, 1 xfailed** (baseline before
this card: 636 passed, 1 xfailed; the xfail is the pre-existing expected one).
+109 tests: 107 new in `tests/test_sourcing_library.py` and 2 new G-4 guard
tests in `tests/test_sourcing_random.py` (75 → 77).

Named AC tests:
- **AC-005** `TestGenerateLibrary_ProducesCatGrid` →
  `test_generate_library_produces_cat_grid` — PASS
- **AC-006** `TestGenerateLibrary_RejectsUnknownKey` →
  `test_generate_library_rejects_unknown_key` — PASS

### Files touched outside the predicted Touches, and why

- `tests/test_sourcing_random.py` — unavoidable: two of its tests encoded "the
  library mode is not registered yet" (`MODES == ("random",)` and
  `for_mode("library")` raising). Both were written by CARD-003 in anticipation
  of this card ("as later cards register their sources") and were retargeted at
  `image`, CARD-015's still-unregistered mode. The G-4 guard changes above are
  in the same file. CARD-003 is merged, so no active card contends for it.
- `tests/test_orchestrator.py` — one line, same reason:
  `test_an_unknown_mode_fails_before_any_candidate_is_sourced` used `library` as
  its example of an unregistered mode; now uses `image`.
- `README.md` — one line: the intro said the library source was "planned".
  Deliberately left the stale `## Status` paragraph alone (it claims there is no
  export writer, which CARD-007 already disproved) — that belongs to the export
  cards running in parallel this wave and touching it would invite a conflict.

### Guardrail check

- G-1 `difficulty.py` — not touched (does not exist yet).
- G-2 `export/**` — not touched.
- G-3 `solver/**`, `clues.py`, `pyproject.toml` — not touched. The `.txt`
  packaging decision above exists *because* of this guardrail.
- G-4 orchestrator core unchanged — one new module-level helper and one changed
  line inside `attempt_candidate`; no new loop, counter or gate.
  `TestRegenerate_FiresOnUniquenessFailure` and
  `TestRetryLoop_BoundedIterations` pass unchanged.
- G-5 no plugin registry — `_TEMPLATES` is a literal dict of explicit imports,
  enforced by an AST test that forbids `pkgutil`/`importlib`/`entry_points`/
  `glob`/`getattr` appearing as real code in `library.py`.
- G-6 no new dependency — stdlib integer arithmetic; Pillow not used, and
  `pyproject.toml` untouched.

No blockers.

---

[Follow-up from CARD-003 review, cycle 2] The G-4 structural test guard in
tests/test_sourcing_random.py (`_random_module_calls`) has two known Minor gaps worth
checking your module against before assuming the guard covers it: (1) `from random
import Random`/`SystemRandom` is unconditionally exempted, which also silently
un-flags `Random().shuffle(x)` — a real violation via a different import spelling than
`random.Random()`. (2) `from random import *` is not detected at all. If this card adds
any RNG usage, prefer the `random.Random(...)` / `import random` spellings the guard
does catch, or tighten the guard as part of this card if it's cheap.
