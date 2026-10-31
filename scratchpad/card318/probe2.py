import sys; sys.path.insert(0, "src")
from nonogram.orchestrator import GenerationRequest, generate
from nonogram.errors import GenerationAbandoned
for (w,d,s) in [(20,40,42),(20,30,42),(15,40,42),(20,40,7),(20,50,42)]:
    try:
        p = generate(GenerationRequest(mode="random", width=w, height=w, density=d, seed=s))
        print(f"{w}x{w} d{d} seed{s}: OK strategies={p.strategies} branch={p.branch_nodes}")
    except GenerationAbandoned as e:
        print(f"{w}x{w} d{d} seed{s}: ABANDONED")
