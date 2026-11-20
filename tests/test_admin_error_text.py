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
from nonogram import clues, errors
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


def _request_export(client, route, book_id, headers=None):
    """Ask for the book's interior through ``route``."""
    if route == "finalise":
        return client.post(
            f"/book/{book_id}/finalize",
            data={"action": "download_pdf", "part": "interior"},
            headers=headers,
        )
    return client.post(f"/book/{book_id}/{route}?part=interior", headers=headers)


#: CARD-496 (IDEA-015): a ``Referer`` the panel did not serve. A failed
#: download never redirects to it.
OFF_SITE_REFERER = {"Referer": "https://evil.example/book/phish"}


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
            response = _request_export(client, route, book_id, OFF_SITE_REFERER)

        assert response.status_code == 302
        # With an off-site Referer (or none) every route goes back to the
        # book's detail page on this panel (CARD-496).
        assert response.headers["Location"].endswith(f"/book/{book_id}")
        assert "evil.example" not in response.headers["Location"]
        assert marker not in response.headers["Location"]
        flashes = _flashes(client)
        assert [m for c, m in flashes if c == "error"] == [PDF_EXPORT_FAILED]
        assert not any(marker in m for _, m in flashes)
        _assert_logged_once(caplog, error, book_id)


# --------------------------------------------------------------------------
# AC-3: a seeded corpus of fake-credential exceptions at six seams
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

#: CARD-496: ``set_book_status`` is Finalise's sixth seam, placed fifth so the
#: corpus's first pass puts a ``ValueError`` there (``EXCEPTION_CLASSES[4]``):
#: a ``ValueError`` that is not a ``StatusRefusal`` is a fault — fixed text,
#: logged — however it reads.
SEAMS = (
    "clear_cover",
    "save_and_finish",
    "export:finalise",
    "export:download-pdf",
    "set_book_status",
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
    elif seam in ("save_and_finish", "set_book_status"):
        # The row read (members_in_order), as a database error would surface;
        # or the status write itself (CARD-496), after every check passed.
        name = "get_puzzle_title" if seam == "save_and_finish" else seam
        _raise_once(monkeypatch, app.book_manager, name, error)
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
    assert ("set_book_status", ValueError) in {(s, type(e)) for s, e, _ in cases}

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
        expected = (
            PDF_EXPORT_FAILED if seam.startswith("export:") else FINALISE_ACTION_FAILED
        )
        if response.status_code == 200:
            assert expected in html.unescape(body), where
        else:
            assert response.status_code == 302, where
            assert ("error", expected) in flashes, where
        _assert_logged_once(caplog, error, book_id)
        checked += 1

    assert checked >= 60


# --------------------------------------------------------------------------
# CARD-383: the one refusal the owner is shown in words
# --------------------------------------------------------------------------

GREEK = "Χιονονιφάδα"


def _retitle_first(app, book_id, title) -> None:
    first = app.book_manager.get_book(book_id).puzzle_ids[0]
    assert app.book_manager.set_puzzle_title(book_id, first, title)


def _error_flashes(client) -> list:
    return [m for c, m in _flashes(client) if c == "error"]


class TestBookPdfDownload_TheUnsettableTitleRefusalIsShownInWords:
    """CARD-383 AC-6, cell (vii): three routes, one branch each, nothing broader."""

    @pytest.mark.parametrize("route", ROUTES)
    def test_a_greek_title_flashes_the_refusal_and_not_the_generic_text(
        self, admin_app, monkeypatch, route
    ) -> None:
        client = admin_app.test_client()
        book_id = _make_book(admin_app)
        _retitle_first(admin_app, book_id, GREEK)

        response = _request_export(client, route, book_id)

        assert response.status_code == 302
        (message,) = _error_flashes(client)
        assert message != PDF_EXPORT_FAILED
        assert GREEK in message and "U+03A7" in message
        assert "Rename" in message and "Arrangement" in message

    @pytest.mark.parametrize("route", ROUTES)
    def test_the_control_every_other_failure_still_flashes_the_generic_text(
        self, admin_app, monkeypatch, caplog, route
    ) -> None:
        # Same book, a Latin title (so the refusal does not apply)
        # and a failure injected at the interior export: it is NOT the
        # refusal, and says what it always said. Injected rather than left to
        # happen (a writer-less generator), so the cell is the same in a tree
        # whose generator is assembled.
        client = admin_app.test_client()
        book_id = _make_book(admin_app)
        _retitle_first(admin_app, book_id, "Winter Star")
        _raise_once(
            monkeypatch,
            BookPDFGenerator,
            "export_interior",
            RuntimeError("card383-other-failure"),
        )

        with caplog.at_level("ERROR", logger=PANEL_LOGGER):
            response = _request_export(client, route, book_id)

        assert response.status_code == 302
        assert _error_flashes(client) == [PDF_EXPORT_FAILED]
        assert len(_panel_errors(caplog)) == 1

    @pytest.mark.parametrize("route", ROUTES)
    @pytest.mark.parametrize(
        "other",
        [errors.UnletterableTitle, errors.InvalidPuzzleName, errors.NonogramError],
        ids=lambda cls: cls.__name__,
    )
    def test_no_other_domain_error_is_caught_by_the_new_branch(
        self, admin_app, monkeypatch, route, other
    ) -> None:
        client = admin_app.test_client()
        book_id = _make_book(admin_app)
        _raise_once(monkeypatch, BookPDFGenerator, "__init__", other("their words"))

        _request_export(client, route, book_id)

        assert _error_flashes(client) == [PDF_EXPORT_FAILED]

    @pytest.mark.parametrize("route", ROUTES)
    def test_what_is_flashed_is_the_refusals_own_text_and_never_its_cause(
        self, admin_app, monkeypatch, caplog, route
    ) -> None:
        client = admin_app.test_client()
        book_id = _make_book(admin_app)
        marker = "card383-driver-marker-password=hunter2"
        refusal = errors.UnsettablePuzzleTitle(
            f"Puzzle 1 (\u201c{GREEK}\u201d) cannot be printed. Rename it.",
            puzzle_id="p",
            puzzle_number=1,
            title=GREEK,
            characters=("\u03a7",),
        )
        refusal.__cause__ = RuntimeError(marker)
        refusal.__context__ = RuntimeError(marker)
        _raise_once(monkeypatch, BookPDFGenerator, "__init__", refusal)

        with caplog.at_level("INFO", logger=PANEL_LOGGER):
            response = _request_export(client, route, book_id)

        body = response.get_data(as_text=True)
        assert _error_flashes(client) == [str(refusal)]
        assert marker not in body
        assert marker not in html.unescape(body)
        assert not any(marker in m for _, m in _flashes(client))
        for name, value in response.headers.items():
            assert marker not in value, name


# --------------------------------------------------------------------------
# CARD-480 — the same rule for the rest of the panel
# --------------------------------------------------------------------------

import ast as _ast

import nonogram.admin.app as _app_module

#: The panel's source, read for the population of handlers below.
_APP_SOURCE = Path(_app_module.__file__).read_text(encoding="utf-8")

#: The only things a broad handler may do with the exception it binds: re-raise
#: it, log it, test what it is (``isinstance``, and the two predicates that
#: tell the page plan's failures apart), stamp it as logged (``setattr``), or
#: hand it to Finalise's plan-failure page — whose on-screen text is CARD-171's
#: deliberate exception: it shows only a failure already stamped as the page
#: plan's own and already logged.
_ALLOWED_USES = {
    "isinstance", "setattr", "_is_an_unpackable_row", "_is_a_logged_plan_failure",
    "_page_plan_failure_page",
}

#: Broad handlers in app.py at this card's head (22, by ``_is_broad``): a
#: floor, so the population cannot silently shrink.
_BROAD_HANDLER_FLOOR = 22


def _is_broad(handler: _ast.ExceptHandler) -> bool:
    """A handler for any exception at all: bare, ``Exception`` or
    ``BaseException``, alone or in a tuple."""
    if handler.type is None:
        return True
    names = handler.type.elts if isinstance(handler.type, _ast.Tuple) else [handler.type]
    return any(isinstance(n, _ast.Name) and n.id in {"Exception", "BaseException"} for n in names)


def _forbidden_uses(handler: _ast.ExceptHandler) -> list[str]:
    """Every read of the handler's bound name that is not one of the allowed
    uses — default-deny: a read is allowed only as an argument of an allowed
    call, inside a logging call, or as what ``raise`` raises."""
    if not handler.name:
        return []
    allowed = set()
    for node in _ast.walk(_ast.Module(body=handler.body, type_ignores=[])):
        if isinstance(node, _ast.Call):
            func = node.func
            name = func.id if isinstance(func, _ast.Name) else getattr(func, "attr", None)
            is_log = isinstance(func, _ast.Attribute) and isinstance(func.value, _ast.Attribute) and func.value.attr == "logger"
            if name in _ALLOWED_USES or is_log:
                allowed.update(id(a) for a in node.args)
        if isinstance(node, _ast.Raise) and isinstance(node.exc, _ast.Name):
            allowed.add(id(node.exc))
    return [
        f"line {node.lineno}"
        for node in _ast.walk(_ast.Module(body=handler.body, type_ignores=[]))
        if isinstance(node, _ast.Name) and node.id == handler.name
        and isinstance(node.ctx, _ast.Load) and id(node) not in allowed
    ]


def _shows_something(handler: _ast.ExceptHandler) -> bool:
    """Whether the handler puts anything on screen itself: a flash, a
    rendered template, a ``return``, or a line appended to a list that the
    page shows."""
    for node in _ast.walk(_ast.Module(body=handler.body, type_ignores=[])):
        if isinstance(node, _ast.Return) and not (
            node.value is None or (isinstance(node.value, _ast.Constant) and node.value.value is None)
        ):
            return True
        if isinstance(node, _ast.Call):
            func = node.func
            name = func.id if isinstance(func, _ast.Name) else getattr(func, "attr", None)
            if name in {"flash", "render_template", "jsonify", "append", "abort"}:
                return True
    return False


def _enclosing_function(tree, target) -> str:
    for node in _ast.walk(tree):
        if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
            if any(child is target for child in _ast.walk(node)):
                innermost = node.name
    return innermost


def test_no_broad_handler_puts_its_exception_on_screen() -> None:
    """AC-1, derived from the source: no handler in app.py that catches any
    exception at all reads its bound exception except to re-raise it, log
    it, test what it is, stamp it, or pass it to Finalise's plan-failure
    page. The proof pages' handler flashes a ValueError's own text
    (CARD-118's refusal for a trim with no room for the proof note); that
    read is the one listed exemption.

    And every broad handler that shows something, by this test's sink
    model, is planted by
    :func:`test_a_planted_failure_shows_fixed_text_and_is_logged`: the plant
    list is held to that population. The sink model is the handler's own
    body only — a ``return`` of anything but ``None``, or a call named
    ``flash``, ``render_template``, ``jsonify``, ``append`` or ``abort``.
    A handler that shows text any other way is outside it and goes
    unplanted (measured in review: text written into the session, or into a
    variable rendered after the ``try``).

    What it cannot see, measured: an exception reached without its bound
    name (``traceback.format_exc()``, ``sys.exc_info()``, ``__context__``), a
    value stamped onto it with ``setattr`` and read back, a broad type
    spelled other than as a bare name (``builtins.Exception``), and a call to
    the plan-failure page from a handler that has not checked the stamp.
    The plants below are what catch the first three on the routes they
    cover."""
    tree = _ast.parse(_APP_SOURCE)
    handlers = [n for n in _ast.walk(tree) if isinstance(n, _ast.ExceptHandler) and _is_broad(n)]
    assert len(handlers) >= _BROAD_HANDLER_FLOOR, len(handlers)

    leaks = {}
    for handler in handlers:
        uses = _forbidden_uses(handler)
        if uses:
            leaks[handler.lineno] = uses
    # The one exemption: the proof pages' ValueError branch, located by text.
    proof = _APP_SOURCE.index('flash(f"Failed to generate proof pages: {e}", "error")')
    proof_line = _APP_SOURCE.count("\n", 0, proof) + 1
    assert list(leaks.values()) == [[f"line {proof_line}"]], leaks

    showing = sorted(
        (_enclosing_function(tree, h), _fixed_sentence(h)) for h in handlers
        if _shows_something(h) and not _shows_through_plan_failure_page(h)
        and (_enclosing_function(tree, h), _fixed_sentence(h)) not in _PLANTED_BY_CARD_177
    )
    assert showing == sorted((fn, name) for fn, _status, name in _SURFACES.values()), showing



#: CARD-177's three handlers, by (function, fixed sentence); they are planted
#: by the tests above this section, through ``SEAMS``. Keyed by both, so a new
#: handler elsewhere that shows one of these sentences is not exempt.
_PLANTED_BY_CARD_177 = {
    ("finalize_book", "FINALISE_ACTION_FAILED"),
    ("generate_book_pdf_download", "PDF_EXPORT_FAILED"),
    ("generate_book_pdf", "PDF_EXPORT_FAILED"),
}


def _fixed_sentence(handler: _ast.ExceptHandler) -> str:
    """The ``*_FAILED`` constant a handler shows, or ``""``."""
    names = {
        n.id for n in _ast.walk(_ast.Module(body=handler.body, type_ignores=[]))
        if isinstance(n, _ast.Name) and n.id.endswith("_FAILED") and n.id.isupper()
    }
    assert len(names) <= 1, names
    return names.pop() if names else ""


def _shows_through_plan_failure_page(handler: _ast.ExceptHandler) -> bool:
    """Finalise's two handlers that show only CARD-171's plan-failure page
    (its deliberate exception, see ``_ALLOWED_USES``); not planted here."""
    return any(
        isinstance(n, _ast.Call) and isinstance(n.func, _ast.Name)
        and n.func.id == "_page_plan_failure_page"
        for n in _ast.walk(_ast.Module(body=handler.body, type_ignores=[]))
    )

#: A message no fixed sentence holds, carrying what a driver error would.
_MARKER = "card480 host=db.internal user=panel password=hunter2"


def _raising(error):
    def boom(*_args, **_kwargs):
        raise error
    return boom


def _png(path, size=(60, 60)):
    from PIL import Image as _Image

    image = _Image.new("L", size, 255)
    for x in range(15, 45):
        for y in range(15, 45):
            image.putpixel((x, y), 0)
    image.save(path)
    return path


def _plant(app, monkeypatch, tmp_path, client, surface):
    """Raise ``RuntimeError(_MARKER)`` at ``surface``'s seam, inside the
    converted handler's ``try``; the response and the error."""
    error = RuntimeError(_MARKER)
    images = _app_module.get_image_manager()
    images.clear_all()
    if surface in {"batch_upload_file", "batch_upload"}:
        if surface == "batch_upload_file":
            monkeypatch.setattr(images, "add_image", _raising(error))
        else:
            monkeypatch.setattr(images, "clear_all", _raising(error))
        with open(_png(tmp_path / "upload.png"), "rb") as handle:
            return client.post(
                "/batch/from-images", data={"image_files": (handle, "upload.png")}
            ), error
    if surface in {"batch_generate_picture", "batch_generate"}:
        assert images.add_image(str(_png(tmp_path / "pic.png")), "pic.png")
        if surface == "batch_generate_picture":
            monkeypatch.setattr(_app_module, "_generate_image_puzzle", _raising(error))
        else:
            monkeypatch.setattr(app.batch_generator, "create_batch", _raising(error))
        return client.post("/batch/generate-puzzles"), error
    if surface in {"image", "cropped_image"}:
        added = images.add_image(str(_png(tmp_path / "shown.png")), "shown.png")
        assert added
        if surface == "image":
            monkeypatch.setattr(_app_module, "send_file", _raising(error))
            return client.get(f"/api/image/{added.file_id}"), error
        import nonogram.sourcing.image as _sourcing_image

        monkeypatch.setattr(_sourcing_image, "load_greyscale", _raising(error))
        return client.get(f"/api/image/{added.file_id}/cropped"), error
    if surface == "cover_upload":
        book_id = _make_book(app, puzzle_count=1)
        monkeypatch.setattr(_app_module.PILImageOps, "exif_transpose", _raising(error))
        with open(_png(tmp_path / "cover.png"), "rb") as handle:
            return client.post(
                f"/book/{book_id}/finalize", data={"cover": (handle, "cover.png")}
            ), error
    if surface == "delete_book":
        book_id = app.book_manager.create_book(
            title="Winter", description="d", theme="generic", target_audience="adults")
        _raise_once(monkeypatch, app.book_manager, "delete_book", error)
        return client.post(f"/book/{book_id}/delete"), error
    if surface == "proof":
        book_id = _make_book(app, puzzle_count=1)
        monkeypatch.setattr(_app_module, "render_proof_pdf", _raising(error))
        return client.get(f"/book/{book_id}/proof-pages"), error
    if surface == "player_bundle":
        book_id = _make_book(app, puzzle_count=1)
        monkeypatch.setattr(_app_module.player_bundle, "export_bundle", _raising(error))
        return client.post(f"/book/{book_id}/export-player-bundle"), error
    book_id = _make_book(app, puzzle_count=1)
    puzzle_id = app.book_manager.get_book(book_id).puzzle_ids[0]
    if surface in {"grid", "grid_download"}:
        monkeypatch.setattr(_app_module, "grid_to_svg", _raising(error))
        suffix = "/download" if surface == "grid_download" else ""
        return client.get(f"/api/puzzle/{puzzle_id}/grid{suffix}"), error
    if surface == "grid_pdf":
        monkeypatch.setattr(_app_module, "render" "_pages", _raising(error))
        return client.get(f"/api/puzzle/{puzzle_id}/grid/download-pdf"), error
    raise AssertionError(surface)


#: Each surface: the function whose broad handler it plants, the status its
#: route answered before this card (G-1 / AC-4, measured at the merge-base),
#: and the name of the fixed sentence that handler now shows.
_SURFACES = {
    "batch_upload_file": ("batch_from_images", 302, "PICTURE_UPLOAD_FAILED"),
    "batch_upload": ("batch_from_images", 302, "BATCH_UPLOAD_FAILED"),
    "batch_generate_picture": ("generate_batch_puzzles", 302, "PICTURE_GENERATE_FAILED"),
    "batch_generate": ("generate_batch_puzzles", 200, "BATCH_GENERATE_FAILED"),
    "cover_upload": ("finalize_book", 200, "COVER_UPLOAD_FAILED"),
    # Spelled in two pieces, as is the render API below: this module only
    # RAISES at those names, and tests/test_suite_profile.py's frozen render
    # census (meta/profiling/rank_durations.py's RENDER_API_PATTERN) greps
    # tests/ for them — a module that renders nothing would join it.
    "proof": ("download_book_proof" "_pages", 302, "PROOF_PAGES_FAILED"),
    "delete_book": ("delete_book", 302, "BOOK_DELETE_FAILED"),
    "player_bundle": ("export_player_bundle", 302, "PLAYER_EXPORT_FAILED"),
    "image": ("api_get_image", 500, "IMAGE_SERVE_FAILED"),
    "cropped_image": ("api_get_cropped_image", 500, "IMAGE_SERVE_FAILED"),
    "grid": ("api_puzzle_grid_from_puzzle", 500, "GRID_SERVE_FAILED"),
    "grid_download": ("api_puzzle_grid_download_from_puzzle", 500, "GRID_SERVE_FAILED"),
    "grid_pdf": ("api_puzzle_grid_download_pdf", 500, "GRID_SERVE_FAILED"),
}


#: The file name a per-picture sentence follows, per surface.
_PICTURE = {"batch_upload_file": "upload.png", "batch_generate_picture": "pic.png"}


@pytest.mark.parametrize("surface", sorted(_SURFACES))
def test_a_planted_failure_shows_fixed_text_and_is_logged(
    admin_app, monkeypatch, tmp_path, caplog, surface
) -> None:
    """AC-1 (every broad handler that shows anything: flash, page, plain
    text), AC-3 and AC-4. The planted message reaches neither the body nor a
    flash; the handler's own fixed sentence does; the error is in the
    panel's log once, with its traceback; the status is the old one."""
    client = admin_app.test_client()
    caplog.set_level("ERROR", logger=PANEL_LOGGER)
    try:
        response, error = _plant(admin_app, monkeypatch, tmp_path, client, surface)
        # Unescaped: a page that renders the flash escapes its apostrophe.
        shown = html.unescape(response.get_data(as_text=True)) + repr(_flashes(client))
    finally:
        monkeypatch.undo()
        _app_module.get_image_manager().clear_all()

    _function, status, name = _SURFACES[surface]
    # The two per-picture sentences follow the picture's own name; matched
    # whole, or the whole-batch sentence (which ends the same) would pass.
    expected = f"{_PICTURE.get(surface, '')} {getattr(_app_module, name)}".strip()
    assert response.status_code == status
    assert "hunter2" not in shown and "card480" not in shown, shown[:300]
    assert expected in shown, (expected, shown[-400:])
    logged = [r for r in _panel_errors(caplog) if r.exc_info and r.exc_info[1] is error]
    assert len(logged) == 1 and logged[0].exc_info[2] is not None


def test_a_domain_refusal_still_says_what_it_is(admin_app, monkeypatch, caplog) -> None:
    """AC-2, one control per surface a touched handler or its route uses.
    Flash: the proof pages' expected refusal is a ValueError written for the
    owner, and still reaches the flash — and its redirect (CARD-496,
    IDEA-015) goes back to a same-site Referer, never to an off-site one,
    which gives way to Print setup. JSON: the puzzles API's own
    refusal of an out-of-range value still answers with its message (an
    untouched ``except ValueError``). Plain text: the touched plain-text
    routes have no domain refusal of their own — their refusals ("Not
    found", "No grid data") answer before the handler, unchanged."""
    client = admin_app.test_client()
    book_id = _make_book(admin_app, puzzle_count=1)
    refusal = ValueError("this trim leaves no room for the proof note")
    monkeypatch.setattr(_app_module, "render_proof_pdf", _raising(refusal))
    response = client.get(f"/book/{book_id}/proof-pages", headers=OFF_SITE_REFERER)
    assert response.status_code == 302
    assert ("error", f"Failed to generate proof pages: {refusal}") in _flashes(client)
    assert response.headers["Location"].endswith(f"/book/{book_id}/setup-print")
    assert "evil.example" not in response.headers["Location"]
    # Review F-001: the scheme and the port are part of "same site" too. Another
    # service on this host, and a script URL naming this host, each fall back.
    for referer in (
        f"http://localhost:5001/book/{book_id}/finalize",
        "javascript://localhost/%0aalert(1)",
    ):
        other = client.get(f"/book/{book_id}/proof-pages", headers={"Referer": referer})
        assert other.headers["Location"].endswith(f"/book/{book_id}/setup-print"), referer
    same_site = f"http://localhost/book/{book_id}/finalize"
    back = client.get(f"/book/{book_id}/proof-pages", headers={"Referer": same_site})
    assert back.headers["Location"] == same_site

    refused = client.get("/api/puzzles?limit=1000")
    assert (refused.status_code, refused.get_json()) == (400, {"error": "Limit must be 1-100"})


@pytest.mark.parametrize("route", ["", "/cropped", "gone-while-sent"])
def test_a_missing_image_file_does_not_name_the_servers_path(
    admin_app, monkeypatch, tmp_path, route
) -> None:
    """Reviewer cycle 1, F-007: an image whose stored file has gone answers
    404 as before, on both image routes and in the image route's
    FileNotFoundError branch (the file going between the check and the
    send), without the server's path."""
    images = _app_module.get_image_manager()
    images.clear_all()
    try:
        path = _png(tmp_path / "gone.png")
        added = images.add_image(str(path), "gone.png")
        if route == "gone-while-sent":
            monkeypatch.setattr(_app_module, "send_file", _raising(FileNotFoundError(added.file_path)))
            url = f"/api/image/{added.file_id}"
        else:
            Path(added.file_path).unlink()  # the copy the manager keeps
            assert not Path(added.file_path).exists()
            url = f"/api/image/{added.file_id}{route}"
        response = admin_app.test_client().get(url)
    finally:
        images.clear_all()
    assert (response.status_code, response.get_data(as_text=True)) == (404, "Image file not found")


def test_the_500_page_shows_what_the_panel_aborted_with_on_purpose(admin_app) -> None:
    """The other half of the 500 page: ``abort(500, description=...)`` is a
    message the panel wrote for the user (the solver page's "no readable
    grid"), and it is shown. The merge gate measured this card's first
    version, which dropped ``str(e)`` from the page, hiding it."""
    admin_app.config["PROPAGATE_EXCEPTIONS"] = False

    def deliberate():
        from flask import abort

        abort(500, description="card480 written for the owner")

    admin_app.add_url_rule("/card480-deliberate", "card480_deliberate", deliberate)
    response = admin_app.test_client().get("/card480-deliberate")
    assert response.status_code == 500
    assert "card480 written for the owner" in response.get_data(as_text=True)


def test_the_500_page_shows_no_error_text(admin_app) -> None:
    """The global 500 page shows no unhandled exception's text. It passes
    ``str(e)``, which for an unhandled exception is werkzeug's own generic
    sentence, so it never leaked there and this card leaves it as it was: a
    regression guard, not a discriminating test."""
    admin_app.config["PROPAGATE_EXCEPTIONS"] = False
    admin_app.add_url_rule("/card480-boom", "card480_boom", _raising(RuntimeError(_MARKER)))
    response = admin_app.test_client().get("/card480-boom")
    assert response.status_code == 500
    assert "hunter2" not in response.get_data(as_text=True)
