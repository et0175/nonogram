# CARD-525: Where picture puzzles lose their difficulty and fail to generate: a measured experiment

**Status:** in_progress
**Priority:** P2
**Category:** feature
**Estimate:** 2c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/525-picture-quality-experiment
**Worktree:** ../PythonProject4-card-525
**Source:** roadmap wave 13, cut 2026-11-22 on the owner's "yes, start wave 13", after CARD-517's measurement.
**Idea:** —
**Wave:** 92
**Created wave:** 92
**Deferred waves:** 0
**Depends on:** —
**Touches:** scripts/ (one experiment script), scripts/README.md
**UI surface:** —
**Review score:** 7.5 (cycle 1/3)
**Started:** 2026-11-22T15:49Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

CARD-517 measured picture puzzles through the admin's own path: on real pictures 70-81% come out easy whatever the cutoff, the medium/hard split depends on which pictures are chosen, and about 1 request in 6 produces no puzzle (abandoned or timed out). The books are made of picture puzzles, and the owner set aside a public "make your own puzzle" feature because arbitrary pictures too often give an unsolvable or unrecognisable puzzle. Both point at the same place: the steps that turn a picture into a grid. This card finds, by measurement, which of those steps make a puzzle trivially easy or ungeneratable, and what changing them would do. It changes no product behaviour.

## What to implement

Read docs/GENERATION_ALGORITHM.md and the image path CARD-517 found (`admin.app._generate_image_puzzle` after `ImageFile.size_fits()`), then trace the stages a picture goes through (loading, cropping/sizing, thresholding to black and white, any clean-up, the uniqueness solve and its retry or abandon). Build one experiment script under scripts/ that reuses CARD-517's corpus (`scripts/measure_difficulty_cutoff.py`'s fixture and seeded corpora, and the owner's `pictures/` folder as an extra, aggregate-only, run) and:

1. **Attributes the outcomes.** For each request, record which stage decided it: easy because line logic alone solves it (and what the grid looks like: fill ratio, run lengths, symmetry), or failed because of no unique solution, an abandoned retry, or the deadline.
2. **Tries one change at a time** (an ablation), each a parameter or step the pipeline already has or a small, clearly-described variant done inside the script without editing src/: for example the threshold or its method, the fill-ratio target, sizing or crop choices, the retry budget. For each, report tier shares, the failure rate, and how far the grid strays from the picture (a simple similarity measure, stated).
3. **Shows the owner.** For a handful of pictures, render the picture, today's grid and each variant's grid side by side to ~/Documents/nonogram-reviews/CARD-525/ (never into the repo), so the owner can judge recognisability by eye.

## Acceptance criteria

* **AC-1**: a stage-by-stage attribution table for today's pipeline on the reproducible corpus: how many puzzles are easy, medium, hard, and failed, and which stage decided each failure; the corpus size asserted, the seed recorded.
* **AC-2**: an ablation table: each variant's tier shares, failure rate and similarity to the picture, against today's row, on the same corpus.
* **AC-3**: the card notes end with a short, plain recommendation for the owner: which one or two changes look worth a card, with their numbers, and what they cost in recognisability; or that none do, if so.
* **AC-4**: renders for at least 6 pictures (fixtures, not the owner's private pictures, unless aggregate-only text is all that leaves the machine) are in ~/Documents/nonogram-reviews/CARD-525/, with an index file naming what each image shows.
* **AC-5**: no change under src/; net test count at most +1 (a smoke test of the script, if any). Report it.

## Guardrails

* **G-1**: product behaviour does not change: nothing under src/ is edited, and the 90.0 cutoff stays.
* **G-2**: the owner's `pictures/` folder is read only, never copied, renamed or restructured; its names and contents are never written into the repo or the card (aggregates only). Its renders may go to ~/Documents/nonogram-reviews/CARD-525/private/ (local, not committed).
* **G-3**: time a small corpus first and state the projected full-run time before starting it; no single run over 30 minutes without saying so in the notes first.

## Worktree notes

- [G-3, before the full runs] Timing run `--pictures 3 --workers 4` (3 fixtures + 3 silhouettes, 69 requests, all nine variants): 178 s wall clock. Eight variants took 0.8..5 s each; `outline` took 162 s (in the full run 338 of its 412 requests are abandoned after the nudges at every extent tried, and 15 hit the deadline). The full corpus adds CARD-517's five fixtures that make nothing at any size (517 measured one at 203 s serial), so with 4 workers a variant's floor is about that one picture. Projection: run A (`today`, `dither_all`, `cut_62`, `cut_37`, `box_resize`) ~20 min; run B (`today`, `despeckle`, `nudges_15`, `deadline_90`) ~21 min; run C (`today`, `outline`) ~20 min; one serial `today` run ~6 min for the premise check. Run one after another, none over 30 min; about 65 min in all.
- [G-3, actuals and the next run] Actuals: serial `today` 334 s; run A 1750 s (projected ~20 min, a miss: `dither_all` and `box_resize` ran 245 s and 262 s); run B 1135 s; run C 604 s; run D (`today`, `fill_holes`, added after reading A-C) 251 s. The private run was started once during a merge-gate full suite in the main checkout and stopped at once (4 busy workers could disturb a timed gate); it was restarted after the lock cleared, with `--only-image-dir`. Next: the owner's folder (25 pictures, read only, aggregate only) under `today`, `dither_all`, `cut_62`, `cut_37`, `despeckle`, `fill_holes`, `nudges_15` with 4 workers. CARD-517 measured `today` on it at 377 s serial; projected ~20-25 min.
- [Actual] Owner's folder run: 267 s (projected 20-25 min; the projection assumed the fixtures ran too).
- [Premise] Re-verified before measuring: the serial `today` run reproduces CARD-517's image corpus exactly: 444 (picture, size) pairs, 32 repeats of an extent already made, 412 requests, 343 made, 62 `GenerationAbandoned`, 7 `SolverTimeout`, 0 branched; 86.9/9.0/4.1 at 90.0. Every later `today` run (A-D, 4 workers each) matched it row for row on outcome and score (`replay of 'today': 444 rows, 0 differ`, four times), so running 4 workers in parallel moved no result, the 7 timeouts included.
- [Change] New `scripts/picture_pipeline_experiment.py`, plus a `scripts/README.md` section. It imports CARD-517's `fixture_pictures`, `seeded_pictures`, `folder_pictures` and `_admin_image` from `scripts/measure_difficulty_cutoff.py` (not copied). `run_picture` runs every size of one picture through `ImageFile.size_fits()` and `admin.app._generate_image_puzzle`, with spies on `orchestrator.generate` (extents tried, outcome) and `solver.solve` (solve count, to tell a deadline on the first solve from one during the nudges). `VARIANTS` holds one change each, applied by `applied` (`unittest.mock.patch.object` on one module attribute for the run); nothing under `src/` changes (`git diff HEAD -- src/` is empty). `reference_grid` and `ink_iou` are the similarity measure. `render` and `write_index` make the sheets. Nothing printed or written to JSON names a picture from `--image-dir`.
- [Variants] Exactly what each changes:
  - `dither_all`: `sourcing.image.DEFAULT_BINARISATION = DITHER` (Floyd-Steinberg for every picture; today the classifier picks).
  - `cut_62` / `cut_37`: `sourcing.image.INK_THRESHOLD` 128 -> 96 / 160, so a cell is filled at about 62% / 37% ink instead of 50%. Only `binarize` reads it at run time; the ink box's threshold is a default argument bound at import and stays 128 (found by `ast`: the two loads of the name are `ink_bounding_box`'s default and `binarize`).
  - `box_resize`: `sourcing.image.RESAMPLING` LANCZOS -> BOX (area average).
  - `despeckle` (script-only step after `convert`): one pass; a filled cell with no filled 4-neighbour is emptied, an empty cell whose 4-neighbours are all filled is filled.
  - `outline` (script-only step after `convert`): a filled cell whose 4-neighbours are all filled is emptied, leaving a one-cell outline.
  - `fill_holes` (script-only step after `convert`): every empty cell not 4-connected to the border is filled, so an outline drawing becomes a silhouette.
  - `nudges_15`: `orchestrator.MAX_NUDGE_ATTEMPTS` 5 -> 15.
  - `deadline_90`: `orchestrator.GENERATION_BUDGET_SECONDS` 30 -> 90.
  - The image path has no fill-ratio target; the two cuts are the nearest lever. Sizing is not a variant: the corpus already spans 10..30, and no request in it was refused for size (0 `cannot fit`, 0 aspect refusals).
- [Similarity] One measure: ink IoU (cells filled in both / cells filled in either) between the puzzle's grid and a reference grid: the picture's ink box, cropped to the grid's ratio by the pipeline's own `fit_crop_box`, area-averaged to the grid's extent, filled where at least half the cell is ink. Limits: the reference is nearly today's threshold conversion, so it favours today and the variants close to it (`box_resize` scores 1.000 by construction, which says nothing about recognisability); on line art a one-cell shift of a thin line counts as two errors, so line-art IoU is low even when the drawing reads well; it is blind to recognisability (an outline of a silhouette is recognisable and scores low). Read it as "how far the grid strays from the picture's cells", and use the renders for "is it recognisable".
- [AC-1] Today's pipeline, corpus: 17 committed fixtures + 20 silhouettes from seed `20261122`, long sides 10,13,15,16,18,20,22,24,25,26,28,30; 444 pairs asserted (`EXPECTED_FULL_REQUESTS`), 32 repeats, 412 requests.

  | | fixtures (17 pictures) | silhouettes (20) | all |
  |---|---|---|---|
  | requests | 191 | 221 | 412 |
  | made: unique at conversion | 44 | 125 | 169 |
  | made: after 1-5 nudges | 71 | 94 | 165 |
  | made: only at a neighbour extent | 7 | 2 | 9 |
  | failed: abandoned, not unique after the nudges at every extent | 62 | 0 | 62 |
  | failed: deadline on the conversion's first solve | 6 | 0 | 6 |
  | failed: deadline during the nudges | 1 | 0 | 1 |
  | failed: cannot fit / aspect refused | 0 | 0 | 0 |
  | made, easy/medium/hard | 85/23/14 (69.7/18.9/11.5%) | 213/8/0 (96.4/3.6/0.0%) | 298/31/14 (86.9/9.0/4.1%) |

  - **Failures come from line drawings.** All 69 failed requests are on 7 of the 17 fixtures; 6 of them (dove1, dove3, duck1, duck2, tiger1, tree1) are outline drawings and fail at 9-12 of their sizes; the 7th, zebra1, fails at 2. At the predicted extent 41 of the 69 conversions took the threshold path and 28 the dither path; 16 of those 28 the classifier sent to threshold, the grid came out under 5% ink, and the guard fell back to dither, which turns thin lines into scattered cells (renders: fixtures 07 and 13). The 6 first-solve timeouts are all one picture (dove1). Failed requests took 317 s of generation time, made ones 14 s.
  - **Easy comes from solid shapes.** Median grid shape, easy vs medium+hard: run length as a share of its line 0.371 vs 0.183 (fixtures 0.229 vs 0.167), clues per line 1.24 vs 1.51 (fixtures 1.52 vs 2.08), fill 0.450 vs 0.371, left-right symmetry 0.750 vs 0.723. Easy grids are blobs with long runs, which the overlap rule finishes. The silhouettes are solid blobs and come out 96.4% easy; that is why they pull the headline toward easy (CARD-517 F-005).
  - Per picture (easy/medium/hard/failed): fixtures 00 11/0/0/0, 01 3/4/4/0, 02 10/0/1/0, 03 8/2/2/0, 04 10/1/0/0, 05 0/0/0/12, 06 0/0/0/12, 07 0/0/0/11, 08 2/0/0/9, 09 6/5/0/0, 10 11/0/0/0, 11 11/0/0/0, 12 0/0/0/11, 13 0/0/0/12, 14 0/10/0/0, 15 7/0/4/0, 16 6/1/3/2. Medium and hard come from 8 fixtures and 7 silhouettes; fixture 14 alone gives 10 of the 23 fixture mediums (CARD-517 F-001 still holds).
- [AC-2] Ablation, fixtures only (the silhouettes barely move under any variant except `outline`; the full tables print per source). Shares are of all 191 requests; "easy/made" is easy among the puzzles made; IoU is over made puzzles; "degen" counts made puzzles under 5% or over 95% ink (`sourcing.image.is_degenerate`), made but no longer a picture; "rescued" are today's failures that this variant makes, with their median IoU and how many pictures they come from.

  | variant | made | failed | easy/med/hard (of requests) | easy/made | IoU median / mean | degen | rescued (IoU, pictures) | made->failed | easy->harder / harder->easy (pictures made harder) |
  |---|---|---|---|---|---|---|---|---|---|
  | today | 122 | 36.1% | 44.5/12.0/7.3 | 69.7% | 0.953 / 0.926 | 1 | - | - | - |
  | dither_all | 118 | 38.2% | 31.9/13.1/16.8 | 51.7% | 0.851 / 0.824 | 0 | 0 | 4 | 29 / 6 (7) |
  | cut_62 | 112 | 41.4% | 31.4/14.1/13.1 | 53.6% | 0.866 / 0.837 | 1 | 1 (0.33, 1) | 11 | 26 / 6 (9) |
  | cut_37 | 142 | 25.7% | 55.5/8.9/9.9 | 74.6% | 0.860 / 0.813 | 1 | 20 (0.66, 4) | 0 | 5 / 24 (2) |
  | box_resize | 122 | 36.1% | 43.5/12.6/7.9 | 68.0% | 0.996 / 0.987 | 0 | 4 (0.96, 2) | 4 | 9 / 9 (6) |
  | despeckle | 170 | 11.0% | 64.9/15.7/8.4 | 72.9% | 0.914 / 0.767 | 31 | 48 (0.34, 7) | 0 | 1 / 12 (1) |
  | outline | 34 | 82.2% | 5.2/2.6/9.9 | 29.4% | 0.720 / 0.689 | 1 | 0 | 88 | 16 / 0 (8) |
  | fill_holes | 135 | 29.3% | 53.4/13.1/4.2 | 75.6% | 0.889 / 0.842 | 1 | 13 (0.62, 2) | 0 | 0 / 10 (0) |
  | nudges_15 | 138 | 27.7% | 48.2/13.6/10.5 | 66.7% | 0.945 / 0.874 | 2 | 16 (0.52, 7) | 0 | 1 / 0 (1) |
  | deadline_90 | 122 | 36.1% | 44.5/12.0/7.3 | 69.7% | 0.953 / 0.926 | 1 | 0 | 0 | 0 / 0 (0) |

  All 412 requests: today 86.9% easy of made, 16.7% failed. `outline` fails 87.1% (202 of the 221 silhouette requests fail). `deadline_90` changes no request: the 7 timeouts still fail, so they are not near misses. `despeckle`'s 48 rescues include 31 degenerate grids: on line art it deletes the dithered strokes and leaves a near-empty grid (renders: fixtures 07 and 13).
- [Private extra, aggregate only] The owner's folder (25 pictures, read only, `--only-image-dir`), 269 requests (31 repeats): today 249 made, 20 failed (7.4%), all failures on 4 pictures (11 of them conversions the blank-grid guard sent to dither); made 80.7/12.4/6.8 (CARD-517 read 81.4/12.6/6.1 on 247 graded). Medium+hard come from 11 pictures. Variants, easy-of-made / failed / IoU median / rescued (IoU): `dither_all` 74.0% / 10.0% / 0.900 / 2 (0.79); `cut_62` 73.6% / 8.6% / 0.895 / 4 (0.76), 11 pictures made harder; `cut_37` 89.5% / 4.5% / 0.906 / 8 (0.76); `despeckle` 87.0% / 0.0% / 0.961 / 20 (0.69), 11 degenerate; `fill_holes` 84.5% / 6.3% / 0.950 / 3 (0.80); `nudges_15` 78.8% / 3.7% / 0.972 / 10 (0.80). Today's IoU median there is 0.974.
- [AC-4] Renders: `~/Documents/nonogram-reviews/CARD-525/`, 34 sheets (all 17 fixtures at long side 20 and 30; a 30-long sheet whose extent the admin made from a smaller request shows that row) and `index.html` naming each sheet's picture and size and explaining the panels. Each sheet: the picture, then one panel per variant with tier and score or FAILED, extent, deciding stage and IoU; black = the puzzle made, red = the conversion that did not become one. The owner's folder: 25 sheets at long side 20 in `.../CARD-525/private/` (local only, its own index; nothing of it is in the repo).
- [Test] `tests/test_picture_pipeline_experiment.py::test_variants_run_through_the_admin_path_and_leave_the_pipeline_unchanged` (new, the one smoke test AC-5 allows): one fixture at long side 10 under `today`, `cut_37` and `despeckle`; asserts every request went through `admin.app._generate_image_puzzle` (spy count), the patched attributes are restored after the runs, `today` made a graded puzzle with IoU > 0.8, `cut_37` fills more cells than today, a reference grid scores IoU 1.0 against itself, both reports print, and the picture's file name does not reach the output.
  - Control 1: `applied` stops entering its patches (mechanism removed). Red: `assert 0.37727272727272726 > 0.37727272727272726` (cut_37's fill against today's).
  - Control 2: `run_picture` calls `orchestrator.generate` directly instead of `_generate_image_puzzle`. Red: `assert 0 == 3` (spy count).
  - Both restored by copy; `cmp` matched the saved file.
- [AC-5] Nothing under `src/` changed. Net collected count: 10694 before, 10695 after (+1).
- [Gate] Unarmed, `-rfs`: `tests/test_picture_pipeline_experiment.py`, `tests/test_measure_difficulty_cutoff.py` (the script whose builders are imported), `tests/test_card_062_abandon_retry.py` (the admin retry the script runs through), `tests/test_difficulty.py` (G-1), `tests/test_kanban_review_record.py`: 118 passed, 0 failed, 0 skipped. No DB tests are involved, so no armed run.
- [G-1, G-2] `classify` and the 90.0 cutoff are used as they are. The owner's folder was only read; no file name of it is in the repo, the card or the JSON.

**AC-3: recommendation for the owner.**

1. **Worth a card: catch line drawings before generating.** Every failure in the reproducible corpus is on 7 of 17 fixtures, and 6 of those 7 are outline drawings (dove, dove on a branch, two ducks, tiger, coral). They fail at 9-12 of their 11-12 requested sizes and used 317 s of the 331 s of generation time. On your own folder, 20 of 269 requests failed, all on 4 pictures. No setting fixes them well: thicker cut (`cut_37`) rescues 20 requests on 4 pictures but the grids keep only about two thirds of the picture's cells (IoU 0.66); filling enclosed areas (`fill_holes`) rescues 13 on 2 pictures (IoU 0.62) and turns them into silhouettes; more nudges rescue 16 (IoU 0.52); despeckling "rescues" 48, but 31 of those are near-empty grids. The card: recognise a line drawing up front and say so quickly ("this is a line drawing; use a filled silhouette, or fill it"), instead of trying up to three sizes for 30 s each. It changes no puzzle, so it costs nothing in recognisability. Whether to also offer `fill_holes` as an option is for you to judge on the renders (fixtures 05, 07, 12, 13).
2. **Not worth a card: making puzzles harder through the conversion.** Easy is set by the picture: easy grids have 1.4 to 2 times the run length of medium/hard ones (0.229 vs 0.167 of a line on fixtures, 0.299 vs 0.168 on your folder). Dither and a stricter cut do lower the easy share (fixtures: 69.7% -> 51.7% and 53.6%; your folder: 80.7% -> 74.0% and 73.6%), but by adding noise. The grids stray further from the picture (IoU median 0.95 -> 0.85-0.87 on fixtures, 0.97 -> 0.90 on yours), more requests fail (11 more with `cut_62` on fixtures), and the tiers reshuffle both ways (`cut_62`: 26 easy -> harder, 6 harder -> easy). The way to get more medium and hard puzzles is to choose pictures with thin parts and detail, not to change the pipeline.
3. **No change:** a longer deadline (90 s rescued nothing), the resize filter (4 rescued, 4 lost), outlines (87% fail).

Sample size: 17 real fixtures and your 25 pictures. The medium/hard counts rest on 8 fixtures (one gives 10 of the 23 mediums) and 11 of your pictures, so read the shares as directions, not precise figures.

[Review 1/3] Score: 7.5, two gating findings, not certified. Code, variants, corpus and today-row figures hold: 69 failures recomputed (62 abandoned, 7 deadline; dove1 12, dove3 12, tree1 12, duck1 11, tiger1 11, duck2 9, zebra1 2); cut_62, dither_all, cut_37, despeckle, fill_holes and nudges_15 rows recompute; every patch target is read at run time; today reproduces CARD-517 exactly; a small rerun differs in 0 rows; both test controls red; privacy clean. F-001 (Important): AC-3 item 2 ("not worth a card") does not follow. Every variant changes all requests, so its cost lands on already-medium/hard pictures; an easy-only fallback (keep today's grid unless easy, then take cut_62 or dither_all if non-easy at IoU >= 0.85), computed post hoc from the card's own JSONs, gives fixtures 69.7% -> 55.7% easy and the owner's folder 80.7% -> 69.5%, overall IoU median 0.939, no request lost. IoU is measured against a 50%-ink reference, which favours today by construction; dolphin1 at long side 30 is HARD 93.4 under cut_62 at IoU 0.91 and looks as recognisable. "Easy is set by the picture" is contradicted by the conversion alone moving fixtures 69.7% -> 51.7%. F-002 (Important): the line-art detector is not measured: "line drawing" is an eye label; the one measured signal covers 16 of 69 failures; ink share and stroke thickness put tsaplia1, zebra1, dolphin2 and bird2 among the line-art six, so a naive detector would refuse good pictures; the timing claim is overstated (62 abandoned failures median 0.45 s, 106.8 s in all; 210 of the 317 s is dove1's six timeouts); the owner's 4 failing pictures were not measured as line art. F-003 (medium): IoU's limits are not stated in AC-3, and it weights by area (today's heron loses legs and neck at IoU 0.90). F-004 (low): four mutants leave the test green (`_despeckle` identity, `_failure_stage` constant, `ink_iou` 1.0, solve counter frozen). F-005 (low): the owner's-folder today row (249 made, 201/31/17) differs from CARD-517's 247, 201/31/15, unexplained. F-006 (info): the dove1 fixture carries a stock-photo watermark.
