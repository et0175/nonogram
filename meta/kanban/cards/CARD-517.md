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
**Review score:** —
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
