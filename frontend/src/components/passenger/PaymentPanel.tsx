"use client";

import { useState } from "react";

import { Badge, paymentStatusTone } from "@/components/ui/Badge";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { ApiError } from "@/lib/api/client";
import { claimPayment } from "@/lib/api/rides";
import { formatNaira, PAYMENT_METHOD_LABELS } from "@/lib/format";
import type { Ride } from "@/types/api";

/** Passenger-side payment box: shows method/status; for transfers lets the
 * passenger send the "I have paid" claim with an optional bank reference. */
export function PaymentPanel({ ride, onRideUpdate }: { ride: Ride; onRideUpdate: (r: Ride) => void }) {
  const payment = ride.payment;
  const [reference, setReference] = useState(payment?.reference ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  if (!payment) return null;

  const amount = payment.amount ?? ride.final_fare ?? ride.estimated_fare;
  const canClaim =
    payment.method === "TRANSFER" &&
    (ride.status === "IN_PROGRESS" || ride.status === "COMPLETED") &&
    (payment.status === "PENDING" || payment.status === "CLAIMED");

  async function submitClaim() {
    setBusy(true);
    setError("");
    try {
      onRideUpdate(await claimPayment(ride.id, reference));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not send. Try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-3 rounded-lg bg-gray-50 p-3">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs text-gray-500">Payment · {PAYMENT_METHOD_LABELS[payment.method]}</p>
          <p className="text-lg font-bold text-gray-900">{formatNaira(amount)}</p>
        </div>
        <Badge tone={paymentStatusTone(payment.status)}>{payment.status}</Badge>
      </div>

      {payment.method === "CASH" && payment.status === "PENDING" && (
        <p className="text-sm text-gray-600">
          Pay the driver in cash at the end of your trip.
        </p>
      )}

      {payment.status === "PAID" && (
        <p className="text-sm font-medium text-emerald-700">Payment confirmed. Thank you!</p>
      )}

      {canClaim && (
        <div className="space-y-2">
          {payment.status === "CLAIMED" && (
            <p className="text-sm text-gray-600">
              Marked as sent — waiting for the driver to confirm. You can update the reference
              below if needed.
            </p>
          )}
          {error && <Alert tone="error">{error}</Alert>}
          <Input
            label="Transfer reference (optional)"
            placeholder="e.g. GTB-2026-0001"
            value={reference}
            onChange={(e) => setReference(e.target.value)}
          />
          <Button fullWidth loading={busy} onClick={submitClaim}>
            {payment.status === "CLAIMED" ? "Update reference" : "I have sent the transfer"}
          </Button>
        </div>
      )}
    </div>
  );
}
