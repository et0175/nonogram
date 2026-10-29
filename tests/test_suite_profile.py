"""CARD-217 -- the suite duration profile and the rankings derived from it.

This card measures the suite; these tests guard the measurement. They assert
that the committed artefact is complete and honest about its conditions
(AC-1), that the derivation from artefact to rankings is reproducible (AC-2),
that a contended run cannot be passed off as the profile (AC-4), and that the
append to ``meta/kanban/suite-timing.log`` keeps the format every wave reads
(AC-5).

CARD-238 cut the one thing here that was never about the code: two tests used
to read that live log, which is gitignored and written by the pipeline, so
their verdict flipped with the host. The format contract is unchanged and is
now asserted only against logs the tests construct, and two structural guards
at the foot of this module keep it that way.

These tests parse text and none of them renders anything, but they are not
free, and the claim that they "shell out exactly once" stopped being true
when CARD-238 added the sandbox comparison. **No test count is given here.**
The sentence that stood in this paragraph said "331 tests" over a module
that collected 341, and CARD-238's own claim sweep asserted that sentence had
been corrected -- the one sweep row the review found wrong on measurement, in
the cycle whose subject was false counts. A count in a docstring cannot go
red when it stops being true, and this module adds tests every time it is
opened, so the number is deleted rather than updated: ``--collect-only -q``
answers it in a second and cannot be stale. The cost, measured on the owner's
host on 2026-10-16: **16.5-16.7s** over three runs on a host whose 1-minute
load average moved between 5.3 and 8.9, in ten subprocesses of its own --
two ranker runs in
``test_rerunning_the_script_is_byte_identical``, six ``git ls-files``
listings behind :func:`_files_under_guard`, and two whole-module pytest
sessions in ``test_the_outcomes_are_identical_with_and_without_the_log``
(which launch four more between them). That one test is 11.7-12.4s of the
total; the two AST scans over both guarded territories are 1.3s each, one
per guard class, since review cycle 3's F-301 put the silence detector over
the same guarded sources as the path guard; and building a sandbox to check
what resolves outside it is 0.1s. The earlier figures -- 16.5-19.8s at load
7.3-12.4 (cycle 4) and 10.7-12.8s at load 3.7-4.0 (cycle 3) -- are not
comparable across loads. CARD-239 measured 16.1-17.2s at load 2-4, with the
stdlib construction probe adding a call per surface spelling and no
subprocess.

Re-measured 2026-10-29 by CARD-304 on a different host (arm64 Darwin 25.6):
**30.4-34.0s over four runs**, and that is the figure WITHOUT CARD-304's own
class as much as with it -- two runs each way, interleaved, 30.37/33.98 against
31.76/33.10. The class costs 3.74-4.03s run alone, which is inside that spread,
so no delta for it is claimed from the module total: a difference smaller than
the quantity's run-to-run spread is not a difference. The 2026-10-16 figures
above are kept rather than replaced, with their domain (that host, that date)
now explicit, because they are what two cards were sized against.
Review cycle 5's added tests are the stdlib-surface audit and the controls
generated from the sets it audits; they add no subprocess and no second
scan, and the two scans' own costs came out at 1.3s each, inside cycle 4's
1.4s and 2.0s despite the wider host-state pattern -- measured at a lower
load, so read it as "not visibly worse" rather than as a speed-up.

That is what it costs to judge the host coupling by *outcome* in every class
rather than by spelling in one -- the defence review cycle 1 showed was the
only one that fired -- after review cycle 2, to judge it in a sandbox of
copies, so that a module reached across a boundary cannot answer for the
real tree, and after review cycle 3, to ask both guards about the whole
guarded tree rather than one of them about one module.

``meta/profiling/rank_durations.py`` is loaded by path rather than imported:
``meta/`` is not a package and is not on ``sys.path``, and putting it there
would make the repo's structural import guard's job harder for no gain.
"""

from __future__ import annotations

import ast
import collections
import glob
import hashlib
import importlib.util
import json
import os
import pathlib
import random
import re
import subprocess
import sys
import textwrap
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from types import ModuleType
from typing import NamedTuple

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PROFILING_DIR = REPO_ROOT / "meta" / "profiling"
RANKER_PATH = PROFILING_DIR / "rank_durations.py"


def _load_ranker() -> ModuleType:
    name = "card217_rank_durations"
    spec = importlib.util.spec_from_file_location(name, RANKER_PATH)
    assert spec is not None and spec.loader is not None, RANKER_PATH
    module = importlib.util.module_from_spec(spec)
    # Registered before exec: @dataclass resolves annotations through
    # sys.modules[cls.__module__], and raises AttributeError on None if the
    # module is not there yet.
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ranker = _load_ranker()


def _artefacts() -> list[Path]:
    """Every committed profile, oldest first by its ``YYYYMMDD`` name."""
    return sorted(PROFILING_DIR.glob("suite-durations-*.txt"))


def _hotspots_for(artefact: Path) -> Path:
    """The analysis document that pairs with an artefact, by naming rule."""
    date = artefact.stem.removeprefix("suite-durations-")
    return artefact.parent / f"suite-hotspots-{date}.md"


@pytest.fixture(scope="module")
def artefact_path() -> Path:
    found = _artefacts()
    assert found, f"no suite-durations-*.txt under {PROFILING_DIR}"
    return found[-1]


@pytest.fixture(scope="module")
def artefact_text(artefact_path: Path) -> str:
    return artefact_path.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def profile(artefact_text: str):
    return ranker.parse_artefact(artefact_text)


# A minimal well-formed artefact, used where a test needs to control the
# numbers rather than depend on the real run's.
SYNTHETIC_ARTEFACT = """\
# CARD-217 suite duration profile
# commit: 0123456789abcdef0123456789abcdef01234567
# host: Test Host
# python: 3.14.3
# command: pytest --durations=0 --durations-min=0 -q
# wall clock: 100.00s
# result: 2 passed, 0 skipped, 0 failed
# solo run: yes

============================= slowest durations =============================
10.00s call     tests/test_a.py::test_slow
1.00s setup    tests/test_a.py::test_slow
0.50s call     tests/test_b.py::test_quick
0.00s teardown tests/test_b.py::test_quick
2 passed, 0 skipped in 100.00s (0:01:40)
"""


class TestSuiteProfile_ArtefactExistsAndIsComplete:
    """AC-1: the artefact exists, states its conditions, and holds the table."""

    def test_at_least_one_artefact_is_committed(self) -> None:
        assert _artefacts(), f"no suite-durations-*.txt under {PROFILING_DIR}"

    @pytest.mark.parametrize(
        "path", _artefacts(), ids=lambda p: p.name if hasattr(p, "name") else str(p)
    )
    def test_every_committed_artefact_is_well_formed(self, path: Path) -> None:
        # Deliberately *not* "exactly one artefact". CARD-218/219/220/235/236
        # are each instructed to re-profile to measure their own saving, so a
        # second, third and fourth profile are the expected end state -- which
        # is why the files are dated. What has to hold of each of them is that
        # it is complete and honest, not that it is alone.
        text = path.read_text(encoding="utf-8")
        assert ranker.missing_header_fields(text) == [], path.name
        assert ranker.is_admissible_profile(text), path.name
        assert len(ranker.parse_artefact(text).tests) > 6000, path.name

    @pytest.mark.parametrize(
        "path", _artefacts(), ids=lambda p: p.name if hasattr(p, "name") else str(p)
    )
    def test_every_artefact_has_a_hotspots_document(self, path: Path) -> None:
        assert _hotspots_for(path).exists(), (
            f"{path.name} has no matching {_hotspots_for(path).name}; the "
            "naming convention pairs a profile with its analysis by date"
        )

    @pytest.mark.parametrize(
        "path", _artefacts(), ids=lambda p: p.name if hasattr(p, "name") else str(p)
    )
    def test_every_hotspots_document_cites_its_own_artefact(
        self, path: Path
    ) -> None:
        # The real risk a multi-profile future introduces is not duplication,
        # it is a hotspots document quietly describing a superseded run. Every
        # document is checked, not just the newest: the moment CARD-218
        # commits a second profile, a stale citation on the *older* pair would
        # otherwise go unnoticed forever.
        artefact_path = path
        digest = hashlib.sha256(artefact_path.read_bytes()).hexdigest()
        document = _hotspots_for(artefact_path).read_text(encoding="utf-8")
        assert digest in document, (
            f"{_hotspots_for(artefact_path).name} does not cite the sha256 of "
            f"{artefact_path.name} ({digest[:16]}...); it was derived from a "
            "different artefact"
        )

    @pytest.mark.parametrize(
        "path", _artefacts(), ids=lambda p: p.name if hasattr(p, "name") else str(p)
    )
    def test_hotspots_ranking_rows_are_the_scripts_own_output(
        self, path: Path
    ) -> None:
        # The sha256 citation pins *which* artefact a document derives from.
        # It says nothing about *what the document claims* about it, and those
        # are different guarantees: a falsified ranking row, or a denominator
        # nudged by 1 %, leaves the citation perfectly valid. Four cards steer
        # on the second guarantee, so it gets its own test.
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        profile = ranker.parse_artefact(path.read_text(encoding="utf-8"))
        generated = ranker.report(profile, path, digest)
        document = _hotspots_for(path).read_text(encoding="utf-8")
        row = re.compile(r"^\s*\d+\s+\d+\.\d+s")
        assert [line for line in document.splitlines() if row.match(line)] == [
            line for line in generated.splitlines() if row.match(line)
        ]

    @pytest.mark.parametrize(
        "path", _artefacts(), ids=lambda p: p.name if hasattr(p, "name") else str(p)
    )
    def test_hotspots_headline_figures_are_the_scripts_own_output(
        self, path: Path
    ) -> None:
        # The ranking rows above are tabular; the conclusion is prose, and the
        # prose is what the follow-on cards actually read. Every figure in the
        # deciding table must appear in the document on a single line, so that
        # editing "366.19 s / 39.78 %" down to "166.19 s / 19.78 %" cannot
        # pass -- which it did before this test existed.
        profile = ranker.parse_artefact(path.read_text(encoding="utf-8"))
        document = _hotspots_for(path).read_text(encoding="utf-8")
        rows = [
            line for line in document.splitlines() if line.lstrip().startswith("|")
        ]
        wrong = []

        # (a) Every seconds/share pair stated in a table must be internally
        # consistent with the attributed denominator. This catches a
        # falsified figure without having to know which figure it was: both
        # columns would have to be forged in agreement to survive, and
        # forging them in agreement means stating the truth.
        for line in rows:
            secs = re.findall(r"(\d+\.\d{2}) s\b", line)
            share = re.findall(r"(\d+\.\d{2}) %", line)
            if len(secs) != 1 or len(share) != 1:
                continue  # not a "time + share" row; nothing to cross-check
            expected = 100.0 * float(secs[0]) / profile.attributed
            if abs(expected - float(share[0])) > 0.01:
                wrong.append(
                    f"{secs[0]} s is {expected:.2f} % of attributed time, "
                    f"row claims {share[0]} %: {line.strip()}"
                )

        # (b) …and each cost family must actually be stated somewhere, so a
        # row cannot simply be deleted to dodge (a).
        for name, seconds, _count in ranker.group_totals(profile):
            pair = (
                f"{seconds:.2f} s",
                f"{100.0 * seconds / profile.attributed:.2f} %",
            )
            if not any(pair[0] in line and pair[1] in line for line in rows):
                wrong.append(f"{name}: no table row states {pair[0]} / {pair[1]}")

        assert wrong == [], wrong

    @pytest.mark.parametrize(
        "path", _artefacts(), ids=lambda p: p.name if hasattr(p, "name") else str(p)
    )
    def test_hotspots_embeds_the_deciding_table_verbatim(self, path: Path) -> None:
        # Belt to the prose check's braces: the script's own deciding-table
        # block is quoted in the document byte for byte, so the authoritative
        # figures are present in a form that cannot be edited into agreement
        # with a falsified prose table.
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        profile = ranker.parse_artefact(path.read_text(encoding="utf-8"))
        generated = ranker.report(profile, path, digest)
        block = generated.partition("## Cost families")[2].partition("\n## ")[0]
        assert block.strip(), "the report no longer has a cost-families block"
        document = _hotspots_for(path).read_text(encoding="utf-8")
        assert block.strip() in document

    def test_artefact_is_named_for_its_date(self, artefact_path: Path) -> None:
        stem = artefact_path.stem
        date = stem.removeprefix("suite-durations-")
        assert len(date) == 8 and date.isdigit(), (
            f"expected suite-durations-YYYYMMDD.txt, got {artefact_path.name}"
        )

    def test_header_states_every_required_field(self, artefact_text: str) -> None:
        assert ranker.missing_header_fields(artefact_text) == []

    @pytest.mark.parametrize("field", ranker.REQUIRED_HEADER_FIELDS)
    def test_each_required_field_is_individually_present(
        self, artefact_text: str, field: str
    ) -> None:
        fields = ranker.parse_header(artefact_text)
        assert field in fields and fields[field].strip()

    def test_header_records_a_passing_run(self, artefact_text: str) -> None:
        result = ranker.parse_header(artefact_text)["result"]
        assert "0 failed" in result, (
            f"the profile must come from a passing run, header says: {result}"
        )

    def test_body_is_the_durations_table(self, profile) -> None:
        assert len(profile.tests) > 6000, (
            "the artefact should carry a timing for essentially every test in "
            f"the suite, found {len(profile.tests)}"
        )
        # Three rows per test, bar the handful skipped at setup. Catches a
        # truncated artefact, which would otherwise rank perfectly happily.
        assert 2.9 < profile.records / len(profile.tests) <= 3.0

    def test_every_test_carries_setup_call_and_teardown(self, profile) -> None:
        # --durations reports the three phases separately, and the hotspots
        # document leans on the distinction (a setup-dominated test is a
        # fixture problem, a call-dominated one is a test problem). The only
        # legitimate exception is a test skipped during setup, which never
        # reaches a call phase.
        shapes = collections.Counter(
            tuple(sorted(record.phases)) for record in profile.tests.values()
        )
        assert set(shapes) <= {
            ("call", "setup", "teardown"),
            ("setup", "teardown"),
        }, dict(shapes)
        assert shapes[("call", "setup", "teardown")] > 6000
        # Tests skipped at setup are a handful, not a silent mass skip.
        assert shapes[("setup", "teardown")] < 50

    def test_counts_are_recovered_despite_the_missing_summary_line(
        self, profile
    ) -> None:
        # pyproject's addopts already carries -q, so the card's -q makes it
        # -qq and pytest prints no summary. The header has to carry the
        # counts instead, and they must agree with the table.
        assert profile.passed is not None and profile.skipped is not None
        assert profile.passed + profile.skipped == len(profile.tests)

    def test_attributed_time_accounts_for_nearly_all_of_the_wall_clock(
        self, profile
    ) -> None:
        assert profile.wall_clock is not None
        assert profile.attributed <= profile.wall_clock + 1.0
        # If a large slice were unattributed the per-file shares would be
        # measuring the wrong denominator.
        assert profile.attributed >= 0.90 * profile.wall_clock

    def test_parser_rejects_a_file_with_no_duration_lines(self) -> None:
        assert ranker.parse_artefact("# header only\nnothing here\n").tests == {}

    def test_bodys_own_summary_wins_over_the_header(self) -> None:
        # The synthetic artefact carries both; pytest's own line is the
        # measurement and the header is only a transcription of it.
        both = SYNTHETIC_ARTEFACT.replace("# wall clock: 100.00s", "# wall clock: 999s")
        assert ranker.parse_artefact(both).wall_clock == 100.00

    def test_header_is_used_when_the_body_has_no_summary(self) -> None:
        without = "\n".join(
            line
            for line in SYNTHETIC_ARTEFACT.splitlines()
            if " passed, " not in line or line.startswith("#")
        )
        parsed = ranker.parse_artefact(without)
        assert parsed.wall_clock == 100.00
        assert (parsed.passed, parsed.skipped) == (2, 0)


class TestSuiteProfile_RankingIsDeterministic:
    """AC-2: the derivation is reproducible and nobody hand-counts it."""

    def test_rerunning_the_script_is_byte_identical(
        self, artefact_path: Path
    ) -> None:
        runs = [
            subprocess.run(
                [sys.executable, str(RANKER_PATH), str(artefact_path)],
                capture_output=True,
                check=True,
            ).stdout
            for _ in range(2)
        ]
        assert runs[0] == runs[1]
        assert runs[0], "the script produced no output"

    def test_report_lists_fifty_tests_and_twenty_files(
        self, profile, artefact_path: Path
    ) -> None:
        # The card asks for 50 and 20 by name, so these are asserted as
        # literals. Comparing against ranker.TOP_TESTS would be tautological:
        # it would pass just as happily if the constants were changed.
        assert (ranker.TOP_TESTS, ranker.TOP_FILES) == (50, 20)
        text = ranker.report(profile, artefact_path, "deadbeef")
        tests_block, _, rest = text.partition("## 20 slowest files")
        tests_rows = [
            line
            for line in tests_block.splitlines()
            if re.match(r"^\s*\d+\s+\d+\.\d+s", line)
        ]
        files_rows = [
            line
            for line in rest.partition("## Render-heavy")[0].splitlines()
            if re.match(r"^\s*\d+\s+\d+\.\d+s", line)
        ]
        assert len(tests_rows) == 50
        assert len(files_rows) == 20

    def test_report_text_carries_the_three_rankings(
        self, profile, artefact_path: Path
    ) -> None:
        text = ranker.report(profile, artefact_path, "deadbeef")
        assert f"## {ranker.TOP_TESTS} slowest tests" in text
        assert f"## {ranker.TOP_FILES} slowest files" in text
        assert "## Render-heavy files" in text
        slowest = ranker.rank_tests(profile)[0]
        assert slowest.nodeid in text
        # Every one of the fifty rows is actually printed, not just the header.
        for record in ranker.rank_tests(profile)[: ranker.TOP_TESTS]:
            assert record.nodeid in text

    def test_tests_are_ranked_by_descending_total(self, profile) -> None:
        totals = [record.total for record in ranker.rank_tests(profile)]
        assert totals == sorted(totals, reverse=True)

    def test_files_are_ranked_by_descending_total(self, profile) -> None:
        seconds = [row[1] for row in ranker.rank_files(profile)]
        assert seconds == sorted(seconds, reverse=True)

    def test_equal_durations_break_ties_on_id_not_on_dict_order(self) -> None:
        # Without an explicit tie-break, two tests of identical duration could
        # swap places between runs and the committed document would drift.
        artefact = "\n".join(
            f"1.00s call     tests/test_t.py::test_{name}"
            for name in ("zulu", "alpha", "mike")
        )
        order = [r.nodeid for r in ranker.rank_tests(ranker.parse_artefact(artefact))]
        assert order == [
            "tests/test_t.py::test_alpha",
            "tests/test_t.py::test_mike",
            "tests/test_t.py::test_zulu",
        ]

    def test_equal_file_totals_break_ties_on_path_not_on_dict_order(self) -> None:
        # rank_files carries the same tie-break as rank_tests and, unlike it,
        # nothing pinned it. Not a live hole today -- sorted() is stable over
        # an insertion order that is itself a pure function of the artefact --
        # but an untested asymmetry between two functions that must behave
        # the same way is how determinism quietly stops being true.
        artefact = "\n".join(
            f"1.00s call     tests/test_{name}.py::test_one"
            for name in ("zulu", "alpha", "mike")
        )
        order = [row[0] for row in ranker.rank_files(ranker.parse_artefact(artefact))]
        assert order == [
            "tests/test_alpha.py",
            "tests/test_mike.py",
            "tests/test_zulu.py",
        ]

    def test_file_totals_sum_the_phases_of_their_tests(self) -> None:
        profile = ranker.parse_artefact(SYNTHETIC_ARTEFACT)
        by_file = dict((path, secs) for path, secs, _ in ranker.rank_files(profile))
        assert by_file["tests/test_a.py"] == pytest.approx(11.0)
        assert by_file["tests/test_b.py"] == pytest.approx(0.5)

    def test_file_rows_count_tests_not_phase_records(self) -> None:
        profile = ranker.parse_artefact(SYNTHETIC_ARTEFACT)
        counts = {path: n for path, _, n in ranker.rank_files(profile)}
        assert counts == {"tests/test_a.py": 1, "tests/test_b.py": 1}

    def test_the_frozen_render_set_still_matches_the_grep_that_defines_it(
        self,
    ) -> None:
        # RENDER_HEAVY_SNAPSHOT is the constant that decides the 21.23 %
        # figure, and CARD-218 and CARD-219 are sized against it. Frozen so
        # the committed ranking cannot shift under a changing tree -- but
        # frozen is only safe if drift is loud, so re-run the defining grep
        # and require agreement. If a render call site is added to a new test
        # file, this goes red and the snapshot (and the profile) are restated
        # deliberately rather than silently diverging.
        live = ranker.regrep_render_set(REPO_ROOT / "tests")
        assert live == list(ranker.RENDER_HEAVY_SNAPSHOT), {
            "added since freeze": sorted(
                set(live) - set(ranker.RENDER_HEAVY_SNAPSHOT)
            ),
            "gone since freeze": sorted(
                set(ranker.RENDER_HEAVY_SNAPSHOT) - set(live)
            ),
        }

    def test_the_frozen_render_set_is_sorted_and_duplicate_free(self) -> None:
        snapshot = list(ranker.RENDER_HEAVY_SNAPSHOT)
        assert snapshot == sorted(set(snapshot))

    def test_render_share_counts_only_the_frozen_set(self) -> None:
        artefact = (
            "5.00s call     tests/test_book_pdf.py::test_render\n"
            "5.00s call     tests/test_solver.py::test_logic\n"
        )
        profile = ranker.parse_artefact(artefact)
        seconds, files, tests = ranker.render_heavy_total(profile)
        assert (seconds, files, tests) == (5.0, 1, 1)

    def test_parametrised_ids_containing_spaces_survive_parsing(self) -> None:
        artefact = "0.25s call     tests/test_x.py::test_y[a b-c d]\n"
        profile = ranker.parse_artefact(artefact)
        assert list(profile.tests) == ["tests/test_x.py::test_y[a b-c d]"]

    def test_phase_totals_add_up_to_attributed_time(self, profile) -> None:
        totals = ranker.phase_totals(profile)
        assert sum(totals.values()) == pytest.approx(profile.attributed, rel=1e-9)


class TestSuiteProfile_RefusesToRecordAContendedRun:
    """AC-4: a run that shared the host is not recorded as the profile."""

    PS_WITH_COMPETITOR = """\
  PID COMMAND
  101 /usr/sbin/syslogd
  202 /path/.venv/bin/python -m pytest --durations=0 -q
  303 /Applications/Google Chrome.app/Contents/MacOS/Google Chrome
"""
    PS_QUIET = """\
  PID COMMAND
  101 /usr/sbin/syslogd
  303 /Applications/Google Chrome.app/Contents/MacOS/Google Chrome
"""

    def test_detects_a_competing_suite(self) -> None:
        found = ranker.other_pytest_processes(self.PS_WITH_COMPETITOR)
        assert len(found) == 1 and "202" in found[0]

    def test_quiet_host_reports_nothing(self) -> None:
        assert ranker.other_pytest_processes(self.PS_QUIET) == []

    def test_own_process_is_not_mistaken_for_a_competitor(self) -> None:
        assert ranker.other_pytest_processes(self.PS_WITH_COMPETITOR, own_pid=202) == []

    def test_the_grep_that_produced_the_listing_is_ignored(self) -> None:
        listing = "  404 grep -E pytest\n"
        assert ranker.other_pytest_processes(listing) == []

    @pytest.mark.parametrize(
        "command",
        [
            "/usr/bin/pytest -q",
            "/opt/x/bin/python3.14 -m pytest tests/",
            "python -m pytest",
            "/path/.venv/bin/pytest --durations=0",
        ],
    )
    def test_invocation_forms_are_all_detected(self, command: str) -> None:
        assert ranker.other_pytest_processes(f"  999 {command}\n")

    @pytest.mark.parametrize(
        "command",
        [
            "/usr/bin/vim meta/profiling/rank_durations.py",
            "/Applications/PyCharm.app/Contents/MacOS/pycharm",
            "tail -f pytest-output.log",
        ],
    )
    def test_bystanders_are_not_detected(self, command: str) -> None:
        assert ranker.other_pytest_processes(f"  999 {command}\n") == []

    def test_a_contended_artefact_is_not_admissible(self) -> None:
        contended = SYNTHETIC_ARTEFACT.replace("solo run: yes", "solo run: no")
        assert ranker.is_admissible_profile(contended) is False

    def test_an_artefact_missing_the_solo_field_is_not_admissible(self) -> None:
        without = SYNTHETIC_ARTEFACT.replace("# solo run: yes\n", "")
        assert "solo run" in ranker.missing_header_fields(without)
        assert ranker.is_admissible_profile(without) is False

    @pytest.mark.parametrize("field", ranker.REQUIRED_HEADER_FIELDS)
    def test_dropping_any_required_field_makes_it_inadmissible(
        self, field: str
    ) -> None:
        without = "\n".join(
            line
            for line in SYNTHETIC_ARTEFACT.splitlines()
            if not line.startswith(f"# {field}:")
        )
        assert ranker.missing_header_fields(without) == [field]
        assert ranker.is_admissible_profile(without) is False

    def test_the_synthetic_control_is_admissible(self) -> None:
        assert ranker.is_admissible_profile(SYNTHETIC_ARTEFACT) is True

    def test_the_committed_artefact_is_admissible(self, artefact_text: str) -> None:
        assert ranker.is_admissible_profile(artefact_text) is True

    def test_a_comment_below_the_table_cannot_supply_a_header_field(self) -> None:
        # The field is absent from the header and appears only after the
        # duration table. Header parsing stops at the table, so it must not
        # count -- otherwise a note at the foot of a contended artefact could
        # declare the run solo.
        sneaky = (
            "\n".join(
                line
                for line in SYNTHETIC_ARTEFACT.splitlines()
                if not line.startswith("# solo run:")
            )
            + "\n# solo run: yes\n"
        )
        assert "solo run" in ranker.missing_header_fields(sneaky)
        assert ranker.is_admissible_profile(sneaky) is False


# --------------------------------------------------------------------------
# CARD-238 -- a seeded corpus and an independent reading of the line format
#
# The format contract used to be checked against the live, gitignored
# ``meta/kanban/suite-timing.log``, which made its verdict a fact about the
# host. The corpus below replaces that breadth with breadth the test owns: a
# seeded sweep of well-formed entries, every one of them mutated nine ways
# into a line that must be refused, cross-checked against a second
# implementation of the format written from its documented shape rather than
# from ``TIMING_LOG_LINE``. No ``hypothesis`` (not in the dependency
# baseline, ADR-0006/R1) -- a ``random.Random`` with a fixed seed, with the
# case count asserted in the test so the corpus cannot silently shrink.
# --------------------------------------------------------------------------

_NOTE_WORDS = (
    "passed",
    "skipped",
    "failed",
    "pre-existing",
    "excluded",
    "duration",
    "not",
    "recorded",
    "solo",
    "gate",
)
_LABELS = ("full-suite", "card-204-merge-gate", "card-217-profiling-run", "wave-smoke")


def _seeded_entries(seed: int = 238, count: int = 160) -> list[str]:
    """``count`` distinct well-formed entries, built from parts, not parsed."""
    rng = random.Random(seed)
    lines: list[str] = []
    seen: set[str] = set()
    while len(lines) < count:
        stamp = (
            f"{rng.randint(2024, 2031)}-{rng.randint(1, 12):02d}-"
            f"{rng.randint(1, 28):02d}T{rng.randint(0, 23):02d}:"
            f"{rng.randint(0, 59):02d}:{rng.randint(0, 59):02d}Z"
        )
        wave = f"wave-{rng.randint(1, 400)}"
        label = rng.choice(_LABELS)
        duration = "---" if rng.random() < 0.15 else f"{rng.randint(1, 99999)}s"
        status = rng.choice(("PASS", "FAIL"))
        # Notes deliberately exclude parentheses and brackets: the real log
        # has none inside a note, and the mutations below depend on the
        # wrapper being the only one.
        notes = " ".join(rng.sample(_NOTE_WORDS, rng.randint(1, 5)))
        if rng.random() < 0.3:
            notes = f"{rng.randint(1, 9999)} passed — {notes}"
        line = f"{stamp} {wave} {label} {duration} {status} ({notes})"
        if rng.random() < 0.5:
            line = f"{line} [{rng.randint(1, 999)}ms/test]"
        # A parenthesised note *after* the rate bracket: the shape log lines
        # 19 and 24 use, which the corpus did not reach before review cycle
        # 1 (F-004) -- so the two implementations agreed on it only by both
        # ignoring the fields.
        if rng.random() < 0.25:
            aside = " ".join(rng.sample(_NOTE_WORDS, rng.randint(1, 4)))
            line = f"{line} ({aside})"
        if line not in seen:
            seen.add(line)
            lines.append(line)
    return lines


def _unlabel(line: str) -> str:
    """Put a space inside the label, which must then be two fields too many."""
    for label in _LABELS:
        if f" {label} " in line:
            return line.replace(f" {label} ", f" {label.replace('-', ' ')} ", 1)
    raise AssertionError(line)  # every generated entry carries one of _LABELS


# Each mutation turns a well-formed entry into one the format must refuse.
# The last is the shape CARD-217's merge gate actually wrote (AC-4).
MUTATIONS: tuple[tuple[str, Callable[[str], str]], ...] = (
    (
        "space instead of T and Z",
        lambda line: line.replace("T", " ", 1).replace("Z", "", 1),
    ),
    ("wave abbreviated", lambda line: line.replace("wave-", "w", 1)),
    (
        "duration without its s",
        lambda line: re.sub(r" (\d+)s ", r" \1 ", line, count=1),
    ),
    (
        "status lowercased",
        lambda line: line.replace("PASS", "pass").replace("FAIL", "fail"),
    ),
    (
        "notes unparenthesised",
        lambda line: line.replace("(", "", 1).replace(")", "", 1),
    ),
    ("label split in two", _unlabel),
    ("leading indent", lambda line: f"  {line}"),
    ("commented out", lambda line: f"# {line}"),
    ("trailing prose after the rate", lambda line: f"{line} — the card's own gate"),
    # A trailing note that is opened and never closed is not the legal shape
    # either: the parenthesis has to pair, or `notes` and `extra` are again
    # whatever the regex happens to swallow.
    ("trailing note left unclosed", lambda line: f"{line} (a note that never ends"),
)


def _mutants(entries: list[str]) -> list[tuple[str, str]]:
    """``(mutation name, line)`` for every entry put through every mutation.

    A mutation that leaves an entry untouched -- dropping the ``s`` from a
    ``---`` duration, say -- contributes nothing and is left out, so no case
    in the corpus is secretly a well-formed line.
    """
    out: list[tuple[str, str]] = []
    for line in entries:
        for name, mutate in MUTATIONS:
            mutated = mutate(line)
            if mutated != line:
                out.append((name, mutated))
    return out


_GOOD_ENTRIES = _seeded_entries()
MUTANT_CASES: list[tuple[str, str]] = _mutants(_GOOD_ENTRIES)
CORPUS: tuple[list[str], list[str]] = (
    _GOOD_ENTRIES,
    [line for _, line in MUTANT_CASES],
)


def _looks_like_an_entry(line: str) -> bool:
    """Decide the line format by hand -- the independent second reading.

    Written from the shape documented in ``rank_durations.py``'s header
    comment and in ``tests/README.md``, using ``str`` methods and
    ``datetime.strptime`` rather than ``TIMING_LOG_LINE``, so that the two
    implementations can be played off each other instead of the regex
    confirming itself:

        <ISO ts> wave-<N> <label> <seconds>s|--- <PASS|FAIL> (<notes>)
        optionally followed by a single ` [<N>ms/test]` and nothing else.

    That grammar understates what this actually accepts, and CARD-239's
    claim sweep measured the difference rather than leaving the sentence
    standing: the note's span is taken to the LAST ``)`` in the line, so a
    parenthesised note *after* the rate bracket -- the shape review cycle 1
    established is legal and in use -- is swallowed into the note and
    accepted. The two implementations therefore agree on it, by two
    different routes, which is what
    ``test_the_parser_agrees_with_an_independent_validator`` measures over
    the whole corpus. A *bare* trailing note is still rejected here, because
    the text after the last ``)`` must be empty or exactly one rate bracket.

    One deliberate difference: ``strptime`` also rejects an impossible date
    (``2026-13-45T99:99:99Z``), which ``TIMING_LOG_LINE``'s two-digit
    groups accept. No case in the corpus below exercises that, because no writer
    produces such a stamp -- and tightening the parser is out of scope here
    (CARD-238 G-3 permits a parser change only for AC-4's shape, and that
    ruling was "reject"). A future corpus that reaches for it should expect
    this function to be the stricter of the two.
    """
    if not line.strip() or line.lstrip().startswith("#"):
        return False
    opened = line.find("(")
    closed = line.rfind(")")
    if opened < 0 or closed < opened:
        return False
    head, tail = line[:opened], line[closed + 1 :]
    if not head.endswith(" "):
        return False
    fields = head[:-1].split(" ")
    if len(fields) != 5:
        return False
    if any(not field or any(ch.isspace() for ch in field) for field in fields):
        return False
    stamp, wave, _label, duration, status = fields
    try:
        datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return False
    if not wave.startswith("wave-") or not wave[len("wave-") :].isdigit():
        return False
    if duration != "---" and not (
        duration.endswith("s") and duration[:-1].isdigit() and len(duration) > 1
    ):
        return False
    if status not in {"PASS", "FAIL"}:
        return False
    if tail == "":
        return True
    if not (tail.startswith(" [") and tail.endswith("ms/test]")):
        return False
    return tail[len(" [") : -len("ms/test]")].isdigit()


class TestSuiteTimingLog_FormatUnchanged:
    """AC-5: the append keeps the format the whole log is read in."""

    GOOD = [
        "2026-10-06T17:20:55Z wave-35 full-suite 770s PASS (6618 passed, 9 skipped, 0 failed)",
        "2026-10-15T06:30:00Z wave-38 card-221-merge-gate 939s PASS (7073 passed) [133ms/test]",
        "2026-10-14T05:20:00Z wave-37 card-214-merge-gate --- PASS (duration not recorded)",
        "2026-09-22T16:27:26Z wave-20 full-suite 125s FAIL (1 pre-existing failure)",
    ]
    BAD = [
        "2026-10-06 17:20:55 wave-35 full-suite 770s PASS (ok)",  # no ISO T/Z
        "2026-10-06T17:20:55Z w35 full-suite 770s PASS (ok)",  # wave malformed
        "2026-10-06T17:20:55Z wave-35 full-suite 770 PASS (ok)",  # no 's'
        "2026-10-06T17:20:55Z wave-35 full-suite 770s OK (ok)",  # not PASS/FAIL
        "2026-10-06T17:20:55Z wave-35 full-suite 770s PASS no parens",
    ]

    @pytest.mark.parametrize("line", GOOD)
    def test_known_good_lines_parse(self, line: str) -> None:
        assert ranker.parse_timing_line(line) is not None

    @pytest.mark.parametrize("line", BAD)
    def test_known_bad_lines_are_rejected(self, line: str) -> None:
        assert ranker.parse_timing_line(line) is None

    def test_fields_are_extracted_not_merely_matched(self) -> None:
        entry = ranker.parse_timing_line(self.GOOD[1])
        assert entry is not None
        assert entry["wave"] == "wave-38"
        assert entry["label"] == "card-221-merge-gate"
        assert entry["duration"] == "939s"
        assert entry["status"] == "PASS"
        assert entry["rate"] == "133ms/test"

    @pytest.mark.parametrize("line", ["", "   ", "# a comment", "  # indented"])
    def test_blanks_and_comments_are_not_entries(self, line: str) -> None:
        assert ranker.parse_timing_line(line) is None

    @pytest.mark.parametrize("prefix", ["# ", "#", "  # ", "## "])
    def test_a_commented_out_entry_is_not_read_back_as_an_entry(
        self, prefix: str
    ) -> None:
        # The log's own header comments quote past runs, and a superseded
        # entry gets commented out rather than deleted. If those parsed, the
        # "last entry" would silently become a historical quotation.
        assert ranker.parse_timing_line(prefix + self.GOOD[0]) is None

    def test_a_commented_out_entry_is_not_counted_in_the_log(self) -> None:
        text = f"{self.GOOD[0]}\n# {self.GOOD[1]}\n"
        entries = ranker.timing_log_entries(text)
        assert len(entries) == 1
        assert entries[0]["wave"] == "wave-35"

    def test_malformed_detector_finds_the_bad_line_among_good_ones(self) -> None:
        text = "\n".join([*self.GOOD, self.BAD[0], "# trailing note"])
        assert ranker.malformed_timing_lines(text) == [self.BAD[0]]

    # ------------------------------------------------------------------
    # CARD-238 replaced two tests here that read the live
    # ``meta/kanban/suite-timing.log``. Both assertions are kept; both are
    # now made against logs the test constructs. See the class comment at
    # the foot of this module for what each one became.
    # ------------------------------------------------------------------

    # Every shape the owner's log actually used as of 2026-10-15, transcribed
    # by hand: a plain wave run, a note carrying an em dash, an unrecorded
    # duration, a line-final rate bracket, and -- twice -- a rate bracket
    # followed by a *parenthesised* second note, plus the header/GAP/NOTE
    # comment lines. This is what "the real log is entirely well formed"
    # asserted, over text that cannot change under the suite's feet.
    #
    # Corrected at review cycle 1 (F-002): the wave-39 profiling-run entry
    # here is log line 24, and its transcription had dropped the
    # parenthesised note it carries. That omission is what made the ruling
    # below say "the ONE entry" when there are two. Its prose is abbreviated
    # from the review's quotation of the line rather than re-read off the
    # file, because this card does not read the live log (G-1); the shape --
    # bracket, space, parenthesised note -- is what the parser is held to,
    # and that is faithful. The card-221 gate line was added in the same
    # pass so a line-final rate bracket is still represented here.
    REAL_SHAPES = (
        "# GAP: waves 36 and 37 have no wave-smoke-test line. The per-card\n"
        "# gates below are labelled as gates and not as wave runs.\n"
        "2026-09-22T16:27:26Z wave-20 full-suite 125s PASS "
        "(1 pre-existing failure excluded)\n"
        "2026-10-04T09:53:23Z wave-32 full-suite 587s PASS "
        "(6083 passed, 0 failed — first wave with a clean suite since wave 20)\n"
        "2026-10-14T05:20:00Z wave-37 card-214-merge-gate --- PASS "
        "(6883 passed, 9 skipped, 0 failed; duration not recorded)\n"
        "2026-10-14T19:20:17Z wave-38 card-212-merge-gate 1123s PASS "
        "(7053 passed, 9 skipped, 0 failed) [159ms/test] "
        "(a first attempt on a shared host failed at 1476s)\n"
        "2026-10-15T06:30:00Z wave-38 card-221-merge-gate 939s PASS "
        "(7073 passed) [133ms/test]\n"
        "2026-10-15T05:34:34Z wave-39 card-217-profiling-run 931s PASS "
        "(7073 passed, 9 skipped, 0 failed) [131ms/test] "
        "(solo profiling run, --durations=0; artefact under meta/profiling)\n"
        "# NOTE 2026-10-15: the two figures above ran on a quiet host.\n"
    )

    # The one line in the owner's log that its own format validator refuses,
    # written at CARD-217's merge gate. Kept verbatim; see
    # test_the_trailing_prose_shape_is_not_legal for the ruling and the
    # writer that produced it.
    CARD_217_GATE_LINE = (
        "2026-10-15T06:49:21Z wave-39 card-217-merge-gate 963s PASS "
        "(7156 passed, 9 skipped, 0 failed) [135ms/test] — the profiling "
        "card's own gate; +83 tests, all of them over the profile artefacts"
    )

    def test_every_shape_the_real_log_uses_is_well_formed(self) -> None:
        assert ranker.malformed_timing_lines(self.REAL_SHAPES) == []
        entries = ranker.timing_log_entries(self.REAL_SHAPES)
        # Field level, not merely "nothing was rejected". Review cycle 1,
        # F-004: this test was green over two entries whose `rate` the greedy
        # `notes` group had swallowed, under a name promising well-formedness.
        # "Well formed" now means the fields come back.
        assert [
            (
                entry["wave"],
                entry["label"],
                entry["duration"],
                entry["status"],
                entry["rate"],
            )
            for entry in entries
        ] == [
            ("wave-20", "full-suite", "125s", "PASS", ""),
            ("wave-32", "full-suite", "587s", "PASS", ""),
            ("wave-37", "card-214-merge-gate", "---", "PASS", ""),
            ("wave-38", "card-212-merge-gate", "1123s", "PASS", "159ms/test"),
            ("wave-38", "card-221-merge-gate", "939s", "PASS", "133ms/test"),
            ("wave-39", "card-217-profiling-run", "931s", "PASS", "131ms/test"),
        ]
        # The bracket is never swallowed into the prose fields either way.
        assert all("ms/test" not in entry["notes"] for entry in entries), entries
        assert all("ms/test" not in entry["extra"] for entry in entries), entries

    def test_the_real_logs_post_bracket_note_keeps_its_rate(self) -> None:
        # AC-4's second half, and the one the ruling got wrong (review
        # cycle 1, F-002). This is log line 19 -- the wave-38 card-212 merge
        # gate -- as this card's first cycle transcribed it and as review
        # cycle 1 quoted it back, not re-read off the file (G-1). The log
        # carries a second entry of the same shape (line 24, wave-39's
        # profiling run), so the shape is in use, which under AC-4 makes it
        # legal; and the parser must then keep the fields the cost trend is
        # read off, which until now it did not.
        line = (
            "2026-10-14T19:20:17Z wave-38 card-212-merge-gate 1123s PASS "
            "(7053 passed, 9 skipped, 0 failed) [159ms/test] "
            "(a first attempt on a shared host failed at 1476s)"
        )
        entry = ranker.parse_timing_line(line)
        assert entry is not None
        assert entry["rate"] == "159ms/test"
        assert entry["notes"] == "7053 passed, 9 skipped, 0 failed"
        assert entry["extra"] == "a first attempt on a shared host failed at 1476s"
        assert entry["duration"] == "1123s"

    def test_the_trailing_prose_shape_is_not_legal(self) -> None:
        # AC-4's ruling, half of it: a **bare** trailing note is not legal.
        # The format already has a slot for free prose -- the parentheses --
        # and every entry in the owner's log uses it, em dashes included
        # ("0 failed — first wave with a clean suite"). Not one entry puts
        # prose after the rate bracket without parentheses, so there is no
        # practice to codify and this line stays rejected.
        #
        # Two statements that stood here through review cycle 1 were false,
        # and are corrected rather than quietly dropped (F-002):
        #   * "the ONE entry that wanted a note after the rate bracket" --
        #     there are TWO, log lines 19 (wave-38 card-212-merge-gate) and
        #     24 (wave-39 card-217-profiling-run). Both are transcribed in
        #     REAL_SHAPES above.
        #   * "the rate bracket terminates the line" -- it does not, for two
        #     of the six rate-bearing entries. That claim was the load-bearing
        #     argument for leaving the parser alone, and it was contradicted
        #     by the data it claimed to summarise.
        #
        # The `notes`/`rate` ambiguity the old comment feared was not a
        # consequence of widening the regex: it was the status quo. The
        # greedy `notes` group swallowed the bracket on exactly those two
        # entries, so three of six rates were lost. The parenthesised shape
        # is legal (it is in use) and is now parsed with its fields intact --
        # see test_the_real_logs_post_bracket_note_keeps_its_rate and
        # rank_durations.py's line-contract comment. G-3 as amended at review
        # cycle 1 licenses that one parser change and no other.
        #
        # Writer, so the next author does not repeat it: the forge:kanban
        # dispatcher's merge-gate "SUITE TIMING" append step
        # (skills/kanban/references/cmd-run.md), which documents the line as
        # `<ISO date> wave-<N> <label> <seconds>s <PASS|FAIL>` and carries
        # neither the trailing-prose form nor the legal parenthesised one.
        # Put the gate's commentary inside parentheses.
        #
        # tests/README.md used to understate the format the same way and no
        # longer does (CARD-239): its "Logging the run" section now shows
        # the parenthesised post-bracket note as legal and this line as
        # rejected, with the writer named. `cmd-run.md` lives in the owner's
        # forge skills, outside this repository, so it is raised rather than
        # edited -- and it is the one the dispatcher actually reads at a
        # merge gate, so the drift that produced this line is still open
        # there.
        assert ranker.parse_timing_line(self.CARD_217_GATE_LINE) is None
        assert ranker.malformed_timing_lines(self.CARD_217_GATE_LINE + "\n") == [
            self.CARD_217_GATE_LINE
        ]

    def test_the_same_note_parenthesised_is_legal_and_keeps_its_fields(self) -> None:
        # The ruling above is about placement, not about content: the very
        # same sentence is accepted the log's own way, and -- since review
        # cycle 1's parser fix -- with every field intact. This test used to
        # assert `rate == ""` under this name, pinning a 50 % field loss as
        # correct for the one shape the ruling recommends as the remedy
        # (F-004). The name is the claim; the body now makes it.
        head, _, tail = self.CARD_217_GATE_LINE.partition(" — ")
        legal = f"{head} ({tail})"
        entry = ranker.parse_timing_line(legal)
        assert entry is not None
        assert entry["label"] == "card-217-merge-gate"
        assert entry["duration"] == "963s"
        assert entry["rate"] == "135ms/test"
        assert entry["notes"] == "7156 passed, 9 skipped, 0 failed"
        assert "the profiling card's own gate" in entry["extra"]

    def test_the_last_entry_is_the_last_uncommented_one(self) -> None:
        # What the deleted "the last entry is this card's profiling run"
        # test could actually check: that `timing_log_entries` reports file
        # order and that a commented-out or quoted entry below the last live
        # one does not become the tail. Whether a profiling run happens to
        # be last is a fact about the pipeline's workflow order, which no
        # code can keep true -- the dispatcher appends a gate line after
        # every card -- so that part is not asserted anywhere now.
        log = (
            f"{self.GOOD[0]}\n"
            "2026-10-15T05:34:34Z wave-39 card-217-profiling-run 931s PASS "
            "(7073 passed) [131ms/test]\n"
            f"# {self.GOOD[1]}\n"
            "# NOTE: the line above is a superseded entry, commented out.\n"
        )
        entries = ranker.timing_log_entries(log)
        assert [entry["wave"] for entry in entries] == ["wave-35", "wave-39"]
        last = entries[-1]
        assert last["label"] == "card-217-profiling-run"
        assert last["status"] == "PASS"
        assert last["duration"] == "931s"
        assert last["rate"] == "131ms/test"

    def test_a_profiling_run_is_recognisable_by_label_or_notes(self) -> None:
        # The other half of the deleted assertion: the *recognition* rule
        # ("profil" in the label or the notes) still works, and does not
        # match a gate line that merely mentions a card number.
        by_label = ranker.parse_timing_line(
            "2026-10-15T05:34:34Z wave-39 card-217-profiling-run 931s PASS (ok)"
        )
        by_notes = ranker.parse_timing_line(
            "2026-10-15T05:34:34Z wave-39 card-217-run 931s PASS (solo profiling run)"
        )
        gate = ranker.parse_timing_line(
            "2026-10-15T06:49:21Z wave-39 card-235-merge-gate 963s PASS (7156 passed)"
        )
        assert by_label is not None and by_notes is not None and gate is not None
        for entry in (by_label, by_notes):
            assert "profil" in entry["label"] or "profil" in entry["notes"]
        assert "profil" not in gate["label"] and "profil" not in gate["notes"]

    def test_the_seeded_corpus_is_large_enough_to_be_a_corpus(self) -> None:
        good, bad = CORPUS
        assert len(good) >= 150, len(good)
        assert len(bad) >= 1000, len(bad)
        assert len(set(good)) == len(good)  # no accidental duplicates
        assert len(MUTATIONS) >= 9, len(MUTATIONS)
        assert len(MUTANT_CASES) == len(bad)

    def test_every_seeded_entry_parses_and_yields_back_its_own_fields(self) -> None:
        good, _ = CORPUS
        rated_with_an_aside = 0
        for line in good:
            entry = ranker.parse_timing_line(line)
            assert entry is not None, line
            # The fields are checked against the shape the generator built,
            # not re-derived with the parser being tested.
            assert line.startswith(f"{entry['ts']} {entry['wave']} {entry['label']} ")
            assert f" {entry['duration']} {entry['status']} (" in line
            assert f"({entry['notes']})" in line, (line, entry)
            if entry["extra"]:
                assert line.endswith(f"({entry['extra']})"), (line, entry)
                if entry["rate"]:
                    rated_with_an_aside += 1
                    assert f"[{entry['rate']}] ({entry['extra']})" in line
            elif entry["rate"]:
                assert line.endswith(f"[{entry['rate']}]")
        # The post-bracket shape must actually be in the corpus, or the two
        # assertions above are vacuous for it (F-004).
        assert rated_with_an_aside >= 10, rated_with_an_aside

    def test_every_seeded_mutant_is_rejected(self) -> None:
        accepted = [
            (name, line)
            for name, line in MUTANT_CASES
            if ranker.parse_timing_line(line) is not None
        ]
        assert accepted == [], accepted[:5]

    def test_the_parser_agrees_with_an_independent_validator(self) -> None:
        # A second implementation of the line format, written by hand from
        # the documented shape rather than from TIMING_LOG_LINE (see
        # _looks_like_an_entry). Either implementation drifting from the
        # other fails here -- including on the CARD-217 gate line and on the
        # commented-out forms, which are in the corpus below.
        good, bad = CORPUS
        extras = [
            *self.GOOD,
            *self.BAD,
            self.CARD_217_GATE_LINE,
            f"# {self.GOOD[0]}",
            "   ",
            "",
        ]
        every = (*good, *bad, *extras)
        disagreed = [
            line
            for line in every
            if (ranker.parse_timing_line(line) is not None)
            != _looks_like_an_entry(line)
        ]
        assert len(every) >= 1150, len(every)
        assert disagreed == [], disagreed[:5]
        # A validator that always answered the same way would agree with
        # nothing; it has to split the corpus roughly as the generator built
        # it, or this cross-check proves nothing.
        verdicts = collections.Counter(_looks_like_an_entry(line) for line in every)
        assert verdicts[True] >= 150 and verdicts[False] >= 1000, verdicts


# --------------------------------------------------------------------------
# CARD-238 -- the suite's verdict may not depend on the live timing log
#
# ``meta/kanban/suite-timing.log`` is gitignored (``.gitignore``'s blanket
# ``*.log``), is appended to by the dispatcher at every merge gate, and is
# absent from a fresh worktree. A test that reads it reports a fact about the
# machine, not about the code: CARD-234's gate was green at 11 skips with the
# file absent while CARD-235's was red at 9 with it present -- the same suite,
# the same code, the same host. The two guards below keep that coupling out,
# structurally, so re-introducing it fails rather than merely re-introducing
# the confusion.
#
# The format contract itself is not host state and stays fully tested, against
# entries the tests construct -- see TestSuiteTimingLog_FormatUnchanged.
# --------------------------------------------------------------------------

# The live log's distinctive name component. Declared as a plain constant on
# purpose: a bare literal bound to a name is not a path and not a read, which
# is exactly the distinction the guard below draws.
LIVE_LOG_STEM = "suite-timing"


# A ``.log`` named under ``meta/kanban`` in one string, whatever its stem:
# the owner's log is the only one that lives there, so a glob or a sibling
# name is the same coupling by a different route.
_LOG_UNDER_KANBAN = re.compile(r"meta[/\\]kanban[/\\][^\s]*\.log")

# The four sets the rules below consult -- the listers, the globbers, the
# joiners and the path wrappers -- are no longer written here. They are
# derived from the audited classification table, immediately after
# :func:`_classified`, which is the earliest point at which they can be. The
# prose that used to stand here moved with them.


# --------------------------------------------------------------------------
# The audit of the sets above and of :data:`_HOST_STATE_PROBES` below.
# --------------------------------------------------------------------------
# Review cycles 1-4 each added a member to one of those sets, and each left
# a set whose completeness nothing could test -- so the fifth missing member
# (``os.walk``, stdlib's most-written directory enumerator, missed by the
# path guard and by the silence probe at once) was inevitable rather than
# unlucky. A hand-written enumeration cannot be audited by a sentence saying
# it is complete; it can only be audited against something outside this file.
#
# So the surface is derived from the standard library itself, and every name
# on it is classified below with a reason. Three audits close the triangle:
#
#   * every name on the live surface appears in the table
#     (``test_every_spelling_the_stdlib_offers_is_classified``) -- a
#     spelling nobody thought of is red, not silent;
#   * each set equals the table's projection, in both directions
#     (``test_the_listing_sets_are_exactly_the_classified_spellings``,
#     ``test_the_host_state_probe_is_exactly_the_classified_spellings``) --
#     a member deleted from a set, and a member added to one without a
#     classification, are both red;
#   * every name the guards actually use exists in the library
#     (``test_a_spelling_the_guards_use_is_a_real_stdlib_name``) -- a typo
#     or an invented member is red.
#
# The bound, stated because it is the one thing this cannot do: the surface
# is the *running* interpreter's. A platform or version offering a name this
# host does not (Linux's ``getxattr``, Windows' ``listdrives``) makes the
# completeness audit red until that name is classified -- which is the audit
# working, not failing. A handful of Linux and Windows spellings are
# pre-classified below as a courtesy to a run on one of those; whether that
# handful is COMPLETE for those hosts is not measured here and is not
# claimed, because it cannot be measured from this one. The reverse
# direction is deliberately not an equality: an entry for a name this host
# lacks is kept, so the table can carry other platforms' spellings, and
# ``test_a_spelling_the_guards_use_is_a_real_stdlib_name`` exempts exactly
# those (KIND_NEITHER) and no others.

KIND_LISTER = "lister"
KIND_GLOBBER = "globber"
KIND_WRAPPER = "wrapper"
KIND_JOINER = "joiner"
KIND_PROBE = "probe"
KIND_NEITHER = "neither"
_ALL_KINDS = frozenset(
    {
        KIND_LISTER, KIND_GLOBBER, KIND_WRAPPER, KIND_JOINER, KIND_PROBE,
        KIND_NEITHER,
    }
)

#: The namespaces the surface is read out of. ``os`` and ``os.path`` because
#: the module functions are the half the rule could not reach until review
#: cycle 3, ``pathlib.Path`` because the methods are the other half, and
#: ``glob`` because ``iglob`` lives nowhere else.
_SURFACE_NAMESPACES: tuple[tuple[str, object], ...] = (
    ("os", os),
    ("os.path", os.path),
    ("glob", glob),
    ("pathlib.Path", Path),
)


def _stdlib_directory_surface() -> dict[str, frozenset[str]]:
    """Every public spelling the library offers, as ``name -> namespaces``.

    Two mechanical filters, each one a reason that can be checked rather
    than taken on trust:

    * a leading underscore is not public API, and no rule here matches one;
    * a non-callable cannot be the function of a call, and every rule here
      fires on a *call* -- so ``os.sep`` and ``os.environ`` cannot be a
      listing however they are spelled.

    From ``pathlib`` itself only the path *classes* are taken: a listing is a
    ``Path`` method, already covered by ``dir(Path)``, and a wrapper has to
    return something that still denotes the directory, which the module's
    other callables (``copyfileobj``, ``S_ISDIR``) do not.
    """
    surface: dict[str, set[str]] = {}
    for label, namespace in _SURFACE_NAMESPACES:
        for name in dir(namespace):
            if name.startswith("_") or not callable(getattr(namespace, name, None)):
                continue
            surface.setdefault(name, set()).add(label)
    for name in dir(pathlib):
        value = getattr(pathlib, name, None)
        if (
            not name.startswith("_")
            and isinstance(value, type)
            and issubclass(value, pathlib.PurePath)
        ):
            surface.setdefault(name, set()).add("pathlib")
    # The one builtin: ``str(REPO_ROOT / "meta" / "kanban")`` is that
    # directory, and ``str`` is in no module's ``dir()``.
    surface.setdefault("str", set()).add("builtins")
    return {name: frozenset(labels) for name, labels in surface.items()}


#: The classification, grouped by the reason rather than one line per
#: name, so the reason is written once and every name carries it. A name
#: in two groups is red (``test_no_spelling_is_classified_twice``), so the
#: grouping cannot quietly last-win.
_SURFACE_CLASSIFICATION: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    # -- the listers: the directory's contents, with no filename at all
    (
        KIND_LISTER,
        "returns the directory's own contents",
        (
            "fwalk", "iterdir", "listdir", "scandir", "walk"
        ),
    ),
    # -- the globbers: the same, filtered by a pattern the call names
    (
        KIND_GLOBBER,
        "returns the directory's contents, filtered by a pattern",
        (
            "glob", "glob0", "glob1", "iglob", "rglob"
        ),
    ),
    # -- the wrappers: peeled before the listing rules judge what is inside
    (
        KIND_WRAPPER,
        "re-spells the same directory without becoming a different one",
        (
            "Path", "PosixPath", "PurePath", "PurePosixPath", "PureWindowsPath",
            "WindowsPath", "absolute", "abspath", "as_posix", "expanduser",
            "expandvars", "fsdecode", "fsencode", "fspath", "normcase",
            "normpath", "realpath", "relpath", "resolve", "str"
        ),
    ),
    # -- the joiners: they ASSEMBLE the directory out of the components the
    # call names, which is the half review cycle 5 left unpoliced (F-501).
    # Membership is not a judgement either: every name here is *measured* to
    # build ``meta/kanban`` out of two component strings, and every other
    # path-algebra name is measured not to
    # (``test_every_construction_spelling_is_classified``). The path
    # constructors do it too (``Path(ROOT, "meta", "kanban")``) and stay
    # KIND_WRAPPER, because with one argument they re-spell rather than
    # assemble; the rule reads the two kinds as one union, so a constructor
    # is covered either way and no name is classified twice.
    (
        KIND_JOINER,
        "assembles a directory out of the components the call names",
        (
            "join", "joinpath", "with_segments"
        ),
    ),
    # -- the host-state probes: a skip keyed on one of these answers is keyed
    # on the host, which is the defect this card removes
    (
        KIND_PROBE,
        "answers what the host's filesystem holds at a path",
        (
            "access", "exists", "fpathconf", "fstat", "fstatvfs", "getatime",
            "getctime", "getmtime", "getsize", "group", "is_block_device",
            "is_char_device", "is_dir", "is_fifo", "is_file", "is_junction",
            "is_mount", "is_socket", "is_symlink", "isdevdrive", "isdir",
            "isfile", "isjunction", "islink", "ismount", "lexists", "lstat",
            "owner", "pathconf", "pread", "preadv", "read", "read_bytes",
            "read_text", "readinto", "readlink", "readv", "samefile",
            "sameopenfile", "samestat", "stat", "statvfs"
        ),
    ),
    (
        KIND_NEITHER,
        "a type or exception object, not a call that reaches a directory",
        (
            "DirEntry", "GenericAlias", "Mapping", "MutableMapping", "PathLike",
            "error", "stat_result", "statvfs_result", "terminal_size",
            "times_result", "uname_result", "waitid_result"
        ),
    ),
    (
        KIND_NEITHER,
        "decodes a child process's exit status; no filesystem in it",
        (
            "WCOREDUMP", "WEXITSTATUS", "WIFCONTINUED", "WIFEXITED",
            "WIFSIGNALED", "WIFSTOPPED", "WSTOPSIG", "WTERMSIG", "wait",
            "wait3", "wait4", "waitid", "waitpid", "waitstatus_to_exitcode"
        ),
    ),
    (
        KIND_NEITHER,
        "process, signal or scheduling control, not the filesystem",
        (
            "abort", "cpu_count", "execl", "execle", "execlp", "execlpe",
            "execv", "execve", "execvp", "execvpe", "fork", "forkpty",
            "getloadavg", "getpgid", "getpgrp", "getpid", "getppid",
            "getpriority", "getrandom", "getsid", "kill", "killpg", "nice",
            "pidfd_open", "plock", "posix_spawn", "posix_spawnp",
            "process_cpu_count", "register_at_fork", "sched_get_priority_max",
            "sched_get_priority_min", "sched_getaffinity", "sched_getparam",
            "sched_getscheduler", "sched_rr_get_interval", "sched_setaffinity",
            "sched_setparam", "sched_setscheduler", "sched_yield", "setpgid",
            "setpgrp", "setpriority", "setsid", "spawnl", "spawnle", "spawnlp",
            "spawnlpe", "spawnv", "spawnve", "spawnvp", "spawnvpe", "strerror",
            "times", "uname", "urandom"
        ),
    ),
    (
        # Review cycle 5's third Minor, corrected rather than restated. These
        # two sat under "it names no directory" and "not the filesystem", and
        # ``os.popen("ls " + str(KANBAN))`` is both -- a plausible-sounding
        # reason that is simply false. The honest reason is that these rules
        # do not read shell command text at all, and the same is true of
        # ``subprocess``, which is outside :data:`_SURFACE_NAMESPACES`
        # entirely and is **this module's own idiom** (``git ls-files``).
        #
        # So the exclusion is stated as what it is -- a non-claim -- and the
        # non-claim is pinned from the other side: the shell-out forms are
        # entries in :data:`MEASURED_STRUCTURAL_MISSES`, so "we do not read
        # shell text" goes red the day a rule here starts to.
        KIND_NEITHER,
        "runs a command whose text these rules do not read; shelling out to "
        "list a directory is a measured, recorded miss and not a claim",
        (
            "popen", "system"
        ),
    ),
    (
        KIND_NEITHER,
        "user, group or device identity, not the filesystem",
        (
            "getegid", "geteuid", "getgid", "getgrouplist", "getgroups",
            "getlogin", "getresgid", "getresuid", "getuid", "initgroups",
            "major", "makedev", "minor", "setegid", "seteuid", "setgid",
            "setgroups", "setregid", "setresgid", "setresuid", "setreuid",
            "setuid"
        ),
    ),
    (
        KIND_NEITHER,
        "answers from the process environment, not from what the "
        "filesystem holds -- the env-var form of this coupling is a "
        "recorded, still-open survivor",
        (
            "confstr", "get_exec_path", "getenv", "getenvb", "putenv",
            "reload_environ", "sysconf", "unsetenv"
        ),
    ),
    (
        KIND_NEITHER,
        "names the process's own directory, not one this guard is about; "
        "a join from it is judged by the join rule",
        (
            "chdir", "cwd", "fchdir", "getcwd", "getcwdb", "home"
        ),
    ),
    (
        KIND_NEITHER,
        "pure path-string arithmetic; it consults no filesystem and it "
        "assembles no directory out of components",
        (
            "basename", "commonpath", "commonprefix", "dirname", "full_match",
            "is_absolute", "is_relative_to", "is_reserved", "isabs", "match",
            "relative_to", "split", "splitdrive", "splitext", "splitroot",
            "with_name", "with_stem", "with_suffix"
        ),
    ),
    (
        KIND_NEITHER,
        "a glob pattern-text helper; it consults no directory",
        (
            "escape", "has_magic", "translate"
        ),
    ),
    (
        KIND_NEITHER,
        "converts between a path and a URI, which no listing call accepts",
        (
            "as_uri", "from_uri"
        ),
    ),
    (
        KIND_NEITHER,
        "changes the filesystem instead of answering what it holds",
        (
            "chflags", "chmod", "chown", "chroot", "copy", "copy_file_range",
            "copy_into", "fchmod", "fchown", "fsync", "ftruncate",
            "hardlink_to", "lchflags", "lchmod", "lchown", "link", "lockf",
            "makedirs", "mkdir", "mkfifo", "mknod", "move", "move_into",
            "posix_fadvise", "posix_fallocate", "pwrite", "pwritev", "remove",
            "removedirs", "rename", "renames", "replace", "rmdir", "sendfile",
            "splice", "symlink", "symlink_to", "sync", "touch", "truncate",
            "umask", "unlink", "utime", "write", "write_bytes", "write_text",
            "writev"
        ),
    ),
    (
        KIND_NEITHER,
        "file-descriptor plumbing; it names no directory and answers no "
        "presence question",
        (
            "close", "closerange", "ctermid", "device_encoding", "dup", "dup2",
            "dup3", "eventfd", "eventfd_read", "eventfd_write", "fdopen",
            "get_blocking", "get_inheritable", "get_terminal_size", "grantpt",
            "isatty", "login_tty", "lseek", "memfd_create", "openpty", "pipe",
            "pipe2", "posix_openpt", "ptsname", "set_blocking",
            "set_inheritable", "tcgetpgrp", "tcsetpgrp", "timerfd_create",
            "timerfd_gettime", "timerfd_gettime_ns", "timerfd_settime",
            "timerfd_settime_ns", "ttyname", "unlockpt"
        ),
    ),
    (
        KIND_NEITHER,
        "opens a handle and raises rather than returning a presence "
        "answer, so a skip keyed on it is an except-handler and not an "
        "if-condition",
        ("open",),
    ),
    (
        KIND_NEITHER,
        "enumerates the host's drives, mounts or volumes and takes no "
        "directory",
        (
            "listdrives", "listmounts", "listvolumes"
        ),
    ),
    (
        KIND_NEITHER,
        "extended-attribute I/O on a path already named; not a listing "
        "and not a presence answer",
        (
            "getxattr", "listxattr", "removexattr", "setxattr"
        ),
    ),
)

#: Every name on that surface, classified, with its reason on the record.
#: An exclusion here is a decision somebody can argue with; an omission is
#: impossible, because the completeness audit fails on one.
STDLIB_DIRECTORY_SURFACE: dict[str, tuple[str, str]] = {
    name: (kind, reason)
    for kind, reason, names in _SURFACE_CLASSIFICATION
    for name in names
}


def _classified(*kinds: str) -> frozenset[str]:
    """The names in :data:`STDLIB_DIRECTORY_SURFACE` of any of ``kinds``."""
    return frozenset(
        name for name, (kind, _) in STDLIB_DIRECTORY_SURFACE.items() if kind in kinds
    )


def _guard_set(*kinds: str) -> frozenset[str]:
    """The classified spellings of ``kinds`` that this interpreter offers.

    The intersection is the whole point and it is review cycle 5's F-502.
    Until CARD-239 the four sets were hand-written frozensets, so a member
    the running interpreter does not have -- ``glob0`` and ``glob1``, which
    CPython deprecates, or ``is_junction``/``isjunction``/``isdevdrive``,
    which arrived in 3.12/3.13 -- was a *typo-shaped* entry that
    ``test_a_spelling_the_guards_use_is_a_real_stdlib_name`` reported as a
    phantom: the module went red on an interpreter lacking any of the five
    (measured by deleting exactly those five attributes in a plugin: 1
    failed, 340 passed).

    Intersecting with the live surface settles it in the direction that
    cannot leave a hole: **a spelling nobody can write cannot be missed**.
    If ``glob.glob0`` does not exist on this interpreter, no source on this
    interpreter can call it, so dropping it from the globbers costs nothing;
    if it does exist, the audit puts it in. The table keeps the entry either
    way, because the table is the record of the decision and is read on
    every host.

    What it does NOT do is excuse a typo: a classified name absent from this
    host is still reported, now against
    :data:`PLATFORM_GATED_SPELLINGS` -- the names recorded as genuinely
    version- or platform-gated -- so an invented ``listdirs`` is red while a
    3.9 run is green.
    """
    return _classified(*kinds) & frozenset(_stdlib_directory_surface())


#: The classified spellings this host does not offer, with the reason each
#: one is absent rather than misspelled. A **subset** claim, not an equality:
#: on the interpreter that has all five the left side is empty, and no static
#: list can be equal to it on every host. So the falsifiable half is the only
#: half there is -- a non-KIND_NEITHER name missing from the surface and
#: missing from here is red
#: (``test_a_spelling_the_guards_use_is_a_real_stdlib_name``), which is what
#: catches a typo. The benign direction is stated rather than claimed: an
#: entry here that stops being gated is not detected, and nothing pretends
#: otherwise.
PLATFORM_GATED_SPELLINGS: dict[str, str] = {
    "glob0": "a private-by-convention glob helper CPython deprecates; gone "
             "in a future version",
    "glob1": "the same, and the same",
    "is_junction": "pathlib.Path.is_junction, added in 3.12",
    "isjunction": "os.path.isjunction, added in 3.12",
    "isdevdrive": "os.path.isdevdrive, added in 3.13",
    "listdrives": "Windows only (os.listdrives, 3.12)",
    "listmounts": "Windows only",
    "listvolumes": "Windows only",
    "with_segments": "pathlib.PurePath.with_segments, added in 3.12",
    "full_match": "pathlib.PurePath.full_match, added in 3.13",
    "copy": "pathlib.Path.copy, added in 3.14",
    "copy_into": "pathlib.Path.copy_into, added in 3.14",
    "move": "pathlib.Path.move, added in 3.14",
    "move_into": "pathlib.Path.move_into, added in 3.14",
}


# --------------------------------------------------------------------------
# The four sets the rules consult, each one the audited table's projection.
# --------------------------------------------------------------------------
# These used to be hand-written frozensets several hundred lines above, which
# is why they are here now: review cycle 5 could audit them only by comparing
# two independently maintained things, and CARD-239 makes the table the one
# source. A member cannot be dropped by hand any more, and a member added to
# the table without a reason is red
# (``test_every_classification_carries_a_reason``). The structural half of
# that is pinned too: ``test_the_guard_sets_are_derived_and_not_hand_written``
# reads this module's own source and fails if any of the five assignments
# below becomes a literal again.

#: The globbers: the directory's contents, filtered by a pattern the call
#: names.
_GLOBBERS = _guard_set(KIND_GLOBBER)

#: The listers: the directory's contents, with no filename at all -- what
#: comes back depends on what the host happens to have put there.
#:
#: The set mixes two call shapes on purpose, and until review cycle 3 (F-301,
#: F-304) the rule could only fire on one of them. ``p.iterdir()`` and
#: ``d.glob(...)`` carry the directory as the call's RECEIVER; ``os.listdir``,
#: ``os.scandir`` and ``glob.iglob`` are module functions that carry it as an
#: ARGUMENT -- positionally or by keyword (``os.listdir(path=...)``, review
#: cycle 4's F-402) -- and there is no ``Path.listdir`` or ``Path.scandir``.
#: The rule tests receiver and arguments alike.
#:
#: ``walk`` and ``fwalk`` are in the table because review cycle 4's Critical
#: found ``os.walk`` -- the most-written directory enumerator in the library
#: -- missing from a set four cycles had edited by hand; ``glob0``/``glob1``
#: because the audit asked what they were and no reason to exclude them
#: survived the asking. Every member also has a positive control the guard is
#: measured to catch (``test_every_listing_and_globbing_spelling_has_a_control``)
#: and that control has to DEPEND on the membership -- caught with the
#: spelling in the set and missed without it
#: (``test_the_control_for_each_spelling_depends_on_the_set``). Both are
#: separate claims from completeness and neither substitutes for it.
_LISTERS = _guard_set(KIND_LISTER)

#: The joiners: the spellings that BUILD the directory rather than read it,
#: which is review cycle 5's F-501 and the half nothing policed. The audit
#: that derived the reading surface from ``dir(os)`` left the construction
#: surface a judgement, and three spellings sat in the "pure path-string
#: arithmetic" exclusion with a reason that was true of their *return type*
#: and false of their use: ``os.listdir(os.path.join(REPO_ROOT, "meta",
#: "kanban"))`` reads the owner's directory and returned ``[]`` from the
#: guard, as did the hoisted form, ``REPO_ROOT.joinpath("meta",
#: "kanban").iterdir()`` and the ``os.getcwd()`` variant -- while the ``/``
#: and ``Path.cwd() / ...`` spellings were caught. Compounded with the
#: except-handler bound, a mutant in that shape survived the whole module at
#: 250 passed.
#:
#: Membership here is MEASURED, not judged: see
#: ``test_every_construction_spelling_is_classified``, which calls every
#: path-algebra spelling the library offers on two component strings and
#: requires every one that comes back denoting ``meta/kanban`` to be a joiner
#: or a wrapper. That is how ``with_segments`` got here -- nobody had thought
#: of it, exactly as nobody had thought of ``fwalk``.
_JOINERS = _guard_set(KIND_JOINER)

#: The joiners the library offers as a path METHOD rather than as a module
#: function, so that such a call's RECEIVER is the base its components hang
#: off: ``ROOT.joinpath("meta", "kanban")`` starts at ``ROOT``, while
#: ``os.path.join(ROOT, "meta", "kanban")`` starts at its first argument and
#: ``os.sep.join([...])``'s receiver is a separator and no part of the path
#: at all. Derived from the same namespaces the surface is, because it is the
#: same question: ``dir(pathlib.Path)`` offers ``joinpath`` and
#: ``with_segments``, ``dir(os.path)`` offers ``join``. Getting this wrong in
#: the lenient direction was measured, not reasoned -- treating every
#: attribute joiner's receiver as a component made ``os.path`` itself a path
#: component and the glob control in :data:`REINTRODUCTIONS` went red.
_PATH_METHOD_JOINERS = frozenset(
    name
    for name, labels in _stdlib_directory_surface().items()
    if name in _JOINERS and labels == frozenset({"pathlib.Path"})
)

#: The wrappers a directory can arrive in without becoming a different
#: directory, in both shapes they are written: a one-argument call
#: (``str(REPO_ROOT / "meta" / "kanban")``) and a no-argument method on the
#: directory itself (``KANBAN.resolve()``). Peeled before the listing rules
#: judge what is inside.
#:
#: Review cycle 4's claim sweep narrowed this set to three on the grounds
#: that ``PosixPath`` and ``WindowsPath`` are "spellings nobody writes", and
#: wrote ``test_every_path_wrapper_is_seen_through`` to justify the narrowing
#: -- which cycle 4's F-403 then showed cannot fail for any bare name,
#: because it generates its source from the set it is testing. Both halves of
#: that are corrected: the membership question is settled by the audit, not
#: by a judgement about what people write, and the narrowness is pinned from
#: the other side by :data:`NOT_A_PATH_WRAPPER`, whose shapes stop being
#: misses the moment a name that denotes a *different* directory is let in.
#:
#: The path constructors are in here rather than in the joiners although they
#: assemble a path from several arguments, because with one argument they
#: re-spell one -- and the rules read ``_JOINERS | _PATH_WRAPPERS`` as the
#: component-bearing union, so ``Path(ROOT, "meta", "kanban")`` is covered by
#: the membership it already had. No name is classified twice
#: (``test_no_spelling_is_classified_twice``).
_PATH_WRAPPERS = _guard_set(KIND_WRAPPER)


class Spellings(NamedTuple):
    """The sets a walk of one source consults, passed rather than read.

    Review cycle 5's meta-guard -- the most valuable test on CARD-238, by
    the reviewer's own reading -- narrowed a set by ``setattr`` on this
    module and restored it in a ``finally``. Correct today, and the reason
    for changing it is **reasoned rather than measured**, which is said
    plainly because this card's subject is claims that cannot fail: neither
    ``pytest-xdist`` nor ``pytest-randomly`` is in this project's dependency
    baseline, so the interleaving that would expose it cannot be
    demonstrated here. What *is* demonstrable is the shape -- a module
    global mutated inside a test, read by a function several other tests
    call -- and the fix costs one defaulted parameter. The sets are that
    parameter now, defaulted to :data:`SPELLINGS`, so narrowing one is a
    local value and the meta-guard has no global to restore.
    """

    listers: frozenset[str]
    globbers: frozenset[str]
    joiners: frozenset[str]
    wrappers: frozenset[str]

    def without(self, spelling: str) -> Spellings:
        """The same sets with ``spelling`` removed from every one of them."""
        return Spellings(
            *(frozenset(field - {spelling}) for field in self)
        )

    @property
    def component_bearing(self) -> frozenset[str]:
        """The calls whose arguments spell out path components."""
        return self.joiners | self.wrappers


#: The default the rules are measured against: the audited projections above.
SPELLINGS = Spellings(
    listers=_LISTERS,
    globbers=_GLOBBERS,
    joiners=_JOINERS,
    wrappers=_PATH_WRAPPERS,
)


#: The two components the construction probe assembles, and the directory it
#: looks for. Relative on purpose: every argument the probe passes is a
#: relative string, so anything a probed call manages to create lands under
#: the temporary working directory the test moves into, and no probed call
#: can name a path outside it.
_PROBE_BASE = "base"
_PROBE_COMPONENTS = ("meta", "kanban")

#: The namespaces :func:`_measured_path_builders` is allowed to CALL into.
#: Every namespace the surface is read out of except the top-level ``os``,
#: which was excluded by measurement: see that function's docstring, and the
#: non-claim it states.
_PROBED_NAMESPACES = frozenset(
    {label for label, _ in _SURFACE_NAMESPACES} | {"pathlib", "builtins"}
) - {"os"}


def _denotes_the_kanban_directory(value: object) -> bool:
    """Does this value, read as a path, end at ``meta/kanban``?"""
    try:
        text = os.fspath(value)  # type: ignore[arg-type]
    except TypeError:
        return False
    return isinstance(text, str) and text.endswith(
        os.sep.join(_PROBE_COMPONENTS)
    )


def _measured_path_builders() -> dict[str, list[str]]:
    """``name -> shapes`` for every surface spelling that ASSEMBLES a directory.

    The authority for "which spellings build a path" is the library's own
    behaviour, so this asks it: every public callable
    :func:`_stdlib_directory_surface` offers in a namespace this is allowed
    to call into (:data:`_PROBED_NAMESPACES`) is called with a base and two
    components, in the three shapes a path assembly is written -- a module
    function over the components, the same with the components in a list
    (``os.sep.join([...])``), and a method on the base -- and whatever comes
    back denoting ``meta/kanban`` is a builder. Measured on 2026-10-17: seven
    of them, the four path constructors plus ``join``, ``joinpath`` and
    ``with_segments``.

    This is review cycle 5's F-501 answered the way cycle 5 answered the
    reading half: nobody enumerates the construction spellings, so the
    enumeration is the thing to get rid of. It named ``with_segments``, which
    no cycle of CARD-238 and no line of its follow-up card had thought of,
    exactly as ``dir(os)`` named ``fwalk``.

    Safety, and the bound that comes with it. Every argument is a
    *relative* string and the caller runs this with the working directory
    inside a ``tmp_path``, so a call that creates something creates it in
    there. That is not enough on its own: probing the top-level ``os``
    namespace was measured first in an isolated subprocess and
    ``os.popen("base", "meta", "kanban")`` **forked a shell**
    (``DeprecationWarning: This process is multi-threaded, use of fork()``),
    so :data:`_PROBED_NAMESPACES` excludes it -- by measurement, not by
    taste. The remaining namespaces are the path-algebra ones: ``os.path``
    is ``posixpath``, ``glob`` is pattern text, and ``pathlib`` is paths.

    So the **stated non-claim**: a builder living only in the top-level
    ``os`` namespace would not be found here. It would still have to be
    classified with a reason, because
    ``test_every_spelling_the_stdlib_offers_is_classified`` is red on an
    unclassified name whatever namespace it is in -- what is lost is the
    behavioural second opinion on that classification, and the two
    construction spellings ``os`` does offer (``fsdecode``, ``fspath``) are
    single-argument wrappers already in a set. This paragraph is a non-claim
    and not a promise; the measured result is pinned by
    ``test_every_construction_spelling_is_classified``'s non-vacuity
    assertions.

    ``BaseException`` is deliberately **not** caught: if some future call
    does escape with one, this must fail loudly rather than report a
    silently shorter list.
    """
    namespaces: dict[str, object] = {
        label: namespace for label, namespace in _SURFACE_NAMESPACES
    }
    namespaces["pathlib"] = pathlib
    builders: dict[str, list[str]] = {}
    for name, labels in _stdlib_directory_surface().items():
        for label in sorted(labels & _PROBED_NAMESPACES):
            shapes: list[tuple[str, Callable[[], object]]] = []
            if label == "pathlib.Path":
                shapes.append(
                    (
                        f"base.{name}(*components)",
                        lambda n=name: getattr(Path(_PROBE_BASE), n)(
                            *_PROBE_COMPONENTS
                        ),
                    )
                )
            else:
                function = (
                    getattr(namespaces[label], name, None)
                    if label in namespaces
                    else globals()["__builtins__"].get(name)
                    if isinstance(globals()["__builtins__"], dict)
                    else getattr(globals()["__builtins__"], name, None)
                )
                if function is None or not callable(function):
                    continue
                shapes.append(
                    (
                        f"{label}.{name}(base, *components)",
                        lambda f=function: f(_PROBE_BASE, *_PROBE_COMPONENTS),
                    )
                )
                shapes.append(
                    (
                        f"{label}.{name}([base, *components])",
                        lambda f=function: f([_PROBE_BASE, *_PROBE_COMPONENTS]),
                    )
                )
            for shape, call in shapes:
                try:
                    produced = call()
                except Exception:
                    continue
                if _denotes_the_kanban_directory(produced):
                    builders.setdefault(name, []).append(shape)
    return builders


def _is_pathish(value: str) -> bool:
    """Could this string be a filename or a path fragment?

    The taint tracking below follows a *name* only when the string it is
    bound to looks like one: no whitespace, nothing of source-code length.
    Without that test, this module's own corpora of fabricated sources --
    which quote the forbidden literals on purpose -- would taint every name
    they are bound to and the guard would flag its own positive controls.

    This filter decides *taint*, not reporting: it is applied to the string
    a *name* is bound to and never to a literal standing in a path position,
    which :func:`_live_log_references` judges on its own -- so a
    ``reason="suite-timing.log is absent"`` string still counts.

    It says nothing about which *wrapper* nodes :func:`_string_values`
    descends through, and two cycles running a sentence here was read as
    though it did. Review cycle 2 (F-105) found "flagged either way" untrue
    of a walrus inside the join; review cycle 3 (F-303) found the narrowed
    replacement still untrue of a ternary. Both are positive controls in
    :data:`REINTRODUCTIONS` now. Which wrappers are descended through is
    pinned there and bounded in :data:`MEASURED_STRUCTURAL_MISSES`, and is
    deliberately not restated here, where it could not go red.
    """
    return bool(value) and len(value) <= 120 and not any(c.isspace() for c in value)


def _string_values(
    node: ast.AST,
    env: dict[str, list[str]],
    spellings: Spellings = SPELLINGS,
) -> list[str]:
    """Every string ``node`` could evaluate to, as far as one module can tell.

    Deliberately over-approximate: a ``%``-format or a ``+`` is reported both
    folded and in parts, a slice reports the string it slices, and a lookup
    reports every value its container holds. The question this answers is
    "could the log's name be in here", so guessing wide is the safe direction.

    One call shape is **not** folded, which is review cycle 1's F-004: a
    path joiner's arguments are separate path *components*, so concatenating
    them yields a string no filesystem has.
    ``glob.glob(os.path.join(ROOT, "meta", "kanban", "*.log"))`` reported two
    references for one call site -- ``glob('*.log') under meta/kanban`` and
    ``glob('metakanban*.log') under meta/kanban`` -- and the second named
    nothing real. Detection was unaffected either way; the message a future
    reader acts on was not. The fold is kept where it means something: a
    ``str.join`` written on a string literal (``"".join(parts)``) *is*
    concatenation, and its receiver says so.
    """
    if isinstance(node, ast.Constant):
        return [node.value] if isinstance(node.value, str) else []
    if isinstance(node, ast.JoinedStr):
        out = ""
        for part in node.values:
            if isinstance(part, ast.Constant) and isinstance(part.value, str):
                out += part.value
            elif isinstance(part, ast.FormattedValue):
                resolved = _string_values(part.value, env, spellings)
                out += resolved[0] if resolved else ""
        return [out]
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        return [
            value
            for elt in node.elts
            for value in _string_values(elt, env, spellings)
        ]
    if isinstance(node, ast.Dict):
        return [
            value
            for item in node.values
            if item is not None
            for value in _string_values(item, env, spellings)
        ]
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Mod)):
        left = _string_values(node.left, env, spellings)
        right = _string_values(node.right, env, spellings)
        folded = [a + b for a in left or [""] for b in right or [""]]
        return [*left, *right, *folded]
    if isinstance(node, ast.Name):
        return env.get(node.id, [])
    if isinstance(node, ast.Attribute):
        return env.get(ast.unparse(node), [])
    if isinstance(node, (ast.Subscript, ast.Starred, ast.NamedExpr)):
        # A dict lookup, an index, a slice, or a walrus: all of them keep
        # the stem. The walrus is review cycle 2, F-105 -- one wrapper node
        # was enough to make a literal written straight into the join
        # invisible.
        return _string_values(node.value, env, spellings)
    if isinstance(node, ast.IfExp):
        # A ternary, which is the same lesson one cycle later (review cycle
        # 3, F-303): either arm is a string the path could be built from.
        return [
            *_string_values(node.body, env, spellings),
            *_string_values(node.orelse, env, spellings),
        ]
    if isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp)):
        # What is comprehended over is where the strings come from; the
        # element expression renames them at most.
        return [
            value
            for generator in node.generators
            for value in _string_values(generator.iter, env, spellings)
        ]
    if isinstance(node, ast.Call):
        # ``"...{}...".format(x)``, ``"".join(parts)``, ``str(p)``: what the
        # call is made of is what matters, not what it is called.
        parts: list[str] = []
        if isinstance(node.func, ast.Attribute):
            parts.extend(_string_values(node.func.value, env, spellings))
        for argument in [*node.args, *(kw.value for kw in node.keywords)]:
            parts.extend(_string_values(argument, env, spellings))
        if _assembles_path_components(node, spellings):
            return parts
        return [*parts, "".join(parts)]
    return []


def _assembles_path_components(node: ast.Call, spellings: Spellings) -> bool:
    """Does this call take its arguments as separate path COMPONENTS?

    Review cycle 1's F-004. ``os.path.join``, ``os.sep.join([...])``,
    ``p.joinpath(...)`` and ``p.with_segments(...)`` are handed components,
    so folding them into one string invents a name no filesystem has
    (``"metakanban*.log"``) -- and that invented name was being *reported*,
    beside the real one, for a glob under a joined directory.

    Which names those are is the audited joiner projection
    (:data:`_JOINERS`, through ``spellings``), not a judgement made here --
    the same source :func:`_component_arguments` reads.

    The one exception is the shape that is genuinely concatenation:
    ``"".join(parts)`` and its siblings, where the separator is a string
    literal the call names. Those keep the fold, so the taint chain that
    resolves ``"suite" + "-timing.log"`` is untouched.
    """
    name = _call_name(node)
    if name is None or name not in spellings.joiners:
        return False
    return not (
        isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Constant)
        and isinstance(node.func.value.value, str)
    )


def _tainted_names(tree: ast.Module) -> dict[str, list[str]]:
    """Names bound, anywhere in ``tree``, to something that names the log.

    Three passes, so a chain settles: ``STEM = "suite-timing"`` then
    ``NAME = STEM + ".log"`` then ``PATHS = {"log": NAME}``.

    Every binding form that can carry a string, not only ``=``: a walrus, a
    tuple-unpacking target, a ``for`` target taking its values from what is
    iterated, and a class-body assignment keyed under both ``LOG`` and
    ``Paths.LOG`` (review cycle 2, F-105 -- four one-step refactors of forms
    already caught, each measured as missed before this). Unpacking is
    deliberately over-approximate: ``OTHER, NAME = "x.txt", "...log"`` taints
    both names, because the question is "could the log's name be in here".
    """
    class_of: dict[int, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for statement in node.body:
                for child in ast.walk(statement):
                    class_of[id(child)] = node.name
    env: dict[str, list[str]] = {}

    def bind(target: ast.AST, carried: list[str], owner: str | None) -> None:
        if isinstance(target, ast.Starred):
            bind(target.value, carried, owner)
            return
        if isinstance(target, (ast.Tuple, ast.List)):
            for element in target.elts:
                bind(element, carried, owner)
            return
        if not isinstance(target, (ast.Name, ast.Attribute)):
            return
        keys = [ast.unparse(target)]
        if owner is not None and isinstance(target, ast.Name):
            keys.append(f"{owner}.{target.id}")
        for key in keys:
            env[key] = sorted({*env.get(key, []), *carried})

    for _ in range(3):
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                targets, value = node.targets, node.value
            elif isinstance(node, (ast.AnnAssign, ast.NamedExpr)):
                if node.value is None:
                    continue
                targets, value = [node.target], node.value
            elif isinstance(node, (ast.For, ast.AsyncFor)):
                # The loop variable is bound to whatever is iterated over.
                targets, value = [node.target], node.iter
            else:
                continue
            carried = sorted(
                {
                    found
                    for found in _string_values(value, env)
                    if _is_pathish(found)
                    and (LIVE_LOG_STEM in found or _LOG_UNDER_KANBAN.search(found))
                }
            )
            if not carried:
                continue
            owner = class_of.get(id(node))
            for target in targets:
                bind(target, carried, owner)
    return env


def _call_name(node: ast.Call) -> str | None:
    """The bare name of the function a call names, however it is reached."""
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    if isinstance(node.func, ast.Name):
        return node.func.id
    return None


def _component_arguments(
    node: ast.Call, spellings: Spellings = SPELLINGS
) -> list[ast.AST] | None:
    """The components a construction call spells out, left to right, or ``None``.

    ``None`` means "not a construction call", which is not the same answer as
    ``[]`` (a construction call that names nothing).

    The two shapes, which is review cycle 5's F-501: a module function taking
    the whole path (``os.path.join(ROOT, "meta", "kanban")``, and the
    constructors ``Path(ROOT, "meta", "kanban")``) and a method on the base
    (``ROOT.joinpath("meta", "kanban")``, ``ROOT.with_segments(...)``), where
    the receiver is the first component. A single list or tuple argument is
    unpacked, because ``os.sep.join(["meta", "kanban"])`` is the same call
    with its components in a container -- the separator receiver is dropped
    on purpose, since it is not a path component.

    Which NAMES count is :data:`Spellings.component_bearing` -- the audited
    joiner and wrapper projections, not a judgement made here. The wrappers
    are in it because a path constructor given several arguments assembles
    rather than re-spells, and the audit classifies it by its one-argument
    behaviour; which of the two kinds a name is does not change what its
    arguments mean.
    """
    name = _call_name(node)
    if name is None or name not in spellings.component_bearing:
        return None
    arguments = [*node.args, *(keyword.value for keyword in node.keywords)]
    if len(arguments) == 1 and isinstance(arguments[0], (ast.List, ast.Tuple)):
        arguments = list(arguments[0].elts)
    elif (
        isinstance(node.func, ast.Attribute)
        and name in spellings.joiners
        and name in _PATH_METHOD_JOINERS
    ):
        arguments = [node.func.value, *arguments]
    return arguments


def _joined_components(
    node: ast.AST, spellings: Spellings = SPELLINGS
) -> list[str]:
    """The path components a receiver expression spells out, left to right.

    Only the literal ones: a ``/`` operand that is not a string contributes
    ``"?"``, and a non-literal root (``REPO_ROOT``, a call with no single
    string argument) contributes nothing, because it *is* the root. So
    ``REPO_ROOT / "meta" / "kanban"`` and ``Path("meta/kanban")`` both come
    back as ``["meta", "kanban"]``.

    Since CARD-239 a *construction* call is read the same way as a ``/``
    chain, which is F-501: ``os.path.join(REPO_ROOT, "meta", "kanban")``,
    its hoisted and ``os.getcwd()`` variants, ``REPO_ROOT.joinpath("meta",
    "kanban")``, ``REPO_ROOT.with_segments(...)``, ``Path(ROOT, "meta",
    "kanban")`` and ``os.sep.join([...])`` all come back as
    ``["meta", "kanban"]`` too, where every one of them used to come back
    empty. Which spellings those are is :func:`_component_arguments`, over
    the audited sets.
    """
    parts: list[str] = []
    while True:
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            if isinstance(node.right, ast.Constant) and isinstance(
                node.right.value, str
            ):
                parts.append(node.right.value)
            else:
                parts.append("?")
            node = node.left
            continue
        if isinstance(node, ast.Call):
            arguments = _component_arguments(node, spellings)
            if arguments is not None and len(arguments) > 1:
                # Every argument but the first is a component; the first one
                # is the base, and recursing into it is what makes a nested
                # construction (`os.path.join(str(ROOT), "meta", "kanban")`)
                # read as one chain.
                for argument in reversed(arguments[1:]):
                    if isinstance(argument, ast.Constant) and isinstance(
                        argument.value, str
                    ):
                        parts.append(argument.value)
                    else:
                        parts.append("?")
                node = arguments[0]
                continue
        break
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        parts.append(node.value)
    elif (
        isinstance(node, ast.Call)
        and len(node.args) == 1
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
    ):
        parts.append(node.args[0].value)
    parts.reverse()
    return [
        component
        for part in parts
        for component in re.split(r"[/\\]", part)
        if component
    ]


def _is_the_kanban_directory(
    node: ast.AST, spellings: Spellings = SPELLINGS
) -> bool:
    """Does this expression name ``meta/kanban`` itself, and nothing below it?

    Review cycle 2, F-104: the listing rule used to fire on any receiver whose
    *text* contained both words, so ``(REPO_ROOT / "meta" / "kanban" /
    "cards").iterdir()`` -- a card-registry walk, of which this repo invites
    many -- was reported as a live-log read. Listing the kanban directory is
    the log coupling with no filename at all; listing a directory under it is
    not, and the ``cards`` listing in :data:`INNOCENT_MENTIONS` pins the line.
    """
    return _joined_components(node, spellings)[-2:] == ["meta", "kanban"]


def _unwrapped(node: ast.AST, spellings: Spellings = SPELLINGS) -> ast.AST:
    """``node`` with the :data:`_PATH_WRAPPERS` peeled off, if any.

    Two shapes, because the same wrapper is written both ways and only one
    of them used to be peeled: ``str(KANBAN)``, ``os.fspath(KANBAN)``,
    ``Path(KANBAN)`` are one-argument calls, while ``KANBAN.resolve()``,
    ``KANBAN.absolute()`` and ``KANBAN.expanduser()`` hang off the directory
    as no-argument methods. ``os.listdir(KANBAN.resolve())`` was a miss until
    the stdlib audit put ``resolve`` and ``absolute`` on the surface and
    asked which kind they were.
    """
    while True:
        if (
            isinstance(node, ast.Call)
            and len(node.args) == 1
            and not node.keywords
            and ast.unparse(node.func).rsplit(".", 1)[-1] in spellings.wrappers
        ):
            node = node.args[0]
        elif (
            isinstance(node, ast.Call)
            and not node.args
            and not node.keywords
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in spellings.wrappers
        ):
            node = node.func.value
        else:
            return node


def _leftmost(node: ast.AST, spellings: Spellings = SPELLINGS) -> ast.AST:
    """The expression a join or a ``+`` concatenation starts from.

    A construction call's base counts as its left operand since CARD-239, so
    the hoisted ``os.path.join(KANBAN, "*.log")`` spelling of the globbing
    rule starts where the ``/`` spelling of it does.
    """
    node = _unwrapped(node, spellings)
    while True:
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Div, ast.Add)):
            node = _unwrapped(node.left, spellings)
            continue
        if isinstance(node, ast.Call):
            arguments = _component_arguments(node, spellings)
            if arguments is not None and len(arguments) > 1:
                node = _unwrapped(arguments[0], spellings)
                continue
        return node


def _is_the_kanban_directory_or_a_name_for_it(
    node: ast.AST, known: frozenset[str], spellings: Spellings = SPELLINGS
) -> bool:
    """Does this expression denote ``meta/kanban`` itself, however spelled?

    The strict test, for the listing rules: the directory itself, or a name
    or attribute bound to it (:func:`_kanban_directories`). A path built
    *under* it is not it -- review cycle 2's
    F-104 (the ``cards`` registry walk) applies to the hoisted spelling just
    as much as to the inline one, and both are pinned in
    :data:`INNOCENT_MENTIONS`.
    """
    node = _unwrapped(node, spellings)
    if _is_the_kanban_directory(node, spellings):
        return True
    return isinstance(node, (ast.Name, ast.Attribute)) and ast.unparse(node) in known


def _starts_at_the_kanban_directory(
    node: ast.AST, known: frozenset[str], spellings: Spellings = SPELLINGS
) -> bool:
    """The loose test, for the globbing rule: does this start from that directory?

    A glob names its own ``.log`` filter, so the directory end of it may be
    judged loosely -- by the text mentioning both components, which is what
    this rule has always done, or by the join/concatenation starting at a
    name bound to the directory, which is the hoisted spelling review cycle
    3 (F-304) measured as missed.
    """
    text = ast.unparse(node)
    if "meta" in text and "kanban" in text:
        return True
    base = _leftmost(node, spellings)
    return isinstance(base, (ast.Name, ast.Attribute)) and ast.unparse(base) in known


def _kanban_directories(
    tree: ast.Module, spellings: Spellings = SPELLINGS
) -> frozenset[str]:
    """Names bound, anywhere in ``tree``, to the kanban directory itself.

    The listing rules need this and the taint tracker cannot supply it:
    :func:`_tainted_names` follows *strings that name the log*, and a
    directory names no log at all -- which is exactly why the ``*.log``
    prefilter in :func:`_live_log_references` does not gate the listing
    rules either.

    Two passes, so an alias chain settles whichever order the bindings are
    written in -- pinned by a control written bottom-up, because in source
    order one pass is enough and the claim would be vacuous. Names and
    attributes are bound, keyed the way :func:`_tainted_names` keys them, so
    a class-body binding answers to both ``KANBAN`` and ``Paths.KANBAN``;
    both have a control. Nothing else is a target here, and nothing is
    claimed about one.
    """
    class_of: dict[int, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for statement in node.body:
                for child in ast.walk(statement):
                    class_of[id(child)] = node.name
    known: set[str] = set()
    for _ in range(2):
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                targets, value = node.targets, node.value
            elif isinstance(node, (ast.AnnAssign, ast.NamedExpr)):
                if node.value is None:
                    continue
                targets, value = [node.target], node.value
            else:
                continue
            if not _is_the_kanban_directory_or_a_name_for_it(
                value, frozenset(known), spellings
            ):
                continue
            owner = class_of.get(id(node))
            for target in targets:
                if not isinstance(target, (ast.Name, ast.Attribute)):
                    continue
                known.add(ast.unparse(target))
                if owner is not None and isinstance(target, ast.Name):
                    known.add(f"{owner}.{target.id}")
    return frozenset(known)


def _caller_supplied(node: ast.FunctionDef | ast.AsyncFunctionDef) -> frozenset[str]:
    """Parameter names whose value only the caller can decide (no default)."""
    spec = node.args
    positional = [*spec.posonlyargs, *spec.args]
    required = positional[: len(positional) - len(spec.defaults)]
    keyword_only = [
        argument
        for argument, default in zip(spec.kwonlyargs, spec.kw_defaults)
        if default is None
    ]
    return frozenset(argument.arg for argument in [*required, *keyword_only])


def _live_log_references(
    source: str, spellings: Spellings = SPELLINGS
) -> list[str]:
    """Places in ``source`` that would reach the live log, by any spelling.

    Takes source text rather than walking the disk itself, so the rule can be
    exercised against the fabricated sources below and cannot pass vacuously
    (the precedent is ``tests/test_cli.py``'s structural import guard).

    A reference is a string that names the log -- by its stem, or as any
    ``.log`` under ``meta/kanban`` -- reaching a place where a path is built
    or read: an operand of a ``/`` join, an argument of a call
    (``Path(...)``, ``open(...)``, ``joinpath(...)``, ``os.path.join(...)``
    and ``skipif(..., reason="...log is absent")``, which is the same
    coupling wearing a different hat), the pattern of a ``glob`` over a
    ``meta/kanban`` directory, or a listing of that directory by any
    spelling :data:`STDLIB_DIRECTORY_SURFACE` classifies as one -- where
    "that directory" is any spelling the table classifies as *assembling*
    one (:data:`_JOINERS`) as much as the ``/`` chain.

    Until CARD-239 that last clause read "a listing of that directory by
    any spelling the table classifies as one", full stop, which was true of
    the spellings that READ a directory and false of the ones that BUILD
    one: ``os.listdir(os.path.join(REPO_ROOT, "meta", "kanban"))``, its
    hoisted form, the ``os.getcwd()`` variant and
    ``REPO_ROOT.joinpath("meta", "kanban").iterdir()`` all returned ``[]``
    while the ``/`` and ``Path.cwd() / ...`` spellings were caught --
    review cycle 5's F-501, which compounded with the except-handler bound
    below into a mutant that survived the whole module at 250 passed. The
    construction spellings are an audited projection now, and the audit is
    behavioural: ``test_every_construction_spelling_is_classified`` calls
    every path-algebra spelling the library offers on two components and
    requires each one that comes back denoting the directory to sit in a
    guard set or in an exclusion carrying a reason.

    Both qualifiers are the point, and they replace four cycles of "at
    all". Which spellings count is not a judgement made here any more: the
    sets are the projection of a table that is audited against ``dir(os)``,
    ``dir(os.path)``, ``dir(glob)`` and ``dir(pathlib.Path)``, so a library
    spelling nobody has judged is a failing test rather than a hole --
    review cycle 4's Critical was ``os.walk``, absent from a set four cycles
    had edited by hand and from the silence probe at the same time.

    A listing or a glob is judged by both ends of the call -- the receiver
    for ``p.iterdir()`` and ``d.glob(...)``, the positional **and keyword**
    arguments for the module functions (``os.listdir``, ``os.scandir``,
    ``os.walk``, ``glob.iglob``), which carry the directory there and have
    no ``Path`` method to be spelled as. ``os.listdir(path=KANBAN)`` is the
    keyword form, review cycle 4's F-402: the omission was inconsistent
    inside this one function, since the string-operand branch beside it had
    always read ``node.keywords``, and the bare-imported spelling of it
    survived a whole module at 168 passed. Until review cycle 3 (F-301,
    F-304) only the receiver was tested, so three members of
    :data:`_LISTERS` and :data:`_GLOBBERS` named a spelling the
    rule could not reach, and a mutant spelled ``os.listdir`` of a hoisted
    kanban directory restored this card's own defect with every guard green.
    The directory may be hoisted to a name at either end
    (:func:`_kanban_directories`): strictly it, for a listing, and merely
    started from, for a glob, which names its own ``.log`` filter. It may
    also arrive wrapped (:data:`_PATH_WRAPPERS`), as a one-argument call or
    as a no-argument method on the directory -- ``str(KANBAN)`` and
    ``KANBAN.resolve()`` are both that directory. One control per spelling
    in :data:`REINTRODUCTIONS`, one per wrapper in each shape, and the
    narrowness pinned from the other side by :data:`INNOCENT_MENTIONS` -- a
    subdirectory listing, by either spelling, and a directory the caller
    passed in -- and by :data:`NOT_A_PATH_WRAPPER`, which is red if a call
    naming a *different* directory is ever peeled.

    The string need not be written there. Review cycle 1 found this guard
    missing ten of twelve re-introductions because it judged by syntactic
    position only -- the decisive one being the routine refactor of naming
    the filename:

        LOG_NAME = "suite-timing.log"
        TIMING_LOG = REPO_ROOT / "meta" / "kanban" / LOG_NAME

    So names are now resolved before they are judged (see
    :func:`_tainted_names`), and every form held in :data:`REINTRODUCTIONS`
    -- hoisted, concatenated, ``%``-formatted, f-string-interpolated,
    starred, sliced, looked up in a dict, behind a walrus or a ternary --
    fails there, one control per form.

    Each of those is a form on its own and they do **not** compose, which
    review cycle 3 (F-305) found this list reading as though they did. The
    taint pass carries a value only once the folded string holds the stem,
    so ``STEM = "suite-timing"`` then ``NAME = STEM + ".log"`` settles over
    three passes and is caught, while a stem split so that neither half
    holds it resolves to nothing and is a miss -- held as the fifth control
    in :data:`MEASURED_STRUCTURAL_MISSES` rather than as a qualifier here.

    Deliberately *not* a reference: the name in a comment, in a docstring, or
    bound to a constant as :data:`LIVE_LOG_STEM` is above. That is the whole
    reason this is an ``ast`` walk and not a ``grep`` -- a grep cannot tell a
    note about the file from a read of it, and this module's own docstring
    mentions the file by name.

    One structural exemption: a ``/`` join whose leftmost operand is a
    *parameter* of the enclosing function is not a reference, because the
    root is whatever the caller passed -- :func:`_build_sandbox` passes a
    ``tmp_path``. The exemption is on the shape of the join and not on any
    name, so hoisting the root to a module constant removes it (asserted by
    ``test_the_sandbox_exemption_turns_off_when_the_root_is_a_constant``);
    a future author cannot borrow the word ``root`` to get through.

    What it cannot see is measured by executing each form, not guessed, and
    is held as controls in :data:`MEASURED_STRUCTURAL_MISSES` rather than
    only described here -- a sentence cannot go red when it stops being true,
    and on this card a stated coverage outran the real one four review
    cycles running. No count of them is written here either, for the same
    reason: the tuple can grow without this paragraph going stale, and a
    number in a docstring is the smallest version of this card's defect.
    Each entry is named there; two are worth a word more. The helper whose
    join is rooted at a parameter -- so the exemption above applies -- but
    which is *called* with a module constant (``_log_under(REPO_ROOT)``) is
    review cycle 2's: the exemption is keyed on the shape of the join, and a
    shape is easier to borrow than a name. The stem split across two names
    where neither half holds it is review cycle 3's, and is the qualifier
    the form list above was missing.

    Which of them the behavioural comparison kills, measured by
    executing each as a mutant in this module on 2026-10-16 and reading the
    verdict, not by reasoning about it:

    * the helper called with a constant root -- KILLED. The outcome flips
      with the sandbox log (PASSED with, FAILED without) because the helper
      is in a module the sandbox copies. Move the helper out of the mirrored
      territories and that stops being true;
    * a path imported from another module -- invisible to *this function*,
      which is handed one module at a time, but not to the guard that calls
      it: the defining module is itself walked whenever it is tracked and
      under :data:`GUARDED_DIRECTORIES`, so that pair is caught structurally
      after all (which is what killed the ranker-constant mutant). When the
      definition is outside those directories it is caught loudly rather
      than precisely -- measured with a sibling module resolving the real
      repository root: all-PASSED in both sandboxes before this fix, and
      afterwards the import either lands on a sandbox copy whose paths name
      the sandbox or is not there at all, so the module stops being
      all-PASSED in both;
    * an absolute path read out of the environment -- **NOT killed, by
      either half.** Measured at review cycle 3 (149 passed), re-measured
      against the widened guards at cycle 4 (161 passed) and again at cycle 5
      against the stdlib-audited sets: with ``CARD238_MUT_LOG`` set to an
      existing absolute path, a test reading it passed in the parent and in
      both sandboxes -- **331 passed, nothing red**; with the variable unset
      the same test is loud in all three (a collection error). An absolute
      path does not vary with the sandbox root, and the source names no log
      for the walk to resolve. Neither the keyword-argument fix nor the
      audited probe set touches it -- ``os.getenv`` is classified
      ``KIND_NEITHER`` deliberately, with a negative control in
      :data:`NOT_A_CONDITIONAL_SILENCE`, so the exclusion is a decision on
      the record. It stays an accepted bound rather than being quietly
      reclassified: the failure mode is loud, which is the property the
      original defect lacked. The same
      form with its *default* spelled out
      (``os.environ.get("...", str(REPO_ROOT / "meta" / "kanban" /
      "suite-timing.log"))``) is caught by both halves, and that is the form
      a refactor actually produces;
    * a stem rebuilt by arithmetic -- killed whenever its outcome varies,
      which is the general rule below. Deliberate evasion either way;
    * a stem split across two names -- **KILLED** by the comparison, not by
      the walk. Measured at cycle 4 by planting it here: the structural
      guard stays green (which is what the control asserts) and
      ``test_the_outcomes_are_identical_with_and_without_the_log`` goes red
      on its own -- 1 failed, 76 passed. It resolves to nothing in one
      module and its outcome still varies with the sandbox log.

    Also not reached by either half, and reasoned rather than measured
    because measuring it means editing ``src/**`` (this card's G-5): a path
    constant in a module that is importable independently of the sandbox --
    the editable-installed ``nonogram`` package -- would resolve the real
    repository from inside both sandboxes. No test here imports one.

    What catches those instead, stated as a bound rather than as a promise.
    The behavioural comparison in
    :class:`TestSuiteTiming_CollectsTheSameWithAndWithoutTheLog` judges by
    outcome, so it catches a coupling exactly when that coupling's outcome
    differs between the with-log and without-log sandboxes. Two things have
    to hold for that, and only the first is now guaranteed:

    * the coupling has to be in a module the sandbox *mirrors* (``tests/`` or
      ``meta/profiling/``) and has to resolve the sandbox root. Every
      ``*.py`` in the sandbox is a copy and no directory is linked, so it
      does --
      pinned by ``test_what_resolves_outside_the_sandbox_is_exactly_the_data_links``
      and by the cross-module control that must flip with the sandbox log.
      Review cycle 2 (F-101) found this false: ``meta/profiling`` was
      symlinked wholesale, so three mutants -- one of them this card's own
      defect, carried by a constant in ``meta/profiling`` -- survived all 41
      guards with ``present == absent`` holding vacuously;
    * the coupling has to *change* an outcome. A read whose result is
      swallowed, or a module outside both mirrored territories, is caught by
      neither half. That is the standing limit of this pair of guards, and
      the reason a tracked module naming the log is a repo-level offence here
      rather than a matter for one test to notice.
    """
    tree = ast.parse(source)
    # Resolving every call argument costs real time over ~110 test modules
    # (2.5s against 0.1s), and it can only ever find a string that some
    # literal in this same module contributed -- that is exactly what makes
    # the resolver below sound. So a module whose parsed tree holds no
    # literal naming a log skips the resolution. It does *not* skip the
    # walk: the glob and directory-listing rules below need no filename at
    # all, and gating those on a literal would put the hole back
    # ("listing the kanban directory, naming no log at all" pins this).
    names_a_log_somewhere = any(
        LIVE_LOG_STEM in node.value
        or node.value.endswith(".log")
        or _LOG_UNDER_KANBAN.search(node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    )
    env = _tainted_names(tree) if names_a_log_somewhere else {}
    found: set[str] = set()

    # Resolved on first use rather than up front, and *not* gated on the
    # ``.log`` prefilter above: a directory names no log, and gating the
    # listing rules on a literal is how the hole got in the first time
    # ("listing the kanban directory, naming no log at all" pins that). The
    # laziness is only cost: the two readers below are the only ones, and
    # they share the one resolution.
    resolved: list[frozenset[str]] = []

    def directories() -> frozenset[str]:
        if not resolved:
            resolved.append(_kanban_directories(tree, spellings))
        return resolved[0]

    def names_the_log(value: str) -> bool:
        return LIVE_LOG_STEM in value or bool(_LOG_UNDER_KANBAN.search(value))

    def join_base(node: ast.AST) -> ast.AST:
        while isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            node = node.left
        return node

    def visit(node: ast.AST, roots: frozenset[str]) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            roots = roots | _caller_supplied(node)
        operands: list[ast.AST] = []
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            base = join_base(node)
            if names_a_log_somewhere and not (
                isinstance(base, ast.Name) and base.id in roots
            ):
                operands = [node.left, node.right]
        elif isinstance(node, ast.Call):
            if names_a_log_somewhere:
                operands = [*node.args, *(kw.value for kw in node.keywords)]
            if isinstance(node.func, ast.Attribute):
                called: str | None = node.func.attr
                receiver: list[ast.AST] = [node.func.value]
            elif isinstance(node.func, ast.Name):
                # `from os import listdir`: no receiver to test at all, which
                # is the receiver-only rule's limit taken one step further.
                called, receiver = node.func.id, []
            else:
                called, receiver = None, []
            if called in (spellings.globbers | spellings.listers):
                # Where the directory can sit: the receiver for the bound-method
                # spellings, an argument for the module-function ones. Review
                # cycle 3, F-301/F-304: only the first was tested, so
                # `os.listdir`, `os.scandir` and a hoisted `glob.iglob` went
                # through. The caller-root exemption applies to both, for the
                # same reason -- a directory the caller passed in is not the
                # owner's -- and `os.listdir(root / "meta" / "kanban")` is its
                # control in :data:`INNOCENT_MENTIONS`.
                #
                # Keywords included, review cycle 4's F-402: `path` is the
                # parameter's real name in `os.listdir`/`os.scandir`, the
                # string-operand branch four lines up has always read
                # `node.keywords`, and `from os import listdir` plus
                # `listdir(path=KANBAN)` was a mutant that survived the whole
                # module at 168 passed.
                where = [
                    candidate
                    for candidate in [
                        *receiver,
                        *node.args,
                        *(keyword.value for keyword in node.keywords),
                    ]
                    if not (
                        isinstance(
                            base := _leftmost(candidate, spellings), ast.Name
                        )
                        and base.id in roots
                    )
                ]
                if called in spellings.listers and any(
                    _is_the_kanban_directory_or_a_name_for_it(
                        candidate, directories(), spellings
                    )
                    for candidate in where
                ):
                    # No filename needed, so no filter -- but the directory has
                    # to BE that directory, not merely mention it (F-104).
                    found.add(f"{called}() of meta/kanban")
                if called in spellings.globbers and any(
                    _starts_at_the_kanban_directory(
                        candidate, directories(), spellings
                    )
                    for candidate in where
                ):
                    # A glob names its own filter, so the looser test stays
                    # here: a `*.log` pattern anywhere under meta/kanban is the
                    # coupling whatever the directory end spells.
                    found.update(
                        f"{called}({pattern!r}) under meta/kanban"
                        for argument in node.args
                        for pattern in _string_values(argument, env, spellings)
                        if pattern.endswith(".log")
                    )
        for operand in operands:
            found.update(
                value
                for value in _string_values(operand, env, spellings)
                if names_the_log(value)
            )
        for child in ast.iter_child_nodes(node):
            visit(child, roots)

    visit(tree, frozenset())
    return sorted(found)


# What a condition has to touch before a skip counts as host state rather
# than as a statement about the code.
#
# A *set*, with the pattern derived from it, rather than a hand-written
# regex: this is the second of the two enumerations review cycle 4's
# Critical implicates, and until it was a set the audit above could not
# police it at all. Membership is
# :data:`STDLIB_DIRECTORY_SURFACE`'s projection and nothing else --
# everything that lists a directory, globs one, or answers what the host's
# filesystem holds at a path.
_HOST_STATE_PROBES = _guard_set(KIND_LISTER, KIND_GLOBBER, KIND_PROBE)


def _probe_pattern(names: frozenset[str]) -> re.Pattern[str]:
    """The host-state pattern for ``names``, in the two shapes they are written.

    ``\bname(`` catches the bound-method and the bare-imported spellings at
    once (``LOG.exists()``, ``listdir(KANBAN)``); the second alternative
    catches a module function named but not called in the condition
    (``os.listdir``, ``os.path.isdir``), which is the shape the hand-written
    pattern this replaces had for four of its alternatives
    (``os.path.exists``, ``os.path.isfile``, ``os.path.isdir``,
    ``os.listdir``) and for none of the rest.
    """
    alternatives = "|".join(sorted(re.escape(name) for name in names))
    return re.compile(
        rf"\b(?:{alternatives})\s*\(|\bos\.(?:path\.)?(?:{alternatives})\b"
    )


_HOST_STATE_PROBE = _probe_pattern(_HOST_STATE_PROBES)


def _host_state_names(tree: ast.Module) -> frozenset[str]:
    """Names bound to the answer of a filesystem probe.

    ``HAVE = LOG.exists()`` and then ``if not HAVE: pytest.skip(...)`` is the
    same silence with the probe hoisted one line up, and it turned the
    detector below off (review cycle 2, F-106) -- cycle 1's decisive miss,
    a name carried past a text-level test, one layer over. Two passes, so
    ``HAVE = LOG.exists()`` then ``READY = HAVE`` settles.
    """
    # The bindings are collected in one walk and the two fixpoint passes run
    # over that list: the same nodes in the same order, with each
    # ``ast.unparse`` done once instead of twice. The detector is run over
    # every guarded source since review cycle 3's F-301, and the second full
    # walk of every tree profiled as the largest single cost in it.
    bindings: list[tuple[str, list[str]]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, (ast.AnnAssign, ast.NamedExpr)):
            if node.value is None:
                continue
            targets, value = [node.target], node.value
        else:
            continue
        bindings.append(
            (
                ast.unparse(value),
                [
                    ast.unparse(target)
                    for target in targets
                    if isinstance(target, (ast.Name, ast.Attribute))
                ],
            )
        )
    names: set[str] = set()
    for _ in range(2):
        for source, bound in bindings:
            if not (
                _HOST_STATE_PROBE.search(source)
                or any(
                    re.search(rf"\b{re.escape(name)}\b", source) for name in names
                )
            ):
                continue
            names.update(bound)
    return frozenset(names)


def _conditional_silences(source: str) -> list[tuple[str, str]]:
    """``(what goes quiet, the condition)`` for every silence in ``source``.

    Named for what it enforces, which is wider than host state in one half
    and narrower in the other. Review cycle 2 (F-106) found the old name,
    docstring and test all saying "host state" while the mark half reported
    ``skipif(sys.platform == 'win32')`` too; the rule is kept and the names
    are corrected, because in *this* module the stricter rule is the one
    worth having -- a conditional skip here is how AC-3 stops being checked.

    Reported:

    * a ``skipif`` or a conditional ``xfail`` condition, **whatever it is
      keyed on** -- on a test, a class or a fixture, through an alias
      (``skipper = mark.skipif``), or as ``pytestmark`` at module level,
      including a list of marks. The platform skipif in
      :data:`CONDITIONAL_SILENCES` is the control for that width. An
      unconditional ``xfail`` is a statement about a defect, not about a
      run, and is not reported;
    * ``pytest.skip(...)`` or an early bare ``return`` in a ``test*`` body,
      when the controlling condition touches the filesystem
      (:data:`_HOST_STATE_PROBE`) or a name bound to such a probe
      (:func:`_host_state_names`) -- otherwise every ordinary ``if`` in a
      test would be reported;
    * ``pytest.skip(..., allow_module_level=True)`` at module scope, under a
      host-state condition or under none at all. Review cycle 2, F-102: that
      form made pytest report ``ERROR: found no collectors`` for *both*
      guard classes, and on a log-less host -- the fresh worktree that hid
      the original defect -- ``1 skipped, exit 0``. It sits above every test
      in the file, so the behavioural comparison cannot be its backstop: the
      comparison is one of the tests it silences.

    What counts as touching the filesystem is :data:`_HOST_STATE_PROBES`,
    and that set is audited against the library rather than written out by
    hand (``test_the_host_state_probe_is_exactly_the_classified_spellings``)
    -- review cycle 4's Critical was a skip gated on ``os.walk``, which the
    hand-written pattern this replaced did not name, and its F-404 was the
    same for ``.iterdir()``, ``os.scandir`` and ``os.access``.

    Measured limits, each one a form this returns ``[]`` for, and each one a
    control in :data:`NOT_A_CONDITIONAL_SILENCE` rather than only a clause
    here: a test that calls a *helper* which skips; a skip keyed on an
    environment variable (which is not filesystem state -- ``os.getenv`` is
    classified ``KIND_NEITHER`` for that reason, and the env-var form of
    this card's coupling is a recorded, still-open survivor); a module-scope
    skip under a condition that is neither host state nor absent, such as an
    interpreter-version check; and a skip from an ``except`` handler rather
    than from an ``if``, since every rule here reads conditions. The helper
    and the except-handler forms are the behavioural comparison's job; the
    version gate is deliberate, since it is a statement about the code. No
    count is given, so the tuple can grow without this paragraph going
    stale.
    """
    tree = ast.parse(source)
    nodes = list(ast.walk(tree))
    found: list[tuple[str, str]] = []
    probes = _host_state_names(tree)

    def is_host_state(condition: str) -> bool:
        return bool(_HOST_STATE_PROBE.search(condition)) or any(
            re.search(rf"\b{re.escape(name)}\b", condition) for name in probes
        )

    aliases = {
        ast.unparse(target): ast.unparse(node.value).rsplit(".", 1)[-1]
        for node in nodes
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
        and ast.unparse(node.value).rsplit(".", 1)[-1] in {"skipif", "xfail"}
    }

    def mark_of(call: ast.Call) -> str | None:
        unparsed = ast.unparse(call.func)
        if unparsed.endswith("skipif") or aliases.get(unparsed) == "skipif":
            return "skipif"
        if unparsed.endswith("xfail") or aliases.get(unparsed) == "xfail":
            return "xfail"
        return None

    def conditions_in(node: ast.AST) -> list[str]:
        """Every condition the marks in ``node`` are keyed on, host state or not.

        Wider than host state on purpose, and the platform skipif in
        :data:`CONDITIONAL_SILENCES` is the control for that width (review
        cycle 2, F-106: the old name and docstring here said host state while
        this reported `sys.platform` too).
        """
        out: list[str] = []
        for child in ast.walk(node):
            if not isinstance(child, ast.Call):
                continue
            mark = mark_of(child)
            if mark is None:
                continue
            if not child.args:
                # An unconditional skipif is not expressible; an
                # unconditional xfail is, and is not host state.
                if mark == "skipif":
                    out.append("")
                continue
            out.append(ast.unparse(child.args[0]))
        return out

    def silences_itself(body: list[ast.stmt]) -> list[str]:
        """Conditions under which this body stops rather than judges."""
        out: list[str] = []
        for statement in body:
            for node in ast.walk(statement):
                if not isinstance(node, ast.If):
                    continue
                condition = ast.unparse(node.test)
                if not is_host_state(condition):
                    continue
                for inner in ast.walk(node):
                    skipped = (
                        isinstance(inner, ast.Call)
                        and ast.unparse(inner.func).rsplit(".", 1)[-1] == "skip"
                    ) or (isinstance(inner, ast.Return) and inner.value is None)
                    if skipped:
                        out.append(condition)
                        break
        return out

    def skips_the_module(body: list[ast.stmt]) -> list[str]:
        """Imperative skips at module scope: the ones above every guard here.

        A statement, not a decorator and not a ``pytestmark``, so neither of
        the two branches below could see it (review cycle 2, F-102). Function
        and class definitions are stepped over: a skip inside a body is the
        in-body rule's business, and walking into them here would report
        every test that skips anything.
        """
        out: list[str] = []
        for statement in body:
            if isinstance(
                statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
            ):
                continue
            if isinstance(statement, ast.If):
                condition = ast.unparse(statement.test)
                if not is_host_state(condition):
                    # An interpreter-version gate is a statement about the
                    # code; pinned as a negative control.
                    continue
            else:
                condition = ""
            for inner in ast.walk(statement):
                if not (
                    isinstance(inner, ast.Call)
                    and ast.unparse(inner.func).rsplit(".", 1)[-1] == "skip"
                ):
                    continue
                if condition or any(
                    keyword.arg == "allow_module_level" for keyword in inner.keywords
                ):
                    out.append(condition)
                    break
        return out

    found.extend(("<module>", condition) for condition in skips_the_module(tree.body))

    for node in nodes:
        if isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call):
                    found.extend(
                        (node.name, condition) for condition in conditions_in(decorator)
                    )
            if not isinstance(node, ast.ClassDef) and node.name.startswith("test"):
                found.extend(
                    (node.name, condition) for condition in silences_itself(node.body)
                )
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = (
                node.targets if isinstance(node, ast.Assign) else [node.target]
            )
            if any(
                isinstance(target, ast.Name) and target.id == "pytestmark"
                for target in targets
            ) and node.value is not None:
                found.extend(
                    ("pytestmark", condition) for condition in conditions_in(node.value)
                )
    return found


# Every form in which the read could come back. Held as a module constant
# rather than inline in a ``parametrize`` call so that these sources are not
# themselves direct call arguments -- which would make this module its own
# first offender.
REINTRODUCTIONS: tuple[tuple[str, str], ...] = (
    (
        "the original coupling, as a literal",
        'TIMING_LOG = REPO_ROOT / "meta" / "kanban" / "suite-timing.log"\n',
    ),
    ("Path of a literal", 'LOG = Path("meta/kanban/suite-timing.log")\n'),
    ("open of a literal", 'text = open("meta/kanban/suite-timing.log").read()\n'),
    (
        "joinpath of literal parts",
        'LOG = REPO_ROOT.joinpath("meta", "kanban", "suite-timing.log")\n',
    ),
    ("an f-string path", 'LOG = Path(f"{root}/meta/kanban/suite-timing.log")\n'),
    (
        "a skipif whose reason names the file",
        "import pytest\n"
        '@pytest.mark.skipif(not LOG.exists(), reason="suite-timing.log is absent")\n'
        "def test_x() -> None:\n    pass\n",
    ),
    # Review cycle 1, F-001: the ten forms the position-only guard missed.
    # The first is not an evasion at all -- it is the routine refactor of
    # naming the filename -- and it reproduced the exact coupling this card
    # exists to remove while all fifteen guard tests stayed green.
    (
        "the filename hoisted to a name",
        'LOG_NAME = "suite-timing.log"\n'
        'TIMING_LOG = REPO_ROOT / "meta" / "kanban" / LOG_NAME\n',
    ),
    (
        "os.path.join with a hoisted name",
        "import os\n"
        'NAME = "suite-timing.log"\n'
        'LOG = os.path.join(str(REPO_ROOT), "meta", "kanban", NAME)\n',
    ),
    (
        "the filename split across a concatenation",
        'LOG = Path("meta/kanban/suite-" + "timing.log")\n',
    ),
    (
        "a glob for any log under meta/kanban",
        'LOG = next((REPO_ROOT / "meta" / "kanban").glob("*.log"))\n',
    ),
    (
        "the path parts starred into Path",
        'PARTS = ("meta", "kanban", "suite-timing.log")\n'
        "LOG = REPO_ROOT / Path(*PARTS)\n",
    ),
    # The form this module's own sandbox helper uses, so the file
    # demonstrated its own bypass. It is caught here and exempted there by
    # the shape of the join, not by the name -- see SANDBOX_ROOTED below.
    (
        "the stem interpolated into an f-string",
        'STEM = "suite-timing"\n'
        'LOG = REPO_ROOT / "meta" / "kanban" / f"{STEM}.log"\n',
    ),
    (
        "a fixture handing the path out",
        "import pytest\n"
        'NAME = "suite-timing.log"\n'
        "@pytest.fixture\n"
        "def live_log() -> Path:\n"
        '    return REPO_ROOT / "meta" / "kanban" / NAME\n',
    ),
    (
        "percent formatting",
        'LOG = Path("meta/kanban/%s.log" % "suite-timing")\n',
    ),
    (
        "a dict lookup",
        'PATHS = {"log": "meta/kanban/suite-timing.log"}\n'
        'LOG = Path(PATHS["log"])\n',
    ),
    (
        "a slice of a longer string",
        'BACKUP = "meta/kanban/suite-timing.log.bak"\n'
        'LOG = Path(BACKUP[: -len(".bak")])\n',
    ),
    (
        "str.format",
        'LOG = Path("meta/kanban/{}.log".format("suite-timing"))\n',
    ),
    ("with_name", 'LOG = OTHER.with_name("suite-timing.log")\n'),
    # Two more found by probing the widened guard itself, so the next
    # refactor past it has to be deliberate rather than idiomatic.
    (
        "the parts through a comprehension",
        'PARTS = ["meta", "kanban", "suite-timing.log"]\n'
        "LOG = REPO_ROOT / Path(*[part for part in PARTS])\n",
    ),
    (
        # No ".log" anywhere in the source: the prefilter that keeps this
        # guard cheap must not be the thing that decides the verdict.
        "listing the kanban directory, naming no log at all",
        'LOG = sorted((REPO_ROOT / "meta" / "kanban").iterdir())[-1]\n',
    ),
    (
        "listing the kanban directory",
        'LOG = next('
        'p for p in (REPO_ROOT / "meta" / "kanban").iterdir() '
        'if p.suffix == ".log"'
        ")\n",
    ),
    # Review cycle 2, F-105: four more single-module bindings, each one step
    # off a form already above, and each measured as missed before this was
    # written. The walrus one mattered beyond its own line: it contradicted
    # :func:`_is_pathish`' claim that a literal written where a path is used
    # is flagged either way -- one wrapper node was enough.
    (
        "the filename in a tuple-unpacking target",
        'OTHER, NAME = "x.txt", "suite-timing.log"\n'
        'LOG = REPO_ROOT / "meta" / "kanban" / NAME\n',
    ),
    (
        "the filename bound by a walrus inside the join",
        'LOG = REPO_ROOT / "meta" / "kanban" / (name := "suite-timing.log")\n',
    ),
    (
        "the filename arriving as a for-loop target",
        'NAMES = ["suite-timing.log"]\n'
        "for name in NAMES:\n"
        '    LOG = REPO_ROOT / "meta" / "kanban" / name\n',
    ),
    (
        "the filename as a class attribute",
        "class Paths:\n"
        '    LOG = "meta/kanban/suite-timing.log"\n'
        "P = Path(Paths.LOG)\n",
    ),
    # Review cycle 3, F-301/F-303/F-304: the listing and globbing rules
    # tested the call's RECEIVER only. ``os.listdir`` and ``os.scandir``
    # take the directory as an ARGUMENT and there is no ``Path.listdir``, so
    # two of the three members of :data:`_LISTERS` and one of
    # :data:`_GLOBBERS` named a spelling the rule could not reach. The
    # reviewer planted the first of them as a mutant in another guarded
    # module -- ``os.listdir`` of a hoisted kanban directory, filtered to
    # ``*.log``, under a host-state skip -- and it restored this card's own
    # defect with both guard classes green. Each form below was measured as
    # missed before the argument rule was written.
    (
        "os.listdir of the kanban directory, naming no log at all",
        "import os\n"
        'NAMES = os.listdir(REPO_ROOT / "meta" / "kanban")\n',
    ),
    (
        "os.scandir of the kanban directory",
        "import os\n"
        'ENTRIES = list(os.scandir(REPO_ROOT / "meta" / "kanban"))\n',
    ),
    (
        "listdir imported bare, so the call has no receiver at all",
        "from os import listdir\n"
        'NAMES = listdir(REPO_ROOT / "meta" / "kanban")\n',
    ),
    (
        # The planted mutant's own shape, less the skip and the read: the
        # directory hoisted to a name and listed through the module function.
        "the kanban directory hoisted to a name, then listed",
        "import os\n"
        'KANBAN = Path(__file__).resolve().parent.parent / "meta" / "kanban"\n'
        'NAMES = [n for n in os.listdir(KANBAN) if n.endswith(".log")]\n',
    ),
    (
        "glob.iglob over a kanban directory hoisted to a name",
        "import glob\n"
        'DIRECTORY = str(REPO_ROOT / "meta" / "kanban")\n'
        'HITS = glob.iglob(DIRECTORY + "/*.log")\n',
    ),
    (
        # Review cycle 3, F-303: one more wrapper node, the same shape as
        # cycle 2's walrus -- a literal standing exactly where a path is
        # used, resolved nowhere.
        "the filename behind a ternary written straight into the join",
        'LOG = REPO_ROOT / "meta" / "kanban" / ("suite-timing.log" if V2 else "old.log")\n',
    ),
    (
        "the filename behind a ternary bound to a name",
        'NAME = "suite-timing.log" if V2 else "old.log"\n'
        'LOG = REPO_ROOT / "meta" / "kanban" / NAME\n',
    ),
    (
        # The one member of :data:`_GLOBBERS` that had no control of its own
        # until the cycle-4 claim sweep asked for one per spelling.
        "a recursive glob for any log under meta/kanban",
        'LOG = next((REPO_ROOT / "meta" / "kanban").rglob("*.log"))\n',
    ),
    (
        # The second pass of :func:`_kanban_directories`, which was claimed
        # and unexercised until the sweep. Written bottom-up on purpose: one
        # pass resolves `KANBAN` only (measured), so the alias needs the
        # second, and in source order the claim would be vacuous.
        "the kanban directory aliased before it is bound, then listed",
        "import os\n"
        "NAMES = os.listdir(DIRECTORY)\n"
        "DIRECTORY = KANBAN\n"
        'KANBAN = REPO_ROOT / "meta" / "kanban"\n',
    ),
    (
        "the kanban directory kept as a class attribute, then listed",
        "import os\n"
        "class Paths:\n"
        '    KANBAN = REPO_ROOT / "meta" / "kanban"\n'
        "NAMES = os.listdir(Paths.KANBAN)\n",
    ),
    (
        # The chain :func:`_tainted_names` says its three passes settle.
        # Claimed in two docstrings since review cycle 1 and exercised by
        # nothing until the cycle-4 sweep.
        "the stem hoisted, concatenated, then looked up in a dict",
        'STEM = "suite-timing"\n'
        'NAME = STEM + ".log"\n'
        'PATHS = {"log": NAME}\n'
        'LOG = REPO_ROOT / "meta" / "kanban" / PATHS["log"]\n',
    ),
    # Review cycle 4's Critical, and the spellings the stdlib audit asked
    # about afterwards. ``os.walk`` is the one that mattered: the reviewer
    # planted it in ``tests/test_clues.py`` in MUT-L's shape -- walk the
    # kanban directory, filter to ``*.log``, skip when the host has none,
    # then assert on the live log -- and it restored this card's own defect
    # at 168 passed, reporting ``1 skipped`` on a log-less worktree. It was
    # missing from :data:`_LISTERS` and from the host-state probe at once.
    # One control per shape, because the rule judges receiver and arguments
    # by different tests.
    (
        "os.walk of the kanban directory, hoisted, filtered to *.log",
        "import os\n"
        'KANBAN = REPO_ROOT / "meta" / "kanban"\n'
        "NAMES = [\n"
        "    name\n"
        "    for _, _, names in os.walk(KANBAN)\n"
        "    for name in names\n"
        '    if name.endswith(".log")\n'
        "]\n",
    ),
    (
        "os.walk of the kanban directory, inline",
        "import os\n"
        'ENTRIES = list(os.walk(REPO_ROOT / "meta" / "kanban"))\n',
    ),
    (
        "Path.walk, the same enumerator as a method",
        'ENTRIES = list((REPO_ROOT / "meta" / "kanban").walk())\n',
    ),
    (
        "os.fwalk, the descriptor-flavoured walk",
        "import os\n"
        'KANBAN = REPO_ROOT / "meta" / "kanban"\n'
        "ENTRIES = list(os.fwalk(KANBAN))\n",
    ),
    # Review cycle 4, F-402: the directory as a KEYWORD argument. `path` is
    # the real parameter name of `os.listdir` and `os.scandir`, and the
    # bare-imported form of this survived cycle 4 at 168 passed -- both
    # halves quiet, because `_HOST_STATE_PROBE` only matched the literal
    # text `os.listdir`.
    (
        "os.listdir with the directory as a keyword argument",
        "import os\n"
        'KANBAN = REPO_ROOT / "meta" / "kanban"\n'
        "NAMES = os.listdir(path=KANBAN)\n",
    ),
    (
        "listdir imported bare, with the directory as a keyword argument",
        "from os import listdir\n"
        'KANBAN = REPO_ROOT / "meta" / "kanban"\n'
        'NAMES = [n for n in listdir(path=KANBAN) if n.endswith(".log")]\n',
    ),
    (
        "os.scandir with the directory as a keyword argument",
        "import os\n"
        'ENTRIES = list(os.scandir(path=REPO_ROOT / "meta" / "kanban"))\n',
    ),
    # The two ``glob`` module functions the audit put on the surface. Nobody
    # reaches for them often; the point is that the reason to exclude them
    # would have had to be written down, and there was not one.
    (
        "glob.glob over a kanban directory hoisted to a name",
        "import glob\n"
        'KANBAN = REPO_ROOT / "meta" / "kanban"\n'
        'HITS = glob.glob(str(KANBAN) + "/*.log")\n',
    ),
    (
        # The pattern names no log on purpose: with `suite-timing.log` in it
        # the string rule caught this source whether or not `glob0` was in
        # :data:`_GLOBBERS`, so the control measured nothing -- see
        # ``test_the_control_for_each_spelling_depends_on_the_set``, which
        # was red at `glob0` until this line changed.
        "glob.glob0 of the kanban directory",
        "import glob\n"
        'KANBAN = REPO_ROOT / "meta" / "kanban"\n'
        'HITS = glob.glob0(str(KANBAN), "latest.log")\n',
    ),
    (
        "glob.glob1 of the kanban directory",
        "import glob\n"
        'KANBAN = REPO_ROOT / "meta" / "kanban"\n'
        'HITS = glob.glob1(str(KANBAN), "*.log")\n',
    ),
    (
        # The wrapper shape `_unwrapped` could not peel until this cycle: a
        # no-argument method on the directory itself. The audit is what
        # surfaced it -- `resolve` and `absolute` are on the stdlib surface
        # and had to be classified, and KIND_WRAPPER was the honest answer.
        "the kanban directory resolved, then listed",
        "import os\n"
        'KANBAN = REPO_ROOT / "meta" / "kanban"\n'
        "NAMES = os.listdir(KANBAN.resolve())\n",
    ),
    # Review cycle 5's F-501, and the half four audited cycles left alone:
    # the audit derived the spellings that READ a directory and nothing
    # derived the spellings that BUILD one, so only the `/` BinOp was
    # recognised. Every source below returned `[]` from this guard before
    # CARD-239, and NONE of them names a log -- deliberately, because the two
    # `os.path.join`/`joinpath` entries that were already in this tuple were
    # caught through their log *filename* and so measured nothing about the
    # construction spelling (the F-403 shape again, one layer out).
    # `test_the_control_for_each_spelling_depends_on_the_set` covers the
    # joiners now and is what holds that line.
    (
        "os.path.join of the kanban directory, naming no log at all",
        "import os\n"
        'NAMES = os.listdir(os.path.join(str(REPO_ROOT), "meta", "kanban"))\n',
    ),
    (
        # The measured shape from CARD-238's cycle-5 review, compounded with
        # the except-handler bound into a mutant that survived at 250 passed.
        "os.path.join hoisted to a name, then listed",
        "import os\n"
        'KANBAN = os.path.join(str(REPO_ROOT), "meta", "kanban")\n'
        "NAMES = os.listdir(KANBAN)\n",
    ),
    (
        "os.path.join rooted at the process's own directory",
        "import os\n"
        'NAMES = os.listdir(os.path.join(os.getcwd(), "meta", "kanban"))\n',
    ),
    (
        "Path.joinpath of the directory, then iterdir",
        'ENTRIES = list(REPO_ROOT.joinpath("meta", "kanban").iterdir())\n',
    ),
    (
        # Nobody had thought of this one: the audit's behavioural probe
        # named it, exactly as cycle 5's audit named `fwalk`, `glob0` and
        # `glob1`. `PurePath.with_segments` builds a path out of segments
        # and discards the receiver, so it reaches the directory from any
        # base at all.
        "Path.with_segments, which the audit named and nobody had written",
        "import os\n"
        'NAMES = os.listdir(REPO_ROOT.with_segments("meta", "kanban"))\n',
    ),
    (
        # The constructor given several segments assembles rather than
        # re-spells. It is KIND_WRAPPER, and the rule reads the joiner and
        # wrapper projections as one union for exactly this reason.
        "the path constructor given the components as separate arguments",
        "import os\n"
        'NAMES = os.listdir(Path(REPO_ROOT, "meta", "kanban"))\n',
    ),
    (
        # `os.sep.join` is `str.join`, the same NAME the audit classifies,
        # with its components in a list instead of in the argument list.
        "the components joined through a separator string",
        "import os\n"
        'NAMES = os.listdir(os.sep.join([str(REPO_ROOT), "meta", "kanban"]))\n',
    ),
    (
        # The globbing rule's end of the same hole: its directory test is
        # the loose one, and the loose one went through `_leftmost`, which
        # knew `/` and `+` and not a construction call.
        "a glob under a kanban directory built by os.path.join",
        "import glob\n"
        "import os\n"
        'KANBAN = os.path.join(str(REPO_ROOT), "meta", "kanban")\n'
        'HITS = glob.glob(os.path.join(KANBAN, "*.log"))\n',
    ),
)


def _needs_a_spelling_this_host_lacks(source: str) -> list[str]:
    """Classified spellings ``source`` calls that this interpreter does not offer.

    A control for ``glob.glob0`` cannot be caught on an interpreter without
    ``glob0``: :func:`_guard_set` intersects with the live surface, so the
    spelling has dropped out of the set the rule consults -- which is
    F-502's fix working, not failing. Such a case is **not collected** on
    that host rather than skipped there: a skip would be a verdict nobody
    reads, and this card's whole subject is that a skip on host state is a
    hole. The number of controls therefore varies with the interpreter, and
    :data:`REINTRODUCTIONS` -- the full tuple -- stays the record of what
    has been measured.
    """
    surface = frozenset(_stdlib_directory_surface())
    return sorted(
        {
            name
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Call)
            and (name := _call_name(node)) is not None
            and STDLIB_DIRECTORY_SURFACE.get(name, (KIND_NEITHER, ""))[0]
            != KIND_NEITHER
            and name not in surface
        }
    )


#: :data:`REINTRODUCTIONS` less the controls whose spelling this interpreter
#: does not have. Equal to it on any host that offers the whole surface.
REINTRODUCTIONS_ON_THIS_HOST: tuple[tuple[str, str], ...] = tuple(
    (name, source)
    for name, source in REINTRODUCTIONS
    if not _needs_a_spelling_this_host_lacks(source)
)


# The forms this guard is measured NOT to catch. Held as controls rather than
# as a sentence in a docstring, because on this card a stated coverage has
# three times outrun the real one: a prose disclosure cannot go red when it
# stops being true, and each of these turns red the day the resolver grows
# past it, which is the day the docstring needs editing.
#
# Measured 2026-10-16 against this module's own guard, each by executing it.
MEASURED_STRUCTURAL_MISSES: tuple[tuple[str, str], ...] = (
    (
        # The whole point of the behavioural comparison: one module cannot
        # see what another one holds.
        "a path imported from another module",
        "from timing_paths import TIMING_LOG\n"
        "def test_x() -> None:\n"
        "    assert TIMING_LOG.read_text()\n",
    ),
    (
        # No log name anywhere in the source, so there is nothing to resolve.
        "a path read out of the environment at run time",
        "import os\n"
        "from pathlib import Path\n"
        'LOG = Path(os.environ["CARD238_LOG"])\n',
    ),
    (
        "a stem rebuilt by arithmetic",
        'LOG = REPO_ROOT / "meta" / "kanban" / "gol.gnimit-etius"[::-1]\n',
    ),
    (
        # Review cycle 2: the sandbox exemption borrowed by shape. The
        # exemption is keyed on the join's shape -- a join rooted at a
        # parameter -- and a shape is easier to borrow than a name, so a
        # helper called with a module constant passes the structural guard.
        # It dies on outcome instead, and only while the helper lives in a
        # module the comparison runs; see the class docstrings.
        "a helper whose root is a parameter, called with a constant",
        "def _log_under(root: Path) -> Path:\n"
        '    return root / "meta" / "kanban" / "suite-timing.log"\n'
        "LOG = _log_under(REPO_ROOT)\n",
    ),
    (
        # Review cycle 3, F-305: the forms this guard catches are each
        # caught on their own and do NOT compose. The taint pass carries a
        # value only when the folded string already holds the stem, so a
        # stem split so that neither half holds it resolves to nothing.
        # ``STEM = "suite-timing"`` then ``NAME = STEM + ".log"`` *is*
        # caught -- the three-pass chain settles that one -- which is why
        # the docstring used to read as though the two composed.
        "the stem split across two names, neither half holding it",
        'A = "suite"\n'
        'B = "-timing.log"\n'
        "NAME = A + B\n"
        'LOG = REPO_ROOT / "meta" / "kanban" / NAME\n',
    ),
    (
        # Review cycle 5's third Minor, measured and recorded rather than
        # fixed. `_unwrapped` peels a wrapper call of exactly ONE argument,
        # so a two-argument wrapper is not seen through. The audit polices
        # WHICH NAMES are wrappers; nothing polices which call SHAPES the
        # peel accepts, and widening the peel to "the first argument of any
        # arity" would hand `Path(ROOT, "meta", "kanban")` to the listing
        # rule as `ROOT`. CARD-239 made the constructors a component chain
        # instead (`_component_arguments`), which is the other half of the
        # problem and not this one. Red the day the peel grows, which is the
        # day the sentence describing the bound needs editing.
        "a two-argument wrapper call, which the peel does not accept",
        "import os\n"
        'KANBAN = REPO_ROOT / "meta" / "kanban"\n'
        "NAMES = os.listdir(os.path.relpath(KANBAN, REPO_ROOT))\n",
    ),
    (
        # The non-claim `popen`/`system`'s classification now states, pinned
        # from the other side. Their old exclusion reasons -- "it names no
        # directory" and "not the filesystem" -- were both false of
        # `os.popen("ls " + str(KANBAN))`, which is a directory listing by
        # any reading. The honest reason is that these rules do not read
        # command text, and this is the control that makes the reason
        # measurable rather than plausible.
        "a directory listed by shelling out through os.popen",
        "import os\n"
        'KANBAN = REPO_ROOT / "meta" / "kanban"\n'
        'NAMES = os.popen("ls " + str(KANBAN)).read()\n',
    ),
    (
        # And the same through `subprocess`, which is outside
        # :data:`_SURFACE_NAMESPACES` entirely -- excluded by not being
        # looked at. That matters because shelling out to list files is
        # **this module's own idiom**: six `git ls-files` listings run
        # behind :func:`_files_under_guard`. Auditing `dir(subprocess)`
        # would put thirty names in the table whose classification nothing
        # could measure either, so the namespace list stays as it is and
        # the non-claim is stated here, where it goes red if a rule ever
        # starts reading argv.
        "a directory listed by shelling out through subprocess",
        "import subprocess\n"
        'KANBAN = REPO_ROOT / "meta" / "kanban"\n'
        'OUT = subprocess.run(["ls", str(KANBAN)], capture_output=True)\n',
    ),
)

# One listing source per :data:`_PATH_WRAPPERS` member, with the wrapper
# substituted in, so the set and the controls cannot drift apart: a member
# added to the set is exercised by ``test_every_path_wrapper_is_seen_through``
# on the next run. A module constant for the same reason
# :data:`REINTRODUCTIONS` is one -- written inline it would be a call
# argument naming the directory.
WRAPPED_DIRECTORY_SOURCE = (
    "import os\n"
    'KANBAN = REPO_ROOT / "meta" / "kanban"\n'
    "NAMES = os.listdir({wrapper}(KANBAN))\n"
)

#: The same, in the other shape a wrapper is written: a no-argument method on
#: the directory. ``os.listdir(KANBAN.resolve())`` was a miss until this
#: cycle, which is why the peel now tries both and the control covers both.
WRAPPED_DIRECTORY_METHOD_SOURCE = (
    "import os\n"
    'KANBAN = REPO_ROOT / "meta" / "kanban"\n'
    "NAMES = os.listdir(KANBAN.{wrapper}())\n"
)

#: The other side of :data:`_PATH_WRAPPERS`, and the half review cycle 4's
#: F-403 found missing: a call that is *not* a wrapper must not be peeled,
#: because peeling one that names a different directory is how
#: ``os.listdir(dirname(KANBAN))`` would start being reported and how
#: ``os.listdir(bogus(root) / "meta" / "kanban")`` would reach the
#: caller-root exemption.
#:
#: The sentence that stood here said "each of these is a measured miss
#: *because* the name is classified KIND_NEITHER; let one into the set and
#: the control goes red", and **it was false of two of the three** --
#: CARD-239's claim sweep measured it, and it is false on CARD-238 as merged
#: too, so it is a cycle-5 survivor rather than something this card broke.
#: Only the ``dirname`` entry's verdict depends on the membership. The other
#: two are misses for an unrelated reason: ``KANBAN.joinpath("cards")`` and
#: ``KANBAN.with_name("profiling")`` are one-*argument* attribute calls, and
#: the peel's one-argument branch takes the ARGUMENT -- the string
#: ``"cards"`` -- while its no-argument branch does not apply, so letting
#: either name into the set changes nothing at all. That is the F-403 shape
#: one more layer out: a corpus whose comment claimed a discriminating power
#: two thirds of it did not have.
#:
#: Both halves are corrected rather than deleted. The entries stay, because
#: "a subdirectory and a sibling are not this directory" is a real claim and
#: F-104's family; which of them the *set* decides is recorded as an
#: equality in :data:`NON_WRAPPERS_THE_SET_DECIDES`, so it goes red if the
#: peel grows; and the discriminating power the comment claimed is now
#: supplied by a control generated from the table over every
#: path-arithmetic name, in both wrapper shapes
#: (``test_a_path_arithmetic_name_is_peeled_only_if_it_is_in_the_set``).
NOT_A_PATH_WRAPPER: tuple[tuple[str, str], ...] = (
    (
        "dirname, which names the directory above",
        "import os\n"
        'KANBAN = REPO_ROOT / "meta" / "kanban"\n'
        "NAMES = os.listdir(os.path.dirname(KANBAN))\n",
    ),
    (
        "joinpath, which names a directory below",
        "import os\n"
        'KANBAN = REPO_ROOT / "meta" / "kanban"\n'
        'NAMES = os.listdir(KANBAN.joinpath("cards"))\n',
    ),
    (
        "with_name, which names a sibling",
        "import os\n"
        'KANBAN = REPO_ROOT / "meta" / "kanban"\n'
        'NAMES = os.listdir(KANBAN.with_name("profiling"))\n',
    ),
)

#: Of :data:`NOT_A_PATH_WRAPPER`, the entries whose verdict actually depends
#: on :data:`_PATH_WRAPPERS`: add the name and the control goes red. Measured
#: 2026-10-17, one of three -- the figure the old comment on that corpus got
#: wrong. An equality, not a sentence, so a peel that grows to accept a
#: one-argument attribute call's receiver makes this red and the paragraph
#: above the thing to edit.
NON_WRAPPERS_THE_SET_DECIDES: tuple[str, ...] = ("dirname",)

#: The exact reason text the table files pure path arithmetic under, so the
#: generated non-wrapper controls can be parametrised from the table rather
#: than from a list written here. Asserted to BE a reason in the table
#: (``test_a_path_arithmetic_name_is_peeled_only_if_it_is_in_the_set``'s
#: parametrisation would otherwise be empty, and the test asserts it is not).
_PATH_ALGEBRA_REASON = (
    "pure path-string arithmetic; it consults no filesystem and it "
    "assembles no directory out of components"
)

#: Every name the table files under that reason. Generated controls below
#: assert each one is NOT peeled and WOULD be if it were let into the
#: wrappers -- the discriminating half the three hand-written entries above
#: only had for one of themselves.
PATH_ARITHMETIC_NAMES: tuple[str, ...] = tuple(
    sorted(
        name
        for name, (_, reason) in STDLIB_DIRECTORY_SURFACE.items()
        if reason == _PATH_ALGEBRA_REASON
    )
)

# Mentions that are not reads. A grep-based guard would fail every one of
# these, which is why the guard parses instead.
INNOCENT_MENTIONS: tuple[tuple[str, str], ...] = (
    ("a comment", "# suite-timing.log is host state; no test may read it\nX = 1\n"),
    (
        "a docstring",
        '"""The appended line keeps suite-timing.log\'s format."""\n',
    ),
    ("the stem bound to a constant", 'LIVE_LOG_STEM = "suite-timing"\n'),
    (
        "a comment inside a test",
        "def test_x() -> None:\n"
        "    # the log (suite-timing.log) is not consulted here\n"
        "    assert True\n",
    ),
    # The structural exemption, pinned as a test rather than left implicit:
    # a join rooted at a *parameter* cannot reach the owner's log, because
    # the root is whatever the caller passed -- this module's sandbox helper
    # passes a tmp_path. Hoisting the root to a module constant removes the
    # exemption, which the next case asserts.
    (
        "a sandbox path built under a caller's root",
        'STEM = "suite-timing"\n'
        "def write(root: Path, text: str) -> None:\n"
        '    (root / "meta" / "kanban" / f"{STEM}.log").write_text(text)\n',
    ),
    (
        "the stem compared, not joined",
        'STEM = "suite-timing"\n'
        "def test_x(name: str) -> None:\n"
        "    assert STEM in name\n",
    ),
    # Review cycle 2, F-104: the listing rule fired on any receiver whose
    # *text* held both words, so this -- a card-registry walk, of which this
    # repo invites many -- was reported as a live-log read, with a message
    # telling its author to assert the log format instead.
    (
        "listing a directory under meta/kanban, naming no log",
        "NAMES = sorted("
        'p.name for p in (REPO_ROOT / "meta" / "kanban" / "cards").iterdir()'
        ")\n",
    ),
    # Review cycle 3: the argument rule written for F-301 has to stay as
    # narrow as F-104 made the receiver rule. A name bound to the kanban
    # directory *is* that directory; a path built under it is not, by either
    # spelling -- and an argument rooted at a caller-supplied parameter is
    # exempt for the same reason the receiver form is.
    (
        "a hoisted kanban directory used to list a subdirectory",
        'KANBAN = REPO_ROOT / "meta" / "kanban"\n'
        'NAMES = sorted(p.name for p in (KANBAN / "cards").iterdir())\n',
    ),
    (
        "os.listdir of a directory under meta/kanban",
        "import os\n"
        'NAMES = os.listdir(REPO_ROOT / "meta" / "kanban" / "cards")\n',
    ),
    (
        "os.listdir of a kanban directory under the caller's root",
        "import os\n"
        "def names(root: Path) -> list[str]:\n"
        '    return os.listdir(root / "meta" / "kanban")\n',
    ),
)

# The untracked scratch file review cycle 2 measured (F-103): tracked by
# nobody, listed by no `git ls-files`, and enough to turn the behavioural
# guard red with a diagnostic pointing at a sandbox outcome diff rather than
# at itself. A module constant for the same reason REINTRODUCTIONS is one:
# written inline it would be a call argument naming the log, and this module
# would be its own first offender.
UNTRACKED_SCRATCH_SOURCE = (
    'LOG = REPO_ROOT / "meta" / "kanban" / "suite-timing.log"\n'
)

# One generated host-state skip per :data:`_HOST_STATE_PROBES` member, for
# the same reason :data:`WRAPPED_DIRECTORY_SOURCE` is generated from its set:
# a member added to the set is exercised on the next run rather than taken on
# trust. A module constant, not an inline literal, like every other corpus
# here.
PROBE_GATED_SKIP = (
    "import pytest\n"
    "def test_x() -> None:\n"
    "    if not LOG.{probe}():\n"
    '        pytest.skip("absent")\n'
    "    assert True\n"
)

FABRICATED_SKIP = (
    "import pytest\n"
    "@pytest.mark.skipif(not LOG.exists(), reason=\"absent\")\n"
    "def test_x() -> None:\n    pass\n"
)

# Every other way a test, or this whole module, can go quiet. Review cycle 1,
# F-003: the detector caught the bare decorator and missed five of these, the
# first of them pytest's own documented way to mark a whole module. Review
# cycle 2, F-102/F-106: it still missed three, including pytest's *imperative*
# module skip, which silences both guard classes at once and reads as
# `1 skipped, exit 0` on the log-less host that hid the original defect.
CONDITIONAL_SILENCES: tuple[tuple[str, str], ...] = (
    (
        "module-level pytestmark",
        "import pytest\n"
        "pytestmark = pytest.mark.skipif(not LOG.exists(), reason=\"absent\")\n"
        "def test_x() -> None:\n    pass\n",
    ),
    (
        "an in-body pytest.skip",
        "import pytest\n"
        "def test_x() -> None:\n"
        "    if not LOG.exists():\n"
        "        pytest.skip(\"absent\")\n"
        "    assert LOG.read_text()\n",
    ),
    (
        "an aliased decorator",
        "from pytest import mark\n"
        "skipper = mark.skipif\n"
        "@skipper(not LOG.exists(), reason=\"absent\")\n"
        "def test_x() -> None:\n    pass\n",
    ),
    (
        "a conditional xfail",
        "import pytest\n"
        "@pytest.mark.xfail(not LOG.exists(), reason=\"absent\")\n"
        "def test_x() -> None:\n    assert LOG.read_text()\n",
    ),
    (
        "an early return",
        "def test_x() -> None:\n"
        "    if not LOG.is_file():\n"
        "        return\n"
        "    assert LOG.read_text()\n",
    ),
    # Review cycle 2, F-102: pytest's own imperative module skip. Executed as
    # a mutant, it made pytest report `ERROR: found no collectors` for BOTH
    # guard classes -- it sits above every test in the file, so the
    # behavioural half cannot help either: the comparison is itself one of
    # the tests it silences. On a host without the log, which is the fresh
    # worktree that hid the original defect, it reads as `1 skipped, exit 0`.
    (
        "a module-level imperative skip on host state",
        "import pytest\n"
        "if not LOG.exists():\n"
        '    pytest.skip("the whole module goes quiet", allow_module_level=True)\n'
        "def test_x() -> None:\n    assert LOG.read_text()\n",
    ),
    (
        "an unconditional module-level skip",
        "import pytest\n"
        'pytest.skip("not here", allow_module_level=True)\n'
        "def test_x() -> None:\n    assert LOG.read_text()\n",
    ),
    # Review cycle 2, F-106: hoisting the probe out of the condition turned
    # the detector off -- cycle 1's decisive miss (a name carried past a
    # text-level test) one layer over.
    (
        "a skip gated on a hoisted exists() flag",
        "import pytest\n"
        "HAVE_LOG = LOG.exists()\n"
        "def test_x() -> None:\n"
        "    if not HAVE_LOG:\n"
        '        pytest.skip("absent")\n'
        "    assert LOG.read_text()\n",
    ),
    (
        # Not host state in the filesystem sense, and reported anyway: a mark
        # condition is reported whatever it is keyed on. Held here as a
        # control so the rule's real width is pinned rather than described --
        # see :func:`_conditional_silences`.
        "a platform skipif, wider than host state and reported too",
        "import pytest\n"
        "import sys\n"
        '@pytest.mark.skipif(sys.platform == "win32", reason="posix only")\n'
        "def test_x() -> None:\n    pass\n",
    ),
)

# Silence this detector must *not* claim, or `declared == []` becomes
# impossible to keep and the guard gets switched off instead of obeyed. Each
# of these is also the control for a sentence in
# :func:`_conditional_silences`' statement of its limits.
NOT_A_CONDITIONAL_SILENCE: tuple[tuple[str, str], ...] = (
    (
        "an unconditional xfail",
        "import pytest\n"
        "@pytest.mark.xfail(reason=\"a known defect, not a host\")\n"
        "def test_x() -> None:\n    assert False\n",
    ),
    (
        "an early return on a value",
        "def test_x(n: int) -> None:\n"
        "    if n > 3:\n"
        "        return\n"
        "    assert n\n",
    ),
    (
        "a helper that probes the filesystem",
        "def _artefacts(root: Path) -> list[Path]:\n"
        "    if not root.exists():\n"
        "        return []\n"
        "    return sorted(root.glob(\"*.txt\"))\n",
    ),
    (
        # The negative control for the module-level pass above: a module skip
        # keyed on the interpreter is a statement about the code's
        # requirements, not about this host's filesystem, and is not claimed.
        "a module-level skip on the interpreter version",
        "import pytest\n"
        "import sys\n"
        "if sys.version_info < (3, 14):\n"
        '    pytest.skip("needs 3.14", allow_module_level=True)\n'
        "def test_x() -> None:\n    pass\n",
    ),
    (
        # The stated limit that had no control, and the negative control for
        # the probe set at the same time: an environment variable is not
        # filesystem state, `os.getenv` is classified KIND_NEITHER for that
        # reason, and this card's env-var survivor is still open and still
        # documented as open at :func:`_live_log_references`. Let `getenv`
        # into :data:`_HOST_STATE_PROBES` and this goes red.
        "a skip keyed on an environment variable",
        "import os\n"
        "import pytest\n"
        'if not os.getenv("CARD238_LOG"):\n'
        '    pytest.skip("no log configured", allow_module_level=True)\n'
        "def test_x() -> None:\n    pass\n",
    ),
    (
        # The other stated limit without one: the rules here read `if`
        # conditions and mark conditions, so a skip reached through an
        # `except` handler is a miss. Recorded as a bound rather than fixed
        # -- the mechanism is outside this cycle's scope -- and red the day
        # the detector grows past it.
        "a skip from an except handler rather than an if",
        "import pytest\n"
        "def test_x() -> None:\n"
        "    try:\n"
        "        text = LOG.read_text()\n"
        "    except FileNotFoundError:\n"
        '        pytest.skip("absent")\n'
        "    assert text\n",
    ),
)


#: Every silence the detector reports in the guarded tree *outside this
#: module*, measured 2026-10-17 by running :func:`_conditional_silences` over
#: all of :func:`_guarded_sources`.
#:
#: Not "every host-state silence", which is what this header said over four
#: entries one of which it itself called "not filesystem state at all"
#: (review cycle 5's F-405 -- the same false-claim habit in miniature, in the
#: card whose subject was false claims). The detector is wider than host
#: state in its mark half on purpose, and the baseline has to be a record of
#: what it reports, not of what a sentence here wishes it reported. No count
#: is written either, for the reason the module docstring no longer carries
#: one: a number in prose is the smallest version of this card's defect.
#:
#: Review cycle 3 (F-301, F-307) measured the asymmetry this closes: the path
#: guard judged every guarded source while the silence guard judged one
#: module -- 221 against 1 on 2026-10-16, so all but one of them had a single
#: defence -- and the mutant that got through was a
#: host-state skip in another one of them, which this detector reports
#: correctly and nothing ran it against. It is run against all of them now,
#: and what it finds has to equal this list exactly: a new one anywhere in
#: the tree makes
#: ``test_the_host_state_silences_elsewhere_are_exactly_the_measured_ones``
#: red, and so does fixing one of these without striking it off. CARD-239
#: struck two by fixing them, and the equality was red in that direction
#: first -- measured, not assumed.
MEASURED_SILENCES_ELSEWHERE: tuple[tuple[str, str, str], ...] = (
    # A design-system directory that exists on the owner's host and in every
    # checkout, and is absent only from an installed wheel -- which is what
    # its reason says. It belongs to forge:ui's card rather than to this one:
    # the skip is a statement about packaging, and whether the admin panel's
    # token mirror should be checked against a directory the package does not
    # ship is that card's question, not a hole in this guard. Recorded, with
    # the reason corrected: it is NOT the host-state shape the two entries
    # CARD-239 struck were.
    (
        "tests/test_admin_design_tokens.py",
        "test_the_served_tokens_are_the_design_systems_tokens",
        "not _DESIGN.exists()",
    ),
    # And one that is not filesystem state at all: a `skipif` mark is reported
    # whatever it is keyed on, which is the width review cycle 2 (F-106)
    # corrected the detector's name and docstring to admit and which the
    # platform skipif in :data:`CONDITIONAL_SILENCES` pins. Recorded here so
    # that width is visible in the baseline too, not only in a control.
    (
        "tests/test_web_submission.py",
        "test_an_out_under_an_unwritable_directory_is_reported_as_a_failure_page",
        "hasattr(os, 'geteuid') and os.geteuid() == 0",
    ),
)

#: The two entries CARD-239 struck from the baseline above by fixing them,
#: kept as a record of what was fixed and why -- a struck entry leaves no
#: trace otherwise, and the next reader of the baseline would have no way to
#: tell a fixed silence from one that was never there.
#:
#: Both were in ``tests/test_sourcing_image.py`` and both were **this card's
#: own defect one module over**: a skip keyed on the presence of the picture
#: corpus, which is 25 *committed* files (``git ls-files pictures`` lists 25),
#: so they could only ever fire on a checkout that had lost a tracked file --
#: the one case the test most needs to report. The same module asserts the
#: corpus is exactly those 25 files unconditionally a thousand lines above,
#: so the skips contradicted their own module as well.
#:
#: Not a claim about anything in the tree; the claim is the equality above,
#: which was verified red with these two fixed and unstruck before they were
#: struck.
SILENCES_FIXED_BY_CARD_239: tuple[tuple[str, str, str], ...] = (
    (
        "tests/test_sourcing_image.py",
        "test_binarize_guard_sends_degenerate_threshold_conversion_to_dither_for_line_art",
        "not picture.is_file()",
    ),
    (
        "tests/test_sourcing_image.py",
        "test_binarize_threshold_corpus_needs_no_more_nudges_than_dither",
        "not PICTURES.is_dir()",
    ),
)

#: The territories this module is answerable for, repo-relative. ``tests/``
#: because that is where a test lives, and ``meta/profiling/`` because review
#: cycle 2 (F-101) put this card's own defect there and watched it survive all
#: 41 guards: the ranker is in this card's ``Touches:``, the declined
#: ``--check-log`` subcommand would put the log's path constant in it, and the
#: AST walk did not go there.
GUARDED_DIRECTORIES = ("tests", "meta/profiling")

#: The sandbox's copy of the parent's tracked list. ``git ls-files`` returns
#: rc=128 inside the sandbox -- it is not a checkout -- so before this the
#: walk fallback was not a rare path but the one the behavioural guard always
#: took, and the walk admits untracked files (review cycle 2, F-103).
#:
#: It is read at the sandbox root and **ignored at the real repository root**
#: (review cycle 5's F-306): the file is gitignored, so a stray copy of it in
#: a worktree is host state, and consulting it there would let an untracked
#: file replace ``git ls-files`` as the set both guards judge -- the exact
#: dependence this card removes, in the resolution order of the guard that
#: removes it. :func:`_files_under_guard` takes the root it must not trust as
#: a parameter so that the rule is measurable without writing anything into
#: the repository, and
#: ``test_a_manifest_at_the_repo_root_is_ignored`` measures it in both
#: directions.
SANDBOX_MANIFEST_NAME = ".card238-tracked"


def _tracked_under_guard(root: Path) -> list[str]:
    """Repo-relative tracked paths under :data:`GUARDED_DIRECTORIES`.

    ``[]`` when git cannot answer, which the callers treat as "ask something
    else" rather than as "there are none".
    """
    try:
        listed = subprocess.run(
            ["git", "ls-files", "-z", "--", *GUARDED_DIRECTORIES],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if listed.returncode != 0:
        return []
    return sorted(
        {
            name
            for name in listed.stdout.split("\0")
            if name and (root / name).is_file()
        }
    )


def _files_under_guard(
    root: Path = REPO_ROOT, untrusted_root: Path = REPO_ROOT
) -> list[str]:
    """The file set both guards judge, repo-relative, in one resolution order.

    The manifest first, so that inside the sandbox the set is the parent's
    tracked list and not whatever happens to be on this disk; then
    ``git ls-files``, which is the answer in a real checkout; then the walk,
    for a checkout with no git at all -- a guard that silently inspects
    nothing is worse than one that inspects a little too much, and
    ``test_the_walk_actually_sees_both_guarded_trees`` is what keeps the choice
    honest.

    Tracked rather than on-disk, in every branch that can tell the
    difference: an untracked scratch file exists on one machine and not the
    next, so letting it decide a verdict would put the host dependence back
    inside the guard meant to remove it (cycle 1 F-008, cycle 2 F-103).

    ``untrusted_root`` is the one root whose manifest is **not** read -- the
    real repository, where the file is gitignored and so is host state
    (review cycle 5's F-306). It is a parameter rather than a comparison
    against :data:`REPO_ROOT` so that the rule can be measured by planting a
    manifest in a ``tmp_path`` and naming that tmp_path untrusted, instead of
    by writing a gitignored file into the owner's checkout to watch what
    happens.
    """
    manifest = root / SANDBOX_MANIFEST_NAME
    if manifest.is_file() and root.resolve() != untrusted_root.resolve():
        return [
            name
            for name in manifest.read_text(encoding="utf-8").split("\n")
            if name and (root / name).is_file()
        ]
    tracked = _tracked_under_guard(root)
    if tracked:
        return tracked
    return sorted(
        str(path.relative_to(root))
        for directory in GUARDED_DIRECTORIES
        for path in (root / directory).rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    )


def _guarded_sources(root: Path = REPO_ROOT) -> list[Path]:
    """Every ``*.py`` under ``root`` whose content the repo is answerable for."""
    return sorted(
        {root / name for name in _files_under_guard(root) if name.endswith(".py")}
    )


class TestSuiteTiming_NoTestReadsTheLiveLog:
    """AC-1: no tracked module here reaches ``meta/kanban/suite-timing.log``.

    The structural half of AC-1, over the two territories the repo is
    answerable for (:data:`GUARDED_DIRECTORIES`). It resolves names before
    judging them, so the ten re-introductions review cycle 1 found invisible
    and the four review cycle 2 found are positive controls here
    (:data:`REINTRODUCTIONS`).

    Its limits are controls too (:data:`MEASURED_STRUCTURAL_MISSES`), not a
    sentence. The earlier wording here said the rest "is caught by outcome
    instead, in the class below"; review cycle 2 disproved that with three
    executed mutants and it is corrected at :func:`_live_log_references`,
    which states per form what the comparison does and does not reach. On
    this card a stated coverage outran the real one three cycles running --
    every time because prose cannot go red.
    """

    def test_no_guarded_module_reaches_for_the_live_log(self) -> None:
        offenders = {
            str(path.relative_to(REPO_ROOT)): references
            for path in _guarded_sources()
            if (references := _live_log_references(path.read_text(encoding="utf-8")))
        }
        assert offenders == {}, (
            "a tracked module under tests/ or meta/profiling/ reaches for the "
            "gitignored live timing log, so a verdict here depends on the host "
            f"rather than on the code: {offenders}. Assert the format against "
            "entries the test constructs instead (CARD-238)."
        )

    def test_the_walk_actually_sees_both_guarded_trees(self) -> None:
        # Guards the guard: a mistyped glob, a `git ls-files` that answers
        # for the wrong tree, or a manifest naming files that are not there
        # would make the test above pass by inspecting nothing at all.
        walked = _guarded_sources()
        assert len(walked) > 100, len(walked)
        assert Path(__file__).resolve() in {path.resolve() for path in walked}
        # And that it sees the second territory, which is where review cycle
        # 2 put the defect that survived every guard (F-101).
        assert RANKER_PATH.resolve() in {path.resolve() for path in walked}

    @pytest.mark.parametrize(
        "source", [source for _, source in REINTRODUCTIONS_ON_THIS_HOST],
        ids=[name for name, _ in REINTRODUCTIONS_ON_THIS_HOST],
    )
    def test_every_way_of_reintroducing_the_read_is_caught(self, source: str) -> None:
        assert _live_log_references(source) != []

    @pytest.mark.parametrize(
        "source", [source for _, source in INNOCENT_MENTIONS],
        ids=[name for name, _ in INNOCENT_MENTIONS],
    )
    def test_a_mention_that_is_not_a_read_is_not_caught(self, source: str) -> None:
        assert _live_log_references(source) == []

    def test_every_listing_and_globbing_spelling_has_a_control(self) -> None:
        # The claim the comment on :data:`_LISTERS` makes, pinned instead of
        # written. Review cycle 3's gating finding was that the set named
        # three listers while the rule could fire on one, and nothing could
        # go red over the difference; a member added to either set from here
        # on without a control makes this red rather than making the comment
        # wrong.
        caught = [
            source
            for _, source in REINTRODUCTIONS_ON_THIS_HOST
            if _live_log_references(source) != []
        ]
        uncontrolled = sorted(
            spelling
            for spelling in _GLOBBERS | _LISTERS | _JOINERS
            if not any(
                re.search(rf"\b{spelling}\(", source) for source in caught
            )
        )
        assert uncontrolled == [], (
            "a listing, globbing or joining spelling is named in "
            "_LISTERS/_GLOBBERS/_JOINERS with no positive control that the "
            f"guard actually catches it: {uncontrolled}"
        )

    @pytest.mark.parametrize("spelling", sorted(_GLOBBERS | _LISTERS | _JOINERS))
    def test_the_control_for_each_spelling_depends_on_the_set(
        self, spelling: str
    ) -> None:
        # One step past "has a control": a control that would be caught
        # anyway is not a control for this spelling. At least one
        # :data:`REINTRODUCTIONS` source per member has to be caught WITH
        # the member in the set and missed WITHOUT it, which is the only way
        # a positive control can be said to measure the member rather than
        # the rest of the rule.
        #
        # Written because this cycle's own first attempt failed it: the
        # ``glob0`` control named ``suite-timing.log`` as its pattern, so the
        # string rule caught it with ``glob0`` removed from
        # :data:`_GLOBBERS` and the control proved nothing -- review cycle
        # 4's F-403 shape, in the pass that was fixing F-403. This test was
        # red at ``glob0`` before the control was changed to a pattern that
        # names no log. CARD-239 widened it to the joiners, where review
        # cycle 5's F-501 was: the `os.path.join` and `joinpath` sources in
        # :data:`REINTRODUCTIONS` were both caught through their log *name*,
        # so they measured nothing about the construction spelling at all.
        #
        # The narrowed set is a VALUE now, not a `setattr` on this module
        # restored in a `finally`. That rebinding was correct in a serial
        # run and wrong in kind: under `pytest-xdist` or `pytest-randomly`
        # another test calling `_live_log_references` inside the window
        # would have consulted the narrowed set.
        narrowed = SPELLINGS.without(spelling)
        discriminating = []
        for name, source in REINTRODUCTIONS_ON_THIS_HOST:
            if _live_log_references(source) == []:
                continue
            if _live_log_references(source, spellings=narrowed) == []:
                discriminating.append(name)
        assert discriminating != [], (
            f"every control that {spelling} is supposed to be caught by is "
            "caught just as well with it removed from the set, so none of "
            "them measures this spelling. Give it a source whose only route "
            "to being reported is the listing, globbing or joining rule -- "
            "no log name, no `meta/kanban/*.log` string"
        )

    def test_every_construction_spelling_is_classified(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # AC-1, and review cycle 5's F-501. The audit derived the spellings
        # that READ a directory from `dir(os)`; nothing derived the ones that
        # BUILD one, so `os.path.join`, `Path.joinpath` and
        # `Path.with_segments` sat in the "pure path-string arithmetic"
        # exclusion -- a reason true of what they return and false of what
        # they do -- and every construction spelling but the `/` BinOp was
        # invisible to the guard.
        #
        # The enumeration is not replaced by a longer enumeration. The
        # library is asked which of its spellings assemble a directory out
        # of components (:func:`_measured_path_builders`), and every answer
        # has to be in a guard set; a name in neither a set nor an exclusion
        # is impossible, because
        # `test_every_spelling_the_stdlib_offers_is_classified` is red on
        # one. That is how `with_segments` got in: the probe named it, and
        # no cycle of CARD-238 had thought of it.
        monkeypatch.chdir(tmp_path)
        builders = _measured_path_builders()
        # Non-vacuity first: a probe that caught every exception and found
        # nothing would make the two assertions below hold trivially.
        assert len(builders) >= 5, builders
        assert "join" in builders and "joinpath" in builders, sorted(builders)
        unaudited = sorted(
            f"{name} ({'; '.join(shapes)})"
            for name, shapes in builders.items()
            if name not in _JOINERS | _PATH_WRAPPERS
        )
        assert unaudited == [], (
            "the standard library offers a spelling that assembles "
            "meta/kanban out of its components and no guard set knows about "
            "it, so a listing of the directory built that way is invisible "
            "to the path guard -- which is review cycle 5's F-501 verbatim. "
            "Classify it KIND_JOINER (or KIND_WRAPPER, if with one argument "
            f"it re-spells rather than assembles): {unaudited}"
        )
        # And the other direction, so the joiners cannot carry a member that
        # builds nothing -- the F-403 failure mode, where a set declared a
        # width no control could fail on.
        idle = sorted(name for name in _JOINERS if name not in builders)
        assert idle == [], (
            "a KIND_JOINER member does not actually assemble a directory "
            f"out of components on this interpreter: {idle}"
        )

    def test_the_guard_sets_are_derived_and_not_hand_written(self) -> None:
        # The claim that makes the equality above worth anything: on this
        # host `_LISTERS == _guard_set(KIND_LISTER)` holds by construction,
        # so that test can no longer fail while the sets are derived at all
        # -- and a test that cannot fail is this card's family. What CAN
        # fail is the derivation itself, so it is read out of this module's
        # own source: hand-write any of the five sets back into a literal
        # and this goes red.
        #
        # Review cycles 1-5 each hand-edited one of them, which is how five
        # spellings went missing. This is the line that stops the sixth
        # edit.
        tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
        derived = {
            node.targets[0].id: ast.unparse(node.value)
            for node in tree.body
            if isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id in {
                "_LISTERS", "_GLOBBERS", "_JOINERS", "_PATH_WRAPPERS",
                "_HOST_STATE_PROBES",
            }
        }
        assert sorted(derived) == [
            "_GLOBBERS", "_HOST_STATE_PROBES", "_JOINERS", "_LISTERS",
            "_PATH_WRAPPERS",
        ], sorted(derived)
        hand_written = sorted(
            f"{name} = {value}"
            for name, value in derived.items()
            if not value.startswith("_guard_set(")
        )
        assert hand_written == [], (
            "a set the guards consult is written out by hand again instead "
            "of being the audited table's projection, so the audit cannot "
            f"police it: {hand_written}"
        )

    def test_every_spelling_the_stdlib_offers_is_classified(self) -> None:
        # The audit the whole cycle exists for. Four cycles added members to
        # sets whose completeness nothing could test, and the fifth missing
        # member was `os.walk`. A set cannot be audited from inside this
        # file; it can be audited against `dir(os)`, `dir(os.path)`,
        # `dir(glob)` and `dir(pathlib.Path)`, which is what this does.
        #
        # Red when the library offers a spelling nobody here has judged, so
        # the next `os.walk` is a failing test rather than a quiet hole.
        surface = _stdlib_directory_surface()
        unclassified = sorted(
            f"{name} ({'/'.join(sorted(surface[name]))})"
            for name in surface
            if name not in STDLIB_DIRECTORY_SURFACE
        )
        assert unclassified == [], (
            "the standard library offers a directory-reaching spelling that "
            "STDLIB_DIRECTORY_SURFACE does not classify, so neither guard "
            "half can be said to cover it. Classify each one as a lister, a "
            "globber, a wrapper, a host-state probe, or KIND_NEITHER with "
            f"the reason it is none of those: {unclassified}"
        )

    def test_the_listing_sets_are_exactly_the_classified_spellings(self) -> None:
        # Both directions, so the audit can fail from either end: a member
        # dropped from a set (the cycle-1-to-4 failure mode) and a member
        # added without a classification (the F-403 failure mode, where the
        # set declared a width no control could fail on).
        declared = {
            "_LISTERS": sorted(_LISTERS),
            "_GLOBBERS": sorted(_GLOBBERS),
            "_JOINERS": sorted(_JOINERS),
            "_PATH_WRAPPERS": sorted(_PATH_WRAPPERS),
        }
        audited = {
            "_LISTERS": sorted(_guard_set(KIND_LISTER)),
            "_GLOBBERS": sorted(_guard_set(KIND_GLOBBER)),
            "_JOINERS": sorted(_guard_set(KIND_JOINER)),
            "_PATH_WRAPPERS": sorted(_guard_set(KIND_WRAPPER)),
        }
        assert declared == audited, (
            "a listing set and its classification in "
            "STDLIB_DIRECTORY_SURFACE disagree. Either the set is missing a "
            "spelling the table calls one, or it names a spelling the table "
            "does not -- and the table is the one audited against the "
            "standard library"
        )
        # The projection is against the live surface, so on an interpreter
        # lacking `glob0` the globbers are smaller -- which is F-502's fix
        # and is why this compares `_guard_set` and not `_classified`. It
        # therefore cannot fail while the sets are derived at all, and the
        # claim that they ARE derived is the one that can:
        # `test_the_guard_sets_are_derived_and_not_hand_written` reads this
        # module's source and is red if any of them becomes a literal again.
        assert _JOINERS, "the joiners cannot be empty on any host"

    def test_a_spelling_the_guards_use_is_a_real_stdlib_name(self) -> None:
        # The third side of the triangle: a classification that is not
        # KIND_NEITHER puts a name into a guard, so a typo or an invented
        # member would otherwise sit there matching nothing. KIND_NEITHER
        # entries are exempt on purpose -- they are allowed to carry other
        # platforms' spellings, which this host's `dir()` does not offer.
        surface = _stdlib_directory_surface()
        phantom = sorted(
            name
            for name, (kind, _) in STDLIB_DIRECTORY_SURFACE.items()
            if kind != KIND_NEITHER
            and name not in surface
            and name not in PLATFORM_GATED_SPELLINGS
        )
        assert phantom == [], (
            "a spelling classified into one of the guards is not a public "
            f"callable of os, os.path, glob or pathlib on this host: "
            f"{phantom}. Either it is a typo, or it is version- or "
            "platform-gated and belongs in PLATFORM_GATED_SPELLINGS with "
            "the reason it is absent"
        )
        # Review cycle 5's F-502: before the gated names were recorded, this
        # test WAS the defect -- five members (`glob0`, `glob1`,
        # `is_junction`, `isjunction`, `isdevdrive`) made the module red on
        # an interpreter that simply does not have them, measured by
        # deleting exactly those five in a plugin: 1 failed, 340 passed. The
        # sets no longer care (`_guard_set` intersects with the surface), so
        # what is left to catch is a typo, and that is what this now says.
        #
        # The other direction is NOT claimed and cannot be: a name recorded
        # as gated that is present here is simply present, and no assertion
        # can tell "recorded for an older interpreter" from "misrecorded".
        # What IS asserted is that the record is not a dumping ground: every
        # entry carries a reason, and no entry is for a name the table does
        # not classify at all.
        assert sorted(PLATFORM_GATED_SPELLINGS) == sorted(
            name
            for name, reason in PLATFORM_GATED_SPELLINGS.items()
            if reason.strip() and name in STDLIB_DIRECTORY_SURFACE
        ), sorted(PLATFORM_GATED_SPELLINGS)

    def test_no_spelling_is_classified_twice(self) -> None:
        # The table is grouped by reason, so a name written into two groups
        # would silently take the last one's kind -- and a `walk` classified
        # both KIND_LISTER and KIND_NEITHER is this card's defect family
        # with the evidence sitting right next to it.
        seen = collections.Counter(
            name for _, _, names in _SURFACE_CLASSIFICATION for name in names
        )
        twice = sorted(name for name, count in seen.items() if count > 1)
        assert twice == [], f"classified in two groups at once: {twice}"

    def test_every_classification_carries_a_reason(self) -> None:
        # So an exclusion is a decision on the record rather than a silent
        # omission, which is the whole difference between this table and the
        # four hand-written sets it replaces as the source of truth.
        unexplained = sorted(
            name
            for name, (kind, reason) in STDLIB_DIRECTORY_SURFACE.items()
            if not reason.strip() or kind not in _ALL_KINDS
        )
        assert unexplained == [], (
            "a classification with no reason, or with a kind that is not one "
            f"of {sorted(_ALL_KINDS)}: {unexplained}"
        )

    @pytest.mark.parametrize(
        "template",
        [WRAPPED_DIRECTORY_SOURCE, WRAPPED_DIRECTORY_METHOD_SOURCE],
        ids=["as a call", "as a method"],
    )
    @pytest.mark.parametrize("wrapper", sorted(_PATH_WRAPPERS))
    def test_every_path_wrapper_is_seen_through(
        self, wrapper: str, template: str
    ) -> None:
        # Non-vacuity of the peel, in both shapes, and nothing more.
        #
        # Review cycle 4's F-403: this test cannot fail for a bare name,
        # because `_unwrapped` peels whatever is in `_PATH_WRAPPERS` and the
        # source is generated from that same set -- so it passed by
        # construction for the two members the cycle-4 sweep had just
        # removed as bogus, while its comment claimed the set "cannot drift
        # apart" from the controls. The claim is corrected to what this can
        # hold: that each member really is seen through, which is still
        # worth asserting (without the peel the hoisted directory is
        # invisible through any of them -- `_joined_components` only looks
        # inside a call whose single argument is a string).
        #
        # What bounds the set is elsewhere, in two tests that CAN fail:
        # `test_the_listing_sets_are_exactly_the_classified_spellings` and
        # `test_a_wrapper_that_names_another_directory_is_not_peeled`.
        source = template.format(wrapper=wrapper)
        assert _live_log_references(source) != [], source

    @pytest.mark.parametrize(
        "source", [source for _, source in NOT_A_PATH_WRAPPER],
        ids=[name for name, _ in NOT_A_PATH_WRAPPER],
    )
    def test_a_wrapper_that_names_another_directory_is_not_peeled(
        self, source: str
    ) -> None:
        # The discriminating half of the wrapper guard (F-403). These are
        # misses *because* the name is not in `_PATH_WRAPPERS`: add
        # `dirname`, `joinpath` or `with_name` to the set and this goes red,
        # which is what makes the set's narrowness measured rather than
        # asserted in a comment.
        assert _live_log_references(source) == [], source

    @pytest.mark.parametrize(
        "template",
        [WRAPPED_DIRECTORY_SOURCE, WRAPPED_DIRECTORY_METHOD_SOURCE],
        ids=["as a call", "as a method"],
    )
    @pytest.mark.parametrize("name", PATH_ARITHMETIC_NAMES)
    def test_a_path_arithmetic_name_is_peeled_only_if_it_is_in_the_set(
        self, name: str, template: str
    ) -> None:
        # The discriminating control the hand-written NOT_A_PATH_WRAPPER
        # corpus claimed to be and was for one of its three entries. Both
        # directions, for every name the table files as path arithmetic, in
        # both shapes a wrapper is written:
        #
        #   * out of the set, the hoisted directory inside it is NOT reached
        #     -- so a name that re-spells a DIFFERENT directory cannot make
        #     the guard report a listing of this one;
        #   * in the set, it IS reached -- so the verdict depends on the
        #     membership and the control measures the set rather than the
        #     rest of the rule.
        #
        # Generated from the table, so a name moved into or out of the
        # path-arithmetic group is exercised on the next run rather than
        # taken on trust.
        source = template.format(wrapper=name)
        assert _live_log_references(source) == [], source
        wider = Spellings(
            listers=_LISTERS,
            globbers=_GLOBBERS,
            joiners=_JOINERS,
            wrappers=frozenset(_PATH_WRAPPERS | {name}),
        )
        assert _live_log_references(source, spellings=wider) != [], source

    def test_the_path_arithmetic_group_is_not_empty(self) -> None:
        # Non-vacuity of the parametrisation above: a reason string edited
        # in one place and not the other would silently collect nothing.
        assert len(PATH_ARITHMETIC_NAMES) >= 10, PATH_ARITHMETIC_NAMES
        assert "dirname" in PATH_ARITHMETIC_NAMES

    def test_which_non_wrapper_controls_the_set_decides_is_the_measured_set(
        self,
    ) -> None:
        # The corrected version of a sentence that was false for two of the
        # three entries in :data:`NOT_A_PATH_WRAPPER`, on this revision and
        # on CARD-238 as merged. Held as an equality rather than as prose:
        # red if the peel grows to accept a one-argument attribute call's
        # receiver (which would make the `joinpath` and `with_name` entries
        # discriminating), and red if `dirname` stops being so.
        decides = []
        for entry, (_, source) in zip(
            NOT_A_PATH_WRAPPER, NOT_A_PATH_WRAPPER, strict=True
        ):
            name = entry[0].split(",")[0]
            wider = Spellings(
                listers=_LISTERS,
                globbers=_GLOBBERS,
                joiners=_JOINERS,
                wrappers=frozenset(_PATH_WRAPPERS | {name}),
            )
            if _live_log_references(source, spellings=wider) != []:
                decides.append(name)
        assert tuple(decides) == NON_WRAPPERS_THE_SET_DECIDES, decides

    def test_the_sandbox_exemption_turns_off_when_the_root_is_a_constant(
        self,
    ) -> None:
        # The exemption above is on the *shape* of the join, not on a name:
        # the same body with the root hoisted to a module constant is a read
        # of the owner's log and is flagged. Were the exemption keyed to the
        # name "root" instead, a future author could borrow the name and the
        # guard would wave them through.
        hoisted = (
            'STEM = "suite-timing"\n'
            "ROOT = REPO_ROOT\n"
            "def write(text: str) -> None:\n"
            '    (ROOT / "meta" / "kanban" / f"{STEM}.log").write_text(text)\n'
        )
        assert _live_log_references(hoisted) != []

    @pytest.mark.parametrize(
        "source", [source for _, source in MEASURED_STRUCTURAL_MISSES],
        ids=[name for name, _ in MEASURED_STRUCTURAL_MISSES],
    )
    def test_the_disclosed_structural_misses_are_still_misses(
        self, source: str
    ) -> None:
        # Not an aspiration: the measured bound of this guard, asserted so
        # that it cannot drift away from what the docstrings say. If the
        # resolver grows past one of these, this goes red and the sentence
        # describing the bound is the thing to edit.
        assert _live_log_references(source) == []

    def test_a_joined_directory_contributes_one_reference_it_can_name(
        self,
    ) -> None:
        # Review cycle 1's F-004. The report is what a future reader acts
        # on, and for a glob under a directory joined inline this guard
        # named two references for one call site -- the second of them
        # `glob('metakanban*.log') under meta/kanban`, the path's components
        # folded without a separator, so a pattern no filesystem has.
        # Detection was never affected; the message was.
        #
        # Both directions, because narrowing a report is also a way to stop
        # reporting: exactly one reference, and it is the pattern the source
        # actually writes.
        inline = (
            "import glob\n"
            "import os\n"
            "HITS = glob.glob(\n"
            '    os.path.join(REPO_ROOT, "meta", "kanban", "*.log")\n'
            ")\n"
        )
        assert _live_log_references(inline) == [
            "glob('*.log') under meta/kanban"
        ]
        # And the fold is kept where it is concatenation rather than path
        # assembly, which is what `_assembles_path_components` turns on: a
        # `str.join` written on a string literal still folds, so a stem
        # built that way is still resolved.
        concatenated = ast.parse(
            'NAME = "".join(["suite", "-timing.log"])\n'
        ).body[0]
        assert "suite-timing.log" in _string_values(concatenated.value, {})

    def test_an_untracked_file_cannot_decide_the_verdict(
        self, tmp_path: Path
    ) -> None:
        # Review cycle 2, F-103: the tracked list is computed where git can
        # answer, and the sandbox is handed a manifest of it. Before that,
        # `git ls-files` returned rc=128 inside the sandbox, so the walk
        # fallback was not a rare path but the one the behavioural guard
        # always took -- and the walk admits untracked files, which is the
        # host dependence this card removes, one test over.
        (tmp_path / "tests").mkdir()
        (tmp_path / "meta" / "profiling").mkdir(parents=True)
        tracked = tmp_path / "tests" / "test_tracked.py"
        tracked.write_text("def test_x() -> None:\n    assert True\n")
        stray = tmp_path / "tests" / "scratch_check_log.py"
        stray.write_text(UNTRACKED_SCRATCH_SOURCE, encoding="utf-8")
        (tmp_path / SANDBOX_MANIFEST_NAME).write_text(
            "tests/test_tracked.py\n", encoding="utf-8"
        )
        listed = _guarded_sources(tmp_path)
        assert listed == [tracked], listed
        assert stray not in listed

    def test_a_manifest_at_the_repo_root_is_ignored(self, tmp_path: Path) -> None:
        # Review cycle 5's F-306. The manifest is gitignored, so a copy of
        # it in a worktree is host state -- and it was consulted at ANY
        # root, including the real repository's, where it would silently
        # replace `git ls-files` as the file set both guards judge. A
        # one-line manifest naming one harmless module would have left the
        # path guard reading one file and reporting nothing, with 357 tests
        # green.
        #
        # Measured in both directions against a planted manifest, on a root
        # this test owns -- the repository's own root is never written to,
        # which is why the untrusted root is a parameter.
        (tmp_path / "tests").mkdir()
        (tmp_path / "meta" / "profiling").mkdir(parents=True)
        for name in ("test_one.py", "test_two.py"):
            (tmp_path / "tests" / name).write_text(
                "def test_x() -> None:\n    assert True\n", encoding="utf-8"
            )
        (tmp_path / SANDBOX_MANIFEST_NAME).write_text(
            "tests/test_one.py\n", encoding="utf-8"
        )
        # Trusted root: the manifest decides, which is what the sandbox needs.
        assert _files_under_guard(tmp_path, untrusted_root=REPO_ROOT) == [
            "tests/test_one.py"
        ]
        # Untrusted root: it is ignored, and the fallbacks answer instead --
        # here the walk, since a tmp_path is no checkout. Both files come
        # back, so the stray manifest cannot narrow what is judged.
        assert sorted(
            _files_under_guard(tmp_path, untrusted_root=tmp_path)
        ) == ["tests/test_one.py", "tests/test_two.py"]


class TestSuiteTiming_CollectsTheSameWithAndWithoutTheLog:
    """AC-3: this module does not go quiet on a condition, nothing else in the tree newly does, and no outcome changes with the log.

    Both halves widened at review cycle 1, again at cycle 2, and the
    structural half's *territory* at cycle 3.

    The structural half reports the silences in
    :data:`CONDITIONAL_SILENCES` -- marks, ``pytestmark``, in-body skips and
    early returns, and, since cycle 2, an imperative module-scope
    ``pytest.skip(..., allow_module_level=True)``. That last one is why the
    two halves are not interchangeable: a module-level skip sits above every
    test in the file, so it silences the comparison below as well. The older
    wording of :func:`_conditional_silences` said "all six forms are now
    reported" while missing three, which is corrected there, with each
    remaining limit named and controlled.

    Cycle 3 (F-301, F-307) measured what the territory cost: the path guard
    judged every guarded source while this detector judged one module -- 221
    against 1 on 2026-10-16, so all but one of them had a single defence --
    and the mutant that walked through both halves was a host-state skip in
    one of the rest, wrapped round an
    ``os.listdir`` of the kanban directory. This detector reported that skip
    correctly; nothing ran it there. It runs over every guarded source now,
    in two tests with two different claims: ``== []`` for this module, which
    is the sharp one, and equality against :data:`MEASURED_SILENCES_ELSEWHERE`
    for the rest, because three pre-existing silences live in modules
    CARD-238's G-4 forbids it to edit. Both go red on a new one.

    The behavioural half compares the outcomes of the **whole module** (not
    of one class -- a cycle-1 mutant restoring the coupling in another class
    walked straight through that), in a sandbox whose every ``*.py`` is a
    copy rather than a symlink, so a module reached across a boundary
    resolves the sandbox root and its outcome can actually vary with the log
    (cycle 2, F-101). What that does and does not catch is stated per form at
    :func:`_live_log_references`; the one thing it cannot judge is itself,
    and that is the structural half above.
    """

    def test_nothing_in_this_module_goes_quiet_on_a_condition(self) -> None:
        declared = _conditional_silences(Path(__file__).read_text(encoding="utf-8"))
        assert declared == [], (
            "a conditional skip here turns 'this cannot run on this machine' "
            "into silence rather than into a failure, and a module-level one "
            f"takes both guard classes with it: {declared}"
        )

    def test_the_host_state_silences_elsewhere_are_exactly_the_measured_ones(
        self,
    ) -> None:
        # Every other guarded source, judged by the same detector as this
        # one. Review cycle 3: before this, a host-state skip anywhere else in
        # the guarded tree was reported by nothing, and a mutant restoring
        # this card's defect in `tests/test_clues.py` -- `os.listdir` of the
        # kanban directory, a skip when the host has no log, then a read of
        # it -- passed both guard classes. The detector reported its skip
        # correctly the whole time; nothing applied it.
        here = Path(__file__).resolve()
        found = tuple(
            sorted(
                (str(path.relative_to(REPO_ROOT)), name, condition)
                for path in _guarded_sources()
                if path.resolve() != here
                for name, condition in _conditional_silences(
                    path.read_text(encoding="utf-8")
                )
            )
        )
        assert found == tuple(sorted(MEASURED_SILENCES_ELSEWHERE)), (
            "the host-state silences in the guarded tree are no longer the "
            "ones CARD-238 measured. A new entry is a verdict that depends on "
            "the host rather than on the code; a missing one has been fixed "
            f"and should be struck off MEASURED_SILENCES_ELSEWHERE: {found}"
        )

    @pytest.mark.parametrize(
        "condition", [condition for _, _, condition in SILENCES_FIXED_BY_CARD_239],
        ids=[name for _, name, _ in SILENCES_FIXED_BY_CARD_239],
    )
    def test_a_silence_this_card_fixed_is_still_one_the_detector_would_report(
        self, condition: str
    ) -> None:
        # The control that gives :data:`SILENCES_FIXED_BY_CARD_239` content.
        # Striking an entry off the baseline is only honest if the detector
        # would still report the shape when it comes back, and after a fix
        # nothing in the tree exercises that shape any more -- so the shape
        # is exercised here, fabricated, in the in-body form where the
        # CONDITION has to be recognised as host state rather than being
        # reported for being a mark. Drop `is_file` or `is_dir` from the
        # probes and this goes red.
        source = (
            "import pytest\n"
            "def test_x() -> None:\n"
            f"    if {condition}:\n"
            '        pytest.skip("absent")\n'
            "    assert True\n"
        )
        assert _conditional_silences(source) != [], source

    def test_the_host_state_probe_is_exactly_the_classified_spellings(
        self,
    ) -> None:
        # The second half of review cycle 4's Critical. Its two omissions
        # compounded -- `walk` was absent from `_LISTERS` AND from the probe
        # -- so auditing one set and not the other would leave the same
        # compound one spelling along. Everything that lists a directory,
        # globs one, or answers what the filesystem holds at a path is a
        # probe: a skip keyed on any of those answers is keyed on the host.
        declared = sorted(_HOST_STATE_PROBES)
        audited = sorted(_guard_set(KIND_LISTER, KIND_GLOBBER, KIND_PROBE))
        assert declared == audited, (
            "_HOST_STATE_PROBES and STDLIB_DIRECTORY_SURFACE disagree, so a "
            "skip keyed on a filesystem answer this table calls a probe "
            "would not be reported as host state (or one it does not is)"
        )

    @pytest.mark.parametrize("probe", sorted(_HOST_STATE_PROBES))
    def test_the_probe_pattern_fires_on_every_spelling_it_names(
        self, probe: str
    ) -> None:
        # Non-vacuity of the *derivation* only, in both shapes the pattern
        # is written for: that `_probe_pattern` really builds a pattern
        # matching each member. It deliberately claims nothing about the
        # set's completeness -- the source is generated from the set, which
        # is precisely the vacuity review cycle 4's F-403 found in
        # `test_every_path_wrapper_is_seen_through`. Membership is bounded
        # by the audit above instead.
        assert _HOST_STATE_PROBE.search(f"not LOG.{probe}()"), probe
        assert _HOST_STATE_PROBE.search(f"not os.{probe}(LOG)"), probe

    @pytest.mark.parametrize("probe", sorted(_HOST_STATE_PROBES))
    def test_a_skip_gated_on_any_probe_is_reported(self, probe: str) -> None:
        # One behavioural control per spelling in the set, generated rather
        # than written out, so a member added to the set is exercised end to
        # end on the next run. Same standing as the test above: a control
        # for the mechanism, not a bound on the set.
        source = PROBE_GATED_SKIP.format(probe=probe)
        assert _conditional_silences(source) != [], source

    def test_the_silence_detector_is_not_vacuous(self) -> None:
        assert _conditional_silences(FABRICATED_SKIP) == [("test_x", "not LOG.exists()")]

    @pytest.mark.parametrize(
        "source", [source for _, source in CONDITIONAL_SILENCES],
        ids=[name for name, _ in CONDITIONAL_SILENCES],
    )
    def test_every_way_of_going_quiet_is_caught(
        self, source: str
    ) -> None:
        assert _conditional_silences(source) != []

    @pytest.mark.parametrize(
        "source", [source for _, source in NOT_A_CONDITIONAL_SILENCE],
        ids=[name for name, _ in NOT_A_CONDITIONAL_SILENCE],
    )
    def test_silence_this_detector_must_not_claim_is_not_claimed(
        self, source: str
    ) -> None:
        assert _conditional_silences(source) == []

    def test_what_resolves_outside_the_sandbox_is_exactly_the_data_links(
        self, tmp_path: Path
    ) -> None:
        # The mechanism review cycle 2 (F-101) measured, pinned rather than
        # asserted in prose. `meta/profiling` was symlinked wholesale and
        # `tests/` mirrored as per-file symlinks, so EVERY module reached
        # that way had `Path(__file__).resolve()` escape through the link to
        # the real repository: its paths pointed at the real tree, its
        # outcome did not change between the two sandboxes, and both
        # `present == absent` and "all PASSED" below held vacuously. Three
        # mutants survived all 41 guards that way, one of them the card's
        # own defect restored.
        #
        # Widened from `*.py` to everything after review cycle 3's F-302,
        # which found `_build_sandbox` claiming a containment it does not have:
        # the data files are symlinks and they do resolve outside. So the
        # assertion is an equality against that measured set rather than
        # `escaping == []`, which could only have been kept by not looking.
        _build_sandbox(tmp_path, SANDBOX_LOG)
        root = tmp_path.resolve()
        entries = sorted(tmp_path.rglob("*"))
        modules = [path for path in entries if path.suffix == ".py"]
        assert len(modules) > 100, len(modules)
        escaping = sorted(
            str(path.relative_to(tmp_path))
            for path in entries
            if root not in path.resolve().parents
        )
        links = sorted(
            str(path.relative_to(tmp_path))
            for path in entries
            if path.is_symlink()
        )
        # Escaping and being a link are the same set, in both directions: a
        # copy cannot escape, and every link here points at the real tree.
        assert escaping == links, (
            "something in the sandbox resolves outside it that is not one of "
            "the data symlinks, or a symlink here no longer escapes: "
            f"escaping={escaping[:20]} links={links[:20]}"
        )
        # And the part that matters for the comparison: no module and no
        # directory is among them, so no module's `Path(__file__).resolve()`
        # leaves the sandbox and no write lands in the real tree by walking
        # into a linked directory.
        assert [name for name in links if name.endswith(".py")] == [], links[:20]
        assert [name for name in links if (tmp_path / name).is_dir()] == [], (
            links[:20]
        )

    def test_the_outcomes_are_identical_with_and_without_the_log(
        self, tmp_path: Path
    ) -> None:
        # The real question is not "are the same tests collected" -- a skipif
        # collects either way -- but "is the same verdict reached". So the
        # *whole module* is run twice in a sandbox tree, once with a timing
        # log and once without, and the two runs' per-test outcomes are
        # compared.
        #
        # Whole module, not one class, because of review cycle 1: a mutant
        # that restored the original coupling in another class of this file
        # passed all fifteen guard tests. Outcome divergence is the defence
        # that does not depend on how the coupling is spelled, so it has to
        # cover every class that could carry one.
        present = _run_module_in_sandbox(tmp_path / "with-log", SANDBOX_LOG)
        absent = _run_module_in_sandbox(tmp_path / "without-log", None)
        # The control first: it is the one thing in the sandbox that is
        # *supposed* to depend on the log, so if it does not flip, the copy
        # is reading somebody else's tree and everything below is vacuous
        # (F-007).
        assert present.pop(SANDBOX_CONTROL_NODEID, None) == "PASSED", present
        assert absent.pop(SANDBOX_CONTROL_NODEID, None) == "FAILED", absent
        # And the same question asked across a module boundary, which is the
        # one the symlinked mirror used to answer wrongly (F-101): a module
        # outside `tests/`, reached the way the sandbox reaches it, must
        # resolve the SANDBOX root. If it resolves the real repository this
        # flips nowhere and everything below is vacuous again.
        assert present.pop(SANDBOX_CROSS_MODULE_NODEID, None) == "PASSED", present
        assert absent.pop(SANDBOX_CROSS_MODULE_NODEID, None) == "FAILED", absent
        # The module has to have actually run in there. A module that
        # silences itself under sandbox conditions -- a host-state skip whose
        # probe is absent in the sandbox -- arrives as an empty dict, and
        # this is the line that reports it (measured against review cycle
        # 2's F-102 mutant: `0 >= 100` fails in the parent while the targeted
        # run of the same mutant reports only `found no collectors`).
        assert len(present) >= 100, len(present)
        assert present == absent
        assert set(present.values()) == {"PASSED"}, present


# A log for the sandbox runs: well formed, and ending on a profiling run, so
# that a reinstated "the last entry is this card's profiling run" assertion
# would *pass* with the file present and skip without it -- i.e. the sandbox
# reproduces the defect rather than papering over it.
SANDBOX_LOG = (
    "# a header comment, as the real log carries\n"
    "2026-10-06T17:20:55Z wave-35 full-suite 770s PASS (6618 passed, 9 skipped, 0 failed)\n"
    "2026-10-15T05:34:34Z wave-39 card-217-profiling-run 931s PASS "
    "(7073 passed, 9 skipped, 0 failed) [131ms/test]\n"
)

_OUTCOME_LINE = re.compile(
    r"^(?P<nodeid>\S+::.+?) "
    r"(?P<outcome>PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)\b"
)

# The fabricated positive control written beside the copy. Its verdict is
# *meant* to depend on the sandbox log: it must pass with the log and fail
# without it, which is only possible if a module in the sandbox resolves the
# sandbox root. Without it, a future refactor that made the copy resolve the
# real repo root would leave `present == absent` and "all PASSED" both true
# and vacuous -- review cycle 1, F-007. It lives outside ``tests/`` on
# purpose, so the AC-1 guard running inside the sandbox does not read it and
# report its (deliberate) coupling as an offence.
SANDBOX_CONTROL_MODULE = '''\
"""A control for CARD-238's AC-3 sandbox: this module DOES judge the host.

Written into the sandbox by tests/test_suite_profile.py. If it ever passes
with the timing log absent, the sandbox is not isolated and the comparison
that writes it proves nothing.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_the_log_this_module_reads_is_the_sandbox_one() -> None:
    live = ROOT / "meta" / "kanban" / "suite-timing.log"
    assert live.is_file(), sorted(path.name for path in live.parent.iterdir())


def test_a_module_outside_tests_resolves_the_sandbox_root() -> None:
    """The log path a module under ``meta/profiling`` would compute.

    Review cycle 2, F-101: ``meta/profiling`` was symlinked into the sandbox
    wholesale, so a module reached through it resolved ``__file__`` *through*
    the link to the real repository. A log path constant living there -- the
    declined ``--check-log`` subcommand's natural home, and now a file this
    card touches -- therefore named the owner's real log from inside both
    sandboxes, so its verdict never varied and the comparison that writes
    this file proved nothing about it. Executed as a mutant it survived all
    41 guards while restoring the card's defect verbatim.

    So this performs that exact computation on the mirrored ranker and must
    flip with the sandbox log: PASSED beside the sandbox log, FAILED without.
    """
    import importlib.util
    import sys

    mirrored = ROOT / "meta" / "profiling" / "rank_durations.py"
    spec = importlib.util.spec_from_file_location("card238_mirror_probe", mirrored)
    assert spec is not None and spec.loader is not None, str(mirrored)
    module = importlib.util.module_from_spec(spec)
    # Registered before exec, for the reason _load_ranker gives: @dataclass
    # resolves annotations through sys.modules[cls.__module__].
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    reached = Path(module.__file__).resolve().parents[2]
    live = reached / "meta" / "kanban" / "suite-timing.log"
    assert live.is_file(), (
        f"a module under meta/profiling resolved {reached}, not the sandbox "
        f"root {ROOT}"
    )
'''

SANDBOX_CONTROL_PATH = Path("control") / "test_sandbox_control.py"
SANDBOX_CONTROL_NODEID = (
    f"{SANDBOX_CONTROL_PATH}::test_the_log_this_module_reads_is_the_sandbox_one"
)
SANDBOX_CROSS_MODULE_NODEID = (
    f"{SANDBOX_CONTROL_PATH}::test_a_module_outside_tests_resolves_the_sandbox_root"
)

# The one node id the sandbox cannot run, and why. It cannot hide a host
# coupling, because the test it names is this one: the comparison would
# launch itself, once per sandbox, without end. Everything else in the module
# runs in there, which is the point of review cycle 1's widening -- including
# the tree-walking guards, which see a full tree because _build_sandbox
# mirrors `tests/`.
#
# CARD-304 adds the second, and the reason is different: the sandbox mirrors
# `tests/` and `meta/profiling/` only, so `meta/kanban/config.yml` -- the file
# that class executes the prescriptions of -- is absent in there, and every
# assertion would error for want of the convention rather than for want of a
# log. It is also the one class in this module that is *supposed* to depend on
# the host: it probes it. Deselected with that stated, and recorded as
# CARD-304 residue: this class carries the structural half of its defence only
# (its own planted controls), not the behavioural comparison's.
SANDBOX_DESELECTED = (
    f"tests/{Path(__file__).name}::TestSuiteTiming_CollectsTheSameWithAndWithoutTheLog"
    "::test_the_outcomes_are_identical_with_and_without_the_log",
    f"tests/{Path(__file__).name}"
    "::TestHostCells_ThePrescribedInstrumentsExecuteAndRespond",
)


def _build_sandbox(root: Path, log: str | None) -> None:
    """Lay out a throwaway tree the copied module can resolve as its own root.

    Every ``*.py`` is a real **copy**, and every directory is created rather
    than linked. That is the whole isolation: paths here are
    ``Path(__file__).resolve()``-relative, and a module reached through a
    symlink resolves *through* the link to the real repository -- its paths
    then name the real tree, its outcome is the same in both sandboxes, and
    the comparison that runs it holds vacuously. Review cycle 2 (F-101)
    measured three mutants surviving all 41 guards that way, one of them this
    card's own defect carried by a path constant in ``meta/profiling``,
    which used to be symlinked here wholesale.
    ``test_what_resolves_outside_the_sandbox_is_exactly_the_data_links`` pins it.

    Data files are symlinked, which is cheap.

    The file set is the parent's tracked list (:func:`_files_under_guard`),
    written into the sandbox as a manifest so that the copy's own guards
    judge the same repo-determined set rather than this disk (F-103).

    This is **not** a containment barrier, and no sentence here should be
    read as one. Every write below joins its path onto ``root``, but being
    under ``root`` is not by itself enough to stay out of the real tree,
    because the data entries are symlinks and a write through one of those
    paths lands on its target in the real worktree. That inference is
    exactly what review cycle 3 (F-302) struck down: the sentence that stood
    here -- "a write here cannot land in the real tree even if a future edit
    points a source path at it" -- rested on the ``mkdir``, which covers
    directories and not the 57 file links four lines down. It is deleted
    rather than requalified, since nothing could make it go red.

    What the layout does deliver is measured and asserted as an equality, in
    ``test_what_resolves_outside_the_sandbox_is_exactly_the_data_links``: the
    entries resolving outside ``root`` are exactly the symlinks, and no
    ``*.py`` and no directory is among them -- which is what the comparison
    needs, since it is a module's ``Path(__file__).resolve()`` that has to
    land inside.

    On CARD-238's G-1: no path in any guarded source names the owner's log
    at all, within the measured bound of
    :class:`TestSuiteTiming_NoTestReadsTheLiveLog` and the entries of
    :data:`MEASURED_STRUCTURAL_MISSES` -- which is the strongest statement
    anything here pins, and stronger than a promise about this one function.
    That bound is wider than it was: the listing and globbing spellings it
    covers are audited against the standard library rather than enumerated
    by hand, so "any guarded source" no longer quietly means "any guarded
    source that does not use ``os.walk``".
    ``log``, when given, is written inside ``root``.
    """
    module = Path(__file__).name
    mirrored_names = _files_under_guard()
    assert len(mirrored_names) > 100, mirrored_names
    (root / "meta" / "kanban").mkdir(parents=True)
    # CARD-304: the mirror has to carry the kanban convention file as well.
    # A mirrored module now reads it AT IMPORT TIME -- the host-cell
    # prescriptions are the parametrize data for
    # TestHostCells_ThePrescribedInstrumentsExecuteAndRespond -- so without it
    # the copy fails to COLLECT, which no `--deselect` can reach: the
    # comparison then sees an empty outcome dict rather than a verdict.
    # Measured that way before it was added.
    #
    # A symlink, like every other data entry here, so
    # test_what_resolves_outside_the_sandbox_is_exactly_the_data_links stays an
    # equality (it is not a `*.py` and not a directory, which is what that
    # assertion cares about). It therefore resolves to the REAL file, which is
    # the second reason that class is deselected in here and not merely the
    # cost one: judging the real convention from inside the sandbox is exactly
    # the vacuity this layout exists to prevent.
    (root / "meta" / "kanban" / KANBAN_CONFIG.name).symlink_to(KANBAN_CONFIG)
    for name in mirrored_names:
        source = REPO_ROOT / name
        mirrored = root / name
        if mirrored.exists() or mirrored.is_symlink() or source.name == module:
            continue
        mirrored.parent.mkdir(parents=True, exist_ok=True)
        if source.suffix == ".py":
            mirrored.write_bytes(source.read_bytes())
        else:
            mirrored.symlink_to(source)
    (root / "tests").mkdir(exist_ok=True)
    (root / "tests" / module).write_text(
        Path(__file__).read_text(encoding="utf-8"), encoding="utf-8"
    )
    (root / SANDBOX_MANIFEST_NAME).write_text(
        "".join(f"{name}\n" for name in mirrored_names), encoding="utf-8"
    )
    (root / SANDBOX_CONTROL_PATH.parent).mkdir()
    (root / SANDBOX_CONTROL_PATH).write_text(SANDBOX_CONTROL_MODULE, encoding="utf-8")
    if log is not None:
        # The name is derived from LIVE_LOG_STEM rather than written as a
        # literal; the guard above exempts this join because its root is a
        # parameter -- a tmp_path, here -- and not a module constant.
        (root / "meta" / "kanban" / f"{LIVE_LOG_STEM}.log").write_text(
            log, encoding="utf-8"
        )


def _run_module_in_sandbox(root: Path, log: str | None) -> dict[str, str]:
    """Run this whole module in a throwaway tree; return ``{nodeid: outcome}``."""
    _build_sandbox(root, log)
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-p",
        "no:cacheprovider",
        "--no-header",
        "-v",
        "--tb=line",
        str(Path("tests") / Path(__file__).name),
        str(SANDBOX_CONTROL_PATH),
    ]
    for node in SANDBOX_DESELECTED:
        command += ["--deselect", node]
    try:
        completed = subprocess.run(
            command,
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
            # A hung sandbox session must fail loudly rather than hang the
            # suite, and the parent's PYTEST_ADDOPTS must not leak in: `-x`
            # or an extra plugin there would change the outcomes this test
            # compares (review cycle 1, F-009).
            timeout=300,
            env={**os.environ, "PYTEST_ADDOPTS": ""},
        )
    except subprocess.TimeoutExpired as expired:
        # `text=True` makes this a str, but TimeoutExpired is also raised
        # before the pipe is decoded in some paths, so handle both.
        captured = expired.stdout or ""
        output = (
            captured.decode("utf-8", "replace")
            if isinstance(captured, bytes)
            else captured
        )
        raise AssertionError(
            f"the sandbox pytest session did not finish in 300s: {output[-4000:]}"
        ) from expired
    outcomes: dict[str, str] = {}
    for line in completed.stdout.splitlines():
        match = _OUTCOME_LINE.match(line)
        if match is not None:
            outcomes[match["nodeid"]] = match["outcome"]
    assert outcomes, completed.stdout[-4000:]
    return outcomes


class TestSuiteCeiling_TheCliffEdgeListIsDerived:
    """CARD-292 / AC-2: which tests sit within 50 % of the suite's per-test
    ceiling, **derived from the committed artefact** rather than listed.

    The ceiling is real and it is in the tree, not in the host:
    ``tests/hang_guard.py`` arms ``faulthandler.dump_traceback_later`` with
    ``exit=True`` **per test** at its default of 120 s, so a test that
    overruns takes the whole process down -- no summary line, no captured
    output, exit 1, and no signal, which is every symptom CARD-292 was opened
    to explain. A test at 110 s is therefore not "slow"; it is one busy
    minute away from reding a gate that has nothing to do with the tree.

    **What is frozen here and what is not** (CARD-292's G-2). The ceiling is
    read off the guard's own source, and the threshold is derived from it, so
    nothing here encodes a property of one machine. What is frozen is the
    *list*, against the one committed artefact it is derived from, so the
    answer cannot drift silently -- the shape
    ``RENDER_HEAVY_SNAPSHOT`` has in this module.

    **The artefact's domain is part of the figures** and is stated rather than
    implied: ``suite-durations-20261023.txt``, commit ``ae164099``, taken
    **before** CARD-276 grew ``test_book_export_interior_cover.py`` from 90
    collected tests to 127. Both rows below are therefore **understatements**
    of that file's cost today, and CARD-292 re-measured the dearest of them
    directly rather than scaling this figure.
    """

    #: How close to the ceiling counts as cliff-edge. AC-2's "within 50 %".
    CEILING_FRACTION = 0.5

    #: Every test of the committed artefact whose summed phase time reaches
    #: ``CEILING_FRACTION`` of the ceiling, derived once and frozen.
    #:
    #: Two, and both in one class of one file -- which is the finding, not an
    #: accident of the threshold: the next test down is 56.92 s
    #: (``tests/test_kill_matrix.py::test_ac7_the_four_arm_grid_of_card_257_reproduces``)
    #: and it would join this list at a 47 % threshold.
    CLIFF_EDGE_SNAPSHOT: tuple[tuple[str, float], ...] = (
        (
            "tests/test_book_export_interior_cover.py::"
            "TestBookPdfStructure_NoPositionCountsTheGuideWithoutTheTitlePage::"
            "test_each_door_axis_arm_catches_a_shape_the_other_misses",
            81.03,
        ),
        (
            "tests/test_book_export_interior_cover.py::"
            "TestBookPdfStructure_NoPositionCountsTheGuideWithoutTheTitlePage::"
            "test_every_door_shape_is_read_or_refused_and_never_silent",
            67.08,
        ),
    )

    #: The artefact ``CLIFF_EDGE_SNAPSHOT`` is a property of. Named rather
    #: than taken as "the newest", so a later profile added beside it does not
    #: silently re-point a frozen list at a different recording.
    SNAPSHOT_ARTEFACT = "suite-durations-20261023.txt"

    #: The floor the derivation refuses below. An artefact whose duration
    #: format moved would parse to **no** tests, and an empty cliff-edge list
    #: reads as good news -- which is why this derivation is default-DENY: it
    #: refuses a profile it cannot see thousands of tests in, instead of
    #: reporting that nothing is near the ceiling.
    PARSE_FLOOR = 5000

    #: Where the ceiling is imposed. Held as a path so the control below can
    #: hand the same derivation a planted source instead.
    GUARD_SOURCE = "tests/hang_guard.py"

    @classmethod
    def _ceiling_seconds(cls, guard: str | None = None) -> float:
        """The per-test ceiling, read off the source of the guard that imposes
        it.

        By AST and not by import: ``HANG_SECONDS`` is
        ``float(os.getenv(..., "120"))``, so an imported value is whatever the
        environment said -- and CARD-292's own measurements set that variable
        to 0 to time a test that the guard would otherwise have killed. The
        **default literal** is the tree's figure; the environment's is the
        caller's.

        The shape is asserted as it is read, so a rewrite of that line reds
        here rather than quietly handing back a wrong ceiling.
        """
        if guard is None:
            guard = (REPO_ROOT / cls.GUARD_SOURCE).read_text(encoding="utf-8")
        tree = ast.parse(guard)
        assigned = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "HANG_SECONDS"
                for target in node.targets
            )
        ]
        assert len(assigned) == 1, (
            "tests/hang_guard.py no longer assigns HANG_SECONDS exactly once, "
            f"so the ceiling below is not read off one authority: {len(assigned)}"
        )
        defaults = [
            node.value
            for node in ast.walk(assigned[0])
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and node.value.replace(".", "", 1).isdigit()
        ]
        assert len(defaults) == 1, (
            "HANG_SECONDS no longer carries exactly one numeric default "
            f"literal, so no ceiling can be derived from it: {defaults}"
        )
        return float(defaults[0])

    @classmethod
    def _cliff_edge(cls, text: str, ceiling: float) -> list[tuple[str, float]]:
        """``[(nodeid, seconds)]`` for every test of ``text`` within
        ``CEILING_FRACTION`` of ``ceiling``, dearest first.

        Summed over **all three phases**, because the guard's alarm wraps
        ``pytest_runtest_protocol`` -- setup, call and teardown -- so a test
        whose call phase is comfortable and whose setup is not is still over
        the line.
        """
        parsed = ranker.parse_artefact(text)
        assert len(parsed.tests) >= cls.PARSE_FLOOR, (
            f"only {len(parsed.tests)} tests parsed out of this artefact, "
            f"under the floor of {cls.PARSE_FLOOR}: the duration format has "
            "moved and an empty cliff-edge list would read as good news"
        )
        threshold = ceiling * cls.CEILING_FRACTION
        return [
            (record.nodeid, round(record.total, 2))
            for record in sorted(
                parsed.tests.values(), key=lambda r: (-r.total, r.nodeid)
            )
            if record.total >= threshold
        ]

    def test_the_ceiling_is_read_off_the_guard_that_imposes_it(self) -> None:
        """The ceiling is the hang guard's own default, and the threshold is
        derived from it -- neither is written here."""
        ceiling = self._ceiling_seconds()
        assert ceiling == 120.0, (
            "the per-test hang guard's default moved, so every figure derived "
            f"from it in this class is stale: {ceiling}"
        )
        assert ceiling * self.CEILING_FRACTION == 60.0, ceiling

        # The can-fail half: the 120.0 above is satisfied by a function that
        # returns 120.0 for any input, so the derivation is asked for an
        # answer it cannot have been written with. A planted guard whose
        # default is 45 must come back as 45.
        planted = (REPO_ROOT / self.GUARD_SOURCE).read_text(encoding="utf-8").replace(
            '"120"', '"45"'
        )
        assert planted != (REPO_ROOT / self.GUARD_SOURCE).read_text(
            encoding="utf-8"
        ), "the plant below changed nothing, so it controls nothing"
        assert self._ceiling_seconds(planted) == 45.0, (
            "the ceiling is not read off the guard's own default: a planted "
            "default of 45 came back as "
            f"{self._ceiling_seconds(planted)}"
        )

    def test_the_cliff_edge_list_matches_a_live_derivation(self) -> None:
        """AC-2: the frozen list equals what the artefact says today."""
        artefact = PROFILING_DIR / self.SNAPSHOT_ARTEFACT
        assert artefact.is_file(), (
            f"{self.SNAPSHOT_ARTEFACT} is the recording CLIFF_EDGE_SNAPSHOT is "
            "a property of and it is not committed, so that list answers for "
            "nothing"
        )
        live = self._cliff_edge(
            artefact.read_text(encoding="utf-8"), self._ceiling_seconds()
        )
        # An EQUALITY, not a containment and not a disjunction: a row gained
        # is as much a finding as a row lost, and this list exists to notice
        # the gain.
        assert live == list(self.CLIFF_EDGE_SNAPSHOT), {
            "gained": [row for row in live if row not in self.CLIFF_EDGE_SNAPSHOT],
            "lost": [row for row in self.CLIFF_EDGE_SNAPSHOT if row not in live],
        }

    def test_the_derivation_refuses_an_artefact_it_cannot_read(self) -> None:
        """The default-DENY half, on the shape the derivation was **not**
        written from: a profile whose duration lines it cannot parse.

        Without this, a format change turns the cliff-edge list into ``[]``
        and the suite reports that nothing is near the ceiling.
        """
        artefact = (PROFILING_DIR / self.SNAPSHOT_ARTEFACT).read_text(
            encoding="utf-8"
        )
        mangled = re.sub(r"^(\d+\.\d+)s ", r"\1 s ", artefact, flags=re.MULTILINE)
        assert ranker.parse_artefact(mangled).tests == {}, (
            "the mangling this control depends on no longer defeats the "
            "parser, so it is not testing the refusal"
        )
        with pytest.raises(AssertionError, match="duration format has"):
            self._cliff_edge(mangled, 120.0)

    def test_the_threshold_is_inclusive_at_its_own_boundary(self) -> None:
        """The edge of the claim, on a synthetic artefact so the numbers are
        controlled: a test exactly at the threshold is listed, one a hundredth
        under it is not, and the sum is over all three phases rather than the
        call alone.

        The ``PARSE_FLOOR`` is lowered **for this one derivation only**, by
        calling the classmethod on a subclass, because a synthetic artefact
        cannot hold five thousand tests and the floor is the point of the test
        above.
        """

        class Unfloored(type(self)):
            PARSE_FLOOR = 1

        rows = "\n".join(
            [
                "59.99s call     tests/test_x.py::test_just_under",
                "60.00s call     tests/test_x.py::test_exactly_at",
                "30.00s call     tests/test_x.py::test_in_two_phases",
                "30.00s setup    tests/test_x.py::test_in_two_phases",
            ]
        )
        text = SYNTHETIC_ARTEFACT.replace(
            "10.00s call     tests/test_a.py::test_slow", rows
        )
        live = Unfloored._cliff_edge(text, 120.0)
        assert [nodeid for nodeid, _ in live] == [
            "tests/test_x.py::test_exactly_at",
            "tests/test_x.py::test_in_two_phases",
        ], live
        assert ("tests/test_x.py::test_in_two_phases", 60.0) in live, (
            "the derivation no longer sums the phases, so a test whose setup "
            "and call straddle the line is invisible to it"
        )

    def test_both_cliff_edge_rows_are_tests_the_suite_still_collects(self) -> None:
        """A frozen node id that no longer exists is a list about the past.

        Checked by collection rather than by grep: a renamed class or a
        reworded parametrize id leaves the method name findable in the file
        and the node id dead, which is the exact shape CARD-282's fix round
        nearly shipped.
        """
        files = sorted({nodeid.split("::", 1)[0] for nodeid, _ in self.CLIFF_EDGE_SNAPSHOT})
        collected = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                *files,
                "-o",
                "addopts=",
                "-q",
                "--collect-only",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        ids = {line.strip() for line in collected.stdout.splitlines() if "::" in line}
        assert len(ids) > 100, (
            "the collection subprocess returned almost nothing, so the "
            f"assertion below would pass vacuously: {collected.stdout[-400:]!r} "
            f"{collected.stderr[-400:]!r}"
        )
        missing = [nodeid for nodeid, _ in self.CLIFF_EDGE_SNAPSHOT if nodeid not in ids]
        assert missing == [], (
            "a frozen cliff-edge node id is no longer collected, so this list "
            f"is about a test that has been renamed or removed: {missing}"
        )


# ==========================================================================
# CARD-304 -- ADR-0039/R4's executing half: the host cells `config.yml`
# prescribes are run, and the instrument among them is run against controls.
# ==========================================================================
#
# R4 says a figure names its instrument, that the instrument must be
# executable on the host that recorded the figure, and that it must be shown
# to respond -- a positive control that it rises and a negative that it does
# not rise on a near-miss. R4 shipped with `check: {kind: review-lens}`
# because nothing in a tree can decide whether a number in prose names a live
# command. This section is the part that *can* be decided, and it is narrow by
# construction: `meta/kanban/config.yml` does not merely report figures, it
# **prescribes the commands that produce them**, and a prescription is a
# string a test can execute.
#
# What it reaches and what it does not is stated in R4's own comment and in
# CARD-304's notes rather than implied here. The three things worth saying at
# the top:
#
#   * two questions, two harnesses. Executability is asked with
#     `set -o pipefail` and judged on exit status; responsiveness is asked
#     WITHOUT pipefail and judged on the reading. A single harness would red a
#     blind instrument for the wrong reason -- "it exited 1" rather than "it
#     did not rise while a real pytest was alive" -- and the whole point of R4
#     is that those two are different findings;
#   * readings are DELTAS. An absolute rival-pytest count is host state: this
#     board runs up to five cards concurrently and a sibling worktree's gate
#     counts. Each case is judged against a baseline taken immediately before
#     it and re-taken after it, and a baseline that moved is a refusal to
#     judge rather than a verdict;
#   * a negative control has to prove it exists. Measured 2026-10-29: the
#     obvious shape for a "a shell whose argv merely mentions pytest" probe,
#     `zsh -c ': <text>; sleep N'`, leaves no such process behind at all --
#     zsh execs its last command and the argv becomes `sleep N`. The
#     instrument then reads "did not rise" because the near-miss was never
#     there, which is a vacuous pass wearing a negative control's clothes.
#     Hence `test_each_near_miss_probe_is_visible_to_ps`.

#: The convention file whose host-cell prescriptions this section executes.
#: Read as text and parsed as JSON: see :func:`_host_cells_block` for why the
#: data is JSON inside a YAML block scalar rather than YAML.
KANBAN_CONFIG = REPO_ROOT / "meta" / "kanban" / "config.yml"

#: The key whose block scalar holds those prescriptions.
HOST_CELLS_KEY = "host_cells"

#: How long a probe process lives if nothing kills it. Every probe IS killed
#: as soon as the instrument has been read, so this is a ceiling for an
#: orphan, not a cost.
PROBE_LIFETIME_SECONDS = 30

#: How long to wait for a probe to become observable, in seconds.
PROBE_VISIBLE_TIMEOUT = 30.0

#: How many times one case may be re-run when the baseline moved under it. A
#: sibling card's gate starting or finishing mid-case moves the reading by
#: one, and that is contention rather than a verdict. Bounded, because a retry
#: loop with no end is a hang; the failure that ends it prints the processes
#: the instrument actually matched, which is the only thing that settles such
#: an argument (five hand-written variants of this instrument, measured at one
#: instant on 2026-10-29, returned five different answers; what settled it was
#: printing the list).
BASELINE_ATTEMPTS = 4


def _host_cells_block(text: str) -> str:
    """The JSON document held in ``config.yml``'s ``host_cells:`` block scalar.

    JSON inside a YAML block scalar, rather than YAML, for one reason that is
    not aesthetic: PyYAML is **not** in ADR-0006/R1's dependency baseline (it
    is in this venv incidentally, as nothing in ``pyproject.toml`` declares
    it), so a test that imported it would gate this check on a package a bare
    checkout does not have. The alternative -- a hand-rolled YAML reader --
    would be one more unproven instrument inside the section about unproven
    instruments.

    So the reader is this: find the key, require the block-scalar marker,
    take the lines indented deeper than the key, dedent, and hand the result
    to :mod:`json`. Every near-miss of that shape raises rather than returning
    something plausible, and :data:`NOT_A_HOST_CELLS_BLOCK` is the control for
    each one -- a reader that quietly returns ``{}`` when the key is renamed
    would make every assertion below pass vacuously, which is this card's
    subject rather than an acceptable failure mode.
    """
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.strip().split(":", 1)[0] != HOST_CELLS_KEY:
            continue
        marker = line.strip().split(":", 1)[1].strip()
        if marker not in {"|", "|-", "|+"}:
            raise AssertionError(
                f"{HOST_CELLS_KEY}: is not a block scalar ({marker!r}); the "
                "reader below would hand json.loads a fragment"
            )
        indent = len(line) - len(line.lstrip())
        body: list[str] = []
        for following in lines[index + 1:]:
            if not following.strip():
                body.append("")
                continue
            if len(following) - len(following.lstrip()) <= indent:
                break
            body.append(following)
        if not any(entry.strip() for entry in body):
            raise AssertionError(f"{HOST_CELLS_KEY}: has an empty block")
        return textwrap.dedent("\n".join(body))
    raise AssertionError(f"no {HOST_CELLS_KEY}: key in {KANBAN_CONFIG}")


def _host_cells(text: str | None = None) -> dict:
    if text is None:
        text = KANBAN_CONFIG.read_text(encoding="utf-8")
    return json.loads(_host_cells_block(text))


#: Near-misses of the block the reader must refuse rather than read. Held as a
#: constant for the reason :data:`REINTRODUCTIONS` is: a fabricated source
#: passed inline would make this module its own first offender.
NOT_A_HOST_CELLS_BLOCK: tuple[tuple[str, str], ...] = (
    (
        "the key renamed",
        "review:\n  host_cell: |\n    {\"cells\": []}\n",
    ),
    (
        "a flow mapping instead of a block scalar",
        "review:\n  host_cells: {}\n",
    ),
    (
        "the block present but empty",
        "review:\n  host_cells: |\n  test_scope: impact\n",
    ),
    (
        "the key absent entirely",
        "review:\n  test_scope: impact\n",
    ),
)

#: The prescribed commands, by cell id, as the live file declares them.
HOST_CELLS = _host_cells()

#: Cell ids that prescribe a command, and the one that declares why it cannot.
COMMANDED_CELLS: tuple[str, ...] = tuple(
    cell["id"] for cell in HOST_CELLS["cells"] if cell.get("command")
)
UNCOMMANDED_CELLS: tuple[str, ...] = tuple(
    cell["id"] for cell in HOST_CELLS["cells"] if not cell.get("command")
)

#: The rival-pytest truth table, and the cases split by what each one claims.
RIVAL = HOST_CELLS["rival_pytest"]
RIVAL_CASES: tuple[dict, ...] = tuple(RIVAL["cases"])
REALIZABLE_CASES: tuple[dict, ...] = tuple(
    case for case in RIVAL_CASES if case.get("probe")
)
RISING_CASES: tuple[dict, ...] = tuple(
    case for case in REALIZABLE_CASES if case["expect"] == "rises"
)
#: The near-misses: flat, realizable, and NOT a real pytest. Case (b) is flat
#: and realizable and is a real pytest, so it is a declared bound rather than
#: a near-miss, and it gets its own test instead of being folded in here --
#: folding it in would read as a claim that a console-script run is a
#: near-miss, which is the opposite of what was measured.
NEAR_MISS_CASES: tuple[dict, ...] = tuple(
    case
    for case in REALIZABLE_CASES
    if case["expect"] == "flat" and not case.get("declared_bound")
)
BOUNDED_CASES: tuple[dict, ...] = tuple(
    case for case in REALIZABLE_CASES if case.get("declared_bound")
)
UNREALIZABLE_CASES: tuple[dict, ...] = tuple(
    case for case in RIVAL_CASES if not case.get("probe")
)
#: The rejected instruments the table says are refuted on this host AND names
#: a test for. Re-executed rather than remembered: a comment saying a flag
#: does not exist cannot go red the day it starts existing.
RE_EXECUTED_REJECTS: tuple[dict, ...] = tuple(
    entry for entry in RIVAL["rejected"] if entry.get("re_executed_by")
)

#: The module a pytest probe is pointed at. It signals readiness and then
#: sleeps **at import time**, so a bare ``--collect-only`` is enough to put a
#: real pytest on the host (CARD-304's G-5: cheap, and it must not take the
#: board's lock). Written into a ``tmp_path_factory`` directory, never into
#: ``tests/`` or ``meta/profiling/`` (G-3), which also keeps the probe's
#: pytest outside this repository entirely: its rootdir is the temporary
#: directory, no ``conftest.py`` is above it, and so CARD-255's foreign-holder
#: guard is never imported and the full-suite lock is never consulted.
#: ``test_the_pytest_probe_runs_outside_this_repository`` measures that rather
#: than asserting it in prose.
PROBE_MODULE = '''\
import pathlib
import time

pathlib.Path({ready!r}).write_text("x", encoding="utf-8")
time.sleep({lifetime!r})


def test_the_probe_was_only_ever_here_to_exist() -> None:
    pass
'''
PROBE_MODULE_NAME = "test_card304_probe.py"


def _shell() -> str:
    return HOST_CELLS["shell"]


def _run_prescribed(command: str) -> subprocess.CompletedProcess[str]:
    """Run a prescribed command the way AC-1 judges it: pipefail, exit 0.

    ``pipefail`` is what makes the exit status mean anything at all here. The
    rejected ``pgrep -fc`` form was prescribed *inside* a ``| wc -l``
    pipeline, and without ``pipefail`` the pipeline's status is ``wc``'s --
    zero -- while ``pgrep``'s usage error goes to stderr and the cell comes
    back empty. Exit 0 with an empty cell is the defect AC-1 exists to catch,
    so the status has to carry the first failing stage.
    """
    return subprocess.run(
        [_shell(), "-c", "set -o pipefail\n" + command],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )


def _reading(command: str) -> int | None:
    """The instrument's reading, or ``None`` when it did not produce a number.

    Deliberately **without** ``pipefail`` and without asserting the exit
    status: this is the responsiveness question, and a form that exits
    non-zero while printing a usable count is still answering it. ``None``
    means the cell came back as something other than a count -- which is a
    distinct finding from "zero", and the distinction R4's sentence is about.
    """
    done = subprocess.run(
        [_shell(), "-c", command],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    printed = done.stdout.strip()
    return int(printed) if printed.isdigit() else None


def _instrument() -> str:
    """The prescribed rival-pytest command, resolved through the table's ref."""
    wanted = RIVAL["instrument_cell"]
    for cell in HOST_CELLS["cells"]:
        if cell["id"] == wanted:
            return cell["command"]
    raise AssertionError(f"{wanted} names no cell in {KANBAN_CONFIG}")


def _matched_lines() -> str:
    """What the instrument actually matched, for a failure message to carry.

    Derived from the prescription by dropping its counting stage rather than
    written out again, so this diagnostic cannot describe a different query
    from the one that produced the number -- and it keeps ``$1`` the
    executable, which is the trap ``config.yml`` records for a ``pid,command``
    column pair.
    """
    command = _instrument()
    suffix = "| wc -l"
    assert command.rstrip().endswith(suffix), command
    return _run_prescribed(command.rstrip().removesuffix(suffix)).stdout


def _argv_of(pid: int) -> str:
    return _run_prescribed(f"ps -o command= -p {pid}").stdout.strip()


def _substituted(text: str) -> str:
    """A case's ``argv_mentions`` with the table's placeholders resolved.

    ``{argv0}`` is read out of a child process rather than assumed: this
    venv's interpreter is a macOS framework build that re-execs through
    ``Python.app``, so the argv a live run shows is not ``sys.executable``,
    and the whole (d3) case exists because that difference was missed once.
    """
    child = subprocess.run(
        [sys.executable, "-c", "import sys; print(sys.orig_argv[0])"],
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )
    return text.format_map(
        {"argv0": child.stdout.strip(), "venv_python": sys.executable}
    )


def _spawn(case: dict, workdir: Path, ready: Path) -> subprocess.Popen:
    """Put this case's condition on the host and return the process to kill."""
    shape = case["probe"]
    if shape == "shell-wrapper":
        # `& wait` and not a trailing `sleep`: zsh execs its last command, so
        # the tail form's argv becomes `sleep N` and the near-miss this case
        # is about never exists. Measured 2026-10-29, both shapes.
        mentioned = _substituted(case["argv_mentions"])
        return subprocess.Popen(
            [_shell(), "-c", f": {mentioned}; sleep {PROBE_LIFETIME_SECONDS} & wait"]
        )
    if shape == "search-tool":
        mentioned = _substituted(case["argv_mentions"])
        return subprocess.Popen(
            [
                _shell(),
                "-c",
                f"sleep {PROBE_LIFETIME_SECONDS} | /usr/bin/grep -- '{mentioned}'",
            ]
        )
    if shape in {"pytest-module", "pytest-console-script"}:
        ready.unlink(missing_ok=True)
        launcher = (
            [sys.executable, "-m", "pytest"]
            if shape == "pytest-module"
            else [str(Path(sys.executable).with_name("pytest"))]
        )
        return subprocess.Popen(
            [
                *launcher,
                "--collect-only",
                "-q",
                "-p",
                "no:randomly",
                "-p",
                "no:cacheprovider",
                "-o",
                "addopts=",
                PROBE_MODULE_NAME,
            ],
            cwd=workdir,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTEST_ADDOPTS": ""},
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    raise AssertionError(f"case {case['id']} names no probe shape: {shape!r}")


def _wait_until_visible(case: dict, proc: subprocess.Popen, ready: Path) -> str:
    """Block until the probe is observable, and return the argv that proves it.

    Two different proofs for two different probe shapes, and neither is "it
    was spawned": for a pytest probe, the module it imports writes ``ready``
    *before* it sleeps, so the file is the interpreter's own signal that it is
    past start-up; for a wrapper or a search tool, the proof is that ``ps``
    shows a process whose argv carries the text the case is about.

    Returns "" if the probe never became observable, which every caller turns
    into a failure. A negative control that cannot be seen is not a control.
    """
    deadline = time.monotonic() + PROBE_VISIBLE_TIMEOUT
    while time.monotonic() < deadline:
        if case["probe"].startswith("pytest"):
            if ready.is_file():
                return _argv_of(proc.pid)
        else:
            argv = _argv_of(proc.pid)
            if "pytest" in argv:
                return argv
        time.sleep(0.05)
    return ""


@pytest.fixture(scope="module")
def rival_matrix(tmp_path_factory: pytest.TempPathFactory) -> dict[str, dict]:
    """Run every realizable case of the truth table once; return the readings.

    One spawn per case rather than one per assertion, because the probes are
    processes and the assertions are many. Each case records ``before``,
    ``during`` and ``after`` readings and the argv that proved the probe was
    there, so the tests below assert on measurements rather than taking them.

    A case whose baseline moved between ``before`` and ``after`` is re-run up
    to :data:`BASELINE_ATTEMPTS` times; this board runs cards concurrently and
    a sibling gate's start is a genuine ±1. What it is *not* is a verdict, so
    the last attempt's reading is kept with ``stable`` false and the tests
    fail on it naming the processes the instrument matched.
    """
    workdir = tmp_path_factory.mktemp("card304-probe")
    ready = workdir / "ready"
    (workdir / PROBE_MODULE_NAME).write_text(
        PROBE_MODULE.format(ready=str(ready), lifetime=PROBE_LIFETIME_SECONDS),
        encoding="utf-8",
    )
    instrument = _instrument()
    measured: dict[str, dict] = {}
    for case in REALIZABLE_CASES:
        for attempt in range(1, BASELINE_ATTEMPTS + 1):
            before = _reading(instrument)
            proc = _spawn(case, workdir, ready)
            try:
                argv = _wait_until_visible(case, proc, ready)
                during = _reading(instrument)
                matched = _matched_lines()
            finally:
                proc.kill()
                proc.wait(timeout=60)
            after = _reading(instrument)
            measured[case["id"]] = {
                "before": before,
                "during": during,
                "after": after,
                "argv": argv,
                "matched": matched,
                "attempts": attempt,
                "stable": before == after and before is not None,
            }
            if measured[case["id"]]["stable"]:
                break
    return measured


class TestHostCells_ThePrescribedInstrumentsExecuteAndRespond:
    """CARD-304: ADR-0039/R4's executing half, over ``meta/kanban/config.yml``.

    AC-1 runs every shell command the file prescribes for a host cell and
    requires exit 0 **and** the output shape the cell declares. AC-2 turns the
    rival-pytest truth table into data and runs the prescribed instrument
    against it: it must rise while a real pytest is alive and must not rise on
    a near-miss, with the near-miss proved to exist first.

    **What this class does not reach**, stated here and in R4's comment rather
    than left to be inferred:

    * a figure in prose. ``config.yml`` is reachable because it *prescribes
      commands*; a number in a card, a retro or a docstring has no
      machine-readable link to the command that produced it, and inventing one
      would be a claim this check could not keep;
    * a ratio whose halves came from different instruments, runs or baselines,
      and a point estimate published for a quantity with run-to-run spread.
      Both are properties of how two numbers were *obtained*, and the text
      retains nothing of that;
    * the live-log sandbox comparison does not cover this class -- it is
      deselected there, because the sandbox mirrors ``tests/`` and
      ``meta/profiling/`` only, so ``config.yml`` is absent in it, and because
      a cell whose job is to probe the host is declaredly host-coupled rather
      than accidentally so.
    """

    def test_the_host_cells_block_is_data_this_test_can_parse(self) -> None:
        data = _host_cells()
        assert [cell["id"] for cell in data["cells"]], data
        assert data["rival_pytest"]["cases"], data

    @pytest.mark.parametrize(
        "source",
        [source for _, source in NOT_A_HOST_CELLS_BLOCK],
        ids=[name for name, _ in NOT_A_HOST_CELLS_BLOCK],
    )
    def test_the_host_cells_reader_refuses_a_near_miss(self, source: str) -> None:
        """The negative control for the reader itself.

        R4's own prescription applied to this check's first instrument: a
        reader that returned ``{}`` for a renamed key would make every
        assertion in this class pass while measuring nothing.
        """
        with pytest.raises((AssertionError, ValueError)):
            _host_cells(source)

    @pytest.mark.parametrize("cell_id", COMMANDED_CELLS)
    def test_every_prescribed_host_cell_command_exits_zero(self, cell_id: str) -> None:
        """AC-1. A flag this platform does not have reds the suite.

        This is the assertion ``pgrep -fc`` fails: BSD pgrep has no ``-c``, so
        it exits 2 with a usage line, and inside a ``$(...)`` cell that is an
        empty host cell rather than a count. It is also the assertion the
        second instance fails -- ``pgrep -f`` is case-sensitive and this
        venv's live ``argv[0]`` is ``.../MacOS/Python``, so the form finds
        nothing and exits 1 even while a run is live.
        """
        cell = next(c for c in HOST_CELLS["cells"] if c["id"] == cell_id)
        done = _run_prescribed(cell["command"])
        assert done.returncode == 0, (
            f"the {cell_id} cell's prescribed command is not executable on "
            f"this host: exit {done.returncode}, stderr {done.stderr[-400:]!r}. "
            "A gate that records this cell would write an empty figure and "
            "read it as a quiet host."
        )

    @pytest.mark.parametrize("cell_id", COMMANDED_CELLS)
    def test_every_prescribed_host_cell_command_prints_its_declared_shape(
        self, cell_id: str
    ) -> None:
        """AC-1's other half: exit 0 is not the same as a usable figure.

        A command can exit 0 and print nothing, or print a usage line, and the
        cell would then carry something that is not the quantity. The declared
        shape is the smallest thing that can tell those apart.
        """
        cell = next(c for c in HOST_CELLS["cells"] if c["id"] == cell_id)
        done = _run_prescribed(cell["command"])
        assert re.match(cell["stdout"], done.stdout.strip()), (
            f"the {cell_id} cell printed {done.stdout.strip()!r}, which is not "
            f"the shape it declares ({cell['stdout']!r})"
        )

    @pytest.mark.parametrize("cell_id", UNCOMMANDED_CELLS)
    def test_a_host_cell_with_no_command_says_why(self, cell_id: str) -> None:
        """Default-deny on the cell list, so AC-1's set cannot shrink quietly.

        Not every host cell is a shell command -- the per-test ceiling is read
        off the run's own durations -- but "no command" has to be a stated
        reason rather than an omission, or a cell could be exempted from AC-1
        by deleting its command.
        """
        cell = next(c for c in HOST_CELLS["cells"] if c["id"] == cell_id)
        assert cell.get("no_command_because"), cell

    @pytest.mark.parametrize("cell_id", COMMANDED_CELLS)
    def test_each_prescribed_command_is_written_in_one_place(
        self, cell_id: str
    ) -> None:
        """R4's last clause, in the one form a tree can check.

        *A figure recomputed and refuted is retracted everywhere it was
        written.* Nothing can find every copy of a number, but a prescription
        that exists twice in the file that prescribes it is exactly how a
        correction survives in one place and not the other -- which this file
        has done: a bound written for ``pgrep -f 'MacOS/Python.*pytest'``
        outlived that instrument by one revision and read as a bound on its
        replacement.

        Measured narrowness, stated because planting a mutant found it: the
        comparison is between the **decoded** command and the raw file text,
        so a prescription whose JSON needs an escape (a ``\\`` in a regex,
        say) counts zero occurrences and reds. That is a loud refusal rather
        than a silent pass -- the equality is ``== 1`` -- and no prescribed
        command carries one today, but a future one would have to be stored
        without an escape or this test restated.
        """
        cell = next(c for c in HOST_CELLS["cells"] if c["id"] == cell_id)
        text = KANBAN_CONFIG.read_text(encoding="utf-8")
        assert text.count(cell["command"]) == 1, (
            f"the {cell_id} cell's command appears {text.count(cell['command'])} "
            "times in config.yml. A second copy is a prescription that can be "
            "corrected in one place and left wrong in the other."
        )

    def test_the_truth_table_carries_a_control_in_each_direction(self) -> None:
        """AC-2's shape, before any of it is run.

        A table of negatives alone cannot tell a working instrument from a
        dead one, and a table of positives alone cannot tell it from one that
        counts everything. R4 asks for both, so the data has to carry both and
        both have to be realizable -- a case that cannot be created is
        declared, not counted.
        """
        assert RISING_CASES, RIVAL_CASES
        assert NEAR_MISS_CASES, RIVAL_CASES

    @pytest.mark.parametrize("case_id", [case["id"] for case in UNREALIZABLE_CASES])
    def test_an_unrealizable_case_says_why(self, case_id: str) -> None:
        case = next(c for c in RIVAL_CASES if c["id"] == case_id)
        assert case.get("not_realizable_because"), case

    @pytest.mark.parametrize(
        "case_id", [case["id"] for case in NEAR_MISS_CASES + BOUNDED_CASES]
    )
    def test_each_near_miss_probe_is_visible_to_ps(
        self, case_id: str, rival_matrix: dict[str, dict]
    ) -> None:
        """The control on the controls, and it is not theoretical.

        Measured 2026-10-29: written as ``zsh -c ': <text>; sleep N'`` -- the
        obvious shape, and the one the table's prose describes -- the wrapper
        does not exist by the time anything looks. zsh execs its last command
        and the process's argv is ``sleep N``; the text the case is about is
        gone, and the instrument reads "did not rise" for the one reason that
        proves nothing. Every negative below is judged only after this.
        """
        seen = rival_matrix[case_id]
        assert "pytest" in seen["argv"], (
            f"case {case_id}'s probe never became observable, so a flat "
            f"reading proves nothing about the instrument: argv {seen['argv']!r}"
        )

    @pytest.mark.parametrize("case_id", [case["id"] for case in RISING_CASES])
    def test_the_instrument_rises_on_a_real_pytest(
        self, case_id: str, rival_matrix: dict[str, dict]
    ) -> None:
        """AC-2's POSITIVE control: the cell can tell a live run from a quiet box.

        This is the assertion both historical blind forms fail, and it fails
        them for the right reason -- not "it errored" but "a real pytest was
        alive and the number did not move".
        """
        seen = rival_matrix[case_id]
        assert seen["stable"], (
            f"case {case_id}: the baseline moved from {seen['before']} to "
            f"{seen['after']} across {seen['attempts']} attempts, so this is a "
            "contended host rather than a verdict. The processes the "
            f"instrument matched:\n{seen['matched']}"
        )
        # The positive control's own vacuity guard: a probe that never started
        # gives a flat reading for a reason that is not about the instrument,
        # and the message below would then name the wrong defect.
        assert "pytest" in seen["argv"], (
            f"case {case_id}'s pytest probe never became observable, so a flat "
            f"reading says nothing about the cell: argv {seen['argv']!r}"
        )
        assert seen["during"] == seen["before"] + 1, (
            f"case {case_id}: a real pytest was alive and the prescribed cell "
            f"read {seen['during']} against a baseline of {seen['before']}. A "
            "cell that cannot rise cannot distinguish a quiet host from a "
            f"blind command.\nthe probe: {seen['argv']!r}\nwhat the "
            f"instrument matched:\n{seen['matched']}"
        )

    @pytest.mark.parametrize("case_id", [case["id"] for case in NEAR_MISS_CASES])
    def test_the_instrument_does_not_rise_on_a_near_miss(
        self, case_id: str, rival_matrix: dict[str, dict]
    ) -> None:
        """AC-2's NEGATIVE controls, one per near-miss the table declares.

        Three shapes, and the third was added by this card: a shell whose argv
        merely spells a pytest command (in three spellings, the last naming
        the framework re-exec path that retired the previous instrument), and
        a **search tool** whose own argv carries the pattern -- a process the
        act of measuring spawns, and one that a probe excluding only shells
        still counts.
        """
        seen = rival_matrix[case_id]
        assert seen["stable"], (
            f"case {case_id}: the baseline moved from {seen['before']} to "
            f"{seen['after']} across {seen['attempts']} attempts. The "
            f"processes the instrument matched:\n{seen['matched']}"
        )
        assert seen["during"] == seen["before"], (
            f"case {case_id}: the prescribed cell rose to {seen['during']} from "
            f"{seen['before']} for a process that is not a pytest run.\nthe "
            f"probe: {seen['argv']!r}\nwhat the instrument matched:\n"
            f"{seen['matched']}"
        )

    @pytest.mark.parametrize("case_id", [case["id"] for case in BOUNDED_CASES])
    def test_a_declared_bound_is_still_exactly_as_blind_as_declared(
        self, case_id: str, rival_matrix: dict[str, dict]
    ) -> None:
        """The bound asserted in both directions, so it cannot drift silently.

        Case (b) -- a real pytest started through the venv's ``bin/pytest``
        console script -- is one the instrument does **not** see, because the
        argv holds ``bin/pytest`` and never ``-m pytest``. The table recorded
        it as a 1 until 2026-10-29 and it is a 0; the same awk keyed on
        ``/pytest/`` reads 0 -> 1.

        Asserting the blindness rather than hiding it means two things go red:
        widening the instrument (which would need its own negative control,
        and has none measured), and the day the console script's argv changes
        shape. G-1: the bound is narrowed, never the rule.
        """
        seen = rival_matrix[case_id]
        assert seen["stable"], (
            f"case {case_id}: the baseline moved from {seen['before']} to "
            f"{seen['after']}. Matched:\n{seen['matched']}"
        )
        assert "pytest" in seen["argv"], seen
        assert seen["during"] == seen["before"], (
            f"case {case_id} is declared BLIND and it rose to {seen['during']} "
            f"from {seen['before']}. If the instrument now sees a "
            "console-script run, the declared bound in config.yml has been "
            "overtaken and must be struck rather than kept."
        )

    def test_the_board_starts_pytest_in_the_form_the_cell_can_see(self) -> None:
        """What makes case (b)'s blindness tolerable, and it is checkable.

        The instrument is blind to a console-script run, and the board's own
        ``review.test_command`` starts pytest as ``-m pytest``. That is the
        whole argument for tolerating the bound, so it is asserted rather than
        asserted-in-prose: change ``test_command`` to the console script and
        the gate's rival-pytest cell goes blind to the board's own runs, and
        this test says so first.
        """
        text = KANBAN_CONFIG.read_text(encoding="utf-8")
        declared = re.search(r'^\s*test_command:\s*"(?P<value>[^"]*)"', text, re.M)
        assert declared is not None, "review.test_command is not in config.yml"
        assert "-m pytest" in declared["value"], (
            f"review.test_command is {declared['value']!r}, which the "
            "rival-pytest cell cannot see: it keys on ' -m pytest' and a "
            "console-script run's argv never holds it. The declared bound on "
            "case (b) rested on this and no longer holds."
        )

    @pytest.mark.parametrize(
        "instrument",
        [entry["instrument"] for entry in RE_EXECUTED_REJECTS],
        ids=[entry["instrument"].split("'")[0].strip() for entry in RE_EXECUTED_REJECTS],
    )
    def test_a_rejected_instrument_is_still_refuted_on_this_host(
        self, instrument: str
    ) -> None:
        """A rejection is a claim too, and this one is re-executed each run.

        ``config.yml`` records six instruments as rejected. Two of them are
        rejected for a reason a command can demonstrate without any pytest
        being alive -- a flag that does not exist, and a pattern that cannot
        match this host's ``argv[0]`` -- and those two are re-run here. A
        comment saying ``pgrep`` has no ``-c`` cannot go red the day it grows
        one; this can.

        The other four are rejected for blindness or false-positives against a
        live process, which is the truth table's job above and not a
        standalone command's.
        """
        done = _run_prescribed(instrument)
        assert done.returncode != 0 or not done.stdout.strip().isdigit(), (
            f"{instrument!r} now exits 0 and prints "
            f"{done.stdout.strip()!r} on this host. config.yml rejects it as "
            "unusable; if that is no longer true the rejection is stale and "
            "must be restated rather than left standing."
        )

    def test_the_pytest_probe_runs_outside_this_repository(
        self, tmp_path: Path
    ) -> None:
        """CARD-304's G-5: the probe must not touch the board's full-suite lock.

        It cannot, and the reason is structural rather than a flag: the probe's
        pytest is pointed at a module in a temporary directory, so its rootdir
        is that directory, no ``conftest.py`` sits above it, and the hook that
        reads the lock is never imported. Measured by running the same
        invocation to completion and reading the rootdir it reports, because
        "no conftest is above it" is the kind of claim that stops being true
        after a refactor and says nothing when it does.
        """
        module = tmp_path / PROBE_MODULE_NAME
        module.write_text(
            PROBE_MODULE.format(ready=str(tmp_path / "ready"), lifetime=0),
            encoding="utf-8",
        )
        done = subprocess.run(
            [
                sys.executable, "-m", "pytest", "--collect-only", "-q",
                "-p", "no:randomly", "-p", "no:cacheprovider",
                "-o", "addopts=", PROBE_MODULE_NAME,
            ],
            cwd=tmp_path,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTEST_ADDOPTS": ""},
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        assert done.returncode == 0, done.stdout[-2000:] + done.stderr[-2000:]
        assert "1 test collected" in done.stdout, done.stdout[-2000:]
        reported = subprocess.run(
            [
                sys.executable, "-m", "pytest", "--collect-only",
                "-p", "no:randomly", "-p", "no:cacheprovider",
                "-o", "addopts=", PROBE_MODULE_NAME,
            ],
            cwd=tmp_path,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTEST_ADDOPTS": ""},
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        rootdir = re.search(r"^rootdir: (?P<path>.+)$", reported.stdout, re.M)
        assert rootdir is not None, reported.stdout[-2000:]
        assert Path(rootdir["path"]).resolve() == tmp_path.resolve(), (
            "the probe's pytest resolved a rootdir outside its temporary "
            f"directory ({rootdir['path']}), so this repository's conftest -- "
            "and with it the full-suite lock guard -- is on its path after all"
        )
