"""CARD-139 — one import style in the admin package (COMP-009).

    AC-1  no module under ``src/nonogram/admin/`` uses a relative import
          TestAdminImports_NoRelativeImports
    AC-2  importing the app under a ``src.``-prefixed name does not create a
          second copy of ``book_plan``
          TestAdminImports_PackageTreeCannotDouble
    AC-3  Print setup renders a book whose plan is **stored**, with no
          ``ValueError`` from ``Plan.cell``, under either import name
          TestAdminImports_StoredPlanRendersUnderEitherImportName

What broke, 2026-09-23, on the owner's live panel: launched as
``flask --app src.nonogram.admin.app``, Python loads the admin package twice.
``nonogram.admin.book_plan`` and ``src.nonogram.admin.book_plan`` both sit in
``sys.modules`` with two distinct ``LongestSideBucket`` enum classes whose
members compare equal to nothing across the divide. ``app.py`` took
``PLAN_BUCKETS`` from its *relative* import while ``book_manager`` — absolute,
like the rest of the package — built the stored ``DistributionPlan``, so
``Plan.cell`` reached ``BUCKETS.index(bucket)`` with a bucket from the other
module and raised ``ValueError: tuple.index(x): x not in tuple``. It fires only
once a plan is *stored*: a plan-less book renders ``DEFAULT_PLAN``, which comes
from app's own copy and is therefore self-consistent, which is why the defect
read as a data bug.

Three tests for three different things, deliberately:

* AC-1 is the *style* rule, walked over the files on disk in the manner of the
  ADR-0007 layering guard in ``tests/test_cli.py`` — so an admin module a later
  card adds is covered the day it is written, not when someone remembers to
  list it here.
* AC-2 is the *property* the style rule exists to buy, stated directly rather
  than through a proxy: import the app under both names and count the
  ``book_plan`` modules. It runs in a **subprocess**, because importing the same
  package twice is exactly what it is testing and doing that in-process would
  leave a duplicate tree in the suite's own ``sys.modules``.
* AC-3 is the regression: the screen that crashed, on a book whose plan is
  stored, under both import names. Also a subprocess, for the same reason.
"""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

# --------------------------------------------------------------------------
# Where the package is, and the walk over it
# --------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[1]
_ADMIN_DIR = _REPO_ROOT / "src" / "nonogram" / "admin"

#: The ``src.``-prefixed import only exists in a source checkout. Everything in
#: this module is about that layout, so an installed-only checkout skips rather
#: than passing vacuously.
_SOURCE_CHECKOUT = (_ADMIN_DIR / "app.py").is_file()

_needs_source = pytest.mark.skipif(
    not _SOURCE_CHECKOUT,
    reason="no src/ layout in this checkout: the src.-prefixed import cannot exist",
)

#: Long enough for a cold import of the admin app plus Pillow/NumPy on a busy
#: machine; short enough that a genuine hang is reported rather than waited on.
_SUBPROCESS_TIMEOUT = 300


def _admin_modules() -> dict[str, Path]:
    """Every module under ``admin/``, as ``{dotted name: file}``.

    Found by walking the directory, not by listing names, so the rule below
    covers a module the day it lands (the precedent is ``_discover_modules``
    in ``tests/test_cli.py``).
    """
    modules: dict[str, Path] = {}
    for path in sorted(_ADMIN_DIR.rglob("*.py")):
        parts = path.relative_to(_ADMIN_DIR).with_suffix("").parts
        if parts[-1] == "__init__":  # a package is named by its directory
            parts = parts[:-1]
        dotted = ".".join(("nonogram", "admin", *parts)).rstrip(".")
        modules[dotted] = path
    return modules


def _relative_imports_in_source(source: str, label: str) -> list[str]:
    """Every ``from .x import y`` in ``source``, as reportable strings.

    Takes text rather than a path so the rule can be exercised against a
    fabricated module below and cannot pass because the walk is broken.
    """
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom) and node.level > 0:
            names = ", ".join(alias.name for alias in node.names)
            found.append(f"{label}:{node.lineno}: from {'.' * node.level}{node.module or ''} import {names}")
    return found


def _relative_imports(path: Path) -> list[str]:
    return _relative_imports_in_source(
        path.read_text(encoding="utf-8"), str(path.relative_to(_REPO_ROOT))
    )


# --------------------------------------------------------------------------
# AC-1 — the style rule
# --------------------------------------------------------------------------


@_needs_source
class TestAdminImports_NoRelativeImports:
    """AC-1 — no module under ``src/nonogram/admin/`` uses a relative import.

    Stated as a property of the tree rather than as a count: CARD-139 was cut
    against 13 relative imports and 15 were there by the time it ran, because
    other admin cards had landed in between. A count would have gone stale; the
    property cannot.
    """

    def test_no_module_uses_a_relative_import(self) -> None:
        offenders = [
            line
            for path in _admin_modules().values()
            for line in _relative_imports(path)
        ]

        assert not offenders, (
            "a relative import under src/nonogram/admin/ lets the package load "
            "twice under two names (CARD-139); write it absolutely, as "
            "`from nonogram.admin.x import y`:\n  " + "\n  ".join(offenders)
        )

    def test_the_walk_actually_sees_the_package(self) -> None:
        """Guard the guard: an empty or misrooted walk must not pass silently."""
        modules = _admin_modules()

        assert {
            "nonogram.admin",
            "nonogram.admin.app",
            "nonogram.admin.book_plan",
            "nonogram.admin.book_manager",
        } <= set(modules)
        # The package is well past a dozen modules; a walk that found only a
        # handful has lost its root.
        assert len(modules) >= 12

    def test_the_rule_catches_a_relative_import(self) -> None:
        """The rule is exercised against source that breaks it, in both forms."""
        assert _relative_imports_in_source("from .book_plan import BUCKETS", "f.py")
        assert _relative_imports_in_source("from ..db import models", "f.py")
        assert _relative_imports_in_source("from . import book_plan", "f.py")
        assert not _relative_imports_in_source(
            "from nonogram.admin.book_plan import BUCKETS\nimport os\n", "f.py"
        )


# --------------------------------------------------------------------------
# The subprocess harness
# --------------------------------------------------------------------------


def _run_in_subprocess(script: str, *args: str) -> str:
    """Run ``script`` against this checkout in a fresh interpreter.

    A subprocess, not an import, because these tests deliberately load the
    admin package under a second name — the very thing the fix prevents from
    happening by accident. Doing it in-process would leave the duplicate tree
    in the suite's own ``sys.modules`` for every later test to trip over.

    The environment reproduces how the panel is launched: the repo root on the
    path (so ``src.nonogram...`` resolves) alongside ``src`` (so
    ``nonogram...`` resolves), in-memory storage, and loopback with no
    credential, which is the admin app's local mode.
    """
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        p
        for p in (str(_REPO_ROOT), str(_REPO_ROOT / "src"), env.get("PYTHONPATH", ""))
        if p
    )
    env["TESTING"] = "true"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    # In-memory storage and local mode: this module is about import names, and
    # a stray DATABASE_URL or ADMIN_ALLOWED_HOST in the developer's shell would
    # change what the app under test even is.
    for leaked in ("DATABASE_URL", "ADMIN_ALLOWED_HOST", "ADMIN_USER", "ADMIN_PASSWORD"):
        env.pop(leaked, None)

    result = subprocess.run(
        [sys.executable, "-c", script, *args],
        cwd=str(_REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=_SUBPROCESS_TIMEOUT,
    )
    assert result.returncode == 0, (
        f"the admin app failed to load or render under {args or ('both names',)}"
        f" (exit {result.returncode})\n"
        f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
    )
    return result.stdout


#: Asserts the checkout under test is the one on the path, so neither
#: subprocess can quietly measure some other editable install.
_PIN_CHECKOUT = """
import pathlib, nonogram.admin
here = pathlib.Path(%r).resolve()
loaded = pathlib.Path(nonogram.admin.__file__).resolve()
assert here in loaded.parents, f"nonogram.admin resolved outside the checkout: {loaded}"
"""


# --------------------------------------------------------------------------
# AC-2 — the tree cannot double
# --------------------------------------------------------------------------

_DOUBLING_SCRIPT = (
    """
import json, sys
"""
    + _PIN_CHECKOUT
    + """
import src.nonogram.admin.app as prefixed
import nonogram.admin.app as plain

print(json.dumps({
    "book_plan": sorted(n for n in sys.modules if n.endswith("nonogram.admin.book_plan")),
    "book_manager": sorted(n for n in sys.modules if n.endswith("nonogram.admin.book_manager")),
    "one_bucket_tuple": prefixed.PLAN_BUCKETS is plain.PLAN_BUCKETS,
    "one_enum_class": type(prefixed.PLAN_BUCKETS[0]) is type(plain.PLAN_BUCKETS[0]),
}))
"""
)


@pytest.fixture(scope="module")
def loaded() -> dict:
    """What one interpreter holds after importing the app under both names."""
    return json.loads(_run_in_subprocess(_DOUBLING_SCRIPT % (str(_REPO_ROOT),)))


@_needs_source
class TestAdminImports_PackageTreeCannotDouble:
    """AC-2 — a ``src.``-prefixed import creates no second copy of ``book_plan``.

    The property that actually broke, stated as itself. The app module is
    genuinely loaded twice here — once as ``nonogram.admin.app`` and once as
    ``src.nonogram.admin.app``, because that is what the test asks for — and the
    point is that *nothing underneath it* doubles: both copies reach the same
    ``nonogram.admin.book_plan``, so there is one ``LongestSideBucket`` class
    and its members compare equal across the two.
    """

    def test_exactly_one_book_plan_module_is_loaded(self, loaded: dict) -> None:
        assert loaded["book_plan"] == ["nonogram.admin.book_plan"]

    def test_exactly_one_book_manager_module_is_loaded(self, loaded: dict) -> None:
        """The other half of the 2026-09-23 divide: the plan's builder."""
        assert loaded["book_manager"] == ["nonogram.admin.book_manager"]

    def test_both_import_names_share_one_bucket_enum(self, loaded: dict) -> None:
        """``PLAN_BUCKETS`` is one object, so ``Plan.cell`` can index it.

        This is the assertion whose failure was the live 500: with two enum
        classes, ``BUCKETS.index(bucket)`` cannot find a bucket built by the
        other copy.
        """
        assert loaded["one_bucket_tuple"] is True
        assert loaded["one_enum_class"] is True


# --------------------------------------------------------------------------
# AC-3 — Print setup renders a stored plan under either import name
# --------------------------------------------------------------------------

_RENDER_SCRIPT = (
    """
import importlib, json, sys
"""
    + _PIN_CHECKOUT
    + """
name = sys.argv[1]
admin_app = importlib.import_module(name)

app = admin_app.create_app()
app.config["TESTING"] = True  # so a ValueError propagates instead of becoming a 500
client = app.test_client()

# A book created through the panel's own route, so the stored plan is the one
# ``book_manager`` builds — which is the whole point: app.py and book_manager
# must agree about which ``book_plan`` module the buckets come from.
created = client.post("/book/create", data={
    "title": "CARD-139 stored plan",
    "description": "Twenty winter pictures for the import-consistency regression.",
    "theme": "generic",
    "target_audience": "adults",
})
assert created.status_code in (301, 302), (created.status_code, created.get_data(as_text=True)[:2000])
book_id = created.headers["Location"].rstrip("/").rsplit("/", 2)[-2]

# The plan must be STORED. A plan-less book renders DEFAULT_PLAN out of app's
# own copy of book_plan, which is self-consistent even with a doubled tree, so
# it never hit the bug and would make this a vacuous test.
plan = admin_app.get_book_manager().get_plan(book_id)
assert plan is not None, "the regression needs a book whose plan is stored, and this one has none"

# The crash was in Plan.cell, reached while rendering this page.
page = client.get("/book/{}/setup-print".format(book_id))
assert page.status_code == 200, (page.status_code, page.get_data(as_text=True)[:2000])
html = page.get_data(as_text=True)

expected_cells = [
    "cell_{}_{}".format(b, tier.value)
    for b in range(len(admin_app.PLAN_BUCKETS))
    for tier in admin_app.PLAN_TIERS
]
print(json.dumps({
    "module_file": admin_app.__file__,
    "plan_count": plan.count,
    "cells_on_page": [name for name in expected_cells if 'id="{}"'.format(name) in html],
    "expected_cells": expected_cells,
}))
"""
)

#: Both names the app can be launched under — the second is the one that
#: produced the live 500 and the one ``scripts/start_admin_local.sh`` used.
_IMPORT_NAMES = ("nonogram.admin.app", "src.nonogram.admin.app")


@pytest.fixture(scope="module", params=_IMPORT_NAMES)
def rendered(request: pytest.FixtureRequest) -> dict:
    """Print setup, rendered in a fresh interpreter under one import name."""
    return json.loads(_run_in_subprocess(_RENDER_SCRIPT % (str(_REPO_ROOT),), request.param))


@_needs_source
class TestAdminImports_StoredPlanRendersUnderEitherImportName:
    """AC-3 — Print setup renders a book whose plan is stored, either way.

    Regression for the 2026-09-23 ``ValueError: tuple.index(x): x not in
    tuple`` out of ``book_plan.Plan.cell``. ``TESTING`` is on in the
    subprocess, so Flask re-raises rather than turning the crash into a 500 —
    a returncode, and the traceback with it, rather than a status code to
    interpret.
    """

    def test_print_setup_renders_the_stored_plan(self, rendered: dict) -> None:
        # Every cell of the 4 x 3 matrix is on the page, so a page that
        # rendered without the plan half cannot pass this.
        assert rendered["cells_on_page"] == rendered["expected_cells"]
        assert len(rendered["expected_cells"]) == 12
        assert rendered["plan_count"] > 0

    def test_the_subprocess_loaded_this_checkout(self, rendered: dict) -> None:
        """Guard the guard: the app under test is the one in this worktree."""
        assert rendered["module_file"].startswith(str(_REPO_ROOT))
