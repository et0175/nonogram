"""EC-001 / CON-005: the uniqueness check never produces a false positive.

    PropertyTest_Solver_NeverFalsePositiveUniqueness
        -> test_never_false_positive_uniqueness      (ADR-0014 direction 1)
        -> test_finds_the_source_grid                (ADR-0014 direction 2)
    PropertyTest_SolverUniqueness_HoldsUnderGivens
        -> test_uniqueness_holds_under_givens        (CARD-214, AC-6)

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

The same property, under given cells (CARD-214)
-----------------------------------------------
``solve`` answers a second question since CARD-214 — *how many solutions are
there given that these cells are known?* — and CON-005 is a statement about the
uniqueness check, not about one of its two questions. So the property is
re-established for the seeded case, over its own corpus of ``(clues, givens)``
pairs, against the same oracle: ``count_solutions`` learned ``givens`` as its
own filter over its own enumeration and still imports nothing from
``nonogram.solver``, which is what keeps the cross-check a cross-check.

The seeded corpus is built to contain the three populations the unseeded one
cannot reach, because the engineering constraint is "for every (clues, givens)
pair" and not "for the pairs the generation path happens to produce":

* reveals taken from the grid the clues came from — the pairs the reveal policy
  actually makes, where the count can only fall from the unseeded one;
* reveals **contradicting** that grid, so the count collapses to 0 or to
  something else entirely — the seeded shape of EC-001's "solver says 1, truth
  says 0" half, and the only way to exercise it;
* reveals on top of *mutated* clues, where no grid is guaranteed to satisfy the
  clues at all.

plus the two degenerate ends: nothing revealed (which must answer exactly what
the unseeded call answers) and everything revealed (which must answer 1 for a
grid's own clues and 0 for a contradicted cell).

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


# --------------------------------------------------------------------------
# CARD-214 / AC-6 — PropertyTest_SolverUniqueness_HoldsUnderGivens
#
# EC(CON-005): the seeded solve holds the no-false-positive property for every
# (clues, givens) pair, not only for the pairs the generation path produces.
# --------------------------------------------------------------------------

#: AC-6's floor. Asserted inside the test, like :data:`REQUIRED_CASES`.
REQUIRED_GIVEN_CASES = 500

#: One seed for the seeded-case corpus, separate from :data:`SEED` so that the
#: two corpora move independently: re-pinning one must not silently reshuffle
#: the other's thousands of cases.
GIVEN_SEED = 20261013

#: Edge lengths for the seeded corpus. Shorter at the top than :data:`SIZES`
#: because a *contradicted* given can make the oracle's row-candidate filter
#: empty only after the product has been set up, and 2..6 already covers every
#: shape of line-placement bug while keeping the whole corpus inside a couple
#: of seconds. 1x1 is dropped for one reason only: there is no interesting
#: partial assignment of a single cell that the "everything revealed" case does
#: not already cover.
GIVEN_SIZES = (2, 3, 4, 5, 6)

#: What fraction of the cells a case reveals, drawn per case. ``0.0`` and
#: ``1.0`` are the two degenerate ends and are deliberately in the list rather
#: than special-cased: nothing revealed must answer exactly what the unseeded
#: call answers, and everything revealed must answer 1 or 0 and never ``MANY``.
#:
#: Weighted toward the sparse end — ``0.0`` and ``0.1`` appear twice — and that
#: weighting is the point rather than taste. A reveal is a very strong
#: constraint at these sizes, so a uniform draw leaves hardly any case whose
#: *truth* is ``MANY``, and "never report 1 where the truth is >= 2" is the
#: half of EC-001 that needs those cases. Measured: 55 of 1500 under a uniform
#: draw against 94 of 1500 here, with 450 cases at 0 and 956 at 1. The floors
#: asserted in the test are what keeps the balance from drifting back.
GIVEN_SHARES = (0.0, 0.0, 0.1, 0.1, 0.2, 0.35, 0.5, 0.75, 1.0)


@dataclass(frozen=True)
class GivenCase:
    """One ``(clues, givens)`` pair, and how it was built."""

    index: int
    size: int
    clues: Clues
    givens: list[list[bool | None]]
    #: The grid the clues came from, or ``None`` when the clues were mutated.
    source: list[list[bool]] | None
    #: ``True`` when at least one revealed cell was flipped against
    #: :attr:`source`, so the pair is deliberately contradictory.
    contradicted: bool

    def describe(self) -> str:
        return (
            f"given-case {self.index} ({self.size}x{self.size}, "
            f"contradicted={self.contradicted}): rows={self.clues.rows} "
            f"columns={self.clues.columns} givens={self.givens}"
        )


def _givens_from(
    rng: random.Random,
    grid: list[list[bool]],
    share: float,
    flip: bool,
) -> tuple[list[list[bool | None]], bool]:
    """Reveal ``share`` of ``grid``'s cells, optionally flipping some of them.

    Returns the assignment and whether anything was actually flipped — a
    ``flip`` request on a case that revealed nothing cannot contradict
    anything, and claiming otherwise would mislabel the case in a failure
    message.
    """
    givens: list[list[bool | None]] = [[None] * len(row) for row in grid]
    contradicted = False
    for row_index, row in enumerate(grid):
        for column_index, value in enumerate(row):
            if rng.random() >= share:
                continue
            if flip and rng.random() < 0.5:
                givens[row_index][column_index] = not value
                contradicted = True
            else:
                givens[row_index][column_index] = value
    return givens, contradicted


def _given_corpus(count: int) -> list[GivenCase]:
    """``count`` reproducible ``(clues, givens)`` pairs, cycling the sizes.

    The mix is stated as probabilities rather than as counts so that changing
    ``count`` does not change what the corpus is *about*: roughly a quarter of
    the cases contradict their grid, roughly a fifth mutate the clues, and the
    rest are the consistent pairs the reveal policy itself produces.
    """
    rng = random.Random(GIVEN_SEED)
    cases: list[GivenCase] = []
    for index in range(count):
        size = GIVEN_SIZES[index % len(GIVEN_SIZES)]
        grid = _random_grid(rng, size, rng.choice(DENSITIES))
        rows, columns = compute_clues(grid)
        givens, contradicted = _givens_from(
            rng, grid, rng.choice(GIVEN_SHARES), flip=rng.random() < 0.25
        )
        source: list[list[bool]] | None = grid
        if rng.random() < 0.2:
            if rng.random() < 0.5:
                rows = _mutate(rng, rows, size)
            else:
                columns = _mutate(rng, columns, size)
            source = None
        cases.append(
            GivenCase(
                index=index,
                size=size,
                clues=Clues(rows, columns),
                givens=givens,
                source=source,
                contradicted=contradicted,
            )
        )
    return cases


#: How many seeded cases actually run — comfortably above
#: :data:`REQUIRED_GIVEN_CASES` for the reason :data:`CASE_COUNT` is above its
#: own floor: solver plus oracle cost a couple of seconds for the whole corpus,
#: so the checkpoint's floor is not also the ceiling.
GIVEN_CASE_COUNT = 1500

GIVEN_CASES = _given_corpus(GIVEN_CASE_COUNT)


def test_uniqueness_holds_under_givens() -> None:
    """EC(CON-005) under given cells: the seeded count agrees with the oracle.

    The same full agreement the unseeded direction asserts, and for the same
    reason — a solver that reports ``MANY`` for a seeded clue set with one
    solution would make the reveal policy give away cells forever — plus the
    two things only the seeded question can get wrong:

    * a counted witness must **agree with every revealed cell**. A solver that
      seeded the wrong bit, or let a cell be overwritten, would still return a
      grid that re-encodes to the clues, so the clue round-trip cannot see
      this; it is the whole content of "the givens were actually applied".
    * revealing *nothing* must answer exactly what the unseeded call answers,
      byte for byte on the count. That is guardrail G-3 as a property rather
      than as a promise: the seeded path and the default path are the same
      search, and an all-``None`` assignment is the default one.
    """
    assert len(GIVEN_CASES) >= REQUIRED_GIVEN_CASES, (
        f"AC-6 requires >= {REQUIRED_GIVEN_CASES} (grid, givens) pairs, the "
        f"corpus has {len(GIVEN_CASES)}"
    )
    # The corpus has to contain the populations the docstring claims, or the
    # count above is just a number: a corpus that drifted into "all consistent
    # reveals" would assert the easy half of the property only.
    contradicted = sum(1 for case in GIVEN_CASES if case.contradicted)
    mutated = sum(1 for case in GIVEN_CASES if case.source is None)
    empty = sum(1 for case in GIVEN_CASES if not any(
        value is not None for row in case.givens for value in row
    ))
    full = sum(1 for case in GIVEN_CASES if all(
        value is not None for row in case.givens for value in row
    ))
    assert contradicted >= 100, f"only {contradicted} contradictory pairs"
    assert mutated >= 100, f"only {mutated} mutated-clue pairs"
    assert empty >= 50, f"only {empty} pairs reveal nothing"
    assert full >= 50, f"only {full} pairs reveal everything"

    truths: dict[int, int] = {0: 0, 1: 0, MANY: 0}
    for case in GIVEN_CASES:
        rows, columns = case.clues
        expected = count_solutions(rows, columns, limit=MANY, givens=case.givens)
        truths[expected] += 1
        result = solve(rows, columns, givens=case.givens)

        assert result.solution_count == expected, (
            f"{case.describe()}: solver said {result.solution_count}, "
            f"brute-force oracle said {expected}"
        )
        if result.solution_count == 0:
            assert result.solution is None, (
                f"{case.describe()}: no solution exists but a grid was returned"
            )
            continue

        for witness in result.witnesses:
            derived = compute_clues(witness)
            assert (derived.rows, derived.columns) == (rows, columns), (
                f"{case.describe()}: a witness encodes to rows="
                f"{derived.rows} columns={derived.columns}"
            )
            for row_index, given_row in enumerate(case.givens):
                for column_index, value in enumerate(given_row):
                    assert value is None or witness[row_index][column_index] == value, (
                        f"{case.describe()}: a counted witness has "
                        f"({row_index}, {column_index}) = "
                        f"{witness[row_index][column_index]} against a given "
                        f"of {value}"
                    )

    # The floors that matter most, taken from the ORACLE's answers rather than
    # from the corpus's construction: EC-001 forbids reporting 1 where the
    # truth is 0 or >= 2, so a corpus whose truths were all 1 would assert
    # nothing about the property it names, however many cases it had.
    assert truths[0] >= 100, f"only {truths[0]} pairs truly have no solution"
    assert truths[MANY] >= 50, f"only {truths[MANY]} pairs are truly ambiguous"
    assert truths[1] >= 100, f"only {truths[1]} pairs truly have one solution"

    # G-3 as a property: with nothing revealed the seeded call *is* the default
    # call. Checked over the whole corpus rather than on a sample, because it
    # is the claim every pre-CARD-214 verdict on record rests on.
    for case in GIVEN_CASES:
        rows, columns = case.clues
        blank: list[list[bool | None]] = [[None] * case.size for _ in range(case.size)]
        assert solve(rows, columns, givens=blank).solution_count == (
            solve(rows, columns).solution_count
        ), f"{case.describe()}: an empty givens changed the count"


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
