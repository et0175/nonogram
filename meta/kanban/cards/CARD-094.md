# CARD-094: Nothing still says 20 attempts or 200 puzzles where it means the live bound

**Status:** in progress
**Priority:** P3
**Category:** docs (plus one bound left behind in code — see "What the sweep found")
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** for the image-count bound only
**Branch:** card/094-stale-bounds-in-prose
**Worktree:** ../PythonProject4-CARD-094
**Source:** owner — "open a card for finding 10" (`docs/GENERATION_ALGORITHM.md` §10.2 finding 10, CARD-092)
**Idea:** —
**Wave:** 1
**Depends on:** CARD-088 (batch ceiling 200 → 50), CARD-090 (retry bound 20 → 30), CARD-091 (K 3 → 5) — the three changes the prose did not follow
**Touches:** src/nonogram/orchestrator.py, src/nonogram/sourcing/library.py, src/nonogram/admin/batch_generator.py, src/nonogram/admin/app.py, src/nonogram/admin/templates/batch_create.html, a test for the image-count bound, docs/GENERATION_ALGORITHM.md (finding 10)
**Review score:** —
**Started:** 2026-09-15
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why

CARD-090 and CARD-091 each updated the constant, its own docstring, the ADR and
the tests that pinned the value — and each missed prose elsewhere that restated
the old number as though it were current. CARD-088 did the same for the batch
ceiling. None of it changes behaviour, but this module's comments are unusually
load-bearing: they are where the *reasons* for each bound live, and a reason
stated against the wrong number reads as a wrong reason.

## What the sweep found

Every mention of 20/200/twenty in a retry, batch or bound context across
`src/nonogram`, on `main` at `5935948`, sorted into three kinds.

### Stale — states a live value that is no longer true (fix)

| where (symbol) | says | is |
|---|---|---|
| `orchestrator` module docstring, POL-001 section | a timeout conflated with a non-unique verdict would "spend 20 full solver deadlines" | the bound is 30 |
| `orchestrator` module docstring, image section | image mode through the regenerate loop would spend "a twentieth of the time budget" and report "abandoned after 20 attempts" | 30 / a thirtieth |
| `GENERATION_BUDGET_SECONDS` comment | "20 retries times a per-solve 30s would be a ten-minute timeout" | 30 × 30 s is fifteen minutes |
| `orchestrator._lineage_key` | "at most 20 of them" | at most `MAX_RETRY_ATTEMPTS` |
| `orchestrator._uniqueness_reason` | make sense of "20 attempts" | the message itself prints the constant |
| `orchestrator._image_uniqueness_reason` | "a message about 20 discarded candidate grids" | 30 |
| `orchestrator.generate` docstring | "a fresh 20 candidates"; "the ADR-0002 bound of 20 covers them together … how the 20 divided" | 30 |
| `orchestrator.generate` `Raises` | "a wiring bug cannot be mistaken for 20 infeasible candidates" | 30 |
| comment above `_resolved_extent(request)` in `generate` | re-deriving per attempt "would decode the file twenty times" | image mode converts once and nudges at most 5 times; the regenerate bound is 30. The sentence is wrong on both counts |
| `orchestrator.BatchResult.abandoned` | "20 draws each" | up to 30 attempts, redraws and repairs |
| `orchestrator.generate_batch`, tier-gate comment | "a batch of 200 fails at the call" | 200 is refused by the count check first; the ceiling is 50 |
| `orchestrator.generate_batch`, clock comment | "abandoned because 20 draws failed" | 30 attempts |
| `orchestrator.generate_batch`, `SolverTimeout` comment | "200 candidates x 30s is an hour and a half"; "Measured: 30x30 at density 50 reaches the deadline rather than the retry bound" | 50 × 30 s is 25 minutes; and CARD-091 measured **0 timeouts in 100** 30x30 requests at K=5 — the measurement is no longer true |
| `sourcing.library` module docstring | re-rendering at 20x20 would hand the loop "the same grid twenty times, twenty identical solver verdicts" | thirty |
| `admin.batch_generator.BatchGenerator.create_batch` docstring | "1-200 for images, 10-200 for random" | the code below it reads `MAX_BATCH_COUNT` (50) |

### A bound left behind in code — changes behaviour

| where | what | effect |
|---|---|---|
| `admin.app` — the `/batch/preview-images` route | `if len(images) < 1 or len(images) > 200`, with the flash "Must be 1-200 images." | a selection of 51–200 pictures **passes preview**, then `create_batch(source="images")` refuses it ("Image batch count must be 1-50") at the generate step |
| `admin/templates/batch_create.html` | "Up to 200 pictures per batch." | tells the owner a number the panel will not accept |

This is exactly the defect `create_batch`'s own comment describes — "200 written
out here *and* 200 written out there, and CARD-088 lowered one of them" — in a
third place CARD-088 did not find.

### Legitimate — history, sample sizes or unrelated examples (keep)

- `MAX_RETRY_ATTEMPTS`'s measurement ("bound 20 abandoned 14, bound 30 abandons 4 …")
- `MAX_CONSECUTIVE_ABANDONMENTS`'s worked example, which already says it was
  restated from `count=200` against a bound of 20
- "over 200 draws per size" (a sample size) and "a 200-puzzle 30x30 batch needs
  about 13 minutes" (why the ceiling came down)
- `generate_batch`'s count error, "The ceiling came down from 200 with CARD-088"
- `create_batch`'s "200 written out here *and* 200 written out there" (the lesson)
- `solver.search`'s "that request's twenty candidates" (a recorded measurement of
  one request) and the "twenty unknown cells" line-freedom examples in the solver
- sizes, pixel counts and percentages that merely contain 20

## Acceptance criteria

- **AC-1** (every stale statement is corrected) — each row of the first table
  either names the constant (`MAX_RETRY_ATTEMPTS`, `MAX_BATCH_COUNT`) where the
  sentence is about the bound, or states the current number where a figure makes
  the argument (fifteen minutes, twenty-five minutes). Prefer the symbol: a
  sentence that names the constant does not go stale on the next retune.
- **AC-2** (the removed measurement is not replaced by a new unmeasured one) —
  the `SolverTimeout` comment keeps its *reason* (a batch that swallowed timeouts
  would have no time bound but its own clock) and drops the claim that 30x30
  reaches the deadline, citing CARD-091's result instead.
- **AC-3** (the image-count bound has one source) — the preview route and the
  form text read `MAX_BATCH_COUNT` rather than stating 200, so preview and
  generate accept and refuse the same selections. Test first: a selection of
  `MAX_BATCH_COUNT + 1` pictures is refused **at preview** with a message naming
  the real ceiling, and `MAX_BATCH_COUNT` is accepted.
- **AC-4** (history stays history) — nothing in the third list is edited.
- **AC-5** (a sweep that can be re-run) — the grep this card was scoped from is
  recorded in the card, with its result after the fix: no remaining match is in
  the "stale" or "left behind" categories.
- **AC-6** (the doc follows) — finding 10 in `docs/GENERATION_ALGORITHM.md` is
  closed with this card, and `meta/ops/check_doc_references.py` still passes.

## Guardrails

- **G-1** — no behaviour change except AC-3. Only comments, docstrings, one
  flash message, one template sentence and the one comparison change; no
  constant moves. The full suite must pass unchanged apart from the new test.
- **G-2** — no rewriting of reasoning beyond the number. Where a sentence's
  argument still holds at 30, only the figure changes.
- **G-3** — test docstrings are out of scope. Several test files narrate their
  own history with old numbers ("The count was 200 until CARD-088"), which is
  correct history; any that state a stale live value can be a follow-up.
- **G-4** — `nonogram_admin.db`, `src/nonogram.egg-info/*` and the stray PDFs
  stay uncommitted; commit with explicit pathspecs only.

## Out-of-scope observations

- **An image batch has no batch clock.** The random path stops starting
  candidates at `BATCH_BUDGET_SECONDS`; the image route loops over every picture
  inside one request, each up to `GENERATION_BUDGET_SECONDS` plus up to two
  neighbour-extent retries. Fifty pictures can far outlast the server's 120 s
  timeout. That is CARD-088 Q-2 (move batch generation off the request) rather
  than a stale number, so it is noted, not fixed.
- **`nonogram.generation.random_generator`** validates its own count as 50–200
  and is imported by nothing in `src/` outside its package — only by CARD-050's
  tests. It looks like a dead module; worth confirming before anyone updates its
  numbers.

## Open questions for the owner

- **Q-1** — fold the image-count bound (AC-3) into this card, or split it out?
  Proposed: **fold it in.** It is the same drift with the same cause, a
  one-comparison fix with its own test, and a "prose" card that found a live
  instance of the bug and left it would be the drift this card exists to end.
