"use client";

import Link from "next/link";
import { useState } from "react";

import { Pagination, Table, Td } from "@/components/admin/Table";
import { Alert } from "@/components/ui/Alert";
import { Badge, paymentStatusTone } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";
import { listPayments } from "@/lib/api/admin";
import { formatDateTime, formatNaira, PAYMENT_METHOD_LABELS } from "@/lib/format";
import { usePaged } from "@/lib/hooks/usePaged";

export default function AdminPaymentsPage() {
  const [status, setStatus] = useState("");
  const [method, setMethod] = useState("");
  const [search, setSearch] = useState("");
  const [applied, setApplied] = useState({ status: "", method: "", search: "" });

  const { data, page, setPage, loading, error } = usePaged(
    (p) =>
      listPayments({
        page: p,
        status: applied.status,
        method: applied.method,
        search: applied.search,
      }),
    JSON.stringify(applied)
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-2">
        <h2 className="mr-auto text-lg font-bold text-gray-900">Payments</h2>
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm"
        >
          <option value="">All statuses</option>
          <option value="PENDING">Pending</option>
          <option value="CLAIMED">Claimed</option>
          <option value="PAID">Paid</option>
          <option value="FAILED">Failed</option>
        </select>
        <select
          value={method}
          onChange={(e) => setMethod(e.target.value)}
          className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm"
        >
          <option value="">All methods</option>
          <option value="CASH">Cash</option>
          <option value="TRANSFER">Transfer</option>
        </select>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search phone or reference…"
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
        />
        <button
          onClick={() => setApplied({ status, method, search })}
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
          <Table
            head={["Ride", "Passenger", "Driver", "Amount", "Method", "Status", "Reference", "Confirmed"]}
          >
            {data.results.map((payment) => (
              <tr key={payment.id}>
                <Td>
                  <Link
                    href={`/admin/rides/${payment.ride_id}`}
                    className="font-semibold text-emerald-600 hover:underline"
                  >
                    #{payment.ride_id}
                  </Link>
                </Td>
                <Td className="font-mono text-xs">{payment.passenger_phone}</Td>
                <Td className="font-mono text-xs">{payment.driver_phone ?? "—"}</Td>
                <Td className="font-semibold">{formatNaira(payment.amount)}</Td>
                <Td className="text-xs">{PAYMENT_METHOD_LABELS[payment.method]}</Td>
                <Td>
                  <Badge tone={paymentStatusTone(payment.status)}>{payment.status}</Badge>
                </Td>
                <Td className="font-mono text-xs">{payment.reference || "—"}</Td>
                <Td className="text-xs text-gray-500">
                  {payment.confirmed_at
                    ? `${formatDateTime(payment.confirmed_at)}${payment.confirmed_by_phone ? ` by ${payment.confirmed_by_phone}` : ""}`
                    : "—"}
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
