# CARD-235 — the browser family's teardown, before and after

Both halves are `meta/profiling/rank_durations.py`'s own output on a **solo
run under `meta/kanban/.full-suite.lock`**, by CARD-217's method (G-3). Nothing
here was counted by hand. To reproduce:

```bash
./.venv/bin/python meta/profiling/rank_durations.py \
    meta/profiling/suite-durations-20261015.txt         # before (CARD-217)
./.venv/bin/python meta/profiling/rank_durations.py \
    meta/profiling/card-235-durations-after.txt         # after  (this card)
```

| artefact | run | sha256 |
|---|---|---|
| before — `suite-durations-20261015.txt` | 2026-10-15T05:19Z, CARD-217 | `7d204cf956580d9f36a223ee196a3d0b739fe5124a5af50265938630a37e760e` |
| after — `card-235-durations-after.txt` | 2026-10-15T10:41Z, poll 0.05 s | `f987166a577d5550446f15c45433c51b67bc632c072b215ceac5a7ab3cdf6dbf` |
| rejected — `card-235-durations-poll-001.txt` | 2026-10-15T09:20Z, poll 0.01 s | `e21f35b5f078dc3be42e197fb323c928e15b4f500c0b948f55cbe92d9536a012` |

The after artefact is deliberately not named `suite-durations-<date>.txt`: that
name is CARD-217's, `tests/test_suite_profile.py` holds a one-profile-per-date
pairing contract around it, and these are further profiles on the same day
rather than further CARD-217 profiles.
`tests/test_browser_fixture_scope.py` carries the equivalent checks for this
pair — admissibility, the sha256 citation, and the deciding table quoted
verbatim — by calling the same script.

---

## The headline

| | before | after | change |
|---|---|---|---|
| browser family, time | 366.19 s | 256.57 s | **−109.62 s** |
| browser family, share of attributed time | 39.78 % | 29.78 % | **−10.00 points** |
| browser family, teardown | 137.97 s | 11.62 s | **−126.35 s** |
| browser family, tests | 422 | 422 | +0 |
| suite wall clock | 930.81 s | 871.02 s | -59.79 s (SUPERSEDED — see below) |

**The wall-clock row is stale and the realised net is about half of it.**
Corrected at review (CARD-235 cycle 2, F-008) rather than left standing. The
after-profile above is pinned by digest to `77428ce`, and at that commit this
card's own guard file `tests/test_browser_fixture_scope.py` cost **23.99 s**,
with its two order-independence runs at 6.99 s and 4.82 s. The review cycle
then moved the order probe from a 5-test file to a 15-test one (F-003), and
those two runs are now 21.51 s and 20.29 s, taking the guard file to a
self-reported **54.05 s** — roughly +30 s that the pinned artefact cannot see,
because every bar in `_failed_bars` reads the frozen artefact and the digest
pins the artefact to itself rather than to the tree.

What did NOT move: the **−126.35 s family teardown saving**, which is what this
card is actually about. The guard file sits outside the
`tests/test_puzzle_solver` prefix, so it is not in the family being measured,
and none of the rows above it are affected. What moved is the net — the card
returns ~126 s to the family and spends ~54 s of it on the guards that keep the
saving from silently disappearing (cycle 1 proved it could: mutant M2 restored
the whole 126 s and 20 tests still passed).

Treat the two drift-immune figures as the card's claim — the family-to-rest
ratio (0.660 → 0.424) and per-test teardown (0.327 → 0.028 s). No wall-clock
saving is claimed: two consecutive runs of an identical tree differed by 60 s
(6.9 %) on this host, which is the same variance CARD-217 warned about.

**Read the share with one caveat, and the ratio instead.** The rest of the
suite — everything outside the family — ran at 83 ms/test in the before
run and 90 ms/test in the after run, +7.6 %, which is
host drift on a machine CARD-217 already measured a 19 % run-to-run spread on.
A slower remainder inflates the denominator and so flatters the family's share.
The ratio of the family to the rest of the suite cancels that drift entirely:

| | before | after |
|---|---|---|
| family / rest of suite | **0.660** | **0.424** |

36 % off the family's cost relative to the suite it runs in — a figure no
amount of host drift can produce, since drift moves both terms together.

## Where the saving is: teardown, and only teardown

| phase | before | after | change |
|---|---|---|---|
| family setup | 30.70 s | 26.12 s | -4.58 s |
| family call | 197.52 s | 218.83 s | +21.31 s |
| family teardown | 137.97 s | 11.62 s | **-126.35 s** |
| whole-suite teardown | 144.37 s | 17.14 s | — |

Per browser test, teardown went **0.327 s to 0.028 s**.
Family `call` rose +10.8 %, against the remainder's
+7.6 % — the same drift, so the chosen interval costs the test bodies
nothing. The whole of the −109.62 s is the teardown line.

## What the 0.33 s actually was

CARD-217 attributed the family's 0.33 s per-test teardown — 137.97 s, 96 % of
the entire suite's teardown — to Chromium's per-test page lifecycle, and
CARD-235 was cut to collapse it by widening the `browser_page` fixture's scope.
Measurement says the page lifecycle is not the cost.

1. **The page lifecycle is 57 ms, not 330 ms.** One `new_context` + `new_page`
   + close, measured 20 times against a launched Chromium on this host, costs
   57 ms; with a shared context it is 57 ms too, so the cost is the page and
   not the context. Collapsing it for all 422 tests would be worth ~24 s, and
   it would be a *setup* saving — where the family spent only 30.70 s in
   total.
2. **The 0.33 s was `socketserver.serve_forever`'s 0.5 s poll interval.** The
   per-test `live` fixture serves the real Flask panel on a thread and stops it
   with `server.shutdown()`, which cannot return until the serve loop next
   wakes up. At the stdlib default that is a uniform 0–0.5 s wait on every
   test's teardown, and `shutdown()` + `join()` mean no test can observe the
   difference either way.

CARD-217's own evidence says so in hindsight. Its teardown distribution was
"mean 0.327 s, median 0.370 s, stdev 0.144 s, max 0.520 s", bimodal with the
mass at 0.3–0.5 s and "no tail at all, stopping dead at 0.520 s". A hard
ceiling at 0.52 s with a flat spread beneath it is the signature of a bounded
poll wait; a browser teardown would have a tail. Its 41-test cluster near zero
is the family's non-browser tests, which never ask for `live` — CARD-217 read
that as "tests that tear nothing down", which is exactly right and was the clue.

The repo already knew the lesson. `tests/test_web_server.py` has carried
`_POLL_INTERVAL_S = 0.01` since it was written, commented "The stdlib default
of 0.5s would be paid on every test's teardown here". The browser family's
fixture never got the memo.

## Why 0.05 s and not the 0.01 s next door

Copying that neighbour's value was the first attempt, and the full-suite
profile of it is committed as `card-235-durations-poll-001.txt` because it is
the measurement that rejected it:

| | before (0.5 s) | poll 0.01 s | poll 0.05 s |
|---|---|---|---|
| family total | 366.19 s | 306.45 s | 256.57 s |
| family call | 197.52 s | 279.99 s | 218.83 s |
| family teardown | 137.97 s | 3.33 s | 11.62 s |
| rest of suite, ms/test | 83 | 84 | 90 |

At 0.01 s the teardown collapsed as predicted but the family's `call` rose
42 % while the rest of the suite held flat at 84 ms/test — so
that was not host drift. A solo back-to-back A/B over all twelve files
confirmed it (`card-235-poll-interval-ab.txt`): 0.01 s buys 8.19 s more
teardown than 0.05 s and costs 92.97 s of call, and a separate two-round A/B on
the family's call-heaviest file, run in a different order, ranks the three
intervals the same way. The mechanism: at 100 Hz the serve thread takes the GIL
from a main thread driving Chromium through synchronous RPC, so a handoff lands
in the middle of a round trip. At 20 Hz that cost is gone and 91 % of the
teardown saving remains. `test_web_server.py` can afford 0.01 s because nothing
there runs a browser on the other side of the GIL — which is why this is a
constant per file and not one shared between them.

## Why no file's page scope changed

The card named three candidate shapes and said to choose on measurement. The
measurement chose the third for all twelve: sharing a page is worth ~24 s and
costs the whole of the order-dependence risk, while the poll interval is worth
−109.62 s and costs nothing a test can observe.

Every one of the twelve mutates page state that navigating does not undo — a
viewport its assertions are computed from, a localStorage save it reloads to
recover, `page.route` interceptors, or `page.on("console")` handlers that would
accumulate so that a later test's output lands in an earlier test's list. The
per-file categories and reasons are declared in
`tests/test_puzzle_solver_page.PAGE_ISOLATION` and checked against the files
themselves by `TestBrowserFixtures_IsolationIsDeclaredPerFile`.

## Order-independence evidence

- All 422 tests of the family run in **reverse** order and in a **shuffled**
  order with seed **20261015** — `card-235-order-independence.txt`.
- Every test of the one file this card edits, run **alone**, plus one test from
  each of the other eleven — 78 runs, 78 passed —
  `card-235-tests-alone.txt`.
- A deliberate failure on one page leaves its neighbours passing —
  `TestBrowserFixtures_AFailureDoesNotCascade`.

---

## Before — the deciding table, verbatim from `rank_durations.py`

```
(the deciding table)

family                                   total   share  tests  ms/test
browser family (Chromium)              366.19s  39.78%    422      868
render-heavy frozen set                195.42s  21.23%   1079      181
property corpora                       140.19s  15.23%    184      762
property AND render                     70.75s   7.68%     11     6432
property OR render                     264.86s  28.77%   1252      212
admin-local script trio                117.16s  12.73%     83     1412
everything but the browser family      554.44s  60.22%   6660       83
```

## After — the deciding table, verbatim from `rank_durations.py`

```
(the deciding table)

family                                   total   share  tests  ms/test
browser family (Chromium)              256.57s  29.78%    422      608
render-heavy frozen set                217.65s  25.26%   1079      202
property corpora                       141.55s  16.43%    184      769
property AND render                     72.91s   8.46%     11     6628
property OR render                     286.29s  33.23%   1252      229
admin-local script trio                122.67s  14.24%     83     1478
everything but the browser family      605.06s  70.22%   6757       90
```
