import sys, time
sys.path.insert(0, "/Users/omelnikova/PycharmProjects/PythonProject4-card-318/src")
from nonogram.orchestrator import GenerationRequest, generate
for size, density, seed in [(20,40,42),(20,40,7),(20,40,1),(15,15,42),(15,40,42)]:
    t=time.time()
    try:
        r = generate(GenerationRequest(mode="random", width=size, height=size, density=density, seed=seed))
        print(f"{size}x{size} d{density} seed{seed}: OK strategies={getattr(r,'strategies',None)} {time.time()-t:.1f}s")
    except Exception as e:
        print(f"{size}x{size} d{density} seed{seed}: {type(e).__name__}: {str(e)[:90]} {time.time()-t:.1f}s")
