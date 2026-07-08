"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export interface NavItem {
  href: string;
  label: string;
  icon: string;
  /** Also highlight when the path starts with any of these. */
  match?: string[];
}

export function BottomNav({ items }: { items: NavItem[] }) {
  const pathname = usePathname();

  const isActive = (item: NavItem) =>
    pathname === item.href || (item.match ?? []).some((prefix) => pathname.startsWith(prefix));

  return (
    <nav className="fixed inset-x-0 bottom-0 z-10 border-t border-gray-200 bg-white">
      <div className="mx-auto flex max-w-md">
        {items.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`flex flex-1 flex-col items-center gap-0.5 py-2.5 text-xs font-medium ${
              isActive(item) ? "text-emerald-600" : "text-gray-500 hover:text-gray-700"
            }`}
          >
            <span className="text-lg leading-none" aria-hidden>
              {item.icon}
            </span>
            {item.label}
          </Link>
        ))}
      </div>
    </nav>
  );
}
