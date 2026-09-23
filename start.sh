#!/bin/bash
# The deployed admin panel's server (CARD-086).
#
# `flask run` served this until now and warned about it on every boot: a
# development server, single-threaded, with no request timeout, no graceful
# shutdown and no worker supervision — carrying a public, credentialed admin
# panel since CARD-085.
#
# --timeout 120 is not a default left alone. It has to clear the worst case of
# the slowest route: `POST /regrade` stops starting new rows after
# REGRADE_BUDGET_SECONDS (60 s) and a row already started may run for
# GENERATION_BUDGET_SECONDS (30 s) more, so the ceiling is 90 s.
# tests/test_admin_serving.py reads this number and asserts it clears that sum,
# so the two cannot drift apart silently.
#
# WEB_CONCURRENCY stays at Render's 1 (CARD-086 G-4): nothing here has been
# examined for multi-worker safety, and the admin keeps in-memory state in its
# legacy non-DB mode.
#
# The app is loaded through the factory, so CARD-085's AdminConfigurationError
# still fails the boot rather than starting a worker that serves an open panel.
#
# The import path carries NO `src.` prefix, and that is load-bearing (2026-09-23).
# requirements.txt installs the package (`-e .`, packages found under src/), so
# `nonogram.admin.app` is the package's real name. Naming it `src.nonogram.admin.app`
# imports the whole package a SECOND time under a second name: `book_plan` then exists
# twice with two distinct LongestSideBucket enums, app.py (relative imports) holds one
# and book_manager (absolute) builds stored plans from the other, and Print setup dies
# with `ValueError: tuple.index(x): x not in tuple` on any book whose plan is stored.
# A plan-less book renders fine, which is what made it look like bad data in production.
# CARD-139 removes the underlying mixed-import trap; this line is the deployed fix.
exec gunicorn \
  --bind "0.0.0.0:$PORT" \
  --workers "${WEB_CONCURRENCY:-1}" \
  --timeout 120 \
  --graceful-timeout 30 \
  --access-logfile - \
  --error-logfile - \
  "nonogram.admin.app:create_app()"
