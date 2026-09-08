# ADR-0012: Grid data representation

**Status:** Accepted
**Date:** 2026-08-27
**Deciders:** Puzzle Creator (project owner)
**Revised:** —
**Migration:** —
**Pattern:** —
**API-Posture:** —

## Context

The solution grid and its derived clue sets are the core data structure every capability touches: CAP-001 writes it, CAP-002 encodes it into clues, CAP-003 (the solver) searches over it, CAP-004 measures it for difficulty, and CAP-005 serializes it on export. AGG-001 and INV-001 govern the grid's invariants, and the choice of in-memory representation dominates NFR-001, since the solver's inner loop intersects candidate line placements on the order of millions of times per generation run at grid sizes up to 50x50. Whatever representation is chosen must also fix what EC-002's JSON/CSV round-trip property has to reproduce exactly, since the boundary representation used for export is not necessarily the same structure the solver operates on internally.

Line lengths in this domain are bounded at 50 cells (the maximum supported grid size, AC-038), which is small enough to fit in a single machine word. Any representation choice therefore has to weigh per-cell object overhead and copy cost in the solver's hottest path against readability, debuggability, and how directly it serializes at the EC-002 boundary. DEC-006 has already fixed the third-party dependency baseline for this project (Pillow for image I/O), which constrains what representations can rely on external libraries without reopening that decision.

## Decision

We adopt `int_bitmask_per_line`: each row (and, symmetrically, each column) is represented as a pair of Python ints used as bitmasks — one for "known filled" cells and one for "known empty" cells — giving the three-valued filled/empty/unknown state the solver needs during propagation. Placement enumeration and intersection, the solver's hot operation, become native integer `&`, `|`, and `~` operations. A plain `list[list[bool]]` (or a tuple of rows) is the boundary representation used for export and the public API, and clues are represented as `tuple[tuple[int, ...], ...]` for rows and columns. This satisfies NFR-001 and INV-001 because at line lengths of at most 50 bits, a single CPython int operation is the fastest primitive available without leaving the language, and it satisfies EC-002 because the boundary type (`list[list[bool]]`) is a structure the solver never operates on directly, keeping the round-trip contract simple and independent of internal representation choices.

Note on NumPy: ADR-0006 separately added NumPy to the project's dependency baseline for image handling (Pillow interop). That inclusion does not extend to the grid representation decided here. At line lengths of ≤50 bits — the maximum this tool supports — NumPy's per-call and array-overhead cost typically loses to a single native Python int operation, so NumPy remains available in the dependency baseline for image-related work but is deliberately not used for the solver's core grid representation.

## Alternatives considered

### list_of_lists

`list[list[Cell]]` throughout, using an enum or small int per cell for filled/empty/unknown, with the solver operating on the same structure the exporter serializes. This is the simplest representation to read, debug, and print, and it is trivially JSON-serializable, making EC-002 nearly free. It was rejected because per-cell Python-object overhead in the solver's innermost loop is likely the difference between meeting and missing NFR-001 at 50x50, and because backtracking over this structure needs deep copies or an explicit undo log, adding both memory churn and implementation complexity exactly where correctness (CON-005) matters most.

### numpy_boolean_array

2-D NumPy arrays for both the grid and solver state, with vectorized line operations, and a natural, free transpose for column passes. This was rejected primarily because it pulls NumPy into the solver's core data path, which DEC-006's chosen baseline (Pillow for image I/O, plain Python structures for grids) does not call for, and because — as DEC-006 itself notes — for lines this short (≤50 bits), NumPy's per-call overhead typically loses to a single native int operation, giving up the vectorization benefit that would otherwise justify the dependency. It would also require explicit `.tolist()` conversions at every export boundary, or risk EC-002's round-trip silently reproducing NumPy scalar types instead of plain JSON-compatible values.

## Consequences

### Positive
- The solver's hot loop — placement-set intersection — becomes a single native `&` over accumulated integer masks, which is the fastest primitive CPython offers at line lengths that fit in one machine word, directly supporting NFR-001's 50x50 time bound.
- Backtracking's undo step is essentially free: ints are immutable, so the search only needs to keep the prior int value rather than performing a deep copy or maintaining an explicit undo log.
- The boundary representation (`list[list[bool]]`) stays simple and decoupled from the solver's internals, so EC-002's round-trip property only has to reason about a plain, JSON-native structure rather than about bitmask encoding details.

### Negative
- Bit-twiddling code is less readable than nested lists or an explicit Cell enum, so the conversion helpers between bitmask and boundary representations need careful, well-tested coverage to avoid off-by-one or bit-order bugs at the seam.
- Column access requires either an explicit transpose or maintaining row and column masks in parallel, adding a small amount of bookkeeping the solver must get right consistently in both directions.

### Neutral
- This decision does not change DEC-006's dependency baseline: NumPy stays in the project via ADR-0006 for image handling, but is explicitly out of scope for the grid representation decided here — the two ADRs describe non-overlapping uses of NumPy's presence in the dependency set.
- Clue tuples (`tuple[tuple[int, ...], ...]`) and grid bitmasks are separate representations serving separate concerns (CAP-002's encoding vs. CAP-003's search), and future work extending the solver should preserve that separation rather than collapsing clues into the bitmask representation.

## References

- DEC-012 (resolved by this ADR)
- CTX-001 (the single bounded context this representation lives inside)
- NFR-001, EC-002, INV-001 (criteria this decision satisfies)
- ADR-0006 (dependency baseline: Pillow + NumPy — the source of the NumPy-availability note above)
- DEC-009 (solver implementation strategy, which operates directly on this representation)

## History

- 2026-08-27: Created — fixed the int-bitmask-per-line solver representation with a `list[list[bool]]` export boundary, over a plain list-of-lists or a NumPy boolean array, on NFR-001 hot-loop performance grounds.
