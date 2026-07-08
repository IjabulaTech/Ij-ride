import type { ReactNode } from "react";

const TONES = {
  error: {
    box: "border-red-200 bg-red-50 text-red-800",
    button: "text-red-500 hover:bg-red-100",
  },
  success: {
    box: "border-emerald-200 bg-emerald-50 text-emerald-800",
    button: "text-emerald-500 hover:bg-emerald-100",
  },
  info: {
    box: "border-blue-200 bg-blue-50 text-blue-800",
    button: "text-blue-500 hover:bg-blue-100",
  },
} as const;

export function Alert({
  tone = "info",
  children,
  onDismiss,
}: {
  tone?: keyof typeof TONES;
  children: ReactNode;
  /** When provided, shows an X in the corner that calls this. */
  onDismiss?: () => void;
}) {
  const t = TONES[tone];
  return (
    <div
      role="alert"
      className={`relative rounded-lg border px-3 py-2.5 text-sm ${t.box} ${
        onDismiss ? "pr-9" : ""
      }`}
    >
      {children}
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          aria-label="Dismiss"
          className={`absolute right-1 top-1 rounded-md p-1 text-lg leading-none ${t.button}`}
        >
          ×
        </button>
      )}
    </div>
  );
}
