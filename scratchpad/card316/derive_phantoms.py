"""Derive the phantom-test-ref population in requirements.yml from an ast index.

Not a list: an index of every class/def name defined anywhere under tests/ and
src/, intersected against every `test:` key carried by an acceptance criterion.
Classification comes from the comment block directly above each entry.
ADR-0039/R2: an entry the walk cannot classify is a FAILURE, not an omission.
"""
import ast
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]


def symbol_index(*dirs):
    """name -> sorted list of 'path:line' for every class/def definition."""
    idx = {}
    for d in dirs:
        base = ROOT / d
        for p in sorted(base.rglob("*.py")):
            if "__pycache__" in p.parts:
                continue
            try:
                tree = ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
            except SyntaxError as exc:            # must not be silent
                raise SystemExit(f"UNPARSEABLE {p}: {exc}")
            for node in ast.walk(tree):
                if isinstance(node, (ast.ClassDef, ast.FunctionDef,
                                     ast.AsyncFunctionDef)):
                    idx.setdefault(node.name, []).append(
                        f"{p.relative_to(ROOT)}:{node.lineno}")
    return idx


ID_RE = re.compile(r"^(\s*)- id: (AC-\d+|EC-\d+)\s*$")
KEY_RE = re.compile(r"^\s*(test|kind):\s*(\S.*?)\s*$")
COMMENT_RE = re.compile(r"^\s*#\s?(.*)$")
MARKERS = (("# alternative:", "alternative"),
           ("# RETIRED", "retired"),
           ("# OWED", "owed"))


def criteria(path):
    """Yield (crit_id, id_line_no, header_comments, {key: (value, line_no)})."""
    lines = path.read_text(encoding="utf-8").splitlines()
    out = []
    for i, line in enumerate(lines):
        m = ID_RE.match(line)
        if not m:
            continue
        indent = len(m.group(1))
        # header comment block: contiguous comment lines immediately above
        header = []
        j = i - 1
        while j >= 0 and COMMENT_RE.match(lines[j]):
            header.append(lines[j].strip())
            j -= 1
        header.reverse()
        # body: lines until dedent to <= indent that are not comments
        body = {}
        k = i + 1
        while k < len(lines):
            ln = lines[k]
            if ln.strip() and (len(ln) - len(ln.lstrip())) <= indent:
                break
            km = KEY_RE.match(ln)
            if km:
                body[km.group(1)] = (km.group(2), k + 1)
            k += 1
        out.append((m.group(2), i + 1, header, body))
    return out


def main():
    req = ROOT / "meta/architecture/requirements.yml"
    idx = symbol_index("tests", "src")
    rows = criteria(req)
    declared = [(cid, ln, hdr, body) for cid, ln, hdr, body in rows if "test" in body]
    phantoms = []
    for cid, ln, hdr, body in declared:
        name, tln = body["test"]
        if name in idx:
            continue
        phantoms.append((cid, ln, tln, name, hdr, body.get("kind", ("-", 0))[0]))

    print(f"criteria with a test: key           {len(declared)}")
    print(f"ast index symbols (tests/ + src/)   {len(idx)}")
    print(f"phantom (no class/def anywhere)     {len(phantoms)}")
    print()
    unclassified = []
    for cid, ln, tln, name, hdr, kind in phantoms:
        tag = None
        for prefix, label in MARKERS:
            if any(h.startswith(prefix) for h in hdr):
                tag = label
                break
        if tag is None:
            unclassified.append(cid)
        print(f"{cid:>8}  id@{ln:<5} test@{tln:<5} kind={kind:<12} "
              f"class={tag}  {name}")
        for h in hdr:
            print(f"             | {h}")
    print()
    if unclassified:
        print(f"FAILURE (ADR-0039/R2): unclassifiable entries: {unclassified}")
        return 1
    print("every phantom classified by its own header comment")
    return 0


if __name__ == "__main__":
    sys.exit(main())
