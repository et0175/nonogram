# CARD-078: Refuse density 0 and 100 — valid range 1..99

**Status:** ready
**Priority:** P3
**Category:** bugfix
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/078-refuse-degenerate-density
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-11
**Idea:** —
**Wave:** 1
**Depends on:** —
**Touches:** src/nonogram/sourcing/random_grid.py (MIN_DENSITY/MAX_DENSITY, validate_density message, the :78-84 docstring), src/nonogram/cli.py (--density help text only), src/nonogram/web/pages.py (numeric bounds on the density field, if any), src/nonogram/admin/batch_generator.py and src/nonogram/admin/templates/batch_create.html (density presets audited for 0/100), tests/test_sourcing_random.py, tests/test_cli.py, tests/test_web_server.py, meta/architecture/requirements.yml (FR-004 amendment note), meta/architecture/decisions/adr/0003-*.md (History note)
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why

Density 0 and 100 are accepted today and yield an all-empty / all-filled
grid that passes the uniqueness check vacuously (score 0.000 / 0.001, tier
Easy) — `docs/GENERATION_ALGORITHM.md` §10.2 finding 2. The comment at
`random_grid.py:78-84` promises that later stages reject them; none does.
ADR-0027 (DEC-034) refuses both as `InvalidDensity` at the one seam where
every other out-of-range density is refused (ADR-0010: domain validation
inward of the adapters), making the valid range 1..99 inclusive. Small and
independent — can ride with any wave-2 card.

**Sequencing.** Independent; no card depends on it and it depends on none.

## What to implement

1. `MIN_DENSITY = 1`, `MAX_DENSITY = 99` in `sourcing/random_grid.py` — the
   only statement of the range (ADR-0027/R1); `validate_density` refuses 0
   and 100 before any grid is drawn with a message naming the range (the
   existing f-string already reads the constants — verify).
2. Replace the misleading docstring at `random_grid.py:78-84` with the
   rule itself: no later stage judges density, and none claims to
   (ADR-0027/R2).
3. Audit the adapters for 0/100: CLI `--density` help text (no argparse
   `choices=`/`type=` bound — ADR-0010); the web form's numeric bounds
   (`min`/`max` attributes are presentational only — the domain seam still
   decides, ADR-0019/R1); admin batch density presets in
   `batch_generator.py` / `batch_create.html`. Fix any preset that emits 0
   or 100.
4. Registry: FR-004's amendment note records the resolution; AC-011's text
   stays as `requirements.yml` decided (150 is outside both ranges — not
   rewritten, test name kept). ADR-0003 History note: the ±3-point band now
   applies over 1..99.

## Acceptance criteria

- **AC-128** — given two random-mode requests at 20x20, density 0 and
  density 100, when each is generated, then each is refused with
  `InvalidDensity` before any grid is drawn.
  *test:* `TestGenerateRandom_RefusesDensityZeroAndHundred`
- **AC-133** — given density 1 and density 99 at 20x20, when each is
  generated, then each is accepted by `validate_density` and a grid is
  drawn.
  *test:* `TestGenerateRandom_AcceptsDensityOneAndNinetyNine`
- **AC-130** — given a random-mode request at 20x20 with density 0, when
  generated, then the verdict is made by `validate_density`, and neither
  the uniqueness check nor the difficulty scorer raises on density grounds
  afterwards.
  *test:* `TestGenerateRandom_DegenerateDensityVerdictIsMadeAtValidateDensitySeam`
- **AC-011** (unchanged) — density 150 still rejected.
  *test:* `TestGenerateRandom_RejectsInvalidDensity`
- **AC-A** (handoff checkpoint) — `nonogram generate --mode random --size
  10 --density 0` exits with the same code family as `--density 150` and
  writes nothing; `--density 1` and `--density 99` generate.
  *test:* `tests/test_cli.py` exit-code case for density 0/100
- **AC-B** — the web form refuses density 0 and 100 through the same
  domain error, writing nothing (EC-003 failure shaping unchanged).
  *test:* web form bound test in `tests/test_web_server.py`

## Guardrails

- G-1: The refusal lives only in `validate_density` — no argparse
  `choices=`/`type=` constraint, no web-adapter validation, no admin-side
  check (ADR-0010, ADR-0019/R1, ADR-0027/R2); no new error class or exit
  code.
- G-2: `DENSITY_TOLERANCE_POINTS` name and value unchanged (ADR-0003;
  CARD-070 G-4); the sampler is not touched.
- G-3: AC-129 / AC-134 (the retired allow-alternative) are not
  implemented and their test names not created.
- G-4: No edits under `src/nonogram/solver/`, `difficulty.py`,
  `orchestrator.py`, `export/**`.
- G-5: Commit only your own files — explicit pathspecs.

## System contract

- ADR-0027/R1 — valid requested density is 1..99 inclusive; 0 and 100
  refused by validate_density before any grid is drawn; MIN_DENSITY /
  MAX_DENSITY the only statement of the range (check:
  TestGenerateRandom_RefusesDensityZeroAndHundred)
- ADR-0027/R2 — the density verdict is made only at the validate_density
  seam; no later stage rejects on density grounds and no module claims one
  does (check: TestGenerateRandom_DegenerateDensityVerdictIsMadeAtValidateDensitySeam)
- ADR-0010 — range validation is a pure domain function inward of the
  adapters, never an argparse constraint (check: tests/test_cli.py)
- ADR-0019/R1 — the web adapter carries no domain validation (check:
  tests/test_web_server.py)
- ADR-0003 — generated density within ±3 points of the request, now over
  1..99 (check: tests/test_sourcing_random.py)
- ADR-0007 — no lateral imports (check: test_every_import_in_the_package_points_inward)

## Architecture context

- **FR:** FR-028 (AC-128, AC-130, AC-133), FR-004 (amended)
- **ADR:** ADR-0027 (R1, R2), ADR-0003 (History), ADR-0010
- **Components:** COMP-003 (the seam); COMP-001 / COMP-008 / admin
  (help text and presets only)
- **Trace:** meta/architecture/trace.yml (FR-028 row)

**Checkpoint (handoff, verbatim):** `nonogram generate --mode random --size
10 --density 0` exits with the same code family as `--density 150` and
writes nothing; `--density 1` and `--density 99` generate.
**Collapses:** FR-028, the degenerate-puzzle product defect (finding 2 of
the 2026-09-12 review).
**Rollback:** Constants and one docstring; revert the branch.

## Worktree notes

—
