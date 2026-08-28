# ADR-0001: Generation-time thresholds for random puzzle generation

**Status:** Accepted (revised 2026-08-28)
**Date:** 2026-08-27
**Deciders:** Puzzle Creator (project owner)
**Revised:** 2026-08-28
**Migration:** grandfather
**Pattern:** —
**API-Posture:** —

## Context

NFR-001 requires random puzzle generation to feel interactive for common grid sizes, and NFR-002 already bounds the regenerate/resample retry loop's iteration count — but neither NFR pins down the actual wall-clock numbers a generation run must meet. docs/requirements.md's NFR-1 only says generation should complete in "a few seconds" for typical sizes, and NFR-2/AC-038 (the 50x50 case) only says the largest supported size must complete "within the configured timeout bound or fail clearly with a timeout error — it never hangs indefinitely," without stating what that bound is.

This leaves two numbers open: (a) the p95 generation-time cap for grids up to 20x20, the size range NFR-001's "typical hardware" condition and AC-037 target, and (b) the hard timeout bound for larger grids (up to the 50x50 maximum size AC-038 exercises), where the regenerate loop's own retry cap (NFR-002) does not guarantee an overall time bound because a single unlucky solve can itself run long.

This ADR was originally written before the solver (FR-006) existed, with both numbers explicitly flagged as unvalidated pending profiling. CARD-004 (the solver) and CARD-006 (the cooperative deadline mechanism) have since supplied that profiling. CARD-006's benchmark (AC-037, `BenchGenerate_20x20_p95Under5s`) measured p95 generation time at 20x20 across the full density range: at density >=50%, the 5s cap is met with large margin (worst observed 0.134s — line logic alone settles nearly the whole board). At density 30-40%, it is not merely missed but unbounded: half the sampled requests never finish inside the 30s hard cap at all (censored lower bound), because line-logic propagation resolves almost nothing (0/400 cells on 11 of 12 sampled 20x20/30% candidates) and the backtracking search has to reject a large number of wrong subtrees one at a time. CARD-004's own findings already established that the search's *propagation* is sound on these grids — a descent guided by the true solution reaches it in 47-283 guesses — so the cost is specifically in how many wrong subtrees the search visits before finding a right one, not in the grid representation or the solver's correctness.

This is exactly the condition this ADR's own Negative consequences section named as grounds for revisiting it.

## Decision

We reaffirm the original numbers unchanged: a 5-second p95 generation-time cap for grids up to and including 20x20 (any density), and a 30-second hard timeout for larger grids up to the 50x50 maximum. The 20x20 shortfall at 30-40% density is treated as an **implementation gap in the solver's search strength, not a wrong requirement** — CARD-004 showed the propagation mechanism is sound and the missing piece (probing / limited lookahead, so a wrong subtree is rejected near the root instead of after thousands of nodes) is a tractable, scoped engineering task, not evidence that 5s was never achievable at 20x20. Narrowing NFR-001 to a density floor, or raising the cap toward AC-038's bound, would each quietly weaken what "interactive at 20x20" promises for a real class of puzzles (nonogram density is a property of the *picture* being encoded, not a nuisance edge case — a sparse or asymmetric image is not scoped as unusual anywhere in this model) in exchange for zero engineering effort, before the one lever CARD-004 already identified as promising has been tried. AC-037's benchmark test (`tests/bench_generate.py::test_20x20_p95_is_under_5s`) is marked `xfail` with this ADR cited as the reason it is expected to fail, rather than left as a permanently red gate or silently loosened — the gap stays visible in every test run until a follow-up card closes it.

## Alternatives considered

### 10s_cap_60s_timeout

(Original alternative, unchanged from this ADR's first version.) Doubles both numbers: a 10s p95 cap for grids up to 20x20 and a 60s hard timeout for larger sizes. Rejected because it gives up the direct match to docs/requirements.md's "a few seconds" phrasing in exchange for headroom not shown to be necessary at the time, and — now that it has been profiled — headroom that would not even close the 20x20/30-40% gap (that gap is unbounded within a single 30s attempt, not a near-miss a few extra seconds would fix).

### scope_by_density (DEC-019)

Redefine NFR-001/AC-037 to apply only at density >=50%, where the target is already met with large margin, and declare lower densities explicitly out of NFR-001's scope. Rejected: this narrows what "interactive for common sizes" means without any evidence that low-density requests are rare — `--density` has no CLI default, so nothing in this model says low density is atypical — and it would lock in the current solver's search strength as a permanent ceiling on the *requirement* rather than treating it as the current state of an improvable implementation.

### raise_cap_uniformly (DEC-019)

Keep NFR-001/AC-037 density-agnostic but raise the numeric p95 cap toward AC-038's 30s hard bound, so the current solver already satisfies it everywhere. Rejected: this defeats NFR-001's actual purpose (the reason 5s was chosen was to match docs/requirements.md's "a few seconds," i.e. to keep the CLI feeling interactive) rather than genuinely meeting it, and would make AC-037 and AC-038 nearly redundant as acceptance criteria.

## Consequences

### Positive
- The requirement keeps stating the behavior actually wanted (interactive generation at 20x20 regardless of density) instead of being narrowed to match a current, improvable implementation limitation.
- Puts the burden of proof on strengthening the solver's search, which is where CARD-004's own findings say the real, tractable cost lives — not on redefining what "done" means.
- The gap is tracked, not hidden: an `xfail` with a reason is visible in every test run (as `XFAIL`, distinct from both a silent pass and a build-breaking failure) until the follow-up card closes it, unlike a quietly loosened threshold that would look identical to the case where 5s was genuinely met.

### Negative
- Leaves a known, unresolved requirement gap in the codebase with no committed timeline — CARD-006 merges with `test_20x20_p95_is_under_5s` marked `xfail` rather than green, and the gap persists until a follow-up card lands.
- If the follow-up solver-strengthening work turns out to be harder than CARD-004's findings suggest, this decision will need to be revisited again — possibly toward `scope_by_density` after all, once there is evidence the gap is not in fact tractable.

### Neutral
- This ADR still fixes the threshold NUMBERS only; the MECHANISM enforcing the 30s deadline was resolved separately by CARD-006 (ADR-0011).
- The 5s figure remains a benchmark gate (AC-037, now `xfail`-marked) rather than a hard failure boundary, while the 30s figure remains a hard failure boundary (AC-038) — this asymmetry is unchanged by this revision.
- Unblocks a specific next step: a follow-up card to strengthen the solver's search (probing / limited lookahead) at mid/low density, which is the second `xfail` reason to become obsolete once that card lands (the first being "resolved by profiling," now done).

## References

- DEC-001 (resolved by the original version of this ADR)
- DEC-019 (resolved by this revision)
- NFR-001 (p95 generation-completion-time metric this decision fixes)
- AC-037, AC-038 (acceptance criteria this decision makes testable)
- DEC-011 / ADR-0011 (the timeout ENFORCEMENT MECHANISM, implemented by CARD-006)

## History

- 2026-08-27: Created — fixed the 5s p95 cap for grids <=20x20 and the 30s hard timeout for larger sizes, matching docs/requirements.md's "a few seconds" language over the more conservative 10s/60s alternative.
- 2026-08-28: Revised — resolves DEC-019. Previous decision: 5s_cap_30s_timeout (numbers unchanged by this revision). Reason: CARD-006's benchmark empirically confirmed the anticipated need to revisit this ADR — the 5s/20x20 cap is unbounded (not merely missed) at 30-40% density. Reaffirmed the original numbers rather than narrowing scope (`scope_by_density`) or raising the cap (`raise_cap_uniformly`), because CARD-004 already established the solver's propagation is sound and the gap is specifically in search strength — a tractable, scoped engineering task. The shortfall is tracked via an `xfail`-marked benchmark test and a follow-up card, not by redefining the requirement.
