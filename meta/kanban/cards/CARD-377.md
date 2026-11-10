# CARD-377: A second actor in one worktree is waved through SILENTLY, and a hard-stopped holder strands the lock for six hours

**Status:** done
**Priority:** P2
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
**Touches:** tests/full_suite_lock.py, tests/test_full_suite_lock.py
**Review score:** n/a — closed on the owner's 2026-11-10 enabler triage; no review of its own.
**Started:** 2026-11-10
**Closed:** 2026-11-10
**Actual:** about two hours, with CARD-377
**Merge commit:** —
**Blocked by:** —

## RE-SCOPED 2026-11-05, and most of the original card is CLOSED BY CONVENTION

This card was cut P1 as *"the lock has no notion of an actor — identity is the worktree, which
separates nothing once two agents share a checkout."* **The owner then closed that by convention**
— instructions for card work route through the orchestrator, therefore one actor per worktree — and
a collision became impossible by construction rather than by discipline. **CARD-378 is retired into
this card** for the same reason: two actors in one worktree derived the same database and dropped
each other's schema, and with one actor there are no two.

So the identity scheme the original card asked for **is not needed**, and building one would have
been the expensive answer to a question the convention had already settled. Measured and withdrawn
rather than carried.

**What the convention does NOT close is two things, and they are small.**

## Residue 1 — the convention has no control, because the pass-through is silent

`verdict()`'s same-worktree branch returns **`(True, None)`** — admitted, and `said` is `None`, so
**nothing is printed at all.** That branch is **correct and must stay**: its own comment says the gate
writes the lock and then runs the suite in the worktree it named, so refusing there *"would stop
every gate on the board."*

But because it is silent, a second actor entering one worktree is both **permitted and invisible**.
The convention therefore lives entirely in the dispatcher's discipline, with nothing in the tree that
fails when it is broken — the same shape as the lock being mandatory on refusal and advisory on
acquisition (see [[full-suite-lock-is-advisory]], now CARD-370's subject).

**The fix is an announcement, not a refusal.** The channel already exists: `report_line()` /
`pytest_terminal_summary`, which is where the refusal and the stale-lock walk-past already surface,
and which survives `addopts = "-q"`. A same-worktree acquisition that is **not** this process's own
says so, once, and the convention acquires a control that can fail.

## Residue 2 — a hard-stopped holder strands the lock for six hours

**Independent of the actor convention**: one actor dying hard does this on its own.

- The `EXIT` trap releases the lock on every path a successful gate takes — verified with a matched
  control, a real gate's `gate.sh` using the identical pattern released correctly.
- It fails only on a **hard stop**, which is the one case no run exercises.
- `at:` is written at **acquisition**, not as a heartbeat, so a lock stranded one minute in is one
  minute old. `STALE_SECONDS = 21600.0` — six hours, and the module's own comment says the number is
  *"bounded from below by the longest lock-hold this board has"*, so it cannot simply be lowered.
- Result: **every other worktree is refused for six hours** with no process alive to finish or
  release.

This happened on 2026-11-05 and was recovered **by hand**: the orchestrator proved the lock stale by
resolving ownership **by cwd** (no live process owned the holder's worktree), kept a copy, and removed
it. That recovery is correct but manual, and it required knowing that `at:` is an acquisition time
rather than a heartbeat.

## Acceptance criteria

- **AC-1** — A same-worktree acquisition that is not this process's own **announces itself** through
  the existing `report_line()` / `pytest_terminal_summary` channel. It still returns allowed — do not
  refuse, or every gate on the board stops.
- **AC-2** — A plant proves AC-1 can fail: write a lock naming this worktree from a different
  process and assert the announcement appears in the terminal summary; the matched control is this
  process's **own** lock, which must stay silent, because a channel that always speaks is no signal.
- **AC-3** — A stranded lock is recoverable without waiting six hours. State the mechanism and its
  reason. **A heartbeat is the candidate worth pricing** because it answers both residues with one
  change: it distinguishes a dead holder from a live one *and* a live second actor from a stale first.
  **Do not lower `STALE_SECONDS`** — the module says it is bounded below by the longest legitimate
  hold, and this board's holds run past 25 minutes.
- **AC-4** — The refusal path and the stale walk-past both keep working, each with a control. A board
  that cannot run tests is worse than one that mis-attributes, which is the module's own stated
  trade.
- **AC-5** — `NONOGRAM_IGNORE_FULL_SUITE_LOCK` must never be set and `NONOGRAM_FULL_SUITE_LOCK` never
  redirected, by this card's code or its tests.

## Not in this card, deliberately

The original carried four non-lock instances of *content detached from what would let a reader weigh
it* — `holder:` prose read as an identity, a shared scratchpad path attributing a session, a claim
arriving without its author, and a summary arriving without its condition. **Those are about claims,
not locks**, and they are recorded in the board's standing brief rules where a future round will meet
them. Keeping them here would have made this card a theme rather than a change.

## Worktree notes

(none yet)

## Closed 2026-11-10 — owner's enabler triage, done together with CARD-370

- **AC-1/AC-2.** A lock in this worktree that carries a token this process did not inherit is announced ("another run in this worktree holds the lock") and the run is still allowed. The control is the holder's own child, which inherits the token through `NONOGRAM_FULL_SUITE_LOCK_OWNER` and stays silent. A gate script's lock (no token) in its own tree stays silent as before.
- **AC-3.** A lock written by a full suite carries `pid` and `host`, and is touched every 60 s. On the writing host a pid that answers to no process makes it stale at once. From another host a heartbeat silent for 900 s does. A live pid outranks a starved heartbeat. A full suite that walks past a stale lock takes it over. `STALE_SECONDS` is unchanged and still governs the gate scripts' locks, which carry neither field.
- **AC-4.** The refusal and the six-hour walk-past keep their existing tests. There is a new real-run refusal by a live foreign holder too.
- **AC-5.** Neither variable is set or redirected by the new code or tests.
