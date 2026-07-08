# IJ Ride — Backend (Django + DRF + Channels)

## Local setup

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements\dev.txt
copy .env.example .env   # then edit values (a working .env is already present in dev)
```

Create the PostgreSQL database (once), then migrate and run:

```powershell
# in psql as the postgres superuser: CREATE DATABASE ijride;
python manage.py migrate
python manage.py createsuperuser   # prompts for phone + password
python manage.py runserver
```

- API base: `http://127.0.0.1:8000/api/v1/`
- Health check: `http://127.0.0.1:8000/healthz/`
- Django admin: `http://127.0.0.1:8000/admin/`

## Settings

`config/settings/` is split into `base.py`, `dev.py` (default), and `prod.py`.
Select via `DJANGO_SETTINGS_MODULE`. All secrets/config come from `.env`
(see `.env.example` for the full list).

## Apps

| App | Responsibility |
|---|---|
| `apps.accounts` | custom phone-based User, roles, auth API |
| `apps.drivers` | driver profile, vehicle, availability, approval |
| `apps.rides` | ride lifecycle + audit trail |
| `apps.payments` | cash/transfer payment records (gateway-ready) |
| `apps.pricing` | fare settings + fare calculation |
| `apps.geo` | geocoding/routing provider abstraction |
| `apps.realtime` | Channels consumers + event broadcast |
