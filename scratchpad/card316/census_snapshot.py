"""Snapshot every pinned class of tests/test_check_ref_resolution.py as NAME SETS.

Run before the edit and after; each move is then a set difference whose movers
can be resolved individually. No baseline figure is ever pasted from a failure
message — the counts printed here are derived from these sets.

The nine predicates are transcribed from the module's own nine `_assert_class`
call sites (not re-invented), so a snapshot and a run of the suite are reading
the same populations.

Usage: census_snapshot.py <out.json>
"""
import importlib.util, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
MOD = ROOT / "tests" / "test_check_ref_resolution.py"

spec = importlib.util.spec_from_file_location("ccr", MOD)
m = importlib.util.module_from_spec(spec)
sys.modules["ccr"] = m
spec.loader.exec_module(m)

V = m._verdicts()

def refs(pred):
    return sorted({v.ref for v in V if pred(v)})

out = {
    # CENSUS — every declared ref (the whole population)
    "census": sorted({v.ref for v in V}),
    # the three EC classes
    "falsely_alive": refs(lambda v: v.falsely_alive),
    "falsely_dead": refs(lambda v: v.falsely_dead),
    "honest_dead": refs(lambda v: not v.loose and not v.strict),
    # the gate's class
    "bookkeeping_only": refs(lambda v: v.bookkeeping_only),
    # node-id resolved only from outside its own module
    "resolved_from_afar": refs(
        lambda v: v.declared.form == m.FORM_NODE_ID and v.strict
        and v.ref.partition("::")[0] not in v.loose),
    # a real definition exists
    "defined": refs(lambda v: bool(v.strict)),
    # node-id whose own module holds both the prose hit and the def
    "same_file_prose": refs(
        lambda v: v.declared.form == m.FORM_NODE_ID and v.strict
        and v.ref.partition("::")[0] in v.loose),
    # trace.yml's own tests: lists, read independently of the census
    "trace_tests": sorted(m._trace_tests_refs_by_backward_scan()),
}
out["_pinned"] = {name: list(getattr(m, name)) for name in (
    "CENSUS", "HONEST_DEAD", "FALSELY_ALIVE", "FALSELY_DEAD",
    "BOOKKEEPING_ONLY", "RESOLVED_FROM_AFAR", "TRACE_TESTS", "DEFINED",
    "SAME_FILE_PROSE")}
out["_fingerprints"] = {
    k: m._fingerprint(tuple(sorted(v))) for k, v in out.items()
    if not k.startswith("_")}

pathlib.Path(sys.argv[1]).write_text(json.dumps(out, indent=1, sort_keys=True))
for k in sorted(out):
    if not k.startswith("_"):
        print(f"{k:<20} {len(out[k]):>4}  {out['_fingerprints'][k]}")
print("pinned (count, fingerprint):")
for k, v in sorted(out["_pinned"].items()):
    print(f"  {k:<20} {v}")
