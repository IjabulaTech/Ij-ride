# IJ Ride V1

A ride-hailing progressive web app for the Nigerian market — a focused,
launchable "simplified Bolt": passengers request rides, drivers accept and
complete them, admins run the operation. Cash and bank-transfer payments with
in-app confirmation (gateway-ready models for later).

## Stack

| Piece | Tech |
|---|---|
| Frontend (`frontend/`) | Next.js 16 · TypeScript · Tailwind CSS 4 · PWA (installable, offline fallback) |
| Backend (`backend/`) | Django 5.2 · DRF · Django Channels (WebSockets) · SimpleJWT (phone-number login) |
| Data | PostgreSQL · Redis (production channel layer) |
| Hosting | Vercel (frontend) · Render (API + DB + Redis + cron) — see [DEPLOYMENT.md](DEPLOYMENT.md) |

## Features

- **Passenger**: phone-number signup, fare estimate (provider-swappable
  geocoding/routing), ride request, live trip tracking over WebSocket,
  transfer "I have paid" claims, history, profile.
- **Driver**: onboarding (license + vehicle), admin approval workflow,
  online/offline with a live dispatch feed (first-accept-wins), trip
  progression (arrived/start/complete), payment confirmation, earnings.
- **Admin**: dashboard, users, driver approvals, ride records with full
  timelines, payment reconciliation, fare settings with pricing history.
- **Engineering**: full ride state machine under row-level locks + partial
  unique DB constraints, append-only ride event audit trail, JWT-authenticated
  WebSockets with poll fallback, 98 backend tests.

## Local development

Backend (Windows-friendly; PostgreSQL required, see [backend/README.md](backend/README.md)):

```powershell
cd backend
python -m venv .venv; .venv\Scripts\Activate.ps1
python -m pip install -r requirements\dev.txt
copy .env.example .env   # set your DATABASE_URL password
python manage.py migrate
python manage.py createsuperuser   # phone + password
python manage.py runserver         # http://127.0.0.1:8000 (HTTP + WS)
```

Frontend:

```powershell
cd frontend
npm install
copy .env.example .env.local       # defaults point at the local backend
npm run dev                        # http://localhost:3000
```

Seed an active fare setting in Django admin (`/admin/` → Fare settings) or via
the admin console, then register a passenger and a driver and ride.

## Testing & deployment

- `python manage.py test apps` — backend suite (98 tests)
- [TESTING.md](TESTING.md) — manual release checklist for every major flow
- [DEPLOYMENT.md](DEPLOYMENT.md) — Render + Vercel guide, env vars, launch checklist

## V1 scope boundaries

No online payment gateway (models are ready), no wallet/promos/ratings/chat,
broadcast dispatch (no proximity ranking), no native apps. These are
deliberate — the architecture leaves room for each.
