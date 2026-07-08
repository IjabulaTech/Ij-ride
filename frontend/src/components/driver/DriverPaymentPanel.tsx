"use client";

import { useState } from "react";

import { Alert } from "@/components/ui/Alert";
import { Badge, paymentStatusTone } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { ApiError } from "@/lib/api/client";
import { confirmPayment } from "@/lib/api/rides";
import { formatDateTime, formatNaira, PAYMENT_METHOD_LABELS } from "@/lib/format";
import type { Ride } from "@/types/api";

/** Driver-side payment box: collect instructions and the "payment received"
 * confirmation once the trip is completed. */
export function DriverPaymentPanel({
  ride,
  onRideUpdate,
}: {
  ride: Ride;
  onRideUpdate: (r: Ride) => void;
}) {
  const payment = ride.payment;
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  if (!payment) return null;

  const amount = payment.amount ?? ride.final_fare ?? ride.estimated_fare;
  const canConfirm =
    ride.status === "COMPLETED" && payment.status !== "PAID" && payment.status !== "FAILED";

  async function confirm() {
    setBusy(true);
    setError("");
    try {
      onRideUpdate(await confirmPayment(ride.id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not confirm. Try again.");
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

      {payment.status === "PAID" && (
        <p className="text-sm font-medium text-emerald-700">
          Payment confirmed {formatDateTime(payment.confirmed_at)}.
        </p>
      )}

      {canConfirm && (
        <div className="space-y-2">
          {payment.method === "CASH" ? (
            <p className="text-sm text-gray-600">
              Collect <span className="font-semibold">{formatNaira(amount)}</span> in cash from
              the passenger.
            </p>
          ) : payment.status === "CLAIMED" ? (
            <div className="rounded-md bg-blue-50 p-2 text-sm text-blue-800">
              Passenger says they&apos;ve sent the transfer
              {payment.reference && (
                <>
                  {" "}
                  — reference: <span className="font-mono font-semibold">{payment.reference}</span>
                </>
              )}
              . Check your account before confirming.
            </div>
          ) : (
            <p className="text-sm text-gray-600">
              Waiting for the passenger&apos;s transfer of{" "}
              <span className="font-semibold">{formatNaira(amount)}</span>. Confirm once it lands.
            </p>
          )}
          {error && <Alert tone="error">{error}</Alert>}
          <Button fullWidth loading={busy} onClick={confirm}>
            Payment received
          </Button>
        </div>
      )}
    </div>
  );
}
