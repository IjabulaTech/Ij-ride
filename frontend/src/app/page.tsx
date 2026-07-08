"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { BrandLogo } from "@/components/ui/BrandLogo";
import { Spinner } from "@/components/ui/Spinner";
import { useAuth } from "@/lib/auth/AuthContext";
import { homeFor } from "@/lib/auth/routes";

/** Landing: brand splash while we decide where to send everyone. */
export default function Home() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    router.replace(user ? homeFor(user.role) : "/login");
  }, [user, loading, router]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-gray-50">
      <BrandLogo size={88} className="shadow-sm" />
      <p className="text-lg font-extrabold text-gray-900">IJ Ride</p>
      <Spinner size="md" />
    </div>
  );
}
