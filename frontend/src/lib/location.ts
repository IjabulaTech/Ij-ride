/** Structured location state used by the passenger booking form. Keeping
 * this shape uniform for both pickup and dropoff avoids the "typed string
 * vs stored coords" ambiguity we had before. */
export type LocationSource = "gps" | "suggestion" | "typed";

export interface LocationField {
  /** What the user sees in the input. Always present. */
  label: string;
  /** Fuller address returned by the provider, when available. */
  address?: string;
  /** Same string Mapbox returns as `place_name` — kept for API symmetry. */
  place_name?: string;
  /** Provider category hints (e.g. ["poi"] or ["hospital"]). */
  place_type?: string[];
  /** Coordinates take precedence in fare math whenever present. */
  lat?: string;
  lng?: string;
  /** Where the value came from — drives the UI indicator + priority rules. */
  source: LocationSource | null;
}

export const EMPTY_LOCATION: LocationField = { label: "", source: null };

export function hasCoords(field: LocationField): field is LocationField & {
  lat: string;
  lng: string;
} {
  return typeof field.lat === "string" && typeof field.lng === "string";
}

/** Shape used when calling the estimate/create endpoints — coordinates
 * always win when present; label falls back to what the user sees. */
export function toApiLocation(field: LocationField) {
  const address = field.address ?? field.label;
  return hasCoords(field)
    ? { address, lat: field.lat, lng: field.lng }
    : { address };
}

/** Yola city centre — matches GEO_PROXIMITY in the backend .env. */
export const YOLA_CENTER = { lat: 9.2035, lng: 12.4954 };

/** Haversine distance in kilometres. */
export function distanceKm(
  a: { lat: number; lng: number },
  b: { lat: number; lng: number }
): number {
  const R = 6371;
  const rad = Math.PI / 180;
  const dLat = (b.lat - a.lat) * rad;
  const dLng = (b.lng - a.lng) * rad;
  const lat1 = a.lat * rad;
  const lat2 = b.lat * rad;
  const h =
    Math.sin(dLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}

/** How far a coordinate pair is from Yola centre (km). */
export function distanceFromYolaKm(lat: number, lng: number): number {
  return distanceKm(YOLA_CENTER, { lat, lng });
}

/** Anything further than this we treat as "not really in the service area";
 * usually a sign the browser fell back to IP-based geolocation. */
export const YOLA_SERVICE_RADIUS_KM = 150;
