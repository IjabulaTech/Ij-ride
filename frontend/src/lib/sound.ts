/**
 * Notification-sound utility for IJ Ride.
 *
 * Primary sound is the uploaded MP3 at /sounds/notification.mp3 (one shared,
 * preloaded <audio> element). If it can't play for any reason, we fall back to
 * a synthesized Web Audio beep so a notification is never silently dropped.
 *   - "alert"  : driver's new ride request (attention-grabbing)
 *   - "normal" : passenger/driver status, payments, admin approvals
 *
 * BROWSER AUTOPLAY REALITY: browsers (esp. iOS Safari) block audio until the
 * user has interacted with the page. We resume the AudioContext AND "prime"
 * the <audio> element (a muted play/pause) on the FIRST user gesture anywhere.
 * Since drivers tap "Go online" and passengers tap through booking before any
 * beep is due, audio is unlocked by the time an event fires. If a user somehow
 * never interacts, beeps are skipped silently (no errors).
 *
 * A mute preference is persisted in localStorage so users can silence alerts.
 */

let ctx: AudioContext | null = null;
const MUTE_KEY = "ijride.sound.muted";
const SOUND_URL = "/sounds/notification.mp3";

let audioEl: HTMLAudioElement | null = null;
let audioPrimed = false;

function getAudio(): HTMLAudioElement | null {
  if (typeof window === "undefined") return null;
  if (!audioEl) {
    audioEl = new Audio(SOUND_URL);
    audioEl.preload = "auto";
  }
  return audioEl;
}

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

/** Resume the audio context AND prime the <audio> element on a user gesture
 * (autoplay policy). Priming = a muted play/pause, which iOS Safari requires
 * before a later programmatic play() (e.g. on a WebSocket event) will work. */
export function unlockAudio(): void {
  const c = getCtx();
  if (c && c.state === "suspended") c.resume().catch(() => undefined);

  const a = getAudio();
  if (a && !audioPrimed) {
    audioPrimed = true;
    a.muted = true;
    a.play()
      .then(() => {
        a.pause();
        a.currentTime = 0;
        a.muted = false;
      })
      .catch(() => {
        a.muted = false; // will retry priming on the next gesture
        audioPrimed = false;
      });
  }
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

/** Synthesized fallback beep — used only if the MP3 can't play. */
function playSynth(kind: BeepKind): void {
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

export function playBeep(kind: BeepKind = "normal"): void {
  if (isSoundMuted()) return;
  const a = getAudio();
  if (a) {
    try {
      a.currentTime = 0;
      const played = a.play();
      // A new ride request is important — give it a second ring shortly after.
      if (kind === "alert") {
        window.setTimeout(() => {
          const el = getAudio();
          if (el && !isSoundMuted()) {
            el.currentTime = 0;
            el.play().catch(() => undefined);
          }
        }, 700);
      }
      if (played) {
        played.catch(() => playSynth(kind)); // blocked/failed → synth fallback
      }
      return;
    } catch {
      /* fall through to synth */
    }
  }
  playSynth(kind);
}
