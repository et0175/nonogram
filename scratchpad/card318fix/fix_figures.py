from pathlib import Path
t = Path("tests/test_solver_strategies.py")
s = t.read_text()

def swap(old, new, label):
    global s
    assert s.count(old) == 1, (label, s.count(old))
    s = s.replace(old, new)
    print("ok:", label)

swap(
    '''    #: The extent the random batch is generated at. ``MIN_SIZE`` will not do:
    #: measured, every 10x10 random candidate solves with the single rung
    #: ``('simple_overlap',)`` (10 of 10 in one batch, 8 of 8 across seeds), so
    #: there the truth *is* the constant R3 plants and the identity assertion
    #: below could not discriminate it. At 20x20, density 50 — the density
    #: ``orchestrator.generate_batch`` uses for every random candidate, not a
    #: number chosen here — 134 of 160 measured candidates carry a longer
    #: ladder, nothing was abandoned or timed out in 160, and a batch of ten
    #: costs 0.3-0.7s.
''',
    '''    #: The extent the random batch is generated at. ``MIN_SIZE`` will not do,
    #: and the figures are counted from the candidates rather than estimated.
    #: At 10x10, density 50: **89 of 100** candidates solve with the single
    #: rung ``('simple_overlap',)``, and **4 of 10** whole batches were
    #: single-rung throughout — a batch in which the truth and the constant
    #: cycle 1's R3 plants are the same value, so at ``MIN_SIZE`` the identity
    #: assertion below would discriminate nothing about two batches in five.
    #: At 20x20, density 50 — the density ``orchestrator.generate_batch``
    #: gives every random candidate, not a number chosen here — **134 of 160**
    #: candidates carry a longer ladder, **0 of 16** batches were single-rung
    #: throughout, nothing was abandoned and nothing timed out, and a batch of
    #: ten costs 0.3-0.7s.
''',
    "LADDER_EXTENT comment, counted from the candidates",
)

swap(
    '''        # corpora assert their per-arm floors. At the measured single-rung rate
        # for this extent (26 of 160 candidates) ten draws miss it with
        # probability ~1e-8; if it ever fires, the batch is degenerate and the
        # identity assertion has stopped meaning anything, which is exactly
        # what a reader needs told.
''',
    '''        # corpora assert their per-arm floors. At the measured single-rung
        # rate for this extent (26 of 160 candidates) ten draws miss it with
        # probability ~1e-8; if it ever fires, the batch is degenerate and the
        # identity assertion has stopped meaning anything, which is exactly
        # what a reader needs told.
        #
        # This line has its own mutant, and it is not the extent: truncating
        # every ladder to its first rung in the solver reds it at any extent,
        # twice out of two, while the identity arms above stay green — they
        # re-derive through the same solver, so a truncated ladder is still
        # that puzzle's list. CARD-318's R8.
''',
    "floor comment: its own mutant",
)

t.write_text(s)
print("written")
