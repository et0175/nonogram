# CARD-526: An easy picture puzzle is retried with a stricter threshold, then dithering, and kept only if it still looks like the picture

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 2c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** owner ruling 2026-11-22 ("I think we can go for Threshold, then dithering"; "yes, write the card"), on CARD-525's measured experiment and its `rescue_easy` sheets.
**Idea:** IDEA-228
**Wave:** —
**Created wave:** 92
**Deferred waves:** 0
**Depends on:** CARD-525 (its experiment script and measures are the reference to re-measure against)
**Touches:** src/nonogram/ (the picture-puzzle generation path: where is the implementer's to find and justify), its tests, docs/GENERATION_ALGORITHM.md, meta/architecture/requirements.yml
**UI surface:** none new; admin picture puzzles come out harder more often
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

CARD-525 measured that most picture puzzles come out Easy: 69.7% on the fixtures and 80.7% on the owner's folder. It also found a rule that lowers that share without touching puzzles that are already Medium or Hard. Keep today's puzzle unless it is Easy. If it is Easy, try a stricter threshold, then dithering, at the same size. Keep a new grid only if it is no longer Easy and still looks like the picture. The look test is `smooth_corr >= 0.96`, the bottom tenth of today's puzzles.

The owner chose threshold, then dithering (2026-11-22). What CARD-525 measured, and what it did not:

- **Threshold step:** measured with the floor. Easy falls from 69.7% to 59.0% on the fixtures and from 80.7% to 70.3% on the owner's folder. No puzzle is lost and no new failure appears.
- **Dithering step:** NOT measured with a fair look test. `smooth_corr` blurs over 3x3 cells, so a dithered grid passes the floor while adding checkered or scattered cells. In CARD-525 review 2, dithering raised `smooth_corr` above today's grid in 15 of 18 replacements while IoU fell. On the sheets, the toucan's beak at size 13 became a checkerboard, and the zebra and owl at size 22 gained scattered single cells. The 48.4% and 63.9% Easy figures with dithering counted those grids. The dithering step therefore needs a look test that catches that noise before it ships.
- **The rule was chosen after seeing CARD-525's runs.** Every figure this card reports must therefore come from pictures CARD-525 did not use.

## What to implement

Read CARD-525's card first, all of its AC-3 rounds and the three review records, plus `scripts/picture_pipeline_experiment.py` (`rescue_easy`, `smooth_corr`, `RESCUE_EASY_FLOOR`, the `cut_62` and `dither_all` variants). Then:

1. **Generation.** In the path the admin uses to make a puzzle from a picture, a puzzle graded Easy is retried at the same size:
   - first with the stricter threshold (`sourcing.image.INK_THRESHOLD` 96 for binarisation only; the ink box keeps 128);
   - then with dithering.

   A retry's grid replaces today's only if it is still uniquely solvable, it is graded Medium or Hard, and it passes the look test. Today's puzzle stands in every other case, including a retry that fails, times out, or exceeds the request's one deadline. Keep the layering rules in CLAUDE.md: no lateral imports between capability modules. A look measure needed in two modules is reimplemented, not imported across.
2. **Look test.** It is `smooth_corr >= 0.96` for both steps, plus a noise check on the dithering step that rejects the CARD-525 cases named above. Design the noise check from the experiment's saved grids. Then fix its threshold before the held-out run and state it in the notes. A plain option: count isolated single cells and checkerboard 2x2 blocks against today's grid. If no check separates the noisy dithered grids from the clean ones, ship the threshold step only, and say so in the notes.
3. **Held-out measurement.** Measure on pictures CARD-525 did not use. First list which picture sets CARD-525 used. If no unused set of at least 10 pictures exists on this machine, stop before measuring and ask the owner for new pictures. Report:
   - Easy/Medium/Hard shares, today versus the new rule;
   - how many replacements each step made;
   - failures and lost puzzles (expected 0);
   - added generation time.
4. **Renders.** Put a sheet of each replaced puzzle beside today's in ~/Documents/nonogram-reviews/CARD-526/, with an index naming the step that made it. Renders of the owner's pictures go only to `private/`.

## Acceptance criteria

* **AC-1:** a picture whose puzzle is Medium or Hard today gets exactly today's puzzle: same grid, no retry run. Control: a mutant that always retries makes the test red.
* **AC-2:** an Easy puzzle is replaced by the threshold retry when that retry is non-Easy and passes the look test, and is tried with dithering only when the threshold retry does not qualify. Controls: swapping the order, or dropping the floor, makes the tests red.
* **AC-3:** a retry that fails the look test, including the dithering noise check if one ships, is discarded and today's puzzle stands. The tests use one grid below the floor and one noisy dithered grid from CARD-525's cases.
* **AC-4:** no request that makes a puzzle today makes none under the new rule; retries stay inside the request's one deadline (`tests/test_timeout.py` rules). A replaced puzzle is uniquely solvable (EC-001).
* **AC-5:** the notes report the held-out measurement (item 3) with its sample size, and the step-1 noise-check threshold as fixed before that run. The figures carry no claim beyond what was measured.
* **AC-6:** `requirements.yml` gains one requirement for the rule, naming its tests, and `docs/GENERATION_ALGORITHM.md` describes the rule as built.
* **AC-7:** the net test count is reported; extend existing picture-generation tests where they fit.

## Guardrails

* **G-1:** puzzles already stored are not regenerated or regraded; only new generation changes. No publish of the public player (its puzzles come from stored ones).
* **G-2:** the owner's `pictures/` folder is read only. Only aggregates go into the repo or the card; renders of it go only to ~/Documents/nonogram-reviews/CARD-526/private/.
* **G-3:** the 90.0 difficulty cutoff and the grading itself do not change. The rule may only decide which candidate grid to keep.
* **G-4:** the public "make your own puzzle" feature stays deferred (IDEA-125/126). This card does not build or propose it.
* **G-5:** time a small held-out corpus first and state the projected full-run time before starting it.

## Worktree notes
