import sys, random; sys.path.insert(0, "src")
from nonogram import clues, solver
rng = random.Random(11)
uniq=branched=settled=total=0
for i in range(300):
    n = rng.choice((8,10,12))
    d = rng.choice((0.3,0.4,0.5,0.6,0.7))
    g = [[rng.random() < d for _ in range(n)] for _ in range(n)]
    cs = clues.compute_clues(g)
    r = solver.solve(cs.rows, cs.columns)
    total+=1
    if r.solution_count != 1: continue
    uniq+=1
    if r.signals.branch_nodes > 0: branched+=1
    else: settled+=1
print(f"random: total={total} unique={uniq} branched={branched} settled={settled}")

# structured stripe family
b=s=0
for n in range(8,21):
    for k in (2,3,4,5):
        g = [[(r+c) % k < max(1,k//2) for c in range(n)] for r in range(n)]
        cs = clues.compute_clues(g)
        r2 = solver.solve(cs.rows, cs.columns)
        if r2.solution_count != 1: continue
        if r2.signals.branch_nodes>0: b+=1
        else: s+=1
print(f"stripes: branched={b} settled={s}")
