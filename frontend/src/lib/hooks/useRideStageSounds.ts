"use client";

import { useEffect, useRef } from "react";

import { playBeep } from "@/lib/sound";
import type { Ride } from "@/types/api";

/**
 * Plays a beep when the given ride transitions INTO a sound-worthy stage —
 * once per transition, never on re-fetch / websocket reconnect / poll refresh.
 *
 * How dedup works: we derive a set of "announceable keys" from the ride's
 * current state (status + payment status). We remember which keys we've
 * already announced for this ride id. On the FIRST time we observe a ride
 * (initial load, or a reconnect that replays current state), we seed the
 * seen-set WITHOUT beeping — so joining a ride mid-flow doesn't fire sounds
 * for stages that already happened. Only genuinely new keys beep afterwards.
 * Changing ride id resets the tracking.
 */

const PASSENGER_STATUS_SOUNDS = new Set(["ACCEPTED", "DRIVER_ARRIVED", "IN_PROGRESS", "COMPLETED"]);
const DRIVER_STATUS_SOUNDS = new Set(["CANCELLED"]); // driver's own active ride cancelled

function announceableKeys(ride: Ride, role: "passenger" | "driver"): string[] {
  const keys: string[] = [];
  const statusSet = role === "passenger" ? PASSENGER_STATUS_SOUNDS : DRIVER_STATUS_SOUNDS;
  if (statusSet.has(ride.status)) keys.push(`s:${ride.status}`);

  const payment = ride.payment?.status;
  if (role === "passenger" && payment === "PAID") keys.push("p:PAID");
  // Driver needs to act when the passenger claims a transfer
  if (role === "driver" && payment === "CLAIMED") keys.push("p:CLAIMED");
  return keys;
}

export function useRideStageSounds(ride: Ride | null, role: "passenger" | "driver"): void {
  const seenRef = useRef<Set<string>>(new Set());
  const rideIdRef = useRef<number | null>(null);

  useEffect(() => {
    if (!ride) {
      rideIdRef.current = null;
      seenRef.current = new Set();
      return;
    }
    const keys = announceableKeys(ride, role);

    // New ride (or first observation): seed silently, no beep for the
    // stage we joined at.
    if (ride.id !== rideIdRef.current) {
      rideIdRef.current = ride.id;
      seenRef.current = new Set(keys);
      return;
    }

    for (const key of keys) {
      if (!seenRef.current.has(key)) {
        seenRef.current.add(key);
        playBeep("normal");
      }
    }
  }, [ride, role]);
}
