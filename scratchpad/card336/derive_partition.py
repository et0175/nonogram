"""CARD-336 AC-3: the derived placed-edge partition over the two Touches modules."""
from __future__ import annotations
import ast, dataclasses, pathlib, sys

sys.path.insert(0, ".")
from tests.helpers.page_ink import Drawing, FrameCentre

INK_READERS = frozenset({"drawing_of", "drawings_of"})
BOUNDARY_READERS = frozenset({"frame_centre_of"})
INK_EDGES = frozenset(set(Drawing.__dataclass_fields__) - {"columns", "rows", "framed"})
BOUNDARY_FIELDS = frozenset(
    f for f in FrameCentre.__dataclass_fields__ if not f.endswith("_rule_px")
)
BOUNDS = {
    "tests/property/test_book_pdf_geometry.py": "HALF_PIXEL_MM",
    "tests/test_book_puzzle_frame.py": "EDGE_TOLERANCE_PX",
}
print("INK_EDGES", sorted(INK_EDGES), "BOUNDARY_FIELDS", sorted(BOUNDARY_FIELDS))


def scopes(tree):
    """(enclosing function node, class-qualified name) for every function."""
    out = {}
    def walk(node, prefix):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                walk(child, prefix + child.name + "::")
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                out[child] = prefix + child.name
                walk(child, prefix + child.name + ".")
            else:
                walk(child, prefix)
    walk(tree, "")
    return out


def bindings(function, module):
    """name -> [value trees], for the function and the module around it."""
    table: dict[str, list[ast.AST]] = {}
    def add(target, value):
        if isinstance(target, ast.Name):
            table.setdefault(target.id, []).append(value)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for element in target.elts:
                add(element, value)
        elif isinstance(target, ast.Starred):
            add(target.value, value)
    nodes = list(module.body) + list(ast.walk(function))
    if True:
        for node in nodes:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    add(target, node.value)
            elif isinstance(node, (ast.AnnAssign, ast.AugAssign)) and node.value:
                add(node.target, node.value)
            elif isinstance(node, (ast.For, ast.AsyncFor)):
                add(node.target, node.iter)
            elif isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp,
                                   ast.GeneratorExp)):
                for gen in node.generators:
                    add(gen.target, gen.iter)
            elif isinstance(node, ast.withitem) and node.optional_vars:
                add(node.optional_vars, node.context_expr)
    return table


def kinds_of(name, table, seen=None):
    """INK / BOUNDARY / set() -- the readers `name` was bound from, to a fixed point."""
    seen = seen or set()
    if name in seen:
        return set()
    seen.add(name)
    found = set()
    for value in table.get(name, ()):
        for node in ast.walk(value):
            if isinstance(node, ast.Call):
                func = node.func
                called = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
                if called in INK_READERS:
                    found.add("INK")
                if called in BOUNDARY_READERS:
                    found.add("BOUNDARY")
            elif isinstance(node, ast.Name) and node.id != name:
                found |= kinds_of(node.id, table, seen)
    return found


def root(node):
    while isinstance(node, (ast.Attribute, ast.Subscript)):
        node = node.value
    return node.id if isinstance(node, ast.Name) else None


def contributing(expression, table, seen=None):
    """The expression plus every expression its local names were bound from."""
    seen = seen or set()
    trees = [expression]
    for node in ast.walk(expression):
        if isinstance(node, ast.Name) and node.id not in seen:
            seen.add(node.id)
            for value in table.get(node.id, ()):
                trees += contributing(value, table, seen)
    return trees


def multiple(site, bound):
    """The constant the site multiplies `bound` by, or 1 for a bare read."""
    for node in ast.walk(site):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
            for one, other in ((node.left, node.right), (node.right, node.left)):
                if isinstance(one, ast.Name) and one.id == bound and isinstance(other, ast.Constant):
                    return other.value
    return 1


for path, bound in BOUNDS.items():
    tree = ast.parse(pathlib.Path(path).read_text())
    print(f"\n######### {path}  (bound {bound})")
    for function, qualified in sorted(scopes(tree).items(), key=lambda kv: kv[0].lineno):
        table = bindings(function, tree)
        for node in ast.walk(function):
            if not isinstance(node, ast.Assert):
                continue
            # WIDENED: the population is no longer only the sites that read
            # the module's own bound. CARD-336 measured why -- the geometry
            # module's `drawing.left >= usable_left - 1` is a placed-edge
            # claim bound by a LITERAL, invisible to a bound-keyed filter, and
            # it is the site that reds once the HALF_PIXEL_MM site above it
            # is closed.
            reads_bound = any(
                isinstance(n, ast.Name) and n.id == bound for n in ast.walk(node)
            )
            trees = contributing(node, table)
            ink, boundary, unresolved = [], [], []
            for sub in trees:
                for attr in ast.walk(sub):
                    if not isinstance(attr, ast.Attribute):
                        continue
                    base = root(attr.value) if not isinstance(attr.value, ast.Name) else attr.value.id
                    kinds = kinds_of(base, table) if base else set()
                    if attr.attr in BOUNDARY_FIELDS and "BOUNDARY" in kinds:
                        boundary.append(attr)
                    elif attr.attr in INK_EDGES and "INK" in kinds:
                        ink.append((sub, attr))
                    elif attr.attr in INK_EDGES and not kinds and base is None:
                        unresolved.append(attr)
            # pairing, inside each contributing tree
            unpaired = []
            parents = {}
            for sub in trees:
                for n in ast.walk(sub):
                    for c in ast.iter_child_nodes(n):
                        parents[c] = n
            inks = {id(a) for _s, a in ink}
            for sub, attr in ink:
                cur, paired = attr, False
                while (cur := parents.get(cur)) is not None:
                    if isinstance(cur, (ast.BinOp, ast.Compare, ast.Call)):
                        if sum(1 for n in ast.walk(cur) if id(n) in inks) >= 2:
                            paired = True
                            break
                if not paired:
                    unpaired.append(attr)
            if not reads_bound and not ink and not boundary:
                continue
            cls = ("UNCLASSIFIED" if unresolved else
                   "boundary" if boundary and not unpaired else
                   "cancelling" if ink and not unpaired else
                   "no_extent" if not ink and not boundary else
                   "INK_VS_COORDINATE")
            print(f"  L{node.lineno:5d} {multiple(node, bound)}x  {cls:18s} {qualified}"
                  f"  ink={[a.attr for a in unpaired]} bnd={[a.attr for a in boundary]}")
