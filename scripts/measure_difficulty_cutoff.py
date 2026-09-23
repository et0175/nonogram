"""CARD-137 step 1 — measure where the medium/hard cutoff would have to sit.

Not a test and not part of the package: a one-shot measurement the owner reads
before choosing ADR-0005's second cutoff constant. It is committed because the
number it is about to move is a *calibration*, and a calibration nobody can
re-run is a guess with a decimal point.

What it measures
----------------
A seeded corpus of real puzzles built through the existing generator —
``orchestrator.generate`` in random mode, the same path the admin's batch
generation uses — scored through the existing scoring path
(``difficulty.score_difficulty`` on the signals of the one verifying solve).
No solver re-entry, no new entry point, nothing re-derived here: every score in
the table is the score the pipeline would have stored for that puzzle.

Then, for each *candidate* medium/hard cutoff, it reports what the three tiers'
shares would become — overall and per the book's own longest-side buckets
(FR-034: <=15, 16-20, 21-25, 26-30).

The candidate cutoffs are applied here as plain arithmetic on the score rather
than through :func:`nonogram.difficulty.classify`, deliberately. ``classify``
is the single classifier (guardrail G-1) and it knows exactly one cutoff — the
one in force. A what-if table is a question about cutoffs that do *not* exist
yet, so it cannot be asked through the classifier without giving the classifier
a second cutoff to know about. The easy/medium boundary is read from
``difficulty.EASY_MAX_SCORE`` rather than restated, and the row for the cutoff
currently in force is cross-checked against ``classify`` on every puzzle, so an
arithmetic drift between this script and the module fails loudly here
(``--self-check``, on by default).

Reproducibility
---------------
One ``random.Random`` seeds the whole run: every request's seed is drawn from
it, so the corpus replays exactly on any machine (ADR-0015 puts all generation
randomness under the request seed). The corpus size is asserted, the same way
the seeded corpora in ``tests/property/`` assert theirs, so a plan edit that
quietly shrinks the sample fails instead of reporting a thinner table.

Usage::

    ./.venv/bin/python scripts/measure_difficulty_cutoff.py
    ./.venv/bin/python scripts/measure_difficulty_cutoff.py --draws 4 --json out.json
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

from nonogram import orchestrator
from nonogram.difficulty import EASY_MAX_SCORE, MEDIUM_MAX_SCORE, SCORE_MAX, Tier, classify
from nonogram.errors import NonogramError
from nonogram.limits import MAX_SIZE, MIN_SIZE
from nonogram.orchestrator import GenerationRequest

#: The seed of the whole corpus. One number, so "rerun it" is a complete
#: instruction.
CORPUS_SEED = 20260923

#: The book's longest-side buckets (FR-034), as ``(label, low, high)`` with both
#: ends inclusive. They span :data:`MIN_SIZE`..:data:`MAX_SIZE` exactly; the
#: bottom and top are written from ``limits`` rather than as 10 and 30.
BUCKETS: tuple[tuple[str, int, int], ...] = (
    (f"<={15}", MIN_SIZE, 15),
    ("16-20", 16, 20),
    ("21-25", 21, 25),
    (f"26-{MAX_SIZE}", 26, MAX_SIZE),
)

#: Sizes sampled in each bucket — three per bucket, including both ends of the
#: supported range so the table cannot be a statement about the middle only.
SIZES: tuple[int, ...] = (
    MIN_SIZE,
    13,
    15,
    16,
    18,
    20,
    22,
    24,
    25,
    26,
    28,
    MAX_SIZE,
)

#: Requested densities, per size. 50 is the value ``orchestrator.generate_batch``
#: hardcodes, so it is in every row; the rest spread around it.
#:
#: The list narrows as the grid grows, and that is measured rather than
#: preferred: below ~50% a large random draw is overwhelmingly ambiguous, so the
#: request spends ADR-0011's whole 30 s deadline or exhausts POL-001's retry
#: budget and produces no puzzle at all. Measured on this machine, 3 requests
#: each: density 35 produced nothing at any size from 20x20 up; density 45
#: produced nothing at 25x25, 28x28 or 30x30 (9 of 9 ``SolverTimeout``);
#: density 48 produced 1 of 3 at 30x30 and 2 of 3 at 28x28. Sampling there
#: would add half an hour of wall clock and almost no puzzles, because those
#: grids are not reachable from generation in the first place — a bias worth
#: naming, since they are also the grids that would score hardest. Densities
#: *above* the list are cheap and stay in it at every size.
DENSITIES_BY_SIZE: tuple[tuple[int, tuple[int, ...]], ...] = (
    (22, (45, 48, 50, 52, 55, 60, 65, 70, 75)),
    (26, (48, 50, 52, 55, 60, 65, 70, 75)),
    (MAX_SIZE, (50, 52, 55, 60, 65, 70, 75)),
)

#: Requests per (size, density) cell.
DRAWS_PER_CELL = 10

#: The floor the corpus asserts, the way ``tests/property/`` corpora do. Well
#: under the plan's own yield so an ordinary miss does not trip it, and well
#: above CARD-137's AC floor of 200 line-solvable puzzles.
MIN_CORPUS = 400

#: The medium/hard cutoffs the table asks about. CARD-137 names the first four;
#: the two ends are there to show which way the curve is moving.
CANDIDATE_CUTOFFS: tuple[float, ...] = (70.0, 75.0, 80.0, 85.0, 90.0, 95.0)


def _densities_for(size: int) -> tuple[int, ...]:
    """The densities sampled at ``size`` — the first row that covers it."""
    for ceiling, densities in DENSITIES_BY_SIZE:
        if size <= ceiling:
            return densities
    raise AssertionError(f"no density row covers size {size}")  # pragma: no cover


def _bucket_for(size: int) -> str:
    """FR-034's longest-side bucket label for a square grid of side ``size``."""
    for label, low, high in BUCKETS:
        if low <= size <= high:
            return label
    raise AssertionError(f"size {size} is outside the supported range")  # pragma: no cover


@dataclass(frozen=True, slots=True)
class Row:
    """One scored puzzle, flattened to what the tables need."""

    size: int
    density: int
    seed: int
    score: float
    branch_nodes: int
    rungs: tuple[str, ...]
    seconds: float

    @property
    def bucket(self) -> str:
        return _bucket_for(self.size)


def build_corpus(draws: int, *, verbose: bool = True) -> tuple[list[Row], Counter[str], float]:
    """Generate and score the corpus. Returns ``(rows, failures, seconds)``."""
    rng = random.Random(CORPUS_SEED)
    rows: list[Row] = []
    failures: Counter[str] = Counter()
    started = time.perf_counter()
    for size in SIZES:
        for density in _densities_for(size):
            cell_started = time.perf_counter()
            kept = 0
            for _ in range(draws):
                seed = rng.getrandbits(32)
                request = GenerationRequest(
                    mode="random", width=size, height=size, density=density, seed=seed
                )
                one = time.perf_counter()
                try:
                    puzzle = orchestrator.generate(request)
                except NonogramError as exc:
                    failures[type(exc).__name__] += 1
                    continue
                rows.append(
                    Row(
                        size=size,
                        density=density,
                        seed=seed,
                        score=puzzle.difficulty_score,
                        branch_nodes=puzzle.branch_nodes,
                        rungs=tuple(puzzle.strategies),
                        seconds=time.perf_counter() - one,
                    )
                )
                kept += 1
            if verbose:
                print(
                    f"  {size:>2}x{size:<2} d{density:<3} {kept:>3}/{draws} kept"
                    f"  {time.perf_counter() - cell_started:6.2f}s",
                    file=sys.stderr,
                    flush=True,
                )
    return rows, failures, time.perf_counter() - started


def _tier_for(score: float, cutoff: float) -> Tier:
    """What ``score`` would classify as if the medium/hard cutoff were ``cutoff``.

    The what-if of the module's own band rule, and the reason it is spelled out
    here rather than delegated is in the module docstring above. The easy/medium
    edge is ``difficulty.EASY_MAX_SCORE``, not a literal.
    """
    if score <= EASY_MAX_SCORE:
        return Tier.EASY
    if score <= cutoff:
        return Tier.MEDIUM
    return Tier.HARD


def _shares(rows: list[Row], cutoff: float) -> tuple[Counter[Tier], int]:
    counts: Counter[Tier] = Counter(_tier_for(row.score, cutoff) for row in rows)
    return counts, len(rows)


def _pct(part: int, whole: int) -> str:
    return f"{100.0 * part / whole:5.1f}%" if whole else "    - "


def _self_check(rows: list[Row]) -> None:
    """The row for the cutoff in force must agree with ``classify`` exactly."""
    for row in rows:
        expected = classify(row.score)
        actual = _tier_for(row.score, MEDIUM_MAX_SCORE)
        if expected is not actual:  # pragma: no cover - a drift guard
            raise SystemExit(
                f"self-check failed: score {row.score!r} classifies {expected} "
                f"but this script's arithmetic says {actual}"
            )


def report(rows: list[Row], failures: Counter[str], seconds: float, draws: int) -> None:
    requested = sum(len(_densities_for(size)) for size in SIZES) * draws
    guessers = [row for row in rows if row.branch_nodes > 0]
    graded = [row for row in rows if row.branch_nodes == 0]

    print("\n== corpus ==")
    print(f"seed                 {CORPUS_SEED}")
    print(f"sizes                {', '.join(str(size) for size in SIZES)}")
    print(f"draws per cell       {draws}")
    print(f"requests issued      {requested}")
    print(f"puzzles generated    {len(rows)}")
    print(f"generation failures  {sum(failures.values())}  {dict(failures)}")
    print(f"branched (excluded)  {len(guessers)}")
    print(f"scored (graded)      {len(graded)}")
    print(f"wall clock           {seconds:.1f}s")

    print("\n== raw score histogram (width 5) ==")
    bins: Counter[int] = Counter(int(row.score // 5) * 5 for row in graded)
    widest = max(bins.values(), default=1)
    for low in range(0, int(SCORE_MAX), 5):
        count = bins.get(low, 0)
        if not count:
            continue
        bar = "#" * max(1, round(40 * count / widest))
        print(f"  {low:>3}-{low + 5:<3} {count:>4}  {bar}")
    exact = Counter(round(row.score, 3) for row in graded)
    print("  most common exact scores: ", end="")
    print(", ".join(f"{score}x{count}" for score, count in exact.most_common(5)))

    print("\n== cutoff sweep: easy / medium / hard shares ==")
    groups: list[tuple[str, list[Row]]] = [("overall", graded)]
    groups += [
        (label, [row for row in graded if row.bucket == label]) for label, _, _ in BUCKETS
    ]
    header = f"{'cutoff':>8} | " + " | ".join(f"{label:^22}" for label, _ in groups)
    print(header)
    print("-" * len(header))
    print(f"{'n':>8} | " + " | ".join(f"{len(rows_):^22}" for _, rows_ in groups))
    print("-" * len(header))
    for cutoff in sorted({*CANDIDATE_CUTOFFS, MEDIUM_MAX_SCORE}):
        cells = []
        for _, subset in groups:
            counts, total = _shares(subset, cutoff)
            cells.append(
                f"{_pct(counts[Tier.EASY], total)}"
                f"/{_pct(counts[Tier.MEDIUM], total)}"
                f"/{_pct(counts[Tier.HARD], total)}"
            )
        marker = " *" if cutoff == MEDIUM_MAX_SCORE else "  "
        print(f"{cutoff:>6.0f}{marker} | " + " | ".join(f"{cell:^22}" for cell in cells))
    print("  * = the cutoff currently in force (difficulty.MEDIUM_MAX_SCORE)")

    print("\n== the decision zone: scores above the easy edge, width 2 ==")
    nontrivial = [row for row in graded if row.score > EASY_MAX_SCORE]
    fine: Counter[int] = Counter(int(row.score // 2) * 2 for row in nontrivial)
    widest = max(fine.values(), default=1)
    for low in range(int(EASY_MAX_SCORE) - 1, int(SCORE_MAX), 2):
        count = fine.get(low, 0)
        if not count:
            continue
        bar = "#" * max(1, round(40 * count / widest))
        print(f"  {low:>3}-{low + 2:<3} {count:>4}  {bar}")
    print(f"  n above {EASY_MAX_SCORE:g}: {len(nontrivial)} of {len(graded)}")

    print("\n== medium/hard split among the puzzles that needed non-trivial work ==")
    print("   (score > the easy edge; the easy share is a density question, not a cutoff one)")
    for cutoff in sorted({*CANDIDATE_CUTOFFS, MEDIUM_MAX_SCORE}):
        counts, total = _shares(nontrivial, cutoff)
        marker = " *" if cutoff == MEDIUM_MAX_SCORE else "  "
        print(
            f"  cutoff {cutoff:>5.0f}{marker}  medium {counts[Tier.MEDIUM]:>4}"
            f" ({_pct(counts[Tier.MEDIUM], total)})   hard {counts[Tier.HARD]:>4}"
            f" ({_pct(counts[Tier.HARD], total)})"
        )

    print("\n== per-density: shares under each candidate cutoff ==")
    print("   (d50 is the value orchestrator.generate_batch hardcodes)")
    for density in sorted({row.density for row in graded}):
        subset = [row for row in graded if row.density == density]
        line = [f"  d{density:<3} n={len(subset):<4}"]
        for cutoff in sorted({*CANDIDATE_CUTOFFS, MEDIUM_MAX_SCORE}):
            counts, total = _shares(subset, cutoff)
            line.append(
                f" {cutoff:g}:{_pct(counts[Tier.EASY], total).strip()}"
                f"/{_pct(counts[Tier.MEDIUM], total).strip()}"
                f"/{_pct(counts[Tier.HARD], total).strip()}"
            )
        print("".join(line))

    print("\n== per-bucket at the batch density (50) ==")
    for label, _, _ in BUCKETS:
        subset = [row for row in graded if row.bucket == label and row.density == 50]
        line = [f"  {label:<6} n={len(subset):<4}"]
        for cutoff in sorted({*CANDIDATE_CUTOFFS, MEDIUM_MAX_SCORE}):
            counts, total = _shares(subset, cutoff)
            line.append(
                f" {cutoff:g}:{_pct(counts[Tier.EASY], total).strip()}"
                f"/{_pct(counts[Tier.MEDIUM], total).strip()}"
                f"/{_pct(counts[Tier.HARD], total).strip()}"
            )
        print("".join(line))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--draws", type=int, default=DRAWS_PER_CELL)
    parser.add_argument("--json", type=Path, default=None)
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--no-self-check", dest="self_check", action="store_false")
    args = parser.parse_args(argv)

    rows, failures, seconds = build_corpus(args.draws, verbose=not args.quiet)
    if args.draws >= DRAWS_PER_CELL:
        assert len(rows) >= MIN_CORPUS, (
            f"corpus shrank to {len(rows)} puzzles, below the asserted floor "
            f"of {MIN_CORPUS} — the plan changed, not the measurement"
        )
    if args.self_check:
        _self_check(rows)
    report(rows, failures, seconds, args.draws)
    if args.json is not None:
        args.json.write_text(
            json.dumps(
                {
                    "seed": CORPUS_SEED,
                    "draws_per_cell": args.draws,
                    "seconds": seconds,
                    "failures": dict(failures),
                    "rows": [asdict(row) for row in rows],
                },
                indent=1,
            ),
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
