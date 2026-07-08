import { BrandLogo } from "@/components/ui/BrandLogo";

export const metadata = { title: "Offline" };

/** Precached by the service worker and shown when a navigation fails. */
export default function OfflinePage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-gray-50 px-6 text-center">
      <BrandLogo size={64} className="mb-1 shadow-sm" />
      <h1 className="text-xl font-bold text-gray-900">You&apos;re offline</h1>
      <p className="max-w-sm text-sm text-gray-600">
        IJ Ride needs an internet connection to request rides and see live trip updates. Check
        your connection and try again.
      </p>
      <a
        href="/"
        className="mt-2 rounded-lg bg-emerald-600 px-5 py-2.5 text-sm font-semibold text-white"
      >
        Try again
      </a>
    </div>
  );
}
