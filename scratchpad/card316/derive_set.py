"""CARD-316's population, derived — never a list copied from the card.

Population = every acceptance criterion in requirements.yml whose `test:` ref
is DEAD on BOTH resolvers (the validator's text search finds nothing, and no
`def`/`class` defines it). That is the validator of record's own notion of a
dead AC ref, taken from tests/test_check_ref_resolution.py's two resolvers
rather than re-implemented here.

Partition = the lifecycle marker that already classifies each entry:
  * `status: superseded` on the entry  -> machine-readable retirement, and the
    ONE case already handled (FR-001/AC-001..004, CARD-317, 2026-10-31), whose
    refs are deliberately kept; out of this card's scope.
  * `# alternative:` header comment    -> a criterion of a rejected DEC branch.
  * `# RETIRED` header comment         -> a criterion the model retired.
  * `# OWED` header comment            -> a forward declaration owed by a card.

ADR-0039/R2: an entry this walk cannot put in exactly one of those four boxes
exits non-zero. The card grew; it does not get covered silently.

Usage: derive_set.py            (report + exit status)
"""
import importlib.util
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
REQ = ROOT / "meta/architecture/requirements.yml"

spec = importlib.util.spec_from_file_location(
    "ccr", ROOT / "tests" / "test_check_ref_resolution.py")
ccr = importlib.util.module_from_spec(spec)
sys.modules["ccr"] = ccr
spec.loader.exec_module(ccr)

DEAD = {v.ref for v in ccr._verdicts() if not v.loose and not v.strict}

ID_RE = re.compile(r"^(\s*)- id: (AC-\d+)\s*$")
CMT_RE = re.compile(r"^\s*#")
MARKERS = (
    (re.compile(r"^#\s*alternative:", re.I), "alternative"),
    (re.compile(r"^#\s*RETIRED\b"), "retired"),
    (re.compile(r"^#\s*OWED\b"), "owed"),
)


def entries():
    """(ac_id, id_line, header_comments, {key: (value, line)}) per AC."""
    lines = REQ.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        m = ID_RE.match(line)
        if not m:
            continue
        indent = len(m.group(1))
        j = i - 1
        header = []
        while j >= 0 and CMT_RE.match(lines[j]):
            header.append(lines[j].strip())
            j -= 1
        header.reverse()
        body, k = {}, i + 1
        while k < len(lines):
            ln = lines[k]
            if ln.strip() and len(ln) - len(ln.lstrip()) <= indent:
                break
            km = re.match(r"^\s*([a-z_]+):\s*(\S.*?)\s*$", ln)
            if km:
                body.setdefault(km.group(1), (km.group(2), k + 1))
            k += 1
        yield m.group(2), i + 1, header, body


def main():
    boxes = {"superseded": [], "alternative": [], "retired": [], "owed": []}
    unclassifiable = []
    for ac_id, id_line, header, body in entries():
        if "test" not in body:
            continue
        ref, ref_line = body["test"]
        if ref not in DEAD:
            continue
        if body.get("status", ("", 0))[0] == "superseded":
            box = "superseded"
        else:
            box = next((lbl for rx, lbl in MARKERS
                        for h in header if rx.match(h)), None)
        if box is None:
            unclassifiable.append((ac_id, id_line, ref))
            continue
        boxes[box].append((ac_id, id_line, ref_line, ref))

    print(f"dead AC `test:` refs in requirements.yml: "
          f"{sum(len(v) for v in boxes.values()) + len(unclassifiable)}\n")
    for box in ("alternative", "retired", "owed", "superseded"):
        scope = "OUT OF SCOPE (CARD-317)" if box == "superseded" else "IN SCOPE"
        print(f"-- {box}: {len(boxes[box])}  [{scope}]")
        for ac_id, id_line, ref_line, ref in boxes[box]:
            print(f"     {ac_id}  id@{id_line}  test@{ref_line}  {ref}")
    in_scope = sum(len(boxes[b]) for b in ("alternative", "retired", "owed"))
    print(f"\nin scope: {in_scope}")
    if unclassifiable:
        print("\nFAILURE (ADR-0039/R2) — unclassifiable dead AC refs, so the "
              "card's population is not the one it was cut for:")
        for ac_id, id_line, ref in unclassifiable:
            print(f"  {ac_id} id@{id_line} {ref}")
        return 1
    return 0


sys.exit(main())
