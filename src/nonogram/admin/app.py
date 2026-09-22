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
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime
import hmac
import json
import os
import secrets
import tempfile
import threading
import time
import urllib.parse
import uuid
from pathlib import Path
from io import BytesIO

from .batch_generator import get_batch_generator, BatchStatus, BatchGenerator
from .puzzle_review import (
    get_puzzle_review_service,
    BOOK_TAB_SORT,
    MAX_PUZZLE_NAME_LENGTH,
    PuzzleFilter,
    PuzzleReviewService,
    PuzzleStatus,
    STRATEGY_NAMES,
)
from .book_manager import get_book_manager, BookStatus, revise_plan
from .book_plan import (
    BUCKETS as PLAN_BUCKETS,
    DEFAULT_PLAN,
    TIERS as PLAN_TIERS,
    InvalidPlan,
    Split as PlanSplit,
    bucket_of,
    planned_cells,
    selection_cells,
)
from .image_manager import (
    CANNOT_FIT,
    MOVED_TO_LARGE,
    SIZE_PRESETS,
    floor_percent,
    get_image_manager,
)
from .grid_renderer import grid_to_svg
from .print_specs import PrintSpecValidator
from .book_pdf_generator import BookPDFGenerator, interior_page_count, tier_breakdown

# Import the professional export PDF module
from nonogram.export.pdf import render_pages
from nonogram.export import ExportPayload
from nonogram import clues, orchestrator
from nonogram.difficulty import Tier, tier_of_record
from nonogram.errors import (
    GenerationAbandoned,
    NonogramError,
    NotUniquelySolvable,
    SizeOutOfRange,
)
from nonogram.limits import MAX_SIZE, MIN_SIZE
from nonogram.orchestrator import BATCH_BUDGET_SECONDS, MAX_BATCH_COUNT

# CARD-050: real image-mode quality/recognizability, in place of the
# density-only heuristic and hardcoded "medium" this replaces below.
from PIL import Image as PILImage
from PIL import ImageOps as PILImageOps
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

#: The image batch's clock (CARD-095). A module attribute rather than a direct
#: ``time.monotonic()`` call so a test can run a batch past its budget without
#: sleeping — the same reason ``orchestrator.generate_batch`` takes ``monotonic``.
_batch_clock = time.monotonic


#: The statuses a puzzle can be filtered by, in curation order (CARD-066).
#: Read from the enum so the page cannot drift from the store.
_PUZZLE_STATUSES = tuple(status.value for status in PuzzleStatus)


def _size_suffix(option_fit, several: bool) -> str:
    """Which size a results line is about, when a picture has more than one.

    ``""`` for a picture with a single option, so every existing line reads
    exactly as it did (CARD-069 AC-3). Otherwise the mode and, where it has
    one, its value — ``" (fixed 20)"`` — because a picture can now appear in
    these lists several times and "skipped: too elongated" against a bare
    filename would not say *which* size was skipped (AC-4).
    """
    if not several:
        return ""
    option = option_fit.option
    if option.mode in ("fixed", "short"):
        return f" ({option.mode} {option.value})"
    return f" ({option.mode})"


def _bulk_report(verb: str, outcome, already: str | None, *, noun: str = "puzzle") -> str:
    """What a bulk action did, in one sentence (CARD-068, CARD-100).

    Three numbers, each earned: what changed, what needed no change, and what a
    book held back. "Approved 1 puzzle" on a batch of three is the kind of
    count that sends the owner looking for the other two.

    The book clause was deliberately absent until CARD-100. The guard it
    reports on read ``Puzzle.book_id``, which nothing wrote — membership went
    to ``Book.puzzle_ids`` alone — so the number was zero however many puzzles
    a book actually held, and a confident "0 left alone: in a book" would have
    been worse than silence. Now that both halves are written together the
    number is true, and the sentence says it.
    """
    plural = "" if outcome.changed == 1 else "s"
    sentence = f"{verb} {outcome.changed} {noun}{plural}"
    if already and outcome.unchanged:
        was = "was" if outcome.unchanged == 1 else "were"
        sentence += f"; {outcome.unchanged} {was} {already}"
    if outcome.in_book:
        sentence += f"; {outcome.in_book} left alone: in a book"
    return sentence + "."


@dataclass(frozen=True)
class PictureGroup:
    """One picture's puzzles, in the order they should be shown (CARD-099).

    ``source`` is the picture's filename, or ``None`` for puzzles that came
    from no picture at all — a random batch. The unnamed group is not a
    picture and is never counted as one.
    """

    source: str | None
    puzzles: list[dict]


def group_by_picture(puzzles) -> list[PictureGroup]:
    """Gather a batch's puzzles into one group per source picture.

    Both orders are computed here rather than inherited, because the order the
    page is given is the wrong one: ``PuzzleFilter``'s default sort is
    ``batch_id,-size,quality``, so within a batch the puzzles arrive
    widest-first and a picture's sizes are interleaved with every other
    picture's.

    * Pictures come in the order their first puzzle was made, which for an
      image batch is the order they were uploaded — the generate loop iterates
      ``(picture, option)`` pairs built in that order (CARD-069).
    * A picture's puzzles come in extent order, smallest area first, so the
      same picture always reads small-to-large.

    Ties fall back to the name and the extent, so the page is a pure function
    of the rows: two reviewers see the same page, and a re-render does not
    reshuffle it.
    """
    groups: dict[str | None, list[dict]] = {}
    for puzzle in puzzles:
        groups.setdefault(puzzle.get("source_image"), []).append(puzzle)

    def made_at(puzzle: dict) -> str:
        # A missing timestamp sorts first rather than raising: this is a page,
        # and a row the store wrote without one is still a row to show.
        return puzzle.get("created_at") or ""

    def picture_key(item):
        source, found = item
        # `source is None` keeps the unnamed group last without comparing
        # None to a string.
        return (source is None, min(made_at(p) for p in found), source or "")

    def extent_key(puzzle: dict):
        width, height = puzzle.get("width") or 0, puzzle.get("height") or 0
        return (width * height, width, height)

    return [
        PictureGroup(source=source, puzzles=sorted(found, key=extent_key))
        for source, found in sorted(groups.items(), key=picture_key)
    ]


class _BatchOutOfTime(Exception):
    """The batch clock ran out between one extent of a picture and the next.

    Raised by :func:`_generate_image_puzzle` instead of trying a neighbour
    extent, so the batch route can tell "this picture was cut short by the
    batch's clock" apart from "this picture could not be made" (CARD-095).
    """


def _generate_image_puzzle(image, width, height, may_start=None):
    """Generate ``image`` at ``(width, height)``; if that extent is abandoned
    (not uniquely solvable within the pixel-nudge bound), retry at the
    long-side ±1 neighbours from ``image.neighbour_extents`` (CARD-062).

    Generation is deterministic per picture and extent, so no extent is tried
    twice. On the predicted extent any other error propagates at once: a
    different extent cannot fix an unreadable picture. On a neighbour, any
    other ``NonogramError`` (e.g. a solver timeout) ends the retry and the
    predicted extent's abandonment is what gets reported — that is the
    picture's real problem, not the neighbour's side effect.

    ``may_start``, when given, is asked before each *neighbour* extent (the
    caller asks before the predicted one). Each extent is a whole
    ``orchestrator.generate`` with its own 30 s deadline, so one picture can cost
    three of them; checking only between pictures would let a batch run
    ``BATCH_BUDGET_SECONDS`` plus three deadlines, past the server's timeout.
    Checked here, the ceiling is one deadline past the budget (CARD-095).

    Returns:
        ``(puzzle, extent_used)``.

    Raises:
        GenerationAbandoned: the predicted extent's own error, when it and
            every neighbour were abandoned.
        _BatchOutOfTime: an extent was abandoned and ``may_start`` said no to
            trying the next one.
    """
    first_abandonment = None
    for index, extent in enumerate([(width, height), *image.neighbour_extents((width, height))]):
        if index > 0 and may_start is not None and not may_start():
            raise _BatchOutOfTime() from first_abandonment
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
    # Still here after CARD-098 retired the *tier* of the same name: a solve
    # that had to branch is still a fact worth showing beside a puzzle, and
    # FR-029 still reports it. Only the difficulty claim went.
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
        # The batch ceiling, for the same reason (CARD-094).
        MAX_BATCH_COUNT=MAX_BATCH_COUNT,
    )
    app.jinja_env.filters['strategy_label'] = lambda name: STRATEGY_LABELS.get(name, name)

    # Construct service instances
    # If DATABASE_URL is set, use DB-backed persistence; otherwise use in-memory mode
    if session_scope:
        puzzle_review = PuzzleReviewService(session_factory=session_scope)
        batch_gen = BatchGenerator(puzzle_review_service=puzzle_review, session_factory=session_scope)
        book_mgr = get_book_manager(session_factory=session_scope, puzzle_store=puzzle_review)
        app.logger.info("Database persistence enabled (DATABASE_URL set)")
    else:
        puzzle_review = PuzzleReviewService(session_factory=None)
        batch_gen = BatchGenerator(puzzle_review_service=puzzle_review, session_factory=None)
        book_mgr = get_book_manager(puzzle_store=puzzle_review)
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

    @app.route("/batch/image/<file_id>/size-option", methods=["POST"])
    def toggle_size_option(file_id):
        """Tick or untick one extra size for this picture (CARD-069).

        A POST per button rather than one fetch per click: the page then
        re-renders every prediction from the same server-side rule, so two
        quick clicks cannot leave a card showing a size it is not set to —
        the failure CARD-067's review found in the fetch path and fixed with
        a request token.

        Un-ticking the last remaining size is refused by the store, not
        treated as removing the picture; the message says where the Remove
        button is.
        """
        image_mgr = get_image_manager()
        image = image_mgr.get_image(file_id)
        mode = request.form.get("mode", "")
        if image is None:
            flash("That picture is no longer in this batch", "info")
        elif any(option.mode == mode for option in image.size_options):
            if not image_mgr.remove_size_option(file_id, mode):
                flash(
                    "A picture needs at least one size — use Remove this "
                    "picture to take it out of the batch",
                    "info",
                )
        elif not image_mgr.add_size_option(file_id, mode, image.size_value):
            flash(f"Could not add the {mode} size", "error")

        return redirect(url_for("preview_batch_images"))

    @app.route("/batch/image/<file_id>/remove", methods=["POST"])
    def remove_batch_image(file_id):
        """Drop one picture from the batch job (CARD-067 AC-5).

        ``ImageManager.remove_image`` already deletes the uploaded temp file
        along with the row, so there is nothing to clean up here — which is
        the answer to the card's open question about it.

        An unknown id is reported rather than ignored: the button only exists
        beside a picture, so reaching this with an id the store does not have
        means the page is stale, and saying so beats a silent redirect that
        looks like it worked. Either way the answer is the preview page, which
        redirects to the upload step by itself once the batch is empty.
        """
        image_mgr = get_image_manager()
        image = image_mgr.get_image(file_id)
        if image is None:
            flash("That picture is no longer in this batch", "info")
        elif image_mgr.remove_image(file_id):
            flash(f"Removed {image.original_filename} from this batch", "success")
        else:
            flash("Could not remove that picture", "error")

        return redirect(url_for("preview_batch_images"))

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
                # Validate image count before processing. The ceiling is the
                # orchestrator's, read here rather than restated: this said 200
                # after CARD-088 lowered it to 50, so a selection of 51-200 passed
                # preview and was refused one step later by create_batch (CARD-094).
                if len(images) < 1 or len(images) > MAX_BATCH_COUNT:
                    flash(
                        f"❌ Invalid image count: {len(images)}. "
                        f"Must be 1-{MAX_BATCH_COUNT} images.",
                        "error",
                    )
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
        #
        # The batch's own clock (CARD-095), started before any work and read
        # before every generate call — each picture's first extent here, each
        # neighbour extent inside _generate_image_puzzle. A picture already
        # running finishes its current extent, so the worst case is
        # BATCH_BUDGET_SECONDS + GENERATION_BUDGET_SECONDS: the same ceiling the
        # random batch holds, and the one tests/test_admin_serving.py checks
        # against gunicorn's --timeout. Before this card an image batch had no
        # bound at all, and one slow picture costs up to three deadlines.
        batch_deadline = _batch_clock() + BATCH_BUDGET_SECONDS

        def may_start() -> bool:
            return _batch_clock() < batch_deadline

        try:
            # Every size that was actually ticked, across every picture
            # (CARD-069): a batch whose pictures carry several options records
            # all of them, and its count is the number of puzzles to be made
            # rather than the number of pictures — the two stopped being the
            # same thing with this card.
            sizes = {
                option.value if option.mode in ("fixed", "short") else 20
                for image in images
                for option in image.size_options
            }
            planned = sum(len(image.size_options) for image in images)

            # Create batch job
            batch_id = batch_gen.create_batch(
                count=planned,
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
            # Pictures the clock stopped the batch before (or part-way through).
            # Kept loaded for the next batch rather than cleared (owner, Q-1).
            not_started = []
            adjustments = []
            skipped = []
            moved = []

            # CARD-069: one puzzle per (picture, size option), not per
            # picture. A picture carries one option unless somebody ticked
            # more, so a batch nobody re-sized is exactly the batch it was.
            # The pairs are built up front so that the counts below, the
            # clock's "not started" list and the results lines all speak about
            # the same unit of work.
            jobs = [
                (image, option_fit)
                for image in images
                for option_fit in image.size_fits()
            ]

            for image, option_fit in jobs:
                # The size this job is for, and how it is to be named. A
                # picture with several options puts its extent in every name
                # from it (AC-7), so two puzzles from one picture are never
                # two rows reading the same; with one option the name is
                # untouched, which is what keeps AC-3 true to the string.
                several = len(image.size_options) > 1
                try:
                    # CARD-064: a size even Large would cut below
                    # MIN_KEPT_SHARE is never generated; it is reported.
                    fit = option_fit.fit
                    if fit.status == CANNOT_FIT:
                        skipped.append(
                            f"{image.original_filename}{_size_suffix(option_fit, several)} "
                            f"skipped: too elongated for any supported size "
                            f"(even Large keeps only {floor_percent(fit.kept)})"
                        )
                        continue
                    width, height = fit.extent

                    # Once the clock has stopped the batch it starts nothing
                    # else; the rest of the loop only sorts the remaining
                    # work into "skipped" (above) and "not started".
                    if not_started or not may_start():
                        not_started.append((image, option_fit))
                        continue

                    # Convert image to puzzle through the canonical,
                    # solver-verified pipeline (CARD-049) — the same
                    # judge_candidate uniqueness check and bounded pixel-nudge
                    # recovery `nonogram generate --mode image` runs, instead
                    # of a grid nothing ever solver-checks. One call per
                    # extent tried: orchestrator.generate_batch() has no
                    # per-item image-path parameter.
                    puzzle, used = _generate_image_puzzle(
                        image, width, height, may_start=may_start
                    )

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
                            # FR-029, as in the random batch: the aggregate
                            # carries the deciding solve's ladder (CARD-072).
                            strategies_used=list(puzzle.strategies),
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
                    # Written as each puzzle is stored, so the record matches
                    # the store even if the worker is killed anyway (CARD-095).
                    # create_batch already marked an image batch COMPLETE
                    # before this loop, so the count was the lie.
                    batch_gen._update_batch_status(batch_id, puzzle_count=generated_count)
                    if several:
                        # AC-7: the extent distinguishes the puzzles one
                        # picture produced. Applied after the store because
                        # `add_puzzle` takes no name — `rename_puzzle` is the
                        # one writer of that column.
                        puzzle_review.rename_puzzle(
                            puzzle_id, f"{image.puzzle_name} ({width}x{height})"
                        )
                    if fit.status == MOVED_TO_LARGE:
                        # CARD-064 (G-2): the chosen size was not used — say
                        # so in the results too, not only in the preview.
                        reason = (
                            f"the chosen size {fit.chosen[0]}x{fit.chosen[1]} would "
                            f"cut it (keeps {floor_percent(fit.chosen_kept)})"
                            if fit.chosen is not None
                            else "the chosen size can't keep its shape"
                        )
                        moved.append(
                            f"{image.original_filename}"
                            f"{_size_suffix(option_fit, several)}: "
                            f"moved up to Large — {reason}"
                        )
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

                except _BatchOutOfTime:
                    # Its predicted extent was abandoned and the clock ran out
                    # before a neighbour could be tried: not a failed picture,
                    # an unfinished one. It goes back to the next batch.
                    not_started.append(image)
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

            if not_started:
                # A clock stop, reported as one (CARD-088's distinction): not bad
                # luck, and the same selection will stop in the same place.
                picture_word = "picture was" if len(not_started) == 1 else "pictures were"
                clock_note = (
                    f"{len(not_started)} {picture_word} not started before this "
                    f"batch's {BATCH_BUDGET_SECONDS:.0f}s time budget ran out. "
                    f"{'It is' if len(not_started) == 1 else 'They are'} still "
                    f"loaded — run another batch for "
                    f"{'it' if len(not_started) == 1 else 'them'}."
                )
                flash(clock_note, "warning")
                if generated_count > 0:
                    # COMPLETE with a note: the puzzles are real (owner, Q-2).
                    batch_gen._update_batch_status(batch_id, error_message=clock_note)
                else:
                    batch_gen._update_batch_status(
                        batch_id, BatchStatus.ERROR, error_message=clock_note
                    )

            # Show results
            if generated_count > 0:
                # "from N picture(s)" stays the picture count, which is no
                # longer an upper bound on the puzzles: a picture with two
                # sizes ticked contributes two (CARD-069).
                flash(
                    f"✅ Generated {generated_count} puzzle(s) from {len(images)} image(s)",
                    "success",
                )
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
            if not_started:
                # Clear only what this batch attempted; the rest waits (Q-1).
                waiting = {image.file_id for image, _ in not_started}
                for image in images:
                    if image.file_id not in waiting:
                        image_mgr.remove_image(image.file_id)
            else:
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

        # CARD-099: two numbers, not one used twice. `total_count` is what the
        # batch *planned* — since CARD-069 a picture can carry several sizes,
        # so it counts puzzles, not pictures, and the page said "2 puzzles from
        # 2 pictures" for one picture at two sizes. The picture count comes
        # from the rows instead; the unnamed group (a random batch) is not a
        # picture and does not count as one.
        groups = group_by_picture(puzzles)
        picture_count = sum(1 for group in groups if group.source)

        batch_job = batch_gen.get_batch_status(batch_id)
        planned_count = batch_job.total_count if batch_job else len(puzzles)
        # What the batch planned and did not store. The page cannot say *why*:
        # quality-filtered, skipped as too elongated, refused by the store and
        # never started all land here identically, so it reports the shortfall
        # and stops short of naming a cause (AC-3).
        missing_count = max(0, planned_count - len(puzzles)) if batch_job else 0

        return render_template(
            "generated_puzzles.html",
            batch_id=batch_id,
            puzzles=puzzles,
            groups=groups,
            strategies=strategies,
            picture_count=picture_count,
            planned_count=planned_count,
            missing_count=missing_count,
            # CARD-068: each bulk button names the number it is about. Asked of
            # the store, not counted off `puzzles` above, so the number in the
            # confirmation and the number the action reports are one rule with
            # two readings rather than two rules.
            action_counts=puzzle_review.batch_action_counts(batch_id),
        )

    @app.route("/batch/<batch_id>/approve-all", methods=["POST"])
    def approve_batch_puzzles(batch_id):
        """Approve every puzzle of a batch that is not already in a book."""
        if not batch_gen.get_batch_status(batch_id):
            flash("Batch not found", "error")
            return redirect(url_for("dashboard"))
        outcome = puzzle_review.set_batch_status(batch_id, PuzzleStatus.APPROVED)
        flash(_bulk_report("Approved", outcome, "already approved"), "success")
        return redirect(url_for("generated_puzzles", batch_id=batch_id))

    @app.route("/batch/<batch_id>/reject-all", methods=["POST"])
    def reject_batch_puzzles(batch_id):
        """Reject every puzzle of a batch that is not already in a book."""
        if not batch_gen.get_batch_status(batch_id):
            flash("Batch not found", "error")
            return redirect(url_for("dashboard"))
        outcome = puzzle_review.set_batch_status(batch_id, PuzzleStatus.REJECTED)
        flash(_bulk_report("Rejected", outcome, "already rejected"), "success")
        return redirect(url_for("generated_puzzles", batch_id=batch_id))

    @app.route("/batch/<batch_id>/delete-rejected", methods=["POST"])
    def delete_rejected_batch_puzzles(batch_id):
        """Delete every rejected puzzle of a batch that is not in a book."""
        if not batch_gen.get_batch_status(batch_id):
            flash("Batch not found", "error")
            return redirect(url_for("dashboard"))
        outcome = puzzle_review.delete_rejected_in_batch(batch_id)
        flash(_bulk_report("Deleted", outcome, None, noun="rejected puzzle"), "success")
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

        # Strategy (FR-029), the same shape as status above and for the same
        # reason: an unknown value is reported and then ignored, because
        # filtering on it would show an empty list that reads as "nothing
        # matches your other filters".
        strategy = request.args.get("strategy") or None
        if strategy and strategy not in STRATEGY_NAMES:
            flash(
                f"Unknown strategy {strategy!r} — showing every strategy instead",
                "info",
            )
            strategy = None

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
                strategy=strategy,
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
                strategies=STRATEGY_NAMES,
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
        # CARD-100: the store refuses a puzzle a book is built on, and a bare
        # "Puzzle not found" would send the owner looking for a missing row
        # rather than telling them what actually stopped it.
        if puzzle_review.in_a_book(puzzle_id):
            flash("Cannot approve a puzzle that is in a book", "error")
        elif puzzle_review.approve_puzzle(puzzle_id):
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
        # CARD-100: the store refuses a puzzle a book is built on, and a bare
        # "Puzzle not found" would send the owner looking for a missing row
        # rather than telling them what actually stopped it.
        if puzzle_review.in_a_book(puzzle_id):
            flash("Cannot reject a puzzle that is in a book", "error")
        elif puzzle_review.reject_puzzle(puzzle_id):
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

    class _PlanFormError(InvalidPlan):
        """A refused Print setup plan, naming the form field(s) that caused it.

        ``fields`` holds the input names the page marks invalid (CARD-120
        review F-003) — only the failing ones, never all of them.
        """

        def __init__(self, message, fields):
            super().__init__(message)
            self.fields = frozenset(fields)

    _SPLIT_FIELDS = tuple(f"split_{tier.value}" for tier in PLAN_TIERS)

    def _plan_from_form(form, current):
        """The plan a Print setup submission asks for (CARD-120).

        HTTP concerns only: read the count, the split and the 12 matrix cells
        as whole numbers and hand them to the domain. The split-sums-to-100
        refusal is ``Split``'s own (INV-005); which cells are hand-edited is
        ``book_manager.revise_plan``'s (POL-007).

        Raises:
            _PlanFormError: a value is not a whole number, or the domain
                refuses it; ``fields`` names the offending input(s).
        """
        def whole(name, label):
            raw = (form.get(name) or "").strip()
            try:
                return int(raw)
            except ValueError:
                raise _PlanFormError(f"{label} must be a whole number, got {raw!r}", {name}) from None

        count = whole("plan_count", "The puzzle count")
        shares = [whole(name, f"The {tier.value} share") for name, tier in zip(_SPLIT_FIELDS, PLAN_TIERS)]
        cell_names = [[f"cell_{b}_{tier.value}" for tier in PLAN_TIERS] for b in range(len(PLAN_BUCKETS))]
        cells = tuple(
            tuple(
                whole(cell_names[b][t], f"The {bucket.label} x {tier.value} cell")
                for t, tier in enumerate(PLAN_TIERS)
            )
            for b, bucket in enumerate(PLAN_BUCKETS)
        )
        try:
            split = PlanSplit(*shares)
        except InvalidPlan as e:
            raise _PlanFormError(str(e), _SPLIT_FIELDS) from None
        try:
            return revise_plan(current, count, split, cells)
        except InvalidPlan as e:
            # The aggregate refused the count or a cell: name whichever it was.
            if count < 1:
                fields = {"plan_count"}
            else:
                fields = {
                    cell_names[b][t]
                    for b, row in enumerate(cells)
                    for t, value in enumerate(row)
                    if value < 0
                }
            raise _PlanFormError(str(e), fields) from None

    def _readable_plan(book_id):
        """``(stored plan or None, damaged)`` for ``book_id`` (CARD-120).

        A stored document the aggregate refuses to decode (``InvalidPlan``)
        is logged and treated as no plan, flagged ``damaged``: Print setup is
        the one screen that can repair it, so it must not fail on it (review
        F-004). The page then shows — and a submission is revised from —
        ``DEFAULT_PLAN``, and saving overwrites the damaged document.
        """
        try:
            return book_mgr.get_plan(book_id), False
        except InvalidPlan as e:
            app.logger.error("Stored distribution plan of book %s is unreadable: %s", book_id, e)
            return None, True

    def _plan_context(book_id, submitted=None, error_fields=frozenset()):
        """What the plan half of Print setup shows (CARD-120).

        The stored plan, or — for a plan-less book created before migration
        010 (G-3), or one whose stored plan cannot be read (``plan_damaged``)
        — the default plan, marked as not yet stored. ``submitted`` is a
        submission that was not saved (plan refused, or trim refused): its raw
        count, split and all 12 cells are carried back into the fields so the
        owner's input is not lost (F-003); the edited marks stay the stored
        plan's, since nothing was stored. ``error_fields`` names the inputs
        to mark invalid.
        """
        stored, damaged = _readable_plan(book_id)
        plan = stored if stored is not None else DEFAULT_PLAN
        split_values = {tier.value: plan.split.percent(tier) for tier in PLAN_TIERS}
        count_value = plan.count

        def cell_value(b, bucket, tier):
            value = plan.cell(bucket, tier)
            if submitted is not None:
                return submitted.get(f"cell_{b}_{tier.value}", value)
            return value

        if submitted is not None:
            count_value = submitted.get("plan_count", count_value)
            split_values = {
                tier.value: submitted.get(f"split_{tier.value}", split_values[tier.value])
                for tier in PLAN_TIERS
            }
        return {
            "plan": plan,
            "plan_stored": stored is not None,
            "plan_damaged": damaged,
            "plan_error_fields": frozenset(error_fields),
            "plan_count_value": count_value,
            "plan_split_values": split_values,
            "plan_tiers": PLAN_TIERS,
            "plan_rows": [
                (
                    b,
                    bucket,
                    [
                        (tier, cell_value(b, bucket, tier), (bucket, tier) in plan.edited)
                        for tier in PLAN_TIERS
                    ],
                )
                for b, bucket in enumerate(PLAN_BUCKETS)
            ],
            "plan_column_totals": [sum(plan.cell(bucket, tier) for bucket in PLAN_BUCKETS) for tier in PLAN_TIERS],
            "plan_tier_counts": plan.tier_counts,
            "plan_disagrees": plan.disagrees_with_split,
        }

    @app.route("/book/<book_id>/setup-print", methods=["GET", "POST"])
    def setup_print(book_id):
        """Configure print specifications for a book (Step 1 of scaffolding).

        CARD-120: also the book's distribution plan — count, split and the
        4 x 3 per-bucket matrix. A submission the plan refuses (a split not
        summing to 100, a non-whole value) is rejected as a whole and leaves
        the stored plan unchanged (AC-197); the page re-renders with everything
        the owner submitted and only the failing field(s) marked invalid. A
        trim refusal likewise stores nothing and carries the input back. A
        saved plan that disagrees with its split is reported with a warning
        flash on the way on (AC-203/FR-034), not only on reopening. A form
        without the plan fields saves the trim size only, as before.
        """
        book = book_mgr.get_book(book_id)
        if not book:
            flash("Book not found", "error")
            return redirect(url_for("books_list"))

        plan_error = None
        plan_error_fields = frozenset()
        submitted = None

        if request.method == "POST":
            try:
                # Get form data
                unit = request.form.get("unit", "cm")
                width_input = request.form.get("width")
                height_input = request.form.get("height")

                session["unit_preference"] = unit  # Persist unit preference in session

                # The plan is checked before anything is stored, so a refused
                # plan stores nothing — neither the plan nor the trim (AC-197).
                new_plan = None
                if "split_easy" in request.form:
                    # Revised from the plan the page showed: the stored one,
                    # or DEFAULT_PLAN for a plan-less or unreadable one (F-004).
                    current, _ = _readable_plan(book_id)
                    try:
                        new_plan = _plan_from_form(request.form, current)
                    except _PlanFormError as e:
                        plan_error = str(e)
                        plan_error_fields = e.fields

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
                elif plan_error is None:
                    if new_plan is not None:
                        # CARD-124 (owner's decision): the plan is what the
                        # readiness gate measures the selection against, so
                        # editing it on a book that has left draft returns the
                        # book to draft — the same rule a membership change
                        # gets (ADR-0035 "Membership change after draft").
                        # Read before the save, which is what returns it.
                        had_left_draft = book.status != BookStatus.DRAFT.value
                        book_mgr.save_plan(book_id, new_plan)
                        if had_left_draft:
                            flash(
                                "The plan changed, so the book is back in draft: it must "
                                "match its plan again before it can leave.",
                                "warning",
                            )
                        if new_plan.disagrees_with_split:
                            # FR-034: warn at the moment the choice is made,
                            # not only when Print setup is reopened (F-002).
                            columns = " / ".join(
                                str(sum(new_plan.cell(bucket, tier) for bucket in PLAN_BUCKETS))
                                for tier in PLAN_TIERS
                            )
                            planned = " / ".join(str(n) for n in new_plan.tier_counts)
                            flash(
                                "The per-bucket plan disagrees with the general split: hand-edited"
                                f" cells give {columns} (easy / medium / hard), the split plans"
                                f" {planned}. The plan was saved as entered.",
                                "warning",
                            )
                    # Store in book metadata (for now, using the in-memory manager)
                    # In production, this would update the Book row in the database
                    book.metadata.size = f"{spec.trim_width_cm}×{spec.trim_height_cm} cm"
                    book.updated_at = datetime.utcnow()

                    flash(f"Print specs set: {spec.trim_width_cm} × {spec.trim_height_cm} cm", "success")
                    # Proceed to Step 2: Puzzle Selection
                    return redirect(url_for("select_puzzles_for_book", book_id=book_id))

            except ValueError as e:
                flash(f"Error: {str(e)}", "error")

            # Reaching here, nothing was stored (a success redirects above):
            # carry the whole submission back so no input is lost (F-003).
            submitted = request.form

        # Prepare default trim size
        default_width = PrintSpecValidator.DEFAULT_TRIM_WIDTH_CM
        default_height = PrintSpecValidator.DEFAULT_TRIM_HEIGHT_CM
        unit_preference = session.get("unit_preference", "cm")

        # Convert defaults to inches if that's the preference
        if unit_preference == "inches":
            default_width = PrintSpecValidator.cm_to_inches(default_width)
            default_height = PrintSpecValidator.cm_to_inches(default_height)

        if submitted is not None:
            default_width = submitted.get("width", default_width)
            default_height = submitted.get("height", default_height)

        context = {
            "book": book,
            "default_width": default_width,
            "default_height": default_height,
            "unit_preference": unit_preference,
            "plan_error": plan_error,
            **_plan_context(book_id, submitted, plan_error_fields),
        }

        return render_template("book_setup_print.html", **context)

    # ------------------------------------------------------------------
    # CARD-122: puzzle selection in four longest-side tabs (FR-036,
    # BK-UI-4/5/6). Everything below reads book_plan — the one bucketing
    # function (EC-024) and the two halves of every planned-vs-selected
    # figure — and never re-derives a threshold of its own.
    # ------------------------------------------------------------------

    #: The tab a ``bucket=`` value names, by its label ("<=15", "16-20", ...).
    _TABS_BY_LABEL = {bucket.label: bucket for bucket in PLAN_BUCKETS}

    #: The filter inputs the selection screen carries across a tab switch.
    #: Paging is *not* one of them: ``limit`` is carried separately (it is a
    #: property of the screen, not of the filter) and ``offset`` is set by the
    #: control that was pressed — a tab switch starts its tab at the first
    #: page, a page button names the page it wants.
    _SELECT_FILTERS = ("difficulty", "quality_min", "theme", "status", "puzzle_name")

    #: How many tiles a page of a tab holds when nothing asks for another size.
    _SELECT_PAGE = 50

    #: Query parameters this step used to honour and no longer does: the
    #: size-range filter the four longest-side tabs replaced (AC-216).
    _RETIRED_SIZE_PARAMS = ("size", "size_from", "size_to")

    #: CARD-122 (review cycle 1, F-004): where a *pending* selection lives.
    #:
    #: The ticked ids are held here, in this process, and the session cookie
    #: carries only the short token that names them. They used to be written
    #: into the cookie itself, which overflows the browser's 4 KB limit at
    #: ~134 UUID ids — and an overflowing cookie is discarded whole, silently,
    #: taking every other session key with it. A book's default plan is 150
    #: puzzles (ADR-0034) and this screen has a "Select all" button, so that
    #: ceiling sat inside ordinary use.
    #:
    #: The lifecycle this buys is worth stating: a pending selection now lives
    #: for as long as this process does, and no longer. Restarting the panel,
    #: or opening a 33rd browser session before coming back to this one, drops
    #: the ticks that were never committed. Nothing committed is at risk —
    #: ``add_puzzles_to_book`` remains the one commit point (card note (b)) —
    #: and the panel is a single-process loopback tool (CON-015), so there is
    #: no second worker to miss the map.
    #: Werkzeug's development server is threaded by default, so two requests
    #: from two browser tabs really do interleave. Every mutation of
    #: ``_pending_selections`` and of the per-book lists inside it is taken
    #: under this lock (review cycle 2, F-005). It is deliberately *not*
    #: re-entrant and never held across a call that takes it again: the three
    #: helpers below acquire it, do one dict operation and release.
    _pending_selections_lock = threading.Lock()

    _PENDING_SELECTION_TOKENS = 32
    _PENDING_SELECTION_KEY = "book_selection_token"
    _pending_selections: "OrderedDict[str, dict]" = OrderedDict()

    def _selection_store(create=False):
        """This browser session's pending-selection map, or ``None``.

        ``create`` mints a token when there is none (or when the one the
        cookie carries has been evicted), which is the only thing this ever
        writes into the session.
        """
        token = session.get(_PENDING_SELECTION_KEY)
        with _pending_selections_lock:
            store = _pending_selections.get(token) if token else None
            if store is not None:
                _pending_selections.move_to_end(token)
                return store
            if not create:
                return None
            token = secrets.token_urlsafe(9)
            store = {}
            _pending_selections[token] = store
            while len(_pending_selections) > _PENDING_SELECTION_TOKENS:
                _pending_selections.popitem(last=False)
        session[_PENDING_SELECTION_KEY] = token
        # A cookie written before F-004 carried the ids themselves. Drop it
        # rather than leave a kilobyte of dead weight in every request.
        session.pop("book_selection", None)
        return store

    def _selected_tab():
        """The longest-side tab in force, defaulting to the first one.

        Read from ``request.values`` so it survives both a ``?bucket=`` link
        and the hidden field a submission of the step carries back.
        """
        return _TABS_BY_LABEL.get((request.values.get("bucket") or "").strip(), PLAN_BUCKETS[0])

    def _tab_query(label, offset=0):
        """The query a tab switch or a page move lands on.

        The tab, the filters in force, the page size if it was asked for, and
        the page being moved to. The move is a POST followed by this redirect,
        so every tab *and every page of one* is a real URL and the browser's
        back/forward buttons walk them.
        """
        query = {"bucket": label}
        for field in _SELECT_FILTERS:
            value = (request.form.get(field) or "").strip()
            if value:
                query[field] = value
        page_size = (request.form.get("limit") or "").strip()
        if page_size:
            query["limit"] = page_size
        if offset:
            query["offset"] = offset
        return query

    def _kept_selection(book_id):
        """The puzzle ids ticked so far for this book (AC-211).

        Held server-side for this browser session (see
        ``_pending_selections``), not written to the book: a tab switch or a
        page move commits nothing, and the step still joins the puzzles to the
        book once, when "Add selected" is pressed.
        """
        store = _selection_store()
        with _pending_selections_lock:
            return [str(pid) for pid in (store or {}).get(book_id, [])]

    def _keep_selection(book_id, puzzle_ids):
        store = _selection_store(create=True)
        kept = list(dict.fromkeys(str(pid) for pid in puzzle_ids))
        with _pending_selections_lock:
            store[book_id] = kept

    def _drop_selection(book_id):
        """Forget every tick kept for this book (the "Clear all selected"
        control, and the commit that has just written them to the book)."""
        store = _selection_store()
        if store is not None:
            with _pending_selections_lock:
                store.pop(book_id, None)

    def _fold_tab_into_selection(book_id):
        """Fold the tab just submitted into the kept selection and return it.

        ``puzzle_ids`` are the tiles ticked on that tab and ``shown_ids`` every
        tile it offered, so a tile the owner unticked is dropped while every
        other tab's choice is left alone (AC-211).
        """
        ticked = request.form.getlist("puzzle_ids")
        shown = set(request.form.getlist("shown_ids"))
        kept = [pid for pid in _kept_selection(book_id) if pid not in shown]
        _keep_selection(book_id, kept + ticked)
        return _kept_selection(book_id)

    def _selected_cells(book, kept_ids):
        """``selection_cells`` over what the book holds plus what is ticked."""
        records = {}
        for puzzle_id in list(book.puzzle_ids) + list(kept_ids):
            if puzzle_id in records:
                continue
            record = puzzle_review.get_puzzle(puzzle_id)
            if record:
                records[puzzle_id] = record
        return selection_cells(records.values())

    def _tier_figures(selected, planned, keys_of_tier):
        """``(per-tier figures, total figure)`` for one row of the summary.

        ``keys_of_tier`` maps each tier to the ``(bucket, tier)`` cells that
        feed it — one bucket's row for a tab, all four for the whole book.
        ``planned`` is None for a book with no stored plan, and then every
        planned figure is None too: the screen shows the selected counts alone
        and points at Print setup (ADR-0035's remedy).
        """
        def figure(label, got, want):
            return {
                "label": label,
                "selected": got,
                "planned": want,
                "over": want is not None and got > want,
            }

        rows = [
            figure(
                tier.value,
                sum(selected[key] for key in keys_of_tier[tier]),
                None if planned is None else sum(planned[key] for key in keys_of_tier[tier]),
            )
            for tier in PLAN_TIERS
        ]
        total = figure(
            "total",
            sum(row["selected"] for row in rows),
            None if planned is None else sum(row["planned"] for row in rows),
        )
        return rows, total

    def _plan_progress(book, kept_ids):
        """Planned vs selected per tab and for the whole book (BK-UI-5)."""
        selected = _selected_cells(book, kept_ids)
        plan, _damaged = _readable_plan(book.book_id)
        planned = planned_cells(plan) if plan is not None else None

        tabs = []
        for bucket in PLAN_BUCKETS:
            rows, total = _tier_figures(
                selected, planned, {tier: ((bucket, tier),) for tier in PLAN_TIERS}
            )
            tabs.append(
                {
                    "bucket": bucket,
                    "label": bucket.label,
                    "tiers": rows,
                    "total": total,
                    "over": any(row["over"] for row in rows),
                }
            )
        book_rows, book_total = _tier_figures(
            selected,
            planned,
            {tier: tuple((bucket, tier) for bucket in PLAN_BUCKETS) for tier in PLAN_TIERS},
        )
        return {
            "plan_present": planned is not None,
            "tab_progress": tabs,
            "book_progress": {"tiers": book_rows, "total": book_total},
        }

    def _is_in_tab(puzzle, bucket):
        """Does this puzzle belong on that tab? ``bucket_of`` alone decides.

        A row stored under an older size limit belongs to no tab rather than
        to the nearest one — the same verdict ``selection_cells`` makes.
        """
        try:
            return bucket_of(puzzle.get("width"), puzzle.get("height")) is bucket
        except SizeOutOfRange:
            return False

    def _tab_order(puzzle):
        """BK-UI-6: tier (easy, medium, hard), then shorter side ascending.

        An ungraded row sorts after every graded one; the id breaks the last
        tie so the order is stable between renders.

        This is the *cross-check*, not the mechanism: the order itself is
        ``puzzle_review.BOOK_TAB_SORT``, applied inside the store query so
        LIMIT/OFFSET page the tab in it (review cycle 2, F-001). The key this
        returns is that sort spelled in Python, term for term — tier rank from
        ``book_plan.TIERS``, ``min`` then ``max`` of the extent pair, then the
        id as a string — so re-sorting a page by it can only ever return the
        page it was handed.
        """
        tier = tier_of_record(puzzle.get("difficulty_tier"))
        rank = PLAN_TIERS.index(tier) if tier in PLAN_TIERS else len(PLAN_TIERS)
        width, height = puzzle.get("width") or 0, puzzle.get("height") or 0
        return (rank, min(width, height), max(width, height), str(puzzle.get("id")))

    @app.route("/book/<book_id>/select-puzzles", methods=["GET", "POST"])
    def select_puzzles_for_book(book_id):
        """Select and add puzzles to a book (Step 2 of scaffolding).

        CARD-122: one tab per longest-side bucket (FR-036). The tab in force is
        ``?bucket=<label>``, the ticked ids are kept server-side so that
        switching tabs or pages never drops them, and both the tab's header and
        the whole-book summary above the tabs read planned vs selected from the
        book's stored plan.

        A tab is a *query*, not a page slice: the store is asked for the rows
        whose longest side is in the bucket, so LIMIT applies to the tab's own
        members and the pages below the list reach all of them (review cycle 1,
        F-001/F-002).
        """
        book = book_mgr.get_book(book_id)
        if not book:
            flash("Book not found", "error")
            return redirect(url_for("books_list"))

        if request.method == "POST":
            if request.form.get("go_clear") is not None:
                # "Clear all selected": the one control that drops the whole
                # pending set. Before the fold, deliberately — the ticks on
                # this page are part of what is being cleared (F-003).
                _drop_selection(book_id)
                flash("Cleared the pending selection.", "info")
                return redirect(
                    url_for(
                        "select_puzzles_for_book",
                        book_id=book_id,
                        **_tab_query(_selected_tab().label),
                    )
                )

            kept_ids = _fold_tab_into_selection(book_id)
            switch_to = request.form.get("go_bucket")
            go_offset = request.form.get("go_offset")
            go_filter = request.form.get("go_filter")
            if switch_to is not None or go_offset is not None or go_filter is not None:
                # A tab switch, a page move or an applied filter: the selection
                # is now kept, nothing is committed. A switch starts the new tab
                # at its first page, a page move stays on the page it names, and
                # a filter change goes back to page 1 of the same tab because
                # the page numbers it left belong to the *old* result set.
                if switch_to is not None:
                    target, offset = _TABS_BY_LABEL.get(switch_to.strip(), PLAN_BUCKETS[0]), 0
                elif go_filter is not None:
                    target, offset = _selected_tab(), 0
                else:
                    target = _selected_tab()
                    try:
                        offset = max(0, int(go_offset))
                    except (TypeError, ValueError):
                        offset = 0
                return redirect(
                    url_for(
                        "select_puzzles_for_book",
                        book_id=book_id,
                        **_tab_query(target.label, offset),
                    )
                )

            if not kept_ids:
                flash("No puzzles selected. Please select at least one puzzle.", "info")
            else:
                try:
                    # Add puzzles to the book
                    if book_mgr.add_puzzles_to_book(book_id, kept_ids):
                        _drop_selection(book_id)
                        flash(f"Added {len(kept_ids)} puzzle(s) to book", "success")
                        # Proceed to Step 3: Puzzle Arrangement
                        return redirect(url_for("arrange_puzzles_in_book", book_id=book_id))
                    else:
                        flash("Book not found", "error")
                except ValueError as e:
                    flash(f"Error: {str(e)}", "error")
            book = book_mgr.get_book(book_id) or book

        # The tab replaces the size-range filter (BK-UI-6); the rest still
        # apply inside it. Read from request.values so a submission that was
        # not committed comes back on the same tab under the same filters.
        bucket = _selected_tab()
        difficulty = request.values.get("difficulty")
        quality_min = request.values.get("quality_min", type=int)
        theme = request.values.get("theme")
        status = request.values.get("status", "approved")  # Default to approved only
        puzzle_name = request.values.get("puzzle_name")
        limit = request.values.get("limit", _SELECT_PAGE, type=int)
        offset = request.values.get("offset", 0, type=int)

        # The size-range filter this step used to carry is gone (AC-216). A
        # bookmark that still names it is answered, not silently re-read as
        # the default tab (review cycle 1, F-009).
        retired = [name for name in _RETIRED_SIZE_PARAMS if request.args.get(name)]
        if retired:
            flash(
                f"The size filter is gone from this step: {', '.join(retired)} was ignored. "
                f"Pick a longest-side tab instead.",
                "info",
            )

        kept_ids = _kept_selection(book_id)
        context = {
            "book": book,
            "buckets": PLAN_BUCKETS,
            "current_bucket": bucket,
            "selected_ids": set(kept_ids),
            "kept_count": len(kept_ids),
            "difficulty": difficulty,
            "quality_min": quality_min,
            "theme": theme,
            "status": status,
            "puzzle_name": puzzle_name,
            "limit": limit,
            "offset": offset,
            **_plan_progress(book, kept_ids),
        }

        # Build filter: exclude puzzles already in this book
        try:
            filter_opts = PuzzleFilter(
                # The tab *is* the query: the store keeps the rows whose
                # longest side falls in the bucket, so LIMIT/OFFSET page the
                # tab's own members rather than a wider "either side in range"
                # superset that the route would then have to throw away (F-001).
                # The (low, high) pair still comes from book_plan's bucket and
                # from nowhere else, and bucket_of below still names the tab —
                # there is no second threshold table (G-1, EC-024).
                longest_side_range=(bucket.low, bucket.high),
                # ...and so is the tab's *order* (AC-215). The store sorts
                # before it counts and slices, so LIMIT/OFFSET cut pages out
                # of the tier-then-shorter-side sequence instead of out of the
                # store's default batch order — which is what made the tier
                # sequence restart at easy on page 2 while the route re-sorted
                # each page in isolation (review cycle 2, F-001).
                sort_by=BOOK_TAB_SORT,
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

            # Three cross-checks over a page the query already decided, all
            # provable no-ops — kept because they are what says the query and
            # the domain functions agree, out loud and per render:
            #   * `book_id is None` restates `book_id="unassigned"` (G-3);
            #   * `_is_in_tab` restates `longest_side_range=(low, high)` — with
            #     the buckets partitioning MIN_SIZE..MAX_SIZE, a row whose
            #     longest side is in [low, high] is a row `bucket_of` puts on
            #     this tab (G-1, EC-024);
            #   * `_tab_order` restates `BOOK_TAB_SORT` term for term.
            # None of them can eat a row or move one any more: the slice they
            # are handed is already the tab's own members in the tab's own
            # order. They are the *last* three operations applied to
            # `result.puzzles`; the figures below take the store's own count
            # and offset and never the surviving slice, and the planned-vs-
            # selected summary is computed from book membership plus the kept
            # ticks, which no page of any tab bounds.
            filtered_puzzles = sorted(
                (
                    p for p in result.puzzles
                    if p.get("book_id") is None and _is_in_tab(p, bucket)
                ),
                key=_tab_order,
            )

            context.update(
                puzzles=filtered_puzzles,
                # The tab's own total, from the store's count of the same
                # query — never the surviving slice of a page (F-002).
                total_count=result.total_count,
                has_more=result.has_more,
                pagination=_page_window(result.total_count, result.limit, result.offset),
            )

            return render_template("book_select_puzzles.html", **context)

        except ValueError as e:
            flash(f"Filter error: {str(e)}", "error")
            context.update(
                puzzles=[], total_count=0, has_more=False, pagination=None, error=str(e)
            )
            return render_template("book_select_puzzles.html", **context)

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
                    # Clear cover image (stored in session). Both keys: popping
                    # only the path left the "uploaded" flag set, so the screen
                    # kept saying a cover was uploaded after it was removed.
                    stored = _stored_cover_path(book_id)
                    session.pop(f"book_{book_id}_cover_path", None)
                    session.pop(f"book_{book_id}_cover_data", None)
                    if stored is not None:
                        stored.unlink(missing_ok=True)
                    flash("Cover image cleared", "success")

                elif action == "save_and_finish":
                    # Mark book as ready and return to books list
                    book_mgr.set_book_status(book_id, BookStatus.READY_FOR_PDF.value)
                    flash(f"Book saved: {book.metadata.title}", "success")
                    return redirect(url_for("books_list"))

                elif action == "download_pdf":
                    # Download one of the export's two files (FR-043): the
                    # form's ``part`` names which, interior by default.
                    return generate_book_pdf_download(
                        book, puzzle_review, request.form.get("part")
                    )

            except Exception as e:
                flash(f"Error: {str(e)}", "error")

        # Handle cover upload
        if "cover" in request.files:
            file = request.files["cover"]
            if file and file.filename:
                try:
                    cover_path = _store_uploaded_cover(book_id, file.stream)
                    # The session keeps the stored file's path (a Pillow Image
                    # can't be serialized); every export route reads it back.
                    session[f"book_{book_id}_cover_path"] = str(cover_path)
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

        # "Cover uploaded" is whether the stored file is still there, not
        # whether the session says one was uploaded: the file lives in a temp
        # dir the OS may purge while the signed cookie outlives it, and the
        # export would then print the title cover under a screen promising
        # the owner's art (CARD-135 review F-001).
        if _forget_stale_cover(book_id):
            flash(
                "Your uploaded cover image is no longer on disk. Upload it "
                "again, or the cover file will be a generated title cover.",
                "warning",
            )

        context = {
            "book": book,
            "puzzles": puzzles_in_book,
            "puzzle_count": len(puzzles_in_book),
            "easy_count": easy_count,
            "medium_count": medium_count,
            "hard_count": hard_count,
            # The interior's pages only — guide, puzzles, SOLUTIONS divider and
            # answers; the cover file is never counted (FR-043, FR-030). The
            # export's own page plan, so the two share one set of layout
            # rules; a puzzle that fails to render still makes this an upper
            # bound — CARD-129 owns the exact equality (EC-034).
            "page_count": interior_page_count(len(puzzles_in_book)),
            "cover_uploaded": _uploaded_cover_file(book_id) is not None,
            "trim_width_cm": book.metadata.size.split("×")[0] if book.metadata.size else PrintSpecValidator.DEFAULT_TRIM_WIDTH_CM,
            "trim_height_cm": book.metadata.size.split("×")[1] if book.metadata.size and "×" in book.metadata.size else PrintSpecValidator.DEFAULT_TRIM_HEIGHT_CM,
        }

        return render_template("book_finalize.html", **context)

    def _cover_dir() -> Path:
        """Where uploaded book covers are kept between upload and export."""
        return Path(
            app.config.get("BOOK_COVER_DIR")
            or Path(tempfile.gettempdir()) / "nonogram_book_covers"
        )

    def _cover_file_for(book_id) -> Path:
        """The one stored-cover file of ``book_id``, named from the id alone.

        The name is per book, not per session: the admin panel has a single
        owner, so a second upload for a book replaces the first on purpose.
        """
        safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(book_id))
        return _cover_dir() / f"{safe_id}_cover.png"

    def _store_uploaded_cover(book_id, stream) -> Path:
        """Decode an uploaded cover and keep it for the book's exports.

        Until CARD-135 the upload was decoded, its *filename* put in the
        session, and the image itself dropped — so no export could ever print
        it. The decoded image is turned upright by its EXIF orientation (a
        phone photo is stored sideways with a rotate tag that PNG does not
        carry), re-encoded as PNG under a name built from the book id (never
        the client's filename), and the session holds that path.
        """
        image = PILImage.open(stream)
        image.load()
        image = PILImageOps.exif_transpose(image)
        path = _cover_file_for(book_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        image.convert("RGB").save(path, format="PNG")
        return path

    def _stored_cover_path(book_id):
        """The session's stored cover file for this book, if it is one of ours.

        Only a file inside :func:`_cover_dir` is honoured, so a session value
        can never make an export read, or a clear delete, anything else.
        """
        stored = session.get(f"book_{book_id}_cover_path")
        if not stored:
            return None
        path = Path(stored).resolve()
        if path.parent != _cover_dir().resolve():
            return None
        return path

    def _uploaded_cover_file(book_id):
        """The uploaded cover's file if it still exists inside the cover dir.

        The single test of "a cover is uploaded" — for the Finalise screen
        and for every export. The session only says where the file was put;
        the file itself can be gone (a purged temp dir), and then no cover is
        uploaded, whatever the session says.
        """
        path = _stored_cover_path(book_id)
        if path is None or not path.is_file():
            return None
        return path

    def _cover_upload_lost(book_id) -> bool:
        """Whether the session claims an uploaded cover whose file is gone."""
        claims = session.get(f"book_{book_id}_cover_path") or session.get(
            f"book_{book_id}_cover_data"
        )
        return bool(claims) and _uploaded_cover_file(book_id) is None

    def _forget_stale_cover(book_id) -> bool:
        """Drop a session cover claim whose file is gone; True if one was dropped.

        Only the session keys are removed — a path outside the cover dir is
        never unlinked.
        """
        if not _cover_upload_lost(book_id):
            return False
        session.pop(f"book_{book_id}_cover_path", None)
        session.pop(f"book_{book_id}_cover_data", None)
        return True

    def _uploaded_cover(book_id):
        """The cover uploaded on Finalise for this book, or None if none is set."""
        path = _uploaded_cover_file(book_id)
        if path is None:
            return None
        with PILImage.open(path) as image:
            return image.convert("RGB")

    def _book_puzzles(book):
        """The book's puzzles in book order; missing ones are logged and skipped."""
        puzzles = []
        for puzzle_id in book.puzzle_ids:
            puzzle = puzzle_review.get_puzzle(puzzle_id)
            if puzzle:
                puzzles.append(puzzle)
            else:
                app.logger.warning("Could not find puzzle %s for PDF generation", puzzle_id)
        app.logger.debug(
            "Total puzzles retrieved: %d/%d", len(puzzles), len(book.puzzle_ids)
        )
        return puzzles

    def _export_part(book, part, puzzles=None):
        """Render one file of the book's export (FR-043) — every route's path.

        Only the requested file is rendered: the interior (puzzles in book
        order, no cover page) or the cover (the uploaded cover when its file
        exists, else the generated title cover). ``puzzles`` may be passed
        by a caller that has already fetched them.
        """
        generator = BookPDFGenerator()
        if part == "interior":
            if puzzles is None:
                puzzles = _book_puzzles(book)
            return generator.export_interior(puzzles)
        return generator.export_cover(
            book.metadata.title, _uploaded_cover(book.book_id)
        )

    #: Refusal text when the session claims a cover whose file is gone.
    _LOST_COVER_MESSAGE = (
        "Your uploaded cover image is no longer on disk, so the cover file "
        "would be a generated title cover instead. Upload the cover again on "
        "the Finalise screen, or remove it there to use the title cover."
    )

    #: The two files of a book export a download may ask for (FR-043).
    _EXPORT_PARTS = ("interior", "cover")

    def _requested_part(part):
        """The export part asked for — interior when unspecified, None if unknown."""
        part = (part or "interior").strip().lower()
        return part if part in _EXPORT_PARTS else None

    def _send_export_part(pdf_bytes, part, stem):
        """One export file as a PDF attachment named ``<stem>_<part>.pdf``."""
        pdf_bytes.seek(0)
        return send_file(
            pdf_bytes,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"{stem}_{part}.pdf",
        )

    def generate_book_pdf_download(book, puzzle_review, part=None):
        """Export the book and return the requested part as a download."""
        back = request.referrer or url_for("book_detail", book_id=book.book_id)
        requested = _requested_part(part)
        if requested is None:
            flash(f"Unknown export part {part!r}: choose interior or cover", "error")
            return redirect(back)
        if requested == "cover" and _cover_upload_lost(book.book_id):
            flash(_LOST_COVER_MESSAGE, "error")
            return redirect(back)

        try:
            pdf_bytes = _export_part(book, requested)
            timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
            return _send_export_part(pdf_bytes, requested, f"book_{timestamp}")

        except Exception as e:
            flash(f"Failed to generate PDF: {str(e)}", "error")
            return redirect(back)

    @app.route("/book/<book_id>/download-pdf", methods=["POST"])
    def download_book_pdf(book_id):
        """Download the book's interior PDF, or its cover with ``?part=cover``."""
        book = book_mgr.get_book(book_id)
        if not book:
            flash("Book not found", "error")
            return redirect(url_for("books_list"))

        return generate_book_pdf_download(
            book, puzzle_review, request.values.get("part")
        )

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
            # The book's stored cover goes with it (its name is built from
            # the id alone, never from the session), and so does the claim.
            session.pop(f"book_{book_id}_cover_path", None)
            session.pop(f"book_{book_id}_cover_data", None)
            try:
                _cover_file_for(book_id).unlink(missing_ok=True)
            except OSError as e:
                app.logger.warning("Could not remove cover of deleted book %s: %s", book_id, e)
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
        """Generate the book's export and download one part of it.

        The interior PDF by default, the cover file with ``?part=cover``.
        Until CARD-135 this route went through ``admin/pdf_generator``'s
        reportlab generator — a different book altogether (title page, table
        of contents, no guide or answer pages) — so the same book exported
        differently depending on the button pressed. It now runs the same
        :class:`BookPDFGenerator` export as the other two routes (FR-043).
        """
        book = book_mgr.get_book(book_id)
        if not book:
            flash("Book not found", "error")
            return redirect(url_for("books_list"))

        if len(book.puzzle_ids) == 0:
            flash("Cannot generate PDF for book with no puzzles", "error")
            return redirect(url_for("book_detail", book_id=book_id))

        part = _requested_part(request.values.get("part"))
        if part is None:
            flash("Unknown export part: choose interior or cover", "error")
            return redirect(url_for("book_detail", book_id=book_id))

        if part == "cover" and _cover_upload_lost(book_id):
            flash(_LOST_COVER_MESSAGE, "error")
            return redirect(url_for("book_detail", book_id=book_id))

        try:
            puzzles = _book_puzzles(book)
            if not puzzles:
                flash("No valid puzzles found for book", "error")
                return redirect(url_for("book_detail", book_id=book_id))

            pdf_bytes = _export_part(book, part, puzzles)

            if part == "interior":
                # Only the interior is "the book's PDF": a cover-only download
                # records nothing. (In production, save to S3 or similar.)
                book_mgr.set_pdf_url(book_id, f"PDF generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}")
                flash("PDF generated successfully!", "success")

            return _send_export_part(
                pdf_bytes, part, book.metadata.title.replace(" ", "_")
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
        # CARD-068: the batch page offers this too now, and lands back on the
        # batch rather than dropping the owner into the global library
        # mid-review — the same `?batch_id=` the Approve and Reject forms beside
        # it have always posted.
        batch_id = request.args.get("batch_id")

        def done():
            if batch_id:
                return redirect(url_for("generated_puzzles", batch_id=batch_id))
            return _back_to_puzzles_list()

        puzzle = puzzle_review.get_puzzle(puzzle_id)

        if not puzzle:
            flash("Puzzle not found", "error")
            return done()

        # Only allow deletion of rejected puzzles
        if puzzle.get("status") != "rejected":
            flash("Only rejected puzzles can be deleted", "error")
            return done()

        # Only allow deletion if not in a book. Two questions, because they
        # have two different answers: the puzzle row's own `book_id`, and the
        # book side that actually records membership. Production writes only
        # the second, so the first alone would delete a puzzle a book is built
        # on and leave the book pointing at nothing (CARD-100). This route
        # destroys something, so it asks both.
        listing_book = book_mgr.book_listing(puzzle_id)
        if puzzle.get("book_id") or listing_book:
            flash("Cannot delete puzzle that is in a book", "error")
            return done()

        if puzzle_review.delete_puzzle(puzzle_id):
            flash("Puzzle deleted", "success")
        else:
            flash("Puzzle not found", "error")

        return done()

    @app.route("/puzzle/<puzzle_id>/restore", methods=["POST"])
    def restore_puzzle(puzzle_id):
        """Restore rejected or approved puzzle back to draft."""
        if puzzle_review.in_a_book(puzzle_id):
            flash("Cannot restore a puzzle that is in a book", "error")
        elif puzzle_review.restore_puzzle(puzzle_id):
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
