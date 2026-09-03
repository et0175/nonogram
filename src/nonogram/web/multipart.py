"""Hand-rolled ``multipart/form-data`` parsing (CARD-021, ADR-0020).

The image-upload half of FR-017. ``cgi.FieldStorage`` — the standard library's
only multipart parser — was removed in Python 3.13 (PEP 594), and this
project's floor is 3.14, so there is no stdlib shortcut left: ADR-0020's answer
is to feed the reconstructed headers-plus-body to
:class:`email.parser.BytesParser`, which already implements RFC 2046 boundary
splitting and RFC 2231 parameter decoding, and read each part back out by hand.

**Getting exact bytes back out is the one genuinely sharp edge.**
``Message.get_payload()`` (no ``decode=``) is lossy for a binary part: internal
storage round-trips arbitrary bytes through ``str`` via
``bytes.decode("ascii", "surrogateescape")``, but the *undecoded* accessor
re-encodes that through the part's declared charset (``ascii`` when none is
declared) with ``errors="replace"`` — every byte 0x80-0xFF comes back as
``U+FFFD``, silently. ``Message.get_payload(decode=True)`` takes a different
path — it re-encodes the same internal ``str`` with
``errors="surrogateescape"`` again, which is the exact inverse of how it went
in — and an upload's part carries no ``Content-Transfer-Encoding`` (a browser
sends the file's raw bytes, not base64 or quoted-printable), so nothing further
transforms it. ``decode=True`` is therefore used for *every* part below, image
or text, not only the file: it is the only accessor this module found, by
direct measurement rather than by reading the docs, that survives a payload
containing every byte value and the boundary sequence itself
(AC-boundary/multipart).

**One request, one temp file, one owner of its cleanup.** :func:`read` writes
the uploaded part to a fresh temp file and hands back its path alongside the
built :class:`~nonogram.web.submission.Submission` — it does not delete it,
and it does not know whether the submission the fields built out to is even
usable, because a bad ``size`` field is exactly the case where a temp file was
still written for an ``image`` part that parsed fine. Whoever calls this
function (``nonogram.web.handler``) owns the file from the moment this returns
a path and must remove it once the run that consumed it — successfully or not
— is over (the card's step 5). That split mirrors
``nonogram.web.submission.Submission``'s own "exactly one of two attributes is
meaningful" shape: here it is "the path may need cleanup regardless of whether
the submission it came from parsed".
"""

from __future__ import annotations

import email.message
import email.parser
import email.policy
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from nonogram.web.submission import Submission, from_fields

__all__ = ["MultipartSubmission", "read"]


@dataclass(frozen=True, slots=True)
class MultipartSubmission:
    """What :func:`read` could make of one ``multipart/form-data`` body.

    Attributes:
        submission: The mapped request, or the reasons it could not be built
            — :mod:`nonogram.web.submission`'s own contract, reused whole.
        image_path: The temp file the ``image`` part was written to, or
            ``None`` when the body carried no uploaded file (no ``image`` part,
            or one with no filename — a file input with nothing chosen, which
            a browser still submits as an empty-named, empty part). Present
            even when ``submission.request`` is ``None``: some *other* field
            can be what made the body unreadable, and the file that was
            already written to disk before that was discovered still needs
            removing (the card's step 5).
    """

    submission: Submission
    image_path: Path | None = None


def _decoded_param(value: str | tuple[str | None, str | None, bytes] | None) -> str | None:
    """A ``Message.get_param`` result, read as plain text.

    ``get_param`` returns a plain ``str`` for an ordinarily quoted parameter —
    every browser's spelling of a field's ``name`` — and only falls back to the
    RFC 2231 ``(charset, language, value)`` triple for one encoded as
    ``name*=UTF-8''...``, which no observed browser does for a form field name.
    Handled anyway rather than assumed away: the alternative is a part this
    function silently drops, which is a field the user typed going missing
    with no error at all.
    """
    if value is None or isinstance(value, str):
        return value
    charset, _language, raw = value
    try:
        return raw.decode(charset or "utf-8", "replace")
    except LookupError:
        return raw.decode("utf-8", "replace")


def _write_temp_file(content: bytes) -> Path:
    """Land ``content`` in a fresh temp file and return its path.

    No suffix is taken from the upload's own filename: Pillow identifies an
    image by its content, not its extension (the sourcing module already opens
    ``--image`` paths with arbitrary or absent extensions), and a name the
    browser sent is not a safe ingredient for a path this module builds —
    ``tempfile``'s own ``suffix`` argument is concatenated onto the generated
    name with no separator-stripping, so a filename containing ``/`` would
    otherwise steer where the write lands.

    No ``try``/``except`` around the write, deliberately (``test_web_server``'s
    ``test_the_web_package_raises_nothing`` — nothing in ``nonogram.web``
    originates a ``raise`` of its own, ADR-0019/R1). A write failure here is a
    standard-library ``OSError`` — a full disk, an unwritable temp directory —
    left to propagate exactly as it arose. It reaches
    ``WebUIRequestHandler._generate`` *before* that method's own
    ``except OSError`` starts (that one only wraps the two orchestrator calls,
    for the reason its docstring gives — an ``OSError`` while writing a
    *response* must not be mistaken for one of these and answered with a
    second, doomed write to the same broken socket), so this one specific
    failure is the same "genuinely unexpected" case the module docstring
    already carves out: a stack trace on stderr and a dropped connection,
    rather than a tidy page, for a disk-full temp directory. The ``with``-
    scoped file descriptor still closes cleanly on the way out; only the
    half-written temp file itself is left behind, in this one rare case.
    """
    descriptor, name = tempfile.mkstemp(prefix="nonogram-upload-")
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(content)
    return Path(name)


def read(content_type: str, body: bytes) -> MultipartSubmission:
    """Read one ``multipart/form-data`` body into a generation request.

    Args:
        content_type: The request's ``Content-Type`` header value, boundary
            parameter and all — the caller's job is only to have recognised it
            as ``multipart/form-data`` before calling this (``handler.py``'s
            branch), not to have parsed it.
        body: The raw request body, undecoded — multipart bodies carry binary
            parts, so nothing upstream of this function may treat them as text
            (contrast :func:`nonogram.web.submission.read`, whose ``body`` is
            already ``str`` because a urlencoded one always is).

    Returns:
        A :class:`MultipartSubmission`. Never raises: a body that is not
        well-formed multipart at all — no boundary parameter, or one
        ``BytesParser`` cannot make sense of — is read as zero fields and no
        image, reported through :class:`~nonogram.web.submission.Submission`'s
        own ``unreadable`` channel exactly as a malformed urlencoded body is.
    """
    header = f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode(
        "latin-1", "replace"
    )
    message = email.parser.BytesParser(policy=email.policy.compat32).parsebytes(header + body)
    if not message.is_multipart():
        return MultipartSubmission(
            Submission(None, ("could not parse the multipart request body",)), None
        )

    fields: dict[str, list[str]] = {}
    image_path: Path | None = None
    for part in message.get_payload():
        if not isinstance(part, email.message.Message):
            continue  # pragma: no cover - BytesParser always yields Message parts
        name = _decoded_param(part.get_param("name", header="content-disposition"))
        if name is None:
            continue
        filename = part.get_filename()
        content = part.get_payload(decode=True) or b""
        if name == "image" and filename:
            if image_path is not None:
                # A second ``image`` part with a filename — not a shape any
                # form this codebase renders produces, but a hand-built body
                # could. The earlier temp file would otherwise never be
                # cleaned up: only the ``image_path`` this function returns is
                # what the caller knows to remove (the card's step 5).
                image_path.unlink(missing_ok=True)
            image_path = _write_temp_file(content)
            continue
        charset = part.get_content_charset() or "utf-8"
        try:
            text = content.decode(charset, "replace")
        except LookupError:
            text = content.decode("utf-8", "replace")
        # "Blank means absent" (submission.py's rule for a urlencoded body,
        # via parse_qs's default keep_blank_values=False) applies here too: an
        # empty text box posts an empty part, and the two encodings must agree
        # on what "not filled in" means.
        if text:
            fields.setdefault(name, []).append(text)

    return MultipartSubmission(from_fields(fields, image=image_path), image_path)
