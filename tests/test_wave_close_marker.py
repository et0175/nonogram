"""CARD-395: the ``wave_close_only`` marker swallows no test, and its registry cannot rot.

The gate stops running the heaviest sweeps; the wave close still runs them bare.
That move is only safe while four things hold, one block each below:

* AC-1 the marker only ADDS a mark: bare collection, collection with the plugin
  disabled, and the marked / unmarked partition are the same node-id set;
* AC-2 the registry and the collected marked set are equal in both directions
  (a renamed test reds the suite rather than silently un-marking);
* AC-3 every marked file keeps a smoke slice and its controls, UNMARKED;
* AC-4 the corpus floors inside the marked tests never shrink (G-4, CARD-220 AC-4);

and AC-7: the wave close and ``review.test_command`` stay bare.

Every check is a pure function over (registry, collected ids, source text), run
once on the real tree and once on a planted defect, so each can be seen to fail.
The three ``--collect-only`` children are the only subprocesses, and they are
shared (one module fixture) because collecting this suite costs ~12 s.
"""

from __future__ import annotations

import ast
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests import wave_close_marker as wcm

REPO = Path(__file__).resolve().parent.parent
_NODE = re.compile(r"^[\w./-]+\.py::\S")


def _collect(*args: str) -> set[str]:
    """Node ids of a ``--collect-only`` child run with the project's own config."""
    cmd = [
        sys.executable, "-m", "pytest", "--collect-only", "-q",
        "-o", "addopts=", "-p", "no:cacheprovider", *args,
    ]
    out = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
    assert out.returncode in (0, 5), out.stdout[-3000:] + out.stderr[-3000:]
    return {line.strip() for line in out.stdout.splitlines() if _NODE.match(line.strip())}


@pytest.fixture(scope="module")
def collected() -> SimpleNamespace:
    """The four collections every AC below reads, taken once."""
    return SimpleNamespace(
        bare=_collect(),
        # Plugin disabled by name. `-m "not wave_close_only"` selects everything
        # iff nothing is marked, so this one run is both "the same set as bare"
        # and "the plugin really is off".
        plugin_off=_collect("-p", "no:wave_close_marker", "-m", f"not {wcm.MARKER}"),
        marked=_collect("-m", wcm.MARKER),
        unmarked=_collect("-m", f"not {wcm.MARKER}"),
    )


# --------------------------------------------------------------------------
# The checks, as pure functions (so a planted defect can be shown to fail them).
# --------------------------------------------------------------------------


def swallowed(bare: set[str], plugin_off: set[str], marked: set[str], unmarked: set[str]) -> list[str]:
    """AC-1: what is wrong with the four collections."""
    problems = []
    if bare != plugin_off:
        problems.append(f"bare != plugin disabled: only bare {sorted(bare - plugin_off)[:3]}, only off {sorted(plugin_off - bare)[:3]}")
    if marked & unmarked:
        problems.append(f"marked and unmarked overlap: {sorted(marked & unmarked)[:3]}")
    if marked | unmarked != bare:
        problems.append(f"marked + unmarked != bare: missing {sorted(bare - (marked | unmarked))[:3]}")
    return problems


def registry_problems(entries, bare: set[str], marked: set[str]) -> list[str]:
    """AC-2: orphan patterns, marked nodes outside the registry, over-marking."""
    problems = []
    for entry in entries:
        for pattern in entry.marked:
            if not any(wcm.matches(n, (pattern,)) for n in bare):
                problems.append(f"{entry.file}: pattern {pattern!r} matches no collected node (renamed?)")
        in_file = {n for n in bare if n.split("::", 1)[0] == entry.file}
        marked_in_file = {n for n in in_file if wcm.matches(n, entry.marked)}
        smoke = {n for n in in_file if wcm.matches(n, entry.smoke)}
        if len(marked_in_file) > len(in_file) - len(smoke):
            problems.append(f"{entry.file}: marks {len(marked_in_file)} of {len(in_file)} with {len(smoke)} smoke")
    patterns = tuple(p for e in entries for p in e.marked)
    for node in sorted(marked):
        if not wcm.matches(node, patterns):
            problems.append(f"{node}: carries the marker but matches no registry pattern")
    for node in sorted(bare):
        if wcm.matches(node, patterns) and node not in marked:
            problems.append(f"{node}: matches a registry pattern but is not marked")
    return problems


def keep_problems(entries, bare: set[str], marked: set[str], unmarked: set[str]) -> list[str]:
    """AC-3: smoke and controls exist, are unmarked, and are in the gate's set."""
    problems = []
    for entry in entries:
        if not entry.smoke:
            problems.append(f"{entry.file}: names no smoke slice")
        for kind, patterns in (("smoke", entry.smoke), ("control", entry.controls)):
            for pattern in patterns:
                hits = {n for n in bare if wcm.matches(n, (pattern,))}
                if not hits:
                    problems.append(f"{entry.file}: {kind} {pattern!r} matches no collected node")
                for node in sorted(hits):
                    if node in marked:
                        problems.append(f"{node}: {kind} is MARKED")
                    elif node not in unmarked:
                        problems.append(f"{node}: {kind} is not in the gate's collection")
    return problems


def collect_floors(source: str, function: str) -> dict[str, int]:
    """``{expression: minimum}`` for the top-level ``assert <expr> >= N`` (or ``> N``)
    lines of ``function``; a bare name on the right resolves to a module constant."""
    tree = ast.parse(source)
    constants = {
        node.targets[0].id: node.value.value
        for node in tree.body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, int)
    }
    found: dict[str, int] = {}
    for fn in ast.walk(tree):
        if not (isinstance(fn, ast.FunctionDef) and fn.name == function):
            continue
        for stmt in fn.body:
            test = stmt.test if isinstance(stmt, ast.Assert) else None
            if not (isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], (ast.GtE, ast.Gt))):
                continue
            right = test.comparators[0]
            value = right.value if isinstance(right, ast.Constant) else constants.get(getattr(right, "id", ""))
            if isinstance(value, int):
                found[ast.unparse(test.left)] = value + (1 if isinstance(test.ops[0], ast.Gt) else 0)
    return found


def floor_problems(entries, read=lambda rel: (REPO / rel).read_text(encoding="utf-8")) -> list[str]:
    """AC-4: a recorded floor that is lower in the source, or gone."""
    problems = []
    for entry in entries:
        source = read(entry.file)
        for function, recorded in entry.floors.items():
            now = collect_floors(source, function)
            if not now and recorded:
                problems.append(f"{entry.file}::{function}: no floor assert found at all")
            for expression, minimum in recorded.items():
                if expression not in now:
                    problems.append(f"{entry.file}::{function}: floor on {expression!r} (>= {minimum}) was removed")
                elif now[expression] < minimum:
                    problems.append(f"{entry.file}::{function}: floor on {expression!r} lowered {minimum} -> {now[expression]}")
    return problems


# --------------------------------------------------------------------------
# AC-1 -- the marker swallows no test.
# --------------------------------------------------------------------------


class TestWaveCloseMarker_SwallowsNoTest:
    def test_bare_collection_equals_collection_with_the_plugin_disabled(self, collected):
        assert swallowed(collected.bare, collected.plugin_off, collected.marked, collected.unmarked) == []
        assert len(collected.bare) > 5000, "the collection is implausibly small: the child collected nothing"

    def test_the_marked_and_unmarked_runs_partition_the_bare_set(self, collected):
        assert collected.marked and collected.unmarked
        assert collected.marked.isdisjoint(collected.unmarked)
        assert collected.marked | collected.unmarked == collected.bare

    def test_the_hook_only_adds_a_mark_and_never_reorders_or_removes(self):
        class Item:
            def __init__(self, nodeid):
                self.nodeid, self.marks = nodeid, []

            def add_marker(self, mark):
                self.marks.append(mark.name)

        ids = [
            "tests/test_kill_matrix.py::test_ac7_the_four_arm_grid_of_card_257_reproduces",
            "tests/test_kill_matrix.py::test_ac1_anything",
            "tests/test_other.py::test_x",
        ]
        items = [Item(n) for n in ids]
        before = list(items)
        wcm.pytest_collection_modifyitems(None, items)
        assert items == before, "the hook changed the list"
        assert [i.marks for i in items] == [[wcm.MARKER], [], []]

    def test_the_plant_a_hook_that_deletes_an_item_is_caught(self, collected):
        """The control: the checker reds on exactly the defect AC-1 exists for."""
        victim = sorted(collected.bare)[0]
        dropped = collected.bare - {victim}
        assert swallowed(collected.bare, dropped, collected.marked, collected.unmarked)
        assert swallowed(collected.bare, collected.bare, collected.marked, collected.unmarked - {victim})
        assert swallowed(collected.bare, collected.bare, collected.marked | {victim}, collected.unmarked)

    def test_the_marker_is_registered_in_pyproject(self):
        config = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
        markers = config["tool"]["pytest"]["ini_options"]["markers"]
        assert any(m.startswith(f"{wcm.MARKER}:") for m in markers), markers
        assert any(m.startswith("browser:") for m in markers), "the existing marker is gone"
        assert "slow" not in " ".join(markers), "slow is conftest's, informational, and is not reused"


# --------------------------------------------------------------------------
# AC-2 -- the marked set is pinned, derived, closed.
# --------------------------------------------------------------------------


class TestWaveCloseMarker_TheMarkedSetIsPinnedBothWays:
    def test_every_pattern_matches_and_every_marked_node_is_registered(self, collected):
        assert registry_problems(wcm.REGISTRY, collected.bare, collected.marked) == []
        assert collected.marked, "nothing is marked: the registry is inert"

    def test_the_plant_a_renamed_test_reds_instead_of_unmarking(self, collected):
        """The renamed test: the registry still says the old name."""
        entry = wcm.LIST_1[0]
        old = entry.marked[0]
        renamed = {n.replace("Drawing", "Drawings") if wcm.matches(n, (old,)) else n for n in collected.bare}
        problems = registry_problems(wcm.REGISTRY, renamed, collected.marked - {old})
        assert any(old in p for p in problems), problems


# --------------------------------------------------------------------------
# AC-3 -- each marked file keeps its smoke slice and its controls at the gate.
# --------------------------------------------------------------------------


class TestWaveCloseMarker_TheGateKeepsSmokeAndControls:
    def test_every_smoke_and_control_exists_is_unmarked_and_is_in_the_gate_set(self, collected):
        assert keep_problems(wcm.REGISTRY, collected.bare, collected.marked, collected.unmarked) == []

    def test_the_plant_a_marked_control_is_caught(self, collected):
        control = next(c for c in wcm.LIST_1[0].controls)
        problems = keep_problems(
            wcm.REGISTRY, collected.bare, collected.marked | {control}, collected.unmarked - {control}
        )
        assert any("MARKED" in p for p in problems), problems


# --------------------------------------------------------------------------
# AC-4 -- corpus floors never shrink (G-4).
# --------------------------------------------------------------------------

#: Hand-written pins on the largest floors, so that lowering a number in the
#: SOURCE and in the registry in one commit still reds here: the registry alone
#: is a record the same hand can edit. These are the numbers the sweeps were
#: written against; raising them is fine, lowering them is the defect.
PINNED_FLOORS = {
    ("test_PropertyTest_BookLayout_DrawingFitsUsableAreaUnderStandardCell_pdf_pages", "checked"): 200,
    ("test_PropertyTest_BookPdf_PortraitWithFixedTopEdgeForEveryExtent_pdf_pages", "len(extents)"): 120,
    ("test_PropertyTest_BookPdf_PortraitWithFixedTopEdgeForEveryExtent_pdf_pages", "counted"): 150,
    ("test_PropertyTest_BookPdf_MirroredMarginsCentreDrawingForEveryParity_pdf_pages", "checked"): 100,
    ("test_PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage", "len(cases)"): 28,
    ("test_PropertyTest_BookPairing_InOrderSameTierFittingNeighboursOnly_interior_pages", "books"): 15,
    ("test_PropertyTest_BookPairing_InOrderSameTierFittingNeighboursOnly_interior_pages", "pages"): 40,
}


class TestWaveCloseMarker_CorpusFloorsNeverShrink:
    def test_every_recorded_floor_is_still_in_the_marked_test_it_guards(self):
        assert floor_problems(wcm.REGISTRY) == []

    def test_the_registry_records_the_floors_of_the_three_property_files(self):
        recorded = {(fn, expr): n for e in wcm.REGISTRY for fn, floors in e.floors.items() for expr, n in floors.items()}
        for key, minimum in PINNED_FLOORS.items():
            assert recorded.get(key, 0) >= minimum, f"the registry no longer records {key} >= {minimum}"
        assert len(recorded) >= 20, "the floor table shrank"

    def test_the_plant_a_lowered_floor_is_caught(self):
        entry = wcm.LIST_1[0]
        original = (REPO / entry.file).read_text(encoding="utf-8")
        assert "assert checked >= 200, checked" in original
        planted = original.replace("assert checked >= 200, checked", "assert checked >= 20, checked")
        problems = floor_problems((entry,), read=lambda rel: planted)
        assert any("lowered 200 -> 20" in p for p in problems), problems


# --------------------------------------------------------------------------
# AC-7 -- the wave close and the backstop cannot be narrowed by accident.
# --------------------------------------------------------------------------


def _recipe(makefile: str, target: str) -> list[str]:
    """The recipe lines (tab-indented) of ``target``."""
    lines = makefile.splitlines()
    start = lines.index(f"{target}:")
    out = []
    for line in lines[start + 1:]:
        if line.startswith("\t"):
            out.append(line.strip())
        elif out and not line.startswith(("\t", " ")) and line.strip() and not line.startswith("#"):
            break
        elif line.strip() == "" and out:
            break
    return out


def command_problems(command: str) -> list[str]:
    """A command that must run the whole suite: no ``-m`` / ``--markexpr``."""
    problems = []
    arguments = command.partition("pytest")[2]  # `python -m pytest`'s own -m is the interpreter's
    if re.search(r"(^|\s)-[A-Za-z]*m(\s|$)|--markexpr", arguments):
        problems.append(f"{command!r} narrows the run with -m")
    if "pytest" not in command:
        problems.append(f"{command!r} is not a pytest command")
    return problems


class TestWaveCloseMarker_TheWaveCloseIsBare:
    def test_make_test_and_the_wave_close_are_the_bare_pytest_line(self):
        makefile = (REPO / "Makefile").read_text(encoding="utf-8")
        assert _recipe(makefile, "test") == ["$(PY) -m pytest"]
        wave_close = _recipe(makefile, "test-wave-close")
        assert wave_close[-1] == "$(PY) -m pytest"
        assert [c for c in wave_close if "pytest" in c and "PYTEST_ADDOPTS" not in c and "echo" not in c] == ["$(PY) -m pytest"]
        assert any("PYTEST_ADDOPTS" in c for c in wave_close), "the wave close does not look at PYTEST_ADDOPTS"
        assert _recipe(makefile, "test-marked") == ["$(PY) -m pytest -m wave_close_only"]

    def test_review_test_command_is_bare_and_the_gate_form_is_named(self):
        text = (REPO / "meta" / "kanban" / "config.yml").read_text(encoding="utf-8")
        review = re.search(r'^  test_command:\s*"(?P<value>[^"]*)"', text, re.M)
        assert review is not None, "review.test_command is not in config.yml"
        assert command_problems(review["value"]) == []
        assert review["value"] == "./.venv/bin/python -m pytest"
        gate = re.search(r'^  gate_test_command:\s*"(?P<value>[^"]*)"', text, re.M)
        assert gate is not None and gate["value"] == "make test-gate"

    def test_PYTEST_ADDOPTS_with_a_marker_expression_makes_the_wave_close_refuse(self):
        assert shutil.which("make"), "make is not installed: the wave-close refusal cannot be run"
        import os

        def run(addopts: str) -> subprocess.CompletedProcess:
            env = {**os.environ, "PYTEST_ADDOPTS": addopts}
            # PY=true: the recipe's last line becomes `true -m pytest`, a no-op.
            return subprocess.run(
                ["make", "-s", "PY=true", "test-wave-close"],
                cwd=REPO, capture_output=True, text=True, env=env,
            )

        for narrowed in ('-m "not wave_close_only"', "-qm x", "--markexpr=x", "-k foo", "--deselect a", "--ignore=tests/a", "--ignore-glob=x"):
            refused = run(narrowed)
            assert refused.returncode == 2, (narrowed, refused.stdout, refused.stderr)
            assert "WAVE CLOSE" not in refused.stdout
        for fine in ("", "-q --maxfail=2 -rEfs", "--durations=0 --durations-min=0", "-p no:cacheprovider"):
            ok = run(fine)
            assert ok.returncode == 0, (fine, ok.stdout, ok.stderr)
            assert "WAVE CLOSE: full suite, no marker deselection" in ok.stdout


# --------------------------------------------------------------------------
# AC-8 (the script half) -- the hotspots report's wave-close share is derived
# from the registry, and the report without it is what it always was.
# --------------------------------------------------------------------------


def _ranker():
    import importlib.util

    path = REPO / "meta" / "profiling" / "rank_durations.py"
    spec = importlib.util.spec_from_file_location("card395_rank_durations", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # @dataclass resolves annotations through sys.modules
    spec.loader.exec_module(module)
    return module


def _independent_share(text: str, patterns: tuple[str, ...]) -> tuple[float, int]:
    """Marked seconds and tests by a second reader of the artefact (a regex per line)."""
    seconds: dict[str, float] = {}
    for match in re.finditer(r"^(?P<s>[\d.]+)s (?:call|setup|teardown)\s+(?P<id>\S+)$", text, re.M):
        seconds[match["id"]] = seconds.get(match["id"], 0.0) + float(match["s"])
    chosen = [n for n in seconds if wcm.matches(n, patterns)]
    return sum(seconds[n] for n in chosen), len(chosen)


class TestWaveCloseMarker_TheHotspotsShareIsDerivedFromTheRegistry:
    ARTEFACT = REPO / "meta" / "profiling" / "suite-durations-20261023.txt"

    def test_the_share_is_the_registrys_own_and_a_second_reader_agrees(self):
        ranker = _ranker()
        text = self.ARTEFACT.read_text(encoding="utf-8")
        profile = ranker.parse_artefact(text)
        patterns = wcm.marked_patterns()
        seconds, tests, files = ranker.wave_close_share(profile, patterns)
        other_seconds, other_tests = _independent_share(text, patterns)
        assert tests == other_tests and tests >= 10
        assert seconds == pytest.approx(other_seconds, abs=0.01) and seconds > 100
        report = ranker.report(profile, self.ARTEFACT, "0" * 64, patterns)
        assert f"time: {seconds:.2f}s" in report.partition("## Wave-close share")[2]
        assert f"registry patterns: {len(patterns)}" in report

    def test_without_the_registry_the_report_is_byte_for_byte_what_it_was(self):
        ranker = _ranker()
        profile = ranker.parse_artefact(self.ARTEFACT.read_text(encoding="utf-8"))
        plain = ranker.report(profile, self.ARTEFACT, "0" * 64)
        assert "Wave-close share" not in plain
        assert ranker.report(profile, self.ARTEFACT, "0" * 64, None) == plain
        withheld = ranker.report(profile, self.ARTEFACT, "0" * 64, wcm.marked_patterns())
        assert withheld.startswith(plain), "the new section must only append"


def share_block(report_text: str) -> str:
    """The script's own 'Wave-close share' section, heading to end."""
    return report_text.partition("## Wave-close share")[2]


def share_problems(document: str, generated: str) -> list[str]:
    """What is wrong with a hotspots document's wave-close row against the script's."""
    wanted = share_block(generated)
    figures = [line for line in wanted.splitlines() if line.startswith(("tests:", "time:", "share of attributed time:"))]
    got = share_block(document)
    return [f"missing from the document: {line!r}" for line in figures if line not in got]


class TestWaveCloseMarker_TheHotspotsDocumentCarriesTheScriptsOwnShare:
    """AC-8's document half. Every hotspots document dated on or after the
    marker (2026-11-07) must carry the share block the script prints for its
    artefact, line for line; older documents pre-date the marker and are exempt
    BY DATE, not by absence (so a new document cannot dodge it by omitting the
    block)."""

    FIRST_DATE = "20261107"

    @staticmethod
    def _pairs():
        profiling = REPO / "meta" / "profiling"
        for artefact in sorted(profiling.glob("suite-durations-*.txt")):
            date = artefact.stem.removeprefix("suite-durations-")
            yield date, artefact, profiling / f"suite-hotspots-{date}.md"

    def test_every_document_from_the_marker_onward_carries_the_block(self):
        ranker = _ranker()
        for date, artefact, document in self._pairs():
            if date < self.FIRST_DATE:
                continue
            raw = artefact.read_bytes()
            import hashlib

            profile = ranker.parse_artefact(raw.decode("utf-8", errors="replace"))
            generated = ranker.report(
                profile, artefact, hashlib.sha256(raw).hexdigest(), wcm.marked_patterns()
            )
            assert "## Wave-close share" in document.read_text(encoding="utf-8"), f"{document.name} omits the block"
            assert share_problems(document.read_text(encoding="utf-8"), generated) == [], document.name


class TestWaveCloseMarker_TheGateTargetRunsEveryCommand:
    def test_run_2_runs_after_run_1_fails_and_the_exit_code_propagates(self, tmp_path):
        """A stub interpreter prints a canned block and logs the commands it is
        given. `make test-gate` must run BOTH printed commands even when the first
        fails, exit nonzero, and pass the selector's EMPTY code (12) through
        without running anything."""
        assert shutil.which("make"), "make is not installed"
        import os

        log = tmp_path / "ran.log"
        stub = tmp_path / "stub.sh"
        stub.write_text(
            "#!/bin/sh\n"
            'if [ "$1" = "scripts/impact_set.py" ]; then\n'
            "  printf 'IMPACT GATE\\nrun 1: python -m pytest FAILME\\nrun 2: python -m pytest -m wave_close_only tests/b.py\\n'\n"
            "  exit ${STUB_CODE:-0}\n"
            "fi\n"
            f'echo "$*" >> {log}\n'
            'case "$*" in *FAILME*) exit 1;; esac\n'
            "exit 0\n"
        )
        stub.chmod(0o755)

        def gate(code: str) -> subprocess.CompletedProcess:
            return subprocess.run(
                ["make", "-s", f"PY={stub}", "BASE=HEAD", "test-gate"],
                cwd=REPO, capture_output=True, text=True, env={**os.environ, "STUB_CODE": code},
            )

        failed = gate("0")
        assert failed.returncode != 0, failed.stdout
        ran = log.read_text().splitlines()
        assert [r.split(" ", 2)[-1] for r in ran] == ["FAILME", "-m wave_close_only tests/b.py"], ran
        log.unlink()
        empty = gate("12")
        assert empty.returncode == 2 and "Error 12" in empty.stderr + empty.stdout, (empty.stdout, empty.stderr)
        assert not log.exists(), "EMPTY ran a command"

