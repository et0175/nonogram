# CARD-476: A guardrail on an open card names a test that exists, or the suite says which one does not

**Status:** in_progress
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/476-open-card-guardrail-refs
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-476
**Source:** roadmap rescore 2026-11-18, wave 1 (IDEA-110, WSJF 12.31); premise re-read against main on 2026-11-18. Origin: wave 37 retrospective: a fabricated test name reached four cards in two waves; resolved by hand since wave 43.
**Idea:** IDEA-110
**Wave:** 80
**Created wave:** 80
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/test_kanban_review_record.py
**UI surface:** none
**Review score:** —
**Started:** 2026-11-18T11:15Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

A card's `## Guardrails` and `## System contract` lines say "this existing behaviour is held by test X". A review scores the diff, so it cannot notice that X resolves to nothing, and a guardrail with a dead name protects nothing. The architecture model's refs are already resolved by `tests/test_check_ref_resolution.py`; the cards' are resolved only when the orchestrator remembers.

## What to implement

In the existing card census (`tests/test_kanban_review_record.py`, which already reads every `meta/kanban/cards/CARD-*.md`): for every card whose status is not `done`, `skipped` or `reverted`, take each backticked name given as `test:` or `check:` under `## Guardrails` and `## System contract`, and resolve it to a `def` or `class` line under `tests/` by `ast`, not by text search. A name that resolves nowhere fails with the card and the name.

## Acceptance criteria

* **AC-1**: a planted open card whose guardrail names a test that does not exist fails the cell, and the message carries the card id and the name.
* **AC-2**: a name that appears only in prose (a comment, a review YAML, another card) does not count as resolved — one planted control.
* **AC-3**: the cell is green on main as it stands, or the card's notes list every open card it reds and each dead name, for the owner to rule on — the card does not edit other cards.
* **AC-4**: net test count: at most +3 (the cell and its two plants).

## Guardrails

* **G-1**: acceptance-criteria refs are out of scope: an open card's AC legitimately names a test the card will write.
* **G-2**: closed cards are out of scope: their tests may have been retired since.
* **G-3**: no edit to `meta/kanban/cards/**` from the worktree (the branch copy is frozen; a dead name found is reported, not repaired here).

## Worktree notes

[Scope narrowed at implementation, 2026-11-18 — the card's body above is NOT what was built] "What to implement" and AC-1 say `## Guardrails` AND `## System contract`. Measured before writing the cell: `## System contract` is a projection of the architecture model's check refs, and of the test-shaped names the 20 open cards carry there, dozens have no definition under `tests/` — the model's own dead refs, already reported by the architecture validator and owned by IDEA-004. Reading them here would re-count that list under a second name and red main on day one. The cell reads `## Guardrails` only, and only `test:` / `check:` clauses there (a guardrail may spell a test-shaped name in prose precisely to say it resolves to nothing — CARD-279 does).
[AC-3, measured] Green on main as it stands: 7 clauses on open cards, 6 names judged, all resolve, 2 `review-lens` clauses, no finding. No open card is reddened.
[AC-4] +3 tests, as allowed.
