"""COMP-008 tests: the submission — form body to pipeline to page (CARD-020).

    AC-049  TestWebUI_SubmitRunsSamePipelineAndReportsFiles
    AC-050  TestWebUI_RejectsOutOfRangeSizeLikeCLI
    AC-051  TestWebUI_ReportsAbandonedGenerationGracefully
    EC-003  PropertyTest_WebUI_SurfacesAnyPipelineErrorAsStructuredFailure

Every criterion here is a statement about what a *browser* gets back, so the
three AC classes drive a real socket through ``tests.test_web_server``'s
helpers rather than calling ``handler`` methods with a fabricated ``self``.
The helpers are imported rather than re-written for the reason that module
imports ``tests.test_cli``'s guard rather than reimplementing it: two copies of
a request helper drift, and a drifted copy is how a test starts asserting
something about a request the server never received.

The one thing they cannot show is that the values on the page came from *this*
submission rather than from a default, so each class also pins the mapping
itself — ``submission.read`` is a pure function over a body string, and what it
builds is compared against what ``cli.build_parser`` builds from the argv that
means the same thing. That comparison is the whole of FR-017's "the same
options as the CLI": not two lists that happen to agree today, but the same
value reached two ways.

Where this module deviates from the criteria as written
------------------------------------------------------
AC-049 names difficulty "Medium" and CARD-020 was cut at wave 13, before the
difficulty scorer and the built-in library met. They do not produce a Medium
puzzle: every built-in template at 20x20 scores Easy (checked, not assumed —
:func:`test_every_built_in_template_scores_easy_at_this_size` below), and
library mode has no randomness for POL-004 to resample into another tier, so
``--difficulty Medium`` on a library key is a run that abandons after 20
identical attempts. AC-049's happy path is therefore exercised with "Easy",
which is the tier the criterion's own options actually produce; the Medium
request is not discarded but moved to where it is now true, as AC-051's
"options make every candidate fail the difficulty checks up to the retry
bound". Recorded in CARD-020's worktree notes.
"""

from __future__ import annotations

import html
import json
import os
import re
import time
import urllib.parse
from collections.abc import Iterator
from pathlib import Path

import pytest

from nonogram import cli, errors, export, orchestrator, web
from nonogram.web import handler, pages, server, submission

# The running-server helpers and the ``(status, headers, body)`` shape live in
# the sibling module that introduced them (AC-052's socket tests). Imported so
# there is exactly one of each.
from tests import test_web_server as web_tests

#: The library key AC-049 names, and the template AC-051 asks for a tier the
#: library cannot deliver.
_KEY = "cat"

#: The size AC-049 names, as the form's single box carries it.
_SIZE = 20

#: Cap on how long a submission may take to answer, in seconds. Not a
#: performance assertion — ADR-0001's budget is 30s and ADR-0011's cooperative
#: deadline is what enforces it — but AC-051's "without hanging" needs *some*
#: bound, and it has to be one a failure trips rather than a slow machine.
_SUBMISSION_BUDGET_S = orchestrator.GENERATION_BUDGET_SECONDS + 10


@pytest.fixture
def running_server() -> Iterator[server.LoopbackHTTPServer]:
    """The server under test, on a kernel-chosen port.

    A local copy of the sibling module's fixture because a fixture is not
    importable as a fixture; the *helper* it wraps is the shared one.
    """
    with web_tests._running(web.create_server(0)) as running:
        yield running


def _submit(port: int, fields: dict[str, str | list[str]]) -> web_tests._Response:
    """Post ``fields`` to the form's action, exactly as a browser would.

    A list value is expanded into several pairs sharing one name, which is how
    a browser sends several ticked checkboxes and the whole reason
    ``export_formats`` arrives as a list.
    """
    pairs: list[tuple[str, str]] = []
    for name, value in fields.items():
        if isinstance(value, list):
            pairs.extend((name, one) for one in value)
        else:
            pairs.append((name, value))
    return web_tests._request(
        port,
        method="POST",
        path=pages.FORM_ACTION,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        body=urllib.parse.urlencode(pairs).encode("utf-8"),
    )


def _outcome(body: bytes) -> str | None:
    """The page's own machine-readable verdict, or ``None`` if it has none.

    Read off the ``data-outcome`` attribute rather than by matching prose:
    ``pages`` is free to reword a heading, and a test that asserted on the
    words would either break for a rewording or be loose enough to pass on the
    wrong page.
    """
    found = re.search(rb'data-outcome="([a-z]+)"', body)
    return found.group(1).decode() if found else None


def _paths_on(body: bytes) -> list[str]:
    """Every file path the result page lists, in the order it lists them."""
    return [
        match.decode()
        for match in re.findall(rb"<li><code>([^<]+)</code></li>", body)
    ]


#: The prefix ``cli._report`` puts in front of every failure it prints. The
#: one thing the two adapters are allowed to differ by: a console line names
#: the program, a page is already on it.
_CLI_ERROR_PREFIX = "nonogram: error: "


def _cli_error_message(argv: list[str], capsys: pytest.CaptureFixture[str]) -> str:
    """The message ``nonogram generate`` prints to stderr for ``argv``.

    The second half of every "the same error the CLI would raise" assertion
    below. Deliberately goes through ``cli.main`` rather than raising the error
    class directly: the claim is about what the *other adapter* reports for the
    same request, and that is a fact about a run, not about a class.

    Captured stderr is drained first, because the server under test logs every
    request it answers to the same stream — ``BaseHTTPRequestHandler``'s access
    log — and a submission has always just happened when this is called. The
    prefix is asserted rather than merely stripped, so this cannot quietly
    return a whole access-log line as "the message".
    """
    capsys.readouterr()
    cli.main(argv)
    printed = capsys.readouterr().err
    _, prefix, message = printed.partition(_CLI_ERROR_PREFIX)
    assert prefix, printed
    return message.split("\n", 1)[0].strip()


def _shown(text: str) -> bytes:
    """``text`` as it must appear in a page body: escaped, then encoded.

    Every message these pages carry has been through :func:`html.escape`, and
    several domain messages quote the value they refused — ``unsupported
    difficulty tier 'extreme'`` — so the raw sentence is *not* what lands in
    the markup. Comparing against the escaped form is both the honest
    assertion and, incidentally, a check that the escaping happened: a page
    that stopped escaping would fail every one of these.
    """
    return html.escape(text).encode("utf-8")


def _no_files_under(directory: Path) -> bool:
    """Whether ``directory`` holds no files at all (it may not even exist)."""
    return not any(path.is_file() for path in directory.rglob("*"))


def _argv_choices(flag: str) -> list[str]:
    """One ``generate`` flag's ``choices``, read off the built parser.

    Read rather than retyped, because the whole point of comparing them is that
    neither list is a copy: a retyped expectation drifts with the thing it is
    supposed to be pinning.
    """
    parser = cli.build_parser()
    for action in parser._subparsers._group_actions:  # type: ignore[union-attr]
        generate = action.choices["generate"]  # type: ignore[attr-defined]
        for option in generate._actions:
            if flag in option.option_strings:
                return list(option.choices or ())
    raise AssertionError(f"the generate parser no longer declares {flag}")


def _argv_mode_choices() -> list[str]:
    """``--mode``'s ``choices``.

    The CLI rejects an unregistered mode with ``choices=`` and the web adapter
    rejects one against ``pages.MODES``; comparing the two against each other
    is what stops the second from quietly becoming a different vocabulary.
    """
    return _argv_choices("--mode")


def _argv_export_choices() -> list[str]:
    """``--export``'s ``choices``.

    The same relationship one delegation over: ``export.for_format`` puts the
    refusal of an unregistered format at the adapter, ``cli.py`` discharges
    that with ``choices=``, and ``submission.read`` discharges it against
    ``export.FORMATS``. The three are meant to be one vocabulary, and reading
    argparse's own list back is what makes that checkable rather than asserted.
    """
    return _argv_choices("--export")


def _form_export_choices() -> set[str]:
    """The formats the rendered form actually offers a checkbox for.

    The third corner of the same triangle, and the one a set comparison against
    ``export.FORMATS`` cannot reach any other way: ``pages`` builds the
    checkboxes from the registry, but only reading the markup back shows that
    what it built is what a browser can post.
    """
    return set(re.findall(r'name="export_formats" value="([^"]+)"', pages.FORM_PAGE))


# --------------------------------------------------------------------------
# AC-049 — the happy path
# --------------------------------------------------------------------------


def test_every_built_in_template_scores_easy_at_this_size() -> None:
    """The premise of this module's AC-049/AC-051 split, checked not assumed.

    AC-049 asks for difficulty "Medium" from library key "cat" and AC-051 asks
    for a request whose candidates all miss the difficulty check. Both are the
    *same* request, and which of the two it is depends on a fact about the
    shipped templates rather than on anything either card says. If a later card
    retunes the scorer or redraws a template, this fails first and says so,
    instead of AC-049 and AC-051 quietly swapping places.
    """
    tiers = {
        key: orchestrator.generate(
            orchestrator.GenerationRequest(mode="library", width=_SIZE, library_key=key)
        ).difficulty_tier
        for key in ("cat", "heart", "house", "moon")
    }

    assert set(tiers) == {"cat", "heart", "house", "moon"}
    assert set(tiers.values()) == {"easy"}, tiers


class TestWebUI_SubmitRunsSamePipelineAndReportsFiles:
    """AC-049 — *given* a web UI submission choosing library key "cat", size
    20x20, difficulty "Easy" (see the module docstring on "Medium"), no name
    override, and export formats png+json, *when* the form is submitted,
    *then* the page reports success with the written PNG/JSON file paths,
    after the same orchestrator pipeline the CLI uses runs to completion.

    "The same pipeline" is asserted as an identity rather than as a
    resemblance: the same options submitted to the form and passed as argv
    produce byte-identical files under the same names. Two adapters, one
    pipeline (FR-017, ADR-0019) — and if the web adapter ever grew a private
    default, a different naming rule, or a second export call, the bytes would
    stop matching.
    """

    def test_the_page_reports_success_and_names_every_file(
        self, running_server: server.LoopbackHTTPServer, tmp_path: Path
    ) -> None:
        """The criterion itself: success, and both written paths on the page."""
        response = _submit(
            running_server.server_port,
            {
                "mode": "library",
                "library_key": _KEY,
                "size": str(_SIZE),
                "difficulty": "Easy",
                "name": "",
                "export_formats": ["png", "json"],
                "out": str(tmp_path),
            },
        )

        assert response.status == 200
        assert response.headers["Content-Type"] == "text/html; charset=utf-8"
        assert _outcome(response.body) == pages.SUCCESS
        listed = _paths_on(response.body)
        assert listed == [str(tmp_path / f"{_KEY}.png"), str(tmp_path / f"{_KEY}.json")]
        assert [Path(one).is_file() for one in listed] == [True, True]

    def test_the_files_are_the_ones_the_cli_writes_for_the_same_options(
        self, running_server: server.LoopbackHTTPServer, tmp_path: Path
    ) -> None:
        """FR-017: the *same* pipeline, compared byte for byte.

        Both runs are given the same seed, so the only thing that could differ
        between them is the adapter — which is the point. A comparison of file
        *names* alone would pass for a web adapter that had grown its own
        rendering call; comparing the bytes leaves nowhere for one to hide.
        """
        through_web, through_argv = tmp_path / "web", tmp_path / "argv"
        submitted = _submit(
            running_server.server_port,
            {
                "mode": "library",
                "library_key": _KEY,
                "size": str(_SIZE),
                "difficulty": "Easy",
                "seed": "7",
                "export_formats": ["png", "json"],
                "out": str(through_web),
            },
        )
        exit_code = cli.main(
            [
                "generate",
                "--mode", "library",
                "--library-key", _KEY,
                "--size", str(_SIZE),
                "--difficulty", "Easy",
                "--seed", "7",
                "--export", "png",
                "--export", "json",
                "--out", str(through_argv),
            ]
        )

        assert (_outcome(submitted.body), exit_code) == (pages.SUCCESS, cli.ExitCode.OK)
        by_name = sorted(path.name for path in through_web.iterdir())
        assert by_name == sorted(path.name for path in through_argv.iterdir())
        assert by_name == [f"{_KEY}.json", f"{_KEY}.png"]
        for name in by_name:
            assert (through_web / name).read_bytes() == (through_argv / name).read_bytes()

    def test_the_one_size_box_travels_as_a_bare_side_exactly_as_argv_does(
        self,
    ) -> None:
        """CARD-020's one open decision, pinned against ``cli``'s own answer.

        The form has a single ``size`` box and ``GenerationRequest`` carries
        two sides, so this card had to decide what one number means. It means
        what a bare ``--size N`` means: ``(N, None)`` — one side stated, the
        other derived from the source's own shape (FR-023, ADR-0022/R4) — and
        emphatically not ``(N, N)``, which since CARD-033 is the *different*
        request that forces a square.

        Asserted against ``cli._extent_token`` rather than against the literal
        pair, so the two adapters cannot be given different readings of one
        number without this failing. Note that neither reading would be caught
        by AC-049 alone: "cat" is a 16x16 square template, so ``(20, None)``
        derives to the very 20x20 the criterion names, which is exactly why
        this needs asserting on the contract rather than on what goes green.
        """
        built = submission.read(f"mode=library&library_key={_KEY}&size={_SIZE}").request

        assert built is not None
        assert (built.width, built.height) == cli._extent_token(str(_SIZE))
        assert (built.width, built.height) == (_SIZE, None)

    def test_the_derived_grid_is_the_square_the_criterion_names(
        self, running_server: server.LoopbackHTTPServer, tmp_path: Path
    ) -> None:
        """AC-049's "20x20": derived, not stated, and it comes out square.

        The behavioural other half of the test above. The submission states one
        number; what the run actually builds is read back off the exported JSON,
        which is the only place on this card's output a grid extent is visible
        (CON-008 keeps the puzzle off the page).
        """
        _submit(
            running_server.server_port,
            {
                "mode": "library",
                "library_key": _KEY,
                "size": str(_SIZE),
                "export_formats": ["json"],
                "out": str(tmp_path),
            },
        )
        exported = json.loads((tmp_path / f"{_KEY}.json").read_text(encoding="utf-8"))

        assert (exported["request"]["width"], exported["request"]["height"]) == (
            _SIZE,
            _SIZE,
        )
        assert len(exported["clues"]["rows"]) == _SIZE
        assert len(exported["clues"]["columns"]) == _SIZE

    def test_an_untouched_name_box_is_the_auto_name_and_not_an_empty_one(
        self, running_server: server.LoopbackHTTPServer, tmp_path: Path
    ) -> None:
        """AC-049's "no name override", as a browser actually sends it.

        A form has one spelling for "I did not fill this in" — the empty string
        — and ``parse_qs`` drops it, so the request carries no name at all and
        FR-015's auto-name applies (here, the library key). Were the empty
        string carried through instead, every default submission would fail
        with ``InvalidPuzzleName`` and AC-049 could never pass. A name that is
        *present* and unusable still reaches the domain — see
        ``test_a_real_submission_reaches_the_real_error``'s
        ``InvalidPuzzleName`` case, whose body posts a single space.
        """
        response = _submit(
            running_server.server_port,
            {
                "mode": "library",
                "library_key": _KEY,
                "size": str(_SIZE),
                "name": "",
                "export_formats": ["json"],
                "out": str(tmp_path),
            },
        )

        assert _outcome(response.body) == pages.SUCCESS
        assert _paths_on(response.body) == [str(tmp_path / f"{_KEY}.json")]

    def test_a_run_that_asked_for_no_format_says_so_instead_of_listing_nothing(
        self, running_server: server.LoopbackHTTPServer, tmp_path: Path
    ) -> None:
        """The boundary of "reports the written file paths": there are none.

        ``export_puzzle`` returns an empty tuple when no format was requested
        and writes nothing, which is a successful run — the same one the CLI
        reports by printing no ``wrote`` lines. An empty ``<ul>`` would read as
        "something went wrong quietly".
        """
        response = _submit(
            running_server.server_port,
            {
                "mode": "library",
                "library_key": _KEY,
                "size": str(_SIZE),
                "out": str(tmp_path),
            },
        )

        assert _outcome(response.body) == pages.SUCCESS
        assert _paths_on(response.body) == []
        assert b"no file was written" in response.body
        assert _no_files_under(tmp_path)

    def test_the_page_reports_the_seed_the_run_used(
        self, running_server: server.LoopbackHTTPServer, tmp_path: Path
    ) -> None:
        """ADR-0015: a seed drawn for the user has nowhere else to be read.

        ``cli._run_generate`` prints it; this is the same report on the other
        adapter. Submitted without a seed on purpose — the interesting case is
        the drawn one, since a seed the user typed is already in their hand.
        """
        response = _submit(
            running_server.server_port,
            {
                "mode": "library",
                "library_key": _KEY,
                "size": str(_SIZE),
                "out": str(tmp_path),
            },
        )
        reported = re.search(rb"seed: <code>(\d+)</code>", response.body)

        assert reported is not None, response.body
        assert int(reported.group(1)) >= 0


# --------------------------------------------------------------------------
# AC-050 — the out-of-range size
# --------------------------------------------------------------------------


class TestWebUI_RejectsOutOfRangeSizeLikeCLI:
    """AC-050 — *given* a web UI submission requesting a grid size of 60x60
    (above the supported range), *when* the form is submitted, *then* the same
    size-range domain error the CLI would raise is surfaced to the page as a
    rejected request, and no files are written.

    "The same error" is asserted as the same *message*, produced by running the
    other adapter on the equivalent argv in the same test. Nothing in the web
    package knows what the supported range is, and that is the mechanism: the
    60 travels inward untouched and comes back as the domain's own refusal
    (ADR-0019/R1, guardrail G-2). A range check in the adapter would pass a
    weaker version of this test and fail the one below it.
    """

    def test_the_page_reports_a_rejected_request_and_writes_no_file(
        self, running_server: server.LoopbackHTTPServer, tmp_path: Path
    ) -> None:
        """The criterion: a structured refusal, and an untouched directory."""
        response = _submit(
            running_server.server_port,
            {
                "mode": "library",
                "library_key": _KEY,
                "size": "60",
                "export_formats": ["png", "json"],
                "out": str(tmp_path),
            },
        )

        assert response.status == 200
        assert _outcome(response.body) == pages.FAILURE
        assert b"between 10 and 30" in response.body
        assert _no_files_under(tmp_path)

    def test_the_message_is_the_one_the_cli_prints_for_the_same_request(
        self,
        running_server: server.LoopbackHTTPServer,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Both adapters, one request, one message — verbatim.

        The CLI's report is ``nonogram: error: <message>``; the page shows the
        ``<message>``. Compared after stripping the prefix the CLI adds, which
        is the only thing the two are allowed to differ by: an exit code and a
        page are different presentations, the domain's sentence is not.
        """
        response = _submit(
            running_server.server_port,
            {"mode": "library", "library_key": _KEY, "size": "60", "out": str(tmp_path)},
        )
        message = _cli_error_message(
            ["generate", "--mode", "library", "--library-key", _KEY, "--size", "60"],
            capsys,
        )

        assert message
        assert _shown(message) in response.body, response.body

    def test_the_adapter_passed_the_sixty_inward_rather_than_judging_it(self) -> None:
        """Guardrail G-2, at the only place it can be observed directly.

        The page above would look identical for an adapter that had grown its
        own range check and written the same sentence by hand — and that
        adapter would be one edit away from disagreeing with the domain. What
        makes AC-050 true *by construction* is this: the request the mapping
        builds carries 60.
        """
        built = submission.read("mode=library&library_key=cat&size=60").request

        assert built is not None
        assert built.width == 60

    def test_the_same_holds_for_a_size_below_the_range(
        self, running_server: server.LoopbackHTTPServer, tmp_path: Path
    ) -> None:
        """The other end of the range, so "out of range" is not "too large".

        One-sided evidence would be satisfied by an adapter that clamped low
        values silently — a clamp is exactly the kind of helpfulness ADR-0019/R1
        forbids, and it would be invisible from the 60 case alone.
        """
        response = _submit(
            running_server.server_port,
            {"mode": "library", "library_key": _KEY, "size": "3", "out": str(tmp_path)},
        )

        assert _outcome(response.body) == pages.FAILURE
        assert b"between 10 and 30" in response.body
        assert _no_files_under(tmp_path)


# --------------------------------------------------------------------------
# AC-051 — the abandoned generation
# --------------------------------------------------------------------------


class TestWebUI_ReportsAbandonedGenerationGracefully:
    """AC-051 — *given* a web UI submission whose options make every candidate
    fail the uniqueness/difficulty checks up to the configured retry bound (the
    same condition that raises ``GenerationAbandoned`` for the CLI), *when* the
    form is submitted, *then* the page reports the generation-abandoned failure
    and its reason, without hanging or returning an unhandled server error.

    The request used is AC-049's own options with difficulty "Medium": every
    built-in template scores Easy at this size and library mode redraws the same
    grid every time, so POL-004 resamples the retry bound away and POL-005
    abandons. That makes this the *deterministic* abandonment — no seed hunting,
    no timing luck — which is what lets "and its reason" be asserted on the
    exact sentence rather than on the presence of some words.

    "Without hanging" is delivered by a mechanism that already exists (ADR-0011's
    cooperative deadline against ADR-0001's budget) and this card was told not to
    build a second one (guardrail G-3), so what is checked here is the property,
    not a new timer: the answer arrives, inside the budget, and the server is
    still serving afterwards.
    """

    def test_the_page_reports_the_abandonment_and_its_reason(
        self, running_server: server.LoopbackHTTPServer, tmp_path: Path
    ) -> None:
        """The criterion: the failure, named, with the reason that caused it."""
        response = _submit(
            running_server.server_port,
            {
                "mode": "library",
                "library_key": _KEY,
                "size": str(_SIZE),
                "difficulty": "Medium",
                "export_formats": ["png", "json"],
                "out": str(tmp_path),
            },
        )

        assert response.status == 200
        assert _outcome(response.body) == pages.FAILURE
        assert b"abandoned after" in response.body
        assert str(orchestrator.MAX_RETRY_ATTEMPTS).encode() in response.body
        assert b"Medium band" in response.body
        assert _no_files_under(tmp_path)

    def test_the_reason_is_the_one_the_cli_prints_for_the_same_request(
        self,
        running_server: server.LoopbackHTTPServer,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """AC-051's "its reason", held to the other adapter's wording.

        ``GenerationAbandoned``'s message is where POL-005 explains what the
        candidates kept failing and which levers change the answer. A page that
        reported only "generation failed" would satisfy the sentence "reports
        the failure" and lose the half that makes it actionable.
        """
        response = _submit(
            running_server.server_port,
            {
                "mode": "library",
                "library_key": _KEY,
                "size": str(_SIZE),
                "difficulty": "Medium",
                "out": str(tmp_path),
            },
        )
        message = _cli_error_message(
            [
                "generate",
                "--mode", "library",
                "--library-key", _KEY,
                "--size", str(_SIZE),
                "--difficulty", "Medium",
            ],
            capsys,
        )

        assert "abandoned after" in message
        assert _shown(message) in response.body, response.body

    def test_it_answers_inside_the_generation_budget_and_keeps_serving(
        self, running_server: server.LoopbackHTTPServer, tmp_path: Path
    ) -> None:
        """AC-051's "without hanging or returning an unhandled server error".

        Three separate claims, and each fails differently. An answer at all —
        an escaping exception would close the connection under
        ``http.client`` and raise here rather than returning a response. Inside
        the budget — ADR-0011's deadline is what bounds it, so a hang would
        mean that mechanism is not reaching this path. And still serving: an
        error that took the serve loop down with it would show up on the next
        request, not on this one.
        """
        started = time.monotonic()
        response = _submit(
            running_server.server_port,
            {
                "mode": "library",
                "library_key": _KEY,
                "size": str(_SIZE),
                "difficulty": "Medium",
                "out": str(tmp_path),
            },
        )
        elapsed = time.monotonic() - started

        assert _outcome(response.body) == pages.FAILURE
        assert elapsed < _SUBMISSION_BUDGET_S, elapsed
        assert web_tests._request(running_server.server_port).status == 200

    def test_no_traceback_reaches_the_browser(
        self, running_server: server.LoopbackHTTPServer, tmp_path: Path
    ) -> None:
        """The negative half of "unhandled server error", on the wire.

        A page can report a failure and still leak the machinery that produced
        it. None of Python's traceback vocabulary, and no dotted module path of
        the raising package, may appear in the body.
        """
        response = _submit(
            running_server.server_port,
            {
                "mode": "library",
                "library_key": _KEY,
                "size": str(_SIZE),
                "difficulty": "Medium",
                "out": str(tmp_path),
            },
        )

        for leak in (b"Traceback", b"most recent call last", b"nonogram.errors", b".py\"",
                     b"GenerationAbandoned"):
            assert leak not in response.body, leak


# --------------------------------------------------------------------------
# EC-003 — every domain error the pipeline can raise
# --------------------------------------------------------------------------


def _error_hierarchy() -> tuple[type[errors.NonogramError], ...]:
    """Every class in the ``NonogramError`` hierarchy, the base included.

    Walked rather than listed, which is what makes EC-003 a property and not a
    handful of examples: an error class a later card adds to ``errors.py``
    joins this corpus without anybody remembering to add it, and if the web
    adapter does not surface it, this fails on the card that added it.

    The walk is transitive, not one level of ``__subclasses__``. That matters
    today — ``SizeTooSmallForSource`` subclasses ``SizeOutOfRange``, not the
    base — and it is asserted below rather than trusted.
    """
    found: dict[str, type[errors.NonogramError]] = {}
    pending: list[type[errors.NonogramError]] = [errors.NonogramError]
    while pending:
        current = pending.pop()
        if current.__name__ in found:
            continue
        found[current.__name__] = current
        pending.extend(current.__subclasses__())
    return tuple(found[name] for name in sorted(found))


#: The corpus, built once at import so the parametrisation can name each case.
_ERROR_CLASSES = _error_hierarchy()

#: The floor on that corpus, asserted inside the test that uses it. Eleven
#: subclasses plus the base, as ``errors.py`` ships them. A hierarchy that
#: shrank below this — a class deleted, a walk that stopped recursing — would
#: otherwise leave every parametrised case below passing over fewer inputs and
#: reporting the same green.
_MINIMUM_ERROR_CLASSES = 12

#: The submissions that reach a real domain error through the real pipeline,
#: one per error class the form can actually provoke. The monkeypatched arm
#: below covers the whole hierarchy; this one covers the part of it a person
#: at the form can reach, which is the part where a mapping bug would hide.
_REAL_FAILURES: dict[str, dict[str, str]] = {
    "SizeOutOfRange": {"mode": "library", "library_key": _KEY, "size": "60"},
    "InvalidDensity": {"mode": "random", "size": "20", "density": "500"},
    "UnknownLibraryImage": {"mode": "library", "library_key": "no-such-key", "size": "20"},
    "InvalidPuzzleName": {"mode": "library", "library_key": _KEY, "size": "20", "name": " "},
    "UnsupportedDifficulty": {
        "mode": "library", "library_key": _KEY, "size": "20", "difficulty": "extreme",
    },
    "UnreadableImage": {"mode": "image", "size": "20"},
    "GenerationAbandoned": {
        "mode": "library", "library_key": _KEY, "size": "20", "difficulty": "Medium",
    },
}


# --------------------------------------------------------------------------
# EC-003 — PropertyTest_WebUI_SurfacesAnyPipelineErrorAsStructuredFailure
#
# Any domain error the orchestrator pipeline raises for a web UI submission is
# caught by the web adapter and surfaced to the page as a structured failure
# response, never as an unhandled exception or a raw stack trace, FOR ANY error
# type the pipeline can raise. Generalizes AC-051.
#
# Written as module-level functions rather than as a class, which is this
# project's convention for a property: the CamelCase name above is the logical
# id the requirement cites, and each ``def`` below is one arm of it.
#
# Two arms, because "any error type the pipeline can raise" is bigger than the
# set a form can provoke:
#
# * ``test_every_error_class_surfaces_as_a_structured_failure`` walks the whole
#   hierarchy and raises each class from each of the two orchestrator calls the
#   adapter makes. This is the property. It reaches the classes no submission
#   can reach on demand — ``SolverTimeout`` needs a grid that outruns the
#   deadline, ``ExportRejected`` needs INV-002 to have been violated,
#   ``ImageNeedsManualCrop`` needs an upload the form has no control for — and
#   it reaches every class a later card adds, without being edited.
# * ``test_a_real_submission_reaches_the_real_error`` submits seven bodies that
#   provoke seven different real errors through the untouched pipeline. This is
#   what the first arm cannot show: that the *mapping* puts a submission where
#   the domain can refuse it. A ``generate`` monkeypatched to raise never looks
#   at the request it was given, so a mapping that dropped every field would
#   pass the property arm outright.
#
# The corpus is asserted non-trivial in
# ``test_the_walked_corpus_is_the_whole_hierarchy``, which also pins it against
# ``cli._EXIT_CODES``: every class the CLI has an exit code for is a class this
# page must be able to show, which is the concrete form of "keep the two error
# taxonomies telling the same story" (ADR-0019). Neither adapter grows a class
# the other has never heard of.
# --------------------------------------------------------------------------

def test_the_walked_corpus_is_the_whole_hierarchy() -> None:
    """The corpus that makes the parametrised cases below non-vacuous."""
    assert len(_ERROR_CLASSES) >= _MINIMUM_ERROR_CLASSES, [
        cls.__name__ for cls in _ERROR_CLASSES
    ]
    # Transitive, not one level: this class is a grandchild of the base.
    assert errors.SizeTooSmallForSource in _ERROR_CLASSES
    assert errors.NonogramError in _ERROR_CLASSES
    # The CLI's table and this corpus are views of one hierarchy.
    assert set(cli._EXIT_CODES) <= set(_ERROR_CLASSES)
    assert all(issubclass(cls, errors.NonogramError) for cls in _ERROR_CLASSES)

@pytest.mark.parametrize(
    "call", ["generate", "export_puzzle"], ids=["from-generate", "from-export"]
)
@pytest.mark.parametrize(
    "error_class", _ERROR_CLASSES, ids=lambda cls: cls.__name__
)
def test_every_error_class_surfaces_as_a_structured_failure(
    running_server: server.LoopbackHTTPServer,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    error_class: type[errors.NonogramError],
    call: str,
) -> None:
    """Each class, from each of the adapter's two calls inward.

    Both call sites, because they fail at different points of the handler:
    one before any puzzle exists, one after a real run has produced one and
    the response is a step closer to being written. EC-003's "before
    anything is written to the response stream" is only interesting for the
    second, and only the second exercises it.

    The failure page is checked for four things: the response arrived at
    all (an escaping exception drops the connection and ``http.client```
    raises instead of returning), it is the structured failure page, it
    carries the error's own message, and it carries none of the machinery —
    no traceback, no class name, no module path.
    """
    marker = f"marker-{_ERROR_CLASSES.index(error_class)}-{call}"

    def raiser(*_args: object, **_kwargs: object) -> object:
        raise error_class(marker)

    monkeypatch.setattr(orchestrator, call, raiser)

    response = _submit(
        running_server.server_port,
        {
            "mode": "library",
            "library_key": _KEY,
            "size": str(_SIZE),
            "export_formats": ["json"],
            "out": str(tmp_path),
        },
    )

    assert response.status == 200
    assert response.headers["Content-Type"] == "text/html; charset=utf-8"
    assert _outcome(response.body) == pages.FAILURE
    assert marker.encode() in response.body, response.body
    for leak in (b"Traceback", b"most recent call last", b"nonogram.errors"):
        assert leak not in response.body, leak
    assert error_class.__name__.encode() not in response.body

@pytest.mark.parametrize("expected", sorted(_REAL_FAILURES), ids=sorted(_REAL_FAILURES))
def test_a_real_submission_reaches_the_real_error(
    running_server: server.LoopbackHTTPServer,
    tmp_path: Path,
    expected: str,
) -> None:
    """Seven bodies, seven domain errors, nothing monkeypatched.

    Each body is submitted to the running server *and* raised directly out
    of the untouched pipeline, so the assertion is not "some failure page
    came back" but "the failure page carries the message of the class this
    body was chosen to provoke". The direct call is what identifies the
    class; the page is what the criterion is about.
    """
    fields = dict(_REAL_FAILURES[expected], out=str(tmp_path))
    response = _submit(running_server.server_port, fields)

    built = submission.read(urllib.parse.urlencode(fields)).request
    assert built is not None
    with pytest.raises(errors.NonogramError) as raised:
        orchestrator.export_puzzle(orchestrator.generate(built))

    assert type(raised.value).__name__ == expected
    assert _outcome(response.body) == pages.FAILURE
    assert _shown(str(raised.value)) in response.body, response.body
    assert _no_files_under(tmp_path)

def test_a_body_the_adapter_cannot_read_never_starts_a_generation(
    running_server: server.LoopbackHTTPServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The one failure that is the adapter's own, and it is not a domain one.

    ``size=twenty`` is not a number, so there is no number to send inward —
    the same wall ``argparse``'s ``type=int`` puts up for the CLI, and
    deliberately *not* a range check (the range is the domain's, AC-050).
    The submission is refused before the pipeline is called at all, which is
    asserted by making a call to it fail the test outright.
    """

    def never(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("the orchestrator was called for an unreadable body")

    monkeypatch.setattr(orchestrator, "generate", never)

    response = _submit(
        running_server.server_port, {"mode": "library", "size": "twenty"}
    )

    assert response.status == 200
    assert _outcome(response.body) == pages.FAILURE
    assert b"expected a whole number" in response.body
    assert b"twenty" in response.body

def test_a_mode_the_form_does_not_offer_is_refused_the_way_argv_is(
    running_server: server.LoopbackHTTPServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The other adapter-level refusal, and why it is not a G-2 violation.

    ``sourcing.for_mode`` raises a bare ``ValueError`` — pointedly *not* a
    ``NonogramError`` — for an unregistered mode, and its own docstring
    says why: "a user typing an unsupported mode is rejected by argparse's
    ``choices`` at the adapter". ``cli.py`` discharges that with
    ``choices=``. Without the equivalent here, a hand-written
    ``mode=bogus`` would escape as an unhandled exception, which is the one
    thing EC-003 forbids. Checked against the very list the form renders,
    so the offered set and the accepted set are one object.
    """

    def never(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("the orchestrator was called for an unoffered mode")

    monkeypatch.setattr(orchestrator, "generate", never)

    response = _submit(running_server.server_port, {"mode": "bogus", "size": "20"})

    assert _outcome(response.body) == pages.FAILURE
    assert b"bogus" in response.body
    assert set(pages.MODES) == set(_argv_mode_choices())


@pytest.mark.parametrize(
    "formats",
    [
        pytest.param(["bogus"], id="only-an-unregistered-format"),
        # The damaging order: the first format is written and the second is what
        # ``export.for_format`` cannot look up, so an adapter that merely let the
        # exception escape had already produced a partial export.
        pytest.param(["png", "bogus"], id="one-real-then-an-unregistered-one"),
        pytest.param(["bogus", "png"], id="an-unregistered-one-then-a-real-one"),
    ],
)
def test_an_export_format_the_registry_does_not_hold_is_refused_the_way_argv_is(
    running_server: server.LoopbackHTTPServer,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    formats: list[str],
) -> None:
    """The other half of the same delegation ``mode`` discharges.

    ``export.for_format`` raises a bare ``ValueError`` — pointedly *not* a
    ``NonogramError`` — for an unregistered name, and its docstring cites the
    same reason ``sourcing.for_mode`` does: an unsupported format "is rejected
    by argparse's ``choices`` at the adapter". ``cli.py`` discharges that with
    ``choices=list(export.FORMATS)``. Without the equivalent here the value
    escaped as an unhandled exception and the browser got a dropped connection
    — and on the ``png,bogus`` row, a written PNG and no response at all.

    Refused before the pipeline runs, asserted by making a call to it fail the
    test outright; the empty ``tmp_path`` is what shows no partial export.
    """

    def never(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("the orchestrator was called for an unoffered format")

    monkeypatch.setattr(orchestrator, "generate", never)

    response = _submit(
        running_server.server_port,
        {"mode": "library", "library_key": _KEY, "size": str(_SIZE),
         "export_formats": formats, "out": str(tmp_path)},
    )

    assert response.status == 200
    assert _outcome(response.body) == pages.FAILURE
    assert b"export_formats" in response.body
    assert b"bogus" in response.body
    assert _no_files_under(tmp_path)
    # The drift assertion, the exact counterpart of the ``mode`` one above: the
    # set this adapter accepts, the set the form offers and the set ``--export``
    # accepts are one object, so the two adapters cannot grow different
    # vocabularies without this failing.
    assert set(export.FORMATS) == set(_argv_export_choices())
    assert set(export.FORMATS) == _form_export_choices()


def test_a_field_carrying_a_nul_is_refused_before_the_pipeline(
    running_server: server.LoopbackHTTPServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``%00`` is the one byte a form can post that argv cannot carry.

    ``Path.mkdir`` answers an embedded NUL with a bare ``ValueError`` — not an
    ``OSError``, so ``_generate``'s non-domain arm never saw it — and the
    browser got a dropped connection. The CLI has no route to that call at all,
    a NUL being unrepresentable in argv, so this is an asymmetry the web
    adapter introduced rather than one it inherited.
    """

    def never(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("the orchestrator was called for a body carrying a NUL")

    monkeypatch.setattr(orchestrator, "generate", never)

    response = _submit(
        running_server.server_port,
        {"mode": "library", "library_key": _KEY, "size": str(_SIZE), "out": "bad\x00dir"},
    )

    assert response.status == 200
    assert _outcome(response.body) == pages.FAILURE
    assert b"NUL" in response.body


# --------------------------------------------------------------------------
# NFR-004 / CON-010 on the method that writes files
#
# The refusal itself is AC-054..AC-058 and EC-004, all in
# ``tests/test_web_server.py``. What is pinned here is the consequence that made
# it urgent: the reach it closes runs a pipeline and writes files, so it is
# checked on ``POST`` against the two things a status code alone cannot show —
# that the orchestrator was not called, and that nothing landed on disk.
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "headers",
    [
        pytest.param({"Sec-Fetch-Site": "cross-site"}, id="fetch-metadata-only"),
        pytest.param({"Origin": "https://evil.example.com"}, id="origin-only"),
        pytest.param(
            {
                "Origin": "https://evil.example.com",
                "Referer": "https://evil.example.com/attack.html",
                "Sec-Fetch-Site": "cross-site",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Dest": "document",
            },
            id="the-whole-auto-submitting-form",
        ),
    ],
)
def test_a_cross_site_submission_never_reaches_the_pipeline_and_writes_nothing(
    running_server: server.LoopbackHTTPServer,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    headers: dict[str, str],
) -> None:
    """The attack the refusal exists for, on the route that made it matter.

    An auto-submitting ``<form method=post>`` on any page the user has open,
    aimed at this server. The ``Host`` it carries is allowlisted — a browser
    sets that from the *target* — so the F-12 check passes it, and before the
    refusal the pipeline ran and wrote four files into a directory the
    attacking page named. No reply is needed for that to work, which is why the
    same-origin policy and CORS are beside the point.
    """

    def never(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("the orchestrator ran for a cross-site submission")

    monkeypatch.setattr(orchestrator, "generate", never)

    response = web_tests._request(
        running_server.server_port,
        method="POST",
        path=pages.FORM_ACTION,
        headers={
            "Host": f"127.0.0.1:{running_server.server_port}",
            "Content-Type": "application/x-www-form-urlencoded",
            **headers,
        },
        body=urllib.parse.urlencode(
            [("mode", "library"), ("library_key", _KEY), ("size", str(_SIZE)),
             ("name", "pwned"), ("export_formats", "png"), ("export_formats", "json"),
             ("out", str(tmp_path))]
        ).encode("utf-8"),
    )

    assert response.status == 400
    assert _outcome(response.body) is None
    assert _no_files_under(tmp_path)


def test_a_same_origin_submission_still_runs_the_pipeline(
    running_server: server.LoopbackHTTPServer, tmp_path: Path
) -> None:
    """The bound on that refusal, on the same route: the form still works.

    The headers a browser attaches when the page at ``/`` posts its own form
    back, which is the only submission path this UI has (CON-008). Without this
    row the refusal above is satisfied by a server that refuses every ``POST``.
    """
    response = web_tests._request(
        running_server.server_port,
        method="POST",
        path=pages.FORM_ACTION,
        headers={
            "Host": f"127.0.0.1:{running_server.server_port}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": f"http://127.0.0.1:{running_server.server_port}",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "navigate",
        },
        body=urllib.parse.urlencode(
            [("mode", "library"), ("library_key", _KEY), ("size", str(_SIZE)),
             ("export_formats", "json"), ("out", str(tmp_path))]
        ).encode("utf-8"),
    )

    assert response.status == 200
    assert _outcome(response.body) == pages.SUCCESS
    assert [Path(path).name for path in _paths_on(response.body)] == [f"{_KEY}.json"]


# --------------------------------------------------------------------------
# The transport bounds this endpoint adds (ADR-0019/R1: HTTP concerns only)
# --------------------------------------------------------------------------


def test_a_post_to_an_unrouted_path_is_the_same_plain_404_a_get_gets(
    running_server: server.LoopbackHTTPServer,
) -> None:
    """``do_POST`` dispatches through the shared router, so misses look alike."""
    response = web_tests._request(
        running_server.server_port, method="POST", path="/nope", body=b"size=20"
    )

    assert response.status == 404
    assert response.headers["Content-Type"] == "text/plain; charset=utf-8"
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_a_submission_naming_a_foreign_host_is_refused_before_the_pipeline(
    running_server: server.LoopbackHTTPServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F-12 still runs first now that there is something behind the router.

    The ``Host`` check was written when the only thing it protected was a
    static page. It now stands in front of a generation that writes files, so
    "before routing" is worth re-asserting on the method that does the writing.
    """

    def never(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("the orchestrator ran for a foreign Host")

    monkeypatch.setattr(orchestrator, "generate", never)

    response = web_tests._request(
        running_server.server_port,
        method="POST",
        path=pages.FORM_ACTION,
        headers={"Host": "evil.example.com"},
        body=b"mode=library&library_key=cat&size=20",
    )

    assert response.status == 400


def test_a_body_over_the_declared_cap_is_refused_without_being_read(
    running_server: server.LoopbackHTTPServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``MAX_BODY_BYTES``: a transport bound, answered with a status code.

    ``http.server`` bounds request lines and header counts and nothing else, so
    without this a ``Content-Length`` of four billion on a loopback socket is
    read into memory in full. Asserted just past the cap rather than at four
    billion, so the test costs one buffer rather than one machine.
    """

    def never(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("the orchestrator ran for an over-long body")

    monkeypatch.setattr(orchestrator, "generate", never)

    oversized = b"size=" + b"9" * (handler.MAX_BODY_BYTES + 1)
    response = web_tests._request(
        running_server.server_port,
        method="POST",
        path=pages.FORM_ACTION,
        body=oversized,
    )

    assert response.status == 413
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_a_body_at_the_cap_is_still_read(
    running_server: server.LoopbackHTTPServer, tmp_path: Path
) -> None:
    """The other side of the bound, so the cap is a cap and not a wall.

    Padded to exactly :data:`nonogram.web.handler.MAX_BODY_BYTES` with a field
    nothing reads, which is what a real form with a long ``out`` path or name
    looks like from the transport's point of view.
    """
    fields = f"mode=library&library_key={_KEY}&size={_SIZE}&out={tmp_path}&pad="
    body = fields.encode() + b"x" * (handler.MAX_BODY_BYTES - len(fields.encode()))
    response = web_tests._request(
        running_server.server_port, method="POST", path=pages.FORM_ACTION, body=body
    )

    assert len(body) == handler.MAX_BODY_BYTES
    assert response.status == 200
    assert _outcome(response.body) == pages.SUCCESS


# --------------------------------------------------------------------------
# The non-domain failure the export can raise (``_generate``'s ``OSError`` arm)
#
# ``export.write`` documents that an unusable ``--out`` raises the standard
# library's own ``OSError`` rather than a ``NonogramError``, which is why the
# handler catches it separately from EC-003's hierarchy. Both rows below are
# reachable from the form with no monkeypatching at all, and neither was pinned
# by anything until now: deleting the whole ``except OSError`` block left the
# suite green.
# --------------------------------------------------------------------------


def test_an_out_naming_an_existing_file_is_reported_as_a_failure_page(
    running_server: server.LoopbackHTTPServer, tmp_path: Path
) -> None:
    """``--out`` pointing at a regular file: ``mkdir`` cannot make it a directory.

    A ``FileExistsError``, which is an ``OSError`` and not a ``NonogramError``,
    so it reaches the handler's second ``except`` arm. The user's answer is to
    pass a different path, and a page saying so is the whole difference between
    this arm existing and not.
    """
    occupied = tmp_path / "not-a-directory"
    occupied.write_text("in the way", encoding="utf-8")

    response = _submit(
        running_server.server_port,
        {"mode": "library", "library_key": _KEY, "size": str(_SIZE),
         "export_formats": ["json"], "out": str(occupied)},
    )

    assert response.status == 200
    assert _outcome(response.body) == pages.FAILURE
    assert b"Errno" in response.body
    assert _shown(str(occupied)) in response.body
    assert occupied.read_text(encoding="utf-8") == "in the way"


@pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0,
    reason="root ignores the directory mode, so the write would succeed",
)
def test_an_out_under_an_unwritable_directory_is_reported_as_a_failure_page(
    running_server: server.LoopbackHTTPServer, tmp_path: Path
) -> None:
    """``--out`` under a directory the user cannot write: ``mkdir`` is refused.

    A ``PermissionError``, the other ``OSError`` an ordinary submission can
    reach. Restored to 0700 in a ``finally`` so ``tmp_path``'s own teardown can
    remove the tree whatever the assertions do.
    """
    locked = tmp_path / "locked"
    locked.mkdir()
    locked.chmod(0o500)
    try:
        response = _submit(
            running_server.server_port,
            {"mode": "library", "library_key": _KEY, "size": str(_SIZE),
             "export_formats": ["json"], "out": str(locked / "below")},
        )

        assert response.status == 200
        assert _outcome(response.body) == pages.FAILURE
        assert b"Errno" in response.body
        assert not (locked / "below").exists()
    finally:
        locked.chmod(0o700)


def test_a_repeated_single_valued_field_takes_the_last_value_as_argv_does() -> None:
    """Two ``size=`` values is argparse's "flag given twice": the last wins."""
    built = submission.read("mode=random&size=10&size=25&density=40").request

    assert built is not None
    assert built.width == 25


def test_every_page_this_endpoint_can_return_escapes_what_it_echoes() -> None:
    """The pages carry user text; ``handler._respond`` only adds ``nosniff``.

    Both pages are built directly rather than fetched, so the escaping is
    tested where it lives — a socket test would also pass if the browser-facing
    markup happened to be filtered somewhere else.
    """
    result = pages.result_page("<script>alert(1)</script>", 1, [Path("<img src=x>")])
    failure = pages.failure_page("summary", ["<script>alert(2)</script>"])

    for page in (result, failure):
        assert "<script>alert" not in page
        assert "&lt;script&gt;" in page or "&lt;img" in page
