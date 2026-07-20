"use client";

import { useEffect, useRef, useState, type RefObject } from "react";

import type { RideSocket } from "@/lib/ws";

/** Don't send more often than this, however fast fixes arrive. */
const MIN_SEND_MS = 4_000;
/** Send even when stationary, so the passenger knows the driver is still live. */
const HEARTBEAT_MS = 20_000;
/** Ignore jitter below this many metres unless the heartbeat is due. */
const MIN_MOVE_M = 10;

function metresBetween(aLat: number, aLng: number, bLat: number, bLng: number): number {
  const R = 6_371_000;
  const toRad = (d: number) => (d * Math.PI) / 180;
  const dLat = toRad(bLat - aLat);
  const dLng = toRad(bLng - aLng);
  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(aLat)) * Math.cos(toRad(bLat)) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}

export type GpsState = "idle" | "watching" | "denied" | "unavailable";

/**
 * Streams the driver's GPS over the ride socket while a trip is active.
 *
 * Battery/bandwidth: one `watchPosition` subscription, but sends are throttled
 * and skipped when the driver hasn't really moved — with a heartbeat so the
 * passenger's map never looks frozen. Stops entirely when `active` is false.
 */
export function useDriverLocationStream(
  socketRef: RefObject<RideSocket | null>,
  active: boolean
): GpsState {
  const [state, setState] = useState<GpsState>("idle");
  const lastSentAt = useRef(0);
  const lastPos = useRef<{ lat: number; lng: number } | null>(null);

  useEffect(() => {
    if (!active) {
      setState("idle");
      return;
    }
    if (typeof navigator === "undefined" || !navigator.geolocation) {
      setState("unavailable");
      return;
    }

    setState("watching");
    const watchId = navigator.geolocation.watchPosition(
      (pos) => {
        setState("watching");
        const { latitude, longitude, heading, speed, accuracy } = pos.coords;
        const now = Date.now();
        const sinceSend = now - lastSentAt.current;
        if (sinceSend < MIN_SEND_MS) return;

        const moved = lastPos.current
          ? metresBetween(lastPos.current.lat, lastPos.current.lng, latitude, longitude)
          : Infinity;
        if (moved < MIN_MOVE_M && sinceSend < HEARTBEAT_MS) return;

        socketRef.current?.sendLocation({
          lat: latitude,
          lng: longitude,
          heading: Number.isFinite(heading) ? heading : null,
          speed: Number.isFinite(speed) ? speed : null,
          accuracy: Number.isFinite(accuracy) ? accuracy : null,
        });
        lastSentAt.current = now;
        lastPos.current = { lat: latitude, lng: longitude };
      },
      (err) => {
        // 1 = PERMISSION_DENIED. Anything else is a transient/unavailable fix.
        setState(err.code === 1 ? "denied" : "unavailable");
      },
      { enableHighAccuracy: true, maximumAge: 5_000, timeout: 20_000 }
    );

    return () => {
      navigator.geolocation.clearWatch(watchId);
      setState("idle");
    };
  }, [active, socketRef]);

  return state;
}
