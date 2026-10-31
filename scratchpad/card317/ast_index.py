"""Resolve names against an ``ast`` index of ``tests/`` and ``src/``.

CARD-317's second instrument, and the one that answers the only question a
census move has: did each entrant and each departure gain or lack a real
``def``/``class``? ``git grep`` answers it with a regex over text; this
answers it by parsing, so the two are independent readings and a regex that
silently matches nothing (CARD-317's G-3: ``\\b`` is undefined in POSIX ERE)
cannot pass for a clean verdict here.

Names are read from FILES given on argv, never written in this module, for the
reason in ``census_dump.py``'s docstring.

Usage::

    python scratchpad/card317/ast_index.py <names-file> [<names-file>...]

Each file is one name per line. Output is one line per name: the definition
sites, or ``(nowhere)``.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ROOTS = ("tests", "src", "player", "scripts", "migrations")


def index() -> dict[str, list[str]]:
    """``name -> ['<path>:<line> (def|class)', ...]`` over every parsed module."""
    out: dict[str, list[str]] = {}
    parsed = 0
    for root in ROOTS:
        for path in sorted((REPO_ROOT / root).rglob("*.py")):
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except (OSError, SyntaxError) as exc:
                raise SystemExit(f"{path}: unparsable ({exc})")
            parsed += 1
            rel = path.relative_to(REPO_ROOT).as_posix()
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    kind = "def"
                elif isinstance(node, ast.ClassDef):
                    kind = "class"
                else:
                    continue
                out.setdefault(node.name, []).append(f"{rel}:{node.lineno} ({kind})")
    if parsed < 100:
        raise SystemExit(f"only {parsed} modules parsed -- the walk is broken")
    print(f"# {parsed} modules parsed, {len(out)} distinct names", file=sys.stderr)
    return out


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    table = index()
    # Both directions, on the table itself: a name it holds and a name it
    # cannot hold. Without this an empty index would report every name dead.
    probe = next(iter(table))
    assert table[probe], probe
    assert "zzz_no_such_symbol_card317" not in table
    for name_file in sys.argv[1:]:
        for name in Path(name_file).read_text(encoding="utf-8").split():
            sites = table.get(name) or ["(nowhere)"]
            print(f"{name}\n    {'; '.join(sites)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
