"use client";

import { useEffect, useState } from "react";

import { Alert } from "@/components/ui/Alert";
import { Card } from "@/components/ui/Card";
import { FullPageSpinner } from "@/components/ui/Spinner";
import { getEarnings } from "@/lib/api/driver";
import { formatNaira } from "@/lib/format";
import type { Earnings, EarningsWindow } from "@/types/api";

const WINDOWS: { key: "today" | "last_7_days" | "all_time"; label: string }[] = [
  { key: "today", label: "Today" },
  { key: "last_7_days", label: "Last 7 days" },
  { key: "all_time", label: "All time" },
];

function EarningsCard({ label, data }: { label: string; data: EarningsWindow }) {
  return (
    <Card className="space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-gray-900">{label}</h3>
        <span className="text-xs text-gray-500">
          {data.trips} trip{data.trips === 1 ? "" : "s"}
        </span>
      </div>
      <p className="text-3xl font-extrabold text-emerald-700">{formatNaira(data.net)}</p>
      <p className="text-xs text-gray-500">
        Your earnings after {formatNaira(data.commission)} IJ Ride commission (gross{" "}
        {formatNaira(data.gross)})
      </p>
      <div className="flex justify-between border-t border-gray-100 pt-2 text-sm">
        <span className="text-gray-500">
          Confirmed: <span className="font-semibold text-gray-900">{formatNaira(data.paid)}</span>
        </span>
        <span className="text-gray-500">
          Unpaid: <span className="font-semibold text-amber-600">{formatNaira(data.unpaid)}</span>
        </span>
      </div>
    </Card>
  );
}

export default function EarningsPage() {
  const [earnings, setEarnings] = useState<Earnings | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getEarnings()
      .then(setEarnings)
      .catch(() => setError("Could not load your earnings."));
  }, []);

  if (error) return <Alert tone="error">{error}</Alert>;
  if (!earnings) return <FullPageSpinner />;

  const owed = parseFloat(earnings.outstanding_commission);

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-bold text-gray-900">Earnings</h2>
      {owed > 0 && (
        <Alert tone="info">
          You currently owe IJ Ride{" "}
          <span className="font-bold">{formatNaira(earnings.outstanding_commission)}</span> in
          commission. Please remit to the IJ Ride account — an admin will confirm it.
        </Alert>
      )}
      {WINDOWS.map(({ key, label }) => (
        <EarningsCard key={key} label={label} data={earnings[key]} />
      ))}
      <p className="text-xs text-gray-500">
        Figures show your net earnings after IJ Ride&apos;s commission. Confirmed counts trips
        whose payment was marked received.
      </p>
    </div>
  );
}
