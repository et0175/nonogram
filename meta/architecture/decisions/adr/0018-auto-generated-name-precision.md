# ADR-0018: Auto-generated name precision for random/image-sourced puzzles

**Status:** Accepted
**Date:** 2026-08-27
**Deciders:** Puzzle Creator (project owner)
**Revised:** —
**Migration:** —
**Pattern:** —
**API-Posture:** —

## Context

FR-015 requires an auto-generated default name for puzzles created from the random and image-sourced modes when the user does not supply `--name`. The raw requirement specifies this name as "`<mode>-<YYYY-MM-DD>-<HHMM>`" (e.g. "random-2026-08-27-1430") — minute precision, derived from the mode and the wall-clock time of generation.

Minute precision means two puzzles generated in the same mode within the same clock minute receive the identical auto-generated name. On its own this is only a display-name collision. But DEC-017 governs what happens when a name — auto-generated or explicit — collides with an existing exported file on disk (FR-016), and its resolution adopts `auto_suffix`: appending an incrementing numeric suffix ("-1", "-2", …) at export time to avoid overwriting or erroring. Whether identical same-minute auto-names are worth preventing at the point they are *generated*, rather than left to be resolved only later at the point of *export*, is the question this decision settles. US-011 frames the auto-name as a convenience for a single-user, single-process CLI (CON-001) rather than as an identifier requiring global uniqueness guarantees, which bounds how much machinery this needs to justify.

## Decision

We will adopt the `counter_suffix` alternative: the auto-generated name keeps minute precision — "`<mode>-<YYYY-MM-DD>-<HHMM>`" — in the common case, and a small disambiguating counter ("-1", "-2", …) is appended only when a same-minute auto-generated name already exists in the current run's naming context. This satisfies FR-015 because it preserves the short, human-readable name the raw requirement specifies for the overwhelming majority of invocations, while still guaranteeing that two puzzles generated within the same minute never carry identical default names. It is also the same mechanism ADR-0017 already adopted for DEC-017's export-time collision policy (`auto_suffix`) — this decision applies that identical idea one layer earlier, at name generation rather than at file export, so the two collision points in the pipeline (name generation, then export) are handled with one consistent disambiguation pattern instead of two different ones.

## Consequences

### Positive
- The common case is unaffected: a puzzle generated in isolation still gets the short, exact "`<mode>-<YYYY-MM-DD>-<HHMM>`" name the raw requirement specifies, with no counter clutter.
- Same-minute collisions are eliminated at the source (name generation) rather than merely papered over later at export, so a same-minute auto-name is never ambiguous even before DEC-017's export-time suffixing has a chance to run.
- Reuses the exact disambiguation mechanism already adopted in ADR-0017 for export collisions, rather than introducing a second, different collision-avoidance idea (e.g. seconds precision) into the pipeline — one mental model covers both collision points.

### Negative
- The counter-suffix branch only executes when two or more same-mode generations land in the same clock minute, which is rare in normal single-user CLI usage; this makes it easy to under-test and easy for a future change to silently break without a test noticing (as the DEC-018 alternative's own stated con anticipates).
- Determining "a same-minute auto-name already exists" requires the generator to track or check previously-used auto-names within its naming context (e.g. the current run, or on-disk exports), which is a small piece of state/logic that a pure minute-precision or seconds-precision approach would not need.

### Neutral
- The auto-name generation logic and the DEC-017 export-suffix logic now share the same suffixing convention ("-1", "-2", …); a future change to one convention (e.g. switching to a different disambiguator) should be evaluated against both call sites together to avoid the two diverging.
- Property/unit tests for FR-015 should include a same-minute-collision case (e.g. by injecting two generations against a fixed clock) specifically because this is the branch most likely to go untested otherwise.

## Alternatives considered

### minute_precision_as_specified

Keep "`<mode>-<YYYY-MM-DD>-<HHMM>`" exactly as given in the raw requirement, with no additional disambiguation, accepting that two same-mode puzzles generated within the same minute get identical default names. This matches the raw requirement most literally and keeps names as short as possible, but it was rejected because it pushes every same-minute collision downstream into DEC-017's export-time handling with no signal at the point the name is chosen — and if a user is naming multiple exports separately, or DEC-017's per-run tracking is scoped differently than name generation is, the same-minute collision could surface in ways export-time suffixing alone does not cleanly cover. Given that closing the gap at the source is cheap, there was no compensating benefit to leaving it open.

### second_precision

Extend the auto-generated name pattern to "`<mode>-<YYYY-MM-DD>-<HHMMSS>`", making same-timestamp collisions effectively impossible without any counter logic. This is simpler to implement (no state tracking, just a wider timestamp) and was seriously considered, but it was rejected because it changes the auto-name's shape for every single invocation — including the overwhelming majority that never collide — to guard against a rare case, and it moves the project away from the raw requirement's literal minute-precision example without reusing the collision-handling pattern DEC-017 already established for the export layer. `counter_suffix` achieves the same collision-free guarantee while keeping the common-case name exactly as specified and reusing one disambiguation idea across both the naming and export layers instead of introducing a second, different one.

## References

- DEC-018 (resolved by this ADR)
- CTX-001 (Puzzle Creation — the context that generates the auto-name and performs export)
- FR-015 (criterion this decision satisfies)
- ADR-0017 (export-time collision policy — the `auto_suffix` mechanism this decision reuses at the name-generation layer)

## History

- 2026-08-27: Created — adopted minute-precision auto-generated names with a disambiguating counter suffix on same-minute collisions, reusing ADR-0017's auto-suffix mechanism one layer earlier at name generation instead of at file export.
