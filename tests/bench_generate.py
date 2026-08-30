"""AC-037 — the NFR-001 generation-time benchmark (ADR-0001's 5s p95 cap).

    AC-037  BenchGenerate_20x20_p95Under5s  ->  test_20x20_p95_is_under_5s

*given* a 20x20 random-grid generation request under typical hardware, *when*
generation runs, including any regenerate retries, *then* p95 completion time
is <= 5s.

This is a gate, not a report: it runs inside ``pytest -q`` with the rest of the
suite (see ``tests/conftest.py`` for why a file named ``bench_generate.py`` is
collected at all), and it fails when the cap is missed. ADR-0001's own
"Negative" section anticipates exactly that — "neither number is validated
against actual solver performance yet; if profiling ... shows the solver
routinely takes longer than 5s at 20x20 ... this ADR will need to be revisited"
— and CARD-006 is explicit that a missed p95 is the deliverable, not something
to be tuned away by loosening the threshold or by picking a friendlier corpus.

Determinism (the card's "keep it runnable and deterministic enough to be a gate")
-------------------------------------------------------------------------------
Fixed corpus, fixed size, fixed seeds, fixed sample count. Every draw in the
pipeline goes through the ``random.Random`` the orchestrator builds from
``request.seed`` (ADR-0015), so a given corpus entry replays the same grids, the
same discarded candidates and the same solver work on every run and on every
machine. The only machine-dependent quantity is wall-clock time, which is the
thing being measured.

What is timed
-------------
``orchestrator.generate`` end to end — sourcing, clue derivation, the
uniqueness check and *every regenerate retry* — as AC-037 requires. A request
that ends in ``GenerationAbandoned`` (20 candidates, none unique) or in
``SolverTimeout`` is timed like any other: what the criterion bounds is how
long a user waits for the tool to finish, not how long a successful run takes.
"""

from __future__ import annotations

import math
import time

import pytest

from nonogram import orchestrator
from nonogram.errors import GenerationAbandoned, SolverTimeout
from nonogram.orchestrator import GenerationRequest

#: ADR-0001's p95 cap for grids up to and including 20x20, in seconds.
P95_CAP_SECONDS = 5.0

#: AC-037's grid size.
SIZE = 20

#: The corpus: every combination of these densities and seeds, 20 requests.
#: The densities span the range a 20x20 request plausibly asks for rather than
#: a single value, because the solver's cost at this size is dominated by
#: density and a one-density corpus would measure a corner instead of the
#: criterion. ``--density`` has no default in the CLI, so there is no single
#: "typical" value to prefer; sampling the middle of the supported 0..100 band
#: evenly is the neutral choice. The seeds are the first five integers — an
#: arbitrary but *fixed* choice, which is all determinism requires.
DENSITIES = (30, 40, 50, 60)
SEEDS = (0, 1, 2, 3, 4)

#: Requests in the order they are run: seed-major, so the four densities are
#: interleaved rather than run in four blocks. Ordering cannot change the p95
#: (a percentile of a set), and interleaving means the early samples are a
#: cross-section of the corpus rather than one density's corner.
CORPUS: tuple[tuple[int, int], ...] = tuple(
    (density, seed) for seed in SEEDS for density in DENSITIES
)

#: Nearest-rank p95: the ``ceil(0.95 * n)``-th smallest sample. With n = 20
#: that is the 19th, so the criterion holds exactly when at most one sample
#: exceeds the cap. No interpolation — at this sample size interpolating
#: between the 19th and 20th value would invent precision the corpus does not
#: have.
_P95_RANK = math.ceil(0.95 * len(CORPUS))

#: How many samples may exceed the cap and still leave p95 <= cap.
_ALLOWED_OVER_CAP = len(CORPUS) - _P95_RANK


def _time_one_request(density: int, seed: int) -> tuple[float, str]:
    """Run one generation request and time it end to end.

    The deadline in force is whatever ``orchestrator.GENERATION_BUDGET_SECONDS``
    currently is — the caller sets it, because "what budget was this measured
    under" is a property of the measurement run, not of one sample.

    Returns:
        ``(elapsed_seconds, outcome)`` where ``outcome`` is ``"unique"``,
        ``"abandoned"`` (POL-005's retry bound) or ``"timeout"`` (ADR-0011's
        deadline). All three are completions as far as AC-037 is concerned;
        only a hang would not be, and ADR-0011 is what rules that out.
    """
    request = GenerationRequest(mode="random", size=SIZE, density=density, seed=seed)
    started = time.perf_counter()
    try:
        orchestrator.generate(request)
        outcome = "unique"
    except GenerationAbandoned:
        outcome = "abandoned"
    except SolverTimeout:
        outcome = "timeout"
    return time.perf_counter() - started, outcome


def measure() -> list[tuple[int, int, float, str]]:
    """Time the whole corpus, without any early exit.

    Not what the gate calls — see :func:`test_20x20_p95_is_under_5s` for why —
    but the honest, uncensored measurement to reach for when the question is
    "how far off is it?" rather than "does it pass?"::

        python -c "from tests.bench_generate import report; report()"
    """
    return [
        (density, seed, *_time_one_request(density, seed)) for density, seed in CORPUS
    ]


def report(budget_seconds: float = 30.0) -> None:  # pragma: no cover - developer tool
    """Print the uncensored corpus timings and their p95."""
    original = orchestrator.GENERATION_BUDGET_SECONDS
    orchestrator.GENERATION_BUDGET_SECONDS = budget_seconds
    try:
        samples = measure()
    finally:
        orchestrator.GENERATION_BUDGET_SECONDS = original
    for density, seed, elapsed, outcome in samples:
        print(f"{SIZE}x{SIZE} density={density:3d} seed={seed}  {elapsed:8.3f}s  {outcome}")
    ordered = sorted(elapsed for _, _, elapsed, _ in samples)
    print(f"p95 (nearest-rank, n={len(ordered)}) = {ordered[_P95_RANK - 1]:.3f}s")


# --------------------------------------------------------------------------
# AC-037 — BenchGenerate_20x20_p95Under5s
# --------------------------------------------------------------------------


@pytest.mark.xfail(
    reason=(
        "AC-037 still unmet, but in a much narrower band than when CARD-006 "
        "marked this: CARD-018's probing search closed 10-30% and >=45% "
        "outright (density 30 went from 5-of-5 requests unbounded at the 30s "
        "cap to 1.3-2.6s; 10-25% now runs 1.4-2.9s where it also used to time "
        "out) and left the 5s cap missed only in the ~32-45% band, worst at "
        "35-42%, where this corpus's density-40 column still runs 13-30s+. "
        "The residual is dominated by individual candidate grids that are hard "
        "in themselves rather than hard for one heuristic — see CARD-018's "
        "worktree notes for the evidence and the full 10-90% sweep. Removing "
        "this marker needs the whole density range under the cap, not this "
        "corpus alone: do not remove it on partial data."
    ),
    strict=True,
)
def test_20x20_p95_is_under_5s(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC-037: p95 completion for a 20x20 request, retries included, <= 5s.

    Two things keep this affordable to run on every ``pytest -q`` without
    weakening it.

    *The per-request budget is the cap itself.* ADR-0011's deadline is set to
    ``P95_CAP_SECONDS`` rather than the production 30s, so a request that would
    run longer is stopped at the cap and recorded as "over". That censors the
    sample — the true time is only known to be ``>= 5s`` — and censoring costs
    this criterion nothing: "p95 <= 5s" is decided entirely by *how many*
    samples exceed 5s, never by how far.

    *The corpus stops as soon as the verdict is settled.* One sample of 20 may
    exceed the cap (nearest-rank p95 is the 19th smallest); the moment a second
    one does, p95 > cap is proven and the remaining requests cannot change it.
    So a failing run costs about two cap-lengths instead of twenty, and a
    passing run has to time every sample, which is exactly the asymmetry a gate
    wants.

    Neither shortcut touches the threshold or the corpus. If this fails, the
    finding is real: per CARD-006 and ADR-0009's "performance tuning at the
    upper end is our problem", the fix belongs in the solver's propagation
    strength, not here.
    """
    monkeypatch.setattr(orchestrator, "GENERATION_BUDGET_SECONDS", P95_CAP_SECONDS)

    samples: list[tuple[int, int, float, str]] = []
    over_cap = 0
    for density, seed in CORPUS:
        elapsed, outcome = _time_one_request(density, seed)
        samples.append((density, seed, elapsed, outcome))
        if outcome == "timeout" or elapsed > P95_CAP_SECONDS:
            over_cap += 1
            if over_cap > _ALLOWED_OVER_CAP:
                break

    ordered = sorted(elapsed for _, _, elapsed, _ in samples)
    measured_p95 = ordered[min(_P95_RANK, len(ordered)) - 1]

    assert over_cap <= _ALLOWED_OVER_CAP, _verdict(samples, over_cap, measured_p95)
    assert measured_p95 <= P95_CAP_SECONDS, _verdict(samples, over_cap, measured_p95)


def _verdict(
    samples: list[tuple[int, int, float, str]], over_cap: int, measured_p95: float
) -> str:
    """The failure report: every sample, so the finding is actionable as-is."""
    lines = [
        f"AC-037 not met: {over_cap} of {len(samples)} timed {SIZE}x{SIZE} requests "
        f"exceeded the ADR-0001 p95 cap of {P95_CAP_SECONDS}s "
        f"(at most {_ALLOWED_OVER_CAP} of {len(CORPUS)} may). "
        f"p95 >= {measured_p95:.3f}s.",
        "Samples run (a request stopped at the cap is a censored lower bound):",
    ]
    lines += [
        f"  density={density:3d} seed={seed}  {elapsed:8.3f}s  {outcome}"
        for density, seed, elapsed, outcome in samples
    ]
    lines.append(
        "Per CARD-006 and ADR-0009, the lever is the solver's propagation "
        "strength (probing / limited lookahead), not this threshold."
    )
    return "\n".join(lines)


# --------------------------------------------------------------------------
# The benchmark's own contract — a gate that cannot fail is not a gate
# --------------------------------------------------------------------------


def test_the_corpus_is_fixed_and_the_p95_rank_is_the_nineteenth_of_twenty() -> None:
    """Pins determinism and the statistic, so neither can drift silently.

    Sample count, rank and tolerance are what turn "p95 <= 5s" into a decidable
    proposition; if a later change grew the corpus without revisiting the rank,
    the gate would quietly start measuring something else.
    """
    assert len(CORPUS) == 20
    assert len(set(CORPUS)) == len(CORPUS)
    assert _P95_RANK == 19
    assert _ALLOWED_OVER_CAP == 1
    assert P95_CAP_SECONDS == 5.0


def test_the_same_corpus_entry_replays_the_same_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ADR-0015 determinism, checked on the benchmark's own inputs.

    A benchmark whose corpus drew fresh randomness each run would measure a
    different puzzle every time and could not gate anything. Timing is not
    compared here — only the *work*: same seed, same discarded candidates, same
    final grid.
    """
    monkeypatch.setattr(orchestrator, "GENERATION_BUDGET_SECONDS", P95_CAP_SECONDS)
    density, seed = 60, SEEDS[0]

    first = orchestrator.generate(
        GenerationRequest(mode="random", size=SIZE, density=density, seed=seed)
    )
    second = orchestrator.generate(
        GenerationRequest(mode="random", size=SIZE, density=density, seed=seed)
    )

    assert first.grid == second.grid
    assert first.regenerate.attempts == second.regenerate.attempts
    assert first.solution_count == second.solution_count
