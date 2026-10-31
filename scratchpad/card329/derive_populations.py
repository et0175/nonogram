"""CARD-329 AC-3: derive both reader populations by AST, state each filter.

Not a test and not under ``tests/`` (G-7). Read-only over the tree.

Two populations, two **filters**, stated here as code so the filter is what is
asserted and not the count (AC-3):

* **Population A** -- a module whose AST contains an ``ImportFrom`` of
  ``tests.helpers.pdf_pages`` that names ``pdf_pages`` itself, the one-image
  reader. This is CARD-309's AC-3 filter verbatim. A module importing only
  ``pdf_page_count`` or ``same_page`` is NOT in A: those two never touch an
  image XObject, so the ``KeyError: b'XObject'`` hazard cannot reach them.
* **Population B** -- a module that reaches the same hazard WITHOUT importing
  the reader: it obtains an interior page from ``interior()`` /
  ``interior_pages()`` (or from a helper that returns one) and that page is
  **used as an image anywhere downstream, however indirectly**. The filter is
  the HAZARD, not a direct PIL attribute: a module that hands the page to a
  helper which rasterises it is in B even though its own AST touches no PIL
  attribute. That is the gap between the card's 9 and the orchestrator's 6.

B is derived in two passes because the hazard crosses a call boundary:

  pass 1  find the helper functions that CONSUME a page as an image --
          any function in ``tests/helpers/**`` or a test module whose body
          reads a PIL image attribute/method off one of its own parameters.
  pass 2  a module is in B if it has a page source AND the page flows into
          either a PIL attribute directly or a call to a pass-1 consumer.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TESTS = ROOT / "tests"

HELPER_MODULE = "tests.helpers.pdf_pages"
READER = "pdf_pages"

#: Names that obtain an interior page (or pages) from the product.
PAGE_SOURCES = frozenset({"interior", "interior_pages"})

#: PIL image surface a page is used *as an image* through. Reading any of
#: these off a page is the hazard: a page written as operators has no image
#: XObject, so the reader that produced it raises before any of these run.
PIL_IMAGE_SURFACE = frozenset(
    {
        "size", "width", "height", "mode", "getpixel", "crop", "convert",
        "load", "resize", "reduce", "tobytes", "getbbox", "getdata",
        "point", "split", "paste", "copy", "save", "transpose", "rotate",
    }
)


def modules() -> list[Path]:
    return sorted(
        path
        for path in TESTS.rglob("*.py")
        if path.name != "__init__.py" and "fixtures" not in path.parts
    )


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(), filename=str(path))


# --------------------------------------------------------------- population A
def imports_from_helper(node: ast.Module) -> set[str]:
    names: set[str] = set()
    for item in ast.walk(node):
        if isinstance(item, ast.ImportFrom) and item.module == HELPER_MODULE:
            names |= {alias.name for alias in item.names}
    return names


# --------------------------------------------------------------- population B
def _attr_names(node: ast.AST) -> set[str]:
    return {
        item.attr for item in ast.walk(node) if isinstance(item, ast.Attribute)
    }


def _called_names(node: ast.AST) -> set[str]:
    out: set[str] = set()
    for item in ast.walk(node):
        if isinstance(item, ast.Call):
            func = item.func
            if isinstance(func, ast.Name):
                out.add(func.id)
            elif isinstance(func, ast.Attribute):
                out.add(func.attr)
    return out


def consumers(paths: list[Path]) -> set[str]:
    """Pass 1: functions that use one of their own parameters as an image,
    **however indirectly** -- closed to a fixed point.

    A page handed to one of these is used as an image, so a module that only
    calls it is still exposed to the hazard. This is what the orchestrator's
    attribute-only filter missed.

    The closure matters and was measured: at depth 1 this walk does NOT
    recognise ``page_ink.drawing_of``, the tree's central pixel oracle, which
    reads nothing off its own ``page`` and passes it to ``_dark`` one frame
    in. Mirrors ``tests/test_book_pdf.py``'s
    ``_page_consuming_functions`` -- the two are independent transcriptions
    of one filter, and a disagreement between them is a finding.
    """
    found: set[str] = set()
    functions = []
    for path in paths:
        for item in ast.walk(tree(path)):
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(
                    (
                        item.name,
                        {
                            arg.arg
                            for arg in (
                                item.args.posonlyargs
                                + item.args.args
                                + item.args.kwonlyargs
                            )
                        },
                        item,
                    )
                )

    for name, params, node in functions:
        for inner in ast.walk(node):
            if (
                isinstance(inner, ast.Attribute)
                and inner.attr in PIL_IMAGE_SURFACE
                and isinstance(inner.value, ast.Name)
                and inner.value.id in params
            ):
                found.add(name)
                break

    def hands_on(node, params) -> bool:
        for inner in ast.walk(node):
            if not isinstance(inner, ast.Call):
                continue
            called = (
                inner.func.id
                if isinstance(inner.func, ast.Name)
                else getattr(inner.func, "attr", None)
            )
            if called not in found:
                continue
            for argument in list(inner.args) + [k.value for k in inner.keywords]:
                if isinstance(argument, ast.Name) and argument.id in params:
                    return True
        return False

    for _round in range(len(functions) + 1):
        grown = {
            name
            for name, params, node in functions
            if name not in found and hands_on(node, params)
        }
        if not grown:
            break
        found |= grown
    return found


def main() -> int:
    paths = modules()
    consumer_names = consumers(paths)

    population_a: list[str] = []
    imports_anything: list[str] = []
    for path in paths:
        names = imports_from_helper(tree(path))
        if names:
            imports_anything.append(rel(path))
        if READER in names:
            population_a.append(rel(path))

    population_b: list[tuple[str, str]] = []
    unclassified: list[str] = []
    for path in paths:
        name = rel(path)
        node = tree(path)
        source_hits = PAGE_SOURCES & (_attr_names(node) | _called_names(node))
        if not source_hits:
            continue
        pil_hits = PIL_IMAGE_SURFACE & _attr_names(node)
        consumer_hits = consumer_names & _called_names(node)
        if name in population_a:
            continue
        if pil_hits:
            population_b.append((name, f"PIL surface {sorted(pil_hits)[:3]}"))
        elif consumer_hits:
            population_b.append(
                (name, f"hands the page to {sorted(consumer_hits)[:3]}")
            )
        else:
            unclassified.append(name)

    print(f"FILTER A: ImportFrom {HELPER_MODULE} naming {READER!r}")
    print(f"A = {len(population_a)}")
    for name in population_a:
        print(f"    {name}")
    print(
        f"\n(for the record: modules importing ANYTHING from the helper = "
        f"{len(imports_anything)} -- the orchestrator's 14)"
    )
    for name in imports_anything:
        if name not in population_a:
            print(f"    NOT in A: {name}")

    print(
        f"\nFILTER B: a page from {sorted(PAGE_SOURCES)} is used as an image "
        f"downstream, directly or via a page-consuming helper"
    )
    print(f"B\\A = {len(population_b)}")
    for name, why in population_b:
        print(f"    {name}   <- {why}")

    print(f"\nUNCLASSIFIED = {len(unclassified)} (ADR-0039/R2: any is a FAILURE)")
    for name in unclassified:
        print(f"    {name}")
    print(f"\nconsumer functions found in pass 1 = {len(consumer_names)}")
    print("   ", sorted(consumer_names))
    return 0


if __name__ == "__main__":
    sys.exit(main())
