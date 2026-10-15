"""CARD-217 -- the suite duration profile and the rankings derived from it.

This card measures the suite; these tests guard the measurement. They assert
that the committed artefact is complete and honest about its conditions
(AC-1), that the derivation from artefact to rankings is reproducible (AC-2),
that a contended run cannot be passed off as the profile (AC-4), and that the
append to ``meta/kanban/suite-timing.log`` keeps the format every wave reads
(AC-5).

These tests are deliberately cheap. The card's whole subject is a suite that
has grown expensive, so its own tests parse text and shell out exactly once;
none of them renders anything.

``meta/profiling/rank_durations.py`` is loaded by path rather than imported:
``meta/`` is not a package and is not on ``sys.path``, and putting it there
would make the repo's structural import guard's job harder for no gain.
"""

from __future__ import annotations

import collections
import importlib.util
import re
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PROFILING_DIR = REPO_ROOT / "meta" / "profiling"
RANKER_PATH = PROFILING_DIR / "rank_durations.py"
TIMING_LOG = REPO_ROOT / "meta" / "kanban" / "suite-timing.log"


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
    return sorted(PROFILING_DIR.glob("suite-durations-*.txt"))


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

    def test_exactly_one_artefact_is_committed(self) -> None:
        found = _artefacts()
        assert len(found) == 1, (
            "the rankings name one source artefact; multiple profiles would "
            f"make 'the' profile ambiguous: {[p.name for p in found]}"
        )

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

    def test_file_totals_sum_the_phases_of_their_tests(self) -> None:
        profile = ranker.parse_artefact(SYNTHETIC_ARTEFACT)
        by_file = dict((path, secs) for path, secs, _ in ranker.rank_files(profile))
        assert by_file["tests/test_a.py"] == pytest.approx(11.0)
        assert by_file["tests/test_b.py"] == pytest.approx(0.5)

    def test_file_rows_count_tests_not_phase_records(self) -> None:
        profile = ranker.parse_artefact(SYNTHETIC_ARTEFACT)
        counts = {path: n for path, _, n in ranker.rank_files(profile)}
        assert counts == {"tests/test_a.py": 1, "tests/test_b.py": 1}

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

    @pytest.mark.skipif(
        not TIMING_LOG.exists(),
        reason="suite-timing.log is gitignored (*.log) and absent from this checkout",
    )
    def test_the_real_log_is_entirely_well_formed(self) -> None:
        text = TIMING_LOG.read_text(encoding="utf-8")
        assert ranker.malformed_timing_lines(text) == []

    @pytest.mark.skipif(
        not TIMING_LOG.exists(),
        reason="suite-timing.log is gitignored (*.log) and absent from this checkout",
    )
    def test_the_last_entry_is_this_cards_profiling_run(self) -> None:
        entries = ranker.timing_log_entries(TIMING_LOG.read_text(encoding="utf-8"))
        assert entries, "the log holds no parseable entries"
        last = entries[-1]
        assert "profil" in last["label"] or "profil" in last["notes"], (
            f"expected the profiling run last, got {last['label']}"
        )
        assert last["status"] == "PASS"
        assert last["duration"] != "---", "the profiling run must record a duration"
