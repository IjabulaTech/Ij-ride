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

// Local YYYY-MM-DD (what <input type="date"> and the API expect), not UTC.
function isoDate(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(
    d.getDate()
  ).padStart(2, "0")}`;
}

// Quick "last N days" presets → a [from, to] pair (empty = no bound).
type Preset = "all" | "today" | "7" | "30" | "custom";
function presetRange(preset: Preset): { from: string; to: string } {
  if (preset === "all" || preset === "custom") return { from: "", to: "" };
  const today = new Date();
  const to = isoDate(today);
  if (preset === "today") return { from: to, to };
  const days = Number(preset); // 7 or 30
  const start = new Date();
  start.setDate(start.getDate() - (days - 1));
  return { from: isoDate(start), to };
}

export default function AdminRidesPage() {
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const [preset, setPreset] = useState<Preset>("all");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [applied, setApplied] = useState({ status: "", search: "", date_from: "", date_to: "" });

  const { data, page, setPage, loading, error } = usePaged(
    (p) =>
      listAdminRides({
        page: p,
        status: applied.status,
        search: applied.search,
        date_from: applied.date_from,
        date_to: applied.date_to,
      }),
    JSON.stringify(applied)
  );

  function choosePreset(next: Preset) {
    setPreset(next);
    if (next !== "custom") {
      const { from, to } = presetRange(next);
      setDateFrom(from);
      setDateTo(to);
    }
  }

  function applyFilters() {
    setApplied({ status, search, date_from: dateFrom, date_to: dateTo });
  }

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
        <select
          value={preset}
          onChange={(e) => choosePreset(e.target.value as Preset)}
          className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm"
          aria-label="Date range"
        >
          <option value="all">Any date</option>
          <option value="today">Today</option>
          <option value="7">Last 7 days</option>
          <option value="30">Last 30 days</option>
          <option value="custom">Custom range…</option>
        </select>
        <label className="flex items-center gap-1 text-xs text-gray-500">
          From
          <input
            type="date"
            value={dateFrom}
            max={dateTo || undefined}
            onChange={(e) => {
              setDateFrom(e.target.value);
              setPreset("custom");
            }}
            className="rounded-lg border border-gray-300 bg-white px-2 py-2 text-sm"
          />
        </label>
        <label className="flex items-center gap-1 text-xs text-gray-500">
          To
          <input
            type="date"
            value={dateTo}
            min={dateFrom || undefined}
            onChange={(e) => {
              setDateTo(e.target.value);
              setPreset("custom");
            }}
            className="rounded-lg border border-gray-300 bg-white px-2 py-2 text-sm"
          />
        </label>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search phone or address…"
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
        />
        <button
          onClick={applyFilters}
          className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white"
        >
          Filter
        </button>
      </div>

      {data && (
        <p className="text-sm text-gray-500">
          {data.count} ride{data.count === 1 ? "" : "s"}
          {applied.status && ` · ${applied.status}`}
          {applied.date_from && applied.date_to
            ? ` · ${applied.date_from} → ${applied.date_to}`
            : applied.date_from
              ? ` · from ${applied.date_from}`
              : applied.date_to
                ? ` · until ${applied.date_to}`
                : ""}
        </p>
      )}

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
