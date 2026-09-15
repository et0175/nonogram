"""CARD-089 AC-1 — measure what a retry bound actually buys, and what it costs.

    PYTHONPATH=src python meta/ops/retry_bound_sweep.py \
        [requests-per-bound] [bounds-csv] [extents-csv] [repairs-csv]

Defaults reproduce CARD-089's sweep. ``repairs-csv`` (CARD-091) adds a K axis:
each row then runs at that ``MAX_CONSECUTIVE_REPAIRS``, and gains the total
recovery attempts per accepted puzzle and a histogram of the repair depth each
accepted puzzle was found at. Without it the output is exactly what CARD-089
and CARD-090 printed. The seeds depend only on the extent, so
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


def _acceptance_depth(recovery: orchestrator.RecoveryLog, repairs_cap: int) -> int:
    """Which repair of its lineage an accepted puzzle was found on (0 = the draw).

    Derived, not instrumented: a lineage that reached the cap cost exactly one
    redraw plus ``repairs_cap`` repairs, so whatever repairs remain belong to
    the lineage that was accepted. ADR-0024's recalibration asked for per-seed
    lineage outcomes, and this is that record read off the existing log.
    """
    depth = recovery.repairs - repairs_cap * recovery.lineages_at_repair_cap
    if not 0 <= depth <= repairs_cap:
        # The derivation rests on every capped lineage costing exactly K
        # repairs. If that ever stops being true the histogram would be quietly
        # wrong, which is worse than no histogram.
        raise AssertionError(f"acceptance depth {depth} outside 0..{repairs_cap}: {recovery}")
    return depth


def sweep(
    extent: int,
    bound: int,
    requests: int,
    seed_base: int,
    repairs_cap: int | None = None,
) -> dict:
    original_regenerate = orchestrator.MAX_REGENERATE_ATTEMPTS
    original_resample = orchestrator.MAX_RESAMPLE_ATTEMPTS
    original_repairs = orchestrator.MAX_CONSECUTIVE_REPAIRS
    original_puzzle = orchestrator.Puzzle
    orchestrator.MAX_REGENERATE_ATTEMPTS = bound
    orchestrator.MAX_RESAMPLE_ATTEMPTS = bound
    created: list[orchestrator.Puzzle] = []
    if repairs_cap is not None:
        orchestrator.MAX_CONSECUTIVE_REPAIRS = repairs_cap

        # An abandoned run never returns its aggregate, and its attempts are
        # exactly the cost being measured -- so keep a reference to each one.
        class _Recorded(original_puzzle):  # type: ignore[valid-type,misc]
            def __init__(self, *args: object, **kwargs: object) -> None:
                super().__init__(*args, **kwargs)
                created.append(self)

        orchestrator.Puzzle = _Recorded
    try:
        durations: list[float] = []
        made = abandoned = timed_out = 0
        attempts = 0
        depths: dict[int, int] = {}
        started = time.monotonic()
        for index in range(requests):
            request_started = time.monotonic()
            accepted = False
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
                accepted = True
            except GenerationAbandoned:
                abandoned += 1
            except SolverTimeout:
                timed_out += 1
            durations.append(time.monotonic() - request_started)
            if repairs_cap is not None and created:
                recovery = created[-1].recovery
                attempts += recovery.redraws + recovery.repairs
                if accepted:
                    depth = _acceptance_depth(recovery, repairs_cap)
                    depths[depth] = depths.get(depth, 0) + 1
                created.clear()
        durations.sort()
        return {
            "repairs_cap": repairs_cap,
            "attempts": attempts,
            "depths": depths,
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
        orchestrator.MAX_CONSECUTIVE_REPAIRS = original_repairs
        orchestrator.Puzzle = original_puzzle


def _numbers(argument: str) -> tuple[int, ...]:
    return tuple(int(part) for part in argument.split(",") if part.strip())


def main() -> None:
    requests = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    bounds = _numbers(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_BOUNDS
    extents = _numbers(sys.argv[3]) if len(sys.argv) > 3 else DEFAULT_EXTENTS
    repairs_caps: tuple[int | None, ...] = (
        _numbers(sys.argv[4]) if len(sys.argv) > 4 else (None,)
    )
    k_axis = repairs_caps != (None,)
    print(f"  {requests} requests per bound, density {DENSITY}, seeded")
    print(f"  bounds {bounds}, extents {extents}")
    if k_axis:
        print(f"  consecutive repairs (K) {repairs_caps}")
    print()
    header = (
        f"  {'extent':>7} {'bound':>6} {'made':>5} {'aband':>6} {'t/out':>6} "
        f"{'success':>8} {'median':>8} {'p95':>8} {'max':>8} {'total':>8}"
    )
    if k_axis:
        header = (
            f"  {'extent':>7} {'bound':>6} {'K':>3} {'made':>5} {'aband':>6} "
            f"{'t/out':>6} {'success':>8} {'median':>8} {'p95':>8} {'max':>8} "
            f"{'total':>8} {'att/made':>9}  depth histogram"
        )
    print(header)
    for extent in extents:
        # The same seeds at every bound, so a difference is the bound and not
        # a different set of grids.
        seed_base = 100_000 + extent * 1_000
        for bound in bounds:
            for repairs_cap in repairs_caps:
                row = sweep(extent, bound, requests, seed_base, repairs_cap)
                if k_axis:
                    shipped = (
                        bound == orchestrator.MAX_RETRY_ATTEMPTS
                        and repairs_cap == orchestrator.MAX_CONSECUTIVE_REPAIRS
                    )
                    per_made = (
                        f"{row['attempts'] / row['made']:>9.1f}" if row["made"] else f"{'-':>9}"
                    )
                    histogram = " ".join(
                        f"{depth}:{count}" for depth, count in sorted(row["depths"].items())
                    )
                    print(
                        f"  {row['extent']}x{row['extent']:<3} {row['bound']:>6} "
                        f"{repairs_cap:>3} {row['made']:>5} {row['abandoned']:>6} "
                        f"{row['timed_out']:>6} "
                        f"{row['made'] / row['requests'] * 100:>7.0f}% "
                        f"{row['median']:>7.2f}s {row['p95']:>7.2f}s "
                        f"{row['max']:>7.2f}s {row['total']:>7.0f}s {per_made}  "
                        f"{histogram}{'  <- shipped' if shipped else ''}",
                        flush=True,
                    )
                    continue
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
