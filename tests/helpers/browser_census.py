"""A pytest plugin: what collection knows about the suite's browser tests.

Loaded only by ``tests/test_browser_fixture_scope.py``'s child collection
(``-p tests.helpers.browser_census``), never by the suite itself. It writes one
JSON file, named by the ``BROWSER_CENSUS_OUT`` environment variable, holding
for every collected item that either carries the ``browser`` marker or reaches
a browser fixture:

* its node id, its file, and whether it carries the marker;
* every fixture it reaches, with that fixture's scope and defining module.

"Reaches" is the item's static fixture closure **plus** every fixture named by
a literal ``request.getfixturevalue("<name>")`` in the test or in a fixture it
reaches, followed transitively (CARD-527 review 1, F-003): ``browser_page``
itself gets Chromium's page that way, so a closure read from signatures alone
would never see ``page``, ``context`` or ``browser``. A ``getfixturevalue``
whose argument is not a string literal cannot be followed; it is reported as
``"<dynamic>"`` so the guard can refuse it rather than pass it.
"""

from __future__ import annotations

import ast
import inspect
import json
import os
import textwrap

#: The fixtures whose presence makes an item a browser test whether or not it
#: is marked (CARD-527 review 1, F-002).
BROWSER_FIXTURES = frozenset({"browser_page", "browser_type"})

_SOURCE_NAMES: dict[object, tuple[str, ...]] = {}


def _getfixturevalue_names(function: object) -> tuple[str, ...]:
    """The literal names ``function`` passes to ``getfixturevalue``."""
    if function in _SOURCE_NAMES:
        return _SOURCE_NAMES[function]
    names: list[str] = []
    try:
        tree = ast.parse(textwrap.dedent(inspect.getsource(function)))
    except (OSError, TypeError, SyntaxError):
        tree = None
    if tree is not None:
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "getfixturevalue"
            ):
                argument = node.args[0] if node.args else None
                if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                    names.append(argument.value)
                else:
                    names.append("<dynamic>")
    _SOURCE_NAMES[function] = tuple(names)
    return _SOURCE_NAMES[function]


def _reached(item) -> dict[str, dict[str, object]]:
    manager = item.session._fixturemanager
    found: dict[str, dict[str, object]] = {}
    queue = list(item.fixturenames) + list(_getfixturevalue_names(getattr(item, "obj", None)))
    while queue:
        name = queue.pop()
        if name in found:
            continue
        if name == "<dynamic>":
            found[name] = {"scope": "?", "module": "?"}
            continue
        definitions = manager.getfixturedefs(name, item)
        if not definitions:
            continue  # a parametrize argument, or a fixture pytest itself supplies late
        definition = definitions[-1]
        module = inspect.getmodule(definition.func)
        found[name] = {
            "scope": definition.scope,
            "module": module.__name__ if module else "?",
        }
        queue.extend(definition.argnames)
        queue.extend(_getfixturevalue_names(definition.func))
    found.pop("request", None)
    return found


def pytest_collection_finish(session) -> None:
    out = os.environ.get("BROWSER_CENSUS_OUT")
    if not out:
        return
    records = []
    for item in session.items:
        marked = item.get_closest_marker("browser") is not None
        if not marked and not BROWSER_FIXTURES & set(getattr(item, "fixturenames", ())):
            # Unmarked and not statically a browser test: still followed, so a
            # browser fixture reached only through getfixturevalue counts.
            reached = _reached(item)
            if not BROWSER_FIXTURES & set(reached):
                continue
        else:
            reached = _reached(item)
        records.append(
            {
                "nodeid": item.nodeid,
                "file": item.nodeid.split("::")[0],
                "marked": marked,
                "fixtures": reached,
            }
        )
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(records, handle, indent=1, sort_keys=True)
