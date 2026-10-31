import sys, time; sys.path.insert(0, "src")
from nonogram import clues, solver
# a structured 20x20 grid that should be line-solvable quickly
g = [[(r*20+c) % 3 != 0 for c in range(20)] for r in range(20)]
cs = clues.compute_clues(g)
t=time.monotonic(); r = solver.solve(cs.rows, cs.columns); e=time.monotonic()-t
print("20x20 structured: count=", r.solution_count, "branch=", r.signals.branch_nodes, "rungs=", r.signals.rungs, f"{e:.3f}s")
# diagonal-ish
g2 = [[(r+c) % 4 < 2 for c in range(20)] for r in range(20)]
cs2 = clues.compute_clues(g2)
t=time.monotonic(); r2 = solver.solve(cs2.rows, cs2.columns); e=time.monotonic()-t
print("20x20 stripes:    count=", r2.solution_count, "branch=", r2.signals.branch_nodes, "rungs=", r2.signals.rungs, f"{e:.3f}s")
