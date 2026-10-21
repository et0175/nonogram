# 03 — Deriving clues (CAP-002 / COMP-004)

> Scope: `src/nonogram/clues.py`, 125 lines, three public functions.

## Why this is the smallest module in the system

CAP-002 is one step: run-length encode every row and column of a solution grid so
the grid becomes a *playable puzzle definition* rather than just a picture
(FR-005). It is the pivot of the whole backwards construction — the grid is the
answer, and these tuples are the question.

It is a pure function module: no state, no I/O, no logging, no clock, no
randomness. Every function is a total function of its arguments, and
`clues.py:4` names the consequence that matters: that is what lets INV-001 be
checked as a property (AC-014) **without any fixture machinery**.

INV-001 — "clues always equal the run-length encoding of the current grid" — is
the invariant this module exists to make checkable. It is *upheld* here and
*enforced* in `orchestrator.Puzzle.record_candidate`, which writes grid and clues
in one operation so the two can never drift (see
[01-the-layered-pipeline.md](01-the-layered-pipeline.md)).

## The boundary representation, and why it is deliberately dull

```python
Grid    = list[list[bool]]              # row-major, True == filled
LineClue = tuple[int, ...]
ClueSet  = tuple[tuple[int, ...], ...]
```

ADR-0012 fixes these. The grid arrives as `list[list[bool]]` and clues leave as
nested tuples. The solver's internal int-bitmask-per-line representation — also
ADR-0012 — is COMP-005's private business and **deliberately does not appear in
this module's API**. `clues.py:7` records the reason as a forward-looking one:
ADR-0012's "Neutral" consequence asks future work to keep clue tuples and grid
bitmasks as separate representations serving separate concerns.

Immutable tuples on the way out mean one clue set can be handed to the solver, the
difficulty scorer and all five exporters without any of them being able to mutate
what the others see.

`Clues` is a `NamedTuple` of `(rows, columns)` rather than two return values,
because "rows and columns are derived from one grid in one pass and are
meaningless apart; naming the two members removes the classic `(rows, cols)`
transposition bug at the call site" (`clues.py:52`). It is still a plain tuple, so
it unpacks and serialises like one.

## `(0,)`, never `()`

```python
EMPTY_LINE_CLUE: LineClue = (0,)
```

A line with no filled cells encodes to `(0,)`. This is the conventional nonogram
notation, and `clues.py:20` gives the structural reason it is not `()`:

> it keeps every line's clue non-empty so downstream renderers and the solver's
> line logic can treat "clue" uniformly — `len(clue)` is always at least 1, and
> the "sum of runs plus one gap between each pair" arithmetic the solver uses
> stays valid without a special case.

The marker is load-bearing in the opposite direction too. `clue_matches_line`
compares **exactly**, in both directions, so an all-empty line is matched only by
`(0,)` and never by `()` — "so a clue set that dropped the marker somewhere is
reported as a mismatch instead of passing silently" (`clues.py:120`).

## The three functions

```python
def encode_line(line: Iterable[bool]) -> LineClue
def compute_clues(grid: Grid) -> Clues
def clue_matches_line(clue: Sequence[int], line: Iterable[bool]) -> bool
```

`encode_line` accepts any iterable of truthy/falsy cells, which is what lets a
caller pass a generator or a transposed column without materialising a list.
`[True, True, False, True, True, True, False, False]` → `(2, 3)` (AC-012).

`compute_clues` encodes rows top-to-bottom and columns left-to-right in one pass:

```python
columns: ClueSet = tuple(encode_line(column) for column in zip(*grid, strict=True))
```

`strict=True` is the interesting character. A ragged grid is a *programming error*,
not a domain condition, so it raises `ValueError` rather than a `NonogramError`.
The alternative is worse than a crash and the docstring says why: without `strict`,
`zip` would silently truncate the columns to the shortest row, "which would produce
clues that quietly disagree with the grid and so violate INV-001 without anything
failing" (`clues.py:94`).

An empty grid yields two empty clue sets.

## `clue_matches_line` is scoped to *complete* lines, and says so

This is the one place in the module with a documented footgun, documented
precisely so a solver author does not step in it (`clues.py:111`):

> Scoped to *complete* lines only … There is no type check here, and any falsy
> value reads as empty and any truthy value reads as filled — so a partial-line
> representation (the solver's per-ADR-0012 internal state during search, where a
> cell can also be "unknown") is silently misread rather than rejected. A solver
> hot-loop that reasons about partial lines must not call this as-is; it needs its
> own three-valued check.

The solver does exactly that. `solver/propagate.py:403` holds `mask_runs`, "the
bitmask twin of `clues.encode_line`, for the one case where the line is complete
and the DP would be wasted work" — a native reimplementation, because ADR-0007
forbids a capability module importing a sibling and `clues` is COMP-004's
capability rather than a shared kernel. The two are pinned against each other from
the test tree, where the import is legal.

So this module has exactly **two** consumers inside `src/`: the orchestrator
(`orchestrator.py:129`, as `clue_derivation`) and the admin panel's storage guard
(ADR-0032/R1 — see
[07-book-assembly-and-the-admin-panel.md](07-book-assembly-and-the-admin-panel.md)).
It has no other callers because it may not have them: everything else is at rank 2
or deeper.

## Bounds and honest gaps

- The module deliberately has no notion of a "valid" clue set. A clue whose runs
  cannot fit a line of that length is not rejected here; that is the solver's
  answer (`solution_count == 0`) rather than this module's error.
- `clue_matches_line` is the INV-001/AC-014 check. It is *not* used anywhere
  inward of the orchestrator as a runtime assertion: the solver's own CON-005
  backstop re-encodes a completed board through `mask_runs` instead (see
  [04-uniqueness-and-recovery.md](04-uniqueness-and-recovery.md)).

## Related

- [01-the-layered-pipeline.md](01-the-layered-pipeline.md) · [04-uniqueness-and-recovery.md](04-uniqueness-and-recovery.md) · [06-exporting-a-finished-puzzle.md](06-exporting-a-finished-puzzle.md)
- ADRs: [ADR-0012](../../../../meta/architecture/decisions/adr/0012-grid-data-representation.md) · [ADR-0007](../../../../meta/architecture/decisions/adr/0007-internal-module-architecture.md)
