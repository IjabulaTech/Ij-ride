import { RequireRole } from "@/components/auth/RequireRole";
import { AppShell } from "@/components/layout/AppShell";
import { BottomNav } from "@/components/layout/BottomNav";

export const metadata = { title: "Passenger" };

const NAV_ITEMS = [
  { href: "/passenger", label: "Book", icon: "🚕", match: ["/passenger/ride"] },
  { href: "/passenger/history", label: "History", icon: "🕘", match: ["/passenger/history"] },
  { href: "/passenger/profile", label: "Profile", icon: "👤" },
];

export default function PassengerLayout({ children }: { children: React.ReactNode }) {
  return (
    <RequireRole role="PASSENGER">
      <AppShell title="Passenger">
        <div className="pb-20">{children}</div>
      </AppShell>
      <BottomNav items={NAV_ITEMS} />
    </RequireRole>
  );
}
