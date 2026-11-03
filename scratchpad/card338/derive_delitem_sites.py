"""CARD-338 AC-2: the probe's own shadow, derived — every
``monkeypatch.delitem`` site on the raster registry, and whether it passes
``raising=False``.

Not a test and not under ``tests/`` (G-2). Read-only over the tree.

A site **without** ``raising=False`` raises ``KeyError: <PageKind.X: 'x'>``
inside ``_pytest/monkeypatch.py`` once this card's probe has already popped the
key, and presents as a red. It is the **instrument's** red, not the
conversion's, and AC-2 is that the census reports both numbers and names these
sites so a downstream card prices the conversion and not the probe.

Derived with ``ast`` and not with ``git grep``: ``git grep -E`` does not honour
``\\b``, and a text search cannot tell a call from a docstring that quotes one
— this tree's comments quote ``_RASTER_DECLARATIONS`` and ``delitem`` in prose
in several modules.

Run::

    python scratchpad/card338/derive_delitem_sites.py
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TESTS = ROOT / "tests"
REGISTRY = "_RASTER_DECLARATIONS"


def modules() -> list[Path]:
    return sorted(
        path
        for path in TESTS.rglob("*.py")
        if path.name != "__init__.py" and "fixtures" not in path.parts
    )


def registry_argument(node: ast.AST) -> bool:
    """Is this argument the raster registry, however it is reached?"""
    for item in ast.walk(node):
        if isinstance(item, ast.Attribute) and item.attr == REGISTRY:
            return True
        if isinstance(item, ast.Name) and item.id == REGISTRY:
            return True
    return False


def kind_of(node: ast.AST) -> str:
    for item in ast.walk(node):
        if isinstance(item, ast.Attribute) and item.attr.isupper():
            return item.attr
        if isinstance(item, ast.Name) and item.id.isupper():
            return item.id
    return "?"


def main() -> int:
    by_module: dict[str, list[tuple[int, str, bool]]] = {}
    referencing: list[str] = []
    for path in modules():
        tree = ast.parse(path.read_text(), filename=str(path))
        name = str(path.relative_to(ROOT))
        touches = any(
            (isinstance(item, ast.Attribute) and item.attr == REGISTRY)
            or (isinstance(item, ast.Name) and item.id == REGISTRY)
            or (
                isinstance(item, ast.ImportFrom)
                and REGISTRY in {alias.name for alias in item.names}
            )
            for item in ast.walk(tree)
        )
        if touches:
            referencing.append(name)
        for item in ast.walk(tree):
            if not isinstance(item, ast.Call):
                continue
            func = item.func
            if not (isinstance(func, ast.Attribute) and func.attr == "delitem"):
                continue
            if not item.args or not registry_argument(item.args[0]):
                continue
            raising = None
            for keyword in item.keywords:
                if keyword.arg == "raising":
                    raising = keyword.value
            safe = isinstance(raising, ast.Constant) and raising.value is False
            kind = kind_of(item.args[1]) if len(item.args) > 1 else "?"
            by_module.setdefault(name, []).append((item.lineno, kind, safe))

    total = sum(len(sites) for sites in by_module.values())
    safe_total = sum(1 for sites in by_module.values() for _l, _k, s in sites if s)
    assert total, (
        f"no monkeypatch.delitem site on {REGISTRY} found anywhere under "
        f"{TESTS}: either the registry was renamed or this derivation is "
        "measuring nothing"
    )

    print(f"modules whose AST references {REGISTRY}: {len(referencing)}")
    for name in referencing:
        print(f"    {name}")
    print(
        f"\nmonkeypatch.delitem({REGISTRY}, ...) sites: {total} "
        f"in {len(by_module)} modules"
    )
    print(f"    with raising=False (no artefact red): {safe_total}")
    print(f"    WITHOUT raising=False (artefact cap): {total - safe_total}")
    for name, sites in sorted(by_module.items()):
        print(f"\n  {name}")
        for lineno, kind, safe in sorted(sites):
            flag = "raising=False" if safe else "RAISES -> artefact red"
            print(f"      {name}:{lineno}  {kind:16} {flag}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
