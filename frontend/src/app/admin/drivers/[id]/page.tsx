"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { Alert } from "@/components/ui/Alert";
import { approvalStatusTone, Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { FullPageSpinner } from "@/components/ui/Spinner";
import { ApiError } from "@/lib/api/client";
import { approveDriver, getDriver, rejectDriver } from "@/lib/api/admin";
import { formatDateTime } from "@/lib/format";
import type { AdminDriver } from "@/types/api";

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-gray-500">{label}</p>
      <p className="text-sm font-medium text-gray-900">{value || "—"}</p>
    </div>
  );
}

export default function AdminDriverDetailPage() {
  const params = useParams<{ id: string }>();
  const [driver, setDriver] = useState<AdminDriver | null>(null);
  const [note, setNote] = useState("");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState<"approve" | "reject" | null>(null);
  const [error, setError] = useState("");
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    getDriver(Number(params.id))
      .then(setDriver)
      .catch(() => setLoadError("Could not load this driver."));
  }, [params.id]);

  async function act(kind: "approve" | "reject") {
    if (!driver) return;
    if (kind === "reject" && !reason.trim()) {
      setError("A rejection reason is required.");
      return;
    }
    setBusy(kind);
    setError("");
    try {
      const updated =
        kind === "approve"
          ? await approveDriver(driver.id, note)
          : await rejectDriver(driver.id, reason);
      setDriver(updated);
      setNote("");
      setReason("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Action failed. Try again.");
    } finally {
      setBusy(null);
    }
  }

  if (loadError) {
    return (
      <div className="space-y-4">
        <Alert tone="error">{loadError}</Alert>
        <Link href="/admin/drivers" className="text-sm font-semibold text-emerald-600">
          ← Back to drivers
        </Link>
      </div>
    );
  }
  if (!driver) return <FullPageSpinner />;

  const name =
    [driver.user.first_name, driver.user.last_name].filter(Boolean).join(" ") || driver.user.phone;

  return (
    <div className="max-w-2xl space-y-4">
      <Link href="/admin/drivers" className="text-sm font-semibold text-emerald-600">
        ← Back to drivers
      </Link>

      <Card className="space-y-4">
        <div className="flex items-center justify-between gap-3">
          <div className="flex min-w-0 items-center gap-3">
            {driver.photo_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={driver.photo_url}
                alt={name}
                className="h-12 w-12 shrink-0 rounded-full border border-gray-200 object-cover"
              />
            ) : (
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-gray-100 text-lg text-gray-400">
                👤
              </div>
            )}
            <h2 className="truncate text-lg font-bold text-gray-900">{name}</h2>
          </div>
          <Badge tone={approvalStatusTone(driver.approval_status)}>{driver.approval_status}</Badge>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Phone" value={driver.user.phone} />
          <Field label="Email" value={driver.user.email} />
          <Field label="License number" value={driver.license_number} />
          <Field label="Registered" value={formatDateTime(driver.created_at)} />
          <Field
            label="Vehicle"
            value={
              driver.active_vehicle
                ? `${driver.active_vehicle.color} ${driver.active_vehicle.make} ${driver.active_vehicle.model} (${driver.active_vehicle.year})`
                : ""
            }
          />
          <Field label="Plate number" value={driver.active_vehicle?.plate_number ?? ""} />
          <Field
            label="Availability"
            value={driver.availability?.is_online ? "Online" : "Offline"}
          />
          <Field label="Approved at" value={formatDateTime(driver.approved_at)} />
        </div>
        {driver.approval_note && (
          <Alert tone="info">Last review note: {driver.approval_note}</Alert>
        )}
      </Card>

      <Card className="space-y-4">
        <h3 className="font-semibold text-gray-900">Review decision</h3>
        {error && <Alert tone="error">{error}</Alert>}

        {driver.approval_status !== "APPROVED" && (
          <div className="space-y-2 rounded-lg border border-emerald-200 bg-emerald-50/50 p-3">
            <Input
              label="Approval note (optional)"
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
            <Button fullWidth loading={busy === "approve"} onClick={() => act("approve")}>
              Approve driver
            </Button>
          </div>
        )}

        {driver.approval_status !== "REJECTED" && (
          <div className="space-y-2 rounded-lg border border-red-200 bg-red-50/50 p-3">
            <Input
              label="Rejection reason (required)"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
            <Button
              fullWidth
              variant="danger"
              loading={busy === "reject"}
              onClick={() => act("reject")}
            >
              Reject driver
            </Button>
          </div>
        )}
      </Card>
    </div>
  );
}
