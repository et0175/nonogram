import time
from nonogram import solver
from nonogram.orchestrator import GenerationRequest, generate

GUESS = solver.STRATEGY_GUESS
print("vocab:", solver.STRATEGY_NAMES if hasattr(solver,'STRATEGY_NAMES') else "n/a")
for size in (10, 12, 15, 18):
    counts = {}
    t0 = time.monotonic()
    for seed in range(1, 9):
        try:
            p = generate(GenerationRequest(mode="random", width=size, height=size, density=50, seed=seed))
            counts[tuple(p.strategies)] = counts.get(tuple(p.strategies), 0) + 1
        except Exception as e:
            counts[type(e).__name__] = counts.get(type(e).__name__, 0) + 1
    print(size, f"{time.monotonic()-t0:.1f}s", counts)
