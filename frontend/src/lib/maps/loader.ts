/** Loads the Google Maps JavaScript API once, on demand.
 *
 * The browser key (NEXT_PUBLIC_GOOGLE_MAPS_KEY) is separate from the
 * server-side Places key and is protected by an HTTP-referrer restriction —
 * it is public by design.
 */
const KEY = process.env.NEXT_PUBLIC_GOOGLE_MAPS_KEY ?? "";
const SCRIPT_ID = "ijride-google-maps";

let loaderPromise: Promise<typeof google.maps> | null = null;

export function mapsKeyConfigured(): boolean {
  return KEY.length > 0;
}

export function loadGoogleMaps(): Promise<typeof google.maps> {
  if (typeof window === "undefined") {
    return Promise.reject(new Error("Google Maps can only load in the browser."));
  }
  if (!KEY) {
    return Promise.reject(new Error("NEXT_PUBLIC_GOOGLE_MAPS_KEY is not set."));
  }
  if (window.google?.maps) return Promise.resolve(window.google.maps);
  if (loaderPromise) return loaderPromise;

  loaderPromise = new Promise((resolve, reject) => {
    const existing = document.getElementById(SCRIPT_ID) as HTMLScriptElement | null;
    const onReady = () => {
      if (window.google?.maps) resolve(window.google.maps);
      else reject(new Error("Google Maps loaded but is unavailable."));
    };
    if (existing) {
      existing.addEventListener("load", onReady);
      existing.addEventListener("error", () => reject(new Error("Google Maps failed to load.")));
      return;
    }
    const script = document.createElement("script");
    script.id = SCRIPT_ID;
    // `geometry` gives us spherical helpers for smooth heading/interpolation.
    script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(
      KEY
    )}&libraries=geometry&loading=async&v=weekly`;
    script.async = true;
    script.defer = true;
    script.onload = onReady;
    script.onerror = () => {
      loaderPromise = null; // allow a retry after a network blip
      reject(new Error("Google Maps failed to load."));
    };
    document.head.appendChild(script);
  });
  return loaderPromise;
}
