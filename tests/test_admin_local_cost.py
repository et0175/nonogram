"""CARD-236 -- what the admin-local script tests cost, and what they still prove.

What CARD-217 measured, and what the cost turned out to be
----------------------------------------------------------
CARD-217 measured the three admin-local script files at **117.16 s across 83
tests, 12.73 % of a 930.81 s suite**, with ``tests/test_start_admin_local.py``
alone the third-slowest file in the repo, and attributed it to "pure subprocess
spawning". CARD-236 was cut to spawn once per scenario instead of once per
assertion, and to replace execution with parsing wherever only the script's
text was being checked.

**Measurement says neither was needed, because spawning is not the cost.** On
this host:

* one ``--check-only`` run of ``start_admin_local.sh`` with the five tool stubs
  freshly written into the test's own ``tmp_path``: **1.10--1.38 s**;
* the same run against a stub directory a previous run had already executed:
  **0.07--0.12 s**;
* writing those five files at all: **0.003--0.006 s**.

So ~92 % of each run was the *first* ``execve`` of a newly created executable,
not the spawn. The host runs Microsoft Defender with real-time protection
(``wdavdaemon privileged``), which scans an executable synchronously the first
time it runs; the trio burned 11 s of CPU over 118 s of wall clock, so it was
blocked, not computing. A bare ``bash -c :`` costs 4 ms here and a fresh
interpreter 18 ms, which is the other half of the same finding: a *repeated*
spawn is cheap.

The whole of this card is therefore :func:`tests.test_start_admin_local.tool_dir`
-- the stub directory is built once per process per stub set instead of once per
test -- and **no test stopped executing its script**. Nothing was converted to
parsing and nothing was retired, so there is no named survivor to declare: the
set of node ids is the same before and after, which
:class:`TestAdminLocalTests_ShareIsRecorded` asserts rather than assumes.

What a parsing-for-execution trade would have given up
------------------------------------------------------
It is worth saying why not, since the card offered it. Reading
``scripts/start_admin_local.sh`` to see that it *writes* ``psql "$PSQL_URL"``
does not prove it *passes* the URL: CARD-151's two defects were both of that
shape -- the script named the right things and handed psql a string it cannot
parse. The suite's whole method is that the psql model
(``tests/test_start_admin_local._PSQL_MODEL``) reads the argument list the way
real psql does and logs what it would have connected to, which only exists if
the script ran. Converting those assertions to a grep would have bought the
same seconds this card gets for free and given up the one thing that caught
CARD-151.

Six tests in the trio already assert on text alone and always did -- they check
``scripts/README.md`` and the three copies of the URL-resolution block against
each other. :class:`TestAdminLocalTests_ExecutionSetIsDeclared` pins that set
at exactly those six, so a later conversion cannot be slipped in silently.

What is recorded here and what is not
-------------------------------------
The trio went from **116.04 s to 13.38 s of attributed time** over 83
unchanged tests, 1398 ms/test to 161 ms/test, and the two further pairs taken
the same way agree (114.73/10.77 and 110.54/10.47). Both halves of every pair
were recorded while CARD-222's fix agent held
``meta/kanban/.full-suite.lock`` in a sibling worktree, so **G-3's solo
profile is not met by this card** and the figures are loaded-host figures.
The bars below are therefore ratios, which cancel a host that was slow for
both halves, and
:meth:`TestAdminLocalTests_ShareIsRecorded.test_neither_artefact_claims_to_be_the_solo_profile_g3_asks_for`
keeps the artefacts from being read as the settled measurement. The settled
figure is the orchestrator's quiet full-suite profile at the merge gate, where
the trio should come in around 13 s and the suite around 816 s.

Cost
----
This file runs ~11 scripts of its own (one per reintroduced defect, plus the
controls) at ~0.1 s each, parses two artefacts, and makes two AST passes over
four files -- 1.3 s in the trio's own run, measured, against the ~103 s the
card returns.
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

from tests.helpers.admin_scripts import SCRIPTS, STUB_USER
from tests.helpers.admin_scripts import connections as sibling_connections
from tests.helpers.admin_scripts import run_script as run_sibling
from tests.test_start_admin_local import DEFAULT_DB, connections, run_script

REPO_ROOT = Path(__file__).resolve().parent.parent
PROFILING = REPO_ROOT / "meta" / "profiling"

#: CARD-217's own recording, read for its node ids and quoted for its figures.
#: Never rewritten by this card (G-3's method, not its artefact).
CARD_217_ARTEFACT = PROFILING / "suite-durations-20261015.txt"
#: This card's two recordings: the trio alone, before and after the change.
BEFORE_ARTEFACT = PROFILING / "card-236-trio-before.txt"
AFTER_ARTEFACT = PROFILING / "card-236-trio-after.txt"
DOCUMENT = PROFILING / "card-236-admin-local-subprocess-cost.md"

#: CARD-217's figures for the trio and for the suite that holds it, quoted from
#: ``meta/profiling/suite-hotspots-20261015.md``. The trio figures are
#: re-derived from its artefact below rather than trusted; the suite's
#: attributed total is the denominator the projected share is taken against.
CARD_217_TRIO_SECONDS = 117.16
CARD_217_TRIO_SHARE_PCT = 12.73
CARD_217_TRIO_TESTS = 83
CARD_217_ATTRIBUTED_SECONDS = 920.63

#: The bar AC-1 is read against. "Materially below 12.73 %" is taken as *at
#: most a quarter of it*; the recorded result is 1.64 %, so the bar has room
#: for a host three times slower than this one before it goes slack.
SHARE_BAR_PCT = CARD_217_TRIO_SHARE_PCT / 4
#: And the saving itself, as a ratio of attributed seconds. Recorded at 8.67x
#: on the committed pair, and 10.65x / 10.56x on the two further pairs the
#: document records. The bar is 5x, which is both well clear of the +-20 %
#: run-to-run band CARD-217 measured on this host and well clear of the
#: contention the recordings were taken under.
SPEEDUP_BAR = 5.0


def _load_ranker() -> ModuleType:
    """``meta/profiling/rank_durations.py``, loaded by path.

    ``meta/`` is not a package and is not on ``sys.path``; this is the same
    loader ``tests/test_suite_profile.py`` uses, for the same reason.
    """
    name = "card236_rank_durations"
    spec = importlib.util.spec_from_file_location(
        name, PROFILING / "rank_durations.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ranker = _load_ranker()

TRIO_ROW = "admin-local script trio"


def _trio(artefact: Path) -> tuple[float, int]:
    """``(seconds, tests)`` for the trio, from the ranker's own deciding table."""
    profile = ranker.parse_artefact(artefact.read_text(encoding="utf-8"))
    for name, seconds, tests in ranker.group_totals(profile):
        if name == TRIO_ROW:
            return seconds, tests
    raise AssertionError(f"{TRIO_ROW!r} is no longer a row of the deciding table")


def _trio_node_ids(artefact: Path) -> set[str]:
    profile = ranker.parse_artefact(artefact.read_text(encoding="utf-8"))
    return {
        nodeid
        for nodeid, record in profile.tests.items()
        if record.file in ranker.ADMIN_LOCAL_TRIO
    }


def projected_share_pct(trio_seconds: float) -> float:
    """The trio's share of the suite, with only the trio's own cost changed.

    AC-1 asks for a share, and a share needs the whole suite in its
    denominator -- but re-profiling the whole suite is this card's merge gate,
    not this card's measurement, and a full-suite run is what the owner's
    standing instruction forbids here. So the trio's measured seconds are put
    back into CARD-217's suite with every other test left exactly as it
    recorded them. It is a projection and is labelled one wherever it appears;
    the merge gate's own profile is what confirms it.
    """
    rest = CARD_217_ATTRIBUTED_SECONDS - CARD_217_TRIO_SECONDS
    return 100.0 * trio_seconds / (rest + trio_seconds)


# ==========================================================================
# AC-1 -- the saving, recorded by the committed script. NOT on solo runs:
# see test_neither_artefact_claims_to_be_the_solo_profile_g3_asks_for.
# ==========================================================================


class TestAdminLocalTests_ShareIsRecorded:
    """AC-1: the trio costs materially less, and both halves are written down."""

    def test_both_artefacts_state_their_host_conditions(self) -> None:
        """Every required header field, on both halves of the comparison."""
        for artefact in (BEFORE_ARTEFACT, AFTER_ARTEFACT):
            text = artefact.read_text(encoding="utf-8")
            assert ranker.missing_header_fields(text) == [], artefact.name

    def test_neither_artefact_claims_to_be_the_solo_profile_g3_asks_for(
        self,
    ) -> None:
        """G-3 is **not** met by these two recordings, and they say so.

        ``is_admissible_profile`` is the ranker's own gate: an artefact may be
        read as *the* profile only when it declares ``solo run: yes``. Both of
        these declare ``no``. CARD-222's fix agent held
        ``meta/kanban/.full-suite.lock`` in a sibling worktree through the
        window in which they were taken, so neither is a solo run, and no
        wording makes one.

        This test exists so that cannot be forgotten: it fails the day somebody
        edits a ``solo run:`` line to ``yes`` without re-measuring on a quiet
        host, which is the one way these figures could quietly become the
        settled measurement. The settled measurement is the orchestrator's
        full-suite profile at the merge gate; when that is recorded, this test
        is what should be replaced by the admissibility check it stands in for.
        """
        for artefact in (BEFORE_ARTEFACT, AFTER_ARTEFACT):
            text = artefact.read_text(encoding="utf-8")
            assert not ranker.is_admissible_profile(text), (
                f"{artefact.name} now declares itself a solo run. If it was "
                f"re-measured on a quiet host, record that in {DOCUMENT.name} "
                f"and retire this test; if only the header was edited, G-3 is "
                f"still unmet and the header is now wrong"
            )
            assert "solo run: no" in text, artefact.name

    def test_both_artefacts_declare_themselves_trio_only_runs(self) -> None:
        """A trio-only artefact must not read as a suite profile.

        Its ``attributed`` total *is* the trio, so a share taken against it
        would be 100 %. The header's ``command`` is where that is visible, so
        it has to name all three files and nothing else.
        """
        for artefact in (BEFORE_ARTEFACT, AFTER_ARTEFACT):
            command = ranker.parse_header(artefact.read_text(encoding="utf-8"))[
                "command"
            ]
            for name in ranker.ADMIN_LOCAL_TRIO:
                assert name in command, (artefact.name, name, command)

    def test_the_before_reproduces_the_number_the_card_was_cut_on(self) -> None:
        """The before column is re-measured here, not quoted from CARD-217.

        CARD-217 warns that this host's run-to-run spread reaches 19 % and that
        a difference under ~20 % is noise, so the band is 20 %. A before that
        fell outside it would mean the two halves are not comparable and the
        ratio below says nothing.
        """
        seconds, tests = _trio(BEFORE_ARTEFACT)

        assert tests == CARD_217_TRIO_TESTS, (
            f"the before run timed {tests} trio tests, CARD-217 timed "
            f"{CARD_217_TRIO_TESTS}"
        )
        assert abs(seconds - CARD_217_TRIO_SECONDS) / CARD_217_TRIO_SECONDS < 0.20, (
            f"the before run cost {seconds:.2f}s against CARD-217's "
            f"{CARD_217_TRIO_SECONDS}s, outside this host's measured 20 % band: "
            f"the two halves of the comparison are not comparable"
        )

    def test_the_trio_costs_materially_less_than_it_did(self) -> None:
        """Three bars, measuring three different ways of being wrong.

        Seconds, because that is what changed. The projected share, because
        that is what AC-1 is phrased in. And the same node ids in both halves,
        because a saving that came from a test no longer running is not this
        card's saving -- it is the loss the card exists to avoid.

        Both halves were recorded on a loaded host (see
        ``test_neither_artefact_claims_to_be_the_solo_profile_g3_asks_for``),
        which is why the bars are ratios of one half to the other and not
        absolute seconds: a host that was slow for both halves cancels, and the
        5x bar is four times the run-to-run band that could not.
        """
        before_seconds, _ = _trio(BEFORE_ARTEFACT)
        after_seconds, after_tests = _trio(AFTER_ARTEFACT)

        assert after_seconds * SPEEDUP_BAR < before_seconds, (
            f"{after_seconds:.2f}s against {before_seconds:.2f}s is only "
            f"{before_seconds / after_seconds:.1f}x, under the {SPEEDUP_BAR}x "
            f"this card measured"
        )
        assert projected_share_pct(after_seconds) < SHARE_BAR_PCT, (
            f"the projected share is "
            f"{projected_share_pct(after_seconds):.2f} %, not materially below "
            f"CARD-217's {CARD_217_TRIO_SHARE_PCT} %"
        )
        assert after_tests == CARD_217_TRIO_TESTS, after_tests
        assert _trio_node_ids(AFTER_ARTEFACT) == _trio_node_ids(BEFORE_ARTEFACT), (
            "the after run did not time the same tests as the before run, so "
            "some of the saving is a test that stopped running"
        )

    def test_no_test_of_the_trio_was_dropped_since_card_217_measured_it(self) -> None:
        """The before/after pair cannot see a test both halves lost.

        Both halves are this card's own runs, so a test deleted before either
        of them would leave them agreeing. CARD-217's frozen artefact is the
        only record from before the card, so that is what the set is anchored
        to.
        """
        recorded = _trio_node_ids(CARD_217_ARTEFACT)
        assert len(recorded) == CARD_217_TRIO_TESTS, len(recorded)

        missing = recorded - _trio_node_ids(AFTER_ARTEFACT)
        assert missing == set(), (
            f"{len(missing)} test(s) CARD-217 timed are not in this card's "
            f"after run: {sorted(missing)[:5]}"
        )

    def test_the_document_cites_the_artefacts_it_describes(self) -> None:
        """Pin the document to the two runs it reports, the way CARD-217's is.

        The sha256 says *which* artefact. Without it, re-running either half
        and forgetting to update the prose produces a document that reads as
        the measurement of a file it no longer describes.
        """
        document = DOCUMENT.read_text(encoding="utf-8")

        for artefact in (BEFORE_ARTEFACT, AFTER_ARTEFACT):
            digest = hashlib.sha256(artefact.read_bytes()).hexdigest()
            assert artefact.name in document, artefact.name
            assert digest in document, (
                f"{DOCUMENT.name} does not cite the sha256 of "
                f"{artefact.name} ({digest}), so it is not pinned to the run "
                f"it reports"
            )

    def test_the_document_records_the_before_and_the_after(self) -> None:
        document = DOCUMENT.read_text(encoding="utf-8")
        before_seconds, _ = _trio(BEFORE_ARTEFACT)
        after_seconds, _ = _trio(AFTER_ARTEFACT)

        missing = [
            figure
            for figure in (
                f"{before_seconds:.2f} s",
                f"{after_seconds:.2f} s",
                f"{projected_share_pct(after_seconds):.2f} %",
                f"{CARD_217_TRIO_SHARE_PCT} %",
            )
            if figure not in document
        ]
        assert missing == [], (
            f"{DOCUMENT.name} does not state {missing}; AC-1 is that the "
            f"before and the after are both recorded"
        )

    def test_the_bar_would_reject_the_cost_as_it_was(self) -> None:
        """The bars bite: fed the before artefact as its own "after", they fail.

        Without this, "the trio got cheaper" is one committed number read
        against another, and nobody can tell whether the thresholds sit where a
        regression would trip them. Rebuilding the per-test stub directory is
        the one change somebody could actually make, and the before artefact is
        exactly what that change costs, measured.
        """
        before_seconds, _ = _trio(BEFORE_ARTEFACT)

        assert not before_seconds * SPEEDUP_BAR < before_seconds
        assert not projected_share_pct(before_seconds) < SHARE_BAR_PCT, (
            f"the share bar passes CARD-217's own {before_seconds:.2f}s, so it "
            f"would not trip on a full regression and says nothing"
        )


# ==========================================================================
# AC-3 -- which tests execute the scripts, and which never did
# ==========================================================================

#: The four files that hold the trio's 83 tests. The contract mixins live in
#: the helper, applied to both sibling scripts, so a walk of the three test
#: files alone would miss 28 of the 83.
TRIO_SOURCES = (
    "tests/test_start_admin_local.py",
    "tests/test_run_admin_tests.py",
    "tests/test_setup_admin_local.py",
    "tests/helpers/admin_scripts.py",
)

#: Every call that ends in a run of a script: the two harnesses' ``run_script``
#: and the contract mixins' ``self.run`` wrapper around it.
_RUNNERS = frozenset({"run_script", "run_sibling", "run"})

#: The tests of the trio that assert on text alone -- and did so before this
#: card as well. Each is here because the artefact it judges *is* text: either
#: ``scripts/README.md``, or the three scripts' source read against each other.
#: Nothing was moved into this set by CARD-236; it is pinned so that nothing
#: can be, silently.
#:
#: Keyed by file as well as by qualified name: all three test files define a
#: ``test_the_harness_reaches_the_end_of_the_script`` at module level, and a
#: key that could not tell those apart would hide two tests.
TEXT_ONLY_TESTS: dict[str, str] = {
    "tests/test_start_admin_local.py::TestStartAdminLocal_ReadmeMatchesTheScript::"
    "test_it_says_an_exported_database_url_wins": (
        "the claim is a sentence in scripts/README.md; the behaviour behind it "
        "is executed by test_uses_an_exported_url_and_says_so"
    ),
    "tests/test_start_admin_local.py::TestStartAdminLocal_ReadmeMatchesTheScript::"
    "test_a_claim_about_the_scripts_names_the_script_it_holds_for": (
        "CARD-150 F-002: the claim is about scripts this suite deliberately "
        "does not drive, so their source is the only evidence available"
    ),
    "tests/test_start_admin_local.py::TestStartAdminLocal_ReadmeMatchesTheScript::"
    "test_it_no_longer_states_a_database_as_a_bare_prerequisite": (
        "a stale line in scripts/README.md's Prerequisites section"
    ),
    "tests/test_setup_admin_local.py::"
    "test_the_readme_no_longer_says_the_siblings_ignore_an_exported_url": (
        "a stale caveat in scripts/README.md"
    ),
    "tests/test_setup_admin_local.py::"
    "test_the_three_copies_of_the_url_resolution_are_identical": (
        "CARD-152 F-004: the three scripts copy the block rather than source "
        "it, so drift between the copies is a property of the text and of "
        "nothing a single run can show"
    ),
    "tests/test_setup_admin_local.py::test_each_script_defaults_to_its_own_database": (
        "CARD-168: the one line the identity check above leaves out, pinned "
        "exactly; each default is also executed, per script, by "
        "test_with_nothing_exported_it_says_it_used_the_project_default"
    ),
}


def _executes_a_script(node: ast.FunctionDef) -> bool:
    """Whether this test's body reaches one of :data:`_RUNNERS`.

    The same structural method ``tests/test_cli.py`` uses on the package: a
    call to one of those three names is the only way a script is ever run
    here, so its absence is what "this test does not execute" means.
    """
    return bool(
        _RUNNERS
        & {
            call.func.id if isinstance(call.func, ast.Name) else call.func.attr
            for call in ast.walk(node)
            if isinstance(call, ast.Call)
            and isinstance(call.func, (ast.Name, ast.Attribute))
        }
    )


def _split_tests(source: str, prefix: str) -> tuple[set[str], set[str]]:
    """``(executing, text only)`` for one module's source."""
    executing: set[str] = set()
    text_only: set[str] = set()

    def visit(node: ast.AST, qualifier: str) -> None:
        for child in getattr(node, "body", []):
            if isinstance(child, ast.ClassDef):
                visit(child, f"{qualifier}{child.name}::")
            elif isinstance(child, ast.FunctionDef) and child.name.startswith("test_"):
                bucket = executing if _executes_a_script(child) else text_only
                bucket.add(f"{prefix}{qualifier}{child.name}")

    visit(ast.parse(source), "")
    return executing, text_only


def _tests_by_whether_they_execute() -> tuple[set[str], set[str]]:
    """``(executing, text only)`` over :data:`TRIO_SOURCES`, read with ``ast``."""
    executing: set[str] = set()
    text_only: set[str] = set()
    for relative in TRIO_SOURCES:
        source = (REPO_ROOT / relative).read_text(encoding="utf-8")
        found, text = _split_tests(source, f"{relative}::")
        executing |= found
        text_only |= text
    return executing, text_only


class TestAdminLocalTests_ExecutionSetIsDeclared:
    """AC-3: the tests that execute the scripts are listed, with the reason."""

    def test_every_test_that_is_not_declared_text_only_executes_a_script(
        self,
    ) -> None:
        """The reason execution is the claim, stated once for all 66 of them.

        Each of these tests asserts on something only a run produces: the
        script's exit code, the argument list psql was handed (read back
        through CARD-151's model of how real psql reads it), what alembic or
        pytest found in ``DATABASE_URL``, and which of the three branches of
        the check the script took. None of that is in the script's text --
        CARD-151's two defects were a script that named the right database and
        handed psql a string it cannot parse -- so none of it can be read off
        the text.
        """
        executing, text_only = _tests_by_whether_they_execute()

        assert text_only == set(TEXT_ONLY_TESTS), {
            "newly text-only": sorted(text_only - set(TEXT_ONLY_TESTS)),
            "no longer text-only": sorted(set(TEXT_ONLY_TESTS) - text_only),
        }
        # 63 before CARD-244, which added three to tests/test_run_admin_tests.py
        # for the TEST_DATABASE_URL the script now exports.
        assert len(executing) == 66, len(executing)
        assert len(executing) + len(text_only) == 72, (
            "the four sources no longer define 72 tests. The trio collects 86: "
            "the 58 defined in the three test files, plus the 14 the two "
            "contract mixins define in the helper, collected once per sibling "
            "script"
        )

    def test_each_text_only_test_is_declared_with_its_reason(self) -> None:
        for name, reason in TEXT_ONLY_TESTS.items():
            assert len(reason) > 30, (name, reason)

    def test_the_declaration_is_read_from_the_tree_and_not_from_itself(
        self,
    ) -> None:
        """The walk bites: a test that stops running a script moves set.

        Asserted by walking a copy of one source with its one ``run_script``
        call removed, rather than by trusting that the walk works -- which is
        the mutant for the check above, taken in memory so the tree is not
        touched.
        """
        relative = "tests/test_setup_admin_local.py"
        hollowed_test = (
            f"{relative}::TestSetupAdminLocal_ChecksTheTargetDatabase::"
            "test_the_old_bare_check_would_have_passed_here"
        )
        source = (REPO_ROOT / relative).read_text(encoding="utf-8")
        hollowed = source.replace(
            'run = run_script(SCRIPT, tmp_path, existing_dbs=["stub_owner", "postgres"])',
            "run = None",
        )
        assert hollowed != source, "the anchor for the mutant has moved"

        before_executing, _ = _split_tests(source, f"{relative}::")
        after_executing, after_text = _split_tests(hollowed, f"{relative}::")

        assert hollowed_test in before_executing, hollowed_test
        assert hollowed_test in after_text, (
            "a test whose only run was deleted still reads as executing, so "
            "the walk cannot tell a converted test from an executing one"
        )
        assert before_executing - after_executing == {hollowed_test}


# ==========================================================================
# AC-4 -- the old defects, reintroduced one at a time
# ==========================================================================

START = "start_admin_local.sh"
SETUP = "setup_admin_local.sh"
RUN = "run_admin_tests.sh"

#: CARD-150's original ``[5/6]``: a failed migration warned and carried on,
#: with alembic's own words discarded.
_MIGRATION_BLOCK = '''    if MIGRATION_OUTPUT="$(alembic upgrade head 2>&1)"; then
        echo -e "${GREEN}✓ Migrations completed${NC}"
    else
        echo -e "${RED}✗ Migrations failed${NC}"'''
_MIGRATION_DEFECT = '''    if alembic upgrade head > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Migrations completed${NC}"
    elif true; then
        echo -e "${YELLOW}⚠ Migrations may have issues (but continuing)${NC}"
    else
        echo -e "${RED}✗ Migrations failed${NC}"'''

#: CARD-151's refusal of a URL that names no database.
_NO_DATABASE_REFUSAL = '''if [ -z "$DB_NAME" ]; then
    echo -e "${RED}✗ DATABASE_URL names no database${NC}"'''
_NO_DATABASE_ACCEPTED = '''if false; then
    echo -e "${RED}✗ DATABASE_URL names no database${NC}"'''


def _defect(script: str, before: str, after: str) -> str:
    """``scripts/<script>`` with one defect put back, exactly once.

    The scripts on disk are never written to: G-1 keeps them out of this
    card's diff, and the text goes to the harness's ``script_text``.
    """
    source = (SCRIPTS / script).read_text(encoding="utf-8")
    assert source.count(before) == 1, (
        f"the anchor for this defect occurs {source.count(before)} times in "
        f"{script}, so the mutation is not the one described"
    )
    return source.replace(before, after)


class TestAdminLocalTests_StillCatchesTheOldDefects:
    """AC-4: each of CARD-150's, CARD-151's and CARD-152's defects is still seen.

    Each test puts one defect back into a copy of the script, runs it through
    the same harness the trio uses, and asserts that the observable its named
    guard keys on is now wrong -- which is what makes that guard red. The
    guards themselves are named rather than invoked: running them would mean a
    child pytest per defect, and the standing claim here is about the harness's
    *visibility* of the defect, which is the part sharing a stub directory
    could in principle have broken.

    ``meta/profiling/card-236-admin-local-subprocess-cost.md`` records the
    other half: every one of these defects run against the whole trio, with the
    test files as they were and as they are, and the same tests red both times.
    """

    def test_a_bare_psql_on_the_local_branch_is_still_visible(
        self, tmp_path: Path
    ) -> None:
        """CARD-150's headline defect. Guard: ``test_the_local_branch_checks_the_target_database``."""
        text = _defect(
            START,
            'elif psql "$PSQL_URL" -c "SELECT 1"',
            'elif psql -c "SELECT 1"',
        )

        run = run_script(tmp_path, "--check-only", script_text=text)
        absent = run_script(
            tmp_path / "absent",
            "--check-only",
            missing_db=DEFAULT_DB,
            script_text=text,
        )

        assert run.called("psql"), run.calls
        assert not any(DEFAULT_DB in call for call in run.called("psql")), (
            "the guard asserts every psql names the target database and the "
            f"defect would still satisfy it: {run.calls}"
        )
        # And the user-visible symptom is back: a green tick while the panel's
        # own database does not exist.
        assert absent.returncode == 0, absent.output
        assert "reachable (Homebrew)" in absent.stdout, absent.output

    def test_a_hardcoded_export_over_the_callers_url_is_still_visible(
        self, tmp_path: Path
    ) -> None:
        """CARD-150's second defect. Guard: ``test_an_exported_url_survives_into_the_environment``."""
        text = _defect(
            START,
            "\nexport DATABASE_URL\n",
            '\nexport DATABASE_URL="$DEFAULT_DATABASE_URL"\n',
        )
        url = "postgresql://someone@localhost:5432/nonogram_dev"

        run = run_script(
            tmp_path, "--check-only", database_url=url, script_text=text
        )

        step4 = run.output.split("[4/6]", 1)[1].split("[5/6]", 1)[0]
        assert url not in step4, (
            f"the guard reads the caller's URL out of step [4/6] and the "
            f"defect would still show it there:\n{step4}"
        )
        assert DEFAULT_DB in step4, step4

    def test_a_migration_failure_that_warns_and_continues_is_still_visible(
        self, tmp_path: Path
    ) -> None:
        """CARD-150's third defect. Guard: ``TestStartAdminLocal_RefusesAndReportsAFailedMigration::test_exits_non_zero``."""
        text = _defect(START, _MIGRATION_BLOCK, _MIGRATION_DEFECT)

        run = run_script(
            tmp_path,
            "--check-only",
            alembic_fails=True,
            alembic_message="FAILED: Can't locate revision identified by 'deadbeef'",
            script_text=text,
        )

        assert run.returncode == 0, run.output
        assert "Migrations failed" not in run.output, run.output
        assert "may have issues" in run.output, run.output
        assert "[6/6]" in run.output, run.output

    def test_alembics_discarded_message_is_still_visible(
        self, tmp_path: Path
    ) -> None:
        """CARD-150 review F-001. Guard: ``test_alembics_own_message_reaches_the_output``.

        The defect is the ``2>&1`` dropped from the capture: the script then
        takes alembic's stdout only, and alembic's message -- which it writes
        to stderr -- goes straight past the script to the terminal instead of
        into the script's own indented quote. ``run.output`` is both streams
        concatenated and cannot tell those apart, which is why the guard reads
        ``run.stdout``; this is the mutant that shows the guard is reading the
        right stream.
        """
        message = "FAILED: Can't locate revision identified by 'deadbeef'"
        text = _defect(
            START,
            'MIGRATION_OUTPUT="$(alembic upgrade head 2>&1)"',
            'MIGRATION_OUTPUT="$(alembic upgrade head)"',
        )

        run = run_script(
            tmp_path,
            "--check-only",
            alembic_fails=True,
            alembic_message=message,
            script_text=text,
        )

        assert run.returncode != 0, run.output
        assert message in run.stderr, (
            "the message did not even reach the terminal past the script, so "
            f"this is not the defect being described:\n{run.stderr}"
        )
        assert f"    {message}" not in run.stdout, (
            f"the guard asserts the script quotes alembic indented on its own "
            f"stdout, and the defect would still satisfy it:\n{run.stdout}"
        )
        assert "(no output)" in run.stdout, run.stdout

    def test_a_driver_qualified_url_handed_to_psql_whole_is_still_visible(
        self, tmp_path: Path
    ) -> None:
        """CARD-151's first defect. Guard: ``TestStartAdminLocal_AcceptsADriverQualifiedUrl::test_psql_is_handed_a_url_it_parses``."""
        text = _defect(
            START,
            'PSQL_URL="${DATABASE_URL%%://*}"\n'
            'PSQL_URL="${PSQL_URL%%+*}://${DATABASE_URL#*://}"',
            'PSQL_URL="$DATABASE_URL"',
        )
        url = "postgresql+psycopg2://someone:secret@localhost:5432/nonogram_dev"

        run = run_script(
            tmp_path, "--check-only", database_url=url, script_text=text
        )

        assert run.returncode != 0, run.output
        assert [c["dbname"] for c in connections(run)] == [url], (
            "the psql model should have taken the whole driver-qualified URL "
            f"as a database name: {run.calls}"
        )

    def test_a_url_that_names_no_database_being_accepted_is_still_visible(
        self, tmp_path: Path
    ) -> None:
        """CARD-151's second defect. Guard: ``TestStartAdminLocal_RefusesAUrlThatNamesNoDatabase``."""
        text = _defect(START, _NO_DATABASE_REFUSAL, _NO_DATABASE_ACCEPTED)

        run = run_script(
            tmp_path,
            "--check-only",
            database_url="postgresql://someone@localhost:5432/",
            existing_dbs=["someone", STUB_USER, "nonogram_dev"],
            script_text=text,
        )

        assert run.returncode == 0, run.output
        assert "names no database" not in run.stdout, run.stdout
        # The green tick naming no database at all, which is the defect.
        assert "database '' reachable" in run.stdout, run.stdout

    def test_the_siblings_bare_psql_is_still_visible(self, tmp_path: Path) -> None:
        """CARD-152's defect in setup_admin_local.sh. Guard: ``test_the_old_bare_check_would_have_passed_here``."""
        text = _defect(
            SETUP,
            'elif psql "$PSQL_URL" -c "SELECT 1"',
            'elif psql -c "SELECT 1"',
        )

        run = run_sibling(
            SETUP,
            tmp_path,
            existing_dbs=[STUB_USER, "postgres"],
            script_text=text,
        )

        assert run.returncode == 0, run.output
        assert "Setup complete!" in run.stdout, run.output
        assert [c["dbname"] for c in sibling_connections(run)] == [STUB_USER], (
            f"the check connected to {sibling_connections(run)} rather than to "
            f"the server's default database, so the defect is not the one "
            f"CARD-152 fixed"
        )

    def test_the_siblings_hardcoded_export_is_still_visible(
        self, tmp_path: Path
    ) -> None:
        """CARD-152's overwrite in run_admin_tests.sh. Guard: ``TestSiblingScripts_ExportedDatabaseUrlWins``."""
        text = _defect(
            RUN,
            "\nexport DATABASE_URL\n",
            '\nexport DATABASE_URL="$DEFAULT_DATABASE_URL"\n',
        )
        url = "postgresql://someone@localhost:5432/nonogram_mine_test"

        run = run_sibling(
            RUN,
            tmp_path,
            database_url=url,
            existing_dbs=["nonogram_mine_test", "nonogram_test"],
            script_text=text,
        )

        assert run.handed("pytest") != [url], (
            f"the guard asserts pytest saw the caller's URL and the defect "
            f"would still satisfy it: {run.calls}"
        )
        assert run.handed("pytest") == [
            "postgresql://postgres:postgres@localhost:5432/nonogram_test"
        ], run.calls

    def test_the_test_runners_default_is_still_visible(
        self, tmp_path: Path
    ) -> None:
        """CARD-168's default. Guard: ``test_with_nothing_exported_it_checks_and_uses_nonogram_test``."""
        text = _defect(
            RUN,
            'DEFAULT_DATABASE_URL="postgresql://postgres:postgres@localhost:5432/nonogram_test"',
            'DEFAULT_DATABASE_URL="postgresql://postgres:postgres@localhost:5432/nonogram_poc"',
        )

        run = run_sibling(
            RUN, tmp_path, existing_dbs=["nonogram_test"], script_text=text
        )

        assert run.returncode != 0, run.output
        assert "Database 'nonogram_poc' is not reachable" in run.stdout, run.output
        assert run.called("pytest") == [], run.calls

    def test_the_unmutated_scripts_are_the_control(self, tmp_path: Path) -> None:
        """Each assertion above is only evidence if the script passes unmutated.

        Three runs, one per script, through the same ``script_text`` door the
        defects use -- so a mutation that silently failed to apply, or a
        harness that cannot run a script handed as text at all, is caught here
        rather than read as nine dead defects.
        """
        start = run_script(
            tmp_path / "start",
            "--check-only",
            script_text=(SCRIPTS / START).read_text(encoding="utf-8"),
        )
        assert start.returncode == 0, start.output
        assert "All checks passed" in start.output

        for i, (script, finished) in enumerate(
            ((SETUP, "Setup complete!"), (RUN, "Tests completed!"))
        ):
            run = run_sibling(
                script,
                tmp_path / f"sibling{i}",
                script_text=(SCRIPTS / script).read_text(encoding="utf-8"),
            )
            assert run.returncode == 0, (script, run.output)
            assert finished in run.stdout, (script, run.output)
