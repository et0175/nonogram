"""CARD-338 AC-2: the ``delitem`` sites, derived — every
``monkeypatch.delitem`` site on the raster registry, and whether it passes
``raising=False``.

Not a test and not under ``tests/`` (G-2). Read-only over the tree.

A site **without** ``raising=False`` raises ``KeyError: <PageKind.X: 'x'>``
inside ``_pytest/monkeypatch.py`` once the key it names is gone, and presents
as a red. **This script used to call that red the instrument's and not the
conversion's. That framing is measured FALSE and is withdrawn**
(ADR-0039/R4 — a refuted figure is retracted everywhere it was written, the
executable places included): ``fidelity_to_the_end_state.py`` counted the
**identical** ``KeyError`` on the E1 tree, five entries deleted in ``src/``
with no probe loaded at all, so the probe's artefact is **0** and these are
reds the conversion owns. AC-2 is that the census labels the share and names
these sites, so a downstream card prices them as work rather than discounting
them as noise.

**A SITE IS NOT A RED, and this is where that confusion starts.** Of the 17
sites, 2 pass ``raising=False`` and 15 can raise; of those 15, two name
``DIVIDER``, which this card's probe does not lift, leaving **13 sites that can
raise**. The census separately measures **13 reds**. The two figures agreeing
is a coincidence of this tree and not a derivation: one site
(``tests/property/test_book_export_interior.py:1388``) produces **5** reds, and
two sites (``tests/test_book_pdf.py:3747``, ``:3774``) are ``delitem`` calls
inside ``for kind in self._interior_kinds()`` loops covering **4+ kinds each**
— printed below as ``LOOP:<var>`` rather than as a kind, because the kind is
not knowable by ``ast``. Quote the 13 reds from the census; quote the 13 sites
from here; never derive one from the other.

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
    """The kind a site names, or ``LOOP:<var>`` when it names a variable.

    A lowercase ``Name`` is a loop or parameter variable, so the site covers
    every kind the loop yields -- which is why this derivation reports SITES
    and the census reports REDS, and why the two are never divided into each
    other. Returning a bare ``?`` here (as this did) hid exactly that.
    """
    for item in ast.walk(node):
        if isinstance(item, ast.Attribute) and item.attr.isupper():
            return item.attr
        if isinstance(item, ast.Name) and item.id.isupper():
            return item.id
    for item in ast.walk(node):
        if isinstance(item, ast.Name):
            return f"LOOP:{item.id}"
        if isinstance(item, ast.Attribute):
            return f"LOOP:{item.attr}"
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
    print(f"    with raising=False (cannot raise): {safe_total}")
    print(f"    WITHOUT raising=False (can raise): {total - safe_total}")
    print("    NOTE: these are SITES, not reds. A LOOP: site covers every kind "
          "its loop yields,")
    print("          and one literal site was measured at 5 reds -- take the "
          "red count from the census.")
    for name, sites in sorted(by_module.items()):
        print(f"\n  {name}")
        for lineno, kind, safe in sorted(sites):
            flag = "raising=False" if safe else "RAISES -> can red"
            print(f"      {name}:{lineno}  {kind:16} {flag}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
