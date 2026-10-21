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

PY ?= ./.venv/bin/python
BASE ?= $(shell git merge-base HEAD main 2>/dev/null || echo main)
FILES ?=

.PHONY: test test-impact impact-set

## Full suite. What the merge gate and the wave smoke test run.
test:
	$(PY) -m pytest

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
