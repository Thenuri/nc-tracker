# NC Tracker – APIIT Sri Lanka

Internal web app to record, validate, track and close non-conformities (NCs) across APIIT departments, in preparation for the ISO Stage 2 external audit.

The full requirements are in `docs/SRS.md`. **Read it before making design decisions.** Requirement IDs (FR-01, NFR-05, etc.) refer to that document; mention them in commit messages and code comments where relevant.

## Current stage: PROTOTYPE that will become the real system

We are building the real app now, but three things are provided later by APIIT IT. Until then they use **swappable stand-ins**. Keep each stand-in isolated so it can be replaced without touching the rest of the code.

| Real (later, from IT) | Stand-in (now) | Where it lives |
| --- | --- | --- |
| Microsoft Entra ID login (apiit.lk accounts) | "Who am I?" role switcher in the navbar (dev only) | `accounts/` app, enabled only when `PROTOTYPE_MODE = True` |
| Outlook email from shared mailbox (nctracker@apiit.lk) | Notifications saved to DB and shown in an on-screen panel; Django console email backend | `notifications/services.py` → single `notify()` function |
| APIIT server + PostgreSQL | Laptop + SQLite | `settings.py` via environment variables |

Rules for stand-ins:
- All notifications go through ONE function: `notify(recipient, subject, message, nc=None)`. It always saves a `Notification` record AND calls Django's `send_mail`. Switching to real email = changing settings only.
- Never check roles by reading the switcher directly. Always use `request.user` and helper permission functions, so real login drops in cleanly.
- Show a visible "PROTOTYPE – sample data" banner when `PROTOTYPE_MODE = True`.
- All config (DB, email, secrets, PROTOTYPE_MODE) comes from environment variables via a `.env` file (use `django-environ`). Never hard-code secrets.

## Tech stack

- Python 3.12, Django 5.x
- SQLite (dev) → PostgreSQL (production)
- Django templates + Bootstrap 5 (no React/SPA)
- Chart.js for dashboard charts
- django-simple-history for the audit trail (FR-42)
- openpyxl for Excel export, WeasyPrint for PDF
- Scheduled management command for daily overdue checks and reminders
- Later: MSAL or django-auth-adfs for Microsoft login; Microsoft Graph or SMTP for email

Keep dependencies minimal. Ask before adding any new package.

## Suggested project structure

```
nc_tracker/          # Django project settings
accounts/            # User model, roles, role switcher (stand-in)
core/                # Departments, processes, sources (lists managed by NC Manager)
ncs/                 # NC model, workflow rules, views, forms
  workflow.py        # THE ONLY place status transitions are defined
notifications/       # Notification model + notify() service
dashboard/           # Register, filters, dashboard, exports
templates/
static/
docs/SRS.md
```

## Roles

- **NC Manager** (+ delegate with identical rights): the only role that can log NCs, decide disputes, verify, close and reopen. Manages lists via Django admin.
- **HoD**: head of a department. Can view ALL NCs read-only (FR-30). Can edit only NCs where their department is the receiving department (FR-40). Validates/disputes and assigns the Action Owner.
- **Action Owner**: staff member assigned to an NC. Enters root cause, corrective action, dates and evidence on their assigned NCs.
- **Management**: read-only access to everything, including dashboard and exports.
- Raising department can view NCs it raised but cannot change them.

A user has a `role` and a `department`. "HoD of department X" = `Department.hod`.

## NC statuses and allowed transitions (Section 3 of SRS)

```
(new)                -> PENDING_VALIDATION     NC Manager logs NC; notify receiving HoD
PENDING_VALIDATION   -> VALID                  Receiving HoD confirms
PENDING_VALIDATION   -> DISPUTED               Receiving HoD says not valid (reason required); notify NC Manager
DISPUTED             -> VALID                  NC Manager overturns (rationale required)
DISPUTED             -> NOT_VALID              NC Manager upholds (rationale required)
VALID                -> IN_PROGRESS            Root cause, action, owner, target date all recorded
IN_PROGRESS          -> PENDING_VERIFICATION   Completion date + evidence required (FR-19)
PENDING_VERIFICATION -> CLOSED                 NC Manager marks effective
PENDING_VERIFICATION -> IN_PROGRESS            NC Manager marks not effective (comments required)
CLOSED               -> IN_PROGRESS            NC Manager reopens (reason required, audit trail) (FR-24)
```

- `OVERDUE` is NOT a status. It is a computed flag: validation deadline or target date has passed and status is not CLOSED or NOT_VALID.
- All transitions MUST go through `ncs/workflow.py`, which checks: allowed from/to, user permission, required fields. Views never set `status` directly.
- NCs can never be deleted by anyone (FR-43). Disable delete in admin too.
- Closed NCs are locked except for NC Manager reopen.
- Changing the target date requires a reason and keeps the original date (FR-20).

## Defaults for [TBC] items (make these configurable settings, not hard-coded)

- Validation deadline: 3 working days (Mon–Fri)
- Reminder to Action Owner: 7 days before target date
- Escalate to NC Manager: 14 days overdue
- Same-department NCs: still require validation
- Severity (Minor/Major): optional field
- NC ID format: `NC-YYYY-###`, sequence resets each year

## UI guidelines

- Plain language labels, mobile-friendly, Bootstrap only.
- Each user sees only the actions they're allowed to take on an NC page; hide the rest.
- Status colours: red = overdue, amber = due within 7 days, green = on track or closed.
- Receiving department fills in no more than 4 action-planning fields plus evidence (NFR-02).

## Sample data

Provide a management command `python manage.py load_sample_data` that creates realistic APIIT-style departments (e.g. Academic, Admissions, Finance, Examinations, Student Services, IT, HR, Library), one HoD each, a few Action Owners, an NC Manager, a delegate, a Management user, and ~20 NCs spread across all statuses, including overdue and cross-department disputed ones. Clearly fake names only.

## Working style

- Work in small steps, one phase at a time. Explain briefly what you changed and how to test it.
- Write tests for `workflow.py` (every allowed and blocked transition) and for permissions.
- After each phase, tell me the exact commands to run and what to click to check it works.
- I am still learning, so keep code readable, with short comments explaining the "why".

## Build phases

1. Project setup, settings from `.env`, Bootstrap base template, prototype banner
2. Models: User/roles, Department, Process, Source, NC, Evidence, ProgressNote, TargetDateChange, Notification; history on NC
3. Role switcher stand-in + permission helpers + sample data command
4. `workflow.py` + tests
5. Screens in order: log NC → validate/dispute → decide dispute → action plan → evidence → verify/close
6. Register with filters (FR-32) + dashboard (FR-33, FR-34, FR-35)
7. Overdue flag, reminders command, notifications panel, Excel/PDF export, printable NC record
8. Demo run-through: cross-department disputed NC from logging to closure
9. (Later, with IT) Microsoft login, real email, PostgreSQL, deployment
