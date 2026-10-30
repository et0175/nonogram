# CARD-321: The hint ladder's answer line is truncated on a phone and pushes the board off a small laptop — the two widths CARD-269 never claimed

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** CARD-269 review cycle 2, findings F-12 and F-13, both should-fix and both explicitly deferred by the reviewer — *"F-12 and F-13 are the next card's, not another cycle."* Measured, not predicted; figures below are the reviewer's and must be re-derived.
**Idea:** —
**Wave:** —
**Created wave:** 68
**Deferred waves:** 0
**Depends on:** CARD-269
**Touches:** src/nonogram/admin/static/admin.css, tests/test_puzzle_solver_phone.py, tests/test_puzzle_solver_hint.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

CARD-269 put the hint ladder's answer on the page as a visible sentence, because rung 2 had been
**measured to change nothing a sighted player could see**. It did that well at 1280 and 1440, where
its review certified it at 8.5. **It did not claim any other width, and at two of them the fix does
not hold.**

**F-12 — the phone is inside the ellipsis band.** The line gets **358 px** at 390 px wide. Every
rung-2 sentence measures **508–594 px**, and so does the exhausted board's rung-3 reveal. **All of
them are ellipsised on a phone.** Only rung 1, the exhausted 1–2 sentence (350.984 px, with 7 px to
spare) and Check's answer fit. So on a phone the ladder's **explanation rung — the half of the
card's title that says "explain the deduction" — is truncated**, which is a weaker form of the very
defect CARD-269 was cut to remove.

**F-13 — the narrow-width rule pushes the board off a small laptop.** CARD-269 gave the line its own
row below about 820 px, at a constant **+38.328 px**. In a **900 px-tall viewport between roughly
700 and 820 px wide**, that puts the board's bottom at **917.297 px against 878.969 px without it** —
**the board leaves the viewport.** That is **the exact failure mode CARD-269 rejected the
toolbar-to-board placement for**, reappearing one width band over, and it was checked at 390×844
only.

**Neither is a defect in what CARD-269 shipped at the widths it measured.** Both are player-facing
at widths it did not.

## What to implement

**The design is not pre-decided and should not be.** Three shapes are plausible and the card should
measure before choosing:

1. **Let the line wrap to two rows on narrow widths** rather than ellipsising, and reclaim the
   vertical cost elsewhere.
2. **Shorten the sentences for narrow widths** — a second, terser string per rung. This changes
   declared copy, so it is an **owner decision**, not an implementation choice.
3. **Move the line on narrow widths** to a place with vertical room, which means finding room that
   CARD-269 measured as not existing at 1280×720 — re-measure at the narrow widths rather than
   assuming the same answer.

**Read CARD-269's CSS comment before designing anything.** It carries the full derivation of why the
toolbar-to-board gap was rejected, both rejected placements, and the note that a future card wanting
room there should **fix the drag helper — measure the whole pointer path once, before the press —
rather than buy the room from that margin.** That note was written for this card.

## Acceptance criteria

- **AC-1** (the phone is not truncated): *Given* the player page at 390 px, *when* each rung is
  pressed on a deducible board and on an exhausted one, *then* the answer is **fully readable** —
  asserted by `scrollWidth ≤ clientWidth` on the element, not by eye.
- **AC-2** (the board stays in the viewport): *Given* viewports across **390, 700, 760, 820, 1024,
  1280 and 1440 px at 844 and 900 px tall**, *then* the board's bottom edge is inside the viewport
  at every one. **The band 700–820 × 900 is the measured failure and must be a named case.**
- **AC-3** (the 1280 and 1440 layouts do not move): *Given* the branch, *then* every toolbar, head,
  counter and board figure CARD-269's review certified is **identical** — line empty, line full, and
  with the line removed. **The owner accepted that 1280 layout on real captures; it must not move.**
- **AC-4** (the property CARD-269 established still holds at every width): *Given* each width in
  AC-2, *then* **every press still changes something a sighted player can see** — reusing CARD-269's
  screenshot instrument, whose separation is already derived (noise ≤ 2 levels, smallest real change
  20).
- **AC-5** (captures at the widths that had none): *Given* the branch, *then* captures exist under
  `~/Documents/nonogram-reviews/CARD-321/` for **a phone, a 760 px viewport, the exhausted board and
  Check** — the four cases CARD-269's captures do not cover. **Standing rule: a UI change needs a
  rendered eyeball.**

## Engineering constraints

- **EC(the line never lies by truncation):** across every width in AC-2 and every rung, the element's
  rendered text is either the whole sentence or an explicitly designed short form — **never a
  silently ellipsised long one**, with a minimum case count asserted inside the test.

## Guardrails

- **G-1: do not change the announce region.** It is `role="status"`, 1×1 and clipped, and CARD-269's
  review confirmed a sighted screen-reader user can still reach the sentence through it. Changing the
  shipped live region is a separate decision.
- **G-2: do not recolour the tint.** Its 1.1526:1 against WCAG's 3:1 is a **declared, owner-accepted
  residual** on CARD-269, acceptable because the sentence carries the meaning. If this card makes the
  sentence unreliable at some width, **that argument weakens and the card must say so** rather than
  quietly recolouring.
- **G-3: no test deleted, renamed, skipped or merged** — `parametrize` ids included.
- **G-4: do not edit `tests/test_puzzle_solver_marking.py`** beyond what a copy change strictly
  requires; CARD-269 fenced it for a reason and its pinned usage paragraph is exact-equality.

## System contract (subset — the pipeline re-derives the full list at dispatch)

- ADR-0039/R1 — a claim needs a control that CAN fail (check: review-lens)
- ADR-0039/R2 — a guard's set is derived from an enumerable authority (check: review-lens)
- ADR-0039/R4 — a figure's instrument is part of the figure (check: **now executing**, CARD-304)
- WCAG 2.1 SC 1.4.11 — non-text contrast, 3:1 (the tint's shortfall is declared on CARD-269)

## Architecture context

- **FR:** FR-044
- **Components:** the player page's CSS and the hint ladder's view layer; no domain change
- **Trace:** CARD-269's AC-335 is already recorded as owed an extension in
  `meta/architecture/inputs/raw-requirements.md`; this card's widths may extend it further.

## Worktree notes

- **CARD-269's screenshot instrument is reusable and already proved in both directions** — same state
  twice is byte-identical on all three regions over six repeats; noise ≤ 2 levels; smallest real
  change 20. **Reuse it rather than building a second one**, and re-prove it at the new widths.
- **The reviewer found the 4–20 level gap is reachable exactly one way** — a 4-level tint change over
  ~10,500 board pixels reads indistinguishable, 5 is caught. That is a bound on **magnitude, not
  area**, documented in the instrument's docstring. If this card changes the tint's area, re-check it.
- **Two figures CARD-269's record carries are not reproducible** and should not be inherited: its
  "18-file set / 750 collected" (never named its files; the reviewer's derivations collect 845 and
  911), and its "6 of 73,500 px at 1 level" toolbar reading (the reviewer got 16 at 2). Derive your
  own set and name it.
