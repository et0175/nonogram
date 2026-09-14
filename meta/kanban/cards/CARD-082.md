# CARD-082: The suite baseline says what it means — three standing failures and one 40% flake

**Status:** done
**Priority:** P2
**Category:** tech-debt
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/082-suite-baseline
**Worktree:** ../PythonProject4-CARD-082
**Source:** owner request after CARD-070 ("fix those three remaining failures"); the residue of the 14-failure baseline that CARD-070 took to 9
**Idea:** —
**Wave:** 1
**Depends on:** — (CARD-070 merged 4362a7e)
**Touches:** pyproject.toml (package-data), tests/test_web_upload.py (one assertion), tests/test_wave1_e2e.py + tests/test_wave2_async_generation.py (one stale call + batch counts and sizes), tests/test_puzzle_review.py (new tests), src/nonogram/admin/puzzle_review.py (a legible refusal)
**Review score:** 9.0 (cycle 1), all findings fixed
**Started:** 2026-09-14
**Closed:** 2026-09-14
**Actual:** —
**Merge commit:** a13c9bf
**Blocked by:** —

## Why

A suite with a standing failure list is a suite nobody reads. Every card this
week has cost a hand-check to decide whether failure number fifteen was mine or
the baseline's, and twice the answer was wrong on the first reading.

Three failures remained after CARD-070, and **one of them was not a test
problem at all**: the font the PDF exporter depends on never reached a built
wheel. The test saying so had been failing for long enough to read as
furniture.

## What was wrong, measured

### 1. The font does not ship (a real defect, not a stale test)

`pyproject.toml` had no `[tool.setuptools.package-data]` block. setuptools
ships no non-Python file without one, so:

```
wheel built from main: 60 entries, font entries: NONE
```

`pdf._font_bytes()` reads through `importlib.resources`, which finds the file
in a source checkout — pytest's `pythonpath = ["src"]` reads it off disk — and
raises on any real install. **PDF export was broken in every wheel this project
could build**, and the one test that checks it was in the standing-failure
list.

ADR-0006/R1 permits the font *because* it ships as package data rather than as
a dependency. That permission was only true once the block existed.

### 2. A test pinning a third-party library's prose

`test_the_page_reports_the_same_failure_the_cli_reports` matched
`cannot read image '<path>': cannot identify image file '<path>'` — half ours,
half Pillow's. Pillow says `broken data stream when reading image file` for
this fixture, because `corrupt.png` is a valid PNG signature followed by
garbage, so Pillow *identifies* it and then fails on the data.

Same history as CARD-070's nudge pins, third instance: the test arrived in
`96da6ac` naming a fixture that was **absent at that commit**, and `02a25a2`
fabricated one two days later. The fixture matches its documented contract
(`test_the_fixture_images_are_present_and_shaped_as_documented` asserts the PNG
signature); the pin never matched the fixture.

Fixed by asserting *our* half of the template on each message and then that the
decoder's half is **identical between the two surfaces** — which is what "the
same domain error" actually claims, is stronger than matching a hardcoded
sentence, and does not break when Pillow rewords.

### 3. A scalar extent, four years after extents became pairs

`tests/test_wave1_e2e.py:270` called `PuzzleFilter(size=15)`. The field is
`Optional[Tuple[int, int]]` and `filter_puzzles` unpacks it, so every run died
with `TypeError: cannot unpack non-iterable int object`. **This was not a
flake** — it failed 6 of 6 isolated runs. It was the last scalar caller in the
repository; every other one has used a pair since CARD-027 (ADR-0022/R1).

Fixed the call, and made the boundary say what rule was broken instead of
unpacking blind — the `TypeError` names no extent and points five frames from
the caller that wrote the scalar.

### 4. The actual flake, quantified (taken on beyond the three)

A random 20x20 at density 50 genuinely fails POL-001's 20 regenerate attempts
about **1 time in 300** (measured, 300 draws per size: 0/300 at 15x15, 1/300 at
20x20). `tests/test_wave1_e2e.py` made **350** such draws per run, and
`orchestrator.generate_batch` has no per-candidate tolerance — one
`GenerationAbandoned` ends the whole batch — so:

| draws per run | P(at least one spurious failure) |
|---|---|
| 350 (before) | ~40% |
| 60 (after) | ~10% |

That is the "flaky e2e test" that moved between tests run to run. Counts are
now the minimum `create_batch` accepts (10); **no claim changed** — each
still checks `puzzle_count == count`, at a fifth of the dice rolls. Two
assertions do carry a different number (`len(puzzles) == 50` -> `== 10`,
`approved >= 50` -> `>= 10`); both scale with the count they are derived
from, which is the distinction the first draft of this sentence blurred.

`tests/test_wave2_async_generation.py` turned out to be the same defect and
worse — roughly **600** draws per run, to support assertions that are mostly
`is not None` against stubs whose implementations are still `# TODO`. Same
treatment: the count that carries each assertion, and `sizes=[15]` wherever the
test says nothing about grid size (measured 0/300 abandonments at 15x15 against
1/300 at 20x20). Two tests keep their volume because the volume *is* the claim
— a 100-row first page needs 200 rows, and approving 25 puzzles needs 25.

**This is a cheaper fixture, not a fix.** The 1-in-300 is real product
behaviour; reducing a test's exposure to it changes nothing about it, which is
what the open question below is for.

Measured after: 8 consecutive clean runs of `test_wave1_e2e.py`, then 6
consecutive clean runs of both wave files together.

## Acceptance criteria

- **AC-1** — a wheel built from this tree contains `nonogram/export/fonts/
  DejaVuSans.ttf` and `.../LICENSE`.
  *test:* `test_the_font_ships_as_package_data_and_not_as_a_dependency`
- **AC-2** — the web-upload test asserts no third-party wording; it compares
  the two surfaces' decoder halves to each other.
  *test:* `test_the_page_reports_the_same_failure_the_cli_reports`
- **AC-3** — a non-pair extent at the filter boundary is refused with a message
  naming `(width, height)`, and a pair is still accepted.
  *test:* `test_an_extent_that_is_not_a_pair_is_refused_by_name`,
  `test_a_pair_is_still_accepted`
- **AC-4** — the suite's non-corpus failures are zero; the only remaining
  failures are the six `tests/test_sourcing_image.py` cases that need the
  owner's `pictures/` folder.

## Guardrails

- G-1: No change to the generation pipeline, the solver, or the nudge
  heuristic. The flake's cause is a product behaviour; this card measures it
  and reduces the suite's exposure to it, and changes nothing about it.
- G-2: No fixture bytes change. `corrupt.png` is correct as documented; the
  test that mismatched it is what moves.
- G-3: Every e2e assertion keeps its meaning. Counts may fall to the documented
  minimum; no assertion may be deleted or weakened to pass.
- G-4: Commit only your own files — `nonogram_admin.db` and the egg-info churn
  are standing untracked/modified noise.

## Open question for the owner

**Should a batch survive one abandoned candidate?** `generate_batch` raises out
of the loop, so a 50-puzzle admin batch is lost entirely when the 37th draw
fails — a 1-in-300 event per 20x20 candidate, so roughly a 15% chance of losing
a full 50-puzzle batch. CARD-080 made the *store* tolerant of a refusal and
counted it; generation has no equivalent. Skipping and reporting the shortfall
is the obvious counterpart, but it changes what `count` promises, which is
yours to decide.

## Worktree notes

—

### Review cycle 1 fixes (73c06a8)

| finding | what was wrong | what it is now |
|---|---|---|
| F-001 | The rewritten upload assertion compared the two messages' causes to each other and nothing else — which **any constant satisfies**. Replacing the decoder's half in `image.py` with the literal `"unreadable"` left the test green. The robustness half of the trade was right; the lost half is the half a user reads. | The expected cause is derived in the test: `corrupt.png` is decoded with PIL and what it raises becomes the expectation. A Pillow reword updates it automatically; a constant no longer passes. |
| F-002 | `assert result is not None` against a function that either returns a response or raises — "did not raise", written indirectly. | Asserts `isinstance(result.puzzles, list)`. |
| F-003 | The card claimed "no assertion changed" where two count-derived assertions did. | Says no *claim* changed, and names them. |

Five mutants, five killed: the cause dropped for a literal, the cause replaced
by an exception class name, the path dropped, the extent guard removed, and the
extent guard tightened into refusing valid pairs.

**What the mutation check bought on this card.** F-001 was invisible to
reading — I had just written that assertion, reasoned about it in the commit
message, and described it to the owner as *stronger* than what it replaced. It
was stronger in one direction and weaker in another, and only a mutant that
replaced the decoder's message with a constant showed which. The final version
is stronger than both the original pin and the first rewrite: wording-
independent like the rewrite, substantive like the pin.
