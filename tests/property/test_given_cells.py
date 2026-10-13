"""EC(ADR-0024/R4): the reveal choice is pure, and the same everywhere.

    PropertyTest_GivenCells_DeterministicForAGrid
        -> test_given_cells_deterministic_for_a_grid        (CARD-214, AC-7)
        -> test_given_cells_deterministic_across_processes  (the "any process"
                                                             half)
    PropertyTest_GivenCells_AlwaysMakeThePuzzleUnique
        -> test_given_cells_always_make_the_puzzle_unique   (AC-1, as a
                                                             property)

AC-7 asks that ``choose_givens`` return "the identical set in the identical
order" for a grid, "any number of times in any process". Those are two
different claims and they need two different checks.

*Any number of times* is a claim about state: a chooser that consulted an rng,
a clock, a module-level cache or a mutable default would answer differently on
a second call. Checked by calling it repeatedly over a corpus, with the global
``random`` module deliberately disturbed in between so that an accidental
``random.random()`` anywhere in the path would show up as a divergence rather
than as a coincidence.

*In any process* is a claim about host state, and the one that in-process
repetition cannot make: ``PYTHONHASHSEED`` changes the iteration order of every
set and dict in the interpreter, so a choice that depended on one — and
"collect the disagreeing cells, take one" is exactly the shape that does — is
stable within a run and unstable across runs. So the second test re-runs the
chooser in a child interpreter under two different hash seeds and compares.

The third test is AC-1 widened from its one example to the whole corpus: it is
not enough that the chooser be *deterministic*, it has to be deterministic and
right. Every case's result is re-verified by a fresh seeded solve, and every
revealed cell is checked against the source grid — which, together with the
oracle cross-check in ``tests/property/test_solver_uniqueness.py``, is the
whole of "the puzzle the user gets has the picture's own answer".

No ``hypothesis`` (ADR-0006's baseline is closed): a seeded ``random.Random``
plus the hand-picked shapes below, with the case count asserted inside the
tests so the corpus cannot silently shrink.
"""

from __future__ import annotations

import os
import random
import subprocess
import sys
from pathlib import Path

from nonogram.clues import compute_clues
from nonogram.solver import MANY, choose_givens, revealed_cells, solve

#: One seed for the whole module, like the other property corpora here.
SEED = 20261013

#: AC-7's floor, asserted in the tests rather than left to a comment.
REQUIRED_CASES = 200

#: Edge lengths. Big enough that a random grid is genuinely ambiguous (the
#: chooser has to do several rounds, so determinism is a claim about a sequence
#: of choices rather than about one), small enough that a few hundred of them
#: solve in seconds.
SIZES = (5, 6, 7, 8, 9)

#: Fill densities. The middle of the range is where ambiguity lives; the ends
#: are in for the degenerate clue sets and come back needing no reveal at all,
#: which is a case determinism has to cover too.
DENSITIES = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8)

#: The cap used throughout: generous enough that no case in the corpus is
#: refused for the cap rather than answered, since what is being checked here
#: is the *choice*, not the bound. The bound's own boundary is pinned in
#: ``tests/test_given_cells.py``.
CAP = 40

#: How many grids the corpus holds. Comfortably above :data:`REQUIRED_CASES`
#: for the usual reason — the whole corpus costs a couple of seconds, so the
#: floor need not also be the ceiling.
CASE_COUNT = 300


def _grid(rng: random.Random, size: int, density: float) -> list[list[bool]]:
    """A random square grid at roughly ``density`` filled.

    Drawn here rather than through ``sourcing.random_grid.generate`` for the
    reason ``test_solver_uniqueness.py`` gives: that module enforces CON-011's
    10..30 range, and this property needs grids small enough to run hundreds
    of multi-solve chooser runs over.
    """
    return [[rng.random() < density for _ in range(size)] for _ in range(size)]


def _corpus(count: int) -> list[tuple[int, list[list[bool]]]]:
    """``count`` reproducible ``(index, grid)`` pairs, cycling the sizes."""
    rng = random.Random(SEED)
    return [
        (index, _grid(rng, SIZES[index % len(SIZES)], rng.choice(DENSITIES)))
        for index in range(count)
    ]


CASES = _corpus(CASE_COUNT)


def _chosen(grid: list[list[bool]]) -> tuple[tuple[int, int, bool], ...]:
    """The chooser's answer for ``grid``'s own clues, as cells."""
    rows, columns = compute_clues(grid)
    return revealed_cells(choose_givens(grid, rows, columns, cap=CAP))


def test_given_cells_deterministic_for_a_grid() -> None:
    """AC-7: the same grid gives the same cells, however many times it is asked.

    Three calls rather than two, with the global ``random`` module reseeded
    between them: two calls can agree by luck if something draws from a stream
    that happens to repeat, three under different global states cannot. The
    corpus is asserted to contain real work — most cases needing at least one
    reveal — because a corpus of already-unique grids would make every call
    return the empty tuple and this test vacuous.
    """
    assert len(CASES) >= REQUIRED_CASES, (
        f"AC-7 needs >= {REQUIRED_CASES} grids, the corpus has {len(CASES)}"
    )

    with_reveals = 0
    multi_step = 0
    for index, grid in CASES:
        random.seed(index)
        first = _chosen(grid)
        random.seed(index * 7919 + 13)
        second = _chosen(grid)
        random.seed()  # back to OS entropy, the least predictable state there is
        third = _chosen(grid)

        assert first == second == third, (
            f"case {index} ({len(grid)}x{len(grid)}) chose {first}, then "
            f"{second}, then {third}"
        )
        if first:
            with_reveals += 1
        if len(first) > 1:
            multi_step += 1

    assert with_reveals >= REQUIRED_CASES // 2, (
        f"only {with_reveals} of {len(CASES)} grids needed any reveal at all; "
        f"the corpus has drifted to grids the chooser does nothing for"
    )
    assert multi_step >= 50, (
        f"only {multi_step} grids needed more than one reveal; determinism "
        f"over a *sequence* of choices is what this property is about"
    )


def test_given_cells_always_make_the_puzzle_unique() -> None:
    """AC-1 over the whole corpus: the answer is unique, and it is this grid's.

    Both halves, on every case:

    * a **fresh** seeded solve of the grid's clues under the chosen reveals
      reports exactly 1, and the one solution it returns is the grid. Not the
      chooser's own last solve — this test runs its own, which is the same
      thing the orchestrator's policy does before accepting a puzzle;
    * every revealed cell holds the grid's own value, so the puzzle's answer is
      the picture rather than something made unique at the picture's expense.

    And the economy claim, which is why a cap of 5% is a refusal threshold and
    not a target: the cells revealed stay a small fraction of the grid.
    """
    assert len(CASES) >= REQUIRED_CASES

    worst_share = 0.0
    for index, grid in CASES:
        rows, columns = compute_clues(grid)
        givens = choose_givens(grid, rows, columns, cap=CAP)
        cells = revealed_cells(givens)

        for row, column, value in cells:
            assert value == grid[row][column], (
                f"case {index}: ({row}, {column}) revealed as {value}, grid "
                f"holds {grid[row][column]}"
            )

        fresh = solve(rows, columns, givens=givens)
        assert fresh.solution_count == 1, (
            f"case {index}: a fresh seeded solve said "
            f"{fresh.solution_count} for {len(cells)} revealed cell(s)"
        )
        assert fresh.solution == grid, (
            f"case {index}: the unique seeded solution is not the source grid"
        )
        if not cells:
            # Nothing revealed means the clues were already unique, which the
            # unseeded solve must agree with — otherwise the chooser skipped
            # work rather than finding none to do.
            assert solve(rows, columns).solution_count == 1, (
                f"case {index}: nothing revealed for an ambiguous grid"
            )
        else:
            assert solve(rows, columns).solution_count == MANY, (
                f"case {index}: cells revealed for a grid that did not need them"
            )
        worst_share = max(worst_share, len(cells) / (len(grid) ** 2))

    # Recorded as an assertion rather than a comment so the number cannot rot:
    # if a change to the solver's branch order started needing a third of the
    # grid revealed, that is a finding about the policy's cap and not a detail.
    assert worst_share <= 0.35, f"worst case revealed {worst_share:.0%} of a grid"


#: The child-process program for the cross-process check. Prints one line per
#: grid, so the parent compares text and needs no serialization protocol.
_CHILD = """
import json, sys
from nonogram.clues import compute_clues
from nonogram.solver import choose_givens, revealed_cells
for grid in json.loads(sys.argv[1]):
    rows, columns = compute_clues(grid)
    cells = revealed_cells(choose_givens(grid, rows, columns, cap=%d))
    print(json.dumps(cells))
""" % CAP


def _in_child(grids: list[list[list[bool]]], hash_seed: str) -> list[str]:
    """Run the chooser over ``grids`` in a child interpreter.

    ``PYTHONHASHSEED`` is the whole point of the subprocess: it is the one
    piece of host state that changes set and dict iteration order, it cannot
    be changed inside a running interpreter, and a choice that depended on it
    would be perfectly stable within a process and silently
    machine-dependent across them.
    """
    import json

    environment = dict(os.environ)
    environment["PYTHONHASHSEED"] = hash_seed
    repository = Path(__file__).resolve().parents[2]
    environment["PYTHONPATH"] = str(repository / "src")
    completed = subprocess.run(
        [sys.executable, "-c", _CHILD, json.dumps(grids)],
        capture_output=True,
        text=True,
        check=True,
        env=environment,
        cwd=repository,
    )
    return completed.stdout.strip().splitlines()


def test_given_cells_deterministic_across_processes() -> None:
    """AC-7's "in any process": two hash seeds, two child interpreters, one
    answer — and the same answer this process gives.

    A sample of the corpus rather than all of it: the claim is about whether
    the choice can depend on host state at all, which one grid needing several
    reveals already answers, and a few hundred subprocess-borne grids would
    buy nothing but seconds. The sample is the first few cases that need more
    than one reveal, so each one is a *sequence* of choices.
    """
    import json

    sample = [grid for _, grid in CASES if len(_chosen(grid)) > 1][:6]
    assert len(sample) == 6, "the corpus should hold several multi-reveal grids"

    here = [json.dumps(_chosen(grid)) for grid in sample]
    assert _in_child(sample, "0") == here
    assert _in_child(sample, "1") == here
