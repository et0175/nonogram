import sys; sys.path.insert(0,"/Users/omelnikova/PycharmProjects/PythonProject4-card-318/src")
import time as _t
from nonogram import clues, solver
from nonogram.solver import propagate
grid=[[(r*30+c)%3!=0 for c in range(20)] for r in range(20)]
lc=clues.compute_clues(grid)
class C:
    def __init__(s): s.reads=0
    def monotonic(s):
        s.reads+=1; return 1000.0
for label,kw in [("deadline=None",{}),("deadline=far",{"deadline":_t.monotonic()+600})]:
    c=C(); orig=propagate.time; propagate.time=c
    try: solver.solve(lc.rows, lc.columns, **kw)
    finally: propagate.time=orig
    print(f"{label}: clock reads = {c.reads}")
