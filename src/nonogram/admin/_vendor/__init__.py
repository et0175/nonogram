"""Third-party source kept verbatim under ADR-0006/R2.

This directory holds exactly one vendored file, ``qrcodegen.py``, beside its
licence (``LICENSE.qrcodegen``) and its provenance record
(``PROVENANCE.qrcodegen``). Nothing here is ours to edit: a test holds the
file's bytes to the sha256 in the provenance record. The only module that may
import it is :mod:`nonogram.admin.book_qr`, which turns its types into the
codebase's own boundary type.
"""
