# CARD-483: A two-up page stops reserving the corner folio it no longer draws, if that is proved

**Status:** review
**Priority:** P2
**Category:** feature
**Estimate:** 2c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/483-two-up-folio-reserve
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-483
**Source:** roadmap rescore 2026-11-18, wave 2 (IDEA-176, WSJF 1.23); premise re-read against main on 2026-11-19.
**Idea:** IDEA-176
**Wave:** 81
**Created wave:** 81
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/book_pdf_generator.py, tests/test_book_pdf_two_up.py, tests/test_layout_two_up.py, tests/property/test_book_pairing.py
**UI surface:** printed interior (two-up pages)
**Review score:** 9.0 (cycle 3/3 - CERTIFIED)
**Started:** 2026-11-19T08:49Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

`_folio_reserve_px` takes 108 px off a two-up pair's lower slot for a corner folio. Since CARD-248 a two-up page draws its folio centred in the footer strip. The corner is used only when `content_bottom` reaches below the footer rule (`_draw_page_frame`'s omission branch). If that branch cannot be reached on a two-up page, the reserve refuses pairs for nothing: 18 pairs at the time of writing (2026-10-18), **before CARD-392's footer change, so the figure is stale**.

## What to implement

1. **Measure first.** Re-run the equal-pair sweep on main (find it from `tests/property/test_book_pairing.py` and `tests/test_book_pdf_two_up.py`) and count the pairs refused only because of the reserve. Record the figure in the card notes.
2. **Stop rule:** if the count is 0, record it, change no code, and close the card as no change.
3. Otherwise, prove the omission branch unreachable for a two-up page, with a control that fails when it becomes reachable (ADR-0039/R3). Include the F-4 one-pixel round-trip residue from CARD-248. Only then drop the reserve for two-up pages.

## Acceptance criteria

* **AC-1**: the re-measured refusal count, with the sweep's own command, is in the notes.
* **AC-2**: if code changed: a test proves a two-up page never takes the corner-folio branch across the sweep, and a planted reachable case reds it.
* **AC-3**: if code changed: the pairs the reserve was refusing now pair, and no single-page layout moves (pin both).
* **AC-4**: renders of three recovered pairs (including the 25 × 10 if it is among them) in `~/Documents/nonogram-reviews/CARD-483` for the owner's visual check after merge.

## Guardrails

* **G-1**: single-page layouts keep the reserve; the corner folio stays where the footer is omitted.
* **G-2**: the vector interior (ADR-0042) and the raster path must agree; change both or neither.

## Worktree notes

—
