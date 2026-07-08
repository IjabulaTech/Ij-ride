/* eslint-disable @next/next/no-img-element */
const SIZES = { sm: "h-4 w-4", md: "h-6 w-6", lg: "h-10 w-10" } as const;

export function Spinner({ size = "md" }: { size?: keyof typeof SIZES }) {
  return (
    <span
      role="status"
      aria-label="Loading"
      className={`inline-block animate-spin rounded-full border-2 border-current border-t-transparent ${SIZES[size]}`}
    />
  );
}

/** Whole-page loader — the IJ Ride mark gently pulsing. Used across every
 * guarded route and data-loading screen, so the logo IS the page loader. */
export function FullPageSpinner() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-5 bg-gray-50">
      <img
        src="/brand/logo-mark.png"
        alt="Loading IJ Ride"
        width={96}
        height={96}
        className="h-24 w-24 animate-pulse object-contain"
      />
      <Spinner size="sm" />
    </div>
  );
}
