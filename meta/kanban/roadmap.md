# Product Roadmap

_Generated: 2026-10-17 (after wave 43)_
_Stage: growth · Methodology: hybrid (RICE for feature, WSJF for enabler/tech-debt/compliance, FIFO for ops)_
_Config source: defaults — this project has no `meta/.skills.yml`_

## The critical path is not a backlog idea

**23 cards are `ready` and 11 of them cannot start.** CARD-222 heads the interior-redesign chain
(CARD-223 → 224/225 → 226/227/229..233) and is blocked on registry amendments that are one
`/forge:architect` session, not a card: **CON-018** (margins — outer 0.5 / top 0.55 / bottom 0.47,
gutter stays at KDP's 0.5 in per the owner's 2026-10-14 decision), **NFR-008** (one cell size per grid
size, capped 7.5 mm), **INV-013/FR-043** (CARD-206's title page ahead of the guide), and **cancelling**
CARD-204's pending **FR-032** amendment, which CARD-224 reverses rather than applies.

That session has been owed since wave 42 and is logged in two retrospectives as `defer_nfr_adr`.
No backlog score outranks it, because nothing it competes with can start.

**Capacity note (owner decision, 2026-10-17):** this wave is planned **unblock-first** rather than by
the `growth` percentages. The stage defaults (feature 55 / enabler 20 / tech-debt 15 / compliance 5 /
ops 5) remain the standing default for later waves — they were not changed. Applying them here would
have scheduled a feature bucket that cannot execute.

## Wave 1 (next iteration) — unblock, then the cheap measurements

### Architect station (not a card, not scored)
1. **One `/forge:architect` session** — CON-018, NFR-008, INV-013/FR-043, cancel FR-032.
   Releases CARD-222 and the 11 cards behind it. **Do this first.**

### tech-debt (WSJF) — ~1d total, all three are one-pointers
1. **IDEA-109** Re-measure "superseded baselines cost no runtime" (WSJF **19.0**) — **must land before
   CARD-220 starts.** Measured 2026-10-17: those baselines are loaded at runtime in **12 places** in
   `tests/test_book_pdf_memory.py`, and CARD-220's premise is that they are inert. CARD-220 is eligible
   now, so this is the cheapest intervention point on the board.
2. **IDEA-110** Resolve card `test:`/`check:` names against `tests/` at the decompose station
   (WSJF **16.0**) — a fabricated name reached four cards in two waves. Done by hand in wave 43 for
   both cards; not mechanised, so it depends on the orchestrator remembering.
3. **IDEA-108** Scope `test_web_upload.py`'s temp sweep to the test's own files (WSJF **13.0**) —
   verified still live (`gettempdir` present), and the board dispatches at concurrency 2, so the
   collision is the normal case. Cost CARD-211 a false red in wave 37.

### Then, in the same wave if capacity allows
4. **IDEA-106** ADR-0039's repo-wide guard audit (WSJF 5.8) — **the formula under-ranks this one and
   the ranking should not be followed blindly.** WSJF divides by job size, so a 5-point mechanism loses
   to three one-pointers; its raw factors (UBV 8 / TC 8 / RR 13) are the highest on the board. It is
   the mechanism behind wave 43's single root cause: two cards violated a mandatory rule squarely
   inside its scope, because R1–R3's checks are point tests over named guards in one file and cannot
   see a claim written elsewhere. ADR-0039 says this about itself and names the audit as deferred work.
   Third instance; a fourth would make it the most expensive unpromoted mechanism on the board.
5. **IDEA-107** Install `pytest-testmon` (WSJF 6.5) — `config.yml` names it as the precondition in its
   own comment. Wave 43's cost per card rose **2.3×** (1322s → 3098s) purely from running a stable
   suite three times per card at 100% full-suite share.

## Wave 2

- **CARD-243** (already carded) — the round-mark check sees the greys the book prints. Depends CARD-241 ✓.
- **IDEA-112** Promote the remaining wave-37 discipline rules into the model (WSJF 5.33, depends
  IDEA-106) — seven sentences the pipeline keeps re-learning one card at a time.
- **IDEA-111** Align review-report severity between the markdown and the YAML (WSJF 10.0) — small, but
  it protects the learning loop's own input, which is otherwise silently lossy.
- The interior-redesign chain, once the architect session lands: CARD-222 → 223 → 224/225 →
  226/227/229..233, plus CARD-206..209 and CARD-215/216/220/236.

## Waiting on the owner (review time, not engineering capacity — not scored)

Six merged cards' renders have never been eyeballed; all are in `~/Documents/nonogram-reviews/`:

| Card | What to look at | Merged |
|------|-----------------|--------|
| CARD-187 | Progress counter renders | wave 34 |
| CARD-189 | Click-sequence renders + the help line | wave 34 |
| CARD-190 | Review-page longest-side renders | wave 34 |
| CARD-191 | Sort-by-size button, confirm text, before/after | wave 34 |
| CARD-192 | Band filter, left/over renders | wave 35 |
| CARD-196 | Clue-number renders | wave 36 |

Deliberately outside the capacity buckets: scoring them as work would double-count your time as
engineering capacity. They are, however, the only record that those renders were never checked.

## Deferred by owner decision (V1 scope, 2026-10-13 — blockers already named)

| Idea | Revival trigger |
|------|-----------------|
| A public online solver | the public phase opens (blocks CARD-210) |
| A stable per-puzzle URL namespace | decided once, before any book ships printed codes (blocks CARD-210) |
| "Generate your own puzzle" second QR | the public generator surface exists |
| Persist user-generated puzzles | the public phase, plus a user/ownership notion and a retention rule |

## Ledger state

- 112 ideas: **28 done** (+9 this run: 8 by authoritative `Idea:` backlink, 1 verified in source),
  69 backlog, 7 screened, 1 rejected, **0 stale `in_kanban`**
- No fuzzy ship candidates above 0.62 similarity — no backlog idea quietly shipped under a
  differently-titled card
- Calibration applied: none needed. `python-pro` ran 0.80× this wave (within band); the cross-project
  entry for python-pro/tech-debt now reads 1.18× over 10 cards

## Not available for this project

- **Velocity forecast** — no `waves.duration` configured, so no sprint cadence to forecast against
- **Capacity drift** — no `meta/.skills.yml`, so no plan to measure actual spend against
- **Risk register, business ledger, intents/weights** — absent, so the constraint, interest-weight,
  unvalidated-assumption and value-calibration screens do not apply

## Next step

Run `/forge:architect` for the four owed amendments. It is the only item that unblocks other work.
