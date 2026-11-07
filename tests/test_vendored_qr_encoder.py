"""CARD-388: the vendored QR encoder, its pinning, and its wrapper.

ADR-0006/R2 admits ONE vendored third-party file under conditions; the first
half of this module holds each condition to a check that can fail, the second
half holds the wrapper (``nonogram.admin.book_qr``) to an independent reader
(``tests/helpers/qr_reader.py``, written from the standard and sharing nothing
with the encoder). Expected values are literals or come from that reader, never
from the encoder under test (CARD-388 G-5).

AC-4's dependency-baseline half is
``tests/test_export_pdf.py::test_the_dependency_baseline_is_still_closed``,
which this card does not duplicate; this module adds the two conditions that
test cannot see (the vendored file's own imports, and who imports it).
"""

from __future__ import annotations

import ast
import hashlib
import random
import sys
from pathlib import Path

import pytest

from nonogram.admin import book_qr
from tests.helpers import qr_reader

SRC = Path(__file__).resolve().parents[1] / "src" / "nonogram"
VENDOR = SRC / "admin" / "_vendor"
RECORD = VENDOR / "PROVENANCE.qrcodegen"


def _provenance() -> dict[str, str]:
    record = {}
    for line in RECORD.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            key, _, value = line.partition(": ")
            record[key] = value
    return record


def _matches_record(data: bytes, record: dict[str, str]) -> bool:
    return hashlib.sha256(data).hexdigest() == record["sha256"]


# -- AC-3: pinned bytes ---------------------------------------------------------


def test_the_vendored_bytes_match_their_recorded_sha256() -> None:
    record = _provenance()
    data = (VENDOR / record["file"]).read_bytes()
    assert _matches_record(data, record), (
        "the vendored file no longer matches its provenance record: an edit to "
        "vendored code is a deliberate act (ADR-0006/R2) -- record the patch "
        "and its reason in PROVENANCE.qrcodegen, then update the sha256"
    )
    assert len(data) == int(record["bytes"])
    # The literal is written here as well, so the record cannot be edited
    # alongside the file in one stroke without this line noticing.
    assert record["sha256"] == (
        "b089855caf16185c61421ea4927c1b213cf9468940d71fa8ab11ef83662dcc84"
    )


def test_the_licence_text_is_present_and_names_the_recorded_licence() -> None:
    record = _provenance()
    licence_path = VENDOR / record["licence_file"]
    licence = licence_path.read_text(encoding="ascii")
    assert record["licence"] == "MIT"
    assert licence.startswith("MIT License\n")
    assert "Copyright (c) Project Nayuki." in licence
    assert "Permission is hereby granted, free of charge" in licence
    assert (
        hashlib.sha256(licence_path.read_bytes()).hexdigest()
        == record["licence_file_sha256"]
    )
    # The attribution the licence requires travels inside the vendored file.
    header = (VENDOR / record["file"]).read_text(encoding="ascii")[:1500]
    assert "Copyright (c) Project Nayuki. (MIT License)" in header
    assert (
        "The above copyright notice and this permission notice shall be included"
        in header
    )
    for field in ("upstream_url", "version", "commit"):
        assert record[field], field


def test_a_one_byte_edit_of_a_copy_fails_the_pin() -> None:
    """The control: the check above is capable of failing."""
    record = _provenance()
    data = bytearray((VENDOR / record["file"]).read_bytes())
    assert _matches_record(bytes(data), record)
    data[len(data) // 2] ^= 0x01
    assert not _matches_record(bytes(data), record)


# -- ADR-0006/R2: stdlib only, one file, one importer -------------------------------


def _imported_roots(path: Path) -> set[str]:
    roots = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            roots |= {alias.name.partition(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0, "a vendored file imports nothing relatively"
            roots.add((node.module or "").partition(".")[0])
    return roots


def test_the_vendored_file_imports_only_the_standard_library() -> None:
    roots = _imported_roots(VENDOR / _provenance()["file"])
    assert roots == {"__future__", "collections", "itertools", "re", "typing"}
    assert roots <= set(sys.stdlib_module_names)


def test_the_vendored_directory_holds_exactly_one_third_party_source_file() -> None:
    assert sorted(p.name for p in VENDOR.glob("*.py")) == [
        "__init__.py",
        "qrcodegen.py",
    ]


def test_only_the_wrapper_imports_the_vendored_file() -> None:
    importers = set()
    for path in sorted(SRC.rglob("*.py")):
        if VENDOR in path.parents:
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""] + [alias.name for alias in node.names]
            if any("qrcodegen" in n or "_vendor" in n for n in names):
                importers.add(path.relative_to(SRC).as_posix())
    assert importers == {"admin/book_qr.py"}


# -- the reader is a control that can fail -------------------------------------------


def test_the_readers_format_words_match_the_standards_published_values() -> None:
    # The four level words for mask 0 as printed in the standard's format table.
    assert f"{qr_reader.format_word(0b01, 0):015b}" == "111011111000100"  # L
    assert f"{qr_reader.format_word(0b00, 0):015b}" == "101010000010010"  # M
    assert f"{qr_reader.format_word(0b11, 0):015b}" == "011010101011111"  # Q
    assert f"{qr_reader.format_word(0b10, 0):015b}" == "001011010001001"  # H


def test_the_reader_refuses_a_symbol_with_a_damaged_data_module() -> None:
    url = "https://nonogram.adverax.io/b/0123456789"
    modules = [list(row) for row in book_qr.encode_text(url)]
    assert qr_reader.read_matrix(modules) == url
    modules[20][21] = not modules[20][21]  # a data module, away from every pattern
    with pytest.raises(qr_reader.QrReadError):
        qr_reader.read_matrix(modules)


# -- AC-1: round trip ---------------------------------------------------------------

_HOSTS = (
    "a.io",
    "nonogram.adverax.io",
    "play.example.org",
    "books.example-publishing.co.uk",
    "nonogram-puzzles.library.example.com",
    "localhost",
)


def _corpus() -> list[str]:
    rng = random.Random(388)
    urls = []
    for _ in range(260):
        host = rng.choice(_HOSTS)
        port = rng.choice(("", "", ":8080", ":443", ":3000"))
        scheme = rng.choice(("https", "https", "http"))
        slug = "".join(rng.choice("0123456789abcdef") for _ in range(10))
        urls.append(f"{scheme}://{host}{port}/b/{slug}")
    urls.append("https://nonogram.adverax.io/b/0123456789")
    return urls


class TestQrEncoder_RoundTripsThroughAnIndependentReader:
    def test_every_url_in_the_corpus_decodes_to_itself(self) -> None:
        corpus = _corpus()
        assert len(corpus) >= 200, "the corpus must not shrink silently"
        sizes = set()
        for url in corpus:
            modules = book_qr.encode_text(url)
            sizes.add(len(modules))
            assert qr_reader.read_matrix(modules) == url
        assert len(sizes) >= 3, f"the corpus should span several versions, got {sizes}"

    def test_the_real_landing_address_is_forty_bytes_and_a_version_four_symbol(
        self,
    ) -> None:
        url = "https://nonogram.adverax.io/b/0123456789"
        assert len(url) == 40
        modules = book_qr.encode_text(url)
        assert len(modules) == 33  # (4 * 4) + 17: version 4
        assert qr_reader.read_matrix(modules) == url

    def test_the_symbol_says_error_correction_level_q(self) -> None:
        modules = book_qr.encode_text("https://nonogram.adverax.io/b/0123456789")
        assert qr_reader.read_format(modules)[0] == "Q"

    def test_the_matrix_is_the_boundary_type_and_nothing_else(self) -> None:
        modules = book_qr.encode_text("https://a.io/b/0123456789")
        assert type(modules) is tuple
        assert all(type(row) is tuple for row in modules)
        assert all(type(cell) is bool for row in modules for cell in row)
        assert {len(row) for row in modules} == {len(modules)}

    def test_the_longest_accepted_text_decodes(self) -> None:
        longest = "https://" + "a" * (74 - len("https://"))
        assert len(longest) == 74 == book_qr.MAX_BYTES
        modules = book_qr.encode_text(longest)
        assert len(modules) == 41  # version 6
        assert qr_reader.read_matrix(modules) == longest


# -- AC-5: capacity ---------------------------------------------------------------------


class TestQrEncoder_RefusesWhatItCannotCarry:
    def test_one_byte_over_the_capacity_raises_a_named_error(self) -> None:
        with pytest.raises(book_qr.QrCapacityError, match="75 bytes"):
            book_qr.encode_text("h" * 75)

    def test_a_text_far_over_the_capacity_raises(self) -> None:
        with pytest.raises(book_qr.QrCapacityError):
            book_qr.encode_text("https://example.org/" + "x" * 2000)

    def test_an_empty_text_raises(self) -> None:
        with pytest.raises(book_qr.QrCapacityError):
            book_qr.encode_text("")

    def test_a_non_ascii_text_raises(self) -> None:
        with pytest.raises(book_qr.QrCapacityError, match="ASCII"):
            book_qr.encode_text("https://example.org/к")

    def test_the_error_is_a_value_error_and_returns_nothing(self) -> None:
        result = None
        with pytest.raises(ValueError):
            result = book_qr.encode_text("h" * 75)
        assert result is None
