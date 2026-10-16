# CARD-238 cycle 5 — claim sweep

Scope of this sweep, per the cycle-5 brief: the **four touched areas** and the
sentences this cycle's changes falsify. Nothing else. Anything found outside
them is listed under "recorded, not fixed" and left alone — breadth is what
has been costing this card.

Areas:

* **A** — the listing/globbing sets (`_LISTERS`, `_GLOBBERS`) and the new
  stdlib-surface audit
* **B** — the keyword omission in the listing rule (F-402)
* **C** — the path-wrapper guard (`_PATH_WRAPPERS`, F-403)
* **D** — the host-state probe set (`_HOST_STATE_PROBE` → `_HOST_STATE_PROBES`,
  F-401's second half and F-404)

Every claim below is one of: **PINNED** (a named control that is measured to go
red when the claim stops being true), **DELETED** (the sentence is gone rather
than requalified), or **RECORDED** (true, unpinnable or out of scope, and said
to be so in the file itself).

Legend for the controls: all node ids are in `tests/test_suite_profile.py`,
classes `TestSuiteTiming_NoTestReadsTheLiveLog` (path) and
`TestSuiteTiming_CollectsTheSameWithAndWithoutTheLog` (silence).

---

## A. the sets and the audit

| # | claim (where) | status | control / note |
|---|---|---|---|
| A1 | "every name on the live surface appears in the table" (comment above `STDLIB_DIRECTORY_SURFACE`) | PINNED | `test_every_spelling_the_stdlib_offers_is_classified` — measured red at 271 names with the table empty |
| A2 | "each set equals the table's projection, in both directions" (same comment) | PINNED | `test_the_listing_sets_are_exactly_the_classified_spellings` — measured red with `walk` deleted from `_LISTERS`, and red with a bogus `dirname` added to `_PATH_WRAPPERS` |
| A3 | the same for the probe half | PINNED | `test_the_host_state_probe_is_exactly_the_classified_spellings` — measured red with `exists` deleted from `_HOST_STATE_PROBES` |
| A4 | "every name the guards actually use exists in the library" | PINNED | `test_a_spelling_the_guards_use_is_a_real_stdlib_name` — measured red with an invented `listdirs` in the table and the set |
| A5 | "a name in two groups is red, so the grouping cannot quietly last-win" | PINNED | `test_no_spelling_is_classified_twice` — measured red with `walk` also in the pattern-helper group |
| A6 | "an exclusion is a decision on the record": every entry carries a reason and a known kind | PINNED | `test_every_classification_carries_a_reason` — measured red with one reason emptied |
| A7 | "every member of `_LISTERS`/`_GLOBBERS` has a positive control the guard catches" | PINNED | `test_every_listing_and_globbing_spelling_has_a_control` — measured red at `['fwalk', 'glob0', 'glob1', 'walk']` before the controls were written |
| A8 | **new this cycle**: "that control has to DEPEND on the membership" | PINNED | `test_the_control_for_each_spelling_depends_on_the_set` — measured red at `glob0`, on **this cycle's own first control**, which named `suite-timing.log` and so was caught by the string rule with `glob0` removed. The F-403 shape inside the pass that was fixing F-403; the control was changed to a pattern naming no log |
| A9 | the two mechanical surface filters (leading underscore; non-callable) "cannot drop a listing" (`_stdlib_directory_surface` docstring) | RECORDED | A judgement, stated with its mechanism: every listing/globbing rule fires on an `ast.Call`, so a non-callable cannot be one. Not pinnable by a control — a control would have to enumerate the thing the filter excludes, which is the surface again. Recorded here as the audit's one remaining judgement call |
| A10 | "the surface is the running interpreter's; a platform offering a name this host does not makes the audit red until it is classified" | PINNED | same mechanism as A1, already measured red. The *direction* is the point: unknown name → red, never silent |
| A11 | "the pre-classified Linux/Windows handful is complete for those hosts" | DELETED | It was in the first draft of that comment ("so it stays quiet on the hosts this repo runs on") and cannot be measured from macOS. Replaced with an explicit *non*-claim: the handful is a courtesy, its completeness is not measured and not claimed |
| A12 | "`glob0`/`glob1` are in `_GLOBBERS` because no reason to exclude them survived the asking" | RECORDED | a rationale, not a coverage claim; their membership is pinned by A2/A7/A8 |
| A13 | `_live_log_references`: "a listing of that directory **at all**" | DELETED | replaced by "by any spelling `STDLIB_DIRECTORY_SURFACE` classifies as one", which A1+A2 make falsifiable. This is cycle 4's F-401 sentence |
| A14 | `_live_log_references`: "**The five**, as of 2026-10-16: …" (the measured-misses enumeration read as closed) | DELETED | the count and the ordinals are gone; the paragraph points at `MEASURED_STRUCTURAL_MISSES`, which can grow without the prose going stale. Entries still pinned by `test_the_disclosed_structural_misses_are_still_misses` |
| A15 | `_build_sandbox` on G-1: "within the measured bound of … and **its five** `MEASURED_STRUCTURAL_MISSES`" | DELETED (count) / PINNED (bound) | the count is gone; the bound itself is the path guard's, pinned by `test_no_guarded_module_reaches_for_the_live_log` + the audit, and the sentence now says the bound got wider and why |
| A16 | module docstring: "**168 tests, 16.5-19.8s**" | corrected to measured fact | 341 tests, 16.5–16.7s over three runs at load 5.3–8.9, scans 1.3s each. A dated measurement record, not a standing property — so it is deliberately not pinned by a test; the date is what makes it honest. RECORDED as such |

## B. the keyword omission (F-402)

| # | claim | status | control / note |
|---|---|---|---|
| B1 | "a listing or a glob is judged by … the **positional and keyword** arguments" | PINNED | three new `REINTRODUCTIONS` controls: `os.listdir(path=KANBAN)`, bare `listdir(path=KANBAN)`, `os.scandir(path=…)`; all three measured as discriminating (caught with the member in `_LISTERS`, missed without) |
| B2 | "the omission was inconsistent inside this one function" | RECORDED | readable in the two adjacent branches; the string-operand branch has always read `node.keywords` |
| B3 | "the bare-imported spelling survived a whole module at 168 passed" | measured, historical | MUT-KB re-planted this cycle: now **3 failed, 237 passed** (path guard `{'tests/test_clues.py': ['listdir() of meta/kanban']}`, the silence equality, and the behavioural comparison transitively) |

## C. the wrapper guard (F-403)

| # | claim | status | control / note |
|---|---|---|---|
| C1 | "`_PATH_WRAPPERS` is exactly the KIND_WRAPPER projection" | PINNED | `test_the_listing_sets_are_exactly_the_classified_spellings`, measured red with `dirname` added |
| C2 | "Three members, each one a spelling somebody writes" | DELETED | the membership question is answered by the audit now, not by a judgement about what people write |
| C3 | "the set and the controls cannot drift apart" / "a member added here is exercised … rather than taken on trust" (cycle 4's wording, F-403's target) | DELETED | replaced by the honest statement: the generated test is **non-vacuity of the peel and nothing more**, and the two tests that *can* fail are named in its comment |
| C4 | "the narrowness is measured, not asserted" | PINNED | **new** `NOT_A_PATH_WRAPPER` + `test_a_wrapper_that_names_another_directory_is_not_peeled` (dirname / joinpath / with_name) — measured red when `dirname` is let into the set |
| C5 | "both shapes are peeled: a one-argument call and a no-argument method" | PINNED | `test_every_path_wrapper_is_seen_through` is now parametrized over both templates (40 cases), plus the `os.listdir(KANBAN.resolve())` entry in `REINTRODUCTIONS` |
| C6 | "`os.listdir(KANBAN.resolve())` was a miss until this cycle" | measured | re-ran `_live_log_references` with cycle 4's one-shape peel: `[]`; with this cycle's: `['listdir() of meta/kanban']` |

## D. the host-state probe set (F-401's second half, F-404)

| # | claim | status | control / note |
|---|---|---|---|
| D1 | "`_HOST_STATE_PROBES` is the table's projection" | PINNED | A3 |
| D2 | "the pattern built from the set fires on every member" | PINNED | `test_the_probe_pattern_fires_on_every_spelling_it_names` (52 cases) — measured red with one alternative dropped from `_probe_pattern` |
| D3 | "a skip gated on any member is reported" | PINNED | `test_a_skip_gated_on_any_probe_is_reported` (52 cases, generated from the set). Stated in its own comment to be a mechanism control, **not** a bound on the set |
| D4 | `_conditional_silences`: "Measured limits … a skip keyed on an environment variable" | PINNED (was prose only) | **new** `NOT_A_CONDITIONAL_SILENCE` entry; doubles as the negative control for `os.getenv` being KIND_NEITHER |
| D5 | "… and a skip from an `except` handler rather than an `if`" | PINNED, and RECORDED as a hole | **new** `NOT_A_CONDITIONAL_SILENCE` entry. The mechanism fix (reading `except` handlers) is **out of this cycle's scope**; the bound is written down and goes red the day the detector grows past it |
| D6 | the old `_HOST_STATE_PROBE` hand-written regex | DELETED | replaced by `_probe_pattern(_HOST_STATE_PROBES)`; the new pattern is a strict superset of the old on all nine of its names (checked alternative by alternative) |
| D7 | "the shape the hand-written pattern had for **exactly two** of its members" (my own first draft) | corrected | it was four alternatives (`os.path.exists/isfile/isdir`, `os.listdir`). A false count written in the pass that is about false counts; corrected in place |
| D8 | widening the probe does not change what is reported elsewhere | measured | `_conditional_silences` over all guarded sources with the widened set: the same **four** entries as `MEASURED_SILENCES_ELSEWHERE`, and `[]` for this module. Pinned by `test_the_host_state_silences_elsewhere_are_exactly_the_measured_ones` and `test_nothing_in_this_module_goes_quiet_on_a_condition` |
| D9 | the env-var survivor | RECORDED, still open | re-measured this cycle: 341 passed with `CARD238_MUT_LOG` set to an existing absolute path (nothing red), loud when unset. Documented as surviving at `_live_log_references`, with `os.getenv`'s KIND_NEITHER classification and D4 as its negative control |

---

## recorded, not fixed (out of this cycle's scope)

* **F-405** (cycle 4, Minor) — `MEASURED_SILENCES_ELSEWHERE`'s header says "Every
  **host-state** silence" and "**These three** are pre-existing" over **four**
  entries, one of which the same block says is not filesystem state. Still true
  of the file. Not touched: the data is unchanged by this cycle (the widened
  probe reports the same four), so it is not a sentence this cycle falsifies,
  and the brief's scope limit says to record rather than sweep. One-word fix for
  whoever opens that block next.
* **the `except`-handler skip** (D5) — a skip reached through
  `except FileNotFoundError` is not reported, because every rule in
  `_conditional_silences` reads `if`/mark conditions. Now a control and a
  written bound; the mechanism is a separate change.
* **the subprocess accounting** in the module docstring ("six `git ls-files`
  listings") — unchanged by this cycle and not re-verified; cycle 4 measured it.
* **F-306 / F-308** (deferred by cycle 4 to a follow-up card: `.gitignore` and a
  second guard module, both forbidden by G-4) — untouched.

## no [BLOCKER]

The audit polices both sets without a false positive on this host: the
completeness check is green at 307 classified names over a 271-name live
surface, `test_no_guarded_module_reaches_for_the_live_log` is `{}` over the
guarded tree, and the silence equality is unchanged at four entries. The one
place the audit cannot reach — whether the pre-classified other-platform
handful is complete — is written in the file as a non-claim (A11).

## counts, before → after (G-2: up, never down)

| corpus | cycle 4 | cycle 5 |
|---|---|---|
| tests in `tests/test_suite_profile.py` | 168 | 341 |
| `_LISTERS` | 3 | 5 |
| `_GLOBBERS` | 3 | 5 |
| `_PATH_WRAPPERS` | 3 | 20 |
| host-state probe spellings | 9 (regex alternatives) | 52 (audited set) |
| `REINTRODUCTIONS` (positive controls) | 36 | 47 |
| `INNOCENT_MENTIONS` | 10 | 10 |
| `NOT_A_PATH_WRAPPER` | — | 3 |
| `CONDITIONAL_SILENCES` | 9 | 9 |
| `NOT_A_CONDITIONAL_SILENCE` | 4 | 6 |
| `MEASURED_STRUCTURAL_MISSES` | 5 | 5 |
| `MEASURED_SILENCES_ELSEWHERE` | 4 | 4 |
| classified stdlib surface | — | 307 entries over a 271-name live surface, 18 reasons |

Nothing was removed. Two self-corrections are on the record above rather than
quietly fixed: the vacuous `glob0` control (A8) and the "exactly two members"
miscount (D7) — and a third, in this file: its first draft said the probe tests
run 53 cases when the set holds 52.
