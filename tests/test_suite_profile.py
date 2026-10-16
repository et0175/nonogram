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

These tests are deliberately cheap. The card's whole subject is a suite that
has grown expensive, so its own tests parse text and shell out exactly once;
none of them renders anything.

``meta/profiling/rank_durations.py`` is loaded by path rather than imported:
``meta/`` is not a package and is not on ``sys.path``, and putting it there
would make the repo's structural import guard's job harder for no gain.
"""

from __future__ import annotations

import ast
import collections
import hashlib
import importlib.util
import random
import re
import subprocess
import sys
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from types import ModuleType

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
    # duration, a rate bracket, a rate bracket followed by a *parenthesised*
    # second note, and the header/GAP/NOTE comment lines. This is what
    # "the real log is entirely well formed" asserted, over text that cannot
    # change under the suite's feet.
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
        "2026-10-15T05:34:34Z wave-39 card-217-profiling-run 931s PASS "
        "(7073 passed, 9 skipped, 0 failed) [131ms/test]\n"
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
        assert len(ranker.timing_log_entries(self.REAL_SHAPES)) == 5

    def test_the_trailing_prose_shape_is_not_legal(self) -> None:
        # AC-4's ruling: **not legal.** The format already has a slot for
        # free prose -- the parentheses -- and all 16 other entries in the
        # owner's log use it, em dashes included ("0 failed — first wave with
        # a clean suite"). The one entry that wanted a note *after* the rate
        # bracket, wave-38's card-212 gate, parenthesised it and parses. So
        # the convention the entries share is: commentary lives inside
        # parentheses, and the rate bracket terminates the line.
        #
        # Widening the regex to swallow a bare trailing tail would make the
        # `notes` and `rate` fields ambiguous for every reader of the log
        # (the cost trend is read off `duration` and `rate`), which is why
        # the parser is left alone here (CARD-238 G-3) and the shape is
        # pinned as rejected instead.
        #
        # Writer, so the next author does not repeat it: the forge:kanban
        # dispatcher's merge-gate "SUITE TIMING" append step
        # (skills/kanban/references/cmd-run.md), which documents the line as
        # `<ISO date> wave-<N> <label> <seconds>s <PASS|FAIL>` and carries no
        # trailing-prose form; tests/README.md's "Logging the run" shows the
        # same. Put the gate's commentary inside the notes parentheses.
        assert ranker.parse_timing_line(self.CARD_217_GATE_LINE) is None
        assert ranker.malformed_timing_lines(self.CARD_217_GATE_LINE + "\n") == [
            self.CARD_217_GATE_LINE
        ]

    def test_the_same_note_parenthesised_is_legal_and_keeps_its_fields(self) -> None:
        # The ruling above is about placement, not about content: the very
        # same sentence is accepted the log's own way, which is what makes
        # "not legal" a correctable instruction rather than a lost note.
        head, _, tail = self.CARD_217_GATE_LINE.partition(" — ")
        legal = f"{head} ({tail})"
        entry = ranker.parse_timing_line(legal)
        assert entry is not None
        assert entry["label"] == "card-217-merge-gate"
        assert entry["duration"] == "963s"
        assert entry["rate"] == ""  # the bracket is no longer line-final
        assert "the profiling card's own gate" in entry["notes"]

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
        for line in good:
            entry = ranker.parse_timing_line(line)
            assert entry is not None, line
            # The fields are checked against the shape the generator built,
            # not re-derived with the parser being tested.
            assert line.startswith(f"{entry['ts']} {entry['wave']} {entry['label']} ")
            assert f" {entry['duration']} {entry['status']} (" in line
            if entry["rate"]:
                assert line.endswith(f"[{entry['rate']}]")

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

TESTS_DIR = REPO_ROOT / "tests"

# The live log's distinctive name component. Declared as a plain constant on
# purpose: a bare literal bound to a name is not a path and not a read, which
# is exactly the distinction the guard below draws.
LIVE_LOG_STEM = "suite-timing"


def _live_log_references(source: str) -> list[str]:
    """Literals in ``source`` that name the live log *where it would be used*.

    Takes source text rather than walking the disk itself, so the rule can be
    exercised against the fabricated sources below and cannot pass vacuously
    (the precedent is ``tests/test_cli.py``'s structural import guard).

    A reference is a literal naming the log that appears either as a direct
    operand of a ``/`` join (``REPO_ROOT / "meta" / "kanban" / "...log"``) or
    as a direct argument of a call (``Path(...)``, ``open(...)``,
    ``joinpath(...)`` -- and ``skipif(..., reason="...log is absent")``, which
    is the same coupling wearing a different hat). f-string parts count.

    Deliberately *not* a reference: the name in a comment, in a docstring, or
    bound to a constant as :data:`LIVE_LOG_STEM` is above. That is the whole
    reason this is an ``ast`` walk and not a ``grep`` -- a grep cannot tell a
    note about the file from a read of it, and this module's own docstring
    mentions the file by name.
    """
    found: list[str] = []

    def literals(node: ast.AST) -> list[str]:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return [node.value]
        if isinstance(node, ast.JoinedStr):
            return [
                part.value
                for part in node.values
                if isinstance(part, ast.Constant) and isinstance(part.value, str)
            ]
        return []

    for node in ast.walk(ast.parse(source)):
        used: list[ast.AST] = []
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            used = [node.left, node.right]
        elif isinstance(node, ast.Call):
            used = [*node.args, *(keyword.value for keyword in node.keywords)]
        for child in used:
            found.extend(
                text for text in literals(child) if LIVE_LOG_STEM in text
            )
    return sorted(set(found))


def _skipif_decorators(source: str) -> list[tuple[str, str]]:
    """``(decorated name, condition source)`` for every ``skipif`` in ``source``."""
    found: list[tuple[str, str]] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            if not ast.unparse(decorator.func).endswith("skipif"):
                continue
            condition = ast.unparse(decorator.args[0]) if decorator.args else ""
            found.append((node.name, condition))
    return found


# Every form in which the read could come back. Held as a module constant
# rather than inline in a ``parametrize`` call so that these sources are not
# themselves direct call arguments -- which would make this module its own
# first offender.
REINTRODUCTIONS: tuple[str, ...] = (
    'TIMING_LOG = REPO_ROOT / "meta" / "kanban" / "suite-timing.log"\n',
    'LOG = Path("meta/kanban/suite-timing.log")\n',
    'text = open("meta/kanban/suite-timing.log").read()\n',
    'LOG = REPO_ROOT.joinpath("meta", "kanban", "suite-timing.log")\n',
    'LOG = Path(f"{root}/meta/kanban/suite-timing.log")\n',
    "import pytest\n"
    '@pytest.mark.skipif(not LOG.exists(), reason="suite-timing.log is absent")\n'
    "def test_x() -> None:\n    pass\n",
)

# Mentions that are not reads. A grep-based guard would fail every one of
# these, which is why the guard parses instead.
INNOCENT_MENTIONS: tuple[str, ...] = (
    "# suite-timing.log is host state; no test may read it\nX = 1\n",
    '"""The appended line keeps suite-timing.log\'s format."""\n',
    'LIVE_LOG_STEM = "suite-timing"\n',
    "def test_x() -> None:\n"
    "    # the log (suite-timing.log) is not consulted here\n"
    "    assert True\n",
)

FABRICATED_SKIP = (
    "import pytest\n"
    "@pytest.mark.skipif(not LOG.exists(), reason=\"absent\")\n"
    "def test_x() -> None:\n    pass\n"
)


class TestSuiteTiming_NoTestReadsTheLiveLog:
    """AC-1: no test reads ``meta/kanban/suite-timing.log``, proved structurally."""

    def test_no_test_module_reaches_for_the_live_log(self) -> None:
        offenders = {
            str(path.relative_to(REPO_ROOT)): references
            for path in sorted(TESTS_DIR.rglob("*.py"))
            if (references := _live_log_references(path.read_text(encoding="utf-8")))
        }
        assert offenders == {}, (
            "a test reaches for the gitignored live timing log, so its verdict "
            f"depends on the host rather than on the code: {offenders}. Assert "
            "the format against entries the test constructs instead (CARD-238)."
        )

    def test_the_walk_actually_sees_the_test_tree(self) -> None:
        # Guards the guard: a mistyped glob would make the test above pass by
        # inspecting nothing at all.
        walked = list(TESTS_DIR.rglob("*.py"))
        assert len(walked) > 100, len(walked)
        assert Path(__file__).resolve() in {path.resolve() for path in walked}

    @pytest.mark.parametrize("source", REINTRODUCTIONS)
    def test_every_way_of_reintroducing_the_read_is_caught(self, source: str) -> None:
        assert _live_log_references(source) != []

    @pytest.mark.parametrize("source", INNOCENT_MENTIONS)
    def test_a_mention_that_is_not_a_read_is_not_caught(self, source: str) -> None:
        assert _live_log_references(source) == []


class TestSuiteTiming_CollectsTheSameWithAndWithoutTheLog:
    """AC-3: the class cannot pass by skipping, and the log cannot change it."""

    TARGET = "tests/test_suite_profile.py::TestSuiteTimingLog_FormatUnchanged"

    def test_no_test_in_this_module_skips_on_host_state(self) -> None:
        declared = _skipif_decorators(Path(__file__).read_text(encoding="utf-8"))
        assert declared == [], (
            "a skipif here turns 'this test cannot run on this machine' into "
            f"silence rather than into a failure: {declared}"
        )

    def test_the_skipif_detector_is_not_vacuous(self) -> None:
        assert _skipif_decorators(FABRICATED_SKIP) == [("test_x", "not LOG.exists()")]

    def test_the_outcomes_are_identical_with_and_without_the_log(
        self, tmp_path: Path
    ) -> None:
        # The real question is not "are the same tests collected" -- a skipif
        # collects either way -- but "is the same verdict reached". So the
        # class is run twice in a sandbox tree that holds nothing but this
        # module, the ranker it loads, and (once) a timing log, and the two
        # runs' per-test outcomes are compared.
        present = _run_format_class(tmp_path / "with-log", SANDBOX_LOG)
        absent = _run_format_class(tmp_path / "without-log", None)
        assert len(present) >= 20, present
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


def _run_format_class(root: Path, log: str | None) -> dict[str, str]:
    """Run the format class in a throwaway tree; return ``{nodeid: outcome}``.

    ``log`` is written to the sandbox's ``meta/kanban/suite-timing.log`` when
    given and omitted when ``None``. Nothing outside ``root`` is touched: the
    owner's log is never created, read or removed by this suite (CARD-238 G-1).
    """
    (root / "tests").mkdir(parents=True)
    (root / "meta" / "profiling").mkdir(parents=True)
    (root / "meta" / "kanban").mkdir(parents=True)
    (root / "tests" / Path(__file__).name).write_text(
        Path(__file__).read_text(encoding="utf-8"), encoding="utf-8"
    )
    (root / "meta" / "profiling" / RANKER_PATH.name).write_text(
        RANKER_PATH.read_text(encoding="utf-8"), encoding="utf-8"
    )
    if log is not None:
        # The name is derived from LIVE_LOG_STEM rather than written as a
        # literal, because the guard above flags that literal in a path join
        # wherever it appears -- and rightly: it cannot tell a sandbox root
        # from REPO_ROOT by looking at the name. This path is under tmp_path,
        # so the owner's log is neither created nor read (CARD-238 G-1).
        (root / "meta" / "kanban" / f"{LIVE_LOG_STEM}.log").write_text(
            log, encoding="utf-8"
        )

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-p",
            "no:cacheprovider",
            "--no-header",
            "-v",
            "--tb=line",
            f"{Path('tests') / Path(__file__).name}::"
            "TestSuiteTimingLog_FormatUnchanged",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    outcomes: dict[str, str] = {}
    for line in completed.stdout.splitlines():
        match = _OUTCOME_LINE.match(line)
        if match is not None:
            outcomes[match["nodeid"]] = match["outcome"]
    assert outcomes, completed.stdout[-4000:]
    return outcomes
