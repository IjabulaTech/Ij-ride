"use client";

import Link from "next/link";
import { useState } from "react";

import { Pagination, Table, Td } from "@/components/admin/Table";
import { Alert } from "@/components/ui/Alert";
import { approvalStatusTone, Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";
import { listDrivers } from "@/lib/api/admin";
import { formatDateTime } from "@/lib/format";
import { usePaged } from "@/lib/hooks/usePaged";

export default function AdminDriversPage() {
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const [applied, setApplied] = useState({ status: "", search: "" });

  const { data, page, setPage, loading, error } = usePaged(
    (p) => listDrivers({ page: p, approval_status: applied.status, search: applied.search }),
    JSON.stringify(applied)
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-2">
        <h2 className="mr-auto text-lg font-bold text-gray-900">Drivers</h2>
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm"
        >
          <option value="">All statuses</option>
          <option value="PENDING">Pending</option>
          <option value="APPROVED">Approved</option>
          <option value="REJECTED">Rejected</option>
        </select>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search phone, name, license, plate…"
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
          <Table head={["Driver", "License", "Vehicle", "Status", "Online", "Registered", ""]}>
            {data.results.map((driver) => (
              <tr key={driver.id}>
                <Td>
                  <p className="font-medium text-gray-900">
                    {[driver.user.first_name, driver.user.last_name].filter(Boolean).join(" ") ||
                      "—"}
                  </p>
                  <p className="font-mono text-xs text-gray-500">{driver.user.phone}</p>
                </Td>
                <Td className="font-mono text-xs">{driver.license_number || "—"}</Td>
                <Td className="text-xs">
                  {driver.active_vehicle
                    ? `${driver.active_vehicle.make} ${driver.active_vehicle.model} · ${driver.active_vehicle.plate_number}`
                    : "—"}
                </Td>
                <Td>
                  <Badge tone={approvalStatusTone(driver.approval_status)}>
                    {driver.approval_status}
                  </Badge>
                </Td>
                <Td>
                  <Badge tone={driver.availability?.is_online ? "green" : "gray"}>
                    {driver.availability?.is_online ? "Online" : "Offline"}
                  </Badge>
                </Td>
                <Td className="text-xs text-gray-500">{formatDateTime(driver.created_at)}</Td>
                <Td>
                  <Link
                    href={`/admin/drivers/${driver.id}`}
                    className="text-sm font-semibold text-emerald-600 hover:underline"
                  >
                    Review
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
