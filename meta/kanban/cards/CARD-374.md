# CARD-374: `suite-timing.log` is six days behind and nothing fails when it falls behind — every gate since wave 64 is missing from "the format every wave reads"

**Status:** skipped
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
**Review score:** n/a — **RETIRED** 2026-11-05 under the owner's cut bar; replaced by a standing brief rule, which is the whole fix.
**Started:** —
**Closed:** 2026-11-05
**Actual:** none as a card — one brief rule, no code. Against the 79-line, five-AC card it replaces.
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

## RETIRED 2026-11-05 — the thing that stopped was a habit, not a writer

**I cut this card on a false premise about the mechanism.** It said every gate since wave 64 was
"missing from the log", implying something had stopped appending. Measured:

- **Nothing in this repository writes `suite-timing.log`.** `meta/profiling/rank_durations.py` only
  *parses* it and `tests/test_suite_profile.py` only *reads* it. The rows are appended **by hand**,
  by whoever runs a gate — visible in the rows themselves, which carry prose.
- `forge_1/forge/ci/suite_cost_ratchet.py` calls it *"THE SOURCE OF TRUTH THE GATE READS"*, and
  **forge_1 is read-only**, so this board cannot make the tool write it either.
- Last row: **wave 64**, 2026-10-29. **Fourteen** waves have run gates since.

So there is no writer to repair. **The fix is one line per gate**, and it is now a standing brief
rule rather than a card: a merge gate appends its row in the format the existing rows keep.

**AC-3's decision is settled by measurement, recorded here so nobody re-opens it: DO NOT track the
file.** It is `*.log`, gitignored at `.gitignore:61`. The check-ref resolver excludes only `*.md`, so
a tracked `.log` sits **inside** the search domain — and this file carries **23** distinct `test_*`
tokens and **7** node-id-like `::` tokens, each of which a word-bounded search over tracked files
would resolve as **alive**. Tracking it would be the largest single instance of CARD-335's measured
revival mechanism on this board.

**AC-4 is also answered rather than deferred:** backfill is impossible, not merely out of scope. No
record exists of the un-appended gates' wall clocks, and fabricating rows is the history-fabrication
this board forbids elsewhere. The series simply has a fourteen-wave hole, and the honest thing is to
resume rather than to invent.

**Why a guard is not the fix here, stated so the omission is deliberate:** the file is gitignored, so
a fresh checkout has none at all, and a guard asserting on an absent optional file is mostly
machinery for handling its absence. If the habit does not stick, a guard becomes worth its cost —
and that is a decision for whoever notices, not a card held open now.

**What the series is for**, so the rule does not read as cargo: it is what makes the owner's
*"wall-clock actuals are unusable"* ruling **measured** rather than asserted — one row shows **2114s**
of wall against pytest's **1560s**, i.e. 555s of the box busy elsewhere. And it is the only way to
see that per-test cost has **improved** (131 ms mid-October → **144 ms** now) while the total grew
with the test count (7082 → **10404**). No single gate can show that; only a series can.
