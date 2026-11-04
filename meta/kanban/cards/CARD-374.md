# CARD-374: `suite-timing.log` is six days behind and nothing fails when it falls behind — every gate since wave 64 is missing from "the format every wave reads"

**Status:** ready
**Priority:** P2
**Category:** enabler
**Estimate:** 1c (0.5d)
**Complexity:** standard
**Revision pending:** false
**Skill:** general-purpose
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** Found by CARD-363's fourth pass, 2026-11-04, while answering the owner's mid-run question about why the full suite takes what it takes. The answer came out of this log; finding it stale was a by-product.
**Idea:** —
**Wave:** —
**Created wave:** 77
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/test_suite_profile.py, meta/kanban/suite-timing.log
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## The gap

`meta/kanban/suite-timing.log` records every gate's wall clock and a per-test cost column.
`tests/test_suite_profile.py` calls it *"the format every wave reads"*.

**Its last dated row is 2026-10-29.** Every gate since **wave 64** is missing — including both of
wave 77's, which between them produced the figures that answered the owner's question. The file is
gitignored and pipeline-written, so no card's diff ever shows the omission.

**And nothing fails when it falls behind.** That is the defect, not the staleness: a log whose job is
to carry a series across waves has no control that fires when a wave does not append to it. It is the
same shape this board has now filed four waves running — an instrument whose silence and whose
correct operation are indistinguishable.

## Why it matters more than a tidy-up

The log is the **only** place the suite's cost series lives, and that series is load-bearing twice
over:

1. It is what makes the owner's standing *"wall-clock actuals are unusable"* ruling **measured**
   rather than asserted — one row shows **2114s of wall against pytest's 1560s**, i.e. 555s of the
   box busy elsewhere. Without new rows that evidence stops accumulating.
2. It is the evidence base for the cards that exist to cheapen the suite. The per-test cost has
   actually **improved** (131 ms mid-October → a 160–173 ms band late October → **144 ms** today),
   while the total grew with the test count (7082 → 10348, +46%). Nobody can see that from a single
   gate; it is only visible as a series.

The two families worth naming, because they are two-thirds of the run and already carded:
`tests/test_book_export_interior_cover.py` alone (~30%; CARD-287/292/299/300, and **CARD-300 is
parked**), and the browser class (646 Chromium tests at ~730 ms ≈ 474s, grown from 18 modules to 24).

## Acceptance criteria

- **AC-1** — A control fails when a wave closes without a row appended for its gate. Derive the
  expected set from the waves the board actually closed (ADR-0039/R2, defaulting to deny), not from a
  list of wave numbers.
- **AC-2** — A plant proves it: remove the newest row and assert the named red; restore from captured
  content. The control must also be shown green on a log that *is* current, so it cannot pass by
  always failing.
- **AC-3** — Decide, and state the reason, whether the log should be **tracked**. It is gitignored
  today, which is why no diff shows the gap — but `meta/review/*.yml` is gitignored for a reason
  (CARD-335: committed artefacts revive dead check refs, and this file is `.log`, not `.md`, so the
  resolver's `*.md` exclusion would not cover it). Measure the check-ref consequence before
  recommending tracking; do not assume either way.
- **AC-4** — Backfill is **out of scope and must be declared as such**, with the measured residue:
  name how many gates are missing and from which wave. Do not fabricate rows for runs nobody
  recorded — that is the history-fabrication G-2 forbids elsewhere on this board.
- **AC-5** — No `src/` change. Run with `-rEfs`; state the skip count as a function of whether
  `DATABASE_URL` is armed.

## Worktree notes

(none yet)
