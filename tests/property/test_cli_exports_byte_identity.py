"""EC-020 / CON-019: CLI and web exports stay byte-identical whatever the book does.

    PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry  (EC-020)
        -> test_property_cli_exports_byte_identical_whatever_the_book_geometry
        -> test_property_web_ui_exports_byte_identical_whatever_the_book_geometry
        -> test_the_corpus_is_the_one_the_golden_was_taken_from  (the corpus's gate)

ADR-0036 is about to give ``compute_layout`` an optional ``PageSpec`` so the book
PDF can lay out on its own trim (CARD-114). CON-019 says the CLI and the web UI
must not notice: for any generation request, the PNG, SVG and PDF written are
byte-for-byte what they were before the book geometry existed. This module pins
"before" (CARD-113, on the commit preceding any geometry change) as SHA-256
digests in ``tests/fixtures/a4_golden/cli_exports.json``, and checks "after" is
the same, over a corpus rather than one example — AC-180's seeded 30x30 is the
named instance, in ``tests/test_export_a4_golden.py``.

The corpus
----------
Built here, by hand, from stdlib ``random.Random`` at a fixed seed (no
``hypothesis``: CLAUDE.md's test policy), with a minimum case count asserted in
every test so it cannot silently shrink. It spans CON-011's whole 10..30 band on
both axes, square and rectangular, explicit ``WxH`` and bare ``N`` size tokens,
densities and seeds; four corner extents are always included rather than left
to the draw.

Densities are drawn from 55..90 and not lower, deliberately. Below roughly 50%
a 20x20-and-up random grid is the known-hard class where the uniqueness search
can run into ``orchestrator.GENERATION_BUDGET_SECONDS`` (measured while building
this corpus: 5 of 80 requests drawn at 40..80% abandoned on the 30 s budget,
and others took 5-13 s). Whether such a request succeeds depends on the host's
speed, so its output is not a function of the request — it cannot be pinned
byte for byte, and it has nothing to do with page geometry. At 55..90% every
request settles well inside a second and is a pure function of its seed.

The web UI (COMP-008)
---------------------
CON-019 names the web UI too, and its form goes through the same
``orchestrator.generate`` -> ``orchestrator.export_puzzle`` sink as the CLI. A
slice of the same corpus is posted to a real loopback server exactly as a
browser posts the form, and must write the *same* bytes the CLI's golden pins
for that request — one golden, two adapters.

Regenerating
------------
Never how a red test gets fixed (CARD-113 G-3): a red test here means a change
reached the CLI or web output, which is what CON-019 forbids. See
``tests/fixtures/a4_golden/regenerate.py`` for the command and its guards.
"""

from __future__ import annotations

import random
import urllib.parse
from pathlib import Path
from typing import NamedTuple

from nonogram import web
from nonogram.limits import MAX_SIZE, MIN_SIZE
from nonogram.web import pages
from tests import test_web_server as web_tests
from tests.fixtures.a4_golden import golden

SEED = 20260922

#: EC-020's floor: the card asks for at least 60 CLI requests.
REQUIRED_CASES = 60

#: How many requests the corpus actually holds — above the floor so the floor
#: is a guard, not the target.
CORPUS_SIZE = 72

#: The density band the corpus draws from (see the module docstring for why it
#: starts at 55).
DENSITY_RANGE = (55, 90)

#: Extents always present, whatever the draw: the band's four corners.
_CORNERS: tuple[tuple[int, int], ...] = (
    (MIN_SIZE, MIN_SIZE),
    (MAX_SIZE, MAX_SIZE),
    (MIN_SIZE, MAX_SIZE),
    (MAX_SIZE, MIN_SIZE),
)

#: Every Nth corpus case is also posted through the web UI.
_WEB_STRIDE = 12


class Case(NamedTuple):
    """One pinned request and the id its golden is stored under."""

    case_id: str
    request: golden.Request


def _corpus() -> tuple[Case, ...]:
    """The EC-020 corpus, deterministically from :data:`SEED`."""
    rng = random.Random(SEED)
    cases: list[Case] = []
    for index in range(CORPUS_SIZE):
        if index < len(_CORNERS):
            width, height = _CORNERS[index]
        else:
            width, height = rng.randint(MIN_SIZE, MAX_SIZE), rng.randint(MIN_SIZE, MAX_SIZE)
        # A quarter of the requests use the bare-N token, which in random mode
        # derives a square (FR-023) — the other spelling a user can type.
        size = f"{width}" if rng.random() < 0.25 else f"{width}x{height}"
        density = rng.randint(*DENSITY_RANGE)
        seed = rng.randrange(2**31)
        name = f"ec020-{index:02d}"
        cases.append(Case(f"ec020-{index:02d}-{size}-d{density}", (size, density, seed, name)))
    return tuple(cases)


CASES = _corpus()


def _golden_cases() -> dict[str, dict[str, object]]:
    return golden.load(golden.CLI_GOLDEN)["cases"]


def test_the_corpus_is_the_one_the_golden_was_taken_from() -> None:
    """The seeded corpus still builds, is big enough, and matches the fixture.

    A corpus that drifted from the golden's (a changed seed, a changed draw
    order, a Python whose ``random`` changed) would be compared against the
    wrong digests and fail for a reason that has nothing to do with CON-019;
    this names that failure for what it is. It also checks the corpus covers
    what EC-020 asks for: the whole 10..30 band on both axes, rectangles, both
    size spellings.
    """
    assert len(CASES) >= REQUIRED_CASES, (
        f"EC-020 needs >= {REQUIRED_CASES} requests, the corpus has {len(CASES)}"
    )
    goldens = _golden_cases()
    for case in CASES:
        assert case.case_id in goldens, f"{case.case_id} has no golden digests"
        assert tuple(goldens[case.case_id]["request"]) == case.request, (
            f"{case.case_id}: the corpus builds {case.request}, "
            f"the golden was taken for {goldens[case.case_id]['request']}"
        )

    sides = [
        (int(size.split("x")[0]), int(size.split("x")[-1]))
        for size, _, _, _ in (case.request for case in CASES)
    ]
    assert {w for w, _ in sides} >= {MIN_SIZE, MAX_SIZE}
    assert {h for _, h in sides} >= {MIN_SIZE, MAX_SIZE}
    assert sum(w != h for w, h in sides) >= REQUIRED_CASES // 2
    assert any("x" not in case.request[0] for case in CASES)
    assert len({case.request[1] for case in CASES}) >= 10
    assert len({case.request[2] for case in CASES}) == len(CASES)


def test_property_cli_exports_byte_identical_whatever_the_book_geometry(
    tmp_path: Path,
) -> None:
    """PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry (EC-020).

    Every corpus request, through ``nonogram generate``, writes a PNG, an SVG
    and a PDF whose digests equal the golden's — the PDF modulo Pillow's
    save-time timestamps and nothing else (see ``golden.normalized_pdf``).
    Every diverging request and format is reported, not only the first.
    """
    assert len(CASES) >= REQUIRED_CASES
    goldens = _golden_cases()
    diverged: list[str] = []
    for case in CASES:
        written = golden.run_cli(case.request, tmp_path / case.case_id)
        diverged += _divergences(case, goldens[case.case_id]["exports"], written, "cli")
    assert not diverged, (
        f"CON-019 broken: {len(diverged)} CLI export(s) changed byte for byte\n"
        + "\n".join(diverged)
    )


def test_property_web_ui_exports_byte_identical_whatever_the_book_geometry(
    tmp_path: Path,
) -> None:
    """The same property through COMP-008's form, on a slice of the corpus.

    Posted to a real loopback server as a browser posts the form, into a fresh
    ``out`` directory, and compared against the *CLI's* golden for the same
    request — CON-019 holds for both adapters because they share one export
    sink, and this is what would notice if that stopped being true.
    """
    web_cases = CASES[::_WEB_STRIDE]
    assert len(web_cases) >= CORPUS_SIZE // _WEB_STRIDE
    goldens = _golden_cases()
    diverged: list[str] = []
    with web_tests._running(web.create_server(0)) as server:
        for case in web_cases:
            out = tmp_path / case.case_id
            response = _post_form(server.server_port, case.request, out)
            assert response.status == 200, f"{case.case_id}: HTTP {response.status}"
            assert b'data-outcome="success"' in response.body, (
                f"{case.case_id}: the web UI did not report success"
            )
            written = golden.digests_of(out)
            diverged += _divergences(case, goldens[case.case_id]["exports"], written, "web")
    assert not diverged, (
        f"CON-019 broken: {len(diverged)} web UI export(s) changed byte for byte\n"
        + "\n".join(diverged)
    )


def _post_form(port: int, request: golden.Request, out: Path) -> web_tests._Response:
    """Post ``request`` to the form's action, fields as the form names them."""
    size, density, seed, name = request
    pairs = [
        ("mode", "random"),
        ("size", size),
        ("density", str(density)),
        ("seed", str(seed)),
        ("name", name),
        *(("export_formats", export_format) for export_format in golden.EXPORT_FORMATS),
        ("out", str(out)),
    ]
    return web_tests._request(
        port,
        method="POST",
        path=pages.FORM_ACTION,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        body=urllib.parse.urlencode(pairs).encode("utf-8"),
    )


def _divergences(
    case: Case,
    expected: object,
    actual: dict[str, dict[str, str]],
    adapter: str,
) -> list[str]:
    """One line per format on which ``actual`` differs from the golden."""
    assert isinstance(expected, dict)
    lines: list[str] = []
    for export_format in sorted(set(expected) | set(actual)):
        want, got = expected.get(export_format), actual.get(export_format)
        if want != got:
            lines.append(f"  [{adapter}] {case.case_id} {export_format}: golden {want}, now {got}")
    return lines
