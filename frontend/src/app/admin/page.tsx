"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { Alert } from "@/components/ui/Alert";
import { Card } from "@/components/ui/Card";
import { FullPageSpinner } from "@/components/ui/Spinner";
import * as adminApi from "@/lib/api/admin";
import { formatNaira, VEHICLE_CATEGORY_LABELS } from "@/lib/format";
import { playBeep } from "@/lib/sound";
import type { FareSetting } from "@/types/api";

// How often the admin dashboard re-fetches its counts.
const ADMIN_POLL_MS = 15_000;

interface Stats {
  users: number;
  pendingDrivers: number;
  rides: number;
  pendingPayments: number;
  activeFares: FareSetting[];
}

function StatCard({ label, value, href }: { label: string; value: number; href: string }) {
  return (
    <Link href={href}>
      <Card className="transition-colors hover:border-emerald-300">
        <p className="text-3xl font-extrabold text-gray-900">{value}</p>
        <p className="mt-1 text-sm text-gray-500">{label}</p>
      </Card>
    </Link>
  );
}

export default function AdminDashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [error, setError] = useState("");
  // Remember the last pending-driver count so we can beep only when it grows
  // (a NEW driver has registered and is waiting for approval).
  const prevPendingRef = useRef<number | null>(null);

  const load = useCallback(async () => {
    try {
      const [users, pending, rides, payments, fares] = await Promise.all([
        adminApi.listUsers({}),
        adminApi.listDrivers({ approval_status: "PENDING" }),
        adminApi.listAdminRides({}),
        adminApi.listPayments({ status: "PENDING" }),
        adminApi.listFareSettings(),
      ]);
      // Alert on a newly-registered driver awaiting approval.
      if (prevPendingRef.current !== null && pending.count > prevPendingRef.current) {
        playBeep("alert");
      }
      prevPendingRef.current = pending.count;
      setStats({
        users: users.count,
        pendingDrivers: pending.count,
        rides: rides.count,
        pendingPayments: payments.count,
        activeFares: fares.results.filter((f) => f.is_active),
      });
      setError("");
    } catch {
      setError("Could not load dashboard data.");
    }
  }, []);

  useEffect(() => {
    load();
    const timer = setInterval(load, ADMIN_POLL_MS);
    return () => clearInterval(timer);
  }, [load]);

  if (error) return <Alert tone="error">{error}</Alert>;
  if (!stats) return <FullPageSpinner />;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Users" value={stats.users} href="/admin/users" />
        <StatCard
          label="Drivers awaiting approval"
          value={stats.pendingDrivers}
          href="/admin/drivers?status=PENDING"
        />
        <StatCard label="Total rides" value={stats.rides} href="/admin/rides" />
        <StatCard
          label="Unsettled payments"
          value={stats.pendingPayments}
          href="/admin/payments"
        />
      </div>

      <Card>
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-gray-900">Active fares</h3>
          <Link href="/admin/settings" className="text-sm font-semibold text-emerald-600">
            Manage →
          </Link>
        </div>
        {stats.activeFares.length ? (
          <ul className="mt-2 space-y-1 text-sm text-gray-600">
            {stats.activeFares.map((fare) => (
              <li key={fare.id}>
                <span className="font-semibold text-gray-800">
                  {VEHICLE_CATEGORY_LABELS[fare.vehicle_category]}:
                </span>{" "}
                base {formatNaira(fare.base_fare)} + {formatNaira(fare.per_km)}/km +{" "}
                {formatNaira(fare.per_minute)}/min · minimum {formatNaira(fare.minimum_fare)}
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-2 text-sm text-red-600">
            No active fare settings — ride requests will fail until they are created.
          </p>
        )}
      </Card>
    </div>
  );
}
