"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/admin", label: "Dashboard", exact: true },
  { href: "/admin/users", label: "Users" },
  { href: "/admin/drivers", label: "Drivers" },
  { href: "/admin/rides", label: "Rides" },
  { href: "/admin/payments", label: "Payments" },
  { href: "/admin/commissions", label: "Commissions" },
  { href: "/admin/support", label: "Support" },
  { href: "/admin/settings", label: "Fare settings" },
];

export function AdminNav() {
  const pathname = usePathname();
  return (
    <nav className="mb-6 flex gap-1 overflow-x-auto border-b border-gray-200">
      {LINKS.map(({ href, label, exact }) => {
        const active = exact ? pathname === href : pathname.startsWith(href);
        return (
          <Link
            key={href}
            href={href}
            className={`whitespace-nowrap border-b-2 px-3 py-2 text-sm font-medium ${
              active
                ? "border-emerald-600 text-emerald-700"
                : "border-transparent text-gray-500 hover:text-gray-800"
            }`}
          >
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
