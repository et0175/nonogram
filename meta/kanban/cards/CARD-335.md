# CARD-335: Committed measurement artefacts revive dead check refs — and the review YAMLs the reviews themselves write are the worst of them

**Status:** ready
**Priority:** P1
**Category:** tech-debt
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** general-purpose
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** CARD-316's fix round 1, 2026-10-31, F-012, then **re-scoped twice the same day** — once by CARD-316's review cycle 2, which measured the surface the hazard actually occupies, and once by the orchestrator confirming it on `main`. The original cut was wrong about where the problem lives. See *What this card got wrong when it was cut*. It measured that a blanket `scratchpad/**` glob reds its own G-2 guard immediately on three tracked files from an earlier card, named them by site, and routed the hazard rather than fixing it by reddening another card's artefacts — the right call for that card's scope. Re-measured at the decompose station, where the population turned out to be larger than three. See below.
**Idea:** —
**Wave:** —
**Created wave:** 72
**Deferred waves:** 0
**Depends on:** —
**Touches:** meta/review/, meta/profiling/, scratchpad/, .gitignore, tests/test_check_ref_resolution.py
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

### Measured 2026-10-31 by the orchestrator — and the card's original figure was the wrong population

**What this card got wrong when it was cut.** It was scoped to `scratchpad/` and said
"eight files", from a loose 541-candidate over-set derived by regex. Both halves were off.
Re-measured on `main` with declared refs taken from a **proper YAML walk** of
`requirements.yml` + `trace.yml` (the `test`/`tests`/`ref` keys, 534 refs) against the
resolver's real domain (1440 tracked files, excluding `meta/architecture` and `*.md`):

| directory | files resolving ≥1 declared ref |
|---|---|
| `meta/review/` | **231** |
| `meta/profiling/` | 6 |
| `meta/kanban/` | 3 |
| `scratchpad/card318fix/` | 3 |
| `scratchpad/card309/` | 1 |
| `player/` | 1 |

**245 files outside `tests/` and `src/`** — and `scratchpad/`, the directory this card was
cut to clean, is **4 of them**. The worst individual offenders:

| refs spelled | file |
|---|---|
| **292** | `meta/profiling/suite-durations-20261023.txt` |
| 285 | `meta/profiling/card-235-durations-after.txt` |
| 285 | `meta/profiling/card-235-durations-poll-001.txt` |
| 285 | `meta/profiling/suite-durations-20261015.txt` |
| 75 | `meta/review/20260930T123942Z-CARD-139-cycle1.yml` |
| 37 | `scratchpad/card309/census-converted.txt` |

CARD-316's review cycle 2 measured the same surface independently and got **322** files
outside `tests/` and `src/` from a 576-ref set (raw strings plus an ADR inline-check scan).
**The two figures bracket rather than agree, so neither is the number** — they differ in how
a declared ref is derived, which is this board's recurring instrument problem. **Re-derive
against the live authorities and the live resolver as the first act of the round, and state
which derivation you used.** The tables above establish the *shape* — that the population is
large and that `meta/review/` dominates it — and nothing more.

### The structural point, which is why this is P1 and not housekeeping

**The per-card review YAML is the worst offender by construction**, because it is written by
the one agent whose job is to name test refs. A review that does its job thoroughly produces
the most polluting artefact on the board. That is not a mistake any single round made; it is
the default, and 231 files is what the default has accumulated.

It has already caused measured damage. CARD-308 measured a synced review YAML **silencing a
live dead-ref warning on `main`** (108 → 107, nothing repaired) — an *active* silencing, not
a latent one. So the population splits two ways and the distinction decides the fix:

- **Active silencing** — the ref has **no** definition anywhere, and the artefact is the only
  thing making it resolve. The warning is suppressed *today*. This is the damage.
- **Revival hazard** — the ref does have a real definition, so it resolves regardless and the
  artefact changes nothing now; it would revive the ref if that definition were removed.
  CARD-316's cycle 2 verified the three `scratchpad/card318fix/` files are this kind (both
  refs defined, at `tests/test_solver_strategies.py:396` and `tests/test_strategies.py:490`).

**Only the first kind is a defect to repair. Report both counts separately** — a round that
reports one number has not understood the finding.

## What to implement

1. **Derive the real population.** For each tracked file in the resolver's domain, ask the
   resolver's own question: does this file cause `git grep -lw <ref>` to succeed for a
   ref that is otherwise **undefined**? That is the only hit that matters — a ref with
   a real `def`/`class` somewhere resolves regardless and the scratchpad copy changes
   nothing. Report the population as *refs revived*, not *files with hits*.
2. **Untrack what is revived, and keep it.** Round artefacts are evidence; the fix is
   that they stop being *tracked*, not that they stop existing. Move them out of the
   repo (`~/Documents/nonogram-reviews/CARD-NNN/` is where this board already keeps
   round renders) or untrack in place, and record for each file which card produced it
   so the trail survives.
3. **Shut the door, and in the place that keeps reopening it.** `.gitignore` `scratchpad/`;
   decide what the standing convention is for `meta/review/` and `meta/profiling/`, which is
   the real decision here and is **not** simply "untrack 231 files" — a review YAML is a
   record someone may want. The options worth measuring are: keep them but **outside the
   resolver's domain** (the `*.md` exclusion already demonstrates the mechanism), rename them
   to an excluded extension, or have reviews spell refs in pieces as this board's briefs
   already require. Recommend one with the measurement behind it. If any card genuinely needs an artefact tracked, it can force-add one
   file deliberately — that is a visible act rather than an invisible default.
4. **Give it a control that can fail.** A cell that asserts no tracked file in the
   resolver's domain revives an otherwise-undefined ref, with a **positive control in the
   same run** (plant a known-dead ref into a tracked file under the directory, prove
   the cell reds, restore). Without the positive control a trie built wrong reads
   identical to a clean tree — which is the trap CARD-316's own G-2 cell was written
   to avoid.

## Acceptance criteria

- **AC-1** — Given the tracked set in the resolver's domain, when each file is asked whether
  it causes an otherwise-undefined declared ref to resolve, then the count of **refs
  revived** is reported, derived from the live authorities and the live resolver, and
  the number of such refs afterwards is **zero**.
  `check: {kind: test}`
- **AC-2** — Given the repaired tree, when the guard cell runs, then it fails on a
  planted known-dead ref in a tracked file in the resolver's domain and passes once the
  plant is removed — both directions demonstrated in one run.
  `check: {kind: test}`
- **AC-3** — Given the validator of record, when it is run before and after, then the
  warning count and the WARN **set** are both recorded, and any warning that
  **appears** is accounted for as a ref that was dead all along rather than one this
  card broke. Expect the count to **rise**: un-reviving a ref restores its warning.
  `check: {kind: test}`
- **AC-4** — Given the chosen convention, when a new measurement artefact or review YAML is
  written, then it lands outside the resolver's domain by default rather than by the author
  remembering to keep it out.
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

**The estimate went 0.5d -> 1d at the re-scope**, and the work changed shape with it: the
original card was a tidy-up of four files, this one carries a convention decision about 231.

**Not scheduled into wave 72 deliberately.** Two cards are in review against `main`
right now and both measure census and validator figures off it; moving refs on `main`
mid-review would invalidate their baselines. This card waits for the wave to close.
