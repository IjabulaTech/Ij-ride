"use client";

import { RideRoute } from "@/components/ride/RideRoute";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import {
  formatDistance,
  formatDuration,
  formatNaira,
  PAYMENT_METHOD_LABELS,
  VEHICLE_CATEGORY_ICONS,
  VEHICLE_CATEGORY_LABELS,
} from "@/lib/format";
import type { OpenRide } from "@/types/api";

export function RequestCard({
  ride,
  busy,
  onAccept,
  onDismiss,
}: {
  ride: OpenRide;
  busy: boolean;
  onAccept: () => void;
  onDismiss: () => void;
}) {
  return (
    <Card className="space-y-3 border-emerald-200">
      <div className="flex items-start justify-between gap-2">
        <RideRoute pickup={ride.pickup_address} dropoff={ride.dropoff_address} />
        <div className="shrink-0 text-right">
          <p className="text-xl font-extrabold text-emerald-700">
            {formatNaira(ride.estimated_fare)}
          </p>
          <p className="text-xs text-gray-500">{PAYMENT_METHOD_LABELS[ride.payment_method]}</p>
        </div>
      </div>
      <p className="text-xs text-gray-500">
        {VEHICLE_CATEGORY_ICONS[ride.requested_vehicle_category]}{" "}
        {VEHICLE_CATEGORY_LABELS[ride.requested_vehicle_category]} ·{" "}
        {formatDistance(ride.estimated_distance_m)} · about{" "}
        {formatDuration(ride.estimated_duration_s)}
        {ride.passenger_first_name && <> · for {ride.passenger_first_name}</>}
      </p>
      <div className="flex gap-2">
        <Button variant="ghost" className="flex-1" onClick={onDismiss} disabled={busy}>
          Dismiss
        </Button>
        <Button className="flex-[2]" loading={busy} onClick={onAccept}>
          Accept ride
        </Button>
      </div>
    </Card>
  );
}
