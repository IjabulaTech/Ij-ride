"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { RideRoute } from "@/components/ride/RideRoute";
import { RideStatusBadge } from "@/components/ride/RideStatusBadge";
import { Alert } from "@/components/ui/Alert";
import { Badge, paymentStatusTone } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { FullPageSpinner } from "@/components/ui/Spinner";
import { getAdminRide } from "@/lib/api/admin";
import {
  formatDateTime,
  formatDistance,
  formatDuration,
  formatNaira,
  PAYMENT_METHOD_LABELS,
} from "@/lib/format";
import type { Ride } from "@/types/api";

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-gray-500">{label}</p>
      <p className="text-sm font-medium text-gray-900">{value || "—"}</p>
    </div>
  );
}

export default function AdminRideDetailPage() {
  const params = useParams<{ id: string }>();
  const [ride, setRide] = useState<Ride | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getAdminRide(Number(params.id))
      .then(setRide)
      .catch(() => setError("Could not load this ride."));
  }, [params.id]);

  if (error) {
    return (
      <div className="space-y-4">
        <Alert tone="error">{error}</Alert>
        <Link href="/admin/rides" className="text-sm font-semibold text-emerald-600">
          ← Back to rides
        </Link>
      </div>
    );
  }
  if (!ride) return <FullPageSpinner />;

  return (
    <div className="max-w-2xl space-y-4">
      <Link href="/admin/rides" className="text-sm font-semibold text-emerald-600">
        ← Back to rides
      </Link>

      <Card className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-gray-900">Ride #{ride.id}</h2>
          <RideStatusBadge status={ride.status} />
        </div>
        <RideRoute pickup={ride.pickup_address} dropoff={ride.dropoff_address} />
        <div className="grid grid-cols-2 gap-3 border-t border-gray-100 pt-3 sm:grid-cols-3">
          <Field
            label="Passenger"
            value={`${[ride.passenger.first_name, ride.passenger.last_name]
              .filter(Boolean)
              .join(" ")} (${ride.passenger.phone})`}
          />
          <Field
            label="Driver"
            value={
              ride.driver
                ? `${[ride.driver.first_name, ride.driver.last_name]
                    .filter(Boolean)
                    .join(" ")} (${ride.driver.phone})`
                : ""
            }
          />
          <Field label="Vehicle" value={ride.vehicle?.plate_number ?? ""} />
          <Field label="Distance" value={formatDistance(ride.estimated_distance_m)} />
          <Field label="Duration (est.)" value={formatDuration(ride.estimated_duration_s)} />
          <Field
            label="Fare"
            value={`${formatNaira(ride.final_fare ?? ride.estimated_fare)}${ride.final_fare ? "" : " (est.)"}`}
          />
        </div>
        <div className="grid grid-cols-2 gap-3 border-t border-gray-100 pt-3 text-xs sm:grid-cols-3">
          <Field label="Requested" value={formatDateTime(ride.created_at)} />
          <Field label="Accepted" value={formatDateTime(ride.accepted_at)} />
          <Field label="Arrived" value={formatDateTime(ride.arrived_at)} />
          <Field label="Started" value={formatDateTime(ride.started_at)} />
          <Field label="Completed" value={formatDateTime(ride.completed_at)} />
          <Field label="Cancelled" value={formatDateTime(ride.cancelled_at)} />
        </div>
        {ride.status === "CANCELLED" && (
          <Alert tone="error">
            Cancelled by {ride.cancelled_by_role.toLowerCase()}
            {ride.cancellation_reason ? `: ${ride.cancellation_reason}` : "."}
          </Alert>
        )}
      </Card>

      {ride.payment && (
        <Card className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-gray-900">Payment</h3>
            <Badge tone={paymentStatusTone(ride.payment.status)}>{ride.payment.status}</Badge>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <Field label="Method" value={PAYMENT_METHOD_LABELS[ride.payment.method]} />
            <Field label="Amount" value={formatNaira(ride.payment.amount)} />
            <Field label="Reference" value={ride.payment.reference} />
            <Field label="Claimed at" value={formatDateTime(ride.payment.claimed_at)} />
            <Field label="Confirmed at" value={formatDateTime(ride.payment.confirmed_at)} />
          </div>
        </Card>
      )}
    </div>
  );
}
