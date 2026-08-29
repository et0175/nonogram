# CARD-015: Uploaded-image conversion via resize and Floyd-Steinberg dithering

**Status:** review
**Priority:** P2
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/015-image-conversion
**Worktree:** ../PythonProject4-card-015
**Source:** meta/architecture/handoff.md#increment-3
**Idea:** —
**Wave:** 9
**Depends on:** CARD-008, CARD-014
**Touches:** src/nonogram/sourcing/image.py, src/nonogram/sourcing/__init__.py, src/nonogram/cli.py, src/nonogram/orchestrator.py, tests/test_sourcing_image.py, tests/fixtures/
**Review score:** —
**Started:** 2026-08-29T06:10:00Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

COMP-003's third and last grid source. The handoff calls this "the last untested technical
risk" — dithering quality is unproven until real images run through it.

1. `sourcing/image.py` — load the user's file with Pillow (ADR-0006), convert to greyscale,
   **resize to exactly the target grid dimensions**, then apply Floyd-Steinberg
   error-diffusion dithering and binarize each cell into the ADR-0012 boundary type.
2. **Aspect ratio (AC-009).** The output grid has exactly the requested dimensions even when
   the source aspect ratio differs. Decide and document the policy in the module docstring
   (stretch vs. letterbox-then-crop) — either is acceptable to the AC, but it must be one
   deliberate choice, tested.
3. **Unreadable input (AC-008).** A missing or corrupt file raises a "cannot read image"
   domain error from `errors.py`; the CLI turns it into a clear message and a non-zero exit.
   Pillow's own exceptions must not leak to the user.
4. Register `image` in `sourcing/__init__.py`'s dispatch table, add `--image <path>` and
   `image` to `--mode`'s choices in `cli.py` (parsing only — the file-readability check is a
   domain concern), and route mode `image` through the orchestrator.
5. Add small fixture images under `tests/fixtures/` — a valid PNG, a non-square PNG, and a
   corrupt file. Keep them tiny; they live in the repo.

**Note on the retry policy:** image mode does **not** use POL-001's regenerate loop — an
uploaded image is fixed and cannot be re-drawn. The recovery path is CARD-016's bounded
pixel nudge. This card must leave the orchestrator's image branch failing cleanly on a
non-unique conversion, not silently regenerating.

## Acceptance criteria

- **AC-007** (happy) — given a valid PNG image and a target size of 25x25, when the image is
  converted, then a 25x25 black/white grid is produced via resize and dithering.
  *test:* `TestConvertImage_ProducesDitheredGrid`
- **AC-008** (negative) — given a path to a non-existent or corrupt image file, when
  conversion is requested, then the request fails with a "cannot read image" error and no
  grid is produced.
  *test:* `TestConvertImage_RejectsUnreadableFile`
- **AC-009** (boundary) — given a source image whose aspect ratio differs from the target
  grid, when the image is converted, then the output grid has exactly the requested target
  dimensions.
  *test:* `TestConvertImage_ProducesExactTargetDimensions`

## Guardrails

- G-1: Do not edit `src/nonogram/sourcing/random_grid.py`,
  `src/nonogram/sourcing/library.py`, `src/nonogram/solver/**`,
  `src/nonogram/export/**`, `src/nonogram/clues.py`, `src/nonogram/difficulty.py` — image
  sourcing is the last additive module and must revert without touching random/library
  modes, the solver, or export (handoff Increment 3 Rollback)
  (test: TestGenerateRandom_ProducesRequestedSize, TestGenerateLibrary_ProducesCatGrid,
  TestExport_WritesPNG)
- G-2: No new dependency — resize and dithering via Pillow, arithmetic via NumPy
  (ADR-0006). Do not reach for OpenCV, scikit-image or similar
- G-3: Out of scope — no pixel-nudge recovery loop (FR-013, CARD-016) and no nudge-count
  reporting (FR-014, CARD-017). A non-unique conversion fails cleanly here; recovery lands
  in the next card
- G-4: Image mode must not be wired into POL-001's regenerate loop — an uploaded image is
  fixed and is never silently re-drawn (policies.yml POL-002 rationale)
  (test: TestRegenerate_FiresOnUniquenessFailure must remain scoped to random/library mode)
- G-5: `--image` validation stays inward of argparse (ADR-0010) — the file-readability check
  is a domain error, not an argparse `type=`
- G-6: INV-003's retry counter keeps its single home in COMP-002 — do not add a counter to
  `image.py`

## System contract

- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions (check: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (check: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (check: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF)
- INV-003 — A puzzle's automatic-retry counter (regenerate, resample, pixel-nudge) never exceeds its configured maximum bound (check: TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestNudge_ReportsFailureAtCap, TestRetryLoop_BoundedIterations)

## Architecture context

- **FR:** FR-003
- **NFR:** —
- **ADR:** ADR-0006, ADR-0010, ADR-0012
- **Components:** COMP-003 (Grid Sourcing — image path), COMP-001 (`--image` flag)
- **Trace:** meta/architecture/trace.yml

## Worktree notes

[Follow-up from CARD-007 review, cycle 2] `cli.py`'s `main()` currently has a bare
`except OSError` clause wrapping the whole `args.handler(args)` call, added by CARD-007 to
report a bad `--out` path cleanly. It maps every `OSError` to `ExitCode.EXPORT_REJECTED`
(5) on the premise — true only until now — that an `OSError` can only come from the export
step. This card reads a user-supplied image file from disk, so a missing/unreadable
`--image` path will now be misreported as "export rejected" instead of an input error.
Either narrow that `except` to wrap only the export call (not the whole handler), or raise
a proper domain error for the image-read failure before it can reach that clause as a bare
OSError.

[Follow-up from CARD-008 review, cycle 1] `orchestrator._source_arguments(request)` maps a
request's mode to the source callable's leading positional arguments via an if/else with a
bare fallback: `mode == LIBRARY → (library_key, size)`, else `→ (size, density)`. The
fallback comment reasons "an unknown mode never reaches here — `for_mode` already raised,"
which is true only for a mode that isn't *registered* at all. When this card registers
`IMAGE: image.generate` in `sourcing/__init__.py`'s dispatch table, if the matching branch
here is forgotten, `image.generate` silently gets called as `(size, density, rng)` — a file
path argument bound to an integer size — producing a confusing failure instead of a clear
wiring error. Add an explicit `mode == RANDOM` branch and raise `ValueError(f"no source
argument list for mode {mode!r}")` in the else, rather than extending the implicit fallback
a third time.

---

[Implementation, CARD-015] What landed, and the decisions behind it.

**`sourcing/image.py` (new).** `generate(source, size, rng) -> list[list[bool]]`, registered
as `IMAGE: image.generate` in `sourcing/__init__.py`'s dispatch table. The pipeline is
`open -> flatten transparency onto white -> greyscale -> centre-crop to square -> resize to
size x size -> Floyd-Steinberg dither -> ink is a filled cell`, split into four named
functions (`load_greyscale`, `square_crop_box`, `binarize`, `to_grid`) so the aspect-ratio
policy and the polarity can each be tested without an image or a threshold in the way.
Dithering is `Image.convert("1", dither=Image.Dither.FLOYDSTEINBERG)` — Pillow's own
Floyd-Steinberg, named explicitly rather than left as the mode-`"1"` default — and NumPy
does the arithmetic on the far side of it, one vectorised comparison against black instead
of a per-pixel loop (ADR-0006's division of labour, guardrail G-2: no new dependency).

The `rng` argument is accepted and deliberately never drawn from. That is the whole reason
image mode cannot join POL-001 (below), and it is asserted directly: two different seeds
give the same grid, and the RNG handed in comes back with its state untouched.

**Aspect-ratio policy (AC-009): centre-crop, then resize.** The source is cropped to its
largest centred square and that square is resized to the grid, so the output is exactly
`size` x `size` whatever the input's proportions were. Both alternatives were rejected for
reasons written into the module docstring. *Stretch* keeps every pixel but distorts the
subject, and at 10..50 cells there is no resolution to spare for the viewer to mentally
un-stretch a squashed face — a nonogram's whole payoff is that the solved grid is a
recognisable picture. *Letterbox* keeps proportions but spends the scarcest resource there
is on nothing: a 16:9 photo padded into a 25x25 grid burns ~7 of its 25 rows on blank paper,
which is both a worse picture and a worse puzzle (an empty row is a `0` clue and a free line
for the solver). Cropping loses the ends of the long axis; that is the honest cost, and it
is centred rather than anchored because the subject of a photograph is near the middle far
more often than at an edge. The `wide.png`/`tall.png` fixtures are built so one assertion
tells all three policies apart: their outer thirds are black, so under a stretch or a
letterbox that ink would reach the grid, and under the crop it does not.

**AC-008.** `errors.UnreadableImage` covers every way a `--image` can fail to become a
picture — missing, unreadable, a directory, a corrupt/undecodable file, or the flag omitted
in image mode. `Image.open` is followed by `.load()` inside the guarded block, because
Pillow is lazy and a truncated body would otherwise raise at the caller's first pixel
access, outside the guard. Tested structurally as well as behaviourally: `UnidentifiedImageError`
is itself an `OSError`, so the test asserts the escaping exception is a `NonogramError` and
is *not* an `OSError` of any kind, with Pillow's exception demoted to a chained `__cause__`.

**G-4 — image mode genuinely bypasses POL-001.** `orchestrator.generate` grew an explicit
`request.mode == sourcing.IMAGE` branch that converts **once**: no `run_bounded`, no counter
advanced, and a candidate that fails either the uniqueness check or the requested tier ends
the run with `GenerationAbandoned` carrying its own wording (`_image_uniqueness_reason` /
`_image_tier_reason`). Neither message mentions attempts, because nothing was retried, and
neither offers `--seed` as a lever, because re-seeding an image run reproduces the identical
grid. The test that matters is not "it fails cleanly" — a run that quietly took one turn of
the regenerate loop would satisfy that — but the count: a scripted source is asked for
exactly one candidate, and both INV-003 counters are read off the aggregate at zero,
including on the happy path. `TestRegenerate_FiresOnUniquenessFailure` in
`tests/test_orchestrator.py` is untouched and still scoped to random/library mode; a test
here re-asserts from the new module that exempting image mode exempted nothing else. There
is also a pinned real-file case: `bands.png` at 10x10 genuinely converts to a non-unique
grid and comes back through the CLI as exit code 4.

No pixel-nudge loop and no nudge count (G-3), and no counter in `image.py` (G-6) — INV-003's
counter keeps its single home in COMP-002, where CARD-016's nudge counter is expected to
land next to `regenerate` and `resample`.

**Follow-up 1 (CARD-007 review, cycle 2) — resolved, both ways.** The bare `except OSError`
that wrapped the whole `args.handler(args)` call in `main()` is gone. It has been moved into
`_run_generate` and narrowed to wrap only `orchestrator.export_puzzle(puzzle)`, which is the
call it was always about; the two reporting sites now share one `_report` helper so the
message format cannot drift. Independently of that, an image read never produces a bare
`OSError` at all — `sourcing.image` raises `UnreadableImage`, which the CLI maps to
`ExitCode.INVALID_INPUT` (3), the same group as a bad size or an unknown library key, and
explicitly not `EXPORT_REJECTED` (5). Three tests pin the outcome: a missing `--image` exits
3 with `cannot read image` on stderr and no traceback; a non-export `OSError` is no longer
swallowed as an export failure (it stays unhandled, which is the honest outcome for a
failure the adapter has no story for); and an export `OSError` is still reported cleanly,
so what CARD-007 added the clause for still works. `tests/test_export_json.py`'s original
`--out`-is-a-file repro passes unchanged.

**Follow-up 2 (CARD-008 review, cycle 1) — resolved as suggested.**
`orchestrator._source_arguments` now has three explicit branches (`RANDOM`, `LIBRARY`,
`IMAGE`) and raises `ValueError(f"no source argument list for mode {mode!r}")` in the else,
the note's exact wording. Confirmed the hazard was real before fixing it: with the implicit
fallback, registering `IMAGE` would have called `image.generate(size, density, rng)` and
bound a file path to an integer. Two tests guard it — the `else` by name, and a loop
asserting every mode in `sourcing.MODES` has an argument list.

**Files touched beyond the predicted `Touches:`** (flagged rather than done silently, per
CARD-010/011/014):

* `src/nonogram/errors.py` — required by AC-008's own wording ("a 'cannot read image'
  domain error **from `errors.py`**"); one new `UnreadableImage` class, no behaviour.
* `tests/test_sourcing_random.py` — `test_the_advertised_modes_match_the_dispatch_table`
  asserted `MODES == ("random", "library")`, and `test_for_mode_rejects_an_unregistered_mode`
  used `"image"` as its unregistered stand-in. Registering the mode necessarily breaks both.
  The stand-in is now a made-up `"webcam"`; the dispatch table is closed at three modes, so
  no future card inherits the same edit.
* `tests/test_orchestrator.py` — same stand-in substitution in
  `test_an_unknown_mode_fails_before_any_candidate_is_sourced`, same reason.
* `tests/test_cli.py` — same stand-in substitution in the usage-error parametrization
  (`--mode image` now parses), plus `UnreadableImage` added to `ERROR_EXIT_CODES`, which
  `test_every_domain_error_has_an_exit_code` requires of every declared domain error.

Fixtures: `tests/fixtures/bands.png` (32x32, black / mid-grey / white bands — the mid band
is the dithering witness, since a 50% threshold renders a flat 128 field as one solid
colour), `wide.png` (60x20) and `tall.png` (20x60, its transpose, so the crop is pinned on
both axes), and `corrupt.png` (a real PNG signature followed by garbage). 88, 100, 97 and 53
bytes respectively. Exotic one-off inputs — a flat mid-grey field, an RGBA image with a
transparent hole — are built in `tmp_path` instead, since a repo fixture should be something
a reader can open and recognise.

Both non-obvious behaviours were mutation-checked before the notes were written: replacing
the crop with a stretch fails 8 tests, and replacing Floyd-Steinberg with `Dither.NONE`
fails 5.

**Test run.** `./.venv/bin/python -m pytest` → **1121 passed, 1 xfailed** (baseline before
this card: 1045 passed, 1 xfailed). No regressions. The pre-existing AC-037 xfail
(`tests/bench_generate.py::test_20x20_p95_is_under_5s`) is unchanged in both status and
reason — still the ADR-0001/CARD-018 solver search-strength gap. The 76 added cases are the
74 in `tests/test_sourcing_image.py` plus two that came free from existing
parametrizations widening (`--mode` choices, the error/exit-code table).

### Orchestrator notes

- **[Scope]** Touches match predicted plus four explicitly-flagged files
  (`src/nonogram/errors.py` for the new `UnreadableImage` class required by
  AC-008's own wording; `tests/test_sourcing_random.py`,
  `tests/test_orchestrator.py`, `tests/test_cli.py` — all three used
  `"image"` as their unregistered-mode stand-in, now `"webcam"`, since the
  mode is now real). No silent creep. G-1 confirmed clean (empty diff on
  `random_grid.py`, `library.py`, `solver/**`, `export/**`, `clues.py`,
  `difficulty.py`); G-2 confirmed clean (`pyproject.toml` untouched).
- **[Build gate]** PASSED (full, independently re-run by orchestrator in a
  fresh venv: 1121 passed, 1 xfailed, exit 0; AC-037 xfail unchanged in
  status and reason).
