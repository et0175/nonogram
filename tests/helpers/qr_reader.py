"""A QR reader written from ISO/IEC 18004, independent of the encoder.

CARD-388 item 6. The survey (CARD-210's retired text asks for one):

* (a) a vendored pure-Python decoder: a second third-party file, which
  ADR-0006/R2 does not admit without a revision;
* (b) a decoder in the dev extra: there is none (``pip list`` in the repo venv
  shows no zbar, OpenCV, ZXing or pyzbar binding, and ``zbarimg`` is not on the
  host), and a new one is a new dev dependency -- the owner's standing rule says
  stop and ask, so it is not taken;
* (c) a reader of our own, written from the standard and not from the encoder.
  **Taken.** This file imports nothing from ``nonogram`` and nothing from
  ``qrcodegen``; it shares no table with them. What it takes from the standard
  is each constant below, and what it does *not* take is any helper from the
  encoder.

What it checks that a lax reader would not: both copies of the format
information agree; every Reed-Solomon block has zero syndromes (a code whose
error-correction bytes are wrong looks right and fails on a phone that has to
verify them); the padding after the terminator is the standard's alternating
``0xEC``/``0x11``; and the module count fits the codeword structure for the
version, so a mistake in this file's own tables shows up as a failure rather
than as a wrong answer.

Scope: versions 1..6 (the most the wrapper produces), error-correction levels L/M/Q/H, numeric, alphanumeric
and byte modes. Anything else raises :class:`QrReadError`.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np

__all__ = ["QrReadError", "format_word", "read_format", "read_image", "read_matrix"]

#: A grey at or below this is ink; the same threshold the other pixel readers
#: in ``tests/helpers`` use.
INK_LEVEL = 128


class QrReadError(ValueError):
    """The modules do not form a readable QR symbol."""


# -- tables, from the standard ------------------------------------------------

# Error-correction level bits in the format information.
_ECL_BITS = {0b01: "L", 0b00: "M", 0b11: "Q", 0b10: "H"}

# (error-correction codewords per block, number of blocks), versions 1..6.
_BLOCKS = {
    "L": [(7, 1), (10, 1), (15, 1), (20, 1), (26, 1), (18, 2)],
    "M": [(10, 1), (16, 1), (26, 1), (18, 2), (24, 2), (16, 4)],
    "Q": [(13, 1), (22, 1), (18, 2), (26, 2), (18, 4), (24, 4)],
    "H": [(17, 1), (28, 1), (22, 2), (16, 4), (22, 4), (28, 4)],
}

_FORMAT_GENERATOR = 0b10100110111  # x^10 + x^8 + x^5 + x^4 + x^2 + x + 1
_FORMAT_MASK = 0b101010000010010

# Total codewords (data + error correction) of versions 1..6.
_TOTAL_CODEWORDS = [26, 44, 70, 100, 134, 172]

_ALPHANUMERIC = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $%*+-./:"

# Character-count field widths for versions 1..9 (this reader stops at 6).
_COUNT_BITS = {0b0001: (10,), 0b0010: (9,), 0b0100: (8,)}


def _bch_remainder(value: int, generator: int, check_bits: int) -> int:
    """``value`` shifted up by ``check_bits``, reduced modulo ``generator``."""
    value <<= check_bits
    top = generator.bit_length() - 1
    for shift in range(value.bit_length() - 1, top - 1, -1):
        if value >> shift & 1:
            value ^= generator << (shift - top)
    return value


def format_word(ecl_bits: int, mask: int) -> int:
    """The 15-bit format information for a level and a mask, per the standard."""
    data = ecl_bits << 3 | mask
    return (data << 10 | _bch_remainder(data, _FORMAT_GENERATOR, 10)) ^ _FORMAT_MASK


def _decode_format(word: int) -> tuple[str, int]:
    """The nearest valid format word, refusing a distance above three."""
    best = min(
        ((format_word(bits, mask), bits, mask) for bits in _ECL_BITS for mask in range(8)),
        key=lambda candidate: bin(candidate[0] ^ word).count("1"),
    )
    if bin(best[0] ^ word).count("1") > 3:
        raise QrReadError("the format information matches no valid word")
    return _ECL_BITS[best[1]], best[2]


# -- geometry -------------------------------------------------------------------


def _alignment_centres(version: int) -> list[int]:
    if version == 1:
        return []
    count = version // 7 + 2
    last = 4 * version + 10
    step = -(-(last - 6) // (count - 1))
    step += step % 2  # the spacing is even
    return [6] + [last - step * k for k in range(count - 2, -1, -1)]


def _function_modules(version: int) -> set[tuple[int, int]]:
    """Every (row, column) that is not data: finders, timing, alignment, info."""
    size = 4 * version + 17
    reserved: set[tuple[int, int]] = set()
    for row in range(9):  # three finders with separator and format strips
        for column in range(9):
            reserved.add((row, column))
        for column in range(size - 8, size):
            reserved.add((row, column))
    for row in range(size - 8, size):
        for column in range(9):
            reserved.add((row, column))
    for index in range(size):  # timing patterns
        reserved.add((6, index))
        reserved.add((index, 6))
    centres = _alignment_centres(version)
    for row in centres:
        for column in centres:
            if (row, column) in {(6, 6), (6, centres[-1]), (centres[-1], 6)}:
                continue
            for dr in range(-2, 3):
                for dc in range(-2, 3):
                    reserved.add((row + dr, column + dc))
    return reserved


def _mask_applies(mask: int, row: int, column: int) -> bool:
    return (
        (row + column) % 2 == 0,
        row % 2 == 0,
        column % 3 == 0,
        (row + column) % 3 == 0,
        (row // 2 + column // 3) % 2 == 0,
        row * column % 2 + row * column % 3 == 0,
        (row * column % 2 + row * column % 3) % 2 == 0,
        ((row + column) % 2 + row * column % 3) % 2 == 0,
    )[mask]


def read_format(modules: Sequence[Sequence[bool]]) -> tuple[str, int]:
    size = len(modules)
    first = [(8, c) for c in (0, 1, 2, 3, 4, 5, 7, 8)] + [(r, 8) for r in (7, 5, 4, 3, 2, 1, 0)]
    second = [(r, 8) for r in range(size - 1, size - 8, -1)] + [
        (8, c) for c in range(size - 8, size)
    ]
    words = []
    for cells in (first, second):
        word = 0
        for row, column in cells:
            word = word << 1 | modules[row][column]
        words.append(word)
    one, two = _decode_format(words[0]), _decode_format(words[1])
    if one != two:
        raise QrReadError(f"the two format copies disagree: {one} vs {two}")
    # A real scanner would correct a damaged copy; this reader is a control on
    # the ENCODER, so both copies must be the exact valid word, not merely near.
    ecl_bits = next(bits for bits, level in _ECL_BITS.items() if level == one[0])
    if words != [format_word(ecl_bits, one[1])] * 2:
        raise QrReadError("a format-information copy is not the exact valid word")
    return one


# -- codewords ------------------------------------------------------------------


def _raw_codewords(modules: Sequence[Sequence[bool]], version: int, mask: int) -> list[int]:
    size = len(modules)
    reserved = _function_modules(version)
    bits: list[int] = []
    column = size - 1
    upward = True
    while column > 0:
        if column == 6:
            column -= 1
        rows = range(size - 1, -1, -1) if upward else range(size)
        for row in rows:
            for c in (column, column - 1):
                if (row, c) not in reserved:
                    bits.append(modules[row][c] ^ _mask_applies(mask, row, c))
        upward = not upward
        column -= 2
    return [
        sum(bit << (7 - i) for i, bit in enumerate(bits[start : start + 8]))
        for start in range(0, len(bits) - len(bits) % 8, 8)
    ]


def _gf_tables() -> tuple[list[int], list[int]]:
    exp, log = [0] * 512, [0] * 256
    value = 1
    for power in range(255):
        exp[power] = value
        log[value] = power
        value <<= 1
        if value & 0x100:
            value ^= 0x11D
    for power in range(255, 512):
        exp[power] = exp[power - 255]
    return exp, log


_EXP, _LOG = _gf_tables()


def _syndromes_are_zero(block: list[int], parity: int) -> bool:
    for root in range(parity):
        total = 0
        for codeword in block:  # Horner's rule over alpha^root
            total = (_EXP[_LOG[total] + root] if total else 0) ^ codeword
        if total:
            return False
    return True


def _data_codewords(codewords: list[int], version: int, ecl: str) -> list[int]:
    parity, blocks = _BLOCKS[ecl][version - 1]
    if len(codewords) < blocks * parity:
        raise QrReadError("fewer codewords than the structure needs")
    data_total = len(codewords) - blocks * parity
    short = data_total // blocks
    lengths = [short + (1 if index >= blocks - data_total % blocks else 0) for index in range(blocks)]
    data = [[] for _ in range(blocks)]
    position = 0
    for column in range(max(lengths)):  # interleaved data
        for index in range(blocks):
            if column < lengths[index]:
                data[index].append(codewords[position])
                position += 1
    ecc = [[] for _ in range(blocks)]
    for _ in range(parity):  # interleaved parity
        for index in range(blocks):
            ecc[index].append(codewords[position])
            position += 1
    for index in range(blocks):
        if not _syndromes_are_zero(data[index] + ecc[index], parity):
            raise QrReadError(f"block {index} fails its Reed-Solomon check")
    return [codeword for block in data for codeword in block]


def _decode_segments(data: list[int], version: int) -> str:
    bits = "".join(f"{codeword:08b}" for codeword in data)
    position = 0

    def take(count: int) -> int:
        nonlocal position
        if position + count > len(bits):
            raise QrReadError("the data ends inside a field")
        value = int(bits[position : position + count], 2)
        position += count
        return value

    out: list[str] = []
    while True:
        mode = take(4) if len(bits) - position >= 4 else 0
        if mode == 0:
            break
        if mode not in _COUNT_BITS:
            raise QrReadError(f"mode {mode:04b} is not supported by this reader")
        count = take(_COUNT_BITS[mode][0])
        if mode == 0b0100:
            raw = bytes(take(8) for _ in range(count))
            out.append(raw.decode("utf-8"))
        elif mode == 0b0010:
            chars = []
            for _ in range(count // 2):
                pair = take(11)
                chars += [_ALPHANUMERIC[pair // 45], _ALPHANUMERIC[pair % 45]]
            if count % 2:
                chars.append(_ALPHANUMERIC[take(6)])
            out.append("".join(chars))
        else:
            digits = []
            for _ in range(count // 3):
                digits.append(f"{take(10):03d}")
            if count % 3 == 2:
                digits.append(f"{take(7):02d}")
            elif count % 3 == 1:
                digits.append(f"{take(4):d}")
            out.append("".join(digits))
    position = -(-position // 8) * 8  # the padding starts on a codeword boundary
    pad_bytes = [int(bits[i : i + 8], 2) for i in range(position, len(bits), 8)]
    for index, value in enumerate(pad_bytes):
        if value != (0xEC, 0x11)[index % 2]:
            raise QrReadError("the padding is not the standard's 0xEC/0x11 run")
    return "".join(out)


# -- doors ----------------------------------------------------------------------


def read_matrix(modules: Sequence[Sequence[bool]]) -> str:
    """The text a QR module matrix (``True`` = dark, no quiet zone) carries."""
    size = len(modules)
    if size < 21 or (size - 17) % 4 or any(len(row) != size for row in modules):
        raise QrReadError(f"a {size}-module square is not a QR symbol")
    version = (size - 17) // 4
    if version > 6:
        raise QrReadError("this reader stops at version 6")
    ecl, mask = read_format(modules)
    codewords = _raw_codewords(modules, version, mask)
    if len(codewords) != _TOTAL_CODEWORDS[version - 1]:
        raise QrReadError(
            f"{len(codewords)} codewords read from a version {version} symbol, "
            f"the standard has {_TOTAL_CODEWORDS[version - 1]}"
        )
    return _decode_segments(_data_codewords(codewords, version, ecl), version)


def read_image(page: np.ndarray, *, ink_level: int = INK_LEVEL) -> str:
    """The text a rendered page carrying ONE code decodes to.

    ``page`` is a greyscale array indexed ``[row, column]`` (what
    ``tests/helpers/pdf_vector.rendered_page`` returns). The symbol is located
    as the bounding box of the ink -- a QR's three finder patterns put dark
    modules on its corners and edges -- and the symbol size is read from the
    top-left finder's first row (seven dark modules), snapped to a valid
    version, with the pitch taken as the bounding width over that size. Each
    module is then sampled at its centre.
    """
    ink = page <= ink_level
    rows, columns = np.where(ink)
    if rows.size == 0:
        raise QrReadError("there is no ink on the page")
    top, bottom, left, right = rows.min(), rows.max() + 1, columns.min(), columns.max() + 1
    run = 0
    while left + run < right and ink[top, left + run]:
        run += 1
    if run < 7:
        raise QrReadError("the top-left finder pattern is not seven modules wide")
    # The finder run gives a rough pitch (a pixel either way matters at 2-3 px
    # a module); the symbol size is then snapped to the nearest valid one
    # (21, 25, 29, ...) and the pitch re-derived from the whole width.
    rough = round((right - left) / (run / 7))
    size = 17 + 4 * max(1, round((rough - 17) / 4))
    pitch = (right - left) / size
    if abs((bottom - top) - size * pitch) > pitch:
        raise QrReadError("the ink is not a square of whole modules")
    modules = tuple(
        tuple(
            bool(ink[int(top + (row + 0.5) * pitch), int(left + (column + 0.5) * pitch)])
            for column in range(size)
        )
        for row in range(size)
    )
    return read_matrix(modules)
