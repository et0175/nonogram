"""EC-011 / EC(ADR-0029/R3) — properties of CARD-073's solver additions.

    EC-011  PropertyTest_Solver_WitnessesDisagreeOnlyInsideUndecidedMask
            -> test_witnesses_disagree_only_inside_the_undecided_mask
    ADR-0029/R3  PropertyTest_Solver_RungTagsDeterministicPerClueSet
            -> test_rung_tags_are_deterministic_per_clue_set

EC-011, in full: for any clue set on which the solver reports MANY, the two
witnesses it returns are distinct cell by cell (TERM-009), each re-encodes
exactly to the input clues, and every cell on which they disagree is a member
of the first-fixed-point undecided mask — because propagation only ever writes
cells that *every* solution agrees on. It is a statement about every clue set,
not about the two examples AC-107 and AC-108 draw, which is why it is here and
not in ``tests/test_solver_witnesses_and_rungs.py``.

The corpus, house style (no ``hypothesis`` — it is not in the dependency
baseline): built by hand from stdlib ``random.Random`` under one module seed,
with the case count asserted *inside* each test so the corpus cannot silently
shrink to nothing and leave a green test behind.

The re-encoding half deliberately goes through ``nonogram.clues`` — COMP-004's
encoder, which ``solver/`` may not import (ADR-0007) and which therefore
checks the solver's native ``mask_runs`` instead of agreeing with it by
construction. Same reasoning as EC-001's oracle next door: an independent
second implementation, not a second call.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass

import pytest

from nonogram.clues import Clues, compute_clues
from nonogram.solver import MANY, RUNG_ORDER, solve

#: One seed for the whole module: change it and both corpora change wholesale,
#: which is a deliberate act and not a side effect of running the suite twice.
SEED = 20260912

#: EC-011's floor, from the card.
REQUIRED_AMBIGUOUS_CASES = 200

#: How many ambiguous cases are actually collected. Comfortably above the
#: floor, because a MANY verdict is the cheapest verdict the solver produces —
#: it stops at the second solution — so the margin is close to free.
AMBIGUOUS_CASES = 320

#: The determinism corpus is every verdict, not only MANY, and is sized to the
#: same floor.
CLOCK_CASES = 240

#: Grid edge lengths drawn from. Small on purpose: ambiguity is common at these
#: sizes and every case is settled in well under a millisecond, so the corpus
#: is wide rather than deep.
SIZES = (3, 4, 5, 6, 7, 8, 9, 10)

#: Fill densities. The low end is where switching blocks live, which is what
#: makes a MANY verdict likely; the high end is included so the corpus is not
#: only one shape of ambiguity.
DENSITIES = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.75)


@dataclass(frozen=True)
class Case:
    """One generated clue set and the grid it was derived from."""

    index: int
    size: int
    clues: Clues
    source: list[list[bool]]

    def describe(self) -> str:
        return (
            f"case {self.index} ({self.size}x{self.size}): "
            f"rows={self.clues.rows} columns={self.clues.columns}"
        )


def _random_grid(rng: random.Random, size: int, density: float) -> list[list[bool]]:
    """A random square grid at roughly ``density`` filled.

    Drawn here rather than through ``nonogram.sourcing.random_grid.generate``
    for EC-001's reason: that module enforces the supported 10x10..30x30 range
    (AC-003/AC-004), and this property wants the small grids where ambiguity is
    common and a case costs nothing. The draw is seeded and reproducible, which
    is the only property of it EC-011 depends on.
    """
    return [[rng.random() < density for _ in range(size)] for _ in range(size)]


def _ambiguous_corpus(count: int) -> list[Case]:
    """``count`` reproducible clue sets on which the solver reports MANY.

    Ambiguity is *found*, not forced: grids are drawn and kept only when the
    solver reports more than one solution, so the corpus is a cross-section of
    the ambiguity real candidates carry rather than a family of hand-built
    switching blocks. The draw is bounded so a solver change that made MANY
    rare would fail the case-count assertion in the test rather than hang here.
    """
    rng = random.Random(SEED)
    cases: list[Case] = []
    for index in range(count * 40):
        if len(cases) == count:
            break
        size = SIZES[index % len(SIZES)]
        grid = _random_grid(rng, size, rng.choice(DENSITIES))
        clues = compute_clues(grid)
        if solve(clues.rows, clues.columns).solution_count == MANY:
            cases.append(Case(index, size, clues, grid))
    return cases


def _mixed_corpus(count: int) -> list[Case]:
    """``count`` reproducible clue sets of every verdict, for the clock test."""
    rng = random.Random(SEED + 1)
    cases: list[Case] = []
    for index in range(count):
        size = SIZES[index % len(SIZES)]
        grid = _random_grid(rng, size, rng.choice(DENSITIES))
        cases.append(Case(index, size, compute_clues(grid), grid))
    return cases


#: Built once at import: both corpora are pure functions of :data:`SEED`.
AMBIGUOUS = _ambiguous_corpus(AMBIGUOUS_CASES)
MIXED = _mixed_corpus(CLOCK_CASES)


def test_witnesses_disagree_only_inside_the_undecided_mask() -> None:
    """EC-011: two distinct witnesses, both real, disagreeing only where open.

    The last clause is the load-bearing one, and it is what makes ADR-0024's
    repair well founded: propagation writes only cells that every solution
    agrees on, so anything two solutions disagree about was still open at the
    first fixed point. A solver change that let a deduction outrun that — a
    "deduction" some solution violates — would show up here as a disagreement
    outside the mask long before it showed up as a wrong count.
    """
    assert len(AMBIGUOUS) >= REQUIRED_AMBIGUOUS_CASES, (
        f"corpus shrank to {len(AMBIGUOUS)} ambiguous cases, below EC-011's "
        f"floor of {REQUIRED_AMBIGUOUS_CASES}"
    )

    for case in AMBIGUOUS:
        result = solve(case.clues.rows, case.clues.columns)
        context = case.describe()

        assert result.solution_count == MANY, context
        assert result.solution is not None, context
        assert result.second_witness is not None, context
        assert len(result.witnesses) == MANY, context

        first, second = result.solution, result.second_witness

        # Distinct, cell by cell (TERM-009) — not merely two objects.
        disagreements = {
            (row, column)
            for row, (left, right) in enumerate(zip(first, second, strict=True))
            for column, (a, b) in enumerate(zip(left, right, strict=True))
            if a != b
        }
        assert disagreements, f"{context}: the two witnesses are the same grid"

        # Each is a real solution of the clues that were asked about.
        for index, witness in enumerate(result.witnesses):
            encoded = compute_clues(witness)
            assert encoded.rows == case.clues.rows, f"{context}: witness {index} rows"
            assert encoded.columns == case.clues.columns, (
                f"{context}: witness {index} columns"
            )

        # And every disagreement lies inside the first fixed point's mask.
        open_cells = {
            (row, column)
            for row, line in enumerate(result.undecided_mask)
            for column, flag in enumerate(line)
            if flag
        }
        assert disagreements <= open_cells, (
            f"{context}: witnesses disagree at "
            f"{sorted(disagreements - open_cells)}, which line logic claimed to "
            f"have settled"
        )


def test_rung_tags_are_deterministic_per_clue_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """EC(ADR-0029/R3): same clues, same tags, under a dilated clock.

    No clock reading may enter a rung tag or the rung list (CON-014, NFR-007,
    guardrail G-5), which is what makes ADR-0029's grade the same on a fast
    machine and a slow one. The check runs the whole corpus twice, the second
    time with both clocks the solver can reach multiplied by a thousand, and
    demands the classification be identical — while ``elapsed_seconds``, the
    one field that is *allowed* to move, is deliberately not compared.

    The dilation is applied to the real clocks rather than to a frozen fake, so
    both stay monotonic and nothing that reads the clock for its own reasons
    misbehaves for the duration.
    """
    assert len(MIXED) >= REQUIRED_AMBIGUOUS_CASES, (
        f"corpus shrank to {len(MIXED)} cases"
    )

    def classification(result: object) -> tuple[object, ...]:
        return (
            result.solution_count,  # type: ignore[attr-defined]
            result.solution,  # type: ignore[attr-defined]
            result.second_witness,  # type: ignore[attr-defined]
            result.undecided_mask,  # type: ignore[attr-defined]
            result.rung_tags,  # type: ignore[attr-defined]
            dict(result.signals.rung_cells),  # type: ignore[attr-defined]
            result.signals.rungs,  # type: ignore[attr-defined]
            result.signals.branch_nodes,  # type: ignore[attr-defined]
        )

    baseline = [classification(solve(case.clues.rows, case.clues.columns)) for case in MIXED]

    real_perf = time.perf_counter
    real_monotonic = time.monotonic
    monkeypatch.setattr(time, "perf_counter", lambda: real_perf() * 1000.0)
    monkeypatch.setattr(time, "monotonic", lambda: real_monotonic() * 1000.0)

    for case, expected in zip(MIXED, baseline, strict=True):
        assert classification(solve(case.clues.rows, case.clues.columns)) == expected, (
            case.describe()
        )


def test_every_tag_is_a_rung_of_the_ladder() -> None:
    """Nothing but ADR-0029's four names ever appears as a tag.

    A cheap totality check over both corpora: the enum is fixed by ADR-0029 and
    a fifth name appearing (``guess``, say, which CARD-072 appends downstream
    and the solver must not) would change what every consumer of the list
    means.
    """
    seen: set[str] = set()
    for case in (*AMBIGUOUS[:80], *MIXED[:80]):
        result = solve(case.clues.rows, case.clues.columns)
        for line in result.rung_tags:
            for tag in line:
                if tag is not None:
                    seen.add(tag)
        assert set(result.signals.rung_cells) == set(RUNG_ORDER), case.describe()
    assert seen, "no cell was tagged anywhere in either corpus"
    assert seen <= set(RUNG_ORDER), sorted(seen - set(RUNG_ORDER))
