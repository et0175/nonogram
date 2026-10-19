#!/usr/bin/env python3
"""Derive the suite's duration rankings from a committed ``--durations`` artefact.

CARD-217. This script exists so that nobody hand-counts the rankings in
``suite-hotspots-<date>.md``: that document is generated from this script's
stdout, and re-running the script on the same artefact reproduces it byte for
byte (AC-2).

Usage::

    python meta/profiling/rank_durations.py meta/profiling/suite-durations-20261015.txt

Determinism contract
--------------------
stdout is a pure function of the artefact's bytes. Nothing is read from the
clock, the environment, the filesystem layout or the host. Ties are broken on
the test id so that equal durations cannot reorder between runs. The one
optional filesystem read -- re-deriving the render-heavy file set from a live
``tests/`` tree via ``--verify-render-set`` -- writes only to stderr, and the
ranking itself always uses the frozen snapshot below.

Why a frozen snapshot of the render-heavy set
---------------------------------------------
The render hypothesis (see the card) is decided by what share of wall clock the
render-heavy test files hold. If the script re-grepped the tree on every run,
its output would silently change as the tree changes and the committed hotspots
document would stop matching the committed artefact. The set is therefore
frozen here, with the exact command that produced it recorded alongside, and
``--verify-render-set`` re-runs that command to report drift.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

# The render APIs named in CARD-217's "render hypothesis". A test file is
# render-heavy if it mentions any of them.
RENDER_API_PATTERN = (
    r"interior\(|solved_puzzle_page|interior_stream|render_pages"
    r"|puzzle_pages|export_book|create_guide_page|proof_pages"
)

# Produced by, from the repo root:
#
#   grep -rlE "interior\(|solved_puzzle_page|interior_stream|render_pages\
#   |puzzle_pages|export_book|create_guide_page|proof_pages" \
#       tests --include="*.py" | sort
#
# at 56c716e. The card estimated "19 render-heavy files"; the grep finds 29
# paths, of which 27 are test modules and 2 are shared helpers
# (tests/helpers/book_corpus.py, tests/helpers/pdf_pages.py). The helpers carry
# no tests of their own, so they contribute no durations and are kept in the
# list only so the set matches the grep exactly.
#
# **Restated once since, deliberately** (CARD-222, 2026-10-17), as
# ``tests/test_suite_profile.py``'s own frozen-set test asks: 30 paths now,
# with ``tests/test_book_page_frame.py`` added — that card's own test file,
# which exports the baseline book's interior through ``interior_stream`` to
# measure the page frame off the rendered pixels. The recorded shares below
# are unchanged by it: they are properties of the 2026-10-15 durations
# artefact, in which this file does not appear at all (it contributes 0 s), so
# the render-heavy set's 21.23 % of attributed time is the same number over the
# same recording. A later recording will attribute its own time to it.
#
# **Restated a second time, deliberately** (CARD-223, 2026-10-18): 31 paths,
# with ``tests/test_book_qr_slot.py`` added. That card moves the placeholder
# QR icon into the footer's outer corner and sets two lines beside it, and
# its own test file exports the baseline book's interior through
# ``interior_stream`` to read the two lines back off the real ``draw.text``
# calls a book makes — the same end-to-end evidence CARD-222's file takes.
# **Added rather than dodged**: the call could have been spelled through a
# sibling API the grep does not match, which would have kept this list short
# while the cost stayed exactly the same — the silent divergence the frozen
# set exists to prevent.
#
# Unlike CARD-222's addition, this one **is** in the 2026-10-15 recording
# (CARD-204 wrote the file; this card rewrote it), so although it contributes
# 0 s there, its tests join the render row's *count*: 1079 → 1091, and with it
# the derived ms/test 181 → 179, in ``suite-hotspots-20261015.md``'s deciding
# table. Those two cells are restated there and nothing else is — every
# measured second and every share below is the same number over the same
# artefact, which is still cited by the same sha256.
RENDER_HEAVY_SNAPSHOT: tuple[str, ...] = (
    "tests/helpers/book_corpus.py",
    "tests/helpers/pdf_pages.py",
    "tests/property/test_book_export_interior.py",
    "tests/property/test_book_order.py",
    "tests/property/test_book_pairing.py",
    "tests/property/test_book_pdf_geometry.py",
    "tests/test_admin_tier_surfaces.py",
    "tests/test_book_answer_key.py",
    # RESTATED 2026-10-19 (CARD-225). tests/test_book_cell_size.py reads the
    # book-wide cell off the RENDERED INK (page_ink / two_up_ink), so it walks
    # the real interior -- 23 mentions of RENDER_API_PATTERN. Unlike CARD-251's
    # entry, this one genuinely draws, so the share it contributes is a real
    # render cost rather than an over-statement.
    "tests/test_book_cell_size.py",
    "tests/test_book_export_interior_cover.py",
    "tests/test_book_finalise_gutter.py",
    "tests/test_book_guide_page.py",
    "tests/test_book_guide_page_type.py",
    "tests/test_book_interior_face.py",
    "tests/test_book_interior_type_floor.py",
    "tests/test_book_page_frame.py",
    "tests/test_book_page_numbers.py",
    "tests/test_book_pdf.py",
    "tests/test_book_pdf_band.py",
    "tests/test_book_pdf_ink_mode.py",
    "tests/test_book_pdf_levels.py",
    "tests/test_book_pdf_memory.py",
    "tests/test_book_pdf_packed_degrade.py",
    "tests/test_book_pdf_two_up.py",
    "tests/test_book_proof_pages.py",
    "tests/test_book_qr_slot.py",
    "tests/test_book_scaffolding.py",
    "tests/test_book_solved_answer_key.py",
    "tests/test_book_solved_page.py",
    "tests/test_book_toc.py",
    "tests/test_export_pdf.py",
    "tests/test_layout_page_spec.py",
    # RESTATED DELIBERATELY 2026-10-19 (CARD-251), which is what this freeze
    # exists to force. The card's route tests gained two mentions of the
    # pattern: `interior_stream` (the transfer test cross-checks the warning's
    # delta against the export's own page count) and `puzzle_pages`, reached
    # through `book_pdf_generator.puzzle_page_plan`.
    #
    # Worth knowing when this file's share is read as a COST: neither mention
    # draws. `interior_stream` "splits the interior into the part that decides
    # and the part that draws, and does all of the first before any of the
    # second" -- the test reads `.page_count` off the plan and never iterates
    # the pages. The set is a MENTION grep by construction ("a test file is
    # render-heavy if it mentions any of them"), so the entry is correct by the
    # definition above; the file's render cost is near zero, and a share
    # computed from its whole runtime over-states this one file.
    "tests/test_puzzle_edit_routes.py",
)

# --------------------------------------------------------------------------
# Artefact header contract
#
# The header is the part of the artefact a reader has to trust before they
# trust a single number in it: which tree was measured, on what, and whether
# anything else was competing for the CPU. CARD-217's AC-1 enumerates the
# fields; AC-4 says a contended run must not be recorded as the profile. Both
# are checked against the functions below rather than by eye.
# --------------------------------------------------------------------------

REQUIRED_HEADER_FIELDS: tuple[str, ...] = (
    "commit",
    "host",
    "python",
    "command",
    "wall clock",
    "result",
    "solo run",
)

_HEADER_LINE = re.compile(r"^#\s*(?P<key>[a-z][a-z0-9 ]*?)\s*:\s*(?P<value>.*?)\s*$")

# A process line counts as a competing suite if it runs pytest. `grep pytest`
# alone also matches the grep itself and any editor showing this file, so the
# match is anchored on an actual invocation. The trailing (\s|$) rather than
# \b matters: \b would also fire on `tail -f pytest-output.log`, because the
# hyphen is a word boundary.
_PYTEST_PROCESS = re.compile(
    r"(?:^|/|\s)(?:py\.test|pytest|python[\d.]*\s+-m\s+pytest)(?:\s|$)"
)

# --------------------------------------------------------------------------
# meta/kanban/suite-timing.log line contract
#
# That log is gitignored (`.gitignore`'s blanket `*.log`), so it is not
# committed and a fresh checkout has none. Its format is nonetheless a real
# contract -- every wave appends to it and the cost trend is read off it -- so
# the format lives here, in a committed file, where a test can hold it still.
#
#   2026-10-06T17:20:55Z wave-35 full-suite 770s PASS (6618 passed, 9 skipped, 0 failed)
#   2026-10-15T06:30:00Z wave-38 card-221-merge-gate 939s PASS (...) [133ms/test]
#   2026-10-14T05:20:00Z wave-37 card-214-merge-gate --- PASS (...)
#   2026-10-14T19:20:17Z wave-38 card-212-merge-gate 1123s PASS (...) [159ms/test] (...)
#
# CARD-238 added the fourth shape -- a parenthesised note *after* the rate
# bracket. It was not new to the log: two entries have used it since wave 38,
# and both of them parsed with `rate=''` because `notes` was a greedy `.*`
# that swallowed the bracket. Six of the log's lines carry a rate and only
# three gave one back. So `notes` is now lazy and the trailing note has a
# group of its own (`extra`), which leaves the accepted/rejected *language*
# exactly as it was -- `(...)` followed by optional junk inside the
# parentheses always matched -- and changes only which field gets which text.
# A *bare* trailing note (` — prose`, no parentheses) stays rejected: no
# entry uses it, and `tests/test_suite_profile.py` pins it, names the writer
# and says why.
# --------------------------------------------------------------------------

#: A rate bracket anywhere in a line, whether or not the line parses. The
#: entry regex cannot answer this for a line it rejects, and the deliberate
#: reader's second question -- how many bracket-bearing lines give their rate
#: back -- is about exactly those lines too.
_RATE_BRACKET = re.compile(r"\[\d+ms/test\]")

TIMING_LOG_LINE = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z) "
    r"(?P<wave>wave-\d+) "
    r"(?P<label>\S+) "
    r"(?P<duration>\d+s|---) "
    r"(?P<status>PASS|FAIL) "
    r"\((?P<notes>.*?)\)"
    r"(?: \[(?P<rate>\d+ms/test)\])?"
    r"(?: \((?P<extra>.*)\))?$"
)

# --------------------------------------------------------------------------
# Cost families -- the deciding table
#
# These are the groupings the card's question is settled on. They are defined
# here, rather than in a throwaway analysis script, so that the hotspots
# document's *headline* is derived from committed code exactly like the three
# rankings below it. The card's conclusion turns on the first two rows, and
# four follow-on cards are steered by them, so a figure nobody can regenerate
# is a figure nobody can check.
#
# The browser family is the twelve tests/test_puzzle_solver_*.py files, which
# all drive Chromium through the shared `browser_page` fixture defined in
# test_puzzle_solver_page.py. Three further files use that same fixture
# (test_books_list_mobile, test_book_finalise_guide_preview_layout,
# test_book_setup_print_mobile, 9.11s between them); they are deliberately
# left out so the figure is a floor rather than a best case -- see the
# hotspots document's caveat.
# --------------------------------------------------------------------------

BROWSER_FAMILY_PREFIX = "tests/test_puzzle_solver"
PROPERTY_PREFIX = "tests/property/"
ADMIN_LOCAL_TRIO = (
    "tests/test_run_admin_tests.py",
    "tests/test_setup_admin_local.py",
    "tests/test_start_admin_local.py",
)

TOP_TESTS = 50
TOP_FILES = 20

PHASES = ("setup", "call", "teardown")

# "12.34s call     tests/test_x.py::test_y[a b]" -- the id may contain spaces
# inside a parametrisation bracket, so the id is the rest of the line.
_DURATION_LINE = re.compile(
    r"^(?P<secs>\d+\.\d+)s\s+(?P<phase>setup|call|teardown)\s+(?P<nodeid>\S.*?)\s*$"
)

# pytest's own summary line, e.g. "7073 passed, 9 skipped in 939.12s (0:15:39)".
#
# It is often absent. pyproject.toml's addopts already carries `-q`, so the
# card's own `-q` raises the quiet level to `-qq`, at which pytest prints no
# summary at all. When that happens the header's `wall clock:` and `result:`
# fields are used instead -- which is why those two are required fields.
_SUMMARY = re.compile(
    r"^.*?(?P<passed>\d+) passed(?:, (?P<skipped>\d+) skipped)?.*? in "
    r"(?P<wall>[\d.]+)s"
)

_HEADER_WALL = re.compile(r"^(?P<wall>[\d.]+)\s*s?$")
_HEADER_RESULT = re.compile(
    r"(?P<passed>\d+) passed(?:,\s*(?P<skipped>\d+) skipped)?"
)


@dataclass
class TestRecord:
    """The three phase timings pytest reports for one test id."""

    nodeid: str
    phases: dict[str, float] = field(default_factory=dict)

    @property
    def total(self) -> float:
        return sum(self.phases.values())

    @property
    def file(self) -> str:
        return self.nodeid.split("::", 1)[0]

    def phase(self, name: str) -> float:
        return self.phases.get(name, 0.0)


@dataclass
class Profile:
    """Everything the rankings need, parsed out of one artefact."""

    tests: dict[str, TestRecord]
    records: int
    wall_clock: float | None
    passed: int | None
    skipped: int | None

    @property
    def attributed(self) -> float:
        return sum(t.total for t in self.tests.values())


def parse_artefact(text: str) -> Profile:
    """Parse a ``--durations`` artefact into per-test phase timings.

    Unknown lines (the header, pytest's progress dots, the summary) are
    ignored rather than rejected, so the artefact can carry a prose header.
    """
    tests: dict[str, TestRecord] = {}
    records = 0
    wall_clock: float | None = None
    passed: int | None = None
    skipped: int | None = None

    for line in text.splitlines():
        match = _DURATION_LINE.match(line)
        if match is not None:
            nodeid = match["nodeid"]
            record = tests.get(nodeid)
            if record is None:
                record = tests[nodeid] = TestRecord(nodeid)
            # A phase repeated for one id would mean a corrupt artefact; sum
            # rather than overwrite so no time is silently dropped.
            record.phases[match["phase"]] = (
                record.phases.get(match["phase"], 0.0) + float(match["secs"])
            )
            records += 1
            continue
        summary = _SUMMARY.match(line)
        if summary is not None and wall_clock is None:
            wall_clock = float(summary["wall"])
            passed = int(summary["passed"])
            skipped = int(summary["skipped"]) if summary["skipped"] else 0

    if wall_clock is None:
        # -qq suppressed pytest's summary; fall back to the header, which the
        # artefact is required to carry precisely so this is always possible.
        header = parse_header(text)
        wall_match = _HEADER_WALL.match(header.get("wall clock", "").strip())
        if wall_match is not None:
            wall_clock = float(wall_match["wall"])
        result_match = _HEADER_RESULT.search(header.get("result", ""))
        if result_match is not None:
            passed = int(result_match["passed"])
            skipped = int(result_match["skipped"] or 0)

    return Profile(
        tests=tests,
        records=records,
        wall_clock=wall_clock,
        passed=passed,
        skipped=skipped,
    )


def parse_header(text: str) -> dict[str, str]:
    """Collect the ``# key: value`` lines that precede the duration table.

    Parsing stops at the first duration line so that a ``#``-prefixed comment
    further down the artefact cannot masquerade as a header field.
    """
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if _DURATION_LINE.match(line):
            break
        match = _HEADER_LINE.match(line)
        if match is not None:
            fields.setdefault(match["key"], match["value"])
    return fields


def missing_header_fields(text: str) -> list[str]:
    """Which of ``REQUIRED_HEADER_FIELDS`` the artefact fails to state."""
    fields = parse_header(text)
    return [
        name
        for name in REQUIRED_HEADER_FIELDS
        if name not in fields or not fields[name].strip()
    ]


def other_pytest_processes(ps_output: str, own_pid: int | None = None) -> list[str]:
    """Competing pytest invocations in ``ps -Ao pid,command`` output.

    Our own process (and the shell pipeline that produced the listing) is
    excluded by pid, so a profiling run does not detect itself.
    """
    found: list[str] = []
    for line in ps_output.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        head, _, command = stripped.partition(" ")
        if not head.isdigit():
            continue
        if own_pid is not None and int(head) == own_pid:
            continue
        if "grep" in command:
            continue
        if _PYTEST_PROCESS.search(command):
            found.append(stripped)
    return found


def is_admissible_profile(text: str) -> bool:
    """True when this artefact may be recorded as *the* profile (AC-4).

    An artefact is admissible only when every required header field is present
    and ``solo run`` is affirmative. A run that overlapped another suite is
    recorded as ``solo run: no`` and is re-run rather than consumed.
    """
    if missing_header_fields(text):
        return False
    return parse_header(text)["solo run"].strip().lower() in {"yes", "true"}


def parse_timing_line(line: str) -> dict[str, str] | None:
    """Parse one ``suite-timing.log`` entry, or ``None`` if it is not one.

    Blank lines and ``#`` comments are not entries and return ``None``.

    ``notes`` is the parenthesised note the format has always had; ``extra``
    is a second parenthesised note after the rate bracket, which two entries
    have used since wave 38 (see the line-contract comment above). ``extra``
    is ``""`` when there is none, as every absent group is.
    """
    stripped = line.rstrip("\n")
    if not stripped.strip() or stripped.lstrip().startswith("#"):
        return None
    match = TIMING_LOG_LINE.match(stripped)
    if match is None:
        return None
    return {key: (value or "") for key, value in match.groupdict().items()}


def timing_log_entries(text: str) -> list[dict[str, str]]:
    """Every parsed entry in a ``suite-timing.log``, in file order."""
    return [
        entry
        for entry in (parse_timing_line(line) for line in text.splitlines())
        if entry is not None
    ]


def malformed_timing_lines(text: str) -> list[str]:
    """Lines that are neither blank, nor a comment, nor a well-formed entry."""
    bad: list[str] = []
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if TIMING_LOG_LINE.match(line.rstrip("\n")) is None:
            bad.append(line)
    return bad


def check_log_report(text: str) -> tuple[list[str], int]:
    """``(report lines, exit status)`` for one timing log's text.

    The deliberate reader CARD-238 removed and CARD-239 puts back somewhere
    it belongs. Two tests used to read the owner's live log *as part of the
    suite*, which made the suite's verdict a fact about the machine -- that
    was the defect CARD-238 cut, and it is not coming back. But the
    mechanism it cut had found a real malformed entry (CARD-217's merge-gate
    line), and after the cut nothing would ever notice the next one. So the
    check lives here, as a subcommand somebody runs on purpose, over a path
    they name.

    Pure: it takes the log's text, not its path, so every test here is over
    a log the test constructs. ``--check-log`` is the only thing that reads
    a file, and no test invokes it -- asserted structurally, because a test
    that ran it on the live log would be the original defect wearing this
    card's badge.

    It reports two things, and the second is why the subcommand is worth
    having rather than a one-liner in the shell. Malformed lines, which is
    the check itself; and **how many of the lines carrying a rate bracket
    actually yield a rate field**, which is the question CARD-238's review
    settled for the two entries it could see -- six bracket-bearing lines,
    three ``rate`` fields -- and which nothing has been able to ask of the
    whole log since. If the two numbers differ, some entry is losing a field
    the cost trend is read off.

    Never writes. The log is the owner's (CARD-238's G-1, CARD-239's G-1).
    """
    lines: list[str] = []
    malformed = malformed_timing_lines(text)
    entries = timing_log_entries(text)
    bracketed = [line for line in text.splitlines() if _RATE_BRACKET.search(line)]
    rated = [entry for entry in entries if entry["rate"]]
    lines.append(f"entries: {len(entries)}")
    lines.append(f"malformed: {len(malformed)}")
    for line in malformed:
        lines.append(f"  not an entry: {line.rstrip()}")
    lines.append(
        f"rate recovered: {len(rated)} of {len(bracketed)} lines carrying a "
        "rate bracket"
    )
    if len(rated) != len(bracketed):
        lines.append(
            "  a bracket-bearing line is not giving its rate back; the line "
            "contract above is what to read next"
        )
    status = 1 if malformed or len(rated) != len(bracketed) else 0
    return lines, status


def rank_tests(profile: Profile) -> list[TestRecord]:
    """Slowest tests first; ties broken on the id so the order is stable."""
    return sorted(profile.tests.values(), key=lambda t: (-t.total, t.nodeid))


def rank_files(profile: Profile) -> list[tuple[str, float, int]]:
    """Slowest files first, as ``(path, seconds, test count)``."""
    seconds: dict[str, float] = defaultdict(float)
    counts: dict[str, int] = defaultdict(int)
    for record in profile.tests.values():
        seconds[record.file] += record.total
        counts[record.file] += 1
    return sorted(
        ((path, seconds[path], counts[path]) for path in seconds),
        key=lambda row: (-row[1], row[0]),
    )


def render_heavy_total(profile: Profile) -> tuple[float, int, int]:
    """Return ``(seconds, files seen, tests)`` for the render-heavy set."""
    wanted = set(RENDER_HEAVY_SNAPSHOT)
    seconds = 0.0
    tests = 0
    files: set[str] = set()
    for record in profile.tests.values():
        if record.file in wanted:
            seconds += record.total
            tests += 1
            files.add(record.file)
    return seconds, len(files), tests


def group_totals(profile: Profile) -> list[tuple[str, float, int]]:
    """The deciding table, as ``(name, seconds, tests)`` in report order.

    Deterministic: the order is fixed here, not derived from a dict or a
    sort over floats, so two runs cannot disagree about it.
    """
    render = set(RENDER_HEAVY_SNAPSHOT)
    tests = profile.tests.values()

    def total(predicate) -> tuple[float, int]:
        chosen = [t for t in tests if predicate(t)]
        return sum(t.total for t in chosen), len(chosen)

    is_browser = lambda t: t.file.startswith(BROWSER_FAMILY_PREFIX)  # noqa: E731
    is_render = lambda t: t.file in render  # noqa: E731
    is_property = lambda t: t.file.startswith(PROPERTY_PREFIX)  # noqa: E731
    is_admin = lambda t: t.file in ADMIN_LOCAL_TRIO  # noqa: E731

    rows = [
        ("browser family (Chromium)", *total(is_browser)),
        ("render-heavy frozen set", *total(is_render)),
        ("property corpora", *total(is_property)),
        ("property AND render", *total(lambda t: is_property(t) and is_render(t))),
        ("property OR render", *total(lambda t: is_property(t) or is_render(t))),
        ("admin-local script trio", *total(is_admin)),
        ("everything but the browser family", *total(lambda t: not is_browser(t))),
    ]
    return rows


def phase_totals(profile: Profile) -> dict[str, float]:
    return {
        phase: sum(t.phase(phase) for t in profile.tests.values()) for phase in PHASES
    }


def _pct(part: float, whole: float) -> str:
    if whole <= 0:
        return "n/a"
    return f"{100.0 * part / whole:6.2f}%"


def regrep_render_set(tests_dir: Path) -> list[str]:
    """Re-derive the render-heavy set from a live tree (stderr reporting only)."""
    pattern = re.compile(RENDER_API_PATTERN)
    root = tests_dir.parent
    found = [
        str(path.relative_to(root))
        for path in sorted(tests_dir.rglob("*.py"))
        if pattern.search(path.read_text(encoding="utf-8", errors="replace"))
    ]
    return found


def report(profile: Profile, source: Path, digest: str) -> str:
    """Build the full stdout report. Pure function of its arguments."""
    out: list[str] = []
    add = out.append

    attributed = profile.attributed
    totals = phase_totals(profile)

    add("# Suite duration rankings")
    add(f"# source: {source.name}")
    add(f"# sha256: {digest}")
    add(f"# tests with timings: {len(profile.tests)}")
    add(f"# phase records parsed: {profile.records}")
    add(f"# attributed time (setup+call+teardown): {attributed:.2f}s")
    for phase in PHASES:
        add(f"#   {phase:<9} {totals[phase]:9.2f}s  {_pct(totals[phase], attributed)}")
    if profile.wall_clock is not None:
        add(f"# pytest wall clock: {profile.wall_clock:.2f}s")
        add(
            f"# unattributed (collection, imports, session fixtures): "
            f"{profile.wall_clock - attributed:.2f}s "
            f"{_pct(profile.wall_clock - attributed, profile.wall_clock)}"
        )
    if profile.passed is not None:
        add(f"# result: {profile.passed} passed, {profile.skipped} skipped")
    add("#")
    add("# Shares below are of attributed time, not of wall clock.")
    add("")

    add("## Cost families (the deciding table)")
    add("")
    add(f"{'family':<36} {'total':>9} {'share':>7} {'tests':>6} {'ms/test':>8}")
    for name, seconds, count in group_totals(profile):
        per = f"{seconds / count * 1000:.0f}" if count else "n/a"
        add(
            f"{name:<36} {seconds:>8.2f}s {_pct(seconds, attributed)} "
            f"{count:>6} {per:>8}"
        )
    add("")

    add(f"## {TOP_TESTS} slowest tests")
    add("")
    add(f"{'#':>4}  {'total':>9}  {'setup':>9}  {'call':>9}  {'teardown':>9}  test")
    for index, record in enumerate(rank_tests(profile)[:TOP_TESTS], start=1):
        add(
            f"{index:>4}  {record.total:>8.3f}s  {record.phase('setup'):>8.3f}s  "
            f"{record.phase('call'):>8.3f}s  {record.phase('teardown'):>8.3f}s  "
            f"{record.nodeid}"
        )
    add("")

    add(f"## {TOP_FILES} slowest files")
    add("")
    add(f"{'#':>4}  {'total':>9}  {'share':>7}  {'tests':>6}  {'s/test':>7}  file")
    for index, (path, seconds, count) in enumerate(
        rank_files(profile)[:TOP_FILES], start=1
    ):
        add(
            f"{index:>4}  {seconds:>8.2f}s  {_pct(seconds, attributed)}  "
            f"{count:>6}  {seconds / count:>6.3f}s  {path}"
        )
    add("")

    heavy_secs, heavy_files, heavy_tests = render_heavy_total(profile)
    add("## Render-heavy files (the render hypothesis)")
    add("")
    add(f"files in the frozen set: {len(RENDER_HEAVY_SNAPSHOT)}")
    add(f"files that contributed timings: {heavy_files}")
    add(f"tests in those files: {heavy_tests}")
    add(f"time: {heavy_secs:.2f}s")
    add(f"share of attributed time: {_pct(heavy_secs, attributed)}")
    if profile.wall_clock is not None:
        add(f"share of wall clock: {_pct(heavy_secs, profile.wall_clock)}")
    add("")
    add("## Non-render remainder")
    add("")
    add(f"time: {attributed - heavy_secs:.2f}s")
    add(f"share of attributed time: {_pct(attributed - heavy_secs, attributed)}")

    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "artefact",
        type=Path,
        nargs="?",
        default=None,
        help="suite-durations-<date>.txt",
    )
    parser.add_argument(
        "--check-log",
        type=Path,
        metavar="PATH",
        dest="check_log",
        default=None,
        # The path is the caller's to give and there is no default, which is
        # deliberate twice over. A default would put the owner's gitignored
        # timing log's path into this file as a constant -- and this file is
        # one of the two territories tests/test_suite_profile.py's AC-1 guard
        # walks, so that constant is the mutant review cycle 2 planted here
        # and watched survive. It would also make the subcommand a thing that
        # reads the owner's log when run with no argument, which is the
        # opposite of deliberate.
        help="read the timing log at PATH and report lines the entry "
        "contract rejects; exits 1 if it finds any. Reads only",
    )
    parser.add_argument(
        "--verify-render-set",
        type=Path,
        metavar="TESTS_DIR",
        default=None,
        help="re-grep this tests/ tree and report drift from the frozen set "
        "(stderr only; stdout is unaffected)",
    )
    args = parser.parse_args(argv)

    if args.check_log is not None:
        lines, status = check_log_report(
            args.check_log.read_text(encoding="utf-8")
        )
        stream = sys.stderr if status else sys.stdout
        for line in lines:
            print(line, file=stream)
        return status

    if args.artefact is None:
        parser.error("give an artefact to rank, or --check-log PATH")

    raw = args.artefact.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    profile = parse_artefact(raw.decode("utf-8", errors="replace"))
    if not profile.tests:
        print(
            f"{args.artefact}: no duration lines found -- is this a "
            f"--durations artefact?",
            file=sys.stderr,
        )
        return 2

    sys.stdout.write(report(profile, args.artefact, digest))

    if args.verify_render_set is not None:
        live = set(regrep_render_set(args.verify_render_set))
        frozen = set(RENDER_HEAVY_SNAPSHOT)
        for path in sorted(live - frozen):
            print(f"render-set drift: added since freeze: {path}", file=sys.stderr)
        for path in sorted(frozen - live):
            print(f"render-set drift: gone since freeze: {path}", file=sys.stderr)
        if live == frozen:
            print("render-set drift: none", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
