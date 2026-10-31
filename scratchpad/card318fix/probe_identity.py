"""Does an independent re-solve of a stored puzzle's clues reproduce the
strategies the generator handed over?  Measured, not assumed."""
import sys

from nonogram import clues as clues_mod, solver
from nonogram.admin.batch_generator import BatchGenerator
from nonogram.admin.puzzle_review import PuzzleReviewService
from nonogram.limits import MIN_SIZE

GUESS = solver.STRATEGY_GUESS


def strategies_of(result):
    return tuple(result.signals.rungs) + ((GUESS,) if result.signals.branch_nodes > 0 else ())


store = PuzzleReviewService()
handed = []
real = store.add_puzzle


def spying(*args, **kwargs):
    handed.append((kwargs.get("grid"), kwargs.get("clues_rows"), kwargs.get("clues_cols"),
                   kwargs.get("strategies_used")))
    return real(*args, **kwargs)


store.add_puzzle = spying
gen = BatchGenerator(puzzle_review_service=store)
gen.create_batch(count=10, sizes=[MIN_SIZE], source="random")

print("handed", len(handed))
mismatch = 0
for i, (grid, rows, cols, names) in enumerate(handed):
    # independent: from the GRID, re-computing clues in the test tree
    lc = clues_mod.compute_clues(grid)
    res = solver.solve(lc.rows, lc.columns)
    derived = strategies_of(res)
    same_clues = (tuple(tuple(r) for r in rows) == lc.rows and tuple(tuple(c) for c in cols) == lc.columns)
    ok = tuple(names) == derived
    mismatch += 0 if ok else 1
    print(i, "handed=", tuple(names), "derived=", derived, "match=", ok,
          "clues_roundtrip=", same_clues, "count=", res.solution_count)
print("MISMATCHES", mismatch)
sys.exit(1 if mismatch else 0)
