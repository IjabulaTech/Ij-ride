"use client";

import { useEffect, useState } from "react";

export interface Coords {
  lat: number;
  lng: number;
}

/** Watches the viewer's own position (used for the passenger's map marker).
 * Low-power settings — this only needs to be roughly right. */
export function useMyLocation(active: boolean): Coords | null {
  const [coords, setCoords] = useState<Coords | null>(null);

  useEffect(() => {
    if (!active || typeof navigator === "undefined" || !navigator.geolocation) return;
    const id = navigator.geolocation.watchPosition(
      (pos) => setCoords({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
      () => undefined, // no permission / no fix: the map simply omits the marker
      { enableHighAccuracy: false, maximumAge: 30_000, timeout: 20_000 }
    );
    return () => navigator.geolocation.clearWatch(id);
  }, [active]);

  return coords;
}
