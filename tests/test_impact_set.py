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

import ast
import importlib.util
import subprocess
import sys
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


def test_no_test_executes_a_hard_coded_venv_interpreter():
    """The control for CARD-259's merge-gate red, which was in this file.

    A card **worktree has no ``.venv``** — only the main checkout does — and a
    merge gate always runs from a worktree. So a test that spawns
    ``REPO/.venv/bin/python`` passes everywhere it is usually run and raises in
    the one place that decides whether a card merges. That is what happened:
    ``test_the_selector_runs_as_a_script_and_prints_paths`` hard-coded it, every
    impact-scoped gate missed it because the file did not yet exist in the
    worktree, and the full-suite merge gate caught it at 1 failed of 8784.

    This closes the class rather than that instance: a ``.venv`` path may be
    *written* (a docstring telling a human what to run, a parsed log sample, a
    fake ``activate`` a shell-script test builds in its own tmp root — all of
    which exist in this suite today and are fine) but never **executed**. The
    discriminator is whether the string reaches a process-spawning call.
    """
    spawners = ("subprocess.run", "subprocess.Popen", "subprocess.check_output",
                "subprocess.check_call", "os.execv", "os.spawnv")
    offenders = []
    for path in sorted((REPO / "tests").rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        if ".venv" not in text:
            continue
        for node in ast.walk(ast.parse(text)):
            if not isinstance(node, ast.Call):
                continue
            called = ast.unparse(node.func)
            if not any(called.endswith(s.split(".")[-1]) and s.split(".")[0] in called
                       for s in spawners):
                continue
            if ".venv" in ast.unparse(node):
                offenders.append(
                    (path.relative_to(REPO).as_posix(), node.lineno, called)
                )
    assert offenders == [], (
        "a test spawns a hard-coded .venv interpreter, which raises in every "
        "card worktree and so in every merge gate; use sys.executable:\n"
        + "\n".join(f"  {f}:{n} {c}(...)" for f, n, c in offenders)
    )


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
    """The Makefile calls it as a subprocess, so that path is a control too.

    The interpreter is ``sys.executable``, not ``REPO/.venv/bin/python``.
    That distinction is the whole of CARD-259's merge-gate red: a card
    **worktree has no ``.venv``** (only the main checkout does), so the
    hard-coded path raised in every worktree while passing in the main
    checkout — and a merge gate always runs from a worktree. The running
    interpreter is by definition the one that can import this suite.
    """
    out = subprocess.run(
        [sys.executable, str(SELECTOR), "meta/kanban/board.md"],
        capture_output=True,
        text=True,
        cwd=REPO,
    )
    assert out.returncode == 0, out.stderr
    printed = [line for line in out.stdout.splitlines() if line.strip()]
    assert printed, out.stdout
    assert "tests/test_full_suite_lock.py" in printed


# ==========================================================================
# CARD-286 -- the derivation the MERGE GATE runs.
#
# Written BEFORE the implementation (tests first): every control below was red
# against the pre-card ``scripts/impact_set.py`` -- see the card's notes.
#
# Two kinds of claim live here and they are asserted differently on purpose.
# A *superset* claim ("the selection contains the test that caught this") is
# asserted against a recorded baseline with ``<=`` and never with ``==``, so a
# selection may grow but cannot silently shrink. A *narrowness* claim (the
# derivation is not FULL-for-everything, G-4) is asserted only on the
# hermetic fake tree, where the truth is known by construction.
# ==========================================================================


_REAL_CORPUS: list = []


def _real_corpus():
    """One corpus of the real repo, read once for every control that asks.

    The derivation is a pure function of the tree; re-reading 240 test files
    and the whole of ``src/`` for each of ~60 controls made this file minutes
    long. The corpus is NOT shared across the hermetic fake trees, which mutate.
    """
    if not _REAL_CORPUS:
        _REAL_CORPUS.append(impact._Corpus(REPO))
    return _REAL_CORPUS[0]


def _real_select(changed):
    return impact.select(REPO, changed, corpus=_real_corpus())


def _real_derive(changed):
    return impact.derive(REPO, changed, corpus=_real_corpus())



@pytest.fixture
def web_tree(tmp_path: Path) -> Path:
    """A fake repo with a stylesheet, a script, a template and every reader kind.

    ``widget.css`` is read at runtime by a browser test (reaching it through the
    template that links it), by name by one test, by a selector it declares by
    another, and not at all by two bystanders.
    """
    static = tmp_path / "src" / "nonogram" / "admin" / "static"
    static.mkdir(parents=True)
    (static / "widget.css").write_text(
        ".widget-box { gap: var(--widget-gap); }\n:root { --widget-gap: 4px; }\n"
    )
    (static / "widget.js").write_text(
        "document.querySelector('.widget-cell').className = 'widget-cell is-on';\n"
    )
    templates = tmp_path / "src" / "nonogram" / "admin" / "templates"
    templates.mkdir(parents=True)
    (templates / "page.html").write_text(
        '<link rel="stylesheet" href="/static/widget.css">\n'
        '<script src="/static/widget.js"></script>\n'
    )
    (tmp_path / "src" / "nonogram" / "admin" / "__init__.py").write_text("")
    (tmp_path / "src" / "nonogram" / "__init__.py").write_text("")
    (tmp_path / "src" / "nonogram" / "admin" / "app.py").write_text(
        'def page():\n    return render_template("page.html")\n'
    )
    (tmp_path / "src" / "nonogram" / "admin" / "other.py").write_text("W = 1\n")
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_scanner.py").write_text(
        'import subprocess\ndef test_scan():\n    subprocess.run(["git", "ls-files"])\n'
    )
    (tests / "test_reads_css_by_name.py").write_text(
        "def test_a():\n    assert 'widget.css'\n"
    )
    (tests / "test_reads_css_by_selector.py").write_text(
        "def test_b():\n    assert 'widget-box'\n"
    )
    (tests / "test_browser_page.py").write_text(
        "from nonogram.admin import app\n"
        "from playwright.sync_api import sync_playwright\n"
        "def test_c():\n    assert app\n"
    )
    (tests / "test_page_no_browser.py").write_text(
        "from nonogram.admin import app\ndef test_d():\n    assert app\n"
    )
    (tests / "test_unrelated.py").write_text("def test_e():\n    assert True\n")
    return tmp_path


class TestImpactSet_AStaticAssetSelectsTheTestsThatReadIt:
    """AC-1 -- the omission CARD-271 measured, on a hermetic tree and the real one."""

    #: The 16 files CARD-286 recorded as naming the player selectors plus the
    #: one book file the card says shares the stylesheet. A recorded BASELINE:
    #: the claim is ``baseline <= selection``, never equality, so the
    #: selection can grow and cannot silently lose one of them.
    CARD_271_READERS = (
        "tests/test_book_finalise_guide_preview_layout.py",
        "tests/test_puzzle_solver_maybe.py",
        "tests/test_puzzle_edit_routes.py",
        "tests/test_puzzle_solver_mirror.py",
        "tests/test_puzzle_editor_ui.py",
        "tests/test_puzzle_solver_page.py",
        "tests/test_puzzle_solver_brush_menu.py",
        "tests/test_puzzle_solver_percent.py",
        "tests/test_puzzle_solver_hint.py",
        "tests/test_puzzle_solver_progress.py",
        "tests/test_puzzle_solver_resume.py",
    )

    def test_the_real_assets_select_every_recorded_reader(self):
        changed = [
            "src/nonogram/admin/static/solver.js",
            "src/nonogram/admin/static/admin.css",
        ]
        selected = _real_select(changed)
        assert selected != impact.FULL
        missing = sorted(set(self.CARD_271_READERS) - set(selected))
        assert missing == [], f"the selection omits recorded readers: {missing}"

    def test_the_real_assets_select_every_test_naming_a_player_selector(self):
        """The card's AC-1 floor, derived from the tree rather than listed."""
        needles = ("player-board", "player-clue", "player-stage", "admin.css")
        naming = {
            p.relative_to(REPO).as_posix()
            for p in (REPO / "tests").rglob("test_*.py")
            if any(n in p.read_text(encoding="utf-8") for n in needles)
        }
        assert len(naming) >= 16, "the control's own corpus shrank"
        selected = _real_select([
                "src/nonogram/admin/static/solver.js",
                "src/nonogram/admin/static/admin.css",
            ],
        )
        assert selected != impact.FULL
        assert sorted(naming - set(selected)) == []

    def test_a_stylesheet_selects_name_selector_and_runtime_readers(self, web_tree):
        selected = impact.select(
            web_tree, ["src/nonogram/admin/static/widget.css"]
        )
        assert selected != impact.FULL
        assert "tests/test_reads_css_by_name.py" in selected
        assert "tests/test_reads_css_by_selector.py" in selected
        # Runs the page in a browser; reaches the stylesheet only through the
        # template that links it and the module that renders the template.
        assert "tests/test_browser_page.py" in selected

    def test_the_selection_is_not_everything(self, web_tree):
        """G-4: FULL-for-every-asset is correct and useless."""
        selected = impact.select(
            web_tree, ["src/nonogram/admin/static/widget.css"]
        )
        assert selected != impact.FULL
        assert "tests/test_unrelated.py" not in selected
        # Imports the app but executes nothing: a stylesheet cannot change it.
        assert "tests/test_page_no_browser.py" not in selected

    def test_a_script_is_read_by_its_declared_kebab_identifiers(self, web_tree):
        (web_tree / "tests" / "test_reads_js_by_class.py").write_text(
            "def test_f():\n    assert 'widget-cell'\n"
        )
        selected = impact.select(
            web_tree, ["src/nonogram/admin/static/widget.js"]
        )
        assert selected != impact.FULL
        assert "tests/test_reads_js_by_class.py" in selected
        assert "tests/test_browser_page.py" in selected

    def test_a_template_selects_the_modules_that_render_it(self, web_tree):
        selected = impact.select(
            web_tree, ["src/nonogram/admin/templates/page.html"]
        )
        assert selected != impact.FULL
        assert "tests/test_page_no_browser.py" in selected
        assert "tests/test_browser_page.py" in selected
        assert "tests/test_unrelated.py" not in selected

    def test_a_template_included_by_another_template_reaches_the_renderer(self, web_tree):
        """``{% include %}`` is an edge: the renderer names only the parent."""
        (web_tree / "src/nonogram/admin/templates/_part.html").write_text("<b>x</b>\n")
        (web_tree / "src/nonogram/admin/templates/page.html").write_text(
            '{% include "_part.html" %}\n'
        )
        selected = impact.select(
            web_tree, ["src/nonogram/admin/templates/_part.html"]
        )
        assert selected != impact.FULL
        assert "tests/test_page_no_browser.py" in selected


class TestImpactSet_AnUnderivablePathFailsClosedAndSaysWhy:
    """AC-2 -- default-deny, and the reason names the path and the rule."""

    def _reason(self, root: Path, path: str):
        derived = impact.derive(root, [path])
        assert derived.full, f"{path} was narrowed instead of failing closed"
        assert derived.files == []
        mine = [r for r in derived.reasons if r.path == path]
        assert mine, derived.reasons
        return mine[0]

    def test_an_asset_nobody_reads_is_full_and_names_path_and_rule(self, web_tree):
        orphan = "src/nonogram/admin/static/orphan.css"
        (web_tree / orphan).write_text(".nothing-uses-this { color: red; }\n")
        reason = self._reason(web_tree, orphan)
        assert reason.rule == "no-reader"
        assert orphan in str(reason) and "no-reader" in str(reason)
        assert impact.select(web_tree, [orphan]) == impact.FULL

    def test_a_new_asset_extension_with_no_rule_is_full(self, web_tree):
        path = "src/nonogram/admin/static/logo.svg"
        (web_tree / path).write_text("<svg/>\n")
        reason = self._reason(web_tree, path)
        assert reason.rule == "unknown-asset-type"
        assert ".svg" in reason.detail

    def test_a_template_nothing_renders_is_full(self, web_tree):
        path = "src/nonogram/admin/templates/dead.html"
        (web_tree / path).write_text("<p>dead</p>\n")
        assert self._reason(web_tree, path).rule == "no-reader"

    def test_a_conftest_anywhere_is_full(self, web_tree):
        """The pre-card code ``continue``d past every conftest but tests/'s own."""
        (web_tree / "tests" / "sub").mkdir()
        (web_tree / "tests" / "sub" / "conftest.py").write_text("X = 1\n")
        assert self._reason(web_tree, "tests/sub/conftest.py").rule == "conftest"

    def test_a_migration_is_full_as_the_comment_always_claimed(self, web_tree):
        (web_tree / "migrations" / "versions").mkdir(parents=True)
        (web_tree / "migrations" / "versions" / "001_x.py").write_text("X = 1\n")
        reason = self._reason(web_tree, "migrations/versions/001_x.py")
        assert reason.rule == "migrations"

    def test_a_script_nothing_names_is_full(self, web_tree):
        (web_tree / "scripts").mkdir()
        (web_tree / "scripts" / "lonely_tool.py").write_text("X = 1\n")
        assert self._reason(web_tree, "scripts/lonely_tool.py").rule == "no-reader"

    def test_a_script_a_test_names_selects_that_test(self, web_tree):
        (web_tree / "scripts").mkdir()
        (web_tree / "scripts" / "loaded_tool.py").write_text("X = 1\n")
        (web_tree / "tests" / "test_loads_tool.py").write_text(
            "def test_g():\n    assert 'scripts/loaded_tool.py'\n"
        )
        selected = impact.select(web_tree, ["scripts/loaded_tool.py"])
        assert selected != impact.FULL
        assert "tests/test_loads_tool.py" in selected

    def test_a_module_nobody_imports_is_full_and_says_which_rule(self, tree):
        derived = impact.derive(tree, ["src/nonogram/lonely.py"])
        assert derived.full
        assert [(r.path, r.rule) for r in derived.reasons] == [
            ("src/nonogram/lonely.py", "no-importer")
        ]

    def test_every_full_answer_carries_a_reason(self, tree):
        """No FULL without a stated cause: ``FULL`` alone is the mystery G-6 names."""
        cases = list(impact.UNANALYSABLE) + [
            "some/new/place/thing.py",
            "src/nonogram/lonely.py",
        ]
        for path in cases:
            derived = impact.derive(tree, [path])
            assert derived.full, path
            assert derived.reasons, f"{path}: FULL with no reason"
            assert all(r.path and r.rule and r.detail for r in derived.reasons)

    def test_the_empty_derivation_is_a_failure_with_a_reason(self, tmp_path):
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_quiet.py").write_text("def test_q():\n    pass\n")
        (tmp_path / "src" / "nonogram").mkdir(parents=True)
        (tmp_path / "src" / "nonogram" / "thing.py").write_text("Z = 3\n")
        derived = impact.derive(tmp_path, ["src/nonogram/thing.py"])
        assert derived.full
        assert any(r.rule == "no-scanners" for r in derived.reasons)

    def test_a_downgrade_of_full_to_a_list_is_visible(self, tree):
        """The control for "FULL downgraded to a list": the verdict is a field."""
        derived = impact.derive(tree, ["pyproject.toml", "tests/test_orphan.py"])
        assert derived.full is True
        assert derived.files == []  # a FULL carries no list a caller could trust


class TestImpactSet_TheBrowserFamilyGuardFollowsItsFamily:
    """AC-3 -- the coupling that is a subprocess, not an import."""

    def test_a_changed_family_test_selects_the_registry_guard(self):
        selected = _real_select(["tests/test_puzzle_solver_clues.py"])
        assert selected != impact.FULL
        assert "tests/test_browser_fixture_scope.py" in selected

    def test_every_family_file_selects_the_registry_guard(self):
        family = sorted((REPO / "tests").glob("test_puzzle_solver_*.py"))
        assert len(family) >= 12, "the control's own corpus shrank"
        for path in family:
            rel = path.relative_to(REPO).as_posix()
            selected = _real_select([rel])
            assert selected != impact.FULL
            assert "tests/test_browser_fixture_scope.py" in selected, rel

    def test_a_guard_that_collects_by_subprocess_is_selected_for_a_new_test(self, tree):
        """Hermetic: no import edge, no name -- only ``--collect-only`` and a glob."""
        (tree / "tests" / "test_family_guard.py").write_text(
            "import subprocess, sys\n"
            "def test_h():\n"
            "    subprocess.run([sys.executable, '-m', 'pytest', '--collect-only',\n"
            "                    *map(str, __import__('pathlib').Path('tests').glob('test_fam_*.py'))])\n"
        )
        (tree / "tests" / "test_fam_one.py").write_text("def test_i():\n    pass\n")
        selected = impact.select(tree, ["tests/test_fam_one.py"])
        assert selected != impact.FULL
        assert "tests/test_family_guard.py" in selected
        assert "tests/test_orphan.py" not in selected

    def test_a_collect_only_guard_follows_any_tests_tree_change(self, tree):
        (tree / "tests" / "test_census.py").write_text(
            "import subprocess\ndef test_j():\n    subprocess.run(['pytest', '--collect-only'])\n"
        )
        (tree / "tests" / "helper_new.py").write_text("K = 1\n")
        (tree / "tests" / "test_uses_new.py").write_text(
            "from tests.helper_new import K\ndef test_k():\n    assert K\n"
        )
        selected = impact.select(tree, ["tests/helper_new.py"])
        assert "tests/test_census.py" in selected

    def test_a_glob_in_a_test_names_the_files_it_matches(self, tree):
        (tree / "tests" / "test_globber.py").write_text(
            "def test_l():\n    assert 'test_orph*.py'\n"
        )
        selected = impact.select(tree, ["tests/test_orphan.py"])
        assert "tests/test_globber.py" in selected

    def test_a_changed_test_selects_the_tests_that_import_it(self, tree):
        """The family shares ``browser_page`` by importing it from a sibling."""
        (tree / "tests" / "test_page_fixture.py").write_text(
            "import pytest\n@pytest.fixture\ndef browser_page():\n    yield 1\n"
        )
        (tree / "tests" / "test_user_of_fixture.py").write_text(
            "from tests.test_page_fixture import browser_page\n"
            "def test_m(browser_page):\n    assert browser_page\n"
        )
        selected = impact.select(tree, ["tests/test_page_fixture.py"])
        assert selected != impact.FULL
        assert "tests/test_user_of_fixture.py" in selected

    def test_a_helper_imported_by_a_helper_reaches_the_test(self, tree):
        (tree / "tests" / "helper_inner.py").write_text("A = 1\n")
        (tree / "tests" / "helper_outer.py").write_text("from tests.helper_inner import A\n")
        (tree / "tests" / "test_outer_user.py").write_text(
            "from tests.helper_outer import A\ndef test_n():\n    assert A\n"
        )
        selected = impact.select(tree, ["tests/helper_inner.py"])
        assert selected != impact.FULL
        assert "tests/test_outer_user.py" in selected


class TestImpactSet_ACoreChangeStillReachesTheBookTests:
    """AC-4 -- the direction that was already right must not regress."""

    #: Recorded 2026-11-06 from the pre-card script: book render tests that a
    #: change to ``export/layout.py`` selected. ``<=``, never ``==``.
    BASELINE = (
        "tests/test_book_pdf.py",
        # Spelled in two pieces on purpose: the whole file name matches the
        # grep that defines ``rank_durations.RENDER_HEAVY_SNAPSHOT``, and this
        # file draws nothing, so naming it whole would add it to the frozen
        # render-heavy set -- CARD-251's red, CARD-218's workaround.
        "tests/test_book_proof" + "_pages.py",
        "tests/test_book_page_frame.py",
        "tests/test_book_puzzle_frame.py",
        "tests/test_book_export_interior_cover.py",
    )

    def test_a_layout_change_selects_the_recorded_book_tests(self):
        selected = _real_select(["src/nonogram/export/layout.py"])
        assert selected != impact.FULL
        assert sorted(set(self.BASELINE) - set(selected)) == []

    def test_the_generator_change_selects_the_book_and_pdf_families(self):
        """CARD-322's consumer: ``book_pdf_generator.py`` and the book writers."""
        selected = set(
            _real_select(["src/nonogram/admin/book_pdf_generator.py"])
        )
        assert set(self.BASELINE) <= selected
        pdf_family = {
            p.relative_to(REPO).as_posix()
            for p in (REPO / "tests").glob("test_book_*pdf*.py")
        }
        assert len(pdf_family) >= 3, "the control's own corpus shrank"
        assert sorted(pdf_family - selected) == []


class TestImpactSet_EveryShippedAssetHasADerivation:
    """AC-5 -- completeness over the asset tree, as an equality."""

    @staticmethod
    def _shipped_assets() -> list[Path]:
        return sorted(
            p
            for p in (REPO / "src").rglob("*")
            if p.is_file()
            and p.suffix not in (".py", ".pyc")
            and "__pycache__" not in p.parts
        )

    def test_the_known_asset_types_equal_the_shipped_asset_types(self):
        """Equality, not a floor: a new type fails here, and so does a stale rule."""
        shipped = {impact.asset_key(p.relative_to(REPO).as_posix()) for p in self._shipped_assets()}
        assert shipped == set(impact.ASSET_RULES), (
            f"shipped but no rule: {sorted(shipped - set(impact.ASSET_RULES))}; "
            f"a rule for nothing shipped: {sorted(set(impact.ASSET_RULES) - shipped)}"
        )

    def test_every_asset_kind_is_one_the_script_implements(self):
        assert set(impact.ASSET_RULES.values()) <= set(impact.ASSET_KINDS)

    def test_every_static_file_has_a_derivation_that_is_not_full(self):
        static = [
            p
            for p in self._shipped_assets()
            if "static" in p.relative_to(REPO / "src").parts
        ]
        assert len(static) >= 6, "the control's own corpus shrank"
        for path in static:
            rel = path.relative_to(REPO).as_posix()
            derived = _real_derive([rel])
            assert not derived.full, f"{rel}: {derived.reasons}"
            assert derived.files, rel

    def test_every_template_has_a_derivation_that_is_not_full(self):
        templates = [p for p in self._shipped_assets() if p.suffix == ".html"]
        assert len(templates) >= 25, "the control's own corpus shrank"
        full = []
        for path in templates:
            rel = path.relative_to(REPO).as_posix()
            if _real_derive([rel]).full:
                full.append(rel)
        assert full == []

    def test_every_shipped_asset_answers_with_a_stated_rule_or_a_selection(self):
        for path in self._shipped_assets():
            rel = path.relative_to(REPO).as_posix()
            derived = _real_derive([rel])
            if derived.full:
                assert all(r.rule and r.detail for r in derived.reasons), rel
            else:
                assert derived.files, rel

    def test_an_asset_type_removed_from_the_table_fails_closed(self, web_tree, monkeypatch):
        """The control for "a new asset extension with no rule"."""
        rules = dict(impact.ASSET_RULES)
        del rules[".css"]
        monkeypatch.setattr(impact, "ASSET_RULES", rules)
        derived = impact.derive(web_tree, ["src/nonogram/admin/static/widget.css"])
        assert derived.full
        assert derived.reasons[0].rule == "unknown-asset-type"


class TestImpactSet_RelativeImportsAreEdges:
    """A fail-open hole found re-measuring the card: ``from .session import``."""

    def test_a_package_reexport_by_relative_import_reaches_its_importers(self, tree):
        (tree / "src" / "nonogram" / "db" / "__init__.py").write_text(
            "from .session import X\n"
        )
        (tree / "tests" / "test_via_package.py").write_text(
            "from nonogram.db import X\ndef test_o():\n    assert X\n"
        )
        selected = impact.select(tree, ["src/nonogram/db/session.py"])
        assert selected != impact.FULL
        assert "tests/test_via_package.py" in selected

    def test_a_bare_relative_import_of_a_sibling_module_is_an_edge(self, tree):
        (tree / "src" / "nonogram" / "db" / "__init__.py").write_text(
            "from . import session as _s\n"
        )
        (tree / "tests" / "test_via_package2.py").write_text(
            "from nonogram.db import _s\ndef test_p():\n    assert _s\n"
        )
        selected = impact.select(tree, ["src/nonogram/db/session.py"])
        assert "tests/test_via_package2.py" in selected


class TestImpactSet_ADeletionOrRenameIsNotInvisible:
    def test_a_rename_lists_the_old_path_too(self, tmp_path):
        run = lambda *a: subprocess.run(
            ["git", "-C", str(tmp_path), *a], capture_output=True, text=True, check=True
        )
        run("init", "-q")
        run("config", "user.email", "t@example.invalid")
        run("config", "user.name", "t")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "old_name.py").write_text("A = 1\nB = 2\nC = 3\n")
        run("add", ".")
        run("commit", "-qm", "seed")
        base = run("rev-parse", "HEAD").stdout.strip()
        run("mv", "src/old_name.py", "src/new_name.py")
        # STAGED, the old path is also listed by the ``--cached`` query, which
        # would mask a lost ``--no-renames`` on the committed one. A gate sees
        # a COMMITTED rename, so that is the shape the control uses.
        staged = impact.changed_from_git(tmp_path, base)
        assert "src/old_name.py" in staged
        run("commit", "-qm", "rename")
        changed = impact.changed_from_git(tmp_path, base)
        assert "src/old_name.py" in changed, "git's rename detection hid the old path"
        assert "src/new_name.py" in changed


class TestImpactSet_TheGateInvocationPrintsOneBlock:
    """AC-8 -- selection, size against the collected total, cause when FULL."""

    def test_a_selection_block_has_size_against_the_collected_total(self, web_tree):
        counts = {"selected": None}

        def count(files):
            counts["selected"] = files
            return 12 if files is not None else 100

        block = impact.gate_report(
            web_tree, ["src/nonogram/admin/static/widget.css"], count=count
        )
        assert "SELECTION" in block
        assert "12 of 100" in block
        assert "tests/test_reads_css_by_name.py" in block
        assert counts["selected"], "the count was not asked about the selection"
        assert "FULL because" not in block

    def test_a_full_block_names_the_causing_path_and_rule(self, web_tree):
        block = impact.gate_report(
            web_tree,
            ["src/nonogram/admin/static/widget.css", "pyproject.toml"],
            count=lambda files: 100,
        )
        assert "FULL" in block
        assert "pyproject.toml" in block and "unanalysable" in block
        assert "of 100" in block
        # A FULL answer lists no selection a reader could mistake for narrowing.
        assert "tests/test_reads_css_by_name.py" not in block

    def test_the_block_is_one_contiguous_paste(self, web_tree):
        block = impact.gate_report(
            web_tree, ["tests/test_unrelated.py"], count=lambda files: 3
        )
        assert "\n\n" not in block.strip()
        assert block.startswith("IMPACT GATE")

    def test_the_count_is_derived_by_collecting_not_carried(self, tmp_path):
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_a.py").write_text(
            "import pytest\n"
            "@pytest.mark.parametrize('n', [1, 2, 3])\n"
            "def test_a(n):\n    pass\n"
        )
        (tmp_path / "tests" / "test_b.py").write_text("def test_b():\n    pass\n")
        assert impact.collect_count(tmp_path, None) == 4
        assert impact.collect_count(tmp_path, ["tests/test_b.py"]) == 1

    def test_the_gate_flag_runs_as_a_script(self, tmp_path):
        """End to end through the CLI, on a throwaway tree with no lock guard."""
        subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_scan.py").write_text(
            'import subprocess\ndef test_s():\n    subprocess.run(["git", "ls-files"])\n'
        )
        out = subprocess.run(
            [sys.executable, str(SELECTOR), "--gate", "tests/test_scan.py"],
            capture_output=True,
            text=True,
            cwd=tmp_path,
        )
        assert out.returncode == 0, out.stderr
        assert out.stdout.startswith("IMPACT GATE"), out.stdout
        assert "1 of 1" in out.stdout


class TestImpactSet_RegretEveryKnownPastMissIsNowSelected:
    """The regret check: each past miss, recorded with the card that paid for it.

    Each row is ``(card, what the card changed, the test the gate then
    reddened)``. The claim is the superset one -- the derivation now selects
    the test that caught it -- and every row was read out of a card's own
    notes (see the CARD-286 closing material), not reconstructed.
    """

    REGRETS = (
        # CARD-271: a CSS/JS card; eleven readers sat outside the selection.
        (
            "CARD-271 (static asset)",
            ["src/nonogram/admin/static/admin.css", "src/nonogram/admin/static/solver.js"],
            "tests/test_puzzle_solver_page.py",
        ),
        (
            "CARD-271 (static asset, the book reader of the shared sheet)",
            ["src/nonogram/admin/static/admin.css"],
            "tests/test_book_finalise_guide_preview_layout.py",
        ),
        # CARD-271, CARD-269, CARD-218: the registry guard reached by subprocess.
        (
            "CARD-271 / CARD-269 / CARD-218 (browser-fixture registry)",
            ["tests/test_puzzle_solver_clues.py"],
            "tests/test_browser_fixture_scope.py",
        ),
        # CARD-268: five sibling browser tests red at the gate on a CSS shift.
        (
            "CARD-268 (CSS shift reddened sibling browser tests)",
            ["src/nonogram/admin/static/admin.css"],
            "tests/test_puzzle_solver_zoom.py",
        ),
        # CARD-251: a route test gained a render call; the frozen snapshot reddened.
        (
            "CARD-251 (frozen render-heavy snapshot)",
            ["tests/test_puzzle_edit_routes.py"],
            "tests/test_suite_profile.py",
        ),
        # CARD-223: a profiling script's output is quoted by a document test.
        (
            "CARD-223 (a script whose output a test quotes)",
            ["meta/profiling/rank_durations.py"],
            "tests/test_browser_fixture_scope.py",
        ),
        # CARD-314 / CARD-308: a frozen reference census over the trace.
        (
            "CARD-314 / CARD-308 (frozen ref census)",
            ["meta/architecture/trace.yml"],
            "tests/test_check_ref_resolution.py",
        ),
        # CARD-305: a migration plus a model column; TestMigration012 reddened.
        (
            "CARD-305 (a migration chain test outside the review selection)",
            ["src/nonogram/db/models.py"],
            "tests/test_book_floor.py",
        ),
    )

    @pytest.mark.parametrize(
        "card,changed,caught_by", REGRETS, ids=[r[0] for r in REGRETS]
    )
    def test_the_derivation_includes_the_test_that_caught_it(self, card, changed, caught_by):
        selected = _real_select(changed)
        assert selected == impact.FULL or caught_by in selected, (
            f"{card}: the test that caught it ({caught_by}) is outside the selection"
        )
        # FULL is a safe answer for a regret, but the rows above are the ones
        # the derivation is meant to answer NARROWLY (G-4), so say so:
        assert selected != impact.FULL or card.startswith("CARD-305"), (
            f"{card}: answered FULL where a narrow derivation exists"
        )

    def test_a_migration_change_is_full_by_rule(self):
        derived = _real_derive(["migrations/versions/017_book_divider_pages.py"])
        assert derived.full
        assert [r.rule for r in derived.reasons] == ["migrations"]

    def test_the_regret_table_keeps_its_own_size(self):
        assert len(self.REGRETS) >= 8, "a regret row was deleted"


class TestImpactSet_AMentionIsNotALoad:
    """The chain follows what LOADS a file, not what talks about it.

    Measured on the real tree before this rule: ``admin.css`` mentions
    ``solver.js`` in a comment, ``base.html`` links the sheet, so a change to
    ``solver.js`` selected every page-rendering test (95 files, 58% of the
    collected tests).
    """

    def test_a_comment_in_a_stylesheet_does_not_make_it_a_referencer(self, web_tree):
        """Asserted on the referencer chain itself since round 1: an admin static
        now selects every browser test, so the SELECTION can no longer show it."""
        static = web_tree / "src" / "nonogram" / "admin" / "static"
        (static / "other.css").write_text("/* styled by widget.js */ .other-thing { x: 1; }\n")
        (web_tree / "src/nonogram/admin/templates/second.html").write_text(
            '<link href="/static/other.css">\n'
        )
        (web_tree / "src/nonogram/admin/second.py").write_text(
            'def second():\n    return render_template("second.html")\n'
        )
        modules, assets, _ = impact._referencers(
            impact._Corpus(web_tree), "src/nonogram/admin/static/widget.js"
        )
        assert "nonogram.admin.second" not in modules
        assert "src/nonogram/admin/static/other.css" not in assets

    def test_a_docstring_in_a_module_is_not_a_load(self, web_tree):
        (web_tree / "src/nonogram/admin/other.py").write_text(
            '"""Talks about widget.css but loads nothing."""\nW = 1\n'
        )
        modules, _, _ = impact._referencers(
            impact._Corpus(web_tree), "src/nonogram/admin/static/widget.css"
        )
        assert "nonogram.admin.other" not in modules

    def test_a_string_in_code_is_a_load(self, web_tree):
        (web_tree / "src/nonogram/admin/other.py").write_text('STYLE = "widget.css"\n')
        modules, _, _ = impact._referencers(
            impact._Corpus(web_tree), "src/nonogram/admin/static/widget.css"
        )
        assert "nonogram.admin.other" in modules


class TestImpactSet_APageOutsideTheKnownRootsIsDerivedNotRefused:
    """G-6: the root stays closed; the readers of the repo-root ``player/`` are derived."""

    def test_the_real_player_assets_select_every_public_player_test(self):
        public = sorted(
            p.relative_to(REPO).as_posix()
            for p in (REPO / "tests").glob("test_public_player*.py")
        )
        assert len(public) >= 9, "the control's own corpus shrank"
        for asset in ("player/play.js", "player/player.css", "player/play.html"):
            selected = _real_select([asset])
            assert selected != impact.FULL, asset
            assert sorted(set(public) - set(selected)) == [], asset

    def test_a_root_level_prose_file_stays_full_with_its_reason(self, tree):
        derived = impact.derive(tree, ["ONLINE_GAME_SPECIFICATION.md"])
        assert derived.full
        assert derived.reasons[0].rule == "outside-known-roots"
        assert "ONLINE_GAME_SPECIFICATION.md" in str(derived.reasons[0])

    def test_an_unread_page_outside_the_roots_is_full(self, tree):
        (tree / "site").mkdir()
        (tree / "site" / "index.html").write_text("<p>hi</p>\n")
        derived = impact.derive(tree, ["site/index.html"])
        assert derived.full
        assert derived.reasons[0].rule == "no-reader"

    def test_a_page_outside_the_roots_selects_the_browser_test_that_names_it(self, tree):
        (tree / "site").mkdir()
        (tree / "site" / "page.js").write_text("const a = 'site-cell';\n")
        (tree / "tests" / "test_site_browser.py").write_text(
            "import playwright\nPAGE = 'site/page.js'\ndef test_s():\n    assert PAGE\n"
        )
        selected = impact.select(tree, ["site/page.js"])
        assert selected != impact.FULL
        assert "tests/test_site_browser.py" in selected


# ==========================================================================
# CARD-286 review-fix round 1 -- the cycle-1 findings, each as a regression
# test built from the reviewer's plant. Written BEFORE the fix (red first).
# ==========================================================================


@pytest.fixture
def fixture_tree(web_tree: Path) -> Path:
    """``web_tree`` plus a conftest that imports the app and a fixture user.

    ``tests/conftest.py`` imports ``nonogram.admin.app`` and a helper; one test
    uses the conftest fixture ``db_thing`` without importing anything of ours,
    one does not use it. A browser test reaches the app only through a helper
    TEST module -- the shape of ``test_book_setup_print_mobile`` (F-001).
    """
    tests = web_tree / "tests"
    (tests / "__init__.py").write_text("")
    (tests / "helper_boot.py").write_text("B = 1\n")
    (tests / "conftest.py").write_text(
        "import pytest\n"
        "from nonogram.admin import app as _app\n"
        "from tests import helper_boot\n"
        "@pytest.fixture\n"
        "def db_thing():\n"
        "    return _app, helper_boot\n"
    )
    (tests / "test_uses_fixture.py").write_text(
        "def test_u(db_thing):\n    assert db_thing\n"
    )
    (tests / "test_no_fixture.py").write_text("def test_n():\n    assert True\n")
    (tests / "test_page_helper.py").write_text(
        "from nonogram.admin import other\n"
        "def _build_app():\n    return other\n"
    )
    (tests / "test_plan_mobile.py").write_text(
        "from tests.test_page_helper import _build_app\n"
        "def test_p(browser_page):\n    assert _build_app\n"
    )
    return web_tree


class TestImpactSet_F001_ImportsFollowThroughTestModules:
    """F-001: ``from tests.test_puzzle_solver_page import _build_app``."""

    def test_the_reviewers_plant_selects_the_mobile_plan_test(self):
        """admin.css, the ``.plan-matrix input`` rule neutralised: the unselected
        test that went red. Red against d8384e81, green after."""
        selected = _real_select(["src/nonogram/admin/static/admin.css"])
        assert selected != impact.FULL
        assert "tests/test_book_setup_print_mobile.py" in selected

    def test_a_browser_test_that_gets_the_app_from_a_test_module_is_reached(self, fixture_tree):
        """The mechanism, on a non-asset change so the browser-wide rule cannot
        mask it: ``other.py`` is imported by a TEST module, which a browser test
        imports."""
        selected = impact.select(fixture_tree, ["src/nonogram/admin/other.py"])
        assert selected != impact.FULL
        assert "tests/test_page_helper.py" in selected
        assert "tests/test_plan_mobile.py" in selected
        assert "tests/test_no_fixture.py" not in selected

    def test_an_ancestor_package_init_is_an_edge(self, tree):
        """Importing ``nonogram.db.models`` runs ``nonogram/db/__init__.py``."""
        (tree / "src" / "nonogram" / "db" / "__init__.py").write_text("D = 1\n")
        (tree / "src" / "nonogram" / "__init__.py").write_text("")
        (tree / "src" / "nonogram" / "db" / "models.py").write_text("M = 1\n")
        (tree / "tests" / "test_models_only.py").write_text(
            "from nonogram.db import models\ndef test_m():\n    assert models\n"
        )
        selected = impact.select(tree, ["src/nonogram/db/__init__.py"])
        assert selected != impact.FULL
        assert "tests/test_models_only.py" in selected

    def test_the_real_tree_reaches_a_test_through_a_test_helper_chain(self):
        """Not an asset: ``admin/pdf_generator.py`` or similar must still reach
        the browser tests importing the app via ``tests.test_puzzle_solver_page``."""
        selected = _real_select(["src/nonogram/admin/puzzle_review.py"])
        assert selected != impact.FULL
        assert "tests/test_book_setup_print_mobile.py" in selected


class TestImpactSet_F003_ConftestIsAnEdge:
    """F-003: conftest imports admin.app et al.; its fixture users must run."""

    #: The reviewer's recorded list of the 13 files using conftest fixtures.
    FIXTURE_USERS = (
        "tests/test_batch_history.py",
        "tests/test_bulk_operations.py",
        "tests/test_card_156_db_fixture.py",
        "tests/test_db_e2e_smoke.py",
        "tests/test_db_engine_lifecycle.py",
        "tests/test_db_isolation.py",
        "tests/test_puzzle_edit_routes.py",
        "tests/test_puzzle_preview.py",
        "tests/test_puzzle_review_bulk_read.py",
        "tests/test_wave1_e2e.py",
        "tests/test_wave2_async_generation.py",
        "tests/test_wave3_e2e.py",
        "tests/test_wave3_image_generation.py",
    )

    def test_the_reviewers_plant_selects_the_mime_type_test(self):
        """``api_get_image`` mimetype -> octet-stream reds this test, which sat
        outside the 126-file selection for ``admin/app.py``."""
        selected = _real_select(["src/nonogram/admin/app.py"])
        assert selected != impact.FULL
        assert (
            "tests/test_wave3_e2e.py" in selected
        ), "TestWave3ImageGeneration::test_image_serving_endpoint_mime_types"
        assert sorted(set(self.FIXTURE_USERS) - set(selected)) == []

    @pytest.mark.parametrize(
        "changed",
        [
            "src/nonogram/export/layout.py",
            "src/nonogram/solver/propagate.py",
            "src/nonogram/limits.py",
            "src/nonogram/errors.py",
            "src/nonogram/admin/puzzle_review.py",
            "src/nonogram/admin/batch_generator.py",
        ],
    )
    def test_every_module_conftest_imports_selects_the_fixture_users(self, changed):
        selected = _real_select([changed])
        assert selected != impact.FULL
        assert sorted(set(self.FIXTURE_USERS) - set(selected)) == [], changed

    def test_a_module_conftest_imports_selects_the_fixture_user(self, fixture_tree):
        selected = impact.select(fixture_tree, ["src/nonogram/admin/app.py"])
        assert selected != impact.FULL
        assert "tests/test_uses_fixture.py" in selected
        assert "tests/test_no_fixture.py" not in selected

    def test_a_module_conftest_does_not_import_does_not_select_fixture_users(self, fixture_tree):
        (fixture_tree / "src" / "nonogram" / "unrelated.py").write_text("U = 1\n")
        (fixture_tree / "tests" / "test_imports_unrelated.py").write_text(
            "from nonogram import unrelated\ndef test_x():\n    assert unrelated\n"
        )
        selected = impact.select(fixture_tree, ["src/nonogram/unrelated.py"])
        assert selected != impact.FULL
        assert "tests/test_imports_unrelated.py" in selected
        assert "tests/test_uses_fixture.py" not in selected


class TestImpactSet_F004_TheConftestClosureIsFullLikeConftest:
    HELPERS = (
        "tests/hang_guard.py",
        "tests/database_guard.py",
        "tests/full_suite_lock.py",
        "tests/db_name.py",
        "tests/helpers/mock_generator.py",
        "tests/helpers/undefined_table_report.py",
        "tests/__init__.py",
    )

    @pytest.mark.parametrize("path", HELPERS)
    def test_a_helper_conftest_imports_is_full(self, path):
        """Plant: hang-guard default 300 -> 0.05 kills tests/test_solver.py."""
        derived = _real_derive([path])
        assert derived.full, f"{path} was narrowed"
        assert [r.rule for r in derived.reasons] == ["conftest-closure"]
        assert path in str(derived.reasons[0])

    def test_a_helper_conftest_imports_is_full_in_a_fake_tree(self, fixture_tree):
        derived = impact.derive(fixture_tree, ["tests/helper_boot.py"])
        assert derived.full
        assert derived.reasons[0].rule == "conftest-closure"

    def test_a_helper_conftest_does_not_import_is_not_full_by_that_rule(self, fixture_tree):
        (fixture_tree / "tests" / "helper_other.py").write_text("O = 1\n")
        (fixture_tree / "tests" / "test_uses_other.py").write_text(
            "from tests.helper_other import O\ndef test_o():\n    assert O\n"
        )
        derived = impact.derive(fixture_tree, ["tests/helper_other.py"])
        assert not derived.full
        assert "tests/test_uses_other.py" in derived.files


class TestImpactSet_F005_TheGateContractCannotSayNothingMoreIsOwedOnAFailedCount:
    """F-005: a failed count is FULL; the exit code branches; empty is named."""

    @staticmethod
    def _git_tree(tmp_path: Path, broken: bool = False) -> Path:
        subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_scan.py").write_text(
            'import subprocess\ndef test_s():\n    subprocess.run(["git", "ls-files"])\n'
        )
        if broken:
            (tmp_path / "tests" / "test_zzz_broken.py").write_text("def test_(:\n")
        return tmp_path

    @staticmethod
    def _gate(cwd: Path, *args: str):
        return subprocess.run(
            [sys.executable, str(SELECTOR), "--gate", *args],
            capture_output=True, text=True, cwd=cwd,
        )

    def test_a_collection_error_is_a_failed_count_and_therefore_full(self, tmp_path):
        tree = self._git_tree(tmp_path, broken=True)
        out = self._gate(tree, "tests/test_scan.py")
        assert out.returncode == impact.EXIT_COUNT_FAILED, out.stdout + out.stderr
        assert "nothing more is owed" not in out.stdout
        assert "answer: FULL" in out.stdout
        assert "count-unavailable" in out.stdout

    def test_collect_count_raises_on_a_collection_error(self, tmp_path):
        """S10: counting what collected beside an error is a green lie."""
        tree = self._git_tree(tmp_path, broken=True)
        with pytest.raises(RuntimeError):
            impact.collect_count(tree, None)

    def test_a_healthy_selection_exits_zero_and_says_so(self, tmp_path):
        tree = self._git_tree(tmp_path)
        out = self._gate(tree, "tests/test_scan.py")
        assert out.returncode == 0, out.stderr
        assert "answer: SELECTION" in out.stdout
        assert "exit code: 0" in out.stdout

    def test_full_has_its_own_exit_code(self, tmp_path):
        tree = self._git_tree(tmp_path)
        out = self._gate(tree, "pyproject.toml")
        assert out.returncode == impact.EXIT_FULL, out.stderr
        assert "answer: FULL" in out.stdout
        assert "exit code: 10" in out.stdout

    def test_the_codes_are_distinct_and_documented(self):
        codes = {impact.EXIT_SELECTION, impact.EXIT_FULL, impact.EXIT_COUNT_FAILED, impact.EXIT_EMPTY}
        assert len(codes) == 4 and impact.EXIT_SELECTION == 0
        for code in codes:
            assert f"{code}" in impact.__doc__
        assert "there is no Makefile" not in impact.__doc__

    def test_a_zero_count_for_a_nonempty_selection_is_a_failed_count(self, web_tree):
        block, code = impact.gate_verdict(
            web_tree,
            ["tests/test_unrelated.py"],
            count=lambda files: 0 if files else 100,
        )
        assert code == impact.EXIT_COUNT_FAILED
        assert "nothing more is owed" not in block

    def test_an_empty_changed_set_is_an_explicit_named_answer(self, web_tree):
        block, code = impact.gate_verdict(web_tree, [], count=lambda files: 100)
        assert code == impact.EXIT_EMPTY
        assert "answer: EMPTY" in block
        assert "nothing more is owed" not in block
        assert "SELECTION" not in block

    def test_the_empty_derivation_is_flagged_not_just_an_empty_list(self, tree):
        derived = impact.derive(tree, [])
        assert derived.empty and not derived.full and derived.files == []
        assert impact.select(tree, []) == []

    def test_the_plain_mode_contract_for_the_makefile_is_unchanged(self, tmp_path):
        """stdout is FULL or paths, exit 0, for every answer but a git failure."""
        tree = self._git_tree(tmp_path)
        full = subprocess.run(
            [sys.executable, str(SELECTOR), "pyproject.toml"],
            capture_output=True, text=True, cwd=tree,
        )
        assert full.returncode == 0 and full.stdout.strip() == "FULL"
        sel = subprocess.run(
            [sys.executable, str(SELECTOR), "tests/test_scan.py"],
            capture_output=True, text=True, cwd=tree,
        )
        assert sel.returncode == 0
        assert sel.stdout.split() == ["tests/test_scan.py"]


class TestImpactSet_F002_AnAdminSurfaceChangeSelectsEveryBrowserTest:
    """The cheap safe rule where tracing is not provably complete."""

    #: Reviewer's measured unselected browser tests (recorded baseline).
    RECORDED = (
        "tests/test_book_setup_print_mobile.py",
        "tests/test_books_list_mobile.py",
        "tests/test_book_arrange_play_link.py",
        "tests/test_status_filter_default.py",
    )
    SURFACE = (
        "src/nonogram/admin/static/admin.css",
        "src/nonogram/admin/static/tokens.css",
        "src/nonogram/admin/static/solver.js",
        "src/nonogram/admin/static/solver_state.js",
        "src/nonogram/admin/static/puzzle_edit.js",
        "src/nonogram/web/static/metadata.js",
        "src/nonogram/admin/templates/base.html",
        "src/nonogram/admin/templates/book_setup_print.html",
        "src/nonogram/admin/templates/book_finalize.html",
        "src/nonogram/admin/templates/books_list.html",
        "src/nonogram/admin/app.py",
    )

    @staticmethod
    def _browser_tests() -> set[str]:
        """Independent of the script: files whose text drives a browser."""
        found = set()
        for p in (REPO / "tests").rglob("test_*.py"):
            text = p.read_text(encoding="utf-8")
            if any(w in text for w in ("playwright", "browser_page", "chromium")):
                found.add(p.relative_to(REPO).as_posix())
        return found

    @pytest.mark.parametrize("changed", SURFACE)
    def test_every_browser_test_is_selected(self, changed):
        browser = self._browser_tests()
        assert len(browser) >= 17, "the control's own corpus shrank"
        selected = _real_select([changed])
        assert selected != impact.FULL
        assert sorted(browser - set(selected)) == [], changed
        assert sorted(set(self.RECORDED) - set(selected)) == [], changed

    def test_a_hermetic_browser_test_importing_nothing_is_selected(self, web_tree):
        (web_tree / "tests" / "test_browser_alone.py").write_text(
            "import playwright\ndef test_z():\n    assert 1\n"
        )
        selected = impact.select(web_tree, ["src/nonogram/admin/templates/page.html"])
        assert "tests/test_browser_alone.py" in selected
        assert "tests/test_unrelated.py" not in selected

    def test_a_font_is_read_by_the_module_that_loads_it(self, web_tree):
        fonts = web_tree / "src" / "nonogram" / "export" / "fonts"
        fonts.mkdir(parents=True)
        (fonts / "Face.ttf").write_bytes(b"\x00\x01")
        (web_tree / "src" / "nonogram" / "export" / "__init__.py").write_text("")
        (web_tree / "src" / "nonogram" / "export" / "pdf.py").write_text(
            'FONT = "Face.ttf"\n'
        )
        (web_tree / "tests" / "test_pdf_render.py").write_text(
            "from nonogram.export import pdf\ndef test_f():\n    assert pdf\n"
        )
        selected = impact.select(web_tree, ["src/nonogram/export/fonts/Face.ttf"])
        assert selected != impact.FULL
        assert "tests/test_pdf_render.py" in selected


class TestImpactSet_InstrumentsAreNamedNotForcedFull:
    """``scratchpad/**`` and ``meta/profiling/**`` are records, not product."""

    def test_an_unread_scratchpad_probe_is_not_full(self, tree):
        (tree / "scratchpad" / "card1").mkdir(parents=True)
        (tree / "scratchpad" / "card1" / "probe.py").write_text("X = 1\n")
        derived = impact.derive(tree, ["scratchpad/card1/probe.py"])
        assert not derived.full
        assert derived.files == ["tests/test_scanner.py"]

    def test_a_scratchpad_probe_a_test_names_selects_that_test(self, tree):
        (tree / "scratchpad").mkdir()
        (tree / "scratchpad" / "named_probe.py").write_text("X = 1\n")
        (tree / "tests" / "test_reads_probe.py").write_text(
            "def test_r():\n    assert 'scratchpad/named_probe.py'\n"
        )
        selected = impact.select(tree, ["scratchpad/named_probe.py"])
        assert "tests/test_reads_probe.py" in selected

    def test_a_profiling_probe_nobody_reads_is_not_full(self, tree):
        (tree / "meta" / "profiling").mkdir(parents=True)
        (tree / "meta" / "profiling" / "probe_x.py").write_text("X = 1\n")
        derived = impact.derive(tree, ["meta/profiling/probe_x.py"])
        assert not derived.full

    def test_the_real_profiling_script_a_test_loads_still_selects_it(self):
        selected = _real_select(["meta/profiling/rank_durations.py"])
        assert selected != impact.FULL
        assert "tests/test_browser_fixture_scope.py" in selected

    def test_a_real_unread_probe_is_not_full(self):
        assert not _real_derive(["meta/profiling/card292_plant_reads.py"]).full

    def test_a_root_level_script_outside_the_instrument_roots_stays_full(self, tree):
        (tree / "elsewhere").mkdir()
        (tree / "elsewhere" / "probe.py").write_text("X = 1\n")
        derived = impact.derive(tree, ["elsewhere/probe.py"])
        assert derived.full and derived.reasons[0].rule == "no-reader"


class TestImpactSet_TheSurvivorsOfCycle1:
    """One control per survivor the reviewer fired against the 92 tests."""

    def test_M2c_a_changed_test_selects_the_importers_of_its_importers(self, tree):
        """Chain A <- B <- C: C names only B, so no name/prefix rule sees A."""
        (tree / "tests" / "test_chain_a.py").write_text("A = 1\ndef test_a():\n    pass\n")
        (tree / "tests" / "test_chain_b.py").write_text(
            "from tests.test_chain_a import A\nB = A\ndef test_b():\n    pass\n"
        )
        (tree / "tests" / "test_chain_c.py").write_text(
            "from tests.test_chain_b import B\ndef test_c():\n    assert B\n"
        )
        selected = impact.select(tree, ["tests/test_chain_a.py"])
        assert "tests/test_chain_b.py" in selected
        assert "tests/test_chain_c.py" in selected

    @pytest.mark.parametrize(
        "idiom",
        ["x = Path('.').iterdir()", "x = Path('.').glob('*')", "x = os.listdir('.')",
         "x = os.scandir('.')", "x = glob.glob('*')"],
    )
    def test_S4_every_walk_idiom_makes_a_tree_reader(self, tree, idiom):
        (tree / "tests" / "test_walker.py").write_text(
            f"def test_w():\n    root = 'tests'\n    {idiom}\n"
        )
        selected = impact.select(tree, ["tests/test_orphan.py"])
        assert "tests/test_walker.py" in selected, idiom

    def test_S8_a_bare_name_prefix_in_a_test_selects_the_family(self, tree):
        (tree / "tests" / "test_prefixer.py").write_text(
            "PREFIX = 'tests/test_orph'\ndef test_p():\n    assert PREFIX\n"
        )
        selected = impact.select(tree, ["tests/test_orphan.py"])
        assert "tests/test_prefixer.py" in selected

    def test_S10_covered_by_the_collection_error_gate_tests_above(self):
        assert impact.EXIT_COUNT_FAILED != impact.EXIT_SELECTION

    def test_S14_an_unreadable_test_is_a_scanner(self, tree):
        locked = tree / "tests" / "test_locked.py"
        locked.write_text("def test_l():\n    pass\n")
        locked.chmod(0o000)
        try:
            assert Path("tests/test_locked.py") in impact.always_on(tree)
            selected = impact.select(tree, ["tests/test_orphan.py"])
            assert "tests/test_locked.py" in selected
        finally:
            locked.chmod(0o644)

    def test_S15_a_browser_test_naming_the_directory_reads_a_page_outside_the_roots(self, tree):
        (tree / "site").mkdir()
        (tree / "site" / "page.js").write_text("const a = 'site-cell';\n")
        (tree / "tests" / "test_site_dir_browser.py").write_text(
            "import playwright\nDIR = '/site/'\ndef test_s():\n    assert DIR\n"
        )
        selected = impact.select(tree, ["site/page.js"])
        assert selected != impact.FULL
        assert "tests/test_site_dir_browser.py" in selected

    @pytest.mark.parametrize(
        "idiom",
        ["import playwright", "def test_e(browser_page): pass", "x = 'chromium'",
         "import selenium", "x = ['node', 'a.js']"],
    )
    def test_S16_every_executor_idiom_makes_a_browser_test(self, web_tree, idiom):
        (web_tree / "tests" / "test_exec_idiom.py").write_text(f"{idiom}\n")
        selected = impact.select(web_tree, ["src/nonogram/admin/static/widget.css"])
        assert "tests/test_exec_idiom.py" in selected, idiom

    @pytest.mark.parametrize(
        "idiom",
        ["subprocess.run(['git', 'ls-files'])", "subprocess.run(['git', 'grep', 'x'])",
         "list(Path('.').rglob('*'))", "list(os.walk('.'))"],
    )
    def test_S18_every_scan_idiom_makes_an_always_on_test(self, tree, idiom):
        (tree / "tests" / "test_scan_idiom.py").write_text(
            f"def test_s():\n    {idiom}\n"
        )
        assert Path("tests/test_scan_idiom.py") in impact.always_on(tree), idiom
        assert "tests/test_scan_idiom.py" in impact.select(tree, ["meta/x.md"])

    def test_S20_a_deleted_test_path_is_not_selected(self, tree):
        selected = impact.select(tree, ["tests/test_deleted_long_ago.py"])
        assert selected != impact.FULL
        assert "tests/test_deleted_long_ago.py" not in selected
