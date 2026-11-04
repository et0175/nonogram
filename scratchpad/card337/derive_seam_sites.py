"""CARD-337 item 0: where CARD-329's ``interior_images`` seam can GO, derived.

Not a test and not under ``tests/`` (G-8). Read-only over the tree.

CARD-329's routing says each of the nine modules needs "the identical one-line
edit (``interior_images`` at the module's one page-source function)". That
sentence has two load-bearing claims, and this walk derives both instead of
assuming them:

1. the module HAS a page source -- a call to ``...interior_pages(...)`` or
   ``...interior(...)``, which is what hands back a page in its own medium;
2. that source is ONE module-level function -- which is what makes the edit
   one line.

A module reading an exported book's BYTES (``pdf_pages(data)``) has neither:
``tests/helpers/pdf_pages.pdf_pages`` already reads both media since CARD-329,
so there is no page object to wrap and the seam is not merely unnecessary there
but inapplicable.

Per ADR-0039/R2 a module this walk cannot place in one of its classes is a
FAILURE, not a skip: ``UNCLASSIFIED`` exits non-zero.

Run::

    python scratchpad/card337/derive_seam_sites.py
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

#: The card's thirteen ``Touches`` paths, in the card's own order.
TOUCHES = (
    "tests/test_book_pdf_band.py",
    "tests/test_book_pdf_memory.py",
    "tests/test_book_pdf_ink_mode.py",
    "tests/property/test_book_export_interior.py",
    "tests/test_book_export_interior_cover.py",
    "tests/test_book_proof_pages.py",
    "tests/test_book_solved_answer_key.py",
    "tests/test_book_divider_pages_option.py",
    "tests/property/test_book_pairing.py",
    "tests/test_book_arrange_page_breaks.py",
    "tests/test_book_pdf_levels.py",
    "tests/test_book_pdf_two_up.py",
    "tests/test_book_interior_type_floor.py",
)

#: The generator methods that hand back a page in **the medium its kind
#: declares**. ``interior_pages`` returns that list; ``interior`` returns a
#: decided interior whose ``.pages`` is that list. Those are the two calls a
#: lifted declaration changes the return type of, and so the only two the seam
#: has anything to wrap.
PAGE_SOURCES = frozenset({"interior_pages", "interior"})

#: NOT a page source, and keeping it out of the set above is the whole
#: correctness of this walk. ``interior_stream`` is the **vector-only arm**: it
#: returns operators by contract, at this commit and after CARD-322, so a
#: reading through it is already medium-gated (CARD-299's shape) and wrapping it
#: in ``interior_images`` would delete the vector reading rather than repair it.
#: Counted and printed so a module whose pages come only from here is visibly
#: a module with no seam site, not a module this walk overlooked.
VECTOR_ARM = "interior_stream"

#: The seam itself, so a module that already carries it is not counted as owing
#: one (CARD-329 landed it in five modules; two of those are in TOUCHES).
SEAM = "interior_images"

#: The byte reader, which already reads both media -- a module whose pages come
#: from here has no page object for the seam to wrap.
BYTE_READER = "pdf_pages"


def _enclosing(tree: ast.Module) -> dict[int, str]:
    """Map every node id to the kind of scope that encloses it."""
    where: dict[int, str] = {}

    def walk(node: ast.AST, scope: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                inner = "module-level def" if scope == "module" else "nested def"
                where[id(child)] = scope
                walk(child, inner)
            elif isinstance(child, ast.ClassDef):
                walk(child, "class body")
            else:
                where[id(child)] = scope
                walk(child, scope)

    walk(tree, "module")
    return where


def _calls(tree: ast.Module, attr: frozenset[str] | str) -> list[ast.Call]:
    wanted = {attr} if isinstance(attr, str) else attr
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = (
            func.attr if isinstance(func, ast.Attribute)
            else func.id if isinstance(func, ast.Name)
            else None
        )
        if name in wanted:
            out.append(node)
    return out


def _module_level_defs_holding(tree: ast.Module, nodes: list[ast.Call]) -> set[str]:
    """Which module-level ``def``s contain any of ``nodes``."""
    found: set[str] = set()
    targets = {id(node) for node in nodes}
    for item in tree.body:
        if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if any(id(child) in targets for child in ast.walk(item)):
            found.add(item.name)
    return found


def main() -> int:
    rows = []
    unclassified = []
    for rel in TOUCHES:
        path = ROOT / rel
        assert path.exists(), f"{rel}: not in the tree -- Touches is stale"
        tree = ast.parse(path.read_text())
        sources = _calls(tree, PAGE_SOURCES)
        seams = _calls(tree, SEAM)
        readers = _calls(tree, BYTE_READER)
        arms = _calls(tree, VECTOR_ARM)
        holders = _module_level_defs_holding(tree, sources)
        inline = len(sources) - sum(
            1
            for node in sources
            if any(
                id(node) in {id(c) for c in ast.walk(item)}
                for item in tree.body
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
            )
        )

        if seams:
            cls = "S0 seam ALREADY present"
        elif not sources:
            cls = "S3 NO page source at all -- seam INAPPLICABLE"
        elif len(holders) == 1 and inline == 0:
            cls = "S1 one module-level page source -- one-line seam"
        elif holders:
            cls = f"S2 {len(holders)} module-level source(s) + {inline} inline"
        elif inline:
            cls = f"S2b NO module-level source; {inline} inline site(s)"
        else:
            cls = "UNCLASSIFIED"
            unclassified.append(rel)
        rows.append((rel, cls, len(sources), len(seams), len(readers),
                     len(arms), sorted(holders)))

    width = max(len(rel) for rel, *_ in rows)
    print(f"{'module':{width}}  {'class':40} src seam pdf_pages vec_arm  holders")
    for rel, cls, nsrc, nseam, nread, narm, holders in rows:
        print(f"{rel:{width}}  {cls:40} {nsrc:3} {nseam:4} {nread:9} {narm:7}  "
              f"{', '.join(holders) or '-'}")

    counts: dict[str, int] = {}
    for _rel, cls, *_ in rows:
        counts[cls.split(" ")[0]] = counts.get(cls.split(" ")[0], 0) + 1
    print("\nby class:", ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))

    if unclassified:
        print("\nFAIL (ADR-0039/R2): this walk could not place "
              f"{len(unclassified)} module(s): {unclassified}")
        return 1
    print("\nOK: every Touches module is placed in exactly one class.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
