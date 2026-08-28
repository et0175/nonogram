"""The built-in library's template data (FR-002, CARD-008).

One module per named template, each exporting a single ``ART`` string: an
ASCII-art picture of the shape, ``#`` for a filled (black) cell and ``.`` for an
empty one, one line per row, every line the same length. Nothing here is code —
these modules hold data and only data, and ``nonogram.sourcing.library`` is the
only thing that reads them.

Why ``.py`` files rather than ``.txt`` package data
---------------------------------------------------
The card asks for the templates to live under ``sourcing/templates/`` as package
data, and a plain ``.txt`` per shape would be the obvious spelling. It does not
survive packaging here: ``pyproject.toml`` declares no ``package-data`` and the
tree has no ``MANIFEST.in``, so setuptools puts the ``.py`` files of a
discovered package into the wheel and drops every other extension — verified by
building a wheel with a probe ``.txt`` in this directory and finding only the
``__init__.py`` inside it. Fixing that means editing ``pyproject.toml``, which
guardrail G-3 forbids this card from touching. So the data is carried in the one
file type the build is already guaranteed to install, and stays *data*: a module
here may contain a docstring and an ``ART`` string, and nothing else — a rule
``tests/test_sourcing_library.py`` checks structurally rather than by
convention.

Adding a shape (ADR-0007's rejected plugin registry, guardrail G-5)
-------------------------------------------------------------------
Drop a module here and add one row to ``library._TEMPLATES``. Deliberately two
edits and not one: the set of library images is fixed in-package by decision, so
there is no directory scan, no entry point and no import hook — the registry is
a literal dict of explicit imports, which is what makes the available keys
knowable by reading the source rather than by running it.
"""

from __future__ import annotations
