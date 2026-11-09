# `docs/qa/` — manual test cases

Human-runnable test cases for the parts of the product where a person is the
better instrument than the suite: a real finger on glass, legibility by eye, the
**deployed** site (the suite drives locally assembled trees), and a printed QR
code under a phone camera.

These are **not the gate.** A card is merged on `pytest`, and every case here
names the automated test that actually pins the behaviour, or says
**manual-only** and why. If a case and its gate disagree, the gate is right
about what the code does and the case is stale.

| File | Covers |
| --- | --- |
| [public-player-test-cases.md](public-player-test-cases.md) | COMP-011 / FR-045 — `/play/<key>`, `/b/<slug>`, `/library`: brushes, Region, the crosshair, zoom, clue circles, the hint, saving and solving, the no-answer spot checks, the after-publish smoke run, and probe mode (written ahead of CARD-380) |

Related: `docs/REQUIREMENTS/TEST_CASES/ADMIN_PANEL_TC.md` is a 2026-09-08
document from a requirements framework that was abandoned and never populated
(see `docs/REQUIREMENTS/README.md`'s banner) — it is not this directory's
sibling and its `Status: Ready` column vouches for nothing.
