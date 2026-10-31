import sys
sys.path.insert(0, "src")
from nonogram import orchestrator, solver
from nonogram.orchestrator import GenerationRequest, generate

calls = []
real = solver.solve
def counting(*a, **k):
    r = real(*a, **k)
    calls.append((r.solution_count, r.signals.branch_nodes, tuple(r.signals.rungs)))
    return r
orchestrator.solver.solve = counting
p = generate(GenerationRequest(mode="random", width=20, height=20, density=40, seed=42))
print("calls:", len(calls))
for c in calls: print("  ", c)
print("strategies:", p.strategies)
print("branch_nodes:", p.branch_nodes)
