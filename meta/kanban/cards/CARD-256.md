# CARD-256: The lock guard's path-redirect variable gets the same control and the same loudness as its override

**Status:** ready
**Priority:** P1
**Category:** ops
**Complexity:** trivial
**Estimate:** 0.25d
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** CARD-255 review cycle 3, F-203 — the certifier's answer to "is there any failure mode that would be *silent*?"
**Idea:** —
**Wave:** 50 (queued)
**Depends on:** CARD-255 (merged)
**Touches:** tests/test_full_suite_lock.py, tests/full_suite_lock.py, tests/README.md
**Review score:** —
**Started:** — · **Closed:** — · **Actual:** — · **Merge commit:** —
**Blocked by:** —

## Why — one measured hole, and it is the silent kind

CARD-255's guard has **two** environment switches. `NONOGRAM_IGNORE_FULL_SUITE_LOCK` walks past a
lock **loudly**, by design, and an in-tree setter of it is caught by a tree-wide scan with its own
control. `NONOGRAM_FULL_SUITE_LOCK` redirects the guard at a different path — and does it in silence.

Probed by the certifier, not reasoned about: pointed at a path holding no lock, `386 passed`,
`current_verdict() == (True, None)`, `report_line() == None`. **A run allowed that should have been
refused, printing nothing at all.** And the scan greps the override variable only, so an in-tree
setter of the path variable sits outside the control that exists for the other one.

The route is concrete, and it is the same file the whole family keeps circling:
`scripts/run_admin_tests.sh` is a pytest wrapper with a block of `export`s. CARD-255 cycle 2's M-H
proved the scan reds when the **override** is exported there. Append
`export NONOGRAM_FULL_SUITE_LOCK=/tmp/none` instead and the scan stays **green**. The guard's own
docstring asserts the condition that makes it safe — *"Unset — which is every real run, gate or
agent"* — and **nothing holds it**.

This card exists because that sentence should be a test, not a hope, in a guard that now runs in
front of every pytest invocation on this board.

## What to implement

1. **Give the path variable the same scan control.** The remedy is two tokens —
   `["git","grep","-l","-e",guard.OVERRIDE,"-e",guard.LOCK_PATH_VAR]` — and the certifier verified it
   adds no hit outside the four files already exempted. Extend the existing control rather than
   writing a second one; the exemption set and its shape constraint stay as CARD-255 left them.
2. **Make the redirection announce itself.** The guard already has `_ANNOUNCEMENT` and
   `pytest_terminal_summary`. A run reading its lock from somewhere other than the board's own path
   should say so, for the same reason the override does: a switch that changes the guard's verdict in
   silence is indistinguishable from the guard not working.
3. **Close F-202's surviving mutant.** `M-M` (the `startswith` half of the prose exemption deleted)
   **survived 36/36** — under it the exemption becomes "any `.md`/`.yml` anywhere", which would absorb
   `ci/forge-ci.yml` and `.github/workflows/*.yml`. It cannot alter the guard's runtime verdict (it
   widens a *test's* exemption), which is why it is not CARD-255's problem — but one assertion closes
   it.
4. **Narrow four sentences CARD-255 left owed** (ADR-0039/R1's own remedy, carried forward):
   `test_full_suite_lock.py:464` *"prose, never anything a shell can run"* and `:555` *"an executable
   under an exempted prefix is still an offender"* — both false as written, because the clause bounds
   the **extension**, and an executable `.md`/`.yml` gets through (probed live at mode 100755);
   `full_suite_lock.py:104-106` *"Unset — which is every real run, gate or agent"* — unverified until
   item 1 lands; and `:735` *"five of the **six** names below"* — the set now holds **seven**, so the
   independent reach is two, which the same docstring already says.

**Optional, if it is cheap:** the mode-bit axis can be closed outright — `git ls-files -s` over both
prefixes returns 542 entries, all `100644`, so an equality on the mode is available and would make
"nothing a shell can run" true rather than narrowed.

## Acceptance criteria

- **AC-1** *Given* an in-tree file exporting `NONOGRAM_FULL_SUITE_LOCK`, *when* the tree scan runs,
  *then* it is reported as an offender, naming the file. (test: the extended scan control)
- **AC-2** (the control) *Given* the second `-e` removed, *then* AC-1's test fails. A scan that cannot
  red on the variable it claims to cover is this board's recurring defect.
- **AC-3** *Given* a run whose lock path is redirected, *then* the run says so in its terminal
  summary; *given* an ordinary run, *then* it says nothing. (test: both halves, since "says nothing"
  is the half that rots)
- **AC-4** *Given* the `startswith` half of the prose exemption deleted, *then* a test reds — M-M
  must no longer survive.
- **AC-5** (guard) *Given* this change, *then* the skip profile is unchanged and a tree with no lock
  behaves exactly as before, both re-proved as CARD-255 proved them.

## Guardrails

- G-1: The guard's **verdict** logic is not touched beyond the announcement — a run that was refused
  before is refused after, and a run that was allowed is allowed. Prove it the way CARD-255's cycle 3
  did: the module's code objects compile to byte-identical `co_code` apart from the announcement path.
- G-2: The abort never becomes a skip; the guard names no skip API.
- G-3: `nonogram_poc` is never created, dropped, connected to or truncated;
  `_refuse_unless_test_database` is neither widened nor bypassed.
- G-4: No new runtime dependency (ADR-0006/R1); stdlib only.
- G-5: **Never create, modify or delete the board's real lock.** Every lock the tests make lives in a
  temp path behind the very variable this card is about.

## Worktree notes

- **[Do not take timing measurements]** other cards may share this machine.
- **[The trap]** This card's own subject is a switch that is silent. The obvious test redirects the
  path, finds no lock, and asserts the run proceeds — which is the *current* behaviour and would pass
  before and after. The test that matters asserts the run **says** it was redirected, and the mutant
  is deleting the announcement, not the redirection.
- **[System contract]** to be derived at dispatch under `meta/kanban/curation.md`. Note the known
  trap: read the ADR files **case-insensitively** for the reach-limit idiom, or ADR-0039 silently
  drops out of the contract — and this card is entirely about ADR-0039/R1 and R3.
