# Render: what production actually runs

The admin panel is deployed on Render as the service `nonogram-admin`, served at
`nonogram-admin.onrender.com`. That service was created in the Render dashboard, not
from a Blueprint. **The dashboard's settings are authoritative; `render.yaml` is not.**
Render ignores the file for this service, so its `buildCommand`, `startCommand` and
`envVars` do not apply, and editing them changes nothing in production. The owner
decided on 2026-10-04 (IDEA-003, CARD-168) to keep the dashboard as the source of truth
and to record its settings here.

This page cannot read the dashboard. A value is filled in only where there is evidence
for it, and the evidence is dated. Everything else is marked
`TODO(owner): copy from the Render dashboard`. An observed fact describes the service
on the day it was observed. It is not a claim about today's settings.

## Settings

| Setting | Current value | Evidence |
| --- | --- | --- |
| Service type | Web Service. TODO(owner): copy from the Render dashboard (and the plan). | It serves HTTP at `nonogram-admin.onrender.com`. `render.yaml` says `type: web`, `plan: free`, but that file is not read. |
| Python version | TODO(owner): copy from the Render dashboard | Observed 2026-09-23: the service's venv path showed `python3.14`. `render.yaml` pins `PYTHON_VERSION: 3.11` and `runtime.txt` says `python-3.11.11`, so neither decided it then. |
| Build Command | TODO(owner): copy from the Render dashboard | None observed. `render.yaml`'s `pip install --upgrade pip && pip install -r requirements.txt && alembic upgrade head` is not read. |
| Start Command | TODO(owner): copy from the Render dashboard | Observed 2026-09-23: Flask's dev server (`flask run`) on `src.nonogram.admin.app`. Fixes merged since then (CARD-139 and others) may have led to a dashboard change, and none is recorded here. |
| Pre-Deploy Command | TODO(owner): copy from the Render dashboard (or "none") | None observed. |
| Auto-Deploy | TODO(owner): copy from the Render dashboard | The owner's policy is "off; deploy from the dashboard" (CARD-086 Q-2, comment in `render.yaml`). Whether the dashboard toggle matches that policy has not been checked. |
| Migrations on deploy | TODO(owner): copy from the Render dashboard (does the Build or Pre-Deploy Command run `alembic upgrade head`?) | Unknown. They run only if a dashboard command runs them, whatever `render.yaml` says. |

### Environment variables (names only)

Never write a value here. The dashboard holds the values.

The panel's code reads these names. This list shows what the code reads. It does not
show which of them the dashboard actually sets.

| Name | Read by | Set in the dashboard? |
| --- | --- | --- |
| `DATABASE_URL` | `src/nonogram/admin/app.py`, `src/nonogram/db/session.py`, `migrations/env.py` | TODO(owner): copy from the Render dashboard |
| `SECRET_KEY` | `src/nonogram/admin/app.py` | TODO(owner): copy from the Render dashboard |
| `ADMIN_ALLOWED_HOST` | `src/nonogram/admin/app.py` (CARD-085) | TODO(owner): copy from the Render dashboard |
| `ADMIN_USER` | `src/nonogram/admin/app.py` (CARD-085) | TODO(owner): copy from the Render dashboard |
| `ADMIN_PASSWORD` | `src/nonogram/admin/app.py` (CARD-085) | TODO(owner): copy from the Render dashboard |
| `FLASK_ENV` | `src/nonogram/admin/app.py` | TODO(owner): copy from the Render dashboard |
| `PYTHON_VERSION` | Render's Python runtime | TODO(owner): copy from the Render dashboard |
| `PORT`, `WEB_CONCURRENCY` | `start.sh` (Render provides `PORT`) | TODO(owner): copy from the Render dashboard |

TODO(owner): add any other names the dashboard sets that are not listed here.

## Evidence: the 2026-09-23 incident

It took four redeploys to see that the repo was not configuring production:

- **The access logs came from Werkzeug's dev server, not gunicorn.** They looked like
  `127.0.0.1 - - [23/Sep/2026 16:47:29] "GET / HTTP/1.1" 200 -`. Gunicorn writes
  `[23/Sep/2026:16:47:29 +0000]` and adds the response size and the user agent. So the
  server was `flask run`, and CARD-086's move to gunicorn (`start.sh`, which
  `render.yaml`'s `startCommand: bash start.sh` names) was being bypassed.
- **The app was loaded as `src.nonogram.admin.app`.** That import path loads the package
  twice and breaks Print setup for any book with a stored plan. The no-`src.` fix in
  `start.sh` (CARD-139 removed the underlying trap) survived three redeploys without
  reaching production, because production never ran `start.sh`.
- **The venv path showed `python3.14`,** while `render.yaml` pins 3.11.

The repo's `Procfile` contains `flask --app src.nonogram.admin.app run --host=0.0.0.0
--port=$PORT`, which matches what was observed. Nothing here shows whether the
dashboard's Start Command was copied from it.

## Drift check

Do this after any deploy-related change: a dashboard setting, `start.sh`,
`requirements.txt`, `pyproject.toml`'s `admin` extra, `migrations/`, or the Python
version.

1. **Dashboard vs. this page.** Open the service's Settings and Environment pages.
   Compare service type, Python version, Build Command, Pre-Deploy Command, Start
   Command, Auto-Deploy and the list of variable *names* with the tables above. Update
   this page wherever they differ, or replace a TODO with the value you saw, and date
   the edit.
2. **Dashboard vs. the repo's intent.** Does the Start Command run `bash start.sh`, i.e.
   gunicorn on `nonogram.admin.app:create_app()` with no `src.` prefix? Does the Build
   Command install `requirements.txt`? Does some command run `alembic upgrade head`, if
   migrations are meant to run on deploy? If not, either change the dashboard or write
   down here why it differs.
3. **What is actually serving.** After the deploy, read a few lines of the service's
   logs. Gunicorn's access-log lines (`[dd/Mon/yyyy:hh:mm:ss +0000]` with size and user
   agent) mean `start.sh` is running. Werkzeug's lines (`[dd/Mon/yyyy hh:mm:ss]`) or a
   "development server" warning mean it is not. Check that the Python version in the
   boot log matches the table.
4. **Do not fix production by editing `render.yaml`.** It changes nothing. Change the
   dashboard, then record the change here.
