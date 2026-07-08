import { RequireRole } from "@/components/auth/RequireRole";
import { AppShell } from "@/components/layout/AppShell";
import { BottomNav } from "@/components/layout/BottomNav";

export const metadata = { title: "Driver" };

const NAV_ITEMS = [
  { href: "/driver", label: "Drive", icon: "🚗", match: ["/driver/trip"] },
  { href: "/driver/history", label: "History", icon: "🕘", match: ["/driver/history"] },
  { href: "/driver/earnings", label: "Earnings", icon: "💰" },
  { href: "/driver/onboarding", label: "Profile", icon: "👤" },
];

export default function DriverLayout({ children }: { children: React.ReactNode }) {
  return (
    <RequireRole role="DRIVER">
      <AppShell title="Driver">
        <div className="pb-20">{children}</div>
      </AppShell>
      <BottomNav items={NAV_ITEMS} />
    </RequireRole>
  );
}
