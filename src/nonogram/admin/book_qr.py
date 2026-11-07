"""Text in, QR module matrix out: the one door onto the vendored encoder.

CARD-388, ADR-0006/R2. The encoder itself is Project Nayuki's
``qrcodegen.py``, kept byte-for-byte under ``admin/_vendor/`` and held to its
recorded content digest by ``tests/test_vendored_qr_encoder.py``. **This module is the
only importer of it** (R2's last condition), and it exists so that nothing
else in the package ever sees the vendored file's types: a caller gets
``tuple[tuple[bool, ...], ...]`` -- the codebase's grid boundary type, row
major, ``True`` = dark -- and nothing else crosses (CARD-388 G-4).

What is fixed here, and why
---------------------------

**Error correction is level Q (25 % of codewords), not boosted.** A book is
handled, folded and printed on cheap stock; a code that survives a quarter of
its codewords damaged costs one QR version more than level M for the address
this book prints (below), and a version is only four modules. ``boostecl`` is
off so that the level is the one stated here and not whatever happened to fit
-- the capacity below is then a fact, not a floor.

**Byte mode, ASCII only.** The text is encoded as one byte segment. The
vendored library would pick numeric or alphanumeric mode where it can, which
makes the capacity depend on the characters; one mode makes "the longest URL
this accepts" a single number. Non-ASCII text is refused rather than encoded,
because a reader that has to guess between ISO-8859-1 and UTF-8 for a byte
segment (the QR standard's default is ISO-8859-1) may print mojibake, and a
URL is ASCII by construction.

**Versions 1..6 only.** At the 2 cm square the book prints, a version-6 code
(41 modules plus the 4-module quiet zone on each side, 49 in all) is 0.408 mm
per module, just above :data:`nonogram.admin.book_vector_draw.MIN_MODULE_MM`.
A longer text would need a larger version and the drawer would refuse the
box, so the encoder refuses first, with the reason, instead of handing back a
code that cannot be printed legibly.

Measured on the vendored encoder (computed, not recalled):

* ``https://nonogram.adverax.io/b/<10 hex>`` is 40 bytes and needs
  **version 4** (33x33 modules; 41 with the quiet zone: 0.488 mm at 2 cm).
* The longest text accepted is **74 bytes** (:data:`MAX_BYTES`), version 6.
"""

from __future__ import annotations

from nonogram.admin._vendor import qrcodegen

__all__ = [
    "ERROR_CORRECTION",
    "MAX_BYTES",
    "MAX_VERSION",
    "QrCapacityError",
    "QrMatrix",
    "encode_text",
]

#: A QR symbol as the codebase passes grids: rows of dark (``True``) modules.
QrMatrix = tuple[tuple[bool, ...], ...]

#: Level Q: about 25 % of codewords may be unreadable.
ERROR_CORRECTION = "Q"

#: The largest version the wrapper will produce (see the module docstring).
MAX_VERSION = 6

#: The longest ASCII text, in bytes, that fits version :data:`MAX_VERSION` at
#: level Q in byte mode. Pinned against the encoder by a test that encodes a
#: text of exactly this length and one byte more.
MAX_BYTES = 74


class QrCapacityError(ValueError):
    """The text cannot be carried by a code this book can print.

    Raised before any matrix exists, so no caller can receive a half answer.
    """


def encode_text(text: str) -> QrMatrix:
    """``text`` as a QR module matrix at level Q, byte mode.

    Raises:
        QrCapacityError: ``text`` is empty, is not ASCII, or is longer than
            :data:`MAX_BYTES` bytes.
    """
    if not text:
        raise QrCapacityError("there is nothing to encode: the text is empty")
    try:
        data = text.encode("ascii")
    except UnicodeEncodeError:
        raise QrCapacityError(
            "a printed link is ASCII; a QR byte segment has no portable way to "
            "say otherwise"
        ) from None
    if len(data) > MAX_BYTES:
        raise QrCapacityError(
            f"{len(data)} bytes do not fit: at level {ERROR_CORRECTION} and "
            f"version {MAX_VERSION} the most a printed code carries here is "
            f"{MAX_BYTES}"
        )
    try:
        symbol = qrcodegen.QrCode.encode_segments(
            [qrcodegen.QrSegment.make_bytes(data)],
            qrcodegen.QrCode.Ecc.QUARTILE,
            maxversion=MAX_VERSION,
            boostecl=False,
        )
    except qrcodegen.DataTooLongError as error:  # MAX_BYTES disagrees with the encoder
        raise QrCapacityError(str(error)) from error
    size = symbol.get_size()
    return tuple(
        tuple(symbol.get_module(x, y) for x in range(size)) for y in range(size)
    )
