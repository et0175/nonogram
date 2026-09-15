# CARD-092: The generation algorithm reference describes the loop the code actually runs

**Status:** in progress
**Priority:** P3
**Category:** docs
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** —
**TDD:** —
**Branch:** card/092-generation-algorithm-doc-current
**Worktree:** ../PythonProject4-CARD-092
**Source:** owner — "open a card for the generation algorithm doc" (CARD-091 out-of-scope observation)
**Idea:** —
**Wave:** 1
**Depends on:** CARD-091 (merged b27435c) — the last change to the loop this documents
**Touches:** docs/GENERATION_ALGORITHM.md, meta/ops/check_doc_references.py (new — AC-4's repeatable check)
**Review score:** —
**Started:** 2026-09-15
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why

`docs/GENERATION_ALGORITHM.md` exists to be the one place that says what the
generator does *as implemented* — it was written because the only earlier
document described an Otsu pipeline that never shipped. It has since been kept
current for the solver (`064611c`), the strategy-ladder grade (`3635ea4`,
`5914b6d`) and the retry bound (`8ccbda9`). It was not kept current for the
rest, and a reference that is wrong in places cannot be trusted in any of them.

Measured against `main` at `41096cf`:

| Section | Says | Code does since |
|---|---|---|
| §8 Retry policies | a non-unique candidate is discarded and redrawn; the word "repair" does not occur in the document | **POL-006 repair, then redraw** (ADR-0024, CARD-074): flip one filled/empty pair inside the witness-disagreement set, re-verify, up to **K=5** times per lineage (CARD-091), all inside the one bound of 30. `RecoveryLog` records redraws, repairs, capped lineages and repeated grids |
| §9 Random batches | count 1..200; a batch ends at its first abandonment (implicitly) | **`MAX_BATCH_COUNT` 50**, default 15, a **75 s batch clock** (CARD-088); an abandoned candidate is **skipped**, and **3 in a row** end the batch (CARD-083); `BatchResult` reports `abandoned` and `not_attempted` |
| §10.2 Findings | "Findings 1, 2 and 4 are cut as CARD-070 and CARD-078 and remain open" | **CARD-070 is done** and closed findings 1, 4, 5 and 7. Finding 2 is still open (CARD-078, ready). Finding 6's status is unstated |
| `file:line` references | 117 of them, `orchestrator.py` anchors taken from a ~1,300-line file | `orchestrator.py` is **2,291 lines**. Spot check: `judge_candidate` cited at `:1167-1198` is at `:1612`; `generate_batch` cited at `:1287-1347` is at `:1873`. The orchestrator anchors are effectively all wrong |
| Header | "reverse-engineered from the code on `main` as of 2026-09-12" | four merged cards later |

The section that matters most is §8: it is where a reader goes to learn why a
request succeeds or is abandoned, and it currently describes a draws-only loop
that succeeds 38% of the time at 30x30 where the real one succeeds 99%.

## Acceptance criteria

- **AC-1** (§8 describes repair-then-redraw) — the loop as ADR-0024 R1–R5 pins
  it: the region (witness disagreement, undecided-mask fallback), the
  deterministic pair choice with no rng draw, the filled count preserved,
  re-verification through the one `judge_candidate` path, the K escape back to
  POL-001, the one shared bound, the rollback switch (K=0), library mode
  redrawing only, and what `RecoveryLog` records — including that a repeated
  grid is counted and not acted on. §2's pipeline overview and §11's "Retry"
  row say the same thing.
- **AC-2** (§9 describes the batch as it runs) — `MAX_BATCH_COUNT`,
  `DEFAULT_BATCH_COUNT`, `BATCH_BUDGET_SECONDS`, `MAX_CONSECUTIVE_ABANDONMENTS`,
  skip-on-abandonment, `BatchResult`'s counters, and that a `SolverTimeout`
  still ends a batch (CARD-083's open owner question, stated as open). The rest
  of §9 — size presets, fit policy, the neighbour-extent retry — is
  **re-verified against the code**, not assumed still true because nobody
  changed it on purpose: the admin panel has had heavy commits since.
- **AC-3** (§10 carries each finding's current status, with evidence) — each of
  findings 1–8 is marked open or closed, and a closed one names the card and
  commit that closed it. A status is established by re-running or re-reading
  the check, not copied from CARD-070's own account. §10.1's "verified sound"
  claims are re-checked where the code they describe changed (retry accounting
  now includes repairs).
- **AC-4** (every reference resolves) — every `file:line` or symbol reference
  in the document points at what it names on the commit the header states.
  Checked by a script that extracts each reference and prints the target, so
  the check is repeatable on the next refresh; the result is recorded in this
  card.
- **AC-5** (measured claims cite their measurement) — the effect of the retry
  bound and of K is summarised briefly with the cards that measured it
  (CARD-089, CARD-090, CARD-091) and the harness that reproduces it
  (`meta/ops/retry_bound_sweep.py`), rather than stated as unsourced fact or
  copied in full.
- **AC-6** (the header is honest about its date) — it names the commit it was
  verified against, and keeps a short changelog of what each refresh covered,
  so the next reader can tell what has *not* been re-checked.

## Guardrails

- **G-1** — documentation only. No file under `src/` or `tests/` changes. If
  verifying the document turns up a real defect, it is recorded as a new
  finding in §10.2 and reported, not fixed here.
- **G-2** — the document describes the code; it does not argue with the ADRs.
  Where code and an ADR disagree, §10.2 records the disagreement.
- **G-3** — `docs/REQUIREMENTS/NONOGRAM_GENERATION_REQUIREMENTS.md` keeps its
  supersession banner and nothing else changes there.
- **G-4** — `nonogram_admin.db`, `src/nonogram.egg-info/*` and the stray PDFs
  stay uncommitted; commit with explicit pathspecs only.

## Open questions for the owner

- **Q-1** — how should the document point into the code? The line numbers went
  stale within three days: `orchestrator.py` grew by roughly 1,000 lines and
  took every anchor with it. Options: **(a) symbol references**
  (`orchestrator.judge_candidate`, `propagate.line_intersection`) — survive edits,
  one grep away from the line; **(b) line numbers**, refreshed each time — the
  most precise, and wrong again after the next orchestrator card; **(c) both**,
  symbol first with the line as of the stated commit. Proposed: **(a)**, with
  line ranges kept only where a symbol is too large to be a useful pointer (the
  solver's search loop). AC-4's script checks whichever form is chosen.

**Answered 2026-09-15:** Q-1 — "take option a": symbol references, with line
ranges kept only where a symbol is too large to be a useful pointer.

## Outcome

`docs/GENERATION_ALGORITHM.md` rewritten against `41096cf` (565 → 724 lines).

- **AC-1.** §8 is now *Recovery policies*: a counter table (regenerate / resample
  / nudge, plus K as a split rather than a bound), §8.1 redraw, **§8.2 repair
  then redraw** (region and fallback, flip, pair choice, re-verify, the K escape,
  the one budget, the K=0 rollback switch, cycling counted not acted on, what
  `RecoveryLog` records), §8.3 resample, §8.4 nudge, §8.5 never retried. §1, §2's
  pipeline diagram and §11's Retry row say the same thing.
- **AC-2.** §9 split into §9.1 `generate_batch` (count 1..50, the 75 s clock read
  before each candidate, skip-on-abandonment, 3-in-a-row raises, `SolverTimeout`
  ends the batch as CARD-083's open question, `BatchResult`'s counters, the two
  empty-result messages) and §9.2 image batches, re-verified against
  `admin/image_manager.py` and `admin/app.py`. What had drifted there was detail,
  not substance: square extents only move toward the picture's shape, neighbour
  ties go to the smaller extent, the fit share is an integer cross-product, `min`
  is a size mode but not a preset, and the random batch falls back to sizes
  `[15, 20, 25]`.
- **AC-3.** Every finding re-established on this tree rather than copied:

  | # | status | evidence |
  |---|---|---|
  | 1 | closed (CARD-070) | `generate_batch(count=1, sizes=[10], difficulty_tier="Easy")` returns a puzzle |
  | 2 | open (CARD-078) | density 0 and 100 → `ready_for_export=True`, score 33.0, `easy` |
  | 3 | closed (CARD-076) | `difficulty.SolverSignals` has no `elapsed_seconds` |
  | 4 | closed (CARD-070) | the `DENSITY_TOLERANCE_POINTS` comment now says the loop never reads it |
  | 5 | closed (CARD-070) | `tests/test_nudge.py` passes |
  | 6 | closed (`f3ba719`) | 117 passed in a clean worktree |
  | 7 | not reproduced | `tests/test_timeout.py` 17/17 three times |
  | 8 | open, unchanged | — |

  §10's suites re-run on `41096cf`: **692 passed, 1 failed**. The failure is the
  admin tier-badge markup test already known to fail on untouched main.
  §10.1's recovery-accounting claim now covers repairs, and a "repair preserves
  density" entry was added.
- **Two new findings, recorded not fixed (G-1):**
  - **9 — a batch that hits 3 consecutive abandonments discards the puzzles it
    already made.** `generate_batch` raises, and `_generate_random_batch` stores
    only after a return, so the loss is total. Rare today (1 abandonment in 100
    at 30x30), but worth a card.
  - **10 — about fifteen comments and docstrings in `orchestrator.py` still say
    20 attempts or 200 puzzles**, and one `generate_batch` comment says 30x30
    "reaches the deadline rather than the retry bound", which CARD-091 measured
    no longer true. Prose only; behaviour is correct.
- **AC-4.** Every code reference is a symbol (Q-1 option a); no line anchors
  remain anywhere, code blocks included. `meta/ops/check_doc_references.py`
  resolves them with `ast` — package re-exports followed, nested functions
  through their parent, bare constants checked, `path::test` checked, and lines
  marked `<!-- historical -->` inverted so the retired ADR-0013 names are proven
  gone. Result: **201 resolved, 0 failed.** Checked that it discriminates: a
  misspelled symbol, a misspelled constant, a "retired" name that still exists
  and a line anchor inside a code block each fail.
- **AC-5.** §8.2 carries one small table (38% / 85% / 95% / 99%) naming CARD-089,
  CARD-090, CARD-091 and the sweep harness, and says timings are only comparable
  within one run.
- **AC-6.** The header names `41096cf`, and a *Refresh log* at the end records
  what each of the four refreshes re-checked **and what it did not**: §7's tier
  distribution and §8.3's tier-by-density table predate repair and were not
  re-measured, which both sections now say in place.
- **A mistake caught in my own draft.** The first version of finding 6 called
  `pictures/` the owner's untracked folder and said a fresh clone would still
  fail. It is tracked (25 files, `f3ba719`); corrected before commit.
- G-1..G-4 held: nothing under `src/` or `tests/` changed, no ADR argued with,
  `NONOGRAM_GENERATION_REQUIREMENTS.md` untouched.

