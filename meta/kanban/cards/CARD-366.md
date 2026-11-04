# CARD-366: The metrics capture has refused on three consecutive waves for a missing registry, so no trend series exists for any signal

**Status:** ready
**Priority:** P2
**Category:** enabler
**Estimate:** 2c (1d)
**Complexity:** standard
**Revision pending:** false
**Skill:** general-purpose
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** Wave 73's retrospective recorded the refusal. Wave 74's recorded it again and said "two refusals is a decision being made by default". Wave 75's is the third, measured 2026-11-04 with the same message verbatim. Carded rather than noted a fourth time.
**Idea:** —
**Wave:** —
**Created wave:** 75
**Deferred waves:** 0
**Depends on:** —
**Touches:** meta/metrics/signal-definitions.yml
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## The refusal, verbatim and reproduced three times

```
forge:metrics — REFUSED: the signal definitions registry is missing:
meta/metrics/signal-definitions.yml. An absent registry is not an empty one — no signal has
a declared meaning, so none may be captured or exported (ADR-0032)
```

**The refusal is correct and should not be worked around.** ADR-0032's reasoning is that an
absent registry is not an empty one: a captured number whose meaning nobody declared is worse
than no number, because it will be compared against something later. The capture is **refusing
to create exactly the kind of figure this board keeps retracting.**

**The consequence, which is the card:** `meta/metrics/` holds **no snapshot for wave 73, 74 or
75**, so **no trend series exists for any signal** and none can be built retroactively — a
snapshot is a reading of a tree at a moment, and those moments are gone.

**Re-derive the refusal and the empty directory** before implementing; three readings of the
same message is still a dated reading.

## The decision this card owes, and it is not "write the file"

The registry declares, per signal: its **definition**, **unit**, **source field**, **denominator**
and **external-slice status**. **Writing a definition for a signal nobody has agreed to measure
is how a metric becomes a target**, so the question is *which* signals this board actually wants
on a series — and the honest answer may be very few.

**Start from what the board has already proved it reads**, because those are the only signals with
a demonstrated consumer:

| candidate | why it has a consumer | the trap it must declare |
|---|---|---|
| `accuracy_ratio` in **review cycles** | wave 74 exported 3-of-3 at 1.000, wave 75 a 0.500 — the first signal this board could read at all | its **denominator** is the estimate's `Nc` term; a card estimated in days yields **null, never 0.0** |
| final **review score** | every closed card carries one | a score is per **cycle**, and the card records only the last |
| **cycles used** | the retrospective's own input | **read it from the `Review score` text, not the marker** — the marker is absent on 152 of 279 closed cards (see CARD-363) |
| gate **suite result** | every merge records one | `passed + skipped + xfailed` against collected, or the figure is vacuous |
| **wall-clock** anything | — | **EXCLUDED by owner ruling**: the clock measures the queue, not the work. Must not appear in the registry at all. |

**That last row is the one to get right.** This board has a standing ruling that wall-clock actuals
are unusable for calibration, and every card since has substituted a derived size datum with the
exclusion stated in its own field. **A registry that declares a duration signal re-opens a
decision the owner already made.**

## What to implement

1. **Propose the signal set and its justification**, smallest first. A signal with no demonstrated
   consumer is not in the first cut; say what you left out and why.
2. **For each signal declare all five fields** the registry requires, and state the **null case
   explicitly** — `accuracy_ratio` over a days-estimated card is null, not zero, and a retro that
   folds it in as 0.0 reads "overestimated" for a card nobody estimated in cycles.
3. **Run the capture** and show it succeeds — exit 0 or 1 with the findings quoted, not exit 2.
   Then run it a second time and show it reports **exit 3, already captured**, which is the
   occupancy behaviour, not a failure.
4. **State plainly that waves 73–75 cannot be recovered**, so the series starts at wave 76 and the
   gap is a declared hole rather than an absence someone later reads as zero.

## Acceptance criteria

- **AC-1** *Given* the registry, *then* the capture **succeeds** for the current wave and the card
  quotes its exit code and any findings. A refusal is not a pass.
  (test: named by the implementation; state it)
- **AC-2** *Given* each declared signal, *then* all five required fields are present and its
  **null case** is stated — and a signal whose denominator can be absent says so.
  (test: named by the implementation; state it)
- **AC-3** *Given* the owner's wall-clock ruling, *then* **no duration signal is declared**, and
  the card states that the exclusion was deliberate rather than overlooked.
  (check: review-lens)
- **AC-4** *Given* a second capture of the same wave, *then* it reports **already captured**
  rather than overwriting — demonstrated, since the retrospective and the post-wave command both
  call it and whichever runs second must be harmless.
  (test: named by the implementation; state it)
- **AC-5** *Given* waves 73–75, *then* the absence of their snapshots is **recorded in the
  registry or beside it** as a declared gap, so a later reader cannot mistake missing for zero.
  (check: review-lens)

## Guardrails

- **G-1** — **Do not work around the refusal.** ADR-0032's reasoning holds: an undeclared signal is
  worse than no signal. A stub registry that declares everything loosely to make the capture pass
  is the defect this card exists to avoid.
- **G-2** — **No wall-clock signal.** The owner ruled those unusable for calibration; declaring one
  re-opens a settled decision.
- **G-3** — Do not declare a signal with no demonstrated consumer. The board's own retrospectives
  name which figures they read; that list is the authority.
- **G-4** — No new runtime dependency (ADR-0006/R1).
- **G-5** — Take no timing measurements and report no durations of your own.
- **G-6** — `/Users/omelnikova/MyProjects/forge_1` is **read-only**. The capture script lives
  there; if the fix belongs in it, that is a finding handed upstream.
- **G-7** — A full suite needs the board's lock (structured, worktree identity, **no pid**). Never
  set `NONOGRAM_IGNORE_FULL_SUITE_LOCK`, never redirect `NONOGRAM_FULL_SUITE_LOCK`.

## System contract

- ADR-0032 — an absent signal registry is not an empty one; nothing may be captured or exported
  without a declared meaning (check: review-lens)
- ADR-0039/R2 — a guard's set is derived from an authority the runtime can enumerate
  (check: review-lens)
- forge_1's ADR-0055 (upstream, not this board's — see CARD-367) — review cycles are the estimate unit (check: review-lens)
