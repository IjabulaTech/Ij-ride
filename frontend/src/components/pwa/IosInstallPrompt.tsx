"use client";

import { useEffect, useState } from "react";

/**
 * iOS Safari has no "Add to Home Screen" API (unlike Android's install prompt),
 * so users must do it manually via the Share sheet. This dismissible banner
 * tells them how — shown only on an iPhone/iPad browser that isn't already
 * running as an installed app. Dismissal is remembered in localStorage.
 */
const DISMISS_KEY = "ijride.ios-install.dismissed";

function isIos(): boolean {
  if (typeof navigator === "undefined") return false;
  const ua = navigator.userAgent;
  const iOSDevice = /iphone|ipad|ipod/i.test(ua);
  // iPadOS 13+ reports as "Macintosh" but is touch-capable
  const iPadOs = /Macintosh/i.test(ua) && navigator.maxTouchPoints > 1;
  return iOSDevice || iPadOs;
}

function isStandalone(): boolean {
  if (typeof window === "undefined") return false;
  return (
    window.matchMedia("(display-mode: standalone)").matches ||
    // iOS Safari exposes this non-standard flag when launched from the home screen
    (window.navigator as unknown as { standalone?: boolean }).standalone === true
  );
}

export function IosInstallPrompt() {
  const [show, setShow] = useState(false);

  useEffect(() => {
    if (!isIos() || isStandalone()) return;
    if (window.localStorage.getItem(DISMISS_KEY) === "1") return;
    setShow(true);
  }, []);

  if (!show) return null;

  function dismiss() {
    window.localStorage.setItem(DISMISS_KEY, "1");
    setShow(false);
  }

  return (
    <div className="fixed inset-x-0 bottom-0 z-50 px-3 pb-[calc(env(safe-area-inset-bottom)+0.75rem)]">
      <div className="mx-auto flex max-w-md items-start gap-3 rounded-xl border border-gray-200 bg-white p-3 shadow-lg">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/icons/apple-touch-icon.png"
          alt="IJ Ride"
          className="h-10 w-10 shrink-0 rounded-lg"
        />
        <div className="min-w-0 flex-1 text-sm text-gray-700">
          <p className="font-semibold text-gray-900">Install IJ Ride</p>
          <p className="mt-0.5">
            Tap the Share icon{" "}
            <span aria-hidden className="mx-0.5 inline-block align-middle">
              {/* iOS share glyph */}
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" className="inline">
                <path
                  d="M12 3v12M12 3l-4 4M12 3l4 4"
                  stroke="#059669"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                <path
                  d="M5 12v7a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-7"
                  stroke="#059669"
                  strokeWidth="2"
                  strokeLinecap="round"
                />
              </svg>
            </span>
            then <span className="font-semibold">“Add to Home Screen”</span>.
          </p>
        </div>
        <button
          type="button"
          onClick={dismiss}
          aria-label="Dismiss install banner"
          className="shrink-0 rounded-lg p-1 text-gray-400 hover:bg-gray-100"
        >
          <span aria-hidden className="text-lg leading-none">
            ×
          </span>
        </button>
      </div>
    </div>
  );
}
