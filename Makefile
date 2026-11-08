# Harness targets for the forge kanban pipeline.
#
# `cmd-start-review` prefers a `test-impact` target here over its own inline
# per-stack recipes ("one source of truth"), which is what makes
# `meta/kanban/config.yml`'s `review.test_scope: impact` mean anything: the
# skill's python-pro recipe narrows only with pytest-testmon installed and
# otherwise falls back to the full suite while the gate note claims to be
# scoped. pytest-testmon is not in this venv, deliberately -- see
# scripts/impact_set.py, which is where the selection logic and its honest
# bounds live.
#
# `test` is the full suite and the definition of done. `test-impact` is a CYCLE
# gate only. Narrowing is safe because the full suite still runs at the merge
# gate; it is not an alternative to that run.
#
# Since CARD-395 the MERGE GATE is `test-gate`, which does not run the tests
# marked `wave_close_only` (the heaviest property sweeps and mutant grids; the
# registry is tests/wave_close_marker.py) unless the changed paths lift them,
# and which says how many it left for the wave close. The WAVE CLOSE is
# `test-wave-close`: the bare suite, marker and all. `test` stays bare too.

PY ?= ./.venv/bin/python
BASE ?= $(shell git merge-base HEAD main 2>/dev/null || echo main)
FILES ?=

.PHONY: test test-impact impact-set test-gate test-marked test-wave-close

## Full suite, BARE: no marker deselection, nothing narrowed. What a local full
## run and the wave smoke test run, and what the merge gate runs when the answer
## is a conftest / pytest-config / Makefile / selector change (CARD-395 rule A).
test:
	$(PY) -m pytest

## WAVE CLOSE: the full suite, no marker deselection. Refuses to run when
## PYTEST_ADDOPTS carries any option that drops tests: -m/--markexpr, -k,
## --deselect, --ignore (--ignore-glob included). A wave close that deselected
## anything is not the backstop. Options that only change reporting are fine.
test-wave-close:
	@if printf '%s' "$$PYTEST_ADDOPTS" | grep -Eq '(^| )(-[A-Za-z]*[mk]|--markexpr|--deselect|--ignore)'; then \
		echo "test-wave-close: PYTEST_ADDOPTS deselects tests (-m/--markexpr/-k/--deselect/--ignore); the wave close is the bare suite. Unset it." >&2; \
		exit 2; \
	fi
	@echo "WAVE CLOSE: full suite, no marker deselection"
	$(PY) -m pytest

## The tests the gate defers (marker `wave_close_only`), alone: for a bisect
## over a wave's merges when the wave close reds in one of them, or a
## pre-wave-close check.
test-marked:
	$(PY) -m pytest -m wave_close_only

## MERGE GATE (CARD-395): derive the gate's block, print it, run the command(s)
## it names, propagate the exit code.
##
##   make test-gate                 # changes against the merge-base with main
##   make test-gate BASE=<rev>
##
## PY defaults to ./.venv/bin/python, which a card WORKTREE does not have: there,
## pass PY=/abs/path/to/main/.venv/bin/python (and PYTHONPATH=<worktree>/src).
##
## `run N:` lines in the block are the commands; `python` in them is $(PY).
## Exit codes of impact_set.py --gate: 0 selection, 10 FULL, 11 count failed
## (= FULL, run bare), 12 EMPTY (nothing to run, and NOT a pass: check BASE).
## The block's closing sentence says 'nothing more is owed AT THIS GATE' and
## states how many marked tests are owed at the wave close.
test-gate:
	@set +e; \
	block=$$($(PY) scripts/impact_set.py --gate --against $(BASE)); code=$$?; \
	printf '%s\n' "$$block"; \
	if [ $$code -eq 12 ]; then exit 12; fi; \
	if [ $$code -ne 0 ] && [ $$code -ne 10 ] && [ $$code -ne 11 ]; then \
		echo "test-gate: impact_set.py exited $$code; nothing was run" >&2; exit $$code; \
	fi; \
	cmds=$$(printf '%s\n' "$$block" | sed -n 's|^run [0-9]*: python |$(PY) |p'); \
	if [ -z "$$cmds" ]; then echo "test-gate: the block names no command; nothing was run" >&2; exit 3; fi; \
	printf '%s\n' "$$cmds" | { rc=0; while IFS= read -r cmd; do echo "+ $$cmd"; sh -c "$$cmd" || rc=1; done; exit $$rc; }

## Print the derived selection without running it -- for reading a gate's scope
## before spending it.
impact-set:
	@if [ -n "$(FILES)" ]; then \
		$(PY) scripts/impact_set.py $(FILES); \
	else \
		$(PY) scripts/impact_set.py --base $(BASE); \
	fi

## Cycle gate: run only the tests the changed paths can affect.
##
##   make test-impact                      # changes against the merge-base with main
##   make test-impact BASE=<rev>           # against another revision
##   make test-impact FILES="a.py b.py"    # an explicit changed set
##
## Falls back to the full suite whenever the selection is FULL, and says so, so
## a scoped gate and a full one are never confused in a card's evidence. An
## empty changed set runs nothing and reports that -- a no-op gate is a fact
## about the diff, not a pass to be quoted as one.
test-impact:
	@set -e; \
	if [ -n "$(FILES)" ]; then \
		sel=$$($(PY) scripts/impact_set.py $(FILES)); \
	else \
		sel=$$($(PY) scripts/impact_set.py --base $(BASE)); \
	fi; \
	if [ "$$sel" = "FULL" ]; then \
		echo "impact: FULL -- the selection could not be narrowed; running the whole suite"; \
		$(PY) -m pytest; \
	elif [ -z "$$sel" ]; then \
		echo "impact: no changed path affects any test -- nothing to run"; \
	else \
		n=$$(printf '%s\n' "$$sel" | grep -c .); \
		echo "impact: $$n test file(s) selected"; \
		printf '%s\n' "$$sel" | sed 's/^/  /'; \
		printf '%s\n' "$$sel" | xargs $(PY) -m pytest; \
	fi
