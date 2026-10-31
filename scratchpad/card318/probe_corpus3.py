import sys, time, random; sys.path.insert(0, "src")
from nonogram import clues, solver
from nonogram.errors import SolverTimeout
BUDGET=0.25
def classify(g):
    cs = clues.compute_clues(g)
    try:
        r = solver.solve(cs.rows, cs.columns, deadline=time.monotonic()+BUDGET)
    except SolverTimeout:
        return None
    return (r.solution_count, r.signals.branch_nodes, tuple(r.signals.rungs))

t0=time.monotonic()
b=s=to=0; bsizes=[]
for n in range(8,21):
    for k in (2,3,4,5,6,7):
        for off in (0,1):
            g=[[(r+c+off)%k < max(1,k//2) for c in range(n)] for r in range(n)]
            res=classify(g)
            if res is None: to+=1; continue
            sc,bn,ru = res
            if sc!=1: continue
            if bn>0: b+=1; bsizes.append((n,k,off,bn,ru))
            else: s+=1
print(f"stripes+off: branched={b} settled={s} timeouts={to} elapsed={time.monotonic()-t0:.2f}s")
for x in bsizes[:12]: print("   branched:", x)
