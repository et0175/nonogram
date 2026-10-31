import ast, os, sys, collections
ROOT = "/Users/omelnikova/PycharmProjects/PythonProject4-card-318/tests"
defs = collections.defaultdict(list)
for dp, dn, fn in os.walk(ROOT):
    dn[:] = [d for d in dn if d != "__pycache__"]
    for f in fn:
        if not f.endswith(".py"): continue
        p = os.path.join(dp, f)
        try: tree = ast.parse(open(p, encoding="utf-8").read())
        except SyntaxError: continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                defs[node.name].append(f"{p}:{node.lineno}")
print("INDEXED_DISTINCT_NAMES", len(defs))
# prove instrument both directions
for probe in ["TestComponentMap_EveryComponentIsListedExactlyOnce","test_reports_unique_solution","NonsenseControl_ZZZ_review318"]:
    print("PROBE", probe, "->", defs.get(probe, "NO DEFINITION"))
print("---")
for name in sys.argv[1:]:
    print(f"{name} -> {defs.get(name, 'NO DEFINITION')}")
