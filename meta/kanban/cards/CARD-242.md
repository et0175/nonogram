# CARD-242: The check-log guard learns the taint step its sibling already has

**Status:** ready
**Priority:** P2
**Category:** tech-debt
**Complexity:** standard
**Estimate:** 0.5d
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** CARD-239's review cycle 2 (2026-10-17), finding F-201 — measured there, recorded as a bound by owner decision rather than fixed, so CARD-239 could land without a third cycle
**Idea:** —
**Wave:** —
**Depends on:** CARD-239 (it owns the guard and the recorded bound this card closes)
**Touches:** tests/test_guard_integrity.py, meta/review/CARD-239-claim-sweep.md
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

CARD-239's `_check_log_invocations` guards AC-6's promise that **no test invokes the deliberate
`--check-log` reader** — the one thing allowed to read the owner's live, gitignored timing log on
purpose. The guard works on every shape but one, and the exception is measured:

```python
_CMD = "python meta/profiling/rank_durations.py --check-log PATH"   # module scope
os.system(_CMD)                                                      # <- SURVIVES the guard
```

Inline, the same call is caught. Hoisted into a module-scope constant, it is exempt — because the
rule exempts **every** module-scope `ast.Assign` unconditionally on its value, on the stated grounds
that "a module-level binding is not an invocation". That is true of prose and false of a command
line that is then executed.

**The missing piece has a working precedent in the same codebase.** The sibling rule,
`_live_log_references` in `tests/test_suite_profile.py`, answers exactly this question with its
taint step (`_tainted_names` / `_string_values`): *does the bound name reach something that
executes it?* `_check_log_invocations` reimplemented the rule's shape and dropped that half. Give
it the taint step.

**Why the obvious narrowing is not the fix, measured in CARD-239's cycle 2.** Keying the exemption
on the value (`node.value == CHECK_LOG_OPTION`) does catch the hoist and keeps all seven positive
and four negative controls green — but it produces one new hit over the real tree:
`SANDBOX_CONTROL_MODULE` at `tests/test_suite_profile.py:4804`, a module-scope constant holding a
fabricated module's source that *mentions* the option as prose. A guard that cannot tell a quoted
example from an executed command is the same defect pointing the other way. The taint step is what
distinguishes them.

## Acceptance criteria

- **AC-1** (happy, the hoist dies): *Given* a module-scope constant holding a `--check-log` command
  line that is then passed to an executor (`os.system`, `subprocess.run(..., shell=True)`,
  `subprocess.run([...])`, `main([...])`), *then* the guard reports it — demonstrated by planting
  and reverting each form. (test: `TestCheckLog_TheDeliberateReader::*`)
- **AC-2** (guard, prose stays exempt): *Given* `SANDBOX_CONTROL_MODULE` and any other module-scope
  constant that merely *mentions* the option without reaching an executor, *then* the guard stays
  silent — and this is asserted over the **real tree**, not a fixture, so the card cannot pass by
  narrowing its own corpus.
- **AC-3** (guard, the exemption carries a control that can fail): *Given* each of the rule's
  exemptions, *then* there is a control for what it must **not absorb**, caught WITH the exemption
  removed and missed WITH it in place. This is CARD-239's own promoted rule and the reason this
  card exists; an exemption with a control only for what it exempts is what produced F-201.
- **AC-4** (guard, one rule, still): *Given* the three tests of that class, *then* each still calls
  `_check_log_invocations` and none re-derives the predicate — CARD-239's RC-1 pin
  (`test_the_invocation_rule_is_the_one_the_guard_runs`) stays green and is extended to the taint
  step. The defect it prevents — a control certifying a copy of the predicate — is what cycle 1
  found, and widening the rule must not reintroduce it.
- **AC-5** (guard, the bound is struck honestly): *Given* CARD-239's recorded bound for F-201 and
  its sweep row, *then* both are struck in the same diff that closes the route, and the sweep's
  equality goes **red** if the bound is struck without the route being closed.
- **AC-6** (edge, no new residue undeclared): *Given* the widened rule, *then* whatever it still
  cannot see is recorded as a measured miss with a control, in the `MEASURED_STRUCTURAL_MISSES`
  shape the sibling module uses.

## Guardrails

- G-1: **do not write, move, rename or normalise `meta/kanban/suite-timing.log`.** Standing owner
  decision from CARD-238. Note CARD-239's near-miss: a control carrying the literal log path was
  itself reported by the *other* module's path guard. Spell control destinations generically.
- G-2: coverage up, not down. Nothing CARD-239 left may be removed.
- G-3: do not weaken the sibling rule or the first module to make this one fit. If the taint step
  needs sharing, the project's convention is to reimplement natively rather than import across —
  see CLAUDE.md and `solver/propagate.py`'s `mask_runs` precedent — and the two guard modules are
  deliberately independent.
- G-4: no `src/**` change; no new runtime dependency (ADR-0006/R1).
- G-5: do not re-measure or regenerate any `meta/profiling` artefact.

## System contract

- ADR-0006/R1 — runtime dependencies are exactly stdlib + Pillow + NumPy (check:
  `tests/test_export_pdf.py::test_the_dependency_baseline_is_still_closed`)

## Architecture context

- **FR:** — (test-integrity card; its done-ness is the ACs above)
- **Components:** — (tests only)
- **Trace:** not updated by this card.

## Worktree notes

- [Why this is a card and not CARD-239's third cycle] Owner decision, 2026-10-17. CARD-239's cycle 2
  closed two findings by mechanism and minted two more in the same family, and its reviewer's
  objection to a third cycle was that it would be "the loop asked to audit the exemptions it just
  wrote" — which is how CARD-238 reached five cycles and 2.7 days. F-202 was a one-liner whose
  control came free and was fixed there; this one needs the taint step, which is real work.
- [Read before starting] CARD-239's cycle-2 report (`meta/review/*CARD-239-cycle2.yml`) has the
  measurements: M2 (hoisted) SURVIVED at 854 passed, M3 (inline) KILLED, and the `SANDBOX_CONTROL_MODULE`
  collision that rules out the naive narrowing. None of it needs re-deriving.
- [The rule this card is an application of] **An exemption is a claim, and it needs the same control
  a set member needs — caught WITH it, missed WITHOUT it, and the residue recorded as a bound.**
  CARD-239 produced that rule by violating it twice. This card is the first work done knowing it.
