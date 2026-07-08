# IJ Ride V1 — Manual Test Checklist

Automated coverage: **98 backend tests** (`python manage.py test apps` from
`backend/`) covering auth, onboarding/approval, geo/fares, the full ride state
machine with locking, payments, and WebSocket flows. This checklist is the
human pass for release candidates — run it against staging/production, or
locally with two browser windows (one normal, one incognito).

Suggested cast: **Passenger P**, **Driver D** (approved, vehicle, online),
**Admin A**.

## 1 — Accounts & auth
- [ ] Register a passenger with a local-format phone (`0803...`) → lands on the passenger dashboard; phone stored as `+234...`
- [ ] Register a driver → driver dashboard shows PENDING notice
- [ ] Log out / log in; wrong password → clear error; duplicate phone on register → field error
- [ ] Deep-link a passenger URL as a driver (e.g. `/passenger/history`) → redirected to `/driver`

## 2 — Driver onboarding & approval
- [ ] D (pending) cannot go online (dashboard shows approval gate)
- [ ] D fills license + vehicle in Profile; duplicate plate number → field error
- [ ] A approves D in `/admin/drivers` → D's dashboard unlocks after refresh
- [ ] A rejects another driver **without** a reason → blocked; with a reason → driver sees the reason
- [ ] Approved D changes license number → status returns to PENDING and D is forced offline

## 3 — Booking & fare estimate (as P)
- [ ] Estimate with two addresses → fare ≥ minimum, multiple of the rounding step, sensible distance/duration
- [ ] Change fare settings as A, estimate again → new tariff applies immediately
- [ ] Request ride (transfer) → active ride screen shows "Finding driver"
- [ ] Try booking a second ride (new tab) → blocked with a link to the active ride
- [ ] Cancel while searching → ride cancelled; can book again
- [ ] Leave a request unaccepted past the timeout (default 10 min) → becomes EXPIRED with a re-request prompt

## 4 — Dispatch & trip lifecycle
- [ ] D goes online → new request appears in D's feed **without reloading**
- [ ] Second driver accepts first → D's accept fails with "no longer available" and the card disappears for both
- [ ] On accept: P sees driver name, vehicle, plate, and a working Call link — live, no reload
- [ ] D taps arrived → start → complete; P's stepper tracks each step live
- [ ] P's cancel button disappears once the trip starts
- [ ] D cannot cancel without a reason; A **can** cancel an in-progress ride

## 5 — Payments
- [ ] Cash ride: after completion D sees "Collect ₦X", confirms → PAID on both sides
- [ ] Transfer ride: P taps "I have sent the transfer" with a reference during/after the trip → D sees the claim + reference live → D confirms → PAID
- [ ] Double-confirm → clean "already confirmed" error
- [ ] D's earnings: gross = sum of completed fares; paid/unpaid split matches confirmations
- [ ] A sees all records in `/admin/payments`; search by transfer reference works

## 6 — Admin console
- [ ] Dashboard counts match reality (users, pending drivers, rides, unsettled payments)
- [ ] Users/rides/payments tables filter and paginate
- [ ] Ride detail shows the full timeline (requested → ... → completed) and payment record
- [ ] Non-admin calling a `/management/` URL directly → 403

## 7 — Realtime resilience
- [ ] Kill the backend briefly mid-ride → frontend recovers via reconnect/poll (status catches up within ~10 s of restart)
- [ ] Two devices/windows on the same ride never show contradictory statuses after settle

## 8 — PWA
- [ ] Production build: install prompt on desktop Chrome / Android; app opens standalone
- [ ] DevTools → offline → navigating shows the offline page; going back online recovers
- [ ] API responses are never served from cache (check DevTools Network while offline: API calls fail rather than return stale rides)
