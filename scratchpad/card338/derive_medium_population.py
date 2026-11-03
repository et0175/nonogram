"""CARD-338 AC-4: the THIRD population, derived — modules that reach the
medium hazard through **the medium decision itself**.

Not a test and not under ``tests/`` (G-2, and the board's standing rule that
instruments are ``.py`` under a card's scratchpad). Read-only over the tree.

CARD-329's census has two filters, and both are filters on **how a page is
read**:

* population A — the module imports ``tests.helpers.pdf_pages``, the
  one-image reader;
* population B — a page from ``interior()``/``interior_pages()`` flows into a
  PIL image surface, directly or through a page-consuming helper.

A module can reach the same hazard through neither. ``page_medium`` is the
production decision, and a test that **asks it** branches its own read on the
declaration: the spy arm for a bitmap page, the stream arm for operators. Lift
a declaration underneath such a module and the arm it takes changes, with no
reader import and no PIL attribute anywhere in its AST. Both of CARD-329's
filters are structurally blind to it.

**Derived, not listed (AC-4).** The membership below is computed from the AST
of every module under ``tests/``; the only hand-written datum is the census
floor this card measured, and the assertion runs in the direction that catches
a module that *should* be in the population and is not:

    derived - floor  →  a new such module exists and nothing has priced it: RED

That direction is deliberate. CARD-331's defect, routed onto CARD-322, was a
guard over a hand-written set that checked every *listed* name had a source and
could not catch a name that should have been listed. Extending a list is that
defect repeating, so the list here is an expectation to be contradicted, never
the membership.

Run::

    python scratchpad/card338/derive_medium_population.py
    python scratchpad/card338/derive_medium_population.py --tests <dir>

``--tests`` points the same derivation at another tests tree, which is how the
red-on-a-new-member proof is run without editing ``tests/`` (G-2).
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

#: The medium decision itself: the production function that reads
#: ``_RASTER_DECLARATIONS``, the enum its answer is one of, and the registry.
#: A module naming any of these asks which medium a kind is written in, which
#: is the branch a lifted declaration moves.
MEDIUM_DECISION = frozenset({"page_medium", "PageMedium", "_RASTER_DECLARATIONS"})

#: Population A's filter (CARD-329, CARD-309's AC-3 verbatim).
HELPER_MODULE = "tests.helpers.pdf_pages"
READER = "pdf_pages"

#: Population A ∪ B, as CARD-329's census fixed them. Imported from the
#: sibling census rather than retyped, so the two cannot drift.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from census_five_kinds import POPULATION_A, POPULATION_B, B_HELPER  # noqa: E402

#: The third population as THIS card measured it, 2026-10-31. An expectation,
#: not the membership: see the module docstring.
MEASURED_FLOOR = ("tests/test_book_interior_type_floor.py",)


def modules(tests: Path) -> list[Path]:
    return sorted(
        path
        for path in tests.rglob("*.py")
        if path.name != "__init__.py" and "fixtures" not in path.parts
    )


def names(node: ast.Module) -> set[str]:
    """Every bare name and attribute name the module's AST mentions."""
    out: set[str] = set()
    for item in ast.walk(node):
        if isinstance(item, ast.Name):
            out.add(item.id)
        elif isinstance(item, ast.Attribute):
            out.add(item.attr)
        elif isinstance(item, ast.ImportFrom):
            out |= {alias.name for alias in item.names}
    return out


def imports_reader(node: ast.Module) -> bool:
    for item in ast.walk(node):
        if isinstance(item, ast.ImportFrom) and item.module == HELPER_MODULE:
            if READER in {alias.name for alias in item.names}:
                return True
    return False


def derive(tests: Path) -> tuple[list[tuple[str, set[str]]], list[str]]:
    census = set(POPULATION_A) | set(POPULATION_B) | set(B_HELPER)
    asks: list[tuple[str, set[str]]] = []
    third: list[str] = []
    for path in modules(tests):
        try:
            tree = ast.parse(path.read_text(), filename=str(path))
        except SyntaxError as problem:  # a tree that will not parse is a finding
            raise AssertionError(f"{path}: {problem}") from problem
        hits = MEDIUM_DECISION & names(tree)
        if not hits:
            continue
        # Relative to the tests root given, so an overlay tree reports the
        # same spelling as ``tests/`` does.
        name = "tests/" + str(path.relative_to(tests))
        asks.append((name, hits))
        if name not in census and not imports_reader(tree):
            third.append(name)
    return asks, third


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tests", default=str(ROOT / "tests"))
    args = parser.parse_args()
    tests = Path(args.tests).resolve()
    assert tests.is_dir(), f"no tests tree at {tests}"

    asks, third = derive(tests)
    assert asks, (
        f"no module under {tests} names any of {sorted(MEDIUM_DECISION)}: the "
        "medium decision has been renamed and this derivation measures nothing"
    )

    print(f"tests tree: {tests}")
    print(
        f"FILTER: a module whose AST names the medium decision itself "
        f"({', '.join(sorted(MEDIUM_DECISION))})"
    )
    print(f"\nasks the medium decision = {len(asks)}")
    for name, hits in asks:
        where = (
            "A" if name in POPULATION_A
            else "B" if name in set(POPULATION_B) | set(B_HELPER)
            else "THIRD"
        )
        print(f"    [{where:5}] {name:56} {sorted(hits)}")

    print(f"\nTHIRD POPULATION (in neither A nor B) = {len(third)}")
    for name in third:
        print(f"    {name}")

    floor = set(MEASURED_FLOOR)
    new = sorted(set(third) - floor)
    gone = sorted(floor - set(third))
    print(f"\nmeasured floor ({len(floor)}): {sorted(floor)}")
    print(f"NEW members not in the floor ({len(new)}): {new}")
    print(f"floor members no longer derived ({len(gone)}): {gone}")
    assert not new, (
        "a module reaches the medium hazard through the medium decision and no "
        f"card has priced it: {new} -- this is the finding, not a list to extend"
    )
    assert not gone, (
        f"a floor member no longer asks the medium decision: {gone} -- either "
        "it was repaired (re-measure the floor) or the filter has rotted"
    )
    print("\nOK: the third population is exactly the measured floor")
    return 0


if __name__ == "__main__":
    sys.exit(main())
