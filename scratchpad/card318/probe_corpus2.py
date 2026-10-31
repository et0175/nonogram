import sys, random; sys.path.insert(0, "src")
from nonogram import clues, solver
def classify(g):
    cs = clues.compute_clues(g)
    r = solver.solve(cs.rows, cs.columns)
    return (r.solution_count, r.signals.branch_nodes)

fams = {}
# stripes with offsets
b=s=0
for n in range(8,21):
    for k in (2,3,4,5,6,7):
        for off in (0,1):
            g=[[(r+c+off)%k < max(1,k//2) for c in range(n)] for r in range(n)]
            sc,bn = classify(g)
            if sc!=1: continue
            if bn>0: b+=1
            else: s+=1
fams["stripes+off"]=(b,s)
# low-density random
b=s=0
rng=random.Random(5)
for i in range(200):
    n=rng.choice((8,9,10,12))
    d=rng.choice((0.15,0.2,0.25,0.8,0.85))
    g=[[rng.random()<d for _ in range(n)] for _ in range(n)]
    sc,bn=classify(g)
    if sc!=1: continue
    if bn>0: b+=1
    else: s+=1
fams["lowdens"]=(b,s)
# xor / mod patterns
b=s=0
for n in range(8,19):
    for m in (3,5,7,11):
        g=[[((r*r+c*c) % m) < m//2 for c in range(n)] for r in range(n)]
        sc,bn=classify(g)
        if sc!=1: continue
        if bn>0: b+=1
        else: s+=1
fams["quadratic"]=(b,s)
for k,v in fams.items(): print(k, "branched/settled =", v)
