# Product Roadmap

_Generated: 2026-10-30 · mode: `plan` (scoring deliberately NOT run — see "Why 107 ideas were not scored")_
_Stage: **pre-launch** · Methodology: **WSJF for every scored category**, FIFO for ops_

## Config of record, and a correction

`meta/.skills.yml` **does not exist** in this project, so the roadmap skill's defaults
would apply: `stage=growth`, **RICE for features**, capacity 55/20/15/5/5. **Those
defaults were not used.** `backlog-scored.yml`'s own `config` block carries the
project's recorded choices, including an explicit owner decision:

> `methodology_note: 'owner choice 2026-10-03: RICE reach is meaningless for a
> single-owner admin tool'`

Running the defaults would have silently overturned that and changed the capacity mix.
**The recorded config governs.** If the stage has genuinely moved (see below), change it
deliberately — not by letting a missing file decide.

## THE HEADLINE: the capacity plan no longer describes this project

| Category | Plan % | Scored ideas | Verdict |
|----------|-------:|-------------:|---------|
| feature | **60** | **3** | plan reserves most of the budget for work that barely exists |
| enabler | 15 | **0** | nothing to spend it on |
| tech-debt | **5** | **71** | 93% of the backlog competing for 5% of the budget |
| compliance | 15 | **0** | nothing to spend it on |
| ops | 5 | 2 | roughly proportionate |

**The plan describes a pre-launch product push. The backlog is 93% tech-debt.** No wave
allocation computed from these percentages would mean anything: filling the feature
bucket exhausts the entire feature backlog in one wave, while the tech-debt bucket admits
roughly one idea per wave against 71 waiting.

This is the same divergence the waves 63–65 retrospective measured from the other
direction — **compliance −15pp, feature +10pp** — and it is now large enough that the
percentages are the thing to fix, not the input to a plan.

**Two readings, and they need different actions:**
1. **The stage moved.** `pre-launch` (60/15/5/15/5) stopped describing reality some waves
   ago; `mature` (40/15/**25**/10/10) is far closer to what the board actually does. That
   is a one-line change to a recorded decision — make it explicitly.
2. **Most of the "tech-debt" is not product work at all** — see the next section. If so,
   it should not be competing for product capacity under any percentage.

Both are probably true. (1) is cheap and (2) is the real cleanup.

## Why 107 ideas were not scored

`backlog.md` holds **186 open ideas**; `backlog-scored.yml` represents **79** of them.
The skill's smart default would score the missing **107**. It was not run, measured:

| What the 107 are about | Count |
|---|---:|
| process / discipline only | 34 |
| process **and** code (mostly a lesson that names a file) | 71 |
| **code only** | **2** |

**Two of 107 are about the product.** The rest are review-cycle findings — several
beginning literally *"Promote to a standing rule:"*. Scoring a discipline lesson with
WSJF's `user_business_value` is meaningless: it has none by construction.

`backlog.md` has become the overflow bin for review findings, and the right home for that
material already exists and was exercised today — **finding-family promotion into ADR
rules** (ADR-0039's R1–R4 are exactly this). Routing them through a prioritised *product*
queue converts a standing rule into a ticket that never gets picked.

## The scored backlog, ranked (ranking unchanged by the ×1.87 recalibration)

A uniform factor rescales absolute job sizes; it reorders nothing.

### feature — WSJF, 3 ideas
| Score | ID | job_size | Depends | Idea |
|------:|----|---------:|---------|------|
| 6.92 | IDEA-105 | 1.3 | — | Finalise guide preview needs changes after the owner look |
| 0.62 | IDEA-058 | 6.5 | IDEA-064 | Keyboard marking of player cells |
| 0.61 | IDEA-075 | 26.2 | — | Online solver public phase: hosting, QR URLs, no solution |

### tech-debt — WSJF, 71 ideas (top 6)
| Score | ID | job_size | Idea |
|------:|----|---------:|------|
| 14.62 | IDEA-109 | 1.3 | Re-measure "superseded baselines cost no runtime" |
| 12.31 | IDEA-110 | 1.3 | Resolve every card's backticked `test:`/`check:` name against the test tree |
| 10.00 | IDEA-108 | 1.3 | `test_web_upload.py` sweeps the machine-wide temp dir |
| 7.69 | IDEA-111 | 1.3 | Review reports disagree with themselves on severity |
| 6.15 | IDEA-007 | 2.6 | Validator ERROR: ADR-0025 ↔ ADR-0031 circular supersession |
| 5.38 | IDEA-082 | 2.6 | Five hollow e2e tests post the dead `images` field |

### ops — FIFO, 2 ideas
IDEA-065 (CI `playwright install chromium`), IDEA-080 (fill `render.md` TODO(owner) rows).

**The top of the tech-debt list and today's retrospective converged independently.**
IDEA-110 is CARD-319's family (a ref resolved by mention, not definition) and IDEA-109 is
ADR-0039/R4's family (a figure whose instrument is unproven). The two highest-scoring
tech-debt ideas on the board are the two families that cost waves 63–66 the most — and
**both already have cards**: CARD-319 (blocked, code outside this repo) and CARD-304
(stamped into wave 67 today). IDEA-007's validator ERROR is the ADR-0025 regex artefact
already known to be a false positive in the plugin-cache copy.

## Signals consulted

- **⚑ Historical drift**: compliance **−15pp** under plan, feature **+10pp** over
  (waves 63–65). Consistent with the headline above.
- **⚑ Tech-debt aging — the signal is BROKEN and must not be used.** 29 cards tracked,
  21 open, and **every one reads `Deferred waves: 0`**, including CARD-220 created in wave
  37 and still `ready` at wave 66. The retro's Step 4c increments only cards *in the
  current wave scope*, so a card never scheduled never ages. Its `estimated_interest_d:
  1.0d` is an artefact of a stuck counter; **real open tech-debt is ~19d across 21 cards**.
- Effort calibration: python-pro/feature avg **2.05×** (4 cards) — `confidence: low`, so
  not surfaced per-idea; and the entry carries `bimodal: true` because the mean is true of
  no card in the sample.
- No risk register, no `intents.md`, no `weights.md`, no `constraints.md`, no research
  synthesis → no risk, interest-weight, constraint or anti-positioning screens ran.
  `assumptions.md` exists but no idea binds to an ASM.

## No Wave 1 allocation is published, and that is deliberate

There is no `waves.duration` or `waves.capacity_d` configured, so there is no wave budget
in days or person-weeks to fill — and with the category mix above, percentages of an
unknown budget would be a fabricated number. **More decisively: throughput is not
backlog-constrained.** The board carries **49 open cards**, of which **14 claim
`src/nonogram/admin/book_pdf_generator.py`**, and the card that would end that contention
(CARD-273) `Depends on:` 21 others. Adding scored ideas to the front of that queue changes
nothing downstream.

## Next step — triage, not architect

`/forge:architect` is the skill's usual next step and it is **not** the right one here:
the top-ranked items are tech-debt with cards already cut, and the feature list is three
items one of which is an owner-look follow-up.

What would actually move: **(1)** decide the stage/capacity question above; **(2)** triage
the 107 — route the ~105 process findings out of the product backlog into rule promotions
or card amendments, and score the genuine remainder; **(3)** resolve CARD-273's ordering,
which is the actual throughput constraint.
