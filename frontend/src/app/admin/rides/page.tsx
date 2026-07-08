"use client";

import Link from "next/link";
import { useState } from "react";

import { Pagination, Table, Td } from "@/components/admin/Table";
import { RideStatusBadge } from "@/components/ride/RideStatusBadge";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { listAdminRides } from "@/lib/api/admin";
import { formatDateTime, formatNaira } from "@/lib/format";
import { usePaged } from "@/lib/hooks/usePaged";
import type { RideStatus } from "@/types/api";

const STATUSES: RideStatus[] = [
  "SEARCHING",
  "ACCEPTED",
  "DRIVER_ARRIVED",
  "IN_PROGRESS",
  "COMPLETED",
  "CANCELLED",
  "EXPIRED",
];

export default function AdminRidesPage() {
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const [applied, setApplied] = useState({ status: "", search: "" });

  const { data, page, setPage, loading, error } = usePaged(
    (p) => listAdminRides({ page: p, status: applied.status, search: applied.search }),
    JSON.stringify(applied)
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-2">
        <h2 className="mr-auto text-lg font-bold text-gray-900">Rides</h2>
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm"
        >
          <option value="">All statuses</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search phone or address…"
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
        />
        <button
          onClick={() => setApplied({ status, search })}
          className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white"
        >
          Filter
        </button>
      </div>

      {error && <Alert tone="error">{error}</Alert>}
      {loading || !data ? (
        <div className="flex justify-center py-16 text-emerald-600">
          <Spinner size="lg" />
        </div>
      ) : (
        <>
          <Table head={["#", "Route", "Passenger", "Driver", "Fare", "Status", "Requested", ""]}>
            {data.results.map((ride) => (
              <tr key={ride.id}>
                <Td className="text-xs text-gray-500">{ride.id}</Td>
                <Td className="max-w-56">
                  <p className="truncate text-xs">
                    {ride.pickup_address} → {ride.dropoff_address}
                  </p>
                </Td>
                <Td className="font-mono text-xs">{ride.passenger.phone}</Td>
                <Td className="font-mono text-xs">{ride.driver?.phone ?? "—"}</Td>
                <Td className="font-semibold">
                  {formatNaira(ride.final_fare ?? ride.estimated_fare)}
                </Td>
                <Td>
                  <RideStatusBadge status={ride.status} />
                </Td>
                <Td className="text-xs text-gray-500">{formatDateTime(ride.created_at)}</Td>
                <Td>
                  <Link
                    href={`/admin/rides/${ride.id}`}
                    className="text-sm font-semibold text-emerald-600 hover:underline"
                  >
                    View
                  </Link>
                </Td>
              </tr>
            ))}
          </Table>
          <Pagination page={page} count={data.count} onPage={setPage} />
        </>
      )}
    </div>
  );
}
