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
    // NOTE: do NOT add `loading=async` to the URL. That switches the API into
    // bootstrap mode where google.maps.Map only exists after an
    // importLibrary() call, so the classic globals this code uses (maps.Map,
    // maps.Marker, maps.geometry) are undefined on load — which surfaces as
    // "Map is not a constructor". Without it the namespace is fully populated.
    const ready = () => typeof window.google?.maps?.Map === "function";
    const onReady = () => {
      if (ready()) {
        resolve(window.google.maps);
      } else {
        loaderPromise = null;
        reject(new Error("Google Maps loaded but the map library is unavailable."));
      }
    };
    const fail = () => {
      loaderPromise = null; // allow a retry after a network blip
      reject(new Error("Google Maps failed to load."));
    };

    const existing = document.getElementById(SCRIPT_ID) as HTMLScriptElement | null;
    if (existing) {
      if (ready()) return onReady();
      existing.addEventListener("load", onReady);
      existing.addEventListener("error", fail);
      return;
    }
    const script = document.createElement("script");
    script.id = SCRIPT_ID;
    // `geometry` gives us spherical helpers for smooth heading/interpolation.
    script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(
      KEY
    )}&libraries=geometry&v=weekly`;
    script.async = true;
    script.defer = true;
    script.onload = onReady;
    script.onerror = fail;
    document.head.appendChild(script);
  });
  return loaderPromise;
}
