"use client";

import { useEffect } from "react";

/** Registers the service worker. Enabled in production builds; opt in during
 * development with NEXT_PUBLIC_ENABLE_PWA=true (a dev service worker caches
 * aggressively and confuses hot reload, so it stays off by default). */
export function PwaRegister() {
  useEffect(() => {
    const enabled =
      process.env.NODE_ENV === "production" || process.env.NEXT_PUBLIC_ENABLE_PWA === "true";
    if (!enabled || typeof window === "undefined" || !("serviceWorker" in navigator)) return;
    navigator.serviceWorker.register("/sw.js").catch(() => {
      /* registration failure just means no offline support */
    });
  }, []);

  return null;
}
