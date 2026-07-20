"use client";

import { useEffect, useState } from "react";

import { formatDistance, formatDuration } from "@/lib/format";
import type { DriverLocationEvent } from "@/types/api";

/** Seconds after which a position is treated as stale (driver lost GPS/network). */
const STALE_AFTER_S = 45;

function useSecondsSince(timestamp: number | null): number {
  const [, tick] = useState(0);
  useEffect(() => {
    if (timestamp === null) return;
    const timer = setInterval(() => tick((n) => n + 1), 5_000);
    return () => clearInterval(timer);
  }, [timestamp]);
  return timestamp === null ? 0 : Math.round((Date.now() - timestamp) / 1000);
}

/**
 * Live distance + ETA for the leg currently being driven. Shown to the
 * passenger (driver approaching) and to the driver (distance to go).
 * Phase 2 adds the map itself; this is the numeric readout beside it.
 */
export function LiveTrackingCard({
  event,
  receivedAt,
  audience,
}: {
  event: DriverLocationEvent | null;
  /** Date.now() when the last event arrived — drives the staleness notice. */
  receivedAt: number | null;
  audience: "passenger" | "driver";
}) {
  const age = useSecondsSince(receivedAt);
  const stale = receivedAt !== null && age > STALE_AFTER_S;

  if (!event) {
    return (
      <div className="rounded-lg border border-dashed border-gray-300 bg-white p-3 text-sm text-gray-500">
        {audience === "passenger"
          ? "Waiting for your driver's location…"
          : "Waiting for a GPS signal…"}
      </div>
    );
  }

  const heading = event.target.kind === "pickup" ? "To pickup" : "To destination";
  const lead =
    audience === "passenger"
      ? event.target.kind === "pickup"
        ? "Driver arriving in"
        : "Arriving in"
      : "You arrive in";

  return (
    <div className="rounded-lg border border-blue-200 bg-blue-50/60 p-3">
      <div className="flex items-baseline justify-between gap-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-blue-700">{heading}</p>
        {stale && (
          <span className="text-xs font-medium text-amber-600">Signal lost — last known</span>
        )}
      </div>
      <div className="mt-1 flex items-baseline gap-3">
        <div>
          <p className="text-2xl font-extrabold leading-tight text-gray-900">
            {formatDuration(event.eta.duration_s)}
          </p>
          <p className="text-xs text-gray-500">{lead}</p>
        </div>
        <div className="ml-auto text-right">
          <p className="text-lg font-bold leading-tight text-gray-900">
            {formatDistance(event.eta.distance_m)}
          </p>
          <p className="text-xs text-gray-500">remaining</p>
        </div>
      </div>
      <p className="mt-2 truncate text-xs text-gray-600">{event.target.address}</p>
      {event.eta.source === "estimate" && (
        <p className="mt-1 text-[11px] text-gray-400">Approximate — routing unavailable.</p>
      )}
    </div>
  );
}
