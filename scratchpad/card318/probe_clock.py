import sys; sys.path.insert(0, "src"); sys.path.insert(0, ".")
from types import SimpleNamespace
from nonogram import clues, solver
from nonogram.solver import propagate as pm
from tests.test_solver_strategies import _settled_grid
class C:
    START=1000.0
    def __init__(s,f): s.f=f; s.reads=0
    def monotonic(s): s.reads+=1; return s.START + s.reads*s.f
g=_settled_grid(); cs=clues.compute_clues(g)
real=pm.time
for f in (1.0,50.0):
    c=C(f); pm.time=SimpleNamespace(monotonic=c.monotonic)
    r=solver.solve(cs.rows,cs.columns,deadline=C.START+1e9)
    print(f"factor={f}: reads={c.reads} apparent_elapsed={c.reads*f} rungs={r.signals.rungs}")
pm.time=real
