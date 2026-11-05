# CARD-377: The full-suite lock has no notion of an ACTOR — identity is the worktree, which separates nothing once two agents share a checkout

**Status:** ready
**Priority:** P1
**Category:** enabler
**Estimate:** 1c (0.5d)
**Complexity:** standard
**Revision pending:** false
**Skill:** general-purpose
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** Measured 2026-11-05 during CARD-349's review, when two agents in one worktree were both waved through the lock and each misread the other's `holder:` line as its own.
**Idea:** —
**Wave:** —
**Created wave:** 78
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/full_suite_lock.py, meta/kanban/config.yml
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## The gap, measured

CARD-255 made the lock's identity the **worktree**, deliberately and for a good reason: the gate
scripts launch pytest as a child, so no pid can work. That decision is correct for the problem it
solved — two *worktrees* contending — and **separates nothing once two actors share one checkout.**

Measured in wave 78: an implementation round and a reviewer were both working in
`PythonProject4-card-349`. The lock's `worktree:` matched for both, so `verdict()` returned
`(True, None)` to each — **two processes in one worktree, both waved through.**

**And `holder:` is not an identity, it is a description of an activity.** The live lock read
`holder: CARD-349 review cycle 1 second reader (armed full suite, still running)`. Both agents
independently read a `holder:` line as the *other's* and both were wrong. A string a human wrote to
describe what a run is doing cannot be compared for equality against anything.

**Two instruments that resemble identity and are not** — both tried and both rejected during the
incident, and both belong in this card:

| candidate | why it fails |
|---|---|
| pid | the gate launches pytest as a child; CARD-255 ruled this out already |
| worktree | shared by every actor in one checkout — the defect above |
| `holder:` prose | a description, not an identity; misread in both directions |
| session scratchpad path | **shared by every agent in one session**, so it attributes a *session*, not an actor |

## Why P1

The lock exists to make a suite's verdict attributable. When it waves two actors through:

- a suite's result becomes a property of what a sibling actor happened to be doing — **which is
  CARD-244's hazard verbatim**, reappearing inside one worktree because CARD-244 isolated worktrees
  and the board now runs two actors per worktree
- the failure is **destructive**, not merely contended: see CARD-378
- and the resulting red carries a signature that gets pinned on the diff

## The EXIT trap is covered on every path except the one that matters

Measured 2026-11-05, with a matched control, during the same incident.

Every round and gate releases the lock via a shell `EXIT` trap. The control: a successful gate's
`gate.sh` uses the identical pattern, ran to completion, **and did release its lock.** So the
mechanism works on the path it was written for.

**It fails only on a hard stop** — the agent killed, the shell gone — and that is the one case no
run exercises. Worse, the two safety nets do not cover it either:

- **No age elapses.** The lock's `at:` is written at acquisition, so a lock stranded one minute in
  is one minute old. The stale-lock walk-past threshold is **six hours**, so it never fires on a
  fresh strand.
- **Nothing else notices.** `verdict()` returns a refusal to every foreign worktree for those six
  hours, with no process alive to finish or release.

So a stopped holder **blocks the board for six hours**, and the mechanism that would have saved it is
exercised by every successful gate and covered by none of them for the case that matters. That is the
same shape as everything else on this card: an instrument whose working path and whose broken path
are indistinguishable until the broken one is needed.

This happened tonight and was recovered by hand — the owner's orchestrator proved the lock stale by
resolving ownership **by cwd** (no live process owned the holder's worktree), kept a copy, and removed
it. That recovery is correct but it is manual, and it required knowing that `at:` is an acquisition
time rather than a heartbeat.

**Fold this into AC-4 rather than treating it as a footnote:** distinguishing a dead holder from a
live one is the same problem as distinguishing two live actors, and a heartbeat would answer both.

## Acceptance criteria

- **AC-1** — Two concurrent runs **in the same worktree** are distinguished. State what the identity
  is and why it is one, having first ruled out pid, worktree, prose and the session scratchpad with
  the reasons above.
- **AC-2** — The refusal path stays load-bearing and total; do not weaken it. Add the missing
  discrimination (ADR-0039/R2: derive the identity, default to deny — an actor it cannot identify is
  refused, not admitted).
- **AC-3** — A plant proves it: hold the lock as one actor and attempt a run as a second actor in the
  **same** worktree, and assert the named refusal. The matched control is the same actor re-entering,
  which must still be allowed, because that is what keeps every gate on the board running.
- **AC-4** — A holder that dies must still leave a walk-past-able stale lock. The module's docstring
  says a board that cannot run tests is worse than one that mis-attributes; preserve that, and state
  how a dead actor is distinguished from a live one **without** `pgrep` on an argv (an argv match is
  how a wait-loop sees itself — resolve ownership by **cwd**).
- **AC-5** — `NONOGRAM_IGNORE_FULL_SUITE_LOCK` must never be set and `NONOGRAM_FULL_SUITE_LOCK` never
  redirected, by this card's code or its tests.
- **AC-6** — Say whether the real fix is instead a **scheduling rule**: one actor per worktree, so the
  lock never has to tell them apart. That may well be the right answer and is cheaper; it is the
  orchestrator's call with the owner, and this card must present the measured cost of each.

## Worktree notes

(none yet)
