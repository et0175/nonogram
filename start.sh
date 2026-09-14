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
exec gunicorn \
  --bind "0.0.0.0:$PORT" \
  --workers "${WEB_CONCURRENCY:-1}" \
  --timeout 120 \
  --graceful-timeout 30 \
  --access-logfile - \
  --error-logfile - \
  "src.nonogram.admin.app:create_app()"
