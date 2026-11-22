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
**Review score:** —
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
