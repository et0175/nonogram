# CARD-303: The door walk is super-linear — 19.4 million inner calls for a module with 832

**Status:** ready
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1d
**Complexity:** complex
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/303-the-door-walk-is-super-linear
**Worktree:** —
**Source:** CARD-287's implementation round, 2026-10-28 — its §7 "could not establish", measured with cProfile and deliberately not pursued because the remedy is the walk's algorithm, which is where CARD-287's G-1 bites and which its G-7 assigns away.
**Idea:** —
**Wave:** unscheduled
**Created wave:** 62
**Deferred waves:** 0
**Depends on:** CARD-287 (in review)
**Touches:** tests/test_book_export_interior_cover.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## The measurement, which is the whole case for this card

CARD-287 profiled `test_each_door_axis_arm_catches_a_shape_the_other_misses` and,
after taking the 45 % saving that was available, reported what was left. For a
module with **832 `ast.Call` nodes**, one analysis of it costs:

| site | ncalls in the profiled dear test | tottime |
|---|---|---|
| `ast.iter_child_nodes` | **49 719 139** | 12.422 s |
| `ast.iter_fields` | **63 111 644** | 7.019 s |
| `builtins.isinstance` | **131 818 991** | 6.512 s |
| `ast.walk` | **23 155 457** | 5.884 s |
| `_page_positions`' inner `called()` | **19 400 000** | — |

**19.4 M calls to `called()` across 108 analyses is ~180 000 per analysis, for a
module holding 832 call nodes — about 216 inner calls per call node.** That ratio
is what makes this super-linear rather than merely large, and it is the reason
the class still costs **32.70 s** after CARD-292 and CARD-287 each took a
near-halving out of it by fixing *constants*.

**Both easy wins are now spent.** CARD-292 memoised the line split (8× per
analysis); CARD-287 found the second call site CARD-292 had missed and routed it
through the same memo (a further 42.8 % off the class). Neither touched **how
many times the walk visits a node**. This card is the first that has to.

## Why it is P3 and `complex` rather than P2

- The prize is bounded: the class is **2.66 %** of a ~1241 s suite. A further
  halving is ~16 s, about 1.3 % of the suite.
- The risk is not bounded in the same way. **The walk is the guard**, and
  CARD-287's G-1 — *do not buy time by guarding less* — bites harder here than
  anywhere this board has applied it: a cheaper traversal that visits fewer nodes
  is a guard that proves less, and the thing being proved was bought over **four
  gating review cycles across CARD-206 and CARD-262**.
- So the honest expected outcome includes **"no remedy survives G-1"**, exactly
  as CARD-287's AC-2 allowed — and CARD-287 is the precedent that such a result
  is worth recording rather than a failure.

## What to implement

1. **Find out why it is super-linear, before proposing anything.** The shape to
   test first: `called()` is an inner function of `_page_positions`, and the walk
   appears to re-enter subtrees — `iter_child_nodes` at 49.7 M against
   `ast.walk` at 23.2 M suggests nodes are visited through more than one path.
   Establish the exponent empirically: run the analysis over **truncated copies
   of the module** at several sizes and fit `calls` against `nodes`. A claim of
   "super-linear" is a figure, and its control is recomputation at more than one
   size.
2. **Then decide whether a remedy exists that changes no verdict.** Candidates to
   price, not to assume: memoising `called()` on node identity; hoisting an
   invariant out of the per-node closure; a single pre-pass building the
   parent/child index the walk currently re-derives. **Each must be priced
   against the capture in item 3 before it is written.**
3. **Reuse CARD-287's verdict capture — do not write a new one.** It built a
   **1 752-line, 52-section** canonical capture of the guard's entire observable
   answer (144 `(arm-config, plant, verdict, refusal-reason)` quadruples, the
   plant inventory, and `sites`/`vocabulary`/`refusals` under ten
   configurations) and proved it **byte-for-byte identical** across its change.
   Its probe scripts are at `~/Documents/nonogram-reviews/CARD-287/`
   (`capture.py`, `ac6_doors.py`). **That capture is this card's safety net and
   its reuse is a requirement, not a convenience.**

## Acceptance criteria

- **AC-1** (the exponent is measured, not asserted): *Given* the analysis run
  over truncated modules at **at least four** sizes, *then* the card records
  inner-call count against node count and states the fitted relationship, with
  the instrument named. "Super-linear" without a second size is a story.
  (recorded, verified by review)
- **AC-2** (the verdict set is unchanged): *Given* CARD-287's canonical capture
  recomputed before and after, *then* it is **byte-for-byte identical** —
  `cmp -s`, not "the tests still pass". (**gate**: the capture re-run on the
  committed blob, as CARD-287 did, because figures taken on an uncommitted arm
  belong to nothing.)
- **AC-3** (the saving, predicted then measured): *Given* a remedy, *then* the
  card states the expected saving **in advance** from an instrument in a
  different domain from the one that found the hotspot, then measures it over
  three runs of each arm **interleaved**, with host cells at both ends of every
  run — load average **and** rival-pytest via
  `pgrep -f 'MacOS/Python.*pytest' | wc -l`. (recorded)
- **AC-4** (a refusal is an acceptable result): *Given* that no candidate
  survives AC-2, *then* the card records which were priced, what each would have
  saved, and which verdict each would have cost — and **lands on that**. A
  refused optimisation with its measurement beats a weakened guard.
- **AC-5** (no test retired): *Given* the touched file, *then* the collected
  node-id set loses nothing — set difference over sorted ids, additions named.
  **Param ids count.**
- **AC-6** (the suite figure): *Given* the next full-suite profile, *then* the
  card records this file's and this class's new seconds and share against
  CARD-287's measured baseline — file **70.62 s**, class **32.70 s**, dear test
  **15.21 s** — and **not** against any earlier figure.

## Guardrails

- **G-1: do not buy time by guarding less.** The central constraint, inherited
  from CARD-287 where it was never actually in tension. **Here it will be.** The
  walk's reach *is* the guard's reach.
- **G-2: do not edit `src/**`.** The analysed module is the subject; a production
  change is a finding to raise.
- **G-3: do not touch CARD-292's memo or `_source_lines`' cap.** CARD-287 priced
  the cap at ≈ 0.45 s and declined it because it changes a declared mechanism and
  the control pinning it. That judgement stands; re-opening it is not this card's.
- **G-4: do not move, mark, or make the class opt-in**, and do not reduce the
  number of plants, arm configurations or analyses. A saving from running less
  evidence is the defect, not the remedy.
- **G-5: probes stay OUT of `tests/`** — `tests/test_suite_profile.py` asserts
  `rank_durations.py`'s frozen render set as an equality, and it enumerates
  **`tests` and `meta/profiling`** via `git ls-files`, so a *tracked* probe under
  `meta/profiling/` is judged by it. A separate guard scans the **whole tree** for
  the full-suite guard's two env switch names and does **not** exempt
  `meta/profiling/` — CARD-292 paid for that twice.
- **G-6: no new dependency** (ADR-0006/R1). `ast` and `functools` are stdlib.
- **G-7: the guard's correctness is not this card's**, and neither is the alias
  family. CARD-287 declared the bound that a stdlib reference bound to a name and
  called through it is invisible to its new guard; that stays declared.

## Worktree notes

- **Runs SOLO.** The deliverable is a timing measurement, and `tests/README.md`
  records that a contended run "tells you nothing at all".
- **The 120 s per-test ceiling is `tests/hang_guard.py`**, armed per test with
  `exit=True`, and `addopts = "-q"` hides the header line that announces it. A
  kill gives exit 1, **no summary line**, truncated output and a dump in
  `$TMPDIR/nonogram-test-hang.txt`. That is a measurement defect, never a tree
  verdict. The dearest test here is now 15.21 s, so there is ample headroom — but
  a candidate remedy that makes the walk *more* expensive could change that.
- **Read CARD-287's `## [IMPLEMENTATION — 2026-10-28]` section before starting.**
  It names the two call sites, the capture, the mutant census, and the three
  bounds it declared rather than closed. This card exists because of its §7.
