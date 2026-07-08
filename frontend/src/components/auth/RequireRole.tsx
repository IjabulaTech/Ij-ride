"use client";

import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { FullPageSpinner } from "@/components/ui/Spinner";
import { useAuth } from "@/lib/auth/AuthContext";
import { homeFor } from "@/lib/auth/routes";
import type { Role } from "@/types/api";

/** Client-side route guard. The API enforces every permission server-side;
 * this only keeps users out of screens they can't use. */
export function RequireRole({ role, children }: { role: Role; children: ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    if (!user) router.replace("/login");
    else if (user.role !== role) router.replace(homeFor(user.role));
  }, [user, loading, role, router]);

  if (loading || !user || user.role !== role) return <FullPageSpinner />;
  return <>{children}</>;
}
