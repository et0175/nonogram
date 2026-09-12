# CARD-070: Generation quick fixes — batch tier spelling, stale nudge pins, docstring drift

**Status:** ready
**Priority:** P2
**Category:** tech-debt
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/070-generation-quick-fixes
**Worktree:** —
**Source:** docs/GENERATION_ALGORITHM.md §10.2, findings 1, 4, 5 and 7 of the 2026-09-12 generation code review; follow-up card, not decomposed from handoff.md
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/orchestrator.py (generate_batch tier validation only), src/nonogram/sourcing/random_grid.py (one comment), tests/test_batch_generator.py or a new tests/test_card_070_batch_tier.py, tests/test_nudge.py, tests/fixtures/bands.png (replace only if (a) below is chosen)
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why

The 2026-09-12 review of the generation pipeline
(`docs/GENERATION_ALGORITHM.md` §10 "Correctness review") found the core
sound (§10.1) and listed eight defects and gaps in §10.2. Four of them are
small and self-contained enough to land together without a decision:

- **§10.2 #1** — `generate_batch` validates `difficulty_tier` against the
  enum *names*, so the spelling its own docstring advertises raises.
- **§10.2 #4** — a comment in `random_grid.py` describes a reader that
  does not exist.
- **§10.2 #5** — three nudge tests pin a fixture as needing exactly two
  nudges, and on `main` it needs none; the tests are green for the wrong
  reason or not exercising what they claim.
- **§10.2 #7** — a possibly timing-flaky suite, to be recorded, not chased.

The other §10.2 items (density 0/100 acceptance, machine-dependent
`time_pressure`, the 16x16 library boundary) each need a decision and are
deliberately *not* on this card.

## What to implement

1. **`generate_batch` accepts the documented tier spelling**
   (`src/nonogram/orchestrator.py:1322`). Today:
   `if difficulty_tier and difficulty_tier not in {t.name for t in difficulty.Tier}`
   — so `"Easy"` and `"easy"` raise `ValueError` although the docstring
   says `"Easy"` and `difficulty.parse_tier` is case-insensitive. Every
   caller passes `None` today, which is why it was never noticed. Validate
   through `difficulty.parse_tier` and pass the *parsed tier's value* into
   the `GenerationRequest`. On an unknown tier raise either the same
   `ValueError` wording as today or `UnsupportedDifficulty` — pick one,
   and write the choice and the reason into the docstring's `Raises:`
   block. The message must list the three tiers. Add tests for `"Easy"`,
   `"easy"`, `"EASY"` and `"extreme"`.
2. **Rewrite the `DENSITY_TOLERANCE_POINTS` comment**
   (`src/nonogram/sourcing/random_grid.py:86-90`). It says "CARD-005's
   regenerate loop is expected to read it rather than restate the
   constant". The loop never reads it and never needs to: the ±3-point
   bound holds by construction (the sampler places an exact filled count
   and shuffles; the only error is rounding — §10.1 "Density"). Say that,
   and that the constant is exported as the sampler's *contract* for
   tests to assert against. No behaviour change.
3. **Re-pin the stale nudge tests honestly** (`tests/test_nudge.py`).
   `test_nudge_attempts_bounded_recovery_on_a_real_image` (line 322)
   pins `tests/fixtures/bands.png` at 10x10 as needing exactly 2 nudges;
   on `main` the fixture converts uniquely on the first solve (0 nudges).
   The ink bounding box is the whole 32x32 file, so the FR-022 trim is
   *not* the cause — the untrimmed conversion is unique too. First
   determine what moved: the fixture bytes (commit `96da6ac` restored
   images from a backup — `git log --follow -- tests/fixtures/bands.png`
   and compare hashes) or the resize/dither path in `sourcing/image.py`.
   Then either
   - **(a) preferred** — replace the fixture with one that genuinely
     needs 2 nudges at 10x10, so the test keeps pinning a real recovery
     (sweep candidate images the way the module docstring describes the
     original pin was taken), or
   - **(b)** re-pin to the observed count with the cause recorded in
     the test docstring.

   Note before starting: §10.2 #5 says "three" tests "on the same
   fixture", but on `main` the two cap tests on a real image
   (`test_nudge_reports_failure_at_cap_on_a_real_image`, line 432, and
   `..._through_the_cli`, line 447) read `landscape.png` at 22x22, not
   `bands.png`. Run the suite first and re-pin exactly the tests that
   actually fail or pin a wrong count; record which in the Worktree
   notes. The mechanism tests with scripted sources
   (`test_nudge_attempts_bounded_recovery_*` with monkeypatched sources,
   `test_nudge_reports_failure_at_cap*` without a real image, the
   `nudge_cells` unit tests) stay untouched.
4. **Note only, no code** — `tests/test_timeout.py` passed 17/17 in
   isolation twice, but one batched run showed two exit-code assertions
   failing (§10.2 #7). Record it in the Worktree notes as a possibly
   timing-flaky suite, with the run in which it was seen if reproducible.
   Do not chase it here.

## Acceptance criteria

- **AC-1** — `generate_batch(count=1, sizes=[10], difficulty_tier="Easy")`
  returns one puzzle whose `difficulty_tier` is `Tier.EASY`; `"easy"` and
  `"EASY"` likewise; `"extreme"` raises with a message that names the
  three tiers.
- **AC-2** — `tests/test_nudge.py` passes in full on `main`, and every
  real-image test's docstring states the count it pins and where it came
  from.
- **AC-3** — the full suite minus the `pictures/`-corpus tests
  (`tests/test_sourcing_image.py`'s 13 `FileNotFoundError` cases, §10.2
  #6) passes.
- **AC-4** — no change to `MAX_NUDGE_ATTEMPTS`, the nudge ranking in
  `nudge_cells`, or any file under `src/nonogram/solver/`.

## Guardrails

- G-1: Do not touch the nudge heuristic — a separate decision and card
  will replace it. Only test pins and, at most, one fixture change.
- G-2: Do not alter any fixture other than `tests/fixtures/bands.png`;
  `landscape.png` and the scripted grids stay byte-identical.
- G-3: No edits under `src/nonogram/solver/`, `difficulty.py`, `cli.py`,
  the web adapter or `admin/`.
- G-4: `random_grid.py` changes are comment-only; `DENSITY_TOLERANCE_POINTS`
  keeps its name and value.
- G-5: Commit only your own files — the working tree carries a large
  standing set of unrelated staged/untracked changes; use explicit
  pathspecs.

## Worktree notes

—
