"""Controls for the cycle-gate test selector (``scripts/impact_set.py``).

Why this file exists at all
---------------------------
The selector makes a claim every time it runs -- *"these are the tests the
changed paths can affect"* -- and a card's gate evidence is then read against
it. Under ADR-0039/R1 a claim needs a control that can fail, and a selector is
the worst place to skip that: its output *looks* like evidence, so a selector
that silently narrows too far turns a green gate into a false one.

The claims under test, each with the state that breaks it:

1. The always-on set is **derived**, not written down. Control:
   :func:`test_a_planted_scanning_test_joins_the_always_on_set` plants a new
   file carrying a scan idiom and requires it to appear; removed, it must not.
   A hard-coded list of paths passes nothing here.
2. Unanalysable changes fail **closed**. Controls: one per entry of
   ``UNANALYSABLE``, plus an unknown root.
3. A changed module with no visible importer fails closed -- an unimported
   module is not an unaffecting one.
4. Reach is by prefix, because ``from nonogram import db`` then ``db.session``
   never names the module.
5. A dotted name that appears only in a string is still reach, because
   ``importlib.import_module`` and ``monkeypatch.setattr`` take one.

What these controls do NOT establish: that the selection is *minimal*, or that
it is complete over couplings the selector cannot see. The selector declares
that bound itself, and the full merge-gate suite is what covers it.
"""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SELECTOR = REPO / "scripts" / "impact_set.py"


def _load():
    """Import the selector from ``scripts/``, which is not on ``sys.path``."""
    spec = importlib.util.spec_from_file_location("impact_set", SELECTOR)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


impact = _load()


# --------------------------------------------------------------------------
# A minimal fake repo, so every control below is hermetic.
# --------------------------------------------------------------------------


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    """A fake repo with one scanning test, one importing test, one orphan.

    Deliberately NOT a copy of this repo: a fixture that mirrored the real tree
    would make every control below depend on the real suite's shape, so a real
    file moving would red a control about the selector's logic.
    """
    (tmp_path / "src" / "nonogram" / "db").mkdir(parents=True)
    (tmp_path / "src" / "nonogram" / "db" / "session.py").write_text("X = 1\n")
    (tmp_path / "src" / "nonogram" / "lonely.py").write_text("Y = 2\n")
    (tmp_path / "tests").mkdir()

    # Scans the tree rather than importing it -- the always-on shape.
    (tmp_path / "tests" / "test_scanner.py").write_text(
        'import subprocess\n'
        'def test_scan():\n'
        '    subprocess.run(["git", "ls-files"])\n'
    )
    # Imports the module by name.
    (tmp_path / "tests" / "test_imports_session.py").write_text(
        "from nonogram.db import session\ndef test_x():\n    assert session\n"
    )
    # Imports nothing of ours.
    (tmp_path / "tests" / "test_orphan.py").write_text("def test_y():\n    assert True\n")
    return tmp_path


# --------------------------------------------------------------------------
# Claim 1 -- the always-on set is derived.
# --------------------------------------------------------------------------


def test_the_always_on_set_is_the_scanning_tests(tree: Path):
    assert impact.always_on(tree) == [Path("tests/test_scanner.py")]


def test_a_planted_scanning_test_joins_the_always_on_set(tree: Path):
    """The control for "derived, not listed".

    A written-down list cannot pass this: the planted file is not in any list
    this repo could have shipped.
    """
    planted = tree / "tests" / "test_planted_scanner.py"
    planted.write_text(
        "from pathlib import Path\n"
        "def test_p():\n"
        "    list(Path('.').rglob('*.py'))\n"
    )
    assert Path("tests/test_planted_scanner.py") in impact.always_on(tree)

    planted.unlink()
    assert Path("tests/test_planted_scanner.py") not in impact.always_on(tree)


def test_a_planted_scanning_test_is_selected_for_an_unrelated_change(tree: Path):
    """Being derived is only useful if the selection then carries it."""
    (tree / "tests" / "test_planted_scanner.py").write_text(
        'import subprocess\n'
        'def test_p():\n'
        '    subprocess.run(["git", "grep", "x"])\n'
    )
    selected = impact.select(tree, ["src/nonogram/db/session.py"])
    assert selected != impact.FULL
    assert "tests/test_planted_scanner.py" in selected


def test_no_scanning_test_found_is_a_failure_not_an_empty_set(tmp_path: Path):
    """The derivation finding nothing is broken, never a licence to narrow."""
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_quiet.py").write_text("def test_q():\n    assert True\n")
    (tmp_path / "src" / "nonogram").mkdir(parents=True)
    (tmp_path / "src" / "nonogram" / "thing.py").write_text("Z = 3\n")
    assert impact.select(tmp_path, ["src/nonogram/thing.py"]) == impact.FULL


# --------------------------------------------------------------------------
# Claim 2 -- unanalysable changes fail closed.
# --------------------------------------------------------------------------


@pytest.mark.parametrize("path", impact.UNANALYSABLE)
def test_every_unanalysable_path_falls_back_to_full(tree: Path, path: str):
    """One control per entry, so adding an entry without a control reds here.

    Parametrised over the tuple itself rather than over a copy of it: a list
    written out here would drift from the tuple silently, which is the defect
    this suite keeps finding.
    """
    assert impact.select(tree, [path]) == impact.FULL


def test_a_path_outside_the_known_roots_falls_back_to_full(tree: Path):
    """"I do not know what this is" and "this affects nothing" differ."""
    assert impact.select(tree, ["some/new/place/thing.py"]) == impact.FULL


def test_one_unanalysable_path_poisons_an_otherwise_narrow_set(tree: Path):
    assert (
        impact.select(tree, ["tests/test_orphan.py", "pyproject.toml"]) == impact.FULL
    )


# --------------------------------------------------------------------------
# Claim 3 -- a module with no visible importer fails closed.
# --------------------------------------------------------------------------


def test_a_module_no_test_imports_falls_back_to_full(tree: Path):
    assert impact.select(tree, ["src/nonogram/lonely.py"]) == impact.FULL


# --------------------------------------------------------------------------
# Claims 4 and 5 -- how reach is computed.
# --------------------------------------------------------------------------


def test_an_importing_test_is_selected(tree: Path):
    selected = impact.select(tree, ["src/nonogram/db/session.py"])
    assert selected != impact.FULL
    assert "tests/test_imports_session.py" in selected
    assert "tests/test_orphan.py" not in selected


def test_a_bound_subpackage_is_reach_because_attribute_access_is_invisible(tree: Path):
    """``from nonogram import db`` binds ``db``, so ``db.session`` is reach."""
    (tree / "tests" / "test_bound_pkg.py").write_text(
        "from nonogram import db\ndef test_z():\n    assert db.session\n"
    )
    selected = impact.select(tree, ["src/nonogram/db/session.py"])
    assert selected != impact.FULL
    assert "tests/test_bound_pkg.py" in selected


def test_a_bound_sibling_member_is_NOT_reach(tree: Path):
    """The control for the over-selection this script was measured making.

    ``from nonogram import errors`` binds ``errors``, not the package, so there
    is no attribute path to ``nonogram.db.session``. Treating the bare package
    as bound here selected 65 extra test files for one change -- so this test
    is the one that fails if that generosity ever comes back.
    """
    (tree / "src" / "nonogram" / "errors.py").write_text("class E(Exception): pass\n")
    (tree / "tests" / "test_sibling_member.py").write_text(
        "from nonogram import errors\ndef test_s():\n    assert errors.E\n"
    )
    selected = impact.select(tree, ["src/nonogram/db/session.py"])
    assert selected != impact.FULL
    assert "tests/test_sibling_member.py" not in selected


def test_a_test_naming_only_a_facade_is_selected_through_the_src_graph(tree: Path):
    """The fail-OPEN hole the first draft had: transitive src->src imports.

    ``test_facade`` names only ``nonogram.facade``; the module under change is
    ``nonogram.db.session``, which the facade imports. Selecting on the test's
    own imports alone would miss it.
    """
    (tree / "src" / "nonogram" / "facade.py").write_text(
        "from nonogram.db import session\n\ndef go():\n    return session.X\n"
    )
    (tree / "tests" / "test_facade.py").write_text(
        "from nonogram import facade\ndef test_f():\n    assert facade.go\n"
    )
    selected = impact.select(tree, ["src/nonogram/db/session.py"])
    assert selected != impact.FULL
    assert "tests/test_facade.py" in selected


def test_the_src_graph_is_transitive_not_one_hop(tree: Path):
    (tree / "src" / "nonogram" / "mid.py").write_text("from nonogram.db import session\n")
    (tree / "src" / "nonogram" / "outer.py").write_text("from nonogram import mid\n")
    (tree / "tests" / "test_outer.py").write_text(
        "from nonogram import outer\ndef test_o():\n    assert outer\n"
    )
    graph = impact.src_import_graph(tree)
    assert "nonogram.outer" in impact.modules_reaching(graph, "nonogram.db.session")
    selected = impact.select(tree, ["src/nonogram/db/session.py"])
    assert selected != impact.FULL
    assert "tests/test_outer.py" in selected


def test_imported_names_splits_named_from_bound(tree: Path):
    """The split is the script's correctness, so it is asserted directly."""
    f = tree / "tests" / "test_forms.py"
    f.write_text(
        "import nonogram.db.session\n"
        "import nonogram.export.layout as lay\n"
        "from nonogram import db\n"
    )
    named, bound = impact.imported_names(tree, Path("tests/test_forms.py"))
    assert "nonogram.db.session" in named
    assert "nonogram" in bound            # `import A.B` binds A
    assert "nonogram.export.layout" in bound  # `import A.B as x` binds A.B
    assert "nonogram.db" in bound         # `from A import B` binds A.B


def test_a_dotted_name_only_in_a_string_is_still_reach(tree: Path):
    """``importlib.import_module`` and ``monkeypatch.setattr`` take strings."""
    (tree / "tests" / "test_dynamic.py").write_text(
        "import importlib\n"
        "def test_d():\n"
        "    importlib.import_module('nonogram.db.session')\n"
    )
    selected = impact.select(tree, ["src/nonogram/db/session.py"])
    assert selected != impact.FULL
    assert "tests/test_dynamic.py" in selected


def test_reach_does_not_match_a_longer_sibling_name():
    """``nonogram.db.session_pool`` is not ``nonogram.db.session``."""
    target = {"nonogram.db.session"}
    assert impact.reaches(({"nonogram.db.session_pool"}, set()), target) is False
    assert impact.reaches(({"nonogram.db.session"}, set()), target) is True
    # A bound package matches only on a dotted boundary, not a text prefix.
    assert impact.reaches((set(), {"nonogram.db"}), target) is True
    assert impact.reaches((set(), {"nonogram.d"}), target) is False


# --------------------------------------------------------------------------
# The remaining selection rules.
# --------------------------------------------------------------------------


def test_a_changed_test_file_runs_itself(tree: Path):
    selected = impact.select(tree, ["tests/test_orphan.py"])
    assert selected != impact.FULL
    assert "tests/test_orphan.py" in selected


def test_an_empty_changed_set_selects_nothing(tree: Path):
    """Not FULL and not everything: a no-op gate is a fact about the diff."""
    assert impact.select(tree, []) == []
    assert impact.select(tree, [""]) == []


def test_prose_contributes_only_the_always_on_scanners(tree: Path):
    """The shape that red twice: prose outside CARD-255's exempt prefixes.

    A ``meta/`` or ``docs/`` change touches no import edge, so the scanners --
    which read the tracked tree -- are the whole selection. Both real reds
    (``backlog.md``, ``dispatcher.state``) took exactly this path.
    """
    selected = impact.select(tree, ["meta/kanban/backlog.md"])
    assert selected == ["tests/test_scanner.py"]


def test_a_test_helper_selects_the_tests_that_import_it(tree: Path):
    (tree / "tests" / "helper_thing.py").write_text("Q = 1\n")
    (tree / "tests" / "test_uses_helper.py").write_text(
        "from tests.helper_thing import Q\ndef test_h():\n    assert Q\n"
    )
    selected = impact.select(tree, ["tests/helper_thing.py"])
    assert selected != impact.FULL
    assert "tests/test_uses_helper.py" in selected


def test_a_test_helper_nothing_imports_falls_back_to_full(tree: Path):
    (tree / "tests" / "helper_unused.py").write_text("R = 1\n")
    assert impact.select(tree, ["tests/helper_unused.py"]) == impact.FULL


# --------------------------------------------------------------------------
# Against the real repository: behaviour, not counted figures.
# --------------------------------------------------------------------------


def test_the_real_suite_has_scanning_tests_and_the_lock_guard_is_one():
    """A floor and a named member, deliberately not a count.

    An exact figure here would be a pin that rots with every card -- the thing
    this board has paid for repeatedly. What is asserted is the property the
    selection depends on: the derivation finds scanners, and it finds the
    tracked-tree guard whose reds are the reason the always-on set exists.
    """
    scanners = impact.always_on(REPO)
    assert scanners, "the derivation found no tree-scanning test in this suite"
    assert Path("tests/test_full_suite_lock.py") in scanners


def test_this_selector_cannot_narrow_the_run_that_would_catch_its_own_breakage():
    assert "scripts/impact_set.py" in impact.UNANALYSABLE
    assert "Makefile" in impact.UNANALYSABLE
    assert impact.select(REPO, ["scripts/impact_set.py"]) == impact.FULL


def test_a_new_untracked_test_file_is_in_the_changed_set(tmp_path: Path):
    """The control for the fail-open hole: ``git diff`` omits untracked files.

    A card that writes a new test and has not committed it must not get a
    selection that omits it. Built on a real throwaway git repo, because the
    claim is about what ``git`` reports, and asserting it against a stub would
    only confirm the stub.
    """
    run = lambda *a: subprocess.run(
        ["git", "-C", str(tmp_path), *a], capture_output=True, text=True, check=True
    )
    run("init", "-q")
    run("config", "user.email", "t@example.invalid")
    run("config", "user.name", "t")
    (tmp_path / "tests").mkdir()
    (tmp_path / "seed.txt").write_text("seed\n")
    run("add", "seed.txt")
    run("commit", "-qm", "seed")
    base = run("rev-parse", "HEAD").stdout.strip()

    (tmp_path / "tests" / "test_brand_new.py").write_text("def test_n():\n    assert 1\n")
    (tmp_path / "untracked_at_top_level.pdf").write_bytes(b"%PDF-1.4\n")

    changed = impact.changed_from_git(tmp_path, base)
    assert "tests/test_brand_new.py" in changed
    # The owner's top-level untracked files stay out, or every set would be FULL.
    assert "untracked_at_top_level.pdf" not in changed


def test_the_selector_runs_as_a_script_and_prints_paths():
    """The Makefile calls it as a subprocess, so that path is a control too."""
    out = subprocess.run(
        [str(REPO / ".venv" / "bin" / "python"), str(SELECTOR), "meta/kanban/board.md"],
        capture_output=True,
        text=True,
        cwd=REPO,
    )
    assert out.returncode == 0, out.stderr
    printed = [line for line in out.stdout.splitlines() if line.strip()]
    assert printed, out.stdout
    assert "tests/test_full_suite_lock.py" in printed
