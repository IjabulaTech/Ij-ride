# IJ Ride V1 — Deployment Guide

Two deployables: the **Django API** (Render) and the **Next.js PWA** (Vercel),
plus PostgreSQL and Redis on Render. Deploy the backend first — the frontend
needs its URL.

```
Vercel (frontend)  ──HTTPS/WSS──▶  Render web service (Django ASGI: HTTP + WebSocket)
                                     ├── Render PostgreSQL
                                     ├── Render Key Value (Redis, channel layer)
                                     └── Render cron: expire_rides every 5 min
```

## Prerequisites

- Code pushed to a GitHub repository (this folder as repo root — `render.yaml`
  must be at the root).
- Render account, Vercel account.
- Optional for launch: a Mapbox access token (free tier) for real geocoding.

---

## Part 1 — Backend on Render

### Option A: Blueprint (recommended)

1. Render dashboard → **New → Blueprint** → select the repo. Render reads
   [render.yaml](render.yaml) and creates: web service `ijride-api`, cron
   `ijride-expire-rides`, PostgreSQL `ijride-db`, Redis `ijride-redis`, and the
   `ijride-shared` env group.
2. Fill the values marked `sync: false` when prompted:
   - `SECRET_KEY` (env group): a long random string — generate with
     `python -c "import secrets; print(secrets.token_urlsafe(64))"`.
   - `MAPBOX_ACCESS_TOKEN` (env group): may stay empty while `GEO_PROVIDER=stub`.
   - `ALLOWED_HOSTS` (web): the service host, e.g. `ijride-api.onrender.com`.
   - `CORS_ALLOWED_ORIGINS` (web): placeholder for now; set after Part 2, e.g.
     `https://ijride.vercel.app`.
3. Deploy. The build script installs deps, runs `collectstatic`, and applies
   migrations automatically.

### Option B: Manual service

Web service → runtime Python, root directory `backend`,
build command `./build.sh`,
start command `python -m uvicorn config.asgi:application --host 0.0.0.0 --port $PORT`,
health check path `/healthz/`. Create the database, the Key Value instance,
and a cron job (`python manage.py expire_rides`, every 5 minutes) by hand, and
set the env vars from the checklist below.

### First-deploy tasks (Render Shell tab on ijride-api)

```bash
python manage.py createsuperuser        # prompts for PHONE (e.g. +234...) + password
```

Then open `https://<api-host>/admin/` and create the first **active
FareSetting** (Pricing → Fare settings), or use the admin console's Fare
settings page once the frontend is up. Without an active fare setting, ride
estimates return a clear 400 error.

### Backend env var checklist

| Variable | Where | Value |
|---|---|---|
| `DJANGO_SETTINGS_MODULE` | group | `config.settings.prod` |
| `SECRET_KEY` | group | long random string — never reuse the dev one |
| `DATABASE_URL` | linked | from `ijride-db` |
| `REDIS_URL` | linked | from `ijride-redis` |
| `ALLOWED_HOSTS` | web | comma-separated API hosts (no scheme) |
| `CORS_ALLOWED_ORIGINS` | web | comma-separated frontend origins (with `https://`) |
| `GEO_PROVIDER` | group | `stub` → **`mapbox` for launch** |
| `MAPBOX_ACCESS_TOKEN` | group | required when provider is `mapbox` |
| `GEO_COUNTRY` / `GEO_PROXIMITY` | group | `NG` / `12.4954,9.2035` (Yola lng,lat bias) |
| `DEFAULT_COUNTRY_CODE` | group | `+234` |
| `RIDE_SEARCH_TIMEOUT_MINUTES` | group | `10` |
| `JWT_ACCESS_MINUTES` / `JWT_REFRESH_DAYS` | group | `60` / `30` |

---

## Part 2 — Frontend on Vercel

1. Vercel → **Add New → Project** → import the repo.
2. **Root Directory: `frontend`** (framework auto-detects Next.js; default
   build settings are correct).
3. Environment variables:

| Variable | Value |
|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | `https://<api-host>/api/v1` |
| `NEXT_PUBLIC_WS_URL` | `wss://<api-host>/ws/rides/` |

   Note `wss://` (not `ws://`) — browsers block insecure sockets from HTTPS pages.
4. Deploy, note the production domain (e.g. `https://ijride.vercel.app`).

## Part 3 — Close the CORS loop

Back on Render, set the web service's `CORS_ALLOWED_ORIGINS` to the exact
Vercel origin(s) — scheme included, no trailing slash — and let it redeploy.
If you add a custom domain to Vercel later, append it here too.

---

## Production readiness checklist

**Security**
- [ ] Fresh `SECRET_KEY` in production (never the one from `backend/.env`)
- [ ] `DJANGO_SETTINGS_MODULE=config.settings.prod` (DEBUG off, HSTS, secure cookies — verified by `manage.py check --deploy`)
- [ ] `ALLOWED_HOSTS` and `CORS_ALLOWED_ORIGINS` list only real domains
- [ ] Django `/admin/` reachable only by staff accounts with strong passwords

**Data & configuration**
- [ ] Superuser created; ops/admin accounts have role ADMIN
- [ ] Active FareSetting created with real tariffs
- [ ] `GEO_PROVIDER=mapbox` with a valid token (the stub geocodes to fake coordinates)
- [ ] Database backups: Render PostgreSQL daily backups available on paid plans — confirm the plan

**Operations**
- [ ] `expire_rides` cron running (check its Render logs after 10+ min with an unaccepted test ride)
- [ ] Health check green on `/healthz/`
- [ ] WebSocket smoke test from the production frontend (driver online sees requests instantly)
- [ ] Log review: Render web service logs are the V1 error channel (no Sentry yet)

**Frontend / PWA**
- [x] Official IJ Ride logo wired into icons, favicon, manifest, and in-app branding
- [ ] Install prompt appears on the production domain; Lighthouse PWA audit passes
- [ ] End-to-end smoke test on production using [TESTING.md](TESTING.md)

**Known V1 limitations (by design)**
- Payments are cash/transfer with manual confirmation — no gateway yet (models are gateway-ready).
- Dispatch is broadcast to all online drivers — no proximity ranking.
- No password reset or OTP login; no push notifications; no ratings/chat/promos.

## Scaling notes (when the time comes)

- The web service is stateless (state lives in Postgres/Redis) — scale by
  raising the instance count; Channels groups already work across instances
  via Redis.
- Add Paystack/Flutterwave by implementing a provider service + webhook that
  writes `provider`, `provider_ref`, and `status` on the existing Payment model.
- Swap/augment geo providers behind `apps/geo` without touching callers.
