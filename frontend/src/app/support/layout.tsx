import { RequireAuth } from "@/components/auth/RequireAuth";
import { AppShell } from "@/components/layout/AppShell";

export const metadata = { title: "Support" };

export default function SupportLayout({ children }: { children: React.ReactNode }) {
  return (
    <RequireAuth>
      <AppShell title="Support">{children}</AppShell>
    </RequireAuth>
  );
}
