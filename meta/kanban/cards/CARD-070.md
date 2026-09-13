# CARD-070: Generation quick fixes — batch tier spelling, stale nudge pins, docstring drift

**Status:** done
**Priority:** P2
**Category:** tech-debt
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/070-generation-quick-fixes
**Worktree:** ../PythonProject4-CARD-070
**Source:** docs/GENERATION_ALGORITHM.md §10.2, findings 1, 4, 5 and 7 of the 2026-09-12 generation code review; follow-up card, not decomposed from handoff.md
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/orchestrator.py (generate_batch tier validation only), src/nonogram/sourcing/random_grid.py (one comment), tests/test_batch_generator.py or a new tests/test_card_070_batch_tier.py, tests/test_nudge.py, tests/fixtures/bands.png (replace only if (a) below is chosen)
**Review score:** 9.0 (cycle 1), all findings fixed
**Started:** 2026-09-13
**Closed:** 2026-09-13
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

### What actually broke the nudge pins: they never matched their fixtures

The card assumed drift — the fixture bytes changed, or the resize/dither path
did. Neither. **The pins and the fixtures were never taken from the same
image.**

`tests/test_nudge.py` arrived whole in `96da6ac` (2026-09-08) carrying pins on
`bands.png` and `landscape.png`. Both files were **absent from the repository at
that commit** (`git cat-file -e 96da6ac:tests/fixtures/bands.png` → missing).
Two days later three commits created stand-ins so the suite could run at all —
`2aece6a` "add missing bands.png test fixture", `4295166` "recreate bands.png
fixture with proper band structure", `02a25a2` "create missing image fixtures
for sourcing tests" — and nobody re-derived the counts.

`src/nonogram/sourcing/image.py` has not changed since. So the pipeline is
innocent and so is the current fixture: there was never a version of this
repository in which those tests measured what they claimed.

### Why re-pinning the size could not work

The module docstring's own recipe is "re-pin by re-running a 10..25 sweep over
the fixtures". Ran it. **Zero nudges at all sixteen sizes, for both fixtures.**

The reason is visible in the files: both stand-ins are hard black-and-white —
`bands.png` is 32x32 with exactly **2** grey levels, `landscape.png` 60x40 with
2. A file named for *bands*, whose job is to exercise Floyd-Steinberg
dithering, contains no mid-tones at all. With nothing to dither, every
conversion is a clean silhouette and trivially unique, so the nudge loop is
never entered at any size.

So neither (a) nor (b) from the card: **(c) re-point the pins at a photograph
already in the repository.** No fixture byte changes (G-2 holds trivially), and
the pins land on a real picture, which is what the module docstring says the
real-image tests are *for*.

### The sweep that chose the new pins

Seven photographic fixtures x sizes 10/12/15/18/20/22/25:

| fixture | 10 | 12 | 15 | 18 | 20 | 22 | 25 |
|---|---|---|---|---|---|---|---|
| duck1 | cap | cap | cap | cap | cap | cap | cap |
| duck2 | cap | cap | cap | cap | cap | cap | cap |
| **owl1** | **2 nudges** | 0 | **cap** | cap | cap | cap | cap |
| tiger1 | cap | cap | cap | cap | cap | cap | cap |
| tree1 | cap | cap | cap | cap | cap | cap | cap |
| tukan | 0 | 0 | cap | 0 | cap | cap | cap |
| zebra1 | 0 | cap | cap | cap | cap | cap | cap |

`owl1.png` (405x500, 256 grey levels) is the only fixture that produces an
intermediate result, and it produces both cases the tests need. Using one
picture for both removes "maybe the other fixture is just harder" as an
explanation for the difference — what separates repair from the cap is the
extent and nothing else.

Both pins are seed-independent, checked across seeds 1, 2, 7, 42, 999 and
unseeded: image mode draws no randomness, so these are facts about the picture
and the extent rather than about a seed.

### The five tests re-pinned (the card predicted three)

| test | was | now |
|---|---|---|
| `test_nudge_attempts_bounded_recovery_on_a_real_image` | bands 10x10, 2 nudges | owl1 10x10, 2 nudges |
| `test_nudge_reports_failure_at_cap_on_a_real_image` | landscape 22x22 | owl1 15x15 |
| `test_nudge_reports_failure_at_cap_through_the_cli` | landscape `--size 22x22` | owl1 `--size 15x15` |
| `test_export_reports_nudge_count` (AC-040) | bands `--size 10` | owl1 `--size 10` |
| `test_a_bare_size_image_run_decodes_the_picture_exactly_twice` | bands bare 10 | owl1 bare 10 |

The card's §10.2 #5 said "three tests on the same fixture"; measured, it is five
across three files, and they were on two fixtures. `bands.png` and
`landscape.png` stay in the repository — `test_sourcing_image.py` and the
aspect-guard helpers in `test_grid_dimensions.py` use `bands.png`'s square ink
box, and `test_nudge_reporting.py`'s AC-041 uses `landscape.png`'s zero-nudge
conversion, which is still true of it.

One docstring needed more than a name swap. `test_a_bare_size_image_run_...`
argued that bare and explicit forms land on the same extent because "bands.png
is 32x32, so a bare --size 10 derives exactly the 10x10 the explicit form
states". owl1 is 405x500, so bare 10 derives `round(10 * 405 / 500) = 8` and
MIN_SIZE raises it to 10. Same destination, different route, and the docstring
now says so rather than leaving a reader to discover it.

### Item 1 — the batch tier gate

Routed through `difficulty.parse_tier`, so a batch and an interactive run share
one vocabulary, and the parsed tier's *value* goes into the request rather than
the caller's string — the request is parsed again downstream, and handing it
the canonical spelling means the second parse cannot disagree with the first.

Chose `UnsupportedDifficulty` over restating a `ValueError`: it is the domain
error already defined for this question, already mapped to
`ExitCode.INVALID_INPUT` by COMP-001, and already carrying a message that lists
the tiers read off the enum. Raising `ValueError` would mean catching that
answer and saying it less well. The choice and the reason are in the
docstring's `Raises:` block, as the card asked.

**AC-1 is stale in one detail:** it says the refusal must name "the three
tiers". ADR-0025 added a fourth. The message lists all four because it reads
the enum, and `test_the_refusal_names_the_tiers_that_do_exist` iterates `Tier`
rather than transcribing a list, so it will keep being right after a fifth.

CARD-076's two tests anticipated this card and needed updating: one asserted
`made == [tier.name]` (now `tier.value`), the other expected the old
`ValueError`.

### Item 4 — the timeout suite

Could not reproduce. `tests/test_timeout.py` passed 17/17 five times in
isolation and once batched with `test_orchestrator.py` and `test_solver.py`.
Recorded as not-reproduced on this tree rather than as a known flake.

### Suite: 14 failures -> 10, and what the last four are

All five stale-pin failures are gone. AC-3 asks for everything except the
`pictures/` corpus to pass; it does not, and the remainder is outside this
card's declared Touches and guardrails:

| failure | what it is | why not here |
|---|---|---|
| `test_export_pdf.py::test_the_font_ships_as_package_data...` | `KeyError: 'package-data'` | a `pyproject.toml` packaging question, not generation |
| `test_web_upload.py::...reports_the_same_failure_the_cli_reports` | Pillow now says "broken data stream when reading image file" where the test pins "cannot identify image file" | a Pillow-version pin in the web adapter's tests; G-3 puts the web adapter off-limits |
| `test_wave1_e2e.py` (x1-2, moves between runs) | the standing `batch_gen.jobs` singleton / unseeded-generation flake — failed 1 of 3 isolated runs, on a different test each time | a flake, not a failure; its own card |

Six `test_sourcing_image.py` failures are the `pictures/` corpus (§10.2 #6),
excluded by AC-3 and by the owner's standing "don't restructure pic1/ and
pictures/".

### Review cycle 1 fixes (1500c1c)

One Important, three Minor, all fixed.

| finding | what was wrong | what it is now |
|---|---|---|
| F-001 | The gate guarded on truthiness, so `""` skipped `parse_tier` and the batch read it as "any tier" while `generate` refused it one frame down — the exact split item 1 was meant to close, while the docstring claimed it was closed. The mutation check caught it: flipping the guard changed nothing the suite could see. | `is not None`. `""` is a tier name that does not exist and both functions say so with the same message, asserted as **one** claim about both so a later change cannot fix half of it. A second test pins that `None` still means "any" — every real caller passes `None`. |
| F-004 | The gate became a pure duplicate of `generate`'s own parse at `:1492`, which already runs before a seed is drawn. | Kept — a batch of 200 should fail at the call, not inside the loop — but the comment now says it is a boundary convenience and not the enforcement point, and that it must stay a *delegation* to `parse_tier` rather than a second statement of the rule. |
| F-002 | `BANDS` left declared and unused in `test_nudge.py` — in the one file whose docstring explains at length why that fixture must not carry nudge pins. | Deleted. `bands.png` itself stays for `test_sourcing_image.py` and the aspect helpers. |
| F-003 | The two cap tests stated their count but not where it came from, which AC-2 asks for. | Both name `landscape.png` 22x22 as what they were re-pinned from. |

**What the mutation check bought.** Nine mutants across the two cycles, eight
killed. The one survivor was F-001 — an inconsistency that no reading of the
diff had turned up, in a line whose comment asserted the opposite. The most
valuable kill was the opposite kind: changing the resize filter from LANCZOS to
NEAREST fails all five re-pinned tests, which is the first evidence that these
pins actually detect pipeline drift. Before this card they could not — they
failed regardless of the pipeline, so a real regression in `sourcing/image.py`
would have been invisible underneath them.

**Suite: 14 failures on `main` -> 9 here.** The five stale-pin failures are
gone. What remains is six `pictures/`-corpus cases (excluded by AC-3), the
`pyproject` packaging `KeyError`, the Pillow error-string pin in the web
adapter's tests, and the standing `wave1_e2e` flake — each outside this card's
Touches and guardrails, and each a small card of its own.
