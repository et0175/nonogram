"""One posted form, read into an ``orchestrator.GenerationRequest``.

This module is the web adapter's counterpart of ``cli._run_generate``'s
request-assembly block, and it is deliberately as thin as that one: it turns
the bytes of an ``application/x-www-form-urlencoded`` body into the boundary
type the orchestrator takes, and it decides nothing about the *values* it
carries (ADR-0019/R1, guardrail G-2). A ``size`` box holding ``60`` produces a
request carrying 60, which the domain refuses inward with the same error a
``--size 60`` argv earns (AC-050) — that is what makes the two adapters tell
one story by construction instead of by parallel maintenance.

Six things happen here, and each of them is the *same* thing ``cli.py`` does
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
``density`` and ``seed`` and nothing else is: that conversion is the web
spelling of argparse's ``type=int``, which is syntax, and the range each value
has to be in is a domain rule that this module must not know (CON-011,
ADR-0022/R2). A value ``int`` cannot read at all — ``twenty`` — is refused
here rather than inward, for the same reason argparse refuses it rather than
passing a string through a field typed ``int | None``: it is not a number, so
there is no number to send anywhere. ``int``'s own tolerances (a leading sign,
surrounding whitespace, ``_`` separators) come along unmodified, exactly as
they do in ``cli._extent_token``, and every value they admit still meets the
range rule inward.

**A size token is ``N`` or ``NxM``, and nothing else is** (:func:`_extent_token`,
CARD-028). The one field with a two-shape grammar rather than a single ``int``
conversion, because ``GenerationRequest`` carries two sides and the form has
one box for both — exactly the shape ``cli._extent_token`` already parses for
``--size``, reimplemented natively here rather than imported (see
:data:`_EXTENT_SEPARATOR`'s docstring on why an import is not available to this
module). A bare ``20`` yields ``(20, None)``; an explicit ``20x30`` yields
``(20, 30)``; anything that is neither shape (``30x``, ``x20``, ``3x4x5``,
``30X20``, ``30.5``) is refused here, the same wall ``argparse`` puts up for
the CLI (AC-064's web mirror). No range check is applied to either side: a
well-shaped but out-of-range token (``60``, ``60x60``) parses cleanly and
travels inward, where the domain refuses it with the same error a matching
``--size`` argv earns (AC-050, AC-065's web mirror).

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

What is deliberately *not* here: any range, any tier vocabulary, and any
judgement about a library key. Those are the domain's (AC-050, AC-021,
AC-006).

**``image`` is filled by a sibling, not by this module** (CARD-021). This
module's own :func:`read` — the ``application/x-www-form-urlencoded`` body a
non-upload submission posts — never carries a picture and always calls
:func:`from_fields` with ``image=None``, exactly as before CARD-021: a
urlencoded body from the CLI-mirrored fields alone has nowhere a picture could
come from. What CARD-021 adds is :func:`from_fields` itself, split out of
``read`` so :mod:`nonogram.web.multipart` — the module that reads a
``multipart/form-data`` body, lands its uploaded part in a temp file and
extracts every other field into the same ``{name: [values]}`` shape
``urllib.parse.parse_qs`` produces — can hand that shape and the temp file's
path to the *same* field-to-request mapping this module already had, rather
than re-deriving the extent-token grammar, the mode/export vocabulary checks
and the NUL guard a second time. A request built with no ``image`` (urlencoded,
or a multipart body with no uploaded file) is an ``image``-mode request only if
its ``mode`` field says so, and then fails inward with the ``--image``-is-
missing error that request deserves (AC-008) — unchanged by this split.
"""

from __future__ import annotations

import urllib.parse
from dataclasses import dataclass
from pathlib import Path

from nonogram import export, orchestrator
from nonogram.web import pages

__all__ = ["DEFAULT_MODE", "Submission", "from_fields", "read"]

#: The ``mode`` a submission that names none is read as, mirroring
#: ``cli.build_parser``'s ``--mode`` default rather than inventing a second
#: one. The form's ``<select>`` always posts a value, so this covers the
#: hand-written body only.
DEFAULT_MODE = "image"

#: The fields ``int`` is applied to directly, and the whole of that list.
#: ``size`` is deliberately not one of them (CARD-028): it has its own two-
#: shape grammar, read by :func:`_extent_token` below, rather than a single
#: ``int`` conversion. Everything else is carried as the string it was posted
#: as.
_NUMERIC_FIELDS = ("density", "seed")

#: The separator in a ``size`` field's ``WxH`` form (CARD-028). A byte-for-byte
#: duplicate of ``cli._EXTENT_SEPARATOR`` rather than an import of it: the
#: structural import guard in ``tests/test_cli.py`` forbids anything inward of
#: the CLI adapter — and ``web/`` is an adapter peer of ``cli``, not something
#: inward of it — from importing ``cli``, so the value is reimplemented here
#: and cross-checked against ``cli._EXTENT_SEPARATOR`` from the test tree,
#: exactly as :func:`_extent_token` below is cross-checked against
#: ``cli._extent_token`` (CLAUDE.md's stated precedent, ``solver/propagate.py``'s
#: ``mask_runs``).
_EXTENT_SEPARATOR = "x"


def _extent_token(text: str) -> tuple[int, int | None] | None:
    """Parse a ``size`` field into ``(width, height)``, mirroring ``cli._extent_token``.

    A native reimplementation of ``cli._extent_token``'s parsing rule, not an
    import of it (see :data:`_EXTENT_SEPARATOR`'s docstring and CARD-028's
    worktree notes on the card). ``"30x20"`` yields ``(30, 20)``; a bare
    ``"30"`` yields ``(30, None)`` — one number, because one number is what
    was posted, and the domain derives the other side from the source's own
    shape (FR-023, ADR-0022/R4). ``"30X20"`` (capital X) is not split — the
    separator is the lowercase literal in :data:`_EXTENT_SEPARATOR`, exactly
    as it is in ``cli.py`` — so it falls through to the single-token branch
    and is refused there for not being a whole number.

    Applies **no range check**, deliberately (ADR-0022/R2, guardrail G-2):
    ``"40x20"``, ``"0"``, ``"9"``, ``"31"`` and ``"-5"`` are all well-formed
    and all parse; each is refused inward by
    ``sourcing.random_grid.validate_extent``, exactly as it is for the CLI
    (AC-065's web mirror). ``int`` is applied to each half, which is what
    admits a leading sign, surrounding whitespace and ``_`` digit separators —
    ``int``'s own documented tolerances rather than a grammar of this
    module's own, exactly as in ``cli._extent_token``.

    Args:
        text: The ``size`` field's value, as posted.

    Returns:
        ``(width, height)`` for a well-formed ``N``/``NxM`` token, both
        unvalidated, or ``None`` when ``text`` is neither shape (``"30x"``,
        ``"x20"``, ``"3x4x5"``, ``"big"``, ``"30X20"``, ``""``, ``"x"``) —
        the same set ``cli._extent_token`` raises
        ``argparse.ArgumentTypeError`` for. Where the CLI's refusal becomes a
        usage error before any request exists (AC-064), this module's ``None``
        is reported by :func:`read` as an unreadable field, exactly as an
        unparseable ``density`` or ``seed`` already is — a malformed token
        never reaches the orchestrator, but an in-range-shaped, out-of-value
        one (``"60x60"``) parses cleanly here and travels inward for the
        domain to refuse, same as the CLI (AC-065's web mirror).
    """
    parts = text.split(_EXTENT_SEPARATOR)
    if len(parts) > 2:
        return None
    try:
        sides = [int(part) for part in parts]
    except ValueError:
        return None
    return (sides[0], sides[1]) if len(sides) == 2 else (sides[0], None)


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
    return from_fields(fields, image=None)


def from_fields(fields: dict[str, list[str]], *, image: Path | None = None) -> Submission:
    """Map ``{field name: posted values}`` onto a generation request.

    The part of :func:`read` that does not care where the fields came from,
    split out for CARD-021 so :mod:`nonogram.web.multipart` can reuse it
    verbatim for a ``multipart/form-data`` body's text parts rather than
    re-deriving the same grammar (see the module docstring). ``fields`` is the
    exact shape :func:`urllib.parse.parse_qs` produces — every value that was
    posted, in order, with a blank value already dropped by the caller
    (:func:`read`'s ``parse_qs`` call for a urlencoded body;
    ``nonogram.web.multipart.read`` reproduces that same "blank means absent"
    drop for a multipart body's text parts, so the rule holds either way).

    Args:
        fields: Every posted field, keyed by name.
        image: The path CARD-021's upload landed in a temp file, or ``None``
            when the body carried no uploaded picture (every urlencoded body,
            and a multipart body whose ``image`` part was empty or absent).
            Unvalidated, like the rest of this function's output — whether the
            path exists and decodes is the sourcing module's question
            (AC-008, guardrail G-4).

    Returns:
        The same :class:`Submission` contract :func:`read` documents.
    """
    unreadable: list[str] = []

    for field, values in sorted(fields.items()):
        for value in values:
            if "\x00" in value:
                unreadable.append(f"{field}: a value may not contain a NUL character")
                break

    width: int | None = None
    height: int | None = None
    raw_size = _one(fields, "size")
    if raw_size is not None:
        parsed_size = _extent_token(raw_size)
        if parsed_size is None:
            unreadable.append(
                f"size: expected N or N{_EXTENT_SEPARATOR}M with whole numbers, "
                f"got {raw_size!r}"
            )
        else:
            width, height = parsed_size

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
            # CARD-020's decision for the bare reading, extended to the explicit
            # form by CARD-028. The form's single size box now accepts both
            # shapes ``_extent_token`` does: a bare ``20`` states one side and
            # leaves the other for the domain to derive from the source's own
            # shape (``width=20, height=None`` — FR-023, ADR-0022/R4), and an
            # explicit ``20x30`` states both (``width=20, height=30``) exactly
            # as ``cli._extent_token`` reads the same two tokens. Neither reading
            # is ``(N, N)``, which forces a square and is a different request. An
            # unposted ``size`` field carries both as ``None``, the same "flag
            # omitted" the CLI's own ``--size`` absence leaves.
            width=width,
            height=height,
            density=numbers["density"],
            library_key=_one(fields, "library_key"),
            # The temp-file path CARD-021's upload landed, or ``None`` — the
            # caller's concern, not this function's (see the docstring above).
            image=image,
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
