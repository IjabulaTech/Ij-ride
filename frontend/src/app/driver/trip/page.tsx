"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { DriverPaymentPanel } from "@/components/driver/DriverPaymentPanel";
import { RideRoute } from "@/components/ride/RideRoute";
import { RideStatusBadge } from "@/components/ride/RideStatusBadge";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { FullPageSpinner } from "@/components/ui/Spinner";
import { ApiError } from "@/lib/api/client";
import {
  activeRide,
  cancelRide,
  completeTrip,
  getRide,
  markArrived,
  startTrip,
} from "@/lib/api/rides";
import { formatNaira, PAYMENT_METHOD_LABELS } from "@/lib/format";
import { useRideSocket } from "@/lib/hooks/useRideSocket";
import type { Ride, RideStatus } from "@/types/api";

const TERMINAL: RideStatus[] = ["COMPLETED", "CANCELLED", "EXPIRED"];

const NEXT_ACTION: Partial<
  Record<RideStatus, { label: string; run: (id: number) => Promise<Ride> }>
> = {
  ACCEPTED: { label: "I've arrived at the pickup", run: markArrived },
  DRIVER_ARRIVED: { label: "Start trip", run: startTrip },
  IN_PROGRESS: { label: "Complete trip", run: completeTrip },
};

export default function DriverTripPage() {
  const router = useRouter();
  const [ride, setRide] = useState<Ride | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionBusy, setActionBusy] = useState(false);
  const [cancelOpen, setCancelOpen] = useState(false);
  const [cancelReason, setCancelReason] = useState("");
  const [cancelBusy, setCancelBusy] = useState(false);
  const [error, setError] = useState("");
  const rideIdRef = useRef<number | null>(null);
  rideIdRef.current = ride?.id ?? null;

  useEffect(() => {
    let cancelled = false;
    activeRide()
      .then((current) => {
        if (cancelled) return;
        if (current) setRide(current);
        else router.replace("/driver");
      })
      .catch(() => !cancelled && router.replace("/driver"))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [router]);

  useRideSocket((message) => {
    if (message.type === "ride.event" && message.ride.id === rideIdRef.current) {
      setRide(message.ride);
    }
  });

  useEffect(() => {
    if (!ride || TERMINAL.includes(ride.status)) return;
    const timer = setInterval(async () => {
      try {
        setRide(await getRide(ride.id));
      } catch {
        /* next tick retries */
      }
    }, 10_000);
    return () => clearInterval(timer);
  }, [ride?.id, ride?.status]); // eslint-disable-line react-hooks/exhaustive-deps

  async function runAction() {
    if (!ride) return;
    const action = NEXT_ACTION[ride.status];
    if (!action) return;
    setActionBusy(true);
    setError("");
    try {
      setRide(await action.run(ride.id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not update the trip. Try again.");
    } finally {
      setActionBusy(false);
    }
  }

  async function submitCancel() {
    if (!ride) return;
    setCancelBusy(true);
    setError("");
    try {
      setRide(await cancelRide(ride.id, cancelReason));
      setCancelOpen(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not cancel. Try again.");
    } finally {
      setCancelBusy(false);
    }
  }

  if (loading || !ride) return <FullPageSpinner />;

  const passenger = ride.passenger;
  const passengerName =
    [passenger.first_name, passenger.last_name].filter(Boolean).join(" ") || "Passenger";

  if (ride.status === "CANCELLED" || ride.status === "EXPIRED") {
    return (
      <Card className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-gray-900">Ride {ride.status.toLowerCase()}</h2>
          <RideStatusBadge status={ride.status} />
        </div>
        {ride.cancellation_reason && (
          <p className="text-sm text-gray-600">Reason: {ride.cancellation_reason}</p>
        )}
        <Link href="/driver" className="block">
          <Button fullWidth>Back to dashboard</Button>
        </Link>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <Card className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-gray-900">Current trip</h2>
          <RideStatusBadge status={ride.status} />
        </div>

        {/* Passenger contact */}
        <div className="flex items-center justify-between rounded-lg bg-gray-50 p-3">
          <div>
            <p className="font-semibold text-gray-900">{passengerName}</p>
            <p className="text-sm text-gray-500">
              {PAYMENT_METHOD_LABELS[ride.payment_method]} ·{" "}
              {formatNaira(ride.final_fare ?? ride.estimated_fare)}
            </p>
          </div>
          <a
            href={`tel:${passenger.phone}`}
            className="rounded-full bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700"
          >
            Call
          </a>
        </div>

        <RideRoute pickup={ride.pickup_address} dropoff={ride.dropoff_address} />
        {error && <Alert tone="error">{error}</Alert>}

        {NEXT_ACTION[ride.status] && (
          <Button fullWidth loading={actionBusy} onClick={runAction}>
            {NEXT_ACTION[ride.status]!.label}
          </Button>
        )}
      </Card>

      {ride.status === "COMPLETED" && (
        <>
          <Card>
            <DriverPaymentPanel ride={ride} onRideUpdate={setRide} />
          </Card>
          <Link href="/driver" className="block">
            <Button fullWidth variant="secondary">
              Back to dashboard
            </Button>
          </Link>
        </>
      )}

      {(ride.status === "ACCEPTED" || ride.status === "DRIVER_ARRIVED") && (
        <Card className="space-y-3">
          {!cancelOpen ? (
            <Button variant="ghost" fullWidth onClick={() => setCancelOpen(true)}>
              Cancel this trip
            </Button>
          ) : (
            <>
              <Input
                label="Reason (required)"
                placeholder="e.g. Vehicle problem"
                value={cancelReason}
                onChange={(e) => setCancelReason(e.target.value)}
              />
              <div className="flex gap-2">
                <Button variant="secondary" className="flex-1" onClick={() => setCancelOpen(false)}>
                  Keep trip
                </Button>
                <Button
                  variant="danger"
                  className="flex-1"
                  loading={cancelBusy}
                  onClick={submitCancel}
                >
                  Cancel trip
                </Button>
              </div>
            </>
          )}
        </Card>
      )}
    </div>
  );
}
