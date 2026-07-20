"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { loadGoogleMaps, mapsKeyConfigured } from "@/lib/maps/loader";

export interface LatLng {
  lat: number;
  lng: number;
}

/** How long to glide the car between two fixes (ms). Matches the send cadence
 * closely enough that motion looks continuous rather than teleporting. */
const ANIMATE_MS = 1_200;
/** Re-request a road route at most this often, or when the target changes. */
const ROUTE_REFRESH_MS = 30_000;
/** Redraw the route if the car strays this far from the drawn path. */
const OFF_ROUTE_M = 150;

/** A car silhouette pointing "north" — rotated by the driver's heading. */
const CAR_SYMBOL =
  "M -1.2,-2.4 L 1.2,-2.4 C 1.6,-2.4 1.8,-2 1.8,-1.4 L 1.8,2 C 1.8,2.5 1.5,2.8 1.1,2.8 " +
  "L -1.1,2.8 C -1.5,2.8 -1.8,2.5 -1.8,2 L -1.8,-1.4 C -1.8,-2 -1.6,-2.4 -1.2,-2.4 Z";

function toLatLng(lat: string | number, lng: string | number): LatLng {
  return { lat: Number(lat), lng: Number(lng) };
}

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

export interface LiveMapProps {
  /** Driver's latest position; null until the first fix arrives. */
  driver: (LatLng & { heading?: number | null }) | null;
  /** Where the driver is currently heading. */
  target: LatLng & { label: string; kind: "pickup" | "dropoff" };
  /** The viewer's own position (passenger), if known. */
  self?: LatLng | null;
  /** Label for the self marker. */
  selfLabel?: string;
  className?: string;
}

/**
 * Live tracking map: an animated car marker, a target marker, the road route
 * between them, and a camera that keeps both in view until the user pans.
 *
 * Everything is driven imperatively against the Google Maps JS API so the car
 * can be interpolated frame-by-frame instead of jumping between fixes.
 */
export function LiveMap({
  driver,
  target,
  self = null,
  selfLabel = "You",
  className = "",
}: LiveMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<google.maps.Map | null>(null);
  const carRef = useRef<google.maps.Marker | null>(null);
  const targetRef = useRef<google.maps.Marker | null>(null);
  const selfRef = useRef<google.maps.Marker | null>(null);
  const routeRef = useRef<google.maps.Polyline | null>(null);
  const directionsRef = useRef<google.maps.DirectionsService | null>(null);

  // Animation + camera bookkeeping
  const animationRef = useRef<number | null>(null);
  const shownPos = useRef<LatLng | null>(null);
  const routeFetchedAt = useRef(0);
  const routeTargetKind = useRef<string>("");
  const routePath = useRef<LatLng[]>([]);
  const userPanned = useRef(false);

  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");
  const [following, setFollowing] = useState(true);

  // ---- boot the map once ----
  useEffect(() => {
    let cancelled = false;
    if (!mapsKeyConfigured()) {
      setError("Map unavailable — NEXT_PUBLIC_GOOGLE_MAPS_KEY is not configured.");
      return;
    }
    loadGoogleMaps()
      .then((maps) => {
        if (cancelled || !containerRef.current) return;
        if (typeof maps.Map !== "function") {
          throw new Error("maps.Map unavailable");
        }
        const map = new maps.Map(containerRef.current, {
          center: driver ?? target,
          zoom: 14,
          disableDefaultUI: true,
          zoomControl: true,
          rotateControl: true, // compass
          gestureHandling: "greedy",
          clickableIcons: false,
          mapTypeControl: false,
          streetViewControl: false,
          fullscreenControl: false,
        });
        mapRef.current = map;
        directionsRef.current = new maps.DirectionsService();
        routeRef.current = new maps.Polyline({
          map,
          geodesic: true,
          strokeColor: "#2563eb",
          strokeOpacity: 0.85,
          strokeWeight: 5,
        });
        // Any manual pan/zoom hands control to the user until they re-centre
        map.addListener("dragstart", () => {
          userPanned.current = true;
          setFollowing(false);
        });
        setReady(true);
      })
      .catch((err: Error) => {
        // Keep the real cause in the console; users get something readable.
        console.error("LiveMap failed to initialise:", err);
        if (!cancelled) setError("Map could not load. Tracking details still update below.");
      });
    return () => {
      cancelled = true;
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
    };
    // Intentionally one-shot: markers/camera update in the effects below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ---- target marker ----
  useEffect(() => {
    const maps = window.google?.maps;
    if (!ready || !maps || !mapRef.current) return;
    const position = { lat: target.lat, lng: target.lng };
    if (!targetRef.current) {
      targetRef.current = new maps.Marker({
        map: mapRef.current,
        position,
        title: target.label,
        icon: {
          path: maps.SymbolPath.CIRCLE,
          scale: 8,
          fillColor: target.kind === "pickup" ? "#059669" : "#dc2626",
          fillOpacity: 1,
          strokeColor: "#ffffff",
          strokeWeight: 3,
        },
      });
    } else {
      targetRef.current.setPosition(position);
      targetRef.current.setTitle(target.label);
      targetRef.current.setIcon({
        path: maps.SymbolPath.CIRCLE,
        scale: 8,
        fillColor: target.kind === "pickup" ? "#059669" : "#dc2626",
        fillOpacity: 1,
        strokeColor: "#ffffff",
        strokeWeight: 3,
      });
    }
  }, [ready, target.lat, target.lng, target.kind, target.label]);

  // ---- the viewer's own marker ----
  useEffect(() => {
    const maps = window.google?.maps;
    if (!ready || !maps || !mapRef.current) return;
    if (!self) {
      selfRef.current?.setMap(null);
      selfRef.current = null;
      return;
    }
    if (!selfRef.current) {
      selfRef.current = new maps.Marker({
        map: mapRef.current,
        position: self,
        title: selfLabel,
        zIndex: 2,
        icon: {
          path: maps.SymbolPath.CIRCLE,
          scale: 6,
          fillColor: "#2563eb",
          fillOpacity: 1,
          strokeColor: "#ffffff",
          strokeWeight: 2,
        },
      });
    } else {
      selfRef.current.setPosition(self);
    }
  }, [ready, self, selfLabel]);

  // ---- fit the camera around everything that matters ----
  const fitCamera = useCallback(() => {
    const maps = window.google?.maps;
    const map = mapRef.current;
    if (!maps || !map) return;
    const bounds = new maps.LatLngBounds();
    if (shownPos.current) bounds.extend(shownPos.current);
    bounds.extend({ lat: target.lat, lng: target.lng });
    if (self) bounds.extend(self);
    if (bounds.isEmpty()) return;
    map.fitBounds(bounds, { top: 60, right: 40, bottom: 60, left: 40 });
  }, [self, target.lat, target.lng]);

  // ---- animate the car between fixes ----
  useEffect(() => {
    const maps = window.google?.maps;
    if (!ready || !maps || !mapRef.current || !driver) return;

    const destination = { lat: driver.lat, lng: driver.lng };
    const heading = typeof driver.heading === "number" ? driver.heading : null;

    const paint = (position: LatLng, rotation: number | null) => {
      const icon: google.maps.Symbol = {
        path: CAR_SYMBOL,
        scale: 5,
        fillColor: "#111827",
        fillOpacity: 1,
        strokeColor: "#ffffff",
        strokeWeight: 1.5,
        rotation: rotation ?? 0,
        anchor: new maps.Point(0, 0),
      };
      if (!carRef.current) {
        carRef.current = new maps.Marker({
          map: mapRef.current,
          position,
          icon,
          zIndex: 3,
          title: "Driver",
        });
      } else {
        carRef.current.setPosition(position);
        carRef.current.setIcon(icon);
      }
    };

    const from = shownPos.current;
    // First fix (or a huge jump): place it directly, no animation
    if (!from || metresBetween(from, destination) > 2_000) {
      shownPos.current = destination;
      paint(destination, heading);
      fitCamera();
      return;
    }

    // Derive heading from travel when the device didn't report one
    const bearing =
      heading ??
      maps.geometry?.spherical.computeHeading(
        new maps.LatLng(from.lat, from.lng),
        new maps.LatLng(destination.lat, destination.lng)
      ) ??
      0;

    const start = performance.now();
    const step = (now: number) => {
      const t = Math.min(1, (now - start) / ANIMATE_MS);
      // ease-out so the car settles instead of stopping dead
      const eased = 1 - (1 - t) ** 2;
      const current = {
        lat: from.lat + (destination.lat - from.lat) * eased,
        lng: from.lng + (destination.lng - from.lng) * eased,
      };
      shownPos.current = current;
      paint(current, bearing);
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
    const service = directionsRef.current;
    const line = routeRef.current;
    if (!ready || !service || !line || !driver) return;

    const now = Date.now();
    const targetChanged = routeTargetKind.current !== target.kind;
    const stale = now - routeFetchedAt.current > ROUTE_REFRESH_MS;
    const offRoute =
      routePath.current.length > 0 &&
      Math.min(...routePath.current.map((p) => metresBetween(p, driver))) > OFF_ROUTE_M;
    if (!targetChanged && !stale && !offRoute) return;

    routeFetchedAt.current = now;
    routeTargetKind.current = target.kind;
    service.route(
      {
        origin: { lat: driver.lat, lng: driver.lng },
        destination: { lat: target.lat, lng: target.lng },
        travelMode: google.maps.TravelMode.DRIVING,
      },
      (result, status) => {
        if (status !== google.maps.DirectionsStatus.OK || !result?.routes?.[0]) {
          // Routing unavailable — fall back to a direct line so the map still
          // communicates direction and distance.
          const straight = [{ lat: driver.lat, lng: driver.lng }, { lat: target.lat, lng: target.lng }];
          routePath.current = straight;
          line.setPath(straight);
          line.setOptions({ strokeOpacity: 0.5 });
          return;
        }
        const path = result.routes[0].overview_path.map((p) => ({ lat: p.lat(), lng: p.lng() }));
        routePath.current = path;
        line.setPath(path);
        line.setOptions({ strokeOpacity: 0.85 });
      }
    );
  }, [ready, driver, target.lat, target.lng, target.kind]);

  function recentre() {
    userPanned.current = false;
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
        <div className="absolute inset-0 flex items-center justify-center bg-gray-50 text-sm text-gray-500">
          Loading map…
        </div>
      )}
      {ready && !following && (
        <button
          type="button"
          onClick={recentre}
          className="absolute bottom-3 right-3 rounded-full bg-white px-3 py-2 text-xs font-semibold text-gray-700 shadow-md ring-1 ring-gray-200 hover:bg-gray-50"
        >
          Re-centre
        </button>
      )}
    </div>
  );
}

export { toLatLng };
