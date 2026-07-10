/**
 * Tiny notification-sound utility for IJ Ride.
 *
 * Uses the Web Audio API to synthesize short beeps — no audio files to load,
 * cache, or trip the PWA service worker / CSP. Two tones:
 *   - "alert"  : two bright beeps — driver's new ride request (attention-grabbing)
 *   - "normal" : one soft beep    — passenger/driver status & payment updates
 *
 * BROWSER AUTOPLAY REALITY: browsers (esp. iOS Safari) block audio until the
 * user has interacted with the page. We create/resume the AudioContext on the
 * FIRST user gesture anywhere (a one-time pointer/key listener). Since drivers
 * tap "Go online" and passengers tap through booking before any beep is due,
 * audio is unlocked by the time an event fires. If a user somehow never
 * interacts, beeps are silently skipped (no errors) — that is the expected,
 * documented limitation.
 *
 * A mute preference is persisted in localStorage so users can silence alerts.
 */

let ctx: AudioContext | null = null;
const MUTE_KEY = "ijride.sound.muted";

function getCtx(): AudioContext | null {
  if (typeof window === "undefined") return null;
  if (!ctx) {
    const AC: typeof AudioContext | undefined =
      window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!AC) return null;
    try {
      ctx = new AC();
    } catch {
      return null;
    }
  }
  return ctx;
}

export function isSoundMuted(): boolean {
  if (typeof window === "undefined") return false;
  return window.localStorage.getItem(MUTE_KEY) === "1";
}

export function setSoundMuted(muted: boolean): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(MUTE_KEY, muted ? "1" : "0");
  if (!muted) unlockAudio(); // toggling on counts as a gesture — unlock now
}

/** Resume/create the audio context on a user gesture (autoplay policy). */
export function unlockAudio(): void {
  const c = getCtx();
  if (c && c.state === "suspended") c.resume().catch(() => undefined);
}

// Unlock on the very first interaction anywhere in the app.
if (typeof window !== "undefined") {
  const once = () => {
    unlockAudio();
    window.removeEventListener("pointerdown", once);
    window.removeEventListener("keydown", once);
  };
  window.addEventListener("pointerdown", once, { once: true });
  window.addEventListener("keydown", once, { once: true });
}

function tone(c: AudioContext, freq: number, startOffset: number, duration: number, peak = 0.18) {
  const osc = c.createOscillator();
  const gain = c.createGain();
  osc.type = "sine";
  osc.frequency.value = freq;
  osc.connect(gain);
  gain.connect(c.destination);
  const t = c.currentTime + startOffset;
  // envelope avoids clicks
  gain.gain.setValueAtTime(0.0001, t);
  gain.gain.exponentialRampToValueAtTime(peak, t + 0.015);
  gain.gain.exponentialRampToValueAtTime(0.0001, t + duration);
  osc.start(t);
  osc.stop(t + duration + 0.02);
}

export type BeepKind = "normal" | "alert";

export function playBeep(kind: BeepKind = "normal"): void {
  if (isSoundMuted()) return;
  const c = getCtx();
  if (!c) return;
  if (c.state === "suspended") c.resume().catch(() => undefined);
  if (c.state !== "running") return; // not unlocked yet — skip silently
  if (kind === "alert") {
    tone(c, 880, 0, 0.18);
    tone(c, 1174, 0.22, 0.22); // second, higher beep
  } else {
    tone(c, 660, 0, 0.2);
  }
}
