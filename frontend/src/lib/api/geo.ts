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
