"""CARD-177 — the book export's error handlers flash fixed text, not the exception's.

    AC-2  TestBookPdfDownload_ErrorIsGenericAndLogged
    AC-3  test_PropertyTest_AdminErrors_RawExceptionTextNeverReachesTheScreen

The panel can be reached at a public hostname behind a credential (ADR-0030,
CON-016), and a database driver's message can name hosts, users and
connection details. Each failure here is injected once, at a seam the request
passes through, and the screen (body, flashes, headers) is searched for the
exception's message. Every credential in this file is invented (G-6).
"""

from __future__ import annotations

import html
import random
import string
from pathlib import Path

import pytest

import nonogram.admin.book_manager as book_manager_module
from nonogram import clues
from nonogram.admin.app import FINALISE_ACTION_FAILED, PDF_EXPORT_FAILED
from nonogram.admin.book_pdf_generator import BookPDFGenerator

#: The logger the panel logs through (``Flask(__name__)``'s own name).
PANEL_LOGGER = "nonogram.admin.app"

#: The three routes of the one book export (FR-043).
ROUTES = ("finalise", "download-pdf", "generate-pdf")


@pytest.fixture
def admin_app(monkeypatch, tmp_path):
    """The admin panel in memory mode, with a book store of its own."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.setattr(
        book_manager_module,
        "_book_manager",
        book_manager_module.BookManager(session_factory=None),
    )
    from nonogram.admin.app import create_app

    app = create_app()
    app.config["TESTING"] = True
    app.config["BOOK_COVER_DIR"] = str(tmp_path / "covers")
    return app


def _rectangle(width, height, left, top, right, bottom):
    return [
        [left <= x < right and top <= y < bottom for x in range(width)]
        for y in range(height)
    ]


def _make_book(app, puzzle_count=3):
    """A draft book holding ``puzzle_count`` easy 20x20 puzzles."""
    book_id = app.book_manager.create_book(
        title="Winter Pictures",
        description="Twenty winter pictures.",
        theme="generic",
        target_audience="adults",
        size="21.59×27.94",
    )
    ids = []
    for i in range(puzzle_count):
        grid = _rectangle(20, 20, i, i, 8 + 2 * i, 10 + i)
        found = clues.compute_clues(grid)
        ids.append(
            app.puzzle_review_service.add_puzzle(
                grid=grid,
                clues_rows=[list(c) for c in found.rows],
                clues_cols=[list(c) for c in found.columns],
                width=20,
                height=20,
                theme="winter",
                difficulty_score=10,
                difficulty_tier="easy",
                quality_score=50,
                recognizability="medium",
                strategies_used=[],
            )
        )
    app.book_manager.add_puzzles_to_book(book_id, ids)
    return book_id


def _raise_once(monkeypatch, owner, name, error):
    """Make ``owner.name`` raise ``error`` on its first call, then behave."""
    original = getattr(owner, name)
    calls = []

    def once(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            raise error
        return original(*args, **kwargs)

    monkeypatch.setattr(owner, name, once)


def _flashes(client):
    with client.session_transaction() as sess:
        return list(sess.get("_flashes", []))


def _panel_errors(caplog) -> list:
    """The ERROR records on the panel's logger."""
    return [
        r for r in caplog.records if r.name == PANEL_LOGGER and r.levelname == "ERROR"
    ]


def _request_export(client, route, book_id):
    """Ask for the book's interior through ``route``."""
    if route == "finalise":
        return client.post(
            f"/book/{book_id}/finalize",
            data={"action": "download_pdf", "part": "interior"},
        )
    return client.post(f"/book/{book_id}/{route}?part=interior")


def _assert_logged_once(caplog, error, book_id):
    (record,) = _panel_errors(caplog)
    assert record.exc_info[1] is error
    assert record.exc_info[2] is not None  # the traceback itself
    assert book_id in record.getMessage()


class TestBookPdfDownload_ErrorIsGenericAndLogged:
    """AC-2 — each export route flashes the fixed text and logs the error once."""

    @pytest.mark.parametrize("route", ROUTES)
    def test_the_flash_is_the_constant_and_the_error_is_logged(
        self, admin_app, monkeypatch, caplog, route
    ) -> None:
        client = admin_app.test_client()
        book_id = _make_book(admin_app)
        marker = "export-card177-marker"
        error = RuntimeError(marker)
        _raise_once(monkeypatch, BookPDFGenerator, "__init__", error)

        with caplog.at_level("ERROR", logger=PANEL_LOGGER):
            response = _request_export(client, route, book_id)

        assert response.status_code == 302
        # With no Referer every route goes back to the book's detail page.
        assert response.headers["Location"].endswith(f"/book/{book_id}")
        assert marker not in response.headers["Location"]
        flashes = _flashes(client)
        assert [m for c, m in flashes if c == "error"] == [PDF_EXPORT_FAILED]
        assert not any(marker in m for _, m in flashes)
        _assert_logged_once(caplog, error, book_id)


# --------------------------------------------------------------------------
# AC-3: a seeded corpus of fake-credential exceptions at five seams
# --------------------------------------------------------------------------


class OperationalError(Exception):
    """A stand-in for a database driver's connection error."""


EXCEPTION_CLASSES = (
    RuntimeError,
    OSError,
    TypeError,
    KeyError,
    ValueError,
    OperationalError,
)

SEAMS = (
    "clear_cover",
    "save_and_finish",
    "export:finalise",
    "export:download-pdf",
    "export:generate-pdf",
)

CORPUS_SEED = 177
CORPUS_SIZE = 60

#: Characters a fake password may hold besides letters and digits: HTML's
#: specials (so an escaped echo is caught only by the unescaped check) but no
#: quote or backslash, which ``repr`` (``KeyError``'s ``str``) would rewrite.
_PASSWORD_SPECIALS = "<>&"


def _fake_password(rng: random.Random) -> str:
    alphabet = string.ascii_letters + string.digits
    core = "".join(rng.choice(alphabet) for _ in range(12))
    if rng.random() < 0.5:
        at = rng.randrange(len(core))
        core = core[:at] + rng.choice(_PASSWORD_SPECIALS) + core[at:]
    return f"fake{core}"


def _message_holding(rng: random.Random, password: str) -> str:
    shapes = (
        f"could not connect to postgresql://nonogram:{password}@db.internal:5432/nonogram_poc",
        f"FATAL: authentication failed: host=db.internal user=nonogram password={password}",
        f"SECRET_KEY={password} rejected",
    )
    message = rng.choice(shapes)
    if rng.random() < 0.5:
        message = f"<b>driver</b> said:\n{message}\n& more"
    return message


def _corpus():
    rng = random.Random(CORPUS_SEED)
    cases = []
    for i in range(CORPUS_SIZE):
        password = _fake_password(rng)
        cls = EXCEPTION_CLASSES[i % len(EXCEPTION_CLASSES)]
        seam = SEAMS[rng.randrange(len(SEAMS))] if i >= len(SEAMS) else SEAMS[i]
        cases.append((seam, cls(_message_holding(rng, password)), password))
    return cases


def _inject_and_request(app, client, monkeypatch, tmp_path, seam, error):
    """Raise ``error`` once at ``seam``; the response, and the book's id."""
    book_id = _make_book(app)
    if seam == "clear_cover":
        app.config["BOOK_COVER_DIR"] = str(tmp_path)
        cover = tmp_path / f"{book_id}_cover.png"
        cover.write_bytes(b"not read")
        with client.session_transaction() as sess:
            sess[f"book_{book_id}_cover_path"] = str(cover)
            sess[f"book_{book_id}_cover_data"] = True
        _raise_once(monkeypatch, Path, "unlink", error)
        response = client.post(
            f"/book/{book_id}/finalize", data={"action": "clear_cover"}
        )
    elif seam == "save_and_finish":
        # The row read (members_in_order), as a database error would surface.
        _raise_once(monkeypatch, app.book_manager, "get_puzzle_title", error)
        response = client.post(
            f"/book/{book_id}/finalize", data={"action": "save_and_finish"}
        )
    else:
        _raise_once(monkeypatch, BookPDFGenerator, "__init__", error)
        response = _request_export(client, seam.split(":", 1)[1], book_id)
    return response, book_id


def test_PropertyTest_AdminErrors_RawExceptionTextNeverReachesTheScreen(
    admin_app, monkeypatch, caplog, tmp_path
) -> None:
    """AC-3 — no fake credential from an exception reaches body, flash or header."""
    cases = _corpus()
    assert len(cases) >= 60
    assert {type(e) for _, e, _ in cases} == set(EXCEPTION_CLASSES)
    assert {seam for seam, _, _ in cases} == set(SEAMS)

    checked = 0
    for n, (seam, error, password) in enumerate(cases):
        client = admin_app.test_client()
        case_dir = tmp_path / f"case{n}"
        case_dir.mkdir()
        caplog.clear()
        with monkeypatch.context() as patch:
            with caplog.at_level("ERROR", logger=PANEL_LOGGER):
                response, book_id = _inject_and_request(
                    admin_app, client, patch, case_dir, seam, error
                )
        where = (n, seam, type(error).__name__)
        assert password in str(error), where  # the case holds its secret

        body = response.get_data(as_text=True)
        assert password not in body, where
        assert password not in html.unescape(body), where
        for name, value in response.headers.items():
            assert password not in value, (where, name)
        flashes = _flashes(client)
        assert not any(password in m for _, m in flashes), where
        expected = FINALISE_ACTION_FAILED if seam in SEAMS[:2] else PDF_EXPORT_FAILED
        if response.status_code == 200:
            assert expected in html.unescape(body), where
        else:
            assert response.status_code == 302, where
            assert ("error", expected) in flashes, where
        _assert_logged_once(caplog, error, book_id)
        checked += 1

    assert checked >= 60
