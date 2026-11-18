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

[Scope narrowed at implementation, 2026-11-18 — the card's body above is NOT what was built] "What to implement" and AC-1 say `## Guardrails` AND `## System contract`. Measured before writing the cell: `## System contract` is a projection of the architecture model's check refs, and of the test-shaped names the 20 open cards carry there, dozens have no definition under `tests/`. Reading them here would red main on day one. **Withdrawn (review cycle 1, F-002): I wrote that the architecture validator already reports these. It does not** — it resolves by text search and reads them as alive; `tests/test_check_ref_resolution.py` is the instrument that knows. Reviewer-measured on main: 92 bare test-shaped occurrences in open cards' `## System contract`, 49 without a definition (25 distinct names, on CARD-215, 216, 232, 249, 273, 274), 23 of the 25 still present in `meta/architecture/`. The cell reads `## Guardrails` only, and only `test:` / `check:` clauses there (a guardrail may spell a test-shaped name in prose precisely to say it resolves to nothing — CARD-279 does).
[AC-3, measured] Green on main as it stands: 7 clauses on open cards, 6 names judged, all resolve, 2 `review-lens` clauses, no finding. No open card is reddened.
[AC-4] +3 tests, as allowed.
[For the owner — dead names this cell does NOT see] Two names in open cards' `## System contract` are no longer model refs at all, so nothing reports them: `test_the_books_own_pages_carry_no_undeclared_round_mark` on CARD-215, CARD-232, CARD-273, CARD-274 (ADR-0036/R3 now names `test_the_books_own_vector_sheets_carry_no_round_mark`), and `PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30` on CARD-273, CARD-274 (retired from the model by CARD-317). Six placements on four cards; a re-decompose of those cards would refresh the projection. Reviewer-measured, not re-derived by me.
[Also unseen, by the card's own wording] A test named in a guardrail without a `test:` / `check:` marker: eight references on six open cards today (CARD-275, 279, 315, 340, 397, 479), all alive. None of CARD-397 or CARD-476..480 writes a marked clause, so the cell judges 6 of the 14 genuine references on the board.
[Review 1/3] Score: 7.0 (three gating findings). F-001 plants depended on which real cards were open; F-002 the validator claim above was false; F-003 thirteen mutants survived, most on routes with no control. Fix: plants on synthetic cards, the uncontrolled routes deleted, the claim withdrawn.
[Review 2/3] Score: 8.0 (two gating findings, both from fix 1). F-201: the walk over cards and clauses had no control (every plant one card, one clause). F-202: the rewritten marker regex lost the backtick exclusion, so prose like "leave the rule's `check:` alone" became a clause naming nothing. Both fixed with arms in the existing plant test; minors F-203 (part), F-204, F-205 fixed. Reviewer confirmed every figure copied from its cycle-1 measurement, bar a slip here (474..480 for 476..480), corrected.
