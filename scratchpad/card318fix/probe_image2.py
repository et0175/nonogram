import os, sys, time
os.environ.pop("DATABASE_URL", None)
os.environ["TESTING"] = "true"
from pathlib import Path
from nonogram import clues as clues_mod, solver
from nonogram.admin import image_manager as image_manager_module
from nonogram.admin.app import create_app

GUESS = solver.STRATEGY_GUESS
FIXTURES = Path("tests/fixtures")
names = sys.argv[1:]

def strategies_of(r):
    return tuple(r.signals.rungs) + ((GUESS,) if r.signals.branch_nodes > 0 else ())

image_manager_module._image_manager = None
app = create_app()
app.config["TESTING"] = True
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024
with app.app_context():
    handed = []
    svc = app.puzzle_review_service
    real = svc.add_puzzle
    def spying(*a, **k):
        handed.append((k.get("source_image"), k.get("grid"), k.get("strategies_used")))
        return real(*a, **k)
    svc.add_puzzle = spying
    client = app.test_client()
    handles = [open(FIXTURES / n, "rb") for n in names]
    up = client.post("/batch/from-images", data={"image_files": [(h, n) for h, n in zip(handles, names)]},
                     content_type="multipart/form-data")
    assert up.status_code == 302, up.status_code
    t0 = time.monotonic()
    r = client.post("/batch/generate-puzzles", data={}, follow_redirects=False)
    dt = time.monotonic() - t0
    print("gen", r.status_code, f"{dt:.1f}s", "n=", len(handed))
    for src, grid, nm in handed:
        lc = clues_mod.compute_clues(grid)
        derived = strategies_of(solver.solve(lc.rows, lc.columns))
        print("  ", src, tuple(nm), "derived=", derived, "match=", tuple(nm) == derived)
