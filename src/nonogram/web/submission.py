"""One posted form, read into an ``orchestrator.GenerationRequest``.

This module is the web adapter's counterpart of ``cli._run_generate``'s
request-assembly block, and it is deliberately as thin as that one: it turns
the bytes of an ``application/x-www-form-urlencoded`` body into the boundary
type the orchestrator takes, and it decides nothing about the *values* it
carries (ADR-0019/R1, guardrail G-2). A ``size`` box holding ``60`` produces a
request carrying 60, which the domain refuses inward with the same error a
``--size 60`` argv earns (AC-050) — that is what makes the two adapters tell
one story by construction instead of by parallel maintenance.

Five things happen here, and each of them is the *same* thing ``cli.py`` does
in its own idiom. Nothing else does.

**Blank means absent.** ``urllib.parse.parse_qs`` (ADR-0020) drops a field
whose value is empty, which is its documented default, and that default is
exactly the semantics an HTML form needs: a text box left alone and a
``<select>`` on its blank option are how a browser spells "this flag was not
passed", and there is no other spelling available to it. So an untouched
``name`` box is ``None`` — the auto-generated name (FR-015) — rather than the
empty string. A name that is *present* and unusable still travels inward and
is still refused there: posting ``name=%20`` builds a request carrying
``" "`` and earns ``InvalidPuzzleName``, because whether a name is usable is
FR-015's rule and not this module's (AC-045).

**One number is one number** (:data:`_NUMERIC_FIELDS`). ``int`` is applied to
``size``, ``density`` and ``seed`` and nothing else is: that conversion is the
web spelling of argparse's ``type=int``, which is syntax, and the range each
value has to be in is a domain rule that this module must not know (CON-011,
ADR-0022/R2). A value ``int`` cannot read at all — ``twenty`` — is refused
here rather than inward, for the same reason argparse refuses it rather than
passing a string through a field typed ``int | None``: it is not a number, so
there is no number to send anywhere. ``int``'s own tolerances (a leading sign,
surrounding whitespace, ``_`` separators) come along unmodified, exactly as
they do in ``cli._extent_token``, and every value they admit still meets the
range rule inward.

**A mode has to be a mode this form offers** (:data:`nonogram.web.pages.MODES`),
**and an export format has to be a format this build registers**
(``export.FORMATS``). The two value-shaped checks in this module, and both are
here because the domain put them here. ``sourcing.for_mode`` documents that "a
user typing an unsupported mode is rejected by argparse's ``choices`` at the
adapter", and ``export.for_format`` says the same of a format in the same
words; each raises a bare ``ValueError`` — pointedly *not* a ``NonogramError``
— for a value that reaches it anyway, which is a contract the adapter is
obliged to discharge, not an error it may forward. ``cli.py`` discharges both
with ``choices=`` (``["random", "library", "image"]`` and ``list(FORMATS)``); a
web adapter with no equivalent turns a hand-written ``mode=bogus`` or
``export_formats=bogus`` into an unhandled exception rather than a page, which
is what EC-003 forbids — and for the format, into a *partial* export, since
``png&bogus`` writes the PNG before the second name is looked up. Each is
checked against the very list the form renders its own control from, so the
offered set and the accepted set are one object rather than two that agree
today.

**A field cannot carry a NUL.** ``%00`` decodes to a character no path can
hold: ``Path.mkdir`` answers it with a bare ``ValueError`` — again not an
``OSError`` and not a ``NonogramError`` — so an ``out=bad%00dir`` submission
would drop the connection. This is an asymmetry the *web* adapter introduces
rather than one it inherits: a NUL cannot appear in argv at all, so ``cli.py``
has never had a way to reach that call. Refusing it in every field rather than
in ``out`` alone keeps this module free of a per-field rule, and costs nothing
a form can express: no keyboard produces one and no browser sends one.

What is deliberately *not* here: any range, any tier vocabulary, any judgement
about a library key, and any reading of an ``image`` field. The first three are
the domain's (AC-050, AC-021, AC-006). The fourth is CARD-021's: an upload is a
``multipart/form-data`` control, the form renders no such field, and this
module never fills ``GenerationRequest.image`` — a request from the web is an
``image``-mode request only if it says so, and then fails inward with the
``--image``-is-missing error that request deserves (AC-008).
"""

from __future__ import annotations

import urllib.parse
from dataclasses import dataclass
from pathlib import Path

from nonogram import export, orchestrator
from nonogram.web import pages

__all__ = ["DEFAULT_MODE", "Submission", "read"]

#: The ``mode`` a submission that names none is read as, mirroring
#: ``cli.build_parser``'s ``--mode`` default rather than inventing a second
#: one. The form's ``<select>`` always posts a value, so this covers the
#: hand-written body only.
DEFAULT_MODE = "random"

#: The fields ``int`` is applied to, and the whole of that list. Everything
#: else is carried as the string it was posted as.
_NUMERIC_FIELDS = ("size", "density", "seed")


@dataclass(frozen=True, slots=True)
class Submission:
    """What :func:`read` could make of one posted body.

    Exactly one of the two attributes is filled. Split this way rather than
    raising because the web package originates no exception of its own — it
    translates failures, and a body it cannot read is a failure to translate,
    reported to the caller as data and rendered as a page.

    Attributes:
        request: The run as the form asked for it, unvalidated, or ``None``
            when ``unreadable`` says why it could not be built.
        unreadable: One sentence per field that could not be read at all,
            empty when ``request`` is filled. Each names the field and what was
            posted for it, so the page can say which box to go and fix.
    """

    request: orchestrator.GenerationRequest | None
    unreadable: tuple[str, ...] = ()


def _one(fields: dict[str, list[str]], field: str) -> str | None:
    """The value of a single-valued ``field``, or ``None`` if it was not sent.

    The *last* value when a body carries several, which is argparse's answer
    for a flag repeated without ``action="append"`` — the two adapters give the
    same reading of the same accident. ``None`` covers both "no such field" and
    "sent blank", since :func:`urllib.parse.parse_qs` has already dropped the
    latter.
    """
    values = fields.get(field)
    return values[-1] if values else None


def read(body: str) -> Submission:
    """Read one urlencoded form body into a generation request.

    Args:
        body: The decoded request body, as posted by the form.

    Returns:
        A :class:`Submission` carrying the request, or carrying the reasons
        the body could not be read as one. Never raises: a body that is not a
        form at all parses to no fields and produces a request with everything
        unset, which the domain then refuses for having no grid extent — the
        same answer ``nonogram generate`` with no ``--size`` gives.
    """
    fields = urllib.parse.parse_qs(body)
    unreadable: list[str] = []

    for field, values in sorted(fields.items()):
        for value in values:
            if "\x00" in value:
                unreadable.append(f"{field}: a value may not contain a NUL character")
                break

    numbers: dict[str, int | None] = {}
    for field in _NUMERIC_FIELDS:
        raw = _one(fields, field)
        if raw is None:
            numbers[field] = None
            continue
        try:
            numbers[field] = int(raw)
        except ValueError:
            numbers[field] = None
            unreadable.append(f"{field}: expected a whole number, got {raw!r}")

    mode = _one(fields, "mode") or DEFAULT_MODE
    if mode not in pages.MODES:
        unreadable.append(
            f"mode: expected one of {', '.join(pages.MODES)}, got {mode!r}"
        )

    formats = tuple(fields.get("export_formats", ()))
    for name in formats:
        if name not in export.FORMATS:
            unreadable.append(
                f"export_formats: expected one of {', '.join(export.FORMATS)}, "
                f"got {name!r}"
            )

    if unreadable:
        return Submission(None, tuple(unreadable))

    out = _one(fields, "out")
    return Submission(
        orchestrator.GenerationRequest(
            mode=mode,
            # The one decision this card had to take that its own text does not
            # make (see CARD-020's worktree notes). The form has a single size
            # box, and since FR-023 a single number is not a synonym for a
            # square: ``(N, None)`` states one side and leaves the other to be
            # derived from the source's own shape, while ``(N, N)`` forces a
            # square. This is the bare reading — byte-for-byte what
            # ``cli._extent_token`` makes of a bare ``--size N`` — because
            # FR-017 puts the *same* options on both adapters, and a web box
            # that meant "square" would be the one option whose meaning changed
            # on the way through the browser.
            width=numbers["size"],
            height=None,
            density=numbers["density"],
            library_key=_one(fields, "library_key"),
            # ``image`` is never filled: see the module docstring (CARD-021).
            name=_one(fields, "name"),
            difficulty=_one(fields, "difficulty"),
            seed=numbers["seed"],
            # Several checkboxes share one name, which is the HTML spelling of
            # ``--export``'s ``action="append"``; every box ticked is one
            # format requested, in the order the form lists them. Checked
            # against ``export.FORMATS`` above for the reason ``mode`` is
            # checked against ``pages.MODES`` — see the module docstring.
            export_formats=formats,
            out=Path(out) if out is not None else None,
        )
    )
