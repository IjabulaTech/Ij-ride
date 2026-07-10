"use client";

import { useEffect, useState } from "react";

import { isSoundMuted, playBeep, setSoundMuted } from "@/lib/sound";

/** Bell toggle to mute/unmute ride notification beeps. Clicking it also
 * counts as the user gesture that unlocks audio playback (autoplay policy),
 * and plays a confirming beep when turning sound on. */
export function SoundToggle() {
  const [muted, setMuted] = useState(false);

  // localStorage is client-only — read after mount to avoid hydration mismatch
  useEffect(() => {
    setMuted(isSoundMuted());
  }, []);

  function toggle() {
    const next = !muted;
    setMuted(next);
    setSoundMuted(next);
    if (!next) playBeep("normal"); // confirm sound is on
  }

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={muted ? "Turn ride sounds on" : "Turn ride sounds off"}
      aria-pressed={!muted}
      title={muted ? "Ride sounds off" : "Ride sounds on"}
      className="rounded-lg p-1.5 text-lg leading-none text-gray-600 hover:bg-gray-100"
    >
      <span aria-hidden>{muted ? "🔕" : "🔔"}</span>
    </button>
  );
}
