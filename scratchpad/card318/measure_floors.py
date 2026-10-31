import sys; sys.path.insert(0, "src"); sys.path.insert(0, ".")
from tests.property.test_solve_strategies import (
    _stripe_grids, _random_grids, _signals_of, GUESS, _the_rule)
b=s=u=0
for g in _stripe_grids() + _random_grids(seed=11, count=120):
    sig = _signals_of(g)
    if sig is None: u+=1; continue
    if sig.branch_nodes>=1: b+=1
    else: s+=1
print(f"EC-017 corpus: branched={b} (floor 8), settled={s} (floor 40), unusable={u}, total usable={b+s}")

c=0
for g in _stripe_grids()[:40] + _random_grids(seed=23, count=40):
    if _signals_of(g) is not None: c+=1
print(f"EC-018 repeated: checked={c} (floor 30)")
