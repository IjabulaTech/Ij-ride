"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { LiveMap } from "@/components/map/LiveMap";
import { PaymentPanel } from "@/components/passenger/PaymentPanel";
import { DriverCard } from "@/components/ride/DriverCard";
import { LiveTrackingCard } from "@/components/ride/LiveTrackingCard";
import { RideRoute } from "@/components/ride/RideRoute";
import { RideStatusBadge } from "@/components/ride/RideStatusBadge";
import { StatusStepper } from "@/components/ride/StatusStepper";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { FullPageSpinner } from "@/components/ui/Spinner";
import { ApiError } from "@/lib/api/client";
import { activeRide, cancelRide, getRide } from "@/lib/api/rides";
import { formatDateTime, formatNaira } from "@/lib/format";
import { useMyLocation } from "@/lib/hooks/useMyLocation";
import { useRideSocket } from "@/lib/hooks/useRideSocket";
import { useRideStageSounds } from "@/lib/hooks/useRideStageSounds";
import type { DriverLocationEvent, Ride, RideStatus } from "@/types/api";

const TERMINAL: RideStatus[] = ["COMPLETED", "CANCELLED", "EXPIRED"];
// V1: passengers may only cancel while the search is still open.
// After ACCEPTED, cancellation is server-blocked and hidden from the UI.
const CANCELLABLE: RideStatus[] = ["SEARCHING"];

export default function ActiveRidePage() {
  const router = useRouter();
  const [ride, setRide] = useState<Ride | null>(null);
  const [loading, setLoading] = useState(true);
  const [cancelOpen, setCancelOpen] = useState(false);
  const [cancelReason, setCancelReason] = useState("");
  const [cancelBusy, setCancelBusy] = useState(false);
  const [error, setError] = useState("");
  // Latest driver position streamed for this ride (drives the ETA readout)
  const [driverLocation, setDriverLocation] = useState<DriverLocationEvent | null>(null);
  const [locationAt, setLocationAt] = useState<number | null>(null);
  const rideIdRef = useRef<number | null>(null);
  rideIdRef.current = ride?.id ?? null;

  // Initial load: the passenger's active ride, or back to booking.
  useEffect(() => {
    let cancelled = false;
    activeRide()
      .then((current) => {
        if (cancelled) return;
        if (current) setRide(current);
        else router.replace("/passenger");
      })
      .catch(() => !cancelled && router.replace("/passenger"))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [router]);

  // Beep on meaningful stage transitions (accepted / arrived / started /
  // completed / payment confirmed) — deduped, so re-fetches don't replay.
  useRideStageSounds(ride, "passenger");

  // Live updates over WebSocket: ride transitions plus the driver's position.
  useRideSocket((message) => {
    if (message.type === "ride.event" && message.ride.id === rideIdRef.current) {
      setRide(message.ride);
    } else if (
      message.type === "ride.driver_location" &&
      message.ride_id === rideIdRef.current
    ) {
      setDriverLocation(message);
      setLocationAt(Date.now());
    }
  });

  // The passenger's own position, for their marker on the map
  const myLocation = useMyLocation(!!ride && !TERMINAL.includes(ride.status));

  // Poll fallback while the ride is active (covers dropped sockets).
  useEffect(() => {
    if (!ride || TERMINAL.includes(ride.status)) return;
    const timer = setInterval(async () => {
      try {
        setRide(await getRide(ride.id));
      } catch {
        /* transient network issues — the next tick retries */
      }
    }, 10_000);
    return () => clearInterval(timer);
  }, [ride?.id, ride?.status]); // eslint-disable-line react-hooks/exhaustive-deps

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

  // ---- terminal screens ----
  if (ride.status === "CANCELLED" || ride.status === "EXPIRED") {
    return (
      <Card className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-gray-900">
            {ride.status === "EXPIRED" ? "No driver found" : "Ride cancelled"}
          </h2>
          <RideStatusBadge status={ride.status} />
        </div>
        <p className="text-sm text-gray-600">
          {ride.status === "EXPIRED"
            ? "No driver was available this time. Please try requesting again."
            : ride.cancellation_reason
              ? `Reason: ${ride.cancellation_reason}`
              : "This ride was cancelled."}
        </p>
        <Link href="/passenger" className="block">
          <Button fullWidth>Book another ride</Button>
        </Link>
      </Card>
    );
  }

  if (ride.status === "COMPLETED") {
    return (
      <div className="space-y-4">
        <Card className="space-y-4 text-center">
          <p className="text-4xl">🎉</p>
          <h2 className="text-lg font-bold text-gray-900">Trip completed</h2>
          <p className="text-3xl font-extrabold text-emerald-700">
            {formatNaira(ride.final_fare)}
          </p>
          <p className="text-sm text-gray-500">Completed {formatDateTime(ride.completed_at)}</p>
        </Card>
        <Card>
          <PaymentPanel ride={ride} onRideUpdate={setRide} />
        </Card>
        <Link href="/passenger" className="block">
          <Button fullWidth variant="secondary">
            Book another ride
          </Button>
        </Link>
      </div>
    );
  }

  // ---- active ride ----
  // Trust the server's idea of the current leg; fall back to the ride status
  // before the first location event arrives.
  const mapTarget = driverLocation
    ? {
        lat: Number(driverLocation.target.lat),
        lng: Number(driverLocation.target.lng),
        label: driverLocation.target.address,
        kind: driverLocation.target.kind,
      }
    : ride.status === "IN_PROGRESS"
      ? {
          lat: Number(ride.dropoff_lat),
          lng: Number(ride.dropoff_lng),
          label: ride.dropoff_address,
          kind: "dropoff" as const,
        }
      : {
          lat: Number(ride.pickup_lat),
          lng: Number(ride.pickup_lng),
          label: ride.pickup_address,
          kind: "pickup" as const,
        };

  return (
    <div className="space-y-4">
      <Card className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-gray-900">Your ride</h2>
          <RideStatusBadge status={ride.status} />
        </div>
        <StatusStepper status={ride.status} />
        {ride.status === "SEARCHING" && (
          <p className="text-sm text-gray-500">
            Notifying nearby drivers… this usually takes a moment.
          </p>
        )}
        {ride.driver && (
          <>
            <LiveMap
              className="h-64"
              driver={
                driverLocation
                  ? {
                      lat: Number(driverLocation.location.lat),
                      lng: Number(driverLocation.location.lng),
                      heading: driverLocation.location.heading,
                    }
                  : null
              }
              target={mapTarget}
              self={myLocation}
              selfLabel="You"
            />
            <LiveTrackingCard
              event={driverLocation}
              receivedAt={locationAt}
              audience="passenger"
            />
            <DriverCard driver={ride.driver} vehicle={ride.vehicle} />
          </>
        )}
        {(ride.status === "ACCEPTED" || ride.status === "DRIVER_ARRIVED") && (
          <p className="text-xs text-gray-500">
            A driver has accepted your ride. If you need to cancel now, please contact support.
          </p>
        )}
      </Card>

      <Card className="space-y-3">
        <RideRoute pickup={ride.pickup_address} dropoff={ride.dropoff_address} />
        <div className="flex items-center justify-between border-t border-gray-100 pt-3">
          <span className="text-sm text-gray-600">Estimated fare</span>
          <span className="text-lg font-bold text-gray-900">
            {formatNaira(ride.estimated_fare)}
          </span>
        </div>
        <PaymentPanel ride={ride} onRideUpdate={setRide} />
      </Card>

      {CANCELLABLE.includes(ride.status) && (
        <Card className="space-y-3">
          {!cancelOpen ? (
            <Button variant="ghost" fullWidth onClick={() => setCancelOpen(true)}>
              Cancel this ride
            </Button>
          ) : (
            <>
              {error && <Alert tone="error">{error}</Alert>}
              <Input
                label="Reason (optional)"
                placeholder="e.g. Change of plans"
                value={cancelReason}
                onChange={(e) => setCancelReason(e.target.value)}
              />
              <div className="flex gap-2">
                <Button
                  variant="secondary"
                  className="flex-1"
                  onClick={() => setCancelOpen(false)}
                >
                  Keep ride
                </Button>
                <Button
                  variant="danger"
                  className="flex-1"
                  loading={cancelBusy}
                  onClick={submitCancel}
                >
                  Cancel ride
                </Button>
              </div>
            </>
          )}
        </Card>
      )}
    </div>
  );
}
