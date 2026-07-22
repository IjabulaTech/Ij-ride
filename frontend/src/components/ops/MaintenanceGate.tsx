"use client";

import { useEffect, useState } from "react";

import { BrandLogo } from "@/components/ui/BrandLogo";
import { maintenanceStatus } from "@/lib/api/ops";
import { useAuth } from "@/lib/auth/AuthContext";
import {
  SUPPORT_PHONE_LOCAL,
  SUPPORT_TEL_HREF,
  SUPPORT_WHATSAPP_HREF,
} from "@/lib/support";

const POLL_MS = 30_000;

/** Shows a full-screen maintenance notice to passengers and drivers while
 * maintenance mode is on. Admins pass straight through so they can keep
 * working (and switch it back off). Re-checks periodically, so the app comes
 * back on its own without anyone refreshing. */
export function MaintenanceGate({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const [state, setState] = useState<{ on: boolean; message: string }>({
    on: false,
    message: "",
  });

  useEffect(() => {
    let cancelled = false;
    const check = async () => {
      try {
        const data = await maintenanceStatus();
        if (!cancelled) setState({ on: data.maintenance, message: data.message });
      } catch {
        /* status unreachable — fail open rather than locking everyone out */
      }
    };
    check();
    const timer = setInterval(check, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, []);

  // Admins keep full access — they're the ones doing the maintenance.
  if (!state.on || user?.role === "ADMIN") return <>{children}</>;

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-5 bg-gray-50 px-6 text-center">
      <BrandLogo size={72} className="shadow-sm" />
      <div className="space-y-2">
        <h1 className="text-2xl font-extrabold text-gray-900">Back shortly</h1>
        <p className="mx-auto max-w-sm text-sm text-gray-600">{state.message}</p>
      </div>
      <div className="flex flex-col items-center gap-2">
        <p className="text-xs text-gray-500">Need help right now?</p>
        <div className="flex gap-2">
          <a
            href={SUPPORT_TEL_HREF}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
          >
            Call {SUPPORT_PHONE_LOCAL}
          </a>
          <a
            href={SUPPORT_WHATSAPP_HREF}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700"
          >
            WhatsApp
          </a>
        </div>
      </div>
      <p className="text-xs text-gray-400">This page updates automatically.</p>
    </div>
  );
}
