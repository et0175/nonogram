# CARD-517: Measure the 90.0 medium/hard cutoff against picture-made puzzles

**Status:** in_progress
**Priority:** P2
**Category:** tech-debt
**Estimate:** 2c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/517-image-difficulty-sweep
**Worktree:** ../PythonProject4-card-517
**Source:** roadmap wave 10, cut 2026-11-22 on the owner's "yes, start wave 10". IDEA-028 (deferred by the owner after CARD-137).
**Idea:** IDEA-028
**Wave:** 89
**Created wave:** 89
**Deferred waves:** 0
**Depends on:** —
**Touches:** scripts/measure_difficulty_cutoff.py
**UI surface:** —
**Review score:** 9.0 (cycle 1/3 - CERTIFIED)
**Started:** 2026-11-22T08:36Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

CARD-137 set the medium/hard cutoff (90.0, ADR-0005) from `scripts/measure_difficulty_cutoff.py` over a seeded corpus of RANDOM-mode puzzles. The books are made of picture puzzles (image mode), whose grids are structured rather than random, so their scores may sit differently against that cutoff. The owner deferred checking it after CARD-137. This card measures; it does not move the cutoff. Moving it is the owner's decision, made from this card's table.

## What to implement

Re-verify on main first: where the cutoff lives, how the script builds and scores its corpus, and what image-mode generation needs as input. Then extend the script (no new script) so the same what-if table can be produced for an image-mode corpus, through the same generation and scoring path the admin uses for picture puzzles.

The corpus must be reproducible: prefer images committed in the repo (test fixtures), or images the script generates itself from a seed. The owner's own picture folders (`pic1/`, `pictures/`, and the local panel database) may be read for an extra, read-only comparison run. Those are experiments and private: never commit them, copy them into the repo, or write their names or contents into the card. Aggregate figures only.

## Acceptance criteria

* **AC-1**: the script produces the what-if table (tier shares per candidate cutoff, overall and per longest-side bucket) for an image-mode corpus, with its size asserted and its seed recorded. The random-mode output is unchanged for the same arguments (show it: same table before and after).
* **AC-2**: the self-check (the current cutoff's row against `classify`) runs on the image corpus too and passes.
* **AC-3**: the card notes give the image-mode table beside the random-mode one, and say plainly what the 90.0 cutoff does to picture puzzles: share of each tier, and whether medium is reachable at each size bucket. If a different cutoff looks better, name it with its table row, as a proposal for the owner.
* **AC-4**: net test count at most +1; change an existing test of the script if one exists. Report it.

## Guardrails

* **G-1**: `nonogram.difficulty`'s cutoff and `classify` are not changed.
* **G-2**: no owner picture, name or local-database content is committed or written into the card; reads of the local panel database are read-only transactions, and never against production.
* **G-3**: a measurement run's wall time is stated before it is started at full size (time a small corpus first).

## Worktree notes

- [Premise] Re-verified on main 2026-11-22. The cutoff is `difficulty.MEDIUM_MAX_SCORE = 90.0`, unchanged (G-1: `src/nonogram/difficulty.py` is not in the diff). The script built random mode only, through `orchestrator.generate`. The admin makes picture puzzles in its image batch route: `ImageFile.size_fits()` picks the extent, then `admin.app._generate_image_puzzle` (found by `ast` call-site walk) runs `orchestrator.generate(GenerationRequest(mode="image", ...))` with the long-side +-1 retry. It stores `puzzle.difficulty_score` / `difficulty_tier` unchanged. The script had no test.
- [Change] `scripts/measure_difficulty_cutoff.py` gains `--mode image` (default stays `random`), plus `--pictures K` (timing runs) and `--image-dir DIR` (private extras). New: `ImageRow`, `fixture_pictures`, `seeded_pictures`, `folder_pictures`, `_admin_image`, `build_image_corpus`, `report_image`, `_image_main`. `report`'s table printers were pulled out as `_bucket_groups`, `_print_raw_histogram`, `_print_sweep`, `_print_decision_zone` and `_print_nontrivial_split`, and both modes use them. Generation goes through `admin.app._generate_image_puzzle` on an `ImageFile` in "fixed" mode at each long side N, so pictures that are too elongated move to Large or are skipped, exactly as in the batch. The admin quality filter is not applied (its session default is 0). The output never names a picture, only a kind and an index.
- [Corpus] 17 committed picture fixtures (`tests/fixtures/`, short side >= 100 px; the smaller files are synthetic sizing fixtures) plus 20 silhouettes drawn from `IMAGE_CORPUS_SEED = 20261122`, at long sides 10,13,15,16,18,20,22,24,25,26,28,30. That is 444 requests and 343 puzzles, all graded (0 branched). Not generated: 62 `GenerationAbandoned`, 7 `SolverTimeout`, 32 that repeated an extent already made for that picture. The graded-count floor `MIN_IMAGE_CORPUS = 250` is asserted, and so is `MIN_FIXTURES = 15`. Replay check: two `--pictures 3` runs gave 69 identical rows (excluding timings), and the fixture and seeded tables came out identical in a second full run.
- [G-3] Random mode: projected ~310 s from a `--draws 1` run (31 s); actual 258.6 s before and 254.4 s after. Image mode: projected "under 60 s" from a `--pictures 2` run (1.4 s); actual **336.6 s**, a miss. Five fixtures produce nothing at any size, and abandonment plus the 30 s deadline make them the cost (one took 203 s). Extra run: projected ~14 min, actual 376.7 s.
- [AC-1] Random mode is unchanged. The full default run on the pre-change script and on the changed script printed identical text except the `wall clock` line, and the `--json` dumps match on all 1005 rows (excluding per-row `seconds`).

  Side by side at the default arguments. Each cell is easy/medium/hard, overall and per FR-034 longest-side bucket; * marks the cutoff in force.

  | cutoff | random overall (n=1001) | image overall (n=343) | image <=15 (66) | image 16-20 (93) | image 21-25 (93) | image 26-30 (91) |
  |---|---|---|---|---|---|---|
  | 70 | 69.7/9.5/20.8 | 86.9/4.4/8.7 | 90.9/4.5/4.5 | 87.1/4.3/8.6 | 83.9/4.3/11.8 | 86.8/4.4/8.8 |
  | 75 | 69.7/11.0/19.3 | 86.9/5.2/7.9 | 90.9/6.1/3.0 | 87.1/5.4/7.5 | 83.9/5.4/10.8 | 86.8/4.4/8.8 |
  | 80 | 69.7/12.2/18.1 | 86.9/7.0/6.1 | 90.9/7.6/1.5 | 87.1/7.5/5.4 | 83.9/6.5/9.7 | 86.8/6.6/6.6 |
  | 85 | 69.7/14.7/15.6 | 86.9/7.6/5.5 | 90.9/7.6/1.5 | 87.1/7.5/5.4 | 83.9/7.5/8.6 | 86.8/7.7/5.5 |
  | **90 *** | 69.7/17.4/12.9 | **86.9/9.0/4.1** | 90.9/9.1/0.0 | 87.1/9.7/3.2 | 83.9/9.7/6.5 | 86.8/7.7/5.5 |
  | 95 | 69.7/21.6/8.7 | 86.9/11.4/1.7 | 90.9/9.1/0.0 | 87.1/11.8/1.1 | 83.9/15.1/1.1 | 86.8/8.8/4.4 |

  Random per bucket at 90: <=15 86.7/10.4/3.0, 16-20 65.2/22.2/12.6, 21-25 63.2/19.8/16.9, 26-30 61.6/17.4/21.0.

  Medium's share of the non-trivial puzzles (score > 33), by cutoff:

  | cutoff | 70 | 75 | 80 | 85 | 90 * | 95 |
  |---|---|---|---|---|---|---|
  | random (n=303) | 31.4% | 36.3% | 40.3% | 48.5% | 57.4% | 71.3% |
  | image (n=45) | 33.3% | 40.0% | 53.3% | 57.8% | 68.9% | 86.7% |

  By image source at 90: fixtures (n=122) 69.7/18.9/11.5, seeded silhouettes (n=221) 96.4/3.6/0.0.
- [AC-2] The self-check (`_self_check`, the in-force row against `classify`) runs on the image rows of every image run, including the default full run above, and passed every time. It is also run in the new test.
- [AC-3] What 90.0 does to picture puzzles: **86.9% easy, 9.0% medium, 4.1% hard**. Medium is reachable in every bucket: 6 of 66 (<=15), 9 of 93 (16-20), 9 of 93 (21-25) and 7 of 91 (26-30), scores 37.23..89.97. Hard is absent at <=15 (0 of 66).
  - Easy dominates because 298 of 343 picture puzzles score exactly 33.0: simple overlap finishes them. Like the random corpus's density effect (CARD-137 step 1), this is a property of the source, not of the cutoff. No cutoff moves easy off 86.9%.
  - The cutoff only divides 45 non-trivial puzzles. At 90 that split is 68.9% medium, close to the plan's 2:1 (66.7%) and more medium-heavy than random's 57.4%. At 85 it is 57.8%, at 95 it is 86.7%, and one puzzle is 2.2 points of that share.
  - **No different cutoff looks better, so none is proposed.** On picture puzzles 90.0 is already at the plan's medium:hard ratio. If the owner wants more medium books, the lever is the share of pictures that leave overlap at all, not the medium/hard edge.
  - Biases to weigh. The seeded silhouettes are simple blobs and come out 96.4% easy, so they pull the overall easy share up; the fixtures alone read 69.7/18.9/11.5. And 5 of the 17 fixtures produce nothing at any size. Those are plausibly the hardest pictures, so the hard share is a floor.
- [Private extra, aggregate only] One `--image-dir` folder of 25 pictures, read only, gave 247 graded puzzles: **81.4/12.6/6.1 at 90**, and 81.4/12.6/6.1 at 80 and 85 too (no score of theirs falls in 80..90). This is close to the reproducible corpus's reading. Combined, the non-trivial split at 90 is 62 medium to 29 hard (68.1%). The second folder named in the brief does not exist in the main checkout. The local panel database `nonogram_poc` does not exist on localhost (the one server there, port 5432, has only `nonogram_dev` and `*_test` databases), so no DB read was made. `nonogram_dev` was not read in its place.
- [Test] `tests/test_measure_difficulty_cutoff.py::test_image_mode_scores_pictures_through_the_admin_path_and_self_checks` is new; no test of the script existed. It runs one fixture and one silhouette at long sides 10 and 20, and asserts: the fixture floor; silhouettes replay byte for byte; every puzzle went through `admin.app._generate_image_puzzle` (spy count == rows); `_self_check` passes; the table prints; no file name reaches the output.
  - Control 1: `build_image_corpus` calls `orchestrator.generate` directly instead of the admin function. Red: `AssertionError: assert 0 == 4` (spy count against rows).
  - Control 2: `_tier_for`'s easy edge drifts from `<=` to `<`. Red: `SystemExit: self-check failed: score 33.0 classifies easy but this script's arithmetic says medium`.
  - Both were restored by copy, and `cmp` matched the saved good file.
- [AC-4] Net collected count: 10691 before, 10692 after (+1).
- [Gate] Unarmed, `-rfs`: `tests/test_measure_difficulty_cutoff.py`, `tests/test_card_062_abandon_retry.py` (the admin retry the script now calls), `tests/test_difficulty.py` (G-1). 46 passed, 0 failed, 0 skipped. No DB tests are involved, so no armed run.
- [Note] `pictures/` in the main checkout is git-tracked (25 files; `f3ba7198` "restore the 25-image picture corpus to main"), not untracked as the brief says. It was still treated as private per G-2: it was not used in the reproducible corpus, and no name from it is written here.

[Review 1/3] Score: 9.0, nothing gating, certified. Every table row recomputes from `img_full.json` (the 90 row 86.9/9.0/4.1, 31 medium; medium by bucket 6/66, 9/93, 9/93, 7/91; fixtures 69.7/18.9/11.5, silhouettes 96.4/3.6/0.0). An independent full rerun (341 s) gave the same 343 rows and the same failures. Random mode differs only in its wall-clock line, and the 1005 JSON rows are equal without `seconds`. The image path is the admin batch's own `_generate_image_puzzle` after `size_fits()`. Both controls red again. No private picture name in the diff. F-001 (medium): the medium/hard split rests on about 15 pictures, not 45 independent puzzles; one fixture supplies 10 of the 31 medium. Without it the split at 90 is 21/14 = 60.0%; fixtures alone give 85 → 48.6%, 90 → 62.2%, 95 → 83.8%. F-002 (low): the reason given for skipping the admin's quality filter is wrong; the upload form submits 25, not 0. Measured at 25: 2 easy rows drop, the 90 row becomes 86.8/9.1/4.1, the 31/14 split is unchanged. F-003 (low): "the hard share is a floor" does not follow; the 5 fixtures that produce nothing fail the same way in the admin and never reach a book. F-004 (low): three mutants pass the test (short sizing, the repeated-extent skip off, the elongation check off). F-005 (low): the headline is mostly synthetic silhouettes (221 of 343 rows); the real-picture readings are fixtures 69.7/18.9/11.5 and the owner's folder 81.4/12.6/6.1. F-006 (info): the 7 solver timeouts are wall-clock dependent, so the corpus replays on this machine.

**Orchestrator reading of AC-3, after review 1.** The owner should read the result as: on real pictures, 90.0 gives 70-81% easy, 13-19% medium and 6-12% hard. Easy is set by the pictures, not by the cutoff. Among the non-trivial puzzles, 90 gives about 60-69% medium, the candidate nearest the plan's 2:1. That split rests on about 15 pictures, so the figure is a direction, not a precise share. The hard share is not a floor (F-003), and skipping the quality filter changes nothing measurable (F-002). No cutoff change is proposed.
