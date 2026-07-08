"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { DriverPaymentPanel } from "@/components/driver/DriverPaymentPanel";
import { RideRoute } from "@/components/ride/RideRoute";
import { RideStatusBadge } from "@/components/ride/RideStatusBadge";
import { Alert } from "@/components/ui/Alert";
import { Card } from "@/components/ui/Card";
import { FullPageSpinner } from "@/components/ui/Spinner";
import { getRide } from "@/lib/api/rides";
import { formatDateTime, formatDistance, formatDuration, formatNaira } from "@/lib/format";
import type { Ride } from "@/types/api";

export default function DriverRideDetailPage() {
  const params = useParams<{ id: string }>();
  const [ride, setRide] = useState<Ride | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getRide(Number(params.id))
      .then(setRide)
      .catch(() => setError("Could not load this trip."));
  }, [params.id]);

  if (error) {
    return (
      <div className="space-y-4">
        <Alert tone="error">{error}</Alert>
        <Link href="/driver/history" className="text-sm font-semibold text-emerald-600">
          ← Back to history
        </Link>
      </div>
    );
  }
  if (!ride) return <FullPageSpinner />;

  const passengerName =
    [ride.passenger.first_name, ride.passenger.last_name].filter(Boolean).join(" ") ||
    "Passenger";

  return (
    <div className="space-y-4">
      <Link href="/driver/history" className="text-sm font-semibold text-emerald-600">
        ← Back to history
      </Link>

      <Card className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-gray-900">Trip #{ride.id}</h2>
          <RideStatusBadge status={ride.status} />
        </div>
        <p className="text-xs text-gray-500">
          {formatDateTime(ride.created_at)} · {passengerName}
        </p>
        <RideRoute pickup={ride.pickup_address} dropoff={ride.dropoff_address} />
        <div className="grid grid-cols-2 gap-2 border-t border-gray-100 pt-3 text-sm">
          <div>
            <p className="text-xs text-gray-500">Distance</p>
            <p className="font-medium">{formatDistance(ride.estimated_distance_m)}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Duration (est.)</p>
            <p className="font-medium">{formatDuration(ride.estimated_duration_s)}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Fare</p>
            <p className="font-bold">{formatNaira(ride.final_fare ?? ride.estimated_fare)}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Completed</p>
            <p className="font-medium">{formatDateTime(ride.completed_at)}</p>
          </div>
        </div>
        {ride.status === "CANCELLED" && (
          <p className="text-sm text-red-600">
            Cancelled by {ride.cancelled_by_role.toLowerCase()}
            {ride.cancellation_reason ? `: ${ride.cancellation_reason}` : "."}
          </p>
        )}
      </Card>

      <Card>
        <DriverPaymentPanel ride={ride} onRideUpdate={setRide} />
      </Card>
    </div>
  );
}
