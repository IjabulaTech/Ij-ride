"use client";

import "leaflet/dist/leaflet.css";

import type * as L from "leaflet";
import { useCallback, useEffect, useRef, useState } from "react";

import { routeGeometry } from "@/lib/api/geo";

export interface LatLng {
  lat: number;
  lng: number;
}

/** How long to glide the car between two fixes (ms) — close to the send
 * cadence, so motion reads as continuous rather than teleporting. */
const ANIMATE_MS = 1_200;
/** Re-request the road route at most this often, or when the leg changes. */
const ROUTE_REFRESH_MS = 30_000;
/** Redraw the route if the car strays this far from the drawn path. */
const OFF_ROUTE_M = 150;

function metresBetween(a: LatLng, b: LatLng): number {
  const R = 6_371_000;
  const toRad = (d: number) => (d * Math.PI) / 180;
  const dLat = toRad(b.lat - a.lat);
  const dLng = toRad(b.lng - a.lng);
  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(a.lat)) * Math.cos(toRad(b.lat)) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}

function bearing(from: LatLng, to: LatLng): number {
  const toRad = (d: number) => (d * Math.PI) / 180;
  const y = Math.sin(toRad(to.lng - from.lng)) * Math.cos(toRad(to.lat));
  const x =
    Math.cos(toRad(from.lat)) * Math.sin(toRad(to.lat)) -
    Math.sin(toRad(from.lat)) * Math.cos(toRad(to.lat)) * Math.cos(toRad(to.lng - from.lng));
  return ((Math.atan2(y, x) * 180) / Math.PI + 360) % 360;
}

/** Car glyph pointing north; the wrapper is rotated by the driver's heading. */
function carHtml(rotation: number): string {
  return `<div style="transform: rotate(${rotation}deg); transition: transform .3s linear; width:34px; height:34px; display:grid; place-items:center;">
    <svg width="30" height="30" viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="11" fill="#ffffff" opacity="0.9"/>
      <path d="M12 2.5 L17 20 L12 16.5 L7 20 Z" fill="#111827"/>
    </svg>
  </div>`;
}

function dotHtml(color: string, size = 16): string {
  return `<div style="width:${size}px;height:${size}px;border-radius:50%;background:${color};border:3px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.4)"></div>`;
}

export interface LiveMapProps {
  /** Driver's latest position; null until the first fix arrives. */
  driver: (LatLng & { heading?: number | null }) | null;
  /** Where the driver is currently heading. */
  target: LatLng & { label: string; kind: "pickup" | "dropoff" };
  /** The viewer's own position (passenger), if known. */
  self?: LatLng | null;
  selfLabel?: string;
  className?: string;
}

/**
 * Live tracking map on OpenStreetMap tiles via Leaflet — no API key, no
 * billing. Shows an animated car marker, the pickup/destination marker, the
 * passenger, and the road route between car and target. The camera keeps
 * everything in view until the user pans, then offers "Re-centre".
 *
 * Leaflet touches `window`, so it is imported dynamically inside an effect to
 * stay clear of server rendering.
 */
export function LiveMap({
  driver,
  target,
  self = null,
  selfLabel = "You",
  className = "",
}: LiveMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const leafletRef = useRef<typeof L | null>(null);
  const mapRef = useRef<L.Map | null>(null);
  const carRef = useRef<L.Marker | null>(null);
  const targetRef = useRef<L.Marker | null>(null);
  const selfRef = useRef<L.Marker | null>(null);
  const routeRef = useRef<L.Polyline | null>(null);

  const animationRef = useRef<number | null>(null);
  const shownPos = useRef<LatLng | null>(null);
  const routeFetchedAt = useRef(0);
  const routeLeg = useRef<string>("");
  const routePath = useRef<LatLng[]>([]);

  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");
  const [following, setFollowing] = useState(true);

  // ---- boot the map once ----
  useEffect(() => {
    let cancelled = false;
    import("leaflet")
      .then((mod) => {
        const leaflet = (mod.default ?? mod) as typeof L;
        if (cancelled || !containerRef.current || mapRef.current) return;
        leafletRef.current = leaflet;

        const map = leaflet.map(containerRef.current, {
          center: [driver?.lat ?? target.lat, driver?.lng ?? target.lng],
          zoom: 14,
          zoomControl: true,
          attributionControl: true,
        });
        // NOTE: use the plain host, NOT "{s}.tile.openstreetmap.org" — OSM has
        // deprecated the a/b/c subdomains and those requests now fail, which
        // renders markers over a blank background. Verified in a browser.
        leaflet
          .tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
            maxZoom: 19,
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
          })
          .addTo(map);

        routeRef.current = leaflet
          .polyline([], { color: "#2563eb", weight: 5, opacity: 0.85 })
          .addTo(map);

        // Any manual pan hands control to the user until they re-centre
        map.on("dragstart", () => setFollowing(false));
        mapRef.current = map;
        setReady(true);
        // Tiles can mis-measure inside a freshly laid-out card
        setTimeout(() => map.invalidateSize(), 200);
      })
      .catch((err: Error) => {
        console.error("LiveMap failed to initialise:", err);
        if (!cancelled) setError("Map could not load. Tracking details still update below.");
      });

    return () => {
      cancelled = true;
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
      mapRef.current?.remove();
      mapRef.current = null;
    };
    // One-shot: markers and camera are handled by the effects below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ---- target marker ----
  useEffect(() => {
    const leaflet = leafletRef.current;
    const map = mapRef.current;
    if (!ready || !leaflet || !map) return;
    const colour = target.kind === "pickup" ? "#059669" : "#dc2626";
    const icon = leaflet.divIcon({
      html: dotHtml(colour),
      className: "",
      iconSize: [16, 16],
      iconAnchor: [8, 8],
    });
    if (!targetRef.current) {
      targetRef.current = leaflet
        .marker([target.lat, target.lng], { icon, title: target.label })
        .addTo(map);
    } else {
      targetRef.current.setLatLng([target.lat, target.lng]);
      targetRef.current.setIcon(icon);
    }
  }, [ready, target.lat, target.lng, target.kind, target.label]);

  // ---- the viewer's own marker ----
  useEffect(() => {
    const leaflet = leafletRef.current;
    const map = mapRef.current;
    if (!ready || !leaflet || !map) return;
    if (!self) {
      selfRef.current?.remove();
      selfRef.current = null;
      return;
    }
    const icon = leaflet.divIcon({
      html: dotHtml("#2563eb", 14),
      className: "",
      iconSize: [14, 14],
      iconAnchor: [7, 7],
    });
    if (!selfRef.current) {
      selfRef.current = leaflet
        .marker([self.lat, self.lng], { icon, title: selfLabel })
        .addTo(map);
    } else {
      selfRef.current.setLatLng([self.lat, self.lng]);
    }
  }, [ready, self, selfLabel]);

  // ---- fit the camera around everything that matters ----
  const fitCamera = useCallback(() => {
    const leaflet = leafletRef.current;
    const map = mapRef.current;
    if (!leaflet || !map) return;
    const points: [number, number][] = [[target.lat, target.lng]];
    if (shownPos.current) points.push([shownPos.current.lat, shownPos.current.lng]);
    if (self) points.push([self.lat, self.lng]);
    if (points.length === 1) {
      map.setView(points[0], Math.max(map.getZoom(), 15));
      return;
    }
    map.fitBounds(leaflet.latLngBounds(points), { padding: [40, 40], maxZoom: 17 });
  }, [self, target.lat, target.lng]);

  // ---- animate the car between fixes ----
  useEffect(() => {
    const leaflet = leafletRef.current;
    const map = mapRef.current;
    if (!ready || !leaflet || !map || !driver) return;

    const destination = { lat: driver.lat, lng: driver.lng };
    const reported = typeof driver.heading === "number" ? driver.heading : null;

    const paint = (position: LatLng, rotation: number) => {
      const icon = leaflet.divIcon({
        html: carHtml(rotation),
        className: "",
        iconSize: [34, 34],
        iconAnchor: [17, 17],
      });
      if (!carRef.current) {
        carRef.current = leaflet
          .marker([position.lat, position.lng], { icon, title: "Driver", zIndexOffset: 1000 })
          .addTo(map);
      } else {
        carRef.current.setLatLng([position.lat, position.lng]);
        carRef.current.setIcon(icon);
      }
    };

    const from = shownPos.current;
    // First fix (or a big jump): place it directly, no animation
    if (!from || metresBetween(from, destination) > 2_000) {
      shownPos.current = destination;
      paint(destination, reported ?? 0);
      fitCamera();
      return;
    }

    const rotation = reported ?? bearing(from, destination);
    const start = performance.now();
    const step = (now: number) => {
      const t = Math.min(1, (now - start) / ANIMATE_MS);
      const eased = 1 - (1 - t) ** 2; // ease-out so the car settles
      const current = {
        lat: from.lat + (destination.lat - from.lat) * eased,
        lng: from.lng + (destination.lng - from.lng) * eased,
      };
      shownPos.current = current;
      paint(current, rotation);
      if (t < 1) {
        animationRef.current = requestAnimationFrame(step);
      } else if (following) {
        fitCamera();
      }
    };
    if (animationRef.current) cancelAnimationFrame(animationRef.current);
    animationRef.current = requestAnimationFrame(step);

    return () => {
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
    };
  }, [ready, driver, following, fitCamera]);

  // ---- road route from the car to the target, refreshed sparingly ----
  useEffect(() => {
    const line = routeRef.current;
    if (!ready || !line || !driver) return;

    const legChanged = routeLeg.current !== target.kind;
    const stale = Date.now() - routeFetchedAt.current > ROUTE_REFRESH_MS;
    const offRoute =
      routePath.current.length > 0 &&
      Math.min(...routePath.current.map((p) => metresBetween(p, driver))) > OFF_ROUTE_M;
    if (!legChanged && !stale && !offRoute) return;

    routeFetchedAt.current = Date.now();
    routeLeg.current = target.kind;
    let cancelled = false;
    routeGeometry(driver.lat, driver.lng, target.lat, target.lng)
      .then((data) => {
        if (cancelled || !routeRef.current) return;
        const points = data.points.map(([lat, lng]) => ({ lat, lng }));
        routePath.current = points;
        routeRef.current.setLatLngs(data.points as [number, number][]);
        routeRef.current.setStyle({ opacity: data.source === "route" ? 0.85 : 0.5 });
      })
      .catch(() => {
        // Routing unavailable — draw a direct line so the map still conveys
        // direction and distance.
        if (cancelled || !routeRef.current) return;
        const straight: [number, number][] = [
          [driver.lat, driver.lng],
          [target.lat, target.lng],
        ];
        routePath.current = straight.map(([lat, lng]) => ({ lat, lng }));
        routeRef.current.setLatLngs(straight);
        routeRef.current.setStyle({ opacity: 0.5 });
      });
    return () => {
      cancelled = true;
    };
  }, [ready, driver, target.lat, target.lng, target.kind]);

  function recentre() {
    setFollowing(true);
    fitCamera();
  }

  if (error) {
    return (
      <div
        className={`flex items-center justify-center rounded-lg border border-dashed border-gray-300 bg-gray-50 p-4 text-center text-sm text-gray-500 ${className}`}
      >
        {error}
      </div>
    );
  }

  return (
    <div className={`relative overflow-hidden rounded-lg border border-gray-200 ${className}`}>
      <div ref={containerRef} className="h-full w-full" />
      {!ready && (
        <div className="absolute inset-0 z-[500] flex items-center justify-center bg-gray-50 text-sm text-gray-500">
          Loading map…
        </div>
      )}
      {ready && !following && (
        <button
          type="button"
          onClick={recentre}
          className="absolute bottom-3 right-3 z-[500] rounded-full bg-white px-3 py-2 text-xs font-semibold text-gray-700 shadow-md ring-1 ring-gray-200 hover:bg-gray-50"
        >
          Re-centre
        </button>
      )}
    </div>
  );
}
