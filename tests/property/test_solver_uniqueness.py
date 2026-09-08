"""EC-001 / CON-005: the uniqueness check never produces a false positive.

    PropertyTest_Solver_NeverFalsePositiveUniqueness
        -> test_never_false_positive_uniqueness      (ADR-0014 direction 1)
        -> test_finds_the_source_grid                (ADR-0014 direction 2)

CON-005 is the one mandatory-severity constraint in the model, and EC-001
states it as a property over *any* clue set: the solver must never report
``solution_count = 1`` for a clue set that actually has 0 or more than 1
solutions. ADR-0014 gives that property two enforcement directions, and this
module runs both:

1. **Cross-check against the brute-force oracle.** Random clue sets small
   enough to enumerate exhaustively, with the solver's verdict compared
   against ``tests/helpers/brute_force_oracle`` — an independently written,
   deliberately naive counter that shares no code with ``nonogram.solver``.
   This is the direction that can see a *missed second solution*, which is the
   exact failure CON-005 forbids and the one a solver cannot detect about
   itself.
2. **Free-direction round-trip.** Clues derived from a real grid have at least
   that grid as a solution, so the solver must never answer 0, and when it
   answers 1 the grid it returns must be the original. No oracle needed.

The increment-1 checkpoint asks for >= 1000 cases; the case count is asserted
in the tests themselves rather than left to a comment, so shrinking the corpus
can never quietly drop below the bar.

Determinism (ADR-0015, guardrail G-2)
-------------------------------------
Every case comes from a seeded ``random.Random``. There is no fixture and no
external dependency — the solver is a pure function of its clues (ADR-0007),
which is precisely what EC-001 relies on to run at this scale. A failure
prints the exact clue set, and re-running the suite reproduces it.

No ``hypothesis``: ADR-0006's dependency baseline is closed, and CARD-002's
property test set the house pattern of a seeded RNG plus hand-picked edge
shapes. This follows it.

Why the corpus tops out at 8x8
------------------------------
EC-001 names 8x8 as the generation ceiling, and it is also where the oracle
stops being free: its cost is the product of each row's candidate count, which
is fine to 8x8 (about 1-4 ms per case, with rare unsatisfiable clue sets
reaching ~0.2 s) and grows sharply beyond it. Cross-checking every case rather
than only the smallest ones is affordable here, so that is what happens — the
weaker "internal consistency only" fallback EC-001 allows for larger grids is
not needed at these sizes.

ADR-0014 also asks for the free-direction check to be scaled to 30x30. That is
deliberately *not* done here: without ADR-0011's cooperative deadline (CARD-006,
out of scope for this card per guardrail G-5) a single pathological large grid
would hang the suite instead of failing it. ``tests/test_solver.py`` carries a
bounded larger-grid round-trip instead, and the card's worktree notes record
the measurements behind that call.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from nonogram.clues import Clues, compute_clues
from nonogram.solver import MANY, solve
from tests.helpers.brute_force_oracle import count_solutions

#: One seed for the whole module: change it and the corpus changes wholesale,
#: which is a deliberate act, not a side effect of running the suite twice.
SEED = 20260827

#: EC-001's increment-1 checkpoint.
REQUIRED_CASES = 1000

#: Grid edge lengths drawn from. The lower end is not padding: 1x1 and 2x2
#: clue sets are where off-by-one bugs in run placement surface most cleanly.
SIZES = (1, 2, 3, 4, 5, 6, 7, 8)

#: Requested fill densities. Both extremes are included because they produce
#: the degenerate clue sets (all-empty, all-filled lines) the ``(0,)`` marker
#: exists for.
DENSITIES = (0.0, 0.1, 0.25, 0.4, 0.5, 0.6, 0.75, 0.9, 1.0)


@dataclass(frozen=True)
class Case:
    """One generated clue set, and the grid it came from if it still has one."""

    index: int
    size: int
    clues: Clues
    #: The grid the clues were derived from, or ``None`` if the clues were
    #: mutated afterwards and so may no longer describe any grid at all.
    source: list[list[bool]] | None

    def describe(self) -> str:
        return (
            f"case {self.index} ({self.size}x{self.size}): "
            f"rows={self.clues.rows} columns={self.clues.columns}"
        )


def _random_grid(rng: random.Random, size: int, density: float) -> list[list[bool]]:
    """A random square grid at roughly ``density`` filled.

    Drawn here rather than through ``nonogram.sourcing.random_grid.generate``
    because that module enforces the 10x10..30x30 *product* range (AC-003/
    AC-004), and this property needs the small grids the oracle can actually
    enumerate. The draw is still seeded and reproducible, which is the only
    property of it EC-001 depends on.
    """
    return [[rng.random() < density for _ in range(size)] for _ in range(size)]


def _mutate(rng: random.Random, clue_set: tuple[tuple[int, ...], ...], size: int) -> tuple[tuple[int, ...], ...]:
    """Perturb one line's clue, so the corpus is not only satisfiable sets.

    Clues derived from a real grid always have at least one solution, and a
    corpus of only those would never exercise the "solver says 1, truth says
    0" half of EC-001. Mutation produces clue sets that are unsatisfiable,
    newly ambiguous, or occasionally still fine — the test does not care
    which, because the oracle decides the truth for each one.
    """
    lines = list(clue_set)
    index = rng.randrange(len(lines))
    runs = list(lines[index])
    choice = rng.randrange(3)
    if choice == 0 and runs != [0]:  # lengthen or shorten one run
        position = rng.randrange(len(runs))
        runs[position] = max(1, runs[position] + rng.choice((-1, 1)))
    elif choice == 1:  # add a run
        runs = [run for run in runs if run] + [rng.randint(1, max(1, size // 2))]
    else:  # drop a run, possibly emptying the line
        runs = [run for run in runs if run]
        if runs:
            runs.pop(rng.randrange(len(runs)))
    lines[index] = tuple(runs) if runs else (0,)
    return tuple(lines)


def _corpus(count: int) -> list[Case]:
    """``count`` reproducible cases, cycling the sizes so all are covered.

    Roughly two in five cases are mutated. The rest keep the clues their grid
    produced, which is what lets the round-trip test assert something stronger
    than "the count is right".
    """
    rng = random.Random(SEED)
    cases: list[Case] = []
    for index in range(count):
        size = SIZES[index % len(SIZES)]
        grid = _random_grid(rng, size, rng.choice(DENSITIES))
        rows, columns = compute_clues(grid)
        if rng.random() < 0.4:
            if rng.random() < 0.5:
                rows = _mutate(rng, rows, size)
            else:
                columns = _mutate(rng, columns, size)
            cases.append(Case(index, size, Clues(rows, columns), None))
        else:
            cases.append(Case(index, size, Clues(rows, columns), grid))
    return cases


#: How many cases actually run. Comfortably above :data:`REQUIRED_CASES`
#: because the whole corpus — solver plus oracle, both — costs under two
#: seconds, so the checkpoint's floor is not also the ceiling: the extra cases
#: are free evidence for the one mandatory constraint in the model.
CASE_COUNT = 2400

#: Built once at import: the corpus is a pure function of ``SEED``, and both
#: tests run over the same cases so a failure in one is diagnosable from the
#: other.
CASES = _corpus(CASE_COUNT)


def test_never_false_positive_uniqueness() -> None:
    """EC-001: the solver's count agrees with the brute-force oracle, always.

    The property EC-001 states is one-directional — never report 1 when the
    truth is not 1 — but the oracle makes full agreement checkable, so full
    agreement is what is asserted: a solver that reports 2 for a unique puzzle
    is also broken (it would make CARD-005's loop discard good puzzles
    forever), and catching it here is free.

    Both sides are capped at 2, since that is the answer FR-006 defines and
    the point past which neither implementation keeps counting.
    """
    assert len(CASES) >= REQUIRED_CASES, (
        f"EC-001's increment-1 checkpoint requires >= {REQUIRED_CASES} cases, "
        f"the corpus has {len(CASES)}"
    )

    for case in CASES:
        rows, columns = case.clues
        expected = count_solutions(rows, columns, limit=MANY)
        result = solve(rows, columns)

        assert result.solution_count == expected, (
            f"{case.describe()}: solver said {result.solution_count}, "
            f"brute-force oracle said {expected}"
        )
        if result.solution_count == 0:
            assert result.solution is None, (
                f"{case.describe()}: no solution exists but a grid was returned"
            )
        else:
            assert result.solution is not None, (
                f"{case.describe()}: {result.solution_count} solution(s) "
                f"reported but no grid returned"
            )
            derived = compute_clues(result.solution)
            assert (derived.rows, derived.columns) == (rows, columns), (
                f"{case.describe()}: the returned grid encodes to "
                f"rows={derived.rows} columns={derived.columns}"
            )


def test_finds_the_source_grid() -> None:
    """ADR-0014's free-direction check: a grid's own clues are always solvable.

    Needs no oracle at all — the grid the clues came from is a witness that at
    least one solution exists — so this is the direction that would scale to
    any size (see the module docstring on why the corpus still stops at 8x8).
    When the solver reports uniqueness, the one solution can only be that
    grid, and that is asserted rather than assumed: a solver returning *some*
    valid grid while a different one also fits would be a CON-005 violation
    dressed up as a success.
    """
    checked = 0
    for case in CASES:
        if case.source is None:
            continue  # mutated clues: no grid is guaranteed to satisfy them
        checked += 1
        rows, columns = case.clues
        result = solve(rows, columns)

        assert result.solution_count >= 1, (
            f"{case.describe()}: reported unsolvable, but it was derived from "
            f"{case.source}"
        )
        if result.is_unique:
            assert result.solution == case.source, (
                f"{case.describe()}: reported a unique solution that is not "
                f"the grid the clues came from"
            )

    assert checked >= REQUIRED_CASES // 2, (
        f"only {checked} unmutated cases in the corpus; the round-trip "
        f"direction needs a meaningful share of it"
    )
