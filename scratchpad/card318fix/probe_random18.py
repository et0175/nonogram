import sys, time, collections
from nonogram import clues as clues_mod, solver
from nonogram.admin.batch_generator import BatchGenerator
from nonogram.admin.puzzle_review import PuzzleReviewService

GUESS = solver.STRATEGY_GUESS
EXTENT = int(sys.argv[1]) if len(sys.argv) > 1 else 18
RUNS = int(sys.argv[2]) if len(sys.argv) > 2 else 3

def strategies_of(result):
    return tuple(result.signals.rungs) + ((GUESS,) if result.signals.branch_nodes > 0 else ())

for run in range(RUNS):
    store = PuzzleReviewService()
    handed = []
    real = store.add_puzzle
    def spying(*a, **k):
        handed.append((k.get("grid"), k.get("strategies_used")))
        return real(*a, **k)
    store.add_puzzle = spying
    gen = BatchGenerator(puzzle_review_service=store)
    t0 = time.monotonic()
    gen.create_batch(count=10, sizes=[EXTENT], source="random")
    dt = time.monotonic() - t0
    dist = collections.Counter()
    bad = 0
    multi = 0
    for grid, names in handed:
        lc = clues_mod.compute_clues(grid)
        derived = strategies_of(solver.solve(lc.rows, lc.columns))
        if tuple(names) != derived:
            bad += 1
            print("  MISMATCH", names, derived)
        dist[tuple(names)] += 1
        if len(names) > 1:
            multi += 1
    print(f"run{run} extent={EXTENT} n={len(handed)} {dt:.1f}s multi={multi} mismatch={bad} {dict(dist)}")
