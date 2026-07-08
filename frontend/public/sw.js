/* IJ Ride service worker.
 *
 * Caching policy (deliberately conservative for a ride-hailing app):
 *  - API requests (different origin, or /api/*): NEVER intercepted — ride
 *    state, auth, and payments must always hit the network.
 *  - Navigations: network first; the precached /offline page when offline.
 *  - Hashed static assets (/_next/static/, /icons/): cache-first — their
 *    filenames change on every deploy, so they are safe to cache forever.
 *  - Everything else: untouched (browser default).
 */
// Bump this version whenever precached assets change (e.g. new branding) so
// clients drop the old cache on activate.
const CACHE = "ijride-v3";
const OFFLINE_URL = "/offline";
const PRECACHE = [
  OFFLINE_URL,
  "/brand/logo.png",
  "/brand/logo-mark.png",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE)
      .then((cache) => cache.addAll(PRECACHE))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;

  const url = new URL(request.url);

  // API and cross-origin (the Django backend) — always network.
  if (url.origin !== self.location.origin) return;
  if (url.pathname.startsWith("/api")) return;

  // Page navigations: network first, offline fallback.
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request).catch(() =>
        caches.match(OFFLINE_URL).then((cached) => cached ?? Response.error())
      )
    );
    return;
  }

  // Immutable hashed assets: cache-first.
  if (url.pathname.startsWith("/_next/static/") || url.pathname.startsWith("/icons/")) {
    event.respondWith(
      caches.match(request).then(
        (cached) =>
          cached ??
          fetch(request).then((response) => {
            if (response.ok) {
              const copy = response.clone();
              caches.open(CACHE).then((cache) => cache.put(request, copy));
            }
            return response;
          })
      )
    );
  }
});
