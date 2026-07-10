"use client";

import { useRouter } from "next/navigation";
import type { ReactNode } from "react";

import { SoundToggle } from "@/components/layout/SoundToggle";
import { Button } from "@/components/ui/Button";
import { BrandLogo } from "@/components/ui/BrandLogo";
import { useAuth } from "@/lib/auth/AuthContext";

export function AppShell({
  title,
  width = "narrow",
  children,
}: {
  title: string;
  /** narrow = phone-width column (passenger/driver); wide = admin tables */
  width?: "narrow" | "wide";
  children: ReactNode;
}) {
  const { user, logout } = useAuth();
  const router = useRouter();

  const handleLogout = () => {
    logout();
    router.replace("/login");
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="sticky top-0 z-10 border-b border-gray-200 bg-white">
        <div
          className={`mx-auto flex items-center justify-between px-4 py-3 ${
            width === "narrow" ? "max-w-md" : "max-w-6xl"
          }`}
        >
          <div className="flex items-center gap-2">
            <BrandLogo size={30} />
            <span className="text-lg font-bold text-gray-900">IJ Ride</span>
            <span className="text-sm text-gray-500">{title}</span>
          </div>
          <div className="flex items-center gap-2">
            {user && (
              <span className="hidden text-sm text-gray-600 sm:inline">
                {user.first_name || user.phone}
              </span>
            )}
            {/* Ride sound control — passengers & drivers get audible alerts */}
            {(user?.role === "PASSENGER" || user?.role === "DRIVER") && <SoundToggle />}
            <Button variant="ghost" onClick={handleLogout}>
              Log out
            </Button>
          </div>
        </div>
      </header>
      <main className={`mx-auto px-4 py-6 ${width === "narrow" ? "max-w-md" : "max-w-6xl"}`}>
        {children}
      </main>
    </div>
  );
}
