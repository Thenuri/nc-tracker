# NC Tracker – APIIT Sri Lanka

Internal web app to record, validate, track and close non-conformities (NCs).
Requirements are in [docs/SRS.md](docs/SRS.md), project rules in [CLAUDE.md](CLAUDE.md),
and a click-by-click demo in [docs/DEMO.md](docs/DEMO.md).

## First-time setup

The `.venv` folder is made for one operating system only, so create it on the
machine you use (it is git-ignored). Then fill in `.env`.

**macOS (Terminal)**

```bash
python3 -m venv .venv               # Python 3.12 or newer
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                # then set SECRET_KEY in .env
python manage.py migrate
python manage.py createsuperuser
python manage.py load_sample_data   # prototype only: fake staff and ~20 NCs
```

**Windows (PowerShell)**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env        # then set SECRET_KEY in .env
python manage.py migrate
python manage.py createsuperuser
python manage.py load_sample_data   # prototype only: fake staff and ~20 NCs
```

## Run

```bash
source .venv/bin/activate           # macOS
.\.venv\Scripts\Activate.ps1        # Windows
python manage.py runserver
```

Open http://127.0.0.1:8000/, click the initials circle (top right) and pick a person in
**Who am I?** (prototype mode). The **?** icon opens the user guide.
The NC Manager's **Manage lists** (departments, processes, sources, public holidays) is in the
same menu, or at http://127.0.0.1:8000/admin/.

## Tests

```bash
python manage.py test               # everything
python manage.py test ncs.test_demo # just the end-to-end demo
```

## Daily reminders

`python manage.py send_reminders` sends validation reminders, target-date reminders,
overdue alerts, escalations and (on Mondays) the weekly digest. Run it once a day:

- **Windows Task Scheduler:** create a daily task running
  `C:\path\to\nc-tracker\.venv\Scripts\python.exe C:\path\to\nc-tracker\manage.py send_reminders`
- **macOS (cron, for testing on a laptop):** run `crontab -e` and add
  `0 7 * * * cd ~/path/to/nc-tracker && .venv/bin/python manage.py send_reminders`
- **Linux server (cron):** `0 7 * * * /srv/nc-tracker/.venv/bin/python /srv/nc-tracker/manage.py send_reminders`

## PDF export

The register's **Export PDF** uses WeasyPrint. On Linux it works after
`pip install -r requirements.txt` (plus the `pango` system package). On macOS
run `brew install pango`; on Apple Silicon you may also need
`export DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib` before `runserver`. On Windows
it also needs the GTK/Pango runtime; without it the app shows a print-ready page
instead (use the browser's **Print → Save as PDF**). Excel export always works.

## Where things are

| Folder | What it holds |
| --- | --- |
| `accounts/` | User with role and department, permission rules (`permissions.py`), the prototype "Who am I?" switcher |
| `core/` | Departments, processes, sources; home page; `load_sample_data` |
| `ncs/` | NC model, **`workflow.py` (the only place statuses change)**, NC screens |
| `notifications/` | `notify()` (saves + emails), notifications panel, `send_reminders` |
| `dashboard/` | Register with filters, dashboard, Excel/PDF export |

## Settings

All configuration comes from `.env` (see `.env.example`): secret key, debug,
database URL, email, site URL, `PROTOTYPE_MODE`, and the [TBC] rules
(validation days, reminder and escalation days, same-department validation).

## Moving to production (Phase 9, with APIIT IT)

1. `PROTOTYPE_MODE=False`, `DEBUG=False`, real `SECRET_KEY`, `ALLOWED_HOSTS`, `SITE_URL`.
2. `DATABASE_URL=postgres://…` then `python manage.py migrate` (add `psycopg` to requirements).
3. Email: set `EMAIL_BACKEND=…smtp.EmailBackend` and `EMAIL_*` for nctracker@apiit.lk
   (or a Microsoft Graph backend). `notify()` does not change.
4. Microsoft Entra ID login (e.g. django-auth-adfs or MSAL): set `LOGIN_URL` to the
   Microsoft sign-in, remove the switcher (`accounts/views.py`, its URL and context
   processor). Permission rules already use `request.user`, so nothing else changes.
5. `python manage.py collectstatic`, serve with a WSGI server behind IIS/nginx, and
   keep `media/` (uploaded evidence) private and backed up.
6. Schedule `send_reminders` daily.
