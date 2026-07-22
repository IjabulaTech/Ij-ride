import { api } from "./client";

export interface GeoSuggestion {
  label: string;
  address: string;
  place_name: string;
  place_type: string;
  lat: string;
  lng: string;
}

/** Optional live-GPS bias: when the rider has already granted geolocation
 * we forward those coords so Mapbox ranks results near where they are. */
export function suggest(
  q: string,
  limit = 5,
  proximity?: { lat: string; lng: string } | null
): Promise<{ results: GeoSuggestion[] }> {
  const params = new URLSearchParams({ q, limit: String(limit) });
  if (proximity) {
    params.set("lat", proximity.lat);
    params.set("lng", proximity.lng);
  }
  return api<{ results: GeoSuggestion[] }>(`/geo/suggest/?${params.toString()}`);
}

export function reverseGeocode(
  lat: string,
  lng: string
): Promise<{ address: string; lat: string; lng: string }> {
  const params = new URLSearchParams({ lat, lng });
  return api(`/geo/reverse/?${params.toString()}`);
}

export interface RouteGeometry {
  /** [lat, lng] pairs ready to hand to Leaflet. */
  points: [number, number][];
  distance_m: number;
  duration_s: number;
  /** "route" = real roads; "straight" = provider unavailable, direct line. */
  source: string;
}

/** Road path between two points, for drawing the live-tracking route. */
export function routeGeometry(
  fromLat: number,
  fromLng: number,
  toLat: number,
  toLng: number
): Promise<RouteGeometry> {
  const params = new URLSearchParams({
    from_lat: String(fromLat),
    from_lng: String(fromLng),
    to_lat: String(toLat),
    to_lng: String(toLng),
  });
  return api<RouteGeometry>(`/geo/route/?${params.toString()}`);
}
