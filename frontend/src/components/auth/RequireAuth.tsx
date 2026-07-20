"use client";

import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { FullPageSpinner } from "@/components/ui/Spinner";
import { useAuth } from "@/lib/auth/AuthContext";

/** Route guard for screens any signed-in user may open (e.g. Support).
 * The API still enforces permissions server-side. */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [user, loading, router]);

  if (loading || !user) return <FullPageSpinner />;
  return <>{children}</>;
}
