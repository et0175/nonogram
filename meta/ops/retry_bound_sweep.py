"""CARD-089 AC-1 — measure what a retry bound actually buys, and what it costs.

    PYTHONPATH=src python meta/ops/retry_bound_sweep.py \
        [requests-per-bound] [bounds-csv] [extents-csv]

Defaults reproduce CARD-089's sweep. The seeds depend only on the extent, so
a later run of one bound is directly comparable to an earlier run of another
at the same extent and request count -- which is how CARD-090 added its 30
row without re-running 20, 40 and 60.

Committed rather than run ad hoc, for the reason ADR-0002 gives for needing it
at all: its two numbers were "chosen without empirical tuning ... and will
likely need revisiting once usage data exists". A sweep that lives only in a
terminal cannot be re-run against a later solver, so the next person asking
"is 40 still right?" would be back to guessing.

Seeded, so two runs of the same command compare. Each request goes through the
real ``orchestrator.generate`` — not a hand-rolled redraw loop — because
POL-006's repair is most of what decides the answer, and a model without it
understates the pipeline by a factor of three (see the card).
"""

from __future__ import annotations

import statistics
import sys
import time

from nonogram import orchestrator
from nonogram.errors import GenerationAbandoned, SolverTimeout

DEFAULT_BOUNDS = (20, 40, 60)
DEFAULT_EXTENTS = (25, 30)
DENSITY = 50  # what generate_batch hardcodes, so this is the lived case


def sweep(extent: int, bound: int, requests: int, seed_base: int) -> dict:
    original_regenerate = orchestrator.MAX_REGENERATE_ATTEMPTS
    original_resample = orchestrator.MAX_RESAMPLE_ATTEMPTS
    orchestrator.MAX_REGENERATE_ATTEMPTS = bound
    orchestrator.MAX_RESAMPLE_ATTEMPTS = bound
    try:
        durations: list[float] = []
        made = abandoned = timed_out = 0
        started = time.monotonic()
        for index in range(requests):
            request_started = time.monotonic()
            try:
                orchestrator.generate(
                    orchestrator.GenerationRequest(
                        mode="random",
                        width=extent,
                        height=extent,
                        density=DENSITY,
                        seed=seed_base + index,
                    )
                )
                made += 1
            except GenerationAbandoned:
                abandoned += 1
            except SolverTimeout:
                timed_out += 1
            durations.append(time.monotonic() - request_started)
        durations.sort()
        return {
            "extent": extent,
            "bound": bound,
            "requests": requests,
            "made": made,
            "abandoned": abandoned,
            "timed_out": timed_out,
            "median": statistics.median(durations),
            "p95": durations[int(len(durations) * 0.95) - 1],
            "max": durations[-1],
            "total": time.monotonic() - started,
        }
    finally:
        orchestrator.MAX_REGENERATE_ATTEMPTS = original_regenerate
        orchestrator.MAX_RESAMPLE_ATTEMPTS = original_resample


def _numbers(argument: str) -> tuple[int, ...]:
    return tuple(int(part) for part in argument.split(",") if part.strip())


def main() -> None:
    requests = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    bounds = _numbers(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_BOUNDS
    extents = _numbers(sys.argv[3]) if len(sys.argv) > 3 else DEFAULT_EXTENTS
    print(f"  {requests} requests per bound, density {DENSITY}, seeded")
    print(f"  bounds {bounds}, extents {extents}")
    print()
    header = (
        f"  {'extent':>7} {'bound':>6} {'made':>5} {'aband':>6} {'t/out':>6} "
        f"{'success':>8} {'median':>8} {'p95':>8} {'max':>8} {'total':>8}"
    )
    print(header)
    for extent in extents:
        # The same seeds at every bound, so a difference is the bound and not
        # a different set of grids.
        seed_base = 100_000 + extent * 1_000
        for bound in bounds:
            row = sweep(extent, bound, requests, seed_base)
            marker = (
                "  <- shipped" if bound == orchestrator.MAX_RETRY_ATTEMPTS else ""
            )
            print(
                f"  {row['extent']}x{row['extent']:<3} {row['bound']:>6} "
                f"{row['made']:>5} {row['abandoned']:>6} {row['timed_out']:>6} "
                f"{row['made'] / row['requests'] * 100:>7.0f}% "
                f"{row['median']:>7.2f}s {row['p95']:>7.2f}s {row['max']:>7.2f}s "
                f"{row['total']:>7.0f}s{marker}",
                flush=True,
            )
        print(flush=True)


if __name__ == "__main__":
    main()
