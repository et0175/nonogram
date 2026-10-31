# CARD-335: Committed measurement artefacts revive dead check refs, and the resolver's own docstring says why

**Status:** ready
**Priority:** P1
**Category:** tech-debt
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** general-purpose
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** CARD-316's fix round 1, 2026-10-31, F-012. It measured that a blanket `scratchpad/**` glob reds its own G-2 guard immediately on three tracked files from an earlier card, named them by site, and routed the hazard rather than fixing it by reddening another card's artefacts — the right call for that card's scope. Re-measured at the decompose station, where the population turned out to be larger than three. See below.
**Idea:** —
**Wave:** —
**Created wave:** 72
**Deferred waves:** 0
**Depends on:** —
**Touches:** scratchpad/card309/, scratchpad/card318fix/, scratchpad/card330/, .gitignore, tests/test_check_ref_resolution.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

The validator of record resolves a check ref by a **text search over tracked files**:

```
git grep -lw <name> -- . :(exclude)meta/architecture :(exclude)*.md
```

`validators/utils.py:237`'s own docstring states the reason the excludes exist, and it
is exactly the failure this card is about:

> `excludes` are git pathspecs that MUST drop the architecture model and docs from the
> search — otherwise the matrix self-validates: trace.yml/requirements.yml name the
> test, so a renamed-away (dead) test still "exists" inside the very file that
> references it and the check silently passes. **Scoping to source files is what makes
> a dead link detectable.**

`scratchpad/` is not in that exclude list. So a dead ref spelled as a whole token in
any **tracked** file under `scratchpad/` resolves, the ref reads as alive, and its
dead-ref warning disappears. The damage is silent and it is in the direction that
hides work: a ref nobody has written reads as written.

This is not hypothetical on this board. CARD-318's merge gate went red on precisely
this — "members resolved from outside `meta/`" — after 55 scratchpad files including
raw validator dumps were committed. Those were untracked again, but **not all of
them**, and three later cards have since committed their own measurement scripts.

### Measured 2026-10-31 by the orchestrator

19 files are tracked under `scratchpad/`. Candidate declared refs were derived from
the two authorities rather than typed (a regex over `requirements.yml` +
`trace.yml`, names longer than 12 characters, 541 candidates — a loose over-set, so
these counts are an **upper bound on hits and a lower bound on nothing**). Whole-token
matches, by file:

| file | hits |
|---|---|
| `scratchpad/card309/census-converted.txt` | **41** |
| `scratchpad/card309/impact.txt` | 3 |
| `scratchpad/card318fix/y1_control.py` | 3 |
| `scratchpad/card318fix/final_mutants.py` | 2 |
| `scratchpad/card318fix/y_discrimination.py` | 2 |
| `scratchpad/card330/mutate.py` | 1 |
| `scratchpad/card330/mutate_fixround.py` | 1 |
| `scratchpad/card330/one_worked_case.py` | 1 |

**Eight files, not three.** CARD-316's round named the three under `card318fix/`
because that is what its own `.py`-scoped experiment surfaced; the largest offender
is a committed **census dump** — a `.txt` holding 41 ref names, which is the artefact
class most likely to revive refs and the least likely to be read by anyone again.

**The 541 is an over-set and the per-file counts inherit that**, so the first job is
to re-derive the population against the real declared-ref set and the real resolver,
not against this table. The table is here to establish that the population is
non-empty and wider than three, not to be copied.

## What to implement

1. **Derive the real population.** For each tracked file under `scratchpad/`, ask the
   resolver's own question: does this file cause `git grep -lw <ref>` to succeed for a
   ref that is otherwise **undefined**? That is the only hit that matters — a ref with
   a real `def`/`class` somewhere resolves regardless and the scratchpad copy changes
   nothing. Report the population as *refs revived*, not *files with hits*.
2. **Untrack what is revived, and keep it.** Round artefacts are evidence; the fix is
   that they stop being *tracked*, not that they stop existing. Move them out of the
   repo (`~/Documents/nonogram-reviews/CARD-NNN/` is where this board already keeps
   round renders) or untrack in place, and record for each file which card produced it
   so the trail survives.
3. **Shut the door.** `.gitignore` `scratchpad/` so the next round cannot reopen this
   by accident. If any card genuinely needs an artefact tracked, it can force-add one
   file deliberately — that is a visible act rather than an invisible default.
4. **Give it a control that can fail.** A cell that asserts no tracked file under
   `scratchpad/` revives an otherwise-undefined ref, with a **positive control in the
   same run** (plant a known-dead ref into a tracked file under the directory, prove
   the cell reds, restore). Without the positive control a trie built wrong reads
   identical to a clean tree — which is the trap CARD-316's own G-2 cell was written
   to avoid.

## Acceptance criteria

- **AC-1** — Given the tracked set under `scratchpad/`, when each file is asked whether
  it causes an otherwise-undefined declared ref to resolve, then the count of **refs
  revived** is reported, derived from the live authorities and the live resolver, and
  the number of such refs afterwards is **zero**.
  `check: {kind: test}`
- **AC-2** — Given the repaired tree, when the guard cell runs, then it fails on a
  planted known-dead ref in a tracked file under `scratchpad/` and passes once the
  plant is removed — both directions demonstrated in one run.
  `check: {kind: test}`
- **AC-3** — Given the validator of record, when it is run before and after, then the
  warning count and the WARN **set** are both recorded, and any warning that
  **appears** is accounted for as a ref that was dead all along rather than one this
  card broke. Expect the count to **rise**: un-reviving a ref restores its warning.
  `check: {kind: test}`
- **AC-4** — Given `.gitignore`, when a new file is created under `scratchpad/`, then
  it is untracked by default.
  `check: {kind: test}`

## Guardrails

- **G-1** — `src/` is not touched. This card changes no production code.
- **G-2** — **Do not run this card's own measurement into a committed file.** The
  defect is committed measurement artefacts; producing another one would be the
  finding reproducing itself. Every dump stays in the session scratchpad, untracked.
- **G-3** — **Do not spell a declared ref in any tracked file in a way that could pass
  for a `def`/`class` line.** Derive names at run time or join them in pieces. The
  orchestrator has reddened this board's guard by naming a verifying ref inside an
  explanatory comment.
- **G-4** — `/Users/omelnikova/MyProjects/forge_1` is read-only. The resolver's
  behaviour is the authority here, not something to change. Note that the exclude list
  is the validator's, so **adding `scratchpad/` to it is not available to this board** —
  which is why the fix is on the repo side.
- **G-5** — The expected direction is **more** warnings, not fewer. A round that
  reports the count going down has either removed a real definition or measured the
  wrong tree.

## Notes

The four items CARD-316's round routed out are now owned as: this card (F-012, the
scratchpad hazard), **CARD-334** (the seven `_meta.dec_expected` flags), and
**CARD-333** + **CARD-319** (the re-point blind spot and mutant 4's residue — both
need a check that reads what a test *asserts*, and both live in `forge_1`).

**Not scheduled into wave 72 deliberately.** Two cards are in review against `main`
right now and both measure census and validator figures off it; moving refs on `main`
mid-review would invalidate their baselines. This card waits for the wave to close.
