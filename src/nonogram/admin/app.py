"""Flask admin panel application for nonogram puzzle management.

The listening socket
--------------------
:data:`LOOPBACK_HOST` is the one load-bearing line in this module. The admin
panel has no authentication, no CSRF token and a route that rewrites every
stored grade (``POST /regrade``, CARD-077), so NFR-003's answer to "who can
reach this?" is "whoever is on this machine" — and that answer is a property of
the bind address, not of anything a request carries.

It was ``0.0.0.0`` with ``debug=True`` until CARD-081: every interface, plus a
Werkzeug debug console, which is remote code execution rather than an
information leak. CARD-077's review found the card asserting the opposite
(cycle 1, F-003) because no test had ever checked.

Two entry points reach the socket and only one of them is ours:

* ``python -m nonogram.admin.app`` runs :func:`main` below, which takes no host
  and passes :data:`LOOPBACK_HOST`.
* ``flask --app nonogram.admin.app run`` — the path ``ADMIN_SETUP.md``
  documents — is Flask's own CLI. It defaults to ``127.0.0.1``, so it is
  correct out of the box, but ``--host`` is its argument and this module cannot
  take it away. :func:`_reject_non_loopback_requests` is why that is survivable:
  a request that arrives over a widened bind is refused by ``Host`` header, the
  same defence ``nonogram.web`` applies at its own boundary (CON-010).

The two are deliberately independent. The bind is the wall; the header check is
what stands when someone opens a door in it.
"""

from flask import Flask, Response, abort, render_template, request, jsonify, flash, redirect, url_for, session, send_file
from datetime import datetime
import hmac
import json
import os
import tempfile
import urllib.parse
import uuid
from pathlib import Path
from io import BytesIO

from .batch_generator import get_batch_generator, BatchStatus, BatchGenerator
from .puzzle_review import (
    get_puzzle_review_service,
    MAX_PUZZLE_NAME_LENGTH,
    PuzzleFilter,
    PuzzleReviewService,
    PuzzleStatus,
)
from .book_manager import get_book_manager, BookStatus
from .pdf_generator import get_pdf_generator
from .image_manager import (
    CANNOT_FIT,
    MOVED_TO_LARGE,
    SIZE_PRESETS,
    floor_percent,
    get_image_manager,
)
from .grid_renderer import grid_to_svg
from .print_specs import PrintSpecValidator
from .book_pdf_generator import BookPDFGenerator, tier_breakdown

# Import the professional export PDF module
from nonogram.export.pdf import render_pages
from nonogram.export import ExportPayload
from nonogram import clues, orchestrator
from nonogram.difficulty import Tier
from nonogram.errors import GenerationAbandoned, NonogramError, NotUniquelySolvable
from nonogram.limits import MAX_SIZE, MIN_SIZE
from nonogram.orchestrator import MAX_BATCH_COUNT

# CARD-050: real image-mode quality/recognizability, in place of the
# density-only heuristic and hardcoded "medium" this replaces below.
from PIL import Image as PILImage
from nonogram.analysis.quality_metric import measure_quality


#: What the create-batch form asks for when the operator does not say.
#:
#: 100 before CARD-088, which asked for roughly 390 s of work at 30x30 from a
#: server that waits 120 — the commonest request anyone makes was the one that
#: could not finish, and nothing pointed at the *default* as the cause.
#:
#: 15 rather than 20, and the difference is the whole point of having a test
#: for it: at the measured 3.9 s per puzzle at 30x30, twenty would cost 78 s
#: against a 75 s batch budget, so the default request would come back *short*
#: at the top of the supported range. A default that silently truncates is a
#: worse default than a small one.
DEFAULT_BATCH_COUNT = 15


#: The statuses a puzzle can be filtered by, in curation order (CARD-066).
#: Read from the enum so the page cannot drift from the store.
_PUZZLE_STATUSES = tuple(status.value for status in PuzzleStatus)


def _generate_image_puzzle(image, width, height):
    """Generate ``image`` at ``(width, height)``; if that extent is abandoned
    (not uniquely solvable within the pixel-nudge bound), retry at the
    long-side ±1 neighbours from ``image.neighbour_extents`` (CARD-062).

    Generation is deterministic per picture and extent, so no extent is tried
    twice. On the predicted extent any other error propagates at once: a
    different extent cannot fix an unreadable picture. On a neighbour, any
    other ``NonogramError`` (e.g. a solver timeout) ends the retry and the
    predicted extent's abandonment is what gets reported — that is the
    picture's real problem, not the neighbour's side effect.

    Returns:
        ``(puzzle, extent_used)``.

    Raises:
        GenerationAbandoned: the predicted extent's own error, when it and
            every neighbour were abandoned.
    """
    first_abandonment = None
    for extent in [(width, height), *image.neighbour_extents((width, height))]:
        request = orchestrator.GenerationRequest(
            mode="image",
            image=Path(image.file_path),
            image_filename=image.original_filename,
            width=extent[0],
            height=extent[1],
        )
        try:
            return orchestrator.generate(request), extent
        except GenerationAbandoned as error:
            if first_abandonment is None:
                first_abandonment = error
        except NonogramError:
            if first_abandonment is None:
                raise
            break
    raise first_abandonment


def _page_window(total_count: int, limit: int, offset: int, width: int = 5) -> dict:
    """Numbered pagination for a list of ``total_count`` items shown ``limit``
    at a time: up to ``width`` page numbers centred on the current page where
    possible and clamped to the real page range, plus the offsets the First,
    Previous, Next and Last links jump to."""
    limit = max(limit, 1)
    pages = max(1, -(-total_count // limit))
    current = min(offset // limit + 1, pages)
    start = max(1, min(current - width // 2, pages - width + 1))
    end = min(pages, start + width - 1)
    return {
        "current": current,
        "pages": pages,
        "numbers": [(n, (n - 1) * limit) for n in range(start, end + 1)],
        "first_offset": 0,
        "prev_offset": max(0, (current - 2) * limit),
        "next_offset": current * limit,
        "last_offset": (pages - 1) * limit,
    }


#: How each FR-029 strategy name reads on a puzzle card, easiest first.
#: A name not listed here is shown as stored rather than hidden.
STRATEGY_LABELS = {
    "simple_overlap": "Simple overlap",
    "line_dp": "Full line solving",
    "probe_contradiction": "Contradiction probing",
    "guess": "Guessing (trial and error)",
}


def _strategy_view(names) -> list[dict] | None:
    """``[{"name", "label"}]`` for a strategies list, or ``None`` if unknown."""
    if names is None:
        return None
    return [{"name": name, "label": STRATEGY_LABELS.get(name, name)} for name in names]


def _list_return_query(raw: str | None) -> str:
    """The review list's filter/sort/page query a puzzle action came from,
    re-encoded from its parsed pairs so only a query string — never a path
    or another host — can come back out of the redirect."""
    pairs = urllib.parse.parse_qsl((raw or "").lstrip("?"), keep_blank_values=True)
    return urllib.parse.urlencode(pairs)


#: The only address the admin's own entry point binds (NFR-003, CON-009).
#:
#: A constant, not a parameter: :func:`main` takes no host, so there is no
#: supported call that widens it. Pinned by
#: ``tests/test_admin_binding.py::TestAdminPanel_BindsLoopbackOnlyByDefault``.
LOOPBACK_HOST = "127.0.0.1"

#: The admin's default port. ``ADMIN_SETUP.md`` documents 8888/8889 via
#: ``flask run --port``; this is only what ``python -m nonogram.admin.app`` uses.
DEFAULT_PORT = 5000

#: Host header values that name this machine.
#:
#: Reimplemented here rather than imported from ``nonogram.web.handler``, which
#: has the same frozenset: ADR-0007 forbids the lateral import, and CLAUDE.md's
#: rule for exactly this case is to reimplement natively (the precedent is
#: ``solver/propagate.py``'s ``mask_runs``). Two short allowlists that agree is
#: the intended shape; one importing the other is not.
ALLOWED_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


def _host_is_local(host_header: str | None) -> bool:
    """Does this ``Host`` header name this machine?

    One sentence: *the value must be a bare authority — no userinfo, path,
    query or fragment, and a port that is absent or all digits — whose host
    component is one of three names.*

    The port's value is ignored (``127.0.0.1:8888`` and ``127.0.0.1`` are the
    same host); its shape is not. Parsed with ``urlsplit`` rather than by
    splitting on ``":"`` so a bracketed ``[::1]:5000`` reads as the host
    ``::1`` and not as ``[``.

    ``@``, ``/``, ``#`` and ``?`` are refused *before* parsing, and that order
    matters. ``urlsplit`` splits all four off, so it reads
    ``evil.com:80@127.0.0.1`` as the host ``127.0.0.1`` — which is how the
    first version of this function let that value through, until
    ``tests/test_admin_binding.py`` said so. An authority is not a URL: RFC
    7230 §5.4 admits none of the four, so a value carrying one is not a host
    name whatever its host component parses to.

    A missing header is refused too. HTTP/1.1 requires one; a request without
    it is not a browser asking for a page.

    This is ``nonogram.web.handler._host_is_local`` reimplemented, not
    imported — ADR-0007 forbids the lateral import, and CLAUDE.md's rule for
    this case is to reimplement natively. The test tree, where the import is
    legal, is what holds the two copies to the same answer.

    The parse itself moved to :func:`_hostname_of` when CARD-085 added a second
    question about the same header. This function's answer is unchanged: the
    same values are refused for the same reasons, and CARD-081's test class
    pins that.
    """
    return _hostname_of(host_header) in ALLOWED_HOSTS


def _port_is_well_formed(authority: str) -> bool:
    """Is the port component absent, or present and all digits?

    An empty port (``127.0.0.1:``) and a non-numeric one (``127.0.0.1:evil``)
    are both read by ``urlsplit`` as the *host* ``127.0.0.1``, so a check
    consulting only the host component would serve them. Neither is a
    well-formed authority; RFC 3986 §3.2.3 admits digits and nothing else.

    The split is taken after the last ``]`` so the colons inside a bracketed
    IPv6 literal are not mistaken for the port separator.
    """
    after_brackets = authority.rsplit("]", 1)[-1]
    _, colon, port = after_brackets.rpartition(":")
    if not colon:
        return True
    return port.isascii() and port.isdigit()


#: The environment variable that opens the *deployed* door (CARD-085).
#:
#: Unset is the whole of CARD-081's behaviour: loopback only, no credential.
#: Set to one hostname — ``nonogram-admin.onrender.com`` — it closes that door
#: and opens a different one: that host, with a credential, and nothing else.
#: Never both at once; see :func:`create_app`'s hook for why.
REMOTE_HOST_VAR = "ADMIN_ALLOWED_HOST"

#: Where the credential comes from. The password has no default on purpose —
#: :func:`create_app` refuses to boot without one when remote access is on.
ADMIN_USER_VAR = "ADMIN_USER"
ADMIN_PASSWORD_VAR = "ADMIN_PASSWORD"
DEFAULT_ADMIN_USER = "admin"

#: The session-signing key this module falls back to, and the one value that
#: must never reach a reachable deployment.
#:
#: It is a literal in this file, so it is a literal in every clone of this
#: repository: cookies signed with it can be forged by anyone who has read the
#: source. Harmless while the panel answers only to this machine, which is why
#: it survived; :func:`create_app` treats it as a fatal misconfiguration the
#: moment :data:`REMOTE_HOST_VAR` is set.
DEV_SECRET_KEY = "dev-key-change-in-production"

#: The shortest ``ADMIN_PASSWORD`` :func:`create_app` will boot with.
#:
#: The check that only asked "is it non-empty?" was the right check for a panel
#: nobody could reach. Once :data:`REMOTE_HOST_VAR` is set the password is the
#: entire defence, there is no rate limiting in this package, and
#: :data:`DEFAULT_ADMIN_USER` means the other half of the credential is usually
#: guessable — so a one-character password is not a weak configuration, it is an
#: open panel with a formality in front of it. ``ADMIN_SETUP.md`` tells the
#: operator to generate 32 bytes; this is what makes that instruction binding
#: rather than advisory (CARD-085 review F-003).
MIN_ADMIN_PASSWORD_LENGTH = 16

#: The ``Sec-Fetch-Site`` values the deployed panel answers.
#:
#: ``same-origin`` is a form posting back to the page it was served from;
#: ``none`` is a user-initiated navigation with no initiator document — a typed
#: URL, a bookmark. The two the fetch-metadata spec defines and this omits,
#: ``same-site`` and ``cross-site``, both say the request was started by a
#: document this panel did not serve, which is the whole of the attack.
#:
#: Reimplemented here rather than imported from ``nonogram.web.handler``, which
#: holds the identical frozenset for the identical reason: ADR-0007 forbids the
#: lateral import and CLAUDE.md's rule is to reimplement natively and hold the
#: two copies together from the test tree — the shape CARD-081 already used for
#: :data:`ALLOWED_HOSTS`.
ALLOWED_FETCH_SITES = frozenset({"same-origin", "none"})


class AdminConfigurationError(RuntimeError):
    """The admin was asked to serve remotely without the means to do it safely.

    Deliberately *not* a :class:`nonogram.errors.NonogramError`: that hierarchy
    is the domain's, and every member of it is something the CLI maps onto an
    exit code for a user who asked for a puzzle. This is an operator telling
    the process to start in a configuration it must refuse — it belongs to the
    admin adapter, and the only correct response to it is a failed boot.

    Raised at :func:`create_app` time rather than per request, so a deploy that
    forgot the password dies in its build logs instead of coming up serving an
    open panel. A loud failure is recoverable in a minute; an open admin is
    not recoverable at all.
    """


def _hostname_of(host_header: str | None) -> str | None:
    """The host component of a ``Host`` header, or ``None`` if it is not one.

    Everything :func:`_host_is_local` used to do inline, minus the final
    comparison, so that the *second* question this module now asks — "is this
    the one host we were configured to answer to?" — is asked of exactly the
    same parse. Two host checks that disagree about what a host is would be a
    bypass waiting to happen.

    The rules and the reasons for them are unchanged; see
    :func:`_host_is_local`.
    """
    if not host_header:
        return None
    if any(char in host_header for char in "@/#?"):
        return None
    if not _port_is_well_formed(host_header):
        return None
    try:
        return urllib.parse.urlsplit(f"//{host_header}").hostname
    except ValueError:
        return None


def _configured_hostname(raw: str) -> str:
    """Reduce whatever the operator pasted into ``ADMIN_ALLOWED_HOST`` to a host.

    The dashboard this value is copied from shows a *URL*
    (``https://nonogram-admin.onrender.com``), so that is what gets pasted, and
    the first version of this code compared it against a bare ``Host`` header —
    which never matches, so every route 404s with no explanation anywhere. The
    operator is then debugging the one refusal the panel deliberately makes
    indistinguishable from "no such page" (CARD-086, after it happened).

    So the common shapes are accepted and normalised rather than rejected: a
    bare host, a URL with a scheme, either with a trailing slash, either with a
    port, any case, any surrounding whitespace. What cannot be reduced to a
    hostname raises :class:`AdminConfigurationError` at boot, where an operator
    is looking at a log, instead of failing silently at request time.

    Returns the lower-cased hostname, which is what
    :func:`_hostname_of` produces for the incoming header — the two have to be
    the output of the same kind of parse or the comparison is a guess.
    """
    value = raw.strip()
    if not value:
        raise AdminConfigurationError(f"{REMOTE_HOST_VAR} is set but empty.")

    # A bare authority is not a URL, so give urlsplit a scheme to find when the
    # operator did not paste one.
    candidate = value if "//" in value else f"//{value}"
    try:
        split = urllib.parse.urlsplit(candidate)
    except ValueError as bad_url:
        raise AdminConfigurationError(
            f"{REMOTE_HOST_VAR}={raw!r} cannot be read as a host name."
        ) from bad_url

    if split.path not in ("", "/") or split.query or split.fragment:
        raise AdminConfigurationError(
            f"{REMOTE_HOST_VAR}={raw!r} carries a path, query or fragment. It "
            f"names the host this panel answers to, not a URL to visit — set "
            f"it to just the host name, e.g. 'nonogram-admin.onrender.com'."
        )

    hostname = split.hostname
    if not hostname:
        raise AdminConfigurationError(
            f"{REMOTE_HOST_VAR}={raw!r} has no host name in it. Set it to the "
            f"service's host, e.g. 'nonogram-admin.onrender.com'."
        )
    return hostname


def _host_is_the_configured_remote(host_header: str | None, expected: str) -> bool:
    """Does this ``Host`` name the one host remote access was configured for?

    An equality test, not an allowlist: the deployed door admits exactly one
    name. Both sides come out of :func:`urllib.parse.urlsplit`'s ``hostname``,
    which lower-cases — the header through :func:`_hostname_of`, the configured
    value through :func:`_configured_hostname` at boot. Two host checks that
    disagreed about what a host is would be a bypass waiting to happen, and
    two that parsed differently would be a 404 nobody could explain.
    """
    hostname = _hostname_of(host_header)
    return hostname is not None and hostname == expected


def _credential_is_correct(
    supplied, expected_user: str, expected_password: str
) -> bool:
    """Is this request carrying the configured username *and* password?

    Both halves are compared every time, with :func:`hmac.compare_digest`, and
    the ``and`` is applied to two values that have *already been computed*. A
    wrong username therefore costs the same work as a wrong password. The
    obvious spelling — ``if user != expected: return False`` — leaks which half
    was wrong through timing, which turns one unknown into two known-separately.

    Compared as UTF-8 bytes rather than as ``str``: ``compare_digest`` refuses
    a ``str`` containing anything outside ASCII, and a password that raises
    ``TypeError`` instead of returning ``False`` would be an availability bug
    reachable by anyone who can type a non-ASCII character into a login box.
    """
    username = (supplied.username or "") if supplied else ""
    password = (supplied.password or "") if supplied else ""

    username_ok = hmac.compare_digest(
        username.encode("utf-8"), expected_user.encode("utf-8")
    )
    password_ok = hmac.compare_digest(
        password.encode("utf-8"), expected_password.encode("utf-8")
    )
    return username_ok and password_ok


def _origin_names(origin: str) -> str | None:
    """The host of an ``Origin`` header, or ``None`` if it is not an origin.

    An ``Origin`` is a *serialized origin* — ``scheme "://" host [":" port]``
    and nothing more (RFC 6454 6.1) — so a value carrying a path, a query or a
    fragment is not one, and the opaque origin ``null`` has no host at all.
    Each is refused rather than mined for a host substring.

    The scheme and port are read for shape and then discarded, exactly as the
    ``Host`` check discards the port: the question is which *name* the
    initiating document was served from.
    """
    value = origin.strip()
    try:
        split = urllib.parse.urlsplit(value)
    except ValueError:
        return None
    if not split.scheme or split.path or split.query or split.fragment:
        return None
    return _hostname_of(split.netloc)


def _is_top_level_navigation(method: str, headers) -> bool:
    """Is this the operator clicking a link to the panel from somewhere else?

    The one cross-site shape that must still be served. A link to the panel in
    a chat message, an email, or another tab's bookmark bar arrives as a
    top-level navigation with ``Sec-Fetch-Site: cross-site``, and refusing it
    would break the operator's most natural way in while buying nothing: every
    route in this panel that changes anything is a ``POST`` (``GET /regrade``
    is a preview that writes through a savepoint and rolls it back), so a
    cross-site ``GET`` has nothing to trigger.

    This is the standard fetch-metadata Resource Isolation Policy carve-out,
    and its three conditions are load-bearing together:

    * **a safe method** — a cross-site *form submission* is also a navigation
      to a document, and that is precisely the CSRF attack. Without the method
      test this exemption would re-open exactly what
      :func:`_request_is_cross_site` exists to close;
    * **``Sec-Fetch-Mode: navigate``** — not a ``fetch``/XHR;
    * **``Sec-Fetch-Dest: document``** — the top-level frame, not an
      ``<iframe>`` (``iframe``), an ``<img>`` (``image``), or a script.

    A request that omits the fetch-metadata headers never reaches here: absent
    means served, decided in :func:`_request_is_cross_site`.
    """
    if method.upper() not in {"GET", "HEAD"}:
        return False
    modes = {value.strip() for header in headers.get_all("Sec-Fetch-Mode")
             for value in header.split(",")}
    dests = {value.strip() for header in headers.get_all("Sec-Fetch-Dest")
             for value in header.split(",")}
    return modes == {"navigate"} and dests == {"document"}


def _request_is_cross_site(method: str, headers, expected_host: str) -> bool:
    """Did a document this panel did not serve start this request?

    The defence HTTP Basic auth does not provide. A browser caches the
    credential per origin and replays it on a *cross-site* form POST, so
    "carries the password" and "was sent deliberately by the operator" stopped
    being the same statement the moment the panel became reachable. Without
    this, any page the operator's browser loads can aim a form at
    ``POST /regrade`` and rewrite every stored grade — which after CARD-084
    keeps no copy of what it replaced (CARD-085 review F-001).

    Two headers, both of which page script is forbidden to set:

    * ``Sec-Fetch-Site`` other than :data:`ALLOWED_FETCH_SITES`;
    * ``Origin`` whose host is not the configured host.

    **Every** value of each header is read, not just the first: a request
    carrying two that disagree has no single answer, and taking the first is
    how an allowlisted value smuggles a foreign one past.

    Under WSGI that means splitting on commas, not iterating ``get_all``. The
    gateway folds repeated headers into a *single* comma-joined value before
    this code ever runs — ``Sec-Fetch-Site: same-origin`` twice over arrives as
    the one string ``"same-origin, cross-site"`` — so ``get_all`` returns one
    element and a loop over it reads the whole smuggled pair as one token.
    Measured, not assumed: a mutation restricting that loop to its first
    element changed nothing, because there was never a second
    (CARD-085 review, M7). Splitting is what makes "every value" true here; the
    loop over ``get_all`` is kept because a future non-WSGI gateway may stop
    folding, and then both arms matter.

    **Absent means served**, and that is safe rather than lucky. A cross-origin
    GET may legitimately carry no ``Origin`` — a ``no-cors`` fetch, an
    ``<img>``, a top-level navigation — so absence proves nothing on its own.
    It does not have to: the Fetch standard requires an ``Origin`` on every
    cross-origin request whose method is not GET/HEAD, plain
    ``<form method=post>`` included, and every route that writes here is a
    POST. On any browser implementing fetch metadata (Chrome 76+, Firefox 90+,
    Safari 16.4+) ``Sec-Fetch-Site`` catches the GET case too. Keeping absence
    servable is also what keeps ``curl``, a typed URL, and Render's own health
    probe working.

    ``Referer`` is deliberately not consulted: an attacking page can switch it
    off with a referrer policy, so a rule resting on it is one the attacker
    controls.

    One cross-site shape is still served: a top-level GET navigation — the
    operator clicking a link to the panel from a chat message or an email. See
    :func:`_is_top_level_navigation` for why that is safe here and for the
    three conditions that keep a cross-site *form post* out of the exemption.
    """
    foreign = False
    for header in headers.get_all("Sec-Fetch-Site"):
        for value in header.split(","):
            if value.strip() not in ALLOWED_FETCH_SITES:
                foreign = True
    for header in headers.get_all("Origin"):
        for value in header.split(","):
            if _origin_names(value) != expected_host:
                foreign = True

    if not foreign:
        return False
    return not _is_top_level_navigation(method, headers)


def _refuse_cross_site() -> Response:
    """403 for a request the browser itself says came from somewhere else.

    Not a 404: this caller reached the configured host *and* presented the
    credential, so there is nothing left to hide from them — and not a 401
    either, because re-prompting for a password would invite the operator to
    re-enter it in answer to a page they did not open.
    """
    return Response(
        "Refused: this request was started by another site.\n",
        403,
        mimetype="text/plain",
    )


def _ask_for_a_credential() -> Response:
    """401 with a challenge, which is the one refusal that has to be legible.

    The wrong-host refusal is a 404 that tells a scanner nothing (CARD-081).
    This one cannot be: a browser shows its password prompt only when it sees
    ``WWW-Authenticate``, so a caller who reached the right host is told, in
    the protocol's own words, that a credential is what is missing.

    That is not a leak. Being at :data:`REMOTE_HOST_VAR`'s hostname already
    means knowing the service exists; the 404 disguise protects the panel from
    people who do not, and this answers the people who do.
    """
    return Response(
        "Authentication required.\n",
        401,
        {"WWW-Authenticate": 'Basic realm="Nonogram admin", charset="UTF-8"'},
        mimetype="text/plain",
    )


def create_app(debug=None):
    """Create and configure the Flask admin panel app."""
    app = Flask(__name__, template_folder="templates")

    # Configuration from environment
    if debug is None:
        debug = os.getenv("FLASK_ENV") == "development"

    app.config["DEBUG"] = debug
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-key-change-in-production")
    app.config["ENV"] = os.getenv("FLASK_ENV", "production" if not debug else "development")
    app.config["SESSION_COOKIE_SECURE"] = False  # Allow localhost
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"  # Chrome compatibility

    # Which door is open. Read once, here, rather than per request: an admin
    # whose reachability could change under a running process would be a
    # configuration question with no single answer, and the boot-time refusal
    # below only means anything if this is the value the hook will use.
    remote_host = os.getenv(REMOTE_HOST_VAR, "").strip()
    if remote_host:
        # Normalised once, at boot, so a pasted URL works and an unusable value
        # fails here rather than as a silent 404 on every route.
        remote_host = _configured_hostname(remote_host)
    expected_user = os.getenv(ADMIN_USER_VAR, "").strip() or DEFAULT_ADMIN_USER
    expected_password = os.getenv(ADMIN_PASSWORD_VAR, "")

    if remote_host:
        # Fail closed, in the build log, before a socket is ever opened.
        if not expected_password:
            raise AdminConfigurationError(
                f"{REMOTE_HOST_VAR} is set to {remote_host!r}, which makes this "
                f"admin panel reachable from outside this machine, but "
                f"{ADMIN_PASSWORD_VAR} is not set. The panel has no other "
                f"authentication and a route that rewrites every stored grade, "
                f"so refusing to start is the only safe answer — set "
                f"{ADMIN_PASSWORD_VAR}, or unset {REMOTE_HOST_VAR} to go back "
                f"to loopback-only."
            )
        if len(expected_password) < MIN_ADMIN_PASSWORD_LENGTH:
            raise AdminConfigurationError(
                f"{ADMIN_PASSWORD_VAR} is {len(expected_password)} characters; "
                f"{MIN_ADMIN_PASSWORD_LENGTH} is the minimum when "
                f"{REMOTE_HOST_VAR} is set. Nothing in this package rate-limits "
                f"guesses and {ADMIN_USER_VAR} defaults to "
                f"{DEFAULT_ADMIN_USER!r}, so a short password is the whole "
                f"defence and a brief one. Generate one with: "
                f"python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )
        if app.config["SECRET_KEY"] == DEV_SECRET_KEY:
            raise AdminConfigurationError(
                f"{REMOTE_HOST_VAR} is set to {remote_host!r} but SECRET_KEY is "
                f"still the built-in development value, which is a literal in "
                f"this repository and therefore public. Session cookies signed "
                f"with it can be forged by anyone who has read the source. Set "
                f"SECRET_KEY to a long random string."
            )
        # The deployed panel is served over HTTPS; say so, so the session
        # cookie is not also offered over a plaintext downgrade.
        app.config["SESSION_COOKIE_SECURE"] = True

    # The re-grade (CARD-077) is an operator step: it rewrites every stored
    # grade with no undo, and its own page says to take a snapshot first. That
    # is a thing to do from this machine against a database whose backup you
    # hold, not a button on a panel the internet can reach — so the deployed
    # panel does not offer it. The routes answer 404 (indistinguishable from
    # "no such page", which is the truth for that instance) and the navigation
    # does not mention it. Local mode is unchanged.
    app.config["REGRADE_ENABLED"] = not remote_host

    # Which mode was chosen, said once at boot. The two modes differ only in an
    # environment variable, and choosing the wrong one produces a panel that
    # 404s every route with no explanation — including when the variable is set
    # to whitespace, which is indistinguishable from unset and lands in local
    # mode silently. An operator reading the boot log should not have to infer
    # which door is open from the behaviour of the door.
    if remote_host:
        app.logger.info(
            "admin reachable at %s=%r, behind a credential", REMOTE_HOST_VAR, remote_host
        )
    else:
        app.logger.info(
            "admin in loopback-only mode (%s not set): every request whose Host "
            "is not localhost/127.0.0.1/::1 gets 404, credentials or not",
            REMOTE_HOST_VAR,
        )

    @app.before_request
    def _refuse_what_this_panel_should_not_serve():
        """Exactly one door is open, and the environment chose which (CARD-085).

        **Local mode** (:data:`REMOTE_HOST_VAR` unset) is CARD-081 unchanged:
        the ``Host`` must name this machine, nothing is asked for beyond that,
        and everything else gets a 404 that admits nothing. The bind address is
        the primary defence; this is the one that survives it being widened by
        ``flask run --host=0.0.0.0``, which this module cannot prevent.

        **Deployed mode** replaces that rule rather than adding to it. The
        ``Host`` must equal the configured hostname, the request must carry the
        credential, **and** the browser must not say the request was started by
        another site — and a request claiming ``Host: localhost`` is refused
        like any other stranger.

        The third rule is the one HTTP Basic auth cannot supply on its own: a
        browser replays a cached credential on a cross-site form POST, so
        "carries the password" stopped meaning "the operator asked for this"
        the moment the panel became reachable. It is checked *after* the
        credential, so an anonymous caller still learns exactly one thing —
        401 — and the vocabulary of refusals does not widen for people who have
        not authenticated (:func:`_request_is_cross_site`).

        That last clause is the point of the whole design. Behind a reverse
        proxy, "this request came from this machine" is not something the
        ``Host`` header can establish: the header is written by the caller, and
        the proxy's own address is what ``REMOTE_ADDR`` shows — Render's logs
        report every request as ``127.0.0.1``. Leaving the loopback door open
        in deployed mode would make ``Host: localhost`` a password bypass, so
        the two doors are mutually exclusive by construction and not by
        vigilance.

        Runs before any view, so a refusal never costs a database query.
        """
        host_header = request.headers.get("Host")

        if not remote_host:
            if not _host_is_local(host_header):
                return render_template("404.html"), 404
            return None

        if not _host_is_the_configured_remote(host_header, remote_host):
            # The refusal stays a bare 404 to the caller — that is the whole
            # point of it (CON-016). But the *operator* gets a reason, in the
            # server log they already have open, because otherwise the one
            # refusal designed to be indistinguishable from "no such page" is
            # also the one they have to debug blind.
            app.logger.warning(
                "refused: Host %r does not match %s=%r",
                host_header,
                REMOTE_HOST_VAR,
                remote_host,
            )
            return render_template("404.html"), 404
        if not _credential_is_correct(
            request.authorization, expected_user, expected_password
        ):
            return _ask_for_a_credential()
        if _request_is_cross_site(
            request.method, request.headers, remote_host.strip().lower()
        ):
            return _refuse_cross_site()
        return None

    # Resolve the DB session factory fresh on every create_app() call rather
    # than once at module-import time. DATABASE_URL can differ per call (the
    # test suite relies on this to toggle DB-backed vs. in-memory mode via
    # monkeypatch), and a module-level check would freeze whatever value was
    # in the environment the first time this module happened to be imported.
    session_scope = None
    if os.getenv('DATABASE_URL'):
        try:
            from nonogram.db import session_scope as db_session_scope
            session_scope = db_session_scope
        except Exception:
            # Database not configured; will use in-memory mode
            session_scope = None

    # Add CORS and security headers for Chrome compatibility
    @app.after_request
    def add_headers(response):
        # The wildcard was written for a panel only this machine could reach,
        # where "any origin" meant "this browser". Once REMOTE_HOST_VAR is set
        # it means any origin on the internet, which is a grant with no
        # purpose: nothing outside this panel is supposed to read its pages
        # (CARD-085 review F-006). Browsers already refuse a wildcard on a
        # credentialed cross-origin read, so dropping it closes no working
        # path — it stops advertising one.
        if not remote_host:
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        return response

    # Custom Jinja2 filter for first N characters (avoids slice filter issues)
    app.jinja_env.filters['first_n'] = lambda s, n: str(s)[:n] if s else ''

    # Shares print the same way in the pages and in the batch results
    # (CARD-065): whole percent, rounded down.
    app.jinja_env.filters['percent'] = floor_percent

    # The supported grid range, for form bounds and labels (CARD-063).
    app.jinja_env.globals.update(
        MIN_SIZE=MIN_SIZE,
        MAX_SIZE=MAX_SIZE,
        MAX_PUZZLE_NAME_LENGTH=MAX_PUZZLE_NAME_LENGTH,
    )
    app.jinja_env.filters['strategy_label'] = lambda name: STRATEGY_LABELS.get(name, name)

    # Construct service instances
    # If DATABASE_URL is set, use DB-backed persistence; otherwise use in-memory mode
    if session_scope:
        puzzle_review = PuzzleReviewService(session_factory=session_scope)
        batch_gen = BatchGenerator(puzzle_review_service=puzzle_review, session_factory=session_scope)
        book_mgr = get_book_manager(session_factory=session_scope)
        app.logger.info("Database persistence enabled (DATABASE_URL set)")
    else:
        puzzle_review = PuzzleReviewService(session_factory=None)
        batch_gen = BatchGenerator(puzzle_review_service=puzzle_review, session_factory=None)
        book_mgr = get_book_manager()
        app.logger.info("Running in in-memory mode (DATABASE_URL not set)")

    # Exposed on the app object (rather than left as route closures only) so
    # tests and management scripts can introspect which mode was actually
    # constructed, instead of only being reachable indirectly through a route.
    app.puzzle_review_service = puzzle_review
    app.batch_generator = batch_gen
    app.book_manager = book_mgr

    def _side_range_from_args():
        """``(from, to)`` in cells from ``size_from``/``size_to``, or None."""
        low = request.args.get("size_from", type=int)
        high = request.args.get("size_to", type=int)
        return (low, high) if low is not None or high is not None else None

    def _back_to_puzzles_list():
        """Return to the review list on the page, filters and sort the action
        was taken from (the form posts them as ``return_to``).

        A form on a batch's puzzle list also posts ``return_batch``, and goes
        back there instead. Only a well-formed batch id is honoured, and the
        URL is built by ``url_for``, so neither field can point off the panel.
        """
        query = _list_return_query(request.form.get("return_to"))
        suffix = f"?{query}" if query else ""
        return_batch = (request.form.get("return_batch") or "").strip()
        if return_batch:
            try:
                return_batch = str(uuid.UUID(return_batch))
            except ValueError:
                return_batch = ""
        if return_batch:
            return redirect(url_for("batch_puzzles", batch_id=return_batch) + suffix)
        return redirect(url_for("puzzles_list") + suffix)

    @app.context_processor
    def _navigation():
        """``nav_current(prefix)`` — is the request inside this section?

        The sidebar marks one link ``aria-current="page"`` per request. The
        dashboard is exact-match (every path starts with "/"); the others are
        prefixes, so /book/<id>/select-puzzles still lights "Books".
        """
        path = request.path

        def nav_current(*prefixes):
            for prefix in prefixes:
                if prefix == "/" and path == "/":
                    return True
                if prefix != "/" and (path == prefix or path.startswith(prefix.rstrip("/") + "/")):
                    return True
            return False

        return {
            "nav_current": nav_current,
            "regrade_enabled": app.config.get("REGRADE_ENABLED", True),
        }

    @app.route("/")
    def dashboard():
        """Admin dashboard overview."""
        batch_stats = {
            "total_batches": len(batch_gen.jobs),
            "pending": sum(
                1 for j in batch_gen.jobs.values() if j.status == BatchStatus.PENDING
            ),
            "generating": sum(
                1 for j in batch_gen.jobs.values()
                if j.status == BatchStatus.GENERATING
            ),
            "complete": sum(
                1 for j in batch_gen.jobs.values() if j.status == BatchStatus.COMPLETE
            ),
        }

        puzzle_stats = puzzle_review.get_stats()
        book_stats = {
            "total_books": len(book_mgr.books),
            "draft": len(book_mgr.get_books_by_status(BookStatus.DRAFT.value)),
            "ready_for_pdf": len(
                book_mgr.get_books_by_status(BookStatus.READY_FOR_PDF.value)
            ),
            "published": len(
                book_mgr.get_books_by_status(BookStatus.PUBLISHED.value)
            ),
        }

        return render_template(
            "dashboard.html",
            batch_stats=batch_stats,
            puzzle_stats=puzzle_stats,
            book_stats=book_stats,
        )

    @app.route("/batch/create", methods=["GET", "POST"])
    def create_batch():
        """Create a new batch generation job."""
        if request.method == "POST":
            try:
                # 20, not 100: a default has to be a number that works at
                # every supported extent, and 100 at 30x30 costs about 390s
                # against a server that waits 120 (CARD-088).
                count = int(request.form.get("count", DEFAULT_BATCH_COUNT))
                sizes = [int(s) for s in request.form.get("sizes", "20").split(",")]
                theme = request.form.get("theme", "christmas")
                source = request.form.get("source", "random")
                quality_filter = int(request.form.get("quality_filter", 0))

                batch_id = batch_gen.create_batch(
                    count=count,
                    sizes=sizes,
                    theme=theme,
                    source=source,
                    quality_filter=quality_filter,
                )

                flash(f"Batch created: {batch_id}", "success")
                return redirect(url_for("batch_status", batch_id=batch_id))

            except ValueError as e:
                flash(f"Error: {str(e)}", "error")

        return _render_batch_step_one()

    def _render_batch_step_one():
        """Step 1 of the batch flow, aware of what is already loaded.

        The image manager keeps the uploaded set until generation finishes,
        so "back" from step 2 or 3 lands here with pictures still loaded. The
        page used to render a blank upload form regardless, which read as
        "your pictures are gone" and pushed the owner into re-uploading
        (which really does discard them: from-images clears first). It now
        shows the loaded set with a way forward and a way to start over, and
        the form remembers the size and quality the set was uploaded with.
        """
        image_mgr = get_image_manager()
        return render_template(
            "batch_create.html",
            loaded_images=image_mgr.get_all_images(),
            default_size=session.get("batch_default_size", "medium"),
            quality_filter=session.get("batch_quality_filter", 25),
        )

    @app.route("/batch/clear-images", methods=["POST"])
    def batch_clear_images():
        """Discard the loaded pictures and start the batch flow over."""
        get_image_manager().clear_all()
        session.pop("batch_quality_filter", None)
        session.pop("batch_default_size", None)
        flash("Loaded pictures discarded", "info")
        return redirect(url_for("batch_select_images"))

    @app.route("/batch/from-images", methods=["POST"])
    def batch_from_images():
        """Handle image uploads from both individual files and directories."""
        try:
            # Get uploaded files from both sources
            individual_files = request.files.getlist("image_files") or []
            directory_files = request.files.getlist("directory") or []
            all_files = individual_files + directory_files
            quality_filter = int(request.form.get("quality_filter", 0))

            # Clear previous batch
            image_mgr = get_image_manager()
            image_mgr.clear_all()

            if not all_files or not any(f.filename for f in all_files):
                flash("No images selected", "error")
                return redirect(url_for("batch_select_images"))

            # Valid image extensions
            valid_extensions = {'.png', '.jpg', '.jpeg', '.gif'}

            # Process uploaded files
            processed_count = 0
            for file in all_files:
                if file and file.filename:
                    # Skip directories and invalid file types
                    file_ext = Path(file.filename).suffix.lower()
                    if not file_ext or file_ext not in valid_extensions:
                        continue

                    try:
                        # Save to persistent uploads directory (not system temp)
                        uploads_dir = Path(tempfile.gettempdir()) / "nonogram_uploads"
                        uploads_dir.mkdir(exist_ok=True)

                        # Extract just the filename (remove any directory path from directory uploads)
                        # When uploading a directory, file.filename includes the path like "birds/raven1.jpg"
                        # We want just "raven1.jpg" to avoid creating nested directories
                        just_filename = Path(file.filename).name
                        safe_filename = just_filename.replace(" ", "_")
                        temp_path = uploads_dir / f"{uuid.uuid4().hex}_{safe_filename}"
                        file.save(str(temp_path))

                        # Add to image manager
                        image = image_mgr.add_image(str(temp_path), file.filename)
                        if image:
                            processed_count += 1
                        else:
                            flash(f"Could not process {file.filename}", "warning")

                    except Exception as e:
                        flash(f"Error processing {file.filename}: {str(e)}", "warning")

            if processed_count == 0:
                flash("No valid images to process", "error")
                return redirect(url_for("batch_select_images"))

            # Read default size from page 1 selection and apply to all images
            default_size = request.form.get("default_size", "medium")
            size_mapping = SIZE_PRESETS

            if default_size in size_mapping:
                size_value, size_mode = size_mapping[default_size]
                # Apply to all loaded images
                for image in image_mgr.get_all_images():
                    if size_mode == "max":
                        image_mgr.update_image_size(image.file_id, "max", 0)
                    else:
                        image_mgr.update_image_size(image.file_id, size_mode, size_value)

            # Store quality filter and default size in session
            session["batch_quality_filter"] = quality_filter
            session["batch_default_size"] = default_size

            flash(f"Loaded {processed_count} image(s) from selected files/folder(s)", "success")
            return redirect(url_for("preview_batch_images"))

        except Exception as e:
            flash(f"Error: {str(e)}", "error")
            return redirect(url_for("batch_select_images"))

    @app.route("/batch/select-images", methods=["GET", "POST"])
    def batch_select_images():
        """Select images for batch generation (Wave 3 workflow)."""
        return _render_batch_step_one()

    @app.route("/batch/preview-images", methods=["GET", "POST"])
    def preview_batch_images():
        """Preview and configure sizes for selected images."""
        image_mgr = get_image_manager()
        images = image_mgr.get_all_images()

        if not images:
            flash("No pictures are loaded — upload some to start a batch.", "error")
            return redirect(url_for("batch_select_images"))

        if request.method == "POST":
            try:
                # Validate image count before processing
                if len(images) < 1 or len(images) > 200:
                    flash(f"❌ Invalid image count: {len(images)}. Must be 1-200 images.", "error")
                    return render_template(
                        "image_preview.html",
                        images=images,
                        total_size_mb=image_mgr.get_total_size_mb(),
                    )

                # Update configuration for each image
                for image in images:
                    file_id = image.file_id
                    mode = request.form.get(f"mode_{file_id}", "fixed")
                    value = int(request.form.get(f"value_{file_id}", 20))
                    name = request.form.get(f"name_{file_id}", image.puzzle_name)

                    # Update image configuration
                    image_mgr.update_image_size(file_id, mode, value)
                    image_mgr.update_image_name(file_id, name)

                flash("Configuration saved", "success")
                return redirect(url_for("generate_batch_puzzles"))  # GET to show confirmation

            except ValueError as e:
                flash(f"Configuration error: {str(e)}", "error")
                return render_template(
                    "image_preview.html",
                    images=images,
                    total_size_mb=image_mgr.get_total_size_mb(),
                )

        # Get stats for display
        total_size_mb = image_mgr.get_total_size_mb()

        return render_template(
            "image_preview.html",
            images=images,
            total_size_mb=total_size_mb,
        )

    @app.route("/batch/generate-puzzles", methods=["GET", "POST"])
    def generate_batch_puzzles():
        """Generate puzzles from configured images (actual E2E conversion)."""
        image_mgr = get_image_manager()
        images = image_mgr.get_all_images()

        if not images:
            # Also where the browser's Back button lands after a batch has
            # finished: the set is cleared on generation, on purpose.
            flash("No pictures are loaded — the last batch has finished, or none were uploaded. Start a new batch.", "error")
            return redirect(url_for("batch_select_images"))

        # GET: Show confirmation page
        if request.method == "GET":
            return render_template(
                "generate_batch.html",
                images=images,
            )

        # POST: Actually generate puzzles
        try:
            # Extract configured sizes from images (unique values)
            sizes = list(set(img.size_value if img.size_mode in ("fixed", "short") else 20 for img in images))

            # Create batch job
            batch_id = batch_gen.create_batch(
                count=len(images),
                sizes=sorted(sizes),
                theme="image",
                source="images",  # Use "images" not "image"
                quality_filter=session.get("batch_quality_filter", 0),
            )

            # Process each image and generate puzzles
            # Use the DB-backed puzzle_review service created in create_app(), not the legacy one
            quality_filter = session.get("batch_quality_filter", 0)
            generated_count = 0
            errors = []
            adjustments = []
            skipped = []
            moved = []

            for image in images:
                try:
                    # CARD-064: a picture even Large would cut below
                    # MIN_KEPT_SHARE is never generated; it is reported.
                    fit = image.size_fit()
                    if fit.status == CANNOT_FIT:
                        skipped.append(
                            f"{image.original_filename} skipped: too elongated for any "
                            f"supported size (even Large keeps only {floor_percent(fit.kept)})"
                        )
                        continue
                    width, height = fit.extent

                    # Convert image to puzzle through the canonical,
                    # solver-verified pipeline (CARD-049) — the same
                    # judge_candidate uniqueness check and bounded pixel-nudge
                    # recovery `nonogram generate --mode image` runs, instead
                    # of a grid nothing ever solver-checks. One call per
                    # extent tried: orchestrator.generate_batch() has no
                    # per-item image-path parameter.
                    puzzle, used = _generate_image_puzzle(image, width, height)

                    # CARD-050 (AC-1): a real measurement against the source
                    # picture this puzzle was converted from, replacing the
                    # output-grid-density-only heuristic and the hardcoded
                    # "medium" recognizability that used to live here (and
                    # still live in image_to_puzzle.create_puzzle_from_image,
                    # which is preview-only in this pipeline — see CARD-049).
                    # Puzzle.grid is already the ADR-0012 boundary type
                    # (list[list[bool]]) measure_quality expects; the source
                    # image is re-opened from the same file path the
                    # GenerationRequest above was given.
                    original_image = PILImage.open(image.file_path)
                    quality_metrics = measure_quality(original_image, puzzle.grid)
                    quality_score = quality_metrics.quality_score
                    recognizability = quality_metrics.recognizability.value

                    # Check quality filter
                    if quality_score < quality_filter:
                        continue

                    # Store puzzle — difficulty_score/difficulty_tier come
                    # from nonogram.difficulty.score_difficulty via the real
                    # SolverSignals orchestrator.generate() computed, not from
                    # grid size alone (AC-3).
                    # CARD-080: the store refuses a grid the solver will not
                    # certify. Reaching it is a bug — this candidate came from
                    # orchestrator.generate, which enforces INV-002 — so it is
                    # reported to the owner in the results list rather than
                    # silently dropped, and this picture is skipped instead of
                    # failing the whole upload.
                    try:
                        puzzle_id = puzzle_review.add_puzzle(
                            grid=puzzle.grid,
                            clues_rows=puzzle.clues.rows,
                            clues_cols=puzzle.clues.columns,
                            width=puzzle.width,
                            height=puzzle.height,
                            theme="image",
                            difficulty_score=puzzle.difficulty_score,
                            difficulty_tier=puzzle.difficulty_tier,
                            quality_score=quality_score,
                            recognizability=recognizability,
                            strategies_used=[],
                            batch_id=batch_id,
                            source_image=image.original_filename,
                        )
                    except NotUniquelySolvable as exc:
                        app.logger.error(
                            "%s: the store refused a generated puzzle — this "
                            "should be unreachable (INV-002)",
                            image.original_filename,
                            exc_info=True,
                        )
                        errors.append(
                            f"{image.original_filename}: not stored — {exc}"
                        )
                        continue

                    generated_count += 1
                    if fit.status == MOVED_TO_LARGE:
                        # CARD-064 (G-2): the chosen size was not used — say
                        # so in the results too, not only in the preview.
                        reason = (
                            f"the chosen size {fit.chosen[0]}x{fit.chosen[1]} would "
                            f"cut it (keeps {floor_percent(fit.chosen_kept)})"
                            if fit.chosen is not None
                            else "the chosen size can't keep its shape"
                        )
                        moved.append(f"{image.original_filename}: moved up to Large — {reason}")
                    if used != (width, height):
                        note = (
                            f"{image.original_filename}: generated at "
                            f"{used[0]}x{used[1]} — {width}x{height} had no "
                            f"unique solution"
                        )
                        # A ±1 retry (CARD-062) can land under MIN_KEPT_SHARE;
                        # it is kept, but never silently.
                        if not image.keeps_enough(used):
                            note += (
                                f"; it keeps {floor_percent(image.kept_share(used))} "
                                f"of the picture"
                            )
                        adjustments.append(note)

                except NonogramError as e:
                    # E.g. GenerationAbandoned: the conversion (and every
                    # bounded pixel-nudge attempt) never came out uniquely
                    # solvable, at the predicted extent or either long-side
                    # neighbour (CARD-062). Record it and keep processing the rest of the
                    # batch (AC-2) instead of failing the whole request.
                    errors.append(f"Error processing {image.original_filename}: {str(e)}")
                except Exception as e:
                    errors.append(f"Error processing {image.original_filename}: {str(e)}")

            # Update batch with final puzzle count
            batch_gen._update_batch_status(batch_id, puzzle_count=generated_count)

            # Show results
            if generated_count > 0:
                flash(f"✅ Generated {generated_count} puzzle(s) from {len(images)} image(s)", "success")
            else:
                flash("No valid puzzles generated", "warning")

            for note in moved[:3]:
                flash(note, "info")
            if len(moved) > 3:
                flash(f"... and {len(moved) - 3} more pictures moved up to Large", "info")

            for adjustment in adjustments[:3]:
                flash(adjustment, "info")
            if len(adjustments) > 3:
                flash(f"... and {len(adjustments) - 3} more size adjustments", "info")

            for note in skipped[:3]:
                flash(note, "info")
            if len(skipped) > 3:
                flash(f"... and {len(skipped) - 3} more skipped pictures", "info")

            if errors:
                for error in errors[:3]:  # Show first 3 errors
                    flash(error, "info")
                if len(errors) > 3:
                    flash(f"... and {len(errors) - 3} more errors", "info")

            # Clear session and image manager
            session.pop("batch_quality_filter", None)
            session.pop("batch_default_size", None)
            image_mgr.clear_all()  # Clear images so next workflow starts fresh

            return redirect(url_for("generated_puzzles", batch_id=batch_id))

        except ValueError as e:
            # Handle validation errors with helpful message
            error_msg = str(e)
            if "must be" in error_msg.lower():
                flash(f"❌ {error_msg}", "error")
            else:
                flash(f"❌ Generation failed: {error_msg}", "error")
            return render_template(
                "generate_batch.html",
                images=images,
            )
        except Exception as e:
            flash(f"❌ Unexpected error: {str(e)}", "error")
            return render_template(
                "generate_batch.html",
                images=images,
            )

    @app.route("/batch/<batch_id>/generated-puzzles")
    def generated_puzzles(batch_id):
        """Display generated puzzles with SVG grids."""
        # Get puzzles for this batch using batch_generator
        puzzles = batch_gen.get_batch_puzzles(batch_id, offset=0, limit=100)

        if not puzzles:
            flash("No puzzles generated for this batch", "warning")
            return redirect(url_for("batch_status", batch_id=batch_id))

        # Keyed by id rather than written onto the dicts: in-memory mode hands
        # back the stored dicts themselves.
        strategies = {p["id"]: puzzle_review.strategies_for(p) for p in puzzles}

        # Get batch job info for total image count
        batch_job = batch_gen.get_batch_status(batch_id)
        total_images = batch_job.total_count if batch_job else len(puzzles)
        filtered_count = total_images - len(puzzles) if batch_job else 0

        return render_template(
            "generated_puzzles.html",
            batch_id=batch_id,
            puzzles=puzzles,
            strategies=strategies,
            total_images=total_images,
            filtered_count=filtered_count,
        )

    @app.route("/batch/<batch_id>/approve-all", methods=["POST"])
    def approve_batch_puzzles(batch_id):
        """Approve every puzzle of a batch that is not already in a book."""
        if not batch_gen.get_batch_status(batch_id):
            flash("Batch not found", "error")
            return redirect(url_for("dashboard"))
        count = puzzle_review.set_batch_status(batch_id, PuzzleStatus.APPROVED)
        flash(f"Approved {count} puzzle(s)", "success")
        return redirect(url_for("generated_puzzles", batch_id=batch_id))

    @app.route("/batch/<batch_id>/reject-all", methods=["POST"])
    def reject_batch_puzzles(batch_id):
        """Reject every puzzle of a batch that is not already in a book."""
        if not batch_gen.get_batch_status(batch_id):
            flash("Batch not found", "error")
            return redirect(url_for("dashboard"))
        count = puzzle_review.set_batch_status(batch_id, PuzzleStatus.REJECTED)
        flash(f"Rejected {count} puzzle(s)", "success")
        return redirect(url_for("generated_puzzles", batch_id=batch_id))

    @app.route("/batch/<batch_id>/delete-rejected", methods=["POST"])
    def delete_rejected_batch_puzzles(batch_id):
        """Delete every rejected puzzle of a batch that is not in a book."""
        if not batch_gen.get_batch_status(batch_id):
            flash("Batch not found", "error")
            return redirect(url_for("dashboard"))
        count = puzzle_review.delete_rejected_in_batch(batch_id)
        flash(f"Deleted {count} rejected puzzle(s)", "success")
        return redirect(url_for("generated_puzzles", batch_id=batch_id))

    @app.route("/batch/<batch_id>")
    def batch_status(batch_id):
        """View batch status and puzzles."""
        job = batch_gen.get_batch_status(batch_id)
        if not job:
            flash("Batch not found", "error")
            return redirect(url_for("dashboard"))

        puzzles = batch_gen.get_batch_puzzles(batch_id, offset=0, limit=50)

        return render_template(
            "batch_status.html",
            batch_id=batch_id,
            job=job,
            puzzles=puzzles or [],
        )

    @app.route("/puzzles")
    def puzzles_list():
        """List and filter puzzles."""
        # Basic filters. ``size`` is the exact-extent filter the API keeps;
        # the page's own fields are the side range (either side, from/to).
        size = request.args.get("size", type=int)
        side_range = _side_range_from_args()
        difficulty = request.args.get("difficulty")
        quality_min = request.args.get("quality_min", type=int)

        # New filters
        date_from = request.args.get("date_from")
        date_to = request.args.get("date_to")
        book_id = request.args.get("book_id")
        puzzle_name = request.args.get("puzzle_name")
        sort_by = request.args.get("sort_by", "batch_id,-size,quality")

        # Status (CARD-066). An unknown value is reported and then ignored:
        # filtering on it would show an empty list that looks like "nothing
        # matches your other filters".
        status = request.args.get("status") or None
        if status and status not in _PUZZLE_STATUSES:
            flash(f"Unknown status {status!r} — showing every status instead", "info")
            status = None

        # Pagination
        limit = request.args.get("limit", 25, type=int)
        offset = request.args.get("offset", 0, type=int)

        # Get available books for filter dropdown
        books = book_mgr.get_all_books()

        try:
            filter_opts = PuzzleFilter(
                size=(size, size) if size is not None else None,
                side_range=side_range,
                difficulty=difficulty,
                quality_min=quality_min,
                date_from=date_from,
                date_to=date_to,
                book_id=book_id,
                puzzle_name=puzzle_name,
                status=status,
                sort_by=sort_by,
                limit=limit,
                offset=offset,
            )
            result = puzzle_review.filter_puzzles(filter_opts)

            # An action can empty the page it was taken on (the last draft on
            # the last page of ?status=draft is approved): show the new last
            # page, keeping every filter, rather than "no puzzles found".
            if not result.puzzles and result.total_count and offset > 0:
                last_offset = _page_window(result.total_count, result.limit, 0)["last_offset"]
                args = request.args.to_dict()
                args["offset"] = str(last_offset)
                return redirect(url_for("puzzles_list", **args))

            return render_template(
                "puzzles_list.html",
                puzzles=result.puzzles,
                total_count=result.total_count,
                offset=result.offset,
                limit=result.limit,
                has_more=result.has_more,
                pagination=_page_window(result.total_count, result.limit, result.offset),
                books=books,
                statuses=_PUZZLE_STATUSES,
            )

        except ValueError as e:
            flash(f"Filter error: {str(e)}", "error")
            return render_template(
                "puzzles_list.html",
                puzzles=[],
                error=str(e),
                books=books,
                statuses=_PUZZLE_STATUSES,
            )

    @app.route("/puzzle/<puzzle_id>/rename", methods=["POST"])
    def rename_puzzle(puzzle_id):
        """Give a puzzle a new display name; blank clears it."""
        try:
            if puzzle_review.rename_puzzle(puzzle_id, request.form.get("puzzle_name")):
                flash("Puzzle renamed", "success")
            else:
                flash("Puzzle not found", "error")
        except ValueError as e:
            flash(f"Error: {str(e)}", "error")
        return _back_to_puzzles_list()

    @app.route("/batches")
    def batches_list():
        """Every batch, newest first, optionally within a from/to date range."""
        date_from = request.args.get("date_from") or None
        date_to = request.args.get("date_to") or None
        try:
            batches = batch_gen.list_batches(date_from=date_from, date_to=date_to)
        except ValueError as e:
            flash(f"Filter error: {str(e)}", "error")
            batches = []
        summaries = puzzle_review.batch_summaries([job.batch_id for job in batches])
        return render_template(
            "batches_list.html",
            batches=batches,
            summaries=summaries,
        )

    @app.route("/batches/<batch_id>")
    def batch_puzzles(batch_id):
        """One batch's puzzles: the review list's table, without its filters."""
        try:
            batch_id = str(uuid.UUID(batch_id))
        except ValueError:
            abort(404)
        job = batch_gen.get_batch_status(batch_id)
        if not job:
            abort(404)

        sort_by = request.args.get("sort_by", "batch_id,-size,quality")
        limit = request.args.get("limit", 25, type=int)
        offset = request.args.get("offset", 0, type=int)
        try:
            result = puzzle_review.filter_puzzles(
                PuzzleFilter(batch_id=batch_id, sort_by=sort_by, limit=limit, offset=offset)
            )
        except ValueError as e:
            flash(f"Error: {str(e)}", "error")
            return redirect(url_for("batch_puzzles", batch_id=batch_id))

        # Same as the review list: an action that empties the last page lands
        # on the new last page.
        if not result.puzzles and result.total_count and offset > 0:
            args = request.args.to_dict()
            args["offset"] = str(_page_window(result.total_count, result.limit, 0)["last_offset"])
            return redirect(url_for("batch_puzzles", batch_id=batch_id, **args))

        return render_template(
            "batch_puzzles.html",
            job=job,
            summary=puzzle_review.batch_summaries([batch_id])[batch_id],
            puzzles=result.puzzles,
            total_count=result.total_count,
            pagination=_page_window(result.total_count, result.limit, result.offset),
        )

    @app.route("/puzzle/<puzzle_id>/approve", methods=["POST"])
    def approve_puzzle(puzzle_id):
        """Approve a puzzle."""
        batch_id = request.args.get("batch_id")
        if puzzle_review.approve_puzzle(puzzle_id):
            flash(f"Puzzle {puzzle_id} approved", "success")
        else:
            flash(f"Puzzle not found", "error")

        # Return to batch if batch_id provided, else global puzzles list
        if batch_id:
            return redirect(url_for("generated_puzzles", batch_id=batch_id))
        return _back_to_puzzles_list()

    @app.route("/puzzle/<puzzle_id>/reject", methods=["POST"])
    def reject_puzzle(puzzle_id):
        """Reject a puzzle."""
        batch_id = request.args.get("batch_id")
        if puzzle_review.reject_puzzle(puzzle_id):
            flash(f"Puzzle {puzzle_id} rejected", "success")
        else:
            flash(f"Puzzle not found", "error")

        # Return to batch if batch_id provided, else global puzzles list
        if batch_id:
            return redirect(url_for("generated_puzzles", batch_id=batch_id))
        return _back_to_puzzles_list()

    @app.route("/books")
    def books_list():
        """List all books."""
        books = book_mgr.get_all_books()
        return render_template("books_list.html", books=books)

    @app.route("/book/create", methods=["GET", "POST"])
    def create_book():
        """Create a new book."""
        if request.method == "POST":
            try:
                title = request.form.get("title")
                description = request.form.get("description")
                theme = request.form.get("theme", "christmas")
                target_audience = request.form.get("target_audience")

                book_id = book_mgr.create_book(
                    title=title,
                    description=description,
                    theme=theme,
                    target_audience=target_audience,
                )

                flash(f"Book created: {book_id}", "success")
                return redirect(url_for("setup_print", book_id=book_id))

            except ValueError as e:
                flash(f"Error: {str(e)}", "error")

        return render_template("book_create.html")

    @app.route("/book/<book_id>/setup-print", methods=["GET", "POST"])
    def setup_print(book_id):
        """Configure print specifications for a book (Step 1 of scaffolding)."""
        book = book_mgr.get_book(book_id)
        if not book:
            flash("Book not found", "error")
            return redirect(url_for("books_list"))

        if request.method == "POST":
            try:
                # Get form data
                unit = request.form.get("unit", "cm")
                width_input = request.form.get("width")
                height_input = request.form.get("height")

                session["unit_preference"] = unit  # Persist unit preference in session

                # Convert to cm if input was in inches
                if unit == "inches":
                    width_cm = PrintSpecValidator.inches_to_cm(width_input)
                    height_cm = PrintSpecValidator.inches_to_cm(height_input)
                else:
                    width_cm = width_input
                    height_cm = height_input

                # Validate and create spec
                spec, error = PrintSpecValidator.create_spec(
                    width_cm=width_cm,
                    height_cm=height_cm,
                )

                if error:
                    flash(f"Error: {error}", "error")
                else:
                    # Store in book metadata (for now, using the in-memory manager)
                    # In production, this would update the Book row in the database
                    book.metadata.size = f"{spec.trim_width_cm}×{spec.trim_height_cm} cm"
                    book.updated_at = datetime.utcnow()

                    flash(f"Print specs set: {spec.trim_width_cm} × {spec.trim_height_cm} cm", "success")
                    # Proceed to Step 2: Puzzle Selection
                    return redirect(url_for("select_puzzles_for_book", book_id=book_id))

            except ValueError as e:
                flash(f"Error: {str(e)}", "error")

        # Prepare default trim size
        default_width = "15.24"
        default_height = "22.86"
        unit_preference = session.get("unit_preference", "cm")

        # Convert defaults to inches if that's the preference
        if unit_preference == "inches":
            default_width = PrintSpecValidator.cm_to_inches(default_width)
            default_height = PrintSpecValidator.cm_to_inches(default_height)

        context = {
            "book": book,
            "default_width": default_width,
            "default_height": default_height,
            "unit_preference": unit_preference,
        }

        return render_template("book_setup_print.html", **context)

    @app.route("/book/<book_id>/select-puzzles", methods=["GET", "POST"])
    def select_puzzles_for_book(book_id):
        """Select and add puzzles to a book (Step 2 of scaffolding)."""
        book = book_mgr.get_book(book_id)
        if not book:
            flash("Book not found", "error")
            return redirect(url_for("books_list"))

        if request.method == "POST":
            # Get selected puzzle IDs from form
            selected_ids = request.form.getlist("puzzle_ids")

            if not selected_ids:
                flash("No puzzles selected. Please select at least one puzzle.", "info")
            else:
                try:
                    # Add puzzles to the book
                    if book_mgr.add_puzzles_to_book(book_id, selected_ids):
                        flash(f"Added {len(selected_ids)} puzzle(s) to book", "success")
                        # Proceed to Step 3: Puzzle Arrangement
                        return redirect(url_for("arrange_puzzles_in_book", book_id=book_id))
                    else:
                        flash("Book not found", "error")
                except ValueError as e:
                    flash(f"Error: {str(e)}", "error")

        # Get filter parameters from query string
        size = request.args.get("size", type=int)
        side_range = _side_range_from_args()
        difficulty = request.args.get("difficulty")
        quality_min = request.args.get("quality_min", type=int)
        theme = request.args.get("theme")
        status = request.args.get("status", "approved")  # Default to approved only
        puzzle_name = request.args.get("puzzle_name")
        limit = request.args.get("limit", 50, type=int)
        offset = request.args.get("offset", 0, type=int)

        # Build filter: exclude puzzles already in this book
        try:
            filter_opts = PuzzleFilter(
                size=(size, size) if size is not None else None,
                side_range=side_range,
                difficulty=difficulty,
                quality_min=quality_min,
                theme=theme,
                status=status,
                puzzle_name=puzzle_name,
                book_id="unassigned",  # Only show puzzles NOT in any book
                limit=limit,
                offset=offset,
            )
            result = puzzle_review.filter_puzzles(filter_opts)

            # Additional filter: exclude puzzles already in this book
            filtered_puzzles = [
                p for p in result.puzzles
                if p.get("book_id") is None
            ]

            context = {
                "book": book,
                "puzzles": filtered_puzzles,
                "total_count": len(filtered_puzzles),
                "has_more": result.has_more,
                "size": size,
                "size_from": side_range[0] if side_range else None,
                "size_to": side_range[1] if side_range else None,
                "difficulty": difficulty,
                "quality_min": quality_min,
                "theme": theme,
                "status": status,
                "puzzle_name": puzzle_name,
                "limit": limit,
                "offset": offset,
            }

            return render_template("book_select_puzzles.html", **context)

        except ValueError as e:
            flash(f"Filter error: {str(e)}", "error")
            return render_template(
                "book_select_puzzles.html",
                book=book,
                puzzles=[],
                total_count=0,
                has_more=False,
                error=str(e),
            )

    @app.route("/book/<book_id>/arrange-puzzles", methods=["GET", "POST"])
    def arrange_puzzles_in_book(book_id):
        """Arrange and name puzzles in a book (Step 3 of scaffolding)."""
        book = book_mgr.get_book(book_id)
        if not book:
            flash("Book not found", "error")
            return redirect(url_for("books_list"))

        # Handle puzzle reordering and title updates via AJAX or form submission
        if request.method == "POST":
            action = request.form.get("action")

            try:
                if action == "move_up":
                    puzzle_id = request.form.get("puzzle_id")
                    book_mgr.move_puzzle_up(book_id, puzzle_id)
                    flash(f"Moved puzzle up", "success")

                elif action == "move_down":
                    puzzle_id = request.form.get("puzzle_id")
                    book_mgr.move_puzzle_down(book_id, puzzle_id)
                    flash(f"Moved puzzle down", "success")

                elif action == "set_title":
                    puzzle_id = request.form.get("puzzle_id")
                    title = request.form.get("title")
                    book_mgr.set_puzzle_title(book_id, puzzle_id, title)
                    flash(f"Updated puzzle title", "success")

                elif action == "delete":
                    puzzle_id = request.form.get("puzzle_id")
                    book_mgr.remove_puzzle_from_book(book_id, puzzle_id)
                    flash(f"Removed puzzle from book", "success")

                elif action == "finish":
                    # Proceed to Step 4: Finalization
                    return redirect(url_for("finalize_book", book_id=book_id))

            except ValueError as e:
                flash(f"Error: {str(e)}", "error")

        # Get puzzles in current order with titles
        puzzles_in_book = []
        for order_num, puzzle_id in enumerate(book.puzzle_ids, start=1):
            # Get puzzle details from puzzle_review service
            puzzle = puzzle_review.get_puzzle(puzzle_id)
            if puzzle:
                # Add custom title if set
                custom_title = book_mgr.get_puzzle_title(book_id, puzzle_id)
                puzzle["order"] = order_num
                puzzle["custom_title"] = custom_title
                puzzles_in_book.append(puzzle)

        # Calculate estimated page count
        # Rough estimate: assume each puzzle is ~1-2 pages based on height
        # Later refinement in Step 4 based on actual trim height
        page_count = max(1, len(puzzles_in_book))  # Minimum 1 page per puzzle

        context = {
            "book": book,
            "puzzles": puzzles_in_book,
            "page_count": page_count,
            "puzzle_count": len(puzzles_in_book),
        }

        return render_template("book_arrange_puzzles.html", **context)

    @app.route("/book/<book_id>/finalize", methods=["GET", "POST"])
    def finalize_book(book_id):
        """Finalize book with cover, guide, and download (Step 4 of scaffolding)."""
        book = book_mgr.get_book(book_id)
        if not book:
            flash("Book not found", "error")
            return redirect(url_for("books_list"))

        if request.method == "POST":
            action = request.form.get("action")

            try:
                if action == "clear_cover":
                    # Clear cover image (stored in session)
                    session.pop(f"book_{book_id}_cover_path", None)
                    flash("Cover image cleared", "success")

                elif action == "save_and_finish":
                    # Mark book as ready and return to books list
                    book_mgr.set_book_status(book_id, BookStatus.READY_FOR_PDF.value)
                    flash(f"Book saved: {book.metadata.title}", "success")
                    return redirect(url_for("books_list"))

                elif action == "download_pdf":
                    # Generate and download PDF
                    return generate_book_pdf_download(book, puzzle_review)

            except Exception as e:
                flash(f"Error: {str(e)}", "error")

        # Handle cover upload
        cover_image = None
        cover_path = session.get(f"book_{book_id}_cover_path")

        if "cover" in request.files:
            file = request.files["cover"]
            if file and file.filename:
                try:
                    from PIL import Image as PILImage
                    cover_image = PILImage.open(file.stream)
                    # Store filename in session (Pillow Image can't be serialized)
                    session[f"book_{book_id}_cover_path"] = file.filename
                    session[f"book_{book_id}_cover_data"] = True  # Flag it exists
                    flash("Cover image uploaded", "success")
                except Exception as e:
                    flash(f"Failed to load image: {str(e)}", "error")

        # Get puzzles in order
        puzzles_in_book = []
        for puzzle_id in book.puzzle_ids:
            puzzle = puzzle_review.get_puzzle(puzzle_id)
            if puzzle:
                custom_title = book_mgr.get_puzzle_title(book_id, puzzle_id)
                puzzle["custom_title"] = custom_title
                puzzles_in_book.append(puzzle)

        # Calculate difficulty breakdown — the same function the PDF guide
        # page uses, so the screen and the printed book cannot disagree.
        tier_counts = tier_breakdown(puzzles_in_book)
        easy_count = tier_counts[Tier.EASY]
        medium_count = tier_counts[Tier.MEDIUM]
        hard_count = tier_counts[Tier.HARD]
        guess_count = tier_counts[Tier.GUESS]

        context = {
            "book": book,
            "puzzles": puzzles_in_book,
            "puzzle_count": len(puzzles_in_book),
            "easy_count": easy_count,
            "medium_count": medium_count,
            "hard_count": hard_count,
            "guess_count": guess_count,
            "page_count": max(1, len(puzzles_in_book) + 2),  # Cover + guide + puzzles
            "cover_uploaded": bool(session.get(f"book_{book_id}_cover_data")),
            "trim_width_cm": book.metadata.size.split("×")[0] if book.metadata.size else "15.24",
            "trim_height_cm": book.metadata.size.split("×")[1] if book.metadata.size and "×" in book.metadata.size else "22.86",
        }

        return render_template("book_finalize.html", **context)

    def generate_book_pdf_download(book, puzzle_review):
        """Generate PDF and return as download response."""
        from io import BytesIO
        from werkzeug.wsgi import wrap_file

        try:
            # Get puzzles
            puzzles = []
            app.logger.debug(
                "Book '%s' has %d puzzle IDs: %s",
                book.metadata.title, len(book.puzzle_ids), book.puzzle_ids,
            )

            for puzzle_id in book.puzzle_ids:
                puzzle = puzzle_review.get_puzzle(puzzle_id)
                if puzzle:
                    app.logger.debug("Retrieved puzzle %s", puzzle_id)
                    puzzles.append(puzzle)
                else:
                    app.logger.warning("Could not find puzzle %s for PDF generation", puzzle_id)

            app.logger.debug(
                "Total puzzles retrieved: %d/%d", len(puzzles), len(book.puzzle_ids)
            )

            # Generate PDF
            pdf_generator = BookPDFGenerator()
            pdf_bytes = pdf_generator.generate_book_pdf(
                puzzles=puzzles,
                book_title=book.metadata.title,
                trim_width_cm=None,  # Could extract from book.metadata.size
                trim_height_cm=None,
            )
            app.logger.debug("PDF generated successfully, size: %d bytes", len(pdf_bytes.getvalue()))

            # Create response
            pdf_bytes.seek(0)
            timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
            filename = f"book_{timestamp}.pdf"

            return send_file(
                pdf_bytes,
                mimetype="application/pdf",
                as_attachment=True,
                download_name=filename,
            )

        except Exception as e:
            flash(f"Failed to generate PDF: {str(e)}", "error")
            return redirect(request.referrer or url_for("book_detail", book_id=book.book_id))

    @app.route("/book/<book_id>/download-pdf", methods=["POST"])
    def download_book_pdf(book_id):
        """Download book as PDF (from books list)."""
        book = book_mgr.get_book(book_id)
        if not book:
            flash("Book not found", "error")
            return redirect(url_for("books_list"))

        return generate_book_pdf_download(book, puzzle_review)

    @app.route("/book/<book_id>/delete", methods=["POST"])
    def delete_book(book_id):
        """Delete a draft book."""
        book = book_mgr.get_book(book_id)
        if not book:
            flash("Book not found", "error")
            return redirect(url_for("books_list"))

        # Only allow deleting draft books
        if book.status != BookStatus.DRAFT.value:
            flash(f"Cannot delete {book.status} book. Only draft books can be deleted.", "error")
            return redirect(url_for("books_list"))

        try:
            book_mgr.delete_book(book_id)
            flash(f"Deleted book: {book.metadata.title}", "success")
        except Exception as e:
            flash(f"Failed to delete book: {str(e)}", "error")

        return redirect(url_for("books_list"))

    @app.route("/book/<book_id>")
    def book_detail(book_id):
        """View and edit book details."""
        book = book_mgr.get_book(book_id)
        if not book:
            flash("Book not found", "error")
            return redirect(url_for("books_list"))

        return render_template("book_detail.html", book=book)

    @app.route("/book/<book_id>/add-puzzles", methods=["POST"])
    def add_puzzles_to_book(book_id):
        """Add puzzles to a book."""
        try:
            puzzle_ids_str = request.form.get("puzzle_ids", "")
            puzzle_ids = [pid.strip() for pid in puzzle_ids_str.split(",") if pid.strip()]

            if book_mgr.add_puzzles_to_book(book_id, puzzle_ids):
                flash(f"Added {len(puzzle_ids)} puzzles to book", "success")
            else:
                flash("Book not found", "error")

        except ValueError as e:
            flash(f"Error: {str(e)}", "error")

        # The puzzle-review modal posts here too and wants its list back, with
        # the filters it was opened from; book_detail's own form has no
        # return_to and lands on the book.
        if request.form.get("return_to") is not None:
            return _back_to_puzzles_list()
        return redirect(url_for("book_detail", book_id=book_id))

    @app.route("/book/<book_id>/remove-puzzle", methods=["POST"])
    def remove_puzzle_from_book(book_id):
        """Remove one puzzle from a book.

        book_detail.html's per-row Remove button posted here since the page
        was written, but no route answered — every click was a 404. The
        manager method it needed already existed.
        """
        puzzle_id = request.form.get("puzzle_id", "").strip()
        if book_mgr.remove_puzzle_from_book(book_id, puzzle_id):
            flash("Puzzle removed from book", "success")
        else:
            flash("Book or puzzle not found", "error")
        return redirect(url_for("book_detail", book_id=book_id))

    @app.route("/book/<book_id>/status", methods=["POST"])
    def update_book_status(book_id):
        """Update book status."""
        status = request.form.get("status")

        try:
            if book_mgr.set_book_status(book_id, status):
                flash(f"Book status updated to {status}", "success")
            else:
                flash("Book not found", "error")

        except ValueError as e:
            flash(f"Error: {str(e)}", "error")

        return redirect(url_for("book_detail", book_id=book_id))

    @app.route("/book/<book_id>/generate-pdf", methods=["POST"])
    def generate_book_pdf(book_id):
        """Generate PDF for a book."""
        book = book_mgr.get_book(book_id)
        if not book:
            flash("Book not found", "error")
            return redirect(url_for("books_list"))

        if len(book.puzzle_ids) == 0:
            flash("Cannot generate PDF for book with no puzzles", "error")
            return redirect(url_for("book_detail", book_id=book_id))

        try:
            # Get puzzles for the book
            puzzle_data = []
            for puzzle_id in book.puzzle_ids:
                puzzle = puzzle_review.get_puzzle(puzzle_id)
                if puzzle:
                    puzzle_data.append(puzzle)

            if not puzzle_data:
                flash("No valid puzzles found for book", "error")
                return redirect(url_for("book_detail", book_id=book_id))

            # Generate PDF
            pdf_gen = get_pdf_generator()
            pdf_bytes = pdf_gen.generate_book_pdf(
                {
                    "title": book.metadata.title,
                    "description": book.metadata.description,
                    "theme": book.metadata.theme,
                    "target_audience": book.metadata.target_audience,
                    "page_count": len(puzzle_data),
                },
                puzzle_data
            )

            # Store PDF URL (in production, save to S3 or similar)
            book_mgr.set_pdf_url(book_id, f"PDF generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}")

            flash("PDF generated successfully!", "success")

            # Return PDF for download
            return send_file(
                pdf_bytes,
                mimetype="application/pdf",
                as_attachment=True,
                download_name=f"{book.metadata.title.replace(' ', '_')}.pdf"
            )

        except Exception as e:
            flash(f"Error generating PDF: {str(e)}", "error")
            return redirect(url_for("book_detail", book_id=book_id))

    @app.route("/api/batch/<batch_id>/status")
    def api_batch_status(batch_id):
        """API endpoint for batch status (JSON)."""
        job = batch_gen.get_batch_status(batch_id)
        if not job:
            return jsonify({"error": "Batch not found", "batch_id": batch_id}), 404

        return jsonify(job.to_dict())

    @app.route("/api/batch/<batch_id>")
    def api_batch_status_alt(batch_id):
        """API endpoint for batch status (alternative URL)."""
        job = batch_gen.get_batch_status(batch_id)
        if not job:
            return jsonify({"error": "Batch not found", "batch_id": batch_id}), 404

        return jsonify(job.to_dict())

    @app.route("/api/puzzles")
    def api_puzzles():
        """API endpoint for filtered puzzles (JSON)."""
        try:
            size = request.args.get("size", type=int)
            difficulty = request.args.get("difficulty")
            quality_min = request.args.get("quality_min", type=int)
            limit = request.args.get("limit", 25, type=int)
            offset = request.args.get("offset", 0, type=int)

            filter_opts = PuzzleFilter(
                size=(size, size) if size is not None else None,
                side_range=_side_range_from_args(),
                puzzle_name=request.args.get("puzzle_name"),
                difficulty=difficulty,
                quality_min=quality_min,
                limit=limit,
                offset=offset,
            )
            result = puzzle_review.filter_puzzles(filter_opts)

            return jsonify(result.to_dict())

        except ValueError as e:
            return jsonify({"error": str(e)}), 400

    @app.route("/api/image/<file_id>")
    def api_get_image(file_id):
        """Serve uploaded image file (original, uncropped)."""
        image_mgr = get_image_manager()
        image = image_mgr.get_image(file_id)

        if not image:
            return "Not found", 404

        try:
            # Verify file exists
            import os
            if not os.path.exists(image.file_path):
                return f"File not found: {image.file_path}", 404

            return send_file(
                image.file_path,
                mimetype=f"image/{image.format.lower()}",
            )
        except FileNotFoundError:
            return f"File missing: {image.file_path}", 404
        except Exception as e:
            return f"Error loading image: {str(e)}", 500

    @app.route("/api/image/<file_id>/size", methods=["POST"])
    def api_update_image_size(file_id):
        """Store an image's size choice and return the grid it now predicts,
        so the preview page's "Predicted Output" follows the size controls
        instead of showing the size the page was rendered with."""
        image_mgr = get_image_manager()
        image = image_mgr.get_image(file_id)
        if not image:
            return jsonify({"error": "Not found"}), 404

        mode = request.form.get("mode", image.size_mode)
        if mode not in ("fixed", "short", "min", "max"):
            return jsonify({"error": f"Unknown size mode {mode!r}"}), 400
        value = request.form.get("value", image.size_value, type=int)
        if value is None or not MIN_SIZE <= value <= MAX_SIZE:
            return jsonify({"error": f"Size must be {MIN_SIZE}-{MAX_SIZE}"}), 400

        image_mgr.update_image_size(file_id, mode, value)
        fit = image.size_fit()
        return jsonify({
            "status": fit.status,
            "extent": list(fit.extent),
            "prediction_html": render_template("_size_fit_prediction.html", image=image, fit=fit),
            "box_html": render_template("_size_fit_box.html", image=image, fit=fit),
        })

    @app.route("/api/image/<file_id>/cropped")
    def api_get_cropped_image(file_id):
        """Serve cropped preview (what will be used for puzzle generation).

        Uses the same ink-bounding-box trim and aspect-preserving centre crop
        as ``nonogram.sourcing.image.generate`` (the pipeline
        :func:`nonogram.admin.image_to_puzzle.image_to_grid` now delegates to)
        so this preview shows the crop that will actually be applied, rather
        than a differently-thresholded content-only trim that never matched
        the final puzzle (which also fit-cropped to the target aspect ratio).
        """
        from nonogram.sourcing.image import load_greyscale, ink_bounding_box, fit_crop_box
        import os
        image_mgr = get_image_manager()
        image = image_mgr.get_image(file_id)

        if not image:
            return "Not found", 404

        try:
            # Verify file exists
            if not os.path.exists(image.file_path):
                return f"File not found: {image.file_path}", 404

            target_width, target_height = image.predict_size()

            greyscale = load_greyscale(image.file_path)
            content = greyscale.crop(ink_bounding_box(greyscale))
            final_box = fit_crop_box(*content.size, target_width, target_height)
            img = content.crop(final_box)

            # Save to bytes
            img_bytes = BytesIO()
            # Convert format to PIL-compatible name (JPEG not JPG)
            save_format = "JPEG" if image.format.upper() in ("JPG", "JPEG") else image.format.upper()
            img.save(img_bytes, format=save_format)
            img_bytes.seek(0)

            return send_file(
                img_bytes,
                mimetype=f"image/{image.format.lower()}",
            )
        except Exception as e:
            return f"Error: {str(e)}", 500

    @app.route("/api/puzzle/<puzzle_id>/grid")
    def api_puzzle_grid_from_puzzle(puzzle_id):
        """Get puzzle grid as SVG from stored puzzle."""
        # Use DB-backed puzzle_review from closure, not legacy service
        puzzle = puzzle_review.get_puzzle(puzzle_id)

        if not puzzle:
            return "Not found", 404

        try:
            # Get grid from puzzle (dict object)
            grid = puzzle.get('grid')
            if not grid:
                return "No grid data stored", 500

            # Validate grid format
            if not isinstance(grid, list) or not grid or not isinstance(grid[0], list):
                return "Invalid grid format", 500

            # Generate SVG
            svg = grid_to_svg(grid, cell_size=20)
            if not svg:
                return "Failed to generate SVG", 500

            return svg, 200, {"Content-Type": "image/svg+xml"}

        except TypeError as e:
            return f"Grid format error: {str(e)}", 500
        except Exception as e:
            return f"Error generating grid: {str(e)}", 500

    @app.route("/api/puzzle/<puzzle_id>/grid/download")
    def api_puzzle_grid_download_from_puzzle(puzzle_id):
        """Download puzzle grid as SVG file from stored puzzle."""
        # Use DB-backed puzzle_review from closure, not legacy service
        puzzle = puzzle_review.get_puzzle(puzzle_id)

        if not puzzle:
            return "Not found", 404

        try:
            # Get grid from puzzle (dict object)
            grid = puzzle.get('grid')
            if not grid:
                return "No grid data", 500

            # Generate SVG
            svg_bytes = grid_to_svg(grid, cell_size=20).encode("utf-8")
            filename = f"puzzle_{puzzle_id}.svg"

            return send_file(
                BytesIO(svg_bytes),
                mimetype="image/svg+xml",
                as_attachment=True,
                download_name=filename,
            )

        except Exception as e:
            return f"Error: {str(e)}", 500

    @app.route("/api/puzzle/<puzzle_id>/grid/download-pdf")
    def api_puzzle_grid_download_pdf(puzzle_id):
        """Download puzzle grid as PDF file with puzzle and solution pages."""
        # Use DB-backed puzzle_review from closure, not legacy service
        puzzle = puzzle_review.get_puzzle(puzzle_id)

        if not puzzle:
            return "Not found", 404

        try:
            # Validate puzzle has required fields
            grid = puzzle.get('grid')
            if not grid:
                return "No grid data", 500

            # Convert grid to clues using the standard clues module
            width = puzzle.get('width', len(grid[0]) if grid else 0)
            height = puzzle.get('height', len(grid) if grid else 0)

            row_clues = tuple(clues.encode_line(row) for row in grid)
            col_clues = tuple(clues.encode_line([grid[i][j] for i in range(height)]) for j in range(width))

            # Create ExportPayload for the professional PDF renderer
            payload = ExportPayload(
                grid=grid,
                row_clues=row_clues,
                column_clues=col_clues,
                seed=0,  # Not tracked in admin panel
                mode="image",  # Generated from image
                width=width,
                height=height,
                density=None,
                name=puzzle.get('puzzle_name', puzzle_id),
                difficulty=puzzle.get('difficulty_tier', 'Unknown'),
            )

            # Use the professional PDF renderer to generate pages
            puzzle_page, answer_page = render_pages(payload)

            # Convert to PDF bytes using Pillow
            pdf_bytes = BytesIO()
            puzzle_page.save(
                pdf_bytes,
                format="PDF",
                save_all=True,
                append_images=[answer_page],
                resolution=300,  # High quality
            )
            pdf_bytes.seek(0)

            filename = f"{puzzle_id}.pdf"
            return send_file(
                pdf_bytes,
                mimetype="application/pdf",
                as_attachment=True,
                download_name=filename,
            )

        except Exception as e:
            app.logger.exception("PDF generation error for %s", puzzle_id)
            return f"Error: {str(e)}", 500

    @app.route("/api/puzzle/<puzzle_id>/details")
    def api_puzzle_details(puzzle_id):
        """Get full puzzle details as JSON (for detail modal)."""
        puzzle = puzzle_review.get_puzzle(puzzle_id)

        if not puzzle:
            return jsonify({"error": "Puzzle not found"}), 404

        # Fetch available books for assignment dropdown
        books = book_mgr.get_all_books()

        return jsonify({
            "puzzle": puzzle,
            "strategies": _strategy_view(puzzle_review.strategies_for(puzzle)),
            "books": [{"id": b.book_id, "title": b.metadata.title} for b in books],
        })

    @app.route("/puzzle/<puzzle_id>/delete", methods=["POST"])
    def delete_puzzle(puzzle_id):
        """Delete a rejected puzzle."""
        puzzle = puzzle_review.get_puzzle(puzzle_id)

        if not puzzle:
            flash("Puzzle not found", "error")
            return _back_to_puzzles_list()

        # Only allow deletion of rejected puzzles
        if puzzle.get("status") != "rejected":
            flash("Only rejected puzzles can be deleted", "error")
            return _back_to_puzzles_list()

        # Only allow deletion if not in a book
        if puzzle.get("book_id"):
            flash("Cannot delete puzzle that is in a book", "error")
            return _back_to_puzzles_list()

        if puzzle_review.delete_puzzle(puzzle_id):
            flash("Puzzle deleted", "success")
        else:
            flash("Puzzle not found", "error")

        return _back_to_puzzles_list()

    @app.route("/puzzle/<puzzle_id>/restore", methods=["POST"])
    def restore_puzzle(puzzle_id):
        """Restore rejected or approved puzzle back to draft."""
        if puzzle_review.restore_puzzle(puzzle_id):
            flash(f"Puzzle restored to draft", "success")
        else:
            flash(f"Puzzle not found", "error")

        # Return to previous page or puzzles list
        batch_id = request.args.get("batch_id")
        if batch_id:
            return redirect(url_for("generated_puzzles", batch_id=batch_id))
        return _back_to_puzzles_list()

    # ----------------------------------------------------------------------
    # CARD-077 — the re-grade batch, behind a confirmation page
    # ----------------------------------------------------------------------

    def _regrade_batch():
        """``admin.regrade``, imported at call time and not at module import.

        The module reaches into ``nonogram.db``, so importing it up top would
        make SQLAlchemy a hard requirement of the admin panel — it is the
        optional ``db`` extra, and the rest of this file already keeps it that
        way (see ``delete_puzzle``). Both routes below refuse before they get
        here when there is no database configured, so the import only runs when
        there is one.
        """
        from .regrade import regrade

        return regrade

    def _render_regrade(report, applied):
        """Render the one page both the preview and the confirmed run answer with.

        One template and one report shape for both, because the whole promise
        of the confirmation page is that what the owner approved is what ran.
        """
        return render_template(
            "regrade.html",
            report=report,
            applied=applied,
            tiers=list(Tier),
        )

    @app.route("/regrade", methods=["GET"])
    def regrade_preview():
        """The dry run: what the batch *would* do, writing nothing.

        Every row is solved here exactly as it would be on the write path, so
        the page costs the same as the run it is previewing. That is affordable
        at this table's size and is the reason the two paths cannot disagree.
        """
        if not app.config["REGRADE_ENABLED"]:
            abort(404)
        if session_scope is None:
            flash("Re-grading needs a database (DATABASE_URL is not set)", "error")
            return redirect(url_for("dashboard"))

        with session_scope() as db:
            report = _regrade_batch()(db, dry_run=True)
        return _render_regrade(report, applied=False)

    @app.route("/regrade", methods=["POST"])
    def regrade_apply():
        """The confirmed run — the one point of no return in this card.

        Reached only from the preview page's button. What it overwrites is
        not recoverable from inside the app: the grades it replaces are not
        copied anywhere (CARD-084 dropped the columns that used to hold them),
        so the only record of them is a snapshot taken beforehand. Rows it
        skips are not touched at all.
        """
        if not app.config["REGRADE_ENABLED"]:
            abort(404)
        if session_scope is None:
            flash("Re-grading needs a database (DATABASE_URL is not set)", "error")
            return redirect(url_for("dashboard"))

        with session_scope() as db:
            report = _regrade_batch()(db, dry_run=False)

        flash(
            f"Re-graded {len(report.regraded)} of {report.row_count} puzzles; "
            f"{len(report.skipped)} left unchanged",
            "success" if not report.skipped else "warning",
        )
        return _render_regrade(report, applied=True)

    @app.errorhandler(404)
    def not_found(e):
        """Handle 404 errors."""
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        """Handle 500 errors."""
        return render_template("500.html", error=str(e)), 500

    return app


def main(port: int = DEFAULT_PORT) -> None:
    """Run the admin panel on this machine only.

    Takes a port and nothing else. A ``host=`` parameter here would move
    NFR-003's criterion out of this module and into every call site, which is
    the shape ``nonogram.web.create_server`` already refuses for the same
    reason — and the shape a test can pin by signature.

    ``debug`` is off. It was on, together with the wildcard bind, which put a
    Werkzeug console on every interface. Debugging is what
    ``flask --app nonogram.admin.app run --debug`` is for: opting in by typing
    it, on a path that already defaults to loopback.
    """
    create_app().run(host=LOOPBACK_HOST, port=port)


if __name__ == "__main__":
    main()
