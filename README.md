# NC Tracker – APIIT Sri Lanka

Internal web app to record, validate, track and close non-conformities (NCs).
Requirements are in [docs/SRS.md](docs/SRS.md) and project rules in [CLAUDE.md](CLAUDE.md).

## First-time setup (Windows, PowerShell)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env        # then set SECRET_KEY in .env
python manage.py migrate
python manage.py createsuperuser
```

## Run

```powershell
.\.venv\Scripts\Activate.ps1
python manage.py runserver
```

Open http://127.0.0.1:8000/ (admin at http://127.0.0.1:8000/admin/).

## Tests

```powershell
python manage.py test
```
