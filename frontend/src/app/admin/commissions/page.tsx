"use client";

import { useCallback, useEffect, useState } from "react";

import { Pagination, Table, Td } from "@/components/admin/Table";
import { Alert } from "@/components/ui/Alert";
import { Badge, type BadgeTone } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { ApiError } from "@/lib/api/client";
import {
  commissionSummary,
  listCommissions,
  remitCommission,
  settleDriver,
} from "@/lib/api/admin";
import { formatDateTime, formatNaira } from "@/lib/format";
import { usePaged } from "@/lib/hooks/usePaged";
import type { CommissionSummary, RemittanceStatus } from "@/types/api";

const STATUS_TONES: Record<RemittanceStatus, BadgeTone> = {
  PENDING: "yellow",
  REMITTED: "green",
  WAIVED: "gray",
};

export default function AdminCommissionsPage() {
  const [summary, setSummary] = useState<CommissionSummary | null>(null);
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const [applied, setApplied] = useState({ status: "", search: "" });
  const [busyId, setBusyId] = useState<number | string | null>(null);
  const [error, setError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);

  const { data, page, setPage, loading } = usePaged(
    (p) => listCommissions({ page: p, status: applied.status, search: applied.search }),
    JSON.stringify(applied) + refreshKey
  );

  const loadSummary = useCallback(() => {
    commissionSummary()
      .then(setSummary)
      .catch(() => undefined);
  }, []);

  useEffect(loadSummary, [loadSummary, refreshKey]);

  async function handleRemit(id: number) {
    setBusyId(id);
    setError("");
    try {
      await remitCommission(id);
      setRefreshKey((k) => k + 1);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not mark as remitted.");
    } finally {
      setBusyId(null);
    }
  }

  async function handleSettle(driverId: number) {
    setBusyId(`driver-${driverId}`);
    setError("");
    try {
      const result = await settleDriver(driverId);
      setError("");
      setRefreshKey((k) => k + 1);
      window.alert?.(
        `Settled ${result.settled_count} ride(s) — ${formatNaira(result.settled_amount)}.`
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not settle this driver.");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-bold text-gray-900">Platform commissions</h2>

      {/* Summary */}
      {summary && (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <Card>
            <p className="text-2xl font-extrabold text-amber-600">
              {formatNaira(summary.totals.outstanding)}
            </p>
            <p className="mt-1 text-sm text-gray-500">Outstanding (owed to IJ Ride)</p>
          </Card>
          <Card>
            <p className="text-2xl font-extrabold text-emerald-700">
              {formatNaira(summary.totals.remitted)}
            </p>
            <p className="mt-1 text-sm text-gray-500">Remitted</p>
          </Card>
          <Card>
            <p className="text-2xl font-extrabold text-gray-900">
              {formatNaira(summary.totals.commission_total)}
            </p>
            <p className="mt-1 text-sm text-gray-500">
              Total earned · {summary.totals.rides_with_commission} rides
            </p>
          </Card>
          <Card>
            <p className="text-2xl font-extrabold text-gray-400">
              {formatNaira(summary.totals.waived)}
            </p>
            <p className="mt-1 text-sm text-gray-500">Waived</p>
          </Card>
        </div>
      )}

      {error && <Alert tone="error">{error}</Alert>}

      {/* Per-driver outstanding balances */}
      {summary && summary.drivers_owing.length > 0 && (
        <Card className="space-y-2">
          <h3 className="font-semibold text-gray-900">Drivers owing</h3>
          <ul className="divide-y divide-gray-100">
            {summary.drivers_owing.map((d) => (
              <li key={d.driver_id} className="flex items-center justify-between gap-3 py-2">
                <div>
                  <p className="text-sm font-medium text-gray-900">{d.name || d.phone}</p>
                  <p className="text-xs text-gray-500">
                    {d.phone} · {d.pending_rides} pending ride{d.pending_rides === 1 ? "" : "s"}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="font-bold text-amber-600">{formatNaira(d.outstanding)}</span>
                  <Button
                    variant="secondary"
                    loading={busyId === `driver-${d.driver_id}`}
                    onClick={() => handleSettle(d.driver_id)}
                  >
                    Mark settled
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {/* Records */}
      <div className="flex flex-wrap items-end gap-2">
        <h3 className="mr-auto font-semibold text-gray-900">Commission records</h3>
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm"
        >
          <option value="">All statuses</option>
          <option value="PENDING">Pending</option>
          <option value="REMITTED">Remitted</option>
          <option value="WAIVED">Waived</option>
        </select>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search driver phone or name…"
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
        />
        <button
          onClick={() => setApplied({ status, search })}
          className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white"
        >
          Filter
        </button>
      </div>

      {loading || !data ? (
        <div className="flex justify-center py-16 text-emerald-600">
          <Spinner size="lg" />
        </div>
      ) : (
        <>
          <Table
            head={["Ride", "Driver", "Fare", "Rule", "Commission", "Driver earning", "Status", "Remitted", ""]}
          >
            {data.results.map((c) => (
              <tr key={c.id}>
                <Td className="text-xs text-gray-500">#{c.ride_id}</Td>
                <Td>
                  <p className="text-sm font-medium text-gray-900">{c.driver_name || "—"}</p>
                  <p className="font-mono text-xs text-gray-500">{c.driver_phone}</p>
                </Td>
                <Td>{formatNaira(c.fare_amount)}</Td>
                <Td className="text-xs text-gray-500">
                  {c.commission_type === "PERCENTAGE"
                    ? `${parseFloat(c.commission_value)}%`
                    : c.commission_type === "FIXED"
                      ? `${formatNaira(c.commission_value)} fixed`
                      : "—"}
                </Td>
                <Td className="font-semibold text-amber-700">{formatNaira(c.commission_amount)}</Td>
                <Td>{formatNaira(c.driver_earning)}</Td>
                <Td>
                  <Badge tone={STATUS_TONES[c.status]}>{c.status}</Badge>
                </Td>
                <Td className="text-xs text-gray-500">
                  {c.remitted_at ? formatDateTime(c.remitted_at) : "—"}
                </Td>
                <Td>
                  {c.status === "PENDING" && (
                    <Button
                      variant="ghost"
                      loading={busyId === c.id}
                      onClick={() => handleRemit(c.id)}
                    >
                      Remit
                    </Button>
                  )}
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
