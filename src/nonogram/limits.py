"""The supported grid size range — the one place it is defined.

Imports nothing, so every layer may depend on it, the same way every layer may
raise from :mod:`nonogram.errors`: the import guard in ``tests/test_cli.py``
puts both modules in the innermost shared rank (ADR-0007 History, CARD-063).
"""

__all__ = ["MAX_SIZE", "MIN_SIZE"]

#: Supported length of **one grid side**, in cells, inclusive on both ends
#: (FR-019, NFR-001). The bound is per side, not per grid: a 30x12 grid is as
#: legal as a 12x12 one. The top is set by print legibility rather than solver
#: cost (ADR-0022): past about 30 cells a side the printed cell drops under
#: ~6 mm on a sheet of paper (NFR-005) and stops being comfortable to mark by
#: hand.
MIN_SIZE = 10
MAX_SIZE = 30
