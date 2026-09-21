"""Hold an uploaded picture between a failed submission and its retry (CARD-037).

The one question this module answers: *which file on this server does this
token stand for?* — and the only tokens it answers for are ones it minted.

Why a token and not the path
----------------------------
A retry needs the browser to say "the same picture as last time". The obvious
way is a hidden field carrying the temp file's path, and that is what the
2026-09-04 branch did (kept as
``meta/ops/CARD-037-uncommitted-work-20260921.patch``)::

    persisted_path = Path(fields["persisted_image_path"][0])
    if persisted_path.exists() and persisted_path.is_file():
        image_path = persisted_path

``fields`` is the submitted body, so every value in it is chosen by whoever
sent the request. That accepts a filesystem path from the client and opens it
as the picture to convert: any readable image on the server becomes a puzzle,
and for anything else the response still distinguishes "exists" from "does
not". The same hazard is refused elsewhere in this adapter on purpose — a
urlencoded ``image=<path>`` is not read as a picture (CARD-032, AC-130).

So the client is given an opaque token instead. It carries no information
about the file, it cannot be constructed, and :func:`resolve` answers only for
tokens this process created. A path submitted in its place is simply a string
that was never minted, and resolves to nothing.

Lifetime
--------
The store lives in the process, like the server itself: ``nonogram.web`` is one
synchronous loopback process (ADR-0021), so there is nothing to share and
nothing to coordinate. A retained file is deleted when its submission
succeeds, when the store evicts it, or when the process ends and the
system's temp directory is cleaned in the usual way.

It is bounded by count rather than by time. A clock would need a sweeper to run
somewhere, and this server has no scheduler; :data:`MAX_RETAINED` is a small
number because the thing being remembered is "the picture I was just looking
at", and nobody has more than a few of those.
"""

from __future__ import annotations

import secrets
from collections import OrderedDict
from pathlib import Path

__all__ = ["MAX_RETAINED", "clear", "release", "resolve", "retain"]

#: How many uploads are held at once. Retaining past this deletes the oldest,
#: file included — a retry that has been abandoned for that many submissions is
#: not coming back, and a browser that never returns must not leave a file on
#: disk for ever.
MAX_RETAINED = 8

#: Token -> retained file. Ordered so eviction is "the one retained longest
#: ago" without storing timestamps.
_RETAINED: "OrderedDict[str, Path]" = OrderedDict()


def retain(path: Path) -> str:
    """Hold ``path`` for a later retry and return the token that names it.

    Each call mints a new token, so the same file retained twice is reachable
    by two names. That is deliberate: the caller decides when a retention
    ends, and reusing a token would make one submission's success delete
    another's picture.
    """
    token = secrets.token_urlsafe(24)
    _RETAINED[token] = Path(path)
    while len(_RETAINED) > MAX_RETAINED:
        _, evicted = _RETAINED.popitem(last=False)
        evicted.unlink(missing_ok=True)
    return token


def resolve(token: object) -> Path | None:
    """The file this token stands for, or ``None``.

    ``None`` for anything this process did not mint — including a filesystem
    path, which is the case this design exists to refuse — and for a token
    whose file has since gone, so the store cannot claim to hold something it
    does not. A vanished file forgets its token rather than lingering as an
    entry that will never resolve.
    """
    if not isinstance(token, str) or not token:
        return None
    path = _RETAINED.get(token)
    if path is None:
        return None
    if not path.is_file():
        del _RETAINED[token]
        return None
    return path


def release(token: object) -> None:
    """Forget the token and delete its file. Safe to call more than once."""
    if not isinstance(token, str):
        return
    path = _RETAINED.pop(token, None)
    if path is not None:
        path.unlink(missing_ok=True)


def clear() -> None:
    """Forget everything and delete every retained file.

    For tests, and for a caller that wants the store empty; the server has no
    shutdown hook of its own to call it from.
    """
    while _RETAINED:
        _, path = _RETAINED.popitem()
        path.unlink(missing_ok=True)
